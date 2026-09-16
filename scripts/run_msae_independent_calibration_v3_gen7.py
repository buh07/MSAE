#!/usr/bin/env python3
"""Authorized calibration-only replay for the exposed-source MSAE v3 protocol."""
from __future__ import annotations
import sys

_early_script_directory = __file__.rpartition("/")[0]
sys.path[:] = [entry for entry in sys.path
               if entry != _early_script_directory
               and not (_early_script_directory == "scripts"
                        and entry.endswith("/scripts"))]

import argparse
import hashlib
import importlib.machinery
import importlib.util
import io
import json
import math
import os
from pathlib import Path
import stat
import traceback
from typing import Any

ROOT = Path(__file__).resolve().parents[1]

# The runner is executed from source, but its first local import must also be
# source-only: ``-B`` otherwise permits an ignored, timestamp-valid controller
# bytecode cache to execute before the authorization gate.  This bootstrap is
# intentionally small and duplicated here because importing a bootstrap module
# through the default finder would recreate the same pre-gate vulnerability.
_SOURCE_ONLY_LOCAL_MODULES = frozenset({
    "msae_independent_measurement_v3",
    "msae_independent_measurement_v3_post_m1",
    "msae_independent_measurement_v3_post_m1_runtime",
    "msae_independent_measurement_v3_post_m2_gen7",
    "msae_independent_measurement_v3_post_m2_gen7_runtime",
    "msae_measurement_remediation_v1",
    "msae_measurement_v2",
    "run_msae_independent_calibration_v3",
    "run_msae_independent_calibration_v3_gen7",
})


def _runner_source_bytes(path: Path) -> bytes:
    directory_fd = os.open(
        path.parent, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC)
    source_fd = -1
    try:
        directory_before = os.fstat(directory_fd)
        directory_path = path.parent.lstat()
        if (not stat.S_ISDIR(directory_before.st_mode)
                or stat.S_ISLNK(directory_path.st_mode)
                or (directory_before.st_dev, directory_before.st_ino) !=
                   (directory_path.st_dev, directory_path.st_ino)
                or directory_before.st_uid != os.getuid()
                or stat.S_IMODE(directory_before.st_mode) & 0o022):
            raise ImportError(f"unsafe runner import directory: {path.parent}")
        source_fd = os.open(
            path.name, os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC,
            dir_fd=directory_fd)
        before = os.fstat(source_fd)
        if (not stat.S_ISREG(before.st_mode) or before.st_uid != os.getuid()
                or before.st_nlink != 1 or stat.S_IMODE(before.st_mode) & 0o022):
            raise ImportError(f"unsafe runner import source: {path}")
        chunks: list[bytes] = []
        while True:
            chunk = os.read(source_fd, 1024 * 1024)
            if not chunk:
                break
            chunks.append(chunk)
        after = os.fstat(source_fd)
        path_after = path.lstat()
        before_identity = (before.st_dev, before.st_ino, before.st_mode, before.st_uid,
                           before.st_nlink, before.st_size, before.st_mtime_ns,
                           before.st_ctime_ns)
        after_identity = (after.st_dev, after.st_ino, after.st_mode, after.st_uid,
                          after.st_nlink, after.st_size, after.st_mtime_ns,
                          after.st_ctime_ns)
        path_identity = (path_after.st_dev, path_after.st_ino, path_after.st_mode,
                         path_after.st_uid, path_after.st_nlink, path_after.st_size,
                         path_after.st_mtime_ns, path_after.st_ctime_ns)
        if before_identity != after_identity or after_identity != path_identity:
            raise ImportError(f"runner import source changed during read: {path}")
        directory_after = os.fstat(directory_fd)
        if ((directory_before.st_dev, directory_before.st_ino,
             directory_before.st_mode, directory_before.st_uid) !=
                (directory_after.st_dev, directory_after.st_ino,
                 directory_after.st_mode, directory_after.st_uid)):
            raise ImportError(f"runner import directory changed during read: {path.parent}")
        raw = b"".join(chunks)
        if len(raw) != before.st_size:
            raise ImportError(f"short runner import source read: {path}")
        return raw
    finally:
        if source_fd >= 0:
            os.close(source_fd)
        os.close(directory_fd)


