#!/usr/bin/env python3
"""Verify frozen atlas data hashes, firewalls, and pre-score label support."""

from __future__ import annotations

import hashlib
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any

from transformers import AutoTokenizer


ROOT = Path(__file__).resolve().parents[1]
DROP = "__DROP__"


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text().splitlines() if line]


def main() -> int:
    frozen = json.loads((ROOT / "configs/atlas/partition_hashes.json").read_text())
    failures: list[str] = []
    for rel, expected in frozen["files"].items():
        path = ROOT / rel
        if not path.exists():
            failures.append(f"missing:{rel}")
            continue
        actual = hashlib.sha256(path.read_bytes()).hexdigest()
        if actual != expected["sha256"]:
            failures.append(f"hash:{rel}")
        if sum(1 for _ in path.open("rb")) != int(expected["rows"]):
            failures.append(f"rows:{rel}")

    records, units = {}, {}
    for role in ["discovery", "calibration", "C1", "C2"]:
        records[role] = load_jsonl(ROOT / f"data/atlas_v1/partitions/{role}.records.jsonl")
        units[role] = load_jsonl(ROOT / f"data/atlas_v1/partitions/{role}.units.jsonl")
    source_config = json.loads((ROOT / "configs/atlas/data_sources.json").read_text())
    tokenizer = AutoTokenizer.from_pretrained(source_config["model"]["name"], revision=source_config["model"]["revision"], use_fast=True)
    for role in records:
        by_id = {record["base_id"]: record for record in records[role]}
        for unit in units[role]:
            if len(unit["input_ids"]) < int(source_config["packing"]["max_length"]):
                continue
            record = by_id[unit["base_id"]]
            offset = int(unit["offset"])
            packed = [unit["prefix_word"]] * offset + record["words"]
            full = tokenizer(packed, is_split_into_words=True, add_special_tokens=False, truncation=False)
            spans: dict[int, list[int]] = {}
            for index, word_id in enumerate(full.word_ids()):
                if word_id is not None:
                    spans.setdefault(int(word_id), []).append(index)
            expected = {word_id - offset for word_id, positions in spans.items()
                        if word_id >= offset and positions[-1] < int(source_config["packing"]["max_length"])}
            observed = {int(row["word_index"]) for row in unit["first_subword_rows"]}
            if observed != expected:
                failures.append(f"partial_tail_word_row:{role}:{unit['variant_id']}")
    for left_index, left in enumerate(records):
        for right in list(records)[left_index + 1:]:
            for key in ["base_id", "content_hash", "document_group"]:
                overlap = {x[key] for x in records[left]} & {x[key] for x in records[right]}
                if overlap:
                    failures.append(f"overlap:{key}:{left}:{right}:{len(overlap)}")
    if (ROOT / ".atlas_final_unlock").exists():
        failures.append("final_unlock_present")

    transform_qa: dict[str, Any] = {}
    for role in ["discovery", "calibration", "C1", "C2"]:
        rows = load_jsonl(ROOT / f"data/atlas_v1/transforms/{role}.jsonl")
        record_by_id = {row["base_id"]: row for row in records[role]}
        visible = {(unit["base_id"], int(unit["offset"])): {int(item["word_index"]) for item in unit["first_subword_rows"]}
                   for unit in units[role] if int(unit["offset"]) in {0, 32}}
        ids = [row["transform_id"] for row in rows]
        if len(ids) != len(set(ids)):
            failures.append(f"transform_duplicate_id:{role}")
        role_qa = {}
        for family in ["position_shift", "lexical_entity_substitution", "structural_active_passive", "punctuation_format"]:
            family_rows = [row for row in rows if row["family"] == family]
            group_counts = Counter(row.get("template_group") for row in family_rows)
            if len(family_rows) != 32 or sorted(group_counts.values()) != [8, 8, 8, 8]:
                failures.append(f"transform_family_or_groups:{role}:{family}")
            if any(row.get("automatic_invariant_check") is not True for row in family_rows):
                failures.append(f"transform_invariant:{role}:{family}")
            if family == "lexical_entity_substitution":
                for row in family_rows:
                    source_encoding = tokenizer(row["source_words"], is_split_into_words=True, add_special_tokens=False)
                    target_encoding = tokenizer(row["target_words"], is_split_into_words=True, add_special_tokens=False)
                    exact_alignment = source_encoding.word_ids() == target_encoding.word_ids()
                    if bool(row.get("token_aligned")) != exact_alignment:
                        failures.append(f"transform_alignment_flag:{role}:{row['transform_id']}")
            if family == "position_shift":
                for row in family_rows:
                    record = record_by_id[row["base_id"]]
                    required = set(range(len(record["words"])))
                    if (visible.get((row["base_id"], int(row["source_offset"]))) != required
                            or visible.get((row["base_id"], int(row["target_offset"]))) != required):
                        failures.append(f"transform_position_visibility:{role}:{row['transform_id']}")
            pairs = {
                (tuple(row.get("source_words", [])), tuple(row.get("target_words", [])),
                 row.get("base_id"), row.get("source_offset"), row.get("target_offset"))
                for row in family_rows
            }
            if len(pairs) != 32:
                failures.append(f"transform_repeated_pair:{role}:{family}")
            role_qa[family] = {"rows": len(family_rows), "template_groups": dict(sorted(group_counts.items())),
                               "unique_content_pairs": len(pairs), "invariant_failures": sum(row.get("automatic_invariant_check") is not True for row in family_rows)}
        transform_qa[role] = role_qa

    tasks = ["relative_quartile", "head_signed_distance", "dependency_depth", "boundary_state",
             "token_identity_256", "lemma_identity_256", "ner_coarse", "upos", "deprel_coarse", "number",
             "capitalization", "word_length", "frequency_bin", "source_type"]
    counts: dict[str, Any] = {}
    for role, rows in records.items():
        counts[role] = {}
        for task in tasks:
            counter: Counter[str] = Counter()
            for row in rows:
                counter.update(x for x in row["labels"][task] if x != DROP)
            counts[role][task] = dict(sorted(counter.items()))
        for task in ["abs_pos_16", "abs_pos_8"]:
            counter = Counter()
            for row in units[role]:
                counter.update(row["absolute_labels"][task])
            counts[role][task] = dict(sorted(counter.items(), key=lambda x: int(x[0])))

    primary_min = {"abs_pos_16": 100, "abs_pos_8": 100, "relative_quartile": 100,
                   "head_signed_distance": 100, "dependency_depth": 100, "boundary_state": 100,
                   "token_identity_256": 50, "lemma_identity_256": 50, "ner_coarse": 100}
    eligibility = {}
    for task, minimum in primary_min.items():
        common = set.intersection(*(set(counts[role][task]) for role in ["discovery", "calibration", "C1", "C2"]))
        eligible = sorted(label for label in common if all(counts[role][task][label] >= minimum for role in ["discovery", "calibration", "C1", "C2"]))
        eligibility[task] = {"minimum_per_class": minimum, "eligible_labels": eligible,
                             "support_roles": ["discovery", "calibration", "C1", "C2"],
                             "n_eligible_labels": len(eligible), "pre_score_eligible": len(eligible) >= 2}
        if len(eligible) < 2:
            failures.append(f"primary_class_support:{task}")

    result = {"schema_version": "atlas_v1_label_counts", "counts": counts, "transform_qa": transform_qa,
              "primary_class_eligibility": eligibility, "failures": failures, "passed": not failures}
    (ROOT / "reports/atlas_label_counts.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"passed": not failures, "failures": failures, "primary": eligibility}, indent=2))
    return bool(failures)


if __name__ == "__main__":
    sys.exit(main())
