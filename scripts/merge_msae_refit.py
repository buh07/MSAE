#!/usr/bin/env python3
"""Validate/merge completion draws and compute amended G1a/G2a diagnostics."""

from __future__ import annotations

import argparse
import copy
import itertools
import json
import math
import pickle
import time
from pathlib import Path
from typing import Any

import numpy as np

from atlas_metrics import simultaneous_bounds
from msa_completion_common import (EVIDENCE_CLASS, ROOT, atomic_write_json,
                                   attest_completion_freeze_record,
                                   chance_score, default_firewall,
                                   deterministic_seed, load_activation,
                                   load_row_file, macro_f1, normalized_recovery,
                                   process_resource_accounting,
                                   read_json, sha256_file, source_equal_score,
                                   require_bound_stage_files,
                                   require_frozen_completion_config,
                                   runtime_environment, seed_provenance,
                                   terminal_state, utc_now,
                                   verify_attestation_current,
                                   verify_completion_freeze,
                                   write_failure_terminal,
                                   write_terminal)
from run_msae_refit_worker import PRIMARY, TASKS, family_rows, rep_matrix


_FAILURE_ATTESTATION: dict[str, Any] = {}


def validate_series_terminal(stage: Path, *, requested: int, config_sha256: str,
                             completion_bundle_sha256: str,
                             point: dict[str, Any], rows: list[dict[str, Any]],
                             errors: list[int], artifacts: dict[str, str],
                             additional_payloads: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    """Validate the immutable worker terminal before any series is merged."""

    if terminal_state(stage) != "complete":
        raise RuntimeError(f"series stage is not measurement-complete: {stage}")
    marker_path = stage / "MEASUREMENT_COMPLETE.json"
    marker = read_json(marker_path)
    scientific_point = point.get("result", point)
    finite_ids = sorted(int(row["draw_id"]) for row in rows
                        if row.get("result", row).get("finite") is True)
    expected_artifacts = {
        str(Path(path).relative_to(stage)): digest
        for path, digest in artifacts.items()
    }
    expected = {
        "requested_draws": requested,
        "config_sha256": config_sha256,
        "completion_bundle_sha256": completion_bundle_sha256,
        "point_scientifically_finite": scientific_point.get("finite") is True,
        "finite_draws": len(finite_ids),
        "scientifically_finite_draw_ids": finite_ids,
        "failed_draws": sorted(errors),
        "artifact_sha256": dict(sorted(expected_artifacts.items())),
    }
    aggregate_attestation: dict[str, Any] = {}
    payloads = [point, *rows, *(additional_payloads or [])]
    required_provenance = {"resolved_config", "resolved_arguments", "seed_provenance",
                           "environment", "started_utc", "ended_utc",
                           "input_attestation"}
    for payload in payloads:
        if str(payload.get("schema_version", "")).startswith("atlas_completion"):
            missing = sorted(required_provenance - set(payload))
            if missing:
                raise RuntimeError(f"series leaf provenance missing {missing}")
        for path, record in payload.get("input_attestation", {}).items():
            if path in aggregate_attestation and aggregate_attestation[path] != record:
                raise RuntimeError(f"series input attestation conflict: {path}")
            aggregate_attestation[path] = record
    expected["input_attestation"] = dict(sorted(aggregate_attestation.items()))
    if any(marker.get(key) != value for key, value in expected.items()):
        raise RuntimeError(f"series terminal disagrees with immutable artifacts: {marker_path}")
    if str(marker.get("schema_version", "")).startswith("atlas_completion"):
        terminal_required = {"resolved_config", "resolved_arguments", "seed_provenance",
                             "environments", "started_utc", "resource_accounting",
                             "parent_bundle_reverified_after_stage_sha256",
                             "completion_bundle_reverified_after_stage_sha256"}
        missing = sorted(terminal_required - set(marker))
        if missing:
            raise RuntimeError(f"series terminal provenance missing {missing}: {marker_path}")
    if expected["point_scientifically_finite"] is not True:
        raise RuntimeError(f"measurement-complete series has nonfinite point: {stage}")
    return marker


def assert_attested_hash(payload: dict[str, Any], path: Path, expected_sha256: str) -> None:
    """Require a producer to have opened the same immutable upstream bytes."""

    resolved = str(path.resolve())
    record = payload.get("input_attestation", {}).get(resolved)
    if (not isinstance(record, dict)
            or record.get("sha256") != expected_sha256
            or record.get("size") != path.stat().st_size):
        raise RuntimeError(f"producer attestation does not bind current upstream: {path}")


def load_series(stage: Path, draws: int, firewall: Any,
                completion_bundle_sha256: str,
                config_sha256: str, *,
                required_attestations: dict[Path, str] | None = None
                ) -> tuple[dict[str, Any], list[dict[str, Any]], list[int], dict[str, str]]:
    point_path = stage / "point.json"
    if not point_path.exists():
        raise RuntimeError(f"missing point result: {point_path}")
    point = read_json(firewall.attest(point_path))
    if (point.get("draw_id") != "point"
            or point.get("config_sha256") != config_sha256
            or point.get("completion_bundle_sha256") != completion_bundle_sha256):
        raise RuntimeError(f"point result is not bound to the completion freeze: {point_path}")
    rows, errors, unaccounted = [], [], []
    additional_payloads: list[dict[str, Any]] = []
    artifacts = {str(point_path): sha256_file(point_path)}
    point_models = stage / "point_models.pkl"
    if point_models.is_file():
        firewall.attest(point_models)
        artifacts[str(point_models)] = sha256_file(point_models)
    for draw in range(draws):
        path = stage / "draws" / f"{draw:04d}.json"
        error_path = stage / "errors" / f"{draw:04d}.json"
        if path.exists() and error_path.exists():
            raise RuntimeError(f"draw has both result and error artifact: {draw}")
        if path.exists():
            row = read_json(firewall.attest(path))
            if row.get("draw_id") != draw:
                raise RuntimeError(f"draw ID mismatch: {path}")
            if (row.get("config_sha256") != config_sha256
                    or row.get("completion_bundle_sha256") != completion_bundle_sha256):
                raise RuntimeError(f"draw is not bound to completion freeze: {path}")
            rows.append(row)
            artifacts[str(path)] = sha256_file(path)
            status_path, status = path, "complete"
        elif error_path.exists():
            error = read_json(firewall.attest(error_path))
            if error.get("draw_id") != draw:
                raise RuntimeError(f"error draw ID mismatch: {error_path}")
            if (error.get("config_sha256") != config_sha256
                    or error.get("completion_bundle_sha256") != completion_bundle_sha256):
                raise RuntimeError(f"draw error is not bound to completion freeze: {error_path}")
            errors.append(draw)
            additional_payloads.append(error)
            artifacts[str(error_path)] = sha256_file(error_path)
            status_path, status = error_path, "failed"
        else:
            unaccounted.append(draw)
            continue
        registry_path = stage / "completed_hashes" / f"{draw:04d}.json"
        registration = read_json(firewall.attest(registry_path))
        if (registration.get("draw_id") != draw or registration.get("status") != status
                or registration.get("artifact_sha256") != sha256_file(status_path)
                or registration.get("config_sha256") != config_sha256
                or registration.get("completion_bundle_sha256") != completion_bundle_sha256):
            raise RuntimeError(f"draw registration mismatch: {registry_path}")
        artifacts[str(registry_path)] = sha256_file(registry_path)
    if unaccounted:
        raise RuntimeError(f"unaccounted requested draw IDs in {stage}: {unaccounted[:20]}")
    for shard_path in sorted(stage.glob("shard_*.json")):
        shard = read_json(firewall.attest(shard_path))
        if (shard.get("config_sha256") != config_sha256
                or shard.get("completion_bundle_sha256") != completion_bundle_sha256
                or not isinstance(shard.get("environment"), dict)
                or not shard.get("started_utc") or not shard.get("ended_utc")):
            raise RuntimeError(f"shard provenance mismatch: {shard_path}")
        additional_payloads.append(shard)
        artifacts[str(shard_path)] = sha256_file(shard_path)
    firewall.attest(stage / "MEASUREMENT_COMPLETE.json")
    validate_series_terminal(stage, requested=draws, config_sha256=config_sha256,
                             completion_bundle_sha256=completion_bundle_sha256,
                             point=point, rows=rows, errors=errors, artifacts=artifacts,
                             additional_payloads=additional_payloads)
    for payload in [point, *rows]:
        for upstream, digest in (required_attestations or {}).items():
            assert_attested_hash(payload, upstream, digest)
    return point, rows, errors, artifacts


def require_measurement_complete(stage: Path, firewall: Any,
                                 expected_files: dict[str, str]) -> dict[str, Any]:
    if terminal_state(stage) != "complete":
        raise RuntimeError(f"required upstream stage is not measurement-complete: {stage}")
    marker_path = firewall.attest(stage / "MEASUREMENT_COMPLETE.json")
    marker = read_json(marker_path)
    for marker_key, filename in expected_files.items():
        path = firewall.attest(stage / filename)
        if marker.get(marker_key) != sha256_file(path):
            raise RuntimeError(f"upstream terminal hash mismatch: {stage}/{filename}")
    return marker


def collateral_noninferiority_gates(
        bounds: dict[str, dict[str, float]] | None, jobs: list[str],
        eligible_sentinels: list[str],
        learned_boundary_failures: list[str]) -> dict[str, Any]:
    """Evaluate every sentinel/CE lower bound; finiteness alone is never a pass."""

    output: dict[str, Any] = {}
    for job in jobs:
        coordinate_names = [f"A_col:{job}:{task}" for task in eligible_sentinels]
        coordinate_names.append(f"A_col:{job}:reconstruction_ce")
        coordinate_gates = {
            name: bool(bounds is not None and name in bounds
                       and math.isfinite(float(bounds[name]["lower"]))
                       and float(bounds[name]["lower"]) >= -0.02)
            for name in coordinate_names
        }
        boundary_clear = all(
            name not in learned_boundary_failures for name in coordinate_names)
        output[job] = {
            "coordinate_lower_at_least_minus_0p02": coordinate_gates,
            "boundary_clear": boundary_clear,
            "passes": bool(coordinate_gates and all(coordinate_gates.values())
                           and boundary_clear),
        }
    return output


def primary_specificity_validity(
        specificity: dict[str, dict[str, Any]],
        primary_jobs: list[str]) -> dict[str, bool]:
    """Keep descriptive g7 science outside primary G2 branch predicates."""

    return {
        "counterfactual_all_valid": all(
            bool(specificity[job]["counterfactual_gate_valid"])
            for job in primary_jobs),
        "identity_collateral_all_valid": all(
            bool(specificity[job]["simple_identity_collateral"]["valid"])
            for job in primary_jobs),
    }


def percentile(values: list[float]) -> dict[str, float | int | None]:
    finite = np.asarray([value for value in values if value is not None and math.isfinite(value)], dtype=float)
    if not len(finite):
        return {"n": 0, "point_bootstrap_mean": None, "ci95": None, "lower95": None, "upper95": None}
    return {"n": len(finite), "point_bootstrap_mean": float(np.mean(finite)),
            "ci95": [float(np.quantile(finite, 0.025)), float(np.quantile(finite, 0.975))],
            "lower95": float(np.quantile(finite, 0.05)), "upper95": float(np.quantile(finite, 0.95))}


def _registered_block_rows(values: list[Any], draw_ids: list[int] | None
                           ) -> tuple[np.ndarray, np.ndarray] | None:
    array = np.asarray(values, dtype=float)
    ids = (np.arange(len(array), dtype=int) if draw_ids is None
           else np.asarray(draw_ids, dtype=int))
    if (len(array) < 450 or len(array) > 500 or len(ids) != len(array)
            or not np.isfinite(array).all() or len(set(ids.tolist())) != len(ids)
            or np.any(ids < 0) or np.any(ids >= 500)):
        return None
    if draw_ids is None and len(array) != 500:
        return None
    return array, ids


def block_mc_uncertainty(values: list[float],
                         draw_ids: list[int] | None = None) -> float | None:
    registered = _registered_block_rows(values, draw_ids)
    if registered is None:
        return None
    array, ids = registered
    endpoints = []
    for block in range(5):
        retained = array[(ids < block * 100) | (ids >= (block + 1) * 100)]
        if len(retained) < 350:
            return None
        endpoints.append([np.quantile(retained, 0.05), np.quantile(retained, 0.95)])
    return float(np.max(np.ptp(np.asarray(endpoints), axis=0)))


def block_quantile_range(values: list[float], quantile: float,
                         draw_ids: list[int] | None = None) -> float | None:
    """Delete registered 100-ID blocks and range one scalar endpoint."""

    registered = _registered_block_rows(values, draw_ids)
    if registered is None:
        return None
    array, ids = registered
    endpoints = []
    for block in range(5):
        retained = array[(ids < block * 100) | (ids >= (block + 1) * 100)]
        if len(retained) < 350:
            return None
        endpoints.append(float(np.quantile(retained, quantile)))
    return float(np.ptp(endpoints))


def block_mean_range(values: list[float], draw_ids: list[int] | None = None) -> float | None:
    """Delete registered 100-ID blocks and range the retained point mean."""

    registered = _registered_block_rows(values, draw_ids)
    if registered is None:
        return None
    array, ids = registered
    endpoints = []
    for block in range(5):
        retained = array[(ids < block * 100) | (ids >= (block + 1) * 100)]
        if len(retained) < 350:
            return None
        endpoints.append(float(np.mean(retained)))
    return float(np.ptp(endpoints))


def threshold_boundary_diagnostic(value: float | None, threshold: float, *,
                                  tolerance: float,
                                  mc_endpoint_range: float | None = None,
                                  mc_not_applicable_reason: str | None = None) -> dict[str, Any]:
    finite = value is not None and math.isfinite(float(value))
    distance = abs(float(value) - threshold) if finite else None
    proximity = bool(distance is not None and distance <= tolerance)
    mc_exceeds = bool(proximity and mc_endpoint_range is not None
                      and math.isfinite(float(mc_endpoint_range))
                      and float(mc_endpoint_range) > tolerance)
    return {"value": value, "threshold": threshold, "distance": distance,
            "tolerance": tolerance, "boundary_proximity": proximity,
            "mc_endpoint_range": mc_endpoint_range,
            "mc_endpoint_range_status": (
                "available" if mc_endpoint_range is not None
                else "not_applicable" if mc_not_applicable_reason is not None
                else "unavailable"),
            "mc_not_applicable_reason": mc_not_applicable_reason,
            "mc_underpowered_at_boundary": mc_exceeds,
            "valid": finite}


def mandatory_evidence_invalid(gates: dict[str, bool]) -> bool:
    """Missing or false mandatory technical evidence has equivocal precedence."""

    return not gates or any(value is not True for value in gates.values())


def registered_g1_randomization_seed(base_seed: int, component_id: str) -> int:
    return deterministic_seed(
        base_seed, "randomization", "g1a_family_lexical_min_topology",
        component_id)


def same_nonzero_direction(values: list[float | None]) -> bool:
    signs = [int(np.sign(float(value))) for value in values
             if value is not None and math.isfinite(float(value))]
    return len(signs) == len(values) and set(signs) in ({-1}, {1})


def k2_localization_gate(row: dict[str, Any], *, tolerance: float = 0.01,
                         mc_ranges: dict[str, float | None] | None = None) -> dict[str, Any]:
    fields = {"assigned_recovery": (0.75, "at_least"),
              "leakage": (0.55, "at_most"),
              "selectivity_margin": (0.20, "at_least")}
    diagnostics = {
        field: threshold_boundary_diagnostic(
            row.get(field), threshold, tolerance=tolerance,
            mc_endpoint_range=None if mc_ranges is None else mc_ranges.get(field),
            mc_not_applicable_reason=(
                "no registered draw series supplied to point-only gate"
                if mc_ranges is None else None))
        for field, (threshold, _) in fields.items()
    }
    gates = {
        "assigned_recovery_at_least_0p75": bool(
            row.get("assigned_recovery") is not None
            and float(row["assigned_recovery"]) >= 0.75
            and not diagnostics["assigned_recovery"]["boundary_proximity"]),
        "leakage_at_most_0p55": bool(
            row.get("leakage") is not None and float(row["leakage"]) <= 0.55
            and not diagnostics["leakage"]["boundary_proximity"]),
        "selectivity_at_least_0p20": bool(
            row.get("selectivity_margin") is not None
            and float(row["selectivity_margin"]) >= 0.20
            and not diagnostics["selectivity_margin"]["boundary_proximity"]),
        "boundary_diagnostics": diagnostics,
    }
    gates["passes"] = all(value for key, value in gates.items()
                           if key != "boundary_diagnostics")
    return gates


def simultaneous_block_mc_diagnostics(observed: list[float], bootstrap: list[list[float]],
                                      draw_ids: list[int] | None = None) -> dict[str, Any] | None:
    """Delete contiguous frozen 100-draw blocks and range bound endpoints."""

    center = np.asarray(observed, dtype=np.float64)
    registered = _registered_block_rows(bootstrap, draw_ids)
    if registered is None:
        return None
    draws, ids = registered
    if draws.ndim != 2 or draws.shape[1] != len(center) or not np.isfinite(center).all():
        return None
    lowers, uppers = [], []
    for block in range(5):
        retained = draws[(ids < block * 100) | (ids >= (block + 1) * 100)]
        if len(retained) < 350:
            return None
        upper_radius = np.quantile(np.max(retained - center, axis=1), 0.95)
        lower_radius = np.quantile(np.max(center - retained, axis=1), 0.95)
        lowers.append(center - lower_radius)
        uppers.append(center + upper_radius)
    return {"lower_endpoint_range": np.ptp(np.asarray(lowers), axis=0).tolist(),
            "upper_endpoint_range": np.ptp(np.asarray(uppers), axis=0).tolist()}


def bh(pvalues: dict[str, float | None]) -> dict[str, float | None]:
    valid = sorted((name, float(value)) for name, value in pvalues.items() if value is not None and math.isfinite(value))
    m = len(pvalues)
    output = {name: None for name in pvalues}
    if not valid:
        return output
    ordered = sorted(valid, key=lambda row: row[1])
    adjusted = [min(1.0, p * m / (i + 1)) for i, (_, p) in enumerate(ordered)]
    for i in range(len(adjusted) - 2, -1, -1):
        adjusted[i] = min(adjusted[i], adjusted[i + 1])
    for (name, _), value in zip(ordered, adjusted, strict=True):
        output[name] = value
    return output


def exact_joint_sign_pvalue(values: list[float] | np.ndarray, *, minimum_clusters: int) -> float | None:
    """Exact one-sided zero-null sign test used by estimator calibration fixtures."""

    array = np.asarray(values, dtype=float)
    if len(array) < minimum_clusters or not np.isfinite(array).all():
        return None
    observed = float(np.mean(array))
    exceed = 0
    for signs in itertools.product((-1.0, 1.0), repeat=len(array)):
        exceed += float(np.mean(array * np.asarray(signs))) >= observed
    return exceed / (2 ** len(array))


def intersection_union_pvalue(components: dict[str, dict[str, Any]],
                              required: list[str]) -> dict[str, Any]:
    """Conservative IUT: every registered component must be valid; use max p."""

    missing = [name for name in required if name not in components]
    invalid = [name for name in required
               if name in components and (components[name].get("valid") is not True
                                           or components[name].get("p") is None
                                           or not math.isfinite(float(components[name]["p"]))) ]
    if missing or invalid:
        return {"valid": False, "p": None, "missing_components": missing,
                "invalid_components": invalid, "winning_component": None}
    ordered = sorted((float(components[name]["p"]), name) for name in required)
    pvalue, winner = ordered[-1]
    if not 0.0 <= pvalue <= 1.0:
        return {"valid": False, "p": None, "missing_components": [],
                "invalid_components": [winner], "winning_component": None}
    return {"valid": True, "p": pvalue, "missing_components": [],
            "invalid_components": [], "winning_component": winner}


def specific_leakage_sign_test(
    primitives: dict[str, dict[str, dict[str, dict[str, Any]]]], *,
    tasks: list[str], assigned: str, leakage: str,
    draws: int, seed: int, minimum_stratum_clusters: int,
    minimum_hypothesis_clusters: int, exact: bool = False,
) -> dict[str, Any]:
    """Source-stratified zero-null sign test for one G1 IUT component."""

    try:
        cells: list[tuple[str, str, dict[str, float]]] = []
        physical: set[tuple[str, str]] = set()
        nonzero: set[tuple[str, str]] = set()
        point_by_task: dict[str, list[float]] = {task: [] for task in tasks}
        for task in tasks:
            sources = sorted(set(primitives[task][assigned]) | set(primitives[task][leakage]))
            if not sources:
                raise ValueError(f"no_sources:{task}")
            for source in sources:
                left = primitives[task][assigned].get(source)
                right = primitives[task][leakage].get(source)
                if left is None or right is None or not left.get("valid") or not right.get("valid"):
                    raise ValueError(f"invalid_primitive:{task}:{source}")
                left_groups = set(left["pseudovalues"])
                right_groups = set(right["pseudovalues"])
                if left_groups != right_groups or len(left_groups) < minimum_stratum_clusters:
                    raise ValueError(f"invalid_or_small_stratum:{task}:{source}")
                delta = {group: float(left["pseudovalues"][group]) - float(right["pseudovalues"][group])
                         for group in sorted(left_groups)}
                if not np.isfinite(list(delta.values())).all():
                    raise ValueError(f"nonfinite_pseudovalue:{task}:{source}")
                cells.append((task, source, delta))
                physical.update((source, group) for group in delta)
                nonzero.update((source, group) for group, value in delta.items() if abs(value) > 1e-15)
                point_by_task[task].append(float(left["point"]) - float(right["point"]))
        if len(nonzero) < minimum_hypothesis_clusters:
            raise ValueError("fewer_than_minimum_nonzero_clusters")

        def aggregate(signs: dict[tuple[str, str], int] | None = None) -> float:
            values_by_task: dict[str, list[float]] = {task: [] for task in tasks}
            for task, source, delta in cells:
                values = [value if signs is None else signs[(source, group)] * value
                          for group, value in delta.items()]
                values_by_task[task].append(float(np.mean(values)))
            return float(np.mean([np.mean(values_by_task[task]) for task in tasks]))

        observed = aggregate()
        point = float(np.mean([np.mean(point_by_task[task]) for task in tasks]))
        reconstruction_error = abs(observed - point)
        if reconstruction_error > 0.01:
            raise ValueError(f"fully_aggregated_reconstruction:{reconstruction_error}")
        keys = sorted(physical)
        exceed = 0
        evaluated = 0
        if exact:
            if len(keys) > 20:
                raise ValueError("exact_enumeration_too_large")
            sign_rows = itertools.product((-1, 1), repeat=len(keys))
        else:
            rng = np.random.Generator(np.random.PCG64(seed))
            sign_rows = (rng.choice(np.asarray([-1, 1], dtype=np.int8), size=len(keys)).tolist()
                         for _ in range(draws))
        for sign_row in sign_rows:
            signs = dict(zip(keys, sign_row, strict=True))
            exceed += aggregate(signs) >= observed
            evaluated += 1
        pvalue = (exceed / evaluated if exact else (1 + exceed) / (draws + 1))
        return {"valid": True, "observed_pseudo_contrast": observed,
                "point_contrast": point, "reconstruction_error": reconstruction_error,
                "clusters": len(keys), "nonzero_clusters": len(nonzero),
                "draws": evaluated, "exact": exact, "p": float(pvalue)}
    except (KeyError, TypeError, ValueError) as exc:
        return {"valid": False, "reason": str(exc), "p": None}


def aggregate_selectivity(means: dict[str, dict[str, dict[str, float]]],
                          families: dict[str, dict[str, Any]], *,
                          assigned_shift: float = 0.0) -> float:
    """Apply source→task→representation→leakage-max→family aggregation."""

    family_values = []
    for family in sorted(families):
        spec = families[family]
        reps = [spec["assigned"], *spec["leakage"]]
        rep_values: dict[str, float] = {}
        for rep in reps:
            task_values = []
            for task in spec["tasks"]:
                source_values = list(means[rep][task].values())
                if not source_values or not np.isfinite(source_values).all():
                    raise ValueError(f"nonfinite primitive mean: {family}/{rep}/{task}")
                task_values.append(float(np.mean(source_values)))
            rep_values[rep] = float(np.mean(task_values))
        # Assigned and comparator coordinates are logical role copies.  A
        # null-imposition shift applies only to the assigned role even when the
        # same physical representation is a comparator in another family.
        family_values.append((rep_values[spec["assigned"]] - assigned_shift)
                             - max(rep_values[rep] for rep in spec["leakage"]))
    if not family_values:
        raise ValueError("no families")
    return float(np.mean(family_values))


def null_imposed_selectivity_test(
    left: dict[str, dict[str, dict[str, dict[str, Any]]]],
    right: dict[str, dict[str, dict[str, dict[str, Any]]]],
    left_families: dict[str, dict[str, Any]],
    right_families: dict[str, dict[str, Any]],
    *, draws: int, seed: int, minimum_stratum_clusters: int,
    minimum_hypothesis_clusters: int, exact: bool = False,
) -> dict[str, Any]:
    """Null-imposed joint source/cluster wild-pseudovalue test from RFC §D.

    Primitive leaves are ``{point, pseudovalues:{group:value}}``.  Physical
    ``(source, group)`` signs are shared across every side/task/representation.
    """

    def validate(primitives: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any],
                                                      set[tuple[str, str]], set[tuple[str, str]]]:
        points: dict[str, Any] = {}
        reconstructed_points: dict[str, Any] = {}
        physical: set[tuple[str, str]] = set()
        nonzero_physical: set[tuple[str, str]] = set()
        for rep, tasks in primitives.items():
            points[rep] = {}
            reconstructed_points[rep] = {}
            for task, sources in tasks.items():
                points[rep][task] = {}
                reconstructed_points[rep][task] = {}
                for source, leaf in sources.items():
                    pseudo = {str(group): float(value) for group, value in leaf["pseudovalues"].items()}
                    point = float(leaf["point"])
                    if len(pseudo) < minimum_stratum_clusters or not np.isfinite([point, *pseudo.values()]).all():
                        raise ValueError(f"invalid_or_small_stratum:{rep}:{task}:{source}")
                    reconstruction = float(np.mean(list(pseudo.values())))
                    if abs(reconstruction - point) > 0.01:
                        raise ValueError(f"primitive_reconstruction:{rep}:{task}:{source}")
                    points[rep][task][source] = point
                    reconstructed_points[rep][task][source] = reconstruction
                    physical.update((source, group) for group in pseudo)
                    nonzero_physical.update((source, group) for group, value in pseudo.items()
                                            if abs(value - reconstruction) > 1e-15)
        return points, reconstructed_points, physical, nonzero_physical

    try:
        left_points, left_reconstructed, left_keys, left_nonzero = validate(left)
        right_points, right_reconstructed, right_keys, right_nonzero = validate(right)
        keys = sorted(left_keys | right_keys)
        nonzero_keys = left_nonzero | right_nonzero
        observed = aggregate_selectivity(left_points, left_families) - aggregate_selectivity(right_points, right_families)
        fully_reconstructed = (aggregate_selectivity(left_reconstructed, left_families)
                               - aggregate_selectivity(right_reconstructed, right_families))
        full_reconstruction_error = abs(fully_reconstructed - observed)
        if full_reconstruction_error > 0.01:
            raise ValueError(f"fully_aggregated_reconstruction:{full_reconstruction_error}")
        if len(nonzero_keys) < minimum_hypothesis_clusters:
            raise ValueError("fewer_than_minimum_nonzero_clusters")
        null_reconstruction = (aggregate_selectivity(left_points, left_families,
                                                      assigned_shift=observed)
                               - aggregate_selectivity(right_points, right_families))
        if abs(null_reconstruction) > 1e-10:
            raise ValueError(f"null_reconstruction:{null_reconstruction}")

        def realized(primitives: dict[str, Any], null_points: dict[str, Any],
                     signs: dict[tuple[str, str], int]) -> dict[str, Any]:
            output = copy.deepcopy(null_points)
            for rep, tasks in primitives.items():
                for task, sources in tasks.items():
                    for source, leaf in sources.items():
                        pseudo = np.asarray(list(leaf["pseudovalues"].values()), dtype=float)
                        groups = list(leaf["pseudovalues"])
                        residual = pseudo - pseudo.mean()
                        sign = np.asarray([signs[(source, str(group))] for group in groups], dtype=float)
                        output[rep][task][source] = float(null_points[rep][task][source] + np.mean(sign * residual))
            return output

        exceed = 0
        evaluated = 0
        if exact:
            if len(keys) > 20:
                raise ValueError("exact_enumeration_too_large")
            sign_rows = itertools.product((-1, 1), repeat=len(keys))
        else:
            rng = np.random.Generator(np.random.PCG64(seed))
            sign_rows = (rng.choice(np.asarray([-1, 1], dtype=np.int8), size=len(keys))
                         for _ in range(draws))
        for sampled in sign_rows:
            signs = dict(zip(keys, list(sampled), strict=True))
            statistic = (aggregate_selectivity(realized(left, left_points, signs), left_families,
                                                assigned_shift=observed)
                         - aggregate_selectivity(realized(right, right_points, signs), right_families))
            exceed += statistic >= observed
            evaluated += 1
        return {"valid": True, "observed": observed,
                "fully_aggregated_pseudomean": fully_reconstructed,
                "fully_aggregated_reconstruction_error": full_reconstruction_error,
                "null_reconstruction": null_reconstruction,
                "clusters": len(keys), "nonzero_clusters": len(nonzero_keys),
                "draws": evaluated, "exact": exact,
                "p": (exceed / evaluated if exact else (1 + exceed) / (draws + 1))}
    except (KeyError, TypeError, ValueError) as exc:
        return {"valid": False, "reason": str(exc), "p": None}


