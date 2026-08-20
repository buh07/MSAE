from __future__ import annotations

import ast
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import atlas_rope_v8 as recovery  # noqa: E402
import run_atlas_rope_v8 as controller  # noqa: E402
from atlas_rope_v6 import read_json, sha256_file  # noqa: E402


def test_attempt11_is_imported_terminal_not_continued() -> None:
    payload = recovery.verify_attempt11_terminal()
    assert sha256_file(recovery.ATTEMPT11_TERMINAL) == recovery.ATTEMPT11_TERMINAL_SHA256
    assert payload["no_retry_authorized"] is True
    assert not recovery.ATTEMPT11_RESULT_ROOT.exists()
    runner = (ROOT / "scripts/run_atlas_rope_v8.py").read_text(encoding="utf-8")
    assert "run_atlas_rope_v7_science" not in runner
    assert "run_atlas_rope_v7.py" not in runner


def test_recovery_config_freezes_exploratory_no_inference_contract() -> None:
    config = recovery.load_recovery_config()
    assert config["claim_class"] == "EXPLORATORY_ANALYSIS_ONLY_RECOVERY"
    assert config["reuse_decision_frozen_before_outcome"] is True
    assert config["scientific_protocol_changed"] is False
    assert config["analysis_attempts"] == 1
    assert config["retry_authorized"] is False
    assert all(value is False for value in config["permissions"].values())
    assert config["gpu_roles"]["extraction_gpu_uuid"] == recovery.EXTRACTION_GPU_UUID
    assert config["gpu_roles"]["analysis_gpu_uuid"] == recovery.ANALYSIS_GPU_UUID
    assert config["gpu_roles"]["required_cuda_visible_devices"] == "0"


def test_exact_import_and_source_inventory_matches() -> None:
    config = recovery.load_recovery_config()
    recovery.verify_imported_files(config)
    assert set(config["prepared_source_files"]) == {
        str(path.relative_to(ROOT))
        for source in recovery.SOURCES
        for path in (ROOT / "data/atlas_discovery_v3_3_attempt7_final_v3/prepared" / source).rglob("*")
        if path.is_file()
    }


def test_validation_and_qa_imports_are_signed_and_passed() -> None:
    config = recovery.load_recovery_config()
    panels = recovery.verify_validation(config)
    assert set(panels) == set(recovery.PANELS)
    assert all(row["integrity_runtime_pass"] and row["approximate_equivariance_pass"] for row in panels.values())
    for source in recovery.SOURCES:
        envelope = recovery.verify_qa(source, config)
        assert envelope["payload"]["status"] == "PASS"


def test_cache_imports_align_to_prepared_rows_and_are_finite() -> None:
    config = recovery.load_recovery_config()
    adapter = recovery.verify_frozen_adapter(config)
    for source in recovery.SOURCES:
        payload = recovery.verify_cache(source, config, adapter)
        assert payload["status"] == "COMPLETE"
        assert payload["runtime_preflight"]["gpu_uuid"] == recovery.EXTRACTION_GPU_UUID
        assert payload["neural_training_run"] is False


def test_operation_audit_has_no_reachable_forward_extraction_or_training_path() -> None:
    audit = recovery.static_operation_audit()
    assert audit["status"] == "PASS"
    assert audit["model_forward_path"] is False
    assert audit["activation_extraction_path"] is False
    assert audit["fresh_validation_path"] is False
    assert audit["neural_training_path"] is False
    assert audit["transitive_analysis_loader"]["legacy_extractor_loaded"] is False
    assert audit["transitive_analysis_loader"]["model_forward_callable_exposed"] is False
    tree = ast.parse((ROOT / "scripts/run_atlas_rope_v8.py").read_text(encoding="utf-8"))
    choices = {
        literal.value
        for node in ast.walk(tree)
        if isinstance(node, (ast.Tuple, ast.List))
        for literal in node.elts
        if isinstance(literal, ast.Constant) and isinstance(literal.value, str)
    }
    assert "extract-ewt" not in choices
    assert "extract-gum" not in choices
    assert "run-panel" not in choices


