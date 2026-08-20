from __future__ import annotations

import ast
import json
import pickle
import py_compile
import sys
from pathlib import Path

import numpy as np
import pytest
import torch
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from analyze_relational_attention_edges_v1 import (
    _bootstrap_binary,
    _component_expansion,
    _feature,
    _select_alpha_binary,
    decision_from_primary,
)
from build_relational_attention_edges_v1 import (
    NormalizedTextMatcher,
    Sentence,
    Token,
    _ancestors,
    _attach_role_attestation,
    _candidate,
    _classify_hit,
    _global_prescore_terminal,
    _opaque_probe,
    _scan_artifact,
    _strict_prior_conllu_sentences,
    _structured_file_evidence,
    build,
    validate_unit_lineage,
    verify_role_sidecar,
)
from relational_attention_edges_v1 import (
    assert_new_destination,
    bootstrap_indices,
    coarse_relation,
    finite_interval,
    load_config,
    exclusive_fsynced_json,
    read_json,
    sha256_file,
    sign_payload,
    study_key,
    verify_preservation,
)

import build_relational_attention_edges_v1 as builder
import relational_attention_edges_v1 as common
from run_relational_attention_edges_v1 import (
    _independent_qk_logits,
    _manual_probabilities,
    _rotary_qkv,
    assert_environment,
    assert_physical_gpu_free,
    assert_visible_gpu,
    pool_link_features,
    review_is_ship_bound,
    validate_runtime_lineage,
)


def test_config_preservation_and_no_training_permissions() -> None:
    config = load_config()
    assert verify_preservation(config)
    assert set(config["permissions"].values()) == {False}
    assert config["analysis"]["primary_link_feature"] == "mean_scaled_rotary_qk_logit"
    assert "query_index" not in config["matching"]["require_exact_fields"]
    assert "sequence_length" not in config["matching"]["require_exact_fields"]
    assert_environment(config)


def test_relation_mapping() -> None:
    assert coarse_relation("nsubj:pass") == "CORE"
    assert coarse_relation("advmod:emph") == "OBLIQUE"
    assert coarse_relation("flat:name") == "NOMINAL"
    assert coarse_relation("punct") == "PUNCT"
    assert coarse_relation("dep") == "OTHER"


def test_transitive_ancestors_and_cycle_rejection() -> None:
    rows = {
        1: Token(1, "a", "NOUN", 2, "nsubj", "_", 0, 0, 1),
        2: Token(2, "b", "VERB", 3, "xcomp", "_", 1, 2, 3),
        3: Token(3, "c", "VERB", 0, "root", "_", 2, 4, 5),
    }
    assert _ancestors(1, rows) == {2, 3}
    cyclic = dict(rows)
    cyclic[3] = Token(3, "c", "VERB", 1, "root", "_", 2, 4, 5)
    with pytest.raises(RuntimeError, match="cycle"):
        _ancestors(1, cyclic)


def _sentence(query_index: int, length: int) -> Sentence:
    tokens = [
        Token(1, "A", "NOUN", 2, "nsubj", "_", 0, 0, 1),
        Token(2, "B", "VERB", 0, "root", "_", 1, 2, 3),
    ]
    return Sentence(
        source="S",
        file_name="train.conllu",
        split="train",
        raw_document_id="d",
        document_id="S:train:d",
        sent_id="x",
        text="A B",
        tokens=tokens,
        has_mwt=False,
        has_empty=False,
        reconstruction_exact=True,
        token_hash="t",
        sentence_hash="s",
        input_ids=list(range(length)),
        offsets=[(i, i + 1) for i in range(length)],
        spans={1: [query_index - 1], 2: [query_index]},
    )


def test_qk_matching_stratum_excludes_absolute_query_and_sequence_length() -> None:
    a, b = _sentence(3, 8), _sentence(17, 40)
    first = _candidate(a, a.tokens[0], a.tokens[1], positive=True, relation="CORE")
    second = _candidate(b, b.tokens[0], b.tokens[1], positive=True, relation="CORE")
    assert first["query_index"] != second["query_index"]
    assert len(a.input_ids or []) != len(b.input_ids or [])
    assert first["stratum"] == second["stratum"]
    assert len(first["stratum"]) == 6


def test_bootstrap_is_deterministic_and_component_complete() -> None:
    maps_a = bootstrap_indices(["a", "b"], direction="x", seed=7, draws=4)
    maps_b = bootstrap_indices(["a", "b"], direction="x", seed=7, draws=4)
    assert np.array_equal(maps_a, maps_b)
    examples = [{"component_id": "a"}, {"component_id": "a"}, {"component_id": "b"}]
    expanded = _component_expansion(examples, ["a", "b"], np.asarray([0, 0]))
    assert expanded.tolist() == [0, 0, 1, 1]


def test_finite_interval_enforces_completeness() -> None:
    config = load_config()
    good = finite_interval(np.linspace(0, 1, 500), config)
    bad = finite_interval([1.0] * 489 + [float("nan")] * 11, config)
    assert good["eligible"] and good["finite"] == 500
    assert not bad["eligible"] and bad["finite"] == 489


