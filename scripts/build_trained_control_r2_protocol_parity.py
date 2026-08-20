#!/usr/bin/env python3
"""Build or verify the fail-closed R1→R2 protocol/source parity certificate."""

from __future__ import annotations

import argparse
import ast
import copy
import difflib
import hashlib
import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "reports/provenance/trained_control_studies_v1_r2_PROTOCOL_PARITY.json"

STUDIES = {
    "sae_capacity": {
        "r1_config": "configs/trained_copy_sae_capacity_v1_r1/run.json",
        "r2_config": "configs/trained_copy_sae_capacity_v1_r2/run.json",
        "r1_source": "scripts/trained_copy_sae_capacity_v1_r1.py",
        "r2_source": "scripts/trained_copy_sae_capacity_v1_r2.py",
        "allowed_changed_definitions": [
            "candidate",
            "create_lock",
            "freeze",
            "run",
            "sae_prediction",
            "validate_recovery_lineage",
            "verify_frozen",
            "verify_protocol_parity",
        ],
    },
    "causal_manifold": {
        "r1_config": "configs/causal_manifold_bridge_v1_r1/run.json",
        "r2_config": "configs/causal_manifold_bridge_v1_r2/run.json",
        "r1_source": "scripts/causal_manifold_bridge_v1_r1.py",
        "r2_source": "scripts/causal_manifold_bridge_v1_r2.py",
        "allowed_changed_definitions": [
            "candidate",
            "create_lock",
            "donor_basis_qa",
            "fit_registry",
            "freeze",
            "validate_recovery_lineage",
            "verify_frozen",
            "verify_protocol_parity",
            "write_donor_basis",
        ],
    },
}

EXPECTED_SOURCE_DIFF_SHA256 = {
    "sae_capacity": "be738d0ccee0691496f7d6ed4d1bedd5a4887b1eee7b11b88badf04f93a12266",
    "causal_manifold": "ed2447556322520190129474556eb621411c4dc9d015a1f01f0ac58a725dcce6",
}

ALLOWED_CONFIG_POINTERS = [
    "/namespace",
    "/runtime/candidate_manifest",
    "/runtime/candidate_review",
    "/runtime/freeze",
    "/runtime/frozen_review",
    "/runtime/generator_lock",
    "/runtime/launch_manifest",
    "/runtime/launcher_log",
    "/runtime/output_root",
    "/runtime/provenance_root",
    "/runtime/review_binding",
    "/runtime/tmux_session",
]
R2_ONLY_CONFIG_POINTERS = ["/recovery_lineage/r1_freezes"]

BOUND_PATHS = [
    "PLAN_TRAINED_CONTROL_STUDIES_R2_TECHNICAL_RECOVERY.md",
    "scripts/preserve_trained_control_r1_failures.py",
    "scripts/build_trained_control_r2_protocol_parity.py",
    "reports/provenance/trained_control_next_studies_v1_r1_failures_preservation.json",
    "reports/provenance/trained_control_next_studies_v1_r1_exposure_attestation.json",
    "scripts/trained_copy_sae_capacity_v1_r1.py",
    "scripts/trained_copy_sae_capacity_v1_r2.py",
    "scripts/causal_manifold_bridge_v1_r1.py",
    "scripts/causal_manifold_bridge_v1_r2.py",
    "configs/trained_copy_sae_capacity_v1_r1/run.json",
    "configs/trained_copy_sae_capacity_v1_r2/run.json",
    "configs/causal_manifold_bridge_v1_r1/run.json",
    "configs/causal_manifold_bridge_v1_r2/run.json",
    "tests/test_trained_copy_sae_capacity_v1_r2.py",
    "tests/test_causal_manifold_bridge_v1_r2.py",
    "tests/test_launch_trained_control_next_studies_v1_r2.py",
    "tests/test_trained_control_r1_failure_preservation.py",
    "tests/test_trained_control_r2_protocol_parity.py",
    "scripts/launch_trained_control_next_studies_v1_r2_tmux.sh",
]


