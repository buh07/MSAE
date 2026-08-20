#!/usr/bin/env python3
"""Discovery/calibration-only numerical and throughput pilot (no C1/C2 access)."""

from __future__ import annotations

import argparse
import hashlib
import json
import pickle
import resource
import time
from pathlib import Path
from typing import Any

import numpy as np
import torch
import torch.nn.functional as F
from sklearn.linear_model import RidgeClassifier

from msa_completion_common import (EVIDENCE_CLASS, ROOT, atomic_write_json,
                                   canonical_json_bytes,
                                   cosine_matched_direction, default_firewall,
                                   deterministic_seed, draw_group_multiplicities,
                                   fit_weighted_ridge_torch, load_activation,
                                   load_row_file, macro_f1, read_json,
                                   orthonormal_basis,
                                   process_resource_accounting,
                                   register_pinned_hf_snapshot,
                                   runtime_environment, sha256_file,
                                   seed_provenance,
                                   unit_group_multiplicities,
                                   verify_parent_freeze_attested,
                                   verify_parent_raw_calibration,
                                   verify_parent_transform_roles,
                                   verify_attestation_current,
                                   validated_cuda_environment,
                                   weighted_linear_cka,
                                   weights_from_multiplicities, write_terminal)
from msa_completion_common import write_failure_terminal
from run_k2_functional_audit import representations
from merge_msae_refit import (frozen_group_bootstrap_maps,
                              intersection_union_pvalue,
                              negative_sensitivity_simulation)
from run_msae_refit_worker import k2_draw, raw_draw
from run_msae_specificity import aggregate_ce_collateral, group_summary
from run_msae_stability import raw_fit_bases, simple_component, task_matrix_cka
from train_msae_k2 import K2MSAE


TASKS = ["abs_pos_16", "abs_pos_8", "relative_quartile", "head_signed_distance", "dependency_depth",
         "boundary_state", "token_identity_256", "lemma_identity_256", "ner_coarse"]

_FAILURE_ATTESTATION: dict[str, Any] = {}

EXERCISED_PATHS = [
    "configs/atlas_completion/analysis.json",
    "data/atlas_completion_v1/MEASUREMENT_COMPLETE.json",
    "data/atlas_completion_v1/pilot_k2_alphas.json",
    "data/atlas_completion_v1/tier2_manifest.json",
    "data/atlas_completion_v1/token_control_manifest.json",
    "data/atlas_completion_v1/upstream_inventory.json",
    "scripts/atlas_freeze.py",
    "scripts/atlas_metrics.py",
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
]


def pilot_terminal_payload(result: dict[str, Any], *, result_sha256: str,
                           stage_budget_pass: dict[str, bool]) -> tuple[bool, dict[str, Any]]:
    """Build either the passing pilot terminal or a non-promotable frozen stop."""

    numerical_pass = result.get("numerical_pass") is True
    budget_pass = result.get("budget_pass") is True
    complete = numerical_pass and budget_pass
    failed_stage_budgets = sorted(
        stage for stage, passed in stage_budget_pass.items() if not passed)
    common = {
        "numerical_pass": numerical_pass,
        "budget_pass": budget_pass,
        "result_sha256": result_sha256,
        "exercised_bundle_sha256": result["exercised_bundle_sha256"],
        "failed_stage_budgets": failed_stage_budgets,
        "projected": result["projected"],
        "score_access_allowed": complete,
        "input_attestation": dict(sorted(result.get("input_attestation", {}).items())),
        "resolved_config": result["resolved_config"],
        "resolved_arguments": result["resolved_arguments"],
        "seed_provenance": result["seed_provenance"],
        "device": result["device"],
        "started_utc": result["started_utc"],
        "environment": result["environment"],
        "resource_accounting": result["resource_accounting"],
        "parent_bundle_reverified_after_stage_sha256": result[
            "parent_bundle_reverified_after_stage_sha256"],
    }
    if complete:
        return True, {"schema_version": "atlas_completion_pilot_complete_v1", **common}
    if not numerical_pass and not budget_pass:
        stop_code = "pilot_numerical_and_resource_gate_failure"
        failed_gate = "pilot_numerical_and_resource_gates"
    elif not numerical_pass:
        stop_code = "pilot_numerical_gate_failure"
        failed_gate = "pilot_numerical_gate"
    else:
        stop_code = "pilot_resource_gate_failure"
        failed_gate = "pilot_resource_gate"
    reason = (f"pilot stopped before score access: numerical_pass={numerical_pass}, "
              f"budget_pass={budget_pass}, failed_stage_budgets={failed_stage_budgets}")
    return False, {
        "schema_version": "atlas_completion_frozen_stop_v1",
        "stop_code": stop_code,
        "failed_gate": failed_gate,
        "reason": reason,
        "requested_draw_ids": [],
        "completed_draw_ids": [],
        "retained_partial_sha256": {"pilot.json": result_sha256},
        "scientific_retry_allowed": False,
        "decision_promotion_allowed": False,
        **common,
    }


def snapshot_exercised_files(paths: list[str] | None = None) -> list[dict[str, str]]:
    """Snapshot the exact pilot/scoring implementation before any work starts."""

    selected = EXERCISED_PATHS if paths is None else paths
    missing = [path for path in selected if not (ROOT / path).is_file()]
    if missing:
        raise FileNotFoundError(f"missing pilot exercised files: {missing}")
    return [{"path": path, "sha256": sha256_file(ROOT / path)}
            for path in sorted(selected)]


def roles_from_attestation(attestation: dict[str, Any]) -> list[str]:
    """Derive accessed atlas roles from opened paths; never rely on a claim."""

    found: set[str] = set()
    for raw_path in attestation:
        normalized = raw_path.replace("\\", "/")
        parts = normalized.split("/")
        for marker in ["raw_activations", "k2_transforms"]:
            if marker in parts:
                index = parts.index(marker)
                role_index = index + (1 if marker == "raw_activations" else 2)
                if role_index < len(parts) and parts[role_index] in {"discovery", "calibration", "C1", "C2", "final"}:
                    found.add(parts[role_index])
        for role in ["discovery", "calibration", "C1", "C2", "final"]:
            if (f"/transforms/{role}.jsonl" in normalized
                    or f"/partitions/{role}." in normalized
                    or f"/{role}." in normalized and "/analysis_rows/" in normalized):
                found.add(role)
    return sorted(found)


