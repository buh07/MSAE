#!/usr/bin/env python3
"""Exhaustive stop-aware replay and disposition for diagnostic continuation."""
from __future__ import annotations
import argparse
import json
import math
import os
import pickle
from datetime import datetime
from itertools import combinations
from pathlib import Path
from typing import Any, Callable

import numpy as np

from msa_completion_common import (
    ROOT, assert_final_locked, atomic_write_bytes, atomic_write_json, canonical_json_bytes,
    read_json, sha256_bytes, sha256_file, terminal_state, write_terminal,
    verify_parent_checkpoint, verify_parent_k2_functional,
)
from msa_completion_continuation_common import (
    BASE_DIGEST, BASE_NOT_LAUNCHED_SHA, BASE_SELECTOR_SHA, BASE_STOP_SHA,
    CONFIG, INVENTORY, JOBS, PARENT_DIGEST, RAW_STAGE, RESULT_ROOT, RUN_ROOT,
    SOURCE_RUN, base_gpu_ledger, canonical_job_specs, canonical_stage_members,
    continuation_firewall, load_old_raw, require_recursive_finite,
    resource_job_cap_hours, strict_json,
    verify_continuation_freeze, verify_fixed_source_hashes, verify_rebound_baseline,
    verify_source_inventory,
)
from verify_msae_completion import (
    verify_refit_leaf_summaries, verify_specificity_leaf_summaries,
    verify_stability_leaf_summaries,
)
from collect_msae_completion_continuation import validate_collection

PRIMARY = {
    "absolute_position": ["abs_pos_16", "abs_pos_8"],
    "relative_structural_position": ["relative_quartile", "head_signed_distance",
                                     "dependency_depth", "boundary_state"],
    "lexical_semantic_content": ["token_identity_256", "lemma_identity_256", "ner_coarse"],
}
TASKS = [task for tasks in PRIMARY.values() for task in tasks]


def strict_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line, parse_constant=lambda x: (_ for _ in ()).throw(
        ValueError(f"nonfinite JSON constant {x} in {path}")))
        for line in path.read_text().splitlines() if line]


def quantile_summary(values: list[float | None], *, allow: bool,
                     null_reason: str = "insufficient_scientifically_finite_draws") -> dict[str, Any]:
    finite = [float(v) for v in values if v is not None and math.isfinite(float(v))]
    if not allow:
        return {"n": len(finite), "median": None, "lower_95_one_sided": None,
                "upper_95_one_sided": None, "ci95": None,
                "reason": null_reason}
    if len(finite) != len(values) or not finite:
        return {"n": len(finite), "median": None, "lower_95_one_sided": None,
                "upper_95_one_sided": None, "ci95": None,
                "reason": "coordinate_unavailable_in_finite_draw_set"}
    a = np.asarray(finite, dtype=float)
    return {"n": len(finite), "median": float(np.quantile(a, .5)),
            "lower_95_one_sided": float(np.quantile(a, .05)),
            "upper_95_one_sided": float(np.quantile(a, .95)),
            "ci95": [float(np.quantile(a, .025)), float(np.quantile(a, .975))],
            "reason": None}


def stage_stop_reason(stage_outcome: str, state: str | None,
                      terminal_path: Path | None) -> str | None:
    if state == "stopped" and terminal_path is not None:
        marker = strict_json(terminal_path)
        return str(marker.get("reason") or marker.get("stop_code")
                   or marker.get("failed_gate") or "stage_stopped")
    if stage_outcome != "complete":
        return stage_outcome
    return None


def null_paths(result: dict[str, Any]) -> list[str]:
    found: list[str] = []
    def walk(value: Any, path: str) -> None:
        if value is None or (isinstance(value, float) and not math.isfinite(value)):
            found.append(path)
        elif isinstance(value, dict):
            for key, item in value.items():
                walk(item, f"{path}.{key}")
        elif isinstance(value, list):
            for i, item in enumerate(value):
                walk(item, f"{path}[{i}]")
    for key in ["families", "recoveries", "sentinels"]:
        if key in result:
            walk(result[key], key)
    return found


def expected_sources() -> dict[str, dict[str, set[str]]]:
    manifest = strict_json(ROOT / "configs/atlas/task_row_manifest.json")
    output: dict[str, dict[str, set[str]]] = {}
    for role in ["calibration", "C1", "C2"]:
        output[role] = {}
        for task in TASKS:
            path = ROOT / manifest["roles"][role][task]["path"]
            output[role][task] = {str(row["source"]) for row in strict_jsonl(path)}
    return output


def validate_registration(stage: Path, draw: int, config_sha: str,
                          freeze_sha: str) -> tuple[str, dict[str, Any]] | None:
    registration_path = stage / "completed_hashes" / f"{draw:04d}.json"
    if not registration_path.is_file():
        return None
    registration = strict_json(registration_path)
    artifact = stage / str(registration.get("artifact"))
    if (registration.get("draw_id") != draw
            or registration.get("status") not in {"complete", "failed"}
            or not artifact.is_file()
            or registration.get("artifact_sha256") != sha256_file(artifact)
            or registration.get("config_sha256") != config_sha
            or registration.get("completion_bundle_sha256") != freeze_sha):
        raise RuntimeError(f"draw registration mismatch: {registration_path}")
    payload = strict_json(artifact)
    if (payload.get("draw_id") != draw
            or payload.get("config_sha256") != config_sha
            or payload.get("completion_bundle_sha256") != freeze_sha):
        raise RuntimeError(f"draw payload identity mismatch: {artifact}")
    return str(registration["status"]), payload


