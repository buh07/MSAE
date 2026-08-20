#!/usr/bin/env python3
"""Attempt-11 endpoint-scoped numerical QA primitives.

This module contains no model training.  It defines the frozen normalized gate,
fresh-panel invariants, signed-artifact helpers, and technical-eligibility overlay.
"""
from __future__ import annotations

import fcntl
import hashlib
import json
import os
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator, Mapping, Sequence

import numpy as np

from atlas_rope_v6 import (
    LENGTH_BINS,
    SHIFTS,
    ROOT,
    atomic_json,
    atomic_jsonl,
    canonical_array_hash,
    canonical_json_bytes,
    read_json,
    read_jsonl,
    recursive_inventory,
    sha256_bytes,
    sha256_file,
    verify_envelope,
    write_signed,
)

RUN_ROOT = ROOT / "pilot_runs/20260803_atlas_rope_technical_v7"
DATA_ROOT = ROOT / "data/atlas_rope_v7_attempt11"
RAW_ROOT = ROOT / "data/atlas_rope_v7_attempt11_raw"
CONFIG_ROOT = ROOT / "configs/atlas_rope_v7"
RESULT_ROOT = ROOT / "results/atlas_rope_v7_attempt11_science"

WIDTH = 768
ROW_NORM_FLOOR = 1e-12
PRIMARY_RELATIVE_L2 = 2e-5
PRIMARY_NORM_RATIO_ERROR = 1e-5
CATASTROPHIC_RELATIVE_L2 = 5e-5
CATASTROPHIC_NORM_RATIO_ERROR = 2e-5
MAX_PRIMARY_PER_CELL = 2
MAX_PRIMARY_PER_PANEL = 6
DESCRIPTIVE_ATOL = 2e-5
DESCRIPTIVE_RTOL = 5e-6
DESCRIPTIVE_COSINE_REFERENCE = 2.5e-10
COSINE_PRODUCT_FLOOR = 1e-24

PANEL_NAMES = ("ENGLISH_CHILDES_CTETEX", "CZECH_PDT")
ATTEMPT10_TERMINAL = ROOT / "pilot_runs/20260803_atlas_rope_technical_v6/TERMINAL.json"
ATTEMPT10_TERMINAL_SHA256 = "9e11622335af072f6f273596917fd729fe38cfd4c65dd18b883fd43cc06dc109"


def stable_sha(*parts: object) -> str:
    return hashlib.sha256("\x1f".join(map(str, parts)).encode("utf-8")).hexdigest()


def verify_attempt10_terminal() -> dict[str, Any]:
    if sha256_file(ATTEMPT10_TERMINAL) != ATTEMPT10_TERMINAL_SHA256:
        raise RuntimeError("Attempt-10 terminal SHA drift")
    payload = verify_envelope(read_json(ATTEMPT10_TERMINAL))
    if (
        payload.get("schema_version") != "atlas_rope_v6_attempt10_terminal_v1"
        or payload.get("status") != "TERMINAL_GENTLE_VALIDATION_FAILED"
        or payload.get("no_retry_authorized") is not True
        or payload.get("neural_training_authorized") is not False
    ):
        raise RuntimeError("Attempt-10 terminal identity drift")
    forbidden = (
        ROOT / "configs/atlas_rope_v6/SCIENCE_AUTHORIZATION.json",
        ROOT / "results/atlas_rope_v6_attempt10_science",
    )
    if any(path.exists() for path in forbidden):
        raise RuntimeError("Attempt-10 forbidden science output exists")
    return payload


@contextmanager
def exclusive_lock(name: str) -> Iterator[None]:
    lock_root = RUN_ROOT / "locks"
    lock_root.mkdir(parents=True, exist_ok=True)
    descriptor = os.open(lock_root / f"{name}.lock", os.O_CREAT | os.O_RDWR, 0o600)
    try:
        try:
            fcntl.flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as error:
            raise RuntimeError(f"another Attempt-11 process holds {name}") from error
        yield
    finally:
        fcntl.flock(descriptor, fcntl.LOCK_UN)
        os.close(descriptor)


