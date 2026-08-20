#!/usr/bin/env python3
"""Trusted numerical QA and frozen activation extraction for Atlas v3.1 attempt 5.

Inference only: no optimizer, gradient update, or neural checkpoint is permitted.
"""

from __future__ import annotations

import argparse
import base64
import fcntl
import hashlib
import json
import os
os.environ.setdefault("CUBLAS_WORKSPACE_CONFIG", ":4096:8")
import platform
import random
import time
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterable, Iterator, Mapping, Sequence

import numpy as np
import torch
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey, Ed25519PublicKey
from transformers import AutoModelForCausalLM

from atlas_discovery_v3 import canonical_json_bytes, read_json, read_jsonl, sha256_file, stable_digest
from atlas_discovery_v3_scoring import derive_numerical_tolerance, elementwise_null_pass, resolve_hidden_state_index

ROOT = Path(__file__).resolve().parents[1]
EXPECTED_CUBLAS = ":4096:8"
QA_SCHEMA = "atlas_discovery_v3_1_attempt5_numerical_qa_v2"
CACHE_SCHEMA = "atlas_discovery_v3_1_attempt5_activation_cache_v2"
AUTH_SCHEMA = "atlas_discovery_v3_1_attempt5_full_extraction_authorization_v1"


def _atomic_json(path: Path, value: Mapping[str, Any]) -> None:
    payload = json.dumps(dict(value), indent=2, sort_keys=True) + "\n"
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    with temporary.open("w", encoding="utf-8") as handle:
        handle.write(payload)
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(temporary, path)
    _fsync_directory(path.parent)


def _fsync_directory(path: Path) -> None:
    descriptor = os.open(path, os.O_RDONLY | os.O_DIRECTORY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def _fsync_file(path: Path) -> None:
    with path.open("rb") as handle:
        os.fsync(handle.fileno())


def _validate_relative_path(raw: str) -> Path:
    path = Path(raw)
    if path.is_absolute() or ".." in path.parts:
        raise RuntimeError(f"unsafe relative path: {raw}")
    return path


def load_scoring_config(path: Path) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    resolved = path.resolve(strict=True)
    if not resolved.is_relative_to(ROOT) or resolved.is_symlink() or not resolved.is_file():
        raise RuntimeError("scoring config must be a regular in-repository file")
    config = read_json(resolved)
    if config.get("schema_version") != "atlas_discovery_v3_1_attempt5_scoring_v2":
        raise RuntimeError("unknown scoring schema")
    if config.get("neural_training_authorized") is not False:
        raise RuntimeError("scoring config must explicitly forbid neural training")
    for raw, expected in config["implementation_inventory"].items():
        candidate = (ROOT / _validate_relative_path(str(raw))).resolve(strict=True)
        if not candidate.is_relative_to(ROOT) or candidate.is_symlink() or not candidate.is_file():
            raise RuntimeError(f"invalid scoring inventory path: {raw}")
        if sha256_file(candidate) != expected:
            raise RuntimeError(f"scoring implementation drift: {raw}")
    prescore_path = (ROOT / _validate_relative_path(str(config["prescore_config"]["path"]))).resolve(strict=True)
    if sha256_file(prescore_path) != config["prescore_config"]["sha256"]:
        raise RuntimeError("prescore config drift")
    prescore = read_json(prescore_path)
    data_root = ROOT / str(prescore["data_root"])
    preflight_path = data_root / "preflight.json"
    manifest_path = data_root / "prepared" / "manifest.json"
    if sha256_file(preflight_path) != config["preflight_sha256"]:
        raise RuntimeError("preflight drift")
    if sha256_file(manifest_path) != config["prepared_manifest_sha256"]:
        raise RuntimeError("prepared manifest drift")
    preflight = read_json(preflight_path)
    manifest = read_json(manifest_path)
    if not preflight.get("all_required_measurement_populations_eligible"):
        raise RuntimeError("prescore feasibility did not pass")
    if manifest.get("schema_version") != "atlas_discovery_v3_1_attempt5_prepared_v1":
        raise RuntimeError("old or unknown prepared cache rejected")
    rebuild_spec = config["rebuild_check"]
    rebuild_path = (ROOT / _validate_relative_path(str(rebuild_spec["path"]))).resolve(strict=True)
    if sha256_file(rebuild_path) != rebuild_spec["sha256"]:
        raise RuntimeError("rebuild attestation drift")
    rebuild = read_json(rebuild_path)
    if (
        rebuild.get("schema_version") != "atlas_discovery_v3_1_attempt5_rebuild_check_v1"
        or rebuild.get("status") != "PASS"
        or rebuild.get("prepared_manifest_sha256") != config["prepared_manifest_sha256"]
        or rebuild.get("preflight_sha256") != config["preflight_sha256"]
    ):
        raise RuntimeError("rebuild attestation invalid")
    review_spec = config["prescore_adversarial_review"]
    review_path = (ROOT / _validate_relative_path(str(review_spec["path"]))).resolve(strict=True)
    if (
        sha256_file(review_path) != review_spec["sha256"]
        or review_spec.get("verdict") != "SHIP"
        or "VERDICT: SHIP" not in review_path.read_text(encoding="utf-8")
    ):
        raise RuntimeError("prescore adversarial SHIP attestation invalid")
    config["_resolved_sha256"] = sha256_file(resolved)
    config["_resolved_path"] = str(resolved.relative_to(ROOT))
    return config, prescore, manifest


def _verify_authorized_signer(config: Mapping[str, Any], private_key_path: Path) -> Ed25519PrivateKey:
    resolved = private_key_path.resolve(strict=True)
    if resolved.is_symlink() or not resolved.is_file():
        raise RuntimeError("signing key must be a regular file")
    private = serialization.load_pem_private_key(resolved.read_bytes(), password=None)
    if not isinstance(private, Ed25519PrivateKey):
        raise RuntimeError("signing key is not Ed25519")
    public = private.public_key().public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw)
    signer = config["qa_signer"]
    if base64.b64encode(public).decode("ascii") != signer["public_key_base64"]:
        raise RuntimeError("signing key does not match frozen public key")
    if hashlib.sha256(public).hexdigest() != signer["public_key_fingerprint_sha256"]:
        raise RuntimeError("signing key fingerprint mismatch")
    return private