def validate_terminal_artifacts(stage: Path, config_sha: str, freeze_sha: str) -> None:
    state = terminal_state(stage)
    if state is None:
        return
    path = stage / ("MEASUREMENT_COMPLETE.json" if state == "complete"
                    else "FROZEN_EQUIVOCAL_STOP.json")
    marker = strict_json(path)
    if (marker.get("config_sha256") != config_sha
            or marker.get("completion_bundle_sha256") != freeze_sha):
        raise RuntimeError(f"series terminal provenance mismatch: {stage}")
    hashes = (marker.get("artifact_sha256") if state == "complete"
              else marker.get("retained_partial_sha256"))
    if isinstance(hashes, dict):
        for relative, digest in hashes.items():
            artifact = stage / relative
            if not artifact.is_file() or sha256_file(artifact) != digest:
                raise RuntimeError(f"series terminal artifact mismatch: {artifact}")


def series_inventory(stage: Path, config_sha: str, freeze_sha: str,
                     leaf_verify: Callable[[dict[str, Any]], None]) -> dict[str, Any]:
    validate_terminal_artifacts(stage, config_sha, freeze_sha)
    registration_files = sorted((stage / "completed_hashes").glob("*.json"))
    observed_names = {p.stem for p in registration_files}
    if any(not name.isdigit() or not 0 <= int(name) < 500 for name in observed_names):
        raise RuntimeError(f"unregistered draw ID in stage: {stage}")
    complete: list[int] = []
    failed: list[int] = []
    finite: list[int] = []
    leaves: dict[int, dict[str, Any]] = {}
    invalid: dict[str, list[str]] = {}
    for draw in range(500):
        row = validate_registration(stage, draw, config_sha, freeze_sha)
        if row is None:
            continue
        status, payload = row
        if status == "failed":
            failed.append(draw)
            continue
        leaf_verify(payload)
        complete.append(draw)
        leaves[draw] = payload
        scientific = payload.get("result", payload)
        if scientific.get("finite") is True:
            finite.append(draw)
        else:
            invalid[str(draw)] = null_paths(scientific)
    state = terminal_state(stage)
    if state is not None:
        terminal_path = stage / ("MEASUREMENT_COMPLETE.json" if state == "complete"
                                 else "FROZEN_EQUIVOCAL_STOP.json")
        marker = strict_json(terminal_path)
        complete_schema = ("atlas_completion_stability_terminal_v1"
                           if stage.name == "stability"
                           else "atlas_completion_refit_terminal_v1")
        technical = marker.get("schema_version") == "atlas_completion_diagnostic_continuation_technical_stop_v1"
        if (state == "complete" and marker.get("schema_version") != complete_schema) or (
                state == "stopped" and marker.get("schema_version") not in {
                    "atlas_completion_frozen_stop_v1",
                    "atlas_completion_diagnostic_continuation_technical_stop_v1"}):
            raise RuntimeError(f"series terminal schema/state mismatch: {stage}")
        if technical:
            if (state != "stopped"
                    or marker.get("diagnostic_continuation_only") is not True
                    or marker.get("scientific_retry_allowed") is not False
                    or marker.get("decision_promotion_allowed") is not False):
                raise RuntimeError(f"technical series terminal semantics mismatch: {stage}")
        else:
            point_path = stage / "point.json"
            if not point_path.is_file():
                raise RuntimeError(f"nontechnical series terminal lacks point artifact: {stage}")
            point_payload = strict_json(point_path)
            if (point_payload.get("config_sha256") != config_sha
                    or point_payload.get("completion_bundle_sha256") != freeze_sha):
                raise RuntimeError(f"series point provenance mismatch: {stage}")
            point_scientific = point_payload.get("result", point_payload)
            point_finite = point_scientific.get("finite") is True
            if (marker.get("requested_draws") != 500
                    or marker.get("scientifically_finite_draw_ids") != finite
                    or marker.get("finite_draws") != len(finite)
                    or marker.get("point_scientifically_finite") is not point_finite):
                raise RuntimeError(f"series terminal inventory mismatch: {stage}")
            point_nonfinite_stop = (
                state == "stopped"
                and marker.get("stop_code") == "point_scientifically_nonfinite"
                and marker.get("failed_gate") == "required_point_finiteness")
            if point_finite == point_nonfinite_stop:
                raise RuntimeError(f"series point/stop semantics mismatch: {stage}")
            terminal_failed = marker.get("failed_draws", marker.get("failed_draw_ids"))
            if terminal_failed != failed:
                raise RuntimeError(f"series terminal failure inventory mismatch: {stage}")
            if state == "stopped" and (
                    marker.get("requested_draw_ids") != list(range(500))
                    or marker.get("registered_complete_draw_ids") != complete
                    or marker.get("completed_draw_ids") != finite):
                raise RuntimeError(f"stopped series terminal inventory mismatch: {stage}")
    return {"requested_draw_ids": list(range(500)), "complete_draw_ids": complete,
            "failed_draw_ids": failed, "scientifically_finite_draw_ids": finite,
            "invalid_draw_fields": invalid, "leaves": leaves}


