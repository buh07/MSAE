from __future__ import annotations

import copy
import hashlib
import json
import os
import pickle
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import msa_completion_continuation_common as cc
from msa_completion_common import atomic_write_json, canonical_json_bytes, sha256_file, write_terminal
from run_msae_completion_continuation import parse_args, resolve


def test_continuation_config_changes_only_executor_root_and_adds_denial_metadata() -> None:
    base = json.loads((ROOT / "configs/atlas_completion/analysis.json").read_text())
    continuation = json.loads(cc.CONFIG.read_text())
    metadata = continuation.pop("diagnostic_continuation")
    assert continuation.pop("run_root") == "pilot_runs/20260802_atlas_completion_diagnostic_continuation_v1"
    assert base.pop("run_root") == "pilot_runs/20260801_atlas_completion_v1"
    assert continuation == base
    assert metadata["diagnostic_continuation_only"] is True
    assert metadata["decision_promotion_allowed"] is False
    assert metadata["base_completion_bundle_sha256"] == cc.BASE_DIGEST
    assert metadata["resource_job_caps_gpu_hours"] == {
        "k2": 5.0, "specificity": 0.3, "stability": 3.25}
    assert metadata["termination_grace_seconds"] == 300
    assert metadata["timeout_accounting_margin_seconds"] == 5


def test_canonical_inventory_has_16_jobs_and_9_stages() -> None:
    specs = cc.canonical_job_specs()
    stages = cc.canonical_stage_members()
    assert len(specs) == 16
    assert len(stages) == 9
    assert sorted(map(len, stages.values())) == [1, 1, 1, 1, 2, 2, 2, 2, 4]
    assert set(specs) == {job for members in stages.values() for job in members}
    caps = [cc.resource_job_cap_hours(spec) for spec in specs.values()]
    assert caps.count(5.0) == 8 and caps.count(3.25) == 4 and caps.count(0.3) == 4
    assert sum(caps) == pytest.approx(54.2)


def test_resource_caps_are_atomic_grace_inclusive_and_use_exact_base_ledger(
        tmp_path: Path) -> None:
    from concurrent.futures import ThreadPoolExecutor

    ledger = cc.base_gpu_ledger()
    assert ledger["total_gpu_hours"] == pytest.approx(11.157119510886776)
    assert [row["accounting_field"] for row in ledger["terminals"]] == [
        "recorded_gpu_hours", "recorded_gpu_hours", "recorded_gpu_hours",
        "recorded_gpu_hours", "recorded_worker_gpu_hours", "recorded_worker_gpu_hours"]
    assert len(ledger["terminals"]) == 6
    policy = cc.runtime_limit_policy(reserved_seconds=18000, stage_remaining_seconds=20000)
    assert policy == {"soft_timeout_seconds": 17695, "termination_grace_seconds": 300,
                      "timeout_accounting_margin_seconds": 5,
                      "hard_runtime_ceiling_seconds": 18000}
    exhausted = cc.runtime_limit_policy(reserved_seconds=1080, stage_remaining_seconds=304)
    assert exhausted["soft_timeout_seconds"] == 0

    run_root = tmp_path / "reservation_race"
    specs = cc.canonical_job_specs()
    def reserve(item: tuple[str, dict[str, object]]) -> dict[str, object]:
        job, spec = item
        return cc.reserve_gpu_resources(
            run_root=run_root, job_id=job, stage=run_root / str(spec["stage"]),
            spec=spec, base_actual_gpu_hours=ledger["total_gpu_hours"])
    with ThreadPoolExecutor(max_workers=16) as pool:
        rows = list(pool.map(reserve, specs.items()))
    reservations = [json.loads(path.read_text())
                    for path in (run_root / "budget_reservations").glob("*.json")]
    assert len(rows) == 16 and len(reservations) == 16
    assert len(list((run_root / "stage_deadlines").glob("*.json"))) == 9
    assert sum(row["reserved_gpu_hours"] for row in reservations) == pytest.approx(54.2)
    assert all(row["base_actual_gpu_hours"] == pytest.approx(ledger["total_gpu_hours"])
               for row in reservations)
    assert max(row["prior_reserved_gpu_hours"] + row["reserved_gpu_hours"]
               for row in reservations) == pytest.approx(54.2)
    running = 0.0
    for row in sorted(reservations, key=lambda item: item["prior_reserved_gpu_hours"]):
        assert row["prior_reserved_gpu_hours"] == pytest.approx(running)
        running += row["reserved_gpu_hours"]
    assert running == pytest.approx(54.2)

    # GNU timeout's grace lies inside, rather than after, the hard ceiling.
    code = "import signal,time; signal.signal(signal.SIGINT, lambda *a: None); time.sleep(30)"
    started = __import__("time").monotonic()
    proc = subprocess.run(
        ["timeout", "--signal=INT", "--kill-after=1s", "1s", sys.executable, "-c", code],
        capture_output=True, text=True, timeout=5)
    elapsed = __import__("time").monotonic() - started
    # Python reports a signal as -9; a shell observes the same supervisor death as 137.
    assert proc.returncode in {124, 137, -9} and elapsed <= 3.0


def test_schema_aware_gpu_ledger_rejects_ambiguous_accounting(tmp_path: Path) -> None:
    baseline = tmp_path / "baseline.json"
    worker = tmp_path / "worker.json"
    atomic_write_json(baseline, {
        "schema_version": "atlas_completion_baseline_complete_v1",
        "resource_accounting": {"recorded_gpu_hours": 1.25}})
    atomic_write_json(worker, {
        "schema_version": "atlas_completion_refit_terminal_v1",
        "resource_accounting": {"recorded_worker_gpu_hours": 2.5}})
    ledger = cc.gpu_terminal_ledger([baseline, worker], scope="fixture")
    assert ledger["total_gpu_hours"] == 3.75
    bad = tmp_path / "ambiguous.json"
    atomic_write_json(bad, {
        "schema_version": "atlas_completion_frozen_stop_v1",
        "resource_accounting": {"recorded_gpu_hours": 1.0,
                                "recorded_worker_gpu_hours": 1.0}})
    with pytest.raises(RuntimeError, match="unregistered"):
        cc.gpu_terminal_ledger([bad], scope="fixture")


