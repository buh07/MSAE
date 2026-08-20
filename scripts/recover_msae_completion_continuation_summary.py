#!/usr/bin/env python3
"""Governed replay and crash-safe publication for the frozen atlas summary incident."""
from __future__ import annotations

import argparse
import ast
import contextlib
import errno
import json
import os
import pickle
import signal
import shutil
import socket
import stat
import subprocess
import sys
import time
import traceback
import uuid
from pathlib import Path
from typing import Any

from msa_completion_common import atomic_write_bytes, atomic_write_json, sha256_file
from msa_completion_summary_recovery_common import (
    CONTINUATION_RUN_ROOT,
    JOBS,
    PRIMARY,
    ROOT,
    TASKS,
    ATTEMPT_RE,
    candidate_root,
    capability_path,
    canonical_json_bytes,
    canonical_root,
    close_attempt,
    close_orphan_attempts,
    config,
    content_digest,
    content_inventory,
    create_attempt,
    deployment_mount,
    ensure_recovery_directories,
    fsync_directory,
    fsync_file,
    fsync_tree,
    implementation_inventory,
    inventory_digest,
    recovery_run_root,
    regular_file_facts,
    read_state_chain,
    resolve_expected_sources,
    root_digest,
    root_inventory,
    sha256_bytes,
    append_state,
    job_lock_path,
    require_job_lock,
    strict_json,
    supervisor_job_lock,
    success_path,
    utc_now,
    validate_candidate,
    validate_capability_payload,
    validate_canonical,
    validate_result_contract,
    verify_incident_inputs,
    verify_execution_owner_mount,
    verify_initial_freeze,
    verify_promotion_freeze,
    write_once_json,
)


# The fresh child owns the sole runtime rebind.  Keep this source deliberately
# small: validate_child_source() rejects any expansion outside the exact adapter.
CHILD_SOURCE = r'''import json
import os
import pathlib
import sys
import summarize_msae_completion_continuation as frozen_summary
import verify_msae_completion as frozen_verifier
import run_msae_refit_worker as frozen_worker

if os.environ.get("MSAE_SUMMARY_RECOVERY_CHILD") != "1":
    raise RuntimeError("summary-recovery child guard is absent")
inventory_path = pathlib.Path(sys.argv[1])
output_root = pathlib.Path(sys.argv[2])
payload = json.loads(inventory_path.read_text(encoding="utf-8"))
inventory = payload["expected_sources"]

def inventory_adapter():
    return {role: {task: set(values) for task, values in tasks.items()} for role, tasks in inventory.items()}

def k2_family_rows_adapter(recovery, mapping, eligible_tasks):
    expected_primary = {
        "absolute_position": ["abs_pos_16", "abs_pos_8"],
        "relative_structural_position": ["relative_quartile", "head_signed_distance", "dependency_depth", "boundary_state"],
        "lexical_semantic_content": ["token_identity_256", "lemma_identity_256", "ner_coarse"],
    }
    expected_mapping = {
        "absolute_position": "pos",
        "relative_structural_position": "pos",
        "lexical_semantic_content": "content",
    }
    expected_eligible = {"relative_quartile", "head_signed_distance", "dependency_depth", "boundary_state", "ner_coarse"}
    expected_tasks = {task for tasks in expected_primary.values() for task in tasks}
    if frozen_worker.PRIMARY != expected_primary or mapping != expected_mapping or set(eligible_tasks) != expected_eligible:
        raise RuntimeError("K2 family adapter call context changed")
    if set(recovery) != {"pos", "content"} or any(set(tasks) != expected_tasks for tasks in recovery.values()):
        raise RuntimeError("K2 family adapter recovery inventory changed")
    output = {}
    for family, family_tasks_all in expected_primary.items():
        family_tasks = [task for task in family_tasks_all if task in eligible_tasks]
        if len(family_tasks) < 2:
            output[family] = {"assigned_recovery": None, "leakage": None, "selectivity_margin": None, "leakage_by_representation": {}, "invalid_reason": "fewer_than_two_eligible_tasks"}
        else:
            assigned = mapping[family]
            other = "content" if assigned == "pos" else "pos"
            output[family] = frozen_worker.family_summary(recovery, assigned, [other], family_tasks)
    return output

frozen_summary.expected_sources = inventory_adapter
frozen_verifier.family_rows = k2_family_rows_adapter
result = frozen_summary.recompute()
report = frozen_summary.report_text(result)
result_bytes = (json.dumps(result, sort_keys=True, separators=(",", ":"), allow_nan=False) + "\n").encode("utf-8")
(output_root / "diagnostic_results.json").write_bytes(result_bytes)
(output_root / "diagnostic_results.md").write_bytes(report.encode("utf-8"))
'''


def _call_name(node: ast.AST) -> str | None:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        prefix = _call_name(node.value)
        return None if prefix is None else f"{prefix}.{node.attr}"
    return None


def validate_child_source(source: str = CHILD_SOURCE) -> str:
    """Deny by default any mutation/call surface beyond the reviewed child."""

    tree = ast.parse(source)
    imports: list[tuple[str, str | None]] = []
    for node in tree.body:
        if isinstance(node, ast.Import):
            imports.extend((alias.name, alias.asname) for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            raise RuntimeError("summary-recovery child may not use from-imports")
    if imports != [
        ("json", None), ("os", None), ("pathlib", None), ("sys", None),
        ("summarize_msae_completion_continuation", "frozen_summary"),
        ("verify_msae_completion", "frozen_verifier"),
        ("run_msae_refit_worker", "frozen_worker"),
    ]:
        raise RuntimeError("summary-recovery child import inventory changed")

    functions = [node for node in ast.walk(tree) if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))]
    if (len(functions) != 2
            or any(not isinstance(node, ast.FunctionDef) for node in functions)
            or {node.name for node in functions} != {"inventory_adapter", "k2_family_rows_adapter"}):
        raise RuntimeError("summary-recovery child function inventory changed")
    if any(isinstance(node, (ast.Delete, ast.AugAssign, ast.AnnAssign, ast.Lambda,
                             ast.ClassDef, ast.With, ast.AsyncWith, ast.Try)) for node in ast.walk(tree)):
        raise RuntimeError("summary-recovery child contains a denied syntax form")

    attribute_stores: list[str] = []
    subscript_stores: list[str | None] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Attribute) and isinstance(node.ctx, ast.Store):
            attribute_stores.append(_call_name(node))
        if isinstance(node, ast.Subscript) and isinstance(node.ctx, ast.Store):
            subscript_stores.append(_call_name(node.value))
    if sorted(attribute_stores) != [
            "frozen_summary.expected_sources", "frozen_verifier.family_rows"] \
            or subscript_stores != ["output", "output"]:
        raise RuntimeError("summary-recovery child mutation inventory changed")

    allowed_calls = {
        "RuntimeError", "set", "json.loads", "json.dumps", "os.environ.get",
        "pathlib.Path", "inventory_path.read_text", "frozen_summary.recompute",
        "frozen_summary.report_text", "report.encode", "inventory.items", "tasks.items",
        "len", "any", "expected_primary.values", "recovery.values",
        "expected_primary.items", "frozen_worker.family_summary",
    }
    # Calls through the two path expressions have an AST BinOp receiver, so
    # recognize their method names separately and still require exactly two.
    path_write_calls = 0
    expression_encode_calls = 0
    frozen_calls: list[str] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        name = _call_name(node.func)
        if isinstance(node.func, ast.Attribute) and node.func.attr == "write_bytes" and name is None:
            path_write_calls += 1
            continue
        if isinstance(node.func, ast.Attribute) and node.func.attr == "encode" and name is None:
            expression_encode_calls += 1
            continue
        if name not in allowed_calls:
            raise RuntimeError(f"summary-recovery child call is denied: {name}")
        if name and name.startswith("frozen_summary."):
            frozen_calls.append(name)
    if path_write_calls != 2:
        raise RuntimeError("summary-recovery child output-write inventory changed")
    if expression_encode_calls != 1:
        raise RuntimeError("summary-recovery child serialization-call inventory changed")
    if sorted(frozen_calls) != ["frozen_summary.recompute", "frozen_summary.report_text"]:
        raise RuntimeError("summary-recovery child frozen-module call inventory changed")

    frozen_attributes = sorted({
        _call_name(node) for node in ast.walk(tree)
        if isinstance(node, ast.Attribute) and _call_name(node)
        and _call_name(node).startswith("frozen_summary.")
    })
    if frozen_attributes != [
        "frozen_summary.expected_sources", "frozen_summary.recompute",
        "frozen_summary.report_text",
    ]:
        raise RuntimeError("summary-recovery child frozen-module access inventory changed")
    verifier_attributes = sorted({
        _call_name(node) for node in ast.walk(tree)
        if isinstance(node, ast.Attribute) and _call_name(node)
        and _call_name(node).startswith("frozen_verifier.")
    })
    if verifier_attributes != ["frozen_verifier.family_rows"]:
        raise RuntimeError("summary-recovery child verifier access inventory changed")
    worker_attributes = sorted({
        _call_name(node) for node in ast.walk(tree)
        if isinstance(node, ast.Attribute) and _call_name(node)
        and _call_name(node).startswith("frozen_worker.")
    })
    if worker_attributes != ["frozen_worker.PRIMARY", "frozen_worker.family_summary"]:
        raise RuntimeError("summary-recovery child producer access inventory changed")
    return sha256_bytes(source.encode("utf-8"))