def k2_series(job: str, stage_outcome: str, config: dict[str, Any],
              config_sha: str, freeze_sha: str, baseline: dict[str, Any],
              sources: dict[str, dict[str, set[str]]]) -> dict[str, Any]:
    stage = RUN_ROOT / "k2_refit" / job
    point_path = stage / "point.json"
    point = strict_json(point_path) if point_path.is_file() else None
    if point is not None:
        if (point.get("draw_id") != "point" or point.get("config_sha256") != config_sha
                or point.get("completion_bundle_sha256") != freeze_sha):
            raise RuntimeError(f"K2 point provenance mismatch: {job}")
        paired = load_old_raw("point")
        verify_refit_leaf_summaries(point, baseline, sources, expected_kind="k2",
                                    expected_layer=3, expected_job=job,
                                    paired_raw_payload=paired)
        old_point = RAW_STAGE / "point.json"
        attested = point.get("input_attestation", {}).get(str(old_point.resolve()))
        if not isinstance(attested, dict) or attested.get("sha256") != sha256_file(old_point):
            raise RuntimeError(f"K2 point lacks paired raw attestation: {job}")
    def verify_leaf(payload: dict[str, Any]) -> None:
        draw = int(payload["draw_id"])
        paired = load_old_raw(draw)
        verify_refit_leaf_summaries(payload, baseline, sources, expected_kind="k2",
                                    expected_layer=3, expected_job=job,
                                    paired_raw_payload=paired)
        required_attested = [RAW_STAGE / f"draws/{draw:04d}.json",
                             RAW_STAGE / f"completed_hashes/{draw:04d}.json"]
        for path in required_attested:
            row = payload.get("input_attestation", {}).get(str(path.resolve()))
            if not isinstance(row, dict) or row.get("sha256") != sha256_file(path):
                raise RuntimeError(f"K2 leaf lacks paired raw attestation: {path}")
    inventory = series_inventory(stage, config_sha, freeze_sha, verify_leaf)
    finite_ids = inventory["scientifically_finite_draw_ids"]
    complete_ids = inventory["complete_draw_ids"]
    leaves = inventory.pop("leaves")
    state = terminal_state(stage)
    terminal_path = (stage / ("MEASUREMENT_COMPLETE.json" if state == "complete"
                              else "FROZEN_EQUIVOCAL_STOP.json") if state else None)
    stop_reason = stage_stop_reason(stage_outcome, state, terminal_path)
    null_reason = (stop_reason or ("point_missing" if point is None else
                   "insufficient_scientifically_finite_draws"))
    allow = bool(stage_outcome == "complete" and state == "complete"
                 and point is not None
                 and len(finite_ids) >= int(config["minimum_complete_draws"]))
    series: dict[str, Any] = {"families": {}, "recoveries": {"pos": {}, "content": {}},
                              "sentinels": {}}
    for family in PRIMARY:
        series["families"][family] = {}
        for field in ["assigned_recovery", "leakage", "selectivity_margin"]:
            values = [leaves[d]["result"]["families"][family].get(field) for d in complete_ids]
            inference_values = [leaves[d]["result"]["families"][family].get(field)
                                for d in finite_ids]
            series["families"][family][field] = {
                "draw_ids": complete_ids, "draw_values": values,
                "inference_draw_ids": finite_ids,
                "summary": quantile_summary(
                    inference_values, allow=allow, null_reason=null_reason)}
    for rep in ["pos", "content"]:
        for task in TASKS:
            values = [leaves[d]["result"]["recoveries"][rep][task] for d in complete_ids]
            inference_values = [leaves[d]["result"]["recoveries"][rep][task]
                                for d in finite_ids]
            series["recoveries"][rep][task] = {
                "draw_ids": complete_ids, "draw_values": values,
                "inference_draw_ids": finite_ids,
                "summary": quantile_summary(
                    inference_values, allow=allow, null_reason=null_reason)}
    for sentinel in config["sentinels"]:
        values = [leaves[d]["result"]["sentinels"][sentinel]["normalized_damage"]
                  for d in complete_ids]
        inference_values = [leaves[d]["result"]["sentinels"][sentinel]["normalized_damage"]
                            for d in finite_ids]
        series["sentinels"][sentinel] = {
            "draw_ids": complete_ids, "draw_values": values,
            "inference_draw_ids": finite_ids,
            "summary": quantile_summary(
                inference_values, allow=allow, null_reason=null_reason)}
    return {
        "stage_outcome": stage_outcome, "terminal_state": state,
        "terminal_path": str(terminal_path) if terminal_path else None,
        "terminal_sha256": sha256_file(terminal_path) if terminal_path else None,
        "stop_reason": stop_reason,
        "point": ({"families": point["result"]["families"],
                   "recoveries": point["result"]["recoveries"],
                   "sentinels": point["result"]["sentinels"],
                   "finite": point["result"]["finite"]} if point else None),
        **inventory, "inference_valid": allow, "inference_gate": None,
        "inference_null_reason": (None if allow else null_reason),
        "series": series,
    }


