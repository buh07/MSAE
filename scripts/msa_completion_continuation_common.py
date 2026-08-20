#!/usr/bin/env python3
"""Strict provenance and closure helpers for the atlas diagnostic continuation."""
from __future__ import annotations

import json
import math
import os
import pickle
import sys
import time
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

from msa_completion_common import (
    EVIDENCE_CLASS,
    ROOT,
    assert_final_locked,
    atomic_write_json,
    canonical_json_bytes,
    default_firewall as frozen_default_firewall,
    process_resource_accounting,
    read_json,
    runtime_environment,
    sha256_bytes,
    sha256_file,
    stage_publication_lock,
    terminal_state,
    utc_now,
    verify_completion_freeze as verify_base_completion_freeze,
    write_terminal,
)

BASE_DIGEST = "0aac744d4d10f56cafae645fdc71ea8348bec743a5c20561d4649aedac0503ee"
PARENT_DIGEST = "e7c12f4407249ccc556c8f56234c8de36af01d29a89de525deed7506876c8c31"
BASE_CONFIG = ROOT / "configs/atlas_completion/analysis.json"
CONFIG = ROOT / "configs/atlas_completion_continuation/analysis.json"
FREEZE = ROOT / "configs/atlas_completion_continuation/freeze_record.json"
SOURCE_RUN = ROOT / "pilot_runs/20260801_atlas_completion_v1"
RUN_ROOT = ROOT / "pilot_runs/20260802_atlas_completion_diagnostic_continuation_v1"
RESULT_ROOT = ROOT / "results/atlas/completion_diagnostic_v1"
INVENTORY = ROOT / "configs/atlas_completion_continuation/original_run_inventory.json"
BASELINE_SOURCE = SOURCE_RUN / "baseline"
RAW_STAGE = SOURCE_RUN / "raw_refit/L3"
BASE_STOP = RAW_STAGE / "FROZEN_EQUIVOCAL_STOP.json"
BASE_SELECTOR = RAW_STAGE / "TERMINAL_STATE.json"
BASE_NOT_LAUNCHED = SOURCE_RUN / "NOT_LAUNCHED_UPSTREAM_STOP.json"
RESULT_REVIEW = ROOT / "reports/adversarial/atlas_completion_result_review_20260801.md"
IMPLEMENTATION_REVIEW = ROOT / "reports/adversarial/atlas_completion_continuation_implementation_review_20260801.json"

BASE_CONFIG_SHA = "99d4f094da4eb38b6fa021967dee18e155698cdbd4cd155761a0c130b90e6e1d"
BASE_STOP_SHA = "612d94df5970236323110e6b6e050d900477738c4488e5d284aa21169becc31c"
BASE_SELECTOR_SHA = "c210d6d44ef8702a4cf391480ce1497a6648fe991103b5c60c1c3977f14af06e"
BASE_NOT_LAUNCHED_SHA = "85656dd825c90e76d0fb9614a791586105175daf9507026fc7865758a43a9dd4"
RESULT_REVIEW_SHA = "7dba52503d9f1ca86cc209d05267737be5cd984b2859c77534a35e978112f172"
BASELINE_HASHES = {
    "baseline.json": "405518bb44bd9525307125d8af7dae735d5d31a93ab1e0a3b23b23a8355cf8b5",
    "baseline_bundle.pkl": "9e967d08488907188d39ba8c8a134a05b9582be438fcfbf1bb91f7d191ac931e",
    "MEASUREMENT_COMPLETE.json": "dcf92e9c5c768660a12c99196a6cb7a7e5394d9687024ca6cf79d1990779d583",
    "TERMINAL_STATE.json": "0b35a119478c39cb954cae0ee8d149b75018e9277175b062439c5259f231bf61",
}
SCIENTIFIC_BASELINE_FIELDS = (
    "schema_version", "evidence_class", "parent_bundle_sha256", "seed_provenance",
    "baseline_selection_failed", "selected_simple_baseline", "selection_trace",
    "candidates", "sentinel_alphas", "sentinels", "tier1_eligibility",
)
JOBS = (
    "k2_wave2_fast_g4_L3_s42_inc1e2",
    "k2_wave2_fast_g5_L3_s43_inc1e2",
    "k2_wave2_fast_g6_L3_s44_inc1e2",
    "k2_wave2_fast_g7_L3_s42_inc0",
)
STABILITY_SHARDS = ((0, 167), (167, 334), (334, 500))
BASE_GPU_TERMINALS = (
    SOURCE_RUN / "pilot_v8/FROZEN_EQUIVOCAL_STOP.json",
    SOURCE_RUN / "pilot_v9/FROZEN_EQUIVOCAL_STOP.json",
    SOURCE_RUN / "pilot_v10/MEASUREMENT_COMPLETE.json",
    SOURCE_RUN / "baseline/MEASUREMENT_COMPLETE.json",
    SOURCE_RUN / "raw_refit/L3/FROZEN_EQUIVOCAL_STOP.json",
    SOURCE_RUN / "raw_refit/L4/MEASUREMENT_COMPLETE.json",
)
CONTINUATION_FREEZE_KEYS = {
    "schema_version", "created_utc", "evidence_class",
    "diagnostic_continuation_only", "decision_promotion_allowed",
    "parent_bundle_sha256", "base_completion_bundle_sha256",
    "base_freeze_record_sha256", "config_sha256",
    "source_inventory_manifest_sha256", "source_inventory_sha256",
    "reviewed_candidate_sha256", "reviewed_candidate_files",
    "implementation_review_sha256", "bundle_files", "bundle_sha256",
    "prescore_clean",
}