def frozen_group_bootstrap_maps(groups_by_source: dict[str, list[str]], *,
                                draws: int, seed: int, role: str = "C1",
                                layer: int = 3) -> dict[str, np.ndarray]:
    """Recreate the registered source-stratified multinomial group maps.

    The ordering and RNG consumption intentionally match
    ``draw_group_multiplicities``: one generator per draw, followed by sources
    and sorted group IDs.  Rows are multiplicities over the original group
    positions and therefore each row sums to the realized source group count.
    """

    sources = sorted(groups_by_source)
    groups = {source: sorted(map(str, groups_by_source[source])) for source in sources}
    if any(not values or len(values) != len(set(values)) for values in groups.values()):
        raise ValueError("group IDs must be nonempty and unique within source")
    output = {source: np.zeros((draws, len(values)), dtype=np.int32)
              for source, values in groups.items()}
    for draw in range(draws):
        rng = np.random.Generator(np.random.PCG64(deterministic_seed(seed, role, layer, draw)))
        for source in sources:
            values = np.asarray(groups[source], dtype=str)
            sampled = rng.choice(values, size=len(values), replace=True)
            unique, counts = np.unique(sampled, return_counts=True)
            positions = {group: index for index, group in enumerate(groups[source])}
            for group, count in zip(unique.tolist(), counts.tolist(), strict=True):
                output[source][draw, positions[str(group)]] = int(count)
    return output


