"""Source-free integration-foundation checks; NOT scientific gate evidence."""
from __future__ import annotations

import copy
import hashlib
import json
import os
from pathlib import Path
import stat
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import msae_jumbo_pair_commit as j
import msae_norspan_jpc_runtime as r

ROOT = Path(__file__).resolve().parents[1]


def fds():
    return set(os.listdir("/proc/self/fd"))


def test_amendment_freezes_literal_science_and_no_launch():
    cfg = r.load_amendment(ROOT)
    original = json.loads((ROOT / "configs/msae_independent_norspan_v1/protocol.json").read_bytes())
    assert r.scientific_projection(original) == cfg["scientific_projection"]
    assert cfg["production_launch_authorized"] is False
    with pytest.raises(r.RuntimeBlocked, match="whole_qualification_pending"):
        r.require_whole_qualification()


@pytest.mark.parametrize("field", ["source", "license", "pedigree", "role", "support", "overlap", "payload", "gates", "containment", "decision_rules", "history", "capability", "authorizations", "acquisition_limits", "runtime", "state_order"])
def test_every_scientific_field_drift_rejected(field):
    cfg = r.load_amendment(ROOT)
    original = json.loads((ROOT / "configs/msae_independent_norspan_v1/protocol.json").read_bytes())
    original[field] = True
    with pytest.raises(r.RuntimeBlocked):
        r.validate_projection(original, cfg)


def test_bool_integer_projection_drift_rejected():
    cfg = r.load_amendment(ROOT)
    original = json.loads((ROOT / "configs/msae_independent_norspan_v1/protocol.json").read_bytes())
    original["decision_rules"]["equivocal_authorizes_training"] = 0
    with pytest.raises(r.RuntimeBlocked):
        r.validate_projection(original, cfg)


@pytest.mark.parametrize("mode", [0o700, 0o555])
def test_flat_aggregate_real_eight_names_external_receipts(tmp_path, mode):
    before = fds()
    files = {str(i): b"synthetic-" + bytes([i]) for i in range(4)}
    manifest = r.publish_flat_pairs(tmp_path / "raw", files, directory_mode=mode, file_mode=0o444)
    assert set(os.listdir(tmp_path / "raw")) == {*(str(i) for i in range(4)), *(f".{i}.stage" for i in range(4))}
    assert stat.S_IMODE((tmp_path / "raw").stat().st_mode) == mode
    assert r.verify_flat_pairs(tmp_path / "raw", manifest, directory_mode=mode, file_mode=0o444, durable=True) == manifest
    assert fds() == before


@pytest.mark.parametrize("attack", ["early_bytes", "late_extra", "third", "substituted_final", "parent"])
def test_aggregate_rechecks_all_owned_writers_and_cardinality(tmp_path, monkeypatch, attack):
    original = j._insert_final
    root = tmp_path / "raw"
    fired = []
    def insert(parent, stage, final):
        original(parent, stage, final)
        if final == "two":
            fired.append(attack)
            if attack == "early_bytes":
                (root / "one").write_bytes(b"xxxxx")
            elif attack == "late_extra":
                (root / "foreign").write_bytes(b"foreign")
            elif attack == "third":
                os.link(root / "one", root / "third")
            elif attack == "substituted_final":
                os.rename(root / "one", root / "retained-original")
                (root / "one").write_bytes(b"alpha")
            else:
                os.rename(root, tmp_path / "retained-original")
                root.mkdir(mode=0o700)
    before = fds()
    monkeypatch.setattr(j, "_insert_final", insert)
    with pytest.raises((j.PairFailure, r.RuntimeBlocked)):
        r.publish_flat_pairs(root, {"one": b"alpha", "two": b"beta"}, directory_mode=0o555, file_mode=0o444)
    assert fired == [attack] and fds() == before
    if attack == "late_extra":
        assert (root / "foreign").read_bytes() == b"foreign"


@pytest.mark.parametrize("boundary", ["mkdir", "write", "link", "sync", "close"])
@pytest.mark.parametrize("error", [OSError, KeyboardInterrupt])
def test_flat_failure_never_returns_success_or_erases_partial(tmp_path, monkeypatch, boundary, error):
    originals = {name: getattr(os, name) for name in ["mkdir", "write", "link", "fsync", "close"]}
    op = "fsync" if boundary == "sync" else boundary
    seen = []
    def fail(*args, **kwargs):
        eligible = not seen
        if op == "close":
            # Real Linux close-after-release; subsequent descriptors must close.
            result = originals[op](*args, **kwargs)
            if eligible:
                seen.append(boundary)
                raise error("aggregate_fault")
            return result
        if eligible:
            seen.append(boundary)
            raise error("aggregate_fault")
        return originals[op](*args, **kwargs)
    before = fds()
    monkeypatch.setattr(os, op, fail)
    with pytest.raises(error, match="aggregate_fault"):
        r.publish_flat_pairs(tmp_path / "raw", {"one": b"alpha", "two": b"beta"}, directory_mode=0o555, file_mode=0o444)
    assert seen == [boundary] and fds() == before


