#!/usr/bin/env python3
"""Shared contracts for the Attempt-13 relational/context measurement study.

This module contains lifecycle, hashing, resampling, and numerical-eligibility
logic only.  It never loads model weights and never trains a representation.
"""
from __future__ import annotations

import base64
import hashlib
import json
import os
import tempfile
from collections import Counter
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

import numpy as np
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey, Ed25519PublicKey


ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "configs/atlas_relation_context_v9/run.json"
DATA_ROOT = ROOT / "data/atlas_relation_context_v9_attempt13"
PREPARED_ROOT = DATA_ROOT / "prepared"
RUN_ROOT = ROOT / "pilot_runs/20260803_atlas_relation_context_v9_attempt13"
RESULT_ROOT = ROOT / "results/atlas_relation_context_v9_attempt13"
HISTORICAL_PAYLOAD = ROOT / "reports/provenance/atlas_v3_9_attempt13_historical_exposure_manifest.payload.json"
HISTORICAL_ENVELOPE = ROOT / "reports/provenance/atlas_v3_9_attempt13_historical_exposure_manifest.envelope.json"
FINAL_FREEZE_PAYLOAD = ROOT / "configs/atlas_relation_context_v9/FINAL_FREEZE.payload.json"
FINAL_FREEZE_ENVELOPE = ROOT / "configs/atlas_relation_context_v9/FINAL_FREEZE.envelope.json"
AUTHORIZATION = ROOT / "configs/atlas_relation_context_v9/SCIENCE_AUTHORIZATION.json"
CANDIDATE_REVIEW = ROOT / "reports/adversarial/atlas_v3_9_attempt13_candidate_review.md"
GLOBAL_OPENING_ROOT = ROOT / "pilot_runs/scientific_source_openings"
ATTEMPT12_RUN = ROOT / "pilot_runs/20260803_atlas_rope_analysis_recovery_v8"
ATTEMPT12_RESULT = ROOT / "results/atlas_rope_v8_attempt12_analysis_recovery"
NAMESPACE = "atlas_relation_context_v9_attempt13"


def canonical_json_bytes(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(4 * 1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def stable_hex(*parts: object) -> str:
    return hashlib.sha256("|".join(map(str, parts)).encode("utf-8")).hexdigest()


def stable_digest(*parts: object) -> bytes:
    return hashlib.sha256("|".join(map(str, parts)).encode("utf-8")).digest()


def stable_fold(source: str, component: str, *, seed: int, folds: int) -> int:
    if folds <= 1:
        raise ValueError("folds must exceed one")
    return int.from_bytes(stable_digest(NAMESPACE, "fold", seed, source, component)[:8], "big") % folds


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]


def atomic_bytes(path: Path, value: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(dir=path.parent, prefix=f".{path.name}.", delete=False) as handle:
        handle.write(value)
        handle.flush()
        os.fsync(handle.fileno())
        temporary = Path(handle.name)
    os.replace(temporary, path)


def atomic_json(path: Path, value: Any) -> str:
    raw = canonical_json_bytes(value) + b"\n"
    atomic_bytes(path, raw)
    return hashlib.sha256(raw).hexdigest()


def atomic_jsonl(path: Path, rows: Iterable[Mapping[str, Any]]) -> tuple[str, int]:
    materialized = [canonical_json_bytes(dict(row)) + b"\n" for row in rows]
    raw = b"".join(materialized)
    atomic_bytes(path, raw)
    return hashlib.sha256(raw).hexdigest(), len(materialized)


def recursive_inventory(root: Path, *, exclude: Sequence[str] = ()) -> list[dict[str, Any]]:
    """Hash regular files with canonical POSIX paths and bytewise path order."""
    if not root.exists():
        return []
    excluded = set(exclude)
    files: list[Path] = []
    for path in root.rglob("*"):
        if path.is_symlink():
            raise RuntimeError(f"symlink forbidden in inventory: {path}")
        if path.is_file():
            rel = path.relative_to(root).as_posix()
            if rel not in excluded:
                files.append(path)
        elif not path.is_dir():
            raise RuntimeError(f"unclassified inventory entry: {path}")
    files.sort(key=lambda path: path.relative_to(root).as_posix().encode("utf-8"))
    return [
        {
            "path": path.relative_to(root).as_posix(),
            "bytes": path.stat().st_size,
            "sha256": sha256_file(path),
        }
        for path in files
    ]


def inventory_digest(entries: Sequence[Mapping[str, Any]]) -> str:
    return hashlib.sha256(canonical_json_bytes(list(entries))).hexdigest()


def load_signing_key(key_path: Path, signer: Mapping[str, Any]) -> Ed25519PrivateKey:
    """Load and pin an Ed25519 lifecycle key before any irreversible write."""
    private = serialization.load_pem_private_key(key_path.read_bytes(), password=None)
    if not isinstance(private, Ed25519PrivateKey):
        raise RuntimeError("lifecycle signing key is not Ed25519")
    public = private.public_key().public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw)
    encoded = base64.b64encode(public).decode("ascii")
    fingerprint = hashlib.sha256(public).hexdigest()
    if (
        signer.get("algorithm") != "Ed25519"
        or signer.get("public_key_base64") != encoded
        or signer.get("public_key_fingerprint_sha256") != fingerprint
    ):
        raise RuntimeError("lifecycle signing key does not match the frozen signer")
    return private


def sign_payload(
    path: Path, payload: Mapping[str, Any], private: Ed25519PrivateKey
) -> dict[str, Any]:
    if not isinstance(private, Ed25519PrivateKey):
        raise TypeError("sign_payload requires a validated Ed25519 private key")
    raw = canonical_json_bytes(dict(payload))
    public = private.public_key().public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw)
    envelope = {
        "payload": dict(payload),
        "signature": {
            "algorithm": "Ed25519",
            "message_sha256": hashlib.sha256(raw).hexdigest(),
            "public_key_base64": base64.b64encode(public).decode("ascii"),
            "public_key_fingerprint_sha256": hashlib.sha256(public).hexdigest(),
            "signature_base64": base64.b64encode(private.sign(raw)).decode("ascii"),
        },
    }
    atomic_json(path, envelope)
    return envelope


