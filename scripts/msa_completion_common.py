#!/usr/bin/env python3
"""Shared deterministic utilities for the additive atlas completion.

The module intentionally has no import-time data access.  Callers must resolve
inputs through :class:`InputFirewall` and attest them in terminal records.
"""

from __future__ import annotations

import hashlib
import fcntl
import json
import math
import os
import platform
import resource
import socket
import sys
import tempfile
import time
import uuid
from dataclasses import dataclass
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

import numpy as np


# Must be present before the first CUDA context is initialized for deterministic
# cuBLAS GEMM/solve behavior.
os.environ.setdefault("CUBLAS_WORKSPACE_CONFIG", ":4096:8")


ROOT = Path(__file__).resolve().parents[1]
EVIDENCE_CLASS = "postscore_amended_architecture_evidence"
FINAL_UNLOCK = ROOT / ".atlas_final_unlock"
PRIVATE_ROOT = (ROOT / "data/atlas_v1/private").resolve()
COMPLETION_FREEZE = ROOT / "configs/atlas_completion/freeze_record.json"
UPSTREAM_INVENTORY = ROOT / "data/atlas_completion_v1/upstream_inventory.json"
_PROCESS_STARTED_MONOTONIC = time.monotonic()
_PROCESS_STARTED_UTC = datetime.now(timezone.utc).isoformat()


class LiveDrawClaimError(RuntimeError):
    """A duplicate worker found the legitimate draw owner still running."""


class StageTerminalError(RuntimeError):
    """A sibling selected the stage terminal before this worker could publish."""


class FrozenClassOmissionError(ValueError):
    """A valid bootstrap map assigned zero weight to a frozen truth class."""


@contextmanager
def stage_publication_lock(stage_dir: Path) -> Iterable[None]:
    """Serialize leaf/terminal publication while allowing expensive compute in parallel."""

    stage_dir.mkdir(parents=True, exist_ok=True)
    lock_path = stage_dir / ".publication.lock"
    with lock_path.open("a+b") as handle:
        fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
        try:
            yield
        finally:
            fcntl.flock(handle.fileno(), fcntl.LOCK_UN)


def sha256_file(path: Path, chunk: int = 8 << 20) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while block := handle.read(chunk):
            digest.update(block)
    return digest.hexdigest()


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def canonical_json_bytes(value: Any) -> bytes:
    return (json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False) + "\n").encode("utf-8")


def atomic_write_bytes(path: Path, payload: bytes, *, create_once: bool = True) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    if create_once and path.exists():
        raise FileExistsError(f"create-once output exists: {path}")
    fd, temp_name = tempfile.mkstemp(prefix=f".{path.name}.tmp.{os.getpid()}.", dir=path.parent)
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        if create_once:
            # Hard-link publication is atomic and refuses an existing name at
            # the filesystem level; unlike check+replace it cannot clobber a
            # concurrently published scientific artifact.
            os.link(temp_name, path)
            os.unlink(temp_name)
            temp_name = ""
        else:
            os.replace(temp_name, path)
            temp_name = ""
        directory_fd = os.open(path.parent, os.O_RDONLY)
        try:
            os.fsync(directory_fd)
        finally:
            os.close(directory_fd)
    except BaseException:
        try:
            if temp_name:
                os.unlink(temp_name)
        except FileNotFoundError:
            pass
        raise
    return sha256_bytes(payload)


def atomic_write_json(path: Path, value: Any, *, create_once: bool = True) -> str:
    return atomic_write_bytes(path, canonical_json_bytes(value), create_once=create_once)


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def stable_hash(*parts: object) -> int:
    payload = "\0".join(str(part) for part in parts).encode("utf-8")
    return int.from_bytes(hashlib.sha256(payload).digest()[:8], "big", signed=False)


def deterministic_seed(base_seed: int, *parts: object) -> int:
    return (int(base_seed) + stable_hash(*parts)) % (2**63)


def utc_now() -> str:
    import datetime as dt

    return dt.datetime.now(dt.timezone.utc).isoformat()


def runtime_environment(device: str | None = None) -> dict[str, Any]:
    row: dict[str, Any] = {
        "python": sys.version,
        "platform": platform.platform(),
        "hostname": socket.gethostname(),
        "pid": os.getpid(),
        "numpy": np.__version__,
    }
    try:
        import sklearn

        row["sklearn"] = sklearn.__version__
    except Exception:
        row["sklearn"] = None
    try:
        import torch

        row.update({"torch": torch.__version__, "cuda": torch.version.cuda, "device_requested": device})
        if device and torch.cuda.is_available():
            d = torch.device(device)
            props = torch.cuda.get_device_properties(d)
            uuid = getattr(props, "uuid", None)
            actual_uuid = None if uuid is None else str(uuid)
            expected_uuid = os.environ.get("MSAE_EXPECTED_GPU_UUID")
            row.update({"cuda_device_name": props.name, "cuda_device_uuid": actual_uuid,
                        "cuda_device_uuid_expected": expected_uuid})
            if expected_uuid and actual_uuid != expected_uuid.removeprefix("GPU-"):
                raise RuntimeError(f"CUDA namespace/UUID drift: expected {expected_uuid}, got {actual_uuid}")
    except RuntimeError as exc:
        if "CUDA namespace/UUID drift" in str(exc):
            raise
        row["torch"] = None
    except Exception:
        row["torch"] = None
    return row


def validated_cuda_environment(device: str) -> dict[str, Any]:
    """Initialize the assigned CUDA namespace and validate its launch-bound UUID before scoring."""

    import torch

    requested = torch.device(device)
    if requested.type != "cuda" or not torch.cuda.is_available():
        raise RuntimeError(f"score-bearing GPU worker requires CUDA: {device}")
    torch.cuda.init()
    environment = runtime_environment(device)
    if not environment.get("cuda_device_name"):
        raise RuntimeError(f"CUDA environment could not be identified: {device}")
    return environment


def seed_provenance(config: Mapping[str, Any], *, contract: str,
                    derived: Mapping[str, int] | None = None) -> dict[str, Any]:
    """Serialize the frozen base seed and any exact derived seeds used by a leaf."""

    return {"base_seed": int(config["seed"]), "contract": contract,
            "derived_seeds": dict(sorted((derived or {}).items()))}


def process_resource_accounting(stage_dir: Path, *, elapsed_sec: float,
                                device: str | None) -> dict[str, Any]:
    """Return direct, labeled process/storage accounting for a terminal marker."""

    storage = sum(path.stat().st_size for path in stage_dir.rglob("*") if path.is_file())
    peak_rss_gib = float(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss) / (1024.0 ** 2)
    peak_cuda_gib: float | None = None
    if device is not None:
        try:
            import torch

            if torch.cuda.is_available() and torch.device(device).type == "cuda":
                peak_cuda_gib = float(torch.cuda.max_memory_allocated(torch.device(device))) / (1024.0 ** 3)
        except Exception:
            peak_cuda_gib = None
    gpu_seconds = float(elapsed_sec) if device is not None and str(device).startswith("cuda") else 0.0
    return {
        "stage_wall_seconds": float(elapsed_sec),
        "recorded_gpu_seconds": gpu_seconds,
        "recorded_gpu_hours": gpu_seconds / 3600.0,
        "peak_host_rss_gib": peak_rss_gib,
        "peak_cuda_memory_gib": peak_cuda_gib,
        "new_storage_bytes_before_terminal": int(storage),
    }


def verify_attestation_current(attestation: Mapping[str, Any]) -> dict[str, Any]:
    """Re-hash a producer's complete opened-input set immediately before terminal publication."""

    verified: dict[str, Any] = {}
    for raw_path, expected in sorted(attestation.items()):
        path = Path(raw_path)
        if expected == {"directory": True}:
            if not path.is_dir():
                raise RuntimeError(f"attested input directory changed before terminal: {path}")
            verified[raw_path] = dict(expected)
            continue
        if (not isinstance(expected, Mapping) or set(expected) != {"sha256", "size"}
                or not path.is_file()):
            raise RuntimeError(f"malformed or absent attested input before terminal: {path}")
        actual = {"sha256": sha256_file(path), "size": path.stat().st_size}
        if actual != dict(expected):
            raise RuntimeError(f"attested input changed before terminal: {path}")
        verified[raw_path] = actual
    return verified


def assert_final_locked() -> None:
    if FINAL_UNLOCK.exists():
        raise RuntimeError("blind-final unlock exists; atlas completion refuses to run")


def verify_parent_bundle_only() -> dict[str, Any]:
    """Verify the parent prescore bundle without opening public role leaves."""

    from atlas_freeze import FREEZE_RECORD, compute_bundle

    expected = read_json(FREEZE_RECORD)
    actual = compute_bundle()
    if (expected.get("bundle_sha256") != actual["bundle_sha256"]
            or expected.get("files") != actual["files"]
            or expected.get("adversarial_digest_quoted") is not True):
        raise RuntimeError("atlas parent prescore bundle differs")
    return expected


