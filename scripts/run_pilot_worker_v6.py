#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import fcntl
import os
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional


MANIFEST_COLUMNS = [
    "job_id",
    "stage",
    "model",
    "seed",
    "layer_index",
    "split_mode",
    "holdout_source_label",
    "max_text_samples",
    "max_tokens_collect",
    "holdout_eval_max_tokens_collect",
    "context_length",
    "batch_size",
    "top_k_tokens",
    "probe_ranks",
    "probe_torch_max_steps_raw",
    "probe_torch_max_steps_projected",
    "probe_torch_patience_raw",
    "probe_torch_patience_projected",
    "train_source_max_text_samples",
    "eval_source_max_text_samples",
    "corpus_holdout_max_text_samples",
    "source_manifest_path",
    "output_dir",
    "log_file",
    "status",
    "attempt",
    "worker",
    "gpu",
    "start_time",
    "end_time",
    "heartbeat_time",
    "error",
    "notes",
]


def now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Queue worker for MSAE pilot v6")
    p.add_argument("--manifest", required=True)
    p.add_argument("--worker", required=True)
    p.add_argument("--gpu", type=int, required=True)
    p.add_argument("--repo_root", required=True)
    p.add_argument("--pilot_script", required=True)
    p.add_argument("--summarizer_script", required=True)
    p.add_argument("--run_root", required=True)
    p.add_argument("--poll_sec", type=float, default=4.0)
    p.add_argument("--heartbeat_sec", type=float, default=60.0)
    return p.parse_args()


def read_rows_unlocked(fh) -> List[Dict[str, str]]:
    fh.seek(0)
    return list(csv.DictReader(fh, delimiter="\t"))


def write_rows_unlocked(fh, rows: List[Dict[str, str]]) -> None:
    fh.seek(0)
    fh.truncate(0)
    writer = csv.DictWriter(fh, fieldnames=MANIFEST_COLUMNS, delimiter="\t")
    writer.writeheader()
    writer.writerows(rows)


def claim_job(manifest: Path, worker: str, gpu: int) -> Optional[Dict[str, str]]:
    with open(manifest, "r+", encoding="utf-8", newline="") as fh:
        fcntl.flock(fh.fileno(), fcntl.LOCK_EX)
        rows = read_rows_unlocked(fh)
        pending = [r for r in rows if r.get("status") == "pending"]
        if not pending:
            fcntl.flock(fh.fileno(), fcntl.LOCK_UN)
            return None
        pending.sort(key=lambda r: (r.get("stage", ""), r.get("job_id", "")))
        chosen_id = pending[0]["job_id"]
        chosen = None
        for row in rows:
            if row.get("job_id") == chosen_id:
                row["status"] = "running"
                row["worker"] = worker
                row["gpu"] = str(gpu)
                row["attempt"] = str(int(row.get("attempt", "0")) + 1)
                row["start_time"] = now_iso()
                row["heartbeat_time"] = row["start_time"]
                row["end_time"] = ""
                row["error"] = ""
                chosen = dict(row)
                break
        write_rows_unlocked(fh, rows)
        fcntl.flock(fh.fileno(), fcntl.LOCK_UN)
        return chosen


def update_row(manifest: Path, job_id: str, updates: Dict[str, str]) -> None:
    with open(manifest, "r+", encoding="utf-8", newline="") as fh:
        fcntl.flock(fh.fileno(), fcntl.LOCK_EX)
        rows = read_rows_unlocked(fh)
        for row in rows:
            if row.get("job_id") == job_id:
                row.update(updates)
                break
        write_rows_unlocked(fh, rows)
        fcntl.flock(fh.fileno(), fcntl.LOCK_UN)


