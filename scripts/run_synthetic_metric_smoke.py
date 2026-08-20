#!/usr/bin/env python3
"""Run planted positive and negative regression regimes for atlas metrics."""

from __future__ import annotations

import argparse
import hashlib
import json
import time
from pathlib import Path
from typing import Any

import numpy as np

from atlas_metrics import (align_components, bh_adjust, chance_score, family_summary, fit_probe, grouped_bootstrap,
                           l4_fallback_trigger, macro_f1, monte_carlo_se, normalized_recovery,
                           orthonormal_basis, percentile_ci, principal_angles_degrees, project,
                           render_joint_decision, sign_flip_pvalue, simultaneous_bounds)


ROOT = Path(__file__).resolve().parents[1]


def data(seed: int, n: int, d: int = 24) -> tuple[np.ndarray, dict[str, np.ndarray], np.ndarray]:
    rng = np.random.default_rng(seed)
    latent = rng.normal(size=(n, 12))
    x = latent @ np.eye(12, d) + rng.normal(scale=0.15, size=(n, d))
    labels = {}
    for family, start in [("absolute", 0), ("structural", 4), ("content", 8)]:
        labels[f"{family}_a"] = (latent[:, start] + 0.2 * latent[:, start + 1] > 0).astype(int)
        labels[f"{family}_b"] = (latent[:, start + 2] - 0.2 * latent[:, start + 3] > 0).astype(int)
    groups = np.asarray([f"g{i // 4}" for i in range(n)])
    return x, labels, groups


def positive_regime() -> dict[str, Any]:
    x_fit, y_fit, _ = data(1, 800)
    x_eval, y_eval, _ = data(2, 400)
    family_tasks = {family: [f"{family}_a", f"{family}_b"] for family in ["absolute", "structural", "content"]}
    raw_probes = {task: fit_probe(x_fit, y, 1.0) for task, y in y_fit.items()}
    # One common discovery scaler: weights are already in each standardized coordinate; planted dimensions have equal scale.
    bases = {}
    for family, tasks in family_tasks.items():
        bases[family] = orthonormal_basis(np.concatenate([raw_probes[t].coef for t in tasks]), 2)
    results = {}
    for family, tasks in family_tasks.items():
        assigned, nonassigned = [], {other: [] for other in family_tasks if other != family}
        for task in tasks:
            raw = macro_f1(raw_probes[task], x_eval, y_eval[task])
            chance = chance_score(y_fit[task], y_eval[task])
            # Project in the task probe's standardized coordinates and refit only on discovery.
            standardized_fit = raw_probes[task].transform(x_fit)
            standardized_eval = raw_probes[task].transform(x_eval)
            for component in family_tasks:
                p_fit = project(standardized_fit, bases[component])
                p_eval = project(standardized_eval, bases[component])
                score = macro_f1(fit_probe(p_fit, y_fit[task], 1.0), p_eval, y_eval[task])
                recovery = normalized_recovery(score, raw, chance, raw_gap_lcb=raw - chance - 0.02)
                if component == family:
                    assigned.append(recovery)
                else:
                    nonassigned[component].append(recovery)
        results[family] = family_summary(assigned, list(nonassigned.values()))
    passed = all(row["assigned_recovery"] is not None and row["assigned_recovery"] >= 0.75 and
                 row["selectivity_margin"] is not None and row["selectivity_margin"] >= 0.20 for row in results.values())
    return {"passed": passed, "families": results,
            "angles": {"absolute_structural": principal_angles_degrees(bases["absolute"], bases["structural"]).tolist()}}


def negative_regimes() -> dict[str, Any]:
    rng = np.random.default_rng(7)
    # Explicit undefined denominator cases.
    absent = normalized_recovery(0.51, 0.51, 0.50, raw_gap_lcb=-0.01)
    near_zero = normalized_recovery(0.502, 0.503, 0.50, raw_gap_lcb=0.001)
    # Overlap: identical bases imply leakage equals assigned recovery.
    overlap = family_summary([0.90, 0.88], [[0.90, 0.88], [0.05, 0.02]])
    # Source-confound reversal: training nuisance predicts y, evaluation reverses it.
    y_train = rng.integers(0, 2, 400)
    y_eval = rng.integers(0, 2, 300)
    x_train = np.column_stack([2 * y_train - 1, rng.normal(size=(400, 7))])
    x_eval = np.column_stack([1 - 2 * y_eval, rng.normal(size=(300, 7))])
    reversal_score = macro_f1(fit_probe(x_train, y_train, 1.0), x_eval, y_eval)
    # Shuffled assignment must not meet a raw-gap eligibility floor.
    x = rng.normal(size=(500, 8)); y = rng.integers(0, 2, 500); rng.shuffle(y)
    shuffled = macro_f1(fit_probe(x[:300], y[:300], 1.0), x[300:], y[300:])
    chance = chance_score(y[:300], y[300:])
    shuffled_norm = normalized_recovery(shuffled, shuffled, chance, raw_gap_lcb=shuffled - chance - 0.03)
    passed = absent is None and near_zero is None and overlap["selectivity_margin"] < 0.20 and reversal_score < 0.20 and shuffled_norm is None
    return {"passed": passed, "absent_is_undefined": absent is None, "near_zero_is_undefined": near_zero is None,
            "overlap": overlap, "source_reversal_macro_f1": reversal_score, "shuffled_macro_f1": shuffled,
            "shuffled_chance": chance, "shuffled_is_undefined": shuffled_norm is None}