def verify_k2_family_drift_contract() -> dict[str, Any]:
    """Prove the recovery adapter is exactly the frozen K2 producer rule."""

    from run_msae_refit_worker import family_rows, family_summary

    with (CONTINUATION_RUN_ROOT / "baseline/baseline_bundle.pkl").open("rb") as handle:
        baseline = pickle.load(handle)
    eligible = {task for task, row in baseline["tier1_eligibility"].items()
                if row["eligible"] is True}
    expected_eligible = {
        "relative_quartile", "head_signed_distance", "dependency_depth",
        "boundary_state", "ner_coarse",
    }
    mapping = {family: ("content" if family == "lexical_semantic_content" else "pos")
               for family in PRIMARY}
    if eligible != expected_eligible or set(TASKS) != {
            task for family_tasks in PRIMARY.values() for task in family_tasks}:
        raise RuntimeError("frozen K2 family/eligibility inventory changed")

    def producer_rows(recovery: dict[str, dict[str, float | None]]) -> dict[str, Any]:
        output: dict[str, Any] = {}
        for family, all_tasks in PRIMARY.items():
            tasks = [task for task in all_tasks if task in eligible]
            if len(tasks) < 2:
                output[family] = {
                    "assigned_recovery": None, "leakage": None,
                    "selectivity_margin": None, "leakage_by_representation": {},
                    "invalid_reason": "fewer_than_two_eligible_tasks",
                }
            else:
                assigned = mapping[family]
                other = "content" if assigned == "pos" else "pos"
                output[family] = family_summary(recovery, assigned, [other], tasks)
        return output

    inventory: list[dict[str, str]] = []
    leaves = corrected_exact = known_generic_drift = 0
    for job in JOBS:
        stage = CONTINUATION_RUN_ROOT / "k2_refit" / job
        paths = [stage / "point.json", *sorted((stage / "draws").glob("*.json"))]
        if len(paths) != 501:
            raise RuntimeError(f"K2 drift audit leaf inventory changed: {job}")
        for path in paths:
            payload = strict_json(path)
            result = payload["result"]
            corrected = producer_rows(result["recoveries"])
            generic = family_rows(result["recoveries"], mapping, eligible)
            if corrected != result["families"]:
                raise RuntimeError(f"producer-rule family reconstruction mismatch: {path}")
            corrected_exact += 1
            if generic == result["families"]:
                raise RuntimeError(f"expected generic verifier drift disappeared: {path}")
            for family in PRIMARY:
                if family != "relative_structural_position":
                    if generic[family] != result["families"][family]:
                        raise RuntimeError(f"generic verifier drift broadened: {path}/{family}")
                    continue
                repaired = dict(generic[family])
                detail = dict(repaired["leakage_by_representation"])
                if detail.pop("pos", None) != repaired["assigned_recovery"]:
                    raise RuntimeError(f"known verifier drift value changed: {path}")
                repaired["leakage_by_representation"] = detail
                if repaired != result["families"][family]:
                    raise RuntimeError(f"generic verifier drift shape broadened: {path}")
            known_generic_drift += 1
            leaves += 1
            inventory.append({"path": str(path.relative_to(ROOT)), "sha256": sha256_file(path)})
    if leaves != 2004 or corrected_exact != leaves or known_generic_drift != leaves:
        raise RuntimeError("K2 verifier-drift audit count mismatch")
    return {
        "schema_version": "atlas_completion_summary_k2_verifier_drift_v1",
        "registered_leaves": leaves,
        "producer_rule_exact_leaves": corrected_exact,
        "known_generic_drift_leaves": known_generic_drift,
        "known_difference": "relative_structural_position_spurious_assigned_pos_leakage_entry",
        "leaf_inventory_sha256": inventory_digest(inventory),
        "producer_sha256": sha256_file(ROOT / "scripts/run_msae_refit_worker.py"),
        "verifier_sha256": sha256_file(ROOT / "scripts/verify_msae_completion.py"),
    }


def immutable_fingerprint() -> str:
    incident = verify_incident_inputs()
    initial = verify_initial_freeze()
    material = {
        "implementation_inventory": implementation_inventory(),
        "implementation_sha256": inventory_digest(implementation_inventory()),
        "initial_recovery_bundle_sha256": initial["bundle_sha256"],
        "original_continuation_bundle_sha256": incident["original_freeze"]["bundle_sha256"],
        "original_continuation_files": incident["original_freeze"]["bundle_files"],
        "source_inventory_sha256": incident["original_freeze"]["source_inventory_sha256"],
        "child_source_sha256": validate_child_source(),
    }
    return sha256_bytes(canonical_json_bytes(material, newline=False))


def _contention_case(root: Path, kind: str) -> dict[str, Any]:
    target = root / f"{kind}.target"
    sources = [root / f"{kind}.source.{index}" for index in range(2)]
    if kind == "file":
        for index, source in enumerate(sources):
            source.write_bytes(f"source-{index}".encode()); fsync_file(source)
    barrier = root / f"{kind}.barrier"
    child = r'''import errno,os,pathlib,sys,time
kind,source_text,target_text,barrier_text=sys.argv[1:]
source,target,barrier=map(pathlib.Path,(source_text,target_text,barrier_text))
deadline=time.monotonic()+10
while not barrier.exists():
    if time.monotonic()>deadline: raise SystemExit(98)
    time.sleep(0.001)
try:
    os.link(source,target) if kind=="file" else os.mkdir(target,0o700)
except OSError as exc:
    raise SystemExit(17 if exc.errno==errno.EEXIST else 99)
'''
    children = [
        subprocess.Popen([sys.executable, "-c", child, kind, str(source),
                          str(target), str(barrier)])
        for source in sources
    ]
    barrier.write_bytes(b"go\n"); fsync_file(barrier); fsync_directory(root)
    try:
        codes = sorted(process.wait(timeout=15) for process in children)
    except BaseException:
        for process in children:
            if process.poll() is None:
                process.kill()
            process.wait()
        raise
    if codes != [0, 17] or not target.exists():
        raise RuntimeError(f"two-process {kind} no-replace contention failed: {codes}")
    if kind == "file":
        source_facts = [regular_file_facts(path) for path in sources]
        target_facts = regular_file_facts(target)
        winners = [
            index for index, facts in enumerate(source_facts)
            if (facts["st_dev"], facts["st_ino"])
            == (target_facts["st_dev"], target_facts["st_ino"])
            and facts["sha256"] == target_facts["sha256"]
            and facts["size"] == target_facts["size"]
        ]
        if len(winners) != 1:
            raise RuntimeError("two-process file target does not identify one exact winner")
        fsync_file(target)
        outcome = {
            "exit_codes": codes, "target_present": True, "sources_preserved": True,
            "source_sha256": [row["sha256"] for row in source_facts],
            "source_size": [row["size"] for row in source_facts],
            "source_regular": [row["regular"] for row in source_facts],
            "source_st_dev": [row["st_dev"] for row in source_facts],
            "source_st_ino": [row["st_ino"] for row in source_facts],
            "target_sha256": target_facts["sha256"], "target_size": target_facts["size"],
            "target_regular": target_facts["regular"], "winner_index": winners[0],
            "target_st_dev": target_facts["st_dev"], "target_st_ino": target_facts["st_ino"],
            "target_matches_winner": True, "target_same_inode_as_winner": True,
        }
    else:
        target_stat = os.lstat(target)
        if not stat.S_ISDIR(target_stat.st_mode) or target.is_symlink() \
                or list(target.iterdir()):
            raise RuntimeError("two-process directory target is not one empty regular directory")
        fsync_directory(target)
        outcome = {
            "exit_codes": codes, "target_present": True,
            "target_directory": True, "target_empty": True,
            "target_st_dev": int(target_stat.st_dev), "target_st_ino": int(target_stat.st_ino),
        }
    fsync_directory(root)
    return outcome