def test_gpu_parser_and_safe_write_boundaries() -> None:
    parsed = recovery._parse_nvidia_smi(
        "0, GPU-ec526219-fb07-e57e-a30d-5d2ab843fb15\n"
        "1, GPU-9b529a09-92a6-caea-fee2-6b2bf07b0e4e\n"
    )
    assert parsed[0] == recovery.ANALYSIS_GPU_UUID
    assert parsed[1] == recovery.EXTRACTION_GPU_UUID
    assert recovery.safe_write_target(recovery.RUN_ROOT / "x.json") == recovery.RUN_ROOT / "x.json"
    assert recovery.safe_write_target(recovery.CONFIG_ROOT / "x.json") == recovery.CONFIG_ROOT / "x.json"
    assert recovery.safe_write_target(recovery.RESULT_ROOT / "x.json") == recovery.RESULT_ROOT / "x.json"
    with pytest.raises(RuntimeError):
        recovery.safe_write_target(recovery.ATTEMPT11_ROOT / "forbidden.json")
    with pytest.raises(RuntimeError):
        recovery.safe_write_target(ROOT / "results/atlas_rope_v7_attempt11_science/forbidden.json")


def test_gpu_live_preflight_records_both_physical_roles(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CUDA_VISIBLE_DEVICES", "0")
    mapping = recovery.verify_gpu_mapping()
    assert mapping["physical_index"] == 0
    assert mapping["physical_uuid"] == recovery.ANALYSIS_GPU_UUID
    assert mapping["extraction_physical_index"] == 1
    assert mapping["extraction_physical_uuid"] == recovery.EXTRACTION_GPU_UUID
    assert mapping["visible_uuid"] == recovery.ANALYSIS_GPU_UUID


def test_frozen_effective_context_changes_only_cache_loader_root() -> None:
    scoring, prescore, manifest = controller._effective_context()
    adapter = read_json(recovery.FROZEN_ADAPTER)
    original_scoring = read_json(ROOT / adapter["frozen_scoring_config"]["path"])
    original_prescore = read_json(ROOT / adapter["frozen_science_prescore"]["path"])
    assert scoring["analysis"] == original_scoring["analysis"] == adapter["frozen_analysis_settings"]
    assert scoring["_resolved_sha256"] == sha256_file(recovery.FROZEN_ADAPTER)
    assert {key: value for key, value in prescore.items() if key != "run_root"} == {
        key: value for key, value in original_prescore.items() if key != "run_root"
    }
    assert prescore["run_root"] == "pilot_runs/20260803_atlas_rope_technical_v7/science"
    assert manifest == read_json(ROOT / adapter["frozen_prepared_manifest"]["path"])


def test_pipeline_is_analysis_only_and_gpu0_pinned() -> None:
    pipeline = (ROOT / "scripts/run_atlas_rope_v8_pipeline.sh").read_text(encoding="utf-8")
    launcher = (ROOT / "scripts/launch_atlas_rope_v8_tmux.sh").read_text(encoding="utf-8")
    assert "run_atlas_rope_v8.py\" analyze" in pipeline
    assert "extract" not in pipeline
    assert "run-panel" not in pipeline
    assert "CUDA_VISIBLE_DEVICES=0" in launcher
    assert recovery.ANALYSIS_GPU_UUID in launcher
    assert "trap reconcile_on_exit EXIT INT TERM" in pipeline
    assert "TERMINAL_COMPLETE" not in pipeline


def test_frozen_analyzer_import_uses_safe_shim_without_transformers() -> None:
    code = r'''
import json,sys
import run_atlas_rope_v8 as runner
frozen=runner.load_frozen_analyzer_safely()
shim=sys.modules["extract_atlas_discovery_v3_3"]
assert shim.__name__=="atlas_rope_v8_analysis_shim"
assert frozen._load_source_bundle is shim._load_source_bundle
assert frozen._gpu_uuid is shim._gpu_uuid
assert "transformers" not in sys.modules
assert not hasattr(shim,"_load_model") and not hasattr(shim,"_forward_units")
print(json.dumps({"shim":shim.__file__,"analyzer":frozen.__file__}))
'''
    env = dict(os.environ)
    env["PYTHONPATH"] = str(ROOT / "scripts")
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    proc = subprocess.run([sys.executable, "-c", code], cwd=ROOT, env=env, capture_output=True, text=True, timeout=60)
    assert proc.returncode == 0, proc.stdout + proc.stderr
    payload = json.loads(proc.stdout)
    assert payload["shim"].endswith("atlas_rope_v8_analysis_shim.py")


def test_safe_shim_source_bundle_matches_frozen_loader() -> None:
    import atlas_rope_v8_analysis_shim as shim
    import extract_atlas_discovery_v3_3 as legacy

    adapter = read_json(recovery.FROZEN_ADAPTER)
    prescore = read_json(ROOT / adapter["frozen_science_prescore"]["path"])
    manifest = read_json(ROOT / adapter["frozen_prepared_manifest"]["path"])
    for source in recovery.SOURCES:
        left = shim._load_source_bundle(prescore, manifest, source)
        right = legacy._load_source_bundle(prescore, manifest, source)
        assert left["root"] == right["root"]
        assert left["units"] == right["units"]
        assert left["rows"] == right["rows"]
        assert left["pairs"] == right["pairs"]
        assert left["row_to_unit"] == right["row_to_unit"]


@pytest.mark.parametrize("failure_mode", ("identity", "signature", "semantic"))
def test_local_signing_fault_never_targets_historical_run(
    failure_mode: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    run_root = tmp_path / "attempt12"
    monkeypatch.setattr(recovery, "ROOT", tmp_path)
    monkeypatch.setattr(recovery, "RUN_ROOT", run_root)
    monkeypatch.setattr(recovery, "CONFIG_ROOT", tmp_path / "config")
    monkeypatch.setattr(recovery, "RESULT_ROOT", tmp_path / "result")
    monkeypatch.setattr(recovery, "ATTEMPT11_ROOT", tmp_path / "attempt11")
    monkeypatch.setattr(recovery, "load_private_key", lambda path: object())
    monkeypatch.setattr(
        recovery,
        "sign_payload",
        lambda payload, private: {"payload": dict(payload), "signature": {"fake": True}},
    )
    calls = 0

    def verify(envelope: dict[str, object]) -> dict[str, object]:
        nonlocal calls
        calls += 1
        if calls == 2 and failure_mode == "signature":
            raise RuntimeError("injected final signature failure")
        if calls == 2 and failure_mode == "semantic":
            return {"status": "different"}
        return dict(envelope["payload"])  # type: ignore[arg-type]

    monkeypatch.setattr(recovery, "verify_envelope", verify)
    monkeypatch.setattr(recovery, "_post_link_identity_matches", lambda *args: failure_mode != "identity")
    key = tmp_path / "key.pem"
    key.write_text("fixture", encoding="utf-8")
    destination = run_root / "provenance/PREFLIGHT.json"
    expected = {
        "identity": "post-link signed artifact identity mismatch",
        "signature": "injected final signature failure",
        "semantic": "post-link signed artifact did not verify",
    }[failure_mode]
    with pytest.raises(RuntimeError, match=expected):
        recovery.write_signed_local(destination, {"status": "fixture"}, key)
    fault = run_root / "SIGNING_FAULT.json"
    assert fault.is_file()
    assert read_json(fault)["schema_version"] == "atlas_rope_v8_attempt12_signing_fault_v1"
    assert not (tmp_path / "pilot_runs/20260803_atlas_rope_technical_v6/SIGNING_FAULT.json").exists()


def test_attempt_lock_rejects_concurrent_recovery(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    run_root = tmp_path / "run"
    monkeypatch.setattr(controller, "RUN_ROOT", run_root)
    monkeypatch.setattr(recovery, "ROOT", tmp_path)
    monkeypatch.setattr(recovery, "RUN_ROOT", run_root)
    monkeypatch.setattr(recovery, "CONFIG_ROOT", tmp_path / "config")
    monkeypatch.setattr(recovery, "RESULT_ROOT", tmp_path / "result")
    monkeypatch.setattr(recovery, "ATTEMPT11_ROOT", tmp_path / "attempt11")
    with controller.exclusive_lock("attempt"):
        with pytest.raises(RuntimeError, match="another Attempt-12 process"):
            with controller.exclusive_lock("attempt"):
                pass


def test_terminal_reconciliation_is_fail_closed_and_result_preferential() -> None:
    assert controller._resolve_terminal_status(
        "TERMINAL_PIPELINE_STAGE_FAILED", result_exists=False, result_valid=False
    ) == "TERMINAL_PIPELINE_STAGE_FAILED"
    assert controller._resolve_terminal_status(
        "TERMINAL_PIPELINE_STAGE_FAILED", result_exists=True, result_valid=True
    ) == "TERMINAL_COMPLETE"
    assert controller._resolve_terminal_status(
        "TERMINAL_COMPLETE", result_exists=True, result_valid=True
    ) == "TERMINAL_COMPLETE"
    with pytest.raises(RuntimeError, match="verified complete result"):
        controller._resolve_terminal_status("TERMINAL_COMPLETE", result_exists=True, result_valid=False)


def test_crash_after_promotion_reconciles_to_success_without_analysis_retry(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from contextlib import contextmanager

    result_root = tmp_path / "result"
    result_root.mkdir()
    monkeypatch.setattr(controller, "RESULT_ROOT", result_root)
    monkeypatch.setattr(controller, "TERMINAL", tmp_path / "TERMINAL.json")

    @contextmanager
    def unlocked(name: str):
        yield

    monkeypatch.setattr(controller, "exclusive_lock", unlocked)
    calls = {"verify_result": 0, "terminal": []}

    def verified() -> dict[str, object]:
        calls["verify_result"] += 1
        return {"status": "COMPLETE"}

    def terminal(signing_key: Path, status: str, reason: str) -> dict[str, object]:
        calls["terminal"].append((status, reason))
        return {"status": status}

    monkeypatch.setattr(controller, "verify_result", verified)
    monkeypatch.setattr(controller, "_write_terminal_locked", terminal)
    observed = controller.terminalize(
        tmp_path / "unused-key.pem",
        "TERMINAL_PIPELINE_STAGE_FAILED",
        "injected interruption after promotion",
    )
    assert observed["status"] == "TERMINAL_COMPLETE"
    assert calls["verify_result"] == 1
    assert calls["terminal"][0][0] == "TERMINAL_COMPLETE"
    assert "reconciled to complete" in calls["terminal"][0][1]


def test_overlay_generation_is_unconditional_and_exact() -> None:
    from atlas_rope_v7 import make_eligibility_overlay

    frozen = {"outcome": "NOMINATE_TOKEN_LOCAL_VS_CONTEXT_DEPENDENT"}
    panels = {
        panel: {"integrity_runtime_pass": True, "approximate_equivariance_pass": True}
        for panel in recovery.PANELS
    }
    overlay = make_eligibility_overlay(frozen, panels, artifact_lineage_valid=True)
    assert overlay["frozen_outcome"] == frozen["outcome"]
    assert overlay["architecture_promotion_status"] == frozen["outcome"]
    assert overlay["path_eligibility"]["task_results.*.*"] == "eligible"
    assert overlay["path_eligibility"]["projections.*.*"] == "eligible"


def test_prestart_absence_is_create_once(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    start = tmp_path / "STARTED.json"
    monkeypatch.setattr(controller, "STARTED", start)
    monkeypatch.setattr(controller, "TERMINAL", tmp_path / "TERMINAL.json")
    monkeypatch.setattr(controller, "RESULT_ROOT", tmp_path / "result")
    controller._assert_pre_start_absence()
    start.write_text("{}\n", encoding="utf-8")
    with pytest.raises(RuntimeError, match="start/terminal/result"):
        controller._assert_pre_start_absence()


def test_review_must_ship_exact_freeze(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    artifact = tmp_path / "freeze.json"
    artifact.write_text('{"x":1}\n', encoding="utf-8")
    review = tmp_path / "review.md"
    review.write_text("VERDICT: SHIP\n", encoding="utf-8")
    monkeypatch.setattr(controller, "ROOT", tmp_path)
    with pytest.raises(RuntimeError, match="exact recovery freeze"):
        controller._review_ship(review, artifact)
    review.write_text(f"VERDICT: SHIP\n{sha256_file(artifact)}\n", encoding="utf-8")
    assert controller._review_ship(review, artifact)["reviewed_sha256"] == sha256_file(artifact)


def test_completed_result_verifies_if_present() -> None:
    if recovery.RESULT_ROOT.exists():
        complete = controller.verify_result()
        assert complete["claim_class"] == "EXPLORATORY_ANALYSIS_ONLY_RECOVERY"
        assert complete["neural_training_run"] is False