def validate_freeze_semantics(record: Mapping[str, Any]) -> None:
    if set(record) != CONTINUATION_FREEZE_KEYS:
        raise RuntimeError("continuation freeze semantic field inventory mismatch")
    if (record.get("schema_version") != "atlas_completion_diagnostic_continuation_freeze_v1"
            or record.get("evidence_class") != EVIDENCE_CLASS
            or record.get("diagnostic_continuation_only") is not True
            or record.get("decision_promotion_allowed") is not False
            or record.get("prescore_clean") is not True):
        raise RuntimeError("continuation freeze denial/prescore semantics mismatch")


def validate_reviewed_freeze_scope(record: Mapping[str, Any],
                                   candidate: Mapping[str, Any],
                                   freeze_bundle: Mapping[str, Any]) -> None:
    if (record.get("reviewed_candidate_files") != candidate.get("bundle_files")
            or record.get("reviewed_candidate_sha256") != candidate.get("bundle_sha256")):
        raise RuntimeError("reviewed continuation candidate scope/digest mismatch")
    if (record.get("bundle_files") != freeze_bundle.get("bundle_files")
            or record.get("bundle_sha256") != freeze_bundle.get("bundle_sha256")):
        raise RuntimeError("continuation freeze file scope differs from implementation")


def canonical_job_specs() -> dict[str, dict[str, Any]]:
    specs: dict[str, dict[str, Any]] = {}
    for job in JOBS:
        short = job.split("_")[3]
        stage = f"k2_refit/{job}"
        specs[f"{short}_point"] = {"stage": stage, "kind": "k2_point", "job": job,
                                    "expected": "point.json"}
        specs[f"{short}_draws"] = {"stage": stage, "kind": "k2_draws", "job": job,
                                    "expected": "shard_0000_0500.json"}
    specs["stability_point"] = {"stage": "stability", "kind": "stability_point",
                                  "expected": "point.json"}
    for start, end in STABILITY_SHARDS:
        specs[f"stability_{start}_{end}"] = {
            "stage": "stability", "kind": "stability_draws", "start": start,
            "end": end, "expected": f"shard_{start:04d}_{end:04d}.json"}
    for job in JOBS:
        short = job.split("_")[3]
        specs[f"specificity_{short}"] = {
            "stage": f"specificity/{job}", "kind": "specificity", "job": job,
            "expected": "specificity.json"}
    if len(specs) != 16:
        raise AssertionError("canonical continuation job inventory must have 16 entries")
    return specs


def canonical_stage_members() -> dict[str, list[str]]:
    out: dict[str, list[str]] = {}
    for job_id, spec in canonical_job_specs().items():
        out.setdefault(str(spec["stage"]), []).append(job_id)
    return {stage: sorted(members) for stage, members in sorted(out.items())}


def canonical_gpu_command(job_id: str) -> list[str]:
    spec = canonical_job_specs()[job_id]
    py = ".venv-atlas/bin/python"
    entry = "scripts/run_msae_completion_continuation.py"
    kind = spec["kind"]
    if kind == "k2_point":
        return [py, entry, "k2", "--job", spec["job"], "--point", "--device", "cuda:0"]
    if kind == "k2_draws":
        return [py, entry, "k2", "--job", spec["job"], "--draw-start", "0",
                "--draw-end", "500", "--device", "cuda:0"]
    if kind == "stability_point":
        return [py, entry, "stability", "--point", "--device", "cuda:0"]
    if kind == "stability_draws":
        return [py, entry, "stability", "--draw-start", str(spec["start"]),
                "--draw-end", str(spec["end"]), "--device", "cuda:0"]
    if kind == "specificity":
        return [py, entry, "specificity", "--job", spec["job"], "--device", "cuda:0"]
    raise RuntimeError(f"unknown canonical GPU job kind: {kind}")


def resource_job_cap_hours(spec: Mapping[str, Any],
                           config: Mapping[str, Any] | None = None) -> float:
    config = read_json(CONFIG) if config is None else config
    caps = config["diagnostic_continuation"]["resource_job_caps_gpu_hours"]
    kind = str(spec["kind"])
    return float(caps["k2"] if kind.startswith("k2_") else
                 caps["stability"] if kind.startswith("stability_")
                 else caps["specificity"])


