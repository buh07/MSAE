#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import statistics
import time
from dataclasses import asdict
from pathlib import Path
from typing import Any

import numpy as np
import torch
import torch.nn.functional as F
from sklearn.metrics import accuracy_score, f1_score, roc_auc_score
from sklearn.model_selection import train_test_split
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
    predict_labels_from_weights,
    resolve_git_commit_hash,
    set_seed,
    write_tsv,
)
from raw_activation_separability_pilot import (
    ProbeFitDiagnostics,
    ProbeMetrics,
    ProbeWeights,
    TorchProbeConfig,
    _predict_logits_batched,
    append_jsonl,
    can_stratify,
    choose_device,
    choose_probe_backend,
    remap_labels,
    remap_with_existing_mapping,
)
from train_msae_k2 import choose_dtype


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Stage A1c PCC confirmation audit on existing K=2 checkpoints")
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


def collapse_bio_label(label: str) -> str:
    if label == "O":
        return "O"
    if label.startswith("B-") or label.startswith("I-"):
        return label.split("-", 1)[1]
    return label


def labels_typeonly(labels: np.ndarray) -> np.ndarray:
    return np.asarray([collapse_bio_label(str(x)) for x in labels.tolist()], dtype=object)


def labels_entity_binary(labels: np.ndarray) -> np.ndarray:
    return np.asarray(["ENTITY" if str(x) != "O" else "O" for x in labels.tolist()], dtype=object)


def metric_from_predictions(metric_name: str, pred: np.ndarray, gold: np.ndarray) -> float:
    if pred.shape[0] == 0:
        return float("nan")
    if metric_name == "accuracy":
        return float(accuracy_score(gold, pred))
    if metric_name == "macro_f1":
        return float(f1_score(gold, pred, average="macro"))
    raise ValueError(f"unsupported metric_name={metric_name}")


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


