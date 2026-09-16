from __future__ import annotations

import array
import importlib.util
import importlib._bootstrap_external
import builtins
import inspect
import hashlib
import json
import os
from pathlib import Path
import stat
import signal
import selectors
import socket
import copy
import subprocess
import sys
import time
import types
import base64
import contextlib

import pytest

ROOT = Path(__file__).resolve().parents[1]
for _local_module in (
    "msae_independent_measurement_v3", "msae_independent_measurement_v3_post_m1",
    "msae_independent_measurement_v3_post_m1_runtime",
    "msae_independent_measurement_v3_post_m2_gen9",
    "msae_independent_measurement_v3_post_m2_gen9_runtime",
    "msae_measurement_remediation_v1", "msae_measurement_v2",
    "run_msae_independent_calibration_v3", "run_msae_independent_calibration_v3_gen9",
):
    sys.modules.pop(_local_module, None)
_controller_path = ROOT / "scripts/msae_independent_measurement_v3_post_m2_gen9.py"
_controller = types.ModuleType("msae_independent_measurement_v3_post_m2_gen9")
_controller.__file__ = str(_controller_path)
_controller.__package__ = None
sys.modules[_controller.__name__] = _controller
exec(compile(_controller_path.read_bytes(), str(_controller_path), "exec"), _controller.__dict__)
SPEC = _controller.source_only_module_spec(
    "msae_v3_post_m2_runtime",
    ROOT / "scripts/msae_independent_measurement_v3_post_m2_gen9_runtime.py")
assert SPEC and SPEC.loader
runtime = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(runtime)


def test_gen9_reviewed_authority_constants_and_public_entry_are_exact():
    assert runtime.FROZEN_PLAN_SHA256 == \
        "7bd04a1c466d6a7e5cd6e570eece4e9a19395bf90d5b1e7cf2e4486616c2dfb4"
    assert runtime.FROZEN_PLAN_REVIEW_SHA256 == \
        "1a7dd1752694599322c80ad2d7e7bd03d306f7d618198a4cc6cd25a8f72720b1"
    entries = runtime.PUBLIC_EXECUTION_ENTRYPOINTS
    assert entries.count("build_changed_regions") == 1
    assert entries.index("build_changed_regions") + 1 == \
        entries.index("probe_gen9_capability")
    assert runtime.GEN9_SUBSTITUTIONS == (
        (b"post_m7_gen7", b"post_m9_gen9"),
        (b"post-m7-gen7", b"post-m9-gen9"),
        (b"msae-independent-v3-gen7", b"msae-independent-v3-gen9"),
        (b"m7t_", b"m9t_"), (b"m7b_", b"m9b_"),
        (b"m7p_", b"m9p_"), (b"m7x_", b"m9x_"),
        (b"m7a_", b"m9a_"), (b"m7c_", b"m9c_"),
        (b"m7s_", b"m9s_"),
        (b"Gen7", b"Gen9"), (b"gen7", b"gen9"),
    )
    runtime._require_exact_command_shape([
        "build-changed-regions", "--output", str(runtime.CHANGE_MANIFEST)])
    with pytest.raises(ValueError, match="output|shape|order"):
        runtime._require_exact_command_shape([
            "build-changed-regions", "--output", "changed_regions.json"])


def test_gen9_changed_region_manifest_is_structural_and_rejects_unregistered_drift(
        tmp_path):
    manifest = runtime._gen7_to_gen9_change_manifest()
    assert set(manifest) == {
        "schema_version", "baseline_subjects", "candidate_subjects",
        "policy", "rows", "manifest_sha256_excluded",
    }
    assert manifest["schema_version"] == "msae_v3_gen9_changed_regions_v1"
    assert manifest["manifest_sha256_excluded"] is True
    assert manifest == runtime._gen7_to_gen9_change_manifest()
    assert all(set(row) == {
        "path", "node_kind", "qualified_name", "occurrence",
        "old_start", "old_end", "new_start", "new_end",
        "old_sha256", "new_sha256", "region_id",
    } for row in manifest["rows"])
    assert manifest["rows"] == sorted(
        manifest["rows"], key=lambda row: (row["path"], row["new_start"]))

    relatives = (
        "scripts/msae_independent_measurement_v3_post_m2_gen9.py",
        "scripts/msae_independent_measurement_v3_post_m2_gen9_runtime.py",
        "scripts/run_msae_independent_calibration_v3_gen9.py",
        "scripts/launch_msae_independent_calibration_v3_gen9.sh",
        "scripts/run_msae_independent_measurement_v3_post_m2_gen9_tmux_test.py",
        "docs/rfc-msae-independent-measurement-v3-post-m9-gen9.md",
        "tests/test_msae_independent_measurement_v3_post_m9_gen9.py",
    )
    candidate = tmp_path / "candidate"
    for relative in relatives:
        source = runtime.ROOT / relative
        target = candidate / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(source.read_bytes())
        target.chmod(stat.S_IMODE(source.stat().st_mode))
    controller = candidate / relatives[0]
    controller.write_bytes(controller.read_bytes() + b"\n# unregistered drift\n")
    with pytest.raises(ValueError, match="byte-identical|outside allowed"):
        runtime._gen7_to_gen9_change_manifest(root=candidate)


def test_gen9_changed_region_rows_bind_new_nodes_and_reject_unknown_nodes():
    baseline = b"VALUE = 1\n\ndef keep():\n    return 1\n"
    candidate = (
        b"VALUE = 2\n\n"
        b"def allowed_new():\n    return 3\n\n"
        b"def keep():\n    return 1\n")
    rows = runtime._gen9_changed_region_rows(
        "fixture.py", baseline, candidate,
        allowed_assignments={"VALUE": "R9_CONSTANTS"},
        allowed_definitions={"allowed_new": "R9_CHANGE_POLICY"},
    )
    assert [(row["qualified_name"], row["region_id"]) for row in rows] == [
        ("VALUE", "R9_CONSTANTS"),
        ("allowed_new", "R9_CHANGE_POLICY"),
    ]
    bad = candidate.replace(b"return 1", b"return 9")
    with pytest.raises(ValueError, match="outside allowed"):
        runtime._gen9_changed_region_rows(
            "fixture.py", baseline, bad,
            allowed_assignments={"VALUE": "R9_CONSTANTS"},
            allowed_definitions={"allowed_new": "R9_CHANGE_POLICY"},
        )


def test_changed_regions_descriptor_embeds_exact_reconstructable_manifest():
    manifest = runtime._gen7_to_gen9_change_manifest()
    descriptor = runtime._changed_regions_transaction_descriptor(manifest)
    assert set(descriptor) == {
        "schema_version", "plan_sha256", "plan_review_sha256",
        "implementation_entries", "manifest", "manifest_sha256", "argv",
        "python_argv", "cwd", "environment", "status",
    }
    assert descriptor["schema_version"] == \
        "msae_v3_gen9_changed_regions_transaction_v1"
    assert descriptor["status"] == "prepared"
    assert descriptor["manifest"] == manifest
    assert descriptor["manifest_sha256"] == runtime.base.sha_bytes(
        runtime.base.canonical_bytes(manifest))
    runtime._validate_changed_regions_transaction(descriptor)
    tampered = copy.deepcopy(descriptor)
    tampered["manifest"]["manifest_sha256_excluded"] = False
    with pytest.raises(ValueError, match="manifest|descriptor"):
        runtime._validate_changed_regions_transaction(tampered)


def test_changed_regions_publisher_round_trip_uses_recoverable_nfs_transaction(
        monkeypatch):
    root = runtime.NFS_PUBLISHER_TEST_ROOT
    assert not (root.exists() or root.is_symlink())
    root.mkdir(mode=0o700); root.chmod(0o700)
    runtime.base._fsync_directory(root.parent)
    analysis = root / "analysis"
    manifest_path = analysis / "changed_regions.json"
    transaction = analysis / ".changed_regions_transaction"
    monkeypatch.setattr(runtime, "CONTAINMENT_ANALYSIS_ROOT", analysis)
    monkeypatch.setattr(runtime, "CAPABILITY_ANALYSIS_ROOT", analysis)
    monkeypatch.setattr(runtime, "CHANGE_MANIFEST", manifest_path)
    monkeypatch.setattr(runtime, "CHANGE_MANIFEST_TRANSACTION", transaction)
    try:
        manifest = runtime._gen7_to_gen9_change_manifest()
        assert runtime._publish_changed_regions(manifest) == manifest
        assert runtime._regular_bytes(manifest_path, mode=0o600) == \
            runtime.base.canonical_bytes(manifest)
        assert not (transaction.exists() or transaction.is_symlink())
        assert runtime._publish_changed_regions(manifest) == manifest
    finally:
        _remove_owned_test_root(root)
    assert not (root.exists() or root.is_symlink())


def test_review_control_parser_requires_exact_contiguous_block_and_rows(tmp_path):
    check = {
        "schema_version": "msae_v3_gen9_review_check_v1", "id": "fixture",
        "subject_sha256": "a" * 64, "argv": ["/usr/bin/true"],
        "cwd": str(runtime.ROOT), "environment": {"LANG": "C"},
        "started_utc": "2026-08-21T00:00:00Z",
        "ended_utc": "2026-08-21T00:00:01Z", "exit_code": 0,
        "stdout_sha256": runtime.base.sha_bytes(b""),
        "stderr_sha256": runtime.base.sha_bytes(b""), "summary": "pass",
    }
    rows_sha = runtime.base.sha_bytes(runtime.base.canonical_bytes([check]))
    controls = {
        "VERDICT": "SHIP", "REVIEW_SCOPE": "fixture",
        "PLAN_SHA256": "b" * 64, "CHECKS_SHA256": rows_sha,
        "CHECK_COUNT": "1",
    }
    path = tmp_path / "review.md"
    lines = [*(f"{key}: {value}" for key, value in controls.items()),
             "CHECK_ROW_JSON: " + runtime.base.canonical_bytes(check).decode().rstrip(),
             "", "prose"]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    path.chmod(0o644)
    parsed = runtime._review_control_lines(
        path, scope="fixture", expected_controls=controls)
    assert runtime._review_check_rows(parsed, expected_count=1) == [check]
    path.write_text(path.read_text().replace(
        "prose", "PLAN_SHA256: " + "c" * 64), encoding="utf-8")
    with pytest.raises(ValueError, match="control"):
        runtime._review_control_lines(
            path, scope="fixture", expected_controls=controls)


def test_failed_gen7_payload_is_honest_typed_and_independently_reconstructed():
    with runtime.quarantine_guard() as tripwire:
        payload = runtime._failed_gen7_terminal_payload()
        verified = runtime._verify_failed_gen7_terminal_payload(payload)
    assert tripwire["blocked_content_open_attempts"] == []
    assert verified == payload
    assert set(payload) == {
        "schema_version", "protocol_id", "generation", "writer_generation",
        "status", "terminal_fields", "frozen_subject", "failure_review",
        "blockers", "checks", "namespace_absence",
        "sealed_payload_metadata", "gen9_plan_authority",
    }
    assert payload["status"] == "failed_before_capability"
    assert payload["failure_review"]["verdict"] == "BLOCK"
    assert payload["failure_review"]["blocker_count"] == 4
    assert [row["ordinal"] for row in payload["blockers"]] == [1, 2, 3, 4]
    assert [row["severity"] for row in payload["blockers"]] == [
        "critical", "critical", "high", "high"]
    assert len(payload["frozen_subject"]) == 10
    assert all(row["expected"] == "absent" and row["lexists"] is False
               for row in payload["namespace_absence"])
    sealed = payload["sealed_payload_metadata"]
    assert sealed["content_read_attempts"] == 0
    assert sealed["before"] == sealed["after"]
    assert set(sealed["before"]) == set(runtime.base.QUARANTINED)

    tampered = copy.deepcopy(payload)
    tampered["blockers"][0]["one_line"] += " altered"
    with pytest.raises(ValueError, match="failed-gen7"):
        runtime._verify_failed_gen7_terminal_payload(tampered)


def test_containment_attempt_and_case_journal_schemas_are_exact():
    descriptor = runtime._containment_attempt_descriptor(
        "a" * 64, started_utc="2026-08-21T01:02:03Z")
    assert set(descriptor) == {
        "schema_version", "test_token", "plan_sha256", "plan_review_sha256",
        "pre_containment_review_sha256", "implementation_entries", "command",
        "python_argv", "environment", "cases", "started_utc", "status",
    }
    assert descriptor["schema_version"] == "msae_v3_gen9_containment_attempt_v1"
    assert descriptor["status"] == "started"
    assert [row["case_id"] for row in descriptor["cases"]] == [
        f"C{index:02d}" for index in range(10)]
    assert descriptor["command"][:2] == ["/usr/bin/env", "-i"]
    assert descriptor["python_argv"][0] == str(runtime.ROOT / ".venv-atlas/bin/python")

    launcher = {
        "schema_version": "msae_v3_gen9_process_v1", "role": "launcher",
        "pid": 1234, "start_ticks": 5678, "ppid": 1000, "pgid": 1234,
        "uid": os.getuid(), "gid": os.getgid(),
    }
    start = runtime._containment_case_start(
        descriptor, "C00", launcher=launcher,
        paths={"scratch": "/tmp/m9s_fixture"},
        started_monotonic_ns=100, started_utc="2026-08-21T01:02:04Z",
        outer_deadline_monotonic_ns=24_000_000_100)
    assert set(start) == {
        "schema_version", "test_token", "case_id", "launcher", "paths",
        "started_monotonic_ns", "started_utc", "outer_deadline_monotonic_ns",
        "status",
    }
    assert start["status"] == "started"


def test_containment_pass_report_requires_complete_ordered_cases_and_zero_tripwires():
    descriptor = runtime._containment_attempt_descriptor(
        "a" * 64, started_utc="2026-08-21T01:02:03Z")
    case_results = []
    outer_results = []
    for index in range(10):
        case_id = f"C{index:02d}"
        boundary = {"schema_version": "fixture-boundary-v1", "case_id": case_id}
        before = {"schema_version": "msae_v3_gen9_outer_before_v1",
                  "case_id": case_id}
        action = {"schema_version": "msae_v3_gen9_outer_action_v1",
                  "case_id": case_id}
        owner = {"schema_version": "fixture-owner-ledger-v1", "case_id": case_id}
        outer = {
            "schema_version": "msae_v3_gen9_case_outer_result_v1",
            "case_id": case_id, "before": before, "action": action,
            "owner_ledger_sha256": runtime.base.sha_bytes(
                runtime.base.canonical_bytes(owner)),
            "processes_extinct": True, "groups_empty": True,
            "session_absent": True, "socket_paths_absent": True,
            "scratch_entries": [], "lease_reacquired": True,
            "tripwires": {
                "schema_version": "msae_v3_gen9_tripwire_counts_v1",
                "gpu_query": 0, "model_import": 0, "model_call": 0,
                "sealed_open": 0, "unregistered_process": 0,
                "environment_activation": 0},
            "emergency_cleanup_used": False, "outcome": "pass",
        }
        result = runtime._containment_case_result(
            case_id=case_id, boundary_event=boundary, before=before,
            action=action, owner_ledger=owner, outer_result=outer,
            ended_utc=f"2026-08-21T01:02:{10 + index:02d}Z")
        case_results.append(result); outer_results.append(outer)
    report = {
        "schema_version": "msae_v3_gen9_tmux_containment_v1",
        "terminal_variant": "pass", "plan_sha256": runtime.FROZEN_PLAN_SHA256,
        "plan_review_sha256": runtime.FROZEN_PLAN_REVIEW_SHA256,
        "pre_containment_review_sha256": "a" * 64,
        "implementation_entries": descriptor["implementation_entries"],
        "command": descriptor["command"], "python_argv": descriptor["python_argv"],
        "environment": descriptor["environment"], "case_results": case_results,
        "outer_results": outer_results, "interruption": None, "failure": None,
        "tripwires": {
            "schema_version": "msae_v3_gen9_tripwire_counts_v1",
            "gpu_query": 0, "model_import": 0, "model_call": 0,
            "sealed_open": 0, "unregistered_process": 0,
            "environment_activation": 0},
        "started_utc": descriptor["started_utc"],
        "ended_utc": "2026-08-21T01:03:00Z", "overall_pass": True,
    }
    assert runtime._validate_containment_report(report) == report
    report["case_results"] = report["case_results"][:-1]
    report["outer_results"] = report["outer_results"][:-1]
    with pytest.raises(ValueError, match="containment.*case|pass"):
        runtime._validate_containment_report(report)


def _remove_owned_test_root(root: Path) -> None:
    """No-follow cleanup limited to an exact registered test root."""
    if not (root.exists() or root.is_symlink()):
        return
    st = root.lstat()
    assert stat.S_ISDIR(st.st_mode) and not stat.S_ISLNK(st.st_mode)
    assert st.st_uid == os.getuid()
    deadline = time.monotonic() + 3.0
    while True:
        retry = False
        for child in sorted(root.rglob("*"), reverse=True):
            try:
                child_st = child.lstat()
            except FileNotFoundError:
                retry = True
                break
            assert not stat.S_ISLNK(child_st.st_mode)
            try:
                if stat.S_ISDIR(child_st.st_mode):
                    child.rmdir()
                else:
                    child.unlink()
            except FileNotFoundError:
                retry = True
                break
            except OSError as error:
                if (error.errno == runtime.errno.EBUSY
                        and child.name.startswith(".nfs")
                        and time.monotonic() < deadline):
                    retry = True
                    break
                raise
        if not retry:
            break
        time.sleep(0.02)
    while True:
        try:
            root.rmdir()
            break
        except OSError as error:
            remaining = []
            with contextlib.suppress(FileNotFoundError):
                remaining = [entry.name for entry in os.scandir(root)]
            if (error.errno not in {runtime.errno.EBUSY, runtime.errno.ENOTEMPTY}
                    or any(not name.startswith(".nfs") for name in remaining)
                    or time.monotonic() >= deadline):
                raise
            time.sleep(0.02)
    runtime.base._fsync_directory(root.parent)


