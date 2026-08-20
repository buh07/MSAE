#!/usr/bin/env python3
"""Strictly reparse and deterministically replay the promoted result from frozen leaves."""

from __future__ import annotations

import json
import math
import pickle
import time
from itertools import combinations
from pathlib import Path
from typing import Any

from msa_completion_common import (
    EVIDENCE_CLASS,
    ROOT,
    atomic_write_json,
    attest_completion_freeze_record,
    canonical_json_bytes,
    default_firewall,
    process_resource_accounting,
    normalized_recovery,
    read_json,
    require_bound_stage_files,
    require_frozen_completion_config,
    require_frozen_upstream_file,
    runtime_environment,
    seed_provenance,
    sha256_bytes,
    sha256_file,
    terminal_state,
    utc_now,
    verify_attestation_current,
    verify_completion_freeze,
    verify_parent_checkpoint,
    verify_parent_k2_functional,
    verify_parent_raw_calibration,
    write_failure_terminal,
    write_terminal,
)
from merge_msae_refit import PRIMARY, merge_g2, merge_raw, merge_stability
from calibrate_msae_completion import (candidate_selection_boundaries,
                                       numerical_rank,
                                       select_candidate)
from run_msae_refit_worker import TASKS, family_rows
from run_msae_specificity import (ASSIGNED, CE_FAMILIES,
                                  aggregate_ce_collateral, group_summary,
                                  punctuation_branch_invalid,
                                  registered_matched_random_seed,
                                  specificity_invariants_finite)
from run_msae_stability import stability_draw_finite
from render_msae_completion_decision import decide, decision_predicates


_FAILURE_ATTESTATION: dict[str, Any] = {}

REGISTERED_SIMPLE_CANDIDATE_MAPPINGS = {
    "projection_broad16": {
        "absolute_position": "broad_position",
        "relative_structural_position": "broad_position",
        "lexical_semantic_content": "broad_complement",
    },
    "projection_split8_8": {
        "absolute_position": "absolute_position",
        "relative_structural_position": "relative_structural_position",
        "lexical_semantic_content": "split_complement",
    },
    "pca16_complement": {
        "absolute_position": "pca16",
        "relative_structural_position": "pca16",
        "lexical_semantic_content": "pca_complement",
    },
}


def reject_json_constant(value: str) -> None:
    raise ValueError(f"non-standard JSON numeric constant: {value}")


def strict_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"), parse_constant=reject_json_constant)


def strict_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            raise ValueError(f"blank JSONL row at {path}:{line_number}")
        row = json.loads(line, parse_constant=reject_json_constant)
        if not isinstance(row, dict):
            raise TypeError(f"non-object JSONL row at {path}:{line_number}")
        require_recursive_finite(row, location=f"{path}:{line_number}")
        rows.append(row)
    return rows


def require_recursive_finite(value: Any, *, location: str = "$") -> None:
    """Allow JSON nulls but reject every non-finite numeric leaf."""

    if isinstance(value, bool) or value is None or isinstance(value, (str, int)):
        return
    if isinstance(value, float):
        if not math.isfinite(value):
            raise ValueError(f"non-finite JSON number at {location}")
        return
    if isinstance(value, list):
        for index, item in enumerate(value):
            require_recursive_finite(item, location=f"{location}[{index}]")
        return
    if isinstance(value, dict):
        for key, item in value.items():
            require_recursive_finite(item, location=f"{location}.{key}")
        return
    raise TypeError(f"non-JSON value at {location}: {type(value).__name__}")


def replay_normalized_recovery(component: Any, raw: Any, chance: Any) -> float | None:
    if component is None or raw is None or chance is None:
        return None
    return normalized_recovery(component, raw, chance)


