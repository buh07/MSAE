#!/usr/bin/env python3
"""Source-only supervisor for the single reviewed gen6 tmux extinction test.

This is a CPU/process-containment harness, not an experiment launcher.  It owns
all temporary names, the broker identity handshake, the pytest deadline, and
final process/session/path extinction.
"""
from __future__ import annotations

import json
import hashlib
import contextlib
import os
from pathlib import Path
import selectors
import signal
import socket
import stat
import struct
import subprocess
import sys
import time
from typing import Any

ROOT = Path("/jumbo/lisp/f004ndc/experiments/wip/MSAE")
PYTHON = ROOT / ".venv-atlas/bin/python"
TMUX = Path("/usr/bin/tmux")
SELF = ROOT / "scripts/run_msae_independent_measurement_v3_post_m2_gen6_tmux_test.py"
PROTOCOL_PREFIX = "msae-independent-v3-gen6-test"
ACK_TIMEOUT = 5.0
CHILD_TIMEOUT = 120.0
TERM_TIMEOUT = 3.0
FAULT_MODES = (
    "fork", "partial_write", "file_fsync", "publish", "identity", "ack",
    "barrier_release", "resistance_arm", "monitor_death", "pane_death",
)


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
    return {"pid": pid, "state": fields[0], "ppid": int(fields[1]),
            "pgrp": int(fields[2]), "start_ticks": int(fields[19])}


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


def _is_equal_or_descended(pid: int, ancestor: int) -> bool:
    current = pid
    seen: set[int] = set()
    while current > 1 and current not in seen:
        if current == ancestor:
            return True
        seen.add(current)
        row = _proc_row(current)
        if row is None:
            return False
        current = int(row["ppid"])
    return current == ancestor


def _terminate_pid(pid: int, ticks: int) -> None:
    if not _pid_matches(pid, ticks):
        return
    try:
        os.kill(pid, signal.SIGTERM)
    except ProcessLookupError:
        return
    deadline = time.monotonic() + TERM_TIMEOUT
    while time.monotonic() < deadline and _pid_matches(pid, ticks):
        time.sleep(0.02)
    if _pid_matches(pid, ticks):
        try:
            os.kill(pid, signal.SIGKILL)
        except ProcessLookupError:
            pass


def _terminate_group(pgid: int) -> None:
    members = _group_members(pgid)
    if not members:
        return
    try:
        os.killpg(pgid, signal.SIGTERM)
    except ProcessLookupError:
        return
    deadline = time.monotonic() + TERM_TIMEOUT
    while time.monotonic() < deadline and _group_members(pgid):
        time.sleep(0.02)
    if _group_members(pgid):
        try:
            os.killpg(pgid, signal.SIGKILL)
        except ProcessLookupError:
            pass
    deadline = time.monotonic() + TERM_TIMEOUT
    while time.monotonic() < deadline and _group_members(pgid):
        time.sleep(0.02)