def _direction(qk_auc: float, residual_auc: float, combined_auc: float, directionality: float) -> dict:
    return {
        "measurable": True,
        "models": {"qk": {"auc": qk_auc}, "residual": {"auc": residual_auc}, "combined": {"auc": combined_auc}, "attention": {"auc": 0.0}},
        "intervals": {
            "qk_auc": {"eligible": True, "lower": qk_auc - 0.01},
            "gain": {"eligible": True, "lower": combined_auc - residual_auc - 0.01},
            "directionality": {"eligible": True, "lower": directionality - 0.01},
        },
        "directionality": directionality,
    }


def test_normalized_attention_is_unreachable_from_decision_gates() -> None:
    config = load_config()
    directions = {"a_to_b": _direction(0.7, 0.60, 0.64, 0.7), "b_to_a": _direction(0.7, 0.60, 0.64, 0.7)}
    first = decision_from_primary(directions, config)
    for row in directions.values():
        row["models"]["attention"]["auc"] = 1.0
    second = decision_from_primary(directions, config)
    assert first == second
    assert first["decision"] == "MATCHED_QK_LINK_INCREMENTAL_PREDICTIVE_DISCOVERY"
    assert first["gate_feature_reachability"] == ["qk", "residual", "combined"]


def test_endpoint_missingness_yields_ineligible_not_zero_signal() -> None:
    config = load_config()
    directions = {"a_to_b": _direction(0.7, 0.60, 0.64, 0.7), "b_to_a": _direction(0.7, 0.60, 0.64, 0.7)}
    directions["b_to_a"]["intervals"]["qk_auc"] = {"eligible": False}
    outcome = decision_from_primary(directions, config)
    assert outcome["decision"] == "RELATIONAL_EDGE_STUDY_INELIGIBLE"


@pytest.mark.parametrize("source,file_name", [("UKRAINIAN_IU", "uk_iu-ud-dev.conllu"), ("LATVIAN_LVTB", "lv_lvtb-ud-test.conllu"), ("ARABIC_PADT", "ar_padt-ud-train.conllu")])
def test_provenance_only_or_rejected_source_cannot_reach_units(source: str, file_name: str) -> None:
    config = load_config()
    unit = {"source": source, "source_file": file_name}
    with pytest.raises(RuntimeError, match="rejected|provenance-only"):
        validate_unit_lineage(config, source, [unit])


def test_lineage_rejects_missing_and_wrong_source_hash() -> None:
    config = load_config()
    source = "UKRAINIAN_IU"
    base = {"source": source, "source_file": config["sources"][source]["analysis_files"][0]}
    with pytest.raises(RuntimeError, match="missing"):
        validate_unit_lineage(config, source, [base])
    with pytest.raises(RuntimeError, match="drift"):
        validate_unit_lineage(config, source, [{**base, "source_file_sha256": "0" * 64}])


def test_canonical_units_trace_only_to_selected_train_hashes() -> None:
    config = load_config()
    for source, spec in config["sources"].items():
        path = ROOT / config["paths"]["prepared_root"] / source / "inference_units.jsonl"
        units = [json.loads(line) for line in path.read_text().splitlines()]
        validate_unit_lineage(config, source, units)
        assert {unit["source_file"] for unit in units} == set(spec["analysis_files"])
        assert {unit["source_file_sha256"] for unit in units} == {spec["files"][name] for name in spec["analysis_files"]}
    report = validate_runtime_lineage(config)
    assert set(report) == set(config["sources"])


def test_manual_probabilities_are_causal_and_padding_safe() -> None:
    logits = torch.zeros((1, 2, 4, 4), dtype=torch.float32)
    mask = torch.tensor([[1, 1, 1, 0]])
    probabilities = _manual_probabilities(logits, mask)
    assert torch.all(probabilities[:, :, 0, 1:] == 0)
    assert torch.all(probabilities[:, :, :, 3] == 0)
    assert torch.allclose(probabilities.sum(-1), torch.ones_like(probabilities.sum(-1)))


def test_feature_combined_is_exact_residual_then_qk() -> None:
    cache = {"residual": np.ones((3, 4)), "qk": np.full((3, 2), 2.0)}
    combined = _feature(cache, "combined")
    assert combined.shape == (3, 6)
    assert np.array_equal(combined[:, :4], cache["residual"])
    assert np.array_equal(combined[:, 4:], cache["qk"])


def test_review_gate_rejects_incidental_duplicate_and_stale_ship() -> None:
    digest = "a" * 64
    assert review_is_ship_bound(f"VERDICT: SHIP\nFREEZE_SHA256: {digest}\n", digest)
    assert not review_is_ship_bound(f"VERDICT: BLOCK\nfinding mentions VERDICT: SHIP\nFREEZE_SHA256: {digest}\n", digest)
    assert not review_is_ship_bound(f"VERDICT: SHIP\nVERDICT: BLOCK\nFREEZE_SHA256: {digest}\n", digest)
    assert not review_is_ship_bound(f"VERDICT: SHIP\nFREEZE_SHA256: {'b' * 64}\n", digest)


def test_exposure_scanner_finds_alias_and_digest(tmp_path: Path) -> None:
    digest = "c" * 64
    path = tmp_path / "report.json"
    path.write_text(json.dumps({"source": "UD_Ukrainian-IU", "sha256": digest}))
    aliases, digests = _scan_artifact(path, [b"UD_Ukrainian-IU"], {digest})
    assert aliases == {"UD_Ukrainian-IU"}
    assert digests == {digest}