def verify_baseline_semantics(
        result: dict[str, Any], bundle: dict[str, Any], config: dict[str, Any],
        tier1_calibration_sources: dict[str, set[str]],
        sentinel_calibration_sources: dict[str, set[str]],
        parent_raw_bundle: dict[str, Any]) -> None:
    import numpy as np
    from merge_msae_refit import threshold_boundary_diagnostic

    semantic_pairs = {
        "selected_simple_baseline": result["selected_simple_baseline"],
        "baseline_selection_failed": result["baseline_selection_failed"],
        "sentinel_alphas": result["sentinel_alphas"],
        "tier1_eligibility": result["tier1_eligibility"],
        "sentinel_eligibility": {
            task: row["eligibility"] for task, row in result["sentinels"].items()},
    }
    if any(bundle.get(key) != value for key, value in semantic_pairs.items()):
        raise RuntimeError("baseline JSON and pickle bundle semantic fields disagree")
    registered_candidates = set(REGISTERED_SIMPLE_CANDIDATE_MAPPINGS)
    if (set(result["candidates"]) != registered_candidates
            or result["selected_simple_baseline"] not in registered_candidates
            or set(result["sentinel_alphas"]["simple"])
                != registered_candidates):
        raise RuntimeError("baseline candidate inventory differs from preregistration")

    eligibility_rows = [
        *[(task, row, tier1_calibration_sources[task])
          for task, row in result["tier1_eligibility"].items()],
        *[(task, row["eligibility"], sentinel_calibration_sources[task])
          for task, row in result["sentinels"].items()],
    ]
    if int(config["draws"]) != 500:
        raise RuntimeError("frozen eligibility contract requires exactly 500 draw IDs")
    for task, row, expected_sources in eligibility_rows:
        draws = row["draws"]
        if len(draws) != int(config["draws"]):
            raise RuntimeError(
                f"baseline eligibility omits registered draw IDs: {task}")
        if row.get("sources", []) != sorted(expected_sources):
            raise RuntimeError(
                f"baseline eligibility source inventory mismatch: {task}")
        finite = np.asarray([value for value in draws
                             if value is not None and math.isfinite(value)], dtype=float)
        se = float(np.std(finite, ddof=1)) if len(finite) >= 2 else None
        lcb = float(np.quantile(finite, 0.025)) if len(finite) >= 2 else None
        threshold = (None if se is None else
                     max(float(config["eligibility_floor"]), 2 * se))
        margin = None if lcb is None or threshold is None else lcb - threshold
        block_margins: list[float] = []
        for block in range(5):
            retained = np.asarray([
                value for draw_id, value in enumerate(draws)
                if not block * 100 <= draw_id < (block + 1) * 100
                and value is not None and math.isfinite(value)], dtype=float)
            if len(retained) < 350:
                block_margins = []
                break
            rse = float(np.std(retained, ddof=1))
            rlcb = float(np.quantile(retained, 0.025))
            block_margins.append(
                rlcb - max(float(config["eligibility_floor"]), 2 * rse))
        endpoint_range = (float(np.ptp(block_margins))
                          if len(block_margins) == 5 else None)
        boundary = threshold_boundary_diagnostic(
            margin, 0.0, tolerance=float(config["boundary_tolerance"]),
            mc_endpoint_range=endpoint_range,
            mc_not_applicable_reason=(
                None if endpoint_range is not None
                else "fewer than 350 finite registered IDs in a delete-100 block"))
        eligible = bool(
            len(finite) >= int(config["minimum_complete_draws"])
            and margin is not None and margin > 0.0
            and not boundary["boundary_proximity"])
        expected = {
            "finite_draws": len(finite), "se_ddof1": se, "lcb_2p5": lcb,
            "threshold": threshold, "eligibility_margin": margin,
            "boundary_diagnostic": boundary, "eligible": eligible,
            "requested_draws": int(config["draws"]),
            "point_raw_minus_chance": (
                float(np.mean(finite)) if len(finite) else None),
            "nonfinite_draws": [i for i, value in enumerate(draws)
                                if value is None or not math.isfinite(value)],
        }
        if any(row.get(key) != value for key, value in expected.items()):
            raise RuntimeError("baseline eligibility summary differs from serialized draws")

    for candidate, row in result["candidates"].items():
        if row.get("tier1_mapping") != REGISTERED_SIMPLE_CANDIDATE_MAPPINGS[
                candidate]:
            raise RuntimeError(
                f"baseline candidate mapping differs from preregistration: {candidate}")
        basis_name = {
            "projection_broad16": "broad_position",
            "projection_split8_8": "split_position_joint",
            "pca16_complement": "pca16",
        }[candidate]
        basis = np.asarray(parent_raw_bundle["bases"][basis_name], dtype=np.float32)
        complement = (np.eye(basis.shape[0], dtype=np.float32)
                      - basis @ basis.T)
        positional_rank, positional_tolerance = numerical_rank(basis)
        complement_rank, complement_tolerance = numerical_rank(complement)
        expected_rank = {
            "positional": positional_rank,
            "complement": complement_rank,
            "positional_tolerance": positional_tolerance,
            "complement_tolerance": complement_tolerance,
        }
        if (expected_rank["positional"] != 16
                or expected_rank["complement"] != 752
                or row.get("fitted_rank") != expected_rank
                or row.get("fitted_rank_total") != 768
                or row["fitted_rank_total"]
                    != positional_rank + complement_rank):
            raise RuntimeError(
                f"baseline fitted operator rank differs from frozen basis: {candidate}")
        for task, collateral in row["collateral"].items():
            expected_degradation = (
                None if (collateral["raw_macro_f1"] is None
                         or collateral["component_macro_f1"] is None)
                else float(collateral["raw_macro_f1"]
                           - collateral["component_macro_f1"]))
            if collateral["degradation"] != expected_degradation:
                raise RuntimeError("baseline sentinel degradation formula disagrees")
        recoveries = row["tier1_recoveries"]
        detail = row["tier1_exact_source_detail"]
        expected_detail = {f"{rep}:{task}" for rep, tasks in recoveries.items()
                           for task in tasks}
        if set(detail) != expected_detail:
            raise RuntimeError("baseline Tier-1 source primitive inventory mismatch")
        for rep, tasks in recoveries.items():
            for task, recovery in tasks.items():
                source_row = detail[f"{rep}:{task}"]
                source_values = []
                for leaf in source_row.get("by_source", {}).values():
                    expected_source = replay_normalized_recovery(
                        leaf["component"], leaf["raw"], leaf["chance"])
                    if leaf["recovery"] != expected_source:
                        raise RuntimeError("baseline source recovery formula disagrees")
                    source_values.append(leaf["recovery"])
                expected_recovery = (
                    None if ("invalid_fit" in source_row
                             or "invalid_source" in source_row
                             or "invalid_sources" in source_row)
                    else (float(np.mean(source_values))
                          if source_values and all(value is not None
                                                   for value in source_values)
                          else None))
                if recovery != expected_recovery:
                    raise RuntimeError("baseline recovery differs from source leaves")
                if list(source_row.get("by_source", {})) != sorted(
                        tier1_calibration_sources[task]):
                    raise RuntimeError(
                        "baseline Tier-1 source set differs from frozen calibration rows")
        eligible_tasks = {task for task, eligibility in result[
            "tier1_eligibility"].items() if eligibility["eligible"]}
        rebuilt_families = family_rows(
            recoveries, row["tier1_mapping"], eligible_tasks)
        rebuilt_retention = {
            family: rebuilt_families[family]["assigned_recovery"]
            for family in PRIMARY}
        rebuilt_macro = (
            float(np.mean([rebuilt_families[family]["selectivity_margin"]
                           for family in PRIMARY]))
            if all(rebuilt_families[family]["selectivity_margin"] is not None
                   for family in PRIMARY) else None)
        if (rebuilt_families != row["tier1_exact_families"]
                or rebuilt_retention != row["tier1_family_assigned_recovery"]
                or rebuilt_macro != row["tier1_macro_selectivity"]):
            raise RuntimeError("baseline Tier-1 family aggregation disagrees")
        boundaries = candidate_selection_boundaries(
            row["tier1_family_assigned_recovery"], row["collateral"], config)
        if boundaries != row["selection_boundary_diagnostics"]:
            raise RuntimeError("baseline candidate boundary diagnostics disagree")
        tier1_ok = bool(
            row["tier1_macro_selectivity"] is not None
            and math.isfinite(row["tier1_macro_selectivity"])
            and all(
                sum(bool(result["tier1_eligibility"][task]["eligible"])
                    for task in tasks) >= int(config["minimum_family_tasks"])
                and row["tier1_family_assigned_recovery"][family] is not None
                and row["tier1_family_assigned_recovery"][family] >= 0.65
                and not boundaries["tier1_family_assigned_recovery"][family][
                    "boundary_proximity"]
                for family, tasks in PRIMARY.items()))
        sentinels_ok = all(result["sentinels"][task]["eligibility"]["eligible"]
                           for task in config["sentinels"])
        collateral_ok = all(
            row["collateral"][task]["degradation"] is not None
            and row["collateral"][task]["degradation"]
                <= float(config["sentinel_max_degradation"])
            and not boundaries["tier2_sentinel_degradation"][task][
                "boundary_proximity"]
            for task in config["sentinels"])
        roundtrip_ok = (row["roundtrip_max_relative_error"]
                        <= float(config["roundtrip_tolerance"]))
        gates = {
            "tier1_retention_pass": tier1_ok,
            "all_nine_sentinels_eligible": sentinels_ok,
            "tier2_collateral_pass": collateral_ok,
            "roundtrip_pass": roundtrip_ok,
            "selection_pass": tier1_ok and sentinels_ok and collateral_ok
                              and roundtrip_ok,
        }
        if any(row.get(key) != value for key, value in gates.items()):
            raise RuntimeError(f"baseline candidate gate differs: {candidate}")
    selected, failed, trace = select_candidate(result["candidates"])
    if (selected != result["selected_simple_baseline"]
            or failed != result["baseline_selection_failed"]
            or trace != result["selection_trace"]):
        raise RuntimeError("baseline selection replay disagrees")


