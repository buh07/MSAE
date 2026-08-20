#!/usr/bin/env python3
"""One-shot Attempt-13 extraction, analysis, and terminal lifecycle."""
from __future__ import annotations

import argparse
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

from extract_atlas_discovery_v3_3 import _forward_units
import run_atlas_rope_v5 as runtime
from analyze_atlas_relation_context_v9 import analyze
from atlas_relation_context_v9 import (
    AUTHORIZATION,
    CANDIDATE_REVIEW,
    CONFIG,
    FINAL_FREEZE_ENVELOPE,
    FINAL_FREEZE_PAYLOAD,
    PREPARED_ROOT,
    RESULT_ROOT,
    ROOT,
    RUN_ROOT,
    assert_attempt12_inventory,
    atomic_json,
    atomic_jsonl,
    consume_study_key,
    inventory_digest,
    load_signing_key,
    opening_path,
    read_json,
    read_jsonl,
    reconcile_frozen_tree,
    recursive_inventory,
    sha256_file,
    sign_payload,
    study_key,
    verify_candidate_review,
    verify_detached,
    verify_signed,
)


SOURCES = ("GENTLE", "CTETEX")


def _require_canonical_config(config_path: Path) -> None:
    if config_path.resolve(strict=True) != CONFIG.resolve(strict=True):
        raise RuntimeError("Attempt-13 requires the canonical frozen config path")


def _verify_config(config: Mapping[str, Any]) -> None:
    for section in ("protocol", "relation_delta", "historical_exposure", "attempt12_inventory", "dependencies"):
        if section == "relation_delta":
            path, expected = config[section]["calibration_path"], config[section]["calibration_sha256"]
        elif section == "historical_exposure":
            for key in ("payload", "envelope"):
                path = ROOT / config[section][f"{key}_path"]
                if sha256_file(path) != config[section][f"{key}_sha256"]:
                    raise RuntimeError(f"{key} historical exposure drift")
            verify_detached(
                ROOT / config[section]["payload_path"],
                ROOT / config[section]["envelope_path"],
                expected_public_fingerprint=config["signer"]["public_key_fingerprint_sha256"],
            )
            continue
        else:
            path, expected = config[section]["path"], config[section]["sha256"]
        if sha256_file(ROOT / path) != expected:
            raise RuntimeError(f"config lineage drift: {section}")
    for source, spec in config["sources"].items():
        if sha256_file(ROOT / spec["path"]) != spec["sha256"]:
            raise RuntimeError(f"source lineage drift: {source}")
    if any(
        config.get(key) is not False
        for key in ("neural_training_authorized", "representation_training_authorized", "fitted_probe_persistence_authorized", "retry_authorized")
    ):
        raise RuntimeError("forbidden training/retry permission")


def _verify_freeze(config: Mapping[str, Any]) -> dict[str, Any]:
    freeze = read_json(FINAL_FREEZE_PAYLOAD)
    verify_detached(
        FINAL_FREEZE_PAYLOAD,
        FINAL_FREEZE_ENVELOPE,
        expected_public_fingerprint=config["signer"]["public_key_fingerprint_sha256"],
    )
    if freeze.get("status") != "FROZEN_FOR_ADVERSARIAL_REVIEW" or freeze.get("study_key") != study_key(config):
        raise RuntimeError("final-freeze identity drift")
    config_sha = sha256_file(CONFIG)
    candidate_config = [
        entry for entry in freeze["candidate_entries"] if entry["path"] == CONFIG.relative_to(ROOT).as_posix()
    ]
    if (
        freeze.get("config_sha256") != config_sha
        or len(candidate_config) != 1
        or candidate_config[0].get("sha256") != config_sha
    ):
        raise RuntimeError("canonical config is not exactly bound to the final freeze")
    for entry in freeze["candidate_entries"]:
        path = ROOT / entry["path"]
        if not path.is_file() or path.is_symlink() or path.stat().st_size != entry["bytes"] or sha256_file(path) != entry["sha256"]:
            raise RuntimeError(f"frozen candidate drift: {entry['path']}")
    if inventory_digest(freeze["candidate_entries"]) != freeze.get("candidate_inventory_sha256"):
        raise RuntimeError("frozen candidate inventory digest drift")
    return freeze


