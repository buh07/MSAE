#!/usr/bin/env python3
"""Attempt-10 budget-aligned RoPE QA amendment and one-shot GENTLE runner.

EWT and GUM are read-only signed calibration histories.  The only technical
model call in this module is the once-authorized GENTLE validation call.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path
from typing import Any, Mapping, Sequence

os.environ.setdefault("CUBLAS_WORKSPACE_CONFIG", ":4096:8")
import numpy as np
import torch

sys.path.insert(0, str(Path(__file__).resolve().parent))

import run_atlas_rope_v5 as attempt9_code
from atlas_rope_v6 import (
    AUTH_SCHEMA, BUNDLE_SCHEMA, COSINE_GRID, REL_L2_GRID, ROOT, RTOL, RUN_ROOT,
    WIDTH, assert_output_allowlist, atomic_json, canonical_array_hash,
    exact_cached_replay, exclusive_lock, inventory_digest, new_staging, promote,
    read_json, read_jsonl, recursive_inventory, score_cell, score_grid,
    sha256_file, sign_terminal, static_no_training_scan, verify_envelope,
    write_signed,
)

ATTEMPT9_ROOT = ROOT / "pilot_runs/20260803_atlas_rope_technical_v5"
ATTEMPT9_TERMINAL = ATTEMPT9_ROOT / "TERMINAL.json"
ATTEMPT9_GUM_GRID = ATTEMPT9_ROOT / "validation/GUM_grid"
ATTEMPT9_GUM_SENTINEL = ATTEMPT9_ROOT / "validation/GUM_sentinel"
ATTEMPT8_ROOT = ROOT / "pilot_runs/20260803_atlas_rope_technical_v4"
ATTEMPT8_DATA_ROOT = ROOT / "data/atlas_rope_v4_attempt8"
DATA_ROOT = ROOT / "data/atlas_rope_v5_attempt9"
CONFIG_PATH = ROOT / "configs/atlas_rope_v5/prescore.json"
AMENDMENT_CONFIG = ROOT / "configs/atlas_rope_v6/amendment.json"
SCIENCE_ADAPTER_CONFIG = ROOT / "configs/atlas_rope_v6/science_adapter.json"
IMPLEMENTATION_CANDIDATE = ROOT / "configs/atlas_rope_v6/implementation_candidate.json"
IMPLEMENTATION_HOTFIX = ROOT / "configs/atlas_rope_v6/IMPLEMENTATION_HOTFIX.json"
HOTFIX_CANDIDATE = ROOT / "configs/atlas_rope_v6/hotfix_candidate.json"
ATTEMPT9_RETIREMENT = RUN_ROOT / "provenance/ATTEMPT9_RETIRED.json"
CALIBRATION_IMPORT = RUN_ROOT / "calibration_history/EWT_GUM_IMPORT.json"
CALIBRATION_CAP_CANDIDATE = ROOT / "configs/atlas_rope_v6/CALIBRATION_CAP_CANDIDATE.json"
FREEZE_CANDIDATE = ROOT / "configs/atlas_rope_v6/validation_freeze_candidate.json"
VALIDATION_AUTHORIZATION = ROOT / "configs/atlas_rope_v6/VALIDATION_AUTHORIZATION.json"
SCIENCE_AUTHORIZATION = ROOT / "configs/atlas_rope_v6/SCIENCE_AUTHORIZATION.json"
TERMINAL_PATH = RUN_ROOT / "TERMINAL.json"
GENTLE_GRID = RUN_ROOT / "validation/GENTLE_grid"
GENTLE_PASS = RUN_ROOT / "validation/GENTLE_PASS.json"
GPU_UUID = attempt9_code.GPU_UUID
_load_model = attempt9_code._load_model
_runtime_attestation = attempt9_code._runtime_attestation
_seed_runtime = attempt9_code._seed_runtime
_retained_attempt7_pair = attempt9_code._retained_attempt7_pair
_verify_attempt8_history = attempt9_code._verify_attempt8_history

FIXED_ATOL = 2e-5
FIXED_RTOL = 5e-6
RELATIVE_SEARCH = (2e-6, 5e-6, 1e-5, 2e-5)
COSINE_SEARCH = (1e-11, 5e-11, 1e-10)
SELECTED_CAPS = {"atol": 2e-5, "relative_l2": 2e-5, "cosine_distance": 5e-11}

ATTEMPT9_EXPECTED_ABSENCES = (
    ATTEMPT9_ROOT / "validation/GUM_PASS.json",
    ATTEMPT9_ROOT / "validation/GENTLE_grid",
    ATTEMPT9_ROOT / "validation/GENTLE_PASS.json",
    ATTEMPT9_ROOT / "science",
    ROOT / "configs/atlas_rope_v5/SCIENCE_AUTHORIZATION.json",
    ROOT / "results/atlas_rope_v5_attempt9_science",
)

IMPLEMENTATION_PATHS = (
    "PLAN_ATTEMPT10.md",
    "configs/atlas_rope_v6/amendment.json",
    "configs/atlas_rope_v6/science_adapter.json",
    "docs/rfc-atlas-v3-6-attempt10-budget-amendment.md",
    "requirements-atlas.lock.txt",
    "scripts/atlas_rope_v6.py",
    "scripts/run_atlas_rope_v6.py",
    "scripts/run_atlas_rope_v6_science.py",
    "scripts/run_atlas_rope_v6_pipeline.sh",
    "scripts/launch_atlas_rope_v6_tmux.sh",
    "tests/test_atlas_rope_v6.py",
    "tests/test_atlas_rope_v6_science.py",
)


def _assert_not_terminal() -> None:
    if (RUN_ROOT / "SIGNING_FAULT.json").exists():
        raise RuntimeError("attempt 10 has a terminal signing fault")
    if TERMINAL_PATH.exists():
        terminal = verify_envelope(read_json(TERMINAL_PATH))
        raise RuntimeError(f"attempt 10 is terminal: {terminal.get('status')}")


def _verify_amendment_contract() -> dict[str, Any]:
    config = read_json(AMENDMENT_CONFIG)
    expected = {
        "schema_version": "atlas_rope_v6_attempt10_budget_amendment_v1",
        "status": "FROZEN_IMPLEMENTATION_INPUT",
        "attempt9_terminal": {"path": str(ATTEMPT9_TERMINAL.relative_to(ROOT)),
                              "sha256": "83a369af693019c768284adfef5811bf7cc56eb9d226d8449e514abf12ecbf06"},
        "calibration_union": {"EWT_attempt8_cells": 30, "GUM_attempt9_cells": 30, "total_cells": 60,
                              "attempt7_rows_separate": 72},
        "caps": {"fixed_atol": FIXED_ATOL, "fixed_rtol": FIXED_RTOL,
                 "relative_l2_outer": list(RELATIVE_SEARCH), "cosine_inner": list(COSINE_SEARCH),
                 "required_selected": SELECTED_CAPS},
        "budgets": {"failing_elements_per_cell": 30, "failing_rows_per_cell": 2,
                    "relative_l2_failures": 0, "cosine_failures": 0},
        "validation_source": "GENTLE_validation", "validation_attempts": 1,
        "new_ewt_or_gum_forward_authorized": False, "neural_training_authorized": False,
        "science_claim_class": "EXPLORATORY_GUM_TECHNICAL_CALIBRATION_DUAL_ROLE",
    }
    if config != expected:
        raise RuntimeError("frozen amendment config/executable contract drift")
    return config


def _terminalize(signing_key: Path, *, status: str, reason: str) -> None:
    if TERMINAL_PATH.exists():
        verify_envelope(read_json(TERMINAL_PATH))
        return
    lineage = {}
    for name, path in {
        "validation_authorization": VALIDATION_AUTHORIZATION,
        "gentle_complete": GENTLE_GRID / "COMPLETE.json",
        "gentle_pass": GENTLE_PASS,
        "science_authorization": SCIENCE_AUTHORIZATION,
    }.items():
        if path.is_file():
            lineage[name] = {"path": str(path.relative_to(ROOT)), "sha256": sha256_file(path)}
    sign_terminal(signing_key.resolve(strict=True), status=status, reason=reason[:2000], lineage=lineage)


def _review_ship(path: Path, artifact: Path) -> dict[str, str]:
    path = path.resolve(strict=True)
    text = path.read_text(encoding="utf-8")
    digest = sha256_file(artifact)
    if "VERDICT: SHIP" not in text or digest not in text:
        raise RuntimeError(f"review does not SHIP exact artifact {digest}")
    return {"path": str(path.relative_to(ROOT)), "sha256": sha256_file(path), "reviewed_sha256": digest}


def _file_inventory(paths: Sequence[str]) -> dict[str, dict[str, Any]]:
    output = {}
    for raw in paths:
        path = ROOT / raw
        if not path.is_file() or path.is_symlink():
            raise RuntimeError(f"missing regular implementation file: {raw}")
        output[raw] = {"bytes": path.stat().st_size, "sha256": sha256_file(path)}
    return output


def make_implementation_candidate(verification_report: Path) -> dict[str, Any]:
    if RUN_ROOT.exists() or IMPLEMENTATION_CANDIDATE.exists():
        raise RuntimeError("attempt-10 implementation candidate must precede all attempt artifacts")
    verification_report = verification_report.resolve(strict=True)
    report = read_json(verification_report)
    if report.get("status") != "PASS":
        raise RuntimeError("implementation verification did not pass")
    inventory = _file_inventory(IMPLEMENTATION_PATHS)
    scan = static_no_training_scan([ROOT / raw for raw in IMPLEMENTATION_PATHS if raw.endswith(".py")])
    if scan["status"] != "PASS":
        raise RuntimeError(f"training primitive found: {scan}")
    payload = {
        "schema_version": "atlas_rope_v6_attempt10_implementation_candidate_v1",
        "status": "READY_FOR_IMPLEMENTATION_ADVERSARIAL_REVIEW",
        "implementation_inventory": inventory,
        "implementation_inventory_sha256": inventory_digest(inventory),
        "verification_report": {"path": str(verification_report.relative_to(ROOT)), "sha256": sha256_file(verification_report)},
        "static_no_training_scan": scan,
        "attempt10_run_root_absent": True,
        "neural_training_authorized": False,
    }
    atomic_json(IMPLEMENTATION_CANDIDATE, payload)
    return payload


def _verify_implementation_candidate() -> dict[str, Any]:
    candidate = read_json(IMPLEMENTATION_CANDIDATE)
    if candidate.get("status") != "READY_FOR_IMPLEMENTATION_ADVERSARIAL_REVIEW":
        raise RuntimeError("implementation candidate status drift")
    inventory = _file_inventory(tuple(candidate["implementation_inventory"]))
    expected_inventory = candidate["implementation_inventory"]
    if inventory != expected_inventory:
        mismatches = [name for name in expected_inventory if inventory.get(name) != expected_inventory[name]]
        if mismatches != ["scripts/run_atlas_rope_v6.py"] or not IMPLEMENTATION_HOTFIX.is_file():
            raise RuntimeError(f"reviewed implementation inventory drift: {mismatches}")
        hotfix = verify_envelope(read_json(IMPLEMENTATION_HOTFIX))
        hotfix_candidate = read_json(HOTFIX_CANDIDATE)
        candidate_sha = sha256_file(HOTFIX_CANDIDATE)
        proposed_path = ROOT / str(hotfix_candidate.get("proposed_path", ""))
        patch_path = ROOT / str(hotfix_candidate.get("diff_path", ""))
        review_path = ROOT / str(hotfix.get("review", {}).get("path", ""))
        if (hotfix_candidate.get("schema_version") != "atlas_rope_v6_attempt10_prevalidation_hotfix_candidate_v1" or
                hotfix_candidate.get("status") != "READY_FOR_ADVERSARIAL_REVIEW" or
                hotfix_candidate.get("base_implementation_candidate_sha256") != sha256_file(IMPLEMENTATION_CANDIDATE) or
                hotfix_candidate.get("target") != "scripts/run_atlas_rope_v6.py" or
                hotfix_candidate.get("old_sha256") != expected_inventory["scripts/run_atlas_rope_v6.py"]["sha256"] or
                hotfix_candidate.get("new_sha256") != inventory["scripts/run_atlas_rope_v6.py"]["sha256"] or
                not proposed_path.is_file() or sha256_file(proposed_path) != hotfix_candidate.get("new_sha256") or
                not patch_path.is_file() or sha256_file(patch_path) != hotfix_candidate.get("diff_sha256") or
                hotfix.get("schema_version") != "atlas_rope_v6_attempt10_prevalidation_hotfix_v1" or
                hotfix.get("status") != "AUTHORIZED_PREVALIDATION_HOTFIX" or
                hotfix.get("base_implementation_candidate_sha256") != hotfix_candidate.get("base_implementation_candidate_sha256") or
                hotfix.get("target") != hotfix_candidate.get("target") or
                hotfix.get("old_sha256") != hotfix_candidate.get("old_sha256") or
                hotfix.get("new_sha256") != hotfix_candidate.get("new_sha256") or
                hotfix.get("hotfix_candidate_sha256") != candidate_sha or
                not review_path.is_file() or sha256_file(review_path) != hotfix.get("review", {}).get("sha256") or
                "VERDICT: SHIP" not in review_path.read_text(encoding="utf-8") or
                candidate_sha not in review_path.read_text(encoding="utf-8") or
                hotfix.get("neural_training_authorized") is not False):
            raise RuntimeError("signed/reviewed implementation hotfix drift")
    elif inventory_digest(inventory) != candidate["implementation_inventory_sha256"]:
        raise RuntimeError("reviewed implementation inventory digest drift")
    report_path = ROOT / candidate["verification_report"]["path"]
    if sha256_file(report_path) != candidate["verification_report"]["sha256"] or read_json(report_path).get("status") != "PASS":
        raise RuntimeError("implementation verification lineage drift")
    _verify_amendment_contract()
    return candidate


def _attempt9_required_absences() -> list[str]:
    return [str(path.relative_to(ROOT)) for path in ATTEMPT9_EXPECTED_ABSENCES if path.exists()]


def _verify_attempt9_terminal() -> dict[str, Any]:
    amendment = _verify_amendment_contract()
    if sha256_file(ATTEMPT9_TERMINAL) != amendment["attempt9_terminal"]["sha256"]:
        raise RuntimeError("attempt-9 terminal SHA differs from frozen amendment")
    terminal = verify_envelope(read_json(ATTEMPT9_TERMINAL))
    if (terminal.get("schema_version") != "atlas_rope_v5_attempt9_terminal_v1" or
            terminal.get("status") != "TERMINAL_GUM_VALIDATION_FAILED" or
            terminal.get("no_retry_authorized") is not True):
        raise RuntimeError("attempt-9 terminal identity drift")
    present = _attempt9_required_absences()
    if present:
        raise RuntimeError(f"attempt-9 forbidden downstream outputs exist: {present}")
    expected_lineage = {
        "gum_grid_complete": sha256_file(ATTEMPT9_GUM_GRID / "COMPLETE.json"),
        "gum_sentinel_complete": sha256_file(ATTEMPT9_GUM_SENTINEL / "COMPLETE.json"),
    }
    for name, digest in expected_lineage.items():
        if terminal.get("lineage", {}).get(name, {}).get("sha256") != digest:
            raise RuntimeError(f"attempt-9 terminal lineage drift: {name}")
    return terminal


def _load_grid_history(root: Path, source: str, data_source: str) -> tuple[np.ndarray, np.ndarray, list[dict[str, Any]], dict[str, Any]]:
    complete_path = root / "COMPLETE.json"
    payload = verify_envelope(read_json(complete_path))
    allowed = {"reference.float32.npy", "reference_repeat_1.float32.npy", "reference_repeat_2.float32.npy",
               "reference_cached_replay.float32.npy", "candidate.float32.npy", "row_ids.json", "COMPLETE.json"}
    assert_output_allowlist(root, allowed)
    if set(payload.get("artifacts", {})) != allowed - {"COMPLETE.json"}:
        raise RuntimeError(f"{source} signed artifact inventory drift")
    for name, spec in payload["artifacts"].items():
        path = root / name
        if path.stat().st_size != int(spec["bytes"]) or sha256_file(path) != spec["sha256"]:
            raise RuntimeError(f"{source} artifact drift: {name}")
    arrays = {name: np.load(root / f"{name}.float32.npy", allow_pickle=False)
              for name in ("reference", "reference_repeat_1", "reference_repeat_2", "reference_cached_replay", "candidate")}
    if (arrays["reference"].shape != (200, WIDTH) or arrays["candidate"].shape != (1200, WIDTH) or
            any(arrays[name].shape != (200, WIDTH) for name in ("reference_repeat_1", "reference_repeat_2", "reference_cached_replay")) or
            any(a.dtype != np.float32 or not a.flags.c_contiguous or not np.isfinite(a).all() for a in arrays.values())):
        raise RuntimeError(f"{source} grid array structure drift")
    if any(not np.array_equal(arrays["reference"], arrays[name]) or arrays["reference"].tobytes() != arrays[name].tobytes()
           for name in ("reference_repeat_1", "reference_repeat_2", "reference_cached_replay")):
        raise RuntimeError(f"{source} replay/live references differ")
    rows = read_jsonl(DATA_ROOT / data_source / "rows.jsonl") if data_source != "EWT_calibration" else read_jsonl(ATTEMPT8_DATA_ROOT / data_source / "rows.jsonl")
    candidates = read_jsonl(DATA_ROOT / data_source / "candidates.jsonl") if data_source != "EWT_calibration" else read_jsonl(ATTEMPT8_DATA_ROOT / data_source / "candidates.jsonl")
    ids = read_json(root / "row_ids.json")
    expected = {"reference": [str(row["row_id"]) for row in rows],
                "candidate": [str(row_id) for unit in candidates for row_id in unit["row_ids"]]}
    if ids != expected:
        raise RuntimeError(f"{source} row lineage drift")
    replay = exact_cached_replay(
        arrays["reference"], arrays["reference_cached_replay"], expected["reference"], expected["reference"],
        left_child_hash=sha256_file(root / "reference.float32.npy"),
        right_child_hash=sha256_file(root / "reference_cached_replay.float32.npy"),
    )
    if replay.get("status") != "PASS" or replay != payload.get("exact_cached_replay"):
        raise RuntimeError(f"{source} signed cached-replay drift/failure")
    if (canonical_array_hash(arrays["reference"]) != payload.get("reference_array_sha256") or
            canonical_array_hash(arrays["candidate"]) != payload.get("candidate_array_sha256")):
        raise RuntimeError(f"{source} signed canonical-array hash drift")
    panel_path = DATA_ROOT / data_source / "panel.json"
    panel = read_json(panel_path)
    if payload.get("panel_sha256") != sha256_file(panel_path) or payload.get("logical_counts") != panel.get("logical_counts"):
        raise RuntimeError(f"{source} signed panel/count lineage drift")
    expected_identity = {
        "GUM": ("atlas_rope_v5_attempt9_technical_bundle_v1", "GUM_fresh_validation", "FAIL"),
        "GENTLE": (BUNDLE_SCHEMA, "GENTLE_validation", payload.get("status")),
    }[source]
    if (payload.get("schema_version"), payload.get("source"), payload.get("status")) != expected_identity or payload.get("bundle_kind") != "minimal_grid":
        raise RuntimeError(f"{source} signed bundle identity drift")
    if payload.get("live_reference_repeats_byte_identical") is not True:
        raise RuntimeError(f"{source} signed live-repeat attestation drift")
    required_false = ("labels_loaded", "estimator_created", "parameter_update_run", "checkpoint_created", "neural_training_run")
    if (payload.get("model_eval") is not True or payload.get("inference_mode") is not True or payload.get("requires_grad") is not False or
            any(payload.get(name) is not False for name in required_false)):
        raise RuntimeError(f"{source} inference/no-training attestation drift")
    expected_runtime_sources = read_json(CONFIG_PATH)["runtime"]["source_hashes"]
    for phase in ("runtime_preflight", "runtime_postflight"):
        runtime = payload.get(phase, {})
        if (runtime.get("required_library_check", {}).get("status") != "PASS" or runtime.get("gpu_uuid") != GPU_UUID or
                runtime.get("attention_backend") != "sdpa" or runtime.get("source_hashes") != expected_runtime_sources):
            raise RuntimeError(f"{source} signed {phase} runtime attestation drift")
    if source == "GUM":
        authorization = payload.get("authorization", {})
        auth_path = ROOT / str(authorization.get("path", ""))
        if (not auth_path.is_file() or sha256_file(auth_path) != authorization.get("sha256") or
                authorization.get("sha256") != sha256_file(ROOT / "configs/atlas_rope_v5/VALIDATION_AUTHORIZATION.json")):
            raise RuntimeError("GUM signed validation authorization lineage drift")
        attempt9_code._verify_authorization(auth_path, stage="SEQUENTIAL_HELDOUT_VALIDATION")
    else:
        if payload.get("authorization_sha256") != sha256_file(VALIDATION_AUTHORIZATION):
            raise RuntimeError("GENTLE signed validation authorization lineage drift")
        _verify_authorization(VALIDATION_AUTHORIZATION, "GENTLE_ONLY_VALIDATION_ONCE")
    return arrays["reference"], arrays["candidate"], rows, {
        "complete_sha256": sha256_file(complete_path), "tree_inventory": recursive_inventory(root),
        "reference_canonical_sha256": canonical_array_hash(arrays["reference"]),
        "candidate_canonical_sha256": canonical_array_hash(arrays["candidate"]),
        "exact_cached_replay": replay, "signed_payload": payload,
    }


def _verify_ewt_history() -> tuple[np.ndarray, np.ndarray, list[dict[str, Any]], dict[str, Any]]:
    reference, candidate, lineage = attempt9_code._verify_attempt8_history()
    rows = read_jsonl(ATTEMPT8_DATA_ROOT / "EWT_calibration/rows.jsonl")
    return reference, candidate, rows, lineage


def _verify_gum_history() -> tuple[np.ndarray, np.ndarray, list[dict[str, Any]], dict[str, Any]]:
    _verify_attempt9_terminal()
    reference, candidate, rows, lineage = _load_grid_history(ATTEMPT9_GUM_GRID, "GUM", "GUM_fresh_validation")
    complete = verify_envelope(read_json(ATTEMPT9_GUM_GRID / "COMPLETE.json"))
    old = score_grid(reference, candidate, rows, atol=2e-5, relative_l2_cap=1e-5, cosine_cap=1e-11)
    if old != complete.get("score") or old.get("status") != "FAIL" or len(old.get("cells", {})) != 30:
        raise RuntimeError("attempt-9 GUM failure does not independently recompute")
    lineage["attempt9_score_under_frozen_caps"] = old
    lineage["terminal_sha256"] = sha256_file(ATTEMPT9_TERMINAL)
    return reference, candidate, rows, lineage


def _verify_gum_sentinel_history(caps: Mapping[str, float]) -> dict[str, Any]:
    _verify_attempt9_terminal()
    root = ATTEMPT9_GUM_SENTINEL
    allowed = {"reference.float32.npy", "reference_repeat_1.float32.npy", "reference_repeat_2.float32.npy",
               "reference_cached_replay.float32.npy", "candidate.float32.npy", "pair_scores.json", "row_ids.json", "COMPLETE.json"}
    assert_output_allowlist(root, allowed)
    complete = verify_envelope(read_json(root / "COMPLETE.json"))
    if (complete.get("bundle_kind") != "fresh_gum_sentinel" or complete.get("status") != "PASS" or
            set(complete.get("artifacts", {})) != allowed - {"COMPLETE.json"}):
        raise RuntimeError("attempt-9 GUM sentinel signed identity drift")
    for name, spec in complete["artifacts"].items():
        path = root / name
        if path.stat().st_size != int(spec["bytes"]) or sha256_file(path) != spec["sha256"]:
            raise RuntimeError(f"attempt-9 GUM sentinel artifact drift: {name}")
    arrays = {name: np.load(root / f"{name}.float32.npy", allow_pickle=False)
              for name in ("reference", "reference_repeat_1", "reference_repeat_2", "reference_cached_replay", "candidate")}
    if any(a.shape != (24, WIDTH) or a.dtype != np.float32 or not a.flags.c_contiguous or not np.isfinite(a).all() for a in arrays.values()):
        raise RuntimeError("attempt-9 GUM sentinel array structure drift")
    if any(not np.array_equal(arrays["reference"], arrays[name]) for name in ("reference_repeat_1", "reference_repeat_2", "reference_cached_replay")):
        raise RuntimeError("attempt-9 GUM sentinel replay/live reference drift")
    panel, _, _, pair_rows = attempt9_code._load_sentinel_panel()
    row_ids = list(map(str, panel["expanded_row_ids"]))
    if read_json(root / "row_ids.json") != {"expanded_row_ids": row_ids}:
        raise RuntimeError("attempt-9 GUM sentinel row-ID lineage drift")
    replay = exact_cached_replay(arrays["reference"], arrays["reference_cached_replay"], row_ids, row_ids,
                                 left_child_hash=sha256_file(root / "reference.float32.npy"),
                                 right_child_hash=sha256_file(root / "reference_cached_replay.float32.npy"))
    if replay.get("status") != "PASS" or replay != complete.get("exact_cached_replay"):
        raise RuntimeError("attempt-9 GUM sentinel signed replay drift/failure")
    if (complete.get("panel_sha256") != sha256_file(DATA_ROOT / "GUM_fresh_sentinel/panel.json") or
            complete.get("authorization_sha256") != sha256_file(ROOT / "configs/atlas_rope_v5/VALIDATION_AUTHORIZATION.json") or
            complete.get("live_reference_repeats_byte_identical") is not True):
        raise RuntimeError("attempt-9 GUM sentinel panel/authorization/repeat lineage drift")
    attempt9_code._verify_authorization(ROOT / "configs/atlas_rope_v5/VALIDATION_AUTHORIZATION.json", stage="SEQUENTIAL_HELDOUT_VALIDATION")
    required_false = ("labels_loaded", "estimator_created", "parameter_update_run", "checkpoint_created", "neural_training_run")
    if (complete.get("model_eval") is not True or complete.get("inference_mode") is not True or complete.get("requires_grad") is not False or
            any(complete.get(name) is not False for name in required_false)):
        raise RuntimeError("attempt-9 GUM sentinel inference/no-training attestation drift")
    expected_runtime_sources = read_json(CONFIG_PATH)["runtime"]["source_hashes"]
    for phase in ("runtime_preflight", "runtime_postflight"):
        runtime = complete.get(phase, {})
        if (runtime.get("required_library_check", {}).get("status") != "PASS" or runtime.get("gpu_uuid") != GPU_UUID or
                runtime.get("attention_backend") != "sdpa" or runtime.get("source_hashes") != expected_runtime_sources):
            raise RuntimeError(f"attempt-9 GUM sentinel {phase} runtime drift")
    signed_rows = read_json(root / "pair_scores.json")["pairs"]
    if len(signed_rows) != len(pair_rows) or any(
            {key: row[key] for key in ("pair_id", "reference_unit_id", "candidate_unit_id", "expanded_row_ids", "roles")} !=
            {key: expected[key] for key in ("pair_id", "reference_unit_id", "candidate_unit_id", "expanded_row_ids", "roles")}
            for row, expected in zip(signed_rows, pair_rows, strict=True)):
        raise RuntimeError("attempt-9 GUM sentinel signed pair lineage drift")
    old_caps = complete.get("caps")
    if old_caps != {"atol": 2e-5, "relative_l2": 1e-5, "cosine_distance": 1e-11}:
        raise RuntimeError("attempt-9 GUM sentinel original caps drift")
    cursor = 0; rescored = []
    for row in signed_rows:
        width = len(row["roles"])
        original = score_cell(arrays["reference"][cursor:cursor + width], arrays["candidate"][cursor:cursor + width],
                              atol=float(old_caps["atol"]), relative_l2_cap=float(old_caps["relative_l2"]),
                              cosine_cap=float(old_caps["cosine_distance"]), strict_zero_failures=True)
        if (original != row.get("score") or original["status"] != "PASS" or
                canonical_array_hash(np.ascontiguousarray(arrays["reference"][cursor:cursor + width])) != row.get("reference_rows_sha256") or
                canonical_array_hash(np.ascontiguousarray(arrays["candidate"][cursor:cursor + width])) != row.get("candidate_rows_sha256")):
            raise RuntimeError(f"attempt-9 GUM sentinel original signed score/hash drift: {row['pair_id']}")
        stat = score_cell(arrays["reference"][cursor:cursor + width], arrays["candidate"][cursor:cursor + width],
                          atol=float(caps["atol"]), relative_l2_cap=float(caps["relative_l2"]),
                          cosine_cap=float(caps["cosine_distance"]), strict_zero_failures=True)
        if stat["status"] != "PASS":
            raise RuntimeError(f"attempt-9 GUM sentinel fails selected caps: {row['pair_id']}")
        rescored.append({"pair_id": row["pair_id"], "family": row["family"], "score": stat})
        cursor += width
    if cursor != 24 or len(rescored) != 16:
        raise RuntimeError("attempt-9 GUM sentinel completeness drift")
    return {"status": "PASS", "pairs": rescored, "complete_sha256": sha256_file(root / "COMPLETE.json"),
            "exact_cached_replay": replay, "original_signed_status": complete["status"]}


def _attempt7_family_scores(caps: Mapping[str, float]) -> dict[str, Any]:
    reference, candidate, lineage = attempt9_code._retained_attempt7_pair()
    output = {}
    for key, indices in lineage["family_indices"].items():
        idx = np.asarray(indices, dtype=np.int64)
        score = score_cell(reference[idx], candidate[idx], atol=float(caps["atol"]),
                           relative_l2_cap=float(caps["relative_l2"]), cosine_cap=float(caps["cosine_distance"]),
                           strict_zero_failures=True)
        if score["status"] != "PASS":
            raise RuntimeError(f"Attempt-7 family fails selected caps: {key}")
        output[key] = score
    return {"rows": len(reference), "families": output, "lineage": lineage}


def _score_calibration_union(atol: float, relative: float, cosine: float) -> dict[str, Any]:
    er, ec, e_rows, _ = _verify_ewt_history()
    gr, gc, g_rows, _ = _verify_gum_history()
    ewt = score_grid(er, ec, e_rows, atol=atol, relative_l2_cap=relative, cosine_cap=cosine)
    gum = score_grid(gr, gc, g_rows, atol=atol, relative_l2_cap=relative, cosine_cap=cosine)
    return {"status": "PASS" if ewt["status"] == gum["status"] == "PASS" else "FAIL", "EWT": ewt, "GUM": gum,
            "cells": len(ewt["cells"]) + len(gum["cells"])}


def _select_caps() -> dict[str, Any]:
    evaluations = []
    passing = []
    for relative in RELATIVE_SEARCH:
        for cosine in COSINE_SEARCH:
            result = _score_calibration_union(FIXED_ATOL, relative, cosine)
            evaluations.append({"relative_l2": relative, "cosine_distance": cosine, "status": result["status"]})
            if result["status"] == "PASS":
                passing.append((relative, cosine))
    if not passing:
        raise RuntimeError("no calibration cap pair passes")
    selected = passing[0]
    minima = [p for p in passing if not any(q != p and q[0] <= p[0] and q[1] <= p[1] for q in passing)]
    caps = {"atol": FIXED_ATOL, "relative_l2": selected[0], "cosine_distance": selected[1]}
    if caps != SELECTED_CAPS or minima != [(2e-5, 5e-11)]:
        raise RuntimeError(f"mechanical cap selection differs from freeze: caps={caps}, minima={minima}")
    selected_score = _score_calibration_union(**{"atol": FIXED_ATOL, "relative": selected[0], "cosine": selected[1]})
    return {"caps": caps, "search_order": {"relative_l2_outer": list(RELATIVE_SEARCH), "cosine_inner": list(COSINE_SEARCH)},
            "evaluations": evaluations, "passing_pairs": [list(x) for x in passing], "coordinatewise_minima": [list(x) for x in minima],
            "selected_union_score": selected_score}


def retire_attempt9(signing_key: Path, review: Path) -> dict[str, Any]:
    _verify_attempt9_terminal()
    if RUN_ROOT.exists() or ATTEMPT9_RETIREMENT.exists():
        raise RuntimeError("Attempt-9 retirement must be first signed Attempt-10 artifact")
    candidate = _verify_implementation_candidate()
    review_spec = _review_ship(review, IMPLEMENTATION_CANDIDATE)
    payload = {"schema_version": "atlas_rope_v6_attempt10_attempt9_retirement_v1", "status": "ATTEMPT9_RETIRED_NO_RETRY",
               "attempt9_terminal_sha256": sha256_file(ATTEMPT9_TERMINAL), "attempt9_tree_inventory": recursive_inventory(ATTEMPT9_ROOT),
               "attempt9_expected_absent_paths": [str(path.relative_to(ROOT)) for path in ATTEMPT9_EXPECTED_ABSENCES],
               "attempt9_present_forbidden_paths": _attempt9_required_absences(), "unlogged_invocation_excluded": False,
               "implementation_candidate_sha256": sha256_file(IMPLEMENTATION_CANDIDATE), "implementation_review": review_spec,
               "neural_training_authorized": False}
    write_signed(ATTEMPT9_RETIREMENT, payload, signing_key.resolve(strict=True))
    return verify_envelope(read_json(ATTEMPT9_RETIREMENT))


def verify_attempt9_retirement() -> dict[str, Any]:
    observed = verify_envelope(read_json(ATTEMPT9_RETIREMENT))
    _verify_attempt9_terminal()
    if observed.get("status") != "ATTEMPT9_RETIRED_NO_RETRY" or observed.get("attempt9_tree_inventory") != recursive_inventory(ATTEMPT9_ROOT):
        raise RuntimeError("Attempt-9 retirement drift")
    _verify_implementation_candidate()
    return observed


def import_calibration(signing_key: Path) -> dict[str, Any]:
    _assert_not_terminal(); retirement = verify_attempt9_retirement()
    if CALIBRATION_IMPORT.exists():
        raise RuntimeError("calibration import is create-once")
    er, ec, _, el = _verify_ewt_history(); gr, gc, _, gl = _verify_gum_history()
    payload = {"schema_version": "atlas_rope_v6_attempt10_opened_calibration_import_v1", "status": "VERIFIED_OPENED_CALIBRATION_HISTORY",
               "sources": {"EWT_attempt8": {"reference_shape": list(er.shape), "candidate_shape": list(ec.shape), "lineage": el},
                           "GUM_attempt9": {"reference_shape": list(gr.shape), "candidate_shape": list(gc.shape), "lineage": gl}},
               "grid_cells": 60, "new_ewt_or_gum_forward": False, "calibration_only": True,
               "attempt9_retirement_sha256": sha256_file(ATTEMPT9_RETIREMENT), "neural_training_authorized": False}
    write_signed(CALIBRATION_IMPORT, payload, signing_key.resolve(strict=True))
    return verify_envelope(read_json(CALIBRATION_IMPORT))


def verify_calibration_import() -> dict[str, Any]:
    payload = verify_envelope(read_json(CALIBRATION_IMPORT)); verify_attempt9_retirement()
    if payload.get("grid_cells") != 60 or payload.get("new_ewt_or_gum_forward") is not False:
        raise RuntimeError("calibration import drift")
    _verify_ewt_history(); _verify_gum_history()
    return payload


def make_calibration_cap_candidate(signing_key: Path) -> dict[str, Any]:
    _assert_not_terminal(); verify_calibration_import()
    if CALIBRATION_CAP_CANDIDATE.exists() or GENTLE_GRID.exists():
        raise RuntimeError("cap candidate is create-once and precedes GENTLE")
    selection = _select_caps()
    families = _attempt7_family_scores(selection["caps"])
    payload = {"schema_version": "atlas_rope_v6_attempt10_budget_aligned_caps_v1", "status": "CALIBRATION_SELECTED_VALIDATION_PREREGISTERED",
               **selection, "attempt7_strict_family_scores": families, "calibration_import_sha256": sha256_file(CALIBRATION_IMPORT),
               "fixed_rtol": FIXED_RTOL, "coordinate_budgets": {"failing_elements_per_cell": 30, "failing_rows_per_cell": 2,
                                                                    "relative_l2_failures": 0, "cosine_failures": 0},
               "GENTLE_values_used": False, "neural_training_authorized": False}
    write_signed(CALIBRATION_CAP_CANDIDATE, payload, signing_key.resolve(strict=True))
    return verify_envelope(read_json(CALIBRATION_CAP_CANDIDATE))


def verify_calibration_cap_candidate() -> dict[str, Any]:
    payload = verify_envelope(read_json(CALIBRATION_CAP_CANDIDATE)); verify_calibration_import()
    selection = _select_caps()
    if payload.get("caps") != selection["caps"] or payload.get("selected_union_score") != selection["selected_union_score"]:
        raise RuntimeError("calibration cap candidate drift")
    _attempt7_family_scores(payload["caps"])
    return payload


def make_freeze_candidate() -> dict[str, Any]:
    _assert_not_terminal(); candidate = _verify_implementation_candidate(); caps = verify_calibration_cap_candidate()
    if FREEZE_CANDIDATE.exists() or GENTLE_GRID.exists() or GENTLE_PASS.exists():
        raise RuntimeError("freeze candidate must be create-once before GENTLE")
    gentle_root = DATA_ROOT / "GENTLE_validation"
    required_absences = [GENTLE_GRID, GENTLE_PASS, SCIENCE_AUTHORIZATION, RUN_ROOT / "science", ROOT / "results/atlas_rope_v6_attempt10_science"]
    present = [str(p.relative_to(ROOT)) for p in required_absences if p.exists()]
    if present:
        raise RuntimeError(f"held-out/downstream paths already exist: {present}")
    payload = {"schema_version": "atlas_rope_v6_attempt10_validation_freeze_v1", "status": "READY_FOR_ADVERSARIAL_REVIEW",
               "caps": caps["caps"], "fixed_rtol": FIXED_RTOL, "implementation_candidate_sha256": sha256_file(IMPLEMENTATION_CANDIDATE),
               "calibration_cap_candidate_sha256": sha256_file(CALIBRATION_CAP_CANDIDATE),
               "implementation_hotfix_sha256": sha256_file(IMPLEMENTATION_HOTFIX),
               "science_adapter": candidate["implementation_inventory"]["configs/atlas_rope_v6/science_adapter.json"],
               "gentle_panel": {"path": str((gentle_root / 'panel.json').relative_to(ROOT)), "sha256": sha256_file(gentle_root / "panel.json"),
                                  "selected_document_union": read_json(gentle_root / "panel.json")["selection_support"]["selected_panel_union_documents"]},
               "gentle_operationally_unopened": True, "unlogged_invocation_excluded": False,
               "required_outputs_absent": True, "validation_order": ["GENTLE_validation"],
               "science_result_claim_class": "EXPLORATORY_GUM_TECHNICAL_CALIBRATION_DUAL_ROLE",
               "neural_training_authorized": False}
    atomic_json(FREEZE_CANDIDATE, payload)
    return payload


def authorize_validation(signing_key: Path, review: Path) -> dict[str, Any]:
    _assert_not_terminal(); _verify_implementation_candidate(); verify_calibration_cap_candidate()
    freeze = read_json(FREEZE_CANDIDATE); review_spec = _review_ship(review, FREEZE_CANDIDATE)
    if freeze.get("status") != "READY_FOR_ADVERSARIAL_REVIEW" or GENTLE_GRID.exists():
        raise RuntimeError("validation freeze state drift")
    if VALIDATION_AUTHORIZATION.exists():
        raise RuntimeError("validation authorization is create-once")
    payload = {"schema_version": AUTH_SCHEMA, "status": "AUTHORIZED", "authorized_stage": "GENTLE_ONLY_VALIDATION_ONCE",
               "freeze_candidate_sha256": sha256_file(FREEZE_CANDIDATE), "caps": freeze["caps"], "review": review_spec,
               "EWT_model_calls_authorized": False, "GUM_model_calls_authorized": False, "GENTLE_model_calls_authorized_once": True,
               "science_model_calls_authorized": False, "threshold_change_authorized": False, "neural_training_authorized": False}
    write_signed(VALIDATION_AUTHORIZATION, payload, signing_key.resolve(strict=True))
    return _verify_authorization(VALIDATION_AUTHORIZATION, "GENTLE_ONLY_VALIDATION_ONCE")


def _verify_authorization(path: Path, stage: str) -> dict[str, Any]:
    payload = verify_envelope(read_json(path))
    if payload.get("schema_version") != AUTH_SCHEMA or payload.get("status") != "AUTHORIZED" or payload.get("authorized_stage") != stage:
        raise RuntimeError("authorization identity drift")
    if payload.get("neural_training_authorized") is not False:
        raise RuntimeError("training authorization forbidden")
    return payload


def _load_gentle_panel() -> tuple[dict[str, Any], list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    return attempt9_code._load_panel("GENTLE_validation")


def _write_npy(path: Path, value: np.ndarray) -> None:
    np.save(path, np.ascontiguousarray(value, dtype=np.float32), allow_pickle=False)
    with path.open("rb") as handle:
        os.fsync(handle.fileno())


def _extract_gentle(signing_key: Path) -> dict[str, Any]:
    auth = _verify_authorization(VALIDATION_AUTHORIZATION, "GENTLE_ONLY_VALIDATION_ONCE")
    config = read_json(CONFIG_PATH); panel, references, candidates, rows = _load_gentle_panel(); caps = auth["caps"]
    if GENTLE_GRID.exists():
        raise RuntimeError("GENTLE output already exists; one-shot validation cannot resume or retry")
    device = torch.device("cuda:0")
    with exclusive_lock("attempt-wide-gpu"):
        attempt9_code._seed_runtime(int(config["seed"])); model = attempt9_code._load_model(config, device)
        runtime_preflight = attempt9_code._runtime_attestation(model, device, config); started = time.time()
        repeats = [attempt9_code._forward_units(model, references, device=device, hidden_index=4, batch_size=64) for _ in range(3)]
        candidate = attempt9_code._forward_units(model, candidates, device=device, hidden_index=4, batch_size=64)
        runtime_postflight = attempt9_code._runtime_attestation(model, device, config)
    if any(x.shape != (200, WIDTH) for x in repeats) or candidate.shape != (1200, WIDTH):
        raise RuntimeError("GENTLE output shape drift")
    if any(not np.array_equal(repeats[0], x) or repeats[0].tobytes() != x.tobytes() for x in repeats[1:]):
        raise RuntimeError("GENTLE repeated live inference differs")
    stage = new_staging("validation-GENTLE", sha256_file(VALIDATION_AUTHORIZATION))
    for name, value in (("reference", repeats[0]), ("reference_repeat_1", repeats[1]), ("reference_repeat_2", repeats[2]), ("candidate", candidate)):
        _write_npy(stage / f"{name}.float32.npy", value)
    cached = np.load(stage / "reference.float32.npy", allow_pickle=False); _write_npy(stage / "reference_cached_replay.float32.npy", cached)
    ids = {"reference": [str(row["row_id"]) for row in rows],
           "candidate": [str(row_id) for unit in candidates for row_id in unit["row_ids"]]}
    atomic_json(stage / "row_ids.json", ids)
    replay = exact_cached_replay(repeats[0], np.load(stage / "reference_cached_replay.float32.npy", allow_pickle=False), ids["reference"], ids["reference"],
                                 left_child_hash=sha256_file(stage / "reference.float32.npy"), right_child_hash=sha256_file(stage / "reference_cached_replay.float32.npy"))
    score = score_grid(repeats[0], candidate, rows, atol=float(caps["atol"]), relative_l2_cap=float(caps["relative_l2"]), cosine_cap=float(caps["cosine_distance"]))
    artifacts = {p.name: {"bytes": p.stat().st_size, "sha256": sha256_file(p)} for p in stage.iterdir() if p.is_file()}
    overall_status = "PASS" if score["status"] == "PASS" and replay["status"] == "PASS" else "FAIL"
    payload = {"schema_version": BUNDLE_SCHEMA, "status": overall_status, "source": "GENTLE_validation", "bundle_kind": "minimal_grid",
               "score": score, "caps": caps, "exact_cached_replay": replay, "live_reference_repeats_byte_identical": True,
               "reference_array_sha256": canonical_array_hash(repeats[0]), "candidate_array_sha256": canonical_array_hash(candidate),
               "panel_sha256": sha256_file(DATA_ROOT / "GENTLE_validation/panel.json"), "logical_counts": panel["logical_counts"],
               "authorization_sha256": sha256_file(VALIDATION_AUTHORIZATION), "runtime_preflight": runtime_preflight, "runtime_postflight": runtime_postflight,
               "model": config["model"], "hidden_state_index": 4, "batch_size": 64, "hidden_state_dtype": "float32",
               "parameter_dtype": "float32", "cache_dtype": "float32",
               "elapsed_seconds": time.time() - started, "model_eval": True, "inference_mode": True, "requires_grad": False,
               "labels_loaded": False, "estimator_created": False, "parameter_update_run": False, "checkpoint_created": False,
               "neural_training_run": False, "artifacts": artifacts}
    write_signed(stage / "COMPLETE.json", payload, signing_key.resolve(strict=True)); promote(stage, GENTLE_GRID)
    return verify_gentle_bundle(require_pass=False)


def verify_gentle_bundle(*, require_pass: bool = True) -> dict[str, Any]:
    auth = _verify_authorization(VALIDATION_AUTHORIZATION, "GENTLE_ONLY_VALIDATION_ONCE")
    reference, candidate, rows, _ = _load_grid_history(GENTLE_GRID, "GENTLE", "GENTLE_validation")
    payload = verify_envelope(read_json(GENTLE_GRID / "COMPLETE.json"))
    score = score_grid(reference, candidate, rows, atol=float(auth["caps"]["atol"]), relative_l2_cap=float(auth["caps"]["relative_l2"]), cosine_cap=float(auth["caps"]["cosine_distance"]))
    replay = payload.get("exact_cached_replay", {})
    expected_status = "PASS" if score["status"] == "PASS" and replay.get("status") == "PASS" else "FAIL"
    config = read_json(CONFIG_PATH)
    if (payload.get("score") != score or payload.get("status") != expected_status or
            replay.get("status") != "PASS" or payload.get("caps") != auth["caps"] or
            payload.get("model") != config["model"] or payload.get("hidden_state_index") != 4 or
            payload.get("batch_size") != 64 or payload.get("hidden_state_dtype") != "float32" or
            payload.get("parameter_dtype") != "float32" or payload.get("cache_dtype") != "float32"):
        raise RuntimeError("GENTLE score drift")
    if require_pass and expected_status != "PASS":
        raise RuntimeError("GENTLE bundle is a valid recorded failure, not a PASS")
    return payload


def run_gentle(signing_key: Path) -> dict[str, Any]:
    _assert_not_terminal(); signing_key = signing_key.resolve(strict=True)
    try:
        _verify_implementation_candidate(); verify_calibration_cap_candidate()
        payload = _extract_gentle(signing_key)
        if payload["status"] != "PASS":
            raise RuntimeError("GENTLE grid failed frozen caps")
        pass_payload = {"schema_version": "atlas_rope_v6_attempt10_source_validation_v1", "status": "PASS", "source": "GENTLE",
                        "grid_complete_sha256": sha256_file(GENTLE_GRID / "COMPLETE.json"), "validation_authorization_sha256": sha256_file(VALIDATION_AUTHORIZATION),
                        "caps": SELECTED_CAPS, "science_model_calls_authorized_next": True, "neural_training_authorized": False}
        write_signed(GENTLE_PASS, pass_payload, signing_key); return verify_envelope(read_json(GENTLE_PASS))
    except Exception as error:
        _terminalize(signing_key, status="TERMINAL_GENTLE_VALIDATION_FAILED", reason=f"GENTLE validation failed: {type(error).__name__}: {error}")
        raise


def authorize_science(signing_key: Path) -> dict[str, Any]:
    _assert_not_terminal(); gentle = verify_envelope(read_json(GENTLE_PASS)); candidate = _verify_implementation_candidate()
    if gentle.get("status") != "PASS" or verify_gentle_bundle().get("status") != "PASS":
        raise RuntimeError("GENTLE did not pass")
    if SCIENCE_AUTHORIZATION.exists():
        raise RuntimeError("science authorization is create-once")
    payload = {"schema_version": AUTH_SCHEMA, "status": "AUTHORIZED", "authorized_stage": "EXPLORATORY_FROZEN_SCIENTIFIC_ATLAS",
               "gentle_pass_sha256": sha256_file(GENTLE_PASS), "validation_authorization_sha256": sha256_file(VALIDATION_AUTHORIZATION),
               "implementation_candidate_sha256": sha256_file(IMPLEMENTATION_CANDIDATE),
               "science_adapter_sha256": candidate["implementation_inventory"]["configs/atlas_rope_v6/science_adapter.json"]["sha256"],
               "calibration_cap_candidate_sha256": sha256_file(CALIBRATION_CAP_CANDIDATE),
               "claim_class": "EXPLORATORY_GUM_TECHNICAL_CALIBRATION_DUAL_ROLE", "scientific_protocol_changes_authorized": False,
               "neural_training_authorized": False}
    write_signed(SCIENCE_AUTHORIZATION, payload, signing_key.resolve(strict=True))
    return _verify_authorization(SCIENCE_AUTHORIZATION, "EXPLORATORY_FROZEN_SCIENTIFIC_ATLAS")


def main() -> None:
    parser = argparse.ArgumentParser(); parser.add_argument("stage", choices=("make-implementation-candidate", "retire-attempt9", "import-calibration", "make-calibration-cap-candidate", "make-freeze-candidate", "authorize-validation", "run-gentle", "authorize-science", "terminalize-failure"))
    parser.add_argument("--signing-key", type=Path); parser.add_argument("--review", type=Path); parser.add_argument("--verification-report", type=Path)
    parser.add_argument("--terminal-status"); parser.add_argument("--reason")
    args = parser.parse_args()
    if args.stage == "make-implementation-candidate":
        if not args.verification_report: raise RuntimeError("verification report required")
        result = make_implementation_candidate(args.verification_report)
    elif args.stage == "retire-attempt9":
        if not args.signing_key or not args.review: raise RuntimeError("signing key and review required")
        result = retire_attempt9(args.signing_key, args.review)
    elif args.stage == "import-calibration":
        if not args.signing_key: raise RuntimeError("signing key required")
        result = import_calibration(args.signing_key)
    elif args.stage == "make-calibration-cap-candidate":
        if not args.signing_key: raise RuntimeError("signing key required")
        result = make_calibration_cap_candidate(args.signing_key)
    elif args.stage == "make-freeze-candidate": result = make_freeze_candidate()
    elif args.stage == "authorize-validation":
        if not args.signing_key or not args.review: raise RuntimeError("signing key and review required")
        result = authorize_validation(args.signing_key, args.review)
    elif args.stage == "run-gentle":
        if not args.signing_key: raise RuntimeError("signing key required")
        result = run_gentle(args.signing_key)
    elif args.stage == "authorize-science":
        if not args.signing_key: raise RuntimeError("signing key required")
        result = authorize_science(args.signing_key)
    else:
        if not args.signing_key or not args.terminal_status or not args.reason: raise RuntimeError("terminalization requires signing key, status, and reason")
        _terminalize(args.signing_key, status=args.terminal_status, reason=args.reason)
        result = verify_envelope(read_json(TERMINAL_PATH))
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
