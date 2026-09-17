"""Source-free resource regressions; no scientific or whole approval fixtures."""
import hashlib
import os
from pathlib import Path
import sys
import tracemalloc

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import msae_jumbo_pair_commit as j
import msae_norspan_jpc_controls as c
import msae_norspan_jpc_runtime as r
import prepare_msae_independent_norspan_v1 as p


def control(tmp_path):
    root = tmp_path / "controls"
    root.mkdir(mode=0o755)
    root.chmod(0o755)
    session = c.ControlSession(root, lineage_sha256="a" * 64)
    receipt = j.create_pair(root / "baseline.json", b"abcdefghi", mode=0o644)
    session.register("baseline.json", receipt)
    return root, session, receipt


def test_opaque_recovery_never_materializes_listdir(tmp_path, monkeypatch):
    root, session, _ = control(tmp_path)
    catalog = session.catalog()
    pin = hashlib.sha256(r.canonical_bytes(catalog)).hexdigest()

    def forbidden(*args, **kwargs):
        raise AssertionError("unbounded_listdir_used")

    monkeypatch.setattr(r.os, "listdir", forbidden)
    result = r.recover_current_custody(root, catalog, expected_catalog_sha256=pin,
                                      lineage_sha256=session.lineage)
    assert result["source_operations"] == result["model_operations"] == 0
    assert result["source_work_authorized"] is False


def test_opaque_recovery_rejects_at_cap_plus_one_and_closes_iterator(tmp_path, monkeypatch):
    root, session, _ = control(tmp_path)
    cap = len(r.CONTROL_NAMES) * 2
    for index in range(cap + 5):
        (root / ("foreign-%04d" % index)).write_bytes(b"foreign")
    catalog = session.catalog()
    pin = hashlib.sha256(r.canonical_bytes(catalog)).hexdigest()
    real = os.scandir
    seen, closed = [], []

    class Iterator:
        def __init__(self, fd):
            self.inner = real(fd)

        def __iter__(self):
            return self

        def __next__(self):
            entry = next(self.inner)
            seen.append(entry.name)
            return entry

        def close(self):
            closed.append(True)
            self.inner.close()

    monkeypatch.setattr(r.os, "scandir", Iterator)
    with pytest.raises(r.RuntimeBlocked, match="directory_entry_limit"):
        r.recover_current_custody(root, catalog, expected_catalog_sha256=pin,
                                 lineage_sha256=session.lineage)
    assert len(seen) == cap + 1 and closed == [True]
    assert len(list(root.iterdir())) == cap + 7


def test_actual_paired_prefix_never_calls_full_buffer_reader(tmp_path, monkeypatch):
    root, session, _ = control(tmp_path)
    monkeypatch.setattr(p, "PROV", root)

    def forbidden(*args, **kwargs):
        raise AssertionError("full_buffer_read_used")

    monkeypatch.setattr(j.OwnedPair, "read_bytes", forbidden)
    with p.paired_control_session(session):
        assert p.read_prefix_nofollow(root / "baseline.json", 3) == b"abc"


def test_large_control_one_byte_prefix_has_bounded_buffer_peak(tmp_path):
    root = tmp_path / "controls"
    root.mkdir(mode=0o755)
    root.chmod(0o755)
    # Allocate fixture before measurement; full validation still streams ALL
    # expected bytes, but the requested output must not buffer the whole fixture.
    payload = b"a" * (8 * 1024**2 + 333)
    session = c.ControlSession(root, lineage_sha256="a" * 64)
    session.register("baseline.json", j.create_pair(root / "baseline.json", payload, mode=0o644))
    tracemalloc.start()
    try:
        assert session.read_prefix("baseline.json", limit=1) == b"a"
        _, peak = tracemalloc.get_traced_memory()
    finally:
        tracemalloc.stop()
    assert peak < 4 * 1024**2, peak