def test_supervisor_classifies_timeout_prompt_crash_and_closed_failures() -> None:
    import time

    prompt = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(30)"])
    time.sleep(0.1)
    prompt.kill(); prompt.wait(timeout=3)
    prompt_shell_status = 128 + (-prompt.returncode)
    native = subprocess.run([sys.executable, "-c", "import os; os.abort()"],
                            capture_output=True, timeout=3)
    native_shell_status = 128 + (-native.returncode)
    common = {"expected_output_exists": False, "stage_terminal_exists": False,
              "matching_launch_failure_exists": False}
    assert cc.classify_supervised_exit(
        exit_code=137, process_elapsed_seconds=10.0, soft_timeout_seconds=10.0,
        **common) == "resource_timeout"
    assert cc.classify_supervised_exit(
        exit_code=prompt_shell_status, process_elapsed_seconds=0.1,
        soft_timeout_seconds=10.0, **common) == "process_crash"
    assert cc.classify_supervised_exit(
        exit_code=native_shell_status, process_elapsed_seconds=0.1,
        soft_timeout_seconds=10.0, **common) == "process_crash"
    assert cc.classify_supervised_exit(
        exit_code=0, process_elapsed_seconds=0.1, soft_timeout_seconds=10.0,
        **common) == "process_crash"
    assert cc.classify_supervised_exit(
        exit_code=1, process_elapsed_seconds=0.1, soft_timeout_seconds=10.0,
        expected_output_exists=False, stage_terminal_exists=True,
        matching_launch_failure_exists=False) == "technical_failure"
    assert cc.classify_supervised_exit(
        exit_code=0, process_elapsed_seconds=0.1, soft_timeout_seconds=10.0,
        expected_output_exists=True, stage_terminal_exists=False,
        matching_launch_failure_exists=False) == "job_process_success"


def test_adapter_cli_exact_allowlist() -> None:
    job = cc.JOBS[0]
    args = parse_args(["k2", "--job", job, "--point", "--device", "cuda:0"])
    job_id, stage, argv, draws = resolve(args)
    assert job_id == "g4_point" and stage == cc.RUN_ROOT / "k2_refit" / job
    assert argv[-2:] == ["--config", str(cc.CONFIG)] and draws == list(range(500))
    args = parse_args(["stability", "--draw-start", "167", "--draw-end", "334",
                       "--device", "cuda:0"])
    assert resolve(args)[0] == "stability_167_334"
    with pytest.raises(SystemExit):
        parse_args(["k2", "--job", job, "--draw-start", "1", "--draw-end", "500",
                    "--device", "cuda:0"])
    with pytest.raises(SystemExit):
        parse_args(["specificity", "--job", job, "--device", "cuda:0",
                    "--config", "evil.json"])
    with pytest.raises(SystemExit):
        parse_args(["stability", "--draw-start", "0", "--draw-end", "166",
                    "--device", "cuda:0"])


def test_narrow_firewall_accepts_only_exact_continuation_config() -> None:
    fw = cc.continuation_firewall(ROOT / "pilot_runs/20260731_atlas_v1_architecture_selection",
                                  cc.RUN_ROOT)
    assert fw.attest(cc.CONFIG) == cc.CONFIG.resolve()
    with pytest.raises(PermissionError):
        fw.attest(cc.INVENTORY)


def test_source_inventory_replays_entire_old_root() -> None:
    row = cc.verify_source_inventory()
    assert row["entry_count"] == len(row["entries"])
    assert row["entries"] == cc.recursive_inventory(cc.SOURCE_RUN)
    assert row["inventory_sha256"] == cc.inventory_digest(row["entries"])
    assert len(row["entries"]) > 2000


def _raw_fixture(tmp_path: Path) -> tuple[Path, dict, str, str]:
    stage = tmp_path / "raw"
    (stage / "draws").mkdir(parents=True)
    (stage / "completed_hashes").mkdir()
    config_sha, bundle_sha = "a" * 64, "b" * 64
    retained: dict[str, str] = {}
    point = {"draw_id": "point", "kind": "raw", "layer": 3,
             "config_sha256": config_sha, "completion_bundle_sha256": bundle_sha,
             "result": {}}
    (stage / "point.json").write_bytes(canonical_json_bytes(point))
    retained["point.json"] = sha256_file(stage / "point.json")
    for draw in range(500):
        leaf = {"draw_id": draw, "kind": "raw", "layer": 3,
                "config_sha256": config_sha, "completion_bundle_sha256": bundle_sha,
                "result": {"finite": True}}
        leaf_path = stage / "draws" / f"{draw:04d}.json"
        leaf_path.write_bytes(canonical_json_bytes(leaf))
        reg = {"draw_id": draw, "status": "complete",
               "artifact": f"draws/{draw:04d}.json", "artifact_sha256": sha256_file(leaf_path),
               "config_sha256": config_sha, "completion_bundle_sha256": bundle_sha}
        reg_path = stage / "completed_hashes" / f"{draw:04d}.json"
        reg_path.write_bytes(canonical_json_bytes(reg))
        retained[f"draws/{draw:04d}.json"] = sha256_file(leaf_path)
        retained[f"completed_hashes/{draw:04d}.json"] = sha256_file(reg_path)
    stop = {"config_sha256": config_sha, "completion_bundle_sha256": bundle_sha,
            "registered_complete_draw_ids": list(range(500)),
            "retained_partial_sha256": retained}
    return stage, stop, config_sha, bundle_sha


def test_all_500_raw_pairings_validate_and_one_corruption_is_fatal(tmp_path: Path) -> None:
    stage, stop, config_sha, bundle_sha = _raw_fixture(tmp_path)
    for draw in range(500):
        payload = cc.validate_old_raw_from_stage(
            stage, stop, draw, config_sha256=config_sha,
            completion_bundle_sha256=bundle_sha)
        assert payload["draw_id"] == draw
    registration = stage / "completed_hashes/0499.json"
    row = json.loads(registration.read_text())
    row["artifact_sha256"] = "0" * 64
    registration.write_bytes(canonical_json_bytes(row))
    # Even if the stop map is maliciously updated to the corrupt registration,
    # the inner artifact binding still makes the single mismatch fatal.
    stop["retained_partial_sha256"]["completed_hashes/0499.json"] = sha256_file(registration)
    with pytest.raises(RuntimeError, match="registration mismatch"):
        cc.validate_old_raw_from_stage(stage, stop, 499, config_sha256=config_sha,
                                       completion_bundle_sha256=bundle_sha)


def test_live_raw_pairing_point_and_draw_registration() -> None:
    assert cc.load_old_raw("point")["draw_id"] == "point"
    assert cc.load_old_raw(0)["draw_id"] == 0
    assert cc.load_old_raw(499)["draw_id"] == 499


def test_baseline_science_gate_allows_only_enumerated_provenance() -> None:
    source = json.loads((cc.BASELINE_SOURCE / "baseline.json").read_text())
    with (cc.BASELINE_SOURCE / "baseline_bundle.pkl").open("rb") as handle:
        source_bundle = pickle.load(handle)
    rebound = copy.deepcopy(source)
    rebound.update({"config_sha256": "1" * 64, "completion_bundle_sha256": "2" * 64,
                    "resolved_config": {}, "resolved_arguments": {}, "device": "cpu",
                    "environment": {}, "input_attestation": {}, "elapsed_sec": 0,
                    "started_utc": "x", "ended_utc": "y",
                    "provenance_rebind": {"science": "equal"}})
    rebound_bundle = copy.deepcopy(source_bundle)
    rebound_bundle["completion_bundle_sha256"] = "2" * 64
    cc.verify_baseline_science_payloads(source, rebound, source_bundle, rebound_bundle,
                                        continuation_bundle_sha256="2" * 64)
    bad = copy.deepcopy(rebound); bad["selected_simple_baseline"] = "pca16_complement"
    with pytest.raises(RuntimeError, match="science mismatch"):
        cc.verify_baseline_science_payloads(source, bad, source_bundle, rebound_bundle,
                                            continuation_bundle_sha256="2" * 64)
    bad_bundle = copy.deepcopy(rebound_bundle); bad_bundle["baseline_selection_failed"] = False
    with pytest.raises(RuntimeError, match="bundle differs"):
        cc.verify_baseline_science_payloads(source, rebound, source_bundle, bad_bundle,
                                            continuation_bundle_sha256="2" * 64)


