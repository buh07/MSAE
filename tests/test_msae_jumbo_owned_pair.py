"""Synthetic native-Jumbo qualification of the retained-handle extension."""
from __future__ import annotations

import dataclasses
import hashlib
import os
from pathlib import Path
import stat
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import msae_jumbo_pair_commit as j


def fds():
    return set(os.listdir("/proc/self/fd"))


def test_writer_stays_owned_until_explicit_aggregate_end(tmp_path):
    before = fds()
    with j.create_owned_pair(tmp_path / "one", b"alpha", mode=0o600) as one:
        with j.create_owned_pair(tmp_path / "two", b"beta", mode=0o600) as two:
            assert os.fstat(one.fd).st_ino == one.receipt.inode
            assert os.fstat(two.fd).st_ino == two.receipt.inode
            one.validate(durable=True)
            two.validate(durable=True)
    assert fds() == before
    with pytest.raises(j.PairFailure, match="closed"):
        one.validate()
    one.close()  # idempotence does not repeat Linux close


@pytest.mark.parametrize("attack", ["bytes", "third", "replacement", "nonleaf"])
def test_early_writer_checked_again_after_later_pair(tmp_path, attack):
    root = tmp_path / "ancestor" / "dest"
    root.mkdir(parents=True)
    before = fds()
    with j.create_owned_pair(root / "one", b"alpha", mode=0o600) as one:
        with j.create_owned_pair(root / "two", b"beta", mode=0o600):
            if attack == "bytes":
                (root / "one").write_bytes(b"xxxxx")
            elif attack == "third":
                os.link(root / "one", root / "third")
            elif attack == "replacement":
                os.rename(root / "one", root / "retained-original")
                (root / "one").write_bytes(b"alpha")
            else:
                os.rename(root.parent, tmp_path / "retained-ancestor")
                root.mkdir(parents=True)
            with pytest.raises(j.PairFailure):
                one.validate(durable=True)
    assert fds() == before


def test_pair_close_failure_propagates_even_inside_unrelated_exception(tmp_path, monkeypatch):
    before = fds()
    close = os.close
    seen = []
    try:
        raise ValueError("unrelated")
    except ValueError:
        pair = j.create_owned_pair(tmp_path / "one", b"alpha", mode=0o600)
        target = pair.fd
        def failed(fd):
            close(fd)
            if fd == target:
                seen.append(fd)
                raise OSError("close-after-release")
        monkeypatch.setattr(j.os, "close", failed)
        with pytest.raises(OSError, match="close-after-release"):
            with pair:
                pair.validate()
        pair.close()
    assert seen == [target] and fds() == before


def test_primary_and_all_secondary_close_errors_are_preserved(tmp_path, monkeypatch):
    before = fds()
    pair = j.create_owned_pair(tmp_path / "one", b"alpha", mode=0o600)
    owned = {pair.fd, *pair.parent.descriptors}
    close = os.close
    seen = []
    def failed(fd):
        close(fd)
        if fd in owned:
            seen.append(fd)
            raise OSError("secondary")
    monkeypatch.setattr(j.os, "close", failed)
    with pytest.raises(KeyboardInterrupt, match="primary") as caught:
        with pair:
            raise KeyboardInterrupt("primary")
    assert len(seen) == len(owned) and len(set(seen)) == len(owned)
    assert len(caught.value.__notes__) == len(owned)
    pair.close()
    assert fds() == before


def test_owned_reader_requires_external_receipt_and_rechecks_read_time(tmp_path, monkeypatch):
    receipt = j.create_pair(tmp_path / "one", b"alpha", mode=0o600)
    before = fds()
    with pytest.raises(TypeError):
        j.open_owned_pair(tmp_path / "one")
    with j.open_owned_pair(tmp_path / "one", receipt) as pair:
        assert pair.read_bytes(max_bytes=5) == b"alpha"
        with pytest.raises(j.PairFailure, match="large"):
            pair.read_bytes(max_bytes=4)
        original = os.pread
        fired = []
        def drift(fd, count, offset):
            result = original(fd, count, offset)
            if fd == pair.fd and not fired:
                fired.append(True)
                (tmp_path / "one").write_bytes(b"xxxxx")
            return result
        monkeypatch.setattr(j.os, "pread", drift)
        with pytest.raises(j.PairFailure):
            pair.read_bytes(max_bytes=5)
    assert fds() == before


@pytest.mark.parametrize("field", list(j.PairReceipt.__dataclass_fields__))
def test_serialized_receipts_reject_type_spoofing(tmp_path, field):
    receipt = j.create_pair(tmp_path / "one", b"alpha", mode=0o600)
    record = j.receipt_record(receipt)
    assert j.receipt_from_record(tmp_path / "one", record) == receipt
    record[field] = True
    with pytest.raises(j.PairFailure):
        j.receipt_from_record(tmp_path / "one", record)


@pytest.mark.parametrize("change", ["extra", "missing", "alias", "hash"])
def test_serialized_receipts_require_exact_keys_names_digest(tmp_path, change):
    receipt = j.create_pair(tmp_path / "one", b"alpha", mode=0o600)
    record = dataclasses.asdict(receipt)
    if change == "extra":
        record["extra"] = 0
    elif change == "missing":
        del record["device"]
    elif change == "alias":
        record["stage_name"] = ".else.stage"
    else:
        record["sha256"] = "G" * 64
    with pytest.raises(j.PairFailure):
        j.receipt_from_record(tmp_path / "one", record)


def test_only_explicit_owned_immediate_parent_mode_transition(tmp_path):
    root = tmp_path / "raw"
    root.mkdir(mode=0o700)
    before = fds()
    with j.create_owned_pair(root / "one", b"alpha", mode=0o444) as pair:
        os.chmod(root, 0o555)
        with pytest.raises(j.PairFailure):
            pair.validate()
        pair.accept_readonly_parent()
        pair.validate(durable=True)
        assert stat.S_IMODE(root.stat().st_mode) == 0o555
    assert fds() == before


@pytest.mark.parametrize("attack", ["not_changed", "wrong_mode", "replacement", "nonleaf"])
def test_readonly_transition_cannot_accept_other_drift(tmp_path, attack):
    root = tmp_path / "ancestor" / "raw"
    root.mkdir(parents=True, mode=0o700)
    with j.create_owned_pair(root / "one", b"alpha", mode=0o444) as pair:
        if attack == "wrong_mode":
            os.chmod(root, 0o777)
        elif attack == "replacement":
            os.rename(root, root.parent / "retained-original")
            root.mkdir(mode=0o555)
        elif attack == "nonleaf":
            os.chmod(root, 0o555)
            os.rename(root.parent, tmp_path / "retained-ancestor")
            root.mkdir(parents=True, mode=0o555)
        with pytest.raises(j.PairFailure):
            pair.accept_readonly_parent()


def test_owned_reader_never_accepts_observed_digest_in_place_of_expectation(tmp_path):
    receipt = j.create_pair(tmp_path / "one", b"alpha", mode=0o600)
    altered = dataclasses.replace(receipt, sha256=hashlib.sha256(b"wrong").hexdigest())
    with pytest.raises(j.PairFailure):
        j.open_owned_pair(tmp_path / "one", altered)