def stability_series(stage_outcome: str, config: dict[str, Any], config_sha: str,
                     freeze_sha: str, baseline: dict[str, Any]) -> dict[str, Any]:
    stage = RUN_ROOT / "stability"
    point_path = stage / "point.json"
    point = strict_json(point_path) if point_path.is_file() else None
    if point is not None:
        if (point.get("config_sha256") != config_sha
                or point.get("completion_bundle_sha256") != freeze_sha):
            raise RuntimeError("stability point provenance mismatch")
        verify_stability_leaf_summaries(point, config, baseline)
    inventory = series_inventory(stage, config_sha, freeze_sha,
                                 lambda p: verify_stability_leaf_summaries(p, config, baseline))
    finite_ids = inventory["scientifically_finite_draw_ids"]
    complete_ids = inventory["complete_draw_ids"]
    leaves = inventory.pop("leaves")
    state = terminal_state(stage)
    terminal_path = (stage / ("MEASUREMENT_COMPLETE.json" if state == "complete"
                              else "FROZEN_EQUIVOCAL_STOP.json") if state else None)
    stop_reason = stage_stop_reason(stage_outcome, state, terminal_path)
    null_reason = (stop_reason or ("point_missing" if point is None else
                   "insufficient_scientifically_finite_draws"))
    allow = bool(stage_outcome == "complete" and state == "complete"
                 and point is not None
                 and len(finite_ids) >= int(config["minimum_complete_draws"]))
    task_names = list(TASKS)
    primary_jobs = list(config["primary_checkpoints"])
    descriptive_job = config["descriptive_checkpoints"][0]
    expected_pair_keys = sorted([
        *(f"{left}__{right}" for left, right in combinations(primary_jobs, 2)),
        f"{primary_jobs[0]}__{descriptive_job}",
    ])
    family_names = list(PRIMARY)
    series: dict[str, Any] = {"tasks": {}, "families": {}}
    for task in task_names:
        eligible = baseline["tier1_eligibility"][task]["eligible"] is True
        first = point["tasks"].get(task) if point else next(
            (row["tasks"].get(task) for row in leaves.values() if task in row["tasks"]), None)
        if eligible and first is None:
            raise RuntimeError(f"eligible stability task is absent: {task}")
        if not eligible and (first is not None or any(task in row["tasks"] for row in leaves.values())):
            raise RuntimeError(f"ineligible stability task unexpectedly scored: {task}")
        pair_keys = sorted(first["k2_pairs"]) if first else expected_pair_keys
        if pair_keys != expected_pair_keys:
            raise RuntimeError(f"stability K2 pair inventory mismatch: {task}")
        simple_values = ([leaves[d]["tasks"][task]["simple_A_B"] for d in complete_ids]
                         if eligible else [None for _ in complete_ids])
        inference_simple = ([leaves[d]["tasks"][task]["simple_A_B"] for d in finite_ids]
                            if eligible else [None for _ in finite_ids])
        task_null_reason = null_reason if eligible else "task_ineligible_at_frozen_baseline"
        series["tasks"][task] = {
            "eligible": eligible,
            "simple_A_B": {"draw_ids": complete_ids, "draw_values": simple_values,
                           "inference_draw_ids": finite_ids,
                           "summary": quantile_summary(
                               inference_simple, allow=allow and eligible,
                               null_reason=task_null_reason)},
            "k2_pairs": {},
        }
        for pair in pair_keys:
            values = ([leaves[d]["tasks"][task]["k2_pairs"][pair] for d in complete_ids]
                      if eligible else [None for _ in complete_ids])
            inference_values = ([leaves[d]["tasks"][task]["k2_pairs"][pair]
                                 for d in finite_ids]
                                if eligible else [None for _ in finite_ids])
            series["tasks"][task]["k2_pairs"][pair] = {
                "draw_ids": complete_ids, "draw_values": values,
                "inference_draw_ids": finite_ids,
                "summary": quantile_summary(
                    inference_values, allow=allow and eligible,
                    null_reason=task_null_reason)}
    family_fields = ["learned_mean_pairwise_cka", "learned_stability_loss",
                     "simple_A_B_cka_descriptive", "g4_g7_regularizer_sensitivity_cka_descriptive"]
    for family in family_names:
        series["families"][family] = {}
        for field in family_fields:
            values = [leaves[d]["families"][family].get(field) for d in complete_ids]
            inference_values = [leaves[d]["families"][family].get(field)
                                for d in finite_ids]
            series["families"][family][field] = {
                "draw_ids": complete_ids, "draw_values": values,
                "inference_draw_ids": finite_ids,
                "summary": quantile_summary(
                    inference_values, allow=allow, null_reason=null_reason)}
    return {"stage_outcome": stage_outcome, "terminal_state": state,
            "terminal_path": str(terminal_path) if terminal_path else None,
            "terminal_sha256": sha256_file(terminal_path) if terminal_path else None,
            "stop_reason": stop_reason,
            "point": ({"tasks": {task: point["tasks"].get(task) for task in TASKS},
                       "task_eligibility": {task: baseline["tier1_eligibility"][task]["eligible"]
                                            for task in TASKS},
                       "families": point["families"], "finite": point["finite"]}
                      if point else None),
            **inventory, "inference_valid": allow, "inference_gate": None,
            "inference_null_reason": (None if allow else null_reason),
            "series": series}


def specificity_series(job: str, stage_outcome: str, config: dict[str, Any],
                       config_sha: str, freeze_sha: str, baseline: dict[str, Any],
                       transforms: list[dict[str, Any]], token_map: dict[str, dict[str, Any]],
                       firewall: Any) -> dict[str, Any]:
    stage = RUN_ROOT / "specificity" / job
    result_path = stage / "specificity.json"
    empty = {"result_sha256": None, "transform_ids": None, "summaries": None, "counterfactual_gate_valid": None,
             "counterfactual_gate_reasons": None, "ce_collateral": None,
             "simple_identity_collateral": None}
    state = terminal_state(stage)
    terminal_path = (stage / ("MEASUREMENT_COMPLETE.json" if state == "complete"
                              else "FROZEN_EQUIVOCAL_STOP.json") if state else None)
    complete_result = bool(stage_outcome == "complete" and state == "complete"
                           and result_path.is_file())
    if not complete_result:
        return {"stage_outcome": stage_outcome, "terminal_state": state,
                "terminal_path": str(terminal_path) if terminal_path else None,
                "terminal_sha256": sha256_file(terminal_path) if terminal_path else None,
                "stop_reason": stage_stop_reason(stage_outcome, state, terminal_path),
                **empty}
    marker = strict_json(terminal_path)
    if marker.get("result_sha256") != sha256_file(result_path):
        raise RuntimeError(f"specificity complete terminal does not bind result: {job}")
    payload = strict_json(result_path)
    if (payload.get("config_sha256") != config_sha
            or payload.get("completion_bundle_sha256") != freeze_sha):
        raise RuntimeError(f"specificity result binding mismatch: {job}")
    checkpoint = verify_parent_checkpoint(job, firewall)
    parent_path = ROOT / f"results/atlas/k2_v1/{job}_functional.json"
    parent = verify_parent_k2_functional(ROOT / config["source_run_root"], job, firewall)
    verify_specificity_leaf_summaries(
        payload, config, token_map, transforms, expected_job=job,
        expected_checkpoint_sha256=checkpoint["sha256"],
        expected_parent_functional_sha256=sha256_file(parent_path),
        expected_parent_counterfactual_rows=parent["counterfactual_rows"],
        expected_parent_ce_rows=parent["ce_rows"],
        expected_simple_candidate=baseline["selected_simple_baseline"])
    return {"stage_outcome": stage_outcome, "terminal_state": state,
            "terminal_path": str(terminal_path) if terminal_path else None,
            "terminal_sha256": sha256_file(terminal_path) if terminal_path else None,
            "stop_reason": (strict_json(terminal_path).get("reason") if state == "stopped" else None),
            "result_sha256": sha256_file(result_path),
            "transform_ids": [row["transform_id"] for row in payload["rows"]],
            "summaries": payload["summaries"],
            "counterfactual_gate_valid": payload["counterfactual_gate_valid"],
            "counterfactual_gate_reasons": payload["counterfactual_gate_reasons"],
            "ce_collateral": payload["ce_collateral"],
            "simple_identity_collateral": payload["simple_identity_collateral"]}