def negative_sensitivity_simulation(
    residuals_by_source: dict[str, np.ndarray],
    bootstrap_maps: dict[str, np.ndarray], *,
    simulations: int, seed: int, effect: float = 0.20,
) -> dict[str, Any]:
    """Frozen six-coordinate negative-gate sensitivity calculation.

    Each simulation independently resamples the observed centered cluster
    vectors within source, re-centers the resampled vectors so the planted
    full-statistic point is exactly ``effect``, and applies the registered 500
    group-bootstrap maps.  Re-centering is essential: otherwise the explicit
    ``point >= effect`` condition would cap power near one half even with
    arbitrarily precise measurements.
    """

    try:
        sources = sorted(residuals_by_source)
        if not sources or set(sources) != set(bootstrap_maps):
            raise ValueError("residual/bootstrap source mismatch")
        coordinate_count = None
        bootstrap_draws = None
        residuals: dict[str, np.ndarray] = {}
        maps: dict[str, np.ndarray] = {}
        for source in sources:
            residual = np.asarray(residuals_by_source[source], dtype=np.float64)
            weights = np.asarray(bootstrap_maps[source], dtype=np.float64)
            if residual.ndim != 2 or weights.ndim != 2 or residual.shape[0] < 2:
                raise ValueError(f"invalid residual/bootstrap shape:{source}")
            if weights.shape[1] != residual.shape[0] or not np.isfinite(residual).all() or not np.isfinite(weights).all():
                raise ValueError(f"nonfinite or mismatched residual/bootstrap:{source}")
            if np.any(weights < 0) or not np.allclose(weights.sum(axis=1), residual.shape[0]):
                raise ValueError(f"invalid multinomial map:{source}")
            if not np.allclose(residual.mean(axis=0), 0.0, atol=1e-10):
                raise ValueError(f"residuals are not centered:{source}")
            coordinate_count = residual.shape[1] if coordinate_count is None else coordinate_count
            bootstrap_draws = weights.shape[0] if bootstrap_draws is None else bootstrap_draws
            if residual.shape[1] != coordinate_count or weights.shape[0] != bootstrap_draws:
                raise ValueError("coordinate/bootstrap draw mismatch across sources")
            residuals[source], maps[source] = residual, weights
        if coordinate_count is None or bootstrap_draws is None or coordinate_count != 6 or bootstrap_draws != 500:
            raise ValueError("negative sensitivity requires six coordinates and 500 bootstrap maps")
        if simulations < 1 or not math.isfinite(effect):
            raise ValueError("invalid sensitivity simulation request")

        successes = np.zeros(coordinate_count, dtype=np.int64)
        success_matrix = np.zeros((simulations, coordinate_count), dtype=bool)
        point_failures = np.zeros(coordinate_count, dtype=np.int64)
        minimum_points = np.full(coordinate_count, np.inf, dtype=np.float64)
        for simulation_id in range(simulations):
            rng = np.random.Generator(np.random.PCG64(seed + simulation_id))
            bootstrap = np.full((bootstrap_draws, coordinate_count), effect, dtype=np.float64)
            point = np.full(coordinate_count, effect, dtype=np.float64)
            for source in sources:
                residual = residuals[source]
                sampled = residual[rng.choice(residual.shape[0], size=residual.shape[0], replace=True)]
                sampled = sampled - sampled.mean(axis=0, keepdims=True)
                source_point = sampled.mean(axis=0)
                point += source_point
                bootstrap += maps[source] @ sampled / residual.shape[0]
            lower, _ = simultaneous_bounds(point, bootstrap)
            point_ok = point >= effect - 1e-12
            point_failures += ~point_ok
            minimum_points = np.minimum(minimum_points, point)
            simulation_success = point_ok & (lower > 0.0)
            success_matrix[simulation_id] = simulation_success
            successes += simulation_success
        power_mc_ranges: list[float | None] = []
        for coordinate in range(coordinate_count):
            endpoints = []
            for start in range(0, simulations, 100):
                stop = min(start + 100, simulations)
                retained = np.concatenate(
                    [success_matrix[:start, coordinate],
                     success_matrix[stop:, coordinate]])
                if len(retained) < 1000:
                    endpoints = []
                    break
                endpoints.append(float(np.mean(retained)))
            power_mc_ranges.append(float(np.ptp(endpoints)) if endpoints else None)
        return {
            "valid": True,
            "simulations_requested": simulations,
            "simulations_completed": simulations,
            "effect": effect,
            "bootstrap_draws": bootstrap_draws,
            "power": (successes / simulations).tolist(),
            "power_mc_100_block_endpoint_range": power_mc_ranges,
            "successes": successes.tolist(),
            "point_failures": point_failures.tolist(),
            "minimum_points": minimum_points.tolist(),
        }
    except (TypeError, ValueError) as exc:
        return {"valid": False, "simulations_requested": simulations,
                "simulations_completed": 0, "effect": effect, "reason": str(exc),
                "power": [None] * 6}


def grouped_f1_point_leave(y: np.ndarray, pred: np.ndarray,
                           groups: np.ndarray) -> tuple[float, dict[str, float]]:
    """Macro-F1 point/delete-one leaves with the point truth classes frozen."""

    labels, encoded = np.unique(np.concatenate([y.astype(str), pred.astype(str)]), return_inverse=True)
    frozen_truth_indices = np.flatnonzero(np.isin(labels, np.unique(y.astype(str))))
    true, predicted = encoded[:len(y)], encoded[len(y):]
    unique_groups, group_index = np.unique(groups.astype(str), return_inverse=True)
    width = len(labels)
    cell = true * width + predicted
    total = np.bincount(cell, minlength=width * width).reshape(width, width).astype(np.float64)
    grouped = np.bincount(group_index * width * width + cell,
                          minlength=len(unique_groups) * width * width).reshape(len(unique_groups), width, width)

    def scores(confusion: np.ndarray) -> np.ndarray:
        diag = np.diagonal(confusion, axis1=-2, axis2=-1)
        denominator = confusion.sum(axis=-1) + confusion.sum(axis=-2)
        active = denominator > 0
        values = np.divide(2.0 * diag, denominator, out=np.zeros_like(diag), where=active)
        result = np.divide(values.sum(axis=-1), active.sum(axis=-1),
                           out=np.full(values.shape[:-1], np.nan),
                           where=active.sum(axis=-1) > 0)
        frozen_present = np.all(
            confusion[..., frozen_truth_indices, :].sum(axis=-1) > 0,
            axis=-1)
        return np.where(frozen_present, result, np.nan)

    point = float(scores(total))
    leave = scores(total[None, :, :] - grouped)
    return point, {str(group): float(value)
                   for group, value in zip(unique_groups.tolist(), leave.tolist(), strict=True)}


def grouped_chance_point_leave(y_fit: np.ndarray, y_eval: np.ndarray,
                               groups: np.ndarray) -> tuple[float, dict[str, float]]:
    """Chance point/delete-one leaves with evaluation truth classes frozen."""

    labels = np.unique(np.concatenate([y_fit.astype(str), y_eval.astype(str)]))
    label_index = {label: index for index, label in enumerate(labels.tolist())}
    fit_counts = np.zeros(len(labels), dtype=np.float64)
    eval_counts = np.zeros(len(labels), dtype=np.float64)
    np.add.at(fit_counts, [label_index[value] for value in y_fit.astype(str)], 1.0)
    eval_encoded = np.asarray([label_index[value] for value in y_eval.astype(str)], dtype=np.int64)
    frozen_eval_indices = np.unique(eval_encoded)
    np.add.at(eval_counts, eval_encoded, 1.0)
    unique_groups, group_index = np.unique(groups.astype(str), return_inverse=True)
    grouped = np.zeros((len(unique_groups), len(labels)), dtype=np.float64)
    np.add.at(grouped, (group_index, eval_encoded), 1.0)
    fit_prior = fit_counts / fit_counts.sum()

    def scores(counts: np.ndarray) -> np.ndarray:
        totals = counts.sum(axis=-1, keepdims=True)
        eval_prior = np.divide(counts, totals, out=np.full_like(counts, np.nan),
                               where=totals > 0)
        denominator = fit_prior + eval_prior
        harmonic = np.divide(2.0 * fit_prior * eval_prior, denominator,
                             out=np.zeros_like(eval_prior), where=denominator > 0)
        result = harmonic.mean(axis=-1)
        frozen_present = np.all(counts[..., frozen_eval_indices] > 0, axis=-1)
        return np.where(frozen_present, result, np.nan)

    point = float(scores(eval_counts))
    leave = scores(eval_counts[None, :] - grouped)
    return point, {str(group): float(value)
                   for group, value in zip(unique_groups.tolist(), leave.tolist(), strict=True)}


