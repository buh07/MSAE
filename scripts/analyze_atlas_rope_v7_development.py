#!/usr/bin/env python3
"""Opened-source cache diagnosis and bounded v2.4 probe sensitivity."""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path
from typing import Any, Mapping

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))

import run_atlas_rope_v6 as old
from atlas_rope_v7 import ROOT, gate_contract, row_metrics, sha256_file
from msae_measurement_v2_run import weighted_macro_f1


def _expanded(reference: np.ndarray) -> np.ndarray:
    return np.ascontiguousarray(np.repeat(reference.reshape(100, 2, 768)[:, None], 6, axis=1).reshape(1200, 768))


def opened_histories() -> dict[str, tuple[np.ndarray, np.ndarray, list[dict[str, Any]], dict[str, Any]]]:
    ewt = old._verify_ewt_history()
    gum = old._verify_gum_history()
    gentle = old._load_grid_history(old.GENTLE_GRID, "GENTLE", "GENTLE_validation")
    return {"EWT": ewt, "GUM": gum, "GENTLE": gentle}


def cache_diagnosis(histories: Mapping[str, tuple[np.ndarray, np.ndarray, list[dict[str, Any]], dict[str, Any]]]) -> tuple[dict[str, Any], list[dict[str, Any]], np.ndarray]:
    def summarize(records: list[dict[str, Any]]) -> dict[str, Any]:
        if not records:
            empty = {"mean": None, "q99": None, "max": None}
            return {"rows": 0, "relative_l2": empty, "norm_ratio_error": dict(empty), "cosine_distance": dict(empty),
                    "primary_failures": 0, "catastrophic_failures": 0}
        relative = np.asarray([row["relative_l2"] for row in records], np.float64)
        norm_error = np.asarray([row["norm_ratio_error"] for row in records], np.float64)
        cosine = np.asarray([row["cosine_distance"] for row in records], np.float64)
        return {
            "rows": len(records),
            "relative_l2": {"mean": float(relative.mean()), "q99": float(np.quantile(relative, .99)), "max": float(relative.max())},
            "norm_ratio_error": {"mean": float(norm_error.mean()), "q99": float(np.quantile(norm_error, .99)), "max": float(norm_error.max())},
            "cosine_distance": {"mean": float(cosine.mean()), "q99": float(np.quantile(cosine, .99)), "max": float(cosine.max())},
            "primary_failures": sum(int(row["primary_failure"]) for row in records),
            "catastrophic_failures": sum(int(row["catastrophic_failure"]) for row in records),
        }

    report: dict[str, Any] = {}
    direction_records: list[dict[str, Any]] = []
    direction_values: list[np.ndarray] = []
    for source, (reference, candidate, rows, lineage) in histories.items():
        expanded = _expanded(reference)
        metrics = row_metrics(expanded, candidate)
        records: list[dict[str, Any]] = []
        cursor = 0
        for base in range(100):
            for shift in (1, 4, 8, 16, 32, 64):
                for slot in range(2):
                    row = rows[2 * base + slot]
                    record = {
                        "source": source, "base_id": row["base_id"], "row_id": row["row_id"],
                        "length_bin": row["length_bin"], "selected_position": int(row["selected_position"]),
                        "shift": shift, "reference_norm": float(metrics["reference_norm"][cursor]),
                        "relative_l2": float(metrics["relative_l2"][cursor]),
                        "norm_ratio_error": float(metrics["norm_ratio_error"][cursor]),
                        "cosine_distance": float(metrics["cosine_distance"][cursor]),
                        "max_abs": float(metrics["max_abs"][cursor]),
                        "primary_failure": bool(metrics["primary_failure"][cursor]),
                        "catastrophic_failure": bool(metrics["catastrophic_failure"][cursor]),
                    }
                    records.append(record)
                    delta = np.asarray(candidate[cursor] - expanded[cursor], dtype=np.float64)
                    if np.isfinite(delta).all() and np.linalg.norm(delta) > 1e-12:
                        direction_records.append({**record, "delta_sha256": hashlib.sha256(delta.tobytes()).hexdigest()})
                        direction_values.append(delta)
                    cursor += 1
        rel = metrics["relative_l2"]
        norm = metrics["norm_ratio_error"]
        cosine = metrics["cosine_distance"]
        norm_edges = np.quantile(np.asarray([row["reference_norm"] for row in records], np.float64), np.linspace(0.0, 1.0, 6))
        norm_groups: dict[str, list[dict[str, Any]]] = {f"q{index + 1}": [] for index in range(5)}
        for row in records:
            index = min(int(np.searchsorted(norm_edges[1:-1], row["reference_norm"], side="right")), 4)
            norm_groups[f"q{index + 1}"].append(row)
        report[source] = {
            "rows": 1200,
            "lineage_complete_sha256": lineage.get("complete_sha256") or lineage.get("staging_complete_sha256"),
            "relative_l2": {"max": float(rel.max()), "q99": float(np.quantile(rel, .99)), "q995": float(np.quantile(rel, .995))},
            "norm_ratio_error": {"max": float(norm.max()), "q99": float(np.quantile(norm, .99)), "q995": float(np.quantile(norm, .995))},
            "cosine_distance": {"max": float(cosine.max()), "q99": float(np.quantile(cosine, .99)), "q995": float(np.quantile(cosine, .995))},
            "primary_failures": int(metrics["primary_failure"].sum()),
            "catastrophic_failures": int(metrics["catastrophic_failure"].sum()),
            "max_row": max(records, key=lambda row: row["relative_l2"]),
            "by_shift": {str(shift): summarize([row for row in records if row["shift"] == shift]) for shift in (1, 4, 8, 16, 32, 64)},
            "by_length_bin": {name: summarize([row for row in records if row["length_bin"] == name]) for name in ("4-8", "9-16", "17-32", "33-64", "65-128")},
            "by_selected_position": {str(position): summarize([row for row in records if row["selected_position"] == position])
                                     for position in sorted({int(row["selected_position"]) for row in records})},
            "by_reference_norm_quintile": {
                name: {"lower": float(norm_edges[index]), "upper": float(norm_edges[index + 1]), **summarize(group)}
                for index, (name, group) in enumerate(norm_groups.items())
            },
            "row_records": records,
        }
    values = np.stack(direction_values)
    return report, direction_records, values