@pytest.mark.parametrize("limit", [True, 0, -1, r.FILE_BYTES_LIMIT + 1])
def test_paired_prefix_limit_rejected_before_open(tmp_path, monkeypatch, limit):
    root, session, _ = control(tmp_path)
    monkeypatch.setattr(p, "PROV", root)

    def forbidden(*args, **kwargs):
        raise AssertionError("opened_before_prefix_limit_check")

    monkeypatch.setattr(j, "open_owned_pair", forbidden)
    with p.paired_control_session(session):
        with pytest.raises(p.GateFailure, match="prefix_limit_schema"):
            p.read_prefix_nofollow(root / "baseline.json", limit)


def test_prefix_copied_bytes_are_bound_to_whole_expected_digest(tmp_path, monkeypatch):
    root, _, receipt = control(tmp_path)
    real = os.pread
    fired = []
    with j.open_owned_pair(root / "baseline.json", receipt) as pair:
        real_validate = pair.validate
        phase = ["before"]

        def validate(*, durable=False):
            phase[0] = "validate"
            result = real_validate(durable=durable)
            phase[0] = "copy"
            return result

        def read(fd, count, offset):
            block = real(fd, count, offset)
            if fd == pair.fd and phase[0] == "copy" and offset == 0 and not fired:
                fired.append(True)
                return b"X" + block[1:]
            return block

        monkeypatch.setattr(pair, "validate", validate)
        monkeypatch.setattr(j.os, "pread", read)
        with pytest.raises(j.PairFailure, match="pair_read_time_drift"):
            pair.read_prefix(limit=3)
    assert fired == [True]
    assert (root / "baseline.json").read_bytes() == b"abcdefghi"


@pytest.mark.parametrize("failure", [OSError, KeyboardInterrupt])
def test_prefix_copy_primary_preserved_and_every_owned_fd_released(tmp_path, monkeypatch, failure):
    root, _, receipt = control(tmp_path)
    pair = j.open_owned_pair(root / "baseline.json", receipt)
    owned = {pair.fd, *pair.parent.descriptors}
    close, read = os.close, os.pread
    seen, fired = [], []
    real_validate = pair.validate
    phase = ["before"]

    def validate(*, durable=False):
        phase[0] = "validate"
        result = real_validate(durable=durable)
        phase[0] = "copy"
        return result

    def injected(fd, count, offset):
        if fd == pair.fd and phase[0] == "copy":
            fired.append(True)
            raise failure("prefix_primary")
        return read(fd, count, offset)

    def released(fd):
        seen.append(fd)
        close(fd)
        raise OSError("prefix_secondary")

    monkeypatch.setattr(pair, "validate", validate)
    monkeypatch.setattr(j.os, "pread", injected)
    monkeypatch.setattr(j.os, "close", released)
    with pytest.raises(failure, match="prefix_primary") as caught:
        with pair:
            pair.read_prefix(limit=3)
    assert fired == [True] and set(seen) == owned and len(seen) == len(owned)
    assert len(caught.value.__notes__) == len(owned)
    pair.close()
    assert len(seen) == len(owned)


@pytest.mark.parametrize("limit,expected", [(1, b"a"), (3, b"abc"), (20, b"abcdefghi")])
def test_prefix_short_preads_keep_only_requested_output(tmp_path, monkeypatch, limit, expected):
    root, _, receipt = control(tmp_path)
    real = os.pread

    def short(fd, count, offset):
        return real(fd, min(count, 2), offset)

    monkeypatch.setattr(j.os, "pread", short)
    assert c.ControlSession.from_catalog(root,
        {"schema_version": "norspan_jpc_custody_catalog_v1", "lineage_sha256": "a" * 64,
         "controls": {"baseline.json": j.receipt_record(receipt)}},
        expected_sha256=hashlib.sha256(r.canonical_bytes(
            {"schema_version": "norspan_jpc_custody_catalog_v1", "lineage_sha256": "a" * 64,
             "controls": {"baseline.json": j.receipt_record(receipt)}})).hexdigest(),
        lineage_sha256="a" * 64).read_prefix("baseline.json", limit=limit) == expected
