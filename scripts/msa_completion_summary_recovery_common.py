#!/usr/bin/env python3
"""Fail-closed helpers for the atlas diagnostic-summary recovery."""
from __future__ import annotations

import errno
import fcntl
import hashlib
import json
import os
import re
import secrets
import socket
import stat
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

import numpy as np

from msa_completion_common import (
    ROOT,
    atomic_write_json,
    load_activation,
    load_row_file,
    sha256_file,
)
from msa_completion_continuation_common import (
    JOBS,
    RUN_ROOT as CONTINUATION_RUN_ROOT,
    continuation_firewall,
    verify_continuation_freeze,
    verify_fixed_source_hashes,
    verify_source_inventory,
)
from collect_msae_completion_continuation import validate_collection

CONFIG = ROOT / "configs/atlas_completion_summary_recovery/analysis.json"
INITIAL_FREEZE = ROOT / "configs/atlas_completion_summary_recovery/freeze_record.json"
PROMOTION_FREEZE = ROOT / "configs/atlas_completion_summary_recovery/promotion_freeze_record.json"
IMPLEMENTATION_REVIEW = ROOT / "reports/adversarial/atlas_completion_summary_recovery_implementation_review_20260802.json"
RESULT_REVIEW = ROOT / "reports/adversarial/atlas_completion_summary_recovery_result_review_20260802.json"
CLAIM_REVIEW = ROOT / "reports/adversarial/atlas_completion_summary_recovery_claim_review_20260802.json"

PRIMARY = {
    "absolute_position": ["abs_pos_16", "abs_pos_8"],
    "relative_structural_position": [
        "relative_quartile", "head_signed_distance", "dependency_depth", "boundary_state"
    ],
    "lexical_semantic_content": ["token_identity_256", "lemma_identity_256", "ner_coarse"],
}
TASKS = [task for tasks in PRIMARY.values() for task in tasks]
ROLES = ["calibration", "C1", "C2"]

MOUNT_KEYS = {
    "mount_id", "parent_mount_id", "major_minor", "mount_point",
    "mount_options", "filesystem_type", "source", "super_options",
    "target", "st_dev",
}

IMPLEMENTATION_FILES = [
    "configs/atlas_completion_summary_recovery/analysis.json",
    "docs/rfc-atlas-v1-diagnostic-summary-recovery.md",
    "scripts/msa_completion_summary_recovery_common.py",
    "scripts/freeze_msae_completion_summary_recovery.py",
    "scripts/freeze_msae_completion_summary_promotion.py",
    "scripts/recover_msae_completion_continuation_summary.py",
    "scripts/launch_msae_completion_summary_recovery_tmux.sh",
    "tests/test_msae_completion_summary_recovery.py",
]


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _require_aware_timestamp(value: Any, label: str) -> None:
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError as exc:
        raise RuntimeError(f"{label} timestamp is invalid") from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise RuntimeError(f"{label} timestamp is not timezone-aware")


def strict_json(path: Path) -> Any:
    payload, _ = _regular_file_bytes(path)
    return json.loads(
        payload.decode("utf-8"),
        parse_constant=lambda value: (_ for _ in ()).throw(
            ValueError(f"nonfinite JSON constant {value} in {path}")),
    )


def strict_jsonl(path: Path) -> list[dict[str, Any]]:
    payload, _ = _regular_file_bytes(path)
    return [
        json.loads(
            line,
            parse_constant=lambda value: (_ for _ in ()).throw(
                ValueError(f"nonfinite JSON constant {value} in {path}")),
        )
        for line in payload.decode("utf-8").splitlines()
        if line
    ]


def canonical_json_bytes(value: Any, *, newline: bool = True) -> bytes:
    suffix = "\n" if newline else ""
    return (json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False) + suffix).encode()


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def require_hash(path: Path, expected: str) -> None:
    try:
        actual = regular_file_facts(path)["sha256"]
    except (OSError, RuntimeError):
        actual = None
    if actual != expected:
        raise RuntimeError(f"frozen hash mismatch: {path}")


def config() -> dict[str, Any]:
    row = strict_json(CONFIG)
    if (
        row.get("schema_version") != "atlas_completion_summary_recovery_v1"
        or row.get("diagnostic_continuation_only") is not True
        or row.get("decision_promotion_allowed") is not False
        or row.get("scientific_retry_allowed") is not False
        or row.get("roles") != ROLES
    ):
        raise RuntimeError("summary-recovery config semantics changed")
    return row


def candidate_root() -> Path:
    return ROOT / config()["candidate_root"]


def canonical_root() -> Path:
    return ROOT / config()["canonical_root"]


def recovery_run_root() -> Path:
    return ROOT / config()["recovery_run_root"]


def _decode_mount_field(value: str) -> str:
    return (value.replace("\\040", " ").replace("\\011", "\t")
            .replace("\\012", "\n").replace("\\134", "\\"))


def deployment_mount() -> dict[str, Any]:
    target = canonical_root().parent.resolve()
    matches: list[dict[str, Any]] = []
    for line in Path("/proc/self/mountinfo").read_text(encoding="utf-8").splitlines():
        left, right = line.split(" - ", 1)
        fields, post = left.split(), right.split()
        mount_point = Path(_decode_mount_field(fields[4]))
        try:
            target.relative_to(mount_point)
        except ValueError:
            continue
        matches.append({
            "mount_id": fields[0], "parent_mount_id": fields[1],
            "major_minor": fields[2], "mount_point": str(mount_point),
            "mount_options": fields[5].split(","), "filesystem_type": post[0],
            "source": _decode_mount_field(post[1]),
            "super_options": post[2].split(",") if len(post) > 2 else [],
        })
    if not matches:
        raise RuntimeError("deployment mount could not be resolved")
    row = max(matches, key=lambda item: len(item["mount_point"]))
    row.update({"target": str(target), "st_dev": int(target.stat().st_dev)})
    if not str(row["filesystem_type"]).startswith("nfs"):
        raise RuntimeError("reviewed recovery expects the bound NFS deployment mount")
    return row


def verify_execution_owner_mount() -> dict[str, Any]:
    owner_path = recovery_run_root() / "execution_owner.json"
    owner = strict_json(owner_path)
    current_mount = _validate_mount(deployment_mount())
    if (
        set(owner) != {"schema_version", "host", "root", "mount", "created_utc"}
        or owner.get("schema_version")
        != "atlas_completion_summary_recovery_execution_owner_v1"
        or owner.get("host") != socket.gethostname()
        or owner.get("root") != str(ROOT.resolve())
        or owner.get("mount") != current_mount
    ):
        raise RuntimeError("recovery execution owner or deployment mount changed")
    _require_aware_timestamp(owner.get("created_utc"), "execution owner")
    return owner


def _validate_mount(row: Any, *, label: str = "deployment mount") -> dict[str, Any]:
    if (
        not isinstance(row, dict)
        or set(row) != MOUNT_KEYS
        or any(not isinstance(row.get(key), str) or not row[key]
               for key in ["mount_id", "parent_mount_id", "major_minor",
                           "mount_point", "filesystem_type", "source", "target"])
        or not str(row["filesystem_type"]).startswith("nfs")
        or not isinstance(row.get("mount_options"), list)
        or not row["mount_options"]
        or not all(isinstance(item, str) and item for item in row["mount_options"])
        or not isinstance(row.get("super_options"), list)
        or not all(isinstance(item, str) and item for item in row["super_options"])
        or not isinstance(row.get("st_dev"), int)
        or row["st_dev"] < 0
    ):
        raise RuntimeError(f"{label} schema mismatch")
    return row


RECOVERY_DIRECTORIES = (
    "logs", "job_manifests", "job_state", "job_state/candidate",
    "job_state/publish", "job_scripts", "work", "verification", "locks",
    "filesystem_capabilities",
)


def ensure_recovery_directories() -> list[Path]:
    """Create and durably validate the fixed recovery evidence ancestry."""

    root = recovery_run_root()
    paths = [root, *(root / relative for relative in RECOVERY_DIRECTORIES)]
    for path in paths:
        if path.exists() and (not path.is_dir() or path.is_symlink()):
            raise RuntimeError(f"unsafe recovery directory: {path}")
        if not path.exists():
            path.mkdir(parents=False, mode=0o700)
        fsync_directory(path)
        fsync_directory(path.parent)
    for path in paths:
        if not path.is_dir() or path.is_symlink():
            raise RuntimeError(f"recovery directory changed during bootstrap: {path}")
        fsync_directory(path)
        fsync_directory(path.parent)
    return paths


def implementation_inventory() -> list[dict[str, str]]:
    rows = []
    for relative in sorted(IMPLEMENTATION_FILES):
        path = ROOT / relative
        try:
            digest = regular_file_facts(path)["sha256"]
        except (OSError, RuntimeError):
            raise RuntimeError(f"implementation candidate missing: {relative}")
        rows.append({"path": relative, "sha256": digest})
    return rows


def inventory_digest(rows: list[dict[str, Any]]) -> str:
    return sha256_bytes(canonical_json_bytes(rows, newline=False))


def verify_incident_inputs() -> dict[str, Any]:
    row = config()
    fixed = {
        row["original_continuation_freeze_path"]: row["original_continuation_freeze_sha256"],
        row["original_summarizer_path"]: row["original_summarizer_sha256"],
        row["original_verifier_path"]: row["original_verifier_sha256"],
        row["original_k2_producer_path"]: row["original_k2_producer_sha256"],
        row["collection_path"]: row["collection_sha256"],
        row["failed_summarize_terminal_path"]: row["failed_summarize_terminal_sha256"],
        row["failed_summarize_log_path"]: row["failed_summarize_log_sha256"],
        row["task_row_manifest_path"]: row["task_row_manifest_sha256"],
        row["plan_path"]: row["plan_sha256"],
        row["plan_review_path"]: row["plan_review_sha256"],
    }
    for relative, expected in fixed.items():
        require_hash(ROOT / relative, expected)
    for role in ROLES:
        lineage = row["partition_lineage"][role]
        require_hash(ROOT / lineage["records_path"], lineage["records_sha256"])
        require_hash(ROOT / lineage["units_path"], lineage["units_sha256"])
    failed = strict_json(ROOT / row["failed_summarize_terminal_path"])
    if not (
        failed.get("job") == "summarize"
        and failed.get("outcome") == "technical_failure"
        and failed.get("exit_code") == 1
        and failed.get("diagnostic_continuation_only") is True
        and failed.get("decision_promotion_allowed") is False
    ):
        raise RuntimeError("original summarize failure semantics changed")
    original = verify_continuation_freeze()
    if original["bundle_sha256"] != row["original_continuation_bundle_sha256"]:
        raise RuntimeError("original continuation bundle mismatch")
    verify_source_inventory()
    verify_fixed_source_hashes()
    collection = strict_json(ROOT / row["collection_path"])
    validate_collection(collection)
    if collection.get("collection_outcome") != "closed_all_stages":
        raise RuntimeError("continuation collection is not closed")
    plan_review = strict_json(ROOT / row["plan_review_record_path"])
    if not (
        plan_review.get("schema_version") == "atlas_completion_summary_recovery_plan_review_v1"
        and plan_review.get("origin") == "forked"
        and plan_review.get("verdict") == "SHIP"
        and plan_review.get("plan_sha256") == row["plan_sha256"]
        and plan_review.get("transcript_sha256") == row["plan_review_sha256"]
    ):
        raise RuntimeError("summary-recovery plan review binding mismatch")
    return {"config": row, "collection": collection, "original_freeze": original}


def _review_binding(path: Path, *, schema: str, candidate_sha: str) -> dict[str, Any]:
    review = strict_json(path)
    transcript = ROOT / str(review.get("transcript_path"))
    try:
        transcript_bytes, _ = _regular_file_bytes(transcript)
    except (OSError, RuntimeError):
        transcript_bytes = b""
    if not (
        review.get("schema_version") == schema
        and review.get("origin") == "forked"
        and review.get("verdict") == "SHIP"
        and review.get("candidate_sha256") == candidate_sha
        and review.get("transcript_sha256") == sha256_bytes(transcript_bytes)
        and transcript_bytes.decode("utf-8").startswith("VERDICT: SHIP")
    ):
        raise RuntimeError(f"review binding mismatch: {path}")
    return review


