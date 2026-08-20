#!/usr/bin/env python3
"""Controller for the one-shot Attempt-12 analysis-only recovery."""
from __future__ import annotations

import argparse
import fcntl
import importlib
import json
import os
import re
import sys
import time
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator, Mapping

os.environ.setdefault("CUBLAS_WORKSPACE_CONFIG", ":4096:8")

sys.path.insert(0, str(Path(__file__).resolve().parent))

from atlas_rope_v6 import (
    atomic_json,
    canonical_json_bytes,
    read_json,
    sha256_bytes,
    sha256_file,
    verify_envelope,
)
from atlas_rope_v8 import (
    ANALYSIS_GPU_UUID,
    ATTEMPT11_ROOT,
    AUTHORIZATION,
    CONFIG_ROOT,
    EXTRACTION_GPU_UUID,
    FROZEN_ADAPTER,
    IMPLEMENTATION_CANDIDATE,
    IMPLEMENTATION_PATHS,
    PANELS,
    PREFLIGHT,
    RECOVERY_CONFIG,
    RECOVERY_FREEZE,
    RESULT_ROOT,
    ROOT,
    RUN_ROOT,
    SOURCES,
    STARTED,
    TERMINAL,
    file_inventory,
    load_recovery_config,
    safe_write_target,
    static_operation_audit,
    verify_all_imports,
    verify_attempt11_terminal,
    verify_cache,
    verify_gpu_mapping,
    verify_qa,
    verify_validation,
    write_signed_local,
)


@contextmanager
def exclusive_lock(name: str) -> Iterator[None]:
    lock_root = RUN_ROOT / "locks"
    safe_write_target(lock_root / "x")
    lock_root.mkdir(parents=True, exist_ok=True)
    descriptor = os.open(lock_root / f"{name}.lock", os.O_CREAT | os.O_RDWR, 0o600)
    try:
        try:
            fcntl.flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as error:
            raise RuntimeError(f"another Attempt-12 process holds {name}") from error
        yield
    finally:
        fcntl.flock(descriptor, fcntl.LOCK_UN)
        os.close(descriptor)


def _assert_no_terminal() -> None:
    if TERMINAL.exists():
        try:
            payload = verify_envelope(read_json(TERMINAL))
            status = payload.get("status")
        except Exception as error:
            raise RuntimeError("Attempt-12 terminal is unreadable; fail closed") from error
        raise RuntimeError(f"Attempt-12 is terminal and cannot resume: {status}")


def _assert_pre_authorization_absence() -> None:
    if any(path.exists() for path in (AUTHORIZATION, STARTED, TERMINAL, RESULT_ROOT)):
        raise RuntimeError("Attempt-12 authorization/start/terminal/result must be absent")


def _assert_pre_start_absence() -> None:
    if any(path.exists() for path in (STARTED, TERMINAL, RESULT_ROOT)):
        raise RuntimeError("Attempt-12 start/terminal/result must be absent")


def _review_ship(review: Path, artifact: Path) -> dict[str, str]:
    review = review.resolve(strict=True)
    digest = sha256_file(artifact)
    text = review.read_text(encoding="utf-8")
    if re.findall(r"(?m)^VERDICT:\s*(SHIP|REVISE|BLOCK)\s*$", text) != ["SHIP"] or digest not in text:
        raise RuntimeError(f"review does not SHIP exact recovery freeze {digest}")
    if not review.is_relative_to(ROOT):
        raise RuntimeError("recovery review must be stored in repository")
    return {"path": str(review.relative_to(ROOT)), "sha256": sha256_file(review), "reviewed_sha256": digest}


def _verify_review(binding: Mapping[str, Any], artifact: Path) -> None:
    path = ROOT / str(binding.get("path", ""))
    if (
        not path.is_file()
        or path.is_symlink()
        or sha256_file(path) != binding.get("sha256")
        or sha256_file(artifact) != binding.get("reviewed_sha256")
        or re.findall(r"(?m)^VERDICT:\s*(SHIP|REVISE|BLOCK)\s*$", path.read_text(encoding="utf-8")) != ["SHIP"]
    ):
        raise RuntimeError("Attempt-12 adversarial review binding drift")