def _verify_freeze_and_authorization(config: Mapping[str, Any]) -> dict[str, Any]:
    freeze = _verify_freeze(config)
    review = verify_candidate_review(CANDIDATE_REVIEW, freeze)
    reconcile_frozen_tree(freeze, stage="preopening")
    authorization = verify_signed(AUTHORIZATION, expected_public_fingerprint=config["signer"]["public_key_fingerprint_sha256"])
    if (
        authorization.get("status") != "AUTHORIZED_ONE_SHOT"
        or authorization.get("study_key") != study_key(config)
        or authorization.get("final_freeze_payload_sha256") != sha256_file(FINAL_FREEZE_PAYLOAD)
        or authorization.get("candidate_review_sha256") != sha256_file(CANDIDATE_REVIEW)
        or authorization.get("candidate_review_verdict") != "SHIP"
        or authorization.get("candidate_inventory_sha256") != review["CANDIDATE_INVENTORY_SHA256"]
        or authorization.get("config_sha256") != freeze["config_sha256"]
        or authorization.get("prepared_manifest_sha256") != freeze["prepared_manifest_sha256"]
        or authorization.get("protocol_sha256") != config["protocol"]["sha256"]
        or authorization.get("gpu_physical_index") != config["runtime"]["physical_gpu_index"]
        or authorization.get("gpu_uuid") != config["runtime"]["gpu_uuid"]
        or authorization.get("primary_relation_prescore_eligible") is not True
        or authorization.get("secondary_prescore_ineligible") is not True
        or authorization.get("endpoint_outcome_naive") is not True
        or authorization.get("exploratory") is not True
        or authorization.get("no_retry_authorized") is not True
        or authorization.get("retry_authorized") is not False
        or authorization.get("neural_training_authorized") is not False
        or authorization.get("representation_training_authorized") is not False
    ):
        raise RuntimeError("science authorization drift")
    if opening_path(config).exists():
        raise RuntimeError("global study key already consumed")
    return authorization


def authorize(config_path: Path, key_path: Path) -> dict[str, Any]:
    """Create the one-shot authorization only after independently reviewed gates pass."""
    _require_canonical_config(config_path)
    config = read_json(config_path)
    _verify_config(config)
    private = load_signing_key(key_path, config["signer"])
    if AUTHORIZATION.exists() or RUN_ROOT.exists() or RESULT_ROOT.exists() or opening_path(config).exists():
        raise RuntimeError("authorization or lifecycle namespace already exists")
    inventory = read_json(ROOT / config["attempt12_inventory"]["path"])
    assert_attempt12_inventory(inventory)
    freeze = _verify_freeze(config)
    review = verify_candidate_review(CANDIDATE_REVIEW, freeze)
    reconciliation = reconcile_frozen_tree(freeze, stage="preauthorization")
    payload = {
        "schema_version": "atlas_relation_context_v9_attempt13_science_authorization_v1",
        "status": "AUTHORIZED_ONE_SHOT",
        "study_key": study_key(config),
        "final_freeze_payload_sha256": review["FINAL_FREEZE_PAYLOAD_SHA256"],
        "candidate_inventory_sha256": review["CANDIDATE_INVENTORY_SHA256"],
        "candidate_review_sha256": sha256_file(CANDIDATE_REVIEW),
        "candidate_review_verdict": review["verdict"],
        "config_sha256": sha256_file(config_path),
        "prepared_manifest_sha256": sha256_file(PREPARED_ROOT / "manifest.json"),
        "protocol_sha256": config["protocol"]["sha256"],
        "gpu_physical_index": config["runtime"]["physical_gpu_index"],
        "gpu_uuid": config["runtime"]["gpu_uuid"],
        "reconciliation": reconciliation,
        "primary_relation_prescore_eligible": True,
        "secondary_prescore_ineligible": True,
        "endpoint_outcome_naive": True,
        "exploratory": True,
        "no_retry_authorized": True,
        "retry_authorized": False,
        "neural_training_authorized": False,
        "representation_training_authorized": False,
        "authorized_unix": time.time(),
    }
    sign_payload(AUTHORIZATION, payload, private)
    verified = verify_signed(
        AUTHORIZATION,
        expected_public_fingerprint=config["signer"]["public_key_fingerprint_sha256"],
    )
    if verified != payload:
        raise RuntimeError("authorization round-trip verification drift")
    return payload


def _runtime_attestation(config: Mapping[str, Any]) -> dict[str, Any]:
    if not torch.cuda.is_available() or torch.cuda.device_count() != 1:
        raise RuntimeError("runner requires exactly one visible CUDA device")
    visible_uuid = torch.cuda.get_device_properties(0).uuid
    rendered = f"GPU-{visible_uuid}" if not str(visible_uuid).startswith("GPU-") else str(visible_uuid)
    if rendered != config["runtime"]["gpu_uuid"]:
        raise RuntimeError(f"GPU UUID drift: {rendered}")
    if os.environ.get("CUDA_VISIBLE_DEVICES") != str(config["runtime"]["physical_gpu_index"]):
        raise RuntimeError("physical/visible GPU mapping drift")
    return {
        "physical_gpu_index": config["runtime"]["physical_gpu_index"],
        "gpu_uuid": rendered,
        "visible_device_count": torch.cuda.device_count(),
        "torch_version": torch.__version__,
        "cuda_version": torch.version.cuda,
        "cublas_workspace_config": os.environ.get("CUBLAS_WORKSPACE_CONFIG"),
    }


