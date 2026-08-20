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
SEMANTIC_FAMILIES = ["sem_wnut17_typeonly", "sem_fewnerd_coarse_binary", "sem_wikineural_en_binary"]
SYNTAX_MEAN_GATE = 0.003
SYNTAX_MEDIAN_GATE = 0.0
SYNTAX_POSITIVE_GATE = 3
SEMANTIC_MAX_MEAN_JOINT_GAIN = 0.005


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Aggregate completed PCC Stage A1c confirmation summaries")
    p.add_argument("--run_root", type=str, required=True)
    p.add_argument("--frozen_a1_run_root", type=str, required=True)
    p.add_argument("--a1b_run_root", type=str, required=True)
    p.add_argument("--revision_path", type=str, required=True)
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


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text()) if path.exists() else {}


def family_pass(*, family_name: str, mean_joint: float, median_joint: float, positive_count: int, content_private_all_runs: bool) -> tuple[bool, bool]:
    syntax_pass = (
        family_name in SYNTAX_FAMILIES
        and mean_joint > SYNTAX_MEAN_GATE
        and median_joint > SYNTAX_MEDIAN_GATE
        and positive_count >= SYNTAX_POSITIVE_GATE
    )
    semantic_pass = (
        family_name in SEMANTIC_FAMILIES
        and content_private_all_runs
        and mean_joint < SEMANTIC_MAX_MEAN_JOINT_GAIN
    )
    return syntax_pass, semantic_pass


