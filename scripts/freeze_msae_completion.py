#!/usr/bin/env python3
"""Create the prescore additive freeze for atlas completion-v1."""

from __future__ import annotations

import argparse
from pathlib import Path

from atlas_freeze import verify_freeze
from msa_completion_common import (COMPLETION_FREEZE, ROOT, atomic_write_json,
                                   canonical_json_bytes, read_json, sha256_bytes,
                                   sha256_file, terminal_state, utc_now,
                                   verify_attestation_current)


IMPLEMENTATION_REVIEW = "reports/adversarial/atlas_completion_implementation_review_20260801.md"
IMPLEMENTATION_REVIEW_RECORD = "reports/adversarial/atlas_completion_implementation_review_20260801.json"


CANDIDATE_FILES = [
    "configs/atlas_completion/analysis.json",
    "docs/rfc-atlas-v1-completion.md",
    "prereg/atlas_completion_amendment_v1.md",
    "reports/adversarial/atlas_completion_plan_review_20260801.md",
    "reports/architecture_decision.json",
    "reports/architecture_decision.md",
    "requirements-atlas.lock.txt",
    "scripts/atlas_freeze.py",
    "scripts/atlas_metrics.py",
    "scripts/build_msae_completion_rows.py",
    "scripts/calibrate_msae_completion.py",
    "scripts/freeze_msae_completion.py",
    "scripts/launch_msae_completion_tmux.sh",
    "scripts/merge_msae_refit.py",
    "scripts/msa_completion_common.py",
    "scripts/msa_completion_cpu_runner.sh",
    "scripts/msa_completion_gpu_runner.sh",
    "scripts/msa_completion_pilot.py",
    "scripts/render_msae_completion_decision.py",
    "scripts/run_k2_functional_audit.py",
    "scripts/run_msae_refit_worker.py",
    "scripts/run_msae_specificity.py",
    "scripts/run_msae_stability.py",
    "scripts/train_msae_k2.py",
    "scripts/verify_msae_completion.py",
    "tests/test_atlas_data.py",
    "tests/test_atlas_metrics.py",
    "tests/test_msae_completion.py",
]


def candidate_files() -> list[Path]:
    files = [ROOT / item for item in CANDIDATE_FILES]
    files.extend(sorted((ROOT / "data/atlas_completion_v1").glob("*")))
    files.extend([
        ROOT / "pilot_runs/20260801_atlas_completion_v1/pilot_v10/pilot.json",
        ROOT / "pilot_runs/20260801_atlas_completion_v1/pilot_v10/MEASUREMENT_COMPLETE.json",
    ])
    missing = [str(path.relative_to(ROOT)) for path in files if not path.is_file()]
    if missing:
        raise FileNotFoundError(f"missing freeze inputs: {missing}")
    return files


def file_entries(files: list[Path]) -> list[dict[str, str]]:
    return sorted(
        ({"path": str(path.relative_to(ROOT)), "sha256": sha256_file(path)} for path in files),
        key=lambda row: row["path"],
    )


def reviewed_candidate() -> tuple[list[dict[str, str]], str]:
    entries = file_entries(candidate_files())
    return entries, sha256_bytes(canonical_json_bytes(entries))


def require_ship_review(candidate_sha256: str) -> list[Path]:
    transcript = ROOT / IMPLEMENTATION_REVIEW
    record_path = ROOT / IMPLEMENTATION_REVIEW_RECORD
    if not transcript.is_file() or not record_path.is_file():
        raise FileNotFoundError("missing final implementation adversarial review transcript/record")
    record = read_json(record_path)
    expected = {
        "schema_version": "atlas_completion_implementation_review_v1",
        "verdict": "SHIP",
        "reviewed_candidate_sha256": candidate_sha256,
        "transcript_sha256": sha256_file(transcript),
    }
    if any(record.get(key) != value for key, value in expected.items()):
        raise RuntimeError("implementation review does not approve this exact candidate digest")
    first = next((line.strip() for line in transcript.read_text().splitlines() if line.strip()), "")
    if first != "VERDICT: SHIP":
        raise RuntimeError("implementation review transcript is not a SHIP verdict")
    return [transcript, record_path]


def verify_pilot_attestation_for_freeze(
        attestation: dict, candidate_entries: list[dict[str, str]]) -> None:
    """Reject post-pilot input drift and paths outside reviewed/frozen inventories."""

    inventory = read_json(ROOT / "data/atlas_completion_v1/upstream_inventory.json")
    allowed = {
        str((ROOT / entry["path"]).resolve()) for entry in candidate_entries
    }
    for name in inventory.get("files", {}):
        path = Path(name)
        allowed.add(str((path if path.is_absolute() else ROOT / path).resolve()))
    token_manifest = read_json(
        ROOT / "data/atlas_completion_v1/token_control_manifest.json")
    for entry in token_manifest["tokenizer"]["files"]:
        allowed.add(str(Path(entry["snapshot_path"]).resolve()))
        allowed.add(str(Path(entry["target_path"]).resolve()))
    unexpected = sorted(path for path in attestation if path not in allowed)
    if unexpected:
        raise RuntimeError(f"pilot attested paths outside reviewed inventories: {unexpected[:10]}")
    verify_attestation_current(attestation)