def runtime_limit_policy(*, reserved_seconds: float, stage_remaining_seconds: float,
                         config: Mapping[str, Any] | None = None) -> dict[str, int]:
    config = read_json(CONFIG) if config is None else config
    metadata = config["diagnostic_continuation"]
    grace = int(metadata["termination_grace_seconds"])
    margin = int(metadata["timeout_accounting_margin_seconds"])
    hard = max(0, int(min(float(reserved_seconds), float(stage_remaining_seconds))))
    return {"soft_timeout_seconds": max(0, hard - grace - margin),
            "termination_grace_seconds": grace,
            "timeout_accounting_margin_seconds": margin,
            "hard_runtime_ceiling_seconds": hard}


def classify_supervised_exit(*, exit_code: int, process_elapsed_seconds: float,
                             soft_timeout_seconds: float, expected_output_exists: bool,
                             stage_terminal_exists: bool,
                             matching_launch_failure_exists: bool) -> str:
    """Classify the process boundary, including failures that bypass Python cleanup."""
    if exit_code in {124, 137} and process_elapsed_seconds + 2.0 >= soft_timeout_seconds:
        return "resource_timeout"
    if exit_code == 0 and expected_output_exists:
        return "job_process_success"
    if stage_terminal_exists or matching_launch_failure_exists:
        return "technical_failure"
    return "process_crash"


def supervisor_record_payload(*, kind: str, job_id: str, exit_code: int,
                              gpu_index: int, gpu_uuid: str, stage: Path,
                              expected_output: str, process_started_utc: str,
                              process_ended_utc: str, process_elapsed_seconds: float,
                              launch_manifest: Path, log: Path, stage_deadline: Path,
                              stage_deadline_sha256: str, budget_reservation: Path,
                              budget_reservation_sha256: str, config_sha256: str,
                              completion_bundle_sha256: str) -> dict[str, Any]:
    """Build the exact hash-bound runner-owned timeout/crash closure."""
    identities = {
        "resource_timeout": (
            "atlas_completion_continuation_resource_timeout_v1",
            "hard_runtime_supervisor_expired"),
        "process_crash": (
            "atlas_completion_continuation_process_crash_v1",
            "uncatchable_process_exit"),
    }
    if kind not in identities:
        raise ValueError(f"unsupported supervisor closure kind: {kind}")
    schema, reason = identities[kind]
    return {
        "schema_version": schema, "job": job_id, "reason": reason,
        "exit_code": int(exit_code), "scoring_started": True,
        "gpu_index": int(gpu_index), "gpu_uuid": gpu_uuid,
        "stage": str(stage), "expected_output": expected_output,
        "process_started_utc": process_started_utc,
        "process_ended_utc": process_ended_utc,
        "process_elapsed_seconds": float(process_elapsed_seconds),
        "launch_manifest_path": str(launch_manifest),
        "launch_manifest_sha256": sha256_file(launch_manifest),
        "log_path": str(log), "log_sha256": sha256_file(log),
        "stage_deadline_path": str(stage_deadline),
        "stage_deadline_sha256": stage_deadline_sha256,
        "budget_reservation_path": str(budget_reservation),
        "budget_reservation_sha256": budget_reservation_sha256,
        "config_sha256": config_sha256,
        "completion_bundle_sha256": completion_bundle_sha256,
        "diagnostic_continuation_only": True,
        "decision_promotion_allowed": False, "recorded_utc": utc_now(),
    }