def verify_completion_freeze(path: Path = COMPLETION_FREEZE) -> dict[str, Any]:
    """Verify the additive implementation bundle and its immutable parent.

    The freeze record is a bootstrap trust root and is intentionally not a member
    of its own bundle.  Every other score-bearing input/code artifact is bound by
    a sorted ``(path, sha256)`` entry and a digest over those entries.
    """

    assert_final_locked()
    record_path = path.resolve(strict=True)
    record_bytes = record_path.read_bytes()
    record = json.loads(record_bytes)
    if record.get("schema_version") != "atlas_completion_freeze_v1":
        raise RuntimeError("unexpected completion freeze schema")
    entries = record.get("bundle_files")
    if not isinstance(entries, list) or not entries:
        raise RuntimeError("completion freeze has no bundle files")
    normalized: list[dict[str, str]] = []
    seen: set[str] = set()
    for entry in entries:
        if not isinstance(entry, dict) or set(entry) != {"path", "sha256"}:
            raise RuntimeError("malformed completion freeze file entry")
        rel = str(entry["path"])
        if rel in seen or Path(rel).is_absolute() or ".." in Path(rel).parts:
            raise RuntimeError(f"unsafe/duplicate completion freeze path: {rel}")
        seen.add(rel)
        candidate = (ROOT / rel).resolve(strict=True)
        try:
            candidate.relative_to(ROOT.resolve())
        except ValueError as exc:
            raise RuntimeError(f"completion freeze path escapes root: {rel}") from exc
        actual = sha256_file(candidate)
        if actual != entry["sha256"]:
            raise RuntimeError(f"completion freeze hash mismatch: {rel}")
        normalized.append({"path": rel, "sha256": actual})
    if normalized != sorted(normalized, key=lambda row: row["path"]):
        raise RuntimeError("completion freeze entries are not sorted")
    digest = sha256_bytes(canonical_json_bytes(normalized))
    if digest != record.get("bundle_sha256"):
        raise RuntimeError("completion freeze bundle digest mismatch")
    parent = verify_parent_bundle_only()
    if parent.get("bundle_sha256") != record.get("parent_bundle_sha256"):
        raise RuntimeError("completion freeze parent digest mismatch")
    if record.get("parent_bundle_sha256") != record.get("config_parent_bundle_sha256"):
        raise RuntimeError("completion freeze config/parent digest mismatch")
    inventory = ROOT / "data/atlas_completion_v1/upstream_inventory.json"
    if record.get("upstream_inventory_sha256") != sha256_file(inventory):
        raise RuntimeError("completion freeze upstream inventory mismatch")
    if read_json(inventory).get("parent_bundle_sha256") != parent.get("bundle_sha256"):
        raise RuntimeError("upstream inventory parent digest mismatch")
    return {**record, "_freeze_record_sha256": sha256_bytes(record_bytes),
            "_freeze_record_path": str(record_path)}


def require_frozen_completion_config(path: Path) -> dict[str, Any]:
    """Verify the extension and reject unbound score-bearing config overrides."""

    expected = (ROOT / "configs/atlas_completion/analysis.json").resolve(strict=True)
    if path.resolve(strict=True) != expected:
        raise RuntimeError(f"score-bearing config is not the frozen config: {path}")
    return verify_completion_freeze()


def attest_completion_freeze_record(
        firewall: "InputFirewall", completion_freeze: Mapping[str, Any]) -> str:
    """Bind the exact trust-root bytes verified before firewall construction."""

    record_path = Path(str(completion_freeze.get(
        "_freeze_record_path", COMPLETION_FREEZE))).resolve(strict=True)
    expected = completion_freeze.get("_freeze_record_sha256")
    if not isinstance(expected, str):
        raise RuntimeError("verified completion freeze lacks its record-byte digest")
    firewall.register_file(record_path)
    opened = firewall.attest(record_path)
    actual = sha256_file(opened)
    if actual != expected:
        raise RuntimeError("completion freeze record changed after verification")
    return actual


class InputFirewall:
    """Small path resolver/attestor used by completion scripts.

    It is not a Python-wide syscall sandbox.  It centralizes all paths supplied by
    this experiment and makes accidental final-role reads fail before I/O.
    """

    def __init__(self, allowed_roots: Sequence[Path] = (), allowed_files: Sequence[Path] = ()) -> None:
        assert_final_locked()
        self.allowed_roots = {p.resolve() for p in allowed_roots}
        self.allowed_files = {p.resolve() for p in allowed_files}
        self.attestation: dict[str, dict[str, Any]] = {}
        self.verified_parent_activations: set[tuple[str, str]] = set()
        self.verified_parent_transforms: set[tuple[str, str]] = set()
        self.verified_parent_transform_role_sets: set[tuple[str, str, tuple[str, ...]]] = set()
        self.upstream_inventory_required = True

    @staticmethod
    def _blind_final(path: Path, role: str | None) -> bool:
        resolved = path.resolve(strict=False)
        try:
            resolved.relative_to(PRIVATE_ROOT)
            return True
        except ValueError:
            pass
        return role == "final" or resolved == FINAL_UNLOCK.resolve(strict=False)

    def register_root(self, path: Path) -> None:
        self.allowed_roots.add(path.resolve())

    def register_file(self, path: Path) -> None:
        self.allowed_files.add(path.resolve())

    def resolve(self, path: Path, *, role: str | None = None, must_exist: bool = True) -> Path:
        assert_final_locked()
        if self._blind_final(path, role):
            raise PermissionError(f"blind-final input refused before access: {path}")
        resolved = path.resolve(strict=must_exist)
        allowed = resolved in self.allowed_files
        if not allowed:
            for root in self.allowed_roots:
                try:
                    resolved.relative_to(root)
                    allowed = True
                    break
                except ValueError:
                    continue
        if not allowed:
            raise PermissionError(f"unregistered input path: {resolved}")
        if self._blind_final(resolved, role):
            raise PermissionError(f"blind-final canonical input refused: {resolved}")
        return resolved

    def attest(self, path: Path, *, role: str | None = None) -> Path:
        resolved = self.resolve(path, role=role)
        if resolved.is_file():
            current = {"sha256": sha256_file(resolved), "size": resolved.stat().st_size}
            prior = self.attestation.get(str(resolved))
            if prior is not None and prior != current:
                raise RuntimeError(f"input changed after first attestation: {resolved}")
            self.attestation[str(resolved)] = current
        else:
            self.attestation[str(resolved)] = {"directory": True}
        return resolved


def default_firewall(source_run_root: Path, additive_run_root: Path | None = None) -> InputFirewall:
    roots = [
        ROOT / "configs/atlas",
        ROOT / "configs/atlas_completion",
        ROOT / "data/atlas_v1/analysis_rows",
        ROOT / "data/atlas_v1/partitions",
        ROOT / "data/atlas_v1/transforms",
        source_run_root / "raw_activations",
        source_run_root / "k2_transforms",
        ROOT / "results/atlas/raw_v1",
        ROOT / "results/atlas/k2_v1",
        ROOT / "data/atlas_completion_v1",
    ]
    if additive_run_root is not None:
        roots.append(additive_run_root)
    return InputFirewall(roots)


def require_frozen_upstream_file(path: Path, firewall: InputFirewall) -> str:
    """Bind an opened parent artifact to the reviewed additive inventory."""

    if not firewall.upstream_inventory_required:
        opened = firewall.attest(path)
        return sha256_file(opened)
    inventory_path = firewall.attest(UPSTREAM_INVENTORY)
    inventory = read_json(inventory_path)
    if inventory.get("schema_version") != "atlas_completion_upstream_inventory_v1":
        raise RuntimeError("invalid completion upstream inventory")
    resolved = path.resolve()
    try:
        key = str(resolved.relative_to(ROOT.resolve()))
    except ValueError:
        key = str(resolved)
    expected = inventory.get("files", {}).get(key)
    if not isinstance(expected, str):
        raise RuntimeError(f"upstream file absent from frozen inventory: {path}")
    opened = firewall.attest(resolved)
    actual = sha256_file(opened)
    if actual != expected:
        raise RuntimeError(f"upstream file differs from frozen inventory: {path}")
    return actual


def attest_parent_freeze_inputs(firewall: InputFirewall,
                                public_roles: Sequence[str] = ()) -> None:
    """Attest every file opened transitively by atlas_freeze.verify_freeze."""

    if not firewall.upstream_inventory_required:
        return
    inventory = read_json(firewall.attest(UPSTREAM_INVENTORY))
    parent_paths = inventory.get("parent_bundle_files")
    by_role = inventory.get("public_role_files_by_role")
    if not isinstance(parent_paths, list) or not isinstance(by_role, dict):
        raise RuntimeError("upstream inventory lacks role-scoped parent inputs")
    paths = list(parent_paths)
    for role in public_roles:
        if role not in {"discovery", "calibration", "C1", "C2"}:
            raise PermissionError(f"invalid public parent role: {role}")
        role_paths = by_role.get(role)
        if not isinstance(role_paths, list):
            raise RuntimeError(f"upstream inventory lacks public role: {role}")
        paths.extend(role_paths)
    for rel in sorted(set(paths)):
        path = ROOT / str(rel)
        firewall.register_file(path)
        require_frozen_upstream_file(path, firewall)
    freeze_record = ROOT / "configs/atlas/freeze_record.json"
    firewall.register_file(freeze_record)
    require_frozen_upstream_file(freeze_record, firewall)


def verify_parent_freeze_attested(firewall: InputFirewall,
                                  public_roles: Sequence[str] = ()) -> dict[str, Any]:
    """Verify parent bundle and only the explicitly accessed public roles."""

    attest_parent_freeze_inputs(firewall, public_roles)
    parent = verify_parent_bundle_only()
    partition_hashes = read_json(
        firewall.attest(ROOT / "configs/atlas/partition_hashes.json"))
    for role in public_roles:
        for rel, spec in partition_hashes["files"].items():
            if spec.get("access") != "public_analysis" or f"/{role}." not in rel:
                continue
            path = ROOT / rel
            firewall.register_file(path)
            if require_frozen_upstream_file(path, firewall) != spec["sha256"]:
                raise RuntimeError(f"frozen public data artifact differs: {rel}")
    return parent