def test_actual_adapter_and_frozen_worker_point_and_shard_paths_are_fixture_only(tmp_path: Path) -> None:
    script = r'''
import importlib,json,pickle,sys
from pathlib import Path
sys.path.insert(0, %r)
import run_msae_completion_continuation as adapter
from msa_completion_common import canonical_json_bytes,sha256_file
root=Path(sys.argv[1]); job=%r; digest="d"*64
config_path=adapter.CONFIG
config=json.loads(config_path.read_text())
(root/"data/atlas_completion_v1").mkdir(parents=True)
(root/"data/atlas_completion_v1/tier2_manifest.json").write_text("{}\n")
baseline=root/config["run_root"]/"baseline"; baseline.mkdir(parents=True)
with (baseline/"baseline_bundle.pkl").open("wb") as h: pickle.dump({"completion_bundle_sha256":digest},h)
class FW:
 def __init__(self): self.attestation={}
 def attest(self,p,role=None): return Path(p)
 def register_root(self,p): pass
 def register_file(self,p): pass
seen=[]
prevalidated=[]
attested=[]
def original(draw,*args,raw_result_override=None,**kwargs):
 assert raw_result_override is not None
 expected="point" if draw is None else draw
 assert raw_result_override["draw_id"]==expected
 seen.append(expected)
 return {"finite":True,"families":{},"recoveries":{},"sentinels":{}}
def register(stage,draw,path,**kwargs):
 p=Path(stage)/"completed_hashes"/f"{draw:04d}.json"; p.parent.mkdir(exist_ok=True)
 p.write_bytes(canonical_json_bytes({"draw_id":draw,"status":kwargs["status"],"artifact":str(Path(path).relative_to(stage)),"artifact_sha256":sha256_file(Path(path)),"config_sha256":kwargs["config_sha256"],"completion_bundle_sha256":kwargs["completion_bundle_sha256"]}))
adapter.verify_continuation_freeze=lambda *a,**k:{"bundle_sha256":digest}
adapter.verify_rebound_baseline=lambda:{"science_equal":True}
adapter.verify_source_inventory=lambda:{"fixture":True}
adapter.prevalidate_old_raw=lambda ids:prevalidated.append(list(ids))
adapter.load_old_raw=lambda draw:{"draw_id":draw,"unchanged":"byte-identified-fixture"}
adapter.attest_old_raw_inputs=lambda firewall,draw:attested.append(draw)
adapter.require_continuation_config=lambda p:{"bundle_sha256":digest,"_freeze_record_path":str(config_path),"_freeze_record_sha256":sha256_file(config_path)}
adapter.continuation_firewall=lambda *a,**k:FW()
adapter.publish_technical_stop=lambda *a,**k:(_ for _ in ()).throw(AssertionError("unexpected stop"))
real_import=importlib.import_module
def instrument(name):
 target=real_import(name)
 target.ROOT=root
 target.attest_completion_freeze_record=lambda *a,**k:None
 target.validated_cuda_environment=lambda d:{"fixture":True}
 target.require_bound_stage_files=lambda *a,**k:{}
 target.load_activation=lambda *a,**k:object()
 target.k2_draw=original
 target.maybe_finalize_draw_stage=lambda *a,**k:None
 target.claim_draw=lambda *a,**k:Path("claim")
 target.release_claim=lambda *a,**k:None
 target.prepare_draw_resume=lambda *a,**k:"new"
 target.register_draw_artifact=register
 return target
adapter.importlib.import_module=instrument
originals=(adapter.base_common.default_firewall,adapter.base_common.verify_completion_freeze,
           adapter.base_common.require_frozen_completion_config,list(sys.argv))
adapter.run(["k2","--job",job,"--point","--device","cuda:0"])
adapter.run(["k2","--job",job,"--draw-start","0","--draw-end","500","--device","cuda:0"])
assert seen[0]=="point" and seen[1:]==list(range(500))
assert prevalidated==[["point"],list(range(500))]
assert attested[0]=="point" and attested[1:]==list(range(500))
stage=root/config["run_root"]/"k2_refit"/job
assert (stage/"point.json").is_file()
assert len(list((stage/"draws").glob("*.json")))==500
assert (stage/"shard_0000_0500.json").is_file()
assert adapter.base_common.default_firewall is originals[0]
assert adapter.base_common.verify_completion_freeze is originals[1]
assert adapter.base_common.require_frozen_completion_config is originals[2]
assert sys.argv==originals[3]
''' % (str(ROOT / "scripts"), cc.JOBS[0])
    env = dict(os.environ)
    env["PYTHONPATH"] = str(ROOT / "scripts")
    proc = subprocess.run([sys.executable, "-c", script, str(tmp_path)], env=env,
                          capture_output=True, text=True, timeout=120)
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert not cc.RUN_ROOT.exists()


