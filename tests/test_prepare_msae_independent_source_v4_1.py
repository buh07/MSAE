from __future__ import annotations

import hashlib
import importlib.util
import json
import os
from pathlib import Path
import sys

import pytest


SCRIPT = Path(__file__).parents[1] / "scripts/prepare_msae_independent_source_v4_1.py"
_spec = importlib.util.spec_from_file_location("msae_v4", SCRIPT)
assert _spec and _spec.loader
m = importlib.util.module_from_spec(_spec)
sys.modules[_spec.name] = m
_spec.loader.exec_module(m)


def sample_conllu() -> bytes:
    return b"""# sent_id = s1\n# text = A AB Ab a-b ...\n1\tA\ta\tNOUN\t_\tNumber=Sing\t0\troot\t_\t_\n2\tAB\tab\tNOUN\t_\tNumber=Plur\t1\tnmod:poss\t_\t_\n3-4\tAb a-b\t_\t_\t_\t_\t_\t_\t_\t_\n3\tAb\tab\tADJ\t_\t_\t2\tamod\t_\t_\n3.1\tghost\tghost\tX\t_\t_\t_\t_\t_\t_\n4\ta-b\ta-b\tNOUN\t_\t_\t2\tconj\t_\t_\n5\t...\t...\tPUNCT\t_\t_\t3\tpunct\t_\t_\n\n"""


def test_parse_and_exact_label_contract(tmp_path: Path):
    path = tmp_path / "x.conllu"
    path.write_bytes(sample_conllu())
    sentences, counts = m.parse_conllu(path)
    assert counts == {"integer_tokens": 5, "multiword_rows": 1, "empty_node_rows": 1}
    s = sentences[0]
    rows = m.sentence_labels(s)
    assert [r["absolute_bucket"] for r in rows] == ["0", "1", "2", "3", "4"]
    assert [r["relative_quartile"] for r in rows] == ["0", "0", "1", "2", "3"]
    assert [r["sentence_boundary"] for r in rows] == ["initial", "interior", "interior", "interior", "final"]
    assert [r["head_signed_distance"] for r in rows] == ["ROOT", "L1_2", "L1_2", "L1_2", "L1_2"]
    assert [r["dependency_depth"] for r in rows] == ["0", "1", "2", "2", "3"]
    assert [r["capitalization"] for r in rows] == ["upper", "upper", "title", "lower", "nonalpha"]
    assert [r["word_length"] for r in rows] == ["1", "2", "2", "3_4", "3_4"]
    assert [r["punctuation"] for r in rows] == ["NONPUNCT"] * 4 + ["PUNCT"]
    assert rows[0]["number"] == "Sing" and rows[1]["number"] == "Plur"
    assert rows[2]["number"] is None and rows[1]["deprel_coarse"] == "nmod"


@pytest.mark.parametrize("feats", ["Number=Sing|Number=Plur", "Number=Sing,Plur", "=x", "A="])
def test_bad_feats_are_terminal(tmp_path: Path, feats: str):
    raw = sample_conllu().replace(b"Number=Sing", feats.encode(), 1)
    path = tmp_path / "bad.conllu"
    path.write_bytes(raw)
    with pytest.raises(m.GateFailure):
        m.parse_conllu(path)


def test_ud_multivalue_nonnumber_is_allowed_and_canonical(tmp_path: Path):
    path = tmp_path / "multi.conllu"
    path.write_bytes(sample_conllu().replace(b"Number=Sing", b"PronType=Int,Rel", 1))
    sentences, _ = m.parse_conllu(path)
    assert m.sentence_labels(sentences[0])[0]["number"] is None


@pytest.mark.parametrize("feats", ["PronType=Rel,Int", "PronType=Int,,Rel", "PronType=Int,Int"])
def test_noncanonical_multivalue_feats_are_terminal(tmp_path: Path, feats: str):
    path = tmp_path / "bad_multi.conllu"
    path.write_bytes(sample_conllu().replace(b"Number=Sing", feats.encode(), 1))
    with pytest.raises(m.GateFailure):
        m.parse_conllu(path)


def test_cycle_is_terminal(tmp_path: Path):
    path = tmp_path / "cycle.conllu"
    path.write_bytes(sample_conllu().replace(b"\t0\troot", b"\t2\troot", 1))
    with pytest.raises(m.GateFailure):
        m.parse_conllu(path)


def test_overlap_rules_and_orientation():
    assert m.overlap_reason(("show", "flights"), ("please", "show", "flights", "now")) == "contained_short"
    a = tuple(f"w{i}" for i in range(24))
    assert m.overlap_reason(a, a) == "exact"
    assert m.overlap_reason(a, a[:-1] + ("other",)) in {"fivegram_jaccard", "covered_fivegrams"}
    assert m.overlap_reason(("...",), ("---",)) is None


def test_split_and_manifest_golden():
    rows = [
        {"sent_id": "x!", "normalized": "x !"},
        {"sent_id": "\u00e9", "normalized": "e accent"},
    ]
    assigned = m.assign_split(rows)
    assert sorted(x["panel"] for x in assigned) == ["C1", "C2"]
    golden = {
        "schema_version": "msae_independent_source_v4_split_manifest_v1",
        "source_commit": "0" * 40,
        "split_algorithm": "sha256-canonical-json-array-v1-even-C1-odd-C2",
        "record_count": 2,
        "C1_count": 1,
        "C2_count": 1,
        "entries": [
            {"sent_id": "\u00e9", "panel": "C1", "zero_based_rank": 0, "split_key_sha256": "0" * 64},
            {"sent_id": "x!", "panel": "C2", "zero_based_rank": 1, "split_key_sha256": "f" * 64},
        ],
    }
    assert hashlib.sha256(m.canonical_file_bytes(golden)).hexdigest() == "bee7c051e64b1a8b113843da9200928503ab5a58fc85aff9af61700ece70b128"


def test_create_once_private_payload_and_no_source_output(tmp_path: Path, capsys):
    private = tmp_path / "private"
    records = [{"canary": "MSAE_V4_SECRET_7f6b6aa8", "id": 1}]
    path = m.publish_private_jsonl(private, "payload.jsonl", records)
    assert path.stat().st_mode & 0o777 == 0o600
    assert private.stat().st_mode & 0o777 == 0o700
    assert capsys.readouterr() == ("", "")
    with pytest.raises(FileExistsError):
        m.publish_private_jsonl(private, "payload.jsonl", records)


def test_lexical_support_is_hashed():
    value = "MSAE_V4_SECRET_LEMMA_9d3e"
    item = m.public_label("lemma_identity", value)
    assert value not in json.dumps(item)
    assert item == hashlib.sha256(("msae-v4/lemma\0" + value).encode()).hexdigest()


def test_quarantine_inventory_is_lstat_only(tmp_path: Path, monkeypatch):
    q = tmp_path / "q.jsonl"
    q.write_text("MSAE_V4_MUST_NOT_OPEN")
    called = []
    real_open = Path.open
    def guarded(self, *args, **kwargs):
        if self == q:
            called.append(True)
            raise AssertionError("quarantine opened")
        return real_open(self, *args, **kwargs)
    monkeypatch.setattr(Path, "open", guarded)
    item = m.inventory_one(q, "q.jsonl", {"q.jsonl"})
    assert item["sha256"] is None
    assert item["adapter"] == "quarantine_lstat_only"
    assert item["content_reads"] == 0
    assert not called


def test_static_no_neural_contract():
    assert m.validate_static_contract(SCRIPT) == []