def _direction_library(records: list[dict[str, Any]], values: np.ndarray) -> tuple[np.ndarray, list[dict[str, Any]]]:
    unique: dict[str, tuple[dict[str, Any], np.ndarray]] = {}
    for record, value in zip(records, values, strict=True):
        digest = hashlib.sha256(np.asarray(value, np.float64).tobytes()).hexdigest()
        unique.setdefault(digest, (record, value))
    ordered = list(unique.values())
    largest = sorted(ordered, key=lambda item: (-float(item[0]["relative_l2"]), item[0]["delta_sha256"]))[:32]
    chosen_sha = {item[0]["delta_sha256"] for item in largest}
    remaining = sorted((item for item in ordered if item[0]["delta_sha256"] not in chosen_sha), key=lambda item: item[0]["delta_sha256"])[:32]
    chosen = largest + remaining
    directions = np.stack([value / np.linalg.norm(value) for _, value in chosen])
    return directions, [record for record, _ in chosen]


def _task_rows(task: str) -> list[dict[str, Any]]:
    path = ROOT / f"data/atlas_measurement_v2_4/prepared/C2/tasks/{task}.jsonl"
    return [json.loads(line) for line in path.read_text().splitlines() if line]


def _predict(x: np.ndarray, weight: np.ndarray, bias: np.ndarray) -> np.ndarray:
    return np.argmax(np.asarray(x, np.float32) @ weight + bias, axis=1).astype(np.int32)


def _macro(labels: np.ndarray, prediction: np.ndarray, classes: int) -> float:
    return float(weighted_macro_f1(labels, prediction, np.ones(len(labels), np.float64), classes))


