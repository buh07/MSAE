#!/usr/bin/env python3
"""Durable, strict, stop-aware collector for continuation jobs and stages."""
from __future__ import annotations

import argparse
import hashlib
import shlex
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Mapping

from msa_completion_common import atomic_write_json, read_json, sha256_file, terminal_state, utc_now
from msa_completion_continuation_common import (
    CONFIG,
    RUN_ROOT,
    base_gpu_ledger,
    canonical_gpu_command,
    canonical_job_specs,
    canonical_stage_members,
    resource_job_cap_hours,
    strict_json,
    verify_continuation_freeze,
    verify_rebound_baseline,
    verify_source_inventory,
)

COLLECTION = RUN_ROOT / "COLLECTION_COMPLETE.json"
NOT_LAUNCHED = RUN_ROOT / "NOT_LAUNCHED_UPSTREAM_STOP.json"
VALID_OUTCOMES = {
    "job_process_success",
    "technical_failure",
    "resource_not_launched",
    "resource_timeout",
    "process_crash",
    "superseded_by_stage_stop",
}
TERMINAL_KEYS = {
    "schema_version", "job", "exit_code", "outcome", "scoring_started",
    "gpu_index", "gpu_uuid", "stage", "expected_output", "config_sha256",
    "process_started_utc", "process_ended_utc", "process_elapsed_seconds",
    "completion_bundle_sha256", "diagnostic_continuation_only",
    "decision_promotion_allowed", "ended_utc",
}
MANIFEST_KEYS = {
    "schema_version", "job", "pid", "gpu_index", "gpu_uuid", "config_sha256",
    "completion_bundle_sha256", "started_utc", "log", "command",
    "stage_deadline_path", "stage_deadline_sha256", "budget_reservation_path",
    "budget_reservation_sha256", "soft_timeout_seconds",
    "termination_grace_seconds", "timeout_accounting_margin_seconds",
    "hard_runtime_ceiling_seconds",
}
DEADLINE_KEYS = {
    "schema_version", "stage", "started_epoch", "deadline_epoch",
    "maximum_stage_wall_seconds", "decision_promotion_allowed",
}
RESERVATION_KEYS = {
    "schema_version", "job", "stage", "reserved_gpu_hours",
    "base_actual_gpu_hours", "prior_reserved_gpu_hours", "maximum_total_gpu_hours",
    "decision_promotion_allowed",
}
RESOURCE_REQUIRED = {
    "schema_version", "job", "reason", "scoring_started", "config_sha256",
    "completion_bundle_sha256", "decision_promotion_allowed",
}
RESOURCE_ALLOWED = RESOURCE_REQUIRED | {
    "recorded_utc", "disk_available_kib", "ram_available_kib",
    "queue_started_utc", "queue_deadline_seconds", "queue_ended_utc",
    "observed_gpu_index", "expected_gpu_uuid", "observed_gpu_uuid",
    "observed_memory_mib", "stage_deadline_path", "stage_deadline_sha256",
    "budget_reservation_path", "budget_reservation_sha256",
    "gpu_observations",
}
RESOURCE_REASON_FIELDS = {
    "disk_or_ram_precheck_failed": {"recorded_utc", "disk_available_kib", "ram_available_kib"},
    "gpu_queue_deadline_exceeded": {
        "queue_started_utc", "queue_deadline_seconds", "queue_ended_utc", "gpu_observations"},
    "gpu_requery_failed": {
        "recorded_utc", "observed_gpu_index", "expected_gpu_uuid",
        "observed_gpu_uuid", "observed_memory_mib"},
    "stage_or_total_gpu_budget_gate_failed": {
        "recorded_utc", "observed_gpu_index", "observed_gpu_uuid"},
    "shared_stage_deadline_exhausted": {
        "recorded_utc", "stage_deadline_path", "stage_deadline_sha256",
        "budget_reservation_path", "budget_reservation_sha256"},
}
SUPERSEDED_KEYS = {
    "schema_version", "job", "stage_terminal_state", "stage_terminal_path",
    "stage_terminal_sha256", "scoring_started", "config_sha256",
    "completion_bundle_sha256", "decision_promotion_allowed", "recorded_utc",
}
TIMEOUT_KEYS = {
    "schema_version", "job", "reason", "exit_code", "scoring_started",
    "gpu_index", "gpu_uuid", "stage", "expected_output",
    "process_started_utc", "process_ended_utc", "process_elapsed_seconds",
    "launch_manifest_path", "launch_manifest_sha256", "log_path", "log_sha256",
    "stage_deadline_path", "stage_deadline_sha256", "budget_reservation_path",
    "budget_reservation_sha256", "config_sha256", "completion_bundle_sha256",
    "diagnostic_continuation_only", "decision_promotion_allowed", "recorded_utc",
}
PROCESS_CRASH_KEYS = TIMEOUT_KEYS


def _utc(value: Any, label: str) -> datetime:
    if not isinstance(value, str):
        raise RuntimeError(f"{label} is not an ISO UTC timestamp")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise RuntimeError(f"{label} is not an ISO UTC timestamp") from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise RuntimeError(f"{label} is not timezone-aware")
    return parsed


def _same_path(value: Any, expected: Path, label: str) -> Path:
    if not isinstance(value, str):
        raise RuntimeError(f"{label} path is absent")
    observed = Path(value)
    if observed.resolve() != expected.resolve():
        raise RuntimeError(f"{label} path is not canonical: {observed}")
    return expected


def _stage_id(stage: Path) -> str:
    return hashlib.sha256(str(stage).encode()).hexdigest()[:24]


def _support(path: Path | None) -> tuple[str | None, str | None]:
    if path is None:
        return None, None
    if not path.is_file():
        raise RuntimeError(f"supporting record is absent: {path}")
    return str(path), sha256_file(path)