def verify_initial_freeze() -> dict[str, Any]:
    incident = verify_incident_inputs()
    record = strict_json(INITIAL_FREEZE)
    inventory = implementation_inventory()
    digest = inventory_digest(inventory)
    if (
        record.get("schema_version") != "atlas_completion_summary_recovery_freeze_v1"
        or record.get("candidate_files") != inventory
        or record.get("candidate_sha256") != digest
        or record.get("diagnostic_continuation_only") is not True
        or record.get("decision_promotion_allowed") is not False
        or record.get("original_continuation_bundle_sha256")
        != incident["config"]["original_continuation_bundle_sha256"]
    ):
        raise RuntimeError("summary-recovery initial freeze mismatch")
    implementation = _review_binding(
        IMPLEMENTATION_REVIEW,
        schema="atlas_completion_summary_recovery_implementation_review_v1",
        candidate_sha=digest,
    )
    material = {
        "candidate_sha256": digest,
        "implementation_review_sha256": implementation["transcript_sha256"],
        "original_continuation_bundle_sha256": incident["config"]["original_continuation_bundle_sha256"],
        "plan_review_sha256": incident["config"]["plan_review_sha256"],
    }
    expected_bundle = sha256_bytes(canonical_json_bytes(material, newline=False))
    if record.get("bundle_material") != material or record.get("bundle_sha256") != expected_bundle:
        raise RuntimeError("summary-recovery initial bundle digest mismatch")
    return record


def content_inventory(root: Path) -> list[dict[str, str]]:
    return [
        {"path": name, "sha256": sha256_file(root / name)}
        for name in sorted(["diagnostic_results.json", "diagnostic_results.md", "source_lineage.json"])
    ]


def content_digest(root: Path) -> str:
    return inventory_digest(content_inventory(root))


def root_inventory(root: Path) -> list[dict[str, Any]]:
    return [
        {"path": path.name, "sha256": sha256_file(path), "size": path.stat().st_size}
        for path in sorted(root.iterdir(), key=lambda item: item.name)
        if path.is_file()
    ]


def root_digest(root: Path) -> str:
    return inventory_digest(root_inventory(root))


def success_path(job: str) -> Path:
    return recovery_run_root() / "job_manifests" / f"{job}.success.json"


def capability_path(job: str, attempt_id: str) -> Path:
    return recovery_run_root() / "filesystem_capabilities" / f"{job}.{attempt_id}.json"


def _valid_digest(value: Any) -> bool:
    return re.fullmatch(r"[0-9a-f]{64}", str(value)) is not None


def _validate_file_capability(row: Any) -> None:
    if not isinstance(row, dict) or set(row) != {
        "success", "eexist_preserved", "two_process",
    }:
        raise RuntimeError("filesystem file-capability schema mismatch")
    success = row["success"]
    if (
        not isinstance(success, dict)
        or set(success) != {
            "source_sha256", "destination_sha256", "source_size",
            "destination_size", "source_regular", "destination_regular",
            "source_st_dev", "source_st_ino", "destination_st_dev",
            "destination_st_ino", "same_inode",
        }
        or success.get("source_sha256") != sha256_bytes(b"success")
        or success.get("destination_sha256") != success.get("source_sha256")
        or success.get("source_size") != len(b"success")
        or success.get("destination_size") != success.get("source_size")
        or success.get("source_regular") is not True
        or success.get("destination_regular") is not True
        or success.get("same_inode") is not True
        or not isinstance(success.get("source_st_dev"), int)
        or not isinstance(success.get("source_st_ino"), int)
        or success["source_st_dev"] < 0 or success["source_st_ino"] <= 0
        or success.get("destination_st_dev") != success.get("source_st_dev")
        or success.get("destination_st_ino") != success.get("source_st_ino")
    ):
        raise RuntimeError("filesystem file-success evidence mismatch")
    collision = row["eexist_preserved"]
    if (
        not isinstance(collision, dict)
        or set(collision) != {
            "source_sha256_before", "source_sha256_after",
            "destination_sha256_before", "destination_sha256_after",
            "source_size_before", "source_size_after",
            "destination_size_before", "destination_size_after",
            "source_st_dev_before", "source_st_dev_after",
            "source_st_ino_before", "source_st_ino_after",
            "destination_st_dev_before", "destination_st_dev_after",
            "destination_st_ino_before", "destination_st_ino_after",
            "source_regular", "destination_regular", "distinct_inodes",
        }
        or collision.get("source_sha256_before") != sha256_bytes(b"source")
        or collision.get("destination_sha256_before") != sha256_bytes(b"destination")
        or collision.get("source_sha256_after") != collision.get("source_sha256_before")
        or collision.get("destination_sha256_after")
        != collision.get("destination_sha256_before")
        or collision.get("source_size_before") != len(b"source")
        or collision.get("source_size_after") != collision.get("source_size_before")
        or collision.get("destination_size_before") != len(b"destination")
        or collision.get("destination_size_after")
        != collision.get("destination_size_before")
        or collision.get("source_regular") is not True
        or collision.get("destination_regular") is not True
        or collision.get("distinct_inodes") is not True
        or not isinstance(collision.get("source_st_dev_before"), int)
        or not isinstance(collision.get("source_st_ino_before"), int)
        or collision["source_st_dev_before"] < 0 or collision["source_st_ino_before"] <= 0
        or collision.get("source_st_dev_after") != collision.get("source_st_dev_before")
        or collision.get("source_st_ino_after") != collision.get("source_st_ino_before")
        or not isinstance(collision.get("destination_st_dev_before"), int)
        or not isinstance(collision.get("destination_st_ino_before"), int)
        or collision["destination_st_dev_before"] < 0
        or collision["destination_st_ino_before"] <= 0
        or collision.get("destination_st_dev_after")
        != collision.get("destination_st_dev_before")
        or collision.get("destination_st_ino_after")
        != collision.get("destination_st_ino_before")
        or (collision.get("source_st_dev_before"), collision.get("source_st_ino_before"))
        == (collision.get("destination_st_dev_before"),
            collision.get("destination_st_ino_before"))
    ):
        raise RuntimeError("filesystem file-EEXIST evidence mismatch")
    contention = row["two_process"]
    if (
        not isinstance(contention, dict)
        or set(contention) != {
            "exit_codes", "target_present", "sources_preserved",
            "source_sha256", "source_size", "source_regular",
            "source_st_dev", "source_st_ino",
            "target_sha256", "target_size", "target_regular",
            "target_st_dev", "target_st_ino",
            "winner_index", "target_matches_winner",
            "target_same_inode_as_winner",
        }
        or contention.get("exit_codes") != [0, 17]
        or contention.get("target_present") is not True
        or contention.get("sources_preserved") is not True
        or not isinstance(contention.get("source_sha256"), list)
        or len(contention["source_sha256"]) != 2
        or contention["source_sha256"]
        != [sha256_bytes(b"source-0"), sha256_bytes(b"source-1")]
        or not isinstance(contention.get("source_size"), list)
        or len(contention["source_size"]) != 2
        or contention["source_size"] != [len(b"source-0"), len(b"source-1")]
        or contention.get("source_regular") != [True, True]
        or not isinstance(contention.get("source_st_dev"), list)
        or len(contention["source_st_dev"]) != 2
        or not all(isinstance(item, int) and item >= 0 for item in contention["source_st_dev"])
        or not isinstance(contention.get("source_st_ino"), list)
        or len(contention["source_st_ino"]) != 2
        or not all(isinstance(item, int) and item > 0 for item in contention["source_st_ino"])
        or contention.get("winner_index") not in {0, 1}
        or contention.get("target_sha256")
        != contention["source_sha256"][contention["winner_index"]]
        or contention.get("target_size")
        != contention["source_size"][contention["winner_index"]]
        or contention.get("target_regular") is not True
        or contention.get("target_matches_winner") is not True
        or contention.get("target_same_inode_as_winner") is not True
        or contention.get("target_st_dev")
        != contention["source_st_dev"][contention["winner_index"]]
        or contention.get("target_st_ino")
        != contention["source_st_ino"][contention["winner_index"]]
    ):
        raise RuntimeError("filesystem file-contention evidence mismatch")


def _validate_directory_capability(row: Any) -> None:
    if not isinstance(row, dict) or set(row) != {
        "success", "eexist_preserved", "two_process",
    }:
        raise RuntimeError("filesystem directory-capability schema mismatch")
    success = row["success"]
    if (
        not isinstance(success, dict)
        or set(success) != {
            "destination_directory", "destination_st_dev", "destination_st_ino",
            "marker_sha256", "marker_size", "marker_regular",
        }
        or success.get("destination_directory") is not True
        or not isinstance(success.get("destination_st_dev"), int)
        or not isinstance(success.get("destination_st_ino"), int)
        or success["destination_st_dev"] < 0 or success["destination_st_ino"] <= 0
        or success.get("marker_sha256") != sha256_bytes(b"success")
        or success.get("marker_size") != len(b"success")
        or success.get("marker_regular") is not True
    ):
        raise RuntimeError("filesystem directory-success evidence mismatch")
    collision = row["eexist_preserved"]
    if (
        not isinstance(collision, dict)
        or set(collision) != {
            "destination_directory", "marker_sha256_before", "marker_sha256_after",
            "marker_size_before", "marker_size_after", "marker_regular",
            "destination_st_dev_before", "destination_st_dev_after",
            "destination_st_ino_before", "destination_st_ino_after",
        }
        or collision.get("destination_directory") is not True
        or collision.get("marker_sha256_before") != sha256_bytes(b"destination")
        or collision.get("marker_sha256_after") != collision.get("marker_sha256_before")
        or collision.get("marker_size_before") != len(b"destination")
        or collision.get("marker_size_after") != collision.get("marker_size_before")
        or collision.get("marker_regular") is not True
        or not isinstance(collision.get("destination_st_dev_before"), int)
        or not isinstance(collision.get("destination_st_ino_before"), int)
        or collision["destination_st_dev_before"] < 0
        or collision["destination_st_ino_before"] <= 0
        or collision.get("destination_st_dev_after")
        != collision.get("destination_st_dev_before")
        or collision.get("destination_st_ino_after")
        != collision.get("destination_st_ino_before")
    ):
        raise RuntimeError("filesystem directory-EEXIST evidence mismatch")
    contention = row["two_process"]
    if contention != {
        "exit_codes": [0, 17], "target_present": True,
        "target_directory": True, "target_empty": True,
        "target_st_dev": contention.get("target_st_dev"),
        "target_st_ino": contention.get("target_st_ino"),
    } or not isinstance(contention.get("target_st_dev"), int) \
            or not isinstance(contention.get("target_st_ino"), int) \
            or contention["target_st_dev"] < 0 or contention["target_st_ino"] <= 0:
        raise RuntimeError("filesystem directory-contention evidence mismatch")


def validate_capability_payload(row: dict[str, Any], *, job: str,
                                attempt_id: str) -> dict[str, Any]:
    expected_keys = {
        "schema_version", "job", "attempt_id", "mode", "argv", "log",
        "tested_host", "mount", "outcomes", "all_passed", "tested_utc",
    }
    if (
        set(row) != expected_keys
        or row.get("schema_version")
        != "atlas_completion_summary_recovery_filesystem_capability_v2"
        or row.get("job") != job
        or row.get("attempt_id") != attempt_id
        or row.get("mode") not in {"run", "reconcile"}
        or not isinstance(row.get("argv"), list)
        or not row["argv"]
        or not all(isinstance(item, str) and item for item in row["argv"])
        or not isinstance(row.get("log"), str)
        or not row["log"]
        or Path(row["log"]).is_absolute()
        or ".." in Path(row["log"]).parts
        or not isinstance(row.get("tested_host"), str)
        or not row["tested_host"]
        or not isinstance(row.get("mount"), dict)
        or not isinstance(row.get("outcomes"), dict)
        or set(row["outcomes"]) != {"file", "directory", "job_lock"}
        or row["outcomes"].get("job_lock") != {
            "separate_descriptor_lost": True,
            "guarded_manifest_marker_created": False,
        }
        or row.get("all_passed") is not True
    ):
        raise RuntimeError("filesystem capability record mismatch")
    _validate_mount(row["mount"], label="filesystem capability mount")
    if row["mount"] != _validate_mount(deployment_mount(), label="current deployment mount"):
        raise RuntimeError("filesystem capability mount differs from current deployment mount")
    _validate_file_capability(row["outcomes"]["file"])
    _validate_directory_capability(row["outcomes"]["directory"])
    log = ROOT / row["log"]
    try:
        log.relative_to(recovery_run_root() / "logs")
    except ValueError as exc:
        raise RuntimeError("capability log path is outside recovery logs") from exc
    _require_aware_timestamp(row.get("tested_utc"), "filesystem capability")
    return row


def _validate_capability(path: Path, *, job: str, attempt_id: str) -> dict[str, Any]:
    if not path.is_file() or path.is_symlink():
        raise RuntimeError(f"filesystem capability path mismatch: {path}")
    return validate_capability_payload(strict_json(path), job=job, attempt_id=attempt_id)


def _applicable_freezes(job: str) -> tuple[str, str | None]:
    initial = verify_initial_freeze()["bundle_sha256"]
    promotion = verify_promotion_freeze()["bundle_sha256"] if job == "publish" else None
    return initial, promotion


