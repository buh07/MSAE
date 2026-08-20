from __future__ import annotations

import json
import itertools
import inspect
import os
import socket
import sys
import threading
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any

import numpy as np
import pytest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from msa_completion_common import (FrozenClassOmissionError, InputFirewall,
                                   LiveDrawClaimError,
                                   atomic_write_json,
                                   attest_completion_freeze_record,
                                   chance_score, claim_draw,
                                   cosine_distance, cosine_matched_direction,
                                   deterministic_seed,
                                   draw_group_multiplicities, family_summary,
                                   fit_weighted_ridge_torch, macro_f1,
                                   maybe_finalize_draw_stage,
                                   not_launched_payload,
                                   prepare_draw_resume, register_draw_artifact,
                                   release_claim,
                                   register_pinned_hf_snapshot,
                                   stable_hash, unit_group_multiplicities,
                                   stage_publication_lock,
                                   terminal_state,
                                   weighted_linear_cka, weighted_mean_scale,
                                   weights_from_multiplicities,
                                   write_failure_terminal, write_terminal)
from merge_msae_refit import (aggregate_selectivity,
                              assert_attested_hash,
                              block_mc_uncertainty,
                              collateral_noninferiority_gates,
                              exact_joint_sign_pvalue,
                              frozen_group_bootstrap_maps,
                              grouped_chance_point_leave,
                              grouped_f1_point_leave,
                              intersection_union_pvalue,
                              k2_localization_gate,
                              mandatory_evidence_invalid,
                              negative_sensitivity_simulation,
                              null_imposed_selectivity_test,
                              percentile,
                              primary_specificity_validity,
                              registered_g1_randomization_seed,
                              same_nonzero_direction,
                              specific_leakage_sign_test,
                              simultaneous_block_mc_diagnostics,
                              threshold_boundary_diagnostic,
                              validate_series_terminal)
from render_msae_completion_decision import decide, decision_predicates
from calibrate_msae_completion import (candidate_selection_boundaries,
                                       fixed_probe_eligibility, numerical_rank,
                                       select_candidate)
from run_msae_refit_worker import score_recovery, simple_roundtrip_checks
from run_msae_specificity import (CE_FAMILIES,
                                  frozen_specificity_group_samples,
                                  group_summary,
                                  punctuation_branch_invalid,
                                  registered_matched_random_seed,
                                  specificity_boundary_diagnostic,
                                  specificity_invariants_finite)
from run_msae_stability import stability_draw_finite
import msa_completion_pilot
import msa_completion_common
import calibrate_msae_completion
import freeze_msae_completion
import run_msae_refit_worker
import run_msae_specificity
import run_msae_stability
import build_msae_completion_rows
import atlas_freeze
import verify_msae_completion


def exact_cluster_sign_pvalue(values: list[float] | np.ndarray, minimum_clusters: int) -> float | None:
    array = np.asarray(values, dtype=float)
    if len(array) < minimum_clusters:
        return None
    observed = float(np.mean(array))
    exceed = 0
    for mask in range(1 << len(array)):
        signs = np.asarray([1.0 if mask & (1 << i) else -1.0 for i in range(len(array))])
        exceed += float(np.mean(signs * array)) >= observed
    return exceed / (1 << len(array))


def test_harmful_but_finite_collateral_cannot_pass_existing_checkpoint_gate() -> None:
    bounds = {
        "A_col:g4:sentinel": {"lower": -0.50, "upper": -0.30},
        "A_col:g4:reconstruction_ce": {"lower": 0.01, "upper": 0.02},
    }
    gates = collateral_noninferiority_gates(bounds, ["g4"], ["sentinel"], [])
    assert np.isfinite(bounds["A_col:g4:sentinel"]["lower"])
    assert gates["g4"]["coordinate_lower_at_least_minus_0p02"][
        "A_col:g4:sentinel"] is False
    assert gates["g4"]["passes"] is False


def test_descriptive_g7_specificity_failure_does_not_disable_primary_g2() -> None:
    specificity = {
        job: {"counterfactual_gate_valid": job != "g7",
              "simple_identity_collateral": {"valid": job != "g7"}}
        for job in ["g4", "g5", "g6", "g7"]
    }
    primary = primary_specificity_validity(specificity, ["g4", "g5", "g6"])
    assert primary == {"counterfactual_all_valid": True,
                       "identity_collateral_all_valid": True}


def test_stable_hash_and_source_stratified_draw_are_deterministic() -> None:
    sources = np.asarray(["a", "a", "a", "b", "b"])
    groups = np.asarray(["1", "1", "2", "x", "y"])
    seed = deterministic_seed(20260731, "C2", 3, 17)
    first = draw_group_multiplicities(sources, groups, seed=seed)
    second = draw_group_multiplicities(sources, groups, seed=seed)
    assert first == second
    assert sum(value for (source, _), value in first.items() if source == "a") == 2
    assert sum(value for (source, _), value in first.items() if source == "b") == 2
    assert stable_hash("x", 3, 1) != stable_hash("x", 3, 2)


