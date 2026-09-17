#!/usr/bin/env python3
"""One-shot, exact-sparse, metadata-quiet NORSPAN-1 source acquisition."""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import stat
import re
import selectors
import signal
import time
import subprocess
from pathlib import Path
from typing import Any

import prepare_msae_independent_norspan_v1 as protocol
import msae_norspan_jpc_runtime as jpc_runtime

FILES = [*protocol.SOURCE_FILES.values(), protocol.LICENSE_FILE]
GIT_BASE = ["git", "-c", "credential.helper=", "-c", "core.hooksPath=/dev/null"]


def minimal_env(home: Path) -> dict[str, str]:
    return {
        "PATH": "/usr/bin:/bin", "HOME": str(home), "LC_ALL": "C",
        "GIT_CONFIG_NOSYSTEM": "1", "GIT_TERMINAL_PROMPT": "0",
        "GIT_PROTOCOL_FROM_USER": "0",
    }


class SupervisionFailure(protocol.GateFailure):
    def __init__(self, reason: str, stdout: bytes, stderr: bytes, returncode: int):
        super().__init__("source_subprocess_" + reason)
        self.reason, self.stdout, self.stderr, self.returncode = reason, stdout, stderr, returncode


def run(argv: list[str], *, env: dict[str, str], cwd: Path | None = None,
        timeout_seconds: float = 600, stdout_limit_bytes: int = 16 * 1024 * 1024,
        stderr_limit_bytes: int = 4 * 1024 * 1024) -> tuple[bytes, bytes, int]:
    """Monotonic, concurrently drained, byte-bounded owned-process-group supervisor."""
    if (type(timeout_seconds) not in {int, float} or not math.isfinite(timeout_seconds)
            or not 0 < timeout_seconds <= 600
            or type(stdout_limit_bytes) is not int or not 1 <= stdout_limit_bytes <= 16 * 1024**2
            or type(stderr_limit_bytes) is not int or not 1 <= stderr_limit_bytes <= 4 * 1024**2):
        raise ValueError("invalid_supervision_limits")
    deadline = time.monotonic() + timeout_seconds
    outputs = {"stdout": bytearray(), "stderr": bytearray()}
    limits = {"stdout": stdout_limit_bytes, "stderr": stderr_limit_bytes}
    failure = None
    selector = selectors.DefaultSelector()
    proc = None
    primary = None
    def exited_without_reaping():
        # Keep the owned leader (including a zombie) until group termination.
        # poll()/wait() here could release the PID before killpg and hit reuse.
        return os.waitid(os.P_PID, proc.pid, os.WEXITED | os.WNOHANG | os.WNOWAIT) is not None
    try:
        proc = subprocess.Popen(argv, cwd=cwd, env=env, stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE, start_new_session=True)
        for name, pipe in [("stdout", proc.stdout), ("stderr", proc.stderr)]:
            if pipe is None:
                raise RuntimeError("missing_supervision_pipe")
            os.set_blocking(pipe.fileno(), False)
            selector.register(pipe, selectors.EVENT_READ, name)
        while selector.get_map() or not exited_without_reaping():
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                failure = "timeout"
                break
            if not selector.get_map():
                time.sleep(min(remaining, 0.01))
                continue
            for key, _mask in selector.select(min(remaining, 0.05)):
                name = key.data
                budget = limits[name] - len(outputs[name])
                block = os.read(key.fileobj.fileno(), min(65536, budget + 1))
                if not block:
                    selector.unregister(key.fileobj)
                    continue
                outputs[name].extend(block[:budget])
                if len(block) > budget:
                    failure = name + "_limit"
                    break
            if failure is not None:
                break
        if failure is not None:
            raise SupervisionFailure(failure, bytes(outputs["stdout"]), bytes(outputs["stderr"]), -1)
    except BaseException as exc:
        primary = exc
        raise
    finally:
        first = primary
        failed_cleanup = False
        actions = []
        if proc is not None:
            def stop_group():
                try:
                    os.killpg(proc.pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
            actions.extend([("group_stop", stop_group), ("leader_reap", lambda: proc.wait(timeout=5))])
        actions.append(("selector_close", selector.close))
        if proc is not None:
            for name, pipe in [("stdout", proc.stdout), ("stderr", proc.stderr)]:
                if pipe is not None:
                    actions.append((name + "_close", pipe.close))
        for label, action in actions:
            try:
                action()
            except BaseException as exc:
                failed_cleanup = True
                if first is None:
                    first = exc
                else:
                    first.add_note("supervisor_secondary:" + label + ":" + type(exc).__name__ + ":" + str(exc))
        if first is not None:
            first.cleanup_complete = not failed_cleanup
            if isinstance(first, SupervisionFailure) and proc is not None:
                first.returncode = proc.returncode if proc.returncode is not None else -1
        if primary is None and first is not None:
            raise first
    return bytes(outputs["stdout"]), bytes(outputs["stderr"]), proc.returncode


def command_record(name: str, argv: list[str], stdout: bytes, stderr: bytes,
                   code: int, supervision_failure: str | None = None) -> dict[str, Any]:
    return {
        "name": name, "argv": argv, "exit_status": code,
        "supervision_failure": supervision_failure,
        "stdout_bytes": len(stdout), "stdout_sha256": hashlib.sha256(stdout).hexdigest(),
        "stderr_bytes": len(stderr), "stderr_sha256": hashlib.sha256(stderr).hexdigest(),
    }


def validate_authority(review_sha256: str) -> tuple[dict[str, Any], Path, dict[str, Any]]:
    if protocol.classify_protocol_state() not in {"authority", "acquisition_entered", "network_ready"}:
        raise protocol.GateFailure("authority_state")
    _cfg, baseline, authority, _registry = protocol.validate_authority_chain(review_sha256)
    review_path = protocol.canonical_authority_review_path()
    current = protocol.evidence_snapshot()
    protocol.validate_evidence(current)
    protocol.evidence_compatible(baseline["evidence"], current)
    return authority, review_path, current


def publish_rejection(code: str, commands: list[dict[str, Any]],
                      scratch_record: dict[str, Any]) -> None:
    # Only observed command failures are verifiable operational rejections.
    # Internal/parse/interrupt/custody failures retain network_started unresolved.
    protocol.validate_command_chain(commands, protocol.load_config(), rejection=True)
    protocol.publish_json(protocol.PROV / "rejection.json", {
        "schema_version": "msae_independent_norspan_v1_rejection_jpc_v1",
        "status": "rejected_during_acquisition", "failure_code": code,
        "commands": commands, "scratch": scratch_record,
        "acquisition_entry_sha256": protocol.sha_file(protocol.PROV / "acquisition_entry.json"),
        "network_started_sha256": protocol.sha_file(protocol.PROV / "network_started.json"),
        "authority_sha256": protocol.sha_file(protocol.PROV / "authority.json"),
        "evidence": protocol.evidence_snapshot(),
        "model_operations": 0, "gpu_queries": 0, "training_runs": 0,
        "next_action": "new_reviewed_protocol_only",
    })

def parse_tree(raw: bytes) -> tuple[str, dict[str, str]]:
    rows = raw.split(b"\0")
    if rows[-1:] == [b""]:
        rows.pop()
    blobs: dict[str, str] = {}
    for row in rows:
        try:
            header, name_raw = row.split(b"\t", 1)
            mode, kind, oid = header.decode("ascii").split(" ")
            name = name_raw.decode("utf-8", "strict")
        except (ValueError, UnicodeDecodeError) as exc:
            raise protocol.GateFailure("source_tree_parse") from exc
        if mode != "100644" or kind != "blob" or name not in FILES or name in blobs:
            raise protocol.GateFailure("source_tree_entry")
        if len(oid) != 40 or any(c not in "0123456789abcdef" for c in oid):
            raise protocol.GateFailure("source_blob_id")
        blobs[name] = oid
    if list(sorted(blobs, key=FILES.index)) != FILES or set(blobs) != set(FILES):
        raise protocol.GateFailure("source_tree_cardinality")
    return hashlib.sha256(raw).hexdigest(), blobs


def read_sparse_files(repo: Path, *, file_bytes: int = jpc_runtime.FILE_BYTES_LIMIT,
                      total_bytes: int = jpc_runtime.TOTAL_BYTES_LIMIT) -> dict[str, bytes]:
    if (type(file_bytes) is not int or not 1 <= file_bytes <= jpc_runtime.FILE_BYTES_LIMIT
            or type(total_bytes) is not int or not 1 <= total_bytes <= jpc_runtime.TOTAL_BYTES_LIMIT):
        raise protocol.GateFailure("sparse_budget_schema")
    resources = []
    primary = None
    try:
        root = jpc_runtime._directory(repo, reserve=False, mode=stat.S_IMODE(repo.lstat().st_mode))
        resources.append(root)
        root.validate({".git", *FILES})
        root_before = protocol.jumbo_pair._fingerprint(os.fstat(root.fd))
        payloads = {}
        original = []
        total = 0
        for name in FILES:
            fd = os.open(name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=root.fd)
            original.append((name, fd, None))
            before = os.fstat(fd)
            if not stat.S_ISREG(before.st_mode) or before.st_nlink != 1:
                raise protocol.GateFailure("sparse_source_custody")
            if before.st_size > file_bytes:
                raise protocol.GateFailure("sparse_file_budget")
            if total + before.st_size > total_bytes:
                raise protocol.GateFailure("sparse_total_budget")
            fp = protocol.jumbo_pair._fingerprint(before)
            original[-1] = (name, fd, fp)
            chunks = []
            count = 0
            while block := os.read(fd, min(1024**2, file_bytes - count + 1, total_bytes - total + 1)):
                count += len(block); total += len(block)
                if count > file_bytes:
                    raise protocol.GateFailure("sparse_file_budget")
                if total > total_bytes:
                    raise protocol.GateFailure("sparse_total_budget")
                chunks.append(block)
            if count != before.st_size:
                raise protocol.GateFailure("sparse_source_drift")
            payloads[name] = b"".join(chunks)
        root.validate({".git", *FILES})
        for name, fd, fp in original:
            if (protocol.jumbo_pair._fingerprint(os.fstat(fd)) != fp
                    or protocol.jumbo_pair._fingerprint(os.stat(name, dir_fd=root.fd, follow_symlinks=False)) != fp):
                raise protocol.GateFailure("sparse_source_drift")
        if protocol.jumbo_pair._fingerprint(os.fstat(root.fd)) != root_before:
            raise protocol.GateFailure("sparse_root_drift")
        return payloads
    except BaseException as exc:
        primary = exc
        raise
    finally:
        first = primary
        try:
            protocol.jumbo_pair._close_fds([fd for _name, fd, _fp in reversed(locals().get("original", []))], primary=first)
        except BaseException as exc:
            first = exc
        jpc_runtime._close_resources(resources, primary=first)
        if primary is None and first is not None:
            raise first


def cleanup_scratch(scratch: Path, parent_fd: int, scratch_fd: int,
                    identity: os.stat_result) -> None:
    """Obsolete destructive interface: explicitly prohibited, no side effects."""
    raise protocol.GateFailure("scratch_deletion_prohibited_jpc")


def acquire(review_sha256: str) -> None:
    protocol.require_jpc_qualification()  # BEFORE any real state or reservation.
    initial = protocol.classify_protocol_state()
    if initial != "authority":
        # A fresh acquisition command never performs implicit restart/replay.
        # Full externally anchored recovery/control integration is still pending.
        raise protocol.GateFailure("explicit_recovery_required:" + initial)
    authority, review_path, current_evidence = validate_authority(review_sha256)
    cfg = jpc_runtime.load_client_contract(protocol.ROOT)
    authority_sha256 = protocol.sha_file(protocol.PROV / "authority.json")
    seed = {
        "authority_sha256": authority_sha256,
        "baseline_sha256": protocol.sha_file(protocol.PROV / "baseline.json"),
        "history_registry_sha256": protocol.sha_file(protocol.PROV / "current_history_registry.json"),
        "runner_sha256": protocol.sha_file(Path(__file__).resolve()),
        "source_commit": protocol.COMMIT, "source_files": FILES,
    }
    entry_lineage = protocol.sha_bytes(protocol.canonical_bytes(seed))
    # Explicit qualified Jumbo client-contract parent must already exist; no default TMPDIR,
    # automatic parent provisioning, prefix discovery, or reservation reuse.
    scratch = Path(cfg["scratch"]["base"]) / (entry_lineage + ".acquisition")
    with jpc_runtime.reserve_scratch(scratch, authority_sha256=authority_sha256,
                                      entry_lineage_sha256=entry_lineage) as lease:
        _acquire_in_reserved_scratch(review_sha256, authority, review_path,
                                     current_evidence, lease)


def _acquire_in_reserved_scratch(review_sha256: str, authority: dict[str, Any],
                                review_path: Path, current_evidence: dict[str, Any],
                                lease: jpc_runtime.ScratchLease) -> None:
    """Live first invocation only; whole state/schema integration remains blocked."""
    lease.validate_pristine()
    runner_path = Path(__file__).resolve()
    entry = {
        "schema_version": "msae_independent_norspan_v1_acquisition_entry_jpc_v1",
        "source_repo": protocol.REPO, "source_commit": protocol.COMMIT,
        "source_files": FILES,
        "scratch_binding": dict(lease.binding),
        "entry_lineage_sha256": lease.binding["entry_lineage_sha256"],
        "baseline_sha256": protocol.sha_file(protocol.PROV / "baseline.json"),
        "history_registry_sha256": protocol.sha_file(protocol.PROV / "current_history_registry.json"),
        "authority_sha256": protocol.sha_file(protocol.PROV / "authority.json"),
        "authority_review_sha256": protocol.sha_file(review_path),
        "runner_sha256": protocol.sha_file(runner_path),
        "authority_controls": authority["controls"],
        "state_order": protocol.load_config()["state_order"],
        "pre_entry_inventory": protocol.protocol_inventory(),
        "expected_absent": authority["absent_at_publication"],
        "expected_schemas": {
            "entry": "msae_independent_norspan_v1_acquisition_entry_jpc_v1",
            "network_ready": "msae_independent_norspan_v1_pre_network_ready_jpc_v1",
            "network_started": "msae_independent_norspan_v1_network_started_jpc_v1",
            "terminal": "msae_independent_norspan_v1_source_acquisition_jpc_v1",
        },
        "pre_entry_evidence": current_evidence,
        "pre_entry_history_census": protocol.validate_history_registry(protocol.load_json(protocol.PROV / "current_history_registry.json"), protocol.load_config()),
        "subprocesses_started": 0, "model_operations": 0, "gpu_queries": 0, "training_runs": 0,
        "status": "entered",
    }
    protocol.publish_json(protocol.PROV / "acquisition_entry.json", entry)
    if protocol.classify_protocol_state() != "acquisition_entered":
        raise protocol.GateFailure("acquisition_entry_state")
    if protocol.classify_protocol_state() == "acquisition_entered":
        protocol.publish_json(protocol.PROV / "pre_network_ready.json", {
            "schema_version": "msae_independent_norspan_v1_pre_network_ready_jpc_v1",
            "acquisition_entry_sha256": protocol.sha_file(protocol.PROV / "acquisition_entry.json"),
            "scratch_binding": dict(lease.binding),
            "evidence": protocol.evidence_snapshot(), "history_census": protocol.validate_history_registry(protocol.load_json(protocol.PROV / "current_history_registry.json"), protocol.load_config()), "status": "ready",
        })
        if protocol.classify_protocol_state() != "network_ready":
            raise protocol.GateFailure("network_ready_state")
    lease.validate_pristine()  # Bound reservation must still be pristine pre-start.
    protocol.publish_json(protocol.PROV / "network_started.json", {
        "schema_version": "msae_independent_norspan_v1_network_started_jpc_v1",
        "pre_network_ready_sha256": protocol.sha_file(protocol.PROV / "pre_network_ready.json"),
        "scratch_binding": dict(lease.binding),
        "evidence": protocol.evidence_snapshot(), "history_census": protocol.validate_history_registry(protocol.load_json(protocol.PROV / "current_history_registry.json"), protocol.load_config()), "status": "started",
    })
    if protocol.classify_protocol_state() != "network_started":
        raise protocol.GateFailure("network_started_state")

    protocol.validate_authority_chain(review_sha256)  # Last complete recensus before any network subprocess.
    commands: list[dict[str, Any]] = []
    scratch = lease.path
    repo = scratch / "repo"
    home = scratch / "home"
    env = minimal_env(home)
    payloads: dict[str, bytes] = {}
    tree_oid = ""
    tree_listing_sha256 = ""
    blobs: dict[str, str] = {}
    try:
        command_specs = [
            ("clone", [*GIT_BASE, "clone", "--quiet", "--filter=blob:none", "--no-checkout",
                       protocol.REPO, str(repo)]),
            ("sparse_init", [*GIT_BASE, "-C", str(repo), "sparse-checkout", "init", "--no-cone"]),
            ("sparse_set", [*GIT_BASE, "-C", str(repo), "sparse-checkout", "set", "--no-cone", *FILES]),
            ("checkout", [*GIT_BASE, "-C", str(repo), "checkout", "--quiet", "--detach", protocol.COMMIT]),
            ("head", [*GIT_BASE, "-C", str(repo), "rev-parse", "HEAD"]),
            ("tree", [*GIT_BASE, "-C", str(repo), "rev-parse", protocol.COMMIT + "^{tree}"]),
            ("ls_tree", [*GIT_BASE, "-C", str(repo), "ls-tree", "-z", protocol.COMMIT, "--", *FILES]),
            ("object_inventory", [*GIT_BASE, "-C", str(repo), "cat-file", "--batch-all-objects",
                                  "--batch-check=%(objectname) %(objecttype) %(objectsize)"]),
        ]
        outputs: dict[str, bytes] = {}
        for name, argv in command_specs:
            try:
                stdout, stderr, code = run(argv, env=env)
            except SupervisionFailure as exc:
                commands.append(command_record(name, argv, exc.stdout, exc.stderr,
                                               exc.returncode, exc.reason))
                raise
            commands.append(command_record(name, argv, stdout, stderr, code))
            if code:
                raise protocol.GateFailure("source_acquisition_" + name)
            outputs[name] = stdout
            lease.snapshot()  # Between-command monitor, NOT hard quota.
        if outputs["head"] != (protocol.COMMIT + "\n").encode("ascii"):
            raise protocol.GateFailure("source_commit")
        tree_oid = outputs["tree"].decode("ascii").removesuffix("\n")
        if (re.fullmatch(r"[0-9a-f]{40}", tree_oid) is None
                or outputs["tree"] != (tree_oid + "\n").encode("ascii")):
            raise protocol.GateFailure("source_tree")
        tree_listing_sha256, blobs = parse_tree(outputs["ls_tree"])
        object_types: dict[str, int] = {}
        local_blobs: set[str] = set()
        seen_objects: set[str] = set()
        object_records: dict[str, tuple[str, int]] = {}
        for line in outputs["object_inventory"].decode("ascii", "strict").splitlines():
            try:
                oid, kind, size_text = line.split(" ")
                if re.fullmatch(r"0|[1-9][0-9]*", size_text) is None:
                    raise ValueError("noncanonical size")
            except ValueError as exc:
                raise protocol.GateFailure("object_inventory_parse") from exc
            if len(oid) != 40 or any(c not in "0123456789abcdef" for c in oid):
                raise protocol.GateFailure("object_inventory_oid")
            if kind not in {"blob", "tree", "commit", "tag"} or oid in seen_objects:
                raise protocol.GateFailure("object_inventory_type_or_duplicate")
            seen_objects.add(oid)
            object_records[oid] = (kind, int(size_text))
            object_types[kind] = object_types.get(kind, 0) + 1
            if kind == "blob":
                local_blobs.add(oid)
        inventory_records = [{"oid": oid, "kind": kind, "bytes": size}
                             for oid, (kind, size) in object_records.items()]
        reconstructed = b"".join(f"{row['oid']} {row['kind']} {row['bytes']}\n".encode("ascii")
                                 for row in inventory_records)
        if reconstructed != outputs["object_inventory"]:
            raise protocol.GateFailure("object_inventory_noncanonical")
        if local_blobs != set(blobs.values()):
            raise protocol.GateFailure("partial_clone_extra_blobs")
        if (object_records.get(protocol.COMMIT, (None, 0))[0] != "commit"
                or object_records.get(tree_oid, (None, 0))[0] != "tree"):
            raise protocol.GateFailure("object_inventory_required_commit_tree")
        payloads = read_sparse_files(repo)
        for name, payload in payloads.items():
            oid = hashlib.sha1(b"blob " + str(len(payload)).encode() + b"\0" + payload).hexdigest()
            if oid != blobs[name] or object_records.get(oid) != ("blob", len(payload)):
                raise protocol.GateFailure("source_blob_custody")
    except BaseException as exc:
        # Retain ALL names/bytes, even when current durability/custody is unproved.
        # A secondary snapshot/publication fault never replaces the first failure.
        scratch_record = None
        try:
            scratch_record = lease.snapshot(durable=True)
        except BaseException as secondary:
            exc.add_note("retained_scratch_unresolved:" + type(secondary).__name__ + ":" + str(secondary))
        code = str(exc) if isinstance(exc, protocol.GateFailure) else "acquisition_internal_error"
        if (getattr(exc, "cleanup_complete", True) and scratch_record is not None and commands
                and (commands[-1]["exit_status"] != 0 or commands[-1]["supervision_failure"] is not None)):
            try:
                publish_rejection(code, commands, scratch_record)
            except BaseException as secondary:
                exc.add_note("rejection_publication_unresolved:" + type(secondary).__name__ + ":" + str(secondary))
        raise
    else:
        scratch_record = lease.snapshot(durable=True)

    protocol.ensure_directory(protocol.DATA, 0o700)
    protocol.ensure_directory(protocol.DATA / "raw", 0o700)
    raw_manifest = protocol.publish_flat_directory(
        protocol.RAW, payloads, directory_mode=0o555, file_mode=0o444,
    )
    files: dict[str, Any] = {}
    for name in FILES:
        files[name] = {**raw_manifest[name], "git_blob_sha1": blobs[name]}
    acquisition = {
        "schema_version": "msae_independent_norspan_v1_source_acquisition_jpc_v1",
        "source_repo": protocol.REPO, "source_commit": protocol.COMMIT,
        "tree_object_sha1": tree_oid, "tree_listing_sha256": tree_listing_sha256,
        "files": files, "commands": commands, "minimal_environment_keys": sorted(env),
        "minimal_environment": env,
        "local_blob_object_ids": sorted(local_blobs),
        "local_object_type_counts": dict(sorted(object_types.items())),
        "local_object_records": inventory_records,
        "sparse_checkout": True, "worktree_exact_four_files": True,
        "scratch": scratch_record, "source_content_printed": False,
        "authority_sha256": protocol.sha_file(protocol.PROV / "authority.json"),
        "authority_review_sha256": protocol.sha_file(review_path),
        "acquisition_entry_sha256": protocol.sha_file(protocol.PROV / "acquisition_entry.json"),
        "post_acquisition_evidence": protocol.evidence_snapshot(),
        "model_operations": 0, "gpu_queries": 0, "training_runs": 0,
        "status": "success",
    }
    protocol.publish_json(protocol.PROV / "source_acquisition.json", acquisition)
    if protocol.classify_protocol_state() != "acquisition_terminal":
        raise protocol.GateFailure("acquisition_terminal_state")


def main() -> None:
    import msae_norspan_jpc_controller as controller
    parser = argparse.ArgumentParser()
    controller.add_arguments(parser)
    args = parser.parse_args()
    active = controller.from_arguments(args)
    result = active.execute("acquire",args)
    print(json.dumps({"result":result,"outside_catalog":str(active.catalog.path),
                      "catalog_sha256":active.catalog.sha256,"source_work_authorized":False},sort_keys=True))


if __name__ == "__main__":
    main()
