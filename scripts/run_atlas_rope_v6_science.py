#!/usr/bin/env python3
"""Pre-validation-frozen adapter for the unchanged Atlas v3.3 scientific computation.

The adapter may change only namespaces, authorization/technical-QA verification,
and signed artifact schemas. Task, relation, intervention, projection, nuisance,
ridge, bootstrap, and decision functions are imported byte-frozen.
"""
from __future__ import annotations

import argparse
import ast
import hashlib
import inspect
import json
import os
import sys
import time
from pathlib import Path
from typing import Any, Mapping

os.environ.setdefault("CUBLAS_WORKSPACE_CONFIG", ":4096:8")

import numpy as np
import torch

sys.path.insert(0, str(Path(__file__).resolve().parent))

import analyze_atlas_discovery_v3_3 as frozen
from extract_atlas_discovery_v3_3 import (
    _forward_units as frozen_forward_units,
    _load_source_bundle as frozen_load_source_bundle,
)
from atlas_rope_v6 import (
    ROOT,
    RUN_ROOT,
    atomic_json,
    atomic_jsonl,
    canonical_array_hash,
    exclusive_lock,
    new_staging,
    promote,
    read_json,
    read_jsonl,
    recursive_inventory,
    score_cell,
    score_grid,
    sha256_file,
    verify_envelope,
    write_signed,
)
from run_atlas_rope_v6 import (
    ATTEMPT8_DATA_ROOT,
    CALIBRATION_CAP_CANDIDATE,
    CONFIG_PATH,
    GPU_UUID,
    IMPLEMENTATION_CANDIDATE,
    SCIENCE_AUTHORIZATION,
    _assert_not_terminal,
    _load_model,
    _runtime_attestation,
    _seed_runtime,
    _verify_authorization,
    _verify_implementation_candidate,
    _verify_ewt_history,
    _verify_gum_history,
    _verify_gum_sentinel_history,
    _retained_attempt7_pair,
)

ADAPTER_CONFIG = ROOT / "configs/atlas_rope_v6/science_adapter.json"
SCIENCE_ROOT = RUN_ROOT / "science"
RESULT_ROOT = ROOT / "results/atlas_rope_v6_attempt10_science"


def _ast_function_hashes(path: Path, names: set[str]) -> dict[str, str]:
    text = path.read_text(encoding="utf-8")
    lines = text.splitlines(keepends=True)
    tree = ast.parse(text)
    output: dict[str, str] = {}
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name in names:
            segment = "".join(lines[node.lineno - 1:node.end_lineno])
            output[node.name] = hashlib.sha256(segment.encode("utf-8")).hexdigest()
    if set(output) != names:
        raise RuntimeError(f"frozen function inventory drift for {path}: {sorted(names - set(output))}")
    return output


