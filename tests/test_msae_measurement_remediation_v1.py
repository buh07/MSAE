from __future__ import annotations

import ast
import builtins
import hashlib
import importlib.util
import json
import math
import os
from pathlib import Path
import socket
import subprocess
import sys
from typing import Any

import numpy as np
import pytest


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))

import msae_measurement_remediation_v1 as remediation  # noqa: E402


SHA_A = "a" * 64
SHA_B = "b" * 64
SHA_C = "c" * 64
SHA_D = "d" * 64
EXPECTED_PUBLIC = {
    "payload_sha256",
    "select_replay_tolerance",
    "summarize_functional_reproducibility",
    "validate_draft_config",
    "verify_dependency",
    "build_stage_a",
    "build_stage_b",
    "build_stage_c",
}


def _dependency_sha256() -> str:
    return hashlib.sha256((SCRIPTS / "msae_measurement_v2.py").read_bytes()).hexdigest()


def _row_digest(row_ids: list[str]) -> str:
    raw = json.dumps(row_ids, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def _stratum(stratum_id: str = "s1") -> dict[str, Any]:
    rows = ["r1", "r2"]
    prefix = "" if stratum_id == "s1" else f"{stratum_id}-"
    return {
        "stratum_id": stratum_id,
        "source_role": "calibration",
        "source_revision": SHA_A,
        "partition": "calibration-public",
        "model_id": "model",
        "checkpoint_id": "checkpoint",
        "code_sha256": SHA_B,
        "environment_sha256": SHA_C,
        "dtype": "float32",
        "pooling_path": "canonical_mean",
        "row_ids_sha256": _row_digest(rows),
        "input_sha256": SHA_D,
        "reference_evaluation_id": f"{prefix}reference",
        "repeat_evaluation_ids": [f"{prefix}repeat-1", f"{prefix}repeat-2", f"{prefix}repeat-3"],
    }


def _config(*, ready: bool = True, two_strata: bool = False) -> dict[str, Any]:
    strata = [_stratum()]
    if two_strata:
        strata.append(_stratum("s2"))
    stage_a = [
        "candidate_confirmation_source",
        "immutable_source_revision",
        "independent_grouping_provenance",
        "label_support_audit",
        "construct_inventory",
        "counterfactual_template_specification",
        "tolerance_ladder_frozen",
        "dependency_attestation",
    ]
    stage_b = [
        "calibration_replay",
        "selected_replay_tolerance",
        "cached_noop_hash_replay",
        "canonical_pooling_qa",
        "counterfactual_cache_alignment_qa",
    ]
    categories = {
        "localization": ["localization_primary"],
        "functional_reproducibility": ["functional_reproducibility_primary"],
        "collateral": ["collateral_primary"],
        "counterfactual": ["counterfactual_primary"],
        "baseline": ["baseline_primary"],
    }
    return {
        "schema_version": "msae_measurement_remediation_config_v1",
        "protocol_id": "synthetic-protocol",
        "artifact_schema_version": "msae_measurement_remediation_artifact_v1",
        "endpoint_schema_version": "msae_endpoint_evidence_v1",
        "replay_bundle_schema_version": "msae_calibration_replay_bundle_v1",
        "dependency": {
            "path": "scripts/msae_measurement_v2.py",
            "sha256": _dependency_sha256(),
        },
        "replay": {
            "source_role": "calibration",
            "source_revision": SHA_A if ready else None,
            "partition": "calibration-public" if ready else None,
            "strata": strata if ready else [],
            "tolerance_ladder": [[1e-7, 0.0], [1e-5, 1e-6]] if ready else [],
            "safety_factor": 2.0 if ready else None,
        },
        "functional_reproducibility": {
            "minimum_checkpoints": 3 if ready else None,
            "checkpoints": [
                {
                    "model_id": "m",
                    "training_run_id": f"run-{index}",
                    "training_run_digest": char * 64,
                    "checkpoint_id": f"cp-{index}",
                    "checkpoint_sha256": str(index + 1) * 64,
                    "seed": index + 10,
                }
                for index, char in enumerate("abc")
            ]
            if ready
            else [],
            "families": {"structure": ["task-a", "task-b"]} if ready else {},
            "maximum_spread": {"recovery": 0.1, "leakage": 0.1, "selectivity": 0.1}
            if ready
            else {"recovery": None, "leakage": None, "selectivity": None},
        },
        "stages": {
            "A": {"purpose": "calibration_replay_candidate", "required": stage_a, "optional": []},
            "B": {"purpose": "confirmation_scoring_candidate", "required": stage_b, "optional": []},
            "C": {
                "purpose": "decision_review_candidate",
                "required_by_category": categories if ready else {name: [] for name in categories},
                "optional": ["diagnostic_optional"],
            },
        },
    }


def _raw_config(*, ready: bool = True, two_strata: bool = False) -> tuple[bytes, str]:
    raw = (json.dumps(_config(ready=ready, two_strata=two_strata), indent=2, sort_keys=True) + "\n").encode()
    return raw, hashlib.sha256(raw).hexdigest()


def _observation(stratum: dict[str, Any], evaluation_id: str, values: np.ndarray) -> dict[str, Any]:
    row_ids = ["r1", "r2"]
    result = {
        key: stratum[key]
        for key in (
            "stratum_id",
            "source_role",
            "source_revision",
            "partition",
            "model_id",
            "checkpoint_id",
            "code_sha256",
            "environment_sha256",
            "dtype",
            "pooling_path",
            "row_ids_sha256",
            "input_sha256",
        )
    }
    result.update(
        {
            "evaluation_id": evaluation_id,
            "row_ids": row_ids,
            "values": values,
            "payload_sha256": remediation.payload_sha256(values, row_ids),
        }
    )
    return result


def _bundle(raw: bytes, *, two_strata: bool = False, delta: float = 0.0) -> dict[str, Any]:
    config = json.loads(raw)
    digest = hashlib.sha256(raw).hexdigest()
    observations: dict[str, Any] = {}
    for stratum in config["replay"]["strata"]:
        reference = stratum["reference_evaluation_id"]
        repeat_1, repeat_2, repeat_3 = stratum["repeat_evaluation_ids"]
        values = {
            reference: np.array([[1.0], [2.0]], dtype=np.float32),
            repeat_1: np.array([[1.0 + delta], [2.0]], dtype=np.float32),
            repeat_2: np.array([[1.0], [2.0]], dtype=np.float32),
            repeat_3: np.array([[1.0], [2.0]], dtype=np.float32),
        }
        observations[stratum["stratum_id"]] = {
            evaluation_id: _observation(stratum, evaluation_id, array)
            for evaluation_id, array in values.items()
        }
    registry_raw = (
        json.dumps(config["replay"]["strata"], sort_keys=True, separators=(",", ":"), ensure_ascii=False)
        + "\n"
    ).encode()
    return {
        "schema_version": config["replay_bundle_schema_version"],
        "protocol_config_sha256": digest,
        "replay_registry_sha256": hashlib.sha256(registry_raw).hexdigest(),
        "source_role": "calibration",
        "source_revision": SHA_A,
        "partition": "calibration-public",
        "observations": observations,
    }


def _evidence(config: dict[str, Any], config_sha: str, name: str, category: str, *, status: str = "eligible") -> dict[str, Any]:
    return {
        "schema_version": config["endpoint_schema_version"],
        "protocol_config_sha256": config_sha,
        "endpoint_name": name,
        "category": category,
        "status": status,
        "reasons": [] if status == "eligible" else ["synthetic_block"],
        "evidence_artifact_sha256": SHA_A if status != "not_run" else None,
        "observed_value": 1.0 if status != "not_run" else None,
    }


def _stage_a_evidence(raw: bytes) -> dict[str, Any]:
    config = json.loads(raw)
    digest = hashlib.sha256(raw).hexdigest()
    return {
        name: _evidence(config, digest, name, "stage_a")
        for name in config["stages"]["A"]["required"]
        if name != "dependency_attestation"
    }


def test_public_surface_is_exact() -> None:
    assert set(remediation.__all__) == EXPECTED_PUBLIC
    assert all(callable(getattr(remediation, name)) for name in EXPECTED_PUBLIC)


def test_payload_hash_binds_dtype_shape_rows_and_c_order() -> None:
    values = np.array([[1.0, 2.0], [3.0, 4.0]], dtype=np.float32)
    assert remediation.payload_sha256(values, ["r1", "r2"]) == remediation.payload_sha256(
        np.asfortranarray(values), ["r1", "r2"]
    )
    assert remediation.payload_sha256(values, ["r1", "r2"]) != remediation.payload_sha256(
        values[::-1].copy(), ["r2", "r1"]
    )
    with pytest.raises(ValueError, match="float32"):
        remediation.payload_sha256(values.astype(np.float64), ["r1", "r2"])
    with pytest.raises(ValueError, match="unique"):
        remediation.payload_sha256(values, ["r1", "r1"])
    with pytest.raises(ValueError, match="finite"):
        remediation.payload_sha256(np.array([[math.nan]], dtype=np.float32), ["r1"])


def test_exact_repeat_selector_uses_all_pairs_and_allows_equal_payloads() -> None:
    raw, digest = _raw_config()
    result = remediation.select_replay_tolerance(raw, digest, _bundle(raw))
    assert result["status"] == "eligible"
    assert result["selected_index"] == 0
    report = result["strata"][0]
    assert report["pair_count"] == 6
    assert report["coordinate_comparison_count"] == 12
    assert len(set(report["payload_sha256"].values())) == 1
    assert report["pass_by_candidate"] == [True, True]


def test_selector_is_multi_stratum_and_selects_first_global_pass() -> None:
    raw, digest = _raw_config(two_strata=True)
    result = remediation.select_replay_tolerance(raw, digest, _bundle(raw, two_strata=True, delta=2e-6))
    assert result["status"] == "eligible"
    assert result["selected_index"] == 1
    assert result["pass_matrix"] == {"s1": [False, True], "s2": [False, True]}


def test_selector_has_no_extrapolation_and_rejects_role_or_payload_forgery() -> None:
    raw, digest = _raw_config()
    no_pass = remediation.select_replay_tolerance(raw, digest, _bundle(raw, delta=1e-2))
    assert no_pass["status"] == "ineligible"
    assert no_pass["selected_tolerance"] is None
    forged_role = _bundle(raw)
    forged_role["source_role"] = "confirmation"
    with pytest.raises(ValueError, match="calibration"):
        remediation.select_replay_tolerance(raw, digest, forged_role)
    forged_payload = _bundle(raw)
    forged_payload["observations"]["s1"]["repeat-1"]["payload_sha256"] = SHA_A
    with pytest.raises(ValueError, match="payload"):
        remediation.select_replay_tolerance(raw, digest, forged_payload)


def test_selector_rejects_invalid_ladder_alignment_and_overflow() -> None:
    config = _config()
    config["replay"]["tolerance_ladder"] = [[0.0, 1e-5]]
    raw = (json.dumps(config) + "\n").encode()
    with pytest.raises(ValueError, match="atol"):
        remediation.select_replay_tolerance(raw, hashlib.sha256(raw).hexdigest(), _bundle(raw))

    raw, digest = _raw_config()
    misaligned = _bundle(raw)
    misaligned["observations"]["s1"]["repeat-1"]["row_ids"] = ["r2", "r1"]
    with pytest.raises(ValueError, match="row"):
        remediation.select_replay_tolerance(raw, digest, misaligned)

    config = _config()
    config["replay"]["safety_factor"] = 1e308
    raw = (json.dumps(config) + "\n").encode()
    with pytest.raises(ValueError, match="finite"):
        remediation.select_replay_tolerance(raw, hashlib.sha256(raw).hexdigest(), _bundle(raw, delta=1e20))


def test_selector_binds_global_source_lineage_to_every_stratum() -> None:
    config = _config()
    config["replay"]["source_revision"] = "e" * 64
    raw = (json.dumps(config) + "\n").encode()
    with pytest.raises(ValueError, match="source revision"):
        remediation.select_replay_tolerance(raw, hashlib.sha256(raw).hexdigest(), _bundle(raw))
    config = _config()
    config["replay"]["partition"] = "other-calibration-partition"
    raw = (json.dumps(config) + "\n").encode()
    with pytest.raises(ValueError, match="partition"):
        remediation.select_replay_tolerance(raw, hashlib.sha256(raw).hexdigest(), _bundle(raw))


@pytest.mark.parametrize("role", ["discovery", "confirmation", "final", "blind", "private"])
def test_selector_refuses_every_noncalibration_role(role: str) -> None:
    raw, digest = _raw_config()
    bundle = _bundle(raw)
    bundle["source_role"] = role
    with pytest.raises(ValueError, match="calibration"):
        remediation.select_replay_tolerance(raw, digest, bundle)


@pytest.mark.parametrize(
    "ladder",
    [
        [[1e-5]],
        [[1e-5, 1e-6], [1e-6, 2e-6]],
        [[1e-5, 1e-6], [2e-5, 5e-7]],
        [[1e-5, 1e-6], [1e-5, 1e-6]],
    ],
)
def test_selector_rejects_malformed_or_incomparable_ladders(ladder: list[list[float]]) -> None:
    config = _config()
    config["replay"]["tolerance_ladder"] = ladder
    raw = (json.dumps(config) + "\n").encode()
    with pytest.raises(ValueError, match="tolerance|ladder"):
        remediation.select_replay_tolerance(raw, hashlib.sha256(raw).hexdigest(), _bundle(raw))


def test_selector_boundary_safety_factor_and_mapping_order_are_exact() -> None:
    config = _config()
    value = np.float32(1e-6)
    config["replay"]["safety_factor"] = 2.0
    config["replay"]["tolerance_ladder"] = [[2.0 * float(value), 0.0]]
    raw = (json.dumps(config) + "\n").encode()
    digest = hashlib.sha256(raw).hexdigest()
    bundle = _bundle(raw)
    observation = bundle["observations"]["s1"]["repeat-1"]
    observation["values"] = np.array([[value], [0.0]], dtype=np.float32)
    for evaluation_id in ("reference", "repeat-2", "repeat-3"):
        other = bundle["observations"]["s1"][evaluation_id]
        other["values"] = np.zeros((2, 1), dtype=np.float32)
        other["payload_sha256"] = remediation.payload_sha256(other["values"], other["row_ids"])
    observation["payload_sha256"] = remediation.payload_sha256(observation["values"], observation["row_ids"])
    first = remediation.select_replay_tolerance(raw, digest, bundle)
    assert first["status"] == "eligible"
    assert first["strata"][0]["maximum_ratio_by_candidate"] == [1.0]
    reversed_bundle = dict(bundle)
    reversed_bundle["observations"] = {
        stratum_id: dict(reversed(list(evaluations.items())))
        for stratum_id, evaluations in reversed(list(bundle["observations"].items()))
    }
    assert remediation.select_replay_tolerance(raw, digest, reversed_bundle) == first


@pytest.mark.parametrize("kind", ["empty", "nonfinite"])
def test_selector_rejects_empty_or_nonfinite_observation_arrays(kind: str) -> None:
    raw, digest = _raw_config()
    bundle = _bundle(raw)
    observation = bundle["observations"]["s1"]["repeat-1"]
    observation["values"] = (
        np.empty((0, 1), dtype=np.float32)
        if kind == "empty"
        else np.array([[np.nan], [2.0]], dtype=np.float32)
    )
    with pytest.raises(ValueError, match="non-empty and finite"):
        remediation.select_replay_tolerance(raw, digest, bundle)


def test_selector_rejects_duplicate_evaluation_ids_and_mixed_provenance() -> None:
    config = _config()
    config["replay"]["strata"][0]["repeat_evaluation_ids"][1] = "repeat-1"
    raw = (json.dumps(config) + "\n").encode()
    with pytest.raises(ValueError, match="unique"):
        remediation.select_replay_tolerance(raw, hashlib.sha256(raw).hexdigest(), _bundle(raw))
    raw, digest = _raw_config()
    bundle = _bundle(raw)
    bundle["observations"]["s1"]["repeat-2"]["checkpoint_id"] = "other-checkpoint"
    with pytest.raises(ValueError, match="provenance"):
        remediation.select_replay_tolerance(raw, digest, bundle)


def _checkpoints() -> list[dict[str, Any]]:
    return _config()["functional_reproducibility"]["checkpoints"]


def _functional_records() -> dict[str, Any]:
    records: dict[str, Any] = {}
    for task_index, task in enumerate(("task-a", "task-b", "task-c")):
        records[task] = {}
        for checkpoint_index, checkpoint in enumerate(_checkpoints()):
            records[task][checkpoint["checkpoint_id"]] = {
                metric: {"status": "eligible", "reasons": [], "value": value}
                for metric, value in {
                    "recovery": 0.8 + task_index * 0.01 + checkpoint_index * 0.01,
                    "leakage": 0.2 + task_index * 0.01 + checkpoint_index * 0.01,
                    "selectivity": 0.6 + checkpoint_index * 0.01,
                }.items()
            }
    return records


def test_functional_reproducibility_reports_ordered_deltas_and_task_first_families() -> None:
    result = remediation.summarize_functional_reproducibility(
        _checkpoints(),
        {"structure": ["task-a", "task-b"], "other": ["task-c"]},
        _functional_records(),
        {"recovery": 0.05, "leakage": 0.05, "selectivity": 0.05},
        minimum_checkpoints=3,
    )
    summary = result["tasks"]["task-a"]["recovery"]
    assert summary["status"] == "eligible"
    assert summary["pairs"][0] == {
        "checkpoint_i": "cp-0",
        "checkpoint_j": "cp-1",
        "signed_delta": pytest.approx(0.01),
        "absolute_delta": pytest.approx(0.01),
    }
    assert result["families"]["structure"]["recovery"]["status"] == "eligible"
    assert result["families"]["structure"]["recovery"]["checkpoint_values"][0]["value"] == pytest.approx(0.805)


def test_functional_missingness_is_endpoint_specific_and_precedence_is_explicit() -> None:
    records = _functional_records()
    records["task-a"]["cp-0"]["recovery"] = {"status": "not_run", "reasons": ["missing"], "value": None}
    records["task-b"]["cp-1"]["recovery"] = {"status": "ineligible", "reasons": ["bad"], "value": 0.81}
    result = remediation.summarize_functional_reproducibility(
        _checkpoints(),
        {"structure": ["task-a", "task-b"], "other": ["task-c"]},
        records,
        {"recovery": 0.05, "leakage": 0.05, "selectivity": 0.05},
        minimum_checkpoints=3,
    )
    assert result["tasks"]["task-a"]["recovery"]["status"] == "not_run"
    assert result["families"]["structure"]["recovery"]["status"] == "ineligible"
    assert result["families"]["structure"]["recovery"]["checkpoint_values"][1]["value"] == pytest.approx(0.81)
    assert result["families"]["other"]["recovery"]["status"] == "eligible"
    assert result["families"]["structure"]["leakage"]["status"] == "eligible"


def test_missing_single_metric_does_not_erase_sibling_metrics() -> None:
    records = _functional_records()
    del records["task-a"]["cp-0"]["selectivity"]
    result = remediation.summarize_functional_reproducibility(
        _checkpoints(),
        {"structure": ["task-a"]},
        {"task-a": records["task-a"]},
        {"recovery": 0.05, "leakage": 0.05, "selectivity": 0.05},
        minimum_checkpoints=3,
    )
    assert result["tasks"]["task-a"]["recovery"]["status"] == "eligible"
    assert result["tasks"]["task-a"]["leakage"]["status"] == "eligible"
    assert result["tasks"]["task-a"]["selectivity"]["status"] == "not_run"


def test_stable_negative_selectivity_is_reproducible_but_not_localization_success() -> None:
    records = _functional_records()
    for checkpoint in _checkpoints():
        records["task-a"][checkpoint["checkpoint_id"]]["selectivity"]["value"] = -0.2
    result = remediation.summarize_functional_reproducibility(
        _checkpoints(),
        {"structure": ["task-a"]},
        {"task-a": records["task-a"]},
        {"recovery": 0.05, "leakage": 0.05, "selectivity": 0.05},
        minimum_checkpoints=3,
    )
    summary = result["tasks"]["task-a"]["selectivity"]
    assert summary["status"] == "eligible"
    assert summary["localization_status"] == "ineligible"
    assert "nonpositive_selectivity" in summary["localization_reasons"]


def test_functional_registry_lineage_and_derived_overflow_fail_closed() -> None:
    checkpoints = _checkpoints()
    checkpoints[1]["training_run_id"] = checkpoints[0]["training_run_id"]
    with pytest.raises(ValueError, match="one-to-one"):
        remediation.summarize_functional_reproducibility(
            checkpoints,
            {"structure": ["task-a"]},
            {"task-a": _functional_records()["task-a"]},
            {"recovery": 0.05, "leakage": 0.05, "selectivity": 0.05},
            minimum_checkpoints=3,
        )


def test_functional_threshold_boundary_unbounded_metrics_and_minimum_checkpoints() -> None:
    records = _functional_records()
    for index, checkpoint in enumerate(_checkpoints()):
        checkpoint_id = checkpoint["checkpoint_id"]
        records["task-a"][checkpoint_id]["recovery"]["value"] = [0.0, 0.02, 0.01][index]
        records["task-a"][checkpoint_id]["leakage"]["value"] = -2.0 + index * 0.1
        records["task-a"][checkpoint_id]["selectivity"]["value"] = 3.0 + index * 0.1
    result = remediation.summarize_functional_reproducibility(
        _checkpoints(),
        {"structure": ["task-a"]},
        {"task-a": records["task-a"]},
        {"recovery": 0.02, "leakage": 0.2, "selectivity": 0.2},
        minimum_checkpoints=3,
    )
    assert result["tasks"]["task-a"]["recovery"]["status"] == "eligible"
    result = remediation.summarize_functional_reproducibility(
        _checkpoints(),
        {"structure": ["task-a"]},
        {"task-a": records["task-a"]},
        {"recovery": 0.019, "leakage": 0.2, "selectivity": 0.2},
        minimum_checkpoints=3,
    )
    assert result["tasks"]["task-a"]["recovery"]["reasons"] == ["maximum_spread_exceeded"]
    with pytest.raises(ValueError, match="fewer than minimum"):
        remediation.summarize_functional_reproducibility(
            _checkpoints()[:2],
            {"structure": ["task-a"]},
            {"task-a": records["task-a"]},
            {"recovery": 1.0, "leakage": 1.0, "selectivity": 1.0},
            minimum_checkpoints=3,
        )


@pytest.mark.parametrize(
    "field",
    ["training_run_id", "training_run_digest", "checkpoint_id", "checkpoint_sha256", "seed"],
)
def test_every_checkpoint_lineage_component_is_one_to_one(field: str) -> None:
    checkpoints = _checkpoints()
    checkpoints[1][field] = checkpoints[0][field]
    with pytest.raises(ValueError, match="one-to-one"):
        remediation.summarize_functional_reproducibility(
            checkpoints,
            {"structure": ["task-a"]},
            {"task-a": _functional_records()["task-a"]},
            {"recovery": 1.0, "leakage": 1.0, "selectivity": 1.0},
            minimum_checkpoints=3,
        )


def test_task_first_family_sum_overflow_is_an_input_error() -> None:
    tasks = [f"task-{index}" for index in range(4)]
    records: dict[str, Any] = {}
    for task in tasks:
        records[task] = {}
        for checkpoint in _checkpoints():
            records[task][checkpoint["checkpoint_id"]] = {
                "recovery": {"status": "eligible", "reasons": [], "value": 5e307},
                "leakage": {"status": "eligible", "reasons": [], "value": 0.1},
                "selectivity": {"status": "eligible", "reasons": [], "value": 0.2},
            }
    with pytest.raises(ValueError, match="sum must remain finite"):
        remediation.summarize_functional_reproducibility(
            _checkpoints(),
            {"structure": tasks},
            records,
            {"recovery": 1.0, "leakage": 1.0, "selectivity": 1.0},
            minimum_checkpoints=3,
        )

    records = _functional_records()
    records["task-a"]["cp-0"]["recovery"]["value"] = -1.7e308
    records["task-a"]["cp-1"]["recovery"]["value"] = 1.7e308
    with pytest.raises(ValueError, match="finite"):
        remediation.summarize_functional_reproducibility(
            _checkpoints(),
            {"structure": ["task-a"]},
            {"task-a": records["task-a"]},
            {"recovery": 1.0, "leakage": 1.0, "selectivity": 1.0},
            minimum_checkpoints=3,
        )


def test_raw_config_digest_duplicate_keys_and_draft_blockers() -> None:
    raw, digest = _raw_config(ready=False)
    report = remediation.validate_draft_config(raw, digest)
    assert report["status"] == "blocked"
    assert "replay_registry_unset" in report["reasons"]
    assert "stage_c_localization_registry_unset" in report["reasons"]
    with pytest.raises(ValueError, match="digest"):
        remediation.validate_draft_config(raw, SHA_A)
    duplicate = b'{"schema_version":"x","schema_version":"y"}\n'
    with pytest.raises(ValueError, match="duplicate"):
        remediation.validate_draft_config(duplicate, hashlib.sha256(duplicate).hexdigest())


def test_stage_a_and_b_required_registries_are_exact_not_subsets() -> None:
    config = _config()
    config["stages"]["A"]["required"] = ["tolerance_ladder_frozen", "dependency_attestation"]
    raw = (json.dumps(config) + "\n").encode()
    with pytest.raises(ValueError, match="stage A required registry"):
        remediation.validate_draft_config(raw, hashlib.sha256(raw).hexdigest())
    config = _config()
    config["stages"]["B"]["required"] = ["calibration_replay", "selected_replay_tolerance"]
    raw = (json.dumps(config) + "\n").encode()
    with pytest.raises(ValueError, match="stage B required registry"):
        remediation.validate_draft_config(raw, hashlib.sha256(raw).hexdigest())


def test_stage_a_reports_all_missing_records_and_creates_dependency_attestation() -> None:
    raw, digest = _raw_config()
    result = remediation.build_stage_a(raw, digest, {})
    assert result["stage"] == "A"
    assert result["stage_ready"] is False
    assert result["endpoints"]["dependency_attestation"]["status"] == "eligible"
    assert result["endpoints"]["candidate_confirmation_source"]["status"] == "not_run"
    assert len(result["aggregate"]["overall"]["blocking_reasons"]) == 7


def test_three_stage_contract_recomputes_replay_and_optional_is_neutral() -> None:
    raw, digest = _raw_config()
    config = json.loads(raw)
    stage_a = remediation.build_stage_a(raw, digest, _stage_a_evidence(raw))
    assert stage_a["stage_ready"] is True

    stage_b_evidence = {
        name: _evidence(config, digest, name, "stage_b")
        for name in config["stages"]["B"]["required"]
        if name not in {"calibration_replay", "selected_replay_tolerance"}
    }
    stage_b = remediation.build_stage_b(raw, digest, stage_a, _bundle(raw), stage_b_evidence)
    assert stage_b["stage_ready"] is True
    assert stage_b["endpoints"]["calibration_replay"]["observed_value"]["source_role"] == "calibration"

    stage_c_evidence = {}
    for category, names in config["stages"]["C"]["required_by_category"].items():
        for name in names:
            stage_c_evidence[name] = _evidence(config, digest, name, category)
    stage_c_evidence["diagnostic_optional"] = _evidence(
        config, digest, "diagnostic_optional", "optional", status="ineligible"
    )
    stage_c = remediation.build_stage_c(raw, digest, stage_a, stage_b, stage_c_evidence)
    assert stage_c["stage_ready"] is True
    assert stage_c["endpoints"]["diagnostic_optional"]["status"] == "ineligible"
    assert "authorized" not in json.dumps(stage_c).lower()


def test_stage_b_rejects_noncalibration_bundle_and_predecessor_tampering() -> None:
    raw, digest = _raw_config()
    stage_a = remediation.build_stage_a(raw, digest, _stage_a_evidence(raw))
    evidence: dict[str, Any] = {}
    bundle = _bundle(raw)
    bundle["source_role"] = "final"
    with pytest.raises(ValueError, match="calibration"):
        remediation.build_stage_b(raw, digest, stage_a, bundle, evidence)
    forged = json.loads(json.dumps(stage_a))
    forged["stage_ready"] = False
    with pytest.raises(ValueError, match="predecessor"):
        remediation.build_stage_b(raw, digest, forged, _bundle(raw), evidence)


@pytest.mark.parametrize("tamper", ["dependency", "registry", "aggregate", "config"])
def test_stage_b_rejects_every_stage_a_binding_tamper(tamper: str) -> None:
    raw, digest = _raw_config()
    stage_a = remediation.build_stage_a(raw, digest, _stage_a_evidence(raw))
    forged = json.loads(json.dumps(stage_a))
    if tamper == "dependency":
        forged["dependency"]["sha256"] = SHA_A
    elif tamper == "registry":
        forged["requirement_registry_sha256"] = SHA_A
    elif tamper == "aggregate":
        forged["aggregate"]["overall"]["status"] = "not_run"
    else:
        forged["protocol_config_sha256"] = SHA_A
    with pytest.raises(ValueError, match="predecessor"):
        remediation.build_stage_b(raw, digest, forged, _bundle(raw), {})


def test_stage_c_rejects_empty_or_cross_category_duplicate_registries() -> None:
    config = _config()
    config["stages"]["C"]["required_by_category"]["baseline"] = ["collateral_primary"]
    raw = (json.dumps(config) + "\n").encode()
    with pytest.raises(ValueError, match="globally unique"):
        remediation.validate_draft_config(raw, hashlib.sha256(raw).hexdigest())

    config = _config()
    config["stages"]["C"]["required_by_category"]["baseline"] = []
    raw = (json.dumps(config) + "\n").encode()
    digest = hashlib.sha256(raw).hexdigest()
    stage_a = remediation.build_stage_a(raw, digest, _stage_a_evidence(raw))
    stage_b_evidence = {
        name: _evidence(config, digest, name, "stage_b")
        for name in config["stages"]["B"]["required"]
        if name not in {"calibration_replay", "selected_replay_tolerance"}
    }
    stage_b = remediation.build_stage_b(raw, digest, stage_a, _bundle(raw), stage_b_evidence)
    with pytest.raises(ValueError, match="baseline registry"):
        remediation.build_stage_c(raw, digest, stage_a, stage_b, {})


@pytest.mark.parametrize("tamper", ["chain", "dependency", "registry", "aggregate", "config"])
def test_stage_c_rejects_every_stage_b_binding_tamper(tamper: str) -> None:
    raw, digest = _raw_config()
    config = json.loads(raw)
    stage_a = remediation.build_stage_a(raw, digest, _stage_a_evidence(raw))
    stage_b_evidence = {
        name: _evidence(config, digest, name, "stage_b")
        for name in config["stages"]["B"]["required"]
        if name not in {"calibration_replay", "selected_replay_tolerance"}
    }
    stage_b = remediation.build_stage_b(raw, digest, stage_a, _bundle(raw), stage_b_evidence)
    forged = json.loads(json.dumps(stage_b))
    if tamper == "chain":
        forged["prior_stage_sha256"] = SHA_A
    elif tamper == "dependency":
        forged["dependency"]["sha256"] = SHA_A
    elif tamper == "registry":
        forged["requirement_registry_sha256"] = SHA_A
    elif tamper == "aggregate":
        forged["aggregate"]["overall"]["status"] = "not_run"
    else:
        forged["protocol_config_sha256"] = SHA_A
    with pytest.raises(ValueError, match="predecessor"):
        remediation.build_stage_c(raw, digest, stage_a, forged, {})


def test_checked_in_draft_is_digest_bound_and_intentionally_blocked() -> None:
    path = ROOT / "configs" / "msae_measurement_remediation_v1" / "draft.json"
    raw = path.read_bytes()
    result = remediation.validate_draft_config(raw, hashlib.sha256(raw).hexdigest())
    assert result["status"] == "blocked"
    assert result["dependency"]["sha256"] == _dependency_sha256()
    assert len(result["reasons"]) >= 10
    config = json.loads(raw)
    digest = hashlib.sha256(raw).hexdigest()
    fabricated = {
        name: _evidence(config, digest, name, "stage_a")
        for name in config["stages"]["A"]["required"]
        if name != "dependency_attestation"
    }
    assert remediation.build_stage_a(raw, digest, fabricated)["stage_ready"] is False


def test_static_import_and_call_boundaries_are_cpu_only_and_write_free(monkeypatch: pytest.MonkeyPatch) -> None:
    source = (SCRIPTS / "msae_measurement_remediation_v1.py").read_text(encoding="utf-8")
    tree = ast.parse(source)
    allowed_roots = {"__future__", "hashlib", "itertools", "json", "math", "pathlib", "stat", "typing", "numpy", "msae_measurement_v2"}

    def qualified_name(node: ast.AST) -> str | None:
        if isinstance(node, ast.Name):
            return node.id
        if isinstance(node, ast.Attribute):
            prefix = qualified_name(node.value)
            return None if prefix is None else f"{prefix}.{node.attr}"
        return None

    forbidden_qualified = {
        "open",
        "Path.open",
        "Path.write_text",
        "Path.write_bytes",
        "Path.touch",
        "Path.mkdir",
        "Path.unlink",
        "Path.rename",
        "Path.replace",
        "np.save",
        "np.savez",
        "np.savez_compressed",
        "np.savetxt",
        "np.memmap",
    }
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            assert all(alias.name.split(".", 1)[0] in allowed_roots for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            assert (node.module or "").split(".", 1)[0] in allowed_roots
        elif isinstance(node, ast.Call):
            name = qualified_name(node.func)
            assert name not in {"eval", "exec", "__import__", "compile"}
            assert name not in forbidden_qualified
            assert name is None or not name.startswith(("os.", "socket.", "subprocess."))
    forbidden_tokens = {"torch", "transformers", "datasets", "socket", "subprocess", "tmux", "requests", "urlopen"}
    assert not any(token in source.lower() for token in forbidden_tokens)

    def deny_write(file: Any, mode: str = "r", *args: Any, **kwargs: Any) -> Any:
        if any(flag in mode for flag in "wax+"):
            raise AssertionError(f"write attempted: {file}")
        return original_open(file, mode, *args, **kwargs)

    original_open = builtins.open
    original_import = builtins.__import__

    def guarded_import(name: str, *args: Any, **kwargs: Any) -> Any:
        if name.split(".", 1)[0] in {"torch", "transformers", "datasets", "socket", "subprocess"}:
            raise AssertionError(f"forbidden import attempted: {name}")
        return original_import(name, *args, **kwargs)

    def deny_side_effect(*args: Any, **kwargs: Any) -> Any:
        raise AssertionError(f"network/process/write side effect attempted: {args!r} {kwargs!r}")

    monkeypatch.setattr(builtins, "open", deny_write)
    monkeypatch.setattr(builtins, "__import__", guarded_import)
    monkeypatch.setattr(socket, "socket", deny_side_effect)
    monkeypatch.setattr(socket, "create_connection", deny_side_effect)
    for name in ("Popen", "run", "call", "check_call", "check_output"):
        monkeypatch.setattr(subprocess, name, deny_side_effect)
    for name in (
        "system",
        "popen",
        "spawnl",
        "spawnle",
        "spawnlp",
        "spawnlpe",
        "spawnv",
        "spawnve",
        "spawnvp",
        "spawnvpe",
        "posix_spawn",
        "posix_spawnp",
    ):
        if hasattr(os, name):
            monkeypatch.setattr(os, name, deny_side_effect)
    for name in ("write_text", "write_bytes", "touch", "mkdir", "unlink", "rename", "replace"):
        monkeypatch.setattr(Path, name, deny_side_effect)

    spec = importlib.util.spec_from_file_location("_guarded_msae_remediation", SCRIPTS / "msae_measurement_remediation_v1.py")
    assert spec is not None and spec.loader is not None
    guarded = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(guarded)

    values = np.array([[1.0]], dtype=np.float32)
    assert len(guarded.payload_sha256(values, ["r1"])) == 64
    raw, digest = _raw_config()
    replay_bundle = _bundle(raw)
    assert guarded.select_replay_tolerance(raw, digest, replay_bundle)["status"] == "eligible"
    assert guarded.summarize_functional_reproducibility(
        _checkpoints(),
        {"structure": ["task-a"]},
        {"task-a": _functional_records()["task-a"]},
        {"recovery": 0.05, "leakage": 0.05, "selectivity": 0.05},
        minimum_checkpoints=3,
    )["tasks"]["task-a"]["recovery"]["status"] == "eligible"
    assert guarded.validate_draft_config(raw, digest)["status"] == "ready"
    assert guarded.verify_dependency(_dependency_sha256())["sha256"] == _dependency_sha256()
    config = json.loads(raw)
    stage_a = guarded.build_stage_a(raw, digest, _stage_a_evidence(raw))
    stage_b_evidence = {
        name: _evidence(config, digest, name, "stage_b")
        for name in config["stages"]["B"]["required"]
        if name not in {"calibration_replay", "selected_replay_tolerance"}
    }
    stage_b = guarded.build_stage_b(raw, digest, stage_a, replay_bundle, stage_b_evidence)
    stage_c_evidence = {
        name: _evidence(config, digest, name, category)
        for category, names in config["stages"]["C"]["required_by_category"].items()
        for name in names
    }
    assert guarded.build_stage_c(raw, digest, stage_a, stage_b, stage_c_evidence)["stage_ready"] is True


def test_dependency_verifier_rejects_wrong_digest() -> None:
    observed = remediation.verify_dependency(_dependency_sha256())
    assert observed["path"] == "scripts/msae_measurement_v2.py"
    with pytest.raises(ValueError, match="dependency digest"):
        remediation.verify_dependency(SHA_A)
    with pytest.raises(ValueError, match="SHA-256"):
        remediation.verify_dependency("١" * 64)