def fixed_recovery_pseudovalues(*, task: str, rep: str, discovery: Any, c1: Any,
                                raw_bundle: dict[str, Any], task_manifest: dict[str, Any],
                                firewall: Any) -> dict[str, Any]:
    dr, dy, ds, _ = load_row_file(ROOT / task_manifest["roles"]["discovery"][task]["path"], discovery, firewall, role="discovery")
    er, ey, es, eg = load_row_file(ROOT / task_manifest["roles"]["C1"][task]["path"], c1, firewall, role="C1")
    dx = (np.asarray(discovery.x[dr], np.float32) - raw_bundle["mean"]) / raw_bundle["scale"]
    ex = (np.asarray(c1.x[er], np.float32) - raw_bundle["mean"]) / raw_bundle["scale"]
    raw_pred = raw_bundle["raw_models"][task].predict(ex)
    rep_x = rep_matrix(ex, rep, raw_bundle["bases"])
    rep_pred = raw_bundle["component_models"][rep][task].predict(rep_x)

    output: dict[str, Any] = {}
    for source in sorted(np.unique(es).tolist()):
        sm = es == source
        source_groups = eg[sm].astype(str)
        groups = np.unique(source_groups)
        raw, raw_leave = grouped_f1_point_leave(ey[sm], raw_pred[sm], source_groups)
        component, component_leave = grouped_f1_point_leave(ey[sm], rep_pred[sm], source_groups)
        chance, chance_leave = grouped_chance_point_leave(dy, ey[sm], source_groups)
        point = normalized_recovery(component, raw, chance)
        if point is None:
            output[source] = {"valid": False, "reason": "undefined_point", "groups": len(groups)}
            continue
        pseudo = {}
        valid = True
        invalid_reason = None
        for group in groups:
            key = str(group)
            value = normalized_recovery(component_leave[key], raw_leave[key], chance_leave[key])
            if value is None:
                valid = False
                invalid_reason = f"undefined_leave_one:{key}"
                break
            pseudo[key] = float(len(groups) * point - (len(groups) - 1) * value)
        reconstruction = float(np.mean(list(pseudo.values()))) if pseudo else None
        if reconstruction is None or abs(reconstruction - point) > 0.01:
            valid = False
            invalid_reason = invalid_reason or "pseudovalue_reconstruction_failure"
        output[source] = {"valid": valid, "point": point, "groups": len(groups),
                          "pseudovalues": pseudo, "pseudo_mean": reconstruction,
                          "reason": invalid_reason,
                          "reconstruction_error": None if reconstruction is None else abs(reconstruction - point)}
    return output


def lexical_g1_randomization(config: dict[str, Any], baseline: dict[str, Any], source_root: Path,
                             run_root: Path, raw_point: dict[str, Any], firewall: Any) -> dict[str, Any]:
    """Executable G1 lexical IUT; other G1 tests are deterministically invalid."""

    discovery = load_activation("discovery", 3, source_root, firewall)
    c1 = load_activation("C1", 3, source_root, firewall)
    exact_bundle_path = firewall.attest(run_root / "raw_refit/L3/point_models.pkl")
    if raw_point.get("point_models_sha256") != sha256_file(exact_bundle_path):
        raise RuntimeError("exact raw point-model bundle hash mismatch")
    with exact_bundle_path.open("rb") as handle:
        bundle = pickle.load(handle)
    if (bundle.get("schema_version") != "atlas_completion_exact_raw_point_models_v1"
            or bundle.get("completion_bundle_sha256") != raw_point.get("completion_bundle_sha256")):
        raise RuntimeError("exact raw point-model bundle metadata mismatch")
    task_manifest = read_json(firewall.attest(ROOT / "configs/atlas/task_row_manifest.json"))
    tasks = [task for task in PRIMARY["lexical_semantic_content"] if baseline["tier1_eligibility"][task]["eligible"]]
    mappings = {
        "split": {"assigned": "split_complement", "leakage": ["absolute_position", "relative_structural_position"]},
        "broad": {"assigned": "broad_complement", "leakage": ["broad_position"]},
    }
    needed = sorted({value for row in mappings.values() for value in [row["assigned"], *row["leakage"]]})
    primitive = {task: {rep: fixed_recovery_pseudovalues(task=task, rep=rep, discovery=discovery, c1=c1,
                                                         raw_bundle=bundle, task_manifest=task_manifest, firewall=firewall)
                        for rep in needed} for task in tasks}
    components = {}
    for topology, mapping in mappings.items():
        for leakage in mapping["leakage"]:
            component_id = f"{topology}:{leakage}"
            components[component_id] = specific_leakage_sign_test(
                primitive, tasks=tasks, assigned=mapping["assigned"], leakage=leakage,
                draws=int(config["randomization_draws"]),
                seed=registered_g1_randomization_seed(config["seed"], component_id),
                minimum_stratum_clusters=int(config["minimum_groups_per_task_source"]),
                minimum_hypothesis_clusters=int(config["minimum_groups_per_hypothesis"]),
            )
    registered_point = raw_effect(raw_point, "family:lexical_semantic_content")
    reconstructed_point = (min(float(row["observed_pseudo_contrast"]) for row in components.values())
                           if components and all(row["valid"] for row in components.values()) else None)
    reconstruction_error = (None if registered_point is None or reconstructed_point is None else
                            abs(float(registered_point) - reconstructed_point))
    required_components = [f"{topology}:{leakage}"
                           for topology, mapping in mappings.items()
                           for leakage in mapping["leakage"]]
    iut = intersection_union_pvalue(components, required_components)
    valid = bool(iut["valid"] and reconstruction_error is not None and reconstruction_error <= 0.01)
    return {"valid": valid, "components": components,
            "p": iut["p"] if valid else None,
            "intersection_union": iut,
            "registered_exact_ridge_point": registered_point,
            "reconstructed_exact_ridge_point": reconstructed_point,
            "point_reconstruction_error": reconstruction_error,
            "primitive_reconstruction": primitive}


def raw_effect(row: dict[str, Any], hypothesis: str) -> float | None:
    raw = row["result"]["raw_g1"]
    if hypothesis.startswith("family:"):
        family = hypothesis.split(":", 1)[1]
        values = [raw[topology][family]["selectivity_margin"] for topology in ["split", "broad"]]
        return None if any(value is None for value in values) else min(map(float, values))
    split_values = [raw["split"][family]["selectivity_margin"] for family in ["absolute_position", "relative_structural_position"]]
    broad_values = [raw["broad"][family]["selectivity_margin"] for family in ["absolute_position", "relative_structural_position"]]
    if any(value is None or not math.isfinite(float(value)) for value in split_values + broad_values):
        return None
    split = np.mean(split_values)
    broad = np.mean(broad_values)
    return float(split - broad)


def topology_family_effect(row: dict[str, Any], topology: str, family: str) -> float | None:
    value = row["result"]["raw_g1"][topology][family]["selectivity_margin"]
    return None if value is None or not math.isfinite(float(value)) else float(value)


def negative_coordinate_vector(primitives: dict[str, dict[str, dict[str, dict[str, Any]]]],
                               eligible_tasks: set[str], *,
                               leave_source: str | None = None,
                               leave_group: str | None = None) -> np.ndarray:
    """Aggregate primitive fixed-model recoveries into the six registered effects."""

    mappings = {
        "split": {"absolute_position": "absolute_position",
                  "relative_structural_position": "relative_structural_position",
                  "lexical_semantic_content": "split_complement"},
        "broad": {"absolute_position": "broad_position",
                  "relative_structural_position": "broad_position",
                  "lexical_semantic_content": "broad_complement"},
    }
    recovery: dict[str, dict[str, float | None]] = {rep: {} for rep in primitives}
    for rep, tasks in primitives.items():
        for task, sources in tasks.items():
            values = []
            for source, leaf in sources.items():
                if not leaf.get("valid") or leaf.get("point") is None:
                    raise ValueError(f"invalid negative-sensitivity primitive:{rep}:{task}:{source}")
                value = float(leaf["point"])
                if source == leave_source and leave_group is not None and leave_group in leaf["pseudovalues"]:
                    count = int(leaf["groups"])
                    if count < 2:
                        raise ValueError(f"too few groups for delete-one primitive:{rep}:{task}:{source}")
                    value = ((count * value - float(leaf["pseudovalues"][leave_group]))
                             / (count - 1))
                values.append(value)
            recovery[rep][task] = float(np.mean(values)) if values else None
    coordinates = []
    for topology in ["split", "broad"]:
        rows = family_rows(recovery, mappings[topology], eligible_tasks)
        for family in PRIMARY:
            value = rows[family]["selectivity_margin"]
            if value is None or not math.isfinite(float(value)):
                raise ValueError(f"undefined negative coordinate:{topology}:{family}")
            coordinates.append(float(value))
    return np.asarray(coordinates, dtype=np.float64)


def build_negative_sensitivity_residuals(
    config: dict[str, Any], baseline: dict[str, Any], source_root: Path,
    run_root: Path, raw_point: dict[str, Any], firewall: Any,
) -> tuple[dict[str, np.ndarray], dict[str, list[str]], dict[str, Any]]:
    """Build centered delete-one full-statistic pseudovalue residual vectors."""

    discovery = load_activation("discovery", 3, source_root, firewall)
    c1 = load_activation("C1", 3, source_root, firewall)
    exact_bundle_path = firewall.attest(run_root / "raw_refit/L3/point_models.pkl")
    if raw_point.get("point_models_sha256") != sha256_file(exact_bundle_path):
        raise RuntimeError("exact raw point-model bundle hash mismatch for sensitivity")
    with exact_bundle_path.open("rb") as handle:
        bundle = pickle.load(handle)
    if (bundle.get("schema_version") != "atlas_completion_exact_raw_point_models_v1"
            or bundle.get("completion_bundle_sha256") != raw_point.get("completion_bundle_sha256")):
        raise RuntimeError("exact raw point-model bundle metadata mismatch for sensitivity")
    task_manifest = read_json(firewall.attest(ROOT / "configs/atlas/task_row_manifest.json"))
    eligible_tasks = {task for task, row in baseline["tier1_eligibility"].items() if row["eligible"]}
    family_tasks = {task for tasks in PRIMARY.values() for task in tasks if task in eligible_tasks}
    mappings = {
        "split": {"absolute_position": "absolute_position",
                  "relative_structural_position": "relative_structural_position",
                  "lexical_semantic_content": "split_complement"},
        "broad": {"absolute_position": "broad_position",
                  "relative_structural_position": "broad_position",
                  "lexical_semantic_content": "broad_complement"},
    }
    needed_reps = sorted({rep for mapping in mappings.values() for rep in mapping.values()})
    primitives = {
        rep: {
            task: fixed_recovery_pseudovalues(task=task, rep=rep, discovery=discovery, c1=c1,
                                               raw_bundle=bundle, task_manifest=task_manifest,
                                               firewall=firewall)
            for task in sorted(family_tasks)
        }
        for rep in needed_reps
    }
    point = negative_coordinate_vector(primitives, eligible_tasks)
    registered = np.asarray([
        topology_family_effect(raw_point, topology, family)
        for topology in ["split", "broad"] for family in PRIMARY
    ], dtype=np.float64)
    if not np.isfinite(registered).all() or np.max(np.abs(point - registered)) > 0.01:
        raise ValueError("negative-sensitivity point reconstruction exceeds 0.01")

    groups_by_source = {
        str(source): sorted(np.unique(c1.row_group[c1.row_source.astype(str) == str(source)].astype(str)).tolist())
        for source in sorted(np.unique(c1.row_source.astype(str)).tolist())
    }
    residuals: dict[str, np.ndarray] = {}
    reconstruction: dict[str, Any] = {}
    for source, groups in groups_by_source.items():
        count = len(groups)
        pseudo = np.empty((count, 6), dtype=np.float64)
        for index, group in enumerate(groups):
            leave = negative_coordinate_vector(primitives, eligible_tasks,
                                                leave_source=source, leave_group=group)
            pseudo[index] = count * point - (count - 1) * leave
        pseudo_mean = pseudo.mean(axis=0)
        error = np.abs(pseudo_mean - point)
        if not np.isfinite(pseudo).all() or np.any(error > 0.01):
            raise ValueError(f"negative-sensitivity pseudovalue reconstruction exceeds 0.01:{source}")
        residuals[source] = pseudo - pseudo_mean
        reconstruction[source] = {
            "groups": count,
            "maximum_absolute_error": float(np.max(error)),
            "error_by_coordinate": error.tolist(),
        }
    diagnostics = {
        "registered_point": registered.tolist(),
        "reconstructed_point": point.tolist(),
        "point_maximum_absolute_error": float(np.max(np.abs(point - registered))),
        "source_reconstruction": reconstruction,
    }
    return residuals, groups_by_source, diagnostics