def make_implementation_candidate(verification_report: Path) -> dict[str, Any]:
    load_recovery_config()
    if IMPLEMENTATION_CANDIDATE.exists() or RUN_ROOT.exists() or RESULT_ROOT.exists():
        raise RuntimeError("implementation candidate must precede Attempt-12 run artifacts")
    report_path = verification_report.resolve(strict=True)
    report = read_json(report_path)
    if report.get("status") != "PASS" or not report_path.is_relative_to(ROOT):
        raise RuntimeError("Attempt-12 verification report did not pass")
    current_inventory = file_inventory(IMPLEMENTATION_PATHS)
    if report.get("implementation_inventory") != current_inventory:
        raise RuntimeError("Attempt-12 verification report implementation inventory drift")
    imports = verify_all_imports(deep_cache=True)
    audit = static_operation_audit()
    payload = {
        "schema_version": "atlas_rope_v8_attempt12_implementation_candidate_v1",
        "status": "READY_FOR_SIGNED_PREFLIGHT",
        "implementation_inventory": current_inventory,
        "verification_report": {"path": str(report_path.relative_to(ROOT)), "sha256": sha256_file(report_path)},
        "import_verification": imports,
        "operation_audit": audit,
        "result_namespace_absent": True,
        "attempt11_controller_stage_authorized": False,
        "model_forward_authorized": False,
        "activation_extraction_authorized": False,
        "fresh_validation_authorized": False,
        "neural_training_authorized": False,
    }
    safe_write_target(IMPLEMENTATION_CANDIDATE)
    atomic_json(IMPLEMENTATION_CANDIDATE, payload)
    return payload


def verify_implementation_candidate() -> dict[str, Any]:
    payload = read_json(IMPLEMENTATION_CANDIDATE)
    if (
        payload.get("schema_version") != "atlas_rope_v8_attempt12_implementation_candidate_v1"
        or payload.get("status") != "READY_FOR_SIGNED_PREFLIGHT"
        or payload.get("implementation_inventory") != file_inventory(IMPLEMENTATION_PATHS)
        or payload.get("operation_audit") != static_operation_audit()
        or payload.get("attempt11_controller_stage_authorized") is not False
        or payload.get("model_forward_authorized") is not False
        or payload.get("activation_extraction_authorized") is not False
        or payload.get("fresh_validation_authorized") is not False
        or payload.get("neural_training_authorized") is not False
    ):
        raise RuntimeError("Attempt-12 implementation candidate drift")
    report_spec = payload.get("verification_report", {})
    report = ROOT / str(report_spec.get("path", ""))
    if not report.is_file() or sha256_file(report) != report_spec.get("sha256") or read_json(report).get("status") != "PASS":
        raise RuntimeError("Attempt-12 verification evidence drift")
    return payload


def run_preflight(signing_key: Path) -> dict[str, Any]:
    verify_implementation_candidate()
    _assert_pre_authorization_absence()
    with exclusive_lock("preflight"):
        verify_implementation_candidate()
        _assert_pre_authorization_absence()
        if PREFLIGHT.exists():
            raise RuntimeError("Attempt-12 preflight is create-once")
        imports = verify_all_imports(deep_cache=True)
        gpu = verify_gpu_mapping()
        payload = {
            "schema_version": "atlas_rope_v8_attempt12_preflight_v1",
            "status": "PASS",
            "implementation_candidate_sha256": sha256_file(IMPLEMENTATION_CANDIDATE),
            "recovery_config_sha256": sha256_file(RECOVERY_CONFIG),
            "import_verification": imports,
            "gpu_mapping": gpu,
            "extraction_gpu_uuid": EXTRACTION_GPU_UUID,
            "analysis_gpu_uuid": ANALYSIS_GPU_UUID,
            "result_namespace_absent": True,
            "attempt11_terminal_preserved": True,
            "scientific_scoring_performed": False,
            "model_forward_performed": False,
            "fresh_validation_performed": False,
            "activation_extraction_performed": False,
            "neural_training_run": False,
        }
        safe_write_target(PREFLIGHT)
        write_signed_local(PREFLIGHT, payload, signing_key.resolve(strict=True))
        return verify_preflight()