def _prepared(source: str) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    units = read_jsonl(PREPARED_ROOT / source / "inference_units.jsonl")
    rows = read_jsonl(PREPARED_ROOT / source / "activation_rows.jsonl")
    flattened = [row_id for unit in units for row_id in unit["row_ids"]]
    if flattened != [row["row_id"] for row in rows]:
        raise RuntimeError(f"prepared row/unit ordering drift: {source}")
    return units, rows


def _write_cache(
    model: Any, source: str, config: Mapping[str, Any], private: Any, device: torch.device
) -> dict[str, Any]:
    root = RUN_ROOT / "activations" / source
    if root.exists():
        raise RuntimeError(f"cache already exists: {source}")
    units, rows = _prepared(source); started = time.time()
    values = _forward_units(
        model,
        units,
        device=device,
        hidden_index=int(config["model"]["hidden_state_index"]),
        batch_size=int(config["model"]["batch_size"]),
    )
    if values.shape != (len(rows), int(config["model"]["width"])) or values.dtype != np.float32 or not np.isfinite(values).all():
        raise RuntimeError(f"invalid extracted activations: {source}")
    root.mkdir(parents=True, exist_ok=False)
    np.save(root / "activations.float32.npy", np.ascontiguousarray(values), allow_pickle=False)
    atomic_jsonl(root / "row_ids.jsonl", ({"row_id": row["row_id"]} for row in rows))
    payload = {
        "schema_version": "atlas_relation_context_v9_attempt13_activation_v1",
        "status": "COMPLETE",
        "source": source,
        "rows": len(rows),
        "width": int(config["model"]["width"]),
        "array_sha256": sha256_file(root / "activations.float32.npy"),
        "row_ids_sha256": sha256_file(root / "row_ids.jsonl"),
        "elapsed_seconds": time.time() - started,
        "model_eval": True,
        "inference_mode": True,
        "requires_grad": False,
        "neural_training_run": False,
        "representation_training_run": False,
        "optimizer_created": False,
        "checkpoint_created": False,
        "study_key": study_key(config),
    }
    sign_payload(root / "COMPLETE.json", payload, private)
    verify_signed(
        root / "COMPLETE.json",
        expected_public_fingerprint=config["signer"]["public_key_fingerprint_sha256"],
    )
    return payload


def _inventory(root: Path, *, exclude: tuple[str, ...] = ()) -> dict[str, Any]:
    entries = recursive_inventory(root, exclude=exclude)
    return {"entries": entries, "digest": inventory_digest(entries)}


