#!/usr/bin/env python3
"""Freeze the reviewed diagnostic-continuation implementation before scoring."""
from __future__ import annotations
import argparse
import json
from pathlib import Path

from msa_completion_common import ROOT, atomic_write_json, read_json, sha256_file, utc_now
from msa_completion_continuation_common import (
    BASELINE_HASHES, BASELINE_SOURCE, BASE_CONFIG, BASE_DIGEST, BASE_NOT_LAUNCHED,
    BASE_SELECTOR, BASE_STOP, CONFIG, FREEZE, IMPLEMENTATION_REVIEW, INVENTORY,
    PARENT_DIGEST, RESULT_REVIEW, RESULT_ROOT, RUN_ROOT, compute_bundle,
    verify_base_completion_freeze, verify_continuation_freeze, verify_fixed_source_hashes,
    verify_source_inventory,
)

PLAN_REVIEW = ROOT / "reports/adversarial/atlas_completion_continuation_plan_review_20260801.json"
PLAN = ROOT / "docs/rfc-atlas-v1-diagnostic-continuation.md"
PLAN_TRANSCRIPT = ROOT / "reports/adversarial/atlas_completion_continuation_plan_review_20260801.md"
IMPLEMENTATION_TRANSCRIPT = ROOT / "reports/adversarial/atlas_completion_continuation_implementation_review_20260801.md"


def validate_plan_review(review: dict[str, object]) -> None:
    expected_keys = {
        "origin", "plan_path", "plan_sha256", "schema_version", "transcript_path",
        "transcript_sha256", "verdict",
    }
    if (set(review) != expected_keys
            or review.get("schema_version") != "atlas_completion_continuation_plan_review_v1"
            or review.get("origin") != "forked"
            or review.get("verdict") != "SHIP"
            or review.get("plan_path") != str(PLAN.relative_to(ROOT))
            or review.get("plan_sha256") != sha256_file(PLAN)
            or review.get("transcript_path") != str(PLAN_TRANSCRIPT.relative_to(ROOT))
            or review.get("transcript_sha256") != sha256_file(PLAN_TRANSCRIPT)
            or not PLAN_TRANSCRIPT.read_text().startswith("VERDICT: SHIP\n")):
        raise RuntimeError("plan review does not bind exact forked SHIP transcript")


def candidate_paths() -> list[Path]:
    paths = [
        CONFIG, INVENTORY,
        ROOT / "docs/rfc-atlas-v1-diagnostic-continuation.md",
        ROOT / "prereg/atlas_completion_diagnostic_continuation_v1.md",
        ROOT / "reports/adversarial/atlas_completion_result_review_20260801.md",
        ROOT / "reports/adversarial/atlas_completion_continuation_plan_review_20260801.md",
        PLAN_REVIEW,
        BASE_CONFIG, BASE_STOP, BASE_SELECTOR, BASE_NOT_LAUNCHED,
        ROOT / "configs/atlas_completion/freeze_record.json",
        ROOT / "scripts/msa_completion_common.py",
        ROOT / "scripts/freeze_msae_completion_continuation.py",
        ROOT / "scripts/run_msae_refit_worker.py",
        ROOT / "scripts/run_msae_stability.py",
        ROOT / "scripts/run_msae_specificity.py",
        ROOT / "scripts/verify_msae_completion.py",
        ROOT / "scripts/snapshot_msae_completion_source_root.py",
        ROOT / "scripts/msa_completion_continuation_common.py",
        ROOT / "scripts/bind_msae_completion_continuation_baseline.py",
        ROOT / "scripts/run_msae_completion_continuation.py",
        ROOT / "scripts/msa_completion_continuation_gpu_runner.sh",
        ROOT / "scripts/msa_completion_continuation_cpu_runner.sh",
        ROOT / "scripts/collect_msae_completion_continuation.py",
        ROOT / "scripts/launch_msae_completion_continuation_tmux.sh",
        ROOT / "scripts/summarize_msae_completion_continuation.py",
        ROOT / "tests/test_msae_completion_continuation.py",
    ]
    paths.extend(BASELINE_SOURCE / name for name in sorted(BASELINE_HASHES))
    return paths


def reviewed_candidate() -> dict[str, object]:
    return compute_bundle(candidate_paths())


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    if RUN_ROOT.exists() or RESULT_ROOT.exists():
        raise RuntimeError("continuation scoring/result output exists before freeze")
    verify_fixed_source_hashes()
    inventory = verify_source_inventory()
    base = verify_base_completion_freeze()
    if base.get("bundle_sha256") != BASE_DIGEST:
        raise RuntimeError("base completion freeze digest mismatch")
    candidate = reviewed_candidate()
    if not IMPLEMENTATION_REVIEW.is_file() or not IMPLEMENTATION_TRANSCRIPT.is_file():
        raise RuntimeError(f"exact implementation SHIP review absent; candidate={candidate['bundle_sha256']}")
    review = read_json(IMPLEMENTATION_REVIEW)
    if (review.get("schema_version") != "atlas_completion_continuation_implementation_review_v1"
            or review.get("verdict") != "SHIP"
            or review.get("candidate_sha256") != candidate["bundle_sha256"]
            or review.get("transcript_path") != str(IMPLEMENTATION_TRANSCRIPT.relative_to(ROOT))
            or review.get("transcript_sha256") != sha256_file(IMPLEMENTATION_TRANSCRIPT)):
        raise RuntimeError("implementation review does not bind exact SHIP candidate")
    if not IMPLEMENTATION_TRANSCRIPT.read_text().startswith("VERDICT: SHIP\n"):
        raise RuntimeError("implementation review transcript is not SHIP")
    validate_plan_review(read_json(PLAN_REVIEW))
    bundle = compute_bundle([*candidate_paths(), IMPLEMENTATION_REVIEW, IMPLEMENTATION_TRANSCRIPT])
    record = {
        "schema_version": "atlas_completion_diagnostic_continuation_freeze_v1",
        "created_utc": utc_now(),
        "evidence_class": "postscore_amended_architecture_evidence",
        "diagnostic_continuation_only": True,
        "decision_promotion_allowed": False,
        "parent_bundle_sha256": PARENT_DIGEST,
        "base_completion_bundle_sha256": BASE_DIGEST,
        "base_freeze_record_sha256": sha256_file(ROOT / "configs/atlas_completion/freeze_record.json"),
        "config_sha256": sha256_file(CONFIG),
        "source_inventory_manifest_sha256": sha256_file(INVENTORY),
        "source_inventory_sha256": inventory["inventory_sha256"],
        "reviewed_candidate_sha256": candidate["bundle_sha256"],
        "reviewed_candidate_files": candidate["bundle_files"],
        "implementation_review_sha256": sha256_file(IMPLEMENTATION_TRANSCRIPT),
        "bundle_files": bundle["bundle_files"],
        "bundle_sha256": bundle["bundle_sha256"],
        "prescore_clean": True,
    }
    if args.dry_run:
        print(json.dumps({"candidate": candidate, "freeze": record}, indent=2))
        return
    atomic_write_json(FREEZE, record)
    verified = verify_continuation_freeze()
    print(json.dumps({"frozen": True, "bundle_sha256": verified["bundle_sha256"],
                      "candidate_sha256": candidate["bundle_sha256"]}, indent=2))


if __name__ == "__main__":
    main()
