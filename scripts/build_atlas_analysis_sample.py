#!/usr/bin/env python3
"""Freeze the base-sentence sample used for tractable atlas activation extraction."""

from __future__ import annotations

import hashlib
import json
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def digest(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


def main() -> None:
    config_path = ROOT / "configs/atlas/analysis_run.json"
    config = json.loads(config_path.read_text())
    manifest = {"schema_version": "atlas_v1_analysis_sample", "seed": config["seed"], "roles": {}}
    for role in ["discovery", "calibration", "C1", "C2"]:
        path = ROOT / f"data/atlas_v1/partitions/{role}.records.jsonl"
        records = [json.loads(line) for line in path.read_text().splitlines() if line]
        selected = []
        caps = config["base_sentence_caps_per_source_type"][role]
        for source_type in ["UD", "NER"]:
            rows = sorted((r for r in records if r["source_type"] == source_type),
                          key=lambda r: digest(f"{config['seed']}:{role}:{r['base_id']}"))
            cap = int(caps[source_type])
            selected.extend(rows if cap < 0 else rows[:cap])
        selected = sorted(selected, key=lambda r: r["base_id"])
        ids = [r["base_id"] for r in selected]
        manifest["roles"][role] = {"base_ids": ids, "base_count": len(ids),
                                     "source_counts": dict(Counter(r["source"] for r in selected)),
                                     "source_type_counts": dict(Counter(r["source_type"] for r in selected)),
                                     "base_id_digest": digest("\n".join(ids))}
    payload = json.dumps(manifest, indent=2, sort_keys=True) + "\n"
    output = ROOT / "configs/atlas/analysis_sample_manifest.json"
    output.write_text(payload)
    print(output, hashlib.sha256(payload.encode()).hexdigest())


if __name__ == "__main__":
    main()
