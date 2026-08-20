#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
import random
import statistics
import subprocess
import time
import urllib.request
from urllib.error import URLError
from collections import Counter, defaultdict
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
DROP_LABEL = "__DROP__"
WIKINEURAL_TAG_NAMES = [
    "O",
    "B-PER",
    "I-PER",
    "B-ORG",
    "I-ORG",
    "B-LOC",
    "I-LOC",
    "B-MISC",
    "I-MISC",
]
TASK_TO_FAMILY = {
    "pos_ud_ewt": "syntax_pos",
    "pos_ambig_ud_ewt": "syntax_pos",
    "deprel_ud_ewt": "syntax_dep",
    "deprel_coarse_ud_ewt": "syntax_dep",
    "head_dir_dist_ud_ewt": "syntax_dep",
    "number_ud_ewt": "syntax_morph",
    "ner_wnut17": "sem_wnut",
    "ner_fewnerd_coarse": "sem_fewnerd",
    "ner_wikineural_en": "sem_wikineural",
}


@dataclass
class TaskDataset:
    name: str
    family: str
    metric_name: str
    label_names: list[str]
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


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Stage A1 PCC audit on existing K=2 checkpoints")
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
        return subprocess.check_output(["git", "rev-parse", "HEAD"], stderr=subprocess.DEVNULL, text=True).strip()
    except Exception:
        return ""


def ensure_download(url: str, dst: Path) -> Path:
    dst.parent.mkdir(parents=True, exist_ok=True)
    if dst.exists() and dst.stat().st_size > 0:
        return dst
    tmp = dst.with_suffix(dst.suffix + ".tmp")
    last_err: Exception | None = None
    for _attempt in range(3):
        try:
            with urllib.request.urlopen(url, timeout=60) as r, open(tmp, "wb") as f:
                f.write(r.read())
            tmp.replace(dst)
            return dst
        except (URLError, ConnectionError, TimeoutError, OSError) as e:
            last_err = e
            if tmp.exists():
                tmp.unlink(missing_ok=True)
            time.sleep(2.0)
    if last_err is not None:
        raise last_err
    return dst


def bucket_signed_distance(tok_idx: int, head_idx: int | None) -> str:
    if head_idx is None:
        return "ROOT"
    dist = head_idx - tok_idx
    side = "L" if dist < 0 else "R"
    mag = abs(dist)
    if mag <= 1:
        return f"{side}1"
    if mag == 2:
        return f"{side}2"
    if 3 <= mag <= 4:
        return f"{side}3_4"
    return f"{side}5p"


def parse_conllu(path: Path, max_sentences: int) -> list[dict[str, Any]]:
    examples: list[dict[str, Any]] = []
    rows: list[tuple[int, str, str, int, str, str]] = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.rstrip("\n")
            if not line:
                if rows:
                    ids = [r[0] for r in rows]
                    id_to_pos = {tid: i for i, tid in enumerate(ids)}
                    words = [r[1] for r in rows]
                    lower = [r[1].lower() for r in rows]
                    pos = [r[2] for r in rows]
                    heads = [r[3] for r in rows]
                    deprel = [r[4] for r in rows]
                    number = [r[5] for r in rows]
                    head_dir_dist = [bucket_signed_distance(i, id_to_pos.get(h) if h != 0 else None) for i, h in enumerate(heads)]
                    deprel_coarse = [d.split(":", 1)[0] for d in deprel]
                    examples.append(
                        {
                            "words": words,
                            "word_lower": lower,
                            "pos": pos,
                            "deprel": deprel,
                            "deprel_coarse": deprel_coarse,
                            "number": number,
                            "head_dir_dist": head_dir_dist,
                        }
                    )
                    if len(examples) >= max_sentences:
                        break
                rows = []
                continue
            if line.startswith("#"):
                continue
            parts = line.split("\t")
            if len(parts) != 10:
                continue
            tok_id = parts[0]
            if "-" in tok_id or "." in tok_id:
                continue
            tid = int(tok_id)
            form = parts[1]
            upos = parts[3]
            head = int(parts[6]) if parts[6].isdigit() else 0
            dep = parts[7]
            feats = parts[5]
            num = DROP_LABEL
            if feats and feats != "_":
                for feat in feats.split("|"):
                    if feat.startswith("Number="):
                        num = feat.split("=", 1)[1]
                        break
            rows.append((tid, form, upos, head, dep, num))
    return examples