def _sign_payload(payload: Mapping[str, Any], private: Ed25519PrivateKey) -> dict[str, Any]:
    message = canonical_json_bytes(dict(payload))
    return {
        "payload": dict(payload),
        "signature": {
            "algorithm": "Ed25519",
            "message_sha256": hashlib.sha256(message).hexdigest(),
            "signature_base64": base64.b64encode(private.sign(message)).decode("ascii"),
        },
    }


def _verify_envelope(envelope: Mapping[str, Any], config: Mapping[str, Any]) -> dict[str, Any]:
    payload, signature = envelope.get("payload"), envelope.get("signature")
    if not isinstance(payload, Mapping) or not isinstance(signature, Mapping):
        raise RuntimeError("malformed signed envelope")
    if signature.get("algorithm") != "Ed25519":
        raise RuntimeError("unexpected signature algorithm")
    message = canonical_json_bytes(dict(payload))
    if hashlib.sha256(message).hexdigest() != signature.get("message_sha256"):
        raise RuntimeError("signed message digest drift")
    public = base64.b64decode(str(config["qa_signer"]["public_key_base64"]), validate=True)
    if hashlib.sha256(public).hexdigest() != config["qa_signer"]["public_key_fingerprint_sha256"]:
        raise RuntimeError("frozen signer fingerprint drift")
    Ed25519PublicKey.from_public_bytes(public).verify(
        base64.b64decode(str(signature["signature_base64"]), validate=True), message
    )
    return dict(payload)


@contextmanager
def _exclusive_lock(run_root: Path, name: str) -> Iterator[None]:
    lock_root = run_root / "locks"
    lock_root.mkdir(parents=True, exist_ok=True)
    path = lock_root / f"{name}.lock"
    descriptor = os.open(path, os.O_CREAT | os.O_RDWR, 0o600)
    try:
        try:
            fcntl.flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as error:
            raise RuntimeError(f"concurrent stage already holds lock: {name}") from error
        yield
    finally:
        fcntl.flock(descriptor, fcntl.LOCK_UN)
        os.close(descriptor)


def _new_staging(run_root: Path, name: str, scoring_sha: str) -> Path:
    root = run_root / "staging"
    root.mkdir(parents=True, exist_ok=True)
    leftovers = sorted(root.glob(f"{name}-{scoring_sha[:12]}-*"))
    if leftovers:
        raise RuntimeError(f"stale staging directory requires explicit audit: {leftovers[0]}")
    stage = root / f"{name}-{scoring_sha[:12]}-{os.getpid()}"
    stage.mkdir()
    return stage


def _promote(stage: Path, final: Path) -> None:
    for path in sorted(stage.rglob("*")):
        if path.is_file():
            _fsync_file(path)
    _fsync_directory(stage)
    final.parent.mkdir(parents=True, exist_ok=True)
    if final.exists():
        raise RuntimeError(f"final output appeared during staging: {final}")
    os.replace(stage, final)
    _fsync_directory(final.parent)


def _seed_everything(seed: int) -> None:
    if os.environ.get("CUBLAS_WORKSPACE_CONFIG") != EXPECTED_CUBLAS:
        raise RuntimeError("CUBLAS_WORKSPACE_CONFIG must be frozen before CUDA initialization")
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    torch.cuda.manual_seed_all(seed)
    torch.use_deterministic_algorithms(True)
    torch.backends.cuda.matmul.allow_tf32 = False
    torch.backends.cudnn.allow_tf32 = False


