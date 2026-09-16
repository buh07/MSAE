"""Pure readiness contracts for a prospective MSAE measurement study.

The functions here operate only on caller-supplied metadata and arrays.  They
cannot authorize a run; ``stage_ready`` is only a technical review candidate.
"""

from __future__ import annotations

import hashlib
import itertools
import json
import math
from pathlib import Path
import stat
from typing import Any, Mapping, Sequence

import numpy as np

import msae_measurement_v2 as _measurement_v2
from msae_measurement_v2 import aggregate_endpoint_records as _aggregate_endpoint_records


__all__ = [
    "payload_sha256",
    "select_replay_tolerance",
    "summarize_functional_reproducibility",
    "validate_draft_config",
    "verify_dependency",
    "build_stage_a",
    "build_stage_b",
    "build_stage_c",
]


_CONFIG_SCHEMA = "msae_measurement_remediation_config_v1"
_ARTIFACT_SCHEMA = "msae_measurement_remediation_artifact_v1"
_ENDPOINT_SCHEMA = "msae_endpoint_evidence_v1"
_REPLAY_BUNDLE_SCHEMA = "msae_calibration_replay_bundle_v1"
_REPLAY_RESULT_SCHEMA = "msae_replay_selection_v1"
_VALID_STATUSES = frozenset({"eligible", "ineligible", "not_run"})
_METRICS = ("recovery", "leakage", "selectivity")
_STAGE_C_CATEGORIES = (
    "localization",
    "functional_reproducibility",
    "collateral",
    "counterfactual",
    "baseline",
)
_STAGE_A_REQUIRED = [
    "candidate_confirmation_source",
    "immutable_source_revision",
    "independent_grouping_provenance",
    "label_support_audit",
    "construct_inventory",
    "counterfactual_template_specification",
    "tolerance_ladder_frozen",
    "dependency_attestation",
]
_STAGE_B_REQUIRED = [
    "calibration_replay",
    "selected_replay_tolerance",
    "cached_noop_hash_replay",
    "canonical_pooling_qa",
    "counterfactual_cache_alignment_qa",
]
_TOP_LEVEL_KEYS = {
    "schema_version",
    "protocol_id",
    "artifact_schema_version",
    "endpoint_schema_version",
    "replay_bundle_schema_version",
    "dependency",
    "replay",
    "functional_reproducibility",
    "stages",
}
_STRATUM_KEYS = {
    "stratum_id",
    "source_role",
    "source_revision",
    "partition",
    "model_id",
    "checkpoint_id",
    "code_sha256",
    "environment_sha256",
    "dtype",
    "pooling_path",
    "row_ids_sha256",
    "input_sha256",
    "reference_evaluation_id",
    "repeat_evaluation_ids",
}
_OBSERVATION_KEYS = {
    "stratum_id",
    "source_role",
    "source_revision",
    "partition",
    "model_id",
    "checkpoint_id",
    "code_sha256",
    "environment_sha256",
    "dtype",
    "pooling_path",
    "row_ids_sha256",
    "input_sha256",
    "evaluation_id",
    "row_ids",
    "values",
    "payload_sha256",
}
_ENDPOINT_KEYS = {
    "schema_version",
    "protocol_config_sha256",
    "endpoint_name",
    "category",
    "status",
    "reasons",
    "evidence_artifact_sha256",
    "observed_value",
}
_STAGE_ARTIFACT_KEYS = {
    "schema_version",
    "stage",
    "purpose",
    "protocol_id",
    "protocol_config_sha256",
    "dependency",
    "requirement_registry_sha256",
    "prior_stage_sha256",
    "endpoints",
    "aggregate",
    "stage_ready",
}


def _require_exact_keys(value: Mapping[str, Any], expected: set[str], label: str) -> None:
    keys = set(value)
    if keys != expected:
        missing = sorted(expected - keys)
        extra = sorted(keys - expected)
        raise ValueError(f"{label} keys mismatch; missing={missing}, extra={extra}")


def _validate_sha256(value: Any, label: str) -> str:
    if (
        not isinstance(value, str)
        or len(value) != 64
        or any(character not in "0123456789abcdef" for character in value)
    ):
        raise ValueError(f"{label} must be a SHA-256 hex digest")
    return value


def _require_nonempty_string(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value:
        raise ValueError(f"{label} must be a non-empty string")
    return value


def _reject_non_json(value: Any, label: str = "value") -> None:
    if value is None or isinstance(value, (str, bool, int)):
        return
    if isinstance(value, float):
        if not math.isfinite(value):
            raise ValueError(f"{label} contains a nonfinite float")
        return
    if isinstance(value, list):
        for index, item in enumerate(value):
            _reject_non_json(item, f"{label}[{index}]")
        return
    if isinstance(value, dict):
        for key, item in value.items():
            if not isinstance(key, str):
                raise ValueError(f"{label} has a non-string object key")
            _reject_non_json(item, f"{label}.{key}")
        return
    raise ValueError(f"{label} is outside the strict JSON domain")


def _canonical_json_bytes(value: Any) -> bytes:
    _reject_non_json(value)
    return (
        json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        )
        + "\n"
    ).encode("utf-8")


def _canonical_digest(value: Any) -> str:
    return hashlib.sha256(_canonical_json_bytes(value)).hexdigest()


def _unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate JSON object key: {key}")
        result[key] = value
    return result


def _reject_constant(token: str) -> Any:
    raise ValueError(f"nonfinite JSON number is forbidden: {token}")


def _load_bound_config(raw_config_bytes: bytes, expected_raw_config_sha256: str) -> tuple[dict[str, Any], str]:
    if not isinstance(raw_config_bytes, bytes):
        raise ValueError("raw config must be bytes")
    expected = _validate_sha256(expected_raw_config_sha256, "expected config digest")
    observed = hashlib.sha256(raw_config_bytes).hexdigest()
    if observed != expected:
        raise ValueError(f"raw config digest mismatch: expected {expected}, got {observed}")
    if raw_config_bytes.startswith(b"\xef\xbb\xbf"):
        raise ValueError("config UTF-8 BOM is forbidden")
    try:
        text = raw_config_bytes.decode("utf-8")
    except UnicodeDecodeError as error:
        raise ValueError("config must be strict UTF-8") from error
    try:
        config = json.loads(text, object_pairs_hook=_unique_object, parse_constant=_reject_constant)
    except json.JSONDecodeError as error:
        raise ValueError(f"invalid config JSON: {error.msg}") from error
    if not isinstance(config, dict):
        raise ValueError("config must be a top-level object")
    _reject_non_json(config, "config")
    _validate_config_structure(config)
    return config, observed


def _validate_unique_names(values: Any, label: str, *, may_be_empty: bool) -> list[str]:
    if not isinstance(values, list) or (not may_be_empty and not values):
        qualifier = "a list" if may_be_empty else "a non-empty list"
        raise ValueError(f"{label} must be {qualifier}")
    names = [_require_nonempty_string(value, label) for value in values]
    if len(set(names)) != len(names):
        raise ValueError(f"{label} must contain unique names")
    return names


