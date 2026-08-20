#!/usr/bin/env python3
"""Frozen transformer-realistic constructed bridge and conditional methods benchmark v1."""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
import math
import os
import platform
import random
import secrets
import shutil
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

import numpy as np
import torch
import torch.nn.functional as F

ROOT = Path(os.environ.get("MSAE_ROOT", Path.cwd()))
BRIDGE_CONFIG = ROOT / "configs/transformer_realistic_bridge_v1_r2/run.json"
METHODS_CONFIG = ROOT / "configs/transformer_realistic_methods_v1_r2/run.json"
PLAN = ROOT / "PLAN_TRANSFORMER_REALISTIC_BRIDGE_V1_R2.md"
RECOVERY_ROOT = ROOT / "reports/provenance/transformer_realistic_bridge_v1_r2_recovery"
RECOVERY_AUTH = RECOVERY_ROOT / "RECOVERY_AUTHORIZATION.json"
RECOVERY_PARITY = RECOVERY_ROOT / "PRELOCK_PARITY.json"
RECOVERY_CONTINUITY = RECOVERY_ROOT / "PAYLOAD_CONTINUITY.json"
RECOVERY_BINDING_SUPPLEMENT = RECOVERY_ROOT / "REVIEW_BINDING_PRESERVATION_SUPPLEMENT.json"
RECOVERY_SUPERSEDED_INDEX = RECOVERY_ROOT / "SUPERSEDED_PARITY_INDEX.json"
RECOVERY_VERIFIER = ROOT / "scripts/verify_transformer_realistic_bridge_v1_r2_recovery.py"
REGIME_ORDER = (
    "ideal_hard",
    "soft_attention",
    "residual_bypass",
    "layernorm",
    "correlated_superposition",
    "realistic_noisy",
)
SCOPE_BRIDGE = {
    "constructed_synthetic_model": True,
    "natural_model_claim": False,
    "natural_prompt_assay": False,
    "k2_evaluated": False,
    "representation_methods_evaluated": False,
    "training_performed": False,
}
SCOPE_METHODS = {
    "constructed_synthetic_model": True,
    "natural_model_claim": False,
    "natural_prompt_assay": False,
    "k2_evaluated": False,
}


def loadj(path: Path) -> Any:
    return json.loads(path.read_text())


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def canonical(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()


def atomic_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        raise RuntimeError(f"immutable output exists: {path}")
    tmp = path.with_name(path.name + f".tmp.{os.getpid()}")
    data = json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n"
    with tmp.open("x") as f:
        f.write(data)
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, path)
    fd = os.open(path.parent, os.O_DIRECTORY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def atomic_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        raise RuntimeError(f"immutable output exists: {path}")
    tmp = path.with_name(path.name + f".tmp.{os.getpid()}")
    with tmp.open("x") as f:
        f.write(text)
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, path)


def config(path: Path) -> dict[str, Any]:
    cfg = loadj(path)
    if not isinstance(cfg, dict):
        raise TypeError("config must be object")
    return cfg


def seed32(*parts: Any) -> int:
    return int.from_bytes(hashlib.sha256("|".join(map(str, parts)).encode()).digest()[:4], "little")


def rng_for(*parts: Any) -> np.random.Generator:
    return np.random.default_rng(seed32(*parts))


def row_margin(logits: np.ndarray, targets: np.ndarray) -> np.ndarray:
    n, v = logits.shape
    return (v * logits[np.arange(n), targets] - logits.sum(axis=1, dtype=np.float64)) / (v - 1)


def centered(x: np.ndarray) -> np.ndarray:
    return x - x.mean(axis=1, keepdims=True, dtype=np.float64)


def regime_cfg(cfg: Mapping[str, Any], name: str) -> Mapping[str, Any]:
    matches = [r for r in cfg["regimes"] if r["name"] == name]
    if len(matches) != 1:
        raise RuntimeError(f"regime registry mismatch: {name}")
    return matches[0]


def model_matrices(cfg: Mapping[str, Any], regime: str) -> dict[str, np.ndarray]:
    m = cfg["model"]
    r = regime_cfg(cfg, regime)
    rc, rn, ro = m["routing_causal_dim"], m["routing_nuisance_dim"], m["routing_observed_dim"]
    pd, sd, vn, vo = m["private_dim"], m["shared_dim"], m["value_nuisance_dim"], m["value_observed_dim"]
    route = np.zeros((ro, rc + rn), dtype=np.float32)
    route[:, :rc] = np.eye(ro, rc, dtype=np.float32)
    rr = rng_for(cfg["seed"], "route_mix", regime).normal(size=(ro, rn)).astype(np.float32)
    rr /= np.maximum(np.linalg.norm(rr, axis=0, keepdims=True), 1e-8)
    route[:, rc:] = np.float32(m["nuisance_gain"] if r["superposition"] else 0.02) * rr
    value = np.zeros((vo, pd + sd + vn), dtype=np.float32)
    if r["superposition"]:
        q, _ = np.linalg.qr(rng_for(cfg["seed"], "causal_mix", regime).normal(size=(vo, pd + sd)))
        causal = q[:, : pd + sd].astype(np.float32)
        value[:, :pd] = np.float32(m["private_gain"]) * causal[:, :pd]
        value[:, pd : pd + sd] = np.float32(m["shared_gain"]) * causal[:, pd : pd + sd]
        nm = rng_for(cfg["seed"], "value_nuisance_mix", regime).normal(size=(vo, vn)).astype(np.float32)
        nm /= np.maximum(np.linalg.norm(nm, axis=0, keepdims=True), 1e-8)
        value[:, pd + sd :] = np.float32(m["nuisance_gain"]) * nm
    else:
        value[:pd, :pd] = np.float32(m["private_gain"]) * np.eye(pd, dtype=np.float32)
        value[pd : pd + sd, pd : pd + sd] = np.float32(m["shared_gain"]) * np.eye(sd, dtype=np.float32)
        # Nuisance is present but weak before the explicit superposition regime.
        nm = rng_for(cfg["seed"], "value_nuisance_diag", regime).normal(size=(vo, vn)).astype(np.float32)
        nm /= np.maximum(np.linalg.norm(nm, axis=0, keepdims=True), 1e-8)
        value[:, pd + sd :] = np.float32(0.01) * nm
    # Fixed readout is the least-squares decoder for the causal private+shared prototypes.
    protos = []
    for value_id in range(m["target_values"]):
        latent = np.zeros(pd + sd + vn, dtype=np.float32)
        latent[value_id] = 1.0
        latent[pd + value_id % sd] = 1.0
        protos.append(value @ latent)
    h = np.stack(protos).astype(np.float64)
    decoder = (np.linalg.pinv(h) @ (np.eye(m["target_values"]) * m["readout_gain"])).astype(np.float32)
    qres = rng_for(cfg["seed"], "query_residual", regime).normal(size=vo).astype(np.float32)
    qres /= np.linalg.norm(qres)
    return {"route_mix": route, "value_mix": value, "decoder": decoder, "query_residual": qres}


def make_rows(stage: str, seed: int, regimes: Sequence[str], blocks: int, rows_per_block: int, target_values: int) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for regime_i, regime in enumerate(regimes):
        for block in range(blocks):
            rg = rng_for(seed, stage, regime, block)
            if rows_per_block == target_values:
                targets = list(range(target_values))
            else:
                offset = (block * rows_per_block) % target_values
                targets = [(offset + i) % target_values for i in range(rows_per_block)]
            rg.shuffle(targets)
            for within, target in enumerate(targets):
                candidates = [x for x in range(target_values) if x != target]
                contrast, sham = rg.choice(candidates, size=2, replace=False).tolist()
                j = int(rg.integers(0, 8))
                k_choices = [x for x in range(8) if x != j]
                k = int(rg.choice(k_choices))
                rows.append(
                    {
                        "row_id": f"{stage}:{regime}:{block:02d}:{within:02d}",
                        "stage": stage,
                        "regime": regime,
                        "regime_index": regime_i,
                        "block": block,
                        "within_block": within,
                        "target": int(target),
                        "contrast": int(contrast),
                        "sham": int(sham),
                        "causal_index": j,
                        "control_index": k,
                        "noise_stratum": [0.5, 1.0, 1.5][block % 3],
                        "row_seed": int(rg.integers(0, 2**31 - 1)),
                    }
                )
    return rows


def write_rows(path: Path, rows: Sequence[Mapping[str, Any]]) -> None:
    if path.exists():
        raise RuntimeError(f"prepared payload exists: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x") as f:
        for row in rows:
            f.write(json.dumps(row, sort_keys=True) + "\n")
        f.flush()
        os.fsync(f.fileno())


def read_rows(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text().splitlines() if line]


def factor_arrays(rows: Sequence[Mapping[str, Any]], cfg: Mapping[str, Any], regime: str) -> dict[str, np.ndarray]:
    m = cfg["model"]
    n, s = len(rows), m["sources"]
    rc, rn = m["routing_causal_dim"], m["routing_nuisance_dim"]
    pd, sd, vn = m["private_dim"], m["shared_dim"], m["value_nuisance_dim"]
    q = np.zeros((n, rc), np.float32)
    key_base = np.zeros((n, s, rc), np.float32)
    key_nuis_base = np.zeros((n, s, rn), np.float32)
    values_base = np.zeros((n, s), np.int64)
    private_base = np.zeros((n, s, pd), np.float32)
    shared_base = np.zeros((n, s, sd), np.float32)
    value_nuis_base = np.zeros((n, s, vn), np.float32)
    j = np.array([r["causal_index"] for r in rows], np.int64)
    k = np.array([r["control_index"] for r in rows], np.int64)
    target = np.array([r["target"] for r in rows], np.int64)
    contrast = np.array([r["contrast"] for r in rows], np.int64)
    sham = np.array([r["sham"] for r in rows], np.int64)
    noise_base = float(regime_cfg(cfg, regime)["noise"])
    for i, row in enumerate(rows):
        rg = rng_for(cfg["seed"], regime, row["row_seed"], "base")
        q[i, target[i]] = 1.0
        # Distractor target-coordinate scores are deliberately neither matching nor uniform.
        scores = np.linspace(m["distractor_score_low"], m["distractor_score_high"], s, dtype=np.float32)
        rg.shuffle(scores)
        for pos in range(s):
            vec = rg.normal(size=rc).astype(np.float32)
            vec[target[i]] = 0.0
            vec /= max(float(np.linalg.norm(vec)), 1e-8)
            key_base[i, pos] = 0.15 * vec
            key_base[i, pos, target[i]] = scores[pos]
        key_base[i, j[i]] = 0.0
        key_base[i, j[i], target[i]] = m["soft_score"]
        candidates = [v for v in range(m["target_values"]) if v not in {target[i], contrast[i], sham[i]}]
        rg.shuffle(candidates)
        vals = (candidates * math.ceil(s / len(candidates)))[:s]
        values_base[i] = np.asarray(vals, np.int64)
        for pos, value_id in enumerate(values_base[i]):
            private_base[i, pos, value_id] = 1.0
            shared_base[i, pos, value_id % sd] = 1.0
        # Base nuisance is shared across conditions and sources; only j gets matched condition-specific nuisance.
        key_nuis_base[i] = rg.normal(size=(s, rn)).astype(np.float32)
        value_nuis_base[i] = rg.normal(size=(s, vn)).astype(np.float32)
    out: dict[str, np.ndarray] = {"query": q, "j": j, "k": k, "target": target, "contrast_id": contrast, "sham_id": sham}
    for condition, ids, route_clean, nuisance_tag in (
        ("clean", target, True, "clean"),
        ("corrupt", contrast, False, "corrupt"),
        ("hybrid", target, True, "corrupt"),
        ("sham", sham, True, "corrupt"),
    ):
        kc = key_base.copy()
        kn = key_nuis_base.copy()
        pr = private_base.copy()
        sh = shared_base.copy()
        nv = value_nuis_base.copy()
        for i, row in enumerate(rows):
            jj = j[i]
            kc[i, jj] = 0.0
            kc[i, jj, target[i]] = m["soft_score"] if route_clean else -m["soft_score"]
            rg = rng_for(cfg["seed"], regime, row["row_seed"], nuisance_tag)
            scale = noise_base * float(row["noise_stratum"])
            # Nonzero matched nuisance exists in every regime; final regime amplifies it.
            kn[i, jj] = rg.normal(size=rn).astype(np.float32) * (0.15 + scale)
            nv[i, jj] = rg.normal(size=vn).astype(np.float32) * (0.15 + scale)
            pr[i, jj] = 0.0
            pr[i, jj, ids[i]] = 1.0
            sh[i, jj] = 0.0
            sh[i, jj, ids[i] % sd] = 1.0
        out[f"key_causal_{condition}"] = kc
        out[f"key_nuisance_{condition}"] = kn
        out[f"private_{condition}"] = pr
        out[f"shared_{condition}"] = sh
        out[f"value_nuisance_{condition}"] = nv
    # Explicit partial causal-factor hybrids.
    out["private_partial"] = out["private_hybrid"].copy()
    out["shared_partial"] = out["shared_hybrid"].copy()
    return out


def observed_np(f: Mapping[str, np.ndarray], mats: Mapping[str, np.ndarray], condition: str) -> tuple[np.ndarray, np.ndarray]:
    key_latent = np.concatenate((f[f"key_causal_{condition}"], f[f"key_nuisance_{condition}"]), axis=-1)
    val_latent = np.concatenate((f[f"private_{condition}"], f[f"shared_{condition}"], f[f"value_nuisance_{condition}"]), axis=-1)
    return key_latent @ mats["route_mix"].T, val_latent @ mats["value_mix"].T


def partial_value_np(f: Mapping[str, np.ndarray], mats: Mapping[str, np.ndarray], private_condition: str, shared_condition: str) -> np.ndarray:
    pr = f[f"private_{private_condition}"]
    sh = f[f"shared_{shared_condition}"]
    latent = np.concatenate((pr, sh, f["value_nuisance_corrupt"]), axis=-1)
    return latent @ mats["value_mix"].T