def _gpu_uuid(device: torch.device) -> str:
    index = device.index if device.index is not None else torch.cuda.current_device()
    # PyTorch resolves the logical index after CUDA_VISIBLE_DEVICES remapping.
    value = str(torch.cuda.get_device_properties(index).uuid)
    return value if value.startswith("GPU-") else f"GPU-{value}"


def _validate_runtime(config: Mapping[str, Any], *, stage: str, source: str, device: torch.device, batch_size: int) -> None:
    expected_device = str(config["extraction"][f"{stage}_devices"][source])
    if str(device) != expected_device:
        raise RuntimeError(f"device override differs from frozen config: {device} != {expected_device}")
    if batch_size != int(config["extraction"]["batch_size"]):
        raise RuntimeError("batch-size override differs from frozen config")
    if device.type != "cuda" or not torch.cuda.is_available():
        raise RuntimeError("score-bearing extraction requires CUDA")
    expected_uuid = str(config["extraction"][f"{stage}_gpu_uuids"][source])
    if _gpu_uuid(device) != expected_uuid:
        raise RuntimeError("GPU UUID differs from frozen config")


def _load_model(prescore: Mapping[str, Any], device: torch.device) -> torch.nn.Module:
    model = AutoModelForCausalLM.from_pretrained(
        str(prescore["model"]["name"]), revision=str(prescore["model"]["revision"]),
        torch_dtype=torch.float16, local_files_only=True,
    ).to(device)
    model.eval().requires_grad_(False)
    if any(parameter.requires_grad for parameter in model.parameters()):
        raise RuntimeError("model parameters remain trainable")
    return model


def _batches(rows: Sequence[Mapping[str, Any]], size: int) -> Iterable[Sequence[Mapping[str, Any]]]:
    for start in range(0, len(rows), size):
        yield rows[start : start + size]


def _forward_units(model: torch.nn.Module, units: Sequence[Mapping[str, Any]], *, device: torch.device, hidden_index: int, batch_size: int) -> np.ndarray:
    blocks: list[np.ndarray] = []
    for batch in _batches(units, batch_size):
        maximum = max(len(row["input_ids"]) for row in batch)
        input_ids = torch.zeros((len(batch), maximum), dtype=torch.long, device=device)
        attention = torch.zeros_like(input_ids)
        position_ids = torch.zeros_like(input_ids)
        for index, row in enumerate(batch):
            n = len(row["input_ids"])
            input_ids[index, :n] = torch.as_tensor(row["input_ids"], dtype=torch.long, device=device)
            attention[index, :n] = torch.as_tensor(row["attention_mask"], dtype=torch.long, device=device)
            position_ids[index, :n] = torch.as_tensor(row["position_ids"], dtype=torch.long, device=device)
        with torch.inference_mode():
            result = model(input_ids=input_ids, attention_mask=attention, position_ids=position_ids,
                           output_hidden_states=True, use_cache=False)
        hidden = result.hidden_states[hidden_index]
        for index, row in enumerate(batch):
            positions = torch.as_tensor(row["positions"], dtype=torch.long, device=device)
            blocks.append(hidden[index].index_select(0, positions).float().cpu().numpy().astype(np.float32))
    if not blocks:
        raise RuntimeError("empty inference population")
    return np.concatenate(blocks, axis=0)


def _resolve_hidden_index(model: torch.nn.Module, unit: Mapping[str, Any], device: torch.device, layer: int) -> int:
    ids = torch.as_tensor([unit["input_ids"]], dtype=torch.long, device=device)
    attention = torch.as_tensor([unit["attention_mask"]], dtype=torch.long, device=device)
    positions = torch.as_tensor([unit["position_ids"]], dtype=torch.long, device=device)
    with torch.inference_mode():
        result = model(input_ids=ids, attention_mask=attention, position_ids=positions,
                       output_hidden_states=True, use_cache=False)
    return resolve_hidden_state_index(layer, len(result.hidden_states))


