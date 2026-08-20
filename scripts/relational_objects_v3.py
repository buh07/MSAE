#!/usr/bin/env python3
"""Deterministic contracts for the relational-objects v3 development study."""

from __future__ import annotations

import base64
import hashlib
import json
import os
from pathlib import Path
import tempfile
from typing import Any, Iterable, Mapping

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey, Ed25519PublicKey

ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "configs/relational_objects_v3/run.json"
NAMESPACE = "relational_objects_v3_opened_development1"


def canonical_bytes(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(4 * 1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def stable_hex(*parts: object) -> str:
    return hashlib.sha256("|".join(map(str, parts)).encode()).hexdigest()


def atomic_bytes(path: Path, raw: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(dir=path.parent, prefix=f".{path.name}.", delete=False) as handle:
        handle.write(raw)
        handle.flush()
        os.fsync(handle.fileno())
        temporary = Path(handle.name)
    os.replace(temporary, path)
    fd = os.open(path.parent, os.O_DIRECTORY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def atomic_json(path: Path, value: Any) -> str:
    raw = canonical_bytes(value) + b"\n"
    atomic_bytes(path, raw)
    return hashlib.sha256(raw).hexdigest()


def atomic_jsonl(path: Path, rows: Iterable[Mapping[str, Any]]) -> tuple[str, int]:
    raw = b"".join(canonical_bytes(dict(row)) + b"\n" for row in rows)
    atomic_bytes(path, raw)
    return hashlib.sha256(raw).hexdigest(), raw.count(b"\n")


def exclusive_json(path: Path, value: Any) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    raw = canonical_bytes(value) + b"\n"
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


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]


def recursive_inventory(root: Path) -> list[dict[str, Any]]:
    return [
        {"path": path.relative_to(ROOT).as_posix(), "sha256": sha256_file(path), "bytes": path.stat().st_size}
        for path in sorted(root.rglob("*"), key=lambda p: p.as_posix().encode())
        if path.is_file()
    ]


def load_private_key(path: Path) -> Ed25519PrivateKey:
    key = serialization.load_pem_private_key(path.read_bytes(), password=None)
    if not isinstance(key, Ed25519PrivateKey):
        raise TypeError("signing key is not Ed25519")
    return key


def signed_payload(payload: Mapping[str, Any], key: Ed25519PrivateKey) -> dict[str, Any]:
    raw = canonical_bytes(dict(payload))
    public = key.public_key().public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw)
    return {
        "payload": dict(payload),
        "signature": {
            "algorithm": "Ed25519",
            "message_sha256": hashlib.sha256(raw).hexdigest(),
            "public_key_base64": base64.b64encode(public).decode(),
            "public_key_fingerprint_sha256": hashlib.sha256(public).hexdigest(),
            "signature_base64": base64.b64encode(key.sign(raw)).decode(),
        },
    }


def sign_json(path: Path, payload: Mapping[str, Any], key: Ed25519PrivateKey, *, exclusive: bool = False) -> str:
    envelope = signed_payload(payload, key)
    return exclusive_json(path, envelope) if exclusive else atomic_json(path, envelope)


def verify_signed(path: Path, expected_fingerprint: str | None = None) -> dict[str, Any]:
    envelope = load_json(path)
    payload, signature = envelope["payload"], envelope["signature"]
    raw = canonical_bytes(payload)
    if hashlib.sha256(raw).hexdigest() != signature["message_sha256"]:
        raise ValueError(f"signed message digest mismatch: {path}")
    public = base64.b64decode(signature["public_key_base64"])
    if hashlib.sha256(public).hexdigest() != signature["public_key_fingerprint_sha256"]:
        raise ValueError(f"signer fingerprint mismatch: {path}")
    if expected_fingerprint is not None and signature["public_key_fingerprint_sha256"] != expected_fingerprint:
        raise ValueError(f"unexpected lifecycle signer: {path}")
    Ed25519PublicKey.from_public_bytes(public).verify(base64.b64decode(signature["signature_base64"]), raw)
    return payload


def study_key(config: Mapping[str, Any]) -> str:
    identity = {
        "namespace": config["namespace"],
        "plan": config["identity"]["plan"],
        "implementation": config["identity"]["implementation"],
        "sources": config["sources"],
        "model": config["model"],
        "runtime": config["runtime"],
    }
    return hashlib.sha256(canonical_bytes(identity)).hexdigest()
