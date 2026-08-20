#!/usr/bin/env python3
"""Separate hooked/unhooked RoPE numerical diagnosis for Atlas attempt 9."""

from __future__ import annotations

import argparse
import json
import os
os.environ.setdefault("CUBLAS_WORKSPACE_CONFIG", ":4096:8")
import sys
import time
from pathlib import Path
from typing import Any, Mapping, Sequence

import numpy as np
import torch

sys.path.insert(0, str(Path(__file__).resolve().parent))

from atlas_rope_v5 import (
    BUNDLE_SCHEMA,
    LENGTH_BINS,
    ROOT,
    RUN_ROOT,
    SHIFTS,
    assert_output_allowlist,
    atomic_json,
    canonical_array_hash,
    causal_valid_logits,
    exclusive_lock,
    inverse_transport_numpy_float64,
    new_staging,
    promote,
    read_json,
    read_jsonl,
    rotary_numpy_float64,
    sha256_file,
    sign_terminal,
    verify_envelope,
    write_signed,
)
from run_atlas_rope_v5 import (
    CALIBRATION_CAP_CANDIDATE,
    CONFIG_PATH,
    DATA_ROOT,
    EWT_AUTHORIZATION,
    _assert_not_terminal,
    _load_model,
    _runtime_attestation,
    _seed_runtime,
    _verify_authorization,
    verify_calibration_cap_candidate,
    _verify_prescore,
    _terminalize,
)


DIAGNOSTIC_ROOT = RUN_ROOT / "diagnostic"


def _diagnostic_conditions() -> tuple[list[dict[str, Any]], dict[str, Any]]:
    references = read_jsonl(DATA_ROOT / "EWT_calibration/references.jsonl")
    candidates = read_jsonl(DATA_ROOT / "EWT_calibration/candidates.jsonl")
    by_base_shift = {(str(unit["base_id"]), int(unit["shift"])): unit for unit in candidates}
    chosen: list[dict[str, Any]] = []
    chosen_ids: dict[str, list[str]] = {}
    for bin_name, _, _ in LENGTH_BINS:
        eligible = sorted((unit for unit in references if unit["length_bin"] == bin_name),
                          key=lambda unit: str(unit["unit_id"]).encode("utf-8"))
        if len(eligible) < 4:
            raise RuntimeError(f"diagnostic bin has fewer than four bases: {bin_name}")
        chosen_ids[bin_name] = [str(unit["unit_id"]) for unit in eligible[:4]]
        for reference in eligible[:4]:
            row = dict(reference); row["diagnostic_condition"] = "reference"; row["shift"] = 0
            chosen.append(row)
            for shift in SHIFTS:
                candidate = dict(by_base_shift[(str(reference["base_id"]), shift)])
                candidate["diagnostic_condition"] = "translated"
                chosen.append(candidate)
    if len(chosen) != 140 or sum(len(unit["positions"]) for unit in chosen) != 280:
        raise RuntimeError("diagnostic condition counts drift")
    manifest = {"schema_version": "atlas_rope_v5_attempt9_diagnostic_population_v1",
                "selection_rule": "first four UTF-8 unit IDs within each frozen EWT length bin; base-major reference then shifts",
                "chosen_reference_unit_ids_by_bin": chosen_ids, "condition_units": 140, "selected_rows": 280,
                "condition_unit_ids": [str(unit["unit_id"]) for unit in chosen], "batch_size": 1}
    return chosen, manifest


def _forward_one(model: torch.nn.Module, unit: Mapping[str, Any], device: torch.device) -> tuple[list[torch.Tensor], np.ndarray]:
    input_ids = torch.as_tensor([unit["input_ids"]], dtype=torch.long, device=device)
    attention = torch.as_tensor([unit["attention_mask"]], dtype=torch.long, device=device)
    positions = torch.as_tensor([unit["position_ids"]], dtype=torch.long, device=device)
    with torch.inference_mode():
        output = model(input_ids=input_ids, attention_mask=attention, position_ids=positions,
                       output_hidden_states=True, output_attentions=False, use_cache=False)
    hidden_states = [value.detach() for value in output.hidden_states]
    selected = torch.as_tensor(unit["positions"], dtype=torch.long, device=device)
    target = hidden_states[4][0].index_select(0, selected).float().cpu().numpy().astype(np.float32, copy=False)
    return hidden_states, np.ascontiguousarray(target)


