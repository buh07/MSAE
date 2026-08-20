#!/usr/bin/env python3
"""GPU worker for deterministic discovery-refit raw/simple or K2 draw shards."""

from __future__ import annotations

import argparse
import json
import math
import pickle
import time
from pathlib import Path
from typing import Any, Mapping

import numpy as np

from msa_completion_common import (EVIDENCE_CLASS, ROOT,
                                   FrozenClassOmissionError,
                                   LiveDrawClaimError,
                                   StageTerminalError,
                                   atomic_write_bytes,
                                   atomic_write_json,
                                   attest_completion_freeze_record,
                                   chance_score, claim_draw, default_firewall,
                                   deterministic_seed, draw_group_multiplicities,
                                   family_summary, fit_weighted_ridge_torch,
                                   load_activation, load_row_file,
                                   maybe_finalize_draw_stage,
                                   normalized_recovery, orthonormal_basis,
                                   prepare_draw_resume,
                                   project_complement, project_coords, read_json,
                                   register_draw_artifact, release_claim,
                                   require_bound_stage_files,
                                   require_frozen_completion_config,
                                   require_registered_series_artifact,
                                   verify_parent_k2_audit,
                                   verify_parent_raw_calibration,
                                   verify_parent_transform,
                                   verify_parent_transform_roles,
                                   runtime_environment, sha256_file,
                                   seed_provenance,
                                   stage_publication_lock,
                                   source_equal_score, terminal_state,
                                   utc_now,
                                   unit_group_multiplicities,
                                   validated_cuda_environment,
                                   weights_from_multiplicities, write_terminal,
                                   weighted_mean_scale, write_failure_terminal)


PRIMARY = {
    "absolute_position": ["abs_pos_16", "abs_pos_8"],
    "relative_structural_position": ["relative_quartile", "head_signed_distance", "dependency_depth", "boundary_state"],
    "lexical_semantic_content": ["token_identity_256", "lemma_identity_256", "ner_coarse"],
}
TASKS = [task for tasks in PRIMARY.values() for task in tasks]
_FAILURE_ATTESTATION: dict[str, Any] = {}


def completion_rows(path: Path, firewall: Any, role: str) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    rows = [json.loads(line) for line in firewall.attest(path, role=role).read_text().splitlines()]
    return (np.asarray([row["activation_row"] for row in rows], dtype=np.int64),
            np.asarray([row["label"] for row in rows], dtype=str),
            np.asarray([row["source"] for row in rows], dtype=str),
            np.asarray([row["document_group"] for row in rows], dtype=str))


def scaler_sample(data: Any, layer: int, config: dict[str, Any]) -> np.ndarray:
    rng = np.random.default_rng(int(config["seed"]) + int(layer))
    return rng.choice(len(data.x), min(int(config["scaler_rows"]), len(data.x)), replace=False)


def k2_scaler_sample(length: int, job_index: int, rep_index: int, config: dict[str, Any]) -> np.ndarray:
    rng = np.random.default_rng(int(config["seed"]) + 100 * job_index + rep_index)
    return rng.choice(length, min(int(config["scaler_rows"]), length), replace=False)


def score_recovery(*, model: Any, raw_model: Any, rep_x: np.ndarray, raw_x: np.ndarray,
                   y_fit: np.ndarray, fit_sources: np.ndarray, fit_weights: np.ndarray,
                   y_eval: np.ndarray, eval_sources: np.ndarray, eval_weights: np.ndarray) -> tuple[float | None, dict[str, Any]]:
    fit_weights = np.asarray(fit_weights, dtype=np.float64)
    eval_weights = np.asarray(eval_weights, dtype=np.float64)
    if (len(fit_weights) != len(y_fit) or len(fit_sources) != len(y_fit)
            or not np.isfinite(fit_weights).all()
            or np.any(fit_weights < 0)):
        raise ValueError("fit recovery weights must be finite, nonnegative, and aligned")
    if (len(eval_weights) != len(y_eval) or len(eval_sources) != len(y_eval)
            or not np.isfinite(eval_weights).all()
            or np.any(eval_weights < 0)):
        raise ValueError("eval recovery weights must be finite, nonnegative, and aligned")
    rep_pred, raw_pred = model.predict(rep_x), raw_model.predict(raw_x)
    by_source: dict[str, Any] = {}
    recoveries = []
    fixed_sources = sorted(np.unique(eval_sources).tolist())
    if fit_weights.sum() <= 0:
        for source in fixed_sources:
            by_source[source] = {
                "raw": None, "component": None, "chance": None,
                "recovery": None, "invalid_reason": "zero_discovery_weight",
            }
        return None, {"invalid_fit": "zero discovery weight", "by_source": by_source}
    invalid_sources: list[str] = []
    for source in fixed_sources:
        em = eval_sources == source
        if eval_weights[em].sum() <= 0:
            by_source[source] = {
                "raw": None, "component": None, "chance": None,
                "recovery": None, "invalid_reason": "zero_evaluation_weight",
            }
            invalid_sources.append(source)
            continue
        try:
            raw = source_equal_score(
                y_eval[em], raw_pred[em], np.asarray([source] * em.sum()),
                eval_weights[em])
            component = source_equal_score(
                y_eval[em], rep_pred[em], np.asarray([source] * em.sum()),
                eval_weights[em])
            chance = chance_score(
                y_fit, y_eval[em], fit_weights, eval_weights[em])
        except FrozenClassOmissionError as exc:
            by_source[source] = {
                "raw": None, "component": None, "chance": None,
                "recovery": None,
                "invalid_reason": f"metric_undefined:{exc}",
            }
            invalid_sources.append(source)
            continue
        recovery = None if raw is None or component is None else normalized_recovery(component, raw, chance)
        by_source[source] = {"raw": raw, "component": component, "chance": chance, "recovery": recovery}
        if recovery is None:
            by_source[source]["invalid_reason"] = "undefined_normalized_recovery"
            invalid_sources.append(source)
        else:
            recoveries.append(recovery)
    if invalid_sources:
        return None, {"invalid_sources": invalid_sources, "by_source": by_source}
    return float(np.mean(recoveries)), {"by_source": by_source}


