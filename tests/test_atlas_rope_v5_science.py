from __future__ import annotations

import copy
import json
import sys
from pathlib import Path

import pytest
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import run_atlas_rope_v5_science as science


def test_frozen_science_contract_and_analysis_settings_match() -> None:
    config = science.verify_frozen_contract()
    old = json.loads((ROOT / config["frozen_scoring_config"]["path"]).read_text(encoding="utf-8"))
    assert config["frozen_analysis_settings"] == old["analysis"]
    assert config["allowed_adapter_changes"] == [
        "config_schema", "run_result_namespace", "technical_qa_verification",
        "science_authorization_verification", "post_load_sdpa_assertion", "signed_artifact_schema",
    ]
    assert set(config["forbidden_scientific_changes"]) == {
        "task_definitions", "relation_definitions", "intervention_definitions", "projection_organizations",
        "projection_ranks", "ridge_alphas", "nuisance_columns", "bootstrap", "decision_thresholds",
    }


def test_every_frozen_function_hash_is_present_and_mutation_changes_hash(tmp_path: Path) -> None:
    config = science.verify_frozen_contract()
    for raw, expected in config["frozen_function_hashes"].items():
        assert science._ast_function_hashes(ROOT / raw, set(expected)) == expected
    source = ROOT / "scripts/atlas_discovery_v3_3_analysis.py"
    mutated = tmp_path / source.name
    mutated.write_text(source.read_text(encoding="utf-8").replace("return float", "return  float", 1), encoding="utf-8")
    expected = config["frozen_function_hashes"]["scripts/atlas_discovery_v3_3_analysis.py"]
    assert science._ast_function_hashes(mutated, set(expected)) != expected


def test_effective_context_changes_only_run_namespace_and_resolved_identity() -> None:
    scoring, prescore, manifest = science._science_context()
    effective_scoring, effective_prescore, effective_manifest = science._effective_analysis_context()
    scoring_copy = copy.deepcopy(effective_scoring)
    scoring_copy.pop("_resolved_sha256")
    assert scoring_copy == scoring
    prescore_copy = copy.deepcopy(effective_prescore)
    prescore_copy["run_root"] = prescore["run_root"]
    assert prescore_copy == prescore
    assert effective_manifest == manifest
    assert effective_scoring["analysis"] == scoring["analysis"]


def test_science_authorization_failure_prevents_model_load(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    loaded = False
    monkeypatch.setattr(science, "_verify_science_authorization",
                        lambda: (_ for _ in ()).throw(RuntimeError("dual validation unavailable")))

    def load(*args: object, **kwargs: object) -> object:
        nonlocal loaded
        loaded = True
        return object()

    monkeypatch.setattr(science, "_load_model", load)
    with pytest.raises(RuntimeError, match="dual validation unavailable"):
        science.extract_source("EWT", tmp_path / "key.pem")
    assert loaded is False


def test_adapter_binding_contains_exact_function_and_file_inventories() -> None:
    config = science.verify_frozen_contract()
    binding = science.science_adapter_binding()
    assert binding["config_sha256"] == science.sha256_file(science.ADAPTER_CONFIG)
    assert binding["adapter_sha256"] == science.sha256_file(Path(science.__file__).resolve())
    assert binding["frozen_files"] == config["frozen_files"]
    assert binding["frozen_function_hashes"] == config["frozen_function_hashes"]


def _passing_cell(*, coordinate_failures: int = 0, failing_rows: int = 0) -> dict[str, object]:
    return {
        "status": "PASS", "rows": 40, "width": 768,
        "coordinate_failing_elements": coordinate_failures,
        "coordinate_failing_rows": failing_rows,
        "relative_l2_failing_rows": 0, "cosine_failing_rows": 0, "nonfinite_rows": 0,
        "budgets": {"coordinate_failing_elements": 30, "coordinate_failing_rows": 2,
                    "relative_l2_failing_rows": 0, "cosine_failing_rows": 0},
        "maxima": {"absolute_difference": 2.1e-5, "required_atol": 2.01e-5,
                   "relative_l2": 4e-6, "cosine_distance": 6e-12},
    }


def test_grid_bridge_preserves_allowed_frozen_budget_failures() -> None:
    cells = {f"cell-{index}": _passing_cell(coordinate_failures=30 if index == 0 else 0,
                                             failing_rows=2 if index == 0 else 0)
             for index in range(30)}
    translated = science._grid_bridge_stat({"status": "PASS", "required_cells": 30, "cells": cells})
    assert translated["status"] == "PASS"
    assert translated["cells"]["cell-0"]["coordinate_failing_elements"] == 30
    assert translated["cells"]["cell-0"]["coordinate_failing_rows"] == 2
    cells["cell-0"] = _passing_cell(coordinate_failures=31, failing_rows=2)
    with pytest.raises(RuntimeError, match="frozen-budget PASS"):
        science._grid_bridge_stat({"status": "PASS", "required_cells": 30, "cells": cells})


def test_attempt7_bridge_uses_exact_family_segments_and_counts() -> None:
    reference, candidate, lineage = science._retained_attempt7_pair()
    caps = {"atol": 2e-5, "relative_l2": 1e-5, "cosine_distance": 1e-11}
    panels = science._attempt7_family_panels(reference, candidate, lineage, caps)
    assert panels["legacy"]["uniform_shift"]["rows"] == 32
    assert panels["legacy"]["prefix_position_only"]["rows"] == 16
    assert panels["fresh"]["uniform_shift"]["rows"] == 16
    assert panels["fresh"]["prefix_position_only"]["rows"] == 8
    assert all(stat["status"] == "PASS" for panel in panels.values() for stat in panel.values())
    assert panels["legacy"]["uniform_shift"] is not panels["legacy"]["prefix_position_only"]
    covered = [index for indices in lineage["family_indices"].values() for index in indices]
    assert sorted(covered) == list(range(72))


def test_attempt8_bridge_scores_base_reference_with_frozen_grid_budgets() -> None:
    reference, candidate, _ = science._verify_attempt8_history()
    rows = science.read_jsonl(science.ATTEMPT8_DATA_ROOT / "EWT_calibration/rows.jsonl")
    score = science.score_grid(reference, candidate, rows, atol=2e-5,
                               relative_l2_cap=1e-5, cosine_cap=1e-11)
    translated = science._grid_bridge_stat(score)
    assert reference.shape == (200, 768) and candidate.shape == (1200, 768)
    assert translated["status"] == "PASS" and translated["rows"] == 1200


def test_sentinel_bridge_preserves_exact_family_pair_scores() -> None:
    rows = []
    for family, width in (("uniform_shift", 2), ("prefix_position_only", 1)):
        for index in range(8):
            score = _passing_cell()
            score["rows"] = width
            score["budgets"] = {"coordinate_failing_elements": 0, "coordinate_failing_rows": 0,
                                "relative_l2_failing_rows": 0, "cosine_failing_rows": 0}
            rows.append({"family": family, "pair_id": f"{family}-{index}", "score": score})
    grouped = science._sentinel_bridge_stats(rows)
    assert grouped["uniform_shift"]["pairs"] == 8 and grouped["uniform_shift"]["rows"] == 16
    assert grouped["prefix_position_only"]["pairs"] == 8 and grouped["prefix_position_only"]["rows"] == 8
    assert grouped["uniform_shift"]["pair_scores"][0]["pair_id"] == "uniform_shift-0"
