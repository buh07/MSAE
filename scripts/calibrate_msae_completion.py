#!/usr/bin/env python3
"""Calibration-only Tier-1/Tier-2 eligibility and baseline selection."""

from __future__ import annotations

import argparse
import json
import math
import pickle
import time
from pathlib import Path
from typing import Any

import numpy as np

from msa_completion_common import (EVIDENCE_CLASS, ROOT, atomic_write_bytes,
                                   atomic_write_json,
                                   attest_completion_freeze_record, chance_score,
                                   default_firewall, deterministic_seed,
                                   draw_group_multiplicities_rng,
                                   fit_weighted_ridge_grid_torch,
                                   fit_weighted_ridge_torch, load_activation,
                                   load_row_file, macro_f1, project_complement,
                                   project_coords, read_json, runtime_environment,
                                   process_resource_accounting,
                                   require_frozen_completion_config, sha256_file,
                                   seed_provenance,
                                   source_equal_score, utc_now,
                                   verify_parent_raw_calibration,
                                   verify_parent_transform_roles,
                                   verify_parent_freeze_attested,
                                   verify_attestation_current,
                                   verify_completion_freeze,
                                   validated_cuda_environment,
                                   weights_from_multiplicities, write_terminal)
from msa_completion_common import write_failure_terminal
from merge_msae_refit import threshold_boundary_diagnostic
from run_msae_refit_worker import family_rows, rep_matrix, score_recovery


PRIMARY = {
    "absolute_position": ["abs_pos_16", "abs_pos_8"],
    "relative_structural_position": ["relative_quartile", "head_signed_distance", "dependency_depth", "boundary_state"],
    "lexical_semantic_content": ["token_identity_256", "lemma_identity_256", "ner_coarse"],
}
_FAILURE_ATTESTATION: dict[str, Any] = {}


def numerical_rank(matrix: np.ndarray) -> tuple[int, float]:
    """Return the RFC numerical rank and its explicit SVD tolerance."""

    original = np.asarray(matrix)
    if not np.issubdtype(original.dtype, np.floating):
        raise TypeError("numerical-rank matrix must be floating point")
    singular = np.linalg.svd(original.astype(np.float64), compute_uv=False)
    largest = float(singular[0]) if len(singular) else 0.0
    tolerance = max(original.shape, default=0) * np.finfo(original.dtype).eps * largest
    return int(np.sum(singular > tolerance)), float(tolerance)


def select_candidate(candidate_results: dict[str, dict[str, Any]]) -> tuple[str, bool, dict[str, Any]]:
    """Apply score, lower-fitted-rank, then ID tie breakers exactly in order."""

    valid = [(name, row) for name, row in candidate_results.items() if row["selection_pass"]]
    if not valid:
        return "projection_broad16", True, {"admissible": [], "score_tied": [],
                                             "rank_tied": [], "fallback": True}
    best = max(float(row["tier1_macro_selectivity"]) for _, row in valid)
    score_tied = [(name, row) for name, row in valid
                  if best - float(row["tier1_macro_selectivity"]) <= 0.01]
    lowest_rank = min(int(row["fitted_rank_total"]) for _, row in score_tied)
    rank_tied = sorted(name for name, row in score_tied
                       if int(row["fitted_rank_total"]) == lowest_rank)
    return rank_tied[0], False, {
        "admissible": sorted(name for name, _ in valid),
        "best_macro_selectivity": best,
        "score_tied": sorted(name for name, _ in score_tied),
        "lowest_fitted_rank_total": lowest_rank,
        "rank_tied": rank_tied,
        "fallback": False,
    }


