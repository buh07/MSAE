#!/usr/bin/env python3
"""Opened GENTLE outlier hook study for Attempt 11 development."""
from __future__ import annotations

import copy
import json
import os
import sys
from pathlib import Path
from typing import Any, Mapping, Sequence

os.environ.setdefault("CUBLAS_WORKSPACE_CONFIG", ":4096:8")
import numpy as np
import torch

sys.path.insert(0, str(Path(__file__).resolve().parent))

import run_atlas_rope_v5 as runtime
from atlas_rope_v6 import causal_valid_logits, inverse_transport_numpy_float64, read_jsonl, rotary_numpy_float64
from atlas_rope_v7 import ROOT

DATA = ROOT / "data/atlas_rope_v5_attempt9/GENTLE_validation"
OUTLIER_BASE_SUFFIX = "base:02edb6a646f1820cf67cdc3f"
SHIFTS = (1, 4, 8, 16, 32, 64)
FLOORS = {"max_abs": 1e-7, "relative_l2": 1e-8, "cosine_distance": 1e-12}


def _summary(a: np.ndarray, b: np.ndarray) -> dict[str, float]:
    left, right = np.asarray(a, np.float64), np.asarray(b, np.float64)
    delta = right - left
    na, nb = float(np.linalg.norm(left)), float(np.linalg.norm(right))
    return {
        "max_abs": float(np.max(np.abs(delta), initial=0.0)),
        "relative_l2": float(np.linalg.norm(delta) / max(na, 1e-12)),
        "cosine_distance": 0.0 if na == nb == 0 else float(1.0 - np.clip(np.sum(left * right) / max(na * nb, 1e-24), -1.0, 1.0)),
    }


def _split_qk(qkv: torch.Tensor) -> tuple[torch.Tensor, torch.Tensor]:
    shaped = qkv.view(1, qkv.shape[1], 12, 3 * 64).transpose(1, 2)
    query, key, _ = shaped.chunk(3, dim=-1)
    return query, key


def _rotate_float32(value: torch.Tensor, positions: Sequence[int], inv_freq: torch.Tensor) -> torch.Tensor:
    ids = torch.as_tensor([list(map(int, positions))], dtype=torch.long, device=value.device)
    frequencies = (inv_freq[None, :, None].float().expand(1, -1, 1) @ ids[:, None, :].float()).transpose(1, 2)
    embedding = torch.cat((frequencies, frequencies), dim=-1)
    cosine, sine = embedding.cos().unsqueeze(1), embedding.sin().unsqueeze(1)
    width = cosine.shape[-1]
    rotating, passing = value[..., :width], value[..., width:]
    half = width // 2
    rotated_half = torch.cat((-rotating[..., half:], rotating[..., :half]), dim=-1)
    return torch.cat((rotating * cosine + rotated_half * sine, passing), dim=-1)


def _forward(model: torch.nn.Module, unit: Mapping[str, Any], device: torch.device) -> tuple[list[torch.Tensor], np.ndarray]:
    ids = torch.as_tensor([unit["input_ids"]], dtype=torch.long, device=device)
    mask = torch.as_tensor([unit["attention_mask"]], dtype=torch.long, device=device)
    positions = torch.as_tensor([unit["position_ids"]], dtype=torch.long, device=device)
    with torch.inference_mode():
        output = model(input_ids=ids, attention_mask=mask, position_ids=positions, output_hidden_states=True, output_attentions=False, use_cache=False)
    selected = torch.as_tensor(unit["positions"], dtype=torch.long, device=device)
    target = output.hidden_states[4][0].index_select(0, selected).float().cpu().numpy().astype(np.float32)
    return [value.detach() for value in output.hidden_states], np.ascontiguousarray(target)


def _population() -> tuple[dict[str, Any], list[dict[str, Any]]]:
    references = read_jsonl(DATA / "references.jsonl")
    candidates = read_jsonl(DATA / "candidates.jsonl")
    matched = [unit for unit in references if OUTLIER_BASE_SUFFIX in str(unit["base_id"])]
    if len(matched) != 1:
        raise RuntimeError("GENTLE outlier base not unique")
    reference = dict(matched[0])
    shifted = [dict(unit) for unit in candidates if unit["base_id"] == reference["base_id"]]
    shifted.sort(key=lambda unit: int(unit["shift"]))
    if [int(unit["shift"]) for unit in shifted] != list(SHIFTS):
        raise RuntimeError("GENTLE outlier shifts incomplete")
    return reference, shifted