def _job_lock_capability(job: str, test_root: Path) -> dict[str, bool]:
    guarded = test_root / "guarded_manifest.marker"
    child = r'''import errno,fcntl,os,pathlib,sys
lock,guarded=map(pathlib.Path,sys.argv[1:])
fd=os.open(lock,os.O_RDWR|os.O_CREAT,0o600)
try:
    try: fcntl.flock(fd,fcntl.LOCK_EX|fcntl.LOCK_NB)
    except OSError as exc: raise SystemExit(17 if exc.errno in {errno.EACCES,errno.EAGAIN} else 99)
    guarded.write_text("lock unexpectedly acquired\n",encoding="utf-8")
finally: os.close(fd)
'''
    code = subprocess.run(
        [sys.executable, "-c", child, str(job_lock_path(job)), str(guarded)],
        check=False, timeout=15).returncode
    if code != 17 or guarded.exists():
        raise RuntimeError(f"separate-descriptor job-lock contention failed: {code}")
    return {"separate_descriptor_lost": True, "guarded_manifest_marker_created": False}


def run_filesystem_capability_gate(job: str, attempt_id: str, argv: list[str],
                                   log: str, mode: str) -> dict[str, Any]:
    require_job_lock(job)
    parent = canonical_root().parent
    if not parent.is_dir() or parent.is_symlink():
        raise RuntimeError("capability-test deployment parent is not precreated")
    mount = deployment_mount()
    test_root = parent / f".summary_recovery_capability.{attempt_id}.{uuid.uuid4().hex}"
    test_root.mkdir(mode=0o700)
    passed = False
    try:
        marker = test_root / "fsync.file"
        marker.write_bytes(b"fsync")
        fsync_file(marker); fsync_directory(test_root)
        outcomes: dict[str, Any] = {"file": {}, "directory": {}}
        for kind in ["file", "directory"]:
            source = test_root / f"{kind}.success.source"
            destination = test_root / f"{kind}.success.destination"
            if kind == "file":
                source.write_bytes(b"success"); fsync_file(source)
                os.link(source, destination)
                source_facts = regular_file_facts(source)
                destination_facts = regular_file_facts(destination)
                if (
                    source_facts["sha256"] != destination_facts["sha256"]
                    or source_facts["size"] != destination_facts["size"]
                    or (source_facts["st_dev"], source_facts["st_ino"])
                    != (destination_facts["st_dev"], destination_facts["st_ino"])
                ):
                    raise RuntimeError("file successful hard link did not preserve exact inode/bytes")
                success: dict[str, Any] = {
                    "source_sha256": source_facts["sha256"],
                    "destination_sha256": destination_facts["sha256"],
                    "source_size": source_facts["size"],
                    "destination_size": destination_facts["size"],
                    "source_regular": source_facts["regular"],
                    "destination_regular": destination_facts["regular"],
                    "source_st_dev": source_facts["st_dev"],
                    "source_st_ino": source_facts["st_ino"],
                    "destination_st_dev": destination_facts["st_dev"],
                    "destination_st_ino": destination_facts["st_ino"],
                    "same_inode": True,
                }
            else:
                os.mkdir(destination, 0o700)
                (destination / "marker").write_bytes(b"success")
                fsync_file(destination / "marker"); fsync_directory(destination)
                marker_facts = regular_file_facts(destination / "marker")
                destination_stat = os.lstat(destination)
                if not stat.S_ISDIR(destination_stat.st_mode) or destination.is_symlink():
                    raise RuntimeError("directory successful mkdir did not preserve a regular directory")
                success = {
                    "destination_directory": True,
                    "destination_st_dev": int(destination_stat.st_dev),
                    "destination_st_ino": int(destination_stat.st_ino),
                    "marker_sha256": marker_facts["sha256"],
                    "marker_size": marker_facts["size"], "marker_regular": True,
                }
            fsync_directory(destination) if destination.is_dir() else fsync_file(destination)
            collision_source = test_root / f"{kind}.collision.source"
            collision_destination = test_root / f"{kind}.collision.destination"
            if kind == "file":
                collision_source.write_bytes(b"source"); collision_destination.write_bytes(b"destination")
                fsync_file(collision_source); fsync_file(collision_destination)
                source_before = regular_file_facts(collision_source)
                destination_before = regular_file_facts(collision_destination)
            else:
                collision_destination.mkdir()
                (collision_destination / "marker").write_bytes(b"destination")
                fsync_file(collision_destination / "marker"); fsync_directory(collision_destination)
                marker_before = regular_file_facts(collision_destination / "marker")
                collision_directory_before = os.lstat(collision_destination)
            try:
                if kind == "file":
                    os.link(collision_source, collision_destination)
                else:
                    os.mkdir(collision_destination, 0o700)
            except OSError as exc:
                if exc.errno != errno.EEXIST:
                    raise
            else:
                raise RuntimeError(f"{kind} no-replace collision unexpectedly succeeded")
            if kind == "file":
                source_after = regular_file_facts(collision_source)
                destination_after = regular_file_facts(collision_destination)
                if (
                    source_after != source_before or destination_after != destination_before
                    or (source_after["st_dev"], source_after["st_ino"])
                    == (destination_after["st_dev"], destination_after["st_ino"])
                ):
                    raise RuntimeError("file collision did not preserve exact distinct names")
                collision: dict[str, Any] = {
                    "source_sha256_before": source_before["sha256"],
                    "source_sha256_after": source_after["sha256"],
                    "destination_sha256_before": destination_before["sha256"],
                    "destination_sha256_after": destination_after["sha256"],
                    "source_size_before": source_before["size"],
                    "source_size_after": source_after["size"],
                    "destination_size_before": destination_before["size"],
                    "destination_size_after": destination_after["size"],
                    "source_st_dev_before": source_before["st_dev"],
                    "source_st_dev_after": source_after["st_dev"],
                    "source_st_ino_before": source_before["st_ino"],
                    "source_st_ino_after": source_after["st_ino"],
                    "destination_st_dev_before": destination_before["st_dev"],
                    "destination_st_dev_after": destination_after["st_dev"],
                    "destination_st_ino_before": destination_before["st_ino"],
                    "destination_st_ino_after": destination_after["st_ino"],
                    "source_regular": True, "destination_regular": True,
                    "distinct_inodes": True,
                }
            else:
                destination_stat = os.lstat(collision_destination)
                marker_after = regular_file_facts(collision_destination / "marker")
                if (not stat.S_ISDIR(destination_stat.st_mode)
                        or collision_destination.is_symlink() or marker_after != marker_before
                        or (destination_stat.st_dev, destination_stat.st_ino)
                        != (collision_directory_before.st_dev,
                            collision_directory_before.st_ino)):
                    raise RuntimeError("directory collision did not preserve exact marker bytes")
                collision = {
                    "destination_directory": True,
                    "destination_st_dev_before": int(collision_directory_before.st_dev),
                    "destination_st_dev_after": int(destination_stat.st_dev),
                    "destination_st_ino_before": int(collision_directory_before.st_ino),
                    "destination_st_ino_after": int(destination_stat.st_ino),
                    "marker_sha256_before": marker_before["sha256"],
                    "marker_sha256_after": marker_after["sha256"],
                    "marker_size_before": marker_before["size"],
                    "marker_size_after": marker_after["size"],
                    "marker_regular": True,
                }
            outcomes[kind] = {
                "success": success, "eexist_preserved": collision,
                "two_process": _contention_case(test_root, kind),
            }
        outcomes["job_lock"] = _job_lock_capability(job, test_root)
        fsync_directory(test_root); fsync_directory(parent)
        passed = True
        capability = {
            "schema_version": "atlas_completion_summary_recovery_filesystem_capability_v2",
            "job": job, "attempt_id": attempt_id, "mode": mode, "argv": argv,
            "log": log, "tested_host": os.uname().nodename,
            "mount": mount, "outcomes": outcomes,
            "all_passed": True, "tested_utc": utc_now(),
        }
        validate_capability_payload(capability, job=job, attempt_id=attempt_id)
        return capability
    finally:
        if passed:
            last_error: OSError | None = None
            for _ in range(50):
                try:
                    shutil.rmtree(test_root)
                    last_error = None
                    break
                except OSError as exc:
                    last_error = exc
                    if exc.errno not in {errno.ENOTEMPTY, errno.EBUSY}:
                        raise
                    time.sleep(0.1)
            if last_error is not None or test_root.exists():
                raise last_error or RuntimeError("capability test root cleanup was not observed")
            fsync_directory(parent)


