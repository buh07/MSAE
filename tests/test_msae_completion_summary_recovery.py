from __future__ import annotations

import errno
import copy
import json
import os
import signal
import shutil
import socket
import subprocess
import sys
import textwrap
import time
import uuid
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import msa_completion_summary_recovery_common as rc
import recover_msae_completion_continuation_summary as recovery
import freeze_msae_completion_summary_recovery as initial_freezer
import freeze_msae_completion_summary_promotion as promotion_freezer
from msa_completion_common import sha256_file

ATTEMPT_A = "20260802T120000Z_10001_aaaabbbb"
ATTEMPT_B = "20260802T120001Z_10002_ccccdddd"

FAKE_MOUNT = {
    "mount_id": "1", "parent_mount_id": "0", "major_minor": "0:1",
    "mount_point": "/fixture", "mount_options": ["rw"],
    "filesystem_type": "nfs4", "source": "fixture:/export",
    "super_options": ["rw"], "target": "/fixture/results/atlas", "st_dev": 1,
}


@contextmanager
def locked_fixture(tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
                   job: str = "candidate") -> Iterator[Path]:
    run = tmp_path / "recovery"
    for relative in rc.RECOVERY_DIRECTORIES:
        (run / relative).mkdir(parents=True, exist_ok=True)
    lock = run / "locks" / f"{job}.lock"
    lock.touch()
    monkeypatch.setattr(rc, "ROOT", tmp_path)
    monkeypatch.setattr(recovery, "ROOT", tmp_path)
    monkeypatch.setattr(rc, "recovery_run_root", lambda: run)
    monkeypatch.setattr(rc, "deployment_mount", lambda: dict(FAKE_MOUNT))
    monkeypatch.setattr(rc, "verify_initial_freeze", lambda: {"bundle_sha256": "1" * 64})
    monkeypatch.setattr(rc, "verify_promotion_freeze", lambda: {"bundle_sha256": "2" * 64})
    monkeypatch.setattr(
        rc, "_applicable_freezes",
        lambda value: ("1" * 64, "2" * 64 if value == "publish" else None),
    )
    with rc.supervisor_job_lock(job):
        yield run


def state_building(destination: Path, stage: Path, attempt: str = ATTEMPT_A) -> None:
    rc.append_state("candidate", attempt, {
        "phase": "building", "publication_attempt_id": ATTEMPT_A,
        "staging": str(stage.relative_to(rc.ROOT)),
        "destination": str(destination.relative_to(rc.ROOT)),
        "initial_recovery_bundle_sha256": "1" * 64,
        "promotion_bundle_sha256": None,
        "parent_fsync_complete": False,
    }, claim=True)


def candidate_stage(parent: Path) -> Path:
    stage = parent / ".completion_diagnostic_candidate.staging.fixture"
    stage.mkdir()
    for name, payload in {
        "diagnostic_results.json": b"{}\n",
        "diagnostic_results.md": b"# report\n",
        "source_lineage.json": b"{}\n",
        "CANDIDATE_COMPLETE.json": b"{}\n",
    }.items():
        (stage / name).write_bytes(payload)
    return stage


def capability_payload(job: str, attempt: str, log: str,
                       mode: str = "run") -> dict[str, object]:
    return {
        "schema_version": "atlas_completion_summary_recovery_filesystem_capability_v2",
        "job": job, "attempt_id": attempt, "mode": mode,
        "argv": ["python", "driver", job], "log": log,
        "tested_host": socket.gethostname(),
        "mount": dict(FAKE_MOUNT),
        "outcomes": {
            "file": {
                "success": {
                    "source_sha256": rc.sha256_bytes(b"success"),
                    "destination_sha256": rc.sha256_bytes(b"success"),
                    "source_size": 7, "destination_size": 7,
                    "source_regular": True, "destination_regular": True,
                    "source_st_dev": 67, "source_st_ino": 101,
                    "destination_st_dev": 67, "destination_st_ino": 101,
                    "same_inode": True,
                },
                "eexist_preserved": {
                    "source_sha256_before": rc.sha256_bytes(b"source"),
                    "source_sha256_after": rc.sha256_bytes(b"source"),
                    "destination_sha256_before": rc.sha256_bytes(b"destination"),
                    "destination_sha256_after": rc.sha256_bytes(b"destination"),
                    "source_size_before": 6, "source_size_after": 6,
                    "destination_size_before": 11, "destination_size_after": 11,
                    "source_st_dev_before": 67, "source_st_dev_after": 67,
                    "source_st_ino_before": 102, "source_st_ino_after": 102,
                    "destination_st_dev_before": 67, "destination_st_dev_after": 67,
                    "destination_st_ino_before": 103, "destination_st_ino_after": 103,
                    "source_regular": True, "destination_regular": True,
                    "distinct_inodes": True,
                },
                "two_process": {
                    "exit_codes": [0, 17], "target_present": True,
                    "sources_preserved": True,
                    "source_sha256": [rc.sha256_bytes(b"source-0"),
                                      rc.sha256_bytes(b"source-1")],
                    "source_size": [8, 8], "source_regular": [True, True],
                    "source_st_dev": [67, 67], "source_st_ino": [104, 105],
                    "target_sha256": rc.sha256_bytes(b"source-0"), "target_size": 8,
                    "target_st_dev": 67, "target_st_ino": 104,
                    "target_regular": True, "winner_index": 0,
                    "target_matches_winner": True,
                    "target_same_inode_as_winner": True,
                },
            },
            "directory": {
                "success": {
                    "destination_directory": True,
                    "destination_st_dev": 67, "destination_st_ino": 106,
                    "marker_sha256": rc.sha256_bytes(b"success"),
                    "marker_size": 7, "marker_regular": True,
                },
                "eexist_preserved": {
                    "destination_directory": True,
                    "marker_sha256_before": rc.sha256_bytes(b"destination"),
                    "marker_sha256_after": rc.sha256_bytes(b"destination"),
                    "marker_size_before": 11, "marker_size_after": 11,
                    "marker_regular": True,
                    "destination_st_dev_before": 67, "destination_st_dev_after": 67,
                    "destination_st_ino_before": 107, "destination_st_ino_after": 107,
                },
                "two_process": {
                    "exit_codes": [0, 17], "target_present": True,
                    "target_directory": True, "target_empty": True,
                    "target_st_dev": 67, "target_st_ino": 108,
                },
            },
            "job_lock": {"separate_descriptor_lost": True,
                         "guarded_manifest_marker_created": False},
        },
        "all_passed": True, "tested_utc": "2026-08-02T12:00:00+00:00",
    }


def install_attempt_evidence(run: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
                             *, attempt: str = ATTEMPT_A, mode: str = "run") -> Path:
    destination = tmp_path / "candidate"
    monkeypatch.setattr(rc, "candidate_root", lambda: destination)
    monkeypatch.setattr(recovery, "candidate_root", lambda: destination)
    monkeypatch.setattr(recovery, "recovery_run_root", lambda: run)
    log = run / "logs" / f"candidate.{attempt}.log"
    log.write_text("attempt\n", encoding="utf-8")
    relative_log = str(log.relative_to(tmp_path))
    argv = ["python", "driver", "supervise"]
    payload = capability_payload("candidate", attempt, relative_log, mode)
    payload["argv"] = argv
    monkeypatch.setattr(recovery, "run_filesystem_capability_gate", lambda *args: payload)
    monkeypatch.setattr(recovery, "ensure_recovery_directories", lambda: [])
    owner_sha, cap, cap_sha = recovery.prepare_attempt_evidence(
        "candidate", attempt, argv, relative_log, mode)
    rc.create_attempt(
        "candidate", attempt, argv, relative_log, mode,
        execution_owner_sha256=owner_sha,
        capability_path=str(cap.relative_to(tmp_path)), capability_sha256=cap_sha)
    return log


def test_incident_plan_review_and_original_inputs_are_still_bound() -> None:
    incident = rc.verify_incident_inputs()
    assert incident["config"]["plan_sha256"] == sha256_file(ROOT / incident["config"]["plan_path"])
    assert incident["config"]["plan_review_sha256"] == sha256_file(
        ROOT / incident["config"]["plan_review_path"])
    assert incident["collection"]["collection_outcome"] == "closed_all_stages"


def test_child_adapter_ast_is_exact_and_rejects_expansion(monkeypatch: pytest.MonkeyPatch) -> None:
    assert len(recovery.validate_child_source()) == 64
    monkeypatch.setattr(recovery, "CHILD_SOURCE", recovery.CHILD_SOURCE + "\nprint('forbidden')\n")
    with pytest.raises(RuntimeError, match="child"):
        recovery.validate_child_source(recovery.CHILD_SOURCE)