def fit_raw_models(discovery: Any, rows: Mapping[str, tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]],
                   standardized: Mapping[str, np.ndarray], weights: Mapping[str, np.ndarray],
                   raw_alpha: Mapping[str, float], device: str) -> dict[str, Any]:
    return {task: fit_weighted_ridge_torch(standardized[task], rows[task][1], weights[task], float(raw_alpha[task]), device)
            for task in TASKS}


def build_bases(raw_models: Mapping[str, Any], config: dict[str, Any], pca_sample: np.ndarray | None = None,
                pca_weights: np.ndarray | None = None, device: str = "cuda:0") -> dict[str, np.ndarray]:
    bases: dict[str, np.ndarray] = {}
    for family, tasks in PRIMARY.items():
        bases[family] = orthonormal_basis(np.concatenate([raw_models[t].coef for t in tasks], axis=0), int(config["family_rank"]))
    bases["broad_position"] = orthonormal_basis(
        np.concatenate([raw_models[t].coef for t in PRIMARY["absolute_position"] + PRIMARY["relative_structural_position"]], axis=0),
        int(config["position_rank"]),
    )
    bases["split_position_joint"] = orthonormal_basis(
        np.concatenate([bases["absolute_position"].T, bases["relative_structural_position"].T], axis=0),
        int(config["position_rank"]),
    )
    if pca_sample is not None and pca_weights is not None:
        import torch

        torch.backends.cuda.matmul.allow_tf32 = False
        x = torch.as_tensor(np.asarray(pca_sample, np.float32), device=device, dtype=torch.float64)
        w = torch.as_tensor(np.asarray(pca_weights, np.float64), device=device, dtype=torch.float64)
        keep = w > 0
        x, w = x[keep], w[keep]
        mean = (x * w[:, None]).sum(0) / w.sum()
        xc = (x - mean) * torch.sqrt(w[:, None])
        gram = xc.T @ xc
        _, vectors = torch.linalg.eigh(gram)
        bases["pca16"] = vectors[:, -int(config["position_rank"]):].flip(1).cpu().numpy().astype(np.float32)
    return bases


def rep_matrix(x: np.ndarray, rep: str, bases: Mapping[str, np.ndarray]) -> np.ndarray:
    if rep.endswith("complement"):
        prefix = rep.split("_", 1)[0]
        basis_name = {"broad": "broad_position", "split": "split_position_joint", "pca": "pca16"}[prefix]
        return project_complement(x, bases[basis_name])
    return project_coords(x, bases[rep])


def simple_roundtrip_checks(x: np.ndarray, bases: Mapping[str, np.ndarray], tolerance: float) -> dict[str, Any]:
    candidate_basis = {"projection_broad16": "broad_position",
                       "projection_split8_8": "split_position_joint",
                       "pca16_complement": "pca16"}
    values = np.asarray(x, dtype=np.float32)
    output: dict[str, Any] = {}
    for candidate, basis_name in candidate_basis.items():
        basis = np.asarray(bases[basis_name], dtype=np.float32)
        projected = (values @ basis) @ basis.T
        reconstructed = projected + (values - projected)
        relative = np.linalg.norm(reconstructed - values, axis=1) / np.maximum(np.linalg.norm(values, axis=1), 1e-12)
        orthonormal_error = float(np.linalg.norm(basis.T @ basis - np.eye(basis.shape[1]), ord="fro"))
        error = max(float(np.max(relative)), orthonormal_error)
        output[candidate] = {"max_relative_reconstruction_error": float(np.max(relative)),
                             "orthonormal_frobenius_error": orthonormal_error,
                             "gate_value": error, "passes": bool(np.isfinite(error) and error <= tolerance)}
    return output


def family_rows(recovery: Mapping[str, Mapping[str, float | None]], mapping: Mapping[str, str],
                eligible_tasks: set[str]) -> dict[str, Any]:
    output = {}
    for family, tasks in PRIMARY.items():
        tasks = [task for task in tasks if task in eligible_tasks]
        if len(tasks) < 2:
            output[family] = {"assigned_recovery": None, "leakage": None, "selectivity_margin": None,
                              "leakage_by_representation": {}, "invalid_reason": "fewer_than_two_eligible_tasks"}
            continue
        assigned = mapping[family]
        nonassigned = sorted({mapping[other] for other in PRIMARY if other != family})
        output[family] = family_summary(recovery, assigned, nonassigned, tasks)
    return output


