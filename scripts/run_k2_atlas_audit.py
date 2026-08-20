#!/usr/bin/env python3
"""Audit all existing K=2 checkpoints against the frozen simple atlas baseline."""

from __future__ import annotations

import argparse
import json
import pickle
import time
from pathlib import Path
from typing import Any

import numpy as np

from atlas_freeze import (activation_artifact_digest, artifact_hash, runtime_environment,
                          utc_now, verify_activation_complete, verify_freeze,
                          verify_calibration_sources, verify_layer_trigger, verify_transform_complete)
from atlas_metrics import family_summary, mean_or_none, normalized_recovery
from run_raw_atlas import PRIMARY, ActivationData, chance_score, choose_alpha, complement, coords, eval_task, frozen_rows, load


ROOT = Path(__file__).resolve().parents[1]


def rep_array(run_root: Path, job: str, role: str, representation: str) -> np.ndarray:
    return np.load(run_root / "k2_transforms" / job / role / f"{representation}.float16.npy", mmap_mode="r")


def standardizer(array: np.ndarray, seed: int) -> tuple[np.ndarray, np.ndarray]:
    rng = np.random.default_rng(seed)
    rows = rng.choice(len(array), min(50000, len(array)), replace=False)
    sample = np.asarray(array[rows], dtype=np.float32)
    mean = sample.mean(axis=0, dtype=np.float64).astype(np.float32)
    scale = sample.std(axis=0, dtype=np.float64).astype(np.float32)
    scale[scale < 1e-6] = 1.0
    return mean, scale


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-root", type=Path, default=ROOT / "pilot_runs/20260731_atlas_v1_architecture_selection")
    parser.add_argument("--raw-results", type=Path, default=ROOT / "results/atlas/raw_v1")
    parser.add_argument("--output", type=Path, default=ROOT / "results/atlas/k2_v1")
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    existing = list(args.output.glob("*_audit.json")) + [path for path in [args.output / "k2_audit.json", args.output / "COMPLETE.json"] if path.exists()]
    if existing:
        raise RuntimeError("K=2 audit is create-once and existing results are not overwritten: " + ", ".join(map(str, existing[:8])))
    freeze = verify_freeze()
    trigger_path = args.raw_results / "layer_trigger_freeze.json"
    verify_layer_trigger(trigger_path, freeze)
    verify_calibration_sources(trigger_path, args.run_root, freeze)
    config = json.loads((ROOT / "configs/atlas/analysis_run.json").read_text())
    eligibility = json.loads((ROOT / "reports/atlas_label_counts.json").read_text())["primary_class_eligibility"]
    with (args.raw_results / "L3_calibration_bundle.pkl").open("rb") as f:
        raw_bundle = pickle.load(f)
    discovery = load("discovery", 3, args.run_root)
    calibration = load("calibration", 3, args.run_root)
    c2 = load("C2", 3, args.run_root)
    source_activation_digests = {
        role: activation_artifact_digest(verify_activation_complete(args.run_root / "raw_activations" / role, role, freeze))
        for role in ["discovery", "calibration", "C2"]
    }
    tasks = [task for values in PRIMARY.values() for task in values]
    selected = raw_bundle["selected_rows"]
    selected["C2"] = {task: frozen_rows(c2, "C2", task) for task in tasks}
    jobs = [row["job_id"] for row in json.loads((ROOT / "reports/provenance/final_checkpoint_metadata.json").read_text())]
    results = {}
    upstream_transforms = {}
    started = time.time()
    started_utc = utc_now()
    for job_index, job in enumerate(jobs):
        transform_dir = args.run_root / "k2_transforms" / job
        transform_info = verify_transform_complete(transform_dir, job, freeze)
        upstream_transforms[job] = {"complete_sha256": artifact_hash(transform_dir / "COMPLETE.json"),
                                    "checkpoint_sha256": transform_info["checkpoint_sha256"]}
        arrays = {role: {rep: rep_array(args.run_root, job, role, rep) for rep in ["pos", "content", "resid"]}
                  for role in ["discovery", "calibration", "C2"]}
        scaling = {rep: standardizer(arrays["discovery"][rep], config["seed"] + 100 * job_index + i)
                   for i, rep in enumerate(["pos", "content", "resid"])}

        def matrix(role: str, rep: str, rows: np.ndarray) -> np.ndarray:
            if rep == "joint":
                return np.concatenate([matrix(role, "pos", rows), matrix(role, "content", rows)], axis=1)
            if rep == "scrubbed_content":
                raw_mean, raw_scale = raw_bundle["mean"], raw_bundle["scale"]
                standardized_content = (np.asarray(arrays[role]["content"][rows], dtype=np.float32) - raw_mean) / raw_scale
                return complement(standardized_content, raw_bundle["bases"]["broad_position"])
            mean, scale = scaling[rep]
            return (np.asarray(arrays[role][rep][rows], dtype=np.float32) - mean) / scale

        models, alpha_tables = {}, {}
        for rep in ["pos", "content", "resid", "joint", "scrubbed_content"]:
            models[rep], alpha_tables[rep] = {}, {}
            for task in tasks:
                dr, dy = selected["discovery"][task]; cr, cy = selected["calibration"][task]
                model, alpha, table = choose_alpha(matrix("discovery", rep, dr), dy, matrix("calibration", rep, cr), cy,
                                                   config["ridge_alphas"])
                models[rep][task] = model
                alpha_tables[rep][task] = {"selected": alpha, "grid": table}

        task_scores, recoveries = {}, {rep: {} for rep in ["pos", "content", "resid", "joint", "scrubbed_content", "simple_assigned"]}
        baseline = raw_bundle["selected_baseline"]
        baseline_mapping = raw_bundle["candidate_mapping"][baseline]
        for family, family_tasks in PRIMARY.items():
            for task in family_tasks:
                rows, y = selected["C2"][task]
                raw_x = (np.asarray(c2.x[rows], dtype=np.float32) - raw_bundle["mean"]) / raw_bundle["scale"]
                raw_result = eval_task(raw_bundle["raw_models"][task], raw_x, selected["discovery"][task][1], y)
                task_scores[task] = {"raw": raw_result["macro_f1"], "chance": raw_result["chance"], "n_rows": len(rows),
                                     "recovery_detail": {}}
                raw_lcb_proxy = raw_result["macro_f1"] - raw_result["chance"] - 0.02
                for rep in ["pos", "content", "resid", "joint", "scrubbed_content"]:
                    rep_result = eval_task(models[rep][task], matrix("C2", rep, rows), selected["discovery"][task][1], y)
                    task_scores[task][rep] = rep_result["macro_f1"]
                    recovery = normalized_recovery(rep_result["macro_f1"], raw_result["macro_f1"], raw_result["chance"], raw_gap_lcb=raw_lcb_proxy)
                    recoveries[rep][task] = recovery
                    task_scores[task]["recovery_detail"][rep] = {
                        "value": recovery,
                        "numerator_component_minus_chance": rep_result["macro_f1"] - raw_result["chance"],
                        "denominator_raw_minus_chance": raw_result["macro_f1"] - raw_result["chance"],
                        "undefined_reason": None if recovery is not None else "raw_gap_proxy_not_positive",
                        "refit_interval": None,
                    }
                simple_rep = baseline_mapping[family]
                if simple_rep.endswith("complement"):
                    basis_name = "broad_position" if simple_rep.startswith("broad") else "split_position_joint" if simple_rep.startswith("split") else "pca16"
                    simple_x = complement(raw_x, raw_bundle["bases"][basis_name])
                else:
                    simple_x = coords(raw_x, raw_bundle["bases"][simple_rep])
                simple_result = eval_task(raw_bundle["component_models"][simple_rep][task], simple_x, selected["discovery"][task][1], y)
                task_scores[task]["simple_assigned"] = simple_result["macro_f1"]
                simple_recovery = normalized_recovery(simple_result["macro_f1"], raw_result["macro_f1"], raw_result["chance"], raw_gap_lcb=raw_lcb_proxy)
                recoveries["simple_assigned"][task] = simple_recovery
                task_scores[task]["recovery_detail"]["simple_assigned"] = {
                    "value": simple_recovery,
                    "numerator_component_minus_chance": simple_result["macro_f1"] - raw_result["chance"],
                    "denominator_raw_minus_chance": raw_result["macro_f1"] - raw_result["chance"],
                    "undefined_reason": None if simple_recovery is not None else "raw_gap_proxy_not_positive",
                    "refit_interval": None,
                }

        k2_families, simple_families = {}, {}
        for family, family_tasks in PRIMARY.items():
            assigned_rep = "pos" if family != "lexical_semantic_content" else "content"
            other_rep = "content" if assigned_rep == "pos" else "pos"
            k2_families[family] = family_summary([recoveries[assigned_rep][task] for task in family_tasks],
                                                  [[recoveries[other_rep][task] for task in family_tasks]])
            # Simple leakage uses the other frozen branch mapping(s).
            other_simple = [raw_bundle["candidate_mapping"][baseline][other] for other in PRIMARY if other != family]
            nonassigned = []
            for rep in other_simple:
                vals = []
                for task in family_tasks:
                    rows, y = selected["C2"][task]
                    raw_x = (np.asarray(c2.x[rows], dtype=np.float32) - raw_bundle["mean"]) / raw_bundle["scale"]
                    if rep.endswith("complement"):
                        basis_name = "broad_position" if rep.startswith("broad") else "split_position_joint" if rep.startswith("split") else "pca16"
                        rx = complement(raw_x, raw_bundle["bases"][basis_name])
                    else:
                        rx = coords(raw_x, raw_bundle["bases"][rep])
                    r = eval_task(raw_bundle["component_models"][rep][task], rx, selected["discovery"][task][1], y)
                    vals.append(normalized_recovery(r["macro_f1"], task_scores[task]["raw"], task_scores[task]["chance"],
                                                    raw_gap_lcb=task_scores[task]["raw"] - task_scores[task]["chance"] - 0.02))
                nonassigned.append(vals)
            simple_families[family] = family_summary([recoveries["simple_assigned"][task] for task in family_tasks], nonassigned)
        k2_macro = mean_or_none([row["selectivity_margin"] for row in k2_families.values()])
        simple_macro = mean_or_none([row["selectivity_margin"] for row in simple_families.values()])
        functional_path = args.output / f"{job}_functional.json"
        functional = json.loads(functional_path.read_text()) if functional_path.exists() else None
        if functional is not None:
            marker_path = args.output / f"{job}_functional_COMPLETE.json"
            if not marker_path.exists():
                raise RuntimeError(f"functional result lacks terminal marker: {job}")
            marker = json.loads(marker_path.read_text())
            if (marker.get("prescore_bundle_sha256") != freeze["bundle_sha256"]
                    or marker.get("result_sha256") != artifact_hash(functional_path)
                    or marker.get("source_transform_complete_sha256") != artifact_hash(transform_dir / "COMPLETE.json")):
                raise RuntimeError(f"functional result terminal marker mismatch: {job}")
        outcome = "equivocal"
        reasons = ["mandatory refit-bootstrap simultaneous bounds not run"]
        if functional is None:
            reasons.append("counterfactual/suffix-CE collateral artifact missing")
        elif functional.get("counterfactual_gate_valid") is not True:
            reasons.append("counterfactual specificity invalid: matched-random/sham representation comparator missing")
        reasons.append("cross-checkpoint CKA stability and Tier-2 sentinel collateral are not implemented")
        results[job] = {"job_id": job, "seed": transform_info["seed"], "lambda_inc": transform_info["lambda_inc"],
                        "task_scores": task_scores, "normalized_recovery": recoveries,
                        "k2_families": k2_families, "simple_families": simple_families,
                        "k2_macro_selectivity": k2_macro, "simple_macro_selectivity": simple_macro,
                        "learned_minus_simple_point": None if k2_macro is None or simple_macro is None else k2_macro - simple_macro,
                        "fvu_total_C2": transform_info["roles"]["C2"]["fvu_total"],
                        "alpha_selection": alpha_tables, "functional": functional,
                        "g2_outcome": outcome, "g2_reasons": reasons,
                        "evidence_class": "development_existing_checkpoint"}
        (args.output / f"{job}_audit.json").write_text(json.dumps(results[job], indent=2, sort_keys=True, allow_nan=False) + "\n")
    aggregate = {"schema_version": "atlas_v1_k2_audit", "selected_simple_baseline": raw_bundle["selected_baseline"],
                 "prescore_bundle_sha256": freeze["bundle_sha256"],
                 "checkpoints": results, "g2_outcome": "equivocal",
                 "training_warranted": False,
                 "decision_note": "No new training is warranted from an equivocal G2; missing primary inference/functional evidence cannot be treated as learned superiority.",
                 "elapsed_sec": time.time() - started, "started_utc": started_utc, "ended_utc": utc_now(),
                 "resolved_config": config, "environment": runtime_environment(),
                 "layer_trigger_sha256": artifact_hash(trigger_path),
                 "source_activation_artifact_sha256": source_activation_digests,
                 "upstream_transforms": upstream_transforms}
    (args.output / "k2_audit.json").write_text(json.dumps(aggregate, indent=2, sort_keys=True, allow_nan=False) + "\n")
    artifacts = {path.name: artifact_hash(path) for path in sorted(args.output.glob("*_audit.json"))}
    (args.output / "COMPLETE.json").write_text(json.dumps({"schema_version": "atlas_v1_k2_audit_complete",
                                                            "complete": True, "jobs": jobs, "g2_outcome": "equivocal",
                                                            "prescore_bundle_sha256": freeze["bundle_sha256"],
                                                            "layer_trigger_sha256": artifact_hash(trigger_path),
                                                            "source_activation_artifact_sha256": source_activation_digests,
                                                            "upstream_transforms": upstream_transforms,
                                                            "ended_utc": utc_now(), "artifacts": artifacts}, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"jobs": jobs, "g2_outcome": "equivocal", "elapsed_sec": time.time() - started}, indent=2))


if __name__ == "__main__":
    main()
