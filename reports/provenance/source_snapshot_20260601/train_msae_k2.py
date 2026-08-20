#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
import math
import os
import random
import time
from collections import Counter, deque
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Iterator

import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F
from datasets import load_dataset
from transformers import AutoModelForCausalLM, AutoTokenizer

METRICS_SCHEMA_VERSION = "k2_msae_v2"


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Train K=2 MSAE on transformer activations (GPU-first)")
    p.add_argument("--model_name", type=str, default="EleutherAI/pythia-160m-deduped")
    p.add_argument("--layer_index", type=int, default=3)
    p.add_argument("--seed", type=int, default=42)
    p.add_argument("--device", type=str, default="cuda")
    p.add_argument("--dtype", type=str, default="fp16", choices=["fp16", "bf16", "fp32"])

    p.add_argument("--dataset_name", type=str, default="ArmelR/the-pile-splitted")
    p.add_argument("--dataset_config", type=str, default="all")
    p.add_argument("--dataset_split", type=str, default="train")
    p.add_argument("--text_field", type=str, default="text")
    p.add_argument("--streaming", action="store_true", default=True)
    p.add_argument("--no_streaming", action="store_false", dest="streaming")
    p.add_argument(
        "--source_configs_csv",
        type=str,
        default="ArXiv,Github,Pile-CC,PubMed Abstracts",
        help="Comma-separated source configs for balanced interleaving when dataset_config=all",
    )
    p.add_argument("--balanced_interleave_sources", action="store_true", default=True)
    p.add_argument("--no_balanced_interleave_sources", action="store_false", dest="balanced_interleave_sources")
    p.add_argument(
        "--data_pipeline_mode",
        type=str,
        default="interleaved_stream",
        choices=["interleaved_stream", "pretok_warm_then_stream"],
        help="Data pipeline mode. pretok_warm_then_stream pre-tokenizes warm shards once before training.",
    )
    p.add_argument(
        "--pretok_warm_tokens",
        type=int,
        default=50_000_000,
        help="Number of valid training tokens to pre-tokenize into shards before training starts.",
    )
    p.add_argument(
        "--pretok_shard_sequences",
        type=int,
        default=250_000,
        help="Number of fixed-length sequences per shard.",
    )
    p.add_argument(
        "--pretok_dir",
        type=str,
        default="",
        help="Directory for pre-tokenized shards. Defaults to <output_dir>/pretok_cache.",
    )
    p.add_argument("--data_monitor", action="store_true", default=True)
    p.add_argument("--no_data_monitor", action="store_false", dest="data_monitor")

    p.add_argument("--context_length", type=int, default=128)
    p.add_argument("--model_batch_size", type=int, default=4)
    p.add_argument("--skip_first_position", action="store_true", default=True)

    p.add_argument("--target_tokens", type=int, default=100_000_000)
    p.add_argument("--microbatch_size", type=int, default=64)
    p.add_argument("--effective_batch_size", type=int, default=4096)

    p.add_argument("--m_pos", type=int, default=8192)
    p.add_argument("--k_pos", type=int, default=8)
    p.add_argument("--m_content", type=int, default=32768)
    p.add_argument("--k_content", type=int, default=24)

    p.add_argument("--lambda_inc", type=float, default=1e-2)
    p.add_argument("--inc_sample_rows_pos", type=int, default=512)
    p.add_argument("--inc_sample_rows_content", type=int, default=512)

    p.add_argument("--lr", type=float, default=7e-5)
    p.add_argument("--adam_beta1", type=float, default=0.0)
    p.add_argument("--adam_beta2", type=float, default=0.999)
    p.add_argument("--adam_eps", type=float, default=1e-8)
    p.add_argument("--warmup_steps", type=int, default=1000)

    p.add_argument("--auxk_revive", action="store_true", default=True)
    p.add_argument("--dead_after_steps", type=int, default=2000)
    p.add_argument("--revive_per_step", type=int, default=64)

    p.add_argument("--log_every_steps", type=int, default=20)
    p.add_argument("--checkpoint_every_tokens", type=int, default=2_000_000)
    p.add_argument("--output_dir", type=str, required=True)
    p.add_argument("--resume_path", type=str, default="")
    p.add_argument("--git_commit_hash", type=str, default="")

    return p.parse_args()


def set_seed(seed: int) -> None:
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)


def choose_dtype(name: str) -> torch.dtype:
    if name == "fp16":
        return torch.float16
    if name == "bf16":
        return torch.bfloat16
    return torch.float32


def resolve_hidden_state_index(requested_layer: int, n_hidden_states: int) -> int:
    max_block = n_hidden_states - 2
    block = min(requested_layer, max_block)
    return block + 1


def normalize_text_field(raw: dict[str, Any], text_field: str) -> str:
    if text_field in raw and isinstance(raw[text_field], str):
        return raw[text_field]
    for key in ("text", "content", "body"):
        if key in raw and isinstance(raw[key], str):
            return raw[key]
    return ""


def parse_source_configs(csv_text: str) -> list[str]:
    parts = [x.strip() for x in csv_text.split(",")]
    return [x for x in parts if x]


def iter_texts_single_source(
    dataset_name: str,
    dataset_config: str,
    dataset_split: str,
    streaming: bool,
) -> Iterator[dict[str, Any]]:
    if dataset_config:
        ds = load_dataset(dataset_name, dataset_config, split=dataset_split, streaming=streaming)
    else:
        ds = load_dataset(dataset_name, split=dataset_split, streaming=streaming)

    if streaming:
        while True:
            for row in ds:
                yield row
    else:
        while True:
            for row in ds:
                yield row


