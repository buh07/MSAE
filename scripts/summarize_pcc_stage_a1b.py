#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
import statistics
from collections import defaultdict
from pathlib import Path
from typing import Any

SYNTAX_FAMILIES = ["syntax_pos", "syntax_dep_coarse", "syntax_morph"]
EXPLORATORY_SYNTAX_FAMILIES = ["syntax_dep_head_dir"]
TYPEONLY_SEMANTIC_FAMILIES = ["sem_wnut17_typeonly", "sem_fewnerd_coarse_typeonly", "sem_wikineural_en_typeonly"]
BINARY_SEMANTIC_FAMILIES = ["sem_wnut17_binary", "sem_fewnerd_coarse_binary", "sem_wikineural_en_binary"]
SYNTAX_MEAN_GATE = 0.003
SYNTAX_MEDIAN_GATE = 0.0
SYNTAX_POSITIVE_GATE = 3
SEMANTIC_MAX_MEAN_JOINT_GAIN = 0.005


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Aggregate completed PCC Stage A1b summaries")
    p.add_argument("--run_root", type=str, required=True)
    p.add_argument("--baseline_a1_run_root", type=str, default="")
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


def family_pass(
    *,
    family_name: str,
    mean_joint: float,
    median_joint: float,
    positive_count: int,
    content_private_all_runs: bool,
) -> tuple[bool, bool]:
    syntax_pass = (
        family_name in SYNTAX_FAMILIES
        and mean_joint > SYNTAX_MEAN_GATE
        and median_joint > SYNTAX_MEDIAN_GATE
        and positive_count >= SYNTAX_POSITIVE_GATE
    )
    semantic_pass = (
        family_name in TYPEONLY_SEMANTIC_FAMILIES + BINARY_SEMANTIC_FAMILIES
        and content_private_all_runs
        and mean_joint < SEMANTIC_MAX_MEAN_JOINT_GAIN
    )
    return syntax_pass, semantic_pass


def load_baseline_note(path_str: str) -> dict[str, Any]:
    if not path_str:
        return {}
    path = Path(path_str) / "stage_a1_decision.json"
    if not path.exists():
        return {}
    return json.loads(path.read_text())