def verify_refit_leaf_summaries(
        payload: dict[str, Any], baseline: dict[str, Any],
        expected_sources: dict[str, dict[str, set[str]]], *,
        expected_kind: str, expected_layer: int,
        expected_job: str | None,
        paired_raw_payload: dict[str, Any] | None = None) -> None:
    import numpy as np

    expected_arguments = {
        "kind": expected_kind, "layer": expected_layer,
        "job": expected_job,
    }
    if (payload.get("kind") != expected_kind
            or payload.get("layer") != expected_layer
            or payload.get("job") != expected_job
            or any(payload.get("resolved_arguments", {}).get(key) != value
                   for key, value in expected_arguments.items())):
        raise RuntimeError("refit leaf identity differs from its frozen stage path")
    result = payload["result"]
    eligible = {task for task, row in baseline["tier1_eligibility"].items()
                if row["eligible"]}
    if payload["kind"] == "raw":
        expected_mappings = {
            "split": {"absolute_position": "absolute_position",
                      "relative_structural_position": "relative_structural_position",
                      "lexical_semantic_content": "split_complement"},
            "broad": {"absolute_position": "broad_position",
                      "relative_structural_position": "broad_position",
                      "lexical_semantic_content": "broad_complement"},
        }
        if result["mappings"] != expected_mappings or any(
                set(tasks) != set(TASKS) for tasks in result["recoveries"].values()):
            raise RuntimeError("raw recovery/mapping inventory mismatch")
        expected_raw_detail = {f"{rep}:{task}" for rep, tasks in result[
            "recoveries"].items() for task in tasks}
        if set(result["source_detail"]) != expected_raw_detail:
            raise RuntimeError("raw per-source primitive inventory mismatch")
        for rep, tasks in result["recoveries"].items():
            for task, recovery in tasks.items():
                source_row = result["source_detail"][f"{rep}:{task}"]
                if list(source_row.get("by_source", {})) != sorted(
                        expected_sources["C1"][task]):
                    raise RuntimeError("raw source set differs from frozen C1 rows")
                for source_leaf in source_row.get("by_source", {}).values():
                    expected_source = replay_normalized_recovery(
                        source_leaf["component"], source_leaf["raw"],
                        source_leaf["chance"])
                    if source_leaf["recovery"] != expected_source:
                        raise RuntimeError("raw source recovery formula disagrees")
                leaves = [row["recovery"]
                          for row in source_row.get("by_source", {}).values()]
                expected_recovery = (
                    None if ("invalid_fit" in source_row
                             or "invalid_source" in source_row
                             or "invalid_sources" in source_row)
                    else (float(np.mean(leaves))
                          if leaves and all(value is not None for value in leaves)
                          else None))
                if recovery != expected_recovery:
                    raise RuntimeError(
                        "raw recovery differs from serialized per-source leaves")
        rebuilt = {
            name: family_rows(result["recoveries"], mapping, eligible)
            for name, mapping in result["mappings"].items()
        }
        if rebuilt != result["raw_g1"]:
            raise RuntimeError("raw refit family summary differs from serialized recoveries")
        required_raw = [result["recoveries"][rep][task]
                        for rep in result["recoveries"] for task in eligible]
        expected_finite = bool(
            required_raw
            and all(value is not None and math.isfinite(float(value))
                    for value in required_raw)
            and all(row["passes"] for row in result["simple_roundtrip"].values()))
        if "simple_c2" in result:
            simple = result["simple_c2"]
            candidate = simple["candidate"]
            if candidate != baseline["selected_simple_baseline"]:
                raise RuntimeError(
                    "raw simple C2 candidate differs from selected baseline")
            if candidate == "projection_broad16":
                expected_simple_mapping = expected_mappings["broad"]
            elif candidate == "projection_split8_8":
                expected_simple_mapping = expected_mappings["split"]
            elif candidate == "pca16_complement":
                expected_simple_mapping = {
                    family: ("pca_complement" if family == "lexical_semantic_content"
                             else "pca16") for family in PRIMARY}
            else:
                raise RuntimeError("unknown simple candidate in raw leaf")
            if (simple["mapping"] != expected_simple_mapping
                    or any(set(tasks) != set(TASKS)
                           for tasks in simple["recoveries"].values())
                    or set(simple["sentinels"]) != set(baseline["sentinel_alphas"]["raw"])):
                raise RuntimeError("simple C2 primitive inventory mismatch")
            for sentinel in simple["sentinels"].values():
                expected_damage = (
                    None if (sentinel["raw"] is None
                             or sentinel["component"] is None
                             or sentinel["chance"] is None
                             or sentinel["raw"] <= sentinel["chance"])
                    else ((sentinel["raw"] - sentinel["component"])
                          / (sentinel["raw"] - sentinel["chance"])))
                if sentinel["normalized_damage"] != expected_damage:
                    raise RuntimeError("simple sentinel damage formula disagrees")
            for rep, tasks in simple["recoveries"].items():
                for task, recovery in tasks.items():
                    source_row = simple["source_detail"][f"{rep}:{task}"]
                    if list(source_row.get("by_source", {})) != sorted(
                            expected_sources["C2"][task]):
                        raise RuntimeError(
                            "simple source set differs from frozen C2 rows")
                    for source_leaf in source_row.get("by_source", {}).values():
                        expected_source = replay_normalized_recovery(
                            source_leaf["component"], source_leaf["raw"],
                            source_leaf["chance"])
                        if source_leaf["recovery"] != expected_source:
                            raise RuntimeError("simple source recovery formula disagrees")
                    leaves = [row["recovery"]
                              for row in source_row.get("by_source", {}).values()]
                    expected_recovery = (
                        None if ("invalid_fit" in source_row
                                 or "invalid_source" in source_row
                                 or "invalid_sources" in source_row)
                        else (float(np.mean(leaves))
                              if leaves and all(value is not None for value in leaves)
                              else None))
                    if recovery != expected_recovery:
                        raise RuntimeError(
                            "simple C2 recovery differs from serialized per-source leaves")
            expected = family_rows(simple["recoveries"], simple["mapping"], eligible)
            if expected != simple["families"]:
                raise RuntimeError(
                    "simple C2 family summary differs from serialized recoveries")
            expected_detail = {
                f"{rep}:{task}" for rep in simple["recoveries"]
                for task in result["recoveries"][next(iter(result["recoveries"]))]
            }
            if set(simple["source_detail"]) != expected_detail:
                raise RuntimeError("simple C2 source-detail primitive inventory mismatch")
            if set(simple.get("raw_tier1", {})) != set(TASKS):
                raise RuntimeError("simple raw Tier-1 task inventory mismatch")
            first_rep = sorted(simple["recoveries"])[0]
            for task in TASKS:
                authoritative_raw = simple["raw_tier1"][task]
                if authoritative_raw != simple["source_detail"][
                        f"{first_rep}:{task}"]:
                    raise RuntimeError(
                        "simple raw Tier-1 leaf is not the registered first-rep leaf")
                expected_source_order = sorted(expected_sources["C2"][task])
                if list(authoritative_raw.get("by_source", {})) != expected_source_order:
                    raise RuntimeError("simple raw Tier-1 source inventory mismatch")
                for rep in simple["recoveries"]:
                    rep_sources = simple["source_detail"][f"{rep}:{task}"][
                        "by_source"]
                    for source in expected_source_order:
                        if (rep_sources[source]["raw"]
                                != authoritative_raw["by_source"][source]["raw"]
                                or rep_sources[source]["chance"]
                                != authoritative_raw["by_source"][source]["chance"]):
                            raise RuntimeError(
                                "simple raw/chance denominator differs across reps")
            required_simple = [simple["recoveries"][rep][task]
                               for rep in simple["recoveries"] for task in eligible]
            required_damage = [row["normalized_damage"]
                               for row in simple["sentinels"].values()]
            expected_finite = bool(
                expected_finite and required_simple and required_damage
                and all(value is not None and math.isfinite(float(value))
                        for value in [*required_simple, *required_damage]))
        if result.get("finite") is not expected_finite:
            raise RuntimeError("raw refit finite flag differs from primitive leaves")
    elif payload["kind"] == "k2":
        if paired_raw_payload is None:
            raise RuntimeError("K2 leaf lacks paired L3 raw artifact")
        paired_raw = paired_raw_payload["result"]["simple_c2"]
        if (set(result["recoveries"]) != {"pos", "content"}
                or any(set(tasks) != set(TASKS)
                       for tasks in result["recoveries"].values())
                or set(result["sentinels"]) != set(baseline["sentinel_alphas"]["raw"])):
            raise RuntimeError("K2 primitive inventory mismatch")
        for sentinel in result["sentinels"].values():
            expected_damage = (
                None if (sentinel["raw"] is None
                         or sentinel["component"] is None
                         or sentinel["chance"] is None
                         or sentinel["raw"] <= sentinel["chance"])
                else ((sentinel["raw"] - sentinel["component"])
                      / (sentinel["raw"] - sentinel["chance"])))
            if sentinel["normalized_damage"] != expected_damage:
                raise RuntimeError("K2 sentinel damage formula disagrees")
        expected_k2_detail = {f"{rep}:{task}" for rep, tasks in result[
            "recoveries"].items() for task in tasks}
        if set(result["source_detail"]) != expected_k2_detail:
            raise RuntimeError("K2 per-source primitive inventory mismatch")
        for rep, tasks in result["recoveries"].items():
            for task, recovery in tasks.items():
                source_detail = result["source_detail"][f"{rep}:{task}"]
                if list(source_detail) != sorted(expected_sources["C2"][task]):
                    raise RuntimeError("K2 source set differs from frozen C2 rows")
                leaves = [row["recovery"] for row in source_detail.values()]
                for source_leaf in source_detail.values():
                    raw_leaf = source_leaf["raw"]
                    expected_source = replay_normalized_recovery(
                        source_leaf["component"],
                        None if raw_leaf is None else raw_leaf["raw"],
                        None if raw_leaf is None else raw_leaf["chance"])
                    if source_leaf["recovery"] != expected_source:
                        raise RuntimeError("K2 source recovery formula disagrees")
                for source, source_leaf in source_detail.items():
                    if source_leaf["raw"] != paired_raw["raw_tier1"][task][
                            "by_source"][source]:
                        raise RuntimeError(
                            "K2 normalization leaf differs from paired raw artifact")
                expected_recovery = (
                    float(np.mean(leaves))
                    if leaves and all(value is not None for value in leaves)
                    else None)
                if recovery != expected_recovery:
                    raise RuntimeError(
                        "K2 recovery differs from serialized per-source leaves")
        mapping = {family: ("content" if family == "lexical_semantic_content"
                            else "pos") for family in PRIMARY}
        expected = family_rows(result["recoveries"], mapping, eligible)
        if expected != result["families"]:
            raise RuntimeError("K2 family summary differs from serialized recoveries")
        for task, sentinel in result["sentinels"].items():
            paired_sentinel = paired_raw["sentinels"][task]
            if (sentinel["raw"] != paired_sentinel["raw"]
                    or sentinel["chance"] != paired_sentinel["chance"]):
                raise RuntimeError(
                    "K2 sentinel denominator differs from paired raw artifact")
        required_recovery = [result["recoveries"][rep][task]
                             for rep in result["recoveries"] for task in eligible]
        required_damage = [row["normalized_damage"]
                           for row in result["sentinels"].values()]
        expected_finite = bool(
            required_recovery and required_damage
            and all(value is not None and math.isfinite(float(value))
                    for value in [*required_recovery, *required_damage]))
        if result.get("finite") is not expected_finite:
            raise RuntimeError("K2 refit finite flag differs from primitive leaves")
    else:
        raise RuntimeError(f"unknown refit leaf kind: {payload.get('kind')}")


