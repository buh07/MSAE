from __future__ import annotations

import hashlib
import json
import shutil
import sys
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import atlas_rope_v7  # noqa: E402
import run_atlas_rope_v7 as controller  # noqa: E402
from atlas_rope_v7 import (  # noqa: E402
    cache_round_trip,
    DATA_ROOT,
    PANEL_NAMES,
    cross_panel_status,
    gate_contract,
    make_eligibility_overlay,
    read_json,
    read_jsonl,
    row_metrics,
    score_grid,
    score_rows,
    sha256_file,
    verify_attempt10_terminal,
    verify_envelope,
)


def test_attempt10_is_immutable_terminal() -> None:
    payload = verify_attempt10_terminal()
    assert payload["status"] == "TERMINAL_GENTLE_VALIDATION_FAILED"
    assert payload["no_retry_authorized"] is True
    reference = controller._attempt10_terminal_reference()
    envelope = read_json(controller.ATTEMPT10_TERMINAL)
    assert reference["message_sha256"] == envelope["signature"]["message_sha256"]
    assert reference["sha256"] == sha256_file(controller.ATTEMPT10_TERMINAL)


def test_preinference_controller_failure_is_preserved_and_superseded() -> None:
    path = ROOT / "reports/atlas_rope_v7/preinference_superseded_81507aa3590a/SUPERSESSION.json"
    payload = verify_envelope(read_json(path))
    assert payload["status"] == "SUPERSEDED_PRE_INFERENCE_CONTROLLER_FAILURE"
    assert payload["model_inference_performed"] is False
    assert payload["fresh_validation_values_inspected"] is False
    assert payload["development_complete_absent"] is True
    assert payload["validation_outputs_absent"] is True
    assert payload["old_authorization_reuse_authorized"] is False


@pytest.mark.parametrize("norm", [0.0, 1e-13, 1e-12])
def test_invalid_reference_norm_is_primary_and_catastrophic(norm: float) -> None:
    reference = np.zeros((1, 768), np.float64)
    reference[0, 0] = norm
    metrics = row_metrics(reference, reference.copy())
    assert metrics["primary_failure"].tolist() == [True]
    assert metrics["catastrophic_failure"].tolist() == [True]
    assert score_rows(reference, reference.copy())["status"] == "FAIL"


def test_primary_and_catastrophic_threshold_boundaries() -> None:
    reference = np.zeros((3, 768), np.float64); reference[:, 0] = 1.0
    candidate = reference.copy()
    candidate[0, 1] = 1.9e-5
    candidate[1, 1] = 2.1e-5
    candidate[2, 1] = 5.1e-5
    metrics = row_metrics(reference, candidate)
    assert metrics["primary_failure"].tolist() == [False, True, True]
    assert metrics["catastrophic_failure"].tolist() == [False, False, True]


def test_nonfinite_fails_both() -> None:
    reference = np.ones((1, 768), np.float64); candidate = reference.copy(); candidate[0, 3] = np.nan
    metrics = row_metrics(reference, candidate)
    assert bool(metrics["primary_failure"][0]) and bool(metrics["catastrophic_failure"][0])


def test_cross_panel_propagation_separates_runtime_and_rope() -> None:
    values = {panel: {"integrity_runtime_pass": True, "approximate_equivariance_pass": True} for panel in PANEL_NAMES}
    assert cross_panel_status(values) == {"baseline_runtime_pass": True, "rope_translation_pass": True}
    values[PANEL_NAMES[0]]["approximate_equivariance_pass"] = False
    assert cross_panel_status(values) == {"baseline_runtime_pass": True, "rope_translation_pass": False}
    values[PANEL_NAMES[0]]["integrity_runtime_pass"] = False
    assert cross_panel_status(values) == {"baseline_runtime_pass": False, "rope_translation_pass": False}


def test_overlay_never_mutates_frozen_outcome() -> None:
    frozen = {"outcome": "nominate_token_local_vs_context_dependent"}
    panels = {panel: {"integrity_runtime_pass": True, "approximate_equivariance_pass": False} for panel in PANEL_NAMES}
    overlay = make_eligibility_overlay(frozen, panels)
    assert frozen == {"outcome": "nominate_token_local_vs_context_dependent"}
    assert overlay["frozen_outcome"] == frozen["outcome"]
    assert overlay["architecture_promotion_status"] == "technically_ineligible"
    assert overlay["path_eligibility"]["task_results.*.*"] == "eligible"
    assert overlay["path_eligibility"]["projections.*.*"] == "ineligible"