def statistics_regime(bootstrap_draws: int, randomization_draws: int) -> dict[str, Any]:
    rng = np.random.default_rng(31)
    groups = np.asarray([f"g{i}" for i in range(80) for _ in range(3)])
    effects = rng.normal(0.25, 0.10, len(groups))
    boot = grouped_bootstrap(groups, lambda idx: float(np.mean(effects[idx])), bootstrap_draws, 32)
    ci = percentile_ci(boot)
    group_effects = [float(np.mean(effects[groups == group])) for group in np.unique(groups)]
    pvalue = sign_flip_pvalue(group_effects, randomization_draws, 33)
    bh = bh_adjust([0.01, 0.04, 0.03, 0.20]).tolist()
    expected_bh = [0.04, 0.05333333333333334, 0.05333333333333334, 0.20]
    # Permutation/sign recovery.
    reference = np.eye(3, 5)
    candidate = np.stack([-reference[2], reference[0], -reference[1]])
    aligned, similarity = align_components(reference, candidate)
    passed = ci[0] > 0 and pvalue <= 0.05 and np.allclose(bh, expected_bh) and np.allclose(aligned, reference) and similarity == 1.0
    observed = np.array([0.10, -0.02])
    paired_boot = rng.normal(observed, [0.02, 0.03], size=(bootstrap_draws, 2))
    lower, upper = simultaneous_bounds(observed, paired_boot)
    return {"passed": bool(passed and np.all(lower <= observed) and np.all(upper >= observed)), "bootstrap_draws": bootstrap_draws, "bootstrap_ci": ci,
            "randomization_draws": randomization_draws, "pvalue": pvalue,
            "pvalue_mc_se_worstcase": monte_carlo_se(0.5, randomization_draws), "bh": bh,
            "permutation_similarity": similarity, "simultaneous_lower": lower.tolist(), "simultaneous_upper": upper.tolist()}


def refit_bootstrap_regime(draws: int) -> dict[str, Any]:
    from sklearn.linear_model import RidgeClassifier
    from sklearn.metrics import f1_score
    rng = np.random.default_rng(90)
    x_fit, y_fit, fit_groups = data(90, 320)
    x_eval, y_eval, eval_groups = data(91, 200)
    fit_unique, eval_unique = np.unique(fit_groups), np.unique(eval_groups)
    fit_rows = {g: np.flatnonzero(fit_groups == g) for g in fit_unique}
    eval_rows = {g: np.flatnonzero(eval_groups == g) for g in eval_unique}
    estimates = []
    for _ in range(draws):
        fi = np.concatenate([fit_rows[g] for g in rng.choice(fit_unique, len(fit_unique), replace=True)])
        ei = np.concatenate([eval_rows[g] for g in rng.choice(eval_unique, len(eval_unique), replace=True)])
        mean, scale = x_fit[fi].mean(0), x_fit[fi].std(0)
        scale[scale < 1e-6] = 1
        dx, ex = (x_fit[fi] - mean) / scale, (x_eval[ei] - mean) / scale
        models = {}
        for task in ["absolute_a", "absolute_b", "structural_a", "structural_b"]:
            models[task] = RidgeClassifier(alpha=1.0, solver="lsqr").fit(dx, y_fit[task][fi])
        abs_basis = orthonormal_basis(np.concatenate([models[t].coef_ for t in ["absolute_a", "absolute_b"]]), 2)
        struct_basis = orthonormal_basis(np.concatenate([models[t].coef_ for t in ["structural_a", "structural_b"]]), 2)
        task_effects = []
        for task in ["absolute_a", "absolute_b"]:
            yfd, yed = y_fit[task][fi], y_eval[task][ei]
            raw = float(f1_score(yed, models[task].predict(ex), average="macro"))
            chance = chance_score(yfd, yed)
            assigned_model = RidgeClassifier(alpha=1.0, solver="lsqr").fit(dx @ abs_basis, yfd)
            other_model = RidgeClassifier(alpha=1.0, solver="lsqr").fit(dx @ struct_basis, yfd)
            assigned = float(f1_score(yed, assigned_model.predict(ex @ abs_basis), average="macro"))
            other = float(f1_score(yed, other_model.predict(ex @ struct_basis), average="macro"))
            denominator = raw - chance
            task_effects.append((assigned - other) / denominator if denominator > 0.02 else np.nan)
        estimates.append(float(np.nanmean(task_effects)))
    ci = percentile_ci(estimates)
    return {"passed": ci[0] > 0.20, "draws": draws, "refits_per_draw": 8, "selectivity_ci": ci,
            "refit_scaler_probe_subspace_each_draw": True}


