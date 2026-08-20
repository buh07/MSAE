from __future__ import annotations

import ast
import json
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

