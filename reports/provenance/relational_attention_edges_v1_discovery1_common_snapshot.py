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
NAMESPACE = "relational_attention_edges_v1_discovery1"


def canonical_json_bytes(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


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
    if config.get("schema_version") != "relational_attention_edges_v1_discovery1_config_v1":
        raise RuntimeError("unexpected relational-link config schema")
    if config.get("namespace") != NAMESPACE or config.get("exploratory") is not True:
        raise RuntimeError("namespace/scope drift")
    assert_permissions(config)
    for field in ("plan", "plan_review", "closure", "preservation", "raw_provenance", "source_amendment"):
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
    for field in ("plan", "builder", "raw_provenance"):
        spec = amendment[field]
        if sha256_file(ROOT / spec["path"]) != spec["sha256"]:
            raise RuntimeError(f"source amendment binding drift: {field}")
    if amendment.get("attestations", {}).get("candidate_source_model_forward_run") is not False:
        raise RuntimeError("source amendment does not attest zero source forwards")
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
    identity = {
        "namespace_family": "relational_attention_edges_v1",
        "sources": {name: spec["files"] for name, spec in sorted(config["sources"].items())},
        "model": config["model"],
        "matching": config["matching"],
        "analysis": config["analysis"],
        "exposure": config["exposure"],
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
