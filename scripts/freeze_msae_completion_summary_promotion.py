#!/usr/bin/env python3
"""Freeze the exact reviewed noncanonical candidate before canonical publication."""
from __future__ import annotations

from msa_completion_summary_recovery_common import (
    CLAIM_REVIEW,
    PROMOTION_FREEZE,
    RESULT_REVIEW,
    _candidate_review,
    canonical_json_bytes,
    canonical_root,
    candidate_root,
    content_inventory,
    sha256_bytes,
    utc_now,
    validate_candidate,
    verify_execution_owner_mount,
    verify_initial_freeze,
    verify_promotion_freeze,
    write_once_json,
)


def main() -> None:
    verify_execution_owner_mount()
    if PROMOTION_FREEZE.exists():
        raise RuntimeError("promotion freeze is create-once")
    if canonical_root().exists():
        raise RuntimeError("canonical result exists before promotion freeze")
    initial = verify_initial_freeze()
    candidate = validate_candidate(require_success=True)
    result_review = _candidate_review(
        RESULT_REVIEW, "atlas_completion_summary_recovery_result_review_v1", candidate)
    claim_review = _candidate_review(
        CLAIM_REVIEW, "atlas_completion_summary_recovery_claim_review_v1", candidate)
    material = {
        "candidate_content_sha256": candidate["content_sha256"],
        "candidate_files": content_inventory(candidate_root()),
        "candidate_terminal_sha256": candidate["terminal_sha256"],
        "claim_review_sha256": claim_review["transcript_sha256"],
        "initial_recovery_bundle_sha256": initial["bundle_sha256"],
        "result_review_sha256": result_review["transcript_sha256"],
    }
    record = {
        "schema_version": "atlas_completion_summary_recovery_promotion_freeze_v1",
        "bundle_material": material,
        "bundle_sha256": sha256_bytes(canonical_json_bytes(material, newline=False)),
        "diagnostic_continuation_only": True,
        "decision_promotion_allowed": False,
        "created_utc": utc_now(),
    }
    write_once_json(PROMOTION_FREEZE, record)
    verified = verify_promotion_freeze()
    print({"frozen": True, "bundle_sha256": verified["bundle_sha256"]})


if __name__ == "__main__":
    main()