def prepare_attempt_evidence(job: str, attempt_id: str, argv: list[str],
                             log: str, mode: str) -> tuple[str, Path, str]:
    require_job_lock(job)
    capability = run_filesystem_capability_gate(job, attempt_id, argv, log, mode)
    validate_capability_payload(capability, job=job, attempt_id=attempt_id)
    ensure_recovery_directories()
    owner_path = recovery_run_root() / "execution_owner.json"
    if owner_path.is_file():
        owner = verify_execution_owner_mount()
        if owner["mount"] != capability["mount"]:
            raise RuntimeError("recovery execution owner or mount changed")
    else:
        owner = {
            "schema_version": "atlas_completion_summary_recovery_execution_owner_v1",
            "host": socket.gethostname(), "root": str(ROOT.resolve()),
            "mount": capability["mount"], "created_utc": utc_now(),
        }
        write_once_json(owner_path, owner)
        verify_execution_owner_mount()
    owner_sha = sha256_file(owner_path)
    close_orphan_attempts(job)
    if success_path(job).exists():
        raise RuntimeError(f"job already has durable success closure: {job}")
    path = capability_path(job, attempt_id)
    write_once_json(path, capability)
    return owner_sha, path, sha256_file(path)


def _attempt_id() -> str:
    value = os.environ.get("MSAE_RECOVERY_ATTEMPT_ID", "")
    if not value:
        raise RuntimeError("MSAE_RECOVERY_ATTEMPT_ID is required; use the tmux launcher")
    return value


def _write_child_inventory(path: Path, expected: dict[str, dict[str, set[str]]]) -> None:
    payload = {
        "schema_version": "atlas_completion_summary_child_inventory_v1",
        "expected_sources": {
            role: {task: sorted(values) for task, values in tasks.items()}
            for role, tasks in expected.items()
        },
    }
    atomic_write_json(path, payload)


def run_isolated_recompute(output_root: Path, expected: dict[str, dict[str, set[str]]],
                           work_root: Path) -> tuple[dict[str, Any], str]:
    validate_child_source()
    work_root.mkdir(parents=True, exist_ok=False)
    inventory_path = work_root / "expected_sources.json"
    _write_child_inventory(inventory_path, expected)
    env = dict(os.environ)
    scripts = str(ROOT / "scripts")
    env["PYTHONPATH"] = scripts + (os.pathsep + env["PYTHONPATH"] if env.get("PYTHONPATH") else "")
    env["MSAE_SUMMARY_RECOVERY_CHILD"] = "1"
    env["PYTHONWARNINGS"] = "ignore::FutureWarning:transformers.utils.hub"
    completed = subprocess.run(
        [sys.executable, "-c", CHILD_SOURCE, str(inventory_path), str(output_root)],
        cwd=ROOT, env=env, text=True, capture_output=True, check=False,
    )
    atomic_write_bytes(work_root / "child.stdout", completed.stdout.encode("utf-8"))
    atomic_write_bytes(work_root / "child.stderr", completed.stderr.encode("utf-8"))
    if completed.returncode != 0:
        raise RuntimeError(
            f"isolated frozen summarizer failed with {completed.returncode}: {completed.stderr[-4000:]}")
    if completed.stdout or completed.stderr:
        raise RuntimeError("isolated frozen summarizer emitted unexpected stdout/stderr")
    result = strict_json(output_root / "diagnostic_results.json")
    report = (output_root / "diagnostic_results.md").read_text(encoding="utf-8")
    validate_result_contract(result)
    if not report.startswith("# Atlas completion diagnostic continuation results\n"):
        raise RuntimeError("frozen diagnostic report contract drift")
    return result, report


def _candidate_terminal(stage: Path, result: dict[str, Any], initial: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema_version": "atlas_completion_summary_recovery_candidate_terminal_v1",
        "canonical": False,
        "candidate_content_sha256": content_digest(stage),
        "completion_bundle_sha256": config()["original_continuation_bundle_sha256"],
        "recovery_bundle_sha256": initial["bundle_sha256"],
        "result_sha256": sha256_file(stage / "diagnostic_results.json"),
        "report_sha256": sha256_file(stage / "diagnostic_results.md"),
        "source_lineage_sha256": sha256_file(stage / "source_lineage.json"),
        "diagnostic_continuation_only": True,
        "decision_promotion_allowed": False,
        "ended_utc": utc_now(),
    }


def _canonical_envelopes(stage: Path, candidate: dict[str, Any], initial: dict[str, Any],
                         promotion: dict[str, Any]) -> tuple[dict[str, Any], str, dict[str, Any]]:
    now = utc_now()
    provenance = {
        "schema_version": "atlas_completion_summary_recovery_provenance_v1",
        "candidate_content_sha256": candidate["content_sha256"],
        "candidate_terminal_sha256": candidate["terminal_sha256"],
        "completion_bundle_sha256": config()["original_continuation_bundle_sha256"],
        "recovery_bundle_sha256": initial["bundle_sha256"],
        "promotion_bundle_sha256": promotion["bundle_sha256"],
        "failed_summarize_terminal_sha256": config()["failed_summarize_terminal_sha256"],
        "failed_summarize_log_sha256": config()["failed_summarize_log_sha256"],
        "diagnostic_continuation_only": True,
        "decision_promotion_allowed": False,
        "published_utc": now,
    }
    atomic_write_json(stage / "RECOVERY_PROVENANCE.json", provenance)
    complete = candidate["result"]["limitations"]["all_diagnostic_stages_complete"] is True
    terminal_name = "MEASUREMENT_COMPLETE.json" if complete else "FROZEN_EQUIVOCAL_STOP.json"
    terminal = {
        "schema_version": "atlas_completion_summary_recovery_canonical_terminal_v1",
        "terminal_state": "measurement_complete" if complete else "frozen_equivocal_stop",
        "reason": None if complete else "one_or_more_diagnostics_stopped_or_unavailable",
        "result_sha256": sha256_file(stage / "diagnostic_results.json"),
        "report_sha256": sha256_file(stage / "diagnostic_results.md"),
        "source_lineage_sha256": sha256_file(stage / "source_lineage.json"),
        "recovery_provenance_sha256": sha256_file(stage / "RECOVERY_PROVENANCE.json"),
        "candidate_content_sha256": candidate["content_sha256"],
        "candidate_terminal_sha256": candidate["terminal_sha256"],
        "completion_bundle_sha256": config()["original_continuation_bundle_sha256"],
        "recovery_bundle_sha256": initial["bundle_sha256"],
        "promotion_bundle_sha256": promotion["bundle_sha256"],
        "failed_summarize_terminal_sha256": config()["failed_summarize_terminal_sha256"],
        "failed_summarize_log_sha256": config()["failed_summarize_log_sha256"],
        "diagnostic_continuation_only": True,
        "decision_promotion_allowed": False,
        "evidence_class": "postscore_amended_architecture_evidence",
        "ended_utc": now,
    }
    return provenance, terminal_name, terminal