def torch_graph(
    query: torch.Tensor,
    keys: torch.Tensor,
    attention_values: torch.Tensor,
    bypass_values: torch.Tensor,
    mats: Mapping[str, np.ndarray],
    cfg: Mapping[str, Any],
    regime: str,
    causal_index: torch.Tensor,
) -> dict[str, torch.Tensor]:
    r, m = regime_cfg(cfg, regime), cfg["model"]
    scores = torch.einsum("nd,nsd->ns", query, keys)
    if r["hard_attention"]:
        idx = torch.argmax(scores, dim=1)
        weights = F.one_hot(idx, num_classes=m["sources"]).to(torch.float32)
    else:
        weights = torch.softmax(scores, dim=-1)
    att = torch.einsum("ns,nsv->nv", weights, attention_values)
    row_index = torch.arange(query.shape[0], device=query.device)
    bypass = bypass_values[row_index, causal_index] if r["bypass"] else torch.zeros_like(att)
    qres = torch.as_tensor(mats["query_residual"], dtype=torch.float32, device=query.device)[None, :]
    raw = np.float32(m["attention_gain"]) * att + np.float32(m["bypass_gain"] if r["bypass"] else 0.0) * bypass + np.float32(m["query_residual_gain"]) * qres
    state = F.layer_norm(raw, (raw.shape[-1],), eps=m["layernorm_eps"]) if r["layernorm"] else raw
    decoder = torch.as_tensor(mats["decoder"], dtype=torch.float32, device=query.device)
    logits = state @ decoder
    return {"scores": scores, "weights": weights, "attention_transport": att, "bypass": bypass, "pre_readout": raw, "state": state, "logits": logits}


def numpy_graph(query: np.ndarray, keys: np.ndarray, attention_values: np.ndarray, bypass_values: np.ndarray, mats: Mapping[str, np.ndarray], cfg: Mapping[str, Any], regime: str, causal_index: np.ndarray) -> dict[str, np.ndarray]:
    r, m = regime_cfg(cfg, regime), cfg["model"]
    scores = np.einsum("nd,nsd->ns", query, keys, optimize=False).astype(np.float32)
    if r["hard_attention"]:
        idx = np.argmax(scores, axis=1)
        weights = np.eye(m["sources"], dtype=np.float32)[idx]
    else:
        shifted = scores - np.max(scores, axis=1, keepdims=True)
        ex = np.exp(shifted, dtype=np.float32)
        weights = (ex / ex.sum(axis=1, keepdims=True, dtype=np.float32)).astype(np.float32)
    att = np.sum(weights[:, :, None] * attention_values, axis=1, dtype=np.float32)
    bypass = bypass_values[np.arange(query.shape[0]), causal_index] if r["bypass"] else np.zeros_like(att)
    raw = np.float32(m["attention_gain"]) * att + np.float32(m["bypass_gain"] if r["bypass"] else 0.0) * bypass + np.float32(m["query_residual_gain"]) * mats["query_residual"][None, :]
    if r["layernorm"]:
        mean = raw.mean(axis=-1, keepdims=True, dtype=np.float32)
        var = ((raw - mean) ** 2).mean(axis=-1, keepdims=True, dtype=np.float32)
        state = ((raw - mean) / np.sqrt(var + np.float32(m["layernorm_eps"]), dtype=np.float32)).astype(np.float32)
    else:
        state = raw
    logits = (state @ mats["decoder"]).astype(np.float32)
    return {"scores": scores, "weights": weights, "attention_transport": att, "bypass": bypass, "pre_readout": raw, "state": state, "logits": logits}


def _tensor(x: np.ndarray, device: torch.device) -> torch.Tensor:
    dtype = torch.long if np.issubdtype(x.dtype, np.integer) else torch.float32
    return torch.as_tensor(x, dtype=dtype, device=device)


def insert_delta_torch(keys: torch.Tensor, values: torch.Tensor, delta: torch.Tensor, indices: torch.Tensor, sign: float = 1.0) -> tuple[torch.Tensor, torch.Tensor]:
    """The one registered observed-state insertion operator used by bridge and methods."""
    out_keys, out_values = keys.clone(), values.clone()
    rows = torch.arange(delta.shape[0], device=delta.device)
    key_dim = keys.shape[-1]
    out_keys[rows, indices] += sign * delta[:, :key_dim]
    out_values[rows, indices] += sign * delta[:, key_dim:]
    return out_keys, out_values


def insert_delta_numpy(keys: np.ndarray, values: np.ndarray, delta: np.ndarray, indices: np.ndarray, sign: float = 1.0) -> tuple[np.ndarray, np.ndarray]:
    out_keys, out_values = keys.copy(), values.copy()
    rows = np.arange(delta.shape[0])
    key_dim = keys.shape[-1]
    out_keys[rows, indices] += np.float32(sign) * delta[:, :key_dim]
    out_values[rows, indices] += np.float32(sign) * delta[:, key_dim:]
    return out_keys, out_values


def torch_forward(rows: Sequence[Mapping[str, Any]], cfg: Mapping[str, Any], regime: str, device: torch.device, keep_tensors: bool = False) -> dict[str, Any]:
    mats = model_matrices(cfg, regime)
    f = factor_arrays(rows, cfg, regime)
    observed = {name: observed_np(f, mats, name) for name in ("clean", "corrupt", "hybrid", "sham")}
    kp = {name: _tensor(observed[name][0], device) for name in observed}
    vp = {name: _tensor(observed[name][1], device) for name in observed}
    q = _tensor(f["query"], device)
    j = _tensor(f["j"], device)
    k = _tensor(f["k"], device)
    idx = torch.arange(len(rows), device=device)
    private_val = _tensor(partial_value_np(f, mats, "hybrid", "corrupt"), device)
    shared_val = _tensor(partial_value_np(f, mats, "corrupt", "hybrid"), device)
    private_sham_val = _tensor(partial_value_np(f, mats, "sham", "corrupt"), device)
    shared_sham_val = _tensor(partial_value_np(f, mats, "corrupt", "sham"), device)

    graph: dict[str, dict[str, torch.Tensor]] = {}
    for name in ("clean", "corrupt", "hybrid", "sham"):
        graph[name] = torch_graph(q, kp[name], vp[name], vp[name], mats, cfg, regime, j)
    graph["routing_only"] = torch_graph(q, kp["hybrid"], vp["corrupt"], vp["corrupt"], mats, cfg, regime, j)
    graph["private_only"] = torch_graph(q, kp["corrupt"], private_val, private_val, mats, cfg, regime, j)
    graph["shared_only"] = torch_graph(q, kp["corrupt"], shared_val, shared_val, mats, cfg, regime, j)
    graph["routing_private"] = torch_graph(q, kp["hybrid"], private_val, private_val, mats, cfg, regime, j)
    graph["routing_shared"] = torch_graph(q, kp["hybrid"], shared_val, shared_val, mats, cfg, regime, j)
    graph["attention_only"] = torch_graph(q, kp["hybrid"], vp["hybrid"], vp["corrupt"], mats, cfg, regime, j)
    graph["bypass_only"] = torch_graph(q, kp["corrupt"], vp["corrupt"], vp["hybrid"], mats, cfg, regime, j)

    # Complete observed-state skyline: only j differs across paired source states.
    state_keys = kp["corrupt"].clone()
    state_vals = vp["corrupt"].clone()
    state_keys[idx, j] = kp["clean"][idx, j]
    state_vals[idx, j] = vp["clean"][idx, j]
    graph["state_skyline"] = torch_graph(q, state_keys, state_vals, state_vals, mats, cfg, regime, j)

    # Same-site matched noncausal control at j; its direction is orthogonal to query/readout target.
    dk = kp["hybrid"][idx, j] - kp["corrupt"][idx, j]
    dv = vp["hybrid"][idx, j] - vp["corrupt"][idx, j]
    gt_delta = torch.cat((dk, dv), dim=1)
    gt_keys, gt_vals = insert_delta_torch(kp["corrupt"], vp["corrupt"], gt_delta, j)
    graph["ground_truth_patch"] = torch_graph(q, gt_keys, gt_vals, gt_vals, mats, cfg, regime, j)
    control_k = []
    control_v = []
    decoder = _tensor(mats["decoder"], device)
    targets = _tensor(f["target"], device)
    for i, row in enumerate(rows):
        rg = rng_for(cfg["seed"], regime, row["row_seed"], "matched_control")
        gk = _tensor(rg.normal(size=dk.shape[1]).astype(np.float32), device)
        gv = _tensor(rg.normal(size=dv.shape[1]).astype(np.float32), device)
        qi = q[i]
        gk = gk - torch.dot(gk, qi) * qi / torch.clamp(torch.dot(qi, qi), min=1e-8)
        readout_target = decoder[:, targets[i]]
        gv = gv - torch.dot(gv, readout_target) * readout_target / torch.clamp(torch.dot(readout_target, readout_target), min=1e-8)
        g = torch.cat((gk, gv))
        d = torch.cat((dk[i], dv[i]))
        g = g * (torch.linalg.vector_norm(d) / torch.clamp(torch.linalg.vector_norm(g), min=1e-8))
        control_k.append(g[: dk.shape[1]])
        control_v.append(g[dk.shape[1] :])
    cdk = torch.stack(control_k)
    cdv = torch.stack(control_v)
    control_keys = kp["corrupt"].clone()
    control_vals = vp["corrupt"].clone()
    control_keys[idx, j] += cdk
    control_vals[idx, j] += cdv
    graph["control"] = torch_graph(q, control_keys, control_vals, control_vals, mats, cfg, regime, j)

    # Direct factor omissions used for necessity.
    graph["routing_omitted"] = torch_graph(q, kp["corrupt"], vp["hybrid"], vp["hybrid"], mats, cfg, regime, j)
    graph["value_omitted"] = graph["routing_only"]

    out_t: dict[str, torch.Tensor] = {
        "query": q,
        "j": j,
        "k": k,
        "target": targets,
        "contrast_id": _tensor(f["contrast_id"], device),
        "keys_clean": kp["clean"],
        "keys_corrupt": kp["corrupt"],
        "keys_hybrid": kp["hybrid"],
        "values_clean": vp["clean"],
        "values_corrupt": vp["corrupt"],
        "values_hybrid": vp["hybrid"],
        "values_sham": vp["sham"],
        "ground_truth_delta": gt_delta,
        "routing_delta": torch.cat((dk, torch.zeros_like(dv)), dim=1),
        "private_delta": torch.cat((torch.zeros_like(dk), private_val[idx, j] - vp["corrupt"][idx, j]), dim=1),
        "shared_delta": torch.cat((torch.zeros_like(dk), shared_val[idx, j] - vp["corrupt"][idx, j]), dim=1),
        "routing_private_delta": torch.cat((dk, private_val[idx, j] - vp["corrupt"][idx, j]), dim=1),
        "routing_shared_delta": torch.cat((dk, shared_val[idx, j] - vp["corrupt"][idx, j]), dim=1),
        "sham_routing_delta": torch.cat((kp["sham"][idx, j] - kp["corrupt"][idx, j], torch.zeros_like(dv)), dim=1),
        "sham_private_delta": torch.cat((torch.zeros_like(dk), private_sham_val[idx, j] - vp["corrupt"][idx, j]), dim=1),
        "sham_shared_delta": torch.cat((torch.zeros_like(dk), shared_sham_val[idx, j] - vp["corrupt"][idx, j]), dim=1),
        "sham_routing_private_delta": torch.cat((kp["sham"][idx, j] - kp["corrupt"][idx, j], private_sham_val[idx, j] - vp["corrupt"][idx, j]), dim=1),
        "sham_routing_shared_delta": torch.cat((kp["sham"][idx, j] - kp["corrupt"][idx, j], shared_sham_val[idx, j] - vp["corrupt"][idx, j]), dim=1),
        "sham_delta": torch.cat((kp["sham"][idx, j] - kp["corrupt"][idx, j], vp["sham"][idx, j] - vp["corrupt"][idx, j]), dim=1),
        "control_delta": torch.cat((cdk, cdv), dim=1),
    }
    for name, rec in graph.items():
        for field, value in rec.items():
            out_t[f"{field}_{name}"] = value
    out_t["logits_output_skyline"] = graph["clean"]["logits"].clone()
    out_t["control_norm_ratio"] = torch.linalg.vector_norm(out_t["control_delta"], dim=1) / torch.clamp(torch.linalg.vector_norm(out_t["ground_truth_delta"], dim=1), min=1e-8)
    # Corrupt nuisance must be byte-identical in the hybrid factor state.
    nuisance_equal = np.array_equal(f["key_nuisance_hybrid"], f["key_nuisance_corrupt"]) and np.array_equal(f["value_nuisance_hybrid"], f["value_nuisance_corrupt"])
    out_t["hybrid_nuisance_preserved"] = torch.full((len(rows),), nuisance_equal, dtype=torch.bool, device=device)
    if device.type == "cuda":
        torch.cuda.synchronize(device)
    if keep_tensors:
        return out_t
    return {name: value.detach().cpu().numpy() for name, value in out_t.items()}


