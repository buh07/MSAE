#!/usr/bin/env python3
"""Build Atlas v3.5 attempt-9 technical panels without loading model weights."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import sys
import tempfile
from collections import Counter
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

sys.path.insert(0, str(Path(__file__).resolve().parent))

from atlas_discovery_v3_3 import parse_conllu, sentence_content_hash, token_layout
from atlas_rope_v5 import (
    ATTEMPT7_ROOT,
    LENGTH_BINS,
    PANEL_SCHEMA,
    PRESCORE_SCHEMA,
    ROOT,
    RUN_ROOT,
    SHIFTS,
    atomic_json,
    atomic_jsonl,
    batch_schedule,
    bidirectional_sequence_view_overlap,
    child_spec,
    deterministic_document_capped_selection,
    length_bin,
    make_grid_units,
    normalized_text_hash,
    read_json,
    read_jsonl,
    recursive_inventory,
    sequence_sha256,
    sha256_bytes,
    sha256_file,
    stable_utf8_sha256,
    validate_grid_units,
    validate_repo_relative,
    verify_attempt7_retirement,
)


DATA_ROOT = ROOT / "data/atlas_rope_v5_attempt9"
PRESCORE_PATH = ROOT / "configs/atlas_rope_v5/prescore.json"
RETIREMENT_PATH = ROOT / "pilot_runs/20260803_atlas_rope_technical_v4/provenance/ATTEMPT7_RETIRED.json"
MEASUREMENT_ROOT = ROOT / "data/atlas_measurement_v2_4/prepared"
FINAL_SCIENCE_ROOT = ROOT / "data/atlas_discovery_v3_3_attempt7_final_v3/prepared"


def _logical_child_spec(path: Path, staging_root: Path) -> dict[str, Any]:
    logical = DATA_ROOT / path.relative_to(staging_root)
    return {"path": str(logical.relative_to(ROOT)), "bytes": path.stat().st_size, "sha256": sha256_file(path)}


def _verify_spec(spec: Mapping[str, Any]) -> Path:
    path = validate_repo_relative(str(spec["path"]))
    if path.is_symlink() or not path.is_file() or sha256_file(path) != str(spec["sha256"]):
        raise RuntimeError(f"input lineage drift: {spec['path']}")
    return path


def _parse_source(path: Path, source: str) -> list[Any]:
    """Parse UD data, synthesizing ESLSpok document markers from record IDs.

    ESLSpok's pinned files have sentence records but no ``newdoc`` comments. Its
    genuine document identity is the filename prefix of ``sent_id``. We group
    blocks by that prefix and inject one parser-only document marker; the raw
    file itself and its hash remain unchanged and bound in the manifest.
    """

    raw = path.read_text(encoding="utf-8")
    if "# newdoc id" in raw:
        return parse_conllu(path, source)
    blocks = [block for block in raw.split("\n\n") if block.strip()]
    by_document: dict[str, list[str]] = {}
    for block in blocks:
        sent_lines = [line for line in block.splitlines() if line.startswith("# sent_id") and "=" in line]
        if len(sent_lines) != 1:
            raise RuntimeError(f"missing/duplicate ESLSpok sent_id block: {path}")
        sent_id = sent_lines[0].split("=", 1)[1].strip()
        if "_" not in sent_id:
            raise RuntimeError(f"ESLSpok record ID lacks document prefix: {sent_id}")
        document = sent_id.rsplit("_", 1)[0]
        by_document.setdefault(document, []).append(block)
    assembled: list[str] = []
    for document in sorted(by_document, key=lambda value: value.encode("utf-8")):
        assembled.append(f"# newdoc id = {document}")
        assembled.extend(by_document[document])
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", suffix=".conllu", delete=False) as handle:
        handle.write("\n\n".join(assembled) + "\n")
        temporary = Path(handle.name)
    try:
        return parse_conllu(temporary, source)
    finally:
        temporary.unlink(missing_ok=True)


def _walk_strings(value: Any) -> Iterable[str]:
    if isinstance(value, str):
        yield value
    elif isinstance(value, Mapping):
        for child in value.values():
            yield from _walk_strings(child)
    elif isinstance(value, Sequence) and not isinstance(value, (bytes, bytearray, str)):
        for child in value:
            yield from _walk_strings(child)


def _science_firewall() -> dict[str, Any]:
    documents: set[str] = set()
    components: set[str] = set()
    sentences: set[str] = set()
    logical_units: set[str] = set()
    sequences: set[str] = set()
    row_ids: set[str] = set()
    for source in ("EWT", "GUM"):
        source_root = FINAL_SCIENCE_ROOT / source
        for path in sorted(source_root.glob("*.jsonl")):
            for record in read_jsonl(path):
                for key in ("document_group", "donor_document_group"):
                    if record.get(key) is not None:
                        documents.add(str(record[key]))
                if record.get("component_id") is not None:
                    components.add(str(record["component_id"]))
                for key in ("sent_id", "target_sent_id", "source_sent_id", "donor_sent_id", "true_prefix_sent_id", "unrelated_prefix_sent_id"):
                    if record.get(key) is not None:
                        sentences.add(str(record[key]))
                if record.get("unit_id") is not None:
                    logical_units.add(str(record["unit_id"]))
                if record.get("row_id") is not None:
                    row_ids.add(str(record["row_id"]))
                if isinstance(record.get("input_ids"), list):
                    sequences.add(sequence_sha256(record["input_ids"]))
    # Bind normalized main-sentence content independently of prepared tokenization.
    content_hashes: set[str] = set()
    run = read_json(ROOT / "configs/atlas_discovery_v3_3/run_final_v3.json")
    for source, spec in run["sources"].items():
        path = _verify_spec(spec)
        for sentence in _parse_source(path, source):
            content_hashes.add(sentence_content_hash(sentence))
    return {
        "documents": sorted(documents),
        "components": sorted(components),
        "sentences": sorted(sentences),
        "logical_units": sorted(logical_units),
        "row_ids": sorted(row_ids),
        "sequence_sha256": sorted(sequences),
        "content_sha256": sorted(content_hashes),
    }


def _prior_esl_exposure(config: Mapping[str, Any]) -> dict[str, Any]:
    row_ids: set[str] = set()
    documents: set[str] = set()
    source_records: set[str] = set()
    roles: dict[str, dict[str, int]] = {}
    sequences: list[list[int]] = []
    sequence_hashes: set[str] = set()
    unit_ids: set[str] = set()
    for role in ("calibration", "discovery", "C1", "C2"):
        row_path = MEASUREMENT_ROOT / role / "activation_rows.jsonl"
        unit_path = MEASUREMENT_ROOT / role / "inference_units.jsonl"
        role_rows = [row for row in read_jsonl(row_path) if row.get("source") == "UD_English-ESLSpok"]
        role_row_ids = {str(row["row_id"]) for row in role_rows}
        row_ids.update(role_row_ids)
        documents.update(str(row["document_group"]) for row in role_rows)
        source_records.update(str(row["source_record_id"]) for row in role_rows)
        role_units = []
        for unit in read_jsonl(unit_path):
            if role_row_ids.intersection(map(str, unit.get("row_ids", []))):
                ids = list(map(int, unit["input_ids"]))
                role_units.append(unit)
                sequences.append(ids)
                sequence_hashes.add(sequence_sha256(ids))
                unit_ids.add(str(unit["unit_id"]))
        roles[role] = {"rows": len(role_rows), "units": len(role_units), "documents": len({str(row["document_group"]) for row in role_rows})}

    # Resolve record identities to normalized raw content across all pinned splits.
    esl = config["rejected_supplemental_candidates"]["ESLSpok"]
    raw_specs = list(esl["files"])
    content_hashes: set[str] = set()
    observed_records: set[str] = set()
    for spec in raw_specs:
        path = _verify_spec(spec)
        for sentence in _parse_source(path, "ESLSpok"):
            if sentence.sent_id in source_records:
                observed_records.add(sentence.sent_id)
                content_hashes.add(sentence_content_hash(sentence))
    if observed_records != source_records:
        missing = sorted(source_records - observed_records)
        raise RuntimeError(f"prior ESL source records not found in pinned raw data: {missing[:5]}")
    sequences.sort(key=lambda values: (len(values), sequence_sha256(values)))
    return {
        "roles": roles,
        "row_ids": sorted(row_ids),
        "documents": sorted(documents),
        "source_record_ids": sorted(source_records),
        "unit_ids": sorted(unit_ids),
        "input_sequences": sequences,
        "sequence_sha256": sorted(sequence_hashes),
        "content_sha256": sorted(content_hashes),
        "exposure_scope": "all prior atlas_measurement_v2_4 roles joined from ESL activation rows to inference units",
    }


def _document_source_urls(path: Path) -> dict[str, str]:
    current: str | None = None
    output: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.startswith("# newdoc id") and "=" in line:
            current = line.split("=", 1)[1].strip()
        elif line.startswith("# meta::sourceURL") and "=" in line:
            if current is None:
                raise RuntimeError(f"sourceURL before document identity: {path}")
            url = line.split("=", 1)[1].strip()
            if current in output and output[current] != url:
                raise RuntimeError(f"multiple source URLs for one document: {path}:{current}")
            output[current] = url
    return output


def _rejected_gumreddit_audit(config: Mapping[str, Any]) -> dict[str, Any]:
    spec = config["rejected_supplemental_candidates"]["GUMReddit"]
    token_rows = 0
    placeholder_forms = 0
    documents: set[str] = set()
    sentences: set[str] = set()
    files: list[dict[str, Any]] = []
    for file_spec in spec["files"]:
        path = _verify_spec(file_spec)
        for line in path.read_text(encoding="utf-8").splitlines():
            if line.startswith("# newdoc id") and "=" in line:
                documents.add(line.split("=", 1)[1].strip())
            elif line.startswith("# sent_id") and "=" in line:
                sentences.add(line.split("=", 1)[1].strip())
            fields = line.split("\t")
            if len(fields) == 10 and fields[0].isdigit():
                token_rows += 1
                placeholder_forms += int(fields[1] == "_")
        files.append({"path": str(path.relative_to(ROOT)), "sha256": sha256_file(path)})
    status = "REJECTED_NO_MODEL_CALLS" if token_rows == placeholder_forms == 16364 and len(documents) == 18 else "AUDIT_DRIFT"
    if status != "REJECTED_NO_MODEL_CALLS":
        raise RuntimeError("GUMReddit rejection audit drift")
    return {"status": status, "reason": str(spec["reason"]), "token_rows": token_rows,
            "placeholder_forms": placeholder_forms, "documents": len(documents), "sentences": len(sentences), "files": files}


def _prior_project_exposure() -> dict[str, Any]:
    """Overinclusive exact-match firewall across every prior prepared input."""

    sequence_hashes: set[str] = set()
    documents: set[str] = set()
    sentences: set[str] = set()
    source_urls: set[str] = set()
    content_hashes: set[str] = set()
    input_files: list[dict[str, Any]] = []
    for path in sorted((ROOT / "data").rglob("inference_units.jsonl"), key=lambda p: str(p).encode("utf-8")):
        if "atlas_rope_v5_attempt9" in path.parts:
            continue
        for unit in read_jsonl(path):
            if isinstance(unit.get("input_ids"), list):
                sequence_hashes.add(sequence_sha256(unit["input_ids"]))
            for key in ("unit_id", "sent_id", "target_sent_id"):
                if unit.get(key) is not None:
                    sentences.add(str(unit[key]))
        input_files.append({"path": str(path.relative_to(ROOT)), "sha256": sha256_file(path)})
    for path in sorted((ROOT / "data").rglob("activation_rows.jsonl"), key=lambda p: str(p).encode("utf-8")):
        if "atlas_rope_v5_attempt9" in path.parts:
            continue
        for row in read_jsonl(path):
            for key in ("document_group", "donor_document_group"):
                if row.get(key) is not None:
                    documents.add(str(row[key])); documents.add(str(row[key]).split(":", 1)[-1])
            for key in ("sent_id", "source_record_id", "target_sent_id", "source_sent_id", "donor_sent_id"):
                if row.get(key) is not None:
                    sentences.add(str(row[key]))
        input_files.append({"path": str(path.relative_to(ROOT)), "sha256": sha256_file(path)})
    gentle_root = ROOT / "data/atlas_rope_v4_raw/UD_English-GENTLE"
    for path in sorted((ROOT / "data").rglob("*.conllu"), key=lambda p: str(p).encode("utf-8")):
        if path.is_relative_to(gentle_root):
            continue
        try:
            parsed = _parse_source(path, "prior")
        except RuntimeError:
            # Combined/derived files can repeat document IDs; their canonical
            # original is also present and inference-unit hashes remain bound.
            continue
        for sentence in parsed:
            documents.add(str(sentence.document_id))
            sentences.add(str(sentence.sent_id))
            content_hashes.add(sentence_content_hash(sentence))
        source_urls.update(_document_source_urls(path).values())
        input_files.append({"path": str(path.relative_to(ROOT)), "sha256": sha256_file(path)})
    # Opened ledgers can contain URLs/IDs absent from representation rows.
    for path in sorted((ROOT / "data").rglob("*opened*ledger*.json"), key=lambda p: str(p).encode("utf-8")):
        text = path.read_text(encoding="utf-8")
        source_urls.update(re.findall(r"https?://[^\s\"']+", text))
        input_files.append({"path": str(path.relative_to(ROOT)), "sha256": sha256_file(path)})
    # Deduplicate the input inventory itself after derived scans.
    unique_files = {(row["path"], row["sha256"]) for row in input_files}
    return {
        "scope": "all repository prior prepared inference units/activation rows, local prior raw conllu, and opened-input ledgers",
        "sequence_sha256": sorted(sequence_hashes),
        "content_sha256": sorted(content_hashes),
        "document_ids": sorted(documents),
        "sentence_ids": sorted(sentences),
        "source_urls": sorted(source_urls),
        "input_files": [{"path": path, "sha256": digest} for path, digest in sorted(unique_files)],
    }


def _gum_legacy_exposure() -> dict[str, Any]:
    split = read_json(ROOT / "configs/atlas_discovery_v3_3/population_split_v3.json")
    documents = set(map(str, split["sources"]["GUM"]["legacy_documents"]))
    legacy_ids = set(map(str, split["sources"]["GUM"]["legacy_pair_ids"]))
    pair_path = ROOT / "data/atlas_discovery_v3_1_attempt5/prepared/GUM/intervention_pairs.jsonl"
    unit_path = ROOT / "data/atlas_discovery_v3_1_attempt5/prepared/GUM/inference_units.jsonl"
    pairs = [row for row in read_jsonl(pair_path) if str(row["pair_id"]) in legacy_ids]
    selected_rows = {value for pair in pairs for value in _walk_strings(pair["rows"]) if value.startswith("atlas_")}
    units = [unit for unit in read_jsonl(unit_path) if selected_rows.intersection(map(str, unit["row_ids"]))]
    return {
        "documents": sorted(documents),
        "sequence_sha256": sorted({sequence_sha256(unit["input_ids"]) for unit in units}),
        "units": sorted(str(unit["unit_id"]) for unit in units),
        "pairs": sorted(legacy_ids),
    }


def _fresh_gum_unit_sequence_hashes() -> set[str]:
    split = read_json(ROOT / "configs/atlas_discovery_v3_3/population_split_v3.json")
    pair_ids = set(map(str, split["sources"]["GUM"]["fresh_pair_ids"]))
    parent = ROOT / "data/atlas_discovery_v3_3_attempt7_qa_compact_v3/prepared/GUM"
    pairs = [row for row in read_jsonl(parent / "intervention_pairs.jsonl") if str(row["pair_id"]) in pair_ids]
    row_ids = {value for pair in pairs for value in _walk_strings(pair["rows"]) if value.startswith("atlas_")}
    return {sequence_sha256(unit["input_ids"]) for unit in read_jsonl(parent / "inference_units.jsonl")
            if row_ids.intersection(map(str, unit["row_ids"]))}


def _candidate_records(config: Mapping[str, Any], tokenizer: Any, source: str,
                       science: Mapping[str, Any], gum: Mapping[str, Any],
                       prior: Mapping[str, Any]) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    parsed = []
    source_urls: dict[str, str] = {}
    for spec in config["sources"][source]["files"]:
        path = _verify_spec(spec)
        parsed.extend(_parse_source(path, source))
        for document, url in _document_source_urls(path).items():
            if document in source_urls and source_urls[document] != url:
                raise RuntimeError(f"source URL drift for {source}:{document}")
            source_urls[document] = url
    seen_sentences: set[str] = set()
    candidates: list[dict[str, Any]] = []
    exclusions: Counter[str] = Counter()
    science_sets = {key: set(map(str, science[key])) for key in science}
    gum_sets = {key: set(map(str, gum[key])) for key in ("documents", "sequence_sha256")}
    prior_sets = {key: set(map(str, prior[key])) for key in ("document_ids", "sentence_ids", "source_urls", "sequence_sha256", "content_sha256")}
    fresh_gum_hashes = _fresh_gum_unit_sequence_hashes() if source == "GUM_fresh_validation" else set()
    for sentence in parsed:
        if sentence.sent_id in seen_sentences:
            raise RuntimeError(f"duplicate sentence ID across source files: {source}:{sentence.sent_id}")
        seen_sentences.add(sentence.sent_id)
        layout = token_layout(tokenizer, sentence, 128)
        if not layout["complete"]:
            exclusions["longer_than_128"] += 1
            continue
        ids = list(map(int, layout["input_ids"]))
        bin_name = length_bin(len(ids))
        if bin_name is None:
            exclusions["outside_length_bins"] += 1
            continue
        seq_hash = sequence_sha256(ids)
        content_hash = sentence_content_hash(sentence)
        doc = f"{source}:{sentence.document_id}"
        # Compare source-normalized identities as well as literal prepared identities.
        science_doc_candidates = {doc, f"EWT:{sentence.document_id}", f"GUM:{sentence.document_id}"}
        if source == "EWT_calibration":
            if science_doc_candidates & science_sets["documents"]:
                exclusions["science_document"] += 1; continue
            if sentence.sent_id in science_sets["sentences"]:
                exclusions["science_sentence"] += 1; continue
            if seq_hash in science_sets["sequence_sha256"]:
                exclusions["science_token_sequence"] += 1; continue
            if content_hash in science_sets["content_sha256"]:
                exclusions["science_normalized_content"] += 1; continue
        elif source == "GUM_fresh_validation":
            if f"GUM:{sentence.document_id}" in gum_sets["documents"]:
                exclusions["opened_legacy_gum_document"] += 1; continue
            if seq_hash in gum_sets["sequence_sha256"]:
                exclusions["opened_legacy_gum_sequence"] += 1; continue
            if seq_hash in fresh_gum_hashes:
                exclusions["separate_fresh_sentinel_sequence"] += 1; continue
        elif source == "GENTLE_validation":
            if any(token.form == "_" for token in sentence.tokens):
                exclusions["placeholder_token_form"] += 1; continue
            if sentence.document_id in prior_sets["document_ids"] or f"GENTLE:{sentence.document_id}" in prior_sets["document_ids"]:
                exclusions["prior_document_identity"] += 1; continue
            if sentence.sent_id in prior_sets["sentence_ids"]:
                exclusions["prior_sentence_identity"] += 1; continue
            url = source_urls.get(sentence.document_id)
            if not url:
                raise RuntimeError(f"GENTLE document missing source URL: {sentence.document_id}")
            if url in prior_sets["source_urls"]:
                exclusions["prior_source_url"] += 1; continue
            if seq_hash in prior_sets["sequence_sha256"]:
                exclusions["prior_exact_token_sequence"] += 1; continue
            if content_hash in prior_sets["content_sha256"]:
                exclusions["prior_exact_content"] += 1; continue
        candidates.append({
            "source": source,
            "document_id": sentence.document_id,
            "sent_id": sentence.sent_id,
            "length_bin": bin_name,
            "input_ids": ids,
            "sequence_sha256": seq_hash,
            "content_sha256": content_hash,
            "source_url": source_urls.get(sentence.document_id),
        })
    return candidates, {"raw_sentences": len(parsed), "retained_candidates": len(candidates), "exclusions": dict(sorted(exclusions.items()))}


def _load_bundle(root: Path) -> dict[str, Any]:
    units = read_jsonl(root / "inference_units.jsonl")
    rows = read_jsonl(root / "activation_rows.jsonl")
    pairs = read_jsonl(root / "intervention_pairs.jsonl")
    row_to_unit: dict[str, dict[str, Any]] = {}
    for unit in units:
        for row_id in unit["row_ids"]:
            if row_id in row_to_unit:
                raise RuntimeError("duplicate row ID in parent QA bundle")
            row_to_unit[str(row_id)] = unit
    return {"units": units, "rows": rows, "pairs": pairs, "row_to_unit": row_to_unit}


def _assert_translation(reference: Mapping[str, Any], candidate: Mapping[str, Any], offset: int) -> None:
    for key in ("input_ids", "attention_mask", "positions"):
        if list(reference[key]) != list(candidate[key]):
            raise RuntimeError(f"fresh GUM sentinel changes {key}")
    differences = [int(b) - int(a) for a, b in zip(reference["position_ids"], candidate["position_ids"], strict=True)]
    if not differences or any(value != offset for value in differences):
        raise RuntimeError("fresh GUM sentinel is not the frozen global translation")


def _build_gum_sentinel(root: Path) -> dict[str, Any]:
    split = read_json(ROOT / "configs/atlas_discovery_v3_3/population_split_v3.json")
    pair_ids = list(map(str, split["sources"]["GUM"]["fresh_pair_ids"]))
    if len(pair_ids) != 16 or len(set(pair_ids)) != 16:
        raise RuntimeError("fresh GUM sentinel pair list drift")
    parent = _load_bundle(ROOT / "data/atlas_discovery_v3_3_attempt7_qa_compact_v3/prepared/GUM")
    by_id = {str(pair["pair_id"]): pair for pair in parent["pairs"]}
    references: list[dict[str, Any]] = []
    candidates: list[dict[str, Any]] = []
    pair_rows: list[dict[str, Any]] = []
    expanded_row_ids: list[str] = []
    counts = Counter()
    for pair_id in pair_ids:
        pair = by_id[pair_id]
        counts[str(pair["construct"])] += 1
        if pair["construct"] == "context_factorial":
            reference = parent["row_to_unit"][str(pair["rows"]["bare"])]
            candidate = parent["row_to_unit"][str(pair["rows"]["prefix_position_only"])]
            roles = ["target"]
            offset = int(pair["prefix_length"]) + 1
            family = "prefix_position_only"
        elif pair["construct"] == "relative_gap":
            reference = parent["row_to_unit"][str(pair["rows"]["bare"]["pre"])]
            candidate = parent["row_to_unit"][str(pair["rows"]["uniform_shift"]["pre"])]
            roles = ["pre", "post"]
            offset = 16
            family = "uniform_shift"
        else:
            raise RuntimeError("unexpected fresh GUM sentinel construct")
        _assert_translation(reference, candidate, offset)
        references.append(dict(reference))
        candidates.append(dict(candidate))
        row_ids = [f"atlas_rope_v5:GUM_sentinel:{pair_id}:{role}" for role in roles]
        expanded_row_ids.extend(row_ids)
        pair_rows.append({"pair_id": pair_id, "family": family, "roles": roles, "offset": offset,
                          "reference_unit_id": reference["unit_id"], "candidate_unit_id": candidate["unit_id"],
                          "expanded_row_ids": row_ids})
    if counts != {"context_factorial": 8, "relative_gap": 8} or sum(len(row["roles"]) for row in pair_rows) != 24:
        raise RuntimeError(f"fresh GUM sentinel counts drift: {counts}")
    sentinel_root = root / "GUM_fresh_sentinel"
    sentinel_root.mkdir(parents=True)
    atomic_jsonl(sentinel_root / "references.jsonl", references)
    atomic_jsonl(sentinel_root / "candidates.jsonl", candidates)
    atomic_jsonl(sentinel_root / "pair_rows.jsonl", pair_rows)
    schedules = {
        "reference": batch_schedule(references),
        "candidate": batch_schedule(candidates),
        "reference_repeats": [batch_schedule(references) for _ in range(3)],
    }
    if [batch["tensor_shape"][0] for batch in schedules["reference"]] != [16] or [batch["tensor_shape"][0] for batch in schedules["candidate"]] != [16]:
        raise RuntimeError("fresh GUM sentinel must use one separate 16-unit partial batch per side")
    manifest = {
        "schema_version": "atlas_rope_v5_attempt9_fresh_gum_sentinel_v1",
        "status": "frozen_unopened",
        "literal_pair_ids": pair_ids,
        "pairs": 16,
        "reference_units": 16,
        "candidate_units": 16,
        "expanded_rows_per_side": 24,
        "expanded_row_ids": expanded_row_ids,
        "family_counts": dict(sorted(counts.items())),
        "schedules": schedules,
        "children": {name: _logical_child_spec(sentinel_root / name, root) for name in ("references.jsonl", "candidates.jsonl", "pair_rows.jsonl")},
        "non_poolable_with_grid": True,
    }
    atomic_json(sentinel_root / "panel.json", manifest)
    return {**manifest, "panel_sha256": sha256_file(sentinel_root / "panel.json")}


def _write_source_panel(root: Path, source: str, candidates: Sequence[Mapping[str, Any]], selection_report: Mapping[str, Any],
                        exclusion_report: Mapping[str, Any]) -> dict[str, Any]:
    selected, support = deterministic_document_capped_selection(candidates)
    selected_union_documents = sorted({str(row["document_id"]) for row in selected}, key=lambda value: value.encode("utf-8"))
    if source == "GENTLE_validation" and len(selected_union_documents) < 20:
        raise RuntimeError("GENTLE selected-panel union has fewer than 20 genuine documents")
    support = {**support, "selected_panel_union_documents": len(selected_union_documents),
               "selected_panel_document_ids": selected_union_documents,
               "selected_panel_union_minimum": 20 if source == "GENTLE_validation" else None}
    references, shifted, rows = make_grid_units(source, selected)
    source_root = root / source
    source_root.mkdir(parents=True)
    atomic_jsonl(source_root / "references.jsonl", references)
    atomic_jsonl(source_root / "candidates.jsonl", shifted)
    atomic_jsonl(source_root / "rows.jsonl", rows)
    schedules = {
        "reference": batch_schedule(references),
        "candidate": batch_schedule(shifted),
        "reference_repeats": [batch_schedule(references) for _ in range(3)],
    }
    panel = {
        "schema_version": PANEL_SCHEMA,
        "status": "eligible_unopened" if source != "EWT_calibration" else "eligible_calibration",
        "source": source,
        "logical_counts": {"bases": 100, "reference_units": 100, "candidate_units": 600,
                           "reference_rows": 200, "candidate_rows": 1200, "cells": 30,
                           "rows_per_cell": 40, "elements_per_cell": 30720},
        "selection_support": support,
        "candidate_audit": dict(exclusion_report),
        "schedules": schedules,
        "children": {name: _logical_child_spec(source_root / name, root) for name in ("references.jsonl", "candidates.jsonl", "rows.jsonl")},
    }
    atomic_json(source_root / "panel.json", panel)
    return {**panel, "panel_sha256": sha256_file(source_root / "panel.json")}


def build(config_path: Path, output_root: Path) -> dict[str, Any]:
    if output_root.exists():
        raise RuntimeError(f"create-once prescore root already exists: {output_root}")
    config = read_json(config_path)
    if config.get("schema_version") != PRESCORE_SCHEMA or config.get("status") != "draft_no_model_calls_authorized":
        raise RuntimeError("attempt-9 prescore config is not the no-model-calls draft")
    if config.get("model_calls_authorized") is not False or config.get("neural_training_authorized") is not False:
        raise RuntimeError("prescore must explicitly forbid model calls and training")
    verify_attempt7_retirement(RETIREMENT_PATH)
    for spec in config["lineage"].values():
        _verify_spec(spec)
    for source in config["sources"].values():
        for spec in source["files"]:
            _verify_spec(spec)
    for rejected in config["rejected_supplemental_candidates"].values():
        for spec in rejected["files"]:
            _verify_spec(spec)
    runtime_probe_path = validate_repo_relative(str(config["runtime"]["required_library_attestation"]))
    runtime_probe = read_json(runtime_probe_path)
    if runtime_probe.get("schema_version") != "atlas_rope_v5_attempt9_runtime_probe_v1" or runtime_probe.get("status") != "PASS_NO_WEIGHT_NO_FORWARD":
        raise RuntimeError("runtime probe is missing or invalid")
    if runtime_probe.get("model_weights_loaded") is not False or runtime_probe.get("neural_forward_run") is not False:
        raise RuntimeError("runtime probe crossed the no-weight/no-forward boundary")
    if (RUN_ROOT / "validation").exists() or (RUN_ROOT / "science").exists() or ATTEMPT7_ROOT.joinpath("numerical_qa/GUM").exists():
        raise RuntimeError("validation/science/attempt7-GUM root must be absent before prescore")

    from transformers import AutoTokenizer

    model = config["model"]
    tokenizer = AutoTokenizer.from_pretrained(str(model["name"]), revision=str(model["revision"]), local_files_only=True)
    science = _science_firewall()
    esl = _prior_esl_exposure(config)
    gum = _gum_legacy_exposure()
    gumreddit = _rejected_gumreddit_audit(config)
    prior = _prior_project_exposure()
    staging = output_root.with_name(f".{output_root.name}.{os.getpid()}.tmp")
    if staging.exists():
        raise RuntimeError(f"stale builder staging root: {staging}")
    staging.mkdir(parents=True)
    try:
        firewall_root = staging / "firewalls"
        firewall_root.mkdir()
        atomic_json(firewall_root / "final_v3_science.json", science)
        atomic_json(firewall_root / "prior_eslspok_exposure.json", esl)
        atomic_json(firewall_root / "legacy_gum_exposure.json", gum)
        atomic_json(firewall_root / "rejected_gumreddit_audit.json", gumreddit)
        atomic_json(firewall_root / "prior_project_exposure.json", prior)
        panels: dict[str, Any] = {}
        candidate_reports: dict[str, Any] = {}
        for source in ("EWT_calibration", "GUM_fresh_validation", "GENTLE_validation"):
            source_candidates, exclusions = _candidate_records(config, tokenizer, source, science, gum, prior)
            counts = Counter(row["length_bin"] for row in source_candidates)
            candidate_reports[source] = {**exclusions, "by_length_bin": {name: counts.get(name, 0) for name, _, _ in LENGTH_BINS}}
            panels[source] = _write_source_panel(staging, source, source_candidates, {}, candidate_reports[source])
        sentinel = _build_gum_sentinel(staging)
        # Independently reload and verify every source child and exact grid invariant.
        for source in panels:
            source_root = staging / source
            references = read_jsonl(source_root / "references.jsonl")
            candidates = read_jsonl(source_root / "candidates.jsonl")
            rows = read_jsonl(source_root / "rows.jsonl")
            validate_grid_units(references, candidates, rows, source=source)
            for name, spec in read_json(source_root / "panel.json")["children"].items():
                path = ROOT / str(spec["path"])
                # Child paths still point at the staging namespace during construction.
                path = source_root / name
                if sha256_file(path) != spec["sha256"] or path.stat().st_size != spec["bytes"]:
                    raise RuntimeError(f"source child failed independent verification: {source}/{name}")
        manifest = {
            "schema_version": "atlas_rope_v5_attempt9_prescore_manifest_v1",
            "status": "PASS_NO_MODEL_CALLS",
            "config": {"path": str(config_path.relative_to(ROOT)), "sha256": sha256_file(config_path)},
            "attempt7_retirement": {"path": str(RETIREMENT_PATH.relative_to(ROOT)), "sha256": sha256_file(RETIREMENT_PATH)},
            "runtime_probe": {"path": str(runtime_probe_path.relative_to(ROOT)), "sha256": sha256_file(runtime_probe_path)},
            "sources": {source: {"panel_path": f"{source}/panel.json", "panel_sha256": panels[source]["panel_sha256"]} for source in panels},
            "fresh_gum_sentinel": {"panel_path": "GUM_fresh_sentinel/panel.json", "panel_sha256": sentinel["panel_sha256"]},
            "firewalls": {name: _logical_child_spec(path, staging) for name, path in {
                "final_v3_science": firewall_root / "final_v3_science.json",
                "prior_eslspok_exposure": firewall_root / "prior_eslspok_exposure.json",
                "legacy_gum_exposure": firewall_root / "legacy_gum_exposure.json",
                "rejected_gumreddit_audit": firewall_root / "rejected_gumreddit_audit.json",
                "prior_project_exposure": firewall_root / "prior_project_exposure.json",
            }.items()},
            "candidate_reports": candidate_reports,
            "representation_scoring_run": False,
            "neural_inference_run": False,
            "neural_training_run": False,
            "model_weights_loaded": False,
        }
        atomic_json(staging / "manifest.json", manifest)
        # Rebase child paths are informational; all validation uses manifest-relative paths and hashes.
        os.replace(staging, output_root)
        parent_fd = os.open(output_root.parent, os.O_RDONLY | os.O_DIRECTORY)
        try:
            os.fsync(parent_fd)
        finally:
            os.close(parent_fd)
    except Exception:
        # Keep failed staging for audit; never silently redraw into a changed population.
        raise
    return read_json(output_root / "manifest.json")


def compare_rebuild(primary: Path, rebuilt: Path, report_path: Path) -> dict[str, Any]:
    left, right = recursive_inventory(primary), recursive_inventory(rebuilt)
    # Ignore only manifest paths whose embedded config-relative paths are identical; all bytes should match.
    status = "PASS" if left == right else "FAIL"
    report = {"schema_version": "atlas_rope_v5_attempt9_rebuild_check_v1", "status": status,
              "primary_root": str(primary.relative_to(ROOT)), "rebuilt_root": str(rebuilt.relative_to(ROOT)),
              "primary_inventory_sha256": sha256_bytes(json.dumps(left, sort_keys=True, separators=(",", ":")).encode()),
              "rebuilt_inventory_sha256": sha256_bytes(json.dumps(right, sort_keys=True, separators=(",", ":")).encode()),
              "mismatched_paths": sorted(set(left) ^ set(right) | {key for key in set(left) & set(right) if left[key] != right[key]})}
    atomic_json(report_path, report)
    if status != "PASS":
        raise RuntimeError(f"prescore rebuild differs: {report['mismatched_paths'][:10]}")
    return report


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, default=PRESCORE_PATH)
    parser.add_argument("--output-root", type=Path, default=DATA_ROOT)
    parser.add_argument("--compare-to", type=Path)
    parser.add_argument("--report", type=Path, default=ROOT / "reports/atlas_rope_v5/prescore_rebuild_check.json")
    args = parser.parse_args()
    config = args.config if args.config.is_absolute() else ROOT / args.config
    output = args.output_root if args.output_root.is_absolute() else ROOT / args.output_root
    result = build(config, output)
    if args.compare_to:
        compare = args.compare_to if args.compare_to.is_absolute() else ROOT / args.compare_to
        result = compare_rebuild(compare, output, args.report if args.report.is_absolute() else ROOT / args.report)
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