def _split_qk(qkv: torch.Tensor, heads: int = 12, head_size: int = 64) -> tuple[torch.Tensor, torch.Tensor]:
    if qkv.ndim != 3 or qkv.shape[0] != 1 or qkv.shape[-1] != 3 * heads * head_size:
        raise RuntimeError(f"captured QKV shape drift: {tuple(qkv.shape)}")
    shaped = qkv.view(qkv.shape[0], qkv.shape[1], heads, 3 * head_size).transpose(1, 2)
    query, key, _ = shaped.chunk(3, dim=-1)
    if query.shape != (1, heads, qkv.shape[1], head_size) or key.shape != query.shape:
        raise RuntimeError("captured Q/K reshape drift")
    return query, key


def _rotate_float32(value: torch.Tensor, position_ids: Sequence[int], inv_freq: torch.Tensor) -> torch.Tensor:
    if value.dtype != torch.float32 or inv_freq.dtype != torch.float32:
        raise RuntimeError("float32 rotary reconstruction dtype drift")
    positions = torch.as_tensor([list(map(int, position_ids))], dtype=torch.long, device=value.device)
    expanded_inv = inv_freq[None, :, None].float().expand(1, -1, 1)
    expanded_positions = positions[:, None, :].float()
    frequencies = (expanded_inv.float() @ expanded_positions.float()).transpose(1, 2)
    embedding = torch.cat((frequencies, frequencies), dim=-1)
    cosine, sine = embedding.cos(), embedding.sin()
    cosine, sine = cosine.unsqueeze(1), sine.unsqueeze(1)
    rotary_dim = cosine.shape[-1]
    rotating, passing = value[..., :rotary_dim], value[..., rotary_dim:]
    half = rotary_dim // 2
    rotated_half = torch.cat((-rotating[..., half:], rotating[..., :half]), dim=-1)
    rotated = rotating * cosine + rotated_half * sine
    return torch.cat((rotated, passing), dim=-1)


def _error_summary(reference: np.ndarray, candidate: np.ndarray) -> dict[str, float]:
    a, b = np.asarray(reference, dtype=np.float64), np.asarray(candidate, dtype=np.float64)
    if a.shape != b.shape or not np.isfinite(a).all() or not np.isfinite(b).all():
        raise RuntimeError("diagnostic residual arrays invalid")
    difference = b - a
    norm_a, norm_b = float(np.linalg.norm(a)), float(np.linalg.norm(b))
    relative = float(np.linalg.norm(difference) / max(norm_a, 1e-12))
    if norm_a == 0 and norm_b == 0:
        cosine = 0.0
    elif norm_a == 0 or norm_b == 0:
        cosine = float("inf")
    else:
        cosine = float(1.0 - np.clip(np.sum(a * b) / max(norm_a * norm_b, 1e-24), -1.0, 1.0))
    return {"max_abs": float(np.max(np.abs(difference), initial=0.0)), "relative_l2": relative, "cosine_distance": cosine}


def _update(aggregate: dict[tuple[Any, ...], dict[str, Any]], key: tuple[Any, ...], summary: Mapping[str, float]) -> None:
    row = aggregate.setdefault(key, {"count": 0, "max_abs": 0.0, "max_relative_l2": 0.0, "max_cosine_distance": 0.0})
    row["count"] += 1
    row["max_abs"] = max(float(row["max_abs"]), float(summary["max_abs"]))
    row["max_relative_l2"] = max(float(row["max_relative_l2"]), float(summary["relative_l2"]))
    row["max_cosine_distance"] = max(float(row["max_cosine_distance"]), float(summary["cosine_distance"]))


def _diagnostic_records(aggregate: Mapping[tuple[Any, ...], Mapping[str, Any]]) -> list[dict[str, Any]]:
    output = []
    for key in sorted(aggregate, key=lambda values: tuple(str(value) for value in values)):
        residual, layer, head, shift, bin_name, tensor = key
        output.append({"residual": residual, "layer": layer, "head": head, "shift": shift,
                       "length_bin": bin_name, "tensor": tensor, **dict(aggregate[key])})
    return output


def _earliest_layers(records: Sequence[Mapping[str, Any]]) -> dict[str, int | None]:
    output: dict[str, int | None] = {}
    for residual in ("propagated_pre", "local_rotary", "aligned_total_post", "invariant_logits", "hidden_state"):
        layers = [int(row["layer"]) for row in records if row["residual"] == residual and
                  (float(row["max_relative_l2"]) > 1e-8 or float(row["max_cosine_distance"]) > 1e-12)]
        output[residual] = min(layers) if layers else None
    return output