def main() -> None:
    global _FAILURE_ATTESTATION
    parser = argparse.ArgumentParser()
    parser.add_argument("--device", default="cuda:0")
    parser.add_argument("--config", type=Path, default=ROOT / "configs/atlas_completion/analysis.json")
    parser.add_argument("--output", type=Path, default=ROOT / "pilot_runs/20260801_atlas_completion_v1/pilot_v10")
    args = parser.parse_args()
    pilot_started = time.monotonic()
    pilot_started_utc = __import__("datetime").datetime.now(
        __import__("datetime").timezone.utc).isoformat()
    exercised_files = snapshot_exercised_files()
    args.output.mkdir(parents=True, exist_ok=True)
    if any(args.output.iterdir()):
        raise RuntimeError("pilot output is create-once")
    config = read_json(args.config)
    source_root, run_root = ROOT / config["source_run_root"], ROOT / config["run_root"]
    firewall = default_firewall(source_root, run_root)
    _FAILURE_ATTESTATION = firewall.attestation
    firewall.register_root(ROOT / "data/atlas_completion_v1")
    firewall.register_root(args.output)
    config_path = firewall.attest(args.config)
    launch_environment = validated_cuda_environment(args.device)
    raw_fixed_startup_start = time.monotonic()
    discovery = load_activation("discovery", 3, source_root, firewall)
    calibration = load_activation("calibration", 3, source_root, firewall)
    task_manifest = read_json(firewall.attest(ROOT / "configs/atlas/task_row_manifest.json"))
    verify_parent_raw_calibration(source_root, firewall)
    with firewall.attest(ROOT / "results/atlas/raw_v1/L3_calibration_bundle.pkl").open("rb") as handle:
        bundle = pickle.load(handle)
    freeze = read_json(firewall.attest(ROOT / "results/atlas/raw_v1/L3_calibration_freeze.json"))
    raw_public_fixed_startup_sec = time.monotonic() - raw_fixed_startup_start
    device = args.device
    torch_device = torch.device(device)
    torch.cuda.reset_peak_memory_stats(torch_device)
    baseline_analogue_start = time.monotonic()
    numerical = {}
    ridge_times = []
    cached = {}
    coefficients: dict[str, dict[str, np.ndarray]] = {"unit_gpu": {}, "unit_reference": {},
                                                      "weighted_gpu": {}, "weighted_reference": {}}
    for task in TASKS:
        dr, dy, ds, dg = load_row_file(ROOT / task_manifest["roles"]["discovery"][task]["path"], discovery, firewall, role="discovery")
        cr, cy, _, _ = load_row_file(ROOT / task_manifest["roles"]["calibration"][task]["path"], calibration, firewall, role="calibration")
        dx = (np.asarray(discovery.x[dr], np.float32) - bundle["mean"]) / bundle["scale"]
        cx = (np.asarray(calibration.x[cr], np.float32) - bundle["mean"]) / bundle["scale"]
        weights = np.ones(len(dy))
        start = time.monotonic()
        model = fit_weighted_ridge_torch(dx, dy, weights, float(freeze["raw_alpha"][task]), device)
        torch.cuda.synchronize()
        ridge_times.append(time.monotonic() - start)
        exact = RidgeClassifier(alpha=float(freeze["raw_alpha"][task]), solver="cholesky", fit_intercept=True).fit(dx, dy)
        parent_compat = RidgeClassifier(alpha=float(freeze["raw_alpha"][task]), solver="lsqr", fit_intercept=True).fit(dx, dy)
        pred, exact_pred, parent_pred = model.predict(cx), exact.predict(cx), parent_compat.predict(cx)
        numerical[task] = {"exact_prediction_agreement": float(np.mean(pred == exact_pred)),
                           "exact_macro_f1_abs_difference": abs(macro_f1(cy, pred) - macro_f1(cy, exact_pred)),
                           "exact_relative_coefficient_error": float(np.linalg.norm(model.coef - exact.coef_) / max(np.linalg.norm(exact.coef_), 1e-12)),
                           "exact_relative_decision_error": float(np.linalg.norm((cx @ model.coef.T + model.intercept).reshape(exact.decision_function(cx).shape) - exact.decision_function(cx)) / max(np.linalg.norm(exact.decision_function(cx)), 1e-12)),
                           "parent_lsqr_prediction_agreement_diagnostic": float(np.mean(pred == parent_pred)),
                           "parent_lsqr_macro_f1_abs_difference": abs(macro_f1(cy, pred) - macro_f1(cy, parent_pred))}
        coefficients["unit_gpu"][task], coefficients["unit_reference"][task] = model.coef, exact.coef_
        # One nonuniform integer document-group draw per task, with raw weights.
        mult = draw_group_multiplicities(ds, dg, seed=deterministic_seed(config["seed"], "pilot_numerical", task, 0))
        nonuniform = weights_from_multiplicities(ds, dg, mult).astype(int)
        weighted_gpu = fit_weighted_ridge_torch(dx, dy, nonuniform, float(freeze["raw_alpha"][task]), device)
        weighted_reference = RidgeClassifier(alpha=float(freeze["raw_alpha"][task]), solver="cholesky", fit_intercept=True).fit(dx, dy, sample_weight=nonuniform)
        replicated_reference = RidgeClassifier(alpha=float(freeze["raw_alpha"][task]), solver="cholesky", fit_intercept=True).fit(
            np.repeat(dx, nonuniform, axis=0), np.repeat(dy, nonuniform, axis=0))
        wg_pred, wr_pred = weighted_gpu.predict(cx), weighted_reference.predict(cx)
        wr_decision = weighted_reference.decision_function(cx)
        wg_decision = (cx @ weighted_gpu.coef.T + weighted_gpu.intercept).reshape(wr_decision.shape)
        numerical[task]["weighted_prediction_agreement"] = float(np.mean(wg_pred == wr_pred))
        numerical[task]["weighted_macro_f1_abs_difference"] = abs(macro_f1(cy, wg_pred) - macro_f1(cy, wr_pred))
        numerical[task]["weighted_relative_coefficient_error"] = float(np.linalg.norm(weighted_gpu.coef - weighted_reference.coef_) / max(np.linalg.norm(weighted_reference.coef_), 1e-12))
        numerical[task]["weighted_relative_decision_error"] = float(np.linalg.norm(wg_decision - wr_decision) / max(np.linalg.norm(wr_decision), 1e-12))
        numerical[task]["literal_replication_relative_coefficient_error"] = float(np.linalg.norm(replicated_reference.coef_ - weighted_reference.coef_) / max(np.linalg.norm(weighted_reference.coef_), 1e-12))
        coefficients["weighted_gpu"][task], coefficients["weighted_reference"][task] = weighted_gpu.coef, weighted_reference.coef_
        cached[task] = (dx, dy, ds, dg)

    projector_errors = {}
    families = {"absolute": TASKS[:2], "structural": TASKS[2:6], "lexical": TASKS[6:]}
    for weighting in ["unit", "weighted"]:
        gpu_family_bases: dict[str, np.ndarray] = {}
        ref_family_bases: dict[str, np.ndarray] = {}
        for family, tasks in families.items():
            rank = int(config["family_rank"])
            gpu_basis = orthonormal_basis(np.concatenate([coefficients[f"{weighting}_gpu"][task] for task in tasks], axis=0), rank)
            ref_basis = orthonormal_basis(np.concatenate([coefficients[f"{weighting}_reference"][task] for task in tasks], axis=0), rank)
            gpu_family_bases[family], ref_family_bases[family] = gpu_basis, ref_basis
            projector_errors[f"{weighting}:{family}"] = float(np.linalg.norm(gpu_basis @ gpu_basis.T - ref_basis @ ref_basis.T) / np.sqrt(rank))
        position_tasks = families["absolute"] + families["structural"]
        position_rank = int(config["position_rank"])
        gpu_broad = orthonormal_basis(np.concatenate(
            [coefficients[f"{weighting}_gpu"][task] for task in position_tasks], axis=0),
            position_rank)
        ref_broad = orthonormal_basis(np.concatenate(
            [coefficients[f"{weighting}_reference"][task] for task in position_tasks], axis=0),
            position_rank)
        projector_errors[f"{weighting}:broad_position"] = float(
            np.linalg.norm(gpu_broad @ gpu_broad.T - ref_broad @ ref_broad.T)
            / np.sqrt(position_rank))
        gpu_split = orthonormal_basis(np.concatenate(
            [gpu_family_bases["absolute"].T, gpu_family_bases["structural"].T], axis=0),
            position_rank)
        ref_split = orthonormal_basis(np.concatenate(
            [ref_family_bases["absolute"].T, ref_family_bases["structural"].T], axis=0),
            position_rank)
        projector_errors[f"{weighting}:split_position_joint"] = float(
            np.linalg.norm(gpu_split @ gpu_split.T - ref_split @ ref_split.T)
            / np.sqrt(position_rank))

    # Ten group-weighted largest-dimension fits.
    timing_task = "boundary_state"
    dx, dy, ds, dg = cached[timing_task]
    weighted_times = []
    for draw in range(10):
        mult = draw_group_multiplicities(ds, dg, seed=deterministic_seed(config["seed"], "pilot", timing_task, draw))
        weights = weights_from_multiplicities(ds, dg, mult)
        start = time.monotonic()
        fit_weighted_ridge_torch(dx, dy, weights, float(freeze["raw_alpha"][timing_task]), device)
        torch.cuda.synchronize()
        weighted_times.append(time.monotonic() - start)

    cpu_two_draw = {}
    for draw in [0, 1]:
        dx_cpu, dy_cpu, ds_cpu, dg_cpu = cached[timing_task]
        mult_cpu = draw_group_multiplicities(ds_cpu, dg_cpu,
            seed=deterministic_seed(config["seed"], "m2_cpu_two_draw", timing_task, draw))
        weights_cpu = weights_from_multiplicities(ds_cpu, dg_cpu, mult_cpu)
        first_cpu = RidgeClassifier(alpha=float(freeze["raw_alpha"][timing_task]), solver="cholesky").fit(
            dx_cpu, dy_cpu, sample_weight=weights_cpu)
        second_cpu = RidgeClassifier(alpha=float(freeze["raw_alpha"][timing_task]), solver="cholesky").fit(
            dx_cpu, dy_cpu, sample_weight=weights_cpu)
        cpu_two_draw[str(draw)] = bool(np.array_equal(first_cpu.predict(dx_cpu), second_cpu.predict(dx_cpu))
                                       and np.allclose(first_cpu.coef_, second_cpu.coef_, rtol=0, atol=0))
    cpu_two_draw_pass = all(cpu_two_draw.values())

    # Score-independent smoke for the exact six-coordinate sensitivity/IUT
    # production helpers.  Confirmation-role pseudovalues are deliberately not
    # constructed until after the completion freeze.
    sensitivity_rng = np.random.default_rng(config["seed"])
    sensitivity_residuals = {
        "source_a": sensitivity_rng.normal(size=(12, 6)),
        "source_b": sensitivity_rng.normal(size=(10, 6)),
    }
    sensitivity_residuals = {
        source: values - values.mean(axis=0, keepdims=True)
        for source, values in sensitivity_residuals.items()
    }
    sensitivity_groups = {
        source: [f"{source}:{index}" for index in range(len(values))]
        for source, values in sensitivity_residuals.items()
    }
    sensitivity_maps = frozen_group_bootstrap_maps(
        sensitivity_groups, draws=500, seed=int(config["seed"]))
    sensitivity_smoke_start = time.monotonic()
    sensitivity_smoke = negative_sensitivity_simulation(
        sensitivity_residuals, sensitivity_maps, simulations=32,
        seed=int(config["seed"]), effect=0.20)
    sensitivity_smoke_sec = time.monotonic() - sensitivity_smoke_start
    iut_smoke = intersection_union_pvalue(
        {"split:a": {"valid": True, "p": 0.01},
         "split:b": {"valid": True, "p": 0.04},
         "broad:c": {"valid": True, "p": 0.02}},
        ["split:a", "split:b", "broad:c"])
    inference_helper_smoke_pass = bool(
        sensitivity_smoke.get("valid")
        and sensitivity_smoke.get("simulations_completed") == 32
        and sensitivity_smoke.get("point_failures") == [0] * 6
        and iut_smoke.get("valid") and iut_smoke.get("p") == 0.04
        and iut_smoke.get("winning_component") == "split:b")

    # Ten actual end-to-end calibration-role raw refits, including global
    # scaling, Tier-1/simple/Tier-2 fits, all three bases, and round-trip gates.
    job = config["primary_checkpoints"][0]
    k2_fixed_startup_start = time.monotonic()
    pilot_alpha_manifest = read_json(
        firewall.attest(ROOT / "data/atlas_completion_v1/pilot_k2_alphas.json"))
    if (pilot_alpha_manifest.get("schema_version") != "atlas_completion_pilot_k2_alphas_v1"
            or pilot_alpha_manifest.get("selection_role") != "calibration"):
        raise RuntimeError("invalid pilot K2 alpha manifest")
    pilot_k2_alphas = pilot_alpha_manifest["jobs"][job]["alpha_selection"]
    for checkpoint_job in config["primary_checkpoints"] + config["descriptive_checkpoints"]:
        verify_parent_transform_roles(
            source_root, checkpoint_job, ["discovery", "calibration"], firewall)
    k2_fixed_startup_sec = time.monotonic() - k2_fixed_startup_start
    tier2_manifest = read_json(firewall.attest(ROOT / "data/atlas_completion_v1/tier2_manifest.json"))
    pilot_sentinel_alphas = {task: 10.0 for task in config["sentinels"]}
    baseline_stub = {"selected_simple_baseline": "projection_broad16",
                     "tier1_eligibility": {task: {"eligible": True} for task in TASKS},
                     "sentinel_alphas": {
                         "raw": pilot_sentinel_alphas,
                         "simple": {"projection_broad16": pilot_sentinel_alphas},
                         "k2": {job: {task: {"representation": ("pos" if config["sentinel_mapping"][task] == "position" else "content"),
                                             "alpha": 10.0}
                                      for task in config["sentinels"]}}}}
    raw_draw_results = []
    raw_draw_times = []
    point_model_smoke: dict[str, Any] = {}
    for draw in range(10):
        start = time.monotonic()
        raw_draw_results.append(raw_draw(draw, 3, config, baseline_stub, tier2_manifest, discovery, calibration,
                                         calibration, bundle, device, firewall, eval_role="calibration",
                                         collateral_role="calibration",
                                         model_sink=point_model_smoke if draw == 0 else None))
        torch.cuda.synchronize()
        raw_draw_times.append(time.monotonic() - start)
    # Recompute two IDs in reverse shard order; canonical results must match.
    two_draw_hashes = {}
    for draw in [1, 0]:
        rerun = raw_draw(draw, 3, config, baseline_stub, tier2_manifest, discovery, calibration,
                         calibration, bundle, device, firewall, eval_role="calibration",
                         collateral_role="calibration")
        two_draw_hashes[str(draw)] = {
            "original": __import__("hashlib").sha256(canonical_json_bytes(raw_draw_results[draw])).hexdigest(),
            "rerun": __import__("hashlib").sha256(canonical_json_bytes(rerun)).hexdigest(),
        }
    two_draw_gpu_pass = all(row["original"] == row["rerun"] for row in two_draw_hashes.values())
    point_model_smoke_pass = bool(set(point_model_smoke) >= {"mean", "scale", "bases", "raw_models", "component_models"}
                                  and len(point_model_smoke["raw_models"]) == 9
                                  and all(len(models) == 9 for models in point_model_smoke["component_models"].values()))
    baseline_analogue_sec = time.monotonic() - baseline_analogue_start

    # Ten production K2 calibration analogues exercise scaler refits, paired raw
    # leaves, source-stratified recovery, and all Tier-2 collateral.
    k2_draw_results = []
    k2_draw_times = []
    for draw in range(10):
        start = time.monotonic()
        k2_draw_results.append(k2_draw(
            draw, job, config, baseline_stub, tier2_manifest, discovery, calibration,
            source_root, device, firewall, eval_role="calibration",
            raw_result_override={"result": raw_draw_results[draw]},
            parent_alpha_override=pilot_k2_alphas))
        torch.cuda.synchronize()
        k2_draw_times.append(time.monotonic() - start)
    k2_draw_hashes = {}
    for draw in [1, 0]:
        rerun = k2_draw(
            draw, job, config, baseline_stub, tier2_manifest, discovery, calibration,
            source_root, device, firewall, eval_role="calibration",
            raw_result_override={"result": raw_draw_results[draw]},
            parent_alpha_override=pilot_k2_alphas)
        k2_draw_hashes[str(draw)] = {
            "original": __import__("hashlib").sha256(canonical_json_bytes(k2_draw_results[draw])).hexdigest(),
            "rerun": __import__("hashlib").sha256(canonical_json_bytes(rerun)).hexdigest(),
        }
    k2_two_draw_pass = bool(
        all(row["original"] == row["rerun"]
            for row in k2_draw_hashes.values())
        and all(isinstance(row.get("finite"), bool)
                for row in k2_draw_results))

    # Every smaller K2 assigned/nonassigned fit plus shape-matched CKA.
    pos_d = np.load(firewall.attest(source_root / f"k2_transforms/{job}/discovery/pos.float16.npy", role="discovery"), mmap_mode="r")
    dr, dy, _, _ = load_row_file(ROOT / task_manifest["roles"]["discovery"][timing_task]["path"], discovery, firewall, role="discovery")
    parent_audit = {"alpha_selection": pilot_k2_alphas}
    k2_fit_times = []
    k2_discovery = {"pos": pos_d,
                    "content": np.load(firewall.attest(source_root / f"k2_transforms/{job}/discovery/content.float16.npy", role="discovery"), mmap_mode="r")}
    for task in TASKS:
        task_rows, labels, _, _ = load_row_file(ROOT / task_manifest["roles"]["discovery"][task]["path"], discovery, firewall, role="discovery")
        for rep in ["pos", "content"]:
            start = time.monotonic()
            fit_weighted_ridge_torch(np.asarray(k2_discovery[rep][task_rows], np.float32), labels, np.ones(len(labels)),
                                     float(parent_audit["alpha_selection"][rep][task]["selected"]), device)
            torch.cuda.synchronize()
            k2_fit_times.append(time.monotonic() - start)
    k2_fit_sec = float(np.mean(k2_fit_times))
    g5 = config["primary_checkpoints"][1]
    pos_c1 = np.load(firewall.attest(source_root / f"k2_transforms/{job}/calibration/pos.float16.npy", role="calibration"), mmap_mode="r")
    pos_c2 = np.load(firewall.attest(source_root / f"k2_transforms/{g5}/calibration/pos.float16.npy", role="calibration"), mmap_mode="r")
    cr, _, _, _ = load_row_file(ROOT / task_manifest["roles"]["calibration"][timing_task]["path"], calibration, firewall, role="calibration")
    start = time.monotonic()
    cka_value = weighted_linear_cka(np.asarray(pos_c1[cr], np.float32), np.asarray(pos_c2[cr], np.float32), np.ones(len(cr)))
    cka_sec = time.monotonic() - start

    # One complete calibration-role stability-shaped draw: two raw refit bases,
    # all three regularized pairs, g4/g7, and simple A/B across every task.
    calibration_rows = {task: load_row_file(ROOT / task_manifest["roles"]["calibration"][task]["path"], calibration, firewall, role="calibration")
                        for task in TASKS}
    discovery_rows = {task: load_row_file(ROOT / task_manifest["roles"]["discovery"][task]["path"], discovery, firewall, role="discovery")
                      for task in TASKS}
    unit_map = unit_group_multiplicities(discovery.row_source.astype(str), discovery.row_group.astype(str))
    stability_start = time.monotonic()
    mean_a, scale_a, bases_a = raw_fit_bases(discovery, discovery_rows, unit_map, 3, config, freeze["raw_alpha"], device, True)
    mean_b, scale_b, bases_b = raw_fit_bases(discovery, discovery_rows, unit_map, 3, config, freeze["raw_alpha"], device, True)
    stability_jobs = config["primary_checkpoints"] + config["descriptive_checkpoints"]
    stability_arrays = {name: {rep: np.load(firewall.attest(source_root / f"k2_transforms/{name}/calibration/{rep}.float16.npy", role="calibration"), mmap_mode="r")
                               for rep in ["pos", "content"]} for name in stability_jobs}
    cka_count = 0
    for task in TASKS:
        rows, _, _, _ = calibration_rows[task]
        family_rep = "content" if task in TASKS[6:] else "pos"
        for left, right in [(stability_jobs[0], stability_jobs[1]), (stability_jobs[0], stability_jobs[2]),
                            (stability_jobs[1], stability_jobs[2]), (stability_jobs[0], stability_jobs[3])]:
            task_matrix_cka(np.asarray(stability_arrays[left][family_rep][rows], np.float32),
                            np.asarray(stability_arrays[right][family_rep][rows], np.float32), np.ones(len(rows)))
            cka_count += 1
        raw_eval = np.asarray(calibration.x[rows], np.float32)
        family = ("lexical_semantic_content" if task in TASKS[6:] else
                  "absolute_position" if task in TASKS[:2] else "relative_structural_position")
        simple_a = simple_component(raw_eval, mean_a, scale_a, bases_a, "projection_broad16", family)
        simple_b = simple_component(raw_eval, mean_b, scale_b, bases_b, "projection_broad16", family)
        task_matrix_cka(simple_a, simple_b, np.ones(len(rows)))
        cka_count += 1
    torch.cuda.synchronize()
    stability_draw_sec = time.monotonic() - stability_start

    # Full 128 calibration-transform functional path for one checkpoint.
    token_manifest = read_json(firewall.attest(ROOT / "data/atlas_completion_v1/token_control_manifest.json"))
    snapshot = register_pinned_hf_snapshot(firewall, token_manifest)
    from transformers import AutoModelForCausalLM, AutoTokenizer
    from atlas_freeze import checkpoint_spec

    functional_startup_start = time.monotonic()
    tokenizer = AutoTokenizer.from_pretrained(snapshot, local_files_only=True, use_fast=True)
    lm = AutoModelForCausalLM.from_pretrained(snapshot, local_files_only=True, torch_dtype=torch.float16).to(device).eval()
    spec = checkpoint_spec(job)
    firewall.register_file(Path(spec["path"]))
    checkpoint = torch.load(firewall.attest(Path(spec["path"])), map_location="cpu", weights_only=False)
    train_args = checkpoint["args"]
    msae = K2MSAE(768, int(train_args["m_pos"]), int(train_args["k_pos"]), int(train_args["m_content"]), int(train_args["k_content"]))
    msae.load_state_dict(checkpoint["model"])
    msae = msae.to(device).eval()
    functional_startup_sec = time.monotonic() - functional_startup_start
    transforms = [json.loads(line) for line in firewall.attest(ROOT / "data/atlas_v1/transforms/calibration.jsonl", role="calibration").read_text().splitlines()]
    mock_specificity_rows = []
    for transform in transforms:
        assigned = "content" if transform["family"] == "lexical_entity_substitution" else "pos"
        actual = {assigned: 0.20, ("content" if assigned == "pos" else "pos"): 0.10}
        specificity = {"pos": (0.0 if transform["family"] == "punctuation_format" else 0.10),
                       "content": (0.0 if transform["family"] == "punctuation_format" else 0.10)}
        summary_row = {"valid": True, "actual_normalized": actual, "specificity": specificity}
        mock_specificity_rows.append({"transform_id": transform["transform_id"], "family": transform["family"],
                                      "template_group": transform["template_group"],
                                      "token_aligned_parent": transform.get("token_aligned"),
                                      "sentence": summary_row, "token_aligned": summary_row})
    # Calibration has only 12 token-aligned lexical transforms, whereas the
    # frozen C2 token-control population has 16.  Exercise the registered
    # 16-row completeness rule from the prescore token manifest without
    # opening any C2 activation/transform artifact in the pilot.
    token_smoke_row = {
        "valid": True,
        "actual_normalized": {"content": 0.20, "pos": 0.10},
        "specificity": {"pos": 0.10, "content": 0.10},
    }
    token_specificity_rows = [
        {
            "transform_id": row["transform_id"],
            "family": "lexical_entity_substitution",
            "template_group": row["template_group"],
            "token_aligned_parent": True,
            "sentence": token_smoke_row,
            "token_aligned": token_smoke_row,
        }
        for row in token_manifest["rows"]
    ]
    summary_checks = [
        group_summary(mock_specificity_rows, "position_shift", "pos", config, "pilot"),
        group_summary(mock_specificity_rows, "structural_active_passive", "pos", config, "pilot"),
        group_summary(mock_specificity_rows, "lexical_entity_substitution", "content", config, "pilot"),
        group_summary(token_specificity_rows, "lexical_entity_substitution", "content", config, "pilot", token=True),
        group_summary(mock_specificity_rows, "punctuation_format", "pos", config, "pilot"),
        group_summary(mock_specificity_rows, "punctuation_format", "content", config, "pilot"),
    ]
    specificity_summary_smoke_pass = all(row["valid"] for row in summary_checks)
    synthetic_ce_rows = [{"transform_id": transform["transform_id"], "side": side,
                          "ce": {"raw": 1.0, "k2_reconstruction": 1.01}}
                         for transform in transforms if "source_words" in transform
                         for side in ["source_words", "target_words"]]
    synthetic_ce_point, synthetic_ce_groups, synthetic_ce_families = aggregate_ce_collateral(
        synthetic_ce_rows, transforms)
    ce_aggregation_smoke_pass = bool(abs(synthetic_ce_point - 0.01) <= 1e-12
                                     and len(synthetic_ce_groups) == 12
                                     and len(synthetic_ce_families) == 3)
    raw = np.load(firewall.attest(source_root / "raw_activations/calibration/L3.float16.npy", role="calibration"), mmap_mode="r")
    with np.load(firewall.attest(source_root / "raw_activations/calibration/row_meta.npz", role="calibration")) as loaded:
        meta = {key: loaded[key] for key in loaded.files}
    records = [json.loads(line) for line in firewall.attest(source_root / "raw_activations/calibration/records.jsonl", role="calibration").read_text().splitlines()]
    base_index = {row["base_id"]: i for i, row in enumerate(records)}
    calibration_units = [json.loads(line) for line in firewall.attest(ROOT / "data/atlas_v1/partitions/calibration.units.jsonl", role="calibration").read_text().splitlines()]
    unit_map = {(row["base_id"], int(row["offset"])): row for row in calibration_units}
    functional_start = time.monotonic()
    functional_rows = 0
    token_control_tokens = 0
    identity_ce_rows = 0
    max_identity_ce_error = 0.0
    simple_mean = torch.as_tensor(bundle["mean"], dtype=torch.float32, device=device)
    simple_scale = torch.as_tensor(bundle["scale"], dtype=torch.float32, device=device)
    simple_basis = torch.as_tensor(bundle["bases"]["broad_position"], dtype=torch.float32, device=device)

    def ce(ids: torch.Tensor, identity: bool) -> float:
        handle = None
        if identity:
            def hook(_module: object, _inputs: object, output: object) -> object:
                hidden_state = output[0] if isinstance(output, tuple) else output
                flat = hidden_state.reshape(-1, hidden_state.shape[-1]).float()
                z = (flat - simple_mean) / simple_scale
                projected = (z @ simple_basis) @ simple_basis.T
                replacement = ((projected + (z - projected)) * simple_scale + simple_mean)
                replacement = replacement.reshape_as(hidden_state).to(hidden_state.dtype)
                return (replacement,) + output[1:] if isinstance(output, tuple) else replacement
            handle = lm.gpt_neox.layers[3].register_forward_hook(hook)
        try:
            with torch.inference_mode():
                logits = lm(ids, use_cache=False).logits
        finally:
            if handle is not None:
                handle.remove()
        return float(F.cross_entropy(logits[:, :-1].float().reshape(-1, logits.shape[-1]),
                                     ids[:, 1:].reshape(-1), reduction="mean").item())

    for transform in transforms:
        if "source_words" in transform:
            hidden = []
            encodings = []
            for words in [transform["source_words"], transform["target_words"], transform["source_words"]]:
                encoding = tokenizer(words, is_split_into_words=True, add_special_tokens=False, return_tensors="pt")
                encodings.append(encoding)
                ids = encoding["input_ids"].to(device)
                with torch.inference_mode():
                    h = lm(ids, output_hidden_states=True, use_cache=False).hidden_states[4]
                hidden.append(h)
            source_rep = representations(hidden[0], msae)
            target_rep = representations(hidden[1], msae)
            delta, _ = cosine_matched_direction(source_rep["raw"], target_rep["raw"],
                seed=deterministic_seed(config["seed"], "pilot_random", transform["transform_id"]))
            random_h = hidden[0].float() + torch.as_tensor(delta, device=device)[None, None, :]
            representations(random_h, msae)
            representations(hidden[2], msae)
            source_word_ids, target_word_ids = encodings[0].word_ids(), encodings[1].word_ids()
            if source_word_ids == target_word_ids:
                changed_words = {i for i, (a, b) in enumerate(zip(transform["source_words"], transform["target_words"], strict=True)) if a != b}
                for token_index, word_id in enumerate(source_word_ids):
                    if word_id not in changed_words:
                        continue
                    source_token = hidden[0][:, token_index:token_index + 1]
                    target_token = hidden[1][:, token_index:token_index + 1]
                    source_token_rep, target_token_rep = representations(source_token, msae), representations(target_token, msae)
                    token_delta, _ = cosine_matched_direction(
                        source_token_rep["raw"], target_token_rep["raw"],
                        seed=deterministic_seed(config["seed"], "pilot_random_token", transform["transform_id"], token_index))
                    representations(source_token.float() + torch.as_tensor(token_delta, device=device)[None, None, :], msae)
                    representations(hidden[2][:, token_index:token_index + 1], msae)
                    token_control_tokens += 1
            for encoding in encodings[:2]:
                ids = encoding["input_ids"].to(device)
                raw_ce, identity_ce = ce(ids, False), ce(ids, True)
                max_identity_ce_error = max(max_identity_ce_error, abs(identity_ce - raw_ce))
                identity_ce_rows += 1
        else:
            hidden = []
            for offset in [transform["source_offset"], transform["target_offset"], transform["source_offset"]]:
                ids = torch.tensor([unit_map[(transform["base_id"], int(offset))]["input_ids"]], dtype=torch.long, device=device)
                with torch.inference_mode():
                    h = lm(ids, output_hidden_states=True, use_cache=False).hidden_states[4]
                hidden.append(h)
            source_rep = representations(hidden[0], msae)
            target_rep = representations(hidden[1], msae)
            delta, _ = cosine_matched_direction(source_rep["raw"], target_rep["raw"],
                seed=deterministic_seed(config["seed"], "pilot_random", transform["transform_id"]))
            representations(hidden[0].float() + torch.as_tensor(delta, device=device)[None, None, :], msae)
            representations(hidden[2], msae)
        functional_rows += 1
    torch.cuda.synchronize()
    functional_sec = time.monotonic() - functional_start

    mean_fit = float(np.mean(weighted_times))
    safety = 2.0
    # Fixed input verification is measured once over all four public-role
    # transform trees.  Production opens C2 too; the explicit 1.5 multiplier
    # accounts for that third, similarly sized role before the universal 2x.
    full_transform_all_jobs_fixed = 1.5 * k2_fixed_startup_sec
    full_raw_activation_fixed = 1.5 * raw_public_fixed_startup_sec
    baseline_gpu_hours = safety * (baseline_analogue_sec + full_transform_all_jobs_fixed
                                   + raw_public_fixed_startup_sec) / 3600
    raw_gpu_hours = safety * (float(np.mean(raw_draw_times)) * 500 * len(config["layers"])
                              + 8.0 * full_raw_activation_fixed) / 3600
    k2_gpu_hours = safety * (float(np.mean(k2_draw_times)) * 500 * len(
        config["primary_checkpoints"] + config["descriptive_checkpoints"])
        + 2.0 * full_transform_all_jobs_fixed) / 3600
    stability_gpu_hours = safety * (stability_draw_sec * 500
                                     + 4.0 * full_transform_all_jobs_fixed) / 3600
    specificity_gpu_hours = safety * ((functional_startup_sec + functional_sec) * 4
                                       + full_transform_all_jobs_fixed) / 3600
    merge_wall_hours = safety * (sensitivity_smoke_sec * (2000 / 32) + 60.0) / 3600
    verification_wall_hours = safety * (
        sensitivity_smoke_sec * (2000 / 32) + 180.0) / 3600
    render_wall_hours = safety * 60.0 / 3600
    total_gpu_hours = (baseline_gpu_hours + raw_gpu_hours + k2_gpu_hours
                       + stability_gpu_hours + specificity_gpu_hours)

    raw_payload_bytes = (sum(len(canonical_json_bytes(row)) for row in raw_draw_results)
                         / len(raw_draw_results) * 500 * len(config["layers"]))
    k2_payload_bytes = (sum(len(canonical_json_bytes(row)) for row in k2_draw_results)
                        / len(k2_draw_results) * 500
                        * len(config["primary_checkpoints"] + config["descriptive_checkpoints"]))
    stability_payload_bytes = 64 * 1024 * 501
    specificity_payload_bytes = functional_rows * 16 * 1024 * 4
    wrapper_registry_attestation_bytes = (2 * 1024 * (1000 + 2000 + 500)
                                          + 64 * 1024 * 64)
    verification_payload_bytes = 16 * 1024**2
    log_reserve_bytes = 1024**3
    scratch_bytes = safety * (raw_payload_bytes + k2_payload_bytes
                              + stability_payload_bytes + specificity_payload_bytes
                              + wrapper_registry_attestation_bytes
                              + verification_payload_bytes + log_reserve_bytes)
    promoted_bytes = safety * (512 * 1024**2)
    projected = {
        "safety_factor": safety,
        "fixed_input_verification_seconds_all_jobs_public_roles": k2_fixed_startup_sec,
        "fixed_raw_activation_calibration_seconds_public_roles": raw_public_fixed_startup_sec,
        "production_full_role_multiplier": 1.5,
        "baseline_gpu_hours": baseline_gpu_hours,
        "raw_gpu_hours": raw_gpu_hours,
        "k2_gpu_hours": k2_gpu_hours,
        "stability_gpu_hours": stability_gpu_hours,
        "specificity_gpu_hours": specificity_gpu_hours,
        "total_gpu_hours": total_gpu_hours,
        "baseline_stage_wall_hours_1_gpu": baseline_gpu_hours,
        "raw_stage_wall_hours_6_gpus": raw_gpu_hours / 6,
        "k2_stage_wall_hours_4_gpus": k2_gpu_hours / 4,
        "stability_stage_wall_hours_3_gpus": stability_gpu_hours / 3,
        "specificity_stage_wall_hours_4_gpus": specificity_gpu_hours / 4,
        "merge_stage_wall_hours_cpu": merge_wall_hours,
        "verification_stage_wall_hours_cpu": verification_wall_hours,
        "render_stage_wall_hours_cpu": render_wall_hours,
        "scratch_writes_gib": scratch_bytes / (1024**3),
        "promoted_output_gib": promoted_bytes / (1024**3),
        "new_storage_gib": (scratch_bytes + promoted_bytes) / (1024**3),
        "storage_components_bytes": {
            "raw_draw_payload": int(raw_payload_bytes),
            "k2_draw_payload": int(k2_payload_bytes),
            "stability_payload_conservative": int(stability_payload_bytes),
            "specificity_payload_conservative": int(specificity_payload_bytes),
            "wrappers_registries_attestations": int(wrapper_registry_attestation_bytes),
            "verification_payload_conservative": int(verification_payload_bytes),
            "logs_reserve": int(log_reserve_bytes),
        },
        "host_ram_gib": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / (1024**2),
        "gpu_peak_gib": torch.cuda.max_memory_allocated(0) / (1024**3),
    }
    numerical_pass = all(row["exact_prediction_agreement"] >= 0.999
                         and row["exact_macro_f1_abs_difference"] <= 0.001
                         and row["exact_relative_coefficient_error"] <= 0.001
                         and row["exact_relative_decision_error"] <= 0.001
                         and row["weighted_prediction_agreement"] >= 0.999
                         and row["weighted_macro_f1_abs_difference"] <= 0.001
                         and row["weighted_relative_coefficient_error"] <= 0.001
                         and row["weighted_relative_decision_error"] <= 0.001
                         and row["literal_replication_relative_coefficient_error"] <= 0.001
                         and row["parent_lsqr_macro_f1_abs_difference"] <= 0.001
                         for row in numerical.values()) and all(value <= 0.001 for value in projector_errors.values())
    numerical_pass = bool(numerical_pass and functional_rows == 128 and token_control_tokens > 0
                          and identity_ce_rows == 192 and max_identity_ce_error <= 1e-5
                          and two_draw_gpu_pass and cpu_two_draw_pass
                          and point_model_smoke_pass
                          and k2_two_draw_pass
                          and inference_helper_smoke_pass
                          and specificity_summary_smoke_pass and ce_aggregation_smoke_pass
                          and len(k2_fit_times) == 18 and cka_count == 45)
    budget = config["budgets"]
    stage_wall_hours = {key: value for key, value in projected.items()
                        if "stage_wall_hours" in key}
    stage_budget_pass = {stage: value <= budget["maximum_stage_wall_hours"]
                         for stage, value in stage_wall_hours.items()}
    budget_pass = (total_gpu_hours <= budget["maximum_total_gpu_hours"]
                   and all(stage_budget_pass.values())
                   and projected["host_ram_gib"] <= budget["maximum_host_ram_gib"]
                   and projected["new_storage_gib"] <= budget["maximum_new_storage_gib"])
    if snapshot_exercised_files() != exercised_files:
        raise RuntimeError("pilot/scoring implementation changed while pilot was running")
    parent_after = verify_parent_freeze_attested(
        firewall, ["discovery", "calibration"])
    verify_attestation_current(firewall.attestation)
    roles_read = roles_from_attestation(firewall.attestation)
    confirmation_roles_read = sorted(set(roles_read) & {"C1", "C2", "final"})
    numerical_pass = bool(numerical_pass and not confirmation_roles_read
                          and set(roles_read) == {"discovery", "calibration"})
    result = {"schema_version": "atlas_completion_pilot_v1", "evidence_class": EVIDENCE_CLASS,
              "roles_read": roles_read, "confirmation_roles_read": confirmation_roles_read,
              "numerical": numerical, "projector_errors": projector_errors, "numerical_pass": numerical_pass,
              "timing": {"ridge_grid_task_seconds": ridge_times, "weighted_fit_seconds": weighted_times,
                         "raw_end_to_end_draw_seconds": raw_draw_times,
                         "k2_end_to_end_draw_seconds": k2_draw_times,
                         "baseline_analogue_seconds": baseline_analogue_sec,
                         "raw_fixed_startup_seconds": raw_public_fixed_startup_sec,
                         "k2_fixed_startup_seconds": k2_fixed_startup_sec,
                         "k2_assigned_fit_seconds": k2_fit_times, "k2_fit_seconds": k2_fit_sec,
                         "stability_full_draw_seconds": stability_draw_sec,
                         "stability_cka_count": cka_count,
                         "cka_seconds": cka_sec, "cka_value": cka_value,
                         "functional_fixed_startup_seconds": functional_startup_sec,
                         "functional_128_rows_seconds": functional_sec, "functional_rows": functional_rows},
              "functional_checks": {"token_control_tokens": token_control_tokens,
                                    "identity_ce_rows": identity_ce_rows,
                                    "max_identity_ce_abs_error": max_identity_ce_error,
                                    "exact_point_model_bundle_smoke": point_model_smoke_pass,
                                    "specificity_group_summary_smoke": specificity_summary_smoke_pass,
                                    "ce_aggregation_smoke": ce_aggregation_smoke_pass},
              "inference_helper_checks": {"passes": inference_helper_smoke_pass,
                                            "negative_sensitivity": sensitivity_smoke,
                                            "intersection_union": iut_smoke},
              "two_draw_gpu_correctness": {"passes": two_draw_gpu_pass, "hashes": two_draw_hashes},
              "two_draw_k2_gpu_correctness": {
                  "passes": k2_two_draw_pass,
                  "hashes": k2_draw_hashes,
                  "finite_draws": sum(bool(row["finite"])
                                      for row in k2_draw_results),
                  "nonfinite_draws": sum(not bool(row["finite"])
                                         for row in k2_draw_results),
                  "interpretation": (
                      "pilot requires deterministic serialized finite/nonfinite "
                      "status; the registered 450-of-500 scientific gate is "
                      "enforced only by each complete score-bearing series"),
              },
              "two_draw_cpu_correctness": {"passes": cpu_two_draw_pass, "draws": cpu_two_draw},
              "exercised_files": exercised_files,
              "exercised_bundle_sha256": __import__("hashlib").sha256(canonical_json_bytes(exercised_files)).hexdigest(),
              "total_observed_seconds": time.monotonic() - pilot_started,
              "projected": projected, "stage_budget_pass": stage_budget_pass,
              "budget_pass": budget_pass,
              "config_sha256": sha256_file(config_path),
              "resolved_config": config,
              "resolved_arguments": {"device": args.device,
                                     "output": str(args.output.resolve())},
              "seed_provenance": seed_provenance(
                  config,
                  contract=("registered discovery/calibration pilot seeds; two raw and K2 "
                            "end-to-end draws use production deterministic_seed contracts")),
              "device": args.device, "started_utc": pilot_started_utc,
              "ended_utc": __import__("datetime").datetime.now(
                  __import__("datetime").timezone.utc).isoformat(),
              "environment": launch_environment,
              "parent_bundle_reverified_after_stage_sha256": parent_after["bundle_sha256"],
              "input_attestation": firewall.attestation}
    atomic_write_json(args.output / "pilot.json", result)
    result["resource_accounting"] = process_resource_accounting(
        args.output, elapsed_sec=time.monotonic() - pilot_started, device=args.device)
    complete, terminal_payload = pilot_terminal_payload(
        result, result_sha256=sha256_file(args.output / "pilot.json"),
        stage_budget_pass=stage_budget_pass)
    write_terminal(args.output, complete=complete, payload=terminal_payload)
    print(json.dumps({"numerical_pass": numerical_pass, "budget_pass": budget_pass,
                      "projected_total_gpu_hours": total_gpu_hours, "functional_seconds": functional_sec}, indent=2))


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        argv = __import__("sys").argv
        output = ROOT / "pilot_runs/20260801_atlas_completion_v1/pilot_v10"
        if "--output" in argv:
            output = Path(argv[argv.index("--output") + 1])
        write_failure_terminal(
            output, stop_code="pilot_unrecoverable_failure",
            failed_gate="pilot_numerical_and_resource_validation", error=exc,
            input_attestation=_FAILURE_ATTESTATION)
        raise
