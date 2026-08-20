#!/usr/bin/env python3
"""Endpoint-scoped adapter around the byte-frozen Atlas v3.3 science."""
from __future__ import annotations

import argparse
import copy
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
import run_atlas_rope_v5 as runtime
import run_atlas_rope_v6_science as legacy
from extract_atlas_discovery_v3_3 import _forward_units as frozen_forward_units, _load_source_bundle as frozen_load_source_bundle
from atlas_rope_v7 import (
    DATA_ROOT,
    PANEL_NAMES,
    RESULT_ROOT,
    ROOT,
    RUN_ROOT,
    atomic_json,
    atomic_jsonl,
    canonical_array_hash,
    exclusive_lock,
    make_eligibility_overlay,
    new_staging,
    promote,
    read_json,
    sha256_file,
    verify_envelope,
    write_signed,
)
from run_atlas_rope_v7 import (
    IMPLEMENTATION_CANDIDATE,
    MODEL_CONFIG,
    SCIENCE_AUTHORIZATION,
    _assert_not_terminal,
    _verify_candidate,
    _verify_science_authorization,
    lifecycle_lock,
)

SCIENCE_ROOT = RUN_ROOT / "science"
FROZEN_ADAPTER = ROOT / "configs/atlas_rope_v6/science_adapter.json"


def verify_frozen_contract() -> dict[str, Any]:
    # The v6 adapter already binds every frozen source/function/config hash.
    return legacy.verify_frozen_contract()


def _authorization() -> dict[str, Any]:
    _assert_not_terminal(); _verify_candidate()
    auth = _verify_science_authorization()
    verify_frozen_contract()
    return auth


def _context() -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    adapter = verify_frozen_contract()
    return (
        read_json(ROOT / adapter["frozen_scoring_config"]["path"]),
        read_json(ROOT / adapter["frozen_science_prescore"]["path"]),
        read_json(ROOT / adapter["frozen_prepared_manifest"]["path"]),
    )


def _cache_root(source: str) -> Path:
    return SCIENCE_ROOT / "activations" / source


def verify_cache(source: str) -> dict[str, Any]:
    _assert_not_terminal(); auth = _authorization()
    if source not in ("EWT", "GUM"):
        raise RuntimeError("unknown frozen science source")
    adapter = verify_frozen_contract(); _, prescore, manifest = _context(); bundle = frozen_load_source_bundle(prescore, manifest, source)
    root = _cache_root(source)
    entries = list(root.iterdir())
    if {path.name for path in entries} != {"COMPLETE.json", "activations.float32.npy", "row_ids.jsonl"} or any(not path.is_file() or path.is_symlink() for path in entries):
        raise RuntimeError("science cache allowlist drift")
    payload = verify_envelope(read_json(root / "COMPLETE.json"))
    expected_artifacts = {
        name: {"bytes": (root / name).stat().st_size, "sha256": sha256_file(root / name)}
        for name in ("activations.float32.npy", "row_ids.jsonl")
    }
    if (
        payload.get("schema_version") != "atlas_rope_v7_attempt11_science_activation_v1"
        or payload.get("status") != "COMPLETE"
        or payload.get("source") != source
        or payload.get("artifacts") != expected_artifacts
        or payload.get("science_authorization_sha256") != sha256_file(SCIENCE_AUTHORIZATION)
        or payload.get("implementation_candidate_sha256") != sha256_file(IMPLEMENTATION_CANDIDATE)
        or payload.get("prepared_manifest_sha256") != adapter["frozen_prepared_manifest"]["sha256"]
        or payload.get("runtime_preflight") != payload.get("runtime_postflight")
        or payload.get("neural_training_run") is not False
        or payload.get("checkpoint_created") is not False
        or payload.get("optimizer_created") is not False
        or auth.get("gpu_uuid") != payload.get("runtime_preflight", {}).get("gpu_uuid")
    ):
        raise RuntimeError("science cache identity drift")
    expected_ids = [str(row["row_id"]) for row in bundle["rows"]]
    observed = [json.loads(line)["row_id"] for line in (root / "row_ids.jsonl").read_text().splitlines() if line]
    array = np.load(root / "activations.float32.npy", mmap_mode="r", allow_pickle=False)
    if observed != expected_ids or array.shape != (len(expected_ids), 768) or array.dtype != np.float32 or not np.isfinite(array).all():
        raise RuntimeError("science cache row/array drift")
    if canonical_array_hash(np.asarray(array)) != payload.get("canonical_array_sha256"):
        raise RuntimeError("science cache hash/authorization drift")
    return payload