def verify_detached(
    payload_path: Path,
    envelope_path: Path,
    *,
    expected_public_fingerprint: str,
) -> dict[str, Any]:
    """Verify a detached Ed25519 signature over the payload file's exact bytes."""
    envelope = read_json(envelope_path)
    signature = envelope.get("signature")
    if not isinstance(signature, Mapping):
        raise RuntimeError(f"malformed detached envelope: {envelope_path}")
    try:
        declared_path = (ROOT / str(envelope.get("payload_path", ""))).resolve(strict=True)
    except (OSError, RuntimeError) as error:
        raise RuntimeError(f"detached payload path is invalid: {envelope_path}") from error
    if declared_path != payload_path.resolve(strict=True):
        raise RuntimeError(f"detached payload path drift: {envelope_path}")
    raw = payload_path.read_bytes()
    payload_sha = hashlib.sha256(raw).hexdigest()
    public = base64.b64decode(str(signature.get("public_key_base64", "")), validate=True)
    fingerprint = hashlib.sha256(public).hexdigest()
    if (
        envelope.get("schema_version") != "atlas_relation_context_v9_attempt13_detached_signature_v1"
        or envelope.get("payload_sha256") != payload_sha
        or signature.get("algorithm") != "Ed25519"
        or signature.get("public_key_fingerprint_sha256") != fingerprint
        or fingerprint != expected_public_fingerprint
    ):
        raise RuntimeError(f"detached signature metadata drift: {envelope_path}")
    Ed25519PublicKey.from_public_bytes(public).verify(
        base64.b64decode(str(signature.get("signature_base64", "")), validate=True), raw
    )
    return dict(envelope)


def verify_candidate_review(path: Path, freeze: Mapping[str, Any]) -> dict[str, str]:
    """Require a unique SHIP verdict bound to this exact frozen candidate."""
    lines = path.read_text(encoding="utf-8").splitlines()
    if not lines or lines[0] != "VERDICT: SHIP":
        raise RuntimeError("candidate review does not begin with exact VERDICT: SHIP")
    verdict_lines = [line for line in lines if line.startswith("VERDICT:")]
    if verdict_lines != ["VERDICT: SHIP"]:
        raise RuntimeError("candidate review has an ambiguous or non-SHIP verdict")
    expected = {
        "FINAL_FREEZE_PAYLOAD_SHA256": sha256_file(FINAL_FREEZE_PAYLOAD),
        "CANDIDATE_INVENTORY_SHA256": str(freeze["candidate_inventory_sha256"]),
    }
    observed: dict[str, str] = {}
    for line in lines[1:]:
        for key in expected:
            prefix = key + ": "
            if line.startswith(prefix):
                if key in observed:
                    raise RuntimeError(f"duplicate candidate review binding: {key}")
                observed[key] = line[len(prefix) :]
    if observed != expected:
        raise RuntimeError("candidate review is not bound to the exact frozen payload and inventory")
    return {"verdict": "SHIP", **observed}


