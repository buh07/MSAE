#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import subprocess
import time
from pathlib import Path
from typing import Any

import numpy as np
import torch
from transformers import AutoModelForCausalLM, AutoTokenizer

from pcc_stage_a1_audit import (
    UD_DEV_URL,
    UD_TRAIN_URL,
    TaskDataset,
    annotate_ud_examples_for_a1,
    compute_ambiguous_vocab,
    ensure_download,
    extract_features_and_labels,
    family_rows_from_tasks,
    infer_d_model,
    load_fewnerd_examples,
    load_msae_from_checkpoint,
    load_wikineural_examples,
    load_wnut_examples,
    parse_conllu,
    prepare_task_dataset,
    resolve_git_commit_hash,
    run_probe_for_rep,
    set_seed,
    write_tsv,
)
from raw_activation_separability_pilot import TorchProbeConfig, choose_device, choose_probe_backend
from train_msae_k2 import choose_dtype


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Stage A1b PCC diagnostic audit on existing K=2 checkpoints")
    p.add_argument("--checkpoint_path", type=str, required=True)
    p.add_argument("--model_name", type=str, default="EleutherAI/pythia-160m-deduped")
    p.add_argument("--layer_index", type=int, default=3)
    p.add_argument("--seed", type=int, default=42)
    p.add_argument("--device", type=str, default="auto", choices=["auto", "cpu", "cuda"])
    p.add_argument("--dtype", type=str, default="auto", choices=["auto", "fp16", "bf16", "fp32"])
    p.add_argument("--output_dir", type=str, required=True)
    p.add_argument("--git_commit_hash", type=str, default="")
    p.add_argument("--context_length", type=int, default=192)
    p.add_argument("--model_batch_size", type=int, default=12)
    p.add_argument("--probe_backend", type=str, default="auto", choices=["auto", "sklearn", "torch"])
    p.add_argument("--probe_c", type=float, default=0.2)
    p.add_argument("--probe_torch_max_steps", type=int, default=1200)
    p.add_argument("--probe_torch_batch_size", type=int, default=8192)
    p.add_argument("--probe_torch_lr", type=float, default=0.02)
    p.add_argument("--probe_torch_scheduler", type=str, default="cosine", choices=["none", "cosine"])
    p.add_argument("--probe_torch_weight_decay", type=float, default=-1.0)
    p.add_argument("--probe_torch_eval_every", type=int, default=50)
    p.add_argument("--probe_torch_patience", type=int, default=300)
    p.add_argument("--probe_torch_min_steps", type=int, default=200)
    p.add_argument("--probe_torch_token_ceiling_top1", type=float, default=0.995)
    p.add_argument("--probe_torch_token_ceiling_evals", type=int, default=3)
    p.add_argument("--probe_torch_token_ceiling_loss_eps", type=float, default=1e-4)
    p.add_argument("--probe_torch_lr_position_raw_highdim", type=float, default=0.01)
    p.add_argument("--probe_torch_lr_position_raw_highdim_threshold", type=int, default=768)
    p.add_argument("--min_examples_per_class", type=int, default=20)
    p.add_argument("--max_train_sentences_ud", type=int, default=4000)
    p.add_argument("--max_eval_sentences_ud", type=int, default=1000)
    p.add_argument("--max_train_sentences_wnut", type=int, default=3394)
    p.add_argument("--max_eval_sentences_wnut", type=int, default=1009)
    p.add_argument("--max_train_sentences_fewnerd", type=int, default=12000)
    p.add_argument("--max_eval_sentences_fewnerd", type=int, default=3000)
    p.add_argument("--max_train_sentences_wikineural", type=int, default=12000)
    p.add_argument("--max_eval_sentences_wikineural", type=int, default=3000)
    p.add_argument("--cache_dir", type=str, default="")
    return p.parse_args()


def collapse_bio_label(label: str) -> str:
    if label == "O":
        return "O"
    if label.startswith("B-") or label.startswith("I-"):
        return label.split("-", 1)[1]
    return label


def labels_typeonly(labels: np.ndarray) -> np.ndarray:
    return np.asarray([collapse_bio_label(str(x)) for x in labels.tolist()], dtype=object)


def labels_entity_binary(labels: np.ndarray) -> np.ndarray:
    out: list[str] = []
    for x in labels.tolist():
        s = str(x)
        out.append("ENTITY" if s != "O" else "O")
    return np.asarray(out, dtype=object)


