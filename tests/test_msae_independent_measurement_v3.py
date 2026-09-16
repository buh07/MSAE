from __future__ import annotations
import copy
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import stat
import subprocess
import sys
import tempfile

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import msae_independent_measurement_v3 as m

RUNNER_SPEC = importlib.util.spec_from_file_location("runner_v3", ROOT / "scripts/run_msae_independent_calibration_v3.py")
assert RUNNER_SPEC and RUNNER_SPEC.loader
runner = importlib.util.module_from_spec(RUNNER_SPEC)
RUNNER_SPEC.loader.exec_module(runner)


def document(name: str, *sentences: tuple[str, ...]) -> m.TextDocument:
    return m.TextDocument(name, name, 0, tuple(sentences))


def unit_weights(*docs: m.TextDocument):
    return {g: m.decimal.Decimal(1) for d in docs for g in d.fivegrams}


def test_typed_tuple_golden_vectors_and_order():
    assert m.tuple_digest(m.PROTOCOL, "C1", "amalgum:academic", "doc-1", "sent-1", 7, "row-1") == "702c0042f05b90c085930fa69cfebba10d72b5d66f34de8992f97a9382a9be8a"
    assert m.tuple_digest(m.PROTOCOL, "20260820", "calibration", "absolute_bucket", "gum", 0, 0) == "ca3ff78f94a1375a397676ea7042323554e88b5688f446bd18e1ff84a63bc9a7"
    assert m.typed_tuple(("a", 1)) < m.typed_tuple(("b", 1))


@pytest.mark.parametrize("parts", [(True,), (-1,), (2**64,), (None,), ("e\u0301",)])
def test_typed_tuple_rejects_untyped_or_non_nfc(parts):
    with pytest.raises(ValueError):
        m.typed_tuple(parts)


def test_sha256_validation_is_ascii_lowercase_only():
    assert m.validate_sha256("a" * 64) == "a" * 64
    for invalid in ("A" * 64, "١" * 64, "０" * 64, "a" * 63, "g" * 64):
        with pytest.raises(ValueError):
            m.validate_sha256(invalid)


@pytest.mark.parametrize("raw,events", [
    ("(place-1)", [("singleton", "place", 1)]),
    ("(substance-14(place-1)", [("open", "substance", 14), ("singleton", "place", 1)]),
    ("place-1)person-5)abstract-6)place-7)(place-9)", [("close", "place", 1), ("close", "person", 5), ("close", "abstract", 6), ("close", "place", 7), ("singleton", "place", 9)]),
    ("(place-7(place-7", [("open", "place", 7), ("open", "place", 7)]),
])
def test_entity_event_grammar(raw, events):
    assert m.parse_entity_events(raw) == events


@pytest.mark.parametrize("raw", ["", "(", "place-0)", "place-1", "(1-thing)", "(place-1)x"])
def test_entity_event_grammar_rejects_malformed(raw):
    with pytest.raises(ValueError):
        m.parse_entity_events(raw)


def test_strict_real_amalgum_entity_parse_includes_cross_sentence_span():
    path = ROOT / "data/msae_independent_measurement_v1/selected_raw/amalgum/voyage/dep/AMALGUM_voyage_phrasebook.conllu"
    docs = m.parse_conllu(path, strict_entities=True)
    assert len(docs) == 1
    spans = docs[0]["spans"]
    assert any(span[2] == "abstract" and span[3] == 51 for span in spans)


def test_strict_conllu_rejects_close_underflow(tmp_path):
    path = tmp_path / "bad.conllu"
    path.write_text("# sent_id = d-1\n# text = A\n1\tA\ta\tNOUN\t_\t_\t0\troot\t_\tEntity=place-1)\n", encoding="utf-8")
    with pytest.raises(ValueError, match="underflow"):
        m.parse_conllu(path)


def test_strict_conllu_rejects_leftover_open(tmp_path):
    path = tmp_path / "bad.conllu"
    path.write_text("# sent_id = d-1\n# text = A\n1\tA\ta\tNOUN\t_\t_\t0\troot\t_\tEntity=\\(place-1\n".replace("\\", ""), encoding="utf-8")
    with pytest.raises(ValueError, match="unclosed"):
        m.parse_conllu(path)


@pytest.mark.parametrize("escaped,expected", [
    (r"\s", "A B"), (r"\n", "A\nB"), (r"\t", "A\tB"),
    (r"\r", "A\rB"), (r"\p", "A|B"), (r"\\", "A\\B"),
    (r"\u0020", "A B"),
])
def test_strict_conllu_spacesafter_complete_escape_grammar(tmp_path, escaped, expected):
    path = tmp_path / "spacing.conllu"
    path.write_text(
        "# sent_id = d-1\n"
        f"1\tA\ta\tNOUN\t_\t_\t0\troot\t_\tSpacesAfter={escaped}\n"
        "2\tB\tb\tNOUN\t_\t_\t1\tdep\t_\tSpaceAfter=No\n",
        encoding="utf-8",
    )
    parsed = m.parse_conllu(path, strict_entities=False)
    rows = [[str(token["id"]), token["form"], token["lemma"], token["upos"], "_",
             token["feats"], str(token["head"]), token["deprel"], "_", token["misc"]]
            for token in parsed[0]["sentences"][0]["tokens"]]
    assert m._reconstruct_text(rows) == expected