def verify_stability_leaf_summaries(payload: dict[str, Any],
                                    config: dict[str, Any],
                                    baseline: dict[str, Any]) -> None:
    import numpy as np

    tasks = payload["tasks"]
    primary = config["primary_checkpoints"]
    descriptive = config["descriptive_checkpoints"][0]
    expected_tasks = {task for task, row in baseline["tier1_eligibility"].items()
                      if row["eligible"]}
    if set(tasks) != expected_tasks:
        raise RuntimeError("stability task inventory differs from frozen eligibility")
    expected_pair_keys = {
        *[f"{left}__{right}" for left, right in combinations(primary, 2)],
        f"{primary[0]}__{descriptive}",
    }
    expected_family_by_task = {
        task: family for family, family_tasks in PRIMARY.items()
        for task in family_tasks}
    for task, row in tasks.items():
        if (row["family"] != expected_family_by_task[task]
                or set(row["k2_pairs"]) != expected_pair_keys
                or "simple_A_B" not in row):
            raise RuntimeError("stability task primitive inventory mismatch")
    rebuilt: dict[str, Any] = {}
    for family, family_tasks in PRIMARY.items():
        usable = [tasks[task] for task in family_tasks if task in tasks]
        family_eligible = len(usable) >= int(config["minimum_family_tasks"])
        pair_means = {
            f"{left}__{right}": (
                float(np.mean([row["k2_pairs"][f"{left}__{right}"]
                               for row in usable]))
                if family_eligible and all(
                    row["k2_pairs"][f"{left}__{right}"] is not None
                    for row in usable) else None)
            for left, right in combinations(primary, 2)
        }
        learned = (float(np.mean(list(pair_means.values())))
                   if pair_means and all(value is not None
                                         for value in pair_means.values()) else None)
        simple = (float(np.mean([row["simple_A_B"] for row in usable]))
                  if family_eligible and all(row["simple_A_B"] is not None
                                             for row in usable) else None)
        g7_key = f"{primary[0]}__{descriptive}"
        g7 = (float(np.mean([row["k2_pairs"][g7_key] for row in usable]))
              if family_eligible and all(row["k2_pairs"][g7_key] is not None
                                         for row in usable) else None)
        rebuilt[family] = {
            "learned_mean_pairwise_cka": learned,
            "learned_stability_loss": None if learned is None else 1.0 - learned,
            "simple_A_B_cka_descriptive": simple,
            "g4_g7_regularizer_sensitivity_cka_descriptive": g7,
            "pair_means": pair_means,
        }
    if rebuilt != payload["families"]:
        raise RuntimeError("stability family summary differs from serialized task leaves")
    expected_finite = stability_draw_finite(tasks, rebuilt)
    if payload.get("finite") is not expected_finite:
        raise RuntimeError("stability finite flag differs from primitive leaves")