def _validate_attempt_manifest(path: Path, *, job: str, attempt_id: str) -> dict[str, Any]:
    row = strict_json(path)
    expected_keys = {
        "schema_version", "job", "attempt_id", "mode", "argv", "pid", "host",
        "started_utc", "initial_recovery_bundle_sha256", "promotion_bundle_sha256",
        "execution_owner_sha256", "filesystem_capability_path",
        "filesystem_capability_sha256", "staging_prefix", "destination", "log",
    }
    initial, promotion = _applicable_freezes(job)
    expected_destination = candidate_root() if job == "candidate" else canonical_root()
    log = ROOT / str(row.get("log", ""))
    try:
        log.relative_to(recovery_run_root() / "logs")
    except ValueError as exc:
        raise RuntimeError("attempt log is outside recovery log root") from exc
    if (
        set(row) != expected_keys
        or row.get("schema_version") != "atlas_completion_summary_recovery_job_manifest_v2"
        or row.get("job") != job
        or row.get("attempt_id") != attempt_id
        or row.get("mode") not in {"run", "reconcile"}
        or not isinstance(row.get("argv"), list)
        or not row["argv"]
        or not all(isinstance(item, str) and item for item in row["argv"])
        or not isinstance(row.get("pid"), int)
        or row["pid"] <= 0
        or not isinstance(row.get("host"), str)
        or not row["host"]
        or row.get("initial_recovery_bundle_sha256") != initial
        or row.get("promotion_bundle_sha256") != promotion
        or row.get("execution_owner_sha256") != sha256_file(
            recovery_run_root() / "execution_owner.json")
        or not re.fullmatch(r"[0-9a-f]{64}", str(row.get("filesystem_capability_sha256")))
        or row.get("staging_prefix") != f"results/atlas/.completion_diagnostic_{job}.staging."
        or row.get("destination") != str(expected_destination.relative_to(ROOT))
    ):
        raise RuntimeError(f"attempt manifest mismatch: {path}")
    capability = ROOT / str(row["filesystem_capability_path"])
    try:
        capability.relative_to(recovery_run_root() / "filesystem_capabilities")
    except ValueError as exc:
        raise RuntimeError("attempt filesystem capability is outside recovery root") from exc
    if (
        capability != capability_path(job, attempt_id)
        or not capability.is_file()
        or sha256_file(capability) != row["filesystem_capability_sha256"]
    ):
        raise RuntimeError("attempt filesystem capability binding mismatch")
    capability_row = _validate_capability(capability, job=job, attempt_id=attempt_id)
    owner_path = recovery_run_root() / "execution_owner.json"
    owner = verify_execution_owner_mount()
    if (
        set(owner) != {"schema_version", "host", "root", "mount", "created_utc"}
        or owner.get("schema_version")
        != "atlas_completion_summary_recovery_execution_owner_v1"
        or owner.get("host") != socket.gethostname()
        or owner.get("root") != str(ROOT.resolve())
        or owner.get("mount") != capability_row["mount"]
    ):
        raise RuntimeError("attempt execution owner binding mismatch")
    _require_aware_timestamp(owner.get("created_utc"), "execution owner")
    if (
        capability_row["mode"] != row["mode"]
        or capability_row["argv"] != row["argv"]
        or capability_row["log"] != row["log"]
        or capability_row["tested_host"] != row["host"]
    ):
        raise RuntimeError("attempt manifest/capability context mismatch")
    _require_aware_timestamp(row.get("started_utc"), "attempt manifest")
    return row


def _validate_attempt_terminal(path: Path, *, job: str) -> dict[str, Any]:
    row = strict_json(path)
    expected_keys = {
        "schema_version", "job", "attempt_id", "manifest_state", "manifest_sha256",
        "filesystem_capability_path", "filesystem_capability_sha256",
        "state_snapshot_path", "state_snapshot_sha256", "log_sha256", "exit_code",
        "outcome", "closure_reason", "last_durable_phase", "released_lock_observed",
        "recovery_host",
        "diagnostic_continuation_only", "decision_promotion_allowed", "ended_utc",
    }
    attempt_id = str(row.get("attempt_id", ""))
    capability = capability_path(job, attempt_id)
    capability_row = _validate_capability(capability, job=job, attempt_id=attempt_id)
    manifest_path = recovery_run_root() / "job_manifests" / f"{job}.{attempt_id}.manifest.json"
    manifest_present = row.get("manifest_state") == "present"
    manifest = (
        _validate_attempt_manifest(manifest_path, job=job, attempt_id=attempt_id)
        if manifest_present else None
    )
    if not manifest_present and manifest_path.exists():
        raise RuntimeError(f"terminal falsely declares manifest absent: {path}")
    log = ROOT / capability_row["log"]
    orphan_reasons = {
        "supervisor_unobservable_exit",
        "supervisor_unobservable_exit_before_manifest",
    }
    orphan = row.get("closure_reason") in orphan_reasons
    before_manifest = row.get("closure_reason") == "supervisor_unobservable_exit_before_manifest"
    expected_outcome = (
        "technical_failure" if orphan else
        ("reconciled" if manifest and manifest["mode"] == "reconcile" else "success")
        if row.get("exit_code") == 0 and row.get("last_durable_phase") == "parent_fsync_complete"
        else ("destination_collision" if row.get("outcome") == "destination_collision"
              else "technical_failure")
    )
    if (
        set(row) != expected_keys
        or row.get("schema_version") != "atlas_completion_summary_recovery_job_attempt_terminal_v3"
        or row.get("job") != job
        or not re.fullmatch(r"[0-9]{8}T[0-9]{6}Z_[0-9]+_[0-9a-f]{8}", attempt_id)
        or row.get("manifest_state") not in {"present", "absent"}
        or before_manifest is not (not manifest_present)
        or row.get("manifest_sha256")
        != (sha256_file(manifest_path) if manifest_present else None)
        or row.get("filesystem_capability_path") != str(capability.relative_to(ROOT))
        or row.get("filesystem_capability_sha256") != sha256_file(capability)
        or row.get("log_sha256") != (sha256_file(log) if log.is_file() else None)
        or (row.get("exit_code") is None) is not orphan
        or (row.get("exit_code") is not None and not isinstance(row.get("exit_code"), int))
        or row.get("outcome") not in {
            "success", "technical_failure", "destination_collision", "reconciled"}
        or row.get("outcome") != expected_outcome
        or row.get("closure_reason") not in {
            "normal_exit", "command_failure", "destination_collision",
            "supervisor_unobservable_exit", "supervisor_unobservable_exit_before_manifest"}
        or row.get("released_lock_observed") is not orphan
        or (row.get("recovery_host") is None) is not (not orphan)
        or not isinstance(row.get("last_durable_phase"), str)
        or row.get("diagnostic_continuation_only") is not True
        or row.get("decision_promotion_allowed") is not False
    ):
        raise RuntimeError(f"attempt terminal mismatch: {path}")
    snapshot = ROOT / str(row.get("state_snapshot_path", ""))
    if (
        not snapshot.is_file()
        or snapshot.is_symlink()
        or row.get("state_snapshot_sha256") != sha256_file(snapshot)
    ):
        raise RuntimeError(f"attempt state snapshot mismatch: {path}")
    snapshot_row = _validate_state_snapshot(snapshot, job=job, attempt_id=attempt_id)
    if not manifest_present and snapshot_row.get("state_status") != "state_absent_for_attempt":
        raise RuntimeError(f"attempt state snapshot mismatch: {path}")
    _require_aware_timestamp(row.get("ended_utc"), "attempt terminal")
    return row


def validate_success_closure(job: str, destination: Path) -> dict[str, Any]:
    if job not in {"candidate", "publish"}:
        raise ValueError(f"invalid recovery job: {job}")
    path = success_path(job)
    success = strict_json(path)
    expected_keys = {
        "schema_version", "job", "successful_attempt_terminal",
        "successful_attempt_terminal_sha256", "successful_filesystem_capability",
        "successful_filesystem_capability_sha256", "successful_state_snapshot",
        "successful_state_snapshot_sha256", "attempt_manifests", "attempt_terminals",
        "attempt_capabilities", "attempt_state_snapshots",
        "final_state_path", "final_state_sha256", "final_state_generation",
        "destination_root_sha256", "initial_recovery_bundle_sha256",
        "promotion_bundle_sha256", "parent_fsync_complete",
        "diagnostic_continuation_only", "decision_promotion_allowed", "ended_utc",
    }
    initial, promotion = _applicable_freezes(job)
    evidence_root = recovery_run_root() / "job_manifests"
    manifest_paths = sorted(evidence_root.glob(f"{job}.*.manifest.json"))
    terminal_paths = sorted(evidence_root.glob(f"{job}.*.terminal.json"))
    capability_paths = sorted(
        (recovery_run_root() / "filesystem_capabilities").glob(f"{job}.*.json"))
    snapshot_paths = sorted(
        (recovery_run_root() / "job_state").glob(f"{job}.*.json"))
    manifest_ids = [_attempt_from_name(item, job, "manifest") for item in manifest_paths]
    terminal_ids = [_attempt_from_name(item, job, "terminal") for item in terminal_paths]
    capability_ids = [_attempt_from_name(item, job, "capability") for item in capability_paths]
    snapshot_ids = [_attempt_from_name(item, job, "snapshot") for item in snapshot_paths]
    expected_manifests = [
        {"path": str(item.relative_to(ROOT)), "sha256": sha256_file(item)}
        for item in manifest_paths
    ]
    expected_terminals = [
        {"path": str(item.relative_to(ROOT)), "sha256": sha256_file(item)}
        for item in terminal_paths
    ]
    expected_capabilities = [
        {"path": str(item.relative_to(ROOT)), "sha256": sha256_file(item)}
        for item in capability_paths
    ]
    expected_snapshots = [
        {"path": str(item.relative_to(ROOT)), "sha256": sha256_file(item)}
        for item in snapshot_paths
    ]
    snapshot_by_id = {
        attempt_id: _validate_state_snapshot(path, job=job, attempt_id=attempt_id)
        for path, attempt_id in zip(snapshot_paths, snapshot_ids)
    }
    terminal_by_path = {
        str(item.relative_to(ROOT)): _validate_attempt_terminal(item, job=job)
        for item in terminal_paths
    }
    successful_relative = str(success.get("successful_attempt_terminal", ""))
    successful = terminal_by_path.get(successful_relative)
    present_manifest_ids = sorted(
        row["attempt_id"] for row in terminal_by_path.values()
        if row["manifest_state"] == "present")
    head = read_state_chain(job)
    if head is None:
        raise RuntimeError("successful job lacks a state journal")
    successful_snapshot = ROOT / str(success.get("successful_state_snapshot", ""))
    successful_snapshot_row = (
        strict_json(successful_snapshot) if successful_snapshot.is_file() else {})
    if (
        set(success) != expected_keys
        or success.get("schema_version") != "atlas_completion_summary_recovery_job_success_v4"
        or success.get("job") != job
        or capability_ids != terminal_ids
        or snapshot_ids != terminal_ids
        or manifest_ids != present_manifest_ids
        or len(capability_ids) != len(set(capability_ids))
        or len(snapshot_ids) != len(set(snapshot_ids))
        or success.get("attempt_manifests") != expected_manifests
        or success.get("attempt_terminals") != expected_terminals
        or success.get("attempt_capabilities") != expected_capabilities
        or success.get("attempt_state_snapshots") != expected_snapshots
        or successful is None
        or success.get("successful_attempt_terminal_sha256")
        != sha256_file(ROOT / successful_relative)
        or successful.get("exit_code") != 0
        or successful.get("outcome") not in {"success", "reconciled"}
        or successful.get("manifest_state") != "present"
        or successful.get("last_durable_phase") != "parent_fsync_complete"
        or success.get("successful_filesystem_capability")
        != successful.get("filesystem_capability_path")
        or success.get("successful_filesystem_capability_sha256")
        != successful.get("filesystem_capability_sha256")
        or not successful_snapshot.is_file()
        or success.get("successful_state_snapshot_sha256") != sha256_file(successful_snapshot)
        or successful.get("state_snapshot_path") != str(successful_snapshot.relative_to(ROOT))
        or successful_snapshot_row
        != snapshot_by_id.get(str(successful.get("attempt_id")))
        or successful_snapshot_row.get("state_status") != "present"
        or successful_snapshot_row.get("state_path") != head["_path"]
        or successful_snapshot_row.get("state_sha256") != head["_sha256"]
        or head.get("active_attempt_id") != successful.get("attempt_id")
        or success.get("final_state_path") != head["_path"]
        or success.get("final_state_sha256") != head["_sha256"]
        or success.get("final_state_generation") != head["generation"]
        or head.get("phase") != "parent_fsync_complete"
        or head.get("destination_root_sha256") != root_digest(destination)
        or success.get("destination_root_sha256") != root_digest(destination)
        or success.get("initial_recovery_bundle_sha256") != initial
        or success.get("promotion_bundle_sha256") != promotion
        or success.get("parent_fsync_complete") is not True
        or success.get("diagnostic_continuation_only") is not True
        or success.get("decision_promotion_allowed") is not False
    ):
        raise RuntimeError(f"{job} lacks a valid durable success closure")
    _require_aware_timestamp(success.get("ended_utc"), "job success closure")
    return success