def run(mode: str, signing_key: Path) -> dict[str, Any]:
    if mode not in {"unhooked", "hooked"}:
        raise RuntimeError("diagnostic mode must be hooked or unhooked")
    _assert_not_terminal()
    config, _ = _verify_prescore()
    _verify_authorization(EWT_AUTHORIZATION, stage="EWT_DIAGNOSTIC_ONLY")
    verify_calibration_cap_candidate()
    if (RUN_ROOT / "validation").exists():
        raise RuntimeError("validation opened before mandatory diagnosis")
    final = DIAGNOSTIC_ROOT / mode
    if final.exists():
        return verify_bundle(final, mode)
    conditions, population = _diagnostic_conditions()
    device = torch.device("cuda:0")
    with exclusive_lock("attempt-wide-gpu"):
        _seed_runtime(int(config["seed"]))
        model = _load_model(config, device)
        runtime_preflight = _runtime_attestation(model, device, config)
        captures: dict[int, torch.Tensor] = {}
        handles = []
        if mode == "hooked":
            def make_hook(layer_index: int):
                def hook(_module: torch.nn.Module, _inputs: tuple[Any, ...], output: torch.Tensor) -> None:
                    if layer_index in captures:
                        raise RuntimeError("diagnostic hook fired more than once in a forward")
                    captures[layer_index] = output.detach().clone()
                return hook
            for layer_index, layer in enumerate(model.gpt_neox.layers):
                handles.append(layer.attention.query_key_value.register_forward_hook(make_hook(layer_index)))
        started = time.time()
        hidden_rows: list[np.ndarray] = []
        row_ids: list[str] = []
        aggregate: dict[tuple[Any, ...], dict[str, Any]] = {}
        reference_by_base: dict[str, dict[str, Any]] = {}
        inv_freq = model.gpt_neox.rotary_emb.inv_freq.detach().float()
        if inv_freq.numel() != 8 or int(config["model"]["rotary_dimension"]) != 16:
            raise RuntimeError("frozen rotary dimension/inv_freq drift")
        for unit in conditions:
            captures.clear()
            hidden_states, selected = _forward_one(model, unit, device)
            hidden_rows.append(selected)
            row_ids.extend(f"diagnostic:{unit['unit_id']}:row:{index}" for index in range(len(unit["positions"])))
            if mode == "hooked" and set(captures) != set(range(len(model.gpt_neox.layers))):
                raise RuntimeError("diagnostic QKV hook completeness drift")
            base_id = str(unit["base_id"])
            if int(unit["shift"]) == 0:
                reference_by_base[base_id] = {
                    "qkv": {layer: captures[layer].detach().cpu().numpy().astype(np.float32) for layer in captures},
                    "hidden": [value.detach().cpu().numpy().astype(np.float32) for value in hidden_states],
                    "position_ids": list(map(int, unit["position_ids"])),
                }
                continue
            if mode != "hooked":
                continue
            reference = reference_by_base.get(base_id)
            if reference is None:
                raise RuntimeError("translated diagnostic condition precedes its reference")
            shift, bin_name = int(unit["shift"]), str(unit["length_bin"])
            selected_indices = np.asarray(unit["positions"], dtype=np.int64)
            for hidden_layer, (ref_hidden, shifted_hidden) in enumerate(zip(reference["hidden"], hidden_states, strict=True)):
                shifted_np = shifted_hidden.detach().cpu().numpy().astype(np.float32)
                summary = _error_summary(ref_hidden[0, selected_indices], shifted_np[0, selected_indices])
                _update(aggregate, ("hidden_state", hidden_layer, -1, shift, bin_name, "hidden"), summary)
            for layer_index in range(len(model.gpt_neox.layers)):
                ref_qkv = torch.as_tensor(reference["qkv"][layer_index], dtype=torch.float32, device=device)
                shifted_qkv = captures[layer_index]
                ref_q, ref_k = _split_qk(ref_qkv)
                shifted_q, shifted_k = _split_qk(shifted_qkv)
                ref_positions = list(map(int, reference["position_ids"]))
                shifted_positions = list(map(int, unit["position_ids"]))
                for tensor_name, ref_pre, shifted_pre in (("Q", ref_q, shifted_q), ("K", ref_k, shifted_k)):
                    ref_pre_np = ref_pre.detach().cpu().numpy().astype(np.float32)
                    shifted_pre_np = shifted_pre.detach().cpu().numpy().astype(np.float32)
                    ref_post = _rotate_float32(ref_pre, ref_positions, inv_freq).detach().cpu().numpy().astype(np.float32)
                    shifted_post = _rotate_float32(shifted_pre, shifted_positions, inv_freq).detach().cpu().numpy().astype(np.float32)
                    ref_pre_shifted_float32 = _rotate_float32(ref_pre, shifted_positions, inv_freq).detach().cpu().numpy().astype(np.float32)
                    ref_pre_shifted_float64 = rotary_numpy_float64(ref_pre_np, np.asarray([shifted_positions]), inv_freq.cpu().numpy())
                    aligned_shifted = inverse_transport_numpy_float64(shifted_post, shift, inv_freq.cpu().numpy())
                    for head in range(12):
                        _update(aggregate, ("propagated_pre", layer_index, head, shift, bin_name, tensor_name),
                                _error_summary(ref_pre_np[:, head], shifted_pre_np[:, head]))
                        _update(aggregate, ("local_rotary", layer_index, head, shift, bin_name, tensor_name),
                                _error_summary(ref_pre_shifted_float64[:, head], ref_pre_shifted_float32[:, head]))
                        _update(aggregate, ("aligned_total_post", layer_index, head, shift, bin_name, tensor_name),
                                _error_summary(ref_post[:, head], aligned_shifted[:, head]))
                ref_q_post = _rotate_float32(ref_q, ref_positions, inv_freq).detach().cpu().numpy().astype(np.float32)
                ref_k_post = _rotate_float32(ref_k, ref_positions, inv_freq).detach().cpu().numpy().astype(np.float32)
                shifted_q_post = _rotate_float32(shifted_q, shifted_positions, inv_freq).detach().cpu().numpy().astype(np.float32)
                shifted_k_post = _rotate_float32(shifted_k, shifted_positions, inv_freq).detach().cpu().numpy().astype(np.float32)
                for head in range(12):
                    ref_logits, _ = causal_valid_logits(ref_q_post[:, head:head+1], ref_k_post[:, head:head+1])
                    shifted_logits, _ = causal_valid_logits(shifted_q_post[:, head:head+1], shifted_k_post[:, head:head+1])
                    _update(aggregate, ("invariant_logits", layer_index, head, shift, bin_name, "QK"),
                            _error_summary(ref_logits, shifted_logits))
        for handle in handles:
            handle.remove()
        hidden = np.ascontiguousarray(np.concatenate(hidden_rows, axis=0), dtype=np.float32)
        if (hidden.shape != (280, 768) or len(row_ids) != 280 or len(set(row_ids)) != 280 or
                not np.isfinite(hidden).all()):
            raise RuntimeError("diagnostic hidden cache structure drift")
        stage = new_staging(f"diagnostic-{mode}", sha256_file(EWT_AUTHORIZATION))
        np.save(stage / "hidden.float32.npy", hidden, allow_pickle=False)
        atomic_json(stage / "row_ids.json", {"row_ids": row_ids})
        atomic_json(stage / "population.json", population)
        records = _diagnostic_records(aggregate) if mode == "hooked" else []
        if mode == "hooked":
            expected_records = (13 * 6 * 5) + (3 * 12 * 12 * 6 * 5 * 2) + (12 * 12 * 6 * 5)
            if len(records) != expected_records or any(int(record["count"]) != 4 for record in records):
                raise RuntimeError("diagnostic summary cell coverage drift")
            atomic_json(stage / "summaries.json", {"records": records, "earliest_layers": _earliest_layers(records),
                                                    "reporting_floors": {"relative_l2": 1e-8, "cosine_distance": 1e-12}})
        payload = {
            "schema_version": BUNDLE_SCHEMA, "bundle_kind": f"diagnostic_{mode}", "status": "COMPLETE",
            "condition_units": 140, "selected_rows": 280, "hidden_array_sha256": canonical_array_hash(hidden),
            "population_sha256": sha256_file(stage / "population.json"),
            "summaries_sha256": sha256_file(stage / "summaries.json") if mode == "hooked" else None,
            "attention_backend_switched": False, "output_attentions": False,
            "hooks": "query_key_value_linear_output_only" if mode == "hooked" else "none",
            "runtime_preflight": runtime_preflight, "runtime_postflight": _runtime_attestation(model, device, config),
            "elapsed_seconds": time.time() - started,
            "calibration_cap_candidate_sha256": sha256_file(CALIBRATION_CAP_CANDIDATE),
            "threshold_tuning_authorized": False, "model_eval": True, "inference_mode": True,
            "requires_grad": False, "labels_loaded": False, "estimator_created": False,
            "parameter_update_run": False, "checkpoint_created": False, "neural_training_run": False,
        }
        payload["artifacts"] = {path.name: {"bytes": path.stat().st_size, "sha256": sha256_file(path)}
                                for path in sorted(stage.iterdir()) if path.is_file()}
        write_signed(stage / "COMPLETE.json", payload, signing_key)
        allowed = {"hidden.float32.npy", "row_ids.json", "population.json", "COMPLETE.json"}
        if mode == "hooked":
            allowed.add("summaries.json")
        assert_output_allowlist(stage, allowed)
        promote(stage, final)
    return verify_bundle(final, mode)


