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

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import msae_independent_measurement_v2 as m

RUNNER_SPEC = importlib.util.spec_from_file_location("runner_v2", ROOT / "scripts/run_msae_independent_calibration_v2.py")
assert RUNNER_SPEC and RUNNER_SPEC.loader
runner = importlib.util.module_from_spec(RUNNER_SPEC)
RUNNER_SPEC.loader.exec_module(runner)


def document(name: str, *sentences: tuple[str, ...]) -> m.TextDocument:
    return m.TextDocument(name, name, 0, tuple(sentences))


def unit_weights(*docs: m.TextDocument):
    return {g: m.decimal.Decimal(1) for d in docs for g in d.fivegrams}


def test_typed_tuple_golden_vectors_and_order():
    assert m.tuple_digest(m.PROTOCOL, "C1", "amalgum:academic", "doc-1", "sent-1", 7, "row-1") == "43dcf75650846dcfabfee037c9190aaca3f1d10e936ee5c80ff2a836428ee399"
    assert m.tuple_digest(m.PROTOCOL, "20260820", "calibration", "absolute_bucket", "gum", 0, 0) == "a65d135b27ed6f9979c6ade8fd107828d62acc6e0b7e5bb1bec29f3d73111dca"
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


def test_json_field_grammar_and_equivalence():
    obj = {"words": ["A", "cat"], "tokens": ["A cat"], "text": "A cat"}
    assert m._json_object_records(obj, "x", 0) == [("base", ("a", "cat"))]
    with pytest.raises(ValueError, match="conflicting"):
        m._json_object_records({"words": ["A", "cat"], "text": "A dog"}, "x", 0)


@pytest.mark.parametrize("value", [[], [""], [1], None, True, {}, [["x"]]])
def test_json_token_array_closed_grammar(value):
    with pytest.raises(ValueError):
        m.token_field(value, "words")


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
    monkeypatch.setattr(m, "V2_PROV", prov)
    with pytest.raises(ValueError, match="not a v2 wrapper"):
        m.validate_stage_a()


def test_private_state_directories_are_exact_mode(monkeypatch, tmp_path):
    keys = tmp_path / "keys"
    state = tmp_path / "state"
    monkeypatch.setattr(m, "PRIVATE_KEY", keys / "private.pem")
    monkeypatch.setattr(m, "STATE_ROOT", state)
    monkeypatch.setattr(m, "NONCE_DIR", state / "independent_measurement_v2/nonces")
    monkeypatch.setattr(m, "GPU_LOCK_DIR", state / "gpu_locks")
    config = tmp_path / "config"
    monkeypatch.setattr(m, "V2_CONFIG", config)
    commitment = m.setup_authorization_state("operator")
    assert stat.S_IMODE((keys / "private.pem").stat().st_mode) == 0o600
    assert stat.S_IMODE(m.NONCE_DIR.stat().st_mode) == 0o700
    assert commitment["contains_execution_authorization"] is False


def test_static_source_has_no_np_allclose_and_broker_has_timeout_cleanup():
    runner_source = (ROOT / "scripts/run_msae_independent_calibration_v2.py").read_text()
    module_source = (ROOT / "scripts/msae_independent_measurement_v2.py").read_text()
    assert "np.allclose" not in runner_source
    assert "6 * 60 * 60" in module_source
    assert "os.killpg" in module_source
    assert "PR_SET_PDEATHSIG" in module_source


def test_shell_launcher_syntax():
    subprocess.check_call(["/usr/bin/bash", "-n", str(ROOT / "scripts/launch_msae_independent_calibration_v2.sh")])