def verify_frozen_contract() -> dict[str, Any]:
    config = read_json(ADAPTER_CONFIG)
    if (config.get("schema_version") != "atlas_rope_v6_attempt10_science_adapter_v1" or
            config.get("status") != "FROZEN_BEFORE_HELDOUT_VALIDATION" or
            config.get("neural_training_authorized") is not False):
        raise RuntimeError("science-adapter config identity/permissions drift")
    for raw, expected in config["frozen_files"].items():
        path = ROOT / raw
        if sha256_file(path) != expected:
            raise RuntimeError(f"frozen science source drift: {raw}")
    for raw, expected in config["frozen_function_hashes"].items():
        observed = _ast_function_hashes(ROOT / raw, set(expected))
        if observed != expected:
            raise RuntimeError(f"frozen science function drift: {raw}")
    scoring_path = ROOT / config["frozen_scoring_config"]["path"]
    prescore_path = ROOT / config["frozen_science_prescore"]["path"]
    manifest_path = ROOT / config["frozen_prepared_manifest"]["path"]
    rebuild_path = ROOT / config["frozen_rebuild"]["path"]
    for path, spec in ((scoring_path, config["frozen_scoring_config"]),
                       (prescore_path, config["frozen_science_prescore"]),
                       (manifest_path, config["frozen_prepared_manifest"]),
                       (rebuild_path, config["frozen_rebuild"])):
        if sha256_file(path) != spec["sha256"]:
            raise RuntimeError(f"frozen science lineage drift: {path}")
    scoring = read_json(scoring_path)
    normalized = hashlib.sha256(json.dumps(scoring["analysis"], sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    if (scoring["analysis"] != config["frozen_analysis_settings"] or
            normalized != config["frozen_analysis_settings_sha256"]):
        raise RuntimeError("frozen analysis settings drift")
    if config["extraction"] != {"batch_size": 64, "device": "cuda:0", "hidden_state_index": 4,
                                "order": ["EWT", "GUM"], "sources": ["EWT", "GUM"]}:
        raise RuntimeError("science extraction adapter contract drift")
    if (config.get("analysis_output") != str(RESULT_ROOT.relative_to(ROOT)) or
            config.get("science_run_root") != str(SCIENCE_ROOT.relative_to(ROOT)) or
            config.get("technical_science_authorization") != str(SCIENCE_AUTHORIZATION.relative_to(ROOT)) or
            config.get("attempt9_run_root") != "pilot_runs/20260803_atlas_rope_technical_v5"):
        raise RuntimeError("science-adapter namespace/authorization contract drift")
    return config


def science_adapter_binding() -> dict[str, Any]:
    config = verify_frozen_contract()
    return {
        "config_path": str(ADAPTER_CONFIG.relative_to(ROOT)),
        "config_sha256": sha256_file(ADAPTER_CONFIG),
        "adapter_path": str(Path(__file__).resolve().relative_to(ROOT)),
        "adapter_sha256": sha256_file(Path(__file__).resolve()),
        "frozen_files": config["frozen_files"],
        "frozen_function_hashes": config["frozen_function_hashes"],
        "allowed_adapter_changes": config["allowed_adapter_changes"],
        "forbidden_scientific_changes": config["forbidden_scientific_changes"],
    }


def _verify_science_authorization() -> dict[str, Any]:
    _assert_not_terminal()
    implementation = _verify_implementation_candidate()
    authorization = _verify_authorization(SCIENCE_AUTHORIZATION, stage="EXPLORATORY_FROZEN_SCIENTIFIC_ATLAS")
    if (authorization.get("implementation_candidate_sha256") != sha256_file(IMPLEMENTATION_CANDIDATE) or
            authorization.get("science_adapter_sha256") != implementation["implementation_inventory"]["configs/atlas_rope_v6/science_adapter.json"]["sha256"] or
            authorization.get("calibration_cap_candidate_sha256") != sha256_file(CALIBRATION_CAP_CANDIDATE)):
        raise RuntimeError("science authorization adapter/calibration lineage drift")
    science_adapter_binding()
    return authorization


def _science_context() -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    adapter = verify_frozen_contract()
    scoring = read_json(ROOT / adapter["frozen_scoring_config"]["path"])
    prescore = read_json(ROOT / adapter["frozen_science_prescore"]["path"])
    manifest = read_json(ROOT / adapter["frozen_prepared_manifest"]["path"])
    return scoring, prescore, manifest


def _cache_paths(source: str) -> tuple[Path, Path, Path]:
    root = SCIENCE_ROOT / "activations" / source
    return root, root / "activations.float32.npy", root / "row_ids.jsonl"


def verify_science_cache(source: str) -> dict[str, Any]:
    if source not in ("EWT", "GUM"):
        raise RuntimeError("unknown science source")
    _, prescore, manifest = _science_context()
    bundle = frozen_load_source_bundle(prescore, manifest, source)
    final, array_path, rows_path = _cache_paths(source)
    if {p.name for p in final.iterdir()} != {"COMPLETE.json", "activations.float32.npy", "row_ids.jsonl"}:
        raise RuntimeError("science cache file allowlist drift")
    payload = verify_envelope(read_json(final / "COMPLETE.json"))
    if (payload.get("schema_version") != "atlas_rope_v6_attempt10_science_activation_v1" or
            payload.get("status") != "COMPLETE" or payload.get("source") != source or
            payload.get("neural_training_run") is not False):
        raise RuntimeError("science cache completion identity drift")
    if set(payload.get("artifacts", {})) != {"activations.float32.npy", "row_ids.jsonl"}:
        raise RuntimeError("science cache signed artifact inventory is not exact")
    for name, spec in payload["artifacts"].items():
        path = final / name
        if path.stat().st_size != int(spec["bytes"]) or sha256_file(path) != spec["sha256"]:
            raise RuntimeError(f"science cache artifact drift: {source}/{name}")
    expected_ids = [str(row["row_id"]) for row in bundle["rows"]]
    observed_ids = [str(row["row_id"]) for row in frozen.jsonl(rows_path)]
    if observed_ids != expected_ids or len(observed_ids) != len(set(observed_ids)):
        raise RuntimeError("science cache row-ID lineage drift")
    array = np.load(array_path, mmap_mode="r", allow_pickle=False)
    if array.dtype != np.float32 or array.shape != (len(expected_ids), 768) or not np.isfinite(array).all():
        raise RuntimeError("science cache array structure drift")
    if canonical_array_hash(np.asarray(array)) != payload["canonical_array_sha256"]:
        raise RuntimeError("science cache canonical array hash drift")
    if (payload.get("prepared_manifest_sha256") != sha256_file(ROOT / verify_frozen_contract()["frozen_prepared_manifest"]["path"]) or
            payload.get("science_authorization_sha256") != sha256_file(SCIENCE_AUTHORIZATION)):
        raise RuntimeError("science cache authorization/prepared lineage drift")
    _verify_science_authorization()
    return payload


def extract_source(source: str, signing_key: Path) -> dict[str, Any]:
    authorization = _verify_science_authorization()
    adapter = verify_frozen_contract()
    _, prescore, manifest = _science_context()
    if source not in adapter["extraction"]["sources"]:
        raise RuntimeError("science source outside frozen adapter")
    if source == "GUM" and not (SCIENCE_ROOT / "activations/EWT/COMPLETE.json").is_file():
        raise RuntimeError("GUM science extraction requires completed EWT science cache")
    final, _, _ = _cache_paths(source)
    if final.exists():
        return verify_science_cache(source)
    bundle = frozen_load_source_bundle(prescore, manifest, source)
    units, rows = bundle["units"], bundle["rows"]
    device = torch.device(adapter["extraction"]["device"])
    with exclusive_lock("attempt-wide-gpu"):
        _seed_runtime(20260803)
        model = _load_model(read_json(CONFIG_PATH), device)
        runtime_preflight = _runtime_attestation(model, device, read_json(CONFIG_PATH))
        started = time.time()
        values = frozen_forward_units(model, units, device=device, hidden_index=4, batch_size=64)
        runtime_postflight = _runtime_attestation(model, device, read_json(CONFIG_PATH))
        if values.shape != (len(rows), 768) or values.dtype != np.float32 or not np.isfinite(values).all():
            raise RuntimeError("science extraction output shape/dtype/finite drift")
        stage = new_staging(f"science-{source}", sha256_file(SCIENCE_AUTHORIZATION))
        np.save(stage / "activations.float32.npy", np.ascontiguousarray(values), allow_pickle=False)
        with (stage / "activations.float32.npy").open("rb") as handle:
            os.fsync(handle.fileno())
        atomic_jsonl(stage / "row_ids.jsonl", ({"row_id": str(row["row_id"])} for row in rows))
        artifacts = {path.name: {"bytes": path.stat().st_size, "sha256": sha256_file(path)}
                     for path in stage.iterdir() if path.is_file()}
        payload = {
            "schema_version": "atlas_rope_v6_attempt10_science_activation_v1",
            "status": "COMPLETE", "source": source, "rows": len(rows), "units": len(units), "width": 768,
            "model": adapter["model"], "hidden_state_index": 4, "batch_size": 64,
            "canonical_array_sha256": canonical_array_hash(values),
            "science_authorization_sha256": sha256_file(SCIENCE_AUTHORIZATION),
            "implementation_candidate_sha256": authorization["implementation_candidate_sha256"],
            "prepared_manifest_sha256": adapter["frozen_prepared_manifest"]["sha256"],
            "runtime_preflight": runtime_preflight, "runtime_postflight": runtime_postflight,
            "elapsed_seconds": time.time() - started,
            "model_eval": True, "inference_mode": True, "requires_grad": False,
            "optimizer_created": False, "checkpoint_created": False, "neural_training_run": False,
            "artifacts": artifacts,
        }
        write_signed(stage / "COMPLETE.json", payload, signing_key.resolve(strict=True))
        promote(stage, final)
    return verify_science_cache(source)


def _attempt7_family_panels(reference: np.ndarray, candidate: np.ndarray, lineage: Mapping[str, Any],
                            caps: Mapping[str, float]) -> dict[str, Any]:
    expected = {"legacy|uniform_shift": 32, "legacy|prefix_position_only": 16,
                "fresh|uniform_shift": 16, "fresh|prefix_position_only": 8}
    raw_indices = lineage.get("family_indices", {})
    if set(raw_indices) != set(expected):
        raise RuntimeError("retained attempt-7 family-index inventory drift")
    panels: dict[str, dict[str, Any]] = {"legacy": {}, "fresh": {}}
    covered: list[int] = []
    for key, count in expected.items():
        panel, family = key.split("|", 1)
        indices = list(map(int, raw_indices[key]))
        if len(indices) != count or len(indices) != len(set(indices)) or any(index < 0 or index >= len(reference) for index in indices):
            raise RuntimeError(f"retained attempt-7 family indices invalid: {key}")
        covered.extend(indices)
        stat = score_cell(reference[np.asarray(indices)], candidate[np.asarray(indices)],
                          atol=float(caps["atol"]), relative_l2_cap=float(caps["relative_l2"]),
                          cosine_cap=float(caps["cosine_distance"]), strict_zero_failures=True)
        panels[panel][family] = {**stat, "criterion": "calibration_cap_exact_family_replay",
                                 "index_count": len(indices)}
    if sorted(covered) != list(range(len(reference))) or len(reference) != len(candidate) or len(reference) != 72:
        raise RuntimeError("retained attempt-7 family indices do not partition the signed rows")
    return panels


def _grid_bridge_stat(score: Mapping[str, Any]) -> dict[str, Any]:
    cells = score.get("cells", {})
    expected_budgets = {"coordinate_failing_elements": 30, "coordinate_failing_rows": 2,
                        "relative_l2_failing_rows": 0, "cosine_failing_rows": 0}
    if score.get("status") != "PASS" or score.get("required_cells") != 30 or len(cells) != 30:
        raise RuntimeError("signed validation grid is not a complete PASS")
    for key, cell in cells.items():
        if (cell.get("status") != "PASS" or cell.get("rows") != 40 or cell.get("width") != 768 or
                cell.get("budgets") != expected_budgets or
                int(cell.get("coordinate_failing_elements", 31)) > 30 or
                int(cell.get("coordinate_failing_rows", 3)) > 2 or
                cell.get("relative_l2_failing_rows") != 0 or cell.get("cosine_failing_rows") != 0 or
                cell.get("nonfinite_rows") != 0):
            raise RuntimeError(f"signed validation grid cell is not a frozen-budget PASS: {key}")
    return {"status": "PASS", "criterion": "exact_signed_frozen_budget_grid",
            "required_cells": 30, "rows": 1200, "cells": dict(cells)}


def _sentinel_bridge_stats(pair_scores: list[Mapping[str, Any]]) -> dict[str, Any]:
    grouped: dict[str, list[Mapping[str, Any]]] = {"uniform_shift": [], "prefix_position_only": []}
    for row in pair_scores:
        family = str(row.get("family"))
        if family not in grouped or row.get("score", {}).get("status") != "PASS":
            raise RuntimeError("signed sentinel pair/family is not a PASS")
        grouped[family].append(row)
    if {family: len(rows) for family, rows in grouped.items()} != {"uniform_shift": 8, "prefix_position_only": 8}:
        raise RuntimeError("signed sentinel family counts drift")
    return {family: {"status": "PASS", "criterion": "exact_signed_strict_pair_scores",
                     "pairs": len(rows), "rows": sum(int(row["score"]["rows"]) for row in rows),
                     "pair_scores": [{"pair_id": str(row["pair_id"]), "score": dict(row["score"])} for row in rows]}
            for family, rows in grouped.items()}


def _qa_bridge_payload(source: str) -> dict[str, Any]:
    authorization = _verify_science_authorization()
    cap = verify_envelope(read_json(CALIBRATION_CAP_CANDIDATE))
    caps = {**cap["caps"], "rtol": cap["fixed_rtol"]}
    if source == "EWT":
        old_ref, old_candidate, old_lineage = _retained_attempt7_pair()
        new_ref, new_candidate, rows, history = _verify_ewt_history()
        attempt8_score = score_grid(new_ref, new_candidate, rows,
                                    atol=float(caps["atol"]), relative_l2_cap=float(caps["relative_l2"]),
                                    cosine_cap=float(caps["cosine_distance"]))
        panels = _attempt7_family_panels(old_ref, old_candidate, old_lineage, caps)
        panels["attempt8_grid"] = {"uniform_shift": _grid_bridge_stat(attempt8_score)}
        lineage = {"calibration_cap_candidate_sha256": sha256_file(CALIBRATION_CAP_CANDIDATE),
                   "attempt8_staging_complete_sha256": history["staging_complete_sha256"]}
    elif source == "GUM":
        reference, candidate, rows, history = _verify_gum_history()
        grid_score = score_grid(reference, candidate, rows,
                                atol=float(caps["atol"]), relative_l2_cap=float(caps["relative_l2"]),
                                cosine_cap=float(caps["cosine_distance"]))
        sentinel = _verify_gum_sentinel_history(cap["caps"])
        pairs = [{"pair_id": row["pair_id"], "family": row["family"], "score": row["score"]} for row in sentinel["pairs"]]
        panels = {"fresh_sentinel": _sentinel_bridge_stats(pairs),
                  "five_bin_grid": {"uniform_shift": _grid_bridge_stat(grid_score)}}
        lineage = {"attempt9_terminal_bound": True,
                   "sentinel_complete_sha256": sentinel["complete_sha256"],
                   "grid_complete_sha256": history["complete_sha256"],
                   "sentinel_status": sentinel["status"], "grid_status": grid_score["status"],
                   "attempt9_gum_pass_required": False}
    else:
        raise RuntimeError("unknown QA bridge source")
    if any(stat["status"] != "PASS" for families in panels.values() for stat in families.values()):
        raise RuntimeError(f"science QA bridge contains a failure: {source}")
    return {
        "schema_version": "atlas_rope_v6_attempt10_science_qa_bridge_v1",
        "status": "PASS", "source": source,
        "tolerance": caps, "panels": panels, "lineage": lineage,
        "science_authorization_sha256": sha256_file(SCIENCE_AUTHORIZATION),
        "implementation_candidate_sha256": authorization["implementation_candidate_sha256"],
        "neural_training_authorized": False,
    }


def _qa_bridge_path(source: str) -> Path:
    return SCIENCE_ROOT / "numerical_qa" / source / "QA_COMPLETE.json"


def make_qa_bridge(source: str, signing_key: Path) -> dict[str, Any]:
    path = _qa_bridge_path(source)
    if path.exists():
        return verify_qa_bridge(source)
    payload = _qa_bridge_payload(source)
    write_signed(path, payload, signing_key.resolve(strict=True))
    return verify_qa_bridge(source)


def verify_qa_bridge(source: str) -> dict[str, Any]:
    observed = verify_envelope(read_json(_qa_bridge_path(source)))
    if observed != _qa_bridge_payload(source):
        raise RuntimeError(f"science QA bridge drift: {source}")
    return {"payload": observed, "signature": read_json(_qa_bridge_path(source))["signature"]}


def _effective_analysis_context() -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    scoring, prescore, manifest = _science_context()
    effective_scoring = json.loads(json.dumps(scoring))
    effective_prescore = json.loads(json.dumps(prescore))
    effective_scoring["_resolved_sha256"] = sha256_file(ADAPTER_CONFIG)
    effective_scoring["analysis"] = verify_frozen_contract()["frozen_analysis_settings"]
    effective_prescore["run_root"] = str(SCIENCE_ROOT.relative_to(ROOT))
    return effective_scoring, effective_prescore, manifest


def run_analysis(signing_key: Path) -> dict[str, Any]:
    _verify_science_authorization()
    verify_science_cache("EWT")
    verify_science_cache("GUM")
    make_qa_bridge("EWT", signing_key)
    make_qa_bridge("GUM", signing_key)
    if RESULT_ROOT.exists():
        return verify_envelope(read_json(RESULT_ROOT / "COMPLETE.json"))
    scoring, prescore, manifest = _effective_analysis_context()
    original_loader = frozen.load_scoring_config
    original_cache_verifier = frozen._verify_complete_cache
    original_qa_verifier = frozen._verify_qa
    try:
        frozen.load_scoring_config = lambda path: (scoring, prescore, manifest)
        frozen._verify_complete_cache = lambda final, cfg, pre, bundle, source: verify_science_cache(source)
        frozen._verify_qa = lambda path, cfg, source: verify_qa_bridge(source)
        started = time.time()
        result = frozen.run(ADAPTER_CONFIG)
    finally:
        frozen.load_scoring_config = original_loader
        frozen._verify_complete_cache = original_cache_verifier
        frozen._verify_qa = original_qa_verifier
    stage = new_staging("science-analysis", sha256_file(SCIENCE_AUTHORIZATION))
    atomic_json(stage / "result.json", result)
    (stage / "report.md").write_text(frozen._render_markdown(result), encoding="utf-8")
    atomic_json(stage / "lineage.json", result["lineage"])
    artifacts = {path.name: {"bytes": path.stat().st_size, "sha256": sha256_file(path)}
                 for path in stage.iterdir() if path.is_file()}
    payload = {
        "schema_version": "atlas_rope_v6_attempt10_science_complete_v1",
        "status": "COMPLETE", "outcome": result["outcome"],
        "science_authorization_sha256": sha256_file(SCIENCE_AUTHORIZATION),
        "implementation_candidate_sha256": sha256_file(IMPLEMENTATION_CANDIDATE),
        "science_adapter": science_adapter_binding(),
        "frozen_result_schema": result["schema_version"],
        "elapsed_seconds": time.time() - started,
        "neural_training_run": False, "artifacts": artifacts,
    }
    write_signed(stage / "COMPLETE.json", payload, signing_key.resolve(strict=True))
    promote(stage, RESULT_ROOT)
    return verify_envelope(read_json(RESULT_ROOT / "COMPLETE.json"))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("stage", choices=("verify", "extract-ewt", "extract-gum", "analyze"))
    parser.add_argument("--signing-key", type=Path)
    args = parser.parse_args()
    if args.stage == "verify":
        result = science_adapter_binding()
    else:
        if args.signing_key is None:
            raise RuntimeError(f"{args.stage} requires --signing-key")
        if args.stage == "extract-ewt":
            result = extract_source("EWT", args.signing_key)
        elif args.stage == "extract-gum":
            result = extract_source("GUM", args.signing_key)
        else:
            result = run_analysis(args.signing_key)
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
