#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import time
from collections import defaultdict
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import numpy as np
import torch
from sklearn.metrics import accuracy_score, f1_score
from transformers import AutoModelForCausalLM, AutoTokenizer

from pcc_stage_a1_audit import (
    DROP_LABEL,
    TaskDataset,
    UD_DEV_URL,
    UD_TRAIN_URL,
    family_rows_from_tasks,
    infer_d_model,
    load_fewnerd_examples,
    load_msae_from_checkpoint,
    load_wikineural_examples,
    load_wnut_examples,
    parse_conllu,
    prepare_task_dataset,
    resolve_git_commit_hash,
    set_seed,
    write_tsv,
)
from pcc_stage_a1c_confirmation import (
    add_task,
    clone_cfg,
    labels_entity_binary,
    labels_typeonly,
    run_probe_for_rep_a1c,
)
from raw_activation_separability_pilot import TorchProbeConfig, choose_device, choose_probe_backend
from train_msae_k2 import K2MSAE, choose_dtype, resolve_hidden_state_index


@dataclass
class ExtractedTokenData:
    raw: np.ndarray
    pos: np.ndarray
    content: np.ndarray
    resid: np.ndarray
    labels_by_key: dict[str, np.ndarray]
    meta: dict[str, np.ndarray]


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Stage B-light PCC control audit on existing K=2 checkpoints")
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
    p.add_argument("--probe_backend", type=str, default="torch", choices=["auto", "sklearn", "torch"])
    p.add_argument("--probe_c", type=float, default=0.2)
    p.add_argument("--probe_torch_max_steps", type=int, default=1200)
    p.add_argument("--probe_torch_max_steps_semantic", type=int, default=2200)
    p.add_argument("--probe_torch_batch_size", type=int, default=8192)
    p.add_argument("--probe_torch_lr", type=float, default=0.02)
    p.add_argument("--probe_torch_scheduler", type=str, default="cosine", choices=["none", "cosine"])
    p.add_argument("--probe_torch_weight_decay", type=float, default=-1.0)
    p.add_argument("--probe_torch_eval_every", type=int, default=50)
    p.add_argument("--probe_torch_patience", type=int, default=300)
    p.add_argument("--probe_torch_patience_semantic", type=int, default=500)
    p.add_argument("--probe_torch_min_steps", type=int, default=200)
    p.add_argument("--probe_torch_min_steps_semantic", type=int, default=300)
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


def position_bucket(word_idx: int) -> str:
    if word_idx <= 0:
        return "P0"
    if word_idx == 1:
        return "P1"
    if word_idx == 2:
        return "P2"
    if 3 <= word_idx <= 4:
        return "P3_4"
    if 5 <= word_idx <= 7:
        return "P5_7"
    if 8 <= word_idx <= 15:
        return "P8_15"
    return "P16p"


def load_wnut_examples_with_lower(split: str, max_sentences: int) -> list[dict[str, Any]]:
    examples = load_wnut_examples(split, max_sentences)
    for ex in examples:
        ex["word_lower"] = [str(w).lower() for w in ex["words"]]
    return examples


def load_fewnerd_examples_with_lower(split: str, max_sentences: int) -> list[dict[str, Any]]:
    examples = load_fewnerd_examples(split, max_sentences)
    for ex in examples:
        ex["word_lower"] = [str(w).lower() for w in ex["words"]]
    return examples


def load_wikineural_examples_with_lower(split: str, max_sentences: int) -> list[dict[str, Any]]:
    examples = load_wikineural_examples(split, max_sentences)
    for ex in examples:
        ex["word_lower"] = [str(w).lower() for w in ex["words"]]
    return examples