def _state_binding(stage: Path, destination: Path,
                   initial: dict[str, Any], promotion: dict[str, Any] | None,
                   publication_attempt_id: str,
                   publication_inventory: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "phase": "ready_to_publish",
        "publication_attempt_id": publication_attempt_id,
        "staging": str(stage.relative_to(ROOT)),
        "destination": str(destination.relative_to(ROOT)),
        "destination_root_sha256": root_digest(stage),
        "staging_inventory": root_inventory(stage),
        "publication_inventory": publication_inventory,
        "published_files": [],
        "root_reservation_attempted": False,
        "root_reservation_confirmed": False,
        "destination_st_dev": None, "destination_st_ino": None,
        "initial_recovery_bundle_sha256": initial["bundle_sha256"],
        "promotion_bundle_sha256": None if promotion is None else promotion["bundle_sha256"],
        "parent_fsync_complete": False,
    }


def _validate_for_job(job: str, root: Path) -> dict[str, Any]:
    return (validate_candidate(root, require_success=False) if job == "candidate"
            else validate_canonical(root, require_success=False))


def _ordered_publication_inventory(job: str, stage: Path) -> list[dict[str, Any]]:
    if job == "candidate":
        names = ["diagnostic_results.json", "diagnostic_results.md", "source_lineage.json",
                 "CANDIDATE_COMPLETE.json"]
    else:
        terminals = [name for name in ["FROZEN_EQUIVOCAL_STOP.json", "MEASUREMENT_COMPLETE.json"]
                     if (stage / name).is_file()]
        if len(terminals) != 1:
            raise RuntimeError("canonical stage lacks exactly one scientific terminal")
        names = ["diagnostic_results.json", "diagnostic_results.md", "source_lineage.json",
                 "RECOVERY_PROVENANCE.json", terminals[0]]
    if {path.name for path in stage.iterdir()} != set(names):
        raise RuntimeError("staged result inventory differs from terminal-last contract")
    if any(not (stage / name).is_file() or (stage / name).is_symlink() for name in names):
        raise RuntimeError("staged result inventory contains a nonregular entry")
    return [
        {"path": name, "sha256": sha256_file(stage / name),
         "size": (stage / name).stat().st_size}
        for name in names
    ]


def _validate_complete_stage(stage: Path, inventory: list[dict[str, Any]],
                             staging_inventory: list[dict[str, Any]],
                             destination_digest: str) -> None:
    if not stage.is_dir() or stage.is_symlink():
        raise RuntimeError("staged publication root is not a regular directory")
    paths = list(stage.iterdir())
    if len(paths) != len(inventory) or {path.name for path in paths} != {
            item["path"] for item in inventory}:
        raise RuntimeError("staged publication name inventory changed")
    observed: list[dict[str, Any]] = []
    for path in sorted(paths, key=lambda item: item.name):
        facts = regular_file_facts(path)
        observed.append({"path": path.name, "sha256": facts["sha256"], "size": facts["size"]})
    if observed != staging_inventory or inventory_digest(observed) != destination_digest:
        raise RuntimeError("staged publication byte inventory changed")


def _validate_link_pair(source: Path, final: Path, item: dict[str, Any]) -> None:
    source_facts = regular_file_facts(source)
    final_facts = regular_file_facts(final)
    if (
        source_facts["sha256"] != item["sha256"]
        or source_facts["size"] != item["size"]
        or final_facts["sha256"] != item["sha256"]
        or final_facts["size"] != item["size"]
        or (source_facts["st_dev"], source_facts["st_ino"])
        != (final_facts["st_dev"], final_facts["st_ino"])
    ):
        raise RuntimeError(f"publication names do not bind one exact staged inode: {final}")


def _reserve_result_root(path: Path) -> None:
    os.mkdir(path, 0o700)


def _reserve_root_with_witness(path: Path) -> os.stat_result:
    """Return an inode witness only when mkdir and both durability checks return."""

    _reserve_result_root(path)
    owned_fd, owned_stat = _open_result_root(path, fsync=True)
    os.close(owned_fd)
    fsync_directory(path)
    fsync_directory(path.parent)
    check_fd, _ = _open_result_root(path, (owned_stat.st_dev, owned_stat.st_ino))
    os.close(check_fd)
    return owned_stat


def _open_result_root(path: Path, expected: tuple[int, int] | None = None,
                      *, fsync: bool = False) -> tuple[int, os.stat_result]:
    flags = os.O_RDONLY | getattr(os, "O_DIRECTORY", 0) | getattr(os, "O_NOFOLLOW", 0)
    fd = os.open(path, flags)
    try:
        opened = os.fstat(fd)
        named = os.lstat(path)
        if (
            not stat.S_ISDIR(opened.st_mode) or not stat.S_ISDIR(named.st_mode)
            or (opened.st_dev, opened.st_ino) != (named.st_dev, named.st_ino)
            or (expected is not None
                and (opened.st_dev, opened.st_ino) != expected)
        ):
            raise RuntimeError("result-root pathname does not bind the owned directory inode")
        if fsync:
            os.fsync(fd)
        return fd, opened
    except BaseException:
        os.close(fd)
        raise


def _validate_owned_result_root(path: Path, binding: dict[str, Any],
                                *, fsync: bool = False) -> None:
    expected = (int(binding["destination_st_dev"]), int(binding["destination_st_ino"]))
    fd, _ = _open_result_root(path, expected, fsync=fsync)
    os.close(fd)


def _link_result_file(source: Path, final: Path, destination_fd: int | None = None) -> None:
    if destination_fd is None:
        os.link(source, final)
    else:
        os.link(source, final.name, dst_dir_fd=destination_fd, follow_symlinks=False)


def _link_into_owned_result(source: Path, final: Path, destination: Path,
                            binding: dict[str, Any]) -> None:
    expected = (int(binding["destination_st_dev"]), int(binding["destination_st_ino"]))
    fd, _ = _open_result_root(destination, expected)
    try:
        _link_result_file(source, final, fd)
    finally:
        os.close(fd)


def _test_sigkill(point: str) -> None:
    del point