def run(gpu_uuid: str) -> dict[str, Any]:
    config = json.loads((ROOT / "configs/atlas_rope_v5/prescore.json").read_text())
    config = copy.deepcopy(config)
    config["runtime"]["gpu_uuid"] = gpu_uuid
    runtime._seed_runtime(int(config["seed"]))
    device = torch.device("cuda:0")
    model = runtime._load_model(config, device)
    preflight = runtime._runtime_attestation(model, device, config)
    reference, shifted = _population()

    # Unhooked repeat evidence is separate from observer-instrumented diagnosis.
    unhooked = [_forward(model, reference, device)[1] for _ in range(3)]
    repeat_exact = all(np.array_equal(unhooked[0], value) and unhooked[0].tobytes() == value.tobytes() for value in unhooked[1:])

    captures: dict[int, torch.Tensor] = {}
    handles = []
    for layer_index, layer in enumerate(model.gpt_neox.layers):
        def hook(_module: torch.nn.Module, _inputs: tuple[Any, ...], output: torch.Tensor, index: int = layer_index) -> None:
            captures[index] = output.detach().clone()
        handles.append(layer.attention.query_key_value.register_forward_hook(hook))

    stored: dict[int, dict[str, Any]] = {}
    records: list[dict[str, Any]] = []
    inv_freq = model.gpt_neox.rotary_emb.inv_freq.detach().float()
    for unit in [reference, *shifted]:
        captures.clear()
        hidden, target = _forward(model, unit, device)
        if set(captures) != set(range(12)):
            raise RuntimeError("QKV hook completeness drift")
        shift = int(unit.get("shift", 0))
        if shift == 0:
            stored[0] = {
                "qkv": {index: value.detach().cpu().numpy().astype(np.float32) for index, value in captures.items()},
                "hidden": [value.detach().cpu().numpy().astype(np.float32) for value in hidden],
                "positions": list(map(int, unit["position_ids"])), "target": target,
            }
            selected = np.asarray(unit["positions"], np.int64)
            for layer_index, value in enumerate(stored[0]["hidden"]):
                records.append({"stage": "hidden_state", "layer": layer_index, "tensor": "residual", "shift": 0,
                                **_summary(value[0, selected], value[0, selected])})
            for layer_index in range(12):
                qkv = torch.as_tensor(stored[0]["qkv"][layer_index], dtype=torch.float32, device=device)
                query, key = _split_qk(qkv)
                rotated: dict[str, np.ndarray] = {}
                for tensor_name, pre_rotary in (("Q", query), ("K", key)):
                    pre = pre_rotary.cpu().numpy().astype(np.float32)
                    post32 = _rotate_float32(pre_rotary, unit["position_ids"], inv_freq).cpu().numpy().astype(np.float32)
                    post64 = rotary_numpy_float64(pre, np.asarray([unit["position_ids"]]), inv_freq.cpu().numpy())
                    aligned = inverse_transport_numpy_float64(post32, 0, inv_freq.cpu().numpy())
                    rotated[tensor_name] = post32
                    records.extend((
                        {"stage": "pre_rotary_qk", "layer": layer_index, "tensor": tensor_name, "shift": 0, **_summary(pre, pre)},
                        {"stage": "float32_vs_float64_rotary", "layer": layer_index, "tensor": tensor_name, "shift": 0, **_summary(post64, post32)},
                        {"stage": "inverse_aligned_post_rotary", "layer": layer_index, "tensor": tensor_name, "shift": 0, **_summary(post32, aligned)},
                    ))
                logits, _ = causal_valid_logits(rotated["Q"], rotated["K"])
                records.append({"stage": "attention_logits", "layer": layer_index, "tensor": "QK", "shift": 0,
                                **_summary(logits, logits)})
            continue
        base = stored[0]
        selected = np.asarray(unit["positions"], np.int64)
        for layer_index, (left_hidden, right_hidden) in enumerate(zip(base["hidden"], hidden, strict=True)):
            right = right_hidden.detach().cpu().numpy().astype(np.float32)
            records.append({"stage": "hidden_state", "layer": layer_index, "tensor": "residual", "shift": shift,
                            **_summary(left_hidden[0, selected], right[0, selected])})
        for layer_index in range(12):
            left_qkv = torch.as_tensor(base["qkv"][layer_index], dtype=torch.float32, device=device)
            right_qkv = captures[layer_index]
            left_q, left_k = _split_qk(left_qkv)
            right_q, right_k = _split_qk(right_qkv)
            for tensor_name, left_pre, right_pre in (("Q", left_q, right_q), ("K", left_k, right_k)):
                left_np = left_pre.cpu().numpy().astype(np.float32)
                right_np = right_pre.cpu().numpy().astype(np.float32)
                left_post = _rotate_float32(left_pre, base["positions"], inv_freq).cpu().numpy().astype(np.float32)
                right_post = _rotate_float32(right_pre, unit["position_ids"], inv_freq).cpu().numpy().astype(np.float32)
                float32_shifted = _rotate_float32(left_pre, unit["position_ids"], inv_freq).cpu().numpy().astype(np.float32)
                float64_shifted = rotary_numpy_float64(left_np, np.asarray([unit["position_ids"]]), inv_freq.cpu().numpy())
                aligned = inverse_transport_numpy_float64(right_post, shift, inv_freq.cpu().numpy())
                records.extend((
                    {"stage": "pre_rotary_qk", "layer": layer_index, "tensor": tensor_name, "shift": shift, **_summary(left_np, right_np)},
                    {"stage": "float32_vs_float64_rotary", "layer": layer_index, "tensor": tensor_name, "shift": shift, **_summary(float64_shifted, float32_shifted)},
                    {"stage": "inverse_aligned_post_rotary", "layer": layer_index, "tensor": tensor_name, "shift": shift, **_summary(left_post, aligned)},
                ))
            left_q_post = _rotate_float32(left_q, base["positions"], inv_freq).cpu().numpy().astype(np.float32)
            left_k_post = _rotate_float32(left_k, base["positions"], inv_freq).cpu().numpy().astype(np.float32)
            right_q_post = _rotate_float32(right_q, unit["position_ids"], inv_freq).cpu().numpy().astype(np.float32)
            right_k_post = _rotate_float32(right_k, unit["position_ids"], inv_freq).cpu().numpy().astype(np.float32)
            left_logits, _ = causal_valid_logits(left_q_post, left_k_post)
            right_logits, _ = causal_valid_logits(right_q_post, right_k_post)
            records.append({"stage": "attention_logits", "layer": layer_index, "tensor": "QK", "shift": shift,
                            **_summary(left_logits, right_logits)})
    for handle in handles:
        handle.remove()
    hooked_reference = stored[0]["target"]
    observer = _summary(unhooked[0], hooked_reference)
    earliest: dict[str, dict[str, int | None]] = {}
    for stage in ("pre_rotary_qk", "float32_vs_float64_rotary", "inverse_aligned_post_rotary", "attention_logits", "hidden_state"):
        stage_rows = [row for row in records if row["stage"] == stage]
        earliest[stage] = {
            metric: min((int(row["layer"]) for row in stage_rows if float(row[metric]) > floor), default=None)
            for metric, floor in FLOORS.items()
        }
    return {
        "schema_version": "atlas_rope_v7_attempt11_gentle_outlier_diagnosis_v1",
        "status": "COMPLETE", "source_role": "OPENED_TECHNICAL_DEVELOPMENT",
        "base_id": reference["base_id"], "row_ids": reference["row_ids"], "shifts": [0, *SHIFTS],
        "unhooked_reference_repeats_byte_identical": repeat_exact,
        "hook_observer_error": observer, "observer_output_used_for_validation": False,
        "reporting_floors": FLOORS, "earliest_layers": earliest, "records": records,
        "runtime_preflight": preflight, "runtime_postflight": runtime._runtime_attestation(model, device, config),
        "float64_reference": "NumPy float64 rotary and inverse transport; diagnostic only",
        "parameter_update_run": False, "checkpoint_created": False, "neural_training_run": False,
    }


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(); parser.add_argument("--gpu-uuid", required=True); args = parser.parse_args()
    print(json.dumps(run(args.gpu_uuid), indent=2, sort_keys=True))