@pytest.mark.parametrize("misc", ["SpaceAfter=Yes", r"SpacesAfter=\x", "SpacesAfter=\\", "SpacesAfter=x"])
def test_strict_conllu_rejects_invalid_spacing_grammar(tmp_path, misc):
    path = tmp_path / "bad-spacing.conllu"
    path.write_text(
        "# sent_id = d-1\n"
        f"1\tA\ta\tNOUN\t_\t_\t0\troot\t_\t{misc}\n",
        encoding="utf-8",
    )
    with pytest.raises(ValueError):
        m.parse_conllu(path, strict_entities=False)


def test_json_field_grammar_and_equivalence():
    obj = {"words": ["A", "cat"], "tokens": ["A cat"], "text": "A cat"}
    assert m._json_object_records(obj, "x", 0) == [("base", ("a", "cat"))]
    with pytest.raises(ValueError, match="conflicting"):
        m._json_object_records({"words": ["A", "cat"], "text": "A dog"}, "x", 0)


@pytest.mark.parametrize("value", [[], [""], [1], None, True, {}, [["x"]]])
def test_json_token_array_closed_grammar(value):
    with pytest.raises(ValueError):
        m.token_field(value, "words")


def test_json_text_field_rejects_empty_but_types_punctuation_nontext():
    with pytest.raises(ValueError):
        m.token_field("", "text")
    assert m.token_field("...", "text") == ()


def test_overlap_exact_and_boundary_flattened_block():
    tokens = tuple(f"t{i}" for i in range(100))
    left = document("a", *(tokens[i:i+4] for i in range(0, 100, 4)))
    right = document("b", tokens)
    decision = m.pair_decision(left, right, unit_weights(left, right))
    assert decision["blocking"]
    assert "exact_full_document" in decision["reasons"]


def test_overlap_10_token_low_diversity_exact_sentence_blocks():
    sentence = tuple("a" if i % 2 else "b" for i in range(10))
    left = document("a", sentence, tuple(f"x{i}" for i in range(9)))
    right = document("b", sentence, tuple(f"y{i}" for i in range(9)))
    decision = m.pair_decision(left, right, unit_weights(left, right))
    assert "exact_substantive_sentence" in decision["reasons"]


def test_short_boilerplate_is_diagnostic_not_blocking():
    shared = (("steps",), ("buy",), ("by", "car"), ("yes",))
    left = document("a", *shared, tuple(f"x{i}" for i in range(9)))
    right = document("b", *shared, tuple(f"y{i}" for i in range(9)))
    decision = m.pair_decision(left, right, unit_weights(left, right))
    assert not decision["blocking"]
    assert decision["shared_short_member_count"] == 4


def test_repeated_heading_does_not_manufacture_passage_coverage():
    left = document("a", *(("steps",) for _ in range(20)))
    right = document("b", *(("steps",) for _ in range(30)))
    decision = m.pair_decision(left, right, unit_weights(left, right))
    assert not decision["blocking"]
    assert decision["covered_selected_positions"] == 20


def test_short_threshold_is_inclusive_at_five_members_and_twenty_tokens():
    shared = tuple(tuple(f"x{i}_{j}" for j in range(4)) for i in range(5))
    left = document("a", *shared, ("unique_a",))
    right = document("b", *shared, ("unique_b",))
    decision = m.pair_decision(left, right, unit_weights(left, right))
    assert "cumulative_short_sentences" in decision["reasons"]


def test_document_comparability_49_versus_50():
    common = tuple(f"x{i}" for i in range(49))
    a = document("a", common)
    b = document("b", common[:-1] + ("different",))
    decision = m.pair_decision(a, b, unit_weights(a, b))
    assert decision["selected_tokens"] == 49
    assert "document_plain_jaccard" not in decision["reasons"]
    a50 = document("a50", common + ("tail",))
    b50 = document("b50", common + ("other",))
    decision50 = m.pair_decision(a50, b50, unit_weights(a50, b50))
    assert "document_plain_jaccard" in decision50["reasons"]


def test_weighted_jaccard_golden_decimal():
    g0, g1, g2 = m.typed_tuple(("a",)*5), m.typed_tuple(("b",)*5), m.typed_tuple(("c",)*5)
    with m.decimal.localcontext(m.DECIMAL_CONTEXT):
        w0 = m.decimal.Decimal(4).ln() - m.decimal.Decimal(2).ln() + 1
        w1 = m.decimal.Decimal(4).ln() - m.decimal.Decimal(3).ln() + 1
    value = m.weighted_jaccard(frozenset({g0, g1}), frozenset({g0, g2}), {g0:w0,g1:w1,g2:w1})
    assert format(value, "f") == "0.39665987775634884002293696822641755903154537267338"


@pytest.mark.parametrize("form,expected", [("abc","lower"),("ABC","upper"),("Abc","title"),("aBc","mixed"),("123","nonalpha")])
def test_capitalization_classes(form, expected):
    assert m._capitalization(form) == expected


def test_dependency_and_number_boundaries():
    assert m._head_bin(-5) == "L5p"
    assert m._head_bin(-2) == "L1_2"
    assert m._head_bin(4) == "R3_4"
    assert m._depth(1, {1:0,2:1}) == "0"
    assert m._depth(2, {1:0,2:1}) == "1"
    assert m._number("Case=Nom|Number=Ptan") == "Ptan"
    assert m._number("Case=Nom") is None
    with pytest.raises(ValueError):
        m._number("Number=Unknown")


def test_selector_exact_boundary_and_nonfinite():
    a = np.array([1.0], dtype=np.float32)
    # float32 realization is used on both sides of the exact inequality.
    b = np.nextafter(a, np.array([2.0], dtype=np.float32))
    difference = float(abs(a.astype(np.float64)[0] - b.astype(np.float64)[0]))
    ok, _ = runner.selector_ok(a, b, str(2 * difference), "0")
    assert ok
    bad = np.array([np.inf], dtype=np.float32)
    assert runner.selector_ok(a, bad, "1", "0")[0] is False