def register_pinned_hf_snapshot(firewall: InputFirewall,
                                token_manifest: Mapping[str, Any]) -> Path:
    """Validate and register exactly the frozen HF snapshot-to-blob file set."""

    tokenizer = token_manifest["tokenizer"]
    snapshot = Path(tokenizer["snapshot"])
    if not snapshot.is_dir():
        raise FileNotFoundError(f"pinned HF snapshot is absent: {snapshot}")
    snapshot_abs = snapshot.absolute()
    expected_entries = {Path(item["snapshot_path"]).absolute() for item in tokenizer["files"]}
    actual_entries = {path.absolute() for path in snapshot.rglob("*")
                      if path.is_file() or path.is_symlink()}
    if actual_entries != expected_entries:
        missing = sorted(map(str, expected_entries - actual_entries))
        extra = sorted(map(str, actual_entries - expected_entries))
        raise RuntimeError(f"pinned HF snapshot file-set mismatch; missing={missing}, extra={extra}")
    blob_root = (snapshot.parents[1] / "blobs").resolve(strict=True)
    for item in tokenizer["files"]:
        entry = Path(item["snapshot_path"])
        target = Path(item["target_path"]).resolve(strict=True)
        if not entry.is_symlink() or entry.resolve(strict=True) != target or not target.is_file():
            raise RuntimeError(f"pinned HF snapshot/blob mismatch: {entry}")
        try:
            target.relative_to(blob_root)
        except ValueError as exc:
            raise RuntimeError(f"HF blob escapes the pinned repository: {target}") from exc
        if sha256_file(target) != item["sha256"]:
            raise RuntimeError(f"pinned HF blob digest mismatch: {target}")
        firewall.register_file(entry)
        firewall.register_file(target)
        firewall.attest(target)
    return snapshot_abs


@dataclass
class ActivationData:
    x: np.ndarray
    meta: dict[str, np.ndarray]
    records: list[dict[str, Any]]
    units: list[dict[str, Any]]
    row_source: np.ndarray
    row_group: np.ndarray


def load_activation(role: str, layer: int, source_run_root: Path, firewall: InputFirewall) -> ActivationData:
    if role not in {"discovery", "calibration", "C1", "C2"}:
        raise PermissionError(f"non-public activation role refused: {role}")
    verify_parent_activation(source_run_root, role, firewall)
    root = firewall.resolve(source_run_root / "raw_activations" / role, role=role)
    x_path = firewall.attest(root / f"L{layer}.float16.npy", role=role)
    meta_path = firewall.attest(root / "row_meta.npz", role=role)
    records_path = firewall.attest(root / "records.jsonl", role=role)
    units_path = firewall.attest(root / "units.json", role=role)
    x = np.load(x_path, mmap_mode="r")
    with np.load(meta_path) as loaded:
        meta = {key: loaded[key] for key in loaded.files}
    records = [json.loads(line) for line in records_path.read_text().splitlines()]
    units = json.loads(units_path.read_text())
    record_source = np.asarray([row["source"] for row in records], dtype=object)
    record_group = np.asarray([row["document_group"] for row in records], dtype=object)
    return ActivationData(
        x=x,
        meta=meta,
        records=records,
        units=units,
        row_source=record_source[meta["record_index"]],
        row_group=record_group[meta["record_index"]],
    )


def verify_parent_checkpoint(job: str, firewall: InputFirewall) -> dict[str, Any]:
    """Inventory-bind a checkpoint before the legacy parent helper can hash it."""

    metadata_path = ROOT / "reports/provenance/final_checkpoint_metadata.json"
    sha_path = ROOT / "reports/provenance/final_checkpoint_sha256.txt"
    firewall.register_file(metadata_path)
    firewall.register_file(sha_path)
    require_frozen_upstream_file(metadata_path, firewall)
    require_frozen_upstream_file(sha_path, firewall)
    rows = read_json(firewall.attest(metadata_path))
    row = next((item for item in rows if item.get("job_id") == job), None)
    if row is None:
        raise ValueError(f"unknown frozen checkpoint job: {job}")
    expected_by_path = {}
    for line in firewall.attest(sha_path).read_text().splitlines():
        digest, rel = line.split(maxsplit=1)
        expected_by_path[rel.strip()] = digest
    rel = str(row["checkpoint_relpath"])
    expected = expected_by_path.get(rel)
    if expected is None:
        raise RuntimeError(f"checkpoint absent from frozen SHA manifest: {job}")
    path = ROOT / rel
    firewall.register_file(path)
    require_frozen_upstream_file(path, firewall)
    from atlas_freeze import checkpoint_spec

    legacy = checkpoint_spec(job)
    if (Path(legacy["path"]).resolve() != path.resolve()
            or legacy["sha256"] != expected):
        raise RuntimeError(f"legacy checkpoint verification disagrees: {job}")
    return {"metadata": row, "path": path, "sha256": expected}


def verify_parent_activation(source_run_root: Path, role: str,
                             firewall: InputFirewall) -> dict[str, Any]:
    key = (str(source_run_root.resolve()), role)
    from atlas_freeze import verify_activation_complete

    if key not in firewall.verified_parent_activations:
        freeze = verify_parent_freeze_attested(firewall, [role])
        directory = source_run_root / "raw_activations" / role
        require_frozen_upstream_file(directory / "COMPLETE.json", firewall)
        prebound_record = read_json(firewall.attest(
            directory / "COMPLETE.json", role=role))
        for name in prebound_record.get("artifacts", {}):
            require_frozen_upstream_file(directory / name, firewall)
        record = verify_activation_complete(directory, role, freeze)
        firewall.verified_parent_activations.add(key)
        return record
    return read_json(firewall.attest(source_run_root / "raw_activations" / role / "COMPLETE.json",
                                     role=role))


def verify_parent_transform(source_run_root: Path, job: str,
                            firewall: InputFirewall) -> dict[str, Any]:
    key = (str(source_run_root.resolve()), job)
    from atlas_freeze import verify_transform_complete

    if key not in firewall.verified_parent_transforms:
        freeze = verify_parent_freeze_attested(
            firewall, ["discovery", "calibration", "C2"])
        directory = source_run_root / "k2_transforms" / job
        require_frozen_upstream_file(directory / "COMPLETE.json", firewall)
        prebound_record = read_json(firewall.attest(directory / "COMPLETE.json"))
        verify_parent_checkpoint(job, firewall)
        for role in ["discovery", "calibration", "C2"]:
            verify_parent_activation(source_run_root, role, firewall)
        for role, role_record in prebound_record.get("roles", {}).items():
            for name in role_record.get("artifacts", {}):
                require_frozen_upstream_file(directory / role / name, firewall)
        record = verify_transform_complete(directory, job, freeze)
        firewall.verified_parent_transforms.add(key)
        return record
    return read_json(firewall.attest(source_run_root / "k2_transforms" / job / "COMPLETE.json"))


def verify_parent_transform_roles(source_run_root: Path, job: str,
                                  roles: Sequence[str],
                                  firewall: InputFirewall) -> dict[str, Any]:
    """Verify only named public roles without opening confirmation artifacts.

    This is the pilot-safe counterpart to ``verify_parent_transform``.  The
    shared COMPLETE metadata must still enumerate the frozen parent transform,
    but only the requested discovery/calibration activation and array files are
    opened and hashed.
    """

    requested = list(dict.fromkeys(roles))
    if not requested or any(role not in {"discovery", "calibration"} for role in requested):
        raise PermissionError(f"pilot transform roles must be discovery/calibration: {requested}")
    from atlas_freeze import activation_artifact_digest

    cache_key = (str(source_run_root.resolve()), job, tuple(sorted(requested)))
    if cache_key in firewall.verified_parent_transform_role_sets:
        return read_json(firewall.attest(
            source_run_root / "k2_transforms" / job / "COMPLETE.json"))

    freeze = verify_parent_freeze_attested(firewall, requested)
    directory = source_run_root / "k2_transforms" / job
    require_frozen_upstream_file(directory / "COMPLETE.json", firewall)
    record = read_json(firewall.attest(directory / "COMPLETE.json"))
    checkpoint = verify_parent_checkpoint(job, firewall)
    if (record.get("job_id") != job
            or record.get("prescore_bundle_sha256") != freeze["bundle_sha256"]
            or record.get("checkpoint_sha256") != checkpoint["sha256"]
            or set(record.get("roles", {})) != {"discovery", "calibration", "C2"}
            or set(record.get("source_activation_artifact_sha256", {}))
               != {"discovery", "calibration", "C2"}):
        raise RuntimeError(f"parent transform metadata mismatch: {job}")
    for role in requested:
        activation = verify_parent_activation(source_run_root, role, firewall)
        if (record["source_activation_artifact_sha256"][role]
                != activation_artifact_digest(activation)):
            raise RuntimeError(f"parent transform is stale for {job}/{role}")
        artifacts = record["roles"][role].get("artifacts", {})
        if set(artifacts) != {"pos.float16.npy", "content.float16.npy", "resid.float16.npy"}:
            raise RuntimeError(f"parent transform role inventory mismatch: {job}/{role}")
        for name, spec in artifacts.items():
            path = firewall.attest(directory / role / name, role=role)
            require_frozen_upstream_file(path, firewall)
            if path.stat().st_size != spec["bytes"] or sha256_file(path) != spec["sha256"]:
                raise RuntimeError(f"parent transform artifact differs: {path}")
    firewall.verified_parent_transform_role_sets.add(cache_key)
    return record