def canonical(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def remove_pointer(value: dict[str, Any], pointer: str) -> None:
    parts = [p.replace("~1", "/").replace("~0", "~") for p in pointer.split("/")[1:]]
    current: Any = value
    for part in parts[:-1]:
        if part not in current:
            raise RuntimeError(f"missing parity pointer parent: {pointer}")
        current = current[part]
    if parts[-1] not in current:
        raise RuntimeError(f"missing parity pointer: {pointer}")
    del current[parts[-1]]


def config_parity(r1_path: Path, r2_path: Path) -> dict[str, Any]:
    r1 = json.loads(r1_path.read_text())
    r2 = json.loads(r2_path.read_text())
    allowed_values = {}
    for pointer in ALLOWED_CONFIG_POINTERS:
        parts = pointer.split("/")[1:]
        a: Any = r1
        b: Any = r2
        for part in parts:
            a = a[part]
            b = b[part]
        allowed_values[pointer] = {"r1": a, "r2": b}
        remove_pointer(r1, pointer)
        remove_pointer(r2, pointer)
    for pointer in R2_ONLY_CONFIG_POINTERS:
        parts = pointer.split("/")[1:]
        b: Any = r2
        for part in parts:
            b = b[part]
        allowed_values[pointer] = {"r1": "ABSENT", "r2": b}
        remove_pointer(r2, pointer)
    if r1 != r2:
        raise RuntimeError("unauthorized scientific config difference")
    protected = {
        "prepared_root": r2["runtime"]["prepared_root"],
        "hard_timeout_hours": r2["hard_timeout_hours"],
        "original_freezes": r2["recovery_lineage"]["original_freezes"],
    }
    return {
        "pass": True,
        "allowed_pointer_values": allowed_values,
        "protected_values": protected,
        "normalized_sha256": hashlib.sha256(canonical(r2)).hexdigest(),
    }


def definitions(path: Path) -> dict[str, str]:
    tree = ast.parse(path.read_text(), filename=str(path))
    result = {}
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            result[node.name] = ast.dump(node, annotate_fields=True, include_attributes=False)
    return result


def source_parity(r1_path: Path, r2_path: Path, allowed: list[str], expected_diff_sha256: str, from_label: str, to_label: str) -> dict[str, Any]:
    a, b = definitions(r1_path), definitions(r2_path)
    allowed_set = set(allowed)
    all_names = set(a) | set(b)
    changed = sorted(name for name in all_names if a.get(name) != b.get(name))
    unauthorized = sorted(set(changed) - allowed_set)
    missing_expected = sorted(allowed_set - set(changed))
    if unauthorized:
        raise RuntimeError(f"unauthorized executable definition changes: {unauthorized}")
    if missing_expected:
        raise RuntimeError(f"declared changed definitions did not change: {missing_expected}")
    diff = "".join(
        difflib.unified_diff(
            r1_path.read_text().splitlines(True),
            r2_path.read_text().splitlines(True),
            fromfile=from_label,
            tofile=to_label,
        )
    )
    diff_sha256 = hashlib.sha256(diff.encode()).hexdigest()
    if diff_sha256 != expected_diff_sha256:
        raise RuntimeError(f"source diff is not the exact authorized recovery patch: {diff_sha256} != {expected_diff_sha256}")
    return {
        "pass": True,
        "changed_definitions": changed,
        "allowed_changed_definitions": sorted(allowed_set),
        "unchanged_definition_count": len(all_names - set(changed)),
        "unified_diff_sha256": diff_sha256,
        "expected_unified_diff_sha256": expected_diff_sha256,
        "unified_diff_lines": len(diff.splitlines()),
        "governance_changes": [
            "R2 module/config/test/launcher/plan/parity bindings",
            "R1 failure preservation and R1-freeze validation",
            "candidate/lock/freeze parity binding",
        ],
    }


def build_record() -> dict[str, Any]:
    studies = {}
    for name, spec in STUDIES.items():
        studies[name] = {
            "config": config_parity(ROOT / spec["r1_config"], ROOT / spec["r2_config"]),
            "source": source_parity(
                ROOT / spec["r1_source"], ROOT / spec["r2_source"], spec["allowed_changed_definitions"],
                EXPECTED_SOURCE_DIFF_SHA256[name], spec["r1_source"], spec["r2_source"]
            ),
        }
    bound = []
    for rel in BOUND_PATHS:
        p = ROOT / rel
        if not p.is_file():
            raise RuntimeError(f"missing parity-bound artifact: {rel}")
        bound.append({"path": rel, "bytes": p.stat().st_size, "sha256": sha(p)})
    return {
        "schema_version": "trained_control_studies_v1_r2_protocol_parity_v1",
        "status": "PASS",
        "allowed_config_pointers": ALLOWED_CONFIG_POINTERS,
        "r2_only_config_pointers": R2_ONLY_CONFIG_POINTERS,
        "studies": studies,
        "bound_artifacts": bound,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--verify", action="store_true")
    args = parser.parse_args()
    record = build_record()
    if args.verify:
        if json.loads(OUT.read_text()) != record:
            raise RuntimeError("protocol parity artifact drift")
    else:
        if OUT.exists():
            raise FileExistsError(OUT)
        OUT.parent.mkdir(parents=True, exist_ok=True)
        OUT.write_bytes(json.dumps(record, indent=2, sort_keys=True).encode() + b"\n")
    print(json.dumps({"status": "PASS", "studies": sorted(studies for studies in record["studies"]), "sha256": sha(OUT) if OUT.exists() else None}, sort_keys=True))


if __name__ == "__main__":
    main()