def verify_preflight() -> dict[str, Any]:
    payload = verify_envelope(read_json(PREFLIGHT))
    if (
        payload.get("schema_version") != "atlas_rope_v8_attempt12_preflight_v1"
        or payload.get("status") != "PASS"
        or payload.get("implementation_candidate_sha256") != sha256_file(IMPLEMENTATION_CANDIDATE)
        or payload.get("recovery_config_sha256") != sha256_file(RECOVERY_CONFIG)
        or payload.get("extraction_gpu_uuid") != EXTRACTION_GPU_UUID
        or payload.get("analysis_gpu_uuid") != ANALYSIS_GPU_UUID
        or payload.get("result_namespace_absent") is not True
        or payload.get("attempt11_terminal_preserved") is not True
        or any(payload.get(key) is not False for key in (
            "scientific_scoring_performed",
            "model_forward_performed",
            "fresh_validation_performed",
            "activation_extraction_performed",
            "neural_training_run",
        ))
    ):
        raise RuntimeError("Attempt-12 signed preflight drift")
    return payload


def make_recovery_freeze() -> dict[str, Any]:
    verify_implementation_candidate()
    preflight = verify_preflight()
    _assert_pre_authorization_absence()
    if RECOVERY_FREEZE.exists():
        raise RuntimeError("Attempt-12 recovery freeze is create-once")
    payload = {
        "schema_version": "atlas_rope_v8_attempt12_recovery_freeze_v1",
        "status": "READY_FOR_ADVERSARIAL_REVIEW",
        "implementation_candidate_sha256": sha256_file(IMPLEMENTATION_CANDIDATE),
        "preflight_sha256": sha256_file(PREFLIGHT),
        "recovery_config_sha256": sha256_file(RECOVERY_CONFIG),
        "implementation_inventory": verify_implementation_candidate()["implementation_inventory"],
        "import_verification": preflight["import_verification"],
        "gpu_mapping": preflight["gpu_mapping"],
        "analysis_attempts": 1,
        "exploratory": True,
        "reuse_decision_frozen_before_outcome": True,
        "scientific_protocol_changed": False,
        "attempt11_continuation_authorized": False,
        "model_forward_authorized": False,
        "activation_extraction_authorized": False,
        "fresh_validation_authorized": False,
        "neural_training_authorized": False,
        "retry_authorized": False,
        "new_result_namespace": str(RESULT_ROOT.relative_to(ROOT)),
        "result_namespace_absent": True,
    }
    safe_write_target(RECOVERY_FREEZE)
    atomic_json(RECOVERY_FREEZE, payload)
    return payload


def verify_recovery_freeze(*, require_pre_authorization_absence: bool = False) -> dict[str, Any]:
    payload = read_json(RECOVERY_FREEZE)
    candidate = verify_implementation_candidate()
    preflight = verify_preflight()
    if (
        payload.get("schema_version") != "atlas_rope_v8_attempt12_recovery_freeze_v1"
        or payload.get("status") != "READY_FOR_ADVERSARIAL_REVIEW"
        or payload.get("implementation_candidate_sha256") != sha256_file(IMPLEMENTATION_CANDIDATE)
        or payload.get("preflight_sha256") != sha256_file(PREFLIGHT)
        or payload.get("recovery_config_sha256") != sha256_file(RECOVERY_CONFIG)
        or payload.get("implementation_inventory") != candidate["implementation_inventory"]
        or payload.get("import_verification") != preflight["import_verification"]
        or payload.get("gpu_mapping") != preflight["gpu_mapping"]
        or payload.get("analysis_attempts") != 1
        or payload.get("exploratory") is not True
        or payload.get("reuse_decision_frozen_before_outcome") is not True
        or payload.get("scientific_protocol_changed") is not False
        or payload.get("attempt11_continuation_authorized") is not False
        or payload.get("retry_authorized") is not False
        or any(payload.get(key) is not False for key in (
            "model_forward_authorized", "activation_extraction_authorized", "fresh_validation_authorized", "neural_training_authorized"
        ))
        or payload.get("new_result_namespace") != str(RESULT_ROOT.relative_to(ROOT))
        or payload.get("result_namespace_absent") is not True
    ):
        raise RuntimeError("Attempt-12 recovery freeze drift")
    if require_pre_authorization_absence:
        _assert_pre_authorization_absence()
    return payload