def _write_success_closure(job: str, terminal_path: Path, snapshot_path: Path) -> dict[str, Any]:
    require_job_lock(job)
    destination = candidate_root() if job == "candidate" else canonical_root()
    terminal = _validate_attempt_terminal(terminal_path, job=job)
    if terminal["outcome"] not in {"success", "reconciled"}:
        raise RuntimeError("technical attempt cannot create success closure")
    head = read_state_chain(job)
    if head is None or head["phase"] != "parent_fsync_complete":
        raise RuntimeError("success closure lacks a parent-fsynced state head")
    evidence_root = recovery_run_root() / "job_manifests"
    manifests = sorted(evidence_root.glob(f"{job}.*.manifest.json"))
    terminals = sorted(evidence_root.glob(f"{job}.*.terminal.json"))
    capabilities = sorted(
        (recovery_run_root() / "filesystem_capabilities").glob(f"{job}.*.json"))
    snapshots = sorted((recovery_run_root() / "job_state").glob(f"{job}.*.json"))
    terminal_rows = [_validate_attempt_terminal(path, job=job) for path in terminals]
    if (
        [_attempt_from_name(path, job, "capability") for path in capabilities]
        != [_attempt_from_name(path, job, "terminal") for path in terminals]
        or [_attempt_from_name(path, job, "snapshot") for path in snapshots]
        != [_attempt_from_name(path, job, "terminal") for path in terminals]
        or [_attempt_from_name(path, job, "manifest") for path in manifests]
        != sorted(row["attempt_id"] for row in terminal_rows
                  if row["manifest_state"] == "present")
    ):
        raise RuntimeError("success closure attempt history is not total")
    initial, promotion = _applicable_freezes(job)
    row = {
        "schema_version": "atlas_completion_summary_recovery_job_success_v4",
        "job": job,
        "successful_attempt_terminal": str(terminal_path.relative_to(ROOT)),
        "successful_attempt_terminal_sha256": sha256_file(terminal_path),
        "successful_filesystem_capability": terminal["filesystem_capability_path"],
        "successful_filesystem_capability_sha256": terminal["filesystem_capability_sha256"],
        "successful_state_snapshot": str(snapshot_path.relative_to(ROOT)),
        "successful_state_snapshot_sha256": sha256_file(snapshot_path),
        "attempt_manifests": [
            {"path": str(path.relative_to(ROOT)), "sha256": sha256_file(path)}
            for path in manifests],
        "attempt_terminals": [
            {"path": str(path.relative_to(ROOT)), "sha256": sha256_file(path)}
            for path in terminals],
        "attempt_capabilities": [
            {"path": str(path.relative_to(ROOT)), "sha256": sha256_file(path)}
            for path in capabilities],
        "attempt_state_snapshots": [
            {"path": str(path.relative_to(ROOT)), "sha256": sha256_file(path)}
            for path in snapshots],
        "final_state_path": head["_path"], "final_state_sha256": head["_sha256"],
        "final_state_generation": head["generation"],
        "destination_root_sha256": root_digest(destination),
        "initial_recovery_bundle_sha256": initial,
        "promotion_bundle_sha256": promotion,
        "parent_fsync_complete": True, "diagnostic_continuation_only": True,
        "decision_promotion_allowed": False, "ended_utc": utc_now(),
    }
    write_once_json(success_path(job), row)
    return validate_success_closure(job, destination)


def validate_candidate(root: Path | None = None, *, require_success: bool = True) -> dict[str, Any]:
    root = root or candidate_root()
    expected_names = {
        "diagnostic_results.json", "diagnostic_results.md", "source_lineage.json", "CANDIDATE_COMPLETE.json"
    }
    if (not root.is_dir() or root.is_symlink()
            or {p.name for p in root.iterdir()} != expected_names
            or any(not p.is_file() or p.is_symlink() for p in root.iterdir())):
        raise RuntimeError("candidate root inventory mismatch")
    initial = verify_initial_freeze()
    result = strict_json(root / "diagnostic_results.json")
    validate_result_contract(result)
    lineage = strict_json(root / "source_lineage.json")
    if (
        set(lineage) != {"schema_version", "roles", "input_sha256", "all_rows_match",
                         "expected_sources", "k2_family_verifier_drift"}
        or lineage.get("schema_version") != "atlas_completion_summary_source_lineage_v1"
        or lineage.get("all_rows_match") is not True
        or set(lineage.get("roles", {})) != set(ROLES)
        or set(lineage.get("expected_sources", {})) != set(ROLES)
        or not isinstance(lineage.get("input_sha256"), dict)
        or not lineage["input_sha256"]
    ):
        raise RuntimeError("candidate source-lineage schema mismatch")
    drift = lineage["k2_family_verifier_drift"]
    if (
        set(drift) != {"schema_version", "registered_leaves", "producer_rule_exact_leaves",
                       "known_generic_drift_leaves", "known_difference",
                       "leaf_inventory_sha256", "producer_sha256", "verifier_sha256"}
        or drift.get("schema_version") != "atlas_completion_summary_k2_verifier_drift_v1"
        or drift.get("registered_leaves") != 2004
        or drift.get("producer_rule_exact_leaves") != 2004
        or drift.get("known_generic_drift_leaves") != 2004
        or drift.get("known_difference")
        != "relative_structural_position_spurious_assigned_pos_leakage_entry"
        or drift.get("producer_sha256") != sha256_file(ROOT / "scripts/run_msae_refit_worker.py")
        or drift.get("verifier_sha256") != sha256_file(ROOT / "scripts/verify_msae_completion.py")
        or not re.fullmatch(r"[0-9a-f]{64}", str(drift.get("leaf_inventory_sha256")))
    ):
        raise RuntimeError("candidate K2 verifier-drift lineage mismatch")
    for role in ROLES:
        role_row = lineage["roles"][role]
        if set(role_row) != {"tasks"} or set(role_row["tasks"]) != set(TASKS):
            raise RuntimeError(f"candidate source-lineage task inventory mismatch: {role}")
        if set(lineage["expected_sources"][role]) != set(TASKS):
            raise RuntimeError(f"candidate expected-source inventory mismatch: {role}")
        for task in TASKS:
            task_row = role_row["tasks"][task]
            if (
                set(task_row) != {"rows", "matching_rows", "sources", "document_groups",
                                  "task_rows_sha256"}
                or not isinstance(task_row["rows"], int)
                or task_row["rows"] <= 0
                or task_row["matching_rows"] != task_row["rows"]
                or task_row["sources"] != lineage["expected_sources"][role][task]
                or not task_row["sources"]
                or not isinstance(task_row["document_groups"], int)
                or task_row["document_groups"] <= 0
                or not re.fullmatch(r"[0-9a-f]{64}", str(task_row["task_rows_sha256"]))
            ):
                raise RuntimeError(f"candidate source-lineage task mismatch: {role}/{task}")
    for relative, digest in lineage["input_sha256"].items():
        path = ROOT / relative
        if Path(relative).is_absolute() or ".." in Path(relative).parts:
            raise RuntimeError("unsafe candidate source-lineage input path")
        if not path.is_file() or sha256_file(path) != digest:
            raise RuntimeError(f"candidate source-lineage input changed: {relative}")
    terminal = strict_json(root / "CANDIDATE_COMPLETE.json")
    expected_keys = {
        "schema_version", "canonical", "candidate_content_sha256", "completion_bundle_sha256",
        "recovery_bundle_sha256", "result_sha256", "report_sha256", "source_lineage_sha256",
        "diagnostic_continuation_only", "decision_promotion_allowed", "ended_utc",
    }
    if (
        set(terminal) != expected_keys
        or terminal["schema_version"] != "atlas_completion_summary_recovery_candidate_terminal_v1"
        or terminal["canonical"] is not False
        or terminal["candidate_content_sha256"] != content_digest(root)
        or terminal["completion_bundle_sha256"] != config()["original_continuation_bundle_sha256"]
        or terminal["recovery_bundle_sha256"] != initial["bundle_sha256"]
        or terminal["result_sha256"] != sha256_file(root / "diagnostic_results.json")
        or terminal["report_sha256"] != sha256_file(root / "diagnostic_results.md")
        or terminal["source_lineage_sha256"] != sha256_file(root / "source_lineage.json")
        or terminal["diagnostic_continuation_only"] is not True
        or terminal["decision_promotion_allowed"] is not False
    ):
        raise RuntimeError("candidate terminal mismatch")
    _require_aware_timestamp(terminal.get("ended_utc"), "candidate terminal")
    if require_success:
        validate_success_closure("candidate", root)
    return {"result": result, "terminal": terminal, "content_sha256": content_digest(root),
            "terminal_sha256": sha256_file(root / "CANDIDATE_COMPLETE.json")}


def _candidate_review(path: Path, schema: str, candidate: dict[str, Any]) -> dict[str, Any]:
    review = strict_json(path)
    transcript = ROOT / str(review.get("transcript_path"))
    try:
        transcript_bytes, _ = _regular_file_bytes(transcript)
    except (OSError, RuntimeError):
        transcript_bytes = b""
    expected_keys = {
        "schema_version", "origin", "verdict", "candidate_content_sha256",
        "candidate_terminal_sha256", "transcript_path", "transcript_sha256",
    }
    if (
        set(review) != expected_keys
        or review.get("schema_version") != schema
        or review.get("origin") != "forked"
        or review.get("verdict") != "SHIP"
        or review.get("candidate_content_sha256") != candidate["content_sha256"]
        or review.get("candidate_terminal_sha256") != candidate["terminal_sha256"]
        or review.get("transcript_sha256") != sha256_bytes(transcript_bytes)
        or not transcript_bytes.decode("utf-8").startswith("VERDICT: SHIP")
    ):
        raise RuntimeError(f"candidate review mismatch: {path}")
    return review


def verify_promotion_freeze() -> dict[str, Any]:
    verify_execution_owner_mount()
    initial = verify_initial_freeze()
    candidate = validate_candidate(require_success=True)
    result_review = _candidate_review(
        RESULT_REVIEW, "atlas_completion_summary_recovery_result_review_v1", candidate)
    claim_review = _candidate_review(
        CLAIM_REVIEW, "atlas_completion_summary_recovery_claim_review_v1", candidate)
    record = strict_json(PROMOTION_FREEZE)
    material = {
        "candidate_content_sha256": candidate["content_sha256"],
        "candidate_files": content_inventory(candidate_root()),
        "candidate_terminal_sha256": candidate["terminal_sha256"],
        "claim_review_sha256": claim_review["transcript_sha256"],
        "initial_recovery_bundle_sha256": initial["bundle_sha256"],
        "result_review_sha256": result_review["transcript_sha256"],
    }
    digest = sha256_bytes(canonical_json_bytes(material, newline=False))
    if (
        record.get("schema_version") != "atlas_completion_summary_recovery_promotion_freeze_v1"
        or record.get("bundle_material") != material
        or record.get("bundle_sha256") != digest
        or record.get("diagnostic_continuation_only") is not True
        or record.get("decision_promotion_allowed") is not False
    ):
        raise RuntimeError("summary-recovery promotion freeze mismatch")
    return record


def validate_result_contract(result: dict[str, Any]) -> None:
    expected_disposition = {
        "original_G1": "equivocal_unchanged",
        "original_G2": "equivocal_unchanged",
        "G1a": "invalid_unrendered",
        "G2a": "not_promotable_unrendered",
        "paper_branch": "unselected",
        "training_warranted": False,
        "diagnostic_continuation_only": True,
        "decision_promotion_allowed": False,
    }
    incident = verify_incident_inputs()
    execution = result.get("execution", {})
    accounting = execution.get("resource_accounting", {})
    continuation_actual = sum(
        float(row["actual_gpu_hours"]) for row in incident["collection"]["jobs"].values())
    if (
        set(result) != {"schema_version", "evidence_class", "provenance", "execution", "k2",
                        "stability", "specificity", "disposition", "limitations"}
        or result.get("schema_version") != "atlas_completion_diagnostic_continuation_results_v1"
        or result.get("evidence_class") != "postscore_amended_architecture_evidence"
        or result.get("disposition") != expected_disposition
        or result.get("provenance", {}).get("continuation_bundle_sha256")
        != config()["original_continuation_bundle_sha256"]
        or result.get("provenance", {}).get("final_unlock_present") is not False
        or set(result.get("k2", {})) != set(JOBS)
        or set(result.get("specificity", {})) != set(JOBS)
        or execution.get("jobs") != incident["collection"]["jobs"]
        or execution.get("stages") != incident["collection"]["stages"]
        or execution.get("forbidden_activity_checks", {}).get("blind_final_unlock_present") is not False
        or abs(float(accounting.get("continuation_actual_gpu_hours", -1)) - continuation_actual) > 1e-9
        or abs(float(accounting.get("continuation_maximum_potential_reserved_gpu_hours", -1)) - 54.2) > 1e-9
        or accounting.get("maximum_total_gpu_hours") != 192
        or set(result.get("limitations", {})) != {
            "all_diagnostic_stages_complete", "unavailable_or_invalid_evidence",
            "job_stop_reasons", "stage_stop_reasons"}
    ):
        raise RuntimeError("diagnostic result contract drift")