def verify_bundle(final: Path, mode: str) -> dict[str, Any]:
    allowed = {"hidden.float32.npy", "row_ids.json", "population.json", "COMPLETE.json"}
    if mode == "hooked":
        allowed.add("summaries.json")
    assert_output_allowlist(final, allowed)
    payload = verify_envelope(read_json(final / "COMPLETE.json"))
    if payload.get("bundle_kind") != f"diagnostic_{mode}" or payload.get("status") != "COMPLETE":
        raise RuntimeError("diagnostic bundle completion drift")
    if set(payload.get("artifacts", {})) != allowed - {"COMPLETE.json"}:
        raise RuntimeError("diagnostic artifact inventory is not exact")
    for name, spec in payload["artifacts"].items():
        path = final / name
        if sha256_file(path) != spec["sha256"] or path.stat().st_size != spec["bytes"]:
            raise RuntimeError(f"diagnostic artifact drift: {mode}/{name}")
    hidden = np.load(final / "hidden.float32.npy", allow_pickle=False)
    if hidden.dtype != np.float32 or hidden.shape != (280, 768) or not hidden.flags.c_contiguous or not np.isfinite(hidden).all():
        raise RuntimeError("diagnostic hidden structure drift")
    if canonical_array_hash(hidden) != payload["hidden_array_sha256"]:
        raise RuntimeError("diagnostic canonical hidden hash drift")
    conditions, expected_population = _diagnostic_conditions()
    if read_json(final / "population.json") != expected_population or sha256_file(final / "population.json") != payload.get("population_sha256"):
        raise RuntimeError("diagnostic population lineage drift")
    expected_row_ids = [f"diagnostic:{unit['unit_id']}:row:{index}"
                        for unit in conditions for index in range(len(unit["positions"]))]
    if (read_json(final / "row_ids.json") != {"row_ids": expected_row_ids} or len(expected_row_ids) != 280 or
            len(set(expected_row_ids)) != 280):
        raise RuntimeError("diagnostic row-ID lineage drift")
    if mode == "hooked":
        summary = read_json(final / "summaries.json")
        expected_records = (13 * 6 * 5) + (3 * 12 * 12 * 6 * 5 * 2) + (12 * 12 * 6 * 5)
        records = summary.get("records", [])
        if (sha256_file(final / "summaries.json") != payload.get("summaries_sha256") or
                len(records) != expected_records or any(int(row.get("count", -1)) != 4 for row in records)):
            raise RuntimeError("diagnostic summary completeness drift")
        numeric_keys = ("max_abs", "max_relative_l2", "max_cosine_distance")
        if any(not all(np.isfinite(float(row[key])) for key in numeric_keys) for row in records):
            raise RuntimeError("diagnostic summary contains nonfinite values")
        if summary.get("earliest_layers") != _earliest_layers(records):
            raise RuntimeError("diagnostic earliest-layer summary drift")
    elif payload.get("summaries_sha256") is not None:
        raise RuntimeError("unhooked diagnostic unexpectedly binds summaries")
    config = read_json(CONFIG_PATH)
    if payload.get("calibration_cap_candidate_sha256") != sha256_file(CALIBRATION_CAP_CANDIDATE):
        raise RuntimeError("diagnostic calibration-cap lineage drift")
    for phase in ("runtime_preflight", "runtime_postflight"):
        runtime = payload.get(phase, {})
        if (runtime.get("required_library_check", {}).get("status") != "PASS" or
                runtime.get("attention_backend") != "sdpa" or
                runtime.get("gpu_uuid") != config["runtime"]["gpu_uuid"] or
                runtime.get("source_hashes") != config["runtime"]["source_hashes"]):
            raise RuntimeError(f"diagnostic {phase} attestation drift")
    return payload