def verify_parent_raw_calibration(source_run_root: Path,
                                  firewall: InputFirewall) -> dict[str, Any]:
    from atlas_freeze import verify_calibration_sources, verify_layer_trigger

    freeze = verify_parent_freeze_attested(
        firewall, ["discovery", "calibration"])
    result_root = ROOT / "results/atlas/raw_v1"
    trigger = result_root / "layer_trigger_freeze.json"
    require_frozen_upstream_file(result_root / "CALIBRATION_COMPLETE.json", firewall)
    complete = read_json(firewall.attest(result_root / "CALIBRATION_COMPLETE.json"))
    for name, digest in complete.get("artifacts", {}).items():
        path = result_root / name
        require_frozen_upstream_file(path, firewall)
        if sha256_file(path) != digest:
            raise RuntimeError(f"parent raw calibration artifact differs: {path}")
    for role in ["discovery", "calibration"]:
        verify_parent_activation(source_run_root, role, firewall)
    verify_layer_trigger(trigger, freeze)
    verify_calibration_sources(trigger, source_run_root, freeze)
    return complete


def verify_parent_k2_audit(source_run_root: Path, job: str,
                           firewall: InputFirewall) -> dict[str, Any]:
    root = ROOT / "results/atlas/k2_v1"
    require_frozen_upstream_file(root / "COMPLETE.json", firewall)
    complete = read_json(firewall.attest(root / "COMPLETE.json"))
    freeze = verify_parent_freeze_attested(
        firewall, ["discovery", "calibration", "C2"])
    if (complete.get("schema_version") != "atlas_v1_k2_audit_complete"
            or complete.get("prescore_bundle_sha256") != freeze["bundle_sha256"]):
        raise RuntimeError("parent K2 audit terminal metadata mismatch")
    path = root / f"{job}_audit.json"
    require_frozen_upstream_file(path, firewall)
    if complete.get("artifacts", {}).get(path.name) != sha256_file(path):
        raise RuntimeError(f"parent K2 audit artifact differs: {path}")
    transform = verify_parent_transform(source_run_root, job, firewall)
    transform_complete = source_run_root / "k2_transforms" / job / "COMPLETE.json"
    upstream = complete.get("upstream_transforms", {}).get(job, {})
    if (upstream.get("complete_sha256") != sha256_file(transform_complete)
            or upstream.get("checkpoint_sha256") != transform.get("checkpoint_sha256")):
        raise RuntimeError(f"parent K2 audit transform binding mismatch: {job}")
    return read_json(path)


def verify_parent_k2_functional(source_run_root: Path, job: str,
                                firewall: InputFirewall) -> dict[str, Any]:
    root = ROOT / "results/atlas/k2_v1"
    require_frozen_upstream_file(root / f"{job}_functional_COMPLETE.json", firewall)
    marker = read_json(firewall.attest(root / f"{job}_functional_COMPLETE.json"))
    result_path = root / f"{job}_functional.json"
    require_frozen_upstream_file(result_path, firewall)
    transform = verify_parent_transform(source_run_root, job, firewall)
    transform_complete = source_run_root / "k2_transforms" / job / "COMPLETE.json"
    freeze = verify_parent_freeze_attested(
        firewall, ["discovery", "calibration", "C2"])
    if (marker.get("schema_version") != "atlas_v1_k2_functional_complete"
            or marker.get("job_id") != job
            or marker.get("prescore_bundle_sha256") != freeze["bundle_sha256"]
            or marker.get("result_sha256") != sha256_file(result_path)
            or marker.get("source_transform_complete_sha256") != sha256_file(transform_complete)
            or transform.get("job_id") != job):
        raise RuntimeError(f"parent K2 functional binding mismatch: {job}")
    return read_json(result_path)


def load_row_file(path: Path, data: ActivationData, firewall: InputFirewall, *, role: str) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    resolved = firewall.attest(path, role=role)
    analysis_root = (ROOT / "data/atlas_v1/analysis_rows").resolve()
    try:
        resolved.relative_to(analysis_root)
    except ValueError:
        pass
    else:
        require_frozen_upstream_file(resolved, firewall)
    unit_index = {unit["variant_id"]: index for index, unit in enumerate(data.units)}
    counts = np.bincount(data.meta["unit_index"], minlength=len(data.units))
    starts = np.concatenate([[0], np.cumsum(counts[:-1])])
    rows: list[int] = []
    labels: list[str] = []
    seen: set[str] = set()
    for line in resolved.read_text().splitlines():
        item = json.loads(line)
        row_id = str(item["row_id"])
        if row_id in seen:
            raise RuntimeError(f"duplicate row id in {resolved}: {row_id}")
        seen.add(row_id)
        variant, token = row_id.rsplit(":", 1)
        if variant not in unit_index:
            raise RuntimeError(f"row id absent from activation units: {row_id}")
        rows.append(int(starts[unit_index[variant]] + int(token)))
        labels.append(str(item["label"]))
    idx = np.asarray(rows, dtype=np.int64)
    return idx, np.asarray(labels, dtype=str), data.row_source[idx].astype(str), data.row_group[idx].astype(str)


def draw_group_multiplicities(sources: np.ndarray, groups: np.ndarray, *, seed: int) -> dict[tuple[str, str], int]:
    rng = np.random.default_rng(seed)
    return draw_group_multiplicities_rng(sources, groups, rng)


def draw_group_multiplicities_rng(sources: np.ndarray, groups: np.ndarray,
                                  rng: np.random.Generator) -> dict[tuple[str, str], int]:
    result: dict[tuple[str, str], int] = {}
    for source in sorted(np.unique(sources).tolist()):
        unique = np.unique(groups[sources == source])
        if not len(unique):
            raise ValueError(f"source has no groups: {source}")
        sampled = rng.choice(unique, size=len(unique), replace=True)
        values, counts = np.unique(sampled, return_counts=True)
        result.update({(str(source), str(group)): int(count) for group, count in zip(values, counts, strict=True)})
    return result


def unit_group_multiplicities(sources: np.ndarray, groups: np.ndarray) -> dict[tuple[str, str], int]:
    return {(str(source), str(group)): 1 for source, group in zip(sources, groups, strict=True)}


def weights_from_multiplicities(sources: np.ndarray, groups: np.ndarray, multiplicities: Mapping[tuple[str, str], int]) -> np.ndarray:
    return np.asarray([multiplicities.get((str(s), str(g)), 0) for s, g in zip(sources, groups, strict=True)], dtype=np.float64)


def weighted_mean_scale(x: np.ndarray, weights: np.ndarray, *, floor: float = 1e-6) -> tuple[np.ndarray, np.ndarray]:
    values = np.asarray(x, dtype=np.float64)
    w = np.asarray(weights, dtype=np.float64)
    total = float(w.sum())
    if values.ndim != 2 or len(w) != len(values) or total <= 0 or np.any(w < 0):
        raise ValueError("invalid weighted scaler inputs")
    mean = np.sum(values * w[:, None], axis=0) / total
    variance = np.sum(((values - mean) ** 2) * w[:, None], axis=0) / total
    scale = np.sqrt(np.maximum(variance, 0.0))
    scale[scale < floor] = 1.0
    return mean.astype(np.float32), scale.astype(np.float32)


def encode_labels(y: np.ndarray, classes: Sequence[str] | None = None) -> tuple[np.ndarray, np.ndarray]:
    labels = np.asarray(y, dtype=str)
    class_array = np.asarray(sorted(np.unique(labels).tolist()) if classes is None else list(classes), dtype=str)
    lookup = {label: i for i, label in enumerate(class_array.tolist())}
    if any(label not in lookup for label in labels.tolist()):
        raise ValueError("label outside frozen class set")
    return np.asarray([lookup[label] for label in labels.tolist()], dtype=np.int64), class_array


@dataclass
class RidgeResult:
    coef: np.ndarray
    intercept: np.ndarray
    classes: np.ndarray
    alpha: float

    def predict(self, x: np.ndarray) -> np.ndarray:
        scores = np.asarray(x, dtype=np.float32) @ self.coef.T + self.intercept
        if len(self.classes) == 2:
            index = (scores[:, 0] > 0).astype(np.int64)
        else:
            index = np.argmax(scores, axis=1)
        return self.classes[index]


def fit_weighted_ridge_torch(x: np.ndarray, y: np.ndarray, weights: np.ndarray, alpha: float, device: str) -> RidgeResult:
    import torch

    if not device.startswith("cuda") or not torch.cuda.is_available():
        raise RuntimeError("score-bearing ridge requires CUDA")
    torch.backends.cuda.matmul.allow_tf32 = False
    torch.backends.cudnn.allow_tf32 = False
    torch.use_deterministic_algorithms(True)
    encoded, classes = encode_labels(y)
    w_np = np.asarray(weights, dtype=np.float32)
    if not np.isfinite(w_np).all() or np.any(w_np < 0):
        raise ValueError("ridge weights must be finite and nonnegative")
    keep = w_np > 0
    if keep.sum() < 2 or set(np.unique(encoded[keep]).tolist()) != set(np.unique(encoded).tolist()):
        raise ValueError("ridge draw lacks positive weight for every frozen class")
    xt = torch.as_tensor(np.asarray(x[keep], dtype=np.float32), device=device, dtype=torch.float64)
    wt = torch.as_tensor(w_np[keep], device=device, dtype=torch.float64)
    et = torch.as_tensor(encoded[keep], device=device)
    total = wt.sum()
    xmean = (xt * wt[:, None]).sum(0) / total
    xc = xt - xmean
    if len(classes) == 2:
        target = (2.0 * et.to(torch.float64) - 1.0)[:, None]
    else:
        target = torch.full((len(et), len(classes)), -1.0, device=device, dtype=torch.float64)
        target.scatter_(1, et[:, None], 1.0)
    ymean = (target * wt[:, None]).sum(0) / total
    yc = target - ymean
    sw = torch.sqrt(wt)[:, None]
    xw = xc * sw
    yw = yc * sw
    gram = xw.T @ xw
    gram.diagonal().add_(float(alpha))
    rhs = xw.T @ yw
    coef = torch.linalg.solve(gram, rhs).T
    intercept = ymean - coef @ xmean
    return RidgeResult(coef.detach().cpu().numpy().astype(np.float32), intercept.detach().cpu().numpy().astype(np.float32), classes, float(alpha))