def reserve_gpu_resources(*, run_root: Path, job_id: str, stage: Path,
                          spec: Mapping[str, Any], config: Mapping[str, Any] | None = None,
                          now_epoch: float | None = None,
                          base_actual_gpu_hours: float | None = None) -> dict[str, Any]:
    """Atomically bind the shared stage deadline and total-budget reservation."""
    import fcntl

    config = read_json(CONFIG) if config is None else config
    now = time.time() if now_epoch is None else float(now_epoch)
    deadlines, reservations = run_root / "stage_deadlines", run_root / "budget_reservations"
    deadlines.mkdir(parents=True, exist_ok=True)
    reservations.mkdir(parents=True, exist_ok=True)
    lock = reservations / ".budget.lock"
    lock.touch(exist_ok=True)
    stage_id = sha256_bytes(str(stage).encode())[:24]
    deadline = deadlines / f"{stage_id}.json"
    reservation = reservations / f"{job_id}.json"
    with lock.open("r+b") as handle:
        fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
        if not deadline.exists():
            atomic_write_json(deadline, {
                "schema_version": "atlas_completion_continuation_stage_deadline_v1",
                "stage": str(stage), "started_epoch": now, "deadline_epoch": now + 86400,
                "maximum_stage_wall_seconds": 86400, "decision_promotion_allowed": False,
            })
        deadline_row = read_json(deadline)
        if (deadline_row.get("schema_version")
                != "atlas_completion_continuation_stage_deadline_v1"
                or deadline_row.get("stage") != str(stage)
                or deadline_row.get("maximum_stage_wall_seconds") != 86400
                or float(deadline_row.get("deadline_epoch", 0))
                   - float(deadline_row.get("started_epoch", 0)) != 86400
                or deadline_row.get("decision_promotion_allowed") is not False):
            raise RuntimeError("stage deadline binding mismatch")
        if reservation.exists():
            raise RuntimeError("duplicate GPU budget reservation")
        existing_rows = [read_json(path) for path in reservations.glob("*.json")]
        if any(row.get("schema_version") != "atlas_completion_continuation_gpu_reservation_v1"
               for row in existing_rows):
            raise RuntimeError("existing GPU reservation schema mismatch")
        existing = sum(float(row["reserved_gpu_hours"]) for row in existing_rows)
        hours = resource_job_cap_hours(spec, config)
        base = (float(base_gpu_ledger()["total_gpu_hours"])
                if base_actual_gpu_hours is None else float(base_actual_gpu_hours))
        maximum = float(config["budgets"]["maximum_total_gpu_hours"])
        if base + existing + hours > maximum:
            raise RuntimeError("total GPU-hour reservation exceeds frozen budget")
        atomic_write_json(reservation, {
            "schema_version": "atlas_completion_continuation_gpu_reservation_v1",
            "job": job_id, "stage": str(stage), "reserved_gpu_hours": hours,
            "base_actual_gpu_hours": base, "prior_reserved_gpu_hours": existing,
            "maximum_total_gpu_hours": maximum, "decision_promotion_allowed": False,
        })
    limits = runtime_limit_policy(
        reserved_seconds=hours * 3600,
        stage_remaining_seconds=float(deadline_row["deadline_epoch"]) - time.time(),
        config=config)
    return {
        "deadline": str(deadline), "deadline_epoch": deadline_row["deadline_epoch"],
        "reservation": str(reservation), "reserved_seconds": hours * 3600,
        "deadline_sha256": sha256_file(deadline),
        "reservation_sha256": sha256_file(reservation), **limits,
    }


def gpu_terminal_ledger(paths: Sequence[Path], *, scope: str) -> dict[str, Any]:
    """Extract a strict, schema-aware GPU-hour ledger from bound terminals."""
    rows: list[dict[str, Any]] = []
    for path in paths:
        payload = read_json(path)
        accounting = payload.get("resource_accounting")
        if not isinstance(accounting, Mapping):
            raise RuntimeError(f"base terminal lacks resource accounting: {path}")
        schema = payload.get("schema_version")
        fields = [field for field in ("recorded_gpu_hours", "recorded_worker_gpu_hours")
                  if field in accounting]
        allowed = {
            "recorded_gpu_hours": {
                "atlas_completion_pilot_complete_v1",
                "atlas_completion_baseline_complete_v1",
                "atlas_completion_frozen_stop_v1",
            },
            "recorded_worker_gpu_hours": {
                "atlas_completion_frozen_stop_v1",
                "atlas_completion_refit_terminal_v1",
            },
        }
        if len(fields) != 1 or schema not in allowed[fields[0]]:
            raise RuntimeError(f"unregistered base GPU terminal schema: {schema}")
        field = fields[0]
        hours = float(accounting[field])
        if not math.isfinite(hours) or hours < 0:
            raise RuntimeError(f"invalid base GPU hours: {path}")
        rows.append({
            "path": str(path), "sha256": sha256_file(path), "schema_version": schema,
            "accounting_field": field, "gpu_hours": hours,
        })
    return {"scope": scope,
            "terminals": rows, "total_gpu_hours": sum(row["gpu_hours"] for row in rows)}


def base_gpu_ledger() -> dict[str, Any]:
    """Strict known-actual GPU ledger for score-bearing base-run terminals."""
    return gpu_terminal_ledger(
        BASE_GPU_TERMINALS, scope="all_base_run_terminals_with_recorded_gpu_hours")


def recursive_inventory(root: Path) -> list[dict[str, Any]]:
    root = root.resolve(strict=True)
    entries: list[dict[str, Any]] = []
    for path in sorted(root.rglob("*"), key=lambda p: str(p.relative_to(root))):
        relative = str(path.relative_to(root))
        if path.is_symlink():
            raise RuntimeError(f"source-run inventory refuses symlink: {relative}")
        if path.is_dir():
            entries.append({"path": relative, "type": "directory", "size": None,
                            "sha256": None})
        elif path.is_file():
            entries.append({"path": relative, "type": "file",
                            "size": path.stat().st_size, "sha256": sha256_file(path)})
        else:
            raise RuntimeError(f"source-run inventory refuses file type: {relative}")
    return entries


def inventory_digest(entries: Sequence[Mapping[str, Any]]) -> str:
    return sha256_bytes(canonical_json_bytes(list(entries)))


