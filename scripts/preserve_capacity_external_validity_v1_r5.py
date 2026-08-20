#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
from typing import Any

ROOT = Path(os.environ.get("MSAE_ROOT", Path(__file__).resolve().parents[1])).resolve()
OUT = ROOT / "reports/provenance/capacity_external_validity_v1_r5_postresult/PRESERVATION.json"
CAP_RESULT = ROOT / "results/capacity_controller_diagnostic_v1_20260810r5/final/result.json"
EXT_RESULT = ROOT / "results/trained_copy_external_v1_20260810r5/final/result.json"


def sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def record(path: Path) -> dict[str, Any]:
    return {"path": path.relative_to(ROOT).as_posix(), "bytes": path.stat().st_size, "sha256": sha(path)}


def inventory() -> list[Path]:
    fixed = [
        ROOT / "PLAN_CAPACITY_EXTERNAL_VALIDITY_V1_R5.md",
        ROOT / "configs/capacity_controller_diagnostic_v1_r5/run.json",
        ROOT / "configs/capacity_controller_diagnostic_v1_r5/RECOVERY_BINDING.json",
        ROOT / "configs/capacity_controller_diagnostic_v1_r5/FREEZE.json",
        ROOT / "configs/trained_copy_external_v1_r5/run.json",
        ROOT / "configs/trained_copy_external_v1_r5/RECOVERY_BINDING.json",
        ROOT / "configs/trained_copy_external_v1_r5/FREEZE.json",
        ROOT / "reports/adversarial/capacity_controller_diagnostic_v1_r5_candidate_review.md",
        ROOT / "reports/adversarial/trained_copy_external_v1_r5_candidate_review.md",
        ROOT / "reports/adversarial/capacity_controller_diagnostic_v1_r5_frozen_review.md",
        ROOT / "reports/adversarial/trained_copy_external_v1_r5_frozen_review.md",
        ROOT / "reports/provenance/capacity_external_validity_v1_r5_REVIEW_BINDING.json",
        ROOT / "scripts/capacity_external_validity_v1_r5.py",
        ROOT / "scripts/launch_capacity_external_validity_v1_r5_tmux.sh",
        ROOT / "tests/test_capacity_external_validity_v1_r5.py",
        CAP_RESULT,
        EXT_RESULT,
    ]
    dynamic: list[Path] = []
    for base in [
        ROOT / "results/capacity_controller_diagnostic_v1_20260810r5/checkpoints",
        ROOT / "results/trained_copy_external_v1_20260810r5/checkpoints",
        ROOT / "reports/provenance/capacity_controller_diagnostic_v1_r5_run_20260810r5",
        ROOT / "reports/provenance/trained_copy_external_v1_r5_run_20260810r5",
    ]:
        dynamic.extend(p for p in base.rglob("*") if p.is_file())
    paths = sorted(set(fixed + dynamic))
    missing = [p for p in paths if not p.is_file()]
    if missing:
        raise RuntimeError(f"missing R5 artifacts: {missing}")
    return paths


def build() -> dict[str, Any]:
    cap = json.loads(CAP_RESULT.read_text())
    ext = json.loads(EXT_RESULT.read_text())
    cap_ckpts = list((ROOT / "results/capacity_controller_diagnostic_v1_20260810r5/checkpoints").rglob("*.pt"))
    ext_ckpts = list((ROOT / "results/trained_copy_external_v1_20260810r5/checkpoints").rglob("*.pt"))
    if cap.get("status") != "CAPACITY_DIAGNOSTIC_COMPLETE" or cap.get("external_authorized") is not True:
        raise RuntimeError("capacity R5 terminal mismatch")
    if ext.get("status") != "TRAINED_COPY_EXTERNAL_QUALIFIED" or ext.get("all_seeds_both_panels_pass") is not True:
        raise RuntimeError("external R5 terminal mismatch")
    if len(cap_ckpts) != 117 or len(ext_ckpts) != 3:
        raise RuntimeError("R5 checkpoint count mismatch")
    terminals = list((ROOT / "reports/provenance").glob("*r5*/*TECHNICAL*"))
    if terminals:
        raise RuntimeError(f"unexpected R5 technical terminal: {terminals}")
    return {
        "schema_version": "capacity_external_validity_v1_r5_postresult_preservation",
        "status": "PRESERVED_COMPLETE_NO_RETRY",
        "no_retry_authorized": True,
        "r5_mutation_authorized": False,
        "capacity_result_sha256": sha(CAP_RESULT),
        "external_result_sha256": sha(EXT_RESULT),
        "capacity_checkpoint_count": len(cap_ckpts),
        "external_checkpoint_count": len(ext_ckpts),
        "technical_terminal_count": 0,
        "artifacts": [record(p) for p in inventory()],
    }


def verify() -> dict[str, Any]:
    got = json.loads(OUT.read_text())
    expected = build()
    if got != expected:
        raise RuntimeError("R5 preservation drift")
    return {"status": "PASS", "path": OUT.relative_to(ROOT).as_posix(), "sha256": sha(OUT), "artifacts": len(got["artifacts"])}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--verify", action="store_true")
    args = ap.parse_args()
    if args.verify:
        print(json.dumps(verify(), sort_keys=True))
        return
    if OUT.exists():
        raise FileExistsError(OUT)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    payload = build()
    data = (json.dumps(payload, indent=2, sort_keys=True) + "\n").encode()
    fd = os.open(OUT, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o444)
    with os.fdopen(fd, "wb") as f:
        f.write(data); f.flush(); os.fsync(f.fileno())
    os.chmod(OUT, 0o444)
    print(json.dumps(verify(), sort_keys=True))


if __name__ == "__main__":
    main()
