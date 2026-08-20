#!/usr/bin/env python3
"""Matched raw-cosine random and independently recomputed sham controls."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import pickle
import time
from collections import defaultdict
from pathlib import Path
from typing import Any

import numpy as np
import torch
import torch.nn.functional as F

from msa_completion_common import (EVIDENCE_CLASS, ROOT, atomic_write_json,
                                   attest_completion_freeze_record,
                                   cosine_distance, cosine_matched_direction,
                                   default_firewall, deterministic_seed,
                                   read_json, require_frozen_completion_config,
                                   require_bound_stage_files,
                                   process_resource_accounting,
                                   register_pinned_hf_snapshot,
                                   runtime_environment, sha256_file,
                                   seed_provenance,
                                   terminal_state, write_failure_terminal,
                                   verify_parent_activation,
                                   verify_parent_checkpoint,
                                   verify_parent_freeze_attested,
                                   verify_parent_k2_functional,
                                   verify_parent_raw_calibration,
                                   verify_parent_transform, write_terminal)
from msa_completion_common import (utc_now, verify_attestation_current,
                                   verify_completion_freeze,
                                   validated_cuda_environment)
from merge_msae_refit import threshold_boundary_diagnostic
from train_msae_k2 import K2MSAE


ASSIGNED = {
    "position_shift": "pos",
    "structural_active_passive": "pos",
    "lexical_entity_substitution": "content",
}
OTHER = {"pos": "content", "content": "pos"}
CE_FAMILIES = {"structural_active_passive", "lexical_entity_substitution", "punctuation_format"}
_FAILURE_ATTESTATION: dict[str, Any] = {}


def punctuation_branch_invalid(summary: dict[str, Any], margin: float) -> bool:
    lower = summary.get("lower_95_one_sided")
    return bool((lower is not None and math.isfinite(float(lower)) and float(lower) >= margin)
                or int(summary.get("positive_groups", 0)) >= 3)


def model_representations(h: torch.Tensor, msae: K2MSAE) -> tuple[dict[str, np.ndarray], dict[str, np.ndarray]]:
    with torch.inference_mode():
        out = msae(h.reshape(-1, h.shape[-1]).float())
    raw_tokens = h.float().reshape(-1, h.shape[-1]).detach().cpu().numpy()
    pos_tokens = out["recon_pos"].reshape(-1, h.shape[-1]).detach().cpu().numpy()
    content_tokens = out["recon_content"].reshape(-1, h.shape[-1]).detach().cpu().numpy()
    tokens = {"raw": raw_tokens, "pos": pos_tokens, "content": content_tokens}
    means = {name: values.mean(0) for name, values in tokens.items()}
    means["joint"] = np.concatenate([means["pos"], means["content"]])
    means["resid"] = means["raw"] - means["pos"] - means["content"]
    return means, tokens


def cached_representations(raw: np.ndarray, pos: np.ndarray, content: np.ndarray, indices: np.ndarray) -> tuple[dict[str, np.ndarray], dict[str, np.ndarray]]:
    tokens = {"raw": np.asarray(raw[indices], np.float32), "pos": np.asarray(pos[indices], np.float32),
              "content": np.asarray(content[indices], np.float32)}
    means = {name: values.mean(0) for name, values in tokens.items()}
    means["joint"] = np.concatenate([means["pos"], means["content"]])
    means["resid"] = means["raw"] - means["pos"] - means["content"]
    return means, tokens


def distances(a: dict[str, np.ndarray], b: dict[str, np.ndarray]) -> dict[str, float]:
    return {rep: cosine_distance(a[rep], b[rep]) for rep in a}


def specificity_invariants_finite(*mappings: dict[str, Any], scalars: list[float] | None = None) -> bool:
    values = [float(value) for mapping in mappings for value in mapping.values()]
    values.extend(map(float, scalars or []))
    return bool(values and np.isfinite(values).all())


def specificity_boundary_diagnostic(draws: list[float], lower: float | None,
                                    margin: float, tolerance: float) -> dict[str, Any]:
    endpoint_range = None
    if len(draws) == 500 and np.isfinite(draws).all():
        endpoints = []
        values = np.asarray(draws, dtype=np.float64)
        for block in range(5):
            retained = np.delete(values, np.s_[block * 100:(block + 1) * 100])
            endpoints.append(float(np.quantile(retained, 0.05)))
        endpoint_range = float(np.ptp(endpoints))
    distance = None if lower is None or not math.isfinite(float(lower)) else abs(float(lower) - margin)
    proximity = bool(distance is not None and distance <= tolerance)
    return {"threshold": margin, "distance": distance,
            "tolerance": tolerance, "boundary_proximity": proximity,
            "mc_100_block_endpoint_range": endpoint_range,
            "mc_underpowered_at_boundary": bool(
                proximity and endpoint_range is not None and endpoint_range > tolerance)}


def safe_normalized(row: dict[str, Any], branch: str, control: str) -> float | None:
    denominator = row["actual"]["raw"]
    value = row[control][branch]
    if denominator < row["raw_distance_floor"] or not np.isfinite([denominator, value]).all():
        return None
    return float(value / denominator)


def frozen_specificity_group_samples(groups: list[str], *, draws: int,
                                     seed: int, job_id: str,
                                     family: str) -> list[list[str]]:
    """Return the one frozen job/family template-group bootstrap map."""

    ordered = sorted(groups)
    if len(ordered) != 4 or len(set(ordered)) != 4:
        raise ValueError("specificity bootstrap requires exactly four groups")
    rng = np.random.Generator(np.random.PCG64(
        deterministic_seed(seed, "specificity", f"{job_id}:{family}", 0)))
    return [rng.choice(ordered, size=4, replace=True).tolist()
            for _ in range(draws)]


def registered_matched_random_seed(base_seed: int, transform_id: str,
                                   token_index: int | None = None) -> int:
    if token_index is None:
        return deterministic_seed(base_seed, "matched_random", transform_id, 0)
    return deterministic_seed(base_seed, "matched_random_token", transform_id,
                              token_index)


def group_summary(rows: list[dict[str, Any]], family: str, branch: str, config: dict[str, Any],
                  job_id: str, *, token: bool = False) -> dict[str, Any]:
    key = "token_aligned" if token else "sentence"
    family_rows = [row for row in rows if row["family"] == family
                   and (not token or bool(row.get("token_aligned_parent")))]
    valid = [row for row in family_rows if row[key].get("valid")]
    by_group: dict[str, list[float]] = defaultdict(list)
    mapping_by_group: dict[str, list[float]] = defaultdict(list)
    for row in valid:
        result = row[key]
        by_group[row["template_group"]].append(result["specificity"][branch])
        if family != "punctuation_format":
            mapping_by_group[row["template_group"]].append(result["actual_normalized"][branch] - result["actual_normalized"][OTHER[branch]])
    group_means = {group: float(np.mean(values)) for group, values in sorted(by_group.items())}
    mapping_means = {group: float(np.mean(values)) for group, values in sorted(mapping_by_group.items())}
    required_rows = 16 if token else 24
    expected_rows = len(family_rows)
    complete = len(valid) >= required_rows and len(group_means) == 4
    draws = []
    if complete:
        groups = sorted(group_means)
        for sampled in frozen_specificity_group_samples(
                groups, draws=int(config["draws"]), seed=int(config["seed"]),
                job_id=job_id, family=family):
            draws.append(float(np.mean([group_means[group] for group in sampled])))
    point = float(np.mean(list(group_means.values()))) if complete else None
    lower = float(np.quantile(draws, 0.05)) if draws else None
    mapping_groups = sum(value >= float(config["specificity_margin"]) for value in mapping_means.values())
    positive_groups = sum(value > 0 for value in group_means.values())
    point_only_reason = (
        "per-template-group specificity is a fixed point endpoint; "
        "no registered draw-level endpoint series exists")
    group_boundary = {
        "specificity_positive": {
            group: threshold_boundary_diagnostic(
                value, 0.0, tolerance=float(config["boundary_tolerance"]),
                mc_not_applicable_reason=point_only_reason)
            for group, value in group_means.items()
        },
        "mapping_margin": {
            group: threshold_boundary_diagnostic(
                value, float(config["specificity_margin"]),
                tolerance=float(config["boundary_tolerance"]),
                mc_not_applicable_reason=point_only_reason)
            for group, value in mapping_means.items()
        },
    }
    group_boundary_clear = all(
        not diagnostic["boundary_proximity"]
        for diagnostics in group_boundary.values()
        for diagnostic in diagnostics.values())
    boundary = specificity_boundary_diagnostic(
        draws, lower, float(config["specificity_margin"]),
        float(config["boundary_tolerance"]))
    return {"valid": complete, "n_rows": len(valid), "expected_rows": expected_rows,
            "invalid_transform_ids": [row["transform_id"] for row in family_rows if not row[key].get("valid")],
            "group_means": group_means, "mapping_group_means": mapping_means,
            "point": point, "lower_95_one_sided": lower, "positive_groups": positive_groups,
            "mapping_margin_groups": mapping_groups, "draws": draws,
            "boundary_diagnostic": boundary,
            "group_boundary_diagnostics": group_boundary,
            "lower_margin_pass": bool(complete and lower is not None and lower >= float(config["specificity_margin"])),
            "passes": bool(complete and lower is not None and lower >= float(config["specificity_margin"])
                           and not boundary["boundary_proximity"]
                           and group_boundary_clear
                           and positive_groups >= 3 and (family == "punctuation_format" or mapping_groups >= 3))}


def aggregate_ce_collateral(ce_rows: list[dict[str, Any]],
                            transforms: list[dict[str, Any]]) -> tuple[float, dict[str, list[float]], dict[str, list[float]]]:
    """Apply the frozen side→transform→group→family CE aggregation."""

    transform_meta = {row["transform_id"]: row for row in transforms}
    ce_by_transform: dict[str, dict[str, float]] = defaultdict(dict)
    for row in ce_rows:
        raw_ce, recon_ce = float(row["ce"]["raw"]), float(row["ce"]["k2_reconstruction"])
        if raw_ce <= 0 or not np.isfinite([raw_ce, recon_ce]).all():
            raise RuntimeError("invalid frozen CE collateral row")
        transform_id, side = row["transform_id"], row.get("side")
        if transform_id not in transform_meta or side not in {"source_words", "target_words"} or side in ce_by_transform[transform_id]:
            raise RuntimeError("CE side identity/duplication failure")
        ce_by_transform[transform_id][side] = (recon_ce - raw_ce) / raw_ce
    if (any(set(values) != {"source_words", "target_words"} for values in ce_by_transform.values())
            or len(ce_by_transform) != 96):
        raise RuntimeError("CE transform/side completeness failure")
    ce_groups: dict[str, list[float]] = defaultdict(list)
    for transform_id, values in ce_by_transform.items():
        meta_row = transform_meta[transform_id]
        ce_groups[f"{meta_row['family']}::{meta_row['template_group']}"].append(float(np.mean(list(values.values()))))
    expected_families = sorted({transform_meta[transform_id]["family"] for transform_id in ce_by_transform})
    if set(expected_families) != CE_FAMILIES:
        raise RuntimeError(f"CE family identity failure: {expected_families}")
    for family in expected_families:
        keys = sorted(key for key in ce_groups if key.startswith(family + "::"))
        if len(keys) != 4 or any(len(ce_groups[key]) != 8 for key in keys):
            raise RuntimeError(f"CE group/transform completeness failure: {family}")
    ce_family: dict[str, list[float]] = defaultdict(list)
    for key, values in ce_groups.items():
        family, _ = key.split("::", 1)
        ce_family[family].append(float(np.mean(values)))
    if sorted(ce_family) != expected_families or any(len(values) != 4 for values in ce_family.values()):
        raise RuntimeError("CE family completeness failure")
    point = float(np.mean([np.mean(values) for values in ce_family.values()]))
    return point, dict(ce_groups), dict(ce_family)


def main() -> None:
    global _FAILURE_ATTESTATION
    parser = argparse.ArgumentParser()
    parser.add_argument("--job", required=True)
    parser.add_argument("--device", default="cuda:0")
    parser.add_argument("--config", type=Path, default=ROOT / "configs/atlas_completion/analysis.json")
    args = parser.parse_args()
    completion_freeze = require_frozen_completion_config(args.config)
    config = read_json(args.config)
    if args.job not in config["primary_checkpoints"] + config["descriptive_checkpoints"]:
        raise ValueError("unregistered checkpoint")
    source_root, run_root = ROOT / config["source_run_root"], ROOT / config["run_root"]
    stage = run_root / "specificity" / args.job
    stage.mkdir(parents=True, exist_ok=True)
    if any(stage.iterdir()) or terminal_state(stage) is not None:
        raise RuntimeError(f"specificity is create-once: {stage}")
    started = time.monotonic()
    started_utc = utc_now()
    firewall = default_firewall(source_root, run_root)
    _FAILURE_ATTESTATION = firewall.attestation
    attest_completion_freeze_record(firewall, completion_freeze)
    launch_environment = validated_cuda_environment(args.device)
    firewall.register_root(ROOT / "data/atlas_completion_v1")
    config_path = firewall.attest(args.config)
    token_manifest = read_json(firewall.attest(ROOT / "data/atlas_completion_v1/token_control_manifest.json"))
    token_map = {row["transform_id"]: row for row in token_manifest["rows"]}
    snapshot = register_pinned_hf_snapshot(firewall, token_manifest)

    device = torch.device(args.device)
    if device.type != "cuda" or not torch.cuda.is_available():
        raise RuntimeError("specificity requires CUDA")
    from transformers import AutoModelForCausalLM, AutoTokenizer

    tokenizer = AutoTokenizer.from_pretrained(snapshot, local_files_only=True, use_fast=True)
    lm = AutoModelForCausalLM.from_pretrained(snapshot, local_files_only=True, torch_dtype=torch.float16).to(device).eval()
    parent_freeze = verify_parent_freeze_attested(
        firewall, ["discovery", "calibration", "C2"])
    if parent_freeze["bundle_sha256"] != config["parent_bundle_sha256"]:
        raise RuntimeError("parent bundle mismatch")
    spec = verify_parent_checkpoint(args.job, firewall)
    verify_parent_transform(source_root, args.job, firewall)
    checkpoint_path = Path(spec["path"])
    firewall.register_file(checkpoint_path)
    firewall.attest(checkpoint_path)
    checkpoint = torch.load(checkpoint_path, map_location="cpu", weights_only=False)
    train_args = checkpoint["args"]
    msae = K2MSAE(768, int(train_args["m_pos"]), int(train_args["k_pos"]), int(train_args["m_content"]), int(train_args["k_content"]))
    msae.load_state_dict(checkpoint["model"])
    msae = msae.to(device).eval()
    require_bound_stage_files(
        run_root / "baseline", firewall, config_sha256=sha256_file(config_path),
        completion_bundle_sha256=completion_freeze["bundle_sha256"],
        expected_files={"result_sha256": "baseline.json",
                        "bundle_sha256": "baseline_bundle.pkl"})
    with firewall.attest(run_root / "baseline/baseline_bundle.pkl").open("rb") as handle:
        baseline = pickle.load(handle)
    if baseline.get("completion_bundle_sha256") != completion_freeze["bundle_sha256"]:
        raise RuntimeError("baseline bundle is not bound to the completion freeze")
    verify_parent_raw_calibration(source_root, firewall)
    with firewall.attest(ROOT / "results/atlas/raw_v1/L3_calibration_bundle.pkl").open("rb") as handle:
        raw_bundle = pickle.load(handle)
    candidate = baseline["selected_simple_baseline"]
    basis_name = {"projection_broad16": "broad_position", "projection_split8_8": "split_position_joint",
                  "pca16_complement": "pca16"}[candidate]
    simple_mean = torch.as_tensor(raw_bundle["mean"], dtype=torch.float32, device=device)
    simple_scale = torch.as_tensor(raw_bundle["scale"], dtype=torch.float32, device=device)
    simple_basis = torch.as_tensor(raw_bundle["bases"][basis_name], dtype=torch.float32, device=device)

    transforms_path = firewall.attest(ROOT / "data/atlas_v1/transforms/C2.jsonl", role="C2")
    transforms = [json.loads(line) for line in transforms_path.read_text().splitlines()]
    transform_ids = [row["transform_id"] for row in transforms]
    if len(transforms) != 128 or len(set(transform_ids)) != 128:
        raise RuntimeError("frozen C2 transform count/ID uniqueness failure")
    parent_path = firewall.attest(ROOT / f"results/atlas/k2_v1/{args.job}_functional.json")
    parent = verify_parent_k2_functional(source_root, args.job, firewall)
    parent_rows = {row["transform_id"]: row for row in parent["counterfactual_rows"]}
    if set(parent_rows) != set(transform_ids):
        raise RuntimeError("parent/new counterfactual transform ID mismatch")
    verify_parent_activation(source_root, "C2", firewall)
    raw_arr = np.load(firewall.attest(source_root / "raw_activations/C2/L3.float16.npy", role="C2"), mmap_mode="r")
    pos_arr = np.load(firewall.attest(source_root / f"k2_transforms/{args.job}/C2/pos.float16.npy", role="C2"), mmap_mode="r")
    content_arr = np.load(firewall.attest(source_root / f"k2_transforms/{args.job}/C2/content.float16.npy", role="C2"), mmap_mode="r")
    with np.load(firewall.attest(source_root / "raw_activations/C2/row_meta.npz", role="C2")) as loaded:
        meta = {key: loaded[key] for key in loaded.files}
    records = [json.loads(line) for line in firewall.attest(source_root / "raw_activations/C2/records.jsonl", role="C2").read_text().splitlines()]
    base_to_record = {row["base_id"]: i for i, row in enumerate(records)}
    units = [json.loads(line) for line in firewall.attest(ROOT / "data/atlas_v1/partitions/C2.units.jsonl", role="C2").read_text().splitlines()]
    unit_map = {(row["base_id"], int(row["offset"])): row for row in units}

    def forward_ids(ids: list[int]) -> torch.Tensor:
        tensor = torch.tensor([ids], dtype=torch.long, device=device)
        with torch.inference_mode():
            return lm(tensor, output_hidden_states=True, use_cache=False).hidden_states[4]

    rows_out = []
    max_parent_error = 0.0
    for transform in transforms:
        if transform["family"] == "position_shift":
            record_index = base_to_record[transform["base_id"]]
            source_idx = np.flatnonzero((meta["record_index"] == record_index) & (meta["offset"] == int(transform["source_offset"])))
            target_idx = np.flatnonzero((meta["record_index"] == record_index) & (meta["offset"] == int(transform["target_offset"])))
            source_means, source_tokens = cached_representations(raw_arr, pos_arr, content_arr, source_idx)
            target_means, target_tokens = cached_representations(raw_arr, pos_arr, content_arr, target_idx)
            source_ids = unit_map[(transform["base_id"], int(transform["source_offset"]))]["input_ids"]
            sham_h = forward_ids(source_ids)
        else:
            source_enc = tokenizer(transform["source_words"], is_split_into_words=True, add_special_tokens=False)
            target_enc = tokenizer(transform["target_words"], is_split_into_words=True, add_special_tokens=False)
            source_h = forward_ids(list(map(int, source_enc["input_ids"])))
            target_h = forward_ids(list(map(int, target_enc["input_ids"])))
            source_means, source_tokens = model_representations(source_h, msae)
            target_means, target_tokens = model_representations(target_h, msae)
            sham_h = forward_ids(list(map(int, source_enc["input_ids"])))
        sham_means, sham_tokens = model_representations(sham_h, msae)
        actual = distances(source_means, target_means)
        parent_dist = parent_rows[transform["transform_id"]]["distances"]
        parent_error = max(abs(actual[rep] - float(parent_dist[rep])) for rep in parent_dist)
        max_parent_error = max(max_parent_error, parent_error)

        sham_dist = distances(source_means, sham_means)
        random_delta = None
        random_qa: dict[str, Any] = {}
        random_dist: dict[str, float] | None = None
        random_raw_error: float | None = None
        sentence_error = None
        matched_random_seed = registered_matched_random_seed(
            config["seed"], transform["transform_id"])
        try:
            random_delta, random_qa = cosine_matched_direction(
                source_means["raw"], target_means["raw"],
                seed=matched_random_seed,
            )
            random_h = torch.as_tensor(source_tokens["raw"] + random_delta[None, :], dtype=torch.float32, device=device)[None, :, :]
            random_means, _ = model_representations(random_h, msae)
            random_dist = distances(source_means, random_means)
            random_raw_error = abs(random_dist["raw"] - actual["raw"])
            sentence_valid = (specificity_invariants_finite(
                                  actual, random_dist, sham_dist, random_qa,
                                  scalars=[parent_error, random_raw_error])
                              and actual["raw"] >= float(config["specificity_raw_distance_floor"])
                              and parent_error <= 1e-6
                              and random_raw_error <= float(config["orthogonality_tolerance"])
                              and random_qa["distance_error"] <= float(config["orthogonality_tolerance"])
                              and random_qa["absolute_cosine_actual_delta"] <= float(config["orthogonality_tolerance"])
                              and random_qa["absolute_cosine_source"] <= float(config["orthogonality_tolerance"])
                              and max(sham_dist[rep] for rep in ["raw", "pos", "content"]) <= float(config["sham_distance_ceiling"]))
        except (FloatingPointError, RuntimeError, ValueError) as exc:
            sentence_valid = False
            sentence_error = f"{type(exc).__name__}:{exc}"
            random_qa = {"error": sentence_error}
        sentence: dict[str, Any] = {"valid": sentence_valid, "reason": sentence_error,
                                    "actual_normalized": {}, "random_normalized": {},
                                    "sham_normalized": {}, "specificity": {}}
        if sentence_valid:
            for branch in ["pos", "content"]:
                sentence["actual_normalized"][branch] = actual[branch] / actual["raw"]
                sentence["random_normalized"][branch] = random_dist[branch] / actual["raw"]
                sentence["sham_normalized"][branch] = sham_dist[branch] / actual["raw"]
                sentence["specificity"][branch] = sentence["actual_normalized"][branch] - max(sentence["random_normalized"][branch], sentence["sham_normalized"][branch])

        token_result: dict[str, Any] = {"valid": False, "reason": "not_frozen_token_aligned"}
        if transform["transform_id"] in token_map:
            token_specs = token_map[transform["transform_id"]]["designated_token_positions"]
            token_rows = []
            for token_index in token_specs:
                source_raw, target_raw = source_tokens["raw"][token_index], target_tokens["raw"][token_index]
                matched_random_token_seed = registered_matched_random_seed(
                    config["seed"], transform["transform_id"], token_index)
                try:
                    delta, qa = cosine_matched_direction(source_raw, target_raw,
                        seed=matched_random_token_seed)
                    random_token_h = torch.as_tensor(source_raw + delta, dtype=torch.float32, device=device)[None, None, :]
                    random_token_means, _ = model_representations(random_token_h, msae)
                    actual_token = {rep: cosine_distance(source_tokens[rep][token_index], target_tokens[rep][token_index]) for rep in ["raw", "pos", "content"]}
                    random_token = {rep: cosine_distance(source_tokens[rep][token_index], random_token_means[rep]) for rep in ["raw", "pos", "content"]}
                    sham_token = {rep: cosine_distance(source_tokens[rep][token_index], sham_tokens[rep][token_index]) for rep in ["raw", "pos", "content"]}
                    random_token_raw_error = abs(random_token["raw"] - actual_token["raw"])
                    token_valid = bool(
                        specificity_invariants_finite(
                            actual_token, random_token, sham_token, qa,
                            scalars=[random_token_raw_error])
                        and actual_token["raw"] >= float(config["specificity_raw_distance_floor"])
                        and random_token_raw_error <= float(config["orthogonality_tolerance"])
                        and qa["distance_error"] <= float(config["orthogonality_tolerance"])
                        and qa["absolute_cosine_actual_delta"] <= float(config["orthogonality_tolerance"])
                        and qa["absolute_cosine_source"] <= float(config["orthogonality_tolerance"])
                        and max(sham_token.values()) <= float(config["sham_distance_ceiling"]))
                    normalized = {kind: {branch: values[branch] / actual_token["raw"] for branch in ["pos", "content"]}
                                  for kind, values in [("actual", actual_token), ("random", random_token), ("sham", sham_token)]}
                    token_rows.append({"token_index": token_index,
                                       "valid": token_valid,
                                       "reason": (None if token_valid else
                                                  "token_control_invariant_failure"),
                                       "qa": qa,
                                       "matched_random_token_seed": matched_random_token_seed,
                                       "computed_random_raw_distance_error": random_token_raw_error,
                                       "actual": actual_token,
                                       "random": random_token,
                                       "sham": sham_token,
                                       "normalized": normalized,
                                       "specificity": {branch: normalized["actual"][branch] - max(normalized["random"][branch], normalized["sham"][branch]) for branch in ["pos", "content"]},
                                       "direction_sha256": hashlib.sha256(delta.tobytes()).hexdigest()})
                except Exception as exc:
                    token_rows.append({
                        "token_index": token_index, "valid": False,
                        "reason": f"{type(exc).__name__}:{exc}",
                        "matched_random_token_seed": matched_random_token_seed,
                    })
            valid = (len(token_rows) == len(token_specs)
                     and all(row["valid"] for row in token_rows))
            if valid:
                token_result = {"valid": True, "n_tokens": len(token_rows), "tokens": token_rows,
                                "actual_normalized": {branch: float(np.mean([r["normalized"]["actual"][branch] for r in token_rows])) for branch in ["pos", "content"]},
                                "specificity": {branch: float(np.mean([r["specificity"][branch] for r in token_rows])) for branch in ["pos", "content"]}}
            else:
                token_result = {
                    "valid": False, "reason": "one_or_more_token_controls_invalid",
                    "tokens": token_rows,
                    "evaluated_tokens": len(token_rows),
                    "valid_tokens": sum(row["valid"] for row in token_rows),
                    "required_tokens": len(token_specs),
                    "invalid_token_indices": [row["token_index"] for row in token_rows
                                              if not row["valid"]],
                }
        rows_out.append({"transform_id": transform["transform_id"], "family": transform["family"],
                         "template_group": transform["template_group"], "token_aligned_parent": transform.get("token_aligned"),
                         "actual": actual, "random": random_dist, "sham": sham_dist, "random_qa": random_qa,
                         "computed_random_raw_distance_error": random_raw_error,
                         "matched_random_seed": matched_random_seed,
                         "random_direction_sha256": (None if random_delta is None else
                                                     hashlib.sha256(random_delta.tobytes()).hexdigest()),
                         "raw_distance_floor": float(config["specificity_raw_distance_floor"]),
                         "parent_actual_max_abs_error": parent_error, "sentence": sentence, "token_aligned": token_result})

    summaries: dict[str, Any] = {}
    for family in sorted({row["family"] for row in rows_out}):
        if family == "punctuation_format":
            summaries[family] = {branch: group_summary(rows_out, family, branch, config, args.job)
                                 for branch in ["pos", "content"]}
        else:
            branch = ASSIGNED[family]
            summaries[family] = {"sentence": group_summary(rows_out, family, branch, config, args.job),
                                 "assigned_branch": branch}
            if family == "lexical_entity_substitution":
                summaries[family]["token_aligned"] = group_summary(rows_out, family, branch, config, args.job, token=True)

    # Exact frozen reconstruction collateral, aggregated sides -> transform -> group -> family.
    ce_point, ce_groups, ce_family = aggregate_ce_collateral(parent["ce_rows"], transforms)

    # A literal position-projection-plus-complement identity hook must reproduce
    # every frozen raw suffix CE row before simple CE damage is treated as zero.
    parent_ce = {(row["transform_id"], row["side"]): float(row["ce"]["raw"]) for row in parent["ce_rows"]}

    def suffix_ce(ids: torch.Tensor, *, identity_projection: bool) -> float:
        handle = None
        if identity_projection:
            def hook(_module: Any, _inputs: Any, output: Any) -> Any:
                hidden = output[0] if isinstance(output, tuple) else output
                flat = hidden.reshape(-1, hidden.shape[-1]).float()
                standardized = (flat - simple_mean) / simple_scale
                projected = (standardized @ simple_basis) @ simple_basis.T
                reconstructed = (projected + (standardized - projected)) * simple_scale + simple_mean
                replacement = reconstructed.reshape_as(hidden).to(hidden.dtype)
                return (replacement,) + output[1:] if isinstance(output, tuple) else replacement

            handle = lm.gpt_neox.layers[3].register_forward_hook(hook)
        try:
            with torch.inference_mode():
                logits = lm(ids, use_cache=False).logits
        finally:
            if handle is not None:
                handle.remove()
        if ids.shape[1] < 2:
            return float("nan")
        loss = F.cross_entropy(logits[:, :-1].float().reshape(-1, logits.shape[-1]),
                               ids[:, 1:].reshape(-1), reduction="mean")
        return float(loss.item())

    identity_rows = []
    max_parent_raw_ce_error = 0.0
    max_identity_ce_error = 0.0
    for transform in transforms:
        if "source_words" not in transform:
            continue
        for side in ["source_words", "target_words"]:
            ids = tokenizer(transform[side], is_split_into_words=True, add_special_tokens=False,
                            return_tensors="pt")["input_ids"].to(device)
            raw_ce = suffix_ce(ids, identity_projection=False)
            identity_ce = suffix_ce(ids, identity_projection=True)
            parent_error = abs(raw_ce - parent_ce[(transform["transform_id"], side)])
            identity_error = abs(identity_ce - raw_ce)
            max_parent_raw_ce_error = max(max_parent_raw_ce_error, parent_error)
            max_identity_ce_error = max(max_identity_ce_error, identity_error)
            identity_rows.append({"transform_id": transform["transform_id"], "side": side,
                                  "raw_ce": raw_ce, "identity_ce": identity_ce,
                                  "parent_raw_ce": parent_ce[(transform["transform_id"], side)],
                                  "parent_raw_abs_error": parent_error,
                                  "identity_abs_error": identity_error})
    identity_valid = bool(len(identity_rows) == 192 and max_parent_raw_ce_error <= 1e-5
                          and max_identity_ce_error <= 1e-5)
    ce_draws = []
    for draw in range(int(config["draws"])):
        family_values = []
        rng = np.random.Generator(np.random.PCG64(
            deterministic_seed(config["seed"], "ce_collateral", draw, 0)))
        for family in sorted(ce_family):
            keys = sorted(key for key in ce_groups if key.startswith(family + "::"))
            sampled = rng.choice(keys, size=len(keys), replace=True)
            family_values.append(float(np.mean([np.mean(ce_groups[key]) for key in sampled])))
        ce_draws.append(float(np.mean(family_values)))

    required = ["position_shift", "structural_active_passive", "lexical_entity_substitution"]
    mapping_valid = all(summaries[f]["sentence"]["passes"] for f in required)
    lexical_token_valid = summaries["lexical_entity_substitution"]["token_aligned"]["passes"]
    punctuation_invalid = any(punctuation_branch_invalid(summaries["punctuation_format"][branch],
                                                         float(config["specificity_margin"]))
                              for branch in ["pos", "content"])
    punctuation_technical_valid = all(
        summaries["punctuation_format"][branch]["valid"]
        and not summaries["punctuation_format"][branch]["boundary_diagnostic"]["boundary_proximity"]
        and all(
            not diagnostic["boundary_proximity"]
            for diagnostics in summaries["punctuation_format"][branch][
                "group_boundary_diagnostics"].values()
            for diagnostic in diagnostics.values())
        for branch in ["pos", "content"])
    gate_valid = bool(max_parent_error <= 1e-6 and mapping_valid and lexical_token_valid
                      and punctuation_technical_valid and not punctuation_invalid)
    elapsed_sec = time.monotonic() - started
    result = {"schema_version": "atlas_completion_specificity_v1", "evidence_class": EVIDENCE_CLASS,
              "job_id": args.job, "rows": rows_out, "summaries": summaries,
              "max_parent_actual_abs_error": max_parent_error, "counterfactual_gate_valid": gate_valid,
              "counterfactual_gate_reasons": {"sentence_mapping_valid": mapping_valid, "lexical_token_valid": lexical_token_valid,
                                               "punctuation_sentinel_valid": not punctuation_invalid,
                                               "punctuation_technical_valid": punctuation_technical_valid},
              "ce_collateral": {"point": ce_point, "draws": ce_draws,
                                "groups": dict(ce_groups),
                                "families": dict(ce_family),
                                "transform_side_rows": parent["ce_rows"]},
              "simple_identity_collateral": {"valid": identity_valid, "candidate": candidate,
                                                "rows": identity_rows,
                                                "max_parent_raw_ce_abs_error": max_parent_raw_ce_error,
                                                "max_identity_ce_abs_error": max_identity_ce_error},
              "checkpoint_sha256": spec["sha256"], "parent_functional_sha256": sha256_file(parent_path),
              "config_sha256": sha256_file(config_path), "elapsed_sec": elapsed_sec,
              "resolved_config": config,
              "resolved_arguments": {"job": args.job, "device": args.device},
              "seed_provenance": seed_provenance(
                  config,
                  contract=("matched-random leaves bind registered_matched_random_seed; "
                            "specificity bootstrap and CE collateral bind deterministic_seed")),
              "device": args.device, "started_utc": started_utc,
              "ended_utc": utc_now(),
              "completion_bundle_sha256": completion_freeze["bundle_sha256"],
              "environment": launch_environment, "input_attestation": firewall.attestation,
              "limitations": ["representation-distance specificity is noncausal", "random directions may be off manifold"]}
    result_path = stage / "specificity.json"
    atomic_write_json(result_path, result)
    parent_after = verify_parent_freeze_attested(
        firewall, ["discovery", "calibration", "C2"])
    extension_after = verify_completion_freeze()
    verify_attestation_current(firewall.attestation)
    elapsed_sec = time.monotonic() - started
    write_terminal(stage, complete=True, payload={"schema_version": "atlas_completion_specificity_complete_v1",
                                                   "job_id": args.job, "result_sha256": sha256_file(result_path),
                                                   "config_sha256": sha256_file(config_path),
                                                   "resolved_config": config,
                                                   "resolved_arguments": {"job": args.job,
                                                                          "device": args.device},
                                                   "seed_provenance": result["seed_provenance"],
                                                   "device": args.device,
                                                   "started_utc": started_utc,
                                                   "environment": launch_environment,
                                                   "resource_accounting": process_resource_accounting(
                                                       stage, elapsed_sec=elapsed_sec,
                                                       device=args.device),
                                                   "completion_bundle_sha256": completion_freeze["bundle_sha256"],
                                                   "counterfactual_gate_valid": gate_valid,
                                                   "parent_bundle_reverified_after_stage_sha256": parent_after["bundle_sha256"],
                                                   "completion_bundle_reverified_after_stage_sha256": extension_after["bundle_sha256"],
                                                   "input_attestation": firewall.attestation})
    print(json.dumps({"job": args.job, "rows": len(rows_out), "gate_valid": gate_valid,
                      "max_parent_error": max_parent_error, "elapsed_sec": time.monotonic() - started}, indent=2))


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        argv = __import__("sys").argv
        job = argv[argv.index("--job") + 1] if "--job" in argv else "unknown_job"
        config = read_json(ROOT / "configs/atlas_completion/analysis.json")
        stage = ROOT / config["run_root"] / "specificity" / job
        write_failure_terminal(stage, stop_code="specificity_unrecoverable_failure",
                               failed_gate="matched_random_sham_specificity", error=exc,
                               input_attestation=_FAILURE_ATTESTATION)
        raise
