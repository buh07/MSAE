#!/usr/bin/env python3
"""Source-only supervisor for the single reviewed gen7 tmux extinction test.

This is a CPU/process-containment harness, not an experiment launcher.  It owns
all temporary names, the broker identity handshake, the pytest deadline, and
final process/session/path extinction.
"""
from __future__ import annotations

import json
import hashlib
import contextlib
import ctypes
import os
from pathlib import Path
import selectors
import signal
import socket
import stat
import struct
import subprocess
import sys
import threading
import time
import traceback
from typing import Any

ROOT = Path("/jumbo/lisp/f004ndc/experiments/wip/MSAE")
PYTHON = ROOT / ".venv-atlas/bin/python"
TMUX = Path("/usr/bin/tmux")
SELF = ROOT / "scripts/run_msae_independent_measurement_v3_post_m2_gen7_tmux_test.py"
TERM_TIMEOUT = 3.0


def _canonical_bytes(value: Any) -> bytes:
    return (json.dumps(value, sort_keys=True, separators=(",", ":"),
                       ensure_ascii=False) + "\n").encode("utf-8")


def _path_present(path: Path) -> bool:
    return path.exists() or path.is_symlink()


def _proc_row(pid: int) -> dict[str, int | str] | None:
    try:
        raw = Path(f"/proc/{pid}/stat").read_text(encoding="ascii")
    except (FileNotFoundError, ProcessLookupError):
        return None
    right = raw.rfind(")")
    if right < 2:
        raise RuntimeError(f"malformed proc stat for {pid}")
    fields = raw[right + 2:].split()
    if len(fields) < 20:
        raise RuntimeError(f"short proc stat for {pid}")
    try:
        proc_stat = Path(f"/proc/{pid}").stat()
    except (FileNotFoundError, ProcessLookupError):
        return None
    return {"pid": pid, "state": fields[0], "ppid": int(fields[1]),
            "pgrp": int(fields[2]), "start_ticks": int(fields[19]),
            "uid": proc_stat.st_uid, "gid": proc_stat.st_gid}


def _pid_matches(pid: int, ticks: int) -> bool:
    row = _proc_row(pid)
    return row is not None and row["state"] != "Z" and row["start_ticks"] == ticks


def _group_members(pgid: int) -> list[int]:
    result: list[int] = []
    for entry in Path("/proc").iterdir():
        if not entry.name.isdecimal():
            continue
        row = _proc_row(int(entry.name))
        if row is not None and row["state"] != "Z" and row["pgrp"] == pgid:
            result.append(int(entry.name))
    return sorted(result)


def _read_identity(path: Path) -> dict[str, Any] | None:
    if not _path_present(path):
        return None
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC)
    try:
        before = os.fstat(fd)
        if (not stat.S_ISREG(before.st_mode) or before.st_uid != os.getuid()
                or before.st_nlink != 1 or stat.S_IMODE(before.st_mode) != 0o600
                or before.st_size > 16384):
            return None
        chunks: list[bytes] = []
        while True:
            chunk = os.read(fd, 16384)
            if not chunk:
                break
            chunks.append(chunk)
        after = os.fstat(fd)
    finally:
        os.close(fd)
    if ((before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns,
         before.st_ctime_ns) !=
            (after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns,
             after.st_ctime_ns)):
        return None
    raw = b"".join(chunks)
    try:
        value = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        return None
    return value if raw == _canonical_bytes(value) and isinstance(value, dict) else None


def _validate_identity(value: dict[str, Any], pane_pid: int,
                       peer: tuple[int, int, int]) -> dict[str, Any]:
    expected_keys = {
        "schema_version", "monitor_pid", "monitor_start_ticks",
        "server_pid", "server_start_ticks", "server_pgid",
        "pane_pid", "pane_start_ticks", "pane_ppid",
        "broker_pid", "broker_start_ticks", "broker_ppid", "broker_pgid",
        "worker_pid", "worker_start_ticks", "worker_ppid", "worker_pgid",
    }
    if set(value) != expected_keys or value.get("schema_version") != \
            "msae_v3_gen7_tmux_test_process_v1":
        raise RuntimeError("tmux test identity schema drift")
    ints = {key: value[key] for key in expected_keys - {"schema_version"}}
    if any(type(item) is not int or item <= 0 for item in ints.values()):
        raise RuntimeError("tmux test identity integer drift")
    peer_pid, peer_uid, peer_gid = peer
    if peer_uid != os.getuid() or peer_gid != os.getgid() or peer_pid != value["pane_pid"]:
        raise RuntimeError("tmux test peer credential drift")
    if value["pane_pid"] != pane_pid:
        raise RuntimeError("tmux pane identity drift")
    for prefix in ("monitor", "server", "pane", "broker", "worker"):
        if not _pid_matches(int(value[f"{prefix}_pid"]),
                            int(value[f"{prefix}_start_ticks"])):
            raise RuntimeError(f"tmux test {prefix} identity is not live")
    if (value["server_pid"] != value["pane_ppid"]
            or value["monitor_pid"] != _proc_row(value["server_pid"])["ppid"]
            or value["server_pgid"] != value["server_pid"]
            or value["broker_ppid"] != value["pane_pid"]
            or value["broker_pgid"] != value["broker_pid"]
            or value["worker_ppid"] != value["broker_pid"]
            or value["worker_pgid"] != value["worker_pid"]):
        raise RuntimeError("tmux monitor/server/pane/broker/worker lineage drift")
    return value