def _load_source_bundle(prescore: Mapping[str, Any], manifest: Mapping[str, Any], source: str) -> dict[str, Any]:
    root = ROOT / str(prescore["data_root"]) / "prepared" / source
    specs = manifest["sources"][source]
    paths = {
        "units": root / "inference_units.jsonl",
        "rows": root / "activation_rows.jsonl",
        "pairs": root / "intervention_pairs.jsonl",
    }
    expected = {
        "units": specs["units_sha256"],
        "rows": specs["activation_rows_sha256"],
        "pairs": specs["intervention_pairs_sha256"],
    }
    for key, path in paths.items():
        if sha256_file(path) != expected[key]:
            raise RuntimeError(f"{source} child input digest drift: {key}")
    units, rows, pairs = read_jsonl(paths["units"]), read_jsonl(paths["rows"]), read_jsonl(paths["pairs"])
    unit_ids, all_row_ids, flattened = set(), set(), []
    row_to_unit: dict[str, dict[str, Any]] = {}
    for unit in units:
        unit_id = str(unit["unit_id"])
        if unit_id in unit_ids:
            raise RuntimeError("duplicate inference unit ID")
        unit_ids.add(unit_id)
        n = len(unit["input_ids"])
        if not n or any(len(unit[key]) != n for key in ("attention_mask", "position_ids")):
            raise RuntimeError("invalid unit tensor lengths")
        if any(int(value) != 1 for value in unit["attention_mask"]):
            raise RuntimeError("prepared unit attention mask is not all visible")
        if len(unit["positions"]) != len(unit["row_ids"]):
            raise RuntimeError("unit target/row length drift")
        if any(not 0 <= int(position) < n for position in unit["positions"]):
            raise RuntimeError("unit target position outside input")
        for row_id in unit["row_ids"]:
            row_id = str(row_id)
            if row_id in all_row_ids:
                raise RuntimeError("duplicate activation row ID")
            all_row_ids.add(row_id)
            flattened.append(row_id)
            row_to_unit[row_id] = unit
    expected_rows = [str(row["row_id"]) for row in rows]
    if len(expected_rows) != len(set(expected_rows)) or flattened != expected_rows:
        raise RuntimeError("ordered activation-row lineage drift")
    pair_ids = [str(row["pair_id"]) for row in pairs]
    if len(pair_ids) != len(set(pair_ids)):
        raise RuntimeError("duplicate intervention pair ID")
    pair_row_ids: set[str] = set()
    def collect(value: Any) -> None:
        if isinstance(value, str):
            pair_row_ids.add(value)
        elif isinstance(value, Mapping):
            for child in value.values(): collect(child)
    for pair in pairs: collect(pair["rows"])
    if not pair_row_ids.issubset(all_row_ids):
        raise RuntimeError("intervention pair references unknown activation row")
    return {"root": root, "units": units, "rows": rows, "pairs": pairs, "row_to_unit": row_to_unit}


def _assert_translation(reference: Mapping[str, Any], candidate: Mapping[str, Any], offset: int) -> None:
    for key in ("input_ids", "attention_mask", "positions"):
        if list(reference[key]) != list(candidate[key]):
            raise RuntimeError(f"null pair changes {key}")
    if len(reference["row_ids"]) != len(candidate["row_ids"]):
        raise RuntimeError("null pair target-row count drift")
    differences = [int(right) - int(left) for left, right in zip(reference["position_ids"], candidate["position_ids"], strict=True)]
    if not differences or any(value != offset for value in differences):
        raise RuntimeError("null pair is not the exact frozen position translation")


def _qa_units(bundle: Mapping[str, Any], prescore: Mapping[str, Any], source: str) -> tuple[list[Mapping[str, Any]], list[Mapping[str, Any]], list[dict[str, Any]], int]:
    pairs, row_to_unit = bundle["pairs"], bundle["row_to_unit"]
    size = int(prescore["numerical_qa"]["set_size_per_source"])
    relative_size, context_size = size // 2, size - size // 2
    relative = sorted((row for row in pairs if row["construct"] == "relative_gap"),
        key=lambda row: stable_digest("atlas_discovery_v3_1_attempt5", "qa-relative", prescore["seed"], source, row["pair_id"]))[:relative_size]
    context = sorted((row for row in pairs if row["construct"] == "context_factorial"),
        key=lambda row: stable_digest("atlas_discovery_v3_1_attempt5", "qa-context", prescore["seed"], source, row["pair_id"]))[:context_size]
    if len(relative) != relative_size or len(context) != context_size:
        raise RuntimeError("insufficient QA population")
    references, candidates, qa_rows = [], [], []
    uniform_rows = 0
    for pair in relative:
        if set(pair["rows"]["bare"]) != {"pre", "post"} or set(pair["rows"]["uniform_shift"]) != {"pre", "post"}:
            raise RuntimeError("relative-gap QA row roles drift")
        reference = row_to_unit[pair["rows"]["bare"]["pre"]]
        candidate = row_to_unit[pair["rows"]["uniform_shift"]["pre"]]
        if list(reference["row_ids"]) != [pair["rows"]["bare"][role] for role in ("pre", "post")]:
            raise RuntimeError("relative bare row ordering drift")
        if list(candidate["row_ids"]) != [pair["rows"]["uniform_shift"][role] for role in ("pre", "post")]:
            raise RuntimeError("relative shifted row ordering drift")
        _assert_translation(reference, candidate, int(prescore["interventions"]["position_shift"]))
        references.append(reference); candidates.append(candidate); uniform_rows += 2
        qa_rows.append({"pair_id": pair["pair_id"], "family": "uniform_shift", "roles": ["pre", "post"]})
    for pair in context:
        reference = row_to_unit[pair["rows"]["bare"]]
        candidate = row_to_unit[pair["rows"]["prefix_position_only"]]
        if list(reference["row_ids"]) != [pair["rows"]["bare"]] or list(candidate["row_ids"]) != [pair["rows"]["prefix_position_only"]]:
            raise RuntimeError("context QA row ordering drift")
        _assert_translation(reference, candidate, int(pair["prefix_length"]) + 1)
        references.append(reference); candidates.append(candidate)
        qa_rows.append({"pair_id": pair["pair_id"], "family": "prefix_position_only", "roles": ["target"]})
    return references, candidates, qa_rows, uniform_rows