def _validate_stage_registries(config: Mapping[str, Any]) -> None:
    stages = config["stages"]
    if not isinstance(stages, dict) or set(stages) != {"A", "B", "C"}:
        raise ValueError("stages must contain exactly A, B, and C")
    expected_purpose = {
        "A": "calibration_replay_candidate",
        "B": "confirmation_scoring_candidate",
        "C": "decision_review_candidate",
    }
    seen: set[str] = set()
    for stage in ("A", "B"):
        value = stages[stage]
        if not isinstance(value, dict):
            raise ValueError(f"stage {stage} must be an object")
        _require_exact_keys(value, {"purpose", "required", "optional"}, f"stage {stage}")
        if value["purpose"] != expected_purpose[stage]:
            raise ValueError(f"stage {stage} purpose is invalid")
        required = _validate_unique_names(value["required"], f"stage {stage} required", may_be_empty=False)
        optional = _validate_unique_names(value["optional"], f"stage {stage} optional", may_be_empty=True)
        if set(required) & set(optional):
            raise ValueError(f"stage {stage} required and optional registries must be disjoint")
        for name in required + optional:
            if name in seen:
                raise ValueError(f"endpoint names must be globally unique: {name}")
            seen.add(name)
    if stages["A"]["required"] != _STAGE_A_REQUIRED:
        raise ValueError("stage A required registry must equal the frozen mandated endpoint list")
    if stages["B"]["required"] != _STAGE_B_REQUIRED:
        raise ValueError("stage B required registry must equal the frozen mandated endpoint list")

    stage_c = stages["C"]
    if not isinstance(stage_c, dict):
        raise ValueError("stage C must be an object")
    _require_exact_keys(stage_c, {"purpose", "required_by_category", "optional"}, "stage C")
    if stage_c["purpose"] != expected_purpose["C"]:
        raise ValueError("stage C purpose is invalid")
    categories = stage_c["required_by_category"]
    if not isinstance(categories, dict) or set(categories) != set(_STAGE_C_CATEGORIES):
        raise ValueError("stage C must contain exactly the five registered categories")
    for category in _STAGE_C_CATEGORIES:
        names = _validate_unique_names(categories[category], f"stage C {category}", may_be_empty=True)
        for name in names:
            if name in seen:
                raise ValueError(f"endpoint names must be globally unique: {name}")
            seen.add(name)
    optional = _validate_unique_names(stage_c["optional"], "stage C optional", may_be_empty=True)
    for name in optional:
        if name in seen:
            raise ValueError(f"required and optional endpoint registries must be disjoint: {name}")
        seen.add(name)


def _validate_config_structure(config: Mapping[str, Any]) -> None:
    _require_exact_keys(config, _TOP_LEVEL_KEYS, "config")
    if config["schema_version"] != _CONFIG_SCHEMA:
        raise ValueError("unsupported config schema_version")
    _require_nonempty_string(config["protocol_id"], "protocol_id")
    if config["artifact_schema_version"] != _ARTIFACT_SCHEMA:
        raise ValueError("unsupported artifact schema version")
    if config["endpoint_schema_version"] != _ENDPOINT_SCHEMA:
        raise ValueError("unsupported endpoint schema version")
    if config["replay_bundle_schema_version"] != _REPLAY_BUNDLE_SCHEMA:
        raise ValueError("unsupported replay bundle schema version")
    dependency = config["dependency"]
    if not isinstance(dependency, dict):
        raise ValueError("dependency must be an object")
    _require_exact_keys(dependency, {"path", "sha256"}, "dependency")
    if dependency["path"] != "scripts/msae_measurement_v2.py":
        raise ValueError("dependency path must name the canonical sibling")
    _validate_sha256(dependency["sha256"], "dependency sha256")
    replay = config["replay"]
    if not isinstance(replay, dict):
        raise ValueError("replay must be an object")
    _require_exact_keys(
        replay,
        {"source_role", "source_revision", "partition", "strata", "tolerance_ladder", "safety_factor"},
        "replay",
    )
    if replay["source_role"] != "calibration":
        raise ValueError("replay source_role must be calibration")
    if not isinstance(replay["strata"], list) or not isinstance(replay["tolerance_ladder"], list):
        raise ValueError("replay strata and ladder must be lists")
    functional = config["functional_reproducibility"]
    if not isinstance(functional, dict):
        raise ValueError("functional_reproducibility must be an object")
    _require_exact_keys(functional, {"minimum_checkpoints", "checkpoints", "families", "maximum_spread"}, "functional")
    if not isinstance(functional["checkpoints"], list) or not isinstance(functional["families"], dict):
        raise ValueError("functional registries have invalid types")
    maximum_spread = functional["maximum_spread"]
    if not isinstance(maximum_spread, dict) or set(maximum_spread) != set(_METRICS):
        raise ValueError("functional maximum_spread must contain the three metrics")
    _validate_stage_registries(config)


def verify_dependency(expected_sha256: str) -> dict[str, str]:
    """Verify the imported reviewed utility against its literal sibling."""
    expected = _validate_sha256(expected_sha256, "expected dependency digest")
    literal = Path(__file__).with_name("msae_measurement_v2.py")
    try:
        mode = literal.lstat().st_mode
    except FileNotFoundError as error:
        raise ValueError("canonical dependency is missing") from error
    if not stat.S_ISREG(mode) or literal.is_symlink():
        raise ValueError("canonical dependency must be a non-symlink regular file")
    canonical = literal.resolve(strict=True)
    imported_raw = getattr(_measurement_v2, "__file__", None)
    if not isinstance(imported_raw, str):
        raise ValueError("imported dependency has no file origin")
    imported = Path(imported_raw)
    if imported.is_symlink() or imported.resolve(strict=True) != canonical:
        raise ValueError("imported dependency origin is not the canonical sibling")
    observed = hashlib.sha256(canonical.read_bytes()).hexdigest()
    if observed != expected:
        raise ValueError(f"dependency digest mismatch: expected {expected}, got {observed}")
    return {"path": "scripts/msae_measurement_v2.py", "sha256": observed}