def fit_weighted_ridge_grid_torch(x: np.ndarray, y: np.ndarray, weights: np.ndarray, alphas: Sequence[float], device: str) -> list[RidgeResult]:
    """Fit an alpha grid while sharing the expensive weighted sufficient statistics."""

    import torch

    if not device.startswith("cuda") or not torch.cuda.is_available():
        raise RuntimeError("score-bearing ridge requires CUDA")
    torch.backends.cuda.matmul.allow_tf32 = False
    torch.backends.cudnn.allow_tf32 = False
    torch.use_deterministic_algorithms(True)
    encoded, classes = encode_labels(y)
    w_np = np.asarray(weights, dtype=np.float32)
    if not np.isfinite(w_np).all() or np.any(w_np < 0):
        raise ValueError("ridge weights must be finite and nonnegative")
    keep = w_np > 0
    if keep.sum() < 2 or set(np.unique(encoded[keep]).tolist()) != set(np.unique(encoded).tolist()):
        raise ValueError("ridge draw lacks positive weight for every frozen class")
    xt = torch.as_tensor(np.asarray(x[keep], dtype=np.float32), device=device, dtype=torch.float64)
    wt = torch.as_tensor(w_np[keep], device=device, dtype=torch.float64)
    et = torch.as_tensor(encoded[keep], device=device)
    total = wt.sum()
    xmean = (xt * wt[:, None]).sum(0) / total
    xc = xt - xmean
    if len(classes) == 2:
        target = (2.0 * et.to(torch.float64) - 1.0)[:, None]
    else:
        target = torch.full((len(et), len(classes)), -1.0, device=device, dtype=torch.float64)
        target.scatter_(1, et[:, None], 1.0)
    ymean = (target * wt[:, None]).sum(0) / total
    yc = target - ymean
    sw = torch.sqrt(wt)[:, None]
    xw = xc * sw
    yw = yc * sw
    gram = xw.T @ xw
    rhs = xw.T @ yw
    identity = torch.eye(gram.shape[0], dtype=gram.dtype, device=gram.device)
    output = []
    for alpha in alphas:
        coef = torch.linalg.solve(gram + float(alpha) * identity, rhs).T
        intercept = ymean - coef @ xmean
        output.append(RidgeResult(coef.detach().cpu().numpy().astype(np.float32), intercept.detach().cpu().numpy().astype(np.float32), classes, float(alpha)))
    return output


def macro_f1(y: np.ndarray, pred: np.ndarray, weights: np.ndarray | None = None) -> float:
    from sklearn.metrics import f1_score

    truth, prediction = np.asarray(y), np.asarray(pred)
    if len(truth) != len(prediction):
        raise ValueError("truth/prediction length mismatch")
    if weights is None:
        return float(f1_score(truth, prediction, average="macro", zero_division=0))
    w = np.asarray(weights, dtype=np.float64)
    if len(w) != len(truth) or not np.isfinite(w).all() or np.any(w < 0):
        raise ValueError("metric weights must be finite, nonnegative, and aligned")
    keep = w > 0
    if not keep.any() or set(np.unique(truth[keep]).tolist()) != set(np.unique(truth).tolist()):
        raise FrozenClassOmissionError(
            "metric lacks positive weight for every frozen truth class")
    return float(f1_score(truth[keep], prediction[keep], average="macro", zero_division=0,
                          sample_weight=w[keep]))


def chance_score(y_fit: np.ndarray, y_eval: np.ndarray, fit_weights: np.ndarray | None = None, eval_weights: np.ndarray | None = None) -> float:
    fit_values, eval_values = np.asarray(y_fit, dtype=str), np.asarray(y_eval, dtype=str)

    def validate(values: np.ndarray, weights: np.ndarray | None, role: str) -> tuple[np.ndarray, np.ndarray]:
        w = np.ones(len(values), dtype=np.float64) if weights is None else np.asarray(weights, dtype=np.float64)
        if len(w) != len(values) or not np.isfinite(w).all() or np.any(w < 0):
            raise ValueError(f"{role} chance weights are invalid")
        keep = w > 0
        if not keep.any() or set(np.unique(values[keep]).tolist()) != set(np.unique(values).tolist()):
            raise FrozenClassOmissionError(
                f"{role} chance weights omit a frozen class")
        return values[keep], w[keep]

    fit_values, fit_w = validate(fit_values, fit_weights, "fit")
    eval_values, eval_w = validate(eval_values, eval_weights, "eval")
    labels = sorted(set(fit_values.tolist()) | set(eval_values.tolist()))

    def priors(values: np.ndarray, weights: np.ndarray | None) -> dict[str, float]:
        v = np.asarray(values, dtype=str)
        w = np.ones(len(v), dtype=np.float64) if weights is None else np.asarray(weights, dtype=np.float64)
        total = float(w.sum())
        return {label: float(w[v == label].sum() / total) for label in labels}

    fit_prior, eval_prior = priors(fit_values, fit_w), priors(eval_values, eval_w)
    return float(np.mean([0.0 if fit_prior[l] + eval_prior[l] == 0 else 2 * fit_prior[l] * eval_prior[l] / (fit_prior[l] + eval_prior[l]) for l in labels]))


def normalized_recovery(component: float, raw: float, chance: float) -> float | None:
    values = np.asarray([component, raw, chance], dtype=float)
    gap = float(raw - chance)
    if not np.isfinite(values).all() or gap <= 0:
        return None
    return float((component - chance) / gap)


def orthonormal_basis(weight_rows: np.ndarray, rank: int) -> np.ndarray:
    rows = np.asarray(weight_rows, dtype=np.float64)
    _, singular, vt = np.linalg.svd(rows, full_matrices=False)
    if not len(singular) or singular[0] <= 0:
        raise ValueError("zero-rank weight matrix")
    tolerance = max(rows.shape) * np.finfo(float).eps * singular[0]
    effective = min(int(rank), int(np.count_nonzero(singular > tolerance)))
    if effective != int(rank):
        raise ValueError(f"basis rank {effective} != registered {rank}")
    return vt[:rank].T.astype(np.float32)


def project_coords(x: np.ndarray, basis: np.ndarray) -> np.ndarray:
    return np.asarray(x, dtype=np.float32) @ np.asarray(basis, dtype=np.float32)


def project_complement(x: np.ndarray, basis: np.ndarray) -> np.ndarray:
    values = np.asarray(x, dtype=np.float32)
    b = np.asarray(basis, dtype=np.float32)
    return values - (values @ b) @ b.T


def weighted_linear_cka(x: np.ndarray, y: np.ndarray, weights: np.ndarray) -> float | None:
    x64, y64, w = np.asarray(x, dtype=np.float64), np.asarray(y, dtype=np.float64), np.asarray(weights, dtype=np.float64)
    keep = w > 0
    if keep.sum() < 2 or np.any(w < 0):
        return None
    x64, y64, w = x64[keep], y64[keep], w[keep]
    q = w / w.sum()
    xc = x64 - np.sum(x64 * q[:, None], axis=0)
    yc = y64 - np.sum(y64 * q[:, None], axis=0)
    cxy = (xc * q[:, None]).T @ yc
    cxx = (xc * q[:, None]).T @ xc
    cyy = (yc * q[:, None]).T @ yc
    numerator = float(np.sum(cxy * cxy))
    denominator = math.sqrt(float(np.sum(cxx * cxx)) * float(np.sum(cyy * cyy)))
    if not math.isfinite(denominator) or denominator <= np.finfo(float).tiny:
        return None
    return numerator / denominator


def cosine_distance(a: np.ndarray, b: np.ndarray) -> float:
    aa, bb = np.asarray(a, dtype=np.float64), np.asarray(b, dtype=np.float64)
    denom = float(np.linalg.norm(aa) * np.linalg.norm(bb))
    if not math.isfinite(denom) or denom <= 0:
        return float("nan")
    return float(1.0 - np.dot(aa, bb) / denom)


def cosine_matched_direction(source: np.ndarray, target: np.ndarray, *, seed: int) -> tuple[np.ndarray, dict[str, float]]:
    """Return a random delta orthogonal to source/actual delta and matched in raw cosine distance."""

    x = np.asarray(source, dtype=np.float64)
    delta = np.asarray(target, dtype=np.float64) - x
    nx, nd = float(np.linalg.norm(x)), float(np.linalg.norm(delta))
    actual_distance = cosine_distance(x, target)
    cosine = 1.0 - actual_distance
    if nx <= 0 or nd <= 0 or not np.isfinite([nx, nd, actual_distance]).all() or cosine <= 0 or cosine > 1:
        raise ValueError("unmatchable source/target cosine geometry")
    rng = np.random.Generator(np.random.PCG64(seed))
    u = rng.standard_normal(len(x))
    # Stable projection onto span{x,delta}; lstsq handles non-orthogonal vectors.
    span = np.stack([x, delta], axis=1)
    singular = np.linalg.svd(span, compute_uv=False)
    tolerance = max(span.shape) * np.finfo(span.dtype).eps * singular[0]
    if int(np.count_nonzero(singular > tolerance)) != 2:
        raise ValueError("rank-deficient source/actual-delta span")
    u = u - span @ np.linalg.lstsq(span, u, rcond=None)[0]
    nu = float(np.linalg.norm(u))
    if nu <= 1e-12:
        raise ValueError("rank-deficient random direction")
    u /= nu
    magnitude = nx * math.sqrt(max(0.0, 1.0 / (cosine * cosine) - 1.0))
    random_delta = u * magnitude
    random_distance = cosine_distance(x, x + random_delta)
    return random_delta.astype(np.float32), {
        "actual_raw_cosine_distance": actual_distance,
        "random_raw_cosine_distance": random_distance,
        "distance_error": abs(actual_distance - random_distance),
        "absolute_cosine_actual_delta": abs(float(np.dot(u, delta) / nd)),
        "absolute_cosine_source": abs(float(np.dot(u, x) / nx)),
        "scale": magnitude,
    }