def extract(source: str, signing_key: Path) -> dict[str, Any]:
    _assert_not_terminal(); auth = _authorization(); adapter = verify_frozen_contract(); _, prescore, manifest = _context()
    final = _cache_root(source)
    with exclusive_lock("stage-science-" + source):
        with lifecycle_lock():
            _assert_not_terminal(); auth = _authorization()
            if source == "GUM":
                verify_cache("EWT")
            if final.exists():
                return verify_cache(source)
            bundle = frozen_load_source_bundle(prescore, manifest, source)
            config = copy.deepcopy(read_json(MODEL_CONFIG)); config["runtime"]["gpu_uuid"] = auth["gpu_uuid"]
            device = torch.device("cuda:0")
            stage = new_staging("science-" + source, sha256_file(SCIENCE_AUTHORIZATION))
        with exclusive_lock("attempt-wide-gpu"):
            _assert_not_terminal(); _authorization()
            runtime._seed_runtime(20260803); model = runtime._load_model(config, device)
            pre = runtime._runtime_attestation(model, device, config); started = time.time()
            values = frozen_forward_units(model, bundle["units"], device=device, hidden_index=4, batch_size=64)
            post = runtime._runtime_attestation(model, device, config)
        if values.shape != (len(bundle["rows"]), 768) or values.dtype != np.float32 or not np.isfinite(values).all() or pre != post:
            raise RuntimeError("science extraction output/runtime drift")
        np.save(stage / "activations.float32.npy", np.ascontiguousarray(values), allow_pickle=False)
        atomic_jsonl(stage / "row_ids.jsonl", ({"row_id": str(row["row_id"])} for row in bundle["rows"]))
        artifacts = {path.name: {"bytes": path.stat().st_size, "sha256": sha256_file(path)} for path in stage.iterdir()}
        payload = {
            "schema_version": "atlas_rope_v7_attempt11_science_activation_v1", "status": "COMPLETE", "source": source,
            "rows": len(bundle["rows"]), "units": len(bundle["units"]), "width": 768,
            "model": adapter["model"], "hidden_state_index": 4, "batch_size": 64,
            "canonical_array_sha256": canonical_array_hash(values), "science_authorization_sha256": sha256_file(SCIENCE_AUTHORIZATION),
            "implementation_candidate_sha256": sha256_file(IMPLEMENTATION_CANDIDATE), "prepared_manifest_sha256": adapter["frozen_prepared_manifest"]["sha256"],
            "runtime_preflight": pre, "runtime_postflight": post, "elapsed_seconds": time.time() - started,
            "model_eval": True, "inference_mode": True, "requires_grad": False, "optimizer_created": False,
            "checkpoint_created": False, "neural_training_run": False, "artifacts": artifacts,
        }
        with lifecycle_lock():
            _assert_not_terminal(); _authorization()
            write_signed(stage / "COMPLETE.json", payload, signing_key.resolve(strict=True)); promote(stage, final)
            return verify_cache(source)


def _panel_payloads() -> dict[str, dict[str, Any]]:
    return {panel: verify_envelope(read_json(RUN_ROOT / "validation" / panel / "COMPLETE.json")) for panel in PANEL_NAMES}