def test_k2_drift_contract_exhaustively_covers_all_registered_leaves() -> None:
    row = recovery.verify_k2_family_drift_contract()
    assert row["registered_leaves"] == 2004
    assert row["producer_rule_exact_leaves"] == 2004
    assert row["known_generic_drift_leaves"] == 2004
    assert row["known_difference"] == (
        "relative_structural_position_spurious_assigned_pos_leakage_entry")


def test_real_source_lineage_matches_scoring_and_partition_rows() -> None:
    expected, report = rc.resolve_expected_sources()
    assert set(expected) == {"calibration", "C1", "C2"}
    assert report["all_rows_match"] is True
    assert all(set(expected[role]) == set(rc.TASKS) for role in expected)
    assert all(report["roles"][role]["tasks"][task]["matching_rows"] > 0
               for role in expected for task in rc.TASKS)


@pytest.mark.parametrize(
    ("mutation", "message"),
    [
        ("negative_token", "invalid token index"),
        ("missing_variant", "missing partition variant"),
        ("source_mismatch", "activation/partition lineage mapping mismatch"),
    ],
)
def test_source_lineage_rejects_malformed_and_conflicting_rows(
        mutation: str, message: str, monkeypatch: pytest.MonkeyPatch) -> None:
    original = rc.strict_jsonl

    def altered(path: Path) -> list[dict[str, object]]:
        rows = original(path)
        text = str(path)
        if mutation in {"negative_token", "missing_variant"} and "analysis_rows" in text:
            rows = [dict(row) for row in rows]
            variant, _ = str(rows[0]["row_id"]).rsplit(":", 1)
            rows[0]["row_id"] = (
                f"{variant}:-1" if mutation == "negative_token"
                else "definitely_missing_variant:0")
        if mutation == "source_mismatch" and text.endswith("calibration.records.jsonl"):
            rows = [dict(row) for row in rows]
            for row in rows:
                row["source"] = "counterfeit_source"
        return rows

    monkeypatch.setattr(rc, "strict_jsonl", altered)
    with pytest.raises(RuntimeError, match=message):
        rc.resolve_expected_sources()


def test_isolated_recompute_uses_all_frozen_diagnostics(tmp_path: Path) -> None:
    expected, _ = rc.resolve_expected_sources()
    output, work = tmp_path / "output", tmp_path / "work"
    output.mkdir()
    result, report = recovery.run_isolated_recompute(output, expected, work)
    assert report.startswith("# Atlas completion diagnostic continuation results\n")
    assert result["execution"]["resource_accounting"]["continuation_actual_gpu_hours"] \
        == pytest.approx(17.021625942461668)
    assert all(len(row["scientifically_finite_draw_ids"]) == 414
               for row in result["k2"].values())
    assert len(result["stability"]["scientifically_finite_draw_ids"]) == 0
    assert all(row["counterfactual_gate_valid"] is False
               for row in result["specificity"].values())
    assert result["disposition"]["paper_branch"] == "unselected"
    assert result["disposition"]["training_warranted"] is False


