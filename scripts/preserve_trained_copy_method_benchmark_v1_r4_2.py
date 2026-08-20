#!/usr/bin/env python3
"""Write/verify the immutable post-result inventory for trained-copy R4.2."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
from typing import Any

ROOT = Path(os.environ.get("MSAE_ROOT", Path(__file__).resolve().parents[1])).resolve()
OUT = ROOT / "reports/provenance/trained_copy_method_benchmark_v1_r4_2_postresult/PRESERVATION.json"
ATTEST = ROOT / "reports/provenance/trained_copy_method_benchmark_v1_r4_2_postresult/ATTESTATION.json"
RESULT = ROOT / "results/trained_copy_method_benchmark_v1_20260810r4_2/final/result.json"
EXPECTED_RESULT_SHA256 = "817afa4c2c2bccc543d92ec0975f3e1db619d5e78b29883c269fe07aca5e22f8"


def sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def record(path: Path) -> dict[str, Any]:
    return {"path": path.relative_to(ROOT).as_posix(), "bytes": path.stat().st_size, "sha256": sha(path)}


def inventory() -> list[Path]:
    fixed = [
        ROOT / "PLAN_TRAINED_COPY_METHOD_BENCHMARK_V1_R4_2.md",
        ROOT / "scripts/trained_copy_method_benchmark_v1_r4_2.py",
        ROOT / "scripts/launch_trained_copy_method_benchmark_v1_r4_2_tmux.sh",
        ROOT / "tests/test_trained_copy_method_benchmark_v1_r4_2.py",
        ROOT / "reports/adversarial/trained_copy_method_benchmark_v1_r4_2_candidate_review.md",
        ROOT / "reports/adversarial/trained_copy_method_benchmark_v1_r4_2_frozen_review.md",
        ROOT / "reports/claim_review/trained_copy_method_benchmark_v1_r4_2_post_result_claim_review.md",
        ROOT / "reports/provenance/trained_copy_method_benchmark_v1_r4_2_REVIEW_BINDING.json",
        ROOT / "reports/provenance/trained_copy_method_benchmark_v1_r4_2_launcher_20260810.log",
        ROOT / "configs/trained_copy_external_v1_r5/run.json",
        ROOT / "configs/trained_copy_external_v1_r5/FREEZE.json",
        ROOT / "reports/provenance/capacity_external_validity_v1_r5_postresult/PRESERVATION.json",
        ROOT / "scripts/capacity_external_validity_v1_r5.py",
    ]
    for seed in (5101, 5102, 5103):
        fixed.append(ROOT / f"results/trained_copy_external_v1_20260810r5/checkpoints/model_seed{seed}.pt")
    dynamic: list[Path] = []
    for base in [
        ROOT / "configs/trained_copy_method_benchmark_v1_r4_2",
        ROOT / "data/trained_copy_method_benchmark_v1_r4_2_prepared",
        ROOT / "reports/provenance/trained_copy_method_benchmark_v1_r4_2_candidate",
        ROOT / "reports/provenance/trained_copy_method_benchmark_v1_r4_2_run_20260810",
        ROOT / "results/trained_copy_method_benchmark_v1_20260810r4_2",
    ]:
        dynamic.extend(p for p in base.rglob("*") if p.is_file())
    paths = sorted(set(fixed + dynamic))
    missing = [p for p in paths if not p.is_file()]
    if missing:
        raise RuntimeError(f"missing R4.2 artifacts: {missing}")
    return paths


def build() -> dict[str, Any]:
    result = json.loads(RESULT.read_text())
    terminal = json.loads(
        (ROOT / "reports/provenance/trained_copy_method_benchmark_v1_r4_2_run_20260810/TERMINAL.json").read_text()
    )
    if sha(RESULT) != EXPECTED_RESULT_SHA256:
        raise RuntimeError("R4.2 final result hash mismatch")
    if result.get("status") != "METHOD_BENCHMARK_COMPLETE" or result.get("confirmation_opened") is not True:
        raise RuntimeError("R4.2 final status mismatch")
    if terminal.get("status") != "METHOD_BENCHMARK_COMPLETE":
        raise RuntimeError("R4.2 terminal mismatch")
    return {
        "schema_version": "trained_copy_method_benchmark_v1_r4_2_postresult_preservation",
        "status": "PRESERVED_COMPLETE_NO_RETRY",
        "no_retry_authorized": True,
        "r4_2_mutation_authorized": False,
        "final_result_sha256": EXPECTED_RESULT_SHA256,
        "artifacts": [record(path) for path in inventory()],
    }


def verify() -> dict[str, Any]:
    got = json.loads(OUT.read_text())
    if got != build():
        raise RuntimeError("R4.2 preservation drift")
    attestation = json.loads(ATTEST.read_text())
    expected_attestation = {
        "schema_version": "trained_copy_method_benchmark_v1_r4_2_preservation_attestation",
        "preservation_path": OUT.relative_to(ROOT).as_posix(),
        "preservation_sha256": sha(OUT),
        "status": "VERIFIED",
    }
    if attestation != expected_attestation:
        raise RuntimeError("R4.2 preservation attestation drift")
    return {"status": "PASS", "artifacts": len(got["artifacts"]), "preservation_sha256": sha(OUT)}


def write_once(path: Path, payload: dict[str, Any]) -> None:
    if path.exists():
        raise FileExistsError(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    data = (json.dumps(payload, indent=2, sort_keys=True, allow_nan=False) + "\n").encode()
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o444)
    with os.fdopen(fd, "wb") as handle:
        handle.write(data)
        handle.flush()
        os.fsync(handle.fileno())
    os.chmod(path, 0o444)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--verify", action="store_true")
    args = parser.parse_args()
    if not args.verify:
        write_once(OUT, build())
        write_once(
            ATTEST,
            {
                "schema_version": "trained_copy_method_benchmark_v1_r4_2_preservation_attestation",
                "preservation_path": OUT.relative_to(ROOT).as_posix(),
                "preservation_sha256": sha(OUT),
                "status": "VERIFIED",
            },
        )
    print(json.dumps(verify(), sort_keys=True))


if __name__ == "__main__":
    main()