def verify_signed(path: Path, *, expected_public_fingerprint: str | None = None) -> dict[str, Any]:
    envelope = read_json(path)
    payload, signature = envelope.get("payload"), envelope.get("signature")
    if not isinstance(payload, Mapping) or not isinstance(signature, Mapping):
        raise RuntimeError(f"malformed signed envelope: {path}")
    raw = canonical_json_bytes(payload)
    public = base64.b64decode(str(signature.get("public_key_base64", "")), validate=True)
    fingerprint = hashlib.sha256(public).hexdigest()
    if (
        signature.get("algorithm") != "Ed25519"
        or signature.get("message_sha256") != hashlib.sha256(raw).hexdigest()
        or signature.get("public_key_fingerprint_sha256") != fingerprint
        or (expected_public_fingerprint is not None and fingerprint != expected_public_fingerprint)
    ):
        raise RuntimeError(f"signature metadata drift: {path}")
    Ed25519PublicKey.from_public_bytes(public).verify(
        base64.b64decode(str(signature.get("signature_base64", "")), validate=True), raw
    )
    return dict(payload)


def normalized_delta(left: np.ndarray, right: np.ndarray, *, floor: float = 1e-12) -> np.ndarray:
    """Return ||left-right|| / max(||left||, ||right||, floor) in float64."""
    a = np.asarray(left, dtype=np.float64)
    b = np.asarray(right, dtype=np.float64)
    if a.shape != b.shape or a.ndim != 2 or not np.isfinite(a).all() or not np.isfinite(b).all():
        raise ValueError("normalized-delta inputs must be equal finite matrices")
    numerator = np.linalg.norm(a - b, axis=1)
    denominator = np.maximum(np.maximum(np.linalg.norm(a, axis=1), np.linalg.norm(b, axis=1)), floor)
    return numerator / denominator


def relation_norm_audit(
    variants: Mapping[str, np.ndarray], *, threshold: float, maximum_rate: float
) -> dict[str, Any]:
    """Apply the frozen pre-norm denominator, inclusive boundary, and union rule."""
    required = ("true", "sham", "sequential_offset")
    if tuple(sorted(variants)) != tuple(sorted(required)):
        raise ValueError("relation norm audit requires true, sham, and sequential_offset")
    arrays = {name: np.asarray(variants[name], dtype=np.float64) for name in required}
    sizes = {array.shape for array in arrays.values()}
    if len(sizes) != 1 or next(iter(sizes))[0] == 0:
        raise ValueError("relation norm variants must have one nonempty shared shape")
    n = next(iter(sizes))[0]
    masks = {name: values <= threshold for name, values in arrays.items()}
    union = np.logical_or.reduce(list(masks.values()))
    rates = {name: float(mask.sum() / n) for name, mask in masks.items()}
    rates["union"] = float(union.sum() / n)
    passing = all(rate <= maximum_rate for rate in rates.values())
    return {
        "denominator": n,
        "threshold": threshold,
        "maximum_rate": maximum_rate,
        "variant_noninformative_counts": {name: int(mask.sum()) for name, mask in masks.items()},
        "union_noninformative_count": int(union.sum()),
        "rates": rates,
        "cap_pass": passing,
        "informative_mask": ~union,
    }


def component_multiplicities(
    components: Sequence[str], *, direction: str, endpoint: str, draw: int, seed: int
) -> dict[str, int]:
    ordered = sorted(set(map(str, components)), key=lambda value: value.encode("utf-8"))
    if len(ordered) != len(components):
        raise RuntimeError("bootstrap component IDs must be unique")
    counts: Counter[str] = Counter()
    for slot in range(len(ordered)):
        digest = stable_digest(NAMESPACE, "component-bootstrap", seed, direction, endpoint, draw, slot)
        counts[ordered[int.from_bytes(digest[:8], "big") % len(ordered)]] += 1
    return dict(counts)


def interval(values: Sequence[float]) -> dict[str, Any]:
    finite = np.asarray([value for value in values if np.isfinite(value)], dtype=np.float64)
    if not len(finite):
        return {"lower": None, "median": None, "upper": None, "finite": 0, "total": len(values)}
    return {
        "lower": float(np.quantile(finite, 0.025)),
        "median": float(np.quantile(finite, 0.5)),
        "upper": float(np.quantile(finite, 0.975)),
        "finite": int(len(finite)),
        "total": len(values),
    }


def study_key(config: Mapping[str, Any]) -> str:
    """Authorization-independent global opening key."""
    identity = {
        "schema": NAMESPACE,
        "sources": {name: spec["sha256"] for name, spec in sorted(config["sources"].items())},
        "model": {
            "name": config["model"]["name"],
            "revision": config["model"]["revision"],
            "layer": config["model"]["layer"],
        },
        "endpoint_protocol_sha256": config["protocol"]["sha256"],
    }
    return hashlib.sha256(canonical_json_bytes(identity)).hexdigest()


def opening_path(config: Mapping[str, Any]) -> Path:
    return GLOBAL_OPENING_ROOT / f"atlas_relation_context_v9_{study_key(config)}" / "SCIENTIFIC_OPENING_CONSUMED.json"


