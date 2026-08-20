#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import statistics
from collections import defaultdict
from pathlib import Path
from typing import Any

from pcc_stage_a1_audit import write_tsv


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Aggregate Stage B-light PCC control audits")
    p.add_argument("--run_root", type=str, required=True)
    p.add_argument("--a1c_run_root", type=str, required=True)
    return p.parse_args()


def median(values: list[float]) -> float:
    return float(statistics.median(values)) if values else float("nan")


def main() -> None:
    args = parse_args()
    run_root = Path(args.run_root)
    summary_paths = sorted(run_root.glob("outputs/*/pcc_stage_b_light_summary.json"))
    if not summary_paths:
        raise SystemExit(f"No Stage B-light summaries found under {run_root}")

    summaries = []
    for path in summary_paths:
        with open(path, "r", encoding="utf-8") as f:
            summaries.append(json.load(f))

    task_rows: list[dict[str, Any]] = []
    grouped: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    seed42_task_map: dict[tuple[str, str], dict[str, float]] = defaultdict(dict)

    for summary in summaries:
        checkpoint_name = Path(summary["checkpoint_path"]).parent.parent.name
        seed = int(summary["seed"])
        lam = "inc0" if checkpoint_name.endswith("inc0") else "inc1e2"
        run_id = f"seed{seed}_{lam}"
        for task_name, task in summary["tasks"].items():
            row = {
                "run_id": run_id,
                "checkpoint_name": checkpoint_name,
                "seed": seed,
                "lambda_regime": lam,
                "task": task_name,
                "family": task["family"],
                "base_family": task["base_family"],
                "control_type": task["control_type"],
                "metric_name": task["metric_name"],
                "best_private_metric": float(task["best_private_metric"]),
                "joint_gain": float(task["joint_gain"]),
                "resid_gain": float(task["resid_gain"]),
                "content_margin": float(task["content_margin"]),
                "raw_gap": float(task["raw_gap"]),
                "n_train": int(task["n_train"]),
                "n_eval": int(task["n_eval"]),
            }
            task_rows.append(row)
            grouped[(task["base_family"], task["control_type"])].append(row)
            if seed == 42:
                seed42_task_map[(task_name, task["control_type"])][lam] = float(task["joint_gain"])

    agg_rows: list[dict[str, Any]] = []
    control_summary: dict[str, dict[str, Any]] = defaultdict(dict)
    for (base_family, control_type), rows in sorted(grouped.items()):
        gains = [float(r["joint_gain"]) for r in rows]
        resids = [float(r["resid_gain"]) for r in rows]
        margins = [float(r["content_margin"]) for r in rows]
        raw_gaps = [float(r["raw_gap"]) for r in rows]
        agg = {
            "base_family": base_family,
            "control_type": control_type,
            "n_runs": len(rows),
            "mean_joint_gain": float(sum(gains) / len(gains)),
            "median_joint_gain": median(gains),
            "positive_count": int(sum(1 for g in gains if g > 0)),
            "mean_resid_gain": float(sum(resids) / len(resids)),
            "mean_content_margin": float(sum(margins) / len(margins)),
            "mean_raw_gap": float(sum(raw_gaps) / len(raw_gaps)),
        }
        agg_rows.append(agg)
        control_summary[base_family][control_type] = agg

    sensitivity_rows: list[dict[str, Any]] = []
    sensitivity_by_base: dict[str, list[float]] = defaultdict(list)
    for (task_name, control_type), vals in sorted(seed42_task_map.items()):
        if "inc0" in vals and "inc1e2" in vals:
            delta = float(vals["inc0"] - vals["inc1e2"])
            base_family = next(r["base_family"] for r in task_rows if r["task"] == task_name and r["control_type"] == control_type)
            row = {
                "task": task_name,
                "base_family": base_family,
                "control_type": control_type,
                "g7_joint_gain": float(vals["inc0"]),
                "g4_joint_gain": float(vals["inc1e2"]),
                "g7_minus_g4_joint_gain": delta,
            }
            sensitivity_rows.append(row)
            sensitivity_by_base[base_family].append(delta)

    sensitivity_family_rows = []
    for base_family, deltas in sorted(sensitivity_by_base.items()):
        sensitivity_family_rows.append({
            "base_family": base_family,
            "n_entries": len(deltas),
            "mean_g7_minus_g4_joint_gain": float(sum(deltas) / len(deltas)),
            "median_g7_minus_g4_joint_gain": median(deltas),
            "positive_count": int(sum(1 for d in deltas if d > 0)),
        })

    def family_signal_text(base_family: str) -> str:
        info = control_summary.get(base_family, {})
        full = info.get("full")
        token = info.get("tokenctrl")
        pos = info.get("posctrl")
        if full is None:
            return f"- `{base_family}`: no full-control result recorded."
        parts = [f"full={full['mean_joint_gain']:.4f}"]
        if token is not None:
            parts.append(f"token={token['mean_joint_gain']:.4f}")
        if pos is not None:
            parts.append(f"pos={pos['mean_joint_gain']:.4f}")
        return f"- `{base_family}` mean joint gains: " + ", ".join(parts)

    syntax_families = ["syntax_pos", "syntax_dep_coarse", "syntax_dep_head_dir", "syntax_morph"]
    sem_families = ["sem_wnut17_typeonly", "sem_fewnerd_coarse_binary", "sem_wikineural_en_binary"]

    memo_lines = [
        "# PCC Stage B-light Control Audit",
        "",
        f"Run root: `{run_root}`",
        f"A1c reference root: `{args.a1c_run_root}`",
        "",
        "## Headline",
        "- This audit stays on the same `g4/g5/g6/g7` checkpoints and adds matched-token controls, coarse matched-position controls, residual-vs-joint summaries, and matched-seed `g4` vs `g7` regularizer sensitivity.",
        "- It is analysis-only and does not launch new PCC branch training.",
        "",
        "## Syntax Families",
    ]
    memo_lines.extend(family_signal_text(fam) for fam in syntax_families)
    memo_lines.extend([
        "",
        "## Semantic Families",
    ])
    memo_lines.extend(family_signal_text(fam) for fam in sem_families)
    memo_lines.extend([
        "",
        "## Matched-Seed Regularizer Sensitivity (`g7 - g4` joint gain)",
    ])
    for row in sensitivity_family_rows:
        memo_lines.append(
            f"- `{row['base_family']}`: mean delta `{row['mean_g7_minus_g4_joint_gain']:.4f}`, median `{row['median_g7_minus_g4_joint_gain']:.4f}`, positive `{row['positive_count']}/{row['n_entries']}`"
        )
    memo_lines.extend([
        "",
        "## Residual-vs-Joint Quick Read",
        "- Positive `mean_resid_gain` suggests useful information still sits outside the private-branch joint representation.",
        "- Negative `mean_resid_gain` suggests the additive residual is weaker than the best private branch for that family/control.",
        "",
        "## Notes",
        "- This is a Stage B-light control pass, not a controlled contrast-set pack yet.",
        "- If these controls preserve the amended A1c signal in syntax while keeping the semantics families content-private, that strengthens the case for a later contrast-set phase before any model-side PCC training.",
    ])

    decision = {
        "stage": "pcc_stage_b_light_controls",
        "run_root": str(run_root),
        "a1c_run_root": str(args.a1c_run_root),
        "n_summaries": len(summaries),
        "control_summary": control_summary,
        "matched_seed_g7_vs_g4": sensitivity_family_rows,
        "note": "Stage B-light is a control audit only. It is intended to sharpen interpretation before any contrast-set or model-side PCC work.",
    }

    write_tsv(run_root / "aggregate_task_metrics.tsv", task_rows)
    write_tsv(run_root / "aggregate_family_metrics.tsv", agg_rows)
    write_tsv(run_root / "regularizer_sensitivity_task.tsv", sensitivity_rows)
    write_tsv(run_root / "regularizer_sensitivity_family.tsv", sensitivity_family_rows)
    with open(run_root / "stage_b_light_controls.json", "w", encoding="utf-8") as f:
        json.dump(decision, f, indent=2)
    with open(run_root / "stage_b_light_controls.md", "w", encoding="utf-8") as f:
        f.write("\n".join(memo_lines) + "\n")

    print(json.dumps({
        "run_root": str(run_root),
        "aggregate_task_metrics": str(run_root / "aggregate_task_metrics.tsv"),
        "aggregate_family_metrics": str(run_root / "aggregate_family_metrics.tsv"),
        "regularizer_sensitivity_task": str(run_root / "regularizer_sensitivity_task.tsv"),
        "regularizer_sensitivity_family": str(run_root / "regularizer_sensitivity_family.tsv"),
        "memo": str(run_root / "stage_b_light_controls.md"),
    }, indent=2))


if __name__ == "__main__":
    main()