def test_parent_analysis_row_open_requires_frozen_inventory(
        tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    row_path = tmp_path / "data/atlas_v1/analysis_rows/discovery.task.jsonl"
    row_path.parent.mkdir(parents=True)
    row_path.write_text(json.dumps({"row_id": "v:0", "label": "x"}) + "\n")
    data = type("Data", (), {
        "units": [{"variant_id": "v"}],
        "meta": {"unit_index": np.asarray([0])},
        "records": [{"source": "s", "document_group": "g"}],
        "row_source": np.asarray(["s"], dtype=object),
        "row_group": np.asarray(["g"], dtype=object),
    })()
    firewall = InputFirewall([tmp_path])
    checked: list[Path] = []
    monkeypatch.setattr(msa_completion_common, "ROOT", tmp_path)
    monkeypatch.setattr(
        msa_completion_common, "require_frozen_upstream_file",
        lambda path, _: checked.append(path.resolve()) or "digest")
    rows, labels, sources, groups = msa_completion_common.load_row_file(
        row_path, data, firewall, role="discovery")
    assert checked == [row_path.resolve()]
    assert rows.tolist() == [0]
    assert labels.tolist() == ["x"]
    assert sources.tolist() == ["s"]
    assert groups.tolist() == ["g"]


def test_activation_artifacts_are_inventory_bound_before_legacy_verifier(
        tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    source = tmp_path / "parent"
    role_dir = source / "raw_activations/discovery"
    role_dir.mkdir(parents=True)
    complete = role_dir / "COMPLETE.json"
    artifact = role_dir / "L3.float16.npy"
    atomic_write_json(complete, {"artifacts": {artifact.name: "digest"}})
    artifact.write_bytes(b"activation")
    prebound: list[Path] = []
    firewall = InputFirewall([tmp_path])

    monkeypatch.setattr(
        msa_completion_common, "verify_parent_freeze_attested",
        lambda _firewall, _roles: {"bundle_sha256": "parent"})

    def bind(path: Path, bound_firewall: InputFirewall) -> str:
        resolved = bound_firewall.attest(path)
        prebound.append(resolved)
        return "digest"

    monkeypatch.setattr(msa_completion_common, "require_frozen_upstream_file", bind)

    def legacy(directory: Path, role: str, freeze: dict[str, Any]) -> dict[str, Any]:
        assert role == "discovery" and freeze["bundle_sha256"] == "parent"
        assert complete.resolve() in prebound
        assert artifact.resolve() in prebound
        return {"artifacts": {artifact.name: "digest"}}

    monkeypatch.setattr(atlas_freeze, "verify_activation_complete", legacy)
    result = msa_completion_common.verify_parent_activation(
        source, "discovery", firewall)
    assert result["artifacts"] == {artifact.name: "digest"}


def test_word_sentinels_use_first_subwords_but_token_sentinels_use_all_rows() -> None:
    data = type("Rows", (), {
        "x": np.zeros((4, 2)),
        "meta": {
            "word_index": np.asarray([-1, 0, 0, 1]),
            "continuation_code": np.asarray([0, 1, 2, 1]),
            "record_index": np.asarray([0, 0, 0, 0]),
            "offset": np.asarray([0, 1, 2, 3]),
        },
        "records": [{"labels": {"upos": ["NOUN", "VERB"]}}],
    })()
    word_rows = build_msae_completion_rows.candidate_rows(data, "upos")
    assert word_rows == {"NOUN": [1], "VERB": [3]}
    continuation_rows = build_msae_completion_rows.candidate_rows(
        data, "continuation_status")
    assert continuation_rows == {
        "prefix": [0], "first": [1, 3], "continuation": [2]}
    context_rows = build_msae_completion_rows.candidate_rows(data, "context_offset")
    assert sum(map(len, context_rows.values())) == 4


def test_gpu_uuid_validation_precedes_score_inputs_in_every_gpu_worker() -> None:
    for module, first_score_input in [
        (msa_completion_pilot, "load_activation("),
        (calibrate_msae_completion, "load_activation("),
        (run_msae_refit_worker, "load_activation("),
        (run_msae_stability, "load_activation("),
        (run_msae_specificity, "register_pinned_hf_snapshot("),
    ]:
        source = inspect.getsource(module.main)
        assert source.index("validated_cuda_environment(") < source.index(first_score_input)


def test_baseline_rep_loader_uses_only_discovery_calibration_transform_verifier(
        tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    root = tmp_path / "source"
    path = root / "k2_transforms/job/discovery/pos.float16.npy"
    path.parent.mkdir(parents=True)
    np.save(path, np.zeros((2, 2), dtype=np.float16))
    calls: list[list[str]] = []
    monkeypatch.setattr(
        calibrate_msae_completion, "verify_parent_transform_roles",
        lambda _root, _job, roles, _firewall: calls.append(list(roles)))
    firewall = InputFirewall([tmp_path])
    loaded = calibrate_msae_completion.rep_array(
        root, "job", "discovery", "pos", firewall)
    assert loaded.shape == (2, 2)
    assert calls == [["discovery", "calibration"]]
    with pytest.raises(PermissionError, match="calibration-only"):
        calibrate_msae_completion.rep_array(
            root, "job", "C2", "pos", firewall)


def test_freeze_rechecks_every_pilot_attested_input(tmp_path: Path,
                                                    monkeypatch: pytest.MonkeyPatch) -> None:
    upstream = tmp_path / "upstream.bin"
    upstream.write_bytes(b"before")
    inventory_path = tmp_path / "data/atlas_completion_v1/upstream_inventory.json"
    token_path = tmp_path / "data/atlas_completion_v1/token_control_manifest.json"
    atomic_write_json(inventory_path, {
        "files": {"upstream.bin": __import__("hashlib").sha256(b"before").hexdigest()}})
    atomic_write_json(token_path, {"tokenizer": {"files": []}})
    attestation = {str(upstream.resolve()): {
        "sha256": __import__("hashlib").sha256(b"before").hexdigest(),
        "size": len(b"before"),
    }}
    monkeypatch.setattr(freeze_msae_completion, "ROOT", tmp_path)
    freeze_msae_completion.verify_pilot_attestation_for_freeze(attestation, [])
    upstream.write_bytes(b"after")
    with pytest.raises(RuntimeError, match="changed before terminal"):
        freeze_msae_completion.verify_pilot_attestation_for_freeze(attestation, [])


def test_completion_freeze_record_bytes_are_attested_again_before_terminal(
        tmp_path: Path) -> None:
    record = tmp_path / "freeze_record.json"
    record.write_text('{"bundle_sha256":"same","created_utc":"before"}\n')
    digest = __import__("hashlib").sha256(record.read_bytes()).hexdigest()
    firewall = InputFirewall([tmp_path])
    attest_completion_freeze_record(firewall, {
        "_freeze_record_path": str(record), "_freeze_record_sha256": digest})
    record.write_text('{"bundle_sha256":"same","created_utc":"after"}\n')
    with pytest.raises(RuntimeError, match="changed before terminal"):
        msa_completion_common.verify_attestation_current(firewall.attestation)


@pytest.mark.parametrize(("numerical", "budget", "stop_code", "failed_gate"), [
    (False, True, "pilot_numerical_gate_failure", "pilot_numerical_gate"),
    (True, False, "pilot_resource_gate_failure", "pilot_resource_gate"),
    (False, False, "pilot_numerical_and_resource_gate_failure",
     "pilot_numerical_and_resource_gates"),
])
def test_failed_pilot_payload_is_a_nonpromotable_frozen_stop(
        numerical: bool, budget: bool, stop_code: str, failed_gate: str) -> None:
    result = {
        "numerical_pass": numerical,
        "budget_pass": budget,
        "exercised_bundle_sha256": "exercised",
        "projected": {"raw_refit_stage_wall_hours": 2.0},
        "input_attestation": {"/upstream": {"sha256": "input", "size": 1}},
        "resolved_config": {"seed": 1}, "resolved_arguments": {"device": "cuda:0"},
        "seed_provenance": {"base_seed": 1}, "device": "cuda:0",
        "started_utc": "2026-08-01T00:00:00+00:00", "environment": {},
        "resource_accounting": {},
        "parent_bundle_reverified_after_stage_sha256": "parent",
    }
    complete, payload = msa_completion_pilot.pilot_terminal_payload(
        result, result_sha256="pilot", stage_budget_pass={"raw": False})
    assert complete is False
    assert payload["schema_version"] == "atlas_completion_frozen_stop_v1"
    assert payload["stop_code"] == stop_code
    assert payload["failed_gate"] == failed_gate
    assert payload["requested_draw_ids"] == []
    assert payload["completed_draw_ids"] == []
    assert payload["retained_partial_sha256"] == {"pilot.json": "pilot"}
    assert payload["input_attestation"] == result["input_attestation"]
    assert payload["scientific_retry_allowed"] is False
    assert payload["decision_promotion_allowed"] is False
    assert payload["score_access_allowed"] is False


def test_passing_pilot_terminal_directly_attests_opened_inputs() -> None:
    result = {
        "numerical_pass": True,
        "budget_pass": True,
        "exercised_bundle_sha256": "exercised",
        "projected": {},
        "input_attestation": {"/upstream": {"sha256": "input", "size": 1}},
        "resolved_config": {"seed": 1}, "resolved_arguments": {"device": "cuda:0"},
        "seed_provenance": {"base_seed": 1}, "device": "cuda:0",
        "started_utc": "2026-08-01T00:00:00+00:00", "environment": {},
        "resource_accounting": {},
        "parent_bundle_reverified_after_stage_sha256": "parent",
    }
    complete, payload = msa_completion_pilot.pilot_terminal_payload(
        result, result_sha256="pilot", stage_budget_pass={"raw": True})
    assert complete is True
    assert payload["schema_version"] == "atlas_completion_pilot_complete_v1"
    assert payload["input_attestation"] == result["input_attestation"]
    assert payload["score_access_allowed"] is True


def test_unrecoverable_pilot_failure_writes_nonpromotable_terminal(tmp_path: Path) -> None:
    marker = write_failure_terminal(
        tmp_path / "pilot", stop_code="pilot_unrecoverable_failure",
        failed_gate="pilot_numerical_and_resource_validation",
        error=RuntimeError("synthetic pilot failure"),
        input_attestation={"/input": {"sha256": "abc", "size": 3}})
    assert marker.name == "FROZEN_EQUIVOCAL_STOP.json"
    payload = json.loads(marker.read_text())
    assert payload["stop_code"] == "pilot_unrecoverable_failure"
    assert payload["failed_gate"] == "pilot_numerical_and_resource_validation"
    assert payload["input_attestation"]["/input"]["sha256"] == "abc"
    assert payload["requested_draw_ids"] == []
    assert payload["completed_draw_ids"] == []
    assert payload["scientific_retry_allowed"] is False
    assert payload["decision_promotion_allowed"] is False
    assert payload["started_utc"]
    assert payload["ended_utc"]
    assert payload["resource_accounting"]["stage_wall_seconds"] > 0


def test_failure_terminal_derives_completed_ids_from_valid_registrations(
        tmp_path: Path) -> None:
    stage = tmp_path / "partial_stage"
    artifact = stage / "draws/0001.json"
    atomic_write_json(artifact, {"draw_id": 1, "finite": True})
    register_draw_artifact(
        stage, 1, artifact, status="complete", config_sha256="c",
        completion_bundle_sha256="f")
    marker = write_failure_terminal(
        stage, stop_code="synthetic_fatal", failed_gate="shard_publication",
        error=RuntimeError("after one draw"), requested_draw_ids=range(3))
    payload = json.loads(marker.read_text())
    assert payload["requested_draw_ids"] == [0, 1, 2]
    assert payload["completed_draw_ids"] == [1]
    assert set(payload["retained_partial_sha256"]) >= {
        "draws/0001.json", "completed_hashes/0001.json"
    }


@pytest.mark.parametrize(("selected", "marker_name"), [
    ("complete", "MEASUREMENT_COMPLETE.json"),
    ("stopped", "FROZEN_EQUIVOCAL_STOP.json"),
])
def test_selector_only_terminal_is_repaired_for_downstream_launch_gate(
        tmp_path: Path, selected: str, marker_name: str) -> None:
    stage = tmp_path / selected
    body = {"schema_version": "test_terminal", "terminal_state": (
        "measurement_complete" if selected == "complete" else "frozen_equivocal_stop")}
    atomic_write_json(stage / "TERMINAL_STATE.json", {
        "selected_state": selected, **body})
    assert terminal_state(stage) == selected
    assert json.loads((stage / marker_name).read_text()) == body


def test_not_launched_marker_binds_evidence_config_and_completion(tmp_path: Path) -> None:
    stop = tmp_path / "FROZEN_EQUIVOCAL_STOP.json"
    stop.write_text("{}\n")
    payload = not_launched_payload(
        stop, skipped_stages=["merge", "render"], config_sha256="config",
        completion_bundle_sha256="freeze")
    assert set(payload) == {
        "schema_version", "evidence_class", "upstream_stop",
        "upstream_stop_sha256", "skipped_stages", "config_sha256",
        "completion_bundle_sha256", "recorded_utc",
    }
    assert payload["evidence_class"] == "postscore_amended_architecture_evidence"
    assert payload["config_sha256"] == "config"
    assert payload["completion_bundle_sha256"] == "freeze"


def test_registered_g1_seed_uses_exact_hypothesis_id() -> None:
    component = "split:absolute_position"
    assert registered_g1_randomization_seed(20260731, component) == deterministic_seed(
        20260731, "randomization", "g1a_family_lexical_min_topology",
        component)
    assert registered_g1_randomization_seed(20260731, component) != deterministic_seed(
        20260731, "randomization", "g1a_lexical", component)


def test_specificity_bootstrap_map_is_shared_across_family_estimators() -> None:
    groups = ["g0", "g1", "g2", "g3"]
    first = frozen_specificity_group_samples(
        groups, draws=500, seed=20260731, job_id="g4",
        family="lexical_entity_substitution")
    # Branch and sentence/token estimator are intentionally absent from the
    # frozen seed contract, so every estimator reuses this exact map.
    second = frozen_specificity_group_samples(
        list(reversed(groups)), draws=500, seed=20260731, job_id="g4",
        family="lexical_entity_substitution")
    assert first == second
    assert first != frozen_specificity_group_samples(
        groups, draws=500, seed=20260731, job_id="g4",
        family="punctuation_format")


def test_specificity_sentence_family_allows_24_of_32_valid_across_four_groups() -> None:
    config = {"draws": 500, "seed": 20260731, "specificity_margin": 0.05,
              "boundary_tolerance": 0.01}

    def rows(invalid: set[int]) -> list[dict[str, Any]]:
        return [{
            "transform_id": f"t{index}", "family": "position_shift",
            "template_group": f"g{index % 4}",
            "sentence": {
                "valid": index not in invalid,
                "specificity": {"pos": 0.20, "content": -0.20},
                "actual_normalized": {"pos": 0.30, "content": 0.10},
            },
        } for index in range(32)]

    valid_24 = group_summary(rows(set(range(8))), "position_shift", "pos", config, "g4")
    assert valid_24["n_rows"] == 24 and len(valid_24["group_means"]) == 4
    assert valid_24["valid"] is True
    assert group_summary(rows(set(range(9))), "position_shift", "pos", config, "g4")["valid"] is False
    missing_group = {index for index in range(32) if index % 4 == 3}
    missing = group_summary(rows(missing_group), "position_shift", "pos", config, "g4")
    assert missing["n_rows"] == 24 and len(missing["group_means"]) == 3
    assert missing["valid"] is False


def test_specificity_group_boundary_disables_count_gate() -> None:
    config = {"draws": 500, "seed": 20260731, "specificity_margin": 0.05,
              "boundary_tolerance": 0.01}
    rows = []
    for index in range(32):
        group = f"g{index % 4}"
        specificity = 0.005 if group == "g0" else 0.20
        rows.append({
            "transform_id": f"t{index}", "family": "position_shift",
            "template_group": group,
            "sentence": {"valid": True,
                         "specificity": {"pos": specificity, "content": -0.20},
                         "actual_normalized": {"pos": 0.30, "content": 0.10}},
        })
    summary = group_summary(rows, "position_shift", "pos", config, "g4")
    diagnostic = summary["group_boundary_diagnostics"][
        "specificity_positive"]["g0"]
    assert diagnostic["boundary_proximity"]
    assert diagnostic["mc_endpoint_range_status"] == "not_applicable"
    assert not summary["passes"]


def test_fixed_calibration_candidate_boundaries_are_explicit() -> None:
    config = {"boundary_tolerance": 0.01, "sentinel_max_degradation": 0.10,
              "sentinels": ["upos"]}
    recovery = {family: 0.655 for family in calibrate_msae_completion.PRIMARY}
    diagnostics = candidate_selection_boundaries(
        recovery, {"upos": {"degradation": 0.095}}, config)
    rows = [*diagnostics["tier1_family_assigned_recovery"].values(),
            *diagnostics["tier2_sentinel_degradation"].values()]
    assert all(row["boundary_proximity"] for row in rows)
    assert all(row["mc_endpoint_range_status"] == "not_applicable" for row in rows)


def test_strict_completion_json_and_recursive_finiteness_reject_nan(
        tmp_path: Path) -> None:
    path = tmp_path / "bad.json"
    path.write_text('{"value": NaN}')
    with pytest.raises(ValueError, match="non-standard JSON"):
        verify_msae_completion.strict_json(path)
    with pytest.raises(ValueError, match="non-finite"):
        verify_msae_completion.require_recursive_finite({"value": float("inf")})


def test_matched_random_seeds_use_registered_sentence_and_token_ids() -> None:
    transform = "lexical_entity_substitution:fixture"
    assert registered_matched_random_seed(20260731, transform) == deterministic_seed(
        20260731, "matched_random", transform, 0)
    assert registered_matched_random_seed(20260731, transform, 7) == deterministic_seed(
        20260731, "matched_random_token", transform, 7)


def test_weighted_scaler_equals_literal_replication() -> None:
    x = np.asarray([[1.0, 2.0], [3.0, -1.0], [8.0, 4.0]])
    weights = np.asarray([2, 0, 3])
    replicated = np.repeat(x, weights, axis=0)
    mean, scale = weighted_mean_scale(x, weights)
    assert np.allclose(mean, replicated.mean(0), atol=1e-7)
    assert np.allclose(scale, replicated.std(0), atol=1e-7)


def test_zero_weight_rows_match_replication_when_every_class_remains() -> None:
    y = np.asarray(["a", "a", "b", "b"])
    pred = np.asarray(["a", "b", "a", "b"])
    weights = np.asarray([2, 0, 1, 3])
    assert macro_f1(y, pred, weights) == pytest.approx(
        macro_f1(np.repeat(y, weights), np.repeat(pred, weights)))
    assert chance_score(y, y, weights, weights) == pytest.approx(
        chance_score(np.repeat(y, weights), np.repeat(y, weights)))


def test_zero_weight_frozen_class_is_invalid_for_metrics_and_ridge() -> None:
    y = np.asarray(["a", "a", "b"])
    pred = np.asarray(["a", "a", "a"])
    weights = np.asarray([1, 1, 0])
    with pytest.raises(FrozenClassOmissionError, match="frozen truth class"):
        macro_f1(y, pred, weights)
    with pytest.raises(FrozenClassOmissionError, match="omit a frozen class"):
        chance_score(y, y, weights, weights)
    if __import__("torch").cuda.is_available():
        with pytest.raises(ValueError, match="every frozen class"):
            fit_weighted_ridge_torch(np.arange(6, dtype=np.float32).reshape(3, 2),
                                     y, weights, 1.0, "cuda:0")


def test_leave_one_metric_primitives_reject_frozen_truth_class_loss() -> None:
    truth = np.asarray(["rare", "common", "common", "common"])
    prediction = truth.copy()
    groups = np.asarray(["rare_group", "g1", "g2", "g3"])
    point, leaves = grouped_f1_point_leave(truth, prediction, groups)
    assert point == pytest.approx(1.0)
    assert np.isnan(leaves["rare_group"])
    chance_point, chance_leaves = grouped_chance_point_leave(
        truth, truth, groups)
    assert np.isfinite(chance_point)
    assert np.isnan(chance_leaves["rare_group"])


def test_fixed_probe_eligibility_retains_one_invalid_draw(monkeypatch: pytest.MonkeyPatch) -> None:
    calls = 0

    def multiplicities(_sources: np.ndarray, _groups: np.ndarray,
                       _rng: np.random.Generator) -> dict[tuple[str, str], int]:
        nonlocal calls
        result = {("s", "rare"): 0 if calls == 0 else 1,
                  ("s", "common"): 1}
        calls += 1
        return result

    monkeypatch.setattr("calibrate_msae_completion.draw_group_multiplicities_rng",
                        multiplicities)
    y = np.asarray(["rare", "common"])
    result = fixed_probe_eligibility(
        task="fixture", y_fit=y, source_fit=np.asarray(["s", "s"]),
        y_cal=y, pred_cal=y, source_cal=np.asarray(["s", "s"]),
        group_cal=np.asarray(["rare", "common"]),
        config={"seed": 7, "draws": 500, "minimum_complete_draws": 450,
                "eligibility_floor": -10.0, "boundary_tolerance": 0.01},
        stage="fixture")
    assert result["finite_draws"] == 499
    assert result["nonfinite_draws"] == [0]


def test_weighted_cka_equals_literal_replication() -> None:
    rng = np.random.default_rng(4)
    x, y = rng.normal(size=(8, 4)), rng.normal(size=(8, 3))
    weights = np.asarray([1, 3, 0, 2, 1, 4, 1, 2])
    weighted = weighted_linear_cka(x, y, weights)
    replicated = weighted_linear_cka(np.repeat(x, weights, axis=0), np.repeat(y, weights, axis=0),
                                     np.ones(weights.sum()))
    assert weighted is not None and replicated is not None
    assert abs(weighted - replicated) < 1e-10
    assert weighted_linear_cka(np.ones((3, 2)), np.ones((3, 2)), np.ones(3)) is None


def test_cosine_control_matches_endpoint_and_is_orthogonal() -> None:
    rng = np.random.default_rng(8)
    source = rng.normal(size=32)
    target = source + 0.1 * rng.normal(size=32)
    delta, qa = cosine_matched_direction(source, target, seed=99)
    assert abs(cosine_distance(source, source + delta) - cosine_distance(source, target)) < 1e-6
    assert qa["absolute_cosine_actual_delta"] < 1e-10
    assert qa["absolute_cosine_source"] < 1e-10


def test_cosine_control_rejects_rank_deficient_source_delta_span() -> None:
    source = np.arange(1, 33, dtype=float)
    with pytest.raises(ValueError, match="rank-deficient source/actual-delta span"):
        cosine_matched_direction(source, 2.0 * source, seed=9)


def test_chance_and_macro_f1_honor_weights() -> None:
    y = np.asarray(["a", "b", "b"])
    pred = np.asarray(["a", "a", "b"])
    w = np.asarray([2, 1, 3])
    assert macro_f1(y, pred, w) == pytest.approx(macro_f1(np.repeat(y, w), np.repeat(pred, w)))
    assert chance_score(y, y, w, w) == pytest.approx(chance_score(np.repeat(y, w), np.repeat(y, w)))


def test_family_leakage_is_max_after_task_aggregation() -> None:
    recovery = {
        "assigned": {"a": 0.8, "b": 0.8},
        "leak1": {"a": 0.9, "b": 0.1},
        "leak2": {"a": 0.1, "b": 0.7},
    }
    row = family_summary(recovery, "assigned", ["leak1", "leak2"], ["a", "b"])
    assert row["leakage"] == pytest.approx(0.5)
    assert row["selectivity_margin"] == pytest.approx(0.3)
    # Mean of per-task maxima would be 0.8 and is explicitly not the estimator.


@pytest.mark.parametrize(("field", "value"), [
    ("assigned_recovery", 0.749), ("leakage", 0.551),
    ("selectivity_margin", 0.199),
])
def test_existing_checkpoint_k2_localization_row_emits_every_gate(
        field: str, value: float) -> None:
    row = {"assigned_recovery": 0.80, "leakage": 0.50,
           "selectivity_margin": 0.25}
    assert k2_localization_gate(row)["passes"]
    row[field] = value
    gates = k2_localization_gate(row)
    assert set(gates) == {
        "assigned_recovery_at_least_0p75", "leakage_at_most_0p55",
        "selectivity_at_least_0p20", "boundary_diagnostics", "passes"}
    assert not gates["passes"]


def test_k2_localization_boundary_proximity_disables_gate_and_reports_mc_policy() -> None:
    gates = k2_localization_gate({
        "assigned_recovery": 0.755, "leakage": 0.50,
        "selectivity_margin": 0.25})
    diagnostic = gates["boundary_diagnostics"]["assigned_recovery"]
    assert diagnostic["boundary_proximity"] is True
    assert diagnostic["mc_endpoint_range_status"] == "not_applicable"
    assert diagnostic["mc_not_applicable_reason"]
    assert gates["passes"] is False


def test_final_firewall_refuses_before_access(tmp_path: Path) -> None:
    public = tmp_path / "public"
    private = ROOT / "data/atlas_v1/private"
    public.mkdir()
    fw = InputFirewall([public])
    with pytest.raises(PermissionError, match="blind-final"):
        fw.resolve(private / "final.records.jsonl", role="final", must_exist=False)
    allowed = public / "final_step100.pt"
    allowed.write_bytes(b"checkpoint-not-blind-data")
    assert fw.resolve(allowed) == allowed.resolve()


@pytest.mark.skipif(__import__("torch").cuda.is_available() is False, reason="CUDA numerical smoke")
@pytest.mark.parametrize("class_count", [2, 3])
def test_gpu_weighted_ridge_matches_exact_sklearn(class_count: int) -> None:
    from sklearn.linear_model import RidgeClassifier

    rng = np.random.default_rng(2)
    x = rng.normal(size=(240, 12)).astype(np.float32)
    labels = np.asarray(["a", "b", "c"][:class_count])
    y = labels[np.argmax(x[:, :class_count] + 0.1 * rng.normal(size=(240, class_count)), axis=1)]
    weights = rng.integers(0, 4, size=len(x)).astype(float)
    ours = fit_weighted_ridge_torch(x, y, weights, 10.0, "cuda:0")
    reference = RidgeClassifier(alpha=10.0, solver="cholesky").fit(x, y, sample_weight=weights)
    replicated = RidgeClassifier(alpha=10.0, solver="cholesky").fit(
        np.repeat(x, weights.astype(int), axis=0), np.repeat(y, weights.astype(int), axis=0))
    ours_prediction = ours.predict(x)
    reference_prediction = reference.predict(x)
    agreement = np.mean(ours_prediction == reference_prediction)
    assert agreement >= 0.999
    assert abs(macro_f1(y, ours_prediction) - macro_f1(y, reference_prediction)) <= 0.001
    assert np.linalg.norm(ours.coef - reference.coef_) / np.linalg.norm(reference.coef_) <= 0.001
    ours_decision = (x @ ours.coef.T + ours.intercept).reshape(reference.decision_function(x).shape)
    assert np.linalg.norm(ours_decision - reference.decision_function(x)) / np.linalg.norm(reference.decision_function(x)) <= 0.001
    assert np.linalg.norm(replicated.coef_ - reference.coef_) / np.linalg.norm(reference.coef_) <= 0.001


@pytest.mark.parametrize(
    ("predicates", "expected"),
    [
        ({"any_primary_invalidity": True, "simple_equivalence": True}, "equivocal_no_decision"),
        ({"simple_equivalence": True}, "existing_simple"),
        ({"existing_checkpoint_all_gates": True}, "existing_checkpoint"),
        ({"learned_model_all_gates": True}, "learned_model_warranted"),
        ({"supported_negative_all_gates": True}, "supported_negative_atlas"),
        ({}, "equivocal_no_decision"),
    ],
)
def test_decision_table(predicates: dict[str, bool], expected: str) -> None:
    assert decide(predicates) == expected


def test_renderer_emits_supported_negative_even_when_invalidity_has_precedence() -> None:
    results = {
        "preflight": {"joint_decision_forced_equivocal": True},
        "baseline": {"selection_failed": False},
        "raw": {"G1a_postscore_amended": {
            "outcome": "equivocal",
            "parent_gate_evaluation": {"inferentially_valid": False},
            "supported_negative_diagnostic": {"supported_negative_all_gates": True},
        }},
        "G2a_postscore_amended": {
            "outcome": "equivocal", "simple_branch_available": False,
            "simple_evidence_invalid": False,
            "existing_checkpoint_branch_evaluation": {"passes": False},
            "learned_model_branch_evaluation": {"passes": False},
        },
    }
    predicates = decision_predicates(results)
    assert predicates["supported_negative_all_gates"] is True
    assert predicates["any_primary_invalidity"] is True
    assert decide(predicates) == "equivocal_no_decision"


def test_missing_learned_comparator_does_not_block_valid_simple_branch() -> None:
    results = {
        "preflight": {"joint_decision_forced_equivocal": False},
        "baseline": {"selection_failed": False},
        "raw": {"G1a_postscore_amended": {
            "parent_gate_evaluation": {"inferentially_valid": True},
            "supported_negative_diagnostic": {"supported_negative_all_gates": False},
        }},
        "G2a_postscore_amended": {
            "simple_branch_available": True,
            "simple_evidence_invalid": False,
            "existing_checkpoint_branch_evaluation": {
                "passes": False,
                "missing_evidence": ["matched_K1_checkpoint_and_FVU_comparator"],
            },
            "learned_model_branch_evaluation": {
                "passes": False,
                "missing_evidence": ["matched_K1_checkpoint_and_FVU_comparator"],
            },
        },
    }
    predicates = decision_predicates(results)
    assert not predicates["any_primary_invalidity"]
    assert predicates["simple_equivalence"]
    assert decide(predicates) == "existing_simple"


def test_invalid_g2_superiority_inference_has_global_precedence_not_simple_scope() -> None:
    results = {
        "preflight": {"joint_decision_forced_equivocal": False},
        "baseline": {"selection_failed": False},
        "raw": {"G1a_postscore_amended": {
            "parent_gate_evaluation": {"inferentially_valid": True},
            "source_reversal_failures": [],
            "supported_negative_diagnostic": {"supported_negative_all_gates": False},
        }},
        "G2a_postscore_amended": {
            "simple_branch_available": True, "simple_evidence_invalid": False,
            "learned_boundary_failures": [],
            "g2_randomization": {"g4": {"valid": False, "p": None}},
            "existing_checkpoint_branch_evaluation": {"passes": False},
            "learned_model_branch_evaluation": {"passes": False},
        },
    }
    predicates = decision_predicates(results)
    assert predicates["simple_equivalence"] is True
    assert predicates["g2_superiority_inference_invalid"] is True
    assert predicates["any_primary_invalidity"] is True
    assert decide(predicates) == "equivocal_no_decision"


def test_source_reversal_is_named_conflicting_axis() -> None:
    results = {
        "preflight": {"joint_decision_forced_equivocal": False},
        "baseline": {"selection_failed": False},
        "raw": {"G1a_postscore_amended": {
            "parent_gate_evaluation": {"inferentially_valid": True},
            "source_reversal_failures": ["family:absolute_position"],
            "supported_negative_diagnostic": {"supported_negative_all_gates": False},
        }},
        "G2a_postscore_amended": {
            "simple_branch_available": True, "simple_evidence_invalid": False,
            "existing_checkpoint_branch_evaluation": {"passes": False},
            "learned_model_branch_evaluation": {"passes": False},
        },
    }
    predicates = decision_predicates(results)
    assert predicates["conflicting_primary_axes"] is True
    assert predicates["any_primary_invalidity"] is True


@pytest.mark.parametrize("missing_gate", [
    "global_bounds_present", "baseline_selection_valid", "roundtrip_point_valid",
    "counterfactual_all_valid", "identity_collateral_all_valid",
    "stability_point_gate_valid", "no_simple_boundary_failures",
])
def test_every_missing_mandatory_simple_gate_is_invalid(missing_gate: str) -> None:
    gates = {
        "global_bounds_present": True, "baseline_selection_valid": True,
        "roundtrip_point_valid": True, "counterfactual_all_valid": True,
        "identity_collateral_all_valid": True, "stability_point_gate_valid": True,
        "no_simple_boundary_failures": True,
    }
    assert not mandatory_evidence_invalid(gates)
    gates[missing_gate] = False
    assert mandatory_evidence_invalid(gates)


def test_valid_g1_nonselection_can_reach_supported_negative_row() -> None:
    results = {
        "preflight": {"joint_decision_forced_equivocal": False},
        "baseline": {"selection_failed": False},
        "raw": {"G1a_postscore_amended": {
            "parent_gate_evaluation": {"inferentially_valid": True,
                                        "no_topology_selected": True},
            "supported_negative_diagnostic": {"supported_negative_all_gates": True},
        }},
        "G2a_postscore_amended": {
            "simple_branch_available": False, "simple_evidence_invalid": False,
            "existing_checkpoint_branch_evaluation": {"passes": False},
            "learned_model_branch_evaluation": {"passes": False},
        },
    }
    predicates = decision_predicates(results)
    assert not predicates["any_primary_invalidity"]
    assert decide(predicates) == "supported_negative_atlas"


def test_unit_multiplicity_and_row_weights() -> None:
    sources = np.asarray(["a", "a", "b"])
    groups = np.asarray(["x", "x", "y"])
    multiplicities = unit_group_multiplicities(sources, groups)
    assert np.array_equal(weights_from_multiplicities(sources, groups, multiplicities), np.ones(3))


def test_punctuation_invalidation_uses_independent_or_predicates() -> None:
    assert punctuation_branch_invalid({"lower_95_one_sided": 0.06, "positive_groups": 0}, 0.05)
    assert punctuation_branch_invalid({"lower_95_one_sided": -0.2, "positive_groups": 3}, 0.05)
    assert not punctuation_branch_invalid({"lower_95_one_sided": 0.049, "positive_groups": 2}, 0.05)


def test_specificity_invariants_reject_nan_in_any_branch_or_qa() -> None:
    good = {"raw": 0.1, "pos": 0.2, "content": 0.3}
    assert specificity_invariants_finite(good, good, good, {"distance_error": 0.0})
    assert not specificity_invariants_finite(good, {**good, "content": float("nan")}, good,
                                                     {"distance_error": 0.0})
    assert not specificity_invariants_finite(good, good, good, {"distance_error": float("nan")})


def test_rank_deficient_specificity_row_round_trips_without_nan(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="rank-deficient"):
        cosine_matched_direction(np.asarray([1.0, 0.0]),
                                 np.asarray([2.0, 0.0]), seed=3)
    row = {"sentence": {"valid": False, "reason": "ValueError:rank-deficient"},
           "random": None, "computed_random_raw_distance_error": None,
           "random_direction_sha256": None}
    path = tmp_path / "invalid_specificity.json"
    atomic_write_json(path, row)
    assert json.loads(path.read_text()) == row


def test_simple_roundtrip_rejects_nonorthonormal_projector() -> None:
    rng = np.random.default_rng(91)
    x = rng.normal(size=(40, 8)).astype(np.float32)
    good, _ = np.linalg.qr(rng.normal(size=(8, 2)))
    bases = {"broad_position": good.astype(np.float32),
             "split_position_joint": good.astype(np.float32),
             "pca16": good.astype(np.float32)}
    assert all(row["passes"] for row in simple_roundtrip_checks(x, bases, 1e-5).values())
    bases["pca16"] = (2 * good).astype(np.float32)
    assert not simple_roundtrip_checks(x, bases, 1e-5)["pca16_complement"]["passes"]


def test_candidate_ties_use_lower_fitted_rank_then_lexicographic_id() -> None:
    rows = {
        "z": {"selection_pass": True, "tier1_macro_selectivity": 0.70, "fitted_rank_total": 768},
        "b": {"selection_pass": True, "tier1_macro_selectivity": 0.695, "fitted_rank_total": 760},
        "a": {"selection_pass": True, "tier1_macro_selectivity": 0.691, "fitted_rank_total": 760},
        "failed": {"selection_pass": False, "tier1_macro_selectivity": 1.0, "fitted_rank_total": 1},
    }
    selected, failed, trace = select_candidate(rows)
    assert not failed and selected == "a"
    assert trace["score_tied"] == ["a", "b", "z"]
    assert trace["rank_tied"] == ["a", "b"]


def test_numerical_rank_uses_fitted_float32_tolerance() -> None:
    rng = np.random.default_rng(11)
    x = rng.normal(size=(1024, 32)).astype(np.float32)
    basis, _ = np.linalg.qr(rng.normal(size=(32, 4)))
    basis = basis.astype(np.float32)
    assert numerical_rank(x @ basis)[0] == 4
    assert numerical_rank(x - (x @ basis) @ basis.T)[0] == 28
    complement_operator = np.eye(32, dtype=np.float32) - basis @ basis.T
    assert numerical_rank(basis)[0] == 4
    assert numerical_rank(complement_operator)[0] == 28


def test_atomic_create_once_cannot_clobber(tmp_path: Path) -> None:
    path = tmp_path / "value.json"
    atomic_write_json(path, {"value": 1})
    with pytest.raises(FileExistsError):
        atomic_write_json(path, {"value": 2})
    assert json.loads(path.read_text()) == {"value": 1}


def test_registered_draw_resume_detects_tampering_and_failed_is_terminal(tmp_path: Path) -> None:
    stage = tmp_path / "stage"
    result = stage / "draws/0000.json"
    payload = {"draw_id": 0, "config_sha256": "config", "completion_bundle_sha256": "freeze"}
    atomic_write_json(result, payload)
    register_draw_artifact(stage, 0, result, status="complete", config_sha256="config",
                           completion_bundle_sha256="freeze")
    assert prepare_draw_resume(stage, 0, config_sha256="config", completion_bundle_sha256="freeze") == "complete"
    result.write_text('{"draw_id":0}\n')
    with pytest.raises(RuntimeError, match="registered draw artifact mismatch"):
        prepare_draw_resume(stage, 0, config_sha256="config", completion_bundle_sha256="freeze")

    failed = stage / "errors/0001.json"
    atomic_write_json(failed, {"draw_id": 1, "config_sha256": "config", "completion_bundle_sha256": "freeze"})
    register_draw_artifact(stage, 1, failed, status="failed", config_sha256="config",
                           completion_bundle_sha256="freeze")
    assert prepare_draw_resume(stage, 1, config_sha256="config", completion_bundle_sha256="freeze") == "failed"


def test_orphan_temporary_is_quarantined(tmp_path: Path) -> None:
    stage = tmp_path / "stage"
    temporary = stage / "draws/.0002.json.tmp.7.orphan"
    temporary.parent.mkdir(parents=True)
    temporary.write_text("partial")
    assert prepare_draw_resume(stage, 2, config_sha256="config", completion_bundle_sha256="freeze") == "absent"
    assert not temporary.exists()
    assert list((stage / "invalid_partial/orphan_temporaries").iterdir())


def test_stale_claim_requires_same_host_dead_pid(tmp_path: Path) -> None:
    stage = tmp_path / "stage"
    claim = stage / "claims/0003"
    claim.mkdir(parents=True)
    atomic_write_json(claim / "claim.json", {"draw_id": 3, "host": socket.gethostname(),
                                              "pid": 2**30, "config_sha256": "config"})
    replacement = claim_draw(stage, 3, "config")
    assert replacement == claim
    assert list((stage / "invalid_partial/stale_claims").iterdir())

    live = stage / "claims/0004"
    live.mkdir()
    atomic_write_json(live / "claim.json", {"draw_id": 4, "host": socket.gethostname(),
                                             "pid": os.getpid(), "config_sha256": "config"})
    with pytest.raises(LiveDrawClaimError, match="live PID"):
        claim_draw(stage, 4, "config")
    assert terminal_state(stage) is None


def test_failure_terminal_waits_for_leaf_publisher_and_blocks_late_output(
        tmp_path: Path) -> None:
    stage = tmp_path / "concurrent_stop"
    claim = claim_draw(stage, 1, "config")
    publisher_entered = threading.Event()

    def publisher() -> None:
        with stage_publication_lock(stage):
            publisher_entered.set()
            __import__("time").sleep(0.05)
            atomic_write_json(stage / "draws/0000.json", {"draw_id": 0})

    thread = threading.Thread(target=publisher)
    thread.start()
    assert publisher_entered.wait(timeout=2)
    marker = write_failure_terminal(
        stage, stop_code="fatal", failed_gate="test",
        error=RuntimeError("fatal"), requested_draw_ids=[0])
    thread.join(timeout=2)
    payload = json.loads(marker.read_text())
    assert "draws/0000.json" in payload["retained_partial_sha256"]
    assert not any(path.startswith("claims/") for path in payload["retained_partial_sha256"])
    release_claim(claim)
    with stage_publication_lock(stage):
        if terminal_state(stage) is None:
            atomic_write_json(stage / "draws/late.json", {"late": True})
    assert not (stage / "draws/late.json").exists()


def test_draw_shards_are_order_invariant() -> None:
    sources = np.asarray(["a", "a", "b", "b"])
    groups = np.asarray(["1", "2", "x", "y"])
    whole = {draw: draw_group_multiplicities(sources, groups,
             seed=deterministic_seed(20260731, "C1", 3, draw)) for draw in range(10)}
    shards = {}
    for start, end in [(5, 10), (0, 5)]:
        for draw in range(start, end):
            shards[draw] = draw_group_multiplicities(sources, groups,
                seed=deterministic_seed(20260731, "C1", 3, draw))
    assert shards == whole


def test_recovery_allows_disjoint_discovery_and_evaluation_sources() -> None:
    class ConstantModel:
        def __init__(self, values: list[str]) -> None:
            self.values = np.asarray(values)

        def predict(self, _x: np.ndarray) -> np.ndarray:
            return self.values

    y_fit = np.asarray(["a", "a", "b", "b"])
    y_eval = np.asarray(["a", "b", "a", "b"])
    value, detail = score_recovery(
        model=ConstantModel(["a", "b", "a", "b"]),
        raw_model=ConstantModel(["a", "b", "a", "b"]),
        rep_x=np.zeros((4, 1)), raw_x=np.zeros((4, 1)),
        y_fit=y_fit, fit_sources=np.asarray(["EWT"] * 4), fit_weights=np.ones(4),
        y_eval=y_eval, eval_sources=np.asarray(["LinES"] * 4), eval_weights=np.ones(4),
    )
    assert value == pytest.approx(1.0)
    assert detail["by_source"]["LinES"]["recovery"] == pytest.approx(1.0)


def test_recovery_serializes_every_frozen_source_when_one_is_invalid() -> None:
    class ConstantModel:
        def predict(self, _x: np.ndarray) -> np.ndarray:
            return np.asarray(["a", "b", "a", "b"])

    value, detail = score_recovery(
        model=ConstantModel(), raw_model=ConstantModel(),
        rep_x=np.zeros((4, 1)), raw_x=np.zeros((4, 1)),
        y_fit=np.asarray(["a", "a", "b", "b"]),
        fit_sources=np.asarray(["fit"] * 4), fit_weights=np.ones(4),
        y_eval=np.asarray(["a", "b", "a", "b"]),
        eval_sources=np.asarray(["source_a", "source_a", "source_b", "source_b"]),
        eval_weights=np.asarray([1.0, 1.0, 0.0, 0.0]),
    )
    assert value is None
    assert set(detail["by_source"]) == {"source_a", "source_b"}
    assert detail["invalid_sources"] == ["source_b"]
    assert detail["by_source"]["source_b"]["invalid_reason"] == "zero_evaluation_weight"


def test_recovery_marks_missing_weighted_truth_class_nonfinite_not_fatal() -> None:
    class ConstantModel:
        def predict(self, _x: np.ndarray) -> np.ndarray:
            return np.asarray(["a", "b", "a", "b"])

    value, detail = score_recovery(
        model=ConstantModel(), raw_model=ConstantModel(),
        rep_x=np.zeros((4, 1)), raw_x=np.zeros((4, 1)),
        y_fit=np.asarray(["a", "a", "b", "b"]),
        fit_sources=np.asarray(["fit"] * 4), fit_weights=np.ones(4),
        y_eval=np.asarray(["a", "b", "a", "b"]),
        eval_sources=np.asarray(["source_a", "source_a", "source_b", "source_b"]),
        eval_weights=np.asarray([1.0, 0.0, 1.0, 1.0]),
    )
    assert value is None
    assert detail["invalid_sources"] == ["source_a"]
    assert set(detail["by_source"]) == {"source_a", "source_b"}
    assert detail["by_source"]["source_a"]["recovery"] is None
    assert detail["by_source"]["source_a"]["invalid_reason"].startswith(
        "metric_undefined:")


@pytest.mark.parametrize("malformed", ["eval_nan", "fit_nan", "fit_negative"])
def test_recovery_keeps_malformed_weights_fatal(malformed: str) -> None:
    class ConstantModel:
        def predict(self, _x: np.ndarray) -> np.ndarray:
            return np.asarray(["a", "b", "a", "b"])

    fit_weights = np.ones(4)
    eval_weights = np.ones(4)
    if malformed == "eval_nan":
        eval_weights[0] = np.nan
    elif malformed == "fit_nan":
        fit_weights[0] = np.nan
    else:
        fit_weights[:] = -1.0
    with pytest.raises(ValueError, match="weights.*invalid|weights must be finite|recovery weights"):
        score_recovery(
            model=ConstantModel(), raw_model=ConstantModel(),
            rep_x=np.zeros((4, 1)), raw_x=np.zeros((4, 1)),
            y_fit=np.asarray(["a", "a", "b", "b"]),
            fit_sources=np.asarray(["fit"] * 4), fit_weights=fit_weights,
            y_eval=np.asarray(["a", "b", "a", "b"]),
            eval_sources=np.asarray(["source"] * 4),
            eval_weights=eval_weights,
        )


def test_firewall_rejects_symlink_escape(tmp_path: Path) -> None:
    allowed = tmp_path / "allowed"
    outside = tmp_path / "outside"
    allowed.mkdir(); outside.mkdir()
    target = outside / "blob"
    target.write_text("secret")
    link = allowed / "link"
    link.symlink_to(target)
    firewall = InputFirewall([allowed])
    with pytest.raises(PermissionError, match="unregistered"):
        firewall.resolve(link)


def test_firewall_rejects_input_changed_after_first_attestation(tmp_path: Path) -> None:
    path = tmp_path / "input.json"
    path.write_text("one")
    firewall = InputFirewall([tmp_path])
    firewall.attest(path)
    path.write_text("two")
    with pytest.raises(RuntimeError, match="changed after first attestation"):
        firewall.attest(path)


def test_pilot_snapshot_detects_midrun_mutation(tmp_path: Path,
                                                monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(msa_completion_pilot, "ROOT", tmp_path)
    path = tmp_path / "candidate.py"
    path.write_text("before")
    first = msa_completion_pilot.snapshot_exercised_files(["candidate.py"])
    path.write_text("after")
    assert msa_completion_pilot.snapshot_exercised_files(["candidate.py"]) != first


def test_pilot_roles_are_derived_from_opened_paths() -> None:
    attestation = {
        "/run/raw_activations/discovery/L3.float16.npy": {},
        "/run/k2_transforms/g4/calibration/pos.float16.npy": {},
    }
    assert msa_completion_pilot.roles_from_attestation(attestation) == [
        "calibration", "discovery"]
    attestation["/run/raw_activations/C2/L3.float16.npy"] = {}
    assert "C2" in msa_completion_pilot.roles_from_attestation(attestation)


def test_pinned_hf_snapshot_requires_exact_blob_symlink_set(tmp_path: Path) -> None:
    repo = tmp_path / "models--test"
    blob_root = repo / "blobs"
    snapshot = repo / "snapshots" / "rev"
    blob_root.mkdir(parents=True)
    snapshot.mkdir(parents=True)
    blob = blob_root / "abc"
    blob.write_bytes(b"weights")
    entry = snapshot / "config.json"
    entry.symlink_to(Path("../../blobs/abc"))
    manifest = {"tokenizer": {"snapshot": str(snapshot), "files": [{
        "snapshot_path": str(entry), "target_path": str(blob),
        "sha256": __import__("hashlib").sha256(b"weights").hexdigest()}]}}
    firewall = InputFirewall()
    assert register_pinned_hf_snapshot(firewall, manifest) == snapshot.absolute()
    (snapshot / "unregistered.json").symlink_to(Path("../../blobs/abc"))
    with pytest.raises(RuntimeError, match="file-set mismatch"):
        register_pinned_hf_snapshot(InputFirewall(), manifest)


def test_terminal_markers_are_mutually_exclusive(tmp_path: Path) -> None:
    stage = tmp_path / "stage"
    write_terminal(stage, complete=True, payload={"schema_version": "test"})
    with pytest.raises(FileExistsError, match="terminal state"):
        write_terminal(stage, complete=False, payload={"schema_version": "test"})


def test_concurrent_complete_and_stop_publish_exactly_one_terminal(tmp_path: Path) -> None:
    stage = tmp_path / "terminal_race"
    barrier = threading.Barrier(2)

    def publish(complete: bool) -> str:
        barrier.wait()
        try:
            return write_terminal(stage, complete=complete,
                                  payload={"schema_version": "test", "requested": complete}).name
        except FileExistsError:
            return "lost"

    with ThreadPoolExecutor(max_workers=2) as pool:
        outcomes = list(pool.map(publish, [True, False]))
    markers = [path.name for path in [stage / "MEASUREMENT_COMPLETE.json",
                                      stage / "FROZEN_EQUIVOCAL_STOP.json"] if path.exists()]
    assert len(markers) == 1
    assert outcomes.count("lost") == 1
    assert (stage / "TERMINAL_STATE.json").is_file()
    assert terminal_state(stage) in {"complete", "stopped"}


def test_realized_small_cluster_design_is_inferentially_invalid() -> None:
    assert exact_cluster_sign_pvalue([0.1, -0.1, 0.2, -0.2], minimum_clusters=10) is None


def test_exact_sign_reference_has_nominal_null_calibration() -> None:
    rng = np.random.default_rng(20260731)
    rejected = 0
    fixtures = 500
    for _ in range(fixtures):
        values = rng.normal(size=8)
        pvalue = exact_joint_sign_pvalue(values, minimum_clusters=8)
        assert pvalue == exact_cluster_sign_pvalue(values, minimum_clusters=8)
        assert pvalue is not None
        rejected += pvalue <= 0.05
    rate = rejected / fixtures
    assert 0.02 <= rate <= 0.08


def test_specific_leakage_sign_estimator_matches_direct_source_enumeration() -> None:
    groups = [f"g{i}" for i in range(4)]

    def leaf(values: list[float]) -> dict[str, Any]:
        return {"valid": True, "point": float(np.mean(values)), "groups": len(values),
                "pseudovalues": dict(zip(groups, values, strict=True))}

    primitive = {
        "t1": {"a": {"s1": leaf([0.3, 0.1, 0.2, 0.2]),
                        "s2": leaf([0.2, 0.4, 0.3, 0.3])},
               "l": {"s1": leaf([0.0, 0.0, 0.0, 0.0]),
                        "s2": leaf([0.0, 0.0, 0.0, 0.0])}},
    }
    result = specific_leakage_sign_test(
        primitive, tasks=["t1"], assigned="a", leakage="l", draws=0, seed=0,
        minimum_stratum_clusters=4, minimum_hypothesis_clusters=8, exact=True)
    assert result["valid"] and result["observed_pseudo_contrast"] == pytest.approx(0.25)
    values = {("s1", group): primitive["t1"]["a"]["s1"]["pseudovalues"][group]
              for group in groups}
    values.update({("s2", group): primitive["t1"]["a"]["s2"]["pseudovalues"][group]
                   for group in groups})
    keys = sorted(values)
    exceed = 0
    for mask in range(1 << len(keys)):
        by_source = []
        for source in ["s1", "s2"]:
            signed = [values[(source, group)] * (1 if mask & (1 << keys.index((source, group))) else -1)
                      for group in groups]
            by_source.append(float(np.mean(signed)))
        exceed += float(np.mean(by_source)) >= 0.25
    assert result["p"] == pytest.approx(exceed / (1 << len(keys)))
    assert result["p"] <= 0.05  # planted positive fixture


def test_active_topology_and_leakage_winners_can_change_without_reordering() -> None:
    def primitive(assigned: float, left: tuple[float, float],
                  right: tuple[float, float]) -> dict[str, Any]:
        return {
            "a": {"t1": {"s1": assigned, "s2": assigned},
                  "t2": {"s1": assigned, "s2": assigned}},
            "l1": {"t1": {"s1": left[0], "s2": left[0]},
                   "t2": {"s1": left[1], "s2": left[1]}},
            "l2": {"t1": {"s1": right[0], "s2": right[0]},
                   "t2": {"s1": right[1], "s2": right[1]}},
        }

    both = {"f": {"tasks": ["t1", "t2"], "assigned": "a",
                   "leakage": ["l1", "l2"]}}
    only_left = {"f": {**both["f"], "leakage": ["l1"]}}
    only_right = {"f": {**both["f"], "leakage": ["l2"]}}

    point_split = primitive(0.70, (0.30, 0.94), (0.61, 0.20))
    point_broad = primitive(0.70, (0.40, 0.76), (0.55, 0.30))
    draw_split = primitive(0.70, (0.30, 0.80), (0.50, 0.40))
    draw_broad = primitive(0.70, (0.45, 0.77), (0.40, 0.50))
    point_topologies = {"split": aggregate_selectivity(point_split, both),
                        "broad": aggregate_selectivity(point_broad, both)}
    draw_topologies = {"split": aggregate_selectivity(draw_split, both),
                       "broad": aggregate_selectivity(draw_broad, both)}
    assert min(point_topologies, key=point_topologies.get) == "split"
    assert min(draw_topologies, key=draw_topologies.get) == "broad"

    # Winner identity is proved through the production aggregator: removing
    # the winner changes selectivity; removing the loser does not.
    learned = primitive(0.70, (0.25, 0.54), (0.55, 0.22))  # l1 wins
    simple = primitive(0.70, (0.62, 0.10), (0.20, 0.58))   # l2 wins
    assert aggregate_selectivity(learned, both) == aggregate_selectivity(learned, only_left)
    assert aggregate_selectivity(learned, both) < aggregate_selectivity(learned, only_right)
    assert aggregate_selectivity(simple, both) == aggregate_selectivity(simple, only_right)
    assert aggregate_selectivity(simple, both) < aggregate_selectivity(simple, only_left)


@pytest.mark.parametrize(("value", "expected"),
                         [(0.05, True), (0.059, True), (0.061, False)])
def test_boundary_proximity_exact_inside_and_outside(value: float, expected: bool) -> None:
    result = threshold_boundary_diagnostic(value, 0.05, tolerance=0.01,
                                           mc_endpoint_range=0.0)
    assert result["boundary_proximity"] is expected


def test_parent_g1_family_ci_uses_two_sided_lower_endpoint() -> None:
    # Four values below zero put q.025 below zero while q.05 is positive.
    values = [-0.02] * 20 + [0.01] * 480
    summary = percentile(values)
    assert summary["ci95"][0] < 0
    assert summary["lower95"] > 0


def test_boundary_mc_range_flags_only_above_tolerance_at_boundary() -> None:
    stable = threshold_boundary_diagnostic(0.05, 0.05, tolerance=0.01,
                                           mc_endpoint_range=0.01)
    unstable = threshold_boundary_diagnostic(0.05, 0.05, tolerance=0.01,
                                             mc_endpoint_range=0.01001)
    assert not stable["mc_underpowered_at_boundary"]
    assert unstable["mc_underpowered_at_boundary"]
    draws = [0.05] * 500
    specificity = specificity_boundary_diagnostic(draws, 0.05, 0.05, 0.01)
    assert specificity["boundary_proximity"] and specificity["mc_100_block_endpoint_range"] == 0.0


def test_simultaneous_mc_range_detects_other_coordinate_max_radius_shift() -> None:
    repeated = np.linspace(-0.1, 0.1, 100)
    draws = np.zeros((500, 6))
    draws[:, 0] = np.tile(repeated, 5)
    draws[400:, 1] = 0.5
    assert block_mc_uncertainty(draws[:, 0].tolist()) == pytest.approx(0.0)
    diagnostic = simultaneous_block_mc_diagnostics([0.0] * 6, draws.tolist())
    assert diagnostic is not None
    assert diagnostic["upper_endpoint_range"][0] > 0.3


def test_mc_diagnostics_preserve_registered_blocks_with_499_finite_draws() -> None:
    ids = [draw for draw in range(500) if draw != 137]
    values = [float(draw % 17) / 100 for draw in ids]
    assert block_mc_uncertainty(values, ids) is not None
    draws = [[value, -value] for value in values]
    diagnostic = simultaneous_block_mc_diagnostics([0.0, 0.0], draws, ids)
    assert diagnostic is not None
    assert len(diagnostic["upper_endpoint_range"]) == 2


def test_null_imposition_recomputes_different_leakage_winners() -> None:
    groups = [f"g{i}" for i in range(12)]

    def leaf(point: float, phase: float) -> dict[str, Any]:
        residual = np.asarray([(-1.0) ** i * (0.01 + phase * (i % 3)) for i in range(12)])
        residual -= residual.mean()
        return {"point": point,
                "pseudovalues": {group: float(point + value) for group, value in zip(groups, residual)}}

    left = {
        "a": {"t1": {"s": leaf(0.72, 0.001)}, "t2": {"s": leaf(0.68, 0.002)}},
        "l1": {"t1": {"s": leaf(0.30, 0.003)}, "t2": {"s": leaf(0.60, 0.001)}},
        "l2": {"t1": {"s": leaf(0.61, 0.002)}, "t2": {"s": leaf(0.20, 0.003)}},
    }
    right = {
        "b": {"t1": {"s": leaf(0.60, 0.002)}, "t2": {"s": leaf(0.58, 0.001)}},
        "q1": {"t1": {"s": leaf(0.25, 0.001)}, "t2": {"s": leaf(0.54, 0.002)}},
        "q2": {"t1": {"s": leaf(0.55, 0.003)}, "t2": {"s": leaf(0.22, 0.001)}},
    }
    left_spec = {"f": {"tasks": ["t1", "t2"], "assigned": "a", "leakage": ["l1", "l2"]}}
    right_spec = {"f": {"tasks": ["t1", "t2"], "assigned": "b", "leakage": ["q1", "q2"]}}
    left_means = {rep: {task: {source: row["point"] for source, row in sources.items()}
                               for task, sources in tasks.items()} for rep, tasks in left.items()}
    right_means = {rep: {task: {source: row["point"] for source, row in sources.items()}
                                for task, sources in tasks.items()} for rep, tasks in right.items()}
    # l1 wins only after task aggregation; mean of within-task maxima is different.
    assert aggregate_selectivity(left_means, left_spec) == pytest.approx(0.25)
    assert np.mean([left_means["l1"][task]["s"] for task in ["t1", "t2"]]) > np.mean(
        [left_means["l2"][task]["s"] for task in ["t1", "t2"]])
    assert np.mean([right_means["q1"][task]["s"] for task in ["t1", "t2"]]) > np.mean(
        [right_means["q2"][task]["s"] for task in ["t1", "t2"]])
    result = null_imposed_selectivity_test(
        left, right, left_spec, right_spec, draws=999, seed=20260731,
        minimum_stratum_clusters=10, minimum_hypothesis_clusters=10)
    assert result["valid"]
    assert abs(result["null_reconstruction"]) <= 1e-10
    assert 0 <= result["p"] <= 1


def test_nonlinear_null_test_matches_literal_enumeration_with_winner_changes() -> None:
    groups = [f"g{i}" for i in range(4)]

    def leaf(point: float, pattern: list[float]) -> dict[str, Any]:
        residual = np.asarray(pattern, dtype=float)
        residual -= residual.mean()
        return {"point": point,
                "pseudovalues": dict(zip(
                    groups, (point + residual).tolist(), strict=True))}

    left = {
        "a": {"t1": {"s": leaf(0.72, [.12, -.12, .08, -.08])},
              "t2": {"s": leaf(0.68, [-.10, .10, -.06, .06])}},
        "l1": {"t1": {"s": leaf(0.30, [.22, -.22, .18, -.18])},
               "t2": {"s": leaf(0.60, [-.18, .18, -.22, .22])}},
        "l2": {"t1": {"s": leaf(0.61, [-.20, .20, -.16, .16])},
               "t2": {"s": leaf(0.20, [.16, -.16, .20, -.20])}},
    }
    right = {
        "b": {"t1": {"s": leaf(0.61, [.09, -.09, .05, -.05])},
              "t2": {"s": leaf(0.59, [-.07, .07, -.11, .11])}},
        "q1": {"t1": {"s": leaf(0.25, [-.17, .17, -.13, .13])},
               "t2": {"s": leaf(0.50, [.13, -.13, .17, -.17])}},
        "q2": {"t1": {"s": leaf(0.56, [.19, -.19, .15, -.15])},
               "t2": {"s": leaf(0.24, [-.15, .15, -.19, .19])}},
    }
    left_spec = {"f": {"tasks": ["t1", "t2"], "assigned": "a",
                        "leakage": ["l1", "l2"]}}
    right_spec = {"f": {"tasks": ["t1", "t2"], "assigned": "b",
                         "leakage": ["q1", "q2"]}}
    result = null_imposed_selectivity_test(
        left, right, left_spec, right_spec, draws=0, seed=0,
        minimum_stratum_clusters=4, minimum_hypothesis_clusters=4,
        exact=True)
    assert result["valid"]

    def points(primitives: dict[str, Any], signs: list[int]) -> dict[str, Any]:
        output: dict[str, Any] = {}
        for rep, tasks in primitives.items():
            output[rep] = {}
            for task, sources in tasks.items():
                output[rep][task] = {}
                for source, value in sources.items():
                    pseudo = np.asarray(list(value["pseudovalues"].values()))
                    residual = pseudo - pseudo.mean()
                    output[rep][task][source] = float(
                        value["point"] + np.mean(np.asarray(signs) * residual))
        return output

    def select(values: dict[str, Any], assigned: str,
               leakage: list[str], shift: float = 0.0) -> tuple[float, str]:
        means = {rep: np.mean([values[rep][task]["s"]
                              for task in ["t1", "t2"]])
                 for rep in [assigned, *leakage]}
        winner = max(leakage, key=lambda rep: means[rep])
        return float(means[assigned] - shift - means[winner]), winner

    left_point, left_winner = select(points(left, [1] * 4), "a", ["l1", "l2"])
    right_point, right_winner = select(points(right, [1] * 4), "b", ["q1", "q2"])
    observed = left_point - right_point
    exceed = 0
    realized_winners = set()
    for signs in itertools.product((-1, 1), repeat=4):
        left_value, lw = select(points(left, list(signs)), "a", ["l1", "l2"], observed)
        right_value, rw = select(points(right, list(signs)), "b", ["q1", "q2"])
        realized_winners.add((lw, rw))
        exceed += left_value - right_value >= observed
    assert left_winner == "l1" and right_winner == "q2"
    assert len(realized_winners) > 1
    assert result["observed"] == pytest.approx(observed)
    assert result["p"] == pytest.approx(exceed / 16)


def test_null_imposed_estimator_rejects_realized_four_cluster_stratum() -> None:
    leaf = {"point": 0.2, "pseudovalues": {f"g{i}": 0.2 for i in range(4)}}
    primitive = {"a": {"t": {"s": leaf}}, "l": {"t": {"s": leaf}}}
    spec = {"f": {"tasks": ["t"], "assigned": "a", "leakage": ["l"]}}
    result = null_imposed_selectivity_test(
        primitive, primitive, spec, spec, draws=99, seed=1,
        minimum_stratum_clusters=10, minimum_hypothesis_clusters=20)
    assert not result["valid"] and result["p"] is None


def test_null_imposed_estimator_rejects_full_nonlinear_reconstruction_failure() -> None:
    groups = {f"g{i}": 0.209 for i in range(12)}
    assigned = {"point": 0.2, "pseudovalues": groups}
    leakage = {"point": 0.1, "pseudovalues": {key: 0.091 for key in groups}}
    left = {"a": {"t": {"s": assigned}}, "l": {"t": {"s": leakage}}}
    right = {"b": {"t": {"s": leakage}}, "q": {"t": {"s": leakage}}}
    spec_left = {"f": {"tasks": ["t"], "assigned": "a", "leakage": ["l"]}}
    spec_right = {"f": {"tasks": ["t"], "assigned": "b", "leakage": ["q"]}}
    result = null_imposed_selectivity_test(
        left, right, spec_left, spec_right, draws=99, seed=1,
        minimum_stratum_clusters=10, minimum_hypothesis_clusters=10)
    assert not result["valid"]
    assert "fully_aggregated_reconstruction" in result["reason"]


def test_null_shift_keeps_shared_representation_comparator_role_fixed() -> None:
    group_ids = [f"g{i}" for i in range(12)]

    def leaf(point: float) -> dict[str, Any]:
        residual = np.asarray([0.01 * (-1) ** i for i in range(12)])
        return {"point": point,
                "pseudovalues": {group: float(point + value)
                                  for group, value in zip(group_ids, residual)}}

    # pos/content exchange assigned/comparator roles between families.  The
    # logical assigned shift must not alter either comparator copy.
    left = {"pos": {"tp": {"s": leaf(0.7)}, "tc": {"s": leaf(0.3)}},
            "content": {"tp": {"s": leaf(0.2)}, "tc": {"s": leaf(0.8)}}}
    right = {"pos": {"tp": {"s": leaf(0.6)}, "tc": {"s": leaf(0.4)}},
             "content": {"tp": {"s": leaf(0.3)}, "tc": {"s": leaf(0.7)}}}
    spec = {"position": {"tasks": ["tp"], "assigned": "pos", "leakage": ["content"]},
            "lexical": {"tasks": ["tc"], "assigned": "content", "leakage": ["pos"]}}
    result = null_imposed_selectivity_test(
        left, right, spec, spec, draws=199, seed=7,
        minimum_stratum_clusters=10, minimum_hypothesis_clusters=10)
    assert result["valid"]
    assert abs(result["null_reconstruction"]) <= 1e-10


def test_null_sign_map_includes_mixed_zero_residual_groups() -> None:
    values = np.asarray([0.0, 0.0] + [0.1, -0.1] * 5)
    groups = [f"g{i}" for i in range(len(values))]

    def leaf(point: float, residual: np.ndarray) -> dict[str, Any]:
        return {"point": point,
                "pseudovalues": {group: float(point + value)
                                  for group, value in zip(groups, residual)}}

    zeros = np.zeros_like(values)
    left = {"a": {"t": {"s": leaf(0.2, values)}}, "l": {"t": {"s": leaf(0.0, zeros)}}}
    right = {"b": {"t": {"s": leaf(0.0, zeros)}}, "q": {"t": {"s": leaf(0.0, zeros)}}}
    spec_left = {"f": {"tasks": ["t"], "assigned": "a", "leakage": ["l"]}}
    spec_right = {"f": {"tasks": ["t"], "assigned": "b", "leakage": ["q"]}}
    result = null_imposed_selectivity_test(
        left, right, spec_left, spec_right, draws=99, seed=3,
        minimum_stratum_clusters=10, minimum_hypothesis_clusters=10)
    assert result["valid"] and result["clusters"] == 12 and result["nonzero_clusters"] == 10


def test_nonlinear_null_imposed_type_i_calibration_over_500_fixtures() -> None:
    rng = np.random.default_rng(20260731)
    groups = [f"g{i}" for i in range(8)]
    zeros = np.zeros(8)
    rejected = 0

    def leaf(point: float, values: np.ndarray) -> dict[str, Any]:
        return {"point": float(point),
                "pseudovalues": {group: float(value)
                                  for group, value in zip(groups, values)}}

    left_spec = {"f": {"tasks": ["t"], "assigned": "a", "leakage": ["l"]}}
    right_spec = {"f": {"tasks": ["t"], "assigned": "b", "leakage": ["q"]}}
    for fixture in range(500):
        values = rng.normal(size=8)
        left = {"a": {"t": {"s": leaf(float(values.mean()), values)}},
                "l": {"t": {"s": leaf(0.0, zeros)}}}
        right = {"b": {"t": {"s": leaf(0.0, zeros)}},
                 "q": {"t": {"s": leaf(0.0, zeros)}}}
        result = null_imposed_selectivity_test(
            left, right, left_spec, right_spec, draws=255, seed=fixture,
            minimum_stratum_clusters=8, minimum_hypothesis_clusters=8)
        assert result["valid"]
        rejected += result["p"] <= 0.05
    assert 0.02 <= rejected / 500 <= 0.08


def test_intersection_union_requires_all_topologies_and_uses_worst_component() -> None:
    required = ["split:absolute", "split:structural", "broad:position"]
    components = {
        "split:absolute": {"valid": True, "p": 0.01},
        "split:structural": {"valid": True, "p": 0.08},
        "broad:position": {"valid": True, "p": 0.03},
    }
    result = intersection_union_pvalue(components, required)
    assert result == {"valid": True, "p": 0.08, "missing_components": [],
                      "invalid_components": [], "winning_component": "split:structural"}
    missing = intersection_union_pvalue({key: value for key, value in components.items()
                                         if key != "broad:position"}, required)
    assert not missing["valid"] and missing["p"] is None
    assert missing["missing_components"] == ["broad:position"]
    invalid_components = dict(components)
    invalid_components["split:absolute"] = {"valid": False, "p": 0.001}
    invalid = intersection_union_pvalue(invalid_components, required)
    assert not invalid["valid"] and invalid["invalid_components"] == ["split:absolute"]


def test_frozen_group_maps_exactly_reproduce_registered_multinomial_draws() -> None:
    groups = {"a": ["1", "2", "3"], "b": ["x", "y"]}
    maps = frozen_group_bootstrap_maps(groups, draws=7, seed=20260731)
    sources = np.asarray(["a"] * 3 + ["b"] * 2)
    group_rows = np.asarray(groups["a"] + groups["b"])
    for draw in range(7):
        expected = draw_group_multiplicities(
            sources, group_rows,
            seed=deterministic_seed(20260731, "C1", 3, draw))
        for source in sorted(groups):
            observed = {group: int(maps[source][draw, index])
                        for index, group in enumerate(groups[source])}
            assert observed == {group: expected.get((source, group), 0)
                                for group in groups[source]}


def test_negative_sensitivity_matches_direct_gaussian_reference() -> None:
    data_rng = np.random.default_rng(931)
    residuals = {
        "a": data_rng.normal(0.0, 0.20, size=(24, 6)),
        "b": data_rng.normal(0.0, 0.20, size=(18, 6)),
    }
    residuals = {source: values - values.mean(axis=0, keepdims=True)
                 for source, values in residuals.items()}
    groups = {source: [f"{source}{index:02d}" for index in range(len(values))]
              for source, values in residuals.items()}
    maps = frozen_group_bootstrap_maps(groups, draws=500, seed=20260731)
    simulations = 2000
    observed = negative_sensitivity_simulation(
        residuals, maps, simulations=simulations, seed=20260731, effect=0.20)
    assert observed["valid"] and observed["simulations_completed"] == simulations
    assert observed["point_failures"] == [0] * 6

    # Deliberately separate, literal reference implementation on planted
    # independent Gaussian cluster vectors.  This catches source weighting,
    # re-centering, seed, and simultaneous-max mistakes in the production helper.
    direct_success = np.zeros(6, dtype=int)
    for simulation_id in range(simulations):
        rng = np.random.Generator(np.random.PCG64(20260731 + simulation_id))
        point = np.full(6, 0.20)
        bootstrap = np.full((500, 6), 0.20)
        for source in sorted(residuals):
            values = residuals[source]
            sampled = values[rng.choice(len(values), size=len(values), replace=True)]
            sampled -= sampled.mean(axis=0, keepdims=True)
            point += sampled.mean(axis=0)
            bootstrap += maps[source] @ sampled / len(sampled)
        deviations = point - bootstrap
        radius = np.quantile(np.max(deviations, axis=1), 0.95)
        lower = point - radius
        direct_success += (point >= 0.20 - 1e-12) & (lower > 0.0)
    direct_power = direct_success / simulations
    assert np.max(np.abs(np.asarray(observed["power"]) - direct_power)) <= 0.03


@pytest.mark.parametrize(("minimum", "terminal"), [(2, "MEASUREMENT_COMPLETE.json"),
                                                    (3, "FROZEN_EQUIVOCAL_STOP.json")])
def test_draw_stage_finalizes_only_after_every_registered_id(tmp_path: Path, minimum: int, terminal: str) -> None:
    stage = tmp_path / f"stage_{minimum}"
    atomic_write_json(stage / "point.json", {"draw_id": "point", "config_sha256": "c",
                                              "completion_bundle_sha256": "f", "finite": True})
    for draw, status in enumerate(["complete", "complete", "failed"]):
        artifact = stage / ("draws" if status == "complete" else "errors") / f"{draw:04d}.json"
        atomic_write_json(artifact, {"draw_id": draw, "config_sha256": "c",
                                     "completion_bundle_sha256": "f", "finite": status == "complete"})
        register_draw_artifact(stage, draw, artifact, status=status, config_sha256="c",
                               completion_bundle_sha256="f")
        if draw < 2:
            assert maybe_finalize_draw_stage(stage, requested_draws=3, minimum_complete_draws=minimum,
                                             config_sha256="c",
                                             completion_bundle_sha256="f", schema_version="test") is None
    marker = maybe_finalize_draw_stage(stage, requested_draws=3, minimum_complete_draws=minimum,
                                       config_sha256="c",
                                       completion_bundle_sha256="f", schema_version="test")
    assert marker is not None and marker.name == terminal
    if minimum == 3:
        stop = json.loads(marker.read_text())
        assert stop["schema_version"] == "atlas_completion_frozen_stop_v1"
        assert stop["stop_code"] == "insufficient_scientifically_finite_draws"
        assert stop["failed_gate"] == "minimum_complete_draws"
        assert stop["requested_draw_ids"] == [0, 1, 2]
        assert stop["completed_draw_ids"] == [0, 1]
        assert stop["registered_complete_draw_ids"] == [0, 1]
        assert stop["failed_draw_ids"] == [2]
        assert stop["scientific_retry_allowed"] is False
        assert stop["decision_promotion_allowed"] is False
        assert set(stop["retained_partial_sha256"]) >= {
            "point.json", "draws/0000.json", "draws/0001.json", "errors/0002.json"
        }


def test_serialized_nonfinite_draw_does_not_count_as_complete_case(tmp_path: Path) -> None:
    stage = tmp_path / "scientific_finiteness"
    atomic_write_json(stage / "point.json", {"draw_id": "point", "config_sha256": "c",
                                              "completion_bundle_sha256": "f", "finite": True})
    for draw, finite in enumerate([True, False, True]):
        artifact = stage / "draws" / f"{draw:04d}.json"
        atomic_write_json(artifact, {"draw_id": draw, "config_sha256": "c",
                                     "completion_bundle_sha256": "f",
                                     "result": {"finite": finite}})
        register_draw_artifact(stage, draw, artifact, status="complete", config_sha256="c",
                               completion_bundle_sha256="f")
    marker = maybe_finalize_draw_stage(stage, requested_draws=3, minimum_complete_draws=3,
                                       config_sha256="c",
                                       completion_bundle_sha256="f", schema_version="test")
    assert marker is not None and marker.name == "FROZEN_EQUIVOCAL_STOP.json"
    terminal = json.loads(marker.read_text())
    assert terminal["finite_draws"] == 2
    assert terminal["scientifically_finite_draw_ids"] == [0, 2]
    assert terminal["completed_draw_ids"] == [0, 2]
    assert terminal["registered_complete_draw_ids"] == [0, 1, 2]
    assert terminal["stop_code"] == "insufficient_scientifically_finite_draws"
    assert terminal["scientific_retry_allowed"] is False
    assert terminal["decision_promotion_allowed"] is False


def test_nonfinite_point_forces_frozen_stop_even_with_all_finite_draws(tmp_path: Path) -> None:
    stage = tmp_path / "nonfinite_point"
    atomic_write_json(stage / "point.json", {"draw_id": "point", "config_sha256": "c",
                                              "completion_bundle_sha256": "f",
                                              "result": {"finite": False}})
    for draw in range(3):
        artifact = stage / "draws" / f"{draw:04d}.json"
        atomic_write_json(artifact, {"draw_id": draw, "config_sha256": "c",
                                     "completion_bundle_sha256": "f",
                                     "result": {"finite": True}})
        register_draw_artifact(stage, draw, artifact, status="complete", config_sha256="c",
                               completion_bundle_sha256="f")
    marker = maybe_finalize_draw_stage(stage, requested_draws=3, minimum_complete_draws=3,
                                       config_sha256="c", completion_bundle_sha256="f",
                                       schema_version="test")
    assert marker is not None and marker.name == "FROZEN_EQUIVOCAL_STOP.json"
    terminal = json.loads(marker.read_text())
    assert terminal["point_scientifically_finite"] is False
    assert terminal["finite_draws"] == 3
    assert terminal["stop_code"] == "point_scientifically_nonfinite"
    assert terminal["failed_gate"] == "required_point_finiteness"
    assert terminal["requested_draw_ids"] == [0, 1, 2]
    assert terminal["completed_draw_ids"] == [0, 1, 2]
    assert terminal["scientific_retry_allowed"] is False
    assert terminal["decision_promotion_allowed"] is False


def test_series_terminal_rejects_post_terminal_point_tampering(tmp_path: Path) -> None:
    stage = tmp_path / "tamper"
    point_path = stage / "point.json"
    point = {"draw_id": "point", "config_sha256": "c",
             "completion_bundle_sha256": "f", "result": {"finite": True}}
    atomic_write_json(point_path, point)
    rows = []
    registrations = []
    for draw in range(3):
        artifact = stage / "draws" / f"{draw:04d}.json"
        row = {"draw_id": draw, "config_sha256": "c",
               "completion_bundle_sha256": "f", "result": {"finite": True}}
        atomic_write_json(artifact, row)
        registry = register_draw_artifact(stage, draw, artifact, status="complete",
                                          config_sha256="c", completion_bundle_sha256="f")
        rows.append(row)
        registrations.append(registry)
    marker = maybe_finalize_draw_stage(stage, requested_draws=3, minimum_complete_draws=3,
                                       config_sha256="c", completion_bundle_sha256="f",
                                       schema_version="test")
    assert marker is not None and marker.name == "MEASUREMENT_COMPLETE.json"

    def artifacts() -> dict[str, str]:
        return {str(path): __import__("hashlib").sha256(path.read_bytes()).hexdigest()
                for path in [point_path,
                             *(stage / "draws" / f"{draw:04d}.json" for draw in range(3)),
                             *registrations]}

    validate_series_terminal(stage, requested=3, config_sha256="c",
                             completion_bundle_sha256="f", point=point,
                             rows=rows, errors=[], artifacts=artifacts())
    point_path.write_text(json.dumps({**point, "tampered": True}))
    with pytest.raises(RuntimeError, match="terminal disagrees"):
        validate_series_terminal(stage, requested=3, config_sha256="c",
                                 completion_bundle_sha256="f",
                                 point=json.loads(point_path.read_text()),
                                 rows=rows, errors=[], artifacts=artifacts())


def test_producer_attestation_detects_tamper_then_restore(tmp_path: Path) -> None:
    upstream = tmp_path / "baseline.pkl"
    upstream.write_bytes(b"original")
    original_sha = __import__("hashlib").sha256(upstream.read_bytes()).hexdigest()
    upstream.write_bytes(b"tampered")
    tampered_sha = __import__("hashlib").sha256(upstream.read_bytes()).hexdigest()
    payload = {"input_attestation": {str(upstream.resolve()): {
        "sha256": tampered_sha, "size": upstream.stat().st_size}}}
    upstream.write_bytes(b"original")
    with pytest.raises(RuntimeError, match="does not bind current upstream"):
        assert_attested_hash(payload, upstream, original_sha)


def test_stability_finiteness_requires_g7_descriptive_comparison() -> None:
    family = {"f": {"learned_stability_loss": 0.1,
                     "simple_A_B_cka_descriptive": 0.9,
                     "g4_g7_regularizer_sensitivity_cka_descriptive": None,
                     "pair_means": {"g4__g5": 0.8}}}
    assert not stability_draw_finite({"task": {}}, family)
    family["f"]["g4_g7_regularizer_sensitivity_cka_descriptive"] = 0.75
    assert stability_draw_finite({"task": {}}, family)


def test_stability_selectivity_direction_rejects_zeros_and_missing() -> None:
    assert same_nonzero_direction([0.1, 0.2, 0.3])
    assert same_nonzero_direction([-0.1, -0.2, -0.3])
    assert not same_nonzero_direction([0.0, 0.0, 0.0])
    assert not same_nonzero_direction([0.1, None, 0.2])


def test_tier2_manifest_records_duplicate_and_parent_membership_qa() -> None:
    manifest = json.loads(
        (ROOT / "data/atlas_completion_v1/tier2_manifest.json").read_text())
    for tasks in manifest["roles"].values():
        for row in tasks.values():
            assert row["qa"]["duplicate_row_ids"] == 0
            assert row["qa"]["unique_row_ids"] == row["rows"]
            assert row["qa"]["parent_base_membership"] is True
            assert row["qa"]["unknown_parent_base_ids"] == []


def test_frozen_ce_rows_cover_exactly_three_text_families() -> None:
    job = "k2_wave2_fast_g4_L3_s42_inc1e2"
    parent = json.loads((ROOT / f"results/atlas/k2_v1/{job}_functional.json").read_text())
    transforms = {row["transform_id"]: row for row in
                  (json.loads(line) for line in (ROOT / "data/atlas_v1/transforms/C2.jsonl").read_text().splitlines())}
    by_family_group: dict[tuple[str, str], set[str]] = {}
    for row in parent["ce_rows"]:
        transform = transforms[row["transform_id"]]
        key = (transform["family"], transform["template_group"])
        by_family_group.setdefault(key, set()).add(row["transform_id"])
    assert {family for family, _ in by_family_group} == CE_FAMILIES
    assert len({transform_id for ids in by_family_group.values() for transform_id in ids}) == 96
    assert all(len(ids) == 8 for ids in by_family_group.values())
    assert all(sum(family == expected for family, _ in by_family_group) == 4 for expected in CE_FAMILIES)
