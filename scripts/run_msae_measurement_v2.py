#!/usr/bin/env python3
"""Stage CLI for the config-bound Atlas/MSAE measurement-v2 experiment."""

from __future__ import annotations

import argparse
import fcntl
import hashlib
import json
import math
import os
import platform
from pathlib import Path
import shutil
import subprocess
import sys
import time
from typing import Any, Mapping, Sequence

import numpy as np

from msae_measurement_v2_run import (
    ALL_TASKS, DIAGNOSTIC_TASKS, FAMILY_TASKS, PRIMARY_TASKS, ROLES, ROOT,
    atomic_create_json, atomic_write_json, cache_manifest, cka_torch, config_sha, cosine_distance,
    group_multiplicities, interval, load_config, prepare_data, read_json,
    read_jsonl, root_path, select_cka_rows, sha256_file, sign_builder_payload,
    source_grouping, stable_key, verify_file, verify_prepared, weighted_macro_f1,
    write_vector_cache,
)


def runtime_environment(device: str | None = None) -> dict[str, Any]:
    result: dict[str, Any] = {"python": platform.python_version(), "numpy": np.__version__}
    try:
        import torch
        result.update({"torch": torch.__version__, "cuda": torch.version.cuda,
            "deterministic_algorithms":torch.are_deterministic_algorithms_enabled(),
            "cuda_matmul_allow_tf32":torch.backends.cuda.matmul.allow_tf32,
            "cudnn_allow_tf32":torch.backends.cudnn.allow_tf32,
            "float32_matmul_precision":torch.get_float32_matmul_precision()})
        if device and torch.cuda.is_available():
            result["gpu"] = torch.cuda.get_device_name(device)
    except Exception as exc:
        result["torch_error"] = str(exc)
    try:
        result["git_head"] = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
        diff = subprocess.check_output(["git", "diff", "--binary"], cwd=ROOT)
        result["git_diff_sha256"] = hashlib.sha256(diff).hexdigest()
    except Exception as exc:
        result["git_error"] = str(exc)
    try:
        import importlib.metadata as metadata
        result["packages"]={name:metadata.version(name) for name in ("transformers","tokenizers","cryptography")}
    except Exception as exc:result["package_version_error"]=str(exc)
    return result


def run_root(cfg: Mapping[str, Any]) -> Path:
    return root_path(str(cfg["run_root"]))


def _configure_torch(cfg: Mapping[str,Any]) -> None:
    import torch
    torch.manual_seed(int(cfg["seed"]));torch.cuda.manual_seed_all(int(cfg["seed"]))
    torch.use_deterministic_algorithms(True)
    torch.backends.cuda.matmul.allow_tf32=False;torch.backends.cudnn.allow_tf32=False
    torch.set_float32_matmul_precision("highest")


def _producer_lineage() -> dict[str,str]:
    job=os.environ.get("MSAE_V2_PRODUCER_JOB");command_sha=os.environ.get("MSAE_V2_PRODUCER_COMMAND_SHA256")
    if not job or not command_sha or len(command_sha)!=64:raise RuntimeError("GPU stage is not owned by a recorded v2 producer job")
    return {"producer_job":job,"producer_command_sha256":command_sha}


def _prepared_paths(cfg: Mapping[str, Any], role: str) -> tuple[Path, list[dict[str, Any]], list[dict[str, Any]]]:
    role_dir = root_path(str(cfg["data_root"])) / "prepared" / role
    units = read_jsonl(role_dir / "inference_units.jsonl")
    rows = read_jsonl(role_dir / "activation_rows.jsonl")
    return role_dir, units, rows


def _inference_batches(model: Any, units: Sequence[Mapping[str, Any]], *, device: str, batch_size: int,
                       hidden_index: int) -> np.ndarray:
    import torch
    total = sum(len(unit["positions"]) for unit in units)
    values: np.ndarray | None = None
    cursor = 0
    for start in range(0, len(units), batch_size):
        batch = units[start:start+batch_size]
        max_len = max(len(unit["input_ids"]) for unit in batch)
        input_ids = torch.zeros((len(batch), max_len), dtype=torch.long, device=device)
        attention = torch.zeros_like(input_ids)
        for bi, unit in enumerate(batch):
            n = len(unit["input_ids"])
            input_ids[bi, :n] = torch.tensor(unit["input_ids"], dtype=torch.long, device=device)
            attention[bi, :n] = 1
        with torch.inference_mode():
            output = model(input_ids, attention_mask=attention, output_hidden_states=True, use_cache=False)
        hidden = output.hidden_states[hidden_index]
        if values is None:
            values = np.empty((total, int(hidden.shape[-1])), dtype=np.float32)
        for bi, unit in enumerate(batch):
            positions = list(map(int, unit["positions"]))
            n = len(positions)
            if n:
                values[cursor:cursor+n] = hidden[bi, positions].detach().float().cpu().numpy()
            cursor += n
    if values is None or cursor != total:
        raise RuntimeError("inference row mismatch")
    return values


def _validated_raw_cache(cfg: Mapping[str, Any], config_path: Path, role: str) -> dict[str, Any]:
    directory = run_root(cfg) / "raw_cache" / role
    manifest = cache_manifest(directory)
    lineage = manifest.get("lineage", {})
    expected_prepared = sha256_file(root_path(str(cfg["data_root"])) / "prepared/manifest.json")
    required = {"kind":"raw","role":role,"config_sha256":sha256_file(config_path),
                "prepared_manifest_sha256":expected_prepared,"model":cfg["model"]}
    for key,value in required.items():
        if lineage.get(key) != value: raise RuntimeError(f"raw-cache lineage drift {role}:{key}")
    prepared_rows = read_jsonl(root_path(str(cfg["data_root"])) / "prepared" / role / "activation_rows.jsonl")
    if read_json(directory/"row_ids.json") != [row["row_id"] for row in prepared_rows]:
        raise RuntimeError(f"raw-cache row lineage drift: {role}")
    return manifest


def _validated_transform(cfg: Mapping[str, Any], config_path: Path, job: str) -> dict[str, Any]:
    spec=next((row for row in cfg["checkpoints"] if row["id"]==job),None)
    if spec is None:raise RuntimeError(f"unknown transform lineage job: {job}")
    directory=run_root(cfg)/"transforms"/job;complete=read_json(directory/"COMPLETE.json")
    if complete.get("config_sha256")!=sha256_file(config_path) or complete.get("checkpoint")!=spec:
        raise RuntimeError(f"transform completion lineage drift: {job}")
    for role in ROLES:
        raw_manifest=_validated_raw_cache(cfg,config_path,role)
        raw_ids=read_json(run_root(cfg)/"raw_cache"/role/"row_ids.json")
        for branch in ("pos","content"):
            branch_dir=directory/role/branch;manifest=cache_manifest(branch_dir);lineage=manifest.get("lineage",{})
            expected={"kind":"k2","branch":branch,"checkpoint":spec,"raw_manifest":raw_manifest,
                      "config_sha256":sha256_file(config_path)}
            for key,value in expected.items():
                if lineage.get(key)!=value:raise RuntimeError(f"transform cache lineage drift {job}/{role}/{branch}:{key}")
            if read_json(branch_dir/"row_ids.json")!=raw_ids:
                raise RuntimeError(f"transform row lineage drift: {job}/{role}/{branch}")
            digest_key=f"{branch}_manifest_sha256"
            if complete["roles"][role][digest_key]!=sha256_file(branch_dir/"manifest.json"):
                raise RuntimeError(f"transform completion manifest drift: {job}/{role}/{branch}")
    return complete