def validate_gpu_process_intervals(rows: list[Mapping[str, Any]]) -> None:
    """Reject overlapping scoring intervals on one physical GPU UUID."""
    for i, left in enumerate(rows):
        for right in rows[i + 1:]:
            if left.get("gpu_uuid") != right.get("gpu_uuid"):
                continue
            ls = _utc(left.get("process_started_utc"), "left process start")
            le = _utc(left.get("process_ended_utc"), "left process end")
            rs = _utc(right.get("process_started_utc"), "right process start")
            re = _utc(right.get("process_ended_utc"), "right process end")
            if le < ls or re < rs:
                raise RuntimeError("negative GPU process interval")
            if max(ls, rs) < min(le, re):
                raise RuntimeError(
                    f"overlapping GPU ownership: {left.get('job')} and {right.get('job')}")


def _validate_deadline(path: Path, stage: Path) -> dict[str, Any]:
    row = strict_json(path)
    if (set(row) != DEADLINE_KEYS
            or row.get("schema_version") != "atlas_completion_continuation_stage_deadline_v1"
            or _same_path(row.get("stage"), stage, "stage deadline stage") != stage
            or row.get("maximum_stage_wall_seconds") != 86400
            or row.get("decision_promotion_allowed") is not False):
        raise RuntimeError(f"invalid stage deadline: {path}")
    start, end = float(row["started_epoch"]), float(row["deadline_epoch"])
    if end - start != 86400:
        raise RuntimeError(f"stage deadline is not exactly 24 hours: {path}")
    return row


def _validate_reservation(path: Path, job_id: str, stage: Path,
                          expected_hours: float, maximum_hours: float) -> dict[str, Any]:
    row = strict_json(path)
    if (set(row) != RESERVATION_KEYS
            or row.get("schema_version") != "atlas_completion_continuation_gpu_reservation_v1"
            or row.get("job") != job_id
            or _same_path(row.get("stage"), stage, "reservation stage") != stage
            or float(row.get("reserved_gpu_hours", -1)) != expected_hours
            or float(row.get("maximum_total_gpu_hours", -1)) != maximum_hours
            or float(row.get("base_actual_gpu_hours", -1)) < 0
            or float(row.get("prior_reserved_gpu_hours", -1)) < 0
            or row.get("decision_promotion_allowed") is not False):
        raise RuntimeError(f"invalid GPU reservation: {path}")
    if (float(row["base_actual_gpu_hours"]) + float(row["prior_reserved_gpu_hours"])
            + float(row["reserved_gpu_hours"]) > maximum_hours + 1e-9):
        raise RuntimeError(f"GPU reservation exceeds total budget: {path}")
    return row


def _reservation_hours(spec: Mapping[str, Any]) -> float:
    return resource_job_cap_hours(spec, strict_json(CONFIG))


def _optional_resource_limits(job_id: str, spec: Mapping[str, Any],
                              maximum_hours: float) -> dict[str, Any]:
    stage = RUN_ROOT / str(spec["stage"])
    deadline = RUN_ROOT / "stage_deadlines" / f"{_stage_id(stage)}.json"
    reservation = RUN_ROOT / "budget_reservations" / f"{job_id}.json"
    deadline_row = (_validate_deadline(deadline, stage) if deadline.is_file() else None)
    reservation_row = (_validate_reservation(
        reservation, job_id, stage, _reservation_hours(spec), maximum_hours)
        if reservation.is_file() else None)
    deadline_path, deadline_sha = _support(deadline if deadline_row is not None else None)
    reservation_path, reservation_sha = _support(
        reservation if reservation_row is not None else None)
    return {
        "stage_deadline_path": deadline_path,
        "stage_deadline_sha256": deadline_sha,
        "budget_reservation_path": reservation_path,
        "budget_reservation_sha256": reservation_sha,
        "reserved_gpu_hours": (float(reservation_row["reserved_gpu_hours"])
                               if reservation_row is not None else 0.0),
    }