def extract_features_labels_meta(
    examples: list[dict[str, Any]],
    label_keys: list[str],
    model_lm: AutoModelForCausalLM,
    tokenizer: AutoTokenizer,
    msae: K2MSAE,
    device: torch.device,
    layer_index: int,
    context_length: int,
    model_batch_size: int,
) -> ExtractedTokenData:
    xs_raw: list[np.ndarray] = []
    xs_pos: list[np.ndarray] = []
    xs_content: list[np.ndarray] = []
    xs_resid: list[np.ndarray] = []
    labels_by_key: dict[str, list[str]] = {k: [] for k in label_keys}
    meta: dict[str, list[str]] = {"word_lower": [], "position_bucket": []}
    hs_idx: int | None = None

    for s in range(0, len(examples), model_batch_size):
        batch = examples[s : s + model_batch_size]
        batch_words = [ex["words"] for ex in batch]
        enc = tokenizer(
            batch_words,
            is_split_into_words=True,
            return_tensors="pt",
            truncation=True,
            padding=True,
            max_length=context_length,
        )
        input_ids = enc["input_ids"].to(device)
        attention_mask = enc["attention_mask"].to(device)
        with torch.no_grad():
            out = model_lm(
                input_ids=input_ids,
                attention_mask=attention_mask,
                output_hidden_states=True,
                use_cache=False,
            )
        if hs_idx is None:
            hs_idx = resolve_hidden_state_index(layer_index, len(out.hidden_states))
        h = out.hidden_states[hs_idx].detach().float()

        batch_token_rows: list[torch.Tensor] = []
        batch_meta: list[tuple[int, int]] = []
        for bi, ex in enumerate(batch):
            word_ids = enc.word_ids(batch_index=bi)
            seen: set[int] = set()
            for ti, wi in enumerate(word_ids):
                if wi is None or wi in seen:
                    continue
                seen.add(wi)
                if any(wi >= len(ex[k]) for k in label_keys):
                    continue
                batch_token_rows.append(h[bi, ti])
                batch_meta.append((bi, wi))
        if not batch_token_rows:
            continue
        x_batch = torch.stack(batch_token_rows, dim=0).to(device)
        with torch.no_grad():
            out_b = msae(x_batch)
        raw_np = x_batch.detach().cpu().numpy().astype(np.float32)
        pos_np = out_b["recon_pos"].detach().cpu().numpy().astype(np.float32)
        content_np = out_b["recon_content"].detach().cpu().numpy().astype(np.float32)
        resid_np = (raw_np - pos_np - content_np).astype(np.float32)
        xs_raw.append(raw_np)
        xs_pos.append(pos_np)
        xs_content.append(content_np)
        xs_resid.append(resid_np)
        for bi, wi in batch_meta:
            ex = batch[bi]
            for k in label_keys:
                labels_by_key[k].append(str(ex[k][wi]))
            meta["word_lower"].append(str(ex.get("word_lower", ex["words"])[wi]).lower())
            meta["position_bucket"].append(position_bucket(int(wi)))

    if not xs_raw:
        raise RuntimeError(f"No features extracted for label_keys={label_keys}")

    return ExtractedTokenData(
        raw=np.concatenate(xs_raw, axis=0),
        pos=np.concatenate(xs_pos, axis=0),
        content=np.concatenate(xs_content, axis=0),
        resid=np.concatenate(xs_resid, axis=0),
        labels_by_key={k: np.asarray(v, dtype=object) for k, v in labels_by_key.items()},
        meta={k: np.asarray(v, dtype=object) for k, v in meta.items()},
    )


def ambiguous_value_set(values: np.ndarray, labels: np.ndarray) -> set[str]:
    table: dict[str, set[str]] = defaultdict(set)
    for value, label in zip(values.tolist(), labels.tolist()):
        label_s = str(label)
        if label_s == DROP_LABEL:
            continue
        table[str(value)].add(label_s)
    return {value for value, lbls in table.items() if len(lbls) > 1}


def filter_labels_by_allowed_values(labels: np.ndarray, values: np.ndarray, allowed: set[str]) -> np.ndarray:
    return np.asarray([
        str(lbl) if str(value) in allowed else DROP_LABEL
        for lbl, value in zip(labels.tolist(), values.tolist())
    ], dtype=object)


