#!/usr/bin/env python3
"""Materialize exact prescore task-row IDs for every atlas analysis role."""

from __future__ import annotations

import hashlib
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DROP = "__DROP__"
TASKS = ["abs_pos_16", "abs_pos_8", "relative_quartile", "head_signed_distance", "dependency_depth",
         "boundary_state", "token_identity_256", "lemma_identity_256", "ner_coarse"]


def canonical(row: dict[str, Any]) -> bytes:
    return (json.dumps(row, sort_keys=True, separators=(",", ":")) + "\n").encode()


def select(rows: list[dict[str, Any]], eligible: list[str], cap: int, seed: int, task: str) -> list[dict[str, Any]]:
    by_class: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        if row["label"] in eligible:
            by_class[row["label"]].append(row)
    for label in eligible:
        by_class[label].sort(key=lambda row: hashlib.sha256(f"{seed}:{task}:{row['row_id']}".encode()).hexdigest())
    ceiling = max(1, cap // len(eligible))
    chosen, remainder = [], []
    for label in eligible:
        chosen.extend(by_class[label][:ceiling])
        remainder.extend(by_class[label][ceiling:])
    remainder.sort(key=lambda row: hashlib.sha256(f"remainder:{seed}:{task}:{row['row_id']}".encode()).hexdigest())
    chosen.extend(remainder[:max(0, cap - len(chosen))])
    return sorted(chosen, key=lambda row: row["row_id"])


def main() -> None:
    config = json.loads((ROOT / "configs/atlas/analysis_run.json").read_text())
    sample = json.loads((ROOT / "configs/atlas/analysis_sample_manifest.json").read_text())
    eligibility = json.loads((ROOT / "reports/atlas_label_counts.json").read_text())["primary_class_eligibility"]
    output = ROOT / "data/atlas_v1/analysis_rows"
    output.mkdir(parents=True, exist_ok=True)
    manifest = {"schema_version": "atlas_v1_task_rows", "seed": config["seed"], "roles": {}}
    for role in ["discovery", "calibration", "C1", "C2"]:
        selected_bases = set(sample["roles"][role]["base_ids"])
        records = [json.loads(line) for line in (ROOT / f"data/atlas_v1/partitions/{role}.records.jsonl").read_text().splitlines()]
        record_map = {row["base_id"]: row for row in records if row["base_id"] in selected_bases}
        units = [json.loads(line) for line in (ROOT / f"data/atlas_v1/partitions/{role}.units.jsonl").read_text().splitlines()]
        units = [unit for unit in units if unit["base_id"] in selected_bases]
        candidates: dict[str, list[dict[str, Any]]] = {task: [] for task in TASKS}
        for unit in units:
            record = record_map[unit["base_id"]]
            shared = {"base_id": unit["base_id"], "document_group": record["document_group"],
                      "source_type": record["source_type"], "offset": unit["offset"]}
            for task in ["abs_pos_16", "abs_pos_8"]:
                for token_index, label in enumerate(unit["absolute_labels"][task]):
                    candidates[task].append({"row_id": f"{unit['variant_id']}:{token_index}", "label": label, **shared})
            for first in unit["first_subword_rows"]:
                word = int(first["word_index"])
                token_index = int(first["model_token_index"])
                for task in TASKS[2:]:
                    label = record["labels"][task][word]
                    if label != DROP:
                        candidates[task].append({"row_id": f"{unit['variant_id']}:{token_index}", "label": label, **shared})
        manifest["roles"][role] = {}
        for task in TASKS:
            rows = select(candidates[task], eligibility[task]["eligible_labels"], int(config["task_row_caps"][role]),
                          int(config["seed"]), task)
            path = output / f"{role}.{task}.jsonl"
            h = hashlib.sha256()
            with path.open("wb") as f:
                for row in rows:
                    payload = canonical(row); f.write(payload); h.update(payload)
            manifest["roles"][role][task] = {"path": path.relative_to(ROOT).as_posix(), "sha256": h.hexdigest(),
                                                     "rows": len(rows), "classes": dict(sorted(Counter(r["label"] for r in rows).items())),
                                                     "groups": len({r["document_group"] for r in rows})}
    payload = json.dumps(manifest, indent=2, sort_keys=True) + "\n"
    path = ROOT / "configs/atlas/task_row_manifest.json"
    path.write_text(payload)
    print(path, hashlib.sha256(payload.encode()).hexdigest())


if __name__ == "__main__":
    main()