def validate_gpu_job(job_id: str, spec: Mapping[str, Any], *, config_sha: str,
                     freeze_sha: str, maximum_hours: float) -> dict[str, Any]:
    terminal_path = RUN_ROOT / "job_manifests" / f"{job_id}.terminal.json"
    terminal = strict_json(terminal_path)
    stage = RUN_ROOT / str(spec["stage"])
    expected = stage / str(spec["expected"])
    if (set(terminal) != TERMINAL_KEYS
            or terminal.get("schema_version") != "atlas_completion_continuation_job_terminal_v1"
            or terminal.get("job") != job_id
            or terminal.get("outcome") not in VALID_OUTCOMES
            or _same_path(terminal.get("stage"), stage, "job stage") != stage
            or terminal.get("expected_output") != spec["expected"]
            or terminal.get("config_sha256") != config_sha
            or terminal.get("completion_bundle_sha256") != freeze_sha
            or terminal.get("diagnostic_continuation_only") is not True
            or terminal.get("decision_promotion_allowed") is not False):
        raise RuntimeError(f"invalid job terminal: {job_id}")
    ended = _utc(terminal.get("ended_utc"), f"{job_id} ended_utc")
    outcome = str(terminal["outcome"])
    expected_state = {
        "job_process_success": (0, True),
        "resource_not_launched": (75, False),
        "superseded_by_stage_stop": (0, False),
    }
    if outcome in expected_state and (terminal.get("exit_code"), terminal.get("scoring_started")) != expected_state[outcome]:
        raise RuntimeError(f"job outcome/exit/scoring mismatch: {job_id}")
    if outcome == "technical_failure" and not (
            isinstance(terminal.get("exit_code"), int)
            and terminal["exit_code"] != 0 and terminal.get("scoring_started") is True):
        raise RuntimeError(f"technical job outcome is inconsistent: {job_id}")
    if outcome == "resource_timeout" and not (
            terminal.get("exit_code") in {124, 137}
            and terminal.get("scoring_started") is True):
        raise RuntimeError(f"timeout job outcome is inconsistent: {job_id}")
    if outcome == "process_crash" and not (
            isinstance(terminal.get("exit_code"), int)
            and terminal["exit_code"] != 0 and terminal.get("scoring_started") is True):
        raise RuntimeError(f"crashed job outcome is inconsistent: {job_id}")
    if outcome in {"resource_not_launched", "superseded_by_stage_stop"} and (
            terminal.get("process_started_utc") is not None
            or terminal.get("process_ended_utc") is not None
            or float(terminal.get("process_elapsed_seconds", -1)) != 0.0):
        raise RuntimeError(f"unlaunched job has process accounting: {job_id}")
    if outcome == "job_process_success" and not expected.is_file():
        raise RuntimeError(f"successful job lacks expected output: {job_id}")

    manifest_path = RUN_ROOT / "job_manifests" / f"{job_id}.json"
    resource_path = RUN_ROOT / "job_manifests" / f"{job_id}.resource_stop.json"
    superseded_path = RUN_ROOT / "job_manifests" / f"{job_id}.superseded_stage.json"
    timeout_path = RUN_ROOT / "job_manifests" / f"{job_id}.resource_timeout.json"
    crash_path = RUN_ROOT / "job_manifests" / f"{job_id}.process_crash.json"
    launch_failure_path = RUN_ROOT / "LAUNCH_FAILURE.json"
    extras = {
        "launch_manifest_path": None, "launch_manifest_sha256": None,
        "resource_stop_path": None, "resource_stop_sha256": None,
        "superseded_stage_path": None, "superseded_stage_sha256": None,
        "resource_timeout_path": None, "resource_timeout_sha256": None,
        "process_crash_path": None, "process_crash_sha256": None,
        "job_stop_reason": None,
        "launch_failure_path": None, "launch_failure_sha256": None,
        "log_path": None, "log_sha256": None, "started_utc": None,
        "elapsed_seconds": 0.0, "process_started_utc": None,
        "process_ended_utc": None, "process_elapsed_seconds": 0.0,
        "actual_gpu_hours": 0.0,
        "stage_deadline_path": None, "stage_deadline_sha256": None,
        "budget_reservation_path": None, "budget_reservation_sha256": None,
        "reserved_gpu_hours": 0.0,
    }
    launched = outcome in {
        "job_process_success", "technical_failure", "resource_timeout", "process_crash"}
    if launched:
        if not manifest_path.is_file():
            raise RuntimeError(f"launched job lacks manifest: {job_id}")
        manifest = strict_json(manifest_path)
        if (set(manifest) != MANIFEST_KEYS
                or manifest.get("schema_version") != "atlas_completion_continuation_job_manifest_v1"
                or manifest.get("job") != job_id
                or not isinstance(manifest.get("pid"), int) or manifest["pid"] <= 0
                or manifest.get("config_sha256") != config_sha
                or manifest.get("completion_bundle_sha256") != freeze_sha
                or manifest.get("gpu_index") != terminal.get("gpu_index")
                or manifest.get("gpu_uuid") != terminal.get("gpu_uuid")
                or not isinstance(manifest.get("gpu_index"), int)
                or not isinstance(manifest.get("gpu_uuid"), str)
                or not manifest["gpu_uuid"].startswith("GPU-")
                or shlex.split(str(manifest.get("command"))) != canonical_gpu_command(job_id)):
            raise RuntimeError(f"invalid launch manifest: {job_id}")
        started = _utc(manifest.get("started_utc"), f"{job_id} started_utc")
        elapsed = (ended - started).total_seconds()
        if elapsed < 0:
            raise RuntimeError(f"negative job runtime: {job_id}")
        log_path = _same_path(manifest.get("log"), RUN_ROOT / "logs" / f"{job_id}.log",
                              "job log")
        if not log_path.is_file():
            raise RuntimeError(f"launched job log is absent: {job_id}")
        deadline_path = _same_path(
            manifest.get("stage_deadline_path"),
            RUN_ROOT / "stage_deadlines" / f"{_stage_id(stage)}.json", "stage deadline")
        reservation_path = _same_path(
            manifest.get("budget_reservation_path"),
            RUN_ROOT / "budget_reservations" / f"{job_id}.json", "GPU reservation")
        deadline = _validate_deadline(deadline_path, stage)
        reservation = _validate_reservation(
            reservation_path, job_id, stage, _reservation_hours(spec), maximum_hours)
        if (manifest.get("stage_deadline_sha256") != sha256_file(deadline_path)
                or manifest.get("budget_reservation_sha256") != sha256_file(reservation_path)):
            raise RuntimeError(f"launch support hash mismatch: {job_id}")
        policy = strict_json(CONFIG)["diagnostic_continuation"]
        soft_timeout = manifest.get("soft_timeout_seconds")
        grace = manifest.get("termination_grace_seconds")
        margin = manifest.get("timeout_accounting_margin_seconds")
        hard_ceiling = manifest.get("hard_runtime_ceiling_seconds")
        if (not all(isinstance(value, int) for value in [soft_timeout, grace, margin, hard_ceiling])
                or soft_timeout <= 0
                or grace != int(policy["termination_grace_seconds"])
                or margin != int(policy["timeout_accounting_margin_seconds"])
                or soft_timeout + grace + margin > hard_ceiling
                or hard_ceiling > int(float(reservation["reserved_gpu_hours"]) * 3600)
                or hard_ceiling > int(float(deadline["deadline_epoch"]) - started.timestamp()) + 2):
            raise RuntimeError(f"launched job runtime exceeds bound: {job_id}")
        process_started = _utc(terminal.get("process_started_utc"),
                               f"{job_id} process_started_utc")
        process_ended = _utc(terminal.get("process_ended_utc"),
                             f"{job_id} process_ended_utc")
        process_elapsed = float(terminal.get("process_elapsed_seconds", -1))
        timestamp_elapsed = (process_ended - process_started).total_seconds()
        if (process_started < started or process_ended > ended
                or process_elapsed < 0 or abs(process_elapsed - timestamp_elapsed) > 1.0
                or process_elapsed > hard_ceiling
                or process_elapsed > float(reservation["reserved_gpu_hours"]) * 3600):
            raise RuntimeError(f"GPU process elapsed time exceeds hard reservation: {job_id}")
        extras.update({
            "launch_manifest_path": str(manifest_path),
            "launch_manifest_sha256": sha256_file(manifest_path),
            "log_path": str(log_path), "log_sha256": sha256_file(log_path),
            "started_utc": manifest["started_utc"], "elapsed_seconds": elapsed,
            "process_started_utc": terminal["process_started_utc"],
            "process_ended_utc": terminal["process_ended_utc"],
            "process_elapsed_seconds": process_elapsed,
            "actual_gpu_hours": process_elapsed / 3600.0,
            "stage_deadline_path": str(deadline_path),
            "stage_deadline_sha256": sha256_file(deadline_path),
            "budget_reservation_path": str(reservation_path),
            "budget_reservation_sha256": sha256_file(reservation_path),
            "reserved_gpu_hours": float(reservation["reserved_gpu_hours"]),
        })
        if resource_path.exists() or superseded_path.exists():
            raise RuntimeError(f"launched job has conflicting unlaunched support: {job_id}")
        if outcome == "technical_failure" and (
                terminal_state(stage) is None or launch_failure_path.is_file()):
            launch = strict_json(launch_failure_path)
            if (launch.get("schema_version") != "atlas_completion_diagnostic_continuation_launch_failure_v1"
                    or launch.get("job_id") != job_id
                    or launch.get("config_sha256") != config_sha
                    or launch.get("completion_bundle_sha256") != freeze_sha
                    or launch.get("diagnostic_continuation_only") is not True
                    or launch.get("decision_promotion_allowed") is not False):
                raise RuntimeError(f"invalid launch-failure closure: {job_id}")
            extras["launch_failure_path"], extras["launch_failure_sha256"] = _support(launch_failure_path)
            extras["job_stop_reason"] = (
                f"launch_failure:{launch.get('error_type')}:{launch.get('error')}")
        if outcome == "technical_failure" and extras["job_stop_reason"] is None:
            state = terminal_state(stage)
            if state is None:
                raise RuntimeError(f"technical job has no replayable failure reason: {job_id}")
            stage_terminal = stage / (
                "MEASUREMENT_COMPLETE.json" if state == "complete"
                else "FROZEN_EQUIVOCAL_STOP.json")
            marker = strict_json(stage_terminal)
            reason = marker.get("reason") or marker.get("stop_code") or marker.get("failed_gate")
            if not isinstance(reason, str) or not reason:
                raise RuntimeError(f"technical stage terminal lacks reason: {job_id}")
            extras["job_stop_reason"] = reason
        if outcome == "resource_timeout":
            timeout = strict_json(timeout_path)
            if (set(timeout) != TIMEOUT_KEYS
                    or timeout.get("schema_version") != "atlas_completion_continuation_resource_timeout_v1"
                    or timeout.get("job") != job_id
                    or timeout.get("reason") != "hard_runtime_supervisor_expired"
                    or timeout.get("exit_code") != terminal.get("exit_code")
                    or timeout.get("scoring_started") is not True
                    or timeout.get("gpu_index") != manifest.get("gpu_index")
                    or timeout.get("gpu_uuid") != manifest.get("gpu_uuid")
                    or _same_path(timeout.get("stage"), stage, "timeout stage") != stage
                    or timeout.get("expected_output") != spec["expected"]
                    or timeout.get("process_started_utc") != terminal.get("process_started_utc")
                    or timeout.get("process_ended_utc") != terminal.get("process_ended_utc")
                    or float(timeout.get("process_elapsed_seconds", -1)) != process_elapsed
                    or _same_path(timeout.get("launch_manifest_path"), manifest_path,
                                  "timeout launch manifest") != manifest_path
                    or timeout.get("launch_manifest_sha256") != sha256_file(manifest_path)
                    or _same_path(timeout.get("log_path"), log_path, "timeout log") != log_path
                    or timeout.get("log_sha256") != sha256_file(log_path)
                    or _same_path(timeout.get("stage_deadline_path"), deadline_path,
                                  "timeout stage deadline") != deadline_path
                    or timeout.get("stage_deadline_sha256") != sha256_file(deadline_path)
                    or _same_path(timeout.get("budget_reservation_path"), reservation_path,
                                  "timeout GPU reservation") != reservation_path
                    or timeout.get("budget_reservation_sha256") != sha256_file(reservation_path)
                    or timeout.get("config_sha256") != config_sha
                    or timeout.get("completion_bundle_sha256") != freeze_sha
                    or timeout.get("diagnostic_continuation_only") is not True
                    or timeout.get("decision_promotion_allowed") is not False
                    or process_elapsed + 2.0 < float(manifest["soft_timeout_seconds"])):
                raise RuntimeError(f"invalid runner-owned timeout closure: {job_id}")
            _utc(timeout.get("recorded_utc"), f"{job_id} timeout recorded_utc")
            extras["resource_timeout_path"], extras["resource_timeout_sha256"] = _support(timeout_path)
            extras["job_stop_reason"] = str(timeout["reason"])
        elif timeout_path.exists():
            raise RuntimeError(f"non-timeout job has conflicting timeout support: {job_id}")
        if outcome == "process_crash":
            crash = strict_json(crash_path)
            if (set(crash) != PROCESS_CRASH_KEYS
                    or crash.get("schema_version") != "atlas_completion_continuation_process_crash_v1"
                    or crash.get("job") != job_id
                    or crash.get("reason") != "uncatchable_process_exit"
                    or crash.get("exit_code") != terminal.get("exit_code")
                    or crash.get("scoring_started") is not True
                    or crash.get("gpu_index") != manifest.get("gpu_index")
                    or crash.get("gpu_uuid") != manifest.get("gpu_uuid")
                    or _same_path(crash.get("stage"), stage, "crash stage") != stage
                    or crash.get("expected_output") != spec["expected"]
                    or crash.get("process_started_utc") != terminal.get("process_started_utc")
                    or crash.get("process_ended_utc") != terminal.get("process_ended_utc")
                    or float(crash.get("process_elapsed_seconds", -1)) != process_elapsed
                    or _same_path(crash.get("launch_manifest_path"), manifest_path,
                                  "crash launch manifest") != manifest_path
                    or crash.get("launch_manifest_sha256") != sha256_file(manifest_path)
                    or _same_path(crash.get("log_path"), log_path, "crash log") != log_path
                    or crash.get("log_sha256") != sha256_file(log_path)
                    or _same_path(crash.get("stage_deadline_path"), deadline_path,
                                  "crash stage deadline") != deadline_path
                    or crash.get("stage_deadline_sha256") != sha256_file(deadline_path)
                    or _same_path(crash.get("budget_reservation_path"), reservation_path,
                                  "crash GPU reservation") != reservation_path
                    or crash.get("budget_reservation_sha256") != sha256_file(reservation_path)
                    or crash.get("config_sha256") != config_sha
                    or crash.get("completion_bundle_sha256") != freeze_sha
                    or crash.get("diagnostic_continuation_only") is not True
                    or crash.get("decision_promotion_allowed") is not False):
                raise RuntimeError(f"invalid runner-owned process-crash closure: {job_id}")
            _utc(crash.get("recorded_utc"), f"{job_id} crash recorded_utc")
            extras["process_crash_path"], extras["process_crash_sha256"] = _support(crash_path)
            extras["job_stop_reason"] = str(crash["reason"])
        elif crash_path.exists():
            raise RuntimeError(f"non-crash job has conflicting process-crash support: {job_id}")
    elif outcome == "resource_not_launched":
        if manifest_path.exists() or superseded_path.exists() or timeout_path.exists() or crash_path.exists():
            raise RuntimeError(f"resource job has conflicting support: {job_id}")
        if terminal.get("gpu_index") is not None or terminal.get("gpu_uuid") is not None:
            raise RuntimeError(f"not-launched job reports a launched GPU: {job_id}")
        resource = strict_json(resource_path)
        reason = resource.get("reason")
        if (not RESOURCE_REQUIRED <= set(resource) or not set(resource) <= RESOURCE_ALLOWED
                or resource.get("schema_version") != "atlas_completion_continuation_resource_stop_v1"
                or resource.get("job") != job_id
                or reason not in RESOURCE_REASON_FIELDS
                or set(resource) != RESOURCE_REQUIRED | RESOURCE_REASON_FIELDS[str(reason)]
                or resource.get("scoring_started") is not False
                or resource.get("config_sha256") != config_sha
                or resource.get("completion_bundle_sha256") != freeze_sha
                or resource.get("decision_promotion_allowed") is not False):
            raise RuntimeError(f"invalid resource closure: {job_id}")
        if "recorded_utc" in resource:
            _utc(resource["recorded_utc"], f"{job_id} resource recorded_utc")
        if "queue_started_utc" in resource:
            _utc(resource["queue_started_utc"], f"{job_id} queue_started_utc")
            _utc(resource.get("queue_ended_utc"), f"{job_id} queue_ended_utc")
            if resource.get("queue_deadline_seconds") != 43200:
                raise RuntimeError(f"invalid allocation deadline: {job_id}")
            observations = resource.get("gpu_observations")
            if not isinstance(observations, list):
                raise RuntimeError(f"invalid GPU queue observations: {job_id}")
            for observation in observations:
                if (not isinstance(observation, dict)
                        or set(observation) != {"gpu_index", "gpu_uuid", "memory_used_mib"}
                        or not isinstance(observation["gpu_index"], int)
                        or not isinstance(observation["gpu_uuid"], str)
                        or not observation["gpu_uuid"].startswith("GPU-")
                        or not isinstance(observation["memory_used_mib"], int)
                        or observation["memory_used_mib"] < 0):
                    raise RuntimeError(f"malformed GPU queue observation: {job_id}")
        extras.update(_optional_resource_limits(job_id, spec, maximum_hours))
        extras["resource_stop_path"], extras["resource_stop_sha256"] = _support(resource_path)
        extras["job_stop_reason"] = str(resource["reason"])
    else:
        if manifest_path.exists() or resource_path.exists() or timeout_path.exists() or crash_path.exists():
            raise RuntimeError(f"superseded job has conflicting support: {job_id}")
        if terminal.get("gpu_index") is not None or terminal.get("gpu_uuid") is not None:
            raise RuntimeError(f"superseded job reports a launched GPU: {job_id}")
        superseded = strict_json(superseded_path)
        state = terminal_state(stage)
        selected = (stage / ("MEASUREMENT_COMPLETE.json" if state == "complete"
                             else "FROZEN_EQUIVOCAL_STOP.json") if state else None)
        if (set(superseded) != SUPERSEDED_KEYS
                or superseded.get("schema_version") != "atlas_completion_continuation_superseded_v1"
                or superseded.get("job") != job_id
                or superseded.get("stage_terminal_state") != state
                or selected is None
                or _same_path(superseded.get("stage_terminal_path"), selected,
                              "superseded stage terminal") != selected
                or superseded.get("stage_terminal_sha256") != sha256_file(selected)
                or superseded.get("scoring_started") is not False
                or superseded.get("config_sha256") != config_sha
                or superseded.get("completion_bundle_sha256") != freeze_sha
                or superseded.get("decision_promotion_allowed") is not False):
            raise RuntimeError(f"invalid superseded closure: {job_id}")
        _utc(superseded.get("recorded_utc"), f"{job_id} superseded recorded_utc")
        extras.update(_optional_resource_limits(job_id, spec, maximum_hours))
        extras["superseded_stage_path"], extras["superseded_stage_sha256"] = _support(superseded_path)
        marker = strict_json(selected)
        reason = marker.get("reason") or marker.get("stop_code") or marker.get("failed_gate")
        extras["job_stop_reason"] = (
            str(reason) if isinstance(reason, str) and reason
            else f"superseded_by_stage_{state}")

    return {
        **terminal,
        "terminal_path": str(terminal_path), "terminal_sha256": sha256_file(terminal_path),
        "expected_output_path": str(expected),
        "expected_output_sha256": sha256_file(expected) if expected.is_file() else None,
        **extras,
    }