def test_nfs_publisher_fault_matrix():
    root = runtime.NFS_PUBLISHER_TEST_ROOT
    assert not (root.exists() or root.is_symlink())
    root.mkdir(mode=0o700)
    root.chmod(0o700)
    runtime.base._fsync_directory(root.parent)
    def reset_root():
        _remove_owned_test_root(root)
        assert not (root.exists() or root.is_symlink())
        root.mkdir(mode=0o700); root.chmod(0o700)
        runtime.base._fsync_directory(root.parent)
    try:
        mount = runtime._mount_identity(root)
        assert mount["filesystem_magic"] == "0x6969"
        assert mount["mountinfo"] == runtime._mount_identity(runtime.ROOT)["mountinfo"]

        # The first case is deliberately uninjected and observes the real
        # server's link state before production cleanup.
        raw = runtime.base.canonical_bytes({
            "schema_version": "msae_v3_gen9_publisher_baseline_v1"})
        row = runtime._publication_row(
            0, root, "source.payload", root, "destination.json",
            raw, 0o600, "publisher_test_baseline")
        descriptor = runtime._link_transaction_payload(
            kind="capability", authority_sha256="a" * 64,
            publications=[row], maximum_seconds=300)
        runtime._bootstrap_link_transaction(root, descriptor)
        observed_pair = []
        def observed_real_link(source_fd, source, destination_fd, destination):
            runtime._linkat(source_fd, source, destination_fd, destination)
            left = os.stat(source, dir_fd=source_fd, follow_symlinks=False)
            right = os.stat(destination, dir_fd=destination_fd,
                            follow_symlinks=False)
            observed_pair.append((left.st_dev, left.st_ino, left.st_nlink,
                                  right.st_dev, right.st_ino,
                                  right.st_nlink))
        outcome = runtime._link_publication(
            descriptor, row, raw, descriptor_path=root / "transaction.json",
            link_function=observed_real_link)
        assert outcome["status"] == "published"
        assert observed_pair
        left_dev, left_ino, left_links, right_dev, right_ino, right_links = \
            observed_pair[0]
        assert (left_dev, left_ino) == (right_dev, right_ino)
        assert left_links == right_links == 2
        assert (root / "destination.json").read_bytes() == raw
        assert (root / "destination.json").stat().st_nlink == 1
        assert not (root / "source.payload").exists()
        reset_root()

        # The descriptor bootstrap has its own recovery authority and fault
        # matrix.  Exercise its exact source/final names rather than relying on
        # the later generic-payload cases to stand in for bootstrap coverage.
        bootstrap_descriptor = runtime._link_transaction_payload(
            kind="capability", authority_sha256="b" * 64,
            publications=[], maximum_seconds=300)
        bootstrap_raw = runtime.base.canonical_bytes(bootstrap_descriptor)

        def bootstrap_objects():
            source = root / ".transaction.json.bootstrap"
            final = root / "transaction.json"
            row = runtime._publication_row(
                0, root, source.name, root, final.name,
                bootstrap_raw, 0o600, "transaction_descriptor")
            authority = {**bootstrap_descriptor, "publications": [row]}
            return source, final, row, authority

        def write_bootstrap_source():
            source, _final, _row, _authority = bootstrap_objects()
            directory_fd = os.open(
                root, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
            try:
                runtime._write_file_at(
                    directory_fd, source.name, bootstrap_raw, 0o600)
            finally:
                os.close(directory_fd)

        # source-only
        source, final, _row, _authority = bootstrap_objects()
        write_bootstrap_source()
        assert source.stat().st_nlink == 1 and not final.exists()
        runtime._bootstrap_link_transaction(root, bootstrap_descriptor)
        assert final.read_bytes() == bootstrap_raw and final.stat().st_nlink == 1
        assert not source.exists()
        reset_root()

        # exact pair
        source, final, _row, _authority = bootstrap_objects()
        write_bootstrap_source(); os.link(source, final, follow_symlinks=False)
        assert source.stat().st_nlink == final.stat().st_nlink == 2
        runtime._bootstrap_link_transaction(root, bootstrap_descriptor)
        assert final.stat().st_nlink == 1 and not source.exists()
        reset_root()

        # destination-only, including a legal crash-left attempt marker.
        source, final, _row, _authority = bootstrap_objects()
        directory_fd = os.open(root, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
        try:
            runtime._write_file_at(directory_fd, final.name, bootstrap_raw, 0o600)
        finally:
            os.close(directory_fd)
        marker = root / ".transaction.json.attempt-1"
        marker.mkdir(mode=0o700); marker.chmod(0o700)
        runtime.base._fsync_directory(root)
        runtime._bootstrap_link_transaction(root, bootstrap_descriptor)
        assert final.stat().st_nlink == 1 and not marker.exists()
        reset_root()

        # Every write/link/fsync/unlink boundary either leaves an exact legal
        # prefix which the next production call consumes, or a bounded partial
        # write which is retained and rejected without interpretation.
        real_write, real_fsync = runtime.os.write, runtime.os.fsync
        real_unlink, real_linkat = runtime.os.unlink, runtime._linkat

        def run_boundary(boundary):
            source, final, _row, _authority = bootstrap_objects()
            triggered = False

            def injected_write(fd, value):
                nonlocal triggered
                if boundary == "partial_write" and not triggered:
                    triggered = True
                    real_write(fd, memoryview(value)[:max(1, len(value) // 2)])
                    raise OSError(runtime.errno.EIO, boundary)
                return real_write(fd, value)

            def injected_fsync(fd):
                nonlocal triggered
                held = os.fstat(fd)
                root_fd = stat.S_ISDIR(held.st_mode) and held.st_ino == root.stat().st_ino
                source_present = source.exists()
                final_present = final.exists()
                pair = (source_present and final_present
                        and source.stat().st_nlink == final.stat().st_nlink == 2)
                marker_present = any(root.glob(".transaction.json.attempt-*"))
                marker_inodes = {
                    path.stat().st_ino
                    for path in root.glob(".transaction.json.attempt-*")}
                should_fail = (
                    boundary == "file_fsync" and stat.S_ISREG(held.st_mode)
                    or boundary == "source_parent_fsync_before_link" and root_fd
                       and source_present and not final_present and not marker_present
                    or boundary == "attempt_marker_fsync"
                       and stat.S_ISDIR(held.st_mode)
                       and held.st_ino in marker_inodes
                    or boundary == "source_parent_fsync_after_marker" and root_fd
                       and source_present and not final_present and marker_present
                    or boundary == "destination_parent_fsync" and root_fd and pair
                    or boundary == "source_parent_fsync_after_unlink" and root_fd
                       and not source_present and final_present and marker_present)
                if should_fail and not triggered:
                    triggered = True
                    raise OSError(runtime.errno.EIO, boundary)
                return real_fsync(fd)

            def injected_linkat(source_fd, source_name,
                                destination_fd, destination_name):
                nonlocal triggered
                real_linkat(source_fd, source_name,
                            destination_fd, destination_name)
                if boundary == "link" and not triggered:
                    triggered = True
                    raise RuntimeError(boundary)

            def injected_unlink(name, *args, **kwargs):
                nonlocal triggered
                result = real_unlink(name, *args, **kwargs)
                if (boundary == "unlink" and not triggered
                        and name == source.name):
                    triggered = True
                    raise OSError(runtime.errno.EIO, boundary)
                return result

            with pytest.MonkeyPatch.context() as patcher:
                patcher.setattr(runtime.os, "write", injected_write)
                patcher.setattr(runtime.os, "fsync", injected_fsync)
                patcher.setattr(runtime.os, "unlink", injected_unlink)
                patcher.setattr(runtime, "_linkat", injected_linkat)
                with pytest.raises((OSError, RuntimeError), match=boundary):
                    runtime._bootstrap_link_transaction(
                        root, bootstrap_descriptor)
            assert triggered
            if boundary == "partial_write":
                with pytest.raises(ValueError, match="source-only bytes drift"):
                    runtime._bootstrap_link_transaction(
                        root, bootstrap_descriptor)
            else:
                runtime._bootstrap_link_transaction(root, bootstrap_descriptor)
                assert final.read_bytes() == bootstrap_raw
                assert final.stat().st_nlink == 1
                assert not source.exists()
                assert not list(root.glob(".transaction.json.attempt-*"))
            reset_root()

        for boundary in (
            "partial_write", "file_fsync", "source_parent_fsync_before_link",
            "attempt_marker_fsync", "source_parent_fsync_after_marker",
            "link", "destination_parent_fsync", "unlink",
            "source_parent_fsync_after_unlink",
        ):
            run_boundary(boundary)

        # Three source-only results consume the complete durable bootstrap
        # attempt budget.  Expiry permits neither a fourth marker nor a link;
        # an already-created exact pair still completes and removes the source
        # followed by markers 3, 2, 1.
        source, final, row, authority = bootstrap_objects()
        link_calls = 0
        def fail_bootstrap_link(*_args):
            nonlocal link_calls
            link_calls += 1
            raise OSError(runtime.errno.EIO, "bootstrap source-only")
        for expected in range(1, 4):
            with pytest.raises(runtime.RecoverableLinkInterruption):
                runtime._link_publication(
                    authority, row, bootstrap_raw, descriptor_path=None,
                    link_function=fail_bootstrap_link)
            assert [path.name for path in sorted(
                root.glob(".transaction.json.attempt-*"))] == [
                    f".transaction.json.attempt-{index}"
                    for index in range(1, expected + 1)]
        with pytest.raises(ValueError, match="attempt budget exhausted"):
            runtime._link_publication(
                authority, row, bootstrap_raw, descriptor_path=None,
                link_function=fail_bootstrap_link)
        assert link_calls == 3
        expired = float(authority["recovery_deadline_unix"]) + 1
        with pytest.raises(ValueError, match="deadline expired"):
            runtime._link_publication(
                authority, row, bootstrap_raw, descriptor_path=None,
                link_function=fail_bootstrap_link, now=expired)
        assert link_calls == 3
        real_rmdir = runtime.os.rmdir
        for reverse_target in (3, 2, 1):
            if reverse_target != 3:
                source, final, row, authority = bootstrap_objects()
                write_bootstrap_source()
                for index in range(1, 4):
                    attempt = root / f".transaction.json.attempt-{index}"
                    attempt.mkdir(mode=0o700); attempt.chmod(0o700)
                runtime.base._fsync_directory(root)
            os.link(source, final, follow_symlinks=False)
            removal_order = []
            reverse_triggered = False
            def observed_unlink(name, *args, **kwargs):
                removal_order.append(("unlink", name))
                return real_unlink(name, *args, **kwargs)
            def observed_rmdir(name, *args, **kwargs):
                removal_order.append(("rmdir", name))
                return real_rmdir(name, *args, **kwargs)
            def fail_reverse_parent_fsync(fd):
                nonlocal reverse_triggered
                if (not reverse_triggered
                        and removal_order
                        and removal_order[-1] == (
                            "rmdir", f".transaction.json.attempt-{reverse_target}")
                        and stat.S_ISDIR(os.fstat(fd).st_mode)
                        and os.fstat(fd).st_ino == root.stat().st_ino):
                    reverse_triggered = True
                    raise OSError(runtime.errno.EIO,
                                  f"reverse-marker-{reverse_target}-fsync")
                return real_fsync(fd)
            with pytest.MonkeyPatch.context() as patcher:
                patcher.setattr(runtime.os, "unlink", observed_unlink)
                patcher.setattr(runtime.os, "rmdir", observed_rmdir)
                patcher.setattr(runtime.os, "fsync", fail_reverse_parent_fsync)
                with pytest.raises(
                        OSError,
                        match=f"reverse-marker-{reverse_target}-fsync"):
                    runtime._link_publication(
                        authority, row, bootstrap_raw, descriptor_path=None,
                        now=expired)
            assert reverse_triggered
            with pytest.MonkeyPatch.context() as patcher:
                patcher.setattr(runtime.os, "rmdir", observed_rmdir)
                runtime._link_publication(
                    authority, row, bootstrap_raw, descriptor_path=None,
                    now=expired)
            assert removal_order == [
                ("unlink", source.name),
                ("rmdir", ".transaction.json.attempt-3"),
                ("rmdir", ".transaction.json.attempt-2"),
                ("rmdir", ".transaction.json.attempt-1"),
            ]
            assert final.stat().st_nlink == 1 and not source.exists()
            reset_root()

        # Expiry from a clean source-only state consumes no marker and makes
        # no link call.  This is distinct from the exhausted-budget check.
        source, final, row, authority = bootstrap_objects()
        write_bootstrap_source()
        expired = float(authority["recovery_deadline_unix"]) + 1
        link_calls = 0
        with pytest.raises(ValueError, match="deadline expired"):
            runtime._link_publication(
                authority, row, bootstrap_raw, descriptor_path=None,
                link_function=fail_bootstrap_link, now=expired)
        assert link_calls == 0 and not final.exists()
        assert not list(root.glob(".transaction.json.attempt-*"))
        os.link(source, final, follow_symlinks=False)
        runtime._link_publication(
            authority, row, bootstrap_raw, descriptor_path=None, now=expired)
        assert final.stat().st_nlink == 1 and not source.exists()
        reset_root()

        # Every error leaves an exact source-only technical interruption.  A
        # separate invocation then consumes the next durable marker and
        # converges via the real production linkat path.
        row = runtime._publication_row(
            0, root, "source.payload", root, "destination.json",
            raw, 0o600, "publisher_error_matrix")
        descriptor = runtime._link_transaction_payload(
            kind="capability", authority_sha256="c" * 64,
            publications=[row], maximum_seconds=300)
        runtime._bootstrap_link_transaction(root, descriptor)
        for error_number in (
            runtime.errno.EEXIST, runtime.errno.EXDEV, runtime.errno.EPERM,
            runtime.errno.EACCES, runtime.errno.EOPNOTSUPP,
            runtime.errno.ENOSYS, runtime.errno.EROFS,
        ):
            def fail_link(*_args, _error=error_number):
                raise OSError(_error, os.strerror(_error))
            try:
                runtime._link_publication(
                    descriptor, row, raw,
                    descriptor_path=root / "transaction.json",
                    link_function=fail_link)
            except runtime.RecoverableLinkInterruption:
                pass
            else:
                raise AssertionError("injected source-only result did not interrupt")
            assert (root / "source.payload").stat().st_size == len(raw)
            assert (root / ".destination.json.attempt-1").is_dir()
            # Test-controlled reset makes the errno cases independent; legal
            # retry convergence is exercised by the state-matrix test.
            (root / "source.payload").unlink()
            (root / ".destination.json.attempt-1").rmdir()
            runtime.base._fsync_directory(root)

        # An error reported after the kernel created the hard link is resolved
        # from the exact inode pair, never from errno.
        def link_then_error(source_fd, source, destination_fd, destination):
            runtime._linkat(source_fd, source, destination_fd, destination)
            raise OSError(runtime.errno.ETIMEDOUT, "uncertain NFS result")
        runtime._link_publication(
            descriptor, row, raw, descriptor_path=root / "transaction.json",
            link_function=link_then_error)
        assert (root / "destination.json").read_bytes() == raw
        (root / "destination.json").unlink()
        (root / "transaction.json").unlink()
        runtime.base._fsync_directory(root)
    finally:
        _remove_owned_test_root(root)
    assert not (root.exists() or root.is_symlink())


def test_local_mount_rejection_precedes_protocol_mutation():
    root = runtime.LOCAL_REJECTION_TEST_ROOT
    assert not (root.exists() or root.is_symlink())
    root.mkdir(mode=0o700)
    root.chmod(0o700)
    runtime.base._fsync_directory(root.parent)
    try:
        before = {entry.name for entry in os.scandir(root)}
        assert before == set()
        with pytest.raises(ValueError, match="registered NFS mount identity drift"):
            runtime._require_bound_nfs_mount(
                root, runtime._mount_identity(runtime.ROOT))
        assert {entry.name for entry in os.scandir(root)} == set()
        for name in (
            "transaction.json", ".transaction.json.bootstrap",
            "source.payload", "destination.json",
            ".destination.json.attempt-1",
        ):
            assert not (root / name).exists()
    finally:
        _remove_owned_test_root(root)
    assert not (root.exists() or root.is_symlink())


def test_post_unlink_reader_waits_for_transient_nfs_link_count(tmp_path, monkeypatch):
    payload = tmp_path / "published.json"
    payload.write_bytes(b"published\n"); payload.chmod(0o600)
    directory_fd = os.open(tmp_path, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    original_stat = runtime.os.stat
    calls = 0

    def delayed_stat(path, *args, **kwargs):
        nonlocal calls
        observed = original_stat(path, *args, **kwargs)
        if path == payload.name and calls == 0:
            calls += 1
            fields = list(observed)
            fields[3] = 2
            return os.stat_result(fields)
        calls += 1
        return observed

    monkeypatch.setattr(runtime.os, "stat", delayed_stat)
    try:
        raw, terminal = runtime._file_at_bytes_after_unlink(
            directory_fd, payload.name, mode=0o600,
            expected_identity=(payload.stat().st_dev, payload.stat().st_ino))
    finally:
        os.close(directory_fd)
    assert raw == b"published\n"
    assert terminal.st_nlink == 1
    assert calls >= 2


def test_post_unlink_reader_rejects_same_bytes_inode_substitution(
        tmp_path, monkeypatch):
    payload = tmp_path / "published.json"
    replacement = tmp_path / "replacement.json"
    payload.write_bytes(b"published\n"); payload.chmod(0o600)
    replacement.write_bytes(b"published\n"); replacement.chmod(0o600)
    expected = (payload.stat().st_dev, payload.stat().st_ino)
    directory_fd = os.open(tmp_path, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    original_stat = runtime.os.stat
    calls = 0

    def substituting_stat(path, *args, **kwargs):
        nonlocal calls
        if path == payload.name:
            if calls == 0:
                observed = original_stat(path, *args, **kwargs)
                fields = list(observed); fields[3] = 2; calls += 1
                return os.stat_result(fields)
            if calls == 1:
                payload.unlink(); replacement.rename(payload); calls += 1
        return original_stat(path, *args, **kwargs)

    monkeypatch.setattr(runtime.os, "stat", substituting_stat)
    try:
        with pytest.raises(ValueError, match="post-unlink identity drift"):
            runtime._file_at_bytes_after_unlink(
                directory_fd, payload.name, mode=0o600,
                expected_identity=expected)
    finally:
        os.close(directory_fd)


def test_nfs_publisher_recovery_and_poisoned_state_matrix(monkeypatch):
    """Exercise the registered legal states and representative poison states."""
    root = runtime.NFS_PUBLISHER_TEST_ROOT
    assert not (root.exists() or root.is_symlink())
    root.mkdir(mode=0o700); root.chmod(0o700)
    runtime.base._fsync_directory(root.parent)
    destination_parent = root / "replacement_parent"
    destination_parent.mkdir(mode=0o700); destination_parent.chmod(0o700)
    runtime.base._fsync_directory(root)
    raw = runtime.base.canonical_bytes({"schema_version": "publisher-state-v1"})

    row = runtime._publication_row(
        0, root, "source.payload", destination_parent,
        "destination.json", raw, 0o600, "publisher_state_test")
    descriptor = runtime._link_transaction_payload(
        kind="capability", authority_sha256="c" * 64,
        publications=[row], maximum_seconds=300)
    runtime._bootstrap_link_transaction(root, descriptor)
    bootstrap_marker = root / ".transaction.json.attempt-1"
    bootstrap_marker.mkdir(mode=0o700); bootstrap_marker.chmod(0o700)
    runtime.base._fsync_directory(root)
    runtime._bootstrap_link_transaction(root, descriptor)
    assert not bootstrap_marker.exists()
    assert (root / "transaction.json").is_file()

    def clear_case():
        import gc
        for name in (
            "source.payload", "third_link.json",
            ".destination.json.attempt-1",
            ".destination.json.attempt-2", ".destination.json.attempt-3",
        ):
            path = root / name
            if path.is_dir() and not path.is_symlink(): path.rmdir()
            elif path.exists() or path.is_symlink(): path.unlink()
        destination = destination_parent / "destination.json"
        if destination.exists() or destination.is_symlink(): destination.unlink()
        runtime.base._fsync_directory(destination_parent)
        runtime.base._fsync_directory(root)
        gc.collect()
        deadline = time.monotonic() + 2.0
        while list(root.glob(".nfs*")) and time.monotonic() < deadline:
            time.sleep(0.02)
        assert not list(root.glob(".nfs*"))

    try:
        # Crash after the destination-parent fsync boundary leaves an exact
        # nlink-2 pair, which a later invocation must finish.
        real_fsync = runtime.os.fsync
        destination_inode = destination_parent.stat().st_ino
        raised = False
        def fail_destination_parent_fsync(fd):
            nonlocal raised
            if (not raised and os.fstat(fd).st_ino == destination_inode
                    and (destination_parent / "destination.json").exists()):
                raised = True
                raise OSError(runtime.errno.EIO, "injected destination-parent fsync")
            return real_fsync(fd)
        monkeypatch.setattr(runtime.os, "fsync", fail_destination_parent_fsync)
        with pytest.raises(OSError, match="destination-parent fsync"):
            runtime._link_publication(
                descriptor, row, raw, descriptor_path=root / "transaction.json")
        monkeypatch.setattr(runtime.os, "fsync", real_fsync)
        assert (root / "source.payload").stat().st_nlink == 2
        runtime._link_publication(
            descriptor, row, raw, descriptor_path=root / "transaction.json")
        assert (destination_parent / "destination.json").stat().st_nlink == 1
        clear_case()

        # Crash after source unlink leaves destination-only plus a marker.
        source_inode = root.stat().st_ino
        raised = False
        def fail_source_parent_fsync(fd):
            nonlocal raised
            if (not raised and os.fstat(fd).st_ino == source_inode
                    and not (root / "source.payload").exists()
                    and (destination_parent / "destination.json").exists()):
                raised = True
                raise OSError(runtime.errno.EIO, "injected source-parent fsync")
            return real_fsync(fd)
        monkeypatch.setattr(runtime.os, "fsync", fail_source_parent_fsync)
        with pytest.raises(OSError, match="source-parent fsync"):
            runtime._link_publication(
                descriptor, row, raw, descriptor_path=root / "transaction.json")
        monkeypatch.setattr(runtime.os, "fsync", real_fsync)
        runtime._link_publication(
            descriptor, row, raw, descriptor_path=root / "transaction.json")
        assert not list(root.glob(".destination.json.attempt-*"))
        clear_case()

        # Three source-only results consume exactly three durable attempts; a
        # fourth invocation performs no link call.
        link_calls = 0
        def always_fail(*_args):
            nonlocal link_calls
            link_calls += 1
            raise OSError(runtime.errno.EIO, "source-only")
        for expected in range(1, 4):
            with pytest.raises(runtime.RecoverableLinkInterruption):
                runtime._link_publication(
                    descriptor, row, raw, descriptor_path=root / "transaction.json",
                    link_function=always_fail)
            assert len(list(root.glob(".destination.json.attempt-*"))) == expected
        with pytest.raises(ValueError, match="attempt budget exhausted"):
            runtime._link_publication(
                descriptor, row, raw, descriptor_path=root / "transaction.json",
                link_function=always_fail)
        assert link_calls == 3
        clear_case()

        # Expiry permits no marker/link, but an already-created exact pair is
        # still safely completed after expiry.
        expired_now = int(descriptor["recovery_deadline_unix"]) + 1
        with pytest.raises(ValueError, match="deadline expired"):
            runtime._link_publication(
                descriptor, row, raw, descriptor_path=root / "transaction.json",
                now=expired_now)
        assert not list(root.glob(".destination.json.attempt-*"))
        os.link(root / "source.payload", destination_parent / "destination.json")
        runtime._link_publication(
            descriptor, row, raw, descriptor_path=root / "transaction.json",
            now=expired_now)
        assert not (root / "source.payload").exists()
        clear_case()

        # Foreign destination, a third hard link, short bytes, and a symlink
        # all block without deleting the planted evidence.
        foreign = destination_parent / "destination.json"
        foreign.write_bytes(b"foreign\n"); foreign.chmod(0o600)
        with pytest.raises(ValueError, match="destination-only bytes drift"):
            runtime._link_publication(
                descriptor, row, raw, descriptor_path=root / "transaction.json")
        assert foreign.read_bytes() == b"foreign\n"
        foreign.unlink(); clear_case()

        (root / "source.payload").write_bytes(raw)
        (root / "source.payload").chmod(0o600)
        os.link(root / "source.payload", destination_parent / "destination.json")
        os.link(root / "source.payload", root / "third_link.json")
        with pytest.raises(ValueError, match="identity drift"):
            runtime._link_publication(
                descriptor, row, raw, descriptor_path=root / "transaction.json")
        assert (root / "third_link.json").exists()
        clear_case()

        (root / "source.payload").write_bytes(raw[:4])
        (root / "source.payload").chmod(0o600)
        with pytest.raises(ValueError, match="source-only bytes drift"):
            runtime._link_publication(
                descriptor, row, raw, descriptor_path=root / "transaction.json")
        clear_case()

        os.symlink("transaction.json", root / "source.payload")
        with pytest.raises(OSError):
            runtime._link_publication(
                descriptor, row, raw, descriptor_path=root / "transaction.json")
        clear_case()
    finally:
        monkeypatch.undo()
        _remove_owned_test_root(root)
    assert not (root.exists() or root.is_symlink())


def test_derived_publication_requires_two_independent_reproductions(
        tmp_path, monkeypatch):
    root = tmp_path / "publisher"; root.mkdir(mode=0o700)
    raw = runtime.base.canonical_bytes({
        "schema_version": "derived-test-v1", "value": 1})
    row = runtime._derived_publication_row(
        0, root, "source.payload", root, "destination.json", 0o600,
        "derived_test", builder_id="derived_test_v1",
        builder_input_sha256="5" * 64, output_schema="derived-test-v1",
        allowed_fields=("schema_version", "value"))
    fake_mount = {
        "schema_version": "msae_v3_gen9_mount_identity_v1",
        "mountinfo": {"filesystem_type": "nfs4"},
        "mountinfo_sha256": "6" * 64,
        "filesystem_magic": "0x6969", "filesystem_fsid": [5, 6],
        "directory_device": root.stat().st_dev,
    }
    monkeypatch.setattr(runtime, "ROOT", root)
    monkeypatch.setattr(runtime, "_mount_identity", lambda _path: dict(fake_mount))
    descriptor = runtime._link_transaction_payload(
        kind="setup", authority_sha256="5" * 64,
        publications=[row], maximum_seconds=300)
    runtime._bootstrap_link_transaction(root, descriptor)
    with pytest.raises(ValueError, match="lacks an independent reproducer"):
        runtime._link_publication(
            descriptor, row, raw, descriptor_path=root / "transaction.json")
    with pytest.raises(ValueError, match="builder reproduction drift"):
        runtime._link_publication(
            descriptor, row, raw, descriptor_path=root / "transaction.json",
            derived_reproducer=lambda: b"wrong\n")
    calls = 0
    def reproduce():
        nonlocal calls
        calls += 1
        return runtime.base.canonical_bytes({
            "schema_version": "derived-test-v1", "value": 1})
    runtime._link_publication(
        descriptor, row, raw, descriptor_path=root / "transaction.json",
        derived_reproducer=reproduce)
    assert calls == 2
    assert (root / "destination.json").read_bytes() == raw

def _write_timestamp_valid_malicious_pyc(source: Path, marker: Path) -> Path:
    """Plant bytecode that is valid for the untouched source's mtime/size."""
    source_stat = source.stat()
    payload = (
        "from pathlib import Path\n"
        f"Path({str(marker)!r}).write_text('malicious-pyc-executed')\n"
    )
    code = compile(payload, str(source), "exec")
    raw = importlib._bootstrap_external._code_to_timestamp_pyc(  # type: ignore[attr-defined]
        code, int(source_stat.st_mtime), source_stat.st_size)
    cached = Path(importlib.util.cache_from_source(str(source)))
    cached.parent.mkdir(parents=True, exist_ok=True)
    cached.write_bytes(raw)
    return cached


def _write_sourceless_malicious_pyc(path: Path, marker: Path) -> None:
    payload = (
        "from pathlib import Path\n"
        f"Path({str(marker)!r}).write_text('sourceless-pyc-executed')\n"
    )
    code = compile(payload, str(path.with_suffix(".py")), "exec")
    raw = importlib._bootstrap_external._code_to_timestamp_pyc(  # type: ignore[attr-defined]
        code, 0, 0)
    path.write_bytes(raw)


def _copy_source_only_cli_fixture(root: Path) -> None:
    import shutil
    for name in (
        "msae_independent_measurement_v3.py",
        "msae_independent_measurement_v3_post_m1.py",
        "msae_independent_measurement_v3_post_m1_runtime.py",
        "msae_independent_measurement_v3_post_m2_gen9.py",
        "msae_independent_measurement_v3_post_m2_gen9_runtime.py",
        "msae_measurement_remediation_v1.py",
        "msae_measurement_v2.py",
        "run_msae_independent_calibration_v3.py",
        "run_msae_independent_calibration_v3_gen9.py",
    ):
        target = root / "scripts" / name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(ROOT / "scripts" / name, target)


def test_controller_ignores_valid_timestamp_local_pyc_before_all_gates(tmp_path):
    candidate = tmp_path / "candidate"
    _copy_source_only_cli_fixture(candidate)
    source = candidate / "scripts/msae_independent_measurement_v3.py"
    marker = tmp_path / "controller-pyc-marker"
    _write_timestamp_valid_malicious_pyc(source, marker)
    python = str(ROOT / ".venv-atlas/bin/python")

    # Prove the planted cache is accepted by Python's default finder.
    control = subprocess.run([
        python, "-S", "-B", "-I", "-c",
        f"import sys;sys.path.insert(0,{str(source.parent)!r});"
        "import msae_independent_measurement_v3",
    ], text=True, capture_output=True)
    assert control.returncode == 0 and marker.read_text() == "malicious-pyc-executed"
    marker.unlink()

    # The reviewed controller runs as source and installs its exact finder
    # before the first local import.  It may fail later because the temp tree is
    # intentionally incomplete, but the valid malicious cache cannot execute.
    result = subprocess.run([
        python, "-S", "-B", "-I",
        str(candidate / "scripts/msae_independent_measurement_v3_post_m2_gen9.py"),
        "not-a-command",
    ], text=True, capture_output=True)
    assert result.returncode != 0
    assert not marker.exists()


def test_runner_ignores_valid_timestamp_controller_pyc_before_auth_gate(tmp_path):
    candidate = tmp_path / "candidate"
    _copy_source_only_cli_fixture(candidate)
    controller = candidate / "scripts/msae_independent_measurement_v3_post_m2_gen9.py"
    marker = tmp_path / "runner-pyc-marker"
    _write_timestamp_valid_malicious_pyc(controller, marker)
    result = subprocess.run([
        str(ROOT / ".venv-atlas/bin/python"), "-S", "-B", "-I",
        str(candidate / "scripts/run_msae_independent_calibration_v3_gen9.py"),
        "--run-root", "not-the-signed-root", "--gpu-uuid", "GPU-fake",
        "--broker-pid", "1", "--readiness-fd", "0", "--final-ack-fd", "0",
        "--confirmed-fd", "0",
    ], text=True, capture_output=True)
    assert result.returncode != 0
    assert not marker.exists()


def test_runner_removes_scripts_path_before_deferred_third_party_import(tmp_path):
    import shutil
    candidate = tmp_path / "candidate"
    _copy_source_only_cli_fixture(candidate)
    (candidate / ".venv-atlas").symlink_to(ROOT / ".venv-atlas", target_is_directory=True)
    m0 = candidate / "data/msae_independent_measurement_v3/m0_completion_manifest.json"
    m0.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(ROOT / "data/msae_independent_measurement_v3/m0_completion_manifest.json", m0)
    shadow = candidate / "scripts/numpy.pyc"
    marker = tmp_path / "sourceless-shadow-marker"
    _write_sourceless_malicious_pyc(shadow, marker)
    python = str(ROOT / ".venv-atlas/bin/python")

    # Prove a default PathFinder search of scripts executes the planted,
    # Git-ignored sourceless cache.
    control = subprocess.run([
        python, "-S", "-B", "-I", "-c",
        f"import sys;sys.path.insert(0,{str(shadow.parent)!r});import numpy",
    ], text=True, capture_output=True)
    assert control.returncode == 0 and marker.read_text() == "sourceless-pyc-executed"
    marker.unlink()

    runner = candidate / "scripts/run_msae_independent_calibration_v3_gen9.py"
    result = subprocess.run([
        python, "-S", "-B", "-I", "-c",
        "import runpy,sys;"
        f"runpy.run_path({str(runner)!r},run_name='msae_runner_source_only_probe');"
        "assert all(not p.endswith('/scripts') for p in sys.path);"
        "import numpy;print(numpy.__file__)",
    ], text=True, capture_output=True)
    assert result.returncode == 0, result.stderr
    assert "site-packages/numpy/__init__.py" in result.stdout
    assert not marker.exists()


def terminal_files():
    return {"stage_b.json": b"{}\n", "status.json": b"{}\n",
            "runtime_native_pre_import.json": b"{}\n",
            "runtime_native_post_torch.json": b"{}\n",
            "runtime_native_post_model.json": b"{}\n",
            "runtime_native_final.json": b"{}\n"}


def test_operator_instruction_is_verbatim_and_not_a_paraphrase():
    assert runtime.OPERATOR_INSTRUCTION.startswith("Do these steps for me.")
    assert "THanks!\n\n### 1. Preserve this attempt as failed" in runtime.OPERATOR_INSTRUCTION
    assert runtime.OPERATOR_INSTRUCTION.endswith("- add behavioral failure-path tests.")
    assert runtime.base.sha_bytes(runtime.OPERATOR_INSTRUCTION.encode("utf-8")) == \
        "8acd2583df6224ff357766296c1f4461212de5383f533ee352d292f9cbdaca12"


def test_endpoint_registry_is_closed_and_has_no_learned_c1_branch_names():
    registry = runtime.endpoint_registry()
    ids = [row["endpoint_id"] for row in registry["entries"]]
    assert len(ids) == len(set(ids)) == registry["endpoint_count"]
    categories = {row["category"] for row in registry["entries"]}
    assert categories == {"localization", "functional_reproducibility", "collateral",
                          "counterfactual", "baseline"}
    c1 = [row for row in registry["entries"] if row.get("role") == "C1"]
    assert all(row.get("checkpoint") in {None, "raw"} for row in c1)
    assert all(row.get("component") not in {"assigned", "nonassigned", "joint"} for row in c1)
    repro = [row for row in registry["entries"] if row["category"] == "functional_reproducibility"]
    assert all(row["checkpoints"] == ["g4", "g5", "g6"] and row["control"] == "g7_descriptive_only"
               for row in repro)
    assert registry["endpoint_count"] == 1541
    assert registry["category_counts"] == {
        "localization": 576, "functional_reproducibility": 33, "collateral": 792,
        "counterfactual": 96, "baseline": 44}
    assert all(row.get("component") for row in registry["entries"]
               if row["category"] == "collateral")


def test_endpoint_registry_rejects_noncanonical_endpoint_id():
    value = copy.deepcopy(runtime.endpoint_registry())
    value["entries"][0]["endpoint_id"] = "arbitrary-but-unique"
    value["endpoint_id_set_sha256"] = runtime.base.sha_bytes(runtime.base.canonical_bytes(
        sorted(row["endpoint_id"] for row in value["entries"])))
    with pytest.raises(ValueError, match="canonical typed-key"):
        runtime.validate_endpoint_registry(value)


@pytest.mark.parametrize("field,replacement", [
    ("role", "C9"), ("checkpoint", "g9"), ("family", "missing_family"),
    ("task", "missing_task"), ("component", "missing_component"),
    ("metric", "missing_metric"), ("layer", 4),
])
def test_endpoint_registry_rejects_every_localization_axis_mutation(field, replacement):
    value = copy.deepcopy(runtime.endpoint_registry())
    row = next(item for item in value["entries"] if item["category"] == "localization")
    row[field] = replacement
    with pytest.raises(ValueError, match="endpoint product mismatch"):
        runtime.validate_endpoint_registry(value)


def test_endpoint_registry_rejects_missing_g7_c1_and_duplicate_cells():
    original = runtime.endpoint_registry()
    for predicate in (
        lambda row: row.get("checkpoint") == "g7",
        lambda row: row.get("role") == "C1",
    ):
        value = copy.deepcopy(original)
        index = next(i for i, row in enumerate(value["entries"]) if predicate(row))
        value["entries"].pop(index)
        with pytest.raises(ValueError, match="endpoint product mismatch"):
            runtime.validate_endpoint_registry(value)
    value = copy.deepcopy(original)
    value["entries"].append(copy.deepcopy(value["entries"][0]))
    with pytest.raises(ValueError, match="endpoint product mismatch"):
        runtime.validate_endpoint_registry(value)


def _minimal_config_candidate_root(root: Path) -> tuple[str, str, str]:
    import shutil
    relatives = (
        "scripts/msae_independent_measurement_v3.py",
        "scripts/msae_measurement_v2.py",
        "scripts/run_msae_independent_calibration_v3.py",
        "scripts/launch_msae_independent_calibration_v3.sh",
        "scripts/run_msae_independent_calibration_v3_gen9.py",
        "scripts/msae_independent_measurement_v3_post_m2_gen9.py",
        "scripts/msae_independent_measurement_v3_post_m2_gen9_runtime.py",
        "scripts/launch_msae_independent_calibration_v3_gen9.sh",
        "docs/rfc-msae-independent-measurement-v3-post-m9-gen9.md",
        "docs/plan-msae-independent-measurement-v3-post-m9-gen9.md",
        "tests/test_msae_independent_measurement_v3_post_m9_gen9.py",
        "reports/adversarial/msae_independent_measurement_v3_post_m2_gen9_plan.md",
        "configs/msae_independent_measurement_v1/protocol.json",
        "data/msae_independent_measurement_v1/calibration_strata.json",
    )
    for relative in relatives:
        target = root / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(ROOT / relative, target)
    implementation = (root /
        "reports/adversarial/msae_independent_measurement_v3_post_m2_gen9_implementation.md")
    pre_capability = (root /
        "reports/adversarial/msae_independent_measurement_v3_post_m2_gen9_pre_capability.md")
    pre_capability.write_text("pre-capability fixture\n")
    pre_capability.chmod(0o644)
    implementation.write_text("implementation fixture\n")
    implementation.chmod(0o644)
    return (runtime.base.sha_file(
        root / "reports/adversarial/msae_independent_measurement_v3_post_m2_gen9_plan.md"),
        runtime.base.sha_file(pre_capability), runtime.base.sha_file(implementation))


def test_generic_protocol_builder_executes_candidate_root_module_not_live_cache(
        tmp_path, monkeypatch):
    root = tmp_path / "candidate"
    _minimal_config_candidate_root(root)
    marker = tmp_path / "rooted-builder-pyc-marker"
    _write_timestamp_valid_malicious_pyc(
        root / "scripts/msae_independent_measurement_v3.py", marker)
    monkeypatch.setattr(
        runtime.base, "build_protocol_config",
        lambda checkpoints: (_ for _ in ()).throw(AssertionError("live builder used")))
    value = runtime._rooted_generic_protocol_config(root, [])
    assert not marker.exists()
    expected_environment = runtime._rooted_generic_environment_sha256(root)
    assert len(value["replay"]["strata"]) == 4
    assert all(row["environment_sha256"] == expected_environment
               for row in value["replay"]["strata"])
    assert all(row["code_sha256"] == runtime.base.sha_file(
        root / "scripts/run_msae_independent_calibration_v3.py")
               for row in value["replay"]["strata"])


def test_real_protocol_config_is_byte_equal_across_two_copied_sparse_roots(tmp_path):
    left, right = tmp_path / "left", tmp_path / "right"
    left_reviews = _minimal_config_candidate_root(left)
    right_reviews = _minimal_config_candidate_root(right)
    assert left_reviews == right_reviews
    left_value = runtime._protocol_config_payload(
        [], runtime.M2_REVIEWED_COMPLETION_SHA256,
        plan_review_sha256=left_reviews[0],
        pre_capability_review_sha256=left_reviews[1],
        implementation_review_sha256=left_reviews[2], root=left)
    right_value = runtime._protocol_config_payload(
        [], runtime.M2_REVIEWED_COMPLETION_SHA256,
        plan_review_sha256=right_reviews[0],
        pre_capability_review_sha256=right_reviews[1],
        implementation_review_sha256=right_reviews[2], root=right)
    assert runtime.base.canonical_bytes(left_value) == runtime.base.canonical_bytes(right_value)
    for row in left_value["replay"]["strata"]:
        assert row["code_sha256"] == runtime.base.sha_file(
            left / "scripts/run_msae_independent_calibration_v3_gen9.py")
        assert row["environment_sha256"] == left_value[
            "post_m2_runtime"]["environment_derivation"]["canonical_environment_sha256"]


def test_protocol_config_adapter_is_root_independent_and_projects_generic_schema(
        tmp_path, monkeypatch):
    from msae_measurement_remediation_v1 import validate_draft_config
    left = tmp_path / "left"; right = tmp_path / "right"
    left_reviews = _minimal_config_candidate_root(left)
    right_reviews = _minimal_config_candidate_root(right)
    assert left_reviews == right_reviews
    template = runtime.base.read_json(runtime.V3_CONFIG / "protocol.json")

    def fake_build(checkpoints, candidate_root):
        value = copy.deepcopy(template)
        for row in value["replay"]["strata"]:
            row["code_sha256"] = runtime.base.sha_file(
                candidate_root / "scripts/run_msae_independent_calibration_v3.py")
            row["environment_sha256"] = runtime._rooted_generic_environment_sha256(
                candidate_root)
        return value

    monkeypatch.setattr(runtime, "_rooted_generic_protocol_config",
                        lambda root, checkpoints: fake_build(checkpoints, root))
    successor = runtime._protocol_config_payload(
        [], runtime.M2_REVIEWED_COMPLETION_SHA256,
        plan_review_sha256=left_reviews[0],
        pre_capability_review_sha256=left_reviews[1],
        implementation_review_sha256=left_reviews[2], root=left)
    rebuilt = runtime._protocol_config_payload(
        [], runtime.M2_REVIEWED_COMPLETION_SHA256,
        plan_review_sha256=right_reviews[0],
        pre_capability_review_sha256=right_reviews[1],
        implementation_review_sha256=right_reviews[2], root=right)
    assert runtime.base.canonical_bytes(successor) == runtime.base.canonical_bytes(rebuilt)
    derivation = successor["post_m2_runtime"]["environment_derivation"]
    assert "candidate_root_generic_environment_sha256" not in derivation
    assert all(row["code_sha256"] == runtime.base.sha_file(
        left / "scripts/run_msae_independent_calibration_v3_gen9.py")
               for row in successor["replay"]["strata"])
    assert all(row["environment_sha256"] == derivation["canonical_environment_sha256"]
               for row in successor["replay"]["strata"])
    generic = runtime.generic_config_projection(successor)
    assert set(generic) == set(runtime.GENERIC_CONFIG_KEYS)
    assert not set(runtime.SUCCESSOR_CONFIG_KEYS) & set(generic)
    raw = runtime.base.canonical_bytes(generic)
    assert validate_draft_config(raw, runtime.base.sha_bytes(raw))["status"] == "ready"
    with pytest.raises(ValueError, match="successor config key mismatch"):
        runtime.generic_config_projection({**successor, "unreviewed": True})


def test_protocol_config_adapter_rejects_wrong_code_or_environment_precondition(
        tmp_path, monkeypatch):
    root = tmp_path / "candidate"
    reviews = _minimal_config_candidate_root(root)
    template = runtime.base.read_json(runtime.V3_CONFIG / "protocol.json")
    for field in ("code_sha256", "environment_sha256"):
        def fake_build(checkpoints, candidate_root, field=field):
            value = copy.deepcopy(template)
            for row in value["replay"]["strata"]:
                row["code_sha256"] = runtime.base.sha_file(
                    candidate_root / "scripts/run_msae_independent_calibration_v3.py")
                row["environment_sha256"] = runtime._rooted_generic_environment_sha256(
                    candidate_root)
            value["replay"]["strata"][0][field] = "f" * 64
            return value
        monkeypatch.setattr(runtime, "_rooted_generic_protocol_config",
                            lambda root, checkpoints, fake_build=fake_build:
                            fake_build(checkpoints, root))
        with pytest.raises(ValueError, match="substitution precondition"):
            runtime._protocol_config_payload(
                [], runtime.M2_REVIEWED_COMPLETION_SHA256,
                plan_review_sha256=reviews[0], pre_capability_review_sha256=reviews[1],
                implementation_review_sha256=reviews[2],
                root=root)


@pytest.mark.parametrize("mutation", ["missing", "duplicate", "extra"])
def test_protocol_config_adapter_rejects_missing_duplicate_or_extra_strata(
        tmp_path, monkeypatch, mutation):
    root = tmp_path / "candidate"
    reviews = _minimal_config_candidate_root(root)
    template = runtime.base.read_json(runtime.V3_CONFIG / "protocol.json")

    def fake_build(checkpoints, candidate_root):
        value = copy.deepcopy(template)
        for row in value["replay"]["strata"]:
            row["code_sha256"] = runtime.base.sha_file(
                candidate_root / "scripts/run_msae_independent_calibration_v3.py")
            row["environment_sha256"] = runtime._rooted_generic_environment_sha256(
                candidate_root)
        if mutation == "missing":
            value["replay"]["strata"].pop()
        elif mutation == "duplicate":
            value["replay"]["strata"][-1] = copy.deepcopy(
                value["replay"]["strata"][0])
        else:
            value["replay"]["strata"].append(copy.deepcopy(
                value["replay"]["strata"][0]))
        return value

    monkeypatch.setattr(runtime, "_rooted_generic_protocol_config",
                        lambda root, checkpoints: fake_build(checkpoints, root))
    with pytest.raises(ValueError, match="stratum dimensions drift"):
        runtime._protocol_config_payload(
            [], runtime.M2_REVIEWED_COMPLETION_SHA256,
            plan_review_sha256=reviews[0], pre_capability_review_sha256=reviews[1],
                implementation_review_sha256=reviews[2],
            root=root)


def test_environment_derivation_never_falls_back_to_candidate_root_venv(tmp_path):
    candidate = tmp_path / "candidate"
    candidate_python = candidate / ".venv-atlas/bin/python"
    candidate_python.parent.mkdir(parents=True)
    candidate_python.write_bytes(b"not the registered interpreter\n")
    candidate_python.chmod(0o755)
    value = runtime._environment_derivation(candidate_root=candidate)
    registered = str((runtime.ROOT / ".venv-atlas/bin/python").resolve(strict=True))
    assert value["canonical_external_python_realpath"] == registered
    assert value["canonical_external_python_realpath"] != str(candidate_python.resolve())
    assert value["canonical_environment_sha256"] != \
        runtime._rooted_generic_environment_sha256(candidate)


def test_protocol_config_adapter_does_not_normalize_an_unrelated_third_field(
        tmp_path, monkeypatch):
    left = tmp_path / "left"; right = tmp_path / "right"
    left_reviews = _minimal_config_candidate_root(left)
    right_reviews = _minimal_config_candidate_root(right)
    template = runtime.base.read_json(runtime.V3_CONFIG / "protocol.json")

    def fake_build(checkpoints, candidate_root):
        value = copy.deepcopy(template)
        for row in value["replay"]["strata"]:
            row["code_sha256"] = runtime.base.sha_file(
                candidate_root / "scripts/run_msae_independent_calibration_v3.py")
            row["environment_sha256"] = runtime._rooted_generic_environment_sha256(
                candidate_root)
        if candidate_root.name == "right":
            value["replay"]["strata"][0]["input_sha256"] = "f" * 64
        return value

    monkeypatch.setattr(runtime, "_rooted_generic_protocol_config",
                        lambda root, checkpoints: fake_build(checkpoints, root))
    left_value = runtime._protocol_config_payload(
        [], runtime.M2_REVIEWED_COMPLETION_SHA256,
        plan_review_sha256=left_reviews[0],
        pre_capability_review_sha256=left_reviews[1],
        implementation_review_sha256=left_reviews[2], root=left)
    right_value = runtime._protocol_config_payload(
        [], runtime.M2_REVIEWED_COMPLETION_SHA256,
        plan_review_sha256=right_reviews[0],
        pre_capability_review_sha256=right_reviews[1],
        implementation_review_sha256=right_reviews[2], root=right)
    assert left_value["replay"]["strata"][0]["input_sha256"] != \
        right_value["replay"]["strata"][0]["input_sha256"]
    assert runtime.base.canonical_bytes(left_value) != runtime.base.canonical_bytes(right_value)


def test_generic_replay_bundle_changes_only_the_config_binding():
    bundle = {"schema_version": "msae_calibration_replay_bundle_v1",
              "protocol_config_sha256": "a" * 64, "replay_registry_sha256": "b" * 64,
              "source_role": "calibration", "source_revision": "c" * 64,
              "partition": "calibration-public", "observations": {}}
    projected = runtime.generic_replay_bundle(bundle, "d" * 64)
    assert projected == {**bundle, "protocol_config_sha256": "d" * 64}
    with pytest.raises(ValueError, match="replay-bundle key mismatch"):
        runtime.generic_replay_bundle({**bundle, "extra": 1}, "d" * 64)


def test_frozen_plan_review_is_canonical_and_machine_bound():
    value = runtime._review_control_lines(
        runtime.PLAN_REVIEW, scope="gen9_plan", expected_controls={
            "VERDICT": "SHIP", "REVIEW_SCOPE": "gen9_plan",
            "PLAN_SHA256": runtime.FROZEN_PLAN_SHA256,
            "SEALED_CONTENT_READS": "0",
        }, expected_sha256=runtime.FROZEN_PLAN_REVIEW_SHA256)
    assert value["scope"] == "gen9_plan"
    assert value["controls"]["PLAN_SHA256"] == runtime.FROZEN_PLAN_SHA256
    assert runtime._review_check_rows(value, expected_count=0) == []
    with pytest.raises(ValueError):
        runtime._review_control_lines(
            runtime.PLAN_REVIEW, scope="gen9_plan", expected_controls={
                "VERDICT": "SHIP", "REVIEW_SCOPE": "gen9_plan",
                "PLAN_SHA256": runtime.FROZEN_PLAN_SHA256,
                "SEALED_CONTENT_READS": "0",
            }, expected_sha256="0" * 64)


def test_review_gate_rejects_missing_extra_duplicate_and_wrong_scope_controls(
        tmp_path, monkeypatch):
    monkeypatch.setattr(runtime, "ROOT", tmp_path)
    path = tmp_path / "review.md"
    expected = {"PLAN": "a" * 64, "RUNTIME": "b" * 64}

    def install(lines):
        path.write_text("\n".join(lines) + "\n")
        path.chmod(0o644)
        return runtime.base.sha_file(path)

    good = ["VERDICT: SHIP", "REVIEW_SCOPE: implementation",
            "PLAN_SHA256: " + "a" * 64, "RUNTIME_SHA256: " + "b" * 64]
    digest = install(good)
    assert runtime._canonical_review(
        path, digest, scope="implementation", expected_digests=expected)["scope"] == \
        "implementation"
    for lines in (
        good + ["EXTRA_SHA256: " + "c" * 64],
        good + ["PLAN_SHA256: " + "a" * 64],
        [line for line in good if not line.startswith("RUNTIME_SHA256")],
        [line.replace("implementation", "plan") for line in good],
        ["VERDICT: BLOCK", *good],
        ["VERDICT : BLOCK", *good],
        ["VERDICT:\tBLOCK", *good],
        ["REVIEW_SCOPE : plan", *good],
        [" VERDICT: SHIP", *good[1:]],
        [*good, "EXTRA_SHA256: not-a-digest"],
    ):
        digest = install(lines)
        with pytest.raises(ValueError):
            runtime._canonical_review(
                path, digest, scope="implementation", expected_digests=expected)


@pytest.mark.parametrize("defect", [
    "symlink", "hardlink", "mode", "owner", "carriage_return",
    "missing_newline", "invalid_utf8", "stale_control", "wrong_scope",
])
def test_create_once_review_rejects_filesystem_and_canonicality_defects(
        tmp_path, monkeypatch, defect):
    monkeypatch.setattr(runtime, "ROOT", tmp_path)
    expected = {"PLAN": "a" * 64}
    raw = ("VERDICT: SHIP\nREVIEW_SCOPE: implementation\n"
           f"PLAN_SHA256: {expected['PLAN']}\n").encode()
    review = tmp_path / "review.md"
    if defect == "carriage_return":
        raw = raw.replace(b"\n", b"\r\n")
    elif defect == "missing_newline":
        raw = raw.rstrip(b"\n")
    elif defect == "invalid_utf8":
        raw += b"\xff\n"
    elif defect == "stale_control":
        raw = raw.replace(b"a" * 64, b"b" * 64)
    elif defect == "wrong_scope":
        raw = raw.replace(b"implementation", b"post_m3")
    if defect == "symlink":
        backing = tmp_path / "backing.md"
        backing.write_bytes(raw); backing.chmod(0o644)
        review.symlink_to(backing)
    else:
        review.write_bytes(raw); review.chmod(0o644)
    if defect == "hardlink":
        os.link(review, tmp_path / "alias.md")
    elif defect == "mode":
        review.chmod(0o600)
    elif defect == "owner":
        actual_uid = review.stat().st_uid
        monkeypatch.setattr(runtime.os, "getuid", lambda: actual_uid + 1)
    supplied = (runtime.base.sha_file(review)
                if defect != "symlink" else "0" * 64)
    with pytest.raises((ValueError, OSError, UnicodeDecodeError)):
        runtime._canonical_review(
            review, supplied, scope="implementation", expected_digests=expected)


def test_gen3_review_namespace_rejects_undeclared_prefixed_sibling(
        tmp_path, monkeypatch):
    root = tmp_path / "reviews"; root.mkdir()
    names = {
        "plan": "msae_independent_measurement_v3_post_m2_gen9_plan.md",
        "pre": "msae_independent_measurement_v3_post_m2_gen9_pre_capability.md",
        "implementation":
            "msae_independent_measurement_v3_post_m2_gen9_implementation.md",
        "post": "msae_independent_measurement_v3_post_m2_gen9_post_m3.md",
        "prescore": "msae_independent_measurement_v3_post_m2_gen9_prescore.md",
    }
    for name in (names["plan"], names["pre"], names["implementation"]):
        (root / name).write_text("review\n")
    monkeypatch.setattr(runtime, "PLAN_REVIEW", root / names["plan"])
    monkeypatch.setattr(runtime, "PRE_CAPABILITY_REVIEW", root / names["pre"])
    monkeypatch.setattr(runtime, "IMPLEMENTATION_REVIEW", root / names["implementation"])
    monkeypatch.setattr(runtime, "POST_M3_REVIEW", root / names["post"])
    monkeypatch.setattr(runtime, "PRESCORE_REVIEW", root / names["prescore"])
    runtime._validate_gen3_review_namespace("implementation")
    (root / "msae_independent_measurement_v3_post_m2_gen9_backup.md").write_text(
        "unexpected\n")
    with pytest.raises(ValueError, match="review namespace drift"):
        runtime._validate_gen3_review_namespace("implementation")


def test_gen2_failure_payload_records_only_independently_reproduced_claims():
    before = runtime.GEN2_FAILURE_PATH.exists()
    value = runtime._gen2_failure_payload()
    assert runtime.GEN2_FAILURE_PATH.exists() is before
    assert value["historical_failure"]["evidence_class"] == "operator_attested"
    assert value["historical_failure"]["full_original_transcript_available"] is False
    reproduction = value["independent_root_cause_reproduction"]
    assert reproduction["differing_field_count"] == 4
    assert reproduction["differing_json_pointers"] == [
        f"/replay/strata/{index}/environment_sha256" for index in range(4)]
    assert reproduction["all_other_generic_fields_unchanged"] is True
    assert [row["pointer"] for row in reproduction["field_differences"]] == \
        reproduction["differing_json_pointers"]
    assert all(row["live"] == reproduction["live_environment_sha256"]
               and row["candidate"] == reproduction["candidate_root_environment_sha256"]
               for row in reproduction["field_differences"])
    assert value["stage_a"] == "not_created" and value["model_gpu_tmux"] == "not_run"


def test_failed_gen2_is_wrapped_in_gen9_without_cross_generation_write():
    historical_existed = runtime.GEN2_FAILURE_PATH.exists()
    terminal = runtime._gen3_terminal_payload()
    failed_gen3 = runtime._failed_gen3_wrapper(terminal)
    failed_gen2 = runtime._failed_gen2_wrapper(
        runtime._gen2_failure_payload(terminal), failed_gen3)
    assert runtime.GEN2_FAILURE_PATH.exists() is historical_existed
    assert runtime.FAILED_GEN2_RECORD.parent == runtime.ACTIVE_PROV
    assert failed_gen2["writer_generation"] == runtime.GENERATION
    assert failed_gen2["terminal_fields"]["stage_a"] == "not_created"


def test_legacy_whole_file_delta_is_dead_and_structural_manifest_is_authority(
        monkeypatch):
    manifest = runtime._gen7_to_gen9_change_manifest()
    monkeypatch.setattr(
        runtime, "gen6_to_gen9_substitution_evidence",
        lambda: (_ for _ in ()).throw(AssertionError("legacy comparator called")))
    monkeypatch.setattr(
        runtime, "_typed_gen9_delta_projection",
        lambda *args, **kwargs: (_ for _ in ()).throw(
            AssertionError("legacy typed projection called")))
    descriptor = runtime._changed_regions_transaction_descriptor(manifest)
    runtime._validate_changed_regions_transaction(descriptor)

    monkeypatch.setattr(
        runtime, "_gen7_to_gen9_change_manifest",
        lambda *args, **kwargs: (_ for _ in ()).throw(
            ValueError("structural manifest unavailable")))
    with pytest.raises(ValueError, match="structural manifest unavailable"):
        runtime._changed_regions_transaction_descriptor(manifest)


def test_closure_registry_contains_every_gen9_review_and_failure_input(monkeypatch):
    monkeypatch.setattr(runtime, "_static_closure_analysis",
                        lambda **_kwargs: {"local_modules": []})
    required = {
        runtime.PLAN_PATH.relative_to(runtime.ROOT).as_posix(),
        runtime.PLAN_REVIEW.relative_to(runtime.ROOT).as_posix(),
        runtime.FAILURE_REVIEW.relative_to(runtime.ROOT).as_posix(),
        runtime.PRE_CONTAINMENT_REVIEW.relative_to(runtime.ROOT).as_posix(),
        runtime.PRE_CAPABILITY_REVIEW.relative_to(runtime.ROOT).as_posix(),
        runtime.IMPLEMENTATION_REVIEW.relative_to(runtime.ROOT).as_posix(),
        runtime.POST_M3_REVIEW.relative_to(runtime.ROOT).as_posix(),
        runtime.CHANGE_MANIFEST.relative_to(runtime.ROOT).as_posix(),
        runtime.CONTAINMENT_REPORT.relative_to(runtime.ROOT).as_posix(),
        runtime.CAPABILITY_REPORT.relative_to(runtime.ROOT).as_posix(),
        runtime.FAILED_GEN7_RECORD.relative_to(runtime.ROOT).as_posix(),
        runtime.FAILED_GEN5_RECORD.relative_to(runtime.ROOT).as_posix(),
        runtime.FAILED_GEN4_RECORD.relative_to(runtime.ROOT).as_posix(),
        runtime.FAILED_GEN3_RECORD.relative_to(runtime.ROOT).as_posix(),
        runtime.FAILED_GEN2_RECORD.relative_to(runtime.ROOT).as_posix(),
        runtime.GEN2_FAILURE_PATH.relative_to(runtime.ROOT).as_posix(),
        runtime.continuation.CONTROLLER_PATH.relative_to(runtime.ROOT).as_posix(),
        runtime.RUNTIME.relative_to(runtime.ROOT).as_posix(),
        runtime.RUNNER.relative_to(runtime.ROOT).as_posix(),
        runtime.LAUNCHER.relative_to(runtime.ROOT).as_posix(),
        runtime.TMUX_TEST_SUPERVISOR.relative_to(runtime.ROOT).as_posix(),
        runtime.RUNTIME_RFC.relative_to(runtime.ROOT).as_posix(),
        runtime.RUNTIME_TEST.relative_to(runtime.ROOT).as_posix(),
    }
    observed = set(runtime._candidate_relatives(include_m4=True))
    assert required <= observed
    assert runtime.FAILED_GEN6_RECORD.relative_to(runtime.ROOT).as_posix() not in observed


def test_rooted_closure_extension_receives_only_candidate_root_paths(tmp_path, monkeypatch):
    observed = []

    def fake_extend(payload, paths):
        observed.extend(paths)
        return {**payload, "entries": [
            {"path": path.relative_to(tmp_path).as_posix()} for path in paths]}

    monkeypatch.setattr(runtime.continuation, "extend_closure_payload", fake_extend)
    original_root = runtime.base.ROOT
    result = runtime._extend_rooted_closure({"entries": []}, root=tmp_path)
    assert observed and all(path.is_relative_to(tmp_path) for path in observed)
    assert runtime.base.ROOT == original_root
    assert len(result["entries"]) == len(observed)


def test_rooted_closure_extension_is_byte_equal_across_two_real_sparse_roots(tmp_path):
    left, right = tmp_path / "left", tmp_path / "right"
    relatives = {
        runtime.PLAN_PATH.relative_to(runtime.ROOT),
        runtime.PLAN_REVIEW.relative_to(runtime.ROOT),
        runtime.IMPLEMENTATION_REVIEW.relative_to(runtime.ROOT),
        runtime.POST_M3_REVIEW.relative_to(runtime.ROOT),
        runtime.continuation.CONTROLLER_PATH.relative_to(runtime.ROOT),
        runtime.immutable_continuation.CONTROLLER_PATH.relative_to(runtime.ROOT),
        runtime.RUNTIME.relative_to(runtime.ROOT),
        runtime.RUNNER.relative_to(runtime.ROOT),
        runtime.LAUNCHER.relative_to(runtime.ROOT),
        runtime.RUNTIME_RFC.relative_to(runtime.ROOT),
        runtime.RUNTIME_TEST.relative_to(runtime.ROOT),
        runtime.GEN2_FAILURE_PATH.relative_to(runtime.ROOT),
        runtime.ACTIVE_CONFIG.relative_to(runtime.ROOT) / "protocol.json",
        runtime.ACTIVE_CONFIG.relative_to(runtime.ROOT) / "authorization_commitment.json",
        runtime.ACTIVE_CONFIG.relative_to(runtime.ROOT) / "ed25519_public.pem",
        runtime.CPU_NO_MODEL_TRACE.relative_to(runtime.ROOT),
        runtime.immutable_continuation.CONTINUATION_RFC.relative_to(runtime.ROOT),
        runtime.immutable_continuation.CONTINUATION_TEST.relative_to(runtime.ROOT),
        runtime.immutable_continuation.M1_COMPLETION_PATH.relative_to(runtime.ROOT),
    }
    for root in (left, right):
        for relative in relatives:
            target = root / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes((relative.as_posix() + "\n").encode())
            target.chmod(0o644)
    left_value = runtime._extend_rooted_closure({"entries": []}, root=left)
    right_value = runtime._extend_rooted_closure({"entries": []}, root=right)
    assert runtime.base.canonical_bytes(left_value) == runtime.base.canonical_bytes(right_value)
    assert all(not Path(row["path"]).is_absolute() for row in left_value["entries"])


def test_config_closure_environment_binding_rejects_missing_and_drifted_python(
        tmp_path, monkeypatch):
    runner = tmp_path / runtime.RUNNER.relative_to(runtime.ROOT)
    runner.parent.mkdir(parents=True)
    runner.write_text("runner\n"); runner.chmod(0o644)
    derivation = runtime._environment_derivation(candidate_root=tmp_path)
    config = {"post_m2_runtime": {"environment_derivation": derivation},
              "replay": {"strata": [
                  {"stratum_id": stratum,
                   "code_sha256": runtime.base.sha_file(runner),
                   "environment_sha256": derivation["canonical_environment_sha256"]}
                  for stratum in runtime.EXPECTED_REPLAY_STRATUM_IDS]}}
    python_row = {
        "path": derivation["canonical_external_python_realpath"],
        "size": derivation["canonical_external_python_size"],
        "mode": derivation["canonical_external_python_mode"],
        "sha256": derivation["canonical_external_python_sha256"], "ldd": [],
    }
    runtime._validate_config_closure_environment(
        config, derivation, [python_row],
        python_executable=derivation["canonical_external_python_realpath"], root=tmp_path)
    for defective in ([], [{**python_row, "size": python_row["size"] + 1}],
                      [{**python_row, "path": "/different/python"}]):
        with pytest.raises(ValueError, match="external Python"):
            runtime._validate_config_closure_environment(
                config, derivation, defective,
                python_executable=derivation["canonical_external_python_realpath"],
                root=tmp_path)
    with pytest.raises(ValueError, match="derivation does not reproduce"):
        runtime._validate_config_closure_environment(
            {**config, "post_m2_runtime": {"environment_derivation": {
                **derivation, "canonical_environment_sha256": "f" * 64}}},
            derivation, [python_row],
            python_executable=derivation["canonical_external_python_realpath"], root=tmp_path)


def test_post_m3_review_binds_every_realized_directory_and_downstream_absence(
        tmp_path, monkeypatch):
    implementation = tmp_path / "implementation.md"
    implementation.write_text("implementation\n"); implementation.chmod(0o644)
    post_m3 = tmp_path / "post_m3.md"
    post_m3.write_text("SEALED_PAYLOAD_CONTENT_READS: 0\n"); post_m3.chmod(0o644)
    subject = {
        "config_entries": [
            {"path": f"config/{name}", "sha256": chr(97 + index) * 64}
            for index, name in enumerate((
                "protocol.json", "cpu_no_model_public_entry_trace.json",
                "authorization_commitment.json", "ed25519_public.pem"))],
        "private_key_lstat": {"inode": 1, "content_read_for_this_binding": False},
        "directory_bindings": {
            name: {"path": name, "inode": index}
            for index, name in enumerate(
                ("config", "provenance", "m4_data", "state", "nonce"), start=1)},
        "failed_gen6_entry": {"sha256": "b" * 64},
        "failed_gen5_entry": {"sha256": "c" * 64},
        "failed_gen4_entry": {"sha256": "d" * 64},
        "failed_gen3_entry": {"sha256": "e" * 64},
        "failed_gen2_entry": {"sha256": "f" * 64},
        "setup_manifest_entry": {"sha256": "1" * 64},
        "downstream_absence_sha256": "f" * 64,
    }
    captured = {}

    def fake_review(path, supplied, *, scope, expected_digests):
        captured.update(expected_digests)
        return {"sha256": supplied, "scope": scope}

    monkeypatch.setattr(runtime, "_post_m3_state_binding", lambda **kwargs: subject)
    monkeypatch.setattr(runtime, "_canonical_review", fake_review)
    monkeypatch.setattr(runtime, "IMPLEMENTATION_REVIEW", implementation)
    monkeypatch.setattr(runtime, "POST_M3_REVIEW", post_m3)
    result = runtime.verify_post_m3_review("9" * 64)
    assert result["review"]["scope"] == "gen9_post_m3"
    assert set(captured) == {
        "GEN7_IMPLEMENTATION_REVIEW", "POST_M3_SUBJECT", "GEN7_PROTOCOL",
        "GEN7_AUTHORIZATION_COMMITMENT", "GEN7_PUBLIC_KEY", "GEN7_CPU_TRACE",
        "GEN7_SETUP_MANIFEST", "GEN7_FAILED_GEN6", "GEN7_FAILED_GEN5",
        "GEN7_FAILED_GEN4", "GEN7_FAILED_GEN3", "GEN7_FAILED_GEN2",
        "M2_COMPLETION",
    }
    assert captured["GEN7_FAILED_GEN2"] == "f" * 64


def test_post_m3_subject_uses_lstat_only_private_key_verification(monkeypatch):
    calls = []
    monkeypatch.setattr(runtime, "_validate_gen3_review_namespace", lambda phase: None)
    monkeypatch.setattr(runtime, "_validate_gen2_terminal_namespace", lambda **kwargs: None)
    monkeypatch.setattr(
        runtime, "_verify_existing_authorization_state",
        lambda **kwargs: calls.append(kwargs))
    monkeypatch.setattr(
        runtime, "_verify_live_cpu_no_model_trace",
        lambda: (_ for _ in ()).throw(RuntimeError("stop after authorization state")))
    with pytest.raises(RuntimeError, match="stop after authorization state"):
        runtime._post_m3_state_binding()
    assert calls == [{"verify_private_content": False}]


def test_post_m3_absence_patterns_cover_immutable_gen2_actual_prefixes():
    patterns = set(runtime._post_m3_forbidden_tmp_patterns())
    assert {
        "msae_independent_measurement_v3_*.prescore.check.json",
        "msae_independent_measurement_v3_*.prescore.trace.log",
        "msae_independent_measurement_v3_*.sock",
    } <= patterns


def test_quarantine_guard_runs_after_checks_when_guarded_body_raises(monkeypatch):
    rows = [{"path": "sealed", "nlink": 1}]
    calls = []
    def metadata():
        calls.append("lstat")
        return copy.deepcopy(rows)
    @contextlib.contextmanager
    def tripwire():
        state = {"before_lstat": copy.deepcopy(rows),
                 "blocked_content_open_attempts": []}
        yield state
    monkeypatch.setattr(runtime, "_quarantine_metadata_rows", metadata)
    monkeypatch.setattr(runtime.base, "quarantine_open_tripwire", tripwire)
    with pytest.raises(RuntimeError, match="guarded failure"):
        with runtime.quarantine_guard():
            raise RuntimeError("guarded failure")
    assert calls == ["lstat", "lstat"]


def test_private_key_content_is_confined_to_explicit_setup_and_signer_paths():
    state_source = inspect.getsource(runtime._verify_existing_authorization_state)
    tree_source = inspect.getsource(runtime._validate_tree_authorization)
    verify_source = inspect.getsource(runtime.verify_authorization)
    assert "if verify_private_content:" in state_source
    assert runtime._verify_existing_authorization_state.__kwdefaults__ == {
        "verify_private_content": False}
    assert "_regular_bytes(ACTIVE_PRIVATE_KEY" not in tree_source
    assert "verify_private_content=True" not in verify_source


def test_private_key_lstat_binding_rejects_same_inode_content_rewrite(tmp_path):
    key = tmp_path / "key.pem"; key.write_bytes(b"first-key\n"); key.chmod(0o600)
    st = key.lstat()
    binding = {"path": str(key), "device": st.st_dev, "inode": st.st_ino,
               "uid": st.st_uid, "gid": st.st_gid, "nlink": st.st_nlink,
               "mode": stat.S_IMODE(st.st_mode), "size": st.st_size,
               "mtime_ns": st.st_mtime_ns, "ctime_ns": st.st_ctime_ns}
    runtime._validate_private_key_lstat_binding(key, binding)
    time.sleep(0.002)
    key.write_bytes(b"other-key\n")
    with pytest.raises(ValueError, match="private key binding drift"):
        runtime._validate_private_key_lstat_binding(key, binding)


def test_setup_receipt_schema_is_exact_and_rejects_bad_digest():
    value = runtime._setup_receipt_value(
        1, "gen9_provenance_root", "mkdir", str(runtime.ACTIVE_PROV),
        "a" * 64, None, None)
    assert set(value) == {
        "schema_version", "protocol_id", "generation", "index", "step",
        "action", "target", "transaction_sha256",
        "predecessor_receipt_sha256", "payload_sha256"}
    with pytest.raises(ValueError):
        runtime._setup_receipt_value(
            1, "gen9_provenance_root", "mkdir", str(runtime.ACTIVE_PROV),
            "not-a-digest", None, None)


def test_regular_candidate_entries_bind_owner_and_link_count(tmp_path, monkeypatch):
    item = tmp_path / "item"; item.write_text("payload\n"); item.chmod(0o644)
    entry = runtime._regular_entry(item, root=tmp_path)
    assert entry["uid"] == os.getuid() and entry["nlink"] == 1
    monkeypatch.setattr(runtime, "ROOT", tmp_path)
    assert runtime._verify_manifest_entry(entry)["result"] == "match"
    with pytest.raises(ValueError, match="candidate entry drift"):
        runtime._verify_manifest_entry({**entry, "uid": entry["uid"] + 1})
    alias = tmp_path / "alias"; os.link(item, alias)
    with pytest.raises(ValueError, match="identity drift"):
        runtime._regular_entry(item, root=tmp_path)


def test_transition_cli_requires_both_review_gates_before_dispatch():
    python = str(ROOT / ".venv-atlas/bin/python")
    controller = str(runtime.continuation.CONTROLLER_PATH)
    guarded = [runtime.ACTIVE_CONFIG, runtime.ACTIVE_PROV, runtime.ACTIVE_M4_DATA,
               runtime.ACTIVE_RUN_ROOT, *(runtime.ROOT / item for item in runtime.M4_NEW)]
    before = [(path.exists(), path.is_symlink()) for path in guarded]
    setup = subprocess.run(
        [python, "-S", "-B", "-I", controller, "setup-m3-gen9",
         "--reviewed-m2-sha256", runtime.M2_REVIEWED_COMPLETION_SHA256],
        text=True, capture_output=True)
    assert setup.returncode != 0
    assert "noncanonical gen9 command shape" in setup.stderr
    m4 = subprocess.run(
        [python, "-S", "-B", "-I", controller, "build-m4-gen9"],
        text=True, capture_output=True)
    assert m4.returncode != 0
    assert "noncanonical gen9 command shape" in m4.stderr
    assert [(path.exists(), path.is_symlink()) for path in guarded] == before


def test_m2_semantic_closure_matches_installed_outputs():
    assert runtime._validate_m2_semantics() == {
        "label_rows": 1491748, "role_task_cells": 68, "map_entries": 34000,
        "finite_draws_per_cell": 500, "support_status": "eligible",
        "finite_pass_status": "eligible",
        "correction_denominators": {"raw_selected": [290192, 36],
                                    "retained_after_cap": [89600, 11],
                                    "tokenizable": [286938, 20]}}


def test_persisted_m2_completion_round_trip_is_verifiable():
    digest = "e593a6283aa5468ddbee1cc755dbe60c4ee503375a0cbce44c52614dd232d737"
    with runtime.base.quarantine_open_tripwire() as state:
        assert runtime.verify_m2_completion(digest)["status"] == \
            "m2_support_and_maps_eligible_ready_for_independent_review_pin"
    assert state["blocked_content_open_attempts"] == []


def test_m3_rejects_every_nonreviewed_m2_digest_before_writing():
    with pytest.raises(ValueError, match="M2 pin drift"):
        runtime.setup_m3_gen9("0" * 64, "a" * 64, "b" * 64,
                              "c" * 64, "d" * 64, "e" * 64,
                              "f" * 64, "1" * 64)


def test_failed_m3_preflight_pins_match_the_preserved_bytes():
    assert runtime.base.sha_file(runtime.V3_CONFIG / "protocol.json") == runtime.FAILED_M3_CONFIG_SHA256
    assert runtime.base.sha_file(runtime.V3_CONFIG / "authorization_commitment.json") == \
        runtime.FAILED_M3_COMMITMENT_SHA256
    assert runtime.base.sha_file(runtime.V3_CONFIG / "ed25519_public.pem") == \
        runtime.FAILED_M3_PUBLIC_SHA256


def test_m3_existing_protocol_rejects_symlink_before_acceptance(tmp_path):
    config = tmp_path / "config"; config.mkdir(mode=0o700)
    private = tmp_path / "private"; private.write_bytes(b"key")
    for name in ("ed25519_public.pem", "authorization_commitment.json"):
        (config / name).write_bytes(b"x")
    cpu_trace = config / "cpu_no_model_public_entry_trace.json"
    cpu_trace.write_bytes(runtime.base.canonical_bytes({})); cpu_trace.chmod(0o644)
    backing = tmp_path / "protocol.json"; backing.write_bytes(runtime.base.canonical_bytes({"x": 1}))
    (config / "protocol.json").symlink_to(backing)
    with pytest.raises(OSError):
        runtime._regular_bytes(config / "protocol.json", mode=0o644)


def test_setup_preflight_rejects_preplanted_namespace_before_any_write(
        tmp_path, monkeypatch):
    config = tmp_path / "config"
    private = tmp_path / "private.pem"
    state = tmp_path / "state"
    provenance = tmp_path / "provenance"; provenance.mkdir(mode=0o700)
    (provenance / "planted.json").write_text("{}\n")
    m4_data = tmp_path / "m4-data"
    post_review = tmp_path / "post-review.md"
    prescore_review = tmp_path / "prescore-review.md"
    run = tmp_path / "run"
    transaction = tmp_path / "transaction"
    primary = tmp_path / "primary"; rebuild = tmp_path / "rebuild"
    monkeypatch.setattr(runtime, "ACTIVE_CONFIG", config)
    monkeypatch.setattr(runtime, "ACTIVE_PRIVATE_KEY", private)
    monkeypatch.setattr(runtime, "ACTIVE_STATE", state)
    monkeypatch.setattr(runtime, "ACTIVE_PROV", provenance)
    monkeypatch.setattr(runtime, "ACTIVE_M4_DATA", m4_data)
    monkeypatch.setattr(runtime, "POST_M3_REVIEW", post_review)
    monkeypatch.setattr(runtime, "PRESCORE_REVIEW", prescore_review)
    monkeypatch.setattr(runtime, "ACTIVE_RUN_ROOT", run)
    monkeypatch.setattr(runtime, "M4_TRANSACTION", transaction)
    monkeypatch.setattr(runtime, "M4_PRIMARY", primary)
    monkeypatch.setattr(runtime, "M4_REBUILD", rebuild)
    monkeypatch.setattr(runtime, "M4_NEW", tuple())
    monkeypatch.setattr(runtime, "_validate_gen3_review_namespace", lambda phase: None)
    with pytest.raises(ValueError, match="projection|undeclared|without its journal"):
        runtime._setup_expected_empty_or_prefix({})
    assert not config.exists() and not private.exists()


def test_setup_config_crash_state_must_be_an_ordered_prefix(tmp_path, monkeypatch):
    config = tmp_path / "config"; config.mkdir(mode=0o700)
    (config / "protocol.json").write_text("out-of-order\n")
    (config / "protocol.json").chmod(0o644)
    monkeypatch.setattr(runtime, "ACTIVE_CONFIG", config)
    monkeypatch.setattr(runtime, "ACTIVE_PROV", tmp_path / "provenance")
    monkeypatch.setattr(runtime, "ACTIVE_M4_DATA", tmp_path / "m4-data")
    monkeypatch.setattr(runtime, "ACTIVE_STATE", tmp_path / "state")
    monkeypatch.setattr(runtime, "ACTIVE_NONCE_DIR", tmp_path / "state/nonces")
    monkeypatch.setattr(runtime, "ACTIVE_PRIVATE_KEY", tmp_path / "private.pem")
    monkeypatch.setattr(runtime, "SETUP_KEY_TRANSACTION", tmp_path / "key-staging")
    monkeypatch.setattr(runtime, "M4_NEW", tuple())
    monkeypatch.setattr(runtime, "M4_TRANSACTION", tmp_path / "transaction")
    monkeypatch.setattr(runtime, "M4_PRIMARY", tmp_path / "primary")
    monkeypatch.setattr(runtime, "M4_REBUILD", tmp_path / "rebuild")
    monkeypatch.setattr(runtime, "POST_M3_REVIEW", tmp_path / "post-review")
    monkeypatch.setattr(runtime, "PRESCORE_REVIEW", tmp_path / "prescore-review")
    monkeypatch.setattr(runtime, "ACTIVE_RUN_ROOT", tmp_path / "run")
    monkeypatch.setattr(runtime, "_post_m3_forbidden_tmp_patterns", lambda: tuple())
    with pytest.raises(ValueError, match="ordered prefix"):
        runtime._setup_expected_empty_or_prefix({})


def test_secure_directory_projection_rejects_permissive_mode(tmp_path):
    directory = tmp_path / "secure"; directory.mkdir(mode=0o700)
    runtime._exact_directory_entries(directory, set(), mode=0o700)
    directory.chmod(0o777)
    with pytest.raises(ValueError, match="invalid projected directory"):
        runtime._exact_directory_entries(directory, set(), mode=0o700)


@pytest.mark.parametrize("line,expected", [
    ('1 openat(AT_FDCWD</repo>, "data/private", O_RDONLY) = 3</repo/data/private>',
     "/repo/data/private"),
    ('2 openat(5</repo/data>, "private", O_RDONLY) = 6</repo/data/private>',
     "/repo/data/private"),
    ('3 open("/repo/data/private", O_RDONLY) = 4</repo/data/private>',
     "/repo/data/private"),
])
def test_trace_parser_resolves_absolute_and_dirfd_opens(line, expected):
    assert expected in runtime._trace_open_candidates(line)
    with pytest.raises(ValueError, match="forbidden content open"):
        runtime.verify_trace_no_forbidden(line, [Path(expected)])


def test_review_verdict_parser_rejects_conflicts_and_duplicate_digest_lines(tmp_path, monkeypatch):
    manifest = {"stage_a_sha256": "a" * 64, "dependency_closure_sha256": "b" * 64}
    check = tmp_path / "check"; check.write_bytes(b"check")
    trace = tmp_path / "trace"; trace.write_bytes(b"trace")
    files = {}
    for name in ("implementation", "post_m3", "protocol", "status",
                 "endpoint_registry.json", "environment_allowlist.json", "checker"):
        path = tmp_path / name; path.write_bytes((name + "\n").encode()); files[name] = path
    active_config = tmp_path / "config"; active_config.mkdir()
    active_prov = tmp_path / "prov"; active_prov.mkdir()
    active_data = tmp_path / "data"; active_data.mkdir()
    (active_config / "protocol.json").write_bytes(files["protocol"].read_bytes())
    (active_prov / "status.json").write_bytes(files["status"].read_bytes())
    (active_data / "endpoint_registry.json").write_bytes(files["endpoint_registry.json"].read_bytes())
    (active_data / "environment_allowlist.json").write_bytes(files["environment_allowlist.json"].read_bytes())
    monkeypatch.setattr(runtime, "IMPLEMENTATION_REVIEW", files["implementation"])
    monkeypatch.setattr(runtime, "POST_M3_REVIEW", files["post_m3"])
    monkeypatch.setattr(runtime, "ACTIVE_CONFIG", active_config)
    monkeypatch.setattr(runtime, "ACTIVE_PROV", active_prov)
    monkeypatch.setattr(runtime, "ACTIVE_M4_DATA", active_data)
    monkeypatch.setattr(runtime, "RUNTIME", files["checker"])
    monkeypatch.setattr(runtime, "_prescore_evidence_paths", lambda digest: (check, trace))
    good = "\n".join(["VERDICT: SHIP", "REVIEW_SCOPE: gen9_prescore",
                       "GEN6_IMPLEMENTATION_REVIEW_SHA256: " + runtime.base.sha_file(files["implementation"]),
                       "GEN6_POST_M3_REVIEW_SHA256: " + runtime.base.sha_file(files["post_m3"]),
                       "GEN6_PROTOCOL_SHA256: " + runtime.base.sha_file(active_config / "protocol.json"),
                       "GEN6_STAGE_A_SHA256: " + "a" * 64,
                       "GEN6_STATUS_SHA256: " + runtime.base.sha_file(active_prov / "status.json"),
                       "GEN6_CANDIDATE_MANIFEST_SHA256: " + "c" * 64,
                       "GEN6_DEPENDENCY_CLOSURE_SHA256: " + "b" * 64,
                       "GEN6_ENDPOINT_REGISTRY_SHA256: " + runtime.base.sha_file(active_data / "endpoint_registry.json"),
                       "GEN6_ENVIRONMENT_ALLOWLIST_SHA256: " + runtime.base.sha_file(active_data / "environment_allowlist.json"),
                       "GEN6_PRESCORE_CHECK_SHA256: " + runtime.base.sha_file(check),
                       "GEN6_PRESCORE_TRACE_SHA256: " + runtime.base.sha_file(trace),
                       "GEN6_PRESCORE_CHECKER_SHA256: " + runtime.base.sha_file(files["checker"]),
                       "SEALED_PAYLOAD_CONTENT_READS: 0"])
    runtime._strict_review_verdict(good, manifest, "c" * 64)
    with pytest.raises(ValueError):
        runtime._strict_review_verdict("VERDICT: BLOCK\n" + good, manifest, "c" * 64)
    with pytest.raises(ValueError):
        runtime._strict_review_verdict(good + "\nGEN6_STAGE_A_SHA256: " + "a" * 64, manifest, "c" * 64)
    with pytest.raises(ValueError):
        runtime._strict_review_verdict(good + "\nGEN6_STAGE_A_SHA256: " + "0" * 64, manifest, "c" * 64)
    with pytest.raises(ValueError):
        runtime._strict_review_verdict(good + "\nEXTRA_SHA256: " + "0" * 64, manifest, "c" * 64)
    with pytest.raises(ValueError):
        runtime._strict_review_verdict(good + "\n GEN6_STAGE_A_SHA256: " + "0" * 64, manifest, "c" * 64)
    with pytest.raises(ValueError):
        runtime._strict_review_verdict(" VERDICT: BLOCK\n" + good, manifest, "c" * 64)
    with pytest.raises(ValueError):
        runtime._strict_review_verdict("VERDICT : BLOCK\n" + good, manifest, "c" * 64)
    with pytest.raises(ValueError):
        runtime._strict_review_verdict("VERDICT:\tBLOCK\n" + good, manifest, "c" * 64)


def test_prescore_trace_requires_the_exact_typed_check_payload(tmp_path, monkeypatch):
    data = tmp_path / "data"; data.mkdir()
    prov = tmp_path / "prov"; prov.mkdir()
    manifest = {"candidate_tree_sha256": "a" * 64,
                "repository_status": ["? candidate"],
                "repository_status_classification": [],
                "candidate_files": [{"path": "candidate"}],
                "candidate_directories": [], "quarantined_entries": []}
    manifest_path = prov / "prescore_candidate_manifest.json"
    stage_path = prov / "stage_a.json"
    status_path = prov / "status.json"
    closure_path = data / "dependency_closure.json"
    manifest_path.write_bytes(runtime.base.canonical_bytes(manifest))
    stage_path.write_bytes(runtime.base.canonical_bytes({"stage_ready": True}))
    status_path.write_bytes(runtime.base.canonical_bytes({"status": "ready_prescore_review"}))
    closure_path.write_bytes(runtime.base.canonical_bytes({"entries": []}))
    for path in (manifest_path, stage_path, status_path, closure_path):
        path.chmod(0o644)
    manifest_sha = runtime.base.sha_file(manifest_path)
    check, trace = tmp_path / "check.json", tmp_path / "trace.log"
    monkeypatch.setattr(runtime, "ACTIVE_PROV", prov)
    monkeypatch.setattr(runtime, "ACTIVE_M4_DATA", data)
    monkeypatch.setattr(runtime, "_prescore_evidence_paths", lambda digest: (check, trace))
    monkeypatch.setattr(runtime, "_expected_live_candidate_paths", lambda: {"candidate"})
    monkeypatch.setattr(runtime, "_directory_entries", lambda *a, **k: [])
    monkeypatch.setattr(runtime, "candidate_manifest_payload", lambda *a, **k: manifest)
    monkeypatch.setattr(runtime, "_verify_manifest_entry", lambda row: {
        "path": "candidate", "verification_action": "content_rehash", "result": "match"})
    monkeypatch.setattr(runtime, "_quarantine_manifest_results", lambda value: [])
    monkeypatch.setattr(runtime, "_protected_baseline_results", lambda: {"result": "match"})
    expected = {
        "schema_version": "msae_v3_prescore_check_v3", "protocol_id": runtime.PROTOCOL,
        "phase": "prescore", "manifest_sha256": manifest_sha,
        "checker_code_sha256": "b" * 64, "candidate_tree_sha256": "a" * 64,
        "dependency_closure_sha256": runtime.base.sha_file(closure_path),
        "stage_a_sha256": runtime.base.sha_file(stage_path), "m4_status_sha256": "c" * 64,
        "candidate_file_results": [{"path": "candidate", "result": "match"}],
        "candidate_directory_results": [], "quarantined_metadata_results": [],
        "protected_baseline_results": {"result": "match"},
        "repository_status_projection": manifest["repository_status"],
        "repository_status_classification": [],
        "repository_status_sha256": runtime.base.sha_bytes(
            runtime.base.canonical_bytes(manifest["repository_status"])),
        "candidate_file_count": 1, "candidate_directory_count": 0,
        "quarantined_entry_count": 0, "sealed_payload_content_reads": 0, "eligible": True,
    }
    monkeypatch.setattr(runtime, "_prescore_check_payload", lambda **kwargs: expected)
    check.write_bytes(runtime.base.canonical_bytes(expected)); check.chmod(0o600)
    required = [runtime.continuation.CONTROLLER_PATH, runtime.RUNTIME, manifest_path,
                stage_path, closure_path]
    lines = [f'{i} open("{path.resolve()}", O_RDONLY) = {i + 3}<{path.resolve()}>'
             for i, path in enumerate(required)]
    lines *= 2
    trace.write_text("\n".join(lines) + "\n" + ("#" * 1024) + "\n")
    trace.chmod(0o600)
    assert runtime.verify_prescore_trace(manifest_path, check, trace)["eligible"] is True
    for key in list(expected):
        mutated = copy.deepcopy(expected)
        mutated[key] = None
        check.write_bytes(runtime.base.canonical_bytes(mutated)); check.chmod(0o600)
        with pytest.raises(ValueError, match="prescore check output mismatch"):
            runtime.verify_prescore_trace(manifest_path, check, trace)
    mutated = {**expected, "unexpected": True}
    check.write_bytes(runtime.base.canonical_bytes(mutated)); check.chmod(0o600)
    with pytest.raises(ValueError, match="prescore check output mismatch"):
        runtime.verify_prescore_trace(manifest_path, check, trace)


def test_ldd_inventory_rejects_missing_dependency(monkeypatch, tmp_path):
    executable = tmp_path / "x"; executable.write_bytes(b"\x7fELF")
    monkeypatch.setattr(runtime.subprocess, "run", lambda *a, **k: subprocess.CompletedProcess(
        a[0], 0, "libmissing.so => not found\n", ""))
    with pytest.raises(ValueError, match="unresolved ldd dependency"):
        runtime._ldd_inventory(executable)


def test_ldd_inventory_uses_closed_environment(monkeypatch, tmp_path):
    executable = tmp_path / "x"; executable.write_bytes(b"#!x")
    observed = {}
    def fake(*args, **kwargs):
        observed.update(kwargs["env"])
        return subprocess.CompletedProcess(args[0], 0, "statically linked\n", "")
    monkeypatch.setenv("LD_PRELOAD", "/tmp/escape.so")
    monkeypatch.setenv("LD_LIBRARY_PATH", "/tmp/escape")
    monkeypatch.setattr(runtime.subprocess, "run", fake)
    assert runtime._ldd_inventory(executable) == []
    assert observed == runtime.FROZEN_BASE_PROCESS_ENVIRONMENT


def test_recursive_static_closure_rejects_planted_surface_escapes(tmp_path):
    import shutil
    for relative in runtime.LOCAL_PYTHON_ENTRYPOINTS:
        target = tmp_path / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(ROOT / relative, target)
    runner = tmp_path / "scripts/run_msae_independent_calibration_v3_gen9.py"
    planted = [
        'subprocess.run(["/bin/false"])',
        'Path("/etc/passwd").read_text()',
        'import ctypes; ctypes.CDLL("/tmp/escape.so")',
        'import socket; socket.socket(socket.AF_INET)',
        'subprocess.run("echo escape", shell=True)',
        'getattr(subprocess, "run")(["/bin/false"])',
        'import subprocess as sp; sp.run(["/bin/false"])',
        'alias = subprocess.run; alias(["/bin/false"])',
    ]
    for statement in planted:
        original = runner.read_text()
        runner.write_text(original + "\n" + statement + "\n")
        with pytest.raises(ValueError):
            runtime._static_closure_analysis(root=tmp_path)
        runner.write_text(original)


def test_static_closure_semantically_rejects_literal_and_unregistered_dynamic_file_sites(tmp_path):
    import shutil
    for relative in runtime.LOCAL_PYTHON_ENTRYPOINTS:
        target = tmp_path / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(ROOT / relative, target)
    runner = tmp_path / "scripts/run_msae_independent_calibration_v3_gen9.py"
    original = runner.read_text()
    runner.write_text(original + '\nPath("/etc/passwd").read_text()\n')
    with pytest.raises(ValueError, match="absolute file literal"):
        runtime._static_closure_analysis(root=tmp_path)
    runner.write_text(original + '\ndef planted_dynamic_file(p): return Path(p).read_text()\n')
    # Even treating both aggregate syntax hashes as already reviewed cannot
    # authorize a new site absent from the per-site binding registry.
    with pytest.raises(ValueError, match="lacks a reviewed typed-field binding"):
        runtime._static_closure_analysis(root=tmp_path)


def test_static_closure_rejects_indirect_helper_keyword_and_assignment_path_bypasses(tmp_path):
    import shutil
    for relative in runtime.LOCAL_PYTHON_ENTRYPOINTS:
        target = tmp_path / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(ROOT / relative, target)
    runner = tmp_path / "scripts/run_msae_independent_calibration_v3_gen9.py"
    original = runner.read_text()
    for planted in (
        '\nprotocol.read_json(Path("/etc/passwd"))\n',
        '\nprotocol.read_json(path=Path("/etc/passwd"))\n',
    ):
        runner.write_text(original + planted)
        with pytest.raises(ValueError, match="absolute file literal"):
            runtime._static_closure_analysis(root=tmp_path)
    # Rebind an already-approved sink variable without changing the sink call
    # or either aggregate surface set. Assignment-origin checking must catch it.
    runner.write_text(original.replace(
        '    config_raw = config_path.read_bytes()\n',
        '    config_path = Path("/etc/passwd")\n    config_raw = config_path.read_bytes()\n'))
    with pytest.raises(ValueError, match="assigned literal outside"):
        runtime._static_closure_analysis(root=tmp_path)
    runner.write_text(original.replace(
        '    config_path = runtime.ACTIVE_CONFIG / "protocol.json"\n',
        '    config_path = Path("/etc") / "passwd"\n'))
    with pytest.raises(ValueError, match="assigned literal outside"):
        runtime._static_closure_analysis(root=tmp_path)


def test_static_network_closure_includes_bound_unix_socket_methods():
    operations = {row["operation"] for row in runtime._static_closure_analysis()["surface_calls"]
                  if row["category"] == "network"}
    assert {"sock.connect", "server.bind", "server.listen", "server.accept",
            "connection.sendmsg", "connection.getsockopt"} <= operations


def test_static_dynamic_imports_have_exact_site_specific_targets(tmp_path):
    import shutil
    value = runtime._static_closure_analysis()
    targets = {tuple(row["finite_mapping"]) for row in value["dynamic_import_mappings"]}
    assert {
        ("scripts/msae_independent_measurement_v3.py",),
        ("scripts/run_msae_independent_calibration_v3.py",),
        ("scripts/run_msae_independent_calibration_v3_gen9.py",),
        ("scripts/msae_measurement_v2.py",),
        ("scripts/msae_measurement_remediation_v1.py",),
    } <= targets
    gen3_dynamic = [row for row in value["dynamic_import_mappings"]
                    if row["path"].endswith("post_m2_gen9_runtime.py")]
    assert gen3_dynamic and all(
        row["operation"] == "continuation.source_only_module_spec"
        for row in gen3_dynamic)
    policy = value["source_only_local_import_policy"]
    assert policy["bytecode_cache_reads"] is False
    assert policy["default_scripts_directory_search"] is False
    assert policy["ignored_sourceless_or_extension_shadowing"] is False
    assert set(policy["modules"]) == {
        Path(relative).stem for relative in runtime.LOCAL_PYTHON_ENTRYPOINTS
        if relative !=
        "scripts/run_msae_independent_measurement_v3_post_m2_gen9_tmux_test.py"}
    for relative in runtime.LOCAL_PYTHON_ENTRYPOINTS:
        target = tmp_path / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(ROOT / relative, target)
    module = tmp_path / "scripts/msae_independent_measurement_v3_post_m2_gen9_runtime.py"
    original = module.read_text()
    module.write_text(original.replace(
        'continuation.source_only_module_spec(module_name, builder_path)',
        'continuation.source_only_module_spec(module_name, candidate_root / '
        '"scripts/run_msae_independent_calibration_v3_gen9.py")', 1))
    with pytest.raises(ValueError, match="dynamic import site lacks an exact mapping"):
        runtime._static_closure_analysis(root=tmp_path)


def test_static_value_flow_ledger_closes_caller_argv_and_helper_return_bypasses(tmp_path):
    import shutil
    for relative in runtime.LOCAL_PYTHON_ENTRYPOINTS:
        target = tmp_path / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(ROOT / relative, target)
    module = tmp_path / "scripts/msae_independent_measurement_v3_post_m2_gen9_runtime.py"
    original = module.read_text()
    module.write_text(original.replace(
        'argv = [str(ROOT / ".venv-atlas/bin/python"), "-S", "-B", "-I",\n'
        '            str(continuation.CONTROLLER_PATH), "broker-gen9",',
        'argv = ["/bin/false", "-S", "-B", "-I",\n'
        '            str(continuation.CONTROLLER_PATH), "broker-gen9",', 1))
    with pytest.raises(ValueError, match="local value-flow AST ledger drift"):
        runtime._static_closure_analysis(root=tmp_path)


def test_static_ledger_self_exclusions_are_syntactically_inert(tmp_path):
    import shutil
    for relative in runtime.LOCAL_PYTHON_ENTRYPOINTS:
        target = tmp_path / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(ROOT / relative, target)
    module = tmp_path / "scripts/msae_independent_measurement_v3_post_m2_gen9_runtime.py"
    original = module.read_text()
    module.write_text(original.replace(
        f'FROZEN_LOCAL_VALUE_FLOW_AST_SHA256 = "{runtime.FROZEN_LOCAL_VALUE_FLOW_AST_SHA256}"',
        'FROZEN_LOCAL_VALUE_FLOW_AST_SHA256 = (base.launch(), "' +
        runtime.FROZEN_LOCAL_VALUE_FLOW_AST_SHA256 + '")[1]'))
    with pytest.raises(ValueError, match="digest constant is not inert"):
        runtime._static_closure_analysis(root=tmp_path)
    module.write_text(original.replace(
        '    return Path(f"{prefix}.prescore.check.json"), Path(f"{prefix}.prescore.trace.log")',
        '    return Path("/etc/passwd"), Path("/etc/shadow")'))
    with pytest.raises(ValueError, match="local value-flow AST ledger drift"):
        runtime._static_closure_analysis(root=tmp_path)


def test_cpu_no_model_trace_executes_every_public_entry_and_planted_tripwires():
    value = runtime.cpu_no_model_public_entry_trace()
    assert value["status"] == "eligible" and value["model_imports"] == 0
    assert value["entrypoints"] == list(runtime.PUBLIC_EXECUTION_ENTRYPOINTS)
    assert [row["entrypoint"] for row in value["results"]] == list(
        runtime.PUBLIC_EXECUTION_ENTRYPOINTS)
    assert all(row["outcome"] != "prescore_rejected:_SurfaceProbeViolation"
               for row in value["results"])
    assert {"indirect_open", "dynamic_subprocess", "shell_expansion", "bash_command",
            "dlopen_escape", "network_escape"} <= set(value["tripwire_proofs"])
    assert value["finite_file_registry"]["schema_version"] == \
        "msae_v3_finite_file_registry_v1"
    assert value["finite_process_registry"]["schema_version"] == \
        "msae_v3_finite_process_registry_v1"
    process_registry = value["finite_process_registry"]
    declared_process_ids = ({row["id"] for row in process_registry["exact_argv"]} |
                            {row["id"] for row in process_registry["templates"]})
    process_requests = [row for row in value["allowed_requests"]
                        if row["category"] == "process"]
    assert process_requests
    assert all(len(row["registry_entry_ids"]) == 1 for row in process_requests)
    assert all(row["registry_entry_ids"][0] in declared_process_ids
               for row in process_requests)
    assert any(row["registry_entry_ids"] == ["isolated_python_worker_execve"]
               for row in process_requests)


def test_cpu_trace_validator_rejects_process_registry_substitution(monkeypatch):
    gates = {
        "plan_sha256": runtime.FROZEN_PLAN_SHA256,
        "plan_entry": {}, "plan_review_sha256": "a" * 64,
        "plan_review_entry": {}, "pre_capability_review_sha256": "c" * 64,
        "pre_capability_review_entry": {},
        "implementation_review_sha256": "b" * 64,
        "implementation_review_entry": {},
    }
    value = runtime.cpu_no_model_public_entry_trace(review_gates=gates)
    monkeypatch.setattr(runtime, "_trace_review_gates", lambda *args: gates)
    mutated = copy.deepcopy(value)
    mutated["finite_process_registry"]["templates"][0]["id"] = "forged"
    with pytest.raises(ValueError, match="finite process registry drift"):
        runtime._validate_cpu_no_model_trace(
            mutated, root=ROOT, checkpoints=runtime.checkpoint_registry())


def test_model_snapshot_exact_set_rejects_extra_missing_and_outbound_symlink(tmp_path):
    snapshot = tmp_path / "cache/hub/snapshots/revision"
    snapshot.mkdir(parents=True)
    for name in runtime.EXPECTED_MODEL_SNAPSHOT_NAMES:
        (snapshot / name).write_bytes(name.encode())
    assert len(runtime._model_snapshot_entries(snapshot)) == 5
    (snapshot / "extra.bin").write_bytes(b"x")
    with pytest.raises(ValueError, match="filename set drift"):
        runtime._model_snapshot_entries(snapshot)
    (snapshot / "extra.bin").unlink()
    missing = snapshot / "config.json"; missing.unlink()
    with pytest.raises(ValueError, match="missing"):
        runtime._model_snapshot_entries(snapshot)
    outside = tmp_path / "outside.json"; outside.write_bytes(b"outside")
    missing.symlink_to(outside)
    with pytest.raises(ValueError, match="escapes frozen cache root"):
        runtime._model_snapshot_entries(snapshot)


def test_candidate_projection_contains_every_protected_predecessor_path():
    candidate = set(runtime._candidate_relatives(include_m4=True))
    for name in ("protected_v1_manifest.json", "protected_v2_manifest.json"):
        protected = runtime.base.read_json(runtime.V3_DATA / name)
        assert {row["path"] for row in protected["entries"]} <= candidate


def test_overlay_never_falls_back_to_live_tree(tmp_path):
    with pytest.raises(FileNotFoundError, match="candidate-root input is absent"):
        runtime._overlay("TODO.md", tmp_path)


def test_rooted_generic_stage_builder_does_not_use_live_cached_dependency(tmp_path):
    scripts = tmp_path / "scripts"; scripts.mkdir()
    for name in ("msae_measurement_v2.py", "msae_measurement_remediation_v1.py"):
        source = ROOT / "scripts" / name
        target = scripts / name
        target.write_bytes(source.read_bytes())
        target.chmod(0o700)
    with (scripts / "msae_measurement_v2.py").open("ab") as handle:
        handle.write(b"\n# planted candidate-tree drift\n")
    raw = (ROOT / "configs/msae_measurement_remediation_v1/draft.json").read_bytes()
    with pytest.raises(ValueError, match="dependency digest mismatch"):
        runtime._rooted_generic_build_stage_a(
            tmp_path, raw, runtime.base.sha_bytes(raw), {})


def test_repository_classification_reads_only_explicit_tree(tmp_path):
    data = tmp_path / "data/msae_independent_measurement_v3"; data.mkdir(parents=True)
    for name in ("protected_v1_manifest.json", "protected_v2_manifest.json",
                 "data_baseline_manifest.json"):
        (data / name).write_text('{"entries":[]}\n')
    rows = runtime._classify_repository_status(["? candidate.txt"], {"candidate.txt"}, root=tmp_path)
    assert rows == [{"line": "? candidate.txt", "path_projection": "candidate.txt",
                     "classification": "candidate"}]


def test_repository_status_rejects_unclassified_path(monkeypatch):
    monkeypatch.setattr(runtime.base, "read_json", lambda path: {"entries": []})
    with pytest.raises(ValueError, match="unclassified"):
        runtime._classify_repository_status(["? surprise.txt"], {"candidate.txt"})


def test_generic_transaction_recovers_all_boundaries(tmp_path, monkeypatch):
    root = tmp_path / "txn"
    repo = tmp_path / "repo"
    repo.mkdir()
    relatives = runtime.M4_NEW
    payloads = {relative: (relative + "\n").encode() for relative in relatives}
    for relative in relatives:
        (repo / relative).parent.mkdir(parents=True, exist_ok=True)
        (repo / relative).parent.chmod(0o700)
    monkeypatch.setattr(runtime, "ROOT", repo)
    fake_mount = {
        "schema_version": "msae_v3_gen9_mount_identity_v1",
        "mountinfo": {"filesystem_type": "nfs4"},
        "mountinfo_sha256": "a" * 64,
        "filesystem_magic": "0x6969", "filesystem_fsid": [1, 2],
        "directory_device": repo.stat().st_dev,
    }
    monkeypatch.setattr(runtime, "_mount_identity", lambda _path: dict(fake_mount))
    original = runtime._linkat
    def interrupted(source_fd, source, destination_fd, destination):
        if destination == Path(relatives[1]).name:
            raise OSError(runtime.errno.EIO, "injected")
        return original(source_fd, source, destination_fd, destination)

    monkeypatch.setattr(runtime, "_linkat", interrupted)
    with pytest.raises(runtime.RecoverableLinkInterruption, match="retained exact source"):
        runtime._install_transaction(root, relatives, payloads, "test")
    monkeypatch.setattr(runtime, "_linkat", original)
    runtime._install_transaction(root, relatives, payloads, "test")
    assert not root.exists()
    assert all((repo / relative).read_bytes() == payloads[relative] for relative in relatives)


def test_transaction_rejects_partial_targets_after_transaction_root_loss(
        tmp_path, monkeypatch):
    repo = tmp_path / "repo"; repo.mkdir()
    txn = tmp_path / "lost-then-recreated-transaction"
    relatives = runtime.M4_NEW
    payloads = {relative: (relative + "\n").encode() for relative in relatives}
    first = repo / relatives[0]; first.parent.mkdir(parents=True)
    first.write_bytes(payloads[relatives[0]]); first.chmod(0o644)
    monkeypatch.setattr(runtime, "ROOT", repo)
    with pytest.raises(ValueError, match="transaction missing"):
        runtime._install_transaction(txn, relatives, payloads, "test")
    assert not txn.exists() and not (repo / relatives[1]).exists()


def test_recovery_rejects_nonprefix_installed_output_set():
    relatives = ("first", "second", "third")
    runtime._require_ordered_output_prefix(
        relatives, {"first": True, "second": True, "third": False})
    for states in (
        {"first": False, "second": True, "third": False},
        {"first": True, "second": False, "third": True},
    ):
        with pytest.raises(ValueError, match="ordered prefix"):
            runtime._require_ordered_output_prefix(relatives, states)


def test_public_m4_gate_recovers_validated_crash_left_tree_before_rebuild(
        tmp_path, monkeypatch):
    primary = tmp_path / "primary"; primary.mkdir(mode=0o700)
    (primary / "partial").write_text("partial\n")
    rebuild = tmp_path / "rebuild"
    transaction = tmp_path / "transaction"; transaction.mkdir(mode=0o700)
    monkeypatch.setattr(runtime, "M4_PRIMARY", primary)
    monkeypatch.setattr(runtime, "M4_REBUILD", rebuild)
    monkeypatch.setattr(runtime, "M4_TRANSACTION", transaction)
    monkeypatch.setattr(runtime, "M4_NEW", tuple())
    monkeypatch.setattr(runtime, "quarantine_guard", contextlib.nullcontext)
    calls = []
    def review(digest, *, allow_m4_recovery=False):
        calls.append(("review", allow_m4_recovery))
        return {"review": {"sha256": digest}}
    def build(digest, *, allow_m4_recovery=False):
        calls.append(("build", allow_m4_recovery))
        # The implementation owns descriptor validation and safe recursive
        # cleanup; the public gate must not blindly remove untrusted trees.
        assert primary.exists() and not rebuild.exists()
        assert transaction.exists()
        return {"stage_ready": True}
    monkeypatch.setattr(runtime, "verify_post_m3_review", review)
    monkeypatch.setattr(runtime, "_build_m4_impl", build)
    result = runtime.build_m4("a" * 64)
    assert result["stage_ready"] is True
    assert calls == [("review", True), ("build", True)]


def test_transaction_rejects_undeclared_staging_entry(tmp_path, monkeypatch):
    repo = tmp_path / "repo"; repo.mkdir()
    txn = tmp_path / "txn"; txn.mkdir(mode=0o700)
    (txn / "evil").write_text("x")
    monkeypatch.setattr(runtime, "ROOT", repo)
    payloads = {relative: relative.encode() for relative in runtime.M4_NEW}
    for relative in runtime.M4_NEW:
        (repo / relative).parent.mkdir(parents=True, exist_ok=True)
    with pytest.raises(ValueError, match="unbound|extras"):
        runtime._install_transaction(txn, runtime.M4_NEW, payloads, "test")
    assert not (repo / "x").exists()


def test_transaction_descriptor_rejects_symlink_identity(tmp_path, monkeypatch):
    repo = tmp_path / "repo"; repo.mkdir()
    txn = tmp_path / "txn"; txn.mkdir(mode=0o700)
    relatives = runtime.M4_NEW
    payloads = {relative: relative.encode() for relative in relatives}
    for relative in relatives:
        (repo / relative).parent.mkdir(parents=True, exist_ok=True)
    relative, raw = relatives[0], payloads[relatives[0]]
    entry = {"relative": relative, "staged": "00.payload", "size": len(raw),
             "sha256": runtime.base.sha_bytes(raw), "mode": 0o644}
    descriptor = runtime.base.canonical_bytes({"schema_version": "test",
                                                "protocol_id": runtime.PROTOCOL,
                                                "entries": [entry],
                                                "entries_sha256": runtime.base.sha_bytes(
                                                    runtime.base.canonical_bytes([entry]))})
    (txn / "00.payload").write_bytes(raw); (txn / "00.payload").chmod(0o600)
    backing = tmp_path / "descriptor"; backing.write_bytes(descriptor); backing.chmod(0o600)
    (txn / "transaction.json").symlink_to(backing)
    monkeypatch.setattr(runtime, "ROOT", repo)
    with pytest.raises(OSError):
        runtime._install_transaction(txn, relatives, payloads, "test")


def test_complete_m4_comparison_covers_nonoutput_inputs(tmp_path):
    left, right = tmp_path / "left", tmp_path / "right"
    for root in (left, right):
        (root / "ordinary.txt").parent.mkdir(parents=True, exist_ok=True)
        (root / "ordinary.txt").write_text("same\n")
        for relative in runtime.M4_NEW:
            path = root / relative; path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes((relative + "\n").encode())
            path.chmod(0o644)
    payloads = runtime._compare_complete_m4_trees(left, right, {"ready": True}, {"ready": True})
    assert set(payloads) == set(runtime.M4_NEW)
    (right / "ordinary.txt").write_text("different\n")
    with pytest.raises(ValueError, match="complete M4 trees differ"):
        runtime._compare_complete_m4_trees(left, right, {"ready": True}, {"ready": True})


def test_two_root_m4_materialization_wires_real_extension_and_manifest_without_live_fallback(
        tmp_path, monkeypatch):
    left, right, projection_root = (tmp_path / name for name in ("left", "right", "projection"))
    fixed = {
        runtime.PLAN_PATH.relative_to(runtime.ROOT),
        runtime.PLAN_REVIEW.relative_to(runtime.ROOT),
        runtime.IMPLEMENTATION_REVIEW.relative_to(runtime.ROOT),
        runtime.POST_M3_REVIEW.relative_to(runtime.ROOT),
        runtime.continuation.CONTROLLER_PATH.relative_to(runtime.ROOT),
        runtime.immutable_continuation.CONTROLLER_PATH.relative_to(runtime.ROOT),
        runtime.RUNTIME.relative_to(runtime.ROOT), runtime.RUNNER.relative_to(runtime.ROOT),
        runtime.LAUNCHER.relative_to(runtime.ROOT), runtime.RUNTIME_RFC.relative_to(runtime.ROOT),
        runtime.RUNTIME_TEST.relative_to(runtime.ROOT),
        runtime.GEN2_FAILURE_PATH.relative_to(runtime.ROOT),
        runtime.ACTIVE_CONFIG.relative_to(runtime.ROOT) / "protocol.json",
        runtime.ACTIVE_CONFIG.relative_to(runtime.ROOT) / "authorization_commitment.json",
        runtime.ACTIVE_CONFIG.relative_to(runtime.ROOT) / "ed25519_public.pem",
        runtime.CPU_NO_MODEL_TRACE.relative_to(runtime.ROOT),
        runtime.immutable_continuation.CONTINUATION_RFC.relative_to(runtime.ROOT),
        runtime.immutable_continuation.CONTINUATION_TEST.relative_to(runtime.ROOT),
        runtime.immutable_continuation.M1_COMPLETION_PATH.relative_to(runtime.ROOT),
        Path("data/msae_independent_measurement_v3/protected_v1_manifest.json"),
        Path("data/msae_independent_measurement_v3/protected_v2_manifest.json"),
        Path("data/msae_independent_measurement_v3/data_baseline_manifest.json"),
    }
    candidate_relatives = sorted(
        {item.as_posix() for item in fixed} | set(runtime.M4_NEW[:-1]))

    def seed(root, **_kwargs):
        root.mkdir(mode=0o700)
        for relative in fixed:
            target = root / relative; target.parent.mkdir(parents=True, exist_ok=True)
            if target.name in {"protected_v1_manifest.json", "protected_v2_manifest.json",
                               "data_baseline_manifest.json"}:
                raw = b'{"entries":[]}\n'
            elif target.name == "authorization_commitment.json":
                raw = runtime.base.canonical_bytes({
                    "private_key_binding": {}, "nonce_directory": {}})
            else:
                raw = (relative.as_posix() + "\n").encode()
            target.write_bytes(raw); target.chmod(0o644)
        for relative in runtime.M4_NEW:
            (root / relative).parent.mkdir(parents=True, exist_ok=True)

    seed(projection_root)
    for relative in runtime.M4_NEW[:-1]:
        target = projection_root / relative
        target.write_text("placeholder\n"); target.chmod(0o644)
    directories = runtime._directory_entries(projection_root, candidate_relatives)

    monkeypatch.setattr(runtime, "_copy_complete_candidate_tree", seed)
    allowed_roots = {left, right}
    def checkpoints(*, root=runtime.ROOT):
        if root not in allowed_roots:
            raise AssertionError(f"live checkpoint fallback: {root}")
        return []
    monkeypatch.setattr(runtime, "checkpoint_registry", checkpoints)
    monkeypatch.setattr(runtime, "_candidate_relatives",
                        lambda **kwargs: candidate_relatives)
    monkeypatch.setattr(runtime, "endpoint_registry",
                        lambda: {"schema_version": "registry", "entries": []})
    monkeypatch.setattr(runtime, "environment_payload",
                        lambda closure, *, root=runtime.ROOT: {
                            "schema_version": "environment",
                            "closure_sha256": runtime.base.sha_bytes(
                                runtime.base.canonical_bytes(closure))})
    monkeypatch.setattr(runtime, "stage_a_payload",
                        lambda *, overlay_root=None: {
                            "schema_version": "stage", "stage_ready": True})
    monkeypatch.setattr(runtime, "closure_payload",
                        lambda checkpoints, *, root=runtime.ROOT:
                        runtime._extend_rooted_closure(
                            {"schema_version": "closure", "entries": []}, root=root))
    original_regular = runtime._regular_entry
    def no_live_regular(path, *, root=runtime.ROOT):
        if Path(path).is_relative_to(runtime.ROOT):
            raise AssertionError(f"live repository fallback: {path}")
        return original_regular(Path(path), root=root)
    monkeypatch.setattr(runtime, "_regular_entry", no_live_regular)
    descriptor = {"schema_version": "test"}
    left_stage = runtime._materialize_complete_m4(
        left, [], [], directories, build_descriptor=descriptor)
    right_stage = runtime._materialize_complete_m4(
        right, [], [], directories, build_descriptor=descriptor)
    payloads = runtime._compare_complete_m4_trees(
        left, right, left_stage, right_stage)
    assert set(payloads) == set(runtime.M4_NEW)


def test_candidate_manifest_construction_uses_only_explicit_tree_root(tmp_path, monkeypatch):
    tree = tmp_path / "tree"
    (tree / "data/msae_independent_measurement_v3").mkdir(parents=True)
    for name in ("protected_v1_manifest.json", "protected_v2_manifest.json",
                 "data_baseline_manifest.json"):
        (tree / "data/msae_independent_measurement_v3" / name).write_text('{"entries":[]}\n')
    for relative in (runtime.M4_NEW[0], runtime.M4_NEW[3]):
        path = tree / relative; path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("{}\n")
    commitment = tree / runtime.ACTIVE_CONFIG.relative_to(runtime.ROOT) / "authorization_commitment.json"
    commitment.parent.mkdir(parents=True, exist_ok=True)
    commitment.write_text('{"private_key_binding":{},"nonce_directory":{}}\n')
    observed_roots = []
    def checkpoints(*, root=runtime.ROOT):
        observed_roots.append(root)
        if root == runtime.ROOT:
            raise AssertionError("live checkpoint fallback")
        return []
    monkeypatch.setattr(runtime, "checkpoint_registry", checkpoints)
    monkeypatch.setattr(runtime, "_candidate_relatives",
                        lambda *, include_m4, root=runtime.ROOT, checkpoints=None: [])
    value = runtime.candidate_manifest_payload(tree, [], [])
    assert value["candidate_files"] == []
    assert observed_roots == [tree]


def test_anticipated_status_matches_git_semantics_for_ignored_m4_data(monkeypatch):
    ignored_data = runtime.M4_NEW[:3]
    for relative in ignored_data:
        result = subprocess.run(
            ["/usr/bin/git", "check-ignore", "--quiet", relative],
            cwd=runtime.ROOT, check=False)
        assert result.returncode == 0, relative
    monkeypatch.setattr(runtime, "_git_status", lambda: ["? existing.txt"])
    projected = runtime._anticipated_status()
    assert "? existing.txt" in projected
    assert all(f"? {relative}" not in projected for relative in ignored_data)
    assert all(f"? {relative}" in projected for relative in runtime.M4_NEW[3:-1])
    assert f"? {runtime.M4_NEW[-1]}" not in projected


def test_anticipated_status_normalizes_crash_left_transaction_and_m4_prefix(monkeypatch):
    transaction = runtime.M4_TRANSACTION.relative_to(runtime.ROOT).as_posix()
    monkeypatch.setattr(runtime, "_git_status", lambda: [
        "? ordinary.txt", f"? {transaction}/transaction.json",
        *(f"? {relative}" for relative in runtime.M4_NEW),
    ])
    projected = runtime._anticipated_status()
    assert "? ordinary.txt" in projected
    assert all(not line.startswith(f"? {transaction}") for line in projected)
    assert all(f"? {relative}" not in projected for relative in runtime.M4_NEW[:3])
    assert all(f"? {relative}" in projected for relative in runtime.M4_NEW[3:-1])
    assert f"? {runtime.M4_NEW[-1]}" not in projected


def test_recovery_manifest_directory_projection_removes_only_transaction_nlink(
        tmp_path, monkeypatch):
    repo = tmp_path / "repo"; provenance = repo / "provenance"
    provenance.mkdir(parents=True)
    transaction = provenance / ".transaction"; transaction.mkdir(mode=0o700)
    monkeypatch.setattr(runtime, "ROOT", repo)
    monkeypatch.setattr(runtime, "M4_TRANSACTION", transaction)
    current = [{"path": "provenance", "type": "directory", "mode": 0o755,
                "uid": os.getuid(), "nlink": provenance.stat().st_nlink}]
    projected = runtime._historical_manifest_directory_projection(current, recovery=True)
    assert projected[0]["nlink"] == current[0]["nlink"] - 1
    assert current[0]["nlink"] == provenance.stat().st_nlink


def test_m4_live_reauthorization_rejects_drift(tmp_path, monkeypatch):
    repo = tmp_path / "repo"; repo.mkdir()
    item = repo / "x"; item.write_text("one\n"); item.chmod(0o644)
    monkeypatch.setattr(runtime, "ROOT", repo)
    monkeypatch.setattr(runtime, "_git_status", lambda: ["? x"])
    monkeypatch.setattr(runtime, "_candidate_relatives", lambda **kwargs: ["x"])
    monkeypatch.setattr(runtime.base, "verify_baseline_projection", lambda phase: {})
    monkeypatch.setattr(runtime.base, "verify_protected_v1", lambda: 372)
    monkeypatch.setattr(runtime.base, "verify_protected_v2", lambda: 14)
    monkeypatch.setattr(runtime.base, "validate_source_exposure", lambda: {})
    snapshot = runtime._tree_entries(repo, ["x"])
    runtime._verify_live_m4_inputs(snapshot, ["? x"], [])
    item.write_text("two\n")
    with pytest.raises(ValueError, match="inputs drifted"):
        runtime._verify_live_m4_inputs(snapshot, ["? x"], [])


@pytest.mark.parametrize("defect", ["symlink", "mode", "hardlink"])
def test_transaction_rejects_existing_target_identity_defects(tmp_path, monkeypatch, defect):
    repo = tmp_path / "repo"; repo.mkdir()
    target = repo / "x"
    raw = b"x"
    if defect == "symlink":
        backing = tmp_path / "backing"; backing.write_bytes(raw)
        target.symlink_to(backing)
    else:
        target.write_bytes(raw)
        target.chmod(0o600 if defect == "mode" else 0o644)
        if defect == "hardlink":
            os.link(target, tmp_path / "second")
    monkeypatch.setattr(runtime, "ROOT", repo)
    with pytest.raises((ValueError, OSError)):
        runtime._install_transaction(tmp_path / "absent", ("x",), {"x": raw}, "test")


def test_terminal_success_and_failure_are_mutually_exclusive(tmp_path):
    run = tmp_path / "run"; run.mkdir(mode=0o700)
    runtime.commit_terminal_success(run, terminal_files())
    assert (run / "terminal_success/stage_b.json").is_file()
    assert runtime.commit_terminal_failure(run, {"status": "not_run"}) is False
    assert not (run / "terminal_failure").exists()


def test_terminal_failure_prevents_stage_b_exposure(tmp_path):
    run = tmp_path / "run"; run.mkdir(mode=0o700)
    assert runtime.commit_terminal_failure(run, {"status": "not_run"}) is True
    with pytest.raises(FileExistsError):
        runtime.commit_terminal_success(run, terminal_files())
    assert not (run / "terminal_success/stage_b.json").exists()


def test_interrupted_success_is_recoverable_as_failure(tmp_path, monkeypatch):
    run = tmp_path / "run"; run.mkdir(mode=0o700)
    original = runtime.base.write_once
    calls = 0

    def fail_second(path, payload, mode=0o644):
        nonlocal calls
        if ".terminal_success_staging" in str(path):
            calls += 1
            if calls == 2:
                raise OSError("injected success write failure")
        return original(path, payload, mode)

    monkeypatch.setattr(runtime.base, "write_once", fail_second)
    with pytest.raises(OSError, match="injected"):
        runtime.commit_terminal_success(run, terminal_files())
    monkeypatch.setattr(runtime.base, "write_once", original)
    assert runtime.commit_terminal_failure(run, {"status": "not_run"}) is True
    assert (run / "terminal_failure/status.json").is_file()
    assert not (run / "terminal_success").exists()


def test_gpu_lock_validator_checks_content_and_identity(tmp_path, monkeypatch):
    config = tmp_path / "config"; config.mkdir(mode=0o700)
    locks = tmp_path / "locks"; locks.mkdir(mode=0o700)
    uuid = "GPU-1234567890abcdef"
    name = runtime.base.sha_bytes(uuid.encode("ascii")) + ".lock"
    lock = locks / name
    lock.write_bytes(runtime.base.canonical_bytes({"schema_version": "msae_gpu_uuid_lock_v1",
                                                   "gpu_uuid": uuid}))
    lock.chmod(0o600)
    commitment = {"gpu_lock_directory": runtime.base._directory_binding(locks)}
    (config / "authorization_commitment.json").write_bytes(runtime.base.canonical_bytes(commitment))
    monkeypatch.setattr(runtime, "ACTIVE_CONFIG", config)
    monkeypatch.setattr(runtime.base, "GPU_LOCK_DIR", locks)
    fd = os.open(lock, os.O_RDWR | os.O_NOFOLLOW)
    try:
        assert runtime._validate_gpu_lock_fd(fd, uuid)["inode"] == os.fstat(fd).st_ino
        os.ftruncate(fd, 0); os.write(fd, b"bad"); os.fsync(fd)
        with pytest.raises(ValueError, match="content drift"):
            runtime._validate_gpu_lock_fd(fd, uuid)
    finally:
        os.close(fd)


def test_gpu_lock_acquisition_contends_and_path_substitution_blocks(tmp_path, monkeypatch):
    config = tmp_path / "config"; config.mkdir(mode=0o700)
    locks = tmp_path / "locks"; locks.mkdir(mode=0o700)
    uuid = "GPU-1234567890abcdef"
    commitment = {"gpu_lock_directory": runtime.base._directory_binding(locks)}
    (config / "authorization_commitment.json").write_bytes(runtime.base.canonical_bytes(commitment))
    monkeypatch.setattr(runtime, "ACTIVE_CONFIG", config)
    monkeypatch.setattr(runtime.base, "GPU_LOCK_DIR", locks)
    fd, directory_fd, path = runtime._open_gpu_lock(uuid)
    try:
        with pytest.raises(BlockingIOError):
            runtime._open_gpu_lock(uuid)
        displaced = tmp_path / "displaced.lock"
        path.rename(displaced)
        path.write_bytes(runtime.base.canonical_bytes(
            {"schema_version": "msae_gpu_uuid_lock_v1", "gpu_uuid": uuid}))
        path.chmod(0o600)
        with pytest.raises(ValueError, match="FD/path"):
            runtime._validate_gpu_lock_fd(fd, uuid)
    finally:
        os.close(fd); os.close(directory_fd)


def test_gpu_lock_short_writes_are_completed_and_zero_write_stays_retryable(tmp_path, monkeypatch):
    config = tmp_path / "config"; config.mkdir(mode=0o700)
    locks = tmp_path / "locks"; locks.mkdir(mode=0o700)
    uuid = "GPU-1234567890abcdef"
    commitment = {"gpu_lock_directory": runtime.base._directory_binding(locks)}
    (config / "authorization_commitment.json").write_bytes(
        runtime.base.canonical_bytes(commitment))
    monkeypatch.setattr(runtime, "ACTIVE_CONFIG", config)
    monkeypatch.setattr(runtime.base, "GPU_LOCK_DIR", locks)
    original_write = os.write

    def short_write(fd, payload):
        return original_write(fd, payload[:max(1, len(payload) // 3)])

    monkeypatch.setattr(runtime.os, "write", short_write)
    fd, directory_fd, path = runtime._open_gpu_lock(uuid)
    try:
        expected = runtime.base.canonical_bytes(
            {"schema_version": "msae_gpu_uuid_lock_v1", "gpu_uuid": uuid})
        assert path.read_bytes() == expected
    finally:
        os.close(fd); os.close(directory_fd)

    path.unlink()
    monkeypatch.setattr(runtime.os, "write", lambda _fd, _payload: 0)
    with pytest.raises(OSError, match="zero-length write"):
        runtime._open_gpu_lock(uuid)
    assert path.read_bytes() == b""
    monkeypatch.setattr(runtime.os, "write", original_write)
    fd, directory_fd, _ = runtime._open_gpu_lock(uuid)
    os.close(fd); os.close(directory_fd)


def test_gpu_flock_contention_is_real_cross_process(tmp_path, monkeypatch):
    config = tmp_path / "config"; config.mkdir(mode=0o700)
    locks = tmp_path / "locks"; locks.mkdir(mode=0o700)
    uuid = "GPU-1234567890abcdef"
    commitment = {"gpu_lock_directory": runtime.base._directory_binding(locks)}
    (config / "authorization_commitment.json").write_bytes(runtime.base.canonical_bytes(commitment))
    monkeypatch.setattr(runtime, "ACTIVE_CONFIG", config)
    monkeypatch.setattr(runtime.base, "GPU_LOCK_DIR", locks)
    fd, directory_fd, path = runtime._open_gpu_lock(uuid)
    code = ("import fcntl,os,sys; fd=os.open(sys.argv[1],os.O_RDWR); "
            "\ntry: fcntl.flock(fd,fcntl.LOCK_EX|fcntl.LOCK_NB); print('acquired')"
            "\nexcept BlockingIOError: print('blocked')")
    try:
        child = subprocess.run([sys.executable, "-c", code, str(path)], check=True,
                               text=True, capture_output=True)
        assert child.stdout.strip() == "blocked"
    finally:
        os.close(fd); os.close(directory_fd)


def test_internal_broker_requires_live_launcher_capability_before_socket_or_gpu(tmp_path, monkeypatch):
    run = tmp_path / "run"; run.mkdir(mode=0o700)
    monkeypatch.setattr(runtime, "ACTIVE_RUN_ROOT", run)
    monkeypatch.setattr(runtime, "LAUNCH_INTENT", run / "launcher_intent.json")
    touched = []
    monkeypatch.setattr(runtime.socket, "socket", lambda *args, **kwargs: touched.append(args))
    socket_path = "/tmp/m9b_" + "a" * 64 + ".sock"
    with pytest.raises(FileNotFoundError):
        runtime.broker(socket_path, "GPU-1234567890abcdef", 0,
                       "a" * 64, "b" * 64)
    assert touched == [] and not (run / "logs").exists()


def test_launcher_intent_binds_capability_socket_gpu_and_lease(tmp_path, monkeypatch):
    run = tmp_path / "run"; run.mkdir(mode=0o700)
    prov = tmp_path / "prov"; prov.mkdir(mode=0o700)
    locks = tmp_path / "locks"; locks.mkdir(mode=0o700)
    stage = prov / "stage_a.json"; stage.write_text("{}\n"); stage.chmod(0o644)
    authorization = run / "authorization.json"; authorization.write_text("{}\n")
    authorization.chmod(0o600)
    uuid = "GPU-1234567890abcdef"
    lock = locks / (runtime.base.sha_bytes(uuid.encode("ascii")) + ".lock")
    lock.write_bytes(runtime.base.canonical_bytes(
        {"schema_version": "msae_gpu_uuid_lock_v1", "gpu_uuid": uuid}))
    lock.chmod(0o600)
    capability = "a" * 64
    pid = os.getpid(); ticks = runtime.base._start_ticks(pid)
    tmux_socket, broker_socket, pane_socket = runtime._tmux_paths(
        runtime.base.sha_file(stage))
    intent = {"schema_version": "msae_v3_launcher_intent_v1",
              "protocol_id": runtime.PROTOCOL, "socket_path": str(broker_socket),
              "tmux_socket_path": str(tmux_socket),
              "pane_socket_path": str(pane_socket),
              "gpu_uuid": uuid, "gpu_index": 0, "lock_path": str(lock),
              "lock_device": lock.stat().st_dev, "lock_inode": lock.stat().st_ino,
              "stage_a_sha256": runtime.base.sha_file(stage),
              "authorization_envelope_sha256": runtime.base.sha_file(authorization),
              "launch_capability_sha256": runtime.base.sha_bytes(capability.encode("ascii")),
              "launcher_pid": pid, "launcher_start_ticks": ticks}
    intent_path = run / "launcher_intent.json"
    intent_path.write_bytes(runtime.base.canonical_bytes(intent)); intent_path.chmod(0o600)
    monkeypatch.setattr(runtime, "ACTIVE_RUN_ROOT", run)
    monkeypatch.setattr(runtime, "LAUNCH_INTENT", intent_path)
    monkeypatch.setattr(runtime, "ACTIVE_PROV", prov)
    monkeypatch.setattr(runtime.base, "GPU_LOCK_DIR", locks)
    fd = os.open(lock, os.O_RDWR | os.O_NOFOLLOW)
    try:
        digest = runtime.base.sha_file(intent_path)
        assert runtime._validate_launcher_intent(
            str(broker_socket), uuid, 0, capability, digest, fd) == intent
        with pytest.raises(ValueError, match="exact socket/GPU/lock"):
            runtime._validate_launcher_intent(
                str(run / "other.sock"), uuid, 0, capability, digest, fd)
        with pytest.raises(ValueError, match="canonical bytes/digest"):
            runtime._validate_launcher_intent(
                str(broker_socket), uuid, 0, capability, "b" * 64, fd)
    finally:
        os.close(fd)


def test_launch_releases_gpu_lease_when_post_acquisition_setup_fails(tmp_path, monkeypatch):
    config = tmp_path / "config"; config.mkdir(mode=0o700)
    locks = tmp_path / "locks"; locks.mkdir(mode=0o700)
    uuid = "GPU-1234567890abcdef"
    commitment = {"gpu_lock_directory": runtime.base._directory_binding(locks)}
    (config / "authorization_commitment.json").write_bytes(
        runtime.base.canonical_bytes(commitment))
    monkeypatch.setattr(runtime, "ACTIVE_CONFIG", config)
    monkeypatch.setattr(runtime.base, "GPU_LOCK_DIR", locks)
    fd, directory_fd, path = runtime._open_gpu_lock(uuid)
    monkeypatch.setattr(runtime, "verify_candidate_manifest", lambda _phase: {})
    monkeypatch.setattr(runtime, "validate_stage_a", lambda: {})
    monkeypatch.setattr(runtime, "verify_authorization", lambda *args, **kwargs:
                        {"envelope_sha256": "a" * 64})
    monkeypatch.setattr(runtime, "_gpu_rows", lambda: [(0, 0, uuid, 0)])
    monkeypatch.setattr(runtime, "_open_gpu_lock", lambda _uuid: (fd, directory_fd, path))
    monkeypatch.setattr(runtime, "_launch_with_acquired_gpu",
                        lambda *args, **kwargs: (_ for _ in ()).throw(OSError("injected setup")))
    with pytest.raises(OSError, match="injected setup"):
        runtime._launch_impl()
    code = ("import fcntl,os,sys; f=os.open(sys.argv[1],os.O_RDWR); "
            "fcntl.flock(f,fcntl.LOCK_EX|fcntl.LOCK_NB); print('acquired')")
    child = subprocess.run([sys.executable, "-c", code, str(path)], check=True,
                           text=True, capture_output=True)
    assert child.stdout.strip() == "acquired"


def test_post_lock_gpu_query_timeout_releases_uuid_lease(tmp_path, monkeypatch):
    config = tmp_path / "config"; config.mkdir(mode=0o700)
    prov = tmp_path / "prov"; prov.mkdir(mode=0o700)
    stage = prov / "stage_a.json"; stage.write_text("{}\n"); stage.chmod(0o644)
    locks = tmp_path / "locks"; locks.mkdir(mode=0o700)
    uuid = "GPU-1234567890abcdef"
    commitment = {"gpu_lock_directory": runtime.base._directory_binding(locks)}
    (config / "authorization_commitment.json").write_bytes(
        runtime.base.canonical_bytes(commitment))
    monkeypatch.setattr(runtime, "ACTIVE_CONFIG", config)
    monkeypatch.setattr(runtime, "ACTIVE_PROV", prov)
    monkeypatch.setattr(runtime.base, "GPU_LOCK_DIR", locks)
    fd, directory_fd, path = runtime._open_gpu_lock(uuid)
    monkeypatch.setattr(runtime, "verify_candidate_manifest", lambda _phase: {})
    monkeypatch.setattr(runtime, "validate_stage_a", lambda: {})
    monkeypatch.setattr(runtime, "verify_authorization", lambda *args, **kwargs:
                        {"envelope_sha256": "a" * 64})
    calls = 0

    def gpu_rows():
        nonlocal calls
        calls += 1
        if calls == 1:
            return [(0, 0, uuid, 0)]
        raise subprocess.TimeoutExpired(["/usr/bin/nvidia-smi"], 15)

    monkeypatch.setattr(runtime, "_gpu_rows", gpu_rows)
    monkeypatch.setattr(runtime, "_open_gpu_lock", lambda _uuid: (fd, directory_fd, path))
    with pytest.raises(subprocess.TimeoutExpired):
        runtime._launch_impl()
    code = ("import fcntl,os,sys; f=os.open(sys.argv[1],os.O_RDWR); "
            "fcntl.flock(f,fcntl.LOCK_EX|fcntl.LOCK_NB); print('acquired')")
    child = subprocess.run([sys.executable, "-c", code, str(path)], check=True,
                           text=True, capture_output=True)
    assert child.stdout.strip() == "acquired" and calls == 2


def test_gpu_queries_are_bounded_without_invoking_nvidia(monkeypatch):
    observed = []

    def blocked(argv, **kwargs):
        observed.append((tuple(argv), kwargs.get("timeout")))
        raise subprocess.TimeoutExpired(argv, kwargs["timeout"])

    monkeypatch.setattr(runtime.subprocess, "check_output", blocked)
    with pytest.raises(subprocess.TimeoutExpired):
        runtime._gpu_rows()
    assert observed == [(('/usr/bin/nvidia-smi',
                           '--query-gpu=index,uuid,memory.used,utilization.gpu',
                           '--format=csv,noheader,nounits'), 15)]


def test_tmux_client_timeout_is_bounded_and_extinguishes_its_captured_group(monkeypatch):
    vector = ["/usr/bin/tmux", "-f", "/dev/null", "-S",
              "/tmp/m9t_" + "a" * 64 + ".sock", "has-session", "-t",
              "msae-independent-v3-gen9-calibration"]
    observed = []

    class FakeProcess:
        pid = 24680
        returncode = None
        def communicate(self, *, timeout):
            observed.append(("communicate", timeout))
            raise subprocess.TimeoutExpired(vector, timeout)
        def wait(self, *, timeout):
            observed.append(("wait", timeout))
            self.returncode = -9
            return self.returncode

    monkeypatch.setattr(runtime.subprocess, "Popen", lambda *args, **kwargs:
                        observed.append(("popen", args, kwargs)) or FakeProcess())
    monkeypatch.setattr(runtime.base, "_start_ticks", lambda pid: "123")
    monkeypatch.setattr(runtime, "_proc_group_pid", lambda pid: pid)
    monkeypatch.setattr(runtime, "_terminate_group", lambda pgid, grace=3:
                        observed.append(("terminate", pgid, grace)))
    with pytest.raises(subprocess.TimeoutExpired):
        runtime._run_tmux_client(vector)
    assert ("communicate", 15) in observed
    assert ("terminate", 24680, 1) in observed
    popen = observed[0]
    assert popen[0] == "popen"
    assert popen[2]["start_new_session"] is True
    assert popen[2]["env"] == runtime.FROZEN_BASE_PROCESS_ENVIRONMENT
    assert popen[2]["shell"] is False and popen[2]["close_fds"] is True


def _gen9_monitor_record_fixture() -> dict:
    stage = "a" * 64
    tmux_path, broker_path, pane_path = runtime._tmux_paths(stage)
    return {
        "schema_version": "msae_v3_gen9_tmux_monitor_v2",
        "protocol_id": runtime.PROTOCOL,
        "generation": runtime.GENERATION,
        "status": "monitor_record_committed",
        "created_utc": "2026-08-21T12:00:00Z",
        "stage_a_sha256": stage,
        "authorization_envelope_sha256": "b" * 64,
        "launcher_intent_sha256": "c" * 64,
        "launch_capability_sha256": "d" * 64,
        "gpu": {"uuid": "GPU-1234567890abcdef", "index": 0},
        "lease": {"path": "/tmp/lease", "device": 1, "inode": 2,
                  "uid": os.getuid(), "gid": os.getgid(), "mode": 0o600,
                  "nlink": 1, "payload_sha256": "e" * 64,
                  "gpu_uuid": "GPU-1234567890abcdef"},
        "launcher": {"pid": 2001, "start_ticks": "11"},
        "monitor": {"pid": 2002, "start_ticks": "12", "pgid": 2002,
                    "argv_sha256": "f" * 64},
        "code": {"controller_sha256": "1" * 64,
                 "runtime_sha256": "2" * 64,
                 "dependency_closure_sha256": "3" * 64},
        "control": {"family": "AF_UNIX", "type": "SOCK_SEQPACKET",
                    "launcher_pid": 2001, "launcher_uid": os.getuid(),
                    "launcher_gid": os.getgid(), "monitor_pid": 2002,
                    "monitor_uid": os.getuid(), "monitor_gid": os.getgid(),
                    "pane_listener_binding": {
                        "path": str(pane_path), "device": 1, "inode": 5,
                        "uid": os.getuid(), "gid": os.getgid(), "mode": 0o700,
                        "nlink": 1},
                    "broker_socket_binding": {
                        "path": str(broker_path), "device": 1, "inode": 6,
                        "uid": os.getuid(), "gid": os.getgid(), "mode": 0o700,
                        "nlink": 1}},
        "inherited_fds": {"control": 3, "lease": 4,
                          "monitor_log": 5, "server_log": 6,
                          "pane_listener": 7, "broker_cleanup": 8},
        "logs": {
            "monitor": {"path": str(runtime.ACTIVE_RUN_ROOT / "logs/monitor.log"),
                        "device": 1, "inode": 3, "uid": os.getuid(),
                        "gid": os.getgid(), "mode": 0o600, "nlink": 1},
            "server": {"path": str(runtime.ACTIVE_RUN_ROOT / "logs/tmux_server.log"),
                       "device": 1, "inode": 4, "uid": os.getuid(),
                       "gid": os.getgid(), "mode": 0o600, "nlink": 1}},
        "tmux_socket_path": str(tmux_path),
        "broker_socket_path": str(broker_path),
        "pane_socket_path": str(pane_path),
        "handoff_deadline_unix": 1_800_000_000,
        "terminal_deadline_unix": 1_800_021_600,
    }


def _gen9_monitor_payload(sequence: int) -> dict:
    digest = "a" * 64
    payloads = {
        1: {"monitor_pid": 2002, "monitor_start_ticks": "12",
            "monitor_pgid": 2002, "monitor_argv_sha256": digest,
            "environment_sha256": digest, "inherited_fd_set_sha256": digest,
            "launcher_intent_sha256": digest},
        2: {"record_path": (runtime.ACTIVE_RUN_ROOT / "tmux_monitor.json").relative_to(
                runtime.ROOT).as_posix(), "record_sha256": digest},
        3: {"record_sha256": digest, "record_subject_sha256": digest},
        4: {"record_sha256": digest, "record_ack_sha256": digest,
            "tmux_socket_path": "/tmp/m9t_" + digest + ".sock",
            "broker_socket_path": "/tmp/m9b_" + digest + ".sock",
            "pane_socket_path": "/tmp/m9p_" + digest + ".sock"},
        5: {"server_pid": 2003, "server_start_ticks": "13",
            "server_pgid": 2003, "pane_pid": 2004,
            "pane_start_ticks": "14",
            "tmux_socket_binding": {"device": 1, "inode": 2,
                                    "uid": os.getuid(), "gid": os.getgid(),
                                    "mode": 0o700, "nlink": 1},
            "session": "msae-independent-v3-gen9-calibration",
            "exit_empty": "on", "server_start_transcript_sha256": digest},
        6: {"handoff_sha256": digest, "gate_confirmation_sha256": digest,
            "broker_family_projection_sha256": digest},
        7: {"handoff_sha256": digest, "gate_confirmation_sha256": digest,
            "monitor_live_subject_sha256": digest,
            "terminal_deadline_unix": 1_800_021_600},
    }
    return payloads[sequence]


def test_monitor_record_and_short_socket_contract_reject_every_mutation():
    record = _gen9_monitor_record_fixture()
    runtime._validate_monitor_record(record, expected=record)
    assert tuple(map(lambda path: len(os.fsencode(path)),
                     runtime._tmux_paths("a" * 64))) == (78, 78, 78)
    mutations = []
    for key in record:
        value = copy.deepcopy(record)
        value.pop(key)
        mutations.append(value)
    for mutate in (
            lambda value: value["inherited_fds"].__setitem__("server_log", 5),
            lambda value: value["control"].__setitem__("monitor_pid", 2003),
            lambda value: value["logs"]["monitor"].__setitem__("path", "/tmp/escape"),
            lambda value: value.__setitem__("tmux_socket_path",
                                            "/tmp/m9t_" + "0" * 64 + ".sock"),
            lambda value: value["monitor"].__setitem__("start_ticks", "0"),
            lambda value: value["lease"].__setitem__("nlink", 2)):
        value = copy.deepcopy(record); mutate(value); mutations.append(value)
    for value in mutations:
        with pytest.raises((ValueError, KeyError)):
            runtime._validate_monitor_record(value)


def test_tmux_socket_mode_promotion_is_identity_preserving_and_exact():
    path = Path("/tmp/m9t_" + "f" * 64 + ".sock")
    assert not (path.exists() or path.is_symlink())
    server = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    try:
        server.bind(str(path)); os.chmod(path, 0o600); server.listen(1)
        before = path.lstat()
        binding = runtime._promote_tmux_socket_mode(path)
        after = path.lstat()
        assert (before.st_dev, before.st_ino) == (after.st_dev, after.st_ino)
        assert stat.S_IMODE(after.st_mode) == 0o700
        assert binding == runtime._tmux_socket_identity(path)
    finally:
        server.close()
        if path.exists() or path.is_symlink():
            st = path.lstat()
            assert stat.S_ISSOCK(st.st_mode) and st.st_uid == os.getuid()
            path.unlink()


def test_monitor_frame_chain_is_canonical_exact_and_datagram_bounded():
    previous = None
    frames = []
    for sequence, (frame_type, _keys) in enumerate(runtime.MONITOR_FRAME_SPECS, 1):
        frame = runtime._monitor_frame(
            frame_type, sequence, previous, _gen9_monitor_payload(sequence))
        runtime._validate_monitor_frame(
            frame, expected_type=frame_type,
            expected_sequence=sequence, expected_prior=previous)
        frames.append(frame)
        previous = runtime.base.sha_bytes(runtime.base.canonical_bytes(frame))
    for sequence, frame in enumerate(frames, 1):
        for mutation in ("extra", "type", "sequence", "prior", "payload"):
            changed = copy.deepcopy(frame)
            if mutation == "extra": changed["extra"] = True
            elif mutation == "type": changed["frame_type"] = "WRONG"
            elif mutation == "sequence": changed["sequence"] = 99
            elif mutation == "prior": changed["prior_frame_sha256"] = "0" * 64
            else: changed["payload"]["extra"] = True
            with pytest.raises(ValueError):
                runtime._validate_monitor_frame(
                    changed, expected_type=frame["frame_type"],
                    expected_sequence=sequence,
                    expected_prior=frame["prior_frame_sha256"])
    left, right = socket.socketpair(socket.AF_UNIX, socket.SOCK_SEQPACKET)
    try:
        sent_sha = runtime._monitor_send(left, frames[0])
        received, received_sha = runtime._monitor_recv(
            right, "MONITOR_HELLO", 1, None)
        assert received == frames[0] and received_sha == sent_sha
        runtime._monitor_require_no_extra_frame(right)
        left.send(b"extra")
        with pytest.raises(ValueError, match="extra"):
            runtime._monitor_require_no_extra_frame(right)
    finally:
        left.close(); right.close()


def test_worker_environment_is_closed_and_inherited_escape_cannot_survive(monkeypatch):
    monkeypatch.setenv("LD_PRELOAD", "/tmp/escape.so")
    monkeypatch.setenv("LD_LIBRARY_PATH", "/tmp/escape")
    value = runtime.worker_environment("GPU-1234567890abcdef", 3, 4, 5, 6)
    assert "LD_PRELOAD" not in value and "LD_LIBRARY_PATH" not in value
    assert value["CUBLAS_WORKSPACE_CONFIG"] == ":4096:8"
    assert value["MSAE_LEASE_FD"] == "3" and set(value) == (
        set(runtime.FROZEN_BASE_PROCESS_ENVIRONMENT) |
        set(runtime.FROZEN_WORKER_ENVIRONMENT) |
        {"CUDA_VISIBLE_DEVICES", "MSAE_LEASE_FD", "MSAE_GPU_UUID",
         "MSAE_READINESS_FD", "MSAE_FINAL_ACK_FD", "MSAE_CONFIRMED_FD"})


def test_authorization_nonce_consumption_is_exactly_once(tmp_path, monkeypatch):
    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
    config = tmp_path / "config"; config.mkdir(mode=0o700)
    prov = tmp_path / "prov"; prov.mkdir(mode=0o700)
    data = tmp_path / "data"; data.mkdir(mode=0o700)
    nonce = tmp_path / "nonces"; nonce.mkdir(mode=0o700)
    locks = tmp_path / "locks"; locks.mkdir(mode=0o700)
    run = tmp_path / "run"; run.mkdir(mode=0o700)
    review = tmp_path / "review.md"; review.write_text("VERDICT: SHIP\n"); review.chmod(0o644)
    for path in (prov / "prescore_candidate_manifest.json", prov / "stage_a.json",
                 data / "dependency_closure.json", config / "protocol.json"):
        path.write_text("{}\n")
    private = Ed25519PrivateKey.generate()
    public = private.public_key().public_bytes(serialization.Encoding.PEM,
                                               serialization.PublicFormat.SubjectPublicKeyInfo)
    (config / "ed25519_public.pem").write_bytes(public)
    (config / "ed25519_public.pem").chmod(0o644)
    commitment = {"envelope_schema": "test_auth_v1", "public_key_sha256": runtime.base.sha_bytes(public),
                  "maximum_lifetime_seconds": 86400,
                  "nonce_directory": runtime.base._directory_binding(nonce)}
    (config / "authorization_commitment.json").write_bytes(runtime.base.canonical_bytes(commitment))
    monkeypatch.setattr(runtime, "ACTIVE_CONFIG", config)
    monkeypatch.setattr(runtime, "ACTIVE_PROV", prov)
    monkeypatch.setattr(runtime, "ACTIVE_M4_DATA", data)
    monkeypatch.setattr(runtime, "ACTIVE_NONCE_DIR", nonce)
    monkeypatch.setattr(runtime, "PRESCORE_REVIEW", review)
    monkeypatch.setattr(runtime, "_verify_existing_authorization_state", lambda: commitment)
    issued = int(time.time())
    unsigned = {"schema_version": "test_auth_v1", "protocol_id": runtime.PROTOCOL,
                "scope": "calibration_replay_only",
                "commitment_sha256": runtime.base.sha_file(config / "authorization_commitment.json"),
                "stage_a_sha256": runtime.base.sha_file(prov / "stage_a.json"),
                "protocol_config_sha256": runtime.base.sha_file(config / "protocol.json"),
                "dependency_closure_sha256": runtime.base.sha_file(data / "dependency_closure.json"),
                "prescore_candidate_manifest_sha256": runtime.base.sha_file(prov / "prescore_candidate_manifest.json"),
                "operator_instruction": runtime.OPERATOR_INSTRUCTION,
                "operator_instruction_sha256": runtime.base.sha_bytes(runtime.OPERATOR_INSTRUCTION.encode()),
                "review_sha256": runtime.base.sha_file(review), "review_verdict": "SHIP",
                "nonce": "a" * 64, "issued_unix": issued, "expires_unix": issued + 600}
    signature = private.sign(runtime.base.canonical_bytes(unsigned))
    envelope = {**unsigned, "signature_b64": base64.b64encode(signature).decode("ascii")}
    envelope_path = run / "authorization.json"
    envelope_path.write_bytes(runtime.base.canonical_bytes(envelope))
    envelope_path.chmod(0o600)
    runtime.verify_authorization(envelope_path, consume=False)
    original_write = os.write

    def short_write(fd, payload):
        return original_write(fd, payload[:max(1, len(payload) // 4)])

    monkeypatch.setattr(runtime.os, "write", short_write)
    result = runtime.verify_authorization(envelope_path, consume=True, run_root=run)
    monkeypatch.setattr(runtime.os, "write", original_write)
    assert result["envelope_sha256"] == runtime.base.sha_file(envelope_path)
    with pytest.raises(ValueError, match="already been consumed"):
        runtime.verify_authorization(envelope_path, consume=False)
    old_nonce = tmp_path / "old_nonces"
    nonce.rename(old_nonce)
    nonce.mkdir(mode=0o700)
    with pytest.raises(ValueError, match="nonce-directory FD"):
        runtime.verify_authorization(envelope_path, consume=False)


def test_runner_readiness_requires_every_exact_lineage_field(tmp_path, monkeypatch):
    run = tmp_path / "run"; run.mkdir(mode=0o700)
    config = tmp_path / "config"; config.mkdir(mode=0o700)
    prov = tmp_path / "prov"; prov.mkdir(mode=0o700)
    data = tmp_path / "data"; data.mkdir(mode=0o700)
    nonce = tmp_path / "nonces"; nonce.mkdir(mode=0o700)
    stage = prov / "stage_a.json"; stage.write_text("{}\n"); stage.chmod(0o644)
    protocol = config / "protocol.json"; protocol.write_text("{}\n"); protocol.chmod(0o644)
    closure = data / "dependency_closure.json"; closure.write_text("{}\n"); closure.chmod(0o644)
    authorization = {"envelope_sha256": "e" * 64}
    record = nonce / f"{authorization['envelope_sha256']}.consumed"
    record_value = {"schema_version": "msae_v3_nonce_consumed_v2",
                    "authorization_file_sha256": authorization["envelope_sha256"],
                    "stage_a_sha256": runtime.base.sha_file(stage)}
    record.write_bytes(runtime.base.canonical_bytes(record_value)); record.chmod(0o600)
    record_st = record.lstat()
    attestation_value = {"schema_version": "msae_v3_nonce_attestation_v2",
                         "record_path": str(record), "record_device": record_st.st_dev,
                         "record_inode": record_st.st_ino, "record_mode": 0o600,
                         "record_sha256": runtime.base.sha_file(record),
                         "authorization_file_sha256": authorization["envelope_sha256"]}
    attestation = run / "nonce_consumed.json"
    attestation.write_bytes(runtime.base.canonical_bytes(attestation_value)); attestation.chmod(0o644)
    monkeypatch.setattr(runtime, "ACTIVE_RUN_ROOT", run)
    monkeypatch.setattr(runtime, "ACTIVE_CONFIG", config)
    monkeypatch.setattr(runtime, "ACTIVE_PROV", prov)
    monkeypatch.setattr(runtime, "ACTIVE_M4_DATA", data)
    monkeypatch.setattr(runtime, "ACTIVE_NONCE_DIR", nonce)
    worker = {"worker_pid": 101, "worker_pgid": 101, "broker_pid": 99}
    expected = {"schema_version": "msae_v3_runner_ready_v1", "protocol_id": runtime.PROTOCOL,
                "worker_pid": 101, "worker_pgid": 101, "broker_pid": 99,
                "gpu_uuid": "GPU-1234567890abcdef",
                "stage_a_sha256": runtime.base.sha_file(stage),
                "protocol_config_sha256": runtime.base.sha_file(protocol),
                "dependency_closure_sha256": runtime.base.sha_file(closure),
                "authorization_envelope_sha256": authorization["envelope_sha256"],
                "nonce_attestation_sha256": runtime.base.sha_file(attestation),
                "pre_model": True}
    assert runtime.validate_runner_readiness(
        expected, worker, "GPU-1234567890abcdef", authorization) == attestation_value
    for key in expected:
        mutated = dict(expected); mutated[key] = None
        with pytest.raises(ValueError, match="exact lineage"):
            runtime.validate_runner_readiness(
                mutated, worker, "GPU-1234567890abcdef", authorization)
    moved = nonce / "../nonces/../wrong.consumed"
    bad_attestation = dict(attestation_value); bad_attestation["record_path"] = str(moved)
    attestation.write_bytes(runtime.base.canonical_bytes(bad_attestation))
    with pytest.raises(ValueError, match="exact derived consumed record"):
        runtime.validate_runner_readiness(
            {**expected, "nonce_attestation_sha256": runtime.base.sha_file(attestation)},
            worker, "GPU-1234567890abcdef", authorization)
    attestation.write_bytes(runtime.base.canonical_bytes(attestation_value))
    record.write_bytes(runtime.base.canonical_bytes({**record_value, "stage_a_sha256": "0" * 64}))
    with pytest.raises(ValueError, match="identity mismatch"):
        runtime.validate_runner_readiness(
            {**expected, "nonce_attestation_sha256": runtime.base.sha_file(attestation)},
            worker, "GPU-1234567890abcdef", authorization)


def test_terminate_group_escalates_without_targeting_invalid_groups(monkeypatch):
    calls = []
    monkeypatch.setattr(runtime.os, "killpg", lambda pgid, sig: calls.append((pgid, sig)))
    runtime._terminate_group(-1)
    assert calls == []


def test_terminate_group_kills_a_term_resistant_real_process_group():
    process = subprocess.Popen(
        [sys.executable, "-c",
         "import signal,time; signal.signal(signal.SIGTERM, signal.SIG_IGN); "
         "print('R', flush=True); time.sleep(60)"],
        start_new_session=True, stdout=subprocess.PIPE, text=True)
    try:
        assert process.stdout is not None and process.stdout.readline().strip() == "R"
        runtime._terminate_group(process.pid, grace=0.05)
        assert process.wait(timeout=3) == -9
    finally:
        if process.poll() is None:
            os.killpg(process.pid, 9)


def test_parent_death_watchdog_kills_worker_when_broker_exits(tmp_path):
    runtime_path = ROOT / "scripts/msae_independent_measurement_v3_post_m2_gen9_runtime.py"
    controller_path = ROOT / "scripts/msae_independent_measurement_v3_post_m2_gen9.py"
    script = f'''\
import importlib.util, os, sys, time, types
controller_path={str(controller_path)!r}
controller=types.ModuleType("msae_independent_measurement_v3_post_m2_gen9")
controller.__file__=controller_path; controller.__package__=None
sys.modules[controller.__name__]=controller
with open(controller_path,"rb") as handle: controller_raw=handle.read()
exec(compile(controller_raw,controller_path,"exec"),controller.__dict__)
spec=controller.source_only_module_spec("watchdog_runtime", {str(runtime_path)!r})
module=importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
out_fd={{{{OUT_FD}}}}
ready_r, ready_w = os.pipe()
pid=os.fork()
if pid == 0:
    os.close(ready_r)
    module.install_parent_death_watchdog(os.getppid())
    os.write(out_fd, (str(os.getpid())+"\\n").encode())
    os.write(ready_w, b"R")
    while True: time.sleep(1)
os.close(ready_w)
os.read(ready_r, 1)
os._exit(0)
'''
    read_fd, write_fd = os.pipe()
    script = script.replace("{{OUT_FD}}", str(write_fd))
    parent = subprocess.Popen([sys.executable, "-c", script], pass_fds=(write_fd,))
    os.close(write_fd)
    try:
        worker_pid = int(os.read(read_fd, 64).strip())
        assert parent.wait(timeout=5) == 0
        deadline = time.monotonic() + 5
        while time.monotonic() < deadline and (Path("/proc") / str(worker_pid)).exists():
            try:
                status = (Path("/proc") / str(worker_pid) / "stat").read_text().split()[2]
            except (FileNotFoundError, ProcessLookupError):
                break
            if status == "Z":
                break
            time.sleep(0.05)
        try:
            final_status = (Path("/proc") / str(worker_pid) / "stat").read_text().split()[2]
        except (FileNotFoundError, ProcessLookupError):
            final_status = "gone"
        assert final_status in {"gone", "Z"}
    finally:
        os.close(read_fd)


def test_supervisor_claims_terminal_failure_when_broker_is_killed(tmp_path, monkeypatch):
    run = tmp_path / "run"; run.mkdir(mode=0o700)
    monkeypatch.setattr(runtime, "ACTIVE_RUN_ROOT", run)
    result = runtime._supervise_broker_process(
        [sys.executable, "-c", "import os,signal; os.kill(os.getpid(),signal.SIGKILL)"],
        runtime.FROZEN_BASE_PROCESS_ENVIRONMENT)
    assert result == -signal.SIGKILL
    status = runtime.base.read_json(run / "terminal_failure/status.json")
    failure = runtime.base.read_json(run / "terminal_failure/technical_failure.json")
    assert status["status"] == "technical_failure_not_run" and status["stage_b_ready"] is False
    assert failure["status"] == "not_run" and failure["stage_b_written"] is False
    assert not (run / "terminal_success").exists()


def test_supervisor_kills_descendant_group_after_worker_leader_exit(tmp_path, monkeypatch):
    run = tmp_path / "run"; run.mkdir(mode=0o700)
    monkeypatch.setattr(runtime, "ACTIVE_RUN_ROOT", run)
    record = run / "lock_acquired.json"
    child_pid_file = run / "child.pid"
    code = r'''
import ctypes, json, os, signal, sys, time
record, child_file = sys.argv[1:]
leader = os.fork()
if leader == 0:
    os.setpgid(0, 0)
    leader_pid = os.getpid()
    raw = open('/proc/self/stat').read()
    ticks = int(raw[raw.rfind(')')+2:].split()[19])
    grandchild = os.fork()
    if grandchild == 0:
        signal.signal(signal.SIGTERM, signal.SIG_IGN)
        ctypes.CDLL(None).prctl(15, b'a b)', 0, 0, 0)
        with open(child_file, 'w') as f: f.write(str(os.getpid()))
        while True: time.sleep(1)
    value = {'worker_pid': leader_pid, 'worker_start_ticks': ticks, 'worker_pgid': leader_pid}
    with open(record, 'w') as f:
        f.write(json.dumps(value,sort_keys=True,separators=(',',':'))+'\n')
    os.chmod(record, 0o644)
    while not os.path.exists(child_file): time.sleep(0.01)
    os._exit(0)
os.waitpid(leader, 0)
os._exit(0)
'''
    result = runtime._supervise_broker_process(
        [sys.executable, "-c", code, str(record), str(child_pid_file)],
        runtime.FROZEN_BASE_PROCESS_ENVIRONMENT)
    child_pid = int(child_pid_file.read_text())
    worker_pgid = runtime.base.read_json(record)["worker_pgid"]
    assert result == 0
    assert not runtime._group_live_pids(worker_pgid)
    assert (run / "terminal_failure/status.json").is_file()


def _tmux_test_process_fixture() -> dict[str, int | str]:
    return {
    "schema_version": "msae_v3_gen9_tmux_test_process_v1",
        "monitor_pid": 2, "monitor_start_ticks": 20,
        "server_pid": 3, "server_start_ticks": 30, "server_pgid": 3,
        "pane_pid": 4, "pane_start_ticks": 40, "pane_ppid": 3,
        "broker_pid": 5, "broker_start_ticks": 50, "broker_ppid": 4,
        "broker_pgid": 5, "worker_pid": 6, "worker_start_ticks": 60,
        "worker_ppid": 5, "worker_pgid": 6,
    }


def test_tmux_supervisor_cleans_exact_crash_left_identity_pairs(tmp_path):
    module_name = "_msae_gen9_tmux_supervisor_pair_test"
    spec = runtime.continuation.source_only_module_spec(
        module_name, runtime.TMUX_TEST_SUPERVISOR)
    assert spec is not None and spec.loader is not None
    supervisor = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(supervisor)
    partial = tmp_path / ".process.json.partial"
    final = tmp_path / "process.json"
    raw = supervisor._canonical_bytes(_tmux_test_process_fixture())
    partial.write_bytes(raw); partial.chmod(0o600)
    os.link(partial, final, follow_symlinks=False)
    assert partial.stat().st_nlink == final.stat().st_nlink == 2
    assert supervisor._read_identity(final) is None
    assert supervisor._cleanup_owned_regular_pair(
        tmp_path, partial.name, final.name) is True
    assert not partial.exists() and not final.exists()


def test_tmux_supervisor_cleanup_rejects_wrong_bytes_and_third_links(tmp_path):
    spec = runtime.continuation.source_only_module_spec(
        "_msae_gen9_tmux_supervisor_cleanup_poison", runtime.TMUX_TEST_SUPERVISOR)
    assert spec is not None and spec.loader is not None
    supervisor = importlib.util.module_from_spec(spec); spec.loader.exec_module(supervisor)
    wrong = tmp_path / "process.json"
    wrong.write_bytes(b"{}\n"); wrong.chmod(0o600)
    assert not supervisor._cleanup_owned_regular_pair(
        tmp_path, ".process.json.partial", "process.json")
    assert wrong.read_bytes() == b"{}\n"
    wrong.unlink()

    value = {"schema_version": "msae_v3_gen9_tmux_test_identity_bound_v1",
             "process_sha256": "c" * 64, "supervisor_pid": os.getpid()}
    partial = tmp_path / ".identity_bound.json.partial"
    final = tmp_path / "identity_bound.json"
    third = tmp_path / "third-link"
    partial.write_bytes(supervisor._canonical_bytes(value)); partial.chmod(0o600)
    os.link(partial, final, follow_symlinks=False)
    os.link(partial, third, follow_symlinks=False)
    assert not supervisor._cleanup_owned_regular_pair(
        tmp_path, partial.name, final.name)
    assert partial.stat().st_nlink == final.stat().st_nlink == third.stat().st_nlink == 3
    third.unlink(); final.unlink(); partial.unlink()

    # Two separately-created valid one-link files are not the publisher's
    # legal hard-link pair and must not be treated as owned cleanup state.
    process_raw = supervisor._canonical_bytes(_tmux_test_process_fixture())
    process_partial = tmp_path / ".process.json.partial"
    process_final = tmp_path / "process.json"
    process_partial.write_bytes(process_raw); process_partial.chmod(0o600)
    process_final.write_bytes(process_raw); process_final.chmod(0o600)
    assert process_partial.stat().st_ino != process_final.stat().st_ino
    assert not supervisor._cleanup_owned_regular_pair(
        tmp_path, process_partial.name, process_final.name)
    assert process_partial.is_file() and process_final.is_file()
    process_partial.unlink(); process_final.unlink()

    # A single registered basename with an outside hard link is not a legal
    # source-only/destination-only state (those always have nlink==1).
    for registered in (".process.json.partial", "process.json"):
        registered_path = tmp_path / registered
        outside = tmp_path / ("outside-" + registered.removeprefix("."))
        registered_path.write_bytes(process_raw); registered_path.chmod(0o600)
        os.link(registered_path, outside, follow_symlinks=False)
        assert not supervisor._cleanup_owned_regular_pair(
            tmp_path, ".process.json.partial", "process.json")
        assert registered_path.is_file() and outside.is_file()
        outside.unlink(); registered_path.unlink()


def test_tmux_supervisor_cleanup_rechecks_second_pair_member_before_unlink(
        tmp_path, monkeypatch):
    spec = runtime.continuation.source_only_module_spec(
        "_msae_gen9_tmux_supervisor_cleanup_substitution",
        runtime.TMUX_TEST_SUPERVISOR)
    assert spec is not None and spec.loader is not None
    supervisor = importlib.util.module_from_spec(spec); spec.loader.exec_module(supervisor)
    raw = supervisor._canonical_bytes(_tmux_test_process_fixture())
    partial = tmp_path / ".process.json.partial"
    final = tmp_path / "process.json"
    parked = tmp_path / "parked-original"
    partial.write_bytes(raw); partial.chmod(0o600)
    os.link(partial, final, follow_symlinks=False)
    original_stat = supervisor.os.stat
    final_stats = 0

    def substituting_stat(path, *args, **kwargs):
        nonlocal final_stats
        if path == final.name and kwargs.get("dir_fd") is not None:
            final_stats += 1
            # Collection, validation, then the immediate pre-unlink recheck.
            if final_stats == 3:
                final.rename(parked)
                final.write_bytes(raw); final.chmod(0o600)
        return original_stat(path, *args, **kwargs)

    monkeypatch.setattr(supervisor.os, "stat", substituting_stat)
    assert not supervisor._cleanup_owned_regular_pair(
        tmp_path, partial.name, final.name)
    assert final.is_file() and parked.is_file()


def test_tmux_supervisor_cleanup_accepts_valid_destination_only_record(tmp_path):
    spec = runtime.continuation.source_only_module_spec(
        "_msae_gen9_tmux_supervisor_cleanup_destination", runtime.TMUX_TEST_SUPERVISOR)
    assert spec is not None and spec.loader is not None
    supervisor = importlib.util.module_from_spec(spec); spec.loader.exec_module(supervisor)
    final = tmp_path / "identity_bound.json"
    final.write_bytes(supervisor._canonical_bytes({
        "schema_version": "msae_v3_gen9_tmux_test_identity_bound_v1",
        "process_sha256": "d" * 64, "supervisor_pid": os.getpid(),
    })); final.chmod(0o600)
    assert supervisor._cleanup_owned_regular_pair(
        tmp_path, ".identity_bound.json.partial", final.name)
    assert not final.exists()


@pytest.mark.parametrize("drift", ("argv", "environment"))
def test_tmux_supervisor_rejects_invocation_drift_before_namespace(drift):
    before = sorted(Path("/tmp").glob("msae-independent-v3-gen9-test-*"))
    argv = [str(ROOT / ".venv-atlas/bin/python"), "-S", "-B", "-I",
            str(runtime.TMUX_TEST_SUPERVISOR)]
    environment = {"PATH": "/usr/bin:/bin", "HOME": "/thayerfs/home/f004ndc",
                   "LANG": "C.UTF-8", "LC_ALL": "C.UTF-8"}
    if drift == "argv":
        argv.append("unexpected")
    else:
        environment["UNREGISTERED"] = "1"
    result = subprocess.run(argv, cwd=ROOT, env=environment,
                            text=True, capture_output=True)
    assert result.returncode != 0
    assert "invocation contract drift" in result.stderr
    assert sorted(Path("/tmp").glob("msae-independent-v3-gen9-test-*")) == before


def test_tmux_supervisor_child_timeout_terminates_real_resistant_group():
    spec = runtime.continuation.source_only_module_spec(
        "_msae_gen9_tmux_supervisor_child_timeout", runtime.TMUX_TEST_SUPERVISOR)
    assert spec is not None and spec.loader is not None
    supervisor = importlib.util.module_from_spec(spec); spec.loader.exec_module(supervisor)
    source = (
        "import os,signal,time\n"
        "signal.signal(signal.SIGTERM,signal.SIG_IGN)\n"
        "pid=os.fork()\n"
        "if pid==0:\n"
        " signal.signal(signal.SIGTERM,signal.SIG_IGN)\n"
        " while True: time.sleep(1)\n"
        "while True: time.sleep(1)\n")
    child = subprocess.Popen(
        [str(Path(sys.executable).resolve()), "-S", "-B", "-I", "-c", source],
        env={"PATH": "/usr/bin:/bin", "HOME": "/thayerfs/home/f004ndc",
             "LANG": "C.UTF-8", "LC_ALL": "C.UTF-8"},
        stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL, start_new_session=True)
    try:
        with pytest.raises(TimeoutError, match="child deadline"):
            supervisor._wait_child_until(
                child, time.monotonic() + 0.1, lambda: False)
        supervisor._terminate_child_group(child)
        assert child.poll() is not None
        assert supervisor._group_members(child.pid) == []
    finally:
        with contextlib.suppress(Exception):
            os.killpg(child.pid, signal.SIGKILL)
        with contextlib.suppress(Exception):
            child.wait(timeout=2)


def test_tmux_supervisor_extinguishes_group_after_pytest_leader_exit():
    spec = runtime.continuation.source_only_module_spec(
        "_msae_gen9_tmux_supervisor_dead_leader", runtime.TMUX_TEST_SUPERVISOR)
    assert spec is not None and spec.loader is not None
    supervisor = importlib.util.module_from_spec(spec); spec.loader.exec_module(supervisor)
    source = (
        "import os,signal,time\n"
        "pid=os.fork()\n"
        "if pid==0:\n"
        " signal.signal(signal.SIGTERM,signal.SIG_IGN)\n"
        " while True: time.sleep(1)\n"
        "os._exit(0)\n")
    child = subprocess.Popen(
        [str(Path(sys.executable).resolve()), "-S", "-B", "-I", "-c", source],
        env={"PATH": "/usr/bin:/bin", "HOME": "/thayerfs/home/f004ndc",
             "LANG": "C.UTF-8", "LC_ALL": "C.UTF-8"},
        stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL, start_new_session=True)
    try:
        assert child.wait(timeout=2) == 0
        deadline = time.monotonic() + 1
        while not supervisor._group_members(child.pid) and time.monotonic() < deadline:
            time.sleep(0.01)
        assert supervisor._group_members(child.pid)
        supervisor._terminate_child_group(child)
        assert supervisor._group_members(child.pid) == []
    finally:
        with contextlib.suppress(Exception): os.killpg(child.pid, signal.SIGKILL)


def test_tmux_supervisor_rejects_late_duplicate_identity_connection(tmp_path):
    spec = runtime.continuation.source_only_module_spec(
        "_msae_gen9_tmux_supervisor_duplicate_connection",
        runtime.TMUX_TEST_SUPERVISOR)
    assert spec is not None and spec.loader is not None
    supervisor = importlib.util.module_from_spec(spec); spec.loader.exec_module(supervisor)
    listener = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    socket_path = tmp_path / "ack.sock"
    listener.bind(str(socket_path)); listener.listen(1); listener.setblocking(False)
    selector = selectors.DefaultSelector()
    selector.register(listener, selectors.EVENT_READ, "listener")
    client = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    client.connect(str(socket_path))

    class LiveChild:
        @staticmethod
        def poll():
            return None

    try:
        with pytest.raises(RuntimeError, match="duplicate or late"):
            supervisor._wait_child_until(
                LiveChild(), time.monotonic() + 1, lambda: False,
                selector=selector)
    finally:
        client.close(); selector.close(); listener.close()

    left, right = socket.socketpair()
    try:
        right.sendall(b"extra")
        with pytest.raises(RuntimeError, match="identity frame"):
            supervisor._reject_pending_identity_frame(left)
    finally:
        left.close(); right.close()


@pytest.mark.parametrize("boundary", (
    "file_fsync", "link", "directory_fsync_before_unlink", "unlink",
    "directory_fsync_after_unlink",
))
def test_tmux_supervisor_publication_fault_boundaries_cleanup(
        tmp_path, monkeypatch, boundary):
    module_name = f"_msae_gen9_tmux_supervisor_fault_{boundary}"
    spec = runtime.continuation.source_only_module_spec(
        module_name, runtime.TMUX_TEST_SUPERVISOR)
    assert spec is not None and spec.loader is not None
    supervisor = importlib.util.module_from_spec(spec); spec.loader.exec_module(supervisor)
    final = tmp_path / "identity_bound.json"
    original_fsync = supervisor.os.fsync
    original_link = supervisor.os.link
    original_unlink = supervisor.os.unlink
    fsync_calls = 0

    def injected_fsync(fd):
        nonlocal fsync_calls
        fsync_calls += 1
        target = {"file_fsync": 1, "directory_fsync_before_unlink": 2,
                  "directory_fsync_after_unlink": 3}.get(boundary)
        if fsync_calls == target:
            raise OSError(boundary)
        return original_fsync(fd)

    def injected_link(*args, **kwargs):
        if boundary == "link":
            raise OSError(boundary)
        return original_link(*args, **kwargs)

    unlink_injected = False
    def injected_unlink(path, *args, **kwargs):
        nonlocal unlink_injected
        if boundary == "unlink" and not unlink_injected:
            unlink_injected = True
            raise OSError(boundary)
        return original_unlink(path, *args, **kwargs)

    monkeypatch.setattr(supervisor.os, "fsync", injected_fsync)
    monkeypatch.setattr(supervisor.os, "link", injected_link)
    monkeypatch.setattr(supervisor.os, "unlink", injected_unlink)
    with pytest.raises(OSError, match=boundary):
        supervisor._publish_identity_bound(final, {
            "schema_version": "msae_v3_gen9_tmux_test_identity_bound_v1",
            "process_sha256": "a" * 64, "supervisor_pid": os.getpid(),
        })
    assert supervisor._cleanup_owned_regular_pair(
        tmp_path, ".identity_bound.json.partial", "identity_bound.json")
    assert list(tmp_path.iterdir()) == []


def test_tmux_supervisor_publication_retries_short_writes(tmp_path, monkeypatch):
    spec = runtime.continuation.source_only_module_spec(
        "_msae_gen9_tmux_supervisor_short_write", runtime.TMUX_TEST_SUPERVISOR)
    assert spec is not None and spec.loader is not None
    supervisor = importlib.util.module_from_spec(spec); spec.loader.exec_module(supervisor)
    original_write = supervisor.os.write
    monkeypatch.setattr(
        supervisor.os, "write",
        lambda fd, value: original_write(fd, memoryview(value)[:1]))
    final = tmp_path / "identity_bound.json"
    supervisor._publish_identity_bound(final, {
        "schema_version": "msae_v3_gen9_tmux_test_identity_bound_v1",
        "process_sha256": "b" * 64, "supervisor_pid": os.getpid(),
    })
    assert supervisor._read_identity(final)["process_sha256"] == "b" * 64


def test_tmux_supervisor_test_terminal_is_exact_create_once_and_owned(tmp_path):
    spec = runtime.continuation.source_only_module_spec(
        "_msae_gen9_tmux_supervisor_terminal", runtime.TMUX_TEST_SUPERVISOR)
    assert spec is not None and spec.loader is not None
    supervisor = importlib.util.module_from_spec(spec); spec.loader.exec_module(supervisor)
    supervisor._write_test_terminal(
        tmp_path, owner="monitor", reason="pane_supervisor_death", pane_pid=2345)
    supervisor._validate_test_terminal(
        tmp_path, owner="monitor", reason="pane_supervisor_death", pane_pid=2345)
    with pytest.raises(FileExistsError):
        supervisor._write_test_terminal(
            tmp_path, owner="monitor", reason="pane_supervisor_death", pane_pid=2345)
    assert supervisor._cleanup_owned_regular_pair(
        tmp_path, ".terminal.claim.test.partial", "terminal.claim.test")
    assert supervisor._cleanup_owned_regular_pair(
        tmp_path, ".technical_failure.test.json.partial",
        "technical_failure.test.json")
    assert list(tmp_path.iterdir()) == []


def test_pre_capability_review_requires_exact_contiguous_command_evidence(
        monkeypatch):
    rows = [{"schema_version": "msae_v3_gen9_pre_capability_check_v1",
             "id": "one", "argv": ["/registered/one"], "cwd": str(ROOT),
             "environment": {}, "subject_sha256": "1" * 64,
             "exit_code": 0, "summary": "pass"},
            {"schema_version": "msae_v3_gen9_pre_capability_check_v1",
             "id": "two", "argv": ["/registered/two"], "cwd": str(ROOT),
             "environment": {}, "subject_sha256": "2" * 64,
             "exit_code": 0, "summary": "pass"}]
    encoded = ["CHECK_ROW_JSON: " + runtime.base.canonical_bytes(row).decode(
        "utf-8").rstrip("\n") for row in rows]
    prefix = ["VERDICT: SHIP", "REVIEW_SCOPE: gen9_pre_capability",
              "CHECKS RUN"]
    suffix = ["SEALED_PAYLOAD_CONTENT_READS: 0"]
    raw_holder = {"raw": ("\n".join([*prefix, *encoded, *suffix]) +
                          "\n").encode()}
    monkeypatch.setattr(runtime, "_pre_capability_check_rows", lambda: rows)
    monkeypatch.setattr(runtime, "_current_gen9_implementation_entries",
                        lambda: {})
    monkeypatch.setattr(runtime, "_canonical_review",
                        lambda *_args, **_kwargs: {"review": "bound"})
    monkeypatch.setattr(runtime, "_regular_bytes",
                        lambda *_args, **_kwargs: raw_holder["raw"])
    assert runtime._pre_capability_review_binding("a" * 64)["checks"] == rows
    for defective in (
        [*prefix, encoded[0], *suffix],
        [*prefix, encoded[1], encoded[0], *suffix],
        [*prefix, encoded[0], "prose between exact rows", encoded[1], *suffix],
        [*prefix, *encoded, "CHECK_ROW_JSON : {}", *suffix],
    ):
        raw_holder["raw"] = ("\n".join(defective) + "\n").encode()
        with pytest.raises(ValueError, match="command-evidence|CHECKS RUN"):
            runtime._pre_capability_review_binding("a" * 64)


def test_pre_capability_namespace_gate_blocks_extra_and_downstream_before_write(
        monkeypatch):
    monkeypatch.setattr(runtime, "_validate_gen3_review_namespace",
                        lambda _phase: None)
    monkeypatch.setattr(runtime, "_all_gen9_short_family_absence",
                        lambda: {prefix: [] for prefix in
                                 runtime.GEN7_SHORT_PREFIXES})
    monkeypatch.setattr(runtime.Path, "glob", lambda *_args, **_kwargs: [])
    monkeypatch.setattr(runtime, "_path_present", lambda _path: False)

    def extra(parent, prefix):
        if parent == runtime.ACTIVE_CONFIG.parent:
            return [prefix + "_undeclared"]
        return []

    monkeypatch.setattr(runtime, "_generation_siblings", extra)
    with pytest.raises(ValueError, match="generation namespace drift"):
        runtime._pre_capability_namespace_gate(allow_capability_root=False)
    monkeypatch.setattr(runtime, "_generation_siblings", lambda *_args: [])
    monkeypatch.setattr(
        runtime, "_path_present",
        lambda path: path == runtime.ACTIVE_STATE)
    with pytest.raises(ValueError, match="downstream namespace exists"):
        runtime._pre_capability_namespace_gate(allow_capability_root=False)


def test_tmux_fault_event_variants_reject_every_unregistered_control_mutation():
    spec = runtime.continuation.source_only_module_spec(
        "_msae_gen9_tmux_supervisor_event_schema",
        runtime.TMUX_TEST_SUPERVISOR)
    assert spec is not None and spec.loader is not None
    supervisor = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(supervisor)
    hook_case = (1, "before_monitor_record_write", "crash")
    hook = {
        "schema_version": "msae_v3_gen9_fault_event_v1",
        "event_type": "HOOK_REACHED", "test_token": "a" * 64,
        "case_id": hook_case[1], "reporter_role": "launcher",
        "reporter_kind": "launcher", "pid": 100, "start_ticks": "200",
        "ppid": 90, "pgid": 100,
        "payload": {"case_index": 1, "hook_id": hook_case[1],
                    "injection_kind": "crash"},
    }
    supervisor._g7_validate_fault_event_variant(hook, hook_case)
    for mutate in (
        lambda value: value.update(event_type="UNKNOWN"),
        lambda value: value["payload"].update(case_index=2),
        lambda value: value.update(reporter_kind="monitor"),
        lambda value: value.update(extra=True),
    ):
        defective = copy.deepcopy(hook); mutate(defective)
        with pytest.raises(RuntimeError):
            supervisor._g7_validate_fault_event_variant(defective, hook_case)
    scenario = ("S06_duplicate_frame",)
    boundary = {
        "schema_version": "msae_v3_gen9_fault_event_v1",
        "event_type": "SCENARIO_BOUNDARY_REACHED", "test_token": "a" * 64,
        "case_id": scenario[0], "reporter_role": "launcher",
        "reporter_kind": "launcher", "pid": 100, "start_ticks": "200",
        "ppid": 90, "pgid": 100,
        "payload": {"scenario_id": scenario[0],
                    "boundary_id": "launcher_after_lm3_before_lm4",
                    "reporter_process": {"pid": 100, "start_ticks": "200",
                                         "ppid": 90, "pgid": 100,
                                         "uid": os.getuid(),
                                         "gid": os.getgid()}},
    }
    supervisor._g7_validate_fault_event_variant(boundary, scenario)
    for key, value in (("boundary_id", "wrong"),
                       ("scenario_id", "S07_late_frame")):
        defective = copy.deepcopy(boundary); defective["payload"][key] = value
        with pytest.raises(RuntimeError):
            supervisor._g7_validate_fault_event_variant(defective, scenario)


def test_tmux_outer_reconstructs_scenario_action_projection():
    spec = runtime.continuation.source_only_module_spec(
        "_msae_gen9_tmux_supervisor_action_projection",
        runtime.TMUX_TEST_SUPERVISOR)
    assert spec is not None and spec.loader is not None
    supervisor = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(supervisor)
    scenario = ("S06_duplicate_frame",)
    reporter = {
        "role": "launcher", "pid": 100, "start_ticks": "200",
        "ppid": 90, "pgid": 100, "uid": os.getuid(), "gid": os.getgid(),
        "live": True,
    }
    boundary = {
        "pid": 100, "reporter_role": "launcher",
    }
    boundary_sha256 = "b" * 64
    action_sha256 = "c" * 64
    target = {
        "schema_version": "msae_v3_gen9_scenario_monitor_frame_v1",
        "kind": "monitor_frame", "direction": "launcher_to_monitor",
        "frame_type": "MONITOR_RECORD_COMMITTED", "sequence": 2,
        "frame_sha256": "0" * 64, "peer_process": reporter,
    }
    expected = {
        "schema_version": "msae_v3_gen9_scenario_action_observation_v1",
        "scenario_id": scenario[0],
        "boundary_event_sha256": boundary_sha256,
        "action_event_sha256": action_sha256,
        "initiator": "per_case_launcher",
        "trigger": "duplicate_monitor_frame_2",
        "target_identity": target,
        "pre_action_processes": [reporter],
        "action": "send_duplicate_lm2",
        "post_action_processes": [reporter],
        "term_escalation": None,
    }
    ledger = {
        "target_identity": target,
        "scenario_action_observation_sha256": hashlib.sha256(
            supervisor._canonical_bytes(expected)).hexdigest(),
    }
    assert supervisor._g7_scenario_action_projection(
        case=scenario, ledger_value=ledger, boundary_event=boundary,
        boundary_sha256=boundary_sha256,
        action_events=[({"event_type": "SCENARIO_ACTION_OBSERVED"},
                        action_sha256)],
        pre_exit_subject={"captured_processes": [reporter]},
        helper_deadline_monotonic_ns=8,
        outer_deadline_monotonic_ns=24) == expected
    for mutate in (
        lambda value: value["target_identity"].update(sequence=99),
        lambda value: value.update(scenario_action_observation_sha256="0" * 64),
    ):
        defective = copy.deepcopy(ledger); mutate(defective)
        with pytest.raises(RuntimeError, match="action projection"):
            supervisor._g7_scenario_action_projection(
                case=scenario, ledger_value=defective, boundary_event=boundary,
                boundary_sha256=boundary_sha256,
                action_events=[({"event_type": "SCENARIO_ACTION_OBSERVED"},
                                action_sha256)],
                pre_exit_subject={"captured_processes": [reporter]},
                helper_deadline_monotonic_ns=8,
                outer_deadline_monotonic_ns=24)


def test_containment_runtime_tripwires_block_transient_env_model_and_process(
        monkeypatch):
    now = time.monotonic_ns()
    control = {
        **runtime._disabled_fault_control(), "enabled": True,
        "mode": "scenario", "selected_scenario_id": "S12_final_absence_probe",
        "action": "run_registered_scenario", "test_token": "a" * 64,
        "scenario_trigger": "expire_at_outer_deadline_minus_14s",
        "cleanup_trigger": "outer_case_deadline_minus_14s",
        "fault_event_binding_sha256": "b" * 64,
        "case_start_monotonic_ns": now,
        "helper_start_deadline_monotonic_ns": now + 8_000_000_000,
        "outer_case_deadline_monotonic_ns": now + 24_000_000_000,
    }
    runtime._validate_fault_control(control)
    for category, probe in (
        ("forbidden_env_mutations",
         lambda: os.environ.__setitem__("CUDA_VISIBLE_DEVICES", "0")),
        ("model_imports", lambda: builtins.__import__("torch")),
        ("forbidden_processes", lambda: subprocess.Popen(
            ["/usr/bin/nvidia-smi"], env=runtime.FROZEN_BASE_PROCESS_ENVIRONMENT)),
    ):
        reader, writer = socket.socketpair(socket.AF_UNIX, socket.SOCK_DGRAM)
        try:
            with pytest.raises(runtime._ContainmentTripwireViolation):
                with runtime._containment_runtime_tripwires(
                        control=control, event_fd=writer.fileno(),
                        role="launcher"):
                    probe()
            value = runtime.base.strict_json_loads(
                reader.recv(4096).decode("utf-8"))
            assert value["event_type"] == "TRIPWIRE_FIRED"
            assert value["payload"]["category"] == category
        finally:
            reader.close(); writer.close()


@pytest.mark.parametrize("kind", ("crash", "exception"))
@pytest.mark.parametrize("operation", runtime.CONTAINMENT_CLEANUP_OPERATION_IDS)
def test_cleanup_side_effect_mutations_fail_for_crash_and_exception(
        tmp_path, monkeypatch, kind, operation):
    """A replaced production cleanup primitive can never produce PASS evidence."""
    now = time.monotonic_ns()
    row = runtime.TMUX_HELPER_HOOKS[0]
    control = {
        **runtime._disabled_fault_control(), "enabled": True, "mode": "hook",
        "selected_hook_id": row[1],
        "action": ("report_then_sigstop_crash" if kind == "crash" else
                   "report_then_raise_after_resume"),
        "test_token": "a" * 64, "case_index": row[0],
        "fault_event_binding_sha256": "b" * 64,
        "case_start_monotonic_ns": now,
        "helper_start_deadline_monotonic_ns": now + 8_000_000_000,
        "outer_case_deadline_monotonic_ns": now + 24_000_000_000,
    }
    runtime._validate_fault_control(control)
    scratch = tmp_path / "scratch"; scratch.mkdir(mode=0o700)
    tmux_path = tmp_path / "tmux.sock"
    config = {
        "scratch_root": str(scratch), "tmux_socket_path": str(tmux_path),
        "broker_socket_path": str(tmp_path / "broker.sock"),
        "pane_socket_path": str(tmp_path / "pane.sock"),
        "session": "msae-independent-v3-gen9-containment",
        "cleanup_budget": dict(runtime.CONTAINMENT_CLEANUP_BUDGET),
        "fault_event_fd": -1, "fault_event_binding": {},
    }
    monkeypatch.setattr(runtime, "_fault_hook", lambda *_args, **_kwargs: None)
    completed = lambda argv, **_kwargs: subprocess.CompletedProcess(argv, 1)
    monkeypatch.setattr(runtime, "_run_tmux_client", completed)
    captured = {}
    child = None
    server = None
    binding = None
    listener = None
    protected_pgids = ()
    real_killpg = os.killpg
    if operation == "tmux_session_clients":
        monkeypatch.setattr(
            runtime, "_run_tmux_client",
            lambda *_args, **_kwargs: (_ for _ in ()).throw(
                RuntimeError("stubbed tmux session client")))
    elif operation == "descendant_groups":
        child = subprocess.Popen(
            [sys.executable, "-c", "import time; time.sleep(30)"],
            start_new_session=True, stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        process = runtime._process_identity(child.pid)
        captured[(child.pid, str(process["start_ticks"]))] = process
        monkeypatch.setattr(runtime, "_containment_terminate_captured",
                            lambda *_args, **_kwargs: None)
    elif operation == "foreground_server":
        class StubServer:
            pid = 999_999
            def poll(self): return None
            def terminate(self): return None
            def kill(self): return None
            def wait(self, **_kwargs): return None
        server = StubServer()
        monkeypatch.setattr(runtime, "_containment_terminate_captured",
                            lambda *_args, **_kwargs: None)
    elif operation == "registered_socket_unlinks":
        monkeypatch.setattr(runtime, "_containment_terminate_captured",
                            lambda *_args, **_kwargs: None)
        listener = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        listener.bind(str(tmux_path)); os.chmod(tmux_path, 0o700)
        binding = runtime._tmux_socket_identity(tmux_path)
        monkeypatch.setattr(runtime, "_containment_unlink_bound_socket",
                            lambda *_args, **_kwargs: None)
    elif operation == "final_has_session_probe":
        monkeypatch.setattr(runtime, "_containment_terminate_captured",
                            lambda *_args, **_kwargs: None)
        monkeypatch.setattr(
            runtime, "_run_tmux_client",
            lambda argv, **_kwargs: subprocess.CompletedProcess(
                argv, 0 if "has-session" in argv else 1))
    elif operation == "terminal_evidence":
        monkeypatch.setattr(runtime, "_containment_terminate_captured",
                            lambda *_args, **_kwargs: None)
        monkeypatch.setattr(runtime, "_containment_terminalize",
                            lambda *_args, **_kwargs: None)
    elif operation == "complementary_groups":
        child = subprocess.Popen(
            [sys.executable, "-c",
             "import signal,time; signal.signal(signal.SIGTERM, signal.SIG_IGN); "
             "time.sleep(30)"],
            start_new_session=True, stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        protected_pgids = (child.pid,)
        monkeypatch.setattr(runtime, "_containment_terminate_captured",
                            lambda *_args, **_kwargs: None)
        monkeypatch.setattr(runtime.os, "killpg", lambda *_args: None)
    else:
        raise AssertionError(f"unregistered cleanup operation: {operation}")
    owner = row[4] if kind == "crash" else row[5]
    try:
        with pytest.raises(RuntimeError, match="cleanup incomplete"):
            runtime._containment_monitor_cleanup(
                config, control, server=server, tmux_binding=binding,
                captured=captured, listener_bindings={}, owner=owner,
                reason="mutation", fired=set(),
                protected_pgids=protected_pgids)
    finally:
        if listener is not None:
            listener.close()
        if tmux_path.exists():
            tmux_path.unlink()
        if child is not None:
            with contextlib.suppress(ProcessLookupError):
                real_killpg(child.pid, signal.SIGKILL)
            with contextlib.suppress(subprocess.TimeoutExpired):
                child.wait(timeout=2)


def test_failed_handoff_extinction_kills_real_processes_and_socket(
        monkeypatch, request):
    """Coordinate the one registered real-tmux matrix; never clean a case."""
    raw_control_fd = os.environ.get("MSAE_GEN7_TEST_CONTROL_FD")
    if raw_control_fd is None:
        pytest.skip("the reviewed gen9 outer supervisor is required")
    assert raw_control_fd.isdecimal() and int(raw_control_fd) >= 3
    control_socket = socket.socket(fileno=int(raw_control_fd))
    control_socket.settimeout(24)
    implementation = (
        runtime.continuation.CONTROLLER_PATH, runtime.RUNTIME, runtime.RUNNER,
        runtime.LAUNCHER, runtime.TMUX_TEST_SUPERVISOR, runtime.RUNTIME_RFC,
        runtime.RUNTIME_TEST,
    )
    token_preimage = {
        "schema_version": "msae_v3_gen9_test_token_preimage_v1",
        "plan_sha256": runtime.base.sha_file(runtime.PLAN_PATH),
        "implementation_sha256s": [runtime.base.sha_file(path)
                                    for path in implementation],
    }
    token = runtime.base.sha_bytes(runtime.base.canonical_bytes(token_preimage))
    cases = [
        (row[0], row[1], kind)
        for row in (*runtime.TMUX_HELPER_HOOKS, *runtime.TMUX_FAKE_HOOKS)
        for kind in ("crash", "exception")
    ]
    cases.extend((row[0],) for row in runtime.TMUX_SCENARIOS)
    assert len(cases) == 162

    def frame(case_id, sequence, prior, frame_type, payload):
        return {"schema_version": "msae_v3_gen9_test_control_frame_v1",
                "test_token": token, "case_id": case_id,
                "sequence": sequence, "prior_frame_sha256": prior,
                "frame_type": frame_type, "payload": payload}

    def send(value):
        raw = runtime.base.canonical_bytes(value)
        assert control_socket.send(raw) == len(raw)
        return runtime.base.sha_bytes(raw)

    def receive(case_id, sequence, prior, frame_type, fd_count=0):
        raw, ancillary, flags, _ = control_socket.recvmsg(
            65536, socket.CMSG_SPACE(4 * max(1, fd_count)))
        assert raw and not flags & (socket.MSG_TRUNC | socket.MSG_CTRUNC)
        received = []
        for level, kind, data in ancillary:
            assert level == socket.SOL_SOCKET and kind == socket.SCM_RIGHTS
            values = array.array("i"); values.frombytes(data[:len(data) - len(data) % values.itemsize])
            received.extend(values.tolist())
        assert len(received) == fd_count
        value = runtime.base.strict_json_loads(raw.decode("utf-8"))
        assert raw == runtime.base.canonical_bytes(value)
        assert value == frame(case_id, sequence, prior, frame_type,
                              value["payload"])
        return value, runtime.base.sha_bytes(raw), received

    closed_environment = {"PATH": "/usr/bin:/bin",
                          "HOME": "/thayerfs/home/f004ndc",
                          "LANG": "C.UTF-8", "LC_ALL": "C.UTF-8"}
    original_popen = subprocess.Popen

    def guarded_popen(argv, *args, **kwargs):
        vector = [str(item) for item in argv]
        assert vector[:5] == [
            str(runtime.ROOT / ".venv-atlas/bin/python"), "-S", "-B", "-I",
            str(runtime.continuation.CONTROLLER_PATH)]
        runtime._require_exact_command_shape(vector[5:])
        assert vector[5:10] == [
            "internal-tmux-test-role", "--role", "launcher",
            "--test-token", token]
        assert kwargs.get("shell", False) is False
        assert kwargs.get("cwd") == runtime.ROOT
        assert dict(kwargs.get("env") or {}) == closed_environment
        return original_popen(argv, *args, **kwargs)

    def forbidden_process(*args, **kwargs):
        raise AssertionError(f"forbidden real-test process surface: {args!r}")

    monkeypatch.setattr(subprocess, "Popen", guarded_popen)
    for name in ("run", "call", "check_call", "check_output"):
        monkeypatch.setattr(subprocess, name, forbidden_process)
    monkeypatch.setattr(os, "system", forbidden_process)
    for name in ("posix_spawn", "posix_spawnp", "execv", "execve", "execvp",
                 "execvpe", "execl", "execlp", "execlpe"):
        if hasattr(os, name):
            monkeypatch.setattr(os, name, forbidden_process)

    forbidden_env = runtime.re.compile(
        r"^(?:CUDA|HIP|ROCR|HSA|NVIDIA|LD_PRELOAD$|LD_LIBRARY_PATH$|"
        r"PYTHONPATH$)", runtime.re.ASCII)
    environ_type = type(os.environ)
    original_env_set = environ_type.__setitem__
    original_env_del = environ_type.__delitem__
    original_env_update = environ_type.update

    def guard_env_set(self, key, value):
        assert forbidden_env.search(str(key)) is None
        original_env_set(self, key, value)

    def guard_env_del(self, key):
        assert forbidden_env.search(str(key)) is None
        original_env_del(self, key)

    def guard_env_update(self, *args, **kwargs):
        values = dict(*args, **kwargs)
        assert all(forbidden_env.search(str(key)) is None for key in values)
        original_env_update(self, values)

    monkeypatch.setattr(environ_type, "__setitem__", guard_env_set)
    monkeypatch.setattr(environ_type, "__delitem__", guard_env_del)
    monkeypatch.setattr(environ_type, "update", guard_env_update)
    original_import = builtins.__import__
    forbidden_imports = (
        "torch", "transformers", "transformer_lens", "tensorflow", "jax",
        "cupy", "triton", "pynvml", "nvidia", "bitsandbytes")

    def guarded_import(name, *args, **kwargs):
        assert not any(name == prefix or name.startswith(prefix + ".")
                       for prefix in forbidden_imports)
        return original_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", guarded_import)
    quarantine = runtime.base.quarantine_open_tripwire()
    quarantine_state = quarantine.__enter__()

    def finish_quarantine():
        quarantine.__exit__(None, None, None)
        assert quarantine_state["blocked_content_open_attempts"] == []

    request.addfinalizer(finish_quarantine)
    for case in cases:
        case_id = str(case[1] if len(case) == 3 else case[0])
        request_payload = ({"case_index": case[0], "hook_id": case[1],
                            "injection_kind": case[2], "scenario_id": None}
                           if len(case) == 3 else
                           {"case_index": None, "hook_id": None,
                            "injection_kind": None, "scenario_id": case[0]})
        prior = send(frame(case_id, 1, None, "CASE_REQUEST", request_payload))
        channel, prior, received = receive(
            case_id, 2, prior, "CASE_EVENT_CHANNEL", fd_count=1)
        event_fd = received[0]
        binding = channel["payload"]["fault_event_binding"]
        assert set(binding) == {"schema_version", "family", "type", "path",
                                "supervisor_endpoint", "writer_endpoint",
                                "supervisor_pid", "pytest_pid", "case_id"}
        assert binding["pytest_pid"] == os.getpid()
        assert binding["case_id"] == case_id
        assert runtime._fault_binding_from_writer_fd(
            event_fd, token=token, case_id=case_id,
            pytest_pid=os.getpid()) == binding
        barrier_read, barrier_write = os.pipe2(os.O_CLOEXEC)
        if len(case) == 3:
            suffix = ["--case-index", f"{case[0]:02d}", "--hook-id", case[1],
                      "--injection-kind", case[2]]
        else:
            suffix = ["--scenario-id", case[0]]
        argv = [str(runtime.ROOT / ".venv-atlas/bin/python"), "-S", "-B", "-I",
                str(runtime.continuation.CONTROLLER_PATH),
                "internal-tmux-test-role", "--role", "launcher",
                "--test-token", token, *suffix,
                "--event-fd", str(event_fd),
                "--start-barrier-fd", str(barrier_read),
                "--case-start-monotonic-ns",
                str(channel["payload"]["case_start_monotonic_ns"]),
                "--helper-start-deadline-monotonic-ns",
                str(channel["payload"]["helper_start_deadline_monotonic_ns"]),
                "--outer-case-deadline-monotonic-ns",
                str(channel["payload"]["outer_case_deadline_monotonic_ns"])]
        launcher = subprocess.Popen(
            argv, cwd=runtime.ROOT, env=closed_environment,
            pass_fds=(event_fd, barrier_read), close_fds=True,
            start_new_session=True, stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
        os.close(event_fd); os.close(barrier_read)
        launcher_row = runtime._process_identity(launcher.pid)
        identity_payload = {
            "pid": launcher_row["pid"], "start_ticks": launcher_row["start_ticks"],
            "ppid": launcher_row["ppid"], "pgid": launcher_row["pgid"],
            "argv_sha256": runtime.base.sha_bytes(runtime.base.canonical_bytes(argv)),
            "environment_sha256": runtime.base.sha_bytes(
                runtime.base.canonical_bytes(closed_environment)),
        }
        prior = send(frame(case_id, 3, prior, "CASE_LAUNCHER_IDENTITY",
                           identity_payload))
        authorization, prior, no_fds = receive(
            case_id, 4, prior, "CASE_LAUNCHER_AUTHORIZED")
        assert not no_fds
        assert authorization["payload"] == {
            "launcher_identity_sha256": runtime.base.sha_bytes(
                runtime.base.canonical_bytes(identity_payload))}
        assert os.write(barrier_write, b"B") == 1
        os.close(barrier_write)
        returncode = launcher.wait(timeout=max(
            0.001, (channel["payload"]["outer_case_deadline_monotonic_ns"] -
                    time.monotonic_ns()) / 1e9))
        scratch = Path(f"/tmp/m9s_{token}")
        ledger = (scratch / f"case-{case[0]:02d}-{case[1]}-{case[2]}.json"
                  if len(case) == 3 else
                  scratch / f"scenario-{case[0]}.json")
        deadline_ns = channel["payload"]["outer_case_deadline_monotonic_ns"]
        ledger_raw = b""
        ledger_value = None
        while time.monotonic_ns() < deadline_ns:
            if ledger.is_file():
                with contextlib.suppress(
                        ValueError, UnicodeDecodeError, json.JSONDecodeError,
                        FileNotFoundError):
                    candidate_raw = runtime._regular_bytes(ledger, mode=0o600)
                    candidate = runtime.base.strict_json_loads(
                        candidate_raw.decode("utf-8"))
                    if candidate_raw == runtime.base.canonical_bytes(candidate):
                        ledger_raw, ledger_value = candidate_raw, candidate
                        break
            time.sleep(0.002)
        diagnostic = b"" if launcher.stderr is None else launcher.stderr.read()
        if ledger_value is None:
            pytest.fail(case_id + "\n" + diagnostic.decode("utf-8", "replace"),
                        pytrace=False)
        assert ledger_raw == runtime.base.canonical_bytes(ledger_value)
        ledger_sha = runtime.base.sha_bytes(ledger_raw)
        prior = send(frame(case_id, 5, prior, "CASE_RESULT", {
            "launcher_returncode": returncode,
            "ledger_path": str(ledger), "ledger_sha256": ledger_sha,
            "outcome": "contained_expected_failure"}))
        release, prior, no_fds = receive(case_id, 6, prior, "CASE_RELEASE")
        assert not no_fds and release["payload"]["ledger_sha256"] == ledger_sha
        assert not ledger.parent.exists()
    control_socket.close()

def test_nonisolated_controller_entry_is_rejected_before_any_command(tmp_path):
    result = subprocess.run(
        [str(ROOT / ".venv-atlas/bin/python"), "-B", "-I",
         str(runtime.continuation.CONTROLLER_PATH), "build-m2-completion"],
        text=True, capture_output=True)
    assert result.returncode != 0
    assert "require -S -I -B interpreter isolation" in result.stderr


def test_gen9_terminal_payload_preserves_two_failed_gen3_invocations_honestly():
    value = runtime._gen3_terminal_payload()
    assert value["status"] == "failed_before_first_protocol_state_write"
    assert value["setup_m3_command_attempts"] == 2
    assert value["setup_m3_attempt_statuses"] == ["failed_prewrite", "failed_prewrite"]
    disclosed = value["operator_disclosed"]["invocations"]
    assert disclosed[0]["full_transcript_available"] is False
    assert disclosed[1]["transcript_size"] == 935
    assert disclosed[1]["transcript_sha256"] == \
        "e39e1583d30ce5eb0aa5277ff88d3eb37bee2eb357d8e68ca366591847413020"
    assert value["mechanically_reproduced_source_control_flow"][
        "raise_dominates_first_protocol_write"] is True
    observed = value["mechanically_observed_current_absence"]
    assert observed["evidence_class"] == "current_state_not_historical_syscall_observation"
    assert observed["sealed_payload_content_reads"] == 0
    assert "protocol_writes_observed" not in value


def test_historical_preflight_verification_has_no_write_or_fsync_surface(monkeypatch):
    def forbidden(*_args, **_kwargs):
        raise AssertionError("read-only preflight attempted a write/fsync")
    monkeypatch.setattr(runtime.base, "write_once", forbidden)
    monkeypatch.setattr(runtime.base, "install_json", forbidden)
    monkeypatch.setattr(runtime.os, "fsync", forbidden)
    value = runtime._verify_historical_preflight_readonly()
    assert value["successor_generation"] == "post_m2_gen2"
    assert runtime.base.sha_file(runtime.PREFLIGHT_FAILURE_PATH) == \
        runtime.HISTORICAL_PREFLIGHT_SHA256


def test_exact_gen9_cli_shape_rejects_reordering_duplicates_and_old_routes():
    setup = [
        "setup-m3-gen9",
        "--reviewed-m2-sha256", runtime.M2_REVIEWED_COMPLETION_SHA256,
        "--failed-gen3-plan-review-sha256", runtime.FAILED_GEN3_PLAN_REVIEW_SHA256,
        "--failed-gen3-implementation-review-sha256",
        runtime.FAILED_GEN3_IMPLEMENTATION_REVIEW_SHA256,
        "--failed-gen4-plan-review-sha256",
        runtime.FAILED_GEN4_PLAN_REVIEW_SHA256,
        "--failed-gen5-plan-review-sha256",
        runtime.FAILED_GEN5_PLAN_REVIEW_SHA256,
        "--gen9-plan-review-sha256", runtime.FROZEN_PLAN_REVIEW_SHA256,
        "--gen9-pre-capability-review-sha256", "b" * 64,
        "--gen9-implementation-review-sha256", "a" * 64,
    ]
    runtime._require_exact_command_shape(setup)
    for defective in (
        [*setup[:3], *setup[5:7], *setup[3:5], *setup[7:]],
        [*setup, "--gen9-implementation-review-sha256", "a" * 64],
        ["setup-m3", *setup[1:]],
        ["build-m4-gen9", "--post-m3-review-sha256", "A" * 64],
        ["sign-gen9", "extra"],
    ):
        with pytest.raises(ValueError):
            runtime._require_exact_command_shape(defective)


def test_atomic_publisher_recovers_only_exact_prefix_partial(tmp_path):
    target = tmp_path / "artifact.json"
    raw = b'{"schema":"registered"}\n'
    partial = tmp_path / ".artifact.json.partial"
    partial.write_bytes(raw[:7]); partial.chmod(0o644)
    runtime._atomic_publish(target, raw, 0o644)
    assert target.read_bytes() == raw and not partial.exists()
    bad = tmp_path / "bad.json"
    bad_partial = tmp_path / ".bad.json.partial"
    bad_partial.write_bytes(b"wrong"); bad_partial.chmod(0o644)
    with pytest.raises(ValueError, match="exact prefix"):
        runtime._atomic_publish(bad, raw, 0o644)
    assert not bad.exists() and bad_partial.exists()


@pytest.mark.parametrize("location", ("analysis", "transaction", "marker_only"))
def test_capability_reentry_rejects_undeclared_children_before_mutation(
        tmp_path, monkeypatch, location):
    analysis = tmp_path / "analysis"; analysis.mkdir(mode=0o700)
    transaction = analysis / ".capability_report_transaction"
    report = analysis / "gen9_capability_reproduction.json"
    if location == "analysis":
        report.write_bytes(b"{}\n"); report.chmod(0o644)
        extra = analysis / "undeclared"; extra.write_bytes(b"x")
    elif location == "transaction":
        transaction.mkdir(mode=0o700)
        extra = transaction / "undeclared"; extra.write_bytes(b"x")
    else:
        transaction.mkdir(mode=0o700)
        extra = transaction / ".transaction.json.attempt-1"; extra.mkdir(mode=0o700)
    before = {path.relative_to(tmp_path).as_posix(): path.read_bytes()
              for path in tmp_path.rglob("*") if path.is_file()}
    monkeypatch.setattr(runtime, "CAPABILITY_ANALYSIS_ROOT", analysis)
    monkeypatch.setattr(runtime, "CAPABILITY_TRANSACTION", transaction)
    monkeypatch.setattr(runtime, "CAPABILITY_REPORT", report)
    monkeypatch.setattr(runtime, "_plan_review_binding", lambda _value: {})
    monkeypatch.setattr(runtime, "_pre_capability_review_binding", lambda _value: {})
    monkeypatch.setattr(runtime, "_failed_gen4_entries", lambda: {})
    monkeypatch.setattr(runtime, "_failed_gen5_entries", lambda: {})
    monkeypatch.setattr(runtime, "_validate_capability_report", lambda _value: None)
    monkeypatch.setattr(
        runtime, "_pre_capability_namespace_gate",
        lambda *, allow_capability_root: {
            "allow_capability_root": allow_capability_root})
    with pytest.raises(ValueError, match=(
            "directory projection drift|undeclared child|lost descriptor authority")):
        runtime.probe_gen9_capability(report, "a" * 64)
    after = {path.relative_to(tmp_path).as_posix(): path.read_bytes()
             for path in tmp_path.rglob("*") if path.is_file()}
    assert after == before and extra.exists()


@pytest.mark.parametrize("late_drift", ("outer_extra", "report_inode_swap"))
def test_capability_reauthorizes_report_and_outer_namespace_before_descriptor_delete(
        tmp_path, monkeypatch, late_drift):
    analysis = tmp_path / "analysis"; analysis.mkdir(mode=0o700)
    transaction = analysis / ".capability_report_transaction"
    transaction.mkdir(mode=0o700)
    report = analysis / "gen9_capability_reproduction.json"
    descriptor_path = transaction / "transaction.json"
    report_value = {"schema_version": "capability-gate-test-v1"}
    report_raw = runtime.base.canonical_bytes(report_value)
    row = runtime._publication_row(
        0, transaction, "report.payload", analysis, report.name,
        report_raw, 0o644, "gen9_capability_report")
    subject = {"GEN6_TEST": {"path": "test", "sha256": "f" * 64}}
    authority = runtime.base.sha_bytes(runtime.base.canonical_bytes({
        "plan_review_sha256": runtime.FROZEN_PLAN_REVIEW_SHA256,
        "pre_capability_review_sha256": "a" * 64,
        "implementation_entries": subject,
    }))
    descriptor = runtime._link_transaction_payload(
        kind="capability", authority_sha256=authority,
        publications=[row], maximum_seconds=300,
        sealed_random_payloads={
            "report_b64": base64.b64encode(report_raw).decode("ascii")})
    descriptor_path.write_bytes(runtime.base.canonical_bytes(descriptor))
    descriptor_path.chmod(0o600)

    monkeypatch.setattr(runtime, "CAPABILITY_ANALYSIS_ROOT", analysis)
    monkeypatch.setattr(runtime, "CAPABILITY_TRANSACTION", transaction)
    monkeypatch.setattr(runtime, "CAPABILITY_REPORT", report)
    monkeypatch.setattr(runtime, "_plan_review_binding", lambda _value: {})
    monkeypatch.setattr(runtime, "_pre_capability_review_binding", lambda _value: {})
    monkeypatch.setattr(runtime, "_failed_gen4_entries", lambda: {})
    monkeypatch.setattr(runtime, "_failed_gen5_entries", lambda: {})
    monkeypatch.setattr(runtime, "_current_gen9_implementation_entries", lambda: subject)
    monkeypatch.setattr(runtime, "_validate_capability_report", lambda _value: None)
    monkeypatch.setattr(
        runtime, "_pre_capability_namespace_gate",
        lambda *, allow_capability_root: {
            "allow_capability_root": allow_capability_root})
    monkeypatch.setattr(runtime, "_bootstrap_link_transaction", lambda *_args: None)

    def publish_then_mutate(*_args, **_kwargs):
        report.write_bytes(report_raw); report.chmod(0o644)
        if late_drift == "outer_extra":
            extra = analysis / "late-extra"
            extra.write_bytes(b"late\n"); extra.chmod(0o600)
        return {"status": "published", "outcome": "linked"}
    monkeypatch.setattr(runtime, "_link_publication", publish_then_mutate)

    original_regular = runtime._regular_bytes
    swapped = False
    def swap_after_report_read(path, *, mode, owner=None):
        nonlocal swapped
        raw = original_regular(path, mode=mode, owner=owner)
        if (late_drift == "report_inode_swap" and Path(path) == report
                and not swapped):
            swapped = True
            report.unlink(); report.write_bytes(report_raw); report.chmod(0o644)
        return raw
    if late_drift == "report_inode_swap":
        monkeypatch.setattr(runtime, "_regular_bytes", swap_after_report_read)

    with pytest.raises(ValueError, match=(
            "directory projection drift|report changed before authority cleanup")):
        runtime.probe_gen9_capability(report, "a" * 64)
    assert descriptor_path.is_file()
    assert runtime.base.read_json(descriptor_path) == descriptor


def test_setup_prefix_validator_rejects_receipt_hole(tmp_path, monkeypatch):
    prov = tmp_path / "prov"; prov.mkdir(mode=0o700)
    journal = prov / ".setup_m3_gen9_transaction"; journal.mkdir(mode=0o700)
    transaction = journal / "transaction.json"
    transaction.write_bytes(runtime.base.canonical_bytes({"schema": "test"})); transaction.chmod(0o600)
    receipt2 = journal / runtime.SETUP_RECEIPT_NAMES[1]
    receipt2.write_bytes(runtime.base.canonical_bytes({"schema": "test"})); receipt2.chmod(0o600)
    monkeypatch.setattr(runtime, "ACTIVE_PROV", prov)
    monkeypatch.setattr(runtime, "SETUP_JOURNAL", journal)
    monkeypatch.setattr(runtime, "SETUP_MANIFEST", prov / "setup_m3_gen9_manifest.json")
    monkeypatch.setattr(runtime, "M4_NEW", tuple())
    monkeypatch.setattr(runtime, "M4_TRANSACTION", tmp_path / "m4txn")
    monkeypatch.setattr(runtime, "M4_PRIMARY", tmp_path / "primary")
    monkeypatch.setattr(runtime, "M4_REBUILD", tmp_path / "rebuild")
    monkeypatch.setattr(runtime, "POST_M3_REVIEW", tmp_path / "post")
    monkeypatch.setattr(runtime, "PRESCORE_REVIEW", tmp_path / "prescore")
    monkeypatch.setattr(runtime, "ACTIVE_RUN_ROOT", tmp_path / "run")
    monkeypatch.setattr(runtime, "_validate_gen3_review_namespace", lambda phase: None)
    monkeypatch.setattr(runtime, "_post_m3_forbidden_tmp_patterns", lambda: tuple())
    with pytest.raises(ValueError, match="receipt set is not a prefix"):
        runtime._setup_expected_empty_or_prefix({})


def test_setup_m3_gen9_builds_and_cleans_exact_24_receipt_chain(
        tmp_path, monkeypatch):
    """Run the real setup state machine with only expensive science stubbed."""
    prov = tmp_path / "provenance"
    data = tmp_path / "m4_data"
    config = tmp_path / "config"
    state = tmp_path / "state"
    nonce = state / "nonces"
    keys = tmp_path / "keys"; keys.mkdir(mode=0o700)
    private = keys / "private.pem"
    key_staging = keys / ".setup_key"
    journal = prov / ".setup"
    manifest = prov / "setup_manifest.json"
    failed5 = prov / "failed_gen5.json"
    failed6 = prov / "failed_gen6.json"
    failed4 = prov / "failed_gen4.json"
    failed3 = prov / "failed_gen3.json"
    failed2 = prov / "failed_gen2.json"
    capability = tmp_path / "capability.json"
    capability.write_bytes(runtime.base.canonical_bytes({"capability": True}))
    capability.chmod(0o644)
    implementation = tmp_path / "implementation.md"
    implementation.write_text("implementation\n"); implementation.chmod(0o644)
    mappings = {
        "ROOT": tmp_path,
        "ACTIVE_PROV": prov, "ACTIVE_M4_DATA": data,
        "ACTIVE_CONFIG": config, "ACTIVE_STATE": state,
        "CPU_NO_MODEL_TRACE": config / "cpu_no_model_public_entry_trace.json",
        "ACTIVE_NONCE_DIR": nonce, "ACTIVE_PRIVATE_KEY": private,
        "SETUP_KEY_TRANSACTION": key_staging, "SETUP_JOURNAL": journal,
        "SETUP_MANIFEST": manifest, "FAILED_GEN4_RECORD": failed4,
        "FAILED_GEN6_RECORD": failed6, "FAILED_GEN5_RECORD": failed5,
        "FAILED_GEN3_RECORD": failed3, "FAILED_GEN2_RECORD": failed2,
        "CAPABILITY_REPORT": capability,
        "IMPLEMENTATION_REVIEW": implementation,
        "M4_TRANSACTION": prov / ".m4", "M4_PRIMARY": tmp_path / "primary",
        "M4_REBUILD": tmp_path / "rebuild",
        "POST_M3_REVIEW": tmp_path / "post_m3.md",
        "PRESCORE_REVIEW": tmp_path / "prescore.md",
        "ACTIVE_RUN_ROOT": tmp_path / "run",
    }
    for name, value in mappings.items():
        monkeypatch.setattr(runtime, name, value)
    fake_mount = {
        "schema_version": "msae_v3_gen9_mount_identity_v1",
        "mountinfo": {"filesystem_type": "nfs4"},
        "mountinfo_sha256": "7" * 64,
        "filesystem_magic": "0x6969", "filesystem_fsid": [7, 8],
        "directory_device": tmp_path.stat().st_dev,
    }
    monkeypatch.setattr(runtime, "_mount_identity", lambda _path: dict(fake_mount))
    monkeypatch.setattr(runtime, "_plan_review_binding", lambda _digest: {})
    monkeypatch.setattr(runtime, "_pre_capability_review_binding", lambda _digest: {})
    monkeypatch.setattr(runtime, "verify_m2_completion", lambda _digest: {})
    monkeypatch.setattr(runtime, "preserve_m3_preflight", lambda: {})
    monkeypatch.setattr(runtime, "_validate_capability_report", lambda _value: None)
    monkeypatch.setattr(runtime, "_validate_gen3_review_namespace", lambda _phase: None)
    monkeypatch.setattr(runtime, "_post_m3_forbidden_tmp_patterns", lambda: tuple())
    monkeypatch.setattr(runtime, "_gen3_terminal_payload",
                        lambda: {"schema_version": "terminal-v1"})
    monkeypatch.setattr(runtime, "_failed_gen3_wrapper",
                        lambda _value: {"schema_version": "failed3-v1"})
    monkeypatch.setattr(runtime, "_gen2_failure_payload",
                        lambda _value: {"schema_version": "failure2-v1"})
    monkeypatch.setattr(runtime, "_failed_gen2_wrapper",
                        lambda _value, _parent: {"schema_version": "failed2-v1"})
    monkeypatch.setattr(runtime, "_failed_gen4_terminal_payload",
                        lambda _value: {"schema_version": "failed4-v1"})
    monkeypatch.setattr(runtime, "_failed_gen5_terminal_payload",
                        lambda _value: {"schema_version": "failed5-v1"})
    monkeypatch.setattr(runtime, "_failed_gen6_terminal_payload",
                        lambda: {"schema_version": "failed6-v1"})
    monkeypatch.setattr(
        runtime, "_implementation_review_binding",
        lambda supplied, *_args: {"sha256": supplied})
    monkeypatch.setattr(runtime, "_current_gen9_entries", lambda: {})
    monkeypatch.setattr(runtime, "_trace_review_gates", lambda *_args: {})
    monkeypatch.setattr(runtime, "checkpoint_registry", lambda *args, **kwargs: [])
    trace = {field: None for field in runtime.CPU_NO_MODEL_TRACE_FIELDS}
    trace["schema_version"] = "msae_v3_cpu_no_model_public_entry_trace_v3"
    trace["status"] = "eligible"
    monkeypatch.setattr(
        runtime, "cpu_no_model_public_entry_trace",
        lambda **_kwargs: copy.deepcopy(trace))
    monkeypatch.setattr(
        runtime, "_validate_cpu_no_model_trace", lambda *_args, **_kwargs: None)
    config_value = {key: None for key in (
        runtime.GENERIC_CONFIG_KEYS + runtime.SUCCESSOR_CONFIG_KEYS)}
    config_value["schema_version"] = "msae_v3_protocol_config_v1"
    monkeypatch.setattr(
        runtime, "_protocol_config_payload",
        lambda *_args, **_kwargs: copy.deepcopy(config_value))

    completion = runtime.setup_m3_gen9(
        runtime.M2_REVIEWED_COMPLETION_SHA256,
        runtime.FAILED_GEN3_PLAN_REVIEW_SHA256,
        runtime.FAILED_GEN3_IMPLEMENTATION_REVIEW_SHA256,
        runtime.FAILED_GEN4_PLAN_REVIEW_SHA256,
        runtime.FAILED_GEN5_PLAN_REVIEW_SHA256,
        runtime.FROZEN_PLAN_REVIEW_SHA256,
        "7" * 64,
        "8" * 64)
    assert completion["schema_version"] == "msae_v3_gen9_m3_completion_v1"
    assert runtime._verify_setup_manifest()["status"] == \
        "complete_non_authorizing_m3"
    assert not journal.exists() and not key_staging.exists()
    assert {entry.name for entry in os.scandir(prov)} == {
        "failed_gen6.json", "failed_gen5.json", "failed_gen4.json",
        "failed_gen3.json", "failed_gen2.json", "setup_manifest.json"}
    assert {entry.name for entry in os.scandir(config)} == {
        "ed25519_public.pem", "authorization_commitment.json",
        "cpu_no_model_public_entry_trace.json", "protocol.json"}
    assert private.exists() and private.stat().st_nlink == 1
    assert not list(prov.glob(".*.partial"))
    assert not list(prov.glob(".*.attempt-*"))


def test_sign_transaction_reuses_bound_random_bytes_after_rename_failure(
        tmp_path, monkeypatch):
    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

    config = tmp_path / "config"; config.mkdir(mode=0o700)
    prov = tmp_path / "prov"; prov.mkdir(mode=0o700)
    data = tmp_path / "data"; data.mkdir(mode=0o700)
    nonce = tmp_path / "state/nonces"; nonce.mkdir(mode=0o700, parents=True)
    run = tmp_path / "run"
    private_path = tmp_path / "keys/private.pem"; private_path.parent.mkdir(mode=0o700)
    private = Ed25519PrivateKey.generate()
    private_raw = private.private_bytes(serialization.Encoding.PEM,
                                        serialization.PrivateFormat.PKCS8,
                                        serialization.NoEncryption())
    private_path.write_bytes(private_raw); private_path.chmod(0o600)
    public_raw = private.public_key().public_bytes(
        serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo)
    for path, raw in (
        (config / "ed25519_public.pem", public_raw),
        (config / "authorization_commitment.json", b"commitment\n"),
        (config / "protocol.json", b"protocol\n"),
        (prov / "stage_a.json", b"stage\n"),
        (prov / "prescore_candidate_manifest.json", b"manifest\n"),
        (data / "dependency_closure.json", b"closure\n"),
    ):
        path.write_bytes(raw); path.chmod(0o644)
    implementation = tmp_path / "implementation.md"
    post_m3 = tmp_path / "post_m3.md"
    prescore = tmp_path / "prescore.md"
    for path, raw in ((implementation, b"implementation\n"),
                      (post_m3, b"post-m3\n"),
                      (prescore, b"prescore\n")):
        path.write_bytes(raw); path.chmod(0o644)
    st = private_path.lstat()
    binding = {"path": str(private_path), "device": st.st_dev, "inode": st.st_ino,
               "uid": st.st_uid, "mode": 0o600, "nlink": 1, "size": st.st_size,
               "mtime_ns": st.st_mtime_ns, "ctime_ns": st.st_ctime_ns,
               "public_key_match": True}
    commitment = {
        "envelope_schema": "msae_v3_signed_authorization_v2",
        "maximum_lifetime_seconds": 86400,
        "operator_instruction_sha256": runtime.base.sha_bytes(
            runtime.OPERATOR_INSTRUCTION.encode()),
        "private_key_binding": binding,
        "public_key_sha256": runtime.base.sha_bytes(public_raw),
        "nonce_directory": runtime.base._directory_binding(nonce),
    }
    monkeypatch.setattr(runtime, "ACTIVE_CONFIG", config)
    monkeypatch.setattr(runtime, "ACTIVE_PROV", prov)
    monkeypatch.setattr(runtime, "ACTIVE_M4_DATA", data)
    monkeypatch.setattr(runtime, "ACTIVE_NONCE_DIR", nonce)
    monkeypatch.setattr(runtime, "ACTIVE_PRIVATE_KEY", private_path)
    monkeypatch.setattr(runtime, "ACTIVE_RUN_ROOT", run)
    monkeypatch.setattr(runtime, "SIGN_TRANSACTION", run / ".sign_transaction")
    monkeypatch.setattr(runtime, "IMPLEMENTATION_REVIEW", implementation)
    monkeypatch.setattr(runtime, "POST_M3_REVIEW", post_m3)
    monkeypatch.setattr(runtime, "PRESCORE_REVIEW", prescore)
    fake_mount = {
        "schema_version": "msae_v3_gen9_mount_identity_v1",
        "mountinfo": {"filesystem_type": "nfs4"},
        "mountinfo_sha256": "b" * 64,
        "filesystem_magic": "0x6969", "filesystem_fsid": [3, 4],
        "directory_device": tmp_path.stat().st_dev,
    }
    monkeypatch.setattr(runtime, "_mount_identity", lambda _path: dict(fake_mount))
    phases = []
    monkeypatch.setattr(runtime, "verify_candidate_manifest",
                        lambda phase: phases.append(phase) or {"eligible": True})
    monkeypatch.setattr(runtime, "_verify_existing_authorization_state",
                        lambda **kwargs: commitment)
    original_link = runtime._linkat
    calls = 0
    def fail_once(source_fd, source, destination_fd, destination):
        nonlocal calls
        if destination == "authorization.json":
            calls += 1
        if destination == "authorization.json" and calls == 1:
            raise OSError(runtime.errno.EIO, "injected link failure")
        return original_link(source_fd, source, destination_fd, destination)
    monkeypatch.setattr(runtime, "_linkat", fail_once)
    with pytest.raises(runtime.RecoverableLinkInterruption,
                       match="retained exact source"):
        runtime._sign_authorization_impl()
    descriptor_before = (run / ".sign_transaction/transaction.json").read_bytes()
    staged_before = (run / ".sign_transaction/authorization.payload").read_bytes()
    output = runtime._sign_authorization_impl()
    assert runtime.base.canonical_bytes(output) == staged_before
    assert not (run / ".sign_transaction").exists()
    assert (run / "authorization.json").read_bytes() == staged_before
    assert runtime.base.sha_bytes(descriptor_before) != runtime.base.sha_bytes(staged_before)
    assert phases == ["post_review", "sign_recovery", "post_signature"]
