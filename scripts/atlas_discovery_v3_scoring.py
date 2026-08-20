#!/usr/bin/env python3
"""Frozen numerical and metric helpers for Atlas discovery v3.1 scoring.

No function in this module updates neural parameters.
"""

from __future__ import annotations

from typing import Any

import numpy as np


def resolve_hidden_state_index(requested_layer: int, n_hidden_states: int) -> int:
    if requested_layer < 0 or n_hidden_states < 2:
        raise ValueError("invalid hidden-state layer request")
    maximum_block = n_hidden_states - 2
    if requested_layer > maximum_block:
        raise ValueError("requested layer exceeds available transformer blocks")
    return requested_layer + 1


def derive_numerical_tolerance(
    max_abs_repeat_error: float,
    *,
    atol_floor: float,
    atol_hard_ceiling: float,
    multiplier: float,
    rtol: float,
) -> dict[str, Any]:
    values = (max_abs_repeat_error, atol_floor, atol_hard_ceiling, multiplier, rtol)
    if (
        not all(np.isfinite(values))
        or min(values) < 0
        or multiplier <= 0
        or rtol <= 0
        or atol_floor >= atol_hard_ceiling
    ):
        raise ValueError("invalid numerical tolerance configuration")
    candidate = multiplier * max_abs_repeat_error
    valid = candidate < atol_hard_ceiling
    return {
        "status": "valid" if valid else "invalid",
        "max_abs_repeat_error": float(max_abs_repeat_error),
        "atol": float(max(atol_floor, candidate)) if valid else None,
        "rtol": float(rtol),
    }


def elementwise_null_pass(
    reference: np.ndarray,
    candidate: np.ndarray,
    *,
    atol: float,
    rtol: float,
) -> bool:
    left = np.asarray(reference, dtype=np.float64)
    right = np.asarray(candidate, dtype=np.float64)
    if left.shape != right.shape or not np.isfinite(left).all() or not np.isfinite(right).all():
        return False
    return bool(np.all(np.abs(right - left) <= atol + rtol * np.abs(left)))


def independent_prior_macro_f1(fit_priors: np.ndarray, heldout_prevalence: np.ndarray) -> float:
    p = np.asarray(fit_priors, dtype=np.float64)
    q = np.asarray(heldout_prevalence, dtype=np.float64)
    if p.ndim != 1 or q.shape != p.shape or not np.isfinite(p).all() or not np.isfinite(q).all():
        raise ValueError("invalid prior vectors")
    if np.any(p < 0) or np.any(q < 0) or not np.isclose(p.sum(), 1.0) or not np.isclose(q.sum(), 1.0):
        raise ValueError("priors must be probability vectors")
    denominator = p + q
    terms = np.divide(2.0 * p * q, denominator, out=np.zeros_like(p), where=denominator != 0)
    return float(terms.mean())


def normalized_recovery(score: float, chance: float) -> float:
    if not np.isfinite(score) or not np.isfinite(chance) or chance >= 1.0:
        return float("nan")
    return float((score - chance) / (1.0 - chance))