class _RunnerSourceOnlyLoader(importlib.machinery.SourceFileLoader):
    def __init__(self, fullname: str, source: Path):
        self.source = Path(source)
        super().__init__(fullname, str(self.source))

    def path_stats(self, path: str) -> dict[str, Any]:
        del path
        raise OSError("runner local module has no bytecode-cache metadata")

    def set_data(self, path: str, data: bytes, **kwargs: Any) -> None:
        del path, data, kwargs
        return None

    def get_data(self, path: str) -> bytes:
        if Path(path) != self.source:
            raise OSError(f"runner source-only loader rejected non-source path: {path}")
        return _runner_source_bytes(self.source)


class _RunnerSourceOnlyFinder:
    _msae_source_only_finder = True

    def __init__(self, scripts: Path):
        self.scripts = Path(scripts)

    def find_spec(self, fullname: str, path: Any = None, target: Any = None) -> Any:
        del path, target
        if fullname not in _SOURCE_ONLY_LOCAL_MODULES:
            return None
        source = self.scripts / f"{fullname}.py"
        loader = _RunnerSourceOnlyLoader(fullname, source)
        spec = importlib.util.spec_from_loader(fullname, loader, origin=str(source))
        if spec is None or spec.loader is None:
            raise ImportError(f"cannot construct runner source-only spec: {fullname}")
        spec.has_location = True
        spec.cached = None
        return spec


_runner_scripts = str(ROOT / "scripts")
sys.path[:] = [entry for entry in sys.path if entry != _runner_scripts]
_existing_source_finders = [
    finder for finder in sys.meta_path
    if finder.__class__.__dict__.get("_msae_source_only_finder") is True
]
if _existing_source_finders:
    if (len(_existing_source_finders) != 1
            or Path(_existing_source_finders[0].scripts) != ROOT / "scripts"):
        raise ImportError("runner inherited a conflicting source-only finder")
else:
    sys.meta_path.insert(0, _RunnerSourceOnlyFinder(ROOT / "scripts"))
import msae_independent_measurement_v3_post_m2_gen7 as protocol
import msae_independent_measurement_v3_post_m2_gen7_runtime as runtime
protocol.sanitize_local_module_search_path()


def create_json(path: Path, value: Any) -> None:
    protocol.write_once(path, protocol.canonical_bytes(value))


def save_npy_once(path: Path, value: Any) -> tuple[str, int]:
    import numpy as np
    buffer = io.BytesIO()
    np.save(buffer, value, allow_pickle=False)
    raw = buffer.getvalue()
    protocol.write_once(path, raw)
    return hashlib.sha256(raw).hexdigest(), len(raw)


def forward(model: Any, units: list[dict[str, Any]], device: str) -> tuple[Any, list[str]]:
    import numpy as np
    import torch
    values = []
    rows: list[str] = []
    for start in range(0, len(units), 8):
        batch = units[start:start + 8]
        width = max(len(unit["input_ids"]) for unit in batch)
        ids = torch.zeros((len(batch), width), dtype=torch.long, device=device)
        attention = torch.zeros_like(ids)
        for i, unit in enumerate(batch):
            length = len(unit["input_ids"])
            ids[i, :length] = torch.tensor(unit["input_ids"], dtype=torch.long, device=device)
            attention[i, :length] = 1
        with torch.inference_mode():
            hidden = model(ids, attention_mask=attention, output_hidden_states=True,
                           use_cache=False).hidden_states[3]
        for i, unit in enumerate(batch):
            positions = torch.tensor(unit["positions"], dtype=torch.long, device=device)
            values.append(hidden[i, positions].float().cpu().numpy())
            rows.extend(unit["row_ids"])
    return np.ascontiguousarray(np.concatenate(values, axis=0), dtype=np.float32), rows