def iter_texts_balanced_sources(
    dataset_name: str,
    source_configs: list[str],
    dataset_split: str,
    streaming: bool,
) -> Iterator[dict[str, Any]]:
    if not source_configs:
        raise ValueError("source_configs cannot be empty for balanced interleave")
    iterators = [
        iter_texts_single_source(
            dataset_name=dataset_name,
            dataset_config=cfg,
            dataset_split=dataset_split,
            streaming=streaming,
        )
        for cfg in source_configs
    ]
    source_idx = 0
    while True:
        cfg = source_configs[source_idx]
        it = iterators[source_idx]
        try:
            row = next(it)
        except StopIteration:
            iterators[source_idx] = iter_texts_single_source(
                dataset_name=dataset_name,
                dataset_config=cfg,
                dataset_split=dataset_split,
                streaming=streaming,
            )
            row = next(iterators[source_idx])
        row = dict(row)
        row["_source_config"] = cfg
        yield row
        source_idx = (source_idx + 1) % len(source_configs)


def iter_texts(
    dataset_name: str,
    dataset_config: str,
    dataset_split: str,
    streaming: bool,
    balanced_interleave_sources: bool,
    source_configs: list[str],
) -> Iterator[dict[str, Any]]:
    if dataset_config == "all" and balanced_interleave_sources and source_configs:
        yield from iter_texts_balanced_sources(
            dataset_name=dataset_name,
            source_configs=source_configs,
            dataset_split=dataset_split,
            streaming=streaming,
        )
        return
    cfg = dataset_config
    if cfg == "all":
        # Keep original behavior as fallback if balancing is disabled.
        cfg = "all"
    yield from iter_texts_single_source(
        dataset_name=dataset_name,
        dataset_config=cfg,
        dataset_split=dataset_split,
        streaming=streaming,
    )


def valid_token_count(attention_mask: np.ndarray | torch.Tensor, skip_first_position: bool) -> int:
    if isinstance(attention_mask, torch.Tensor):
        c = int(attention_mask.sum().item())
        if skip_first_position:
            c -= int(attention_mask.shape[0])
        return max(0, c)
    c = int(np.sum(attention_mask))
    if skip_first_position:
        c -= int(attention_mask.shape[0])
    return max(0, c)