def test_four_roles_have_distinct_pairs_and_only_final_consumers(tmp_path):
    before = fds()
    payloads = {role: b"synthetic-" + role.encode() for role in r.ROLES}
    manifest = r.publish_role_pairs(tmp_path / "private", payloads)
    assert set(os.listdir(tmp_path / "private")) == {role.lower() for role in r.ROLES}
    assert len({(item["pair"]["device"], item["pair"]["inode"]) for item in manifest.values()}) == 4
    assert r.verify_role_pairs(tmp_path / "private", manifest, durable=True) == manifest
    for role in r.ROLES:
        path = tmp_path / "private" / role.lower() / "payload.jsonl"
        with j.open_owned_pair(path, j.receipt_from_record(path, manifest[role]["pair"])) as pair:
            assert pair.read_bytes(max_bytes=100) == payloads[role]
    assert fds() == before


@pytest.mark.parametrize("attack", ["early_bytes", "cross_role", "root_extra", "role_extra", "second_partial"])
def test_four_role_faults_preserve_all_preceding_and_foreign_evidence(tmp_path, monkeypatch, attack):
    original = j._insert_final
    root = tmp_path / "private"
    count = []
    def insert(parent, stage, final):
        count.append(final)
        if len(count) == 2 and attack == "second_partial":
            raise KeyboardInterrupt("second_partial")
        original(parent, stage, final)
        if len(count) == 4:
            one = root / "discovery" / "payload.jsonl"
            if attack == "early_bytes":
                one.write_bytes(b"foreign")
            elif attack == "cross_role":
                os.link(one, root / "c1" / "foreign-alias")
            elif attack == "root_extra":
                (root / "foreign").write_bytes(b"foreign")
            elif attack == "role_extra":
                (root / "c2" / "foreign").write_bytes(b"foreign")
    before = fds()
    monkeypatch.setattr(j, "_insert_final", insert)
    with pytest.raises((r.RuntimeBlocked, j.PairFailure, KeyboardInterrupt)):
        r.publish_role_pairs(root, {role: role.encode() for role in r.ROLES})
    assert (root / "discovery" / ".payload.jsonl.stage").exists()
    assert (root / "discovery" / "payload.jsonl").exists()
    assert fds() == before


def lease(root):
    return r.reserve_scratch(root / "lease", authority_sha256="a" * 64, entry_lineage_sha256="b" * 64)


def test_scratch_prestart_binding_fsync_and_reopen_retains_all_bytes(tmp_path):
    before = fds()
    with lease(tmp_path) as scratch:
        scratch.validate_pristine()
        binding = copy.deepcopy(scratch.binding)
        assert binding["path"] == str(tmp_path / "lease")
        assert binding["mode"] == 0o700
        assert binding["cleanup_attempts"] == 0
        repo = tmp_path / "lease" / "repo"
        repo.mkdir(mode=0o700)
        (repo / ".git").mkdir(mode=0o700)
        (repo / "synthetic").write_bytes(b"retained source")
        result = scratch.snapshot(durable=True)
        assert result["retained"] is True and result["cleanup_attempts"] == 0
        assert result["total_bytes"] == len(b"retained source")
    with r.reopen_scratch(binding) as current:
        assert current.snapshot(durable=True)["total_bytes"] == len(b"retained source")
    assert (repo / "synthetic").read_bytes() == b"retained source"
    assert fds() == before


@pytest.mark.parametrize("attack", ["foreign", "root_replaced", "special", "hardlink", "file_budget", "total_budget", "entry_budget"])
def test_scratch_obstruction_or_budget_failure_preserves_every_object(tmp_path, attack):
    before = fds()
    with lease(tmp_path) as scratch:
        root = tmp_path / "lease"
        repo = root / "repo"
        repo.mkdir(mode=0o700)
        file = repo / "one"
        file.write_bytes(b"synthetic")
        limits = dict(file_bytes=100, total_bytes=100, entries=100)
        if attack == "foreign":
            (root / "foreign").write_bytes(b"foreign")
        elif attack == "root_replaced":
            os.rename(root, tmp_path / "retained-original")
            root.mkdir(mode=0o700)
            (root / "foreign").write_bytes(b"foreign")
        elif attack == "special":
            os.mkfifo(repo / "foreign-fifo", 0o600)
        elif attack == "hardlink":
            os.link(file, repo / "foreign-alias")
        elif attack == "file_budget":
            limits["file_bytes"] = 1
        elif attack == "total_budget":
            limits["total_bytes"] = 1
        else:
            limits["entries"] = 1
        with pytest.raises((r.RuntimeBlocked, j.PairFailure)):
            scratch.snapshot(durable=True, **limits)
    original = tmp_path / "retained-original" if attack == "root_replaced" else tmp_path / "lease"
    assert (original / "repo" / "one").read_bytes() == b"synthetic"
    assert fds() == before