def authorize(signing_key: Path, review: Path) -> dict[str, Any]:
    verify_recovery_freeze(require_pre_authorization_absence=True)
    _assert_pre_authorization_absence()
    with exclusive_lock("lifecycle"):
        verify_recovery_freeze(require_pre_authorization_absence=True)
        _assert_pre_authorization_absence()
        verify_all_imports(deep_cache=True)
        gpu = verify_gpu_mapping()
        payload = {
            "schema_version": "atlas_rope_v8_attempt12_authorization_v1",
            "status": "AUTHORIZED",
            "authorized_stage": "ONE_SHOT_EXPLORATORY_ANALYSIS_ONLY_RECOVERY",
            "recovery_freeze_sha256": sha256_file(RECOVERY_FREEZE),
            "preflight_sha256": sha256_file(PREFLIGHT),
            "implementation_candidate_sha256": sha256_file(IMPLEMENTATION_CANDIDATE),
            "review": _review_ship(review, RECOVERY_FREEZE),
            "gpu_mapping": gpu,
            "analysis_attempts": 1,
            "exploratory": True,
            "model_forward_authorized": False,
            "activation_extraction_authorized": False,
            "fresh_validation_authorized": False,
            "neural_training_authorized": False,
            "retry_authorized": False,
        }
        safe_write_target(AUTHORIZATION)
        write_signed_local(AUTHORIZATION, payload, signing_key.resolve(strict=True))
        return verify_authorization(live_gpu=False)


def verify_authorization(*, live_gpu: bool) -> dict[str, Any]:
    payload = verify_envelope(read_json(AUTHORIZATION))
    verify_recovery_freeze()
    if (
        payload.get("schema_version") != "atlas_rope_v8_attempt12_authorization_v1"
        or payload.get("status") != "AUTHORIZED"
        or payload.get("authorized_stage") != "ONE_SHOT_EXPLORATORY_ANALYSIS_ONLY_RECOVERY"
        or payload.get("recovery_freeze_sha256") != sha256_file(RECOVERY_FREEZE)
        or payload.get("preflight_sha256") != sha256_file(PREFLIGHT)
        or payload.get("implementation_candidate_sha256") != sha256_file(IMPLEMENTATION_CANDIDATE)
        or payload.get("analysis_attempts") != 1
        or payload.get("exploratory") is not True
        or payload.get("retry_authorized") is not False
        or any(payload.get(key) is not False for key in (
            "model_forward_authorized", "activation_extraction_authorized", "fresh_validation_authorized", "neural_training_authorized"
        ))
    ):
        raise RuntimeError("Attempt-12 authorization drift")
    _verify_review(payload.get("review", {}), RECOVERY_FREEZE)
    if live_gpu and payload.get("gpu_mapping") != verify_gpu_mapping():
        raise RuntimeError("Attempt-12 authorization/live GPU mapping drift")
    return payload


def _begin(signing_key: Path) -> dict[str, Any]:
    verify_authorization(live_gpu=True)
    _assert_pre_start_absence()
    with exclusive_lock("lifecycle"):
        verify_authorization(live_gpu=True)
        _assert_pre_start_absence()
        imports = verify_all_imports(deep_cache=True)
        payload = {
            "schema_version": "atlas_rope_v8_attempt12_started_v1",
            "status": "STARTED_ONE_SHOT",
            "authorization_sha256": sha256_file(AUTHORIZATION),
            "recovery_freeze_sha256": sha256_file(RECOVERY_FREEZE),
            "import_verification": imports,
            "gpu_mapping": verify_gpu_mapping(),
            "analysis_attempt": 1,
            "exploratory": True,
            "retry_authorized": False,
            "model_forward_authorized": False,
            "activation_extraction_authorized": False,
            "fresh_validation_authorized": False,
            "neural_training_authorized": False,
        }
        safe_write_target(STARTED)
        write_signed_local(STARTED, payload, signing_key.resolve(strict=True))
        return payload


def verify_started() -> dict[str, Any]:
    payload = verify_envelope(read_json(STARTED))
    if (
        payload.get("schema_version") != "atlas_rope_v8_attempt12_started_v1"
        or payload.get("status") != "STARTED_ONE_SHOT"
        or payload.get("authorization_sha256") != sha256_file(AUTHORIZATION)
        or payload.get("recovery_freeze_sha256") != sha256_file(RECOVERY_FREEZE)
        or payload.get("analysis_attempt") != 1
        or payload.get("exploratory") is not True
        or payload.get("retry_authorized") is not False
        or any(payload.get(key) is not False for key in (
            "model_forward_authorized", "activation_extraction_authorized", "fresh_validation_authorized", "neural_training_authorized"
        ))
    ):
        raise RuntimeError("Attempt-12 start marker drift")
    return payload