def stage_extract(cfg: Mapping[str, Any], config_path: Path, role: str, device: str, batch_size: int) -> dict[str, Any]:
    import torch
    from transformers import AutoModelForCausalLM
    from train_msae_k2 import resolve_hidden_state_index
    _configure_torch(cfg)

    prepared = verify_prepared(cfg, config_path)
    _, units, rows = _prepared_paths(cfg, role)
    expected_ids = [row["row_id"] for row in rows]
    flattened = [row_id for unit in units for row_id in unit["row_ids"]]
    if flattened != expected_ids:
        raise RuntimeError("prepared unit/row order mismatch")
    output = run_root(cfg) / "raw_cache" / role
    if output.exists():
        return _validated_raw_cache(cfg,config_path,role)
    if not torch.cuda.is_available() or not device.startswith("cuda"):
        raise RuntimeError("real v2 extraction requires CUDA")
    started = time.time()
    model = AutoModelForCausalLM.from_pretrained(
        cfg["model"]["name"], revision=cfg["model"]["revision"],
        torch_dtype=torch.float16, local_files_only=True,
    ).to(device).eval()
    first = torch.tensor([units[0]["input_ids"]], dtype=torch.long, device=device)
    with torch.inference_mode():
        first_output = model(first, output_hidden_states=True, use_cache=False)
    hidden_index = resolve_hidden_state_index(int(cfg["model"]["layer"]), len(first_output.hidden_states))
    values = _inference_batches(model, units, device=device, batch_size=batch_size, hidden_index=hidden_index)
    qa: dict[str, Any] | None = None
    if role == "calibration":
        ordered = sorted(units, key=lambda unit: stable_key("numerical-qa-unit", str(unit["unit_id"])))
        size = int(cfg["numerical_qa"]["set_size"])
        if len(ordered) < 2*size:
            raise RuntimeError("too few calibration units for held-out numerical QA")
        set_results: dict[str, list[np.ndarray]] = {}
        for name, subset in (("A", ordered[:size]), ("B", ordered[size:2*size])):
            set_results[name] = [
                _inference_batches(model, subset, device=device, batch_size=batch_size, hidden_index=hidden_index)
                for _ in range(int(cfg["numerical_qa"]["repeats"]))
            ]
        a_ref = set_results["A"][0].astype(np.float64)
        a_max = max(float(np.max(np.abs(x.astype(np.float64)-a_ref))) for x in set_results["A"][1:])
        atol = max(float(cfg["numerical_qa"]["atol_floor"]), float(cfg["numerical_qa"]["atol_multiplier"])*a_max)
        if atol > float(cfg["numerical_qa"]["atol_hard_ceiling"]):
            raise RuntimeError(f"calibration numerical tolerance exceeds hard ceiling: {atol}")
        rtol = float(cfg["numerical_qa"]["rtol"])
        b_ref = set_results["B"][0].astype(np.float64)
        b_diffs = [np.abs(x.astype(np.float64)-b_ref) for x in set_results["B"][1:]]
        b_max = max(float(np.max(x)) for x in b_diffs)
        passed = all(bool(np.all(diff <= atol + rtol*np.abs(b_ref))) for diff in b_diffs)
        qa = {"set_size": size, "repeats": 3, "set_A_max_abs_error": a_max, "atol": atol,
              "rtol": rtol, "hard_ceiling": cfg["numerical_qa"]["atol_hard_ceiling"],
              "set_B_max_abs_error": b_max, "heldout_passed": passed}
        if not passed:
            raise RuntimeError("held-out numerical reproducibility QA failed")
    lineage = {
        "kind": "raw", "role": role, "config_sha256": sha256_file(config_path),
        "prepared_manifest_sha256": sha256_file(root_path(str(cfg["data_root"])) / "prepared/manifest.json"),
        "model": cfg["model"], "hidden_state_index": hidden_index, "batch_size": batch_size,
        "numerical_qa": qa, "elapsed_sec": time.time()-started, "environment": runtime_environment(device),
        **_producer_lineage(),
    }
    return write_vector_cache(output, values, expected_ids, lineage)


def stage_transform(cfg: Mapping[str, Any], config_path: Path, job: str, device: str, batch_size: int) -> dict[str, Any]:
    import torch
    from train_msae_k2 import K2MSAE
    _configure_torch(cfg)

    spec = next((row for row in cfg["checkpoints"] if row["id"] == job), None)
    if spec is None:
        raise ValueError(f"unknown checkpoint: {job}")
    checkpoint_path = root_path(spec["path"]); verify_file(checkpoint_path, spec["sha256"])
    checkpoint = torch.load(checkpoint_path, map_location="cpu", weights_only=False)
    cargs = checkpoint["args"]
    model = K2MSAE(d_model=768, m_pos=int(cargs["m_pos"]), k_pos=int(cargs["k_pos"]),
                   m_content=int(cargs["m_content"]), k_content=int(cargs["k_content"]))
    model.load_state_dict(checkpoint["model"]); model.to(device).eval()
    output_root = run_root(cfg) / "transforms" / job
    if (output_root / "COMPLETE.json").exists():
        return _validated_transform(cfg,config_path,job)
    if output_root.exists():
        raise RuntimeError(f"nonterminal transform output: {output_root}")
    tmp = output_root.parent / f".{job}.{os.getpid()}.tmp"; tmp.mkdir(parents=True)
    roles: dict[str, Any] = {}; started = time.time()
    with torch.inference_mode():
        for role in ROLES:
            raw_dir = run_root(cfg) / "raw_cache" / role
            raw_manifest = cache_manifest(raw_dir)
            raw = np.load(raw_dir / "values.float32.npy", mmap_mode="r")
            row_ids = read_json(raw_dir / "row_ids.json")
            pos = np.empty(raw.shape, np.float32); content = np.empty(raw.shape, np.float32)
            for start in range(0, len(raw), batch_size):
                x = torch.from_numpy(np.asarray(raw[start:start+batch_size], np.float32)).to(device)
                transformed = model(x)
                pos[start:start+len(x)] = transformed["recon_pos"].detach().float().cpu().numpy()
                content[start:start+len(x)] = transformed["recon_content"].detach().float().cpu().numpy()
            role_dir = tmp / role; role_dir.mkdir()
            pos_m = write_vector_cache(role_dir / "pos", pos, row_ids, {
                "kind": "k2", "branch": "pos", "checkpoint": spec, "raw_manifest": raw_manifest,
                "config_sha256": sha256_file(config_path),**_producer_lineage(),
            })
            content_m = write_vector_cache(role_dir / "content", content, row_ids, {
                "kind": "k2", "branch": "content", "checkpoint": spec, "raw_manifest": raw_manifest,
                "config_sha256": sha256_file(config_path),**_producer_lineage(),
            })
            roles[role] = {"pos_manifest_sha256": sha256_file(role_dir / "pos/manifest.json"),
                           "content_manifest_sha256": sha256_file(role_dir / "content/manifest.json"),
                           "rows": len(raw)}
    complete = {"schema_version": "atlas_measurement_v2_transform_complete_v1", "job": job,
                "checkpoint": spec, "roles": roles, "elapsed_sec": time.time()-started,
                "config_sha256": sha256_file(config_path), "environment": runtime_environment(device)}
    complete.update(_producer_lineage())
    atomic_write_json(tmp / "COMPLETE.json", complete)
    output_root.parent.mkdir(parents=True, exist_ok=True); os.replace(tmp, output_root)
    return _validated_transform(cfg,config_path,job)


def _task_data(cfg: Mapping[str, Any], role: str, task: str) -> list[dict[str, Any]]:
    return read_jsonl(root_path(str(cfg["data_root"])) / "prepared" / role / "tasks" / f"{task}.jsonl")


def _representation_arrays(cfg: Mapping[str, Any], role: str) -> dict[str, np.ndarray]:
    arrays: dict[str, np.ndarray] = {
        "raw": np.load(run_root(cfg) / "raw_cache" / role / "values.float32.npy", mmap_mode="r")
    }
    for spec in cfg["checkpoints"]:
        for branch in ("pos", "content"):
            directory = run_root(cfg) / "transforms" / spec["id"] / role / branch
            cache_manifest(directory)
            arrays[f"{spec['id']}_{branch}"] = np.load(directory / "values.float32.npy", mmap_mode="r")
    return arrays