def _continue_reserved_publication(job: str, attempt: str, stage: Path,
                                   destination: Path, binding: dict[str, Any]) -> None:
    inventory = list(binding["publication_inventory"])
    _validate_complete_stage(
        stage, inventory, binding["staging_inventory"], binding["destination_root_sha256"])
    expected_order = [item["path"] for item in inventory]
    current = read_state_chain(job)
    recovering = (
        current is not None and current.get("active_attempt_id") == attempt
        and current.get("phase") == "reconciling"
    )
    # Any failed/ambiguous reservation is permanently non-owned.  Record it in
    # the fail-closed reconciliation phase rather than manufacturing a reusable
    # ready state with `root_reservation_attempted=True`.
    unowned_phase = "reconciling"

    confirmed = binding.get("root_reservation_confirmed") is True
    attempted = binding.get("root_reservation_attempted") is True
    if not confirmed:
        if attempted or destination.exists():
            append_state(job, attempt, {
                **binding, "phase": unowned_phase,
                "root_reservation_attempted": True,
                "root_reservation_confirmed": False,
                "error_type": "FileExistsError",
                "error_message": "root ownership is absent for an existing/attempted reservation",
                "error_errno": errno.EEXIST,
            })
            raise FileExistsError(errno.EEXIST, "unowned result-root reservation", str(destination))
        try:
            _test_sigkill("before_root_reservation")
            owned_stat = _reserve_root_with_witness(destination)
        except (OSError, RuntimeError) as exc:
            append_state(job, attempt, {
                **binding, "phase": unowned_phase,
                "root_reservation_attempted": True,
                "root_reservation_confirmed": False,
                "error_type": type(exc).__name__, "error_message": str(exc),
                "error_errno": exc.errno if isinstance(exc, OSError) else None,
            })
            if isinstance(exc, OSError) and exc.errno == errno.EEXIST:
                raise FileExistsError(
                    errno.EEXIST, "mkdir did not return success", str(destination)) from exc
            raise
        binding = {
            **binding, "root_reservation_attempted": True,
            "root_reservation_confirmed": True,
            "destination_st_dev": int(owned_stat.st_dev),
            "destination_st_ino": int(owned_stat.st_ino),
        }
        append_state(job, attempt, {
            **binding, "phase": "root_reserved",
            "published_files": list(binding.get("published_files", [])),
        })
    _validate_owned_result_root(destination, binding)

    actual_paths = list(destination.iterdir())
    if any(not path.is_file() or path.is_symlink() for path in actual_paths):
        raise FileExistsError(errno.EEXIST, "reserved result root has nonregular entries", str(destination))
    actual_names = {path.name for path in actual_paths}
    prefix_lengths = [
        length for length in range(len(expected_order) + 1)
        if actual_names == set(expected_order[:length])
    ]
    if len(prefix_lengths) != 1:
        raise FileExistsError(errno.EEXIST, "reserved result root is not an ordered prefix", str(destination))
    state_prefix = list(binding.get("published_files", []))
    if expected_order[:len(state_prefix)] != state_prefix or prefix_lengths[0] < len(state_prefix):
        raise FileExistsError(errno.EEXIST, "reserved result root precedes journaled prefix", str(destination))

    published: list[str] = list(state_prefix)
    for index, item in enumerate(inventory):
        source, final = stage / item["path"], destination / item["path"]
        if index < len(state_prefix):
            try:
                _validate_link_pair(source, final, item)
                _validate_complete_stage(
                    stage, inventory, binding["staging_inventory"],
                    binding["destination_root_sha256"])
            except (OSError, RuntimeError) as exc:
                raise FileExistsError(
                    errno.EEXIST, "journaled publication prefix changed", str(final)) from exc
            fsync_file(final)
            _validate_link_pair(source, final, item)
            _validate_complete_stage(
                stage, inventory, binding["staging_inventory"],
                binding["destination_root_sha256"])
            _validate_owned_result_root(destination, binding, fsync=True)
            fsync_directory(destination)
            _validate_owned_result_root(destination, binding)
            continue
        link_error: OSError | None = None
        if not final.exists() and not final.is_symlink():
            try:
                _link_into_owned_result(source, final, destination, binding)
            except OSError as exc:
                link_error = exc
        try:
            _validate_link_pair(source, final, item)
            _validate_complete_stage(
                stage, inventory, binding["staging_inventory"],
                binding["destination_root_sha256"])
        except (OSError, RuntimeError) as validation_error:
            append_state(job, attempt, {
                **binding,
                "phase": ("reconciling" if recovering else
                          ("root_reserved" if not published else "files_publishing")),
                "published_files": published,
                "error_type": type(link_error or validation_error).__name__,
                "error_message": str(link_error or validation_error),
                "error_errno": link_error.errno if link_error is not None else None,
            })
            raise link_error or validation_error
        fsync_file(final)
        _validate_link_pair(source, final, item)
        _validate_complete_stage(
            stage, inventory, binding["staging_inventory"], binding["destination_root_sha256"])
        _validate_owned_result_root(destination, binding, fsync=True)
        fsync_directory(destination)
        _validate_owned_result_root(destination, binding)
        _validate_link_pair(source, final, item)
        _validate_complete_stage(
            stage, inventory, binding["staging_inventory"], binding["destination_root_sha256"])
        published.append(item["path"])
        append_state(job, attempt, {
            **binding,
            "phase": "terminal_published" if len(published) == len(inventory)
            else "files_publishing",
            "published_files": list(published),
            "error_type": None if link_error is None else type(link_error).__name__,
            "error_message": None if link_error is None else str(link_error),
            "error_errno": None if link_error is None else link_error.errno,
        })
    _validate_complete_stage(
        stage, inventory, binding["staging_inventory"], binding["destination_root_sha256"])
    _validate_for_job(job, destination)
    if root_digest(destination) != binding["destination_root_sha256"]:
        raise RuntimeError("completed reserved result root digest mismatch")
    _validate_owned_result_root(destination, binding, fsync=True)
    fsync_directory(destination)
    _validate_owned_result_root(destination, binding)
    _validate_complete_stage(
        stage, inventory, binding["staging_inventory"], binding["destination_root_sha256"])
    _validate_for_job(job, destination)
    append_state(job, attempt, {
        **binding, "phase": "destination_fsync_complete",
        "published_files": list(published), "parent_fsync_complete": False,
    })
    _validate_complete_stage(
        stage, inventory, binding["staging_inventory"], binding["destination_root_sha256"])
    fsync_directory(destination.parent)
    _validate_owned_result_root(destination, binding)
    _validate_complete_stage(
        stage, inventory, binding["staging_inventory"], binding["destination_root_sha256"])
    _validate_for_job(job, destination)
    append_state(job, attempt, {
        **binding, "phase": "parent_fsync_complete",
        "published_files": list(published), "parent_fsync_complete": True,
    })
    _test_sigkill("after_parent_fsync_state")


def _publish_stage(job: str, stage: Path, destination: Path,
                   initial: dict[str, Any], promotion: dict[str, Any] | None) -> None:
    attempt = _attempt_id()
    _validate_for_job(job, stage)
    fsync_tree(stage)
    fsync_directory(stage.parent)
    inventory = _ordered_publication_inventory(job, stage)
    binding = _state_binding(stage, destination, initial, promotion, attempt, inventory)
    append_state(job, attempt, binding)
    _continue_reserved_publication(job, attempt, stage, destination, binding)


def _record_error(job: str, exc: BaseException) -> None:
    try:
        require_job_lock(job)
        attempt = _attempt_id()
        head = read_state_chain(job)
        if head is None or head["active_attempt_id"] != attempt:
            return
        append_state(job, attempt, {
            "phase": head["phase"], "parent_fsync_complete": head["parent_fsync_complete"],
            "error_type": type(exc).__name__, "error_message": str(exc),
            "error_errno": exc.errno if isinstance(exc, OSError) else None,
        })
    except BaseException:
        return


RECONCILABLE_PHASES = {
    "ready_to_publish", "reconciling", "root_reserved", "files_publishing",
    "terminal_published", "destination_fsync_complete", "parent_fsync_complete",
}


def _create_staging_directory(path: Path) -> None:
    path.mkdir(parents=False, exist_ok=False, mode=0o700)
    fsync_directory(path)
    fsync_directory(path.parent)
    row = os.lstat(path)
    if not stat.S_ISDIR(row.st_mode) or path.is_symlink():
        raise RuntimeError("staging directory changed during durable creation")