def _qa_payload(source: str) -> dict[str, Any]:
    panels = _panel_payloads()
    rendered: dict[str, Any] = {}
    maximum_abs = 0.0
    maximum_ratio = 0.0
    for panel, payload in panels.items():
        cells = payload["score"]["cells"]
        value = max(float(row["maxima"]["absolute_difference"] or 0.0) for row in cells.values())
        ratio = max(float(row["maxima"]["coordinate_bound_ratio"] or 0.0) for row in cells.values())
        maximum_abs = max(maximum_abs, value)
        maximum_ratio = max(maximum_ratio, ratio)
        stat = {"status": "PASS" if payload["integrity_runtime_pass"] else "FAIL", "rows": 1200,
                "max_abs_error": value, "max_bound_ratio": ratio,
                "attempt11_approximate_equivariance_pass": payload["approximate_equivariance_pass"]}
        rendered[panel] = {"uniform_shift": stat, "prefix_position_only": dict(stat)}
    return {
        "schema_version": "atlas_rope_v7_attempt11_science_qa_bridge_v1", "status": "PASS", "source": source,
        "tolerance": {"atol": 2e-5, "rtol": 5e-6, "max_abs_repeat_error": 0.0, "status": "valid"},
        "panels": rendered, "maximum_abs_error": maximum_abs, "maximum_bound_ratio": maximum_ratio,
        "cross_panel": verify_envelope(read_json(SCIENCE_AUTHORIZATION))["cross_panel"],
        "science_authorization_sha256": sha256_file(SCIENCE_AUTHORIZATION), "neural_training_authorized": False,
    }


def _qa_path(source: str) -> Path:
    return SCIENCE_ROOT / "numerical_qa" / source / "QA_COMPLETE.json"


def make_qa(source: str, signing_key: Path) -> dict[str, Any]:
    _assert_not_terminal(); _authorization(); path = _qa_path(source)
    with exclusive_lock("stage-science-qa-" + source):
        with lifecycle_lock():
            _assert_not_terminal(); _authorization(); expected = _qa_payload(source)
            if not path.exists():
                write_signed(path, expected, signing_key.resolve(strict=True))
            return verify_qa(source)


def verify_qa(source: str) -> dict[str, Any]:
    _assert_not_terminal(); _authorization(); path = _qa_path(source)
    observed = verify_envelope(read_json(path))
    if observed != _qa_payload(source):
        raise RuntimeError("QA bridge drift")
    return {"payload": observed, "signature": read_json(path)["signature"]}


def _effective_context() -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    scoring, prescore, manifest = _context()
    scoring = json.loads(json.dumps(scoring)); prescore = json.loads(json.dumps(prescore))
    scoring["_resolved_sha256"] = sha256_file(FROZEN_ADAPTER)
    scoring["analysis"] = verify_frozen_contract()["frozen_analysis_settings"]
    prescore["run_root"] = str(SCIENCE_ROOT.relative_to(ROOT))
    return scoring, prescore, manifest


