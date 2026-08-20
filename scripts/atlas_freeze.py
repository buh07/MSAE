#!/usr/bin/env python3
"""Compute and enforce the immutable atlas-v1 prescore bundle."""

from __future__ import annotations

import hashlib
import json
import platform
import sys
from datetime import datetime, timezone
from functools import lru_cache
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
FREEZE_RECORD = ROOT / "configs/atlas/freeze_record.json"
UNLOCK_TEXT = "atlas-v1-M8-unlock"


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def runtime_environment(device: str | None = None) -> dict[str, object]:
    import numpy
    import sklearn
    import torch
    result: dict[str, object] = {
        "python": sys.version, "platform": platform.platform(), "numpy": numpy.__version__,
        "sklearn": sklearn.__version__, "torch": torch.__version__, "cuda_runtime": torch.version.cuda,
    }
    if device is not None:
        parsed = torch.device(device)
        result["device"] = str(parsed)
        result["hardware"] = torch.cuda.get_device_name(parsed) if parsed.type == "cuda" else platform.processor()
    return result


def bundle_files() -> list[Path]:
    paths: set[Path] = set()
    for pattern in [
        "configs/atlas/*.json", "configs/atlas/*.yaml", "prereg/separable_information_atlas_v1.md",
        "analysis/label_inventory/*", "requirements-atlas.lock.txt", "scripts/atlas_*.py",
        "scripts/build_atlas_*.py", "scripts/extract_atlas_activations.py", "scripts/run_raw_atlas.py",
        "scripts/transform_atlas_k2.py", "scripts/run_k2_atlas_audit.py", "scripts/run_k2_functional_audit.py",
        "scripts/qa_atlas_data.py", "scripts/run_synthetic_metric_smoke.py", "tests/test_atlas_*.py",
        "scripts/freeze_atlas_bundle.py", "reports/atlas_data_qa.json", "reports/atlas_data_qa.md",
        "reports/atlas_label_counts.json", "reports/counterfactual_template_review.md", "reports/synthetic_metric_smoke.md",
        "reports/provenance/final_checkpoint_metadata.json", "reports/provenance/final_checkpoint_sha256.txt",
        "results/synthetic/atlas_v1_smoke.json", "requirements-atlas.lock.txt",
    ]:
        paths.update(path for path in ROOT.glob(pattern) if path.is_file())
    paths.discard(FREEZE_RECORD)
    return sorted(paths)


