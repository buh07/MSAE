#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
import statistics
from collections import defaultdict
from pathlib import Path
from typing import Any

SYNTAX_GATE_MEAN = 0.003
SYNTAX_GATE_MEDIAN = 0.0
SYNTAX_GATE_POSITIVE_COUNT = 3

TASK_TO_FAMILY = {
    "pos_ud_ewt": "syntax_pos",
    "deprel_ud_ewt": "syntax_dep",
    "ner_wnut17": "sem_wnut",
}


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Aggregate completed PCC Stage A0 summaries")
    p.add_argument("--run_root", type=str, required=True)
    return p.parse_args()


def mean(xs: list[float]) -> float:
    return float(sum(xs) / len(xs)) if xs else float("nan")


def median(xs: list[float]) -> float:
    return float(statistics.median(xs)) if xs else float("nan")


def write_tsv(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        return
    with open(path, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()), delimiter="\t")
        w.writeheader()
        w.writerows(rows)


def main() -> None:
    args = parse_args()
    run_root = Path(args.run_root)
    summary_paths = sorted(run_root.glob("outputs/*/pcc_stage_a0_summary.json"))
    if not summary_paths:
        raise SystemExit(f"No Stage A0 summaries found under {run_root}")

    per_task: dict[str, list[dict[str, Any]]] = defaultdict(list)
    per_family: dict[str, list[dict[str, Any]]] = defaultdict(list)
    run_rows: list[dict[str, Any]] = []

    for sp in summary_paths:
        data = json.load(open(sp, "r", encoding="utf-8"))
        output_id = sp.parent.name
        seed = int(data.get("seed", -1))
        checkpoint_path = str(data.get("checkpoint_path", ""))
        for task_name, task in data["tasks"].items():
            pos_priv = float(task["representations"]["pos_priv"]["primary_metric"])
            content_priv = float(task["representations"]["content_priv"]["primary_metric"])
            raw_metric = float(task["representations"]["raw"]["primary_metric"])
            joint_metric = float(task["representations"]["joint"]["primary_metric"])
            best_private = float(task["best_private_metric"])
            joint_gain = float(task["joint_gain"])
            content_margin = content_priv - pos_priv
            family = TASK_TO_FAMILY.get(task_name, "other")
            row = {
                "output_id": output_id,
                "seed": seed,
                "task": task_name,
                "family": family,
                "metric_name": task["metric_name"],
                "raw_metric": raw_metric,
                "pos_priv_metric": pos_priv,
                "content_priv_metric": content_priv,
                "best_private_metric": best_private,
                "joint_metric": joint_metric,
                "joint_gain": joint_gain,
                "content_margin": content_margin,
                "checkpoint_path": checkpoint_path,
                "summary_path": str(sp),
            }
            run_rows.append(row)
            per_task[task_name].append(row)
            per_family[family].append(row)

    agg_task_rows: list[dict[str, Any]] = []
    for task_name, rows in sorted(per_task.items()):
        gains = [float(r["joint_gain"]) for r in rows]
        raws = [float(r["raw_metric"]) for r in rows]
        bests = [float(r["best_private_metric"]) for r in rows]
        joints = [float(r["joint_metric"]) for r in rows]
        margins = [float(r["content_margin"]) for r in rows]
        family = rows[0]["family"]
        metric_name = rows[0]["metric_name"]
        positive_count = sum(1 for g in gains if g > 0.0)
        is_syntax = family.startswith("syntax_")
        is_content_private = all(float(r["content_priv_metric"]) > float(r["pos_priv_metric"]) for r in rows)
        syntax_gate_pass = (
            is_syntax
            and mean(gains) > SYNTAX_GATE_MEAN
            and median(gains) > SYNTAX_GATE_MEDIAN
            and positive_count >= SYNTAX_GATE_POSITIVE_COUNT
        )
        agg_task_rows.append(
            {
                "task": task_name,
                "family": family,
                "metric_name": metric_name,
                "n_runs": len(rows),
                "mean_joint_gain": mean(gains),
                "median_joint_gain": median(gains),
                "min_joint_gain": min(gains),
                "max_joint_gain": max(gains),
                "positive_count": positive_count,
                "mean_raw_metric": mean(raws),
                "mean_best_private_metric": mean(bests),
                "mean_joint_metric": mean(joints),
                "mean_content_minus_pos": mean(margins),
                "syntax_gate_pass": bool(syntax_gate_pass),
                "content_private_pass": bool(is_content_private),
            }
        )

    agg_family_rows: list[dict[str, Any]] = []
    for family, rows in sorted(per_family.items()):
        gains = [float(r["joint_gain"]) for r in rows]
        raws = [float(r["raw_metric"]) for r in rows]
        bests = [float(r["best_private_metric"]) for r in rows]
        joints = [float(r["joint_metric"]) for r in rows]
        margins = [float(r["content_margin"]) for r in rows]
        positive_count = sum(1 for g in gains if g > 0.0)
        agg_family_rows.append(
            {
                "family": family,
                "n_rows": len(rows),
                "n_unique_tasks": len(sorted({str(r['task']) for r in rows})),
                "mean_joint_gain": mean(gains),
                "median_joint_gain": median(gains),
                "min_joint_gain": min(gains),
                "max_joint_gain": max(gains),
                "positive_count": positive_count,
                "mean_raw_metric": mean(raws),
                "mean_best_private_metric": mean(bests),
                "mean_joint_metric": mean(joints),
                "mean_content_minus_pos": mean(margins),
            }
        )

    task_index = {r["task"]: r for r in agg_task_rows}
    pos_pass = bool(task_index["pos_ud_ewt"]["syntax_gate_pass"])
    dep_pass = bool(task_index["deprel_ud_ewt"]["syntax_gate_pass"])
    wnut_content_private = bool(task_index["ner_wnut17"]["content_private_pass"])
    proceed = pos_pass and dep_pass and wnut_content_private

    decision = {
        "stage": "pcc_stage_a0_aggregate",
        "run_root": str(run_root),
        "n_summaries": len(summary_paths),
        "thresholds": {
            "syntax_mean_joint_gain_gt": SYNTAX_GATE_MEAN,
            "syntax_median_joint_gain_gt": SYNTAX_GATE_MEDIAN,
            "syntax_positive_count_gte": SYNTAX_GATE_POSITIVE_COUNT,
            "semantics_content_private_all_runs": True,
        },
        "task_verdicts": {
            "pos_ud_ewt": {
                "stable_positive": pos_pass,
                "stats": task_index["pos_ud_ewt"],
            },
            "deprel_ud_ewt": {
                "stable_positive": dep_pass,
                "stats": task_index["deprel_ud_ewt"],
            },
            "ner_wnut17": {
                "content_private": wnut_content_private,
                "stats": task_index["ner_wnut17"],
            },
        },
        "conclusion": {
            "proceed_to_stage_a1": proceed,
            "summary": (
                "Proceed to Stage A1: POS and dependency are promising syntax families; "
                "WNUT NER remains content-private but not strongly crossover-enriched. "
                "Stage A1 should be syntax-heavy with replicated semantics sentinels."
                if proceed
                else "Do not proceed to Stage A1 under the current gate."
            ),
        },
    }

    write_tsv(run_root / "aggregate_task_metrics.tsv", agg_task_rows)
    write_tsv(run_root / "aggregate_family_summary.tsv", agg_family_rows)
    with open(run_root / "stage_a0_decision.json", "w", encoding="utf-8") as f:
        json.dump(decision, f, indent=2)
    md = [
        "# Stage A0 Decision",
        "",
        f"- Run root: `{run_root}`",
        f"- Summaries aggregated: `{len(summary_paths)}`",
        f"- POS stable-positive: `{pos_pass}`",
        f"- Deprel stable-positive: `{dep_pass}`",
        f"- WNUT content-private: `{wnut_content_private}`",
        f"- Proceed to Stage A1: `{proceed}`",
        "",
        "## Conclusion",
        decision["conclusion"]["summary"],
        "",
        "## Task Summary",
        "| task | mean_joint_gain | median_joint_gain | positive_count | content_private_pass | syntax_gate_pass |",
        "|---|---:|---:|---:|---|---|",
    ]
    for row in agg_task_rows:
        md.append(
            f"| {row['task']} | {row['mean_joint_gain']:.6f} | {row['median_joint_gain']:.6f} | {row['positive_count']} | {row['content_private_pass']} | {row['syntax_gate_pass']} |"
        )
    with open(run_root / "stage_a0_decision.md", "w", encoding="utf-8") as f:
        f.write("\n".join(md) + "\n")

    print(json.dumps({
        "run_root": str(run_root),
        "aggregate_task_metrics": str(run_root / 'aggregate_task_metrics.tsv'),
        "aggregate_family_summary": str(run_root / 'aggregate_family_summary.tsv'),
        "decision_json": str(run_root / 'stage_a0_decision.json'),
        "decision_md": str(run_root / 'stage_a0_decision.md'),
        "proceed_to_stage_a1": proceed,
    }, indent=2))


if __name__ == "__main__":
    main()