def verify_source_inventory() -> dict[str, Any]:
    manifest = read_json(INVENTORY)
    if manifest.get("schema_version") != "atlas_completion_source_run_inventory_v1":
        raise RuntimeError("invalid source-run inventory schema")
    if manifest.get("root") != str(SOURCE_RUN.relative_to(ROOT)):
        raise RuntimeError("source-run inventory root mismatch")
    current = recursive_inventory(SOURCE_RUN)
    if current != manifest.get("entries"):
        expected = {r["path"]: r for r in manifest.get("entries", [])}
        observed = {r["path"]: r for r in current}
        changed = sorted(set(expected) ^ set(observed) |
                         {p for p in set(expected) & set(observed) if expected[p] != observed[p]})
        raise RuntimeError(f"immutable source run differs: {changed[:10]}")
    digest = inventory_digest(current)
    if manifest.get("inventory_sha256") != digest:
        raise RuntimeError("source-run inventory digest mismatch")
    return manifest


def compute_bundle(paths: Iterable[Path]) -> dict[str, Any]:
    rows = []
    for path in sorted({p.resolve(strict=True) for p in paths}, key=lambda p: str(p.relative_to(ROOT))):
        relative = str(path.relative_to(ROOT))
        rows.append({"path": relative, "sha256": sha256_file(path)})
    return {"bundle_files": rows, "bundle_sha256": sha256_bytes(canonical_json_bytes(rows))}


def verify_continuation_freeze(path: Path = FREEZE, *,
                               check_source_inventory: bool = True) -> dict[str, Any]:
    assert_final_locked()
    record_path = path.resolve(strict=True)
    record_bytes = record_path.read_bytes()
    record = json.loads(record_bytes)
    validate_freeze_semantics(record)
    entries = record.get("bundle_files")
    if not isinstance(entries, list) or not entries:
        raise RuntimeError("continuation freeze has no bundle files")
    paths: list[Path] = []
    normalized: list[dict[str, str]] = []
    seen: set[str] = set()
    for row in entries:
        if not isinstance(row, dict) or set(row) != {"path", "sha256"}:
            raise RuntimeError("malformed continuation freeze entry")
        relative = str(row["path"])
        if relative in seen or Path(relative).is_absolute() or ".." in Path(relative).parts:
            raise RuntimeError(f"unsafe continuation freeze path: {relative}")
        seen.add(relative)
        candidate = (ROOT / relative).resolve(strict=True)
        candidate.relative_to(ROOT.resolve())
        actual = sha256_file(candidate)
        if actual != row["sha256"]:
            raise RuntimeError(f"continuation freeze hash mismatch: {relative}")
        paths.append(candidate)
        normalized.append({"path": relative, "sha256": actual})
    if normalized != sorted(normalized, key=lambda r: r["path"]):
        raise RuntimeError("continuation freeze entries are not sorted")
    computed = compute_bundle(paths)
    if computed["bundle_sha256"] != record.get("bundle_sha256"):
        raise RuntimeError("continuation freeze bundle digest mismatch")
    base = verify_base_completion_freeze()
    if base.get("bundle_sha256") != BASE_DIGEST or record.get("base_completion_bundle_sha256") != BASE_DIGEST:
        raise RuntimeError("base completion bundle mismatch")
    if record.get("parent_bundle_sha256") != PARENT_DIGEST:
        raise RuntimeError("parent bundle mismatch")
    if record.get("base_freeze_record_sha256") != sha256_file(
            ROOT / "configs/atlas_completion/freeze_record.json"):
        raise RuntimeError("base freeze record binding mismatch")
    if sha256_file(CONFIG) != record.get("config_sha256"):
        raise RuntimeError("continuation config binding mismatch")
    verify_fixed_source_hashes()
    inventory = verify_source_inventory() if check_source_inventory else read_json(INVENTORY)
    if sha256_file(INVENTORY) != record.get("source_inventory_manifest_sha256"):
        raise RuntimeError("source inventory manifest binding mismatch")
    if inventory.get("inventory_sha256") != record.get("source_inventory_sha256"):
        raise RuntimeError("source inventory digest binding mismatch")
    review = read_json(IMPLEMENTATION_REVIEW)
    if (review.get("verdict") != "SHIP"
            or review.get("candidate_sha256") != record.get("reviewed_candidate_sha256")):
        raise RuntimeError("implementation review is not SHIP for frozen candidate")
    # The trust-root may not supply an alternative file list while retaining a
    # previously reviewed digest.  Reconstruct both scopes from the reviewed
    # implementation itself.
    from freeze_msae_completion_continuation import (
        IMPLEMENTATION_TRANSCRIPT, candidate_paths, reviewed_candidate)
    candidate = reviewed_candidate()
    expected_freeze_bundle = compute_bundle([
        *candidate_paths(), IMPLEMENTATION_REVIEW, IMPLEMENTATION_TRANSCRIPT])
    validate_reviewed_freeze_scope(record, candidate, expected_freeze_bundle)
    return {**record, "_freeze_record_sha256": sha256_bytes(record_bytes),
            "_freeze_record_path": str(record_path)}


def require_continuation_config(path: Path) -> dict[str, Any]:
    if path.resolve(strict=True) != CONFIG.resolve(strict=True):
        raise RuntimeError(f"score-bearing config is not the continuation config: {path}")
    return verify_continuation_freeze()