def compute_ambiguous_vocab(examples: list[dict[str, Any]]) -> set[str]:
    vocab: dict[str, set[str]] = defaultdict(set)
    for ex in examples:
        for w, p in zip(ex["word_lower"], ex["pos"]):
            vocab[str(w)].add(str(p))
    return {w for w, tags in vocab.items() if len(tags) > 1}


def annotate_ud_examples_for_a1(examples: list[dict[str, Any]], ambiguous_vocab: set[str]) -> None:
    for ex in examples:
        ex["pos_ambig"] = [p if w in ambiguous_vocab else DROP_LABEL for w, p in zip(ex["word_lower"], ex["pos"])]


def load_wnut_examples(split: str, max_sentences: int) -> list[dict[str, Any]]:
    ds = load_dataset("flaitenberger/wnut_17", split=split)
    label_names = ds.features["ner_tags"].feature.names
    examples: list[dict[str, Any]] = []
    for row in ds:
        tokens = [str(t) for t in row["tokens"]]
        labels = [label_names[int(x)] for x in row["ner_tags"]]
        if tokens:
            examples.append({"words": tokens, "ner": labels})
        if len(examples) >= max_sentences:
            break
    return examples


def load_fewnerd_examples(split: str, max_sentences: int) -> list[dict[str, Any]]:
    ds = load_dataset("DFKI-SLT/few-nerd", "supervised", split=split)
    label_names = ds.features["ner_tags"].feature.names
    examples: list[dict[str, Any]] = []
    for row in ds:
        tokens = [str(t) for t in row["tokens"]]
        labels = [label_names[int(x)] for x in row["ner_tags"]]
        if tokens:
            examples.append({"words": tokens, "ner": labels})
        if len(examples) >= max_sentences:
            break
    return examples


def load_wikineural_examples(split: str, max_sentences: int) -> list[dict[str, Any]]:
    ds = load_dataset("Babelscape/wikineural", split=split)
    examples: list[dict[str, Any]] = []
    for row in ds:
        tokens = [str(t) for t in row["tokens"]]
        labels = [WIKINEURAL_TAG_NAMES[int(x)] for x in row["ner_tags"]]
        if tokens:
            examples.append({"words": tokens, "ner": labels})
        if len(examples) >= max_sentences:
            break
    return examples


def filter_train_labels(train_labels: np.ndarray, eval_labels: np.ndarray, min_examples_per_class: int) -> tuple[np.ndarray, np.ndarray, list[int]]:
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
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, dict[str, np.ndarray]]:
    xs_raw: list[np.ndarray] = []
    xs_pos: list[np.ndarray] = []
    xs_content: list[np.ndarray] = []
    xs_resid: list[np.ndarray] = []
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

    if not xs_raw:
        raise RuntimeError(f"No features extracted for label_keys={label_keys}")
    return (
        np.concatenate(xs_raw, axis=0),
        np.concatenate(xs_pos, axis=0),
        np.concatenate(xs_content, axis=0),
        np.concatenate(xs_resid, axis=0),
        {k: np.asarray(v, dtype=object) for k, v in labels_by_key.items()},
    )


def prepare_task_dataset(
    name: str,
    family: str,
    metric_name: str,
    train_raw: np.ndarray,
    train_pos: np.ndarray,
    train_content: np.ndarray,
    train_resid: np.ndarray,
    train_labels_obj: np.ndarray,
    eval_raw: np.ndarray,
    eval_pos: np.ndarray,
    eval_content: np.ndarray,
    eval_resid: np.ndarray,
    eval_labels_obj: np.ndarray,
    min_examples_per_class: int,
    train_source: str,
    eval_source: str,
) -> TaskDataset:
    train_keep = train_labels_obj != DROP_LABEL
    eval_keep = eval_labels_obj != DROP_LABEL
    train_labels_obj = train_labels_obj[train_keep]
    eval_labels_obj = eval_labels_obj[eval_keep]
    train_raw = train_raw[train_keep]
    train_pos = train_pos[train_keep]
    train_content = train_content[train_keep]
    train_resid = train_resid[train_keep]
    eval_raw = eval_raw[eval_keep]
    eval_pos = eval_pos[eval_keep]
    eval_content = eval_content[eval_keep]
    eval_resid = eval_resid[eval_keep]

    if train_labels_obj.shape[0] == 0 or eval_labels_obj.shape[0] == 0:
        raise RuntimeError(f"Task {name} has zero examples after drop filtering")

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
        family=family,
        metric_name=metric_name,
        label_names=label_names,
        train_raw=train_raw[train_mask],
        train_pos=train_pos[train_mask],
        train_content=train_content[train_mask],
        train_resid=train_resid[train_mask],
        train_labels=train_labels,
        eval_raw=eval_raw[eval_mask],
        eval_pos=eval_pos[eval_mask],
        eval_content=eval_content[eval_mask],
        eval_resid=eval_resid[eval_mask],
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
    return {
        "primary_metric": primary_metric,
        "metric_name": metric_name,
        "top1": float(metrics.top1),
        "auc_ovo_macro": float(metrics.auc_ovo_macro),
        "n_classes": int(metrics.n_classes),
        "n_train": int(metrics.n_train),
        "n_test": int(metrics.n_test),
        "diagnostics": asdict(diag),
    }


