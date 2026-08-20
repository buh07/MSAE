#!/usr/bin/env python3
"""Build Attempt-11 fresh technical panels without loading model weights."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import sys
import tempfile
from collections import Counter
from pathlib import Path
from typing import Any, Mapping

sys.path.insert(0, str(Path(__file__).resolve().parent))

from transformers import AutoTokenizer

from atlas_discovery_v3_3 import parse_conllu, sentence_content_hash, token_layout
from atlas_rope_v6 import (
    LENGTH_BINS,
    deterministic_document_capped_selection,
    length_bin,
    make_grid_units,
    sequence_sha256,
    validate_grid_units,
)
from atlas_rope_v7 import (
    CONFIG_ROOT,
    DATA_ROOT,
    RAW_ROOT,
    ROOT,
    atomic_json,
    atomic_jsonl,
    read_json,
    read_jsonl,
    recursive_inventory,
    sha256_file,
    stable_sha,
)

SOURCE_CONFIG = CONFIG_ROOT / "sources.json"
MODEL_CONFIG = ROOT / "configs/atlas_rope_v5/prescore.json"


def _verify_spec(spec: Mapping[str, Any]) -> Path:
    raw = Path(str(spec["path"]))
    if raw.is_absolute() or ".." in raw.parts:
        raise RuntimeError("source path escapes repository")
    unresolved = ROOT / raw
    relative_parts = unresolved.relative_to(ROOT).parts
    cursor = ROOT
    if any((cursor := cursor / part).is_symlink() for part in relative_parts):
        raise RuntimeError(f"symlink forbidden in raw source lineage: {raw}")
    path = unresolved.resolve(strict=True)
    if not path.is_relative_to(ROOT) or not path.is_file() or path.is_symlink() or sha256_file(path) != str(spec["sha256"]):
        raise RuntimeError(f"raw source lineage drift: {raw}")
    return path


def _source_urls(path: Path) -> dict[str, str]:
    current: str | None = None
    output: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.startswith("# newdoc id") and "=" in line:
            current = line.split("=", 1)[1].strip()
        elif line.startswith("# meta::sourceURL") and "=" in line and current:
            output[current] = line.split("=", 1)[1].strip()
    return output


def _block_comments(block: str, required: tuple[str, ...]) -> dict[str, str]:
    values: dict[str, list[str]] = {key: [] for key in required}
    for line in block.splitlines():
        if not line.startswith("#") or "=" not in line:
            continue
        key, value = line[1:].split("=", 1)
        key = key.strip()
        if key in values:
            values[key].append(value.strip())
    output: dict[str, str] = {}
    for key, observed in values.items():
        if len(observed) != 1:
            raise RuntimeError(f"missing/duplicate {key} metadata")
        value = observed[0]
        if not value or any(character in value for character in ("\x00", "\r", "\n")):
            raise RuntimeError(f"empty/forbidden {key} metadata")
        output[key] = value
    return output


def _parse_source_files(paths: list[Path], panel: str, source_name: str) -> tuple[list[Any], dict[str, dict[str, Any]]]:
    if source_name != "CHILDES":
        output = []
        provenance: dict[str, dict[str, Any]] = {}
        for path in paths:
            parsed = parse_conllu(path, f"{panel}:{source_name}")
            raw_sha = sha256_file(path)
            blocks = [value for value in path.read_text(encoding="utf-8").split("\n\n") if value.strip()]
            by_sent: dict[str, tuple[int, str]] = {}
            for block_index, block in enumerate(blocks, 1):
                metadata = _block_comments(block, ("sent_id",))
                if metadata["sent_id"] in by_sent:
                    raise RuntimeError("duplicate sentence ID in raw blocks")
                by_sent[metadata["sent_id"]] = (block_index, hashlib.sha256(block.encode("utf-8")).hexdigest())
            for sentence in parsed:
                block_index, block_sha = by_sent[sentence.sent_id]
                provenance[sentence.sent_id] = {
                    "raw_path": str(path.relative_to(ROOT)), "raw_sha256": raw_sha,
                    "raw_block_index_one_based": block_index, "raw_block_sha256": block_sha,
                }
            output.extend(parsed)
        return output, provenance
    # CHILDES has no newdoc markers.  corpus_name + child_name identifies an
    # upstream participant-transcript group.  Inject one parser-only marker per
    # group without changing or replacing the hashed raw files.
    groups: dict[str, list[str]] = {}
    provenance: dict[str, dict[str, Any]] = {}
    canonical_by_group: dict[str, bytes] = {}
    for path in paths:
        raw_sha = sha256_file(path)
        for block_index, block in enumerate([value for value in path.read_text(encoding="utf-8").split("\n\n") if value.strip()], 1):
            comments = _block_comments(block, ("sent_id", "corpus_name", "child_name"))
            canonical = json.dumps([comments["corpus_name"], comments["child_name"]], ensure_ascii=False, separators=(",", ":")).encode("utf-8")
            group = "childes_group:" + hashlib.sha256(canonical).hexdigest()[:24]
            if group in canonical_by_group and canonical_by_group[group] != canonical:
                raise RuntimeError("distinct CHILDES tuples collide after group-ID truncation")
            canonical_by_group[group] = canonical
            sent_id = comments["sent_id"]
            if sent_id in provenance:
                raise RuntimeError("duplicate CHILDES sent_id across raw files")
            provenance[sent_id] = {
                "raw_path": str(path.relative_to(ROOT)), "raw_sha256": raw_sha,
                "raw_block_index_one_based": block_index,
                "raw_block_sha256": hashlib.sha256(block.encode("utf-8")).hexdigest(),
                "sent_id": sent_id, "corpus_name": comments["corpus_name"], "child_name": comments["child_name"],
                "canonical_group_tuple_sha256": hashlib.sha256(canonical).hexdigest(), "derived_group_id": group,
            }
            groups.setdefault(group, []).append(block)
    assembled: list[str] = []
    for group in sorted(groups, key=lambda value: value.encode("utf-8")):
        assembled.append(f"# newdoc id = {group}")
        assembled.extend(groups[group])
    with tempfile.NamedTemporaryFile("w", suffix=".conllu", encoding="utf-8", delete=False) as handle:
        handle.write("\n\n".join(assembled) + "\n")
        temporary = Path(handle.name)
    try:
        parsed = parse_conllu(temporary, f"{panel}:{source_name}")
        if any(provenance[sentence.sent_id]["derived_group_id"] != sentence.document_id for sentence in parsed):
            raise RuntimeError("CHILDES parser-only group lineage drift")
        return parsed, provenance
    finally:
        temporary.unlink(missing_ok=True)


def _prior_firewall(tokenizer: Any) -> dict[str, set[str]]:
    prior = read_json(ROOT / "data/atlas_rope_v5_attempt9/firewalls/prior_project_exposure.json")
    science = read_json(ROOT / "data/atlas_rope_v5_attempt9/firewalls/final_v3_science.json")
    output = {
        "documents": set(map(str, prior["document_ids"])) | set(map(str, science["documents"])),
        "sentences": set(map(str, prior["sentence_ids"])) | set(map(str, science["sentences"])),
        "source_urls": set(map(str, prior["source_urls"])),
        "sequences": set(map(str, prior["sequence_sha256"])) | set(map(str, science["sequence_sha256"])),
        "contents": set(map(str, prior["content_sha256"])) | set(map(str, science["content_sha256"])),
    }
    # GENTLE was intentionally excluded from the old freshness firewall.  It is
    # opened now, so incorporate its exact identities before selecting v7.
    for path in sorted((ROOT / "data/atlas_rope_v4_raw/UD_English-GENTLE").rglob("*.conllu")):
        urls = _source_urls(path)
        output["source_urls"].update(urls.values())
        for sentence in parse_conllu(path, "GENTLE_OPENED"):
            output["documents"].update((sentence.document_id, f"GENTLE:{sentence.document_id}"))
            output["sentences"].add(sentence.sent_id)
            output["contents"].add(sentence_content_hash(sentence))
            layout = token_layout(tokenizer, sentence, 128)
            if layout["complete"]:
                output["sequences"].add(sequence_sha256(layout["input_ids"]))
    return output


def _candidate_records(
    panel: str,
    source_name: str,
    source_spec: Mapping[str, Any],
    allowed_bins: set[str],
    tokenizer: Any,
    firewall: Mapping[str, set[str]],
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    parsed = []
    urls: dict[str, str] = {}
    files: list[dict[str, Any]] = []
    paths: list[Path] = []
    for spec in source_spec["files"]:
        path = _verify_spec(spec)
        paths.append(path)
        urls.update(_source_urls(path))
        files.append({"path": str(path.relative_to(ROOT)), "sha256": sha256_file(path)})
    parsed, source_lineage = _parse_source_files(paths, panel, source_name)
    seen_sentences: set[str] = set()
    candidates: list[dict[str, Any]] = []
    excluded: Counter[str] = Counter()
    for sentence in parsed:
        if sentence.sent_id in seen_sentences:
            raise RuntimeError(f"duplicate sentence ID: {panel}/{source_name}/{sentence.sent_id}")
        seen_sentences.add(sentence.sent_id)
        if not sentence.document_id:
            excluded["missing_document"] += 1
            continue
        if any(token.form == "_" for token in sentence.tokens):
            excluded["placeholder_form"] += 1
            continue
        layout = token_layout(tokenizer, sentence, 128)
        if not layout["complete"]:
            excluded["longer_than_128"] += 1
            continue
        ids = list(map(int, layout["input_ids"]))
        bin_name = length_bin(len(ids))
        if bin_name is None or bin_name not in allowed_bins:
            excluded["outside_allowed_bin"] += 1
            continue
        sequence = sequence_sha256(ids)
        content = sentence_content_hash(sentence)
        url = urls.get(sentence.document_id)
        document_candidates = {sentence.document_id, f"{source_name}:{sentence.document_id}", f"{panel}:{sentence.document_id}"}
        if document_candidates & firewall["documents"]:
            excluded["prior_document"] += 1
            continue
        if sentence.sent_id in firewall["sentences"]:
            excluded["prior_sentence"] += 1
            continue
        if url and url in firewall["source_urls"]:
            excluded["prior_source_url"] += 1
            continue
        if sequence in firewall["sequences"]:
            excluded["prior_sequence"] += 1
            continue
        if content in firewall["contents"]:
            excluded["prior_content"] += 1
            continue
        candidates.append({
            "source": f"{panel}:{source_name}",
            "document_id": f"{source_name}:{sentence.document_id}",
            "sent_id": f"{source_name}:{sentence.sent_id}",
            "length_bin": bin_name,
            "input_ids": ids,
            "sequence_sha256": sequence,
            "content_sha256": content,
            "source_url": url,
            "selection_key": stable_sha("atlas_rope_v7_attempt11", source_name, sentence.document_id, sentence.sent_id, sequence),
            "raw_lineage": source_lineage[sentence.sent_id],
        })
    candidates.sort(key=lambda row: (str(row["selection_key"]), str(row["sent_id"]).encode("utf-8")))
    return candidates, {
        "source": source_name,
        "revision": source_spec["revision"],
        "files": files,
        "raw_sentences": len(parsed),
        "retained_candidates": len(candidates),
        "exclusions": dict(sorted(excluded.items())),
    }


def _select(candidates: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    # The v6 selector's stable key is not the v7 frozen salt.  Preserve the v7
    # ordering by passing an already sorted list and selecting directly.
    selected: list[dict[str, Any]] = []
    report: dict[str, Any] = {}
    for name, _, _ in LENGTH_BINS:
        rows = [dict(row) for row in candidates if row["length_bin"] == name]
        rows.sort(key=lambda row: (str(row["selection_key"]), str(row["sent_id"]).encode("utf-8")))
        docs: Counter[str] = Counter()
        sequences: set[str] = set()
        retained: list[dict[str, Any]] = []
        for row in rows:
            document = str(row["document_id"])
            if docs[document] >= 2 or row["sequence_sha256"] in sequences:
                continue
            docs[document] += 1
            sequences.add(str(row["sequence_sha256"]))
            retained.append(row)
            if len(retained) == 20:
                break
        report[name] = {"candidates": len(rows), "retained": len(retained), "documents": len(docs), "max_per_document": max(docs.values(), default=0)}
        if len(retained) != 20 or len(docs) < 10:
            raise RuntimeError(f"panel cannot fill {name}: {report[name]}")
        selected.extend(retained)
    return selected, report


def _replace_namespace(value: Any) -> Any:
    if isinstance(value, str):
        return value.replace("atlas_rope_v6:", "atlas_rope_v7:")
    if isinstance(value, list):
        return [_replace_namespace(child) for child in value]
    if isinstance(value, dict):
        return {key: _replace_namespace(child) for key, child in value.items()}
    return value


def build(output_root: Path = DATA_ROOT) -> dict[str, Any]:
    config = read_json(SOURCE_CONFIG)
    model_config = read_json(MODEL_CONFIG)
    allowed_raw = {"UD_English-CHILDES", "UD_English-CTeTex", "UD_Czech-PDT"}
    observed_raw = {path.name for path in RAW_ROOT.iterdir()}
    if observed_raw != allowed_raw or any(not path.is_dir() or path.is_symlink() for path in RAW_ROOT.iterdir()):
        raise RuntimeError(f"Attempt-11 raw-root allowlist drift: {sorted(observed_raw)}")
    if "PUD" in SOURCE_CONFIG.read_text(encoding="utf-8"):
        raise RuntimeError("rejected PUD appears in validation source config")
    if output_root.exists():
        manifest = read_json(output_root / "manifest.json")
        if manifest.get("schema_version") != "atlas_rope_v7_attempt11_prescore_v1":
            raise RuntimeError("existing Attempt-11 data root identity drift")
        return manifest
    tokenizer = AutoTokenizer.from_pretrained(
        model_config["model"]["name"], revision=model_config["model"]["revision"], local_files_only=True
    )
    firewall = _prior_firewall(tokenizer)
    staging = Path(tempfile.mkdtemp(prefix=".atlas_rope_v7_build_", dir=str(output_root.parent)))
    try:
        panels: dict[str, Any] = {}
        for panel_name, panel_spec in config["panels"].items():
            all_candidates: list[dict[str, Any]] = []
            source_reports: dict[str, Any] = {}
            for source_name, source_spec in panel_spec["sources"].items():
                allowed = {name for name, source in panel_spec["bin_sources"].items() if source == source_name}
                rows, report = _candidate_records(panel_name, source_name, source_spec, allowed, tokenizer, firewall)
                all_candidates.extend(rows)
                source_reports[source_name] = report
            # Enforce exact source allocation before deterministic selection.
            for row in all_candidates:
                source_name = str(row["source"]).split(":", 1)[1]
                if panel_spec["bin_sources"][str(row["length_bin"])] != source_name:
                    raise RuntimeError("per-bin source allocation drift")
            selected, support = _select(all_candidates)
            references, candidates, row_manifest = make_grid_units(panel_name, selected)
            references = _replace_namespace(references)
            candidates = _replace_namespace(candidates)
            row_manifest = _replace_namespace(row_manifest)
            validate_grid_units(references, candidates, row_manifest, source=panel_name)
            base_by_sequence = {str(row["sequence_sha256"]): str(row["base_id"]) for row in references}
            selected_lineage = [
                {
                    "base_id": base_by_sequence[str(row["sequence_sha256"])],
                    "source": row["source"], "document_group": row["document_id"], "sent_id": row["sent_id"],
                    "length_bin": row["length_bin"], "sequence_sha256": row["sequence_sha256"],
                    "content_sha256": row["content_sha256"], "selection_key": row["selection_key"],
                    "raw_lineage": row["raw_lineage"],
                }
                for row in selected
            ]
            selected_lineage.sort(key=lambda row: str(row["base_id"]).encode("utf-8"))
            panel_root = staging / panel_name
            panel_root.mkdir()
            atomic_jsonl(panel_root / "references.jsonl", references)
            atomic_jsonl(panel_root / "candidates.jsonl", candidates)
            atomic_jsonl(panel_root / "rows.jsonl", row_manifest)
            atomic_jsonl(panel_root / "selected_bases.jsonl", selected_lineage)
            panel_manifest = {
                "schema_version": "atlas_rope_v7_attempt11_panel_v1",
                "status": "FROZEN_UNOPENED",
                "panel": panel_name,
                "source_allocation": panel_spec["bin_sources"],
                "source_reports": source_reports,
                "support": support,
                "logical_counts": {"reference_units": 100, "candidate_units": 600, "reference_rows": 200, "candidate_rows": 1200, "cells": 30},
                "children": {},
                "model_inference_performed": False,
                "neural_training_authorized": False,
            }
            for name in ("references.jsonl", "candidates.jsonl", "rows.jsonl", "selected_bases.jsonl"):
                path = panel_root / name
                panel_manifest["children"][name] = {"bytes": path.stat().st_size, "sha256": sha256_file(path)}
            atomic_json(panel_root / "panel.json", panel_manifest)
            panels[panel_name] = {"panel_sha256": sha256_file(panel_root / "panel.json"), "support": support, "source_reports": source_reports}
        manifest = {
            "schema_version": "atlas_rope_v7_attempt11_prescore_v1",
            "status": "FROZEN_UNOPENED",
            "source_config": {"path": str(SOURCE_CONFIG.relative_to(ROOT)), "sha256": sha256_file(SOURCE_CONFIG)},
            "model_config": {"path": str(MODEL_CONFIG.relative_to(ROOT)), "sha256": sha256_file(MODEL_CONFIG)},
            "panels": panels,
            "firewall_counts": {key: len(value) for key, value in firewall.items()},
            "tree_inventory_before_manifest": recursive_inventory(staging),
            "model_inference_performed": False,
            "neural_training_authorized": False,
        }
        atomic_json(staging / "manifest.json", manifest)
        os.replace(staging, output_root)
        return manifest
    except Exception:
        shutil.rmtree(staging, ignore_errors=True)
        raise


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-root", type=Path, default=DATA_ROOT)
    args = parser.parse_args()
    print(json.dumps(build(args.output_root), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