def test_overlay_fails_closed_on_artifact_lineage() -> None:
    frozen = {"outcome": "nominate_token_local_vs_context_dependent"}
    panels = {panel: {"integrity_runtime_pass": True, "approximate_equivariance_pass": True} for panel in PANEL_NAMES}
    overlay = make_eligibility_overlay(frozen, panels, artifact_lineage_valid=False)
    assert overlay["artifact_lineage_valid"] is False
    assert overlay["interpretation_authorized"] is False
    assert overlay["architecture_promotion_status"] == "technically_ineligible"
    assert all(value == "ineligible" for key, value in overlay["path_eligibility"].items() if key != "numerical_null_qa.*")


def test_overlay_fails_closed_on_baseline_runtime_failure() -> None:
    frozen = {"outcome": "nominate_token_local_vs_context_dependent"}
    panels = {panel: {"integrity_runtime_pass": True, "approximate_equivariance_pass": True} for panel in PANEL_NAMES}
    panels[PANEL_NAMES[0]]["integrity_runtime_pass"] = False
    panels[PANEL_NAMES[0]]["approximate_equivariance_pass"] = False
    overlay = make_eligibility_overlay(frozen, panels, artifact_lineage_valid=True)
    assert overlay["artifact_lineage_valid"] is True
    assert overlay["runtime_lineage_valid"] is False
    assert overlay["interpretation_authorized"] is False
    assert overlay["path_eligibility"]["schema_version"] == "ineligible"
    assert overlay["path_eligibility"]["task_results.*.*"] == "ineligible"
    assert overlay["architecture_promotion_status"] == "technically_ineligible"


def _synthetic_grid() -> tuple[np.ndarray, np.ndarray, list[dict[str, str]]]:
    reference = np.zeros((200, 768), dtype=np.float32)
    reference[:, 0] = 1.0
    rows: list[dict[str, str]] = []
    bins = ["4-8", "9-16", "17-32", "33-64", "65-128"]
    for bin_name in bins:
        for base in range(20):
            rows.extend(({"row_id": f"{bin_name}:{base}:0", "length_bin": bin_name},
                         {"row_id": f"{bin_name}:{base}:1", "length_bin": bin_name}))
    candidate = np.concatenate([reference[2 * base:2 * base + 2] for base in range(100) for _ in range(6)], axis=0)
    return reference, candidate, rows


def _candidate_index(base: int, shift_index: int, row: int = 0) -> int:
    return base * 12 + shift_index * 2 + row


def test_score_grid_enforces_cell_panel_and_catastrophic_budgets() -> None:
    reference, candidate, rows = _synthetic_grid()
    two_in_one_cell = candidate.copy()
    for base in (0, 1):
        two_in_one_cell[_candidate_index(base, 0), 1] = 2.1e-5
    assert score_grid(reference, two_in_one_cell, rows)["status"] == "PASS"

    three_in_one_cell = two_in_one_cell.copy()
    three_in_one_cell[_candidate_index(2, 0), 1] = 2.1e-5
    assert score_grid(reference, three_in_one_cell, rows)["status"] == "FAIL"

    seven_panelwide = candidate.copy()
    for shift_index in range(6):
        seven_panelwide[_candidate_index(0, shift_index), 1] = 2.1e-5
    seven_panelwide[_candidate_index(20, 0), 1] = 2.1e-5
    score = score_grid(reference, seven_panelwide, rows)
    assert score["primary_failures_panel"] == 7 and score["status"] == "FAIL"

    catastrophic = candidate.copy()
    catastrophic[_candidate_index(0, 0), 1] = 5.1e-5
    score = score_grid(reference, catastrophic, rows)
    assert score["catastrophic_failures_panel"] == 1 and score["status"] == "FAIL"