def main() -> None:
    args = parse_args()
    run_root = Path(args.run_root)
    summary_paths = sorted(run_root.glob("outputs/*/pcc_stage_a1c_summary.json"))
    if not summary_paths:
        raise SystemExit(f"No Stage A1c summaries found under {run_root}")

    frozen_a1 = load_json(Path(args.frozen_a1_run_root) / "stage_a1_decision.json")
    a1b = load_json(Path(args.a1b_run_root) / "stage_a1b_diagnostic.json")
    revision = Path(args.revision_path)

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
                        "best_eval_primary_metric": float(diag.get("best_eval_primary_metric", float("nan"))),
                        "selection_metric_name": str(diag.get("selection_metric_name", "")),
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
        best_primary = [float(r["best_eval_primary_metric"]) for r in rows]
        final_loss = [float(r["final_train_loss"]) for r in rows]
        agg_probe_fit_rows.append(
            {
                "task": task_name,
                "family": rows[0]["family"],
                "representation": rep_name,
                "metric_name": rows[0]["metric_name"],
                "selection_metric_name": rows[0]["selection_metric_name"],
                "n_runs": len(rows),
                "hit_max_iter_count": sum(hits),
                "hit_max_iter_frac": sum(hits) / len(hits),
                "mean_n_iter_max": mean([float(x) for x in iters]),
                "median_n_iter_max": median([float(x) for x in iters]),
                "mean_elapsed_sec": mean(elapsed),
                "mean_best_eval_top1": mean(best_top1),
                "mean_best_eval_primary_metric": mean(best_primary),
                "mean_final_train_loss": mean(final_loss),
                "effective_lr": rows[0]["effective_lr"],
                "scheduler": rows[0]["scheduler"],
            }
        )

    passed_syntax = sorted([name for name, row in family_verdicts.items() if row["syntax_family_pass"]])
    passed_semantic = sorted([name for name, row in family_verdicts.items() if row["semantic_family_pass"]])
    amendment_confirmed = len(passed_syntax) >= 2 and len(passed_semantic) >= 2

    fit_health = {
        "worst_hit_max_iter": sorted(agg_probe_fit_rows, key=lambda r: (-float(r["hit_max_iter_frac"]), -float(r["mean_n_iter_max"]), str(r["task"]), str(r["representation"])))[:12]
    }

    confirmation = {
        "stage": "pcc_stage_a1c_confirmation",
        "run_root": str(run_root),
        "n_summaries": len(summary_paths),
        "frozen_a1_run_root": str(args.frozen_a1_run_root),
        "frozen_a1_no_go": bool(not frozen_a1.get("proceed_to_stage_b", False)),
        "a1b_run_root": str(args.a1b_run_root),
        "a1b_candidate_amendment_supported": bool(a1b.get("candidate_amendment_supported", False)),
        "revision_path": str(revision),
        "thresholds": {
            "syntax_mean_joint_gain_gt": SYNTAX_MEAN_GATE,
            "syntax_median_joint_gain_gt": SYNTAX_MEDIAN_GATE,
            "syntax_positive_count_gte": SYNTAX_POSITIVE_GATE,
            "semantic_content_private_all_runs": True,
            "semantic_mean_joint_gain_lt": SEMANTIC_MAX_MEAN_JOINT_GAIN,
        },
        "passed_syntax_families": passed_syntax,
        "passed_semantic_families": passed_semantic,
        "amendment_confirmed": amendment_confirmed,
        "family_verdicts": family_verdicts,
        "fit_health_summary": fit_health,
        "conclusion": (
            "A1c confirms the proposed revision path: the amended syntax and semantic family set still satisfies the revised observational gate under macro_f1-aligned NER checkpoint selection."
            if amendment_confirmed else
            "A1c weakens the A1b revision case: the revised observational gate is not confirmed under macro_f1-aligned NER checkpoint selection."
        ),
    }

    write_tsv(run_root / "aggregate_task_metrics.tsv", agg_task_rows)
    write_tsv(run_root / "aggregate_family_metrics.tsv", agg_family_rows)
    write_tsv(run_root / "aggregate_probe_fit_metrics.tsv", agg_probe_fit_rows)
    with open(run_root / "stage_a1c_confirmation.json", "w", encoding="utf-8") as f:
        json.dump(confirmation, f, indent=2)

    md_lines = [
        "# Stage A1c Confirmation",
        "",
        f"- Run root: `{run_root}`",
        f"- Summaries aggregated: `{len(summary_paths)}`",
        f"- Frozen A1 no-go preserved: `{bool(not frozen_a1.get('proceed_to_stage_b', False))}`",
        f"- A1b candidate amendment supported: `{bool(a1b.get('candidate_amendment_supported', False))}`",
        f"- Amendment confirmed by A1c: `{amendment_confirmed}`",
        f"- Passed syntax families: `{', '.join(passed_syntax) if passed_syntax else '(none)'}`",
        f"- Passed semantic families: `{', '.join(passed_semantic) if passed_semantic else '(none)'}`",
        "",
        "## Conclusion",
        confirmation["conclusion"],
        "",
        "## Family Summary",
        "| family | mean_joint_gain | median_joint_gain | positive_count | content_private_all_runs | syntax_family_pass | semantic_family_pass |",
        "|---|---:|---:|---:|---|---|---|",
    ]
    for row in agg_family_rows:
        md_lines.append(
            f"| {row['family']} | {row['mean_joint_gain']:.6f} | {row['median_joint_gain']:.6f} | {row['positive_count']} | {row['content_private_all_runs']} | {row['syntax_family_pass']} | {row['semantic_family_pass']} |"
        )
    md_lines.extend([
        "",
        "## Fit-Health Appendix",
        "- Probe selection regime in A1c: validation-accuracy selection for syntax tasks; validation-macro_f1 selection for NER tasks.",
        "- The table below summarizes the most capped probe families by `(task, representation)`.",
        "",
        "| task | representation | selection_metric_name | hit_max_iter_count | mean_n_iter_max | mean_best_eval_primary_metric | mean_best_eval_top1 | mean_final_train_loss |",
        "|---|---|---|---:|---:|---:|---:|---:|",
    ])
    for row in fit_health["worst_hit_max_iter"]:
        md_lines.append(
            f"| {row['task']} | {row['representation']} | {row['selection_metric_name']} | {row['hit_max_iter_count']} | {row['mean_n_iter_max']:.1f} | {row['mean_best_eval_primary_metric']:.4f} | {row['mean_best_eval_top1']:.4f} | {row['mean_final_train_loss']:.4f} |"
        )
    (run_root / "stage_a1c_confirmation.md").write_text("\n".join(md_lines) + "\n", encoding="utf-8")

    adoption = {
        "revision_path": str(revision),
        "frozen_a1_run_root": str(args.frozen_a1_run_root),
        "a1b_run_root": str(args.a1b_run_root),
        "a1c_run_root": str(run_root),
        "adopt_revision": amendment_confirmed,
        "reason": (
            "A1c confirms the amendment under metric-aligned NER selection." if amendment_confirmed else
            "A1c does not confirm the amendment strongly enough to adopt it."
        ),
    }
    with open(run_root / "amendment_decision.json", "w", encoding="utf-8") as f:
        json.dump(adoption, f, indent=2)
    (run_root / "amendment_decision.md").write_text(
        "# PCC Amendment Decision\n\n"
        f"- Revision path: `{revision}`\n"
        f"- Adopt revision: `{amendment_confirmed}`\n"
        f"- Reason: {adoption['reason']}\n",
        encoding="utf-8",
    )

    if amendment_confirmed:
        stage_a1r = {
            "stage": "pcc_stage_a1r",
            "revision_path": str(revision),
            "based_on_run_root": str(run_root),
            "passed_syntax_families": passed_syntax,
            "passed_semantic_families": passed_semantic,
            "proceed_to_stage_b": True,
            "note": "This is an amended observational decision under PCC Gate Revision v1. It does not replace the frozen A1 record.",
        }
        with open(run_root / "stage_a1r_decision.json", "w", encoding="utf-8") as f:
            json.dump(stage_a1r, f, indent=2)
        (run_root / "stage_a1r_decision.md").write_text(
            "# Stage A1r Decision\n\n"
            f"- Revision path: `{revision}`\n"
            f"- Based on run root: `{run_root}`\n"
            f"- Passed syntax families: `{', '.join(passed_syntax)}`\n"
            f"- Passed semantic families: `{', '.join(passed_semantic)}`\n"
            f"- Proceed to Stage B: `True`\n\n"
            "## Note\n"
            "This amended decision is prospective and exists alongside the frozen A1 no-go record.\n",
            encoding="utf-8",
        )

    print(json.dumps({
        "run_root": str(run_root),
        "aggregate_task_metrics": str(run_root / "aggregate_task_metrics.tsv"),
        "aggregate_family_metrics": str(run_root / "aggregate_family_metrics.tsv"),
        "aggregate_probe_fit_metrics": str(run_root / "aggregate_probe_fit_metrics.tsv"),
        "confirmation_json": str(run_root / "stage_a1c_confirmation.json"),
        "confirmation_md": str(run_root / "stage_a1c_confirmation.md"),
        "amendment_decision_json": str(run_root / "amendment_decision.json"),
        "amendment_confirmed": amendment_confirmed,
    }, indent=2))


if __name__ == "__main__":
    main()