def raw_source_effects(row: dict[str, Any], eligible_tasks: set[str]) -> dict[str, dict[str, float | None]]:
    """Recompute registered G1 effects within each applicable dataset source."""

    result = row["result"]
    detail = result["source_detail"]
    mappings = {
        "split": {"absolute_position": "absolute_position", "relative_structural_position": "relative_structural_position",
                  "lexical_semantic_content": "split_complement"},
        "broad": {"absolute_position": "broad_position", "relative_structural_position": "broad_position",
                  "lexical_semantic_content": "broad_complement"},
    }
    by_topology: dict[str, dict[str, dict[str, float | None]]] = {topology: {} for topology in mappings}
    for topology, mapping in mappings.items():
        for family, tasks_all in PRIMARY.items():
            tasks = [task for task in tasks_all if task in eligible_tasks]
            assigned = mapping[family]
            leakage = sorted({mapping[other] for other in PRIMARY if other != family})
            sources = sorted({source for task in tasks for source in detail[f"{assigned}:{task}"]["by_source"]})
            values: dict[str, float | None] = {}
            for source in sources:
                assigned_tasks, leakage_tasks = [], {rep: [] for rep in leakage}
                invalid_applicable_leaf = False
                for task in tasks:
                    assigned_row = detail[f"{assigned}:{task}"]["by_source"].get(source)
                    # A source absent from this task is structurally inapplicable.
                    # A present source with an undefined required leaf is invalid
                    # and must not silently shrink the task mean.
                    if assigned_row is None:
                        continue
                    if assigned_row.get("recovery") is None:
                        invalid_applicable_leaf = True
                        break
                    rep_rows = {rep: detail[f"{rep}:{task}"]["by_source"].get(source) for rep in leakage}
                    if any(value is None or value.get("recovery") is None for value in rep_rows.values()):
                        invalid_applicable_leaf = True
                        break
                    assigned_tasks.append(float(assigned_row["recovery"]))
                    for rep, value in rep_rows.items():
                        leakage_tasks[rep].append(float(value["recovery"]))
                if invalid_applicable_leaf:
                    values[source] = None
                elif assigned_tasks and all(len(values_rep) == len(assigned_tasks) for values_rep in leakage_tasks.values()):
                    values[source] = float(np.mean(assigned_tasks) - max(np.mean(v) for v in leakage_tasks.values()))
            by_topology[topology][family] = values
    output: dict[str, dict[str, float | None]] = {}
    for family in PRIMARY:
        common = sorted(set(by_topology["split"][family]) & set(by_topology["broad"][family]))
        output[f"family:{family}"] = {
            source: (None if by_topology["split"][family][source] is None
                     or by_topology["broad"][family][source] is None else
                     min(float(by_topology["split"][family][source]),
                         float(by_topology["broad"][family][source])))
            for source in common
        }
    positional_sources = sorted(set.intersection(*[
        set(by_topology[topology][family])
        for topology in ["split", "broad"]
        for family in ["absolute_position", "relative_structural_position"]
    ]))
    output["split_minus_broad_positional"] = {
        source: (None if any(by_topology[topology][family][source] is None
                             for topology in ["split", "broad"]
                             for family in ["absolute_position", "relative_structural_position"])
                 else float(np.mean([float(by_topology["split"][family][source])
                                     for family in ["absolute_position", "relative_structural_position"]])
                            - np.mean([float(by_topology["broad"][family][source])
                                       for family in ["absolute_position", "relative_structural_position"]])))
        for source in positional_sources
    }
    return output


def merge_raw(config: dict[str, Any], baseline: dict[str, Any], source_root: Path, run_root: Path,
              firewall: Any, completion_bundle_sha256: str,
              config_sha256: str) -> dict[str, Any]:
    hypotheses = ["family:absolute_position", "family:relative_structural_position", "family:lexical_semantic_content", "split_minus_broad_positional"]
    eligible_tasks = {task for task, row in baseline["tier1_eligibility"].items() if row["eligible"]}
    layers = {}
    primary_point: dict[str, Any] | None = None
    primary_rows: list[dict[str, Any]] | None = None
    baseline_path = run_root / "baseline/baseline_bundle.pkl"
    baseline_attestation = {baseline_path: sha256_file(baseline_path)}
    for layer in config["layers"]:
        stage = run_root / "raw_refit" / f"L{layer}"
        point, rows, errors, artifacts = load_series(stage, int(config["draws"]), firewall,
                                                     completion_bundle_sha256, config_sha256,
                                                     required_attestations=baseline_attestation)
        finite_rows = [row for row in rows if row["result"].get("finite") is True]
        finite_draw_ids = [int(row["draw_id"]) for row in finite_rows]
        nonfinite_draw_ids = [int(row["draw_id"]) for row in rows if row["result"].get("finite") is not True]
        effects = {hyp: [raw_effect(row, hyp) for row in finite_rows] for hyp in hypotheses}
        point_effects = {hyp: raw_effect(point, hyp) for hyp in hypotheses}
        topology_family = {}
        for topology in ["split", "broad"]:
            topology_family[topology] = {}
            for family in PRIMARY:
                point_row = point["result"]["raw_g1"][topology][family]
                field_draws = {
                    field: [row["result"]["raw_g1"][topology][family][field]
                            for row in finite_rows]
                    for field in ["assigned_recovery", "leakage", "selectivity_margin"]
                }
                topology_family[topology][family] = {
                    "point": {field: point_row[field] for field in field_draws},
                    "bootstrap": {
                        field: {**percentile(values),
                                "ci95_lower_mc_100_block_endpoint_range":
                                    block_quantile_range(values, 0.025,
                                                         finite_draw_ids),
                                "point_mc_100_block_endpoint_range":
                                    block_mean_range(values, finite_draw_ids)}
                        for field, values in field_draws.items()
                    },
                }
        point_source = raw_source_effects(point, eligible_tasks)
        source_reversal = {}
        for hyp in hypotheses:
            aggregate = point_effects[hyp]
            invalid_point_sources = sorted(source for source, value in point_source[hyp].items() if value is None)
            reversed_sources = (sorted(source for source, value in point_source[hyp].items()
                                       if value is not None and aggregate is not None
                                       and float(value) * float(aggregate) < 0))
            draw_reversal_ids = []
            draw_invalid_ids = []
            for draw_row in finite_rows:
                draw_aggregate = raw_effect(draw_row, hyp)
                draw_source = raw_source_effects(draw_row, eligible_tasks)[hyp]
                if draw_aggregate is None or any(value is None for value in draw_source.values()):
                    draw_invalid_ids.append(int(draw_row["draw_id"]))
                elif any(float(value) * float(draw_aggregate) < 0 for value in draw_source.values() if value is not None):
                    draw_reversal_ids.append(int(draw_row["draw_id"]))
            source_reversal[hyp] = {"point_source_effects": point_source[hyp],
                                    "point_invalid_sources": invalid_point_sources,
                                    "point_reversed_sources": reversed_sources,
                                    "point_passes": bool(aggregate is not None and not invalid_point_sources and not reversed_sources),
                                    "draw_reversal_count": len(draw_reversal_ids),
                                    "draw_reversal_ids": draw_reversal_ids,
                                    "draw_invalid_count": len(draw_invalid_ids),
                                    "draw_invalid_ids": draw_invalid_ids}
        layers[str(layer)] = {"point": point_effects,
                              "topology_family": topology_family,
                              "bootstrap": {
                                  hyp: {**percentile(values),
                                        "mc_100_block_endpoint_range":
                                            block_mc_uncertainty(values,
                                                                 finite_draw_ids),
                                        "lower95_mc_100_block_endpoint_range":
                                            block_quantile_range(
                                                values, 0.05, finite_draw_ids),
                                        "upper95_mc_100_block_endpoint_range":
                                            block_quantile_range(
                                                values, 0.95, finite_draw_ids)}
                                  for hyp, values in effects.items()},
                              "source_reversal": source_reversal,
                              "requested": config["draws"], "present": len(rows),
                              "finite_complete_cases": len(finite_rows),
                              "nonfinite_draw_ids": nonfinite_draw_ids, "failed_draws": errors}
        if int(layer) == int(config["primary_layer"]):
            primary_point, primary_rows = point, finite_rows
    if primary_point is None or primary_rows is None:
        raise RuntimeError("primary raw-refit layer was not merged")

    negative_coordinates = [(topology, family) for topology in ["split", "broad"] for family in PRIMARY]
    negative_names = [f"{topology}:{family}" for topology, family in negative_coordinates]
    negative_point = [topology_family_effect(primary_point, topology, family)
                      for topology, family in negative_coordinates]
    negative_draws = [[topology_family_effect(row, topology, family)
                       for topology, family in negative_coordinates] for row in primary_rows]
    negative_complete_pairs = [
        (int(primary_rows[index]["draw_id"]), row)
        for index, row in enumerate(negative_draws)
        if all(value is not None and math.isfinite(float(value)) for value in row)]
    negative_complete_ids = [draw_id for draw_id, _ in negative_complete_pairs]
    negative_complete = [row for _, row in negative_complete_pairs]
    negative_bounds = None
    negative_mc_ranges = {name: None for name in negative_names}
    if (len(negative_complete) >= int(config["minimum_complete_draws"])
            and all(value is not None and math.isfinite(float(value)) for value in negative_point)):
        lower, upper = simultaneous_bounds([float(value) for value in negative_point], np.asarray(negative_complete))
        negative_bounds = {name: {"point": float(negative_point[i]), "lower": float(lower[i]), "upper": float(upper[i])}
                           for i, name in enumerate(negative_names)}
        negative_mc = simultaneous_block_mc_diagnostics(
            [float(value) for value in negative_point],
            [[float(value) for value in row] for row in negative_complete],
            negative_complete_ids)
        if negative_mc is not None:
            negative_mc_ranges = {
                name: float(negative_mc["upper_endpoint_range"][index])
                for index, name in enumerate(negative_names)
            }
    tolerance = float(config["boundary_tolerance"])
    negative_boundary = {
        name: threshold_boundary_diagnostic(
            None if negative_bounds is None else negative_bounds[name]["upper"], 0.20,
            tolerance=tolerance, mc_endpoint_range=negative_mc_ranges[name])
        for name in negative_names
    }
    negative_boundary_failures = sorted(
        name for name, row in negative_boundary.items()
        if not row["valid"] or row["boundary_proximity"])
    try:
        residuals, groups_by_source, sensitivity_diagnostics = build_negative_sensitivity_residuals(
            config, baseline, source_root, run_root, primary_point, firewall)
        maps = frozen_group_bootstrap_maps(groups_by_source, draws=int(config["draws"]),
                                           seed=int(config["seed"]), role="C1", layer=3)
        sensitivity_result = negative_sensitivity_simulation(
            residuals, maps, simulations=2000, seed=int(config["seed"]), effect=0.20)
        negative_sensitivity = {
            **sensitivity_result,
            "power_by_coordinate": {
                name: sensitivity_result["power"][index]
                for index, name in enumerate(negative_names)
            },
            "power_mc_100_block_endpoint_range_by_coordinate": {
                name: sensitivity_result["power_mc_100_block_endpoint_range"][index]
                for index, name in enumerate(negative_names)
            },
            "realized_source_group_counts": {
                source: len(groups) for source, groups in groups_by_source.items()
            },
            "pseudovalue_diagnostics": sensitivity_diagnostics,
        }
    except (KeyError, RuntimeError, TypeError, ValueError) as exc:
        negative_sensitivity = {
            "valid": False,
            "simulations_requested": 2000,
            "simulations_completed": 0,
            "reason": str(exc),
            "power_by_coordinate": {name: None for name in negative_names},
            "power_mc_100_block_endpoint_range_by_coordinate": {
                name: None for name in negative_names},
        }
    sensitivity_boundary = {
        name: threshold_boundary_diagnostic(
            negative_sensitivity["power_by_coordinate"][name], 0.80,
            tolerance=tolerance,
            mc_endpoint_range=negative_sensitivity[
                "power_mc_100_block_endpoint_range_by_coordinate"][name])
        for name in negative_names
    }
    sensitivity_pass = bool(
        negative_sensitivity.get("valid")
        and all(value is not None and float(value) >= 0.80
                for value in negative_sensitivity["power_by_coordinate"].values())
        and all(row["valid"] and not row["boundary_proximity"]
                for row in sensitivity_boundary.values()))
    negative_gate = {
        "coordinates": negative_names,
        "complete_case_draws": len(negative_complete),
        "simultaneous_bounds": negative_bounds,
        "boundary_diagnostics": negative_boundary,
        "boundary_failures": negative_boundary_failures,
        "all_upper_below_0p20": bool(negative_bounds is not None
                                      and not negative_boundary_failures
                                      and all(row["upper"] < 0.20 for row in negative_bounds.values())),
        "sensitivity": negative_sensitivity,
        "sensitivity_boundary_diagnostics": sensitivity_boundary,
        "sensitivity_at_least_0p80": sensitivity_pass,
        # Learned-new-family advantage is evaluated in the joint renderer; this
        # raw diagnostic records only the two raw-side negative requirements.
        "raw_negative_requirements_pass": bool(
            negative_bounds is not None
            and not negative_boundary_failures
            and all(row["upper"] < 0.20 for row in negative_bounds.values())
            and sensitivity_pass),
        "supported_negative_all_gates": False,
    }
    lexical = lexical_g1_randomization(config, baseline, source_root, run_root, primary_point, firewall)
    pvalues = {"g1a_family_absolute_min_topology": None,
               "g1a_family_structural_min_topology": None,
               "g1a_family_lexical_min_topology": lexical["p"],
               "g1a_split_minus_broad_positional": None}
    randomization = {
        "g1a_family_absolute_min_topology": {"valid": False, "reason": "broad topology assigned representation is also a registered nonassigned representation; fewer than 20 nonzero contrast clusters"},
        "g1a_family_structural_min_topology": {"valid": False, "reason": "LinES task/source strata have fewer than 10 document groups"},
        "g1a_family_lexical_min_topology": lexical,
        "g1a_split_minus_broad_positional": {"valid": False, "reason": "depends on LinES task/source strata with fewer than 10 document groups"},
    }
    qvalues = bh(pvalues)
    fourth_bootstrap = layers[str(config["primary_layer"])]["bootstrap"]["split_minus_broad_positional"]
    fourth_boundary = {
        endpoint: threshold_boundary_diagnostic(
            fourth_bootstrap[endpoint], 0.05, tolerance=tolerance,
            mc_endpoint_range=fourth_bootstrap[
                f"{endpoint}_mc_100_block_endpoint_range"])
        for endpoint in ["lower95", "upper95"]
    }
    primary_layer = layers[str(config["primary_layer"])]
    reversal_failures = [hyp for hyp, row in primary_layer["source_reversal"].items()
                         if not row["point_passes"]]
    family_gates = {}
    family_boundary_diagnostics: dict[str, dict[str, Any]] = {}
    q_names = {
        "absolute_position": "g1a_family_absolute_min_topology",
        "relative_structural_position": "g1a_family_structural_min_topology",
        "lexical_semantic_content": "g1a_family_lexical_min_topology",
    }
    source_hypotheses = {family: f"family:{family}" for family in PRIMARY}
    for family, q_name in q_names.items():
        topology_gates = {}
        family_boundary_diagnostics[family] = {}
        for topology in ["split", "broad"]:
            row = primary_layer["topology_family"][topology][family]
            point_row, bootstrap_row = row["point"], row["bootstrap"]
            selectivity_ci95 = bootstrap_row["selectivity_margin"]["ci95"]
            selectivity_lower = None if selectivity_ci95 is None else selectivity_ci95[0]
            point_diagnostics = {
                "assigned_recovery": threshold_boundary_diagnostic(
                    point_row["assigned_recovery"], 0.75, tolerance=tolerance,
                    mc_endpoint_range=bootstrap_row["assigned_recovery"][
                        "point_mc_100_block_endpoint_range"]),
                "leakage": threshold_boundary_diagnostic(
                    point_row["leakage"], 0.55, tolerance=tolerance,
                    mc_endpoint_range=bootstrap_row["leakage"][
                        "point_mc_100_block_endpoint_range"]),
                "selectivity_margin": threshold_boundary_diagnostic(
                    point_row["selectivity_margin"], 0.20, tolerance=tolerance,
                    mc_endpoint_range=bootstrap_row["selectivity_margin"][
                        "point_mc_100_block_endpoint_range"]),
                "selectivity_ci95_lower": threshold_boundary_diagnostic(
                    selectivity_lower, 0.0, tolerance=tolerance,
                    mc_endpoint_range=bootstrap_row["selectivity_margin"][
                        "ci95_lower_mc_100_block_endpoint_range"]),
            }
            family_boundary_diagnostics[family][topology] = point_diagnostics
            topology_gates[topology] = {
                "assigned_recovery_at_least_0p75": bool(
                    point_row["assigned_recovery"] is not None
                    and float(point_row["assigned_recovery"]) >= 0.75
                    and not point_diagnostics["assigned_recovery"]["boundary_proximity"]),
                "leakage_at_most_0p55": bool(
                    point_row["leakage"] is not None and float(point_row["leakage"]) <= 0.55
                    and not point_diagnostics["leakage"]["boundary_proximity"]),
                "selectivity_at_least_0p20": bool(
                    point_row["selectivity_margin"] is not None
                    and float(point_row["selectivity_margin"]) >= 0.20
                    and not point_diagnostics["selectivity_margin"]["boundary_proximity"]),
                "selectivity_lower95_positive": bool(
                    selectivity_lower is not None
                    and float(selectivity_lower) > 0.0
                    and not point_diagnostics["selectivity_ci95_lower"]["boundary_proximity"]),
            }
            topology_gates[topology]["passes"] = all(topology_gates[topology].values())
        qvalue = qvalues[q_name]
        q_boundary = threshold_boundary_diagnostic(
            qvalue, 0.05, tolerance=tolerance,
            mc_not_applicable_reason=(
                "BH q-value has no registered bootstrap endpoint; its source randomization "
                "diagnostic is reported separately"))
        family_gates[family] = {
            "topologies": topology_gates,
            "randomization_valid": bool(randomization[q_name]["valid"]),
            "bh_q_at_most_0p05": bool(
                qvalue is not None and float(qvalue) <= 0.05
                and not q_boundary["boundary_proximity"]),
            "bh_q_boundary_diagnostic": q_boundary,
            "source_direction_pass": source_hypotheses[family] not in reversal_failures,
        }
        family_gates[family]["passes"] = bool(
            all(row["passes"] for row in topology_gates.values())
            and family_gates[family]["randomization_valid"]
            and family_gates[family]["bh_q_at_most_0p05"]
            and family_gates[family]["source_direction_pass"])
    all_families_pass = all(row["passes"] for row in family_gates.values())
    fourth_name = "g1a_split_minus_broad_positional"
    fourth_q_boundary = threshold_boundary_diagnostic(
        qvalues[fourth_name], 0.05, tolerance=tolerance,
        mc_not_applicable_reason=(
            "BH q-value has no registered bootstrap endpoint; its source randomization "
            "diagnostic is reported separately"))
    fourth_inference_gate = {
        "randomization_valid": bool(randomization[fourth_name]["valid"]),
        "bh_q_at_most_0p05": bool(
            qvalues[fourth_name] is not None
            and float(qvalues[fourth_name]) <= 0.05
            and not fourth_q_boundary["boundary_proximity"]),
        "bh_q_boundary_diagnostic": fourth_q_boundary,
    }
    fourth_inference_gate["passes"] = bool(
        fourth_inference_gate["randomization_valid"]
        and fourth_inference_gate["bh_q_at_most_0p05"])
    family_boundary_failures = sorted(
        f"{family}:{topology}"
        for family, topologies in family_boundary_diagnostics.items()
        for topology, diagnostics in topologies.items()
        if any(not row["valid"] or row["boundary_proximity"]
               for row in diagnostics.values()))
    q_boundary_failures = sorted([
        *[f"{family}:bh_q" for family, row in family_gates.items()
          if (not row["bh_q_boundary_diagnostic"]["valid"]
              or row["bh_q_boundary_diagnostic"]["boundary_proximity"])],
        *(["split_minus_broad:bh_q"]
          if (not fourth_q_boundary["valid"]
              or fourth_q_boundary["boundary_proximity"]) else []),
    ])
    complete_case_gate = (
        primary_layer["finite_complete_cases"]
        >= int(config["minimum_complete_draws"]))
    topology_selection = {
        "split": bool(complete_case_gate
                      and all_families_pass
                      and fourth_inference_gate["passes"]
                      and fourth_bootstrap["lower95"] is not None
                      and float(fourth_bootstrap["lower95"]) >= 0.05
                      and not fourth_boundary["lower95"]["boundary_proximity"]),
        "broad": bool(complete_case_gate
                      and all_families_pass
                      and fourth_inference_gate["passes"]
                      and fourth_bootstrap["upper95"] is not None
                      and float(fourth_bootstrap["upper95"]) < 0.05
                      and not fourth_boundary["upper95"]["boundary_proximity"]),
    }
    reasons = ["mandatory G1a randomization hypotheses invalid under frozen minimum-cluster/nonzero-cluster rules"]
    if not complete_case_gate:
        reasons.append(
            f"global complete cases {primary_layer['finite_complete_cases']} "
            f"< {config['minimum_complete_draws']}")
    if reversal_failures:
        reasons.append(f"point source reversal for: {', '.join(reversal_failures)}")
    if any(row["boundary_proximity"] for row in fourth_boundary.values()):
        reasons.append("split/broad positional endpoint is within the frozen 0.01 boundary tolerance")
    if family_boundary_failures:
        reasons.append("one or more family/topology selectivity CI endpoints are absent or within the frozen boundary tolerance")
    if q_boundary_failures:
        reasons.append("one or more G1 BH-q endpoints are absent or within the frozen boundary tolerance")
    inferentially_valid = bool(
        all(row["valid"] for row in randomization.values())
        and all(value is not None and math.isfinite(float(value)) for value in qvalues.values())
        and primary_layer["finite_complete_cases"] >= int(config["minimum_complete_draws"])
        and not reversal_failures
        and not family_boundary_failures
        and not q_boundary_failures
        and all(row["valid"] and not row["boundary_proximity"]
                for row in fourth_boundary.values()))
    g1a = {"outcome": "equivocal", "reasons": reasons,
           "pvalues": pvalues, "bh_qvalues": qvalues, "randomization": randomization,
           "source_reversal_failures": reversal_failures,
           "boundary_diagnostics": {
               "split_minus_broad_positional": fourth_boundary,
               "bh_q": {
                   **{family: row["bh_q_boundary_diagnostic"]
                      for family, row in family_gates.items()},
                   "split_minus_broad_positional": fourth_q_boundary,
               },
               "family_topology_thresholds": family_boundary_diagnostics,
           },
           "parent_gate_evaluation": {
               "family_gates": family_gates,
               "split_minus_broad_inference_gate": fourth_inference_gate,
               "topology_selection": topology_selection,
               "supported_topologies": [name for name, passes in topology_selection.items() if passes],
               "inferentially_valid": inferentially_valid,
               "no_topology_selected": not any(topology_selection.values()),
           },
           "supported_negative_diagnostic": negative_gate,
           "original_G1": "equivocal"}
    return {"layers": layers, "G1a_postscore_amended": g1a}


