from __future__ import annotations

import copy
import contextlib
import json
import math
import shutil
from pathlib import Path

import numpy as np
import pytest
import torch

import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import atlas_rope_v4 as core
import diagnose_atlas_rope_v4 as diagnostic
import run_atlas_rope_v4 as runner


def _synthetic_bases() -> list[dict[str, object]]:
    bases: list[dict[str, object]] = []
    for bin_name, lower, _ in core.LENGTH_BINS:
        for index in range(20):
            document = f"{bin_name}-doc-{index // 2:02d}"
            input_ids = list(range(1, lower + 1))
            bases.append(
                {
                    "source": "synthetic",
                    "document_id": document,
                    "sent_id": f"{bin_name}-sentence-{19-index:02d}",
                    "length_bin": bin_name,
                    "input_ids": input_ids,
                    "sequence_sha256": core.sequence_sha256([*input_ids, index]),
                    "content_sha256": core.normalized_text_hash(f"{bin_name} {index}"),
                }
            )
    return bases


def test_make_grid_units_aligns_rows_after_canonical_reference_sort() -> None:
    references, candidates, rows = core.make_grid_units("synthetic", list(reversed(_synthetic_bases())))
    core.validate_grid_units(references, candidates, rows, source="synthetic")
    assert all(
        references[index]["base_id"] == rows[2 * index]["base_id"] == rows[2 * index + 1]["base_id"]
        for index in range(100)
    )
    assert [row["row_id"] for row in rows[:2]] == references[0]["row_ids"]


def test_validate_grid_rejects_row_reference_misalignment() -> None:
    references, candidates, rows = core.make_grid_units("synthetic", _synthetic_bases())
    bad_rows = copy.deepcopy(rows)
    bad_rows[:2], bad_rows[2:4] = bad_rows[2:4], bad_rows[:2]
    with pytest.raises(RuntimeError, match="row manifest is not aligned"):
        core.validate_grid_units(references, candidates, bad_rows, source="synthetic")


def test_prescore_panels_are_reference_row_aligned() -> None:
    for source in ("EWT_calibration", "GUM_fresh_validation", "GENTLE_validation"):
        root = ROOT / "data/atlas_rope_v4_attempt8" / source
        references = core.read_jsonl(root / "references.jsonl")
        candidates = core.read_jsonl(root / "candidates.jsonl")
        rows = core.read_jsonl(root / "rows.jsonl")
        core.validate_grid_units(references, candidates, rows, source=source)


def test_document_capped_selection_has_real_cluster_support() -> None:
    selected, report = core.deterministic_document_capped_selection(_synthetic_bases())
    assert len(selected) == 100
    assert all(row["status"] == "eligible" and row["documents"] == 10 for row in report.values())
    assert all(row["max_per_document"] == 2 for row in report.values())
    sparse = [row for row in _synthetic_bases() if row["length_bin"] != "65-128"]
    sparse.extend({**row, "document_id": "single-long-doc"} for row in _synthetic_bases() if row["length_bin"] == "65-128")
    with pytest.raises(RuntimeError, match="cannot fill required bin"):
        core.deterministic_document_capped_selection(sparse)


def test_batch_schedules_are_frozen_and_contiguous() -> None:
    references, candidates, _ = core.make_grid_units("synthetic", _synthetic_bases())
    reference_schedule = core.batch_schedule(references)
    candidate_schedule = core.batch_schedule(candidates)
    assert [row["tensor_shape"][0] for row in reference_schedule] == [64, 36]
    assert [row["tensor_shape"][0] for row in candidate_schedule] == [64] * 9 + [24]
    assert reference_schedule[-1]["final_partial"] is True
    assert candidate_schedule[-1]["final_partial"] is True
    assert all(row["padding"] == {"input_id": 0, "attention_mask": 0, "position_id": 0, "side": "right"}
               for row in reference_schedule + candidate_schedule)


def test_exact_cached_replay_checks_bytes_dtype_order_and_ids() -> None:
    array = np.arange(12, dtype=np.float32).reshape(3, 4)
    passed = core.exact_cached_replay(array, array.copy(), ["a", "b", "c"], ["a", "b", "c"],
                                      left_child_hash="left", right_child_hash="right")
    assert passed["status"] == "PASS"
    failed = core.exact_cached_replay(array, np.asfortranarray(array), ["a", "b", "c"], ["a", "c", "b"],
                                      left_child_hash="left", right_child_hash="right")
    assert failed["status"] == "FAIL"
    assert failed["checks"]["row_ids_equal"] is False
    assert failed["checks"]["c_contiguous"] is False


