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
    p = argparse.ArgumentParser(description="Aggregate Stage B curated contrast audits")
    p.add_argument("--run_root", required=True)
    p.add_argument("--a1c_run_root", required=True)
    p.add_argument("--b_light_run_root", required=True)
    return p.parse_args()


def median(xs: list[float]) -> float:
    return float(statistics.median(xs)) if xs else float("nan")


def main() -> None:
    args = parse_args()
    run_root = Path(args.run_root)
    summary_paths = sorted(run_root.glob("outputs/*/pcc_stage_b_contrasts_summary.json"))
    if not summary_paths:
        raise SystemExit(f"No contrast summaries found under {run_root}")

    summaries = [json.loads(Path(p).read_text()) for p in summary_paths]
    family_rows = []
    family_grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    sensitivity_grouped: dict[str, dict[str, float]] = defaultdict(dict)

    for summary in summaries:
        checkpoint_name = Path(summary["checkpoint_path"]).parent.parent.name
        seed = int(summary["seed"])
        lam = "inc0" if checkpoint_name.endswith("inc0") else "inc1e2"
        run_id = f"seed{seed}_{lam}"
        for family, row in summary["families"].items():
            rec = {
                "run_id": run_id,
                "checkpoint_name": checkpoint_name,
                "seed": seed,
                "lambda_regime": lam,
                **row,
            }
            family_rows.append(rec)
            family_grouped[family].append(rec)
            if seed == 42:
                sensitivity_grouped[family][lam] = float(row["mean_joint_minus_content"] if row["contrast_type"] == "syntax" else row["mean_content_minus_pos"])

    agg_rows = []
    syntax_pass_count = 0
    semantic_pass_count = 0
    for family, rows in sorted(family_grouped.items()):
        contrast_type = rows[0]["contrast_type"]
        pass_vals = [bool(r["family_pass"]) for r in rows]
        if contrast_type == "syntax":
            key = "mean_joint_minus_content"
        else:
            key = "mean_content_minus_pos"
        vals = [float(r[key]) for r in rows]
        rec = {
            "family": family,
            "contrast_type": contrast_type,
            "n_runs": len(rows),
            "mean_signal": float(sum(vals) / len(vals)),
            "median_signal": median(vals),
            "positive_count": int(sum(1 for v in vals if v > 0)),
            "pass_count": int(sum(pass_vals)),
            "family_pass_all_runs": bool(all(pass_vals)),
        }
        if rec["family_pass_all_runs"]:
            if contrast_type == "syntax":
                syntax_pass_count += 1
            else:
                semantic_pass_count += 1
        agg_rows.append(rec)

    sens_rows = []
    for family, vals in sorted(sensitivity_grouped.items()):
        if "inc0" in vals and "inc1e2" in vals:
            sens_rows.append({
                "family": family,
                "g7_minus_g4_signal": float(vals["inc0"] - vals["inc1e2"]),
            })

    proceed_to_stage_c = syntax_pass_count >= 3 and semantic_pass_count >= 3
    decision = {
        "stage": "pcc_stage_b_contrasts",
        "run_root": str(run_root),
        "a1c_run_root": str(args.a1c_run_root),
        "b_light_run_root": str(args.b_light_run_root),
        "n_summaries": len(summaries),
        "syntax_family_pass_all_runs_count": syntax_pass_count,
        "semantic_family_pass_all_runs_count": semantic_pass_count,
        "proceed_to_stage_c": proceed_to_stage_c,
        "note": "Proceed only if multiple syntax and semantic contrast families show stable directional asymmetry across the checkpoint set.",
    }

    lines = [
        "# PCC Stage B Curated Contrast Audit",
        "",
        f"Run root: `{run_root}`",
        f"A1c reference root: `{args.a1c_run_root}`",
        f"Stage B-light reference root: `{args.b_light_run_root}`",
        "",
        "## Family Signals",
    ]
    for row in agg_rows:
        lines.append(
            f"- `{row['family']}` ({row['contrast_type']}): mean signal `{row['mean_signal']:.4f}`, median `{row['median_signal']:.4f}`, pass-all-runs `{row['family_pass_all_runs']}`"
        )
    lines.extend([
        "",
        "## Matched-Seed `g7 - g4` Sensitivity",
    ])
    for row in sens_rows:
        lines.append(f"- `{row['family']}`: `{row['g7_minus_g4_signal']:.4f}`")
    lines.extend([
        "",
        "## Gate",
        f"- Syntax families passing in all runs: `{syntax_pass_count}`",
        f"- Semantic families passing in all runs: `{semantic_pass_count}`",
        f"- Proceed to Stage C: `{proceed_to_stage_c}`",
    ])

    write_tsv(run_root / "aggregate_family_metrics.tsv", agg_rows)
    write_tsv(run_root / "regularizer_sensitivity_family.tsv", sens_rows)
    with open(run_root / "stage_b_contrasts_decision.json", "w", encoding="utf-8") as f:
        json.dump(decision, f, indent=2)
    with open(run_root / "stage_b_contrasts_decision.md", "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    print(json.dumps({
        "run_root": str(run_root),
        "aggregate_family_metrics": str(run_root / "aggregate_family_metrics.tsv"),
        "regularizer_sensitivity_family": str(run_root / "regularizer_sensitivity_family.tsv"),
        "decision_json": str(run_root / "stage_b_contrasts_decision.json"),
        "decision_md": str(run_root / "stage_b_contrasts_decision.md"),
        "proceed_to_stage_c": proceed_to_stage_c,
    }, indent=2))


if __name__ == "__main__":
    main()