def test_save_npy_once_is_create_once_and_byte_exact(tmp_path):
    value = np.arange(6, dtype=np.float32).reshape(2, 3)
    path = tmp_path / "x.npy"
    digest, size = runner.save_npy_once(path, value)
    assert hashlib.sha256(path.read_bytes()).hexdigest() == digest
    assert path.stat().st_size == size
    assert np.array_equal(np.load(path, allow_pickle=False), value)
    with pytest.raises(FileExistsError):
        runner.save_npy_once(path, value)


def test_validate_stage_a_rejects_generic_base_artifact(monkeypatch, tmp_path):
    prov = tmp_path / "prov"
    prov.mkdir()
    (prov / "stage_a.json").write_text(json.dumps({"schema_version":"msae_measurement_remediation_artifact_v1","stage_ready":True}))
    monkeypatch.setattr(m, "V3_PROV", prov)
    with pytest.raises(ValueError, match="not a v3 wrapper"):
        m.validate_stage_a()


def test_private_state_directories_are_exact_mode(monkeypatch, tmp_path):
    keys = tmp_path / "keys"
    state = tmp_path / "state"
    monkeypatch.setattr(m, "PRIVATE_KEY", keys / "private.pem")
    monkeypatch.setattr(m, "STATE_ROOT", state)
    monkeypatch.setattr(m, "NONCE_DIR", state / "independent_measurement_v3/nonces")
    monkeypatch.setattr(m, "GPU_LOCK_DIR", state / "gpu_locks")
    config = tmp_path / "config"
    monkeypatch.setattr(m, "V3_CONFIG", config)
    monkeypatch.setattr(m, "verify_baseline_projection", lambda phase="M4": {"phase": phase})
    commitment = m.setup_authorization_state("operator")
    assert stat.S_IMODE((keys / "private.pem").stat().st_mode) == 0o600
    assert stat.S_IMODE(m.NONCE_DIR.stat().st_mode) == 0o700
    assert commitment["contains_execution_authorization"] is False


def test_static_source_has_no_np_allclose_and_broker_has_timeout_cleanup():
    runner_source = (ROOT / "scripts/run_msae_independent_calibration_v3.py").read_text()
    module_source = (ROOT / "scripts/msae_independent_measurement_v3.py").read_text()
    assert "np.allclose" not in runner_source
    assert "6 * 60 * 60" in module_source
    assert "os.killpg" in module_source
    assert "PR_SET_PDEATHSIG" in module_source


def test_shell_launcher_syntax():
    subprocess.check_call(["/usr/bin/bash", "-n", str(ROOT / "scripts/launch_msae_independent_calibration_v3.sh")])


def test_v3_short_gate_exact_integer_boundaries_and_repeat_invariance():
    assert not m.short_sentence_gate(4, 40, 100)
    assert m.short_sentence_gate(5, 20, 200)
    assert not m.short_sentence_gate(5, 20, 201)
    assert not m.short_sentence_gate(5, 19, 100)
    # Occurrences are deliberately absent from the API: only distinct members/sum count.
    assert m.short_sentence_gate(5, 20, 200) == m.short_sentence_gate(5, 20, 200)


def test_v3_passage_gate_exact_boundaries():
    assert not m.passage_coverage_gate(3, 20, 100)
    assert not m.passage_coverage_gate(4, 19, 100)
    assert not m.passage_coverage_gate(4, 20, 201)
    assert m.passage_coverage_gate(4, 20, 200)


def test_historical_comment_mismatch_is_typed_diagnostic(tmp_path):
    path = tmp_path / "historical.conllu"
    path.write_text("# sent_id = d-1\n# text = Different\n1\tActual\tactual\tNOUN\t_\t_\t0\troot\t_\t_\n", encoding="utf-8")
    docs = m.parse_conllu(path, strict_entities=False)
    diagnostics = [item for doc in docs for item in doc["diagnostics"]]
    assert diagnostics
    assert all(item["kind"] == "historical_text_comment_mismatch" for item in diagnostics)
    assert all(len(item["comment_sha256"]) == 64 and len(item["reconstruction_sha256"]) == 64 for item in diagnostics)


def test_punctuation_only_json_has_distinct_nontext_identity(tmp_path):
    path = tmp_path / "rows.jsonl"
    path.write_text('{"words":["..."]}\n', encoding="utf-8")
    docs, census = m.json_documents(path, "rows.jsonl", jsonl=True)
    assert docs == []
    assert census["punctuation_or_redaction_only_non_text"] == 1
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    assert census["non_text_diagnostics"][0]["identity"] == m.tuple_digest(
        m.PROTOCOL, "historical_json_nontext", digest, 0, "base")
    assert census["candidate_field_occurrences"] == census["candidate_field_occurrences_accounted"] == 1


def test_paired_json_accounts_for_each_side_independently(tmp_path):
    path = tmp_path / "rows.jsonl"
    path.write_text('{"source_words":["..."],"target_words":["A"]}\n', encoding="utf-8")
    docs, census = m.json_documents(path, "rows.jsonl", jsonl=True)
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    assert [doc.source_id for doc in docs] == [m.tuple_digest(
        m.PROTOCOL, "historical_json_document", "file_record", digest, 0, "target")]
    assert census["candidate_field_occurrences"] == 2
    assert census["candidate_field_occurrences_accounted"] == 2
    assert census["included_subrecords"] == 1
    assert census["punctuation_or_redaction_only_non_text_subrecords"] == 1
    assert census["non_text_diagnostics"][0]["side"] == "source"
    assert census["document_ledger"][0]["source_records"][0]["record_index"] == 0
    assert census["document_ledger"][0]["source_records"][0]["normalized_sentence_sha256"]