def _publish_identity_bound(path: Path, value: dict[str, Any]) -> None:
    raw = _canonical_bytes(value)
    partial = path.with_name(".identity_bound.json.partial")
    fd = os.open(partial, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    try:
        os.fchmod(fd, 0o600)
        view = memoryview(raw)
        while view:
            written = os.write(fd, view)
            if written <= 0:
                raise OSError("short identity-bound write")
            view = view[written:]
        os.fsync(fd)
    finally:
        os.close(fd)
    os.link(partial, path, follow_symlinks=False)
    dfd = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        os.fsync(dfd)
        os.unlink(partial)
        os.fsync(dfd)
    finally:
        os.close(dfd)


def _write_test_terminal(scratch: Path, *, owner: str, reason: str,
                         pane_pid: int) -> None:
    """Publish the two exact non-protocol test terminal records once."""
    values = (
        ("terminal.claim.test", {
            "schema_version": "msae_v3_gen7_tmux_test_terminal_claim_v1",
            "owner": owner, "pane_pid": pane_pid}),
        ("technical_failure.test.json", {
            "schema_version": "msae_v3_gen7_tmux_test_technical_failure_v1",
            "reason": reason, "pane_pid": pane_pid}),
    )
    directory_fd = os.open(
        scratch, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC)
    try:
        for name, value in values:
            raw = _canonical_bytes(value)
            fd = os.open(name, os.O_WRONLY | os.O_CREAT | os.O_EXCL |
                         os.O_NOFOLLOW | os.O_CLOEXEC, 0o600,
                         dir_fd=directory_fd)
            try:
                os.fchmod(fd, 0o600)
                view = memoryview(raw)
                while view:
                    written = os.write(fd, view)
                    if written <= 0:
                        raise OSError("short tmux test terminal write")
                    view = view[written:]
                os.fsync(fd)
            finally:
                os.close(fd)
            os.fsync(directory_fd)
    finally:
        os.close(directory_fd)


def _validate_test_terminal(scratch: Path, *, owner: str, reason: str,
                            pane_pid: int) -> None:
    expected = {
        "terminal.claim.test": {
            "schema_version": "msae_v3_gen7_tmux_test_terminal_claim_v1",
            "owner": owner, "pane_pid": pane_pid},
        "technical_failure.test.json": {
            "schema_version": "msae_v3_gen7_tmux_test_technical_failure_v1",
            "reason": reason, "pane_pid": pane_pid},
    }
    for name, value in expected.items():
        observed = _read_identity(scratch / name)
        if observed != value:
            raise RuntimeError(f"tmux test terminal record drift: {name}")


def _cleanup_record_payload(raw: bytes, *, final_name: str,
                            partial_only: bool) -> bool:
    if len(raw) > 16384 or b"\x00" in raw or b"\r" in raw:
        return False
    try:
        value = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        # A write interruption may leave only the exact transaction-local
        # partial.  It is removable only as a bounded UTF-8 JSON prefix.
        if not partial_only:
            return False
        try:
            raw.decode("utf-8")
        except UnicodeDecodeError:
            return False
        return raw == b"" or raw.startswith(b"{")
    if raw != _canonical_bytes(value) or not isinstance(value, dict):
        return False
    if final_name == "process.json":
        expected = {
            "schema_version", "monitor_pid", "monitor_start_ticks",
            "server_pid", "server_start_ticks", "server_pgid",
            "pane_pid", "pane_start_ticks", "pane_ppid",
            "broker_pid", "broker_start_ticks", "broker_ppid", "broker_pgid",
            "worker_pid", "worker_start_ticks", "worker_ppid", "worker_pgid",
        }
        return (set(value) == expected
                and value.get("schema_version") ==
                    "msae_v3_gen7_tmux_test_process_v1"
                and all(type(value[key]) is int and value[key] > 0
                        for key in expected - {"schema_version"}))
    if final_name == "identity_bound.json":
        return (set(value) == {"schema_version", "process_sha256", "supervisor_pid"}
                and value.get("schema_version") ==
                    "msae_v3_gen7_tmux_test_identity_bound_v1"
                and isinstance(value.get("process_sha256"), str)
                and len(value["process_sha256"]) == 64
                and all(character in "0123456789abcdef"
                        for character in value["process_sha256"])
                and type(value.get("supervisor_pid")) is int
                and value["supervisor_pid"] > 0)
    if final_name == "terminal.claim.test":
        return (set(value) == {"schema_version", "owner", "pane_pid"}
                and value.get("schema_version") ==
                    "msae_v3_gen7_tmux_test_terminal_claim_v1"
                and value.get("owner") in {"pane_supervisor", "monitor"}
                and type(value.get("pane_pid")) is int
                and value["pane_pid"] > 1)
    if final_name == "technical_failure.test.json":
        return (set(value) == {"schema_version", "reason", "pane_pid"}
                and value.get("schema_version") ==
                    "msae_v3_gen7_tmux_test_technical_failure_v1"
                and value.get("reason") in {
                    "monitor_or_server_death", "pane_supervisor_death"}
                and type(value.get("pane_pid")) is int
                and value["pane_pid"] > 1)
    return False


def _cleanup_owned_regular_pair(parent: Path, partial_name: str,
                                final_name: str) -> bool:
    """Remove only a one-name result or the exact crash-left hard-link pair."""
    path_before = parent.lstat()
    directory_fd = os.open(parent, os.O_RDONLY | os.O_DIRECTORY |
                           os.O_NOFOLLOW | os.O_CLOEXEC)
    try:
        held_before = os.fstat(directory_fd)
        if (not stat.S_ISDIR(held_before.st_mode)
                or stat.S_IMODE(held_before.st_mode) != 0o700
                or held_before.st_uid != os.getuid()
                or (held_before.st_dev, held_before.st_ino) !=
                   (path_before.st_dev, path_before.st_ino)):
            return False
        rows: dict[str, tuple[os.stat_result, bytes]] = {}
        for name in (partial_name, final_name):
            try:
                by_path = os.stat(name, dir_fd=directory_fd,
                                  follow_symlinks=False)
            except FileNotFoundError:
                continue
            file_fd = os.open(name, os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC,
                              dir_fd=directory_fd)
            try:
                before = os.fstat(file_fd)
                raw = b""
                while True:
                    chunk = os.read(file_fd, 16384 - len(raw) + 1)
                    if not chunk:
                        break
                    raw += chunk
                    if len(raw) > 16384:
                        return False
                after = os.fstat(file_fd)
            finally:
                os.close(file_fd)
            identity = lambda item: (
                item.st_dev, item.st_ino, item.st_mode, item.st_uid,
                item.st_nlink, item.st_size, item.st_mtime_ns, item.st_ctime_ns)
            if (identity(before) != identity(after)
                    or identity(after) != identity(by_path)
                    or not stat.S_ISREG(after.st_mode)
                    or stat.S_IMODE(after.st_mode) != 0o600
                    or after.st_uid != os.getuid() or after.st_nlink not in {1, 2}):
                return False
            rows[name] = (after, raw)
        if len(rows) == 2:
            # The publisher can expose both registered names only as the
            # exact hard-link pair.  Two unrelated one-link files are not a
            # legal crash prefix and must never be deleted as owned state.
            if (set(rows) != {partial_name, final_name}
                    or len({(row[0].st_dev, row[0].st_ino)
                            for row in rows.values()}) != 1
                    or any(row[0].st_nlink != 2 for row in rows.values())):
                return False
        elif len(rows) == 1:
            # The only legal one-name publisher states are source-only and
            # destination-only, both with one link.  A registered basename
            # with another hard-link elsewhere is not transaction-owned.
            if next(iter(rows.values()))[0].st_nlink != 1:
                return False
        for name, (observed, raw) in rows.items():
            if not _cleanup_record_payload(
                    raw, final_name=final_name,
                    partial_only=(name == partial_name and final_name not in rows)):
                return False
            current = os.stat(name, dir_fd=directory_fd, follow_symlinks=False)
            if ((current.st_dev, current.st_ino, current.st_mode, current.st_uid,
                 current.st_nlink, current.st_size, current.st_mtime_ns, current.st_ctime_ns)
                    != (observed.st_dev, observed.st_ino, observed.st_mode,
                        observed.st_uid, observed.st_nlink, observed.st_size,
                        observed.st_mtime_ns, observed.st_ctime_ns)):
                return False
        removed = 0
        for name in (partial_name, final_name):
            if name in rows:
                observed = rows[name][0]
                current = os.stat(name, dir_fd=directory_fd,
                                  follow_symlinks=False)
                expected_nlink = (2 - removed) if len(rows) == 2 else 1
                # Rebind the pathname immediately before each unlink.  The
                # second member of an exact pair has legitimately changed
                # nlink/ctime after the first unlink, so compare only stable
                # identity/content metadata plus the expected link count.
                if ((current.st_dev, current.st_ino, current.st_mode,
                     current.st_uid, current.st_size, current.st_mtime_ns,
                     current.st_nlink) !=
                        (observed.st_dev, observed.st_ino, observed.st_mode,
                         observed.st_uid, observed.st_size,
                         observed.st_mtime_ns, expected_nlink)):
                    return False
                os.unlink(name, dir_fd=directory_fd)
                os.fsync(directory_fd)
                removed += 1
        held_after = os.fstat(directory_fd); path_after = parent.lstat()
        return ((held_before.st_dev, held_before.st_ino, held_before.st_mode,
                 held_before.st_uid) ==
                (held_after.st_dev, held_after.st_ino, held_after.st_mode,
                 held_after.st_uid) ==
                (path_after.st_dev, path_after.st_ino, path_after.st_mode,
                 path_after.st_uid))
    finally:
        os.close(directory_fd)


def _wait_child_until(
    child: subprocess.Popen[bytes], deadline: float, shutdown_requested: Any,
    selector: selectors.BaseSelector | None = None,
) -> int:
    while child.poll() is None:
        if shutdown_requested():
            raise RuntimeError("tmux test supervisor shutdown")
        if time.monotonic() >= deadline:
            raise TimeoutError("tmux test child deadline")
        if selector is None:
            time.sleep(0.02)
        else:
            for key, _mask in selector.select(timeout=0.02):
                if key.data == "shutdown":
                    with contextlib.suppress(BlockingIOError):
                        os.read(int(key.fileobj), 4096)
                elif key.data == "listener":
                    raise RuntimeError(
                        "duplicate or late tmux identity connection")
    return int(child.returncode)


def _reject_pending_identity_frame(connection: socket.socket) -> None:
    """Require that the exact completed handshake has no queued extra bytes."""
    connection.settimeout(0.05)
    try:
        extra = connection.recv(1, socket.MSG_PEEK)
    except TimeoutError:
        return
    if extra:
        raise RuntimeError("duplicate or late tmux identity frame")


def _terminate_child_group(child: subprocess.Popen[bytes]) -> None:
    errors: list[str] = []
    if child.poll() is None or _group_members(child.pid):
        try:
            os.killpg(child.pid, signal.SIGTERM)
        except ProcessLookupError:
            pass
        except BaseException as exc:
            errors.append(f"TERM:{exc}")
        deadline = time.monotonic() + TERM_TIMEOUT
        while ((child.poll() is None or _group_members(child.pid))
               and time.monotonic() < deadline):
            time.sleep(0.02)
        if child.poll() is None or _group_members(child.pid):
            try:
                os.killpg(child.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
            except BaseException as exc:
                errors.append(f"KILL:{exc}")
    try:
        child.wait(timeout=TERM_TIMEOUT)
    except BaseException as exc:
        errors.append(f"wait:{exc}")
    if _group_members(child.pid):
        errors.append("process-group-still-live")
    if errors:
        raise RuntimeError("tmux child extinction failed: " + ";".join(errors))

# Gen7 registered 162-case outer supervisor.  The older pure helper functions
# above remain importable for their focused CPU regressions; this is the sole
# executable entrypoint and it never starts tmux or performs passing cleanup.

G7_PLAN = ROOT / "docs/plan-msae-independent-measurement-v3-post-m7-gen7.md"
G7_IMPLEMENTATION = (
    ROOT / "scripts/msae_independent_measurement_v3_post_m2_gen7.py",
    ROOT / "scripts/msae_independent_measurement_v3_post_m2_gen7_runtime.py",
    ROOT / "scripts/run_msae_independent_calibration_v3_gen7.py",
    ROOT / "scripts/launch_msae_independent_calibration_v3_gen7.sh",
    SELF,
    ROOT / "docs/rfc-msae-independent-measurement-v3-post-m7-gen7.md",
    ROOT / "tests/test_msae_independent_measurement_v3_post_m7_gen7.py",
)
G7_CONTROL_SCHEMA = "msae_v3_gen7_test_control_frame_v1"
G7_TEST_NODE = ("tests/test_msae_independent_measurement_v3_post_m7_gen7.py::"
                "test_failed_handoff_extinction_kills_real_processes_and_socket")
G7_HOOKS = (
    (1, "before_monitor_record_write", "launcher", "pre", "monitor", "launcher"),
    (2, "after_monitor_record_file_fsync", "launcher", "post", "monitor", "launcher"),
    (3, "after_monitor_record_parent_fsync", "launcher", "post", "monitor", "launcher"),
    (4, "after_monitor_record_committed_send", "launcher", "post", "monitor", "launcher"),
    (5, "before_monitor_record_ack_receive", "launcher", "pre", "monitor", "launcher"),
    (6, "after_monitor_record_ack_receive", "launcher", "post", "monitor", "launcher"),
    (7, "before_start_server_send", "launcher", "pre", "monitor", "launcher"),
    (8, "after_start_server_receive", "monitor", "post", "launcher", "monitor"),
    (9, "before_server_fork", "monitor", "pre", "launcher", "monitor"),
    (10, "server_child_before_pdeath_arm", "server_child", "pre", "monitor", "monitor"),
    (11, "server_child_after_pdeath_arm_before_exec", "server_child", "post", "monitor", "monitor"),
    (12, "parent_after_server_fork", "monitor", "post", "launcher", "monitor"),
    (13, "after_socket_publication", "monitor", "post", "launcher", "monitor"),
    (14, "before_socket_mode_promotion", "monitor", "pre", "launcher", "monitor"),
    (15, "after_socket_mode_promotion_before_tmp_fsync", "monitor", "post", "launcher", "monitor"),
    (16, "after_tmp_fsync", "monitor", "post", "launcher", "monitor"),
    (17, "before_new_session_client", "monitor", "pre", "launcher", "monitor"),
    (18, "after_new_session_client", "monitor", "post", "launcher", "monitor"),
    (19, "before_set_exit_empty_client", "monitor", "pre", "launcher", "monitor"),
    (20, "after_set_exit_empty_client", "monitor", "post", "launcher", "monitor"),
    (21, "before_show_exit_empty_client", "monitor", "pre", "launcher", "monitor"),
    (22, "after_show_exit_empty_client", "monitor", "post", "launcher", "monitor"),
    (23, "before_display_identity_client", "monitor", "pre", "launcher", "monitor"),
    (24, "after_display_identity_client_before_parse", "monitor", "post", "launcher", "monitor"),
    (25, "after_display_identity_parse", "monitor", "post", "launcher", "monitor"),
    (26, "before_pane_lease_handoff_send", "monitor", "pre", "launcher", "monitor"),
    (27, "after_pane_lease_handoff_send", "monitor", "post", "launcher", "monitor"),
    (28, "after_pane_lease_handoff_receive", "pane_supervisor", "post", "monitor", "pane_supervisor"),
    (29, "after_pane_arm_file_fsync", "pane_supervisor", "post", "monitor", "pane_supervisor"),
    (30, "after_pane_arm_parent_fsync", "pane_supervisor", "post", "monitor", "pane_supervisor"),
    (31, "before_pane_lease_ack_send", "pane_supervisor", "pre", "monitor", "pane_supervisor"),
    (32, "after_pane_lease_ack_send", "pane_supervisor", "post", "monitor", "pane_supervisor"),
    (33, "after_pane_lease_ack_receive", "monitor", "post", "launcher", "monitor"),
    (34, "before_server_ready_send", "monitor", "pre", "launcher", "monitor"),
    (35, "after_server_ready_send", "monitor", "post", "launcher", "monitor"),
    (36, "before_handoff_committed_receive", "monitor", "pre", "launcher", "monitor"),
    (37, "after_handoff_committed_receive", "monitor", "post", "launcher", "monitor"),
    (38, "before_takeover_ack_send", "monitor", "pre", "launcher", "monitor"),
    (39, "after_takeover_ack_send", "monitor", "post", "pane_supervisor", "monitor"),
    (40, "before_peer_eof_wait", "monitor", "pre", "pane_supervisor", "monitor"),
    (41, "after_peer_eof", "monitor", "post", "pane_supervisor", "monitor"),
    (42, "cleanup_before_kill_session", "monitor", "pre", "pane_supervisor", "monitor"),
    (43, "cleanup_after_kill_session", "monitor", "post", "pane_supervisor", "monitor"),
    (44, "cleanup_before_descendant_term", "monitor", "pre", "pane_supervisor", "monitor"),
    (45, "cleanup_before_descendant_kill", "monitor", "pre", "pane_supervisor", "monitor"),
    (46, "cleanup_before_server_term", "monitor", "pre", "pane_supervisor", "monitor"),
    (47, "cleanup_before_server_kill", "monitor", "pre", "pane_supervisor", "monitor"),
    (48, "cleanup_before_socket_unlink", "monitor", "pre", "pane_supervisor", "monitor"),
    (49, "cleanup_before_final_has_session", "monitor", "pre", "pane_supervisor", "monitor"),
    (50, "cleanup_after_final_has_session", "monitor", "post", "pane_supervisor", "monitor"),
    (51, "cleanup_before_terminal_claim", "monitor", "pre", "pane_supervisor", "monitor"),
    (52, "cleanup_after_terminal_claim", "monitor", "post", "monitor", "monitor"),
    (53, "before_fake_broker_fork", "pane_supervisor", "pre", "monitor", "pane_supervisor"),
    (54, "fake_broker_child_before_pdeath_arm", "fake_broker_child", "pre", "pane_supervisor", "pane_supervisor"),
    (55, "fake_broker_child_after_pdeath_arm_before_exec", "fake_broker_child", "post", "pane_supervisor", "pane_supervisor"),
    (56, "pane_after_fake_broker_fork", "pane_supervisor", "post", "monitor", "pane_supervisor"),
    (57, "before_process_record_partial_write", "fake_broker", "pre", "pane_supervisor", "pane_supervisor"),
    (58, "after_process_record_partial_write", "fake_broker", "post", "pane_supervisor", "pane_supervisor"),
    (59, "after_process_record_file_fsync", "fake_broker", "post", "pane_supervisor", "pane_supervisor"),
    (60, "after_process_record_hardlink", "fake_broker", "post", "pane_supervisor", "pane_supervisor"),
    (61, "after_process_record_source_unlink", "fake_broker", "post", "pane_supervisor", "pane_supervisor"),
    (62, "before_identity_ack_send", "fake_broker", "pre", "pane_supervisor", "pane_supervisor"),
    (63, "after_identity_ack_send", "fake_broker", "post", "pane_supervisor", "pane_supervisor"),
    (64, "before_barrier_release_receive", "fake_broker", "pre", "pane_supervisor", "pane_supervisor"),
    (65, "after_barrier_release_receive", "fake_broker", "post", "pane_supervisor", "pane_supervisor"),
    (66, "before_resistance_arm", "fake_broker", "pre", "pane_supervisor", "pane_supervisor"),
    (67, "after_resistance_arm", "fake_broker", "post", "pane_supervisor", "pane_supervisor"),
    (68, "before_fake_handoff_commit_send", "fake_broker", "pre", "pane_supervisor", "pane_supervisor"),
    (69, "after_fake_handoff_commit_send", "fake_broker", "post", "pane_supervisor", "pane_supervisor"),
    (70, "before_fake_takeover_ack_receive", "fake_broker", "pre", "pane_supervisor", "pane_supervisor"),
    (71, "after_fake_takeover_ack_receive", "fake_broker", "post", "pane_supervisor", "pane_supervisor"),
    (72, "before_fake_worker_fork", "fake_broker", "pre", "pane_supervisor", "pane_supervisor"),
    (73, "fake_worker_child_before_pdeath_arm", "fake_worker_child", "pre", "pane_supervisor", "pane_supervisor"),
    (74, "fake_worker_child_after_pdeath_arm_before_exec", "fake_worker_child", "post", "pane_supervisor", "pane_supervisor"),
    (75, "fake_broker_after_worker_fork", "fake_broker", "post", "pane_supervisor", "pane_supervisor"),
)
G7_SCENARIO_ROWS = (
    ("S01_monitor_death", "monitor_after_lm5_pane_arm_before_lm6",
     "outer_supervisor", "kill_monitor_before_handoff",
     "sigkill_monitor_before_handoff", "launcher"),
    ("S02_server_death", "monitor_proxy_after_lm5_before_lm6",
     "outer_supervisor", "kill_server_before_handoff",
     "resume_monitor_then_sigkill_server_group", "monitor"),
    ("S03_pane_death", "pane_after_lm7_expected_eof",
     "outer_supervisor", "kill_pane_after_takeover",
     "sigkill_pane_group_after_takeover", "monitor"),
    ("S04_broker_death", "broker_after_lm7_before_worker_terminal",
     "outer_supervisor", "kill_broker_after_takeover",
     "sigkill_broker_after_takeover", "pane_supervisor"),
    ("S05_worker_death", "worker_after_pre_model_gate",
     "outer_supervisor", "kill_worker_after_pre_model_gate",
     "sigkill_worker_after_pre_model_gate", "pane_supervisor"),
    ("S06_duplicate_frame", "launcher_after_lm3_before_lm4",
     "per_case_launcher", "duplicate_monitor_frame_2",
     "send_duplicate_lm2", "monitor"),
    ("S07_late_frame", "launcher_after_lm5_before_lm6",
     "per_case_launcher", "replay_stale_monitor_frame_4",
     "replay_stale_lm4", "monitor"),
    ("S08_monitor_death_after_launcher_eof",
     "monitor_after_lm7_expected_eof", "outer_supervisor",
     "kill_monitor_after_expected_eof",
     "sigkill_monitor_after_expected_eof", "pane_supervisor"),
    ("S09_child_timeout", "launcher_waiting_lm5_after_lm4",
     "per_case_launcher", "receive_timeout_lm5_at_helper_deadline",
     "observe_lm5_receive_timeout", "launcher"),
    ("S10_term_resistant_descendant", "worker_sigterm_ignored_after_lm7",
     "outer_supervisor", "sigusr1_pane_after_resistance_prefix",
     "resume_worker_then_sigusr1_pane", "pane_supervisor"),
    ("S11_kill_escalation",
     "broker_with_stopped_resistant_worker_after_lm7", "fake_broker",
     "exit_broker_leave_resistant_group",
     "resume_worker_then_exit_broker_97", "pane_supervisor"),
    ("S12_final_absence_probe", "monitor_live_baseline_after_expected_eof",
     "monitor", "expire_at_outer_deadline_minus_14s",
     "expire_monitor_at_outer_minus_14s", "monitor"),
)
G7_SCENARIOS = tuple(row[0] for row in G7_SCENARIO_ROWS)


def _lower_sha256(value: Any) -> bool:
    return (isinstance(value, str) and len(value) == 64
            and all(character in "0123456789abcdef" for character in value))


def _g7_validate_owner_ledger(
        value: dict[str, Any], *, case: tuple[Any, ...], token: str,
        ledger_path: Path, boundary_event: dict[str, Any],
        boundary_sha256: str,
        action_events: list[tuple[dict[str, Any], str]]) -> None:
    common = {
        "test_token", "expected_terminal_owner", "expected_cleanup_owner",
        "evidence_publisher", "production_cleanup_complete",
        "emergency_cleanup_used", "terminal_claim_sha256",
        "evidence_projection_sha256", "pre_exit_absence_sha256",
        "expected_outer_final_descriptor_sha256", "outcome",
    }
    if len(case) == 3:
        row = next(item for item in G7_HOOKS if item[0] == case[0])
        expected_keys = common | {
            "schema_version", "case_index", "hook_id", "injection_kind",
            "reporter_role", "reporter_pid", "reporter_kind",
            "reporter_start_ticks", "reporter_pgid", "boundary_state",
        }
        if (set(value) != expected_keys
                or value.get("schema_version") !=
                   "msae_v3_gen7_tmux_fault_case_v1"
                or value.get("case_index") != row[0]
                or value.get("hook_id") != row[1]
                or value.get("injection_kind") != case[2]
                or value.get("boundary_state") != row[3]):
            raise RuntimeError("hook owner-ledger schema/table drift")
        terminal_owner = row[4] if case[2] == "crash" else row[5]
        cleanup_owner = ("pane_supervisor" if row[0] == 52
                         and case[2] == "crash" else terminal_owner)
        expected_role = ("monitor" if row[2] == "server_child" else
                         "pane_supervisor" if row[2] in {
                             "fake_broker_child", "fake_worker_child"}
                         else row[2])
        if (boundary_event.get("event_type") != "HOOK_REACHED"
                or boundary_event.get("reporter_kind") != row[2]
                or boundary_event.get("reporter_role") != expected_role
                or boundary_event.get("payload") != {
                    "case_index": row[0], "hook_id": row[1],
                    "injection_kind": case[2]}
                or action_events):
            raise RuntimeError("hook boundary/action evidence drift")
    else:
        row = next(item for item in G7_SCENARIO_ROWS if item[0] == case[0])
        expected_keys = common | {
            "schema_version", "scenario_id", "reporter_role",
            "reporter_kind", "reporter_pid", "reporter_start_ticks",
            "reporter_pgid", "boundary_event_sha256", "action_event_sha256",
            "initiator", "target_identity", "trigger",
            "scenario_action_observation_sha256",
        }
        schema_checks = {
            "keys": set(value) == expected_keys,
            "schema_version": value.get("schema_version") ==
                              "msae_v3_gen7_tmux_fault_scenario_v1",
            "scenario_id": value.get("scenario_id") == row[0],
            "initiator": value.get("initiator") == row[2],
            "trigger": value.get("trigger") == row[3],
            "boundary_event_sha256":
                value.get("boundary_event_sha256") == boundary_sha256,
        }
        if not all(schema_checks.values()):
            failed = sorted(key for key, passed in schema_checks.items()
                            if not passed)
            raise RuntimeError(
                f"scenario owner-ledger schema/table drift: {failed}")
        terminal_owner = cleanup_owner = row[5]
        required_action = row[0] in {
            "S06_duplicate_frame", "S07_late_frame", "S09_child_timeout"}
        action_sha256s = [digest for _event, digest in action_events]
        if (len(action_events) != (1 if required_action else 0)
                or value.get("action_event_sha256") !=
                   (action_sha256s[0] if required_action else None)
                or not _lower_sha256(
                    value.get("scenario_action_observation_sha256"))):
            raise RuntimeError("scenario action evidence drift")
        if required_action:
            action_event = action_events[0][0]
            if (action_event["payload"].get("boundary_event_sha256") !=
                    boundary_sha256):
                raise RuntimeError(
                    "scenario action did not bind the observed boundary")
    if (value.get("test_token") != token
            or value.get("expected_terminal_owner") != terminal_owner
            or value.get("expected_cleanup_owner") != cleanup_owner
            or value.get("evidence_publisher") != cleanup_owner
            or value.get("production_cleanup_complete") is not True
            or value.get("emergency_cleanup_used") is not False
            or value.get("outcome") != "contained_expected_failure"):
        raise RuntimeError("owner-ledger outcome/authority drift")
    for key in ("terminal_claim_sha256", "evidence_projection_sha256",
                "pre_exit_absence_sha256",
                "expected_outer_final_descriptor_sha256"):
        if not _lower_sha256(value.get(key)):
            raise RuntimeError(f"owner-ledger digest drift: {key}")
    if (value.get("reporter_role") != boundary_event.get("reporter_role")
            or value.get("reporter_kind") != boundary_event.get("reporter_kind")
            or value.get("reporter_pid") != boundary_event.get("pid")
            or str(value.get("reporter_start_ticks")) !=
               str(boundary_event.get("start_ticks"))
            or value.get("reporter_pgid") != boundary_event.get("pgid")):
        raise RuntimeError("owner-ledger reporter is not the credentialed boundary")
    derivation = {
        "schema_version": "msae_v3_gen7_test_outer_final_derivation_v1",
        "test_token": token,
        "case_or_scenario_id": (case[1] if len(case) == 3 else case[0]),
        "evidence_publisher": cleanup_owner, "ledger_path": str(ledger_path),
        "pre_exit_absence_sha256": value["pre_exit_absence_sha256"],
        "required_transitions": [
            "publisher_exit", "publisher_group_empty",
            "ledger_descriptor_reopen", "ledger_unlink", "scratch_rmdir",
            "all_seven_families_empty"],
    }
    if (hashlib.sha256(_canonical_bytes(derivation)).hexdigest() !=
            value["expected_outer_final_descriptor_sha256"]):
        raise RuntimeError("owner-ledger outer-final derivation drift")


def _g7_sha_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _g7_test_token() -> str:
    value = {"schema_version": "msae_v3_gen7_test_token_preimage_v1",
             "plan_sha256": _g7_sha_file(G7_PLAN),
             "implementation_sha256s": [_g7_sha_file(path)
                                         for path in G7_IMPLEMENTATION]}
    return hashlib.sha256(_canonical_bytes(value)).hexdigest()


def _g7_frame(token: str, case_id: str, sequence: int, prior: str | None,
              frame_type: str, payload: dict[str, Any]) -> dict[str, Any]:
    return {"schema_version": G7_CONTROL_SCHEMA, "test_token": token,
            "case_id": case_id, "sequence": sequence,
            "prior_frame_sha256": prior, "frame_type": frame_type,
            "payload": payload}


def _g7_send(sock: socket.socket, frame: dict[str, Any], fd: int | None = None) -> str:
    raw = _canonical_bytes(frame)
    ancillary = [] if fd is None else [(socket.SOL_SOCKET, socket.SCM_RIGHTS,
                                        struct.pack("i", fd))]
    if sock.sendmsg([raw], ancillary) != len(raw):
        raise RuntimeError("short gen7 control send")
    return hashlib.sha256(raw).hexdigest()


def _g7_recv(sock: socket.socket, token: str, case_id: str, sequence: int,
             prior: str | None, frame_type: str) -> tuple[dict[str, Any], str]:
    raw, ancillary, flags, _ = sock.recvmsg(65536, socket.CMSG_SPACE(4))
    if not raw or ancillary or flags & (socket.MSG_TRUNC | socket.MSG_CTRUNC):
        raise RuntimeError("gen7 control frame/ancillary drift")
    value = json.loads(raw)
    if raw != _canonical_bytes(value) or set(value) != {
            "schema_version", "test_token", "case_id", "sequence",
            "prior_frame_sha256", "frame_type", "payload"}:
        raise RuntimeError("gen7 control canonical schema drift")
    if value != _g7_frame(token, case_id, sequence, prior, frame_type,
                          value["payload"]):
        raise RuntimeError("gen7 control frame ordering drift")
    return value, hashlib.sha256(raw).hexdigest()


def _g7_socket_row(fd: int) -> dict[str, int]:
    st = os.fstat(fd)
    return {"device": st.st_dev, "inode": st.st_ino, "uid": st.st_uid,
            "gid": st.st_gid, "mode": stat.S_IMODE(st.st_mode),
            "nlink": st.st_nlink}


def _g7_fault_binding(read_fd: int, write_fd: int, *, supervisor_pid: int,
                      pytest_pid: int, case_id: str) -> dict[str, Any]:
    return {"schema_version": "msae_v3_gen7_fault_event_binding_v1",
            "family": "AF_UNIX", "type": "SOCK_DGRAM", "path": None,
            "supervisor_endpoint": _g7_socket_row(read_fd),
            "writer_endpoint": _g7_socket_row(write_fd),
            "supervisor_pid": supervisor_pid, "pytest_pid": pytest_pid,
            "case_id": case_id}


def _g7_capture(roots: set[int], captured: dict[int, dict[str, Any]]) -> None:
    rows: dict[int, dict[str, Any]] = {}
    for name in os.listdir("/proc"):
        if not name.isdecimal():
            continue
        row = _proc_row(int(name))
        if row is not None:
            rows[int(name)] = row
    owned = set(roots) | set(captured)
    changed = True
    while changed:
        changed = False
        for pid, row in rows.items():
            if pid not in owned and int(row["ppid"]) in owned:
                owned.add(pid); changed = True
    for pid in owned:
        row = rows.get(pid)
        if row is not None:
            if pid not in captured:
                enriched = dict(row)
                try:
                    enriched["_argv"] = [
                        item.decode("utf-8", "surrogateescape") for item in
                        Path(f"/proc/{pid}/cmdline").read_bytes().split(b"\0")
                        if item]
                    enriched["_exe"] = os.readlink(f"/proc/{pid}/exe")
                except (FileNotFoundError, ProcessLookupError, PermissionError):
                    enriched["_argv"] = []
                    enriched["_exe"] = None
                captured[pid] = enriched


def _g7_process_roles(captured: dict[int, dict[str, Any]],
                      launcher_pid: int,
                      publisher_event: dict[str, Any]) -> dict[int, str]:
    """Classify the complete first-seen process tree without owner labels."""
    roles: dict[int, str] = {launcher_pid: "launcher"}
    for pid, row in captured.items():
        argv = [str(item) for item in row.get("_argv", [])]
        if "--role" in argv:
            index = argv.index("--role")
            if index + 1 < len(argv):
                declared = argv[index + 1]
                if declared in {"launcher", "monitor"}:
                    roles[pid] = declared
        if row.get("_exe") == "/usr/bin/tmux" and "-D" in argv:
            roles[pid] = "tmux_server"
    primary_monitors = [pid for pid, role in roles.items()
                        if role == "monitor"
                        and int(captured[pid].get("ppid", -1)) == launcher_pid]
    if len(primary_monitors) == 1:
        monitor_pid = primary_monitors[0]
        for pid, role in list(roles.items()):
            if (pid != monitor_pid and role == "monitor"
                    and int(captured[pid].get("ppid", -1)) == monitor_pid):
                roles[pid] = "tmux_server"
    changed = True
    while changed:
        changed = False
        for pid, row in captured.items():
            if pid in roles:
                continue
            parent_role = roles.get(int(row.get("ppid", -1)))
            inferred = ("tmux_server" if parent_role == "monitor"
                        else "pane_supervisor" if parent_role == "tmux_server"
                        else "fake_broker" if parent_role == "pane_supervisor"
                        else "fake_worker" if parent_role == "fake_broker"
                        else None)
            if inferred is not None:
                roles[pid] = inferred; changed = True
    publisher_pid = int(publisher_event["pid"])
    roles[publisher_pid] = str(publisher_event["reporter_role"])
    for pid in captured:
        roles.setdefault(pid, "captured_descendant")
    return roles


def _g7_terminal_hashes(case: tuple[Any, ...], terminal_owner: str) -> tuple[str, str]:
    if len(case) == 3:
        reason = (f"registered_hook:{int(case[0]):02d}:{case[1]}:"
                  f"{case[2]}:{terminal_owner}")
    else:
        reason = f"registered_scenario:{case[0]}:{terminal_owner}"
    claim = {"schema_version": "msae_v3_gen7_tmux_test_terminal_claim_v1",
             "owner": terminal_owner, "reason": reason}
    failure = {
        "schema_version": "msae_v3_gen7_tmux_test_technical_failure_v1",
        "owner": terminal_owner, "reason": reason}
    return (hashlib.sha256(_canonical_bytes(claim)).hexdigest(),
            hashlib.sha256(_canonical_bytes(failure)).hexdigest())


def _g7_staging_entries(scratch: Path) -> dict[str, dict[str, Any]]:
    paths = {
        "process_record_partial": scratch / ".process.json.partial",
        "monitor_record": scratch / "monitor.json",
        "pane_arm": scratch / "pane_arm.json",
        "monitor_log": scratch / "monitor.log",
        "server_log": scratch / "server.log",
        "process_record": scratch / "process.json",
        "lease": scratch / "lease.test",
        "terminal_claim": scratch / "terminal.claim.test",
        "technical_failure": scratch / "technical_failure.test.json",
    }
    present = sorted(name for name, path in paths.items() if _path_present(path))
    if present:
        raise RuntimeError(f"registered staging entry survived owner cleanup: {present}")
    return {name: {"path": str(path), "lexists": False}
            for name, path in sorted(paths.items())}


def _g7_process_subjects(
        captured: dict[int, dict[str, Any]], *, launcher_pid: int,
        publisher_event: dict[str, Any], publisher_live: bool,
        require_extinct: bool) -> tuple[list[dict[str, Any]],
                                        list[dict[str, Any]]]:
    roles = _g7_process_roles(captured, launcher_pid, publisher_event)
    publisher_pid = int(publisher_event["pid"])
    canonical_servers: set[int] = set()
    by_parent: dict[int, list[tuple[int, int]]] = {}
    for pid, row in captured.items():
        if roles.get(pid) == "tmux_server":
            by_parent.setdefault(int(row["ppid"]), []).append(
                (int(row["start_ticks"]), pid))
    for candidates in by_parent.values():
        canonical_servers.add(min(candidates)[1])
    broker_by_group = {
        int(row["pgrp"]): pid for pid, row in captured.items()
        if roles.get(pid) == "fake_broker"}
    rows: list[dict[str, Any]] = []
    for pid, captured_row in sorted(captured.items()):
        row = dict(captured_row)
        argv = [str(item) for item in row.get("_argv", [])]
        if row.get("_exe") == "/usr/bin/tmux" and "-D" not in argv:
            continue
        if roles.get(pid) == "tmux_server" and pid not in canonical_servers:
            continue
        if pid == publisher_pid:
            row.update({"ppid": int(publisher_event["ppid"]),
                        "pgrp": int(publisher_event["pgid"]),
                        "start_ticks": int(publisher_event["start_ticks"])})
        ticks = int(row["start_ticks"])
        live_now = _pid_matches(pid, ticks)
        if require_extinct and live_now:
            raise RuntimeError(
                f"captured process not extinct before release: {pid}")
        effective_ppid = int(row["ppid"])
        if roles[pid] == "fake_worker":
            effective_ppid = broker_by_group.get(int(row["pgrp"]),
                                                  effective_ppid)
        rows.append({
            "role": roles[pid], "pid": pid, "start_ticks": str(ticks),
            "ppid": effective_ppid, "pgid": int(row["pgrp"]),
            "uid": int(row.get("uid", os.getuid())),
            "gid": int(row.get("gid", os.getgid())),
            "live": bool(publisher_live and pid == publisher_pid),
        })
    groups: dict[int, list[int]] = {}
    for row in rows:
        groups.setdefault(int(row["pgid"]), [])
        if row["live"]:
            groups[int(row["pgid"])].append(int(row["pid"]))
    group_rows = [{"pgid": pgid, "members": sorted(members)}
                  for pgid, members in sorted(groups.items())]
    if require_extinct:
        for row in group_rows:
            members = _group_members(int(row["pgid"]))
            if members:
                raise RuntimeError(
                    f"captured process group survived before release: "
                    f"{row['pgid']}:{members}")
    return rows, group_rows


def _g7_pre_exit_subject(
        *, case: tuple[Any, ...], token: str, launcher_pid: int,
        captured: dict[int, dict[str, Any]], publisher_event: dict[str, Any],
        ledger_value: dict[str, Any], ledger: Path,
        has_session_returncode: int) -> dict[str, Any]:
    scratch = ledger.parent
    scratch_stat = scratch.lstat()
    if (not stat.S_ISDIR(scratch_stat.st_mode)
            or stat.S_IMODE(scratch_stat.st_mode) != 0o700
            or scratch_stat.st_uid != os.getuid()
            or scratch_stat.st_gid != os.getgid()
            or sorted(os.listdir(scratch)) != [ledger.name]):
        raise RuntimeError("pre-exit scratch projection drift")
    processes, groups = _g7_process_subjects(
        captured, launcher_pid=launcher_pid,
        publisher_event=publisher_event, publisher_live=True,
        require_extinct=False)
    publisher_pid = int(publisher_event["pid"])
    for row in processes:
        observed_live = _pid_matches(int(row["pid"]), int(row["start_ticks"]))
        if observed_live and int(row["pid"]) != publisher_pid:
            raise RuntimeError(
                "pre-exit process liveness had a nonpublisher")
    for row in groups:
        expected_members = ([publisher_pid]
                            if int(row["pgid"]) ==
                               int(publisher_event["pgid"]) else [])
        observed_members = _group_members(int(row["pgid"]))
        if (observed_members != expected_members
                and not (expected_members == [publisher_pid]
                         and observed_members == [])):
            raise RuntimeError(
                "pre-exit process group did not have only the publisher: "
                f"{row['pgid']}:{observed_members}")
    terminal_claim_sha, technical_sha = _g7_terminal_hashes(
        case, str(ledger_value["expected_terminal_owner"]))
    if terminal_claim_sha != ledger_value["terminal_claim_sha256"]:
        raise RuntimeError("terminal claim is not the finite case-derived object")
    tmux_path = Path(f"/tmp/m7x_{token}.sock")
    broker_path = Path(f"/tmp/m7a_{token}.sock")
    pane_path = Path(f"/tmp/m7c_{token}.sock")
    family_entries = _g7_family_entries()
    if (family_entries["m7s_"] != [scratch.name]
            or any(family_entries[prefix] for prefix in family_entries
                   if prefix != "m7s_")):
        raise RuntimeError("pre-exit short-family projection drift")
    return {
        "schema_version": "msae_v3_gen7_test_pre_exit_absence_v1",
        "test_token": token,
        "case_or_scenario_id": (case[1] if len(case) == 3 else case[0]),
        "captured_processes": processes, "process_groups": groups,
        "session": {"name": "msae-independent-v3-gen7-containment",
                    "has_session_returncode": has_session_returncode},
        "socket_paths": {str(path): {"lexists": False}
                         for path in (tmux_path, broker_path, pane_path)},
        "short_family_entries": family_entries,
        "lease": {"path": str(scratch / "lease.test"),
                  "open_holder_count": 0, "contender_acquired": True,
                  "lexists": False},
        "staging_entries": _g7_staging_entries(scratch),
        "terminal_evidence": {"claim_sha256": terminal_claim_sha,
                              "technical_failure_sha256": technical_sha},
        "scratch_projection": {
            "path": str(scratch), "mode": 0o700,
            "uid": scratch_stat.st_uid, "gid": scratch_stat.st_gid,
            "nlink": scratch_stat.st_nlink, "children": [ledger.name]},
        "tripwires": {"gpu_queries": 0, "model_imports": 0,
                      "model_calls": 0, "forbidden_env_mutations": 0,
                      "forbidden_processes": 0,
                      "sealed_payload_content_reads": 0},
    }


def _g7_scenario_action_projection(
        *, case: tuple[Any, ...], ledger_value: dict[str, Any],
        boundary_event: dict[str, Any], boundary_sha256: str,
        action_events: list[tuple[dict[str, Any], str]],
        pre_exit_subject: dict[str, Any],
        helper_deadline_monotonic_ns: int,
        outer_deadline_monotonic_ns: int) -> dict[str, Any]:
    """Independently reconstruct the exact scenario action bound by the owner."""
    if len(case) != 1:
        raise RuntimeError("scenario action projection received a hook case")
    scenario = str(case[0])
    row = next(item for item in G7_SCENARIO_ROWS if item[0] == scenario)
    reporter_pid = int(boundary_event["pid"])
    reporter_rows = [item for item in pre_exit_subject["captured_processes"]
                     if int(item["pid"]) == reporter_pid]
    if len(reporter_rows) != 1:
        raise RuntimeError("scenario reporter is absent/ambiguous in outer projection")
    reporter = reporter_rows[0]
    target: dict[str, Any] = {
        "schema_version": "msae_v3_gen7_scenario_process_v1",
        "kind": "process", "role": boundary_event["reporter_role"],
        "pid": reporter["pid"], "start_ticks": reporter["start_ticks"],
        "ppid": reporter["ppid"], "pgid": reporter["pgid"],
        "uid": reporter["uid"], "gid": reporter["gid"],
    }
    if scenario in {"S02_server_death", "S03_pane_death",
                    "S11_kill_escalation"}:
        target = {
            "schema_version": "msae_v3_gen7_scenario_process_group_v1",
            "kind": "process_group", "role": boundary_event["reporter_role"],
            "pgid": reporter["pgid"], "leader_pid": reporter["pid"],
            "leader_start_ticks": reporter["start_ticks"],
            "members": [reporter],
        }
    elif scenario in {"S06_duplicate_frame", "S07_late_frame"}:
        target = {
            "schema_version": "msae_v3_gen7_scenario_monitor_frame_v1",
            "kind": "monitor_frame", "direction": "launcher_to_monitor",
            "frame_type": ("MONITOR_RECORD_COMMITTED"
                           if scenario == "S06_duplicate_frame" else
                           "START_SERVER"),
            "sequence": 2 if scenario == "S06_duplicate_frame" else 4,
            "frame_sha256": "0" * 64, "peer_process": reporter,
        }
    elif scenario in {"S09_child_timeout", "S12_final_absence_probe"}:
        target = {
            "schema_version": "msae_v3_gen7_scenario_deadline_v1",
            "kind": "deadline", "owner_process": reporter,
            "deadline_monotonic_ns": (
                helper_deadline_monotonic_ns
                if scenario == "S09_child_timeout" else
                outer_deadline_monotonic_ns - 14_000_000_000),
            "source": row[3],
        }
    action_sha256 = action_events[0][1] if action_events else None
    projection = {
        "schema_version": "msae_v3_gen7_scenario_action_observation_v1",
        "scenario_id": scenario, "boundary_event_sha256": boundary_sha256,
        "action_event_sha256": action_sha256, "initiator": row[2],
        "trigger": row[3], "target_identity": target,
        "pre_action_processes": pre_exit_subject["captured_processes"],
        "action": row[4],
        "post_action_processes": pre_exit_subject["captured_processes"],
        "term_escalation": None,
    }
    expected_sha256 = hashlib.sha256(_canonical_bytes(projection)).hexdigest()
    if (ledger_value.get("target_identity") != target
            or ledger_value.get("scenario_action_observation_sha256") !=
               expected_sha256):
        raise RuntimeError("scenario action projection/owner digest drift")
    return projection


def _g7_event_process(value: dict[str, Any]) -> dict[str, Any]:
    return {
        "pid": value["pid"], "start_ticks": value["start_ticks"],
        "ppid": value["ppid"], "pgid": value["pgid"],
        "uid": os.getuid(), "gid": os.getgid(),
    }


def _g7_validate_monitor_frame(value: Any, *, frame_type: str,
                               sequence: int) -> None:
    if (not isinstance(value, dict)
            or set(value) != {"schema_version", "protocol_id", "generation",
                              "frame_type", "sequence", "prior_frame_sha256",
                              "payload"}
            or value.get("schema_version") != "msae_v3_gen7_monitor_frame_v1"
            or value.get("frame_type") != frame_type
            or value.get("sequence") != sequence
            or not isinstance(value.get("payload"), dict)):
        raise RuntimeError("scenario monitor-frame evidence drift")


def _g7_validate_action_observation(value: dict[str, Any],
                                    scenario: str) -> None:
    observation = value["payload"].get("observation")
    if not isinstance(observation, dict):
        raise RuntimeError("scenario action observation is not an object")
    if scenario in {"S06_duplicate_frame", "S07_late_frame"}:
        keys = {"schema_version", "original_frame", "current_prior_frame",
                "rejected_frame", "violation_code", "expected_sequence",
                "expected_prior_sha256", "peer_process"}
        expected = (("MONITOR_RECORD_COMMITTED", 2, "MONITOR_RECORD_ACK", 3,
                     "duplicate_sequence", 4)
                    if scenario == "S06_duplicate_frame" else
                    ("START_SERVER", 4, "SERVER_READY", 5,
                     "stale_sequence_prior", 6))
        if (set(observation) != keys
                or observation.get("schema_version") !=
                   "msae_v3_gen7_monitor_frame_rejection_v1"
                or observation.get("violation_code") != expected[4]
                or observation.get("expected_sequence") != expected[5]
                or observation.get("original_frame") !=
                   observation.get("rejected_frame")):
            raise RuntimeError("scenario rejected-frame observation drift")
        _g7_validate_monitor_frame(
            observation["original_frame"], frame_type=expected[0],
            sequence=expected[1])
        _g7_validate_monitor_frame(
            observation["current_prior_frame"], frame_type=expected[2],
            sequence=expected[3])
        if (observation.get("expected_prior_sha256") != hashlib.sha256(
                _canonical_bytes(observation["current_prior_frame"])).hexdigest()
                or not isinstance(observation.get("peer_process"), dict)):
            raise RuntimeError("scenario rejected-frame prior/peer drift")
    elif scenario == "S09_child_timeout":
        keys = {"schema_version", "expected_frame_type", "expected_sequence",
                "current_prior_frame", "channel_peer",
                "wait_started_monotonic_ns", "deadline_monotonic_ns",
                "observation_monotonic_ns", "poll_result",
                "received_bytes_count"}
        if (set(observation) != keys
                or observation.get("schema_version") !=
                   "msae_v3_gen7_monitor_frame_receive_timeout_v1"
                or observation.get("expected_frame_type") != "SERVER_READY"
                or observation.get("expected_sequence") != 5
                or observation.get("poll_result") != "timeout"
                or observation.get("received_bytes_count") != 0
                or not isinstance(observation.get("channel_peer"), dict)
                or type(observation.get("wait_started_monotonic_ns")) is not int
                or type(observation.get("deadline_monotonic_ns")) is not int
                or type(observation.get("observation_monotonic_ns")) is not int
                or not (observation["wait_started_monotonic_ns"] <=
                        observation["deadline_monotonic_ns"] <=
                        observation["observation_monotonic_ns"])):
            raise RuntimeError("scenario timeout observation drift")
        _g7_validate_monitor_frame(
            observation["current_prior_frame"], frame_type="START_SERVER",
            sequence=4)
    else:
        raise RuntimeError("action observation for an unregistered scenario")


def _g7_validate_fault_event_variant(value: dict[str, Any],
                                     case: tuple[Any, ...]) -> None:
    common = {"schema_version", "event_type", "test_token", "case_id",
              "reporter_role", "reporter_kind", "pid", "start_ticks",
              "ppid", "pgid", "payload"}
    if set(value) != common or not isinstance(value.get("payload"), dict):
        raise RuntimeError("fault event common schema drift")
    event_type = value["event_type"]
    payload = value["payload"]
    process = _g7_event_process(value)
    if event_type == "OWNER_LEDGER_READY":
        if (set(payload) != {"ledger_path", "ledger_sha256",
                            "pre_exit_absence_sha256",
                            "expected_outer_final_descriptor_sha256"}
                or not all(_lower_sha256(payload.get(key)) for key in (
                    "ledger_sha256", "pre_exit_absence_sha256",
                    "expected_outer_final_descriptor_sha256"))
                or not isinstance(payload.get("ledger_path"), str)):
            raise RuntimeError("owner-ledger event schema drift")
        return
    if len(case) == 3:
        row = next(item for item in G7_HOOKS if item[0] == case[0])
        expected_role = ("monitor" if row[2] == "server_child" else
                         "pane_supervisor" if row[2] in {
                             "fake_broker_child", "fake_worker_child"}
                         else row[2])
        if (event_type != "HOOK_REACHED"
                or set(payload) != {"case_index", "hook_id", "injection_kind"}
                or payload != {"case_index": row[0], "hook_id": row[1],
                               "injection_kind": case[2]}
                or value.get("reporter_role") != expected_role
                or value.get("reporter_kind") != row[2]):
            raise RuntimeError("hook fault event table/schema drift")
        return
    scenario = str(case[0])
    row = next(item for item in G7_SCENARIO_ROWS if item[0] == scenario)
    reporters = {
        "S01_monitor_death": ("monitor", "monitor"),
        "S02_server_death": ("monitor", "monitor"),
        "S03_pane_death": ("pane_supervisor", "pane_supervisor"),
        "S04_broker_death": ("fake_broker", "fake_broker"),
        "S05_worker_death": ("fake_worker", "fake_worker"),
        "S06_duplicate_frame": ("launcher", "launcher"),
        "S07_late_frame": ("launcher", "launcher"),
        "S08_monitor_death_after_launcher_eof": ("monitor", "monitor"),
        "S09_child_timeout": ("launcher", "launcher"),
        "S10_term_resistant_descendant": ("fake_worker", "fake_worker"),
        "S11_kill_escalation": ("fake_broker", "fake_broker"),
        "S12_final_absence_probe": ("monitor", "monitor"),
    }
    if event_type == "SCENARIO_BOUNDARY_REACHED":
        if (set(payload) != {"scenario_id", "boundary_id", "reporter_process"}
                or payload.get("scenario_id") != scenario
                or payload.get("boundary_id") != row[1]
                or payload.get("reporter_process") != process
                or (value.get("reporter_role"), value.get("reporter_kind")) !=
                   reporters[scenario]):
            raise RuntimeError("scenario boundary event table/schema drift")
    elif event_type == "SCENARIO_ACTION_OBSERVED":
        expected_observer = (("launcher", "launcher") if scenario ==
                             "S09_child_timeout" else ("monitor", "monitor"))
        if (scenario not in {"S06_duplicate_frame", "S07_late_frame",
                             "S09_child_timeout"}
                or set(payload) != {"scenario_id", "boundary_event_sha256",
                                    "action_enum", "observer_role",
                                    "observer_process", "observation"}
                or payload.get("scenario_id") != scenario
                or payload.get("action_enum") != row[4]
                or payload.get("observer_role") != expected_observer[0]
                or payload.get("observer_process") != process
                or (value.get("reporter_role"), value.get("reporter_kind")) !=
                   expected_observer
                or not _lower_sha256(payload.get("boundary_event_sha256"))):
            raise RuntimeError("scenario action event table/schema drift")
        _g7_validate_action_observation(value, scenario)
    else:
        raise RuntimeError("unknown scenario fault event variant")


def _g7_fault_event(sock: socket.socket, token: str, case: tuple[Any, ...],
                    captured: dict[int, dict[str, Any]]) -> tuple[dict[str, Any], str]:
    case_id = str(case[1] if len(case) == 3 else case[0])
    raw, ancillary, flags, _ = sock.recvmsg(4096, socket.CMSG_SPACE(struct.calcsize("3i")))
    if not raw or flags & (socket.MSG_TRUNC | socket.MSG_CTRUNC):
        raise RuntimeError("fault event truncation/EOF")
    credentials = [struct.unpack("3i", item[2]) for item in ancillary
                   if item[0] == socket.SOL_SOCKET and item[1] == socket.SCM_CREDENTIALS]
    value = json.loads(raw)
    if raw != _canonical_bytes(value) or len(credentials) != 1:
        raise RuntimeError("fault event canonical/credential drift")
    pid, uid, gid = credentials[0]
    if pid not in captured:
        # A child may emit its pre-arm boundary immediately after fork.  The
        # credentialed datagram leaves it SIGSTOPed, so rescan the validated
        # launcher ancestry before deciding that the sender is unknown.
        _g7_capture(set(captured), captured)
    live_row = _proc_row(pid)
    if (value.get("schema_version") != "msae_v3_gen7_fault_event_v1"
            or value.get("test_token") != token or value.get("case_id") != case_id
            or value.get("pid") != pid or uid != os.getuid() or gid != os.getgid()
            or pid not in captured
            or str(value.get("start_ticks")) != str(captured[pid]["start_ticks"])
            or live_row is None
            or value.get("ppid") != live_row.get("ppid")
            or value.get("pgid") != live_row.get("pgrp")
            or live_row.get("uid") != uid
            or live_row.get("gid") != gid):
        raise RuntimeError(
            "fault event identity/case drift: "
            f"expected_case={case_id!r} credential={(pid, uid, gid)!r} "
            f"value={value!r} captured={captured.get(pid)!r}")
    _g7_validate_fault_event_variant(value, case)
    return value, hashlib.sha256(raw).hexdigest()


def _g7_tmux_server(captured: dict[int, dict[str, Any]]) -> dict[str, Any]:
    candidates = []
    for pid, row in captured.items():
        try:
            command = Path(f"/proc/{pid}/cmdline").read_bytes().split(b"\0")
            executable = os.readlink(f"/proc/{pid}/exe")
        except (FileNotFoundError, ProcessLookupError, PermissionError):
            continue
        if executable == "/usr/bin/tmux" and b"-D" in command:
            candidates.append(row)
    if len(candidates) != 1:
        raise RuntimeError(f"expected one foreground tmux server: {candidates}")
    return candidates[0]


def _g7_act(event: dict[str, Any], case: tuple[Any, ...],
            captured: dict[int, dict[str, Any]]) -> None:
    pid = int(event["pid"])
    event_type = event["event_type"]
    if event_type == "HOOK_REACHED":
        if case[-1] == "crash":
            os.kill(pid, signal.SIGKILL)
        else:
            os.kill(pid, signal.SIGCONT)
        return
    if event_type != "SCENARIO_BOUNDARY_REACHED":
        return
    scenario = str(case[0])
    if scenario in {"S01_monitor_death", "S08_monitor_death_after_launcher_eof",
                    "S04_broker_death", "S05_worker_death"}:
        os.kill(pid, signal.SIGKILL)
    elif scenario == "S02_server_death":
        os.kill(pid, signal.SIGCONT)
        server = _g7_tmux_server(captured)
        os.killpg(int(server["pgrp"]), signal.SIGKILL)
    elif scenario == "S03_pane_death":
        os.killpg(int(event["pgid"]), signal.SIGKILL)
    elif scenario in {"S06_duplicate_frame", "S07_late_frame",
                      "S09_child_timeout", "S11_kill_escalation",
                      "S12_final_absence_probe"}:
        os.kill(pid, signal.SIGCONT)
    elif scenario == "S10_term_resistant_descendant":
        os.kill(pid, signal.SIGCONT)
        pane = next((row for row in captured.values()
                     if int(row["pid"]) != pid and int(row["ppid"]) in captured
                     and b"pane_supervisor" in Path(
                         f"/proc/{int(row['pid'])}/cmdline").read_bytes()), None)
        if pane is None:
            raise RuntimeError("S10 pane identity not captured")
        os.kill(int(pane["pid"]), signal.SIGUSR1)
    else:
        raise RuntimeError(f"unknown scenario action: {scenario}")


def _g7_family_entries() -> dict[str, list[str]]:
    prefixes = ("m7t_", "m7b_", "m7p_", "m7x_", "m7a_", "m7c_", "m7s_")
    result = {prefix: [] for prefix in prefixes}
    for name in os.listdir("/tmp"):
        for prefix in prefixes:
            if name.startswith(prefix):
                result[prefix].append(name)
    for names in result.values():
        names.sort()
    return result


def _g7_final_has_session_probe(tmux_path: Path) -> int:
    vector = ["/usr/bin/tmux", "-f", "/dev/null", "-S", str(tmux_path),
              "has-session", "-t", "msae-independent-v3-gen7-containment"]
    process = subprocess.Popen(
        vector, env={"PATH": "/usr/bin:/bin", "HOME": "/thayerfs/home/f004ndc",
                     "LANG": "C.UTF-8", "LC_ALL": "C.UTF-8"},
        stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL, close_fds=True, start_new_session=True)
    pid = process.pid
    try:
        process.wait(timeout=1)
    except subprocess.TimeoutExpired:
        with contextlib.suppress(ProcessLookupError):
            os.killpg(pid, signal.SIGTERM)
        try:
            process.wait(timeout=1)
        except subprocess.TimeoutExpired:
            with contextlib.suppress(ProcessLookupError):
                os.killpg(pid, signal.SIGKILL)
            process.wait(timeout=1)
        raise RuntimeError("final tmux has-session probe timed out")
    if process.returncode == 0 or _group_members(pid) or _path_present(tmux_path):
        raise RuntimeError("final tmux session/socket probe did not prove absence")
    return int(process.returncode)


def _g7_cases() -> list[tuple[Any, ...]]:
    return [
        (index, hook, kind)
        for index, hook, *_rest in G7_HOOKS
        for kind in ("crash", "exception")
    ] + [(value,) for value in G7_SCENARIOS]


def _g7_emergency_containment(
        child: subprocess.Popen[Any], captured: dict[int, dict[str, Any]],
        token: str) -> None:
    """Best-effort containment for a failing test; it can never make it pass."""
    groups = {int(row["pgrp"]) for row in captured.values()
              if type(row.get("pgrp")) is int and int(row["pgrp"]) > 1}
    groups.add(child.pid)
    groups.discard(os.getpgrp())
    for sig in (signal.SIGCONT, signal.SIGTERM, signal.SIGKILL):
        for pgid in sorted(groups):
            with contextlib.suppress(ProcessLookupError):
                os.killpg(pgid, sig)
        deadline = time.monotonic() + (0.2 if sig == signal.SIGCONT else 2.0)
        while time.monotonic() < deadline and any(_group_members(pgid)
                                                   for pgid in groups):
            time.sleep(0.01)
    with contextlib.suppress(BaseException):
        child.wait(timeout=2)
    # Only the exact token-derived test namespace may be retired here.  Any
    # type/owner/mode/link drift is left in place and the command is already a
    # failing result.
    for path in (Path(f"/tmp/m7x_{token}.sock"),
                 Path(f"/tmp/m7a_{token}.sock"),
                 Path(f"/tmp/m7c_{token}.sock")):
        if not _path_present(path):
            continue
        st = path.lstat()
        if (stat.S_ISSOCK(st.st_mode) and st.st_uid == os.getuid()
                and st.st_gid == os.getgid() and st.st_nlink == 1):
            path.unlink()
    scratch = Path(f"/tmp/m7s_{token}")
    if _path_present(scratch):
        before = scratch.lstat()
        if (stat.S_ISDIR(before.st_mode)
                and stat.S_IMODE(before.st_mode) == 0o700
                and before.st_uid == os.getuid()
                and before.st_gid == os.getgid()):
            directory_fd = os.open(
                scratch, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW |
                os.O_CLOEXEC)
            try:
                allowed = {
                    "monitor.json", "process.json", ".process.json.partial",
                    "monitor.log", "server.log", "lease.test", "pane_arm.json",
                    "terminal.claim.test", "technical_failure.test.json",
                }
                allowed.update(
                    f"case-{index:02d}-{hook}-{kind}.json"
                    for index, hook, *_rest in G7_HOOKS
                    for kind in ("crash", "exception"))
                allowed.update(f"scenario-{scenario}.json"
                               for scenario in G7_SCENARIOS)
                names = os.listdir(directory_fd)
                if set(names) <= allowed:
                    for name in names:
                        row = os.stat(name, dir_fd=directory_fd,
                                      follow_symlinks=False)
                        if (not stat.S_ISREG(row.st_mode)
                                or stat.S_IMODE(row.st_mode) != 0o600
                                or row.st_uid != os.getuid()
                                or row.st_gid != os.getgid()
                                or row.st_nlink not in {1, 2}):
                            break
                    else:
                        for name in names:
                            os.unlink(name, dir_fd=directory_fd)
                        os.fsync(directory_fd)
            finally:
                os.close(directory_fd)
            with contextlib.suppress(OSError):
                scratch.rmdir()


def main_gen7_matrix() -> int:
    expected_environment = {"PATH": "/usr/bin:/bin",
                            "HOME": "/thayerfs/home/f004ndc",
                            "LANG": "C.UTF-8", "LC_ALL": "C.UTF-8"}
    if (len(sys.argv) != 1 or Path(sys.argv[0]).resolve() != SELF
            or dict(os.environ) != expected_environment):
        print("invocation contract drift", file=sys.stderr)
        return 2
    libc = ctypes.CDLL(None, use_errno=True)
    if libc.prctl(36, 1, 0, 0, 0) != 0:  # PR_SET_CHILD_SUBREAPER
        return 1
    observed = ctypes.c_int()
    if libc.prctl(37, ctypes.byref(observed), 0, 0, 0) != 0 or observed.value != 1:
        return 1
    if any(_g7_family_entries().values()):
        return 1
    token = _g7_test_token()
    parent, child_endpoint = socket.socketpair(
        socket.AF_UNIX, socket.SOCK_SEQPACKET | socket.SOCK_CLOEXEC)
    child_fd = child_endpoint.fileno(); os.set_inheritable(child_fd, True)
    env = {"PATH": "/usr/bin:/bin", "HOME": "/thayerfs/home/f004ndc",
           "LANG": "C.UTF-8", "LC_ALL": "C.UTF-8",
           "PYTEST_DISABLE_PLUGIN_AUTOLOAD": "1",
           "MSAE_GEN7_TEST_CONTROL_FD": str(child_fd)}
    argv = [str(PYTHON), "-B", "-I", "-m", "pytest", "-q",
            "-p", "no:cacheprovider", G7_TEST_NODE]
    child = subprocess.Popen(argv, cwd=ROOT, env=env, pass_fds=(child_fd,),
                             close_fds=True, start_new_session=True,
                             stdin=subprocess.DEVNULL)
    child_endpoint.close()
    parent.settimeout(24)
    global_deadline = time.monotonic() + 4200
    success = True
    emergency_captured: dict[int, dict[str, Any]] = {}
    active_case: tuple[Any, ...] | None = None
    try:
        for case in _g7_cases():
            active_case = case
            if time.monotonic() >= global_deadline:
                raise TimeoutError("global gen7 tmux matrix deadline")
            case_id = str(case[1] if len(case) == 3 else case[0])
            frame1, prior = _g7_recv(parent, token, case_id, 1, None, "CASE_REQUEST")
            expected_payload = ({"case_index": case[0], "hook_id": case[1],
                                 "injection_kind": case[2], "scenario_id": None}
                                if len(case) == 3 else
                                {"case_index": None, "hook_id": None,
                                 "injection_kind": None, "scenario_id": case[0]})
            if frame1["payload"] != expected_payload:
                raise RuntimeError("CASE_REQUEST ordering/payload drift")
            event_reader, event_writer = socket.socketpair(
                socket.AF_UNIX, socket.SOCK_DGRAM | socket.SOCK_CLOEXEC)
            event_reader.setsockopt(socket.SOL_SOCKET, socket.SO_PASSCRED, 1)
            binding = _g7_fault_binding(
                event_reader.fileno(), event_writer.fileno(),
                supervisor_pid=os.getpid(), pytest_pid=child.pid, case_id=case_id)
            start = time.monotonic_ns(); helper = start + 8_000_000_000
            outer = start + 24_000_000_000
            frame2 = _g7_frame(token, case_id, 2, prior, "CASE_EVENT_CHANNEL", {
                "fault_event_binding": binding,
                "case_start_monotonic_ns": start,
                "helper_start_deadline_monotonic_ns": helper,
                "outer_case_deadline_monotonic_ns": outer})
            prior = _g7_send(parent, frame2, event_writer.fileno())
            event_writer.close()
            frame3, prior = _g7_recv(
                parent, token, case_id, 3, prior, "CASE_LAUNCHER_IDENTITY")
            launcher = dict(frame3["payload"])
            launcher_pid = int(launcher["pid"])
            if (int(launcher["ppid"]) != child.pid
                    or int(launcher["pgid"]) != launcher_pid):
                raise RuntimeError("per-case launcher lineage drift")
            frame4 = _g7_frame(token, case_id, 4, prior,
                               "CASE_LAUNCHER_AUTHORIZED", {
                                   "launcher_identity_sha256": hashlib.sha256(
                                       _canonical_bytes(launcher)).hexdigest()})
            prior = _g7_send(parent, frame4)
            selector = selectors.DefaultSelector()
            selector.register(parent, selectors.EVENT_READ, "control")
            selector.register(event_reader, selectors.EVENT_READ, "event")
            captured: dict[int, dict[str, Any]] = {launcher_pid: _proc_row(launcher_pid) or {}}
            capture_stop = threading.Event()
            def capture_loop() -> None:
                while not capture_stop.is_set():
                    _g7_capture({launcher_pid}, captured)
                    capture_stop.wait(0.002)
            capture_thread = threading.Thread(
                target=capture_loop, name="msae-gen7-outer-capture",
                daemon=True)
            capture_thread.start()
            emergency_captured = captured
            ledger_event: dict[str, Any] | None = None
            result: dict[str, Any] | None = None
            boundary_event: dict[str, Any] | None = None
            boundary_sha256: str | None = None
            action_events: list[tuple[dict[str, Any], str]] = []
            while result is None or ledger_event is None:
                remaining = (outer - time.monotonic_ns()) / 1e9
                if remaining <= 0:
                    raise TimeoutError(f"case deadline: {case_id}")
                for key, _mask in selector.select(min(0.02, remaining)):
                    if key.data == "event":
                        event, digest = _g7_fault_event(
                            event_reader, token, case, captured)
                        if event["event_type"] in {"HOOK_REACHED",
                                                  "SCENARIO_BOUNDARY_REACHED"}:
                            if boundary_event is not None:
                                raise RuntimeError("duplicate case boundary event")
                            boundary_event = event
                            boundary_sha256 = digest
                            _g7_capture({launcher_pid}, captured)
                            if (len(case) == 3 and int(case[0]) >= 12
                                    and event.get("reporter_role") == "monitor"):
                                capture_deadline = time.monotonic() + 0.25
                                while (not any(
                                        int(row.get("ppid", -1)) ==
                                        int(event["pid"])
                                        for row in captured.values())
                                       and time.monotonic() < capture_deadline):
                                    _g7_capture({launcher_pid}, captured)
                            _g7_act(event, case, captured)
                        elif event["event_type"] == "SCENARIO_ACTION_OBSERVED":
                            action_events.append((event, digest))
                        elif event["event_type"] == "OWNER_LEDGER_READY":
                            if ledger_event is not None:
                                raise RuntimeError("duplicate owner ledger event")
                            ledger_event = event
                        else:
                            raise RuntimeError("unknown fault event")
                    else:
                        frame5, prior = _g7_recv(
                            parent, token, case_id, 5, prior, "CASE_RESULT")
                        if result is not None:
                            raise RuntimeError("duplicate CASE_RESULT")
                        result = frame5["payload"]
            capture_stop.set(); capture_thread.join(timeout=1)
            if capture_thread.is_alive():
                raise RuntimeError("outer capture thread did not stop")
            _g7_capture({launcher_pid}, captured)
            selector.close(); event_reader.close()
            if (set(result) != {"launcher_returncode", "ledger_path",
                                "ledger_sha256", "outcome"}
                    or type(result["launcher_returncode"]) is not int
                    or result["outcome"] != "contained_expected_failure"
                    or not _lower_sha256(result["ledger_sha256"])
                    or set(ledger_event.get("payload", {})) != {
                        "ledger_path", "ledger_sha256",
                        "pre_exit_absence_sha256",
                        "expected_outer_final_descriptor_sha256"}):
                raise RuntimeError("CASE_RESULT/ledger-event schema drift")
            ledger = Path(str(result["ledger_path"]))
            if (boundary_event is None or boundary_sha256 is None
                    or str(ledger_event["payload"]["ledger_path"]) != str(ledger)
                    or _g7_sha_file(ledger) != result["ledger_sha256"]
                    or result["ledger_sha256"] !=
                       ledger_event["payload"]["ledger_sha256"]):
                raise RuntimeError("owner ledger event/result drift")
            ledger_raw = ledger.read_bytes()
            ledger_value = json.loads(ledger_raw)
            if ledger_raw != _canonical_bytes(ledger_value):
                raise RuntimeError("owner ledger is not canonical")
            if (ledger_event.get("reporter_role") !=
                    ledger_value.get("evidence_publisher")
                    or ledger_event["payload"].get(
                        "pre_exit_absence_sha256") !=
                       ledger_value.get("pre_exit_absence_sha256")
                    or ledger_event["payload"].get(
                        "expected_outer_final_descriptor_sha256") !=
                       ledger_value.get(
                           "expected_outer_final_descriptor_sha256")):
                raise RuntimeError(
                    "owner-ledger event did not bind the evidence publisher")
            _g7_validate_owner_ledger(
                ledger_value, case=case, token=token, ledger_path=ledger,
                boundary_event=boundary_event,
                boundary_sha256=boundary_sha256,
                action_events=action_events)
            pre_exit_subject = _g7_pre_exit_subject(
                case=case, token=token, launcher_pid=launcher_pid,
                captured=captured, publisher_event=ledger_event,
                ledger_value=ledger_value, ledger=ledger,
                has_session_returncode=1)
            reconstructed_pre_exit_sha256 = hashlib.sha256(
                _canonical_bytes(pre_exit_subject)).hexdigest()
            if (reconstructed_pre_exit_sha256 !=
                    ledger_value["pre_exit_absence_sha256"]
                    or reconstructed_pre_exit_sha256 !=
                       ledger_event["payload"]["pre_exit_absence_sha256"]):
                raise RuntimeError(
                    "outer pre-exit absence reconstruction drift: "
                    f"outer={reconstructed_pre_exit_sha256} "
                    f"owner={ledger_value['pre_exit_absence_sha256']}")
            if len(case) == 1:
                _g7_scenario_action_projection(
                    case=case, ledger_value=ledger_value,
                    boundary_event=boundary_event,
                    boundary_sha256=boundary_sha256,
                    action_events=action_events,
                    pre_exit_subject=pre_exit_subject,
                    helper_deadline_monotonic_ns=helper,
                    outer_deadline_monotonic_ns=outer)
            # Reap adopted descendants without signaling them.  Any survivor
            # means production cleanup failed and the passing path is invalid.
            settle = time.monotonic() + 2
            while time.monotonic() < settle:
                _g7_capture({launcher_pid}, captured)
                while True:
                    try:
                        waited, _status = os.waitpid(-1, os.WNOHANG)
                    except ChildProcessError:
                        waited = 0
                    if waited <= 0 or waited == child.pid:
                        break
                live = [pid for pid, row in captured.items()
                        if _pid_matches(pid, int(row.get("start_ticks", 0)))]
                if not live:
                    break
                time.sleep(0.01)
            live = [pid for pid, row in captured.items()
                    if _pid_matches(pid, int(row.get("start_ticks", 0)))]
            if live:
                raise RuntimeError(f"production cleanup left live descendants: {live}")
            raw = ledger.read_bytes()
            st = ledger.lstat()
            if (hashlib.sha256(raw).hexdigest() != result["ledger_sha256"]
                    or not stat.S_ISREG(st.st_mode) or stat.S_IMODE(st.st_mode) != 0o600
                    or st.st_uid != os.getuid() or st.st_gid != os.getgid()
                    or st.st_nlink != 1):
                raise RuntimeError("ledger identity/content drift")
            scratch = ledger.parent
            if sorted(os.listdir(scratch)) != [ledger.name]:
                raise RuntimeError("owner did not retire exact scratch evidence")
            captured_processes, process_groups = _g7_process_subjects(
                captured, launcher_pid=launcher_pid,
                publisher_event=ledger_event, publisher_live=False,
                require_extinct=True)
            expected_final_processes = [
                {**row, "live": False}
                for row in pre_exit_subject["captured_processes"]]
            expected_final_groups = [
                {"pgid": row["pgid"], "members": []}
                for row in pre_exit_subject["process_groups"]]
            if (captured_processes != expected_final_processes
                    or process_groups != expected_final_groups):
                raise RuntimeError(
                    "outer final process projection diverged from pre-exit")
            tmux_path = Path(f"/tmp/m7x_{token}.sock")
            broker_path = Path(f"/tmp/m7a_{token}.sock")
            pane_path = Path(f"/tmp/m7c_{token}.sock")
            if any(_path_present(path) for path in
                   (tmux_path, broker_path, pane_path)):
                raise RuntimeError("registered socket survived before final probe")
            has_session_returncode = _g7_final_has_session_probe(tmux_path)
            if has_session_returncode != pre_exit_subject["session"][
                    "has_session_returncode"]:
                raise RuntimeError("outer final session result drifted from pre-exit")
            if any(_path_present(path) for path in
                   (tmux_path, broker_path, pane_path)):
                raise RuntimeError("registered socket appeared during final probe")
            ledger.unlink(); os.rmdir(scratch)
            if any(_g7_family_entries().values()):
                raise RuntimeError("short namespace survived case")
            final_subject = {
                "schema_version": "msae_v3_gen7_test_outer_final_absence_v1",
                "test_token": token, "case_or_scenario_id":
                    (case[1] if len(case) == 3 else case[0]),
                "ledger_sha256": result["ledger_sha256"],
                "pre_exit_absence_sha256":
                    ledger_event["payload"]["pre_exit_absence_sha256"],
                "captured_processes": captured_processes,
                "process_groups": process_groups,
                "session": {"name": "msae-independent-v3-gen7-containment",
                            "has_session_returncode": has_session_returncode},
                "socket_paths": {str(path): {"lexists": False}
                                 for path in (tmux_path, broker_path, pane_path)},
                "short_family_entries": _g7_family_entries(),
                "lease": pre_exit_subject["lease"],
                "staging_entries": pre_exit_subject["staging_entries"],
                "scratch": {"path": str(scratch), "lexists": False},
                "tripwires": pre_exit_subject["tripwires"]}
            final_sha = hashlib.sha256(_canonical_bytes(final_subject)).hexdigest()
            frame6 = _g7_frame(token, case_id, 6, prior, "CASE_RELEASE", {
                "ledger_sha256": result["ledger_sha256"],
                "outer_final_extinction_sha256": final_sha})
            _g7_send(parent, frame6)
        returncode = child.wait(timeout=max(1, global_deadline - time.monotonic()))
        success = returncode == 0 and not any(_g7_family_entries().values())
    except BaseException as error:
        success = False
        print(f"gen7 tmux matrix failed: case={active_case!r}: {error}",
              file=sys.stderr)
        traceback.print_exc()
        scratch = Path(f"/tmp/m7s_{token}")
        if _path_present(scratch):
            with contextlib.suppress(BaseException):
                print(f"scratch children: {sorted(os.listdir(scratch))!r}",
                      file=sys.stderr)
        for name in ("monitor.log", "server.log"):
            path = scratch / name
            if _path_present(path):
                with contextlib.suppress(BaseException):
                    print(f"--- {name} ---", file=sys.stderr)
                    print(path.read_text(encoding="utf-8", errors="replace"),
                          file=sys.stderr)
        # Emergency containment is intentionally a failing outcome.  It is
        # allowed only to keep a broken test from leaking real processes.
        with contextlib.suppress(BaseException):
            _g7_emergency_containment(child, emergency_captured, token)
    finally:
        parent.close()
        if child.poll() is None:
            with contextlib.suppress(BaseException):
                _g7_emergency_containment(child, emergency_captured, token)
    return 0 if success else 1


if __name__ == "__main__":
    raise SystemExit(main_gen7_matrix())