def verify_result() -> dict[str, Any]:
    _assert_not_terminal(); _authorization()
    cache_payloads = {source: verify_cache(source) for source in ("EWT", "GUM")}
    qa_payloads = {source: verify_qa(source) for source in ("EWT", "GUM")}
    entries = list(RESULT_ROOT.iterdir())
    expected_names = {"COMPLETE.json", "frozen_result.json", "technical_eligibility_overlay.json", "report.md", "lineage.json"}
    if {path.name for path in entries} != expected_names or any(not path.is_file() or path.is_symlink() for path in entries):
        raise RuntimeError("Attempt-11 science result allowlist drift")
    complete = verify_envelope(read_json(RESULT_ROOT / "COMPLETE.json"))
    artifacts = {
        name: {"bytes": (RESULT_ROOT / name).stat().st_size, "sha256": sha256_file(RESULT_ROOT / name)}
        for name in sorted(expected_names - {"COMPLETE.json"})
    }
    result = read_json(RESULT_ROOT / "frozen_result.json")
    overlay = read_json(RESULT_ROOT / "technical_eligibility_overlay.json")
    lineage = read_json(RESULT_ROOT / "lineage.json")
    expected_overlay = make_eligibility_overlay(result, _panel_payloads(), artifact_lineage_valid=True)
    if (
        complete.get("schema_version") != "atlas_rope_v7_attempt11_science_complete_v1"
        or complete.get("status") != "COMPLETE"
        or complete.get("artifacts") != artifacts
        or complete.get("architecture_promotion_status") != overlay.get("architecture_promotion_status")
        or complete.get("frozen_outcome") != result.get("outcome")
        or complete.get("frozen_result_mutated") is not False
        or complete.get("promotion_from_frozen_result_alone_authorized") is not False
        or complete.get("science_authorization_sha256") != sha256_file(SCIENCE_AUTHORIZATION)
        or complete.get("frozen_adapter_sha256") != sha256_file(FROZEN_ADAPTER)
        or complete.get("implementation_candidate_sha256") != sha256_file(IMPLEMENTATION_CANDIDATE)
        or complete.get("neural_training_run") is not False
    ):
        raise RuntimeError("Attempt-11 science completion lineage drift")
    if (
        result.get("schema_version") != "atlas_discovery_v3_3_attempt7_result_v2"
        or result.get("status") not in {"COMPLETE", "TERMINAL_TECHNICALLY_INELIGIBLE"}
        or result.get("neural_training_run") is not False
        or lineage != result.get("lineage")
        or overlay != expected_overlay
    ):
        raise RuntimeError("frozen science result/overlay drift")
    qa_hashes = lineage.get("qa_complete_sha256", {})
    activation_hashes = lineage.get("activation_complete_sha256", {})
    _, _, prepared_manifest = _context()
    prepared_root = ROOT / verify_frozen_contract()["frozen_prepared_manifest"]["path"]
    prepared_root = prepared_root.parent
    expected_prepared_inventory: dict[str, dict[str, str]] = {}
    for source in ("EWT", "GUM"):
        source_root = prepared_root / source
        expected_prepared_inventory[source] = {}
        expected_labels = {f"tasks/{task}" for task in prepared_manifest["sources"][source]["tasks"] if task != "pair_distance"}
        expected_labels |= {"pair_rows", "relation_rows", "cross_family_rows"}
        observed_labels = set(lineage.get("verified_analysis_child_inventory", {}).get(source, {}))
        if observed_labels != expected_labels:
            raise RuntimeError("science result prepared-child inventory membership drift")
        for label in sorted(expected_labels):
            relative = Path(label + ".jsonl")
            expected_prepared_inventory[source][label] = sha256_file(source_root / relative)
    if (
        qa_hashes != {source: sha256_file(_qa_path(source)) for source in ("EWT", "GUM")}
        or activation_hashes != {source: sha256_file(_cache_root(source) / "COMPLETE.json") for source in ("EWT", "GUM")}
        or lineage.get("verified_analysis_child_inventory") != expected_prepared_inventory
        or any(payload.get("science_authorization_sha256") != sha256_file(SCIENCE_AUTHORIZATION) for payload in cache_payloads.values())
        or any(envelope["payload"].get("science_authorization_sha256") != sha256_file(SCIENCE_AUTHORIZATION) for envelope in qa_payloads.values())
    ):
        raise RuntimeError("science result activation/QA lineage drift")
    report = (RESULT_ROOT / "report.md").read_text(encoding="utf-8")
    if not report.startswith("# Attempt 11 exploratory atlas") or "The frozen result alone is non-promotable" not in report:
        raise RuntimeError("Attempt-11 report interpretation boundary drift")
    return complete