def merge_stability(config: dict[str, Any], run_root: Path, firewall: Any,
                    completion_bundle_sha256: str,
                    config_sha256: str) -> tuple[dict[str, Any], dict[str, dict[int, float | None]]]:
    stage = run_root / "stability"
    baseline_path = run_root / "baseline/baseline_bundle.pkl"
    point, rows, errors, artifacts = load_series(stage, int(config["draws"]), firewall,
                                                 completion_bundle_sha256, config_sha256,
                                                 required_attestations={
                                                     baseline_path: sha256_file(baseline_path)})
    finite_rows = [row for row in rows if row.get("finite") is True]
    families = list(PRIMARY)
    draws = {family: {int(row["draw_id"]): row["families"][family]["learned_stability_loss"] for row in finite_rows}
             for family in families}
    summary = {family: {"point": point["families"][family], "bootstrap": percentile(list(values.values()))}
               for family, values in draws.items()}
    primary_pairs = sorted(point["families"][families[0]]["pair_means"])
    pair_overall = {}
    for pair in primary_pairs:
        values = [point["families"][family]["pair_means"][pair] for family in families]
        pair_overall[pair] = (float(np.mean(values)) if all(value is not None and math.isfinite(float(value)) for value in values)
                              else None)
    overall_values = [point["families"][family]["learned_mean_pairwise_cka"] for family in families]
    overall = (float(np.mean(overall_values))
               if all(value is not None and math.isfinite(float(value)) for value in overall_values) else None)
    draw_ids = [int(row["draw_id"]) for row in finite_rows]
    overall_draws = [float(np.mean([
        row["families"][family]["learned_mean_pairwise_cka"] for family in families]))
        for row in finite_rows]
    pair_draws = {
        pair: [float(np.mean([
            row["families"][family]["pair_means"][pair] for family in families]))
            for row in finite_rows]
        for pair in primary_pairs
    }
    tolerance = float(config["boundary_tolerance"])
    boundary_diagnostics = {
        "overall_mean": threshold_boundary_diagnostic(
            overall, 0.80, tolerance=tolerance,
            mc_endpoint_range=block_mean_range(overall_draws, draw_ids)),
        "pair_overall_means": {
            pair: threshold_boundary_diagnostic(
                pair_overall[pair], 0.70, tolerance=tolerance,
                mc_endpoint_range=block_mean_range(pair_draws[pair], draw_ids))
            for pair in primary_pairs
        },
    }
    point_gate = {"overall_mean": overall, "pair_overall_means": pair_overall,
                  "boundary_diagnostics": boundary_diagnostics,
                  "overall_at_least_0p80": bool(
                      overall is not None and overall >= 0.80
                      and not boundary_diagnostics["overall_mean"]["boundary_proximity"]),
                  "every_pair_at_least_0p70": all(
                      value is not None and value >= 0.70
                      and not boundary_diagnostics["pair_overall_means"][pair]["boundary_proximity"]
                      for pair, value in pair_overall.items())}
    return {"families": summary, "serialized_draws": len(rows), "finite_complete_cases": len(finite_rows),
            "nonfinite_draw_ids": [int(row["draw_id"]) for row in rows if row.get("finite") is not True],
            "failed_draws": errors, "point_stability_gate": point_gate}, draws