def test_metric_zero_near_zero_and_nonfinite_semantics() -> None:
    zeros = np.zeros((2, 4), dtype=np.float32)
    metrics = core.row_error_metrics(zeros, zeros.copy())
    assert np.array_equal(metrics.relative_l2, np.zeros(2))
    assert np.array_equal(metrics.cosine_distance, np.zeros(2))
    one_nonzero = zeros.copy()
    one_nonzero[0, 0] = np.float32(1e-12)
    metrics = core.row_error_metrics(zeros, one_nonzero)
    assert math.isinf(float(metrics.cosine_distance[0]))
    nonfinite = zeros.copy()
    nonfinite[1, 0] = np.nan
    score = core.score_cell(zeros, nonfinite, atol=1e-6, relative_l2_cap=1e-5, cosine_cap=1e-10)
    assert score["status"] == "FAIL"
    assert score["nonfinite_rows"] == 1
    assert score["maxima"]["absolute_difference"] is None
    # Failure artifacts must still be strict JSON rather than NaN/Infinity JSON.
    core.canonical_json_bytes(score)


def test_coordinate_budgets_are_exact_and_row_concentration_matters() -> None:
    reference = np.ones((40, core.WIDTH), dtype=np.float32)
    candidate = reference.copy()
    candidate[0, :30] += np.float32(7e-6)
    score = core.score_cell(reference, candidate, atol=1e-6, relative_l2_cap=1.0, cosine_cap=1.0)
    assert score["status"] == "PASS"
    assert score["coordinate_failing_elements"] == 30
    assert score["coordinate_failing_rows"] == 1
    candidate[0, 30] += np.float32(7e-6)
    assert core.score_cell(reference, candidate, atol=1e-6, relative_l2_cap=1.0, cosine_cap=1.0)["status"] == "FAIL"
    candidate = reference.copy()
    for row in range(3):
        candidate[row, :10] += np.float32(7e-6)
    concentrated = core.score_cell(reference, candidate, atol=1e-6, relative_l2_cap=1.0, cosine_cap=1.0)
    assert concentrated["coordinate_failing_elements"] == 30
    assert concentrated["coordinate_failing_rows"] == 3
    assert concentrated["status"] == "FAIL"


def test_strict_sentinel_budget_permits_no_coordinate_failure() -> None:
    reference = np.ones((1, core.WIDTH), dtype=np.float32)
    candidate = reference.copy()
    candidate[0, 0] += np.float32(7e-6)
    score = core.score_cell(reference, candidate, atol=1e-6, relative_l2_cap=1.0,
                            cosine_cap=1.0, strict_zero_failures=True)
    assert score["status"] == "FAIL"
    assert score["budgets"]["coordinate_failing_elements"] == 0


def test_cap_grid_boundary_and_out_of_grid() -> None:
    assert core.choose_grid_cap(8e-7, core.ATOL_GRID) == 1e-6
    assert core.choose_grid_cap(8e-6, core.ATOL_GRID) is None
    assert core.choose_grid_cap(float("nan"), core.ATOL_GRID) is None
    reference = np.ones((1, 4), dtype=np.float32)
    candidate = reference.copy()
    candidate[0, 0] += np.float32(1e-3)
    assert core.derive_caps([(reference, candidate)])["status"] == "INELIGIBLE"


def test_score_grid_has_every_required_cell_and_rejects_missing_rows() -> None:
    references, candidates, rows = core.make_grid_units("synthetic", _synthetic_bases())
    reference_array = np.ones((200, core.WIDTH), dtype=np.float32)
    candidate_array = np.ones((1200, core.WIDTH), dtype=np.float32)
    result = core.score_grid(reference_array, candidate_array, rows, atol=5e-7,
                             relative_l2_cap=2e-6, cosine_cap=1e-11)
    assert result["status"] == "PASS"
    assert len(result["cells"]) == result["required_cells"] == 30
    bad_rows = copy.deepcopy(rows)
    bad_rows[0]["length_bin"] = "9-16"
    with pytest.raises(RuntimeError, match="length-bin mismatch|missing required grid cell"):
        core.score_grid(reference_array, candidate_array, bad_rows, atol=5e-7,
                        relative_l2_cap=2e-6, cosine_cap=1e-11)