def test_json_fallback_identity_and_record_index_preserve_source_row(tmp_path):
    path = tmp_path / "rows.jsonl"
    path.write_text('{"metadata":true}\n{"text":"Actual row"}\n', encoding="utf-8")
    docs, census = m.json_documents(path, "rows.jsonl", jsonl=True)
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    assert docs[0].source_id == m.tuple_digest(
        m.PROTOCOL, "historical_json_document", "file_record", digest, 1, "base")
    assert docs[0].record_index == 1
    assert docs[0].source_record_indices == (1,)
    assert census["document_ledger"][0]["source_records"][0]["record_index"] == 1


def test_markdown_adapter_uses_only_physical_lf_boundaries_and_closes_ledger(tmp_path):
    path = tmp_path / "sample.md"
    path.write_text("alpha\u2028beta\r\n...\nfinal", encoding="utf-8")
    docs, census = m.line_documents(path, "sample.md")
    assert docs[0].sentences == (("alpha", "beta"), ("final",))
    assert docs[0].source_record_indices == (0, 2)
    assert census["physical_line_count"] == 3
    assert [row["outcome"] for row in census["line_ledger"]] == [
        "included_text", "punctuation_or_redaction_only_non_text", "included_text"]
    path.write_bytes(b"alpha\rbeta\n")
    bare_cr_docs, bare_cr_census = m.line_documents(path, "sample.md")
    assert bare_cr_census["physical_line_count"] == 1
    assert bare_cr_docs[0].sentences == (("alpha", "beta"),)


@pytest.mark.parametrize("constant", ["NaN", "Infinity", "-Infinity"])
def test_json_adapter_rejects_nonstandard_numeric_constants(tmp_path, constant):
    path = tmp_path / "bad.jsonl"
    path.write_text(f'{{"metadata":{constant}}}\n', encoding="utf-8")
    with pytest.raises(ValueError, match="invalid JSONL"):
        m.json_documents(path, "bad.jsonl", jsonl=True)


@pytest.mark.parametrize("payload", [
    '{"text":"secret","text":"innocuous"}\n',
    '{"source_revision":"a","source_revision":"b","text":"x"}\n',
    '{"nested":{"text":"a","text":"b"}}\n',
])
def test_json_adapter_rejects_duplicate_members_recursively(tmp_path, payload):
    path = tmp_path / "duplicate.jsonl"
    path.write_text(payload, encoding="utf-8")
    with pytest.raises(ValueError, match="invalid JSONL"):
        m.json_documents(path, "duplicate.jsonl", jsonl=True)


def test_json_adapter_rejects_duplicate_top_level_container_member(tmp_path):
    path = tmp_path / "duplicate.json"
    path.write_text('{"records":[],"records":[]}\n', encoding="utf-8")
    with pytest.raises(ValueError, match="duplicate JSON member"):
        m.json_documents(path, "duplicate.json", jsonl=False)


def test_json_structured_identity_has_no_delimiter_alias_and_paired_candidates_stay_distinct(tmp_path):
    left = tmp_path / "left.jsonl"
    left.write_text('{"source_revision":"a:b","document_group":"c","text":"same"}\n')
    right = tmp_path / "right.jsonl"
    right.write_text('{"source_revision":"a","document_group":"b:c","text":"same"}\n')
    left_doc = m.json_documents(left, "left.jsonl", jsonl=True)[0][0]
    right_doc = m.json_documents(right, "right.jsonl", jsonl=True)[0][0]
    assert left_doc.source_id != right_doc.source_id
    paired = tmp_path / "paired.jsonl"
    paired.write_text('{"source_words":["same"],"target_words":["same"]}\n')
    paired_docs, _ = m.json_documents(paired, "paired.jsonl", jsonl=True)
    assert len(paired_docs) == 2
    assert len({m._overlap_candidate_key(0, doc) for doc in paired_docs}) == 2


def test_punctuation_only_conllu_document_has_typed_identity(tmp_path):
    path = tmp_path / "punct.conllu"
    path.write_text("# newdoc id = p\n# sent_id = p-1\n# text = ...\n1\t...\t...\tPUNCT\t_\t_\t0\troot\t_\t_\n", encoding="utf-8")
    parsed = m.parse_conllu(path, strict_entities=False)
    docs, nontext = m._conllu_text_outcomes(parsed, "punct.conllu")
    assert docs == []
    assert nontext == [{"kind": "punctuation_or_redaction_only_non_text", "path": "punct.conllu",
                        "document_id": "p", "document_index": 0,
                        "identity": "punct.conllu:0:conllu:punctuation_or_redaction_only_non_text"}]