def null_metric(reason: str) -> dict[str, Any]:
    return {"draw_ids": [], "draw_values": [], "inference_draw_ids": [],
            "summary": {"n": 0, "median": None, "lower_95_one_sided": None,
                        "upper_95_one_sided": None, "ci95": None,
                        "reason": reason}}


def null_k2(job: str, reason: str) -> dict[str, Any]:
    return {"stage_outcome": "baseline_not_complete", "terminal_state": None,
            "terminal_path": None, "terminal_sha256": None, "stop_reason": reason,
            "point": None, "requested_draw_ids": list(range(500)),
            "complete_draw_ids": [], "failed_draw_ids": [],
            "scientifically_finite_draw_ids": [], "invalid_draw_fields": {},
            "inference_valid": False, "inference_gate": None,
            "inference_null_reason": reason,
            "series": {
                "families": {family: {field: null_metric(reason) for field in
                    ["assigned_recovery", "leakage", "selectivity_margin"]}
                    for family in PRIMARY},
                "recoveries": {rep: {task: null_metric(reason) for task in TASKS}
                               for rep in ["pos", "content"]},
                "sentinels": {task: null_metric(reason)
                              for task in read_json(CONFIG)["sentinels"]}}}


def null_stability(reason: str) -> dict[str, Any]:
    config = read_json(CONFIG)
    source_baseline = read_json(SOURCE_RUN / "baseline/baseline.json")
    primary = config["primary_checkpoints"]
    pair_keys = sorted([
        *(f"{left}__{right}" for left, right in combinations(primary, 2)),
        f"{primary[0]}__{config['descriptive_checkpoints'][0]}",
    ])
    family_fields = ["learned_mean_pairwise_cka", "learned_stability_loss",
                     "simple_A_B_cka_descriptive",
                     "g4_g7_regularizer_sensitivity_cka_descriptive"]
    return {"stage_outcome": "baseline_not_complete", "terminal_state": None,
            "terminal_path": None, "terminal_sha256": None, "stop_reason": reason,
            "point": None, "requested_draw_ids": list(range(500)),
            "complete_draw_ids": [], "failed_draw_ids": [],
            "scientifically_finite_draw_ids": [], "invalid_draw_fields": {},
            "inference_valid": False, "inference_gate": None,
            "inference_null_reason": reason,
            "series": {"tasks": {
                task: {"eligible": source_baseline["tier1_eligibility"][task]["eligible"],
                       "simple_A_B": null_metric(reason),
                       "k2_pairs": {pair: null_metric(reason) for pair in pair_keys}}
                for task in TASKS},
                "families": {family: {field: null_metric(reason) for field in family_fields}
                             for family in PRIMARY}}}


def null_specificity(reason: str) -> dict[str, Any]:
    return {"stage_outcome": "baseline_not_complete", "terminal_state": None,
            "terminal_path": None, "terminal_sha256": None, "stop_reason": reason,
            "result_sha256": None, "transform_ids": None, "summaries": None,
            "counterfactual_gate_valid": None, "counterfactual_gate_reasons": None,
            "ce_collateral": None, "simple_identity_collateral": None}


def fixed_disposition() -> dict[str, Any]:
    return {"original_G1": "equivocal_unchanged",
            "original_G2": "equivocal_unchanged", "G1a": "invalid_unrendered",
            "G2a": "not_promotable_unrendered", "paper_branch": "unselected",
            "training_warranted": False, "diagnostic_continuation_only": True,
            "decision_promotion_allowed": False}


def resource_accounting_report(
        collection: dict[str, Any], *, continuation_actual_gpu_hours: float,
        base_ledger: dict[str, Any]) -> dict[str, Any]:
    config = strict_json(CONFIG)
    specs = canonical_job_specs()
    assignments = {
        job: resource_job_cap_hours(spec, config) for job, spec in sorted(specs.items())}
    maximum_potential = sum(assignments.values())
    if abs(maximum_potential - 54.2) > 1e-9:
        raise RuntimeError("continuation maximum-potential reservation sum changed")
    jobs = collection.get("jobs", {})
    observed = sum(float(row.get("reserved_gpu_hours", 0.0)) for row in jobs.values())
    reached = sorted(
        job for job, row in jobs.items() if float(row.get("reserved_gpu_hours", 0.0)) > 0)
    expected_observed = sum(assignments[job] for job in reached)
    if abs(observed - expected_observed) > 1e-9:
        raise RuntimeError("published reservation total differs from reached-job caps")
    base_actual = float(base_ledger["total_gpu_hours"])
    maximum_total = float(config["budgets"]["maximum_total_gpu_hours"])
    cumulative_actual = base_actual + float(continuation_actual_gpu_hours)
    cumulative_reserved = base_actual + observed
    if cumulative_actual > maximum_total + 1e-9 or cumulative_reserved > maximum_total + 1e-9:
        raise RuntimeError("published continuation resource accounting exceeds budget")
    return {
        "base_actual_gpu_hours": base_actual, "base_gpu_ledger": base_ledger,
        "continuation_actual_gpu_hours": float(continuation_actual_gpu_hours),
        "cumulative_actual_gpu_hours": cumulative_actual,
        "continuation_observed_reserved_gpu_hours": observed,
        "cumulative_base_actual_plus_continuation_reserved_gpu_hours": cumulative_reserved,
        "continuation_maximum_potential_reserved_gpu_hours": maximum_potential,
        "maximum_total_gpu_hours": maximum_total,
        "reservation_cap_assignments_gpu_hours": assignments,
        "jobs_reaching_reservation": reached,
        "projected_continuation_gpu_hours": 27.3943,
    }