def _tmux(socket_path: Path, *tail: str, check: bool = False) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [str(TMUX), "-f", "/dev/null", "-S", str(socket_path), *tail],
        stdin=subprocess.DEVNULL, text=True, capture_output=True, timeout=3,
        env={"PATH": "/usr/bin:/bin", "HOME": "/thayerfs/home/f004ndc",
             "LANG": "C.UTF-8", "LC_ALL": "C.UTF-8"}, check=check)


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
            "msae_v3_gen6_tmux_test_process_v1":
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
            "schema_version": "msae_v3_gen6_tmux_test_terminal_claim_v1",
            "owner": owner, "pane_pid": pane_pid}),
        ("technical_failure.test.json", {
            "schema_version": "msae_v3_gen6_tmux_test_technical_failure_v1",
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
            "schema_version": "msae_v3_gen6_tmux_test_terminal_claim_v1",
            "owner": owner, "pane_pid": pane_pid},
        "technical_failure.test.json": {
            "schema_version": "msae_v3_gen6_tmux_test_technical_failure_v1",
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
                    "msae_v3_gen6_tmux_test_process_v1"
                and all(type(value[key]) is int and value[key] > 0
                        for key in expected - {"schema_version"}))
    if final_name == "identity_bound.json":
        return (set(value) == {"schema_version", "process_sha256", "supervisor_pid"}
                and value.get("schema_version") ==
                    "msae_v3_gen6_tmux_test_identity_bound_v1"
                and isinstance(value.get("process_sha256"), str)
                and len(value["process_sha256"]) == 64
                and all(character in "0123456789abcdef"
                        for character in value["process_sha256"])
                and type(value.get("supervisor_pid")) is int
                and value["supervisor_pid"] > 0)
    if final_name == "terminal.claim.test":
        return (set(value) == {"schema_version", "owner", "pane_pid"}
                and value.get("schema_version") ==
                    "msae_v3_gen6_tmux_test_terminal_claim_v1"
                and value.get("owner") in {"pane_supervisor", "monitor"}
                and type(value.get("pane_pid")) is int
                and value["pane_pid"] > 1)
    if final_name == "technical_failure.test.json":
        return (set(value) == {"schema_version", "reason", "pane_pid"}
                and value.get("schema_version") ==
                    "msae_v3_gen6_tmux_test_technical_failure_v1"
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


def _socket_identity(path: Path, *, expected_mode: int = 0o700
                     ) -> tuple[int, int, int, int, int]:
    observed = path.lstat()
    if (not stat.S_ISSOCK(observed.st_mode) or stat.S_ISLNK(observed.st_mode)
            or observed.st_uid != os.getuid() or observed.st_gid != os.getgid()
            or stat.S_IMODE(observed.st_mode) != expected_mode
            or observed.st_nlink != 1):
        raise RuntimeError(f"tmux test socket identity drift: {path}")
    return (observed.st_dev, observed.st_ino, observed.st_mode,
            observed.st_uid, observed.st_nlink)


def _promote_tmux_socket_mode(path: Path) -> tuple[int, int, int, int, int]:
    """Promote tmux's owner-only 0600 socket to the frozen 0700 contract."""
    if (path.parent != Path("/tmp")
            or not path.name.startswith(f"{PROTOCOL_PREFIX}-")
            or not path.name.endswith(".tmux.sock")):
        raise RuntimeError("unregistered tmux-test socket promotion path")
    parent_fd = os.open(
        "/tmp", os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC)
    try:
        parent = os.fstat(parent_fd); parent_path = Path("/tmp").lstat()
        if ((parent.st_dev, parent.st_ino) !=
                (parent_path.st_dev, parent_path.st_ino)
                or parent.st_uid != 0
                or stat.S_IMODE(parent.st_mode) != 0o1777):
            raise RuntimeError("tmux-test /tmp identity drift")
        before = os.stat(path.name, dir_fd=parent_fd, follow_symlinks=False)
        if (not stat.S_ISSOCK(before.st_mode) or before.st_uid != os.getuid()
                or before.st_gid != os.getgid() or before.st_nlink != 1
                or stat.S_IMODE(before.st_mode) not in {0o600, 0o700}):
            raise RuntimeError("tmux-test socket is not owned promotable state")
        if stat.S_IMODE(before.st_mode) == 0o600:
            os.chmod(path.name, 0o700, dir_fd=parent_fd, follow_symlinks=False)
            os.fsync(parent_fd)
        after = os.stat(path.name, dir_fd=parent_fd, follow_symlinks=False)
        if ((before.st_dev, before.st_ino, before.st_uid, before.st_gid,
             before.st_nlink) !=
                (after.st_dev, after.st_ino, after.st_uid, after.st_gid,
                 after.st_nlink)
                or stat.S_IMODE(after.st_mode) != 0o700):
            raise RuntimeError("tmux-test socket changed during promotion")
    finally:
        os.close(parent_fd)
    return _socket_identity(path)


def _tmux_process_identity(socket_path: Path, session: str) -> tuple[int, int, int, int] | None:
    shown = _tmux(socket_path, "display-message", "-p", "-t", session,
                  "#{pid} #{pane_pid}")
    fields = shown.stdout.strip().split()
    if shown.returncode != 0 or len(fields) != 2 or not all(
            field.isdecimal() for field in fields):
        return None
    server_pid, pane_pid = map(int, fields)
    server_row = _proc_row(server_pid); pane_row = _proc_row(pane_pid)
    if server_row is None or pane_row is None:
        return None
    return (server_pid, int(server_row["start_ticks"]),
            pane_pid, int(pane_row["start_ticks"]))


def _captured_descendants(ancestor_pid: int) -> list[tuple[int, int]]:
    captured: list[tuple[int, int]] = []
    for entry in Path("/proc").iterdir():
        if not entry.name.isdecimal():
            continue
        pid = int(entry.name)
        if pid == ancestor_pid:
            continue
        row = _proc_row(pid)
        if (row is not None and row["state"] != "Z"
                and _is_equal_or_descended(pid, ancestor_pid)):
            captured.append((pid, int(row["start_ticks"])))
    return sorted(set(captured))


def _remove_bound_tmux_socket(path: Path,
                              expected: tuple[int, int, int, int, int]) -> None:
    if not _path_present(path):
        return
    before = _socket_identity(path)
    if before != expected:
        raise RuntimeError("tmux fault-case socket substitution")
    probe = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    probe.settimeout(0.2)
    try:
        try:
            probe.connect(str(path))
        except (ConnectionRefusedError, FileNotFoundError):
            pass
        else:
            raise RuntimeError("tmux fault-case socket still has a listener")
    finally:
        probe.close()
    if _socket_identity(path) != expected:
        raise RuntimeError("tmux fault-case socket changed during cleanup")
    path.unlink()


def _cleanup_fault_case(
    *, socket_path: Path, session: str, scratch: Path,
    socket_identity: tuple[int, int, int, int, int] | None,
    server_identity: tuple[int, int] | None,
    pane_identity: tuple[int, int] | None,
    captured: list[tuple[int, int]], identity: dict[str, Any] | None,
) -> None:
    """Run every independent cleanup action, then require exact extinction."""
    errors: list[str] = []

    def attempt(label: str, action: Any) -> None:
        try:
            action()
        except BaseException as exc:
            errors.append(f"{label}:{type(exc).__name__}:{exc}")

    if identity is not None:
        attempt("worker-group", lambda: _terminate_group(
            int(identity["worker_pgid"])))
    trusted = list(captured)
    if pane_identity is not None:
        trusted.append(pane_identity)
    if identity is not None:
        trusted.extend([
            (int(identity["worker_pid"]),
             int(identity["worker_start_ticks"])),
            (int(identity["broker_pid"]),
             int(identity["broker_start_ticks"])),
        ])
    for pid, ticks in reversed(list(dict.fromkeys(trusted))):
        attempt(f"pid-{pid}", lambda pid=pid, ticks=ticks:
                _terminate_pid(pid, ticks))

    for tail in (("kill-session", "-t", session), ("kill-server",)):
        def command(tail: tuple[str, ...] = tail) -> None:
            if not _path_present(socket_path):
                return
            if (socket_identity is None
                    or _socket_identity(socket_path) != socket_identity):
                raise RuntimeError("tmux fault-case socket changed before command")
            _tmux(socket_path, *tail)
        attempt("tmux-" + tail[0], command)

    if server_identity is not None:
        attempt(f"server-{server_identity[0]}", lambda:
                _terminate_pid(server_identity[0], server_identity[1]))
        trusted.append(server_identity)

    for partial_name, final_name in (
            (".process.json.partial", "process.json"),
            (".identity_bound.json.partial", "identity_bound.json"),
            (".terminal.claim.test.partial", "terminal.claim.test"),
            (".technical_failure.test.json.partial",
             "technical_failure.test.json")):
        def remove_pair(partial_name: str = partial_name,
                        final_name: str = final_name) -> None:
            if not _path_present(scratch):
                return
            if not _cleanup_owned_regular_pair(
                    scratch, partial_name, final_name):
                raise RuntimeError(f"unsafe fault-case pair: {final_name}")
        attempt("pair-" + final_name, remove_pair)

    if socket_identity is not None:
        attempt("socket-unlink", lambda: _remove_bound_tmux_socket(
            socket_path, socket_identity))
    elif _path_present(socket_path):
        errors.append("unbound-socket-path-present")
    if (not _path_present(socket_path)
            or (socket_identity is not None
                and _socket_identity(socket_path) == socket_identity)):
        final_session = _tmux(socket_path, "has-session", "-t", session)
        if final_session.returncode == 0:
            errors.append("final-has-session:session-still-live")
    if _path_present(socket_path):
        errors.append("socket-path-present")
    for path in (scratch / ".process.json.partial", scratch / "process.json",
                 scratch / ".identity_bound.json.partial",
                 scratch / "identity_bound.json",
                 scratch / ".terminal.claim.test.partial",
                 scratch / "terminal.claim.test",
                 scratch / ".technical_failure.test.json.partial",
                 scratch / "technical_failure.test.json"):
        if _path_present(path):
            errors.append(f"scratch-entry-present:{path.name}")
    if identity is not None and _group_members(int(identity["worker_pgid"])):
        errors.append("worker-group-present")
    for pid, ticks in dict.fromkeys(trusted):
        if _pid_matches(pid, ticks):
            errors.append(f"pid-present:{pid}")
    if errors:
        raise RuntimeError("tmux injected-case cleanup failed: " + ";".join(errors))


def _supervise_fault_case(
    mode: str, *, listener: socket.socket, child: subprocess.Popen[bytes],
    socket_path: Path, session: str, scratch: Path,
    global_deadline: float, shutdown_requested: Any,
    selector: selectors.BaseSelector,
) -> None:
    """Drive one real tmux/fake-broker stop with this supervisor as authority."""
    if mode not in FAULT_MODES:
        raise RuntimeError("unregistered tmux fault case")
    deadline = min(time.monotonic() + 6.0, global_deadline)
    socket_identity: tuple[int, int, int, int, int] | None = None
    captured_tmux: tuple[int, int, int, int] | None = None
    connection: socket.socket | None = None
    captured: list[tuple[int, int]] = []
    identity: dict[str, Any] | None = None
    foreground_server: subprocess.Popen[bytes] | None = None
    server_process: subprocess.Popen[bytes] | None = None
    listener.setblocking(False)
    try:
        previous_umask = os.umask(0o077)
        try:
            server_process = subprocess.Popen(
                [str(TMUX), "-D", "-f", "/dev/null", "-S", str(socket_path)],
                stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL, env={
                    "PATH": "/usr/bin:/bin", "HOME": "/thayerfs/home/f004ndc",
                    "LANG": "C.UTF-8", "LC_ALL": "C.UTF-8"},
                start_new_session=True, close_fds=True)
        finally:
            os.umask(previous_umask)
        server_row = _proc_row(server_process.pid)
        if (server_row is None or int(server_row["pgrp"]) != server_process.pid):
            raise RuntimeError(f"foreground tmux server identity drift for {mode}")
        server_identity_direct = (
            server_process.pid, int(server_row["start_ticks"]))
        socket_deadline = min(time.monotonic() + 3.0, deadline)
        while not _path_present(socket_path):
            if server_process.poll() is not None:
                raise RuntimeError(f"foreground tmux server exited before socket for {mode}")
            if time.monotonic() >= socket_deadline:
                raise TimeoutError(f"foreground tmux socket timeout for {mode}")
            time.sleep(0.01)
        socket_identity = _promote_tmux_socket_mode(socket_path)
        while time.monotonic() < deadline:
            if shutdown_requested():
                raise RuntimeError("tmux supervisor shutdown during fault matrix")
            if child.poll() is not None:
                raise RuntimeError(f"pytest child exited during {mode}")
            if _path_present(socket_path):
                if socket_identity is None:
                    socket_identity = _socket_identity(socket_path)
                if captured_tmux is None:
                    captured_tmux = _tmux_process_identity(socket_path, session)
                if captured_tmux is not None:
                    captured.extend(_captured_descendants(captured_tmux[2]))
            for key, _mask in selector.select(timeout=0.01):
                if key.data == "listener":
                    connection, _ = listener.accept()
                    break
                if key.data == "shutdown":
                    # The signal handler owns the flag; draining the pipe only
                    # keeps this one selector-driven lifecycle responsive.
                    with contextlib.suppress(BlockingIOError):
                        os.read(int(key.fileobj), 4096)
            if connection is not None:
                break
            if (mode in {"fork", "partial_write", "file_fsync", "publish"}
                    and captured_tmux is not None
                    and not _pid_matches(captured_tmux[2], captured_tmux[3])):
                break
        if socket_identity is None or captured_tmux is None:
            diagnostic = _tmux(
                socket_path, "display-message", "-p", "-t", session,
                "#{pid} #{pane_pid}")
            raise RuntimeError(
                f"tmux identity not captured for {mode}: "
                f"returncode={diagnostic.returncode},stdout={diagnostic.stdout!r},"
                f"stderr={diagnostic.stderr!r},server_returncode="
                f"{server_process.poll() if server_process is not None else None}")
        server_pid, server_ticks, pane_pid, pane_ticks = captured_tmux
        if (server_pid, server_ticks) != server_identity_direct:
            raise RuntimeError(f"foreground tmux server/display identity drift for {mode}")
        captured.extend(_captured_descendants(pane_pid))
        process_path = scratch / "process.json"
        partial_path = scratch / ".process.json.partial"
        if mode in {"fork", "partial_write", "file_fsync", "publish"}:
            expected = {
                "fork": (False, False),
                "partial_write": (True, False),
                "file_fsync": (True, False),
                "publish": (True, True),
            }[mode]
            until = time.monotonic() + 1.0
            while time.monotonic() < until:
                state = (_path_present(partial_path), _path_present(process_path))
                if state == expected:
                    break
                time.sleep(0.01)
            if (_path_present(partial_path), _path_present(process_path)) != expected:
                raise RuntimeError(f"tmux {mode} did not reach its registered boundary")
            if connection is not None:
                raise RuntimeError(f"tmux {mode} unexpectedly connected")
            if not captured:
                raise RuntimeError(f"tmux {mode} descendant identity was not captured")
        else:
            if connection is None:
                raise RuntimeError(f"tmux {mode} did not connect")
            connection.settimeout(2)
            credentials = struct.unpack(
                "3i", connection.getsockopt(
                    socket.SOL_SOCKET, socket.SO_PEERCRED,
                    struct.calcsize("3i")))
            raw = b""
            while not raw.endswith(b"\n"):
                chunk = connection.recv(16384 - len(raw))
                if not chunk:
                    raise RuntimeError(f"tmux {mode} identity frame ended early")
                raw += chunk
            sent = json.loads(raw.decode("utf-8"))
            durable = _read_identity(process_path)
            if (durable is None or raw != _canonical_bytes(sent)
                    or sent != durable):
                raise RuntimeError(f"tmux {mode} durable identity mismatch")
            identity = _validate_identity(durable, pane_pid, credentials)
            captured.extend(_captured_descendants(pane_pid))
            if mode == "identity":
                if connection.recv(1) != b"":
                    raise RuntimeError("identity boundary did not close")
            else:
                connection.sendall(b"I")
                if mode in {"ack", "barrier_release", "resistance_arm"}:
                    expected = {"ack": b"1", "barrier_release": b"2",
                                "resistance_arm": b"3"}[mode]
                    if connection.recv(1) != expected:
                        raise RuntimeError(f"tmux {mode} boundary ACK drift")
                else:
                    if connection.recv(1) != b"A":
                        raise RuntimeError("tmux resistance ACK drift")
                    _publish_identity_bound(scratch / "identity_bound.json", {
                        "schema_version": "msae_v3_gen6_tmux_test_identity_bound_v1",
                        "process_sha256": hashlib.sha256(
                            _canonical_bytes(durable)).hexdigest(),
                        "supervisor_pid": os.getpid(),
                    })
                    connection.sendall(b"B")
                    if mode == "monitor_death":
                        # The independently captured foreground-server parent
                        # is the test monitor's child authority.  Its death
                        # delivers HUP to the deliberately non-PDEATH pane,
                        # which must clean its broker/worker and terminalize.
                        _terminate_pid(server_pid, server_ticks)
                        terminal_deadline = time.monotonic() + 3
                        while (not (scratch / "terminal.claim.test").is_file()
                               or not (scratch / "technical_failure.test.json").is_file()):
                            if time.monotonic() >= terminal_deadline:
                                raise TimeoutError(
                                    "pane supervisor did not terminalize server death")
                            time.sleep(0.02)
                        _validate_test_terminal(
                            scratch, owner="pane_supervisor",
                            reason="monitor_or_server_death", pane_pid=pane_pid)
                    elif mode == "pane_death":
                        if _pid_matches(pane_pid, pane_ticks):
                            with contextlib.suppress(ProcessLookupError):
                                os.kill(pane_pid, signal.SIGKILL)
                        pane_deadline = time.monotonic() + TERM_TIMEOUT
                        while (_pid_matches(pane_pid, pane_ticks)
                               and time.monotonic() < pane_deadline):
                            time.sleep(0.02)
                        if _pid_matches(pane_pid, pane_ticks):
                            raise RuntimeError("pane supervisor survived injected death")
                        _terminate_group(int(identity["worker_pgid"]))
                        _terminate_pid(int(identity["broker_pid"]),
                                       int(identity["broker_start_ticks"]))
                        _write_test_terminal(
                            scratch, owner="monitor",
                            reason="pane_supervisor_death", pane_pid=pane_pid)
                        _validate_test_terminal(
                            scratch, owner="monitor",
                            reason="pane_supervisor_death", pane_pid=pane_pid)
                    else:
                        time.sleep(0.1)
    finally:
        if connection is not None:
            connection.close()
        if socket_identity is None and _path_present(socket_path):
            socket_identity = _socket_identity(socket_path)
        if captured_tmux is None and socket_identity is not None:
            captured_tmux = _tmux_process_identity(socket_path, session)
        server_identity = ((captured_tmux[0], captured_tmux[1])
                           if captured_tmux is not None else
                           (server_process.pid, int(_proc_row(server_process.pid)["start_ticks"]))
                           if server_process is not None and _proc_row(server_process.pid) is not None
                           else None)
        pane_identity = ((captured_tmux[2], captured_tmux[3])
                         if captured_tmux is not None else None)
        try:
            _cleanup_fault_case(
                socket_path=socket_path, session=session, scratch=scratch,
                socket_identity=socket_identity,
                server_identity=server_identity, pane_identity=pane_identity,
                captured=list(dict.fromkeys(captured)), identity=identity)
        finally:
            if server_process is not None:
                if server_process.poll() is None:
                    _terminate_group(server_process.pid)
                with contextlib.suppress(subprocess.TimeoutExpired):
                    server_process.wait(timeout=TERM_TIMEOUT)


def _recycle_fault_namespace(
    listener: socket.socket, ack_socket: Path, scratch: Path,
    ack_identity: tuple[int, int, int, int, int],
) -> tuple[socket.socket, tuple[int, int, int, int, int]]:
    """Prove per-case ACK/scratch absence, then recreate the fixed namespace."""
    errors: list[str] = []
    try:
        listener.close()
    except BaseException as exc:
        errors.append(f"listener-close:{exc}")
    try:
        if (not _path_present(ack_socket)
                or _socket_identity(ack_socket, expected_mode=0o600) != ack_identity):
            raise RuntimeError("fault-case ACK socket identity drift")
        ack_socket.unlink()
    except BaseException as exc:
        errors.append(f"ack-unlink:{exc}")
    try:
        if any(os.scandir(scratch)):
            raise RuntimeError("fault-case scratch is not empty")
        scratch.rmdir()
    except BaseException as exc:
        errors.append(f"scratch-rmdir:{exc}")
    if any(_path_present(path) for path in (ack_socket, scratch)):
        errors.append("per-case namespace absence failed")
    if errors:
        raise RuntimeError("tmux fault namespace recycle failed: " + ";".join(errors))
    # Make the full absence observable to the sole pytest child before the
    # next case reuses the exact registered names.
    time.sleep(0.05)
    scratch.mkdir(mode=0o700); os.chmod(scratch, 0o700)
    replacement = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    replacement.bind(str(ack_socket)); os.chmod(ack_socket, 0o600)
    replacement.listen(1)
    return replacement, _socket_identity(ack_socket, expected_mode=0o600)


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


def _await_child_timeout_arm(
    *, selector: selectors.BaseSelector, listener: socket.socket,
    child: subprocess.Popen[bytes], deadline: float,
    shutdown_requested: Any,
) -> None:
    """Bind the exact pytest peer's one-byte request for the timeout boundary."""
    connection: socket.socket | None = None
    try:
        while connection is None:
            if shutdown_requested():
                raise RuntimeError("tmux supervisor shutdown before timeout arm")
            if child.poll() is not None:
                raise RuntimeError("pytest exited before timeout boundary")
            if time.monotonic() >= deadline:
                raise TimeoutError("pytest did not arm child-timeout boundary")
            for key, _mask in selector.select(
                    timeout=min(0.05, max(0.0, deadline - time.monotonic()))):
                if key.data == "shutdown":
                    with contextlib.suppress(BlockingIOError):
                        os.read(int(key.fileobj), 4096)
                elif key.data == "listener":
                    connection, _ = listener.accept()
        connection.settimeout(1)
        peer_pid, peer_uid, peer_gid = struct.unpack(
            "3i", connection.getsockopt(
                socket.SOL_SOCKET, socket.SO_PEERCRED,
                struct.calcsize("3i")))
        if (peer_pid != child.pid or peer_uid != os.getuid()
                or peer_gid != os.getgid()):
            raise RuntimeError("child-timeout arm peer drift")
        if connection.recv(2) != b"T" or connection.recv(1) != b"":
            raise RuntimeError("child-timeout arm frame drift")
    finally:
        if connection is not None:
            connection.close()


def _wait_for_registered_child_timeout(
    *, selector: selectors.BaseSelector, child: subprocess.Popen[bytes],
    deadline: float, shutdown_requested: Any,
) -> None:
    """Reach the real monotonic deadline without accepting later connections."""
    while time.monotonic() < deadline:
        if shutdown_requested():
            raise RuntimeError("tmux supervisor shutdown before child deadline")
        if child.poll() is not None:
            raise RuntimeError("pytest exited before registered child timeout")
        for key, _mask in selector.select(
                timeout=min(0.05, max(0.0, deadline - time.monotonic()))):
            if key.data == "shutdown":
                with contextlib.suppress(BlockingIOError):
                    os.read(int(key.fileobj), 4096)
            elif key.data == "listener":
                raise RuntimeError("duplicate connection before child timeout")


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


def main() -> int:
    if sys.flags.no_site != 1 or sys.flags.isolated != 1 or sys.flags.dont_write_bytecode != 1:
        raise RuntimeError("tmux test supervisor requires -S -I -B")
    expected_environment = {
        "PATH": "/usr/bin:/bin", "HOME": "/thayerfs/home/f004ndc",
        "LANG": "C.UTF-8", "LC_ALL": "C.UTF-8",
    }
    if (Path.cwd().resolve() != ROOT or Path(sys.executable).resolve() != PYTHON.resolve()
            or len(sys.argv) != 1 or Path(sys.argv[0]).resolve() != SELF
            or dict(os.environ) != expected_environment):
        raise RuntimeError("tmux test supervisor invocation contract drift")
    token = str(os.getpid())
    session = f"{PROTOCOL_PREFIX}-{token}"
    tmux_socket = Path(f"/tmp/{session}.tmux.sock")
    ack_socket = Path(f"/tmp/{session}.ack.sock")
    scratch = Path(f"/tmp/{session}.scratch")
    process_path = scratch / "process.json"
    bound_path = scratch / "identity_bound.json"
    for path in (tmux_socket, ack_socket, scratch):
        if _path_present(path):
            raise RuntimeError(f"tmux test namespace is not initially absent: {path}")

    shutdown_r, shutdown_w = os.pipe2(os.O_CLOEXEC | os.O_NONBLOCK)
    shutdown = False
    def request_shutdown(_signum: int, _frame: Any) -> None:
        nonlocal shutdown
        if shutdown:
            return
        shutdown = True
        try:
            os.write(shutdown_w, b"X")
        except OSError:
            pass
    for signum in (signal.SIGTERM, signal.SIGHUP, signal.SIGINT):
        signal.signal(signum, request_shutdown)

    listener: socket.socket | None = None
    selector: selectors.BaseSelector | None = None
    child: subprocess.Popen[bytes] | None = None
    pane_pid: int | None = None
    pane_ticks: int | None = None
    tmux_server_pid: int | None = None
    tmux_server_ticks: int | None = None
    tmux_socket_identity: tuple[int, int, int, int, int] | None = None
    ack_socket_identity: tuple[int, int, int, int, int] | None = None
    peer_pid: int | None = None
    identity: dict[str, Any] | None = None
    foreground_server: subprocess.Popen[bytes] | None = None
    success = False
    phase = "initialize"
    try:
        phase = "create-owned-namespace"
        scratch.mkdir(mode=0o700)
        os.chmod(scratch, 0o700)
        listener = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        listener.bind(str(ack_socket)); os.chmod(ack_socket, 0o600); listener.listen(1)
        ack_socket_identity = _socket_identity(ack_socket, expected_mode=0o600)
        listener.setblocking(False)
        selector = selectors.DefaultSelector()
        selector.register(listener, selectors.EVENT_READ, "listener")
        selector.register(shutdown_r, selectors.EVENT_READ, "shutdown")
        child_env = {
            "PATH": "/usr/bin:/bin", "HOME": "/thayerfs/home/f004ndc",
            "LANG": "C.UTF-8", "LC_ALL": "C.UTF-8",
            "PYTEST_DISABLE_PLUGIN_AUTOLOAD": "1",
            "MSAE_GEN6_ALLOW_REAL_TMUX_TEST": "1",
            "MSAE_GEN6_TMUX_TEST_TOKEN": token,
            "CUDA_VISIBLE_DEVICES": "",
        }
        child_argv = [str(PYTHON), "-B", "-I", "-m", "pytest", "-q",
                      "-p", "no:cacheprovider",
                      "tests/test_msae_independent_measurement_v3_post_m6_gen6.py::test_failed_handoff_extinction_kills_real_processes_and_socket"]
        child = subprocess.Popen(child_argv, cwd=ROOT, env=child_env,
                                 stdin=subprocess.DEVNULL, start_new_session=True)
        started = time.monotonic()
        global_child_deadline = started + CHILD_TIMEOUT
        for fault_mode in FAULT_MODES:
            phase = f"fault-matrix-{fault_mode}"
            _supervise_fault_case(
                fault_mode, listener=listener, child=child,
                socket_path=tmux_socket, session=session, scratch=scratch,
                global_deadline=global_child_deadline,
                shutdown_requested=lambda: shutdown, selector=selector)
            selector.unregister(listener)
            listener, ack_socket_identity = _recycle_fault_namespace(
                listener, ack_socket, scratch, ack_socket_identity)
            selector.register(listener, selectors.EVENT_READ, "listener")
        phase = "start-final-foreground-server"
        previous_umask = os.umask(0o077)
        try:
            foreground_server = subprocess.Popen(
                [str(TMUX), "-D", "-f", "/dev/null", "-S", str(tmux_socket)],
                stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL, env=expected_environment,
                start_new_session=True, close_fds=True)
        finally:
            os.umask(previous_umask)
        foreground_row = _proc_row(foreground_server.pid)
        if (foreground_row is None
                or int(foreground_row["pgrp"]) != foreground_server.pid):
            raise RuntimeError("final foreground tmux server identity drift")
        socket_deadline = min(time.monotonic() + 3, global_child_deadline)
        while not _path_present(tmux_socket):
            if foreground_server.poll() is not None:
                raise RuntimeError("final foreground tmux server exited before socket")
            if time.monotonic() >= socket_deadline:
                raise TimeoutError("final foreground tmux socket timeout")
            time.sleep(0.01)
        tmux_socket_identity = _promote_tmux_socket_mode(tmux_socket)
        phase = "await-identity-connection"
        handshake_deadline = min(time.monotonic() + ACK_TIMEOUT,
                                 global_child_deadline)
        connection: socket.socket | None = None
        try:
            while connection is None:
                if shutdown or child.poll() is not None or time.monotonic() >= handshake_deadline:
                    raise RuntimeError("tmux test failed before identity connection")
                if _path_present(tmux_socket) and pane_pid is None:
                    if tmux_socket_identity is None:
                        tmux_socket_identity = _socket_identity(tmux_socket)
                    captured = _tmux_process_identity(tmux_socket, session)
                    if captured is not None:
                        (tmux_server_pid, tmux_server_ticks,
                         pane_pid, pane_ticks) = captured
                for key, _mask in selector.select(timeout=0.05):
                    if key.data == "listener":
                        connection, _ = listener.accept(); connection.settimeout(ACK_TIMEOUT)
                    else:
                        os.read(shutdown_r, 4096)
            # The fake broker can connect between the last socket-presence
            # check and ``accept``.  Bind the pane after accept as well rather
            # than treating that benign race as a missing identity.
            while pane_pid is None and time.monotonic() < handshake_deadline:
                if tmux_socket_identity is None and _path_present(tmux_socket):
                    tmux_socket_identity = _socket_identity(tmux_socket)
                captured = _tmux_process_identity(tmux_socket, session)
                if captured is not None:
                    (tmux_server_pid, tmux_server_ticks,
                     pane_pid, pane_ticks) = captured
                    break
                if shutdown or child.poll() is not None:
                    break
                time.sleep(0.02)
            if pane_pid is None or pane_ticks is None:
                raise RuntimeError("tmux pane identity was not captured")
            phase = "read-identity"
            credentials = struct.unpack("3i", connection.getsockopt(
                socket.SOL_SOCKET, socket.SO_PEERCRED, struct.calcsize("3i")))
            peer_pid = credentials[0]
            raw = b""
            while not raw.endswith(b"\n"):
                chunk = connection.recv(16384 - len(raw))
                if not chunk or len(raw) + len(chunk) > 16384:
                    raise RuntimeError("tmux test identity frame drift")
                raw += chunk
            sent = json.loads(raw.decode("utf-8"))
            durable = _read_identity(process_path)
            if durable is None or raw != _canonical_bytes(sent) or sent != durable:
                raise RuntimeError("tmux test durable/sent identity mismatch")
            identity = _validate_identity(durable, pane_pid, credentials)
            phase = "arm-descendant"
            connection.sendall(b"I")
            if connection.recv(1) != b"A":
                raise RuntimeError("tmux test resistance ACK drift")
            identity = _validate_identity(durable, pane_pid, credentials)
            phase = "publish-bound-identity"
            _publish_identity_bound(bound_path, {
                "schema_version": "msae_v3_gen6_tmux_test_identity_bound_v1",
                "process_sha256": hashlib.sha256(_canonical_bytes(durable)).hexdigest(),
                "supervisor_pid": os.getpid(),
            })
            phase = "confirm-bound-identity"
            connection.sendall(b"B")
            _reject_pending_identity_frame(connection)
            phase = "await-child-timeout-arm"
            _await_child_timeout_arm(
                selector=selector, listener=listener, child=child,
                deadline=global_child_deadline,
                shutdown_requested=lambda: shutdown)
            phase = "reach-child-timeout"
            _wait_for_registered_child_timeout(
                selector=selector, child=child,
                deadline=global_child_deadline,
                shutdown_requested=lambda: shutdown)
            phase = "terminate-timed-out-child-group"
            _terminate_child_group(child)
            success = child.returncode == 0
        finally:
            if connection is not None:
                connection.close()
    except BaseException as exc:
        print(f"tmux test supervisor failure during {phase}: {exc}", file=sys.stderr)
        success = False
    finally:
        if selector is not None:
            try: selector.close()
            except Exception: success = False
        if child is not None:
            try: _terminate_child_group(child)
            except Exception: success = False
        if foreground_server is not None:
            try:
                if foreground_server.poll() is None:
                    _terminate_group(foreground_server.pid)
                foreground_server.wait(timeout=TERM_TIMEOUT)
            except Exception:
                success = False
        # Never signal PIDs supplied by an identity that did not pass the full
        # peer/pane/process validation above.
        candidate = identity
        if candidate is not None:
            try: _terminate_group(int(candidate["worker_pgid"]))
            except Exception: success = False
            for prefix in ("worker", "broker", "pane"):
                try: _terminate_pid(int(candidate[f"{prefix}_pid"]),
                                    int(candidate[f"{prefix}_start_ticks"]))
                except Exception: success = False
        # A peer PID becomes signal authority only through ``identity`` above.
        # SO_PEERCRED alone is same-UID provenance, not proof that the peer is
        # the captured pane/broker; never signal an unvalidated connector.
        if pane_pid is not None and pane_ticks is not None:
            try: _terminate_pid(pane_pid, pane_ticks)
            except Exception: success = False
        if _path_present(tmux_socket):
            try:
                if (tmux_socket_identity is None
                        or _socket_identity(tmux_socket) != tmux_socket_identity):
                    success = False
                else:
                    for tail in (("kill-session", "-t", session),
                                 ("kill-server",)):
                        # Rebind the pathname before every destructive tmux
                        # client invocation; a replacement socket is never
                        # command authority.
                        if _socket_identity(tmux_socket) != tmux_socket_identity:
                            raise RuntimeError("tmux test socket changed before cleanup")
                        _tmux(tmux_socket, *tail)
            except Exception:
                success = False
        if tmux_server_pid is not None and tmux_server_ticks is not None:
            try: _terminate_pid(tmux_server_pid, tmux_server_ticks)
            except Exception: success = False
        if listener is not None:
            try: listener.close()
            except Exception: success = False
        if _path_present(ack_socket):
            try:
                if (ack_socket_identity is None
                        or _socket_identity(ack_socket, expected_mode=0o600) != ack_socket_identity):
                    success = False
                else:
                    ack_socket.unlink()
            except (OSError, RuntimeError):
                success = False
        for partial_name, final_name in (
                (".process.json.partial", "process.json"),
                (".identity_bound.json.partial", "identity_bound.json"),
                (".terminal.claim.test.partial", "terminal.claim.test"),
                (".technical_failure.test.json.partial",
                 "technical_failure.test.json")):
            try:
                if (_path_present(scratch)
                        and not _cleanup_owned_regular_pair(
                            scratch, partial_name, final_name)):
                    success = False
            except (OSError, RuntimeError):
                success = False
        try:
            if _path_present(scratch):
                if any(os.scandir(scratch)): success = False
                else: scratch.rmdir()
        except OSError:
            success = False
        if _path_present(tmux_socket):
            try:
                session_state = _tmux(tmux_socket, "has-session", "-t", session)
                server_live = (tmux_server_pid is not None
                               and tmux_server_ticks is not None
                               and _pid_matches(tmux_server_pid, tmux_server_ticks))
                if (session_state.returncode == 0 or server_live
                        or tmux_socket_identity is None
                        or _socket_identity(tmux_socket) != tmux_socket_identity):
                    success = False
                else:
                    tmux_socket.unlink()
            except (OSError, RuntimeError):
                success = False
        try:
            final_session = _tmux(
                tmux_socket, "has-session", "-t", session)
            if final_session.returncode == 0:
                success = False
        except Exception:
            success = False
        try:
            if candidate is not None and _group_members(
                    int(candidate["worker_pgid"])):
                success = False
        except Exception:
            success = False
        try:
            if (pane_pid is not None and pane_ticks is not None
                    and _pid_matches(pane_pid, pane_ticks)):
                success = False
        except Exception:
            success = False
        try:
            if (tmux_server_pid is not None and tmux_server_ticks is not None
                    and _pid_matches(tmux_server_pid, tmux_server_ticks)):
                success = False
        except Exception:
            success = False
        try:
            if any(_path_present(path) for path in
                   (tmux_socket, ack_socket, scratch)):
                success = False
        except Exception:
            success = False
        for fd in (shutdown_r, shutdown_w):
            try: os.close(fd)
            except OSError: success = False
    return 0 if success else 1


if __name__ == "__main__":
    raise SystemExit(main())
