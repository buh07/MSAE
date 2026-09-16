#!/usr/bin/env python3
"""Authorized calibration-only replay for the exposed-source MSAE v2 protocol."""
from __future__ import annotations
import argparse
import hashlib
import io
import json
import os
from pathlib import Path
import sys
import traceback
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import msae_independent_measurement_v2 as v2


def create_json(path: Path, value: Any) -> None:
    v2.write_once(path, v2.canonical_bytes(value))


def save_npy_once(path: Path, value: Any) -> tuple[str, int]:
    import numpy as np
    buffer = io.BytesIO()
    np.save(buffer, value, allow_pickle=False)
    raw = buffer.getvalue()
    v2.write_once(path, raw)
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
    difference = np.abs(aa - bb)
    scale = np.maximum(np.abs(aa), np.abs(bb))
    with np.errstate(over="raise", invalid="raise"):
        try:
            bound = float(atol) + float(rtol) * scale
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
    failure = {"schema_version": "msae_v2_technical_failure_v1", "protocol_id": v2.PROTOCOL,
               "status": "not_run", "error_type": type(error).__name__, "error": str(error),
               "traceback": traceback.format_exc(), "stage_b_written": False}
    try:
        create_json(run / "technical_failure.json", failure)
    except FileExistsError:
        pass
    try:
        create_json(run / "status.json", {"schema_version": "msae_v2_runtime_status_v1",
                                           "status": "technical_failure_not_run", "stage_b_ready": False})
    except FileExistsError:
        pass