def candidate_selection_boundaries(
        family_retention: dict[str, float | None],
        collateral: dict[str, dict[str, Any]],
        config: dict[str, Any]) -> dict[str, dict[str, dict[str, Any]]]:
    point_only_reason = (
        "calibration candidate selection is a fixed point endpoint; "
        "no registered draw-level endpoint series exists")
    return {
        "tier1_family_assigned_recovery": {
            family: threshold_boundary_diagnostic(
                family_retention[family], 0.65,
                tolerance=float(config["boundary_tolerance"]),
                mc_not_applicable_reason=point_only_reason)
            for family in PRIMARY
        },
        "tier2_sentinel_degradation": {
            task: threshold_boundary_diagnostic(
                collateral[task]["degradation"],
                float(config["sentinel_max_degradation"]),
                tolerance=float(config["boundary_tolerance"]),
                mc_not_applicable_reason=point_only_reason)
            for task in config["sentinels"]
        },
    }


def completion_rows(path: Path, firewall: Any, role: str) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    resolved = firewall.attest(path, role=role)
    items = [json.loads(line) for line in resolved.read_text().splitlines()]
    return (np.asarray([row["activation_row"] for row in items], dtype=np.int64),
            np.asarray([row["label"] for row in items], dtype=str),
            np.asarray([row["source"] for row in items], dtype=str),
            np.asarray([row["document_group"] for row in items], dtype=str))


def choose(models: list[Any], x: np.ndarray, y: np.ndarray, alphas: list[float], tie: float) -> tuple[Any, dict[str, float]]:
    scores = [macro_f1(y, model.predict(x)) for model in models]
    best = max(scores)
    eligible = [i for i, value in enumerate(scores) if best - value <= tie]
    index = max(eligible, key=lambda i: alphas[i])
    return models[index], {str(alpha): value for alpha, value in zip(alphas, scores, strict=True)}


def fixed_probe_eligibility(*, task: str, y_fit: np.ndarray, source_fit: np.ndarray,
                            y_cal: np.ndarray, pred_cal: np.ndarray, source_cal: np.ndarray,
                            group_cal: np.ndarray, config: dict[str, Any], stage: str) -> dict[str, Any]:
    sources = sorted(np.unique(source_cal).tolist())
    draws: list[float | None] = []
    rng = np.random.Generator(np.random.PCG64(
        deterministic_seed(config["seed"], stage, task, 0)))
    for draw in range(int(config["draws"])):
        mult = draw_group_multiplicities_rng(source_cal, group_cal, rng)
        weights = weights_from_multiplicities(source_cal, group_cal, mult)
        source_gaps = []
        valid = True
        for source in sources:
            cmask = source_cal == source
            if weights[cmask].sum() <= 0:
                valid = False
                break
            try:
                raw = macro_f1(y_cal[cmask], pred_cal[cmask], weights[cmask])
                # Discovery and evaluation intentionally use disjoint datasets.
                # The fitted prior is therefore the full discovery fit
                # distribution; only evaluation is source-stratified.
                chance = chance_score(y_fit, y_cal[cmask], None, weights[cmask])
            except ValueError:
                valid = False
                break
            source_gaps.append(raw - chance)
        draws.append(float(np.mean(source_gaps)) if valid and np.isfinite(source_gaps).all() else None)
    finite = np.asarray([value for value in draws if value is not None and math.isfinite(value)], dtype=float)
    if len(finite) >= 2:
        se = float(np.std(finite, ddof=1))
        lcb = float(np.quantile(finite, 0.025))
    else:
        se, lcb = None, None
    threshold = None if se is None else max(float(config["eligibility_floor"]), 2 * se)
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
        retained_se = float(np.std(retained, ddof=1))
        retained_lcb = float(np.quantile(retained, 0.025))
        block_margins.append(
            retained_lcb - max(float(config["eligibility_floor"]),
                               2 * retained_se))
    endpoint_range = float(np.ptp(block_margins)) if len(block_margins) == 5 else None
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
    return {"eligible": bool(eligible), "finite_draws": len(finite), "requested_draws": config["draws"],
            "se_ddof1": se, "lcb_2p5": lcb,
            "threshold": threshold, "eligibility_margin": margin,
            "boundary_diagnostic": boundary,
            "draws": draws,
            "point_raw_minus_chance": float(np.mean(finite)) if len(finite) else None,
            "sources": sources, "nonfinite_draws": [i for i, value in enumerate(draws) if value is None or not math.isfinite(value)]}