def verify_specificity_leaf_summaries(
        payload: dict[str, Any], config: dict[str, Any],
        token_map: dict[str, dict[str, Any]],
        transforms: list[dict[str, Any]], *, expected_job: str,
        expected_checkpoint_sha256: str,
        expected_parent_functional_sha256: str,
        expected_parent_counterfactual_rows: list[dict[str, Any]],
        expected_parent_ce_rows: list[dict[str, Any]],
        expected_simple_candidate: str) -> None:
    import numpy as np

    rows = payload["rows"]
    job = payload["job_id"]
    if (job != expected_job
            or payload.get("resolved_arguments", {}).get("job") != expected_job
            or payload.get("checkpoint_sha256") != expected_checkpoint_sha256
            or payload.get("parent_functional_sha256")
                != expected_parent_functional_sha256):
        raise RuntimeError(
            "specificity checkpoint identity/provenance differs from stage path")
    expected_transform_metadata = [
        (row["transform_id"], row["family"], row["template_group"],
         row.get("token_aligned"))
        for row in transforms
    ]
    observed_transform_metadata = [
        (row.get("transform_id"), row.get("family"), row.get("template_group"),
         row.get("token_aligned_parent"))
        for row in rows
    ]
    if (len(transforms) != 128
            or len({row["transform_id"] for row in transforms}) != 128
            or observed_transform_metadata != expected_transform_metadata):
        raise RuntimeError(
            "specificity transform inventory/metadata differs from frozen C2 rows")
    parent_counterfactual = {
        row["transform_id"]: row
        for row in expected_parent_counterfactual_rows
    }
    if ([row["transform_id"] for row in expected_parent_counterfactual_rows]
            != [row["transform_id"] for row in transforms]
            or len(parent_counterfactual) != 128):
        raise RuntimeError(
            "parent counterfactual inventory differs from frozen transforms")
    for row in rows:
        actual, random, sham = row["actual"], row["random"], row["sham"]
        qa = row["random_qa"]
        parent_row = parent_counterfactual[row["transform_id"]]
        parent_distances = parent_row["distances"]
        if (set(actual) != set(parent_distances)
                or parent_row.get("family") != row["family"]
                or parent_row.get("token_aligned")
                    != row["token_aligned_parent"]):
            raise RuntimeError(
                "specificity actual/parent distance schema or metadata differs")
        expected_parent_error = max(
            abs(float(actual[rep]) - float(parent_distances[rep]))
            for rep in parent_distances)
        if row["parent_actual_max_abs_error"] != expected_parent_error:
            raise RuntimeError(
                "specificity parent actual error differs from authoritative row")
        if row["matched_random_seed"] != registered_matched_random_seed(
                int(config["seed"]), row["transform_id"]):
            raise RuntimeError("specificity sentence seed binding disagrees")
        direction = row.get("random_direction_sha256")
        if random is not None and (not isinstance(direction, str) or len(direction) != 64
                                   or any(char not in "0123456789abcdef"
                                          for char in direction)):
            raise RuntimeError("specificity sentence direction digest is malformed")
        random_error = (None if random is None else
                        abs(float(random["raw"]) - float(actual["raw"])))
        if random_error != row["computed_random_raw_distance_error"]:
            raise RuntimeError("specificity random raw-distance error disagrees")
        expected_valid = bool(
            random is not None
            and specificity_invariants_finite(
                actual, random, sham, qa,
                scalars=[row["parent_actual_max_abs_error"], random_error])
            and actual["raw"] >= float(config["specificity_raw_distance_floor"])
            and row["parent_actual_max_abs_error"] <= 1e-6
            and random_error <= float(config["orthogonality_tolerance"])
            and qa["distance_error"] <= float(config["orthogonality_tolerance"])
            and qa["absolute_cosine_actual_delta"]
                <= float(config["orthogonality_tolerance"])
            and qa["absolute_cosine_source"]
                <= float(config["orthogonality_tolerance"])
            and max(sham[rep] for rep in ["raw", "pos", "content"])
                <= float(config["sham_distance_ceiling"]))
        sentence = row["sentence"]
        if sentence["valid"] is not expected_valid:
            raise RuntimeError("specificity sentence validity disagrees with primitives")
        if expected_valid:
            for branch in ["pos", "content"]:
                expected_actual = actual[branch] / actual["raw"]
                expected_random = random[branch] / actual["raw"]
                expected_sham = sham[branch] / actual["raw"]
                expected_specificity = expected_actual - max(
                    expected_random, expected_sham)
                observed_values = [sentence["actual_normalized"][branch],
                                   sentence["random_normalized"][branch],
                                   sentence["sham_normalized"][branch],
                                   sentence["specificity"][branch]]
                expected_values = [expected_actual, expected_random,
                                   expected_sham, expected_specificity]
                if not np.allclose(observed_values, expected_values,
                                   rtol=0.0, atol=1e-15):
                    raise RuntimeError(
                        "specificity sentence normalization/formula disagrees")
        token = row["token_aligned"]
        token_spec = token_map.get(row["transform_id"])
        if token_spec is not None:
            token_rows = token.get("tokens", [])
            expected_indices = token_spec["designated_token_positions"]
            if [item["token_index"] for item in token_rows] != expected_indices:
                raise RuntimeError("token specificity index/count inventory mismatch")
            replay_validity: list[bool] = []
            for token_row in token_rows:
                expected_seed = registered_matched_random_seed(
                    int(config["seed"]), row["transform_id"],
                    int(token_row["token_index"]))
                if token_row["matched_random_token_seed"] != expected_seed:
                    raise RuntimeError("token specificity seed binding disagrees")
                if not all(key in token_row for key in [
                        "actual", "random", "sham", "qa", "normalized",
                        "specificity", "computed_random_raw_distance_error"]):
                    if token_row.get("valid") is not False or not token_row.get("reason"):
                        raise RuntimeError("token exception leaf is unexplained")
                    replay_validity.append(False)
                    continue
                random_error = abs(
                    token_row["random"]["raw"] - token_row["actual"]["raw"])
                expected_token_valid = bool(
                    specificity_invariants_finite(
                        token_row["actual"], token_row["random"],
                        token_row["sham"], token_row["qa"],
                        scalars=[random_error])
                    and token_row["actual"]["raw"]
                        >= float(config["specificity_raw_distance_floor"])
                    and random_error <= float(config["orthogonality_tolerance"])
                    and token_row["qa"]["distance_error"]
                        <= float(config["orthogonality_tolerance"])
                    and token_row["qa"]["absolute_cosine_actual_delta"]
                        <= float(config["orthogonality_tolerance"])
                    and token_row["qa"]["absolute_cosine_source"]
                        <= float(config["orthogonality_tolerance"])
                    and max(token_row["sham"].values())
                        <= float(config["sham_distance_ceiling"]))
                if (token_row.get("valid") is not expected_token_valid
                        or token_row["computed_random_raw_distance_error"] != random_error):
                    raise RuntimeError("token row validity differs from frozen invariants")
                replay_validity.append(expected_token_valid)
                direction = token_row.get("direction_sha256")
                if (not isinstance(direction, str) or len(direction) != 64
                        or any(char not in "0123456789abcdef" for char in direction)):
                    raise RuntimeError("token direction digest is malformed")
                denominator = token_row["actual"]["raw"]
                for branch in ["pos", "content"]:
                    expected_normalized = {
                        kind: token_row[kind][branch] / denominator
                        for kind in ["actual", "random", "sham"]}
                    observed_normalized = {
                        kind: token_row["normalized"][kind][branch]
                        for kind in ["actual", "random", "sham"]}
                    if not np.allclose(
                            list(observed_normalized.values()),
                            list(expected_normalized.values()),
                            rtol=0.0, atol=1e-15):
                        raise RuntimeError("token specificity normalization disagrees")
                    expected_specificity = expected_normalized["actual"] - max(
                        expected_normalized["random"], expected_normalized["sham"])
                    if not math.isclose(token_row["specificity"][branch],
                                        expected_specificity, rel_tol=0.0,
                                        abs_tol=1e-15):
                        raise RuntimeError("token specificity formula disagrees")
            expected_valid = bool(len(replay_validity) == len(expected_indices)
                                  and all(replay_validity))
            if token.get("valid") is not expected_valid:
                raise RuntimeError("token aggregate validity differs from token leaves")
            if expected_valid:
                expected_actual_means = {
                    branch: float(np.mean([
                        item["normalized"]["actual"][branch] for item in token_rows]))
                    for branch in ["pos", "content"]}
                expected_specificity_means = {
                    branch: float(np.mean([
                        item["specificity"][branch] for item in token_rows]))
                    for branch in ["pos", "content"]}
                if (token.get("n_tokens") != len(expected_indices)
                        or token["actual_normalized"] != expected_actual_means
                        or token["specificity"] != expected_specificity_means):
                    raise RuntimeError("token aggregate differs from token leaves")
            else:
                invalid_indices = [item["token_index"] for item, valid
                                   in zip(token_rows, replay_validity, strict=True)
                                   if not valid]
                if (token.get("reason") != "one_or_more_token_controls_invalid"
                        or token.get("evaluated_tokens") != len(expected_indices)
                        or token.get("valid_tokens") != sum(replay_validity)
                        or token.get("required_tokens") != len(expected_indices)
                        or token.get("invalid_token_indices") != invalid_indices):
                    raise RuntimeError("invalid token aggregate bookkeeping disagrees")
        else:
            if token.get("reason") != "not_frozen_token_aligned":
                raise RuntimeError("non-token transform has unexpected token status")
    if payload["max_parent_actual_abs_error"] != max(
            row["parent_actual_max_abs_error"] for row in rows):
        raise RuntimeError("specificity maximum parent error disagrees with rows")
    rebuilt: dict[str, Any] = {}
    for family in sorted({row["family"] for row in rows}):
        if family == "punctuation_format":
            rebuilt[family] = {
                branch: group_summary(rows, family, branch, config, job)
                for branch in ["pos", "content"]}
        else:
            branch = ASSIGNED[family]
            rebuilt[family] = {
                "sentence": group_summary(rows, family, branch, config, job),
                "assigned_branch": branch,
            }
            if family == "lexical_entity_substitution":
                rebuilt[family]["token_aligned"] = group_summary(
                    rows, family, branch, config, job, token=True)
    if rebuilt != payload["summaries"]:
        raise RuntimeError("specificity summaries differ from serialized control rows")

    required = ["position_shift", "structural_active_passive",
                "lexical_entity_substitution"]
    mapping_valid = all(rebuilt[family]["sentence"]["passes"]
                        for family in required)
    lexical_valid = rebuilt["lexical_entity_substitution"]["token_aligned"]["passes"]
    punctuation_invalid = any(
        punctuation_branch_invalid(
            rebuilt["punctuation_format"][branch],
            float(config["specificity_margin"]))
        for branch in ["pos", "content"])
    punctuation_technical = all(
        rebuilt["punctuation_format"][branch]["valid"]
        and not rebuilt["punctuation_format"][branch]["boundary_diagnostic"][
            "boundary_proximity"]
        and all(
            not diagnostic["boundary_proximity"]
            for diagnostics in rebuilt["punctuation_format"][branch][
                "group_boundary_diagnostics"].values()
            for diagnostic in diagnostics.values())
        for branch in ["pos", "content"])
    gate = bool(payload["max_parent_actual_abs_error"] <= 1e-6
                and mapping_valid and lexical_valid and punctuation_technical
                and not punctuation_invalid)
    reasons = {
        "sentence_mapping_valid": mapping_valid,
        "lexical_token_valid": lexical_valid,
        "punctuation_sentinel_valid": not punctuation_invalid,
        "punctuation_technical_valid": punctuation_technical,
    }
    if gate != payload["counterfactual_gate_valid"] or reasons != payload[
            "counterfactual_gate_reasons"]:
        raise RuntimeError("specificity gate differs from serialized control rows")

    ce = payload["ce_collateral"]
    groups = ce["groups"]
    ce_rows = ce.get("transform_side_rows")
    if ce_rows != expected_parent_ce_rows:
        raise RuntimeError(
            "CE transform/side primitives differ from frozen parent functional rows")
    replay_point, replay_groups, replay_families = aggregate_ce_collateral(
        ce_rows, transforms)
    ce_transforms = [row for row in transforms if row["family"] in CE_FAMILIES]
    expected_ce_groups: dict[str, int] = {}
    for transform in ce_transforms:
        key = f"{transform['family']}::{transform['template_group']}"
        expected_ce_groups[key] = expected_ce_groups.get(key, 0) + 1
    if (len(ce_transforms) != 96
            or set(groups) != set(expected_ce_groups)
            or set(expected_ce_groups.values()) != {8}
            or any(len(groups[key]) != expected_ce_groups[key]
                   for key in expected_ce_groups)):
        raise RuntimeError("CE collateral transform/group inventory mismatch")
    if (replay_point != ce["point"] or replay_groups != groups
            or replay_families != ce["families"]):
        raise RuntimeError(
            "CE side-to-transform-to-group aggregation differs from primitives")
    families = replay_families
    point = replay_point
    draws: list[float] = []
    from msa_completion_common import deterministic_seed

    for draw in range(int(config["draws"])):
        rng = np.random.Generator(np.random.PCG64(
            deterministic_seed(config["seed"], "ce_collateral", draw, 0)))
        family_values = []
        for family in sorted(families):
            keys = sorted(key for key in groups if key.startswith(family + "::"))
            sampled = rng.choice(keys, size=len(keys), replace=True)
            family_values.append(float(np.mean(
                [np.mean(groups[key]) for key in sampled])))
        draws.append(float(np.mean(family_values)))
    if (point != ce["point"] or families != ce["families"]
            or draws != ce["draws"]):
        raise RuntimeError("CE collateral summary differs from serialized group leaves")
    identity = payload["simple_identity_collateral"]
    if identity.get("candidate") != expected_simple_candidate:
        raise RuntimeError(
            "simple identity collateral is not bound to selected baseline")
    identity_rows = identity["rows"]
    parent_ce = {
        (row["transform_id"], row["side"]): float(row["ce"]["raw"])
        for row in expected_parent_ce_rows
    }
    expected_identity_inventory = [
        (row["transform_id"], side)
        for row in transforms if "source_words" in row
        for side in ["source_words", "target_words"]
    ]
    if ([(row.get("transform_id"), row.get("side"))
         for row in identity_rows] != expected_identity_inventory):
        raise RuntimeError("simple identity CE transform/side inventory mismatch")
    max_parent = max(row["parent_raw_abs_error"] for row in identity_rows)
    max_identity = max(row["identity_abs_error"] for row in identity_rows)
    for row in identity_rows:
        if row["parent_raw_ce"] != parent_ce[(row["transform_id"], row["side"])]:
            raise RuntimeError(
                "identity collateral parent raw CE differs from authoritative row")
        if not math.isclose(row["parent_raw_abs_error"],
                            abs(row["raw_ce"] - row["parent_raw_ce"]),
                            rel_tol=0.0, abs_tol=1e-15):
            raise RuntimeError("parent CE error differs from leaves")
        if not math.isclose(row["identity_abs_error"],
                            abs(row["identity_ce"] - row["raw_ce"]),
                            rel_tol=0.0, abs_tol=1e-15):
            raise RuntimeError("identity CE error differs from leaves")
    expected_identity_valid = bool(
        len(identity_rows) == 192 and max_parent <= 1e-5
        and max_identity <= 1e-5)
    if (identity["max_parent_raw_ce_abs_error"] != max_parent
            or identity["max_identity_ce_abs_error"] != max_identity
            or identity["valid"] is not expected_identity_valid):
        raise RuntimeError("simple identity collateral summary disagrees")


