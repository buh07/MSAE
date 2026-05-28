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
    "lambda_inc",
    "target_tokens",
    "context_length",
    "model_batch_size",
    "microbatch_size",
    "effective_batch_size",
    "dataset_name",
    "dataset_config",
    "dataset_split",
    "text_field",
    "output_dir",
    "log_file",
    "resume_path",
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
    p = argparse.ArgumentParser(description="Queue worker for K2 MSAE training")
    p.add_argument("--manifest", required=True)
    p.add_argument("--worker", required=True)
    p.add_argument("--gpu", type=int, required=True)
    p.add_argument("--repo_root", required=True)
    p.add_argument("--train_script", required=True)
    p.add_argument("--run_root", required=True)
    p.add_argument("--git_commit_hash", default="")
    p.add_argument("--poll_sec", type=float, default=4.0)
    p.add_argument("--heartbeat_sec", type=float, default=60.0)
    p.add_argument("--checkpoint_every_tokens", type=int, default=25_000_000)
    p.add_argument("--log_every_steps", type=int, default=20)
    p.add_argument("--warmup_steps", type=int, default=1000)
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
        args.train_script,
        "--model_name",
        job["model"],
        "--seed",
        job["seed"],
        "--layer_index",
        job["layer_index"],
        "--lambda_inc",
        job["lambda_inc"],
        "--target_tokens",
        job["target_tokens"],
        "--context_length",
        job["context_length"],
        "--model_batch_size",
        job["model_batch_size"],
        "--microbatch_size",
        job["microbatch_size"],
        "--effective_batch_size",
        job["effective_batch_size"],
        "--dataset_name",
        job["dataset_name"],
        "--dataset_config",
        job["dataset_config"],
        "--dataset_split",
        job["dataset_split"],
        "--text_field",
        job["text_field"],
        "--output_dir",
        str(out_dir),
        "--checkpoint_every_tokens",
        str(args.checkpoint_every_tokens),
        "--log_every_steps",
        str(args.log_every_steps),
        "--warmup_steps",
        str(args.warmup_steps),
    ]
    if job.get("resume_path", ""):
        cmd.extend(["--resume_path", job["resume_path"]])
    if args.git_commit_hash:
        cmd.extend(["--git_commit_hash", args.git_commit_hash])

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
                    raise RuntimeError(f"train script exited with code {rc}")
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
                last_heartbeat = now_t
            time.sleep(2.0)


def main() -> None:
    args = parse_args()
    if not args.git_commit_hash:
        try:
            args.git_commit_hash = subprocess.check_output(
                ["git", "rev-parse", "HEAD"],
                cwd=args.repo_root,
                text=True,
            ).strip()
        except Exception:
            args.git_commit_hash = ""

    manifest = Path(args.manifest).resolve()

    while True:
        job = claim_job(manifest, worker=args.worker, gpu=args.gpu)
        if job is None:
            print(f"[{args.worker}] queue empty")
            break

        job_id = job["job_id"]
        print(
            f"[{args.worker}] claimed job_id={job_id} stage={job['stage']} "
            f"layer={job['layer_index']} seed={job['seed']} lambda_inc={job['lambda_inc']}"
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
        time.sleep(args.poll_sec)


if __name__ == "__main__":
    main()