def consume_study_key(config: Mapping[str, Any], payload: Mapping[str, Any]) -> Path:
    """Exclusively and durably consume the global study key before any forward."""
    path = opening_path(config)
    path.parent.mkdir(parents=True, exist_ok=True)
    raw = canonical_json_bytes(dict(payload)) + b"\n"
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o444)
    try:
        with os.fdopen(descriptor, "wb", closefd=False) as handle:
            handle.write(raw)
            handle.flush()
            os.fsync(handle.fileno())
    finally:
        os.close(descriptor)
    parent = os.open(path.parent, os.O_RDONLY)
    try:
        os.fsync(parent)
    finally:
        os.close(parent)
    return path


def assert_attempt12_inventory(expected: Mapping[str, Any]) -> None:
    for label, root in (("run", ATTEMPT12_RUN), ("result", ATTEMPT12_RESULT)):
        observed = recursive_inventory(root)
        if observed != expected[label]["entries"] or inventory_digest(observed) != expected[label]["digest"]:
            raise RuntimeError(f"Attempt-12 {label} inventory drift")


def reconcile_frozen_tree(freeze: Mapping[str, Any], *, stage: str) -> dict[str, Any]:
    """Reconcile the historical snapshot, final candidate, and exact late paths.

    This intentionally rehashes historical files at authorization and opening;
    a path absent from both manifests and the exact lifecycle allowlist is fatal.
    """
    if stage not in {"preauthorization", "preopening"}:
        raise ValueError("unknown reconciliation stage")
    historical = read_json(HISTORICAL_PAYLOAD)
    historical_entries = {str(row["path"]): dict(row) for row in historical["entries"]}
    candidate_entries = {str(row["path"]): dict(row) for row in freeze["candidate_entries"]}
    for mapping, label in ((historical_entries, "historical"), (candidate_entries, "candidate")):
        for relative, entry in mapping.items():
            path = ROOT / relative
            if (
                not path.is_file()
                or path.is_symlink()
                or path.stat().st_size != int(entry["bytes"])
                or sha256_file(path) != str(entry["sha256"])
            ):
                raise RuntimeError(f"{label} freeze drift: {relative}")

    exact_late = {
        FINAL_FREEZE_PAYLOAD.relative_to(ROOT).as_posix(),
        FINAL_FREEZE_ENVELOPE.relative_to(ROOT).as_posix(),
        CANDIDATE_REVIEW.relative_to(ROOT).as_posix(),
        AUTHORIZATION.relative_to(ROOT).as_posix(),
    }
    allowed = set(historical_entries) | set(candidate_entries) | exact_late
    tool_directories = {".git", ".venv-atlas", ".cache", ".pytest_cache", "__pycache__"}
    lifecycle_prefixes = (
        RUN_ROOT.relative_to(ROOT).as_posix() + "/",
        RESULT_ROOT.relative_to(ROOT).as_posix() + "/",
        "pilot_runs/scientific_source_openings/atlas_relation_context_v9_",
    )
    unexpected: list[str] = []
    lifecycle_present: list[str] = []
    for base, directories, files in os.walk(ROOT, topdown=True, followlinks=False):
        retained_directories: list[str] = []
        for name in sorted(directories, key=lambda value: value.encode("utf-8")):
            path = Path(base) / name
            if path.is_symlink():
                unexpected.append(path.relative_to(ROOT).as_posix() + "/")
            elif name not in tool_directories:
                retained_directories.append(name)
        directories[:] = retained_directories
        for name in sorted(files, key=lambda value: value.encode("utf-8")):
            path = Path(base) / name
            relative = path.relative_to(ROOT).as_posix()
            if relative in allowed:
                continue
            if any(relative.startswith(prefix) for prefix in lifecycle_prefixes):
                lifecycle_present.append(relative)
            else:
                unexpected.append(relative)
    if unexpected:
        raise RuntimeError(f"unclassified late repository files: {unexpected[:10]}")
    if lifecycle_present:
        raise RuntimeError(f"lifecycle path exists before {stage}: {lifecycle_present[:10]}")
    required_late = {
        "preauthorization": {FINAL_FREEZE_PAYLOAD.relative_to(ROOT).as_posix(), FINAL_FREEZE_ENVELOPE.relative_to(ROOT).as_posix(), CANDIDATE_REVIEW.relative_to(ROOT).as_posix()},
        "preopening": exact_late,
    }[stage]
    missing = [relative for relative in required_late if not (ROOT / relative).is_file()]
    if missing:
        raise RuntimeError(f"required late-stage artifacts missing: {missing}")
    return {
        "status": "PASS",
        "stage": stage,
        "historical_files_rehashed": len(historical_entries),
        "candidate_files_rehashed": len(candidate_entries),
        "unclassified_late_files": [],
        "lifecycle_paths_present": [],
    }