def test_adapter_injected_failures_close_new_stage_and_preserve_old_root(monkeypatch: pytest.MonkeyPatch) -> None:
    import types
    import run_msae_completion_continuation as adapter

    for target_name in adapter.TARGETS.values():
        monkeypatch.delitem(sys.modules, target_name, raising=False)
    before = cc.recursive_inventory(cc.SOURCE_RUN)
    before_mtimes = {str(path.relative_to(cc.SOURCE_RUN)): path.stat().st_mtime_ns
                     for path in cc.SOURCE_RUN.rglob("*") if path.is_file()}
    published: list[tuple[Path, str]] = []
    monkeypatch.setattr(adapter, "verify_continuation_freeze", lambda: {"bundle_sha256": "d" * 64})
    monkeypatch.setattr(adapter, "verify_rebound_baseline", lambda: {"science_equal": True})
    monkeypatch.setattr(adapter, "verify_source_inventory", lambda: {"fixture": True})
    monkeypatch.setattr(adapter, "prevalidate_old_raw", lambda draws: None)
    monkeypatch.setattr(adapter, "continuation_firewall", lambda *a, **k: object())
    monkeypatch.setattr(adapter, "require_continuation_config", lambda path: {"bundle_sha256": "d" * 64})
    def publish_stop(stage: Path, **kwargs: object) -> Path:
        published.append((stage, str(kwargs["job_id"])))
        return stage / "FROZEN_EQUIVOCAL_STOP.json"
    monkeypatch.setattr(adapter, "publish_technical_stop", publish_stop)
    monkeypatch.setattr(adapter, "publish_launch_failure",
                        lambda **kwargs: (_ for _ in ()).throw(AssertionError("root fallback used")))

    def fake_import(name: str) -> object:
        module = types.SimpleNamespace(
            __file__=str(ROOT / "scripts" / f"{name}.py"),
            default_firewall=adapter.continuation_firewall,
            require_frozen_completion_config=adapter.require_continuation_config,
            verify_completion_freeze=adapter.verify_continuation_freeze,
            _FAILURE_ATTESTATION={},
        )
        module.main = lambda: (_ for _ in ()).throw(RuntimeError(f"injected {name}"))
        if name == "run_msae_refit_worker":
            module.k2_draw = lambda *a, **k: None
        return module

    monkeypatch.setattr(adapter.importlib, "import_module", fake_import)
    cases = [
        (["k2", "--job", cc.JOBS[0], "--point", "--device", "cuda:0"], "g4_point"),
        (["stability", "--point", "--device", "cuda:0"], "stability_point"),
        (["specificity", "--job", cc.JOBS[0], "--device", "cuda:0"], "specificity_g4"),
    ]
    for argv, _ in cases:
        with pytest.raises(RuntimeError, match="injected"):
            adapter.run(argv)
    assert [job for _, job in published] == [job for _, job in cases]
    assert all(stage.resolve().is_relative_to(cc.RUN_ROOT.resolve()) for stage, _ in published)
    assert before == cc.recursive_inventory(cc.SOURCE_RUN)
    after_mtimes = {str(path.relative_to(cc.SOURCE_RUN)): path.stat().st_mtime_ns
                    for path in cc.SOURCE_RUN.rglob("*") if path.is_file()}
    assert before_mtimes == after_mtimes


