#!/usr/bin/env python3
"""Create or verify the immutable preservation manifest for the two terminal R2 studies."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "reports/provenance/trained_control_r2_outcomes_preservation_v1.json"
PAPER_ATTESTATION = ROOT / "reports/provenance/trained_control_r2_paper_inputs_v1.json"

ROOTS = (
    "configs/trained_copy_sae_capacity_v1_r2",
    "configs/causal_manifold_bridge_v1_r2",
    "data/trained_copy_sae_capacity_v1_prepared",
    "data/causal_manifold_bridge_v1_prepared",
    "results/trained_copy_sae_capacity_v1_r2_20260813",
    "results/causal_manifold_bridge_v1_r2_20260813",
    "reports/provenance/trained_copy_sae_capacity_v1_r2_candidate",
    "reports/provenance/trained_copy_sae_capacity_v1_r2_run_20260813",
    "reports/provenance/causal_manifold_bridge_v1_r2_candidate",
    "reports/provenance/causal_manifold_bridge_v1_r2_run_20260813",
)
FILES = (
    "PLAN_TRAINED_CONTROL_STUDIES_R2_TECHNICAL_RECOVERY.md",
    "scripts/trained_copy_sae_capacity_v1_r2.py",
    "scripts/causal_manifold_bridge_v1_r2.py",
    "scripts/launch_trained_control_next_studies_v1_r2_tmux.sh",
    "tests/test_trained_copy_sae_capacity_v1_r2.py",
    "tests/test_causal_manifold_bridge_v1_r2.py",
    "tests/test_launch_trained_control_next_studies_v1_r2.py",
    "reports/trained_control_next_studies_v1_r2_postresult_summary.json",
    "reports/claim_review/trained_control_next_studies_v1_r2_post_result_claim_review.md",
    "reports/adversarial/trained_copy_sae_capacity_v1_r2_candidate_review.md",
    "reports/adversarial/trained_copy_sae_capacity_v1_r2_frozen_review.md",
    "reports/adversarial/causal_manifold_bridge_v1_r2_candidate_review.md",
    "reports/adversarial/causal_manifold_bridge_v1_r2_frozen_review.md",
    "reports/provenance/trained_copy_sae_capacity_v1_r2_LAUNCH.json",
    "reports/provenance/trained_copy_sae_capacity_v1_r2_REVIEW_BINDING.json",
    "reports/provenance/causal_manifold_bridge_v1_r2_LAUNCH.json",
    "reports/provenance/causal_manifold_bridge_v1_r2_REVIEW_BINDING.json",
)
FORBIDDEN = (
    "results/causal_manifold_bridge_v1_r2_20260813/confirmation",
    "results/causal_manifold_bridge_v1_r2_20260813/final",
)


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def inventory() -> dict[str, str]:
    paths: list[Path] = []
    for rel in ROOTS:
        base = ROOT / rel
        if not base.is_dir():
            raise FileNotFoundError(rel)
        paths.extend(p for p in base.rglob("*") if p.is_file())
    for rel in FILES:
        p = ROOT / rel
        if not p.is_file():
            raise FileNotFoundError(rel)
        paths.append(p)
    return {str(p.relative_to(ROOT)): sha256(p) for p in sorted(set(paths))}


def terminal_checks() -> None:
    sae_terminal = json.loads(
        (ROOT / "reports/provenance/trained_copy_sae_capacity_v1_r2_run_20260813/TERMINAL.json").read_text()
    )
    bridge_terminal = json.loads(
        (ROOT / "reports/provenance/causal_manifold_bridge_v1_r2_run_20260813/TERMINAL.json").read_text()
    )
    if sae_terminal.get("no_retry_authorized") is not True:
        raise RuntimeError("SAE R2 terminal is not no-retry")
    if bridge_terminal.get("no_retry_authorized") is not True:
        raise RuntimeError("bridge R2 terminal is not no-retry")
    final = ROOT / "results/trained_copy_sae_capacity_v1_r2_20260813/final/result.json"
    expected = sae_terminal.get("final_sha256") or sae_terminal.get("result_sha256")
    if expected and sha256(final) != expected:
        raise RuntimeError("SAE terminal/final hash disagreement")
    for rel in FORBIDDEN:
        if (ROOT / rel).exists():
            raise RuntimeError(f"forbidden bridge artifact appeared: {rel}")


def create() -> None:
    if OUT.exists() or PAPER_ATTESTATION.exists():
        raise FileExistsError("preservation artifacts already exist; use --verify")
    terminal_checks()
    items = inventory()
    payload = {
        "schema_version": "trained_control_r2_outcomes_preservation_v1",
        "immutable_roots": list(ROOTS),
        "forbidden_paths": list(FORBIDDEN),
        "items": items,
        "inventory_sha256": hashlib.sha256(
            json.dumps(items, sort_keys=True, separators=(",", ":")).encode()
        ).hexdigest(),
        "no_retry_authorized": True,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    paper = {rel: sha256(ROOT / rel) for rel in ("PAPER.md", "reports/paper_claim_ledger_v1.json")}
    PAPER_ATTESTATION.write_text(
        json.dumps({"schema_version": "trained_control_r2_paper_inputs_v1", "items": paper}, indent=2, sort_keys=True)
        + "\n"
    )


def verify() -> None:
    terminal_checks()
    saved = json.loads(OUT.read_text())
    actual = inventory()
    if saved["items"] != actual:
        missing = sorted(set(saved["items"]) - set(actual))
        added = sorted(set(actual) - set(saved["items"]))
        changed = sorted(k for k in set(saved["items"]) & set(actual) if saved["items"][k] != actual[k])
        raise RuntimeError(f"R2 preservation mismatch missing={missing} added={added} changed={changed}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--create", action="store_true")
    parser.add_argument("--verify", action="store_true")
    args = parser.parse_args()
    if args.create == args.verify:
        parser.error("choose exactly one of --create or --verify")
    create() if args.create else verify()


if __name__ == "__main__":
    main()