def _verify_qa(path: Path, config: Mapping[str, Any], source: str) -> dict[str, Any]:
    envelope = read_json(path); payload = _verify_envelope(envelope, config)
    if payload.get("schema_version") != QA_SCHEMA or payload.get("source") != source or payload.get("status") != "PASS":
        raise RuntimeError("QA envelope identity/status invalid")
    if payload.get("scoring_config_sha256") != config["_resolved_sha256"] or payload.get("prepared_manifest_sha256") != config["prepared_manifest_sha256"]:
        raise RuntimeError("QA lineage drift")
    expected_device = str(config["extraction"]["qa_devices"][source])
    if (
        payload.get("device") != expected_device
        or payload.get("gpu_uuid") != config["extraction"]["qa_gpu_uuids"][source]
        or payload.get("batch_size") != int(config["extraction"]["batch_size"])
        or payload.get("layer") != 3
        or payload.get("hidden_state_index") != 4
        or payload.get("model") is None
        or payload.get("neural_training_run") is not False
        or payload.get("uniform_shift_pass") is not True
        or payload.get("prefix_position_only_pass") is not True
        or payload.get("tolerance", {}).get("status") != "valid"
    ):
        raise RuntimeError("QA decision-relevant payload drift")
    root = path.parent
    expected_files = {"QA_COMPLETE.json", "qa_arrays.float32.npz", "qa_rows.json"}
    if {p.name for p in root.iterdir() if p.is_file()} != expected_files:
        raise RuntimeError("QA bundle file set drift")
    if sha256_file(root / "qa_rows.json") != payload["qa_row_manifest_sha256"] or sha256_file(root / "qa_arrays.float32.npz") != payload["qa_arrays_sha256"]:
        raise RuntimeError("QA child artifact drift")
    return dict(envelope)