def source_equal_score(y: np.ndarray, pred: np.ndarray, sources: np.ndarray, weights: np.ndarray) -> float | None:
    values: list[float] = []
    for source in sorted(np.unique(sources).tolist()):
        mask = sources == source
        if float(np.asarray(weights)[mask].sum()) <= 0:
            return None
        values.append(macro_f1(y[mask], pred[mask], np.asarray(weights)[mask]))
    return float(np.mean(values)) if values else None


def family_summary(recoveries: Mapping[str, Mapping[str, float | None]], assigned: str, nonassigned: Sequence[str], tasks: Sequence[str]) -> dict[str, Any]:
    def task_mean(rep: str) -> float | None:
        values = [recoveries[rep].get(task) for task in tasks]
        if any(value is None or not math.isfinite(float(value)) for value in values):
            return None
        return float(np.mean(values))

    assigned_value = task_mean(assigned)
    leakage_values = {rep: task_mean(rep) for rep in nonassigned}
    if assigned_value is None or any(value is None for value in leakage_values.values()):
        return {"assigned_recovery": assigned_value, "leakage": None, "selectivity_margin": None, "leakage_by_representation": leakage_values}
    leakage = max(float(value) for value in leakage_values.values() if value is not None)
    return {"assigned_recovery": assigned_value, "leakage": leakage, "selectivity_margin": assigned_value - leakage, "leakage_by_representation": leakage_values}


def terminal_state(stage_dir: Path) -> str | None:
    selector = stage_dir / "TERMINAL_STATE.json"
    complete = (stage_dir / "MEASUREMENT_COMPLETE.json").exists()
    stopped = (stage_dir / "FROZEN_EQUIVOCAL_STOP.json").exists()
    if complete and stopped:
        raise RuntimeError(f"stage has conflicting terminal markers: {stage_dir}")
    if selector.exists():
        body = read_json(selector)
        selected = body.get("selected_state")
        if selected not in {"complete", "stopped"}:
            raise RuntimeError(f"invalid terminal selector: {selector}")
        expected_name = ("MEASUREMENT_COMPLETE.json" if selected == "complete"
                         else "FROZEN_EQUIVOCAL_STOP.json")
        opposite_name = ("FROZEN_EQUIVOCAL_STOP.json" if selected == "complete"
                         else "MEASUREMENT_COMPLETE.json")
        if (stage_dir / opposite_name).exists():
            raise RuntimeError(f"terminal selector conflicts with marker: {stage_dir}")
        marker = stage_dir / expected_name
        marker_body = {key: value for key, value in body.items() if key != "selected_state"}
        if not marker.exists():
            # Recover a publisher that won the atomic selector but died before
            # materializing the conventional marker.
            try:
                atomic_write_json(marker, marker_body)
            except FileExistsError:
                pass
        if read_json(marker) != marker_body:
            raise RuntimeError(f"terminal selector/marker payload mismatch: {stage_dir}")
        return str(selected)
    return "complete" if complete else "stopped" if stopped else None


def not_launched_payload(stop: Path, *, skipped_stages: Sequence[str],
                         config_sha256: str,
                         completion_bundle_sha256: str) -> dict[str, Any]:
    """Build the exact root marker for stages skipped after an upstream stop."""

    return {
        "schema_version": "atlas_completion_not_launched_v1",
        "evidence_class": EVIDENCE_CLASS,
        "upstream_stop": str(stop),
        "upstream_stop_sha256": sha256_file(stop),
        "skipped_stages": list(skipped_stages),
        "config_sha256": config_sha256,
        "completion_bundle_sha256": completion_bundle_sha256,
        "recorded_utc": utc_now(),
    }


def write_terminal(stage_dir: Path, *, complete: bool, payload: dict[str, Any]) -> Path:
    stage_dir.mkdir(parents=True, exist_ok=True)
    if terminal_state(stage_dir) is not None:
        raise FileExistsError(f"terminal state already exists: {stage_dir}")
    name = "MEASUREMENT_COMPLETE.json" if complete else "FROZEN_EQUIVOCAL_STOP.json"
    body = dict(payload)
    body.update({"terminal_state": "measurement_complete" if complete else "frozen_equivocal_stop", "evidence_class": EVIDENCE_CLASS, "ended_utc": utc_now()})
    selector_body = {"selected_state": "complete" if complete else "stopped", **body}
    try:
        atomic_write_json(stage_dir / "TERMINAL_STATE.json", selector_body)
    except FileExistsError:
        # The other publisher owns the outcome.  terminal_state also repairs a
        # crash between selector and conventional marker publication.
        terminal_state(stage_dir)
        raise FileExistsError(f"terminal state already exists: {stage_dir}") from None
    try:
        atomic_write_json(stage_dir / name, body)
    except FileExistsError:
        if read_json(stage_dir / name) != body:
            raise RuntimeError(f"terminal marker publication mismatch: {stage_dir}") from None
    return stage_dir / name


def _write_failure_terminal_locked(stage_dir: Path, *, stop_code: str, failed_gate: str,
                           error: BaseException, requested_draw_ids: Sequence[int] = (),
                           completed_draw_ids: Sequence[int] | None = None,
                           input_attestation: Mapping[str, Any] | None = None) -> Path:
    """Durably terminate a launched scientific stage after an unrecoverable failure."""

    stage_dir.mkdir(parents=True, exist_ok=True)
    if terminal_state(stage_dir) is not None:
        return stage_dir / ("MEASUREMENT_COMPLETE.json" if terminal_state(stage_dir) == "complete"
                            else "FROZEN_EQUIVOCAL_STOP.json")
    partial: dict[str, str] = {}
    for path in sorted(stage_dir.rglob("*")):
        relative = path.relative_to(stage_dir)
        if (path.is_file() and ".tmp." not in path.name
                and "claims" not in relative.parts
                and path.name not in {".publication.lock", "TERMINAL_STATE.json",
                                      "MEASUREMENT_COMPLETE.json",
                                      "FROZEN_EQUIVOCAL_STOP.json"}):
            partial[str(relative)] = sha256_file(path)
    registered_complete: list[int] = []
    for registration_path in sorted((stage_dir / "completed_hashes").glob("*.json")):
        try:
            registration = read_json(registration_path)
            artifact = stage_dir / str(registration["artifact"])
            if (registration.get("status") == "complete" and artifact.is_file()
                    and sha256_file(artifact) == registration.get("artifact_sha256")):
                registered_complete.append(int(registration["draw_id"]))
        except Exception:
            # The stop still has to publish if the triggering failure was a
            # malformed registration; retained hashes preserve it for audit.
            continue
    registered_complete = sorted(set(registered_complete))
    completed = (registered_complete if completed_draw_ids is None
                 else sorted(set(map(int, completed_draw_ids))))
    if completed_draw_ids is not None and registered_complete != completed:
        raise RuntimeError(
            f"declared completed draw IDs disagree with registrations: "
            f"declared={completed}, registered={registered_complete}")
    config_path = ROOT / "configs/atlas_completion/analysis.json"
    resolved_config: dict[str, Any] | None = None
    config_sha256: str | None = None
    failure_attestation = dict(input_attestation or {})
    if config_path.is_file():
        resolved_config = read_json(config_path)
        config_sha256 = sha256_file(config_path)
        failure_attestation.setdefault(
            str(config_path.resolve()),
            {"sha256": config_sha256, "size": config_path.stat().st_size})
    argv = list(sys.argv[1:])
    device = argv[argv.index("--device") + 1] if "--device" in argv else None
    try:
        failure_environment = runtime_environment(device)
    except Exception as environment_error:
        failure_environment = {
            "device_requested": device,
            "environment_capture_error_type": type(environment_error).__name__,
            "environment_capture_error": str(environment_error),
        }
    elapsed_sec = max(0.0, time.monotonic() - _PROCESS_STARTED_MONOTONIC)
    payload = {
        "schema_version": "atlas_completion_frozen_stop_v1",
        "stop_code": stop_code,
        "failed_gate": failed_gate,
        "error_type": type(error).__name__,
        "error": str(error),
        "requested_draw_ids": list(requested_draw_ids),
        "completed_draw_ids": completed,
        "retained_partial_sha256": partial,
        "config_sha256": config_sha256,
        "resolved_config": resolved_config,
        "resolved_arguments": {"argv": argv},
        "seed_provenance": (None if resolved_config is None else seed_provenance(
            resolved_config, contract="failure terminal retains the frozen base seed; derived seeds remain in partial leaves")),
        "device": device,
        "started_utc": _PROCESS_STARTED_UTC,
        "environment": failure_environment,
        "resource_accounting": process_resource_accounting(
            stage_dir, elapsed_sec=elapsed_sec, device=device),
        "input_attestation": failure_attestation,
        "scientific_retry_allowed": False,
        "decision_promotion_allowed": False,
    }
    try:
        return write_terminal(stage_dir, complete=False, payload=payload)
    except FileExistsError:
        state = terminal_state(stage_dir)
        if state is None:
            raise
        return stage_dir / ("MEASUREMENT_COMPLETE.json" if state == "complete" else "FROZEN_EQUIVOCAL_STOP.json")