def _train_eval_probe_torch_select(
    *,
    X: np.ndarray | torch.Tensor,
    y: np.ndarray,
    seed: int,
    c_value: float,
    probe_name: str,
    device: torch.device,
    cfg: TorchProbeConfig,
    intermediates_dir: str | None,
    eval_override: tuple[np.ndarray | torch.Tensor, np.ndarray],
    selection_metric_name: str,
) -> tuple[ProbeMetrics, ProbeWeights, ProbeFitDiagnostics, dict[str, Any]]:
    t0 = time.time()
    rng = np.random.default_rng(seed)

    y_reindexed, y_mapping = remap_labels(y)
    X_eval, y_eval = eval_override
    y_eval_reindexed, eval_mask = remap_with_existing_mapping(y_eval, y_mapping)
    if y_eval_reindexed.shape[0] == 0:
        raise RuntimeError(f"No eval samples survived mapping for probe {probe_name}.")
    if torch.is_tensor(X_eval):
        X_eval = X_eval[torch.from_numpy(eval_mask.astype(np.bool_)).to(X_eval.device)]
    else:
        X_eval = X_eval[eval_mask]

    n_samples = int(y_reindexed.shape[0])
    all_idx = np.arange(n_samples, dtype=np.int64)
    train_idx = all_idx
    y_train = y_reindexed

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
    y_fit = y_reindexed[fit_idx]
    y_val = y_reindexed[val_idx]

    if torch.is_tensor(X):
        x_all_t = X.to(device=device, dtype=torch.float32)
    else:
        x_all_t = torch.from_numpy(X.astype(np.float32)).to(device)

    train_idx_t = torch.from_numpy(train_idx.astype(np.int64)).to(device)
    fit_idx_t = torch.from_numpy(fit_idx.astype(np.int64)).to(device)
    val_idx_t = torch.from_numpy(val_idx.astype(np.int64)).to(device)

    x_train_t = x_all_t[train_idx_t]
    mu_t = x_train_t.mean(dim=0, keepdim=True)
    sigma_t = x_train_t.std(dim=0, keepdim=True) + 1e-6
    x_all_norm_t = (x_all_t - mu_t) / sigma_t

    x_fit_t = x_all_norm_t[fit_idx_t]
    y_fit_t = torch.from_numpy(y_fit.astype(np.int64)).to(device)
    x_val_t = x_all_norm_t[val_idx_t]
    y_val_t = torch.from_numpy(y_val.astype(np.int64)).to(device)

    if torch.is_tensor(X_eval):
        x_eval_t = X_eval.to(device=device, dtype=torch.float32)
    else:
        x_eval_t = torch.from_numpy(X_eval.astype(np.float32)).to(device)
    x_test_t = (x_eval_t - mu_t) / sigma_t
    y_test_t = torch.from_numpy(y_eval_reindexed.astype(np.int64)).to(device)

    n_classes = int(np.unique(y_reindexed).shape[0])
    hidden_size = int(x_all_t.shape[1])
    model = torch.nn.Linear(hidden_size, n_classes, bias=True, device=device, dtype=torch.float32)

    if cfg.weight_decay >= 0.0:
        weight_decay = cfg.weight_decay
    else:
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
    best_val_primary = -1.0
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
        batch_n = min(cfg.batch_size, x_fit_t.shape[0])
        idx = perm[cursor : cursor + batch_n]
        cursor += batch_n
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
                val_pred_t = torch.argmax(val_logits, dim=1)
                val_pred = val_pred_t.detach().cpu().numpy().astype(np.int64)
                y_val_np = y_val_t.detach().cpu().numpy().astype(np.int64)
                val_top1 = float((val_pred_t == y_val_t).float().mean().item())
                val_primary = metric_from_predictions(selection_metric_name, val_pred, y_val_np)

            prior_best_val_loss = best_val_loss
            improved = False
            if val_primary > best_val_primary + 1e-6:
                improved = True
            elif abs(val_primary - best_val_primary) <= 1e-6 and val_loss < best_val_loss:
                improved = True

            if improved:
                best_val_primary = val_primary
                best_val_top1 = val_top1
                best_val_loss = val_loss
                best_state = {k: v.detach().cpu().clone() for k, v in model.state_dict().items()}
                no_improve_steps = 0
            else:
                no_improve_steps += cfg.eval_every

            loss_improvement = max(0.0, prior_best_val_loss - val_loss)
            if probe_name.startswith("token_"):
                if val_top1 >= cfg.token_ceiling_top1 and loss_improvement < cfg.token_ceiling_loss_eps:
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
                "val_primary": val_primary,
                "selection_metric_name": selection_metric_name,
                "best_val_primary": best_val_primary,
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
                f"val_primary={val_primary:.4f} best_val_primary={best_val_primary:.4f} elapsed_s={elapsed:.1f}"
            )
            if log_path is not None:
                append_jsonl(log_path, progress)

            if step >= cfg.min_steps and no_improve_steps >= cfg.patience:
                print(f"[probe-early-stop] name={probe_name} step={step} patience={cfg.patience}")
                break
            if probe_name.startswith("token_") and step >= cfg.min_steps and token_ceiling_hits >= cfg.token_ceiling_evals:
                print(
                    "[probe-ceiling-stop] "
                    f"name={probe_name} step={step} top1={val_top1:.4f} "
                    f"hits={token_ceiling_hits}/{cfg.token_ceiling_evals}"
                )
                break

    with torch.no_grad():
        model.load_state_dict({k: v.to(device) for k, v in best_state.items()})
        test_logits = _predict_logits_batched(model, x_test_t)
        test_pred_t = torch.argmax(test_logits, dim=1)
        top1 = float((test_pred_t == y_test_t).float().mean().item())
        test_proba = torch.softmax(test_logits, dim=1).detach().cpu().numpy()

    auc = float("nan")
    try:
        auc = float(roc_auc_score(y_eval_reindexed, test_proba, multi_class="ovo", average="macro"))
    except Exception:
        pass

    metrics = ProbeMetrics(
        top1=top1,
        auc_ovo_macro=auc,
        n_classes=n_classes,
        n_train=int(y_reindexed.shape[0]),
        n_test=int(y_eval_reindexed.shape[0]),
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

    del model, x_fit_t, y_fit_t, x_val_t, y_val_t, x_test_t, y_test_t, test_logits, x_all_t, x_train_t, x_all_norm_t, train_idx_t, fit_idx_t, val_idx_t, mu_t, sigma_t
    if torch.cuda.is_available():
        torch.cuda.empty_cache()

    extra = {
        "selection_metric_name": selection_metric_name,
        "best_eval_primary_metric": float(best_val_primary),
    }
    return metrics, weights, diagnostics, extra


def clone_cfg(cfg: TorchProbeConfig, *, max_steps: int | None = None, patience: int | None = None, min_steps: int | None = None) -> TorchProbeConfig:
    return TorchProbeConfig(
        max_steps=int(max_steps if max_steps is not None else cfg.max_steps),
        batch_size=int(cfg.batch_size),
        lr=float(cfg.lr),
        weight_decay=float(cfg.weight_decay),
        eval_every=int(cfg.eval_every),
        patience=int(patience if patience is not None else cfg.patience),
        min_steps=int(min_steps if min_steps is not None else cfg.min_steps),
        token_ceiling_top1=float(cfg.token_ceiling_top1),
        token_ceiling_evals=int(cfg.token_ceiling_evals),
        token_ceiling_loss_eps=float(cfg.token_ceiling_loss_eps),
        position_raw_highdim_lr=float(cfg.position_raw_highdim_lr),
        position_raw_highdim_threshold=int(cfg.position_raw_highdim_threshold),
        scheduler=str(cfg.scheduler),
    )


def run_probe_for_rep_a1c(
    *,
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
    if probe_backend != "torch":
        raise ValueError("Stage A1c confirmation is currently locked to the torch probe backend.")
    metrics, weights, diag, extra = _train_eval_probe_torch_select(
        X=X_train,
        y=y_train,
        seed=42,
        c_value=c_value,
        probe_name=probe_name,
        device=probe_device,
        cfg=torch_cfg,
        intermediates_dir=str(out_dir / "probe_logs"),
        eval_override=(X_eval, y_eval),
        selection_metric_name=metric_name,
    )
    pred, gold = predict_labels_from_weights(weights, X_eval, y_train, y_eval)
    primary_metric = metric_from_predictions(metric_name, pred, gold)
    diag_dict = asdict(diag)
    diag_dict.update(extra)
    return {
        "primary_metric": primary_metric,
        "metric_name": metric_name,
        "top1": float(metrics.top1),
        "auc_ovo_macro": float(metrics.auc_ovo_macro),
        "n_classes": int(metrics.n_classes),
        "n_train": int(metrics.n_train),
        "n_test": int(metrics.n_test),
        "diagnostics": diag_dict,
    }


def main() -> None:
    args = parse_args()
    set_seed(args.seed)
    device = choose_device(args.device)
    dtype = choose_dtype(args.dtype)
    probe_backend = choose_probe_backend(args.probe_backend, device)
    if probe_backend != "torch":
        raise SystemExit("Stage A1c confirmation currently requires probe_backend=torch")

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
    add_task(tasks, name="pos_ud_ewt", family="syntax_pos", metric_name="accuracy", train_raw=ud_train_raw, train_pos=ud_train_pos, train_content=ud_train_content, train_resid=ud_train_resid, train_labels=ud_train_labels["pos"], eval_raw=ud_eval_raw, eval_pos=ud_eval_pos, eval_content=ud_eval_content, eval_resid=ud_eval_resid, eval_labels=ud_eval_labels["pos"], min_examples_per_class=args.min_examples_per_class, train_source="UD_EWT_train", eval_source="UD_EWT_dev")
    add_task(tasks, name="pos_ambig_ud_ewt", family="syntax_pos", metric_name="accuracy", train_raw=ud_train_raw, train_pos=ud_train_pos, train_content=ud_train_content, train_resid=ud_train_resid, train_labels=ud_train_labels["pos_ambig"], eval_raw=ud_eval_raw, eval_pos=ud_eval_pos, eval_content=ud_eval_content, eval_resid=ud_eval_resid, eval_labels=ud_eval_labels["pos_ambig"], min_examples_per_class=args.min_examples_per_class, train_source="UD_EWT_train", eval_source="UD_EWT_dev")
    add_task(tasks, name="deprel_coarse_ud_ewt", family="syntax_dep_coarse", metric_name="accuracy", train_raw=ud_train_raw, train_pos=ud_train_pos, train_content=ud_train_content, train_resid=ud_train_resid, train_labels=ud_train_labels["deprel_coarse"], eval_raw=ud_eval_raw, eval_pos=ud_eval_pos, eval_content=ud_eval_content, eval_resid=ud_eval_resid, eval_labels=ud_eval_labels["deprel_coarse"], min_examples_per_class=args.min_examples_per_class, train_source="UD_EWT_train", eval_source="UD_EWT_dev")
    add_task(tasks, name="head_dir_dist_ud_ewt", family="syntax_dep_head_dir", metric_name="accuracy", train_raw=ud_train_raw, train_pos=ud_train_pos, train_content=ud_train_content, train_resid=ud_train_resid, train_labels=ud_train_labels["head_dir_dist"], eval_raw=ud_eval_raw, eval_pos=ud_eval_pos, eval_content=ud_eval_content, eval_resid=ud_eval_resid, eval_labels=ud_eval_labels["head_dir_dist"], min_examples_per_class=args.min_examples_per_class, train_source="UD_EWT_train", eval_source="UD_EWT_dev")
    add_task(tasks, name="number_ud_ewt", family="syntax_morph", metric_name="accuracy", train_raw=ud_train_raw, train_pos=ud_train_pos, train_content=ud_train_content, train_resid=ud_train_resid, train_labels=ud_train_labels["number"], eval_raw=ud_eval_raw, eval_pos=ud_eval_pos, eval_content=ud_eval_content, eval_resid=ud_eval_resid, eval_labels=ud_eval_labels["number"], min_examples_per_class=args.min_examples_per_class, train_source="UD_EWT_train", eval_source="UD_EWT_dev")
    add_task(tasks, name="ner_wnut17_typeonly", family="sem_wnut17_typeonly", metric_name="macro_f1", train_raw=wnut_train_raw, train_pos=wnut_train_pos, train_content=wnut_train_content, train_resid=wnut_train_resid, train_labels=labels_typeonly(wnut_train_labels["ner"]), eval_raw=wnut_eval_raw, eval_pos=wnut_eval_pos, eval_content=wnut_eval_content, eval_resid=wnut_eval_resid, eval_labels=labels_typeonly(wnut_eval_labels["ner"]), min_examples_per_class=args.min_examples_per_class, train_source="WNUT17_train", eval_source="WNUT17_validation")
    add_task(tasks, name="ner_fewnerd_coarse_binary", family="sem_fewnerd_coarse_binary", metric_name="macro_f1", train_raw=few_train_raw, train_pos=few_train_pos, train_content=few_train_content, train_resid=few_train_resid, train_labels=labels_entity_binary(few_train_labels["ner"]), eval_raw=few_eval_raw, eval_pos=few_eval_pos, eval_content=few_eval_content, eval_resid=few_eval_resid, eval_labels=labels_entity_binary(few_eval_labels["ner"]), min_examples_per_class=args.min_examples_per_class, train_source="FewNERD_train", eval_source="FewNERD_validation")
    add_task(tasks, name="ner_wikineural_en_binary", family="sem_wikineural_en_binary", metric_name="macro_f1", train_raw=wiki_train_raw, train_pos=wiki_train_pos, train_content=wiki_train_content, train_resid=wiki_train_resid, train_labels=labels_entity_binary(wiki_train_labels["ner"]), eval_raw=wiki_eval_raw, eval_pos=wiki_eval_pos, eval_content=wiki_eval_content, eval_resid=wiki_eval_resid, eval_labels=labels_entity_binary(wiki_eval_labels["ner"]), min_examples_per_class=args.min_examples_per_class, train_source="WikiNEuRal_train_en", eval_source="WikiNEuRal_val_en")

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
        "stage": "pcc_stage_a1c",
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
            "confirmation_changes_vs_a1b": [
                "same amended task framing as A1b, reduced to the proposed gated families plus exploratory head_dir",
                "NER probe checkpoint selection aligned to macro_f1 instead of validation top1",
                "large semantic probes use an increased max_steps budget",
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

    with open(out_dir / "pcc_stage_a1c_summary.json", "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)
    write_tsv(out_dir / "pcc_stage_a1c_metrics.tsv", rows)
    write_tsv(out_dir / "pcc_stage_a1c_family_summary.tsv", family_rows)
    print(json.dumps({
        "output_dir": str(out_dir),
        "summary": str(out_dir / "pcc_stage_a1c_summary.json"),
        "metrics_tsv": str(out_dir / "pcc_stage_a1c_metrics.tsv"),
        "family_tsv": str(out_dir / "pcc_stage_a1c_family_summary.tsv"),
        "task_joint_gains": {k: v["joint_gain"] for k, v in summary_tasks.items()},
    }, indent=2))


if __name__ == "__main__":
    main()
