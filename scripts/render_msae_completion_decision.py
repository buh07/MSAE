#!/usr/bin/env python3
"""Render the immutable amended planning endpoint without editing atlas-v1."""

from __future__ import annotations

import argparse
import json
import time
from pathlib import Path
from typing import Any

from msa_completion_common import (EVIDENCE_CLASS, ROOT, atomic_write_json,
                                   atomic_write_bytes,
                                   attest_completion_freeze_record,
                                   default_firewall,
                                   process_resource_accounting,
                                   read_json, require_frozen_completion_config,
                                   require_frozen_upstream_file,
                                   verify_parent_freeze_attested,
                                   runtime_environment, seed_provenance,
                                   sha256_file, terminal_state, utc_now,
                                   verify_attestation_current,
                                   verify_completion_freeze,
                                   write_failure_terminal, write_terminal)


_FAILURE_ATTESTATION: dict[str, Any] = {}


def decide(predicates: dict[str, bool]) -> str:
    """Exhaustive highest-precedence amended decision table."""

    if predicates.get("any_primary_invalidity", False):
        return "equivocal_no_decision"
    if predicates.get("simple_equivalence", False):
        return "existing_simple"
    if predicates.get("existing_checkpoint_all_gates", False):
        return "existing_checkpoint"
    if predicates.get("learned_model_all_gates", False):
        return "learned_model_warranted"
    if predicates.get("supported_negative_all_gates", False):
        return "supported_negative_atlas"
    return "equivocal_no_decision"


def decision_predicates(results: dict[str, Any]) -> dict[str, bool]:
    """Emit every registered branch predicate even when equivocal wins first."""

    g1 = results["raw"]["G1a_postscore_amended"]
    g2 = results["G2a_postscore_amended"]
    negative = g1["supported_negative_diagnostic"]
    g2_randomization = g2.get("g2_randomization", {})
    g2_superiority_inference_invalid = bool(
        g2_randomization and not all(
            row.get("valid") is True and row.get("p") is not None
            for row in g2_randomization.values()))
    learned_boundary_proximity = bool(g2.get("learned_boundary_failures", []))
    conflicting_primary_axes = bool(g1.get("source_reversal_failures", []))
    return {
        "any_primary_invalidity": bool(results["preflight"]["joint_decision_forced_equivocal"]
                                        or not g1["parent_gate_evaluation"]["inferentially_valid"]
                                        or g2["simple_evidence_invalid"]
                                        or results["baseline"]["selection_failed"]
                                        or g2_superiority_inference_invalid
                                        or learned_boundary_proximity
                                        or conflicting_primary_axes),
        "g2_superiority_inference_invalid": g2_superiority_inference_invalid,
        "learned_boundary_proximity": learned_boundary_proximity,
        "conflicting_primary_axes": conflicting_primary_axes,
        "simple_equivalence": bool(g2["simple_branch_available"]),
        "existing_checkpoint_all_gates": bool(g2["existing_checkpoint_branch_evaluation"]["passes"]),
        "learned_model_all_gates": bool(g2["learned_model_branch_evaluation"]["passes"]),
        "supported_negative_all_gates": bool(negative["supported_negative_all_gates"]),
    }