def _fit_ridge(x: np.ndarray, labels: np.ndarray, classes: int, alphas: Sequence[float],
               x_cal: np.ndarray, y_cal: np.ndarray, device: str) -> tuple[np.ndarray, np.ndarray, float, dict[str, float]]:
    import torch
    label_array=np.asarray(labels);cal_label_array=np.asarray(y_cal)
    if (label_array.ndim!=1 or cal_label_array.ndim!=1 or len(label_array)!=len(x) or len(cal_label_array)!=len(x_cal)
            or not np.issubdtype(label_array.dtype,np.integer) or not np.issubdtype(cal_label_array.dtype,np.integer)
            or np.any(label_array<0) or np.any(label_array>=classes)
            or np.any(cal_label_array<0) or np.any(cal_label_array>=classes)):
        raise ValueError("ridge labels must be in-range integer class indices")
    xt = torch.as_tensor(np.asarray(x, np.float32), device=device)
    # Prepared labels use compact integer dtypes; one_hot requires torch.long.
    yt = torch.nn.functional.one_hot(
        torch.as_tensor(label_array.astype(np.int64,copy=False), device=device), classes
    ).float()
    xmean = xt.mean(0); ymean = yt.mean(0); xc = xt-xmean; yc = yt-ymean
    gram = xc.T@xc; rhs = xc.T@yc
    eig, vec = torch.linalg.eigh(gram)
    projections = vec.T@rhs
    grid: dict[str, float] = {}; candidates: dict[float, tuple[np.ndarray, np.ndarray]] = {}
    cal = torch.as_tensor(np.asarray(x_cal, np.float32), device=device)
    for alpha in alphas:
        weight = vec @ (projections/(eig[:, None]+float(alpha)))
        bias = ymean - xmean@weight
        pred = torch.argmax(cal@weight+bias, dim=1).detach().cpu().numpy()
        score = weighted_macro_f1(y_cal, pred, np.ones(len(pred)), classes)
        grid[str(alpha)] = score
        candidates[float(alpha)] = (weight.detach().cpu().numpy().astype(np.float32), bias.detach().cpu().numpy().astype(np.float32))
    selected = max(map(float, alphas), key=lambda a: (grid[str(a)], a))
    weight, bias = candidates[selected]
    return weight, bias, selected, grid


def _predict(x: np.ndarray, weight: np.ndarray, bias: np.ndarray) -> np.ndarray:
    return np.argmax(np.asarray(x, np.float32)@weight+bias, axis=1).astype(np.int32)


def _scaler(array: np.ndarray, indices: np.ndarray, floor: float) -> tuple[np.ndarray, np.ndarray]:
    sample = np.asarray(array[indices], np.float64)
    mean = sample.mean(0); scale = sample.std(0)
    scale[scale < floor] = 1.0
    return mean.astype(np.float32), scale.astype(np.float32)


def _standardized(array: np.ndarray, indices: np.ndarray, mean: np.ndarray, scale: np.ndarray) -> np.ndarray:
    return (np.asarray(array[indices], np.float32)-mean)/scale


def _label_contract(cfg: Mapping[str, Any], task: str) -> tuple[list[str], dict[str, int]]:
    labels = sorted({str(row["label"]) for role in ROLES for row in _task_data(cfg, role, task)}, key=lambda x: x.encode())
    if len(labels) < 2:
        raise RuntimeError(f"task lacks labels: {task}")
    return labels, {label: i for i, label in enumerate(labels)}


def _bootstrap_scores(y: np.ndarray, pred: np.ndarray, groups: Sequence[str], *, role: str, source: str,
                      task: str, classes: int, cfg: Mapping[str, Any]) -> list[float]:
    values: list[float] = []
    group_array = np.asarray(groups, dtype=str)
    for draw in range(int(cfg["bootstrap"]["draws"])):
        mult = group_multiplicities(
            groups, role=role, task=task, source=source, draw=draw, seed=int(cfg["seed"]),
        )
        weights = np.asarray([mult.get(group, 0) for group in group_array], np.float64)
        values.append(weighted_macro_f1(y, pred, weights, classes))
    return values


def _metric_record(point: float, draws: Sequence[float | None]) -> dict[str, Any]:
    return {"point": point, "interval": interval(draws), "draws": list(draws)}


def _build_projection_basis(raw_weights: Mapping[str, np.ndarray], cfg: Mapping[str, Any]) -> tuple[np.ndarray | None, dict[str, Any]]:
    tasks = ("relative_quartile", "head_signed_distance", "deprel_coarse", "dependency_depth")
    blocks: list[np.ndarray] = []
    for task in tasks:
        weight = np.asarray(raw_weights[task], np.float64)
        centered = weight-weight.mean(1, keepdims=True)
        norms = np.linalg.norm(centered, axis=0)
        keep = norms > 1e-12
        if not np.any(keep):
            return None, {"status": "not_run", "reason": f"zero_decoder_block:{task}"}
        block = centered[:, keep]/norms[keep]
        block /= math.sqrt(block.shape[1])
        blocks.append(block)
    matrix = np.concatenate(blocks, axis=1)
    u, s, _ = np.linalg.svd(matrix, full_matrices=False)
    rank = int(cfg["probe"]["projection_rank"]); floor = float(cfg["probe"]["projection_singular_floor"])
    if len(s) < rank or s[rank-1] <= floor:
        return None, {"status": "not_run", "reason": "rank_below_16", "singular_values": s.tolist()}
    gap = math.inf if len(s) == rank else float(s[rank-1]-s[rank])
    if gap <= float(cfg["probe"]["projection_gap_relative"])*float(s[0]):
        return None, {"status": "not_run", "reason": "rank_boundary_gap", "singular_values": s.tolist()}
    basis = u[:, :rank]
    for col in range(rank):
        pivot = int(np.argmax(np.abs(basis[:, col])))
        if basis[pivot, col] < 0: basis[:, col] *= -1
    return basis.astype(np.float32), {"status": "eligible", "rank": rank, "gap": gap, "singular_values": s.tolist(), "tasks": list(tasks)}


def _task_evaluation(
    cfg: Mapping[str, Any], task: str, representation: str, arrays: Mapping[str, Mapping[str, np.ndarray]],
    mean: np.ndarray, scale: np.ndarray, device: str,
) -> tuple[dict[str, Any], np.ndarray, np.ndarray]:
    labels, mapping = _label_contract(cfg, task)
    role_rows = {role: _task_data(cfg, role, task) for role in ROLES}
    role_indices = {role: np.asarray([int(row["activation_index"]) for row in rows], np.int64) for role, rows in role_rows.items()}
    role_y = {role: np.asarray([mapping[str(row["label"])] for row in rows], np.int32) for role, rows in role_rows.items()}
    x_discovery = _standardized(arrays["discovery"][representation], role_indices["discovery"], mean, scale)
    x_cal = _standardized(arrays["calibration"][representation], role_indices["calibration"], mean, scale)
    weight, bias, alpha, grid = _fit_ridge(x_discovery, role_y["discovery"], len(labels), cfg["probe"]["alphas"], x_cal, role_y["calibration"], device)
    result: dict[str, Any] = {"labels": labels, "alpha": alpha, "calibration_alpha_grid": grid, "roles": {}}
    c2_pred = np.empty(0, np.int32); c2_y = np.empty(0, np.int32)
    for role in ("calibration", "C1", "C2"):
        x = _standardized(arrays[role][representation], role_indices[role], mean, scale)
        pred = _predict(x, weight, bias); y = role_y[role]
        groups = [str(row["document_group"]) for row in role_rows[role]]
        point = weighted_macro_f1(y, pred, np.ones(len(y)), len(labels))
        sources = {str(row["source"]) for row in role_rows[role]}
        if len(sources) != 1:
            raise RuntimeError(f"task bootstrap requires one frozen source: {role}/{task}")
        draws = _bootstrap_scores(
            y, pred, groups, role=role, source=next(iter(sources)), task=task,
            classes=len(labels), cfg=cfg,
        ) if role in {"C1", "C2"} else []
        result["roles"][role] = {"macro_f1": point, "bootstrap": interval(draws), "draws": draws}
        if role == "C2": c2_pred, c2_y = pred, y
    result["model"] = {"weight_shape": list(weight.shape), "weight_sha256": hashlib.sha256(weight.tobytes()).hexdigest(),
                       "bias_sha256": hashlib.sha256(bias.tobytes()).hexdigest()}
    return result, weight, bias