def test_cache_round_trip_checks_bytes_and_row_ids(tmp_path: Path) -> None:
    left = tmp_path / "left.npy"; right = tmp_path / "right.npy"
    np.save(left, np.arange(12, dtype=np.float32).reshape(3, 4), allow_pickle=False)
    shutil.copyfile(left, right)
    assert cache_round_trip(left, right, ["a", "b", "c"], ["a", "b", "c"])["status"] == "PASS"
    assert cache_round_trip(left, right, ["a", "b", "c"], ["a", "c", "b"])["status"] == "FAIL"
    changed = np.load(right, allow_pickle=False); changed[0, 0] = 99; np.save(right, changed, allow_pickle=False)
    assert cache_round_trip(left, right, ["a", "b", "c"], ["a", "b", "c"])["status"] == "FAIL"


def test_staging_claim_is_atomic_and_create_once(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(atlas_rope_v7, "RUN_ROOT", tmp_path / "run")
    first = atlas_rope_v7.new_staging("panel", "a" * 64)
    assert first.is_dir()
    with pytest.raises(RuntimeError, match="stale or concurrent"):
        atlas_rope_v7.new_staging("panel", "a" * 64)


def test_review_binding_detects_artifact_mutation(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    artifact = tmp_path / "artifact.json"; artifact.write_text("before", encoding="utf-8")
    digest = sha256_file(artifact)
    review = tmp_path / "review.md"; review.write_text(f"VERDICT: SHIP\nreviewed {digest}\n", encoding="utf-8")
    monkeypatch.setattr(controller, "ROOT", tmp_path)
    binding = {"path": "review.md", "sha256": sha256_file(review), "reviewed_sha256": digest}
    controller._verify_review_binding(binding, artifact)
    artifact.write_text("after", encoding="utf-8")
    with pytest.raises(RuntimeError, match="review binding drift"):
        controller._verify_review_binding(binding, artifact)


def test_review_ship_requires_one_unambiguous_anchored_verdict(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    artifact = tmp_path / "artifact.json"; artifact.write_text("candidate", encoding="utf-8")
    digest = sha256_file(artifact)
    review = tmp_path / "review.md"
    review.write_text(f"VERDICT: BLOCK\nquoted prior line:\nVERDICT: SHIP\n{digest}\n", encoding="utf-8")
    monkeypatch.setattr(controller, "ROOT", tmp_path)
    with pytest.raises(RuntimeError, match="does not SHIP"):
        controller._review_ship(review, artifact)


def test_terminal_guard_fails_closed_on_unreadable_terminal(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    terminal = tmp_path / "TERMINAL.json"; terminal.write_text("{}", encoding="utf-8")
    monkeypatch.setattr(controller, "TERMINAL", terminal)
    with pytest.raises(RuntimeError, match="unreadable terminal"):
        controller._assert_not_terminal()


def test_terminalization_cannot_interleave_lifecycle_promotion(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    run_root = tmp_path / "run"
    monkeypatch.setattr(atlas_rope_v7, "RUN_ROOT", run_root)
    monkeypatch.setattr(controller, "RUN_ROOT", run_root)
    monkeypatch.setattr(controller, "TERMINAL", run_root / "TERMINAL.json")
    with controller.lifecycle_lock():
        with pytest.raises(RuntimeError, match="holds attempt-lifecycle"):
            controller.terminalize(tmp_path / "unused-key.pem", "TERMINAL_TEST", "race")
    assert not (run_root / "TERMINAL.json").exists()


def test_attempt11_implementation_has_no_training_primitives() -> None:
    assert controller._tree_has_forbidden_training(ROOT) == []


def test_transitive_runtime_dependencies_are_discovered_and_regular() -> None:
    dependencies = set(controller._runtime_dependency_paths(ROOT))
    assert {
        "scripts/run_atlas_rope_v5.py",
        "scripts/atlas_rope_v6.py",
        "scripts/run_atlas_rope_v6.py",
        "scripts/run_atlas_rope_v6_science.py",
        "scripts/msae_measurement_v2_run.py",
        "scripts/extract_atlas_discovery_v3_3.py",
        "scripts/analyze_atlas_discovery_v3_3.py",
        "scripts/atlas_discovery_v3_3_analysis.py",
        "configs/atlas_rope_v5/prescore.json",
        "configs/atlas_rope_v6/science_adapter.json",
    }.issubset(dependencies)
    assert all((ROOT / raw).is_file() and not (ROOT / raw).is_symlink() for raw in dependencies)


def test_prescore_panels_have_exact_support_lineage_and_no_pud() -> None:
    manifest = read_json(DATA_ROOT / "manifest.json")
    assert set(manifest["panels"]) == set(PANEL_NAMES)
    assert manifest["model_inference_performed"] is False
    for panel in PANEL_NAMES:
        root = DATA_ROOT / panel
        panel_manifest = read_json(root / "panel.json")
        assert panel_manifest["status"] == "FROZEN_UNOPENED"
        assert set(panel_manifest["support"]) == {"4-8", "9-16", "17-32", "33-64", "65-128"}
        assert all(row["retained"] == 20 and row["documents"] >= 10 and row["max_per_document"] <= 2 for row in panel_manifest["support"].values())
        for name, spec in panel_manifest["children"].items():
            assert sha256_file(root / name) == spec["sha256"]
        text = "\n".join(path.read_text(encoding="utf-8") for path in root.iterdir() if path.suffix in {".json", ".jsonl"})
        assert "PUD" not in text
        references, candidates, rows = read_jsonl(root / "references.jsonl"), read_jsonl(root / "candidates.jsonl"), read_jsonl(root / "rows.jsonl")
        assert (len(references), len(candidates), len(rows)) == (100, 600, 200)
        assert all([int(unit["shift"]) for unit in candidates[start:start + 6]] == [1, 4, 8, 16, 32, 64]
                   for start in range(0, 600, 6))
        assert [str(row_id) for unit in references for row_id in unit["row_ids"]] == [str(row["row_id"]) for row in rows]
        assert len({str(row_id) for unit in candidates for row_id in unit["row_ids"]}) == 1200


def test_childes_canonical_group_and_raw_block_lineage() -> None:
    selected = read_jsonl(DATA_ROOT / "ENGLISH_CHILDES_CTETEX/selected_bases.jsonl")
    childes = [row for row in selected if row["source"].endswith(":CHILDES")]
    assert len(childes) == 20
    groups: dict[str, int] = {}
    tuples: dict[str, bytes] = {}
    for row in childes:
        lineage = row["raw_lineage"]
        canonical = json.dumps([lineage["corpus_name"], lineage["child_name"]], ensure_ascii=False, separators=(",", ":")).encode("utf-8")
        digest = hashlib.sha256(canonical).hexdigest()
        assert lineage["canonical_group_tuple_sha256"] == digest
        assert lineage["derived_group_id"] == "childes_group:" + digest[:24]
        assert row["document_group"] == "CHILDES:" + lineage["derived_group_id"]
        path = ROOT / lineage["raw_path"]
        assert sha256_file(path) == lineage["raw_sha256"]
        blocks = [value for value in path.read_text(encoding="utf-8").split("\n\n") if value.strip()]
        block = blocks[int(lineage["raw_block_index_one_based"]) - 1]
        assert hashlib.sha256(block.encode("utf-8")).hexdigest() == lineage["raw_block_sha256"]
        assert f"# sent_id = {lineage['sent_id']}" in block
        groups[lineage["derived_group_id"]] = groups.get(lineage["derived_group_id"], 0) + 1
        assert lineage["derived_group_id"] not in tuples or tuples[lineage["derived_group_id"]] == canonical
        tuples[lineage["derived_group_id"]] = canonical
    assert len(groups) >= 10 and max(groups.values()) <= 2


def test_validation_raw_root_allowlist_and_pud_isolated() -> None:
    raw = ROOT / "data/atlas_rope_v7_attempt11_raw"
    assert {path.name for path in raw.iterdir()} == {"UD_English-CHILDES", "UD_English-CTeTex", "UD_Czech-PDT"}
    rejection = read_json(ROOT / "data/atlas_rope_v7_attempt11_rejected_scouting/REJECTION.json")
    assert rejection["status"] == "REJECTED_NO_ATTEMPT11_INFERENCE"
    assert rejection["validation_root_membership"] is False
    assert rejection["model_inference_performed"] is False


def test_gate_contract_exact_values() -> None:
    assert gate_contract() == read_json(ROOT / "configs/atlas_rope_v7/amendment.json")["gate"]