def main() -> None:
    global _FAILURE_ATTESTATION
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, default=ROOT / "configs/atlas_completion/analysis.json")
    parser.add_argument("--results", type=Path, default=ROOT / "results/atlas/completion_v1/completion_results.json")
    parser.add_argument("--json-output", type=Path, default=ROOT / "reports/planning_decision_v2.json")
    parser.add_argument("--md-output", type=Path, default=ROOT / "reports/planning_decision_v2.md")
    parser.add_argument("--results-report", type=Path, default=ROOT / "reports/atlas_completion_results.md")
    args = parser.parse_args()
    started = time.monotonic()
    started_utc = utc_now()
    completion_freeze = require_frozen_completion_config(args.config)
    config = read_json(args.config)
    expected_paths = {
        "results": ROOT / "results/atlas/completion_v1/completion_results.json",
        "json_output": ROOT / "reports/planning_decision_v2.json",
        "md_output": ROOT / "reports/planning_decision_v2.md",
        "results_report": ROOT / "reports/atlas_completion_results.md",
    }
    for name, expected in expected_paths.items():
        if getattr(args, name).resolve() != expected.resolve():
            raise PermissionError(f"{name} must equal the frozen canonical path")
    source_root, run_root = ROOT / config["source_run_root"], ROOT / config["run_root"]
    render_stage = run_root / "render"
    render_stage.mkdir(parents=True, exist_ok=True)
    if terminal_state(render_stage) is not None or any(render_stage.iterdir()):
        raise RuntimeError("render stage is create-once/terminal")
    firewall = default_firewall(source_root, run_root)
    _FAILURE_ATTESTATION = firewall.attestation
    attest_completion_freeze_record(firewall, completion_freeze)
    firewall.register_root(ROOT / "results/atlas/completion_v1")
    firewall.register_root(ROOT / "reports")
    config_path = firewall.attest(args.config)
    verify_parent_freeze_attested(firewall)
    results_path = firewall.attest(args.results)
    results = read_json(results_path)
    result_stage = results_path.parent
    if terminal_state(result_stage) != "complete":
        raise RuntimeError("completion results stage is not measurement-complete")
    result_marker = read_json(firewall.attest(result_stage / "MEASUREMENT_COMPLETE.json"))
    if result_marker.get("result_sha256") != sha256_file(results_path):
        raise RuntimeError("completion result terminal hash mismatch")
    if results.get("completion_bundle_sha256") != completion_freeze["bundle_sha256"]:
        raise RuntimeError("completion results are not bound to the verified extension")
    verification_stage = run_root / "verification"
    if terminal_state(verification_stage) != "complete":
        raise RuntimeError("strict completion verification is not measurement-complete")
    verification_marker = read_json(firewall.attest(
        verification_stage / "MEASUREMENT_COMPLETE.json"))
    verification_result = firewall.attest(
        verification_stage / "verification.json")
    verification_payload = read_json(verification_result)
    if (verification_marker.get("result_sha256") != sha256_file(verification_result)
            or verification_marker.get("completion_results_sha256")
               != sha256_file(results_path)
            or verification_marker.get("config_sha256") != sha256_file(config_path)
            or verification_marker.get("completion_bundle_sha256")
               != completion_freeze["bundle_sha256"]
            or verification_marker.get("leaf_recomputation_pass") is not True
            or verification_marker.get("recursive_finite_pass") is not True
            or verification_payload.get("completion_results_sha256")
               != sha256_file(results_path)
            or verification_payload.get("leaf_recomputation_pass") is not True
            or verification_payload.get("recursive_finite_pass") is not True):
        raise RuntimeError("strict completion verification binding mismatch")
    original_json = firewall.attest(ROOT / "reports/architecture_decision.json")
    original_md = firewall.attest(ROOT / "reports/architecture_decision.md")
    require_frozen_upstream_file(original_json, firewall)
    require_frozen_upstream_file(original_md, firewall)
    original = read_json(original_json)
    g1 = results["raw"]["G1a_postscore_amended"]
    g2 = results["G2a_postscore_amended"]
    predicates = decision_predicates(results)
    outcome = decide(predicates)
    if outcome != results["decision"]["planning_decision_v2"]:
        raise RuntimeError("renderer disagrees with merged decision")
    payload: dict[str, Any] = {
        "schema_version": "atlas_completion_planning_decision_v2",
        "evidence_class": EVIDENCE_CLASS,
        "completion_bundle_sha256": completion_freeze["bundle_sha256"],
        "planning_decision_v2": outcome,
        "training_warranted": outcome == "learned_model_warranted",
        "predicates": predicates,
        "G1a_postscore_amended": g1,
        "G2a_postscore_amended": g2,
        "reasons": results["decision"]["reasons"],
        "original_decision": original,
        "original_decision_sha256": sha256_file(original_json),
        "original_decision_md_sha256": sha256_file(original_md),
        "completion_results_sha256": sha256_file(results_path),
        "completion_verification_sha256": sha256_file(verification_result),
        "config_sha256": sha256_file(config_path),
        "resolved_config": config,
        "resolved_arguments": {name: str(getattr(args, name).resolve())
                               for name in expected_paths},
        "seed_provenance": seed_provenance(
            config, contract="renderer is deterministic and consumes frozen inferential leaves"),
        "device": None, "started_utc": started_utc,
        "ended_utc": utc_now(), "environment": runtime_environment(None),
        "input_attestation": firewall.attestation,
        "blind_final_state": "locked_unopened",
    }
    atomic_write_json(args.json_output, payload)
    md = f"""# Atlas-v1 amended planning decision

**Evidence class:** `{EVIDENCE_CLASS}`  
**Planning decision v2:** `{outcome}`  
**Training warranted:** `{str(payload['training_warranted']).lower()}`  
**Blind final:** locked and unopened

## Why

The additive completion ran after C1/C2 point scores were known. The manifest-only
preflight found four/five-group LinES strata, below the frozen ten-group minimum.
That invalidates mandatory G1a/G2a randomization hypotheses and has
highest-precedence equivocal status. Diagnostic refit, collateral, stability, and
specificity measurements cannot override this failure.

The original G1, G2, and architecture decision remain unchanged and equivocal.
No new model training and no blind-final opening are authorized.

## Machine predicates

```json
{json.dumps(predicates, indent=2, sort_keys=True)}
```

See `reports/atlas_completion_results.md` and
`results/atlas/completion_v1/completion_results.json` for all estimates and
failure reasons.
"""
    atomic_write_bytes(args.md_output, md.encode())
    l3 = results["raw"]["layers"]["3"]
    report = f"""# Atlas completion results

**Evidence class:** `{EVIDENCE_CLASS}`

## Scope

This additive result completes the requested 500-draw discovery-refit analysis,
Tier-2 collateral, cross-checkpoint stability, and matched-random/sham controls.
It is diagnostic post-score evidence, not a pristine replacement for a blind
final estimate.

## Outcomes

- G1a: **{g1['outcome']}**
- G2a: **{g2['outcome']}**
- Planning decision v2: **{outcome}**
- L3 refit draws present: {l3['present']} / {l3['requested']}
- G2 global complete-case draws: {g2['complete_case_draws']} / {config['draws']}
- Baseline selection failed: {str(results['baseline']['selection_failed']).lower()}

## Controlling limitation

The structural LinES sources contain only four/five independent document groups,
so mandatory conditional randomization inference is invalid under the frozen
minimum-cluster rule. The result remains equivocal; non-rejection is not a
supported negative.

## Provenance

- Parent bundle: `{config['parent_bundle_sha256']}`
- Completion result: `{sha256_file(results_path)}`
- Blind final: locked/unopened
- New training: none
"""
    atomic_write_bytes(args.results_report, report.encode())
    parent_after = verify_parent_freeze_attested(firewall)
    extension_after = verify_completion_freeze()
    verify_attestation_current(firewall.attestation)
    elapsed_sec = time.monotonic() - started
    resources = process_resource_accounting(
        render_stage, elapsed_sec=elapsed_sec, device=None)
    resources["external_output_bytes_before_terminal"] = sum(
        path.stat().st_size for path in [args.json_output, args.md_output,
                                        args.results_report])
    write_terminal(render_stage, complete=True,
                   payload={"schema_version": "atlas_completion_render_complete_v1",
                            "config_sha256": sha256_file(config_path),
                            "resolved_config": config,
                            "resolved_arguments": payload["resolved_arguments"],
                            "seed_provenance": payload["seed_provenance"],
                            "device": None, "started_utc": started_utc,
                            "environment": runtime_environment(None),
                            "resource_accounting": resources,
                            "completion_bundle_sha256": completion_freeze["bundle_sha256"],
                            "planning_decision_v2": outcome,
                            "planning_json_sha256": sha256_file(args.json_output),
                            "planning_markdown_sha256": sha256_file(args.md_output),
                            "results_report_sha256": sha256_file(args.results_report),
                            "completion_verification_sha256": sha256_file(verification_result),
                            "parent_bundle_reverified_after_stage_sha256": parent_after["bundle_sha256"],
                            "completion_bundle_reverified_after_stage_sha256": extension_after["bundle_sha256"],
                            "input_attestation": firewall.attestation})
    print(json.dumps({"planning_decision_v2": outcome, "json": str(args.json_output), "markdown": str(args.md_output)}, indent=2))


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        config = read_json(ROOT / "configs/atlas_completion/analysis.json")
        write_failure_terminal(ROOT / config["run_root"] / "render",
                               stop_code="render_unrecoverable_failure",
                               failed_gate="planning_decision_render", error=exc,
                               input_attestation=_FAILURE_ATTESTATION)
        raise