def test_float64_rotary_translation_and_inverse_transport() -> None:
    generator = np.random.default_rng(17)
    value = generator.normal(size=(1, 2, 7, 64)).astype(np.float64)
    inv_freq = 1.0 / (10000.0 ** (np.arange(0, 16, 2, dtype=np.float64) / 16.0))
    positions = np.arange(7, dtype=np.float64)[None, :]
    reference = core.rotary_numpy_float64(value, positions, inv_freq)
    shifted = core.rotary_numpy_float64(value, positions + 32, inv_freq)
    aligned = core.inverse_transport_numpy_float64(shifted, 32, inv_freq)
    np.testing.assert_allclose(aligned, reference, atol=2e-14, rtol=2e-14)
    # Non-rotary dimensions are exact pass-through values.
    assert np.array_equal(shifted[..., 16:], value[..., 16:])


def test_float32_rotary_reconstruction_matches_float64_reference() -> None:
    generator = np.random.default_rng(23)
    value = generator.normal(size=(1, 2, 5, 64)).astype(np.float32)
    inv_freq = (1.0 / (10000.0 ** (np.arange(0, 16, 2, dtype=np.float32) / 16.0))).astype(np.float32)
    observed = diagnostic._rotate_float32(torch.from_numpy(value), list(range(5)), torch.from_numpy(inv_freq)).numpy()
    expected = core.rotary_numpy_float64(value, np.arange(5)[None, :], inv_freq)
    np.testing.assert_allclose(observed, expected, atol=2e-6, rtol=5e-6)


def test_qk_shape_and_causal_valid_indices() -> None:
    qkv = torch.zeros((1, 5, 3 * 12 * 64), dtype=torch.float32)
    query, key = diagnostic._split_qk(qkv)
    assert query.shape == key.shape == (1, 12, 5, 64)
    with pytest.raises(RuntimeError, match="shape drift"):
        diagnostic._split_qk(torch.zeros((1, 5, 12), dtype=torch.float32))
    query_np = np.ones((1, 1, 3, 4), dtype=np.float64)
    logits, mask = core.causal_valid_logits(query_np, query_np)
    assert logits.shape == (6,)
    assert int(mask.sum()) == 6
    assert np.all(logits == 2.0)


def test_diagnostic_population_count_and_order() -> None:
    conditions, manifest = diagnostic._diagnostic_conditions()
    assert len(conditions) == manifest["condition_units"] == 140
    assert sum(len(row["positions"]) for row in conditions) == manifest["selected_rows"] == 280
    for start in range(0, 140, 7):
        block = conditions[start : start + 7]
        assert [int(row["shift"]) for row in block] == [0, *core.SHIFTS]
        assert len({str(row["base_id"]) for row in block}) == 1


def test_diagnostic_observer_comparison_is_byte_and_lineage_strict() -> None:
    hidden = np.arange(12, dtype=np.float32).reshape(3, 4)
    checks = diagnostic.observer_comparison(hidden, hidden.copy(), {"row_ids": ["a", "b", "c"]},
                                            {"row_ids": ["a", "b", "c"]}, "same", "same")
    assert all(checks.values())
    changed = hidden.copy()
    changed[0, 0] = np.nextafter(changed[0, 0], np.float32(1.0))
    checks = diagnostic.observer_comparison(hidden, changed, {"row_ids": ["a", "b", "c"]},
                                            {"row_ids": ["a", "c", "b"]}, "same", "different")
    assert not any(checks.values())


def test_actual_gentle_and_sentinel_support_contracts() -> None:
    gentle = ROOT / "data/atlas_rope_v4_attempt8/GENTLE_validation/panel.json"
    panel = core.read_json(gentle)
    support = panel["selection_support"]
    assert support["selected_panel_union_documents"] >= support["selected_panel_union_minimum"] == 20
    assert all(support[name]["documents"] >= 10 and support[name]["retained"] == 20
               for name, _, _ in core.LENGTH_BINS)
    source_path = ROOT / "data/atlas_rope_v4_raw/UD_English-GENTLE/fd7a1bfc82896e362c66f59492b5525940f52fa7/en_gentle-ud-test.conllu"
    integer_forms = []
    for line in source_path.read_text(encoding="utf-8").splitlines():
        fields = line.split("\t")
        if fields and fields[0].isdigit() and len(fields) > 1:
            integer_forms.append(fields[1])
    assert integer_forms and "_" not in integer_forms
    sentinel = core.read_json(ROOT / "data/atlas_rope_v4_attempt8/GUM_fresh_sentinel/panel.json")
    assert sentinel["pairs"] == 16
    assert sentinel["expanded_rows_per_side"] == 24
    assert [row["tensor_shape"][0] for row in sentinel["schedules"]["reference"]] == [16]
    assert len(sentinel["schedules"]["reference_repeats"]) == 3


