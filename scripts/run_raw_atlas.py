#!/usr/bin/env python3
"""Calibrate and score the frozen L3/L4 raw separable-information atlas."""

from __future__ import annotations

import argparse
import hashlib
import json
import pickle
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
from sklearn.decomposition import PCA
from sklearn.linear_model import RidgeClassifier
from sklearn.metrics import f1_score

from atlas_freeze import (activation_artifact_digest, artifact_hash, runtime_environment, utc_now,
                          verify_activation_complete, verify_freeze,
                          verify_calibration_sources, verify_layer_trigger)
from atlas_metrics import (chance_score, family_summary, mean_or_none,
                           normalized_recovery, orthonormal_basis,
                           principal_angles_degrees)


ROOT = Path(__file__).resolve().parents[1]
PRIMARY = {
    "absolute_position": ["abs_pos_16", "abs_pos_8"],
    "relative_structural_position": ["relative_quartile", "head_signed_distance", "dependency_depth", "boundary_state"],
    "lexical_semantic_content": ["token_identity_256", "lemma_identity_256", "ner_coarse"],
}
WORD_LABEL = {
    "relative_quartile": "relative_quartile", "head_signed_distance": "head_signed_distance",
    "dependency_depth": "dependency_depth", "boundary_state": "boundary_state",
    "token_identity_256": "token_identity_256", "lemma_identity_256": "lemma_identity_256", "ner_coarse": "ner_coarse",
}


@dataclass
class ActivationData:
    x: np.ndarray
    meta: dict[str, np.ndarray]
    records: list[dict[str, Any]]
    units: list[dict[str, Any]]


def load(role: str, layer: int, run_root: Path, freeze: dict[str, object] | None = None) -> ActivationData:
    root = run_root / "raw_activations" / role
    verify_activation_complete(root, role, freeze or verify_freeze())
    x = np.load(root / f"L{layer}.float16.npy", mmap_mode="r")
    loaded = np.load(root / "row_meta.npz")
    meta = {key: loaded[key] for key in loaded.files}
    records = [json.loads(line) for line in (root / "records.jsonl").read_text().splitlines()]
    units = json.loads((root / "units.json").read_text())
    return ActivationData(x, meta, records, units)


def frozen_rows(data: ActivationData, role: str, task: str) -> tuple[np.ndarray, np.ndarray]:
    manifest = json.loads((ROOT / "configs/atlas/task_row_manifest.json").read_text())
    spec = manifest["roles"][role][task]
    path = ROOT / spec["path"]
    if hashlib.sha256(path.read_bytes()).hexdigest() != spec["sha256"]:
        raise RuntimeError(f"task-row hash mismatch: {role}/{task}")
    unit_index = {unit["variant_id"]: index for index, unit in enumerate(data.units)}
    counts = np.bincount(data.meta["unit_index"], minlength=len(data.units))
    starts = np.concatenate([[0], np.cumsum(counts[:-1])])
    rows, values = [], []
    for line in path.read_text().splitlines():
        item = json.loads(line)
        variant, token = item["row_id"].rsplit(":", 1)
        index = unit_index.get(variant)
        if index is None:
            raise RuntimeError(f"frozen task row missing from activations: {item['row_id']}")
        rows.append(int(starts[index] + int(token)))
        values.append(item["label"])
    if len(rows) != int(spec["rows"]):
        raise RuntimeError(f"task-row count mismatch: {role}/{task}")
    return np.asarray(rows, dtype=np.int64), np.asarray(values, dtype=str)


def labels(data: ActivationData, task: str) -> np.ndarray:
    if task in {"abs_pos_16", "abs_pos_8"}:
        return data.meta[task].astype(str)
    result = np.full(len(data.x), "__DROP__", dtype=object)
    valid = np.flatnonzero(data.meta["word_index"] >= 0)
    key = WORD_LABEL[task]
    for row in valid:
        record = data.records[int(data.meta["record_index"][row])]
        word = int(data.meta["word_index"][row])
        if word < len(record["labels"][key]):
            result[row] = record["labels"][key][word]
    return result.astype(str)