def write_failure_terminal(stage_dir: Path, *, stop_code: str, failed_gate: str,
                           error: BaseException, requested_draw_ids: Sequence[int] = (),
                           completed_draw_ids: Sequence[int] | None = None,
                           input_attestation: Mapping[str, Any] | None = None) -> Path:
    with stage_publication_lock(stage_dir):
        return _write_failure_terminal_locked(
            stage_dir, stop_code=stop_code, failed_gate=failed_gate, error=error,
            requested_draw_ids=requested_draw_ids,
            completed_draw_ids=completed_draw_ids,
            input_attestation=input_attestation)


def require_bound_stage_files(stage_dir: Path, firewall: Any, *,
                              config_sha256: str,
                              completion_bundle_sha256: str,
                              expected_files: Mapping[str, str]) -> dict[str, Any]:
    """Validate an upstream terminal and exact bound artifacts at consumption."""

    if terminal_state(stage_dir) != "complete":
        raise RuntimeError(f"upstream stage is not measurement-complete: {stage_dir}")
    marker_path = firewall.attest(stage_dir / "MEASUREMENT_COMPLETE.json")
    selector = stage_dir / "TERMINAL_STATE.json"
    if selector.exists():
        firewall.attest(selector)
    marker = read_json(marker_path)
    if (marker.get("config_sha256") != config_sha256
            or marker.get("completion_bundle_sha256") != completion_bundle_sha256):
        raise RuntimeError(f"upstream terminal binding mismatch: {stage_dir}")
    for marker_key, filename in expected_files.items():
        path = firewall.attest(stage_dir / filename)
        if marker.get(marker_key) != sha256_file(path):
            raise RuntimeError(f"upstream artifact hash mismatch: {stage_dir / filename}")
    return marker


def require_registered_series_artifact(stage_dir: Path, artifact: Path, *,
                                       draw_id: int | str, firewall: Any,
                                       config_sha256: str,
                                       completion_bundle_sha256: str) -> dict[str, Any]:
    """Validate a raw point/draw against its complete terminal at K2 use time."""

    marker = require_bound_stage_files(
        stage_dir, firewall, config_sha256=config_sha256,
        completion_bundle_sha256=completion_bundle_sha256,
        expected_files={})
    artifact = firewall.attest(artifact)
    relative = str(artifact.relative_to(stage_dir))
    if marker.get("artifact_sha256", {}).get(relative) != sha256_file(artifact):
        raise RuntimeError(f"series terminal artifact mismatch: {artifact}")
    if draw_id != "point":
        registry = stage_dir / "completed_hashes" / f"{int(draw_id):04d}.json"
        registry = firewall.attest(registry)
        registry_relative = str(registry.relative_to(stage_dir))
        registration = read_json(registry)
        if (marker.get("artifact_sha256", {}).get(registry_relative) != sha256_file(registry)
                or registration.get("draw_id") != int(draw_id)
                or registration.get("status") != "complete"
                or registration.get("artifact_sha256") != sha256_file(artifact)
                or registration.get("config_sha256") != config_sha256
                or registration.get("completion_bundle_sha256") != completion_bundle_sha256):
            raise RuntimeError(f"series draw registration mismatch: {artifact}")
    return marker


def _claim_draw_locked(stage_dir: Path, draw_id: int, config_sha256: str) -> Path:
    claims = stage_dir / "claims"
    claims.mkdir(parents=True, exist_ok=True)
    path = claims / f"{draw_id:04d}"
    try:
        path.mkdir()
    except FileExistsError:
        claim_file = path / "claim.json"
        if not claim_file.is_file():
            raise RuntimeError(f"existing draw claim lacks metadata: {path}")
        prior = read_json(claim_file)
        if prior.get("host") != socket.gethostname():
            raise RuntimeError(f"cannot prove remote draw claim is stale: {path}")
        pid = int(prior.get("pid", -1))
        alive = pid > 0
        if alive:
            try:
                os.kill(pid, 0)
            except ProcessLookupError:
                alive = False
            except PermissionError:
                alive = True
        if alive:
            raise LiveDrawClaimError(f"draw is claimed by live PID {pid}: {path}")
        quarantine = stage_dir / "invalid_partial" / "stale_claims"
        quarantine.mkdir(parents=True, exist_ok=True)
        destination = quarantine / f"{draw_id:04d}.{uuid.uuid4().hex}"
        os.rename(path, destination)
        path.mkdir()
    atomic_write_json(path / "claim.json", {"draw_id": draw_id, "host": socket.gethostname(), "pid": os.getpid(), "started_utc": utc_now(), "config_sha256": config_sha256})
    return path


def claim_draw(stage_dir: Path, draw_id: int, config_sha256: str) -> Path:
    with stage_publication_lock(stage_dir):
        if terminal_state(stage_dir) is not None:
            raise StageTerminalError(f"stage became terminal before draw claim: {stage_dir}")
        return _claim_draw_locked(stage_dir, draw_id, config_sha256)


def release_claim(path: Path) -> None:
    for child in path.iterdir():
        child.unlink()
    path.rmdir()


def register_draw_artifact(stage_dir: Path, draw_id: int, artifact: Path, *, status: str,
                           config_sha256: str, completion_bundle_sha256: str) -> Path:
    if status not in {"complete", "failed"}:
        raise ValueError(status)
    registry = stage_dir / "completed_hashes"
    registry.mkdir(parents=True, exist_ok=True)
    path = registry / f"{draw_id:04d}.json"
    atomic_write_json(path, {"draw_id": draw_id, "status": status,
                             "artifact": str(artifact.relative_to(stage_dir)),
                             "artifact_sha256": sha256_file(artifact),
                             "config_sha256": config_sha256,
                             "completion_bundle_sha256": completion_bundle_sha256,
                             "registered_utc": utc_now()})
    return path


def _prepare_draw_resume_locked(stage_dir: Path, draw_id: int, *, config_sha256: str,
                        completion_bundle_sha256: str) -> str:
    """Validate or recover a draw before claim; never replace a registered chunk."""

    output = stage_dir / "draws" / f"{draw_id:04d}.json"
    error = stage_dir / "errors" / f"{draw_id:04d}.json"
    registry = stage_dir / "completed_hashes" / f"{draw_id:04d}.json"
    quarantine = stage_dir / "invalid_partial" / "orphan_temporaries"
    for parent in [stage_dir / "draws", stage_dir / "errors"]:
        if parent.exists():
            for temporary in parent.glob(f".{draw_id:04d}.json.tmp.*"):
                quarantine.mkdir(parents=True, exist_ok=True)
                os.rename(temporary, quarantine / f"{temporary.name}.{uuid.uuid4().hex}")
    if output.exists() and error.exists():
        raise RuntimeError(f"draw has both result and error artifact: {draw_id}")
    artifact, status = (output, "complete") if output.exists() else ((error, "failed") if error.exists() else (None, None))
    if registry.exists():
        registration = read_json(registry)
        if artifact is None:
            raise RuntimeError(f"registered draw artifact is absent: {draw_id}")
        expected = {"draw_id": draw_id, "status": status, "artifact_sha256": sha256_file(artifact),
                    "config_sha256": config_sha256,
                    "completion_bundle_sha256": completion_bundle_sha256}
        if any(registration.get(key) != value for key, value in expected.items()):
            raise RuntimeError(f"registered draw artifact mismatch: {draw_id}")
        return str(status)
    if artifact is None:
        return "absent"
    try:
        row = read_json(artifact)
        if row.get("draw_id") != draw_id or row.get("config_sha256") != config_sha256 or row.get("completion_bundle_sha256") != completion_bundle_sha256:
            raise RuntimeError("unregistered artifact metadata mismatch")
    except Exception:
        destination_dir = stage_dir / "invalid_partial" / "unregistered_artifacts"
        destination_dir.mkdir(parents=True, exist_ok=True)
        os.rename(artifact, destination_dir / f"{artifact.name}.{uuid.uuid4().hex}")
        return "absent"
    register_draw_artifact(stage_dir, draw_id, artifact, status=str(status),
                           config_sha256=config_sha256,
                           completion_bundle_sha256=completion_bundle_sha256)
    return str(status)


def prepare_draw_resume(stage_dir: Path, draw_id: int, *, config_sha256: str,
                        completion_bundle_sha256: str) -> str:
    with stage_publication_lock(stage_dir):
        if terminal_state(stage_dir) is not None:
            raise StageTerminalError(f"stage became terminal before draw recovery: {stage_dir}")
        return _prepare_draw_resume_locked(
            stage_dir, draw_id, config_sha256=config_sha256,
            completion_bundle_sha256=completion_bundle_sha256)