def add_task(
    tasks: list[TaskDataset],
    *,
    name: str,
    family: str,
    metric_name: str,
    train_raw: np.ndarray,
    train_pos: np.ndarray,
    train_content: np.ndarray,
    train_resid: np.ndarray,
    train_labels: np.ndarray,
    eval_raw: np.ndarray,
    eval_pos: np.ndarray,
    eval_content: np.ndarray,
    eval_resid: np.ndarray,
    eval_labels: np.ndarray,
    min_examples_per_class: int,
    train_source: str,
    eval_source: str,
) -> None:
    tasks.append(
        prepare_task_dataset(
            name,
            family,
            metric_name,
            train_raw,
            train_pos,
            train_content,
            train_resid,
            train_labels,
            eval_raw,
            eval_pos,
            eval_content,
            eval_resid,
            eval_labels,
            min_examples_per_class,
            train_source,
            eval_source,
        )
    )


def main() -> None:
    args = parse_args()
    set_seed(args.seed)
    device = choose_device(args.device)
    dtype = choose_dtype(args.dtype)
    probe_backend = choose_probe_backend(args.probe_backend, device)

    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "probe_logs").mkdir(parents=True, exist_ok=True)
    cache_dir = Path(args.cache_dir) if args.cache_dir else (out_dir / "cache")
    cache_dir.mkdir(parents=True, exist_ok=True)
    git_hash = resolve_git_commit_hash(args.git_commit_hash)

    ud_train_path = ensure_download(UD_TRAIN_URL, cache_dir / "ud" / "en_ewt-ud-train.conllu")
    ud_dev_path = ensure_download(UD_DEV_URL, cache_dir / "ud" / "en_ewt-ud-dev.conllu")
    ud_train = parse_conllu(ud_train_path, args.max_train_sentences_ud)
    ud_dev = parse_conllu(ud_dev_path, args.max_eval_sentences_ud)
    ambiguous_vocab = compute_ambiguous_vocab(ud_train)
    annotate_ud_examples_for_a1(ud_train, ambiguous_vocab)
    annotate_ud_examples_for_a1(ud_dev, ambiguous_vocab)

    wnut_train = load_wnut_examples("train", args.max_train_sentences_wnut)
    wnut_eval = load_wnut_examples("validation", args.max_eval_sentences_wnut)
    fewnerd_train = load_fewnerd_examples("train", args.max_train_sentences_fewnerd)
    fewnerd_eval = load_fewnerd_examples("validation", args.max_eval_sentences_fewnerd)
    wikineural_train = load_wikineural_examples("train_en", args.max_train_sentences_wikineural)
    wikineural_eval = load_wikineural_examples("val_en", args.max_eval_sentences_wikineural)

    tokenizer = AutoTokenizer.from_pretrained(args.model_name, use_fast=True)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token
    model_lm = AutoModelForCausalLM.from_pretrained(args.model_name, torch_dtype=dtype, low_cpu_mem_usage=True).to(device)
    model_lm.eval()
    model_lm.config.use_cache = False

    d_model = infer_d_model(model_lm, tokenizer, device, args.layer_index)
    msae, ckpt = load_msae_from_checkpoint(Path(args.checkpoint_path), device, d_model)

    torch_cfg = TorchProbeConfig(
        max_steps=int(args.probe_torch_max_steps),
        batch_size=int(args.probe_torch_batch_size),
        lr=float(args.probe_torch_lr),
        weight_decay=float(args.probe_torch_weight_decay),
        eval_every=int(args.probe_torch_eval_every),
        patience=int(args.probe_torch_patience),
        min_steps=int(args.probe_torch_min_steps),
        token_ceiling_top1=float(args.probe_torch_token_ceiling_top1),
        token_ceiling_evals=int(args.probe_torch_token_ceiling_evals),
        token_ceiling_loss_eps=float(args.probe_torch_token_ceiling_loss_eps),
        position_raw_highdim_lr=float(args.probe_torch_lr_position_raw_highdim),
        position_raw_highdim_threshold=int(args.probe_torch_lr_position_raw_highdim_threshold),
        scheduler=str(args.probe_torch_scheduler),
    )

    t0 = time.time()
    ud_train_raw, ud_train_pos, ud_train_content, ud_train_resid, ud_train_labels = extract_features_and_labels(
        ud_train,
        ["pos", "pos_ambig", "deprel_coarse", "number", "head_dir_dist"],
        model_lm, tokenizer, msae, device, args.layer_index, args.context_length, args.model_batch_size,
    )
    ud_eval_raw, ud_eval_pos, ud_eval_content, ud_eval_resid, ud_eval_labels = extract_features_and_labels(
        ud_dev,
        ["pos", "pos_ambig", "deprel_coarse", "number", "head_dir_dist"],
        model_lm, tokenizer, msae, device, args.layer_index, args.context_length, args.model_batch_size,
    )
    wnut_train_raw, wnut_train_pos, wnut_train_content, wnut_train_resid, wnut_train_labels = extract_features_and_labels(
        wnut_train, ["ner"], model_lm, tokenizer, msae, device, args.layer_index, args.context_length, args.model_batch_size,
    )
    wnut_eval_raw, wnut_eval_pos, wnut_eval_content, wnut_eval_resid, wnut_eval_labels = extract_features_and_labels(
        wnut_eval, ["ner"], model_lm, tokenizer, msae, device, args.layer_index, args.context_length, args.model_batch_size,
    )
    few_train_raw, few_train_pos, few_train_content, few_train_resid, few_train_labels = extract_features_and_labels(
        fewnerd_train, ["ner"], model_lm, tokenizer, msae, device, args.layer_index, args.context_length, args.model_batch_size,
    )
    few_eval_raw, few_eval_pos, few_eval_content, few_eval_resid, few_eval_labels = extract_features_and_labels(
        fewnerd_eval, ["ner"], model_lm, tokenizer, msae, device, args.layer_index, args.context_length, args.model_batch_size,
    )
    wiki_train_raw, wiki_train_pos, wiki_train_content, wiki_train_resid, wiki_train_labels = extract_features_and_labels(
        wikineural_train, ["ner"], model_lm, tokenizer, msae, device, args.layer_index, args.context_length, args.model_batch_size,
    )
    wiki_eval_raw, wiki_eval_pos, wiki_eval_content, wiki_eval_resid, wiki_eval_labels = extract_features_and_labels(
        wikineural_eval, ["ner"], model_lm, tokenizer, msae, device, args.layer_index, args.context_length, args.model_batch_size,
    )
    extract_elapsed = time.time() - t0

    tasks: list[TaskDataset] = []
    add_task(
        tasks,
        name="pos_ud_ewt",
        family="syntax_pos",
        metric_name="accuracy",
        train_raw=ud_train_raw,
        train_pos=ud_train_pos,
        train_content=ud_train_content,
        train_resid=ud_train_resid,
        train_labels=ud_train_labels["pos"],
        eval_raw=ud_eval_raw,
        eval_pos=ud_eval_pos,
        eval_content=ud_eval_content,
        eval_resid=ud_eval_resid,
        eval_labels=ud_eval_labels["pos"],
        min_examples_per_class=args.min_examples_per_class,
        train_source="UD_EWT_train",
        eval_source="UD_EWT_dev",
    )
    add_task(
        tasks,
        name="pos_ambig_ud_ewt",
        family="syntax_pos",
        metric_name="accuracy",
        train_raw=ud_train_raw,
        train_pos=ud_train_pos,
        train_content=ud_train_content,
        train_resid=ud_train_resid,
        train_labels=ud_train_labels["pos_ambig"],
        eval_raw=ud_eval_raw,
        eval_pos=ud_eval_pos,
        eval_content=ud_eval_content,
        eval_resid=ud_eval_resid,
        eval_labels=ud_eval_labels["pos_ambig"],
        min_examples_per_class=args.min_examples_per_class,
        train_source="UD_EWT_train",
        eval_source="UD_EWT_dev",
    )
    add_task(
        tasks,
        name="deprel_coarse_ud_ewt",
        family="syntax_dep_coarse",
        metric_name="accuracy",
        train_raw=ud_train_raw,
        train_pos=ud_train_pos,
        train_content=ud_train_content,
        train_resid=ud_train_resid,
        train_labels=ud_train_labels["deprel_coarse"],
        eval_raw=ud_eval_raw,
        eval_pos=ud_eval_pos,
        eval_content=ud_eval_content,
        eval_resid=ud_eval_resid,
        eval_labels=ud_eval_labels["deprel_coarse"],
        min_examples_per_class=args.min_examples_per_class,
        train_source="UD_EWT_train",
        eval_source="UD_EWT_dev",
    )
    add_task(
        tasks,
        name="head_dir_dist_ud_ewt",
        family="syntax_dep_head_dir",
        metric_name="accuracy",
        train_raw=ud_train_raw,
        train_pos=ud_train_pos,
        train_content=ud_train_content,
        train_resid=ud_train_resid,
        train_labels=ud_train_labels["head_dir_dist"],
        eval_raw=ud_eval_raw,
        eval_pos=ud_eval_pos,
        eval_content=ud_eval_content,
        eval_resid=ud_eval_resid,
        eval_labels=ud_eval_labels["head_dir_dist"],
        min_examples_per_class=args.min_examples_per_class,
        train_source="UD_EWT_train",
        eval_source="UD_EWT_dev",
    )
    add_task(
        tasks,
        name="number_ud_ewt",
        family="syntax_morph",
        metric_name="accuracy",
        train_raw=ud_train_raw,
        train_pos=ud_train_pos,
        train_content=ud_train_content,
        train_resid=ud_train_resid,
        train_labels=ud_train_labels["number"],
        eval_raw=ud_eval_raw,
        eval_pos=ud_eval_pos,
        eval_content=ud_eval_content,
        eval_resid=ud_eval_resid,
        eval_labels=ud_eval_labels["number"],
        min_examples_per_class=args.min_examples_per_class,
        train_source="UD_EWT_train",
        eval_source="UD_EWT_dev",
    )

    semantic_specs = [
        ("wnut17", "WNUT17_train", "WNUT17_validation", wnut_train_raw, wnut_train_pos, wnut_train_content, wnut_train_resid, wnut_train_labels["ner"], wnut_eval_raw, wnut_eval_pos, wnut_eval_content, wnut_eval_resid, wnut_eval_labels["ner"]),
        ("fewnerd_coarse", "FewNERD_train", "FewNERD_validation", few_train_raw, few_train_pos, few_train_content, few_train_resid, few_train_labels["ner"], few_eval_raw, few_eval_pos, few_eval_content, few_eval_resid, few_eval_labels["ner"]),
        ("wikineural_en", "WikiNEuRal_train_en", "WikiNEuRal_val_en", wiki_train_raw, wiki_train_pos, wiki_train_content, wiki_train_resid, wiki_train_labels["ner"], wiki_eval_raw, wiki_eval_pos, wiki_eval_content, wiki_eval_resid, wiki_eval_labels["ner"]),
    ]
    for short_name, train_source, eval_source, tr_raw, tr_pos, tr_content, tr_resid, tr_labels, ev_raw, ev_pos, ev_content, ev_resid, ev_labels in semantic_specs:
        add_task(
            tasks,
            name=f"ner_{short_name}_typeonly",
            family=f"sem_{short_name}_typeonly",
            metric_name="macro_f1",
            train_raw=tr_raw,
            train_pos=tr_pos,
            train_content=tr_content,
            train_resid=tr_resid,
            train_labels=labels_typeonly(tr_labels),
            eval_raw=ev_raw,
            eval_pos=ev_pos,
            eval_content=ev_content,
            eval_resid=ev_resid,
            eval_labels=labels_typeonly(ev_labels),
            min_examples_per_class=args.min_examples_per_class,
            train_source=train_source,
            eval_source=eval_source,
        )
        add_task(
            tasks,
            name=f"ner_{short_name}_entity_binary",
            family=f"sem_{short_name}_binary",
            metric_name="macro_f1",
            train_raw=tr_raw,
            train_pos=tr_pos,
            train_content=tr_content,
            train_resid=tr_resid,
            train_labels=labels_entity_binary(tr_labels),
            eval_raw=ev_raw,
            eval_pos=ev_pos,
            eval_content=ev_content,
            eval_resid=ev_resid,
            eval_labels=labels_entity_binary(ev_labels),
            min_examples_per_class=args.min_examples_per_class,
            train_source=train_source,
            eval_source=eval_source,
        )

    rows: list[dict[str, Any]] = []
    summary_tasks: dict[str, Any] = {}
    for task in tasks:
        X_joint_train = np.concatenate([task.train_pos, task.train_content], axis=1).astype(np.float32)
        X_joint_eval = np.concatenate([task.eval_pos, task.eval_content], axis=1).astype(np.float32)
        reps = {
            "raw": (task.train_raw, task.eval_raw),
            "pos_priv": (task.train_pos, task.eval_pos),
            "content_priv": (task.train_content, task.eval_content),
            "joint": (X_joint_train, X_joint_eval),
            "resid_additive": (task.train_resid, task.eval_resid),
        }
        rep_results: dict[str, Any] = {}
        for rep_name, (Xtr, Xev) in reps.items():
            rep_results[rep_name] = run_probe_for_rep(
                X_train=Xtr,
                y_train=task.train_labels,
                X_eval=Xev,
                y_eval=task.eval_labels,
                probe_backend=probe_backend,
                probe_device=device,
                torch_cfg=torch_cfg,
                probe_name=f"{task.name}_{rep_name}",
                c_value=args.probe_c,
                out_dir=out_dir,
                metric_name=task.metric_name,
            )
            rows.append(
                {
                    "task": task.name,
                    "family": task.family,
                    "metric_name": task.metric_name,
                    "representation": rep_name,
                    "primary_metric": rep_results[rep_name]["primary_metric"],
                    "top1": rep_results[rep_name]["top1"],
                    "n_train": task.train_labels.shape[0],
                    "n_eval": task.eval_labels.shape[0],
                    "n_classes_train": int(np.unique(task.train_labels).shape[0]),
                    "train_source": task.train_source,
                    "eval_source": task.eval_source,
                }
            )
        best_private = max(rep_results["pos_priv"]["primary_metric"], rep_results["content_priv"]["primary_metric"])
        joint_metric = float(rep_results["joint"]["primary_metric"])
        resid_metric = float(rep_results["resid_additive"]["primary_metric"])
        summary_tasks[task.name] = {
            "family": task.family,
            "metric_name": task.metric_name,
            "n_train": int(task.train_labels.shape[0]),
            "n_eval": int(task.eval_labels.shape[0]),
            "n_classes_train": int(np.unique(task.train_labels).shape[0]),
            "label_names": task.label_names,
            "train_source": task.train_source,
            "eval_source": task.eval_source,
            "best_private_metric": float(best_private),
            "joint_gain": float(joint_metric - best_private),
            "resid_gain": float(resid_metric - best_private),
            "content_margin": float(rep_results["content_priv"]["primary_metric"] - rep_results["pos_priv"]["primary_metric"]),
            "raw_gap": float(rep_results["raw"]["primary_metric"] - joint_metric),
            "representations": rep_results,
        }

    family_rows = family_rows_from_tasks(summary_tasks)
    family_summary = {row["family"]: row for row in family_rows}
    summary = {
        "stage": "pcc_stage_a1b",
        "checkpoint_path": str(args.checkpoint_path),
        "model_name": args.model_name,
        "layer_index": int(args.layer_index),
        "seed": int(args.seed),
        "device": str(device),
        "dtype": str(dtype),
        "probe_backend": probe_backend,
        "git_commit_hash": git_hash,
        "checkpoint_git_commit_hash": str(ckpt.get("args", {}).get("git_commit_hash", "")),
        "checkpoint_tokens_seen": int(ckpt.get("tokens_seen", 0)),
        "checkpoint_step": int(ckpt.get("step", 0)),
        "extract_elapsed_sec": float(extract_elapsed),
        "tasks": summary_tasks,
        "families": family_summary,
        "notes": {
            "diagnostic_changes_vs_a1": [
                "BIO-collapsed entity-type labels for all NER datasets",
                "entity-vs-nonentity binary labels for all NER datasets",
                "deprel_coarse and head_dir_dist split into separate syntax families",
                "original Stage A1 selection regime preserved for comparability",
            ]
        },
        "ud_sources": {"train_url": UD_TRAIN_URL, "dev_url": UD_DEV_URL},
        "semantic_sources": {
            "wnut17": "flaitenberger/wnut_17",
            "fewnerd": "DFKI-SLT/few-nerd:supervised",
            "wikineural_en": "Babelscape/wikineural",
        },
        "args": vars(args),
    }

    with open(out_dir / "pcc_stage_a1b_summary.json", "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)
    write_tsv(out_dir / "pcc_stage_a1b_metrics.tsv", rows)
    write_tsv(out_dir / "pcc_stage_a1b_family_summary.tsv", family_rows)
    print(
        json.dumps(
            {
                "output_dir": str(out_dir),
                "summary": str(out_dir / "pcc_stage_a1b_summary.json"),
                "metrics_tsv": str(out_dir / "pcc_stage_a1b_metrics.tsv"),
                "family_tsv": str(out_dir / "pcc_stage_a1b_family_summary.tsv"),
                "task_joint_gains": {k: v["joint_gain"] for k, v in summary_tasks.items()},
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
