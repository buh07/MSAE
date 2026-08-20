#!/usr/bin/env python3
"""Apply each existing K=2 checkpoint to frozen L3 atlas activations."""

from __future__ import annotations

import argparse
import hashlib
import json
import time
from pathlib import Path

import numpy as np
import torch

from train_msae_k2 import K2MSAE
from atlas_freeze import (activation_artifact_digest, checkpoint_spec,
                          runtime_environment, utc_now, verify_activation_complete, verify_freeze,
                          verify_calibration_sources, verify_layer_trigger, verify_transform_complete)


ROOT = Path(__file__).resolve().parents[1]


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        while chunk := f.read(16 << 20):
            h.update(chunk)
    return h.hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--job", required=True)
    parser.add_argument("--run-root", type=Path, default=ROOT / "pilot_runs/20260731_atlas_v1_architecture_selection")
    parser.add_argument("--device", default="cuda:0")
    parser.add_argument("--batch-size", type=int, default=4096)
    args = parser.parse_args()
    freeze = verify_freeze()
    trigger_path = ROOT / "results/atlas/raw_v1/layer_trigger_freeze.json"
    verify_layer_trigger(trigger_path, freeze)
    verify_calibration_sources(trigger_path, args.run_root, freeze)
    frozen_checkpoint = checkpoint_spec(args.job)
    row = frozen_checkpoint["metadata"]
    checkpoint_path = frozen_checkpoint["path"]
    checkpoint = torch.load(checkpoint_path, map_location="cpu", weights_only=False)
    cargs = checkpoint["args"]
    device = torch.device(args.device)
    if device.type != "cuda" or not torch.cuda.is_available():
        raise RuntimeError("atlas-v1 K=2 transforms require CUDA; CPU output is refused")
    model = K2MSAE(d_model=768, m_pos=int(cargs["m_pos"]), k_pos=int(cargs["k_pos"]),
                   m_content=int(cargs["m_content"]), k_content=int(cargs["k_content"]))
    model.load_state_dict(checkpoint["model"])
    model.to(device).eval()
    output = args.run_root / "k2_transforms" / args.job
    output.mkdir(parents=True, exist_ok=True)
    if (output / "COMPLETE.json").exists():
        verify_transform_complete(output, args.job, freeze)
        print(f"already complete {output}")
        return
    if any(output.iterdir()):
        raise RuntimeError(f"incomplete transform directory is not overwritten automatically: {output}")
    started = time.time()
    started_utc = utc_now()
    role_results = {}
    source_activation_digests = {}
    for role in ["discovery", "calibration", "C2"]:
        activation_dir = args.run_root / "raw_activations" / role
        activation_record = verify_activation_complete(activation_dir, role, freeze)
        source_activation_digests[role] = activation_artifact_digest(activation_record)
        raw_path = activation_dir / "L3.float16.npy"
        raw = np.load(raw_path, mmap_mode="r")
        shape = raw.shape
        role_dir = output / role
        role_dir.mkdir(parents=True, exist_ok=True)
        pos = np.lib.format.open_memmap(role_dir / "pos.float16.npy", mode="w+", dtype=np.float16, shape=shape)
        content = np.lib.format.open_memmap(role_dir / "content.float16.npy", mode="w+", dtype=np.float16, shape=shape)
        resid = np.lib.format.open_memmap(role_dir / "resid.float16.npy", mode="w+", dtype=np.float16, shape=shape)
        sse = 0.0; energy = 0.0
        with torch.inference_mode():
            for start in range(0, len(raw), args.batch_size):
                x = torch.from_numpy(np.asarray(raw[start:start + args.batch_size], dtype=np.float32)).to(device)
                transformed = model(x)
                p = transformed["recon_pos"].detach().float().cpu().numpy()
                c = transformed["recon_content"].detach().float().cpu().numpy()
                r = np.asarray(raw[start:start + len(p)], dtype=np.float32) - p - c
                pos[start:start + len(p)] = p.astype(np.float16)
                content[start:start + len(c)] = c.astype(np.float16)
                resid[start:start + len(r)] = r.astype(np.float16)
                sse += float(np.square(r, dtype=np.float64).sum())
                energy += float(np.square(np.asarray(raw[start:start + len(r)], dtype=np.float64)).sum())
        for array in [pos, content, resid]:
            array.flush()
        artifacts = {p.name: {"sha256": sha256(p), "bytes": p.stat().st_size} for p in role_dir.iterdir() if p.is_file()}
        role_results[role] = {"rows": len(raw), "fvu_total": sse / energy, "artifacts": artifacts}
    complete = {"schema_version": "atlas_v1_k2_transform", "job_id": args.job,
                "checkpoint": row["checkpoint_relpath"], "checkpoint_sha256": frozen_checkpoint["sha256"],
                "seed": cargs["seed"], "lambda_inc": cargs["lambda_inc"], "tokens_seen": checkpoint["tokens_seen"],
                "roles": role_results, "source_activation_artifact_sha256": source_activation_digests,
                "prescore_bundle_sha256": freeze["bundle_sha256"], "elapsed_sec": time.time() - started,
                "started_utc": started_utc, "ended_utc": utc_now(),
                "resolved_config": {"device": str(device), "batch_size": args.batch_size, "checkpoint_args": cargs},
                "environment": runtime_environment(str(device))}
    (output / "COMPLETE.json").write_text(json.dumps(complete, indent=2, sort_keys=True) + "\n")
    verify_transform_complete(output, args.job, freeze)
    print(json.dumps(complete, indent=2))


if __name__ == "__main__":
    main()
