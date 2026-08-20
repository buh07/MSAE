#!/usr/bin/env python3
"""Attempt-11 governance, development, and one-shot technical validation."""
from __future__ import annotations

import argparse
import ast
import copy
import json
import os
import re
import shutil
import sys
import time
from pathlib import Path
from typing import Any, Mapping, Sequence

os.environ.setdefault("CUBLAS_WORKSPACE_CONFIG", ":4096:8")
import numpy as np
import torch

sys.path.insert(0, str(Path(__file__).resolve().parent))

import analyze_atlas_rope_v7_development as development
import diagnose_atlas_rope_v7 as hook_study
import run_atlas_rope_v5 as runtime
from atlas_rope_v6 import validate_grid_units
from atlas_rope_v7 import (
    ATTEMPT10_TERMINAL,
    CONFIG_ROOT,
    DATA_ROOT,
    PANEL_NAMES,
    RESULT_ROOT,
    ROOT,
    RUN_ROOT,
    atomic_json,
    cache_round_trip,
    cross_panel_status,
    gate_contract,
    new_staging,
    promote,
    read_json,
    read_jsonl,
    recursive_inventory,
    score_grid,
    sha256_file,
    verify_attempt10_terminal,
    verify_envelope,
    write_signed,
)

AMENDMENT = CONFIG_ROOT / "amendment.json"
SOURCES = CONFIG_ROOT / "sources.json"
IMPLEMENTATION_CANDIDATE = CONFIG_ROOT / "implementation_candidate.json"
DEVELOPMENT_AUTHORIZATION = CONFIG_ROOT / "DEVELOPMENT_AUTHORIZATION.json"
FREEZE_CANDIDATE = CONFIG_ROOT / "validation_freeze_candidate.json"
VALIDATION_AUTHORIZATION = CONFIG_ROOT / "VALIDATION_AUTHORIZATION.json"
SCIENCE_AUTHORIZATION = CONFIG_ROOT / "SCIENCE_AUTHORIZATION.json"
RETIREMENT = RUN_ROOT / "provenance/ATTEMPT10_RETIRED.json"
DEVELOPMENT_ROOT = RUN_ROOT / "development"
TERMINAL = RUN_ROOT / "TERMINAL.json"
MODEL_CONFIG = ROOT / "configs/atlas_rope_v5/prescore.json"

IMPLEMENTATION_PATHS = (
    "PLAN_ATTEMPT11.md",
    "requirements-atlas.lock.txt",
    "configs/atlas_rope_v7/amendment.json",
    "configs/atlas_rope_v7/sources.json",
    "scripts/atlas_rope_v7.py",
    "scripts/build_atlas_rope_v7.py",
    "scripts/analyze_atlas_rope_v7_development.py",
    "scripts/diagnose_atlas_rope_v7.py",
    "scripts/run_atlas_rope_v7.py",
    "scripts/run_atlas_rope_v7_science.py",
    "scripts/run_atlas_rope_v7_development.sh",
    "scripts/run_atlas_rope_v7_pipeline.sh",
    "scripts/launch_atlas_rope_v7_tmux.sh",
    "tests/test_atlas_rope_v7.py",
    "data/atlas_rope_v7_attempt11/manifest.json",
    "data/atlas_rope_v7_attempt11/ENGLISH_CHILDES_CTETEX/panel.json",
    "data/atlas_rope_v7_attempt11/CZECH_PDT/panel.json",
    "data/atlas_rope_v7_attempt11_rejected_scouting/REJECTION.json",
    "reports/atlas_rope_v7/preinference_superseded_81507aa3590a/SUPERSESSION.json",
)
RUNTIME_CONFIG_PATHS = (
    "configs/atlas_rope_v5/prescore.json",
    "configs/atlas_rope_v6/science_adapter.json",
)


def _verify_amendment() -> dict[str, Any]:
    value = read_json(AMENDMENT)
    if (
        value.get("schema_version") != "atlas_rope_v7_attempt11_amendment_v1"
        or value.get("status") != "FROZEN_PLAN_INPUT"
        or value.get("gate") != gate_contract()
        or value.get("fresh_validation_order") != list(PANEL_NAMES)
        or value.get("neural_training_authorized") is not False
        or sha256_file(MODEL_CONFIG) != value.get("model_config_sha256")
    ):
        raise RuntimeError("Attempt-11 amendment contract drift")
    verify_attempt10_terminal()
    return value


def _assert_not_terminal() -> None:
    if TERMINAL.exists():
        try:
            payload = verify_envelope(read_json(TERMINAL))
            status = payload.get("status")
        except Exception as error:
            raise RuntimeError("Attempt-11 has an unreadable terminal and is fail-closed") from error
        raise RuntimeError(f"Attempt-11 is terminal and cannot resume: {status}")


def _file_inventory(paths: Sequence[str]) -> dict[str, dict[str, Any]]:
    output = {}
    for raw in paths:
        path = ROOT / raw
        if not path.is_file() or path.is_symlink():
            raise RuntimeError(f"implementation file absent/nonregular: {raw}")
        output[raw] = {"bytes": path.stat().st_size, "sha256": sha256_file(path)}
    return output