def merge_g2(config: dict[str, Any], baseline: dict[str, Any], run_root: Path,
             stability: dict[str, Any], stability_draws: dict[str, dict[int, float | None]],
             firewall: Any, completion_bundle_sha256: str,
             config_sha256: str) -> dict[str, Any]:
    baseline_path = run_root / "baseline/baseline_bundle.pkl"
    baseline_attestation = {baseline_path: sha256_file(baseline_path)}
    raw_stage = run_root / "raw_refit/L3"
    raw_point, raw_rows, _, raw_artifacts = load_series(
        raw_stage, int(config["draws"]), firewall,
        completion_bundle_sha256, config_sha256,
        required_attestations=baseline_attestation)
    raw_by_id = {row["draw_id"]: row for row in raw_rows if row["result"].get("finite") is True}
    jobs = config["primary_checkpoints"]
    point_rows, draws_by_job = {}, {}
    for job in config["primary_checkpoints"] + config["descriptive_checkpoints"]:
        stage = run_root / "k2_refit" / job
        point, rows, errors, artifacts = load_series(stage, int(config["draws"]), firewall,
                                                     completion_bundle_sha256, config_sha256,
                                                     required_attestations=baseline_attestation)
        raw_point_path = raw_stage / "point.json"
        assert_attested_hash(point, raw_point_path,
                             raw_artifacts[str(raw_point_path)])
        for row in rows:
            raw_path = raw_stage / "draws" / f"{int(row['draw_id']):04d}.json"
            assert_attested_hash(row, raw_path, raw_artifacts[str(raw_path)])
        point_rows[job], draws_by_job[job] = point, {
            row["draw_id"]: row for row in rows if row["result"].get("finite") is True
        }

    direction_detail = {}
    for family in PRIMARY:
        margins = {job: point_rows[job]["result"]["families"][family]["selectivity_margin"] for job in jobs}
        signs = [int(np.sign(float(value))) for value in margins.values()
                 if value is not None and math.isfinite(float(value))]
        direction_boundary = {}
        for job in jobs:
            job_draw_ids = sorted(map(int, draws_by_job[job]))
            values = [float(draws_by_job[job][draw]["result"]["families"][family]["selectivity_margin"])
                      for draw in job_draw_ids]
            direction_boundary[job] = threshold_boundary_diagnostic(
                margins[job], 0.0, tolerance=float(config["boundary_tolerance"]),
                mc_endpoint_range=block_mean_range(values, job_draw_ids))
        direction_detail[family] = {
            "margins": margins, "signs": signs,
            "boundary_diagnostics": direction_boundary,
            "same_direction": bool(same_nonzero_direction(list(margins.values()))
                                   and all(row["valid"] and not row["boundary_proximity"]
                                           for row in direction_boundary.values())),
        }
    stability["point_stability_gate"]["selectivity_direction"] = direction_detail
    stability["point_stability_gate"]["selectivity_same_direction_all_families"] = all(
        row["same_direction"] for row in direction_detail.values())
    stability["point_stability_gate"]["passes"] = bool(
        stability["point_stability_gate"]["overall_at_least_0p80"]
        and stability["point_stability_gate"]["every_pair_at_least_0p70"]
        and stability["point_stability_gate"]["selectivity_same_direction_all_families"])

    coordinates: list[str] = []
    point_values: list[float] = []

    def add(name: str, value: float | None) -> None:
        coordinates.append(name)
        point_values.append(float("nan") if value is None else float(value))

    def difference(left: Any, right: Any) -> float | None:
        if left is None or right is None or not np.isfinite([left, right]).all():
            return None
        return float(left - right)

    eligible_sentinels = [task for task, row in baseline["sentinel_eligibility"].items() if row["eligible"]]
    point_roundtrip = raw_point["result"]["simple_roundtrip"]
    point_roundtrip_valid = all(row["passes"] for row in point_roundtrip.values())
    specificity = {}
    for job in config["primary_checkpoints"] + config["descriptive_checkpoints"]:
        stage = run_root / "specificity" / job
        require_bound_stage_files(
            stage, firewall, config_sha256=config_sha256,
            completion_bundle_sha256=completion_bundle_sha256,
            expected_files={"result_sha256": "specificity.json"})
        specificity[job] = read_json(firewall.attest(stage / "specificity.json"))
        assert_attested_hash(specificity[job], baseline_path,
                             baseline_attestation[baseline_path])
    for job in jobs:
        learned = point_rows[job]["result"]
        simple = raw_point["result"]["simple_c2"]
        for family in PRIMARY:
            add(f"A_sel:{job}:{family}", difference(learned["families"][family]["selectivity_margin"],
                                                     simple["families"][family]["selectivity_margin"])
                if point_roundtrip_valid else None)
            add(f"A_ret:{job}:{family}", difference(learned["families"][family]["assigned_recovery"],
                                                     simple["families"][family]["assigned_recovery"])
                if point_roundtrip_valid else None)
        for task in eligible_sentinels:
            add(f"A_col:{job}:{task}", difference(simple["sentinels"][task]["normalized_damage"],
                                                   learned["sentinels"][task]["normalized_damage"]))
        identity_valid = bool(specificity[job]["simple_identity_collateral"]["valid"])
        add(f"A_col:{job}:reconstruction_ce",
            -float(specificity[job]["ce_collateral"]["point"]) if identity_valid else None)
    stability_point = read_json(firewall.attest(run_root / "stability/point.json"))
    for family in PRIMARY:
        add(f"L_stab:{family}", stability_point["families"][family]["learned_stability_loss"])

    complete_ids = sorted(set(raw_by_id).intersection(*(set(draws_by_job[job]) for job in jobs)))
    bootstrap_rows = []
    bootstrap_ids: list[int] = []
    for index, draw in enumerate(complete_ids):
        raw = raw_by_id[draw]["result"]["simple_c2"]
        values = []
        valid = all(row["passes"] for row in raw_by_id[draw]["result"]["simple_roundtrip"].values())
        for job in jobs:
            learned = draws_by_job[job][draw]["result"]
            for family in PRIMARY:
                pairs = [(learned["families"][family]["selectivity_margin"], raw["families"][family]["selectivity_margin"]),
                         (learned["families"][family]["assigned_recovery"], raw["families"][family]["assigned_recovery"])]
                for left, right in pairs:
                    if left is None or right is None:
                        valid = False
                        break
                    values.append(float(left - right))
                if not valid:
                    break
            if not valid:
                break
            for task in eligible_sentinels:
                simple_damage = raw["sentinels"][task]["normalized_damage"]
                learned_damage = learned["sentinels"][task]["normalized_damage"]
                if simple_damage is None or learned_damage is None:
                    valid = False
                    break
                values.append(float(simple_damage - learned_damage))
            if not valid:
                break
            values.append(-float(specificity[job]["ce_collateral"]["draws"][draw]))
        if valid:
            for family in PRIMARY:
                value = stability_draws[family].get(draw)
                if value is None:
                    valid = False
                    break
                values.append(float(value))
        if valid and len(values) == len(coordinates) and np.isfinite(values).all():
            bootstrap_rows.append(values)
            bootstrap_ids.append(int(draw))
    bounds = None
    invalid_reason = None
    g2_mc = simultaneous_block_mc_diagnostics(point_values, bootstrap_rows,
                                               bootstrap_ids)
    if len(bootstrap_rows) >= int(config["minimum_complete_draws"]) and np.isfinite(point_values).all():
        lower, upper = simultaneous_bounds(point_values, np.asarray(bootstrap_rows))
        bounds = {name: {"point": point_values[i], "lower": float(lower[i]), "upper": float(upper[i])} for i, name in enumerate(coordinates)}
    else:
        invalid_reason = f"global complete cases {len(bootstrap_rows)} < {config['minimum_complete_draws']} or nonfinite point"
    equivalence = {}
    boundary_diagnostics: dict[str, Any] = {}
    tolerance = float(config["boundary_tolerance"])
    if bounds is not None:
        for index, name in enumerate(coordinates):
            if name.startswith("A_sel:"):
                simple_threshold, learned_threshold = 0.05, 0.05
            elif name.startswith("A_ret:") or name.startswith("A_col:"):
                simple_threshold, learned_threshold = 0.02, -0.02
            else:
                simple_threshold, learned_threshold = 0.05, None
            upper_mc = None if g2_mc is None else g2_mc["upper_endpoint_range"][index]
            lower_mc = None if g2_mc is None else g2_mc["lower_endpoint_range"][index]
            boundary_diagnostics[name] = {
                "simple_upper": threshold_boundary_diagnostic(
                    bounds[name]["upper"], simple_threshold, tolerance=tolerance,
                    mc_endpoint_range=upper_mc),
                "learned_lower": (None if learned_threshold is None else
                                    threshold_boundary_diagnostic(
                                        bounds[name]["lower"], learned_threshold,
                                        tolerance=tolerance, mc_endpoint_range=lower_mc)),
            }
        for job in jobs:
            family_pass = {}
            for family in PRIMARY:
                relevant_col = [bounds[f"A_col:{job}:{task}"]["upper"] <= 0.02 for task in eligible_sentinels]
                relevant_col.append(bounds[f"A_col:{job}:reconstruction_ce"]["upper"] <= 0.02)
                family_pass[family] = (bounds[f"A_sel:{job}:{family}"]["upper"] <= 0.05
                                       and bounds[f"A_ret:{job}:{family}"]["upper"] <= 0.02
                                       and all(relevant_col) and bounds[f"L_stab:{family}"]["upper"] <= 0.05)
            equivalence[job] = {"families": family_pass, "passing_families": sum(family_pass.values())}
    simple_boundary_failures = sorted(
        name for name, row in boundary_diagnostics.items()
        if row["simple_upper"]["boundary_proximity"])
    learned_boundary_failures = sorted(
        name for name, row in boundary_diagnostics.items()
        if row["learned_lower"] is not None and row["learned_lower"]["boundary_proximity"])
    g2_randomization = {
        job: {"valid": False, "p": None,
              "reason": "G2 macro hypothesis depends on four-group LinES C2 strata"}
        for job in jobs
    }
    g2_pvalues = {job: row["p"] for job, row in g2_randomization.items()}
    g2_qvalues = bh(g2_pvalues)
    g2_q_boundary_diagnostics = {
        job: threshold_boundary_diagnostic(
            g2_qvalues[job], 0.05, tolerance=tolerance,
            mc_not_applicable_reason=(
                "BH q-value is derived from a fixed 9,999-sign randomization "
                "family, not a 500-draw endpoint series"))
        for job in jobs
    }
    g2_randomization_all_valid = bool(all(
        row["valid"] and row["p"] is not None
        and g2_qvalues[job] is not None
        and g2_q_boundary_diagnostics[job]["valid"]
        and not g2_q_boundary_diagnostics[job]["boundary_proximity"]
        for job, row in g2_randomization.items()))
    g2_bh_all_pass = bool(
        g2_randomization_all_valid
        and all(float(g2_qvalues[job]) <= 0.05 for job in jobs))
    primary_specificity = primary_specificity_validity(specificity, jobs)
    simple_technical_evidence = {
        "global_bounds_present": bounds is not None,
        "baseline_selection_valid": not baseline["baseline_selection_failed"],
        "roundtrip_point_valid": point_roundtrip_valid,
        "counterfactual_all_valid": primary_specificity["counterfactual_all_valid"],
        "identity_collateral_all_valid": primary_specificity[
            "identity_collateral_all_valid"],
        "stability_point_gate_valid": bool(stability["point_stability_gate"]["passes"]),
        "no_simple_boundary_failures": not simple_boundary_failures,
    }
    simple_evidence_invalid = mandatory_evidence_invalid(simple_technical_evidence)
    simple_branch = bool(not simple_evidence_invalid
                         and all(row["passing_families"] >= 2 for row in equivalence.values()))
    learned_coordinate_gates = {}
    if bounds is not None:
        for job in jobs:
            family_rows = {}
            for family in PRIMARY:
                collateral_lower = [bounds[f"A_col:{job}:{task}"]["lower"] >= -0.02
                                    for task in eligible_sentinels]
                collateral_lower.append(bounds[f"A_col:{job}:reconstruction_ce"]["lower"] >= -0.02)
                family_rows[family] = {
                    "selectivity_lower_at_least_0p05": bounds[f"A_sel:{job}:{family}"]["lower"] >= 0.05,
                    "retention_lower_at_least_minus_0p02": bounds[f"A_ret:{job}:{family}"]["lower"] >= -0.02,
                    "collateral_lower_at_least_minus_0p02": all(collateral_lower),
                    "stability_upper_at_most_0p05": bounds[f"L_stab:{family}"]["upper"] <= 0.05,
                }
                family_rows[family]["passes"] = all(family_rows[family].values())
            learned_coordinate_gates[job] = family_rows
    learned_branch_evaluation = {
        "coordinate_gates": learned_coordinate_gates,
        "g2_randomization_all_valid": g2_randomization_all_valid,
        "g2_bh_all_pass": g2_bh_all_pass,
        "point_stability_pass": bool(stability["point_stability_gate"]["passes"]),
        "counterfactual_all_valid": all(bool(specificity[job]["counterfactual_gate_valid"])
                                          for job in jobs),
        "matched_k1_reconstruction_comparator_present": False,
        "g1_topology_supported": False,
        "existing_k2_failure_on_supported_topology": False,
        "simple_equivalence_failed": not simple_branch,
        "otherwise_valid_g2": False,
        "falsifiable_mapping_present": bool(all(
            specificity[job]["counterfactual_gate_valid"] for job in jobs)),
        "boundary_failures": learned_boundary_failures,
        "missing_evidence": ["matched_K1_checkpoint_and_FVU_comparator"],
        "passes": False,
    }
    collateral_noninferiority_by_job = collateral_noninferiority_gates(
        bounds, jobs, eligible_sentinels, learned_boundary_failures)
    k2_localization_gates: dict[str, dict[str, dict[str, Any]]] = {}
    for topology in ["split", "broad"]:
        k2_localization_gates[topology] = {}
        for job in jobs:
            k2_localization_gates[topology][job] = {}
            for family in PRIMARY:
                row = point_rows[job]["result"]["families"][family]
                job_draw_ids = sorted(map(int, draws_by_job[job]))
                mc_ranges = {
                    field: block_mean_range([
                        float(draws_by_job[job][draw]["result"]["families"][family][field])
                        for draw in job_draw_ids], job_draw_ids)
                    for field in ["assigned_recovery", "leakage", "selectivity_margin"]
                }
                k2_localization_gates[topology][job][family] = k2_localization_gate(
                    row, tolerance=float(config["boundary_tolerance"]),
                    mc_ranges=mc_ranges)
    existing_checkpoint_branch_evaluation = {
        "g1_supported_topologies": [],
        "k2_localization_recovery_leakage_gates": k2_localization_gates,
        "corresponding_k2_localization_recovery_leakage_pass": False,
        "counterfactual_all_valid": learned_branch_evaluation["counterfactual_all_valid"],
        "tier2_collateral_all_finite": bool(all(
            point_rows[job]["result"]["sentinels"][task]["normalized_damage"] is not None
            and math.isfinite(float(point_rows[job]["result"]["sentinels"][task]["normalized_damage"]))
            for job in jobs for task in eligible_sentinels)
            and all(specificity[job]["ce_collateral"]["point"] is not None
                    and math.isfinite(float(specificity[job]["ce_collateral"]["point"]))
                    for job in jobs)),
        "collateral_noninferiority_by_job": collateral_noninferiority_by_job,
        "collateral_noninferiority_all_pass": bool(
            all(row["passes"] for row in collateral_noninferiority_by_job.values())),
        "point_stability_pass": learned_branch_evaluation["point_stability_pass"],
        "matched_k1_fvu_gate_present": False,
        "missing_evidence": ["matched_K1_checkpoint_and_FVU_comparator"],
        "passes": False,
    }
    g2_superiority_inference_invalid = not all(
        bool(row["valid"]) and row["p"] is not None
        and g2_qvalues[job] is not None
        and g2_q_boundary_diagnostics[job]["valid"]
        and not g2_q_boundary_diagnostics[job]["boundary_proximity"]
        for job, row in g2_randomization.items())
    g2_primary_inference_invalid = bool(
        g2_superiority_inference_invalid or learned_boundary_failures)
    g2 = {"outcome": ("simple_equivalence" if simple_branch
                       and not g2_primary_inference_invalid else "equivocal"),
          "reasons": [], "global_coordinates": coordinates, "complete_case_draws": len(bootstrap_rows),
          "simultaneous_bounds": bounds, "invalid_reason": invalid_reason, "simple_equivalence": equivalence,
          "boundary_diagnostics": boundary_diagnostics,
          "simple_boundary_failures": simple_boundary_failures,
          "learned_boundary_failures": learned_boundary_failures,
          "mc_100_block_simultaneous_endpoint_ranges": g2_mc,
          "simple_branch_available": simple_branch, "learned_superiority_valid": False,
          "primary_inference_invalid": g2_primary_inference_invalid,
          "g2_superiority_inference_invalid": g2_superiority_inference_invalid,
          "learned_new_family_advantage": None,
          "learned_new_family_advantage_inference_valid": False,
          "simple_evidence_invalid": simple_evidence_invalid,
          "simple_technical_evidence": simple_technical_evidence,
          "existing_checkpoint_branch_evaluation": existing_checkpoint_branch_evaluation,
          "learned_model_branch_evaluation": learned_branch_evaluation,
          "g2_randomization": g2_randomization,
          "pvalues": g2_pvalues,
          "bh_qvalues": g2_qvalues,
          "bh_q_boundary_diagnostics": g2_q_boundary_diagnostics,
          "g2_bh_all_pass": g2_bh_all_pass,
          "counterfactual_gates": {job: specificity[job]["counterfactual_gate_valid"] for job in specificity},
          "simple_identity_collateral_gates": {job: specificity[job]["simple_identity_collateral"]["valid"]
                                                  for job in specificity},
          "simple_roundtrip_point_gate": {"valid": point_roundtrip_valid, "candidates": point_roundtrip},
          "point_stability_gate": stability["point_stability_gate"],
          "original_G2": "equivocal"}
    if baseline["baseline_selection_failed"]:
        g2["reasons"].append("calibration baseline selection failed")
    if invalid_reason:
        g2["reasons"].append(invalid_reason)
    if simple_boundary_failures or learned_boundary_failures:
        g2["reasons"].append("one or more G2 endpoints are within the frozen 0.01 decision-boundary tolerance")
    if g2_superiority_inference_invalid:
        g2["reasons"].append("one or more G2 superiority randomization hypotheses are invalid")
    g2["reasons"].append("learned branches unavailable because matched K=1 reconstruction comparator is absent")
    return g2


