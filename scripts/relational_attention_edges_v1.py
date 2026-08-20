#!/usr/bin/env python3
"""Shared contracts for the relational attention-link discovery study.

This module contains only deterministic data/lifecycle utilities.  It never loads
model weights and exposes no optimizer, checkpoint, or neural-training path.
"""
from __future__ import annotations

import base64
import hashlib
import json
import os
import tempfile
import copy
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

import numpy as np
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey, Ed25519PublicKey


ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "configs/relational_attention_edges_v1/run.json"
FREEZE = ROOT / "configs/relational_attention_edges_v1/FINAL_FREEZE.json"
BACKEND_QA = ROOT / "configs/relational_attention_edges_v1/BACKEND_QA.json"
AUTHORIZATION = ROOT / "configs/relational_attention_edges_v1/SCIENCE_AUTHORIZATION.json"
NAMESPACE = "relational_attention_edges_v1_discovery2"
PRESCORE_LIFECYCLE_PATHS = {
    "data_root": "data/relational_attention_edges_v1_discovery2",
    "rebuild_root": "data/relational_attention_edges_v1_discovery2_rebuild",
    "prescore_record": "pilot_runs/scientific_source_openings/relational_attention_edges_v1_discovery2.PRESCORE_OPENED.json",
    "prescore_rebuild_record": "pilot_runs/scientific_source_openings/relational_attention_edges_v1_discovery2.REBUILD_CLAIM.json",
    "prescore_primary_complete": "pilot_runs/scientific_source_openings/relational_attention_edges_v1_discovery2.PRESCORE_COMPLETE.json",
    "prescore_terminal": "pilot_runs/scientific_source_openings/relational_attention_edges_v1_discovery2.PRESCORE_TERMINAL.json",
}
EXPECTED_SIGNER = {
    "algorithm": "Ed25519",
    "public_key_base64": "GhsF4vIJ52n0fXBCRhuK/BEi1MG55+Gs2LKykDGsuhI=",
    "public_key_fingerprint_sha256": "1eb6470fb2bd3a114ca4427174a12eb5fb14639ca1e763f75b9afbb564b2e503",
}
EXPOSURE_UNIVERSE_PATH = "reports/provenance/relational_attention_edges_v1_discovery2_exposure_universe.json"


def canonical_json_bytes(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def semantic_config_digest(config: Mapping[str, Any]) -> str:
    """Hash config semantics while breaking review/amendment self-reference cycles."""
    projected = copy.deepcopy(dict(config))
    if isinstance(projected.get("source_amendment"), dict):
        projected["source_amendment"]["sha256"] = "SELF_REFERENTIAL_SOURCE_AMENDMENT"
    if isinstance(projected.get("plan_review"), dict):
        projected["plan_review"]["sha256"] = "POST_PLAN_REVIEW_BINDING"
    return hashlib.sha256(canonical_json_bytes(projected)).hexdigest()


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(4 * 1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def stable_digest(*parts: object) -> bytes:
    return hashlib.sha256("|".join(map(str, parts)).encode("utf-8")).digest()


def stable_hex(*parts: object) -> str:
    return stable_digest(*parts).hex()


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
    directory_fd = os.open(path.parent, os.O_DIRECTORY)
    try:
        os.fsync(directory_fd)
    finally:
        os.close(directory_fd)


def atomic_json(path: Path, value: Any) -> str:
    raw = canonical_json_bytes(value) + b"\n"
    atomic_bytes(path, raw)
    return hashlib.sha256(raw).hexdigest()


def atomic_jsonl(path: Path, rows: Iterable[Mapping[str, Any]]) -> tuple[str, int]:
    raw = b"".join(canonical_json_bytes(dict(row)) + b"\n" for row in rows)
    atomic_bytes(path, raw)
    return hashlib.sha256(raw).hexdigest(), raw.count(b"\n")


def exclusive_fsynced_json(path: Path, value: Any) -> str:
    """Atomically consume a global key and durably record the winner."""
    path.parent.mkdir(parents=True, exist_ok=True)
    raw = canonical_json_bytes(value) + b"\n"
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    try:
        offset = 0
        while offset < len(raw):
            offset += os.write(fd, raw[offset:])
        os.fsync(fd)
    finally:
        os.close(fd)
    directory_fd = os.open(path.parent, os.O_DIRECTORY)
    try:
        os.fsync(directory_fd)
    finally:
        os.close(directory_fd)
    return hashlib.sha256(raw).hexdigest()


def recursive_inventory(root: Path, *, exclude: Sequence[str] = ()) -> list[dict[str, Any]]:
    if not root.exists():
        return []
    excluded = set(exclude)
    output: list[dict[str, Any]] = []
    for path in sorted(root.rglob("*"), key=lambda p: p.as_posix().encode("utf-8")):
        if path.is_symlink():
            raise RuntimeError(f"symlink forbidden in inventory: {path}")
        if path.is_file():
            rel = path.relative_to(root).as_posix()
            if rel not in excluded:
                output.append({"path": rel, "bytes": path.stat().st_size, "sha256": sha256_file(path)})
        elif not path.is_dir():
            raise RuntimeError(f"unclassified inventory entry: {path}")
    return output


def inventory_digest(entries: Sequence[Mapping[str, Any]]) -> str:
    return hashlib.sha256(canonical_json_bytes(list(entries))).hexdigest()


def load_signing_key(path: Path, signer: Mapping[str, Any]) -> Ed25519PrivateKey:
    private = serialization.load_pem_private_key(path.read_bytes(), password=None)
    if not isinstance(private, Ed25519PrivateKey):
        raise RuntimeError("lifecycle key is not Ed25519")
    public = private.public_key().public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw)
    if (
        signer.get("algorithm") != "Ed25519"
        or signer.get("public_key_base64") != base64.b64encode(public).decode("ascii")
        or signer.get("public_key_fingerprint_sha256") != hashlib.sha256(public).hexdigest()
    ):
        raise RuntimeError("signing key identity drift")
    return private


def sign_payload(path: Path, payload: Mapping[str, Any], private: Ed25519PrivateKey) -> str:
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
    return atomic_json(path, envelope)


def exclusive_sign_payload(path: Path, payload: Mapping[str, Any], private: Ed25519PrivateKey) -> str:
    """Create a signed, durable, write-once lifecycle envelope."""
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
    return exclusive_fsynced_json(path, envelope)


def verify_signed(path: Path, expected_fingerprint: str) -> dict[str, Any]:
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
        or fingerprint != expected_fingerprint
    ):
        raise RuntimeError(f"signed-envelope metadata drift: {path}")
    Ed25519PublicKey.from_public_bytes(public).verify(
        base64.b64decode(str(signature.get("signature_base64", "")), validate=True), raw
    )
    return dict(payload)