def numpy_forward(rows: Sequence[Mapping[str, Any]], cfg: Mapping[str, Any], regime: str) -> dict[str, np.ndarray]:
    mats = model_matrices(cfg, regime)
    f = factor_arrays(rows, cfg, regime)
    observed = {name: observed_np(f, mats, name) for name in ("clean", "corrupt", "hybrid", "sham")}
    keys = {name: observed[name][0] for name in observed}
    vals = {name: observed[name][1] for name in observed}
    q, j, k = f["query"], f["j"], f["k"]
    idx = np.arange(len(rows))
    private_val = partial_value_np(f, mats, "hybrid", "corrupt")
    shared_val = partial_value_np(f, mats, "corrupt", "hybrid")
    private_sham_val = partial_value_np(f, mats, "sham", "corrupt")
    shared_sham_val = partial_value_np(f, mats, "corrupt", "sham")
    graph: dict[str, dict[str, np.ndarray]] = {}
    for name in ("clean", "corrupt", "hybrid", "sham"):
        graph[name] = numpy_graph(q, keys[name], vals[name], vals[name], mats, cfg, regime, j)
    graph["routing_only"] = numpy_graph(q, keys["hybrid"], vals["corrupt"], vals["corrupt"], mats, cfg, regime, j)
    graph["private_only"] = numpy_graph(q, keys["corrupt"], private_val, private_val, mats, cfg, regime, j)
    graph["shared_only"] = numpy_graph(q, keys["corrupt"], shared_val, shared_val, mats, cfg, regime, j)
    graph["routing_private"] = numpy_graph(q, keys["hybrid"], private_val, private_val, mats, cfg, regime, j)
    graph["routing_shared"] = numpy_graph(q, keys["hybrid"], shared_val, shared_val, mats, cfg, regime, j)
    graph["attention_only"] = numpy_graph(q, keys["hybrid"], vals["hybrid"], vals["corrupt"], mats, cfg, regime, j)
    graph["bypass_only"] = numpy_graph(q, keys["corrupt"], vals["corrupt"], vals["hybrid"], mats, cfg, regime, j)
    state_keys, state_vals = keys["corrupt"].copy(), vals["corrupt"].copy()
    state_keys[idx, j], state_vals[idx, j] = keys["clean"][idx, j], vals["clean"][idx, j]
    graph["state_skyline"] = numpy_graph(q, state_keys, state_vals, state_vals, mats, cfg, regime, j)
    dk = keys["hybrid"][idx, j] - keys["corrupt"][idx, j]
    dv = vals["hybrid"][idx, j] - vals["corrupt"][idx, j]
    gt_delta = np.concatenate((dk, dv), axis=1)
    gt_keys, gt_vals = insert_delta_numpy(keys["corrupt"], vals["corrupt"], gt_delta, j)
    graph["ground_truth_patch"] = numpy_graph(q, gt_keys, gt_vals, gt_vals, mats, cfg, regime, j)
    cdk, cdv = [], []
    targets = f["target"]
    for i, row in enumerate(rows):
        rg = rng_for(cfg["seed"], regime, row["row_seed"], "matched_control")
        gk = rg.normal(size=dk.shape[1]).astype(np.float32)
        gv = rg.normal(size=dv.shape[1]).astype(np.float32)
        qi = q[i]
        gk -= np.dot(gk, qi) * qi / max(float(np.dot(qi, qi)), 1e-8)
        rt = mats["decoder"][:, targets[i]]
        gv -= np.dot(gv, rt) * rt / max(float(np.dot(rt, rt)), 1e-8)
        g = np.concatenate((gk, gv))
        d = np.concatenate((dk[i], dv[i]))
        g *= np.linalg.norm(d) / max(float(np.linalg.norm(g)), 1e-8)
        cdk.append(g[: dk.shape[1]])
        cdv.append(g[dk.shape[1] :])
    cdk, cdv = np.stack(cdk), np.stack(cdv)
    control_keys, control_vals = keys["corrupt"].copy(), vals["corrupt"].copy()
    control_keys[idx, j] += cdk
    control_vals[idx, j] += cdv
    graph["control"] = numpy_graph(q, control_keys, control_vals, control_vals, mats, cfg, regime, j)
    graph["routing_omitted"] = numpy_graph(q, keys["corrupt"], vals["hybrid"], vals["hybrid"], mats, cfg, regime, j)
    graph["value_omitted"] = graph["routing_only"]
    out: dict[str, np.ndarray] = {
        "query": q,
        "j": j,
        "k": k,
        "target": targets,
        "contrast_id": f["contrast_id"],
        "keys_clean": keys["clean"],
        "keys_corrupt": keys["corrupt"],
        "keys_hybrid": keys["hybrid"],
        "values_clean": vals["clean"],
        "values_corrupt": vals["corrupt"],
        "values_hybrid": vals["hybrid"],
        "values_sham": vals["sham"],
        "ground_truth_delta": gt_delta,
        "routing_delta": np.concatenate((dk, np.zeros_like(dv)), axis=1),
        "private_delta": np.concatenate((np.zeros_like(dk), private_val[idx, j] - vals["corrupt"][idx, j]), axis=1),
        "shared_delta": np.concatenate((np.zeros_like(dk), shared_val[idx, j] - vals["corrupt"][idx, j]), axis=1),
        "routing_private_delta": np.concatenate((dk, private_val[idx, j] - vals["corrupt"][idx, j]), axis=1),
        "routing_shared_delta": np.concatenate((dk, shared_val[idx, j] - vals["corrupt"][idx, j]), axis=1),
        "sham_routing_delta": np.concatenate((keys["sham"][idx, j] - keys["corrupt"][idx, j], np.zeros_like(dv)), axis=1),
        "sham_private_delta": np.concatenate((np.zeros_like(dk), private_sham_val[idx, j] - vals["corrupt"][idx, j]), axis=1),
        "sham_shared_delta": np.concatenate((np.zeros_like(dk), shared_sham_val[idx, j] - vals["corrupt"][idx, j]), axis=1),
        "sham_routing_private_delta": np.concatenate((keys["sham"][idx, j] - keys["corrupt"][idx, j], private_sham_val[idx, j] - vals["corrupt"][idx, j]), axis=1),
        "sham_routing_shared_delta": np.concatenate((keys["sham"][idx, j] - keys["corrupt"][idx, j], shared_sham_val[idx, j] - vals["corrupt"][idx, j]), axis=1),
        "sham_delta": np.concatenate((keys["sham"][idx, j] - keys["corrupt"][idx, j], vals["sham"][idx, j] - vals["corrupt"][idx, j]), axis=1),
        "control_delta": np.concatenate((cdk, cdv), axis=1),
    }
    for name, rec in graph.items():
        for field, value in rec.items():
            out[f"{field}_{name}"] = value
    out["logits_output_skyline"] = graph["clean"]["logits"].copy()
    out["control_norm_ratio"] = np.linalg.norm(out["control_delta"], axis=1) / np.maximum(np.linalg.norm(out["ground_truth_delta"], axis=1), 1e-8)
    out["hybrid_nuisance_preserved"] = np.full(len(rows), np.array_equal(f["key_nuisance_hybrid"], f["key_nuisance_corrupt"]) and np.array_equal(f["value_nuisance_hybrid"], f["value_nuisance_corrupt"]), dtype=bool)
    return out


def compare_qa(first: Mapping[str, np.ndarray], second: Mapping[str, np.ndarray], oracle: Mapping[str, np.ndarray], cfg: Mapping[str, Any]) -> dict[str, Any]:
    if set(first) != set(second) or set(first) != set(oracle):
        raise RuntimeError("QA field registry mismatch")
    repeated = {}
    oracle_fields = {}
    all_repeat = True
    all_oracle = True
    atol = cfg["qa"]["oracle_atol"]
    rel_cap = cfg["qa"]["oracle_relative_l2"]
    for name in sorted(first):
        a, b, c = first[name], second[name], oracle[name]
        same = a.dtype == b.dtype and a.shape == b.shape and np.array_equal(a, b)
        all_repeat &= bool(same)
        repeated[name] = bool(same)
        if a.dtype == bool or np.issubdtype(a.dtype, np.integer):
            ok = np.array_equal(a, c)
            max_abs = 0.0 if ok else float("inf")
            rel = 0.0 if ok else float("inf")
        else:
            diff = np.asarray(a, np.float64) - np.asarray(c, np.float64)
            max_abs = float(np.max(np.abs(diff))) if diff.size else 0.0
            rel = float(np.linalg.norm(diff) / max(np.linalg.norm(np.asarray(c, np.float64)), 1e-12))
            ok = bool(max_abs <= atol and rel <= rel_cap)
        all_oracle &= ok
        oracle_fields[name] = {"pass": ok, "max_abs": max_abs, "relative_l2": rel}
    if cfg["qa"]["repeated_live_exact"] and not all_repeat:
        raise RuntimeError("repeated live inference was not bitwise exact")
    if not all_oracle:
        bad = [k for k, v in oracle_fields.items() if not v["pass"]]
        raise RuntimeError(f"NumPy oracle mismatch: {bad[:8]}")
    return {"repeated_live_exact": all_repeat, "oracle_pass": all_oracle, "repeated_fields": repeated, "oracle_fields": oracle_fields}


def endpoint_seed(base: int, stage: str, regime: str, name: str) -> int:
    return seed32(base, stage, regime, name)


def interval(values: np.ndarray, blocks: np.ndarray, cfg: Mapping[str, Any], stage: str, regime: str, name: str) -> dict[str, Any]:
    uniq = np.arange(cfg["panels"]["blocks_per_regime"])
    block_values = [values[blocks == b] for b in uniq]
    if any(len(x) == 0 for x in block_values):
        raise RuntimeError(f"empty block in {regime}:{name}")
    point = float(np.mean([x.mean() for x in block_values]))
    rg = np.random.default_rng(endpoint_seed(cfg["seed"], stage, regime, name))
    draws = []
    for _ in range(cfg["bootstrap"]["draws"]):
        sampled = rg.choice(uniq, size=len(uniq), replace=True)
        means = []
        for b in sampled:
            x = block_values[int(b)]
            means.append(float(rg.choice(x, size=len(x), replace=True).mean()))
        draws.append(float(np.mean(means)))
    lo, hi = np.quantile(np.asarray(draws), cfg["bootstrap"]["quantiles"], method=cfg["bootstrap"]["method"])
    return {"point": point, "lower": float(lo), "upper": float(hi), "draws": len(draws), "weighting": cfg["bootstrap"]["weighting"]}


def gate_pass(name: str, rec: Mapping[str, float], gates: Mapping[str, Any]) -> bool:
    gate = gates[name]
    if "point_min" in gate:
        return bool(rec["point"] >= gate["point_min"] and rec["lower"] > gate["lower_strict_min"])
    return bool(rec["point"] <= gate["point_max"] and rec["upper"] < gate["upper_strict_max"])


def evaluate_regime(arr: Mapping[str, np.ndarray], rows: Sequence[Mapping[str, Any]], cfg: Mapping[str, Any], stage: str, regime: str) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    n = len(rows)
    if n != cfg["panels"]["blocks_per_regime"] * cfg["panels"]["rows_per_block"]:
        raise RuntimeError("regime row count")
    # All post-softmax and scientific arrays must be finite.
    for name, value in arr.items():
        if value.dtype != bool and not np.all(np.isfinite(value)):
            raise FloatingPointError(f"nonfinite {regime}:{name}")
    if not np.all(arr["hybrid_nuisance_preserved"]):
        raise RuntimeError("hybrid nuisance was not preserved")
    if not np.array_equal(arr["logits_state_skyline"], arr["logits_clean"]):
        raise RuntimeError("observed-state skyline failed donor identity")
    if not np.array_equal(arr["logits_output_skyline"], arr["logits_clean"]):
        raise RuntimeError("output skyline failed donor identity")
    if not np.allclose(arr["control_norm_ratio"], 1.0, atol=2e-6, rtol=2e-6):
        raise RuntimeError("matched control norm")
    r = regime_cfg(cfg, regime)
    if not r["hard_attention"]:
        w = arr["weights_hybrid"]
        j = arr["j"].astype(int)
        causal = w[np.arange(n), j]
        check = cfg["attention_checks"]
        noncausal = w.copy()
        noncausal[np.arange(n), j] = 0.0
        if not (
            np.all(w > 0)
            and np.all(causal >= check["causal_min"])
            and np.all(causal <= check["causal_max"])
            and np.all((noncausal > check["noncausal_weight_min"]).sum(axis=1) >= check["minimum_noncausal_above"])
        ):
            raise RuntimeError(f"soft attention construction check failed: {regime}")
    if r["bypass"]:
        att_delta = np.linalg.norm(arr["attention_transport_hybrid"] - arr["attention_transport_corrupt"], axis=1)
        bypass_delta = np.linalg.norm(arr["bypass_hybrid"] - arr["bypass_corrupt"], axis=1)
        if not (np.all(att_delta > 1e-7) and np.all(bypass_delta > 1e-7)):
            raise RuntimeError("attention/bypass independent path check")
    if r["superposition"]:
        mats = model_matrices(cfg, regime)
        m = cfg["model"]
        latent = m["private_dim"] + m["shared_dim"] + m["value_nuisance_dim"]
        if latent <= m["value_observed_dim"] or np.linalg.matrix_rank(mats["value_mix"]) != m["value_observed_dim"]:
            raise RuntimeError("superposition rank check")
        # Private identity deterministically predicts shared group; verify nonzero empirical cross-covariance.
        private = np.eye(m["private_dim"], dtype=np.float32)[: m["target_values"]]
        shared = np.eye(m["shared_dim"], dtype=np.float32)[np.arange(m["target_values"]) % m["shared_dim"]]
        cross = (private - private.mean(0)).T @ (shared - shared.mean(0)) / (m["target_values"] - 1)
        if not np.linalg.norm(cross) > 0.01:
            raise RuntimeError("shared factor correlation check")
    targets = arr["target"].astype(int)
    blocks = np.asarray([r0["block"] for r0 in rows], np.int64)
    z_hybrid = arr["logits_hybrid"]
    z_corrupt = arr["logits_corrupt"]
    mh = row_margin(z_hybrid, targets)
    mc = row_margin(z_corrupt, targets)
    d = mh - mc
    scale = np.sqrt(np.mean((centered(z_hybrid) - centered(z_corrupt)) ** 2, axis=1))
    e = cfg["eligibility"]
    top1 = np.argmax(z_hybrid, axis=1) == targets
    eligible = top1 & (mh > e["hybrid_margin_strict"]) & (mc < e["corrupt_margin_strict_upper"]) & (d > e["effect_strict"]) & (d > e["denominator_strict"]) & (scale > e["centered_scale_strict"])
    gt_norm = np.linalg.norm(arr["ground_truth_delta"], axis=1)
    eligible &= np.isfinite(gt_norm) & (gt_norm > 0)
    safe_d = np.where(d > e["denominator_strict"], d, 1.0)
    safe_scale = np.where(scale > e["centered_scale_strict"], scale, 1.0)
    def rec(name: str) -> np.ndarray:
        return (row_margin(arr[f"logits_{name}"], targets) - mc) / safe_d
    gt = rec("ground_truth_patch")
    sham = rec("sham")
    control = rec("control")
    incomplete_names = ["routing_only", "private_only", "shared_only", "routing_private", "routing_shared"]
    if r["bypass"]:
        incomplete_names.extend(("attention_only", "bypass_only"))
    incomplete = np.stack([rec(x) for x in incomplete_names], axis=1)
    metrics: dict[str, np.ndarray] = {
        "ground_truth_recovery": gt,
        "sham_specificity": gt - sham,
        "control_margin": gt - control,
        "joint_necessity": (mh - mc) / safe_d,
        "routing_necessity": (mh - row_margin(arr["logits_routing_omitted"], targets)) / safe_d,
        "value_necessity": (mh - row_margin(arr["logits_value_omitted"], targets)) / safe_d,
        "incomplete_gap": gt - np.max(incomplete, axis=1),
        "full_vocab_recovery": 1.0 - np.sqrt(np.mean((centered(arr["logits_ground_truth_patch"]) - centered(z_hybrid)) ** 2, axis=1)) / safe_scale,
    }
    collateral = []
    for i in range(n):
        mask = np.ones(z_hybrid.shape[1], bool)
        mask[targets[i]] = False
        mask[arr["contrast_id"][i]] = False
        collateral.append(float(np.sqrt(np.mean((centered(arr["logits_ground_truth_patch"])[i, mask] - centered(z_hybrid)[i, mask]) ** 2)) / safe_scale[i]))
    metrics["collateral_error"] = np.asarray(collateral)
    if any(not np.all(np.isfinite(v)) for v in metrics.values()):
        raise FloatingPointError("nonfinite bridge metric")
    total = int(eligible.sum())
    per = {str(b): int(np.sum(eligible & (blocks == b))) for b in range(cfg["panels"]["blocks_per_regime"])}
    exclusion = 1.0 - total / n
    support = bool(total >= e["minimum_total_per_regime"] and all(x >= e["minimum_per_block"] for x in per.values()) and exclusion <= e["maximum_exclusion_rate"])
    summaries = {name: interval(value[eligible], blocks[eligible], cfg, stage, regime, name) for name, value in metrics.items()} if support else {}
    decisions = {name: gate_pass(name, value, cfg["gates"]) for name, value in summaries.items()} if support else {}
    all_pass = bool(support and len(decisions) == len(cfg["gates"]) and all(decisions.values()))
    row_records = []
    for i, row in enumerate(rows):
        row_records.append(
            {
                "row_id": row["row_id"],
                "block": int(blocks[i]),
                "target": int(targets[i]),
                "eligible": bool(eligible[i]),
                "hybrid_margin": float(mh[i]),
                "corrupt_margin": float(mc[i]),
                "denominator": float(d[i]),
                "centered_scale": float(scale[i]),
                **{name: float(value[i]) for name, value in metrics.items()},
                "maximum_incomplete_recovery": float(np.max(incomplete[i])),
            }
        )
    summary = {
        "schema_version": "transformer_realistic_bridge_v1_regime_summary",
        "stage": stage,
        "regime": regime,
        "status": "PASS" if all_pass else "GATE_STOP",
        "technical_valid": True,
        "support_pass": support,
        "common_cohort_total": total,
        "common_cohort_per_block": per,
        "exclusion_rate": exclusion,
        "metrics": summaries,
        "gate_decisions": decisions,
        "all_gates_pass": all_pass,
        **SCOPE_BRIDGE,
    }
    return row_records, summary