def run(args: argparse.Namespace) -> None:
    import numpy as np
    run_root = (ROOT / args.run_root).resolve(strict=True)
    if run_root != v2.RUN_ROOT.resolve(strict=True):
        raise ValueError("unexpected run root")
    if os.environ.get("CUDA_VISIBLE_DEVICES") != args.gpu_uuid:
        raise ValueError("CUDA UUID environment binding mismatch")
    stage_a = v2.validate_stage_a()
    lease_raw = os.environ.get("MSAE_LEASE_FD")
    if lease_raw is None or not lease_raw.isdecimal():
        raise ValueError("missing inherited GPU lease FD")
    lease_fd = int(lease_raw)
    lease_stat = os.fstat(lease_fd)
    lock_record = v2.read_json(run_root / "lock_acquired.json")
    if (lease_stat.st_dev, lease_stat.st_ino) != (lock_record["lock_device"], lock_record["lock_inode"]):
        raise ValueError("inherited lease FD identity mismatch")
    if lock_record["gpu_uuid"] != args.gpu_uuid or lock_record["broker_pid"] != args.broker_pid:
        raise ValueError("lease lineage mismatch")
    if v2._start_ticks(args.broker_pid) != lock_record["broker_start_ticks"]:
        raise ValueError("broker PID/start-ticks mismatch")
    if os.getpgrp() != lock_record["worker_pgid"] or os.getpid() != lock_record["worker_pid"]:
        raise ValueError("worker PID/process-group mismatch")
    authorization = v2.verify_authorization(run_root / "authorization.json", consume=True, run_root=run_root)
    create_json(run_root / "observed_environment.json", {
        "schema_version": "msae_v2_observed_environment_v1", "protocol_id": v2.PROTOCOL,
        "stage_a_sha256": v2.sha_file(v2.V2_PROV / "stage_a.json"),
        "authorization_envelope_sha256": authorization["envelope_sha256"],
        "gpu_uuid_requested": args.gpu_uuid, "broker_pid": args.broker_pid,
        "python_executable": str(Path(sys.executable).resolve()),
    })
    config_path = v2.V2_CONFIG / "protocol.json"
    config_raw = config_path.read_bytes()
    config_sha = v2.sha_bytes(config_raw)
    config = json.loads(config_raw)
    if config_sha != stage_a["protocol_config_sha256"]:
        raise ValueError("protocol config drift")
    closure = v2.read_json(v2.V2_DATA / "dependency_closure.json")
    local_entries = {item["path"]: item for item in closure["entries"]}
    expected_runner = local_entries["scripts/run_msae_independent_calibration_v2.py"]["sha256"]
    if v2.sha_file(Path(__file__)) != expected_runner:
        raise ValueError("runner code drift")
    # No torch import occurs before all authorization, nonce, closure, config, and
    # Stage-A checks above have passed.
    import torch
    torch.use_deterministic_algorithms(True)
    torch.backends.cuda.matmul.allow_tf32 = False
    torch.backends.cudnn.allow_tf32 = False
    torch.set_float32_matmul_precision("highest")
    if torch.cuda.device_count() != 1:
        raise ValueError("expected exactly one UUID-scoped visible GPU")
    properties = torch.cuda.get_device_properties(0)
    actual_uuid = str(getattr(properties, "uuid", ""))
    if actual_uuid.lower().replace("gpu-", "") != args.gpu_uuid.lower().replace("gpu-", ""):
        raise ValueError(f"runtime GPU UUID mismatch: {actual_uuid}")
    from transformers import AutoModelForCausalLM
    model = AutoModelForCausalLM.from_pretrained(str(v2.SNAPSHOT), local_files_only=True,
                                                  torch_dtype=torch.float16).to("cuda").eval()
    frozen = v2.read_json(ROOT / "data/msae_independent_measurement_v1/calibration_strata.json")
    observations: dict[str, Any] = {}
    references: dict[str, tuple[Any, list[str]]] = {}
    cache_records = []
    for meta in config["replay"]["strata"]:
        sid = meta["stratum_id"]
        units = frozen["strata"][sid]["units"]
        observations[sid] = {}
        evaluations = [meta["reference_evaluation_id"], *meta["repeat_evaluation_ids"]]
        cache_dir = run_root / "cache" / sid
        cache_dir.mkdir(mode=0o700, parents=True, exist_ok=False)
        for index, evaluation_id in enumerate(evaluations):
            values, rows = forward(model, units, "cuda")
            if v2.sha_bytes(v2.canonical_bytes(rows)) != meta["row_ids_sha256"]:
                raise ValueError(f"runtime row order drift: {sid}")
            path = cache_dir / f"forward_{index}.npy"
            digest, size = save_npy_once(path, values)
            loaded = np.load(path, allow_pickle=False)
            redigest = v2.sha_file(path)
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
        "replay_registry_sha256": v2.sha_bytes(v2.canonical_bytes(config["replay"]["strata"])),
        "source_role": config["replay"]["source_role"],
        "source_revision": config["replay"]["source_revision"],
        "partition": config["replay"]["partition"], "observations": observations,
    }
    from msae_measurement_remediation_v1 import build_stage_b, select_replay_tolerance
    selection = select_replay_tolerance(config_raw, config_sha, bundle)
    selected = selection["selected_tolerance"]
    selection_record = {**selection, "selector_inequality": "2*abs(a-b)<=atol+rtol*max(abs(a),abs(b))",
                        "array_allclose_forbidden": True}
    create_json(run_root / "tolerance_selection.json", selection_record)
    selection_sha = v2.sha_file(run_root / "tolerance_selection.json")
    noop = {"schema_version": "msae_v2_cached_noop_hash_replay_v1", "status": "eligible",
            "cache_records": cache_records}
    create_json(run_root / "cached_noop_hash_replay.json", noop)
    noop_sha = v2.sha_file(run_root / "cached_noop_hash_replay.json")
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
        reference, ref_rows = references[sid]
        if rows != ref_rows:
            pooling_ok = False
            ok, maximum = False, float("inf")
        elif selected is None:
            ok, maximum = False, float("inf")
        else:
            ok, maximum = selector_ok(reference, per_unit, str(selected["atol"]), str(selected["rtol"]))
            pooling_ok &= ok
        pooling_rows.append({"stratum_id": sid, "row_ids_sha256": v2.sha_bytes(v2.canonical_bytes(rows)),
                             "reference_payload_sha256": observations[sid][meta["reference_evaluation_id"]]["payload_sha256"],
                             "unit_payload_sha256": observation(meta, "unit_replay", per_unit, rows)["payload_sha256"],
                             "max_abs": maximum, "selector_pass": ok})
    pooling = {"schema_version": "msae_v2_canonical_pooling_qa_v1",
               "status": "eligible" if pooling_ok else "ineligible", "strata": pooling_rows,
               "selected_tolerance": selected}
    create_json(run_root / "canonical_pooling_qa.json", pooling)
    pooling_sha = v2.sha_file(run_root / "canonical_pooling_qa.json")
    pair_rows = []
    alignment_ok = True
    for sid in ("pair_context", "pair_entity"):
        units = frozen["strata"][sid]["units"]
        if len(units) != 16:
            alignment_ok = False
        for index in range(0, len(units), 2):
            source, target = units[index:index + 2]
            source_id, target_id = source["unit_id"], target["unit_id"]
            pair_id_ok = source_id.endswith(":source") and target_id.endswith(":target") and source_id[:-7] == target_id[:-7]
            row_ok = len(source["row_ids"]) == len(target["row_ids"])
            input_ok = all(key in source and key in target for key in ("input_ids", "positions", "row_ids"))
            alignment_ok &= pair_id_ok and row_ok and input_ok
            pair_rows.append({"stratum_id": sid, "pair_id": source_id[:-7] if pair_id_ok else None,
                              "source_unit_id": source_id, "target_unit_id": target_id,
                              "source_input_sha256": v2.sha_bytes(v2.canonical_bytes(source["input_ids"])),
                              "target_input_sha256": v2.sha_bytes(v2.canonical_bytes(target["input_ids"])),
                              "source_row_ids_sha256": v2.sha_bytes(v2.canonical_bytes(source["row_ids"])),
                              "target_row_ids_sha256": v2.sha_bytes(v2.canonical_bytes(target["row_ids"])),
                              "pair_id_valid": pair_id_ok, "row_count_valid": row_ok,
                              "mapping_valid": pair_id_ok and row_ok and input_ok})
    alignment = {"schema_version": "msae_v2_counterfactual_cache_alignment_qa_v1",
                 "status": "eligible" if alignment_ok else "ineligible", "pairs": pair_rows}
    create_json(run_root / "counterfactual_cache_alignment_qa.json", alignment)
    alignment_sha = v2.sha_file(run_root / "counterfactual_cache_alignment_qa.json")
    stage_evidence = {
        "cached_noop_hash_replay": evidence(config_sha, "cached_noop_hash_replay", noop["status"],
                                               {"byte_exact": noop["status"] == "eligible"}, noop_sha, []),
        "canonical_pooling_qa": evidence(config_sha, "canonical_pooling_qa", pooling["status"],
                                           {"selected_tolerance": selected, "strata": pooling_rows}, pooling_sha,
                                           [] if pooling_ok else ["unit_batch_selector_failure"]),
        "counterfactual_cache_alignment_qa": evidence(config_sha, "counterfactual_cache_alignment_qa", alignment["status"],
                                                        {"alignment_valid": alignment_ok, "pair_count": len(pair_rows)}, alignment_sha,
                                                        [] if alignment_ok else ["typed_pair_alignment_failure"]),
    }
    base_stage_b = build_stage_b(config_raw, config_sha, stage_a["base_stage_a"], bundle, stage_evidence)
    stage_b = {"schema_version": "msae_exposed_source_stage_b_v2", "protocol_id": v2.PROTOCOL,
               "prior_stage_sha256": v2.sha_file(v2.V2_PROV / "stage_a.json"),
               "base_stage_b": base_stage_b, "typed_qa": {
                   "cached_noop_hash_replay_sha256": noop_sha,
                   "canonical_pooling_qa_sha256": pooling_sha,
                   "counterfactual_cache_alignment_qa_sha256": alignment_sha,
                   "tolerance_selection_sha256": selection_sha,
               }, "stage_ready": bool(base_stage_b["stage_ready"] and pooling_ok and alignment_ok)}
    create_json(run_root / "stage_b.json", stage_b)
    create_json(run_root / "status.json", {"schema_version": "msae_v2_runtime_status_v1",
                                            "status": "eligible" if stage_b["stage_ready"] else "ineligible",
                                            "stage_b_ready": stage_b["stage_ready"],
                                            "stage_b_sha256": v2.sha_file(run_root / "stage_b.json")})


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-root", required=True)
    parser.add_argument("--gpu-uuid", required=True)
    parser.add_argument("--broker-pid", required=True, type=int)
    args = parser.parse_args()
    try:
        run(args)
    except BaseException as error:
        run_root = ROOT / args.run_root
        if run_root.exists():
            _write_failure(run_root, error)
        raise


if __name__ == "__main__":
    main()