def assert_permissions(config: Mapping[str, Any]) -> None:
    permissions = config.get("permissions")
    if not isinstance(permissions, Mapping) or any(value is not False for value in permissions.values()):
        raise RuntimeError("all training/retry/persistence permissions must be false")


def load_config() -> dict[str, Any]:
    config = read_json(CONFIG)
    if config.get("schema_version") != "relational_attention_edges_v1_discovery2_config_v1":
        raise RuntimeError("unexpected relational-link config schema")
    if config.get("namespace") != NAMESPACE or config.get("exploratory") is not True:
        raise RuntimeError("namespace/scope drift")
    assert_permissions(config)
    if config.get("signer") != EXPECTED_SIGNER:
        raise RuntimeError("canonical lifecycle signer identity drift")
    if any(config.get("paths", {}).get(field) != value for field, value in PRESCORE_LIFECYCLE_PATHS.items()):
        raise RuntimeError("canonical prescore lifecycle routing drift")
    if config.get("exposure", {}).get("universe_path") != EXPOSURE_UNIVERSE_PATH:
        raise RuntimeError("canonical exposure-universe routing drift")
    for field in (
        "plan", "plan_review", "closure", "preservation", "raw_provenance",
        "source_amendment", "source_amendment_superseded", "failed_prescore",
    ):
        spec = config[field]
        path = ROOT / spec["path"]
        if not path.is_file() or sha256_file(path) != spec["sha256"]:
            raise RuntimeError(f"frozen input drift: {field}")
    if config["plan_review"].get("verdict") != "SHIP":
        raise RuntimeError("plan is not SHIP")
    amendment = verify_signed(
        ROOT / config["source_amendment"]["path"], config["signer"]["public_key_fingerprint_sha256"]
    )
    if amendment.get("status") != "FROZEN_LABEL_ONLY_SOURCE_AMENDMENT":
        raise RuntimeError("source amendment status drift")
    for field in (
        "plan", "builder", "common", "raw_provenance", "config_projection", "discovery1_retirement",
        "superseded_draft", "opaque_sidecar", "role_sidecar",
    ):
        spec = amendment[field]
        if field == "config_projection":
            if spec.get("sha256") != semantic_config_digest(config):
                raise RuntimeError("source amendment config projection drift")
            continue
        if sha256_file(ROOT / spec["path"]) != spec["sha256"]:
            raise RuntimeError(f"source amendment binding drift: {field}")
    current_builder = sha256_file(ROOT / "scripts/build_relational_attention_edges_v1.py")
    if (
        config["exposure"].get("audit_implementation_sha256") != current_builder
        or amendment["builder"].get("sha256") != current_builder
    ):
        raise RuntimeError("exposure audit implementation binding drift")
    if amendment.get("attestations", {}).get("candidate_source_model_forward_run") is not False:
        raise RuntimeError("source amendment does not attest zero source forwards")
    for field, config_field in (("opaque_sidecar", "opaque_sidecar_sha256"), ("role_sidecar", "role_sidecar_sha256")):
        if amendment[field].get("sha256") != config["exposure"].get(config_field):
            raise RuntimeError(f"source amendment {field} config binding drift")
    retirement = verify_signed(
        ROOT / config["failed_prescore"]["path"], config["signer"]["public_key_fingerprint_sha256"]
    )
    if retirement.get("status") != "RETIRED_PRESCORE_INELIGIBLE_UNCHANGED":
        raise RuntimeError("Discovery-1 prescore retirement drift")
    for entry in retirement.get("artifacts", []):
        path = ROOT / entry["path"]
        if not path.is_file() or path.is_symlink() or path.stat().st_size != entry["bytes"] or sha256_file(path) != entry["sha256"]:
            raise RuntimeError(f"Discovery-1 retired artifact drift: {entry['path']}")
    if inventory_digest(retirement.get("artifacts", [])) != retirement.get("artifacts_sha256"):
        raise RuntimeError("Discovery-1 retirement inventory digest drift")
    terminal_entries = [
        entry for entry in retirement.get("artifacts", [])
        if entry.get("path") == "data/relational_attention_edges_v1_discovery1/TERMINAL_PRESCORE_INELIGIBLE.json"
    ]
    if len(terminal_entries) != 1:
        raise RuntimeError("Discovery-1 retirement lacks unique terminal")
    if config["failed_prescore"].get("terminal_sha256") != terminal_entries[0]["sha256"]:
        raise RuntimeError("configured Discovery-1 terminal binding drift")
    audit_entries = [
        entry for entry in retirement.get("artifacts", [])
        if entry.get("path") == "data/relational_attention_edges_v1_discovery1/exposure_audit.json"
    ]
    if len(audit_entries) != 1:
        raise RuntimeError("Discovery-1 retirement lacks unique exposure audit")
    discovery1_terminal = verify_signed(
        ROOT / terminal_entries[0]["path"], config["signer"]["public_key_fingerprint_sha256"]
    )
    if (
        discovery1_terminal.get("status") != "TERMINAL_PRESCORE_INELIGIBLE"
        or discovery1_terminal.get("model_forward_run") is not False
        or discovery1_terminal.get("neural_training_run") is not False
        or discovery1_terminal.get("retry_authorized") is not False
        or discovery1_terminal.get("config_sha256") != retirement.get("discovery1_terminal_config_sha256")
        or discovery1_terminal.get("exposure_audit_sha256") != audit_entries[0]["sha256"]
        or discovery1_terminal.get("reason") != "exposure_audit_failed"
    ):
        raise RuntimeError("Discovery-1 signed terminal content drift")
    retirement_binding = amendment.get("discovery1_retirement", {})
    if retirement_binding.get("sha256") != sha256_file(ROOT / config["failed_prescore"]["path"]):
        raise RuntimeError("source amendment does not bind Discovery-1 retirement")
    old_key = retirement.get("discovery1_study_key")
    successor = amendment.get("study_keys", {})
    if (
        successor.get("discovery1") != old_key
        or successor.get("discovery2") != study_key(config)
        or successor.get("discovery1") == successor.get("discovery2")
    ):
        raise RuntimeError("source amendment successor-key binding drift")
    for source, spec in config["sources"].items():
        root = ROOT / spec["root"]
        observed = {p.name: sha256_file(p) for p in sorted(root.glob("*.conllu"))}
        if observed != spec["files"]:
            raise RuntimeError(f"raw source drift: {source}")
    return config


