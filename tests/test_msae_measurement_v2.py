from __future__ import annotations

import ast
import hashlib
import json
import sys
from pathlib import Path

import numpy as np
import pytest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from msae_measurement_v2 import (  # noqa: E402
    SupportThresholds,
    aggregate_endpoint_records,
    aggregate_statuses,
    audit_task_support,
    branch_cka_matrix,
    canonical_pool,
    cap_rows_by_group,
    counterfactual_delta_cka,
    family_cka_summary,
    linear_cka,
    load_representation_cache,
    map_row_labels,
    numerical_agreement,
    residual_cka,
    resolve_allowlisted_inputs,
    select_identity_vocabulary,
    source_from_group,
    validate_blind_attestation_shape,
    validate_grouping_provenance,
    validate_measurement_config,
    validate_output_root,
    verify_freeze_record,
    write_representation_cache,
)
import msae_measurement_v2 as measurement_v2  # noqa: E402
import audit_msae_measurement_v2 as measurement_cli  # noqa: E402


THRESHOLDS = SupportThresholds(
    min_groups=25,
    min_class_groups=20,
    max_rows_per_group=256,
    bootstrap_draws=500,
    min_finite_draws=490,
    seed=20260802,
)


def _rows_for_source(source: str, groups: int, *, labels: tuple[str, ...] = ("a", "b")) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for group_index in range(groups):
        for label in labels:
            rows.append(
                {
                    "document_group": f"{source}:g{group_index:03d}",
                    "source": source,
                    "label": label,
                    "row_id": f"{source}-{group_index}-{label}",
                }
            )
    return rows


def test_many_balanced_rows_from_one_document_fail_support() -> None:
    rows = [
        {"document_group": "s:g0", "source": "s", "label": str(i % 2), "row_id": f"r{i}"}
        for i in range(20_000)
    ]
    result = audit_task_support(rows, role="calibration", task="identity", expected_sources=["s"], thresholds=THRESHOLDS)
    assert result["status"] == "ineligible"
    assert result["sources"]["s"]["groups"] == 1
    assert result["sources"]["s"]["max_rows_per_group"] == 20_000
    assert "minimum_groups" in result["reasons"]
    assert "maximum_group_contribution" in result["reasons"]


def test_adequate_multidocument_support_passes() -> None:
    result = audit_task_support(
        _rows_for_source("s", 30), role="calibration", task="identity", expected_sources=["s"], thresholds=THRESHOLDS
    )
    assert result["status"] == "eligible"
    assert result["bootstrap"]["finite_draws"] == 500


def test_pooled_source_type_does_not_require_both_labels_within_each_source() -> None:
    rows = []
    for source, label in (("ud", "UD"), ("ner", "NER")):
        rows.extend(_rows_for_source(source, 25, labels=(label,)))
    result = audit_task_support(
        rows,
        role="calibration",
        task="source_type",
        expected_sources=["ud", "ner"],
        thresholds=THRESHOLDS,
        nuisance_pooled=True,
    )
    assert result["status"] == "eligible"
    assert result["pooled_class_group_counts"] == {"NER": 25, "UD": 25}


def test_exact_hash_bootstrap_fixture_for_one_in_500_rare_group() -> None:
    rows = _rows_for_source("wnut", 500, labels=("common",))
    rows.append({"document_group": "wnut:g000", "source": "wnut", "label": "rare", "row_id": "rare"})
    result = audit_task_support(
        rows, role="calibration", task="abs_pos_16", expected_sources=["wnut"], thresholds=THRESHOLDS
    )
    assert result["bootstrap"]["finite_draws"] == 347
    assert result["status"] == "ineligible"
    assert "minimum_class_groups" in result["reasons"]
    assert "bootstrap_completeness" in result["reasons"]


def test_group_cap_round_robins_labels_and_is_deterministic() -> None:
    rows = [
        {"document_group": "s:g", "source": "s", "label": label, "row_id": f"{label}-{i}"}
        for label in ("a", "b", "c")
        for i in range(20)
    ]
    first = cap_rows_by_group(rows, max_rows_per_group=5)
    second = cap_rows_by_group(list(reversed(rows)), max_rows_per_group=5)
    assert [row["row_id"] for row in first] == [row["row_id"] for row in second]
    assert len(first) == 5
    assert {row["label"] for row in first} == {"a", "b", "c"}