def verify_fixed_source_hashes() -> None:
    expected = {
        BASE_CONFIG: BASE_CONFIG_SHA,
        BASE_STOP: BASE_STOP_SHA,
        BASE_SELECTOR: BASE_SELECTOR_SHA,
        BASE_NOT_LAUNCHED: BASE_NOT_LAUNCHED_SHA,
        RESULT_REVIEW: RESULT_REVIEW_SHA,
        **{BASELINE_SOURCE / name: digest for name, digest in BASELINE_HASHES.items()},
    }
    mismatches = {}
    for path, digest in expected.items():
        actual = sha256_file(path) if path.is_file() else None
        if actual != digest:
            mismatches[str(path)] = (digest, actual)
    if mismatches:
        raise RuntimeError(f"fixed source hash mismatch: {mismatches}")


def continuation_firewall(source_run_root: Path, additive_run_root: Path | None = None) -> Any:
    firewall = frozen_default_firewall(source_run_root, additive_run_root)
    firewall.register_file(CONFIG)
    return firewall


def verify_raw_trust_root_hashes() -> None:
    expected = {BASE_CONFIG: BASE_CONFIG_SHA, BASE_STOP: BASE_STOP_SHA,
                BASE_SELECTOR: BASE_SELECTOR_SHA}
    mismatches = {str(path): (digest, sha256_file(path) if path.is_file() else None)
                  for path, digest in expected.items()
                  if not path.is_file() or sha256_file(path) != digest}
    if mismatches:
        raise RuntimeError(f"fixed raw trust-root hash mismatch: {mismatches}")


def load_old_raw(draw_id: int | str, *, verify_inventory: bool = False) -> dict[str, Any]:
    if verify_inventory:
        verify_source_inventory()
    verify_raw_trust_root_hashes()
    stop = read_json(BASE_STOP)
    return validate_old_raw_from_stage(
        RAW_STAGE, stop, draw_id, config_sha256=BASE_CONFIG_SHA,
        completion_bundle_sha256=BASE_DIGEST)


def validate_old_raw_from_stage(stage: Path, stop: Mapping[str, Any],
                                draw_id: int | str, *, config_sha256: str,
                                completion_bundle_sha256: str) -> dict[str, Any]:
    """Pure path/registration validator, including the 500-ID stop contract."""
    if (stop.get("config_sha256") != config_sha256
            or stop.get("completion_bundle_sha256") != completion_bundle_sha256
            or stop.get("registered_complete_draw_ids") != list(range(500))):
        raise RuntimeError("base L3 stop binding/inventory mismatch")
    if draw_id == "point":
        relative = "point.json"
    else:
        if isinstance(draw_id, bool) or not isinstance(draw_id, int) or not 0 <= draw_id < 500:
            raise ValueError(f"invalid raw draw ID: {draw_id!r}")
        relative = f"draws/{draw_id:04d}.json"
    if stop.get("config_sha256") != config_sha256:
        raise RuntimeError("base L3 stop config mismatch")
    path = stage / relative
    retained = stop.get("retained_partial_sha256", {})
    if retained.get(relative) != sha256_file(path):
        raise RuntimeError(f"base raw retained-leaf mismatch: {relative}")
    payload = read_json(path)
    expected_inner = "point" if draw_id == "point" else draw_id
    if (payload.get("draw_id") != expected_inner
            or payload.get("kind") != "raw" or payload.get("layer") != 3
            or payload.get("config_sha256") != config_sha256
            or payload.get("completion_bundle_sha256") != completion_bundle_sha256):
        raise RuntimeError(f"base raw leaf metadata mismatch: {relative}")
    if draw_id != "point":
        registration_relative = f"completed_hashes/{draw_id:04d}.json"
        registration_path = stage / registration_relative
        if retained.get(registration_relative) != sha256_file(registration_path):
            raise RuntimeError(f"base raw retained-registration mismatch: {draw_id}")
        registration = read_json(registration_path)
        if (registration.get("draw_id") != draw_id
                or registration.get("status") != "complete"
                or registration.get("artifact") != relative
                or registration.get("artifact_sha256") != sha256_file(path)
                or registration.get("config_sha256") != config_sha256
                or registration.get("completion_bundle_sha256") != completion_bundle_sha256):
            raise RuntimeError(f"base raw registration mismatch: {draw_id}")
    return payload


def prevalidate_old_raw(draw_ids: Sequence[int | str]) -> None:
    verify_source_inventory()
    verify_fixed_source_hashes()
    stop = read_json(BASE_STOP)
    for draw_id in draw_ids:
        validate_old_raw_from_stage(
            RAW_STAGE, stop, draw_id, config_sha256=BASE_CONFIG_SHA,
            completion_bundle_sha256=BASE_DIGEST)