def run_analysis(signing_key: Path) -> dict[str, Any]:
    _assert_not_terminal(); _authorization(); verify_cache("EWT"); verify_cache("GUM"); make_qa("EWT", signing_key); make_qa("GUM", signing_key)
    with exclusive_lock("stage-science-analysis"):
        with lifecycle_lock():
            _assert_not_terminal(); _authorization(); verify_cache("EWT"); verify_cache("GUM"); verify_qa("EWT"); verify_qa("GUM")
            if RESULT_ROOT.exists():
                return verify_result()
            scoring, prescore, manifest = _effective_context()
            original_loader, original_cache, original_qa = frozen.load_scoring_config, frozen._verify_complete_cache, frozen._verify_qa
            stage = new_staging("science-analysis", sha256_file(SCIENCE_AUTHORIZATION))
        try:
            frozen.load_scoring_config = lambda path: (scoring, prescore, manifest)
            frozen._verify_complete_cache = lambda final, cfg, pre, bundle, source: verify_cache(source)
            frozen._verify_qa = lambda path, cfg, source: verify_qa(source)
            with exclusive_lock("attempt-wide-gpu"):
                _assert_not_terminal(); _authorization(); started = time.time(); result = frozen.run(FROZEN_ADAPTER)
        finally:
            frozen.load_scoring_config, frozen._verify_complete_cache, frozen._verify_qa = original_loader, original_cache, original_qa
        panels = _panel_payloads(); overlay = make_eligibility_overlay(result, panels, artifact_lineage_valid=True)
        atomic_json(stage / "frozen_result.json", result); atomic_json(stage / "technical_eligibility_overlay.json", overlay)
        frozen_report = frozen._render_markdown(result)
        report = (
            "# Attempt 11 exploratory atlas\n\n"
            f"**Architecture promotion status: `{overlay['architecture_promotion_status']}`.**\n\n"
            "The frozen result alone is non-promotable. This report binds the separate technical-eligibility overlay.\n\n"
            f"- Baseline runtime: `{overlay['cross_panel']['baseline_runtime_pass']}`\n"
            f"- RoPE translation: `{overlay['cross_panel']['rope_translation_pass']}`\n"
            f"- Frozen outcome (unmodified): `{overlay['frozen_outcome']}`\n\n---\n\n" + frozen_report
        )
        (stage / "report.md").write_text(report, encoding="utf-8")
        atomic_json(stage / "lineage.json", result["lineage"])
        artifacts = {path.name: {"bytes": path.stat().st_size, "sha256": sha256_file(path)} for path in stage.iterdir()}
        payload = {
            "schema_version": "atlas_rope_v7_attempt11_science_complete_v1", "status": "COMPLETE",
            "architecture_promotion_status": overlay["architecture_promotion_status"], "frozen_outcome": result["outcome"],
            "frozen_result_mutated": False, "promotion_from_frozen_result_alone_authorized": False,
            "science_authorization_sha256": sha256_file(SCIENCE_AUTHORIZATION),
            "frozen_adapter_sha256": sha256_file(FROZEN_ADAPTER), "implementation_candidate_sha256": sha256_file(IMPLEMENTATION_CANDIDATE),
            "elapsed_seconds": time.time() - started, "neural_training_run": False, "artifacts": artifacts,
        }
        with lifecycle_lock():
            _assert_not_terminal(); _authorization(); verify_cache("EWT"); verify_cache("GUM"); verify_qa("EWT"); verify_qa("GUM")
            write_signed(stage / "COMPLETE.json", payload, signing_key.resolve(strict=True)); promote(stage, RESULT_ROOT)
            return verify_result()


def main() -> None:
    parser = argparse.ArgumentParser(); parser.add_argument("stage", choices=("verify", "extract-ewt", "extract-gum", "analyze")); parser.add_argument("--signing-key", type=Path); args = parser.parse_args()
    if args.stage == "verify": result = verify_frozen_contract()
    else:
        if not args.signing_key: raise RuntimeError("signing key required")
        result = extract("EWT", args.signing_key) if args.stage == "extract-ewt" else extract("GUM", args.signing_key) if args.stage == "extract-gum" else run_analysis(args.signing_key)
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
