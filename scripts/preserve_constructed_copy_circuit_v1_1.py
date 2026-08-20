#!/usr/bin/env python3
"""Create/verify the immutable post-result preservation bundle for constructed-copy v1.1."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
from typing import Any

ROOT = Path(os.environ.get("MSAE_ROOT", Path.cwd()))
FREEZE = ROOT / "configs/constructed_copy_circuit_v1_1/FREEZE.json"
OUT = ROOT / "reports/provenance/constructed_copy_circuit_v1_1_postresult"
MANIFEST = OUT / "PRESERVATION.json"
SNAPSHOTS = {
    "PAPER.md": OUT / "PAPER.pre_constructed_v1_1_postresult.md",
    "reports/paper_claim_ledger_v1.json": OUT / "paper_claim_ledger_v1.pre_constructed_v1_1_postresult.json",
}


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def rec(path: Path) -> dict[str, Any]:
    return {"path": path.relative_to(ROOT).as_posix(), "bytes": path.stat().st_size, "sha256": sha(path)}


def frozen_paths() -> list[Path]:
    exact = [
        ROOT / "PLAN_CONSTRUCTED_COPY_CIRCUIT_V1_1.md",
        ROOT / "scripts/constructed_copy_circuit_v1_1.py",
        ROOT / "scripts/launch_constructed_copy_circuit_v1_1_tmux.sh",
        ROOT / "tests/test_constructed_copy_circuit_v1_1.py",
        ROOT / "reports/claim_review/constructed_copy_circuit_v1_1_post_result_claim_review.md",
    ]
    roots = [
        ROOT / "configs/constructed_copy_circuit_v1_1",
        ROOT / "data/constructed_copy_circuit_v1_1_prepared",
        ROOT / "results/constructed_copy_circuit_v1_1_20260809",
        ROOT / "reports/provenance/constructed_copy_circuit_v1_1_candidate",
        ROOT / "reports/provenance/constructed_copy_circuit_v1_1_run_20260809",
    ]
    exact.extend(sorted((ROOT / "reports/adversarial").glob("constructed_copy_circuit_v1_1_*.md")))
    for base in roots:
        exact.extend(sorted(p for p in base.rglob("*") if p.is_file()))
    exact.extend(SNAPSHOTS.values())
    unique = {p.relative_to(ROOT).as_posix(): p for p in exact}
    missing = [name for name, p in unique.items() if not p.is_file()]
    if missing:
        raise RuntimeError(f"missing v1.1 preservation artifacts: {missing}")
    return [unique[k] for k in sorted(unique)]


def verify_original_freeze_with_snapshots() -> None:
    freeze = json.loads(FREEZE.read_text())
    for item in freeze["candidate_inventory"]:
        rel = item["path"]
        path = SNAPSHOTS.get(rel, ROOT / rel)
        if not path.is_file() or path.stat().st_size != item["bytes"] or sha(path) != item["sha256"]:
            raise RuntimeError(f"original v1.1 freeze mismatch via preservation mapping: {rel}")


def create() -> None:
    if MANIFEST.exists() or any(p.exists() for p in SNAPSHOTS.values()):
        raise RuntimeError("v1.1 post-result preservation output already exists")
    OUT.mkdir(parents=True, exist_ok=False)
    for rel, target in SNAPSHOTS.items():
        target.write_bytes((ROOT / rel).read_bytes())
    verify_original_freeze_with_snapshots()
    final = json.loads((ROOT / "results/constructed_copy_circuit_v1_1_20260809/final/result.json").read_text())
    if final["status"] != "GROUND_TRUTH_CIRCUIT_CONTROL_CONFIRMED":
        raise RuntimeError("unexpected v1.1 final status")
    if final["training_performed"] or final["representation_methods_evaluated"]:
        raise RuntimeError("v1.1 scope drift")
    inventory = [rec(p) for p in frozen_paths()]
    payload = {
        "schema_version": "constructed_copy_circuit_v1_1_postresult_preservation_v1",
        "status": "PRESERVED",
        "original_freeze": rec(FREEZE),
        "original_freeze_documents_verified_via_immutable_snapshots": {
            rel: rec(path) for rel, path in SNAPSHOTS.items()
        },
        "live_documents_intentionally_superseded_after_snapshot": sorted(SNAPSHOTS),
        "original_freeze_and_verifier_modified": False,
        "immutable_experiment_namespace_files_modified": False,
        "final_status": final["status"],
        "training_performed": False,
        "representation_methods_evaluated": False,
        "inventory": inventory,
        "inventory_sha256": hashlib.sha256(json.dumps(inventory, sort_keys=True, separators=(",", ":")).encode()).hexdigest(),
    }
    MANIFEST.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    verify()


def verify() -> None:
    payload = json.loads(MANIFEST.read_text())
    verify_original_freeze_with_snapshots()
    inventory = payload["inventory"]
    expected = hashlib.sha256(json.dumps(inventory, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    if expected != payload["inventory_sha256"]:
        raise RuntimeError("preservation inventory digest mismatch")
    for item in inventory:
        path = ROOT / item["path"]
        if not path.is_file() or path.stat().st_size != item["bytes"] or sha(path) != item["sha256"]:
            raise RuntimeError(f"preservation drift: {item['path']}")
    final = json.loads((ROOT / "results/constructed_copy_circuit_v1_1_20260809/final/result.json").read_text())
    if final["status"] != payload["final_status"] or final["training_performed"] or final["representation_methods_evaluated"]:
        raise RuntimeError("v1.1 final drift")
    print(json.dumps({"status": "PASS", "inventory": len(inventory), "manifest_sha256": sha(MANIFEST)}, sort_keys=True))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=("create", "verify"))
    args = parser.parse_args()
    {"create": create, "verify": verify}[args.command]()


if __name__ == "__main__":
    main()