def score_bridge_rows(rows: Sequence[Mapping[str, Any]], cfg: Mapping[str, Any], stage: str, device: torch.device) -> tuple[list[dict[str, Any]], dict[str, Any], dict[str, Any]]:
    all_rows: list[dict[str, Any]] = []
    summaries: dict[str, Any] = {}
    qa: dict[str, Any] = {}
    first_failure: str | None = None
    for regime in REGIME_ORDER:
        subset = [r for r in rows if r["regime"] == regime]
        if first_failure is not None:
            summaries[regime] = {"status": "NOT_SCORED_AFTER_FIRST_FAILURE", "prior_failure": first_failure}
            continue
        a = torch_forward(subset, cfg, regime, device)
        b = torch_forward(subset, cfg, regime, device)
        oracle = numpy_forward(subset, cfg, regime)
        qa[regime] = compare_qa(a, b, oracle, cfg)
        recs, summary = evaluate_regime(a, subset, cfg, stage, regime)
        all_rows.extend(recs)
        summaries[regime] = summary
        if not summary["all_gates_pass"]:
            first_failure = regime
    all_pass = first_failure is None
    overall = {
        "schema_version": "transformer_realistic_bridge_v1_stage_summary",
        "stage": stage,
        "status": f"{stage.upper()}_PASS" if all_pass else f"{stage.upper()}_FIRST_REGIME_STOP",
        "regimes": summaries,
        "first_failure_regime": first_failure,
        "all_gates_pass": all_pass,
        "technical_valid": True,
        **SCOPE_BRIDGE,
    }
    return all_rows, overall, qa


def ambient_context(rows: Sequence[Mapping[str, Any]], bridge_cfg: Mapping[str, Any], device: torch.device) -> dict[str, torch.Tensor]:
    return torch_forward(rows, bridge_cfg, "realistic_noisy", device, keep_tensors=True)


def apply_state_delta(ctx: Mapping[str, torch.Tensor], delta: torch.Tensor, bridge_cfg: Mapping[str, Any], device: torch.device, *, base: str = "corrupt", subtract: bool = False, site: str = "causal", path_mode: str = "both") -> dict[str, torch.Tensor]:
    mats = model_matrices(bridge_cfg, "realistic_noisy")
    base_keys, base_vals = ctx[f"keys_{base}"], ctx[f"values_{base}"]
    j, k = ctx["j"], ctx["k"]
    which = j if site == "causal" else k
    patched_keys, patched_vals = insert_delta_torch(base_keys, base_vals, delta, which, -1.0 if subtract else 1.0)
    if path_mode == "both":
        att_keys, att_vals, bypass_vals = patched_keys, patched_vals, patched_vals
    elif path_mode == "attention_only":
        att_keys, att_vals, bypass_vals = patched_keys, patched_vals, base_vals
    elif path_mode == "bypass_only":
        att_keys, att_vals, bypass_vals = base_keys, base_vals, patched_vals
    else:
        raise RuntimeError(f"unknown path mode {path_mode}")
    return torch_graph(ctx["query"], att_keys, att_vals, bypass_vals, mats, bridge_cfg, "realistic_noisy", j)


def matched_norm(delta: torch.Tensor, reference: torch.Tensor) -> tuple[torch.Tensor, torch.Tensor]:
    norm = torch.linalg.vector_norm(delta, dim=1, keepdim=True)
    ref = torch.linalg.vector_norm(reference, dim=1, keepdim=True)
    valid = torch.isfinite(norm[:, 0]) & (norm[:, 0] > 1e-10) & torch.isfinite(ref[:, 0]) & (ref[:, 0] > 0)
    scale = torch.where(valid[:, None], ref / torch.clamp(norm, min=1e-10), torch.zeros_like(norm))
    return delta * scale, valid


def matched_method_control(delta: torch.Tensor, ctx: Mapping[str, torch.Tensor], bridge_cfg: Mapping[str, Any], rows: Sequence[Mapping[str, Any]], method_name: str) -> torch.Tensor:
    mats = model_matrices(bridge_cfg, "realistic_noisy")
    decoder = torch.as_tensor(mats["decoder"], dtype=torch.float32, device=delta.device)
    key_dim = ctx["keys_corrupt"].shape[-1]
    outputs = []
    for i, row in enumerate(rows):
        rg = rng_for(bridge_cfg["seed"], row["row_seed"], method_name, "method_control")
        gk = torch.as_tensor(rg.normal(size=key_dim).astype(np.float32), device=delta.device)
        gv = torch.as_tensor(rg.normal(size=delta.shape[1] - key_dim).astype(np.float32), device=delta.device)
        qi = ctx["query"][i]
        gk -= torch.dot(gk, qi) * qi / torch.clamp(torch.dot(qi, qi), min=1e-8)
        rt = decoder[:, ctx["target"][i]]
        gv -= torch.dot(gv, rt) * rt / torch.clamp(torch.dot(rt, rt), min=1e-8)
        g = torch.cat((gk, gv))
        g *= torch.linalg.vector_norm(delta[i]) / torch.clamp(torch.linalg.vector_norm(g), min=1e-10)
        outputs.append(g)
    return torch.stack(outputs)


class TopKSAE(torch.nn.Module):
    def __init__(self, d: int, width: int, topk: int, seed: int, device: torch.device):
        super().__init__()
        gen = torch.Generator(device=device).manual_seed(seed)
        self.encoder = torch.nn.Parameter(torch.randn(d, width, generator=gen, device=device) / math.sqrt(d))
        self.decoder = torch.nn.Parameter(torch.randn(width, d, generator=gen, device=device) / math.sqrt(width))
        self.bias = torch.nn.Parameter(torch.zeros(d, device=device))
        self.topk = topk

    def encode(self, x: torch.Tensor) -> torch.Tensor:
        z = F.relu((x - self.bias) @ self.encoder)
        values, indices = torch.topk(z, self.topk, dim=1)
        sparse = torch.zeros_like(z)
        return sparse.scatter(1, indices, values)

    def decode(self, z: torch.Tensor) -> torch.Tensor:
        return z @ self.decoder + self.bias

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.decode(self.encode(x))


@dataclass
class MethodModel:
    name: str
    family: str
    kind: str
    payload: Any
    seed: int | None = None


def base_method_models() -> list[MethodModel]:
    """Prospectively registered exact and deliberately incomplete circuit controls."""
    return [
        MethodModel("ground_truth", "ground_truth", "ground_truth", None),
        MethodModel("incomplete_routing_only", "incomplete_routing_only", "incomplete_delta", "routing_delta"),
        MethodModel("incomplete_private_only", "incomplete_private_only", "incomplete_delta", "private_delta"),
        MethodModel("incomplete_shared_only", "incomplete_shared_only", "incomplete_delta", "shared_delta"),
        MethodModel("incomplete_routing_private", "incomplete_routing_private", "incomplete_delta", "routing_private_delta"),
        MethodModel("incomplete_routing_shared", "incomplete_routing_shared", "incomplete_delta", "routing_shared_delta"),
        MethodModel("incomplete_attention_only", "incomplete_attention_only", "path_ground_truth", "attention_only"),
        MethodModel("incomplete_bypass_only", "incomplete_bypass_only", "path_ground_truth", "bypass_only"),
    ]


def train_sae(x: torch.Tensor, cfg: Mapping[str, Any], seed: int, out: Path) -> tuple[TopKSAE, dict[str, Any]]:
    d = x.shape[1]
    sc = cfg["methods"]["sae"]
    torch.manual_seed(seed)
    model = TopKSAE(d, d * sc["width_multiplier"], sc["topk"], seed, x.device)
    opt = torch.optim.Adam(model.parameters(), lr=sc["learning_rate"])
    gen = torch.Generator(device=x.device).manual_seed(seed + 99)
    losses = []
    for step in range(sc["steps"]):
        idx = torch.randint(0, x.shape[0], (sc["batch_size"],), generator=gen, device=x.device)
        pred = model(x[idx])
        loss = F.mse_loss(pred, x[idx])
        if not torch.isfinite(loss):
            raise FloatingPointError(f"SAE nonfinite seed {seed}")
        opt.zero_grad(set_to_none=True)
        loss.backward()
        opt.step()
        if step in {0, sc["steps"] - 1}:
            losses.append(float(loss.detach().cpu()))
    torch.save({"state_dict": model.state_dict(), "seed": seed, "config": sc}, out)
    return model, {"initial_loss": losses[0], "final_loss": losses[-1], "steps": sc["steps"], "seed": seed}


class SupervisedLowRank(torch.nn.Module):
    def __init__(self, d: int, rank: int, seed: int, device: torch.device):
        super().__init__()
        gen = torch.Generator(device=device).manual_seed(seed)
        self.u = torch.nn.Parameter(torch.randn(d, rank, generator=gen, device=device) * 0.02)
        self.v = torch.nn.Parameter(torch.randn(rank, d, generator=gen, device=device) * 0.02)

    def forward(self, delta: torch.Tensor) -> torch.Tensor:
        return delta @ self.u @ self.v


def _slice_ctx(ctx: Mapping[str, torch.Tensor], ix: torch.Tensor) -> dict[str, torch.Tensor]:
    n = ctx["j"].shape[0]
    return {k: (v[ix] if isinstance(v, torch.Tensor) and v.ndim > 0 and v.shape[0] == n else v) for k, v in ctx.items()}


def torch_margin(logits: torch.Tensor, targets: torch.Tensor) -> torch.Tensor:
    v = logits.shape[1]
    return (v * logits[torch.arange(logits.shape[0], device=logits.device), targets] - logits.sum(dim=1)) / (v - 1)


