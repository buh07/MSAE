#!/usr/bin/env python3
"""One-shot extractor and signed lifecycle for relational QK-link discovery v1."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import signal
import subprocess
import sys
import time
import traceback
from importlib.metadata import version as package_version
from pathlib import Path
from typing import Any, Mapping, Sequence

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))

from analyze_relational_attention_edges_v1 import analyze
from relational_attention_edges_v1 import (
    AUTHORIZATION,
    BACKEND_QA,
    CONFIG,
    FREEZE,
    ROOT,
    assert_new_destination,
    atomic_json,
    canonical_json_bytes,
    exclusive_fsynced_json,
    inventory_digest,
    load_config,
    load_signing_key,
    read_json,
    read_jsonl,
    recursive_inventory,
    sha256_file,
    sign_payload,
    verify_preservation,
    verify_signed,
)

REVIEWED = ROOT / "configs/relational_attention_edges_v1/REVIEWED_SHIP.json"
REBUILD_ATTESTATION = ROOT / "reports/provenance/relational_attention_edges_v1_rebuild_attestation.json"
KEY_PATH_DEFAULT = Path("/jumbo/lisp/f004ndc/.generated/sessions/unleashed-3/modes/unleashed/.secrets/attempt13_ed25519.pem")


def _nvidia_rows() -> list[dict[str, Any]]:
    command = [
        "nvidia-smi",
        "--query-gpu=index,uuid,memory.used,memory.free,utilization.gpu,mig.mode.current",
        "--format=csv,noheader,nounits",
    ]
    output = subprocess.check_output(command, text=True)
    rows = []
    for line in output.splitlines():
        index, uuid, used, free, utilization, mig = [item.strip() for item in line.split(",")]
        rows.append({"index": int(index), "uuid": uuid, "memory_used_mib": int(used), "memory_free_mib": int(free), "utilization_percent": int(utilization), "mig_mode": f"[{mig}]" if not mig.startswith("[") else mig})
    return rows


def _compute_apps() -> list[tuple[str, int]]:
    output = subprocess.check_output(["nvidia-smi", "--query-compute-apps=gpu_uuid,pid", "--format=csv,noheader,nounits"], text=True)
    apps = []
    for line in output.splitlines():
        if not line.strip() or "No running" in line:
            continue
        uuid, pid = [item.strip() for item in line.split(",")]
        apps.append((uuid, int(pid)))
    return apps


def assert_physical_gpu_free(config: Mapping[str, Any]) -> dict[str, Any]:
    expected = config["runtime"]
    matches = [row for row in _nvidia_rows() if row["index"] == int(expected["physical_gpu_index"])]
    if len(matches) != 1:
        raise RuntimeError("frozen physical GPU index missing or ambiguous")
    row = matches[0]
    foreign_apps = [(uuid, pid) for uuid, pid in _compute_apps() if pid != os.getpid()]
    if row["uuid"] != expected["gpu_uuid"] or any(uuid == row["uuid"] for uuid, _pid in foreign_apps):
        raise RuntimeError("frozen GPU identity is busy or drifted")
    if row["mig_mode"] != expected["mig_mode"]:
        raise RuntimeError("frozen GPU MIG identity drift")
    if row["memory_used_mib"] > int(expected["maximum_memory_used_mib"]):
        raise RuntimeError("frozen GPU memory-use ceiling failed")
    if row["memory_free_mib"] < int(expected["minimum_memory_free_mib"]):
        raise RuntimeError("frozen GPU free-memory floor failed")
    if row["utilization_percent"] != int(expected["required_utilization_percent"]):
        raise RuntimeError("frozen GPU utilization gate failed")
    return row


def assert_environment(config: Mapping[str, Any]) -> None:
    environment = config["environment"]
    lock = ROOT / environment["lock_path"]
    if not lock.is_file() or sha256_file(lock) != environment["lock_sha256"]:
        raise RuntimeError("dependency lock drift")
    observed = {name: package_version(name) for name in environment["versions"]}
    if observed != environment["versions"]:
        raise RuntimeError(f"dependency version drift: {observed}")


def assert_visible_gpu(config: Mapping[str, Any]) -> str:
    import torch
    if not torch.cuda.is_available() or torch.cuda.device_count() != 1:
        raise RuntimeError("runner requires exactly one Torch-visible CUDA device")
    observed = str(torch.cuda.get_device_properties(0).uuid)
    if not observed.startswith("GPU-"):
        observed = "GPU-" + observed
    if observed != config["runtime"]["gpu_uuid"]:
        raise RuntimeError(f"Torch-visible GPU UUID drift: {observed}")
    return observed


def _implementation_inventory(config: Mapping[str, Any]) -> list[dict[str, Any]]:
    paths = [
        CONFIG,
        ROOT / "scripts/relational_attention_edges_v1.py",
        ROOT / "scripts/build_relational_attention_edges_v1.py",
        ROOT / "scripts/analyze_relational_attention_edges_v1.py",
        ROOT / "scripts/run_relational_attention_edges_v1.py",
        ROOT / "scripts/run_relational_attention_edges_v1_pipeline.sh",
        ROOT / "scripts/launch_relational_attention_edges_v1_tmux.sh",
        ROOT / "tests/test_relational_attention_edges_v1.py",
        ROOT / config["environment"]["lock_path"],
    ]
    output = []
    for path in paths:
        if not path.is_file() or path.is_symlink():
            raise RuntimeError(f"candidate implementation missing or symlinked: {path}")
        output.append({"path": path.relative_to(ROOT).as_posix(), "bytes": path.stat().st_size, "sha256": sha256_file(path)})
    return output


def _prepared_manifest(config: Mapping[str, Any]) -> tuple[Path, dict[str, Any]]:
    path = ROOT / config["paths"]["prepared_root"] / "manifest.json"
    manifest = read_json(path)
    if manifest.get("status") != "PRESCORE_COMPLETE" or manifest.get("all_primary_sources_eligible") is not True:
        raise RuntimeError("prepared sample is not prescore-complete and eligible")
    if manifest.get("config_sha256") != sha256_file(CONFIG):
        raise RuntimeError("prepared sample was not built from the exact frozen config")
    if manifest.get("model_forward_run") is not False or manifest.get("endpoint_scores_computed") is not False:
        raise RuntimeError("prepared sample source-outcome exposure drift")
    entries = recursive_inventory(path.parent, exclude=("manifest.json",))
    if entries != manifest["prepared_inventory"] or inventory_digest(entries) != manifest["prepared_inventory_sha256"]:
        raise RuntimeError("prepared inventory drift")
    return path, manifest


def verify_rebuild_attestation(config: Mapping[str, Any]) -> dict[str, Any]:
    payload = verify_signed(REBUILD_ATTESTATION, config["signer"]["public_key_fingerprint_sha256"])
    if payload.get("status") != "BYTE_IDENTICAL_REBUILD_PASS" or payload.get("config_sha256") != sha256_file(CONFIG):
        raise RuntimeError("rebuild attestation identity drift")
    canonical = ROOT / payload["canonical_root"]
    rebuild = ROOT / payload["rebuild_root"]
    canonical_inventory = recursive_inventory(canonical)
    rebuild_inventory = recursive_inventory(rebuild)
    if canonical_inventory != rebuild_inventory:
        raise RuntimeError("canonical/rebuild trees are not byte-identical")
    digest = inventory_digest(canonical_inventory)
    if digest != payload["full_tree_inventory_sha256"]:
        raise RuntimeError("rebuild attestation inventory drift")
    return payload


def validate_runtime_lineage(config: Mapping[str, Any]) -> dict[str, Any]:
    reports: dict[str, Any] = {}
    prepared = ROOT / config["paths"]["prepared_root"]
    for source, spec in config["sources"].items():
        examples = read_jsonl(prepared / source / "examples.jsonl")
        pairs = read_jsonl(prepared / source / "pairs.jsonl")
        units = read_jsonl(prepared / source / "inference_units.jsonl")
        selected = set(spec["analysis_files"])
        observed_indices: list[int] = []
        for unit in units:
            if unit.get("source") != source or unit.get("source_file") not in selected:
                raise RuntimeError(f"runtime source/split lineage failure: {source}")
            expected_hash = spec["files"][unit["source_file"]]
            if unit.get("source_file_sha256") != expected_hash:
                raise RuntimeError(f"runtime source hash lineage failure: {source}")
            for reference in unit["examples"]:
                index = int(reference["example_index"])
                if index < 0 or index >= len(examples):
                    raise RuntimeError(f"runtime example FK out of range: {source}")
                row = examples[index]
                if row["sentence_key"] != unit["unit_id"] or int(row["query_index"]) != int(reference["query_index"]) or list(row["key_positions"]) != list(reference["key_positions"]):
                    raise RuntimeError(f"runtime unit/example FK mismatch: {source}:{index}")
                observed_indices.append(index)
        if sorted(observed_indices) != list(range(len(examples))):
            raise RuntimeError(f"runtime unit/example coverage is not bijective: {source}")
        for pair in pairs:
            edge, nonedge = int(pair["edge_index"]), int(pair["nonedge_index"])
            if examples[edge]["pair_id"] != pair["pair_id"] or examples[nonedge]["pair_id"] != pair["pair_id"] or int(examples[edge]["label"]) != 1 or int(examples[nonedge]["label"]) != 0:
                raise RuntimeError(f"runtime pair/example FK mismatch: {source}")
        ids = [str(row["example_id"]) for row in examples]
        if len(set(ids)) != len(ids):
            raise RuntimeError(f"duplicate runtime example ID: {source}")
        reports[source] = {"examples": len(examples), "pairs": len(pairs), "units": len(units), "example_id_set_sha256": hashlib.sha256(canonical_json_bytes(sorted(ids))).hexdigest()}
    return reports


def create_freeze(config: Mapping[str, Any], key_path: Path) -> dict[str, Any]:
    if FREEZE.exists():
        raise RuntimeError("freeze already exists")
    for path in (REVIEWED, BACKEND_QA, AUTHORIZATION):
        if path.exists():
            raise RuntimeError(f"post-freeze lifecycle artifact already exists: {path}")
    verify_preservation(config)
    assert_environment(config)
    prepared_path, prepared = _prepared_manifest(config)
    lineage = validate_runtime_lineage(config)
    rebuild = verify_rebuild_attestation(config)
    for path in (ROOT / config["paths"]["run_root"], ROOT / config["paths"]["result_root"], ROOT / config["paths"]["opening"]):
        assert_new_destination(config, path)
        if path.exists():
            raise RuntimeError(f"one-shot namespace is not absent: {path}")
    gpu = assert_physical_gpu_free(config)
    implementation = _implementation_inventory(config)
    payload = {
        "schema_version": "relational_attention_edges_v1_freeze_v1",
        "status": "FROZEN",
        "config_sha256": sha256_file(CONFIG),
        "prepared_manifest": {"path": prepared_path.relative_to(ROOT).as_posix(), "sha256": sha256_file(prepared_path), "inventory_sha256": prepared["prepared_inventory_sha256"]},
        "runtime_lineage": lineage,
        "rebuild_attestation_sha256": sha256_file(REBUILD_ATTESTATION),
        "rebuild_full_tree_inventory_sha256": rebuild["full_tree_inventory_sha256"],
        "implementation": implementation,
        "implementation_sha256": inventory_digest(implementation),
        "preservation_entries_sha256": verify_preservation(config),
        "source_amendment_sha256": config["source_amendment"]["sha256"],
        "plan_review_sha256": config["plan_review"]["sha256"],
        "gpu": gpu,
        "gpu_uuid": config["runtime"]["gpu_uuid"],
        "model_forward_run": False,
        "candidate_source_model_forward_run": False,
        "endpoint_scores_computed": False,
        "neural_training_run": False,
        "retry_authorized": False,
    }
    key = load_signing_key(key_path, config["signer"])
    sign_payload(FREEZE, payload, key)
    return payload


def verify_freeze(config: Mapping[str, Any]) -> dict[str, Any]:
    payload = verify_signed(FREEZE, config["signer"]["public_key_fingerprint_sha256"])
    if payload.get("status") != "FROZEN" or payload.get("config_sha256") != sha256_file(CONFIG):
        raise RuntimeError("freeze identity drift")
    prepared_path, manifest = _prepared_manifest(config)
    verify_rebuild_attestation(config)
    if payload["prepared_manifest"]["sha256"] != sha256_file(prepared_path) or payload["prepared_manifest"]["inventory_sha256"] != manifest["prepared_inventory_sha256"]:
        raise RuntimeError("freeze prepared binding drift")
    implementation = _implementation_inventory(config)
    if implementation != payload["implementation"] or inventory_digest(implementation) != payload["implementation_sha256"]:
        raise RuntimeError("frozen implementation drift")
    verify_preservation(config)
    assert_environment(config)
    return payload


def create_reviewed(config: Mapping[str, Any], key_path: Path) -> dict[str, Any]:
    if REVIEWED.exists():
        raise RuntimeError("reviewed marker already exists")
    freeze = verify_freeze(config)
    review = ROOT / config["paths"]["candidate_review"]
    if not review.is_file():
        raise RuntimeError("exact-candidate review is absent")
    review_text = review.read_text(encoding="utf-8")
    if not review_is_ship_bound(review_text, sha256_file(FREEZE)):
        raise RuntimeError("exact-candidate review is absent or not SHIP")
    payload = {
        "schema_version": "relational_attention_edges_v1_review_v1",
        "status": "REVIEWED_SHIP",
        "freeze_sha256": sha256_file(FREEZE),
        "review_path": review.relative_to(ROOT).as_posix(),
        "review_sha256": sha256_file(review),
        "implementation_sha256": freeze["implementation_sha256"],
        "candidate_source_model_forward_run": False,
    }
    sign_payload(REVIEWED, payload, load_signing_key(key_path, config["signer"]))
    return payload


def verify_reviewed(config: Mapping[str, Any]) -> dict[str, Any]:
    payload = verify_signed(REVIEWED, config["signer"]["public_key_fingerprint_sha256"])
    if payload.get("status") != "REVIEWED_SHIP" or payload.get("freeze_sha256") != sha256_file(FREEZE):
        raise RuntimeError("reviewed marker drift")
    review = ROOT / payload["review_path"]
    review_text = review.read_text(encoding="utf-8")
    if sha256_file(review) != payload["review_sha256"] or not review_is_ship_bound(review_text, sha256_file(FREEZE)):
        raise RuntimeError("candidate review drift")
    return payload


def review_is_ship_bound(text: str, freeze_sha256: str) -> bool:
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    verdicts = [line for line in lines if line.startswith("VERDICT:")]
    bindings = [line for line in lines if line.startswith("FREEZE_SHA256:")]
    return bool(
        lines
        and lines[0] == "VERDICT: SHIP"
        and verdicts == ["VERDICT: SHIP"]
        and bindings == [f"FREEZE_SHA256: {freeze_sha256}"]
    )


def _load_model(config: Mapping[str, Any]):
    import torch
    from transformers import AutoModelForCausalLM
    assert_visible_gpu(config)
    model = AutoModelForCausalLM.from_pretrained(
        config["model"]["name"],
        revision=config["model"]["revision"],
        local_files_only=bool(config["model"]["local_files_only"]),
        torch_dtype=torch.float32,
        attn_implementation="eager",
    ).to("cuda:0")
    model.eval()
    if model.config._attn_implementation != "eager":
        raise RuntimeError("model did not honor eager attention")
    attention = model.gpt_neox.layers[int(config["model"]["block_index"])].attention
    if int(model.config.num_attention_heads) != int(config["model"]["num_heads"]) or int(attention.head_size) != int(config["model"]["head_size"]):
        raise RuntimeError("model attention geometry drift")
    assert_visible_gpu(config)
    return model


def _rotary_qkv(model: Any, qkv: Any, hidden_input: Any, position_ids: Any, block: int):
    from transformers.models.gpt_neox.modeling_gpt_neox import apply_rotary_pos_emb
    attention = model.gpt_neox.layers[block].attention
    shape = (*qkv.shape[:-1], -1, 3 * attention.head_size)
    qkv_heads = qkv.view(shape).transpose(1, 2)
    query, key, value = qkv_heads.chunk(3, dim=-1)
    cos, sin = model.gpt_neox.rotary_emb(hidden_input, position_ids)
    query, key = apply_rotary_pos_emb(query, key, cos, sin)
    logits = query @ key.transpose(2, 3) * attention.scaling
    return query, key, value, logits


def _capture_batch(model: Any, input_ids: Any, attention_mask: Any, config: Mapping[str, Any]):
    import torch
    block = int(config["model"]["block_index"])
    captured: dict[str, Any] = {}
    module = model.gpt_neox.layers[block].attention.query_key_value

    def hook(_module: Any, inputs: tuple[Any, ...], output: Any) -> None:
        captured["hidden_input"] = inputs[0]
        captured["qkv"] = output

    handle = module.register_forward_hook(hook)
    try:
        with torch.inference_mode():
            outputs = model(
                input_ids=input_ids,
                attention_mask=attention_mask,
                use_cache=False,
                output_attentions=True,
                output_hidden_states=True,
                return_dict=True,
            )
    finally:
        handle.remove()
    if set(captured) != {"hidden_input", "qkv"}:
        raise RuntimeError("QKV hook did not fire exactly as expected")
    position_ids = torch.arange(input_ids.shape[1], device=input_ids.device).unsqueeze(0).expand(input_ids.shape[0], -1)
    query, key, value, logits = _rotary_qkv(model, captured["qkv"], captured["hidden_input"], position_ids, block)
    return outputs, captured, query, key, value, logits


def _manual_probabilities(logits: Any, attention_mask: Any):
    import torch
    batch, _heads, query_length, key_length = logits.shape
    causal = torch.arange(key_length, device=logits.device).view(1, 1, 1, -1) <= torch.arange(query_length, device=logits.device).view(1, 1, -1, 1)
    valid_key = attention_mask[:, None, None, :].bool()
    allowed = causal & valid_key
    masked = logits.masked_fill(~allowed, torch.finfo(logits.dtype).min)
    return torch.softmax(masked, dim=-1, dtype=torch.float32).to(logits.dtype)


def _independent_qk_logits(model: Any, qkv: Any, hidden_input: Any, position_ids: Any, block: int):
    """Independent literal partial-RoPE/QK reference used only by backend QA."""
    import torch
    attention = model.gpt_neox.layers[block].attention
    shaped = qkv.reshape(qkv.shape[0], qkv.shape[1], int(model.config.num_attention_heads), 3 * int(attention.head_size))
    query, key, _value = shaped.permute(0, 2, 1, 3).chunk(3, dim=-1)
    cos, sin = model.gpt_neox.rotary_emb(hidden_input, position_ids)
    cos, sin = cos.unsqueeze(1), sin.unsqueeze(1)
    rotary_dim = cos.shape[-1]

    def rotate_half(x: Any):
        left, right = x.chunk(2, dim=-1)
        return torch.cat((-right, left), dim=-1)

    q_rot, q_pass = query[..., :rotary_dim], query[..., rotary_dim:]
    k_rot, k_pass = key[..., :rotary_dim], key[..., rotary_dim:]
    q_manual = torch.cat((q_rot * cos + rotate_half(q_rot) * sin, q_pass), dim=-1)
    k_manual = torch.cat((k_rot * cos + rotate_half(k_rot) * sin, k_pass), dim=-1)
    return torch.matmul(q_manual, k_manual.transpose(2, 3)) * float(attention.scaling)


def pool_link_features(logits: Any, probabilities: Any, value: Any, residuals: Any, batch_index: int, query_index: int, key_positions: Sequence[int], attention_floor: float) -> dict[str, Any]:
    """Pool one frozen query-word/key-word link from already validated tensors."""
    import torch
    keys = list(map(int, key_positions))
    if not keys or max(keys) > query_index:
        raise ValueError("key positions must be nonempty and causally available")
    qk = logits[batch_index, :, query_index, keys].mean(dim=-1)
    attention_mass = probabilities[batch_index, :, query_index, keys].sum(dim=-1)
    transport = (probabilities[batch_index, :, query_index, keys].unsqueeze(-1) * value[batch_index, :, keys, :]).sum(dim=-2)
    unweighted = value[batch_index, :, keys, :].mean(dim=-2)
    query_residual = residuals[batch_index, query_index]
    key_residual = residuals[batch_index, keys].mean(dim=0)
    return {
        "qk": qk,
        "attention": torch.log(torch.clamp(attention_mass, min=float(attention_floor))),
        "transport": transport.reshape(-1),
        "value": unweighted.reshape(-1),
        "residual": torch.cat((query_residual, key_residual - query_residual)),
    }


def run_backend_qa(config: Mapping[str, Any], key_path: Path) -> dict[str, Any]:
    if BACKEND_QA.exists():
        raise RuntimeError("backend QA already exists")
    verify_freeze(config)
    verify_reviewed(config)
    assert_physical_gpu_free(config)
    import torch
    model = _load_model(config)
    # Synthetic token IDs only: no candidate-source text or tokenization is used.
    input_ids = torch.tensor([[10, 11, 12, 13, 14, 15], [20, 21, 22, 23, 0, 0]], device="cuda:0", dtype=torch.long)
    mask = torch.tensor([[1, 1, 1, 1, 1, 1], [1, 1, 1, 1, 0, 0]], device="cuda:0", dtype=torch.long)
    outputs, captured, _query, _key, value, logits = _capture_batch(model, input_ids, mask, config)
    returned = outputs.attentions[int(config["model"]["block_index"])]
    recomputed = _manual_probabilities(logits, mask)
    max_abs = float((returned - recomputed).abs().max().item())
    max_rel = float(((returned - recomputed).abs() / torch.maximum(returned.abs(), torch.tensor(1e-8, device=returned.device))).max().item())
    with torch.inference_mode():
        live_recomputed_qkv = model.gpt_neox.layers[int(config["model"]["block_index"])].attention.query_key_value(captured["hidden_input"])
    qkv_abs = float((live_recomputed_qkv - captured["qkv"]).abs().max().item())
    key_positions = [1, 2]
    q = 4
    position_ids = torch.arange(input_ids.shape[1], device=input_ids.device).unsqueeze(0).expand(input_ids.shape[0], -1)
    independent_logits = _independent_qk_logits(model, captured["qkv"], captured["hidden_input"], position_ids, int(config["model"]["block_index"]))
    qk_logit_abs = float((logits - independent_logits).abs().max().item())
    primary_qk = logits[0, :, q, key_positions].mean(dim=-1)
    independent_primary_qk = (independent_logits[0, :, q, key_positions[0]] + independent_logits[0, :, q, key_positions[1]]) / 2.0
    qk_pooling_abs = float((primary_qk - independent_primary_qk).abs().max().item())
    attention_mass = returned[0, :, q, key_positions].sum(dim=-1)
    transport = (returned[0, :, q, key_positions].unsqueeze(-1) * value[0, :, key_positions, :]).sum(dim=-2)
    manual_transport = torch.stack([sum(returned[0, h, q, k] * value[0, h, k] for k in key_positions) for h in range(value.shape[1])])
    multi_key_transport_abs = float((transport - manual_transport).abs().max().item())
    future_mask = (
        torch.arange(returned.shape[3], device=returned.device)[None, :]
        > torch.arange(returned.shape[2], device=returned.device)[:, None]
    ).view(1, 1, returned.shape[2], returned.shape[3]).expand_as(returned)
    future_max = float(returned.masked_select(future_mask).abs().max().item())
    padding_max = float(returned[1, :, :, 4:].abs().max().item())
    contributions = returned.unsqueeze(-1) * value.unsqueeze(2)
    future_message_mask = future_mask.unsqueeze(-1).expand_as(contributions)
    future_message_max = float(contributions.masked_select(future_message_mask).abs().max().item())
    padding_message_max = float(contributions[1, :, :, 4:, :].abs().max().item())
    del model
    torch.cuda.empty_cache()
    tolerance = config["backend_qa"]
    passed = bool(max_abs <= tolerance["attention_probability_atol"] and max_rel <= tolerance["attention_probability_rtol"] and qkv_abs == 0.0 and qk_logit_abs <= tolerance["qk_logit_atol"] and qk_pooling_abs <= tolerance["qk_logit_atol"] and multi_key_transport_abs <= tolerance["pooling_atol"] and future_max == 0.0 and padding_max == 0.0 and future_message_max == 0.0 and padding_message_max == 0.0 and torch.isfinite(primary_qk).all().item() and torch.isfinite(attention_mass).all().item())
    payload = {
        "schema_version": "relational_attention_edges_v1_backend_qa_v1",
        "status": "BACKEND_QA_PASS" if passed else "BACKEND_QA_FAIL",
        "freeze_sha256": sha256_file(FREEZE),
        "reviewed_sha256": sha256_file(REVIEWED),
        "gpu_uuid": config["runtime"]["gpu_uuid"],
        "synthetic_token_ids_only": True,
        "candidate_source_model_forward_run": False,
        "metrics": {"attention_probability_max_abs": max_abs, "attention_probability_max_rel": max_rel, "qkv_repeat_max_abs": qkv_abs, "qk_logit_reference_max_abs": qk_logit_abs, "multi_key_qk_mean_max_abs": qk_pooling_abs, "multi_key_transport_max_abs": multi_key_transport_abs, "future_probability_max_abs": future_max, "padding_probability_max_abs": padding_max, "future_message_max_abs": future_message_max, "padding_message_max_abs": padding_message_max},
        "tolerance": tolerance,
        "neural_training_run": False,
    }
    sign_payload(BACKEND_QA, payload, load_signing_key(key_path, config["signer"]))
    if not passed:
        raise RuntimeError("synthetic backend QA failed")
    return payload


def create_authorization(config: Mapping[str, Any], key_path: Path) -> dict[str, Any]:
    if AUTHORIZATION.exists():
        raise RuntimeError("authorization already exists")
    verify_freeze(config)
    verify_reviewed(config)
    qa = verify_signed(BACKEND_QA, config["signer"]["public_key_fingerprint_sha256"])
    if qa.get("status") != "BACKEND_QA_PASS" or qa.get("freeze_sha256") != sha256_file(FREEZE):
        raise RuntimeError("backend QA does not authorize science")
    assert_physical_gpu_free(config)
    payload = {
        "schema_version": "relational_attention_edges_v1_authorization_v1",
        "status": "AUTHORIZED",
        "freeze_sha256": sha256_file(FREEZE),
        "reviewed_sha256": sha256_file(REVIEWED),
        "backend_qa_sha256": sha256_file(BACKEND_QA),
        "gpu_uuid": config["runtime"]["gpu_uuid"],
        "one_shot": True,
        "neural_training_authorized": False,
        "retry_authorized": False,
    }
    sign_payload(AUTHORIZATION, payload, load_signing_key(key_path, config["signer"]))
    return payload


def _verify_authorization(config: Mapping[str, Any]) -> dict[str, Any]:
    verify_freeze(config)
    verify_reviewed(config)
    payload = verify_signed(AUTHORIZATION, config["signer"]["public_key_fingerprint_sha256"])
    if payload.get("status") != "AUTHORIZED" or payload.get("freeze_sha256") != sha256_file(FREEZE) or payload.get("backend_qa_sha256") != sha256_file(BACKEND_QA):
        raise RuntimeError("science authorization drift")
    return payload


def _save_npz_atomic(path: Path, arrays: Mapping[str, np.ndarray]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp.npz")
    np.savez(temporary, **arrays)
    with temporary.open("rb+") as handle:
        os.fsync(handle.fileno())
    os.replace(temporary, path)
    directory = os.open(path.parent, os.O_DIRECTORY)
    try:
        os.fsync(directory)
    finally:
        os.close(directory)


def extract_source(model: Any, source: str, config: Mapping[str, Any], cache_root: Path) -> dict[str, Any]:
    import torch
    units = read_jsonl(ROOT / config["paths"]["prepared_root"] / source / "inference_units.jsonl")
    examples = read_jsonl(ROOT / config["paths"]["prepared_root"] / source / "examples.jsonl")
    n = len(examples)
    arrays = {
        "qk": np.empty((n, 12), dtype=np.float32),
        "attention": np.empty((n, 12), dtype=np.float32),
        "transport": np.empty((n, 768), dtype=np.float32),
        "value": np.empty((n, 768), dtype=np.float32),
        "residual": np.empty((n, 1536), dtype=np.float32),
        "label": np.asarray([row["label"] for row in examples], dtype=np.int64),
        "fold": np.asarray([row["fold"] for row in examples], dtype=np.int64),
        "example_index": np.arange(n, dtype=np.int64),
        "example_id_sha256": np.asarray([hashlib.sha256(str(row["example_id"]).encode("utf-8")).digest() for row in examples], dtype="|S32"),
    }
    seen = np.zeros(n, dtype=np.uint8)
    batch_size = int(config["model"]["batch_size"])
    pad_id = int(model.config.eos_token_id or 0)
    for start in range(0, len(units), batch_size):
        batch = units[start : start + batch_size]
        maximum = max(len(unit["input_ids"]) for unit in batch)
        input_ids = torch.full((len(batch), maximum), pad_id, device="cuda:0", dtype=torch.long)
        mask = torch.zeros((len(batch), maximum), device="cuda:0", dtype=torch.long)
        for i, unit in enumerate(batch):
            length = len(unit["input_ids"])
            input_ids[i, :length] = torch.tensor(unit["input_ids"], device="cuda:0", dtype=torch.long)
            mask[i, :length] = 1
        outputs, _captured, _query, _key, value, logits = _capture_batch(model, input_ids, mask, config)
        probabilities = outputs.attentions[int(config["model"]["block_index"])]
        residuals = outputs.hidden_states[int(config["model"]["block_output_hidden_state_index"])]
        for i, unit in enumerate(batch):
            for example in unit["examples"]:
                index, q = int(example["example_index"]), int(example["query_index"])
                keys = list(map(int, example["key_positions"]))
                if seen[index] or q >= len(unit["input_ids"]) or not keys or max(keys) >= q + 1:
                    raise RuntimeError(f"invalid or duplicate extraction row: {source}:{index}")
                pooled = pool_link_features(logits, probabilities, value, residuals, i, q, keys, float(config["analysis"]["attention_log_floor"]))
                for name in ("qk", "attention", "transport", "value", "residual"):
                    arrays[name][index] = pooled[name].float().cpu().numpy()
                seen[index] = 1
    if not np.all(seen == 1) or any(
        value.dtype.kind in "fc" and not np.isfinite(value).all() for value in arrays.values()
    ):
        raise RuntimeError(f"incomplete/nonfinite feature cache: {source}")
    path = cache_root / f"{source}.features.npz"
    _save_npz_atomic(path, arrays)
    return {"source": source, "examples": n, "units": len(units), "path": path.relative_to(ROOT).as_posix(), "sha256": sha256_file(path), "shapes": {name: list(value.shape) for name, value in arrays.items()}}


def _signed_exclusive(path: Path, payload: Mapping[str, Any], key: Any) -> str:
    import base64
    import hashlib
    from cryptography.hazmat.primitives import serialization
    raw = canonical_json_bytes(dict(payload))
    public = key.public_key().public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw)
    envelope = {"payload": dict(payload), "signature": {"algorithm": "Ed25519", "message_sha256": hashlib.sha256(raw).hexdigest(), "public_key_base64": base64.b64encode(public).decode("ascii"), "public_key_fingerprint_sha256": hashlib.sha256(public).hexdigest(), "signature_base64": base64.b64encode(key.sign(raw)).decode("ascii")}}
    return exclusive_fsynced_json(path, envelope)


def run_science(config: Mapping[str, Any], key_path: Path) -> dict[str, Any]:
    _verify_authorization(config)
    assert_physical_gpu_free(config)
    assert_environment(config)
    assert_visible_gpu(config)
    validate_runtime_lineage(config)
    run_root = ROOT / config["paths"]["run_root"]
    result_root = ROOT / config["paths"]["result_root"]
    opening_target = ROOT / config["paths"]["opening"]
    for path in (run_root, result_root, opening_target):
        assert_new_destination(config, path)
    if run_root.exists() or result_root.exists() or opening_target.exists():
        raise RuntimeError("one-shot run/result/opening namespace is not absent")
    run_root.mkdir(parents=True, exist_ok=False)
    key = load_signing_key(key_path, config["signer"])
    ready = {"schema_version": "relational_attention_edges_v1_runner_ready_v1", "status": "RUNNER_READY", "freeze_sha256": sha256_file(FREEZE), "authorization_sha256": sha256_file(AUTHORIZATION), "gpu_uuid": config["runtime"]["gpu_uuid"]}
    sign_payload(run_root / "RUNNER_READY.json", ready, key)
    ack = run_root / "LAUNCH_ACK"
    deadline = time.time() + 60
    while time.time() < deadline and not ack.exists():
        time.sleep(0.25)
    if not ack.is_file() or ack.read_text(encoding="utf-8").strip() != sha256_file(run_root / "RUNNER_READY.json"):
        raise RuntimeError("launcher did not acknowledge RUNNER_READY")
    assert_physical_gpu_free(config)
    assert_visible_gpu(config)
    opening = {"schema_version": "relational_attention_edges_v1_opening_v1", "status": "OPENING_CONSUMED", "study_key": __import__("relational_attention_edges_v1").study_key(config), "freeze_sha256": sha256_file(FREEZE), "authorization_sha256": sha256_file(AUTHORIZATION), "gpu_uuid": config["runtime"]["gpu_uuid"], "retry_authorized": False}
    _signed_exclusive(opening_target, opening, key)
    sign_payload(run_root / "RUNNING.json", {**opening, "status": "RUNNING", "opening_sha256": sha256_file(opening_target)}, key)
    model = _load_model(config)
    cache_root = run_root / "feature_cache"
    cache_records = [extract_source(model, source, config, cache_root) for source in sorted(config["sources"])]
    del model
    import torch
    torch.cuda.empty_cache()
    result = analyze(config, cache_root)
    result_root.mkdir(parents=True, exist_ok=False)
    atomic_json(result_root / "result.json", result)
    payload = {"schema_version": "relational_attention_edges_v1_terminal_v1", "status": "TERMINAL_COMPLETE", "decision": result["decision"], "result_sha256": sha256_file(result_root / "result.json"), "cache_records": cache_records, "freeze_sha256": sha256_file(FREEZE), "opening_sha256": sha256_file(opening_target), "preservation_entries_sha256": verify_preservation(config), "neural_training_run": False, "optimizer_run": False, "checkpoint_written": False, "retry_authorized": False}
    sign_payload(run_root / "TERMINAL.json", payload, key)
    return payload


def _write_failure(config: Mapping[str, Any], key_path: Path, exc: BaseException) -> None:
    run_root = ROOT / config["paths"]["run_root"]
    run_root.mkdir(parents=True, exist_ok=True)
    opening_path = ROOT / config["paths"]["opening"]
    payload = {"schema_version": "relational_attention_edges_v1_terminal_v1", "status": "TERMINAL_FAILED_POSTOPENING" if opening_path.exists() else "TERMINAL_FAILED_PREOPENING", "error_type": type(exc).__name__, "error": str(exc), "traceback": traceback.format_exc(), "opening_exists": opening_path.exists(), "neural_training_run": False, "retry_authorized": False}
    try:
        sign_payload(run_root / "TERMINAL.json", payload, load_signing_key(key_path, config["signer"]))
    except Exception:
        atomic_json(run_root / "UNSIGNED_TERMINAL_FALLBACK.json", payload)


def terminalize_handshake_timeout(config: Mapping[str, Any], key_path: Path) -> dict[str, Any]:
    run_root = ROOT / config["paths"]["run_root"]
    terminal = run_root / "TERMINAL.json"
    opening = ROOT / config["paths"]["opening"]
    if not run_root.is_dir() or terminal.exists() or opening.exists():
        raise RuntimeError("handshake-timeout terminalization preconditions failed")
    payload = {
        "schema_version": "relational_attention_edges_v1_terminal_v1",
        "status": "TERMINAL_FAILED_PREOPENING",
        "error_type": "LauncherHandshakeTimeout",
        "error": "RUNNER_READY handshake timed out and coordinated cancellation completed",
        "opening_exists": False,
        "neural_training_run": False,
        "retry_authorized": False,
    }
    sign_payload(terminal, payload, load_signing_key(key_path, config["signer"]))
    return payload


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=("freeze", "reviewed", "backend-qa", "authorize", "run", "terminalize-handshake-timeout"))
    parser.add_argument("--signing-key", type=Path, default=KEY_PATH_DEFAULT)
    args = parser.parse_args()
    config = load_config()
    if args.command == "run":
        def _termination_handler(signum: int, _frame: Any) -> None:
            raise RuntimeError(f"runner received termination signal {signum}")

        signal.signal(signal.SIGTERM, _termination_handler)
        signal.signal(signal.SIGINT, _termination_handler)
    functions = {"freeze": create_freeze, "reviewed": create_reviewed, "backend-qa": run_backend_qa, "authorize": create_authorization, "run": run_science, "terminalize-handshake-timeout": terminalize_handshake_timeout}
    try:
        output = functions[args.command](config, args.signing_key)
    except BaseException as exc:
        if args.command == "run":
            _write_failure(config, args.signing_key, exc)
        raise
    print(json.dumps(output, sort_keys=True, indent=2))


if __name__ == "__main__":
    main()
