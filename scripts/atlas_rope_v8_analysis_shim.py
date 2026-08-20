#!/usr/bin/env python3
"""Read-only shim for the frozen Atlas v3.3 analyzer.

The historical analyzer imports several names from its extraction module.  An
Attempt-12 process installs this module under that legacy module name before
loading the analyzer.  Only source-bundle loading and GPU identity are usable;
all extraction, staging, and legacy CLI support fails closed.
"""
from __future__ import annotations

from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator, Mapping

import torch

from atlas_rope_v6 import ROOT, read_jsonl, sha256_file


def _gpu_uuid(device: torch.device) -> str:
    index = device.index if device.index is not None else torch.cuda.current_device()
    value = str(torch.cuda.get_device_properties(index).uuid)
    return value if value.startswith("GPU-") else f"GPU-{value}"


def _load_source_bundle(
    prescore: Mapping[str, Any], manifest: Mapping[str, Any], source: str, *, data_root: str | None = None
) -> dict[str, Any]:
    root = ROOT / str(data_root or prescore["data_root"]) / "prepared" / source
    specs = manifest["sources"][source]
    paths = {
        "units": root / "inference_units.jsonl",
        "rows": root / "activation_rows.jsonl",
        "pairs": root / "intervention_pairs.jsonl",
    }
    expected = {
        "units": specs["units_sha256"],
        "rows": specs["activation_rows_sha256"],
        "pairs": specs["intervention_pairs_sha256"],
    }
    for key, path in paths.items():
        if sha256_file(path) != expected[key]:
            raise RuntimeError(f"{source} child input digest drift: {key}")
    units, rows, pairs = read_jsonl(paths["units"]), read_jsonl(paths["rows"]), read_jsonl(paths["pairs"])
    unit_ids: set[str] = set()
    all_row_ids: set[str] = set()
    flattened: list[str] = []
    row_to_unit: dict[str, dict[str, Any]] = {}
    for unit in units:
        unit_id = str(unit["unit_id"])
        if unit_id in unit_ids:
            raise RuntimeError("duplicate inference unit ID")
        unit_ids.add(unit_id)
        n = len(unit["input_ids"])
        if not n or any(len(unit[key]) != n for key in ("attention_mask", "position_ids")):
            raise RuntimeError("invalid unit tensor lengths")
        if any(int(value) != 1 for value in unit["attention_mask"]):
            raise RuntimeError("prepared unit attention mask is not all visible")
        if len(unit["positions"]) != len(unit["row_ids"]):
            raise RuntimeError("unit target/row length drift")
        if any(not 0 <= int(position) < n for position in unit["positions"]):
            raise RuntimeError("unit target position outside input")
        for raw_row_id in unit["row_ids"]:
            row_id = str(raw_row_id)
            if row_id in all_row_ids:
                raise RuntimeError("duplicate activation row ID")
            all_row_ids.add(row_id)
            flattened.append(row_id)
            row_to_unit[row_id] = unit
    expected_rows = [str(row["row_id"]) for row in rows]
    if len(expected_rows) != len(set(expected_rows)) or flattened != expected_rows:
        raise RuntimeError("ordered activation-row lineage drift")
    pair_ids = [str(row["pair_id"]) for row in pairs]
    if len(pair_ids) != len(set(pair_ids)):
        raise RuntimeError("duplicate intervention pair ID")
    pair_row_ids: set[str] = set()

    def collect(value: Any) -> None:
        if isinstance(value, str):
            pair_row_ids.add(value)
        elif isinstance(value, Mapping):
            for child in value.values():
                collect(child)

    for pair in pairs:
        collect(pair["rows"])
    if not pair_row_ids.issubset(all_row_ids):
        raise RuntimeError("intervention pair references unknown activation row")
    return {"root": root, "units": units, "rows": rows, "pairs": pairs, "row_to_unit": row_to_unit}


def _forbidden(*args: Any, **kwargs: Any) -> Any:
    raise RuntimeError("Attempt-12 safe analyzer shim forbids legacy extraction/staging entry points")


@contextmanager
def _exclusive_lock(*args: Any, **kwargs: Any) -> Iterator[None]:
    _forbidden(*args, **kwargs)
    yield  # pragma: no cover


_fsync_directory = _forbidden
_fsync_file = _forbidden
_new_staging = _forbidden
_promote = _forbidden
_verify_complete_cache = _forbidden
_verify_qa = _forbidden
load_scoring_config = _forbidden
