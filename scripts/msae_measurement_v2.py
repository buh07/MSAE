"""Pure, prescore utilities for the draft Atlas/MSAE measurement-v2 protocol.

This module deliberately has no model, network, process, or GPU dependencies.  It
operates on labels, group identifiers, cached arrays, and explicit digests only.
"""

from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass
import hashlib
import json
import math
import os
from pathlib import Path
import stat
from typing import Any, Iterable, Mapping, Sequence

import numpy as np


SCHEMA_VERSION = "atlas_measurement_v2_draft"
FORBIDDEN_PATH_TOKENS = frozenset({"private", "final", "blind", "unlock"})
VALID_STATUSES = frozenset({"eligible", "ineligible", "not_run"})


@dataclass(frozen=True)
class SupportThresholds:
    min_groups: int
    min_class_groups: int
    max_rows_per_group: int
    bootstrap_draws: int
    min_finite_draws: int
    seed: int

    def __post_init__(self) -> None:
        if self.min_groups < 1 or self.min_class_groups < 1 or self.max_rows_per_group < 1:
            raise ValueError("support thresholds must be positive")
        if self.bootstrap_draws < 1 or not 0 <= self.min_finite_draws <= self.bootstrap_draws:
            raise ValueError("invalid bootstrap completeness threshold")


def _utf8_key(value: str) -> bytes:
    return value.encode("utf-8")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def canonical_json_bytes(value: Any) -> bytes:
    return (json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False) + "\n").encode("utf-8")


def _validate_sha256(value: Any, field: str) -> str:
    if not isinstance(value, str) or len(value) != 64:
        raise ValueError(f"{field} must be a SHA-256 hex digest")
    try:
        int(value, 16)
    except ValueError as error:
        raise ValueError(f"{field} must be a SHA-256 hex digest") from error
    return value.lower()


def _path_has_forbidden_token(path: Path) -> bool:
    for part in path.parts:
        normalized = part.lower()
        tokens = normalized.replace("-", ".").replace("_", ".").split(".")
        if FORBIDDEN_PATH_TOKENS.intersection(tokens):
            return True
    return False


def _require_relative_path(raw_path: str) -> Path:
    path = Path(raw_path)
    if path.is_absolute() or not path.parts or any(part in {"", ".", ".."} for part in path.parts):
        raise ValueError(f"path must be a normalized repository-relative path: {raw_path!r}")
    if _path_has_forbidden_token(path):
        raise ValueError(f"forbidden path component in {raw_path!r}")
    return path