def family_rows_from_tasks(summary_tasks: dict[str, Any]) -> list[dict[str, Any]]:
    fam_to_tasks: dict[str, list[tuple[str, dict[str, Any]]]] = defaultdict(list)
    for task_name, task in summary_tasks.items():
        fam_to_tasks[str(task["family"])].append((task_name, task))
    rows: list[dict[str, Any]] = []
    for family, items in sorted(fam_to_tasks.items()):
        joint_gains = [float(task["joint_gain"]) for _, task in items]
        resid_gains = [float(task["resid_gain"]) for _, task in items]
        content_margins = [float(task["content_margin"]) for _, task in items]
        raw_gaps = [float(task["raw_gap"]) for _, task in items]
        best_privates = [float(task["best_private_metric"]) for _, task in items]
        raws = [float(task["representations"]["raw"]["primary_metric"]) for _, task in items]
        joints = [float(task["representations"]["joint"]["primary_metric"]) for _, task in items]
        resids = [float(task["representations"]["resid_additive"]["primary_metric"]) for _, task in items]
        pos_vals = [float(task["representations"]["pos_priv"]["primary_metric"]) for _, task in items]
        content_vals = [float(task["representations"]["content_priv"]["primary_metric"]) for _, task in items]
        rows.append(
            {
                "family": family,
                "n_tasks": len(items),
                "task_names": ",".join(name for name, _ in items),
                "mean_joint_gain": float(sum(joint_gains) / len(joint_gains)),
                "median_joint_gain": float(statistics.median(joint_gains)),
                "mean_resid_gain": float(sum(resid_gains) / len(resid_gains)),
                "median_resid_gain": float(statistics.median(resid_gains)),
                "mean_content_margin": float(sum(content_margins) / len(content_margins)),
                "mean_raw_gap": float(sum(raw_gaps) / len(raw_gaps)),
                "mean_best_private_metric": float(sum(best_privates) / len(best_privates)),
                "mean_raw_metric": float(sum(raws) / len(raws)),
                "mean_joint_metric": float(sum(joints) / len(joints)),
                "mean_resid_metric": float(sum(resids) / len(resids)),
                "mean_pos_priv_metric": float(sum(pos_vals) / len(pos_vals)),
                "mean_content_priv_metric": float(sum(content_vals) / len(content_vals)),
            }
        )
    return rows