def new_staging(name: str, binding: str) -> Path:
    root = RUN_ROOT / "staging"
    root.mkdir(parents=True, exist_ok=True)
    # A deterministic claim path makes the check-and-create itself atomic.
    # Callers additionally hold a stage lock through final promotion.
    path = root / f"{name}-{binding[:12]}"
    try:
        path.mkdir()
    except FileExistsError as error:
        raise RuntimeError(f"stale or concurrent staging requires audit: {path}") from error
    return path


def promote(stage: Path, final: Path) -> None:
    if final.exists():
        raise RuntimeError(f"create-once output exists: {final}")
    for path in stage.rglob("*"):
        if path.is_file():
            with path.open("rb") as handle:
                os.fsync(handle.fileno())
    final.parent.mkdir(parents=True, exist_ok=True)
    os.replace(stage, final)


def row_metrics(reference: np.ndarray, candidate: np.ndarray) -> dict[str, np.ndarray]:
    a = np.asarray(reference, dtype=np.float64)
    b = np.asarray(candidate, dtype=np.float64)
    if a.shape != b.shape or a.ndim != 2:
        raise ValueError("row metrics require equal 2D arrays")
    finite_inputs = np.isfinite(a).all(axis=1) & np.isfinite(b).all(axis=1)
    na = np.linalg.norm(np.where(np.isfinite(a), a, 0.0), axis=1)
    nb = np.linalg.norm(np.where(np.isfinite(b), b, 0.0), axis=1)
    valid_norm = finite_inputs & np.isfinite(na) & np.isfinite(nb) & (na > ROW_NORM_FLOOR)
    relative = np.full(len(a), np.inf, dtype=np.float64)
    norm_ratio_error = np.full(len(a), np.inf, dtype=np.float64)
    cosine = np.full(len(a), np.inf, dtype=np.float64)
    if np.any(valid_norm):
        idx = np.flatnonzero(valid_norm)
        difference = b[idx] - a[idx]
        relative[idx] = np.linalg.norm(difference, axis=1) / na[idx]
        norm_ratio_error[idx] = np.abs(nb[idx] / na[idx] - 1.0)
        product = na[idx] * nb[idx]
        cosine[idx] = 1.0 - np.clip(
            np.einsum("ij,ij->i", a[idx], b[idx]) / np.maximum(product, COSINE_PRODUCT_FLOOR),
            -1.0,
            1.0,
        )
    coordinate = np.abs(b - a)
    bounds = DESCRIPTIVE_ATOL + DESCRIPTIVE_RTOL * np.abs(a)
    coordinate_failure = (~np.isfinite(coordinate)) | (~np.isfinite(bounds)) | (coordinate > bounds)
    coordinate_bound_ratio = np.max(
        np.divide(coordinate, bounds, out=np.full_like(coordinate, np.inf), where=np.isfinite(bounds) & (bounds > 0)),
        axis=1,
        initial=0.0,
    )
    metric_finite = np.isfinite(relative) & np.isfinite(norm_ratio_error) & np.isfinite(cosine)
    primary = (~valid_norm) | (~metric_finite) | (relative > PRIMARY_RELATIVE_L2) | (norm_ratio_error > PRIMARY_NORM_RATIO_ERROR)
    catastrophic = (~valid_norm) | (~metric_finite) | (relative > CATASTROPHIC_RELATIVE_L2) | (norm_ratio_error > CATASTROPHIC_NORM_RATIO_ERROR)
    return {
        "reference_norm": na,
        "candidate_norm": nb,
        "relative_l2": relative,
        "norm_ratio_error": norm_ratio_error,
        "cosine_distance": cosine,
        "finite": metric_finite,
        "primary_failure": primary,
        "catastrophic_failure": catastrophic,
        "coordinate_failure": coordinate_failure,
        "coordinate_bound_ratio": coordinate_bound_ratio,
        "max_abs": np.max(coordinate, axis=1, initial=0.0),
    }


def _finite_max(values: np.ndarray) -> float | None:
    return float(values.max(initial=0.0)) if np.isfinite(values).all() else None