def test_source_role_and_sequence_overlap_guards() -> None:
    references, candidates, rows = core.make_grid_units("synthetic", _synthetic_bases())
    leaked = copy.deepcopy(candidates)
    leaked[0]["source"] = "other"
    with pytest.raises(RuntimeError, match="source role leakage"):
        core.validate_grid_units(references, leaked, rows, source="synthetic")
    assert core.bidirectional_sequence_view_overlap([2, 3], [1, 2, 3, 4]) is True
    assert core.bidirectional_sequence_view_overlap([7, 8], [1, 2, 3, 4]) is False


def test_output_allowlist_static_scan_and_stale_staging(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    output = tmp_path / "output"
    output.mkdir()
    (output / "allowed.json").write_text("{}", encoding="utf-8")
    core.assert_output_allowlist(output, {"allowed.json"})
    (output / "checkpoint.pt").write_bytes(b"not a checkpoint")
    with pytest.raises(RuntimeError, match="allowlist drift|forbidden"):
        core.assert_output_allowlist(output, {"allowed.json"})
    clean = tmp_path / "clean.py"
    clean.write_text("x = 1\n", encoding="utf-8")
    forbidden = tmp_path / "forbidden.py"
    forbidden.write_text("import torch." + "optim\n", encoding="utf-8")
    assert core.static_no_training_scan([clean])["status"] == "PASS"
    assert core.static_no_training_scan([forbidden])["status"] == "FAIL"
    monkeypatch.setattr(core, "RUN_ROOT", tmp_path / "run")
    stale = core.RUN_ROOT / "staging" / "stage-abcdef123456-old"
    stale.mkdir(parents=True)
    with pytest.raises(RuntimeError, match="stale staging"):
        core.new_staging("stage", "abcdef1234567890")


def test_signed_retirement_verifies_and_tampering_fails() -> None:
    retirement = core.read_json(ROOT / "pilot_runs/20260803_atlas_rope_technical_v4/provenance/ATTEMPT7_RETIRED.json")
    payload = core.verify_envelope(retirement)
    assert payload["status"] == "RETIRED_NO_RETRY"
    tampered = copy.deepcopy(retirement)
    tampered["payload"]["status"] = "RETIRED_RETRY"
    with pytest.raises(RuntimeError, match="message digest drift"):
        core.verify_envelope(tampered)


def test_terminal_helper_is_fail_closed_and_no_retry(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, object] = {}

    def fake_write(path: Path, payload: dict[str, object], signing_key: Path, *, create_once: bool = True) -> str:
        captured.update({"path": path, "payload": payload, "signing_key": signing_key, "create_once": create_once})
        return "digest"

    monkeypatch.setattr(core, "RUN_ROOT", tmp_path / "run")
    monkeypatch.setattr(core, "write_signed", fake_write)
    path = core.sign_terminal(tmp_path / "key.pem", status="TERMINAL_TEST", reason="synthetic failure",
                              lineage={"child": "digest"})
    assert path == tmp_path / "run/TERMINAL.json"
    payload = captured["payload"]
    assert isinstance(payload, dict)
    assert payload["schema_version"] == core.TERMINAL_SCHEMA
    assert payload["no_retry_authorized"] is True
    assert payload["neural_training_authorized"] is False
    assert captured["create_once"] is True


def test_library_attestation_requires_exact_required_and_unique_sonames() -> None:
    required = [{"canonical_path": "/a/lib.so", "soname": "lib.so", "sha256": "aaa"}]
    assert core.verify_library_attestation(required, required, forbidden_sonames=[])["status"] == "PASS"
    conflict = [*required, {"canonical_path": "/b/lib.so", "soname": "lib.so", "sha256": "bbb"}]
    result = core.verify_library_attestation(required, conflict, forbidden_sonames=[])
    assert result["status"] == "FAIL"
    assert result["conflicting_duplicate_sonames"]
    assert core.verify_library_attestation(required, [], forbidden_sonames=[])["status"] == "FAIL"


def test_controller_stage_order_matches_frozen_config_and_uses_gentle() -> None:
    config = core.read_json(ROOT / "configs/atlas_rope_v4/prescore.json")
    assert tuple(config["stage_order"]) == runner.CONTROLLER_STAGE_ORDER
    assert "run_gentle" in runner.CONTROLLER_STAGE_ORDER
    assert not any("eslspok" in stage.casefold() for stage in runner.CONTROLLER_STAGE_ORDER)


def test_every_reviewed_path_mutation_fails_exact_inventory(tmp_path: Path) -> None:
    archive = ROOT / "pilot_runs/20260803_atlas_rope_technical_v4/failed_implementation_candidates/cc62c33e_BLOCK_v1"
    candidate = core.read_json(archive / "implementation_candidate.json")
    snapshot = tmp_path / "snapshot"
    shutil.copytree(archive / "snapshot", snapshot)
    paths = {name: snapshot / name for name in candidate["implementation_inventory"]}
    runner._verify_exact_inventory(paths, candidate["implementation_inventory"])
    for name, path in paths.items():
        original = path.read_bytes()
        path.write_bytes(original + b"mutation")
        try:
            with pytest.raises(RuntimeError, match="inventory drift"):
                runner._verify_exact_inventory(paths, candidate["implementation_inventory"])
        finally:
            path.write_bytes(original)


def test_validation_rejects_implementation_drift_before_model_load(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    signing_key = tmp_path / "key.pem"
    signing_key.write_text("not read", encoding="utf-8")
    loaded = False

    monkeypatch.setattr(runner, "_assert_not_terminal", lambda: None)
    monkeypatch.setattr(runner, "_verify_implementation_candidate",
                        lambda: (_ for _ in ()).throw(RuntimeError("implementation candidate inventory drift")))
    monkeypatch.setattr(runner, "_terminalize", lambda *args, **kwargs: None)

    def load_model(*args: object, **kwargs: object) -> object:
        nonlocal loaded
        loaded = True
        return object()

    monkeypatch.setattr(runner, "_load_model", load_model)
    with pytest.raises(RuntimeError, match="inventory drift"):
        runner.run_gum(signing_key)
    assert loaded is False


def test_runtime_preflight_failure_prevents_score_forward(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    signing_key = tmp_path / "key.pem"
    signing_key.write_text("not read", encoding="utf-8")
    extraction_called = False
    forward_called = False
    monkeypatch.setattr(runner, "_assert_not_terminal", lambda: None)
    monkeypatch.setattr(runner, "_verify_prescore", lambda: ({"seed": 1}, {}))
    monkeypatch.setattr(runner, "_verify_authorization", lambda *args, **kwargs: {})
    monkeypatch.setattr(runner, "exclusive_lock", lambda *args, **kwargs: contextlib.nullcontext())
    monkeypatch.setattr(runner, "_seed_runtime", lambda seed: None)
    monkeypatch.setattr(runner, "_load_model", lambda *args, **kwargs: object())
    monkeypatch.setattr(runner, "_runtime_attestation",
                        lambda *args, **kwargs: (_ for _ in ()).throw(RuntimeError("runtime mismatch")))
    monkeypatch.setattr(runner, "_terminalize", lambda *args, **kwargs: None)

    def extract(*args: object, **kwargs: object) -> dict[str, object]:
        nonlocal extraction_called
        extraction_called = True
        return {}

    def forward(*args: object, **kwargs: object) -> np.ndarray:
        nonlocal forward_called
        forward_called = True
        return np.empty((0, 0), dtype=np.float32)

    monkeypatch.setattr(runner, "_extract_grid", extract)
    monkeypatch.setattr(runner, "_forward_units", forward)
    with pytest.raises(RuntimeError, match="runtime mismatch"):
        runner.run_ewt(signing_key)
    assert extraction_called is False
    assert forward_called is False


def test_retained_attempt7_semantics_recompute_and_corruption_rejects(tmp_path: Path) -> None:
    source = ROOT / "pilot_runs/20260803_atlas_discovery_v3_3_attempt7/staging/qa-EWT-2cc24b036a00-2392334"
    copied = tmp_path / "qa"
    shutil.copytree(source, copied)
    reference, candidate, lineage = runner._retained_attempt7_pair(qa_root_override=copied)
    assert reference.shape == candidate.shape == (72, core.WIDTH)
    assert lineage["semantic_verification"] == "PASS"
    assert lineage["expanded_rows"] == 72
    for name in ("QA_COMPLETE.json", "qa_rows.json", "qa_arrays.float32.npz"):
        path = copied / name
        original = path.read_bytes()
        path.write_bytes(original + b"corruption")
        try:
            with pytest.raises(Exception):
                runner._retained_attempt7_pair(qa_root_override=copied)
        finally:
            path.write_bytes(original)