def test_write_once_link_reconciles_applied_error_and_preserves_unapplied_temp(
        tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    parent = tmp_path / "evidence"; parent.mkdir()
    final = parent / "record.json"
    real_link = os.link

    def applied(source: Path, destination: Path) -> None:
        real_link(source, destination)
        raise OSError(errno.EIO, "ambiguous applied link")

    monkeypatch.setattr(rc.os, "link", applied)
    digest = rc.write_once_bytes(final, b"payload")
    assert digest == rc.sha256_bytes(b"payload") and final.read_bytes() == b"payload"

    second = parent / "unapplied.json"
    monkeypatch.setattr(rc.os, "link", lambda *_: (_ for _ in ()).throw(
        OSError(errno.EIO, "unapplied link")))
    with pytest.raises(OSError, match="unapplied"):
        rc.write_once_bytes(second, b"other")
    assert not second.exists()
    assert any(path.name.startswith(".unapplied.json.write_once.") for path in parent.iterdir())


def test_write_once_rejects_symlink_and_requires_inode_identity_after_ambiguous_link(
        tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    parent = tmp_path / "evidence"; parent.mkdir()
    external = tmp_path / "external"; external.write_bytes(b"payload")
    final = parent / "record"; final.symlink_to(external)
    with pytest.raises(RuntimeError, match="malformed"):
        rc.write_once_bytes(final, b"payload")

    real_link = os.link
    ambiguous = parent / "ambiguous"

    def different_inode_then_error(source: Path, destination: Path) -> None:
        destination.write_bytes(source.read_bytes())
        raise OSError(errno.EIO, "ambiguous but not the linked inode")

    monkeypatch.setattr(rc.os, "link", different_inode_then_error)
    with pytest.raises(RuntimeError, match="inode identity"):
        rc.write_once_bytes(ambiguous, b"same bytes")
    assert ambiguous.read_bytes() == b"same bytes"
    monkeypatch.setattr(rc.os, "link", real_link)


def test_write_once_concurrent_identical_publish_has_one_inode_winner(tmp_path: Path) -> None:
    parent = tmp_path / "evidence"; parent.mkdir()
    script = textwrap.dedent("""
        import pathlib,sys
        sys.path.insert(0, sys.argv[1])
        import msa_completion_summary_recovery_common as rc
        rc.write_once_bytes(pathlib.Path(sys.argv[2]), b'identical')
    """)
    final = parent / "record"
    children = [subprocess.Popen([
        sys.executable, "-c", script, str(ROOT / "scripts"), str(final)]) for _ in range(2)]
    codes = [child.wait(timeout=20) for child in children]
    assert codes == [0, 0]
    facts = rc.regular_file_facts(final)
    assert facts["sha256"] == rc.sha256_bytes(b"identical")
    assert facts["regular"] is True


@pytest.mark.parametrize("boundary", ["temporary", "final", "parent"])
def test_write_once_fsync_failures_never_consume_unconfirmed_evidence(
        boundary: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    parent = tmp_path / "evidence"; parent.mkdir()
    final = parent / f"{boundary}.json"
    real_os_fsync = os.fsync
    real_final_fsync = rc._fsync_regular_file
    real_parent_fsync = rc.fsync_directory
    failed = {"done": False}
    if boundary == "temporary":
        def fail_temp(fd: int) -> None:
            if not failed["done"]:
                failed["done"] = True
                raise OSError(errno.EIO, "temporary fsync")
            real_os_fsync(fd)
        monkeypatch.setattr(rc.os, "fsync", fail_temp)
    elif boundary == "final":
        def fail_final(path: Path):
            if path == final and not failed["done"]:
                failed["done"] = True
                raise OSError(errno.EIO, "final fsync")
            return real_final_fsync(path)
        monkeypatch.setattr(rc, "_fsync_regular_file", fail_final)
    else:
        def fail_parent(path: Path) -> None:
            if path == parent and not failed["done"]:
                failed["done"] = True
                raise OSError(errno.EIO, "parent fsync")
            real_parent_fsync(path)
        monkeypatch.setattr(rc, "fsync_directory", fail_parent)
    with pytest.raises(OSError, match="fsync"):
        rc.write_once_bytes(final, b"payload")
    if boundary == "temporary":
        assert not final.exists()
    else:
        assert final.read_bytes() == b"payload"
    monkeypatch.setattr(rc.os, "fsync", real_os_fsync)
    monkeypatch.setattr(rc, "_fsync_regular_file", real_final_fsync)
    monkeypatch.setattr(rc, "fsync_directory", real_parent_fsync)
    assert rc.write_once_bytes(final, b"payload") == rc.sha256_bytes(b"payload")


def test_write_once_rejects_replacement_during_final_fsync(
        tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    parent = tmp_path / "evidence"; parent.mkdir()
    final = parent / "record"
    real_fsync = rc._fsync_regular_file
    replaced = {"done": False}

    def replace(path: Path):
        if path == final and not replaced["done"]:
            replaced["done"] = True
            path.unlink()
            path.write_bytes(b"CORRUPT")
        return real_fsync(path)

    monkeypatch.setattr(rc, "_fsync_regular_file", replace)
    with pytest.raises(RuntimeError, match="changed after file fsync"):
        rc.write_once_bytes(final, b"payload")
    assert final.read_bytes() == b"CORRUPT"


def test_recovery_directory_bootstrap_retries_every_ancestry_fsync_boundary(
        tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Every bootstrap fsync may fail without creating consumable evidence."""

    real_fsync = rc.fsync_directory
    expected_calls = 4 * (1 + len(rc.RECOVERY_DIRECTORIES))
    for fail_at in range(1, expected_calls + 1):
        case = tmp_path / f"bootstrap-{fail_at:03d}"
        case.mkdir()
        run = case / "recovery"
        monkeypatch.setattr(rc, "recovery_run_root", lambda run=run: run)
        observed = {"count": 0}

        def injected(path: Path) -> None:
            observed["count"] += 1
            if observed["count"] == fail_at:
                raise OSError(errno.EIO, f"bootstrap fsync {fail_at}")
            real_fsync(path)

        monkeypatch.setattr(rc, "fsync_directory", injected)
        with pytest.raises(OSError, match=f"bootstrap fsync {fail_at}"):
            rc.ensure_recovery_directories()
        assert not run.exists() or not any(path.is_file() for path in run.rglob("*"))

        monkeypatch.setattr(rc, "fsync_directory", real_fsync)
        paths = rc.ensure_recovery_directories()
        assert len(paths) == 1 + len(rc.RECOVERY_DIRECTORIES)
        assert all(path.is_dir() and not path.is_symlink() for path in paths)


@pytest.mark.parametrize("boundary", ["staging_directory", "staging_parent"])
def test_staging_directory_creation_fsync_failures_precede_all_evidence(
        boundary: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    run = tmp_path / "recovery"
    for relative in rc.RECOVERY_DIRECTORIES:
        (run / relative).mkdir(parents=True, exist_ok=True)
    stage = tmp_path / f".{boundary}.staging"
    real_fsync = recovery.fsync_directory
    failed = {"done": False}

    def injected(path: Path) -> None:
        target = stage if boundary == "staging_directory" else stage.parent
        if path == target and not failed["done"]:
            failed["done"] = True
            raise OSError(errno.EIO, f"injected {boundary} fsync")
        real_fsync(path)

    monkeypatch.setattr(recovery, "fsync_directory", injected)
    with pytest.raises(OSError, match=f"injected {boundary}"):
        recovery._create_staging_directory(stage)
    assert stage.is_dir()
    assert not any(path.is_file() for path in (run / "job_state").rglob("*"))
    assert not any(path.is_file() for path in (run / "job_manifests").rglob("*"))


def test_append_only_state_rejects_gap_tamper_and_prefix_regression(
        tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    with locked_fixture(tmp_path, monkeypatch):
        destination, stage = tmp_path / "candidate", tmp_path / "stage"
        stage.mkdir()
        state_building(destination, stage)
        head = rc.read_state_chain("candidate")
        assert head and head["generation"] == 1
        first = rc.state_directory("candidate") / "g000001.json"
        row = json.loads(first.read_text())
        row["phase"] = ""
        first.write_text(json.dumps(row) + "\n")
        with pytest.raises(RuntimeError, match="journal mismatch"):
            rc.read_state_chain("candidate")

    # A missing generation is detected independently of JSON contents.
    with locked_fixture(tmp_path / "gap", monkeypatch):
        destination, stage = tmp_path / "gap/candidate", tmp_path / "gap/stage"
        stage.mkdir(parents=True)
        state_building(destination, stage)
        directory = rc.state_directory("candidate")
        (directory / "g000001.json").rename(directory / "g000002.json")
        with pytest.raises(RuntimeError, match="gap or fork"):
            rc.read_state_chain("candidate")


def test_state_phase_prefix_and_attempt_transition_fail_before_publication(
        tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    with locked_fixture(tmp_path, monkeypatch):
        destination, stage = tmp_path / "candidate", candidate_stage(tmp_path)
        state_building(destination, stage)
        inventory = recovery._ordered_publication_inventory("candidate", stage)
        binding = recovery._state_binding(
            stage, destination, {"bundle_sha256": "1" * 64}, None, ATTEMPT_A, inventory)
        rc.append_state("candidate", ATTEMPT_A, binding)
        directory = rc.state_directory("candidate")
        with pytest.raises(RuntimeError, match="phase/prefix"):
            rc.append_state("candidate", ATTEMPT_A, {
                **binding, "phase": "files_publishing",
                "root_reservation_attempted": True, "root_reservation_confirmed": True,
                "destination_st_dev": 1, "destination_st_ino": 1,
                "published_files": [],
            })
        assert not (directory / "g000003.json").exists()
        with pytest.raises(RuntimeError, match="new recovery attempt"):
            rc.append_state("candidate", ATTEMPT_B, {
                **binding, "phase": "root_reserved",
                "root_reservation_attempted": True, "root_reservation_confirmed": True,
                "destination_st_dev": 1, "destination_st_ino": 1,
            }, claim=True)
        assert not (directory / "g000003.json").exists()
        owned = {**binding, "phase": "root_reserved",
                 "root_reservation_attempted": True, "root_reservation_confirmed": True,
                 "destination_st_dev": 1, "destination_st_ino": 1}
        rc.append_state("candidate", ATTEMPT_A, owned)
        rc.append_state("candidate", ATTEMPT_A, {
            **owned, "phase": "files_publishing",
            "published_files": [inventory[0]["path"]],
        })
        with pytest.raises(RuntimeError, match="progress regressed"):
            rc.append_state("candidate", ATTEMPT_A, {
                **owned, "phase": "reconciling", "published_files": [],
            })
        assert not (directory / "g000005.json").exists()


def test_state_journal_rejects_symlink_substitution_even_for_identical_bytes(
        tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    with locked_fixture(tmp_path, monkeypatch):
        destination, stage = tmp_path / "candidate", tmp_path / "stage"
        stage.mkdir()
        state_building(destination, stage)
        generation = rc.state_directory("candidate") / "g000001.json"
        external = tmp_path / "external-state.json"
        external.write_bytes(generation.read_bytes())
        generation.unlink()
        generation.symlink_to(external)
        with pytest.raises((OSError, RuntimeError)):
            rc.read_state_chain("candidate")


def test_reserved_root_success_is_terminal_last_and_parent_fsynced(
        tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    with locked_fixture(tmp_path, monkeypatch):
        destination = tmp_path / "candidate"
        stage = candidate_stage(tmp_path)
        monkeypatch.setattr(recovery, "_validate_for_job", lambda *_: {})
        monkeypatch.setenv("MSAE_RECOVERY_ATTEMPT_ID", ATTEMPT_A)
        state_building(destination, stage)
        recovery._publish_stage(
            "candidate", stage, destination, {"bundle_sha256": "1" * 64}, None)
        head = rc.read_state_chain("candidate")
        assert head and head["phase"] == "parent_fsync_complete"
        assert head["root_reservation_attempted"] is True
        assert head["root_reservation_confirmed"] is True
        assert head["staging_inventory"] == sorted(
            head["staging_inventory"], key=lambda item: item["path"])
        assert head["publication_inventory"][-1]["path"] == "CANDIDATE_COMPLETE.json"
        assert head["published_files"][-1] == "CANDIDATE_COMPLETE.json"
        assert {path.name for path in destination.iterdir()} == set(head["published_files"])
        assert all(os.stat(stage / name).st_ino == os.stat(destination / name).st_ino
                   for name in head["published_files"])


def test_preexisting_empty_root_is_permanent_collision(
        tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    with locked_fixture(tmp_path, monkeypatch):
        destination = tmp_path / "candidate"; destination.mkdir()
        stage = candidate_stage(tmp_path)
        monkeypatch.setattr(recovery, "_validate_for_job", lambda *_: {})
        monkeypatch.setenv("MSAE_RECOVERY_ATTEMPT_ID", ATTEMPT_A)
        state_building(destination, stage)
        with pytest.raises(FileExistsError, match="unowned"):
            recovery._publish_stage(
                "candidate", stage, destination, {"bundle_sha256": "1" * 64}, None)
        head = rc.read_state_chain("candidate")
        assert head and head["root_reservation_attempted"] is True
        assert head["root_reservation_confirmed"] is False
        assert list(destination.iterdir()) == []


@pytest.mark.parametrize("applied", [False, True])
def test_ambiguous_mkdir_never_confirms_root_ownership(
        applied: bool, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    with locked_fixture(tmp_path, monkeypatch):
        destination, stage = tmp_path / "candidate", candidate_stage(tmp_path)
        monkeypatch.setattr(recovery, "_validate_for_job", lambda *_: {})
        monkeypatch.setenv("MSAE_RECOVERY_ATTEMPT_ID", ATTEMPT_A)
        state_building(destination, stage)

        def ambiguous(path: Path) -> None:
            if applied:
                os.mkdir(path, 0o700)
            raise OSError(errno.EIO, "ambiguous mkdir")

        monkeypatch.setattr(recovery, "_reserve_result_root", ambiguous)
        with pytest.raises(OSError, match="ambiguous mkdir"):
            recovery._publish_stage(
                "candidate", stage, destination, {"bundle_sha256": "1" * 64}, None)
        head = rc.read_state_chain("candidate")
        assert head and head["phase"] == "reconciling"
        assert head["root_reservation_attempted"] is True
        assert head["root_reservation_confirmed"] is False
        assert destination.exists() is applied


def test_root_reservation_rejects_directory_inode_replacement_before_witness(
        tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    with locked_fixture(tmp_path, monkeypatch):
        destination, stage = tmp_path / "candidate", candidate_stage(tmp_path)
        monkeypatch.setattr(recovery, "_validate_for_job", lambda *_: {})
        monkeypatch.setenv("MSAE_RECOVERY_ATTEMPT_ID", ATTEMPT_A)
        state_building(destination, stage)
        real_fsync = recovery.fsync_directory
        swapped = {"done": False}

        def swap_before_parent_witness(path: Path) -> None:
            if path == destination.parent and destination.exists() and not swapped["done"]:
                swapped["done"] = True
                destination.rename(tmp_path / "created-but-unwitnessed")
                destination.mkdir()
            real_fsync(path)

        monkeypatch.setattr(recovery, "fsync_directory", swap_before_parent_witness)
        with pytest.raises(RuntimeError, match="owned directory inode"):
            recovery._publish_stage(
                "candidate", stage, destination, {"bundle_sha256": "1" * 64}, None)
        head = rc.read_state_chain("candidate")
        assert head and head["phase"] == "reconciling"
        assert head["root_reservation_confirmed"] is False
        assert head["destination_st_dev"] is None and head["destination_st_ino"] is None


@pytest.mark.parametrize("applied", [False, True])
def test_ambiguous_file_link_advances_only_for_exact_same_inode(
        applied: bool, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    with locked_fixture(tmp_path, monkeypatch):
        destination, stage = tmp_path / "candidate", candidate_stage(tmp_path)
        monkeypatch.setattr(recovery, "_validate_for_job", lambda *_: {})
        monkeypatch.setenv("MSAE_RECOVERY_ATTEMPT_ID", ATTEMPT_A)
        state_building(destination, stage)
        real_link = os.link

        def ambiguous(source: Path, final: Path, destination_fd: int | None = None) -> None:
            if applied:
                if destination_fd is None:
                    real_link(source, final)
                else:
                    real_link(source, final.name, dst_dir_fd=destination_fd)
            raise OSError(errno.EIO, "ambiguous link")

        monkeypatch.setattr(recovery, "_link_result_file", ambiguous)
        if applied:
            recovery._publish_stage(
                "candidate", stage, destination, {"bundle_sha256": "1" * 64}, None)
            head = rc.read_state_chain("candidate")
            assert head and head["phase"] == "parent_fsync_complete"
            assert all(
                os.stat(stage / name).st_ino == os.stat(destination / name).st_ino
                for name in head["published_files"])
        else:
            with pytest.raises(OSError, match="ambiguous link"):
                recovery._publish_stage(
                    "candidate", stage, destination, {"bundle_sha256": "1" * 64}, None)
            head = rc.read_state_chain("candidate")
            assert head and head["phase"] == "root_reserved"
            assert head["published_files"] == []
            assert list(destination.iterdir()) == []


@pytest.mark.parametrize("mutation", ["removed", "replaced"])
def test_post_link_stage_disappearance_or_replacement_is_rejected(
        mutation: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    with locked_fixture(tmp_path, monkeypatch):
        destination, stage = tmp_path / "candidate", candidate_stage(tmp_path)
        monkeypatch.setattr(recovery, "_validate_for_job", lambda *_: {})
        monkeypatch.setenv("MSAE_RECOVERY_ATTEMPT_ID", ATTEMPT_A)
        state_building(destination, stage)
        real_link = os.link
        changed = {"done": False}

        def mutate_source(source: Path, final: Path, destination_fd: int | None = None) -> None:
            if destination_fd is None:
                real_link(source, final)
            else:
                real_link(source, final.name, dst_dir_fd=destination_fd)
            if not changed["done"]:
                changed["done"] = True
                source.unlink()
                if mutation == "replaced":
                    source.write_bytes(final.read_bytes())

        monkeypatch.setattr(recovery, "_link_result_file", mutate_source)
        with pytest.raises((OSError, RuntimeError)):
            recovery._publish_stage(
                "candidate", stage, destination, {"bundle_sha256": "1" * 64}, None)
        head = rc.read_state_chain("candidate")
        assert head and head["published_files"] == []


@pytest.mark.parametrize(
    ("boundary", "expected_phase"),
    [("root", "reconciling"), ("destination", "terminal_published"),
     ("parent", "destination_fsync_complete")],
)
def test_root_destination_and_parent_fsync_failures_do_not_advance(
        boundary: str, expected_phase: str, tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch) -> None:
    with locked_fixture(tmp_path, monkeypatch):
        destination, stage = tmp_path / "candidate", candidate_stage(tmp_path)
        monkeypatch.setattr(recovery, "_validate_for_job", lambda *_: {})
        monkeypatch.setenv("MSAE_RECOVERY_ATTEMPT_ID", ATTEMPT_A)
        state_building(destination, stage)
        real_fsync_directory = recovery.fsync_directory

        def injected(path: Path) -> None:
            head = rc.read_state_chain("candidate")
            phase = None if head is None else head["phase"]
            should_fail = (
                boundary == "root" and path == destination and phase == "ready_to_publish"
                or boundary == "destination" and path == destination
                and phase == "terminal_published"
                or boundary == "parent" and path == destination.parent
                and phase == "destination_fsync_complete"
            )
            if should_fail:
                raise OSError(errno.EIO, f"injected {boundary} fsync")
            real_fsync_directory(path)

        monkeypatch.setattr(recovery, "fsync_directory", injected)
        with pytest.raises(OSError, match=f"injected {boundary}"):
            recovery._publish_stage(
                "candidate", stage, destination, {"bundle_sha256": "1" * 64}, None)
        head = rc.read_state_chain("candidate")
        assert head and head["phase"] == expected_phase


def test_partial_owned_prefix_reconciles_but_fsync_failure_does_not_advance(
        tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    with locked_fixture(tmp_path, monkeypatch):
        destination = tmp_path / "candidate"
        stage = candidate_stage(tmp_path)
        monkeypatch.setattr(recovery, "_validate_for_job", lambda *_: {})
        monkeypatch.setattr(recovery, "candidate_root", lambda: destination)
        monkeypatch.setattr(recovery, "verify_initial_freeze", lambda: {"bundle_sha256": "1" * 64})
        monkeypatch.setenv("MSAE_RECOVERY_ATTEMPT_ID", ATTEMPT_A)
        state_building(destination, stage)
        real_fsync = recovery.fsync_file
        failed = {"done": False}

        def fail_second_final(path: Path) -> None:
            if path.parent == destination and path.name == "diagnostic_results.md" and not failed["done"]:
                failed["done"] = True
                raise OSError(errno.EIO, "injected final fsync")
            real_fsync(path)

        monkeypatch.setattr(recovery, "fsync_file", fail_second_final)
        with pytest.raises(OSError, match="injected"):
            recovery._publish_stage(
                "candidate", stage, destination, {"bundle_sha256": "1" * 64}, None)
        head = rc.read_state_chain("candidate")
        assert head and head["published_files"] == ["diagnostic_results.json"]
        assert {path.name for path in destination.iterdir()} == {
            "diagnostic_results.json", "diagnostic_results.md"}

        monkeypatch.setattr(recovery, "fsync_file", real_fsync)
        monkeypatch.setenv("MSAE_RECOVERY_ATTEMPT_ID", ATTEMPT_B)
        row = recovery.reconcile("candidate")
        assert row["reconciled"] == "candidate"
        head = rc.read_state_chain("candidate")
        assert head and head["phase"] == "parent_fsync_complete"
        assert head["published_files"][-1] == "CANDIDATE_COMPLETE.json"


def test_terminal_before_content_nonprefix_is_rejected(
        tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    with locked_fixture(tmp_path, monkeypatch):
        destination = tmp_path / "candidate"; destination.mkdir()
        stage = candidate_stage(tmp_path)
        monkeypatch.setattr(recovery, "_validate_for_job", lambda *_: {})
        monkeypatch.setenv("MSAE_RECOVERY_ATTEMPT_ID", ATTEMPT_A)
        state_building(destination, stage)
        inventory = recovery._ordered_publication_inventory("candidate", stage)
        binding = recovery._state_binding(
            stage, destination, {"bundle_sha256": "1" * 64}, None, ATTEMPT_A, inventory)
        rc.append_state("candidate", ATTEMPT_A, binding)
        owned = {**binding, "root_reservation_attempted": True,
                 "root_reservation_confirmed": True,
                 "destination_st_dev": destination.stat().st_dev,
                 "destination_st_ino": destination.stat().st_ino}
        rc.append_state("candidate", ATTEMPT_A, {**owned, "phase": "root_reserved"})
        os.link(stage / "CANDIDATE_COMPLETE.json", destination / "CANDIDATE_COMPLETE.json")
        with pytest.raises(FileExistsError, match="ordered prefix"):
            recovery._continue_reserved_publication(
                "candidate", ATTEMPT_A, stage, destination, owned)


def test_capability_only_crash_gets_manifest_absent_orphan_terminal(
        tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    with locked_fixture(tmp_path, monkeypatch) as run:
        log = run / "logs" / f"candidate.{ATTEMPT_A}.log"; log.write_text("pre-manifest\n")
        relative_log = str(log.relative_to(tmp_path))
        cap = rc.capability_path("candidate", ATTEMPT_A)
        rc.write_once_json(cap, capability_payload("candidate", ATTEMPT_A, relative_log))
        created = rc.close_orphan_attempts("candidate")
        assert len(created) == 1
        terminal = rc._validate_attempt_terminal(created[0], job="candidate")
        assert terminal["manifest_state"] == "absent"
        assert terminal["manifest_sha256"] is None
        assert terminal["closure_reason"] == "supervisor_unobservable_exit_before_manifest"
        assert terminal["outcome"] == "technical_failure"
        assert not rc.success_path("candidate").exists()


def test_attempt_manifest_and_terminal_bind_same_capability_record(
        tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    with locked_fixture(tmp_path, monkeypatch) as run:
        destination = tmp_path / "candidate"
        monkeypatch.setattr(rc, "candidate_root", lambda: destination)
        monkeypatch.setattr(recovery, "candidate_root", lambda: destination)
        monkeypatch.setattr(recovery, "recovery_run_root", lambda: run)
        log = run / "logs" / f"candidate.{ATTEMPT_A}.log"; log.write_text("attempt\n")
        relative_log = str(log.relative_to(tmp_path))
        argv = ["python", "driver", "candidate"]
        payload = capability_payload("candidate", ATTEMPT_A, relative_log)
        monkeypatch.setattr(
            recovery, "run_filesystem_capability_gate", lambda *args: payload)
        monkeypatch.setattr(recovery, "ensure_recovery_directories", lambda: [])
        owner_sha, cap, cap_sha = recovery.prepare_attempt_evidence(
            "candidate", ATTEMPT_A, argv, relative_log, "run")
        manifest = rc.create_attempt(
            "candidate", ATTEMPT_A, argv, relative_log, "run",
            execution_owner_sha256=owner_sha,
            capability_path=str(cap.relative_to(tmp_path)), capability_sha256=cap_sha)
        terminal = rc.close_attempt("candidate", ATTEMPT_A, 1)
        assert terminal["manifest_state"] == "present"
        assert terminal["manifest_sha256"] == sha256_file(manifest)
        assert terminal["filesystem_capability_sha256"] == sha256_file(cap)
        assert terminal["outcome"] == "technical_failure"


def test_success_closure_rejects_any_extra_attempt_state_snapshot(
        tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    with locked_fixture(tmp_path, monkeypatch) as run:
        destination, stage = tmp_path / "candidate", candidate_stage(tmp_path)
        install_attempt_evidence(run, tmp_path, monkeypatch)
        monkeypatch.setattr(recovery, "_validate_for_job", lambda *_: {})
        monkeypatch.setattr(rc, "validate_candidate", lambda *_args, **_kwargs: {})
        monkeypatch.setenv("MSAE_RECOVERY_ATTEMPT_ID", ATTEMPT_A)
        state_building(destination, stage)
        recovery._publish_stage(
            "candidate", stage, destination, {"bundle_sha256": "1" * 64}, None)
        terminal = rc.close_attempt("candidate", ATTEMPT_A, 0)
        assert terminal["outcome"] == "success"
        assert rc.validate_success_closure("candidate", destination)["job"] == "candidate"

        head = rc.read_state_chain("candidate")
        assert head is not None
        extra = run / "job_state" / f"candidate.{ATTEMPT_B}.json"
        rc.write_once_json(extra, {
            "schema_version": "atlas_completion_summary_recovery_attempt_state_snapshot_v1",
            "job": "candidate", "attempt_id": ATTEMPT_B,
            "state_status": "state_absent_for_attempt",
            "state_path": None, "state_sha256": None, "state_generation": None,
            "observed_head_path": head["_path"], "observed_head_sha256": head["_sha256"],
            "observed_head_generation": head["generation"],
            "created_utc": "2026-08-02T12:00:01+00:00",
        })
        with pytest.raises(RuntimeError, match="valid durable success closure"):
            rc.validate_success_closure("candidate", destination)


@pytest.mark.parametrize("record", ["snapshot", "terminal", "success_closure"])
@pytest.mark.parametrize(
    "boundary", ["temporary_fsync", "link_applied", "link_unapplied",
                 "final_file_fsync", "parent_fsync"])
def test_attempt_evidence_persistence_failures_retry_without_rewriting_history(
        record: str, boundary: str, tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch) -> None:
    with locked_fixture(tmp_path, monkeypatch) as run:
        destination, stage = tmp_path / "candidate", candidate_stage(tmp_path)
        install_attempt_evidence(run, tmp_path, monkeypatch)
        monkeypatch.setattr(recovery, "_validate_for_job", lambda *_: {})
        monkeypatch.setattr(rc, "validate_candidate", lambda *_args, **_kwargs: {})
        monkeypatch.setenv("MSAE_RECOVERY_ATTEMPT_ID", ATTEMPT_A)
        state_building(destination, stage)
        recovery._publish_stage(
            "candidate", stage, destination, {"bundle_sha256": "1" * 64}, None)

        targets = {
            "snapshot": run / "job_state" / f"candidate.{ATTEMPT_A}.json",
            "terminal": run / "job_manifests" / f"candidate.{ATTEMPT_A}.terminal.json",
            "success_closure": run / "job_manifests" / "candidate.success.json",
        }
        target = targets[record]
        real_os_fsync = os.fsync
        real_link = os.link
        real_file_fsync = rc._fsync_regular_file
        real_parent_fsync = rc.fsync_directory
        failed = {"done": False}

        if boundary == "temporary_fsync":
            def fail_temporary(fd: int) -> None:
                try:
                    opened = Path(os.readlink(f"/proc/self/fd/{fd}"))
                except OSError:
                    opened = Path()
                if (opened.name.startswith(f".{target.name}.write_once.")
                        and not failed["done"]):
                    failed["done"] = True
                    raise OSError(errno.EIO, f"injected {record} temporary_fsync")
                real_os_fsync(fd)
            monkeypatch.setattr(rc.os, "fsync", fail_temporary)
        elif boundary in {"link_applied", "link_unapplied"}:
            def fail_link(source: Path, destination: Path, *args, **kwargs) -> None:
                if Path(destination) == target and not failed["done"]:
                    failed["done"] = True
                    if boundary == "link_applied":
                        real_link(source, destination, *args, **kwargs)
                    raise OSError(errno.EIO, f"injected {record} {boundary}")
                real_link(source, destination, *args, **kwargs)
            monkeypatch.setattr(rc.os, "link", fail_link)
        elif boundary == "final_file_fsync":
            def fail_file(path: Path):
                if path == target and not failed["done"]:
                    failed["done"] = True
                    raise OSError(errno.EIO, f"injected {record} final_file_fsync")
                return real_file_fsync(path)
            monkeypatch.setattr(rc, "_fsync_regular_file", fail_file)
        else:
            def fail_parent(path: Path) -> None:
                if path == target.parent and target.exists() and not failed["done"]:
                    failed["done"] = True
                    raise OSError(errno.EIO, f"injected {record} parent_fsync")
                real_parent_fsync(path)
            monkeypatch.setattr(rc, "fsync_directory", fail_parent)

        if boundary == "link_applied":
            terminal = rc.close_attempt("candidate", ATTEMPT_A, 0)
            assert terminal["outcome"] == "success"
        else:
            with pytest.raises(OSError, match=f"injected {record} {boundary}"):
                rc.close_attempt("candidate", ATTEMPT_A, 0)
            assert target.exists() is (boundary in {"final_file_fsync", "parent_fsync"})

        monkeypatch.setattr(rc.os, "fsync", real_os_fsync)
        monkeypatch.setattr(rc.os, "link", real_link)
        monkeypatch.setattr(rc, "_fsync_regular_file", real_file_fsync)
        monkeypatch.setattr(rc, "fsync_directory", real_parent_fsync)
        terminal = rc.close_attempt("candidate", ATTEMPT_A, 0)
        assert terminal["outcome"] == "success"
        closure = rc.validate_success_closure("candidate", destination)
        assert closure["successful_attempt_terminal"].endswith(
            f"candidate.{ATTEMPT_A}.terminal.json")
        assert len(list((run / "job_state").glob("candidate.*.json"))) == 1
        assert len(list((run / "job_manifests").glob("candidate.*.terminal.json"))) == 1


def test_capability_or_terminal_without_matching_universe_is_rejected(
        tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    with locked_fixture(tmp_path, monkeypatch) as run:
        stray = run / "job_manifests" / f"candidate.{ATTEMPT_A}.manifest.json"
        stray.write_text("{}\n")
        with pytest.raises(RuntimeError, match="without its capability"):
            rc.close_orphan_attempts("candidate")


def test_capability_validator_rejects_mount_and_exact_evidence_tamper(
        tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    with locked_fixture(tmp_path, monkeypatch) as run:
        log = run / "logs/test.log"; log.write_text("test\n", encoding="utf-8")
        relative_log = str(log.relative_to(tmp_path))
        for index, mutation in enumerate(["mount", "inode", "marker"]):
            attempt = f"20260802T12000{index}Z_1000{index}_{index:08x}"
            payload = capability_payload("candidate", attempt, relative_log)
            if mutation == "mount":
                del payload["mount"]["mount_id"]  # type: ignore[index]
            elif mutation == "inode":
                payload["outcomes"]["file"]["success"]["same_inode"] = False  # type: ignore[index]
            else:
                payload["outcomes"]["directory"]["eexist_preserved"][
                    "marker_sha256_after"] = "2" * 64  # type: ignore[index]
            path = run / "filesystem_capabilities" / f"candidate.{attempt}.json"
            path.write_text(json.dumps(payload) + "\n", encoding="utf-8")
            with pytest.raises(RuntimeError, match="capability|mount|evidence"):
                rc._validate_capability(path, job="candidate", attempt_id=attempt)


def test_actual_nfs_capability_gate_includes_lock_link_mkdir_and_fsync(
        monkeypatch: pytest.MonkeyPatch) -> None:
    rc.ensure_recovery_directories()
    with rc.supervisor_job_lock("candidate"):
        row = recovery.run_filesystem_capability_gate(
            "candidate", ATTEMPT_A, ["python", "driver", "candidate"],
            "pilot_runs/20260802_atlas_completion_summary_recovery_v1/logs/test.log", "run")
    assert row["all_passed"] is True
    assert row["outcomes"]["job_lock"] == {
        "separate_descriptor_lost": True, "guarded_manifest_marker_created": False}
    assert row["outcomes"]["file"]["two_process"]["exit_codes"] == [0, 17]
    assert row["outcomes"]["file"]["two_process"]["target_same_inode_as_winner"] is True
    assert row["outcomes"]["directory"]["two_process"]["exit_codes"] == [0, 17]


def test_live_nfs_ambiguous_link_and_mkdir_are_observed_fail_closed(
        monkeypatch: pytest.MonkeyPatch) -> None:
    parent = rc.canonical_root().parent
    mount = rc.deployment_mount()
    assert str(mount["filesystem_type"]).startswith("nfs")
    root = parent / f".summary_recovery_faulttest.{uuid.uuid4().hex}"
    root.mkdir(mode=0o700)
    rc.fsync_directory(root); rc.fsync_directory(parent)
    real_link = os.link
    real_reserve = recovery._reserve_result_root
    try:
        applied = root / "applied"

        def applied_link(source: Path, destination: Path) -> None:
            real_link(source, destination)
            raise OSError(errno.EIO, "live ambiguous applied link")

        monkeypatch.setattr(rc.os, "link", applied_link)
        rc.write_once_bytes(applied, b"live-nfs")
        assert applied.read_bytes() == b"live-nfs"

        monkeypatch.setattr(rc.os, "link", lambda *_args, **_kwargs: (_ for _ in ()).throw(
            OSError(errno.EIO, "live ambiguous unapplied link")))
        unapplied = root / "unapplied"
        with pytest.raises(OSError, match="unapplied"):
            rc.write_once_bytes(unapplied, b"live-nfs")
        assert not unapplied.exists()
        monkeypatch.setattr(rc.os, "link", real_link)

        def applied_mkdir(path: Path) -> None:
            os.mkdir(path, 0o700)
            raise OSError(errno.EIO, "live ambiguous applied mkdir")

        monkeypatch.setattr(recovery, "_reserve_result_root", applied_mkdir)
        applied_directory = root / "applied-directory"
        with pytest.raises(OSError, match="applied mkdir"):
            recovery._reserve_root_with_witness(applied_directory)
        assert applied_directory.is_dir()

        monkeypatch.setattr(recovery, "_reserve_result_root", lambda _path: (_ for _ in ()).throw(
            OSError(errno.EIO, "live ambiguous unapplied mkdir")))
        unapplied_directory = root / "unapplied-directory"
        with pytest.raises(OSError, match="unapplied mkdir"):
            recovery._reserve_root_with_witness(unapplied_directory)
        assert not unapplied_directory.exists()
    finally:
        monkeypatch.setattr(rc.os, "link", real_link)
        monkeypatch.setattr(recovery, "_reserve_result_root", real_reserve)
        for _ in range(50):
            try:
                shutil.rmtree(root)
                break
            except OSError as exc:
                if exc.errno not in {errno.ENOTEMPTY, errno.EBUSY}:
                    raise
                time.sleep(0.1)
        assert not root.exists()
        rc.fsync_directory(parent)


def test_supervisor_uses_one_process_lifetime_guard_for_prepare_run_and_close(
        tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    run = tmp_path / "recovery"
    monkeypatch.setattr(rc, "ROOT", tmp_path)
    monkeypatch.setattr(recovery, "ROOT", tmp_path)
    monkeypatch.setattr(rc, "recovery_run_root", lambda: run)
    monkeypatch.setattr(recovery, "recovery_run_root", lambda: run)
    monkeypatch.setattr(rc, "candidate_root", lambda: tmp_path / "candidate")
    monkeypatch.setattr(recovery, "candidate_root", lambda: tmp_path / "candidate")
    monkeypatch.setattr(rc, "deployment_mount", lambda: dict(FAKE_MOUNT))
    monkeypatch.setattr(rc, "verify_initial_freeze", lambda: {"bundle_sha256": "1" * 64})
    monkeypatch.setattr(rc, "_applicable_freezes", lambda _job: ("1" * 64, None))
    log = "recovery/logs/candidate.supervisor.log"
    closure = "recovery/logs/candidate.supervisor.closure.log"
    payload = capability_payload("candidate", ATTEMPT_A, log)
    payload["argv"] = ["python", "driver", "supervise"]
    monkeypatch.setattr(recovery, "run_filesystem_capability_gate", lambda *args: payload)
    observed: list[str] = []

    def science() -> dict[str, object]:
        rc.require_job_lock("candidate")
        observed.append("science")
        return {"ok": True}

    def close(job: str, attempt: str, exit_code: int) -> dict[str, object]:
        rc.require_job_lock(job)
        observed.append("close")
        assert attempt == ATTEMPT_A and exit_code == 0
        return {"outcome": "success"}

    monkeypatch.setattr(recovery, "run_candidate", science)
    monkeypatch.setattr(recovery, "close_attempt", close)
    output = recovery.supervise(
        "candidate", ATTEMPT_A, "run", log, closure,
        ["python", "driver", "supervise"])
    assert output == {"ok": True}
    assert observed == ["science", "close"]
    assert rc._SUPERVISOR_JOB is None


def test_two_real_supervisor_processes_have_exactly_one_lock_winner(tmp_path: Path) -> None:
    run = tmp_path / "recovery"
    for relative in rc.RECOVERY_DIRECTORIES:
        (run / relative).mkdir(parents=True, exist_ok=True)
    barrier = tmp_path / "barrier"
    winner = tmp_path / "winner"
    script = textwrap.dedent("""
        import pathlib,sys,time
        sys.path.insert(0, sys.argv[1])
        import msa_completion_summary_recovery_common as rc
        root,run,barrier,winner=map(pathlib.Path,sys.argv[2:])
        rc.ROOT=root
        rc.recovery_run_root=lambda: run
        deadline=time.monotonic()+10
        while not barrier.exists():
            if time.monotonic()>deadline: raise SystemExit(98)
            time.sleep(0.001)
        try:
            with rc.supervisor_job_lock('candidate'):
                with winner.open('x',encoding='utf-8') as handle: handle.write('winner\\n')
                time.sleep(0.5)
        except (RuntimeError,FileExistsError):
            raise SystemExit(75)
    """)
    children = [subprocess.Popen([
        sys.executable, "-c", script, str(ROOT / "scripts"), str(tmp_path), str(run),
        str(barrier), str(winner)]) for _ in range(2)]
    barrier.write_text("go\n", encoding="utf-8")
    codes = sorted(child.wait(timeout=20) for child in children)
    assert codes == [0, 75]
    assert winner.read_text(encoding="utf-8") == "winner\n"


def test_two_complete_supervisors_on_live_nfs_leave_no_loser_evidence() -> None:
    parent = rc.canonical_root().parent
    assert str(rc.deployment_mount()["filesystem_type"]).startswith("nfs")
    root = parent / f".summary_recovery_supervisors.{uuid.uuid4().hex}"
    run = root / "recovery"
    root.mkdir(mode=0o700)
    for relative in rc.RECOVERY_DIRECTORIES:
        (run / relative).mkdir(parents=True, exist_ok=True)
    barrier = root / "barrier"
    attempts = [ATTEMPT_A, ATTEMPT_B]
    script = textwrap.dedent("""
        import json,pathlib,sys,time
        sys.path.insert(0,sys.argv[1])
        import msa_completion_summary_recovery_common as rc
        import recover_msae_completion_continuation_summary as r
        root,run,barrier=map(pathlib.Path,sys.argv[2:5]); attempt=sys.argv[5]
        destination=root/'candidate'
        rc.ROOT=root; r.ROOT=root
        rc.recovery_run_root=lambda: run; r.recovery_run_root=lambda: run
        rc.candidate_root=lambda: destination; r.candidate_root=lambda: destination
        rc.canonical_root=lambda: root/'canonical'; r.canonical_root=lambda: root/'canonical'
        rc.verify_initial_freeze=lambda: {'bundle_sha256':'1'*64}
        rc._applicable_freezes=lambda job: ('1'*64,None)
        rc.validate_candidate=lambda *args,**kwargs: {}
        r._validate_for_job=lambda *args,**kwargs: {}
        def science():
            stage=root/('.completion_diagnostic_candidate.staging.'+attempt)
            stage.mkdir()
            for name,data in {
                'diagnostic_results.json':b'{}\\n','diagnostic_results.md':b'# report\\n',
                'source_lineage.json':b'{}\\n','CANDIDATE_COMPLETE.json':b'{}\\n'}.items():
                (stage/name).write_bytes(data)
            rc.append_state('candidate',attempt,{
                'phase':'building','publication_attempt_id':attempt,
                'staging':str(stage.relative_to(root)),
                'destination':str(destination.relative_to(root)),
                'initial_recovery_bundle_sha256':'1'*64,
                'promotion_bundle_sha256':None,'parent_fsync_complete':False},claim=True)
            time.sleep(1.0)
            r._publish_stage('candidate',stage,destination,{'bundle_sha256':'1'*64},None)
            return {'winner':attempt}
        r.run_candidate=science
        deadline=time.monotonic()+10
        while not barrier.exists():
            if time.monotonic()>deadline: raise SystemExit(98)
            time.sleep(0.001)
        log='recovery/logs/candidate.'+attempt+'.log'
        closure='recovery/logs/candidate.'+attempt+'.closure.log'
        out=r.supervise('candidate',attempt,'run',log,closure,
                        ['python','fixture','supervise',attempt])
        print(json.dumps(out,sort_keys=True))
    """)
    children = [subprocess.Popen([
        sys.executable, "-c", script, str(ROOT / "scripts"), str(root), str(run),
        str(barrier), attempt], text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        for attempt in attempts]
    barrier.write_text("go\n", encoding="utf-8")
    results = []
    try:
        for attempt, child in zip(attempts, children):
            stdout, stderr = child.communicate(timeout=30)
            results.append((attempt, child.returncode, stdout, stderr))
        winners = [row for row in results if row[1] == 0]
        losers = [row for row in results if row[1] != 0]
        assert len(winners) == 1 and len(losers) == 1
        winner_id, loser_id = winners[0][0], losers[0][0]
        assert not (run / "filesystem_capabilities" / f"candidate.{loser_id}.json").exists()
        assert not (run / "job_manifests" / f"candidate.{loser_id}.manifest.json").exists()
        assert not (run / "job_manifests" / f"candidate.{loser_id}.terminal.json").exists()
        assert not (run / "job_state" / f"candidate.{loser_id}.json").exists()
        success = json.loads((run / "job_manifests/candidate.success.json").read_text())
        assert winner_id in success["successful_attempt_terminal"]
        state_text = "\n".join(
            path.read_text(encoding="utf-8") for path in sorted(
                (run / "job_state/candidate").glob("g*.json")))
        assert loser_id not in state_text
        assert (root / "candidate").is_dir()
    finally:
        for child in children:
            if child.poll() is None:
                child.kill(); child.wait()
        for _ in range(50):
            try:
                shutil.rmtree(root)
                break
            except OSError as exc:
                if exc.errno not in {errno.ENOTEMPTY, errno.EBUSY}:
                    raise
                time.sleep(0.1)
        assert not root.exists()
        rc.fsync_directory(parent)


def _sigkill_supervisor(tmp_path: Path, point: str) -> subprocess.CompletedProcess[str]:
    run = tmp_path / "recovery"
    for relative in rc.RECOVERY_DIRECTORIES:
        (run / relative).mkdir(parents=True, exist_ok=True)
    log = run / "logs" / f"candidate.{ATTEMPT_A}.log"
    closure = run / "logs" / f"candidate.{ATTEMPT_A}.closure.log"
    argv = ["python", "fixture", "supervise"]
    payload = capability_payload(
        "candidate", ATTEMPT_A, str(log.relative_to(tmp_path)))
    payload["argv"] = argv
    script = textwrap.dedent("""
        import json,os,pathlib,signal,sys
        sys.path.insert(0, sys.argv[1])
        import msa_completion_summary_recovery_common as rc
        import recover_msae_completion_continuation_summary as r
        root,run,point=pathlib.Path(sys.argv[2]),pathlib.Path(sys.argv[3]),sys.argv[4]
        payload=json.loads(sys.argv[5]); mount=json.loads(sys.argv[6])
        destination=root/'candidate'
        rc.ROOT=root; r.ROOT=root
        rc.recovery_run_root=lambda: run; r.recovery_run_root=lambda: run
        rc.candidate_root=lambda: destination; r.candidate_root=lambda: destination
        rc.deployment_mount=lambda: mount
        rc.verify_initial_freeze=lambda: {'bundle_sha256':'1'*64}
        rc._applicable_freezes=lambda job: ('1'*64,None)
        r.run_filesystem_capability_gate=lambda *args: payload
        r._validate_for_job=lambda *args: {}
        def kill_hook(observed):
            if observed==point: os.kill(os.getpid(),signal.SIGKILL)
        r._test_sigkill=kill_hook
        def science():
            stage=root/'.completion_diagnostic_candidate.staging.fixture'
            stage.mkdir()
            for name,data in {
                'diagnostic_results.json':b'{}\\n','diagnostic_results.md':b'# report\\n',
                'source_lineage.json':b'{}\\n','CANDIDATE_COMPLETE.json':b'{}\\n'}.items():
                (stage/name).write_bytes(data)
            rc.append_state('candidate',sys.argv[7],{
                'phase':'building','publication_attempt_id':sys.argv[7],
                'staging':str(stage.relative_to(root)),
                'destination':str(destination.relative_to(root)),
                'initial_recovery_bundle_sha256':'1'*64,
                'promotion_bundle_sha256':None,'parent_fsync_complete':False},claim=True)
            r._publish_stage('candidate',stage,destination,{'bundle_sha256':'1'*64},None)
            return {'ok':True}
        r.run_candidate=science
        r.supervise('candidate',sys.argv[7],'run',sys.argv[8],sys.argv[9],payload['argv'])
    """)
    return subprocess.run([
        sys.executable, "-c", script, str(ROOT / "scripts"), str(tmp_path), str(run), point,
        json.dumps(payload), json.dumps(FAKE_MOUNT), ATTEMPT_A,
        str(log.relative_to(tmp_path)), str(closure.relative_to(tmp_path)),
    ], text=True, capture_output=True, check=False, timeout=30)


@pytest.mark.parametrize(
    ("point", "expected_phase", "destination_present"),
    [("after_capability_before_manifest", None, False),
     ("before_root_reservation", "ready_to_publish", False),
     ("after_parent_fsync_state", "parent_fsync_complete", True)],
)
def test_sigkill_supervisor_points_are_orphaned_and_fail_closed(
        point: str, expected_phase: str | None, destination_present: bool,
        tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    completed = _sigkill_supervisor(tmp_path, point)
    assert completed.returncode == -signal.SIGKILL
    run = tmp_path / "recovery"
    cap = run / "filesystem_capabilities" / f"candidate.{ATTEMPT_A}.json"
    manifest = run / "job_manifests" / f"candidate.{ATTEMPT_A}.manifest.json"
    assert cap.is_file()
    assert manifest.exists() is (point != "after_capability_before_manifest")
    with locked_fixture(tmp_path, monkeypatch) as locked_run:
        monkeypatch.setattr(rc, "candidate_root", lambda: tmp_path / "candidate")
        monkeypatch.setattr(recovery, "candidate_root", lambda: tmp_path / "candidate")
        created = rc.close_orphan_attempts("candidate")
        assert len(created) == 1
        terminal = rc._validate_attempt_terminal(created[0], job="candidate")
        assert terminal["outcome"] == "technical_failure"
        assert terminal["released_lock_observed"] is True
        head = rc.read_state_chain("candidate")
        assert (None if head is None else head["phase"]) == expected_phase
        assert (tmp_path / "candidate").exists() is destination_present
        assert locked_run == run
        assert not rc.success_path("candidate").exists()
        if expected_phase is not None:
            monkeypatch.setattr(recovery, "verify_initial_freeze", lambda: {
                "bundle_sha256": "1" * 64})
            monkeypatch.setattr(recovery, "_validate_for_job", lambda *_: {})
            monkeypatch.setattr(rc, "validate_candidate", lambda *_args, **_kwargs: {})
            install_attempt_evidence(
                run, tmp_path, monkeypatch, attempt=ATTEMPT_B, mode="reconcile")
            monkeypatch.setenv("MSAE_RECOVERY_ATTEMPT_ID", ATTEMPT_B)
            reconciled = recovery.reconcile("candidate")
            assert reconciled["reconciled"] == "candidate"
            terminal_b = rc.close_attempt("candidate", ATTEMPT_B, 0)
            assert terminal_b["outcome"] == "reconciled"
            closure = rc.validate_success_closure("candidate", tmp_path / "candidate")
            assert closure["successful_attempt_terminal"].endswith(
                f"candidate.{ATTEMPT_B}.terminal.json")


def test_promotion_freeze_contract_requires_per_file_candidate_inventory(
        monkeypatch: pytest.MonkeyPatch) -> None:
    source = Path(rc.verify_promotion_freeze.__code__.co_filename).read_text(encoding="utf-8")
    freezer = (ROOT / "scripts/freeze_msae_completion_summary_promotion.py").read_text(
        encoding="utf-8")
    assert '"candidate_files": content_inventory(candidate_root())' in source
    assert '"candidate_files": content_inventory(candidate_root())' in freezer
    publish = Path(recovery.run_publish.__code__.co_filename).read_text(encoding="utf-8")
    assert "canonical staged bytes differ from reviewed candidate" in publish
    assert "promotion[\"bundle_material\"][\"candidate_files\"]" in publish


def test_initial_freezer_is_durable_create_once_and_refuses_second_creation(
        tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    freeze = tmp_path / "freeze.json"
    monkeypatch.setattr(initial_freezer, "INITIAL_FREEZE", freeze)
    monkeypatch.setattr(initial_freezer, "candidate_root", lambda: tmp_path / "candidate")
    monkeypatch.setattr(initial_freezer, "canonical_root", lambda: tmp_path / "canonical")
    monkeypatch.setattr(initial_freezer, "verify_incident_inputs", lambda: {
        "config": {"original_continuation_bundle_sha256": "a" * 64,
                   "plan_review_sha256": "b" * 64}})
    inventory = [{"path": "implementation.py", "sha256": "c" * 64}]
    monkeypatch.setattr(initial_freezer, "implementation_inventory", lambda: inventory)
    monkeypatch.setattr(initial_freezer, "_review_binding", lambda *args, **kwargs: {
        "transcript_sha256": "d" * 64})
    monkeypatch.setattr(initial_freezer, "verify_initial_freeze", lambda: rc.strict_json(freeze))
    monkeypatch.setattr(sys, "argv", ["freeze"])
    initial_freezer.main()
    assert freeze.is_file() and not freeze.is_symlink()
    with pytest.raises(RuntimeError, match="create-once"):
        initial_freezer.main()


def test_two_concurrent_initial_freezers_create_one_exact_immutable_record(
        tmp_path: Path) -> None:
    freeze = tmp_path / "freeze.json"
    barrier = tmp_path / "barrier"
    script = textwrap.dedent("""
        import pathlib,sys,time
        sys.path.insert(0,sys.argv[1])
        import msa_completion_summary_recovery_common as rc
        import freeze_msae_completion_summary_recovery as freezer
        root,freeze,barrier=map(pathlib.Path,sys.argv[2:5])
        freezer.INITIAL_FREEZE=freeze
        freezer.candidate_root=lambda: root/'candidate'
        freezer.canonical_root=lambda: root/'canonical'
        freezer.verify_incident_inputs=lambda: {'config': {
            'original_continuation_bundle_sha256':'a'*64,
            'plan_review_sha256':'b'*64}}
        freezer.implementation_inventory=lambda: [
            {'path':'implementation.py','sha256':'c'*64}]
        freezer._review_binding=lambda *args,**kwargs: {'transcript_sha256':'d'*64}
        freezer.verify_initial_freeze=lambda: rc.strict_json(freeze)
        freezer.utc_now=lambda: '2026-08-02T12:00:00+00:00'
        deadline=time.monotonic()+10
        while not barrier.exists():
            if time.monotonic()>deadline: raise SystemExit(98)
            time.sleep(0.001)
        sys.argv=['freeze']
        try:
            freezer.main()
        except RuntimeError as exc:
            if 'create-once' not in str(exc): raise
            raise SystemExit(75)
    """)
    children = [subprocess.Popen([
        sys.executable, "-c", script, str(ROOT / "scripts"), str(tmp_path),
        str(freeze), str(barrier)], stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        text=True) for _ in range(2)]
    barrier.write_text("go\n", encoding="utf-8")
    results = [child.communicate(timeout=20) for child in children]
    codes = [child.returncode for child in children]
    assert all(code in {0, 75} for code in codes) and 0 in codes, results
    facts = rc.regular_file_facts(freeze)
    assert facts["regular"] is True
    assert rc.strict_json(freeze)["schema_version"] == "atlas_completion_summary_recovery_freeze_v1"

    third = subprocess.run([
        sys.executable, "-c", script, str(ROOT / "scripts"), str(tmp_path),
        str(freeze), str(barrier)], text=True, capture_output=True, timeout=20, check=False)
    assert third.returncode == 75


def test_promotion_freezer_checks_current_mount_before_create_once_write(
        tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    freeze = tmp_path / "promotion.json"
    candidate = tmp_path / "candidate"; candidate.mkdir()
    (candidate / "diagnostic_results.json").write_text("{}\n", encoding="utf-8")
    (candidate / "diagnostic_results.md").write_text("# report\n", encoding="utf-8")
    (candidate / "source_lineage.json").write_text("{}\n", encoding="utf-8")
    monkeypatch.setattr(promotion_freezer, "PROMOTION_FREEZE", freeze)
    monkeypatch.setattr(promotion_freezer, "candidate_root", lambda: candidate)
    monkeypatch.setattr(promotion_freezer, "canonical_root", lambda: tmp_path / "canonical")
    monkeypatch.setattr(promotion_freezer, "verify_execution_owner_mount", lambda: (_ for _ in ()).throw(
        RuntimeError("current mount mismatch")))
    with pytest.raises(RuntimeError, match="mount mismatch"):
        promotion_freezer.main()
    assert not freeze.exists()

    monkeypatch.setattr(promotion_freezer, "verify_execution_owner_mount", lambda: {})
    monkeypatch.setattr(promotion_freezer, "verify_initial_freeze", lambda: {
        "bundle_sha256": "1" * 64})
    candidate_row = {"content_sha256": "2" * 64, "terminal_sha256": "3" * 64}
    monkeypatch.setattr(promotion_freezer, "validate_candidate", lambda **kwargs: candidate_row)
    monkeypatch.setattr(promotion_freezer, "_candidate_review", lambda *args, **kwargs: {
        "transcript_sha256": "4" * 64})
    monkeypatch.setattr(promotion_freezer, "verify_promotion_freeze", lambda: rc.strict_json(freeze))
    promotion_freezer.main()
    assert freeze.is_file() and not freeze.is_symlink()
    with pytest.raises(RuntimeError, match="create-once"):
        promotion_freezer.main()


def test_launcher_exposes_only_the_one_process_supervisor() -> None:
    source = (ROOT / "scripts/launch_msae_completion_summary_recovery_tmux.sh").read_text(
        encoding="utf-8")
    assert 'driver" supervise --job' in source
    assert "create-attempt" not in source and "close-attempt" not in source
    assert "exec 8>>" in source and "flock -n 8" in source
    driver = (ROOT / "scripts/recover_msae_completion_continuation_summary.py").read_text(
        encoding="utf-8")
    assert '"supervise", "verify-candidate", "verify-only"' in driver