def attest_old_raw_inputs(firewall: Any, draw_id: int | str) -> None:
    """Add only the consumed old-raw trust chain to the target attestation."""
    paths = [BASE_STOP, BASE_SELECTOR]
    if draw_id == "point":
        paths.append(RAW_STAGE / "point.json")
    else:
        paths.extend([RAW_STAGE / "draws" / f"{int(draw_id):04d}.json",
                      RAW_STAGE / "completed_hashes" / f"{int(draw_id):04d}.json"])
    for path in paths:
        firewall.register_file(path)
        firewall.attest(path)


def assert_stage_path(stage: Path) -> Path:
    resolved = stage.resolve()
    resolved.relative_to(RUN_ROOT.resolve())
    allowed = {RUN_ROOT / stage_name for stage_name in canonical_stage_members()}
    allowed.add(RUN_ROOT / "baseline")
    if resolved not in {p.resolve() for p in allowed}:
        raise RuntimeError(f"continuation stage is not allowlisted: {stage}")
    return resolved


def completed_registration_ids(stage: Path) -> list[int]:
    completed: list[int] = []
    for path in sorted((stage / "completed_hashes").glob("*.json")):
        try:
            row = read_json(path)
            artifact = stage / str(row["artifact"])
            if (row.get("status") == "complete" and artifact.is_file()
                    and row.get("artifact_sha256") == sha256_file(artifact)):
                completed.append(int(row["draw_id"]))
        except Exception:
            continue
    return sorted(set(completed))


def retained_partial(stage: Path) -> dict[str, str]:
    result: dict[str, str] = {}
    for path in sorted(stage.rglob("*")):
        if not path.is_file():
            continue
        relative = path.relative_to(stage)
        if ("claims" in relative.parts or ".tmp." in path.name
                or path.name in {".publication.lock", "TERMINAL_STATE.json",
                                 "MEASUREMENT_COMPLETE.json", "FROZEN_EQUIVOCAL_STOP.json"}):
            continue
        result[str(relative)] = sha256_file(path)
    return result


def publish_technical_stop(stage: Path, *, stop_code: str, failed_gate: str,
                           error: BaseException, job_id: str,
                           requested_draw_ids: Sequence[int] = (), device: str | None = None,
                           input_attestation: Mapping[str, Any] | None = None,
                           elapsed_sec: float = 0.0,
                           verified_bundle_sha256: str | None = None) -> Path:
    stage = assert_stage_path(stage)
    try:
        config = read_json(CONFIG)
        config_error = None
    except Exception as exc:
        config = None
        config_error = f"{type(exc).__name__}:{exc}"
    freeze_error = None
    try:
        freeze = verify_continuation_freeze(check_source_inventory=False)
    except Exception as exc:
        # A provenance failure may be the reason this stop is required.  The
        # immutable freeze-record bytes remain the trust-root reference; never
        # turn a corrupt scientific input into an unreported/hanging process.
        try:
            freeze = read_json(FREEZE)
        except Exception:
            freeze = {"bundle_sha256": verified_bundle_sha256}
        freeze_error = f"{type(exc).__name__}:{exc}"
    bundle_sha = verified_bundle_sha256 or freeze.get("bundle_sha256")
    try:
        config_sha = sha256_file(CONFIG)
    except BaseException:
        config_sha = None
    try:
        environment = runtime_environment(device)
    except BaseException as exc:
        environment = {"capture_error_type": type(exc).__name__,
                       "capture_error": str(exc), "device_requested": device}
    try:
        accounting = process_resource_accounting(
            stage, elapsed_sec=max(0.0, float(elapsed_sec)), device=device)
    except BaseException as exc:
        accounting = {"capture_error_type": type(exc).__name__,
                      "capture_error": str(exc),
                      "elapsed_sec": max(0.0, float(elapsed_sec))}
    with stage_publication_lock(stage):
        state = terminal_state(stage)
        if state is not None:
            return stage / ("MEASUREMENT_COMPLETE.json" if state == "complete"
                            else "FROZEN_EQUIVOCAL_STOP.json")
        completed = completed_registration_ids(stage)
        payload = {
            "schema_version": "atlas_completion_diagnostic_continuation_technical_stop_v1",
            "stop_code": stop_code,
            "failed_gate": failed_gate,
            "error_type": type(error).__name__,
            "error": str(error),
            "job_id": job_id,
            "requested_draw_ids": list(requested_draw_ids),
            "completed_draw_ids": completed,
            "retained_partial_sha256": retained_partial(stage),
            "config_sha256": config_sha,
            "completion_bundle_sha256": bundle_sha,
            "resolved_config": config,
            "resolved_arguments": {"job_id": job_id, "argv": list(sys.argv[1:])},
            "device": device,
            "resource_accounting": accounting,
            "environment": environment,
            "input_attestation": dict(input_attestation or {}),
            "freeze_verification_error_at_failure": freeze_error,
            "config_verification_error_at_failure": config_error,
            "diagnostic_continuation_only": True,
            "scientific_retry_allowed": False,
            "decision_promotion_allowed": False,
        }
        return write_terminal(stage, complete=False, payload=payload)