def _effective_context() -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    adapter = read_json(FROZEN_ADAPTER)
    scoring = read_json(ROOT / adapter["frozen_scoring_config"]["path"])
    prescore = read_json(ROOT / adapter["frozen_science_prescore"]["path"])
    manifest = read_json(ROOT / adapter["frozen_prepared_manifest"]["path"])
    scoring = json.loads(json.dumps(scoring))
    prescore = json.loads(json.dumps(prescore))
    scoring["_resolved_sha256"] = sha256_file(FROZEN_ADAPTER)
    if scoring["analysis"] != adapter["frozen_analysis_settings"]:
        raise RuntimeError("effective analysis settings differ from frozen adapter")
    prescore["run_root"] = str((ATTEMPT11_ROOT / "science").relative_to(ROOT))
    return scoring, prescore, manifest


def load_frozen_analyzer_safely() -> Any:
    """Load the byte-frozen analyzer without loading its legacy model module."""
    if "analyze_atlas_discovery_v3_3" in sys.modules or "extract_atlas_discovery_v3_3" in sys.modules:
        raise RuntimeError("frozen analyzer/extractor was loaded before the Attempt-12 safe shim")
    from atlas_rope_v8 import runtime_dependency_audit
    import atlas_rope_v8_analysis_shim as shim

    runtime_dependency_audit()
    sys.modules["extract_atlas_discovery_v3_3"] = shim
    frozen = importlib.import_module("analyze_atlas_discovery_v3_3")
    if (
        sys.modules.get("extract_atlas_discovery_v3_3") is not shim
        or getattr(frozen, "_load_source_bundle", None) is not shim._load_source_bundle
        or getattr(frozen, "_gpu_uuid", None) is not shim._gpu_uuid
        or "transformers" in sys.modules
        or hasattr(shim, "_load_model")
        or hasattr(shim, "_forward_units")
    ):
        raise RuntimeError("Attempt-12 safe analyzer import closure drift")
    return frozen


def _new_staging() -> Path:
    root = RUN_ROOT / "staging"
    safe_write_target(root / "x")
    root.mkdir(parents=True, exist_ok=True)
    path = root / f"analysis-{sha256_file(AUTHORIZATION)[:12]}"
    path.mkdir()
    return path


def _promote(stage: Path) -> None:
    if RESULT_ROOT.exists():
        raise RuntimeError("Attempt-12 result is create-once")
    for path in stage.iterdir():
        if path.is_file():
            with path.open("rb") as handle:
                os.fsync(handle.fileno())
    RESULT_ROOT.parent.mkdir(parents=True, exist_ok=True)
    os.replace(stage, RESULT_ROOT)


def _panel_payloads() -> dict[str, dict[str, Any]]:
    return verify_validation(load_recovery_config())