def build_pretokenized_warm_cache(
    pretok_dir: Path,
    tokenizer: AutoTokenizer,
    text_iter: Iterator[dict[str, Any]],
    text_field: str,
    context_length: int,
    model_batch_size: int,
    skip_first_position: bool,
    target_valid_tokens: int,
    shard_sequences: int,
) -> dict[str, Any]:
    pretok_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = pretok_dir / "manifest.json"
    if manifest_path.exists():
        with open(manifest_path, "r", encoding="utf-8") as f:
            old = json.load(f)
        if (
            old.get("context_length") == context_length
            and old.get("text_field") == text_field
            and int(old.get("target_valid_tokens", 0)) >= int(target_valid_tokens)
            and old.get("status") == "ready"
        ):
            return old

    # Remove stale files from previous partial attempts.
    for p in pretok_dir.glob("ids_*.npy"):
        p.unlink(missing_ok=True)
    for p in pretok_dir.glob("mask_*.npy"):
        p.unlink(missing_ok=True)
    for p in pretok_dir.glob("shards.tsv"):
        p.unlink(missing_ok=True)

    source_counts: Counter[str] = Counter()
    shard_rows: list[dict[str, Any]] = []
    shard_id = 0
    total_valid_tokens = 0
    total_sequences = 0
    build_start = time.time()
    buffered_ids: list[np.ndarray] = []
    buffered_masks: list[np.ndarray] = []
    buffered_seq = 0

    def flush_shard() -> None:
        nonlocal shard_id, buffered_ids, buffered_masks, buffered_seq
        if buffered_seq == 0:
            return
        shard_id += 1
        ids = np.concatenate(buffered_ids, axis=0)
        masks = np.concatenate(buffered_masks, axis=0)
        ids_path = pretok_dir / f"ids_{shard_id:05d}.npy"
        masks_path = pretok_dir / f"mask_{shard_id:05d}.npy"
        np.save(ids_path, ids)
        np.save(masks_path, masks)
        shard_rows.append(
            {
                "shard_id": shard_id,
                "ids_path": str(ids_path),
                "mask_path": str(masks_path),
                "num_sequences": int(ids.shape[0]),
                "valid_tokens": int(valid_token_count(masks, skip_first_position)),
            }
        )
        buffered_ids = []
        buffered_masks = []
        buffered_seq = 0

    while total_valid_tokens < target_valid_tokens:
        batch_texts: list[str] = []
        batch_sources: list[str] = []
        while len(batch_texts) < model_batch_size:
            row = next(text_iter)
            source = str(row.get("_source_config", row.get("domain", "unknown")))
            t = normalize_text_field(row, text_field).strip()
            if t:
                batch_texts.append(t)
                batch_sources.append(source)
        t0 = time.time()
        enc = tokenizer(
            batch_texts,
            return_tensors="np",
            truncation=True,
            padding="max_length",
            max_length=context_length,
        )
        _ = time.time() - t0
        ids = enc["input_ids"].astype(np.uint16, copy=False)
        masks = enc["attention_mask"].astype(np.uint8, copy=False)

        for s in batch_sources:
            source_counts[s] += 1
        n_valid = valid_token_count(masks, skip_first_position)
        total_valid_tokens += int(n_valid)
        total_sequences += int(ids.shape[0])
        buffered_ids.append(ids)
        buffered_masks.append(masks)
        buffered_seq += int(ids.shape[0])
        if buffered_seq >= shard_sequences:
            flush_shard()
        if total_sequences % 100_000 == 0:
            tok_s = total_valid_tokens / max(1e-6, (time.time() - build_start))
            print(
                f"[pretok] seq={total_sequences} valid_tokens={total_valid_tokens} "
                f"tok_s={tok_s:.1f} target={target_valid_tokens}"
            )

    flush_shard()
    tok_s = total_valid_tokens / max(1e-6, (time.time() - build_start))
    manifest = {
        "status": "ready",
        "context_length": context_length,
        "text_field": text_field,
        "target_valid_tokens": int(target_valid_tokens),
        "total_valid_tokens": int(total_valid_tokens),
        "total_sequences": int(total_sequences),
        "num_shards": int(len(shard_rows)),
        "source_counts": dict(source_counts),
        "throughput_valid_tok_s": float(tok_s),
        "shards": shard_rows,
    }
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)
    with open(pretok_dir / "shards.tsv", "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["shard_id", "ids_path", "mask_path", "num_sequences", "valid_tokens"], delimiter="\t")
        w.writeheader()
        w.writerows(shard_rows)
    return manifest


class PretokBatchProvider:
    def __init__(self, manifest: dict[str, Any], model_batch_size: int, seed: int):
        shards = manifest.get("shards", [])
        if not shards:
            raise ValueError("pretokenized manifest has no shards")
        self.model_batch_size = model_batch_size
        self.rng = random.Random(seed)
        self.shards = [dict(s) for s in shards]
        self.shard_order: deque[int] = deque()
        self.cur_ids: np.ndarray | None = None
        self.cur_masks: np.ndarray | None = None
        self.cur_idx = 0
        self._reshuffle()

    def _reshuffle(self) -> None:
        order = list(range(len(self.shards)))
        self.rng.shuffle(order)
        self.shard_order = deque(order)
        self.cur_ids = None
        self.cur_masks = None
        self.cur_idx = 0

    def _load_next_shard(self) -> None:
        if not self.shard_order:
            self._reshuffle()
        idx = self.shard_order.popleft()
        shard = self.shards[idx]
        self.cur_ids = np.load(shard["ids_path"], mmap_mode="r")
        self.cur_masks = np.load(shard["mask_path"], mmap_mode="r")
        self.cur_idx = 0

    def next_batch(self) -> tuple[np.ndarray, np.ndarray]:
        ids_out: list[np.ndarray] = []
        masks_out: list[np.ndarray] = []
        while len(ids_out) < self.model_batch_size:
            if self.cur_ids is None or self.cur_idx >= int(self.cur_ids.shape[0]):
                self._load_next_shard()
            assert self.cur_ids is not None and self.cur_masks is not None
            n_take = min(self.model_batch_size - len(ids_out), int(self.cur_ids.shape[0]) - self.cur_idx)
            if n_take <= 0:
                self._load_next_shard()
                continue
            sl = slice(self.cur_idx, self.cur_idx + n_take)
            ids_out.append(np.asarray(self.cur_ids[sl]))
            masks_out.append(np.asarray(self.cur_masks[sl]))
            self.cur_idx += n_take
        return np.concatenate(ids_out, axis=0), np.concatenate(masks_out, axis=0)


class TopKBranch(nn.Module):
    def __init__(self, d_model: int, m: int, k: int):
        super().__init__()
        self.m = m
        self.k = k
        self.encoder = nn.Linear(d_model, m, bias=False)
        dec = torch.randn(m, d_model) / math.sqrt(float(d_model))
        dec = F.normalize(dec, dim=1)
        self.decoder = nn.Parameter(dec)

    def forward(self, x: torch.Tensor) -> tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
        z = F.relu(self.encoder(x))
        k = min(self.k, z.shape[1])
        vals, idx = torch.topk(z, k=k, dim=1)
        # Efficient sparse decode: sum_i vals_i * decoder[idx_i]
        dec_rows = self.decoder[idx]  # [B, K, D]
        recon = torch.sum(dec_rows * vals.unsqueeze(-1), dim=1)
        return recon, idx, vals

    @torch.no_grad()
    def renorm_decoder(self) -> None:
        self.decoder.copy_(F.normalize(self.decoder, dim=1))


class K2MSAE(nn.Module):
    def __init__(self, d_model: int, m_pos: int, k_pos: int, m_content: int, k_content: int):
        super().__init__()
        self.pos = TopKBranch(d_model=d_model, m=m_pos, k=k_pos)
        self.content = TopKBranch(d_model=d_model, m=m_content, k=k_content)

    def forward(self, x: torch.Tensor) -> dict[str, torch.Tensor]:
        recon_pos, idx_pos, vals_pos = self.pos(x)
        recon_content, idx_content, vals_content = self.content(x)
        recon = recon_pos + recon_content
        return {
            "recon": recon,
            "recon_pos": recon_pos,
            "recon_content": recon_content,
            "idx_pos": idx_pos,
            "vals_pos": vals_pos,
            "idx_content": idx_content,
            "vals_content": vals_content,
        }

    @torch.no_grad()
    def renorm_decoders(self) -> None:
        self.pos.renorm_decoder()
        self.content.renorm_decoder()


@dataclass
class StepStats:
    step: int
    tokens_seen: int
    recon_loss: float
    incoh_loss_est: float
    total_loss: float
    fvu_total: float
    fvu_pos: float
    fvu_content: float
    fvu_only_pos: float
    fvu_only_content: float
    delta_drop_pos: float
    delta_drop_content: float
    energy_ratio_pos: float
    energy_ratio_content: float
    active_latent_frac_pos: float
    active_latent_frac_content: float
    usage_entropy_pos: float
    usage_entropy_content: float
    usage_gini_pos: float
    usage_gini_content: float
    revival_rate_pos_per_mtok: float
    revival_rate_content_per_mtok: float
    pos_dead_fraction: float
    content_dead_fraction: float
    throughput_tok_s: float
    elapsed_s: float


class DeadTracker:
    def __init__(self, m: int, device: torch.device):
        self.last_used_step = torch.zeros(m, dtype=torch.long, device=device)

    @torch.no_grad()
    def update(self, idx: torch.Tensor, step: int) -> None:
        flat = idx.reshape(-1)
        uniq = torch.unique(flat)
        self.last_used_step[uniq] = step

    @torch.no_grad()
    def dead_mask(self, step: int, dead_after_steps: int) -> torch.Tensor:
        return (step - self.last_used_step) > dead_after_steps

    @torch.no_grad()
    def dead_fraction(self, step: int, dead_after_steps: int) -> float:
        return float(self.dead_mask(step, dead_after_steps).float().mean().item())


@torch.no_grad()
def maybe_revive_dead_latents(
    branch: TopKBranch,
    tracker: DeadTracker,
    step: int,
    dead_after_steps: int,
    revive_per_step: int,
    x_batch: torch.Tensor,
) -> int:
    dead = torch.nonzero(tracker.dead_mask(step, dead_after_steps), as_tuple=False).squeeze(1)
    if dead.numel() == 0 or revive_per_step <= 0:
        return 0
    n = min(revive_per_step, int(dead.numel()))
    perm = torch.randperm(dead.numel(), device=dead.device)[:n]
    chosen = dead[perm]

    sel = torch.randint(0, x_batch.shape[0], (n,), device=x_batch.device)
    samples = F.normalize(x_batch[sel], dim=1)

    branch.decoder[chosen] = samples
    branch.encoder.weight[chosen] = samples
    tracker.last_used_step[chosen] = step
    return n


def incoherence_estimate(
    d_pos: torch.Tensor,
    d_content: torch.Tensor,
    sample_pos: int,
    sample_content: int,
) -> torch.Tensor:
    m_pos = d_pos.shape[0]
    m_content = d_content.shape[0]
    sp = min(sample_pos, m_pos)
    sc = min(sample_content, m_content)
    idx_p = torch.randperm(m_pos, device=d_pos.device)[:sp]
    idx_c = torch.randperm(m_content, device=d_content.device)[:sc]
    a = d_pos[idx_p]  # [sp, d]
    b = d_content[idx_c]  # [sc, d]
    gram = a @ b.T
    return torch.mean(gram * gram)


def usage_entropy_and_gini(counts: torch.Tensor) -> tuple[float, float]:
    counts = counts.float()
    total = counts.sum()
    if float(total.item()) <= 0.0:
        return 0.0, 0.0

    nonzero = counts[counts > 0]
    p = nonzero / total
    denom = max(1.0, math.log(float(counts.numel())))
    entropy = float((-(p * torch.log(p + 1e-12)).sum() / denom).item())

    xs, _ = torch.sort(counts)
    n = xs.numel()
    idx = torch.arange(1, n + 1, device=xs.device, dtype=xs.dtype)
    gini = (2.0 * torch.sum(idx * xs) / (float(n) * total)) - (float(n + 1) / float(n))
    gini = float(torch.clamp(gini, 0.0, 1.0).item())
    return entropy, gini


def finite_float(x: Any) -> bool:
    try:
        xv = float(x)
    except Exception:
        return False
    return math.isfinite(xv)


def tail_median(rows: list[dict[str, Any]], key: str, window: int) -> float:
    vals = [float(r[key]) for r in rows if key in r and finite_float(r[key])]
    if not vals:
        return float("nan")
    tail = vals[-window:]
    return float(np.median(np.asarray(tail, dtype=np.float64)))


def tail_slope(rows: list[dict[str, Any]], key: str, window: int) -> float:
    vals = [float(r[key]) for r in rows if key in r and finite_float(r[key])]
    if len(vals) < 2:
        return float("nan")
    tail = np.asarray(vals[-window:], dtype=np.float64)
    if tail.size < 2:
        return float("nan")
    xs = np.arange(tail.size, dtype=np.float64)
    slope = np.polyfit(xs, tail, 1)[0]
    return float(slope)


def save_checkpoint(
    path: Path,
    model: K2MSAE,
    optimizer: torch.optim.Optimizer,
    scheduler: torch.optim.lr_scheduler.LambdaLR,
    step: int,
    tokens_seen: int,
    pos_tracker: DeadTracker,
    content_tracker: DeadTracker,
    args: argparse.Namespace,
) -> None:
    obj = {
        "model": model.state_dict(),
        "optimizer": optimizer.state_dict(),
        "scheduler": scheduler.state_dict(),
        "step": step,
        "tokens_seen": tokens_seen,
        "pos_last_used_step": pos_tracker.last_used_step.detach().cpu(),
        "content_last_used_step": content_tracker.last_used_step.detach().cpu(),
        "torch_rng_state": torch.get_rng_state(),
        "cuda_rng_state_all": torch.cuda.get_rng_state_all() if torch.cuda.is_available() else None,
        "np_rng_state": np.random.get_state(),
        "py_rng_state": random.getstate(),
        "args": vars(args),
        "saved_at": time.time(),
    }
    torch.save(obj, path)


def try_save_checkpoint(
    path: Path,
    model: K2MSAE,
    optimizer: torch.optim.Optimizer,
    scheduler: torch.optim.lr_scheduler.LambdaLR,
    step: int,
    tokens_seen: int,
    pos_tracker: DeadTracker,
    content_tracker: DeadTracker,
    args: argparse.Namespace,
) -> tuple[bool, str]:
    try:
        save_checkpoint(
            path=path,
            model=model,
            optimizer=optimizer,
            scheduler=scheduler,
            step=step,
            tokens_seen=tokens_seen,
            pos_tracker=pos_tracker,
            content_tracker=content_tracker,
            args=args,
        )
        return True, ""
    except Exception as exc:
        return False, str(exc)


def load_checkpoint(
    path: Path,
    model: K2MSAE,
    optimizer: torch.optim.Optimizer,
    scheduler: torch.optim.lr_scheduler.LambdaLR,
    pos_tracker: DeadTracker,
    content_tracker: DeadTracker,
) -> tuple[int, int]:
    ckpt = torch.load(path, map_location="cpu", weights_only=False)
    model.load_state_dict(ckpt["model"])
    optimizer.load_state_dict(ckpt["optimizer"])
    scheduler.load_state_dict(ckpt["scheduler"])

    pos_tracker.last_used_step.copy_(ckpt["pos_last_used_step"].to(pos_tracker.last_used_step.device))
    content_tracker.last_used_step.copy_(ckpt["content_last_used_step"].to(content_tracker.last_used_step.device))

    torch.set_rng_state(ckpt["torch_rng_state"])
    if torch.cuda.is_available() and ckpt.get("cuda_rng_state_all") is not None:
        torch.cuda.set_rng_state_all(ckpt["cuda_rng_state_all"])
    np.random.set_state(ckpt["np_rng_state"])
    random.setstate(ckpt["py_rng_state"])

    return int(ckpt["step"]), int(ckpt["tokens_seen"])


def main() -> None:
    args = parse_args()
    set_seed(args.seed)

    out = Path(args.output_dir)
    out.mkdir(parents=True, exist_ok=True)
    ckpt_dir = out / "checkpoints"
    ckpt_dir.mkdir(parents=True, exist_ok=True)
    metrics_jsonl = out / "train_metrics.jsonl"
    summary_json = out / "train_summary.json"

    device = torch.device(args.device)
    dtype = choose_dtype(args.dtype)

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

    # Resolve hidden size via tiny probe pass
    enc0 = tokenizer(["hello world"], return_tensors="pt", padding=True, truncation=True, max_length=8)
    with torch.no_grad():
        out0 = model_lm(
            input_ids=enc0["input_ids"].to(device),
            attention_mask=enc0["attention_mask"].to(device),
            output_hidden_states=True,
            use_cache=False,
        )
    hs_idx = resolve_hidden_state_index(args.layer_index, len(out0.hidden_states))
    d_model = int(out0.hidden_states[hs_idx].shape[-1])

    msae = K2MSAE(
        d_model=d_model,
        m_pos=args.m_pos,
        k_pos=args.k_pos,
        m_content=args.m_content,
        k_content=args.k_content,
    ).to(device)

    optimizer = torch.optim.Adam(
        msae.parameters(),
        lr=args.lr,
        betas=(args.adam_beta1, args.adam_beta2),
        eps=args.adam_eps,
    )

    def lr_lambda(step: int) -> float:
        if args.warmup_steps <= 0:
            return 1.0
        return min(1.0, float(step + 1) / float(args.warmup_steps))

    scheduler = torch.optim.lr_scheduler.LambdaLR(optimizer, lr_lambda=lr_lambda)

    pos_tracker = DeadTracker(args.m_pos, device=device)
    content_tracker = DeadTracker(args.m_content, device=device)

    step = 0
    tokens_seen = 0
    if args.resume_path:
        step, tokens_seen = load_checkpoint(
            path=Path(args.resume_path),
            model=msae,
            optimizer=optimizer,
            scheduler=scheduler,
            pos_tracker=pos_tracker,
            content_tracker=content_tracker,
        )

    accum_steps = max(1, math.ceil(args.effective_batch_size / args.microbatch_size))
    accum_count = 0
    source_configs = parse_source_configs(args.source_configs_csv)
    text_iter = iter_texts(
        dataset_name=args.dataset_name,
        dataset_config=args.dataset_config,
        dataset_split=args.dataset_split,
        streaming=args.streaming,
        balanced_interleave_sources=args.balanced_interleave_sources,
        source_configs=source_configs,
    )

    pretok_provider: PretokBatchProvider | None = None
    data_mode_effective = "interleaved_stream"
    if args.data_pipeline_mode == "pretok_warm_then_stream" and args.pretok_warm_tokens > 0:
        remaining_tokens = max(0, int(args.target_tokens) - int(tokens_seen))
        warm_tokens = min(int(args.pretok_warm_tokens), remaining_tokens)
        if warm_tokens > 0:
            pretok_dir = Path(args.pretok_dir) if args.pretok_dir else (out / "pretok_cache")
            print(
                f"[pretok] building warm shard cache "
                f"tokens={warm_tokens} dir={pretok_dir} "
                f"source_configs={source_configs if source_configs else [args.dataset_config]}"
            )
            pretok_manifest = build_pretokenized_warm_cache(
                pretok_dir=pretok_dir,
                tokenizer=tokenizer,
                text_iter=text_iter,
                text_field=args.text_field,
                context_length=args.context_length,
                model_batch_size=args.model_batch_size,
                skip_first_position=args.skip_first_position,
                target_valid_tokens=warm_tokens,
                shard_sequences=args.pretok_shard_sequences,
            )
            pretok_provider = PretokBatchProvider(
                manifest=pretok_manifest,
                model_batch_size=args.model_batch_size,
                seed=args.seed,
            )
            data_mode_effective = "pretok_warm_then_stream"

    start_time = time.time()
    last_log_time = start_time
    last_ckpt_tokens = tokens_seen
    optimizer.zero_grad(set_to_none=True)

    running = {
        "recon_loss": 0.0,
        "incoh": 0.0,
        "total": 0.0,
        "fvu_total": 0.0,
        "fvu_pos": 0.0,
        "fvu_content": 0.0,
        "delta_drop_pos": 0.0,
        "delta_drop_content": 0.0,
        "energy_ratio_pos": 0.0,
        "energy_ratio_content": 0.0,
        "n_micro": 0,
        "n_tok": 0,
        "revived_pos": 0,
        "revived_content": 0,
    }
    window_usage_pos = torch.zeros(args.m_pos, dtype=torch.float32, device=device)
    window_usage_content = torch.zeros(args.m_content, dtype=torch.float32, device=device)
    running["rows"] = 0
    running["tok_wall"] = 0.0
    running["source_counts"] = Counter()
    running["data_mode_pretok_batches"] = 0
    running["data_mode_stream_batches"] = 0

    def flush_log() -> None:
        nonlocal last_log_time
        if running["n_micro"] == 0:
            return
        now = time.time()
        elapsed = now - start_time
        dt = max(1e-6, now - last_log_time)
        tok_rate = running["n_tok"] / dt
        window_tok_m = max(1e-9, running["n_tok"] / 1_000_000.0)
        active_latent_frac_pos = float((window_usage_pos > 0).float().mean().item())
        active_latent_frac_content = float((window_usage_content > 0).float().mean().item())
        usage_entropy_pos, usage_gini_pos = usage_entropy_and_gini(window_usage_pos)
        usage_entropy_content, usage_gini_content = usage_entropy_and_gini(window_usage_content)
        st = StepStats(
            step=step,
            tokens_seen=tokens_seen,
            recon_loss=running["recon_loss"] / running["n_micro"],
            incoh_loss_est=running["incoh"] / running["n_micro"],
            total_loss=running["total"] / running["n_micro"],
            fvu_total=running["fvu_total"] / running["n_micro"],
            fvu_pos=running["fvu_pos"] / running["n_micro"],
            fvu_content=running["fvu_content"] / running["n_micro"],
            fvu_only_pos=running["fvu_pos"] / running["n_micro"],
            fvu_only_content=running["fvu_content"] / running["n_micro"],
            delta_drop_pos=running["delta_drop_pos"] / running["n_micro"],
            delta_drop_content=running["delta_drop_content"] / running["n_micro"],
            energy_ratio_pos=running["energy_ratio_pos"] / running["n_micro"],
            energy_ratio_content=running["energy_ratio_content"] / running["n_micro"],
            active_latent_frac_pos=active_latent_frac_pos,
            active_latent_frac_content=active_latent_frac_content,
            usage_entropy_pos=usage_entropy_pos,
            usage_entropy_content=usage_entropy_content,
            usage_gini_pos=usage_gini_pos,
            usage_gini_content=usage_gini_content,
            revival_rate_pos_per_mtok=running["revived_pos"] / window_tok_m,
            revival_rate_content_per_mtok=running["revived_content"] / window_tok_m,
            pos_dead_fraction=pos_tracker.dead_fraction(step, args.dead_after_steps),
            content_dead_fraction=content_tracker.dead_fraction(step, args.dead_after_steps),
            throughput_tok_s=tok_rate,
            elapsed_s=elapsed,
        )
        rec = asdict(st)
        rec["metrics_schema_version"] = METRICS_SCHEMA_VERSION
        rec["lr"] = optimizer.param_groups[0]["lr"]
        rec["accum_steps"] = accum_steps
        rec["revived_pos_last_window"] = running["revived_pos"]
        rec["revived_content_last_window"] = running["revived_content"]
        rec["data_mode_effective"] = data_mode_effective
        rec["stream_rows_last_window"] = int(running["rows"])
        rec["stream_tokenizer_sec_last_window"] = float(running["tok_wall"])
        rec["stream_rows_per_sec"] = float(running["rows"] / max(1e-6, dt))
        rec["stream_tokenizer_rows_per_sec"] = float(running["rows"] / max(1e-6, running["tok_wall"]))
        rec["data_mode_pretok_batches_last_window"] = int(running["data_mode_pretok_batches"])
        rec["data_mode_stream_batches_last_window"] = int(running["data_mode_stream_batches"])
        rec["source_mix_last_window"] = dict(running["source_counts"])
        with open(metrics_jsonl, "a", encoding="utf-8") as f:
            f.write(json.dumps(rec) + "\n")
        source_summary = "-"
        if running["source_counts"]:
            top = running["source_counts"].most_common(3)
            source_summary = ",".join(f"{k}:{v}" for k, v in top)
        print(
            "[train] "
            f"step={step} tokens={tokens_seen} loss={rec['total_loss']:.6f} "
            f"recon={rec['recon_loss']:.6f} incoh={rec['incoh_loss_est']:.6f} "
            f"fvu={rec['fvu_total']:.6f} tok_s={rec['throughput_tok_s']:.1f} "
            f"rows_s={rec['stream_rows_per_sec']:.1f} tokzr_rows_s={rec['stream_tokenizer_rows_per_sec']:.1f} "
            f"src={source_summary} "
            f"dead_pos={rec['pos_dead_fraction']:.4f} dead_content={rec['content_dead_fraction']:.4f}"
        )
        running.update(
            {
                k: 0.0
                for k in [
                    "recon_loss",
                    "incoh",
                    "total",
                    "fvu_total",
                    "fvu_pos",
                    "fvu_content",
                    "delta_drop_pos",
                    "delta_drop_content",
                    "energy_ratio_pos",
                    "energy_ratio_content",
                ]
            }
        )
        running.update({"n_micro": 0, "n_tok": 0, "revived_pos": 0, "revived_content": 0})
        running["rows"] = 0
        running["tok_wall"] = 0.0
        running["source_counts"] = Counter()
        running["data_mode_pretok_batches"] = 0
        running["data_mode_stream_batches"] = 0
        window_usage_pos.zero_()
        window_usage_content.zero_()
        last_log_time = now

    while tokens_seen < args.target_tokens:
        use_pretok = pretok_provider is not None
        if use_pretok:
            ids_np, mask_np = pretok_provider.next_batch()
            input_ids = torch.from_numpy(ids_np.astype(np.int64, copy=False)).to(device)
            attention_mask = torch.from_numpy(mask_np.astype(np.int64, copy=False)).to(device)
            running["data_mode_pretok_batches"] += 1
        else:
            batch_texts: list[str] = []
            t_sources: list[str] = []
            while len(batch_texts) < args.model_batch_size:
                row = next(text_iter)
                source = str(row.get("_source_config", row.get("domain", "unknown")))
                t = normalize_text_field(row, args.text_field).strip()
                if t:
                    batch_texts.append(t)
                    t_sources.append(source)
            tok_t0 = time.time()
            enc = tokenizer(
                batch_texts,
                return_tensors="pt",
                truncation=True,
                padding=True,
                max_length=args.context_length,
            )
            running["tok_wall"] += float(time.time() - tok_t0)
            running["rows"] += len(batch_texts)
            for s in t_sources:
                running["source_counts"][s] += 1
            input_ids = enc["input_ids"].to(device)
            attention_mask = enc["attention_mask"].to(device)
            running["data_mode_stream_batches"] += 1

        with torch.no_grad():
            out_h = model_lm(
                input_ids=input_ids,
                attention_mask=attention_mask,
                output_hidden_states=True,
                use_cache=False,
            )
        h = out_h.hidden_states[hs_idx].detach()  # [B, T, D]

        valid = attention_mask.bool()
        if args.skip_first_position:
            valid[:, 0] = False
        x = h[valid]  # [N, D]
        if x.shape[0] == 0:
            continue
        x = x.float()

        perm = torch.randperm(x.shape[0], device=device)
        for s in range(0, x.shape[0], args.microbatch_size):
            if tokens_seen >= args.target_tokens:
                break
            idx = perm[s : s + args.microbatch_size]
            xb = x[idx]
            out_b = msae(xb)

            recon = out_b["recon"]
            recon_loss = F.mse_loss(recon, xb)

            d_pos = F.normalize(msae.pos.decoder, dim=1)
            d_content = F.normalize(msae.content.decoder, dim=1)
            incoh = incoherence_estimate(
                d_pos=d_pos,
                d_content=d_content,
                sample_pos=args.inc_sample_rows_pos,
                sample_content=args.inc_sample_rows_content,
            )
            loss = recon_loss + args.lambda_inc * incoh
            (loss / float(accum_steps)).backward()

            var_x = torch.var(xb, unbiased=False) + 1e-8
            fvu_total = F.mse_loss(recon, xb) / var_x
            fvu_pos = F.mse_loss(out_b["recon_pos"], xb) / var_x
            fvu_content = F.mse_loss(out_b["recon_content"], xb) / var_x
            energy_ratio_pos = torch.var(out_b["recon_pos"], unbiased=False) / var_x
            energy_ratio_content = torch.var(out_b["recon_content"], unbiased=False) / var_x
            delta_drop_pos = fvu_content - fvu_total
            delta_drop_content = fvu_pos - fvu_total

            pos_tracker.update(out_b["idx_pos"], step)
            content_tracker.update(out_b["idx_content"], step)
            window_usage_pos += torch.bincount(
                out_b["idx_pos"].reshape(-1), minlength=args.m_pos
            ).float()
            window_usage_content += torch.bincount(
                out_b["idx_content"].reshape(-1), minlength=args.m_content
            ).float()

            bsz = int(xb.shape[0])
            tokens_seen += bsz
            accum_count += 1
            running["recon_loss"] += float(recon_loss.detach().item())
            running["incoh"] += float(incoh.detach().item())
            running["total"] += float(loss.detach().item())
            running["fvu_total"] += float(fvu_total.detach().item())
            running["fvu_pos"] += float(fvu_pos.detach().item())
            running["fvu_content"] += float(fvu_content.detach().item())
            running["delta_drop_pos"] += float(delta_drop_pos.detach().item())
            running["delta_drop_content"] += float(delta_drop_content.detach().item())
            running["energy_ratio_pos"] += float(energy_ratio_pos.detach().item())
            running["energy_ratio_content"] += float(energy_ratio_content.detach().item())
            running["n_micro"] += 1
            running["n_tok"] += bsz

            if accum_count >= accum_steps or tokens_seen >= args.target_tokens:
                optimizer.step()
                scheduler.step()
                optimizer.zero_grad(set_to_none=True)
                msae.renorm_decoders()
                step += 1
                accum_count = 0

                if args.auxk_revive:
                    running["revived_pos"] += maybe_revive_dead_latents(
                        branch=msae.pos,
                        tracker=pos_tracker,
                        step=step,
                        dead_after_steps=args.dead_after_steps,
                        revive_per_step=args.revive_per_step,
                        x_batch=xb,
                    )
                    running["revived_content"] += maybe_revive_dead_latents(
                        branch=msae.content,
                        tracker=content_tracker,
                        step=step,
                        dead_after_steps=args.dead_after_steps,
                        revive_per_step=args.revive_per_step,
                        x_batch=xb,
                    )

                if step % args.log_every_steps == 0:
                    flush_log()

                if tokens_seen - last_ckpt_tokens >= args.checkpoint_every_tokens:
                    ckpt_path = ckpt_dir / f"ckpt_step{step}_tok{tokens_seen}.pt"
                    ok, err = try_save_checkpoint(
                        path=ckpt_path,
                        model=msae,
                        optimizer=optimizer,
                        scheduler=scheduler,
                        step=step,
                        tokens_seen=tokens_seen,
                        pos_tracker=pos_tracker,
                        content_tracker=content_tracker,
                        args=args,
                    )
                    if not ok:
                        print(f"[warn] checkpoint save failed path={ckpt_path} err={err}")
                    else:
                        print(f"[checkpoint] saved {ckpt_path}")
                    last_ckpt_tokens = tokens_seen

    flush_log()
    final_ckpt = ckpt_dir / f"final_step{step}_tok{tokens_seen}.pt"
    final_ckpt_saved = ""
    ok, err = try_save_checkpoint(
        path=final_ckpt,
        model=msae,
        optimizer=optimizer,
        scheduler=scheduler,
        step=step,
        tokens_seen=tokens_seen,
        pos_tracker=pos_tracker,
        content_tracker=content_tracker,
        args=args,
    )
    if not ok:
        print(f"[warn] final checkpoint save failed path={final_ckpt} err={err}")
    else:
        final_ckpt_saved = str(final_ckpt)

    metrics_rows: list[dict[str, Any]] = []
    if metrics_jsonl.exists():
        with open(metrics_jsonl, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    metrics_rows.append(json.loads(line))
                except Exception:
                    continue

    summary = {
        "model_name": args.model_name,
        "layer_index": args.layer_index,
        "seed": args.seed,
        "lambda_inc": args.lambda_inc,
        "target_tokens": args.target_tokens,
        "tokens_seen": tokens_seen,
        "steps": step,
        "elapsed_sec": time.time() - start_time,
        "throughput_tok_s": tokens_seen / max(1e-6, (time.time() - start_time)),
        "pos_dead_fraction_final": pos_tracker.dead_fraction(step, args.dead_after_steps),
        "content_dead_fraction_final": content_tracker.dead_fraction(step, args.dead_after_steps),
        "checkpoint_final": final_ckpt_saved,
        "git_commit_hash": args.git_commit_hash,
        "metrics_schema_version": METRICS_SCHEMA_VERSION,
        "data_pipeline_mode_requested": args.data_pipeline_mode,
        "data_pipeline_mode_effective": data_mode_effective,
        "source_configs": source_configs,
        "balanced_interleave_sources": bool(args.balanced_interleave_sources),
        "pretok_warm_tokens": int(args.pretok_warm_tokens),
        "pretok_shard_sequences": int(args.pretok_shard_sequences),
        "tail100_fvu_total_median": tail_median(metrics_rows, "fvu_total", 100),
        "tail500_fvu_total_median": tail_median(metrics_rows, "fvu_total", 500),
        "tail100_incoh_loss_est_median": tail_median(metrics_rows, "incoh_loss_est", 100),
        "tail500_incoh_loss_est_median": tail_median(metrics_rows, "incoh_loss_est", 500),
        "tail100_fvu_total_slope": tail_slope(metrics_rows, "fvu_total", 100),
        "tail100_incoh_loss_est_slope": tail_slope(metrics_rows, "incoh_loss_est", 100),
        "tail100_stream_rows_per_sec_median": tail_median(metrics_rows, "stream_rows_per_sec", 100),
        "tail100_stream_tokenizer_rows_per_sec_median": tail_median(metrics_rows, "stream_tokenizer_rows_per_sec", 100),
        "tail100_active_latent_frac_pos_median": tail_median(metrics_rows, "active_latent_frac_pos", 100),
        "tail100_active_latent_frac_content_median": tail_median(metrics_rows, "active_latent_frac_content", 100),
        "tail100_usage_entropy_pos_median": tail_median(metrics_rows, "usage_entropy_pos", 100),
        "tail100_usage_entropy_content_median": tail_median(metrics_rows, "usage_entropy_content", 100),
        "tail_windows": {
            "100": {
                "fvu_total_median": tail_median(metrics_rows, "fvu_total", 100),
                "incoh_loss_est_median": tail_median(metrics_rows, "incoh_loss_est", 100),
                "recon_loss_median": tail_median(metrics_rows, "recon_loss", 100),
            },
            "500": {
                "fvu_total_median": tail_median(metrics_rows, "fvu_total", 500),
                "incoh_loss_est_median": tail_median(metrics_rows, "incoh_loss_est", 500),
                "recon_loss_median": tail_median(metrics_rows, "recon_loss", 500),
            },
        },
    }
    with open(summary_json, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)

    print(f"[done] wrote {summary_json}")


if __name__ == "__main__":
    main()