def publish_launch_failure(*, job_id: str, error: BaseException,
                           device: str | None = None) -> Path:
    RUN_ROOT.mkdir(parents=True, exist_ok=True)
    try:
        config_sha = sha256_file(CONFIG)
    except BaseException:
        config_sha = None
    try:
        bundle_sha = read_json(FREEZE).get("bundle_sha256") if FREEZE.is_file() else None
    except BaseException:
        bundle_sha = None
    payload = {
        "schema_version": "atlas_completion_diagnostic_continuation_launch_failure_v1",
        "evidence_class": EVIDENCE_CLASS,
        "job_id": job_id,
        "error_type": type(error).__name__,
        "error": str(error),
        "config_sha256": config_sha,
        "completion_bundle_sha256": bundle_sha,
        "device": device,
        "recorded_utc": utc_now(),
        "diagnostic_continuation_only": True,
        "decision_promotion_allowed": False,
    }
    path = RUN_ROOT / "LAUNCH_FAILURE.json"
    if path.exists():
        prior = read_json(path)
        if prior.get("job_id") != job_id:
            raise RuntimeError("root launch failure already belongs to another job")
        return path
    atomic_write_json(path, payload)
    return path


def verify_rebound_baseline() -> dict[str, Any]:
    verify_fixed_source_hashes()
    freeze = verify_continuation_freeze()
    stage = RUN_ROOT / "baseline"
    if terminal_state(stage) != "complete":
        raise RuntimeError("rebound baseline is not measurement-complete")
    marker = read_json(stage / "MEASUREMENT_COMPLETE.json")
    result_path, bundle_path = stage / "baseline.json", stage / "baseline_bundle.pkl"
    if (marker.get("config_sha256") != sha256_file(CONFIG)
            or marker.get("completion_bundle_sha256") != freeze["bundle_sha256"]
            or marker.get("result_sha256") != sha256_file(result_path)
            or marker.get("bundle_sha256") != sha256_file(bundle_path)):
        raise RuntimeError("rebound baseline terminal mismatch")
    source_result, rebound = read_json(BASELINE_SOURCE / "baseline.json"), read_json(result_path)
    if (rebound.get("config_sha256") != sha256_file(CONFIG)
            or rebound.get("completion_bundle_sha256") != freeze["bundle_sha256"]
            or rebound.get("resolved_config") != read_json(CONFIG)
            or rebound.get("provenance_rebind", {}).get("decision_promotion_allowed") is not False):
        raise RuntimeError("rebound baseline provenance binding mismatch")
    with (BASELINE_SOURCE / "baseline_bundle.pkl").open("rb") as handle:
        source_bundle = pickle.load(handle)
    with bundle_path.open("rb") as handle:
        rebound_bundle = pickle.load(handle)
    verify_baseline_science_payloads(
        source_result, rebound, source_bundle, rebound_bundle,
        continuation_bundle_sha256=freeze["bundle_sha256"])
    return {"science_equal": True, "result": rebound, "terminal": marker,
            "result_sha256": sha256_file(result_path), "bundle_sha256": sha256_file(bundle_path)}


def verify_baseline_science_payloads(
        source_result: Mapping[str, Any], rebound: Mapping[str, Any],
        source_bundle: Mapping[str, Any], rebound_bundle: Mapping[str, Any], *,
        continuation_bundle_sha256: str) -> None:
    """Pure equality gate used by the binder, runtime verifier, and tests."""
    for field in SCIENTIFIC_BASELINE_FIELDS:
        if rebound.get(field) != source_result.get(field):
            raise RuntimeError(f"rebound baseline science mismatch: {field}")
    if set(rebound) - set(source_result) != {"provenance_rebind"}:
        raise RuntimeError("unexpected rebound baseline fields")
    allowed = {"config_sha256", "completion_bundle_sha256", "resolved_config",
               "resolved_arguments", "device", "environment", "input_attestation",
               "elapsed_sec", "started_utc", "ended_utc"}
    for field in set(source_result) - set(SCIENTIFIC_BASELINE_FIELDS):
        if field not in allowed:
            raise RuntimeError(f"unclassified baseline field: {field}")
    expected_bundle = dict(source_bundle)
    expected_bundle["completion_bundle_sha256"] = continuation_bundle_sha256
    if rebound_bundle != expected_bundle:
        raise RuntimeError("rebound baseline bundle differs beyond freeze digest")


def strict_json(path: Path) -> Any:
    def reject(value: str) -> None:
        raise ValueError(f"nonfinite JSON constant {value} in {path}")
    return json.loads(path.read_text(encoding="utf-8"), parse_constant=reject)


def require_recursive_finite(value: Any, location: str = "$") -> None:
    if isinstance(value, float) and not math.isfinite(value):
        raise RuntimeError(f"nonfinite number at {location}")
    if isinstance(value, dict):
        for key, item in value.items():
            require_recursive_finite(item, f"{location}.{key}")
    elif isinstance(value, list):
        for index, item in enumerate(value):
            require_recursive_finite(item, f"{location}[{index}]")