def run_analysis(signing_key: Path) -> dict[str, Any]:
    with exclusive_lock("attempt"):
        _assert_no_terminal()
        _begin(signing_key)
        verify_started()
        verify_authorization(live_gpu=True)
        imports_before = verify_all_imports(deep_cache=True)
        if RESULT_ROOT.exists():
            raise RuntimeError("Attempt-12 result already exists after one-shot start")
        scoring, prescore, manifest = _effective_context()
        stage = _new_staging()
        started_at = time.time()

        # Lazy, shimmed import only after the signed one-shot start and complete preflight.
        frozen = load_frozen_analyzer_safely()
        from atlas_rope_v7 import make_eligibility_overlay

        original_loader = frozen.load_scoring_config
        original_cache = frozen._verify_complete_cache
        original_qa = frozen._verify_qa
        try:
            frozen.load_scoring_config = lambda path: (scoring, prescore, manifest)
            frozen._verify_complete_cache = lambda final, cfg, pre, bundle, source: verify_cache(source)
            frozen._verify_qa = lambda path, cfg, source: verify_qa(source)
            result = frozen.run(FROZEN_ADAPTER)
        finally:
            frozen.load_scoring_config = original_loader
            frozen._verify_complete_cache = original_cache
            frozen._verify_qa = original_qa

        if result.get("schema_version") != "atlas_discovery_v3_3_attempt7_result_v2" or result.get("neural_training_run") is not False:
            raise RuntimeError("frozen analyzer returned unexpected result schema")
        panels = _panel_payloads()
        overlay = make_eligibility_overlay(result, panels, artifact_lineage_valid=True)
        frozen_result_canonical_sha256 = sha256_bytes(canonical_json_bytes(result))
        atomic_json(stage / "frozen_result.json", result)
        atomic_json(stage / "technical_eligibility_overlay.json", overlay)
        recovery_lineage = {
            "schema_version": "atlas_rope_v8_attempt12_lineage_v1",
            "authorization_sha256": sha256_file(AUTHORIZATION),
            "started_sha256": sha256_file(STARTED),
            "recovery_freeze_sha256": sha256_file(RECOVERY_FREEZE),
            "preflight_sha256": sha256_file(PREFLIGHT),
            "implementation_candidate_sha256": sha256_file(IMPLEMENTATION_CANDIDATE),
            "recovery_config_sha256": sha256_file(RECOVERY_CONFIG),
            "frozen_adapter_sha256": sha256_file(FROZEN_ADAPTER),
            "frozen_result_canonical_sha256": frozen_result_canonical_sha256,
            "frozen_result_lineage": result["lineage"],
            "import_verification_before": imports_before,
            "gpu_mapping": verify_gpu_mapping(),
            "cache_reused_without_new_forward": True,
            "fresh_validation_rerun": False,
            "scientific_protocol_changed": False,
            "exploratory": True,
        }
        atomic_json(stage / "lineage.json", recovery_lineage)
        frozen_report = frozen._render_markdown(result)
        report = (
            "# Attempt 12 exploratory analysis-only recovery\n\n"
            f"**Architecture promotion status: `{overlay['architecture_promotion_status']}`.**\n\n"
            "Attempt 11 remains terminal and is not continued. This successor reused its signed EWT/GUM caches without model forwards.\n\n"
            "The recovered frozen result alone is non-promotable and not confirmatory.\n\n"
            f"- Baseline runtime eligibility: `{overlay['cross_panel']['baseline_runtime_pass']}`\n"
            f"- RoPE translation eligibility: `{overlay['cross_panel']['rope_translation_pass']}`\n"
            f"- Frozen exploratory outcome: `{overlay['frozen_outcome']}`\n"
            "- Neural training authorized: `false`\n\n---\n\n" + frozen_report
        )
        (stage / "report.md").write_text(report, encoding="utf-8")
        artifacts = {
            path.name: {"bytes": path.stat().st_size, "sha256": sha256_file(path)}
            for path in stage.iterdir()
            if path.is_file()
        }
        complete = {
            "schema_version": "atlas_rope_v8_attempt12_result_complete_v1",
            "status": "COMPLETE",
            "claim_class": "EXPLORATORY_ANALYSIS_ONLY_RECOVERY",
            "architecture_promotion_status": overlay["architecture_promotion_status"],
            "frozen_outcome": result["outcome"],
            "frozen_result_canonical_sha256": frozen_result_canonical_sha256,
            "frozen_result_mutated": False,
            "promotion_from_recovered_result_alone_authorized": False,
            "authorization_sha256": sha256_file(AUTHORIZATION),
            "started_sha256": sha256_file(STARTED),
            "elapsed_seconds": time.time() - started_at,
            "model_forward_performed": False,
            "activation_extraction_performed": False,
            "fresh_validation_performed": False,
            "neural_training_run": False,
            "artifacts": artifacts,
        }
        write_signed_local(stage / "COMPLETE.json", complete, signing_key.resolve(strict=True))
        imports_after = verify_all_imports(deep_cache=True)
        if imports_after != imports_before:
            raise RuntimeError("imported Attempt-11/source inventory changed during analysis")
        with exclusive_lock("lifecycle"):
            _assert_no_terminal()
            verify_started()
            _promote(stage)
            verified = verify_result()
            _write_terminal_locked(
                signing_key,
                "TERMINAL_COMPLETE",
                "Attempt-12 one-shot exploratory analysis-only recovery completed",
            )
        return verified