def _validate_stage_terminal(stage: Path, *, config_sha: str,
                             freeze_sha: str) -> tuple[str | None, Path | None]:
    state = terminal_state(stage)
    if state is None:
        return None, None
    path = stage / ("MEASUREMENT_COMPLETE.json" if state == "complete"
                    else "FROZEN_EQUIVOCAL_STOP.json")
    marker = strict_json(path)
    relative = stage.resolve().relative_to(RUN_ROOT.resolve())
    if relative.parts[0] == "k2_refit":
        allowed = ({"atlas_completion_refit_terminal_v1"} if state == "complete" else
                   {"atlas_completion_frozen_stop_v1",
                    "atlas_completion_diagnostic_continuation_technical_stop_v1"})
    elif relative.parts == ("stability",):
        allowed = ({"atlas_completion_stability_terminal_v1"} if state == "complete" else
                   {"atlas_completion_frozen_stop_v1",
                    "atlas_completion_diagnostic_continuation_technical_stop_v1"})
    elif relative.parts[0] == "specificity":
        allowed = ({"atlas_completion_specificity_complete_v1"} if state == "complete" else
                   {"atlas_completion_diagnostic_continuation_technical_stop_v1"})
    else:
        raise RuntimeError(f"unregistered continuation stage terminal: {stage}")
    if (marker.get("config_sha256") != config_sha
            or marker.get("completion_bundle_sha256") != freeze_sha
            or marker.get("schema_version") not in allowed
            or marker.get("terminal_state") != (
                "measurement_complete" if state == "complete" else "frozen_equivocal_stop")
            or marker.get("evidence_class") != "postscore_amended_architecture_evidence"
            or marker.get("decision_promotion_allowed") is True):
        raise RuntimeError(f"stage terminal binding mismatch: {stage}")
    if state == "stopped" and marker.get("decision_promotion_allowed") is not False:
        raise RuntimeError(f"stopped stage terminal permits or omits promotion denial: {stage}")
    if marker.get("schema_version") == "atlas_completion_diagnostic_continuation_technical_stop_v1" and (
            marker.get("diagnostic_continuation_only") is not True
            or marker.get("scientific_retry_allowed") is not False):
        raise RuntimeError(f"technical stage terminal semantics mismatch: {stage}")
    _utc(marker.get("ended_utc"), f"{stage} terminal ended_utc")
    return state, path