def test_fixture_artifact_covers_all_frozen_boundaries():
    artifact = m.build_overlap_fixtures()
    assert artifact["status"] == "eligible"
    names = {row["name"] for row in artifact["fixtures"]}
    required = {
        "document_49_tokens_not_comparable", "document_50_tokens_comparable",
        "document_20_grams_comparable",
        "document_19_grams_not_comparable", "sentence_9_tokens_non_substantive",
        "sentence_10_tokens_substantive", "sentence_5_distinct_grams",
        "sentence_6_distinct_grams", "plain_jaccard_exact_0_80",
        "plain_jaccard_below_0_80", "weighted_jaccard_exact_0_75",
        "weighted_jaccard_below_0_75", "passage_3_grams", "passage_19_positions",
        "passage_20_positions_at_10pct", "passage_20_positions_below_10pct",
        "short_repeat_1_vs_100_invariance", "independent_short_positive_at_10pct",
    }
    assert required <= names
    by_name = {row["name"]: row for row in artifact["fixtures"]}
    assert "document_plain_jaccard" not in by_name["plain_jaccard_below_0_80"]["observed"]["reasons"]
    assert "document_plain_jaccard" in by_name["plain_jaccard_exact_0_80"]["observed"]["reasons"]
    assert "document_idf_jaccard" not in by_name["weighted_jaccard_below_0_75"]["observed"]["reasons"]
    assert "document_idf_jaccard" in by_name["weighted_jaccard_exact_0_75"]["observed"]["reasons"]
    with m.decimal.localcontext(m.DECIMAL_CONTEXT):
        expected_below = format(m.decimal.Decimal(20) / m.decimal.Decimal(201), "f")
    assert by_name["passage_20_positions_below_10pct"]["observed"]["selected_coverage"] == expected_below
    assert by_name["passage_20_positions_at_10pct"]["observed"]["selected_coverage"] == "0.1"
    posthoc = json.loads((m.V3_DATA / "v2_posthoc_boilerplate_analysis.json").read_text())
    for name, row in zip(("min_esl", "min_childes", "bengali_esl", "bengali_childes"), posthoc["rows"]):
        observed = by_name[f"observed_v2_negative_{name}"]["observed"]
        assert observed["shared_short_member_count"] == row["distinct_tuple_count"]
        assert observed["shared_short_token_count"] == row["unique_tuple_token_sum"]
        assert observed["shared_short_tuple_set_sha256"] == row["shared_short_tuple_set_sha256"]
    assert by_name["passage_19_positions"]["multi_sentence_selected"] is True
    for name, expected in (("short_members_4_pair", False), ("short_members_5_pair", True),
                           ("short_tokens_19_pair", False), ("short_fraction_below_pair", False),
                           ("short_fraction_at_pair", True)):
        assert ("cumulative_short_sentences" in by_name[name]["observed"]["reasons"]) is expected


def test_binary_array_adapter_parses_complete_npy_and_npz_and_rejects_truncation(tmp_path):
    npy = tmp_path / "valid.npy"
    np.save(npy, np.arange(6, dtype=np.float32).reshape(2, 3), allow_pickle=False)
    structure = m.verify_binary_array(npy, ".npy")
    assert structure["members"][0]["shape"] == [2, 3]
    npz = tmp_path / "valid.npz"
    np.savez(npz, values=np.arange(3, dtype=np.int64))
    assert m.verify_binary_array(npz, ".npz")["members"][0]["name"] == "values.npy"
    prefixed = tmp_path / "prefixed.npz"
    prefixed.write_bytes(b"NOT_NPZ_TEXT_PREFIX" + npz.read_bytes())
    with pytest.raises(ValueError, match="byte-zero"):
        m.verify_binary_array(prefixed, ".npz")
    for name, payload, suffix in (("short.npy", b"\x93NUMPYxx", ".npy"),
                                  ("short.npz", b"PK\x03\x04junk", ".npz")):
        path = tmp_path / name
        path.write_bytes(payload)
        with pytest.raises(ValueError):
            m.verify_binary_array(path, suffix)


def test_unicode_case_and_materially_different_whitespace_normalize_identically():
    left = m.lexical_tokens(" \tCAFÉ\u00a0Straße\n")
    right = m.lexical_tokens("cafe\u0301\u2003  STRAẞE")
    assert left == right == ("café", "straße")
    a, b = document("a", left), document("b", right)
    decision = m.pair_decision(a, b, unit_weights(a, b))
    assert decision["blocking"] and "exact_full_document" in decision["reasons"]


def test_m1_recoverable_transaction_repairs_matching_partial_install(monkeypatch, tmp_path):
    data = tmp_path / "data"
    prov = tmp_path / "prov"
    transaction = prov / ".m1_install_transaction"
    data.mkdir()
    prov.mkdir()
    monkeypatch.setattr(m, "V3_DATA", data)
    monkeypatch.setattr(m, "V3_PROV", prov)
    monkeypatch.setattr(m, "M1_TRANSACTION_ROOT", transaction)
    payloads = {name: m.canonical_bytes({"name": name}) for name in m.V3_DATA_PHASE_FILES["M1"]}
    transaction.mkdir(mode=0o700)
    first = m.V3_DATA_PHASE_FILES["M1"][0]
    m.write_once(transaction / f"00.{first}.payload", payloads[first], 0o600)
    m.write_once(data / first, payloads[first], 0o644)
    m._install_m1_transaction(payloads)
    assert not transaction.exists()
    assert {path.name for path in data.iterdir()} == set(payloads)
    assert all((data / name).read_bytes() == payload for name, payload in payloads.items())


def test_m1_partial_targets_without_transaction_block(monkeypatch, tmp_path):
    data = tmp_path / "data"
    prov = tmp_path / "prov"
    data.mkdir()
    prov.mkdir()
    monkeypatch.setattr(m, "V3_DATA", data)
    monkeypatch.setattr(m, "V3_PROV", prov)
    monkeypatch.setattr(m, "M1_TRANSACTION_ROOT", prov / ".m1_install_transaction")
    payloads = {name: m.canonical_bytes({"name": name}) for name in m.V3_DATA_PHASE_FILES["M1"]}
    first = m.V3_DATA_PHASE_FILES["M1"][0]
    m.write_once(data / first, payloads[first], 0o644)
    with pytest.raises(ValueError, match="orphaned partial"):
        m._install_m1_transaction(payloads)


