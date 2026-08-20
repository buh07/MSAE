#!/usr/bin/env python3
"""Atlas v3.5 attempt-9 technical measurement primitives.

This module deliberately contains no model loader.  It is shared by the
label-free panel builder, the score-bearing inference process, the independent
verifier, and the diagnostic process.  Technical stages are inference-only;
neural training is never authorized by any schema in this file.
"""

from __future__ import annotations

import ast
import base64
import fcntl
import hashlib
import json
import math
import os
import subprocess
import tempfile
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Iterator, Mapping, Sequence

import numpy as np
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey, Ed25519PublicKey


ROOT = Path(__file__).resolve().parents[1]
RUN_ROOT = ROOT / "pilot_runs/20260803_atlas_rope_technical_v5"
ATTEMPT7_ROOT = ROOT / "pilot_runs/20260803_atlas_discovery_v3_3_attempt7"
ATTEMPT7_SCORING = ROOT / "configs/atlas_discovery_v3_3/scoring.json"
SIGNING_KEY_FINGERPRINT = "56308de36cf46c6c18f0a08b54d0884dd88b23e1f612cc4b6c93c9844d72025d"
SIGNING_PUBLIC_KEY_BASE64 = "TTupMmkJYG7oNU26egYLWutbxM2sWzkLCn7xI9TwHXc="

# Attempt 9 re-verifies the already-signed attempt-7 retirement from attempt 8.
RETIREMENT_SCHEMA = "atlas_rope_v4_attempt8_attempt7_retirement_v1"
ATTEMPT8_RETIREMENT_SCHEMA = "atlas_rope_v5_attempt9_attempt8_retirement_v1"
PRESCORE_SCHEMA = "atlas_rope_v5_attempt9_prescore_v1"
PANEL_SCHEMA = "atlas_rope_v5_attempt9_panel_v1"
AUTH_SCHEMA = "atlas_rope_v5_attempt9_stage_authorization_v1"
BUNDLE_SCHEMA = "atlas_rope_v5_attempt9_technical_bundle_v1"
FREEZE_SCHEMA = "atlas_rope_v5_attempt9_validation_freeze_v1"
TERMINAL_SCHEMA = "atlas_rope_v5_attempt9_terminal_v1"

LENGTH_BINS: tuple[tuple[str, int, int], ...] = (
    ("4-8", 4, 8),
    ("9-16", 9, 16),
    ("17-32", 17, 32),
    ("33-64", 33, 64),
    ("65-128", 65, 128),
)
SHIFTS: tuple[int, ...] = (1, 4, 8, 16, 32, 64)
BATCH_SIZE = 64
WIDTH = 768
RTOL = 5e-6
OLD_ATOL_GRID: tuple[float, ...] = (5e-7, 1e-6, 2e-6, 4e-6, 8e-6)
ATOL_GRID: tuple[float, ...] = (*OLD_ATOL_GRID, 2e-5)
REL_L2_GRID: tuple[float, ...] = (2e-6, 5e-6, 1e-5)
COSINE_GRID: tuple[float, ...] = (1e-11, 5e-11, 1e-10)
SAFETY_FACTOR = 1.25
CELL_ROWS = 40
CELL_ELEMENTS = CELL_ROWS * WIDTH
MAX_FAILING_ELEMENTS = math.floor(0.001 * CELL_ELEMENTS)
MAX_FAILING_ROWS = math.floor(0.05 * CELL_ROWS)


def canonical_json_bytes(value: Any) -> bytes:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False
    ).encode("utf-8")


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def read_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError(f"expected JSON object: {path}")
    return value


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    output: list[dict[str, Any]] = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        value = json.loads(line)
        if not isinstance(value, dict):
            raise RuntimeError(f"expected JSON object at {path}:{line_number}")
        output.append(value)
    return output


def _fsync_directory(path: Path) -> None:
    descriptor = os.open(path, os.O_RDONLY | os.O_DIRECTORY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def atomic_json(path: Path, value: Mapping[str, Any]) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    raw = json.dumps(dict(value), indent=2, sort_keys=True, ensure_ascii=False, allow_nan=False) + "\n"
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    with temporary.open("w", encoding="utf-8") as handle:
        handle.write(raw)
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(temporary, path)
    _fsync_directory(path.parent)
    return sha256_bytes(raw.encode("utf-8"))


def atomic_jsonl(path: Path, values: Iterable[Mapping[str, Any]]) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    with temporary.open("w", encoding="utf-8") as handle:
        for value in values:
            handle.write(json.dumps(
                dict(value), sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False
            ) + "\n")
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(temporary, path)
    _fsync_directory(path.parent)
    return sha256_file(path)


def validate_repo_relative(raw: str) -> Path:
    relative = Path(raw)
    if relative.is_absolute() or ".." in relative.parts:
        raise RuntimeError(f"unsafe repository-relative path: {raw}")
    path = (ROOT / relative).resolve()
    if not path.is_relative_to(ROOT):
        raise RuntimeError(f"path escapes repository: {raw}")
    return path


def regular_file(path: Path) -> Path:
    resolved = path.resolve(strict=True)
    if path.is_symlink() or not resolved.is_file():
        raise RuntimeError(f"regular non-symlink file required: {path}")
    return resolved


def load_private_key(path: Path) -> Ed25519PrivateKey:
    resolved = regular_file(path)
    private = serialization.load_pem_private_key(resolved.read_bytes(), password=None)
    if not isinstance(private, Ed25519PrivateKey):
        raise RuntimeError("signing key is not Ed25519")
    public = private.public_key().public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw)
    if hashlib.sha256(public).hexdigest() != SIGNING_KEY_FINGERPRINT:
        raise RuntimeError("signing key fingerprint differs from the frozen signer")
    if base64.b64encode(public).decode("ascii") != SIGNING_PUBLIC_KEY_BASE64:
        raise RuntimeError("signing key public material differs from the frozen signer")
    return private