def test_frozen_label_mapping_is_applied_before_capping_and_unknowns_fail() -> None:
    rows = [
        {"document_group": "s:g", "source": "s", "label": label, "row_id": f"r{i}"}
        for i, label in enumerate(["12", "13", "14", "15"])
    ]
    mapped = map_row_labels(rows, {str(i): "tail" for i in range(12, 16)})
    assert {row["label"] for row in mapped} == {"tail"}
    assert len(cap_rows_by_group(mapped, max_rows_per_group=2)) == 2
    with pytest.raises(ValueError, match="absent"):
        map_row_labels(rows, {"12": "tail"})


def test_identity_vocabulary_uses_minimum_source_document_frequency() -> None:
    counts = {"s1": {"x": 30, "y": 25, "z": 19}, "s2": {"x": 20, "y": 25, "z": 100}}
    assert select_identity_vocabulary(counts, minimum=20, maximum_size=2) == ["y", "x"]
    with pytest.raises(ValueError, match="fewer than two"):
        select_identity_vocabulary({"s1": {"x": 20}, "s2": {"x": 20}}, minimum=20, maximum_size=256)


def test_source_adapter_is_exact_and_role_bound() -> None:
    mapping = {
        "calibration": {"UD_English-GUM:": "UD_English-GUM", "flaitenberger/wnut_17:": "wnut"},
        "C1": {"UD_English-LinES:": "UD_English-LinES"},
    }
    assert source_from_group("UD_English-GUM:doc", "calibration", mapping) == "UD_English-GUM"
    with pytest.raises(ValueError, match="unmatched"):
        source_from_group("UD_English-GUM:doc", "C1", mapping)


def test_endpoint_status_precedence_and_empty_required_set() -> None:
    assert aggregate_statuses(["eligible", "not_run"]) == {"status": "not_run", "reason": "required_not_run"}
    assert aggregate_statuses(["not_run", "ineligible"]) == {"status": "ineligible", "reason": "required_ineligible"}
    assert aggregate_statuses(["eligible", "eligible"])["status"] == "eligible"
    assert aggregate_statuses([]) == {"status": "ineligible", "reason": "no_required_endpoints"}


def test_structured_endpoint_aggregation_preserves_finite_values_and_all_blocks() -> None:
    endpoints = {
        "task": {"status": "eligible", "reasons": [], "observed_value": 0.8},
        "stability": {"status": "ineligible", "reasons": ["missing_family"], "observed_value": 0.71},
    }
    result = aggregate_endpoint_records(
        endpoints,
        required_endpoints=["task", "stability"],
        additional_blocking_reasons=["replacement_unset"],
    )
    assert result["overall"]["status"] == "ineligible"
    assert result["endpoints"]["task"]["observed_value"] == 0.8
    assert result["endpoints"]["stability"]["observed_value"] == 0.71
    assert result["overall"]["blocking_reasons"] == ["stability:missing_family", "replacement_unset"]
    with pytest.raises(ValueError, match="sequence of strings"):
        aggregate_endpoint_records(
            {"task": {"status": "eligible", "reasons": "not-a-sequence", "observed_value": 0.8}},
            required_endpoints=["task"],
        )


def test_source_type_must_be_a_pooled_nuisance_sentinel() -> None:
    good = {
        "replacement_confirmation": {"status": "unset"},
        "sentinels": {"source_type": {"role": "nuisance", "stratification": "pooled"}},
    }
    validate_measurement_config(good)
    bad = json.loads(json.dumps(good))
    bad["sentinels"]["source_type"] = {"role": "retention", "stratification": "source"}
    with pytest.raises(ValueError, match="source_type"):
        validate_measurement_config(bad)
    promoted = json.loads(json.dumps(good))
    promoted["replacement_confirmation"] = {"status": "ready", "source": None}
    with pytest.raises(ValueError, match="replacement"):
        validate_measurement_config(promoted)


