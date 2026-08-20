#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
import os
import random
import subprocess
import time
import urllib.request
from collections import Counter
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import numpy as np
import torch
from datasets import load_dataset
from sklearn.metrics import accuracy_score, f1_score
from transformers import AutoModelForCausalLM, AutoTokenizer

from raw_activation_separability_pilot import (
    TorchProbeConfig,
    choose_device,
    choose_probe_backend,
    train_eval_probe,
)
from train_msae_k2 import K2MSAE, choose_dtype, resolve_hidden_state_index

UD_TRAIN_URL = "https://raw.githubusercontent.com/UniversalDependencies/UD_English-EWT/master/en_ewt-ud-train.conllu"
UD_DEV_URL = "https://raw.githubusercontent.com/UniversalDependencies/UD_English-EWT/master/en_ewt-ud-dev.conllu"


@dataclass
class TaskResult:
    task_name: str
    metric_name: str
    n_train: int
    n_eval: int
    n_classes_train: int
    best_private_metric: float
    joint_metric: float
    joint_gain: float
    raw_metric: float
    pos_priv_metric: float
    content_priv_metric: float


@dataclass
class TaskDataset:
    name: str
    metric_name: str
    label_names: list[str]
    train_raw: np.ndarray
    train_pos: np.ndarray
    train_content: np.ndarray
    train_labels: np.ndarray
    eval_raw: np.ndarray
    eval_pos: np.ndarray
    eval_content: np.ndarray
    eval_labels: np.ndarray
    train_source: str
    eval_source: str


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Stage A0 PCC audit on existing K=2 checkpoints")
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
    p.add_argument("--cache_dir", type=str, default="")
    return p.parse_args()


def set_seed(seed: int) -> None:
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)


def resolve_git_commit_hash(arg_hash: str) -> str:
    if arg_hash:
        return arg_hash
    try:
        return (
            subprocess.check_output(["git", "rev-parse", "HEAD"], stderr=subprocess.DEVNULL, text=True)
            .strip()
        )
    except Exception:
        return ""


def ensure_download(url: str, dst: Path) -> Path:
    dst.parent.mkdir(parents=True, exist_ok=True)
    if dst.exists() and dst.stat().st_size > 0:
        return dst
    with urllib.request.urlopen(url, timeout=60) as r, open(dst, "wb") as f:
        f.write(r.read())
    return dst


def parse_conllu(path: Path, max_sentences: int) -> list[dict[str, Any]]:
    examples: list[dict[str, Any]] = []
    words: list[str] = []
    upos: list[str] = []
    deprel: list[str] = []
    feats_number: list[str] = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.rstrip("\n")
            if not line:
                if words:
                    examples.append(
                        {
                            "words": words,
                            "pos": upos,
                            "deprel": deprel,
                            "number": feats_number,
                        }
                    )
                    if len(examples) >= max_sentences:
                        break
                words, upos, deprel, feats_number = [], [], [], []
                continue
            if line.startswith("#"):
                continue
            parts = line.split("\t")
            if len(parts) != 10:
                continue
            tok_id = parts[0]
            if "-" in tok_id or "." in tok_id:
                continue
            form = parts[1]
            pos = parts[3]
            dep = parts[7]
            feats = parts[5]
            num = "None"
            if feats and feats != "_":
                for feat in feats.split("|"):
                    if feat.startswith("Number="):
                        num = feat.split("=", 1)[1]
                        break
            words.append(form)
            upos.append(pos)
            deprel.append(dep)
            feats_number.append(num)
    return examples


def load_wnut_examples(split: str, max_sentences: int) -> tuple[list[dict[str, Any]], list[str]]:
    ds = load_dataset("flaitenberger/wnut_17", split=split)
    label_names = ds.features["ner_tags"].feature.names
    examples: list[dict[str, Any]] = []
    for row in ds:
        tokens = [str(t) for t in row["tokens"]]
        ner_labels = [label_names[int(x)] for x in row["ner_tags"]]
        if tokens:
            examples.append({"words": tokens, "ner": ner_labels})
        if len(examples) >= max_sentences:
            break
    return examples, list(label_names)