def recompute_stages(jobs: Mapping[str, Mapping[str, Any]], *, config_sha: str,
                     freeze_sha: str) -> dict[str, Any]:
    stages: dict[str, Any] = {}
    for stage_name, members in canonical_stage_members().items():
        stage = RUN_ROOT / stage_name
        state, terminal_path = _validate_stage_terminal(
            stage, config_sha=config_sha, freeze_sha=freeze_sha)
        outcomes = [str(jobs[j]["outcome"]) for j in members]
        if any(outcome in {"resource_not_launched", "resource_timeout"} for outcome in outcomes):
            stage_outcome = "resource_incomplete"
        elif any(outcome == "process_crash" for outcome in outcomes):
            stage_outcome = "process_incomplete"
        elif any(jobs[j].get("launch_failure_path") for j in members):
            stage_outcome = "launch_failure_incomplete"
        elif state == "complete" and all(outcome == "job_process_success" for outcome in outcomes):
            stage_outcome = "complete"
        elif state == "stopped" and all(outcome in {
                "job_process_success", "technical_failure", "superseded_by_stage_stop"
        } for outcome in outcomes):
            stage_outcome = "stopped"
        elif state is None:
            failing = [job for job in members if jobs[job]["outcome"] == "technical_failure"]
            if failing and all(jobs[j].get("launch_failure_path") for j in failing):
                stage_outcome = "launch_failure_incomplete"
            else:
                raise RuntimeError(f"stage lacks terminal without bound closure: {stage_name}")
        else:
            raise RuntimeError(f"incompatible job/stage terminal outcomes: {stage_name}")
        for job in members:
            if jobs[job]["outcome"] == "superseded_by_stage_stop":
                if (jobs[job]["superseded_stage_path"] != str(terminal_path)
                        or jobs[job].get("expected_output_sha256") is not None):
                    raise RuntimeError(f"superseded job conflicts with stage terminal: {job}")
        stages[stage_name] = {
            "member_jobs": members,
            "member_outcomes": dict(zip(members, outcomes)),
            "stage_outcome": stage_outcome,
            "selected_terminal_state": state,
            "terminal_path": str(terminal_path) if terminal_path else None,
            "terminal_sha256": sha256_file(terminal_path) if terminal_path else None,
        }
    return stages