def _config_blockers(config: Mapping[str, Any]) -> list[str]:
    replay = config["replay"]
    functional = config["functional_reproducibility"]
    blockers: list[str] = []
    if replay["source_revision"] is None:
        blockers.append("replay_source_revision_unset")
    else:
        _validate_sha256(replay["source_revision"], "replay source_revision")
    if replay["partition"] is None:
        blockers.append("replay_partition_unset")
    else:
        _require_nonempty_string(replay["partition"], "replay partition")
    if not replay["strata"]:
        blockers.append("replay_registry_unset")
    else:
        _validate_stratum_registry(
            replay["strata"],
            expected_source_revision=replay["source_revision"],
            expected_partition=replay["partition"],
        )
    if not replay["tolerance_ladder"]:
        blockers.append("replay_tolerance_ladder_unset")
    else:
        _validate_ladder(replay["tolerance_ladder"])
    if replay["safety_factor"] is None:
        blockers.append("replay_safety_factor_unset")
    else:
        safety = _finite_float(replay["safety_factor"], "safety_factor")
        if safety <= 1.0:
            raise ValueError("safety_factor must be strictly greater than one")

    minimum = functional["minimum_checkpoints"]
    if minimum is None:
        blockers.append("functional_minimum_checkpoints_unset")
    elif isinstance(minimum, bool) or not isinstance(minimum, int) or minimum < 3:
        raise ValueError("minimum_checkpoints must be an integer of at least three")
    if not functional["checkpoints"]:
        blockers.append("functional_checkpoint_registry_unset")
    elif minimum is not None:
        _validate_checkpoint_registry(functional["checkpoints"], minimum)
    if not functional["families"]:
        blockers.append("functional_family_registry_unset")
    else:
        _validate_families(functional["families"])
    for metric in _METRICS:
        threshold = functional["maximum_spread"][metric]
        if threshold is None:
            blockers.append(f"functional_{metric}_maximum_spread_unset")
        else:
            number = _finite_float(threshold, f"{metric} maximum spread")
            if number < 0.0:
                raise ValueError(f"{metric} maximum spread must be nonnegative")
    categories = config["stages"]["C"]["required_by_category"]
    for category in _STAGE_C_CATEGORIES:
        if not categories[category]:
            blockers.append(f"stage_c_{category}_registry_unset")
    return blockers


def validate_draft_config(raw_config_bytes: bytes, expected_raw_config_sha256: str) -> dict[str, Any]:
    config, digest = _load_bound_config(raw_config_bytes, expected_raw_config_sha256)
    dependency = verify_dependency(config["dependency"]["sha256"])
    blockers = _config_blockers(config)
    return {
        "schema_version": "msae_measurement_remediation_config_validation_v1",
        "protocol_id": config["protocol_id"],
        "protocol_config_sha256": digest,
        "dependency": dependency,
        "status": "ready" if not blockers else "blocked",
        "reasons": blockers,
    }


