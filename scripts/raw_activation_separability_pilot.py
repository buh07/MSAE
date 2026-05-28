#!/usr/bin/env python3
"""
Raw-activation separability pilot (no SAE).

Implements the Paper-1 de-risking experiment in MSAE_revised.md §1.5B:
1) Collect token-level activations from a chosen residual/hidden layer.
2) Train linear probes for position and token identity on raw activations.
3) Derive probe subspaces from probe weight matrices (SVD of probe coefficients).
4) Evaluate transfer under projection to S_pos, S_pos^perp, S_tok, S_tok^perp.
5) Compute geometric overlap diagnostics (principal angles, cross projection energy).
6) Emit metrics + threshold checks.

This script is intentionally small-model friendly and can run on ~16GB VRAM with
appropriate args (small model, short context, small batch, capped collected tokens).
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import os
import random
import subprocess
import time
from collections import Counter
from dataclasses import dataclass
from typing import Dict, List, Tuple

import numpy as np
import torch
import torch.nn.functional as F
from datasets import load_dataset
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, roc_auc_score
from sklearn.model_selection import train_test_split
from transformers import AutoModelForCausalLM, AutoTokenizer


@dataclass
class ProbeMetrics:
    top1: float
    auc_ovo_macro: float
    n_classes: int
    n_train: int
    n_test: int


@dataclass
class ProbeFitDiagnostics:
    n_iter_max: int
    hit_max_iter: bool
    backend: str
    elapsed_sec: float
    final_train_loss: float | None
    best_eval_top1: float | None
    effective_lr: float | None
    scheduler: str | None


@dataclass
class ProbeWeights:
    coef: np.ndarray
    intercept: np.ndarray
    mu: np.ndarray | None = None
    sigma: np.ndarray | None = None


@dataclass
class TorchProbeConfig:
    max_steps: int
    batch_size: int
    lr: float
    weight_decay: float
    eval_every: int
    patience: int
    min_steps: int
    token_ceiling_top1: float
    token_ceiling_evals: int
    token_ceiling_loss_eps: float
    position_raw_highdim_lr: float
    position_raw_highdim_threshold: int
    scheduler: str


@dataclass
class SourceSpec:
    dataset_name: str
    dataset_config: str
    dataset_split: str
    text_field: str
    source_label: str


DEFAULT_BALANCED_SOURCE_MANIFEST: List[SourceSpec] = [
    SourceSpec(
        dataset_name="HuggingFaceFW/fineweb-edu",
        dataset_config="CC-MAIN-2024-10",
        dataset_split="train",
        text_field="text",
        source_label="FineWeb-Edu",
    ),
    SourceSpec(
        dataset_name="ArmelR/the-pile-splitted",
        dataset_config="Pile-CC",
        dataset_split="train",
        text_field="text",
        source_label="Pile-CC",
    ),
    SourceSpec(
        dataset_name="ArmelR/the-pile-splitted",
        dataset_config="Github",
        dataset_split="train",
        text_field="text",
        source_label="Github",
    ),
    SourceSpec(
        dataset_name="ArmelR/the-pile-splitted",
        dataset_config="PubMed Abstracts",
        dataset_split="train",
        text_field="text",
        source_label="PubMed Abstracts",
    ),
    SourceSpec(
        dataset_name="ArmelR/the-pile-splitted",
        dataset_config="ArXiv",
        dataset_split="train",
        text_field="text",
        source_label="ArXiv",
    ),
]


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Raw-activation separability pilot")
    p.add_argument(
        "--split_mode",
        type=str,
        default="iid",
        choices=["iid", "source_holdout", "corpus_holdout", "dual_holdout"],
    )
    p.add_argument("--model_name", type=str, default="EleutherAI/pythia-70m-deduped")
    p.add_argument("--dataset_name", type=str, default="wikitext")
    p.add_argument("--dataset_config", type=str, default="wikitext-2-raw-v1")
    p.add_argument("--dataset_split", type=str, default="train")
    p.add_argument("--text_field", type=str, default="text")
    p.add_argument("--max_text_samples", type=int, default=4000)
    p.add_argument("--max_tokens_collect", type=int, default=120000)
    p.add_argument("--context_length", type=int, default=128)
    p.add_argument("--batch_size", type=int, default=8)
    p.add_argument("--layer_index", type=int, default=4)
    p.add_argument("--position_max", type=int, default=64)
    p.add_argument("--top_k_tokens", type=int, default=256)
    p.add_argument("--train_frac", type=float, default=0.8)
    p.add_argument("--probe_ranks", type=str, default="8,16,32")
    p.add_argument("--min_examples_per_class", type=int, default=20)
    p.add_argument("--min_samples_after_filter", type=int, default=1000)
    p.add_argument("--probe_max_iter", type=int, default=200)
    p.add_argument("--probe_c_raw", type=float, default=0.2)
    p.add_argument("--probe_c_projected", type=float, default=1.0)
    p.add_argument("--probe_backend", type=str, default="auto", choices=["auto", "sklearn", "torch"])
    p.add_argument("--probe_torch_max_steps_raw", type=int, default=1200)
    p.add_argument("--probe_torch_max_steps_projected", type=int, default=3000)
    p.add_argument("--probe_torch_batch_size", type=int, default=4096)
    p.add_argument("--probe_torch_lr", type=float, default=0.05)
    p.add_argument("--probe_torch_scheduler", type=str, default="none", choices=["none", "cosine"])
    p.add_argument(
        "--probe_torch_weight_decay",
        type=float,
        default=-1.0,
        help="If < 0, uses an sklearn-like scaled L2 value derived from C and n_train.",
    )
    p.add_argument("--probe_torch_eval_every", type=int, default=50)
    p.add_argument("--probe_torch_patience_raw", type=int, default=250)
    p.add_argument("--probe_torch_patience_projected", type=int, default=600)
    p.add_argument("--probe_torch_min_steps", type=int, default=200)
    p.add_argument("--probe_torch_token_ceiling_top1", type=float, default=0.995)
    p.add_argument("--probe_torch_token_ceiling_evals", type=int, default=3)
    p.add_argument("--probe_torch_token_ceiling_loss_eps", type=float, default=1e-4)
    p.add_argument("--probe_torch_lr_position_raw_highdim", type=float, default=0.01)
    p.add_argument("--probe_torch_lr_position_raw_highdim_threshold", type=int, default=768)
    p.add_argument("--source_manifest_path", type=str, default="")
    p.add_argument("--train_source_max_text_samples", type=int, default=1200)
    p.add_argument("--eval_source_max_text_samples", type=int, default=1200)
    p.add_argument("--holdout_source_label", type=str, default="")
    p.add_argument("--corpus_holdout_dataset_name", type=str, default="Skylion007/openwebtext")
    p.add_argument("--corpus_holdout_dataset_config", type=str, default="")
    p.add_argument("--corpus_holdout_dataset_split", type=str, default="train")
    p.add_argument("--corpus_holdout_text_field", type=str, default="text")
    p.add_argument("--corpus_holdout_max_text_samples", type=int, default=2500)
    p.add_argument("--holdout_eval_max_tokens_collect", type=int, default=50000)
    p.add_argument("--disable_causal_sanity", action="store_true")
    p.add_argument("--disable_intermediates", action="store_true")
    p.add_argument(
        "--c2_alt_mode",
        type=str,
        default="linear_rank_drop",
        choices=["linear_rank_drop"],
    )
    p.add_argument("--c2_var_v2_ratio_threshold", type=float, default=3.0)
    p.add_argument("--c2_var_v2_excess_floor", type=float, default=0.05)
    p.add_argument("--c3_v2_drop_fraction", type=float, default=0.25)
    p.add_argument("--seed", type=int, default=42)
    p.add_argument("--git_commit_hash", type=str, default="")
    p.add_argument("--device", type=str, default="auto", choices=["auto", "cpu", "cuda"])
    p.add_argument("--dtype", type=str, default="auto", choices=["auto", "fp32", "fp16", "bf16"])
    p.add_argument("--skip_first_position", action="store_true")
    p.add_argument("--output_dir", type=str, default="MSAE/pilot_outputs/raw_sep")
    return p.parse_args()


def set_seed(seed: int) -> None:
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)


def choose_device(arg_device: str) -> torch.device:
    if arg_device == "cpu":
        return torch.device("cpu")
    if arg_device == "cuda":
        if not torch.cuda.is_available():
            raise RuntimeError("CUDA requested but not available.")
        return torch.device("cuda")
    return torch.device("cuda" if torch.cuda.is_available() else "cpu")


def choose_probe_backend(arg_probe_backend: str, device: torch.device) -> str:
    if arg_probe_backend == "auto":
        return "torch" if device.type == "cuda" else "sklearn"
    if arg_probe_backend == "torch" and device.type != "cuda":
        print("[warn] --probe_backend=torch on non-CUDA device. Falling back to sklearn backend.")
        return "sklearn"
    return arg_probe_backend


def choose_dtype(arg_dtype: str, device: torch.device) -> torch.dtype:
    if arg_dtype == "fp32":
        return torch.float32
    if arg_dtype == "fp16":
        return torch.float16
    if arg_dtype == "bf16":
        return torch.bfloat16
    # auto
    if device.type == "cuda":
        return torch.float16
    return torch.float32


def normalize_text_field(raw: dict, text_field: str) -> str:
    if text_field in raw and isinstance(raw[text_field], str):
        return raw[text_field]
    for key in ("text", "content", "body"):
        if key in raw and isinstance(raw[key], str):
            return raw[key]
    return ""


def _load_dataset_local(dataset_name: str, dataset_config: str, dataset_split: str):
    if dataset_config:
        return load_dataset(dataset_name, dataset_config, split=dataset_split)
    return load_dataset(dataset_name, split=dataset_split)


def load_texts(
    dataset_name: str,
    dataset_config: str,
    dataset_split: str,
    text_field: str,
    max_text_samples: int,
) -> List[str]:
    ds = _load_dataset_local(dataset_name, dataset_config, dataset_split)
    texts: List[str] = []
    for row in ds:
        t = normalize_text_field(row, text_field).strip()
        if not t:
            continue
        texts.append(t)
        if len(texts) >= max_text_samples:
            break
    if not texts:
        raise RuntimeError("No usable texts found in dataset.")
    return texts


def load_source_manifest(source_manifest_path: str) -> List[SourceSpec]:
    if not source_manifest_path:
        return list(DEFAULT_BALANCED_SOURCE_MANIFEST)
    with open(source_manifest_path, "r", encoding="utf-8") as f:
        raw = json.load(f)
    specs: List[SourceSpec] = []
    for row in raw:
        specs.append(
            SourceSpec(
                dataset_name=str(row["dataset_name"]),
                dataset_config=str(row.get("dataset_config", "")),
                dataset_split=str(row.get("dataset_split", "train")),
                text_field=str(row.get("text_field", "text")),
                source_label=str(row["source_label"]),
            )
        )
    if not specs:
        raise RuntimeError("Source manifest is empty.")
    return specs


def load_texts_from_source_specs(
    source_specs: List[SourceSpec], max_per_source: int
) -> Tuple[List[str], List[str]]:
    texts: List[str] = []
    labels: List[str] = []
    for spec in source_specs:
        t = load_texts(
            dataset_name=spec.dataset_name,
            dataset_config=spec.dataset_config,
            dataset_split=spec.dataset_split,
            text_field=spec.text_field,
            max_text_samples=max_per_source,
        )
        texts.extend(t)
        labels.extend([spec.source_label] * len(t))
    return texts, labels


def resolve_git_commit_hash(arg_hash: str) -> str:
    if arg_hash:
        return arg_hash
    try:
        out = subprocess.check_output(
            ["git", "rev-parse", "HEAD"],
            stderr=subprocess.DEVNULL,
            text=True,
        ).strip()
        return out
    except Exception:
        return ""


def resolve_holdout_plan(args: argparse.Namespace) -> Dict[str, object]:
    source_specs = load_source_manifest(args.source_manifest_path) if args.source_manifest_path else []
    mode = args.split_mode
    if mode == "iid":
        # Backward compatibility:
        # - If source manifest is provided, use balanced multi-source IID mix.
        # - Otherwise fall back to single-dataset IID behavior.
        if source_specs:
            train_texts, train_src = load_texts_from_source_specs(source_specs, args.train_source_max_text_samples)
            manifest_hash = hashlib.sha1(
                json.dumps([s.__dict__ for s in source_specs], sort_keys=True).encode("utf-8")
            ).hexdigest()
        else:
            train_texts = load_texts(
                dataset_name=args.dataset_name,
                dataset_config=args.dataset_config,
                dataset_split=args.dataset_split,
                text_field=args.text_field,
                max_text_samples=args.max_text_samples,
            )
            train_src = []
            manifest_hash = ""
        return {
            "train_texts": train_texts,
            "eval_texts": None,
            "train_sources": train_src,
            "eval_sources": [],
            "mode": mode,
            "holdout_source_label": "",
            "corpus_holdout_dataset_name": "",
            "manifest_hash": manifest_hash,
        }

    if mode == "source_holdout":
        if not args.holdout_source_label:
            raise RuntimeError("--holdout_source_label is required for split_mode=source_holdout")
        holdout = args.holdout_source_label
        train_specs = [s for s in source_specs if s.source_label != holdout]
        eval_specs = [s for s in source_specs if s.source_label == holdout]
        if not train_specs or not eval_specs:
            raise RuntimeError(f"Invalid holdout source label: {holdout!r}")
        train_texts, train_src = load_texts_from_source_specs(train_specs, args.train_source_max_text_samples)
        eval_texts, eval_src = load_texts_from_source_specs(eval_specs, args.eval_source_max_text_samples)
        manifest_hash = hashlib.sha1(
            json.dumps([s.__dict__ for s in source_specs], sort_keys=True).encode("utf-8")
        ).hexdigest()
        return {
            "train_texts": train_texts,
            "eval_texts": eval_texts,
            "train_sources": train_src,
            "eval_sources": eval_src,
            "mode": mode,
            "holdout_source_label": holdout,
            "corpus_holdout_dataset_name": "",
            "manifest_hash": manifest_hash,
        }

    if mode in {"corpus_holdout", "dual_holdout"}:
        train_texts, train_src = load_texts_from_source_specs(source_specs, args.train_source_max_text_samples)
        # For dual_holdout we use the explicit corpus holdout as the primary eval set
        # and store source labels only for training provenance.
        eval_texts = load_texts(
            dataset_name=args.corpus_holdout_dataset_name,
            dataset_config=args.corpus_holdout_dataset_config,
            dataset_split=args.corpus_holdout_dataset_split,
            text_field=args.corpus_holdout_text_field,
            max_text_samples=args.corpus_holdout_max_text_samples,
        )
        manifest_hash = hashlib.sha1(
            json.dumps([s.__dict__ for s in source_specs], sort_keys=True).encode("utf-8")
        ).hexdigest()
        return {
            "train_texts": train_texts,
            "eval_texts": eval_texts,
            "train_sources": train_src,
            "eval_sources": ["corpus_holdout"] * len(eval_texts),
            "mode": mode,
            "holdout_source_label": "",
            "corpus_holdout_dataset_name": args.corpus_holdout_dataset_name,
            "manifest_hash": manifest_hash,
        }

    raise RuntimeError(f"Unsupported split_mode={mode}")


def chunked(items: List[str], batch_size: int) -> List[List[str]]:
    return [items[i : i + batch_size] for i in range(0, len(items), batch_size)]


def resolve_hidden_state_index(requested_layer: int, n_hidden_states: int) -> int:
    # hidden_states includes embeddings at index 0, then per-layer outputs.
    # requested_layer is treated as transformer block index (0-based).
    max_block = n_hidden_states - 2
    if requested_layer < 0:
        return max(1, n_hidden_states + requested_layer)
    block = min(requested_layer, max_block)
    return block + 1


def collect_token_level_activations(
    model: AutoModelForCausalLM,
    model_name: str,
    tokenizer: AutoTokenizer,
    texts: List[str],
    device: torch.device,
    context_length: int,
    batch_size: int,
    layer_index: int,
    position_max: int,
    max_tokens_collect: int,
    skip_first_position: bool,
) -> Tuple[np.ndarray, np.ndarray, np.ndarray, Dict[str, int]]:
    xs: List[np.ndarray] = []
    pos_labels: List[np.ndarray] = []
    tok_labels: List[np.ndarray] = []

    total_tokens = 0
    n_batches = 0
    n_examples = 0
    logged_layer_mapping = False

    for batch_text in chunked(texts, batch_size):
        enc = tokenizer(
            batch_text,
            return_tensors="pt",
            truncation=True,
            padding=True,
            max_length=context_length,
        )
        input_ids = enc["input_ids"].to(device)
        attention_mask = enc["attention_mask"].to(device)

        with torch.no_grad():
            out = model(
                input_ids=input_ids,
                attention_mask=attention_mask,
                output_hidden_states=True,
                use_cache=False,
            )

        hs_idx = resolve_hidden_state_index(layer_index, len(out.hidden_states))
        if not logged_layer_mapping:
            print(
                "[layer-map] "
                f"model={model_name} requested_layer={layer_index} "
                f"using hidden_states[{hs_idx}] = output of block {hs_idx - 1}"
            )
            logged_layer_mapping = True
        h = out.hidden_states[hs_idx].detach().float().cpu().numpy()  # [B, T, D]
        ids = input_ids.detach().cpu().numpy()
        att = attention_mask.detach().cpu().numpy()
        bsz, tlen, _ = h.shape

        for bi in range(bsz):
            valid = att[bi].astype(bool)
            positions = np.arange(tlen, dtype=np.int64)
            if skip_first_position:
                valid &= positions > 0
            if position_max > 0:
                valid &= positions < position_max
            if not np.any(valid):
                continue

            x_i = h[bi][valid]
            p_i = positions[valid]
            tok_i = ids[bi][valid]

            xs.append(x_i)
            pos_labels.append(p_i)
            tok_labels.append(tok_i)

            total_tokens += int(valid.sum())
            n_examples += 1
            if total_tokens >= max_tokens_collect:
                break

        n_batches += 1
        if total_tokens >= max_tokens_collect:
            break

    if not xs:
        raise RuntimeError("No token-level activations collected; try increasing text/batch limits.")

    X = np.concatenate(xs, axis=0)
    y_pos = np.concatenate(pos_labels, axis=0)
    y_tok = np.concatenate(tok_labels, axis=0)

    if X.shape[0] > max_tokens_collect:
        X = X[:max_tokens_collect]
        y_pos = y_pos[:max_tokens_collect]
        y_tok = y_tok[:max_tokens_collect]

    stats = {
        "n_batches": n_batches,
        "n_sequences_with_valid_tokens": n_examples,
        "n_tokens_collected": int(X.shape[0]),
        "hidden_size": int(X.shape[1]),
    }
    return X, y_pos, y_tok, stats


def top_k_token_filter(y_tok: np.ndarray, top_k: int) -> np.ndarray:
    c = Counter(int(x) for x in y_tok.tolist())
    top = {tid for tid, _ in c.most_common(top_k)}
    return np.array([int(t) in top for t in y_tok.tolist()], dtype=bool)


def remap_labels(y: np.ndarray) -> Tuple[np.ndarray, Dict[int, int]]:
    uniq = np.unique(y)
    mapping = {int(v): i for i, v in enumerate(uniq.tolist())}
    y_new = np.array([mapping[int(v)] for v in y.tolist()], dtype=np.int64)
    return y_new, mapping


def can_stratify(y: np.ndarray, n_train: int, n_test: int) -> bool:
    uniq, counts = np.unique(y, return_counts=True)
    n_classes = int(uniq.shape[0])
    if n_classes < 2:
        return False
    if n_train < n_classes or n_test < n_classes:
        return False
    if int(np.min(counts)) < 2:
        return False
    return True


def filter_min_examples_per_class(
    X: np.ndarray, y: np.ndarray, min_examples_per_class: int
) -> Tuple[np.ndarray, np.ndarray]:
    c = Counter(int(v) for v in y.tolist())
    keep = {k for k, v in c.items() if v >= min_examples_per_class}
    mask = np.array([int(v) in keep for v in y.tolist()], dtype=bool)
    return X[mask], y[mask]


def remap_with_existing_mapping(y: np.ndarray, mapping: Dict[int, int]) -> Tuple[np.ndarray, np.ndarray]:
    mask = np.array([int(v) in mapping for v in y.tolist()], dtype=bool)
    if not np.any(mask):
        return np.zeros((0,), dtype=np.int64), mask
    y_new = np.array([mapping[int(v)] for v in y[mask].tolist()], dtype=np.int64)
    return y_new, mask


def append_jsonl(path: str, obj: Dict[str, object]) -> None:
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(obj) + "\n")


def atomic_write_json(path: str, obj: Dict[str, object]) -> None:
    tmp = f"{path}.tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(obj, f, indent=2)
    os.replace(tmp, path)


def write_rows_csv(path: str, rows: List[Dict[str, object]]) -> None:
    if not rows:
        return
    with open(path, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


@torch.no_grad()
def _predict_logits_batched(
    model: torch.nn.Linear, x_t: torch.Tensor, batch_size: int = 8192
) -> torch.Tensor:
    logits_chunks = []
    for s in range(0, x_t.shape[0], batch_size):
        logits_chunks.append(model(x_t[s : s + batch_size]))
    return torch.cat(logits_chunks, dim=0)


def _train_eval_probe_sklearn(
    X: np.ndarray,
    y: np.ndarray,
    train_frac: float,
    seed: int,
    max_iter: int,
    c_value: float,
    eval_override: tuple[np.ndarray, np.ndarray] | None = None,
) -> Tuple[ProbeMetrics, ProbeWeights, ProbeFitDiagnostics]:
    t0 = time.time()
    if eval_override is None:
        n_total = int(y.shape[0])
        n_train_target = max(1, min(n_total - 1, int(round(train_frac * n_total))))
        n_test_target = n_total - n_train_target
        stratify_primary = y if can_stratify(y, n_train_target, n_test_target) else None
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, train_size=train_frac, random_state=seed, stratify=stratify_primary
        )
    else:
        X_train = X
        y_train = y
        X_test, y_test = eval_override

    mu = X_train.mean(axis=0, keepdims=True)
    sigma = X_train.std(axis=0, keepdims=True) + 1e-6
    X_train = (X_train - mu) / sigma
    X_test = (X_test - mu) / sigma

    probe = LogisticRegression(
        solver="saga",
        max_iter=max_iter,
        C=c_value,
        random_state=seed,
    )
    probe.fit(X_train, y_train)

    pred = probe.predict(X_test)
    top1 = float(accuracy_score(y_test, pred))

    auc = float("nan")
    try:
        proba = probe.predict_proba(X_test)
        auc = float(roc_auc_score(y_test, proba, multi_class="ovo", average="macro"))
    except Exception:
        pass

    metrics = ProbeMetrics(
        top1=top1,
        auc_ovo_macro=auc,
        n_classes=int(np.unique(y).shape[0]),
        n_train=int(y_train.shape[0]),
        n_test=int(y_test.shape[0]),
    )

    n_iter = np.asarray(probe.n_iter_, dtype=np.int64)
    n_iter_max = int(np.max(n_iter)) if n_iter.size else 0
    diagnostics = ProbeFitDiagnostics(
        n_iter_max=n_iter_max,
        hit_max_iter=bool(n_iter_max >= max_iter),
        backend="sklearn",
        elapsed_sec=float(time.time() - t0),
        final_train_loss=None,
        best_eval_top1=None,
        effective_lr=None,
        scheduler=None,
    )
    weights = ProbeWeights(
        coef=probe.coef_.astype(np.float64),
        intercept=probe.intercept_.astype(np.float64),
        mu=mu.astype(np.float64).reshape(-1),
        sigma=sigma.astype(np.float64).reshape(-1),
    )
    return metrics, weights, diagnostics


def _train_eval_probe_torch(
    X: np.ndarray | torch.Tensor,
    y: np.ndarray,
    train_frac: float,
    seed: int,
    c_value: float,
    probe_name: str,
    device: torch.device,
    cfg: TorchProbeConfig,
    intermediates_dir: str | None,
    eval_override: tuple[np.ndarray | torch.Tensor, np.ndarray] | None = None,
) -> Tuple[ProbeMetrics, ProbeWeights, ProbeFitDiagnostics]:
    t0 = time.time()
    rng = np.random.default_rng(seed)

    n_samples = int(y.shape[0])
    all_idx = np.arange(n_samples, dtype=np.int64)
    if eval_override is None:
        n_train_target = max(1, min(n_samples - 1, int(round(train_frac * n_samples))))
        n_test_target = n_samples - n_train_target
        stratify_primary = y if can_stratify(y, n_train_target, n_test_target) else None
        train_idx, test_idx = train_test_split(
            all_idx, train_size=train_frac, random_state=seed, stratify=stratify_primary
        )
        y_train = y[train_idx]
        y_test = y[test_idx]
    else:
        train_idx = all_idx
        y_train = y
        y_test = eval_override[1]

    n_train_split = int(train_idx.shape[0])
    n_fit_target = max(1, min(n_train_split - 1, int(round(0.9 * n_train_split))))
    n_val_target = n_train_split - n_fit_target
    stratify_fit = y_train if can_stratify(y_train, n_fit_target, n_val_target) else None
    fit_idx, val_idx = train_test_split(
        train_idx,
        train_size=0.9,
        random_state=seed + 17,
        stratify=stratify_fit,
    )
    y_fit = y[fit_idx]
    y_val = y[val_idx]

    if torch.is_tensor(X):
        x_all_t = X.to(device=device, dtype=torch.float32)
    else:
        x_all_t = torch.from_numpy(X.astype(np.float32)).to(device)

    train_idx_t = torch.from_numpy(train_idx.astype(np.int64)).to(device)
    fit_idx_t = torch.from_numpy(fit_idx.astype(np.int64)).to(device)
    val_idx_t = torch.from_numpy(val_idx.astype(np.int64)).to(device)
    test_idx_t = torch.from_numpy(test_idx.astype(np.int64)).to(device) if eval_override is None else None

    x_train_t = x_all_t[train_idx_t]
    mu_t = x_train_t.mean(dim=0, keepdim=True)
    sigma_t = x_train_t.std(dim=0, keepdim=True) + 1e-6
    x_all_norm_t = (x_all_t - mu_t) / sigma_t

    x_fit_t = x_all_norm_t[fit_idx_t]
    y_fit_t = torch.from_numpy(y_fit.astype(np.int64)).to(device)
    x_val_t = x_all_norm_t[val_idx_t]
    y_val_t = torch.from_numpy(y_val.astype(np.int64)).to(device)
    if eval_override is None:
        x_test_t = x_all_norm_t[test_idx_t]
        y_test_t = torch.from_numpy(y_test.astype(np.int64)).to(device)
    else:
        X_eval, y_eval = eval_override
        if torch.is_tensor(X_eval):
            x_eval_t = X_eval.to(device=device, dtype=torch.float32)
        else:
            x_eval_t = torch.from_numpy(X_eval.astype(np.float32)).to(device)
        x_test_t = (x_eval_t - mu_t) / sigma_t
        y_test_t = torch.from_numpy(y_eval.astype(np.int64)).to(device)

    n_classes = int(np.unique(y).shape[0])
    hidden_size = int(x_all_t.shape[1])
    model = torch.nn.Linear(hidden_size, n_classes, bias=True, device=device, dtype=torch.float32)

    if cfg.weight_decay >= 0.0:
        weight_decay = cfg.weight_decay
    else:
        # sklearn-like scaling: stronger C -> weaker effective L2.
        weight_decay = 1.0 / max(1.0, float(x_fit_t.shape[0]) * max(c_value, 1e-8))

    effective_lr = cfg.lr
    if probe_name == "position_raw" and hidden_size >= cfg.position_raw_highdim_threshold:
        effective_lr = cfg.position_raw_highdim_lr

    optimizer = torch.optim.AdamW(model.parameters(), lr=effective_lr, weight_decay=weight_decay)
    scheduler = None
    if cfg.scheduler == "cosine":
        scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=max(2, cfg.max_steps))

    log_path = None
    if intermediates_dir is not None:
        log_path = os.path.join(intermediates_dir, f"{probe_name}_train_log.jsonl")
        if os.path.exists(log_path):
            os.remove(log_path)

    best_state = {k: v.detach().cpu().clone() for k, v in model.state_dict().items()}
    best_val_top1 = -1.0
    best_val_loss = float("inf")
    no_improve_steps = 0
    steps_run = 0
    final_train_loss = None
    token_ceiling_hits = 0

    perm = rng.permutation(x_fit_t.shape[0])
    cursor = 0

    for step in range(1, cfg.max_steps + 1):
        if cursor + cfg.batch_size > x_fit_t.shape[0]:
            perm = rng.permutation(x_fit_t.shape[0])
            cursor = 0
        idx = perm[cursor : cursor + min(cfg.batch_size, x_fit_t.shape[0])]
        cursor += min(cfg.batch_size, x_fit_t.shape[0])
        idx_t = torch.from_numpy(idx.astype(np.int64)).to(device)

        xb = x_fit_t[idx_t]
        yb = y_fit_t[idx_t]

        optimizer.zero_grad(set_to_none=True)
        logits = model(xb)
        loss = F.cross_entropy(logits, yb)
        loss.backward()
        optimizer.step()
        if scheduler is not None:
            scheduler.step()

        final_train_loss = float(loss.detach().item())
        steps_run = step

        should_eval = step == 1 or step % cfg.eval_every == 0 or step == cfg.max_steps
        if should_eval:
            with torch.no_grad():
                val_logits = _predict_logits_batched(model, x_val_t)
                val_loss = float(F.cross_entropy(val_logits, y_val_t).item())
                val_pred = torch.argmax(val_logits, dim=1)
                val_top1 = float((val_pred == y_val_t).float().mean().item())

            prior_best_val_loss = best_val_loss
            improved = False
            if val_top1 > best_val_top1 + 1e-6:
                improved = True
            elif abs(val_top1 - best_val_top1) <= 1e-6 and val_loss < best_val_loss:
                improved = True

            if improved:
                best_val_top1 = val_top1
                best_val_loss = val_loss
                best_state = {k: v.detach().cpu().clone() for k, v in model.state_dict().items()}
                no_improve_steps = 0
            else:
                no_improve_steps += cfg.eval_every

            loss_improvement = max(0.0, prior_best_val_loss - val_loss)
            if probe_name.startswith("token_"):
                if (
                    val_top1 >= cfg.token_ceiling_top1
                    and loss_improvement < cfg.token_ceiling_loss_eps
                ):
                    token_ceiling_hits += 1
                else:
                    token_ceiling_hits = 0

            elapsed = float(time.time() - t0)
            progress = {
                "probe_name": probe_name,
                "step": step,
                "max_steps": cfg.max_steps,
                "train_loss": final_train_loss,
                "val_loss": val_loss,
                "val_top1": val_top1,
                "best_val_top1": best_val_top1,
                "no_improve_steps": no_improve_steps,
                "token_ceiling_hits": token_ceiling_hits,
                "elapsed_sec": elapsed,
                "batch_size": cfg.batch_size,
                "weight_decay": weight_decay,
                "effective_lr": effective_lr,
            }
            print(
                "[probe-progress] "
                f"name={probe_name} step={step}/{cfg.max_steps} "
                f"train_loss={final_train_loss:.5f} val_top1={val_top1:.4f} "
                f"best_val_top1={best_val_top1:.4f} elapsed_s={elapsed:.1f}"
            )
            if log_path is not None:
                append_jsonl(log_path, progress)

            if step >= cfg.min_steps and no_improve_steps >= cfg.patience:
                print(f"[probe-early-stop] name={probe_name} step={step} patience={cfg.patience}")
                break
            if (
                probe_name.startswith("token_")
                and step >= cfg.min_steps
                and token_ceiling_hits >= cfg.token_ceiling_evals
            ):
                print(
                    "[probe-ceiling-stop] "
                    f"name={probe_name} step={step} top1={val_top1:.4f} "
                    f"hits={token_ceiling_hits}/{cfg.token_ceiling_evals}"
                )
                break

    with torch.no_grad():
        model.load_state_dict({k: v.to(device) for k, v in best_state.items()})
        test_logits = _predict_logits_batched(model, x_test_t)
        test_pred = torch.argmax(test_logits, dim=1)
        top1 = float((test_pred == y_test_t).float().mean().item())
        test_proba = torch.softmax(test_logits, dim=1).detach().cpu().numpy()

    auc = float("nan")
    try:
        auc = float(roc_auc_score(y_test, test_proba, multi_class="ovo", average="macro"))
    except Exception:
        pass

    metrics = ProbeMetrics(
        top1=top1,
        auc_ovo_macro=auc,
        n_classes=n_classes,
        n_train=int(y_train.shape[0]),
        n_test=int(y_test.shape[0]),
    )

    diagnostics = ProbeFitDiagnostics(
        n_iter_max=steps_run,
        hit_max_iter=bool(steps_run >= cfg.max_steps),
        backend="torch",
        elapsed_sec=float(time.time() - t0),
        final_train_loss=final_train_loss,
        best_eval_top1=best_val_top1,
        effective_lr=float(effective_lr),
        scheduler=str(cfg.scheduler),
    )

    weights = ProbeWeights(
        coef=model.weight.detach().cpu().numpy().astype(np.float64),
        intercept=model.bias.detach().cpu().numpy().astype(np.float64),
        mu=mu_t.detach().cpu().numpy().astype(np.float64).reshape(-1),
        sigma=sigma_t.detach().cpu().numpy().astype(np.float64).reshape(-1),
    )

    del (
        model,
        x_fit_t,
        y_fit_t,
        x_val_t,
        y_val_t,
        x_test_t,
        y_test_t,
        test_logits,
        x_all_t,
        x_train_t,
        x_all_norm_t,
        train_idx_t,
        fit_idx_t,
        val_idx_t,
        test_idx_t,
        mu_t,
        sigma_t,
    )
    if torch.cuda.is_available():
        torch.cuda.empty_cache()

    return metrics, weights, diagnostics


def train_eval_probe(
    X: np.ndarray | torch.Tensor,
    y: np.ndarray,
    train_frac: float,
    seed: int,
    max_iter: int,
    c_value: float,
    probe_backend: str,
    probe_device: torch.device,
    torch_cfg: TorchProbeConfig,
    probe_name: str,
    intermediates_dir: str | None,
    eval_override: tuple[np.ndarray | torch.Tensor, np.ndarray] | None = None,
) -> Tuple[ProbeMetrics, ProbeWeights, ProbeFitDiagnostics]:
    # Cross-entropy implementations require labels in [0, n_classes-1].
    # Filtering can introduce gaps in integer IDs, so we reindex here.
    y_reindexed, y_mapping = remap_labels(y)
    if probe_backend == "sklearn":
        if torch.is_tensor(X):
            X = X.detach().cpu().numpy()
        if eval_override is not None:
            X_eval, y_eval = eval_override
            if torch.is_tensor(X_eval):
                X_eval = X_eval.detach().cpu().numpy()
            y_eval_reindexed, eval_mask = remap_with_existing_mapping(y_eval, y_mapping)
            if y_eval_reindexed.shape[0] == 0:
                raise RuntimeError(f"No eval samples survived mapping for probe {probe_name}.")
            X_eval = X_eval[eval_mask]
            return _train_eval_probe_sklearn(
                X,
                y_reindexed,
                train_frac,
                seed,
                max_iter,
                c_value,
                eval_override=(X_eval, y_eval_reindexed),
            )
        return _train_eval_probe_sklearn(X, y_reindexed, train_frac, seed, max_iter, c_value)
    if probe_backend == "torch":
        eval_override_reindexed = None
        if eval_override is not None:
            X_eval, y_eval = eval_override
            y_eval_reindexed, eval_mask = remap_with_existing_mapping(y_eval, y_mapping)
            if y_eval_reindexed.shape[0] == 0:
                raise RuntimeError(f"No eval samples survived mapping for probe {probe_name}.")
            if torch.is_tensor(X_eval):
                X_eval = X_eval[torch.from_numpy(eval_mask.astype(np.bool_)).to(X_eval.device)]
            else:
                X_eval = X_eval[eval_mask]
            eval_override_reindexed = (X_eval, y_eval_reindexed)
        return _train_eval_probe_torch(
            X=X,
            y=y_reindexed,
            train_frac=train_frac,
            seed=seed,
            c_value=c_value,
            probe_name=probe_name,
            device=probe_device,
            cfg=torch_cfg,
            intermediates_dir=intermediates_dir,
            eval_override=eval_override_reindexed,
        )
    raise ValueError(f"Unsupported probe backend: {probe_backend}")


def basis_from_probe(weights: ProbeWeights, rank: int) -> np.ndarray:
    coef = weights.coef.astype(np.float64)  # [C, D]
    # SVD over class-weight matrix gives discriminative directions in feature space
    _, _, vt = np.linalg.svd(coef, full_matrices=False)
    r = min(rank, vt.shape[0], vt.shape[1])
    return vt[:r].T  # [D, r]


def basis_from_probe_torch(weights: ProbeWeights, rank: int, device: torch.device) -> torch.Tensor:
    coef_t = torch.from_numpy(weights.coef.astype(np.float32)).to(device)
    _, _, vh = torch.linalg.svd(coef_t, full_matrices=False)
    r = min(rank, int(vh.shape[0]), int(vh.shape[1]))
    return vh[:r].T.contiguous()  # [D, r]


def project_to_basis(X: np.ndarray, basis: np.ndarray) -> np.ndarray:
    # X_proj = X * B * B^T
    return (X @ basis) @ basis.T


def project_to_basis_torch(X_t: torch.Tensor, basis_t: torch.Tensor) -> torch.Tensor:
    return (X_t @ basis_t) @ basis_t.T


def orthogonal_complement_projection(X: np.ndarray, basis: np.ndarray) -> np.ndarray:
    return X - project_to_basis(X, basis)


def orthogonal_complement_projection_torch(X_t: torch.Tensor, basis_t: torch.Tensor) -> torch.Tensor:
    return X_t - project_to_basis_torch(X_t, basis_t)


def principal_angle_summary(basis_a: np.ndarray, basis_b: np.ndarray) -> Dict[str, float]:
    # cos(theta_i) are singular values of Qa^T Qb
    qa, _ = np.linalg.qr(basis_a)
    qb, _ = np.linalg.qr(basis_b)
    s = np.linalg.svd(qa.T @ qb, compute_uv=False)
    s = np.clip(s, -1.0, 1.0)
    angles = np.degrees(np.arccos(s))
    return {
        "min_angle_deg": float(np.min(angles)),
        "median_angle_deg": float(np.median(angles)),
        "max_angle_deg": float(np.max(angles)),
    }


def principal_angle_summary_torch(basis_a_t: torch.Tensor, basis_b_t: torch.Tensor) -> Dict[str, float]:
    qa, _ = torch.linalg.qr(basis_a_t)
    qb, _ = torch.linalg.qr(basis_b_t)
    s = torch.linalg.svdvals(qa.T @ qb).clamp(min=-1.0, max=1.0)
    angles = torch.rad2deg(torch.arccos(s))
    return {
        "min_angle_deg": float(torch.min(angles).item()),
        "median_angle_deg": float(torch.median(angles).item()),
        "max_angle_deg": float(torch.max(angles).item()),
    }


def cross_projection_energy(basis_a: np.ndarray, basis_b: np.ndarray) -> float:
    # ||P_a P_b||_F with P = B B^T (orthonormalized first)
    qa, _ = np.linalg.qr(basis_a)
    qb, _ = np.linalg.qr(basis_b)
    pa = qa @ qa.T
    pb = qb @ qb.T
    return float(np.linalg.norm(pa @ pb, ord="fro"))


def cross_projection_energy_torch(basis_a_t: torch.Tensor, basis_b_t: torch.Tensor) -> float:
    qa, _ = torch.linalg.qr(basis_a_t)
    qb, _ = torch.linalg.qr(basis_b_t)
    pa = qa @ qa.T
    pb = qb @ qb.T
    return float(torch.linalg.matrix_norm(pa @ pb, ord="fro").item())


def normalized_cross_projection_energy(
    cross_projection_energy_fro: float, rank_a: int, rank_b: int
) -> float:
    min_rank = max(1, min(rank_a, rank_b))
    return float(cross_projection_energy_fro / math.sqrt(float(min_rank)))


def safe_ratio(num: float, den: float) -> float:
    if math.isnan(num) or math.isnan(den):
        return float("nan")
    if abs(den) < 1e-12:
        return float("nan")
    return float(num / den)


def projection_energy_ratio(x_proj: np.ndarray, x_raw: np.ndarray) -> float:
    proj_energy = float(np.square(np.asarray(x_proj, dtype=np.float64)).sum())
    raw_energy = float(np.square(np.asarray(x_raw, dtype=np.float64)).sum())
    return safe_ratio(proj_energy, raw_energy)


def projection_energy_ratio_torch(x_proj_t: torch.Tensor, x_raw_t: torch.Tensor) -> float:
    proj_energy = float(torch.sum(x_proj_t.to(torch.float64) ** 2).item())
    raw_energy = float(torch.sum(x_raw_t.to(torch.float64) ** 2).item())
    return safe_ratio(proj_energy, raw_energy)


def stable_softmax_numpy(logits: np.ndarray) -> np.ndarray:
    z = logits - np.max(logits, axis=1, keepdims=True)
    ez = np.exp(z)
    return ez / np.sum(ez, axis=1, keepdims=True)


def eval_frozen_probe_metrics(
    weights: ProbeWeights,
    y_train: np.ndarray,
    X_eval: np.ndarray,
    y_eval: np.ndarray,
) -> ProbeMetrics:
    y_train_remap, mapping = remap_labels(y_train)
    del y_train_remap
    y_eval_remap, eval_mask = remap_with_existing_mapping(y_eval, mapping)
    if y_eval_remap.shape[0] == 0:
        return ProbeMetrics(
            top1=float("nan"),
            auc_ovo_macro=float("nan"),
            n_classes=int(len(mapping)),
            n_train=int(y_train.shape[0]),
            n_test=0,
        )
    X_eval = X_eval[eval_mask]

    mu = weights.mu if weights.mu is not None else np.zeros((weights.coef.shape[1],), dtype=np.float64)
    sigma = weights.sigma if weights.sigma is not None else np.ones((weights.coef.shape[1],), dtype=np.float64)
    Xn = (X_eval.astype(np.float64) - mu.reshape(1, -1)) / (sigma.reshape(1, -1) + 1e-6)
    logits = Xn @ weights.coef.T + weights.intercept.reshape(1, -1)
    proba = stable_softmax_numpy(logits)
    pred = np.argmax(proba, axis=1)
    top1 = float(accuracy_score(y_eval_remap, pred))
    auc = float("nan")
    try:
        auc = float(roc_auc_score(y_eval_remap, proba, multi_class="ovo", average="macro"))
    except Exception:
        pass
    return ProbeMetrics(
        top1=top1,
        auc_ovo_macro=auc,
        n_classes=int(len(mapping)),
        n_train=int(y_train.shape[0]),
        n_test=int(y_eval_remap.shape[0]),
    )


def check_thresholds(
    raw_pos: ProbeMetrics,
    raw_tok: ProbeMetrics,
    pos_on_spos: ProbeMetrics,
    pos_on_spos_perp: ProbeMetrics,
    tok_on_stok: ProbeMetrics,
    tok_on_stok_perp: ProbeMetrics,
    tok_on_spos: ProbeMetrics,
    pos_on_stok: ProbeMetrics,
    angle_median_deg: float,
    rank: int,
    hidden_size: int,
    c2_alt_mode: str,
    tok_energy_excess: float,
    tok_energy_ratio: float,
    c2_var_v2_ratio_threshold: float,
    c2_var_v2_excess_floor: float,
    c3_v2_drop_fraction: float,
) -> Dict[str, object]:
    # Directly aligned with MSAE_revised.md §1.5B thresholds.
    # 1) Position separation
    c1 = (
        not math.isnan(pos_on_spos.auc_ovo_macro)
        and not math.isnan(pos_on_spos_perp.auc_ovo_macro)
        and pos_on_spos.auc_ovo_macro >= 0.90
        and pos_on_spos_perp.auc_ovo_macro <= 0.70
    )
    # 2) Token retention/drop (use top1 metrics)
    c2 = (
        tok_on_stok.top1 >= 0.75 * raw_tok.top1
        and tok_on_stok_perp.top1 <= 0.60 * raw_tok.top1
    )
    if c2_alt_mode == "linear_rank_drop":
        c2_alt_drop_cap = raw_tok.top1 * max(0.0, 1.0 - (float(rank) / float(hidden_size)))
        c2_alt = (
            tok_on_stok.top1 >= 0.75 * raw_tok.top1 and tok_on_stok_perp.top1 <= c2_alt_drop_cap
        )
    else:
        raise ValueError(f"Unsupported c2_alt_mode={c2_alt_mode!r}")
    c2_var = tok_energy_excess >= 0.20
    tok_energy_baseline = float(rank) / max(1.0, float(hidden_size))
    c2_var_ratio = safe_ratio(tok_energy_ratio, max(tok_energy_baseline, 1e-8))
    c2_var_v2 = (
        (not math.isnan(c2_var_ratio))
        and c2_var_ratio >= c2_var_v2_ratio_threshold
        and tok_energy_excess >= c2_var_v2_excess_floor
    )

    # 3) Cross-talk reduction
    c3 = (
        tok_on_spos.top1 <= 0.75 * raw_tok.top1
        and (not math.isnan(pos_on_stok.auc_ovo_macro))
        and (not math.isnan(raw_pos.auc_ovo_macro))
        and pos_on_stok.auc_ovo_macro <= 0.75 * raw_pos.auc_ovo_macro
    )

    # 3b) Chance-corrected cross-talk reduction
    raw_pos_auc = raw_pos.auc_ovo_macro if not math.isnan(raw_pos.auc_ovo_macro) else 0.5
    pos_stok_auc = pos_on_stok.auc_ovo_macro if not math.isnan(pos_on_stok.auc_ovo_macro) else 0.5
    pos_excess_raw = max(0.0, raw_pos_auc - 0.5)
    pos_excess_stok = max(0.0, pos_stok_auc - 0.5)
    tok_chance = 1.0 / max(1.0, float(raw_tok.n_classes))
    tok_excess_raw = max(0.0, raw_tok.top1 - tok_chance)
    tok_excess_spos = max(0.0, tok_on_spos.top1 - tok_chance)
    pos_drop_frac = safe_ratio(pos_excess_raw - pos_excess_stok, max(pos_excess_raw, 1e-8))
    tok_drop_frac = safe_ratio(tok_excess_raw - tok_excess_spos, max(tok_excess_raw, 1e-8))
    c3_v2 = (
        (not math.isnan(pos_drop_frac))
        and (not math.isnan(tok_drop_frac))
        and pos_drop_frac >= c3_v2_drop_fraction
        and tok_drop_frac >= c3_v2_drop_fraction
    )

    # 4) Principal angle median
    c4 = angle_median_deg >= 45.0
    return {
        "criterion_1_position_subspace_auc": bool(c1),
        "criterion_2_token_retention_vs_perp_drop": bool(c2),
        "criterion_2_alt_rank_linear_drop": bool(c2_alt),
        "criterion_2_var_energy_excess": bool(c2_var),
        "criterion_2_var_v2_ratio_excess": bool(c2_var_v2),
        "criterion_3_cross_talk_reduction": bool(c3),
        "criterion_3_v2_chance_corrected": bool(c3_v2),
        "criterion_4_principal_angle": bool(c4),
        "c2_var_ratio": c2_var_ratio,
        "c2_var_threshold": float(c2_var_v2_ratio_threshold),
        "c2_var_excess_floor": float(c2_var_v2_excess_floor),
        "pos_drop_frac_v2": pos_drop_frac,
        "tok_drop_frac_v2": tok_drop_frac,
        "c3_v2_drop_fraction": float(c3_v2_drop_fraction),
        "criterion_1_new_rank_recovery": False,
        "c1_new_rank_recovery": False,
        "rank_at_pos90": None,
        "rank_budget_d_over_8": int(math.ceil(float(hidden_size) / 8.0)),
        "all_pass_recovery_var": False,
        "all_pass_v2": False,
        "all_pass": bool(c1 and c2 and c3 and c4),
        "all_pass_alt_c2": bool(c1 and c2_alt and c3 and c4),
    }


def update_rank_recovery_metrics(
    rank_results: Dict[str, Dict[str, object]],
    rows_by_rank: Dict[int, Dict[str, object]],
    hidden_size: int,
) -> Dict[str, object]:
    available_ranks = sorted(int(k) for k in rank_results.keys())
    rank_budget = int(math.ceil(float(hidden_size) / 8.0))
    rank_at_pos90: int | None = None

    for r in available_ranks:
        rr = rank_results[str(r)]
        raw_pos_auc = float(rr["position_raw"]["auc_ovo_macro"])
        pos_spos_auc = float(rr["position_on_S_pos"]["auc_ovo_macro"])
        raw_tok_top1 = float(rr["token_raw"]["top1"])
        tok_stok_top1 = float(rr["token_on_S_tok"]["top1"])

        pos_auc_recovery = safe_ratio(pos_spos_auc, raw_pos_auc)
        tok_top1_recovery = safe_ratio(tok_stok_top1, raw_tok_top1)
        rr["pos_auc_recovery"] = pos_auc_recovery
        rr["tok_top1_recovery"] = tok_top1_recovery

        if rank_at_pos90 is None and (not math.isnan(pos_auc_recovery)) and pos_auc_recovery >= 0.90:
            rank_at_pos90 = r

    c1_new = bool(rank_at_pos90 is not None and rank_at_pos90 <= rank_budget)

    for r in available_ranks:
        rr = rank_results[str(r)]
        checks = rr["threshold_checks"]
        checks["criterion_1_new_rank_recovery"] = c1_new
        checks["c1_new_rank_recovery"] = c1_new
        checks["rank_at_pos90"] = rank_at_pos90
        checks["rank_budget_d_over_8"] = rank_budget
        checks["all_pass_recovery_var"] = bool(
            c1_new
            and checks["criterion_2_var_energy_excess"]
            and checks["criterion_3_cross_talk_reduction"]
            and checks["criterion_4_principal_angle"]
        )
        checks["all_pass_v2"] = bool(
            c1_new
            and checks["criterion_2_var_v2_ratio_excess"]
            and checks["criterion_3_v2_chance_corrected"]
            and checks["criterion_4_principal_angle"]
        )
        row = rows_by_rank.get(r)
        if row is None:
            continue
        row["pos_auc_recovery"] = float(rr["pos_auc_recovery"])
        row["tok_top1_recovery"] = float(rr["tok_top1_recovery"])
        row["rank_at_pos90"] = "" if rank_at_pos90 is None else int(rank_at_pos90)
        row["rank_budget_d_over_8"] = int(rank_budget)
        row["c1_new_rank_recovery"] = int(checks["criterion_1_new_rank_recovery"])
        row["c2_var_energy_excess"] = int(checks["criterion_2_var_energy_excess"])
        row["c2_var_v2"] = int(checks["criterion_2_var_v2_ratio_excess"])
        row["c3_v2"] = int(checks["criterion_3_v2_chance_corrected"])
        row["all_pass_v2"] = int(checks["all_pass_v2"])
        row["all_pass_recovery_var"] = int(checks["all_pass_recovery_var"])
        row["c2_var_ratio"] = checks["c2_var_ratio"]
        row["c2_var_threshold"] = checks["c2_var_threshold"]
        row["c2_var_excess_floor"] = checks["c2_var_excess_floor"]
        row["pos_drop_frac_v2"] = checks["pos_drop_frac_v2"]
        row["tok_drop_frac_v2"] = checks["tok_drop_frac_v2"]
        row["c3_v2_drop_fraction"] = checks["c3_v2_drop_fraction"]

    return {
        "rank_budget_d_over_8": rank_budget,
        "rank_at_pos90": rank_at_pos90,
        "criterion_1_new_rank_recovery": c1_new,
    }


def metrics_to_dict(m: ProbeMetrics) -> Dict[str, float]:
    return {
        "top1": m.top1,
        "auc_ovo_macro": m.auc_ovo_macro,
        "n_classes": m.n_classes,
        "n_train": m.n_train,
        "n_test": m.n_test,
    }


def diagnostics_to_dict(d: ProbeFitDiagnostics) -> Dict[str, float | bool | str | None]:
    return {
        "n_iter_max": d.n_iter_max,
        "hit_max_iter": d.hit_max_iter,
        "backend": d.backend,
        "elapsed_sec": d.elapsed_sec,
        "final_train_loss": d.final_train_loss,
        "best_eval_top1": d.best_eval_top1,
        "effective_lr": d.effective_lr,
        "scheduler": d.scheduler,
    }


def build_summary(
    args: argparse.Namespace,
    device: torch.device,
    dtype: torch.dtype,
    probe_backend: str,
    stats: Dict[str, int],
    y_pos_remap: np.ndarray,
    y_tok_remap: np.ndarray,
    tok_mapping: Dict[int, int],
    pos_mapping: Dict[int, int],
    rank_results: Dict[str, Dict[str, object]],
    holdout_stats: Dict[str, int] | None = None,
    run_metadata: Dict[str, object] | None = None,
    recovery_meta: Dict[str, object] | None = None,
) -> Dict[str, object]:
    out = {
        "args": vars(args),
        "device": str(device),
        "dtype": str(dtype),
        "probe_backend": probe_backend,
        "collection_stats": stats,
        "position_num_classes_after_filter": int(np.unique(y_pos_remap).shape[0]),
        "token_num_classes_after_filter": int(np.unique(y_tok_remap).shape[0]),
        "token_top_k_mapping_size": len(tok_mapping),
        "position_mapping_size": len(pos_mapping),
        "rank_results": rank_results,
    }
    if holdout_stats is not None:
        out["holdout_collection_stats"] = holdout_stats
    if run_metadata is not None:
        out["run_metadata"] = run_metadata
    if recovery_meta is not None:
        out["recovery_rank_metrics"] = recovery_meta
    return out


def main() -> None:
    args = parse_args()
    args.git_commit_hash = resolve_git_commit_hash(args.git_commit_hash)
    os.makedirs(args.output_dir, exist_ok=True)
    intermediates_dir = None
    if not args.disable_intermediates:
        intermediates_dir = os.path.join(args.output_dir, "intermediates")
        os.makedirs(intermediates_dir, exist_ok=True)

    set_seed(args.seed)

    device = choose_device(args.device)
    dtype = choose_dtype(args.dtype, device)
    probe_backend = choose_probe_backend(args.probe_backend, device)

    torch_cfg_raw = TorchProbeConfig(
        max_steps=int(args.probe_torch_max_steps_raw),
        batch_size=int(args.probe_torch_batch_size),
        lr=float(args.probe_torch_lr),
        weight_decay=float(args.probe_torch_weight_decay),
        eval_every=int(args.probe_torch_eval_every),
        patience=int(args.probe_torch_patience_raw),
        min_steps=int(args.probe_torch_min_steps),
        token_ceiling_top1=float(args.probe_torch_token_ceiling_top1),
        token_ceiling_evals=int(args.probe_torch_token_ceiling_evals),
        token_ceiling_loss_eps=float(args.probe_torch_token_ceiling_loss_eps),
        position_raw_highdim_lr=float(args.probe_torch_lr_position_raw_highdim),
        position_raw_highdim_threshold=int(args.probe_torch_lr_position_raw_highdim_threshold),
        scheduler=str(args.probe_torch_scheduler),
    )
    torch_cfg_projected = TorchProbeConfig(
        max_steps=int(args.probe_torch_max_steps_projected),
        batch_size=int(args.probe_torch_batch_size),
        lr=float(args.probe_torch_lr),
        weight_decay=float(args.probe_torch_weight_decay),
        eval_every=int(args.probe_torch_eval_every),
        patience=int(args.probe_torch_patience_projected),
        min_steps=int(args.probe_torch_min_steps),
        token_ceiling_top1=float(args.probe_torch_token_ceiling_top1),
        token_ceiling_evals=int(args.probe_torch_token_ceiling_evals),
        token_ceiling_loss_eps=float(args.probe_torch_token_ceiling_loss_eps),
        position_raw_highdim_lr=float(args.probe_torch_lr_position_raw_highdim),
        position_raw_highdim_threshold=int(args.probe_torch_lr_position_raw_highdim_threshold),
        scheduler=str(args.probe_torch_scheduler),
    )

    print(
        f"[config] model={args.model_name} device={device} dtype={dtype} "
        f"probe_backend={probe_backend} probe_max_iter={args.probe_max_iter} "
        f"probe_c_raw={args.probe_c_raw} probe_c_projected={args.probe_c_projected} "
        f"torch_steps_raw={torch_cfg_raw.max_steps} torch_steps_projected={torch_cfg_projected.max_steps} "
        f"token_ceiling_top1={torch_cfg_raw.token_ceiling_top1} "
        f"token_ceiling_evals={torch_cfg_raw.token_ceiling_evals} "
        f"pos_raw_highdim_lr={torch_cfg_raw.position_raw_highdim_lr} "
        f"scheduler={torch_cfg_raw.scheduler}"
    )

    tokenizer = AutoTokenizer.from_pretrained(args.model_name, use_fast=True)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token

    model = AutoModelForCausalLM.from_pretrained(
        args.model_name,
        dtype=dtype,
        low_cpu_mem_usage=True,
    )
    model.to(device)
    model.eval()
    model.config.use_cache = False

    holdout_plan = resolve_holdout_plan(args)
    train_texts = holdout_plan["train_texts"]
    eval_texts = holdout_plan["eval_texts"]

    X_train_raw, y_pos_train_raw, y_tok_train_raw, stats = collect_token_level_activations(
        model=model,
        model_name=args.model_name,
        tokenizer=tokenizer,
        texts=train_texts,
        device=device,
        context_length=args.context_length,
        batch_size=args.batch_size,
        layer_index=args.layer_index,
        position_max=args.position_max,
        max_tokens_collect=args.max_tokens_collect,
        skip_first_position=args.skip_first_position,
    )

    print(
        f"[collect-train] tokens={stats['n_tokens_collected']} hidden_size={stats['hidden_size']} "
        f"n_batches={stats['n_batches']} split_mode={args.split_mode}"
    )

    X_eval_raw = None
    y_pos_eval_raw = None
    y_tok_eval_raw = None
    holdout_stats = None
    if eval_texts is not None:
        X_eval_raw, y_pos_eval_raw, y_tok_eval_raw, holdout_stats = collect_token_level_activations(
            model=model,
            model_name=args.model_name,
            tokenizer=tokenizer,
            texts=eval_texts,
            device=device,
            context_length=args.context_length,
            batch_size=args.batch_size,
            layer_index=args.layer_index,
            position_max=args.position_max,
            max_tokens_collect=args.holdout_eval_max_tokens_collect,
            skip_first_position=args.skip_first_position,
        )
        print(
            f"[collect-eval] tokens={holdout_stats['n_tokens_collected']} "
            f"hidden_size={holdout_stats['hidden_size']} n_batches={holdout_stats['n_batches']}"
        )
    run_metadata = {
        "seed": int(args.seed),
        "git_commit_hash": args.git_commit_hash,
        "split_mode": args.split_mode,
        "holdout_source_label": str(holdout_plan.get("holdout_source_label", "")),
        "corpus_holdout_dataset_name": str(holdout_plan.get("corpus_holdout_dataset_name", "")),
        "source_manifest_hash": str(holdout_plan.get("manifest_hash", "")),
        "c2_var_v2_ratio_threshold": float(args.c2_var_v2_ratio_threshold),
        "c2_var_v2_excess_floor": float(args.c2_var_v2_excess_floor),
        "c3_v2_drop_fraction": float(args.c3_v2_drop_fraction),
        "probe_torch_scheduler": str(args.probe_torch_scheduler),
        "probe_torch_lr": float(args.probe_torch_lr),
        "probe_torch_lr_position_raw_highdim": float(args.probe_torch_lr_position_raw_highdim),
        "probe_torch_lr_position_raw_highdim_threshold": int(args.probe_torch_lr_position_raw_highdim_threshold),
        "train_source_counts": dict(Counter(holdout_plan.get("train_sources", []))),
        "eval_source_counts": dict(Counter(holdout_plan.get("eval_sources", []))),
    }

    # Release model memory before probe training to maximize GPU memory for probes.
    del model
    if torch.cuda.is_available():
        torch.cuda.empty_cache()

    # Filter token identity task to top-K frequent tokens
    tok_mask_train = top_k_token_filter(y_tok_train_raw, args.top_k_tokens)
    X_train_shared = X_train_raw[tok_mask_train]
    y_pos_train_shared = y_pos_train_raw[tok_mask_train]
    y_tok_train_shared = y_tok_train_raw[tok_mask_train]
    top_tok_ids = set(int(v) for v in np.unique(y_tok_train_shared).tolist())

    X_eval_shared = None
    y_pos_eval_shared = None
    y_tok_eval_shared = None
    if X_eval_raw is not None and y_tok_eval_raw is not None and y_pos_eval_raw is not None:
        tok_mask_eval = np.array([int(t) in top_tok_ids for t in y_tok_eval_raw.tolist()], dtype=bool)
        X_eval_shared = X_eval_raw[tok_mask_eval]
        y_pos_eval_shared = y_pos_eval_raw[tok_mask_eval]
        y_tok_eval_shared = y_tok_eval_raw[tok_mask_eval]

    X_pos, y_pos_task = filter_min_examples_per_class(
        X_train_shared,
        y_pos_train_shared,
        args.min_examples_per_class,
    )
    X_tok, y_tok_task = filter_min_examples_per_class(
        X_train_shared,
        y_tok_train_shared,
        args.min_examples_per_class,
    )
    y_pos_remap, pos_mapping = remap_labels(y_pos_task)
    y_tok_remap, tok_mapping = remap_labels(y_tok_task)

    X_pos_eval = None
    y_pos_eval_task = None
    X_tok_eval = None
    y_tok_eval_task = None
    if X_eval_shared is not None and y_pos_eval_shared is not None and y_tok_eval_shared is not None:
        y_pos_eval_remap, pos_eval_mask = remap_with_existing_mapping(y_pos_eval_shared, pos_mapping)
        y_tok_eval_remap, tok_eval_mask = remap_with_existing_mapping(y_tok_eval_shared, tok_mapping)
        if np.any(pos_eval_mask):
            X_pos_eval = X_eval_shared[pos_eval_mask]
            y_pos_eval_task = y_pos_eval_shared[pos_eval_mask]
        if np.any(tok_eval_mask):
            X_tok_eval = X_eval_shared[tok_eval_mask]
            y_tok_eval_task = y_tok_eval_shared[tok_eval_mask]

    if X_pos.shape[0] < args.min_samples_after_filter or X_tok.shape[0] < args.min_samples_after_filter:
        raise RuntimeError(
            f"Not enough filtered data after class-balancing. "
            f"Position samples={X_pos.shape[0]}, token samples={X_tok.shape[0]}. "
            f"Try increasing --max_tokens_collect/--max_text_samples or lowering "
            f"--min_examples_per_class/--min_samples_after_filter."
        )
    if eval_texts is not None:
        if X_pos_eval is None or y_pos_eval_task is None or X_pos_eval.shape[0] == 0:
            raise RuntimeError("No position eval samples survived holdout filtering/mapping.")
        if X_tok_eval is None or y_tok_eval_task is None or X_tok_eval.shape[0] == 0:
            raise RuntimeError("No token eval samples survived holdout filtering/mapping.")

    print(
        f"[filtered] position_samples={X_pos.shape[0]} token_samples={X_tok.shape[0]} "
        f"position_classes={np.unique(y_pos_remap).shape[0]} token_classes={np.unique(y_tok_remap).shape[0]}"
    )
    if eval_texts is not None and X_pos_eval is not None and X_tok_eval is not None:
        print(
            f"[filtered-eval] position_samples={X_pos_eval.shape[0]} token_samples={X_tok_eval.shape[0]} "
            f"split_mode={args.split_mode}"
        )

    use_gpu_projection = probe_backend == "torch" and device.type == "cuda"
    X_pos_t: torch.Tensor | None = None
    X_tok_t: torch.Tensor | None = None
    X_pos_eval_t: torch.Tensor | None = None
    X_tok_eval_t: torch.Tensor | None = None
    if use_gpu_projection:
        X_pos_t = torch.from_numpy(X_pos.astype(np.float32)).to(device)
        X_tok_t = torch.from_numpy(X_tok.astype(np.float32)).to(device)
        if X_pos_eval is not None:
            X_pos_eval_t = torch.from_numpy(X_pos_eval.astype(np.float32)).to(device)
        if X_tok_eval is not None:
            X_tok_eval_t = torch.from_numpy(X_tok_eval.astype(np.float32)).to(device)

    # Raw probes
    pos_eval_override = None
    tok_eval_override = None
    if y_pos_eval_task is not None:
        pos_eval_override = (
            X_pos_eval_t if X_pos_eval_t is not None else X_pos_eval,
            y_pos_eval_task,
        )
    if y_tok_eval_task is not None:
        tok_eval_override = (
            X_tok_eval_t if X_tok_eval_t is not None else X_tok_eval,
            y_tok_eval_task,
        )

    pos_raw_metrics, pos_probe_w, pos_raw_diag = train_eval_probe(
        X_pos_t if X_pos_t is not None else X_pos,
        y_pos_task,
        args.train_frac,
        args.seed,
        args.probe_max_iter,
        args.probe_c_raw,
        probe_backend=probe_backend,
        probe_device=device,
        torch_cfg=torch_cfg_raw,
        probe_name="position_raw",
        intermediates_dir=intermediates_dir,
        eval_override=pos_eval_override,
    )
    tok_raw_metrics, tok_probe_w, tok_raw_diag = train_eval_probe(
        X_tok_t if X_tok_t is not None else X_tok,
        y_tok_task,
        args.train_frac,
        args.seed,
        args.probe_max_iter,
        args.probe_c_raw,
        probe_backend=probe_backend,
        probe_device=device,
        torch_cfg=torch_cfg_raw,
        probe_name="token_raw",
        intermediates_dir=intermediates_dir,
        eval_override=tok_eval_override,
    )

    if intermediates_dir is not None:
        atomic_write_json(
            os.path.join(intermediates_dir, "raw_probe_metrics.json"),
            {
                "position_raw": metrics_to_dict(pos_raw_metrics),
                "token_raw": metrics_to_dict(tok_raw_metrics),
                "run_metadata": run_metadata,
                "fit_diagnostics": {
                    "position_raw": diagnostics_to_dict(pos_raw_diag),
                    "token_raw": diagnostics_to_dict(tok_raw_diag),
                },
            },
        )

    ranks = [int(r.strip()) for r in args.probe_ranks.split(",") if r.strip()]
    rank_results: Dict[str, Dict[str, object]] = {}
    rows_for_csv_by_rank: Dict[int, Dict[str, object]] = {}
    recovery_meta: Dict[str, object] = {
        "rank_budget_d_over_8": int(math.ceil(float(stats["hidden_size"]) / 8.0)),
        "rank_at_pos90": None,
        "criterion_1_new_rank_recovery": False,
    }

    for r in ranks:
        print(f"[rank] begin rank={r}")
        pos_spos_eval_override = None
        pos_spos_perp_eval_override = None
        pos_stok_eval_override = None
        tok_stok_eval_override = None
        tok_stok_perp_eval_override = None
        tok_spos_eval_override = None

        if use_gpu_projection and X_pos_t is not None and X_tok_t is not None:
            s_pos_t = basis_from_probe_torch(pos_probe_w, r, device)
            s_tok_t = basis_from_probe_torch(tok_probe_w, r, device)
            s_pos = s_pos_t.detach().cpu().numpy().astype(np.float64)
            s_tok = s_tok_t.detach().cpu().numpy().astype(np.float64)

            # Projected representations (GPU path)
            X_pos_on_spos = project_to_basis_torch(X_pos_t, s_pos_t)
            X_pos_on_spos_perp = orthogonal_complement_projection_torch(X_pos_t, s_pos_t)
            X_pos_on_stok = project_to_basis_torch(X_pos_t, s_tok_t)

            X_tok_on_stok = project_to_basis_torch(X_tok_t, s_tok_t)
            X_tok_on_stok_perp = orthogonal_complement_projection_torch(X_tok_t, s_tok_t)
            X_tok_on_spos = project_to_basis_torch(X_tok_t, s_pos_t)

            if X_pos_eval_t is not None and y_pos_eval_task is not None:
                X_pos_eval_on_spos = project_to_basis_torch(X_pos_eval_t, s_pos_t)
                X_pos_eval_on_spos_perp = orthogonal_complement_projection_torch(X_pos_eval_t, s_pos_t)
                X_pos_eval_on_stok = project_to_basis_torch(X_pos_eval_t, s_tok_t)
                pos_spos_eval_override = (X_pos_eval_on_spos, y_pos_eval_task)
                pos_spos_perp_eval_override = (X_pos_eval_on_spos_perp, y_pos_eval_task)
                pos_stok_eval_override = (X_pos_eval_on_stok, y_pos_eval_task)

            if X_tok_eval_t is not None and y_tok_eval_task is not None:
                X_tok_eval_on_stok = project_to_basis_torch(X_tok_eval_t, s_tok_t)
                X_tok_eval_on_stok_perp = orthogonal_complement_projection_torch(X_tok_eval_t, s_tok_t)
                X_tok_eval_on_spos = project_to_basis_torch(X_tok_eval_t, s_pos_t)
                tok_stok_eval_override = (X_tok_eval_on_stok, y_tok_eval_task)
                tok_stok_perp_eval_override = (X_tok_eval_on_stok_perp, y_tok_eval_task)
                tok_spos_eval_override = (X_tok_eval_on_spos, y_tok_eval_task)
        else:
            s_pos = basis_from_probe(pos_probe_w, r)
            s_tok = basis_from_probe(tok_probe_w, r)

            # Projected representations (CPU fallback path)
            X_pos_on_spos = project_to_basis(X_pos, s_pos)
            X_pos_on_spos_perp = orthogonal_complement_projection(X_pos, s_pos)
            X_pos_on_stok = project_to_basis(X_pos, s_tok)

            X_tok_on_stok = project_to_basis(X_tok, s_tok)
            X_tok_on_stok_perp = orthogonal_complement_projection(X_tok, s_tok)
            X_tok_on_spos = project_to_basis(X_tok, s_pos)

            if X_pos_eval is not None and y_pos_eval_task is not None:
                X_pos_eval_on_spos = project_to_basis(X_pos_eval, s_pos)
                X_pos_eval_on_spos_perp = orthogonal_complement_projection(X_pos_eval, s_pos)
                X_pos_eval_on_stok = project_to_basis(X_pos_eval, s_tok)
                pos_spos_eval_override = (X_pos_eval_on_spos, y_pos_eval_task)
                pos_spos_perp_eval_override = (X_pos_eval_on_spos_perp, y_pos_eval_task)
                pos_stok_eval_override = (X_pos_eval_on_stok, y_pos_eval_task)

            if X_tok_eval is not None and y_tok_eval_task is not None:
                X_tok_eval_on_stok = project_to_basis(X_tok_eval, s_tok)
                X_tok_eval_on_stok_perp = orthogonal_complement_projection(X_tok_eval, s_tok)
                X_tok_eval_on_spos = project_to_basis(X_tok_eval, s_pos)
                tok_stok_eval_override = (X_tok_eval_on_stok, y_tok_eval_task)
                tok_stok_perp_eval_override = (X_tok_eval_on_stok_perp, y_tok_eval_task)
                tok_spos_eval_override = (X_tok_eval_on_spos, y_tok_eval_task)

        causal_metrics: Dict[str, Dict[str, float]] = {}
        if not args.disable_causal_sanity:
            if use_gpu_projection and X_pos_t is not None and X_tok_t is not None:
                pos_eval_x_spos = X_pos_eval_on_spos if (X_pos_eval_t is not None and y_pos_eval_task is not None) else X_pos_on_spos
                pos_eval_x_spos_perp = (
                    X_pos_eval_on_spos_perp if (X_pos_eval_t is not None and y_pos_eval_task is not None) else X_pos_on_spos_perp
                )
                pos_eval_x_stok = X_pos_eval_on_stok if (X_pos_eval_t is not None and y_pos_eval_task is not None) else X_pos_on_stok
                tok_eval_x_stok = X_tok_eval_on_stok if (X_tok_eval_t is not None and y_tok_eval_task is not None) else X_tok_on_stok
                tok_eval_x_stok_perp = (
                    X_tok_eval_on_stok_perp if (X_tok_eval_t is not None and y_tok_eval_task is not None) else X_tok_on_stok_perp
                )
                tok_eval_x_spos = X_tok_eval_on_spos if (X_tok_eval_t is not None and y_tok_eval_task is not None) else X_tok_on_spos
                pos_eval_y = y_pos_eval_task if y_pos_eval_task is not None else y_pos_task
                tok_eval_y = y_tok_eval_task if y_tok_eval_task is not None else y_tok_task
                causal_pos_spos = eval_frozen_probe_metrics(
                    pos_probe_w,
                    y_pos_task,
                    pos_eval_x_spos.detach().cpu().numpy(),
                    pos_eval_y,
                )
                causal_pos_spos_perp = eval_frozen_probe_metrics(
                    pos_probe_w,
                    y_pos_task,
                    pos_eval_x_spos_perp.detach().cpu().numpy(),
                    pos_eval_y,
                )
                causal_pos_stok = eval_frozen_probe_metrics(
                    pos_probe_w,
                    y_pos_task,
                    pos_eval_x_stok.detach().cpu().numpy(),
                    pos_eval_y,
                )
                causal_tok_stok = eval_frozen_probe_metrics(
                    tok_probe_w,
                    y_tok_task,
                    tok_eval_x_stok.detach().cpu().numpy(),
                    tok_eval_y,
                )
                causal_tok_stok_perp = eval_frozen_probe_metrics(
                    tok_probe_w,
                    y_tok_task,
                    tok_eval_x_stok_perp.detach().cpu().numpy(),
                    tok_eval_y,
                )
                causal_tok_spos = eval_frozen_probe_metrics(
                    tok_probe_w,
                    y_tok_task,
                    tok_eval_x_spos.detach().cpu().numpy(),
                    tok_eval_y,
                )
            else:
                pos_eval_x_spos = X_pos_eval_on_spos if (X_pos_eval is not None and y_pos_eval_task is not None) else X_pos_on_spos
                pos_eval_x_spos_perp = (
                    X_pos_eval_on_spos_perp if (X_pos_eval is not None and y_pos_eval_task is not None) else X_pos_on_spos_perp
                )
                pos_eval_x_stok = X_pos_eval_on_stok if (X_pos_eval is not None and y_pos_eval_task is not None) else X_pos_on_stok
                tok_eval_x_stok = X_tok_eval_on_stok if (X_tok_eval is not None and y_tok_eval_task is not None) else X_tok_on_stok
                tok_eval_x_stok_perp = (
                    X_tok_eval_on_stok_perp if (X_tok_eval is not None and y_tok_eval_task is not None) else X_tok_on_stok_perp
                )
                tok_eval_x_spos = X_tok_eval_on_spos if (X_tok_eval is not None and y_tok_eval_task is not None) else X_tok_on_spos
                pos_eval_y = y_pos_eval_task if y_pos_eval_task is not None else y_pos_task
                tok_eval_y = y_tok_eval_task if y_tok_eval_task is not None else y_tok_task
                causal_pos_spos = eval_frozen_probe_metrics(pos_probe_w, y_pos_task, pos_eval_x_spos, pos_eval_y)
                causal_pos_spos_perp = eval_frozen_probe_metrics(
                    pos_probe_w, y_pos_task, pos_eval_x_spos_perp, pos_eval_y
                )
                causal_pos_stok = eval_frozen_probe_metrics(pos_probe_w, y_pos_task, pos_eval_x_stok, pos_eval_y)
                causal_tok_stok = eval_frozen_probe_metrics(tok_probe_w, y_tok_task, tok_eval_x_stok, tok_eval_y)
                causal_tok_stok_perp = eval_frozen_probe_metrics(
                    tok_probe_w, y_tok_task, tok_eval_x_stok_perp, tok_eval_y
                )
                causal_tok_spos = eval_frozen_probe_metrics(tok_probe_w, y_tok_task, tok_eval_x_spos, tok_eval_y)
            causal_metrics = {
                "position_raw_probe_on_S_pos": metrics_to_dict(causal_pos_spos),
                "position_raw_probe_on_S_pos_perp": metrics_to_dict(causal_pos_spos_perp),
                "position_raw_probe_on_S_tok": metrics_to_dict(causal_pos_stok),
                "token_raw_probe_on_S_tok": metrics_to_dict(causal_tok_stok),
                "token_raw_probe_on_S_tok_perp": metrics_to_dict(causal_tok_stok_perp),
                "token_raw_probe_on_S_pos": metrics_to_dict(causal_tok_spos),
            }

        # Train/eval probes on projected reps
        pos_spos, _, pos_spos_diag = train_eval_probe(
            X_pos_on_spos,
            y_pos_task,
            args.train_frac,
            args.seed,
            args.probe_max_iter,
            args.probe_c_projected,
            probe_backend=probe_backend,
            probe_device=device,
            torch_cfg=torch_cfg_projected,
            probe_name=f"position_on_spos_r{r}",
            intermediates_dir=intermediates_dir,
            eval_override=pos_spos_eval_override,
        )
        pos_spos_perp, _, pos_spos_perp_diag = train_eval_probe(
            X_pos_on_spos_perp,
            y_pos_task,
            args.train_frac,
            args.seed,
            args.probe_max_iter,
            args.probe_c_projected,
            probe_backend=probe_backend,
            probe_device=device,
            torch_cfg=torch_cfg_projected,
            probe_name=f"position_on_spos_perp_r{r}",
            intermediates_dir=intermediates_dir,
            eval_override=pos_spos_perp_eval_override,
        )
        pos_stok, _, pos_stok_diag = train_eval_probe(
            X_pos_on_stok,
            y_pos_task,
            args.train_frac,
            args.seed,
            args.probe_max_iter,
            args.probe_c_projected,
            probe_backend=probe_backend,
            probe_device=device,
            torch_cfg=torch_cfg_projected,
            probe_name=f"position_on_stok_r{r}",
            intermediates_dir=intermediates_dir,
            eval_override=pos_stok_eval_override,
        )

        tok_stok, _, tok_stok_diag = train_eval_probe(
            X_tok_on_stok,
            y_tok_task,
            args.train_frac,
            args.seed,
            args.probe_max_iter,
            args.probe_c_projected,
            probe_backend=probe_backend,
            probe_device=device,
            torch_cfg=torch_cfg_projected,
            probe_name=f"token_on_stok_r{r}",
            intermediates_dir=intermediates_dir,
            eval_override=tok_stok_eval_override,
        )
        tok_stok_perp, _, tok_stok_perp_diag = train_eval_probe(
            X_tok_on_stok_perp,
            y_tok_task,
            args.train_frac,
            args.seed,
            args.probe_max_iter,
            args.probe_c_projected,
            probe_backend=probe_backend,
            probe_device=device,
            torch_cfg=torch_cfg_projected,
            probe_name=f"token_on_stok_perp_r{r}",
            intermediates_dir=intermediates_dir,
            eval_override=tok_stok_perp_eval_override,
        )
        tok_spos, _, tok_spos_diag = train_eval_probe(
            X_tok_on_spos,
            y_tok_task,
            args.train_frac,
            args.seed,
            args.probe_max_iter,
            args.probe_c_projected,
            probe_backend=probe_backend,
            probe_device=device,
            torch_cfg=torch_cfg_projected,
            probe_name=f"token_on_spos_r{r}",
            intermediates_dir=intermediates_dir,
            eval_override=tok_spos_eval_override,
        )

        if use_gpu_projection and X_pos_t is not None and X_tok_t is not None:
            angles = principal_angle_summary_torch(s_pos_t, s_tok_t)
            xproj = cross_projection_energy_torch(s_pos_t, s_tok_t)
            tok_energy_ratio = projection_energy_ratio_torch(X_tok_on_stok, X_tok_t)
        else:
            angles = principal_angle_summary(s_pos, s_tok)
            xproj = cross_projection_energy(s_pos, s_tok)
            tok_energy_ratio = projection_energy_ratio(X_tok_on_stok, X_tok)

        xproj_norm = normalized_cross_projection_energy(
            xproj, rank_a=int(s_pos.shape[1]), rank_b=int(s_tok.shape[1])
        )
        tok_energy_baseline = float(r) / float(stats["hidden_size"])
        tok_energy_excess = float(tok_energy_ratio - tok_energy_baseline)
        checks = check_thresholds(
            raw_pos=pos_raw_metrics,
            raw_tok=tok_raw_metrics,
            pos_on_spos=pos_spos,
            pos_on_spos_perp=pos_spos_perp,
            tok_on_stok=tok_stok,
            tok_on_stok_perp=tok_stok_perp,
            tok_on_spos=tok_spos,
            pos_on_stok=pos_stok,
            angle_median_deg=angles["median_angle_deg"],
            rank=r,
            hidden_size=stats["hidden_size"],
            c2_alt_mode=args.c2_alt_mode,
            tok_energy_excess=tok_energy_excess,
            tok_energy_ratio=tok_energy_ratio,
            c2_var_v2_ratio_threshold=float(args.c2_var_v2_ratio_threshold),
            c2_var_v2_excess_floor=float(args.c2_var_v2_excess_floor),
            c3_v2_drop_fraction=float(args.c3_v2_drop_fraction),
        )

        rank_results[str(r)] = {
            "position_raw": metrics_to_dict(pos_raw_metrics),
            "token_raw": metrics_to_dict(tok_raw_metrics),
            "position_on_S_pos": metrics_to_dict(pos_spos),
            "position_on_S_pos_perp": metrics_to_dict(pos_spos_perp),
            "position_on_S_tok": metrics_to_dict(pos_stok),
            "token_on_S_tok": metrics_to_dict(tok_stok),
            "token_on_S_tok_perp": metrics_to_dict(tok_stok_perp),
            "token_on_S_pos": metrics_to_dict(tok_spos),
            "principal_angles_deg": angles,
            "cross_projection_energy_fro": xproj,
            "cross_projection_energy_normalized": xproj_norm,
            "tok_energy_ratio": tok_energy_ratio,
            "tok_energy_baseline": tok_energy_baseline,
            "tok_energy_excess": tok_energy_excess,
            "fit_diagnostics": {
                "position_raw": diagnostics_to_dict(pos_raw_diag),
                "token_raw": diagnostics_to_dict(tok_raw_diag),
                "position_on_S_pos": diagnostics_to_dict(pos_spos_diag),
                "position_on_S_pos_perp": diagnostics_to_dict(pos_spos_perp_diag),
                "position_on_S_tok": diagnostics_to_dict(pos_stok_diag),
                "token_on_S_tok": diagnostics_to_dict(tok_stok_diag),
                "token_on_S_tok_perp": diagnostics_to_dict(tok_stok_perp_diag),
                "token_on_S_pos": diagnostics_to_dict(tok_spos_diag),
            },
            "causal_sanity_frozen": causal_metrics,
            "threshold_checks": checks,
        }

        rows_for_csv_by_rank[r] = {
            "rank": r,
            "all_pass": int(checks["all_pass"]),
            "c1_position_subspace_auc": int(checks["criterion_1_position_subspace_auc"]),
            "c2_token_retention_vs_perp_drop": int(checks["criterion_2_token_retention_vs_perp_drop"]),
            "c2_alt_rank_linear_drop": int(checks["criterion_2_alt_rank_linear_drop"]),
            "c2_var_energy_excess": int(checks["criterion_2_var_energy_excess"]),
            "c2_var_v2": int(checks["criterion_2_var_v2_ratio_excess"]),
            "c3_cross_talk_reduction": int(checks["criterion_3_cross_talk_reduction"]),
            "c3_v2": int(checks["criterion_3_v2_chance_corrected"]),
            "c4_principal_angle": int(checks["criterion_4_principal_angle"]),
            "all_pass_alt_c2": int(checks["all_pass_alt_c2"]),
            "all_pass_v2": 0,
            "all_pass_recovery_var": 0,
            "c1_new_rank_recovery": 0,
            "rank_at_pos90": "",
            "rank_budget_d_over_8": int(math.ceil(float(stats["hidden_size"]) / 8.0)),
            "raw_pos_auc": pos_raw_metrics.auc_ovo_macro,
            "raw_tok_top1": tok_raw_metrics.top1,
            "pos_spos_auc": pos_spos.auc_ovo_macro,
            "pos_spos_perp_auc": pos_spos_perp.auc_ovo_macro,
            "pos_auc_recovery": float("nan"),
            "tok_stok_top1": tok_stok.top1,
            "tok_stok_perp_top1": tok_stok_perp.top1,
            "tok_top1_recovery": float("nan"),
            "tok_spos_top1": tok_spos.top1,
            "pos_stok_auc": pos_stok.auc_ovo_macro,
            "tok_energy_ratio": tok_energy_ratio,
            "tok_energy_baseline": tok_energy_baseline,
            "tok_energy_excess": tok_energy_excess,
            "c2_var_ratio": checks["c2_var_ratio"],
            "c2_var_threshold": checks["c2_var_threshold"],
            "c2_var_excess_floor": checks["c2_var_excess_floor"],
            "pos_drop_frac_v2": checks["pos_drop_frac_v2"],
            "tok_drop_frac_v2": checks["tok_drop_frac_v2"],
            "c3_v2_drop_fraction": checks["c3_v2_drop_fraction"],
            "principal_median_angle_deg": angles["median_angle_deg"],
            "cross_projection_energy_fro": xproj,
            "cross_projection_energy_normalized": xproj_norm,
            "position_raw_n_iter_max": pos_raw_diag.n_iter_max,
            "position_raw_hit_max_iter": int(pos_raw_diag.hit_max_iter),
            "token_raw_n_iter_max": tok_raw_diag.n_iter_max,
            "token_raw_hit_max_iter": int(tok_raw_diag.hit_max_iter),
            "probe_backend": probe_backend,
            "seed": int(args.seed),
            "split_mode": args.split_mode,
            "git_commit_hash": args.git_commit_hash,
            "probe_torch_scheduler": args.probe_torch_scheduler,
            "position_raw_effective_lr": pos_raw_diag.effective_lr if pos_raw_diag.effective_lr is not None else float("nan"),
            "token_raw_effective_lr": tok_raw_diag.effective_lr if tok_raw_diag.effective_lr is not None else float("nan"),
            "causal_pos_raw_on_spos_auc": float(
                causal_metrics.get("position_raw_probe_on_S_pos", {}).get("auc_ovo_macro", float("nan"))
            ),
            "causal_pos_raw_on_spos_perp_auc": float(
                causal_metrics.get("position_raw_probe_on_S_pos_perp", {}).get("auc_ovo_macro", float("nan"))
            ),
            "causal_pos_raw_on_stok_auc": float(
                causal_metrics.get("position_raw_probe_on_S_tok", {}).get("auc_ovo_macro", float("nan"))
            ),
            "causal_tok_raw_on_stok_top1": float(
                causal_metrics.get("token_raw_probe_on_S_tok", {}).get("top1", float("nan"))
            ),
            "causal_tok_raw_on_stok_perp_top1": float(
                causal_metrics.get("token_raw_probe_on_S_tok_perp", {}).get("top1", float("nan"))
            ),
            "causal_tok_raw_on_spos_top1": float(
                causal_metrics.get("token_raw_probe_on_S_pos", {}).get("top1", float("nan"))
            ),
        }

        if use_gpu_projection and X_pos_t is not None and X_tok_t is not None:
            del (
                s_pos_t,
                s_tok_t,
                X_pos_on_spos,
                X_pos_on_spos_perp,
                X_pos_on_stok,
                X_tok_on_stok,
                X_tok_on_stok_perp,
                X_tok_on_spos,
            )
            torch.cuda.empty_cache()

        recovery_meta = update_rank_recovery_metrics(
            rank_results=rank_results,
            rows_by_rank=rows_for_csv_by_rank,
            hidden_size=stats["hidden_size"],
        )

        if intermediates_dir is not None:
            atomic_write_json(os.path.join(intermediates_dir, f"rank_{r}_result.json"), rank_results[str(r)])
            rows_for_csv = [rows_for_csv_by_rank[rr] for rr in sorted(rows_for_csv_by_rank)]
            partial_summary = build_summary(
                args=args,
                device=device,
                dtype=dtype,
                probe_backend=probe_backend,
                stats=stats,
                y_pos_remap=y_pos_remap,
                y_tok_remap=y_tok_remap,
                tok_mapping=tok_mapping,
                pos_mapping=pos_mapping,
                rank_results=rank_results,
                holdout_stats=holdout_stats,
                run_metadata=run_metadata,
                recovery_meta=recovery_meta,
            )
            atomic_write_json(os.path.join(intermediates_dir, "partial_summary.json"), partial_summary)
            write_rows_csv(os.path.join(intermediates_dir, "partial_rank_table.csv"), rows_for_csv)

        print(
            f"[rank] done rank={r} all_pass={int(checks['all_pass'])} "
            f"all_pass_alt_c2={int(checks['all_pass_alt_c2'])} "
            f"all_pass_v2={int(checks['all_pass_v2'])}"
        )

    rows_for_csv = [rows_for_csv_by_rank[rr] for rr in sorted(rows_for_csv_by_rank)]
    recovery_meta = update_rank_recovery_metrics(
        rank_results=rank_results,
        rows_by_rank=rows_for_csv_by_rank,
        hidden_size=stats["hidden_size"],
    )

    summary = build_summary(
        args=args,
        device=device,
        dtype=dtype,
        probe_backend=probe_backend,
        stats=stats,
        y_pos_remap=y_pos_remap,
        y_tok_remap=y_tok_remap,
        tok_mapping=tok_mapping,
        pos_mapping=pos_mapping,
        rank_results=rank_results,
        holdout_stats=holdout_stats,
        run_metadata=run_metadata,
        recovery_meta=recovery_meta,
    )

    json_path = os.path.join(args.output_dir, "raw_sep_summary.json")
    atomic_write_json(json_path, summary)

    csv_path = os.path.join(args.output_dir, "raw_sep_rank_table.csv")
    write_rows_csv(csv_path, rows_for_csv)

    print(f"[done] wrote {json_path}")
    print(f"[done] wrote {csv_path}")
    print("[summary] per-rank all_pass flags:")
    for row in rows_for_csv:
        print(
            f"  rank={row['rank']}: all_pass={row['all_pass']} "
            f"all_pass_alt_c2={row['all_pass_alt_c2']} "
            f"all_pass_recovery_var={row['all_pass_recovery_var']} "
            f"all_pass_v2={row['all_pass_v2']}"
        )


if __name__ == "__main__":
    main()