def run_qa(config: Mapping[str, Any], prescore: Mapping[str, Any], manifest: Mapping[str, Any], *, source: str, device: torch.device, batch_size: int, signing_key: Path) -> dict[str, Any]:
    if config.get("status") != "frozen_numerical_qa_authorized":
        raise RuntimeError("stable scoring config does not authorize numerical QA")
    _validate_runtime(config, stage="qa", source=source, device=device, batch_size=batch_size)
    qa_config = prescore["numerical_qa"]
    if (int(qa_config["repeats"]) != 3 or float(qa_config["atol_multiplier"]) != 2.0
        or float(qa_config["rtol"]) <= 0 or float(qa_config["atol_floor"]) >= float(qa_config["atol_hard_ceiling"])):
        raise RuntimeError("numerical QA configuration violates frozen formula")
    private = _verify_authorized_signer(config, signing_key)
    run_root = ROOT / str(prescore["run_root"]); final = run_root / "numerical_qa" / source
    with _exclusive_lock(run_root, f"qa-{source}"):
        if final.exists(): return _verify_qa(final / "QA_COMPLETE.json", config, source)
        stage = _new_staging(run_root, f"qa-{source}", str(config["_resolved_sha256"]))
        bundle = _load_source_bundle(prescore, manifest, source)
        references, candidates, qa_rows, uniform_rows = _qa_units(bundle, prescore, source)
        _seed_everything(int(prescore["seed"])); model = _load_model(prescore, device)
        hidden_index = _resolve_hidden_index(model, references[0], device, int(prescore["model"]["layer"]))
        repeats = [_forward_units(model, references, device=device, hidden_index=hidden_index, batch_size=batch_size) for _ in range(3)]
        shifted = _forward_units(model, candidates, device=device, hidden_index=hidden_index, batch_size=batch_size)
        reference = repeats[0]
        if shifted.shape != reference.shape or any(row.shape != reference.shape for row in repeats):
            raise RuntimeError("QA array shape drift")
        error = max(float(np.max(np.abs(row.astype(np.float64) - reference.astype(np.float64)))) for row in repeats[1:])
        tolerance = derive_numerical_tolerance(error, atol_floor=float(qa_config["atol_floor"]),
            atol_hard_ceiling=float(qa_config["atol_hard_ceiling"]), multiplier=2.0, rtol=float(qa_config["rtol"]))
        valid = tolerance["status"] == "valid"
        uniform_pass = valid and elementwise_null_pass(reference[:uniform_rows], shifted[:uniform_rows], atol=float(tolerance["atol"]), rtol=float(tolerance["rtol"]))
        prefix_pass = valid and elementwise_null_pass(reference[uniform_rows:], shifted[uniform_rows:], atol=float(tolerance["atol"]), rtol=float(tolerance["rtol"]))
        np.savez(stage / "qa_arrays.float32.npz", reference=reference, repeat_1=repeats[1], repeat_2=repeats[2], candidate=shifted)
        (stage / "qa_rows.json").write_text(json.dumps(qa_rows, indent=2, sort_keys=True) + "\n")
        payload = {"schema_version": QA_SCHEMA, "source": source, "status": "PASS" if uniform_pass and prefix_pass else "FAIL",
            "tolerance": tolerance, "uniform_shift_pass": bool(uniform_pass), "prefix_position_only_pass": bool(prefix_pass),
            "qa_underlying_units": len(qa_rows), "qa_activation_rows": int(reference.shape[0]),
            "qa_row_manifest_sha256": sha256_file(stage / "qa_rows.json"), "qa_arrays_sha256": sha256_file(stage / "qa_arrays.float32.npz"),
            "hidden_state_index": hidden_index, "layer": int(prescore["model"]["layer"]), "dtype": "float16_inference_float32_cache",
            "device": str(device), "gpu_uuid": _gpu_uuid(device), "batch_size": batch_size, "model": prescore["model"],
            "scoring_config_sha256": config["_resolved_sha256"], "prescore_config_sha256": config["prescore_config"]["sha256"],
            "prepared_manifest_sha256": config["prepared_manifest_sha256"], "neural_training_run": False,
            "environment": {"python": platform.python_version(), "torch": torch.__version__, "cuda": torch.version.cuda,
                "cudnn": torch.backends.cudnn.version(), "cublas_workspace_config": os.environ["CUBLAS_WORKSPACE_CONFIG"],
                "deterministic_algorithms": torch.are_deterministic_algorithms_enabled(), "tf32": False}}
        envelope = _sign_payload(payload, private); _atomic_json(stage / "QA_COMPLETE.json", envelope)
        if payload["status"] != "PASS":
            raise RuntimeError(f"numerical QA failed; staged evidence retained at {stage}")
        _verify_qa(stage / "QA_COMPLETE.json", config, source); _promote(stage, final)
        return _verify_qa(final / "QA_COMPLETE.json", config, source)


def authorize_full(config: Mapping[str, Any], prescore: Mapping[str, Any], *, signing_key: Path) -> dict[str, Any]:
    if config.get("status") != "frozen_numerical_qa_authorized":
        raise RuntimeError("scoring config is not frozen for staged authorization")
    private = _verify_authorized_signer(config, signing_key); run_root = ROOT / str(prescore["run_root"])
    authorization_path = ROOT / _validate_relative_path(str(config["full_authorization_path"]))
    with _exclusive_lock(run_root, "full-authorization"):
        if authorization_path.exists(): return _verify_full_authorization(config, prescore)
        qa_digests = {}
        for source in ("EWT", "GUM"):
            path = run_root / "numerical_qa" / source / "QA_COMPLETE.json"; _verify_qa(path, config, source)
            qa_digests[source] = sha256_file(path)
        payload = {"schema_version": AUTH_SCHEMA, "status": "AUTHORIZED", "scoring_config_sha256": config["_resolved_sha256"],
            "prepared_manifest_sha256": config["prepared_manifest_sha256"], "qa_complete_sha256": qa_digests,
            "authorized_stage": "full_activation_extraction_only", "neural_training_authorized": False}
        authorization_path.parent.mkdir(parents=True, exist_ok=True); _atomic_json(authorization_path, _sign_payload(payload, private))
        return _verify_full_authorization(config, prescore)