def assert_no_forbidden_continuation_activity() -> dict[str, Any]:
    """Enforce the diagnostic-only boundary without opening blind-final files."""
    assert_final_locked()
    forbidden_decision_outputs = [
        ROOT / "results/atlas/completion_v1",
        ROOT / "reports/planning_decision_v2.json",
        ROOT / "reports/planning_decision_v2.md",
    ]
    present_decisions = [str(path) for path in forbidden_decision_outputs if path.exists()]
    if present_decisions:
        raise RuntimeError(f"forbidden decision-bearing output exists: {present_decisions}")
    forbidden_suffixes = {".pt", ".pth", ".ckpt", ".safetensors", ".bin"}
    forbidden_training_outputs = [
        str(path) for path in RUN_ROOT.rglob("*") if path.is_file()
        and (path.suffix.lower() in forbidden_suffixes
             or "checkpoint" in path.name.lower()
             or "train" in path.name.lower())
    ]
    if forbidden_training_outputs:
        raise RuntimeError(
            f"training/checkpoint output in continuation root: {forbidden_training_outputs}")
    owned_needles = {str(RUN_ROOT.resolve()), str(CONFIG.resolve())}
    for path in [RUN_ROOT, CONFIG]:
        if path.is_relative_to(ROOT):
            owned_needles.add(str(path.relative_to(ROOT)))
    training_processes: list[dict[str, Any]] = []
    for proc in Path("/proc").glob("[0-9]*/cmdline"):
        try:
            raw = proc.read_bytes()
        except (FileNotFoundError, PermissionError, ProcessLookupError):
            continue
        text = raw.replace(b"\0", b" ").decode("utf-8", errors="replace")
        tokens = [token for token in text.split() if token]
        owns_continuation = any(needle in text for needle in owned_needles)
        is_training = any(
            Path(token).name.startswith(("train_", "finetune_"))
            or Path(token).name in {"train", "trainer"} for token in tokens)
        if owns_continuation and is_training:
            training_processes.append({"pid": int(proc.parent.name), "command": text})
    if training_processes:
        raise RuntimeError(f"continuation-owned training process exists: {training_processes}")
    return {
        "blind_final_unlock_present": False,
        "blind_final_access_authorized": False,
        "blind_final_path_referenced_by_continuation_support": False,
        "forbidden_decision_outputs_present": [],
        "continuation_training_outputs_present": [],
        "continuation_training_processes_present": [],
    }


def baseline_failure_result(collection: dict[str, Any], freeze: dict[str, Any],
                            inventory: dict[str, Any]) -> dict[str, Any]:
    if collection.get("collection_outcome") != "baseline_not_complete":
        raise RuntimeError("invalid baseline-failure collection outcome")
    if set(collection.get("jobs", {})) != set(canonical_job_specs()):
        raise RuntimeError("baseline-failure job inventory mismatch")
    allowed_causes = {
        (RUN_ROOT / "baseline/FROZEN_EQUIVOCAL_STOP.json").resolve(),
        (RUN_ROOT / "job_manifests/baseline_rebind.terminal.json").resolve(),
    }
    causes = {Path(row["cause_path"]).resolve() for row in collection["jobs"].values()}
    if len(causes) != 1 or next(iter(causes)) not in allowed_causes:
        raise RuntimeError("baseline-failure cause is not canonical")
    cause = next(iter(causes))
    for row in collection["jobs"].values():
        if (row.get("outcome") != "baseline_not_complete"
                or row.get("cause_sha256") != sha256_file(cause)):
            raise RuntimeError("baseline-failure cause binding mismatch")
    reason = "baseline_provenance_rebind_failed"
    k2 = {job: null_k2(job, reason) for job in JOBS}
    specificity = {job: null_specificity(reason) for job in JOBS}
    checked = {}
    for path in sorted(RUN_ROOT.rglob("*.json")):
        parsed = strict_json(path); require_recursive_finite(parsed, str(path.relative_to(ROOT)))
        checked[str(path.relative_to(ROOT))] = sha256_file(path)
    base_ledger = base_gpu_ledger()
    resource_accounting = resource_accounting_report(
        collection, continuation_actual_gpu_hours=0.0, base_ledger=base_ledger)
    return {
        "schema_version": "atlas_completion_diagnostic_continuation_results_v1",
        "evidence_class": "postscore_amended_architecture_evidence",
        "provenance": {"parent_bundle_sha256": PARENT_DIGEST,
            "base_completion_bundle_sha256": BASE_DIGEST,
            "continuation_bundle_sha256": freeze["bundle_sha256"],
            "config_sha256": sha256_file(CONFIG), "base_l3_stop_sha256": BASE_STOP_SHA,
            "base_l3_selector_sha256": BASE_SELECTOR_SHA,
            "base_not_launched_sha256": BASE_NOT_LAUNCHED_SHA,
            "source_inventory_manifest_sha256": sha256_file(INVENTORY),
            "source_inventory_before_after_sha256": inventory["inventory_sha256"],
            "final_unlock_present": False,
            "baseline_rebind": {"science_equal": False, "cause_path": str(cause),
                                "cause_sha256": sha256_file(cause)}},
        "execution": {"baseline_rebind": None, "jobs": collection["jobs"],
                      "stages": collection["stages"], "strict_json_files": checked,
                      "forbidden_activity_checks": assert_no_forbidden_continuation_activity(),
                      "resource_accounting": resource_accounting},
        "k2": k2, "stability": null_stability(reason),
        "specificity": specificity, "disposition": fixed_disposition(),
        "limitations": {"all_diagnostic_stages_complete": False,
            "unavailable_or_invalid_evidence": [reason],
            "job_stop_reasons": {job: reason for job in canonical_job_specs()},
            "stage_stop_reasons": {
                **{f"k2:{job}": reason for job in JOBS}, "stability": reason,
                **{f"specificity:{job}": reason for job in JOBS}}}}