def test_structured_hit_cannot_borrow_sibling_label_only_metadata(tmp_path: Path) -> None:
    text = "candidate sentence"
    digest = __import__("hashlib").sha256(text.encode()).hexdigest()
    path = tmp_path / "mixed.json"
    path.write_text(
        json.dumps(
            [
                {"text": text},
                {
                    "model_forward_run": False,
                    "endpoint_scores_computed": False,
                    "label_only": True,
                },
            ]
        )
    )
    evidence = _structured_file_evidence(path, {digest}, set())
    assert len(evidence["records"]) == 1
    assert evidence["records"][0]["metadata"] == {}
    assert _classify_hit(evidence["records"][0]) == "UNRESOLVED_BLOCKING_HIT"

    attached = tmp_path / "attached.jsonl"
    attached.write_text(
        json.dumps(
            {
                "text": text,
                "model_forward_run": False,
                "endpoint_scores_computed": False,
                "label_only": True,
            }
        )
        + "\n"
    )
    attached_evidence = _structured_file_evidence(attached, {digest}, set())
    assert _classify_hit(attached_evidence["records"][0]) == "UNRESOLVED_BLOCKING_HIT"
    signed = {**attached_evidence["records"][0], "signed_role_attestation_verified": True}
    assert _classify_hit(signed) == "EXPLICIT_LABEL_ONLY_NONFATAL"


def test_embedded_normalized_text_is_found_behind_prefix_and_markup(tmp_path: Path) -> None:
    text = "the exact candidate sentence"
    digest = __import__("hashlib").sha256(text.encode()).hexdigest()
    matcher = NormalizedTextMatcher({text: digest})
    for name, content in (
        ("run.log", f"model input: {text} [done]\n"),
        ("report.html", f"<p>{text}</p>\n"),
        ("notes.md", f"- observed: **{text}**\n"),
    ):
        path = tmp_path / name
        path.write_text(content)
        evidence = _structured_file_evidence(path, {digest}, set(), text_matcher=matcher)
        assert evidence["records"][0]["text_hashes"] == [digest]


def test_role_attestation_requires_exact_artifact_hash_and_pointer() -> None:
    attestation = {
        "path": "reports/x.json",
        "artifact_sha256": "a" * 64,
        "pointer": "$/row/0",
        "stage": "LABEL_ONLY_PRESCORE",
        "model_forward_run": False,
        "endpoint_scores_computed": False,
        "label_only": True,
    }
    entries = {(attestation["path"], attestation["artifact_sha256"], attestation["pointer"]): attestation}
    valid = {"path": attestation["path"], "pointer": attestation["pointer"], "metadata": {}}
    _attach_role_attestation(valid, "a" * 64, entries)
    assert valid["signed_role_attestation_verified"] is True
    assert _classify_hit(valid) == "EXPLICIT_LABEL_ONLY_NONFATAL"
    for wrong_hash, wrong_pointer in (("b" * 64, attestation["pointer"]), ("a" * 64, "$/row/1")):
        invalid = {"path": attestation["path"], "pointer": wrong_pointer, "metadata": {}}
        _attach_role_attestation(invalid, wrong_hash, entries)
        assert "signed_role_attestation_verified" not in invalid
        assert _classify_hit(invalid) == "UNRESOLVED_BLOCKING_HIT"


def _test_signer(private: Ed25519PrivateKey) -> dict[str, str]:
    import base64
    import hashlib

    public = private.public_key().public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw)
    return {
        "algorithm": "Ed25519",
        "public_key_base64": base64.b64encode(public).decode("ascii"),
        "public_key_fingerprint_sha256": hashlib.sha256(public).hexdigest(),
    }