def selector_ok(a: Any, b: Any, atol: str, rtol: str) -> tuple[bool, float]:
    import numpy as np
    if a.shape != b.shape or a.dtype != np.float32 or b.dtype != np.float32:
        return False, float("inf")
    aa = a.astype(np.float64)
    bb = b.astype(np.float64)
    if not np.isfinite(aa).all() or not np.isfinite(bb).all():
        return False, float("inf")
    try:
        absolute_tolerance = float(atol)
        relative_tolerance = float(rtol)
    except (TypeError, ValueError, OverflowError):
        return False, float("inf")
    if (not math.isfinite(absolute_tolerance) or not math.isfinite(relative_tolerance)
            or absolute_tolerance < 0 or relative_tolerance < 0):
        return False, float("inf")
    difference = np.abs(aa - bb)
    scale = np.maximum(np.abs(aa), np.abs(bb))
    with np.errstate(over="raise", invalid="raise"):
        try:
            bound = absolute_tolerance + relative_tolerance * scale
            if not np.isfinite(bound).all():
                return False, float("inf")
            ok = bool(np.all(2.0 * difference <= bound))
        except FloatingPointError:
            return False, float("inf")
    return ok, float(difference.max(initial=0.0))


def observation(meta: dict[str, Any], evaluation_id: str, values: Any, rows: list[str]) -> dict[str, Any]:
    from msae_measurement_remediation_v1 import payload_sha256
    return {**{key: meta[key] for key in (
        "stratum_id", "source_role", "source_revision", "partition", "model_id",
        "checkpoint_id", "code_sha256", "environment_sha256", "dtype", "pooling_path",
        "row_ids_sha256", "input_sha256")},
        "evaluation_id": evaluation_id, "row_ids": rows, "values": values,
        "payload_sha256": payload_sha256(values, rows)}


def evidence(config_sha: str, name: str, status: str, observed: Any, artifact_sha: str, reasons: list[str]) -> dict[str, Any]:
    return {"schema_version": "msae_endpoint_evidence_v1", "protocol_config_sha256": config_sha,
            "endpoint_name": name, "category": "stage_b", "status": status,
            "reasons": reasons, "evidence_artifact_sha256": artifact_sha, "observed_value": observed}


def _write_failure(run: Path, error: BaseException) -> None:
    failure = {"schema_version": "msae_v3_technical_failure_v3", "protocol_id": protocol.PROTOCOL,
               "status": "not_run", "error_type": type(error).__name__, "error": str(error),
               "traceback": traceback.format_exc(), "stage_b_written": False}
    runtime.commit_terminal_failure(run, failure)


def _validated_failure_run_root(raw_run_root: str) -> Path | None:
    """Return only the exact signed run root; never write to caller-chosen paths."""
    if raw_run_root != runtime.ACTIVE_RUN_REL:
        return None
    candidate = ROOT / raw_run_root
    try:
        if candidate.resolve(strict=True) != runtime.ACTIVE_RUN_ROOT.resolve(strict=True):
            return None
        st = candidate.lstat()
    except (FileNotFoundError, OSError):
        return None
    if (not stat.S_ISDIR(st.st_mode) or stat.S_ISLNK(st.st_mode)
            or stat.S_IMODE(st.st_mode) != 0o700 or st.st_uid != os.getuid()):
        return None
    return candidate