def recompute() -> dict[str, Any]:
    forbidden_checks = assert_no_forbidden_continuation_activity()
    freeze = verify_continuation_freeze()
    inventory = verify_source_inventory()
    verify_fixed_source_hashes()
    collection = validate_collection(strict_json(RUN_ROOT / "COLLECTION_COMPLETE.json"))
    if collection.get("collection_outcome") == "baseline_not_complete":
        result = baseline_failure_result(collection, freeze, inventory)
        require_recursive_finite(result)
        return result
    config = strict_json(CONFIG)
    baseline_verified = verify_rebound_baseline()
    baseline_result = baseline_verified["result"]
    with (RUN_ROOT / "baseline/baseline_bundle.pkl").open("rb") as handle:
        baseline = pickle.load(handle)
    sources = expected_sources()
    config_sha, freeze_sha = sha256_file(CONFIG), freeze["bundle_sha256"]
    k2 = {job: k2_series(job, collection["stages"][f"k2_refit/{job}"]["stage_outcome"],
                         config, config_sha, freeze_sha, baseline, sources) for job in JOBS}
    stability = stability_series(collection["stages"]["stability"]["stage_outcome"],
                                 config, config_sha, freeze_sha, baseline)
    transforms = strict_jsonl(ROOT / "data/atlas_v1/transforms/C2.jsonl")
    if len(transforms) != 128 or len({r["transform_id"] for r in transforms}) != 128:
        raise RuntimeError("frozen specificity transform inventory mismatch")
    token_manifest = strict_json(ROOT / "data/atlas_completion_v1/token_control_manifest.json")
    token_map = {row["transform_id"]: row for row in token_manifest["rows"]}
    firewall = continuation_firewall(ROOT / config["source_run_root"], RUN_ROOT)
    specificity = {job: specificity_series(
        job, collection["stages"][f"specificity/{job}"]["stage_outcome"],
        config, config_sha, freeze_sha, baseline, transforms, token_map, firewall)
        for job in JOBS}
    # Strictly parse every JSON artifact and reject NaN/Inf while preserving null.
    checked: dict[str, str] = {}
    for root in [RUN_ROOT]:
        for path in sorted(root.rglob("*.json")):
            parsed = strict_json(path); require_recursive_finite(parsed, str(path.relative_to(ROOT)))
            checked[str(path.relative_to(ROOT))] = sha256_file(path)
    continuation_gpu = sum(float(row["actual_gpu_hours"])
                           for row in collection["jobs"].values())
    base_ledger = base_gpu_ledger()
    resource_accounting = resource_accounting_report(
        collection, continuation_actual_gpu_hours=continuation_gpu,
        base_ledger=base_ledger)
    all_complete = (all(row["stage_outcome"] == "complete"
                        for row in collection["stages"].values())
                    and all(row["inference_valid"] is True for row in k2.values())
                    and stability["inference_valid"] is True
                    and all(row["terminal_state"] == "complete"
                            for row in specificity.values()))
    job_stop_reasons = {
        job: row.get("job_stop_reason") for job, row in sorted(collection["jobs"].items())}
    limitations = sorted({
        reason for row in [*k2.values(), stability, *specificity.values()]
        for reason in [row.get("stop_reason"), row.get("inference_null_reason")]
        if reason is not None} | {
        f"job:{job}:{reason}" for job, reason in job_stop_reasons.items()
        if reason is not None})
    result = {
        "schema_version": "atlas_completion_diagnostic_continuation_results_v1",
        "evidence_class": "postscore_amended_architecture_evidence",
        "provenance": {
            "parent_bundle_sha256": PARENT_DIGEST,
            "base_completion_bundle_sha256": BASE_DIGEST,
            "continuation_bundle_sha256": freeze_sha,
            "config_sha256": config_sha,
            "base_l3_stop_sha256": BASE_STOP_SHA,
            "base_l3_selector_sha256": BASE_SELECTOR_SHA,
            "base_not_launched_sha256": BASE_NOT_LAUNCHED_SHA,
            "source_inventory_manifest_sha256": sha256_file(INVENTORY),
            "source_inventory_before_after_sha256": inventory["inventory_sha256"],
            "final_unlock_present": False,
            "baseline_rebind": {"science_equal": True,
                                "source_result_sha256": baseline_result["provenance_rebind"]["source_result_sha256"],
                                "rebound_result_sha256": baseline_verified["result_sha256"],
                                "rebound_bundle_sha256": baseline_verified["bundle_sha256"],
                                "selected_simple_baseline": baseline["selected_simple_baseline"],
                                "baseline_selection_failed": baseline["baseline_selection_failed"]},
        },
        "execution": {"baseline_rebind": baseline_verified["terminal"],
                      "jobs": collection["jobs"], "stages": collection["stages"],
                      "strict_json_files": checked,
                      "forbidden_activity_checks": forbidden_checks,
                      "resource_accounting": resource_accounting},
        "k2": k2, "stability": stability, "specificity": specificity,
        "disposition": fixed_disposition(),
        "limitations": {"all_diagnostic_stages_complete": all_complete,
                        "unavailable_or_invalid_evidence": limitations,
                        "job_stop_reasons": job_stop_reasons,
                        "stage_stop_reasons": {
                            **{f"k2:{j}": k2[j]["stop_reason"] for j in JOBS},
                            "stability": stability["stop_reason"],
                            **{f"specificity:{j}": specificity[j]["stop_reason"] for j in JOBS}}},
    }
    require_recursive_finite(result)
    return result