def complete_joint_evaluations(raw: dict[str, Any], g2: dict[str, Any],
                               config: dict[str, Any]) -> None:
    """Repeat the cross-subtree gates separately from the merge entry point."""

    negative = raw["G1a_postscore_amended"]["supported_negative_diagnostic"]
    negative["learned_new_family_advantage"] = g2["learned_new_family_advantage"]
    negative["no_learned_new_family_advantage_valid"] = bool(
        g2["learned_new_family_advantage_inference_valid"]
        and g2["learned_new_family_advantage"] is False)
    negative["supported_negative_all_gates"] = bool(
        negative["raw_negative_requirements_pass"]
        and negative["no_learned_new_family_advantage_valid"])
    supported = raw["G1a_postscore_amended"]["parent_gate_evaluation"][
        "supported_topologies"]
    existing = g2["existing_checkpoint_branch_evaluation"]
    existing["g1_supported_topologies"] = supported
    corresponding = bool(
        supported and all(
            existing["k2_localization_recovery_leakage_gates"][topology][job][family][
                "passes"]
            for topology in supported
            for job in config["primary_checkpoints"]
            for family in PRIMARY))
    existing["corresponding_k2_localization_recovery_leakage_pass"] = corresponding
    existing["passes"] = bool(
        supported
        and corresponding
        and existing["counterfactual_all_valid"]
        and existing["tier2_collateral_all_finite"]
        and existing["collateral_noninferiority_all_pass"]
        and existing["point_stability_pass"]
        and existing["matched_k1_fvu_gate_present"])
    learned = g2["learned_model_branch_evaluation"]
    learned["g1_topology_supported"] = bool(supported)
    learned["existing_k2_failure_on_supported_topology"] = bool(
        supported and not corresponding)
    learned["simple_equivalence_failed"] = not g2["simple_branch_available"]
    learned["otherwise_valid_g2"] = bool(
        learned["g2_randomization_all_valid"]
        and learned["g2_bh_all_pass"]
        and learned["coordinate_gates"]
        and all(row["passes"]
                for rows in learned["coordinate_gates"].values()
                for row in rows.values())
        and learned["point_stability_pass"]
        and learned["counterfactual_all_valid"]
        and not learned["boundary_failures"])
    learned["passes"] = bool(
        learned["g1_topology_supported"]
        and learned["existing_k2_failure_on_supported_topology"]
        and learned["simple_equivalence_failed"]
        and learned["otherwise_valid_g2"]
        and learned["falsifiable_mapping_present"]
        and learned["matched_k1_reconstruction_comparator_present"])