def validate_canonical(root: Path | None = None, *, require_success: bool = True) -> dict[str, Any]:
    root = root or canonical_root()
    promotion = verify_promotion_freeze()
    candidate = validate_candidate(require_success=True)
    expected_terminal = (
        "MEASUREMENT_COMPLETE.json"
        if candidate["result"]["limitations"]["all_diagnostic_stages_complete"] is True
        else "FROZEN_EQUIVOCAL_STOP.json"
    )
    expected_names = {
        "diagnostic_results.json", "diagnostic_results.md", "source_lineage.json",
        "RECOVERY_PROVENANCE.json", expected_terminal,
    }
    if (not root.is_dir() or root.is_symlink()
            or {p.name for p in root.iterdir()} != expected_names
            or any(not p.is_file() or p.is_symlink() for p in root.iterdir())):
        raise RuntimeError("canonical root inventory mismatch")
    for name in ["diagnostic_results.json", "diagnostic_results.md", "source_lineage.json"]:
        if sha256_file(root / name) != sha256_file(candidate_root() / name):
            raise RuntimeError(f"canonical content differs from reviewed candidate: {name}")
    provenance = strict_json(root / "RECOVERY_PROVENANCE.json")
    terminal = strict_json(root / expected_terminal)
    provenance_keys = {
        "schema_version", "candidate_content_sha256", "candidate_terminal_sha256",
        "completion_bundle_sha256", "recovery_bundle_sha256", "promotion_bundle_sha256",
        "failed_summarize_terminal_sha256", "failed_summarize_log_sha256",
        "diagnostic_continuation_only", "decision_promotion_allowed", "published_utc",
    }
    if (
        set(provenance) != provenance_keys
        or provenance.get("schema_version") != "atlas_completion_summary_recovery_provenance_v1"
        or provenance.get("candidate_content_sha256") != candidate["content_sha256"]
        or provenance.get("candidate_terminal_sha256") != candidate["terminal_sha256"]
        or provenance.get("completion_bundle_sha256") != config()["original_continuation_bundle_sha256"]
        or provenance.get("recovery_bundle_sha256") != verify_initial_freeze()["bundle_sha256"]
        or provenance.get("promotion_bundle_sha256") != promotion["bundle_sha256"]
        or provenance.get("failed_summarize_terminal_sha256") != config()["failed_summarize_terminal_sha256"]
        or provenance.get("failed_summarize_log_sha256") != config()["failed_summarize_log_sha256"]
        or provenance.get("diagnostic_continuation_only") is not True
        or provenance.get("decision_promotion_allowed") is not False
    ):
        raise RuntimeError("canonical recovery provenance mismatch")
    _require_aware_timestamp(provenance.get("published_utc"), "canonical provenance")
    required_terminal = {
        "schema_version", "terminal_state", "reason", "result_sha256", "report_sha256",
        "source_lineage_sha256", "recovery_provenance_sha256", "candidate_content_sha256",
        "candidate_terminal_sha256", "completion_bundle_sha256", "recovery_bundle_sha256",
        "promotion_bundle_sha256", "failed_summarize_terminal_sha256",
        "failed_summarize_log_sha256", "diagnostic_continuation_only",
        "decision_promotion_allowed", "evidence_class", "ended_utc",
    }
    expected_state = "measurement_complete" if expected_terminal.startswith("MEASUREMENT") else "frozen_equivocal_stop"
    expected_reason = None if expected_state == "measurement_complete" else "one_or_more_diagnostics_stopped_or_unavailable"
    if (
        set(terminal) != required_terminal
        or terminal.get("schema_version") != "atlas_completion_summary_recovery_canonical_terminal_v1"
        or terminal.get("terminal_state") != expected_state
        or terminal.get("reason") != expected_reason
        or terminal.get("result_sha256") != sha256_file(root / "diagnostic_results.json")
        or terminal.get("report_sha256") != sha256_file(root / "diagnostic_results.md")
        or terminal.get("source_lineage_sha256") != sha256_file(root / "source_lineage.json")
        or terminal.get("recovery_provenance_sha256") != sha256_file(root / "RECOVERY_PROVENANCE.json")
        or terminal.get("candidate_content_sha256") != candidate["content_sha256"]
        or terminal.get("candidate_terminal_sha256") != candidate["terminal_sha256"]
        or terminal.get("completion_bundle_sha256") != config()["original_continuation_bundle_sha256"]
        or terminal.get("recovery_bundle_sha256") != verify_initial_freeze()["bundle_sha256"]
        or terminal.get("promotion_bundle_sha256") != promotion["bundle_sha256"]
        or terminal.get("failed_summarize_terminal_sha256") != config()["failed_summarize_terminal_sha256"]
        or terminal.get("failed_summarize_log_sha256") != config()["failed_summarize_log_sha256"]
        or terminal.get("diagnostic_continuation_only") is not True
        or terminal.get("decision_promotion_allowed") is not False
        or terminal.get("evidence_class") != "postscore_amended_architecture_evidence"
    ):
        raise RuntimeError("canonical terminal mismatch")
    _require_aware_timestamp(terminal.get("ended_utc"), "canonical terminal")
    if require_success:
        validate_success_closure("publish", root)
    return {"result": strict_json(root / "diagnostic_results.json"), "terminal": terminal,
            "root_sha256": root_digest(root)}


def _unique_mapping(rows: Iterable[dict[str, Any]], key: str, value_keys: tuple[str, ...], label: str) -> dict[str, tuple[str, ...]]:
    result: dict[str, tuple[str, ...]] = {}
    for row in rows:
        name = str(row.get(key, ""))
        value = tuple(str(row.get(field, "")) for field in value_keys)
        if not name or any(not item for item in value):
            raise RuntimeError(f"empty {label} mapping")
        if name in result and result[name] != value:
            raise RuntimeError(f"conflicting duplicate {label}: {name}")
        result[name] = value
    return result


def resolve_expected_sources() -> tuple[dict[str, dict[str, set[str]]], dict[str, Any]]:
    incident = verify_incident_inputs()
    row_manifest = strict_json(ROOT / incident["config"]["task_row_manifest_path"])
    activation_source_root = ROOT / incident["config"]["source_run_root"]
    if activation_source_root.resolve() != (ROOT / config()["source_run_root"]).resolve():
        raise RuntimeError("recovery source-run root drift")
    firewall = continuation_firewall(activation_source_root, CONTINUATION_RUN_ROOT)
    expected: dict[str, dict[str, set[str]]] = {}
    report: dict[str, Any] = {
        "schema_version": "atlas_completion_summary_source_lineage_v1",
        "roles": {},
        "input_sha256": {},
        "all_rows_match": True,
    }
    token_re = re.compile(r"^[0-9]+$")
    for role in ROLES:
        data = load_activation(role, 3, activation_source_root, firewall)
        unit_index = np.asarray(data.meta.get("unit_index"))
        record_index = np.asarray(data.meta.get("record_index"))
        if (
            unit_index.ndim != 1 or record_index.ndim != 1
            or len(unit_index) != len(record_index) or len(unit_index) != len(data.x)
            or np.any(unit_index < 0) or np.any(unit_index >= len(data.units))
            or np.any(record_index < 0) or np.any(record_index >= len(data.records))
        ):
            raise RuntimeError(f"activation metadata bounds mismatch: {role}")
        counts = np.bincount(unit_index, minlength=len(data.units))
        if not np.array_equal(unit_index, np.repeat(np.arange(len(data.units)), counts)):
            raise RuntimeError(f"activation rows are not grouped by unit: {role}")
        starts = np.concatenate([[0], np.cumsum(counts[:-1])])
        activation_units = _unique_mapping(data.units, "variant_id", ("base_id",), f"activation unit/{role}")
        activation_positions = {str(item["variant_id"]): i for i, item in enumerate(data.units)}
        activation_records = _unique_mapping(
            data.records, "base_id", ("source", "document_group"), f"activation record/{role}")
        lineage = incident["config"]["partition_lineage"][role]
        partition_units = _unique_mapping(
            strict_jsonl(ROOT / lineage["units_path"]),
            "variant_id", ("base_id",), f"partition unit/{role}")
        partition_records = _unique_mapping(
            strict_jsonl(ROOT / lineage["records_path"]),
            "base_id", ("source", "document_group"), f"partition record/{role}")
        if (
            any(partition_units.get(key) != value for key, value in activation_units.items())
            or any(partition_records.get(key) != value for key, value in activation_records.items())
        ):
            raise RuntimeError(f"activation/partition lineage mapping mismatch: {role}")
        expected[role] = {}
        role_report: dict[str, Any] = {"tasks": {}}
        for task in TASKS:
            manifest_row = row_manifest["roles"][role][task]
            task_path = ROOT / manifest_row["path"]
            require_hash(task_path, manifest_row["sha256"])
            indices, _, scoring_sources, scoring_groups = load_row_file(
                task_path, data, firewall, role=role)
            rows = strict_jsonl(task_path)
            if len(rows) != len(indices):
                raise RuntimeError(f"task/scoring row-count mismatch: {role}/{task}")
            seen: set[str] = set()
            partition_sources: list[str] = []
            partition_groups: list[str] = []
            for offset, row in enumerate(rows):
                row_id = str(row.get("row_id", ""))
                if row_id in seen or ":" not in row_id:
                    raise RuntimeError(f"duplicate or malformed row ID: {role}/{task}/{row_id}")
                seen.add(row_id)
                variant, token_text = row_id.rsplit(":", 1)
                if not token_re.fullmatch(token_text):
                    raise RuntimeError(f"invalid token index: {row_id}")
                token = int(token_text)
                if variant not in partition_units:
                    raise RuntimeError(f"missing partition variant: {row_id}")
                base_id = partition_units[variant][0]
                if base_id not in partition_records:
                    raise RuntimeError(f"missing partition record: {base_id}")
                activation_position = activation_positions.get(variant)
                if activation_position is None or token >= int(counts[activation_position]):
                    raise RuntimeError(f"token index outside activation unit: {row_id}")
                expected_index = int(starts[activation_position] + token)
                if expected_index != int(indices[offset]) or expected_index >= len(data.x):
                    raise RuntimeError(f"resolved activation row mismatch: {row_id}")
                activation_record = data.records[int(record_index[expected_index])]
                if str(activation_record.get("base_id", "")) != base_id:
                    raise RuntimeError(f"activation row/base lineage mismatch: {row_id}")
                source, group = partition_records[base_id]
                partition_sources.append(source)
                partition_groups.append(group)
            if (
                partition_sources != scoring_sources.tolist()
                or partition_groups != scoring_groups.tolist()
            ):
                raise RuntimeError(f"per-row source/group lineage mismatch: {role}/{task}")
            sources = set(partition_sources)
            if not sources:
                raise RuntimeError(f"empty task source inventory: {role}/{task}")
            expected[role][task] = sources
            role_report["tasks"][task] = {
                "rows": len(rows), "matching_rows": len(rows),
                "sources": sorted(sources), "document_groups": len(set(partition_groups)),
                "task_rows_sha256": sha256_file(task_path),
            }
        report["roles"][role] = role_report
        for name in ["L3.float16.npy", "row_meta.npz", "records.jsonl", "units.json", "COMPLETE.json"]:
            path = activation_source_root / "raw_activations" / role / name
            if not path.is_file():
                raise RuntimeError(f"activation lineage input is absent: {path}")
            report["input_sha256"][str(path.relative_to(ROOT))] = sha256_file(path)
        report["input_sha256"][lineage["records_path"]] = sha256_file(ROOT / lineage["records_path"])
        report["input_sha256"][lineage["units_path"]] = sha256_file(ROOT / lineage["units_path"])
    for job in JOBS:
        point = strict_json(CONTINUATION_RUN_ROOT / "k2_refit" / job / "point.json")
        for key, source_rows in point["result"]["source_detail"].items():
            _, task = key.split(":", 1)
            if set(source_rows) != expected["C2"][task]:
                raise RuntimeError(f"K2 point source inventory mismatch: {job}/{key}")
    report["input_sha256"][incident["config"]["task_row_manifest_path"]] = sha256_file(
        ROOT / incident["config"]["task_row_manifest_path"])
    report["expected_sources"] = {
        role: {task: sorted(values) for task, values in tasks.items()}
        for role, tasks in expected.items()
    }
    return expected, report