def _maybe_finalize_draw_stage_locked(stage_dir: Path, *, requested_draws: int,
                              minimum_complete_draws: int,
                              config_sha256: str,
                              completion_bundle_sha256: str,
                              schema_version: str,
                              expected_shards: Sequence[tuple[int, int]] = (),
                              extra: Mapping[str, Any] | None = None) -> Path | None:
    """Write the sole stage terminal when point plus every draw registration exist."""

    if terminal_state(stage_dir) is not None:
        return None
    point = stage_dir / "point.json"
    if not point.is_file():
        return None
    shard_paths = [stage_dir / f"shard_{start:04d}_{end:04d}.json"
                   for start, end in expected_shards]
    if any(not path.is_file() for path in shard_paths):
        return None
    registrations = []
    for draw in range(requested_draws):
        path = stage_dir / "completed_hashes" / f"{draw:04d}.json"
        if not path.is_file():
            return None
        row = read_json(path)
        if (row.get("draw_id") != draw
                or row.get("config_sha256") != config_sha256
                or row.get("completion_bundle_sha256") != completion_bundle_sha256):
            raise RuntimeError(f"invalid draw registration during finalization: {path}")
        artifact = stage_dir / row["artifact"]
        if not artifact.is_file() or sha256_file(artifact) != row.get("artifact_sha256"):
            raise RuntimeError(f"registered artifact mismatch during finalization: {path}")
        registrations.append(row)
    scientifically_finite: list[int] = []
    input_attestation: dict[str, Any] = {}
    provenance_payloads: list[dict[str, Any]] = []
    point_payload = read_json(point)
    if (point_payload.get("draw_id") != "point"
            or point_payload.get("config_sha256") != config_sha256
            or point_payload.get("completion_bundle_sha256") != completion_bundle_sha256):
        raise RuntimeError(f"point metadata mismatch during finalization: {point}")
    point_scientific = point_payload.get("result", point_payload)
    point_finite = point_scientific.get("finite") is True
    provenance_payloads.append(point_payload)
    input_attestation.update(point_payload.get("input_attestation", {}))
    for shard_path, (start, end) in zip(shard_paths, expected_shards, strict=True):
        shard = read_json(shard_path)
        if (shard.get("draw_start") != start or shard.get("draw_end") != end
                or shard.get("config_sha256") != config_sha256
                or shard.get("completion_bundle_sha256") != completion_bundle_sha256):
            raise RuntimeError(f"shard metadata mismatch during finalization: {shard_path}")
        provenance_payloads.append(shard)
        for path, attestation in shard.get("input_attestation", {}).items():
            if path in input_attestation and input_attestation[path] != attestation:
                raise RuntimeError(f"conflicting input attestation across shard artifacts: {path}")
            input_attestation[path] = attestation
    for registration in registrations:
        result_row = read_json(stage_dir / registration["artifact"])
        if (result_row.get("draw_id") != registration["draw_id"]
                or result_row.get("config_sha256") != config_sha256
                or result_row.get("completion_bundle_sha256") != completion_bundle_sha256):
            raise RuntimeError(f"draw metadata mismatch during finalization: {registration['artifact']}")
        provenance_payloads.append(result_row)
        for path, attestation in result_row.get("input_attestation", {}).items():
            if path in input_attestation and input_attestation[path] != attestation:
                raise RuntimeError(f"conflicting input attestation across draw artifacts: {path}")
            input_attestation[path] = attestation
        if registration["status"] != "complete":
            continue
        scientific = result_row.get("result", result_row)
        if scientific.get("finite") is True:
            scientifically_finite.append(int(registration["draw_id"]))
    finite = len(scientifically_finite)
    failed = [int(row["draw_id"]) for row in registrations if row["status"] == "failed"]
    artifacts = {str(point.relative_to(stage_dir)): sha256_file(point)}
    point_models = stage_dir / "point_models.pkl"
    if point_models.is_file():
        artifacts[str(point_models.relative_to(stage_dir))] = sha256_file(point_models)
    artifacts.update({str((stage_dir / row["artifact"]).relative_to(stage_dir)): row["artifact_sha256"]
                      for row in registrations})
    artifacts.update({
        str((stage_dir / "completed_hashes" / f"{int(row['draw_id']):04d}.json").relative_to(stage_dir)):
        sha256_file(stage_dir / "completed_hashes" / f"{int(row['draw_id']):04d}.json")
        for row in registrations
    })
    artifacts.update({str(path.relative_to(stage_dir)): sha256_file(path)
                      for path in shard_paths})
    if schema_version.startswith("atlas_completion"):
        required = {"resolved_config", "resolved_arguments", "seed_provenance",
                    "environment", "started_utc", "ended_utc", "input_attestation"}
        for row in provenance_payloads:
            missing = sorted(required - set(row))
            if missing:
                raise RuntimeError(
                    f"score-bearing leaf lacks required provenance {missing}: "
                    f"{row.get('schema_version', row.get('draw_id'))}")
            if (row["resolved_config"] != point_payload["resolved_config"]
                    or row["seed_provenance"].get("base_seed")
                    != point_payload["seed_provenance"].get("base_seed")):
                raise RuntimeError("score-bearing leaves disagree on resolved config/base seed")
        verify_attestation_current(input_attestation)
        extension = verify_completion_freeze()
        if extension.get("bundle_sha256") != completion_bundle_sha256:
            raise RuntimeError("completion freeze changed before draw-stage terminal publication")
        parent_after = verify_parent_bundle_only()
        parent_after_sha256 = parent_after["bundle_sha256"]
    else:
        parent_after_sha256 = None
    worker_payloads = [point_payload, *[read_json(path) for path in shard_paths]]
    elapsed_values = [float(row.get("elapsed_sec", 0.0)) for row in worker_payloads]
    starts = [str(row["started_utc"]) for row in worker_payloads if row.get("started_utc")]
    ends = [str(row["ended_utc"]) for row in worker_payloads if row.get("ended_utc")]
    wall_seconds = None
    if starts and ends:
        wall_seconds = (max(datetime.fromisoformat(value) for value in ends)
                        - min(datetime.fromisoformat(value) for value in starts)).total_seconds()
    environments = []
    seen_environments: set[bytes] = set()
    for row in worker_payloads:
        environment = row.get("environment")
        if not isinstance(environment, dict):
            continue
        encoded = canonical_json_bytes(environment)
        if encoded not in seen_environments:
            seen_environments.add(encoded)
            environments.append(environment)
    terminal_provenance = {
        "resolved_config": point_payload.get("resolved_config"),
        "resolved_arguments": point_payload.get("resolved_arguments"),
        "seed_provenance": {
            "base_seed": point_payload.get("seed_provenance", {}).get("base_seed"),
            "contract": "per-leaf derived seeds are bound in retained point/draw/error/shard artifacts",
        },
        "started_utc": min(starts) if starts else None,
        "environments": environments,
        "resource_accounting": {
            "stage_wall_seconds": wall_seconds,
            "recorded_worker_gpu_seconds": float(sum(elapsed_values)),
            "recorded_worker_gpu_hours": float(sum(elapsed_values)) / 3600.0,
            "new_storage_bytes_before_terminal": int(sum(
                (stage_dir / relative).stat().st_size for relative in artifacts)),
            "worker_records": len(worker_payloads),
        },
        "parent_bundle_reverified_after_stage_sha256": parent_after_sha256,
        "completion_bundle_reverified_after_stage_sha256": (
            completion_bundle_sha256 if schema_version.startswith("atlas_completion") else None),
    }
    complete = point_finite and finite >= minimum_complete_draws
    if complete:
        payload = {"schema_version": schema_version, "requested_draws": requested_draws,
                   "config_sha256": config_sha256,
                   "point_scientifically_finite": point_finite,
                   "finite_draws": finite,
                   "scientifically_finite_draw_ids": scientifically_finite,
                   "failed_draws": failed,
                   "completion_bundle_sha256": completion_bundle_sha256,
                   "artifact_sha256": dict(sorted(artifacts.items())),
                   "input_attestation": dict(sorted(input_attestation.items()))}
    else:
        registered_complete = [int(row["draw_id"]) for row in registrations
                               if row["status"] == "complete"]
        if not point_finite:
            stop_code = "point_scientifically_nonfinite"
            failed_gate = "required_point_finiteness"
            reason = "required point estimate was scientifically nonfinite"
        else:
            stop_code = "insufficient_scientifically_finite_draws"
            failed_gate = "minimum_complete_draws"
            reason = (f"only {finite} of {requested_draws} registered draws were "
                      f"scientifically finite; minimum is {minimum_complete_draws}")
        payload = {
            "schema_version": "atlas_completion_frozen_stop_v1",
            "stop_code": stop_code,
            "failed_gate": failed_gate,
            "reason": reason,
            "requested_draw_ids": list(range(requested_draws)),
            "completed_draw_ids": scientifically_finite,
            "registered_complete_draw_ids": registered_complete,
            "failed_draw_ids": failed,
            "requested_draws": requested_draws,
            "minimum_complete_draws": minimum_complete_draws,
            "point_scientifically_finite": point_finite,
            "finite_draws": finite,
            "scientifically_finite_draw_ids": scientifically_finite,
            "retained_partial_sha256": dict(sorted(artifacts.items())),
            "config_sha256": config_sha256,
            "completion_bundle_sha256": completion_bundle_sha256,
            "input_attestation": dict(sorted(input_attestation.items())),
            "scientific_retry_allowed": False,
            "decision_promotion_allowed": False,
        }
    payload.update(terminal_provenance)
    payload.update(dict(extra or {}))
    try:
        return write_terminal(stage_dir, complete=complete, payload=payload)
    except FileExistsError:
        return None


def maybe_finalize_draw_stage(stage_dir: Path, *, requested_draws: int,
                              minimum_complete_draws: int,
                              config_sha256: str,
                              completion_bundle_sha256: str,
                              schema_version: str,
                              expected_shards: Sequence[tuple[int, int]] = (),
                              extra: Mapping[str, Any] | None = None) -> Path | None:
    with stage_publication_lock(stage_dir):
        return _maybe_finalize_draw_stage_locked(
            stage_dir, requested_draws=requested_draws,
            minimum_complete_draws=minimum_complete_draws,
            config_sha256=config_sha256,
            completion_bundle_sha256=completion_bundle_sha256,
            schema_version=schema_version, expected_shards=expected_shards,
            extra=extra)


def stage_timer() -> tuple[float, str]:
    return time.monotonic(), utc_now()
