#!/usr/bin/env python3
"""Cross-checkpoint K2 CKA and separate simple refit-reproducibility CKA."""

from __future__ import annotations

import argparse
import json
import pickle
import time
from itertools import combinations
from pathlib import Path
from typing import Any

import numpy as np

from msa_completion_common import (EVIDENCE_CLASS, ROOT, LiveDrawClaimError,
                                   StageTerminalError,
                                   atomic_write_json,
                                   attest_completion_freeze_record,
                                   claim_draw, default_firewall,
                                   deterministic_seed, draw_group_multiplicities,
                                   fit_weighted_ridge_torch, load_activation,
                                   load_row_file, maybe_finalize_draw_stage,
                                   project_complement,
                                   prepare_draw_resume, project_coords, read_json,
                                   register_draw_artifact, release_claim,
                                   require_bound_stage_files,
                                   require_frozen_completion_config,
                                   runtime_environment, sha256_file,
                                   seed_provenance,
                                   stage_publication_lock,
                                   terminal_state, weighted_linear_cka,
                                   unit_group_multiplicities,
                                   validated_cuda_environment,
                                   utc_now,
                                   verify_parent_raw_calibration,
                                   verify_parent_transform,
                                   weighted_mean_scale,
                                   weights_from_multiplicities,
                                   write_failure_terminal)
from run_msae_refit_worker import PRIMARY, TASKS, build_bases, scaler_sample


_FAILURE_ATTESTATION: dict[str, Any] = {}


def stability_draw_finite(task_values: dict[str, Any], family_values: dict[str, Any]) -> bool:
    """All primary, simple, and mandatory g7 descriptive CKA leaves must exist."""

    return bool(task_values and all(
        row["learned_stability_loss"] is not None
        and row["simple_A_B_cka_descriptive"] is not None
        and row["g4_g7_regularizer_sensitivity_cka_descriptive"] is not None
        and all(value is not None for value in row["pair_means"].values())
        for row in family_values.values()))


def rep_array(root: Path, job: str, role: str, rep: str, firewall: Any) -> np.ndarray:
    return np.load(firewall.attest(root / "k2_transforms" / job / role / f"{rep}.float16.npy", role=role), mmap_mode="r")


def task_matrix_cka(x: np.ndarray, y: np.ndarray, weights: np.ndarray) -> float | None:
    """Frozen stability estimator: one weighted CKA per complete task matrix."""

    return weighted_linear_cka(x, y, weights)


def raw_fit_bases(discovery: Any, task_rows: dict[str, tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]],
                  group_mult: dict[tuple[str, str], int], layer: int, config: dict[str, Any],
                  raw_alpha: dict[str, float], device: str, need_pca: bool) -> tuple[np.ndarray, np.ndarray, dict[str, np.ndarray]]:
    sample = scaler_sample(discovery, layer, config)
    sample_weights = weights_from_multiplicities(discovery.row_source[sample], discovery.row_group[sample], group_mult)
    mean, scale = weighted_mean_scale(np.asarray(discovery.x[sample], np.float32), sample_weights)
    models = {}
    for task in TASKS:
        rows, labels, sources, groups = task_rows[task]
        weights = weights_from_multiplicities(sources, groups, group_mult)
        x = (np.asarray(discovery.x[rows], np.float32) - mean) / scale
        models[task] = fit_weighted_ridge_torch(x, labels, weights, float(raw_alpha[task]), device)
    pca_x = (np.asarray(discovery.x[sample], np.float32) - mean) / scale if need_pca else None
    return mean, scale, build_bases(models, config, pca_x, sample_weights if need_pca else None, device)


def simple_component(x_raw: np.ndarray, mean: np.ndarray, scale: np.ndarray, bases: dict[str, np.ndarray],
                     candidate: str, family: str) -> np.ndarray:
    x = (np.asarray(x_raw, np.float32) - mean) / scale
    if candidate == "projection_broad16":
        basis = bases["broad_position"]
        position = family != "lexical_semantic_content"
    elif candidate == "projection_split8_8":
        basis = bases["absolute_position"] if family == "absolute_position" else bases["relative_structural_position"] if family == "relative_structural_position" else bases["split_position_joint"]
        position = family != "lexical_semantic_content"
    else:
        basis, position = bases["pca16"], family != "lexical_semantic_content"
    component = (project_coords(x, basis) @ basis.T) if position else project_complement(x, basis)
    # Return to ambient activation coordinates.  Additive constants do not affect centered CKA.
    return component * scale


