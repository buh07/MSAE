#!/usr/bin/env python3
"""Create or verify the immutable inventory of both trained-control R1 failures."""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "reports/provenance/trained_control_next_studies_v1_r1_failures_preservation.json"
ATTEST = ROOT / "reports/provenance/trained_control_next_studies_v1_r1_exposure_attestation.json"

ROOTS = [
    "results/trained_copy_sae_capacity_v1_r1_20260813",
    "results/causal_manifold_bridge_v1_r1_20260813",
    "reports/provenance/trained_copy_sae_capacity_v1_r1_run_20260813",
    "reports/provenance/causal_manifold_bridge_v1_r1_run_20260813",
]

FILES = [
    "PLAN_TRAINED_CONTROL_NEXT_STUDIES_V1.md",
    "scripts/trained_copy_sae_capacity_v1_r1.py",
    "scripts/causal_manifold_bridge_v1_r1.py",
    "scripts/launch_trained_control_next_studies_v1_r1_tmux.sh",
    "tests/test_trained_copy_sae_capacity_v1_r1.py",
    "tests/test_causal_manifold_bridge_v1_r1.py",
    "tests/test_launch_trained_control_next_studies_v1_r1.py",
    "configs/trained_copy_sae_capacity_v1_r1/run.json",
    "configs/trained_copy_sae_capacity_v1_r1/GENERATOR_LOCK.json",
    "configs/trained_copy_sae_capacity_v1_r1/FREEZE.json",
    "configs/causal_manifold_bridge_v1_r1/run.json",
    "configs/causal_manifold_bridge_v1_r1/GENERATOR_LOCK.json",
    "configs/causal_manifold_bridge_v1_r1/FREEZE.json",
    "reports/provenance/trained_copy_sae_capacity_v1_r1_candidate/CANDIDATE.json",
    "reports/provenance/causal_manifold_bridge_v1_r1_candidate/CANDIDATE.json",
    "reports/adversarial/trained_copy_sae_capacity_v1_r1_candidate_review.md",
    "reports/adversarial/trained_copy_sae_capacity_v1_r1_frozen_review.md",
    "reports/adversarial/causal_manifold_bridge_v1_r1_candidate_review.md",
    "reports/adversarial/causal_manifold_bridge_v1_r1_frozen_review.md",
    "reports/provenance/trained_copy_sae_capacity_v1_r1_REVIEW_BINDING.json",
    "reports/provenance/causal_manifold_bridge_v1_r1_REVIEW_BINDING.json",
    "reports/provenance/trained_copy_sae_capacity_v1_r1_LAUNCH.json",
    "reports/provenance/causal_manifold_bridge_v1_r1_LAUNCH.json",
    "reports/provenance/trained_copy_sae_capacity_v1_r1_launcher_20260813.log",
    "reports/provenance/causal_manifold_bridge_v1_r1_launcher_20260813.log",
    "reports/provenance/trained_control_next_studies_v1_attempt1_preservation_v2.json",
]