def _verify_full_authorization(config: Mapping[str, Any], prescore: Mapping[str, Any]) -> dict[str, Any]:
    path = ROOT / _validate_relative_path(str(config["full_authorization_path"])); envelope = read_json(path)
    payload = _verify_envelope(envelope, config)
    if payload.get("schema_version") != AUTH_SCHEMA or payload.get("status") != "AUTHORIZED" or payload.get("authorized_stage") != "full_activation_extraction_only" or payload.get("scoring_config_sha256") != config["_resolved_sha256"] or payload.get("prepared_manifest_sha256") != config["prepared_manifest_sha256"] or payload.get("neural_training_authorized") is not False or set(payload.get("qa_complete_sha256", {})) != {"EWT", "GUM"}:
        raise RuntimeError("full extraction authorization invalid")
    run_root = ROOT / str(prescore["run_root"])
    for source in ("EWT", "GUM"):
        qa_path = run_root / "numerical_qa" / source / "QA_COMPLETE.json"; _verify_qa(qa_path, config, source)
        if sha256_file(qa_path) != payload["qa_complete_sha256"][source]: raise RuntimeError("authorization QA digest drift")
    return dict(envelope)


def _artifact_inventory(root: Path) -> dict[str, dict[str, Any]]:
    return {path.name: {"sha256": sha256_file(path), "bytes": path.stat().st_size}
        for path in sorted(root.iterdir()) if path.is_file() and path.name != "COMPLETE.json"}


def _verify_complete_cache(final: Path, config: Mapping[str, Any], prescore: Mapping[str, Any], bundle: Mapping[str, Any], source: str) -> dict[str, Any]:
    expected_files = {"COMPLETE.json", "activations.float32.npy", "row_ids.jsonl"}
    if {p.name for p in final.iterdir() if p.is_file()} != expected_files: raise RuntimeError("activation bundle file set drift")
    envelope = read_json(final / "COMPLETE.json"); payload = _verify_envelope(envelope, config)
    if payload.get("schema_version") != CACHE_SCHEMA or payload.get("status") != "COMPLETE" or payload.get("source") != source:
        raise RuntimeError("activation completion identity invalid")
    expected = {"activations.float32.npy", "row_ids.jsonl"}
    if set(payload.get("artifacts", {})) != expected: raise RuntimeError("activation artifact inventory is not exact")
    for name in expected:
        path = final / name; spec = payload["artifacts"][name]
        if path.stat().st_size != int(spec["bytes"]) or sha256_file(path) != spec["sha256"]: raise RuntimeError(f"activation artifact drift: {name}")
    rows, units = bundle["rows"], bundle["units"]
    if payload.get("rows") != len(rows) or payload.get("units") != len(units) or payload.get("layer") != int(prescore["model"]["layer"]) or payload.get("model") != prescore["model"] or payload.get("scoring_config_sha256") != config["_resolved_sha256"] or payload.get("prepared_manifest_sha256") != config["prepared_manifest_sha256"]:
        raise RuntimeError("activation completion lineage/count drift")
    if (
        payload.get("device") != str(config["extraction"]["full_devices"][source])
        or payload.get("gpu_uuid") != config["extraction"]["full_gpu_uuids"][source]
        or payload.get("batch_size") != int(config["extraction"]["batch_size"])
        or payload.get("hidden_state_index") != int(prescore["model"]["layer"]) + 1
        or payload.get("dtype") != "float32"
        or payload.get("inference_dtype") != "float16"
        or payload.get("neural_training_run") is not False
        or payload.get("optimizer_created") is not False
        or payload.get("checkpoint_created") is not False
    ):
        raise RuntimeError("activation completion decision-relevant payload drift")
    sidecar = [json.loads(line)["row_id"] for line in (final / "row_ids.jsonl").read_text().splitlines() if line]
    if sidecar != [row["row_id"] for row in rows] or len(sidecar) != len(set(sidecar)): raise RuntimeError("activation row sidecar drift")
    array = np.load(final / "activations.float32.npy", mmap_mode="r")
    if array.dtype != np.float32 or array.shape != (len(rows), int(payload["width"])) or not np.isfinite(array).all():
        raise RuntimeError("activation array structure drift")
    authorization_path = ROOT / _validate_relative_path(str(config["full_authorization_path"]))
    if payload.get("full_authorization_sha256") != sha256_file(authorization_path): raise RuntimeError("activation authorization lineage drift")
    qa_path = ROOT / str(prescore["run_root"]) / "numerical_qa" / source / "QA_COMPLETE.json"
    if payload.get("qa_complete_sha256") != sha256_file(qa_path): raise RuntimeError("activation QA lineage drift")
    return dict(envelope)