def test_m1_undeclared_transaction_entry_blocks_before_any_target_write(monkeypatch, tmp_path):
    data = tmp_path / "data"
    prov = tmp_path / "prov"
    transaction = prov / ".m1_install_transaction"
    data.mkdir()
    prov.mkdir()
    transaction.mkdir(mode=0o700)
    (transaction / "undeclared").write_text("no")
    monkeypatch.setattr(m, "V3_DATA", data)
    monkeypatch.setattr(m, "V3_PROV", prov)
    monkeypatch.setattr(m, "M1_TRANSACTION_ROOT", transaction)
    payloads = {name: m.canonical_bytes({"name": name}) for name in m.V3_DATA_PHASE_FILES["M1"]}
    with pytest.raises(ValueError, match="undeclared M1 transaction"):
        m._install_m1_transaction(payloads)
    assert list(data.iterdir()) == []


def test_m1_first_transaction_fsyncs_new_provenance_parent(monkeypatch, tmp_path):
    data = tmp_path / "data"
    provenance_parent = tmp_path / "reports/provenance"
    prov = provenance_parent / "msae_independent_measurement_v3"
    transaction = prov / ".m1_install_transaction"
    data.mkdir()
    provenance_parent.mkdir(parents=True)
    monkeypatch.setattr(m, "V3_DATA", data)
    monkeypatch.setattr(m, "V3_PROV", prov)
    monkeypatch.setattr(m, "M1_TRANSACTION_ROOT", transaction)
    payloads = {name: m.canonical_bytes({"name": name}) for name in m.V3_DATA_PHASE_FILES["M1"]}
    calls = []
    original = m._fsync_directory
    def recording(path):
        calls.append(path)
        original(path)
    monkeypatch.setattr(m, "_fsync_directory", recording)
    m._install_m1_transaction(payloads)
    assert provenance_parent in calls
    assert prov in calls
    assert not transaction.exists()


def test_quarantine_tripwire_blocks_builtin_path_and_dirfd_open_surfaces(monkeypatch, tmp_path):
    private = tmp_path / "private"
    private.mkdir()
    sealed = private / "final.jsonl"
    sealed.write_text("sealed")
    rel = "private/final.jsonl"
    monkeypatch.setattr(m, "ROOT", tmp_path)
    monkeypatch.setattr(m, "QUARANTINED", {rel: ("a" * 64, sealed.stat().st_size)})
    with m.quarantine_open_tripwire() as state:
        with pytest.raises(PermissionError):
            open(sealed, "rb")
        with pytest.raises(PermissionError):
            sealed.read_bytes()
        directory_fd = os.open(private, os.O_RDONLY | os.O_DIRECTORY)
        try:
            with pytest.raises(PermissionError):
                os.open("final.jsonl", os.O_RDONLY, dir_fd=directory_fd)
        finally:
            os.close(directory_fd)
    assert state["blocked_content_open_attempts"] == [rel, rel, rel]


def test_fixture_bytes_are_python_hash_seed_invariant(tmp_path):
    code = ("import sys;sys.path.insert(0,'scripts');import msae_independent_measurement_v3 as m;"
            "sys.stdout.buffer.write(m.canonical_bytes(m.build_overlap_fixtures()))")
    outputs = []
    for seed in ("1", "7", "101"):
        env = os.environ.copy()
        env["PYTHONHASHSEED"] = seed
        outputs.append(subprocess.check_output([sys.executable, "-B", "-c", code], cwd=ROOT, env=env))
    assert outputs[0] == outputs[1] == outputs[2]


def _alignment_inputs():
    frozen = json.loads((ROOT / "data/msae_independent_measurement_v1/calibration_strata.json").read_text())
    units = [json.loads(line) for line in (ROOT / frozen["source_path"]).read_text().splitlines()]
    pairs = [json.loads(line) for line in
             (ROOT / "data/atlas_measurement_v2_4/prepared/calibration/pairs.jsonl").read_text().splitlines()]
    return frozen, units, pairs


def test_counterfactual_alignment_reconstructs_all_sixteen_pairs():
    frozen, units, pairs = _alignment_inputs()
    result = m.counterfactual_alignment_qa(frozen, units, pairs)
    assert result["status"] == "eligible"
    assert result["pair_count"] == 16
    assert len({row["pair_id"] for row in result["pairs"]}) == 16


@pytest.mark.parametrize("mutation", ["reorder", "input", "position", "row", "side", "truncate"])
def test_counterfactual_alignment_rejects_mapping_mutations(mutation):
    frozen, units, pairs = _alignment_inputs()
    frozen = copy.deepcopy(frozen)
    target = frozen["strata"]["pair_context"]["units"]
    if mutation == "reorder":
        target[0], target[1] = target[1], target[0]
    elif mutation == "input":
        target[0]["input_ids"][0] += 1
    elif mutation == "position":
        target[0]["positions"][0] += 1
    elif mutation == "row":
        target[0]["row_ids"][0] += ":changed"
    elif mutation == "side":
        target[0]["side"] = "target"
    else:
        target.pop()
    with pytest.raises(ValueError):
        m.counterfactual_alignment_qa(frozen, units, pairs)