@dataclass
class ControlTaskSpec:
    name: str
    family: str
    base_family: str
    control_type: str
    metric_name: str
    train_raw: np.ndarray
    train_pos: np.ndarray
    train_content: np.ndarray
    train_resid: np.ndarray
    train_labels: np.ndarray
    eval_raw: np.ndarray
    eval_pos: np.ndarray
    eval_content: np.ndarray
    eval_resid: np.ndarray
    eval_labels: np.ndarray
    train_source: str
    eval_source: str


def make_control_spec(
    *,
    name: str,
    family: str,
    base_family: str,
    control_type: str,
    metric_name: str,
    train: ExtractedTokenData,
    eval_: ExtractedTokenData,
    label_key: str,
    train_labels: np.ndarray,
    eval_labels: np.ndarray,
    train_source: str,
    eval_source: str,
) -> ControlTaskSpec:
    return ControlTaskSpec(
        name=name,
        family=family,
        base_family=base_family,
        control_type=control_type,
        metric_name=metric_name,
        train_raw=train.raw,
        train_pos=train.pos,
        train_content=train.content,
        train_resid=train.resid,
        train_labels=train_labels,
        eval_raw=eval_.raw,
        eval_pos=eval_.pos,
        eval_content=eval_.content,
        eval_resid=eval_.resid,
        eval_labels=eval_labels,
        train_source=train_source,
        eval_source=eval_source,
    )