def verify_result() -> dict[str, Any]:
    expected = {"COMPLETE.json", "frozen_result.json", "technical_eligibility_overlay.json", "report.md", "lineage.json"}
    entries = list(RESULT_ROOT.iterdir())
    if {path.name for path in entries} != expected or any(not path.is_file() or path.is_symlink() for path in entries):
        raise RuntimeError("Attempt-12 result allowlist drift")
    complete = verify_envelope(read_json(RESULT_ROOT / "COMPLETE.json"))
    artifacts = {
        name: {"bytes": (RESULT_ROOT / name).stat().st_size, "sha256": sha256_file(RESULT_ROOT / name)}
        for name in sorted(expected - {"COMPLETE.json"})
    }
    result = read_json(RESULT_ROOT / "frozen_result.json")
    overlay = read_json(RESULT_ROOT / "technical_eligibility_overlay.json")
    lineage = read_json(RESULT_ROOT / "lineage.json")
    from atlas_rope_v7 import make_eligibility_overlay

    expected_overlay = make_eligibility_overlay(result, _panel_payloads(), artifact_lineage_valid=True)
    canonical_sha = sha256_bytes(canonical_json_bytes(result))
    if (
        complete.get("schema_version") != "atlas_rope_v8_attempt12_result_complete_v1"
        or complete.get("status") != "COMPLETE"
        or complete.get("claim_class") != "EXPLORATORY_ANALYSIS_ONLY_RECOVERY"
        or complete.get("artifacts") != artifacts
        or complete.get("architecture_promotion_status") != overlay.get("architecture_promotion_status")
        or complete.get("frozen_outcome") != result.get("outcome")
        or complete.get("frozen_result_canonical_sha256") != canonical_sha
        or complete.get("frozen_result_mutated") is not False
        or complete.get("promotion_from_recovered_result_alone_authorized") is not False
        or complete.get("authorization_sha256") != sha256_file(AUTHORIZATION)
        or complete.get("started_sha256") != sha256_file(STARTED)
        or any(complete.get(key) is not False for key in (
            "model_forward_performed", "activation_extraction_performed", "fresh_validation_performed", "neural_training_run"
        ))
        or result.get("schema_version") != "atlas_discovery_v3_3_attempt7_result_v2"
        or result.get("neural_training_run") is not False
        or overlay != expected_overlay
        or lineage.get("frozen_result_lineage") != result.get("lineage")
        or lineage.get("frozen_result_canonical_sha256") != canonical_sha
        or lineage.get("cache_reused_without_new_forward") is not True
        or lineage.get("scientific_protocol_changed") is not False
        or lineage.get("exploratory") is not True
    ):
        raise RuntimeError("Attempt-12 result identity/lineage drift")
    report = (RESULT_ROOT / "report.md").read_text(encoding="utf-8")
    if not report.startswith("# Attempt 12 exploratory analysis-only recovery") or "non-promotable and not confirmatory" not in report:
        raise RuntimeError("Attempt-12 interpretation boundary drift")
    verify_all_imports(deep_cache=True)
    return complete


def _resolve_terminal_status(requested: str, *, result_exists: bool, result_valid: bool) -> str:
    if requested not in {"TERMINAL_COMPLETE", "TERMINAL_PIPELINE_STAGE_FAILED"}:
        raise RuntimeError("unknown Attempt-12 terminal status")
    if result_valid:
        return "TERMINAL_COMPLETE"
    if requested == "TERMINAL_COMPLETE":
        raise RuntimeError("success terminal requires a verified complete result")
    return "TERMINAL_PIPELINE_STAGE_FAILED"


def _terminal_payload(status: str, reason: str) -> dict[str, Any]:
    return {
        "schema_version": "atlas_rope_v8_attempt12_terminal_v1",
        "status": status,
        "reason": reason[:2000],
        "lineage": {
            "recovery_config": {"path": str(RECOVERY_CONFIG.relative_to(ROOT)), "sha256": sha256_file(RECOVERY_CONFIG)},
            "implementation_candidate": {"path": str(IMPLEMENTATION_CANDIDATE.relative_to(ROOT)), "sha256": sha256_file(IMPLEMENTATION_CANDIDATE)},
            "preflight": {"path": str(PREFLIGHT.relative_to(ROOT)), "sha256": sha256_file(PREFLIGHT)},
            "recovery_freeze": {"path": str(RECOVERY_FREEZE.relative_to(ROOT)), "sha256": sha256_file(RECOVERY_FREEZE)},
            "authorization": {"path": str(AUTHORIZATION.relative_to(ROOT)), "sha256": sha256_file(AUTHORIZATION)},
            "started": {"path": str(STARTED.relative_to(ROOT)), "sha256": sha256_file(STARTED)} if STARTED.exists() else None,
            "result_complete": {
                "path": str((RESULT_ROOT / "COMPLETE.json").relative_to(ROOT)),
                "sha256": sha256_file(RESULT_ROOT / "COMPLETE.json"),
            } if (RESULT_ROOT / "COMPLETE.json").exists() else None,
        },
        "attempt11_terminal_preserved": sha256_file(ATTEMPT11_ROOT / "TERMINAL.json"),
        "exploratory": True,
        "no_retry_authorized": True,
        "model_forward_authorized": False,
        "activation_extraction_authorized": False,
        "fresh_validation_authorized": False,
        "neural_training_authorized": False,
    }