@pytest.mark.parametrize("atol,rtol", [("nan", "0"), ("inf", "0"), ("0", "-1"), ("1e309", "0")])
def test_selector_rejects_nonfinite_negative_or_overflowing_tolerances(atol, rtol):
    value = np.array([1.0], dtype=np.float32)
    assert runner.selector_ok(value, value, atol, rtol)[0] is False


def test_closed_baseline_projection_rejects_undeclared_data_addition(monkeypatch, tmp_path):
    root = tmp_path / "repo"
    data = root / "data"
    data.mkdir(parents=True)
    old = data / "old.json"
    old.write_text("{}\n")
    v3 = data / "msae_independent_measurement_v3"
    v3.mkdir()
    monkeypatch.setattr(m, "ROOT", root)
    monkeypatch.setattr(m, "V3_DATA", v3)
    monkeypatch.setattr(m, "QUARANTINED", {})
    baseline = {"schema_version": "msae_v3_data_baseline_manifest_v1", "protocol_id": m.PROTOCOL,
                "v3_root_absent_at_snapshot": True, "quarantined_paths": [], "entries": [
        {"path": "data/old.json", "type": "regular", "mode": stat.S_IMODE(old.stat().st_mode),
         "size": old.stat().st_size, "sha256": hashlib.sha256(old.read_bytes()).hexdigest(),
         "verification_action": "content_rehash"},
    ]}
    for name in m.V3_DATA_PHASE_FILES["M0"]:
        (v3 / name).write_text("{}\n")
    (v3 / "data_baseline_manifest.json").write_text(json.dumps(baseline))
    # The manifest entry for itself is intentionally not in the pre-v3 baseline.
    assert m.verify_baseline_projection("M0")["declared_v3_files"] == len(m.V3_DATA_PHASE_FILES["M0"])
    old_mode = stat.S_IMODE(old.stat().st_mode)
    old.chmod(old_mode ^ stat.S_IXUSR)
    with pytest.raises(ValueError, match="baseline content drift"):
        m.verify_baseline_projection("M0")
    old.chmod(old_mode)
    (data / "undeclared.json").write_text("{}\n")
    with pytest.raises(ValueError, match="closed data projection"):
        m.verify_baseline_projection("M0")


def test_quarantine_baseline_checks_complete_lstat_identity_without_open(monkeypatch, tmp_path):
    root = tmp_path / "repo"
    data = root / "data"
    v3 = data / "msae_independent_measurement_v3"
    v3.mkdir(parents=True)
    sealed = data / "sealed.bin"
    sealed.write_bytes(b"do-not-open")
    st = sealed.lstat()
    rel = "data/sealed.bin"
    frozen_hash = "a" * 64
    monkeypatch.setattr(m, "ROOT", root)
    monkeypatch.setattr(m, "V3_DATA", v3)
    monkeypatch.setattr(m, "QUARANTINED", {rel: (frozen_hash, st.st_size)})
    entry = {"path": rel, "type": "regular", "mode": stat.S_IMODE(st.st_mode),
             "size": st.st_size, "sha256": frozen_hash, "device": st.st_dev,
             "inode": st.st_ino, "nlink": st.st_nlink, "ctime_ns": st.st_ctime_ns,
             "mtime_ns": st.st_mtime_ns,
             "verification_action": "lstat_only_against_frozen_v1_evidence"}
    baseline = {"schema_version": "msae_v3_data_baseline_manifest_v1", "protocol_id": m.PROTOCOL,
                "v3_root_absent_at_snapshot": True, "quarantined_paths": [rel], "entries": [entry]}
    for name in m.V3_DATA_PHASE_FILES["M0"]:
        (v3 / name).write_text("{}\n")
    (v3 / "data_baseline_manifest.json").write_text(json.dumps(baseline))
    assert m.verify_baseline_projection("M0")["lstat_only"] == 1
    baseline["entries"][0]["inode"] += 1
    (v3 / "data_baseline_manifest.json").write_text(json.dumps(baseline))
    with pytest.raises(ValueError, match="metadata drift"):
        m.verify_baseline_projection("M0")


def test_candidate_paths_reject_undeclared_v3_file(monkeypatch, tmp_path):
    v3 = tmp_path / "v3"
    v3.mkdir()
    for name in m.V3_DATA_ALL_FILES:
        (v3 / name).write_text("{}\n")
    (v3 / "surprise.json").write_text("{}\n")
    monkeypatch.setattr(m, "V3_DATA", v3)
    with pytest.raises(ValueError, match="candidate set mismatch"):
        m._candidate_paths()


def test_m4_constructs_two_complete_trees_and_cleans_them(monkeypatch, tmp_path):
    root = tmp_path / "repo"
    v3 = root / "data/msae_independent_measurement_v3"
    v3.mkdir(parents=True)
    primary, rebuild = tmp_path / "primary", tmp_path / "rebuild"
    monkeypatch.setattr(m, "ROOT", root)
    monkeypatch.setattr(m, "V3_DATA", v3)
    monkeypatch.setattr(m, "PRIMARY_BUILD_ROOT", primary)
    monkeypatch.setattr(m, "REBUILD_BUILD_ROOT", rebuild)
    monkeypatch.setattr(m, "verify_baseline_projection", lambda phase="M4": {"phase": phase})
    monkeypatch.setattr(m, "closure_payload", lambda checkpoints: {"kind": "closure", "checkpoints": checkpoints})
    monkeypatch.setattr(m, "endpoint_registry", lambda: {"kind": "registry"})
    monkeypatch.setattr(m, "environment_payload", lambda closure: {"kind": "environment", "closure": closure})
    stage = {"schema_version": "test_stage", "stage_ready": True}
    monkeypatch.setattr(m, "stage_a_payload", lambda **kwargs: stage)
    monkeypatch.setattr(m, "build_candidate_manifest", lambda **kwargs: {"kind": "manifest"})
    monkeypatch.setattr(m, "_anticipated_m4_status", lambda: [])
    result = m.build_m4([{"checkpoint_id": "x"}])
    assert result == stage
    assert not primary.exists() and not rebuild.exists()
    for relative in m._M4_NEW_RELATIVES:
        assert (root / relative).is_file()