def main() -> None:
    args = parse_args()
    run_root = Path(args.run_root)
    summary_paths = sorted(run_root.glob("outputs/*/pcc_stage_a1b_summary.json"))
    if not summary_paths:
        raise SystemExit(f"No Stage A1b summaries found under {run_root}")

    baseline = load_baseline_note(args.baseline_a1_run_root)

    per_task: dict[str, list[dict[str, Any]]] = defaultdict(list)
    per_family: dict[str, list[dict[str, Any]]] = defaultdict(list)
    probe_fit_rows: list[dict[str, Any]] = []

    for sp in summary_paths:
        data = json.loads(sp.read_text())
        output_id = sp.parent.name
        seed = int(data.get("seed", -1))
        checkpoint_path = str(data.get("checkpoint_path", ""))
        for task_name, task in data["tasks"].items():
            row = {
                "output_id": output_id,
                "seed": seed,
                "task": task_name,
                "family": task["family"],
                "metric_name": task["metric_name"],
                "best_private_metric": float(task["best_private_metric"]),
                "joint_gain": float(task["joint_gain"]),
                "resid_gain": float(task["resid_gain"]),
                "content_margin": float(task["content_margin"]),
                "raw_gap": float(task["raw_gap"]),
                "raw_metric": float(task["representations"]["raw"]["primary_metric"]),
                "pos_priv_metric": float(task["representations"]["pos_priv"]["primary_metric"]),
                "content_priv_metric": float(task["representations"]["content_priv"]["primary_metric"]),
                "joint_metric": float(task["representations"]["joint"]["primary_metric"]),
                "resid_metric": float(task["representations"]["resid_additive"]["primary_metric"]),
                "checkpoint_path": checkpoint_path,
                "summary_path": str(sp),
            }
            per_task[task_name].append(row)
            for rep_name, rep in task["representations"].items():
                diag = rep.get("diagnostics", {})
                probe_fit_rows.append(
                    {
                        "output_id": output_id,
                        "seed": seed,
                        "task": task_name,
                        "family": task["family"],
                        "representation": rep_name,
                        "metric_name": task["metric_name"],
                        "primary_metric": float(rep["primary_metric"]),
                        "n_iter_max": int(diag.get("n_iter_max", -1)),
                        "hit_max_iter": bool(diag.get("hit_max_iter", False)),
                        "elapsed_sec": float(diag.get("elapsed_sec", float("nan"))),
                        "best_eval_top1": float(diag.get("best_eval_top1", float("nan"))),
                        "final_train_loss": float(diag.get("final_train_loss", float("nan"))),
                        "effective_lr": float(diag.get("effective_lr", float("nan"))),
                        "scheduler": str(diag.get("scheduler", "")),
                    }
                )
        for family_name, fam in data["families"].items():
            per_family[family_name].append(
                {
                    "output_id": output_id,
                    "seed": seed,
                    "family": family_name,
                    "n_tasks": int(fam["n_tasks"]),
                    "mean_joint_gain": float(fam["mean_joint_gain"]),
                    "median_joint_gain": float(fam["median_joint_gain"]),
                    "mean_resid_gain": float(fam["mean_resid_gain"]),
                    "median_resid_gain": float(fam["median_resid_gain"]),
                    "mean_content_margin": float(fam["mean_content_margin"]),
                    "mean_raw_gap": float(fam["mean_raw_gap"]),
                    "mean_best_private_metric": float(fam["mean_best_private_metric"]),
                    "mean_raw_metric": float(fam["mean_raw_metric"]),
                    "mean_joint_metric": float(fam["mean_joint_metric"]),
                    "mean_resid_metric": float(fam["mean_resid_metric"]),
                    "mean_pos_priv_metric": float(fam["mean_pos_priv_metric"]),
                    "mean_content_priv_metric": float(fam["mean_content_priv_metric"]),
                }
            )

    agg_task_rows: list[dict[str, Any]] = []
    for task_name, rows in sorted(per_task.items()):
        gains = [float(r["joint_gain"]) for r in rows]
        resid_gains = [float(r["resid_gain"]) for r in rows]
        margins = [float(r["content_margin"]) for r in rows]
        raw_gaps = [float(r["raw_gap"]) for r in rows]
        raws = [float(r["raw_metric"]) for r in rows]
        pos_vals = [float(r["pos_priv_metric"]) for r in rows]
        content_vals = [float(r["content_priv_metric"]) for r in rows]
        joints = [float(r["joint_metric"]) for r in rows]
        resids = [float(r["resid_metric"]) for r in rows]
        bests = [float(r["best_private_metric"]) for r in rows]
        agg_task_rows.append(
            {
                "task": task_name,
                "family": rows[0]["family"],
                "metric_name": rows[0]["metric_name"],
                "n_runs": len(rows),
                "mean_joint_gain": mean(gains),
                "median_joint_gain": median(gains),
                "min_joint_gain": min(gains),
                "max_joint_gain": max(gains),
                "positive_count": sum(1 for g in gains if g > 0.0),
                "mean_resid_gain": mean(resid_gains),
                "median_resid_gain": median(resid_gains),
                "mean_content_margin": mean(margins),
                "mean_raw_gap": mean(raw_gaps),
                "mean_raw_metric": mean(raws),
                "mean_pos_priv_metric": mean(pos_vals),
                "mean_content_priv_metric": mean(content_vals),
                "mean_joint_metric": mean(joints),
                "mean_resid_metric": mean(resids),
                "mean_best_private_metric": mean(bests),
            }
        )

    agg_family_rows: list[dict[str, Any]] = []
    family_verdicts: dict[str, Any] = {}
    for family_name, rows in sorted(per_family.items()):
        gains = [float(r["mean_joint_gain"]) for r in rows]
        resid_gains = [float(r["mean_resid_gain"]) for r in rows]
        margins = [float(r["mean_content_margin"]) for r in rows]
        raw_gaps = [float(r["mean_raw_gap"]) for r in rows]
        pos_vals = [float(r["mean_pos_priv_metric"]) for r in rows]
        content_vals = [float(r["mean_content_priv_metric"]) for r in rows]
        mean_joint = mean(gains)
        median_joint = median(gains)
        positive_count = sum(1 for g in gains if g > 0.0)
        content_private_all_runs = all(c > p for c, p in zip(content_vals, pos_vals))
        syntax_pass, semantic_pass = family_pass(
            family_name=family_name,
            mean_joint=mean_joint,
            median_joint=median_joint,
            positive_count=positive_count,
            content_private_all_runs=content_private_all_runs,
        )
        row = {
            "family": family_name,
            "n_runs": len(rows),
            "mean_joint_gain": mean_joint,
            "median_joint_gain": median_joint,
            "min_joint_gain": min(gains),
            "max_joint_gain": max(gains),
            "positive_count": positive_count,
            "mean_resid_gain": mean(resid_gains),
            "median_resid_gain": median(resid_gains),
            "mean_content_margin": mean(margins),
            "mean_raw_gap": mean(raw_gaps),
            "mean_pos_priv_metric": mean(pos_vals),
            "mean_content_priv_metric": mean(content_vals),
            "content_private_all_runs": content_private_all_runs,
            "syntax_family_pass": syntax_pass,
            "semantic_family_pass": semantic_pass,
            "exploratory_family": family_name in EXPLORATORY_SYNTAX_FAMILIES,
        }
        agg_family_rows.append(row)
        family_verdicts[family_name] = row

    agg_probe_fit_rows: list[dict[str, Any]] = []
    by_probe_key: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for row in probe_fit_rows:
        by_probe_key[(str(row["task"]), str(row["representation"]))].append(row)
    for (task_name, rep_name), rows in sorted(by_probe_key.items()):
        iters = [int(r["n_iter_max"]) for r in rows]
        hits = [1 if bool(r["hit_max_iter"]) else 0 for r in rows]
        elapsed = [float(r["elapsed_sec"]) for r in rows]
        best_top1 = [float(r["best_eval_top1"]) for r in rows]
        final_loss = [float(r["final_train_loss"]) for r in rows]
        agg_probe_fit_rows.append(
            {
                "task": task_name,
                "family": rows[0]["family"],
                "representation": rep_name,
                "metric_name": rows[0]["metric_name"],
                "n_runs": len(rows),
                "hit_max_iter_count": sum(hits),
                "hit_max_iter_frac": sum(hits) / len(hits),
                "mean_n_iter_max": mean([float(x) for x in iters]),
                "median_n_iter_max": median([float(x) for x in iters]),
                "mean_elapsed_sec": mean(elapsed),
                "mean_best_eval_top1": mean(best_top1),
                "mean_final_train_loss": mean(final_loss),
                "effective_lr": rows[0]["effective_lr"],
                "scheduler": rows[0]["scheduler"],
            }
        )

    passed_syntax = [f for f in SYNTAX_FAMILIES if family_verdicts.get(f, {}).get("syntax_family_pass")]
    passed_typeonly = [f for f in TYPEONLY_SEMANTIC_FAMILIES if family_verdicts.get(f, {}).get("semantic_family_pass")]
    passed_binary = [f for f in BINARY_SEMANTIC_FAMILIES if family_verdicts.get(f, {}).get("semantic_family_pass")]
    candidate_amendment_supported = len(passed_syntax) >= 2 and (len(passed_typeonly) >= 2 or len(passed_binary) >= 2)

    decision = {
        "stage": "pcc_stage_a1b_aggregate",
        "run_root": str(run_root),
        "n_summaries": len(summary_paths),
        "thresholds": {
            "syntax_mean_joint_gain_gt": SYNTAX_MEAN_GATE,
            "syntax_median_joint_gain_gt": SYNTAX_MEDIAN_GATE,
            "syntax_positive_count_gte": SYNTAX_POSITIVE_GATE,
            "semantic_content_private_all_runs": True,
            "semantic_mean_joint_gain_lt": SEMANTIC_MAX_MEAN_JOINT_GAIN,
        },
        "baseline_a1_run_root": str(args.baseline_a1_run_root) if args.baseline_a1_run_root else "",
        "baseline_a1_no_go": bool(not baseline.get("proceed_to_stage_b", False)) if baseline else None,
        "passed_syntax_families": passed_syntax,
        "passed_typeonly_semantic_families": passed_typeonly,
        "passed_binary_semantic_families": passed_binary,
        "candidate_amendment_supported": candidate_amendment_supported,
        "family_verdicts": family_verdicts,
        "fit_health_summary": {
            "worst_hit_max_iter": [
                row
                for row in sorted(
                    agg_probe_fit_rows,
                    key=lambda r: (-int(r["hit_max_iter_count"]), -float(r["mean_n_iter_max"]), str(r["task"]), str(r["representation"])),
                )
                if int(row["hit_max_iter_count"]) > 0
            ][:12]
        },
        "conclusion": (
            "A1b diagnostics support considering a preregistered gate amendment: at least two syntax families pass once deprel_coarse is separated, and at least two semantic diagnostic families pass under BIO-collapsed/entity-binary labeling."
            if candidate_amendment_supported
            else "A1b diagnostics do not yet justify a gate amendment. Keep the current Stage A1 no-go as the operative decision."
        ),
    }

    write_tsv(run_root / "aggregate_task_metrics.tsv", agg_task_rows)
    write_tsv(run_root / "aggregate_family_metrics.tsv", agg_family_rows)
    write_tsv(run_root / "aggregate_probe_fit_metrics.tsv", agg_probe_fit_rows)
    with open(run_root / "stage_a1b_diagnostic.json", "w", encoding="utf-8") as f:
        json.dump(decision, f, indent=2)

    md = [
        "# Stage A1b Diagnostic Decision",
        "",
        f"- Run root: `{run_root}`",
        f"- Summaries aggregated: `{len(summary_paths)}`",
        f"- Passed syntax families: `{', '.join(passed_syntax) if passed_syntax else 'none'}`",
        f"- Passed type-only semantic families: `{', '.join(passed_typeonly) if passed_typeonly else 'none'}`",
        f"- Passed entity-binary semantic families: `{', '.join(passed_binary) if passed_binary else 'none'}`",
        f"- Candidate amendment supported: `{candidate_amendment_supported}`",
        "",
        "## Conclusion",
        decision["conclusion"],
        "",
        "## Family Summary",
        "| family | mean_joint_gain | median_joint_gain | positive_count | content_private_all_runs | syntax_family_pass | semantic_family_pass | exploratory_family |",
        "|---|---:|---:|---:|---|---|---|---|",
    ]
    for row in agg_family_rows:
        md.append(
            f"| {row['family']} | {row['mean_joint_gain']:.6f} | {row['median_joint_gain']:.6f} | {row['positive_count']} | {row['content_private_all_runs']} | {row['syntax_family_pass']} | {row['semantic_family_pass']} | {row['exploratory_family']} |"
        )
    md.extend(
        [
            "",
            "## Fit-Health Appendix",
            "- Probe selection regime in this A1b diagnostic run matches the frozen A1 run for comparability.",
            "",
            "| task | representation | hit_max_iter_count | mean_n_iter_max | mean_best_eval_top1 | mean_final_train_loss |",
            "|---|---|---:|---:|---:|---:|",
        ]
    )
    for row in decision["fit_health_summary"]["worst_hit_max_iter"]:
        md.append(
            f"| {row['task']} | {row['representation']} | {row['hit_max_iter_count']} | {row['mean_n_iter_max']:.1f} | {row['mean_best_eval_top1']:.4f} | {row['mean_final_train_loss']:.4f} |"
        )
    with open(run_root / "stage_a1b_diagnostic.md", "w", encoding="utf-8") as f:
        f.write("\n".join(md) + "\n")

    print(
        json.dumps(
            {
                "run_root": str(run_root),
                "aggregate_task_metrics": str(run_root / "aggregate_task_metrics.tsv"),
                "aggregate_family_metrics": str(run_root / "aggregate_family_metrics.tsv"),
                "aggregate_probe_fit_metrics": str(run_root / "aggregate_probe_fit_metrics.tsv"),
                "diagnostic_json": str(run_root / "stage_a1b_diagnostic.json"),
                "diagnostic_md": str(run_root / "stage_a1b_diagnostic.md"),
                "candidate_amendment_supported": candidate_amendment_supported,
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