def _verify_existing_terminal() -> dict[str, Any]:
    payload = verify_envelope(read_json(TERMINAL))
    if (
        payload.get("schema_version") != "atlas_rope_v8_attempt12_terminal_v1"
        or payload.get("status") not in {"TERMINAL_COMPLETE", "TERMINAL_PIPELINE_STAGE_FAILED"}
        or payload.get("no_retry_authorized") is not True
        or payload.get("exploratory") is not True
        or any(payload.get(key) is not False for key in (
            "model_forward_authorized", "activation_extraction_authorized", "fresh_validation_authorized", "neural_training_authorized"
        ))
    ):
        raise RuntimeError("Attempt-12 terminal identity drift")
    if payload["status"] == "TERMINAL_COMPLETE":
        verify_result()
    elif RESULT_ROOT.exists():
        try:
            verify_result()
        except Exception:
            pass
        else:
            raise RuntimeError("failure terminal conflicts with a verified complete result")
    return payload


def _write_terminal_locked(signing_key: Path, status: str, reason: str) -> dict[str, Any]:
    if TERMINAL.exists():
        return _verify_existing_terminal()
    payload = _terminal_payload(status, reason)
    safe_write_target(TERMINAL)
    write_signed_local(TERMINAL, payload, signing_key.resolve(strict=True))
    return _verify_existing_terminal()


def terminalize(signing_key: Path, status: str, reason: str) -> dict[str, Any]:
    """Reconcile crash points without ever rerunning the analysis."""
    with exclusive_lock("attempt"):
        with exclusive_lock("lifecycle"):
            if TERMINAL.exists():
                return _verify_existing_terminal()
            result_exists = RESULT_ROOT.exists()
            result_valid = False
            result_error: str | None = None
            if result_exists:
                try:
                    verify_result()
                    result_valid = True
                except Exception as error:
                    result_error = f"{type(error).__name__}: {error}"
            resolved = _resolve_terminal_status(status, result_exists=result_exists, result_valid=result_valid)
            if result_valid and status != "TERMINAL_COMPLETE":
                reason = "Recovered verified result after interruption; terminal reconciled to complete. " + reason
            elif result_exists and not result_valid:
                reason = f"Invalid promoted result preserved ({result_error}). " + reason
            return _write_terminal_locked(signing_key, resolved, reason)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("stage", choices=(
        "make-implementation-candidate",
        "preflight",
        "make-recovery-freeze",
        "authorize",
        "analyze",
        "verify-result",
        "terminalize",
    ))
    parser.add_argument("--signing-key", type=Path)
    parser.add_argument("--verification-report", type=Path)
    parser.add_argument("--review", type=Path)
    parser.add_argument("--terminal-status", default="TERMINAL_PIPELINE_STAGE_FAILED")
    parser.add_argument("--reason", default="unspecified Attempt-12 failure")
    args = parser.parse_args()
    if args.stage == "make-implementation-candidate":
        if not args.verification_report:
            raise RuntimeError("verification report required")
        result = make_implementation_candidate(args.verification_report)
    elif args.stage == "make-recovery-freeze":
        result = make_recovery_freeze()
    elif args.stage == "verify-result":
        result = verify_result()
    else:
        if not args.signing_key:
            raise RuntimeError("signing key required")
        if args.stage == "preflight":
            result = run_preflight(args.signing_key)
        elif args.stage == "authorize":
            if not args.review:
                raise RuntimeError("adversarial review required")
            result = authorize(args.signing_key, args.review)
        elif args.stage == "analyze":
            result = run_analysis(args.signing_key)
        else:
            result = terminalize(args.signing_key, args.terminal_status, args.reason)
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