def observer_comparison(hooked_hidden: np.ndarray, unhooked_hidden: np.ndarray,
                        hooked_rows: Mapping[str, Any], unhooked_rows: Mapping[str, Any],
                        hooked_population_sha256: str, unhooked_population_sha256: str) -> dict[str, bool]:
    return {
        "row_ids_equal": dict(hooked_rows) == dict(unhooked_rows),
        "population_equal": hooked_population_sha256 == unhooked_population_sha256,
        "array_equal": bool(np.array_equal(hooked_hidden, unhooked_hidden)),
        "c_order_bytes_equal": hooked_hidden.tobytes(order="C") == unhooked_hidden.tobytes(order="C"),
    }


def compare(signing_key: Path) -> dict[str, Any]:
    hooked = verify_bundle(DIAGNOSTIC_ROOT / "hooked", "hooked")
    unhooked = verify_bundle(DIAGNOSTIC_ROOT / "unhooked", "unhooked")
    hooked_hidden = np.load(DIAGNOSTIC_ROOT / "hooked/hidden.float32.npy", allow_pickle=False)
    unhooked_hidden = np.load(DIAGNOSTIC_ROOT / "unhooked/hidden.float32.npy", allow_pickle=False)
    checks = observer_comparison(
        hooked_hidden, unhooked_hidden,
        read_json(DIAGNOSTIC_ROOT / "hooked/row_ids.json"), read_json(DIAGNOSTIC_ROOT / "unhooked/row_ids.json"),
        sha256_file(DIAGNOSTIC_ROOT / "hooked/population.json"), sha256_file(DIAGNOSTIC_ROOT / "unhooked/population.json"),
    )
    passed = all(checks.values())
    if not passed:
        sign_terminal(signing_key, status="TERMINAL_TECHNICAL_DIAGNOSTIC_INVALID",
                      reason="hooked and unhooked hidden states are not byte-identical",
                      lineage={"hooked_complete_sha256": sha256_file(DIAGNOSTIC_ROOT / "hooked/COMPLETE.json"),
                               "unhooked_complete_sha256": sha256_file(DIAGNOSTIC_ROOT / "unhooked/COMPLETE.json")})
        raise RuntimeError("diagnostic observer comparison failed and terminalized")
    path = DIAGNOSTIC_ROOT / "DIAGNOSTIC_COMPLETE.json"
    payload = {"schema_version": "atlas_rope_v5_attempt9_diagnostic_complete_v1", "status": "PASS",
               "hooked_complete_sha256": sha256_file(DIAGNOSTIC_ROOT / "hooked/COMPLETE.json"),
               "unhooked_complete_sha256": sha256_file(DIAGNOSTIC_ROOT / "unhooked/COMPLETE.json"),
               "summaries_sha256": sha256_file(DIAGNOSTIC_ROOT / "hooked/summaries.json"),
               "observer_checks": checks,
               "calibration_cap_candidate_sha256": sha256_file(CALIBRATION_CAP_CANDIDATE),
               "threshold_tuning_authorized": False, "neural_training_authorized": False}
    if not path.exists():
        write_signed(path, payload, signing_key)
    observed = verify_envelope(read_json(path))
    if observed != payload:
        raise RuntimeError("diagnostic completion drift")
    return observed


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=("unhooked", "hooked", "compare"))
    parser.add_argument("--signing-key", type=Path, required=True)
    args = parser.parse_args()
    try:
        result = compare(args.signing_key) if args.mode == "compare" else run(args.mode, args.signing_key)
    except Exception as error:
        if EWT_AUTHORIZATION.exists():
            _terminalize(args.signing_key, status="TERMINAL_TECHNICAL_DIAGNOSTIC_INVALID",
                         reason=f"diagnostic {args.mode} failed: {type(error).__name__}: {error}")
        raise
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