def fsync_file(path: Path) -> None:
    _fsync_regular_file(path)


def _regular_file_bytes(path: Path) -> tuple[bytes, os.stat_result]:
    flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0)
    fd = os.open(path, flags)
    try:
        before = os.fstat(fd)
        if not stat.S_ISREG(before.st_mode):
            raise RuntimeError(f"evidence path is not a regular file: {path}")
        chunks: list[bytes] = []
        while True:
            chunk = os.read(fd, 1024 * 1024)
            if not chunk:
                break
            chunks.append(chunk)
        after = os.fstat(fd)
        if (before.st_dev, before.st_ino, before.st_size) != (
                after.st_dev, after.st_ino, after.st_size):
            raise RuntimeError(f"evidence file changed while reading: {path}")
        named = os.lstat(path)
        if (not stat.S_ISREG(named.st_mode)
                or (named.st_dev, named.st_ino) != (after.st_dev, after.st_ino)):
            raise RuntimeError(f"evidence pathname changed while reading: {path}")
        return b"".join(chunks), after
    finally:
        os.close(fd)


def regular_file_facts(path: Path) -> dict[str, Any]:
    payload, row = _regular_file_bytes(path)
    return {
        "sha256": sha256_bytes(payload), "size": len(payload),
        "st_dev": int(row.st_dev), "st_ino": int(row.st_ino), "regular": True,
    }


def _fsync_regular_file(path: Path) -> os.stat_result:
    flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0)
    fd = os.open(path, flags)
    try:
        row = os.fstat(fd)
        if not stat.S_ISREG(row.st_mode):
            raise RuntimeError(f"fsync target is not a regular file: {path}")
        os.fsync(fd)
        named = os.lstat(path)
        if (not stat.S_ISREG(named.st_mode)
                or (named.st_dev, named.st_ino) != (row.st_dev, row.st_ino)):
            raise RuntimeError(f"fsync target pathname changed: {path}")
        return row
    finally:
        os.close(fd)


def fsync_directory(path: Path) -> None:
    flags = (os.O_RDONLY | getattr(os, "O_DIRECTORY", 0)
             | getattr(os, "O_NOFOLLOW", 0))
    fd = os.open(path, flags)
    try:
        row = os.fstat(fd)
        if not stat.S_ISDIR(row.st_mode):
            raise RuntimeError(f"fsync target is not a directory: {path}")
        os.fsync(fd)
        named = os.lstat(path)
        if (not stat.S_ISDIR(named.st_mode)
                or (named.st_dev, named.st_ino) != (row.st_dev, row.st_ino)):
            raise RuntimeError(f"fsync directory pathname changed: {path}")
    finally:
        os.close(fd)


def fsync_tree(root: Path) -> None:
    for path in sorted(root.iterdir()):
        if path.is_file():
            fsync_file(path)
    fsync_directory(root)


def write_once_bytes(path: Path, payload: bytes) -> str:
    """Durably publish immutable evidence and reconcile ambiguous NFS returns."""

    if not path.parent.is_dir() or path.parent.is_symlink():
        raise RuntimeError(f"write-once evidence parent is not precreated: {path.parent}")
    expected = sha256_bytes(payload)
    if path.exists() or path.is_symlink():
        try:
            existing, existing_stat = _regular_file_bytes(path)
        except (OSError, RuntimeError) as exc:
            raise RuntimeError(f"conflicting or malformed write-once record: {path}") from exc
        if sha256_bytes(existing) != expected or existing != payload:
            raise RuntimeError(f"conflicting or malformed write-once record: {path}")
        _fsync_regular_file(path)
        after_file, after_file_stat = _regular_file_bytes(path)
        if (after_file != payload
                or (after_file_stat.st_dev, after_file_stat.st_ino)
                != (existing_stat.st_dev, existing_stat.st_ino)):
            raise RuntimeError(f"write-once record changed after file fsync: {path}")
        fsync_directory(path.parent)
        after_parent, after_parent_stat = _regular_file_bytes(path)
        if (after_parent != payload
                or (after_parent_stat.st_dev, after_parent_stat.st_ino)
                != (existing_stat.st_dev, existing_stat.st_ino)):
            raise RuntimeError(f"write-once record changed after parent fsync: {path}")
        return expected
    temporary = path.parent / f".{path.name}.write_once.{os.getpid()}.{secrets.token_hex(8)}"
    fd = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
    except BaseException:
        raise
    link_error: OSError | None = None
    try:
        os.link(temporary, path)
    except OSError as exc:
        link_error = exc
    try:
        final_bytes, final_stat = _regular_file_bytes(path)
        final_valid = sha256_bytes(final_bytes) == expected and final_bytes == payload
    except (OSError, RuntimeError):
        final_stat, final_valid = None, False
    try:
        temp_bytes, temp_stat = _regular_file_bytes(temporary)
        temp_valid = sha256_bytes(temp_bytes) == expected and temp_bytes == payload
    except (OSError, RuntimeError):
        temp_stat, temp_valid = None, False
    if final_valid:
        if (link_error is None or link_error.errno != errno.EEXIST) and (
            final_stat is None or temp_stat is None
            or (final_stat.st_dev, final_stat.st_ino) != (temp_stat.st_dev, temp_stat.st_ino)
        ):
            raise RuntimeError(f"write-once link did not preserve inode identity: {path}")
        _fsync_regular_file(path)
        after_file, after_file_stat = _regular_file_bytes(path)
        if (after_file != payload or final_stat is None
                or (after_file_stat.st_dev, after_file_stat.st_ino)
                != (final_stat.st_dev, final_stat.st_ino)):
            raise RuntimeError(f"write-once final changed after file fsync: {path}")
        fsync_directory(path.parent)
        after_parent, after_parent_stat = _regular_file_bytes(path)
        if (after_parent != payload
                or (after_parent_stat.st_dev, after_parent_stat.st_ino)
                != (after_file_stat.st_dev, after_file_stat.st_ino)):
            raise RuntimeError(f"write-once final changed after parent fsync: {path}")
        return expected
    if path.exists() or path.is_symlink():
        raise RuntimeError(f"write-once final record conflicts after link: {path}")
    if not temp_valid:
        raise RuntimeError(f"write-once publication lost both valid names: {path}")
    if link_error is not None:
        raise link_error
    raise RuntimeError(f"write-once publication did not produce a final record: {path}")


def write_once_json(path: Path, payload: Any) -> str:
    return write_once_bytes(path, canonical_json_bytes(payload))


def job_lock_path(job: str) -> Path:
    if job not in {"candidate", "publish"}:
        raise ValueError(f"invalid recovery job: {job}")
    return recovery_run_root() / "locks" / f"{job}.lock"


_SUPERVISOR_JOB: str | None = None
_SUPERVISOR_LOCK_FD: int | None = None
_SUPERVISOR_PID: int | None = None


@contextmanager
def supervisor_job_lock(job: str) -> Iterable[int]:
    """Own one job lock and process-lifetime guard for an entire attempt."""

    global _SUPERVISOR_JOB, _SUPERVISOR_LOCK_FD, _SUPERVISOR_PID
    if _SUPERVISOR_JOB is not None:
        raise RuntimeError("a recovery supervisor is already active in this process")
    path = job_lock_path(job)
    if not path.parent.is_dir() or path.parent.is_symlink():
        raise RuntimeError("recovery lock ancestry is not precreated")
    flags = os.O_RDWR | os.O_CREAT | getattr(os, "O_NOFOLLOW", 0)
    fd = os.open(path, flags, 0o600)
    try:
        descriptor = os.fstat(fd)
        if not stat.S_ISREG(descriptor.st_mode):
            raise RuntimeError("recovery job lock is not a regular file")
        os.fsync(fd)
        fsync_directory(path.parent)
        named = os.lstat(path)
        if (not stat.S_ISREG(named.st_mode)
                or (named.st_dev, named.st_ino)
                != (descriptor.st_dev, descriptor.st_ino)):
            raise RuntimeError("recovery job lock pathname changed during acquisition")
        try:
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError as exc:
            if exc.errno in {errno.EACCES, errno.EAGAIN}:
                raise RuntimeError("recovery job lock is held by another supervisor") from exc
            raise
        _SUPERVISOR_JOB, _SUPERVISOR_LOCK_FD, _SUPERVISOR_PID = job, fd, os.getpid()
        yield fd
    finally:
        _SUPERVISOR_JOB = _SUPERVISOR_LOCK_FD = _SUPERVISOR_PID = None
        os.close(fd)


def require_job_lock(job: str) -> int:
    if (
        _SUPERVISOR_JOB != job
        or _SUPERVISOR_LOCK_FD is None
        or _SUPERVISOR_PID != os.getpid()
    ):
        raise RuntimeError("recovery mutation lacks the active process-lifetime supervisor guard")
    fd = _SUPERVISOR_LOCK_FD
    try:
        descriptor = os.fstat(fd)
        expected = os.lstat(job_lock_path(job))
        if (not stat.S_ISREG(descriptor.st_mode)
                or not stat.S_ISREG(expected.st_mode)
                or (descriptor.st_dev, descriptor.st_ino) != (expected.st_dev, expected.st_ino)):
            raise RuntimeError("supervisor lock descriptor targets the wrong inode")
        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except (OSError, ValueError) as exc:
        raise RuntimeError("recovery job lock is not exclusively held") from exc
    return fd


ATTEMPT_RE = re.compile(r"^[0-9]{8}T[0-9]{6}Z_[0-9]+_[0-9a-f]{8}$")


def state_directory(job: str) -> Path:
    return recovery_run_root() / "job_state" / job


def state_path(job: str) -> Path:
    """Compatibility accessor returning the immutable current journal head."""

    head = read_state_chain(job)
    if head is None:
        return state_directory(job) / "ABSENT"
    return ROOT / head["_path"]


def _state_files(job: str) -> list[Path]:
    directory = state_directory(job)
    return sorted(directory.glob("g[0-9][0-9][0-9][0-9][0-9][0-9].json")) if directory.is_dir() else []


STATE_TRANSITIONS = {
    "building": {"building", "ready_to_publish"},
    "ready_to_publish": {"ready_to_publish", "root_reserved", "reconciling"},
    "root_reserved": {"root_reserved", "files_publishing", "terminal_published", "reconciling"},
    "files_publishing": {"files_publishing", "terminal_published", "reconciling"},
    "terminal_published": {
        "terminal_published", "destination_fsync_complete", "reconciling"},
    "destination_fsync_complete": {
        "destination_fsync_complete", "parent_fsync_complete", "reconciling"},
    "parent_fsync_complete": {"parent_fsync_complete", "reconciling"},
    "reconciling": {
        "reconciling", "root_reserved", "files_publishing", "terminal_published",
        "destination_fsync_complete", "parent_fsync_complete",
    },
}


def _validate_state_semantics(row: dict[str, Any], previous: dict[str, Any] | None,
                              *, label: str) -> None:
    phase = row.get("phase")
    publication = row.get("publication_inventory")
    staging = row.get("staging_inventory")
    published = row.get("published_files")
    if (
        phase not in STATE_TRANSITIONS
        or not isinstance(publication, list)
        or not isinstance(staging, list)
        or not isinstance(published, list)
        or published != [item.get("path") for item in publication[:len(published)]]
    ):
        raise RuntimeError(f"recovery state semantic mismatch: {label}")
    complete = bool(publication) and (
        staging == sorted(staging, key=lambda item: item.get("path", ""))
        and {item.get("path"): item for item in staging}
        == {item.get("path"): item for item in publication}
        and len({item.get("path") for item in publication}) == len(publication)
        and _valid_digest(row.get("destination_root_sha256"))
        and inventory_digest(staging) == row.get("destination_root_sha256")
    )
    attempted = row.get("root_reservation_attempted") is True
    confirmed = row.get("root_reservation_confirmed") is True
    identity_confirmed = (
        isinstance(row.get("destination_st_dev"), int)
        and row["destination_st_dev"] >= 0
        and isinstance(row.get("destination_st_ino"), int)
        and row["destination_st_ino"] > 0
    )
    identity_absent = (
        row.get("destination_st_dev") is None and row.get("destination_st_ino") is None)
    parent_complete = row.get("parent_fsync_complete") is True
    prefix_length, total = len(published), len(publication)
    valid_phase = False
    if phase == "building":
        valid_phase = (
            publication == [] and staging == [] and published == []
            and row.get("destination_root_sha256") is None
            and not attempted and not confirmed and identity_absent and not parent_complete
        )
    elif phase == "ready_to_publish":
        valid_phase = complete and prefix_length == 0 and not attempted and not confirmed \
            and identity_absent \
            and not parent_complete
    elif phase == "reconciling":
        valid_phase = complete and 0 <= prefix_length <= total and not parent_complete \
            and (not confirmed or attempted) \
            and (identity_confirmed if confirmed else identity_absent)
    elif phase == "root_reserved":
        valid_phase = complete and prefix_length == 0 and attempted and confirmed \
            and identity_confirmed \
            and not parent_complete
    elif phase == "files_publishing":
        valid_phase = complete and 1 <= prefix_length < total and attempted and confirmed \
            and identity_confirmed \
            and not parent_complete
    elif phase in {"terminal_published", "destination_fsync_complete"}:
        valid_phase = complete and prefix_length == total and attempted and confirmed \
            and identity_confirmed \
            and not parent_complete
    elif phase == "parent_fsync_complete":
        valid_phase = complete and prefix_length == total and attempted and confirmed \
            and identity_confirmed \
            and parent_complete
    if not valid_phase:
        raise RuntimeError(f"recovery state phase/prefix invariant mismatch: {label}")
    if previous is None:
        if phase != "building":
            raise RuntimeError(f"recovery state must begin in building: {label}")
        return
    if row.get("active_attempt_id") != previous.get("active_attempt_id"):
        if phase != "reconciling":
            raise RuntimeError(f"new recovery attempt did not enter reconciling: {label}")
    elif phase not in STATE_TRANSITIONS[str(previous.get("phase"))]:
        raise RuntimeError(
            f"illegal recovery state transition {previous.get('phase')} -> {phase}: {label}")