def filter_train_labels(
    train_labels: np.ndarray,
    eval_labels: np.ndarray,
    min_examples_per_class: int,
) -> tuple[np.ndarray, np.ndarray, list[str]]:
    counts = Counter(train_labels.tolist())
    keep = {lbl for lbl, c in counts.items() if c >= min_examples_per_class}
    train_mask = np.array([lbl in keep for lbl in train_labels.tolist()], dtype=bool)
    eval_mask = np.array([lbl in keep for lbl in eval_labels.tolist()], dtype=bool)
    kept = sorted(keep)
    return train_mask, eval_mask, kept


def predict_labels_from_weights(weights, X_eval: np.ndarray, y_train: np.ndarray, y_eval: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    uniq = np.unique(y_train)
    mapping = {int(v): i for i, v in enumerate(uniq.tolist())}
    mask = np.array([int(v) in mapping for v in y_eval.tolist()], dtype=bool)
    if not np.any(mask):
        return np.zeros((0,), dtype=np.int64), np.zeros((0,), dtype=np.int64)
    y_eval_remap = np.array([mapping[int(v)] for v in y_eval[mask].tolist()], dtype=np.int64)
    mu = weights.mu if weights.mu is not None else np.zeros((weights.coef.shape[1],), dtype=np.float64)
    sigma = weights.sigma if weights.sigma is not None else np.ones((weights.coef.shape[1],), dtype=np.float64)
    Xn = (X_eval[mask].astype(np.float64) - mu.reshape(1, -1)) / (sigma.reshape(1, -1) + 1e-6)
    logits = Xn @ weights.coef.T + weights.intercept.reshape(1, -1)
    pred = np.argmax(logits, axis=1).astype(np.int64)
    return pred, y_eval_remap


def metric_from_predictions(metric_name: str, pred: np.ndarray, gold: np.ndarray) -> float:
    if pred.shape[0] == 0:
        return float("nan")
    if metric_name == "accuracy":
        return float(accuracy_score(gold, pred))
    if metric_name == "macro_f1":
        return float(f1_score(gold, pred, average="macro"))
    raise ValueError(f"unsupported metric_name={metric_name}")


def load_checkpoint_model(checkpoint_path: Path, device: torch.device) -> tuple[K2MSAE, dict[str, Any]]:
    ckpt = torch.load(checkpoint_path, map_location="cpu", weights_only=False)
    args = ckpt["args"]
    model = K2MSAE(
        d_model=int(args.get("d_model", 768)) if "d_model" in args else 768,
        m_pos=int(args["m_pos"]),
        k_pos=int(args["k_pos"]),
        m_content=int(args["m_content"]),
        k_content=int(args["k_content"]),
    ).to(device)
    model.load_state_dict(ckpt["model"])
    model.eval()
    return model, ckpt


def infer_d_model(model_lm, tokenizer, device, layer_index: int) -> int:
    enc = tokenizer(["hello world"], return_tensors="pt", padding=True, truncation=True, max_length=8)
    with torch.no_grad():
        out = model_lm(
            input_ids=enc["input_ids"].to(device),
            attention_mask=enc["attention_mask"].to(device),
            output_hidden_states=True,
            use_cache=False,
        )
    hs_idx = resolve_hidden_state_index(layer_index, len(out.hidden_states))
    return int(out.hidden_states[hs_idx].shape[-1])


def load_msae_from_checkpoint(checkpoint_path: Path, device: torch.device, d_model: int) -> tuple[K2MSAE, dict[str, Any]]:
    ckpt = torch.load(checkpoint_path, map_location="cpu", weights_only=False)
    args = ckpt["args"]
    model = K2MSAE(
        d_model=d_model,
        m_pos=int(args["m_pos"]),
        k_pos=int(args["k_pos"]),
        m_content=int(args["m_content"]),
        k_content=int(args["k_content"]),
    ).to(device)
    model.load_state_dict(ckpt["model"])
    model.eval()
    return model, ckpt


def extract_features_and_labels(
    examples: list[dict[str, Any]],
    label_keys: list[str],
    model_lm: AutoModelForCausalLM,
    tokenizer: AutoTokenizer,
    msae: K2MSAE,
    device: torch.device,
    layer_index: int,
    context_length: int,
    model_batch_size: int,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, dict[str, np.ndarray]]:
    xs_raw: list[np.ndarray] = []
    xs_pos: list[np.ndarray] = []
    xs_content: list[np.ndarray] = []
    labels_by_key: dict[str, list[str]] = {k: [] for k in label_keys}
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

        # Gather first-subtoken token positions only.
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
        xs_raw.append(raw_np)
        xs_pos.append(pos_np)
        xs_content.append(content_np)
        for bi, wi in batch_meta:
            ex = batch[bi]
            for k in label_keys:
                labels_by_key[k].append(str(ex[k][wi]))

    if not xs_raw:
        raise RuntimeError(f"No features extracted for label_keys={label_keys}")
    return (
        np.concatenate(xs_raw, axis=0),
        np.concatenate(xs_pos, axis=0),
        np.concatenate(xs_content, axis=0),
        {k: np.asarray(v, dtype=object) for k, v in labels_by_key.items()},
    )


def prepare_task_dataset(
    name: str,
    metric_name: str,
    train_raw: np.ndarray,
    train_pos: np.ndarray,
    train_content: np.ndarray,
    train_labels_obj: np.ndarray,
    eval_raw: np.ndarray,
    eval_pos: np.ndarray,
    eval_content: np.ndarray,
    eval_labels_obj: np.ndarray,
    min_examples_per_class: int,
    train_source: str,
    eval_source: str,
) -> TaskDataset:
    label_to_id = {lbl: i for i, lbl in enumerate(sorted(set(train_labels_obj.tolist()) | set(eval_labels_obj.tolist())))}
    train_labels = np.asarray([label_to_id[x] for x in train_labels_obj.tolist()], dtype=np.int64)
    eval_labels = np.asarray([label_to_id[x] for x in eval_labels_obj.tolist()], dtype=np.int64)
    train_mask, eval_mask, kept = filter_train_labels(train_labels, eval_labels, min_examples_per_class)
    train_labels = train_labels[train_mask]
    eval_labels = eval_labels[eval_mask]
    inv = {v: k for k, v in label_to_id.items()}
    label_names = [str(inv[k]) for k in kept]
    return TaskDataset(
        name=name,
        metric_name=metric_name,
        label_names=label_names,
        train_raw=train_raw[train_mask],
        train_pos=train_pos[train_mask],
        train_content=train_content[train_mask],
        train_labels=train_labels,
        eval_raw=eval_raw[eval_mask],
        eval_pos=eval_pos[eval_mask],
        eval_content=eval_content[eval_mask],
        eval_labels=eval_labels,
        train_source=train_source,
        eval_source=eval_source,
    )


def run_probe_for_rep(
    X_train: np.ndarray,
    y_train: np.ndarray,
    X_eval: np.ndarray,
    y_eval: np.ndarray,
    probe_backend: str,
    probe_device: torch.device,
    torch_cfg: TorchProbeConfig,
    probe_name: str,
    c_value: float,
    out_dir: Path,
    metric_name: str,
) -> dict[str, Any]:
    metrics, weights, diag = train_eval_probe(
        X=X_train,
        y=y_train,
        train_frac=1.0,
        seed=42,
        max_iter=200,
        c_value=c_value,
        probe_backend=probe_backend,
        probe_device=probe_device,
        torch_cfg=torch_cfg,
        probe_name=probe_name,
        intermediates_dir=str(out_dir / "probe_logs"),
        eval_override=(X_eval, y_eval),
    )
    pred, gold = predict_labels_from_weights(weights, X_eval, y_train, y_eval)
    primary_metric = metric_from_predictions(metric_name, pred, gold)
    out = {
        "primary_metric": primary_metric,
        "metric_name": metric_name,
        "top1": float(metrics.top1),
        "auc_ovo_macro": float(metrics.auc_ovo_macro),
        "n_classes": int(metrics.n_classes),
        "n_train": int(metrics.n_train),
        "n_test": int(metrics.n_test),
        "diagnostics": asdict(diag),
    }
    return out


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
    wnut_train, wnut_label_names = load_wnut_examples("train", args.max_train_sentences_wnut)
    wnut_dev, _ = load_wnut_examples("validation", args.max_eval_sentences_wnut)

    tokenizer = AutoTokenizer.from_pretrained(args.model_name, use_fast=True)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token

    model_lm = AutoModelForCausalLM.from_pretrained(
        args.model_name,
        torch_dtype=dtype,
        low_cpu_mem_usage=True,
    ).to(device)
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
    ud_train_raw, ud_train_pos, ud_train_content, ud_train_labels = extract_features_and_labels(
        ud_train,
        ["pos", "deprel"],
        model_lm,
        tokenizer,
        msae,
        device,
        args.layer_index,
        args.context_length,
        args.model_batch_size,
    )
    ud_eval_raw, ud_eval_pos, ud_eval_content, ud_eval_labels = extract_features_and_labels(
        ud_dev,
        ["pos", "deprel"],
        model_lm,
        tokenizer,
        msae,
        device,
        args.layer_index,
        args.context_length,
        args.model_batch_size,
    )
    wnut_train_raw, wnut_train_pos, wnut_train_content, wnut_train_labels = extract_features_and_labels(
        wnut_train,
        ["ner"],
        model_lm,
        tokenizer,
        msae,
        device,
        args.layer_index,
        args.context_length,
        args.model_batch_size,
    )
    wnut_eval_raw, wnut_eval_pos, wnut_eval_content, wnut_eval_labels = extract_features_and_labels(
        wnut_dev,
        ["ner"],
        model_lm,
        tokenizer,
        msae,
        device,
        args.layer_index,
        args.context_length,
        args.model_batch_size,
    )
    extract_elapsed = time.time() - t0

    tasks = [
        prepare_task_dataset(
            name="pos_ud_ewt",
            metric_name="accuracy",
            train_raw=ud_train_raw,
            train_pos=ud_train_pos,
            train_content=ud_train_content,
            train_labels_obj=ud_train_labels["pos"],
            eval_raw=ud_eval_raw,
            eval_pos=ud_eval_pos,
            eval_content=ud_eval_content,
            eval_labels_obj=ud_eval_labels["pos"],
            min_examples_per_class=args.min_examples_per_class,
            train_source="UD_EWT_train",
            eval_source="UD_EWT_dev",
        ),
        prepare_task_dataset(
            name="deprel_ud_ewt",
            metric_name="accuracy",
            train_raw=ud_train_raw,
            train_pos=ud_train_pos,
            train_content=ud_train_content,
            train_labels_obj=ud_train_labels["deprel"],
            eval_raw=ud_eval_raw,
            eval_pos=ud_eval_pos,
            eval_content=ud_eval_content,
            eval_labels_obj=ud_eval_labels["deprel"],
            min_examples_per_class=args.min_examples_per_class,
            train_source="UD_EWT_train",
            eval_source="UD_EWT_dev",
        ),
        prepare_task_dataset(
            name="ner_wnut17",
            metric_name="macro_f1",
            train_raw=wnut_train_raw,
            train_pos=wnut_train_pos,
            train_content=wnut_train_content,
            train_labels_obj=wnut_train_labels["ner"],
            eval_raw=wnut_eval_raw,
            eval_pos=wnut_eval_pos,
            eval_content=wnut_eval_content,
            eval_labels_obj=wnut_eval_labels["ner"],
            min_examples_per_class=args.min_examples_per_class,
            train_source="WNUT17_train",
            eval_source="WNUT17_validation",
        ),
    ]

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
        joint_gain = rep_results["joint"]["primary_metric"] - best_private
        summary_tasks[task.name] = {
            "metric_name": task.metric_name,
            "n_train": int(task.train_labels.shape[0]),
            "n_eval": int(task.eval_labels.shape[0]),
            "n_classes_train": int(np.unique(task.train_labels).shape[0]),
            "label_names": task.label_names,
            "train_source": task.train_source,
            "eval_source": task.eval_source,
            "best_private_metric": float(best_private),
            "joint_gain": float(joint_gain),
            "representations": rep_results,
        }

    summary = {
        "stage": "pcc_stage_a0",
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
        "ud_sources": {"train_url": UD_TRAIN_URL, "dev_url": UD_DEV_URL},
        "wnut_source": "flaitenberger/wnut_17",
        "args": vars(args),
    }
    with open(out_dir / "pcc_stage_a0_summary.json", "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)
    with open(out_dir / "pcc_stage_a0_metrics.tsv", "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()), delimiter="\t")
        w.writeheader()
        w.writerows(rows)
    print(json.dumps({
        "output_dir": str(out_dir),
        "summary": str(out_dir / 'pcc_stage_a0_summary.json'),
        "metrics_tsv": str(out_dir / 'pcc_stage_a0_metrics.tsv'),
        "task_joint_gains": {k: v['joint_gain'] for k, v in summary_tasks.items()},
    }, indent=2))


if __name__ == "__main__":
    main()