def test_signed_authorization_binds_scope_time_operator_and_is_single_use(monkeypatch, tmp_path):
    config = tmp_path / "config"
    data = tmp_path / "data"
    prov = tmp_path / "prov"
    run = tmp_path / "run"
    review = tmp_path / "review.md"
    private = tmp_path / "keys/private.pem"
    state = tmp_path / "state"
    nonce = state / "independent_measurement_v3/nonces"
    locks = state / "gpu_locks"
    for path in (config, data, prov):
        path.mkdir()
    (config / "protocol.json").write_text("{}\n")
    (data / "dependency_closure.json").write_text("{}\n")
    (prov / "stage_a.json").write_text("{}\n")
    review.write_text("VERDICT: SHIP\n")
    monkeypatch.setattr(m, "V3_CONFIG", config)
    monkeypatch.setattr(m, "V3_DATA", data)
    monkeypatch.setattr(m, "V3_PROV", prov)
    monkeypatch.setattr(m, "V3_REVIEW", review)
    monkeypatch.setattr(m, "RUN_ROOT", run)
    monkeypatch.setattr(m, "PRIVATE_KEY", private)
    monkeypatch.setattr(m, "STATE_ROOT", state)
    monkeypatch.setattr(m, "NONCE_DIR", nonce)
    monkeypatch.setattr(m, "GPU_LOCK_DIR", locks)
    monkeypatch.setattr(m, "verify_candidate_manifest", lambda phase="prescore": {"eligible": True})
    monkeypatch.setattr(m, "verify_baseline_projection", lambda phase="M4": {"phase": phase})
    m.setup_authorization_state("operator instruction")
    envelope = m.sign_authorization()
    assert m.verify_authorization(run / "authorization.json", consume=False)["scope"] == "calibration_replay_only"
    consumed = m.verify_authorization(run / "authorization.json", consume=True, run_root=run)
    record = nonce / f"{consumed['envelope_sha256']}.consumed"
    assert stat.S_IMODE(record.stat().st_mode) == 0o600
    with pytest.raises(FileExistsError):
        m.verify_authorization(run / "authorization.json", consume=True, run_root=run)

    from cryptography.hazmat.primitives import serialization
    private_key = serialization.load_pem_private_key(private.read_bytes(), password=None)
    original = json.loads((run / "authorization.json").read_text())
    for field, value, match in (
        ("scope", "confirmation", "scope"),
        ("operator_instruction_sha256", "a" * 64, "operator"),
        ("review_verdict", "BLOCK", "verdict"),
        ("expires_unix", original["issued_unix"] + 86401, "time"),
    ):
        changed = {k: v for k, v in original.items() if k != "signature_b64"}
        changed[field] = value
        changed["signature_b64"] = __import__("base64").b64encode(
            private_key.sign(m.canonical_bytes(changed))).decode("ascii")
        path = tmp_path / f"bad-{field}.json"
        path.write_bytes(m.canonical_bytes(changed))
        with pytest.raises(ValueError, match=match):
            m.verify_authorization(path, consume=False)


def test_gpu_uuid_lock_is_shared_contention_safe_and_fail_closed(monkeypatch, tmp_path):
    lock_dir = tmp_path / "locks"
    lock_dir.mkdir(mode=0o700)
    os.chmod(lock_dir, 0o700)
    config = tmp_path / "config"
    config.mkdir()
    binding = m._directory_binding(lock_dir)
    (config / "authorization_commitment.json").write_bytes(m.canonical_bytes({"gpu_lock_directory": binding}))
    monkeypatch.setattr(m, "GPU_LOCK_DIR", lock_dir)
    monkeypatch.setattr(m, "V3_CONFIG", config)
    uuid = "GPU-01234567-89ab-cdef-0123-456789abcdef"
    first, path = m._open_gpu_lock(uuid)
    try:
        with pytest.raises(BlockingIOError):
            m._open_gpu_lock(uuid)
        assert path.read_bytes() == m.canonical_bytes({"schema_version": "msae_gpu_uuid_lock_v1", "gpu_uuid": uuid})
        assert stat.S_IMODE(path.stat().st_mode) == 0o600
    finally:
        os.close(first)
    path.chmod(0o644)
    with pytest.raises(ValueError, match="invalid persistent GPU lock"):
        m._open_gpu_lock(uuid)


def test_gpu_discovery_validates_rows_and_orders_candidates(monkeypatch):
    good = "1, GPU-11111111-1111-1111-1111-111111111111, 20, 1\n0, GPU-00000000-0000-0000-0000-000000000000, 10, 2\n"
    responses = iter([good, ""])
    monkeypatch.setattr(m.subprocess, "check_output", lambda *args, **kwargs: next(responses))
    rows = m._gpu_rows()
    assert [row[3] for row in rows] == [0, 1]
    responses = iter(["0, GPU-x;touch /tmp/pwn, 0, 0\n", ""])
    monkeypatch.setattr(m.subprocess, "check_output", lambda *args, **kwargs: next(responses))
    with pytest.raises(ValueError, match="malformed nvidia-smi"):
        m._gpu_rows()