def _row_ids_bytes(row_ids: Sequence[str]) -> bytes:
    return json.dumps(list(row_ids), sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def _validate_row_ids(row_ids: Any, expected_rows: int) -> list[str]:
    if not isinstance(row_ids, (list, tuple)) or not row_ids:
        raise ValueError("row IDs must be a non-empty sequence")
    rows = [_require_nonempty_string(value, "row ID") for value in row_ids]
    if len(rows) != expected_rows:
        raise ValueError("row ID count must match the first array dimension")
    if len(set(rows)) != len(rows):
        raise ValueError("row IDs must be unique")
    return rows


def payload_sha256(values: np.ndarray, row_ids: Sequence[str]) -> str:
    """Hash float32 values with dtype, shape, and ordered row IDs."""
    if not isinstance(values, np.ndarray) or values.dtype != np.dtype(np.float32):
        raise ValueError("payload values must be a float32 array")
    if values.ndim < 1 or values.size == 0 or any(dimension < 1 for dimension in values.shape):
        raise ValueError("payload array must have a non-empty shape")
    if not np.isfinite(values).all():
        raise ValueError("payload array must contain only finite values")
    rows = _validate_row_ids(row_ids, values.shape[0])
    header = {"dtype": "float32", "shape": list(values.shape)}
    header_bytes = json.dumps(header, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    rows_bytes = _row_ids_bytes(rows)
    contiguous = np.ascontiguousarray(values)
    framed = (
        len(header_bytes).to_bytes(8, "big")
        + header_bytes
        + len(rows_bytes).to_bytes(8, "big")
        + rows_bytes
        + contiguous.tobytes(order="C")
    )
    return hashlib.sha256(framed).hexdigest()


def _finite_float(value: Any, label: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float, np.integer, np.floating)):
        raise ValueError(f"{label} must be a finite real number")
    try:
        number = float(value)
    except (OverflowError, ValueError) as error:
        raise ValueError(f"{label} must be representable as finite float64") from error
    if not math.isfinite(number):
        raise ValueError(f"{label} must be finite")
    return number


def _validate_ladder(raw_ladder: Any) -> list[tuple[float, float]]:
    if not isinstance(raw_ladder, list) or not raw_ladder:
        raise ValueError("tolerance ladder must be non-empty")
    ladder: list[tuple[float, float]] = []
    for index, entry in enumerate(raw_ladder):
        if not isinstance(entry, list) or len(entry) != 2:
            raise ValueError("each tolerance candidate must be [atol, rtol]")
        atol = _finite_float(entry[0], f"ladder[{index}] atol")
        rtol = _finite_float(entry[1], f"ladder[{index}] rtol")
        if atol <= 0.0:
            raise ValueError("every tolerance candidate atol must be strictly positive")
        if rtol < 0.0:
            raise ValueError("every tolerance candidate rtol must be nonnegative")
        candidate = (atol, rtol)
        if candidate in ladder:
            raise ValueError("tolerance ladder candidates must be unique")
        if ladder:
            previous = ladder[-1]
            if atol < previous[0] or rtol < previous[1] or candidate == previous:
                raise ValueError("tolerance ladder must be componentwise nondecreasing")
        ladder.append(candidate)
    return ladder


def _validate_stratum_registry(
    raw_registry: Any,
    *,
    expected_source_revision: str | None = None,
    expected_partition: str | None = None,
) -> list[dict[str, Any]]:
    if not isinstance(raw_registry, list) or not raw_registry:
        raise ValueError("replay stratum registry must be non-empty")
    registry: list[dict[str, Any]] = []
    seen_strata: set[str] = set()
    seen_evaluations: set[str] = set()
    for raw in raw_registry:
        if not isinstance(raw, dict):
            raise ValueError("each replay stratum must be an object")
        _require_exact_keys(raw, _STRATUM_KEYS, "replay stratum")
        stratum = dict(raw)
        stratum_id = _require_nonempty_string(stratum["stratum_id"], "stratum_id")
        if stratum_id in seen_strata:
            raise ValueError("stratum IDs must be unique")
        seen_strata.add(stratum_id)
        if stratum["source_role"] != "calibration":
            raise ValueError("every replay stratum role must be calibration")
        if expected_source_revision is not None and stratum["source_revision"] != expected_source_revision:
            raise ValueError("every replay stratum source revision must match the global replay registry")
        if expected_partition is not None and stratum["partition"] != expected_partition:
            raise ValueError("every replay stratum partition must match the global replay registry")
        for field in ("source_revision", "code_sha256", "environment_sha256", "row_ids_sha256", "input_sha256"):
            _validate_sha256(stratum[field], f"{stratum_id} {field}")
        for field in ("partition", "model_id", "checkpoint_id", "dtype", "pooling_path"):
            _require_nonempty_string(stratum[field], f"{stratum_id} {field}")
        if stratum["dtype"] != "float32":
            raise ValueError("replay stratum dtype must be float32")
        reference = _require_nonempty_string(stratum["reference_evaluation_id"], "reference evaluation ID")
        repeats = _validate_unique_names(stratum["repeat_evaluation_ids"], "repeat evaluation IDs", may_be_empty=False)
        if len(repeats) < 3:
            raise ValueError("each replay stratum requires at least three repeats")
        evaluation_ids = [reference, *repeats]
        if len(set(evaluation_ids)) != len(evaluation_ids):
            raise ValueError("reference and repeat evaluation IDs must be unique")
        for evaluation_id in evaluation_ids:
            if evaluation_id in seen_evaluations:
                raise ValueError("evaluation IDs must be globally unique")
            seen_evaluations.add(evaluation_id)
        registry.append(stratum)
    return registry


def _validate_bundle(
    bundle: Any,
    config: Mapping[str, Any],
    config_digest: str,
    registry: Sequence[Mapping[str, Any]],
) -> dict[str, dict[str, dict[str, Any]]]:
    if not isinstance(bundle, dict):
        raise ValueError("replay bundle must be an object")
    expected_keys = {
        "schema_version",
        "protocol_config_sha256",
        "replay_registry_sha256",
        "source_role",
        "source_revision",
        "partition",
        "observations",
    }
    _require_exact_keys(bundle, expected_keys, "replay bundle")
    if bundle["schema_version"] != config["replay_bundle_schema_version"]:
        raise ValueError("replay bundle schema mismatch")
    if bundle["protocol_config_sha256"] != config_digest:
        raise ValueError("replay bundle config digest mismatch")
    expected_registry_digest = _canonical_digest(list(registry))
    if bundle["replay_registry_sha256"] != expected_registry_digest:
        raise ValueError("replay registry digest mismatch")
    replay_config = config["replay"]
    if bundle["source_role"] != "calibration" or bundle["source_role"] != replay_config["source_role"]:
        raise ValueError("replay bundle role must be calibration")
    if bundle["source_revision"] != replay_config["source_revision"]:
        raise ValueError("replay bundle source revision mismatch")
    if bundle["partition"] != replay_config["partition"]:
        raise ValueError("replay bundle partition mismatch")
    observations = bundle["observations"]
    if not isinstance(observations, dict) or set(observations) != {item["stratum_id"] for item in registry}:
        raise ValueError("replay bundle strata do not match the registry")
    normalized: dict[str, dict[str, dict[str, Any]]] = {}
    provenance_fields = (
        "stratum_id",
        "source_role",
        "source_revision",
        "partition",
        "model_id",
        "checkpoint_id",
        "code_sha256",
        "environment_sha256",
        "dtype",
        "pooling_path",
        "row_ids_sha256",
        "input_sha256",
    )
    for stratum in registry:
        stratum_id = stratum["stratum_id"]
        raw_evaluations = observations[stratum_id]
        if not isinstance(raw_evaluations, dict):
            raise ValueError("stratum observations must be an evaluation mapping")
        evaluation_ids = [stratum["reference_evaluation_id"], *stratum["repeat_evaluation_ids"]]
        if set(raw_evaluations) != set(evaluation_ids):
            raise ValueError("replay evaluations do not match the frozen registry")
        normalized[stratum_id] = {}
        expected_rows: list[str] | None = None
        expected_shape: tuple[int, ...] | None = None
        for evaluation_id in evaluation_ids:
            raw = raw_evaluations[evaluation_id]
            if not isinstance(raw, dict):
                raise ValueError("replay observation must be an object")
            _require_exact_keys(raw, _OBSERVATION_KEYS, "replay observation")
            if raw["evaluation_id"] != evaluation_id:
                raise ValueError("evaluation ID does not match its registry key")
            for field in provenance_fields:
                if raw[field] != stratum[field]:
                    raise ValueError(f"replay observation provenance mismatch: {field}")
            values = raw["values"]
            if not isinstance(values, np.ndarray) or values.dtype != np.dtype(np.float32):
                raise ValueError("replay observation values must be float32 arrays")
            if values.ndim < 1 or values.size == 0 or not np.isfinite(values).all():
                raise ValueError("replay observation arrays must be non-empty and finite")
            rows = _validate_row_ids(raw["row_ids"], values.shape[0])
            row_digest = hashlib.sha256(_row_ids_bytes(rows)).hexdigest()
            if row_digest != stratum["row_ids_sha256"]:
                raise ValueError("ordered row digest mismatch")
            if expected_rows is None:
                expected_rows = rows
                expected_shape = values.shape
            elif rows != expected_rows or values.shape != expected_shape:
                raise ValueError("replay row order and array shape must align")
            supplied_payload = _validate_sha256(raw["payload_sha256"], "payload digest")
            observed_payload = payload_sha256(values, rows)
            if supplied_payload != observed_payload:
                raise ValueError("replay payload digest mismatch")
            normalized[stratum_id][evaluation_id] = dict(raw)
    return normalized


def _checked_array(value: np.ndarray, label: str) -> np.ndarray:
    if not np.isfinite(value).all():
        raise ValueError(f"{label} must remain finite in float64")
    return value


def select_replay_tolerance(
    raw_config_bytes: bytes,
    expected_raw_config_sha256: str,
    replay_bundle: Mapping[str, Any],
) -> dict[str, Any]:
    config, config_digest = _load_bound_config(raw_config_bytes, expected_raw_config_sha256)
    blockers = _config_blockers(config)
    replay_blockers = [reason for reason in blockers if reason.startswith("replay_")]
    if replay_blockers:
        raise ValueError(f"replay config is incomplete: {replay_blockers}")
    replay = config["replay"]
    registry = _validate_stratum_registry(
        replay["strata"],
        expected_source_revision=replay["source_revision"],
        expected_partition=replay["partition"],
    )
    ladder = _validate_ladder(replay["tolerance_ladder"])
    safety_factor = _finite_float(replay["safety_factor"], "safety_factor")
    if safety_factor <= 1.0:
        raise ValueError("safety_factor must be strictly greater than one")
    observations = _validate_bundle(replay_bundle, config, config_digest, registry)

    stratum_reports: list[dict[str, Any]] = []
    pass_matrix: dict[str, list[bool]] = {}
    for stratum in registry:
        stratum_id = stratum["stratum_id"]
        evaluation_ids = [stratum["reference_evaluation_id"], *stratum["repeat_evaluation_ids"]]
        arrays = {
            evaluation_id: observations[stratum_id][evaluation_id]["values"].astype(np.float64, copy=False).ravel(order="C")
            for evaluation_id in evaluation_ids
        }
        pair_errors: list[np.ndarray] = []
        pair_scales: list[np.ndarray] = []
        for left, right in itertools.combinations(evaluation_ids, 2):
            with np.errstate(over="ignore", invalid="ignore"):
                error = np.abs(arrays[left] - arrays[right])
                scale = np.maximum(np.abs(arrays[left]), np.abs(arrays[right]))
            pair_errors.append(_checked_array(error, "pairwise error"))
            pair_scales.append(_checked_array(scale, "pairwise scale"))
        passes: list[bool] = []
        max_ratios: list[float] = []
        for atol, rtol in ladder:
            candidate_pass = True
            candidate_max_ratio = 0.0
            for error, scale in zip(pair_errors, pair_scales):
                with np.errstate(over="ignore", invalid="ignore", divide="ignore"):
                    left = safety_factor * error
                    right = atol + rtol * scale
                    ratio = left / right
                _checked_array(left, "safety-adjusted error")
                _checked_array(right, "tolerance bound")
                _checked_array(ratio, "diagnostic ratio")
                candidate_pass = candidate_pass and bool(np.all(left <= right))
                candidate_max_ratio = max(candidate_max_ratio, float(np.max(ratio)))
            passes.append(candidate_pass)
            max_ratios.append(candidate_max_ratio)
        pass_matrix[stratum_id] = passes
        all_errors = np.concatenate(pair_errors)
        all_scales = np.concatenate(pair_scales)
        stratum_reports.append(
            {
                "stratum_id": stratum_id,
                "evaluation_ids": evaluation_ids,
                "payload_sha256": {
                    evaluation_id: observations[stratum_id][evaluation_id]["payload_sha256"]
                    for evaluation_id in evaluation_ids
                },
                "pair_count": len(pair_errors),
                "coordinate_comparison_count": len(pair_errors) * arrays[evaluation_ids[0]].size,
                "maximum_absolute_error": float(np.max(all_errors)),
                "maximum_symmetric_scale": float(np.max(all_scales)),
                "pass_by_candidate": passes,
                "maximum_ratio_by_candidate": max_ratios,
            }
        )
    selected_index = next(
        (
            index
            for index in range(len(ladder))
            if all(pass_matrix[stratum["stratum_id"]][index] for stratum in registry)
        ),
        None,
    )
    selected = list(ladder[selected_index]) if selected_index is not None else None
    return {
        "schema_version": _REPLAY_RESULT_SCHEMA,
        "protocol_config_sha256": config_digest,
        "replay_registry_sha256": _canonical_digest(registry),
        "source_role": "calibration",
        "source_revision": replay["source_revision"],
        "partition": replay["partition"],
        "pairing_rule": "all_unordered_evaluation_pairs",
        "safety_factor": safety_factor,
        "tolerance_ladder": [list(candidate) for candidate in ladder],
        "strata": stratum_reports,
        "pass_matrix": pass_matrix,
        "status": "eligible" if selected_index is not None else "ineligible",
        "reasons": [] if selected_index is not None else ["no_registered_tolerance_passed_all_strata"],
        "selected_index": selected_index,
        "selected_tolerance": selected,
        "rationale": "first_registered_global_pass" if selected_index is not None else "no_extrapolation_beyond_registered_ladder",
    }


def _validate_checkpoint_registry(raw: Any, minimum_checkpoints: int) -> list[dict[str, Any]]:
    if isinstance(minimum_checkpoints, bool) or not isinstance(minimum_checkpoints, int) or minimum_checkpoints < 3:
        raise ValueError("minimum_checkpoints must be an integer of at least three")
    if not isinstance(raw, list) or len(raw) < minimum_checkpoints:
        raise ValueError("checkpoint registry has fewer than minimum_checkpoints")
    expected = {
        "model_id",
        "training_run_id",
        "training_run_digest",
        "checkpoint_id",
        "checkpoint_sha256",
        "seed",
    }
    checkpoints: list[dict[str, Any]] = []
    components: dict[str, set[Any]] = {
        "training_run_id": set(),
        "training_run_digest": set(),
        "checkpoint_id": set(),
        "checkpoint_sha256": set(),
        "seed": set(),
    }
    model_id: str | None = None
    for raw_checkpoint in raw:
        if not isinstance(raw_checkpoint, dict):
            raise ValueError("checkpoint records must be objects")
        _require_exact_keys(raw_checkpoint, expected, "checkpoint")
        checkpoint = dict(raw_checkpoint)
        current_model = _require_nonempty_string(checkpoint["model_id"], "model_id")
        if model_id is None:
            model_id = current_model
        elif current_model != model_id:
            raise ValueError("all registered checkpoints must share one model_id")
        for field in ("training_run_id", "checkpoint_id"):
            _require_nonempty_string(checkpoint[field], field)
        for field in ("training_run_digest", "checkpoint_sha256"):
            _validate_sha256(checkpoint[field], field)
        seed = checkpoint["seed"]
        if isinstance(seed, bool) or not isinstance(seed, int):
            raise ValueError("checkpoint seed must be an integer")
        for field in components:
            value = checkpoint[field]
            if value in components[field]:
                raise ValueError("checkpoint lineage components must form a one-to-one mapping")
            components[field].add(value)
        checkpoints.append(checkpoint)
    return checkpoints


def _validate_families(raw: Any) -> dict[str, list[str]]:
    if not isinstance(raw, dict) or not raw:
        raise ValueError("family registry must be a non-empty object")
    families: dict[str, list[str]] = {}
    seen_tasks: set[str] = set()
    for family, raw_tasks in raw.items():
        _require_nonempty_string(family, "family name")
        tasks = _validate_unique_names(raw_tasks, f"family {family} tasks", may_be_empty=False)
        overlap = seen_tasks.intersection(tasks)
        if overlap:
            raise ValueError(f"tasks may appear in only one family: {sorted(overlap)}")
        seen_tasks.update(tasks)
        families[family] = tasks
    return families


def _checked_scalar(value: float, label: str) -> float:
    if not math.isfinite(value):
        raise ValueError(f"{label} must remain finite in float64")
    return value


def _checked_mean(values: Sequence[float], label: str) -> float:
    try:
        total = math.fsum(values)
    except OverflowError as error:
        raise ValueError(f"{label} sum must remain finite in float64") from error
    _checked_scalar(total, f"{label} sum")
    return _checked_scalar(total / len(values), f"{label} mean")


def _normalize_metric_record(raw: Any, label: str) -> dict[str, Any]:
    if not isinstance(raw, dict):
        raise ValueError(f"{label} must be an object")
    _require_exact_keys(raw, {"status", "reasons", "value"}, label)
    status_value = raw["status"]
    if status_value not in _VALID_STATUSES:
        raise ValueError(f"{label} has an invalid status")
    reasons = raw["reasons"]
    if not isinstance(reasons, list) or any(not isinstance(reason, str) or not reason for reason in reasons):
        raise ValueError(f"{label} reasons must be non-empty strings")
    if len(set(reasons)) != len(reasons):
        raise ValueError(f"{label} reasons must be unique")
    value = raw["value"]
    if value is None:
        if status_value == "eligible":
            raise ValueError(f"{label} eligible value is missing")
        normalized_value = None
    else:
        normalized_value = _finite_float(value, f"{label} value")
    return {"status": status_value, "reasons": list(reasons), "value": normalized_value}


def _summarize_checkpoint_values(
    checkpoint_ids: Sequence[str],
    records: Mapping[str, Mapping[str, Any]],
    threshold: float,
    metric: str,
) -> dict[str, Any]:
    entries = [
        {
            "checkpoint_id": checkpoint_id,
            "status": records[checkpoint_id]["status"],
            "reasons": list(records[checkpoint_id]["reasons"]),
            "value": records[checkpoint_id]["value"],
        }
        for checkpoint_id in checkpoint_ids
    ]
    available = [(entry["checkpoint_id"], entry["value"]) for entry in entries if entry["value"] is not None]
    pairs: list[dict[str, Any]] = []
    for left_index, right_index in itertools.combinations(range(len(entries)), 2):
        left = entries[left_index]
        right = entries[right_index]
        if left["value"] is None or right["value"] is None:
            signed_delta = None
            absolute_delta = None
        else:
            signed_delta = _checked_scalar(right["value"] - left["value"], "signed checkpoint delta")
            absolute_delta = _checked_scalar(abs(signed_delta), "absolute checkpoint delta")
        pairs.append(
            {
                "checkpoint_i": left["checkpoint_id"],
                "checkpoint_j": right["checkpoint_id"],
                "signed_delta": signed_delta,
                "absolute_delta": absolute_delta,
            }
        )
    values = [value for _, value in available]
    if values:
        minimum = min(values)
        maximum = max(values)
        mean = _checked_mean(values, "checkpoint values")
        spread = _checked_scalar(maximum - minimum, "checkpoint spread")
    else:
        minimum = maximum = mean = spread = None
    statuses = [entry["status"] for entry in entries]
    reasons: list[str] = []
    if "ineligible" in statuses:
        status_value = "ineligible"
        for entry in entries:
            if entry["status"] == "ineligible":
                reasons.extend(f"{entry['checkpoint_id']}:{reason}" for reason in entry["reasons"] or ["ineligible"])
    elif "not_run" in statuses:
        status_value = "not_run"
        for entry in entries:
            if entry["status"] == "not_run":
                reasons.extend(f"{entry['checkpoint_id']}:{reason}" for reason in entry["reasons"] or ["not_run"])
    else:
        if len(values) != len(entries):
            raise ValueError("eligible checkpoint records must all have finite values")
        if spread is None:
            raise ValueError("complete checkpoint summary has no spread")
        if spread > threshold:
            status_value = "ineligible"
            reasons = ["maximum_spread_exceeded"]
        else:
            status_value = "eligible"
    result: dict[str, Any] = {
        "status": status_value,
        "reasons": reasons,
        "threshold": threshold,
        "checkpoint_values": entries,
        "pairs": pairs,
        "mean": mean,
        "minimum": minimum,
        "maximum": maximum,
        "maximum_spread": spread,
        "complete": all(status == "eligible" for status in statuses),
    }
    if metric == "selectivity":
        if status_value == "not_run":
            localization_status = "not_run"
            localization_reasons = ["selectivity_incomplete"]
        elif status_value == "ineligible":
            localization_status = "ineligible"
            localization_reasons = ["selectivity_reproducibility_ineligible"]
        elif any(value <= 0.0 for value in values):
            localization_status = "ineligible"
            localization_reasons = ["nonpositive_selectivity"]
        else:
            localization_status = "eligible"
            localization_reasons = []
        result["localization_status"] = localization_status
        result["localization_reasons"] = localization_reasons
    return result


def summarize_functional_reproducibility(
    checkpoints: Sequence[Mapping[str, Any]],
    families: Mapping[str, Sequence[str]],
    records: Mapping[str, Mapping[str, Mapping[str, Mapping[str, Any]]]],
    maximum_spread: Mapping[str, float],
    *,
    minimum_checkpoints: int,
) -> dict[str, Any]:
    registered_checkpoints = _validate_checkpoint_registry(list(checkpoints), minimum_checkpoints)
    registered_families = _validate_families(dict(families))
    if not isinstance(maximum_spread, dict) or set(maximum_spread) != set(_METRICS):
        raise ValueError("maximum_spread must contain exactly the three metrics")
    thresholds: dict[str, float] = {}
    for metric in _METRICS:
        value = _finite_float(maximum_spread[metric], f"{metric} maximum spread")
        if value < 0.0:
            raise ValueError("maximum spread thresholds must be nonnegative")
        thresholds[metric] = value
    tasks = [task for family_tasks in registered_families.values() for task in family_tasks]
    if not isinstance(records, Mapping) or set(records) - set(tasks):
        raise ValueError("functional records contain unregistered tasks")
    checkpoint_ids = [checkpoint["checkpoint_id"] for checkpoint in registered_checkpoints]
    normalized: dict[str, dict[str, dict[str, dict[str, Any]]]] = {}
    for task in tasks:
        raw_task = records.get(task, {})
        if not isinstance(raw_task, Mapping) or set(raw_task) - set(checkpoint_ids):
            raise ValueError(f"task {task} contains unregistered checkpoints")
        normalized[task] = {}
        for checkpoint_id in checkpoint_ids:
            raw_checkpoint = raw_task.get(checkpoint_id)
            normalized[task][checkpoint_id] = {}
            for metric in _METRICS:
                if raw_checkpoint is None:
                    normalized_record = {"status": "not_run", "reasons": ["missing_record"], "value": None}
                else:
                    if not isinstance(raw_checkpoint, Mapping) or set(raw_checkpoint) - set(_METRICS):
                        raise ValueError(f"{task}/{checkpoint_id} contains an unregistered metric")
                    raw_metric = raw_checkpoint.get(metric)
                    normalized_record = (
                        {"status": "not_run", "reasons": ["missing_metric_record"], "value": None}
                        if raw_metric is None
                        else _normalize_metric_record(raw_metric, f"{task}/{checkpoint_id}/{metric}")
                    )
                normalized[task][checkpoint_id][metric] = normalized_record

    task_summaries: dict[str, dict[str, Any]] = {}
    for task in tasks:
        task_summaries[task] = {}
        for metric in _METRICS:
            by_checkpoint = {checkpoint_id: normalized[task][checkpoint_id][metric] for checkpoint_id in checkpoint_ids}
            task_summaries[task][metric] = _summarize_checkpoint_values(
                checkpoint_ids, by_checkpoint, thresholds[metric], metric
            )

    family_summaries: dict[str, dict[str, Any]] = {}
    for family, family_tasks in registered_families.items():
        family_summaries[family] = {}
        for metric in _METRICS:
            derived: dict[str, dict[str, Any]] = {}
            for checkpoint_id in checkpoint_ids:
                task_records = [normalized[task][checkpoint_id][metric] for task in family_tasks]
                statuses = [record["status"] for record in task_records]
                values = [record["value"] for record in task_records]
                descriptive_values = [float(value) for value in values if value is not None]
                descriptive_mean = (
                    _checked_mean(descriptive_values, f"{family}/{checkpoint_id}/{metric} descriptive")
                    if len(descriptive_values) == len(values)
                    else None
                )
                if "ineligible" in statuses:
                    derived[checkpoint_id] = {
                        "status": "ineligible",
                        "reasons": ["representative_task_ineligible"],
                        "value": descriptive_mean,
                    }
                elif "not_run" in statuses or any(value is None for value in values):
                    derived[checkpoint_id] = {
                        "status": "not_run",
                        "reasons": ["representative_task_not_run"],
                        "value": descriptive_mean,
                    }
                else:
                    derived[checkpoint_id] = {
                        "status": "eligible",
                        "reasons": [],
                        "value": descriptive_mean,
                    }
            family_summaries[family][metric] = _summarize_checkpoint_values(
                checkpoint_ids, derived, thresholds[metric], metric
            )
    return {
        "schema_version": "msae_functional_reproducibility_v1",
        "metrics": list(_METRICS),
        "minimum_checkpoints": minimum_checkpoints,
        "checkpoint_registry": registered_checkpoints,
        "family_registry": registered_families,
        "maximum_spread_thresholds": thresholds,
        "tasks": task_summaries,
        "families": family_summaries,
    }


def _endpoint_record(
    config: Mapping[str, Any],
    config_digest: str,
    name: str,
    category: str,
    status_value: str,
    reasons: Sequence[str],
    evidence_digest: str | None,
    observed_value: Any,
) -> dict[str, Any]:
    return {
        "schema_version": config["endpoint_schema_version"],
        "protocol_config_sha256": config_digest,
        "endpoint_name": name,
        "category": category,
        "status": status_value,
        "reasons": list(reasons),
        "evidence_artifact_sha256": evidence_digest,
        "observed_value": observed_value,
    }


def _validate_endpoint_record(
    raw: Any,
    config: Mapping[str, Any],
    config_digest: str,
    name: str,
    category: str,
) -> dict[str, Any]:
    if not isinstance(raw, dict):
        raise ValueError(f"endpoint {name} must be an object")
    _require_exact_keys(raw, _ENDPOINT_KEYS, f"endpoint {name}")
    if raw["schema_version"] != config["endpoint_schema_version"]:
        raise ValueError(f"endpoint {name} schema mismatch")
    if raw["protocol_config_sha256"] != config_digest:
        raise ValueError(f"endpoint {name} config digest mismatch")
    if raw["endpoint_name"] != name or raw["category"] != category:
        raise ValueError(f"endpoint {name} registry binding mismatch")
    status_value = raw["status"]
    if status_value not in _VALID_STATUSES:
        raise ValueError(f"endpoint {name} has an invalid status")
    reasons = raw["reasons"]
    if not isinstance(reasons, list) or any(not isinstance(reason, str) or not reason for reason in reasons):
        raise ValueError(f"endpoint {name} reasons are invalid")
    if len(set(reasons)) != len(reasons):
        raise ValueError(f"endpoint {name} reasons must be unique")
    evidence_digest = raw["evidence_artifact_sha256"]
    if status_value == "not_run":
        if evidence_digest is not None:
            raise ValueError(f"endpoint {name} not_run evidence digest must be null")
    else:
        _validate_sha256(evidence_digest, f"endpoint {name} evidence digest")
    _reject_non_json(raw["observed_value"], f"endpoint {name} observed_value")
    return dict(raw)


def _missing_endpoint(config: Mapping[str, Any], config_digest: str, name: str, category: str) -> dict[str, Any]:
    return _endpoint_record(
        config,
        config_digest,
        name,
        category,
        "not_run",
        ["missing_required_evidence"],
        None,
        None,
    )


def _collect_generic_records(
    config: Mapping[str, Any],
    config_digest: str,
    supplied: Mapping[str, Mapping[str, Any]],
    categories: Mapping[str, str],
    internal: set[str],
) -> dict[str, dict[str, Any]]:
    if not isinstance(supplied, Mapping):
        raise ValueError("endpoint evidence must be a mapping")
    registered = set(categories)
    extra = set(supplied) - registered
    if extra:
        raise ValueError(f"unregistered endpoint evidence: {sorted(extra)}")
    forbidden = set(supplied) & internal
    if forbidden:
        raise ValueError(f"internally constructed endpoints cannot be supplied: {sorted(forbidden)}")
    result: dict[str, dict[str, Any]] = {}
    for name, category in categories.items():
        if name in internal:
            continue
        raw = supplied.get(name)
        result[name] = (
            _missing_endpoint(config, config_digest, name, category)
            if raw is None
            else _validate_endpoint_record(raw, config, config_digest, name, category)
        )
    return result


def _stage_registry(config: Mapping[str, Any], stage: str) -> tuple[list[str], list[str], dict[str, str]]:
    stage_config = config["stages"][stage]
    if stage in {"A", "B"}:
        required = list(stage_config["required"])
        optional = list(stage_config["optional"])
        category = f"stage_{stage.lower()}"
        categories = {name: category for name in required + optional}
    else:
        required = []
        categories = {}
        for category_name in _STAGE_C_CATEGORIES:
            names = list(stage_config["required_by_category"][category_name])
            if not names:
                raise ValueError(f"stage C {category_name} registry must be non-empty")
            required.extend(names)
            categories.update({name: category_name for name in names})
        optional = list(stage_config["optional"])
        categories.update({name: "optional" for name in optional})
    return required, optional, categories


def _make_stage_artifact(
    config: Mapping[str, Any],
    config_digest: str,
    dependency: Mapping[str, str],
    stage: str,
    prior_stage_sha256: str | None,
    endpoints: Mapping[str, Mapping[str, Any]],
    additional_blocking_reasons: Sequence[str] = (),
) -> dict[str, Any]:
    required, optional, _ = _stage_registry(config, stage)
    aggregate = _aggregate_endpoint_records(
        endpoints,
        required_endpoints=required,
        additional_blocking_reasons=additional_blocking_reasons,
    )
    registry = {"required": required, "optional": optional}
    return {
        "schema_version": config["artifact_schema_version"],
        "stage": stage,
        "purpose": config["stages"][stage]["purpose"],
        "protocol_id": config["protocol_id"],
        "protocol_config_sha256": config_digest,
        "dependency": dict(dependency),
        "requirement_registry_sha256": _canonical_digest(registry),
        "prior_stage_sha256": prior_stage_sha256,
        "endpoints": {name: dict(record) for name, record in endpoints.items()},
        "aggregate": aggregate,
        "stage_ready": aggregate["overall"]["status"] == "eligible",
    }


def _verify_predecessor(
    artifact: Any,
    config: Mapping[str, Any],
    config_digest: str,
    dependency: Mapping[str, str],
    expected_stage: str,
    expected_prior_stage_sha256: str | None = None,
) -> str:
    if not isinstance(artifact, dict):
        raise ValueError("predecessor artifact must be an object")
    _require_exact_keys(artifact, _STAGE_ARTIFACT_KEYS, "predecessor artifact")
    if artifact["schema_version"] != config["artifact_schema_version"]:
        raise ValueError("predecessor schema mismatch")
    if artifact["stage"] != expected_stage or artifact["purpose"] != config["stages"][expected_stage]["purpose"]:
        raise ValueError("predecessor stage or purpose mismatch")
    if artifact["protocol_id"] != config["protocol_id"] or artifact["protocol_config_sha256"] != config_digest:
        raise ValueError("predecessor protocol binding mismatch")
    if artifact["dependency"] != dict(dependency):
        raise ValueError("predecessor dependency binding mismatch")
    required, optional, categories = _stage_registry(config, expected_stage)
    expected_registry_digest = _canonical_digest({"required": required, "optional": optional})
    if artifact["requirement_registry_sha256"] != expected_registry_digest:
        raise ValueError("predecessor requirement registry mismatch")
    endpoints = artifact["endpoints"]
    if not isinstance(endpoints, dict) or set(endpoints) != set(required + optional):
        raise ValueError("predecessor endpoints do not match the registry")
    validated = {
        name: _validate_endpoint_record(record, config, config_digest, name, categories[name])
        for name, record in endpoints.items()
    }
    additional_blockers = [
        reason for reason in _config_blockers(config) if reason.startswith("replay_")
    ] if expected_stage == "A" else []
    recomputed = _aggregate_endpoint_records(
        validated,
        required_endpoints=required,
        additional_blocking_reasons=additional_blockers,
    )
    if artifact["aggregate"] != recomputed:
        raise ValueError("predecessor aggregate does not recompute")
    expected_ready = recomputed["overall"]["status"] == "eligible"
    if artifact["stage_ready"] is not expected_ready:
        raise ValueError("predecessor stage_ready does not recompute")
    if expected_stage == "A":
        if expected_prior_stage_sha256 is not None or artifact["prior_stage_sha256"] is not None:
            raise ValueError("stage A predecessor binding must be null")
    else:
        if expected_prior_stage_sha256 is None:
            raise ValueError("expected prior-stage digest is required for chained predecessor verification")
        _validate_sha256(expected_prior_stage_sha256, "expected prior-stage digest")
        if artifact["prior_stage_sha256"] != expected_prior_stage_sha256:
            raise ValueError("predecessor prior-stage digest does not match the verified artifact")
    if not expected_ready:
        raise ValueError("predecessor is not technically ready")
    return _canonical_digest(artifact)


def build_stage_a(
    raw_config_bytes: bytes,
    expected_raw_config_sha256: str,
    endpoint_evidence: Mapping[str, Mapping[str, Any]],
) -> dict[str, Any]:
    config, config_digest = _load_bound_config(raw_config_bytes, expected_raw_config_sha256)
    dependency = verify_dependency(config["dependency"]["sha256"])
    required, optional, categories = _stage_registry(config, "A")
    internal = {"dependency_attestation"}
    records = _collect_generic_records(config, config_digest, endpoint_evidence, categories, internal)
    records["dependency_attestation"] = _endpoint_record(
        config,
        config_digest,
        "dependency_attestation",
        categories["dependency_attestation"],
        "eligible",
        [],
        dependency["sha256"],
        dict(dependency),
    )
    ordered = {name: records[name] for name in required + optional}
    replay_blockers = [reason for reason in _config_blockers(config) if reason.startswith("replay_")]
    return _make_stage_artifact(
        config,
        config_digest,
        dependency,
        "A",
        None,
        ordered,
        replay_blockers,
    )


def build_stage_b(
    raw_config_bytes: bytes,
    expected_raw_config_sha256: str,
    stage_a_artifact: Mapping[str, Any],
    replay_bundle: Mapping[str, Any],
    endpoint_evidence: Mapping[str, Mapping[str, Any]],
) -> dict[str, Any]:
    config, config_digest = _load_bound_config(raw_config_bytes, expected_raw_config_sha256)
    dependency = verify_dependency(config["dependency"]["sha256"])
    prior_digest = _verify_predecessor(stage_a_artifact, config, config_digest, dependency, "A")
    selection = select_replay_tolerance(raw_config_bytes, expected_raw_config_sha256, replay_bundle)
    selection_digest = _canonical_digest(selection)
    required, optional, categories = _stage_registry(config, "B")
    internal = {"calibration_replay", "selected_replay_tolerance"}
    records = _collect_generic_records(config, config_digest, endpoint_evidence, categories, internal)
    records["calibration_replay"] = _endpoint_record(
        config,
        config_digest,
        "calibration_replay",
        categories["calibration_replay"],
        "eligible",
        [],
        selection_digest,
        {
            "source_role": selection["source_role"],
            "source_revision": selection["source_revision"],
            "partition": selection["partition"],
            "replay_registry_sha256": selection["replay_registry_sha256"],
            "selector_result_sha256": selection_digest,
            "payload_sha256": {
                report["stratum_id"]: report["payload_sha256"] for report in selection["strata"]
            },
        },
    )
    records["selected_replay_tolerance"] = _endpoint_record(
        config,
        config_digest,
        "selected_replay_tolerance",
        categories["selected_replay_tolerance"],
        selection["status"],
        selection["reasons"],
        selection_digest,
        {
            "selected_index": selection["selected_index"],
            "selected_tolerance": selection["selected_tolerance"],
            "pass_matrix": selection["pass_matrix"],
            "rationale": selection["rationale"],
        },
    )
    ordered = {name: records[name] for name in required + optional}
    return _make_stage_artifact(config, config_digest, dependency, "B", prior_digest, ordered)


def build_stage_c(
    raw_config_bytes: bytes,
    expected_raw_config_sha256: str,
    stage_a_artifact: Mapping[str, Any],
    stage_b_artifact: Mapping[str, Any],
    endpoint_evidence: Mapping[str, Mapping[str, Any]],
) -> dict[str, Any]:
    config, config_digest = _load_bound_config(raw_config_bytes, expected_raw_config_sha256)
    dependency = verify_dependency(config["dependency"]["sha256"])
    stage_a_digest = _verify_predecessor(stage_a_artifact, config, config_digest, dependency, "A")
    prior_digest = _verify_predecessor(
        stage_b_artifact,
        config,
        config_digest,
        dependency,
        "B",
        expected_prior_stage_sha256=stage_a_digest,
    )
    functional_blockers = [
        reason for reason in _config_blockers(config) if reason.startswith("functional_")
    ]
    if functional_blockers:
        raise ValueError(f"stage C functional registry is incomplete: {functional_blockers}")
    required, optional, categories = _stage_registry(config, "C")
    records = _collect_generic_records(config, config_digest, endpoint_evidence, categories, set())
    ordered = {name: records[name] for name in required + optional}
    return _make_stage_artifact(config, config_digest, dependency, "C", prior_digest, ordered)