def read_state_chain(job: str) -> dict[str, Any] | None:
    previous_path: str | None = None
    previous_sha: str | None = None
    head: dict[str, Any] | None = None
    for generation, path in enumerate(_state_files(job), start=1):
        if path.name != f"g{generation:06d}.json":
            raise RuntimeError(f"recovery state journal gap or fork: {job}/{path.name}")
        row = strict_json(path)
        required = {
            "schema_version", "job", "generation", "previous_path", "previous_sha256",
            "phase", "active_attempt_id", "publication_attempt_id", "staging",
            "destination", "destination_root_sha256", "staging_inventory",
            "publication_inventory",
            "published_files", "root_reservation_attempted",
            "root_reservation_confirmed", "destination_st_dev", "destination_st_ino",
            "initial_recovery_bundle_sha256",
            "promotion_bundle_sha256", "parent_fsync_complete", "error_type",
            "error_message", "error_errno", "created_utc",
        }
        if (
            set(row) != required
            or row.get("schema_version") != "atlas_completion_summary_recovery_job_state_v4"
            or row.get("job") != job
            or row.get("generation") != generation
            or row.get("previous_path") != previous_path
            or row.get("previous_sha256") != previous_sha
            or not ATTEMPT_RE.fullmatch(str(row.get("active_attempt_id", "")))
            or not ATTEMPT_RE.fullmatch(str(row.get("publication_attempt_id", "")))
            or row.get("phase") not in {
                "building", "ready_to_publish", "reconciling", "root_reserved",
                "files_publishing", "terminal_published",
                "destination_fsync_complete", "parent_fsync_complete",
            }
            or not isinstance(row.get("parent_fsync_complete"), bool)
            or not isinstance(row.get("root_reservation_attempted"), bool)
            or not isinstance(row.get("root_reservation_confirmed"), bool)
            or (row.get("root_reservation_confirmed") is True
                and row.get("root_reservation_attempted") is not True)
            or (row.get("root_reservation_confirmed") is True and (
                not isinstance(row.get("destination_st_dev"), int)
                or not isinstance(row.get("destination_st_ino"), int)
                or row["destination_st_dev"] < 0 or row["destination_st_ino"] <= 0))
            or (row.get("root_reservation_confirmed") is False and (
                row.get("destination_st_dev") is not None
                or row.get("destination_st_ino") is not None))
            or not isinstance(row.get("publication_inventory"), list)
            or not isinstance(row.get("staging_inventory"), list)
            or not all(
                isinstance(item, dict)
                and set(item) == {"path", "sha256", "size"}
                and isinstance(item.get("path"), str)
                and item["path"] == Path(item["path"]).name
                and item["path"] not in {"", ".", ".."}
                and re.fullmatch(r"[0-9a-f]{64}", str(item.get("sha256")))
                and isinstance(item.get("size"), int)
                and item["size"] >= 0
                for item in [*row.get("publication_inventory", []),
                             *row.get("staging_inventory", [])])
            or not isinstance(row.get("published_files"), list)
            or row.get("published_files") != [
                item["path"] for item in row.get("publication_inventory", [])
                ][:len(row.get("published_files", []))]
        ):
            raise RuntimeError(f"recovery state journal mismatch: {path}")
        if row["publication_inventory"] and (
            not re.fullmatch(r"[0-9a-f]{64}", str(row.get("destination_root_sha256")))
            or row["phase"] == "building"
            or row["staging_inventory"]
            != sorted(row["staging_inventory"], key=lambda item: item["path"])
            or {item["path"]: item for item in row["staging_inventory"]}
            != {item["path"]: item for item in row["publication_inventory"]}
            or inventory_digest(row["staging_inventory"])
            != row["destination_root_sha256"]
        ):
            raise RuntimeError(f"recovery ready-state binding mismatch: {path}")
        if row["phase"] in {
            "root_reserved", "files_publishing", "terminal_published",
            "destination_fsync_complete", "parent_fsync_complete",
        } and row["root_reservation_confirmed"] is not True:
            raise RuntimeError(f"recovery state advances without root ownership: {path}")
        if row["parent_fsync_complete"] is not (row["phase"] == "parent_fsync_complete"):
            raise RuntimeError(f"recovery parent-fsync phase mismatch: {path}")
        if head is not None:
            immutable = {
                "publication_attempt_id", "staging", "destination",
                "initial_recovery_bundle_sha256", "promotion_bundle_sha256",
            }
            if any(row[key] != head[key] for key in immutable):
                raise RuntimeError(f"recovery state immutable binding changed: {path}")
            if head["destination_root_sha256"] is not None and (
                row["destination_root_sha256"] != head["destination_root_sha256"]
                or row["staging_inventory"] != head["staging_inventory"]
                or row["publication_inventory"] != head["publication_inventory"]
            ):
                raise RuntimeError(f"recovery publication inventory changed: {path}")
            if (
                head["root_reservation_attempted"] and not row["root_reservation_attempted"]
                or head["root_reservation_confirmed"] and not row["root_reservation_confirmed"]
                or head["root_reservation_confirmed"] and (
                    row["destination_st_dev"] != head["destination_st_dev"]
                    or row["destination_st_ino"] != head["destination_st_ino"])
                or len(row["published_files"]) < len(head["published_files"])
            ):
                raise RuntimeError(f"recovery state progress regressed: {path}")
        _validate_state_semantics(row, head, label=str(path))
        _require_aware_timestamp(row.get("created_utc"), "state generation")
        previous_path = str(path.relative_to(ROOT))
        previous_sha = sha256_file(path)
        head = {**row, "_path": previous_path, "_sha256": previous_sha}
    return head


def append_state(job: str, attempt_id: str, payload: dict[str, Any], *,
                 claim: bool = False, expected_generation: int | None = None) -> dict[str, Any]:
    require_job_lock(job)
    if not ATTEMPT_RE.fullmatch(attempt_id):
        raise ValueError("invalid recovery attempt ID")
    head = read_state_chain(job)
    current_generation = 0 if head is None else int(head["generation"])
    if expected_generation is not None and expected_generation != current_generation:
        raise RuntimeError("recovery state generation compare-and-swap failed")
    if not claim and (head is None or head["active_attempt_id"] != attempt_id):
        raise RuntimeError("recovery state attempt owner mismatch")
    publication = str(payload.get(
        "publication_attempt_id", attempt_id if head is None else head["publication_attempt_id"]))
    if head is not None and publication != head["publication_attempt_id"]:
        raise RuntimeError("recovery publication attempt changed")
    values = {
        "phase": payload.get("phase"),
        "active_attempt_id": attempt_id,
        "publication_attempt_id": publication,
        "staging": payload.get("staging", None if head is None else head["staging"]),
        "destination": payload.get("destination", None if head is None else head["destination"]),
        "destination_root_sha256": payload.get(
            "destination_root_sha256", None if head is None else head["destination_root_sha256"]),
        "publication_inventory": payload.get(
            "publication_inventory", [] if head is None else head["publication_inventory"]),
        "staging_inventory": payload.get(
            "staging_inventory", [] if head is None else head["staging_inventory"]),
        "published_files": payload.get(
            "published_files", [] if head is None else head["published_files"]),
        "root_reservation_attempted": bool(payload.get(
            "root_reservation_attempted", False if head is None
            else head["root_reservation_attempted"])),
        "root_reservation_confirmed": bool(payload.get(
            "root_reservation_confirmed", False if head is None
            else head["root_reservation_confirmed"])),
        "destination_st_dev": payload.get(
            "destination_st_dev", None if head is None else head["destination_st_dev"]),
        "destination_st_ino": payload.get(
            "destination_st_ino", None if head is None else head["destination_st_ino"]),
        "initial_recovery_bundle_sha256": payload.get(
            "initial_recovery_bundle_sha256",
            verify_initial_freeze()["bundle_sha256"] if head is None
            else head["initial_recovery_bundle_sha256"]),
        "promotion_bundle_sha256": payload.get(
            "promotion_bundle_sha256", None if head is None else head["promotion_bundle_sha256"]),
        "parent_fsync_complete": bool(payload.get("parent_fsync_complete", False)),
        "error_type": payload.get("error_type"),
        "error_message": payload.get("error_message"),
        "error_errno": payload.get("error_errno"),
    }
    if not values["phase"] or not values["destination"]:
        raise RuntimeError("recovery state lacks phase or destination")
    if head is not None:
        immutable = {
            "publication_attempt_id", "staging", "destination",
            "initial_recovery_bundle_sha256", "promotion_bundle_sha256",
        }
        if any(values[key] != head[key] for key in immutable):
            raise RuntimeError("recovery state immutable binding changed before publication")
        if head["destination_root_sha256"] is not None and (
            values["destination_root_sha256"] != head["destination_root_sha256"]
            or values["staging_inventory"] != head["staging_inventory"]
            or values["publication_inventory"] != head["publication_inventory"]
        ):
            raise RuntimeError("recovery publication inventory changed before publication")
        if (
            head["root_reservation_attempted"] and not values["root_reservation_attempted"]
            or head["root_reservation_confirmed"] and not values["root_reservation_confirmed"]
            or head["root_reservation_confirmed"] and (
                values["destination_st_dev"] != head["destination_st_dev"]
                or values["destination_st_ino"] != head["destination_st_ino"])
            or len(values["published_files"]) < len(head["published_files"])
        ):
            raise RuntimeError("recovery state progress regressed before publication")
    generation = current_generation + 1
    path = state_directory(job) / f"g{generation:06d}.json"
    row = {
        "schema_version": "atlas_completion_summary_recovery_job_state_v4",
        "job": job, "generation": generation,
        "previous_path": None if head is None else head["_path"],
        "previous_sha256": None if head is None else head["_sha256"],
        **values, "created_utc": utc_now(),
    }
    _validate_state_semantics(row, head, label=str(path))
    write_once_json(path, row)
    replayed = read_state_chain(job)
    if replayed is None or replayed["generation"] != generation:
        raise RuntimeError("recovery state journal publication did not advance")
    return replayed


def _validate_state_snapshot(path: Path, *, job: str, attempt_id: str) -> dict[str, Any]:
    if path != recovery_run_root() / "job_state" / f"{job}.{attempt_id}.json" \
            or not path.is_file() or path.is_symlink():
        raise RuntimeError("attempt state snapshot path mismatch")
    row = strict_json(path)
    if (
        set(row) != {
            "schema_version", "job", "attempt_id", "state_status", "state_path",
            "state_sha256", "state_generation", "observed_head_path",
            "observed_head_sha256", "observed_head_generation", "created_utc",
        }
        or row.get("schema_version")
        != "atlas_completion_summary_recovery_attempt_state_snapshot_v1"
        or row.get("job") != job
        or row.get("attempt_id") != attempt_id
        or row.get("state_status") not in {"present", "state_absent_for_attempt"}
    ):
        raise RuntimeError("attempt state snapshot identity mismatch")
    for prefix in ["state", "observed_head"]:
        relative = row[f"{prefix}_path"]
        digest = row[f"{prefix}_sha256"]
        generation = row[f"{prefix}_generation"]
        if relative is None:
            if digest is not None or generation is not None:
                raise RuntimeError("attempt state snapshot null binding mismatch")
        else:
            target = ROOT / relative
            try:
                target.relative_to(state_directory(job))
            except ValueError as exc:
                raise RuntimeError("attempt snapshot points outside its journal") from exc
            if (not target.is_file() or target.is_symlink() or sha256_file(target) != digest
                    or strict_json(target).get("generation") != generation):
                raise RuntimeError("attempt state snapshot journal binding mismatch")
    if row["state_status"] == "present" and row["state_path"] is None:
        raise RuntimeError("present attempt state snapshot lacks state")
    if row["state_status"] == "state_absent_for_attempt" and row["state_path"] is not None:
        raise RuntimeError("absent attempt state snapshot binds state")
    _require_aware_timestamp(row.get("created_utc"), "attempt state snapshot")
    return row


