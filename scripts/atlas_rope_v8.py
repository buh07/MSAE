#!/usr/bin/env python3
"""Attempt-12 analysis-only recovery primitives.

This module verifies imported Attempt-11 artifacts and the physical/visible GPU
mapping.  It deliberately contains no model loader, forward path, extractor,
fresh-panel executor, optimizer, or neural-training entry point.
"""
from __future__ import annotations

import ast
import hashlib
import json
import os
import re
import subprocess
import tempfile
from pathlib import Path
from typing import Any, Mapping, Sequence

import numpy as np
import torch

from atlas_rope_v6 import (
    ROOT,
    canonical_json_bytes,
    inventory_digest,
    load_private_key,
    read_json,
    recursive_inventory,
    sha256_file,
    sign_payload,
    verify_envelope,
)

CONFIG_ROOT = ROOT / "configs/atlas_rope_v8"
RECOVERY_CONFIG = CONFIG_ROOT / "recovery.json"
IMPLEMENTATION_CANDIDATE = CONFIG_ROOT / "IMPLEMENTATION_CANDIDATE.json"
RECOVERY_FREEZE = CONFIG_ROOT / "RECOVERY_FREEZE.json"
AUTHORIZATION = CONFIG_ROOT / "RECOVERY_AUTHORIZATION.json"

RUN_ROOT = ROOT / "pilot_runs/20260803_atlas_rope_analysis_recovery_v8"
PREFLIGHT = RUN_ROOT / "provenance/PREFLIGHT.json"
STARTED = RUN_ROOT / "STARTED.json"
TERMINAL = RUN_ROOT / "TERMINAL.json"
RESULT_ROOT = ROOT / "results/atlas_rope_v8_attempt12_analysis_recovery"

ATTEMPT11_ROOT = ROOT / "pilot_runs/20260803_atlas_rope_technical_v7"
ATTEMPT11_TERMINAL = ATTEMPT11_ROOT / "TERMINAL.json"
ATTEMPT11_RESULT_ROOT = ROOT / "results/atlas_rope_v7_attempt11_science"
FROZEN_ADAPTER = ROOT / "configs/atlas_rope_v6/science_adapter.json"

ATTEMPT11_TERMINAL_SHA256 = "ad7fd3b4de265879737774df38220956a4947298f3122f37b207c2bea46285d1"
EXTRACTION_GPU_UUID = "GPU-9b529a09-92a6-caea-fee2-6b2bf07b0e4e"
ANALYSIS_GPU_UUID = "GPU-ec526219-fb07-e57e-a30d-5d2ab843fb15"
ANALYSIS_PHYSICAL_INDEX = 0
REQUIRED_VISIBLE_DEVICES = "0"
SOURCES = ("EWT", "GUM")
PANELS = ("ENGLISH_CHILDES_CTETEX", "CZECH_PDT")

IMPLEMENTATION_PATHS = (
    "PLAN_ATTEMPT12.md",
    "scripts/atlas_rope_v8.py",
    "scripts/atlas_rope_v8_analysis_shim.py",
    "scripts/run_atlas_rope_v8.py",
    "scripts/run_atlas_rope_v8_pipeline.sh",
    "scripts/launch_atlas_rope_v8_tmux.sh",
    "tests/test_atlas_rope_v8.py",
    "configs/atlas_rope_v8/recovery.json",
)
RUNTIME_OPERATION_PATHS = (
    "scripts/atlas_rope_v8.py",
    "scripts/atlas_rope_v8_analysis_shim.py",
    "scripts/run_atlas_rope_v8.py",
    "scripts/run_atlas_rope_v8_pipeline.sh",
    "scripts/launch_atlas_rope_v8_tmux.sh",
)


def file_record(path: Path) -> dict[str, Any]:
    resolved = path.resolve(strict=True)
    if path.is_symlink() or not resolved.is_file() or not resolved.is_relative_to(ROOT):
        raise RuntimeError(f"regular in-repository file required: {path}")
    return {"bytes": resolved.stat().st_size, "sha256": sha256_file(resolved)}