def test_safe_input_resolution_rejects_symlinks_and_digest_mismatch(tmp_path: Path) -> None:
    root = tmp_path / "rows"
    root.mkdir()
    row_file = root / "calibration.task.jsonl"
    row_file.write_text("{}\n", encoding="utf-8")
    digest = hashlib.sha256(row_file.read_bytes()).hexdigest()
    resolved = resolve_allowlisted_inputs(tmp_path, [{"path": "rows/calibration.task.jsonl", "sha256": digest}], [root])
    assert resolved == [row_file.resolve()]

    alias = root / "alias.jsonl"
    alias.symlink_to(row_file)
    with pytest.raises(ValueError, match="symlink"):
        resolve_allowlisted_inputs(tmp_path, [{"path": "rows/alias.jsonl", "sha256": digest}], [root])
    with pytest.raises(ValueError, match="digest"):
        resolve_allowlisted_inputs(tmp_path, [{"path": "rows/calibration.task.jsonl", "sha256": "0" * 64}], [root])


def test_complete_path_plan_is_validated_before_any_digest_open(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    root = tmp_path / "rows"
    root.mkdir()
    first = root / "first.jsonl"
    first.write_text("{}\n", encoding="utf-8")
    alias = root / "second.jsonl"
    alias.symlink_to(first)
    entries = [
        {"path": "rows/first.jsonl", "sha256": hashlib.sha256(first.read_bytes()).hexdigest()},
        {"path": "rows/second.jsonl", "sha256": hashlib.sha256(first.read_bytes()).hexdigest()},
    ]
    monkeypatch.setattr(measurement_v2, "sha256_file", lambda _path: pytest.fail("digest opened before path-plan refusal"))
    monkeypatch.setattr(Path, "open", lambda *_args, **_kwargs: pytest.fail("file opened before path-plan refusal"))
    with pytest.raises(ValueError, match="symlink"):
        resolve_allowlisted_inputs(tmp_path, entries, [root])


def test_output_root_is_exact_absent_and_not_symlinked(tmp_path: Path) -> None:
    reports = tmp_path / "reports"
    reports.mkdir()
    output = validate_output_root(tmp_path, "reports/atlas_measurement_v2", reports)
    assert output == reports / "atlas_measurement_v2"
    output.mkdir()
    with pytest.raises(ValueError, match="already exists"):
        validate_output_root(tmp_path, "reports/atlas_measurement_v2", reports)

    output.rmdir()
    real_parent = tmp_path / "real_reports"
    real_parent.mkdir()
    reports.rmdir()
    reports.symlink_to(real_parent, target_is_directory=True)
    with pytest.raises(ValueError, match="symlink"):
        validate_output_root(tmp_path, "reports/atlas_measurement_v2", reports)


def test_existing_reviewed_output_refuses_before_row_digest_access(monkeypatch: pytest.MonkeyPatch) -> None:
    config = json.loads((ROOT / "configs" / "atlas_measurement_v2" / "prescore.json").read_text(encoding="utf-8"))
    monkeypatch.setattr(
        measurement_cli,
        "resolve_allowlisted_inputs",
        lambda *_args, **_kwargs: pytest.fail("row resolver called before existing-output refusal"),
    )
    with pytest.raises(ValueError, match="already exists"):
        measurement_cli.run(config)


def test_freeze_record_verification_includes_trust_root(tmp_path: Path) -> None:
    payload = tmp_path / "payload.txt"
    payload.write_text("frozen", encoding="utf-8")
    record = tmp_path / "freeze.json"
    record.write_text(
        json.dumps({"bundle_files": [{"path": "payload.txt", "sha256": hashlib.sha256(payload.read_bytes()).hexdigest()}]}),
        encoding="utf-8",
    )
    result = verify_freeze_record(tmp_path, record)
    assert result["ok"] is True
    assert {entry["path"] for entry in result["inventory"]} == {"freeze.json", "payload.txt"}
    payload.write_text("drift", encoding="utf-8")
    assert verify_freeze_record(tmp_path, record)["ok"] is False


def test_cache_lineage_pooling_and_tamper_detection(tmp_path: Path) -> None:
    values = np.asarray([[1, 3], [3, 5], [10, 20]], dtype=np.float32)
    cache = tmp_path / "cache"
    manifest = write_representation_cache(
        cache,
        values=values,
        offsets=np.asarray([0, 2, 3]),
        row_ids=["r1", "r2"],
        checkpoint="g4",
        transform="shift",
    )
    loaded = load_representation_cache(
        cache,
        expected_manifest_sha256=manifest["manifest_sha256"],
        expected_checkpoint="g4",
        expected_transform="shift",
    )
    assert loaded["values"].dtype == np.float32
    assert np.allclose(canonical_pool(loaded["values"], loaded["offsets"]), [[2, 4], [10, 20]])

    (cache / "row_ids.json").write_text('["r2","r1"]\n', encoding="utf-8")
    with pytest.raises(ValueError, match="hash"):
        load_representation_cache(
            cache,
            expected_manifest_sha256=manifest["manifest_sha256"],
            expected_checkpoint="g4",
            expected_transform="shift",
        )


def test_cache_loader_rejects_manifest_that_omits_lineage_hashes(tmp_path: Path) -> None:
    cache = tmp_path / "cache"
    manifest = write_representation_cache(
        cache,
        values=np.ones((2, 2), dtype=np.float32),
        offsets=np.asarray([0, 1, 2]),
        row_ids=["a", "b"],
        checkpoint="g4",
        transform="noop",
    )
    raw = json.loads((cache / "manifest.json").read_text(encoding="utf-8"))
    raw["files"] = {}
    (cache / "manifest.json").write_bytes(measurement_v2.canonical_json_bytes(raw))
    tampered_digest = hashlib.sha256((cache / "manifest.json").read_bytes()).hexdigest()
    with pytest.raises(ValueError, match="three canonical files"):
        load_representation_cache(
            cache,
            expected_manifest_sha256=tampered_digest,
            expected_checkpoint="g4",
            expected_transform="noop",
        )
    assert manifest["checkpoint"] == "g4"
    with pytest.raises(ValueError, match="non-empty"):
        load_representation_cache(
            cache,
            expected_manifest_sha256=tampered_digest,
            expected_checkpoint="",
            expected_transform="noop",
        )


def test_numerical_agreement_is_separate_and_scale_aware() -> None:
    report = numerical_agreement(np.asarray([1.0, 1000.0]), np.asarray([1.00001, 1000.005]), atol=1e-6, rtol=1e-5)
    assert report["passed"] is True
    assert report["max_abs_error"] > 1e-3
    assert numerical_agreement(np.asarray([0.0]), np.asarray([2e-6]), atol=1e-6, rtol=0.0)["passed"] is False


def test_linear_and_branch_cka_have_explicit_degeneracy_and_swap_margin() -> None:
    rng = np.random.default_rng(4)
    pos = rng.normal(size=(80, 5))
    content = rng.normal(size=(80, 7))
    row_ids = [f"r{i}" for i in range(80)]
    assert np.isclose(linear_cka(pos, pos, x_row_ids=row_ids, y_row_ids=row_ids)["value"], 1.0)
    assert linear_cka(
        np.ones((4, 2)), np.ones((4, 3)), x_row_ids=list("abcd"), y_row_ids=list("abcd")
    ) == {"value": None, "reason": "zero_variance"}
    assert linear_cka(pos, pos[::-1], x_row_ids=row_ids, y_row_ids=list(reversed(row_ids))) == {
        "value": None,
        "reason": "row_mismatch",
    }

    matrix = branch_cka_matrix(
        {"pos": pos, "content": content},
        {"pos": content, "content": pos},
        left_row_ids=row_ids,
        right_row_ids=row_ids,
    )
    assert matrix["identity_margin"] < 0
    assert matrix["cells"]["pos__content"]["value"] == pytest.approx(1.0)


def test_residual_cka_removes_shared_nuisance() -> None:
    rng = np.random.default_rng(10)
    z = rng.normal(size=(200, 1))
    x = 4 * z + rng.normal(scale=0.5, size=(200, 3))
    y = 4 * z + rng.normal(scale=0.5, size=(200, 4))
    row_ids = [f"r{i}" for i in range(200)]
    marginal = linear_cka(x, y, x_row_ids=row_ids, y_row_ids=row_ids)["value"]
    conditional = residual_cka(
        x, y, z, x_row_ids=row_ids, y_row_ids=row_ids, nuisance_row_ids=row_ids
    )["value"]
    assert marginal is not None and conditional is not None
    assert marginal > conditional
    assert residual_cka(
        np.ones((2, 1)),
        np.ones((2, 1)),
        np.ones((2, 1)),
        x_row_ids=["a", "b"],
        y_row_ids=["a", "b"],
        nuisance_row_ids=["a", "b"],
    ) == {"value": None, "reason": "insufficient_residual_df"}
    nonfinite = x.copy()
    nonfinite[0, 0] = np.nan
    assert residual_cka(
        nonfinite,
        y,
        z,
        x_row_ids=row_ids,
        y_row_ids=row_ids,
        nuisance_row_ids=row_ids,
    ) == {"value": None, "reason": "nonfinite"}


def test_delta_cka_requires_aligned_pre_post_and_cross_checkpoint_rows() -> None:
    rng = np.random.default_rng(8)
    pre = rng.normal(size=(30, 4))
    delta = rng.normal(size=(30, 4))
    ids = [f"r{i}" for i in range(30)]
    result = counterfactual_delta_cka(
        pre,
        pre + delta,
        pre * 2,
        pre * 2 + delta,
        left_pre_row_ids=ids,
        left_post_row_ids=ids,
        right_pre_row_ids=ids,
        right_post_row_ids=ids,
    )
    assert result["value"] == pytest.approx(1.0)
    mismatch = counterfactual_delta_cka(
        pre,
        pre + delta,
        pre * 2,
        pre * 2 + delta,
        left_pre_row_ids=ids,
        left_post_row_ids=ids,
        right_pre_row_ids=list(reversed(ids)),
        right_post_row_ids=list(reversed(ids)),
    )
    assert mismatch == {"value": None, "reason": "row_mismatch"}


def test_family_cka_keeps_partial_values_descriptive_only() -> None:
    summary = family_cka_summary({"bucket": 0.9, "shift": None}, required_tasks=["bucket", "shift"])
    assert summary == {
        "status": "ineligible",
        "complete_value": None,
        "available_task_mean": 0.9,
        "tasks_available": 1,
        "tasks_required": 2,
        "missing_tasks": ["shift"],
        "undefined_task_reasons": {"shift": "missing"},
    }
    invalid = family_cka_summary({"bucket": float("nan"), "shift": 1.2}, required_tasks=["bucket", "shift"])
    assert invalid["status"] == "ineligible"
    assert invalid["undefined_task_reasons"] == {"bucket": "invalid_cka", "shift": "invalid_cka"}


def test_grouping_provenance_and_blind_attestation_are_disclosure_allowlists() -> None:
    provenance = {
        "dataset_id": "candidate",
        "revision": "abc",
        "bundle_sha256": "a" * 64,
        "grouping_unit_type": "document",
        "grouping_unit_field": "doc_id",
        "grouping_code_sha256": "b" * 64,
        "original_units": 30,
        "groups": 30,
        "dependence_rationale": "publisher document IDs",
        "builder_id": "builder",
        "reviewer_id": "reviewer",
        "review_decision": "pass",
        "reviewed_utc": "2026-08-02T00:00:00Z",
        "builder_key_fingerprint": "builder-key",
        "builder_signature": "sig1",
        "reviewer_key_fingerprint": "reviewer-key",
        "reviewer_signature": "sig2",
    }
    assert validate_grouping_provenance(provenance)["authorization"] == "blocked"
    same_person = dict(provenance, reviewer_id="builder")
    with pytest.raises(ValueError, match="distinct"):
        validate_grouping_provenance(same_person)
    with pytest.raises(ValueError, match="split"):
        validate_grouping_provenance(dict(provenance, groups=31))

    attestation = {
        "schema_version": "atlas_measurement_v2_attestation",
        "protocol_config_sha256": "c" * 64,
        "dataset_bundle_sha256": "d" * 64,
        "grouping_code_sha256": "b" * 64,
        "producer_id": "custodian",
        "key_fingerprint": "custodian-key",
        "created_utc": "2026-08-02T00:00:00Z",
        "tasks": [],
        "signature": "signed",
    }
    assert validate_blind_attestation_shape(attestation)["authorization"] == "blocked"
    with pytest.raises(ValueError, match="disallowed"):
        validate_blind_attestation_shape(dict(attestation, labels=["secret"]))


@pytest.mark.parametrize("relative", ["scripts/msae_measurement_v2.py", "scripts/audit_msae_measurement_v2.py"])
def test_measurement_code_has_no_experiment_or_network_imports(relative: str) -> None:
    tree = ast.parse((ROOT / relative).read_text(encoding="utf-8"))
    imported = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported.add(node.module.split(".")[0])
    assert imported.isdisjoint({"torch", "transformers", "datasets", "requests", "subprocess", "socket"})


def test_reviewed_config_is_digest_bound_and_contains_only_public_audit_inputs() -> None:
    config_path = ROOT / "configs" / "atlas_measurement_v2" / "prescore.json"
    config = json.loads(config_path.read_text(encoding="utf-8"))
    validate_measurement_config(config)
    assert len(config["inputs"]) == 54
    assert len({entry["path"] for entry in config["inputs"]}) == 54
    assert config["roles"] == ["calibration", "C1", "C2"]
    assert config["output_root"] == "reports/atlas_measurement_v2"
    assert config["replacement_confirmation"]["status"] == "unset"
    for entry in config["inputs"]:
        assert not {"final", "private", "blind", "unlock"}.intersection(Path(entry["path"]).parts)
        assert hashlib.sha256((ROOT / entry["path"]).read_bytes()).hexdigest() == entry["sha256"]
        assert bool(entry["nuisance_pooled"]) == (entry["task"] == "source_type")
        assert isinstance(entry["required_for_task_measurability"], bool)
        contract = config["label_contracts"][entry["label_contract"]]
        if contract["type"] == "mapping":
            observed = {
                (json.loads(line)["label"].split(":", 1)[0] if contract.get("strip_subtype") else json.loads(line)["label"])
                for line in (ROOT / entry["path"]).read_text(encoding="utf-8").splitlines()
            }
            assert observed <= set(contract["mapping"])

    cli_tree = ast.parse((ROOT / "scripts" / "audit_msae_measurement_v2.py").read_text(encoding="utf-8"))
    constants = {
        target.id: node.value.value
        for node in cli_tree.body
        if isinstance(node, ast.Assign)
        for target in node.targets
        if isinstance(target, ast.Name)
        and target.id == "CONFIG_SHA256"
        and isinstance(node.value, ast.Constant)
    }
    assert constants["CONFIG_SHA256"] == hashlib.sha256(config_path.read_bytes()).hexdigest()


def test_pure_prescore_path_cannot_create_processes_or_network_connections(monkeypatch: pytest.MonkeyPatch) -> None:
    import socket
    import subprocess

    monkeypatch.setattr(socket, "socket", lambda *_args, **_kwargs: pytest.fail("network access attempted"))
    monkeypatch.setattr(socket, "create_connection", lambda *_args, **_kwargs: pytest.fail("network access attempted"))
    monkeypatch.setattr(socket, "getaddrinfo", lambda *_args, **_kwargs: pytest.fail("network access attempted"))
    monkeypatch.setattr(subprocess, "Popen", lambda *_args, **_kwargs: pytest.fail("process creation attempted"))
    monkeypatch.setattr(subprocess, "run", lambda *_args, **_kwargs: pytest.fail("process creation attempted"))
    monkeypatch.setattr(measurement_cli.os, "system", lambda *_args, **_kwargs: pytest.fail("process creation attempted"))
    for name in ("spawnl", "spawnle", "spawnlp", "spawnlpe", "spawnv", "spawnve", "spawnvp", "spawnvpe", "posix_spawn", "posix_spawnp"):
        if hasattr(measurement_cli.os, name):
            monkeypatch.setattr(measurement_cli.os, name, lambda *_args, **_kwargs: pytest.fail("process creation attempted"))
    config = json.loads((ROOT / "configs" / "atlas_measurement_v2" / "prescore.json").read_text(encoding="utf-8"))
    monkeypatch.setattr(Path, "open", lambda *_args, **_kwargs: pytest.fail("row file opened on safe refusal path"))
    with pytest.raises(ValueError, match="already exists"):
        measurement_cli.run(config)


def test_process_evidence_unavailable_fails_closed() -> None:
    with pytest.raises(ValueError, match="fails closed"):
        measurement_cli._require_clean_process_snapshot(
            {"available": False, "processes": [], "experiment_matches": []}, stage="before"
        )
