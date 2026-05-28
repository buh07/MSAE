#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import math
import os
import random
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Iterator

import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F
from datasets import load_dataset
from transformers import AutoModelForCausalLM, AutoTokenizer


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


def iter_texts(dataset_name: str, dataset_config: str, dataset_split: str, streaming: bool) -> Iterator[dict[str, Any]]:
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

    text_iter = iter_texts(
        dataset_name=args.dataset_name,
        dataset_config=args.dataset_config,
        dataset_split=args.dataset_split,
        streaming=args.streaming,
    )

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
        "n_micro": 0,
        "n_tok": 0,
        "revived_pos": 0,
        "revived_content": 0,
    }

    def flush_log() -> None:
        nonlocal last_log_time
        if running["n_micro"] == 0:
            return
        now = time.time()
        elapsed = now - start_time
        dt = max(1e-6, now - last_log_time)
        tok_rate = running["n_tok"] / dt
        st = StepStats(
            step=step,
            tokens_seen=tokens_seen,
            recon_loss=running["recon_loss"] / running["n_micro"],
            incoh_loss_est=running["incoh"] / running["n_micro"],
            total_loss=running["total"] / running["n_micro"],
            fvu_total=running["fvu_total"] / running["n_micro"],
            fvu_pos=running["fvu_pos"] / running["n_micro"],
            fvu_content=running["fvu_content"] / running["n_micro"],
            pos_dead_fraction=pos_tracker.dead_fraction(step, args.dead_after_steps),
            content_dead_fraction=content_tracker.dead_fraction(step, args.dead_after_steps),
            throughput_tok_s=tok_rate,
            elapsed_s=elapsed,
        )
        rec = asdict(st)
        rec["lr"] = optimizer.param_groups[0]["lr"]
        rec["accum_steps"] = accum_steps
        rec["revived_pos_last_window"] = running["revived_pos"]
        rec["revived_content_last_window"] = running["revived_content"]
        with open(metrics_jsonl, "a", encoding="utf-8") as f:
            f.write(json.dumps(rec) + "\n")
        print(
            "[train] "
            f"step={step} tokens={tokens_seen} loss={rec['total_loss']:.6f} "
            f"recon={rec['recon_loss']:.6f} incoh={rec['incoh_loss_est']:.6f} "
            f"fvu={rec['fvu_total']:.6f} tok_s={rec['throughput_tok_s']:.1f} "
            f"dead_pos={rec['pos_dead_fraction']:.4f} dead_content={rec['content_dead_fraction']:.4f}"
        )
        running.update({k: 0.0 for k in ["recon_loss", "incoh", "total", "fvu_total", "fvu_pos", "fvu_content"]})
        running.update({"n_micro": 0, "n_tok": 0, "revived_pos": 0, "revived_content": 0})
        last_log_time = now

    while tokens_seen < args.target_tokens:
        batch_texts: list[str] = []
        while len(batch_texts) < args.model_batch_size:
            row = next(text_iter)
            t = normalize_text_field(row, args.text_field).strip()
            if t:
                batch_texts.append(t)

        enc = tokenizer(
            batch_texts,
            return_tensors="pt",
            truncation=True,
            padding=True,
            max_length=args.context_length,
        )
        input_ids = enc["input_ids"].to(device)
        attention_mask = enc["attention_mask"].to(device)

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

            pos_tracker.update(out_b["idx_pos"], step)
            content_tracker.update(out_b["idx_content"], step)

            bsz = int(xb.shape[0])
            tokens_seen += bsz
            accum_count += 1
            running["recon_loss"] += float(recon_loss.detach().item())
            running["incoh"] += float(incoh.detach().item())
            running["total"] += float(loss.detach().item())
            running["fvu_total"] += float(fvu_total.detach().item())
            running["fvu_pos"] += float(fvu_pos.detach().item())
            running["fvu_content"] += float(fvu_content.detach().item())
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
    }
    with open(summary_json, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)

    print(f"[done] wrote {summary_json}")


if __name__ == "__main__":
    main()