def file_inventory(paths: Sequence[str]) -> dict[str, dict[str, Any]]:
    return {raw: file_record(ROOT / raw) for raw in paths}


def _require_exact_file(raw: str, spec: Mapping[str, Any]) -> Path:
    relative = Path(raw)
    if relative.is_absolute() or ".." in relative.parts:
        raise RuntimeError(f"unsafe imported path: {raw}")
    path = ROOT / relative
    if file_record(path) != dict(spec):
        raise RuntimeError(f"imported file drift: {raw}")
    return path


def _attempt11_tree_digest() -> tuple[str, int]:
    inventory = recursive_inventory(ATTEMPT11_ROOT)
    return inventory_digest(inventory), len(inventory)


def verify_attempt11_terminal() -> dict[str, Any]:
    if sha256_file(ATTEMPT11_TERMINAL) != ATTEMPT11_TERMINAL_SHA256:
        raise RuntimeError("Attempt-11 terminal SHA drift")
    payload = verify_envelope(read_json(ATTEMPT11_TERMINAL))
    if (
        payload.get("schema_version") != "atlas_rope_v7_attempt11_terminal_v1"
        or payload.get("status") != "TERMINAL_PIPELINE_STAGE_FAILED"
        or payload.get("no_retry_authorized") is not True
        or payload.get("neural_training_authorized") is not False
        or payload.get("reason") != "Attempt-11 pipeline stage science_analysis_and_overlay failed with exit 1"
    ):
        raise RuntimeError("Attempt-11 terminal identity drift")
    if ATTEMPT11_RESULT_ROOT.exists():
        raise RuntimeError("Attempt-11 result namespace unexpectedly exists")
    return payload


def load_recovery_config() -> dict[str, Any]:
    config = read_json(RECOVERY_CONFIG)
    expected_namespaces = {
        "attempt11_run_root": str(ATTEMPT11_ROOT.relative_to(ROOT)),
        "attempt11_result_root": str(ATTEMPT11_RESULT_ROOT.relative_to(ROOT)),
        "attempt12_run_root": str(RUN_ROOT.relative_to(ROOT)),
        "attempt12_result_root": str(RESULT_ROOT.relative_to(ROOT)),
        "attempt12_tmux_session": "atlas_rope_v8_attempt12_20260803",
    }
    expected_gpu = {
        "extraction_gpu_uuid": EXTRACTION_GPU_UUID,
        "extraction_physical_index": 1,
        "analysis_gpu_uuid": ANALYSIS_GPU_UUID,
        "analysis_physical_index": ANALYSIS_PHYSICAL_INDEX,
        "analysis_visible_index": 0,
        "required_cuda_visible_devices": REQUIRED_VISIBLE_DEVICES,
    }
    permissions = config.get("permissions", {})
    if (
        config.get("schema_version") != "atlas_rope_v8_attempt12_analysis_recovery_v1"
        or config.get("status") != "FROZEN_BEFORE_SCIENTIFIC_OUTCOME"
        or config.get("claim_class") != "EXPLORATORY_ANALYSIS_ONLY_RECOVERY"
        or config.get("reuse_decision_frozen_before_outcome") is not True
        or config.get("scientific_protocol_changed") is not False
        or config.get("namespaces") != expected_namespaces
        or config.get("gpu_roles") != expected_gpu
        or config.get("analysis_attempts") != 1
        or config.get("retry_authorized") is not False
        or any(permissions.get(key) is not False for key in (
            "model_forward_authorized",
            "activation_extraction_authorized",
            "fresh_validation_authorized",
            "neural_training_authorized",
            "checkpoint_creation_authorized",
            "optimizer_authorized",
        ))
    ):
        raise RuntimeError("Attempt-12 recovery config identity/permission drift")
    if set(config.get("imported_files", {})) != set(config.get("prepared_source_files", {})) | set(config.get("fixed_lineage_files", {})):
        raise RuntimeError("recovery imported inventory membership drift")
    supersession = config.get("superseded_pre_authorization_candidate", {})
    supersession_path = ROOT / str(supersession.get("path", ""))
    if (
        not supersession_path.is_file()
        or supersession_path.is_symlink()
        or sha256_file(supersession_path) != supersession.get("sha256")
    ):
        raise RuntimeError("Attempt-12 pre-authorization supersession lineage drift")
    superseded_payload = verify_envelope(read_json(supersession_path))
    if (
        superseded_payload.get("status") != "SUPERSEDED_BEFORE_AUTHORIZATION"
        or superseded_payload.get("reviewed_recovery_freeze_sha256")
        != "435dbad80bb2f4567d28e556be5301d166b9781fca7819c7d92d3ef9423e3dad"
        or superseded_payload.get("authorization_created") is not False
        or superseded_payload.get("started_created") is not False
        or superseded_payload.get("scientific_scoring_performed") is not False
        or superseded_payload.get("successor_revision_authorized") is not True
    ):
        raise RuntimeError("Attempt-12 superseded candidate disposition drift")
    return config