def train_supervised(ctx: Mapping[str, torch.Tensor], bridge_cfg: Mapping[str, Any], methods_cfg: Mapping[str, Any], seed: int, out: Path, device: torch.device) -> tuple[SupervisedLowRank, dict[str, Any]]:
    sc = methods_cfg["methods"]["supervised"]
    d = ctx["ground_truth_delta"].shape[1]
    model = SupervisedLowRank(d, sc["rank"], seed, device)
    opt = torch.optim.Adam(model.parameters(), lr=sc["learning_rate"])
    gen = torch.Generator(device=device).manual_seed(seed + 71)
    losses = []
    for step in range(sc["steps"]):
        ix = torch.randint(0, ctx["j"].shape[0], (sc["batch_size"],), generator=gen, device=device)
        c = _slice_ctx(ctx, ix)
        clean_delta = model(c["ground_truth_delta"])
        sham_delta = model(c["sham_delta"])
        patch = apply_state_delta(c, clean_delta, bridge_cfg, device)["logits"]
        sham = apply_state_delta(c, sham_delta, bridge_cfg, device)["logits"]
        hybrid = c["logits_hybrid"]
        corrupt = c["logits_corrupt"]
        denom = torch_margin(hybrid, c["target"]) - torch_margin(corrupt, c["target"])
        recovery = (torch_margin(patch, c["target"]) - torch_margin(corrupt, c["target"])) / torch.clamp(denom, min=1e-6)
        sham_rec = (torch_margin(sham, c["target"]) - torch_margin(corrupt, c["target"])) / torch.clamp(denom, min=1e-6)
        coll = torch.mean((patch - hybrid) ** 2)
        loss = -recovery.mean() + sc["collateral_weight"] * coll + sc["sham_weight"] * (sham_rec**2).mean() + sc["norm_weight"] * (clean_delta**2).mean()
        if not torch.isfinite(loss):
            raise FloatingPointError(f"supervised nonfinite seed {seed}")
        opt.zero_grad(set_to_none=True)
        loss.backward()
        opt.step()
        if step in {0, sc["steps"] - 1}:
            losses.append(float(loss.detach().cpu()))
    torch.save({"state_dict": model.state_dict(), "seed": seed, "config": sc}, out)
    return model, {"initial_loss": losses[0], "final_loss": losses[-1], "steps": sc["steps"], "seed": seed}


def fit_methods(rows: Sequence[Mapping[str, Any]], bridge_cfg: Mapping[str, Any], methods_cfg: Mapping[str, Any], device: torch.device, checkpoint_root: Path) -> tuple[list[MethodModel], dict[str, Any]]:
    checkpoint_root.mkdir(parents=True, exist_ok=False)
    ctx = ambient_context(rows, bridge_cfg, device)
    targets = ctx["target"].detach().cpu().numpy()
    blocks = np.asarray([r["block"] for r in rows])
    for target in range(methods_cfg["panels"]["target_values"]):
        mask = targets == target
        if int(mask.sum()) < methods_cfg["panels"]["minimum_train_rows_per_target"] or len(set(blocks[mask].tolist())) < methods_cfg["panels"]["minimum_train_blocks_per_target"]:
            raise RuntimeError(f"insufficient train support for target {target}")
    delta = ctx["ground_truth_delta"].detach()
    d = delta.shape[1]
    rank = methods_cfg["methods"]["rank"]
    models: list[MethodModel] = base_method_models()
    # Random orthogonal projector.
    rg = np.random.default_rng(methods_cfg["methods"]["random_seed"])
    q, _ = np.linalg.qr(rg.normal(size=(d, rank)))
    random_p = torch.as_tensor((q @ q.T).astype(np.float32), device=device)
    models.append(MethodModel("random_rank8", "random", "matrix", random_p))
    # PCA projector on paired deltas.
    dc = delta - delta.mean(dim=0, keepdim=True)
    _, _, vh = torch.linalg.svd(dc, full_matrices=False)
    pca_p = vh[:rank].T @ vh[:rank]
    models.append(MethodModel("pca_rank8", "pca", "matrix", pca_p))
    # Target-specific difference means.
    mu = torch.stack([delta[ctx["target"] == target].mean(dim=0) for target in range(methods_cfg["panels"]["target_values"])])
    models.append(MethodModel("diffmean", "diffmean", "diffmean", mu))
    # LEACE-style removed concept component.
    x = delta - delta.mean(dim=0, keepdim=True)
    z = F.one_hot(ctx["target"], num_classes=methods_cfg["panels"]["target_values"]).to(torch.float32)
    z = z - z.mean(dim=0, keepdim=True)
    c = (x.T @ x) / (x.shape[0] - 1) + methods_cfg["methods"]["leace_ridge"] * torch.eye(d, device=device)
    evals, evecs = torch.linalg.eigh(c)
    csqrt = evecs @ torch.diag(torch.sqrt(torch.clamp(evals, min=1e-8))) @ evecs.T
    cinv = evecs @ torch.diag(torch.rsqrt(torch.clamp(evals, min=1e-8))) @ evecs.T
    cross = (x.T @ z) / (x.shape[0] - 1)
    ql, _ = torch.linalg.qr(cinv @ cross, mode="reduced")
    removed = csqrt @ ql @ ql.T @ cinv
    models.append(MethodModel("leace_style", "leace_style", "matrix", removed))
    fit = {"nonlearned": [m.name for m in models], "learned": {}}
    # SAE representation fit; selected feature indices are train-only.
    idx = torch.arange(len(rows), device=device)
    state_clean = torch.cat((ctx["keys_clean"][idx, ctx["j"]], ctx["values_clean"][idx, ctx["j"]]), dim=1)
    state_corrupt = torch.cat((ctx["keys_corrupt"][idx, ctx["j"]], ctx["values_corrupt"][idx, ctx["j"]]), dim=1)
    state_sham = state_corrupt + ctx["sham_delta"]
    train_states = torch.cat((state_clean, state_corrupt, state_sham), dim=0)
    for seed in methods_cfg["methods"]["sae"]["seeds"]:
        sae, rec = train_sae(train_states, methods_cfg, seed, checkpoint_root / f"sae_seed{seed}.pt")
        with torch.no_grad():
            change = torch.mean(torch.abs(sae.encode(state_clean) - sae.encode(state_corrupt)), dim=0)
            selected = torch.topk(change, methods_cfg["methods"]["sae"]["topk"]).indices
        payload = {"model": sae, "selected": selected}
        name = f"sae_seed{seed}"
        models.append(MethodModel(name, "sae", "sae", payload, seed))
        fit["learned"][name] = {**rec, "selected_features": selected.detach().cpu().tolist()}
    for seed in methods_cfg["methods"]["supervised"]["seeds"]:
        sup, rec = train_supervised(ctx, bridge_cfg, methods_cfg, seed, checkpoint_root / f"supervised_seed{seed}.pt", device)
        name = f"supervised_seed{seed}"
        models.append(MethodModel(name, "supervised", "supervised", sup, seed))
        fit["learned"][name] = rec
    fit["checkpoint_inventory"] = [
        {"path": p.name, "bytes": p.stat().st_size, "sha256": sha(p)}
        for p in sorted(checkpoint_root.glob("*.pt"))
    ]
    atomic_json(checkpoint_root / "FIT_SUMMARY.json", fit)
    return models, fit


def predict_method(model: MethodModel, ctx: Mapping[str, torch.Tensor]) -> tuple[torch.Tensor, torch.Tensor]:
    clean = ctx["ground_truth_delta"]
    sham = ctx["sham_delta"]
    if model.kind == "ground_truth":
        return clean, sham
    if model.kind == "incomplete_delta":
        return ctx[model.payload], ctx["sham_" + model.payload]
    if model.kind == "path_ground_truth":
        return clean, sham
    if model.kind == "matrix":
        return clean @ model.payload.T, sham @ model.payload.T
    if model.kind == "diffmean":
        pred = model.payload[ctx["target"]]
        return pred, pred.clone()
    if model.kind == "sae":
        sae, selected = model.payload["model"], model.payload["selected"]
        key_dim = ctx["keys_corrupt"].shape[-1]
        idx = torch.arange(ctx["j"].shape[0], device=clean.device)
        corrupt_state = torch.cat((ctx["keys_corrupt"][idx, ctx["j"]], ctx["values_corrupt"][idx, ctx["j"]]), dim=1)
        clean_state = corrupt_state + clean
        sham_state = corrupt_state + sham
        zc = sae.encode(corrupt_state)
        zclean = zc.clone(); zclean[:, selected] = sae.encode(clean_state)[:, selected]
        zsham = zc.clone(); zsham[:, selected] = sae.encode(sham_state)[:, selected]
        base = sae.decode(zc)
        return sae.decode(zclean) - base, sae.decode(zsham) - base
    if model.kind == "supervised":
        return model.payload(clean), model.payload(sham)
    raise RuntimeError(f"unknown method kind: {model.kind}")


def method_interval(values: np.ndarray, blocks: np.ndarray, cfg: Mapping[str, Any], stage: str, method: str, estimand: str, name: str) -> dict[str, Any]:
    block_count = cfg["panels"][stage]["blocks"]
    uniq = np.arange(block_count)
    block_values = [values[blocks == b] for b in uniq]
    if any(len(x) == 0 for x in block_values):
        raise RuntimeError("empty method block")
    point = float(np.mean([x.mean() for x in block_values]))
    rg = np.random.default_rng(seed32(cfg["seed"], stage, method, estimand, name))
    draws = []
    for _ in range(cfg["bootstrap"]["draws"]):
        sample = rg.choice(uniq, size=len(uniq), replace=True)
        means = []
        for b in sample:
            x = block_values[int(b)]
            means.append(float(rg.choice(x, size=len(x), replace=True).mean()))
        draws.append(float(np.mean(means)))
    lo, hi = np.quantile(np.asarray(draws), cfg["bootstrap"]["quantiles"], method=cfg["bootstrap"]["method"])
    return {"point": point, "lower": float(lo), "upper": float(hi), "draws": len(draws), "weighting": cfg["bootstrap"]["weighting"]}