def raw_draw(draw: int | None, layer: int, config: dict[str, Any], baseline: dict[str, Any], manifest: dict[str, Any],
             discovery: Any, eval_data: Any, c2: Any | None, raw_bundle: dict[str, Any], device: str,
             firewall: Any, *, eval_role: str = "C1",
             collateral_role: str = "C2",
             model_sink: dict[str, Any] | None = None) -> dict[str, Any]:
    if eval_role not in {"calibration", "C1"}:
        raise ValueError(f"invalid raw evaluation role: {eval_role}")
    roles = {"discovery": discovery, eval_role: eval_data}
    if collateral_role not in {"calibration", "C2"}:
        raise ValueError(f"invalid collateral role: {collateral_role}")
    if c2 is not None:
        roles[collateral_role] = c2
    task_manifest = read_json(firewall.attest(ROOT / "configs/atlas/task_row_manifest.json"))
    task_rows: dict[str, dict[str, tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]]] = {role: {} for role in roles}
    for role, data in roles.items():
        for task in TASKS:
            task_rows[role][task] = load_row_file(ROOT / task_manifest["roles"][role][task]["path"], data, firewall, role=role)

    mult = {role: (unit_group_multiplicities(data.row_source.astype(str), data.row_group.astype(str)) if draw is None else
                   draw_group_multiplicities(data.row_source.astype(str), data.row_group.astype(str),
                                             seed=deterministic_seed(config["seed"], role, layer, draw)))
            for role, data in roles.items()}
    sample_rows = scaler_sample(discovery, layer, config)
    sample_weights = weights_from_multiplicities(discovery.row_source[sample_rows], discovery.row_group[sample_rows], mult["discovery"])
    mean, scale = weighted_mean_scale(np.asarray(discovery.x[sample_rows], np.float32), sample_weights)
    standardized: dict[str, dict[str, np.ndarray]] = {role: {} for role in roles}
    weights: dict[str, dict[str, np.ndarray]] = {role: {} for role in roles}
    for role, data in roles.items():
        for task in TASKS:
            rows, _, sources, groups = task_rows[role][task]
            standardized[role][task] = (np.asarray(data.x[rows], np.float32) - mean) / scale
            weights[role][task] = weights_from_multiplicities(sources, groups, mult[role])
    raw_alpha = raw_bundle["raw_alpha"] if "raw_alpha" in raw_bundle else None
    if raw_alpha is None:
        # Parent pickle stores models but the JSON freeze stores selected raw alphas.
        raw_alpha = read_json(firewall.attest(ROOT / f"results/atlas/raw_v1/L{layer}_calibration_freeze.json"))["raw_alpha"]
    raw_models = fit_raw_models(discovery, task_rows["discovery"], standardized["discovery"], weights["discovery"], raw_alpha, device)
    pca_sample = (np.asarray(discovery.x[sample_rows], np.float32) - mean) / scale
    bases = build_bases(raw_models, config, pca_sample, sample_weights, device)
    if model_sink is not None:
        model_sink.update({"mean": mean, "scale": scale, "bases": bases,
                           "raw_models": raw_models, "component_models": {}})
    roundtrip = simple_roundtrip_checks(pca_sample[: min(4096, len(pca_sample))], bases,
                                        float(config["roundtrip_tolerance"]))
    mappings = {
        "split": {"absolute_position": "absolute_position", "relative_structural_position": "relative_structural_position", "lexical_semantic_content": "split_complement"},
        "broad": {"absolute_position": "broad_position", "relative_structural_position": "broad_position", "lexical_semantic_content": "broad_complement"},
    }
    component_alpha = raw_bundle["component_alpha"]
    needed_reps = sorted({rep for mapping in mappings.values() for rep in mapping.values()})
    recovery: dict[str, dict[str, float | None]] = {rep: {} for rep in needed_reps}
    detail: dict[str, Any] = {}
    for rep in needed_reps:
        for task in TASKS:
            dx = rep_matrix(standardized["discovery"][task], rep, bases)
            ex = rep_matrix(standardized[eval_role][task], rep, bases)
            model = fit_weighted_ridge_torch(dx, task_rows["discovery"][task][1], weights["discovery"][task],
                                             float(component_alpha[rep][task]), device)
            if model_sink is not None:
                model_sink["component_models"].setdefault(rep, {})[task] = model
            value, row = score_recovery(model=model, raw_model=raw_models[task], rep_x=ex, raw_x=standardized[eval_role][task],
                                        y_fit=task_rows["discovery"][task][1], fit_sources=task_rows["discovery"][task][2],
                                        fit_weights=weights["discovery"][task], y_eval=task_rows[eval_role][task][1],
                                        eval_sources=task_rows[eval_role][task][2], eval_weights=weights[eval_role][task])
            recovery[rep][task] = value
            detail[f"{rep}:{task}"] = row
    eligible_tasks = {task for task, row in baseline["tier1_eligibility"].items() if row["eligible"]}
    raw_g1 = {name: family_rows(recovery, mapping, eligible_tasks) for name, mapping in mappings.items()}
    required_g1_recoveries = [recovery[rep][task] for rep in needed_reps for task in eligible_tasks]
    finite = bool(required_g1_recoveries
                  and all(value is not None and math.isfinite(float(value)) for value in required_g1_recoveries)
                  and all(row["passes"] for row in roundtrip.values()))
    output: dict[str, Any] = {"raw_g1": raw_g1,
                              "recoveries": recovery,
                              "mappings": mappings,
                              "simple_roundtrip": roundtrip,
                              "source_detail": detail, "finite": finite}

    if c2 is not None:
        candidate = baseline["selected_simple_baseline"]
        if candidate == "projection_broad16":
            selected_map = mappings["broad"]
        elif candidate == "projection_split8_8":
            selected_map = mappings["split"]
        else:
            selected_map = {family: "pca16" if family != "lexical_semantic_content" else "pca_complement" for family in PRIMARY}
        selected_reps = sorted(set(selected_map.values()))
        simple_recovery: dict[str, dict[str, float | None]] = {rep: {} for rep in selected_reps}
        raw_tier1: dict[str, Any] = {}
        simple_detail: dict[str, Any] = {}
        for rep in selected_reps:
            for task in TASKS:
                dx = rep_matrix(standardized["discovery"][task], rep, bases)
                ex = rep_matrix(standardized[collateral_role][task], rep, bases)
                model = fit_weighted_ridge_torch(dx, task_rows["discovery"][task][1], weights["discovery"][task],
                                                 float(component_alpha[rep][task]), device)
                value, score_row = score_recovery(model=model, raw_model=raw_models[task], rep_x=ex, raw_x=standardized[collateral_role][task],
                                                  y_fit=task_rows["discovery"][task][1], fit_sources=task_rows["discovery"][task][2],
                                                  fit_weights=weights["discovery"][task], y_eval=task_rows[collateral_role][task][1],
                                                  eval_sources=task_rows[collateral_role][task][2], eval_weights=weights[collateral_role][task])
                simple_recovery[rep][task] = value
                simple_detail[f"{rep}:{task}"] = score_row
                raw_tier1.setdefault(task, score_row)
        output["simple_c2"] = {"families": family_rows(simple_recovery, selected_map, eligible_tasks), "candidate": candidate,
                               "recoveries": simple_recovery,
                               "source_detail": simple_detail,
                               "mapping": selected_map,
                               "raw_tier1": raw_tier1}

        # Tier-2 assigned collateral on C2, including raw leaf scores for K2 pairing.
        sent_rows = {role: {} for role in ["discovery", collateral_role]}
        for role, data in [("discovery", discovery), (collateral_role, c2)]:
            for task in config["sentinels"]:
                sent_rows[role][task] = completion_rows(ROOT / manifest["roles"][role][task]["path"], firewall, role)
        sentinel_out = {}
        for task in config["sentinels"]:
            dr, dy, ds, dg = sent_rows["discovery"][task]
            er, ey, es, eg = sent_rows[collateral_role][task]
            dw = weights_from_multiplicities(ds, dg, mult["discovery"])
            ew = weights_from_multiplicities(es, eg, mult[collateral_role])
            dx_raw = (np.asarray(discovery.x[dr], np.float32) - mean) / scale
            ex_raw = (np.asarray(c2.x[er], np.float32) - mean) / scale
            raw_model = fit_weighted_ridge_torch(dx_raw, dy, dw, float(baseline["sentinel_alphas"]["raw"][task]), device)
            mapped = config["sentinel_mapping"][task]
            rep = (selected_map["absolute_position"] if mapped == "position" else selected_map["lexical_semantic_content"])
            dx, ex = rep_matrix(dx_raw, rep, bases), rep_matrix(ex_raw, rep, bases)
            model = fit_weighted_ridge_torch(dx, dy, dw, float(baseline["sentinel_alphas"]["simple"][candidate][task]), device)
            raw_pred, comp_pred = raw_model.predict(ex_raw), model.predict(ex)
            invalid_reasons: list[str] = []
            try:
                raw_f1 = source_equal_score(ey, raw_pred, es, ew)
            except FrozenClassOmissionError as exc:
                raw_f1 = None
                invalid_reasons.append(f"raw_metric_undefined:{exc}")
            try:
                comp_f1 = source_equal_score(ey, comp_pred, es, ew)
            except FrozenClassOmissionError as exc:
                comp_f1 = None
                invalid_reasons.append(f"component_metric_undefined:{exc}")
            chance_sources = []
            for source in sorted(np.unique(es).tolist()):
                em = es == source
                if dw.sum() <= 0 or ew[em].sum() <= 0:
                    chance_sources = []
                    invalid_reasons.append(f"chance_weight_undefined:{source}")
                    break
                try:
                    chance_sources.append(chance_score(dy, ey[em], dw, ew[em]))
                except FrozenClassOmissionError as exc:
                    chance_sources = []
                    invalid_reasons.append(
                        f"chance_metric_undefined:{source}:{exc}")
                    break
            chance = float(np.mean(chance_sources)) if chance_sources else None
            damage = None if raw_f1 is None or comp_f1 is None or chance is None or raw_f1 <= chance else (raw_f1 - comp_f1) / (raw_f1 - chance)
            sentinel_out[task] = {
                "raw": raw_f1, "component": comp_f1, "chance": chance,
                "normalized_damage": damage,
                "invalid_reasons": invalid_reasons,
            }
        output["simple_c2"]["sentinels"] = sentinel_out
        output["simple_c2"]["evaluation_role"] = collateral_role
        required_simple = [simple_recovery[rep][task] for rep in selected_reps for task in eligible_tasks]
        required_damage = [row["normalized_damage"] for row in sentinel_out.values()]
        output["finite"] = bool(output["finite"] and required_simple and required_damage
                                and all(value is not None and math.isfinite(float(value))
                                        for value in required_simple + required_damage))
    return output