def recompute_job_and_stage_records() -> tuple[dict[str, Any], dict[str, Any], str]:
    freeze = verify_continuation_freeze()
    config = strict_json(CONFIG)
    config_sha, freeze_sha = sha256_file(CONFIG), str(freeze["bundle_sha256"])
    specs = canonical_job_specs()
    jobs = {job: validate_gpu_job(
        job, spec, config_sha=config_sha, freeze_sha=freeze_sha,
        maximum_hours=float(config["budgets"]["maximum_total_gpu_hours"]))
        for job, spec in specs.items()}
    # Reservations are conservative and actual launched time is the authoritative
    # accounting. Both independently remain within the same frozen total cap.
    reservations = [float(row["reserved_gpu_hours"]) for row in jobs.values()]
    base_values = []
    for row in jobs.values():
        path = row.get("budget_reservation_path")
        if path:
            base_values.append(float(strict_json(Path(path))["base_actual_gpu_hours"]))
    base_ledger = base_gpu_ledger()
    expected_base = float(base_ledger["total_gpu_hours"])
    if base_values and any(abs(value - expected_base) > 1e-9 for value in base_values):
        raise RuntimeError("GPU reservation base accounting is inconsistent")
    maximum = float(config["budgets"]["maximum_total_gpu_hours"])
    base = expected_base
    bound_reservations = {
        Path(str(row["budget_reservation_path"])).resolve()
        for row in jobs.values() if row.get("budget_reservation_path")}
    observed_reservations = {
        path.resolve() for path in (RUN_ROOT / "budget_reservations").glob("*.json")
    }
    if bound_reservations != observed_reservations:
        raise RuntimeError("GPU reservation file inventory differs from job replay")
    reservation_rows = [strict_json(path) for path in bound_reservations]
    running, pending = 0.0, list(reservation_rows)
    while pending:
        matches = [row for row in pending
                   if abs(float(row["prior_reserved_gpu_hours"]) - running) <= 1e-9]
        if len(matches) != 1:
            raise RuntimeError("GPU reservation atomic prior-total chain is invalid")
        row = matches[0]; pending.remove(row)
        running += float(row["reserved_gpu_hours"])
    if abs(running - sum(reservations)) > 1e-9:
        raise RuntimeError("observed reservation sum differs from assigned job caps")
    if base + sum(reservations) > maximum + 1e-9:
        raise RuntimeError("continuation reservations exceed frozen total GPU-hour budget")
    if base + sum(float(row["actual_gpu_hours"]) for row in jobs.values()) > maximum + 1e-9:
        raise RuntimeError("actual continuation GPU-hours exceed frozen total budget")
    # The allocator must not overlap two scoring processes on one physical UUID.
    launched = [row for row in jobs.values() if row["started_utc"] is not None]
    validate_gpu_process_intervals(launched)
    stages = recompute_stages(jobs, config_sha=config_sha, freeze_sha=freeze_sha)
    outcome = ("closed_all_stages" if all(
        row["stage_outcome"] in {"complete", "stopped"} for row in stages.values())
        else "closed_with_incomplete_diagnostics")
    return jobs, stages, outcome