def firewall_regime() -> dict[str, Any]:
    discovery = {"a", "b"}; calibration = {"c"}; confirmation = {"d"}; final = {"e"}
    clean = not ((discovery & calibration) | (discovery & confirmation) | (discovery & final) |
                 (calibration & confirmation) | (calibration & final) | (confirmation & final))
    duplicate_fixture_detected = bool({"a", "b"} & {"b", "c"})
    train = np.array([[0.0], [2.0]])
    eval_x = np.array([[100.0]])
    probe = fit_probe(np.column_stack([train, [0.0, 1.0]]), np.array([0, 1]), 1.0)
    train_only_mean = probe.scaler_mean.tolist()
    vocab = {"known"}; eval_labels = ["known", "unseen"]
    mapped = [x if x in vocab else "__DROP__" for x in eval_labels]
    imbalanced_fit = np.array([0] * 90 + [1] * 10)
    imbalanced_eval = np.array([0] * 180 + [1] * 20)
    imbalance_chance = chance_score(imbalanced_fit, imbalanced_eval)
    decisions = {
        "invalid": render_joint_decision(invalid=True, simple_equivalent_families=3, g1_topology="broad", existing_k2_pass=True,
                                          simple_equivalence_failed=False, mandatory_g2_valid=True, negative_upper_bounds_pass=True,
                                          sensitivity_at_least_80=True, learned_new_family_advantage=False),
        "simple": render_joint_decision(invalid=False, simple_equivalent_families=2, g1_topology="none", existing_k2_pass=False,
                                         simple_equivalence_failed=False, mandatory_g2_valid=True, negative_upper_bounds_pass=False,
                                         sensitivity_at_least_80=False, learned_new_family_advantage=False),
        "learned": render_joint_decision(invalid=False, simple_equivalent_families=0, g1_topology="split", existing_k2_pass=False,
                                          simple_equivalence_failed=True, mandatory_g2_valid=True, negative_upper_bounds_pass=False,
                                          sensitivity_at_least_80=False, learned_new_family_advantage=False),
        "negative": render_joint_decision(invalid=False, simple_equivalent_families=0, g1_topology="none", existing_k2_pass=False,
                                           simple_equivalence_failed=True, mandatory_g2_valid=True, negative_upper_bounds_pass=True,
                                           sensitivity_at_least_80=True, learned_new_family_advantage=False),
    }
    l4_cases = [l4_fallback_trigger({"a": 1, "b": 1, "c": 2}, {"a": 2, "b": 2, "c": 1}),
                l4_fallback_trigger({"a": 2, "b": 2, "c": 1}, {"a": 2, "b": 2, "c": 2})]
    passed = (clean and duplicate_fixture_detected and train_only_mean[0] == 1.0 and mapped[-1] == "__DROP__"
              and np.isclose(imbalance_chance, 0.5) and decisions == {"invalid": "equivocal", "simple": "existing_simple",
              "learned": "learned_model", "negative": "supported_negative"} and l4_cases == [True, False])
    return {"passed": passed, "clean_roles": clean, "duplicate_fixture_detected": duplicate_fixture_detected,
            "train_only_scaler_mean": train_only_mean, "unknown_label_mapping": mapped,
            "imbalanced_prior_chance": imbalance_chance, "decision_matrix": decisions, "l4_trigger_cases": l4_cases}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=ROOT / "results/synthetic/atlas_v1_smoke.json")
    parser.add_argument("--bootstrap-draws", type=int, default=500)
    parser.add_argument("--randomization-draws", type=int, default=9999)
    args = parser.parse_args()
    result = {"schema_version": "atlas_v1_synthetic_smoke", "seed": 20260731,
              "positive": positive_regime(), "negative": negative_regimes(),
              "statistics": statistics_regime(args.bootstrap_draws, args.randomization_draws),
              "refit_bootstrap": refit_bootstrap_regime(args.bootstrap_draws),
              "firewall": firewall_regime()}
    result["passed"] = all(result[key]["passed"] for key in ["positive", "negative", "statistics", "refit_bootstrap", "firewall"])
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    digest = hashlib.sha256(args.output.read_bytes()).hexdigest()
    print(json.dumps({"passed": result["passed"], "output": str(args.output), "sha256": digest}, indent=2))
    if not result["passed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