def _derive_localization(cfg: Mapping[str, Any], evaluations: Mapping[str, Mapping[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    candidates = [row["id"] for row in cfg["checkpoints"] if row["role"] == "candidate"]
    for job in candidates + ["g7"]:
        job_result: dict[str, Any] = {"tasks": {}, "families": {}}
        for task in PRIMARY_TASKS:
            raw = evaluations["raw"][task]
            assigned_name = f"{job}_{'content' if task == 'token_identity_v2' else 'pos'}"
            leak_name = f"{job}_{'pos' if task == 'token_identity_v2' else 'content'}"
            assigned = evaluations[assigned_name][task]; leakage = evaluations[leak_name][task]
            classes = len(raw["labels"]); chance = 1.0/classes
            point_denom = raw["roles"]["C2"]["macro_f1"]-chance
            point_assigned = None if point_denom <= float(cfg["probe"]["raw_denominator_floor"]) else (assigned["roles"]["C2"]["macro_f1"]-chance)/point_denom
            point_leak = None if point_denom <= float(cfg["probe"]["raw_denominator_floor"]) else (leakage["roles"]["C2"]["macro_f1"]-chance)/point_denom
            draws_a: list[float | None] = []; draws_l: list[float | None] = []; draws_s: list[float | None] = []
            for r, a, l in zip(raw["roles"]["C2"]["draws"], assigned["roles"]["C2"]["draws"], leakage["roles"]["C2"]["draws"], strict=True):
                denom = r-chance
                if denom <= float(cfg["probe"]["raw_denominator_floor"]):
                    draws_a.append(None); draws_l.append(None); draws_s.append(None)
                else:
                    ar=(a-chance)/denom; lr=(l-chance)/denom
                    draws_a.append(ar); draws_l.append(lr); draws_s.append(ar-lr)
            a_int=interval(draws_a); l_int=interval(draws_l); s_int=interval(draws_s)
            c1_raw = raw["roles"]["C1"]
            c1_signal = c1_raw["macro_f1"]-chance
            c1_draw_signal = [x-chance for x in c1_raw["draws"]]
            c1_int = interval(c1_draw_signal)
            measurable = c1_signal >= float(cfg["tasks"]["raw_signal_minimum"]) and c1_int["lower"] is not None and c1_int["lower"] > 0
            c1_denom=c1_raw["macro_f1"]-chance
            c1_assigned_point=None if c1_denom<=float(cfg["probe"]["raw_denominator_floor"]) else (assigned["roles"]["C1"]["macro_f1"]-chance)/c1_denom
            c1_leak_point=None if c1_denom<=float(cfg["probe"]["raw_denominator_floor"]) else (leakage["roles"]["C1"]["macro_f1"]-chance)/c1_denom
            c1_a_draws: list[float | None]=[];c1_l_draws: list[float | None]=[];c1_s_draws: list[float | None]=[]
            for r,a,l in zip(raw["roles"]["C1"]["draws"],assigned["roles"]["C1"]["draws"],leakage["roles"]["C1"]["draws"],strict=True):
                denom=r-chance
                if denom<=float(cfg["probe"]["raw_denominator_floor"]):
                    c1_a_draws.append(None);c1_l_draws.append(None);c1_s_draws.append(None)
                else:
                    ar=(a-chance)/denom;lr=(l-chance)/denom
                    c1_a_draws.append(ar);c1_l_draws.append(lr);c1_s_draws.append(ar-lr)
            c1_a_int=interval(c1_a_draws);c1_l_int=interval(c1_l_draws);c1_s_int=interval(c1_s_draws)
            complete = all(
                row["finite"] >= int(cfg["bootstrap"]["minimum_finite"])
                for row in (a_int, l_int, s_int)
            )
            localization_pass = (a_int["finite"] >= int(cfg["bootstrap"]["minimum_finite"])
                                 and a_int["lower"] is not None and a_int["lower"] >= float(cfg["tasks"]["assigned_recovery_lcb"])
                                 and s_int["lower"] is not None and s_int["lower"] > float(cfg["tasks"]["selectivity_lcb"]))
            job_result["tasks"][task] = {
                "chance_convention": chance, "c1_raw_signal": c1_signal, "c1_raw_signal_interval": c1_int,
                "c1_raw_measurable": measurable, "c2_finite_complete": complete,
                "measurement_eligible": measurable and complete,
                "c1_localization_diagnostic":{"assigned_recovery":{"point":c1_assigned_point,"interval":c1_a_int},
                    "leakage":{"point":c1_leak_point,"interval":c1_l_int},
                    "selectivity":{"point":None if c1_assigned_point is None or c1_leak_point is None else c1_assigned_point-c1_leak_point,
                                   "interval":c1_s_int}},
                "assigned_recovery": {"point": point_assigned, "interval": a_int},
                "leakage": {"point": point_leak, "interval": l_int},
                "selectivity": {"point": None if point_assigned is None else point_assigned-point_leak, "interval": s_int},
                "localization_pass": localization_pass,
            }
        structural_tasks = FAMILY_TASKS["broad_structural_context_position"]
        job_result["families"]["broad_structural_context_position"] = {
            "probe_pass": all(job_result["tasks"][task]["localization_pass"] for task in structural_tasks)
        }
        job_result["families"]["lexical_content"] = {"probe_pass": job_result["tasks"]["token_identity_v2"]["localization_pass"]}
        result[job] = job_result
    return result


def _pair_index(cfg: Mapping[str, Any], role: str) -> tuple[list[dict[str, Any]], dict[str, int]]:
    pairs = read_jsonl(root_path(str(cfg["data_root"])) / "prepared" / role / "pairs.jsonl")
    rows = read_jsonl(root_path(str(cfg["data_root"])) / "prepared" / role / "activation_rows.jsonl")
    return pairs, {str(row["row_id"]): int(row["activation_index"]) for row in rows}


def _pair_responses(
    array: np.ndarray, raw: np.ndarray, pairs: Sequence[Mapping[str, Any]],
    index: Mapping[str, int], raw_distance_floor: float,
) -> list[dict[str, Any]]:
    values: list[dict[str, Any]] = []
    for pair in pairs:
        source_idx=[index[x] for x in pair["source_row_ids"]]; target_idx=[index[x] for x in pair["target_row_ids"]]
        source=np.asarray(array[source_idx],np.float32).mean(0); target=np.asarray(array[target_idx],np.float32).mean(0)
        raw_source=np.asarray(raw[source_idx],np.float32).mean(0); raw_target=np.asarray(raw[target_idx],np.float32).mean(0)
        distance=cosine_distance(source,target); raw_distance=cosine_distance(raw_source,raw_target)
        ratio=None if distance is None or raw_distance is None or raw_distance<=raw_distance_floor else distance/raw_distance
        values.append({"pair_id":pair["pair_id"],"group":pair["component_group"],"construct":pair["construct"],
                       "distance":distance,"raw_distance":raw_distance,"ratio":ratio})
    return values


def _weighted_pair_mean(rows: Sequence[Mapping[str, Any]], mult: Mapping[str, int]) -> float | None:
    finite=[row for row in rows if row["ratio"] is not None and math.isfinite(float(row["ratio"]))]
    weights=np.asarray([mult.get(str(row["group"]),0) for row in finite],np.float64)
    if not finite or weights.sum()<=0:return None
    return float(np.average([float(row["ratio"]) for row in finite],weights=weights))


def _cached_noop_qa(array: np.ndarray, pairs: Sequence[Mapping[str, Any]], index: Mapping[str, int]) -> dict[str, Any]:
    checked=0
    for pair in pairs:
        source_idx=[index[x] for x in pair["source_row_ids"]]
        first=np.asarray(array[source_idx],np.float32).mean(0,dtype=np.float32)
        replay=np.asarray(array[source_idx],np.float32).mean(0,dtype=np.float32)
        if not np.array_equal(first,replay):
            return {"status":"ineligible","reason":"cached_noop_not_bit_identical","checked":checked}
        checked+=1
    return {"status":"eligible","bit_identical":True,"distance":0.0,"checked":checked}


def _specificity(cfg: Mapping[str, Any], arrays: Mapping[str, Mapping[str, np.ndarray]]) -> dict[str, Any]:
    role="C2"; pairs,index=_pair_index(cfg,role); raw=arrays[role]["raw"]
    by_construct={name:[p for p in pairs if p["construct"]==name] for name in ("document_context_anchor","entity_substitution")}
    output:dict[str,Any]={}
    for job in [row["id"] for row in cfg["checkpoints"]]:
        responses={branch:{construct:_pair_responses(
                               arrays[role][f"{job}_{branch}"], raw, rows, index,
                               float(cfg["specificity"]["raw_distance_floor"]),
                           )
                           for construct,rows in by_construct.items()} for branch in ("pos","content")}
        noop={branch:{construct:_cached_noop_qa(arrays[role][f"{job}_{branch}"],rows,index)
                      for construct,rows in by_construct.items()} for branch in ("pos","content")}
        constructs={}
        for construct,assigned,other in (("document_context_anchor","pos","content"),("entity_substitution","content","pos")):
            own=responses[assigned][construct]; leak=responses[other][construct]
            control_construct="entity_substitution" if construct=="document_context_anchor" else "document_context_anchor"
            control=responses[assigned][control_construct]
            own_map={r["pair_id"]:r for r in own}; leak_map={r["pair_id"]:r for r in leak}
            finite_ids=[pid for pid in own_map if own_map[pid]["ratio"] is not None and leak_map[pid]["ratio"] is not None]
            paired_own=[own_map[pid] for pid in finite_ids];paired_leak=[leak_map[pid] for pid in finite_ids]
            assigned_finite=[r for r in own if r["ratio"] is not None]
            point_assigned=float(np.mean([r["ratio"] for r in assigned_finite])) if assigned_finite else None
            point_assigned_paired=float(np.mean([own_map[x]["ratio"] for x in finite_ids])) if finite_ids else None
            point_leak=float(np.mean([leak_map[x]["ratio"] for x in finite_ids])) if finite_ids else None
            control_finite=[r for r in control if r["ratio"] is not None]
            point_control=float(np.mean([r["ratio"] for r in control_finite])) if control_finite else None
            branch_draws=[]; control_draws=[]
            own_groups=[r["group"] for r in own]; control_groups=[r["group"] for r in control]
            for draw in range(int(cfg["bootstrap"]["draws"])):
                source = str(cfg["replacement_source"]["id"])
                mult_own=group_multiplicities(own_groups,role=role,task=construct,source=source,draw=draw,seed=int(cfg["seed"]))
                mult_control=group_multiplicities(control_groups,role=role,task=control_construct,source=source,draw=draw,seed=int(cfg["seed"]))
                am_paired=_weighted_pair_mean(paired_own,mult_own);lm=_weighted_pair_mean(paired_leak,mult_own)
                am_control=_weighted_pair_mean(own,mult_own);cm=_weighted_pair_mean(control,mult_control)
                branch_draws.append(None if am_paired is None or lm is None else am_paired-lm)
                control_draws.append(None if am_control is None or cm is None else am_control-cm)
            bint=interval(branch_draws);cint=interval(control_draws)
            finite_fraction=len(finite_ids)/max(1,len(own))
            control_fraction=len(control_finite)/max(1,len(control))
            eligible=(len(finite_ids)>=int(cfg["specificity"]["minimum_finite_pairs"])
                    and finite_fraction>=float(cfg["specificity"]["minimum_finite_fraction"])
                    and len(control_finite)>=int(cfg["specificity"]["minimum_finite_pairs"])
                    and control_fraction>=float(cfg["specificity"]["minimum_finite_fraction"])
                    and bint["finite"]>=int(cfg["bootstrap"]["minimum_finite"])
                    and cint["finite"]>=int(cfg["bootstrap"]["minimum_finite"]))
            noop_pass=noop[assigned][construct]["status"]=="eligible"
            eligible=eligible and noop_pass
            passed=(eligible
                    and bint["lower"] is not None and bint["lower"]>=float(cfg["specificity"]["branch_margin_lcb"])
                    and cint["lower"] is not None and cint["lower"]>float(cfg["specificity"]["control_margin_lcb"]))
            constructs[construct]={"pairs":len(own),"finite_pairs":len(finite_ids),"finite_fraction":finite_fraction,
                "control_pairs":len(control),"finite_control_pairs":len(control_finite),"finite_control_fraction":control_fraction,
                "assigned_response":point_assigned,"paired_assigned_response":point_assigned_paired,
                "leakage_response":point_leak,"cross_family_control_response":point_control,
                "cached_noop":noop[assigned][construct],
                "branch_margin":{"point":None if point_assigned_paired is None or point_leak is None else point_assigned_paired-point_leak,"interval":bint,"draws":branch_draws},
                "control_margin":{"point":None if point_assigned is None else point_assigned-point_control,"interval":cint,"draws":control_draws},
                "eligible":eligible,"passed":passed}
        output[job]={"constructs":constructs,"responses":responses}
    return output


def _nuisance_levels(cfg: Mapping[str, Any]) -> dict[str, list[str]]:
    rows = read_jsonl(root_path(str(cfg["data_root"])) / "prepared/discovery/activation_rows.jsonl")
    fields = ("upos_coarse", "punctuation", "word_length", "token_identity_nuisance")
    main = [row for row in rows if row["kind"] == "main"]
    levels = {
        field: sorted({str(row["labels"][field]) for row in main}, key=lambda x: x.encode())
        for field in fields
    }
    if "__NONRETAINED__" not in levels["token_identity_nuisance"]:
        raise RuntimeError("discovery nuisance contract lacks __NONRETAINED__")
    return levels


def _partial_residuals(
    values: np.ndarray, selected_rows: Sequence[Mapping[str, Any]], metadata: Mapping[int, Mapping[str, Any]],
    levels: Mapping[str, Sequence[str]], maximum_columns: int,
) -> tuple[np.ndarray | None, dict[str, Any]]:
    fields = ("upos_coarse", "punctuation", "word_length", "token_identity_nuisance")
    columns: list[np.ndarray] = [np.ones(len(selected_rows), np.float64)]
    column_names = ["intercept"]
    for field in fields:
        frozen = list(levels[field])
        for level in frozen[1:]:
            encoded = []
            for row in selected_rows:
                value = str(metadata[int(row["activation_index"])]["labels"][field])
                if value not in frozen:
                    if field == "token_identity_nuisance":
                        value = "__NONRETAINED__"
                    else:
                        return None, {"status": "undefined", "reason": f"unknown_nuisance_level:{field}:{value}"}
                encoded.append(float(value == level))
            columns.append(np.asarray(encoded, np.float64)); column_names.append(f"{field}={level}")
    if len(columns) > maximum_columns:
        return None, {"status": "undefined", "reason": "nuisance_columns_above_128", "columns": len(columns)}
    design = np.column_stack(columns)
    rank = int(np.linalg.matrix_rank(design))
    if len(selected_rows) < 2:
        return None, {"status": "undefined", "reason": "fewer_than_two_rows"}
    if len(selected_rows) <= rank + 1:
        return None, {"status": "undefined", "reason": "insufficient_residual_degrees_of_freedom", "rank": rank}
    u, _, _ = np.linalg.svd(design, full_matrices=False)
    q = u[:, :rank]
    x = np.asarray(values, np.float64)
    residual = x - q @ (q.T @ x)
    if not np.isfinite(residual).all() or float(np.linalg.norm(residual)) <= 0:
        return None, {"status": "undefined", "reason": "zero_or_nonfinite_residual_denominator", "rank": rank}
    return residual.astype(np.float32), {
        "status": "eligible", "rank": rank, "columns": len(columns),
        "column_names_sha256": hashlib.sha256("\n".join(column_names).encode()).hexdigest(),
    }


def _pair_delta_matrix(
    array: np.ndarray, raw: np.ndarray, pairs: Sequence[Mapping[str, Any]], index: Mapping[str, int],
    raw_distance_floor: float,
) -> tuple[np.ndarray, list[str]]:
    deltas: list[np.ndarray] = []; pair_ids: list[str] = []
    for pair in pairs:
        source_idx = [index[x] for x in pair["source_row_ids"]]
        target_idx = [index[x] for x in pair["target_row_ids"]]
        raw_source = np.asarray(raw[source_idx], np.float32).mean(0, dtype=np.float32)
        raw_target = np.asarray(raw[target_idx], np.float32).mean(0, dtype=np.float32)
        raw_distance = cosine_distance(raw_source, raw_target)
        if raw_distance is None or raw_distance <= raw_distance_floor:
            continue
        source = np.asarray(array[source_idx], np.float32).mean(0, dtype=np.float32)
        target = np.asarray(array[target_idx], np.float32).mean(0, dtype=np.float32)
        delta = target - source
        if np.isfinite(delta).all():
            deltas.append(delta); pair_ids.append(str(pair["pair_id"]))
    width = int(array.shape[1])
    return (np.stack(deltas).astype(np.float32) if deltas else np.empty((0, width), np.float32)), pair_ids


def _stability(cfg: Mapping[str, Any], arrays: Mapping[str, Mapping[str, np.ndarray]], device: str) -> dict[str, Any]:
    jobs=[row["id"] for row in cfg["checkpoints"]]
    output:dict[str,Any]={"tasks":{},"pairs":{},"counterfactual_deltas":{}}
    role="C2"; rows_meta=read_jsonl(root_path(str(cfg["data_root"])) / "prepared" / role / "activation_rows.jsonl")
    metadata = {int(row["activation_index"]): row for row in rows_meta}
    nuisance_levels = _nuisance_levels(cfg)
    for task in PRIMARY_TASKS:
        rows=select_cka_rows(_task_data(cfg,role,task),int(cfg["stability"]["rows_per_task"]))
        idx=np.asarray([int(r["activation_index"]) for r in rows],np.int64)
        task_meta={"rows":len(idx),"row_ids_sha256":hashlib.sha256("\n".join(str(r["row_id"]) for r in rows).encode()).hexdigest(),
                   "nuisance_levels":nuisance_levels}
        output["tasks"][task]=task_meta
        for i,left in enumerate(jobs):
            for right in jobs[i+1:]:
                key=f"{left}__{right}"; output["pairs"].setdefault(key,{"tasks":{}})
                matrix={}; partial_matrix={}; partial_status={}
                for lb,rb in (("pos","pos"),("content","content"),("pos","content"),("content","pos")):
                    matrix[f"{lb}__{rb}"]=cka_torch(np.asarray(arrays[role][f"{left}_{lb}"][idx],np.float32),
                                                    np.asarray(arrays[role][f"{right}_{rb}"][idx],np.float32),device)
                    lres,lstatus=_partial_residuals(
                        np.asarray(arrays[role][f"{left}_{lb}"][idx],np.float32), rows, metadata,
                        nuisance_levels, int(cfg["stability"]["nuisance_max_columns"]),
                    )
                    rres,rstatus=_partial_residuals(
                        np.asarray(arrays[role][f"{right}_{rb}"][idx],np.float32), rows, metadata,
                        nuisance_levels, int(cfg["stability"]["nuisance_max_columns"]),
                    )
                    cell=f"{lb}__{rb}";partial_status[cell]={"left":lstatus,"right":rstatus}
                    partial_matrix[cell]=None if lres is None or rres is None else cka_torch(lres,rres,device)
                vals=list(matrix.values())
                margin=None if any(v is None for v in vals) else (matrix["pos__pos"]+matrix["content__content"]-matrix["pos__content"]-matrix["content__pos"])/2
                pvals=list(partial_matrix.values())
                pmargin=None if any(v is None for v in pvals) else (partial_matrix["pos__pos"]+partial_matrix["content__content"]-partial_matrix["pos__content"]-partial_matrix["content__pos"])/2
                output["pairs"][key]["tasks"][task]={"matrix":matrix,"identity_margin":margin,
                    "partial_matrix":partial_matrix,"partial_identity_margin":pmargin,"partial_status":partial_status}

    pairs, index = _pair_index(cfg, role); raw = arrays[role]["raw"]
    for construct in ("document_context_anchor", "entity_substitution"):
        frozen_pairs = [row for row in pairs if row["construct"] == construct]
        construct_output: dict[str, Any] = {}
        for i,left in enumerate(jobs):
            for right in jobs[i+1:]:
                key=f"{left}__{right}"; matrix={}; row_hashes={}
                for lb,rb in (("pos","pos"),("content","content"),("pos","content"),("content","pos")):
                    ldelta,lids=_pair_delta_matrix(
                        arrays[role][f"{left}_{lb}"], raw, frozen_pairs, index,
                        float(cfg["specificity"]["raw_distance_floor"]),
                    )
                    rdelta,rids=_pair_delta_matrix(
                        arrays[role][f"{right}_{rb}"], raw, frozen_pairs, index,
                        float(cfg["specificity"]["raw_distance_floor"]),
                    )
                    if lids != rids:
                        raise RuntimeError("counterfactual delta row drift")
                    cell=f"{lb}__{rb}"; matrix[cell]=cka_torch(ldelta,rdelta,device)
                    row_hashes[cell]=hashlib.sha256("\n".join(lids).encode()).hexdigest()
                construct_output[key]={"matrix":matrix,"pair_ids_sha256":row_hashes,
                    "finite_pairs":len(lids),"total_pairs":len(frozen_pairs)}
        output["counterfactual_deltas"][construct]=construct_output
    candidates=[row["id"] for row in cfg["checkpoints"] if row["role"]=="candidate"]
    required_keys={"__".join(sorted((a,b),key=lambda x:int(x[1:]))) for i,a in enumerate(candidates) for b in candidates[i+1:]}
    complete=True; hypothesis=True
    for key in required_keys:
        for task,row in output["pairs"][key]["tasks"].items():
            matrix=row["matrix"]
            if any(v is None for v in matrix.values()) or row["identity_margin"] is None:
                complete=False;hypothesis=False;continue
            hypothesis &= matrix["pos__pos"]>=float(cfg["stability"]["same_branch_minimum"])
            hypothesis &= matrix["content__content"]>=float(cfg["stability"]["same_branch_minimum"])
            hypothesis &= row["identity_margin"]>float(cfg["stability"]["identity_margin_minimum"])
    output["candidate_geometry_complete"]=complete;output["candidate_geometry_passed"]=bool(hypothesis)
    return output


def stage_analyze(cfg: Mapping[str, Any], config_path: Path, device: str) -> dict[str, Any]:
    _configure_torch(cfg)
    verify_prepared(cfg,config_path)
    for spec in cfg["checkpoints"]:_validated_transform(cfg,config_path,str(spec["id"]))
    output=run_root(cfg)/"analysis"
    if (output/"COMPLETE.json").exists():
        complete=read_json(output/"COMPLETE.json")
        verify_file(output/"results.json",complete["results_sha256"])
        verify_file(output/"probe_models.npz",complete["probe_models_sha256"])
        return complete
    if output.exists():raise RuntimeError(f"nonterminal analysis output: {output}")
    tmp=output.parent/f".analysis.{os.getpid()}.tmp";tmp.mkdir(parents=True)
    arrays={role:_representation_arrays(cfg,role) for role in ROLES}
    # Common scaler per representation over the frozen UTF-8 row-ID union.
    discovery_meta=read_jsonl(root_path(str(cfg["data_root"])) / "prepared/discovery/activation_rows.jsonl")
    discovery_index={str(row["row_id"]):int(row["activation_index"]) for row in discovery_meta}
    union_ids=sorted({str(row["row_id"]) for task in ALL_TASKS for row in _task_data(cfg,"discovery",task)},key=lambda x:x.encode())
    union=np.asarray([discovery_index[row_id] for row_id in union_ids],np.int64)
    scalers={rep:_scaler(arr,union,float(cfg["probe"]["zero_scale"])) for rep,arr in arrays["discovery"].items()}
    evaluations:dict[str,dict[str,Any]]={};weights:dict[str,dict[str,np.ndarray]]={}
    biases:dict[str,dict[str,np.ndarray]]={}; model_arrays:dict[str,np.ndarray]={}
    for rep in arrays["discovery"]:
        evaluations[rep]={};weights[rep]={};biases[rep]={}
        mean,scale=scalers[rep]
        model_arrays[f"{rep}__scaler_mean"]=mean;model_arrays[f"{rep}__scaler_scale"]=scale
        for task in ALL_TASKS:
            result,w,b=_task_evaluation(cfg,task,rep,arrays,mean,scale,device)
            evaluations[rep][task]=result;weights[rep][task]=w;biases[rep][task]=b
            model_arrays[f"{rep}__{task}__weight"]=w;model_arrays[f"{rep}__{task}__bias"]=b
    basis,basis_meta=_build_projection_basis(weights["raw"],cfg)
    if basis is not None:
        raw_mean,raw_scale=scalers["raw"]
        for role in ROLES:
            z=(np.asarray(arrays[role]["raw"],np.float32)-raw_mean)/raw_scale
            pos=(z@basis)@basis.T
            arrays[role]["simple_pos"]=pos.astype(np.float32);arrays[role]["simple_content"]=(z-pos).astype(np.float32)
        for rep in ("simple_pos","simple_content"):
            scalers[rep]=_scaler(arrays["discovery"][rep],union,float(cfg["probe"]["zero_scale"]))
            evaluations[rep]={};weights[rep]={};biases[rep]={}
            model_arrays[f"{rep}__scaler_mean"]=scalers[rep][0]
            model_arrays[f"{rep}__scaler_scale"]=scalers[rep][1]
            for task in ALL_TASKS:
                result,w,b=_task_evaluation(cfg,task,rep,arrays,*scalers[rep],device)
                evaluations[rep][task]=result;weights[rep][task]=w;biases[rep][task]=b
                model_arrays[f"{rep}__{task}__weight"]=w;model_arrays[f"{rep}__{task}__bias"]=b
    if basis is not None:
        model_arrays["simple_projection_basis"]=basis
    np.savez_compressed(tmp/"probe_models.npz",**model_arrays)
    model_artifact={"sha256":sha256_file(tmp/"probe_models.npz"),"arrays":{
        key:{"shape":list(value.shape),"dtype":str(value.dtype),"sha256":hashlib.sha256(value.tobytes()).hexdigest()}
        for key,value in sorted(model_arrays.items())}}
    localization=_derive_localization(cfg,evaluations)
    specificity=_specificity(cfg,arrays)
    for job in localization:
        localization[job]["families"]["broad_structural_context_position"]["counterfactual_pass"]=specificity[job]["constructs"]["document_context_anchor"]["passed"]
        localization[job]["families"]["lexical_content"]["counterfactual_pass"]=specificity[job]["constructs"]["entity_substitution"]["passed"]
        localization[job]["selective_k2_posfam_passed"]=all(f["probe_pass"] and f["counterfactual_pass"] for f in localization[job]["families"].values())
    stability=_stability(cfg,arrays,device)
    numerical=cache_manifest(run_root(cfg)/"raw_cache/calibration")["lineage"]["numerical_qa"]
    candidates=[row["id"] for row in cfg["checkpoints"] if row["role"]=="candidate"]
    specificity_complete=all(
        specificity[job]["constructs"][construct]["eligible"]
        for job in candidates for construct in ("document_context_anchor","entity_substitution")
    )
    measurement_eligible=(bool(numerical and numerical["heldout_passed"]) and stability["candidate_geometry_complete"]
                          and specificity_complete
                          and all(all(row["measurement_eligible"] for row in localization[job]["tasks"].values()) for job in candidates))
    if not measurement_eligible: outcome="equivocal"
    elif all(localization[job]["selective_k2_posfam_passed"] for job in candidates) and stability["candidate_geometry_passed"]:
        outcome="K2_broad_position_content_selective_supported"
    else: outcome="K2_broad_position_content_selective_not_supported"
    input_inventory={"raw_cache":{},"transforms":{}}
    for role in ROLES:
        input_inventory["raw_cache"][role]=sha256_file(run_root(cfg)/"raw_cache"/role/"manifest.json")
    for spec in cfg["checkpoints"]:
        complete_path=run_root(cfg)/"transforms"/spec["id"]/"COMPLETE.json"
        input_inventory["transforms"][spec["id"]]=sha256_file(complete_path)
    result={"schema_version":"atlas_measurement_v2_analysis_v1","config_sha256":sha256_file(config_path),
            **_producer_lineage(),
            "strict_absolute_position":{"status":"ineligible","reason":"model_architecture_symmetry"},
            "sentinels":{"source_type":{"status":"ineligible","reason":"not_applicable_single_source"}},
            "optional_collateral_diagnostics":{
                name:{"status":"not_run","reason":"optional_not_scored_in_v2_execution"}
                for name in ("upos_coarse","capitalization","word_length","punctuation")},
            "projection_baseline":basis_meta,"probe_model_artifact":model_artifact,
            "input_inventory":input_inventory,"evaluations":evaluations,"localization":localization,
            "specificity":specificity,"stability":stability,"numerical_qa":numerical,
            "endpoint_eligibility":{"signed_grouping_provenance":"eligible","cache_lineage":"eligible",
                "numerical_qa":"eligible" if numerical and numerical["heldout_passed"] else "ineligible",
                "counterfactual_validity":"eligible" if specificity_complete else "ineligible",
                "geometry_completeness":"eligible" if stability["candidate_geometry_complete"] else "ineligible"},
            "overall_decision_eligibility":"eligible" if measurement_eligible else "ineligible",
            "architecture_outcome":outcome,"environment":runtime_environment(device)}
    atomic_write_json(tmp/"results.json",result)
    complete={"schema_version":"atlas_measurement_v2_analysis_complete_v1","config_sha256":sha256_file(config_path),
              "results_sha256":sha256_file(tmp/"results.json"),
              "probe_models_sha256":sha256_file(tmp/"probe_models.npz"),"architecture_outcome":outcome}
    complete.update(_producer_lineage())
    atomic_write_json(tmp/"COMPLETE.json",complete);os.replace(tmp,output)
    return complete


def _stage_aggregate_locked(cfg: Mapping[str, Any], config_path: Path) -> dict[str, Any]:
    from validate_msae_measurement_v2_terminal import validate_final_report,validate_for_aggregation
    root=run_root(cfg)
    for marker in ("FAILED.json","ABANDONED.json"):
        if (root/marker).exists():raise RuntimeError(f"terminal marker blocks aggregation: {marker}")
    final=root/"final"
    if (root/"COMPLETE.json").exists():
        terminal=read_json(root/"COMPLETE.json")
        verify_file(final/"report.json",terminal["report_sha256"]);verify_file(final/"report.md",terminal["report_md_sha256"])
        verify_file(final/"FINAL.json",terminal["final_manifest_sha256"])
        return terminal
    terminal_validation=validate_for_aggregation(cfg,config_path,root)
    analysis=read_json(root/"analysis/results.json")
    analysis_complete=read_json(root/"analysis/COMPLETE.json")
    verify_file(root/"analysis/results.json",analysis_complete["results_sha256"])
    verify_file(root/"analysis/probe_models.npz",analysis_complete["probe_models_sha256"])
    if analysis["probe_model_artifact"]["sha256"] != analysis_complete["probe_models_sha256"]:
        raise RuntimeError("probe-model artifact lineage drift")
    prepared=verify_prepared(cfg,config_path)
    inputs={"config":sha256_file(config_path),"prepared":sha256_file(root_path(str(cfg["data_root"]))/"prepared/manifest.json")}
    for role in ROLES:
        cache_manifest(root/"raw_cache"/role)
        verify_file(root/"raw_cache"/role/"manifest.json",analysis["input_inventory"]["raw_cache"][role])
    for spec in cfg["checkpoints"]:
        _validated_transform(cfg,config_path,str(spec["id"]))
        verify_file(root/"transforms"/spec["id"]/"COMPLETE.json",analysis["input_inventory"]["transforms"][spec["id"]])
        for role in ROLES:
            for branch in ("pos","content"):cache_manifest(root/"transforms"/spec["id"]/role/branch)
    report={"schema_version":"atlas_measurement_v2_report_v1","run_id":Path(str(cfg["run_root"])).name,
            "claim_scope":cfg["claim_scope"],"inputs":inputs,"data":prepared,"analysis":analysis,
            "terminal_validation":terminal_validation,"final_environment":runtime_environment(),
            "claim_review_status":"not_run_required_before_claim"}
    validate_final_report(report,terminal_validation,cfg)
    if final.exists():
        final_manifest=read_json(final/"FINAL.json")
        if final_manifest.get("config_sha256")!=sha256_file(config_path) or final_manifest.get("analysis_results_sha256")!=sha256_file(root/"analysis/results.json"):
            raise RuntimeError("recovered final-bundle lineage drift")
        verify_file(final/"report.json",final_manifest["report_sha256"])
        verify_file(final/"report.md",final_manifest["report_md_sha256"])
    else:
        tmp=root/f".final.{os.getpid()}.tmp";tmp.mkdir()
        atomic_write_json(tmp/"report.json",report)
        lines=["# Atlas/MSAE measurement v2", "",f"- Eligibility: **{analysis['overall_decision_eligibility']}**",
               f"- Architecture outcome: **{analysis['architecture_outcome']}**",
               "- Strict absolute position: ineligible (GPT-NeoX/RoPE translation symmetry)",
               "- Claim review: not run; no publication claim is authorized", ""]
        (tmp/"report.md").write_text("\n".join(lines),encoding="utf-8")
        final_manifest={"schema_version":"atlas_measurement_v2_final_bundle_v1",
            "config_sha256":sha256_file(config_path),"report_sha256":sha256_file(tmp/"report.json"),
            "report_md_sha256":sha256_file(tmp/"report.md"),
            "analysis_results_sha256":sha256_file(root/"analysis/results.json")}
        atomic_write_json(tmp/"FINAL.json",final_manifest);os.replace(tmp,final)
    terminal={"schema_version":"atlas_measurement_v2_terminal_v1","status":"complete","config_sha256":sha256_file(config_path),
              "report_sha256":sha256_file(final/"report.json"),"report_md_sha256":sha256_file(final/"report.md"),
              "final_manifest_sha256":sha256_file(final/"FINAL.json"),
              "architecture_outcome":analysis["architecture_outcome"],"claim_review_status":"not_run_required_before_claim"}
    atomic_create_json(root/"COMPLETE.json",terminal);return terminal


def stage_aggregate(cfg: Mapping[str, Any], config_path: Path) -> dict[str, Any]:
    root=run_root(cfg);lock_path=root/"terminal.lock"
    fd=os.open(lock_path,os.O_RDWR|os.O_CREAT|os.O_NOFOLLOW,0o600)
    try:
        info=os.fstat(fd)
        if (info.st_mode&0o777)!=0o600 or info.st_uid!=os.getuid():raise RuntimeError("terminal lock ownership/mode drift")
        fcntl.flock(fd,fcntl.LOCK_EX)
        return _stage_aggregate_locked(cfg,config_path)
    finally:
        os.close(fd)


def stage_validate(cfg: Mapping[str, Any], config_path: Path) -> dict[str, Any]:
    for role,spec in cfg["existing_public_records"].items():verify_file(root_path(spec["path"]),spec["sha256"])
    for spec in cfg["checkpoints"]:verify_file(root_path(spec["path"]),spec["sha256"])
    import importlib.metadata as metadata
    locked={}
    for line in (ROOT/"requirements-atlas.lock.txt").read_text().splitlines():
        if line and not line.startswith("#"):
            name,version=line.split("==",1);locked[name]=version
    observed={name:metadata.version(name) for name in locked}
    if observed!=locked:raise RuntimeError(f"installed environment differs from lock: {observed} != {locked}")
    return {"schema_version":"atlas_measurement_v2_validation_v1","config_sha256":sha256_file(config_path),
            "reviewer_trust":cfg["reviewer_trust"],"inputs_valid":True,"environment_lock":observed,
            "environment":runtime_environment()}


def main() -> None:
    parser=argparse.ArgumentParser()
    parser.add_argument("--config",type=Path,required=True)
    parser.add_argument("--stage",required=True,choices=["validate","source-grouping","prepare","extract","transform","analyze","aggregate"])
    parser.add_argument("--role",choices=ROLES);parser.add_argument("--job");parser.add_argument("--device",default="cuda:0")
    parser.add_argument("--batch-size",type=int,default=24)
    args=parser.parse_args();config_path=args.config.resolve(strict=True);cfg=load_config(config_path)
    if args.stage=="validate": result=stage_validate(cfg,config_path)
    elif args.stage=="source-grouping":
        payload=source_grouping(cfg,config_path);envelope=sign_builder_payload(payload)
        path=root_path(cfg["data_root"])/"provenance/builder.json"
        if path.exists():raise RuntimeError("builder provenance is create-once")
        atomic_write_json(path,envelope);result={"path":str(path),"payload_sha256":envelope["payload_sha256"],"payload":payload}
    elif args.stage=="prepare":result=prepare_data(cfg,config_path)
    elif args.stage=="extract":
        if args.role is None:parser.error("--role required for extract")
        result=stage_extract(cfg,config_path,args.role,args.device,args.batch_size)
    elif args.stage=="transform":
        if args.job is None:parser.error("--job required for transform")
        result=stage_transform(cfg,config_path,args.job,args.device,max(256,args.batch_size))
    elif args.stage=="analyze":result=stage_analyze(cfg,config_path,args.device)
    else:result=stage_aggregate(cfg,config_path)
    print(json.dumps(result,indent=2,sort_keys=True),flush=True)


if __name__=="__main__":
    main()