def validate_baseline_failure_collection(collection: Mapping[str, Any]) -> dict[str, Any]:
    freeze = verify_continuation_freeze()
    inventory = verify_source_inventory()
    expected_keys = {
        "schema_version", "evidence_class", "reason", "jobs", "stages",
        "config_sha256", "completion_bundle_sha256", "source_inventory_sha256",
        "diagnostic_continuation_only", "decision_promotion_allowed", "recorded_utc",
        "collection_outcome",
    }
    if (set(collection) != expected_keys
            or collection.get("schema_version") != "atlas_completion_diagnostic_continuation_collection_v1"
            or collection.get("collection_outcome") != "baseline_not_complete"
            or collection.get("reason") != "baseline_provenance_rebind_failed"
            or collection.get("config_sha256") != sha256_file(CONFIG)
            or collection.get("completion_bundle_sha256") != freeze["bundle_sha256"]
            or collection.get("source_inventory_sha256") != inventory["inventory_sha256"]
            or collection.get("diagnostic_continuation_only") is not True
            or collection.get("decision_promotion_allowed") is not False):
        raise RuntimeError("invalid baseline-failure collection")
    _utc(collection.get("recorded_utc"), "collection recorded_utc")
    specs, stage_members = canonical_job_specs(), canonical_stage_members()
    if set(collection.get("jobs", {})) != set(specs) or set(collection.get("stages", {})) != set(stage_members):
        raise RuntimeError("baseline-failure collection inventory mismatch")
    allowed = {
        (RUN_ROOT / "baseline/FROZEN_EQUIVOCAL_STOP.json").resolve(),
        (RUN_ROOT / "job_manifests/baseline_rebind.terminal.json").resolve(),
    }
    causes = {Path(row.get("cause_path", "")).resolve() for row in collection["jobs"].values()}
    if len(causes) != 1 or next(iter(causes)) not in allowed:
        raise RuntimeError("baseline-failure cause is not canonical")
    cause = next(iter(causes))
    if not cause.is_file():
        raise RuntimeError("baseline-failure cause is absent")
    cause_sha = sha256_file(cause)
    for job, spec in specs.items():
        expected = {"outcome": "baseline_not_complete", "stage": spec["stage"],
                    "cause_path": str(cause), "cause_sha256": cause_sha}
        if collection["jobs"][job] != expected:
            raise RuntimeError(f"baseline-failure job binding mismatch: {job}")
    for stage, members in stage_members.items():
        expected = {"member_jobs": members, "stage_outcome": "baseline_not_complete",
                    "terminal_path": None, "terminal_sha256": None}
        if collection["stages"][stage] != expected:
            raise RuntimeError(f"baseline-failure stage binding mismatch: {stage}")
    marker = strict_json(NOT_LAUNCHED)
    expected_marker = dict(collection)
    expected_marker.pop("collection_outcome")
    expected_marker["schema_version"] = "atlas_completion_diagnostic_continuation_not_launched_v1"
    if marker != expected_marker:
        raise RuntimeError("baseline not-launched marker differs from collection")
    return dict(collection)


def validate_collection(collection: Mapping[str, Any]) -> dict[str, Any]:
    if collection.get("collection_outcome") == "baseline_not_complete":
        return validate_baseline_failure_collection(collection)
    freeze = verify_continuation_freeze()
    inventory = verify_source_inventory()
    expected_keys = {
        "schema_version", "collection_outcome", "jobs", "stages", "config_sha256",
        "completion_bundle_sha256", "source_inventory_sha256",
        "diagnostic_continuation_only", "decision_promotion_allowed", "recorded_utc",
    }
    if (set(collection) != expected_keys
            or collection.get("schema_version") != "atlas_completion_diagnostic_continuation_collection_v1"
            or collection.get("config_sha256") != sha256_file(CONFIG)
            or collection.get("completion_bundle_sha256") != freeze["bundle_sha256"]
            or collection.get("source_inventory_sha256") != inventory["inventory_sha256"]
            or collection.get("diagnostic_continuation_only") is not True
            or collection.get("decision_promotion_allowed") is not False):
        raise RuntimeError("invalid continuation collection envelope")
    _utc(collection.get("recorded_utc"), "collection recorded_utc")
    jobs, stages, outcome = recompute_job_and_stage_records()
    if collection.get("jobs") != jobs or collection.get("stages") != stages or collection.get("collection_outcome") != outcome:
        raise RuntimeError("collection differs from strict supporting-record replay")
    marker_required = outcome != "closed_all_stages" or any(
        row["outcome"] != "job_process_success" for row in jobs.values())
    if marker_required:
        marker = strict_json(NOT_LAUNCHED)
        expected_marker = marker_payload(
            jobs=jobs, stages=stages,
            reason="diagnostic_jobs_not_all_scientifically_complete")
        expected_marker["recorded_utc"] = marker.get("recorded_utc")
        _utc(marker.get("recorded_utc"), "not-launched recorded_utc")
        if marker != expected_marker:
            raise RuntimeError("not-launched marker differs from strict replay")
    elif NOT_LAUNCHED.exists():
        raise RuntimeError("unexpected not-launched marker for fully successful collection")
    return dict(collection)


