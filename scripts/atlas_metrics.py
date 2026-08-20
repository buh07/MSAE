#!/usr/bin/env python3
"""Shared deterministic metrics/statistics for the separable-information atlas."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Iterable, Sequence

import numpy as np
from scipy.optimize import linear_sum_assignment
from sklearn.linear_model import RidgeClassifier
from sklearn.metrics import f1_score
from sklearn.preprocessing import StandardScaler


@dataclass(frozen=True)
class Probe:
    scaler_mean: np.ndarray
    scaler_scale: np.ndarray
    coef: np.ndarray
    intercept: np.ndarray
    classes: np.ndarray
    alpha: float

    def transform(self, x: np.ndarray) -> np.ndarray:
        return (np.asarray(x, dtype=np.float64) - self.scaler_mean) / self.scaler_scale

    def predict(self, x: np.ndarray) -> np.ndarray:
        scores = self.transform(x) @ self.coef.T + self.intercept
        if self.coef.shape[0] == 1 and len(self.classes) == 2:
            indices = (scores[:, 0] > 0).astype(int)
        else:
            indices = np.argmax(scores, axis=1)
        return self.classes[indices]


def fit_probe(x: np.ndarray, y: np.ndarray, alpha: float) -> Probe:
    x = np.asarray(x, dtype=np.float64)
    y = np.asarray(y)
    scaler = StandardScaler().fit(x)
    model = RidgeClassifier(alpha=float(alpha), fit_intercept=True).fit(scaler.transform(x), y)
    scale = np.asarray(scaler.scale_, dtype=np.float64)
    scale[scale == 0] = 1.0
    return Probe(np.asarray(scaler.mean_), scale, np.asarray(model.coef_), np.atleast_1d(model.intercept_),
                 np.asarray(model.classes_), float(alpha))


def macro_f1(probe: Probe, x: np.ndarray, y: np.ndarray) -> float:
    return float(f1_score(y, probe.predict(x), average="macro", zero_division=0))


def majority_score(y_fit: np.ndarray, y_eval: np.ndarray) -> float:
    values, counts = np.unique(y_fit, return_counts=True)
    majority = values[np.argmax(counts)]
    pred = np.full(len(y_eval), majority, dtype=np.asarray(y_eval).dtype)
    return float(f1_score(y_eval, pred, average="macro", zero_division=0))


def chance_score(y_fit: np.ndarray, y_eval: np.ndarray) -> float:
    """Expected macro-F1 for predictions sampled from discovery label priors.

    Majority macro-F1 is retained as a descriptive baseline, but is too low to be
    a no-information denominator for macro-F1 (balanced random predictions beat it).
    """
    fit_values, fit_counts = np.unique(y_fit, return_counts=True)
    eval_values, eval_counts = np.unique(y_eval, return_counts=True)
    fit_priors = {value: count / len(y_fit) for value, count in zip(fit_values.tolist(), fit_counts.tolist())}
    eval_priors = {value: count / len(y_eval) for value, count in zip(eval_values.tolist(), eval_counts.tolist())}
    labels = sorted(set(fit_priors) | set(eval_priors), key=str)
    f1s = []
    for label in labels:
        predicted = fit_priors.get(label, 0.0)
        actual = eval_priors.get(label, 0.0)
        f1s.append(0.0 if predicted + actual == 0 else 2.0 * predicted * actual / (predicted + actual))
    return float(np.mean(f1s))


def normalized_recovery(component: float, raw: float, chance: float, *, raw_gap_lcb: float,
                        floor: float = 0.02) -> float | None:
    """Normalize without epsilon substitution; return None for an ineligible denominator."""
    denominator = float(raw) - float(chance)
    if not np.isfinite([component, raw, chance, raw_gap_lcb]).all() or denominator <= 0 or raw_gap_lcb <= floor:
        return None
    return float((component - chance) / denominator)


def mean_or_none(values: Sequence[float | None]) -> float | None:
    finite = [float(value) for value in values if value is not None]
    if not finite or not np.all(np.isfinite(finite)):
        return None
    return float(np.mean(finite))


def family_summary(assigned: Sequence[float | None], nonassigned: Sequence[Sequence[float | None]]) -> dict[str, float | int | None]:
    assigned_valid = [float(x) for x in assigned if x is not None and np.isfinite(x)]
    other_valid = [[float(x) for x in row if x is not None and np.isfinite(x)] for row in nonassigned]
    other_means = [float(np.mean(row)) for row in other_valid if row]
    recovery = float(np.mean(assigned_valid)) if assigned_valid else None
    leakage = max(other_means) if other_means else None
    return {"assigned_recovery": recovery, "leakage": leakage,
            "selectivity_margin": None if recovery is None or leakage is None else recovery - leakage,
            "undefined_tasks": len(assigned) - len(assigned_valid)}


def orthonormal_basis(weight_rows: np.ndarray, rank: int) -> np.ndarray:
    rows = np.asarray(weight_rows, dtype=np.float64)
    if rows.ndim != 2 or not rows.size:
        raise ValueError("weight_rows must be nonempty 2-D")
    _, singular, vt = np.linalg.svd(rows, full_matrices=False)
    effective = min(int(rank), int(np.count_nonzero(singular > max(rows.shape) * np.finfo(float).eps * singular[0])))
    if effective < 1:
        raise ValueError("weight_rows have zero numerical rank")
    return vt[:effective].T


def project(x_standardized: np.ndarray, basis: np.ndarray) -> np.ndarray:
    basis = np.asarray(basis, dtype=np.float64)
    return np.asarray(x_standardized, dtype=np.float64) @ basis @ basis.T


def principal_angles_degrees(left: np.ndarray, right: np.ndarray) -> np.ndarray:
    singular = np.linalg.svd(np.asarray(left).T @ np.asarray(right), compute_uv=False)
    return np.degrees(np.arccos(np.clip(singular, -1.0, 1.0)))


def bh_adjust(pvalues: Sequence[float]) -> np.ndarray:
    values = np.asarray(pvalues, dtype=np.float64)
    if values.ndim != 1 or np.any(~np.isfinite(values)) or np.any((values < 0) | (values > 1)):
        raise ValueError("p-values must be finite values in [0,1]")
    n = len(values)
    order = np.argsort(values, kind="mergesort")
    ranked = values[order]
    adjusted_ranked = np.minimum.accumulate((ranked * n / np.arange(1, n + 1))[::-1])[::-1]
    adjusted = np.empty(n, dtype=np.float64)
    adjusted[order] = np.minimum(adjusted_ranked, 1.0)
    return adjusted


def sign_flip_pvalue(group_effects: Sequence[float], draws: int, seed: int) -> float:
    effects = np.asarray(group_effects, dtype=np.float64)
    effects = effects[np.isfinite(effects)]
    if not len(effects):
        return float("nan")
    observed = float(np.mean(effects))
    rng = np.random.default_rng(seed)
    exceed = 0
    remaining = int(draws)
    while remaining:
        n = min(remaining, 4096)
        signs = rng.choice(np.array([-1.0, 1.0]), size=(n, len(effects)))
        exceed += int(np.sum(np.mean(signs * effects, axis=1) >= observed))
        remaining -= n
    return float((exceed + 1) / (draws + 1))


def grouped_bootstrap(groups: Sequence[str], statistic: Callable[[np.ndarray], float], draws: int,
                      seed: int) -> np.ndarray:
    groups = np.asarray(groups)
    unique = np.unique(groups)
    if len(unique) < 2:
        raise ValueError("grouped bootstrap requires at least two groups")
    indices = {group: np.flatnonzero(groups == group) for group in unique}
    rng = np.random.default_rng(seed)
    estimates = np.empty(draws, dtype=np.float64)
    for draw in range(draws):
        sampled = rng.choice(unique, size=len(unique), replace=True)
        row_indices = np.concatenate([indices[group] for group in sampled])
        estimates[draw] = statistic(row_indices)
    return estimates


def percentile_ci(samples: Sequence[float], confidence: float = 0.95) -> tuple[float, float]:
    values = np.asarray(samples, dtype=np.float64)
    alpha = (1.0 - confidence) / 2.0
    return float(np.quantile(values, alpha)), float(np.quantile(values, 1.0 - alpha))


def align_components(reference: np.ndarray, candidate: np.ndarray) -> tuple[np.ndarray, float]:
    """Permutation/sign-align candidate rows to reference rows by absolute cosine."""
    ref = np.asarray(reference, dtype=np.float64)
    cand = np.asarray(candidate, dtype=np.float64)
    ref_n = ref / np.maximum(np.linalg.norm(ref, axis=1, keepdims=True), 1e-12)
    cand_n = cand / np.maximum(np.linalg.norm(cand, axis=1, keepdims=True), 1e-12)
    similarity = ref_n @ cand_n.T
    row, col = linear_sum_assignment(-np.abs(similarity))
    aligned = cand[col].copy()
    signs = np.sign(similarity[row, col])
    signs[signs == 0] = 1
    aligned *= signs[:, None]
    return aligned, float(np.mean(np.abs(similarity[row, col])))


def monte_carlo_se(p: float, draws: int) -> float:
    return float(np.sqrt(float(p) * (1.0 - float(p)) / int(draws)))


def simultaneous_bounds(observed: Sequence[float], bootstrap: np.ndarray, confidence: float = 0.95) -> tuple[np.ndarray, np.ndarray]:
    """Single-step max-statistic simultaneous bounds for a vector of effects."""
    center = np.asarray(observed, dtype=np.float64)
    draws = np.asarray(bootstrap, dtype=np.float64)
    if draws.ndim != 2 or draws.shape[1] != len(center):
        raise ValueError("bootstrap must have shape (draws, effects)")
    if draws.shape[0] < 450:
        raise ValueError("simultaneous bounds require at least 450 valid bootstrap draws")
    if not np.all(np.isfinite(center)) or not np.all(np.isfinite(draws)):
        raise ValueError("simultaneous bounds require finite observed effects and bootstrap draws")
    alpha = 1.0 - confidence
    upper_radius = np.quantile(np.max(draws - center, axis=1), 1.0 - alpha)
    lower_radius = np.quantile(np.max(center - draws, axis=1), 1.0 - alpha)
    if not np.isfinite(upper_radius) or not np.isfinite(lower_radius):
        raise ValueError("simultaneous bound radius is nonfinite")
    return center - lower_radius, center + upper_radius


def l4_fallback_trigger(l3_eligible_tasks: dict[str, int], l4_eligible_tasks: dict[str, int]) -> bool:
    l3_families = sum(count >= 2 for count in l3_eligible_tasks.values())
    l4_families = sum(count >= 2 for count in l4_eligible_tasks.values())
    return l3_families < 2 and l4_families >= 2


def render_joint_decision(*, invalid: bool, simple_equivalent_families: int, g1_topology: str,
                          existing_k2_pass: bool, simple_equivalence_failed: bool,
                          mandatory_g2_valid: bool, negative_upper_bounds_pass: bool,
                          sensitivity_at_least_80: bool, learned_new_family_advantage: bool) -> str:
    """Exhaustive atlas G1×G2 decision with equivocal highest precedence."""
    if invalid:
        return "equivocal"
    if simple_equivalent_families >= 2:
        return "existing_simple"
    if g1_topology in {"broad", "split"} and existing_k2_pass:
        return "existing_checkpoint"
    if (g1_topology in {"broad", "split"} and not existing_k2_pass and simple_equivalence_failed
            and mandatory_g2_valid):
        return "learned_model"
    if negative_upper_bounds_pass and sensitivity_at_least_80 and not learned_new_family_advantage:
        return "supported_negative"
    return "equivocal"