def candidate_matrix(x: np.ndarray, bundle: dict[str, Any], candidate: str, mapped: str) -> np.ndarray:
    if candidate == "projection_broad16":
        basis = bundle["bases"]["broad_position"]
    elif candidate == "projection_split8_8":
        basis = bundle["bases"]["split_position_joint"]
    elif candidate == "pca16_complement":
        basis = bundle["bases"]["pca16"]
    else:
        raise KeyError(candidate)
    return project_coords(x, basis) if mapped == "position" else project_complement(x, basis)


def rep_array(source_run_root: Path, job: str, role: str, rep: str, firewall: Any) -> np.ndarray:
    if role not in {"discovery", "calibration"}:
        raise PermissionError(f"baseline transform role is not calibration-only: {role}")
    verify_parent_transform_roles(
        source_run_root, job, ["discovery", "calibration"], firewall)
    path = firewall.attest(source_run_root / "k2_transforms" / job / role / f"{rep}.float16.npy", role=role)
    return np.load(path, mmap_mode="r")


def main() -> None:
    global _FAILURE_ATTESTATION
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, default=ROOT / "configs/atlas_completion/analysis.json")
    parser.add_argument("--manifests", type=Path, default=ROOT / "data/atlas_completion_v1")
    parser.add_argument("--output", type=Path, default=ROOT / "pilot_runs/20260801_atlas_completion_v1/baseline")
    parser.add_argument("--device", default="cuda:0")
    args = parser.parse_args()
    started = time.monotonic()
    started_utc = utc_now()
    completion_freeze = require_frozen_completion_config(args.config)
    config = read_json(args.config)
    canonical_manifests = (ROOT / "data/atlas_completion_v1").resolve()
    canonical_output = (ROOT / config["run_root"] / "baseline").resolve()
    if args.manifests.resolve() != canonical_manifests or args.output.resolve() != canonical_output:
        raise PermissionError("score-bearing baseline paths must equal the frozen canonical manifest/output roots")
    source_run_root = ROOT / config["source_run_root"]
    firewall = default_firewall(source_run_root, args.output.parents[0])
    _FAILURE_ATTESTATION = firewall.attestation
    attest_completion_freeze_record(firewall, completion_freeze)
    launch_environment = validated_cuda_environment(args.device)
    firewall.register_root(args.manifests)
    firewall.register_root(args.output)
    config_path = firewall.attest(args.config)
    manifest = read_json(firewall.attest(args.manifests / "tier2_manifest.json"))
    firewall.attest(args.manifests / "MEASUREMENT_COMPLETE.json")
    args.output.mkdir(parents=True, exist_ok=True)
    if any(args.output.iterdir()):
        raise RuntimeError(f"baseline output must be empty/create-once: {args.output}")

    # Parent freeze is verified before any scoring.  Its own exact bundle files
    # are trusted and attested via the parent marker.
    parent = verify_parent_freeze_attested(
        firewall, ["discovery", "calibration"])
    if parent["bundle_sha256"] != config["parent_bundle_sha256"]:
        raise RuntimeError("parent freeze digest mismatch")
    firewall.attest(ROOT / "configs/atlas/freeze_record.json")

    discovery = load_activation("discovery", 3, source_run_root, firewall)
    calibration = load_activation("calibration", 3, source_run_root, firewall)
    verify_parent_raw_calibration(source_run_root, firewall)
    bundle_path = firewall.attest(ROOT / "results/atlas/raw_v1/L3_calibration_bundle.pkl")
    freeze_path = firewall.attest(ROOT / "results/atlas/raw_v1/L3_calibration_freeze.json")
    with bundle_path.open("rb") as handle:
        raw_bundle = pickle.load(handle)
    parent_calibration = read_json(freeze_path)
    mean, scale = raw_bundle["mean"], raw_bundle["scale"]
    alphas = list(map(float, config["ridge_alphas"]))
    tie = float(config["alpha_tie"])

    tier1_manifest = read_json(firewall.attest(ROOT / "configs/atlas/task_row_manifest.json"))
    tier1_eligibility: dict[str, Any] = {}
    tier1_rows: dict[str, dict[str, tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]]] = {
        "discovery": {}, "calibration": {}}
    exact_raw_models: dict[str, Any] = {}
    for family, tasks in PRIMARY.items():
        for task in tasks:
            dr, dy, ds, dg = load_row_file(ROOT / tier1_manifest["roles"]["discovery"][task]["path"], discovery, firewall, role="discovery")
            cr, cy, cs, cg = load_row_file(ROOT / tier1_manifest["roles"]["calibration"][task]["path"], calibration, firewall, role="calibration")
            tier1_rows["discovery"][task] = (dr, dy, ds, dg)
            tier1_rows["calibration"][task] = (cr, cy, cs, cg)
            dx = (np.asarray(discovery.x[dr], np.float32) - mean) / scale
            cx = (np.asarray(calibration.x[cr], np.float32) - mean) / scale
            exact_raw_models[task] = fit_weighted_ridge_torch(
                dx, dy, np.ones(len(dy)), float(parent_calibration["raw_alpha"][task]), args.device)
            pred = exact_raw_models[task].predict(cx)
            tier1_eligibility[task] = fixed_probe_eligibility(task=task, y_fit=dy, source_fit=ds, y_cal=cy,
                                                               pred_cal=pred, source_cal=cs, group_cal=cg,
                                                               config=config, stage="tier1_eligibility")

    sentinel_results: dict[str, Any] = {}
    sentinel_alphas: dict[str, Any] = {"raw": {}, "simple": {}, "k2": {}}
    sentinel_rows: dict[str, dict[str, tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]]] = {"discovery": {}, "calibration": {}}
    for task in config["sentinels"]:
        for role in ["discovery", "calibration"]:
            spec = manifest["roles"][role][task]
            sentinel_rows[role][task] = completion_rows(ROOT / spec["path"], firewall, role)
        dr, dy, ds, _ = sentinel_rows["discovery"][task]
        cr, cy, cs, cg = sentinel_rows["calibration"][task]
        dx = (np.asarray(discovery.x[dr], np.float32) - mean) / scale
        cx = (np.asarray(calibration.x[cr], np.float32) - mean) / scale
        models = fit_weighted_ridge_grid_torch(dx, dy, np.ones(len(dy)), alphas, args.device)
        raw_model, table = choose(models, cx, cy, alphas, tie)
        pred = raw_model.predict(cx)
        eligibility = fixed_probe_eligibility(task=task, y_fit=dy, source_fit=ds, y_cal=cy, pred_cal=pred,
                                              source_cal=cs, group_cal=cg, config=config, stage="sentinel_eligibility")
        sentinel_alphas["raw"][task] = raw_model.alpha
        sentinel_results[task] = {"eligibility": eligibility, "raw_alpha_grid": table,
                                  "raw_macro_f1": source_equal_score(cy, pred, cs, np.ones(len(cy)))}

    candidates = ["projection_broad16", "projection_split8_8", "pca16_complement"]
    candidate_results: dict[str, Any] = {}
    for candidate in candidates:
        sentinel_alphas["simple"][candidate] = {}
        collateral: dict[str, Any] = {}
        roundtrip_errors = []
        for task in config["sentinels"]:
            mapped = config["sentinel_mapping"][task]
            dr, dy, _, _ = sentinel_rows["discovery"][task]
            cr, cy, cs, _ = sentinel_rows["calibration"][task]
            dx_raw = (np.asarray(discovery.x[dr], np.float32) - mean) / scale
            cx_raw = (np.asarray(calibration.x[cr], np.float32) - mean) / scale
            dx = candidate_matrix(dx_raw, raw_bundle, candidate, mapped)
            cx = candidate_matrix(cx_raw, raw_bundle, candidate, mapped)
            models = fit_weighted_ridge_grid_torch(dx, dy, np.ones(len(dy)), alphas, args.device)
            model, table = choose(models, cx, cy, alphas, tie)
            component_f1 = source_equal_score(cy, model.predict(cx), cs, np.ones(len(cy)))
            raw_f1 = sentinel_results[task]["raw_macro_f1"]
            degradation = None if component_f1 is None or raw_f1 is None else float(raw_f1 - component_f1)
            sentinel_alphas["simple"][candidate][task] = model.alpha
            collateral[task] = {"mapped_component": mapped, "alpha": model.alpha, "alpha_grid": table,
                                "component_macro_f1": component_f1, "raw_macro_f1": raw_f1, "degradation": degradation}
        # One deterministic matrix per candidate is sufficient for the exact projection identity.
        sample = (np.asarray(calibration.x[: min(4096, len(calibration.x))], np.float32) - mean) / scale
        if candidate == "projection_broad16":
            basis = raw_bundle["bases"]["broad_position"]
        elif candidate == "projection_split8_8":
            basis = raw_bundle["bases"]["split_position_joint"]
        else:
            basis = raw_bundle["bases"]["pca16"]
        # The lower-rank tie rule compares the two registered float32 linear
        # feature operators, not an unregistered row subset whose realized rank
        # can vary with sample composition.
        basis32 = np.asarray(basis, dtype=np.float32)
        complement_operator = (np.eye(basis32.shape[0], dtype=np.float32)
                               - basis32 @ basis32.T)
        positional_rank, positional_tolerance = numerical_rank(basis32)
        complement_rank, complement_tolerance = numerical_rank(complement_operator)
        reconstructed = (sample @ basis) @ basis.T + project_complement(sample, basis)
        roundtrip_errors.append(float(np.max(np.linalg.norm(reconstructed - sample, axis=1) / np.maximum(np.linalg.norm(sample, axis=1), 1e-12))))
        mapping = raw_bundle["candidate_mapping"][candidate]
        needed_reps = sorted(set(mapping.values()))
        recovery: dict[str, dict[str, float | None]] = {rep: {} for rep in needed_reps}
        exact_source_detail: dict[str, Any] = {}
        for rep in needed_reps:
            for task in [task for tasks in PRIMARY.values() for task in tasks]:
                dr, dy, ds, _ = tier1_rows["discovery"][task]
                cr, cy, cs, _ = tier1_rows["calibration"][task]
                dx_raw = (np.asarray(discovery.x[dr], np.float32) - mean) / scale
                cx_raw = (np.asarray(calibration.x[cr], np.float32) - mean) / scale
                model = fit_weighted_ridge_torch(
                    rep_matrix(dx_raw, rep, raw_bundle["bases"]), dy, np.ones(len(dy)),
                    float(raw_bundle["component_alpha"][rep][task]), args.device)
                value, source_detail = score_recovery(
                    model=model, raw_model=exact_raw_models[task],
                    rep_x=rep_matrix(cx_raw, rep, raw_bundle["bases"]), raw_x=cx_raw,
                    y_fit=dy, fit_sources=ds, fit_weights=np.ones(len(dy)),
                    y_eval=cy, eval_sources=cs, eval_weights=np.ones(len(cy)))
                recovery[rep][task] = value
                exact_source_detail[f"{rep}:{task}"] = source_detail
        eligible_tasks = {task for task, row in tier1_eligibility.items() if row["eligible"]}
        exact_families = family_rows(recovery, mapping, eligible_tasks)
        family_retention = {family: exact_families[family]["assigned_recovery"] for family in PRIMARY}
        macro_selectivity = (float(np.mean([exact_families[family]["selectivity_margin"] for family in PRIMARY]))
                             if all(exact_families[family]["selectivity_margin"] is not None for family in PRIMARY)
                             else None)
        parent_row = parent_calibration["baseline_candidates"][candidate]
        selection_boundaries = candidate_selection_boundaries(
            family_retention, collateral, config)
        retention_boundary = selection_boundaries[
            "tier1_family_assigned_recovery"]
        collateral_boundary = selection_boundaries[
            "tier2_sentinel_degradation"]
        tier1_ok = bool(macro_selectivity is not None and math.isfinite(macro_selectivity) and all(
                       sum(bool(tier1_eligibility[t]["eligible"]) for t in tasks) >= int(config["minimum_family_tasks"])
                       and family_retention[family] is not None and float(family_retention[family]) >= 0.65
                       and not retention_boundary[family]["boundary_proximity"]
                       for family, tasks in PRIMARY.items()))
        all_sentinels_eligible = all(sentinel_results[t]["eligibility"]["eligible"] for t in config["sentinels"])
        collateral_ok = all(collateral[t]["degradation"] is not None
                            and collateral[t]["degradation"] <= float(config["sentinel_max_degradation"])
                            and not collateral_boundary[t]["boundary_proximity"]
                            for t in config["sentinels"])
        candidate_results[candidate] = {"tier1_family_assigned_recovery": family_retention,
                                        "tier1_macro_selectivity": macro_selectivity,
                                        "tier1_recoveries": recovery,
                                        "tier1_mapping": mapping,
                                        "tier1_exact_families": exact_families,
                                        "tier1_exact_source_detail": exact_source_detail,
                                        "parent_lsqr_compatibility_diagnostic": {
                                            "macro_selectivity": parent_row["macro_selectivity"],
                                            "families": parent_row["families"]},
                                        "tier1_retention_pass": tier1_ok, "all_nine_sentinels_eligible": all_sentinels_eligible,
                                        "tier2_collateral_pass": collateral_ok,
                                        "selection_boundary_diagnostics": selection_boundaries,
                                        "roundtrip_pass": max(roundtrip_errors) <= float(config["roundtrip_tolerance"]),
                                        "selection_pass": (tier1_ok and all_sentinels_eligible and collateral_ok
                                                           and max(roundtrip_errors) <= float(config["roundtrip_tolerance"])),
                                        "roundtrip_max_relative_error": max(roundtrip_errors),
                                        "fitted_rank": {"positional": positional_rank, "complement": complement_rank,
                                                        "positional_tolerance": positional_tolerance,
                                                        "complement_tolerance": complement_tolerance},
                                        "fitted_rank_total": positional_rank + complement_rank,
                                        "collateral": collateral}

    selected, selection_failed, selection_trace = select_candidate(candidate_results)

    # K2 sentinel alpha calibration at each checkpoint's original scaler sample.
    jobs = config["primary_checkpoints"] + config["descriptive_checkpoints"]
    for job_index, job in enumerate(jobs):
        sentinel_alphas["k2"][job] = {}
        arrays = {role: {rep: rep_array(source_run_root, job, role, rep, firewall) for rep in ["pos", "content"]}
                  for role in ["discovery", "calibration"]}
        scaling: dict[str, tuple[np.ndarray, np.ndarray]] = {}
        for rep_index, rep in enumerate(["pos", "content"]):
            rng = np.random.default_rng(int(config["seed"]) + 100 * job_index + rep_index)
            sample_rows = rng.choice(len(arrays["discovery"][rep]), min(int(config["scaler_rows"]), len(arrays["discovery"][rep])), replace=False)
            sample = np.asarray(arrays["discovery"][rep][sample_rows], np.float32)
            rep_mean = sample.mean(0, dtype=np.float64).astype(np.float32)
            rep_scale = sample.std(0, dtype=np.float64).astype(np.float32)
            rep_scale[rep_scale < 1e-6] = 1.0
            scaling[rep] = (rep_mean, rep_scale)
        for task in config["sentinels"]:
            rep = "pos" if config["sentinel_mapping"][task] == "position" else "content"
            dr, dy, _, _ = sentinel_rows["discovery"][task]
            cr, cy, _, _ = sentinel_rows["calibration"][task]
            rep_mean, rep_scale = scaling[rep]
            dx = (np.asarray(arrays["discovery"][rep][dr], np.float32) - rep_mean) / rep_scale
            cx = (np.asarray(arrays["calibration"][rep][cr], np.float32) - rep_mean) / rep_scale
            models = fit_weighted_ridge_grid_torch(dx, dy, np.ones(len(dy)), alphas, args.device)
            model, table = choose(models, cx, cy, alphas, tie)
            sentinel_alphas["k2"][job][task] = {"representation": rep, "alpha": model.alpha, "grid": table}

    elapsed_sec = time.monotonic() - started
    result = {"schema_version": "atlas_completion_baseline_v1", "evidence_class": EVIDENCE_CLASS,
              "parent_bundle_sha256": parent["bundle_sha256"], "tier1_eligibility": tier1_eligibility,
              "sentinels": sentinel_results, "candidates": candidate_results,
              "selected_simple_baseline": selected, "baseline_selection_failed": selection_failed,
              "selection_trace": selection_trace,
              "sentinel_alphas": sentinel_alphas, "started_utc": started_utc,
              "ended_utc": utc_now(), "config_sha256": sha256_file(config_path),
              "resolved_config": config,
              "resolved_arguments": {"manifests": str(canonical_manifests),
                                     "output": str(canonical_output),
                                     "device": args.device},
              "seed_provenance": seed_provenance(
                  config,
                  contract=("fixed calibration alpha/eligibility seeds plus "
                            "base_seed+100*job_index+rep_index K2 scaler samples")),
              "device": args.device,
              "completion_bundle_sha256": completion_freeze["bundle_sha256"],
              "elapsed_sec": elapsed_sec, "environment": launch_environment,
              "input_attestation": firewall.attestation}
    result_path = args.output / "baseline.json"
    atomic_write_json(result_path, result)
    bundle = {"selected_simple_baseline": selected, "baseline_selection_failed": selection_failed,
              "completion_bundle_sha256": completion_freeze["bundle_sha256"],
              "sentinel_alphas": sentinel_alphas, "tier1_eligibility": tier1_eligibility,
              "sentinel_eligibility": {task: row["eligibility"] for task, row in sentinel_results.items()}}
    atomic_write_bytes(args.output / "baseline_bundle.pkl", pickle.dumps(bundle, protocol=5))
    parent_after = verify_parent_freeze_attested(
        firewall, ["discovery", "calibration"])
    extension_after = verify_completion_freeze()
    verify_attestation_current(firewall.attestation)
    elapsed_sec = time.monotonic() - started
    write_terminal(args.output, complete=True, payload={"schema_version": "atlas_completion_baseline_complete_v1",
                                                        "config_sha256": sha256_file(config_path),
                                                        "resolved_config": config,
                                                        "resolved_arguments": {"manifests": str(canonical_manifests),
                                                                               "output": str(canonical_output),
                                                                               "device": args.device},
                                                        "seed_provenance": result["seed_provenance"],
                                                        "device": args.device,
                                                        "started_utc": started_utc,
                                                        "environment": launch_environment,
                                                        "resource_accounting": process_resource_accounting(
                                                            args.output, elapsed_sec=elapsed_sec,
                                                            device=args.device),
                                                        "result_sha256": sha256_file(result_path),
                                                        "bundle_sha256": sha256_file(args.output / "baseline_bundle.pkl"),
                                                        "completion_bundle_sha256": completion_freeze["bundle_sha256"],
                                                        "selected_simple_baseline": selected,
                                                        "baseline_selection_failed": selection_failed,
                                                        "parent_bundle_reverified_after_stage_sha256": parent_after["bundle_sha256"],
                                                        "completion_bundle_reverified_after_stage_sha256": extension_after["bundle_sha256"],
                                                        "input_attestation": firewall.attestation})
    print(json.dumps({"selected": selected, "baseline_selection_failed": selection_failed,
                      "eligible_sentinels": sum(row["eligibility"]["eligible"] for row in sentinel_results.values()),
                      "eligible_tier1": sum(row["eligible"] for row in tier1_eligibility.values()),
                      "elapsed_sec": time.monotonic() - started}, indent=2))


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        output = ROOT / "pilot_runs/20260801_atlas_completion_v1/baseline"
        if "--output" in __import__("sys").argv:
            output = Path(__import__("sys").argv[__import__("sys").argv.index("--output") + 1])
        write_failure_terminal(output, stop_code="baseline_unrecoverable_failure",
                               failed_gate="calibration_baseline", error=exc,
                               input_attestation=_FAILURE_ATTESTATION)
        raise