def score_rows(reference: np.ndarray, candidate: np.ndarray) -> dict[str, Any]:
    metrics = row_metrics(reference, candidate)
    primary = int(metrics["primary_failure"].sum())
    catastrophic = int(metrics["catastrophic_failure"].sum())
    passed = primary <= MAX_PRIMARY_PER_CELL and catastrophic == 0
    return {
        "status": "PASS" if passed else "FAIL",
        "rows": int(len(reference)),
        "primary_failures": primary,
        "catastrophic_failures": catastrophic,
        "nonfinite_or_invalid_norm_rows": int((~metrics["finite"]).sum()),
        "coordinate_failing_rows": int(np.any(metrics["coordinate_failure"], axis=1).sum()),
        "coordinate_failing_elements": int(metrics["coordinate_failure"].sum()),
        "descriptive_cosine_reference_exceedances": int((metrics["cosine_distance"] > DESCRIPTIVE_COSINE_REFERENCE).sum()),
        "maxima": {
            "relative_l2": _finite_max(metrics["relative_l2"]),
            "norm_ratio_error": _finite_max(metrics["norm_ratio_error"]),
            "cosine_distance": _finite_max(metrics["cosine_distance"]),
            "absolute_difference": _finite_max(metrics["max_abs"]),
            "coordinate_bound_ratio": _finite_max(metrics["coordinate_bound_ratio"]),
        },
    }