def preservation_manifest(config: Mapping[str, Any]) -> dict[str, Any]:
    manifest = read_json(ROOT / config["preservation"]["path"])
    if manifest.get("status") != "FROZEN_IMMUTABLE":
        raise RuntimeError("preservation manifest is not frozen")
    return manifest


def verify_preservation(config: Mapping[str, Any]) -> str:
    manifest = preservation_manifest(config)
    for entry in manifest["entries"]:
        path = ROOT / entry["path"]
        if (
            not path.is_file()
            or path.is_symlink()
            or path.stat().st_size != entry["bytes"]
            or sha256_file(path) != entry["sha256"]
        ):
            raise RuntimeError(f"preserved Attempt-13/14 artifact drift: {entry['path']}")
    if inventory_digest(manifest["entries"]) != manifest["entries_sha256"]:
        raise RuntimeError("preservation manifest self-digest drift")
    return str(manifest["entries_sha256"])


def assert_new_destination(config: Mapping[str, Any], path: Path) -> None:
    destination = path.resolve(strict=False)
    for rel in preservation_manifest(config)["preserved_roots"]:
        preserved = (ROOT / rel).resolve(strict=True)
        if destination == preserved or preserved in destination.parents:
            raise RuntimeError(f"new-study writer targets preserved root: {path}")