def _is_relative_to(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
    except ValueError:
        return False
    return True


def _reject_symlink_chain(path: Path, stop: Path) -> None:
    """Reject an existing symlink at any component from stop through path."""
    stop_resolved = stop.resolve(strict=True)
    if stop.is_symlink():
        raise ValueError(f"symlink repository/root is forbidden: {stop}")
    try:
        relative = path.absolute().relative_to(stop.absolute())
    except ValueError as error:
        raise ValueError(f"path escapes root: {path}") from error
    current = stop
    for part in relative.parts:
        current = current / part
        if current.is_symlink():
            raise ValueError(f"symlink path component is forbidden: {current}")
    # The comparison also catches aliases in an ancestor above stop.
    if not _is_relative_to(path.resolve(strict=False), stop_resolved):
        raise ValueError(f"resolved path escapes root: {path}")


def _reject_any_symlink_component(path: Path) -> None:
    absolute = path.absolute()
    current = Path(absolute.anchor)
    for part in absolute.parts[1:]:
        current = current / part
        if current.is_symlink():
            raise ValueError(f"symlink path component is forbidden: {current}")


def resolve_allowlisted_inputs(
    repository_root: Path,
    entries: Sequence[Mapping[str, Any]],
    allowed_roots: Sequence[Path],
) -> list[Path]:
    """Validate the complete input plan before a caller opens any row file."""
    repository_root = repository_root.absolute()
    _reject_any_symlink_component(repository_root)
    if not repository_root.is_dir() or repository_root.is_symlink():
        raise ValueError("repository root must be a real directory")
    canonical_repository = repository_root.resolve(strict=True)

    canonical_allowed: list[Path] = []
    for root in allowed_roots:
        absolute_root = root if root.is_absolute() else repository_root / root
        _reject_symlink_chain(absolute_root, repository_root)
        if not absolute_root.is_dir():
            raise ValueError(f"allowed input root is not a directory: {root}")
        resolved_root = absolute_root.resolve(strict=True)
        if not _is_relative_to(resolved_root, canonical_repository):
            raise ValueError(f"allowed input root escapes repository: {root}")
        if _path_has_forbidden_token(resolved_root.relative_to(canonical_repository)):
            raise ValueError(f"forbidden allowed input root: {root}")
        canonical_allowed.append(resolved_root)

    resolved_inputs: list[Path] = []
    expected_digests: list[str] = []
    seen: set[Path] = set()
    for entry in entries:
        relative = _require_relative_path(str(entry.get("path", "")))
        expected_digest = _validate_sha256(entry.get("sha256"), "sha256")
        candidate = repository_root / relative
        _reject_symlink_chain(candidate, repository_root)
        try:
            mode = candidate.stat().st_mode
        except FileNotFoundError as error:
            raise ValueError(f"allowlisted input is missing: {relative}") from error
        if not stat.S_ISREG(mode):
            raise ValueError(f"allowlisted input is not a regular file: {relative}")
        resolved = candidate.resolve(strict=True)
        if not any(_is_relative_to(resolved, root) for root in canonical_allowed):
            raise ValueError(f"allowlisted input is outside approved roots: {relative}")
        if resolved in seen:
            raise ValueError(f"duplicate allowlisted input: {relative}")
        seen.add(resolved)
        resolved_inputs.append(resolved)
        expected_digests.append(expected_digest)

    # Only after the entire path plan is structurally safe do we open files for
    # digest verification.
    for entry, resolved, expected_digest in zip(entries, resolved_inputs, expected_digests):
        observed_digest = sha256_file(resolved)
        if observed_digest != expected_digest:
            raise ValueError(f"digest mismatch for {entry['path']}: expected {expected_digest}, got {observed_digest}")
    return resolved_inputs


def validate_output_root(repository_root: Path, output_relative: str, allowed_parent: Path) -> Path:
    repository_root = repository_root.absolute()
    _reject_any_symlink_component(repository_root)
    relative = _require_relative_path(output_relative)
    output = repository_root / relative
    parent = allowed_parent if allowed_parent.is_absolute() else repository_root / allowed_parent
    _reject_symlink_chain(parent, repository_root)
    if not parent.is_dir():
        raise ValueError("output parent must be an existing real directory")
    if output.parent.absolute() != parent.absolute():
        raise ValueError("output root must be a direct child of the approved parent")
    _reject_symlink_chain(output, repository_root)
    if os.path.lexists(output):
        raise ValueError(f"output root already exists: {output}")
    if not _is_relative_to(output.resolve(strict=False), parent.resolve(strict=True)):
        raise ValueError("output root escapes approved parent")
    return output


def source_from_group(group: str, role: str, prefix_map: Mapping[str, Mapping[str, str]]) -> str:
    role_map = prefix_map.get(role)
    if role_map is None:
        raise ValueError(f"unrecognized role: {role}")
    matches = [source for prefix, source in role_map.items() if group.startswith(prefix)]
    if len(matches) != 1:
        qualifier = "unmatched" if not matches else "multiply matched"
        raise ValueError(f"{qualifier} document_group prefix for role {role}: {group}")
    return matches[0]


def _hash_group_index(*, role: str, task: str, source: str, draw: int, slot: int, seed: int, n: int) -> int:
    payload = f"atlas_measurement_v2|{seed}|{role}|{task}|{source}|{draw}|{slot}".encode("utf-8")
    return int.from_bytes(hashlib.sha256(payload).digest()[:8], "big", signed=False) % n


def _bootstrap_finite_count(
    rows_by_source: Mapping[str, Sequence[Mapping[str, Any]]],
    *,
    role: str,
    task: str,
    thresholds: SupportThresholds,
    nuisance_pooled: bool,
) -> int:
    source_group_labels: dict[str, dict[str, set[str]]] = {}
    source_targets: dict[str, set[str]] = {}
    for source in sorted(rows_by_source, key=_utf8_key):
        groups: dict[str, set[str]] = defaultdict(set)
        for row in rows_by_source[source]:
            groups[str(row["document_group"])].add(str(row["label"]))
        source_group_labels[source] = dict(groups)
        source_targets[source] = set().union(*groups.values()) if groups else set()

    pooled_targets = set().union(*source_targets.values()) if source_targets else set()
    finite = 0
    for draw in range(thresholds.bootstrap_draws):
        observed_by_source: dict[str, set[str]] = {}
        for source in sorted(source_group_labels, key=_utf8_key):
            group_map = source_group_labels[source]
            group_ids = sorted(group_map, key=_utf8_key)
            observed: set[str] = set()
            for slot in range(len(group_ids)):
                index = _hash_group_index(
                    role=role,
                    task=task,
                    source=source,
                    draw=draw,
                    slot=slot,
                    seed=thresholds.seed,
                    n=len(group_ids),
                )
                observed.update(group_map[group_ids[index]])
            observed_by_source[source] = observed
        if nuisance_pooled:
            draw_is_finite = set().union(*observed_by_source.values()) >= pooled_targets
        else:
            draw_is_finite = all(observed_by_source[source] >= source_targets[source] for source in source_targets)
        finite += int(draw_is_finite)
    return finite


def audit_task_support(
    rows: Sequence[Mapping[str, Any]],
    *,
    role: str,
    task: str,
    expected_sources: Sequence[str],
    thresholds: SupportThresholds,
    nuisance_pooled: bool = False,
) -> dict[str, Any]:
    if not expected_sources or len(set(expected_sources)) != len(expected_sources):
        raise ValueError("expected_sources must be a non-empty unique list")
    required_fields = {"document_group", "source", "label", "row_id"}
    rows_by_source: dict[str, list[Mapping[str, Any]]] = {source: [] for source in expected_sources}
    seen_row_ids: set[str] = set()
    for row in rows:
        missing = required_fields.difference(row)
        if missing:
            raise ValueError(f"row missing fields: {sorted(missing)}")
        row_id = str(row["row_id"])
        if row_id in seen_row_ids:
            raise ValueError(f"duplicate row_id: {row_id}")
        seen_row_ids.add(row_id)
        source = str(row["source"])
        if source not in rows_by_source:
            raise ValueError(f"unexpected source for {role}/{task}: {source}")
        rows_by_source[source].append(row)

    reasons: set[str] = set()
    source_reports: dict[str, Any] = {}
    pooled_class_groups: dict[str, set[str]] = defaultdict(set)
    for source in expected_sources:
        source_rows = rows_by_source[source]
        group_counts = Counter(str(row["document_group"]) for row in source_rows)
        class_groups: dict[str, set[str]] = defaultdict(set)
        for row in source_rows:
            group = str(row["document_group"])
            class_groups[str(row["label"])].add(group)
            pooled_class_groups[str(row["label"])].add(group)
        report = {
            "rows": len(source_rows),
            "groups": len(group_counts),
            "class_group_counts": {label: len(groups) for label, groups in sorted(class_groups.items(), key=lambda x: _utf8_key(x[0]))},
            "max_rows_per_group": max(group_counts.values(), default=0),
        }
        source_reports[source] = report
        if report["groups"] < thresholds.min_groups:
            reasons.add("minimum_groups")
        if report["max_rows_per_group"] > thresholds.max_rows_per_group:
            reasons.add("maximum_group_contribution")
        if not nuisance_pooled:
            if len(class_groups) < 2 or any(len(groups) < thresholds.min_class_groups for groups in class_groups.values()):
                reasons.add("minimum_class_groups")

    pooled_counts = {label: len(groups) for label, groups in sorted(pooled_class_groups.items(), key=lambda x: _utf8_key(x[0]))}
    if nuisance_pooled and (len(pooled_counts) < 2 or any(count < thresholds.min_class_groups for count in pooled_counts.values())):
        reasons.add("minimum_class_groups")

    finite_draws = 0
    if all(rows_by_source.values()):
        finite_draws = _bootstrap_finite_count(
            rows_by_source,
            role=role,
            task=task,
            thresholds=thresholds,
            nuisance_pooled=nuisance_pooled,
        )
    if finite_draws < thresholds.min_finite_draws:
        reasons.add("bootstrap_completeness")

    return {
        "role": role,
        "task": task,
        "status": "eligible" if not reasons else "ineligible",
        "reasons": sorted(reasons, key=_utf8_key),
        "sources": source_reports,
        "pooled_class_group_counts": pooled_counts if nuisance_pooled else None,
        "bootstrap": {
            "draws": thresholds.bootstrap_draws,
            "finite_draws": finite_draws,
            "minimum_finite_draws": thresholds.min_finite_draws,
            "rejection_rate": 1.0 - finite_draws / thresholds.bootstrap_draws,
        },
    }


def cap_rows_by_group(rows: Sequence[Mapping[str, Any]], *, max_rows_per_group: int) -> list[Mapping[str, Any]]:
    if max_rows_per_group < 1:
        raise ValueError("max_rows_per_group must be positive")
    groups: dict[str, dict[str, list[Mapping[str, Any]]]] = defaultdict(lambda: defaultdict(list))
    seen: set[str] = set()
    for row in rows:
        row_id = str(row["row_id"])
        if row_id in seen:
            raise ValueError(f"duplicate row_id: {row_id}")
        seen.add(row_id)
        groups[str(row["document_group"])][str(row["label"])].append(row)

    selected: list[Mapping[str, Any]] = []
    for group in sorted(groups, key=_utf8_key):
        label_rows = groups[group]
        for label in label_rows:
            label_rows[label].sort(
                key=lambda row: hashlib.sha256(f"atlas_measurement_v2|row-cap|{row['row_id']}".encode("utf-8")).digest()
            )
        labels = sorted(label_rows, key=_utf8_key)
        cursors = {label: 0 for label in labels}
        group_selected: list[Mapping[str, Any]] = []
        while len(group_selected) < max_rows_per_group:
            progressed = False
            for label in labels:
                cursor = cursors[label]
                if cursor < len(label_rows[label]) and len(group_selected) < max_rows_per_group:
                    group_selected.append(label_rows[label][cursor])
                    cursors[label] += 1
                    progressed = True
            if not progressed:
                break
        selected.extend(group_selected)
    return selected


def summarize_rows_by_source(
    rows: Sequence[Mapping[str, Any]], *, expected_sources: Sequence[str]
) -> dict[str, Any]:
    by_source: dict[str, list[Mapping[str, Any]]] = {source: [] for source in expected_sources}
    for row in rows:
        source = str(row["source"])
        if source not in by_source:
            raise ValueError(f"unexpected source: {source}")
        by_source[source].append(row)
    output: dict[str, Any] = {}
    for source, source_rows in by_source.items():
        groups = Counter(str(row["document_group"]) for row in source_rows)
        class_groups: dict[str, set[str]] = defaultdict(set)
        for row in source_rows:
            class_groups[str(row["label"])].add(str(row["document_group"]))
        output[source] = {
            "rows": len(source_rows),
            "groups": len(groups),
            "class_group_counts": {
                label: len(label_groups) for label, label_groups in sorted(class_groups.items(), key=lambda item: _utf8_key(item[0]))
            },
            "max_rows_per_group": max(groups.values(), default=0),
        }
    return output


def map_row_labels(
    rows: Sequence[Mapping[str, Any]],
    mapping: Mapping[str, str],
    *,
    strip_subtype: bool = False,
) -> list[dict[str, Any]]:
    output: list[dict[str, Any]] = []
    for row in rows:
        raw_label = str(row["label"])
        lookup = raw_label.split(":", 1)[0] if strip_subtype else raw_label
        if lookup not in mapping:
            raise ValueError(f"label is absent from the frozen mapping: {raw_label}")
        mapped = dict(row)
        mapped["label"] = str(mapping[lookup])
        output.append(mapped)
    return output


def identity_document_frequencies(
    rows: Sequence[Mapping[str, Any]], *, expected_sources: Sequence[str]
) -> dict[str, dict[str, int]]:
    groups: dict[str, dict[str, set[str]]] = {source: defaultdict(set) for source in expected_sources}
    for row in rows:
        source = str(row["source"])
        if source not in groups:
            raise ValueError(f"unexpected source: {source}")
        groups[source][str(row["label"])].add(str(row["document_group"]))
    return {
        source: {label: len(label_groups) for label, label_groups in label_map.items()}
        for source, label_map in groups.items()
    }


def select_identity_vocabulary(
    document_frequency_by_source: Mapping[str, Mapping[str, int]],
    *,
    minimum: int,
    maximum_size: int,
) -> list[str]:
    if not document_frequency_by_source:
        raise ValueError("at least one applicable source is required")
    candidates = set.intersection(*(set(counts) for counts in document_frequency_by_source.values()))
    eligible = [
        label
        for label in candidates
        if all(int(counts.get(label, 0)) >= minimum for counts in document_frequency_by_source.values())
    ]
    eligible.sort(
        key=lambda label: (
            -min(int(counts[label]) for counts in document_frequency_by_source.values()),
            -sum(int(counts[label]) for counts in document_frequency_by_source.values()),
            _utf8_key(label),
        )
    )
    selected = eligible[:maximum_size]
    if len(selected) < 2:
        raise ValueError("fewer than two identity labels satisfy document-frequency support")
    return selected


def aggregate_statuses(statuses: Sequence[str]) -> dict[str, str]:
    if not statuses:
        return {"status": "ineligible", "reason": "no_required_endpoints"}
    unknown = set(statuses).difference(VALID_STATUSES)
    if unknown:
        raise ValueError(f"unknown endpoint statuses: {sorted(unknown)}")
    if "ineligible" in statuses:
        return {"status": "ineligible", "reason": "required_ineligible"}
    if "not_run" in statuses:
        return {"status": "not_run", "reason": "required_not_run"}
    return {"status": "eligible", "reason": "all_required_eligible"}


def aggregate_endpoint_records(
    endpoints: Mapping[str, Mapping[str, Any]],
    *,
    required_endpoints: Sequence[str],
    additional_blocking_reasons: Sequence[str] = (),
) -> dict[str, Any]:
    if not required_endpoints or len(set(required_endpoints)) != len(required_endpoints):
        raise ValueError("required_endpoints must be a non-empty unique list")
    missing = [name for name in required_endpoints if name not in endpoints]
    if missing:
        raise ValueError(f"required endpoint records are missing: {missing}")
    preserved = {name: dict(value) for name, value in endpoints.items()}
    for name, record in preserved.items():
        if record.get("status") not in VALID_STATUSES:
            raise ValueError(f"endpoint {name} has an invalid status")
        record.setdefault("reasons", [])
        record.setdefault("observed_value", None)
        reasons = record["reasons"]
        if not isinstance(reasons, (list, tuple)) or any(not isinstance(reason, str) for reason in reasons):
            raise ValueError(f"endpoint {name} reasons must be a sequence of strings")
    aggregate = aggregate_statuses([str(preserved[name]["status"]) for name in required_endpoints])
    blocking_reasons: list[str] = []
    for name in required_endpoints:
        record = preserved[name]
        if record["status"] != "eligible":
            reasons = record.get("reasons") or [record["status"]]
            blocking_reasons.extend(f"{name}:{reason}" for reason in reasons)
    blocking_reasons.extend(str(reason) for reason in additional_blocking_reasons)
    if additional_blocking_reasons:
        aggregate["status"] = "ineligible"
        aggregate["reason"] = "additional_decision_block"
    return {
        "endpoints": preserved,
        "required_endpoints": list(required_endpoints),
        "overall": {**aggregate, "blocking_reasons": blocking_reasons},
    }


def validate_measurement_config(config: Mapping[str, Any]) -> None:
    sentinel = config.get("sentinels", {}).get("source_type")
    if sentinel != {"role": "nuisance", "stratification": "pooled"}:
        raise ValueError("source_type must be a pooled nuisance sentinel")
    replacement = config.get("replacement_confirmation", {})
    status_value = replacement.get("status")
    if status_value not in {"unset", "ready"}:
        raise ValueError("replacement confirmation status must be unset or ready")
    if status_value == "ready" and not replacement.get("source"):
        raise ValueError("replacement confirmation cannot be ready without a source")
    inputs = config.get("inputs")
    contracts = config.get("label_contracts")
    if inputs is not None:
        if not isinstance(inputs, list) or not isinstance(contracts, Mapping):
            raise ValueError("measurement inputs and label contracts must be declared")
        for entry in inputs:
            nuisance = bool(entry.get("nuisance_pooled"))
            if nuisance != (entry.get("task") == "source_type"):
                raise ValueError("only source_type may be configured as a pooled nuisance task")
            if entry.get("label_contract") not in contracts:
                raise ValueError(f"input references an unknown label contract: {entry.get('label_contract')}")
            if not isinstance(entry.get("required_for_task_measurability"), bool):
                raise ValueError("every input must declare required_for_task_measurability as a boolean")
    required_endpoints = config.get("required_endpoints")
    if required_endpoints is not None and (not isinstance(required_endpoints, list) or len(set(required_endpoints)) != len(required_endpoints)):
        raise ValueError("required_endpoints must be a unique list")


def verify_freeze_record(repository_root: Path, freeze_record: Path) -> dict[str, Any]:
    repository_root = repository_root.absolute()
    record_path = freeze_record if freeze_record.is_absolute() else repository_root / freeze_record
    _reject_symlink_chain(record_path, repository_root)
    if not record_path.is_file():
        raise ValueError("freeze record is missing or not a regular file")
    with record_path.open("r", encoding="utf-8") as handle:
        record = json.load(handle)
    entries = record.get("bundle_files")
    if not isinstance(entries, list):
        raise ValueError("freeze record bundle_files must be a list")

    inventory = [
        {
            "path": record_path.relative_to(repository_root).as_posix(),
            "sha256": sha256_file(record_path),
            "kind": "trust_root",
        }
    ]
    mismatches: list[dict[str, str]] = []
    for entry in entries:
        relative = _require_relative_path(str(entry.get("path", "")))
        expected = _validate_sha256(entry.get("sha256"), "sha256")
        path = repository_root / relative
        _reject_symlink_chain(path, repository_root)
        if not path.is_file():
            mismatches.append({"path": relative.as_posix(), "expected": expected, "observed": "missing"})
            continue
        observed = sha256_file(path)
        inventory.append({"path": relative.as_posix(), "sha256": observed, "kind": "bundle_file"})
        if observed != expected:
            mismatches.append({"path": relative.as_posix(), "expected": expected, "observed": observed})
    inventory.sort(key=lambda item: _utf8_key(item["path"]))
    return {"ok": not mismatches, "mismatches": mismatches, "inventory": inventory}


def _validate_cache_arrays(values: np.ndarray, offsets: np.ndarray, row_ids: Sequence[str]) -> None:
    if values.ndim != 2 or values.dtype != np.float32 or not np.all(np.isfinite(values)):
        raise ValueError("cache values must be a finite float32 matrix")
    if offsets.ndim != 1 or not np.issubdtype(offsets.dtype, np.integer):
        raise ValueError("cache offsets must be an integer vector")
    if len(offsets) != len(row_ids) + 1 or len(offsets) < 2:
        raise ValueError("cache offsets must have one boundary per row plus one")
    if int(offsets[0]) != 0 or int(offsets[-1]) != len(values) or np.any(np.diff(offsets) <= 0):
        raise ValueError("cache offsets must be strictly increasing from zero to token count")
    if len(set(row_ids)) != len(row_ids) or any(not isinstance(row_id, str) or not row_id for row_id in row_ids):
        raise ValueError("cache row IDs must be unique non-empty strings")


def write_representation_cache(
    cache_dir: Path,
    *,
    values: np.ndarray,
    offsets: np.ndarray,
    row_ids: Sequence[str],
    checkpoint: str,
    transform: str,
) -> dict[str, Any]:
    _reject_any_symlink_component(cache_dir.parent)
    if os.path.lexists(cache_dir):
        raise ValueError("cache directory already exists")
    if not checkpoint or not transform:
        raise ValueError("cache checkpoint and transform must be non-empty")
    array = np.asarray(values, dtype=np.float32)
    boundaries = np.asarray(offsets, dtype=np.int64)
    _validate_cache_arrays(array, boundaries, row_ids)
    cache_dir.mkdir(parents=False)
    values_path = cache_dir / "tokens.float32.npy"
    offsets_path = cache_dir / "offsets.int64.npy"
    row_ids_path = cache_dir / "row_ids.json"
    np.save(values_path, array, allow_pickle=False)
    np.save(offsets_path, boundaries, allow_pickle=False)
    row_ids_path.write_bytes(canonical_json_bytes(list(row_ids)))
    manifest = {
        "schema_version": "atlas_measurement_v2_representation_cache",
        "checkpoint": checkpoint,
        "transform": transform,
        "dtype": "float32",
        "shape": list(array.shape),
        "token_count": len(array),
        "hidden_dim": int(array.shape[1]),
        "rows": len(row_ids),
        "offset_count": len(boundaries),
        "files": {
            "tokens.float32.npy": sha256_file(values_path),
            "offsets.int64.npy": sha256_file(offsets_path),
            "row_ids.json": sha256_file(row_ids_path),
        },
    }
    manifest_path = cache_dir / "manifest.json"
    manifest_path.write_bytes(canonical_json_bytes(manifest))
    returned = dict(manifest)
    returned["manifest_sha256"] = sha256_file(manifest_path)
    return returned


def load_representation_cache(
    cache_dir: Path,
    *,
    expected_manifest_sha256: str,
    expected_checkpoint: str,
    expected_transform: str,
) -> dict[str, Any]:
    expected_manifest_sha256 = _validate_sha256(expected_manifest_sha256, "expected_manifest_sha256")
    if not expected_checkpoint or not expected_transform:
        raise ValueError("expected cache checkpoint and transform must be non-empty")
    _reject_any_symlink_component(cache_dir)
    if cache_dir.is_symlink() or not cache_dir.is_dir():
        raise ValueError("cache directory must be a real directory")
    manifest_path = cache_dir / "manifest.json"
    if manifest_path.is_symlink() or not manifest_path.is_file():
        raise ValueError("cache manifest must be a regular non-symlink file")
    if sha256_file(manifest_path) != expected_manifest_sha256:
        raise ValueError("manifest hash mismatch")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    required_manifest_fields = {
        "schema_version",
        "checkpoint",
        "transform",
        "dtype",
        "shape",
        "token_count",
        "hidden_dim",
        "rows",
        "offset_count",
        "files",
    }
    if set(manifest) != required_manifest_fields:
        raise ValueError("cache manifest fields do not match the exact schema")
    if manifest["schema_version"] != "atlas_measurement_v2_representation_cache":
        raise ValueError("cache manifest schema mismatch")
    if manifest["checkpoint"] != expected_checkpoint or manifest["transform"] != expected_transform:
        raise ValueError("cache checkpoint/transform lineage mismatch")
    if manifest["dtype"] != "float32":
        raise ValueError("cache dtype metadata mismatch")
    required_files = {"tokens.float32.npy", "offsets.int64.npy", "row_ids.json"}
    if not isinstance(manifest["files"], dict) or set(manifest["files"]) != required_files:
        raise ValueError("cache manifest must bind exactly the three canonical files")
    for filename, expected in manifest["files"].items():
        _validate_sha256(expected, f"files.{filename}")
        path = cache_dir / filename
        _reject_symlink_chain(path, cache_dir)
        if path.is_symlink() or not path.is_file() or sha256_file(path) != expected:
            raise ValueError(f"cache file hash mismatch: {filename}")
    values = np.load(cache_dir / "tokens.float32.npy", allow_pickle=False)
    offsets = np.load(cache_dir / "offsets.int64.npy", allow_pickle=False)
    row_ids = json.loads((cache_dir / "row_ids.json").read_text(encoding="utf-8"))
    _validate_cache_arrays(values, offsets, row_ids)
    if (
        list(values.shape) != manifest["shape"]
        or len(values) != manifest["token_count"]
        or values.shape[1] != manifest["hidden_dim"]
        or len(row_ids) != manifest["rows"]
        or len(offsets) != manifest["offset_count"]
    ):
        raise ValueError("cache shape/row metadata mismatch")
    return {"manifest": manifest, "values": values, "offsets": offsets, "row_ids": row_ids}


def canonical_pool(values: np.ndarray, offsets: np.ndarray) -> np.ndarray:
    array = np.asarray(values)
    boundaries = np.asarray(offsets)
    if array.ndim != 2 or array.dtype != np.float32 or boundaries.ndim != 1 or len(boundaries) < 2:
        raise ValueError("invalid values/offsets")
    if int(boundaries[0]) != 0 or int(boundaries[-1]) != len(array) or np.any(np.diff(boundaries) <= 0):
        raise ValueError("offsets must define non-empty contiguous rows")
    return np.stack(
        [np.mean(array[int(start) : int(stop)], axis=0, dtype=np.float64) for start, stop in zip(boundaries[:-1], boundaries[1:])]
    )


def numerical_agreement(reference: np.ndarray, repeated: np.ndarray, *, atol: float, rtol: float) -> dict[str, Any]:
    left = np.asarray(reference, dtype=np.float64)
    right = np.asarray(repeated, dtype=np.float64)
    if left.shape != right.shape or not np.all(np.isfinite(left)) or not np.all(np.isfinite(right)):
        raise ValueError("numerical agreement requires aligned finite arrays")
    if atol < 0 or rtol < 0:
        raise ValueError("atol and rtol must be non-negative")
    error = np.abs(right - left)
    bounds = atol + rtol * np.abs(left)
    passed = bool(np.all(error <= bounds))
    normalized = np.divide(error, bounds, out=np.where(error == 0, 0.0, np.inf), where=bounds > 0)
    return {
        "passed": passed,
        "atol": float(atol),
        "rtol": float(rtol),
        "max_abs_error": float(np.max(error, initial=0.0)),
        "max_bound_ratio": float(np.max(normalized, initial=0.0)),
    }


def _aligned_row_ids(left: Sequence[str], right: Sequence[str], expected_rows: int) -> bool:
    return len(left) == expected_rows and len(right) == expected_rows and list(left) == list(right) and len(set(left)) == expected_rows


def linear_cka(
    x: np.ndarray,
    y: np.ndarray,
    *,
    x_row_ids: Sequence[str],
    y_row_ids: Sequence[str],
) -> dict[str, Any]:
    left = np.asarray(x, dtype=np.float64)
    right = np.asarray(y, dtype=np.float64)
    if left.ndim != 2 or right.ndim != 2:
        return {"value": None, "reason": "not_matrix"}
    if len(left) != len(right):
        return {"value": None, "reason": "row_mismatch"}
    if not _aligned_row_ids(x_row_ids, y_row_ids, len(left)):
        return {"value": None, "reason": "row_mismatch"}
    if len(left) < 2:
        return {"value": None, "reason": "insufficient_rows"}
    if not np.all(np.isfinite(left)) or not np.all(np.isfinite(right)):
        return {"value": None, "reason": "nonfinite"}
    left = left - np.mean(left, axis=0, keepdims=True)
    right = right - np.mean(right, axis=0, keepdims=True)
    cross_sq = float(np.sum((left.T @ right) ** 2))
    left_sq = float(np.sum((left.T @ left) ** 2))
    right_sq = float(np.sum((right.T @ right) ** 2))
    denominator = math.sqrt(left_sq * right_sq)
    if not math.isfinite(denominator) or denominator <= np.finfo(np.float64).tiny:
        return {"value": None, "reason": "zero_variance"}
    value = max(0.0, min(1.0, cross_sq / denominator))
    return {"value": float(value), "reason": None}


def branch_cka_matrix(
    left: Mapping[str, np.ndarray],
    right: Mapping[str, np.ndarray],
    *,
    left_row_ids: Sequence[str],
    right_row_ids: Sequence[str],
) -> dict[str, Any]:
    branches = ("pos", "content")
    if set(left) != set(branches) or set(right) != set(branches):
        raise ValueError("K2 branch mappings must contain exactly pos and content")
    cells: dict[str, dict[str, Any]] = {}
    for left_branch in branches:
        for right_branch in branches:
            cells[f"{left_branch}__{right_branch}"] = linear_cka(
                left[left_branch],
                right[right_branch],
                x_row_ids=left_row_ids,
                y_row_ids=right_row_ids,
            )
    required = [cells["pos__pos"], cells["content__content"], cells["pos__content"], cells["content__pos"]]
    if any(cell["value"] is None for cell in required):
        margin = None
        reason = "undefined_cell"
    else:
        same = (float(cells["pos__pos"]["value"]) + float(cells["content__content"]["value"])) / 2
        swapped = (float(cells["pos__content"]["value"]) + float(cells["content__pos"]["value"])) / 2
        margin = same - swapped
        reason = None
    return {"cells": cells, "identity_margin": margin, "identity_margin_reason": reason}


def residual_cka(
    x: np.ndarray,
    y: np.ndarray,
    nuisance: np.ndarray,
    *,
    x_row_ids: Sequence[str],
    y_row_ids: Sequence[str],
    nuisance_row_ids: Sequence[str],
) -> dict[str, Any]:
    left = np.asarray(x, dtype=np.float64)
    right = np.asarray(y, dtype=np.float64)
    z = np.asarray(nuisance, dtype=np.float64)
    if left.ndim != 2 or right.ndim != 2 or z.ndim != 2 or len(left) != len(right) or len(left) != len(z):
        return {"value": None, "reason": "shape_mismatch"}
    if not _aligned_row_ids(x_row_ids, y_row_ids, len(left)) or list(x_row_ids) != list(nuisance_row_ids):
        return {"value": None, "reason": "row_mismatch"}
    if not np.all(np.isfinite(left)) or not np.all(np.isfinite(right)) or not np.all(np.isfinite(z)):
        return {"value": None, "reason": "nonfinite"}
    design = np.column_stack([np.ones(len(z), dtype=np.float64), z])
    rank = int(np.linalg.matrix_rank(design))
    if len(z) <= rank + 1:
        return {"value": None, "reason": "insufficient_residual_df"}
    left_residual = left - design @ np.linalg.lstsq(design, left, rcond=None)[0]
    right_residual = right - design @ np.linalg.lstsq(design, right, rcond=None)[0]
    return linear_cka(left_residual, right_residual, x_row_ids=x_row_ids, y_row_ids=y_row_ids)


def counterfactual_delta_cka(
    left_pre: np.ndarray,
    left_post: np.ndarray,
    right_pre: np.ndarray,
    right_post: np.ndarray,
    *,
    left_pre_row_ids: Sequence[str],
    left_post_row_ids: Sequence[str],
    right_pre_row_ids: Sequence[str],
    right_post_row_ids: Sequence[str],
) -> dict[str, Any]:
    arrays = [np.asarray(value, dtype=np.float64) for value in (left_pre, left_post, right_pre, right_post)]
    if arrays[0].shape != arrays[1].shape or arrays[2].shape != arrays[3].shape:
        return {"value": None, "reason": "delta_shape_mismatch"}
    if list(left_pre_row_ids) != list(left_post_row_ids) or list(right_pre_row_ids) != list(right_post_row_ids):
        return {"value": None, "reason": "row_mismatch"}
    return linear_cka(
        arrays[1] - arrays[0],
        arrays[3] - arrays[2],
        x_row_ids=left_pre_row_ids,
        y_row_ids=right_pre_row_ids,
    )


def family_cka_summary(task_values: Mapping[str, float | None], *, required_tasks: Sequence[str]) -> dict[str, Any]:
    if not required_tasks or len(set(required_tasks)) != len(required_tasks):
        raise ValueError("required_tasks must be a non-empty unique list")
    undefined: dict[str, str] = {}
    available: list[float] = []
    for task in required_tasks:
        value = task_values.get(task)
        if value is None:
            undefined[task] = "missing"
        elif not math.isfinite(float(value)) or not 0.0 <= float(value) <= 1.0:
            undefined[task] = "invalid_cka"
        else:
            available.append(float(value))
    missing = [task for task in required_tasks if task in undefined]
    return {
        "status": "eligible" if not missing else "ineligible",
        "complete_value": float(np.mean(available)) if not missing else None,
        "available_task_mean": float(np.mean(available)) if available else None,
        "tasks_available": len(available),
        "tasks_required": len(required_tasks),
        "missing_tasks": missing,
        "undefined_task_reasons": undefined,
    }


def validate_grouping_provenance(manifest: Mapping[str, Any]) -> dict[str, Any]:
    required = {
        "dataset_id",
        "revision",
        "bundle_sha256",
        "grouping_unit_type",
        "grouping_unit_field",
        "grouping_code_sha256",
        "original_units",
        "groups",
        "dependence_rationale",
        "builder_id",
        "reviewer_id",
        "review_decision",
        "reviewed_utc",
        "builder_key_fingerprint",
        "builder_signature",
        "reviewer_key_fingerprint",
        "reviewer_signature",
    }
    missing = required.difference(manifest)
    if missing:
        raise ValueError(f"grouping provenance missing fields: {sorted(missing)}")
    _validate_sha256(manifest["bundle_sha256"], "bundle_sha256")
    _validate_sha256(manifest["grouping_code_sha256"], "grouping_code_sha256")
    if manifest["builder_id"] == manifest["reviewer_id"]:
        raise ValueError("grouping provenance builder and reviewer must be distinct")
    if manifest["review_decision"] != "pass":
        raise ValueError("grouping provenance review must pass")
    if int(manifest["original_units"]) < 1 or int(manifest["groups"]) < 1:
        raise ValueError("grouping provenance unit counts must be positive")
    if int(manifest["groups"]) > int(manifest["original_units"]):
        raise ValueError("grouping provenance cannot split original units into more groups")
    for field in ("builder_signature", "reviewer_signature", "builder_key_fingerprint", "reviewer_key_fingerprint"):
        if not isinstance(manifest[field], str) or not manifest[field]:
            raise ValueError(f"grouping provenance {field} is required")
    return {
        "shape_valid": True,
        "authorization": "blocked",
        "reason": "cryptographic_signature_and_key_allowlist_verification_not_implemented",
    }


BLIND_ATTESTATION_FIELDS = frozenset(
    {
        "schema_version",
        "protocol_config_sha256",
        "dataset_bundle_sha256",
        "grouping_code_sha256",
        "producer_id",
        "key_fingerprint",
        "created_utc",
        "tasks",
        "signature",
    }
)
BLIND_TASK_FIELDS = frozenset(
    {
        "role",
        "source",
        "task",
        "total_groups",
        "minimum_anonymous_class_groups",
        "maximum_rows_per_group",
        "bootstrap_finite_draws",
        "eligible",
        "reasons",
    }
)


def validate_blind_attestation_shape(attestation: Mapping[str, Any]) -> dict[str, Any]:
    extras = set(attestation).difference(BLIND_ATTESTATION_FIELDS)
    missing = BLIND_ATTESTATION_FIELDS.difference(attestation)
    if extras:
        raise ValueError(f"blind attestation contains disallowed fields: {sorted(extras)}")
    if missing:
        raise ValueError(f"blind attestation missing fields: {sorted(missing)}")
    if attestation["schema_version"] != "atlas_measurement_v2_attestation":
        raise ValueError("blind attestation schema version mismatch")
    for field in ("protocol_config_sha256", "dataset_bundle_sha256", "grouping_code_sha256"):
        _validate_sha256(attestation[field], field)
    tasks = attestation["tasks"]
    if not isinstance(tasks, list):
        raise ValueError("blind attestation tasks must be a list")
    seen: set[tuple[str, str, str]] = set()
    for task in tasks:
        if not isinstance(task, Mapping):
            raise ValueError("blind attestation task must be an object")
        task_extras = set(task).difference(BLIND_TASK_FIELDS)
        task_missing = BLIND_TASK_FIELDS.difference(task)
        if task_extras or task_missing:
            raise ValueError(f"blind attestation task has disallowed/missing fields: {sorted(task_extras | task_missing)}")
        key = (str(task["role"]), str(task["source"]), str(task["task"]))
        if key in seen:
            raise ValueError(f"duplicate blind attestation task: {key}")
        seen.add(key)
    for field in ("producer_id", "key_fingerprint", "created_utc", "signature"):
        if not isinstance(attestation[field], str) or not attestation[field]:
            raise ValueError(f"blind attestation {field} is required")
    return {
        "shape_valid": True,
        "authorization": "blocked",
        "reason": "external_ed25519_verification_not_implemented",
    }
