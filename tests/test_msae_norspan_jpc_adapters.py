"""Actual publication adapters and production entry guards, synthetic data only."""
from __future__ import annotations

import json
import ast
import os
from pathlib import Path
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import acquire_msae_independent_norspan_v1 as acquisition
import prepare_msae_independent_norspan_v1 as protocol
import msae_jumbo_pair_commit as j
import msae_norspan_jpc_runtime as r

ROOT = Path(__file__).resolve().parents[1]


def test_actual_public_control_publisher_retains_pair(tmp_path, monkeypatch):
    monkeypatch.setattr(protocol, "ROOT", tmp_path)
    record = {"scope": "fresh synthetic control, not scientific evidence"}
    public = tmp_path / "public"
    public.mkdir(mode=0o755)
    public.chmod(0o755)  # observed Jumbo default ACL may narrow mkdir permissions
    receipt = protocol.publish_json(public / "control.json", record)
    assert receipt.mode == 0o644
    assert j.verify_pair(public / "control.json", receipt, durable=True) == receipt
    assert json.loads((public / "control.json").read_bytes()) == record
    assert set(os.listdir(public)) == {"control.json", ".control.json.stage"}


def test_actual_raw_adapter_has_eight_names_and_external_manifest(tmp_path, monkeypatch):
    monkeypatch.setattr(protocol, "ROOT", tmp_path)
    manifest = protocol.publish_flat_directory(tmp_path / "raw", {str(i): b"synthetic" for i in range(4)},
                                               directory_mode=0o555, file_mode=0o444)
    assert len(os.listdir(tmp_path / "raw")) == 8
    assert r.verify_flat_pairs(tmp_path / "raw", manifest, directory_mode=0o555, file_mode=0o444) == manifest


def test_actual_private_adapter_retains_distinct_role_writer_pairs(tmp_path, monkeypatch):
    monkeypatch.setattr(protocol, "ROOT", tmp_path)
    monkeypatch.setattr(protocol, "DATA", tmp_path / "data")
    monkeypatch.setattr(protocol, "PRIVATE", tmp_path / "data" / "private")
    roles = {role: [] for role in r.ROLES}
    result = protocol.publish_private_roles(roles)
    expected = {role: {k: v for k, v in item.items() if k in {"sha256", "bytes", "mode", "nlink", "pair"}}
                for role, item in result.items()}
    assert all(item["record_count"] == 0 and item["scientific_open_count"] == 0 for item in result.values())
    assert r.verify_role_pairs(protocol.PRIVATE, expected) == expected


@pytest.mark.parametrize("name", ["cmd_build_history", "cmd_build_authority", "cmd_prepare", "cmd_verify", "acquire"])
def test_real_entrypoints_block_before_any_state_or_evidence_access(monkeypatch, name):
    def forbidden(*args, **kwargs):
        pytest.fail("entrypoint touched real state before pending qualification guard")
    for helper in ["classify_protocol_state", "evidence_snapshot", "build_history_registry", "validate_authority_chain"]:
        monkeypatch.setattr(protocol, helper, forbidden)
    with pytest.raises(protocol.GateFailure, match="jpc_whole_qualification_pending"):
        if name == "acquire":
            acquisition.acquire("a" * 64)
        else:
            getattr(protocol, name)(None)


def test_runner_has_no_initiated_cleanup_or_default_temporary_placement():
    source = (ROOT / "scripts/acquire_msae_independent_norspan_v1.py").read_text()
    tree = ast.parse(source)
    forbidden = {"cleanup_scratch", "remove_tree_fd", "mkdtemp", "unlink", "rmdir", "rename", "replace"}
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            name = node.func.id if isinstance(node.func, ast.Name) else getattr(node.func, "attr", None)
            assert name not in forbidden
    assert "cleanup_verified" not in source
    assert "tempfile" not in source


def test_runner_static_prestart_scratch_binding_precedes_first_subprocess():
    source = (ROOT / "scripts/acquire_msae_independent_norspan_v1.py").read_text()
    reserve = source.index("with jpc_runtime.reserve_scratch(")
    inner = source.index("def _acquire_in_reserved_scratch(")
    start = source.index('protocol.publish_json(protocol.PROV / "network_started.json"', inner)
    spawn = source.index("stdout, stderr, code = run(", inner)
    assert reserve < inner < start < spawn
    prefix = source[inner:start]
    assert '"scratch_binding": dict(lease.binding)' in prefix
    assert prefix.count("lease.validate_pristine()") == 2
    # Structural evidence only. Actual phase-schema/history/authority replay and
    # fake-Git whole-state success/rejection/interrupt matrices remain required.


@pytest.mark.parametrize("error", [OSError, KeyboardInterrupt])
def test_actual_public_adapter_parent_close_error_closes_chain_no_publication(tmp_path, monkeypatch, error):
    monkeypatch.setattr(protocol, "ROOT", tmp_path)
    public = tmp_path / "public"
    public.mkdir(mode=0o755)
    public.chmod(0o755)
    before = set(os.listdir("/proc/self/fd"))
    close = os.close
    monitor = os.stat('/proc/self/fd')
    open_parent = protocol._open_parent_fd
    target = []
    def parent(*args, **kwargs):
        result = open_parent(*args, **kwargs)
        target.append(result.descriptors[-1])
        return result
    monkeypatch.setattr(protocol, "_open_parent_fd", parent)
    seen = []; monitors = []; fired = []
    def fault(fd):
        observed = os.fstat(fd)
        close(fd)
        if (observed.st_dev,observed.st_ino)==(monitor.st_dev,monitor.st_ino):
            monitors.append(fd)
            return
        seen.append(fd)
        if target and fd == target[0]:
            fired.append(fd)
            raise error("parent-close-after-release")
    monkeypatch.setattr(os, "close", fault)
    with pytest.raises(error, match="parent-close-after-release"):
        protocol.publish_json(public / "control.json", {"synthetic": True})
    assert len(seen) == len(set(seen))
    assert monitors and fired == [target[0]]
    assert set(os.listdir("/proc/self/fd")) == before
    assert not list(public.iterdir())