def study_key(config: Mapping[str, Any]) -> str:
    protocol = {
        "sources": {
            name: {
                "revision": spec["revision"],
                "analysis_files": list(spec["analysis_files"]),
                "analysis_file_sha256": {file: spec["files"][file] for file in spec["analysis_files"]},
                "all_pinned_files": spec["files"],
            }
            for name, spec in sorted(config["sources"].items())
        },
        "source_partition_rule": config["source_partition_rule"],
        "model": config["model"],
        "matching": config["matching"],
        "analysis": config["analysis"],
        "exposure": config["exposure"],
    }
    identity = {
        "namespace": config["namespace"],
        "namespace_family": "relational_attention_edges_v1",
        "protocol_sha256": hashlib.sha256(canonical_json_bytes(protocol)).hexdigest(),
        "exposure_implementation_sha256": config["exposure"]["audit_implementation_sha256"],
        "discovery1_terminal_sha256": config["failed_prescore"]["terminal_sha256"],
        "discovery1_retirement_sha256": config["failed_prescore"]["sha256"],
        "canonical_prescore_lifecycle_paths": PRESCORE_LIFECYCLE_PATHS,
        "canonical_signer_fingerprint_sha256": EXPECTED_SIGNER["public_key_fingerprint_sha256"],
    }
    return hashlib.sha256(canonical_json_bytes(identity)).hexdigest()


def bootstrap_indices(components: Sequence[str], *, direction: str, seed: int, draws: int) -> np.ndarray:
    ordered = sorted(set(map(str, components)), key=lambda value: value.encode("utf-8"))
    if len(ordered) != len(components) or not ordered:
        raise ValueError("bootstrap components must be unique and nonempty")
    output = np.empty((draws, len(ordered)), dtype=np.uint32)
    for draw in range(draws):
        draw_seed = int.from_bytes(stable_digest(NAMESPACE, "bootstrap", seed, direction, draw)[:8], "big")
        output[draw] = np.random.default_rng(draw_seed).integers(0, len(ordered), len(ordered), dtype=np.uint32)
    return output


def bootstrap_multiplicity(index_row: np.ndarray, size: int) -> np.ndarray:
    indices = np.asarray(index_row)
    if indices.ndim != 1 or indices.size != size or np.any(indices < 0) or np.any(indices >= size):
        raise ValueError("invalid bootstrap index row")
    return np.bincount(indices.astype(np.int64), minlength=size).astype(np.int64)


def finite_interval(values: Sequence[float], config: Mapping[str, Any]) -> dict[str, Any]:
    array = np.asarray(values, dtype=np.float64)
    finite = array[np.isfinite(array)]
    analysis = config["analysis"]
    if finite.size < int(analysis["minimum_finite_draws"]):
        return {"finite": int(finite.size), "total": int(array.size), "eligible": False}
    q = np.quantile(finite, analysis["quantiles"], method=analysis["quantile_method"])
    return {
        "finite": int(finite.size),
        "total": int(array.size),
        "eligible": True,
        "lower": float(q[0]),
        "median": float(q[1]),
        "upper": float(q[2]),
    }


RELATION_GROUPS: dict[str, set[str]] = {
    "CORE": {"nsubj", "csubj", "obj", "iobj", "ccomp", "xcomp"},
    "OBLIQUE": {"obl", "advcl", "advmod"},
    "NOMINAL": {"nmod", "appos", "acl", "amod", "nummod", "compound", "flat", "fixed"},
    "COORD": {"conj", "cc"},
    "FUNCTION": {"det", "case", "mark", "aux", "cop", "clf"},
    "PUNCT": {"punct"},
}


def coarse_relation(label: str) -> str:
    base = str(label).split(":", 1)[0]
    for group, values in RELATION_GROUPS.items():
        if base in values:
            return group
    return "OTHER"