def snapshot_attempt_state(job: str, attempt_id: str) -> tuple[Path, dict[str, Any]]:
    require_job_lock(job)
    path = recovery_run_root() / "job_state" / f"{job}.{attempt_id}.json"
    if path.is_file() or path.is_symlink():
        row = _validate_state_snapshot(path, job=job, attempt_id=attempt_id)
        write_once_json(path, row)
        return path, _validate_state_snapshot(path, job=job, attempt_id=attempt_id)
    head = read_state_chain(job)
    belongs = head is not None and head["active_attempt_id"] == attempt_id
    row = {
        "schema_version": "atlas_completion_summary_recovery_attempt_state_snapshot_v1",
        "job": job, "attempt_id": attempt_id,
        "state_status": "present" if belongs else "state_absent_for_attempt",
        "state_path": head["_path"] if belongs else None,
        "state_sha256": head["_sha256"] if belongs else None,
        "state_generation": head["generation"] if belongs else None,
        "observed_head_path": None if head is None else head["_path"],
        "observed_head_sha256": None if head is None else head["_sha256"],
        "observed_head_generation": None if head is None else head["generation"],
        "created_utc": _validate_capability(
            capability_path(job, attempt_id), job=job, attempt_id=attempt_id)["tested_utc"],
    }
    write_once_json(path, row)
    return path, _validate_state_snapshot(path, job=job, attempt_id=attempt_id)


def _manifest_path(job: str, attempt_id: str) -> Path:
    return recovery_run_root() / "job_manifests" / f"{job}.{attempt_id}.manifest.json"


def _terminal_path(job: str, attempt_id: str) -> Path:
    return recovery_run_root() / "job_manifests" / f"{job}.{attempt_id}.terminal.json"


def create_attempt(job: str, attempt_id: str, argv: list[str], log: str, mode: str,
                   *, execution_owner_sha256: str, capability_path: str,
                   capability_sha256: str) -> Path:
    require_job_lock(job)
    if job not in {"candidate", "publish"} or mode not in {"run", "reconcile"}:
        raise ValueError("invalid recovery attempt")
    if not ATTEMPT_RE.fullmatch(attempt_id):
        raise ValueError("invalid recovery attempt ID")
    if not argv or not all(isinstance(item, str) and item for item in argv):
        raise ValueError("recovery attempt argv is empty or malformed")
    if success_path(job).exists():
        raise RuntimeError(f"job already has durable success closure: {job}")
    initial, promotion_sha = _applicable_freezes(job)
    log_path = ROOT / log
    try:
        log_path.relative_to(recovery_run_root() / "logs")
    except ValueError as exc:
        raise ValueError("recovery attempt log is outside the recovery log root") from exc
    path = _manifest_path(job, attempt_id)
    capability_file = ROOT / capability_path
    capability_row = _validate_capability(capability_file, job=job, attempt_id=attempt_id)
    if (
        capability_file != globals()["capability_path"](job, attempt_id)
        or capability_sha256 != sha256_file(capability_file)
        or capability_row["mode"] != mode
        or capability_row["argv"] != argv
        or capability_row["log"] != log
    ):
        raise RuntimeError("attempt capability context changed before manifest")
    payload = {
        "schema_version": "atlas_completion_summary_recovery_job_manifest_v2",
        "job": job, "attempt_id": attempt_id, "mode": mode, "argv": argv,
        "pid": os.getpid(), "host": socket.gethostname(), "started_utc": utc_now(),
        "initial_recovery_bundle_sha256": initial,
        "promotion_bundle_sha256": promotion_sha,
        "execution_owner_sha256": execution_owner_sha256,
        "filesystem_capability_path": capability_path,
        "filesystem_capability_sha256": capability_sha256,
        "staging_prefix": f"results/atlas/.completion_diagnostic_{job}.staging.",
        "destination": str((candidate_root() if job == "candidate" else canonical_root()).relative_to(ROOT)),
        "log": log,
    }
    write_once_json(path, payload)
    _validate_attempt_manifest(path, job=job, attempt_id=attempt_id)
    return path


def close_orphan_attempts(job: str) -> list[Path]:
    require_job_lock(job)
    root = recovery_run_root() / "job_manifests"
    capabilities = {
        _attempt_from_name(path, job, "capability"): path
        for path in sorted((recovery_run_root() / "filesystem_capabilities").glob(f"{job}.*.json"))
    }
    manifests = {_attempt_from_name(path, job, "manifest"): path
                 for path in sorted(root.glob(f"{job}.*.manifest.json"))}
    terminals = {_attempt_from_name(path, job, "terminal"): path
                 for path in sorted(root.glob(f"{job}.*.terminal.json"))}
    if set(manifests) - set(capabilities) or set(terminals) - set(capabilities):
        raise RuntimeError("attempt manifest/terminal exists without its capability")
    for path in capabilities.values():
        write_once_json(path, strict_json(path))
    for path in manifests.values():
        write_once_json(path, strict_json(path))
    for path in terminals.values():
        write_once_json(path, strict_json(path))
    created: list[Path] = []
    for attempt_id in sorted(set(capabilities) - set(terminals)):
        capability = _validate_capability(capabilities[attempt_id], job=job, attempt_id=attempt_id)
        manifest_present = attempt_id in manifests
        manifest = (
            _validate_attempt_manifest(manifests[attempt_id], job=job, attempt_id=attempt_id)
            if manifest_present else None
        )
        snapshot_path, snapshot = snapshot_attempt_state(job, attempt_id)
        if not manifest_present and snapshot["state_status"] != "state_absent_for_attempt":
            raise RuntimeError("capability-only attempt unexpectedly owns job state")
        log_path = ROOT / capability["log"]
        terminal_path = _terminal_path(job, attempt_id)
        terminal = {
            "schema_version": "atlas_completion_summary_recovery_job_attempt_terminal_v3",
            "job": job, "attempt_id": attempt_id,
            "manifest_state": "present" if manifest_present else "absent",
            "manifest_sha256": sha256_file(manifests[attempt_id]) if manifest_present else None,
            "filesystem_capability_path": str(capabilities[attempt_id].relative_to(ROOT)),
            "filesystem_capability_sha256": sha256_file(capabilities[attempt_id]),
            "state_snapshot_path": str(snapshot_path.relative_to(ROOT)),
            "state_snapshot_sha256": sha256_file(snapshot_path),
            "log_sha256": sha256_file(log_path) if log_path.is_file() else None,
            "exit_code": None, "outcome": "technical_failure",
            "closure_reason": (
                "supervisor_unobservable_exit" if manifest_present
                else "supervisor_unobservable_exit_before_manifest"),
            "last_durable_phase": (
                strict_json(ROOT / snapshot["state_path"])["phase"]
                if snapshot["state_status"] == "present" else "not_started"),
            "released_lock_observed": True, "recovery_host": socket.gethostname(),
            "diagnostic_continuation_only": True, "decision_promotion_allowed": False,
            "ended_utc": utc_now(),
        }
        write_once_json(terminal_path, terminal)
        _validate_attempt_terminal(terminal_path, job=job)
        created.append(terminal_path)
    if success_path(job).exists() or success_path(job).is_symlink():
        write_once_json(success_path(job), strict_json(success_path(job)))
        validate_success_closure(
            job, candidate_root() if job == "candidate" else canonical_root())
    else:
        successful = []
        for path in sorted(root.glob(f"{job}.*.terminal.json")):
            row = _validate_attempt_terminal(path, job=job)
            if row["outcome"] in {"success", "reconciled"}:
                successful.append((path, ROOT / row["state_snapshot_path"]))
        if len(successful) > 1:
            raise RuntimeError("multiple successful attempt terminals lack one closure")
        if successful:
            _write_success_closure(job, *successful[0])
    return created


def _attempt_from_name(path: Path, job: str, kind: str) -> str:
    prefix = f"{job}."
    suffix = ".json" if kind in {"capability", "snapshot"} else f".{kind}.json"
    if not path.name.startswith(prefix) or not path.name.endswith(suffix):
        raise RuntimeError(f"malformed attempt evidence filename: {path}")
    attempt = path.name[len(prefix):-len(suffix)]
    if not ATTEMPT_RE.fullmatch(attempt):
        raise RuntimeError(f"malformed attempt ID in evidence filename: {path}")
    return attempt


def close_attempt(job: str, attempt_id: str, exit_code: int) -> dict[str, Any]:
    require_job_lock(job)
    manifest_path = _manifest_path(job, attempt_id)
    manifest = _validate_attempt_manifest(manifest_path, job=job, attempt_id=attempt_id)
    capability = capability_path(job, attempt_id)
    _validate_capability(capability, job=job, attempt_id=attempt_id)
    terminal_path = _terminal_path(job, attempt_id)
    if terminal_path.is_file() or terminal_path.is_symlink():
        row = strict_json(terminal_path)
        write_once_json(terminal_path, row)
        verified = _validate_attempt_terminal(terminal_path, job=job)
        if verified["outcome"] in {"success", "reconciled"}:
            snapshot = ROOT / verified["state_snapshot_path"]
            if success_path(job).exists() or success_path(job).is_symlink():
                write_once_json(success_path(job), strict_json(success_path(job)))
                validate_success_closure(
                    job, candidate_root() if job == "candidate" else canonical_root())
            else:
                _write_success_closure(job, terminal_path, snapshot)
        return verified
    head = read_state_chain(job)
    phase = (head["phase"] if head is not None and head["active_attempt_id"] == attempt_id
             else "not_started")
    if exit_code == 0 and phase == "parent_fsync_complete":
        destination = candidate_root() if job == "candidate" else canonical_root()
        try:
            if job == "candidate":
                validate_candidate(destination, require_success=False)
            else:
                validate_canonical(destination, require_success=False)
            if head is None or root_digest(destination) != head["destination_root_sha256"]:
                raise RuntimeError("success-terminal destination digest mismatch")
            if head["published_files"] != [
                    item["path"] for item in head["publication_inventory"]]:
                raise RuntimeError("success-terminal state lacks the full publication prefix")
        except BaseException as exc:
            append_state(job, attempt_id, {
                "phase": "parent_fsync_complete", "parent_fsync_complete": True,
                "error_type": type(exc).__name__, "error_message": str(exc),
                "error_errno": exc.errno if isinstance(exc, OSError) else None,
            })
            head = read_state_chain(job)
            phase = "parent_fsync_complete"
            exit_code = 1
    snapshot_path, snapshot = snapshot_attempt_state(job, attempt_id)
    if exit_code == 0 and phase == "parent_fsync_complete":
        outcome = "reconciled" if manifest["mode"] == "reconcile" else "success"
        reason = "normal_exit"
    elif head is not None and head["active_attempt_id"] == attempt_id and head.get("error_errno") == errno.EEXIST:
        outcome, reason = "destination_collision", "destination_collision"
    else:
        outcome, reason = "technical_failure", "command_failure"
    log_path = ROOT / manifest["log"]
    terminal = {
        "schema_version": "atlas_completion_summary_recovery_job_attempt_terminal_v3",
        "job": job, "attempt_id": attempt_id, "manifest_state": "present",
        "manifest_sha256": sha256_file(manifest_path),
        "filesystem_capability_path": str(capability.relative_to(ROOT)),
        "filesystem_capability_sha256": sha256_file(capability),
        "state_snapshot_path": str(snapshot_path.relative_to(ROOT)),
        "state_snapshot_sha256": sha256_file(snapshot_path),
        "log_sha256": sha256_file(log_path) if log_path.is_file() else None,
        "exit_code": int(exit_code), "outcome": outcome, "closure_reason": reason,
        "last_durable_phase": phase, "released_lock_observed": False,
        "recovery_host": None,
        "diagnostic_continuation_only": True, "decision_promotion_allowed": False,
        "ended_utc": utc_now(),
    }
    write_once_json(terminal_path, terminal)
    verified = _validate_attempt_terminal(terminal_path, job=job)
    if outcome in {"success", "reconciled"}:
        _write_success_closure(job, terminal_path, snapshot_path)
    return verified