def canonical(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()


def sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def file_record(path: Path) -> dict[str, Any]:
    st = path.stat()
    return {
        "path": path.relative_to(ROOT).as_posix(),
        "bytes": st.st_size,
        "mtime_ns": st.st_mtime_ns,
        "sha256": sha(path),
    }


def root_record(path: Path) -> dict[str, Any]:
    if not path.is_dir():
        raise RuntimeError(f"missing R1 root: {path}")
    files = [file_record(p) for p in sorted(path.rglob("*")) if p.is_file()]
    dirs = [p.relative_to(path).as_posix() for p in sorted(path.rglob("*")) if p.is_dir()]
    return {
        "path": path.relative_to(ROOT).as_posix(),
        "files": files,
        "file_count": len(files),
        "directories": dirs,
        "directory_count": len(dirs),
    }


def absence_audit() -> dict[str, bool]:
    a_result = ROOT / ROOTS[0]
    b_result = ROOT / ROOTS[1]
    a_prov = ROOT / ROOTS[2]
    b_prov = ROOT / ROOTS[3]
    checks = {
        "a_no_confirmation_event": not any((a_prov / "events").glob("04*_CONFIRMATION*")),
        "b_no_development_event": not any((b_prov / "events").glob("02*_DEVELOPMENT*")),
        "b_no_confirmation_event": not any((b_prov / "events").glob("04*_CONFIRMATION*")),
        "a_no_serialized_development_score": not (a_result / "development").exists(),
        "b_no_serialized_development_score": not (b_result / "development").exists(),
        "a_no_confirmation_artifacts": not (a_result / "confirmation").exists(),
        "b_no_confirmation_artifacts": not (b_result / "confirmation").exists(),
        "a_no_final_result": not (a_result / "final/result.json").exists(),
        "b_no_final_result": not (b_result / "final/result.json").exists(),
        "a_no_terminal": not (a_prov / "TERMINAL.json").exists(),
        "b_no_terminal": not (b_prov / "TERMINAL.json").exists(),
    }
    if not all(checks.values()):
        raise RuntimeError(f"R1 absence audit failed: {checks}")
    return checks


def make_attestation() -> dict[str, Any]:
    body = {
        "schema_version": "trained_control_r1_exposure_attestation_v1",
        "sae_capacity_r1": {
            "fit_opened": True,
            "development_opened": True,
            "confirmation_opened": False,
            "possible_transient_native_development_scores": 1,
            "serialized_scientific_scores": 0,
            "score_values_inspected": False,
            "score_values_used_for_recovery_design": False,
            "failure": "autograd_tensor_numpy_boundary",
        },
        "causal_manifold_r1": {
            "fit_opened": True,
            "development_opened": False,
            "confirmation_opened": False,
            "serialized_scientific_scores": 0,
            "score_values_inspected": False,
            "score_values_used_for_recovery_design": False,
            "failure": "runtime_rank_condition_dtype_mismatch",
        },
        "attested_by": "root_execution_audit",
    }
    body["statement_sha256"] = hashlib.sha256(canonical(body)).hexdigest()
    return body


def create() -> dict[str, Any]:
    if OUT.exists() or ATTEST.exists():
        raise FileExistsError("R1 preservation artifacts already exist")
    attestation = make_attestation()
    ATTEST.parent.mkdir(parents=True, exist_ok=True)
    ATTEST.write_bytes(json.dumps(attestation, sort_keys=True, indent=2).encode() + b"\n")
    singletons = []
    for rel in FILES:
        p = ROOT / rel
        if not p.is_file():
            raise RuntimeError(f"missing R1 artifact: {rel}")
        singletons.append(file_record(p))
    result = {
        "schema_version": "trained_control_next_studies_v1_r1_failures_preservation_v1",
        "recorded_at": datetime.now(timezone.utc).isoformat(),
        "exposure_attestation": file_record(ATTEST),
        "singletons": singletons,
        "roots": [root_record(ROOT / rel) for rel in ROOTS],
        "absence_audit": absence_audit(),
    }
    OUT.write_bytes(json.dumps(result, sort_keys=True, indent=2).encode() + b"\n")
    return {"status": "PASS", "artifacts": len(singletons) + sum(x["file_count"] for x in result["roots"]) + 1, "preservation_sha256": sha(OUT)}


def verify() -> dict[str, Any]:
    record = json.loads(OUT.read_text())
    expected_attestation = record["exposure_attestation"]
    if file_record(ATTEST) != expected_attestation:
        raise RuntimeError("exposure attestation drift")
    for expected in record["singletons"]:
        if file_record(ROOT / expected["path"]) != expected:
            raise RuntimeError(f"R1 singleton drift: {expected['path']}")
    for expected in record["roots"]:
        if root_record(ROOT / expected["path"]) != expected:
            raise RuntimeError(f"R1 root inventory drift: {expected['path']}")
    if absence_audit() != record["absence_audit"]:
        raise RuntimeError("R1 absence audit drift")
    attestation = json.loads(ATTEST.read_text())
    signature = attestation.pop("statement_sha256")
    if hashlib.sha256(canonical(attestation)).hexdigest() != signature:
        raise RuntimeError("exposure attestation signature mismatch")
    return {"status": "PASS", "preservation_sha256": sha(OUT)}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--verify", action="store_true")
    args = parser.parse_args()
    print(json.dumps(verify() if args.verify else create(), sort_keys=True))


if __name__ == "__main__":
    main()