def run_job(args: argparse.Namespace, job: Dict[str, str], manifest: Path) -> None:
    out_dir = Path(job["output_dir"])
    out_dir.mkdir(parents=True, exist_ok=True)
    log_file = Path(job["log_file"])
    log_file.parent.mkdir(parents=True, exist_ok=True)

    cmd = [
        "python",
        "-u",
        args.pilot_script,
        "--model_name",
        job["model"],
        "--seed",
        job["seed"],
        "--layer_index",
        job["layer_index"],
        "--split_mode",
        job["split_mode"],
        "--holdout_source_label",
        job["holdout_source_label"],
        "--max_text_samples",
        job["max_text_samples"],
        "--max_tokens_collect",
        job["max_tokens_collect"],
        "--holdout_eval_max_tokens_collect",
        job["holdout_eval_max_tokens_collect"],
        "--context_length",
        job["context_length"],
        "--batch_size",
        job["batch_size"],
        "--top_k_tokens",
        job["top_k_tokens"],
        "--probe_ranks",
        job["probe_ranks"],
        "--probe_torch_max_steps_raw",
        job["probe_torch_max_steps_raw"],
        "--probe_torch_max_steps_projected",
        job["probe_torch_max_steps_projected"],
        "--probe_torch_patience_raw",
        job["probe_torch_patience_raw"],
        "--probe_torch_patience_projected",
        job["probe_torch_patience_projected"],
        "--train_source_max_text_samples",
        job["train_source_max_text_samples"],
        "--eval_source_max_text_samples",
        job["eval_source_max_text_samples"],
        "--corpus_holdout_max_text_samples",
        job["corpus_holdout_max_text_samples"],
        "--source_manifest_path",
        job["source_manifest_path"],
        "--probe_backend",
        "torch",
        "--probe_torch_scheduler",
        "cosine",
        "--probe_torch_lr",
        "0.05",
        "--probe_torch_lr_position_raw_highdim",
        "0.01",
        "--probe_torch_lr_position_raw_highdim_threshold",
        "768",
        "--probe_c_raw",
        "0.2",
        "--probe_c_projected",
        "1.0",
        "--probe_torch_eval_every",
        "50",
        "--probe_torch_min_steps",
        "200",
        "--probe_torch_token_ceiling_top1",
        "0.995",
        "--probe_torch_token_ceiling_evals",
        "3",
        "--probe_torch_token_ceiling_loss_eps",
        "1e-4",
        "--probe_torch_batch_size",
        "8192",
        "--position_max",
        "64",
        "--skip_first_position",
        "--c2_alt_mode",
        "linear_rank_drop",
        "--c2_var_v2_ratio_threshold",
        "3.0",
        "--c2_var_v2_excess_floor",
        "0.05",
        "--c3_v2_drop_fraction",
        "0.25",
        "--corpus_holdout_dataset_name",
        "Skylion007/openwebtext",
        "--corpus_holdout_dataset_split",
        "train",
        "--corpus_holdout_text_field",
        "text",
        "--output_dir",
        str(out_dir),
    ]

    env = os.environ.copy()
    env["PYTHONUNBUFFERED"] = "1"
    env["CUDA_VISIBLE_DEVICES"] = str(args.gpu)
    env["HF_HOME"] = env.get("HF_HOME", "/jumbo/lisp/f004ndc/hf_cache")
    env["HF_DATASETS_CACHE"] = env.get("HF_DATASETS_CACHE", "/jumbo/lisp/f004ndc/hf_cache/datasets")

    with open(log_file, "a", encoding="utf-8") as lf:
        lf.write(f"\n[run] {now_iso()} job_id={job['job_id']} gpu={args.gpu}\n")
        lf.flush()
        proc = subprocess.Popen(
            cmd,
            cwd=args.repo_root,
            env=env,
            stdout=lf,
            stderr=lf,
            text=True,
        )
        last_heartbeat = time.time()
        while True:
            rc = proc.poll()
            if rc is not None:
                if rc != 0:
                    raise RuntimeError(f"pilot exited with code {rc}")
                break
            now_t = time.time()
            if now_t - last_heartbeat >= float(args.heartbeat_sec):
                update_row(
                    manifest,
                    job["job_id"],
                    {
                        "heartbeat_time": now_iso(),
                        "notes": "running",
                    },
                )
                run_summarizer(args)
                last_heartbeat = now_t
            time.sleep(2.0)


def run_summarizer(args: argparse.Namespace) -> None:
    subprocess.run(
        ["python", args.summarizer_script, "--run_root", args.run_root],
        cwd=args.repo_root,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=False,
        text=True,
    )


def main() -> None:
    args = parse_args()
    manifest = Path(args.manifest).resolve()
    while True:
        job = claim_job(manifest, worker=args.worker, gpu=args.gpu)
        if job is None:
            print(f"[{args.worker}] queue empty")
            break

        job_id = job["job_id"]
        print(
            f"[{args.worker}] claimed job_id={job_id} stage={job['stage']} "
            f"model={job['model']} layer={job['layer_index']} split={job['split_mode']}"
        )
        try:
            run_job(args, job, manifest)
            update_row(
                manifest,
                job_id,
                {
                    "status": "done",
                    "end_time": now_iso(),
                    "heartbeat_time": now_iso(),
                    "notes": "completed",
                },
            )
        except Exception as exc:
            update_row(
                manifest,
                job_id,
                {
                    "status": "failed",
                    "end_time": now_iso(),
                    "heartbeat_time": now_iso(),
                    "error": str(exc),
                    "notes": "failed",
                },
            )
        finally:
            run_summarizer(args)
            time.sleep(args.poll_sec)


if __name__ == "__main__":
    main()