def verify_frozen_adapter(config: Mapping[str, Any]) -> dict[str, Any]:
    adapter = read_json(FROZEN_ADAPTER)
    if file_record(FROZEN_ADAPTER) != config["fixed_lineage_files"][str(FROZEN_ADAPTER.relative_to(ROOT))]:
        raise RuntimeError("frozen adapter drift")
    analysis = adapter.get("frozen_analysis_settings", {})
    normalized = hashlib.sha256(json.dumps(analysis, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    if (
        adapter.get("schema_version") != "atlas_rope_v6_attempt10_science_adapter_v1"
        or adapter.get("status") != "FROZEN_BEFORE_HELDOUT_VALIDATION"
        or adapter.get("neural_training_authorized") is not False
        or analysis.get("ridge_device") != "cuda:0"
        or analysis.get("ridge_gpu_uuid") != ANALYSIS_GPU_UUID
        or normalized != adapter.get("frozen_analysis_settings_sha256")
    ):
        raise RuntimeError("frozen adapter analysis contract drift")
    for raw, expected in adapter.get("frozen_files", {}).items():
        if sha256_file(ROOT / raw) != expected:
            raise RuntimeError(f"frozen analyzer file drift: {raw}")
    for raw, expected in adapter.get("frozen_function_hashes", {}).items():
        if ast_function_hashes(ROOT / raw, set(expected)) != expected:
            raise RuntimeError(f"frozen analyzer function drift: {raw}")
    for key in ("frozen_scoring_config", "frozen_science_prescore", "frozen_prepared_manifest", "frozen_rebuild"):
        spec = adapter[key]
        if sha256_file(ROOT / str(spec["path"])) != spec["sha256"]:
            raise RuntimeError(f"frozen adapter lineage drift: {key}")
    return adapter


def ast_function_hashes(path: Path, names: set[str]) -> dict[str, str]:
    text = path.read_text(encoding="utf-8")
    lines = text.splitlines(keepends=True)
    tree = ast.parse(text, filename=str(path))
    output: dict[str, str] = {}
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name in names:
            segment = "".join(lines[node.lineno - 1 : node.end_lineno])
            output[node.name] = hashlib.sha256(segment.encode("utf-8")).hexdigest()
    if set(output) != names:
        raise RuntimeError(f"missing frozen functions: {path}: {sorted(names - set(output))}")
    return output


def verify_imported_files(config: Mapping[str, Any]) -> None:
    for raw, spec in config["imported_files"].items():
        _require_exact_file(str(raw), spec)
    digest, count = _attempt11_tree_digest()
    expected = config["attempt11_tree"]
    if digest != expected.get("inventory_sha256") or count != expected.get("entries"):
        raise RuntimeError("Attempt-11 tree inventory drift")


def _panel_path(panel: str) -> Path:
    return ATTEMPT11_ROOT / "validation" / panel / "COMPLETE.json"


def verify_validation(config: Mapping[str, Any]) -> dict[str, dict[str, Any]]:
    science_auth_path = ROOT / "configs/atlas_rope_v7/SCIENCE_AUTHORIZATION.json"
    science_auth = verify_envelope(read_json(science_auth_path))
    if (
        science_auth.get("status") != "AUTHORIZED"
        or science_auth.get("authorized_stage") != "EXPLORATORY_FROZEN_SCIENCE_WITH_ELIGIBILITY_OVERLAY"
        or science_auth.get("cross_panel") != {"baseline_runtime_pass": True, "rope_translation_pass": True}
        or science_auth.get("gpu_uuid") != EXTRACTION_GPU_UUID
        or science_auth.get("neural_training_authorized") is not False
    ):
        raise RuntimeError("Attempt-11 science authorization drift")
    panels: dict[str, dict[str, Any]] = {}
    for panel in PANELS:
        path = _panel_path(panel)
        payload = verify_envelope(read_json(path))
        if (
            payload.get("status") != "COMPLETE"
            or payload.get("panel") != panel
            or payload.get("integrity_runtime_pass") is not True
            or payload.get("approximate_equivariance_pass") is not True
            or payload.get("runtime_preflight") != payload.get("runtime_postflight")
            or payload.get("runtime_preflight", {}).get("gpu_uuid") != EXTRACTION_GPU_UUID
            or payload.get("neural_training_run") is not False
        ):
            raise RuntimeError(f"Attempt-11 validation panel drift: {panel}")
        panels[panel] = payload
    expected_hashes = {panel: sha256_file(_panel_path(panel)) for panel in PANELS}
    if science_auth.get("panel_complete_sha256") != expected_hashes:
        raise RuntimeError("Attempt-11 validation/science authorization lineage drift")
    return panels


def _prepared_root(adapter: Mapping[str, Any]) -> Path:
    return (ROOT / str(adapter["frozen_prepared_manifest"]["path"])).parent


def _jsonl_values(path: Path) -> list[dict[str, Any]]:
    output: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as handle:
        for number, line in enumerate(handle, 1):
            if not line.strip():
                continue
            value = json.loads(line)
            if not isinstance(value, dict):
                raise RuntimeError(f"non-object JSONL row: {path}:{number}")
            output.append(value)
    return output


def _canonical_array_hash_stream(array: np.ndarray) -> str:
    if not array.flags.c_contiguous:
        raise RuntimeError("cache array is not C contiguous")
    view = memoryview(array).cast("B")
    digest = hashlib.sha256()
    for start in range(0, len(view), 16 * 1024 * 1024):
        digest.update(view[start : start + 16 * 1024 * 1024])
    return digest.hexdigest()


def verify_cache(source: str, config: Mapping[str, Any] | None = None, adapter: Mapping[str, Any] | None = None) -> dict[str, Any]:
    if source not in SOURCES:
        raise RuntimeError("unknown recovery source")
    config = dict(config or load_recovery_config())
    adapter = dict(adapter or verify_frozen_adapter(config))
    manifest = read_json(ROOT / str(adapter["frozen_prepared_manifest"]["path"]))
    source_root = _prepared_root(adapter) / source
    units = _jsonl_values(source_root / "inference_units.jsonl")
    rows = _jsonl_values(source_root / "activation_rows.jsonl")
    flattened = [str(row_id) for unit in units for row_id in unit["row_ids"]]
    expected_ids = [str(row["row_id"]) for row in rows]
    if flattened != expected_ids or len(expected_ids) != len(set(expected_ids)):
        raise RuntimeError(f"prepared activation row lineage drift: {source}")

    cache_root = ATTEMPT11_ROOT / "science/activations" / source
    if {path.name for path in cache_root.iterdir()} != {"COMPLETE.json", "activations.float32.npy", "row_ids.jsonl"}:
        raise RuntimeError(f"Attempt-11 cache allowlist drift: {source}")
    complete_path = cache_root / "COMPLETE.json"
    payload = verify_envelope(read_json(complete_path))
    artifacts = {name: file_record(cache_root / name) for name in ("activations.float32.npy", "row_ids.jsonl")}
    if (
        payload.get("schema_version") != "atlas_rope_v7_attempt11_science_activation_v1"
        or payload.get("status") != "COMPLETE"
        or payload.get("source") != source
        or payload.get("artifacts") != artifacts
        or payload.get("prepared_manifest_sha256") != adapter["frozen_prepared_manifest"]["sha256"]
        or payload.get("science_authorization_sha256") != sha256_file(ROOT / "configs/atlas_rope_v7/SCIENCE_AUTHORIZATION.json")
        or payload.get("runtime_preflight") != payload.get("runtime_postflight")
        or payload.get("runtime_preflight", {}).get("gpu_uuid") != EXTRACTION_GPU_UUID
        or payload.get("neural_training_run") is not False
        or payload.get("optimizer_created") is not False
        or payload.get("checkpoint_created") is not False
    ):
        raise RuntimeError(f"Attempt-11 cache completion drift: {source}")
    observed_ids = [str(row["row_id"]) for row in _jsonl_values(cache_root / "row_ids.jsonl")]
    if observed_ids != expected_ids:
        raise RuntimeError(f"Attempt-11 cache/prepared row mismatch: {source}")
    array = np.load(cache_root / "activations.float32.npy", mmap_mode="r", allow_pickle=False)
    if array.dtype != np.float32 or array.shape != (len(expected_ids), 768) or not array.flags.c_contiguous:
        raise RuntimeError(f"Attempt-11 cache array structure drift: {source}")
    for start in range(0, len(array), 8192):
        if not np.isfinite(array[start : start + 8192]).all():
            raise RuntimeError(f"Attempt-11 cache contains nonfinite values: {source}")
    if _canonical_array_hash_stream(array) != payload.get("canonical_array_sha256"):
        raise RuntimeError(f"Attempt-11 cache canonical hash drift: {source}")
    return payload


def verify_qa(source: str, config: Mapping[str, Any] | None = None) -> dict[str, Any]:
    if source not in SOURCES:
        raise RuntimeError("unknown recovery QA source")
    config = config or load_recovery_config()
    path = ATTEMPT11_ROOT / "science/numerical_qa" / source / "QA_COMPLETE.json"
    envelope = read_json(path)
    payload = verify_envelope(envelope)
    if (
        payload.get("schema_version") != "atlas_rope_v7_attempt11_science_qa_bridge_v1"
        or payload.get("status") != "PASS"
        or payload.get("source") != source
        or payload.get("cross_panel") != {"baseline_runtime_pass": True, "rope_translation_pass": True}
        or payload.get("science_authorization_sha256") != sha256_file(ROOT / "configs/atlas_rope_v7/SCIENCE_AUTHORIZATION.json")
        or payload.get("neural_training_authorized") is not False
        or set(payload.get("panels", {})) != set(PANELS)
        or any(
            family.get("status") != "PASS"
            for panel in payload.get("panels", {}).values()
            for family in panel.values()
        )
    ):
        raise RuntimeError(f"Attempt-11 QA bridge drift: {source}")
    return envelope


def verify_all_imports(*, deep_cache: bool = True) -> dict[str, Any]:
    config = load_recovery_config()
    verify_attempt11_terminal()
    verify_imported_files(config)
    adapter = verify_frozen_adapter(config)
    panels = verify_validation(config)
    cache_payloads: dict[str, Any] = {}
    qa_hashes: dict[str, str] = {}
    for source in SOURCES:
        if deep_cache:
            cache_payloads[source] = verify_cache(source, config, adapter)
        qa = verify_qa(source, config)
        qa_hashes[source] = sha256_file(ATTEMPT11_ROOT / "science/numerical_qa" / source / "QA_COMPLETE.json")
        if qa["payload"].get("source") != source:
            raise RuntimeError("QA envelope source drift")
    return {
        "config_sha256": sha256_file(RECOVERY_CONFIG),
        "attempt11_terminal_sha256": sha256_file(ATTEMPT11_TERMINAL),
        "attempt11_tree_inventory_sha256": _attempt11_tree_digest()[0],
        "adapter_sha256": sha256_file(FROZEN_ADAPTER),
        "panel_complete_sha256": {panel: sha256_file(_panel_path(panel)) for panel in PANELS},
        "activation_complete_sha256": {
            source: sha256_file(ATTEMPT11_ROOT / "science/activations" / source / "COMPLETE.json") for source in SOURCES
        },
        "qa_complete_sha256": qa_hashes,
        "cross_panel": {"baseline_runtime_pass": True, "rope_translation_pass": True},
        "deep_cache_verified": deep_cache,
        "cache_rows": {source: int(payload["rows"]) for source, payload in cache_payloads.items()},
        "panel_names": sorted(panels),
    }


def _parse_nvidia_smi(text: str) -> dict[int, str]:
    output: dict[int, str] = {}
    for raw in text.splitlines():
        if not raw.strip():
            continue
        fields = [field.strip() for field in raw.split(",")]
        if len(fields) < 2 or not fields[0].isdigit() or not fields[1].startswith("GPU-"):
            raise RuntimeError(f"unparseable nvidia-smi row: {raw}")
        index = int(fields[0])
        if index in output:
            raise RuntimeError("duplicate physical GPU index")
        output[index] = fields[1]
    return output


def verify_gpu_mapping() -> dict[str, Any]:
    if os.environ.get("CUDA_VISIBLE_DEVICES") != REQUIRED_VISIBLE_DEVICES:
        raise RuntimeError("CUDA_VISIBLE_DEVICES must equal the frozen physical index '0'")
    command = ["nvidia-smi", "--query-gpu=index,uuid", "--format=csv,noheader"]
    result = subprocess.run(command, check=True, capture_output=True, text=True)
    physical = _parse_nvidia_smi(result.stdout)
    if physical.get(ANALYSIS_PHYSICAL_INDEX) != ANALYSIS_GPU_UUID:
        raise RuntimeError("physical GPU-0 UUID differs from frozen analysis UUID")
    if physical.get(1) != EXTRACTION_GPU_UUID:
        raise RuntimeError("physical GPU-1 UUID differs from imported extraction UUID")
    if not torch.cuda.is_available() or torch.cuda.device_count() != 1:
        raise RuntimeError("analysis process must see exactly one CUDA device")
    visible = str(torch.cuda.get_device_properties(0).uuid)
    if not visible.startswith("GPU-"):
        visible = "GPU-" + visible
    if visible != ANALYSIS_GPU_UUID:
        raise RuntimeError("visible cuda:0 does not resolve to frozen physical GPU 0")
    adapter = read_json(FROZEN_ADAPTER)
    analysis = adapter["frozen_analysis_settings"]
    if analysis.get("ridge_device") != "cuda:0" or analysis.get("ridge_gpu_uuid") != visible:
        raise RuntimeError("adapter/visible analysis GPU mapping drift")
    return {
        "cuda_visible_devices": REQUIRED_VISIBLE_DEVICES,
        "physical_index": ANALYSIS_PHYSICAL_INDEX,
        "physical_uuid": physical[ANALYSIS_PHYSICAL_INDEX],
        "extraction_physical_index": 1,
        "extraction_physical_uuid": physical[1],
        "visible_device_count": 1,
        "visible_index": 0,
        "visible_uuid": visible,
        "name": torch.cuda.get_device_name(0),
        "torch": torch.__version__,
        "cuda": torch.version.cuda,
        "cudnn": torch.backends.cudnn.version(),
    }


def static_operation_audit(paths: Sequence[str] = RUNTIME_OPERATION_PATHS) -> dict[str, Any]:
    forbidden_imports = {
        "transformers",
        "run_atlas_rope_v5",
        "run_atlas_rope_v7",
        "run_atlas_rope_v7_science",
        "extract_atlas_discovery_v3_3",
        "torch.optim",
        "torch.autograd",
    }
    forbidden_calls = {
        "_load_model",
        "_forward_units",
        "from_pretrained",
        "backward",
        "step",
        "zero_grad",
        "save_pretrained",
        "torch.save",
    }
    findings: list[dict[str, Any]] = []

    def dotted(node: ast.AST) -> str:
        if isinstance(node, ast.Name):
            return node.id
        if isinstance(node, ast.Attribute):
            prefix = dotted(node.value)
            return f"{prefix}.{node.attr}" if prefix else node.attr
        return ""

    for raw in paths:
        path = ROOT / raw
        if raw.endswith(".sh"):
            for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
                command = line.strip()
                if re.search(r"run_atlas_rope_v[457]_science|run-panel|extract-(ewt|gum)|train_msae|torchrun", command):
                    findings.append({"path": raw, "line": line_number, "construct": command})
            continue
        if not raw.endswith(".py"):
            continue
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                modules = [alias.name for alias in node.names]
            elif isinstance(node, ast.ImportFrom):
                modules = [str(node.module or "")]
            else:
                modules = []
            for module in modules:
                if module in forbidden_imports or any(module.startswith(name + ".") for name in forbidden_imports):
                    findings.append({"path": raw, "line": node.lineno, "construct": f"import {module}"})
            if isinstance(node, ast.Call):
                call = dotted(node.func)
                leaf = call.rsplit(".", 1)[-1]
                if call in forbidden_calls or leaf in forbidden_calls:
                    findings.append({"path": raw, "line": node.lineno, "construct": call})
    if findings:
        raise RuntimeError(f"forbidden Attempt-12 operation path: {findings}")
    return {
        "status": "PASS",
        "reviewed_paths": list(paths),
        "transitive_analysis_loader": runtime_dependency_audit(),
        "model_forward_path": False,
        "activation_extraction_path": False,
        "fresh_validation_path": False,
        "neural_training_path": False,
    }


def runtime_dependency_audit() -> dict[str, Any]:
    """Bind the safe extractor shim used to import the frozen analyzer.

    The frozen analyzer has a historical import from the extraction module.  The
    Attempt-12 loader installs this audited shim under that exact module name
    before importing the analyzer, so the legacy Transformers/model/CLI module is
    never loaded by the recovery process.
    """
    analyzer = ROOT / "scripts/analyze_atlas_discovery_v3_3.py"
    shim = ROOT / "scripts/atlas_rope_v8_analysis_shim.py"
    tree = ast.parse(analyzer.read_text(encoding="utf-8"), filename=str(analyzer))
    imported = {
        str(node.module or "")
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom)
    }
    if "extract_atlas_discovery_v3_3" not in imported:
        raise RuntimeError("frozen analyzer extractor import changed")
    shim_tree = ast.parse(shim.read_text(encoding="utf-8"), filename=str(shim))
    forbidden_modules = {"transformers", "torch.optim", "torch.autograd", "extract_atlas_discovery_v3_3"}
    for node in ast.walk(shim_tree):
        if isinstance(node, ast.Import):
            modules = [alias.name for alias in node.names]
        elif isinstance(node, ast.ImportFrom):
            modules = [str(node.module or "")]
        else:
            modules = []
        if any(module in forbidden_modules or any(module.startswith(name + ".") for name in forbidden_modules) for module in modules):
            raise RuntimeError(f"safe analysis shim imports forbidden module at line {node.lineno}")
    return {
        "status": "PASS",
        "frozen_analyzer_sha256": sha256_file(analyzer),
        "safe_shim_sha256": sha256_file(shim),
        "legacy_extractor_loaded": False,
        "transformers_loaded": False,
        "model_forward_callable_exposed": False,
        "extraction_cli_exposed": False,
    }


def safe_write_target(path: Path) -> Path:
    resolved = path.resolve(strict=False)
    allowed = (CONFIG_ROOT.resolve(), RUN_ROOT.resolve(), RESULT_ROOT.resolve(strict=False))
    if not any(resolved == root or resolved.is_relative_to(root) for root in allowed):
        raise RuntimeError(f"Attempt-12 write target outside isolated namespaces: {path}")
    if resolved.is_relative_to(ATTEMPT11_ROOT.resolve()):
        raise RuntimeError("Attempt-12 cannot write into Attempt-11")
    return path


def _fsync_directory_local(path: Path) -> None:
    descriptor = os.open(path, os.O_RDONLY | os.O_DIRECTORY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def _write_signing_fault_local(path: Path, *, temporary: Path, reason: str) -> None:
    fault = safe_write_target(RUN_ROOT / "SIGNING_FAULT.json")
    fault.parent.mkdir(parents=True, exist_ok=True)
    value = {
        "schema_version": "atlas_rope_v8_attempt12_signing_fault_v1",
        "status": "TERMINAL_SIGNING_FAULT",
        "reason": reason,
        "destination": str(path),
        "temporary": str(temporary),
        "no_retry_authorized": True,
    }
    raw = (json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False, allow_nan=False) + "\n").encode("utf-8")
    try:
        descriptor = os.open(fault, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    except FileExistsError:
        return
    with os.fdopen(descriptor, "wb", closefd=True) as handle:
        handle.write(raw)
        handle.flush()
        os.fsync(handle.fileno())
    _fsync_directory_local(fault.parent)


def _post_link_identity_matches(temporary: Path, final: Path, temporary_stat: os.stat_result) -> bool:
    final_stat = final.stat()
    return (
        (temporary_stat.st_dev, temporary_stat.st_ino, temporary_stat.st_size)
        == (final_stat.st_dev, final_stat.st_ino, final_stat.st_size)
        and sha256_file(temporary) == sha256_file(final)
    )


def write_signed_local(path: Path, payload: Mapping[str, Any], signing_key: Path) -> str:
    """Atomic no-clobber signed writer with Attempt-12-local fault evidence."""
    safe_write_target(path)
    if path.exists():
        raise RuntimeError(f"create-once signed artifact already exists: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    normalized = json.loads(canonical_json_bytes(dict(payload)).decode("utf-8"))
    if not isinstance(normalized, dict):
        raise RuntimeError("signed payload must normalize to a JSON object")
    envelope = sign_payload(normalized, load_private_key(signing_key))
    raw = (json.dumps(envelope, indent=2, sort_keys=True, ensure_ascii=False, allow_nan=False) + "\n").encode("utf-8")
    descriptor, temporary_raw = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".verified.tmp", dir=path.parent)
    temporary = Path(temporary_raw)
    linked = False
    try:
        with os.fdopen(descriptor, "wb", closefd=True) as handle:
            handle.write(raw)
            handle.flush()
            os.fsync(handle.fileno())
        if temporary.read_bytes() != raw or verify_envelope(read_json(temporary)) != normalized:
            raise RuntimeError("temporary signed artifact did not verify")
        temporary_stat = temporary.stat()
        try:
            os.link(temporary, path)
        except FileExistsError as error:
            raise RuntimeError(f"create-once signed artifact already exists: {path}") from error
        linked = True
        _fsync_directory_local(path.parent)
        if not _post_link_identity_matches(temporary, path, temporary_stat):
            _write_signing_fault_local(path, temporary=temporary, reason="post-link inode/size/hash identity mismatch")
            raise RuntimeError("post-link signed artifact identity mismatch")
        temporary.unlink()
        _fsync_directory_local(path.parent)
        try:
            final_payload = verify_envelope(read_json(path))
        except Exception as error:
            _write_signing_fault_local(
                path,
                temporary=temporary,
                reason=f"post-link signature verification raised {type(error).__name__}: {error}",
            )
            raise
        if final_payload != normalized:
            _write_signing_fault_local(path, temporary=temporary, reason="post-link signature/semantic verification mismatch")
            raise RuntimeError("post-link signed artifact did not verify")
        return sha256_file(path)
    except Exception:
        if temporary.exists() and not linked:
            temporary.unlink()
            _fsync_directory_local(path.parent)
        raise
