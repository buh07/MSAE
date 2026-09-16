from __future__ import annotations

import importlib.util
import json
import os
from pathlib import Path
import stat

import pytest

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "msae_v3_post_m1", ROOT / "scripts/msae_independent_measurement_v3_post_m1.py")
assert SPEC and SPEC.loader
continuation = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(continuation)


@pytest.mark.parametrize("form,raw,expected", [
    ('"', "``", "PUNCT"), ("'", "''", "PUNCT"), ("!", ".", "PUNCT"),
    ("✉", "``", "SYM"), ("word", "NOUN", "NOUN"),
])
def test_registered_legacy_upos_repair(form, raw, expected):
    assert continuation.corrected_upos(form, raw) == expected


def test_exact_lexical_exception_registry():
    assert continuation.corrected_upos("'d", "''", lemma="will", deprel="xcomp") == "AUX"
    assert continuation.corrected_upos("’", "``", lemma="'s", deprel="case") == "PART"
    with pytest.raises(ValueError):
        continuation.corrected_upos("'d", "''", lemma="would", deprel="xcomp")


@pytest.mark.parametrize("form,raw", [("word", "``"), ("a!", "."), ("!", "BAD"), ("", "``")])
def test_legacy_upos_repair_is_closed(form, raw):
    with pytest.raises(ValueError):
        continuation.corrected_upos(form, raw)


def test_repair_is_strictly_amalgum_scoped():
    with pytest.raises(ValueError, match="unknown UPOS"):
        continuation._corrected_base_labels(
            '"', '"', 0, 2, source_genre="UD_English-GUM:UD", upos="``")
    labels = continuation._corrected_base_labels(
        '"', '"', 0, 2, source_genre="AMALGUM:news", upos="``")
    assert labels["upos_coarse"] == "PUNCT"


def test_real_selected_unknown_upos_inventory_is_exactly_repairable():
    counts = {}
    total = 0
    token_count = 0
    for path in sorted((ROOT / "data/msae_independent_measurement_v1/selected_raw/amalgum").rglob("*.conllu")):
        for line in path.read_text(encoding="utf-8").splitlines():
            fields = line.split("\t")
            if len(fields) == 10 and fields[0].isdigit():
                token_count += 1
                if fields[3] not in continuation.base.UPOS:
                    corrected = continuation.corrected_upos(
                        fields[1], fields[3], lemma=fields[2], deprel=fields[7])
                    counts[(fields[3], corrected)] = counts.get((fields[3], corrected), 0) + 1
                    total += 1
    assert token_count == continuation.EXPECTED_POPULATION_COUNTS["raw_selected"]
    assert total == 36
    assert counts == continuation.EXPECTED_TRANSITIONS["raw_selected"]


def test_historical_sources_contain_no_repairable_legacy_upos():
    token_count = 0
    unknown = []
    for role in ("discovery", "calibration"):
        path = ROOT / f"data/atlas_v1/partitions/{role}.records.jsonl"
        for index, line in enumerate(path.read_text(encoding="utf-8").splitlines()):
            record = json.loads(line)
            if record["source_type"] != "UD":
                continue
            for j, upos in enumerate(record["labels"]["upos"]):
                token_count += 1
                if upos not in continuation.base.UPOS and upos != "__DROP__":
                    unknown.append((role, index, j, upos))
    assert token_count == 91906
    assert unknown == []


def test_continuation_pins_successful_m1_builder_and_m0():
    assert continuation.base.sha_file(Path(continuation.base.__file__)) == continuation.BASE_M1_SHA256
    assert continuation.base.sha_file(
        continuation.base.V3_DATA / "m0_completion_manifest.json") == continuation.M0_COMPLETION_SHA256


def test_m1_completion_requires_external_digest_and_canonical_semantics(tmp_path, monkeypatch):
    path = tmp_path / "m1.json"
    payload = {"status": "eligible", "entries": [1, 2, 3]}
    path.write_bytes(continuation.base.canonical_bytes(payload))
    monkeypatch.setattr(continuation, "M1_COMPLETION_PATH", path)
    monkeypatch.setattr(continuation, "_m1_completion_payload", lambda: payload)
    monkeypatch.setattr(continuation.base, "verify_m0_completion", lambda *a, **k: {})
    digest = continuation.base.sha_file(path)
    assert continuation.verify_m1_completion(digest) == payload
    with pytest.raises(ValueError, match="digest mismatch"):
        continuation.verify_m1_completion("0" * 64)
    path.write_bytes(b'{"status":"eligible", "entries":[1,2,3]}\n')
    with pytest.raises(ValueError, match="semantic/canonical"):
        continuation.verify_m1_completion(continuation.base.sha_file(path))