def sign_payload(payload: Mapping[str, Any], private: Ed25519PrivateKey) -> dict[str, Any]:
    # The signed contract is JSON, not Python container identity. Normalize
    # tuples and all other JSON-compatible containers before both signing and
    # returning the envelope so the in-memory and persisted payloads agree.
    normalized = json.loads(canonical_json_bytes(dict(payload)).decode("utf-8"))
    if not isinstance(normalized, dict):
        raise RuntimeError("signed payload must normalize to a JSON object")
    message = canonical_json_bytes(normalized)
    return {
        "payload": normalized,
        "signature": {
            "algorithm": "Ed25519",
            "message_sha256": sha256_bytes(message),
            "signature_base64": base64.b64encode(private.sign(message)).decode("ascii"),
            "public_key_fingerprint_sha256": SIGNING_KEY_FINGERPRINT,
        },
    }


def verify_envelope(envelope: Mapping[str, Any]) -> dict[str, Any]:
    payload, signature = envelope.get("payload"), envelope.get("signature")
    if not isinstance(payload, Mapping) or not isinstance(signature, Mapping):
        raise RuntimeError("malformed signed envelope")
    if signature.get("algorithm") != "Ed25519" or signature.get("public_key_fingerprint_sha256") not in (None, SIGNING_KEY_FINGERPRINT):
        raise RuntimeError("signed envelope algorithm/signer drift")
    message = canonical_json_bytes(dict(payload))
    if sha256_bytes(message) != signature.get("message_sha256"):
        raise RuntimeError("signed envelope message digest drift")
    public = base64.b64decode(SIGNING_PUBLIC_KEY_BASE64, validate=True)
    if sha256_bytes(public) != SIGNING_KEY_FINGERPRINT:
        raise RuntimeError("embedded public-key fingerprint drift")
    Ed25519PublicKey.from_public_bytes(public).verify(
        base64.b64decode(str(signature.get("signature_base64", "")), validate=True), message
    )
    return dict(payload)