def main() -> None:
    global _FAILURE_ATTESTATION
    started = time.monotonic()
    started_utc = utc_now()
    config_path = ROOT / "configs/atlas_completion/analysis.json"
    completion_freeze = require_frozen_completion_config(config_path)
    config = read_json(config_path)
    source_root = ROOT / config["source_run_root"]
    run_root = ROOT / config["run_root"]
    results_root = ROOT / "results/atlas/completion_v1"
    stage = run_root / "verification"
    stage.mkdir(parents=True, exist_ok=True)
    if terminal_state(stage) is not None or any(stage.iterdir()):
        raise RuntimeError(f"completion verification is create-once: {stage}")
    firewall = default_firewall(source_root, run_root)
    _FAILURE_ATTESTATION = firewall.attestation
    attest_completion_freeze_record(firewall, completion_freeze)
    firewall.register_root(ROOT / "data/atlas_completion_v1")
    firewall.register_root(results_root)
    firewall.register_root(stage)
    config_path = firewall.attest(config_path)
    config_sha = sha256_file(config_path)
    bundle_sha = completion_freeze["bundle_sha256"]

    task_manifest_path = ROOT / "configs/atlas/task_row_manifest.json"
    require_frozen_upstream_file(task_manifest_path, firewall)
    task_manifest = strict_json(firewall.attest(task_manifest_path))
    expected_sources: dict[str, dict[str, set[str]]] = {}
    for role in ["calibration", "C1", "C2"]:
        expected_sources[role] = {}
        for task in TASKS:
            row_path = firewall.attest(
                ROOT / task_manifest["roles"][role][task]["path"], role=role)
            require_frozen_upstream_file(row_path, firewall)
            expected_sources[role][task] = {
                str(row["source"]) for row in strict_jsonl(row_path)}
            if not expected_sources[role][task]:
                raise RuntimeError(
                    f"empty frozen source inventory for {role}/{task}")
    tier2_manifest = strict_json(firewall.attest(
        ROOT / "data/atlas_completion_v1/tier2_manifest.json"))
    sentinel_calibration_sources = {
        task: set(map(str, tier2_manifest["roles"]["calibration"][task]["sources"]))
        for task in config["sentinels"]
    }
    transforms_path = firewall.attest(
        ROOT / "data/atlas_v1/transforms/C2.jsonl", role="C2")
    require_frozen_upstream_file(transforms_path, firewall)
    transforms = strict_jsonl(transforms_path)
    transform_ids = [row.get("transform_id") for row in transforms]
    if len(transforms) != 128 or len(set(transform_ids)) != 128:
        raise RuntimeError("frozen C2 transform count/ID uniqueness failure")

    result_marker = require_bound_stage_files(
        results_root, firewall, config_sha256=config_sha,
        completion_bundle_sha256=bundle_sha,
        expected_files={"result_sha256": "completion_results.json"})
    result_path = firewall.attest(results_root / "completion_results.json")
    observed = strict_json(result_path)

    checked_json: dict[str, str] = {}
    strict_roots = [
        run_root / "baseline", run_root / "raw_refit", run_root / "k2_refit",
        run_root / "stability", run_root / "specificity", results_root,
    ]
    for root in strict_roots:
        if not root.is_dir():
            raise FileNotFoundError(f"missing verification input root: {root}")
        for path in sorted(root.rglob("*.json")):
            parsed = strict_json(firewall.attest(path))
            require_recursive_finite(parsed, location=str(path.relative_to(ROOT)))
            checked_json[str(path.relative_to(ROOT))] = sha256_file(path)

    require_bound_stage_files(
        run_root / "baseline", firewall, config_sha256=config_sha,
        completion_bundle_sha256=bundle_sha,
        expected_files={"result_sha256": "baseline.json",
                        "bundle_sha256": "baseline_bundle.pkl"})
    with firewall.attest(run_root / "baseline/baseline_bundle.pkl").open("rb") as handle:
        baseline = pickle.load(handle)
    if baseline.get("completion_bundle_sha256") != bundle_sha:
        raise RuntimeError("baseline bundle is not bound to completion freeze")
    baseline_result = strict_json(firewall.attest(
        run_root / "baseline/baseline.json"))
    verify_parent_raw_calibration(source_root, firewall)
    parent_raw_bundle_path = (
        ROOT / "results/atlas/raw_v1/L3_calibration_bundle.pkl")
    require_frozen_upstream_file(parent_raw_bundle_path, firewall)
    with firewall.attest(parent_raw_bundle_path).open("rb") as handle:
        parent_raw_bundle = pickle.load(handle)
    verify_baseline_semantics(
        baseline_result, baseline, config, expected_sources["calibration"],
        sentinel_calibration_sources, parent_raw_bundle)

    primitive_checks = {"refit_leaves": 0, "stability_leaves": 0,
                        "specificity_leaves": 0}
    paired_l3_raw: dict[str | int, dict[str, Any]] = {}
    for path in sorted((run_root / "raw_refit").rglob("*.json")):
        if path.name != "point.json" and path.parent.name != "draws":
            continue
        stage_name = (path.parent.parent.name
                      if path.parent.name == "draws" else path.parent.name)
        if not stage_name.startswith("L"):
            raise RuntimeError(f"malformed raw stage path: {path}")
        expected_layer = int(stage_name[1:])
        if expected_layer not in config["layers"]:
            raise RuntimeError(f"unregistered raw layer stage: {path}")
        payload = strict_json(path)
        verify_refit_leaf_summaries(
            payload, baseline, expected_sources,
            expected_kind="raw", expected_layer=expected_layer,
            expected_job=None)
        if expected_layer == 3:
            paired_l3_raw[payload["draw_id"]] = payload
        primitive_checks["refit_leaves"] += 1
    paired_draw_ids = {key for key in paired_l3_raw if key != "point"}
    if ("point" not in paired_l3_raw
            or len(paired_draw_ids) < int(config["minimum_complete_draws"])
            or not paired_draw_ids.issubset(set(range(int(config["draws"]))))):
        raise RuntimeError("paired L3 raw draw inventory is incomplete")
    registered_k2_jobs = set(
        config["primary_checkpoints"] + config["descriptive_checkpoints"])
    for path in sorted((run_root / "k2_refit").rglob("*.json")):
        if path.name != "point.json" and path.parent.name != "draws":
            continue
        stage_name = (path.parent.parent.name
                      if path.parent.name == "draws" else path.parent.name)
        expected_layer = 3
        expected_job = stage_name
        if expected_job not in registered_k2_jobs:
            raise RuntimeError(f"unregistered K2 refit stage: {path}")
        payload = strict_json(path)
        if payload["draw_id"] not in paired_l3_raw:
            raise RuntimeError(
                "K2 result exists without paired successful L3 raw artifact")
        verify_refit_leaf_summaries(
            payload, baseline, expected_sources,
            expected_kind="k2", expected_layer=expected_layer,
            expected_job=expected_job,
            paired_raw_payload=paired_l3_raw[payload["draw_id"]])
        primitive_checks["refit_leaves"] += 1
    stability_root = run_root / "stability"
    for path in sorted(stability_root.rglob("*.json")):
        if path.name != "point.json" and path.parent.name != "draws":
            continue
        verify_stability_leaf_summaries(strict_json(path), config, baseline)
        primitive_checks["stability_leaves"] += 1
    token_manifest = strict_json(firewall.attest(
        ROOT / "data/atlas_completion_v1/token_control_manifest.json"))
    token_map = {row["transform_id"]: row for row in token_manifest["rows"]}
    expected_specificity_jobs = set(
        config["primary_checkpoints"] + config["descriptive_checkpoints"])
    observed_specificity_jobs: set[str] = set()
    for path in sorted((run_root / "specificity").glob("*/specificity.json")):
        expected_job = path.parent.name
        if expected_job not in expected_specificity_jobs:
            raise RuntimeError(f"unregistered specificity stage: {expected_job}")
        observed_specificity_jobs.add(expected_job)
        checkpoint = verify_parent_checkpoint(expected_job, firewall)
        parent_functional_path = firewall.attest(
            ROOT / f"results/atlas/k2_v1/{expected_job}_functional.json")
        parent_functional = verify_parent_k2_functional(
            source_root, expected_job, firewall)
        verify_specificity_leaf_summaries(
            strict_json(path), config, token_map, transforms,
            expected_job=expected_job,
            expected_checkpoint_sha256=checkpoint["sha256"],
            expected_parent_functional_sha256=sha256_file(
                parent_functional_path),
            expected_parent_counterfactual_rows=parent_functional[
                "counterfactual_rows"],
            expected_parent_ce_rows=parent_functional["ce_rows"],
            expected_simple_candidate=baseline["selected_simple_baseline"])
        primitive_checks["specificity_leaves"] += 1
    if observed_specificity_jobs != expected_specificity_jobs:
        raise RuntimeError("specificity checkpoint stage inventory mismatch")
    minimum_refit_leaves = 6 * (1 + int(config["minimum_complete_draws"]))
    minimum_stability_leaves = 1 + int(config["minimum_complete_draws"])
    if (primitive_checks["refit_leaves"] < minimum_refit_leaves
            or primitive_checks["stability_leaves"] < minimum_stability_leaves
            or primitive_checks["specificity_leaves"] != 4):
        raise RuntimeError(f"unexpected primitive leaf inventory: {primitive_checks}")

    raw = merge_raw(config, baseline, source_root, run_root, firewall,
                    bundle_sha, config_sha)
    stability, stability_draws = merge_stability(
        config, run_root, firewall, bundle_sha, config_sha)
    g2 = merge_g2(config, baseline, run_root, stability, stability_draws,
                  firewall, bundle_sha, config_sha)
    complete_joint_evaluations(raw, g2, config)
    preflight = strict_json(firewall.attest(
        ROOT / "data/atlas_completion_v1/preflight.json"))
    decision_inputs = {
        "preflight": preflight,
        "baseline": {
            "selected": baseline["selected_simple_baseline"],
            "selection_failed": baseline["baseline_selection_failed"],
        },
        "raw": raw,
        "G2a_postscore_amended": g2,
    }
    predicates = decision_predicates(decision_inputs)
    outcome = decide(predicates)
    decision = {
        "planning_decision_v2": outcome,
        "training_warranted": outcome == "learned_model_warranted",
        "reasons": [
            "known manifest-only minimum-cluster invalidity has highest precedence",
            *raw["G1a_postscore_amended"]["reasons"], *g2["reasons"],
        ],
        "original_architecture_decision": "equivocal_no_decision",
    }
    recomputed = {
        "baseline": {
            "selected": baseline["selected_simple_baseline"],
            "selection_failed": baseline["baseline_selection_failed"],
        },
        "preflight": preflight,
        "raw": raw,
        "stability": stability,
        "G2a_postscore_amended": g2,
        "decision": decision,
    }
    observed_science = {key: observed[key] for key in recomputed}
    if observed_science != recomputed:
        raise RuntimeError("strict leaf recomputation disagrees with promoted completion result")
    require_recursive_finite(recomputed)
    if (observed.get("schema_version") != "atlas_completion_results_v1"
            or observed.get("evidence_class") != EVIDENCE_CLASS
            or observed.get("config_sha256") != config_sha
            or observed.get("completion_bundle_sha256") != bundle_sha
            or result_marker.get("result_sha256") != sha256_file(result_path)):
        raise RuntimeError("promoted completion metadata binding mismatch")

    payload = {
        "schema_version": "atlas_completion_verification_v1",
        "evidence_class": EVIDENCE_CLASS,
        "config_sha256": config_sha,
        "completion_bundle_sha256": bundle_sha,
        "completion_results_sha256": sha256_file(result_path),
        "strict_json_files": checked_json,
        "strict_json_file_count": len(checked_json),
        "recursive_finite_pass": True,
        "leaf_recomputation_pass": True,
        "primitive_summary_recomputation": primitive_checks,
        "recomputed_scientific_sha256": sha256_bytes(
            canonical_json_bytes(recomputed)),
        "resolved_config": config,
        "resolved_arguments": {"results": str(result_path.resolve()),
                               "stage": str(stage.resolve())},
        "seed_provenance": seed_provenance(
            config, contract="deterministic strict reparse and leaf recomputation"),
        "device": None,
        "started_utc": started_utc,
        "ended_utc": utc_now(),
        "environment": runtime_environment(None),
        "input_attestation": firewall.attestation,
    }
    result = stage / "verification.json"
    atomic_write_json(result, payload)
    extension_after = verify_completion_freeze()
    verify_attestation_current(firewall.attestation)
    elapsed = time.monotonic() - started
    write_terminal(stage, complete=True, payload={
        "schema_version": "atlas_completion_verification_complete_v1",
        "result_sha256": sha256_file(result),
        "completion_results_sha256": sha256_file(result_path),
        "config_sha256": config_sha,
        "completion_bundle_sha256": bundle_sha,
        "resolved_config": config,
        "resolved_arguments": payload["resolved_arguments"],
        "seed_provenance": payload["seed_provenance"],
        "device": None,
        "started_utc": started_utc,
        "environment": runtime_environment(None),
        "resource_accounting": process_resource_accounting(
            stage, elapsed_sec=elapsed, device=None),
        "completion_bundle_reverified_after_stage_sha256": extension_after[
            "bundle_sha256"],
        "leaf_recomputation_pass": True,
        "recursive_finite_pass": True,
        "input_attestation": firewall.attestation,
    })
    print(json.dumps({"verified": True, "result": str(result),
                      "files": len(checked_json)}, indent=2))


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        config = read_json(ROOT / "configs/atlas_completion/analysis.json")
        write_failure_terminal(
            ROOT / config["run_root"] / "verification",
            stop_code="completion_verification_failure",
            failed_gate="strict_leaf_recomputation", error=exc,
            input_attestation=_FAILURE_ATTESTATION)
        raise