def test_closure_extension_binds_every_continuation_byte_and_rejects_drift(tmp_path, monkeypatch):
    names = ["controller.py", "rfc.md", "test.py", "m1.json"]
    paths = []
    for i, name in enumerate(names):
        path = tmp_path / name
        path.write_bytes(f"payload-{i}\n".encode())
        paths.append(path)
    monkeypatch.setattr(continuation, "CONTROLLER_PATH", paths[0])
    monkeypatch.setattr(continuation, "CONTINUATION_RFC", paths[1])
    monkeypatch.setattr(continuation, "CONTINUATION_TEST", paths[2])
    monkeypatch.setattr(continuation, "M1_COMPLETION_PATH", paths[3])
    entries = continuation.continuation_closure_entries()
    assert {Path(item["path"]) for item in entries} == set(paths)
    frozen = continuation.base.sha_bytes(continuation.base.canonical_bytes(entries))
    for path in paths:
        old = path.read_bytes()
        path.write_bytes(old + b"drift")
        changed = continuation.continuation_closure_entries()
        assert continuation.base.sha_bytes(continuation.base.canonical_bytes(changed)) != frozen
        path.write_bytes(old)


@pytest.fixture
def transaction_tree(tmp_path, monkeypatch):
    data = tmp_path / "data"
    prov = tmp_path / "provenance"
    data.mkdir(mode=0o755)
    prov.mkdir(mode=0o700)
    transaction = prov / ".m2_install_transaction"
    monkeypatch.setattr(continuation.base, "V3_DATA", data)
    monkeypatch.setattr(continuation, "M2_TRANSACTION_ROOT", transaction)
    payloads = {name: f"{name}\n".encode()
                for name in continuation.base.V3_DATA_PHASE_FILES["M2"]}
    return data, transaction, payloads


@pytest.mark.parametrize("failure_boundary", range(7))
def test_m2_transaction_recovers_every_target_boundary(
        transaction_tree, monkeypatch, failure_boundary):
    data, transaction, payloads = transaction_tree
    original = continuation.base.write_once
    target_calls = 0

    def interrupted(path, payload, mode=0o644):
        nonlocal target_calls
        if path.parent == data:
            if target_calls == failure_boundary:
                target_calls += 1
                raise OSError("injected target-write interruption")
            target_calls += 1
        return original(path, payload, mode)

    monkeypatch.setattr(continuation.base, "write_once", interrupted)
    with pytest.raises(OSError, match="injected"):
        continuation._install_m2_transaction(payloads)
    assert transaction.is_dir()
    monkeypatch.setattr(continuation.base, "write_once", original)
    continuation._install_m2_transaction(payloads)
    assert not transaction.exists()
    for name, payload in payloads.items():
        path = data / name
        assert path.read_bytes() == payload
        assert stat.S_IMODE(path.stat().st_mode) == 0o644
    # A complete identical set is an idempotent no-op; drift is not.
    continuation._install_m2_transaction(payloads)
    first = data / continuation.base.V3_DATA_PHASE_FILES["M2"][0]
    first.write_bytes(b"drift\n")
    with pytest.raises(ValueError, match="completed M2 output drift"):
        continuation._install_m2_transaction(payloads)


def test_m2_transaction_rejects_undeclared_entry_before_target_write(transaction_tree):
    data, transaction, payloads = transaction_tree
    transaction.mkdir(mode=0o700)
    (transaction / "undeclared").write_bytes(b"x")
    with pytest.raises(ValueError, match="undeclared M2 transaction entries"):
        continuation._install_m2_transaction(payloads)
    assert list(data.iterdir()) == []


def test_partial_targets_without_transaction_are_rejected(transaction_tree):
    data, transaction, payloads = transaction_tree
    first = continuation.base.V3_DATA_PHASE_FILES["M2"][0]
    (data / first).write_bytes(payloads[first])
    with pytest.raises(ValueError, match="orphaned partial M2"):
        continuation._install_m2_transaction(payloads)


def test_placeholder_runtime_fails_closed():
    spec = importlib.util.spec_from_file_location(
        "msae_v3_post_m1_runtime",
        ROOT / "scripts/msae_independent_measurement_v3_post_m1_runtime.py")
    assert spec and spec.loader
    runtime = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(runtime)
    with pytest.raises(RuntimeError, match="not implemented or prescore-authorized"):
        runtime.dispatch(["launch"])