def _write_signing_fault(path: Path, *, temporary: Path, reason: str) -> None:
    """Create an unsigned no-clobber hard stop if post-link identity ever fails."""
    fault = RUN_ROOT / "SIGNING_FAULT.json"
    fault.parent.mkdir(parents=True, exist_ok=True)
    value = {
        "schema_version": "atlas_rope_v5_attempt9_signing_fault_v1",
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
    try:
        with os.fdopen(descriptor, "wb", closefd=True) as handle:
            handle.write(raw)
            handle.flush()
            os.fsync(handle.fileno())
        _fsync_directory(fault.parent)
    except Exception:
        raise


def write_signed(path: Path, payload: Mapping[str, Any], signing_key: Path, *, create_once: bool = True) -> str:
    """Persist a verified signed JSON envelope with atomic no-clobber semantics.

    The exact temporary inode is serialized, fsynced, read back, signature
    verified, and semantically compared before it is hard-linked into place.
    ``os.link`` fails if the destination exists and therefore never overwrites
    a create-once artifact. The final link and temporary are the same inode.
    """
    if not create_once:
        raise RuntimeError("attempt-9 signed artifacts are always create-once")
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
        _fsync_directory(path.parent)
        final_stat = path.stat()
        if ((temporary_stat.st_dev, temporary_stat.st_ino, temporary_stat.st_size) !=
                (final_stat.st_dev, final_stat.st_ino, final_stat.st_size) or
                sha256_file(temporary) != sha256_file(path)):
            _write_signing_fault(path, temporary=temporary, reason="post-link inode/size/hash identity mismatch")
            raise RuntimeError("post-link signed artifact identity mismatch")
        temporary.unlink()
        _fsync_directory(path.parent)
        try:
            final_payload = verify_envelope(read_json(path))
        except Exception as error:
            _write_signing_fault(path, temporary=temporary,
                                 reason=f"post-link signature verification raised {type(error).__name__}: {error}")
            raise
        if final_payload != normalized:
            _write_signing_fault(path, temporary=temporary, reason="post-link signature/semantic verification mismatch")
            raise RuntimeError("post-link signed artifact did not verify")
        return sha256_file(path)
    except Exception:
        # Before a successful link, no final artifact was created. After a link,
        # preserve the verified inode/fault evidence and never delete the final.
        if temporary.exists() and not linked:
            temporary.unlink()
            _fsync_directory(path.parent)
        raise


def recursive_inventory(root: Path) -> dict[str, dict[str, Any]]:
    root = root.resolve(strict=True)
    output: dict[str, dict[str, Any]] = {}
    for path in sorted(root.rglob("*"), key=lambda p: str(p.relative_to(root)).encode("utf-8")):
        relative = str(path.relative_to(root))
        if path.is_symlink():
            raise RuntimeError(f"symlink forbidden in inventoried tree: {path}")
        if path.is_file():
            output[relative] = {"bytes": path.stat().st_size, "sha256": sha256_file(path)}
        elif path.is_dir():
            output[relative + "/"] = {"type": "directory"}
        else:
            raise RuntimeError(f"unsupported object in inventoried tree: {path}")
    return output


def inventory_digest(inventory: Mapping[str, Any]) -> str:
    return sha256_bytes(canonical_json_bytes(dict(inventory)))


def verify_inventory(root: Path, expected: Mapping[str, Any]) -> None:
    observed = recursive_inventory(root)
    if observed != dict(expected):
        raise RuntimeError(f"recursive inventory drift: {root}")


def attempt7_forbidden_outputs() -> tuple[str, ...]:
    return (
        "numerical_qa/GUM",
        "activations",
        "analysis",
        "results",
        "checkpoints",
        "full_extraction_authorization",
    )


def assert_attempt7_terminal_state() -> dict[str, Any]:
    terminal_path = ATTEMPT7_ROOT / "TERMINAL.json"
    terminal = read_json(regular_file(terminal_path))
    payload = terminal.get("payload", {})
    if payload.get("status") != "TERMINAL_TECHNICALLY_INELIGIBLE" or payload.get("no_retry_authorized") is not True:
        raise RuntimeError("attempt 7 is not in its signed no-retry terminal state")
    qa_dirs = sorted((ATTEMPT7_ROOT / "staging").glob("qa-EWT-*"))
    if len(qa_dirs) != 1:
        raise RuntimeError("attempt-7 retained EWT staging inventory drift")
    for relative in attempt7_forbidden_outputs():
        if (ATTEMPT7_ROOT / relative).exists():
            raise RuntimeError(f"attempt-7 forbidden downstream output exists: {relative}")
    forbidden_suffixes = (".pt", ".pth", ".ckpt", ".safetensors")
    if any(path.is_file() and path.name.lower().endswith(forbidden_suffixes) for path in ATTEMPT7_ROOT.rglob("*")):
        raise RuntimeError("attempt-7 contains a neural checkpoint artifact")
    return terminal


def make_attempt7_retirement_payload() -> dict[str, Any]:
    terminal = assert_attempt7_terminal_state()
    inventory = recursive_inventory(ATTEMPT7_ROOT)
    bindings = {
        "attempt7_terminal": {
            "path": str((ATTEMPT7_ROOT / "TERMINAL.json").relative_to(ROOT)),
            "sha256": sha256_file(ATTEMPT7_ROOT / "TERMINAL.json"),
        },
        "attempt7_scoring_config": {
            "path": str(ATTEMPT7_SCORING.relative_to(ROOT)),
            "sha256": sha256_file(ATTEMPT7_SCORING),
        },
        "claim_review": {
            "path": "reports/claim_review/atlas_v3_3_attempt7_post_result_claim_review.md",
            "sha256": sha256_file(ROOT / "reports/claim_review/atlas_v3_3_attempt7_post_result_claim_review.md"),
        },
        "post_result_adversarial_review": {
            "path": "reports/adversarial/atlas_v3_3_attempt7_post_result_review.md",
            "sha256": sha256_file(ROOT / "reports/adversarial/atlas_v3_3_attempt7_post_result_review.md"),
        },
    }
    qa_root = next((ATTEMPT7_ROOT / "staging").glob("qa-EWT-*"))
    bindings["retained_ewt_qa"] = {
        "path": str(qa_root.relative_to(ROOT)),
        "children": recursive_inventory(qa_root),
        "inventory_sha256": inventory_digest(recursive_inventory(qa_root)),
    }
    return {
        "schema_version": RETIREMENT_SCHEMA,
        "status": "RETIRED_NO_RETRY",
        "attempt": "atlas_discovery_v3_3_attempt7",
        "operator_intent": "Retire attempt 7 without changing tolerance, opening GUM, continuing full extraction, or training.",
        "scope_caveat": "This freezes current retained evidence and operator intent; it is not proof against an unlogged historical invocation.",
        "no_retry_authorized": True,
        "terminal_payload_message_sha256": terminal["signature"]["message_sha256"],
        "forbidden_outputs_absent": list(attempt7_forbidden_outputs()),
        "attempt7_tree_inventory": inventory,
        "attempt7_tree_inventory_sha256": inventory_digest(inventory),
        "bindings": bindings,
        "neural_training_authorized": False,
    }


def verify_attempt7_retirement(path: Path) -> dict[str, Any]:
    payload = verify_envelope(read_json(regular_file(path)))
    if payload.get("schema_version") != RETIREMENT_SCHEMA or payload.get("status") != "RETIRED_NO_RETRY":
        raise RuntimeError("unknown/invalid attempt-7 retirement")
    if payload.get("no_retry_authorized") is not True or payload.get("neural_training_authorized") is not False:
        raise RuntimeError("attempt-7 retirement permissions drift")
    verify_inventory(ATTEMPT7_ROOT, payload["attempt7_tree_inventory"])
    if inventory_digest(payload["attempt7_tree_inventory"]) != payload["attempt7_tree_inventory_sha256"]:
        raise RuntimeError("attempt-7 signed inventory digest drift")
    for spec in payload["bindings"].values():
        if "path" in spec and "sha256" in spec:
            target = validate_repo_relative(str(spec["path"]))
            if sha256_file(regular_file(target)) != spec["sha256"]:
                raise RuntimeError(f"retirement binding drift: {spec['path']}")
    assert_attempt7_terminal_state()
    return payload


@contextmanager
def exclusive_lock(name: str) -> Iterator[None]:
    lock_root = RUN_ROOT / "locks"
    lock_root.mkdir(parents=True, exist_ok=True)
    path = lock_root / f"{name}.lock"
    descriptor = os.open(path, os.O_CREAT | os.O_RDWR, 0o600)
    try:
        try:
            fcntl.flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as error:
            raise RuntimeError(f"another attempt-8 process holds lock {name}") from error
        yield
    finally:
        fcntl.flock(descriptor, fcntl.LOCK_UN)
        os.close(descriptor)


def new_staging(stage_name: str, binding_sha256: str) -> Path:
    root = RUN_ROOT / "staging"
    root.mkdir(parents=True, exist_ok=True)
    prefix = f"{stage_name}-{binding_sha256[:12]}-"
    leftovers = sorted(root.glob(prefix + "*"))
    if leftovers:
        raise RuntimeError(f"stale staging requires explicit audit: {leftovers[0]}")
    path = root / f"{prefix}{os.getpid()}"
    path.mkdir()
    return path


def promote(stage: Path, final: Path) -> None:
    if final.exists():
        raise RuntimeError(f"create-once final already exists: {final}")
    for path in sorted(stage.rglob("*")):
        if path.is_file():
            with path.open("rb") as handle:
                os.fsync(handle.fileno())
    _fsync_directory(stage)
    final.parent.mkdir(parents=True, exist_ok=True)
    os.replace(stage, final)
    _fsync_directory(final.parent)


def sequence_sha256(input_ids: Sequence[int]) -> str:
    return sha256_bytes(canonical_json_bytes([int(value) for value in input_ids]))


def normalized_text_hash(text: str) -> str:
    normalized = " ".join(text.casefold().split())
    return sha256_bytes(normalized.encode("utf-8"))


def is_contiguous_subsequence(needle: Sequence[int], haystack: Sequence[int]) -> bool:
    left, right = tuple(map(int, needle)), tuple(map(int, haystack))
    if not left or len(left) > len(right):
        return False
    width = len(left)
    return any(right[start : start + width] == left for start in range(len(right) - width + 1))


def bidirectional_sequence_view_overlap(left: Sequence[int], right: Sequence[int]) -> bool:
    return is_contiguous_subsequence(left, right) or is_contiguous_subsequence(right, left)


def length_bin(length: int) -> str | None:
    for name, lower, upper in LENGTH_BINS:
        if lower <= int(length) <= upper:
            return name
    return None


def selected_positions(length: int) -> tuple[int, int]:
    if length < 1:
        raise RuntimeError("cannot select positions from an empty sequence")
    return ((int(length) - 1) // 3, int(length) - 1)


def stable_utf8_sha256(*parts: Any) -> str:
    raw = "\x1f".join(str(part) for part in parts).encode("utf-8")
    return sha256_bytes(raw)


def deterministic_document_capped_selection(
    candidates: Sequence[Mapping[str, Any]], *, per_bin: int = 20, max_per_document: int = 2, minimum_documents: int = 10
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Select a deterministic, sequence-distinct, document-capped five-bin grid."""

    selected: list[dict[str, Any]] = []
    report: dict[str, Any] = {}
    for bin_name, _, _ in LENGTH_BINS:
        eligible = [dict(row) for row in candidates if row.get("length_bin") == bin_name]
        eligible.sort(key=lambda row: (
            stable_utf8_sha256(row["source"], row["document_id"], row["sent_id"], row["sequence_sha256"]),
            str(row["sent_id"]).encode("utf-8"),
        ))
        counts: dict[str, int] = {}
        sequences: set[str] = set()
        retained: list[dict[str, Any]] = []
        for row in eligible:
            document = str(row["document_id"])
            sequence = str(row["sequence_sha256"])
            if counts.get(document, 0) >= max_per_document or sequence in sequences:
                continue
            retained.append(row)
            counts[document] = counts.get(document, 0) + 1
            sequences.add(sequence)
            if len(retained) == per_bin:
                break
        status = "eligible" if len(retained) == per_bin and len(counts) >= minimum_documents else "ineligible"
        report[bin_name] = {
            "status": status,
            "candidates": len(eligible),
            "retained": len(retained),
            "documents": len(counts),
            "max_per_document": max(counts.values(), default=0),
        }
        if status != "eligible":
            raise RuntimeError(f"technical source cannot fill required bin {bin_name}: {report[bin_name]}")
        selected.extend(retained)
    return selected, report


def make_grid_units(source: str, bases: Sequence[Mapping[str, Any]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    if len(bases) != 100:
        raise RuntimeError("technical grid requires exactly 100 bases")
    reference: list[dict[str, Any]] = []
    for base in bases:
        ids = list(map(int, base["input_ids"]))
        base_id = f"atlas_rope_v5:{source}:base:{stable_utf8_sha256(source, base['document_id'], base['sent_id'], base['sequence_sha256'])[:24]}"
        positions = list(selected_positions(len(ids)))
        row_ids = [f"{base_id}:row:{slot}:{position}" for slot, position in enumerate(positions)]
        unit = {
            "unit_id": base_id + ":reference",
            "base_id": base_id,
            "source": source,
            "document_id": str(base["document_id"]),
            "sent_id": str(base["sent_id"]),
            "length_bin": str(base["length_bin"]),
            "input_ids": ids,
            "attention_mask": [1] * len(ids),
            "position_ids": list(range(len(ids))),
            "positions": positions,
            "row_ids": row_ids,
            "sequence_sha256": str(base["sequence_sha256"]),
            "content_sha256": str(base["content_sha256"]),
        }
        reference.append(unit)
    reference.sort(key=lambda unit: str(unit["unit_id"]).encode("utf-8"))
    # The row manifest is score-bearing: its base-major order must be identical
    # to the sorted reference-cache order.  Construct it only after the
    # canonical reference sort rather than preserving input-selection order.
    rows: list[dict[str, Any]] = []
    for unit in reference:
        rows.extend({
            "row_id": row_id,
            "base_id": str(unit["base_id"]),
            "source": source,
            "length_bin": str(unit["length_bin"]),
            "selected_position": position,
            "document_id": str(unit["document_id"]),
            "sent_id": str(unit["sent_id"]),
        } for row_id, position in zip(unit["row_ids"], unit["positions"], strict=True))
    candidates: list[dict[str, Any]] = []
    for unit in reference:
        for shift in SHIFTS:
            candidate = dict(unit)
            candidate["unit_id"] = f"{unit['base_id']}:shift:{shift}"
            candidate["reference_unit_id"] = unit["unit_id"]
            candidate["shift"] = shift
            candidate["position_ids"] = [int(position) + shift for position in unit["position_ids"]]
            candidate["row_ids"] = [f"{row_id}:shift:{shift}" for row_id in unit["row_ids"]]
            candidates.append(candidate)
    validate_grid_units(reference, candidates, rows, source=source)
    return reference, candidates, rows


def batch_schedule(units: Sequence[Mapping[str, Any]], *, batch_size: int = BATCH_SIZE) -> list[dict[str, Any]]:
    output: list[dict[str, Any]] = []
    for batch_index, start in enumerate(range(0, len(units), batch_size)):
        batch = units[start : start + batch_size]
        maximum = max(len(unit["input_ids"]) for unit in batch)
        output.append({
            "batch_index": batch_index,
            "start": start,
            "stop": start + len(batch),
            "ordered_unit_ids": [str(unit["unit_id"]) for unit in batch],
            "tensor_shape": [len(batch), maximum],
            "max_length": maximum,
            "final_partial": len(batch) < batch_size,
            "padding": {"input_id": 0, "attention_mask": 0, "position_id": 0, "side": "right"},
        })
    return output


def validate_grid_units(
    references: Sequence[Mapping[str, Any]], candidates: Sequence[Mapping[str, Any]], rows: Sequence[Mapping[str, Any]], *, source: str
) -> None:
    if len(references) != 100 or len(candidates) != 600 or len(rows) != 200:
        raise RuntimeError("technical grid logical counts drift")
    if [str(unit["unit_id"]) for unit in references] != sorted(
        (str(unit["unit_id"]) for unit in references), key=lambda value: value.encode("utf-8")
    ):
        raise RuntimeError("reference unit order is not canonical UTF-8 order")
    if len({str(unit["unit_id"]) for unit in references}) != 100 or len({str(unit["unit_id"]) for unit in candidates}) != 600:
        raise RuntimeError("duplicate technical unit ID")
    by_base = {str(unit["base_id"]): unit for unit in references}
    expected_candidates = [(base, shift) for base in by_base for shift in SHIFTS]
    observed_candidates = [(str(unit["base_id"]), int(unit["shift"])) for unit in candidates]
    if observed_candidates != expected_candidates:
        raise RuntimeError("candidate base/shift ordering drift")
    for candidate in candidates:
        reference = by_base[str(candidate["base_id"])]
        for key in ("input_ids", "attention_mask", "positions", "length_bin", "sequence_sha256"):
            if candidate[key] != reference[key]:
                raise RuntimeError(f"translated candidate changes {key}")
        differences = [int(right) - int(left) for left, right in zip(reference["position_ids"], candidate["position_ids"], strict=True)]
        if any(value != int(candidate["shift"]) for value in differences):
            raise RuntimeError("candidate position IDs are not a global translation")
    for base_index, reference in enumerate(references):
        paired_rows = rows[2 * base_index : 2 * base_index + 2]
        if [str(row["base_id"]) for row in paired_rows] != [str(reference["base_id"])] * 2:
            raise RuntimeError("row manifest is not aligned with canonical reference order")
        if [str(row["row_id"]) for row in paired_rows] != list(map(str, reference["row_ids"])):
            raise RuntimeError("row IDs are not aligned with canonical reference order")
        if [int(row["selected_position"]) for row in paired_rows] != list(map(int, reference["positions"])):
            raise RuntimeError("row positions are not aligned with canonical reference order")
    cell_counts: dict[tuple[str, int], int] = {}
    docs: dict[str, set[str]] = {}
    doc_contribution: dict[tuple[str, str], int] = {}
    for unit in references:
        bin_name, document = str(unit["length_bin"]), str(unit["document_id"])
        docs.setdefault(bin_name, set()).add(document)
        doc_contribution[(bin_name, document)] = doc_contribution.get((bin_name, document), 0) + 1
        for shift in SHIFTS:
            cell_counts[(bin_name, shift)] = cell_counts.get((bin_name, shift), 0) + len(unit["positions"])
    if set(cell_counts) != {(name, shift) for name, _, _ in LENGTH_BINS for shift in SHIFTS} or any(count != CELL_ROWS for count in cell_counts.values()):
        raise RuntimeError("required shift-by-length cells are incomplete")
    if any(len(docs.get(name, set())) < 10 for name, _, _ in LENGTH_BINS):
        raise RuntimeError("document support below 10 in a length bin")
    if any(value > 2 for value in doc_contribution.values()):
        raise RuntimeError("document contributes more than two bases in a bin")
    if any(str(unit.get("source")) != source for unit in (*references, *candidates)):
        raise RuntimeError("source role leakage in grid")
    ref_schedule, candidate_schedule = batch_schedule(references), batch_schedule(candidates)
    if [batch["tensor_shape"][0] for batch in ref_schedule] != [64, 36]:
        raise RuntimeError("reference 64+36 schedule drift")
    if [batch["tensor_shape"][0] for batch in candidate_schedule] != [64] * 9 + [24]:
        raise RuntimeError("candidate 9x64+24 schedule drift")


def child_spec(path: Path) -> dict[str, Any]:
    return {"path": str(path.relative_to(ROOT)), "bytes": path.stat().st_size, "sha256": sha256_file(path)}


def canonical_array_hash(array: np.ndarray) -> str:
    value = np.asarray(array)
    if not value.flags.c_contiguous:
        raise RuntimeError("canonical array must be C-contiguous")
    return sha256_bytes(value.tobytes(order="C"))


def exact_cached_replay(
    left: np.ndarray, right: np.ndarray, left_row_ids: Sequence[str], right_row_ids: Sequence[str], *,
    left_child_hash: str, right_child_hash: str,
) -> dict[str, Any]:
    a, b = np.asarray(left), np.asarray(right)
    c_contiguous = bool(a.flags.c_contiguous and b.flags.c_contiguous)
    checks = {
        "row_ids_equal": list(left_row_ids) == list(right_row_ids),
        "row_ids_match_array_rows": len(left_row_ids) == len(right_row_ids) == (a.shape[0] if a.ndim else 0),
        "row_ids_unique": len(left_row_ids) == len(set(left_row_ids)) and len(right_row_ids) == len(set(right_row_ids)),
        "dtype_float32": a.dtype == np.float32 and b.dtype == np.float32,
        "shape_equal": a.shape == b.shape,
        "c_contiguous": c_contiguous,
        "array_equal": bool(np.array_equal(a, b)),
        "c_order_bytes_equal": a.tobytes(order="C") == b.tobytes(order="C"),
        "canonical_hash_equal": c_contiguous and canonical_array_hash(a) == canonical_array_hash(b),
        "declared_child_hashes_present": bool(left_child_hash) and bool(right_child_hash),
    }
    return {"status": "PASS" if all(checks.values()) else "FAIL", "checks": checks,
            "left_child_sha256": left_child_hash, "right_child_sha256": right_child_hash}


@dataclass(frozen=True)
class RowErrorMetrics:
    required_atol: np.ndarray
    relative_l2: np.ndarray
    cosine_distance: np.ndarray
    finite_rows: np.ndarray


def row_error_metrics(reference: np.ndarray, candidate: np.ndarray, *, rtol: float = RTOL) -> RowErrorMetrics:
    left, right = np.asarray(reference), np.asarray(candidate)
    if left.dtype != np.float32 or right.dtype != np.float32 or left.ndim != 2 or right.shape != left.shape:
        raise RuntimeError("metric inputs must be same-shape 2D float32 arrays")
    a, b = left.astype(np.float64), right.astype(np.float64)
    finite_rows = np.isfinite(a).all(axis=1) & np.isfinite(b).all(axis=1)
    difference = np.abs(b - a)
    required = np.maximum(0.0, difference - float(rtol) * np.abs(a))
    difference[~np.isfinite(difference)] = np.inf
    required[~np.isfinite(required)] = np.inf
    relative_l2 = np.linalg.norm(b - a, axis=1) / np.maximum(np.linalg.norm(a, axis=1), 1e-12)
    norm_a, norm_b = np.linalg.norm(a, axis=1), np.linalg.norm(b, axis=1)
    both_zero = (norm_a == 0) & (norm_b == 0)
    one_zero = (norm_a == 0) ^ (norm_b == 0)
    denominator = np.maximum(norm_a * norm_b, 1e-24)
    similarity = np.clip(np.sum(a * b, axis=1) / denominator, -1.0, 1.0)
    cosine = 1.0 - similarity
    cosine[both_zero] = 0.0
    cosine[one_zero] = np.inf
    relative_l2[~finite_rows] = np.inf
    cosine[~finite_rows] = np.inf
    return RowErrorMetrics(required_atol=required, relative_l2=relative_l2,
                           cosine_distance=cosine, finite_rows=finite_rows)


def choose_grid_cap(value: float, grid: Sequence[float], *, safety_factor: float = SAFETY_FACTOR) -> float | None:
    if not math.isfinite(value) or value < 0:
        return None
    target = float(value) * float(safety_factor)
    return next((float(candidate) for candidate in grid if candidate >= target), None)


def derive_caps(calibration_pairs: Sequence[tuple[np.ndarray, np.ndarray]]) -> dict[str, Any]:
    if not calibration_pairs:
        raise RuntimeError("calibration union is empty")
    required_atol = 0.0
    relative_l2 = 0.0
    cosine = 0.0
    rows = 0
    for reference, candidate in calibration_pairs:
        metrics = row_error_metrics(reference, candidate)
        if not metrics.finite_rows.all():
            return {"status": "INELIGIBLE", "reason": "nonfinite_calibration"}
        required_atol = max(required_atol, float(metrics.required_atol.max(initial=0.0)))
        relative_l2 = max(relative_l2, float(metrics.relative_l2.max(initial=0.0)))
        cosine = max(cosine, float(metrics.cosine_distance.max(initial=0.0)))
        rows += int(reference.shape[0])
    caps = {
        "atol": choose_grid_cap(required_atol, ATOL_GRID),
        "relative_l2": choose_grid_cap(relative_l2, REL_L2_GRID),
        "cosine_distance": choose_grid_cap(cosine, COSINE_GRID),
    }
    status = "PASS" if all(value is not None for value in caps.values()) else "INELIGIBLE"
    return {
        "status": status,
        "rtol": RTOL,
        "safety_factor": SAFETY_FACTOR,
        "observed_maxima": {"required_atol": required_atol, "relative_l2": relative_l2, "cosine_distance": cosine},
        "caps": caps,
        "calibration_rows": rows,
        "grids": {"atol": list(ATOL_GRID), "relative_l2": list(REL_L2_GRID), "cosine_distance": list(COSINE_GRID)},
    }


def score_cell(reference: np.ndarray, candidate: np.ndarray, *, atol: float, relative_l2_cap: float,
               cosine_cap: float, strict_zero_failures: bool = False) -> dict[str, Any]:
    metrics = row_error_metrics(reference, candidate)
    left = np.asarray(reference).astype(np.float64)
    right = np.asarray(candidate).astype(np.float64)
    difference = np.abs(right - left)
    bounds = float(atol) + RTOL * np.abs(left)
    coordinate_failures = (~np.isfinite(difference)) | (~np.isfinite(bounds)) | (difference > bounds)
    failing_elements = int(coordinate_failures.sum())
    failing_rows = int(np.any(coordinate_failures, axis=1).sum())
    relative_failures = int((~np.isfinite(metrics.relative_l2) | (metrics.relative_l2 > relative_l2_cap)).sum())
    cosine_failures = int((~np.isfinite(metrics.cosine_distance) | (metrics.cosine_distance > cosine_cap)).sum())
    finite = bool(metrics.finite_rows.all())
    element_budget = 0 if strict_zero_failures else MAX_FAILING_ELEMENTS
    row_budget = 0 if strict_zero_failures else MAX_FAILING_ROWS
    passed = finite and failing_elements <= element_budget and failing_rows <= row_budget and relative_failures == 0 and cosine_failures == 0
    def finite_max(value: np.ndarray) -> float | None:
        return float(value.max(initial=0.0)) if np.isfinite(value).all() else None

    return {
        "status": "PASS" if passed else "FAIL",
        "rows": int(reference.shape[0]),
        "width": int(reference.shape[1]),
        "coordinate_failing_elements": failing_elements,
        "coordinate_failing_rows": failing_rows,
        "relative_l2_failing_rows": relative_failures,
        "cosine_failing_rows": cosine_failures,
        "nonfinite_rows": int((~metrics.finite_rows).sum()),
        "budgets": {"coordinate_failing_elements": element_budget, "coordinate_failing_rows": row_budget,
                    "relative_l2_failing_rows": 0, "cosine_failing_rows": 0},
        "maxima": {
            "absolute_difference": finite_max(difference),
            "required_atol": finite_max(metrics.required_atol),
            "relative_l2": finite_max(metrics.relative_l2),
            "cosine_distance": finite_max(metrics.cosine_distance),
        },
    }


def score_grid(reference: np.ndarray, candidate: np.ndarray, row_records: Sequence[Mapping[str, Any]], *,
               atol: float, relative_l2_cap: float, cosine_cap: float) -> dict[str, Any]:
    if reference.shape != (200, WIDTH) or candidate.shape != (1200, WIDTH):
        raise RuntimeError("grid score array shape drift")
    if len(row_records) != 200:
        raise RuntimeError("grid row-record count drift")
    cell_stats: dict[str, Any] = {}
    candidate_cursor = 0
    # Candidate arrays follow base-major, then shift, then the two selected rows.
    index_by_cell: dict[tuple[str, int], list[int]] = {(name, shift): [] for name, _, _ in LENGTH_BINS for shift in SHIFTS}
    reference_by_cell: dict[tuple[str, int], list[int]] = {(name, shift): [] for name, _, _ in LENGTH_BINS for shift in SHIFTS}
    for base_index in range(100):
        bin_name = str(row_records[2 * base_index]["length_bin"])
        if str(row_records[2 * base_index + 1]["length_bin"]) != bin_name:
            raise RuntimeError("base row length-bin mismatch")
        for shift in SHIFTS:
            index_by_cell[(bin_name, shift)].extend((candidate_cursor, candidate_cursor + 1))
            reference_by_cell[(bin_name, shift)].extend((2 * base_index, 2 * base_index + 1))
            candidate_cursor += 2
    if candidate_cursor != 1200:
        raise RuntimeError("candidate row traversal incomplete")
    for bin_name, _, _ in LENGTH_BINS:
        for shift in SHIFTS:
            ref_indices = reference_by_cell[(bin_name, shift)]
            cand_indices = index_by_cell[(bin_name, shift)]
            if len(ref_indices) != CELL_ROWS or len(cand_indices) != CELL_ROWS:
                raise RuntimeError("missing required grid cell")
            key = f"{bin_name}|shift={shift}"
            cell_stats[key] = score_cell(reference[np.asarray(ref_indices)], candidate[np.asarray(cand_indices)],
                                         atol=atol, relative_l2_cap=relative_l2_cap, cosine_cap=cosine_cap)
    return {"status": "PASS" if all(value["status"] == "PASS" for value in cell_stats.values()) else "FAIL",
            "cells": cell_stats, "required_cells": 30}


def rotate_half_numpy(value: np.ndarray) -> np.ndarray:
    if value.shape[-1] % 2:
        raise RuntimeError("rotary dimension must be even")
    first, second = np.split(value, 2, axis=-1)
    return np.concatenate((-second, first), axis=-1)


def rotary_numpy_float64(value: np.ndarray, positions: np.ndarray, inv_freq: np.ndarray, *, inverse_shift: float = 0.0) -> np.ndarray:
    x = np.asarray(value, dtype=np.float64)
    pos = np.asarray(positions, dtype=np.float64) - float(inverse_shift)
    freq = np.einsum("bt,d->btd", pos, np.asarray(inv_freq, dtype=np.float64))
    embedding = np.concatenate((freq, freq), axis=-1)[:, None, :, :]
    rotary_dim = embedding.shape[-1]
    rotated = x[..., :rotary_dim] * np.cos(embedding) + rotate_half_numpy(x[..., :rotary_dim]) * np.sin(embedding)
    return np.concatenate((rotated, x[..., rotary_dim:]), axis=-1)


def inverse_transport_numpy_float64(value: np.ndarray, delta: int, inv_freq: np.ndarray) -> np.ndarray:
    x = np.asarray(value, dtype=np.float64)
    phase = np.asarray(inv_freq, dtype=np.float64) * (-float(delta))
    embedding = np.concatenate((phase, phase))[None, None, None, :]
    rotary_dim = embedding.shape[-1]
    rotated = x[..., :rotary_dim] * np.cos(embedding) + rotate_half_numpy(x[..., :rotary_dim]) * np.sin(embedding)
    return np.concatenate((rotated, x[..., rotary_dim:]), axis=-1)


def causal_valid_logits(query: np.ndarray, key: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    q, k = np.asarray(query, dtype=np.float64), np.asarray(key, dtype=np.float64)
    if q.shape != k.shape or q.ndim != 4:
        raise RuntimeError("Q/K must have equal [batch,head,token,head_dim] shape")
    logits = np.einsum("bhtd,bhsd->bhts", q, k) / math.sqrt(q.shape[-1])
    token_count = q.shape[2]
    mask = np.tri(token_count, token_count, k=0, dtype=bool)[None, None, :, :]
    mask = np.broadcast_to(mask, logits.shape)
    return logits[mask], mask


FORBIDDEN_AST_TOKENS = (
    "torch.optim", "torch.autograd", "sklearn", "backward", "optimizer", "scheduler",
    "gradient_checkpoint", "save_pretrained", "state_dict",
)
FORBIDDEN_OUTPUT_SUFFIXES = (".pt", ".pth", ".ckpt", ".safetensors", ".joblib", ".pickle", ".pkl")


def static_no_training_scan(paths: Sequence[Path]) -> dict[str, Any]:
    def display_path(path: Path) -> str:
        resolved = path.resolve()
        return str(resolved.relative_to(ROOT)) if resolved.is_relative_to(ROOT) else str(resolved)

    findings: list[dict[str, Any]] = []
    for path in paths:
        source = path.read_text(encoding="utf-8")
        tree = ast.parse(source, filename=str(path))
        for node in ast.walk(tree):
            text = ast.unparse(node) if isinstance(node, (ast.Import, ast.ImportFrom, ast.Call, ast.Attribute)) else ""
            for forbidden in FORBIDDEN_AST_TOKENS:
                if forbidden in text:
                    findings.append({"path": display_path(path), "line": getattr(node, "lineno", 0),
                                     "token": forbidden, "expression": text[:200]})

    return {"status": "PASS" if not findings else "FAIL", "findings": findings,
            "paths": [display_path(path) for path in paths]}


def assert_output_allowlist(root: Path, allowed: set[str]) -> None:
    observed = {str(path.relative_to(root)) for path in root.rglob("*") if path.is_file()}
    if observed != allowed:
        raise RuntimeError(f"output file allowlist drift: missing={sorted(allowed-observed)} extra={sorted(observed-allowed)}")
    if any(path.lower().endswith(FORBIDDEN_OUTPUT_SUFFIXES) for path in observed):
        raise RuntimeError("technical output contains forbidden training/checkpoint suffix")


def soname(path: Path) -> str:
    completed = subprocess.run(["readelf", "-d", str(path)], check=True, capture_output=True, text=True)
    for line in completed.stdout.splitlines():
        if "(SONAME)" in line and "[" in line and "]" in line:
            return line.split("[", 1)[1].split("]", 1)[0]
    return path.name


def loaded_library_attestation(paths: Sequence[Path]) -> list[dict[str, Any]]:
    output: list[dict[str, Any]] = []
    for raw in sorted({str(path.resolve(strict=True)) for path in paths}, key=lambda value: value.encode("utf-8")):
        path = Path(raw)
        output.append({"canonical_path": raw, "soname": soname(path), "sha256": sha256_file(path), "bytes": path.stat().st_size})
    return output


def verify_library_attestation(required: Sequence[Mapping[str, Any]], observed: Sequence[Mapping[str, Any]], *,
                               forbidden_sonames: Sequence[str]) -> dict[str, Any]:
    expected = {(str(row["canonical_path"]), str(row["soname"]), str(row["sha256"])) for row in required}
    actual = {(str(row["canonical_path"]), str(row["soname"]), str(row["sha256"])) for row in observed}
    missing = [list(row) for row in sorted(expected - actual)]
    by_soname: dict[str, set[tuple[str, str]]] = {}
    for row in observed:
        by_soname.setdefault(str(row["soname"]), set()).add((str(row["canonical_path"]), str(row["sha256"])))
    conflicts = {name: [list(row) for row in sorted(values)] for name, values in by_soname.items() if len(values) > 1}
    forbidden = sorted(name for name in forbidden_sonames if name in by_soname)
    passed = not missing and not conflicts and not forbidden
    return {"status": "PASS" if passed else "FAIL", "missing_required": missing,
            "conflicting_duplicate_sonames": conflicts, "forbidden_present": forbidden,
            "extra_observed": [list(row) for row in sorted(actual - expected)]}


def sign_terminal(signing_key: Path, *, status: str, reason: str, lineage: Mapping[str, Any]) -> Path:
    path = RUN_ROOT / "TERMINAL.json"
    payload = {"schema_version": TERMINAL_SCHEMA, "status": status, "reason": reason,
               "lineage": dict(lineage), "no_retry_authorized": True, "neural_training_authorized": False}
    write_signed(path, payload, signing_key)
    return path