def test_technical_stop_survives_environment_and_accounting_capture_failures(
        tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    run_root = tmp_path / "run"
    config = tmp_path / "analysis.json"
    config.write_bytes(canonical_json_bytes({"fixture": True}))
    monkeypatch.setattr(cc, "RUN_ROOT", run_root)
    monkeypatch.setattr(cc, "CONFIG", config)
    monkeypatch.setattr(cc, "canonical_stage_members", lambda: {"k2_refit/job": ["job"]})
    monkeypatch.setattr(cc, "verify_continuation_freeze",
                        lambda **kwargs: {"bundle_sha256": "d" * 64})
    monkeypatch.setattr(cc, "runtime_environment",
                        lambda device: (_ for _ in ()).throw(KeyboardInterrupt("env")))
    monkeypatch.setattr(cc, "process_resource_accounting",
                        lambda *a, **k: (_ for _ in ()).throw(SystemExit("accounting")))
    stage = run_root / "k2_refit/job"
    path = cc.publish_technical_stop(
        stage, stop_code="fixture_stop", failed_gate="fixture_gate",
        error=RuntimeError("original"), job_id="job", requested_draw_ids=[0],
        device="cuda:0", elapsed_sec=3.5, verified_bundle_sha256="d" * 64)
    row = json.loads(path.read_text())
    assert row["stop_code"] == "fixture_stop"
    assert row["environment"]["capture_error_type"] == "KeyboardInterrupt"
    assert row["resource_accounting"]["capture_error_type"] == "SystemExit"
    assert row["resource_accounting"]["elapsed_sec"] == 3.5
    assert (stage / "TERMINAL_STATE.json").is_file()


def _write_job_fixture(tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
                       outcome: str) -> tuple[object, str, dict[str, object]]:
    import collect_msae_completion_continuation as collector

    job = "g4_point"
    spec = cc.canonical_job_specs()[job]
    run_root = tmp_path / "continuation"
    monkeypatch.setattr(collector, "RUN_ROOT", run_root)
    stage = run_root / str(spec["stage"])
    terminal_dir = run_root / "job_manifests"
    terminal_dir.mkdir(parents=True)
    stage.mkdir(parents=True)
    config_sha, freeze_sha = "a" * 64, "b" * 64
    terminal = {
        "schema_version": "atlas_completion_continuation_job_terminal_v1",
        "job": job, "exit_code": 0, "outcome": outcome,
        "scoring_started": outcome in {"job_process_success", "technical_failure", "resource_timeout", "process_crash"},
        "gpu_index": 0 if outcome in {"job_process_success", "technical_failure", "resource_timeout", "process_crash"} else None,
        "gpu_uuid": "GPU-fixture" if outcome in {"job_process_success", "technical_failure", "resource_timeout", "process_crash"} else None,
        "process_started_utc": None, "process_ended_utc": None,
        "process_elapsed_seconds": 0.0,
        "stage": str(stage), "expected_output": spec["expected"],
        "config_sha256": config_sha, "completion_bundle_sha256": freeze_sha,
        "diagnostic_continuation_only": True, "decision_promotion_allowed": False,
        "ended_utc": datetime.now(timezone.utc).isoformat(),
    }
    if outcome == "technical_failure":
        terminal["exit_code"] = 1
    if outcome == "resource_timeout":
        terminal["exit_code"] = 137
    if outcome == "process_crash":
        terminal["exit_code"] = 134
    if outcome == "resource_not_launched":
        terminal["exit_code"] = 75
        atomic_write_json(terminal_dir / f"{job}.resource_stop.json", {
            "schema_version": "atlas_completion_continuation_resource_stop_v1",
            "job": job, "reason": "gpu_queue_deadline_exceeded",
            "queue_started_utc": (datetime.now(timezone.utc) - timedelta(hours=12)).isoformat(),
            "queue_deadline_seconds": 43200,
            "queue_ended_utc": datetime.now(timezone.utc).isoformat(),
            "gpu_observations": [{"gpu_index": 0, "gpu_uuid": "GPU-fixture",
                                  "memory_used_mib": 123}],
            "scoring_started": False, "config_sha256": config_sha,
            "completion_bundle_sha256": freeze_sha, "decision_promotion_allowed": False,
        })
    elif outcome == "superseded_by_stage_stop":
        marker = write_terminal(stage, complete=False, payload={
            "config_sha256": config_sha, "completion_bundle_sha256": freeze_sha,
            "decision_promotion_allowed": False, "reason": "fixture_stop"})
        atomic_write_json(terminal_dir / f"{job}.superseded_stage.json", {
            "schema_version": "atlas_completion_continuation_superseded_v1",
            "job": job, "stage_terminal_state": "stopped",
            "stage_terminal_path": str(marker), "stage_terminal_sha256": sha256_file(marker),
            "scoring_started": False, "config_sha256": config_sha,
            "completion_bundle_sha256": freeze_sha, "decision_promotion_allowed": False,
            "recorded_utc": datetime.now(timezone.utc).isoformat(),
        })
    else:
        if outcome == "job_process_success":
            (stage / str(spec["expected"])).write_text("fixture\n")
        deadline = run_root / "stage_deadlines" / f"{collector._stage_id(stage)}.json"
        reservation = run_root / "budget_reservations" / f"{job}.json"
        now = datetime.now(timezone.utc)
        start_epoch = now.timestamp() - 10
        atomic_write_json(deadline, {
            "schema_version": "atlas_completion_continuation_stage_deadline_v1",
            "stage": str(stage), "started_epoch": start_epoch,
            "deadline_epoch": start_epoch + 86400, "maximum_stage_wall_seconds": 86400,
            "decision_promotion_allowed": False,
        })
        atomic_write_json(reservation, {
            "schema_version": "atlas_completion_continuation_gpu_reservation_v1",
            "job": job, "stage": str(stage), "reserved_gpu_hours": 5.0,
            "base_actual_gpu_hours": 1.0, "prior_reserved_gpu_hours": 0.0,
            "maximum_total_gpu_hours": 192.0, "decision_promotion_allowed": False,
        })
        log = run_root / "logs" / f"{job}.log"
        log.parent.mkdir(); log.write_text("fixture log\n")
        started = now - timedelta(seconds=5)
        terminal["ended_utc"] = now.isoformat()
        terminal["process_started_utc"] = started.isoformat()
        terminal["process_ended_utc"] = now.isoformat()
        terminal["process_elapsed_seconds"] = 5.0
        manifest_path = terminal_dir / f"{job}.json"
        atomic_write_json(manifest_path, {
            "schema_version": "atlas_completion_continuation_job_manifest_v1",
            "job": job, "pid": 123, "gpu_index": 0, "gpu_uuid": "GPU-fixture",
            "config_sha256": config_sha, "completion_bundle_sha256": freeze_sha,
            "started_utc": started.isoformat(), "log": str(log),
            "command": shlex_join(cc.canonical_gpu_command(job)),
            "stage_deadline_path": str(deadline), "stage_deadline_sha256": sha256_file(deadline),
            "budget_reservation_path": str(reservation),
            "budget_reservation_sha256": sha256_file(reservation),
            "soft_timeout_seconds": 1 if outcome == "resource_timeout" else 17695,
            "termination_grace_seconds": 300,
            "timeout_accounting_margin_seconds": 5,
            "hard_runtime_ceiling_seconds": 18000,
        })
        if outcome == "technical_failure":
            write_terminal(stage, complete=False, payload={
                "config_sha256": config_sha, "completion_bundle_sha256": freeze_sha,
                "decision_promotion_allowed": False, "reason": "fixture_technical_stop"})
        elif outcome == "resource_timeout":
            atomic_write_json(
                terminal_dir / f"{job}.resource_timeout.json",
                cc.supervisor_record_payload(
                    kind="resource_timeout", job_id=job, exit_code=137,
                    gpu_index=0, gpu_uuid="GPU-fixture", stage=stage,
                    expected_output=str(spec["expected"]),
                    process_started_utc=started.isoformat(),
                    process_ended_utc=now.isoformat(), process_elapsed_seconds=5.0,
                    launch_manifest=manifest_path, log=log, stage_deadline=deadline,
                    stage_deadline_sha256=sha256_file(deadline),
                    budget_reservation=reservation,
                    budget_reservation_sha256=sha256_file(reservation),
                    config_sha256=config_sha, completion_bundle_sha256=freeze_sha))
        elif outcome == "process_crash":
            atomic_write_json(
                terminal_dir / f"{job}.process_crash.json",
                cc.supervisor_record_payload(
                    kind="process_crash", job_id=job, exit_code=134,
                    gpu_index=0, gpu_uuid="GPU-fixture", stage=stage,
                    expected_output=str(spec["expected"]),
                    process_started_utc=started.isoformat(),
                    process_ended_utc=now.isoformat(), process_elapsed_seconds=5.0,
                    launch_manifest=manifest_path, log=log, stage_deadline=deadline,
                    stage_deadline_sha256=sha256_file(deadline),
                    budget_reservation=reservation,
                    budget_reservation_sha256=sha256_file(reservation),
                    config_sha256=config_sha, completion_bundle_sha256=freeze_sha))
    atomic_write_json(terminal_dir / f"{job}.terminal.json", terminal)
    return collector, job, spec


def shlex_join(parts: list[str]) -> str:
    import shlex
    return shlex.join(parts)


@pytest.mark.parametrize("outcome", [
    "job_process_success", "technical_failure", "resource_not_launched",
    "resource_timeout", "process_crash", "superseded_by_stage_stop",
])
def test_collector_validates_every_job_outcome_and_rehashes_support(
        tmp_path: Path, monkeypatch: pytest.MonkeyPatch, outcome: str) -> None:
    collector, job, spec = _write_job_fixture(tmp_path, monkeypatch, outcome)
    row = collector.validate_gpu_job(
        job, spec, config_sha="a" * 64, freeze_sha="b" * 64, maximum_hours=192.0)
    assert row["outcome"] == outcome
    if outcome in {"job_process_success", "technical_failure", "resource_timeout", "process_crash"}:
        assert row["launch_manifest_sha256"] and row["log_sha256"]
        if outcome == "resource_timeout":
            assert row["resource_timeout_sha256"]
            assert cc.terminal_state(Path(row["stage"])) is None
        if outcome == "process_crash":
            assert row["process_crash_sha256"]
            assert cc.terminal_state(Path(row["stage"])) is None
        if outcome in {"resource_timeout", "process_crash"}:
            monkeypatch.setattr(
                collector, "canonical_stage_members",
                lambda: {str(spec["stage"]): [job]})
            stages = collector.recompute_stages(
                {job: row}, config_sha="a" * 64, freeze_sha="b" * 64)
            assert stages[str(spec["stage"])]["stage_outcome"] == (
                "resource_incomplete" if outcome == "resource_timeout"
                else "process_incomplete")
        Path(row["log_path"]).write_text("tampered\n")
        with pytest.raises(
                RuntimeError, match="replay|manifest|log|support|timeout closure|process-crash closure"):
            # The manifest binds support but the collector also captures the new
            # log hash, so a persisted collection would differ on strict replay.
            replayed = collector.validate_gpu_job(
                job, spec, config_sha="a" * 64, freeze_sha="b" * 64,
                maximum_hours=192.0)
            if replayed["log_sha256"] != row["log_sha256"]:
                raise RuntimeError("support log differs on replay")
    elif outcome == "resource_not_launched":
        assert row["resource_stop_sha256"] and row["actual_gpu_hours"] == 0
        assert row["job_stop_reason"] == "gpu_queue_deadline_exceeded"
    else:
        assert row["superseded_stage_sha256"] and row["actual_gpu_hours"] == 0


def test_collector_gpu_overlap_policy() -> None:
    from collect_msae_completion_continuation import validate_gpu_process_intervals

    t0 = datetime(2026, 8, 2, tzinfo=timezone.utc)
    def row(job: str, uuid: str, start: int, end: int) -> dict[str, object]:
        return {"job": job, "gpu_uuid": uuid,
                "process_started_utc": (t0 + timedelta(seconds=start)).isoformat(),
                "process_ended_utc": (t0 + timedelta(seconds=end)).isoformat()}
    validate_gpu_process_intervals([
        row("a", "GPU-1", 0, 5), row("b", "GPU-1", 5, 10)])
    validate_gpu_process_intervals([
        row("a", "GPU-1", 0, 10), row("b", "GPU-2", 1, 9)])
    with pytest.raises(RuntimeError, match="overlapping GPU ownership"):
        validate_gpu_process_intervals([
            row("a", "GPU-1", 0, 10), row("b", "GPU-1", 9, 11)])


def test_resource_incomplete_series_never_exposes_inference_and_stopped_specificity_is_null(
        tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    import summarize_msae_completion_continuation as summary

    run_root = tmp_path / "run"
    monkeypatch.setattr(summary, "RUN_ROOT", run_root)
    job = cc.JOBS[0]
    stage = run_root / "k2_refit" / job
    stage.mkdir(parents=True)
    config_sha, freeze_sha = "a" * 64, "b" * 64
    old_point = summary.RAW_STAGE / "point.json"
    result = {
        "finite": True,
        "families": {family: {"assigned_recovery": 1.0, "leakage": 0.0,
                               "selectivity_margin": 1.0} for family in summary.PRIMARY},
        "recoveries": {rep: {task: 1.0 for task in summary.TASKS}
                       for rep in ["pos", "content"]},
        "sentinels": {sentinel: {"normalized_damage": 0.0}
                      for sentinel in json.loads(cc.CONFIG.read_text())["sentinels"]},
    }
    atomic_write_json(stage / "point.json", {
        "draw_id": "point", "config_sha256": config_sha,
        "completion_bundle_sha256": freeze_sha, "result": result,
        "input_attestation": {str(old_point.resolve()): {"sha256": sha256_file(old_point)}},
    })
    leaves = {draw: {"result": result} for draw in range(500)}
    monkeypatch.setattr(summary, "load_old_raw", lambda draw: {"draw_id": draw})
    monkeypatch.setattr(summary, "verify_refit_leaf_summaries", lambda *a, **k: None)
    monkeypatch.setattr(summary, "series_inventory", lambda *a, **k: {
        "requested_draw_ids": list(range(500)), "complete_draw_ids": list(range(500)),
        "failed_draw_ids": [], "scientifically_finite_draw_ids": list(range(500)),
        "invalid_draw_fields": {}, "leaves": leaves,
    })
    k2 = summary.k2_series(
        job, "resource_incomplete", json.loads(cc.CONFIG.read_text()),
        config_sha, freeze_sha, {}, {})
    assert k2["inference_valid"] is False
    assert k2["inference_gate"] is None
    assert k2["inference_null_reason"] == "resource_incomplete"
    assert all(
        field["summary"]["median"] is None
        for family in k2["series"]["families"].values() for field in family.values())

    specificity_stage = run_root / "specificity" / job
    specificity_stage.mkdir(parents=True)
    atomic_write_json(specificity_stage / "specificity.json", {"secret_result": 123.0})
    write_terminal(specificity_stage, complete=False, payload={
        "config_sha256": config_sha, "completion_bundle_sha256": freeze_sha,
        "decision_promotion_allowed": False, "reason": "fixture_stop"})
    specificity = summary.specificity_series(
        job, "stopped", json.loads(cc.CONFIG.read_text()), config_sha, freeze_sha,
        {}, [], {}, object())
    assert specificity["result_sha256"] is None
    assert specificity["summaries"] is None
    assert specificity["ce_collateral"] is None
    assert specificity["simple_identity_collateral"] is None


def test_valid_point_nonfinite_stop_replays_with_null_inference(
        tmp_path: Path) -> None:
    import summarize_msae_completion_continuation as summary

    stage = tmp_path / "stage"
    stage.mkdir()
    config_sha, freeze_sha = "a" * 64, "b" * 64
    point = stage / "point.json"
    atomic_write_json(point, {
        "draw_id": "point", "config_sha256": config_sha,
        "completion_bundle_sha256": freeze_sha, "result": {"finite": False}})
    write_terminal(stage, complete=False, payload={
        "schema_version": "atlas_completion_frozen_stop_v1",
        "stop_code": "point_scientifically_nonfinite",
        "failed_gate": "required_point_finiteness",
        "reason": "required point estimate was scientifically nonfinite",
        "requested_draw_ids": list(range(500)), "completed_draw_ids": [],
        "registered_complete_draw_ids": [], "failed_draw_ids": [],
        "requested_draws": 500, "minimum_complete_draws": 450,
        "point_scientifically_finite": False, "finite_draws": 0,
        "scientifically_finite_draw_ids": [],
        "retained_partial_sha256": {"point.json": sha256_file(point)},
        "config_sha256": config_sha, "completion_bundle_sha256": freeze_sha,
        "decision_promotion_allowed": False})
    inventory = summary.series_inventory(stage, config_sha, freeze_sha, lambda payload: None)
    assert inventory["scientifically_finite_draw_ids"] == []
    marker = json.loads((stage / "FROZEN_EQUIVOCAL_STOP.json").read_text())
    marker["stop_code"] = "insufficient_scientifically_finite_draws"
    (stage / "FROZEN_EQUIVOCAL_STOP.json").write_bytes(canonical_json_bytes(marker))
    (stage / "TERMINAL_STATE.json").write_bytes(
        canonical_json_bytes({**marker, "selected_state": "stopped"}))
    with pytest.raises(RuntimeError, match="point/stop semantics"):
        summary.series_inventory(stage, config_sha, freeze_sha, lambda payload: None)


def test_stage_terminal_schema_state_substitution_is_rejected(
        tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    import collect_msae_completion_continuation as collector
    import summarize_msae_completion_continuation as summary

    run_root = tmp_path / "run"
    monkeypatch.setattr(collector, "RUN_ROOT", run_root)
    config_sha, freeze_sha = "a" * 64, "b" * 64
    k2_stage = run_root / "k2_refit/job"
    point = k2_stage / "point.json"
    atomic_write_json(point, {"config_sha256": config_sha,
                              "completion_bundle_sha256": freeze_sha,
                              "result": {"finite": True}})
    write_terminal(k2_stage, complete=True, payload={
        "schema_version": "atlas_completion_diagnostic_continuation_technical_stop_v1",
        "config_sha256": config_sha, "completion_bundle_sha256": freeze_sha,
        "diagnostic_continuation_only": True, "scientific_retry_allowed": False,
        "decision_promotion_allowed": False})
    with pytest.raises(RuntimeError, match="terminal binding"):
        collector._validate_stage_terminal(
            k2_stage, config_sha=config_sha, freeze_sha=freeze_sha)
    with pytest.raises(RuntimeError, match="schema/state"):
        summary.series_inventory(k2_stage, config_sha, freeze_sha, lambda payload: None)

    stability = run_root / "stability"
    write_terminal(stability, complete=True, payload={
        "schema_version": "atlas_completion_refit_terminal_v1",
        "config_sha256": config_sha, "completion_bundle_sha256": freeze_sha,
        "decision_promotion_allowed": False})
    with pytest.raises(RuntimeError, match="terminal binding"):
        collector._validate_stage_terminal(
            stability, config_sha=config_sha, freeze_sha=freeze_sha)


def test_published_resource_accounting_exposes_caps_and_observed_reservations() -> None:
    import summarize_msae_completion_continuation as summary

    jobs = {job: {"reserved_gpu_hours": 0.0} for job in cc.canonical_job_specs()}
    jobs["g4_point"]["reserved_gpu_hours"] = 5.0
    ledger = {"scope": "fixture", "terminals": [], "total_gpu_hours": 11.0}
    report = summary.resource_accounting_report(
        {"jobs": jobs}, continuation_actual_gpu_hours=1.5, base_ledger=ledger)
    assert report["continuation_observed_reserved_gpu_hours"] == 5.0
    assert report["cumulative_base_actual_plus_continuation_reserved_gpu_hours"] == 16.0
    assert report["continuation_maximum_potential_reserved_gpu_hours"] == pytest.approx(54.2)
    assert report["maximum_total_gpu_hours"] == 192
    assert len(report["reservation_cap_assignments_gpu_hours"]) == 16
    assert report["jobs_reaching_reservation"] == ["g4_point"]


def test_final_result_terminal_replay_is_state_and_no_promotion_strict(
        tmp_path: Path) -> None:
    import summarize_msae_completion_continuation as summary

    root = tmp_path / "result"
    root.mkdir()
    result_path, report_path = root / "diagnostic_results.json", root / "diagnostic_results.md"
    result = {"limitations": {"all_diagnostic_stages_complete": False},
              "provenance": {"continuation_bundle_sha256": "b" * 64}}
    atomic_write_json(result_path, result); report_path.write_text("fixture\n")
    write_terminal(root, complete=False, payload={
        "schema_version": "atlas_completion_diagnostic_continuation_result_terminal_v1",
        "result_sha256": sha256_file(result_path), "report_sha256": sha256_file(report_path),
        "config_sha256": sha256_file(cc.CONFIG), "completion_bundle_sha256": "b" * 64,
        "diagnostic_continuation_only": True, "decision_promotion_allowed": False,
        "reason": "one_or_more_diagnostics_stopped_or_unavailable"})
    assert summary.validate_result_terminal(
        result, result_path, report_path, result_root=root) == "stopped"
    marker_path, selector_path = root / "FROZEN_EQUIVOCAL_STOP.json", root / "TERMINAL_STATE.json"
    marker = json.loads(marker_path.read_text()); marker["decision_promotion_allowed"] = True
    marker_path.write_bytes(canonical_json_bytes(marker))
    selector_path.write_bytes(canonical_json_bytes({**marker, "selected_state": "stopped"}))
    with pytest.raises(RuntimeError, match="envelope"):
        summary.validate_result_terminal(result, result_path, report_path, result_root=root)


def test_baseline_failure_disposition_does_not_open_rebound_bundle(
        tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    import summarize_msae_completion_continuation as summary

    run_root = tmp_path / "run"
    cause = run_root / "baseline/FROZEN_EQUIVOCAL_STOP.json"
    atomic_write_json(cause, {"reason": "fixture baseline failure"})
    monkeypatch.setattr(summary, "RUN_ROOT", run_root)
    monkeypatch.setattr(summary, "ROOT", tmp_path)
    monkeypatch.setattr(summary, "base_gpu_ledger",
                        lambda: {"scope": "fixture", "terminals": [], "total_gpu_hours": 0.0})
    jobs = {job: {"outcome": "baseline_not_complete", "stage": spec["stage"],
                  "cause_path": str(cause.resolve()), "cause_sha256": sha256_file(cause)}
            for job, spec in cc.canonical_job_specs().items()}
    stages = {stage: {"member_jobs": members, "stage_outcome": "baseline_not_complete",
                      "terminal_path": None, "terminal_sha256": None}
              for stage, members in cc.canonical_stage_members().items()}
    result = summary.baseline_failure_result(
        {"collection_outcome": "baseline_not_complete", "jobs": jobs, "stages": stages},
        {"bundle_sha256": "d" * 64}, {"inventory_sha256": "i" * 64})
    assert result["disposition"]["paper_branch"] == "unselected"
    assert result["disposition"]["training_warranted"] is False
    assert all(row["inference_valid"] is False for row in result["k2"].values())
    assert result["stability"]["inference_valid"] is False
    assert all(row["summaries"] is None for row in result["specificity"].values())
    accounting = result["execution"]["resource_accounting"]
    assert accounting["continuation_observed_reserved_gpu_hours"] == 0.0
    assert accounting["continuation_maximum_potential_reserved_gpu_hours"] == pytest.approx(54.2)
    assert set(result["limitations"]["job_stop_reasons"]) == set(cc.canonical_job_specs())
    assert not (run_root / "baseline/baseline_bundle.pkl").exists()


def test_freeze_semantic_and_scope_tampering_is_rejected() -> None:
    from freeze_msae_completion_continuation import candidate_paths

    freeze_script = ROOT / "scripts/freeze_msae_completion_continuation.py"
    assert freeze_script in candidate_paths()
    record = {key: "fixture" for key in cc.CONTINUATION_FREEZE_KEYS}
    record.update({
        "schema_version": "atlas_completion_diagnostic_continuation_freeze_v1",
        "evidence_class": "postscore_amended_architecture_evidence",
        "diagnostic_continuation_only": True, "decision_promotion_allowed": False,
        "prescore_clean": True,
    })
    cc.validate_freeze_semantics(record)
    for key, bad in [
        ("diagnostic_continuation_only", False),
        ("decision_promotion_allowed", True),
        ("prescore_clean", False),
        ("evidence_class", "wrong"),
    ]:
        tampered = dict(record); tampered[key] = bad
        with pytest.raises(RuntimeError, match="semantics"):
            cc.validate_freeze_semantics(tampered)
    candidate = {"bundle_files": [{"path": "a", "sha256": "1"}],
                 "bundle_sha256": "candidate"}
    freeze_bundle = {"bundle_files": [{"path": "a", "sha256": "1"},
                                      {"path": "review", "sha256": "2"}],
                     "bundle_sha256": "freeze"}
    scoped = dict(record)
    scoped.update({"reviewed_candidate_files": candidate["bundle_files"],
                   "reviewed_candidate_sha256": candidate["bundle_sha256"],
                   "bundle_files": freeze_bundle["bundle_files"],
                   "bundle_sha256": freeze_bundle["bundle_sha256"]})
    cc.validate_reviewed_freeze_scope(scoped, candidate, freeze_bundle)
    tampered = copy.deepcopy(scoped); tampered["reviewed_candidate_files"] = []
    with pytest.raises(RuntimeError, match="candidate scope"):
        cc.validate_reviewed_freeze_scope(tampered, candidate, freeze_bundle)
    tampered = copy.deepcopy(scoped); tampered["bundle_files"] = candidate["bundle_files"]
    with pytest.raises(RuntimeError, match="file scope"):
        cc.validate_reviewed_freeze_scope(tampered, candidate, freeze_bundle)


def test_auxiliary_runners_reject_noncanonical_root_command_and_cause(tmp_path: Path) -> None:
    job = "g4_point"
    canonical = cc.canonical_gpu_command(job)
    bad_root = subprocess.run(
        ["bash", "scripts/msa_completion_continuation_gpu_runner.sh", str(tmp_path), job,
         str(tmp_path / "log"), *canonical], cwd=ROOT, capture_output=True, text=True)
    assert bad_root.returncode != 0 and "noncanonical continuation run root" in bad_root.stderr
    bad_command = subprocess.run(
        ["bash", "scripts/msa_completion_continuation_gpu_runner.sh", str(cc.RUN_ROOT), job,
         str(cc.RUN_ROOT / "logs" / f"{job}.log"), "/bin/true"],
        cwd=ROOT, capture_output=True, text=True)
    assert bad_command.returncode != 0 and "noncanonical GPU command" in bad_command.stderr
    bad_cause = subprocess.run(
        ["bash", "scripts/msa_completion_continuation_cpu_runner.sh", str(cc.RUN_ROOT),
         "collector", str(cc.RUN_ROOT / "logs/collector.log"),
         ".venv-atlas/bin/python", "scripts/collect_msae_completion_continuation.py",
         "--baseline-failed", "data/atlas_v1/private/final.jsonl"],
        cwd=ROOT, capture_output=True, text=True)
    assert bad_cause.returncode != 0 and "noncanonical CPU command" in bad_cause.stderr


@pytest.mark.parametrize(("case", "expected"), [
    ("timeout", "resource_timeout"), ("sigkill", "process_crash"),
    ("abort", "process_crash"), ("missing_output", "process_crash"),
])
def test_exact_gpu_runner_selftest_publishes_supervisor_closure(
        tmp_path: Path, case: str, expected: str) -> None:
    run = tmp_path / f"runner_{case}"
    env = dict(os.environ, MSAE_CONTINUATION_SUPERVISOR_SELFTEST="1")
    proc = subprocess.run(
        ["bash", "scripts/msa_completion_continuation_gpu_runner.sh",
         "--self-test-supervisor", str(run), case],
        cwd=ROOT, env=env, capture_output=True, text=True, timeout=8)
    assert proc.returncode == 0, proc.stderr
    job = f"selftest_{case}"
    record_path = run / "job_manifests" / (
        f"{job}.resource_timeout.json" if expected == "resource_timeout"
        else f"{job}.process_crash.json")
    terminal_path = run / "job_manifests" / f"{job}.terminal.json"
    record, terminal = json.loads(record_path.read_text()), json.loads(terminal_path.read_text())
    assert terminal["outcome"] == expected and terminal["exit_code"] != 0
    assert record["reason"] == (
        "hard_runtime_supervisor_expired" if expected == "resource_timeout"
        else "uncatchable_process_exit")
    assert record["launch_manifest_sha256"] == sha256_file(Path(record["launch_manifest_path"]))
    assert record["log_sha256"] == sha256_file(Path(record["log_path"]))
    assert record["stage_deadline_sha256"] == sha256_file(Path(record["stage_deadline_path"]))
    assert record["budget_reservation_sha256"] == sha256_file(
        Path(record["budget_reservation_path"]))
    assert cc.terminal_state(run / "stage") is None


def test_gpu_runner_selftest_rejects_missing_guard_and_unknown_case(tmp_path: Path) -> None:
    root = tmp_path / "runner_guard"
    missing = subprocess.run(
        ["bash", "scripts/msa_completion_continuation_gpu_runner.sh",
         "--self-test-supervisor", str(root), "timeout"],
        cwd=ROOT, capture_output=True, text=True)
    assert missing.returncode != 0 and "explicit test guard" in missing.stderr
    unknown = subprocess.run(
        ["bash", "scripts/msa_completion_continuation_gpu_runner.sh",
         "--self-test-supervisor", str(root), "arbitrary"], cwd=ROOT,
        env=dict(os.environ, MSAE_CONTINUATION_SUPERVISOR_SELFTEST="1"),
        capture_output=True, text=True)
    assert unknown.returncode != 0 and "unknown supervisor self-test case" in unknown.stderr


@pytest.mark.parametrize("protected", [
    ROOT,
    cc.SOURCE_RUN,
    cc.RUN_ROOT,
    cc.RESULT_ROOT,
])
def test_gpu_runner_selftest_rejects_pytest_shaped_protected_roots(
        protected: Path) -> None:
    candidate = protected / "pytest-of-f004ndc/pytest-999/selftest_should_not_exist"
    proc = subprocess.run(
        ["bash", "scripts/msa_completion_continuation_gpu_runner.sh",
         "--self-test-supervisor", str(candidate), "missing_output"], cwd=ROOT,
        env=dict(os.environ, MSAE_CONTINUATION_SUPERVISOR_SELFTEST="1"),
        capture_output=True, text=True)
    assert proc.returncode != 0
    assert not candidate.exists()


def test_quantile_null_contract_and_recursive_nonfinite_rejection() -> None:
    from summarize_msae_completion_continuation import quantile_summary
    assert quantile_summary([1.0] * 449, allow=False)["lower_95_one_sided"] is None
    assert quantile_summary([1.0, None], allow=True)["reason"] == "coordinate_unavailable_in_finite_draw_set"
    with pytest.raises(RuntimeError, match="nonfinite"):
        cc.require_recursive_finite({"bad": float("nan")})
    cc.require_recursive_finite({"registered_missing": None, "ok": [1.0]})


def test_plan_review_binds_current_plan() -> None:
    from freeze_msae_completion_continuation import validate_plan_review

    review = json.loads((ROOT / "reports/adversarial/atlas_completion_continuation_plan_review_20260801.json").read_text())
    plan = ROOT / review["plan_path"]
    assert review["verdict"] == "SHIP"
    assert review["plan_sha256"] == hashlib.sha256(plan.read_bytes()).hexdigest()
    validate_plan_review(review)
    tampered = dict(review); tampered["origin"] = "fallback"
    with pytest.raises(RuntimeError, match="exact forked SHIP"):
        validate_plan_review(tampered)