def run_candidate() -> dict[str, Any]:
    require_job_lock("candidate")
    initial = verify_initial_freeze()
    destination = candidate_root()
    if success_path("candidate").exists():
        raise RuntimeError("candidate already has durable success closure")
    attempt = _attempt_id()
    prior = read_state_chain("candidate")
    if prior is not None:
        raise RuntimeError("candidate job already has durable state; use explicit reconciliation")
    stage = destination.parent / f".completion_diagnostic_candidate.staging.{attempt}.{uuid.uuid4().hex}"
    work = recovery_run_root() / "work" / f"candidate.{attempt}.{uuid.uuid4().hex}"
    _create_staging_directory(stage)
    append_state("candidate", attempt, {
        "phase": "building", "publication_attempt_id": attempt,
        "staging": str(stage.relative_to(ROOT)),
        "destination": str(destination.relative_to(ROOT)), "parent_fsync_complete": False,
        "initial_recovery_bundle_sha256": initial["bundle_sha256"],
        "promotion_bundle_sha256": None,
    }, claim=True)
    if destination.exists():
        raise FileExistsError(errno.EEXIST, "candidate destination already exists", str(destination))
    before = immutable_fingerprint()
    expected, lineage = resolve_expected_sources()
    lineage["k2_family_verifier_drift"] = verify_k2_family_drift_contract()
    result, _ = run_isolated_recompute(stage, expected, work)
    after = immutable_fingerprint()
    if before != after:
        raise RuntimeError("immutable recovery/source fingerprint changed across child replay")
    atomic_write_json(stage / "source_lineage.json", lineage)
    atomic_write_json(stage / "CANDIDATE_COMPLETE.json", _candidate_terminal(stage, result, initial))
    _publish_stage("candidate", stage, destination, initial, None)
    return {"published": "candidate", "root_sha256": root_digest(destination),
            "content_sha256": content_digest(destination)}


def _replay_candidate_bytes(root: Path) -> dict[str, Any]:
    verify_execution_owner_mount()
    candidate = validate_candidate(root, require_success=True)
    attempt = f"verify.{uuid.uuid4().hex}"
    replay = recovery_run_root() / "verification" / attempt
    output = replay / "output"
    work = replay / "work"
    output.mkdir(parents=True, exist_ok=False)
    before = immutable_fingerprint()
    try:
        expected, lineage = resolve_expected_sources()
        lineage["k2_family_verifier_drift"] = verify_k2_family_drift_contract()
        run_isolated_recompute(output, expected, work)
        atomic_write_json(output / "source_lineage.json", lineage)
        for name in ["diagnostic_results.json", "diagnostic_results.md", "source_lineage.json"]:
            if (output / name).read_bytes() != (root / name).read_bytes():
                raise RuntimeError(f"candidate differs from fresh frozen replay: {name}")
    finally:
        after = immutable_fingerprint()
        if replay.exists():
            shutil.rmtree(replay)
    if before != after:
        raise RuntimeError("immutable fingerprint changed during candidate verification")
    return candidate


def verify_candidate_replay() -> dict[str, Any]:
    row = _replay_candidate_bytes(candidate_root())
    return {"verified": True, "candidate_content_sha256": row["content_sha256"],
            "candidate_terminal_sha256": row["terminal_sha256"]}


def run_publish() -> dict[str, Any]:
    require_job_lock("publish")
    initial = verify_initial_freeze()
    promotion = verify_promotion_freeze()
    candidate = _replay_candidate_bytes(candidate_root())
    destination = canonical_root()
    if success_path("publish").exists():
        raise RuntimeError("canonical publication already has durable success closure")
    attempt = _attempt_id()
    prior = read_state_chain("publish")
    if prior is not None:
        raise RuntimeError("publish job already has durable state; use explicit reconciliation")
    stage = destination.parent / f".completion_diagnostic_publish.staging.{attempt}.{uuid.uuid4().hex}"
    _create_staging_directory(stage)
    append_state("publish", attempt, {
        "phase": "building", "publication_attempt_id": attempt,
        "staging": str(stage.relative_to(ROOT)),
        "destination": str(destination.relative_to(ROOT)), "parent_fsync_complete": False,
        "initial_recovery_bundle_sha256": initial["bundle_sha256"],
        "promotion_bundle_sha256": promotion["bundle_sha256"],
    }, claim=True)
    if destination.exists():
        raise FileExistsError(errno.EEXIST, "canonical destination already exists", str(destination))
    for name in ["diagnostic_results.json", "diagnostic_results.md", "source_lineage.json"]:
        atomic_write_bytes(stage / name, (candidate_root() / name).read_bytes())
        if (stage / name).read_bytes() != (candidate_root() / name).read_bytes():
            raise RuntimeError(f"canonical staged bytes differ from reviewed candidate: {name}")
    if content_inventory(stage) != promotion["bundle_material"]["candidate_files"]:
        raise RuntimeError("canonical staged content inventory differs from promotion freeze")
    _, terminal_name, terminal = _canonical_envelopes(stage, candidate, initial, promotion)
    atomic_write_json(stage / terminal_name, terminal)
    _publish_stage("publish", stage, destination, initial, promotion)
    return {"published": "canonical", "root_sha256": root_digest(destination),
            "terminal": terminal_name}


def reconcile(job: str) -> dict[str, Any]:
    require_job_lock(job)
    initial = verify_initial_freeze()
    promotion = verify_promotion_freeze() if job == "publish" else None
    destination = candidate_root() if job == "candidate" else canonical_root()
    if success_path(job).exists():
        raise RuntimeError(f"{job} already has durable success closure")
    state = read_state_chain(job)
    if state is None:
        raise RuntimeError(f"{job} has no durable publication state")
    expected_promotion = None if promotion is None else promotion["bundle_sha256"]
    if (
        state.get("job") != job
        or state.get("phase") not in RECONCILABLE_PHASES
        or state.get("destination") != str(destination.relative_to(ROOT))
        or state.get("initial_recovery_bundle_sha256") != initial["bundle_sha256"]
        or state.get("promotion_bundle_sha256") != expected_promotion
    ):
        raise RuntimeError(f"{job} state is not an exact reconcilable publication")
    stage = ROOT / str(state.get("staging", ""))
    try:
        stage.relative_to(destination.parent)
    except ValueError as exc:
        raise RuntimeError("recovery staging path is outside destination parent") from exc
    if stage.is_symlink():
        raise RuntimeError("recovery staging path is a symlink")
    attempt = _attempt_id()
    publication_attempt = state["publication_attempt_id"]
    _validate_for_job(job, stage)
    inventory = _ordered_publication_inventory(job, stage)
    if (
        inventory != state.get("publication_inventory")
        or root_inventory(stage) != state.get("staging_inventory")
        or root_digest(stage) != state.get("destination_root_sha256")
    ):
        raise RuntimeError("recovery staging differs from the durable ready inventory")
    append_state(job, attempt, {
        "phase": "reconciling", "publication_attempt_id": publication_attempt,
        "staging": state["staging"], "destination": state["destination"],
        "destination_root_sha256": state["destination_root_sha256"],
        "staging_inventory": state["staging_inventory"],
        "publication_inventory": inventory,
        "published_files": state["published_files"],
        "root_reservation_attempted": state["root_reservation_attempted"],
        "root_reservation_confirmed": state["root_reservation_confirmed"],
        "destination_st_dev": state["destination_st_dev"],
        "destination_st_ino": state["destination_st_ino"],
        "initial_recovery_bundle_sha256": state["initial_recovery_bundle_sha256"],
        "promotion_bundle_sha256": state["promotion_bundle_sha256"],
        "parent_fsync_complete": False,
    }, claim=True)
    binding = {
        "phase": "ready_to_publish", "publication_attempt_id": publication_attempt,
        "staging": state["staging"], "destination": state["destination"],
        "destination_root_sha256": state["destination_root_sha256"],
        "staging_inventory": state["staging_inventory"],
        "publication_inventory": inventory,
        "published_files": state["published_files"],
        "root_reservation_attempted": state["root_reservation_attempted"],
        "root_reservation_confirmed": state["root_reservation_confirmed"],
        "destination_st_dev": state["destination_st_dev"],
        "destination_st_ino": state["destination_st_ino"],
        "initial_recovery_bundle_sha256": state["initial_recovery_bundle_sha256"],
        "promotion_bundle_sha256": state["promotion_bundle_sha256"],
        "parent_fsync_complete": False,
    }
    if state["root_reservation_confirmed"] is not True and (
        state["root_reservation_attempted"] is True or destination.exists()
    ):
        append_state(job, attempt, {
            **binding, "phase": "reconciling",
            "error_type": "FileExistsError",
            "error_message": "reconciliation lacks durable root ownership",
            "error_errno": errno.EEXIST,
        })
        raise FileExistsError(errno.EEXIST, "unowned recovery destination", str(destination))
    if state["root_reservation_confirmed"] is True and not destination.is_dir():
        raise RuntimeError("owned recovery destination is absent")
    _continue_reserved_publication(job, attempt, stage, destination, binding)
    return {"reconciled": job, "root_sha256": root_digest(destination)}