def run(args: argparse.Namespace) -> None:
    import numpy as np
    run_root = (ROOT / args.run_root).resolve(strict=True)
    if run_root != runtime.ACTIVE_RUN_ROOT.resolve(strict=True):
        raise ValueError("unexpected run root")
    if os.environ.get("CUDA_VISIBLE_DEVICES") != args.gpu_uuid:
        raise ValueError("CUDA UUID environment binding mismatch")
    lease_environment = os.environ.get("MSAE_LEASE_FD", "")
    if not lease_environment.isdecimal():
        raise ValueError("missing inherited GPU lease FD")
    expected_environment = runtime.worker_environment(
        args.gpu_uuid, int(lease_environment), args.readiness_fd,
        args.final_ack_fd, args.confirmed_fd)
    if dict(os.environ) != expected_environment:
        raise ValueError("deterministic/offline worker environment mismatch")
    stage_a = runtime.validate_stage_a()
    lease_fd = int(lease_environment)
    lease_stat = os.fstat(lease_fd)
    strict_lock = runtime._validate_gpu_lock_fd(lease_fd, args.gpu_uuid)
    lock_record = protocol.read_json(run_root / "lock_acquired.json")
    if protocol.sha_file(runtime.LAUNCH_INTENT) != lock_record.get("launcher_intent_sha256"):
        raise ValueError("worker launcher-intent lineage mismatch")
    if (lease_stat.st_dev, lease_stat.st_ino) != (lock_record["lock_device"], lock_record["lock_inode"]):
        raise ValueError("inherited lease FD identity mismatch")
    if strict_lock != {"device": lock_record["lock_device"], "inode": lock_record["lock_inode"]}:
        raise ValueError("strict inherited lease validation/record mismatch")
    commitment = protocol.read_json(runtime.ACTIVE_CONFIG / "authorization_commitment.json")
    lock_directory_fd = os.open(protocol.GPU_LOCK_DIR,
                                os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC)
    try:
        directory_stat = os.fstat(lock_directory_fd)
        directory_path_stat = protocol.GPU_LOCK_DIR.lstat()
        directory_expected = commitment["gpu_lock_directory"]
        if ((directory_stat.st_dev, directory_stat.st_ino) !=
                (directory_path_stat.st_dev, directory_path_stat.st_ino)
                or (directory_stat.st_dev, directory_stat.st_ino, directory_stat.st_uid,
                    stat.S_IMODE(directory_stat.st_mode), directory_stat.st_nlink) !=
                   (directory_expected["device"], directory_expected["inode"],
                    directory_expected["uid"], directory_expected["mode"],
                    directory_expected["nlink"])):
            raise ValueError("worker GPU lock-directory binding mismatch")
        lock_name = f"{protocol.sha_bytes(args.gpu_uuid.encode('ascii'))}.lock"
        lock_probe = os.open(lock_name, os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC,
                             dir_fd=lock_directory_fd)
        try:
            lock_probe_stat = os.fstat(lock_probe)
        finally:
            os.close(lock_probe)
        lock_path_stat = (protocol.GPU_LOCK_DIR / lock_name).lstat()
        if ((lease_stat.st_dev, lease_stat.st_ino) !=
                (lock_probe_stat.st_dev, lock_probe_stat.st_ino)
                or (lease_stat.st_dev, lease_stat.st_ino) !=
                   (lock_path_stat.st_dev, lock_path_stat.st_ino)
                or not stat.S_ISREG(lease_stat.st_mode) or stat.S_ISLNK(lock_path_stat.st_mode)
                or stat.S_IMODE(lease_stat.st_mode) != 0o600
                or lease_stat.st_uid != os.getuid() or lease_stat.st_nlink != 1):
            raise ValueError("worker GPU lease FD/path/type/mode/ownership mismatch")
    finally:
        os.close(lock_directory_fd)
    if (lock_record.get("schema_version") != "msae_v3_lock_acquired_v2"
            or lock_record["gpu_uuid"] != args.gpu_uuid or lock_record["broker_pid"] != args.broker_pid):
        raise ValueError("lease lineage mismatch")
    if protocol._start_ticks(args.broker_pid) != lock_record["broker_start_ticks"]:
        raise ValueError("broker PID/start-ticks mismatch")
    if os.getpgrp() != lock_record["worker_pgid"] or os.getpid() != lock_record["worker_pid"]:
        raise ValueError("worker PID/process-group mismatch")
    authorization = runtime.verify_authorization(run_root / "authorization.json", consume=True, run_root=run_root)
    create_json(run_root / "observed_environment.json", {
        "schema_version": "msae_v3_observed_environment_v1", "protocol_id": protocol.PROTOCOL,
        "stage_a_sha256": protocol.sha_file(runtime.ACTIVE_PROV / "stage_a.json"),
        "authorization_envelope_sha256": authorization["envelope_sha256"],
        "gpu_uuid_requested": args.gpu_uuid, "broker_pid": args.broker_pid,
        "python_executable": str(Path(sys.executable).resolve()),
        "deterministic_offline_environment": expected_environment,
    })
    config_path = runtime.ACTIVE_CONFIG / "protocol.json"
    config_raw = config_path.read_bytes()
    config_sha = protocol.sha_bytes(config_raw)
    config = json.loads(config_raw)
    if config_sha != stage_a["protocol_config_sha256"]:
        raise ValueError("protocol config drift")
    generic_config = runtime.generic_config_projection(config)
    generic_config_raw = protocol.canonical_bytes(generic_config)
    generic_config_sha = protocol.sha_bytes(generic_config_raw)
    closure = protocol.read_json(runtime.ACTIVE_M4_DATA / "dependency_closure.json")
    local_entries = {item["path"]: item for item in closure["entries"]}
    expected_runner = local_entries["scripts/run_msae_independent_calibration_v3_gen7.py"]["sha256"]
    if protocol.sha_file(Path(__file__)) != expected_runner:
        raise ValueError("runner code drift")
    closure = runtime.verify_dependency_closure()
    frozen_path = ROOT / "data/msae_independent_measurement_v1/calibration_strata.json"
    frozen = protocol.read_json(frozen_path)
    inference_path = ROOT / frozen["source_path"]
    if protocol.sha_file(inference_path) != frozen["source_sha256"]:
        raise ValueError("frozen calibration source digest drift")
    inference_units = [json.loads(line) for line in inference_path.read_text(encoding="utf-8").splitlines()]
    pair_path = inference_path.with_name("pairs.jsonl")
    pair_registry = [json.loads(line) for line in pair_path.read_text(encoding="utf-8").splitlines()]
    alignment = protocol.counterfactual_alignment_qa(frozen, inference_units, pair_registry)
    pre_import_native_realization = runtime.verify_runtime_loaded_libraries(closure)
    readiness_fd = args.readiness_fd
    if os.environ.get("MSAE_READINESS_FD") != str(readiness_fd):
        raise ValueError("runner readiness FD environment/argv mismatch")
    if not stat.S_ISFIFO(os.fstat(readiness_fd).st_mode):
        raise ValueError("runner readiness descriptor is not a pipe")
    if (os.environ.get("MSAE_FINAL_ACK_FD") != str(args.final_ack_fd)
            or os.environ.get("MSAE_CONFIRMED_FD") != str(args.confirmed_fd)
            or not stat.S_ISFIFO(os.fstat(args.final_ack_fd).st_mode)
            or not stat.S_ISFIFO(os.fstat(args.confirmed_fd).st_mode)):
        raise ValueError("runner final-ack/confirmation descriptor mismatch")
    readiness = {
        "schema_version": "msae_v3_runner_ready_v1", "protocol_id": protocol.PROTOCOL,
        "worker_pid": os.getpid(), "worker_pgid": os.getpgrp(),
        "broker_pid": args.broker_pid, "gpu_uuid": args.gpu_uuid,
        "stage_a_sha256": protocol.sha_file(runtime.ACTIVE_PROV / "stage_a.json"),
        "protocol_config_sha256": config_sha,
        "dependency_closure_sha256": protocol.sha_file(runtime.ACTIVE_M4_DATA / "dependency_closure.json"),
        "authorization_envelope_sha256": authorization["envelope_sha256"],
        "nonce_attestation_sha256": protocol.sha_file(run_root / "nonce_consumed.json"),
        "pre_model": True,
    }
    os.write(readiness_fd, protocol.canonical_bytes(readiness))
    os.close(readiness_fd)
    runtime.confirm_pre_model_gate(args.final_ack_fd, args.confirmed_fd)
    # No torch import occurs before all authorization, nonce, closure, config, and
    # Stage-A checks and the durable launcher handoff above have passed.
    import torch
    torch.use_deterministic_algorithms(True)
    torch.backends.cuda.matmul.allow_tf32 = False
    torch.backends.cudnn.allow_tf32 = False
    torch.set_float32_matmul_precision("highest")
    post_torch_native_realization = runtime.verify_runtime_loaded_libraries(closure)
    if torch.cuda.device_count() != 1:
        raise ValueError("expected exactly one UUID-scoped visible GPU")
    properties = torch.cuda.get_device_properties(0)
    actual_uuid = str(getattr(properties, "uuid", ""))
    if actual_uuid.lower().replace("gpu-", "") != args.gpu_uuid.lower().replace("gpu-", ""):
        raise ValueError(f"runtime GPU UUID mismatch: {actual_uuid}")
    from transformers import AutoModelForCausalLM
    model = AutoModelForCausalLM.from_pretrained(str(protocol.SNAPSHOT), local_files_only=True,
                                                  torch_dtype=torch.float16).to("cuda").eval()
    post_model_native_realization = runtime.verify_runtime_loaded_libraries(closure)
    observations: dict[str, Any] = {}
    references: dict[str, tuple[Any, list[str]]] = {}
    cache_records = []
    cache_root = run_root / "cache"
    cache_root.mkdir(mode=0o700, parents=False, exist_ok=False)
    os.chmod(cache_root, 0o700)
    protocol._fsync_directory(run_root)
    for meta in config["replay"]["strata"]:
        sid = meta["stratum_id"]
        units = frozen["strata"][sid]["units"]
        observations[sid] = {}
        evaluations = [meta["reference_evaluation_id"], *meta["repeat_evaluation_ids"]]
        cache_dir = run_root / "cache" / sid
        cache_dir.mkdir(mode=0o700, parents=False, exist_ok=False)
        os.chmod(cache_dir, 0o700)
        protocol._fsync_directory(cache_root)
        os.chmod(cache_dir.parent, 0o700)
        os.chmod(cache_dir, 0o700)
        for index, evaluation_id in enumerate(evaluations):
            values, rows = forward(model, units, "cuda")
            if protocol.sha_bytes(protocol.canonical_bytes(rows)) != meta["row_ids_sha256"]:
                raise ValueError(f"runtime row order drift: {sid}")
            path = cache_dir / f"forward_{index}.npy"
            digest, size = save_npy_once(path, values)
            loaded = np.load(path, allow_pickle=False)
            redigest = protocol.sha_file(path)
            exact = digest == redigest and loaded.dtype == np.float32 and loaded.shape == values.shape and np.array_equal(loaded, values)
            if not exact:
                raise ValueError(f"cached no-op byte/payload replay failure: {sid}/{index}")
            cache_records.append({"stratum_id": sid, "evaluation_id": evaluation_id,
                                  "path": str(path.relative_to(ROOT)), "sha256": digest,
                                  "bytes": size, "dtype": str(values.dtype), "shape": list(values.shape),
                                  "row_ids_sha256": meta["row_ids_sha256"], "exact_reload": exact})
            observations[sid][evaluation_id] = observation(meta, evaluation_id, values, rows)
            if index == 0:
                references[sid] = (values, rows)
    bundle = {
        "schema_version": "msae_calibration_replay_bundle_v1",
        "protocol_config_sha256": config_sha,
        "replay_registry_sha256": protocol.sha_bytes(protocol.canonical_bytes(config["replay"]["strata"])),
        "source_role": config["replay"]["source_role"],
        "source_revision": config["replay"]["source_revision"],
        "partition": config["replay"]["partition"], "observations": observations,
    }
    generic_bundle = runtime.generic_replay_bundle(bundle, generic_config_sha)
    from msae_measurement_remediation_v1 import build_stage_b, select_replay_tolerance
    selection = select_replay_tolerance(generic_config_raw, generic_config_sha, generic_bundle)
    selected = selection["selected_tolerance"]
    selection_record = {**selection, "selector_inequality": "2*abs(a-b)<=atol+rtol*max(abs(a),abs(b))",
                        "array_allclose_forbidden": True}
    create_json(run_root / "tolerance_selection.json", selection_record)
    selection_sha = protocol.sha_file(run_root / "tolerance_selection.json")
    noop = {"schema_version": "msae_v3_cached_noop_hash_replay_v1", "status": "eligible",
            "cache_records": cache_records}
    create_json(run_root / "cached_noop_hash_replay.json", noop)
    noop_sha = protocol.sha_file(run_root / "cached_noop_hash_replay.json")
    pooling_rows = []
    pooling_ok = selected is not None
    for meta in config["replay"]["strata"]:
        sid = meta["stratum_id"]
        pieces = []
        rows: list[str] = []
        for unit in frozen["strata"][sid]["units"]:
            values, unit_rows = forward(model, [unit], "cuda")
            pieces.append(values)
            rows.extend(unit_rows)
        per_unit = np.concatenate(pieces, axis=0)
        pooling_path = run_root / "cache" / sid / "pooling_per_unit.npy"
        pooling_digest, pooling_bytes = save_npy_once(pooling_path, per_unit)
        reference, ref_rows = references[sid]
        if rows != ref_rows:
            pooling_ok = False
            ok, maximum = False, None
        elif selected is None:
            ok = False
            maximum = float(np.max(np.abs(reference.astype(np.float64) -
                                          per_unit.astype(np.float64)), initial=0.0))
        else:
            ok, maximum = selector_ok(reference, per_unit, str(selected[0]), str(selected[1]))
            pooling_ok &= ok
        pooling_rows.append({"stratum_id": sid, "row_ids_sha256": protocol.sha_bytes(protocol.canonical_bytes(rows)),
                             "path": str(pooling_path.relative_to(ROOT)), "sha256": pooling_digest,
                             "bytes": pooling_bytes, "dtype": str(per_unit.dtype),
                             "shape": list(per_unit.shape),
                             "reference_payload_sha256": observations[sid][meta["reference_evaluation_id"]]["payload_sha256"],
                             "unit_payload_sha256": observation(meta, "unit_replay", per_unit, rows)["payload_sha256"],
                             "max_abs": maximum, "selector_pass": ok})
        protocol._fsync_directory(pooling_path.parent)
    pooling = {"schema_version": "msae_v3_canonical_pooling_qa_v1",
               "status": "eligible" if pooling_ok else "ineligible", "strata": pooling_rows,
               "selected_tolerance": selected,
               "reasons": [] if pooling_ok else (["no_registered_tolerance"] if selected is None
                                                   else ["unit_batch_selector_failure"])}
    create_json(run_root / "canonical_pooling_qa.json", pooling)
    pooling_sha = protocol.sha_file(run_root / "canonical_pooling_qa.json")
    alignment_ok = alignment["status"] == "eligible"
    pair_rows = alignment["pairs"]
    create_json(run_root / "counterfactual_cache_alignment_qa.json", alignment)
    alignment_sha = protocol.sha_file(run_root / "counterfactual_cache_alignment_qa.json")
    stage_evidence = {
        "cached_noop_hash_replay": evidence(generic_config_sha, "cached_noop_hash_replay", noop["status"],
                                               {"byte_exact": noop["status"] == "eligible"}, noop_sha, []),
        "canonical_pooling_qa": evidence(generic_config_sha, "canonical_pooling_qa", pooling["status"],
                                           {"selected_tolerance": selected, "strata": pooling_rows}, pooling_sha,
                                           [] if pooling_ok else (["no_registered_tolerance"] if selected is None
                                                                  else ["unit_batch_selector_failure"])),
        "counterfactual_cache_alignment_qa": evidence(generic_config_sha, "counterfactual_cache_alignment_qa", alignment["status"],
                                                        {"alignment_valid": alignment_ok, "pair_count": len(pair_rows),
                                                         "frozen_strata_payload_sha256": alignment["frozen_strata_payload_sha256"],
                                                         "source_inference_units_payload_sha256": alignment["source_inference_units_payload_sha256"],
                                                         "source_pair_registry_payload_sha256": alignment["source_pair_registry_payload_sha256"]}, alignment_sha,
                                                        [] if alignment_ok else ["typed_pair_alignment_failure"]),
    }
    typed_qa = runtime.validate_stage_b_typed_qa(run_root, config, bundle, selection)
    typed_qa["tolerance_selection_sha256"] = selection_sha
    typed_qa["outer_protocol_config_sha256"] = config_sha
    typed_qa["generic_protocol_config_sha256"] = generic_config_sha
    base_stage_b = build_stage_b(generic_config_raw, generic_config_sha,
                                 stage_a["base_stage_a"], generic_bundle, stage_evidence)
    if runtime._validate_gpu_lock_fd(lease_fd, args.gpu_uuid) != strict_lock:
        raise ValueError("final GPU lease identity drift")
    final_native_realization = runtime.verify_runtime_loaded_libraries(closure)
    native_realizations = {
        "pre_import": pre_import_native_realization,
        "post_torch": post_torch_native_realization,
        "post_model": post_model_native_realization,
        "final": final_native_realization,
    }
    native_raw = {name: protocol.canonical_bytes(payload)
                  for name, payload in native_realizations.items()}
    stage_b = {"schema_version": "msae_exposed_source_stage_b_v4", "protocol_id": protocol.PROTOCOL,
               "prior_stage_sha256": protocol.sha_file(runtime.ACTIVE_PROV / "stage_a.json"),
               "base_stage_b": base_stage_b, "typed_qa": typed_qa,
               "runtime_native_realization_sha256": {
                   name: protocol.sha_bytes(raw) for name, raw in native_raw.items()},
               "stage_ready": bool(base_stage_b["stage_ready"] and pooling_ok and alignment_ok)}
    stage_raw = protocol.canonical_bytes(stage_b)
    status = {"schema_version": "msae_v3_runtime_status_v2",
              "status": "eligible" if stage_b["stage_ready"] else "ineligible",
              "stage_b_ready": stage_b["stage_ready"],
              "stage_b_sha256": protocol.sha_bytes(stage_raw)}
    runtime.commit_terminal_success(run_root, {
        "stage_b.json": stage_raw, "status.json": protocol.canonical_bytes(status),
        **{f"runtime_native_{name}.json": raw for name, raw in native_raw.items()}})


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-root", required=True)
    parser.add_argument("--gpu-uuid", required=True)
    parser.add_argument("--broker-pid", required=True, type=int)
    parser.add_argument("--readiness-fd", required=True, type=int)
    parser.add_argument("--final-ack-fd", required=True, type=int)
    parser.add_argument("--confirmed-fd", required=True, type=int)
    args = parser.parse_args()
    try:
        run(args)
    except BaseException as error:
        run_root = _validated_failure_run_root(args.run_root)
        if run_root is not None:
            _write_failure(run_root, error)
        raise


if __name__ == "__main__":
    main()