def marker_payload(*, jobs: Mapping[str, Mapping[str, Any]],
                   stages: Mapping[str, Mapping[str, Any]], reason: str) -> dict[str, Any]:
    freeze = verify_continuation_freeze()
    entries: dict[str, Any] = {}
    for job_id, row in sorted(jobs.items()):
        stage_name = str(canonical_job_specs()[job_id]["stage"])
        if row["outcome"] == "job_process_success" and stages[stage_name]["stage_outcome"] in {"complete", "stopped"}:
            continue
        support_fields = [
            ("resource_stop_path", "resource_stop_sha256"),
            ("resource_timeout_path", "resource_timeout_sha256"),
            ("process_crash_path", "process_crash_sha256"),
            ("superseded_stage_path", "superseded_stage_sha256"),
            ("launch_failure_path", "launch_failure_sha256"),
            ("terminal_path", "terminal_sha256"),
        ]
        cause_path, cause_sha = next(
            ((row[p], row[h]) for p, h in support_fields if row.get(p)), (None, None))
        entries[job_id] = {
            "cause_path": cause_path, "cause_sha256": cause_sha,
            "reason": (row["outcome"] if row["outcome"] != "job_process_success"
                       else f"sibling_{stages[stage_name]['stage_outcome']}"),
        }
    return {
        "schema_version": "atlas_completion_diagnostic_continuation_not_launched_v1",
        "evidence_class": "postscore_amended_architecture_evidence",
        "reason": reason, "jobs": entries, "stages": stages,
        "config_sha256": sha256_file(CONFIG),
        "completion_bundle_sha256": freeze["bundle_sha256"],
        "source_inventory_sha256": verify_source_inventory()["inventory_sha256"],
        "diagnostic_continuation_only": True, "decision_promotion_allowed": False,
        "recorded_utc": utc_now(),
    }


def close_baseline_failure(cause: Path) -> None:
    freeze = verify_continuation_freeze()
    inventory = verify_source_inventory()
    allowed = {
        (RUN_ROOT / "baseline/FROZEN_EQUIVOCAL_STOP.json").resolve(),
        (RUN_ROOT / "job_manifests/baseline_rebind.terminal.json").resolve(),
    }
    cause = cause.resolve()
    if cause not in allowed:
        raise PermissionError("baseline-failure cause is not a canonical continuation artifact")
    if not cause.is_file():
        raise RuntimeError(f"baseline failure cause absent: {cause}")
    cause_sha = sha256_file(cause)
    jobs = {job: {"outcome": "baseline_not_complete", "stage": spec["stage"],
                  "cause_path": str(cause), "cause_sha256": cause_sha}
            for job, spec in canonical_job_specs().items()}
    stages = {stage: {"member_jobs": members, "stage_outcome": "baseline_not_complete",
                      "terminal_path": None, "terminal_sha256": None}
              for stage, members in canonical_stage_members().items()}
    payload = {
        "schema_version": "atlas_completion_diagnostic_continuation_not_launched_v1",
        "evidence_class": "postscore_amended_architecture_evidence",
        "reason": "baseline_provenance_rebind_failed", "jobs": jobs, "stages": stages,
        "config_sha256": sha256_file(CONFIG),
        "completion_bundle_sha256": freeze["bundle_sha256"],
        "source_inventory_sha256": inventory["inventory_sha256"],
        "diagnostic_continuation_only": True, "decision_promotion_allowed": False,
        "recorded_utc": utc_now(),
    }
    atomic_write_json(NOT_LAUNCHED, payload)
    collection = {**payload,
        "schema_version": "atlas_completion_diagnostic_continuation_collection_v1",
        "collection_outcome": "baseline_not_complete"}
    atomic_write_json(COLLECTION, collection)
    validate_collection(collection)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--baseline-failed", type=Path)
    args = parser.parse_args()
    verify_continuation_freeze()
    verify_source_inventory()
    if args.baseline_failed is not None:
        close_baseline_failure(args.baseline_failed)
        return
    verify_rebound_baseline()
    specs = canonical_job_specs()
    terminal_dir = RUN_ROOT / "job_manifests"
    deadline = time.monotonic() + 133200  # 12h allocation + 24h stage + 1h closure.
    while True:
        missing = [job for job in specs if not (terminal_dir / f"{job}.terminal.json").is_file()]
        if not missing:
            break
        if time.monotonic() >= deadline:
            raise RuntimeError(f"collector deadline exceeded with missing jobs: {missing}")
        time.sleep(30)
    observed = {p.name.removesuffix(".terminal.json") for p in terminal_dir.glob("*.terminal.json")
                if p.name not in {"baseline_rebind.terminal.json", "collector.terminal.json"}}
    if observed != set(specs):
        raise RuntimeError(f"GPU job terminal inventory mismatch: {sorted(observed ^ set(specs))}")
    jobs, stages, outcome = recompute_job_and_stage_records()
    payload = {
        "schema_version": "atlas_completion_diagnostic_continuation_collection_v1",
        "collection_outcome": outcome, "jobs": jobs, "stages": stages,
        "config_sha256": sha256_file(CONFIG),
        "completion_bundle_sha256": verify_continuation_freeze()["bundle_sha256"],
        "source_inventory_sha256": verify_source_inventory()["inventory_sha256"],
        "diagnostic_continuation_only": True, "decision_promotion_allowed": False,
        "recorded_utc": utc_now(),
    }
    atomic_write_json(COLLECTION, payload)
    if outcome != "closed_all_stages" or any(
            row["outcome"] != "job_process_success" for row in jobs.values()):
        atomic_write_json(NOT_LAUNCHED, marker_payload(
            jobs=jobs, stages=stages,
            reason="diagnostic_jobs_not_all_scientifically_complete"))
    validate_collection(payload)
    print({"collection_outcome": outcome, "jobs": len(jobs), "stages": len(stages)})


if __name__ == "__main__":
    main()