def write_tsv(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        return
    with open(path, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()), delimiter="\t")
        w.writeheader()
        w.writerows(rows)


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
        ["pos", "pos_ambig", "deprel", "deprel_coarse", "number", "head_dir_dist"],
        model_lm, tokenizer, msae, device, args.layer_index, args.context_length, args.model_batch_size,
    )
    ud_eval_raw, ud_eval_pos, ud_eval_content, ud_eval_resid, ud_eval_labels = extract_features_and_labels(
        ud_dev,
        ["pos", "pos_ambig", "deprel", "deprel_coarse", "number", "head_dir_dist"],
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

    tasks = [
        prepare_task_dataset("pos_ud_ewt", "syntax_pos", "accuracy", ud_train_raw, ud_train_pos, ud_train_content, ud_train_resid, ud_train_labels["pos"], ud_eval_raw, ud_eval_pos, ud_eval_content, ud_eval_resid, ud_eval_labels["pos"], args.min_examples_per_class, "UD_EWT_train", "UD_EWT_dev"),
        prepare_task_dataset("pos_ambig_ud_ewt", "syntax_pos", "accuracy", ud_train_raw, ud_train_pos, ud_train_content, ud_train_resid, ud_train_labels["pos_ambig"], ud_eval_raw, ud_eval_pos, ud_eval_content, ud_eval_resid, ud_eval_labels["pos_ambig"], args.min_examples_per_class, "UD_EWT_train", "UD_EWT_dev"),
        prepare_task_dataset("deprel_ud_ewt", "syntax_dep", "accuracy", ud_train_raw, ud_train_pos, ud_train_content, ud_train_resid, ud_train_labels["deprel"], ud_eval_raw, ud_eval_pos, ud_eval_content, ud_eval_resid, ud_eval_labels["deprel"], args.min_examples_per_class, "UD_EWT_train", "UD_EWT_dev"),
        prepare_task_dataset("deprel_coarse_ud_ewt", "syntax_dep", "accuracy", ud_train_raw, ud_train_pos, ud_train_content, ud_train_resid, ud_train_labels["deprel_coarse"], ud_eval_raw, ud_eval_pos, ud_eval_content, ud_eval_resid, ud_eval_labels["deprel_coarse"], args.min_examples_per_class, "UD_EWT_train", "UD_EWT_dev"),
        prepare_task_dataset("number_ud_ewt", "syntax_morph", "accuracy", ud_train_raw, ud_train_pos, ud_train_content, ud_train_resid, ud_train_labels["number"], ud_eval_raw, ud_eval_pos, ud_eval_content, ud_eval_resid, ud_eval_labels["number"], args.min_examples_per_class, "UD_EWT_train", "UD_EWT_dev"),
        prepare_task_dataset("head_dir_dist_ud_ewt", "syntax_dep", "accuracy", ud_train_raw, ud_train_pos, ud_train_content, ud_train_resid, ud_train_labels["head_dir_dist"], ud_eval_raw, ud_eval_pos, ud_eval_content, ud_eval_resid, ud_eval_labels["head_dir_dist"], args.min_examples_per_class, "UD_EWT_train", "UD_EWT_dev"),
        prepare_task_dataset("ner_wnut17", "sem_wnut", "macro_f1", wnut_train_raw, wnut_train_pos, wnut_train_content, wnut_train_resid, wnut_train_labels["ner"], wnut_eval_raw, wnut_eval_pos, wnut_eval_content, wnut_eval_resid, wnut_eval_labels["ner"], args.min_examples_per_class, "WNUT17_train", "WNUT17_validation"),
        prepare_task_dataset("ner_fewnerd_coarse", "sem_fewnerd", "macro_f1", few_train_raw, few_train_pos, few_train_content, few_train_resid, few_train_labels["ner"], few_eval_raw, few_eval_pos, few_eval_content, few_eval_resid, few_eval_labels["ner"], args.min_examples_per_class, "FewNERD_train", "FewNERD_validation"),
        prepare_task_dataset("ner_wikineural_en", "sem_wikineural", "macro_f1", wiki_train_raw, wiki_train_pos, wiki_train_content, wiki_train_resid, wiki_train_labels["ner"], wiki_eval_raw, wiki_eval_pos, wiki_eval_content, wiki_eval_resid, wiki_eval_labels["ner"], args.min_examples_per_class, "WikiNEuRal_train_en", "WikiNEuRal_val_en"),
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
        joint_gain = joint_metric - best_private
        resid_gain = resid_metric - best_private
        content_margin = float(rep_results["content_priv"]["primary_metric"] - rep_results["pos_priv"]["primary_metric"])
        raw_gap = float(rep_results["raw"]["primary_metric"] - joint_metric)
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
            "joint_gain": float(joint_gain),
            "resid_gain": float(resid_gain),
            "content_margin": float(content_margin),
            "raw_gap": float(raw_gap),
            "representations": rep_results,
        }

    family_rows = family_rows_from_tasks(summary_tasks)
    family_summary = {row["family"]: row for row in family_rows}

    summary = {
        "stage": "pcc_stage_a1",
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
        "ud_sources": {"train_url": UD_TRAIN_URL, "dev_url": UD_DEV_URL},
        "semantic_sources": {
            "wnut17": "flaitenberger/wnut_17",
            "fewnerd": "DFKI-SLT/few-nerd:supervised",
            "wikineural_en": "Babelscape/wikineural",
        },
        "args": vars(args),
    }

    with open(out_dir / "pcc_stage_a1_summary.json", "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)
    write_tsv(out_dir / "pcc_stage_a1_metrics.tsv", rows)
    write_tsv(out_dir / "pcc_stage_a1_family_summary.tsv", family_rows)
    print(json.dumps({
        "output_dir": str(out_dir),
        "summary": str(out_dir / 'pcc_stage_a1_summary.json'),
        "metrics_tsv": str(out_dir / 'pcc_stage_a1_metrics.tsv'),
        "family_tsv": str(out_dir / 'pcc_stage_a1_family_summary.tsv'),
        "task_joint_gains": {k: v['joint_gain'] for k, v in summary_tasks.items()},
    }, indent=2))


if __name__ == "__main__":
    main()