def sensitivity(directions: np.ndarray, direction_records: list[dict[str, Any]]) -> dict[str, Any]:
    root = ROOT / "pilot_runs/20260802_atlas_measurement_v2_4"
    raw = np.load(root / "raw_cache/C2/values.float32.npy", mmap_mode="r")
    probes = np.load(root / "analysis/probe_models.npz")
    results = json.loads((root / "analysis/results.json").read_text())
    basis = np.asarray(probes["simple_projection_basis"], np.float64)
    raw_mean = np.asarray(probes["raw__scaler_mean"], np.float64)
    raw_scale = np.asarray(probes["raw__scaler_scale"], np.float64)
    tasks = ("relative_quartile", "head_signed_distance", "deprel_coarse", "dependency_depth", "token_identity_v2")
    baseline: dict[str, Any] = {}
    task_cache: dict[str, Any] = {}
    for task in tasks:
        rows = _task_rows(task)
        indices = np.asarray([int(row["activation_index"]) for row in rows], np.int64)
        labels_text = list(results["evaluations"]["raw"][task]["labels"])
        mapping = {label: index for index, label in enumerate(labels_text)}
        y = np.asarray([mapping[str(row["label"])] for row in rows], np.int32)
        x_raw = np.asarray(raw[indices], np.float64)
        z = (x_raw - raw_mean) / raw_scale
        pos = (z @ basis) @ basis.T
        representations = {"raw": x_raw, "simple_pos": pos, "simple_content": z - pos}
        baseline[task] = {}
        for rep, values in representations.items():
            mean = np.asarray(probes[f"{rep}__scaler_mean"], np.float64)
            scale = np.asarray(probes[f"{rep}__scaler_scale"], np.float64)
            weight = np.asarray(probes[f"{rep}__{task}__weight"], np.float64)
            bias = np.asarray(probes[f"{rep}__{task}__bias"], np.float64)
            pred = _predict((values - mean) / scale, weight, bias)
            baseline[task][rep] = {"macro_f1": _macro(y, pred, len(labels_text)), "prediction": pred}
        task_cache[task] = {"indices": indices, "labels": y, "classes": len(labels_text), "x_raw": x_raw, "z": z}

    def comparisons(scores: Mapping[str, Mapping[str, float]]) -> dict[str, bool]:
        output = {}
        for task in tasks:
            chance = 1.0 / task_cache[task]["classes"]
            denominator = scores[task]["raw"] - chance
            assigned = "simple_content" if task == "token_identity_v2" else "simple_pos"
            leak = "simple_pos" if task == "token_identity_v2" else "simple_content"
            recovery = (scores[task][assigned] - chance) / denominator if denominator > 1e-6 else float("-inf")
            leakage = (scores[task][leak] - chance) / denominator if denominator > 1e-6 else float("inf")
            output[f"{task}:assigned_recovery_ge_0.65"] = recovery >= .65
            output[f"{task}:selectivity_gt_0"] = recovery - leakage > 0.0
        return output

    base_scores = {task: {rep: float(row["macro_f1"]) for rep, row in reps.items()} for task, reps in baseline.items()}
    base_comparisons = comparisons(base_scores)
    scales: dict[str, Any] = {}
    for epsilon in (2e-5, 5e-5):
        worst_change = 0.0
        worst_flip = 0.0
        macro_worst_case: dict[str, Any] | None = None
        flip_worst_case: dict[str, Any] | None = None
        comparison_change_counts = {key: 0 for key in base_comparisons}
        endpoint = {
            task: {rep: {"worst_absolute_macro_f1_change": 0.0, "worst_prediction_flip_fraction": 0.0}
                   for rep in ("raw", "simple_pos", "simple_content")}
            for task in tasks
        }
        for direction_index, direction in enumerate(directions):
            for sign in (-1.0, 1.0):
                scores: dict[str, dict[str, float]] = {}
                for task in tasks:
                    cache = task_cache[task]
                    x_raw = cache["x_raw"]
                    delta_raw = sign * epsilon * np.linalg.norm(x_raw, axis=1)[:, None] * direction[None, :]
                    perturbed_raw = x_raw + delta_raw
                    dz = delta_raw / raw_scale
                    dpos = (dz @ basis) @ basis.T
                    values = {"raw": perturbed_raw, "simple_pos": cache["z"] @ basis @ basis.T + dpos,
                              "simple_content": cache["z"] - cache["z"] @ basis @ basis.T + dz - dpos}
                    scores[task] = {}
                    for rep, x in values.items():
                        mean = np.asarray(probes[f"{rep}__scaler_mean"], np.float64)
                        scale = np.asarray(probes[f"{rep}__scaler_scale"], np.float64)
                        weight = np.asarray(probes[f"{rep}__{task}__weight"], np.float64)
                        bias = np.asarray(probes[f"{rep}__{task}__bias"], np.float64)
                        pred = _predict((x - mean) / scale, weight, bias)
                        score = _macro(cache["labels"], pred, cache["classes"])
                        scores[task][rep] = score
                        change = abs(score - base_scores[task][rep])
                        flip = float(np.mean(pred != baseline[task][rep]["prediction"]))
                        endpoint[task][rep]["worst_absolute_macro_f1_change"] = max(endpoint[task][rep]["worst_absolute_macro_f1_change"], change)
                        endpoint[task][rep]["worst_prediction_flip_fraction"] = max(endpoint[task][rep]["worst_prediction_flip_fraction"], flip)
                        if change > worst_change:
                            worst_change = change
                            macro_worst_case = {"direction_index": direction_index, "sign": sign, "task": task, "representation": rep,
                                                "macro_f1_change": change, "prediction_flip_fraction": flip}
                        if flip > worst_flip:
                            worst_flip = flip
                            flip_worst_case = {"direction_index": direction_index, "sign": sign, "task": task, "representation": rep,
                                               "macro_f1_change": change, "prediction_flip_fraction": flip}
                observed_comparisons = comparisons(scores)
                for key, baseline_value in base_comparisons.items():
                    comparison_change_counts[key] += int(observed_comparisons[key] != baseline_value)
        task_stability: dict[str, Any] = {}
        for task in tasks:
            task_changes = {key: value for key, value in comparison_change_counts.items() if key.startswith(task + ":")}
            stable = all(row["worst_absolute_macro_f1_change"] <= .001 for row in endpoint[task].values()) and not any(task_changes.values())
            task_stability[task] = {"representations": endpoint[task], "threshold_label_change_counts": task_changes, "decision_stable": stable}
        stable = all(row["decision_stable"] for row in task_stability.values())
        scales[str(epsilon)] = {
            "worst_absolute_macro_f1_change": worst_change,
            "worst_prediction_flip_fraction": worst_flip,
            "threshold_label_change_counts": comparison_change_counts,
            "threshold_comparison_changing_conditions": sum(comparison_change_counts.values()),
            "decision_stable": stable,
            "task_stability": task_stability,
            "macro_f1_worst_case": macro_worst_case,
            "prediction_flip_worst_case": flip_worst_case,
        }

    # Exact raw-linear margin certificate at the primary radius.
    certificates: dict[str, float] = {}
    epsilon = 2e-5
    for task in tasks:
        cache = task_cache[task]
        x = cache["x_raw"]
        mean = np.asarray(probes["raw__scaler_mean"], np.float64)
        scale = np.asarray(probes["raw__scaler_scale"], np.float64)
        weight = np.asarray(probes[f"raw__{task}__weight"], np.float64)
        bias = np.asarray(probes[f"raw__{task}__bias"], np.float64)
        logits = ((x - mean) / scale) @ weight + bias
        winner = np.argmax(logits, axis=1)
        certified = np.ones(len(x), dtype=bool)
        effective = weight / scale[:, None]
        radius = epsilon * np.linalg.norm(x, axis=1)
        for alternative in range(weight.shape[1]):
            mask = winner != alternative
            margin = logits[np.arange(len(x)), winner] - logits[:, alternative]
            norm = np.linalg.norm(effective[:, winner].T - effective[:, alternative], axis=1)
            certified &= (~mask) | (margin > radius * norm)
        certificates[task] = float(certified.mean())
    return {
        "schema_version": "atlas_rope_v7_attempt11_v2_4_sensitivity_v1",
        "direction_count": int(len(directions)), "signs": [-1, 1],
        "direction_records": direction_records,
        "scales": scales,
        "raw_linear_primary_radius_certified_fraction": certificates,
        "baseline_threshold_comparisons": base_comparisons,
        "preexisting_labels": {
            "projection_baseline_status": {"value": results["projection_baseline"]["status"],
                                            "sensitivity_status": "invariant_by_frozen_no_refit_definition"},
            "architecture_outcome": {"value": results["architecture_outcome"],
                                     "sensitivity_status": "not_certified_by_v2_4_sensitivity"},
        },
        "supported_endpoint_scope": "frozen raw/simple linear-probe predictions and their retention/selectivity threshold labels",
        "learned_and_nonlinear_v3_3_endpoints": "not_certified_by_v2_4_sensitivity",
        "probe_models_sha256": sha256_file(root / "analysis/probe_models.npz"),
    }


def run() -> dict[str, Any]:
    histories = opened_histories()
    cache, records, values = cache_diagnosis(histories)
    directions, direction_records = _direction_library(records, values)
    return {
        "schema_version": "atlas_rope_v7_attempt11_opened_development_v1",
        "status": "COMPLETE",
        "gate_contract": gate_contract(),
        "opened_cache_diagnosis": cache,
        "sensitivity": sensitivity(directions, direction_records),
        "validation_sources_used": [],
        "threshold_or_budget_changed": False,
        "neural_training_run": False,
    }


if __name__ == "__main__":
    print(json.dumps(run(), indent=2, sort_keys=True))