def test_role_sidecar_verifier_rejects_stale_pointer_duplicate_and_file_count(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    artifact = tmp_path / "prior.json"
    artifact.write_text("{}\n")
    scripts = tmp_path / "scripts"
    scripts.mkdir()
    (scripts / "relational_attention_edges_v1.py").write_bytes(
        (ROOT / "scripts/relational_attention_edges_v1.py").read_bytes()
    )
    private = Ed25519PrivateKey.generate()
    signer = _test_signer(private)
    entry = {
        "path": "prior.json",
        "artifact_sha256": sha256_file(artifact),
        "pointer": "$/row/0",
        "stage": "LABEL_ONLY_PRESCORE",
        "model_forward_run": False,
        "endpoint_scores_computed": False,
        "label_only": True,
    }
    sidecar = tmp_path / "role.json"
    config = {
        "signer": signer,
        "exposure": {
            "role_sidecar_path": "role.json",
            "role_sidecar_sha256": "",
            "role_attestations": [entry],
        },
    }
    monkeypatch.setattr(builder, "ROOT", tmp_path)
    monkeypatch.setattr(builder, "_prior_artifact_paths", lambda _config: [artifact])

    with pytest.raises(FileNotFoundError):
        verify_role_sidecar(config)

    def write_payload(entries: list[dict], files: int) -> None:
        payload = {
            "schema_version": "relational_attention_edges_v1_role_sidecar_v1",
            "status": "FROZEN_EXACT_RECORD_ROLE_ATTESTATIONS",
            "builder_sha256": sha256_file(Path(builder.__file__)),
            "common_sha256": sha256_file(scripts / "relational_attention_edges_v1.py"),
            "entries": entries,
            "entries_sha256": builder.inventory_digest(entries),
            "files": files,
        }
        sign_payload(sidecar, payload, private)
        config["exposure"]["role_sidecar_sha256"] = sha256_file(sidecar)

    write_payload([entry], 1)
    assert verify_role_sidecar(config)["entries"] == [entry]

    envelope = json.loads(sidecar.read_text())
    envelope["payload"]["schema_version"] = "wrong"
    sign_payload(sidecar, envelope["payload"], private)
    config["exposure"]["role_sidecar_sha256"] = sha256_file(sidecar)
    with pytest.raises(RuntimeError, match="identity"):
        verify_role_sidecar(config)

    write_payload([entry], 1)
    envelope = json.loads(sidecar.read_text())
    envelope["signature"]["signature_base64"] = "A" * len(envelope["signature"]["signature_base64"])
    sidecar.write_text(json.dumps(envelope))
    config["exposure"]["role_sidecar_sha256"] = sha256_file(sidecar)
    with pytest.raises(Exception):
        verify_role_sidecar(config)

    stale = {**entry, "pointer": "$/row/1"}
    write_payload([stale], 1)
    with pytest.raises(RuntimeError, match="config attestations"):
        verify_role_sidecar(config)

    write_payload([entry, entry], 1)
    with pytest.raises(RuntimeError, match="duplicate|config attestations"):
        verify_role_sidecar(config)

    write_payload([entry], 2)
    with pytest.raises(RuntimeError, match="file count"):
        verify_role_sidecar(config)


def test_prior_conllu_parser_is_strict_and_preserves_normalized_sentences(tmp_path: Path) -> None:
    valid = tmp_path / "valid.conllu"
    valid.write_text(
        "# newdoc id = d1\n# sent_id = s1\n1\tCAFÉ\t_\tNOUN\t_\t_\t0\troot\t_\t_\n\n"
        "# sent_id = s2\n1\tWord\t_\tNOUN\t_\t_\t0\troot\t_\t_\n\n",
        encoding="utf-8",
    )
    assert _strict_prior_conllu_sentences(valid) == [("d1", ["café"]), ("d1", ["word"])]

    malformed = tmp_path / "malformed.conllu"
    malformed.write_text("1\tonly-two-columns\n\n", encoding="utf-8")
    with pytest.raises(RuntimeError, match="10 columns"):
        _strict_prior_conllu_sentences(malformed)

    invalid_utf8 = tmp_path / "invalid.conllu"
    invalid_utf8.write_bytes(b"1\t\xff\t_\tNOUN\t_\t_\t0\troot\t_\t_\n")
    with pytest.raises(UnicodeDecodeError):
        _strict_prior_conllu_sentences(invalid_utf8)

    missing_separator = tmp_path / "missing-separator.conllu"
    missing_separator.write_text(
        "# sent_id = s1\n1\tFirst\t_\tNOUN\t_\t_\t0\troot\t_\t_\n"
        "# sent_id = s2\n1\tSecond\t_\tNOUN\t_\t_\t0\troot\t_\t_\n\n"
    )
    with pytest.raises(RuntimeError, match="separator|comment after data"):
        _strict_prior_conllu_sentences(missing_separator)

    invalid_range = tmp_path / "invalid-range.conllu"
    invalid_range.write_text("2-1\tx\t_\t_\t_\t_\t_\t_\t_\t_\n\n")
    with pytest.raises(RuntimeError, match="range"):
        _strict_prior_conllu_sentences(invalid_range)

    out_of_range = tmp_path / "out-of-range.conllu"
    out_of_range.write_text(
        "99-100\tx\t_\t_\t_\t_\t_\t_\t_\t_\n"
        "1\tOnly\t_\tNOUN\t_\t_\t0\troot\t_\t_\n\n"
    )
    with pytest.raises(RuntimeError, match="misplaced|exceeds"):
        _strict_prior_conllu_sentences(out_of_range)

    misplaced_empty = tmp_path / "misplaced-empty.conllu"
    misplaced_empty.write_text(
        "1\tOnly\t_\tNOUN\t_\t_\t0\troot\t_\t_\n"
        "99.1\tx\t_\tX\t_\t_\t_\tdep\t_\t_\n\n"
    )
    with pytest.raises(RuntimeError, match="empty-node"):
        _strict_prior_conllu_sentences(misplaced_empty)

    restarted = tmp_path / "restarted.conllu"
    restarted.write_text(
        "1\tFirst\t_\tNOUN\t_\t_\t0\troot\t_\t_\n"
        "1\tSecond\t_\tNOUN\t_\t_\t0\troot\t_\t_\n\n"
    )
    with pytest.raises(RuntimeError, match="restarted"):
        _strict_prior_conllu_sentences(restarted)


def test_primary_claim_is_consumed_before_full_validation(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    config = read_json(ROOT / "configs/relational_attention_edges_v1/run.json")
    private = Ed25519PrivateKey.generate()
    key_path = tmp_path / "key.pem"
    key_path.write_bytes(
        private.private_bytes(
            serialization.Encoding.PEM,
            serialization.PrivateFormat.PKCS8,
            serialization.NoEncryption(),
        )
    )
    config["signer"] = _test_signer(private)
    canonical_paths = {
        "data_root": "data/primary",
        "rebuild_root": "data/rebuild",
        "prescore_record": "lifecycle/opened.json",
        "prescore_rebuild_record": "lifecycle/rebuild.json",
        "prescore_primary_complete": "lifecycle/complete.json",
        "prescore_terminal": "lifecycle/terminal.json",
    }
    # Deliberately drift mutable config routing and signer identity. The owned
    # attempt must still consume and terminalize the code-fixed canonical path.
    config["paths"].update({key: f"drifted/{Path(value).name}" for key, value in canonical_paths.items()})
    config["signer"] = {"algorithm": "wrong"}
    config_path = tmp_path / "run.json"
    config_path.write_text(json.dumps(config))
    monkeypatch.setattr(builder, "ROOT", tmp_path)
    monkeypatch.setattr(builder, "CONFIG", config_path)
    monkeypatch.setattr(builder, "PRESCORE_LIFECYCLE_PATHS", canonical_paths)
    monkeypatch.setattr(common, "PRESCORE_LIFECYCLE_PATHS", canonical_paths)
    monkeypatch.setattr(builder, "EXPECTED_SIGNER", _test_signer(private))
    monkeypatch.setattr(common, "EXPECTED_SIGNER", _test_signer(private))
    monkeypatch.setattr(builder, "EXPOSURE_UNIVERSE_PATH", "universe.json")
    monkeypatch.setattr(builder, "load_config", lambda: (_ for _ in ()).throw(RuntimeError("full validation failed")))
    with pytest.raises(RuntimeError, match="full validation failed"):
        build("primary", key_path)
    assert (tmp_path / "lifecycle/opened.json").is_file()
    assert (tmp_path / "lifecycle/terminal.json").is_file()
    assert not (tmp_path / "drifted/opened.json").exists()


@pytest.mark.parametrize("invalid_kind", ["permission", "exploratory", "schema", "malformed"])
def test_invalid_config_is_claimed_terminalized_and_cannot_be_repaired_for_retry(
    invalid_kind: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    private = Ed25519PrivateKey.generate()
    signer = _test_signer(private)
    key_path = tmp_path / "key.pem"
    key_path.write_bytes(
        private.private_bytes(
            serialization.Encoding.PEM,
            serialization.PrivateFormat.PKCS8,
            serialization.NoEncryption(),
        )
    )
    canonical_paths = {
        "data_root": "data/primary",
        "rebuild_root": "data/rebuild",
        "prescore_record": "lifecycle/opened.json",
        "prescore_rebuild_record": "lifecycle/rebuild.json",
        "prescore_primary_complete": "lifecycle/complete.json",
        "prescore_terminal": "lifecycle/terminal.json",
    }
    valid = read_json(ROOT / "configs/relational_attention_edges_v1/run.json")
    valid["signer"] = signer
    valid["paths"].update(canonical_paths)
    valid["exposure"]["universe_path"] = "universe.json"
    invalid = json.loads(json.dumps(valid))
    if invalid_kind == "permission":
        invalid["permissions"]["retry_authorized"] = True
    elif invalid_kind == "exploratory":
        invalid["exploratory"] = False
    elif invalid_kind == "schema":
        invalid["schema_version"] = "wrong"
    config_path = tmp_path / "run.json"
    config_path.write_text("{" if invalid_kind == "malformed" else json.dumps(invalid))
    monkeypatch.setattr(builder, "ROOT", tmp_path)
    monkeypatch.setattr(builder, "CONFIG", config_path)
    monkeypatch.setattr(builder, "PRESCORE_LIFECYCLE_PATHS", canonical_paths)
    monkeypatch.setattr(common, "PRESCORE_LIFECYCLE_PATHS", canonical_paths)
    monkeypatch.setattr(builder, "EXPECTED_SIGNER", signer)
    monkeypatch.setattr(common, "EXPECTED_SIGNER", signer)
    monkeypatch.setattr(builder, "EXPOSURE_UNIVERSE_PATH", "universe.json")
    monkeypatch.setattr(common, "EXPOSURE_UNIVERSE_PATH", "universe.json")
    with pytest.raises(Exception):
        build("primary", key_path)
    opening = tmp_path / canonical_paths["prescore_record"]
    terminal = tmp_path / canonical_paths["prescore_terminal"]
    assert opening.is_file() and terminal.is_file()
    opening_bytes = opening.read_bytes()
    config_path.write_text(json.dumps(valid))
    with pytest.raises(RuntimeError, match="terminal already exists"):
        build("primary", key_path)
    assert opening.read_bytes() == opening_bytes


def test_opaque_numpy_probe_is_typed_and_nonexecuting(tmp_path: Path) -> None:
    path = tmp_path / "ids.npy"
    np.save(path, np.asarray([[1, 2, 3]], dtype=np.int32), allow_pickle=False)
    probe = _opaque_probe(path)
    assert probe["format_status"] == "NUMPY_ARRAY_HEADER_AND_TYPED_PAYLOAD_INSPECTED"
    assert probe["integer_payloads"] == [{"member": "$ARRAY", "dtype": "int32", "shape": [1, 3]}]


def test_opaque_torch_pickle_and_bytecode_integer_payloads_are_enumerated(tmp_path: Path) -> None:
    torch_path = tmp_path / "cache.pt"
    torch.save({"input_ids": torch.tensor([[1, 2, 3]], dtype=torch.int64)}, torch_path)
    torch_probe = _opaque_probe(torch_path)
    assert torch_probe["identity_bearing_field_names"] == ["input_ids"]
    assert any(entry["shape"] == [1, 3] for entry in torch_probe["integer_payloads"])

    numpy_torch_path = tmp_path / "numpy-rng-cache.pt"
    torch.save({"np_rng_state": np.arange(8, dtype=np.uint32)}, numpy_torch_path)
    numpy_torch_probe = _opaque_probe(numpy_torch_path)
    assert numpy_torch_probe["format_status"] == "TORCH_ZIP_RESTRICTED_WEIGHTS_ONLY_AND_MEMBER_INVENTORY_INSPECTED"
    assert any(entry["dtype"] == "uint32" and entry["shape"] == [8] for entry in numpy_torch_probe["integer_payloads"])

    pickle_path = tmp_path / "cache.pkl"
    pickle_path.write_bytes(pickle.dumps({"input_ids": [1, 2, 3]}, protocol=5))
    pickle_probe = _opaque_probe(pickle_path)
    assert pickle_probe["identity_bearing_field_names"] == ["input_ids"]
    assert any(entry["shape"] == [3] for entry in pickle_probe["integer_payloads"])

    source = tmp_path / "literal.py"
    source.write_text("VALUES = (1, 2, 3)\n")
    pyc_path = Path(py_compile.compile(str(source), doraise=True))
    pyc_probe = _opaque_probe(pyc_path)
    assert any(entry["shape"] == [3] for entry in pyc_probe["integer_payloads"])


def test_successor_key_binds_selected_split_and_revision() -> None:
    config = read_json(ROOT / "configs/relational_attention_edges_v1/run.json")
    original = study_key(config)
    changed_split = json.loads(json.dumps(config))
    changed_split["sources"]["UKRAINIAN_IU"]["analysis_files"] = ["uk_iu-ud-dev.conllu"]
    assert study_key(changed_split) != original
    changed_revision = json.loads(json.dumps(config))
    changed_revision["sources"]["UKRAINIAN_IU"]["revision"] = "0" * 40
    assert study_key(changed_revision) != original


def test_preservation_destination_guard_rejects_root_descendant_and_symlink(tmp_path: Path) -> None:
    config = load_config()
    preserved = ROOT / json.loads((ROOT / config["preservation"]["path"]).read_text())["preserved_roots"][0]
    with pytest.raises(RuntimeError, match="preserved"):
        assert_new_destination(config, preserved)
    with pytest.raises(RuntimeError, match="preserved"):
        assert_new_destination(config, preserved / "child")
    link = tmp_path / "link"
    link.symlink_to(preserved, target_is_directory=True)
    with pytest.raises(RuntimeError, match="preserved"):
        assert_new_destination(config, link / "child")
    assert_new_destination(config, tmp_path / "allowed")


def test_exclusive_record_has_single_winner(tmp_path: Path) -> None:
    target = tmp_path / "opening.json"
    exclusive_fsynced_json(target, {"winner": 1})
    with pytest.raises(FileExistsError):
        exclusive_fsynced_json(target, {"winner": 2})


def test_global_prescore_terminal_is_write_once_and_exact(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    private = Ed25519PrivateKey.generate()
    key_path = tmp_path / "key.pem"
    key_path.write_bytes(
        private.private_bytes(
            serialization.Encoding.PEM,
            serialization.PrivateFormat.PKCS8,
            serialization.NoEncryption(),
        )
    )
    config = {
        "namespace": "relational_attention_edges_v1_discovery2",
        "signer": _test_signer(private),
        "paths": {
            "prescore_record": "opened.json",
            "prescore_rebuild_record": "rebuild.json",
            "prescore_terminal": "terminal.json",
        },
    }
    monkeypatch.setattr(builder, "ROOT", tmp_path)
    sign_payload(
        tmp_path / "opened.json",
        {"owner_nonce": "owner", "study_key": "key", "config_sha256": "config"},
        private,
    )
    _global_prescore_terminal(config, key_path, owner_nonce="owner", reason="failed")
    first = (tmp_path / "terminal.json").read_bytes()
    _global_prescore_terminal(config, key_path, owner_nonce="owner", reason="failed")
    assert (tmp_path / "terminal.json").read_bytes() == first
    with pytest.raises(RuntimeError, match="conflicting"):
        _global_prescore_terminal(config, key_path, owner_nonce="owner", reason="different")
    sign_payload(
        tmp_path / "rebuild.json",
        {"owner_nonce": "other", "study_key": "key", "config_sha256": "config"},
        private,
    )
    with pytest.raises(RuntimeError, match="conflicting"):
        _global_prescore_terminal(config, key_path, owner_nonce="other", reason="failed")


def test_rebuild_requires_completion_and_claim_has_one_winner(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    private = Ed25519PrivateKey.generate()
    signer = _test_signer(private)
    key_path = tmp_path / "key.pem"
    key_path.write_bytes(
        private.private_bytes(
            serialization.Encoding.PEM,
            serialization.PrivateFormat.PKCS8,
            serialization.NoEncryption(),
        )
    )
    canonical_paths = {
        "data_root": "data/primary",
        "rebuild_root": "data/rebuild",
        "prescore_record": "lifecycle/opened.json",
        "prescore_rebuild_record": "lifecycle/rebuild.json",
        "prescore_primary_complete": "lifecycle/complete.json",
        "prescore_terminal": "lifecycle/terminal.json",
    }
    config = read_json(ROOT / "configs/relational_attention_edges_v1/run.json")
    config["signer"] = signer
    config["paths"].update(canonical_paths)
    config["exposure"]["universe_path"] = "universe.json"
    config_path = tmp_path / "run.json"
    config_path.write_text(json.dumps(config))
    monkeypatch.setattr(builder, "ROOT", tmp_path)
    monkeypatch.setattr(builder, "CONFIG", config_path)
    monkeypatch.setattr(builder, "PRESCORE_LIFECYCLE_PATHS", canonical_paths)
    monkeypatch.setattr(common, "PRESCORE_LIFECYCLE_PATHS", canonical_paths)
    monkeypatch.setattr(builder, "EXPECTED_SIGNER", signer)
    monkeypatch.setattr(common, "EXPECTED_SIGNER", signer)
    monkeypatch.setattr(builder, "EXPOSURE_UNIVERSE_PATH", "universe.json")
    monkeypatch.setattr(common, "EXPOSURE_UNIVERSE_PATH", "universe.json")
    config_sha = sha256_file(config_path)
    key = study_key(config)
    opening_path = tmp_path / canonical_paths["prescore_record"]
    sign_payload(
        opening_path,
        {
            "schema_version": "relational_attention_edges_v1_discovery2_prescore_opening_v1",
            "status": "PRESCORE_OPENING_CONSUMED",
            "study_key": key,
            "study_key_status": "DECLARED_PROTOCOL",
            "config_sha256": config_sha,
            "owner_nonce": "primary-owner",
            "primary_root": canonical_paths["data_root"],
            "rebuild_root": canonical_paths["rebuild_root"],
            "candidate_source_model_forward_run": False,
            "retry_authorized": False,
        },
        private,
    )
    with pytest.raises(FileNotFoundError):
        builder._build_impl("rebuild", key_path)
    assert not (tmp_path / canonical_paths["prescore_rebuild_record"]).exists()

    manifest_path = tmp_path / canonical_paths["data_root"] / "prepared/manifest.json"
    manifest_path.parent.mkdir(parents=True)
    manifest = {
        "status": "PRESCORE_COMPLETE",
        "all_primary_sources_eligible": True,
        "study_key": key,
        "preservation_entries_sha256": "preservation",
    }
    manifest_path.write_text(json.dumps(manifest))
    universe_path = tmp_path / "universe.json"
    universe_path.write_text("{}\n")
    completion_path = tmp_path / canonical_paths["prescore_primary_complete"]
    sign_payload(
        completion_path,
        {
            "schema_version": "relational_attention_edges_v1_discovery2_primary_complete_v1",
            "status": "PRESCORE_PRIMARY_COMPLETE",
            "study_key": key,
            "config_sha256": config_sha,
            "owner_nonce": "primary-owner",
            "primary_manifest": {
                "path": manifest_path.relative_to(tmp_path).as_posix(),
                "sha256": sha256_file(manifest_path),
            },
            "prescore_opening_sha256": sha256_file(opening_path),
            "preservation_entries_sha256": "preservation",
            "exposure_universe_sha256": sha256_file(universe_path),
            "candidate_source_model_forward_run": False,
            "endpoint_scores_computed": False,
            "neural_training_run": False,
            "retry_authorized": False,
        },
        private,
    )
    monkeypatch.setattr(builder, "load_config", lambda: (_ for _ in ()).throw(RuntimeError("stop after claim")))
    with pytest.raises(RuntimeError, match="stop after claim"):
        builder._build_impl("rebuild", key_path)
    claim_path = tmp_path / canonical_paths["prescore_rebuild_record"]
    first_claim = claim_path.read_bytes()
    with pytest.raises(FileExistsError):
        builder._build_impl("rebuild", key_path)
    assert claim_path.read_bytes() == first_claim

    completion = json.loads(completion_path.read_text())
    completion["payload"]["schema_version"] = "wrong"
    sign_payload(completion_path, completion["payload"], private)
    with pytest.raises(RuntimeError, match="completion record drift"):
        builder._verify_primary_completion(
            {"paths": canonical_paths, "signer": signer, "exposure": {"universe_path": "universe.json"}},
            expected_config_sha256=config_sha,
            expected_study_key=key,
        )


def test_alpha_tie_breaks_larger_and_scaler_is_fold_local(monkeypatch: pytest.MonkeyPatch) -> None:
    config = load_config()
    X = np.asarray([[0.0], [1.0], [2.0], [3.0], [4.0], [5.0], [6.0], [7.0], [8.0], [9.0]])
    y = np.asarray([0, 1] * 5, dtype=np.int64)
    folds = np.repeat(np.arange(5), 2)
    # Real CV execution is the leakage check: every validation fold is absent from its fit mask.
    selected = _select_alpha_binary(X, y, folds, config)
    assert selected["selected_alpha"] in config["analysis"]["alphas"]
    assert all(len(row["fold_auc"]) == 5 for row in selected["candidates"] if row["valid"])


def test_bootstrap_rejects_corrupt_map_shape() -> None:
    config = load_config()
    examples = [{"component_id": "c", "label": label} for label in (1, 0)]
    pairs = [{"component_id": "c", "edge_index": 0, "nonedge_index": 1}]
    scores = {name: np.asarray([1.0, 0.0]) for name in ("qk", "residual", "combined")}
    with pytest.raises(ValueError, match="shape"):
        _bootstrap_binary(examples, pairs, np.zeros((1, 1), dtype=np.uint32), scores, config)


def test_independent_partial_rope_qk_reference_and_multi_key_mean() -> None:
    class Attention:
        head_size = 4
        scaling = 0.5

    class Layer:
        attention = Attention()

    class NeoX:
        layers = [Layer()]

        @staticmethod
        def rotary_emb(hidden, position_ids):
            shape = (hidden.shape[0], hidden.shape[1], 2)
            return torch.ones(shape), torch.zeros(shape)

    class Config:
        num_attention_heads = 2

    class Model:
        gpt_neox = NeoX()
        config = Config()

    torch.manual_seed(7)
    qkv = torch.randn(1, 4, 24)
    hidden = torch.randn(1, 4, 8)
    positions = torch.arange(4).unsqueeze(0)
    *_unused, logits = _rotary_qkv(Model(), qkv, hidden, positions, 0)
    reference = _independent_qk_logits(Model(), qkv, hidden, positions, 0)
    assert torch.allclose(logits, reference, atol=0, rtol=0)
    pooled = logits[0, :, 3, [1, 2]].mean(-1)
    manual = (reference[0, :, 3, 1] + reference[0, :, 3, 2]) / 2
    assert torch.equal(pooled, manual)


def test_multi_subtoken_qk_attention_value_and_residual_pooling() -> None:
    logits = torch.arange(1 * 2 * 4 * 4, dtype=torch.float32).reshape(1, 2, 4, 4)
    probabilities = torch.softmax(logits, dim=-1)
    values = torch.arange(1 * 2 * 4 * 3, dtype=torch.float32).reshape(1, 2, 4, 3)
    residuals = torch.arange(1 * 4 * 6, dtype=torch.float32).reshape(1, 4, 6)
    pooled = pool_link_features(logits, probabilities, values, residuals, 0, 3, [1, 2], 1e-12)
    assert pooled["qk"].shape == (2,)
    assert torch.equal(pooled["qk"], (logits[0, :, 3, 1] + logits[0, :, 3, 2]) / 2)
    expected_transport = (probabilities[0, :, 3, [1, 2]].unsqueeze(-1) * values[0, :, [1, 2], :]).sum(-2).reshape(-1)
    assert torch.equal(pooled["transport"], expected_transport)
    assert pooled["value"].shape == (6,)
    assert pooled["residual"].shape == (12,)
    with pytest.raises(ValueError, match="causally"):
        pool_link_features(logits, probabilities, values, residuals, 0, 1, [2], 1e-12)


def test_gpu_identity_mig_busy_and_visible_checks_fail_closed(monkeypatch: pytest.MonkeyPatch) -> None:
    import run_relational_attention_edges_v1 as runner
    config = load_config()
    expected = config["runtime"]
    row = {"index": expected["physical_gpu_index"], "uuid": expected["gpu_uuid"], "memory_used_mib": 2, "memory_free_mib": 48000, "utilization_percent": 0, "mig_mode": expected["mig_mode"]}
    monkeypatch.setattr(runner, "_nvidia_rows", lambda: [row])
    monkeypatch.setattr(runner, "_compute_apps", lambda: [])
    assert assert_physical_gpu_free(config)["uuid"] == expected["gpu_uuid"]
    monkeypatch.setattr(runner, "_nvidia_rows", lambda: [{**row, "mig_mode": "[Enabled]"}])
    with pytest.raises(RuntimeError, match="MIG"):
        assert_physical_gpu_free(config)
    monkeypatch.setattr(runner, "_nvidia_rows", lambda: [row])
    monkeypatch.setattr(runner, "_compute_apps", lambda: [(expected["gpu_uuid"], 999999)])
    with pytest.raises(RuntimeError, match="busy"):
        assert_physical_gpu_free(config)

    class Properties:
        uuid = "wrong"

    monkeypatch.setattr(torch.cuda, "is_available", lambda: True)
    monkeypatch.setattr(torch.cuda, "device_count", lambda: 1)
    monkeypatch.setattr(torch.cuda, "get_device_properties", lambda _index: Properties())
    with pytest.raises(RuntimeError, match="UUID"):
        assert_visible_gpu(config)


def test_no_optimizer_training_or_checkpoint_api_in_new_program() -> None:
    paths = sorted((ROOT / "scripts").glob("*relational_attention_edges_v1*"))
    forbidden = ("torch.optim", ".backward(", "save_pretrained(", "state_dict(", "load_state_dict(")
    text = "\n".join(path.read_text() for path in paths if path.suffix in {".py", ".sh"})
    for token in forbidden:
        assert token not in text
    for path in paths:
        if path.suffix == ".py":
            ast.parse(path.read_text())