def main() -> None:
    global _FAILURE_ATTESTATION
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, default=ROOT / "configs/atlas_completion/analysis.json")
    parser.add_argument("--output", type=Path, default=ROOT / "results/atlas/completion_v1")
    args = parser.parse_args()
    started = time.monotonic()
    started_utc = utc_now()
    completion_freeze = require_frozen_completion_config(args.config)
    config = read_json(args.config)
    if args.output.resolve() != (ROOT / "results/atlas/completion_v1").resolve():
        raise PermissionError("completion promotion path must equal the frozen canonical output root")
    source_root, run_root = ROOT / config["source_run_root"], ROOT / config["run_root"]
    firewall = default_firewall(source_root, run_root)
    _FAILURE_ATTESTATION = firewall.attestation
    attest_completion_freeze_record(firewall, completion_freeze)
    firewall.register_root(ROOT / "data/atlas_completion_v1")
    firewall.register_root(args.output)
    config_path = firewall.attest(args.config)
    bundle_sha = completion_freeze["bundle_sha256"]
    config_sha = sha256_file(config_path)
    require_bound_stage_files(
        run_root / "baseline", firewall, config_sha256=config_sha,
        completion_bundle_sha256=bundle_sha,
        expected_files={"result_sha256": "baseline.json",
                        "bundle_sha256": "baseline_bundle.pkl"})
    with firewall.attest(run_root / "baseline/baseline_bundle.pkl").open("rb") as handle:
        baseline = pickle.load(handle)
    if baseline.get("completion_bundle_sha256") != completion_freeze["bundle_sha256"]:
        raise RuntimeError("baseline bundle is not bound to the completion freeze")
    args.output.mkdir(parents=True, exist_ok=True)
    if any(args.output.iterdir()):
        raise RuntimeError(f"promoted completion output is create-once: {args.output}")
    raw = merge_raw(config, baseline, source_root, run_root, firewall, bundle_sha, config_sha)
    stability, stability_draws = merge_stability(config, run_root, firewall, bundle_sha, config_sha)
    g2 = merge_g2(config, baseline, run_root, stability, stability_draws, firewall, bundle_sha,
                  config_sha)
    negative = raw["G1a_postscore_amended"]["supported_negative_diagnostic"]
    negative["learned_new_family_advantage"] = g2["learned_new_family_advantage"]
    negative["no_learned_new_family_advantage_valid"] = bool(
        g2["learned_new_family_advantage_inference_valid"]
        and g2["learned_new_family_advantage"] is False)
    negative["supported_negative_all_gates"] = bool(
        negative["raw_negative_requirements_pass"]
        and negative["no_learned_new_family_advantage_valid"])
    supported_topologies = raw["G1a_postscore_amended"]["parent_gate_evaluation"]["supported_topologies"]
    g2["existing_checkpoint_branch_evaluation"]["g1_supported_topologies"] = supported_topologies
    corresponding_k2_pass = bool(
        supported_topologies and all(
            g2["existing_checkpoint_branch_evaluation"]
              ["k2_localization_recovery_leakage_gates"][topology][job][family]["passes"]
            for topology in supported_topologies
            for job in config["primary_checkpoints"]
            for family in PRIMARY))
    g2["existing_checkpoint_branch_evaluation"][
        "corresponding_k2_localization_recovery_leakage_pass"] = corresponding_k2_pass
    g2["existing_checkpoint_branch_evaluation"]["passes"] = bool(
        supported_topologies
        and corresponding_k2_pass
        and g2["existing_checkpoint_branch_evaluation"]["counterfactual_all_valid"]
        and g2["existing_checkpoint_branch_evaluation"]["tier2_collateral_all_finite"]
        and g2["existing_checkpoint_branch_evaluation"]["collateral_noninferiority_all_pass"]
        and g2["existing_checkpoint_branch_evaluation"]["point_stability_pass"]
        and g2["existing_checkpoint_branch_evaluation"]["matched_k1_fvu_gate_present"])
    learned_eval = g2["learned_model_branch_evaluation"]
    learned_eval["g1_topology_supported"] = bool(supported_topologies)
    learned_eval["existing_k2_failure_on_supported_topology"] = bool(
        supported_topologies and not corresponding_k2_pass)
    learned_eval["simple_equivalence_failed"] = not g2["simple_branch_available"]
    learned_eval["otherwise_valid_g2"] = bool(
        learned_eval["g2_randomization_all_valid"]
        and learned_eval["g2_bh_all_pass"]
        and learned_eval["coordinate_gates"]
        and all(row["passes"]
                for job_rows in learned_eval["coordinate_gates"].values()
                for row in job_rows.values())
        and learned_eval["point_stability_pass"]
        and learned_eval["counterfactual_all_valid"]
        and not learned_eval["boundary_failures"])
    learned_eval["passes"] = bool(
        learned_eval["g1_topology_supported"]
        and learned_eval["existing_k2_failure_on_supported_topology"]
        and learned_eval["simple_equivalence_failed"]
        and learned_eval["otherwise_valid_g2"]
        and learned_eval["falsifiable_mapping_present"]
        and learned_eval["matched_k1_reconstruction_comparator_present"])
    preflight = read_json(firewall.attest(ROOT / "data/atlas_completion_v1/preflight.json"))
    decision = {"planning_decision_v2": "equivocal_no_decision", "training_warranted": False,
                "reasons": ["known manifest-only minimum-cluster invalidity has highest precedence",
                            *raw["G1a_postscore_amended"]["reasons"], *g2["reasons"]],
                "original_architecture_decision": "equivocal_no_decision"}
    result = {"schema_version": "atlas_completion_results_v1", "evidence_class": EVIDENCE_CLASS,
              "parent_bundle_sha256": config["parent_bundle_sha256"], "preflight": preflight,
              "completion_bundle_sha256": completion_freeze["bundle_sha256"],
              "config_sha256": config_sha, "resolved_config": config,
              "resolved_arguments": {"output": str(args.output.resolve())},
              "seed_provenance": seed_provenance(
                  config,
                  contract="all inferential derived seeds are bound in merged leaf artifacts"),
              "device": None, "started_utc": started_utc, "ended_utc": utc_now(),
              "elapsed_sec": time.monotonic() - started,
              "environment": runtime_environment(None),
              "baseline": {"selected": baseline["selected_simple_baseline"], "selection_failed": baseline["baseline_selection_failed"]},
              "raw": raw, "stability": stability, "G2a_postscore_amended": g2, "decision": decision,
              "input_attestation": firewall.attestation}
    result_path = args.output / "completion_results.json"
    atomic_write_json(result_path, result)
    extension_after = verify_completion_freeze()
    verify_attestation_current(firewall.attestation)
    elapsed_sec = time.monotonic() - started
    write_terminal(args.output, complete=True, payload={"schema_version": "atlas_completion_results_complete_v1",
                                                        "result_sha256": sha256_file(result_path),
                                                        "config_sha256": config_sha,
                                                        "resolved_config": config,
                                                        "resolved_arguments": result["resolved_arguments"],
                                                        "seed_provenance": result["seed_provenance"],
                                                        "device": None,
                                                        "started_utc": started_utc,
                                                        "environment": runtime_environment(None),
                                                        "resource_accounting": process_resource_accounting(
                                                            args.output, elapsed_sec=elapsed_sec,
                                                            device=None),
                                                        "completion_bundle_sha256": completion_freeze["bundle_sha256"],
                                                        "parent_bundle_reverified_after_stage_sha256": config["parent_bundle_sha256"],
                                                        "completion_bundle_reverified_after_stage_sha256": extension_after["bundle_sha256"],
                                                        "planning_decision_v2": decision["planning_decision_v2"],
                                                        "input_attestation": firewall.attestation})
    print(json.dumps({"output": str(result_path), "G1a": raw["G1a_postscore_amended"]["outcome"],
                      "G2a": g2["outcome"], "decision": decision["planning_decision_v2"]}, indent=2))


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        write_failure_terminal(ROOT / "results/atlas/completion_v1",
                               stop_code="completion_merge_unrecoverable_failure",
                               failed_gate="G1a_G2a_merge", error=exc,
                               input_attestation=_FAILURE_ATTESTATION)
        raise