def assert_prescore_clean(config: dict) -> None:
    run_root = ROOT / config["run_root"]
    forbidden = [run_root / name for name in [
        "baseline", "raw_refit", "k2_refit", "stability", "specificity",
        "verification", "render", "NOT_LAUNCHED_UPSTREAM_STOP.json", "FROZEN_EQUIVOCAL_STOP.json",
    ]]
    forbidden.extend([
        ROOT / "results/atlas/completion_v1",
        ROOT / "reports/planning_decision_v2.json",
        ROOT / "reports/planning_decision_v2.md",
        ROOT / "reports/atlas_completion_results.md",
    ])
    present = [str(path.relative_to(ROOT)) for path in forbidden if path.exists()]
    if present:
        raise RuntimeError(f"completion score output exists before freeze: {present}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--replace-before-score", action="store_true")
    args = parser.parse_args()
    config = read_json(ROOT / "configs/atlas_completion/analysis.json")
    assert_prescore_clean(config)
    parent = verify_freeze()
    if parent["bundle_sha256"] != config["parent_bundle_sha256"]:
        raise RuntimeError("configured parent digest mismatch")
    pilot_path = ROOT / "pilot_runs/20260801_atlas_completion_v1/pilot_v10/pilot.json"
    pilot_terminal_path = ROOT / "pilot_runs/20260801_atlas_completion_v1/pilot_v10/MEASUREMENT_COMPLETE.json"
    pilot = read_json(pilot_path)
    if terminal_state(pilot_path.parent) != "complete":
        raise RuntimeError("pilot is not measurement-complete; resource/numerical stop blocks freeze")
    pilot_terminal = read_json(pilot_terminal_path)
    if not pilot.get("numerical_pass") or not pilot.get("budget_pass"):
        raise RuntimeError("approved pilot did not pass numerical/resource gates")
    expected_terminal = {
        "schema_version": "atlas_completion_pilot_complete_v1",
        "numerical_pass": True,
        "budget_pass": True,
        "result_sha256": sha256_file(pilot_path),
        "exercised_bundle_sha256": pilot.get("exercised_bundle_sha256"),
        "terminal_state": "measurement_complete",
        "score_access_allowed": True,
        "failed_stage_budgets": [],
        "projected": pilot.get("projected"),
        "input_attestation": pilot.get("input_attestation"),
        "resolved_config": pilot.get("resolved_config"),
        "resolved_arguments": pilot.get("resolved_arguments"),
        "seed_provenance": pilot.get("seed_provenance"),
        "device": pilot.get("device"),
        "started_utc": pilot.get("started_utc"),
        "environment": pilot.get("environment"),
        "resource_accounting": pilot_terminal.get("resource_accounting"),
        "parent_bundle_reverified_after_stage_sha256": parent["bundle_sha256"],
        "evidence_class": config["evidence_class"],
    }
    if any(pilot_terminal.get(key) != value
           for key, value in expected_terminal.items()):
        raise RuntimeError("pilot terminal does not exactly bind the approved passing result")
    if set(pilot_terminal) != {*expected_terminal, "ended_utc"}:
        raise RuntimeError("pilot terminal contains an unreviewed field set")
    if (pilot.get("confirmation_roles_read") != []
            or set(pilot.get("roles_read", [])) != {"discovery", "calibration"}):
        raise RuntimeError("pilot role isolation failed")
    for entry in pilot.get("exercised_files", []):
        if sha256_file(ROOT / entry["path"]) != entry["sha256"]:
            raise RuntimeError(f"pilot exercised-code binding mismatch: {entry['path']}")
    candidate_entries, candidate_sha = reviewed_candidate()
    verify_pilot_attestation_for_freeze(
        pilot_terminal.get("input_attestation", {}), candidate_entries)
    review_files = require_ship_review(candidate_sha)
    entries = sorted([*candidate_entries, *file_entries(review_files)], key=lambda row: row["path"])
    record = {
        "schema_version": "atlas_completion_freeze_v1",
        "evidence_class": config["evidence_class"],
        "created_utc": utc_now(),
        "bundle_files": entries,
        "bundle_sha256": sha256_bytes(canonical_json_bytes(entries)),
        "reviewed_candidate_sha256": candidate_sha,
        "implementation_review_sha256": sha256_file(ROOT / IMPLEMENTATION_REVIEW),
        "implementation_review_record_sha256": sha256_file(ROOT / IMPLEMENTATION_REVIEW_RECORD),
        "parent_bundle_sha256": parent["bundle_sha256"],
        "upstream_inventory_sha256": sha256_file(
            ROOT / "data/atlas_completion_v1/upstream_inventory.json"),
        "config_parent_bundle_sha256": config["parent_bundle_sha256"],
        "pilot_result_sha256": sha256_file(pilot_path),
        "pilot_terminal_sha256": sha256_file(pilot_terminal_path),
        "pilot_result_hash": sha256_file(pilot_path),
        "pilot_numerical_pass": True,
        "pilot_budget_pass": True,
        "pilot_exercised_bundle_sha256": pilot["exercised_bundle_sha256"],
        "score_bearing_outputs_absent_at_freeze": True,
    }
    atomic_write_json(COMPLETION_FREEZE, record, create_once=not args.replace_before_score)
    print(record["bundle_sha256"])


if __name__ == "__main__":
    main()