def run_full(config: Mapping[str, Any], prescore: Mapping[str, Any], manifest: Mapping[str, Any], *, source: str, device: torch.device, batch_size: int, signing_key: Path) -> dict[str, Any]:
    _validate_runtime(config, stage="full", source=source, device=device, batch_size=batch_size)
    private = _verify_authorized_signer(config, signing_key); _verify_full_authorization(config, prescore)
    run_root = ROOT / str(prescore["run_root"]); final = run_root / "activations" / source
    with _exclusive_lock(run_root, f"full-{source}"):
        bundle = _load_source_bundle(prescore, manifest, source)
        if final.exists(): return _verify_complete_cache(final, config, prescore, bundle, source)
        stage = _new_staging(run_root, f"full-{source}", str(config["_resolved_sha256"]))
        units, rows = bundle["units"], bundle["rows"]
        _seed_everything(int(prescore["seed"])); model = _load_model(prescore, device)
        hidden_index = _resolve_hidden_index(model, units[0], device, int(prescore["model"]["layer"]))
        first = _forward_units(model, units[:1], device=device, hidden_index=hidden_index, batch_size=1); width = int(first.shape[1])
        cache = np.lib.format.open_memmap(stage / "activations.float32.npy", mode="w+", dtype=np.float32, shape=(len(rows), width))
        started, cursor = time.time(), 0
        for batch_index, batch in enumerate(_batches(units, batch_size)):
            block = _forward_units(model, batch, device=device, hidden_index=hidden_index, batch_size=batch_size)
            cache[cursor:cursor + len(block)] = block; cursor += len(block)
            if batch_index % 25 == 0: print(json.dumps({"source": source, "units_complete": min((batch_index+1)*batch_size,len(units)), "units_total": len(units), "rows_complete": cursor, "rows_total": len(rows), "elapsed_seconds": time.time()-started}), flush=True)
        if cursor != len(rows) or not np.isfinite(cache).all(): raise RuntimeError("activation cache incomplete/non-finite")
        cache.flush(); del cache
        with (stage / "row_ids.jsonl").open("w", encoding="utf-8") as handle:
            for row in rows: handle.write(json.dumps({"row_id": row["row_id"]}, sort_keys=True, separators=(",", ":")) + "\n")
        artifacts = _artifact_inventory(stage); auth_path = ROOT / _validate_relative_path(str(config["full_authorization_path"])); qa_path = run_root / "numerical_qa" / source / "QA_COMPLETE.json"
        payload = {"schema_version": CACHE_SCHEMA, "source": source, "status": "COMPLETE", "rows": len(rows), "units": len(units), "width": width,
            "layer": int(prescore["model"]["layer"]), "hidden_state_index": hidden_index, "dtype": "float32", "inference_dtype": "float16",
            "device": str(device), "gpu_uuid": _gpu_uuid(device), "batch_size": batch_size, "elapsed_seconds": time.time()-started,
            "model": prescore["model"], "qa_complete_sha256": sha256_file(qa_path), "full_authorization_sha256": sha256_file(auth_path),
            "scoring_config_sha256": config["_resolved_sha256"], "prescore_config_sha256": config["prescore_config"]["sha256"], "prepared_manifest_sha256": config["prepared_manifest_sha256"],
            "neural_training_run": False, "optimizer_created": False, "checkpoint_created": False,
            "environment": {"python": platform.python_version(), "torch": torch.__version__, "cuda": torch.version.cuda, "cudnn": torch.backends.cudnn.version(), "gpu": torch.cuda.get_device_name(device), "cublas_workspace_config": os.environ["CUBLAS_WORKSPACE_CONFIG"], "deterministic_algorithms": torch.are_deterministic_algorithms_enabled(), "tf32": False}, "artifacts": artifacts}
        _atomic_json(stage / "COMPLETE.json", _sign_payload(payload, private)); _verify_complete_cache(stage, config, prescore, bundle, source); _promote(stage, final)
        return _verify_complete_cache(final, config, prescore, bundle, source)


def main() -> None:
    parser = argparse.ArgumentParser(); parser.add_argument("--config", default="configs/atlas_discovery_v3/scoring.json")
    parser.add_argument("--stage", required=True, choices=("qa", "authorize-full", "full")); parser.add_argument("--source", choices=("EWT", "GUM"))
    parser.add_argument("--device"); parser.add_argument("--batch-size", type=int); parser.add_argument("--signing-key", type=Path)
    args = parser.parse_args(); config, prescore, manifest = load_scoring_config(ROOT / args.config)
    if args.stage == "authorize-full":
        if args.source or args.device or args.batch_size or args.signing_key is None: raise RuntimeError("authorize-full requires only --signing-key")
        result = authorize_full(config, prescore, signing_key=args.signing_key)
    else:
        if args.source is None or args.signing_key is None: raise RuntimeError("qa/full require --source and --signing-key")
        stage_key = "qa" if args.stage == "qa" else "full"; frozen_device = str(config["extraction"][f"{stage_key}_devices"][args.source]); frozen_batch = int(config["extraction"]["batch_size"])
        device = torch.device(args.device or frozen_device); batch_size = args.batch_size or frozen_batch
        result = run_qa(config,prescore,manifest,source=args.source,device=device,batch_size=batch_size,signing_key=args.signing_key) if args.stage == "qa" else run_full(config,prescore,manifest,source=args.source,device=device,batch_size=batch_size,signing_key=args.signing_key)
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__": main()