def verify_canonical_replay() -> dict[str, Any]:
    candidate = _replay_candidate_bytes(candidate_root())
    canonical = validate_canonical(canonical_root(), require_success=True)
    return {
        "verified": True, "candidate_content_sha256": candidate["content_sha256"],
        "canonical_root_sha256": canonical["root_sha256"],
        "terminal_state": canonical["terminal"]["terminal_state"],
    }


class SupervisorInterrupted(RuntimeError):
    def __init__(self, signum: int) -> None:
        super().__init__(f"recovery supervisor received signal {signum}")
        self.signum = signum


def _open_supervisor_log(relative: str):
    if Path(relative).is_absolute() or ".." in Path(relative).parts:
        raise RuntimeError("supervisor log path is not a safe project-relative path")
    path = ROOT / relative
    try:
        path.relative_to(recovery_run_root() / "logs")
    except ValueError as exc:
        raise RuntimeError("supervisor log is outside the recovery log root") from exc
    flags = os.O_WRONLY | os.O_APPEND | os.O_CREAT | getattr(os, "O_NOFOLLOW", 0)
    fd = os.open(path, flags, 0o600)
    row = os.fstat(fd)
    if not stat.S_ISREG(row.st_mode):
        os.close(fd)
        raise RuntimeError("supervisor log is not a regular file")
    os.fsync(fd)
    fsync_directory(path.parent)
    return path, os.fdopen(fd, "a", encoding="utf-8")


def supervise(job: str, attempt_id: str, mode: str, log: str, closure_log: str,
              argv: list[str]) -> dict[str, Any]:
    """Run one whole attempt under one process and one open-file-description lock."""

    if job not in {"candidate", "publish"} or mode not in {"run", "reconcile"}:
        raise ValueError("invalid supervised recovery attempt")
    if not ATTEMPT_RE.fullmatch(attempt_id):
        raise ValueError("invalid supervised recovery attempt ID")
    expected_mode = "reconcile" if mode == "reconcile" else "run"
    ensure_recovery_directories()
    log_path, log_handle = _open_supervisor_log(log)
    closure_path, closure_handle = _open_supervisor_log(closure_log)
    old_attempt = os.environ.get("MSAE_RECOVERY_ATTEMPT_ID")
    os.environ["MSAE_RECOVERY_ATTEMPT_ID"] = attempt_id
    saved_handlers: dict[int, Any] = {}
    saved_error: BaseException | None = None
    closure_error: BaseException | None = None
    output: dict[str, Any] | None = None
    terminal: dict[str, Any] | None = None
    exit_code = 1

    def interrupted(signum: int, _frame: Any) -> None:
        raise SupervisorInterrupted(signum)

    try:
        with supervisor_job_lock(job):
            for signum in [signal.SIGINT, signal.SIGTERM, signal.SIGHUP]:
                saved_handlers[signum] = signal.getsignal(signum)
                signal.signal(signum, interrupted)
            try:
                owner_sha, capability_file, capability_sha = prepare_attempt_evidence(
                    job, attempt_id, argv, log, expected_mode)
                _test_sigkill("after_capability_before_manifest")
                create_attempt(
                    job, attempt_id, argv, log, expected_mode,
                    execution_owner_sha256=owner_sha,
                    capability_path=str(capability_file.relative_to(ROOT)),
                    capability_sha256=capability_sha,
                )
                with contextlib.redirect_stdout(log_handle), contextlib.redirect_stderr(log_handle):
                    if job == "candidate" and mode == "run":
                        output = run_candidate()
                    elif job == "publish" and mode == "run":
                        output = run_publish()
                    else:
                        output = reconcile(job)
                    print(json.dumps(output, sort_keys=True, allow_nan=False), flush=True)
                exit_code = 0
            except BaseException as exc:
                saved_error = exc
                exit_code = 128 + exc.signum if isinstance(exc, SupervisorInterrupted) else 1
                log_handle.write("".join(traceback.format_exception(exc)))
                log_handle.flush()
                _record_error(job, exc)
            finally:
                log_handle.flush()
                os.fsync(log_handle.fileno())
                capability_file = capability_path(job, attempt_id)
                try:
                    if capability_file.is_file():
                        manifest = recovery_run_root() / "job_manifests" / \
                            f"{job}.{attempt_id}.manifest.json"
                        if manifest.is_file():
                            terminal = close_attempt(job, attempt_id, exit_code)
                        else:
                            close_orphan_attempts(job)
                            terminal_path = recovery_run_root() / "job_manifests" / \
                                f"{job}.{attempt_id}.terminal.json"
                            terminal = strict_json(terminal_path) if terminal_path.is_file() else None
                except BaseException as exc:
                    closure_error = exc
                closure_handle.write(json.dumps({
                    "attempt_id": attempt_id, "job": job, "mode": mode,
                    "scientific_exit_code": exit_code,
                    "terminal_outcome": None if terminal is None else terminal.get("outcome"),
                    "closure_error": None if closure_error is None else {
                        "type": type(closure_error).__name__, "message": str(closure_error)},
                    "ended_utc": utc_now(),
                }, sort_keys=True, allow_nan=False) + "\n")
                closure_handle.flush()
                os.fsync(closure_handle.fileno())
                fsync_directory(closure_path.parent)
                for signum, handler in saved_handlers.items():
                    signal.signal(signum, handler)
    finally:
        log_handle.close()
        closure_handle.close()
        if old_attempt is None:
            os.environ.pop("MSAE_RECOVERY_ATTEMPT_ID", None)
        else:
            os.environ["MSAE_RECOVERY_ATTEMPT_ID"] = old_attempt
    if closure_error is not None:
        raise RuntimeError("supervisor could not durably close its attempt") from closure_error
    if saved_error is not None:
        raise saved_error
    if terminal is None or terminal.get("outcome") not in {"success", "reconciled"}:
        raise RuntimeError("supervisor scientific command did not produce a successful closure")
    if output is None:
        raise RuntimeError("supervisor completed without scientific output")
    return output


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=[
        "supervise", "verify-candidate", "verify-only",
    ])
    parser.add_argument("--job", choices=["candidate", "publish"])
    parser.add_argument("--attempt-id")
    parser.add_argument("--mode", choices=["run", "reconcile"])
    parser.add_argument("--log")
    parser.add_argument("--closure-log")
    args = parser.parse_args()
    try:
        if args.command == "supervise":
            if None in {args.job, args.attempt_id, args.mode, args.log, args.closure_log}:
                parser.error("supervise requires job, attempt-id, mode, log, and closure-log")
            output = supervise(
                str(args.job), str(args.attempt_id), str(args.mode), str(args.log),
                str(args.closure_log), [sys.executable, *sys.argv],
            )
        elif args.command == "verify-candidate":
            output = verify_candidate_replay()
        else:
            output = verify_canonical_replay()
        print(json.dumps(output, sort_keys=True, allow_nan=False))
    except BaseException:
        raise


if __name__ == "__main__":
    main()