def _local_dependency_paths(path: Path) -> tuple[str, ...]:
    scripts = path / "scripts"
    modules = {candidate.stem: candidate for candidate in scripts.glob("*.py") if candidate.is_file() and not candidate.is_symlink()}
    queue = [path / raw for raw in IMPLEMENTATION_PATHS if raw.endswith(".py")]
    seen: set[Path] = set()
    while queue:
        source = queue.pop()
        source = source.resolve(strict=True)
        if source in seen:
            continue
        seen.add(source)
        tree = ast.parse(source.read_text(encoding="utf-8"), filename=str(source))
        names: set[str] = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                names.update(alias.name.split(".", 1)[0] for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                names.add(node.module.split(".", 1)[0])
        queue.extend(modules[name] for name in sorted(names) if name in modules)
    implementation = {str(raw) for raw in IMPLEMENTATION_PATHS}
    return tuple(sorted(str(source.relative_to(path)) for source in seen if str(source.relative_to(path)) not in implementation))


def _runtime_dependency_paths(path: Path = ROOT) -> tuple[str, ...]:
    return tuple(sorted(set(_local_dependency_paths(path)) | set(RUNTIME_CONFIG_PATHS)))


def _tree_has_forbidden_training(path: Path) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []

    def dotted(node: ast.AST) -> str:
        if isinstance(node, ast.Name):
            return node.id
        if isinstance(node, ast.Attribute):
            prefix = dotted(node.value)
            return f"{prefix}.{node.attr}" if prefix else node.attr
        return ""

    reviewed_paths = tuple(sorted(set(IMPLEMENTATION_PATHS) | set(_runtime_dependency_paths(path))))
    for raw in reviewed_paths:
        source_path = path / raw
        if raw.endswith(".sh"):
            for line_number, line in enumerate(source_path.read_text(encoding="utf-8").splitlines(), start=1):
                command = line.strip().lower()
                if any(token in command for token in ("train_msae", "scripts/train", "torchrun")):
                    findings.append({"path": raw, "line": line_number, "construct": "training shell command"})
            continue
        if not raw.endswith(".py"):
            continue
        tree = ast.parse(source_path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, (ast.Import, ast.ImportFrom)):
                modules = [alias.name for alias in node.names] if isinstance(node, ast.Import) else [str(node.module or "")]
                if any(module == "torch.optim" or module.startswith("torch.optim.") or module == "torch.autograd" or module.startswith("torch.autograd.") for module in modules):
                    findings.append({"path": raw, "line": node.lineno, "construct": "training module import"})
            if not isinstance(node, ast.Call):
                continue
            call = dotted(node.func)
            leaf = call.rsplit(".", 1)[-1]
            if call.startswith(("torch.optim", "torch.autograd")) or leaf in {"backward", "step", "zero_grad", "save_pretrained"} or call == "torch.save":
                findings.append({"path": raw, "line": node.lineno, "construct": call})
            if leaf == "requires_grad_" and (not node.args or not isinstance(node.args[0], ast.Constant) or node.args[0].value is not False):
                findings.append({"path": raw, "line": node.lineno, "construct": "requires_grad_ not frozen"})
    return findings


def make_implementation_candidate(verification_report: Path) -> dict[str, Any]:
    _verify_amendment()
    if IMPLEMENTATION_CANDIDATE.exists() or RUN_ROOT.exists():
        raise RuntimeError("implementation candidate must precede Attempt-11 run artifacts")
    verification_report = verification_report.resolve(strict=True)
    report = read_json(verification_report)
    if report.get("status") != "PASS":
        raise RuntimeError("implementation verification did not pass")
    inventory = _file_inventory(IMPLEMENTATION_PATHS)
    training = _tree_has_forbidden_training(ROOT)
    if training:
        raise RuntimeError(f"training primitive found: {training}")
    data_manifest = read_json(DATA_ROOT / "manifest.json")
    if data_manifest.get("model_inference_performed") is not False:
        raise RuntimeError("fresh panel manifest claims prior inference")
    payload = {
        "schema_version": "atlas_rope_v7_attempt11_implementation_candidate_v1",
        "status": "READY_FOR_ADVERSARIAL_REVIEW",
        "implementation_inventory": inventory,
        "runtime_dependency_inventory": _file_inventory(_runtime_dependency_paths(ROOT)),
        "verification_report": {"path": str(verification_report.relative_to(ROOT)), "sha256": sha256_file(verification_report)},
        "fresh_panel_tree_inventory": recursive_inventory(DATA_ROOT),
        "validation_outputs_absent": all(not (RUN_ROOT / "validation" / panel).exists() for panel in PANEL_NAMES),
        "rejected_pud_runtime_authorized": False,
        "neural_training_authorized": False,
    }
    atomic_json(IMPLEMENTATION_CANDIDATE, payload)
    return payload


def _verify_candidate() -> dict[str, Any]:
    value = read_json(IMPLEMENTATION_CANDIDATE)
    if (
        value.get("status") != "READY_FOR_ADVERSARIAL_REVIEW"
        or value.get("implementation_inventory") != _file_inventory(IMPLEMENTATION_PATHS)
        or value.get("runtime_dependency_inventory") != _file_inventory(_runtime_dependency_paths(ROOT))
    ):
        raise RuntimeError("reviewed implementation candidate drift")
    if value.get("fresh_panel_tree_inventory") != recursive_inventory(DATA_ROOT):
        raise RuntimeError("reviewed fresh panel tree drift")
    return value


def _review_ship(review: Path, artifact: Path) -> dict[str, str]:
    review = review.resolve(strict=True)
    digest = sha256_file(artifact)
    text = review.read_text(encoding="utf-8")
    if re.findall(r"(?m)^VERDICT:\s*(SHIP|REVISE|BLOCK)\s*$", text) != ["SHIP"] or digest not in text:
        raise RuntimeError(f"review does not SHIP exact artifact {digest}")
    return {"path": str(review.relative_to(ROOT)), "sha256": sha256_file(review), "reviewed_sha256": digest}


def _verify_review_binding(binding: Mapping[str, Any], artifact: Path) -> None:
    review = ROOT / str(binding.get("path", ""))
    if (
        not review.is_file()
        or sha256_file(review) != binding.get("sha256")
        or sha256_file(artifact) != binding.get("reviewed_sha256")
        or re.findall(r"(?m)^VERDICT:\s*(SHIP|REVISE|BLOCK)\s*$", review.read_text(encoding="utf-8")) != ["SHIP"]
    ):
        raise RuntimeError("review binding drift")


def _verify_development_authorization() -> dict[str, Any]:
    payload = _verify_authorization(DEVELOPMENT_AUTHORIZATION, "OPENED_TECHNICAL_DEVELOPMENT_ONLY")
    _verify_candidate()
    if (
        payload.get("implementation_candidate_sha256") != sha256_file(IMPLEMENTATION_CANDIDATE)
        or payload.get("opened_sources") != ["EWT", "GUM", "GENTLE"]
        or payload.get("fresh_validation_model_calls_authorized") is not False
        or payload.get("threshold_change_authorized") is not False
    ):
        raise RuntimeError("development authorization lineage/permission drift")
    _verify_review_binding(payload.get("review", {}), IMPLEMENTATION_CANDIDATE)
    return payload


def _verify_freeze_candidate() -> dict[str, Any]:
    value = read_json(FREEZE_CANDIDATE)
    verify_development()
    expected = {
        "implementation_candidate_sha256": sha256_file(IMPLEMENTATION_CANDIDATE),
        "development_complete_sha256": sha256_file(DEVELOPMENT_ROOT / "COMPLETE.json"),
        "development_threshold_changed": False,
        "gate_contract": gate_contract(),
        "validation_order": list(PANEL_NAMES),
        "panel_manifests": {panel: sha256_file(DATA_ROOT / panel / "panel.json") for panel in PANEL_NAMES},
        "panel_tree_inventory": recursive_inventory(DATA_ROOT),
        "field_dependency_overlay_schema": "atlas_rope_v7_attempt11_technical_eligibility_overlay_v1",
        "pud_forbidden": True, "fresh_values_used": False, "validation_attempts": 1,
        "science_semantics_changed": False, "neural_training_authorized": False,
    }
    if value.get("schema_version") != "atlas_rope_v7_attempt11_validation_freeze_v1" or value.get("status") != "READY_FOR_ADVERSARIAL_REVIEW":
        raise RuntimeError("freeze candidate identity drift")
    if any(value.get(key) != expected_value for key, expected_value in expected.items()):
        raise RuntimeError("freeze candidate complete binding drift")
    _verify_candidate()
    return value


def _verify_validation_authorization() -> dict[str, Any]:
    payload = _verify_authorization(VALIDATION_AUTHORIZATION, "ONE_SHOT_FRESH_TECHNICAL_VALIDATION")
    _verify_freeze_candidate()
    if (
        payload.get("freeze_candidate_sha256") != sha256_file(FREEZE_CANDIDATE)
        or payload.get("panels") != list(PANEL_NAMES)
        or payload.get("attempts_per_panel") != 1
        or payload.get("gate_contract") != gate_contract()
        or not str(payload.get("gpu_uuid", "")).startswith("GPU-")
        or payload.get("threshold_change_authorized") is not False
        or payload.get("pud_runtime_authorized") is not False
        or payload.get("science_model_calls_authorized") is not False
    ):
        raise RuntimeError("validation authorization lineage/permission drift")
    _verify_review_binding(payload.get("review", {}), FREEZE_CANDIDATE)
    return payload


def _verify_science_authorization() -> dict[str, Any]:
    payload = _verify_authorization(SCIENCE_AUTHORIZATION, "EXPLORATORY_FROZEN_SCIENCE_WITH_ELIGIBILITY_OVERLAY")
    validation_authorization = _verify_validation_authorization(); _verify_candidate()
    panels = {panel: verify_panel(panel) for panel in PANEL_NAMES}
    expected_hashes = {panel: sha256_file(RUN_ROOT / "validation" / panel / "COMPLETE.json") for panel in PANEL_NAMES}
    if (
        payload.get("panel_complete_sha256") != expected_hashes
        or payload.get("cross_panel") != cross_panel_status(panels)
        or payload.get("implementation_candidate_sha256") != sha256_file(IMPLEMENTATION_CANDIDATE)
        or payload.get("validation_authorization_sha256") != sha256_file(VALIDATION_AUTHORIZATION)
        or payload.get("gpu_uuid") != validation_authorization.get("gpu_uuid")
        or payload.get("frozen_science_semantics_changed") is not False
        or payload.get("pud_runtime_authorized") is not False
    ):
        raise RuntimeError("science authorization complete lineage drift")
    return payload


def authorize_development(signing_key: Path, review: Path) -> dict[str, Any]:
    _assert_not_terminal(); _verify_amendment(); _verify_candidate()
    with lifecycle_lock():
        _assert_not_terminal(); _verify_amendment(); _verify_candidate()
        if DEVELOPMENT_AUTHORIZATION.exists():
            raise RuntimeError("development authorization is create-once")
        if any(path.exists() for path in (RETIREMENT, DEVELOPMENT_ROOT, RUN_ROOT / "validation")):
            raise RuntimeError("development authorization must precede Attempt-11 run artifacts")
        payload = {
        "schema_version": "atlas_rope_v7_attempt11_authorization_v1", "status": "AUTHORIZED",
        "authorized_stage": "OPENED_TECHNICAL_DEVELOPMENT_ONLY",
        "implementation_candidate_sha256": sha256_file(IMPLEMENTATION_CANDIDATE),
        "review": _review_ship(review, IMPLEMENTATION_CANDIDATE),
        "opened_sources": ["EWT", "GUM", "GENTLE"], "fresh_validation_model_calls_authorized": False,
        "threshold_change_authorized": False, "neural_training_authorized": False,
        }
        write_signed(DEVELOPMENT_AUTHORIZATION, payload, signing_key.resolve(strict=True))
    return _verify_development_authorization()


def _verify_authorization(path: Path, stage: str) -> dict[str, Any]:
    payload = verify_envelope(read_json(path))
    if payload.get("status") != "AUTHORIZED" or payload.get("authorized_stage") != stage or payload.get("neural_training_authorized") is not False:
        raise RuntimeError("authorization identity drift")
    return payload


def _attempt10_terminal_reference() -> dict[str, str]:
    verify_attempt10_terminal()
    envelope = read_json(ATTEMPT10_TERMINAL)
    return {
        "path": str(ATTEMPT10_TERMINAL.relative_to(ROOT)),
        "sha256": sha256_file(ATTEMPT10_TERMINAL),
        "message_sha256": str(envelope["signature"]["message_sha256"]),
    }


def retire_attempt10(signing_key: Path) -> dict[str, Any]:
    _assert_not_terminal(); _verify_development_authorization()
    with lifecycle_lock():
        _assert_not_terminal(); _verify_development_authorization()
        if RETIREMENT.exists():
            return verify_retirement()
        payload = {
            "schema_version": "atlas_rope_v7_attempt11_attempt10_retirement_v1", "status": "RETIRED_NO_RETRY",
            "attempt10_terminal": _attempt10_terminal_reference(),
            "no_retry_authorized": True, "threshold_change_for_attempt10_authorized": False,
            "attempt10_science_authorized": False, "neural_training_authorized": False,
        }
        write_signed(RETIREMENT, payload, signing_key.resolve(strict=True))
        return verify_retirement()


def verify_retirement() -> dict[str, Any]:
    payload = verify_envelope(read_json(RETIREMENT))
    expected_terminal = _attempt10_terminal_reference()
    if (
        payload.get("schema_version") != "atlas_rope_v7_attempt11_attempt10_retirement_v1"
        or payload.get("status") != "RETIRED_NO_RETRY"
        or payload.get("attempt10_terminal") != expected_terminal
        or payload.get("no_retry_authorized") is not True
        or payload.get("threshold_change_for_attempt10_authorized") is not False
        or payload.get("attempt10_science_authorized") is not False
        or payload.get("neural_training_authorized") is not False
    ):
        raise RuntimeError("Attempt-10 retirement drift")
    return payload


def verify_development() -> dict[str, Any]:
    _assert_not_terminal(); _verify_development_authorization(); _verify_candidate(); verify_retirement()
    entries = list(DEVELOPMENT_ROOT.iterdir())
    expected_names = {"COMPLETE.json", "cache_and_sensitivity.json", "gentle_outlier_hook.json"}
    if {path.name for path in entries} != expected_names or any(not path.is_file() or path.is_symlink() for path in entries):
        raise RuntimeError("Attempt-11 development allowlist drift")
    payload = verify_envelope(read_json(DEVELOPMENT_ROOT / "COMPLETE.json"))
    artifacts = {
        name: {"bytes": (DEVELOPMENT_ROOT / name).stat().st_size, "sha256": sha256_file(DEVELOPMENT_ROOT / name)}
        for name in sorted(expected_names - {"COMPLETE.json"})
    }
    offline = read_json(DEVELOPMENT_ROOT / "cache_and_sensitivity.json")
    hook = read_json(DEVELOPMENT_ROOT / "gentle_outlier_hook.json")
    diagnoses = offline.get("opened_cache_diagnosis", {})
    sensitivity = offline.get("sensitivity", {})
    hook_records = hook.get("records", [])
    required_tasks = {"relative_quartile", "head_signed_distance", "deprel_coarse", "dependency_depth", "token_identity_v2"}
    diagnosis_complete = set(diagnoses) == {"EWT", "GUM", "GENTLE"} and all(
        all(key in source for key in ("by_shift", "by_length_bin", "by_selected_position", "by_reference_norm_quintile", "row_records"))
        and len(source["row_records"]) == 1200
        for source in diagnoses.values()
    )
    sensitivity_complete = (
        sensitivity.get("learned_and_nonlinear_v3_3_endpoints") == "not_certified_by_v2_4_sensitivity"
        and sensitivity.get("preexisting_labels", {}).get("architecture_outcome", {}).get("sensitivity_status") == "not_certified_by_v2_4_sensitivity"
        and all(set(scale.get("task_stability", {})) == required_tasks for scale in sensitivity.get("scales", {}).values())
        and set(sensitivity.get("scales", {})) == {"2e-05", "5e-05"}
    )
    hook_complete = all(
        {int(row["shift"]) for row in hook_records if row.get("stage") == stage} == {0, 1, 4, 8, 16, 32, 64}
        for stage in ("pre_rotary_qk", "float32_vs_float64_rotary", "inverse_aligned_post_rotary", "attention_logits", "hidden_state")
    )
    if (
        payload.get("schema_version") != "atlas_rope_v7_attempt11_development_complete_v1"
        or payload.get("status") != "COMPLETE"
        or payload.get("source_role") != "OPENED_TECHNICAL_DEVELOPMENT"
        or payload.get("sources") != ["EWT", "GUM", "GENTLE"]
        or payload.get("artifacts") != artifacts
        or payload.get("implementation_candidate_sha256") != sha256_file(IMPLEMENTATION_CANDIDATE)
        or payload.get("development_authorization_sha256") != sha256_file(DEVELOPMENT_AUTHORIZATION)
        or payload.get("gate_contract") != gate_contract()
        or payload.get("threshold_or_budget_changed") is not False
        or payload.get("fresh_validation_values_used") is not False
        or payload.get("neural_training_run") is not False
        or offline.get("schema_version") != "atlas_rope_v7_attempt11_opened_development_v1"
        or offline.get("status") != "COMPLETE"
        or offline.get("validation_sources_used") != []
        or offline.get("threshold_or_budget_changed") is not False
        or not diagnosis_complete
        or not sensitivity_complete
        or hook.get("schema_version") != "atlas_rope_v7_attempt11_gentle_outlier_diagnosis_v1"
        or hook.get("status") != "COMPLETE"
        or hook.get("shifts") != [0, 1, 4, 8, 16, 32, 64]
        or hook.get("runtime_preflight") != hook.get("runtime_postflight")
        or not hook_complete
        or hook.get("neural_training_run") is not False
    ):
        raise RuntimeError("Attempt-11 development artifact/lineage drift")
    return payload


def run_development(signing_key: Path, gpu_uuid: str) -> dict[str, Any]:
    _assert_not_terminal(); _verify_development_authorization(); _verify_candidate(); verify_retirement()
    with exclusive_gpu_lock("stage-opened-development"):
        with lifecycle_lock():
            _assert_not_terminal(); _verify_development_authorization(); _verify_candidate(); verify_retirement()
            if DEVELOPMENT_ROOT.exists():
                return verify_development()
            stage = new_staging("opened-development", sha256_file(DEVELOPMENT_AUTHORIZATION))
        started = time.time()
        offline = development.run()
        atomic_json(stage / "cache_and_sensitivity.json", offline)
        with exclusive_gpu_lock("attempt-wide-gpu"):
            _assert_not_terminal(); _verify_development_authorization()
            hook = hook_study.run(gpu_uuid)
        atomic_json(stage / "gentle_outlier_hook.json", hook)
        payload = {
        "schema_version": "atlas_rope_v7_attempt11_development_complete_v1", "status": "COMPLETE",
        "source_role": "OPENED_TECHNICAL_DEVELOPMENT", "sources": ["EWT", "GUM", "GENTLE"],
        "artifacts": {path.name: {"bytes": path.stat().st_size, "sha256": sha256_file(path)} for path in stage.iterdir()},
        "implementation_candidate_sha256": sha256_file(IMPLEMENTATION_CANDIDATE),
        "development_authorization_sha256": sha256_file(DEVELOPMENT_AUTHORIZATION),
        "gate_contract": gate_contract(), "threshold_or_budget_changed": False,
        "fresh_validation_values_used": False, "elapsed_seconds": time.time() - started,
        "parameter_update_run": False, "checkpoint_created": False, "neural_training_run": False,
        }
        with lifecycle_lock():
            _assert_not_terminal(); _verify_development_authorization(); _verify_candidate(); verify_retirement()
            write_signed(stage / "COMPLETE.json", payload, signing_key.resolve(strict=True))
            promote(stage, DEVELOPMENT_ROOT)
            return verify_development()


def make_freeze_candidate() -> dict[str, Any]:
    _assert_not_terminal(); _verify_development_authorization(); _verify_candidate()
    with lifecycle_lock():
        _assert_not_terminal(); _verify_development_authorization(); _verify_candidate()
        development_complete = verify_development()
        if FREEZE_CANDIDATE.exists():
            raise RuntimeError("freeze candidate is create-once")
        if (RUN_ROOT / "validation").exists():
            raise RuntimeError("validation output exists before freeze")
        payload = {
            "schema_version": "atlas_rope_v7_attempt11_validation_freeze_v1", "status": "READY_FOR_ADVERSARIAL_REVIEW",
            "implementation_candidate_sha256": sha256_file(IMPLEMENTATION_CANDIDATE),
            "development_complete_sha256": sha256_file(DEVELOPMENT_ROOT / "COMPLETE.json"),
            "development_threshold_changed": development_complete.get("threshold_or_budget_changed"),
            "gate_contract": gate_contract(), "validation_order": list(PANEL_NAMES),
            "panel_manifests": {panel: sha256_file(DATA_ROOT / panel / "panel.json") for panel in PANEL_NAMES},
            "panel_tree_inventory": recursive_inventory(DATA_ROOT),
            "field_dependency_overlay_schema": "atlas_rope_v7_attempt11_technical_eligibility_overlay_v1",
            "pud_forbidden": True, "fresh_values_used": False, "validation_attempts": 1,
            "science_semantics_changed": False, "neural_training_authorized": False,
        }
        atomic_json(FREEZE_CANDIDATE, payload)
        return payload


def authorize_validation(signing_key: Path, review: Path, gpu_uuid: str) -> dict[str, Any]:
    _assert_not_terminal(); _verify_candidate(); _verify_freeze_candidate()
    with lifecycle_lock():
        _assert_not_terminal()
        if VALIDATION_AUTHORIZATION.exists():
            raise RuntimeError("validation authorization is create-once")
        if (RUN_ROOT / "validation").exists():
            raise RuntimeError("validation already opened")
        payload = {
        "schema_version": "atlas_rope_v7_attempt11_authorization_v1", "status": "AUTHORIZED",
        "authorized_stage": "ONE_SHOT_FRESH_TECHNICAL_VALIDATION",
        "freeze_candidate_sha256": sha256_file(FREEZE_CANDIDATE), "review": _review_ship(review, FREEZE_CANDIDATE),
        "gpu_uuid": gpu_uuid, "panels": list(PANEL_NAMES), "attempts_per_panel": 1,
        "gate_contract": gate_contract(), "threshold_change_authorized": False,
        "pud_runtime_authorized": False, "science_model_calls_authorized": False,
        "neural_training_authorized": False,
        }
        write_signed(VALIDATION_AUTHORIZATION, payload, signing_key.resolve(strict=True))
    return _verify_validation_authorization()


def _panel(panel: str) -> tuple[dict[str, Any], list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    if panel not in PANEL_NAMES:
        raise RuntimeError("unknown panel")
    root = DATA_ROOT / panel
    manifest = read_json(root / "panel.json")
    if manifest.get("status") != "FROZEN_UNOPENED" or manifest.get("panel") != panel:
        raise RuntimeError("panel identity drift")
    for name, spec in manifest["children"].items():
        path = root / name
        if path.stat().st_size != spec["bytes"] or sha256_file(path) != spec["sha256"]:
            raise RuntimeError("panel child drift")
    references, candidates, rows = read_jsonl(root / "references.jsonl"), read_jsonl(root / "candidates.jsonl"), read_jsonl(root / "rows.jsonl")
    validate_grid_units(references, candidates, rows, source=panel)
    if any("PUD" in json.dumps(value) for value in (manifest, references, candidates, rows)):
        raise RuntimeError("rejected PUD appears in validation panel")
    return manifest, references, candidates, rows


def _write_array(path: Path, value: np.ndarray) -> None:
    np.save(path, np.ascontiguousarray(value, dtype=np.float32), allow_pickle=False)
    with path.open("rb") as handle:
        os.fsync(handle.fileno())


def verify_panel(panel: str) -> dict[str, Any]:
    _assert_not_terminal(); _verify_validation_authorization(); _verify_candidate()
    _, references, candidates, rows = _panel(panel)
    root = RUN_ROOT / "validation" / panel
    array_names = {
        "reference.float32.npy",
        "reference_repeat_1.float32.npy",
        "reference_repeat_2.float32.npy",
        "candidate.float32.npy",
        "reference_cache_roundtrip.float32.npy",
    }
    expected_names = array_names | {"row_ids.json", "COMPLETE.json"}
    entries = list(root.iterdir())
    if {path.name for path in entries} != expected_names or any(not path.is_file() or path.is_symlink() for path in entries):
        raise RuntimeError(f"{panel} validation allowlist drift")
    payload = verify_envelope(read_json(root / "COMPLETE.json"))
    artifacts = {
        name: {"bytes": (root / name).stat().st_size, "sha256": sha256_file(root / name)}
        for name in sorted(expected_names - {"COMPLETE.json"})
    }
    arrays = {name: np.load(root / name, allow_pickle=False) for name in array_names}
    expected_shapes = {name: ((1200, 768) if name == "candidate.float32.npy" else (200, 768)) for name in array_names}
    expected_ids = {
        "reference": [str(row["row_id"]) for row in rows],
        "candidate": [str(row_id) for unit in candidates for row_id in unit["row_ids"]],
    }
    observed_ids = read_json(root / "row_ids.json")
    roundtrip = cache_round_trip(
        root / "reference.float32.npy",
        root / "reference_cache_roundtrip.float32.npy",
        expected_ids["reference"],
        observed_ids.get("reference", []),
    )
    references_live = [arrays["reference.float32.npy"], arrays["reference_repeat_1.float32.npy"], arrays["reference_repeat_2.float32.npy"]]
    repeat_exact = all(np.array_equal(references_live[0], value) and references_live[0].tobytes() == value.tobytes() for value in references_live[1:])
    arrays_finite = all(value.shape == expected_shapes[name] and value.dtype == np.float32 and np.isfinite(value).all() for name, value in arrays.items())
    score = score_grid(references_live[0], arrays["candidate.float32.npy"], rows)
    integrity = roundtrip["status"] == "PASS" and repeat_exact and arrays_finite and payload.get("runtime_preflight") == payload.get("runtime_postflight")
    approximate = integrity and score["approximate_equivariance_metric_pass"]
    if (
        observed_ids != expected_ids
        or payload.get("schema_version") != "atlas_rope_v7_attempt11_validation_panel_v1"
        or payload.get("status") != "COMPLETE"
        or payload.get("panel") != panel
        or payload.get("artifacts") != artifacts
        or payload.get("cache_round_trip_integrity") != roundtrip
        or payload.get("live_reference_repeats_byte_identical") is not repeat_exact
        or payload.get("arrays_finite") is not arrays_finite
        or payload.get("runtime_pre_post_exact") is not (payload.get("runtime_preflight") == payload.get("runtime_postflight"))
        or payload.get("score") != score
        or payload.get("integrity_runtime_pass") is not integrity
        or payload.get("approximate_equivariance_pass") is not approximate
        or payload.get("gate_contract") != gate_contract()
        or payload.get("panel_sha256") != sha256_file(DATA_ROOT / panel / "panel.json")
        or payload.get("validation_authorization_sha256") != sha256_file(VALIDATION_AUTHORIZATION)
        or payload.get("implementation_candidate_sha256") != sha256_file(IMPLEMENTATION_CANDIDATE)
        or payload.get("neural_training_run") is not False
    ):
        raise RuntimeError(f"{panel} validation artifact/lineage drift")
    return payload


def run_panel(panel: str, signing_key: Path) -> dict[str, Any]:
    _assert_not_terminal(); auth = _verify_validation_authorization(); _verify_candidate()
    final = RUN_ROOT / "validation" / panel
    with exclusive_gpu_lock("stage-validation-" + panel):
        with lifecycle_lock():
            _assert_not_terminal(); auth = _verify_validation_authorization()
            index = PANEL_NAMES.index(panel)
            if index:
                verify_panel(PANEL_NAMES[index - 1])
            if final.exists():
                return verify_panel(panel)
            manifest, references, candidates, rows = _panel(panel)
            config = copy.deepcopy(read_json(MODEL_CONFIG)); config["runtime"]["gpu_uuid"] = auth["gpu_uuid"]
            stage = new_staging("validation-" + panel, sha256_file(VALIDATION_AUTHORIZATION))
        started = time.time(); device = torch.device("cuda:0")
        with exclusive_gpu_lock("attempt-wide-gpu"):
            _assert_not_terminal(); _verify_validation_authorization()
            runtime._seed_runtime(int(config["seed"])); model = runtime._load_model(config, device)
            preflight = runtime._runtime_attestation(model, device, config)
            repeats = [runtime._forward_units(model, references, device=device, hidden_index=4, batch_size=64) for _ in range(3)]
            shifted = runtime._forward_units(model, candidates, device=device, hidden_index=4, batch_size=64)
            postflight = runtime._runtime_attestation(model, device, config)
        for name, value in (("reference", repeats[0]), ("reference_repeat_1", repeats[1]), ("reference_repeat_2", repeats[2]), ("candidate", shifted)):
            _write_array(stage / f"{name}.float32.npy", value)
        shutil.copyfile(stage / "reference.float32.npy", stage / "reference_cache_roundtrip.float32.npy")
        ids = {"reference": [str(row["row_id"]) for row in rows], "candidate": [str(row_id) for unit in candidates for row_id in unit["row_ids"]]}
        atomic_json(stage / "row_ids.json", ids)
        roundtrip = cache_round_trip(stage / "reference.float32.npy", stage / "reference_cache_roundtrip.float32.npy", ids["reference"], ids["reference"])
        repeat_exact = all(np.array_equal(repeats[0], value) and repeats[0].tobytes() == value.tobytes() for value in repeats[1:])
        arrays_finite = all(np.isfinite(value).all() for value in (*repeats, shifted))
        runtime_match = preflight == postflight
        integrity = roundtrip["status"] == "PASS" and repeat_exact and arrays_finite and runtime_match
        score = score_grid(repeats[0], shifted, rows)
        approximate = integrity and score["approximate_equivariance_metric_pass"]
        artifacts = {path.name: {"bytes": path.stat().st_size, "sha256": sha256_file(path)} for path in stage.iterdir()}
        payload = {
            "schema_version": "atlas_rope_v7_attempt11_validation_panel_v1", "status": "COMPLETE", "panel": panel,
            "integrity_runtime_pass": integrity, "approximate_equivariance_pass": approximate,
            "cache_round_trip_integrity": roundtrip, "live_reference_repeats_byte_identical": repeat_exact,
            "arrays_finite": arrays_finite, "runtime_pre_post_exact": runtime_match, "score": score,
            "gate_contract": gate_contract(), "panel_sha256": sha256_file(DATA_ROOT / panel / "panel.json"),
            "validation_authorization_sha256": sha256_file(VALIDATION_AUTHORIZATION),
            "implementation_candidate_sha256": sha256_file(IMPLEMENTATION_CANDIDATE),
            "runtime_preflight": preflight, "runtime_postflight": postflight,
            "artifacts": artifacts, "elapsed_seconds": time.time() - started,
            "model_eval": True, "inference_mode": True, "requires_grad": False, "labels_loaded": False,
            "estimator_created": False, "parameter_update_run": False, "checkpoint_created": False, "neural_training_run": False,
        }
        with lifecycle_lock():
            _assert_not_terminal(); _verify_validation_authorization()
            write_signed(stage / "COMPLETE.json", payload, signing_key.resolve(strict=True))
            promote(stage, final)
            return verify_panel(panel)


def exclusive_gpu_lock(name: str = "attempt-wide-gpu"):
    from atlas_rope_v7 import exclusive_lock
    return exclusive_lock(name)


def lifecycle_lock():
    return exclusive_gpu_lock("attempt-lifecycle")


def authorize_science(signing_key: Path) -> dict[str, Any]:
    _assert_not_terminal(); _verify_validation_authorization()
    with lifecycle_lock():
        _assert_not_terminal(); _verify_validation_authorization()
        panels = {panel: verify_panel(panel) for panel in PANEL_NAMES}
        if SCIENCE_AUTHORIZATION.exists():
            raise RuntimeError("science authorization is create-once")
        cross = cross_panel_status(panels)
        payload = {
        "schema_version": "atlas_rope_v7_attempt11_authorization_v1", "status": "AUTHORIZED",
        "authorized_stage": "EXPLORATORY_FROZEN_SCIENCE_WITH_ELIGIBILITY_OVERLAY",
        "panel_complete_sha256": {panel: sha256_file(RUN_ROOT / "validation" / panel / "COMPLETE.json") for panel in PANEL_NAMES},
        "cross_panel": cross, "frozen_science_semantics_changed": False,
        "gpu_uuid": verify_envelope(read_json(VALIDATION_AUTHORIZATION))["gpu_uuid"],
        "architecture_promotion_if_rope_fails": "technically_ineligible",
        "implementation_candidate_sha256": sha256_file(IMPLEMENTATION_CANDIDATE),
        "validation_authorization_sha256": sha256_file(VALIDATION_AUTHORIZATION),
        "pud_runtime_authorized": False, "neural_training_authorized": False,
        }
        write_signed(SCIENCE_AUTHORIZATION, payload, signing_key.resolve(strict=True))
    return _verify_science_authorization()


def terminalize(signing_key: Path, status: str, reason: str) -> dict[str, Any]:
    with lifecycle_lock():
        if TERMINAL.exists():
            return verify_envelope(read_json(TERMINAL))
        lineage = {name: {"path": str(path.relative_to(ROOT)), "sha256": sha256_file(path)} for name, path in {
            "development_authorization": DEVELOPMENT_AUTHORIZATION, "development_complete": DEVELOPMENT_ROOT / "COMPLETE.json",
            "validation_authorization": VALIDATION_AUTHORIZATION, "science_authorization": SCIENCE_AUTHORIZATION,
        }.items() if path.is_file()}
        payload = {
            "schema_version": "atlas_rope_v7_attempt11_terminal_v1", "status": status, "reason": reason[:2000],
            "lineage": lineage, "no_retry_authorized": True, "neural_training_authorized": False,
        }
        write_signed(TERMINAL, payload, signing_key.resolve(strict=True))
        return verify_envelope(read_json(TERMINAL))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("stage", choices=("make-implementation-candidate", "authorize-development", "retire-attempt10", "run-development", "make-freeze-candidate", "authorize-validation", "run-panel", "authorize-science", "terminalize"))
    parser.add_argument("--verification-report", type=Path); parser.add_argument("--review", type=Path)
    parser.add_argument("--signing-key", type=Path); parser.add_argument("--gpu-uuid"); parser.add_argument("--panel", choices=PANEL_NAMES)
    parser.add_argument("--terminal-status", default="TERMINAL_PIPELINE_STAGE_FAILED"); parser.add_argument("--reason", default="unspecified failure")
    args = parser.parse_args()
    if args.stage == "make-implementation-candidate":
        if not args.verification_report: raise RuntimeError("verification report required")
        result = make_implementation_candidate(args.verification_report)
    elif args.stage == "make-freeze-candidate": result = make_freeze_candidate()
    else:
        if not args.signing_key: raise RuntimeError("signing key required")
        if args.stage == "authorize-development":
            if not args.review: raise RuntimeError("review required")
            result = authorize_development(args.signing_key, args.review)
        elif args.stage == "retire-attempt10": result = retire_attempt10(args.signing_key)
        elif args.stage == "run-development":
            if not args.gpu_uuid: raise RuntimeError("gpu UUID required")
            result = run_development(args.signing_key, args.gpu_uuid)
        elif args.stage == "authorize-validation":
            if not args.review or not args.gpu_uuid: raise RuntimeError("review and GPU UUID required")
            result = authorize_validation(args.signing_key, args.review, args.gpu_uuid)
        elif args.stage == "run-panel":
            if not args.panel: raise RuntimeError("panel required")
            result = run_panel(args.panel, args.signing_key)
        elif args.stage == "authorize-science": result = authorize_science(args.signing_key)
        else: result = terminalize(args.signing_key, args.terminal_status, args.reason)
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