def execute(config_path: Path, key: Path) -> dict[str, Any]:
    _require_canonical_config(config_path)
    config = read_json(config_path); _verify_config(config)
    # Key identity and type must fail before RUN_ROOT or the global opening can exist.
    private = load_signing_key(key, config["signer"])
    inventory = read_json(ROOT / config["attempt12_inventory"]["path"]); assert_attempt12_inventory(inventory)
    authorization = _verify_freeze_and_authorization(config); runtime_pre = _runtime_attestation(config)
    if RUN_ROOT.exists() or RESULT_ROOT.exists():
        raise RuntimeError("Attempt-13 run/result namespace already exists")
    RUN_ROOT.mkdir(parents=True, exist_ok=False)
    consumed: Path | None = None
    try:
        started_payload = {
            "schema_version": "atlas_relation_context_v9_attempt13_started_v1",
            "status": "STARTING_GLOBAL_STUDY_KEY_CONSUMPTION",
            "study_key": study_key(config),
            "authorization_sha256": sha256_file(AUTHORIZATION),
            "runtime": runtime_pre,
            "started_unix": time.time(),
            "no_retry_authorized": True,
        }
        sign_payload(RUN_ROOT / "STARTED.json", started_payload, private)
        verify_signed(
            RUN_ROOT / "STARTED.json",
            expected_public_fingerprint=config["signer"]["public_key_fingerprint_sha256"],
        )
        consumed = consume_study_key(
            config,
            {
                "schema_version": "atlas_relation_context_v9_global_opening_v1",
                "status": "SCIENTIFIC_OPENING_CONSUMED",
                "study_key": study_key(config),
                "authorization_sha256": sha256_file(AUTHORIZATION),
                "final_freeze_payload_sha256": sha256_file(FINAL_FREEZE_PAYLOAD),
                "source_sha256": {source: config["sources"][source]["sha256"] for source in SOURCES},
                "model": config["model"],
                "consumed_unix": time.time(),
                "retry_authorized": False,
            },
        )
        assert consumed is not None
        runtime._seed_runtime(int(config["seed"])); device = torch.device("cuda:0")
        model_config = {
            "model": config["model"],
            "runtime": {"gpu_uuid": config["runtime"]["gpu_uuid"]},
        }
        model = runtime._load_model(model_config, device)
        model.eval(); torch.set_grad_enabled(False)
        cache_complete_sha256: dict[str, str] = {}
        for source in SOURCES:
            _write_cache(model, source, config, private, device)
            cache_complete_sha256[source] = sha256_file(RUN_ROOT / "activations" / source / "COMPLETE.json")
        del model; torch.cuda.empty_cache()
        result = analyze(config_path)
        result_complete = {
            "schema_version": "atlas_relation_context_v9_attempt13_result_complete_v1",
            "status": "COMPLETE",
            "result_sha256": sha256_file(RESULT_ROOT / "result.json"),
            "report_sha256": sha256_file(RESULT_ROOT / "report.md"),
            "activation_complete_sha256": cache_complete_sha256,
            "run_inventory_before_result_completion": _inventory(RUN_ROOT),
            "result_inventory_excluding_complete": _inventory(RESULT_ROOT, exclude=("COMPLETE.json",)),
            "decision": result["decision"],
            "training_authorized": False,
            "neural_training_run": False,
            "fit_source_component_uncertainty": "intervals_condition_on_each_ephemeral_fitted_ridge_model",
        }
        sign_payload(RESULT_ROOT / "COMPLETE.json", result_complete, private)
        verify_signed(
            RESULT_ROOT / "COMPLETE.json",
            expected_public_fingerprint=config["signer"]["public_key_fingerprint_sha256"],
        )
        assert_attempt12_inventory(inventory)
        terminal = {
            "schema_version": "atlas_relation_context_v9_attempt13_terminal_v1",
            "status": "TERMINAL_COMPLETE",
            "study_key": study_key(config),
            "consumed_record_path": str(consumed.relative_to(ROOT)),
            "consumed_record_sha256": sha256_file(consumed),
            "result_complete_sha256": sha256_file(RESULT_ROOT / "COMPLETE.json"),
            "activation_complete_sha256": cache_complete_sha256,
            "run_inventory_excluding_terminal": _inventory(RUN_ROOT, exclude=("TERMINAL.json",)),
            "result_inventory": _inventory(RESULT_ROOT),
            "decision": result["decision"],
            "runtime_preflight": runtime_pre,
            "runtime_postflight": _runtime_attestation(config),
            "attempt12_unchanged": True,
            "no_retry_authorized": True,
            "neural_training_run": False,
            "representation_training_run": False,
            "optimizer_created": False,
            "checkpoint_created": False,
        }
        sign_payload(RUN_ROOT / "TERMINAL.json", terminal, private)
        verify_signed(
            RUN_ROOT / "TERMINAL.json",
            expected_public_fingerprint=config["signer"]["public_key_fingerprint_sha256"],
        )
        return terminal
    except BaseException as error:
        consumed_record = consumed if consumed is not None else opening_path(config)
        opened = consumed_record.is_file()
        failure = {
            "schema_version": "atlas_relation_context_v9_attempt13_terminal_v1",
            "status": (
                "TERMINAL_FAILED_AFTER_SCIENTIFIC_OPENING"
                if opened
                else "TERMINAL_FAILED_BEFORE_SCIENTIFIC_OPENING"
            ),
            "study_key": study_key(config),
            "error_type": type(error).__name__,
            "error": str(error),
            "scientific_opening_consumed": opened,
            "run_inventory_excluding_terminal": _inventory(RUN_ROOT, exclude=("TERMINAL.json",)),
            "result_inventory_if_any": _inventory(RESULT_ROOT),
            "no_retry_authorized": True,
            "neural_training_run": False,
        }
        if opened:
            failure["consumed_record_path"] = str(consumed_record.relative_to(ROOT))
            failure["consumed_record_sha256"] = sha256_file(consumed_record)
        sign_payload(RUN_ROOT / "TERMINAL.json", failure, private)
        verify_signed(
            RUN_ROOT / "TERMINAL.json",
            expected_public_fingerprint=config["signer"]["public_key_fingerprint_sha256"],
        )
        raise


def main() -> None:
    parser = argparse.ArgumentParser(); parser.add_argument("--config", default=str(CONFIG.relative_to(ROOT))); parser.add_argument("--signing-key", required=True); parser.add_argument("--authorize-only", action="store_true"); args = parser.parse_args()
    config_path = (ROOT / args.config).resolve(strict=True)
    key_path = Path(args.signing_key).resolve(strict=True)
    output = authorize(config_path, key_path) if args.authorize_only else execute(config_path, key_path)
    print(json.dumps(output, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