def score_grid(reference: np.ndarray, candidate: np.ndarray, rows: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    if reference.shape != (200, WIDTH) or candidate.shape != (1200, WIDTH) or len(rows) != 200:
        raise RuntimeError("Attempt-11 grid shape/count drift")
    ref_by_cell = {(name, shift): [] for name, _, _ in LENGTH_BINS for shift in SHIFTS}
    cand_by_cell = {(name, shift): [] for name, _, _ in LENGTH_BINS for shift in SHIFTS}
    cursor = 0
    for base in range(100):
        name = str(rows[2 * base]["length_bin"])
        if str(rows[2 * base + 1]["length_bin"]) != name:
            raise RuntimeError("base row length-bin mismatch")
        for shift in SHIFTS:
            ref_by_cell[(name, shift)].extend((2 * base, 2 * base + 1))
            cand_by_cell[(name, shift)].extend((cursor, cursor + 1))
            cursor += 2
    cells: dict[str, Any] = {}
    all_primary = 0
    all_catastrophic = 0
    for name, _, _ in LENGTH_BINS:
        for shift in SHIFTS:
            ri = np.asarray(ref_by_cell[(name, shift)], dtype=np.int64)
            ci = np.asarray(cand_by_cell[(name, shift)], dtype=np.int64)
            value = score_rows(reference[ri], candidate[ci])
            cells[f"{name}|shift={shift}"] = value
            all_primary += int(value["primary_failures"])
            all_catastrophic += int(value["catastrophic_failures"])
    approximate = all(row["status"] == "PASS" for row in cells.values()) and all_primary <= MAX_PRIMARY_PER_PANEL and all_catastrophic == 0
    return {
        "approximate_equivariance_metric_pass": bool(approximate),
        "status": "PASS" if approximate else "FAIL",
        "primary_failures_panel": all_primary,
        "catastrophic_failures_panel": all_catastrophic,
        "cells": cells,
        "required_cells": 30,
    }


def cache_round_trip(reference_path: Path, replay_path: Path, row_ids: Sequence[str], replay_ids: Sequence[str]) -> dict[str, Any]:
    left = np.load(reference_path, allow_pickle=False)
    right = np.load(replay_path, allow_pickle=False)
    passed = (
        left.shape == right.shape
        and left.dtype == right.dtype
        and left.tobytes() == right.tobytes()
        and list(map(str, row_ids)) == list(map(str, replay_ids))
        and sha256_file(reference_path) == sha256_file(replay_path)
    )
    return {
        "status": "PASS" if passed else "FAIL",
        "byte_exact": bool(left.tobytes() == right.tobytes()),
        "row_ids_exact": list(map(str, row_ids)) == list(map(str, replay_ids)),
        "left_sha256": sha256_file(reference_path),
        "right_sha256": sha256_file(replay_path),
        "canonical_array_sha256": canonical_array_hash(left) if passed else None,
    }


def cross_panel_status(panel_payloads: Mapping[str, Mapping[str, Any]]) -> dict[str, bool]:
    if set(panel_payloads) != set(PANEL_NAMES):
        raise RuntimeError("both fixed validation panels are required")
    baseline = all(row.get("integrity_runtime_pass") is True for row in panel_payloads.values())
    rope = baseline and all(row.get("approximate_equivariance_pass") is True for row in panel_payloads.values())
    return {"baseline_runtime_pass": baseline, "rope_translation_pass": rope}


def make_eligibility_overlay(
    frozen_result: Mapping[str, Any], panel_payloads: Mapping[str, Mapping[str, Any]], *, artifact_lineage_valid: bool = True
) -> dict[str, Any]:
    status = cross_panel_status(panel_payloads)
    runtime_lineage_valid = bool(artifact_lineage_valid and status["baseline_runtime_pass"])
    baseline = "eligible" if runtime_lineage_valid else "ineligible"
    rope = "eligible" if runtime_lineage_valid and status["rope_translation_pass"] else "ineligible"
    promotion = str(frozen_result.get("outcome")) if runtime_lineage_valid and status["rope_translation_pass"] else "technically_ineligible"
    paths = {
        "schema_version": "eligible" if runtime_lineage_valid else "ineligible",
        "status": "eligible" if runtime_lineage_valid else "ineligible",
        "lineage": "eligible" if runtime_lineage_valid else "ineligible",
        "environment": "eligible" if runtime_lineage_valid else "ineligible",
        "neural_training_run": "eligible" if runtime_lineage_valid else "ineligible",
        "task_results.*.*": baseline,
        "relational_advantage.*.*": baseline,
        "numerical_null_qa.*": "not_applicable",
        "interventions.*.summaries.relative_gap": rope,
        "interventions.*.summaries.true_context": rope,
        "interventions.*.summaries.unrelated_context": rope,
        "interventions.*.summaries.proper_noun_substitution": baseline,
        "cross_family_specificity.*": rope,
        "delta_basis_overlap.relative_gap.*": rope,
        "delta_basis_overlap.true_context.*": rope,
        "delta_basis_overlap.unrelated_context.*": rope,
        "delta_basis_overlap.proper_noun_substitution.within": baseline,
        "delta_basis_overlap.proper_noun_substitution.cross": rope,
        "delta_basis_overlap.proper_noun_substitution.max_cross": rope,
        "delta_basis_overlap.proper_noun_substitution.pass": rope,
        "projections.*.*": rope,
        "candidate_statuses.*": rope,
        "outcome": rope,
        "technical_failure": rope,
        "technical_failure_reasons": rope,
    }
    return {
        "schema_version": "atlas_rope_v7_attempt11_technical_eligibility_overlay_v1",
        "status": "COMPLETE",
        "cross_panel": status,
        "artifact_lineage_valid": bool(artifact_lineage_valid),
        "runtime_lineage_valid": runtime_lineage_valid,
        "interpretation_authorized": runtime_lineage_valid,
        "path_eligibility": paths,
        "frozen_outcome": frozen_result.get("outcome"),
        "architecture_promotion_status": promotion,
        "frozen_result_mutated": False,
        "promotion_from_frozen_result_alone_authorized": False,
        "claim_class": "EXPLORATORY_OPENED_SCIENCE",
        "neural_training_run": False,
    }


def gate_contract() -> dict[str, Any]:
    return {
        "row_norm_floor": ROW_NORM_FLOOR,
        "primary": {"relative_l2": PRIMARY_RELATIVE_L2, "norm_ratio_error": PRIMARY_NORM_RATIO_ERROR},
        "catastrophic": {"relative_l2": CATASTROPHIC_RELATIVE_L2, "norm_ratio_error": CATASTROPHIC_NORM_RATIO_ERROR},
        "budgets": {"primary_per_cell": MAX_PRIMARY_PER_CELL, "primary_per_panel": MAX_PRIMARY_PER_PANEL, "catastrophic": 0},
        "descriptive": {"atol": DESCRIPTIVE_ATOL, "rtol": DESCRIPTIVE_RTOL, "cosine_reference": DESCRIPTIVE_COSINE_REFERENCE, "cosine_product_floor": COSINE_PRODUCT_FLOOR},
    }