def test_scratch_interrupt_and_primary_cleanup_fault_do_not_delete(tmp_path, monkeypatch):
    before = fds()
    scratch = lease(tmp_path)
    close = os.close
    target = scratch.fd
    def fail(fd):
        close(fd)
        if fd == target:
            raise OSError("close-after-release")
    monkeypatch.setattr(os, "close", fail)
    with pytest.raises(KeyboardInterrupt, match="primary") as caught:
        with scratch:
            (tmp_path / "lease" / "home" / "foreign").write_bytes(b"foreign")
            raise KeyboardInterrupt("primary")
    assert "close-after-release" in " ".join(caught.value.__notes__)
    assert (tmp_path / "lease" / "home" / "foreign").read_bytes() == b"foreign"
    assert fds() == before


def test_late_scratch_file_mutation_during_root_sync_rejects_stale_snapshot(tmp_path, monkeypatch):
    with lease(tmp_path) as scratch:
        repo = tmp_path / "lease" / "repo"
        repo.mkdir(mode=0o700)
        file = repo / "one"
        file.write_bytes(b"synthetic")
        original = os.fsync
        seen = []
        def sync(fd):
            result = original(fd)
            if fd == scratch.fd and not seen:
                seen.append(True)
                file.write_bytes(b"foreign longer bytes")
            return result
        monkeypatch.setattr(os, "fsync", sync)
        with pytest.raises(r.RuntimeBlocked, match="drift"):
            scratch.snapshot(durable=True)
        assert seen == [True] and file.read_bytes() == b"foreign longer bytes"


def test_scratch_home_extra_is_unresolved_and_retained(tmp_path):
    with lease(tmp_path) as scratch:
        extra = tmp_path / "lease" / "home" / "foreign"
        extra.write_bytes(b"foreign")
        with pytest.raises(r.RuntimeBlocked):
            scratch.snapshot(durable=True)
        assert extra.read_bytes() == b"foreign"


def test_directory_context_entry_failure_closes_all_owned_descriptors(tmp_path, monkeypatch):
    before = fds()
    scratch = lease(tmp_path)
    (tmp_path / "lease").chmod(0o755)
    with pytest.raises(r.RuntimeBlocked):
        with scratch:
            pytest.fail("entered drifted lease")
    assert fds() == before


def catalog(root, names):
    return {"schema_version": "norspan_jpc_custody_catalog_v1", "lineage_sha256": "c" * 64,
            "controls": {name: j.receipt_record(j.create_pair(root / name, b"synthetic", mode=0o644)) for name in names}}


def recover(root, expected):
    digest = hashlib.sha256(r.canonical_bytes(expected)).hexdigest()
    return r.recover_current_custody(root, expected, expected_catalog_sha256=digest, lineage_sha256="c" * 64)


@pytest.mark.parametrize("names, expected_kind", [(["acquisition_entry.json", "pre_network_ready.json"], "prestart_current_custody"), (["network_started.json", "source_acquisition.json"], "terminal_current_custody")])
def test_explicit_recovery_is_current_opaque_custody_never_repeated_work(tmp_path, names, expected_kind):
    expected = catalog(tmp_path, names)
    before = fds()
    result = recover(tmp_path, expected)
    assert result["status"] == expected_kind
    assert result["source_operations"] == 0 and result["model_operations"] == 0
    assert result["historical_producer_success_inferred"] is False
    assert result["source_work_authorized"] is False
    assert fds() == before


@pytest.mark.parametrize("kind", ["incomplete", "malformed", "started_stage", "started_final", "catalog_digest", "lineage", "extra"])
def test_recovery_unresolved_or_untrusted_never_recreates_or_replays(tmp_path, kind):
    expected = catalog(tmp_path, ["acquisition_entry.json", "pre_network_ready.json"])
    if kind == "incomplete":
        (tmp_path / ".foreign.stage").write_bytes(b"partial")
    elif kind == "malformed":
        expected["controls"]["pre_network_ready.json"]["inode"] = True
    elif kind == "started_stage":
        (tmp_path / ".network_started.json.stage").write_bytes(b"partial")
    elif kind == "started_final":
        j.create_pair(tmp_path / "network_started.json", b"synthetic", mode=0o644)
    elif kind == "extra":
        (tmp_path / "foreign").write_bytes(b"foreign")
    elif kind == "lineage":
        expected["lineage_sha256"] = "d" * 64
    names = set(os.listdir(tmp_path))
    before = fds()
    with pytest.raises((r.RuntimeBlocked, j.PairFailure)):
        if kind == "catalog_digest":
            r.recover_current_custody(tmp_path, expected, expected_catalog_sha256="0" * 64, lineage_sha256="c" * 64)
        else:
            recover(tmp_path, expected)
    assert set(os.listdir(tmp_path)) == names and fds() == before