def score_method_estimand(
    method_name: str,
    clean_delta: torch.Tensor,
    sham_delta: torch.Tensor,
    ctx: Mapping[str, torch.Tensor],
    rows: Sequence[Mapping[str, Any]],
    bridge_cfg: Mapping[str, Any],
    methods_cfg: Mapping[str, Any],
    stage: str,
    estimand: str,
    device: torch.device,
    matched_complete: bool,
    path_mode: str = "both",
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    control_delta = matched_method_control(clean_delta, ctx, bridge_cfg, rows, method_name + ":" + estimand)
    patch = apply_state_delta(ctx, clean_delta, bridge_cfg, device, path_mode=path_mode)["logits"]
    sham = apply_state_delta(ctx, sham_delta, bridge_cfg, device, path_mode=path_mode)["logits"]
    # Same-site, same-path, norm-matched orthogonal control.
    control = apply_state_delta(ctx, control_delta, bridge_cfg, device, path_mode=path_mode)["logits"]
    ablated = apply_state_delta(ctx, clean_delta, bridge_cfg, device, base="hybrid", subtract=True, path_mode=path_mode)["logits"]
    arrays = {"patch": patch, "sham": sham, "control": control, "ablated": ablated}
    if any(not bool(torch.all(torch.isfinite(v))) for v in arrays.values()):
        raise FloatingPointError(f"nonfinite method output {method_name}:{estimand}")
    target = ctx["target"].detach().cpu().numpy().astype(int)
    contrast = ctx["contrast_id"].detach().cpu().numpy().astype(int)
    z_h = ctx["logits_hybrid"].detach().cpu().numpy()
    z_c = ctx["logits_corrupt"].detach().cpu().numpy()
    out = {k: v.detach().cpu().numpy() for k, v in arrays.items()}
    mh, mc = row_margin(z_h, target), row_margin(z_c, target)
    d = mh - mc
    scale = np.sqrt(np.mean((centered(z_h) - centered(z_c)) ** 2, axis=1))
    e = bridge_cfg["eligibility"]
    eligible = (np.argmax(z_h, axis=1) == target) & (mh > e["hybrid_margin_strict"]) & (mc < e["corrupt_margin_strict_upper"]) & (d > e["effect_strict"]) & (d > e["denominator_strict"]) & (scale > e["centered_scale_strict"])
    safe_d = np.where(d > e["denominator_strict"], d, 1.0)
    safe_scale = np.where(scale > e["centered_scale_strict"], scale, 1.0)
    recovery = (row_margin(out["patch"], target) - mc) / safe_d
    sham_recovery = (row_margin(out["sham"], target) - mc) / safe_d
    control_recovery = (row_margin(out["control"], target) - mc) / safe_d
    necessity = (mh - row_margin(out["ablated"], target)) / safe_d
    fv = 1.0 - np.sqrt(np.mean((centered(out["patch"]) - centered(z_h)) ** 2, axis=1)) / safe_scale
    coll = []
    for i in range(len(rows)):
        mask = np.ones(z_h.shape[1], bool); mask[target[i]] = False; mask[contrast[i]] = False
        coll.append(float(np.sqrt(np.mean((centered(out["patch"])[i, mask] - centered(z_h)[i, mask]) ** 2)) / safe_scale[i]))
    metrics = {
        "recovery": recovery,
        "sham_specificity": recovery - sham_recovery,
        "control_margin": recovery - control_recovery,
        "collateral_error": np.asarray(coll),
        "necessity": necessity,
        "full_vocab_recovery": fv,
    }
    if any(not np.all(np.isfinite(v)) for v in metrics.values()):
        raise FloatingPointError(f"nonfinite method metric {method_name}:{estimand}")
    blocks = np.asarray([r["block"] for r in rows], np.int64)
    total = int(eligible.sum())
    per = {str(b): int(np.sum(eligible & (blocks == b))) for b in range(methods_cfg["panels"][stage]["blocks"])}
    target_support = {
        str(target_value): {
            "eligible_rows": int(np.sum(eligible & (target == target_value))),
            "eligible_blocks": int(len(set(blocks[eligible & (target == target_value)].tolist()))),
        }
        for target_value in range(methods_cfg["panels"]["target_values"])
    }
    target_support_pass = all(
        rec["eligible_rows"] >= methods_cfg["panels"]["minimum_eval_rows_per_target"]
        and rec["eligible_blocks"] >= methods_cfg["panels"]["minimum_eval_blocks_per_target"]
        for rec in target_support.values()
    )
    exclusion = 1 - total / len(rows)
    support = bool(total >= methods_cfg["panels"]["minimum_eval_total"] and all(x >= methods_cfg["panels"]["minimum_eval_per_block"] for x in per.values()) and target_support_pass and exclusion <= methods_cfg["panels"]["maximum_exclusion_rate"])
    summaries = {name: method_interval(value[eligible], blocks[eligible], methods_cfg, stage, method_name, estimand, name) for name, value in metrics.items()} if support else {}
    gate_names = methods_cfg["gates"]
    decisions = {name: gate_pass(name, summaries[name], gate_names) for name in gate_names} if support and all(name in summaries for name in gate_names) else {}
    all_pass = bool(estimand == "matched" and matched_complete and support and len(decisions) == len(gate_names) and all(decisions.values()))
    records = []
    for i, row in enumerate(rows):
        records.append({"row_id": row["row_id"], "block": int(blocks[i]), "target": int(target[i]), "eligible": bool(eligible[i]), **{name: float(value[i]) for name, value in metrics.items()}})
    summary = {
        "schema_version": "transformer_realistic_methods_v1_method_summary",
        "method": method_name,
        "stage": stage,
        "estimand": estimand,
        "matched_complete": matched_complete,
        "support_pass": support,
        "common_cohort_total": total,
        "common_cohort_per_block": per,
        "target_support": target_support,
        "target_support_pass": target_support_pass,
        "exclusion_rate": exclusion,
        "metrics": summaries,
        "gate_decisions": decisions,
        "all_gates_pass": all_pass,
        **SCOPE_METHODS,
        "representation_methods_evaluated": True,
    }
    return records, summary


def score_methods(rows: Sequence[Mapping[str, Any]], models: Sequence[MethodModel], bridge_cfg: Mapping[str, Any], methods_cfg: Mapping[str, Any], stage: str, device: torch.device) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    ctx = ambient_context(rows, bridge_cfg, device)
    records: list[dict[str, Any]] = []
    summaries: dict[str, Any] = {}
    for model in models:
        try:
            with torch.no_grad():
                native_clean, native_sham = predict_method(model, ctx)
                if not torch.all(torch.isfinite(native_clean)) or not torch.all(torch.isfinite(native_sham)):
                    raise FloatingPointError("nonfinite native delta")
                matched_clean, valid_clean = matched_norm(native_clean, ctx["ground_truth_delta"])
                matched_sham, valid_sham = matched_norm(native_sham, ctx["ground_truth_delta"])
                complete = bool(torch.all(valid_clean & valid_sham))
                path_mode = str(model.payload) if model.kind == "path_ground_truth" else "both"
                native_rows, native_summary = score_method_estimand(model.name, native_clean, native_sham, ctx, rows, bridge_cfg, methods_cfg, stage, "native", device, complete, path_mode)
                matched_rows, matched_summary = score_method_estimand(model.name, matched_clean, matched_sham, ctx, rows, bridge_cfg, methods_cfg, stage, "matched", device, complete, path_mode)
            records.extend([{**r, "method": model.name, "estimand": "native"} for r in native_rows])
            records.extend([{**r, "method": model.name, "estimand": "matched"} for r in matched_rows])
            summaries[model.name] = {"family": model.family, "seed": model.seed, "native": native_summary, "matched": matched_summary, "technical_valid": True}
        except Exception as exc:
            summaries[model.name] = {"family": model.family, "seed": model.seed, "technical_valid": False, "status": "METHOD_TECHNICAL_FAILURE", "reason": f"{type(exc).__name__}: {exc}", "matched": {"all_gates_pass": False}}
    family_pass: dict[str, bool] = {}
    families = sorted(set(m.family for m in models))
    for family in families:
        names = [m.name for m in models if m.family == family]
        family_pass[family] = bool(names and all(summaries[name].get("technical_valid") and summaries[name]["matched"]["all_gates_pass"] for name in names))
    learned_seed_means: dict[str, Any] = {}
    for family in ("sae", "supervised"):
        names = [m.name for m in models if m.family == family]
        if names and all(summaries[name].get("technical_valid") for name in names):
            learned_seed_means[family] = {}
            for estimand in ("native", "matched"):
                learned_seed_means[family][estimand] = {}
                metric_names = summaries[names[0]][estimand].get("metrics", {})
                for metric in metric_names:
                    learned_seed_means[family][estimand][metric] = {
                        field: float(np.mean([summaries[name][estimand]["metrics"][metric][field] for name in names]))
                        for field in ("point", "lower", "upper")
                    }
    overall = {
        "schema_version": "transformer_realistic_methods_v1_stage_summary",
        "stage": stage,
        "status": f"{stage.upper()}_COMPLETE",
        "methods": summaries,
        "family_pass_every_seed": family_pass,
        "learned_seed_descriptive_means": learned_seed_means,
        "technical_valid": all(x.get("technical_valid") for x in summaries.values()),
        **SCOPE_METHODS,
        "representation_methods_evaluated": True,
    }
    return records, overall


def paper_verify() -> dict[str, Any]:
    # Inline verifier avoids assumptions about how the NFS workspace path was reached.
    import re
    ledger = loadj(ROOT / "reports/paper_claim_ledger_v1.json")
    paper = (ROOT / "PAPER.md").read_text()
    ids = [c["id"] for c in ledger["claims"]]
    if len(ids) != len(set(ids)):
        raise RuntimeError("duplicate paper claims")
    bindings = 0
    for claim in ledger["claims"]:
        if f"[{claim['id']}]" not in paper:
            raise RuntimeError(f"paper claim missing {claim['id']}")
        for selector in claim.get("paper_selectors", []):
            if paper.count(selector) != 1:
                raise RuntimeError(f"paper selector drift {claim['id']}")
        for ev in claim["evidence"]:
            p = ROOT / ev["path"]
            if not p.is_file() or sha(p) != ev["sha256"]:
                raise RuntimeError(f"paper evidence drift {claim['id']}")
            if "pointer" in ev:
                value: Any = loadj(p)
                for part in ev["pointer"].lstrip("/").split("/") if ev["pointer"] else []:
                    part = part.replace("~1", "/").replace("~0", "~")
                    value = value[int(part)] if isinstance(value, list) else value[part]
                if value != ev["expected"]:
                    raise RuntimeError(f"paper pointer drift {claim['id']}")
            if "selector" in ev and p.read_text().count(ev["selector"]) != 1:
                raise RuntimeError(f"paper evidence selector drift {claim['id']}")
            bindings += 1
    known = set(ids)
    if any(x not in known for x in re.findall(r"\[(C\d{3})\]", paper)):
        raise RuntimeError("unknown paper claim marker")
    return {"status": "PASS", "claims": len(ids), "evidence_bindings": bindings}


def run_preservation_verify() -> dict[str, Any]:
    manifest = ROOT / "reports/provenance/constructed_copy_circuit_v1_1_postresult/PRESERVATION.json"
    p = loadj(manifest)
    for item in p["inventory"]:
        path = ROOT / item["path"]
        if not path.is_file() or path.stat().st_size != item["bytes"] or sha(path) != item["sha256"]:
            raise RuntimeError(f"v1.1 preservation drift {item['path']}")
    return {"status": "PASS", "manifest_sha256": sha(manifest)}


def candidate_paths(kind: str) -> list[Path]:
    common = [
        PLAN,
        ROOT / "PAPER.md",
        ROOT / "reports/paper_claim_ledger_v1.json",
        ROOT / "scripts/preserve_constructed_copy_circuit_v1_1.py",
        ROOT / "reports/provenance/constructed_copy_circuit_v1_1_postresult/PRESERVATION.json",
        ROOT / "reports/provenance/constructed_copy_circuit_v1_1_postresult/PRESERVATION_FIELD_CLARIFICATION.json",
        ROOT / "reports/claim_review/constructed_copy_circuit_v1_1_post_result_claim_review.md",
        ROOT / "reports/adversarial/transformer_realistic_bridge_v1_r2_plan_review.md",
        RECOVERY_VERIFIER,
        RECOVERY_AUTH,
        RECOVERY_PARITY,
        RECOVERY_BINDING_SUPPLEMENT,
        RECOVERY_SUPERSEDED_INDEX,
        ROOT / "reports/provenance/transformer_realistic_bridge_v1_run_20260810/PRELAUNCH_TERMINAL.json",
        ROOT / "reports/provenance/transformer_realistic_methods_v1_run_20260810/PRELAUNCH_TERMINAL.json",
        ROOT / "scripts/transformer_realistic_bridge_v1_r2.py",
        ROOT / "scripts/launch_transformer_realistic_bridge_v1_r2_tmux.sh",
        ROOT / "tests/test_transformer_realistic_bridge_v1_r2.py",
    ]
    if kind == "bridge":
        common.append(BRIDGE_CONFIG)
    elif kind == "methods":
        common.extend((BRIDGE_CONFIG, METHODS_CONFIG))
    else:
        raise ValueError(kind)
    missing = [str(p) for p in common if not p.is_file()]
    if missing:
        raise RuntimeError(f"candidate artifacts missing: {missing}")
    return sorted(set(common), key=lambda p: p.relative_to(ROOT).as_posix())


def inventory(paths: Iterable[Path]) -> list[dict[str, Any]]:
    return [{"path": p.relative_to(ROOT).as_posix(), "bytes": p.stat().st_size, "sha256": sha(p)} for p in paths]


def generator_lock_path(kind: str) -> Path:
    cfg = config(BRIDGE_CONFIG if kind == "bridge" else METHODS_CONFIG)
    return ROOT / cfg["runtime"]["generator_lock"]


def freeze_path(kind: str) -> Path:
    cfg = config(BRIDGE_CONFIG if kind == "bridge" else METHODS_CONFIG)
    return ROOT / cfg["runtime"]["freeze"]


def candidate_preflight() -> None:
    bcfg, mcfg = config(BRIDGE_CONFIG), config(METHODS_CONFIG)
    run_preservation_verify()
    paper_verify()
    subprocess.check_call([sys.executable, str(RECOVERY_VERIFIER), "check-prelock"], env={**os.environ, "MSAE_ROOT": str(ROOT)})
    parity = loadj(RECOVERY_PARITY)
    if parity.get("status") != "PASS" or parity.get("payloads_accessed") is not False or parity.get("new_source_sha256") != sha(ROOT / "scripts/transformer_realistic_bridge_v1_r2.py"):
        raise RuntimeError("r2 recovery parity is absent or stale")
    if tuple(r["name"] for r in bcfg["regimes"]) != REGIME_ORDER:
        raise RuntimeError("regime order drift")
    if bcfg["model"]["private_dim"] + bcfg["model"]["shared_dim"] + bcfg["model"]["value_nuisance_dim"] <= bcfg["model"]["value_observed_dim"]:
        raise RuntimeError("overcomplete factor contract")
    if mcfg["panels"]["target_values"] != bcfg["model"]["target_values"]:
        raise RuntimeError("target registry drift")
    for cfg in (bcfg, mcfg):
        out = ROOT / cfg["runtime"]["output_root"]
        prov = ROOT / cfg["runtime"]["provenance_root"]
        if out.exists() or prov.exists():
            raise RuntimeError(f"result/provenance namespace exists: {cfg['namespace']}")
    print(json.dumps({"status": "PASS", "paper": paper_verify(), "preservation": run_preservation_verify()}, sort_keys=True))


def smoke(device_name: str) -> None:
    bcfg = config(BRIDGE_CONFIG)
    device = torch.device(device_name)
    rows = make_rows("nonpanel_smoke", 999001, REGIME_ORDER, bcfg["panels"]["blocks_per_regime"], bcfg["panels"]["rows_per_block"], bcfg["panels"]["target_values"])
    row_records, summary, qa = score_bridge_rows(rows, bcfg, "nonpanel_smoke", device)
    if not summary["all_gates_pass"]:
        raise RuntimeError(f"nonpanel bridge smoke failed: {summary['first_failure_regime']}")
    root = ROOT / bcfg["runtime"]["candidate_root"]
    name = "SMOKE_GPU.json" if device.type == "cuda" else "SMOKE_CPU.json"
    target = root / name
    if target.exists():
        old = loadj(target)
        if old.get("summary") != summary:
            raise RuntimeError("smoke result drift")
        print(json.dumps({"status": "PASS", "existing": True, "path": target.relative_to(ROOT).as_posix()}))
        return
    atomic_json(target, {"schema_version": "transformer_realistic_bridge_v1_smoke", "device": str(device), "summary": summary, "qa": qa, "rows_scored": len(row_records), "torch": torch.__version__, "numpy": np.__version__})
    print(json.dumps({"status": "PASS", "path": target.relative_to(ROOT).as_posix()}))


def calibrate() -> None:
    bcfg = config(BRIDGE_CONFIG)
    rows = make_rows("nonpanel_calibration", 999002, REGIME_ORDER, bcfg["panels"]["blocks_per_regime"], bcfg["panels"]["rows_per_block"], bcfg["panels"]["target_values"])
    outcomes = {}
    for regime in REGIME_ORDER:
        subset = [r for r in rows if r["regime"] == regime]
        arr = torch_forward(subset, bcfg, regime, torch.device("cpu"))
        _, good = evaluate_regime(arr, subset, bcfg, "nonpanel_calibration", regime)
        if not good["all_gates_pass"]:
            raise RuntimeError(f"passing calibration failed {regime}")
        mutated = {k: v.copy() for k, v in arr.items()}
        mutated["logits_routing_omitted"] = mutated["logits_hybrid"].copy()
        _, route_bad = evaluate_regime(mutated, subset, bcfg, "nonpanel_route_mutation", regime)
        if route_bad["gate_decisions"].get("routing_necessity", True):
            raise RuntimeError("routing mutation was not rejected")
        mutated2 = {k: v.copy() for k, v in arr.items()}
        mutated2["logits_routing_private"] = mutated2["logits_hybrid"].copy()
        _, gap_bad = evaluate_regime(mutated2, subset, bcfg, "nonpanel_gap_mutation", regime)
        if gap_bad["gate_decisions"].get("incomplete_gap", True):
            raise RuntimeError("incomplete mutation was not rejected")
        outcomes[regime] = {"passing": True, "routing_mutation_rejected": True, "incomplete_mutation_rejected": True}
    target = ROOT / bcfg["runtime"]["candidate_root"] / "CALIBRATION.json"
    if target.exists():
        if loadj(target).get("outcomes") != outcomes:
            raise RuntimeError("calibration drift")
    else:
        atomic_json(target, {"schema_version": "transformer_realistic_bridge_v1_calibration", "outcomes": outcomes, "scientific_panels_read": False})
    print(json.dumps({"status": "PASS", "regimes": len(outcomes)}))


def methods_smoke(device_name: str) -> None:
    """Exercise every registered method on nonpanel fixtures with two-step learned fits."""
    bcfg = config(BRIDGE_CONFIG)
    mcfg = copy.deepcopy(config(METHODS_CONFIG))
    mcfg["bootstrap"]["draws"] = 20
    mcfg["methods"]["sae"]["steps"] = 2
    mcfg["methods"]["supervised"]["steps"] = 2
    device = torch.device(device_name)
    root = ROOT / mcfg["runtime"]["candidate_root"]
    checkpoint_root = root / "methods_smoke_checkpoints"
    target = root / "METHODS_SMOKE_GPU.json"
    if target.exists():
        print(json.dumps({"status": "PASS", "existing": True, "path": target.relative_to(ROOT).as_posix()}))
        return
    train_cfg = mcfg["panels"]["train"]
    train_rows = make_rows("nonpanel_methods_smoke_train", 999003, ("realistic_noisy",), train_cfg["blocks"], train_cfg["rows_per_block"], mcfg["panels"]["target_values"])
    models, fit = fit_methods(train_rows, bcfg, mcfg, device, checkpoint_root)
    eval_cfg = mcfg["panels"]["development"]
    eval_rows = make_rows("nonpanel_methods_smoke_eval", 999004, ("realistic_noisy",), eval_cfg["blocks"], eval_cfg["rows_per_block"], mcfg["panels"]["target_values"])
    records, summary = score_methods(eval_rows, models, bcfg, mcfg, "development", device)
    expected = {m.name for m in base_method_models()}
    if not expected.issubset(summary["methods"]):
        raise RuntimeError("registered incomplete method absent from smoke")
    if not summary["methods"]["ground_truth"]["matched"]["all_gates_pass"]:
        raise RuntimeError("ground-truth method smoke failed")
    if not summary["technical_valid"]:
        raise RuntimeError("method smoke technical failure")
    atomic_json(target, {"schema_version": "transformer_realistic_methods_v1_smoke", "device": str(device), "fit": fit, "summary": summary, "rows_scored": len(records), "scientific_panels_read": False, "learned_steps": 2})
    print(json.dumps({"status": "PASS", "methods": len(models), "path": target.relative_to(ROOT).as_posix()}))


def create_generator_locks() -> None:
    candidate_preflight()
    for kind, cfg_path in (("bridge", BRIDGE_CONFIG), ("methods", METHODS_CONFIG)):
        cfg = config(cfg_path)
        lock = generator_lock_path(kind)
        if lock.exists():
            raise RuntimeError(f"generator lock exists: {kind}")
        review = ROOT / cfg["runtime"]["candidate_review"]
        if not review.is_file() or not review.read_text().startswith("VERDICT: SHIP"):
            raise RuntimeError(f"candidate review not SHIP: {kind}")
        paths = candidate_paths(kind)
        # Candidate smoke/calibration are protocol inputs and must exist before lock.
        bcfg = config(BRIDGE_CONFIG)
        paths.extend(
            [
                ROOT / bcfg["runtime"]["candidate_root"] / "SMOKE_CPU.json",
                ROOT / bcfg["runtime"]["candidate_root"] / "SMOKE_GPU.json",
                ROOT / bcfg["runtime"]["candidate_root"] / "CALIBRATION.json",
                review,
            ]
        )
        if kind == "methods":
            paths.append(ROOT / cfg["runtime"]["candidate_root"] / "METHODS_SMOKE_GPU.json")
        inv = inventory(sorted(set(paths), key=lambda p: p.relative_to(ROOT).as_posix()))
        atomic_json(lock, {"schema_version": f"transformer_realistic_{kind}_v1_generator_lock", "status": "LOCKED_BEFORE_SCIENTIFIC_PAYLOAD_GENERATION", "kind": kind, "config_sha256": sha(cfg_path), "candidate_inventory": inv, "candidate_inventory_sha256": hashlib.sha256(canonical(inv)).hexdigest(), "scientific_seed_values_locked": True, "scientific_payloads_generated": False})
    print(json.dumps({"status": "PASS", "bridge_lock": sha(generator_lock_path("bridge")), "methods_lock": sha(generator_lock_path("methods"))}, sort_keys=True))


def verify_generator_lock(kind: str) -> dict[str, Any]:
    cfg_path = BRIDGE_CONFIG if kind == "bridge" else METHODS_CONFIG
    lock = loadj(generator_lock_path(kind))
    if lock["config_sha256"] != sha(cfg_path) or hashlib.sha256(canonical(lock["candidate_inventory"])).hexdigest() != lock["candidate_inventory_sha256"]:
        raise RuntimeError(f"generator lock digest {kind}")
    for item in lock["candidate_inventory"]:
        path = ROOT / item["path"]
        if not path.is_file() or path.stat().st_size != item["bytes"] or sha(path) != item["sha256"]:
            raise RuntimeError(f"generator drift {kind}:{item['path']}")
    return lock


def prepare() -> None:
    bridge_lock = verify_generator_lock("bridge")
    methods_lock = verify_generator_lock("methods")
    bcfg, mcfg = config(BRIDGE_CONFIG), config(METHODS_CONFIG)
    b_root = ROOT / bcfg["runtime"]["prepared_root"]
    m_root = ROOT / mcfg["runtime"]["prepared_root"]
    if any(b_root.iterdir()) or any(m_root.iterdir()):
        raise RuntimeError("prepared root is not empty")
    b_panels = {}
    for stage, seed in (("development", bcfg["panels"]["development_seed"]), ("confirmation", bcfg["panels"]["confirmation_seed"])):
        rows = make_rows(stage, seed, REGIME_ORDER, bcfg["panels"]["blocks_per_regime"], bcfg["panels"]["rows_per_block"], bcfg["panels"]["target_values"])
        path = b_root / f"{stage}.jsonl"
        write_rows(path, rows)
        b_panels[stage] = {"path": path.relative_to(ROOT).as_posix(), "bytes": path.stat().st_size, "sha256": sha(path), "rows": len(rows)}
    m_panels = {}
    for stage in ("train", "development", "confirmation"):
        pc = mcfg["panels"][stage]
        rows = make_rows(f"methods_{stage}", pc["seed"], ("realistic_noisy",), pc["blocks"], pc["rows_per_block"], mcfg["panels"]["target_values"])
        path = m_root / f"{stage}.jsonl"
        write_rows(path, rows)
        m_panels[stage] = {"path": path.relative_to(ROOT).as_posix(), "bytes": path.stat().st_size, "sha256": sha(path), "rows": len(rows)}
    # Cross-split row IDs and row seeds are disjoint by construction.
    all_meta = list(b_panels.values()) + list(m_panels.values())
    if len({x["sha256"] for x in all_meta}) != len(all_meta):
        raise RuntimeError("panel digest collision")
    atomic_json(b_root / "PANEL_METADATA.json", {"schema_version": "transformer_realistic_bridge_v1_panel_metadata", "generator_lock_sha256": sha(generator_lock_path("bridge")), "panels": b_panels})
    atomic_json(m_root / "PANEL_METADATA.json", {"schema_version": "transformer_realistic_methods_v1_panel_metadata", "generator_lock_sha256": sha(generator_lock_path("methods")), "panels": m_panels})
    atomic_json(b_root / "PREPARED.json", {"status": "PREPARED_AFTER_GENERATOR_LOCK", "generator_lock_inventory_sha256": bridge_lock["candidate_inventory_sha256"], "scientific_payloads_opened_for_scoring": False})
    atomic_json(m_root / "PREPARED.json", {"status": "PREPARED_AFTER_GENERATOR_LOCK", "generator_lock_inventory_sha256": methods_lock["candidate_inventory_sha256"], "scientific_payloads_opened_for_scoring": False})
    subprocess.check_call([sys.executable, str(RECOVERY_VERIFIER), "write-continuity"], env={**os.environ, "MSAE_ROOT": str(ROOT)})
    print(json.dumps({"status": "PASS", "bridge_panels": b_panels, "methods_panels": m_panels}, sort_keys=True))


def experiment_inventory(kind: str) -> list[dict[str, Any]]:
    cfg = config(BRIDGE_CONFIG if kind == "bridge" else METHODS_CONFIG)
    paths = candidate_paths(kind)
    bcfg = config(BRIDGE_CONFIG)
    paths.extend([ROOT / bcfg["runtime"]["candidate_root"] / n for n in ("SMOKE_CPU.json", "SMOKE_GPU.json", "CALIBRATION.json")])
    if kind == "methods":
        paths.append(ROOT / cfg["runtime"]["candidate_root"] / "METHODS_SMOKE_GPU.json")
    paths.extend((generator_lock_path(kind), ROOT / cfg["runtime"]["candidate_review"], ROOT / cfg["runtime"]["prepared_root"] / "PANEL_METADATA.json", ROOT / cfg["runtime"]["prepared_root"] / "PREPARED.json"))
    paths.append(RECOVERY_CONTINUITY)
    return inventory(sorted(set(paths), key=lambda p: p.relative_to(ROOT).as_posix()))


def freeze() -> None:
    for kind, cfg_path in (("bridge", BRIDGE_CONFIG), ("methods", METHODS_CONFIG)):
        verify_generator_lock(kind)
        cfg = config(cfg_path)
        target = freeze_path(kind)
        if target.exists():
            raise RuntimeError(f"freeze exists: {kind}")
        metadata = loadj(ROOT / cfg["runtime"]["prepared_root"] / "PANEL_METADATA.json")
        inv = experiment_inventory(kind)
        atomic_json(target, {"schema_version": f"transformer_realistic_{kind}_v1_experiment_freeze", "status": "FROZEN_BEFORE_SCIENTIFIC_OPENING", "kind": kind, "generator_lock_sha256": sha(generator_lock_path(kind)), "candidate_inventory": inv, "candidate_inventory_sha256": hashlib.sha256(canonical(inv)).hexdigest(), "opaque_panel_metadata": metadata["panels"], "panel_paths_accessed_during_freeze": False})
    print(json.dumps({"status": "PASS", "bridge_freeze": sha(freeze_path("bridge")), "methods_freeze": sha(freeze_path("methods"))}, sort_keys=True))


def verify_freeze(kind: str) -> dict[str, Any]:
    verify_generator_lock(kind)
    cfg = config(BRIDGE_CONFIG if kind == "bridge" else METHODS_CONFIG)
    rec = loadj(freeze_path(kind))
    if rec["generator_lock_sha256"] != sha(generator_lock_path(kind)) or hashlib.sha256(canonical(rec["candidate_inventory"])).hexdigest() != rec["candidate_inventory_sha256"]:
        raise RuntimeError(f"freeze digest {kind}")
    for item in rec["candidate_inventory"]:
        path = ROOT / item["path"]
        if not path.is_file() or path.stat().st_size != item["bytes"] or sha(path) != item["sha256"]:
            raise RuntimeError(f"frozen drift {kind}:{item['path']}")
    return rec


def bind_reviews() -> None:
    for kind, cfg_path in (("bridge", BRIDGE_CONFIG), ("methods", METHODS_CONFIG)):
        rec = verify_freeze(kind)
        cfg = config(cfg_path)
        review = ROOT / cfg["runtime"]["frozen_review"]
        if not review.is_file() or not review.read_text().startswith("VERDICT: SHIP"):
            raise RuntimeError(f"frozen review not SHIP: {kind}")
        target = ROOT / cfg["runtime"]["candidate_root"] / "FROZEN_REVIEW_BINDING.json"
        atomic_json(target, {"schema_version": f"transformer_realistic_{kind}_v1_frozen_review_binding", "status": "BOUND", "freeze_sha256": sha(freeze_path(kind)), "candidate_inventory_sha256": rec["candidate_inventory_sha256"], "review_path": review.relative_to(ROOT).as_posix(), "review_sha256": sha(review)})
    print(json.dumps({"status": "PASS"}))


def verify_review_binding(kind: str) -> dict[str, Any]:
    rec = verify_freeze(kind)
    cfg = config(BRIDGE_CONFIG if kind == "bridge" else METHODS_CONFIG)
    target = ROOT / cfg["runtime"]["candidate_root"] / "FROZEN_REVIEW_BINDING.json"
    bind = loadj(target)
    review = ROOT / bind["review_path"]
    if bind["freeze_sha256"] != sha(freeze_path(kind)) or bind["candidate_inventory_sha256"] != rec["candidate_inventory_sha256"] or bind["review_sha256"] != sha(review) or not review.read_text().startswith("VERDICT: SHIP"):
        raise RuntimeError(f"review binding {kind}")
    return bind


def launch_manifest_path(kind: str) -> Path:
    cfg = config(BRIDGE_CONFIG if kind == "bridge" else METHODS_CONFIG)
    return ROOT / cfg["runtime"]["provenance_root"] / "launch_manifest.json"


def validate_gpu(physical_index: int, expected_uuid: str) -> torch.device:
    if os.environ.get("CUDA_VISIBLE_DEVICES") != str(physical_index):
        raise RuntimeError("CUDA_VISIBLE_DEVICES mismatch")
    observed = subprocess.check_output(["nvidia-smi", "--query-gpu=uuid", "--format=csv,noheader", "-i", str(physical_index)], text=True).strip()
    if observed != expected_uuid:
        raise RuntimeError(f"physical GPU UUID mismatch: {observed} != {expected_uuid}")
    if not torch.cuda.is_available() or torch.cuda.device_count() != 1:
        raise RuntimeError("expected exactly one visible CUDA device")
    torch.use_deterministic_algorithms(True)
    torch.backends.cudnn.benchmark = False
    return torch.device("cuda:0")


def create_launch_manifests(physical_index: int, gpu_uuid: str, launch_token: str) -> None:
    for kind, cfg_path in (("bridge", BRIDGE_CONFIG), ("methods", METHODS_CONFIG)):
        verify_review_binding(kind)
        cfg = config(cfg_path)
        prov = ROOT / cfg["runtime"]["provenance_root"]
        prov.mkdir(parents=True, exist_ok=True)
        binding = ROOT / cfg["runtime"]["candidate_root"] / "FROZEN_REVIEW_BINDING.json"
        atomic_json(prov / "launch_manifest.json", {
            "schema_version": f"transformer_realistic_{kind}_v1_launch_manifest",
            "status": "LAUNCHED", "kind": kind, "launch_token": launch_token,
            "physical_gpu_index": physical_index, "gpu_uuid": gpu_uuid,
            "cuda_visible_devices": os.environ.get("CUDA_VISIBLE_DEVICES"),
            "freeze_sha256": sha(freeze_path(kind)), "generator_lock_sha256": sha(generator_lock_path(kind)),
            "review_binding_sha256": sha(binding), "python": sys.version, "platform": platform.platform(),
            "torch": torch.__version__, "numpy": np.__version__,
            "cublas_workspace_config": os.environ.get("CUBLAS_WORKSPACE_CONFIG"), "time_ns": time.time_ns(),
        })


def validate_launch(kind: str, token: str) -> dict[str, Any]:
    cfg = config(BRIDGE_CONFIG if kind == "bridge" else METHODS_CONFIG)
    rec = loadj(launch_manifest_path(kind))
    binding = ROOT / cfg["runtime"]["candidate_root"] / "FROZEN_REVIEW_BINDING.json"
    if rec["launch_token"] != token or rec["freeze_sha256"] != sha(freeze_path(kind)) or rec["review_binding_sha256"] != sha(binding):
        raise RuntimeError(f"launch lineage {kind}")
    return rec


def event(root: Path, index: int, state: str, **extra: Any) -> None:
    atomic_json(root / f"{index:02d}_{state}.json", {"state": state, "time_ns": time.time_ns(), **extra})


def open_panel(kind: str, stage: str, launch_token: str) -> list[dict[str, Any]]:
    cfg = config(BRIDGE_CONFIG if kind == "bridge" else METHODS_CONFIG)
    validate_launch(kind, launch_token)
    freeze_rec = verify_freeze(kind)
    metadata = freeze_rec["opaque_panel_metadata"][stage]
    events = ROOT / cfg["runtime"]["provenance_root"] / "panel_opening" / stage
    if events.exists():
        raise RuntimeError(f"panel opening already attempted: {kind}:{stage}")
    events.mkdir(parents=True)
    event(events, 0, "PRECHECK_JOURNALED_NO_ACCESS", payload_access_may_have_occurred=False, metadata=metadata)
    event(events, 1, "ACCESS_MAY_HAVE_OCCURRED", payload_access_may_have_occurred=True)
    path = ROOT / metadata["path"]
    try:
        size, digest = path.stat().st_size, sha(path)
        if size != metadata["bytes"] or digest != metadata["sha256"]:
            raise RuntimeError("panel hash mismatch")
        rows = read_rows(path)
        if len(rows) != metadata["rows"]:
            raise RuntimeError("panel row mismatch")
        event(events, 2, "CLOSED_OPENED", payload_access_may_have_occurred=True, payload_bytes=size, payload_sha256=digest, rows=len(rows))
        return rows
    except Exception as exc:
        event(events, 2, "CLOSED_TECHNICAL_INVALID", payload_access_may_have_occurred=True, reason=f"{type(exc).__name__}: {exc}")
        raise


def write_jsonl(path: Path, rows: Sequence[Mapping[str, Any]]) -> None:
    atomic_text(path, "".join(json.dumps(row, sort_keys=True, allow_nan=False) + "\n" for row in rows))


def run_bridge_stage(stage: str, launch_token: str, device: torch.device) -> dict[str, Any]:
    cfg = config(BRIDGE_CONFIG)
    out = ROOT / cfg["runtime"]["output_root"] / stage
    if out.exists():
        raise RuntimeError(f"bridge stage exists: {stage}")
    out.mkdir(parents=True)
    atomic_json(out / "STARTED.json", {"status": "RUNNING", "stage": stage, "launch_manifest_sha256": sha(launch_manifest_path("bridge")), **SCOPE_BRIDGE})
    rows = open_panel("bridge", stage, launch_token)
    records, summary, qa = score_bridge_rows(rows, cfg, stage, device)
    write_jsonl(out / "metrics.jsonl", records)
    atomic_json(out / "QA.json", qa)
    atomic_json(out / "SUMMARY.json", summary)
    atomic_json(out / "COMPLETE.json", {"status": "COMPLETE", "summary_sha256": sha(out / "SUMMARY.json"), "metrics_sha256": sha(out / "metrics.jsonl"), "qa_sha256": sha(out / "QA.json"), **SCOPE_BRIDGE})
    return summary


def finalize_bridge(development: Mapping[str, Any] | None, confirmation: Mapping[str, Any] | None, error: str | None = None) -> dict[str, Any]:
    cfg = config(BRIDGE_CONFIG); out = ROOT / cfg["runtime"]["output_root"]
    if error: status = "TECHNICAL_INVALID_STOP"
    elif not development or not development["all_gates_pass"]: status = "DEVELOPMENT_BRIDGE_STOP"
    elif not confirmation or not confirmation["all_gates_pass"]: status = "CONFIRMATION_BRIDGE_STOP"
    else: status = "TRANSFORMER_REALISTIC_GROUND_TRUTH_CONFIRMED"
    payload = {"schema_version": "transformer_realistic_bridge_v1_final", "status": status, "development": development, "confirmation": confirmation, "validation_error": error, "methods_authorized": status == "TRANSFORMER_REALISTIC_GROUND_TRUTH_CONFIRMED", "launch_manifest_sha256": sha(launch_manifest_path("bridge")), "freeze_sha256": sha(freeze_path("bridge")), **SCOPE_BRIDGE}
    atomic_json(out / "final/result.json", payload)
    return payload


def block_methods(bridge_final: Mapping[str, Any], reason: str) -> None:
    cfg = config(METHODS_CONFIG); out = ROOT / cfg["runtime"]["output_root"]
    out.mkdir(parents=True, exist_ok=True)
    bridge_path = ROOT / config(BRIDGE_CONFIG)["runtime"]["output_root"] / "final/result.json"
    atomic_json(out / "METHODS_BLOCKED.json", {"schema_version": "transformer_realistic_methods_v1_blocked", "status": "BLOCKED_UNOPENED", "reason": reason, "bridge_status": bridge_final["status"], "bridge_final_sha256": sha(bridge_path), "train_payload_touched": False, "development_payload_touched": False, "confirmation_payload_touched": False, "training_performed": False, **SCOPE_METHODS, "representation_methods_evaluated": False})
    atomic_json(out / "final/result.json", {"schema_version": "transformer_realistic_methods_v1_final", "status": "BLOCKED_UNOPENED", "bridge_status": bridge_final["status"], "training_performed": False, "confirmation_opened": False, **SCOPE_METHODS, "representation_methods_evaluated": False})


def authorize_methods(bridge_final: Mapping[str, Any], launch_token: str) -> None:
    if bridge_final["status"] != "TRANSFORMER_REALISTIC_GROUND_TRUTH_CONFIRMED":
        raise RuntimeError("bridge did not authorize methods")
    cfg = config(METHODS_CONFIG); validate_launch("methods", launch_token)
    out = ROOT / cfg["runtime"]["output_root"]
    out.mkdir(parents=True, exist_ok=False)
    events = ROOT / cfg["runtime"]["provenance_root"] / "authorization_events"; events.mkdir(parents=True)
    bridge_path = ROOT / config(BRIDGE_CONFIG)["runtime"]["output_root"] / "final/result.json"
    event(events, 0, "PRECHECK_JOURNALED_NO_ACCESS", payload_access_may_have_occurred=False, bridge_final_sha256=sha(bridge_path))
    target = out / "authorization/METHODS_AUTHORIZATION.json"
    atomic_json(target, {"schema_version": "transformer_realistic_methods_v1_authorization", "status": "AUTHORIZED", "bridge_status": bridge_final["status"], "bridge_final_sha256": sha(bridge_path), "methods_freeze_sha256": sha(freeze_path("methods")), "scientific_payload_accessed": False})
    event(events, 1, "CLOSED_AUTHORIZED_NO_ACCESS", payload_access_may_have_occurred=False, authorization_sha256=sha(target))


def run_methods(bridge_final: Mapping[str, Any], launch_token: str, device: torch.device) -> dict[str, Any]:
    bcfg, mcfg = config(BRIDGE_CONFIG), config(METHODS_CONFIG)
    authorize_methods(bridge_final, launch_token)
    out = ROOT / mcfg["runtime"]["output_root"]
    try:
        train_rows = open_panel("methods", "train", launch_token)
        models, _ = fit_methods(train_rows, bcfg, mcfg, device, out / "checkpoints")
        summaries = {}
        for stage in ("development", "confirmation"):
            rows = open_panel("methods", stage, launch_token)
            stage_out = out / stage; stage_out.mkdir(parents=True)
            records, summary = score_methods(rows, models, bcfg, mcfg, stage, device)
            write_jsonl(stage_out / "metrics.jsonl", records)
            atomic_json(stage_out / "SUMMARY.json", summary)
            atomic_json(stage_out / "COMPLETE.json", {"status": "COMPLETE", "summary_sha256": sha(stage_out / "SUMMARY.json"), "metrics_sha256": sha(stage_out / "metrics.jsonl")})
            summaries[stage] = summary
        final = {"schema_version": "transformer_realistic_methods_v1_final", "status": "METHOD_BENCHMARK_COMPLETE", "bridge_final_sha256": sha(ROOT / bcfg["runtime"]["output_root"] / "final/result.json"), "training_performed": True, "fit_summary_sha256": sha(out / "checkpoints/FIT_SUMMARY.json"), "development": summaries["development"], "confirmation": summaries["confirmation"], "prospective_interpretation": "RESULT_PENDING_POSTRESULT_CLAIM_REVIEW", **SCOPE_METHODS, "representation_methods_evaluated": True}
        atomic_json(out / "final/result.json", final)
        return final
    except Exception as exc:
        final = {"schema_version": "transformer_realistic_methods_v1_final", "status": "METHODS_TECHNICAL_INVALID_STOP", "reason": f"{type(exc).__name__}: {exc}", "training_may_have_occurred": (out / "checkpoints").exists(), **SCOPE_METHODS, "representation_methods_evaluated": True}
        if not (out / "final/result.json").exists(): atomic_json(out / "final/result.json", final)
        raise


def run_pipeline(physical_index: int, gpu_uuid: str, launch_token: str) -> None:
    device = validate_gpu(physical_index, gpu_uuid)
    for cfg_path in (BRIDGE_CONFIG, METHODS_CONFIG):
        cfg = config(cfg_path)
        if (ROOT / cfg["runtime"]["output_root"]).exists(): raise RuntimeError(f"output namespace exists: {cfg['namespace']}")
    create_launch_manifests(physical_index, gpu_uuid, launch_token)
    bcfg = config(BRIDGE_CONFIG); bout = ROOT / bcfg["runtime"]["output_root"]; bout.mkdir(parents=True)
    development = confirmation = None
    try:
        development = run_bridge_stage("development", launch_token, device)
        if development["all_gates_pass"]:
            confirmation = run_bridge_stage("confirmation", launch_token, device)
        else:
            atomic_json(bout / "confirmation/CONFIRMATION_BLOCKED.json", {"status": "BLOCKED_UNOPENED", "reason": "DEVELOPMENT_BRIDGE_STOP", "payload_touched": False, **SCOPE_BRIDGE})
        bridge_final = finalize_bridge(development, confirmation)
    except Exception as exc:
        bridge_final = finalize_bridge(development, confirmation, f"{type(exc).__name__}: {exc}")
    if bridge_final["status"] == "TRANSFORMER_REALISTIC_GROUND_TRUTH_CONFIRMED": run_methods(bridge_final, launch_token, device)
    else: block_methods(bridge_final, "BRIDGE_DID_NOT_CONFIRM")


def main() -> None:
    parser = argparse.ArgumentParser(); sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("candidate-preflight")
    p = sub.add_parser("smoke"); p.add_argument("--device", choices=("cpu", "cuda"), required=True)
    p = sub.add_parser("methods-smoke"); p.add_argument("--device", choices=("cuda",), required=True)
    for name in ("calibrate", "generator-lock", "prepare", "freeze", "bind-reviews"): sub.add_parser(name)
    p = sub.add_parser("verify-freeze"); p.add_argument("--kind", choices=("bridge", "methods", "both"), default="both")
    p = sub.add_parser("verify-review-binding"); p.add_argument("--kind", choices=("bridge", "methods", "both"), default="both")
    p = sub.add_parser("run-pipeline"); p.add_argument("--physical-index", type=int, required=True); p.add_argument("--gpu-uuid", required=True); p.add_argument("--launch-token", required=True)
    args = parser.parse_args()
    if args.command == "candidate-preflight": candidate_preflight()
    elif args.command == "smoke": smoke(args.device)
    elif args.command == "methods-smoke": methods_smoke(args.device)
    elif args.command == "calibrate": calibrate()
    elif args.command == "generator-lock": create_generator_locks()
    elif args.command == "prepare": prepare()
    elif args.command == "freeze": freeze()
    elif args.command == "verify-freeze":
        kinds = ("bridge", "methods") if args.kind == "both" else (args.kind,); print(json.dumps({k: verify_freeze(k)["candidate_inventory_sha256"] for k in kinds}, sort_keys=True))
    elif args.command == "bind-reviews": bind_reviews()
    elif args.command == "verify-review-binding":
        kinds = ("bridge", "methods") if args.kind == "both" else (args.kind,); print(json.dumps({k: verify_review_binding(k)["review_sha256"] for k in kinds}, sort_keys=True))
    elif args.command == "run-pipeline": run_pipeline(args.physical_index, args.gpu_uuid, args.launch_token)


if __name__ == "__main__": main()