def k2_draw(draw: int | None, job: str, config: dict[str, Any], baseline: dict[str, Any], manifest: dict[str, Any],
            discovery: Any, c2: Any, source_run_root: Path, device: str, firewall: Any, *,
            eval_role: str = "C2", raw_result_override: dict[str, Any] | None = None,
            parent_alpha_override: dict[str, Any] | None = None) -> dict[str, Any]:
    if eval_role not in {"calibration", "C2"}:
        raise ValueError(f"invalid K2 evaluation role: {eval_role}")
    job_order = config["primary_checkpoints"] + config["descriptive_checkpoints"]
    job_index = job_order.index(job)
    if parent_alpha_override is None:
        verify_parent_transform(source_run_root, job, firewall)
        parent = verify_parent_k2_audit(source_run_root, job, firewall)
        alpha = parent["alpha_selection"]
    else:
        if eval_role != "calibration":
            raise PermissionError("parent alpha override is pilot-only")
        verify_parent_transform_roles(source_run_root, job, ["discovery", "calibration"], firewall)
        alpha = parent_alpha_override
    task_manifest = read_json(firewall.attest(ROOT / "configs/atlas/task_row_manifest.json"))
    rows = {role: {task: load_row_file(ROOT / task_manifest["roles"][role][task]["path"], data, firewall, role=role)
                   for task in TASKS} for role, data in [("discovery", discovery), (eval_role, c2)]}
    mult = {role: (unit_group_multiplicities(data.row_source.astype(str), data.row_group.astype(str)) if draw is None else
                   draw_group_multiplicities(data.row_source.astype(str), data.row_group.astype(str),
                                             seed=deterministic_seed(config["seed"], role, 3, draw)))
            for role, data in [("discovery", discovery), (eval_role, c2)]}
    arrays = {role: {rep: np.load(firewall.attest(source_run_root / "k2_transforms" / job / role / f"{rep}.float16.npy", role=role), mmap_mode="r")
                     for rep in ["pos", "content"]} for role in ["discovery", eval_role]}
    scaling = {}
    for rep_index, rep in enumerate(["pos", "content"]):
        sample = k2_scaler_sample(len(arrays["discovery"][rep]), job_index, rep_index, config)
        sw = weights_from_multiplicities(discovery.row_source[sample], discovery.row_group[sample], mult["discovery"])
        scaling[rep] = weighted_mean_scale(np.asarray(arrays["discovery"][rep][sample], np.float32), sw)
    recovery: dict[str, dict[str, float | None]] = {"pos": {}, "content": {}}
    detail = {}
    # Raw leaves are loaded from the paired raw draw, avoiding a second raw refit.
    raw_chunk = (ROOT / config["run_root"] / "raw_refit" / "L3" / "point.json" if draw is None else
                 ROOT / config["run_root"] / "raw_refit" / "L3" / "draws" / f"{draw:04d}.json")
    if raw_result_override is None:
        require_registered_series_artifact(
            ROOT / config["run_root"] / "raw_refit/L3", raw_chunk,
            draw_id="point" if draw is None else int(draw), firewall=firewall,
            config_sha256=sha256_file(ROOT / "configs/atlas_completion/analysis.json"),
            completion_bundle_sha256=baseline["completion_bundle_sha256"])
    raw_result = raw_result_override if raw_result_override is not None else read_json(firewall.attest(raw_chunk))
    for task in TASKS:
        dr, dy, ds, dg = rows["discovery"][task]
        er, ey, es, eg = rows[eval_role][task]
        dw = weights_from_multiplicities(ds, dg, mult["discovery"])
        ew = weights_from_multiplicities(es, eg, mult[eval_role])
        for rep in ["pos", "content"]:
            mean, scale = scaling[rep]
            dx = (np.asarray(arrays["discovery"][rep][dr], np.float32) - mean) / scale
            ex = (np.asarray(arrays[eval_role][rep][er], np.float32) - mean) / scale
            model = fit_weighted_ridge_torch(dx, dy, dw, float(alpha[rep][task]["selected"]), device)
            pred = model.predict(ex)
            values = []
            source_rows = {}
            all_sources_valid = True
            raw_detail = raw_result["result"]["simple_c2"]["raw_tier1"][task]
            for source in sorted(np.unique(es).tolist()):
                mask = es == source
                invalid_reason = None
                try:
                    component = source_equal_score(
                        ey[mask], pred[mask],
                        np.asarray([source] * mask.sum()), ew[mask])
                except FrozenClassOmissionError as exc:
                    component = None
                    invalid_reason = f"component_metric_undefined:{exc}"
                raw_leaf = raw_detail["by_source"].get(source)
                value = (None if (component is None or raw_leaf is None
                                  or raw_leaf.get("raw") is None
                                  or raw_leaf.get("chance") is None)
                         else normalized_recovery(
                             component, raw_leaf["raw"], raw_leaf["chance"]))
                source_rows[source] = {
                    "component": component, "raw": raw_leaf,
                    "recovery": value, "invalid_reason": invalid_reason,
                }
                if value is None:
                    all_sources_valid = False
                else:
                    values.append(value)
            recovery[rep][task] = (float(np.mean(values))
                                   if all_sources_valid and values else None)
            detail[f"{rep}:{task}"] = source_rows
    mapping = {family: ("content" if family == "lexical_semantic_content" else "pos") for family in PRIMARY}
    eligible_tasks = {task for task, row in baseline["tier1_eligibility"].items() if row["eligible"]}
    families = {}
    for family, family_tasks_all in PRIMARY.items():
        family_tasks = [task for task in family_tasks_all if task in eligible_tasks]
        assigned = mapping[family]
        other = "content" if assigned == "pos" else "pos"
        families[family] = (family_summary(recovery, assigned, [other], family_tasks)
                            if len(family_tasks) >= 2 else
                            {"assigned_recovery": None, "leakage": None, "selectivity_margin": None,
                             "leakage_by_representation": {}, "invalid_reason": "fewer_than_two_eligible_tasks"})

    sentinel_rows = {role: {task: completion_rows(ROOT / manifest["roles"][role][task]["path"], firewall, role)
                            for task in config["sentinels"]} for role in ["discovery", eval_role]}
    sentinels = {}
    for task in config["sentinels"]:
        rep = baseline["sentinel_alphas"]["k2"][job][task]["representation"]
        dr, dy, ds, dg = sentinel_rows["discovery"][task]
        er, ey, es, eg = sentinel_rows[eval_role][task]
        dw = weights_from_multiplicities(ds, dg, mult["discovery"])
        ew = weights_from_multiplicities(es, eg, mult[eval_role])
        mean, scale = scaling[rep]
        dx = (np.asarray(arrays["discovery"][rep][dr], np.float32) - mean) / scale
        ex = (np.asarray(arrays[eval_role][rep][er], np.float32) - mean) / scale
        model = fit_weighted_ridge_torch(dx, dy, dw, float(baseline["sentinel_alphas"]["k2"][job][task]["alpha"]), device)
        invalid_reason = None
        try:
            component = source_equal_score(ey, model.predict(ex), es, ew)
        except FrozenClassOmissionError as exc:
            component = None
            invalid_reason = f"component_metric_undefined:{exc}"
        raw_leaf = raw_result["result"]["simple_c2"]["sentinels"][task]
        damage = None if component is None or raw_leaf["raw"] is None or raw_leaf["chance"] is None or raw_leaf["raw"] <= raw_leaf["chance"] else (raw_leaf["raw"] - component) / (raw_leaf["raw"] - raw_leaf["chance"])
        sentinels[task] = {"representation": rep, "component": component, "raw": raw_leaf["raw"],
                           "chance": raw_leaf["chance"], "normalized_damage": damage,
                           "invalid_reason": invalid_reason}
    required_recovery = [recovery[rep][task] for rep in ["pos", "content"] for task in eligible_tasks]
    required_damage = [row["normalized_damage"] for row in sentinels.values()]
    finite = bool(required_recovery and required_damage
                  and all(value is not None and math.isfinite(float(value))
                          for value in required_recovery + required_damage))
    return {"families": families, "recoveries": recovery, "source_detail": detail,
            "sentinels": sentinels, "evaluation_role": eval_role, "finite": finite}


