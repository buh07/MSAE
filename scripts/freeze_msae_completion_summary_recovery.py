#!/usr/bin/env python3
"""Create the initial, implementation-reviewed summary-recovery freeze."""
from __future__ import annotations

import argparse

from msa_completion_summary_recovery_common import (
    IMPLEMENTATION_REVIEW,
    INITIAL_FREEZE,
    ROOT,
    _review_binding,
    candidate_root,
    canonical_json_bytes,
    canonical_root,
    implementation_inventory,
    inventory_digest,
    sha256_bytes,
    utc_now,
    verify_incident_inputs,
    verify_initial_freeze,
    write_once_json,
)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--candidate-only", action="store_true")
    args = parser.parse_args()
    incident = verify_incident_inputs()
    inventory = implementation_inventory()
    digest = inventory_digest(inventory)
    if args.candidate_only:
        print({"candidate_sha256": digest, "candidate_files": inventory})
        return
    if INITIAL_FREEZE.exists():
        raise RuntimeError("initial recovery freeze is create-once")
    if candidate_root().exists() or canonical_root().exists():
        raise RuntimeError("recovery result root exists before initial freeze")
    review = _review_binding(
        IMPLEMENTATION_REVIEW,
        schema="atlas_completion_summary_recovery_implementation_review_v1",
        candidate_sha=digest,
    )
    material = {
        "candidate_sha256": digest,
        "implementation_review_sha256": review["transcript_sha256"],
        "original_continuation_bundle_sha256": incident["config"]["original_continuation_bundle_sha256"],
        "plan_review_sha256": incident["config"]["plan_review_sha256"],
    }
    record = {
        "schema_version": "atlas_completion_summary_recovery_freeze_v1",
        "candidate_files": inventory,
        "candidate_sha256": digest,
        "bundle_material": material,
        "bundle_sha256": sha256_bytes(canonical_json_bytes(material, newline=False)),
        "original_continuation_bundle_sha256": incident["config"]["original_continuation_bundle_sha256"],
        "diagnostic_continuation_only": True,
        "decision_promotion_allowed": False,
        "created_utc": utc_now(),
    }
    write_once_json(INITIAL_FREEZE, record)
    verified = verify_initial_freeze()
    print({"frozen": True, "bundle_sha256": verified["bundle_sha256"], "candidate_sha256": digest})


if __name__ == "__main__":
    main()
