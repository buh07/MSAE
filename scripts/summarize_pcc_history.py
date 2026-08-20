#!/usr/bin/env python3
"""Build a compact, auditable PCC history from frozen structured artifacts."""

from __future__ import annotations

import hashlib
import json
from collections import defaultdict
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def rel(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


def load(path: Path) -> Any:
    return json.loads(path.read_text())


def aggregate_summaries(run: str) -> dict[str, Any]:
    paths = sorted((ROOT / "pilot_runs" / run / "outputs").glob("*/*.json"))
    tasks: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for path in paths:
        for name, row in load(path).get("tasks", {}).items():
            tasks[name].append(row)
    compact: dict[str, Any] = {}
    for name, rows in sorted(tasks.items()):
        compact[name] = {
            "family": rows[0].get("base_family", rows[0].get("family")),
            "control_type": rows[0].get("control_type", "none"),
            "n_checkpoints": len(rows),
            "mean_joint_gain": sum(float(r["joint_gain"]) for r in rows) / len(rows),
            "positive_count": sum(float(r["joint_gain"]) > 0 for r in rows),
            "mean_content_margin": sum(float(r["content_margin"]) for r in rows) / len(rows),
            "mean_raw_gap": sum(float(r["raw_gap"]) for r in rows) / len(rows),
        }
    return {
        "source_files": [{"path": rel(p), "sha256": sha256(p)} for p in paths],
        "tasks": compact,
    }


def main() -> None:
    decisions = [
        "20260604_184924_pcc_stage_a0/stage_a0_decision.json",
        "20260605_013756_pcc_stage_a1/stage_a1_decision.json",
        "20260605_034815_pcc_stage_a1c/amendment_decision.json",
        "20260605_034815_pcc_stage_a1c/stage_a1r_decision.json",
        "20260605_111613_pcc_stage_b_contrasts/stage_b_contrasts_decision.json",
    ]
    decision_rows = []
    for item in decisions:
        path = ROOT / "pilot_runs" / item
        decision_rows.append({"path": rel(path), "sha256": sha256(path), "payload": load(path)})
    result = {
        "schema_version": "pcc_historical_synthesis_v1",
        "evidence_class": "frozen_historical_and_diagnostic",
        "decisions": decision_rows,
        "a1b_diagnostic": aggregate_summaries("20260605_030600_pcc_stage_a1b"),
        "a1c_confirmation": aggregate_summaries("20260605_034815_pcc_stage_a1c"),
        "b_light_controls": aggregate_summaries("20260605_040323_pcc_stage_b_light_controls"),
    }
    output = ROOT / "reports/pcc_historical_synthesis.json"
    output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(output)


if __name__ == "__main__":
    main()