def groups(data: ActivationData, rows: np.ndarray) -> np.ndarray:
    return np.asarray([data.records[int(data.meta["record_index"][i])]["document_group"] for i in rows])


def balanced_rows(data: ActivationData, task: str, eligible: list[str], cap: int, seed: int) -> tuple[np.ndarray, np.ndarray]:
    y = labels(data, task)
    per_class = max(1, cap // len(eligible))
    rng = np.random.default_rng(seed + int(hashlib.sha256(task.encode()).hexdigest()[:8], 16))
    selected, remainder = [], []
    for label in eligible:
        idx = np.flatnonzero(y == label)
        idx = idx[rng.permutation(len(idx))]
        selected.extend(idx[:per_class].tolist())
        remainder.extend(idx[per_class:].tolist())
    if len(selected) < cap and remainder:
        remainder = np.asarray(remainder)
        selected.extend(remainder[rng.permutation(len(remainder))[:cap - len(selected)]].tolist())
    rows = np.asarray(sorted(selected), dtype=np.int64)
    return rows, y[rows]


def fit(x: np.ndarray, y: np.ndarray, alpha: float) -> RidgeClassifier:
    return RidgeClassifier(alpha=float(alpha), solver="lsqr", fit_intercept=True).fit(x, y)


def score(model: RidgeClassifier, x: np.ndarray, y: np.ndarray) -> tuple[float, np.ndarray]:
    pred = model.predict(x)
    return float(f1_score(y, pred, average="macro", zero_division=0)), pred


def choose_alpha(x_fit: np.ndarray, y_fit: np.ndarray, x_cal: np.ndarray, y_cal: np.ndarray, alphas: list[float]) -> tuple[RidgeClassifier, float, dict[str, float]]:
    rows = []
    for alpha in alphas:
        model = fit(x_fit, y_fit, alpha)
        value, _ = score(model, x_cal, y_cal)
        rows.append((value, alpha, model))
    best_value = max(row[0] for row in rows)
    eligible = [row for row in rows if best_value - row[0] <= 0.005]
    chosen = max(eligible, key=lambda row: row[1])
    return chosen[2], float(chosen[1]), {str(alpha): value for value, alpha, _ in rows}


def coords(x: np.ndarray, basis: np.ndarray) -> np.ndarray:
    return x @ basis


def complement(x: np.ndarray, basis: np.ndarray, shrink: float = 1.0) -> np.ndarray:
    return x - shrink * (x @ basis @ basis.T)


def eval_task(model: RidgeClassifier, x_eval: np.ndarray, y_fit: np.ndarray, y_eval: np.ndarray) -> dict[str, Any]:
    value, pred = score(model, x_eval, y_eval)
    return {"macro_f1": value, "chance": chance_score(y_fit, y_eval), "pred": pred}


def fixed_group_ci(y: np.ndarray, pred: np.ndarray, group: np.ndarray, chance: float, raw: float, draws: int, seed: int) -> tuple[float, float]:
    unique = np.unique(group)
    group_rows = {g: np.flatnonzero(group == g) for g in unique}
    rng = np.random.default_rng(seed)
    values = []
    for _ in range(draws):
        sampled = rng.choice(unique, len(unique), replace=True)
        idx = np.concatenate([group_rows[g] for g in sampled])
        values.append(float(f1_score(y[idx], pred[idx], average="macro", zero_division=0) - chance))
    return float(np.quantile(values, 0.025)), float(np.quantile(values, 0.975))


def run_layer(layer: int, run_root: Path, config: dict[str, Any], eligibility: dict[str, Any],
              output: Path, phase: str) -> dict[str, Any]:
    discovery = load("discovery", layer, run_root)
    calibration = load("calibration", layer, run_root)
    cap = config["task_row_caps"]
    tasks = [task for values in PRIMARY.values() for task in values]
    selected: dict[str, dict[str, tuple[np.ndarray, np.ndarray]]] = {"discovery": {}, "calibration": {}}
    for task in tasks:
        eligible = eligibility[task]["eligible_labels"]
        selected["discovery"][task] = frozen_rows(discovery, "discovery", task)
        selected["calibration"][task] = frozen_rows(calibration, "calibration", task)

    rng = np.random.default_rng(config["seed"] + layer)
    scaler_rows = rng.choice(len(discovery.x), min(50000, len(discovery.x)), replace=False)
    scaler_sample = np.asarray(discovery.x[scaler_rows], dtype=np.float32)
    mean = scaler_sample.mean(axis=0, dtype=np.float64).astype(np.float32)
    scale = scaler_sample.std(axis=0, dtype=np.float64).astype(np.float32)
    scale[scale < 1e-6] = 1.0
    del scaler_sample

    def standardized(data: ActivationData, rows: np.ndarray) -> np.ndarray:
        return (np.asarray(data.x[rows], dtype=np.float32) - mean) / scale

    raw_models, raw_alpha, alpha_tables = {}, {}, {}
    for task in tasks:
        dr, dy = selected["discovery"][task]; cr, cy = selected["calibration"][task]
        model, alpha, table = choose_alpha(standardized(discovery, dr), dy, standardized(calibration, cr), cy, config["ridge_alphas"])
        raw_models[task], raw_alpha[task], alpha_tables[task] = model, alpha, table

    bases = {}
    for family, family_tasks in PRIMARY.items():
        weight_rows = np.concatenate([raw_models[task].coef_ for task in family_tasks], axis=0)
        bases[family] = orthonormal_basis(weight_rows, int(config["family_rank"])).astype(np.float32)
    broad_rows = np.concatenate([raw_models[t].coef_ for t in PRIMARY["absolute_position"] + PRIMARY["relative_structural_position"]], axis=0)
    bases["broad_position"] = orthonormal_basis(broad_rows, int(config["broad_position_rank"])).astype(np.float32)
    split_basis = orthonormal_basis(np.concatenate([bases["absolute_position"].T, bases["relative_structural_position"].T]), 16).astype(np.float32)
    bases["split_position_joint"] = split_basis
    pca = PCA(n_components=16, svd_solver="randomized", random_state=config["seed"]).fit(standardized(discovery, scaler_rows))
    bases["pca16"] = pca.components_.T.astype(np.float32)

    representations = list(bases) + ["broad_complement", "split_complement", "pca_complement"]
    component_models, component_alpha, calibration_scores = {}, {}, {}
    for representation in representations:
        component_models[representation], component_alpha[representation], calibration_scores[representation] = {}, {}, {}
        for task in tasks:
            dr, dy = selected["discovery"][task]; cr, cy = selected["calibration"][task]
            dx, cx = standardized(discovery, dr), standardized(calibration, cr)
            if representation.endswith("complement"):
                basis_name = "broad_position" if representation.startswith("broad") else "split_position_joint" if representation.startswith("split") else "pca16"
                dx, cx = complement(dx, bases[basis_name]), complement(cx, bases[basis_name])
            else:
                dx, cx = coords(dx, bases[representation]), coords(cx, bases[representation])
            model, alpha, table = choose_alpha(dx, dy, cx, cy, config["ridge_alphas"])
            component_models[representation][task] = model
            component_alpha[representation][task] = alpha
            value, _ = score(model, cx, cy)
            calibration_scores[representation][task] = {"macro_f1": value, "alpha_grid": table}

    def task_recovery(role_data: ActivationData, role_name: str, task: str, representation: str) -> tuple[float | None, dict[str, Any]]:
        rows, y = selected[role_name][task]
        raw_x = standardized(role_data, rows)
        raw_result = eval_task(raw_models[task], raw_x, selected["discovery"][task][1], y)
        if representation.endswith("complement"):
            basis_name = "broad_position" if representation.startswith("broad") else "split_position_joint" if representation.startswith("split") else "pca16"
            rep_x = complement(raw_x, bases[basis_name])
        else:
            rep_x = coords(raw_x, bases[representation])
        rep_result = eval_task(component_models[representation][task], rep_x, selected["discovery"][task][1], y)
        # Calibration selection uses a point eligibility approximation only; C1 recomputes a grouped bound.
        recovery = normalized_recovery(rep_result["macro_f1"], raw_result["macro_f1"], raw_result["chance"],
                                       raw_gap_lcb=raw_result["macro_f1"] - raw_result["chance"] - 0.02)
        return recovery, {"raw": raw_result["macro_f1"], "chance": raw_result["chance"], "component": rep_result["macro_f1"]}

    candidate_mapping = {
        "projection_broad16": {"absolute_position": "broad_position", "relative_structural_position": "broad_position", "lexical_semantic_content": "broad_complement"},
        "projection_split8_8": {"absolute_position": "absolute_position", "relative_structural_position": "relative_structural_position", "lexical_semantic_content": "split_complement"},
        "pca16_complement": {"absolute_position": "pca16", "relative_structural_position": "pca16", "lexical_semantic_content": "pca_complement"},
    }
    baseline_rows = {}
    for candidate, mapping in candidate_mapping.items():
        family_rows = {}
        for family, family_tasks in PRIMARY.items():
            assigned = [task_recovery(calibration, "calibration", task, mapping[family])[0] for task in family_tasks]
            nonassigned = []
            for other_family, other_rep in mapping.items():
                if other_family != family:
                    nonassigned.append([task_recovery(calibration, "calibration", task, other_rep)[0] for task in family_tasks])
            family_rows[family] = family_summary(assigned, nonassigned)
        margins = [row["selectivity_margin"] for row in family_rows.values() if row["selectivity_margin"] is not None]
        recoveries = [row["assigned_recovery"] for row in family_rows.values() if row["assigned_recovery"] is not None]
        retention_pass = len(recoveries) == 3 and min(recoveries) >= 0.65
        baseline_rows[candidate] = {"families": family_rows, "macro_selectivity": float(np.mean(margins)) if len(margins) == 3 else None,
                                    "retention_pass": retention_pass, "collateral_status": "missing_tier2_probe_audit",
                                    "selection_pass": False}
    # Collateral is mandatory. This implementation cannot silently select on Tier-1
    # alone: it freezes the preregistered default and records selection failure.
    valid = [(name, row) for name, row in baseline_rows.items() if row["selection_pass"] and row["macro_selectivity"] is not None]
    if valid:
        best_value = max(row["macro_selectivity"] for _, row in valid)
        tied = sorted((name, row) for name, row in valid if best_value - row["macro_selectivity"] <= 0.01)
        selected_baseline = tied[0][0]
        baseline_selection_failed = False
    else:
        selected_baseline, baseline_selection_failed = "projection_broad16", True

    bundle = {"mean": mean, "scale": scale, "bases": bases, "raw_models": raw_models,
              "component_models": component_models, "selected_rows": selected,
              "component_alpha": component_alpha, "candidate_mapping": candidate_mapping,
              "calibration_scores": calibration_scores, "selected_baseline": selected_baseline}
    bundle_path = output / f"L{layer}_calibration_bundle.pkl"
    freeze_path = output / f"L{layer}_calibration_freeze.json"
    calibration_eligibility: dict[str, dict[str, Any]] = {}
    for family, family_tasks in PRIMARY.items():
        task_rows: dict[str, Any] = {}
        for task in family_tasks:
            rows, y = selected["calibration"][task]
            evaluation = eval_task(raw_models[task], standardized(calibration, rows),
                                   selected["discovery"][task][1], y)
            ci = fixed_group_ci(y, evaluation["pred"], groups(calibration, rows),
                                evaluation["chance"], evaluation["macro_f1"],
                                config["bootstrap_draws"], config["seed"] + layer)
            approximate_se = (ci[1] - ci[0]) / (2.0 * 1.96)
            threshold = max(0.02, 2.0 * approximate_se)
            task_rows[task] = {
                "raw_minus_chance": evaluation["macro_f1"] - evaluation["chance"],
                "group_bootstrap_ci": ci,
                "approximate_se": approximate_se,
                "required_lcb": threshold,
                "denominator_eligible": ci[0] > threshold,
            }
        calibration_eligibility[family] = {
            "tasks": task_rows,
            "eligible_task_count": sum(row["denominator_eligible"] for row in task_rows.values()),
        }

    if phase == "calibrate":
        with bundle_path.open("xb") as f:
            pickle.dump(bundle, f, protocol=5)
        calibration_freeze = {"schema_version": "atlas_v1_calibration_freeze", "layer": layer, "raw_alpha": raw_alpha,
                              "raw_alpha_tables": alpha_tables, "component_alpha": component_alpha,
                              "component_calibration_scores": calibration_scores,
                              "baseline_candidates": baseline_rows, "selected_baseline": selected_baseline,
                              "baseline_selection_failed": baseline_selection_failed,
                              "calibration_denominator_eligibility": calibration_eligibility,
                              "confirmation_state_at_freeze": "not_opened_create_once",
                              "bundle_sha256": hashlib.sha256(bundle_path.read_bytes()).hexdigest()}
        with freeze_path.open("x") as f:
            f.write(json.dumps(calibration_freeze, indent=2, sort_keys=True) + "\n")
        return {"schema_version": "atlas_v1_calibration_result", "layer": layer,
                "selected_simple_baseline": selected_baseline,
                "baseline_selection_failed": baseline_selection_failed,
                "calibration_denominator_eligibility": calibration_eligibility,
                "bundle_sha256": calibration_freeze["bundle_sha256"]}

    # Confirmation is a separate invocation. It may load C1 only after both layers'
    # calibration bundles and the L4 trigger have been frozen.
    trigger_path = output / "layer_trigger_freeze.json"
    if not freeze_path.exists() or not bundle_path.exists() or not trigger_path.exists():
        raise RuntimeError("confirmation requested before calibration/layer-trigger freeze")
    calibration_freeze = json.loads(freeze_path.read_text())
    if hashlib.sha256(bundle_path.read_bytes()).hexdigest() != calibration_freeze["bundle_sha256"]:
        raise RuntimeError(f"L{layer} calibration bundle hash mismatch")
    trigger_record = json.loads(trigger_path.read_text())
    if trigger_record.get("calibration_bundle_sha256", {}).get(str(layer)) != calibration_freeze["bundle_sha256"]:
        raise RuntimeError(f"L{layer} calibration bundle does not match frozen layer trigger")
    with bundle_path.open("rb") as f:
        frozen = pickle.load(f)
    mean, scale, bases = frozen["mean"], frozen["scale"], frozen["bases"]
    raw_models, component_models = frozen["raw_models"], frozen["component_models"]
    selected, candidate_mapping = frozen["selected_rows"], frozen["candidate_mapping"]
    selected_baseline = frozen["selected_baseline"]

    confirmation = load("C1", layer, run_root)
    selected["C1"] = {}
    for task in tasks:
        selected["C1"][task] = frozen_rows(confirmation, "C1", task)

    task_scores = {}
    recoveries: dict[str, dict[str, float | None]] = {rep: {} for rep in representations}
    raw_gap_bounds = {}
    for task in tasks:
        rows, y = selected["C1"][task]
        sx = standardized(confirmation, rows)
        raw_eval = eval_task(raw_models[task], sx, selected["discovery"][task][1], y)
        group = groups(confirmation, rows)
        bound = fixed_group_ci(y, raw_eval["pred"], group, raw_eval["chance"], raw_eval["macro_f1"], config["bootstrap_draws"], config["seed"])
        raw_gap_bounds[task] = bound
        task_scores[task] = {"raw_macro_f1": raw_eval["macro_f1"], "chance_macro_f1": raw_eval["chance"],
                             "raw_minus_chance_fixed_probe_group_ci": bound, "n_rows": len(rows), "n_groups": len(np.unique(group)),
                             "recovery_detail": {}}
        for representation in representations:
            if representation.endswith("complement"):
                basis_name = "broad_position" if representation.startswith("broad") else "split_position_joint" if representation.startswith("split") else "pca16"
                rx = complement(sx, bases[basis_name])
            else:
                rx = coords(sx, bases[representation])
            rep_eval = eval_task(component_models[representation][task], rx, selected["discovery"][task][1], y)
            recovery = normalized_recovery(rep_eval["macro_f1"], raw_eval["macro_f1"], raw_eval["chance"],
                                           raw_gap_lcb=bound[0])
            recoveries[representation][task] = recovery
            task_scores[task][representation] = rep_eval["macro_f1"]
            task_scores[task]["recovery_detail"][representation] = {
                "value": recovery,
                "numerator_component_minus_chance": rep_eval["macro_f1"] - raw_eval["chance"],
                "denominator_raw_minus_chance": raw_eval["macro_f1"] - raw_eval["chance"],
                "undefined_reason": None if recovery is not None else "raw_gap_fixed_group_lcb_not_positive",
                "refit_interval": None,
            }

    split_families, broad_families = {}, {}
    split_mapping = candidate_mapping["projection_split8_8"]
    broad_mapping = candidate_mapping["projection_broad16"]
    all_primary_components = ["absolute_position", "relative_structural_position", "lexical_semantic_content"]
    for family, family_tasks in PRIMARY.items():
        split_assigned = [recoveries[split_mapping[family]][task] for task in family_tasks]
        split_other = [[recoveries[split_mapping[o]][task] for task in family_tasks] for o in PRIMARY if o != family]
        split_families[family] = family_summary(split_assigned, split_other)
        broad_assigned = [recoveries[broad_mapping[family]][task] for task in family_tasks]
        broad_other = [[recoveries[broad_mapping[o]][task] for task in family_tasks] for o in PRIMARY if o != family]
        broad_families[family] = family_summary(broad_assigned, broad_other)

    split_macro = mean_or_none([split_families[f]["selectivity_margin"] for f in ["absolute_position", "relative_structural_position"]])
    broad_macro = mean_or_none([broad_families[f]["selectivity_margin"] for f in ["absolute_position", "relative_structural_position"]])
    result = {"schema_version": "atlas_v1_raw_result", "layer": layer, "task_scores": task_scores,
              "normalized_recovery": recoveries, "split_families": split_families, "broad_families": broad_families,
              "split_macro_positional_selectivity": split_macro, "broad_macro_positional_selectivity": broad_macro,
              "geometry": {"abs_struct_angles_deg": principal_angles_degrees(bases["absolute_position"], bases["relative_structural_position"]).tolist()},
              "primary_pvalues": None, "primary_pvalues_unavailable_reason": "hierarchical refit/group randomization inference is not implemented; no proxy p-values are reported",
              "inference_protocol": "fixed_probe_group_resampling_diagnostic_not_preregistered_refit",
              "g1_outcome": "equivocal", "g1_reason": "mandatory 500-draw refit bootstrap was not executed; point/fixed-probe results cannot promote architecture",
              "selected_simple_baseline": selected_baseline, "calibration_freeze": f"L{layer}_calibration_freeze.json"}
    (output / f"L{layer}_raw_atlas.json").write_text(json.dumps(result, indent=2, sort_keys=True, allow_nan=False) + "\n")
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-root", type=Path, default=ROOT / "pilot_runs/20260731_atlas_v1_architecture_selection")
    parser.add_argument("--output", type=Path, default=ROOT / "results/atlas/raw_v1")
    parser.add_argument("--phase", choices=["calibrate", "confirm"], required=True)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    prescore = verify_freeze()
    config = json.loads((ROOT / "configs/atlas/analysis_run.json").read_text())
    eligibility = json.loads((ROOT / "reports/atlas_label_counts.json").read_text())["primary_class_eligibility"]
    if args.phase == "calibrate":
        protected = list(args.output.glob("*"))
        for role in ["C1", "C2"]:
            role_dir = args.run_root / "raw_activations" / role
            if role_dir.exists() and any(role_dir.iterdir()):
                protected.append(role_dir)
        if protected:
            raise RuntimeError("calibration is create-once and cannot run after calibration/confirmation artifacts exist: "
                               + ", ".join(str(path) for path in protected[:8]))
    if args.phase == "confirm":
        trigger_path = args.output / "layer_trigger_freeze.json"
        verify_layer_trigger(trigger_path, prescore)
        verify_calibration_sources(trigger_path, args.run_root, prescore)
        existing_results = [path for path in [args.output / "L3_raw_atlas.json", args.output / "L4_raw_atlas.json",
                                               args.output / "COMPLETE.json"] if path.exists()]
        if existing_results:
            raise RuntimeError("confirmation is create-once and existing results are not overwritten: "
                               + ", ".join(str(path) for path in existing_results))
    consumed_roles = ["discovery", "calibration"] + (["C1"] if args.phase == "confirm" else [])
    source_activation_digests = {
        role: activation_artifact_digest(verify_activation_complete(args.run_root / "raw_activations" / role, role, prescore))
        for role in consumed_roles
    }
    started = time.time()
    started_utc = utc_now()
    results = {}
    for layer in config["layers"]:
        results[str(layer)] = run_layer(int(layer), args.run_root, config, eligibility, args.output, args.phase)
    if args.phase == "calibrate":
        counts = {
            layer: {family: row["eligible_task_count"] for family, row in result["calibration_denominator_eligibility"].items()}
            for layer, result in results.items()
        }
        # L3 is preregistered primary. The full refit/source-stratified trigger
        # estimator is not implemented, so calibration diagnostics cannot select L4.
        trigger = False
        freeze = {"schema_version": "atlas_v1_layer_trigger", "l4_fallback_activated": trigger,
                  "prescore_bundle_sha256": prescore["bundle_sha256"],
                  "reason": "L3 fixed primary; L4 fallback disabled because the required refit/source-stratified trigger estimator is unavailable",
                  "calibration_eligible_task_counts": counts,
                  "calibration_bundle_sha256": {layer: result["bundle_sha256"] for layer, result in results.items()},
                  "primary_layer": 4 if trigger else 3, "descriptive_layer": 3 if trigger else 4}
        with (args.output / "layer_trigger_freeze.json").open("x") as f:
            f.write(json.dumps(freeze, indent=2, sort_keys=True) + "\n")
        complete = {"schema_version": "atlas_v1_raw_calibration_complete", "phase": "calibrate",
                    "layers": [3, 4], "l4_fallback": trigger,
                    "layer_trigger_sha256": artifact_hash(args.output / "layer_trigger_freeze.json"),
                    "prescore_bundle_sha256": prescore["bundle_sha256"], "resolved_config": config,
                    "source_activation_artifact_sha256": source_activation_digests,
                    "started_utc": started_utc, "ended_utc": utc_now(), "elapsed_sec": time.time() - started,
                    "environment": runtime_environment(),
                    "artifacts": {path.name: artifact_hash(path) for path in sorted(args.output.iterdir()) if path.is_file()}}
        with (args.output / "CALIBRATION_COMPLETE.json").open("x") as f:
            f.write(json.dumps(complete, indent=2, sort_keys=True) + "\n")
    else:
        trigger_record = json.loads((args.output / "layer_trigger_freeze.json").read_text())
        if trigger_record.get("prescore_bundle_sha256") != prescore["bundle_sha256"]:
            raise RuntimeError("layer trigger belongs to a different prescore bundle")
        trigger = trigger_record["l4_fallback_activated"]
        primary = "4" if trigger else "3"
        complete = {"schema_version": "atlas_v1_raw_complete", "phase": "confirm",
                    "layers": [3, 4], "primary_g1": results[primary]["g1_outcome"], "l4_fallback": trigger,
                    "prescore_bundle_sha256": prescore["bundle_sha256"], "resolved_config": config,
                    "source_activation_artifact_sha256": source_activation_digests,
                    "layer_trigger_sha256": artifact_hash(args.output / "layer_trigger_freeze.json"),
                    "started_utc": started_utc, "ended_utc": utc_now(), "elapsed_sec": time.time() - started,
                    "environment": runtime_environment(),
                    "artifacts": {path.name: artifact_hash(path) for path in sorted(args.output.glob("L*_raw_atlas.json"))}}
        (args.output / "COMPLETE.json").write_text(json.dumps(complete, indent=2, sort_keys=True) + "\n")
    print(json.dumps(complete, indent=2))


if __name__ == "__main__":
    main()