def main() -> None:
    global _FAILURE_ATTESTATION
    parser = argparse.ArgumentParser()
    parser.add_argument("--draw-start", type=int)
    parser.add_argument("--draw-end", type=int)
    parser.add_argument("--point", action="store_true")
    parser.add_argument("--device", default="cuda:0")
    parser.add_argument("--config", type=Path, default=ROOT / "configs/atlas_completion/analysis.json")
    args = parser.parse_args()
    completion_freeze = require_frozen_completion_config(args.config)
    config = read_json(args.config)
    if not args.point and (args.draw_start is None or args.draw_end is None or not (0 <= args.draw_start < args.draw_end <= int(config["draws"]))):
        raise ValueError("invalid draw shard")
    source_root = ROOT / config["source_run_root"]
    run_root = ROOT / config["run_root"]
    stage = run_root / "stability"
    stage.mkdir(parents=True, exist_ok=True)
    if terminal_state(stage) is not None:
        raise RuntimeError("stability stage is terminal")
    draws_dir = stage / "draws"
    draws_dir.mkdir(exist_ok=True)
    firewall = default_firewall(source_root, run_root)
    _FAILURE_ATTESTATION = firewall.attestation
    attest_completion_freeze_record(firewall, completion_freeze)
    launch_environment = validated_cuda_environment(args.device)
    config_sha = sha256_file(firewall.attest(args.config))
    require_bound_stage_files(
        run_root / "baseline", firewall, config_sha256=config_sha,
        completion_bundle_sha256=completion_freeze["bundle_sha256"],
        expected_files={"result_sha256": "baseline.json",
                        "bundle_sha256": "baseline_bundle.pkl"})
    with firewall.attest(run_root / "baseline/baseline_bundle.pkl").open("rb") as handle:
        baseline = pickle.load(handle)
    if baseline.get("completion_bundle_sha256") != completion_freeze["bundle_sha256"]:
        raise RuntimeError("baseline bundle is not bound to the completion freeze")
    candidate = baseline["selected_simple_baseline"]
    discovery = load_activation("discovery", 3, source_root, firewall)
    c2 = load_activation("C2", 3, source_root, firewall)
    task_manifest = read_json(firewall.attest(ROOT / "configs/atlas/task_row_manifest.json"))
    drows = {task: load_row_file(ROOT / task_manifest["roles"]["discovery"][task]["path"], discovery, firewall, role="discovery") for task in TASKS}
    erows = {task: load_row_file(ROOT / task_manifest["roles"]["C2"][task]["path"], c2, firewall, role="C2") for task in TASKS}
    verify_parent_raw_calibration(source_root, firewall)
    raw_freeze = read_json(firewall.attest(ROOT / "results/atlas/raw_v1/L3_calibration_freeze.json"))
    raw_alpha = raw_freeze["raw_alpha"]
    primary = config["primary_checkpoints"]
    descriptive = config["descriptive_checkpoints"][0]
    for job in primary + [descriptive]:
        verify_parent_transform(source_root, job, firewall)
    arrays = {job: {rep: rep_array(source_root, job, "C2", rep, firewall) for rep in ["pos", "content"]}
              for job in primary + [descriptive]}
    eligible = {task for task, row in baseline["tier1_eligibility"].items() if row["eligible"]}
    completed, failed = [], []
    shard_started = time.monotonic()
    shard_started_utc = utc_now()
    draw_ids: list[int | None] = [None] if args.point else list(range(args.draw_start, args.draw_end))
    for draw in draw_ids:
        if terminal_state(stage) is not None:
            return
        path = stage / "point.json" if draw is None else draws_dir / f"{draw:04d}.json"
        if draw is not None:
            resume_state = prepare_draw_resume(stage, draw, config_sha256=config_sha,
                                               completion_bundle_sha256=completion_freeze["bundle_sha256"])
            if resume_state == "complete":
                completed.append(draw)
                continue
            if resume_state == "failed":
                failed.append(draw)
                continue
        elif path.exists():
            prior = read_json(path)
            if prior.get("completion_bundle_sha256") != completion_freeze["bundle_sha256"]:
                raise RuntimeError("existing stability point is not bound to completion freeze")
            continue
        claim = None if draw is None else claim_draw(stage, draw, config_sha)
        started = time.monotonic()
        draw_started_utc = utc_now()
        try:
            eval_mult = (unit_group_multiplicities(c2.row_source.astype(str), c2.row_group.astype(str)) if draw is None else
                         draw_group_multiplicities(c2.row_source.astype(str), c2.row_group.astype(str),
                                                   seed=deterministic_seed(config["seed"], "C2", 3, draw)))
            map_a = (unit_group_multiplicities(discovery.row_source.astype(str), discovery.row_group.astype(str)) if draw is None else
                     draw_group_multiplicities(discovery.row_source.astype(str), discovery.row_group.astype(str),
                                               seed=deterministic_seed(config["seed"], "simple_stability_A", 3, draw)))
            map_b = (unit_group_multiplicities(discovery.row_source.astype(str), discovery.row_group.astype(str)) if draw is None else
                     draw_group_multiplicities(discovery.row_source.astype(str), discovery.row_group.astype(str),
                                               seed=deterministic_seed(config["seed"], "simple_stability_B", 3, draw)))
            need_pca = candidate == "pca16_complement"
            mean_a, scale_a, bases_a = raw_fit_bases(discovery, drows, map_a, 3, config, raw_alpha, args.device, need_pca)
            mean_b, scale_b, bases_b = raw_fit_bases(discovery, drows, map_b, 3, config, raw_alpha, args.device, need_pca)
            task_values: dict[str, Any] = {}
            for family, tasks in PRIMARY.items():
                for task in tasks:
                    if task not in eligible:
                        continue
                    rows, _, sources, groups = erows[task]
                    weights = weights_from_multiplicities(sources, groups, eval_mult)
                    k2_rep = "content" if family == "lexical_semantic_content" else "pos"
                    pair_values = {}
                    for left, right in combinations(primary, 2):
                        pair_values[f"{left}__{right}"] = task_matrix_cka(
                            np.asarray(arrays[left][k2_rep][rows], np.float32),
                            np.asarray(arrays[right][k2_rep][rows], np.float32), weights)
                    pair_values[f"{primary[0]}__{descriptive}"] = task_matrix_cka(
                        np.asarray(arrays[primary[0]][k2_rep][rows], np.float32),
                        np.asarray(arrays[descriptive][k2_rep][rows], np.float32), weights)
                    raw_x = np.asarray(c2.x[rows], np.float32)
                    simple_a = simple_component(raw_x, mean_a, scale_a, bases_a, candidate, family)
                    simple_b = simple_component(raw_x, mean_b, scale_b, bases_b, candidate, family)
                    simple = task_matrix_cka(simple_a, simple_b, weights)
                    task_values[task] = {"family": family, "k2_pairs": pair_values, "simple_A_B": simple}
            family_values = {}
            for family, tasks in PRIMARY.items():
                usable = [task_values[t] for t in tasks if t in task_values]
                family_eligible = len(usable) >= int(config["minimum_family_tasks"])
                primary_pairs = list(combinations(primary, 2))
                pair_means = {f"{a}__{b}": float(np.mean([row["k2_pairs"][f"{a}__{b}"] for row in usable]))
                              if family_eligible and all(row["k2_pairs"][f"{a}__{b}"] is not None for row in usable) else None
                              for a, b in primary_pairs}
                learned = float(np.mean(list(pair_means.values()))) if pair_means and all(v is not None for v in pair_means.values()) else None
                simple = (float(np.mean([row["simple_A_B"] for row in usable]))
                          if family_eligible and all(row["simple_A_B"] is not None for row in usable) else None)
                g7_key = f"{primary[0]}__{descriptive}"
                g7_value = (float(np.mean([row["k2_pairs"][g7_key] for row in usable]))
                            if family_eligible and all(row["k2_pairs"][g7_key] is not None for row in usable) else None)
                family_values[family] = {"learned_mean_pairwise_cka": learned,
                                         "learned_stability_loss": None if learned is None else 1.0 - learned,
                                         "simple_A_B_cka_descriptive": simple,
                                         "g4_g7_regularizer_sensitivity_cka_descriptive": g7_value,
                                         "pair_means": pair_means}
            derived_seeds = ({} if draw is None else {
                "C2": deterministic_seed(config["seed"], "C2", 3, draw),
                "simple_stability_A": deterministic_seed(
                    config["seed"], "simple_stability_A", 3, draw),
                "simple_stability_B": deterministic_seed(
                    config["seed"], "simple_stability_B", 3, draw),
            })
            result = {"schema_version": "atlas_completion_stability_draw_v1", "evidence_class": EVIDENCE_CLASS,
                      "draw_id": "point" if draw is None else draw, "families": family_values, "tasks": task_values,
                      "finite": stability_draw_finite(task_values, family_values),
                      "elapsed_sec": time.monotonic() - started, "config_sha256": config_sha,
                      "resolved_config": config,
                      "resolved_arguments": {"point": draw is None, "draw_id": draw,
                                             "device": args.device},
                      "seed_provenance": seed_provenance(
                          config,
                          contract=("unit weights for point; otherwise deterministic_seed(base_seed, "
                                    "C2/simple_stability_A/simple_stability_B, 3, draw_id)"),
                          derived=derived_seeds),
                      "device": args.device,
                      "started_utc": draw_started_utc, "ended_utc": utc_now(),
                      "completion_bundle_sha256": completion_freeze["bundle_sha256"],
                      "environment": launch_environment,
                      "input_attestation": firewall.attestation}
            with stage_publication_lock(stage):
                if terminal_state(stage) is not None:
                    return
                atomic_write_json(path, result)
                if draw is not None:
                    register_draw_artifact(stage, draw, path, status="complete",
                                           config_sha256=config_sha,
                                           completion_bundle_sha256=completion_freeze["bundle_sha256"])
                    completed.append(draw)
        except Exception as exc:
            error_name = "point.json" if draw is None else f"{draw:04d}.json"
            error_path = stage / "errors" / error_name
            error_payload = {
                "schema_version": "atlas_completion_stability_draw_error_v1",
                "evidence_class": EVIDENCE_CLASS,
                "draw_id": "point" if draw is None else draw,
                "error_type": type(exc).__name__, "error": str(exc),
                "elapsed_sec": time.monotonic() - started,
                "started_utc": draw_started_utc, "ended_utc": utc_now(),
                "environment": launch_environment,
                "config_sha256": config_sha,
                "resolved_config": config,
                "resolved_arguments": {"point": draw is None, "draw_id": draw,
                                       "device": args.device},
                "seed_provenance": seed_provenance(
                    config,
                    contract=("unit weights for point; otherwise deterministic_seed(base_seed, "
                              "C2/simple_stability_A/simple_stability_B, 3, draw_id)"),
                    derived=({} if draw is None else {
                        "C2": deterministic_seed(config["seed"], "C2", 3, draw),
                        "simple_stability_A": deterministic_seed(
                            config["seed"], "simple_stability_A", 3, draw),
                        "simple_stability_B": deterministic_seed(
                            config["seed"], "simple_stability_B", 3, draw),
                    })),
                "device": args.device,
                "completion_bundle_sha256": completion_freeze["bundle_sha256"],
                "input_attestation": dict(firewall.attestation),
            }
            with stage_publication_lock(stage):
                if terminal_state(stage) is not None:
                    return
                atomic_write_json(error_path, error_payload)
                if draw is not None:
                    register_draw_artifact(stage, draw, error_path, status="failed",
                                           config_sha256=config_sha,
                                           completion_bundle_sha256=completion_freeze["bundle_sha256"])
                    failed.append(draw)
            if draw is None:
                raise
        finally:
            if claim is not None:
                release_claim(claim)
    if args.point:
        maybe_finalize_draw_stage(stage, requested_draws=int(config["draws"]),
                                  minimum_complete_draws=int(config["minimum_complete_draws"]),
                                  config_sha256=config_sha,
                                  completion_bundle_sha256=completion_freeze["bundle_sha256"],
                                  schema_version="atlas_completion_stability_terminal_v1",
                                  expected_shards=[(0, 167), (167, 334), (334, 500)])
        print(json.dumps({"stage": str(stage), "point": True}, indent=2))
        return
    with stage_publication_lock(stage):
        if terminal_state(stage) is not None:
            return
        atomic_write_json(stage / f"shard_{args.draw_start:04d}_{args.draw_end:04d}.json",
                          {"schema_version": "atlas_completion_stability_shard_v1", "draw_start": args.draw_start,
                       "draw_end": args.draw_end, "completed": completed, "failed": failed,
                       "config_sha256": config_sha,
                       "resolved_config": config,
                       "resolved_arguments": {"point": False,
                                              "draw_start": args.draw_start,
                                              "draw_end": args.draw_end,
                                              "device": args.device},
                       "seed_provenance": seed_provenance(
                           config,
                           contract=("draw leaves bind deterministic_seed(base_seed, "
                                     "C2/simple_stability_A/simple_stability_B, 3, draw_id)")),
                       "device": args.device,
                       "completion_bundle_sha256": completion_freeze["bundle_sha256"],
                       "elapsed_sec": time.monotonic() - shard_started,
                       "started_utc": shard_started_utc, "ended_utc": utc_now(),
                           "environment": launch_environment, "input_attestation": firewall.attestation})
    maybe_finalize_draw_stage(stage, requested_draws=int(config["draws"]),
                              minimum_complete_draws=int(config["minimum_complete_draws"]),
                              config_sha256=config_sha,
                              completion_bundle_sha256=completion_freeze["bundle_sha256"],
                              schema_version="atlas_completion_stability_terminal_v1",
                              expected_shards=[(0, 167), (167, 334), (334, 500)])
    print(json.dumps({"completed": len(completed), "failed": len(failed), "stage": str(stage)}, indent=2))


if __name__ == "__main__":
    try:
        main()
    except (LiveDrawClaimError, StageTerminalError) as exc:
        print(json.dumps({"worker_blocked_by_existing_work_or_terminal": str(exc)}))
    except Exception as exc:
        argv = __import__("sys").argv
        config = read_json(ROOT / "configs/atlas_completion/analysis.json")
        stage = ROOT / config["run_root"] / "stability"
        write_failure_terminal(stage, stop_code="stability_worker_unrecoverable_failure",
                               failed_gate="cross_checkpoint_stability", error=exc,
                               requested_draw_ids=range(int(config["draws"])),
                               input_attestation=_FAILURE_ATTESTATION)
        raise
