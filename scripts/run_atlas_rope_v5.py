#!/usr/bin/env python3
"""Score-bearing Atlas v3.5 attempt-9 technical runner and stage controller.

The technical path performs frozen-model inference only. It never loads labels,
fits an estimator, updates parameters, or emits a neural checkpoint.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
os.environ.setdefault("CUBLAS_WORKSPACE_CONFIG", ":4096:8")
import platform
import random
import sys
import time
from pathlib import Path
from typing import Any, Mapping, Sequence

import numpy as np
import torch
from transformers import AutoModelForCausalLM

sys.path.insert(0, str(Path(__file__).resolve().parent))

from atlas_rope_v5 import (
    ATTEMPT8_RETIREMENT_SCHEMA,
    ATOL_GRID,
    AUTH_SCHEMA,
    BATCH_SIZE,
    BUNDLE_SCHEMA,
    COSINE_GRID,
    FREEZE_SCHEMA,
    LENGTH_BINS,
    OLD_ATOL_GRID,
    REL_L2_GRID,
    ROOT,
    RTOL,
    RUN_ROOT,
    SAFETY_FACTOR,
    SHIFTS,
    WIDTH,
    assert_output_allowlist,
    atomic_json,
    batch_schedule,
    canonical_array_hash,
    canonical_json_bytes,
    child_spec,
    choose_grid_cap,
    derive_caps,
    exact_cached_replay,
    exclusive_lock,
    inventory_digest,
    loaded_library_attestation,
    new_staging,
    promote,
    read_json,
    read_jsonl,
    recursive_inventory,
    row_error_metrics,
    score_cell,
    score_grid,
    sha256_bytes,
    sha256_file,
    sign_terminal,
    static_no_training_scan,
    validate_grid_units,
    validate_repo_relative,
    verify_attempt7_retirement,
    verify_envelope,
    verify_library_attestation,
    write_signed,
)
from probe_atlas_rope_v5_runtime import _source_hashes
from extract_atlas_discovery_v3_3 import (
    _load_source_bundle as _attempt7_load_source_bundle,
    _qa_panel_units as _attempt7_qa_panel_units,
    _recompute_qa_evidence as _attempt7_recompute_qa_evidence,
)


CONFIG_PATH = ROOT / "configs/atlas_rope_v5/prescore.json"
DATA_ROOT = ROOT / "data/atlas_rope_v5_attempt9"
REBUILD_REPORT = ROOT / "reports/atlas_rope_v5/prescore_rebuild_check.json"
RUNTIME_PROBE = ROOT / "data/atlas_rope_v5_attempt9_runtime_probe.json"
ATTEMPT7_RETIREMENT = ROOT / "pilot_runs/20260803_atlas_rope_technical_v4/provenance/ATTEMPT7_RETIRED.json"
ATTEMPT8_RETIREMENT = RUN_ROOT / "provenance/ATTEMPT8_RETIRED.json"
CALIBRATION_IMPORT = RUN_ROOT / "calibration_history/ATTEMPT8_EWT_IMPORT.json"
CALIBRATION_CAP_CANDIDATE = ROOT / "configs/atlas_rope_v5/CALIBRATION_CAP_CANDIDATE.json"
EWT_AUTHORIZATION = ROOT / "configs/atlas_rope_v5/EWT_DIAGNOSTIC_AUTHORIZATION.json"
FREEZE_CANDIDATE = ROOT / "configs/atlas_rope_v5/validation_freeze_candidate.json"
VALIDATION_AUTHORIZATION = ROOT / "configs/atlas_rope_v5/VALIDATION_AUTHORIZATION.json"
SCIENCE_AUTHORIZATION = ROOT / "configs/atlas_rope_v5/SCIENCE_AUTHORIZATION.json"
IMPLEMENTATION_CANDIDATE = ROOT / "configs/atlas_rope_v5/implementation_candidate.json"
GPU_UUID = "GPU-ec526219-fb07-e57e-a30d-5d2ab843fb15"
TERMINAL_PATH = RUN_ROOT / "TERMINAL.json"
ATTEMPT8_ROOT = ROOT / "pilot_runs/20260803_atlas_rope_technical_v4"
ATTEMPT8_DATA_ROOT = ROOT / "data/atlas_rope_v4_attempt8"
ATTEMPT8_CONFIG_ROOT = ROOT / "configs/atlas_rope_v4"
ATTEMPT8_STAGING = ATTEMPT8_ROOT / "staging/minimal-EWT_calibration-67f720a9b43d-2654766"
CONTROLLER_STAGE_ORDER = (
    "build_unsigned_prescore", "implementation_review_ship", "retire_attempt8",
    "import_opened_ewt_calibration", "freeze_calibration_caps", "authorize_ewt_diagnostic",
    "run_ewt_diagnostic", "freeze_validation", "freeze_review_ship",
    "run_gum_sentinel_and_grid", "run_gentle", "authorize_science",
    "run_frozen_unchanged_science", "claim_review",
)


def _assert_not_terminal() -> None:
    if (RUN_ROOT / "SIGNING_FAULT.json").exists():
        raise RuntimeError("attempt 9 has a terminal signing fault and cannot continue")
    if TERMINAL_PATH.exists():
        payload = verify_envelope(read_json(TERMINAL_PATH))
        raise RuntimeError(f"attempt 9 is terminal and cannot continue: {payload.get('status')}")


def _existing_lineage() -> dict[str, Any]:
    paths = {
        "ewt_authorization": EWT_AUTHORIZATION,
        "ewt_complete": RUN_ROOT / "calibration/EWT_minimal/COMPLETE.json",
        "diagnostic_complete": RUN_ROOT / "diagnostic/DIAGNOSTIC_COMPLETE.json",
        "freeze_candidate": FREEZE_CANDIDATE,
        "validation_authorization": VALIDATION_AUTHORIZATION,
        "gum_sentinel_complete": RUN_ROOT / "validation/GUM_sentinel/COMPLETE.json",
        "gum_grid_complete": RUN_ROOT / "validation/GUM_grid/COMPLETE.json",
        "gum_pass": RUN_ROOT / "validation/GUM_PASS.json",
        "gentle_grid_complete": RUN_ROOT / "validation/GENTLE_grid/COMPLETE.json",
        "gentle_pass": RUN_ROOT / "validation/GENTLE_PASS.json",
    }
    return {name: {"path": str(path.relative_to(ROOT)), "sha256": sha256_file(path)}
            for name, path in paths.items() if path.is_file()}


def _attempt8_required_absences() -> tuple[Path, ...]:
    return (
        ATTEMPT8_ROOT / "calibration",
        ATTEMPT8_ROOT / "diagnostic",
        ATTEMPT8_ROOT / "validation",
        ATTEMPT8_ROOT / "science",
        ATTEMPT8_CONFIG_ROOT / "validation_freeze_candidate.json",
        ATTEMPT8_CONFIG_ROOT / "VALIDATION_AUTHORIZATION.json",
        ATTEMPT8_CONFIG_ROOT / "SCIENCE_AUTHORIZATION.json",
    )


def _attempt8_external_bindings() -> dict[str, Path]:
    candidate_path = ATTEMPT8_CONFIG_ROOT / "implementation_candidate.json"
    candidate = read_json(candidate_path)
    paths = {f"candidate_inventory:{name}": ROOT / name for name in candidate["implementation_inventory"]}
    paths.update({
        "implementation_candidate": candidate_path,
        "ewt_authorization": ATTEMPT8_CONFIG_ROOT / "EWT_AUTHORIZATION.json",
        "prescore_manifest": ATTEMPT8_DATA_ROOT / "manifest.json",
        "prescore_rebuild": ROOT / "reports/atlas_rope_v4/prescore_rebuild_check.json",
        "runtime_probe": ROOT / "data/atlas_rope_v4_attempt8_runtime_probe.json",
        "implementation_verification": ROOT / "reports/atlas_rope_v4/implementation_verification.json",
        "implementation_review": ROOT / "reports/adversarial/atlas_v3_4_attempt8_implementation_review.md",
        "post_failure_review": ROOT / "reports/adversarial/atlas_v3_4_attempt8_post_failure_review.md",
        "source_provenance": ROOT / "data/atlas_rope_v4_raw/PROVENANCE.json",
        "attempt7_retirement": ATTEMPT7_RETIREMENT,
    })
    return paths


def _old_grid_caps(reference: np.ndarray, candidate: np.ndarray) -> dict[str, Any]:
    metrics = row_error_metrics(reference, candidate)
    if not metrics.finite_rows.all():
        return {"status": "INELIGIBLE", "reason": "nonfinite_calibration"}
    maxima = {
        "required_atol": float(metrics.required_atol.max(initial=0.0)),
        "relative_l2": float(metrics.relative_l2.max(initial=0.0)),
        "cosine_distance": float(metrics.cosine_distance.max(initial=0.0)),
    }
    caps = {
        "atol": choose_grid_cap(maxima["required_atol"], OLD_ATOL_GRID),
        "relative_l2": choose_grid_cap(maxima["relative_l2"], REL_L2_GRID),
        "cosine_distance": choose_grid_cap(maxima["cosine_distance"], COSINE_GRID),
    }
    return {
        "status": "PASS" if all(value is not None for value in caps.values()) else "INELIGIBLE",
        "rtol": RTOL,
        "safety_factor": SAFETY_FACTOR,
        "observed_maxima": maxima,
        "caps": caps,
        "calibration_rows": int(reference.shape[0]),
        "grids": {"atol": list(OLD_ATOL_GRID), "relative_l2": list(REL_L2_GRID),
                  "cosine_distance": list(COSINE_GRID)},
    }


def _verify_attempt8_history() -> tuple[np.ndarray, np.ndarray, dict[str, Any]]:
    terminal_path = ATTEMPT8_ROOT / "TERMINAL.json"
    terminal = verify_envelope(read_json(terminal_path))
    if (terminal.get("schema_version") != "atlas_rope_v4_attempt8_terminal_v1" or
            terminal.get("status") != "TERMINAL_EWT_CALIBRATION_INVALID" or
            terminal.get("no_retry_authorized") is not True or
            "signed artifact did not verify after write" not in str(terminal.get("reason"))):
        raise RuntimeError("attempt-8 terminal identity drift")
    present = [str(path.relative_to(ROOT)) for path in _attempt8_required_absences() if path.exists()]
    if present:
        raise RuntimeError(f"attempt-8 forbidden promoted/downstream outputs exist: {present}")
    if not ATTEMPT8_STAGING.is_dir() or set(path.name for path in ATTEMPT8_STAGING.iterdir()) != {
        "reference.float32.npy", "reference_repeat_1.float32.npy", "reference_repeat_2.float32.npy",
        "reference_cached_replay.float32.npy", "candidate.float32.npy", "row_ids.json", "COMPLETE.json",
    }:
        raise RuntimeError("attempt-8 EWT staging inventory drift")
    complete_path = ATTEMPT8_STAGING / "COMPLETE.json"
    complete = verify_envelope(read_json(complete_path))
    if (complete.get("schema_version") != "atlas_rope_v4_attempt8_technical_bundle_v1" or
            complete.get("bundle_kind") != "minimal_grid" or complete.get("source") != "EWT_calibration" or
            complete.get("status") != "COMPLETE" or complete.get("score", {}).get("status") != "CALIBRATION_ONLY"):
        raise RuntimeError("attempt-8 staging completion identity drift")
    artifact_names = set(complete.get("artifacts", {}))
    expected_artifacts = {"reference.float32.npy", "reference_repeat_1.float32.npy",
                          "reference_repeat_2.float32.npy", "reference_cached_replay.float32.npy",
                          "candidate.float32.npy", "row_ids.json"}
    if artifact_names != expected_artifacts:
        raise RuntimeError("attempt-8 staging artifact inventory drift")
    for name, spec in complete["artifacts"].items():
        path = ATTEMPT8_STAGING / name
        if path.stat().st_size != int(spec["bytes"]) or sha256_file(path) != spec["sha256"]:
            raise RuntimeError(f"attempt-8 staging child drift: {name}")
    arrays = {name: np.load(ATTEMPT8_STAGING / f"{name}.float32.npy", allow_pickle=False)
              for name in ("reference", "reference_repeat_1", "reference_repeat_2",
                           "reference_cached_replay", "candidate")}
    if (any(value.dtype != np.float32 or not value.flags.c_contiguous or not np.isfinite(value).all()
            for value in arrays.values()) or arrays["reference"].shape != (200, WIDTH) or
            arrays["candidate"].shape != (1200, WIDTH) or
            any(arrays[name].shape != (200, WIDTH) for name in
                ("reference_repeat_1", "reference_repeat_2", "reference_cached_replay"))):
        raise RuntimeError("attempt-8 staging array structure drift")
    if any(not np.array_equal(arrays["reference"], arrays[name]) or
           arrays["reference"].tobytes(order="C") != arrays[name].tobytes(order="C")
           for name in ("reference_repeat_1", "reference_repeat_2", "reference_cached_replay")):
        raise RuntimeError("attempt-8 exact replay/live repeat drift")
    rows = read_jsonl(ATTEMPT8_DATA_ROOT / "EWT_calibration/rows.jsonl")
    candidates = read_jsonl(ATTEMPT8_DATA_ROOT / "EWT_calibration/candidates.jsonl")
    row_ids = read_json(ATTEMPT8_STAGING / "row_ids.json")
    expected_reference_ids = [str(row["row_id"]) for row in rows]
    expected_candidate_ids = [str(row_id) for unit in candidates for row_id in unit["row_ids"]]
    if row_ids != {"reference": expected_reference_ids, "candidate": expected_candidate_ids}:
        raise RuntimeError("attempt-8 staging row order/lineage drift")
    expanded = _expanded_grid_reference(arrays["reference"])
    old_raw = _old_grid_caps(expanded, arrays["candidate"])
    if complete.get("score", {}).get("raw_cap_inputs") != old_raw or old_raw.get("status") != "INELIGIBLE":
        raise RuntimeError("attempt-8 calibration metrics did not independently recompute")
    if old_raw["observed_maxima"]["required_atol"] != 1.3512020111083984e-05:
        raise RuntimeError("attempt-8 disclosed required-atol maximum drift")
    authorization = ATTEMPT8_CONFIG_ROOT / "EWT_AUTHORIZATION.json"
    if (complete.get("authorization", {}).get("sha256") != sha256_file(authorization) or
            terminal.get("lineage", {}).get("ewt_authorization", {}).get("sha256") != sha256_file(authorization)):
        raise RuntimeError("attempt-8 authorization lineage drift")
    lineage = {
        "terminal_sha256": sha256_file(terminal_path),
        "staging_complete_sha256": sha256_file(complete_path),
        "staging_tree_inventory": recursive_inventory(ATTEMPT8_STAGING),
        "old_raw_cap_inputs": old_raw,
        "reference_canonical_sha256": canonical_array_hash(arrays["reference"]),
        "candidate_canonical_sha256": canonical_array_hash(arrays["candidate"]),
        "status": "VERIFIED_OPENED_CALIBRATION_HISTORY",
    }
    lineage["staging_tree_inventory_sha256"] = inventory_digest(lineage["staging_tree_inventory"])
    return arrays["reference"], arrays["candidate"], lineage


def _terminalize(signing_key: Path, *, status: str, reason: str, extra: Mapping[str, Any] | None = None) -> None:
    if TERMINAL_PATH.exists():
        verify_envelope(read_json(TERMINAL_PATH))
        return
    lineage = _existing_lineage()
    if extra:
        lineage.update(dict(extra))
    sign_terminal(signing_key.resolve(strict=True), status=status, reason=reason[:2000], lineage=lineage)


def _verify_live_source_contract(config: Mapping[str, Any]) -> dict[str, Any]:
    transformers_version, source_hashes = _source_hashes()
    expected = config["runtime"]
    if transformers_version != expected["transformers"] or source_hashes != expected["source_hashes"]:
        raise RuntimeError("live Transformers source/version drift")
    return {"transformers": transformers_version, "source_hashes": source_hashes}


def _gpu_uuid(device: torch.device) -> str:
    index = device.index if device.index is not None else torch.cuda.current_device()
    value = str(torch.cuda.get_device_properties(index).uuid)
    return value if value.startswith("GPU-") else f"GPU-{value}"


def _seed_runtime(seed: int) -> None:
    if os.environ.get("CUBLAS_WORKSPACE_CONFIG") != ":4096:8":
        raise RuntimeError("CUBLAS_WORKSPACE_CONFIG drift before CUDA initialization")
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    torch.cuda.manual_seed_all(seed)
    torch.use_deterministic_algorithms(True)
    torch.backends.cuda.matmul.allow_tf32 = False
    torch.backends.cudnn.allow_tf32 = False
    if torch.is_autocast_enabled() or torch.is_autocast_enabled("cuda"):
        raise RuntimeError("autocast must be disabled")


def _verify_prescore() -> tuple[dict[str, Any], dict[str, Any]]:
    config = read_json(CONFIG_PATH)
    if config.get("schema_version") != "atlas_rope_v5_attempt9_prescore_v1":
        raise RuntimeError("unknown attempt-9 prescore schema")
    if config.get("neural_training_authorized") is not False or config.get("model_calls_authorized") is not False:
        raise RuntimeError("base prescore config permission drift")
    if tuple(config.get("stage_order", ())) != CONTROLLER_STAGE_ORDER:
        raise RuntimeError("configured stage order differs from the executable controller")
    verify_attempt7_retirement(ATTEMPT7_RETIREMENT)
    manifest_path = DATA_ROOT / "manifest.json"
    manifest = read_json(manifest_path)
    if manifest.get("status") != "PASS_NO_MODEL_CALLS" or manifest.get("config", {}).get("sha256") != sha256_file(CONFIG_PATH):
        raise RuntimeError("prescore manifest config/status drift")
    if manifest.get("model_weights_loaded") is not False or manifest.get("neural_inference_run") is not False:
        raise RuntimeError("prescore crossed the no-inference boundary")
    rebuild = read_json(REBUILD_REPORT)
    if rebuild.get("status") != "PASS" or rebuild.get("mismatched_paths") != []:
        raise RuntimeError("prescore independent rebuild did not pass")
    rebuild_root = ROOT / str(rebuild.get("rebuilt_root", ""))
    primary_root = ROOT / str(rebuild.get("primary_root", ""))
    if primary_root.resolve() != DATA_ROOT.resolve() or not rebuild_root.is_dir():
        raise RuntimeError("prescore rebuild root lineage drift")
    primary_inventory, rebuilt_inventory = recursive_inventory(primary_root), recursive_inventory(rebuild_root)
    primary_digest = sha256_bytes(json.dumps(primary_inventory, sort_keys=True, separators=(",", ":")).encode())
    rebuilt_digest = sha256_bytes(json.dumps(rebuilt_inventory, sort_keys=True, separators=(",", ":")).encode())
    if (primary_inventory != rebuilt_inventory or rebuild.get("primary_inventory_sha256") != primary_digest or
            rebuild.get("rebuilt_inventory_sha256") != rebuilt_digest):
        raise RuntimeError("prescore rebuild inventory drift")
    runtime = read_json(RUNTIME_PROBE)
    if runtime.get("status") != "PASS_NO_WEIGHT_NO_FORWARD" or runtime.get("source_hashes") != config["runtime"]["source_hashes"]:
        raise RuntimeError("runtime probe drift")
    _verify_live_source_contract(config)
    for source, spec in manifest["sources"].items():
        path = DATA_ROOT / str(spec["panel_path"])
        if sha256_file(path) != spec["panel_sha256"]:
            raise RuntimeError(f"panel manifest drift: {source}")
    sentinel = manifest["fresh_gum_sentinel"]
    if sha256_file(DATA_ROOT / sentinel["panel_path"]) != sentinel["panel_sha256"]:
        raise RuntimeError("fresh GUM sentinel panel drift")
    return config, manifest


def _load_panel(source: str) -> tuple[dict[str, Any], list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    panel_root = DATA_ROOT / source
    panel = read_json(panel_root / "panel.json")
    references = read_jsonl(panel_root / "references.jsonl")
    candidates = read_jsonl(panel_root / "candidates.jsonl")
    rows = read_jsonl(panel_root / "rows.jsonl")
    for name, spec in panel["children"].items():
        path = panel_root / name
        if sha256_file(path) != spec["sha256"] or path.stat().st_size != spec["bytes"]:
            raise RuntimeError(f"panel child drift: {source}/{name}")
    validate_grid_units(references, candidates, rows, source=source)
    if panel["schedules"]["reference"] != batch_schedule(references) or panel["schedules"]["candidate"] != batch_schedule(candidates):
        raise RuntimeError("panel batch schedule drift")
    if panel["schedules"]["reference_repeats"] != [batch_schedule(references) for _ in range(3)]:
        raise RuntimeError("panel repeated-reference schedule drift")
    return panel, references, candidates, rows


def _verify_authorization(path: Path, *, stage: str) -> dict[str, Any]:
    payload = verify_envelope(read_json(path))
    if payload.get("schema_version") != AUTH_SCHEMA or payload.get("status") != "AUTHORIZED" or payload.get("authorized_stage") != stage:
        raise RuntimeError(f"invalid stage authorization: {stage}")
    if payload.get("neural_training_authorized") is not False:
        raise RuntimeError("authorization unexpectedly permits neural training")
    if payload.get("prescore_config_sha256") != sha256_file(CONFIG_PATH) or payload.get("prescore_manifest_sha256") != sha256_file(DATA_ROOT / "manifest.json"):
        raise RuntimeError("authorization prescore lineage drift")
    if stage == "EWT_DIAGNOSTIC_ONLY":
        _verify_implementation_candidate()
        verify_attempt8_retirement()
        if (payload.get("implementation_candidate_sha256") != sha256_file(IMPLEMENTATION_CANDIDATE) or
                payload.get("attempt8_retirement_sha256") != sha256_file(ATTEMPT8_RETIREMENT) or
                payload.get("calibration_import_sha256") != sha256_file(CALIBRATION_IMPORT) or
                payload.get("calibration_cap_candidate_sha256") != sha256_file(CALIBRATION_CAP_CANDIDATE)):
            raise RuntimeError("EWT diagnostic authorization lineage drift")
        review = ROOT / str(payload.get("implementation_review", {}).get("path", ""))
        if not review.is_file() or sha256_file(review) != payload.get("implementation_review", {}).get("sha256"):
            raise RuntimeError("EWT authorization implementation-review drift")
    elif stage == "SEQUENTIAL_HELDOUT_VALIDATION":
        implementation = _verify_implementation_candidate()
        if payload.get("freeze_candidate_sha256") != sha256_file(FREEZE_CANDIDATE) or payload.get("freeze_candidate") != read_json(FREEZE_CANDIDATE):
            raise RuntimeError("validation authorization freeze drift")
        if (payload.get("implementation_candidate_sha256") != sha256_file(IMPLEMENTATION_CANDIDATE) or
                payload.get("implementation_inventory") != implementation["implementation_inventory"] or
                payload.get("implementation_verification_report") != implementation["verification_report"] or
                payload.get("ewt_authorization_sha256") != sha256_file(EWT_AUTHORIZATION) or
                payload.get("calibration_cap_candidate_sha256") != sha256_file(CALIBRATION_CAP_CANDIDATE) or
                payload.get("attempt8_retirement_sha256") != sha256_file(ATTEMPT8_RETIREMENT) or
                payload.get("science_adapter") != implementation["science_adapter"]):
            raise RuntimeError("validation authorization implementation/EWT lineage drift")
        _verify_authorization(EWT_AUTHORIZATION, stage="EWT_DIAGNOSTIC_ONLY")
        review = ROOT / str(payload.get("freeze_review", {}).get("path", ""))
        if not review.is_file() or sha256_file(review) != payload.get("freeze_review", {}).get("sha256"):
            raise RuntimeError("validation authorization freeze-review drift")
    elif stage == "UNCHANGED_SCIENTIFIC_ATLAS":
        implementation = _verify_implementation_candidate()
        if (payload.get("validation_authorization_sha256") != sha256_file(VALIDATION_AUTHORIZATION) or
                payload.get("gum_pass_sha256") != sha256_file(RUN_ROOT / "validation/GUM_PASS.json") or
                payload.get("gentle_pass_sha256") != sha256_file(RUN_ROOT / "validation/GENTLE_PASS.json") or
                payload.get("implementation_candidate_sha256") != sha256_file(IMPLEMENTATION_CANDIDATE) or
                payload.get("science_adapter") != implementation["science_adapter"] or
                payload.get("calibration_cap_candidate_sha256") != sha256_file(CALIBRATION_CAP_CANDIDATE)):
            raise RuntimeError("science authorization validation lineage drift")
    return payload


IMPLEMENTATION_PATHS = tuple(ROOT / path for path in (
    "PLAN_ATTEMPT9.md",
    "scripts/atlas_rope_v5.py",
    "scripts/build_atlas_rope_v5.py",
    "scripts/probe_atlas_rope_v5_runtime.py",
    "scripts/run_atlas_rope_v5.py",
    "scripts/diagnose_atlas_rope_v5.py",
    "tests/test_atlas_rope_v5.py",
    "configs/atlas_rope_v5/prescore.json",
    "configs/atlas_rope_v5/science_adapter.json",
    "docs/rfc-atlas-v3-5-attempt9-rope-technical.md",
    "requirements-atlas.lock.txt",
    "reports/adversarial/atlas_v3_5_attempt9_plan_review.md",
    "reports/adversarial/atlas_v3_5_attempt9_implementation_review_block_v1.md",
    "reports/adversarial/atlas_v3_5_attempt9_implementation_review_block_v2.md",
    "scripts/run_atlas_rope_v5_science.py",
    "scripts/extract_atlas_discovery_v3_3.py",
    "scripts/analyze_atlas_discovery_v3_3.py",
    "scripts/atlas_discovery_v3_3_analysis.py",
    "tests/test_atlas_discovery_v3_3_scoring.py",
    "tests/test_atlas_rope_v5_science.py",
))
NO_TRAINING_PATHS = tuple(ROOT / path for path in (
    "scripts/atlas_rope_v5.py", "scripts/build_atlas_rope_v5.py",
    "scripts/probe_atlas_rope_v5_runtime.py", "scripts/run_atlas_rope_v5.py",
    "scripts/diagnose_atlas_rope_v5.py", "scripts/run_atlas_rope_v5_science.py",
    "tests/test_atlas_rope_v5.py", "tests/test_atlas_rope_v5_science.py",
))


def _exact_inventory(paths: Mapping[str, Path]) -> dict[str, dict[str, Any]]:
    return {name: {"bytes": path.stat().st_size, "sha256": sha256_file(path)} for name, path in paths.items()}


def _verify_exact_inventory(paths: Mapping[str, Path], expected: Mapping[str, Any]) -> None:
    if _exact_inventory(paths) != dict(expected):
        raise RuntimeError("implementation candidate inventory drift")


def _verify_report_inventory_hashes(report: Mapping[str, Any], inventory: Mapping[str, Any]) -> None:
    expected = {str(name): str(spec["sha256"]) for name, spec in inventory.items()}
    if report.get("implementation_hashes") != expected:
        raise RuntimeError("implementation verification report does not bind the exact candidate inventory")


def _require_ship_review(review_path: Path, reviewed_artifact: Path) -> Path:
    review = review_path.resolve(strict=True)
    if not review.is_relative_to(ROOT / "reports/adversarial"):
        raise RuntimeError("adversarial review must be retained under reports/adversarial")
    text = review.read_text(encoding="utf-8")
    verdicts = [line.strip() for line in text.splitlines() if line.startswith("VERDICT:")]
    if verdicts != ["VERDICT: SHIP"]:
        raise RuntimeError("adversarial review does not have one unambiguous SHIP verdict")
    if sha256_file(reviewed_artifact) not in text:
        raise RuntimeError("adversarial review does not bind the reviewed artifact SHA-256")
    return review


def make_attempt8_retirement_payload(review_path: Path) -> dict[str, Any]:
    _verify_implementation_candidate()
    review = _require_ship_review(review_path, IMPLEMENTATION_CANDIDATE)
    _, _, history = _verify_attempt8_history()
    run_inventory = recursive_inventory(ATTEMPT8_ROOT)
    external_paths = _attempt8_external_bindings()
    external_inventory = _exact_inventory(external_paths)
    absent = [str(path.relative_to(ROOT)) for path in _attempt8_required_absences()]
    if any(path.exists() for path in _attempt8_required_absences()):
        raise RuntimeError("attempt-8 required-absent downstream path exists")
    return {
        "schema_version": ATTEMPT8_RETIREMENT_SCHEMA,
        "status": "RETIRED_NO_RETRY",
        "attempt": "atlas_rope_v4_attempt8",
        "operator_intent": "Preserve attempt 8 as terminal; never retry, promote staging, freeze its invalid grid, or open its held-out stages.",
        "scope_caveat": "This inventories retained artifacts and recorded calls; it is not proof against an unlogged historical invocation.",
        "no_retry_authorized": True,
        "attempt8_run_tree_inventory": run_inventory,
        "attempt8_run_tree_inventory_sha256": inventory_digest(run_inventory),
        "external_input_inventory": external_inventory,
        "external_input_inventory_sha256": inventory_digest(external_inventory),
        "required_absent_paths": absent,
        "opened_calibration_history": history,
        "implementation_candidate_sha256": sha256_file(IMPLEMENTATION_CANDIDATE),
        "implementation_review": {"path": str(review.relative_to(ROOT)), "sha256": sha256_file(review), "verdict": "SHIP"},
        "validation_artifacts_or_model_calls_recorded": False,
        "neural_training_authorized": False,
    }


def verify_attempt8_retirement() -> dict[str, Any]:
    payload = verify_envelope(read_json(ATTEMPT8_RETIREMENT))
    if (payload.get("schema_version") != ATTEMPT8_RETIREMENT_SCHEMA or
            payload.get("status") != "RETIRED_NO_RETRY" or payload.get("no_retry_authorized") is not True or
            payload.get("neural_training_authorized") is not False):
        raise RuntimeError("attempt-8 retirement identity/permissions drift")
    run_inventory = recursive_inventory(ATTEMPT8_ROOT)
    if (payload.get("attempt8_run_tree_inventory") != run_inventory or
            payload.get("attempt8_run_tree_inventory_sha256") != inventory_digest(run_inventory)):
        raise RuntimeError("attempt-8 retired run-tree inventory drift")
    external = _exact_inventory(_attempt8_external_bindings())
    if (payload.get("external_input_inventory") != external or
            payload.get("external_input_inventory_sha256") != inventory_digest(external)):
        raise RuntimeError("attempt-8 retired external-input inventory drift")
    absent = [str(path.relative_to(ROOT)) for path in _attempt8_required_absences()]
    if payload.get("required_absent_paths") != absent or any(path.exists() for path in _attempt8_required_absences()):
        raise RuntimeError("attempt-8 retired required-absence drift")
    _, _, history = _verify_attempt8_history()
    if payload.get("opened_calibration_history") != history:
        raise RuntimeError("attempt-8 retired calibration-history drift")
    if payload.get("implementation_candidate_sha256") != sha256_file(IMPLEMENTATION_CANDIDATE):
        raise RuntimeError("attempt-8 retirement implementation binding drift")
    review = ROOT / str(payload.get("implementation_review", {}).get("path", ""))
    if not review.is_file() or sha256_file(review) != payload.get("implementation_review", {}).get("sha256"):
        raise RuntimeError("attempt-8 retirement review binding drift")
    return payload


def retire_attempt8(signing_key: Path, review_path: Path) -> dict[str, Any]:
    _assert_not_terminal()
    if ATTEMPT8_RETIREMENT.exists():
        raise RuntimeError("attempt-8 retirement is create-once")
    payload = make_attempt8_retirement_payload(review_path)
    write_signed(ATTEMPT8_RETIREMENT, payload, signing_key.resolve(strict=True))
    return verify_attempt8_retirement()


def make_implementation_candidate(verification_report: Path) -> dict[str, Any]:
    _assert_not_terminal()
    _, manifest = _verify_prescore()
    if IMPLEMENTATION_CANDIDATE.exists():
        raise RuntimeError("implementation candidate is create-once")
    if any(path.exists() for path in (RUN_ROOT, ATTEMPT8_RETIREMENT, CALIBRATION_IMPORT,
                                      CALIBRATION_CAP_CANDIDATE, EWT_AUTHORIZATION,
                                      FREEZE_CANDIDATE, VALIDATION_AUTHORIZATION, SCIENCE_AUTHORIZATION)):
        raise RuntimeError("model-stage roots must be absent before implementation freeze")
    _, _, attempt8_history = _verify_attempt8_history()
    attempt8_inventory = recursive_inventory(ATTEMPT8_ROOT)
    report_path = verification_report.resolve(strict=True)
    report = read_json(report_path)
    if report.get("status") != "PASS_NO_MODEL_CALLS" or report.get("neural_inference_run") is not False:
        raise RuntimeError("implementation verification report is not a no-inference PASS")
    path_map = {str(path.relative_to(ROOT)): path for path in IMPLEMENTATION_PATHS}
    inventory = _exact_inventory(path_map)
    _verify_report_inventory_hashes(report, inventory)
    scan = static_no_training_scan(NO_TRAINING_PATHS)
    if scan["status"] != "PASS":
        raise RuntimeError(f"technical implementation contains a forbidden training construct: {scan}")
    selected_support = {}
    for source in ("EWT_calibration", "GUM_fresh_validation", "GENTLE_validation"):
        panel_path = DATA_ROOT / source / "panel.json"
        panel = read_json(panel_path)
        references = read_jsonl(DATA_ROOT / source / "references.jsonl")
        union = len({str(unit["document_id"]) for unit in references})
        if union < 20:
            raise RuntimeError(f"selected-panel document union below 20: {source}")
        selected_support[source] = {"panel_sha256": sha256_file(panel_path), "selected_document_union": union,
                                    "minimum": 20, "logical_counts": panel["logical_counts"]}
    from run_atlas_rope_v5_science import science_adapter_binding
    science_adapter = science_adapter_binding()
    payload = {
        "schema_version": "atlas_rope_v5_attempt9_implementation_candidate_v1",
        "status": "READY_FOR_IMPLEMENTATION_ADVERSARIAL_REVIEW",
        "implementation_inventory": inventory,
        "static_no_training_scan": scan,
        "verification_report": {"path": str(report_path.relative_to(ROOT)), "sha256": sha256_file(report_path)},
        "prescore_config_sha256": sha256_file(CONFIG_PATH),
        "prescore_manifest_sha256": sha256_file(DATA_ROOT / "manifest.json"),
        "prescore_rebuild_report_sha256": sha256_file(REBUILD_REPORT),
        "runtime_probe_sha256": sha256_file(RUNTIME_PROBE),
        "attempt7_retirement_sha256": sha256_file(ATTEMPT7_RETIREMENT),
        "attempt8_terminal_sha256": attempt8_history["terminal_sha256"],
        "attempt8_staging_complete_sha256": attempt8_history["staging_complete_sha256"],
        "attempt8_run_tree_inventory_sha256": inventory_digest(attempt8_inventory),
        "attempt8_required_absences": [str(path.relative_to(ROOT)) for path in _attempt8_required_absences()],
        "source_provenance_sha256": sha256_file(ROOT / "data/atlas_rope_v4_raw/PROVENANCE.json"),
        "selected_panel_support": selected_support,
        "science_adapter": science_adapter,
        "validation_roots_absent": True,
        "model_calls_authorized": False,
        "neural_training_authorized": False,
    }
    atomic_json(IMPLEMENTATION_CANDIDATE, payload)
    return payload


def _verify_implementation_candidate() -> dict[str, Any]:
    payload = read_json(IMPLEMENTATION_CANDIDATE)
    if payload.get("schema_version") != "atlas_rope_v5_attempt9_implementation_candidate_v1" or payload.get("status") != "READY_FOR_IMPLEMENTATION_ADVERSARIAL_REVIEW":
        raise RuntimeError("implementation candidate identity drift")
    path_map = {str(path.relative_to(ROOT)): path for path in IMPLEMENTATION_PATHS}
    _verify_exact_inventory(path_map, payload.get("implementation_inventory", {}))
    report = ROOT / str(payload["verification_report"]["path"])
    report_payload = read_json(report)
    if sha256_file(report) != payload["verification_report"]["sha256"] or report_payload.get("status") != "PASS_NO_MODEL_CALLS":
        raise RuntimeError("implementation verification lineage drift")
    _verify_report_inventory_hashes(report_payload, payload["implementation_inventory"])
    if static_no_training_scan(NO_TRAINING_PATHS) != payload.get("static_no_training_scan"):
        raise RuntimeError("implementation static scan drift")
    bindings = {
        "prescore_config_sha256": CONFIG_PATH,
        "prescore_manifest_sha256": DATA_ROOT / "manifest.json",
        "prescore_rebuild_report_sha256": REBUILD_REPORT,
        "runtime_probe_sha256": RUNTIME_PROBE,
        "attempt7_retirement_sha256": ATTEMPT7_RETIREMENT,
        "source_provenance_sha256": ROOT / "data/atlas_rope_v4_raw/PROVENANCE.json",
    }
    if any(payload.get(key) != sha256_file(path) for key, path in bindings.items()):
        raise RuntimeError("implementation candidate evidence binding drift")
    _, _, attempt8_history = _verify_attempt8_history()
    if (payload.get("attempt8_terminal_sha256") != attempt8_history["terminal_sha256"] or
            payload.get("attempt8_staging_complete_sha256") != attempt8_history["staging_complete_sha256"] or
            payload.get("attempt8_run_tree_inventory_sha256") != inventory_digest(recursive_inventory(ATTEMPT8_ROOT)) or
            payload.get("attempt8_required_absences") != [str(path.relative_to(ROOT)) for path in _attempt8_required_absences()]):
        raise RuntimeError("implementation candidate attempt-8 history drift")
    for source, expected in payload.get("selected_panel_support", {}).items():
        panel_path = DATA_ROOT / source / "panel.json"
        references = read_jsonl(DATA_ROOT / source / "references.jsonl")
        observed = {"panel_sha256": sha256_file(panel_path),
                    "selected_document_union": len({str(unit["document_id"]) for unit in references}),
                    "minimum": 20, "logical_counts": read_json(panel_path)["logical_counts"]}
        if observed != expected or observed["selected_document_union"] < 20:
            raise RuntimeError(f"implementation selected-panel support drift: {source}")
    if set(payload.get("selected_panel_support", {})) != {"EWT_calibration", "GUM_fresh_validation", "GENTLE_validation"}:
        raise RuntimeError("implementation selected-panel support inventory drift")
    from run_atlas_rope_v5_science import science_adapter_binding
    if payload.get("science_adapter") != science_adapter_binding():
        raise RuntimeError("implementation science-adapter binding drift")
    return payload


def authorize_ewt(signing_key: Path, review_path: Path) -> dict[str, Any]:
    _assert_not_terminal()
    _verify_prescore()
    candidate = _verify_implementation_candidate()
    verify_attempt8_retirement()
    verify_calibration_import()
    verify_calibration_cap_candidate()
    if EWT_AUTHORIZATION.exists():
        raise RuntimeError("EWT authorization is create-once")
    review_path = _require_ship_review(review_path, IMPLEMENTATION_CANDIDATE)
    if any((RUN_ROOT / name).exists() for name in ("diagnostic", "validation", "science")):
        raise RuntimeError("downstream run roots must be absent before EWT authorization")
    payload = {
        "schema_version": AUTH_SCHEMA,
        "status": "AUTHORIZED",
        "authorized_stage": "EWT_DIAGNOSTIC_ONLY",
        "prescore_config_sha256": sha256_file(CONFIG_PATH),
        "prescore_manifest_sha256": sha256_file(DATA_ROOT / "manifest.json"),
        "prescore_rebuild_report_sha256": sha256_file(REBUILD_REPORT),
        "runtime_probe_sha256": sha256_file(RUNTIME_PROBE),
        "attempt7_retirement_sha256": sha256_file(ATTEMPT7_RETIREMENT),
        "attempt8_retirement_sha256": sha256_file(ATTEMPT8_RETIREMENT),
        "calibration_import_sha256": sha256_file(CALIBRATION_IMPORT),
        "calibration_cap_candidate_sha256": sha256_file(CALIBRATION_CAP_CANDIDATE),
        "implementation_candidate_sha256": sha256_file(IMPLEMENTATION_CANDIDATE),
        "implementation_review": {"path": str(review_path.relative_to(ROOT)), "sha256": sha256_file(review_path), "verdict": "SHIP"},
        "implementation_inventory": candidate["implementation_inventory"],
        "validation_model_calls_authorized": False,
        "science_model_calls_authorized": False,
        "neural_training_authorized": False,
    }
    write_signed(EWT_AUTHORIZATION, payload, signing_key)
    return _verify_authorization(EWT_AUTHORIZATION, stage="EWT_DIAGNOSTIC_ONLY")


def _loaded_relevant_libraries() -> list[dict[str, Any]]:
    paths: set[Path] = {Path(torch._C.__file__).resolve()}
    prefixes = ("libtorch", "libcuda", "libcud", "libcublas")
    for line in Path("/proc/self/maps").read_text(encoding="utf-8").splitlines():
        fields = line.split()
        if fields and fields[-1].startswith("/"):
            path = Path(fields[-1])
            if path.name.lower().startswith(prefixes):
                paths.add(path.resolve())
    return loaded_library_attestation(sorted(paths, key=lambda path: str(path).encode("utf-8")))


def _runtime_attestation(model: torch.nn.Module, device: torch.device, config: Mapping[str, Any]) -> dict[str, Any]:
    flags = {"flash": torch.backends.cuda.flash_sdp_enabled(), "mem_efficient": torch.backends.cuda.mem_efficient_sdp_enabled(),
             "math": torch.backends.cuda.math_sdp_enabled(), "cudnn": torch.backends.cuda.cudnn_sdp_enabled()}
    observed = _loaded_relevant_libraries()
    probe = read_json(RUNTIME_PROBE)
    library_check = verify_library_attestation(probe["required_libraries"], observed,
                                               forbidden_sonames=config["runtime"]["forbidden_alternate_sonames"])
    live_source = _verify_live_source_contract(config)
    result = {
        "python": platform.python_version(), "torch": torch.__version__, "cuda": torch.version.cuda,
        "cudnn": torch.backends.cudnn.version(), "gpu_uuid": _gpu_uuid(device),
        "cublas_workspace_config": os.environ.get("CUBLAS_WORKSPACE_CONFIG"),
        "deterministic_algorithms": torch.are_deterministic_algorithms_enabled(), "tf32": False,
        "autocast": False, "attention_backend": getattr(model.config, "_attn_implementation", None),
        "sdpa_flags": flags, "required_library_check": library_check, "observed_libraries": observed,
        "transformers": live_source["transformers"], "source_hashes": live_source["source_hashes"],
    }
    expected = config["runtime"]
    if (result["torch"] != expected["torch"] or result["cuda"] != expected["cuda"] or
            result["cudnn"] != expected["cudnn"] or result["gpu_uuid"] != expected["gpu_uuid"] or
            result["cublas_workspace_config"] != expected["cublas_workspace_config"] or
            result["attention_backend"] != "sdpa" or flags != expected["sdpa_flags"] or
            result["transformers"] != expected["transformers"] or result["source_hashes"] != expected["source_hashes"] or
            result["deterministic_algorithms"] is not True or library_check["status"] != "PASS"):
        raise RuntimeError(f"score-bearing runtime attestation failed: {result}")
    if json.loads(canonical_json_bytes(result)) != result:
        raise RuntimeError("runtime attestation is not strict JSON-native before forward")
    return result


def _load_model(config: Mapping[str, Any], device: torch.device) -> torch.nn.Module:
    spec = config["model"]
    model = AutoModelForCausalLM.from_pretrained(str(spec["name"]), revision=str(spec["revision"]),
                                                torch_dtype=torch.float32, local_files_only=True).to(device)
    model.eval().requires_grad_(False)
    if any(parameter.requires_grad for parameter in model.parameters()):
        raise RuntimeError("model parameters remain trainable")
    floating = [value.dtype for value in list(model.parameters()) + list(model.buffers()) if value.is_floating_point()]
    if not floating or set(floating) != {torch.float32}:
        raise RuntimeError(f"model floating dtype drift: {set(floating)}")
    if getattr(model.config, "_attn_implementation", None) != "sdpa":
        raise RuntimeError("frozen model loader did not resolve to SDPA")
    return model


def _forward_units(model: torch.nn.Module, units: Sequence[Mapping[str, Any]], *, device: torch.device,
                   hidden_index: int, batch_size: int) -> np.ndarray:
    if batch_size != BATCH_SIZE:
        raise RuntimeError("score-bearing batch size must be 64")
    blocks: list[np.ndarray] = []
    for start in range(0, len(units), batch_size):
        batch = units[start : start + batch_size]
        maximum = max(len(unit["input_ids"]) for unit in batch)
        input_ids = torch.zeros((len(batch), maximum), dtype=torch.long, device=device)
        attention_mask = torch.zeros_like(input_ids)
        position_ids = torch.zeros_like(input_ids)
        for index, unit in enumerate(batch):
            length = len(unit["input_ids"])
            input_ids[index, :length] = torch.as_tensor(unit["input_ids"], dtype=torch.long, device=device)
            attention_mask[index, :length] = torch.as_tensor(unit["attention_mask"], dtype=torch.long, device=device)
            position_ids[index, :length] = torch.as_tensor(unit["position_ids"], dtype=torch.long, device=device)
        with torch.inference_mode():
            output = model(input_ids=input_ids, attention_mask=attention_mask, position_ids=position_ids,
                           output_hidden_states=True, output_attentions=False, use_cache=False)
        if hidden_index >= len(output.hidden_states):
            raise RuntimeError("hidden-state index unavailable")
        hidden = output.hidden_states[hidden_index]
        if hidden.dtype != torch.float32:
            raise RuntimeError("hidden-state dtype drift")
        for index, unit in enumerate(batch):
            positions = torch.as_tensor(unit["positions"], dtype=torch.long, device=device)
            value = hidden[index].index_select(0, positions).float().cpu().numpy().astype(np.float32, copy=False)
            blocks.append(np.ascontiguousarray(value))
    if not blocks:
        raise RuntimeError("empty technical inference population")
    result = np.ascontiguousarray(np.concatenate(blocks, axis=0), dtype=np.float32)
    if not np.isfinite(result).all():
        raise RuntimeError("nonfinite technical inference output")
    return result


def _write_npy(path: Path, array: np.ndarray) -> None:
    np.save(path, np.ascontiguousarray(array, dtype=np.float32), allow_pickle=False)
    with path.open("rb") as handle:
        os.fsync(handle.fileno())


def _expanded_grid_reference(reference: np.ndarray) -> np.ndarray:
    if reference.shape != (200, WIDTH):
        raise RuntimeError("reference array shape drift")
    return np.ascontiguousarray(np.repeat(reference.reshape(100, 2, WIDTH)[:, None, :, :], len(SHIFTS), axis=1).reshape(1200, WIDTH))


def _extract_grid(model: torch.nn.Module, config: Mapping[str, Any], source: str, final: Path,
                  *, device: torch.device, validation_caps: Mapping[str, float] | None,
                  authorization_path: Path, signing_key: Path,
                  runtime_preflight: Mapping[str, Any]) -> dict[str, Any]:
    expected_finals = {
        "GUM_fresh_validation": RUN_ROOT / "validation/GUM_grid",
        "GENTLE_validation": RUN_ROOT / "validation/GENTLE_grid",
    }
    if source not in expected_finals:
        raise RuntimeError("attempt 9 forbids a new EWT score-bearing calibration forward")
    if validation_caps is None:
        raise RuntimeError("held-out validation requires frozen validation caps")
    if final.resolve() != expected_finals[source].resolve() or authorization_path.resolve() != VALIDATION_AUTHORIZATION.resolve():
        raise RuntimeError("held-out grid destination/authorization drift")
    _verify_authorization(VALIDATION_AUTHORIZATION, stage="SEQUENTIAL_HELDOUT_VALIDATION")
    if final.exists():
        return verify_grid_bundle(final, source=source, validation_caps=validation_caps)
    panel, references, candidates, rows = _load_panel(source)
    stage = new_staging(f"minimal-{source}", sha256_file(authorization_path))
    started = time.time()
    reference_repeats = [_forward_units(model, references, device=device, hidden_index=4, batch_size=64) for _ in range(3)]
    candidate = _forward_units(model, candidates, device=device, hidden_index=4, batch_size=64)
    if any(array.shape != (200, WIDTH) for array in reference_repeats) or candidate.shape != (1200, WIDTH):
        raise RuntimeError("grid output shape drift")
    if any(not np.array_equal(reference_repeats[0], value) or reference_repeats[0].tobytes(order="C") != value.tobytes(order="C")
           for value in reference_repeats[1:]):
        raise RuntimeError("repeated live inference is not byte-identical")
    for name, array in (("reference", reference_repeats[0]), ("reference_repeat_1", reference_repeats[1]),
                        ("reference_repeat_2", reference_repeats[2]), ("candidate", candidate)):
        _write_npy(stage / f"{name}.float32.npy", array)
    cached = np.load(stage / "reference.float32.npy", allow_pickle=False)
    _write_npy(stage / "reference_cached_replay.float32.npy", cached)
    replay = np.load(stage / "reference_cached_replay.float32.npy", allow_pickle=False)
    row_ids = [str(row["row_id"]) for row in rows]
    atomic_json(stage / "row_ids.json", {"reference": row_ids,
                                         "candidate": [str(row_id) for unit in candidates for row_id in unit["row_ids"]]})
    replay_check = exact_cached_replay(cached, replay, row_ids, row_ids,
                                       left_child_hash=sha256_file(stage / "reference.float32.npy"),
                                       right_child_hash=sha256_file(stage / "reference_cached_replay.float32.npy"))
    score = score_grid(reference_repeats[0], candidate, rows, atol=float(validation_caps["atol"]),
                       relative_l2_cap=float(validation_caps["relative_l2"]), cosine_cap=float(validation_caps["cosine_distance"]))
    status = "PASS" if score["status"] == "PASS" and replay_check["status"] == "PASS" else "FAIL"
    runtime_postflight = _runtime_attestation(model, device, config)
    artifacts = {path.name: {"bytes": path.stat().st_size, "sha256": sha256_file(path)}
                 for path in sorted(stage.iterdir()) if path.is_file()}
    payload = {
        "schema_version": BUNDLE_SCHEMA, "bundle_kind": "minimal_grid", "source": source, "status": status,
        "logical_counts": panel["logical_counts"], "score": score, "exact_cached_replay": replay_check,
        "live_reference_repeats_byte_identical": True, "reference_array_sha256": canonical_array_hash(reference_repeats[0]),
        "candidate_array_sha256": canonical_array_hash(candidate), "panel_sha256": sha256_file(DATA_ROOT / source / "panel.json"),
        "authorization": {"path": str(authorization_path.relative_to(ROOT)), "sha256": sha256_file(authorization_path)},
        "prescore_config_sha256": sha256_file(CONFIG_PATH), "prescore_manifest_sha256": sha256_file(DATA_ROOT / "manifest.json"),
        "runtime_preflight": dict(runtime_preflight), "runtime_postflight": runtime_postflight,
        "elapsed_seconds": time.time() - started, "artifacts": artifacts,
        "model": config["model"], "hidden_state_index": 4, "batch_size": 64,
        "parameter_dtype": "float32", "hidden_state_dtype": "float32", "cache_dtype": "float32",
        "model_eval": True, "inference_mode": True, "requires_grad": False,
        "labels_loaded": False, "estimator_created": False, "parameter_update_run": False,
        "checkpoint_created": False, "neural_training_run": False,
    }
    write_signed(stage / "COMPLETE.json", payload, signing_key)
    allowed = {"reference.float32.npy", "reference_repeat_1.float32.npy", "reference_repeat_2.float32.npy",
               "reference_cached_replay.float32.npy", "candidate.float32.npy", "row_ids.json", "COMPLETE.json"}
    assert_output_allowlist(stage, allowed)
    promote(stage, final)
    return verify_grid_bundle(final, source=source, validation_caps=validation_caps)


def verify_grid_bundle(final: Path, *, source: str, validation_caps: Mapping[str, float] | None) -> dict[str, Any]:
    expected_finals = {
        "GUM_fresh_validation": RUN_ROOT / "validation/GUM_grid",
        "GENTLE_validation": RUN_ROOT / "validation/GENTLE_grid",
    }
    if source not in expected_finals:
        raise RuntimeError("attempt 9 has no promoted score-bearing calibration bundle")
    if validation_caps is None:
        raise RuntimeError("held-out validation requires frozen validation caps")
    if final.resolve() != expected_finals[source].resolve():
        raise RuntimeError("held-out grid destination drift")
    _verify_authorization(VALIDATION_AUTHORIZATION, stage="SEQUENTIAL_HELDOUT_VALIDATION")
    allowed = {"reference.float32.npy", "reference_repeat_1.float32.npy", "reference_repeat_2.float32.npy",
               "reference_cached_replay.float32.npy", "candidate.float32.npy", "row_ids.json", "COMPLETE.json"}
    assert_output_allowlist(final, allowed)
    payload = verify_envelope(read_json(final / "COMPLETE.json"))
    if payload.get("schema_version") != BUNDLE_SCHEMA or payload.get("source") != source or payload.get("bundle_kind") != "minimal_grid":
        raise RuntimeError("grid completion identity drift")
    expected_status = "PASS"
    if payload.get("status") != expected_status:
        raise RuntimeError(f"grid bundle did not pass: {payload.get('status')}")
    artifact_names = allowed - {"COMPLETE.json"}
    if set(payload.get("artifacts", {})) != artifact_names:
        raise RuntimeError("grid artifact inventory is not exact")
    for name, spec in payload["artifacts"].items():
        path = final / name
        if sha256_file(path) != spec["sha256"] or path.stat().st_size != spec["bytes"]:
            raise RuntimeError(f"grid artifact drift: {name}")
    arrays = {name: np.load(final / f"{name}.float32.npy", allow_pickle=False)
              for name in ("reference", "reference_repeat_1", "reference_repeat_2", "reference_cached_replay", "candidate")}
    if any(array.dtype != np.float32 or not array.flags.c_contiguous or not np.isfinite(array).all() for array in arrays.values()):
        raise RuntimeError("grid arrays dtype/order/finite drift")
    if any(not np.array_equal(arrays["reference"], arrays[name]) for name in ("reference_repeat_1", "reference_repeat_2", "reference_cached_replay")):
        raise RuntimeError("grid repeat/cache replay drift")
    if arrays["reference"].shape != (200, WIDTH) or arrays["candidate"].shape != (1200, WIDTH):
        raise RuntimeError("grid array shape drift")
    if any(arrays[name].shape != (200, WIDTH) for name in ("reference_repeat_1", "reference_repeat_2", "reference_cached_replay")):
        raise RuntimeError("grid reference replay shape drift")
    panel, references, candidates, rows = _load_panel(source)
    row_ids = read_json(final / "row_ids.json")
    expected_reference_ids = [str(row["row_id"]) for row in rows]
    expected_candidate_ids = [str(row_id) for unit in candidates for row_id in unit["row_ids"]]
    if row_ids != {"reference": expected_reference_ids, "candidate": expected_candidate_ids}:
        raise RuntimeError("grid row-ID lineage drift")
    replay = exact_cached_replay(
        arrays["reference"], arrays["reference_cached_replay"], expected_reference_ids, expected_reference_ids,
        left_child_hash=sha256_file(final / "reference.float32.npy"),
        right_child_hash=sha256_file(final / "reference_cached_replay.float32.npy"),
    )
    if replay != payload.get("exact_cached_replay") or replay["status"] != "PASS":
        raise RuntimeError("grid cached replay did not independently recompute")
    if canonical_array_hash(arrays["reference"]) != payload.get("reference_array_sha256") or canonical_array_hash(arrays["candidate"]) != payload.get("candidate_array_sha256"):
        raise RuntimeError("grid canonical array digest drift")
    if payload.get("panel_sha256") != sha256_file(DATA_ROOT / source / "panel.json") or payload.get("logical_counts") != panel["logical_counts"]:
        raise RuntimeError("grid panel/count lineage drift")
    authorization_path = ROOT / str(payload.get("authorization", {}).get("path", ""))
    if not authorization_path.is_file() or sha256_file(authorization_path) != payload.get("authorization", {}).get("sha256"):
        raise RuntimeError("grid authorization lineage drift")
    _verify_authorization(authorization_path, stage="SEQUENTIAL_HELDOUT_VALIDATION")
    if payload.get("live_reference_repeats_byte_identical") is not True:
        raise RuntimeError("grid live-repeat attestation drift")
    for phase in ("runtime_preflight", "runtime_postflight"):
        runtime = payload.get(phase, {})
        if (runtime.get("required_library_check", {}).get("status") != "PASS" or runtime.get("gpu_uuid") != GPU_UUID or
                runtime.get("attention_backend") != "sdpa" or runtime.get("source_hashes") != read_json(CONFIG_PATH)["runtime"]["source_hashes"]):
            raise RuntimeError(f"grid {phase} attestation drift")
    recomputed = score_grid(arrays["reference"], arrays["candidate"], rows, atol=float(validation_caps["atol"]),
                            relative_l2_cap=float(validation_caps["relative_l2"]), cosine_cap=float(validation_caps["cosine_distance"]))
    if recomputed != payload["score"] or recomputed["status"] != "PASS":
        raise RuntimeError("grid validation score did not independently recompute")
    return payload


def _calibration_import_payload() -> dict[str, Any]:
    verify_attempt8_retirement()
    reference, candidate, history = _verify_attempt8_history()
    return {
        "schema_version": "atlas_rope_v5_attempt9_opened_calibration_import_v1",
        "status": "VERIFIED_OPENED_CALIBRATION_HISTORY",
        "source_attempt": "atlas_rope_v4_attempt8",
        "source_attempt_status": "TERMINAL_EWT_CALIBRATION_INVALID",
        "source_bundle_promoted": False,
        "source_bundle_represented_as_attempt8_pass": False,
        "source_staging_path": str(ATTEMPT8_STAGING.relative_to(ROOT)),
        "history": history,
        "reference_shape": list(reference.shape),
        "candidate_shape": list(candidate.shape),
        "exact_cached_replay": True,
        "three_live_references_byte_identical": True,
        "attempt8_retirement_sha256": sha256_file(ATTEMPT8_RETIREMENT),
        "implementation_candidate_sha256": sha256_file(IMPLEMENTATION_CANDIDATE),
        "validation_model_calls_recorded": False,
        "calibration_only": True,
        "neural_training_authorized": False,
    }


def import_attempt8_calibration(signing_key: Path) -> dict[str, Any]:
    _assert_not_terminal()
    _verify_prescore()
    _verify_implementation_candidate()
    if CALIBRATION_IMPORT.exists():
        raise RuntimeError("opened calibration import is create-once")
    if any((RUN_ROOT / name).exists() for name in ("calibration", "diagnostic", "validation", "science")):
        raise RuntimeError("promoted/model-stage root exists before calibration import")
    payload = _calibration_import_payload()
    write_signed(CALIBRATION_IMPORT, payload, signing_key.resolve(strict=True))
    return verify_calibration_import()


def verify_calibration_import() -> dict[str, Any]:
    observed = verify_envelope(read_json(CALIBRATION_IMPORT))
    expected = _calibration_import_payload()
    if observed != expected:
        raise RuntimeError("opened calibration import drift")
    return observed


def _calibration_cap_payload() -> dict[str, Any]:
    imported = verify_calibration_import()
    old_reference, old_candidate, old_lineage = _retained_attempt7_pair()
    new_reference, new_candidate, history = _verify_attempt8_history()
    caps = derive_caps([
        (old_reference, old_candidate),
        (_expanded_grid_reference(new_reference), new_candidate),
    ])
    if (caps.get("status") != "PASS" or caps.get("caps") != {
            "atol": 2e-5, "relative_l2": 1e-5, "cosine_distance": 1e-11} or
            caps.get("calibration_rows") != 1272):
        raise RuntimeError(f"calibration-selected caps differ from the frozen attempt-9 contract: {caps}")
    return {
        "schema_version": "atlas_rope_v5_attempt9_calibration_cap_candidate_v1",
        "status": "CALIBRATION_SELECTED_VALIDATION_PREREGISTERED",
        "caps": caps["caps"],
        "rtol": caps["rtol"],
        "safety_factor": caps["safety_factor"],
        "observed_calibration_maxima": caps["observed_maxima"],
        "calibration_rows": caps["calibration_rows"],
        "old_atol_grid": list(OLD_ATOL_GRID),
        "expanded_atol_grid": list(ATOL_GRID),
        "relative_l2_grid": list(REL_L2_GRID),
        "cosine_distance_grid": list(COSINE_GRID),
        "selection_arithmetic": {
            "observed_required_atol": 1.3512020111083984e-05,
            "safety_factor": 1.25,
            "target": 1.689002513885498e-05,
            "smallest_expanded_grid_cap_at_or_above_target": 2e-05,
        },
        "retained_attempt7_ewt": old_lineage,
        "imported_attempt8_ewt": history,
        "calibration_import_sha256": sha256_file(CALIBRATION_IMPORT),
        "attempt8_retirement_sha256": imported["attempt8_retirement_sha256"],
        "diagnostic_values_used": False,
        "diagnostic_outputs_existed_at_freeze": False,
        "validation_outputs_existed_at_freeze": False,
        "neural_training_authorized": False,
    }


def make_calibration_cap_candidate(signing_key: Path) -> dict[str, Any]:
    _assert_not_terminal()
    if CALIBRATION_CAP_CANDIDATE.exists():
        raise RuntimeError("calibration-cap candidate is create-once")
    if (RUN_ROOT / "diagnostic").exists() or (RUN_ROOT / "validation").exists():
        raise RuntimeError("diagnostic/validation opened before calibration-cap freeze")
    payload = _calibration_cap_payload()
    write_signed(CALIBRATION_CAP_CANDIDATE, payload, signing_key.resolve(strict=True))
    return verify_calibration_cap_candidate()


def verify_calibration_cap_candidate() -> dict[str, Any]:
    observed = verify_envelope(read_json(CALIBRATION_CAP_CANDIDATE))
    expected = _calibration_cap_payload()
    if observed != expected:
        raise RuntimeError("calibration-cap candidate drift")
    return observed


def _retained_attempt7_pair(*, qa_root_override: Path | None = None) -> tuple[np.ndarray, np.ndarray, dict[str, Any]]:
    retirement = verify_attempt7_retirement(ATTEMPT7_RETIREMENT)
    qa_root = qa_root_override or ROOT / retirement["bindings"]["retained_ewt_qa"]["path"]
    if {path.name for path in qa_root.iterdir()} != {"QA_COMPLETE.json", "qa_arrays.float32.npz", "qa_rows.json"} or any(
            not path.is_file() or path.is_symlink() for path in qa_root.iterdir()):
        raise RuntimeError("retained attempt-7 QA file inventory drift")
    complete = verify_envelope(read_json(qa_root / "QA_COMPLETE.json"))
    scoring_path = ROOT / retirement["bindings"]["attempt7_scoring_config"]["path"]
    scoring = read_json(scoring_path)
    if sha256_file(scoring_path) != retirement["bindings"]["attempt7_scoring_config"]["sha256"]:
        raise RuntimeError("retained attempt-7 scoring-config binding drift")
    prescore_path = ROOT / str(scoring["prescore_config"]["path"])
    split_path = ROOT / str(scoring["population_split"]["path"])
    prescore, split = read_json(prescore_path), read_json(split_path)
    final_manifest_path = ROOT / str(prescore["data_root"]) / "prepared/manifest.json"
    attempt8_runtime = read_json(CONFIG_PATH)["runtime"]
    expected_environment = {
        "python": read_json(RUNTIME_PROBE)["python"], "torch": attempt8_runtime["torch"],
        "cuda": attempt8_runtime["cuda"], "cudnn": attempt8_runtime["cudnn"],
        "cublas_workspace_config": attempt8_runtime["cublas_workspace_config"],
        "deterministic_algorithms": True, "tf32": False,
    }
    if complete.get("schema_version") != "atlas_discovery_v3_3_attempt7_numerical_qa_v2" or complete.get("source") != "EWT" or complete.get("status") != "FAIL":
        raise RuntimeError("retained attempt-7 EWT evidence identity drift")
    if (scoring.get("schema_version") != "atlas_discovery_v3_3_attempt7_scoring_v2" or
            scoring.get("status") != "frozen_numerical_qa_authorized" or
            complete.get("scoring_config_sha256") != sha256_file(scoring_path) or
            sha256_file(prescore_path) != scoring["prescore_config"]["sha256"] or
            complete.get("prescore_config_sha256") != scoring["prescore_config"]["sha256"] or
            sha256_file(split_path) != scoring["population_split"]["sha256"] or
            sha256_file(final_manifest_path) != scoring["prepared_manifest_sha256"] or
            complete.get("prepared_manifest_sha256") != scoring["prepared_manifest_sha256"]):
        raise RuntimeError("retained attempt-7 top-level lineage drift")
    expected_payload = {
        "model": prescore["model"], "layer": int(prescore["model"]["layer"]),
        "hidden_state_index": int(prescore["model"]["layer"]) + 1,
        "device": scoring["extraction"]["qa_devices"]["EWT"],
        "gpu_uuid": scoring["extraction"]["qa_gpu_uuids"]["EWT"],
        "batch_size": int(scoring["extraction"]["batch_size"]),
        "dtype": "float32_inference_float32_cache", "parameter_dtype": "float32",
        "hidden_state_dtype": "float32", "cache_dtype": "float32",
        "autocast_enabled": False, "optimizer_created": False, "checkpoint_created": False,
        "neural_training_run": False,
    }
    if any(complete.get(key) != value for key, value in expected_payload.items()) or complete.get("environment") != expected_environment:
        raise RuntimeError("retained attempt-7 model/runtime semantic contract drift")
    if sha256_file(qa_root / "qa_arrays.float32.npz") != complete["qa_arrays_sha256"] or sha256_file(qa_root / "qa_rows.json") != complete["qa_row_manifest_sha256"]:
        raise RuntimeError("retained attempt-7 child digest drift")
    expected_rows: list[dict[str, Any]] = []
    reference_units: list[Mapping[str, Any]] = []
    candidate_units: list[Mapping[str, Any]] = []
    parents: dict[str, Any] = {}
    for panel in ("legacy", "fresh"):
        parent_spec = scoring[f"{panel}_qa_parent"]
        parent_config_path = ROOT / str(parent_spec["config_path"])
        parent_manifest_path = ROOT / str(parent_spec["manifest_path"])
        if sha256_file(parent_config_path) != parent_spec["config_sha256"] or sha256_file(parent_manifest_path) != parent_spec["manifest_sha256"]:
            raise RuntimeError(f"retained attempt-7 {panel} parent binding drift")
        parent_config, parent_manifest = read_json(parent_config_path), read_json(parent_manifest_path)
        if parent_manifest.get("config_sha256") != parent_spec["config_sha256"]:
            raise RuntimeError(f"retained attempt-7 {panel} parent config/manifest mismatch")
        bundle = _attempt7_load_source_bundle(parent_config, parent_manifest, "EWT")
        pair_ids = list(map(str, split["sources"]["EWT"][f"{panel}_pair_ids"]))
        panel_refs, panel_candidates, panel_rows, _ = _attempt7_qa_panel_units(
            bundle, pair_ids, prescore, panel=panel
        )
        reference_units.extend(panel_refs)
        candidate_units.extend(panel_candidates)
        expected_rows.extend(panel_rows)
        parents[panel] = {
            "config_sha256": parent_spec["config_sha256"],
            "manifest_sha256": parent_spec["manifest_sha256"],
            "inference_units_sha256": parent_manifest["sources"]["EWT"]["units_sha256"],
            "activation_rows_sha256": parent_manifest["sources"]["EWT"]["activation_rows_sha256"],
            "intervention_pairs_sha256": parent_manifest["sources"]["EWT"]["intervention_pairs_sha256"],
        }
    expected_lineage = {
        "population_split_sha256": sha256_file(split_path),
        "prescore_config_sha256": sha256_file(prescore_path),
        "parents": parents,
    }
    observed_rows = json.loads((qa_root / "qa_rows.json").read_text(encoding="utf-8"))
    if observed_rows != expected_rows or complete.get("qa_input_lineage") != expected_lineage:
        raise RuntimeError("retained attempt-7 exact row/parent lineage drift")
    if len(expected_rows) != 48 or complete.get("qa_underlying_units") != 48:
        raise RuntimeError("retained attempt-7 underlying-unit count drift")
    expanded: list[dict[str, Any]] = []
    family_indices: dict[str, list[int]] = {}
    for row, reference_unit, candidate_unit in zip(expected_rows, reference_units, candidate_units, strict=True):
        roles = list(map(str, row["roles"]))
        if len(reference_unit["row_ids"]) != len(roles) or len(candidate_unit["row_ids"]) != len(roles):
            raise RuntimeError("retained attempt-7 role expansion drift")
        for role, reference_row_id, candidate_row_id in zip(
                roles, reference_unit["row_ids"], candidate_unit["row_ids"], strict=True):
            family_indices.setdefault(f"{row['panel']}|{row['family']}", []).append(len(expanded))
            expanded.append({"panel": row["panel"], "family": row["family"], "pair_id": row["pair_id"],
                             "role": role, "reference_row_id": str(reference_row_id),
                             "candidate_row_id": str(candidate_row_id)})
    if (len(expanded) != 72 or complete.get("qa_activation_rows") != 72 or
            len({row["reference_row_id"] for row in expanded}) != 72 or
            len({row["candidate_row_id"] for row in expanded}) != 72):
        raise RuntimeError("retained attempt-7 expanded row mapping drift")
    with np.load(qa_root / "qa_arrays.float32.npz", allow_pickle=False) as loaded:
        arrays = {name: np.ascontiguousarray(loaded[name]) for name in loaded.files}
    if set(arrays) != {"reference", "repeat_1", "repeat_2", "candidate"} or any(value.dtype != np.float32 or value.shape != (72, WIDTH) for value in arrays.values()):
        raise RuntimeError("retained attempt-7 array structure drift")
    if any(not np.isfinite(value).all() or not value.flags.c_contiguous for value in arrays.values()):
        raise RuntimeError("retained attempt-7 array finite/order drift")
    if any(not np.array_equal(arrays["reference"], arrays[name]) or arrays["reference"].tobytes(order="C") != arrays[name].tobytes(order="C")
           for name in ("repeat_1", "repeat_2")):
        raise RuntimeError("retained attempt-7 reference repeats drift")
    tolerance, panels = _attempt7_recompute_qa_evidence(arrays, expected_rows, prescore["numerical_qa"])
    if tolerance != complete.get("tolerance") or panels != complete.get("panels"):
        raise RuntimeError("retained attempt-7 signed numerical evidence does not independently recompute")
    expected_panel_rows = {"legacy": {"uniform_shift": 32, "prefix_position_only": 16},
                           "fresh": {"uniform_shift": 16, "prefix_position_only": 8}}
    if (set(panels) != {"legacy", "fresh"} or any(set(panels[panel]) != {"uniform_shift", "prefix_position_only"}
            or any(panels[panel][family]["rows"] != rows for family, rows in expected_panel_rows[panel].items())
            for panel in expected_panel_rows)):
        raise RuntimeError("retained attempt-7 panel/family semantic contract drift")
    expected_family_counts = {"legacy|uniform_shift": 32, "legacy|prefix_position_only": 16,
                              "fresh|uniform_shift": 16, "fresh|prefix_position_only": 8}
    if set(family_indices) != set(expected_family_counts) or any(
            len(family_indices[key]) != count for key, count in expected_family_counts.items()):
        raise RuntimeError("retained attempt-7 expanded family-index contract drift")
    return arrays["reference"], arrays["candidate"], {"qa_complete_sha256": sha256_file(qa_root / "QA_COMPLETE.json"),
                                                       "qa_arrays_sha256": sha256_file(qa_root / "qa_arrays.float32.npz"),
                                                       "qa_rows_sha256": sha256_file(qa_root / "qa_rows.json"),
                                                       "expanded_mapping_sha256": sha256_bytes(json.dumps(expanded, sort_keys=True, separators=(",", ":")).encode()),
                                                       "expanded_rows": len(expanded),
                                                       "family_indices": family_indices,
                                                       "semantic_verification": "PASS"}


def make_freeze_candidate(signing_key: Path | None = None) -> dict[str, Any]:
    _assert_not_terminal()
    implementation = _verify_implementation_candidate()
    _verify_prescore()
    verify_attempt8_retirement()
    imported = verify_calibration_import()
    cap_candidate = verify_calibration_cap_candidate()
    ewt_authorization = _verify_authorization(EWT_AUTHORIZATION, stage="EWT_DIAGNOSTIC_ONLY")
    diagnostic = RUN_ROOT / "diagnostic/DIAGNOSTIC_COMPLETE.json"
    diagnostic_payload = verify_envelope(read_json(diagnostic))
    if (diagnostic_payload.get("status") != "PASS" or
            diagnostic_payload.get("threshold_tuning_authorized") is not False or
            diagnostic_payload.get("calibration_cap_candidate_sha256") != sha256_file(CALIBRATION_CAP_CANDIDATE)):
        raise RuntimeError("mandatory diagnostic observer comparison did not pass")
    payload = {
        "schema_version": "atlas_rope_v5_attempt9_validation_freeze_candidate_v1", "status": "READY_FOR_ADVERSARIAL_REVIEW",
        "caps": cap_candidate["caps"], "rtol": cap_candidate["rtol"],
        "safety_factor": cap_candidate["safety_factor"],
        "observed_calibration_maxima": cap_candidate["observed_calibration_maxima"],
        "calibration_rows": cap_candidate["calibration_rows"],
        "calibration_cap_candidate_sha256": sha256_file(CALIBRATION_CAP_CANDIDATE),
        "calibration_import_sha256": sha256_file(CALIBRATION_IMPORT),
        "attempt8_retirement_sha256": sha256_file(ATTEMPT8_RETIREMENT),
        "engineering_budgets": {"per_cell_failing_elements": 30, "per_cell_failing_rows": 2,
                                "relative_l2_failures": 0, "cosine_failures": 0},
        "retained_attempt7_ewt": cap_candidate["retained_attempt7_ewt"],
        "imported_attempt8_ewt": imported["history"],
        "diagnostic_complete_sha256": sha256_file(diagnostic),
        "diagnostic_values_used_for_thresholds": False,
        "implementation_candidate_sha256": sha256_file(IMPLEMENTATION_CANDIDATE),
        "implementation_inventory": implementation["implementation_inventory"],
        "implementation_verification_report": implementation["verification_report"],
        "ewt_authorization_sha256": sha256_file(EWT_AUTHORIZATION),
        "implementation_review_sha256": ewt_authorization["implementation_review"]["sha256"],
        "prescore_config_sha256": sha256_file(CONFIG_PATH), "prescore_manifest_sha256": sha256_file(DATA_ROOT / "manifest.json"),
        "science_adapter": implementation["science_adapter"],
        "validation_order": ["GUM_fresh_sentinel", "GUM_fresh_validation", "GENTLE_validation"],
        "validation_model_calls_already_run": False, "neural_training_authorized": False,
    }
    if FREEZE_CANDIDATE.exists():
        if read_json(FREEZE_CANDIDATE) != payload:
            raise RuntimeError("existing freeze candidate drift")
    else:
        atomic_json(FREEZE_CANDIDATE, payload)
    return payload


def authorize_validation(signing_key: Path, review_path: Path) -> dict[str, Any]:
    _assert_not_terminal()
    candidate = make_freeze_candidate(signing_key)
    if VALIDATION_AUTHORIZATION.exists():
        raise RuntimeError("validation authorization is create-once")
    review_path = _require_ship_review(review_path, FREEZE_CANDIDATE)
    if (RUN_ROOT / "validation").exists():
        raise RuntimeError("validation root exists before authorization")
    payload = {
        "schema_version": AUTH_SCHEMA, "status": "AUTHORIZED", "authorized_stage": "SEQUENTIAL_HELDOUT_VALIDATION",
        "prescore_config_sha256": sha256_file(CONFIG_PATH), "prescore_manifest_sha256": sha256_file(DATA_ROOT / "manifest.json"),
        "freeze_candidate_sha256": sha256_file(FREEZE_CANDIDATE), "freeze_candidate": candidate,
        "implementation_candidate_sha256": candidate["implementation_candidate_sha256"],
        "implementation_inventory": candidate["implementation_inventory"],
        "implementation_verification_report": candidate["implementation_verification_report"],
        "ewt_authorization_sha256": candidate["ewt_authorization_sha256"],
        "calibration_cap_candidate_sha256": candidate["calibration_cap_candidate_sha256"],
        "attempt8_retirement_sha256": candidate["attempt8_retirement_sha256"],
        "science_adapter": candidate["science_adapter"],
        "freeze_review": {"path": str(review_path.relative_to(ROOT)), "sha256": sha256_file(review_path), "verdict": "SHIP"},
        "fresh_gum_first": True, "gentle_requires_gum_pass": True, "threshold_change_authorized": False,
        "science_model_calls_authorized": False, "neural_training_authorized": False,
    }
    write_signed(VALIDATION_AUTHORIZATION, payload, signing_key)
    return _verify_authorization(VALIDATION_AUTHORIZATION, stage="SEQUENTIAL_HELDOUT_VALIDATION")


def _validation_caps() -> dict[str, float]:
    auth = _verify_authorization(VALIDATION_AUTHORIZATION, stage="SEQUENTIAL_HELDOUT_VALIDATION")
    candidate = auth["freeze_candidate"]
    if sha256_file(FREEZE_CANDIDATE) != auth["freeze_candidate_sha256"] or read_json(FREEZE_CANDIDATE) != candidate:
        raise RuntimeError("validation freeze candidate drift")
    return {key: float(value) for key, value in candidate["caps"].items()}


def _load_sentinel_panel() -> tuple[dict[str, Any], list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    panel_root = DATA_ROOT / "GUM_fresh_sentinel"
    panel = read_json(panel_root / "panel.json")
    references = read_jsonl(panel_root / "references.jsonl")
    candidates = read_jsonl(panel_root / "candidates.jsonl")
    pair_rows = read_jsonl(panel_root / "pair_rows.jsonl")
    if set(panel.get("children", {})) != {"references.jsonl", "candidates.jsonl", "pair_rows.jsonl"}:
        raise RuntimeError("fresh GUM sentinel child inventory drift")
    for name, spec in panel["children"].items():
        path = panel_root / name
        if sha256_file(path) != spec["sha256"] or path.stat().st_size != spec["bytes"]:
            raise RuntimeError(f"fresh GUM sentinel panel child drift: {name}")
    if len(references) != 16 or len(candidates) != 16 or len(pair_rows) != 16:
        raise RuntimeError("fresh GUM sentinel unit count drift")
    pair_ids = [str(row["pair_id"]) for row in pair_rows]
    if panel.get("literal_pair_ids") != pair_ids or len(set(pair_ids)) != 16:
        raise RuntimeError("fresh GUM sentinel literal pair order/uniqueness drift")
    if [str(row["reference_unit_id"]) for row in pair_rows] != [str(unit["unit_id"]) for unit in references]:
        raise RuntimeError("fresh GUM sentinel reference order drift")
    if [str(row["candidate_unit_id"]) for row in pair_rows] != [str(unit["unit_id"]) for unit in candidates]:
        raise RuntimeError("fresh GUM sentinel candidate order drift")
    expanded_ids = [str(value) for row in pair_rows for value in row["expanded_row_ids"]]
    if (expanded_ids != list(map(str, panel.get("expanded_row_ids", []))) or len(expanded_ids) != 24 or
            len(set(expanded_ids)) != 24):
        raise RuntimeError("fresh GUM sentinel expanded row IDs drift")
    if [len(unit["positions"]) for unit in references] != [len(row["roles"]) for row in pair_rows] or [len(unit["positions"]) for unit in candidates] != [len(row["roles"]) for row in pair_rows]:
        raise RuntimeError("fresh GUM sentinel role expansion drift")
    reference_schedule, candidate_schedule = batch_schedule(references), batch_schedule(candidates)
    if panel["schedules"]["reference"] != reference_schedule or panel["schedules"]["candidate"] != candidate_schedule:
        raise RuntimeError("fresh GUM sentinel schedule drift")
    if panel["schedules"]["reference_repeats"] != [reference_schedule for _ in range(3)]:
        raise RuntimeError("fresh GUM sentinel repeat schedule drift")
    return panel, references, candidates, pair_rows


def _extract_sentinel(model: torch.nn.Module, config: Mapping[str, Any], device: torch.device,
                      caps: Mapping[str, float], signing_key: Path,
                      runtime_preflight: Mapping[str, Any]) -> dict[str, Any]:
    final = RUN_ROOT / "validation/GUM_sentinel"
    if final.exists():
        return verify_sentinel_bundle(final, caps)
    panel_root = DATA_ROOT / "GUM_fresh_sentinel"
    panel, references, candidates, pair_rows = _load_sentinel_panel()
    stage = new_staging("sentinel-GUM", sha256_file(VALIDATION_AUTHORIZATION))
    repeats = [_forward_units(model, references, device=device, hidden_index=4, batch_size=64) for _ in range(3)]
    candidate = _forward_units(model, candidates, device=device, hidden_index=4, batch_size=64)
    if any(value.shape != (24, WIDTH) for value in repeats) or candidate.shape != (24, WIDTH):
        raise RuntimeError("fresh GUM sentinel array shape drift")
    if any(not np.array_equal(repeats[0], value) or repeats[0].tobytes(order="C") != value.tobytes(order="C") for value in repeats[1:]):
        raise RuntimeError("fresh GUM sentinel live repeats differ")
    for name, array in (("reference", repeats[0]), ("reference_repeat_1", repeats[1]),
                        ("reference_repeat_2", repeats[2]), ("candidate", candidate)):
        _write_npy(stage / f"{name}.float32.npy", array)
    cached = np.load(stage / "reference.float32.npy", allow_pickle=False)
    _write_npy(stage / "reference_cached_replay.float32.npy", cached)
    replay = np.load(stage / "reference_cached_replay.float32.npy", allow_pickle=False)
    row_ids = list(map(str, panel["expanded_row_ids"]))
    replay_check = exact_cached_replay(cached, replay, row_ids, row_ids,
                                       left_child_hash=sha256_file(stage / "reference.float32.npy"),
                                       right_child_hash=sha256_file(stage / "reference_cached_replay.float32.npy"))
    cursor = 0
    scores: list[dict[str, Any]] = []
    for row in pair_rows:
        width = len(row["roles"])
        stat = score_cell(repeats[0][cursor:cursor + width], candidate[cursor:cursor + width],
                          atol=caps["atol"], relative_l2_cap=caps["relative_l2"], cosine_cap=caps["cosine_distance"],
                          strict_zero_failures=True)
        scores.append({**row, "score": stat,
                       "reference_rows_sha256": canonical_array_hash(repeats[0][cursor:cursor + width]),
                       "candidate_rows_sha256": canonical_array_hash(candidate[cursor:cursor + width])})
        cursor += width
    if cursor != 24:
        raise RuntimeError("fresh GUM sentinel row traversal drift")
    atomic_json(stage / "pair_scores.json", {"pairs": scores})
    atomic_json(stage / "row_ids.json", {"expanded_row_ids": row_ids})
    passed = replay_check["status"] == "PASS" and all(row["score"]["status"] == "PASS" for row in scores)
    payload = {"schema_version": BUNDLE_SCHEMA, "bundle_kind": "fresh_gum_sentinel", "source": "GUM", "status": "PASS" if passed else "FAIL",
               "pairs": 16, "rows": 24, "pair_scores_sha256": sha256_file(stage / "pair_scores.json"),
               "exact_cached_replay": replay_check, "live_reference_repeats_byte_identical": True,
               "panel_sha256": sha256_file(panel_root / "panel.json"), "caps": dict(caps),
               "authorization_sha256": sha256_file(VALIDATION_AUTHORIZATION),
               "runtime_preflight": dict(runtime_preflight), "runtime_postflight": _runtime_attestation(model, device, config),
               "model_eval": True, "inference_mode": True, "requires_grad": False, "labels_loaded": False,
               "estimator_created": False, "parameter_update_run": False, "checkpoint_created": False, "neural_training_run": False}
    payload["artifacts"] = {path.name: {"bytes": path.stat().st_size, "sha256": sha256_file(path)} for path in sorted(stage.iterdir()) if path.is_file()}
    write_signed(stage / "COMPLETE.json", payload, signing_key)
    allowed = {"reference.float32.npy", "reference_repeat_1.float32.npy", "reference_repeat_2.float32.npy",
               "reference_cached_replay.float32.npy", "candidate.float32.npy", "pair_scores.json", "row_ids.json", "COMPLETE.json"}
    assert_output_allowlist(stage, allowed)
    promote(stage, final)
    return verify_sentinel_bundle(final, caps)


def verify_sentinel_bundle(final: Path, caps: Mapping[str, float]) -> dict[str, Any]:
    allowed = {"reference.float32.npy", "reference_repeat_1.float32.npy", "reference_repeat_2.float32.npy",
               "reference_cached_replay.float32.npy", "candidate.float32.npy", "pair_scores.json", "row_ids.json", "COMPLETE.json"}
    assert_output_allowlist(final, allowed)
    payload = verify_envelope(read_json(final / "COMPLETE.json"))
    if payload.get("bundle_kind") != "fresh_gum_sentinel" or payload.get("status") != "PASS" or payload.get("caps") != dict(caps):
        raise RuntimeError("fresh GUM sentinel completion drift/failure")
    if set(payload.get("artifacts", {})) != allowed - {"COMPLETE.json"}:
        raise RuntimeError("fresh GUM sentinel artifact inventory is not exact")
    for name, spec in payload["artifacts"].items():
        path = final / name
        if sha256_file(path) != spec["sha256"] or path.stat().st_size != spec["bytes"]:
            raise RuntimeError(f"fresh GUM sentinel artifact drift: {name}")
    arrays = {name: np.load(final / f"{name}.float32.npy", allow_pickle=False)
              for name in ("reference", "reference_repeat_1", "reference_repeat_2", "reference_cached_replay", "candidate")}
    if any(value.dtype != np.float32 or value.shape != (24, WIDTH) or not value.flags.c_contiguous or not np.isfinite(value).all()
           for value in arrays.values()):
        raise RuntimeError("fresh GUM sentinel array structure drift")
    reference, candidate = arrays["reference"], arrays["candidate"]
    if any(not np.array_equal(reference, arrays[name]) or reference.tobytes(order="C") != arrays[name].tobytes(order="C")
           for name in ("reference_repeat_1", "reference_repeat_2", "reference_cached_replay")):
        raise RuntimeError("fresh GUM sentinel repeat/cache replay drift")
    panel, references, candidates, pair_rows = _load_sentinel_panel()
    row_ids = list(map(str, panel["expanded_row_ids"]))
    if read_json(final / "row_ids.json") != {"expanded_row_ids": row_ids}:
        raise RuntimeError("fresh GUM sentinel row-ID lineage drift")
    replay = exact_cached_replay(reference, arrays["reference_cached_replay"], row_ids, row_ids,
                                 left_child_hash=sha256_file(final / "reference.float32.npy"),
                                 right_child_hash=sha256_file(final / "reference_cached_replay.float32.npy"))
    if replay != payload.get("exact_cached_replay") or replay["status"] != "PASS":
        raise RuntimeError("fresh GUM sentinel cached replay did not independently recompute")
    if payload.get("live_reference_repeats_byte_identical") is not True or payload.get("panel_sha256") != sha256_file(DATA_ROOT / "GUM_fresh_sentinel/panel.json"):
        raise RuntimeError("fresh GUM sentinel repeat/panel lineage drift")
    if payload.get("authorization_sha256") != sha256_file(VALIDATION_AUTHORIZATION):
        raise RuntimeError("fresh GUM sentinel authorization lineage drift")
    _verify_authorization(VALIDATION_AUTHORIZATION, stage="SEQUENTIAL_HELDOUT_VALIDATION")
    for phase in ("runtime_preflight", "runtime_postflight"):
        runtime = payload.get(phase, {})
        if (runtime.get("required_library_check", {}).get("status") != "PASS" or runtime.get("gpu_uuid") != GPU_UUID or
                runtime.get("attention_backend") != "sdpa" or runtime.get("source_hashes") != read_json(CONFIG_PATH)["runtime"]["source_hashes"]):
            raise RuntimeError(f"fresh GUM sentinel {phase} attestation drift")
    scores = read_json(final / "pair_scores.json")["pairs"]
    if len(scores) != len(pair_rows) or any({key: row[key] for key in ("pair_id", "reference_unit_id", "candidate_unit_id", "expanded_row_ids", "roles")}
                                               != {key: expected[key] for key in ("pair_id", "reference_unit_id", "candidate_unit_id", "expanded_row_ids", "roles")}
                                               for row, expected in zip(scores, pair_rows, strict=True)):
        raise RuntimeError("fresh GUM sentinel pair lineage drift")
    cursor = 0
    for row in scores:
        width = len(row["roles"])
        stat = score_cell(reference[cursor:cursor + width], candidate[cursor:cursor + width],
                          atol=caps["atol"], relative_l2_cap=caps["relative_l2"], cosine_cap=caps["cosine_distance"], strict_zero_failures=True)
        if stat != row["score"] or stat["status"] != "PASS":
            raise RuntimeError("fresh GUM sentinel pair score drift")
        if canonical_array_hash(np.ascontiguousarray(reference[cursor:cursor + width])) != row["reference_rows_sha256"] or canonical_array_hash(np.ascontiguousarray(candidate[cursor:cursor + width])) != row["candidate_rows_sha256"]:
            raise RuntimeError("fresh GUM sentinel row digest drift")
        cursor += width
    if cursor != 24 or len(scores) != 16:
        raise RuntimeError("fresh GUM sentinel completeness drift")
    return payload


def run_gum(signing_key: Path) -> dict[str, Any]:
    _assert_not_terminal()
    signing_key = signing_key.resolve(strict=True)
    try:
        _verify_implementation_candidate()
        config, _ = _verify_prescore()
        caps = _validation_caps()
        if (RUN_ROOT / "validation/GENTLE_grid").exists():
            raise RuntimeError("GENTLE appeared before fresh GUM")
        device = torch.device("cuda:0")
        with exclusive_lock("attempt-wide-gpu"):
            _seed_runtime(int(config["seed"]))
            model = _load_model(config, device)
            runtime_preflight = _runtime_attestation(model, device, config)
            _extract_sentinel(model, config, device, caps, signing_key, runtime_preflight)
            _extract_grid(model, config, "GUM_fresh_validation", RUN_ROOT / "validation/GUM_grid",
                          device=device, validation_caps=caps, authorization_path=VALIDATION_AUTHORIZATION,
                          signing_key=signing_key, runtime_preflight=runtime_preflight)
        pass_path = RUN_ROOT / "validation/GUM_PASS.json"
        payload = {"schema_version": "atlas_rope_v5_attempt9_source_validation_v1", "status": "PASS", "source": "GUM",
                   "sentinel_complete_sha256": sha256_file(RUN_ROOT / "validation/GUM_sentinel/COMPLETE.json"),
                   "grid_complete_sha256": sha256_file(RUN_ROOT / "validation/GUM_grid/COMPLETE.json"),
                   "validation_authorization_sha256": sha256_file(VALIDATION_AUTHORIZATION),
                   "caps": caps, "gentle_model_calls_authorized_next": True, "science_model_calls_authorized": False,
                   "neural_training_authorized": False}
        if not pass_path.exists():
            write_signed(pass_path, payload, signing_key)
        observed = verify_envelope(read_json(pass_path))
        if observed != payload:
            raise RuntimeError("fresh GUM PASS artifact drift")
        return observed
    except Exception as error:
        _terminalize(signing_key, status="TERMINAL_GUM_VALIDATION_FAILED",
                     reason=f"fresh GUM validation failed: {type(error).__name__}: {error}")
        raise


def run_gentle(signing_key: Path) -> dict[str, Any]:
    _assert_not_terminal()
    signing_key = signing_key.resolve(strict=True)
    try:
        _verify_implementation_candidate()
        config, _ = _verify_prescore()
        caps = _validation_caps()
        gum_pass_path = RUN_ROOT / "validation/GUM_PASS.json"
        gum_pass = verify_envelope(read_json(gum_pass_path))
        if gum_pass.get("status") != "PASS" or gum_pass.get("source") != "GUM":
            raise RuntimeError("fresh GUM did not authorize GENTLE")
        device = torch.device("cuda:0")
        with exclusive_lock("attempt-wide-gpu"):
            _seed_runtime(int(config["seed"]))
            model = _load_model(config, device)
            runtime_preflight = _runtime_attestation(model, device, config)
            _extract_grid(model, config, "GENTLE_validation", RUN_ROOT / "validation/GENTLE_grid",
                          device=device, validation_caps=caps, authorization_path=VALIDATION_AUTHORIZATION,
                          signing_key=signing_key, runtime_preflight=runtime_preflight)
        pass_path = RUN_ROOT / "validation/GENTLE_PASS.json"
        payload = {"schema_version": "atlas_rope_v5_attempt9_source_validation_v1", "status": "PASS", "source": "GENTLE",
                   "grid_complete_sha256": sha256_file(RUN_ROOT / "validation/GENTLE_grid/COMPLETE.json"),
                   "gum_pass_sha256": sha256_file(gum_pass_path), "validation_authorization_sha256": sha256_file(VALIDATION_AUTHORIZATION),
                   "caps": caps, "science_model_calls_authorized_next": True, "neural_training_authorized": False}
        if not pass_path.exists():
            write_signed(pass_path, payload, signing_key)
        observed = verify_envelope(read_json(pass_path))
        if observed != payload:
            raise RuntimeError("GENTLE PASS artifact drift")
        return observed
    except Exception as error:
        _terminalize(signing_key, status="TERMINAL_GENTLE_VALIDATION_FAILED",
                     reason=f"GENTLE validation failed: {type(error).__name__}: {error}")
        raise


def authorize_science(signing_key: Path) -> dict[str, Any]:
    _assert_not_terminal()
    _verify_prescore()
    gum = verify_envelope(read_json(RUN_ROOT / "validation/GUM_PASS.json"))
    gentle = verify_envelope(read_json(RUN_ROOT / "validation/GENTLE_PASS.json"))
    if gum.get("status") != "PASS" or gentle.get("status") != "PASS":
        raise RuntimeError("dual held-out validation did not pass")
    if SCIENCE_AUTHORIZATION.exists():
        raise RuntimeError("science authorization is create-once")
    implementation = _verify_implementation_candidate()
    freeze = read_json(FREEZE_CANDIDATE)
    if freeze.get("science_adapter") != implementation["science_adapter"]:
        raise RuntimeError("validation freeze did not bind the reviewed science adapter")
    payload = {"schema_version": AUTH_SCHEMA, "status": "AUTHORIZED", "authorized_stage": "UNCHANGED_SCIENTIFIC_ATLAS",
               "prescore_config_sha256": sha256_file(CONFIG_PATH), "prescore_manifest_sha256": sha256_file(DATA_ROOT / "manifest.json"),
               "validation_authorization_sha256": sha256_file(VALIDATION_AUTHORIZATION),
               "gum_pass_sha256": sha256_file(RUN_ROOT / "validation/GUM_PASS.json"),
               "gentle_pass_sha256": sha256_file(RUN_ROOT / "validation/GENTLE_PASS.json"),
               "implementation_candidate_sha256": sha256_file(IMPLEMENTATION_CANDIDATE),
               "science_adapter": implementation["science_adapter"],
               "calibration_cap_candidate_sha256": sha256_file(CALIBRATION_CAP_CANDIDATE),
               "scientific_protocol_changes_authorized": False, "neural_training_authorized": False}
    write_signed(SCIENCE_AUTHORIZATION, payload, signing_key)
    return _verify_authorization(SCIENCE_AUTHORIZATION, stage="UNCHANGED_SCIENTIFIC_ATLAS")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("stage", choices=("make-implementation-candidate", "retire-attempt8",
                                          "import-calibration", "make-calibration-cap-candidate",
                                          "authorize-ewt-diagnostic", "make-freeze-candidate",
                                          "authorize-validation", "run-gum", "run-gentle", "authorize-science"))
    parser.add_argument("--signing-key", type=Path)
    parser.add_argument("--review", type=Path)
    parser.add_argument("--verification-report", type=Path)
    args = parser.parse_args()
    if args.stage == "make-implementation-candidate":
        if args.verification_report is None:
            raise RuntimeError("make-implementation-candidate requires a verification report")
        result = make_implementation_candidate(args.verification_report)
    elif args.stage == "retire-attempt8":
        if args.signing_key is None or args.review is None:
            raise RuntimeError("retire-attempt8 requires signing key and implementation review")
        result = retire_attempt8(args.signing_key, args.review)
    elif args.stage == "import-calibration":
        if args.signing_key is None:
            raise RuntimeError("import-calibration requires signing key")
        result = import_attempt8_calibration(args.signing_key)
    elif args.stage == "make-calibration-cap-candidate":
        if args.signing_key is None:
            raise RuntimeError("make-calibration-cap-candidate requires signing key")
        result = make_calibration_cap_candidate(args.signing_key)
    elif args.stage == "authorize-ewt-diagnostic":
        if args.signing_key is None or args.review is None:
            raise RuntimeError("authorize-ewt-diagnostic requires signing key and implementation review")
        result = authorize_ewt(args.signing_key, args.review)
    elif args.stage == "make-freeze-candidate":
        if args.signing_key is None:
            raise RuntimeError("make-freeze-candidate requires signing key for fail-closed terminalization")
        result = make_freeze_candidate(args.signing_key)
    elif args.stage == "authorize-validation":
        if args.signing_key is None or args.review is None:
            raise RuntimeError("authorize-validation requires signing key and freeze review")
        result = authorize_validation(args.signing_key, args.review)
    elif args.stage == "run-gum":
        if args.signing_key is None:
            raise RuntimeError("run-gum requires signing key")
        result = run_gum(args.signing_key)
    elif args.stage == "run-gentle":
        if args.signing_key is None:
            raise RuntimeError("run-gentle requires signing key")
        result = run_gentle(args.signing_key)
    else:
        if args.signing_key is None:
            raise RuntimeError("authorize-science requires signing key")
        result = authorize_science(args.signing_key)
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