def report_text(result: dict[str, Any]) -> str:
    lines = ["# Atlas completion diagnostic continuation results", "",
             "This artifact is diagnostic-only and cannot select a paper branch.", "",
             "## Fixed disposition", "",
             "- Original G1/G2 remain equivocal and unchanged.",
             "- G1a is invalid/unrendered; G2a is not promotable/unrendered.",
             "- Paper branch remains unselected; training is not warranted.", "",
             "## Stage outcomes", ""]
    for stage, row in result["execution"]["stages"].items():
        lines.append(f"- `{stage}`: `{row['stage_outcome']}`")
    accounting = result["execution"]["resource_accounting"]
    lines.extend(["", "## Resource accounting", "",
                  f"- Base actual GPU-hours: {accounting['base_actual_gpu_hours']}",
                  f"- Continuation actual GPU-hours: {accounting['continuation_actual_gpu_hours']}",
                  f"- Continuation observed reserved GPU-hours: {accounting['continuation_observed_reserved_gpu_hours']}",
                  f"- Continuation maximum-potential reserved GPU-hours: {accounting['continuation_maximum_potential_reserved_gpu_hours']}",
                  f"- Frozen total GPU-hour ceiling: {accounting['maximum_total_gpu_hours']}"])
    lines.extend(["", "## Scientifically finite draws", ""])
    for job, row in result["k2"].items():
        lines.append(f"- K2 `{job}`: {len(row['scientifically_finite_draw_ids'])}/500")
    lines.append(f"- stability: {len(result['stability']['scientifically_finite_draw_ids'])}/500")
    lines.extend(["", "## Limitations", ""])
    limitations = result["limitations"]["unavailable_or_invalid_evidence"]
    lines.extend([f"- {item}" for item in limitations] or ["- none"])
    return "\n".join(lines) + "\n"


def validate_result_terminal(result: dict[str, Any], result_path: Path,
                             report_path: Path, *, result_root: Path = RESULT_ROOT) -> str:
    expected_complete = result["limitations"]["all_diagnostic_stages_complete"] is True
    expected_state = "complete" if expected_complete else "stopped"
    state = terminal_state(result_root)
    if state != expected_state:
        raise RuntimeError("diagnostic result terminal state contradicts replay")
    marker_path = result_root / (
        "MEASUREMENT_COMPLETE.json" if state == "complete" else "FROZEN_EQUIVOCAL_STOP.json")
    marker = strict_json(marker_path)
    expected_keys = {
        "schema_version", "result_sha256", "report_sha256", "config_sha256",
        "completion_bundle_sha256", "diagnostic_continuation_only",
        "decision_promotion_allowed", "reason", "terminal_state", "evidence_class",
        "ended_utc",
    }
    expected_reason = None if expected_complete else "one_or_more_diagnostics_stopped_or_unavailable"
    if (set(marker) != expected_keys
            or marker.get("schema_version") != "atlas_completion_diagnostic_continuation_result_terminal_v1"
            or marker.get("result_sha256") != sha256_file(result_path)
            or marker.get("report_sha256") != sha256_file(report_path)
            or marker.get("config_sha256") != sha256_file(CONFIG)
            or marker.get("completion_bundle_sha256") != result["provenance"]["continuation_bundle_sha256"]
            or marker.get("diagnostic_continuation_only") is not True
            or marker.get("decision_promotion_allowed") is not False
            or marker.get("reason") != expected_reason
            or marker.get("terminal_state") != (
                "measurement_complete" if expected_complete else "frozen_equivocal_stop")
            or marker.get("evidence_class") != "postscore_amended_architecture_evidence"):
        raise RuntimeError("diagnostic result terminal envelope mismatch")
    ended = marker.get("ended_utc")
    try:
        parsed = datetime.fromisoformat(str(ended).replace("Z", "+00:00"))
    except ValueError as exc:
        raise RuntimeError("diagnostic result terminal timestamp is invalid") from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise RuntimeError("diagnostic result terminal timestamp is not timezone-aware")
    return state


def main() -> None:
    parser = argparse.ArgumentParser(); parser.add_argument("--verify-only", action="store_true")
    args = parser.parse_args()
    result = recompute(); text = report_text(result)
    result_path = RESULT_ROOT / "diagnostic_results.json"
    report_path = RESULT_ROOT / "diagnostic_results.md"
    if args.verify_only:
        if strict_json(result_path) != result or report_path.read_text() != text:
            raise RuntimeError("persisted diagnostic disposition differs from replay")
        state = validate_result_terminal(result, result_path, report_path)
        print({"verified": True, "result_sha256": sha256_file(result_path), "state": state})
        return
    if RESULT_ROOT.exists():
        raise RuntimeError("diagnostic result root is create-once")
    RESULT_ROOT.mkdir(parents=True)
    atomic_write_json(result_path, result)
    atomic_write_bytes(report_path, text.encode("utf-8"))
    all_complete = result["limitations"]["all_diagnostic_stages_complete"]
    write_terminal(RESULT_ROOT, complete=bool(all_complete), payload={
        "schema_version": "atlas_completion_diagnostic_continuation_result_terminal_v1",
        "result_sha256": sha256_file(result_path), "report_sha256": sha256_file(report_path),
        "config_sha256": sha256_file(CONFIG),
        "completion_bundle_sha256": result["provenance"]["continuation_bundle_sha256"],
        "diagnostic_continuation_only": True, "decision_promotion_allowed": False,
        "reason": (None if all_complete else "one_or_more_diagnostics_stopped_or_unavailable")})
    print({"result": str(result_path), "sha256": sha256_file(result_path),
           "terminal": terminal_state(RESULT_ROOT)})


if __name__ == "__main__":
    main()
