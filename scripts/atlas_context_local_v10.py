#!/usr/bin/env python3
"""Attempt-14 contracts: deterministic data, inference-only forwards, analysis, and signing.

No representation or neural training is authorized or reachable from this module.
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
CONFIG = ROOT / "configs/atlas_context_local_v10/run.json"
FINAL_FREEZE = ROOT / "configs/atlas_context_local_v10/FINAL_FREEZE.json"
SCIENCE_AUTHORIZATION = ROOT / "configs/atlas_context_local_v10/SCIENCE_AUTHORIZATION.json"
CANDIDATE_REVIEW = ROOT / "reports/adversarial/atlas_v3_10_attempt14_candidate_review.md"
PLAN_REVIEW = ROOT / "reports/adversarial/atlas_v3_10_attempt14_plan_review_ship.md"
PLAN = ROOT / "PLAN_ATTEMPT14.md"
NAMESPACE = "atlas_context_local_v10_attempt14"


def canonical_json_bytes(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode("utf-8")


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(4 * 1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def stable_hex(*parts: object) -> str:
    return hashlib.sha256("|".join(map(str, parts)).encode()).hexdigest()


def stable_u64(*parts: object) -> int:
    return int(stable_hex(*parts)[:16], 16)


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(x) for x in path.read_text(encoding="utf-8").splitlines() if x]


def atomic_bytes(path: Path, raw: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(dir=path.parent, prefix=f".{path.name}.", delete=False) as f:
        f.write(raw); f.flush(); os.fsync(f.fileno()); tmp = Path(f.name)
    os.replace(tmp, path)


def atomic_json(path: Path, value: Any) -> str:
    raw = canonical_json_bytes(value) + b"\n"
    atomic_bytes(path, raw)
    return hashlib.sha256(raw).hexdigest()


def atomic_jsonl(path: Path, rows: Iterable[Mapping[str, Any]]) -> tuple[str, int]:
    raw = b"".join(canonical_json_bytes(dict(x)) + b"\n" for x in rows)
    atomic_bytes(path, raw)
    return hashlib.sha256(raw).hexdigest(), raw.count(b"\n")


def recursive_inventory(root: Path, exclude: Sequence[str] = ()) -> list[dict[str, Any]]:
    if not root.exists():
        return []
    exc = set(exclude); files: list[Path] = []
    for p in root.rglob("*"):
        if p.is_symlink():
            raise RuntimeError(f"symlink forbidden: {p}")
        if p.is_file() and p.relative_to(root).as_posix() not in exc:
            files.append(p)
        elif not p.is_file() and not p.is_dir():
            raise RuntimeError(f"unclassified path: {p}")
    files.sort(key=lambda p: p.relative_to(root).as_posix().encode())
    return [{"path": p.relative_to(root).as_posix(), "bytes": p.stat().st_size, "sha256": sha256_file(p)} for p in files]


def inventory_digest(entries: Sequence[Mapping[str, Any]]) -> str:
    return hashlib.sha256(canonical_json_bytes(list(entries))).hexdigest()


def load_signing_key(path: Path, signer: Mapping[str, Any]) -> Ed25519PrivateKey:
    key = serialization.load_pem_private_key(path.read_bytes(), password=None)
    if not isinstance(key, Ed25519PrivateKey):
        raise RuntimeError("not Ed25519")
    raw = key.public_key().public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw)
    if signer != {"algorithm": "Ed25519", "public_key_base64": base64.b64encode(raw).decode(),
                   "public_key_fingerprint_sha256": hashlib.sha256(raw).hexdigest()}:
        raise RuntimeError("signing key mismatch")
    return key


def sign_payload(path: Path, payload: Mapping[str, Any], key: Ed25519PrivateKey) -> str:
    body = canonical_json_bytes(dict(payload))
    pub = key.public_key().public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw)
    env = {"envelope_schema_version": "atlas_context_local_v10_attempt14_signed_envelope_v1",
        "payload": dict(payload), "signature": {"algorithm": "Ed25519",
        "message_sha256": hashlib.sha256(body).hexdigest(),
        "public_key_base64": base64.b64encode(pub).decode(),
        "public_key_fingerprint_sha256": hashlib.sha256(pub).hexdigest(),
        "signature_base64": base64.b64encode(key.sign(body)).decode()}}
    return atomic_json(path, env)


def verify_signed(path: Path, expected_fingerprint: str, *, allow_legacy_envelope: bool = False) -> dict[str, Any]:
    env = read_json(path); payload = env.get("payload"); sig = env.get("signature")
    if not isinstance(payload, dict) or not isinstance(sig, dict):
        raise RuntimeError(f"malformed signed file: {path}")
    body = canonical_json_bytes(payload); pub = base64.b64decode(sig["public_key_base64"], validate=True)
    fp = hashlib.sha256(pub).hexdigest()
    if ((not allow_legacy_envelope and env.get("envelope_schema_version") != "atlas_context_local_v10_attempt14_signed_envelope_v1")
        or sig.get("algorithm") != "Ed25519" or fp != expected_fingerprint
        or sig.get("public_key_fingerprint_sha256") != fp or sig.get("message_sha256") != hashlib.sha256(body).hexdigest()):
        raise RuntimeError(f"signed metadata mismatch: {path}")
    Ed25519PublicKey.from_public_bytes(pub).verify(base64.b64decode(sig["signature_base64"], validate=True), body)
    return payload


def verify_candidate_review(path: Path, freeze_sha: str, inventory_sha: str) -> None:
    lines = path.read_text().splitlines()
    if not lines or lines[0] != "VERDICT: SHIP" or [x for x in lines if x.startswith("VERDICT:")] != ["VERDICT: SHIP"]:
        raise RuntimeError("candidate review is not an unambiguous SHIP")
    required = {f"FINAL_FREEZE_SHA256: {freeze_sha}", f"CANDIDATE_INVENTORY_SHA256: {inventory_sha}"}
    if not required.issubset(set(lines)):
        raise RuntimeError("candidate review bindings mismatch")


def normalized_pair_delta(a: np.ndarray, b: np.ndarray, floor: float = 1e-12) -> np.ndarray:
    a = np.asarray(a, np.float64); b = np.asarray(b, np.float64)
    if a.shape != b.shape or a.ndim != 2:
        raise ValueError("pair matrices mismatch")
    den = np.maximum(np.maximum(np.linalg.norm(a, axis=1), np.linalg.norm(b, axis=1)), floor)
    return np.linalg.norm(a - b, axis=1) / den


def normalized_vector_norm(delta: np.ndarray, left: np.ndarray, right: np.ndarray, floor: float = 1e-12) -> np.ndarray:
    delta = np.asarray(delta, np.float64); left = np.asarray(left, np.float64); right = np.asarray(right, np.float64)
    den = np.maximum(np.maximum(np.linalg.norm(left, axis=1), np.linalg.norm(right, axis=1)), floor)
    return np.linalg.norm(delta, axis=1) / den


def projector(matrix: np.ndarray, rank: int, ratio_floor: float) -> tuple[np.ndarray | None, dict[str, Any]]:
    x = np.asarray(matrix, np.float64)
    distinct = len({row.tobytes() for row in x})
    if x.ndim != 2 or len(x) < rank or distinct < rank or not np.isfinite(x).all():
        return None, {"eligible": False, "rows": len(x), "distinct_rows": distinct, "reason": "row_support"}
    from scipy.linalg import eigh
    gram = x @ x.T
    values, left = eigh(gram, subset_by_index=[len(x)-rank, len(x)-1], driver="evr")
    order = np.argsort(values)[::-1]; values = np.maximum(values[order], 0.0); left = left[:, order]
    s = np.sqrt(values)
    ratio = float(s[rank-1] / s[0]) if s.size >= rank and s[0] > 0 else 0.0
    if s.size < rank or ratio < ratio_floor or s[-1] <= 0:
        return None, {"eligible": False, "rows": len(x), "distinct_rows": distinct, "rank_ratio": ratio, "reason": "rank"}
    basis, _ = np.linalg.qr(x.T @ (left / s[None, :]))
    return basis, {"eligible": True, "rows": len(x), "distinct_rows": distinct, "rank_ratio": ratio}


def capture_rows(delta: np.ndarray, basis: np.ndarray, floor: float = 1e-12) -> np.ndarray:
    x = np.asarray(delta, np.float64)
    den = np.sum(x*x, axis=1); num = np.sum((x @ basis)**2, axis=1)
    return np.divide(num, den, out=np.zeros_like(num), where=den > floor)


def complement_rows(delta: np.ndarray, basis: np.ndarray, floor: float = 1e-12) -> np.ndarray:
    x = np.asarray(delta, np.float64); residual = x - (x @ basis) @ basis.T
    den = np.sum(x*x, axis=1); num = np.sum(residual*residual, axis=1)
    return np.divide(num, den, out=np.zeros_like(num), where=den > floor)


def gate4_energy_rows(dtrue: np.ndarray, dunrelated: np.ndarray, basis: np.ndarray, floor: float = 1e-12) -> np.ndarray:
    """Frozen common-denominator projected-energy contrast, including sub-floor rows."""
    a=np.asarray(dtrue,np.float64); b=np.asarray(dunrelated,np.float64)
    num=np.sum((a@basis)**2,axis=1)-np.sum((b@basis)**2,axis=1)
    den=np.sum(a*a,axis=1)+np.sum(b*b,axis=1)
    return num / np.maximum(den,floor)


def bootstrap_indices(uniform_u64: np.ndarray, n: int) -> np.ndarray:
    if n <= 0: raise ValueError("empty bootstrap population")
    # Multiplication-high maps an unsigned 64-bit uniform variate to [0,n) without float rounding.
    flat = uniform_u64.astype(object).ravel()
    out = np.fromiter(((int(x) * n) >> 64 for x in flat), dtype=np.int64, count=len(flat))
    return out.reshape(uniform_u64.shape)


def production_forward(model: Any, rows: Sequence[Mapping[str, Any]], device: str = "cuda:0") -> tuple[np.ndarray, np.ndarray]:
    """One inference-only, same-component five-condition batch per row."""
    import torch
    targets: list[np.ndarray] = []; controls: list[np.ndarray] = []
    for row in rows:
        true = list(row["true_prefix_ids"]); unrelated = list(row["unrelated_prefix_ids"])
        target = list(row["target_segment_ids"]); sub = list(row["substituted_target_segment_ids"])
        if len(true) != len(unrelated) or len(target) != len(sub):
            raise RuntimeError("geometry mismatch")
        ids = [true+target, true+target, unrelated+target, unrelated+target, true+sub]
        if len({len(x) for x in ids}) != 1:
            raise RuntimeError("condition lengths mismatch")
        p = len(true); L = len(ids[0])
        masks = [[0]*p+[1]*(L-p), [1]*L, [0]*p+[1]*(L-p), [1]*L, [1]*L]
        input_ids = torch.tensor(ids, dtype=torch.long, device=device)
        attention_mask = torch.tensor(masks, dtype=torch.long, device=device)
        position_ids = torch.arange(L, dtype=torch.long, device=device).unsqueeze(0).expand(5, -1)
        with torch.inference_mode():
            out = model(input_ids=input_ids, attention_mask=attention_mask, position_ids=position_ids,
                        use_cache=False, output_hidden_states=True, return_dict=True)
        h = out.hidden_states[4].to(dtype=torch.float32)
        ti = int(row["target_sequence_index"]); ci = int(row["control_sequence_index"])
        targets.append(h[:, ti, :].cpu().numpy()); controls.append(h[:, ci, :].cpu().numpy())
    return np.stack(targets).astype(np.float32), np.stack(controls).astype(np.float32)