def main() -> None:
    global _FAILURE_ATTESTATION
    parser = argparse.ArgumentParser()
    parser.add_argument("--kind", choices=["raw", "k2"], required=True)
    parser.add_argument("--layer", type=int, default=3)
    parser.add_argument("--job")
    parser.add_argument("--draw-start", type=int)
    parser.add_argument("--draw-end", type=int)
    parser.add_argument("--point", action="store_true")
    parser.add_argument("--device", default="cuda:0")
    parser.add_argument("--config", type=Path, default=ROOT / "configs/atlas_completion/analysis.json")
    args = parser.parse_args()
    completion_freeze = require_frozen_completion_config(args.config)
    config = read_json(args.config)
    if not args.point and (args.draw_start is None or args.draw_end is None or not (0 <= args.draw_start < args.draw_end <= int(config["draws"]))):
        raise ValueError("draw shard outside 0..499")
    if args.kind == "k2" and (args.job not in config["primary_checkpoints"] + config["descriptive_checkpoints"] or args.layer != 3):
        raise ValueError("invalid K2 job/layer")
    stage_dir = ROOT / config["run_root"] / ("raw_refit" if args.kind == "raw" else "k2_refit")
    stage_dir = stage_dir / (f"L{args.layer}" if args.kind == "raw" else str(args.job))
    stage_dir.mkdir(parents=True, exist_ok=True)
    if terminal_state(stage_dir) is not None:
        raise RuntimeError(f"stage is terminal: {stage_dir}")
    draw_dir = stage_dir / "draws"
    draw_dir.mkdir(exist_ok=True)
    config_sha = sha256_file(args.config)
    source_run_root = ROOT / config["source_run_root"]
    firewall = default_firewall(source_run_root, ROOT / config["run_root"])
    _FAILURE_ATTESTATION = firewall.attestation
    attest_completion_freeze_record(firewall, completion_freeze)
    launch_environment = validated_cuda_environment(args.device)
    firewall.register_root(ROOT / "data/atlas_completion_v1")
    firewall.attest(args.config)
    manifest = read_json(firewall.attest(ROOT / "data/atlas_completion_v1/tier2_manifest.json"))
    require_bound_stage_files(
        ROOT / config["run_root"] / "baseline", firewall,
        config_sha256=config_sha,
        completion_bundle_sha256=completion_freeze["bundle_sha256"],
        expected_files={"result_sha256": "baseline.json",
                        "bundle_sha256": "baseline_bundle.pkl"})
    with firewall.attest(ROOT / config["run_root"] / "baseline/baseline_bundle.pkl").open("rb") as handle:
        baseline = pickle.load(handle)
    if baseline.get("completion_bundle_sha256") != completion_freeze["bundle_sha256"]:
        raise RuntimeError("baseline bundle is not bound to the completion freeze")
    discovery = load_activation("discovery", args.layer, source_run_root, firewall)
    eval_role = "C1" if args.kind == "raw" else "C2"
    eval_data = load_activation(eval_role, args.layer, source_run_root, firewall)
    c2 = load_activation("C2", 3, source_run_root, firewall) if args.kind == "raw" and args.layer == 3 else None
    if args.kind == "raw":
        verify_parent_raw_calibration(source_run_root, firewall)
        with firewall.attest(ROOT / f"results/atlas/raw_v1/L{args.layer}_calibration_bundle.pkl").open("rb") as handle:
            raw_bundle = pickle.load(handle)
    else:
        raw_bundle = None
    if args.point:
        point_path = stage_dir / "point.json"
        if point_path.exists():
            raise FileExistsError(f"point output exists: {point_path}")
        started = time.monotonic()
        started_utc = utc_now()
        point_models: dict[str, Any] | None = {} if args.kind == "raw" else None
        result = (raw_draw(None, args.layer, config, baseline, manifest, discovery, eval_data, c2, raw_bundle, args.device, firewall,
                           eval_role=eval_role, model_sink=point_models)
                  if args.kind == "raw" else
                  k2_draw(None, str(args.job), config, baseline, manifest, discovery, eval_data, source_run_root, args.device, firewall))
        point_model_sha = None
        with stage_publication_lock(stage_dir):
            if terminal_state(stage_dir) is not None:
                return
            if point_models is not None:
                point_models.update({"schema_version": "atlas_completion_exact_raw_point_models_v1",
                                     "layer": args.layer, "config_sha256": config_sha,
                                     "completion_bundle_sha256": completion_freeze["bundle_sha256"]})
                point_model_path = stage_dir / "point_models.pkl"
                atomic_write_bytes(point_model_path, pickle.dumps(point_models, protocol=5))
                point_model_sha = sha256_file(point_model_path)
            atomic_write_json(point_path, {"schema_version": "atlas_completion_refit_point_v1", "evidence_class": EVIDENCE_CLASS,
                                       "kind": args.kind, "layer": args.layer, "job": args.job, "draw_id": "point",
                                       "config_sha256": config_sha,
                                       "resolved_config": config,
                                       "resolved_arguments": {"kind": args.kind, "layer": args.layer,
                                                              "job": args.job, "point": True,
                                                              "device": args.device},
                                       "seed_provenance": seed_provenance(
                                           config, contract=(
                                               "unit document-group weights; fixed scaler sample seeds are "
                                               "base_seed+layer for raw and base_seed+100*job_index+rep_index for K2")),
                                       "device": args.device,
                                       "completion_bundle_sha256": completion_freeze["bundle_sha256"], "result": result,
                                       "point_models_sha256": point_model_sha,
                                       "elapsed_sec": time.monotonic() - started,
                                       "started_utc": started_utc,
                                       "ended_utc": utc_now(),
                                       "environment": launch_environment,
                                       "input_attestation": firewall.attestation})
        maybe_finalize_draw_stage(stage_dir, requested_draws=int(config["draws"]),
                                  minimum_complete_draws=int(config["minimum_complete_draws"]),
                                  config_sha256=config_sha,
                                  completion_bundle_sha256=completion_freeze["bundle_sha256"],
                                  schema_version="atlas_completion_refit_terminal_v1",
                                  expected_shards=([(0, 167), (167, 334), (334, 500)]
                                                   if args.kind == "raw" else [(0, 500)]),
                                  extra={"kind": args.kind, "layer": args.layer, "job": args.job})
        print(json.dumps({"stage": str(stage_dir), "point": True, "elapsed_sec": time.monotonic() - started}, indent=2))
        return
    completed, failed = [], []
    shard_started = time.monotonic()
    shard_started_utc = utc_now()
    for draw in range(args.draw_start, args.draw_end):
        if terminal_state(stage_dir) is not None:
            return
        output = draw_dir / f"{draw:04d}.json"
        resume_state = prepare_draw_resume(stage_dir, draw, config_sha256=config_sha,
                                           completion_bundle_sha256=completion_freeze["bundle_sha256"])
        if resume_state == "complete":
            completed.append(draw)
            continue
        if resume_state == "failed":
            failed.append(draw)
            continue
        claim = claim_draw(stage_dir, draw, config_sha)
        started = time.monotonic()
        draw_started_utc = utc_now()
        try:
            result = (raw_draw(draw, args.layer, config, baseline, manifest, discovery, eval_data, c2, raw_bundle, args.device, firewall,
                               eval_role=eval_role)
                      if args.kind == "raw" else
                      k2_draw(draw, str(args.job), config, baseline, manifest, discovery, eval_data, source_run_root, args.device, firewall))
            bootstrap_roles = (["discovery", eval_role, "C2"]
                               if args.kind == "raw" and args.layer == 3
                               else ["discovery", eval_role])
            derived_seeds = {
                role: deterministic_seed(config["seed"], role, args.layer, draw)
                for role in sorted(set(bootstrap_roles))
            }
            row = {"schema_version": "atlas_completion_refit_draw_v1", "evidence_class": EVIDENCE_CLASS,
                   "kind": args.kind, "layer": args.layer, "job": args.job, "draw_id": draw,
                   "config_sha256": config_sha, "completion_bundle_sha256": completion_freeze["bundle_sha256"],
                   "resolved_config": config,
                   "resolved_arguments": {"kind": args.kind, "layer": args.layer,
                                          "job": args.job, "point": False,
                                          "draw_id": draw, "device": args.device},
                   "seed_provenance": seed_provenance(
                       config,
                       contract="deterministic_seed(base_seed, role, layer, draw_id)",
                       derived=derived_seeds),
                   "device": args.device,
                   "result": result, "elapsed_sec": time.monotonic() - started,
                   "started_utc": draw_started_utc, "ended_utc": utc_now(),
                   "environment": launch_environment,
                   "input_attestation": dict(firewall.attestation)}
            with stage_publication_lock(stage_dir):
                if terminal_state(stage_dir) is not None:
                    return
                atomic_write_json(output, row)
                register_draw_artifact(stage_dir, draw, output, status="complete",
                                       config_sha256=config_sha,
                                       completion_bundle_sha256=completion_freeze["bundle_sha256"])
                completed.append(draw)
        except Exception as exc:
            bootstrap_roles = (["discovery", eval_role, "C2"]
                               if args.kind == "raw" and args.layer == 3
                               else ["discovery", eval_role])
            derived_seeds = {
                role: deterministic_seed(config["seed"], role, args.layer, draw)
                for role in sorted(set(bootstrap_roles))
            }
            error = {"schema_version": "atlas_completion_refit_draw_error_v1",
                     "evidence_class": EVIDENCE_CLASS, "draw_id": draw,
                     "error_type": type(exc).__name__, "error": str(exc), "elapsed_sec": time.monotonic() - started,
                     "started_utc": draw_started_utc, "ended_utc": utc_now(),
                     "environment": launch_environment,
                     "config_sha256": config_sha,
                     "resolved_config": config,
                     "resolved_arguments": {"kind": args.kind, "layer": args.layer,
                                            "job": args.job, "point": False,
                                            "draw_id": draw, "device": args.device},
                     "seed_provenance": seed_provenance(
                         config,
                         contract="deterministic_seed(base_seed, role, layer, draw_id)",
                         derived=derived_seeds),
                     "device": args.device,
                     "completion_bundle_sha256": completion_freeze["bundle_sha256"],
                     "input_attestation": dict(firewall.attestation)}
            error_path = stage_dir / "errors" / f"{draw:04d}.json"
            with stage_publication_lock(stage_dir):
                if terminal_state(stage_dir) is not None:
                    return
                atomic_write_json(error_path, error)
                register_draw_artifact(stage_dir, draw, error_path, status="failed",
                                       config_sha256=config_sha,
                                       completion_bundle_sha256=completion_freeze["bundle_sha256"])
                failed.append(draw)
        finally:
            release_claim(claim)
    shard = {"schema_version": "atlas_completion_refit_shard_v1", "evidence_class": EVIDENCE_CLASS,
             "kind": args.kind, "layer": args.layer, "job": args.job, "draw_start": args.draw_start,
             "draw_end": args.draw_end, "completed": completed, "failed": failed,
             "config_sha256": config_sha,
             "resolved_config": config,
             "resolved_arguments": {"kind": args.kind, "layer": args.layer,
                                    "job": args.job, "point": False,
                                    "draw_start": args.draw_start,
                                    "draw_end": args.draw_end, "device": args.device},
             "seed_provenance": seed_provenance(
                 config,
                 contract="draw leaves bind deterministic_seed(base_seed, role, layer, draw_id)"),
             "device": args.device,
             "completion_bundle_sha256": completion_freeze["bundle_sha256"],
             "elapsed_sec": time.monotonic() - shard_started,
             "started_utc": shard_started_utc, "ended_utc": utc_now(),
             "environment": launch_environment, "input_attestation": firewall.attestation}
    with stage_publication_lock(stage_dir):
        if terminal_state(stage_dir) is not None:
            return
        atomic_write_json(stage_dir / f"shard_{args.draw_start:04d}_{args.draw_end:04d}.json", shard)
    maybe_finalize_draw_stage(stage_dir, requested_draws=int(config["draws"]),
                              minimum_complete_draws=int(config["minimum_complete_draws"]),
                              config_sha256=config_sha,
                              completion_bundle_sha256=completion_freeze["bundle_sha256"],
                              schema_version="atlas_completion_refit_terminal_v1",
                              expected_shards=([(0, 167), (167, 334), (334, 500)]
                                               if args.kind == "raw" else [(0, 500)]),
                              extra={"kind": args.kind, "layer": args.layer, "job": args.job})
    print(json.dumps({"stage": str(stage_dir), "completed": len(completed), "failed": len(failed)}, indent=2))


if __name__ == "__main__":
    try:
        main()
    except (LiveDrawClaimError, StageTerminalError) as exc:
        print(json.dumps({"worker_blocked_by_existing_work_or_terminal": str(exc)}))
    except Exception as exc:
        argv = __import__("sys").argv
        config = read_json(ROOT / "configs/atlas_completion/analysis.json")
        kind = argv[argv.index("--kind") + 1] if "--kind" in argv else "unknown"
        layer = int(argv[argv.index("--layer") + 1]) if "--layer" in argv else 3
        job = argv[argv.index("--job") + 1] if "--job" in argv else None
        stage = ROOT / config["run_root"] / ("raw_refit" if kind == "raw" else "k2_refit")
        stage = stage / (f"L{layer}" if kind == "raw" else str(job))
        write_failure_terminal(stage, stop_code="refit_worker_unrecoverable_failure",
                               failed_gate=f"{kind}_refit_worker", error=exc,
                               requested_draw_ids=range(int(config["draws"])),
                               input_attestation=_FAILURE_ATTESTATION)
        raise