def file_hash(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(16 << 20):
            digest.update(chunk)
    return digest.hexdigest()


@lru_cache(maxsize=256)
def _cached_file_hash(path: str, size: int, mtime_ns: int) -> str:
    del size, mtime_ns
    return file_hash(Path(path))


def artifact_hash(path: Path) -> str:
    stat = path.stat()
    return _cached_file_hash(str(path.resolve()), stat.st_size, stat.st_mtime_ns)


def compute_bundle() -> dict[str, object]:
    files = {path.relative_to(ROOT).as_posix(): file_hash(path) for path in bundle_files()}
    canonical = "".join(f"{name}\0{digest}\n" for name, digest in sorted(files.items())).encode()
    return {"schema_version": "atlas_v1_prescore_freeze", "bundle_sha256": hashlib.sha256(canonical).hexdigest(), "files": files}


def verify_freeze() -> dict[str, object]:
    if not FREEZE_RECORD.exists():
        raise RuntimeError("atlas prescore freeze_record.json is absent")
    expected = json.loads(FREEZE_RECORD.read_text())
    actual = compute_bundle()
    if expected.get("bundle_sha256") != actual["bundle_sha256"] or expected.get("files") != actual["files"]:
        raise RuntimeError("atlas prescore bundle differs from freeze_record.json")
    if expected.get("adversarial_digest_quoted") is not True:
        raise RuntimeError("freeze record lacks independent adversarial digest acknowledgement")
    partition_hashes = json.loads((ROOT / "configs/atlas/partition_hashes.json").read_text())
    for rel, spec in partition_hashes["files"].items():
        # Do not re-open the blind final payload during ordinary analysis. Its
        # published digest is itself covered by the immutable prescore bundle.
        if spec.get("access") != "public_analysis":
            continue
        path = ROOT / rel
        if not path.exists() or artifact_hash(path) != spec["sha256"]:
            raise RuntimeError(f"frozen public data artifact differs: {rel}")
    return expected


def checkpoint_spec(job: str) -> dict[str, object]:
    rows = json.loads((ROOT / "reports/provenance/final_checkpoint_metadata.json").read_text())
    row = next((item for item in rows if item["job_id"] == job), None)
    if row is None:
        raise ValueError(f"unknown frozen checkpoint job: {job}")
    expected_by_path = {}
    for line in (ROOT / "reports/provenance/final_checkpoint_sha256.txt").read_text().splitlines():
        digest, rel = line.split(maxsplit=1)
        expected_by_path[rel.strip()] = digest
    rel = row["checkpoint_relpath"]
    expected = expected_by_path.get(rel)
    path = ROOT / rel
    if expected is None or not path.exists() or artifact_hash(path) != expected:
        raise RuntimeError(f"frozen checkpoint differs: {job}")
    return {"metadata": row, "path": path, "sha256": expected}


def verify_activation_complete(directory: Path, role: str, freeze: dict[str, object]) -> dict[str, object]:
    complete_path = directory / "COMPLETE.json"
    if not complete_path.exists():
        raise RuntimeError(f"activation extraction incomplete: {directory}")
    record = json.loads(complete_path.read_text())
    sample = json.loads((ROOT / "configs/atlas/analysis_sample_manifest.json").read_text())
    model = json.loads((ROOT / "configs/atlas/data_sources.json").read_text())["model"]
    if (record.get("role") != role or record.get("prescore_bundle_sha256") != freeze["bundle_sha256"]
            or record.get("sample_digest") != sample["roles"][role]["base_id_digest"] or record.get("model") != model
            or record.get("dtype") != "torch.float16" or not str(record.get("device", "")).startswith("cuda")):
        raise RuntimeError(f"activation COMPLETE metadata mismatch: {directory}")
    resolved = record.get("resolved_config")
    if (not isinstance(resolved, dict) or resolved.get("role") != role or resolved.get("seed") is None
            or resolved.get("dtype") != "float16" or not record.get("started_utc") or not record.get("ended_utc")):
        raise RuntimeError(f"activation COMPLETE provenance is incomplete: {directory}")
    for name, spec in record.get("artifacts", {}).items():
        path = directory / name
        if not path.exists() or path.stat().st_size != spec["bytes"] or artifact_hash(path) != spec["sha256"]:
            raise RuntimeError(f"activation artifact differs: {path}")
    required = {"row_meta.npz", "records.jsonl", "units.json"} | {f"L{layer}.float16.npy" for layer in [3, 4]}
    if set(record.get("artifacts", {})) != required:
        raise RuntimeError(f"activation artifact inventory incomplete: {directory}")
    return record


def activation_artifact_digest(record: dict[str, object]) -> str:
    payload = json.dumps(record["artifacts"], sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(payload).hexdigest()


def verify_transform_complete(directory: Path, job: str, freeze: dict[str, object]) -> dict[str, object]:
    complete_path = directory / "COMPLETE.json"
    if not complete_path.exists():
        raise RuntimeError(f"K=2 transform incomplete: {directory}")
    record = json.loads(complete_path.read_text())
    checkpoint = checkpoint_spec(job)
    if (record.get("job_id") != job or record.get("prescore_bundle_sha256") != freeze["bundle_sha256"]
            or record.get("checkpoint_sha256") != checkpoint["sha256"]):
        raise RuntimeError(f"K=2 transform COMPLETE metadata mismatch: {directory}")
    if set(record.get("roles", {})) != {"discovery", "calibration", "C2"}:
        raise RuntimeError(f"K=2 transform role inventory incomplete: {directory}")
    source_digests = record.get("source_activation_artifact_sha256")
    if not isinstance(source_digests, dict) or set(source_digests) != {"discovery", "calibration", "C2"}:
        raise RuntimeError(f"K=2 transform source-activation inventory incomplete: {directory}")
    for role, role_record in record["roles"].items():
        activation = verify_activation_complete(directory.parents[1] / "raw_activations" / role, role, freeze)
        if source_digests[role] != activation_artifact_digest(activation):
            raise RuntimeError(f"K=2 transform is stale relative to source activations: {job}/{role}")
        artifacts = role_record.get("artifacts", {})
        if set(artifacts) != {"pos.float16.npy", "content.float16.npy", "resid.float16.npy"}:
            raise RuntimeError(f"K=2 transform artifact inventory incomplete: {job}/{role}")
        for name, spec in artifacts.items():
            path = directory / role / name
            if not path.exists() or path.stat().st_size != spec["bytes"] or artifact_hash(path) != spec["sha256"]:
                raise RuntimeError(f"K=2 transform artifact differs: {path}")
    return record


def verify_layer_trigger(path: Path, freeze: dict[str, object]) -> dict[str, object]:
    """Verify the calibration-only trigger and both immutable layer bundles."""
    if not path.exists():
        raise RuntimeError("atlas layer-trigger freeze is absent")
    record = json.loads(path.read_text())
    if (record.get("schema_version") != "atlas_v1_layer_trigger"
            or record.get("l4_fallback_activated") is not False
            or record.get("primary_layer") != 3 or record.get("descriptive_layer") != 4):
        raise RuntimeError("layer trigger violates the fixed-L3 atlas-v1 policy")
    if record.get("prescore_bundle_sha256") != freeze["bundle_sha256"]:
        raise RuntimeError("layer trigger belongs to a different prescore bundle")
    hashes = record.get("calibration_bundle_sha256")
    if not isinstance(hashes, dict) or set(hashes) != {"3", "4"}:
        raise RuntimeError("layer trigger does not enumerate exactly L3 and L4 calibration bundles")
    for layer, expected in hashes.items():
        bundle = path.parent / f"L{layer}_calibration_bundle.pkl"
        layer_freeze = path.parent / f"L{layer}_calibration_freeze.json"
        if not bundle.exists() or not layer_freeze.exists():
            raise RuntimeError(f"L{layer} calibration artifact is absent")
        actual = file_hash(bundle)
        if actual != expected or json.loads(layer_freeze.read_text()).get("bundle_sha256") != actual:
            raise RuntimeError(f"L{layer} calibration bundle is absent or changed")
    calibration_complete = path.parent / "CALIBRATION_COMPLETE.json"
    if not calibration_complete.exists():
        raise RuntimeError("calibration completion marker is absent")
    completion = json.loads(calibration_complete.read_text())
    if (completion.get("schema_version") != "atlas_v1_raw_calibration_complete"
            or completion.get("phase") != "calibrate"
            or completion.get("layer_trigger_sha256") != artifact_hash(path)):
        raise RuntimeError("calibration completion marker does not bind the layer trigger")
    return record


def verify_calibration_sources(trigger_path: Path, run_root: Path,
                               freeze: dict[str, object]) -> dict[str, str]:
    """Bind calibration bundles to the exact discovery/calibration activations."""
    completion_path = trigger_path.parent / "CALIBRATION_COMPLETE.json"
    if not completion_path.exists():
        raise RuntimeError("calibration completion marker is absent")
    completion = json.loads(completion_path.read_text())
    expected = completion.get("source_activation_artifact_sha256")
    if not isinstance(expected, dict) or set(expected) != {"discovery", "calibration"}:
        raise RuntimeError("calibration source-activation binding is incomplete")
    for role in ["discovery", "calibration"]:
        record = verify_activation_complete(run_root / "raw_activations" / role, role, freeze)
        if expected[role] != activation_artifact_digest(record):
            raise RuntimeError(f"calibration bundle is stale relative to {role} activations")
    return expected


def assert_role_access(role: str) -> None:
    if role != "final":
        return
    unlock = ROOT / ".atlas_final_unlock"
    if not unlock.exists() or unlock.read_text().strip() != UNLOCK_TEXT:
        raise PermissionError("final atlas role is locked; M8 unlock token is absent or invalid")
    partition_hashes = json.loads((ROOT / "configs/atlas/partition_hashes.json").read_text())
    final_entries = {rel: spec for rel, spec in partition_hashes["files"].items()
                     if spec.get("access") == "M8_only_unlock_required"}
    if not final_entries:
        raise RuntimeError("final atlas manifest has no M8 payload entries")
    for rel, spec in final_entries.items():
        path = ROOT / rel
        if not path.exists() or artifact_hash(path) != spec["sha256"]:
            raise RuntimeError(f"blind final artifact differs from frozen manifest: {rel}")