def main() -> None:
    args = parse_args()
    set_seed(args.seed)
    device = choose_device(args.device)
    dtype = choose_dtype(args.dtype)
    probe_backend = choose_probe_backend(args.probe_backend, device)
    if probe_backend != "torch":
        raise SystemExit("Stage B-light currently requires probe_backend=torch")

    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "probe_logs").mkdir(parents=True, exist_ok=True)
    cache_dir = Path(args.cache_dir) if args.cache_dir else (out_dir / "cache")
    cache_dir.mkdir(parents=True, exist_ok=True)
    git_hash = resolve_git_commit_hash(args.git_commit_hash)

    from pcc_stage_a1_audit import ensure_download  # local import to keep startup lighter

    ud_train_path = ensure_download(UD_TRAIN_URL, cache_dir / "ud" / "en_ewt-ud-train.conllu")
    ud_dev_path = ensure_download(UD_DEV_URL, cache_dir / "ud" / "en_ewt-ud-dev.conllu")
    ud_train = parse_conllu(ud_train_path, args.max_train_sentences_ud)
    ud_dev = parse_conllu(ud_dev_path, args.max_eval_sentences_ud)

    wnut_train = load_wnut_examples_with_lower("train", args.max_train_sentences_wnut)
    wnut_eval = load_wnut_examples_with_lower("validation", args.max_eval_sentences_wnut)
    fewnerd_train = load_fewnerd_examples_with_lower("train", args.max_train_sentences_fewnerd)
    fewnerd_eval = load_fewnerd_examples_with_lower("validation", args.max_eval_sentences_fewnerd)
    wikineural_train = load_wikineural_examples_with_lower("train_en", args.max_train_sentences_wikineural)
    wikineural_eval = load_wikineural_examples_with_lower("val_en", args.max_eval_sentences_wikineural)

    tokenizer = AutoTokenizer.from_pretrained(args.model_name, use_fast=True)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token
    model_lm = AutoModelForCausalLM.from_pretrained(args.model_name, torch_dtype=dtype, low_cpu_mem_usage=True).to(device)
    model_lm.eval()
    model_lm.config.use_cache = False

    d_model = infer_d_model(model_lm, tokenizer, device, args.layer_index)
    msae, ckpt = load_msae_from_checkpoint(Path(args.checkpoint_path), device, d_model)

    torch_cfg_base = TorchProbeConfig(
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
    torch_cfg_semantic = clone_cfg(
        torch_cfg_base,
        max_steps=int(args.probe_torch_max_steps_semantic),
        patience=int(args.probe_torch_patience_semantic),
        min_steps=int(args.probe_torch_min_steps_semantic),
    )

    t0 = time.time()
    ud_train_data = extract_features_labels_meta(
        ud_train,
        ["pos", "deprel_coarse", "head_dir_dist", "number"],
        model_lm,
        tokenizer,
        msae,
        device,
        args.layer_index,
        args.context_length,
        args.model_batch_size,
    )
    ud_eval_data = extract_features_labels_meta(
        ud_dev,
        ["pos", "deprel_coarse", "head_dir_dist", "number"],
        model_lm,
        tokenizer,
        msae,
        device,
        args.layer_index,
        args.context_length,
        args.model_batch_size,
    )
    wnut_train_data = extract_features_labels_meta(
        wnut_train, ["ner"], model_lm, tokenizer, msae, device, args.layer_index, args.context_length, args.model_batch_size
    )
    wnut_eval_data = extract_features_labels_meta(
        wnut_eval, ["ner"], model_lm, tokenizer, msae, device, args.layer_index, args.context_length, args.model_batch_size
    )
    few_train_data = extract_features_labels_meta(
        fewnerd_train, ["ner"], model_lm, tokenizer, msae, device, args.layer_index, args.context_length, args.model_batch_size
    )
    few_eval_data = extract_features_labels_meta(
        fewnerd_eval, ["ner"], model_lm, tokenizer, msae, device, args.layer_index, args.context_length, args.model_batch_size
    )
    wiki_train_data = extract_features_labels_meta(
        wikineural_train, ["ner"], model_lm, tokenizer, msae, device, args.layer_index, args.context_length, args.model_batch_size
    )
    wiki_eval_data = extract_features_labels_meta(
        wikineural_eval, ["ner"], model_lm, tokenizer, msae, device, args.layer_index, args.context_length, args.model_batch_size
    )
    extract_elapsed = time.time() - t0

    pos_train = ud_train_data.labels_by_key["pos"]
    pos_eval = ud_eval_data.labels_by_key["pos"]
    dep_train = ud_train_data.labels_by_key["deprel_coarse"]
    dep_eval = ud_eval_data.labels_by_key["deprel_coarse"]
    head_train = ud_train_data.labels_by_key["head_dir_dist"]
    head_eval = ud_eval_data.labels_by_key["head_dir_dist"]
    num_train = ud_train_data.labels_by_key["number"]
    num_eval = ud_eval_data.labels_by_key["number"]

    wnut_type_train = labels_typeonly(wnut_train_data.labels_by_key["ner"])
    wnut_type_eval = labels_typeonly(wnut_eval_data.labels_by_key["ner"])
    few_bin_train = labels_entity_binary(few_train_data.labels_by_key["ner"])
    few_bin_eval = labels_entity_binary(few_eval_data.labels_by_key["ner"])
    wiki_bin_train = labels_entity_binary(wiki_train_data.labels_by_key["ner"])
    wiki_bin_eval = labels_entity_binary(wiki_eval_data.labels_by_key["ner"])

    pos_word_allowed = ambiguous_value_set(ud_train_data.meta["word_lower"], pos_train)
    pos_pos_allowed = ambiguous_value_set(ud_train_data.meta["position_bucket"], pos_train)
    dep_word_allowed = ambiguous_value_set(ud_train_data.meta["word_lower"], dep_train)
    dep_pos_allowed = ambiguous_value_set(ud_train_data.meta["position_bucket"], dep_train)
    wnut_word_allowed = ambiguous_value_set(wnut_train_data.meta["word_lower"], wnut_type_train)
    wnut_pos_allowed = ambiguous_value_set(wnut_train_data.meta["position_bucket"], wnut_type_train)
    few_word_allowed = ambiguous_value_set(few_train_data.meta["word_lower"], few_bin_train)
    few_pos_allowed = ambiguous_value_set(few_train_data.meta["position_bucket"], few_bin_train)
    wiki_word_allowed = ambiguous_value_set(wiki_train_data.meta["word_lower"], wiki_bin_train)
    wiki_pos_allowed = ambiguous_value_set(wiki_train_data.meta["position_bucket"], wiki_bin_train)

    specs: list[ControlTaskSpec] = []

    def add_control_triplet(base_name: str, base_family: str, metric_name: str, train_data: ExtractedTokenData, eval_data: ExtractedTokenData, train_labels: np.ndarray, eval_labels: np.ndarray, word_allowed: set[str], pos_allowed: set[str], train_source: str, eval_source: str) -> None:
        specs.append(make_control_spec(name=f"{base_name}", family=f"{base_family}_full", base_family=base_family, control_type="full", metric_name=metric_name, train=train_data, eval_=eval_data, label_key="", train_labels=train_labels, eval_labels=eval_labels, train_source=train_source, eval_source=eval_source))
        specs.append(make_control_spec(name=f"{base_name}_tokenctrl", family=f"{base_family}_tokenctrl", base_family=base_family, control_type="tokenctrl", metric_name=metric_name, train=train_data, eval_=eval_data, label_key="", train_labels=filter_labels_by_allowed_values(train_labels, train_data.meta["word_lower"], word_allowed), eval_labels=filter_labels_by_allowed_values(eval_labels, eval_data.meta["word_lower"], word_allowed), train_source=train_source, eval_source=eval_source))
        specs.append(make_control_spec(name=f"{base_name}_posctrl", family=f"{base_family}_posctrl", base_family=base_family, control_type="posctrl", metric_name=metric_name, train=train_data, eval_=eval_data, label_key="", train_labels=filter_labels_by_allowed_values(train_labels, train_data.meta["position_bucket"], pos_allowed), eval_labels=filter_labels_by_allowed_values(eval_labels, eval_data.meta["position_bucket"], pos_allowed), train_source=train_source, eval_source=eval_source))

    add_control_triplet("pos_ud_ewt", "syntax_pos", "accuracy", ud_train_data, ud_eval_data, pos_train, pos_eval, pos_word_allowed, pos_pos_allowed, "UD_EWT_train", "UD_EWT_dev")
    add_control_triplet("deprel_coarse_ud_ewt", "syntax_dep_coarse", "accuracy", ud_train_data, ud_eval_data, dep_train, dep_eval, dep_word_allowed, dep_pos_allowed, "UD_EWT_train", "UD_EWT_dev")
    # exploratory head-direction task: full only
    specs.append(make_control_spec(name="head_dir_dist_ud_ewt", family="syntax_dep_head_dir_full", base_family="syntax_dep_head_dir", control_type="full", metric_name="accuracy", train=ud_train_data, eval_=ud_eval_data, label_key="", train_labels=head_train, eval_labels=head_eval, train_source="UD_EWT_train", eval_source="UD_EWT_dev"))
    specs.append(make_control_spec(name="number_ud_ewt", family="syntax_morph_full", base_family="syntax_morph", control_type="full", metric_name="accuracy", train=ud_train_data, eval_=ud_eval_data, label_key="", train_labels=num_train, eval_labels=num_eval, train_source="UD_EWT_train", eval_source="UD_EWT_dev"))
    add_control_triplet("ner_wnut17_typeonly", "sem_wnut17_typeonly", "macro_f1", wnut_train_data, wnut_eval_data, wnut_type_train, wnut_type_eval, wnut_word_allowed, wnut_pos_allowed, "WNUT17_train", "WNUT17_validation")
    add_control_triplet("ner_fewnerd_coarse_binary", "sem_fewnerd_coarse_binary", "macro_f1", few_train_data, few_eval_data, few_bin_train, few_bin_eval, few_word_allowed, few_pos_allowed, "FewNERD_train", "FewNERD_validation")
    add_control_triplet("ner_wikineural_en_binary", "sem_wikineural_en_binary", "macro_f1", wiki_train_data, wiki_eval_data, wiki_bin_train, wiki_bin_eval, wiki_word_allowed, wiki_pos_allowed, "WikiNEuRal_train_en", "WikiNEuRal_val_en")

    tasks: list[TaskDataset] = []
    task_meta: dict[str, dict[str, str]] = {}
    for spec in specs:
        add_task(
            tasks,
            name=spec.name,
            family=spec.family,
            metric_name=spec.metric_name,
            train_raw=spec.train_raw,
            train_pos=spec.train_pos,
            train_content=spec.train_content,
            train_resid=spec.train_resid,
            train_labels=spec.train_labels,
            eval_raw=spec.eval_raw,
            eval_pos=spec.eval_pos,
            eval_content=spec.eval_content,
            eval_resid=spec.eval_resid,
            eval_labels=spec.eval_labels,
            min_examples_per_class=args.min_examples_per_class,
            train_source=spec.train_source,
            eval_source=spec.eval_source,
        )
        task_meta[spec.name] = {"base_family": spec.base_family, "control_type": spec.control_type}

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
        cfg = torch_cfg_semantic if task.metric_name == "macro_f1" else torch_cfg_base
        for rep_name, (Xtr, Xev) in reps.items():
            rep_results[rep_name] = run_probe_for_rep_a1c(
                X_train=Xtr,
                y_train=task.train_labels,
                X_eval=Xev,
                y_eval=task.eval_labels,
                probe_backend=probe_backend,
                probe_device=device,
                torch_cfg=cfg,
                probe_name=f"{task.name}_{rep_name}",
                c_value=args.probe_c,
                out_dir=out_dir,
                metric_name=task.metric_name,
            )
            rows.append(
                {
                    "task": task.name,
                    "family": task.family,
                    "base_family": task_meta[task.name]["base_family"],
                    "control_type": task_meta[task.name]["control_type"],
                    "metric_name": task.metric_name,
                    "representation": rep_name,
                    "primary_metric": rep_results[rep_name]["primary_metric"],
                    "top1": rep_results[rep_name]["top1"],
                    "selection_metric_name": rep_results[rep_name]["diagnostics"].get("selection_metric_name", task.metric_name),
                    "best_eval_primary_metric": rep_results[rep_name]["diagnostics"].get("best_eval_primary_metric", float("nan")),
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
            "base_family": task_meta[task.name]["base_family"],
            "control_type": task_meta[task.name]["control_type"],
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
        "stage": "pcc_stage_b_light_controls",
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
            "stage_b_light_scope": [
                "matched-token controls",
                "coarse matched-position controls via sentence position buckets",
                "residual-vs-joint comparisons",
                "regularizer sensitivity to be aggregated across g4/g5/g6/g7",
            ],
            "not_included_yet": [
                "curated contrast-set pack",
                "new PCC branch training",
                "new checkpoints",
            ],
        },
        "args": vars(args),
    }

    with open(out_dir / "pcc_stage_b_light_summary.json", "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)
    write_tsv(out_dir / "pcc_stage_b_light_metrics.tsv", rows)
    write_tsv(out_dir / "pcc_stage_b_light_family_summary.tsv", family_rows)
    print(json.dumps({
        "output_dir": str(out_dir),
        "summary": str(out_dir / "pcc_stage_b_light_summary.json"),
        "metrics_tsv": str(out_dir / "pcc_stage_b_light_metrics.tsv"),
        "family_tsv": str(out_dir / "pcc_stage_b_light_family_summary.tsv"),
        "task_joint_gains": {k: v["joint_gain"] for k, v in summary_tasks.items()},
    }, indent=2))


if __name__ == "__main__":
    main()
