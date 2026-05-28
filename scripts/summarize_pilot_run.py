#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import datetime as dt
import json
import math
import os
from collections import defaultdict
from typing import Any
import random


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Summarize MSAE pilot run outputs")
    p.add_argument("--run_root", type=str, required=True)
    p.add_argument("--manifest", type=str, default="run_manifest.tsv")
    p.add_argument("--output_aggregate", type=str, default="aggregate_results.tsv")
    p.add_argument("--output_per_layer", type=str, default="per_layer_aggregate.tsv")
    p.add_argument("--output_status", type=str, default="status_snapshot.json")
    p.add_argument("--output_ci", type=str, default="ci_metrics.tsv")
    p.add_argument("--output_sensitivity", type=str, default="threshold_sensitivity.tsv")
    p.add_argument("--output_decision_json", type=str, default="pre_k2_decision.json")
    p.add_argument("--output_decision_md", type=str, default="pre_k2_decision.md")
    p.add_argument("--bootstrap_samples", type=int, default=2000)
    return p.parse_args()


def to_int_bool(v: Any) -> int:
    return int(bool(v))


def safe_float(v: Any) -> float:
    try:
        x = float(v)
        return x
    except Exception:
        return float("nan")


def finite(v: Any) -> bool:
    try:
        x = float(v)
        return math.isfinite(x)
    except Exception:
        return False


def bootstrap_mean_ci(
    values: list[float], n_boot: int = 2000, alpha: float = 0.05, seed: int = 0
) -> tuple[float, float, float]:
    if not values:
        return float("nan"), float("nan"), float("nan")
    vals = [float(v) for v in values if finite(v)]
    if not vals:
        return float("nan"), float("nan"), float("nan")
    point = float(sum(vals) / len(vals))
    if len(vals) == 1:
        return point, point, point
    rng = random.Random(seed)
    boots: list[float] = []
    n = len(vals)
    for _ in range(n_boot):
        sample = [vals[rng.randrange(n)] for _ in range(n)]
        boots.append(sum(sample) / n)
    boots.sort()
    lo_i = max(0, int(math.floor((alpha / 2.0) * (n_boot - 1))))
    hi_i = min(n_boot - 1, int(math.floor((1.0 - alpha / 2.0) * (n_boot - 1))))
    return point, float(boots[lo_i]), float(boots[hi_i])


def read_manifest(path: str) -> list[dict[str, str]]:
    with open(path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f, delimiter="\t")
        return [dict(row) for row in reader]


def write_tsv(path: str, rows: list[dict[str, Any]]) -> None:
    if not rows:
        return
    with open(path, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()), delimiter="\t")
        w.writeheader()
        w.writerows(rows)


def main() -> None:
    args = parse_args()
    manifest_path = args.manifest
    if not os.path.isabs(manifest_path):
        manifest_path = os.path.join(args.run_root, manifest_path)

    runs = read_manifest(manifest_path)
    aggregate_rows: list[dict[str, Any]] = []
    status_runs: list[dict[str, Any]] = []

    for run in runs:
        out_dir = run["output_dir"]
        log_file = run.get("log_file", "")
        summary_path = os.path.join(out_dir, "raw_sep_summary.json")
        partial_path = os.path.join(out_dir, "intermediates", "partial_summary.json")

        run_status: dict[str, Any] = dict(run)
        run_status["summary_path"] = summary_path
        run_status["partial_summary_path"] = partial_path
        manifest_status = str(run.get("status", "")).strip().lower()
        if manifest_status in {"running", "done", "failed", "pending"}:
            run_status["status"] = manifest_status
        else:
            run_status["status"] = "pending"
        run_status["completed_ranks"] = []
        run_status["layer_index_effective"] = run.get("layer_index", "")
        run_status["collection_stats"] = {}

        if os.path.exists(log_file):
            run_status["log_size_bytes"] = os.path.getsize(log_file)
        else:
            run_status["log_size_bytes"] = 0

        summary_obj: dict[str, Any] | None = None
        if os.path.exists(summary_path):
            with open(summary_path, "r", encoding="utf-8") as f:
                summary_obj = json.load(f)
            run_status["status"] = "done"
        elif os.path.exists(partial_path):
            run_status["status"] = "running"
            with open(partial_path, "r", encoding="utf-8") as f:
                summary_obj = json.load(f)

        if summary_obj is not None:
            args_obj = summary_obj.get("args", {})
            run_status["layer_index_effective"] = args_obj.get("layer_index", run_status["layer_index_effective"])
            run_status["collection_stats"] = summary_obj.get("collection_stats", {})
            run_status["probe_backend_effective"] = summary_obj.get("probe_backend", "")
            rank_results = summary_obj.get("rank_results", {})
            completed_ranks = sorted(int(r) for r in rank_results.keys())
            run_status["completed_ranks"] = completed_ranks

            if run_status["status"] == "done":
                for rank_str, rr in rank_results.items():
                    rank = int(rank_str)
                    checks = rr.get("threshold_checks", {})
                    pos_raw = rr.get("position_raw", {})
                    tok_raw = rr.get("token_raw", {})
                    pos_spos = rr.get("position_on_S_pos", {})
                    pos_spos_perp = rr.get("position_on_S_pos_perp", {})
                    tok_stok = rr.get("token_on_S_tok", {})
                    tok_stok_perp = rr.get("token_on_S_tok_perp", {})
                    tok_spos = rr.get("token_on_S_pos", {})
                    pos_stok = rr.get("position_on_S_tok", {})
                    fit_diag = rr.get("fit_diagnostics", {})
                    dpos = fit_diag.get("position_raw", {})
                    dtok = fit_diag.get("token_raw", {})

                    aggregate_rows.append(
                        {
                            "session": run.get("session", ""),
                            "gpu": run.get("gpu", ""),
                            "model": run.get("model", ""),
                            "seed": run.get("seed", ""),
                            "layer_index": args_obj.get("layer_index", run.get("layer_index", "")),
                            "split_mode": args_obj.get("split_mode", ""),
                            "rank": rank,
                            "all_pass": to_int_bool(checks.get("all_pass", False)),
                            "all_pass_alt_c2": to_int_bool(checks.get("all_pass_alt_c2", False)),
                            "all_pass_recovery_var": to_int_bool(checks.get("all_pass_recovery_var", False)),
                            "all_pass_v2": to_int_bool(checks.get("all_pass_v2", False)),
                            "c1": to_int_bool(checks.get("criterion_1_position_subspace_auc", False)),
                            "c1_new_rank_recovery": to_int_bool(
                                checks.get("criterion_1_new_rank_recovery", checks.get("c1_new_rank_recovery", False))
                            ),
                            "c2": to_int_bool(checks.get("criterion_2_token_retention_vs_perp_drop", False)),
                            "c2_alt": to_int_bool(checks.get("criterion_2_alt_rank_linear_drop", False)),
                            "c2_var": to_int_bool(checks.get("criterion_2_var_energy_excess", False)),
                            "c2_var_v2": to_int_bool(checks.get("criterion_2_var_v2_ratio_excess", False)),
                            "c3": to_int_bool(checks.get("criterion_3_cross_talk_reduction", False)),
                            "c3_v2": to_int_bool(checks.get("criterion_3_v2_chance_corrected", False)),
                            "c4": to_int_bool(checks.get("criterion_4_principal_angle", False)),
                            "rank_at_pos90": checks.get("rank_at_pos90", ""),
                            "rank_budget_d_over_8": checks.get("rank_budget_d_over_8", ""),
                            "raw_pos_auc": pos_raw.get("auc_ovo_macro", float("nan")),
                            "raw_tok_top1": tok_raw.get("top1", float("nan")),
                            "pos_spos_auc": pos_spos.get("auc_ovo_macro", float("nan")),
                            "pos_spos_perp_auc": pos_spos_perp.get("auc_ovo_macro", float("nan")),
                            "pos_auc_recovery": rr.get("pos_auc_recovery", float("nan")),
                            "tok_stok_top1": tok_stok.get("top1", float("nan")),
                            "tok_stok_perp_top1": tok_stok_perp.get("top1", float("nan")),
                            "tok_top1_recovery": rr.get("tok_top1_recovery", float("nan")),
                            "tok_spos_top1": tok_spos.get("top1", float("nan")),
                            "pos_stok_auc": pos_stok.get("auc_ovo_macro", float("nan")),
                            "tok_energy_ratio": rr.get("tok_energy_ratio", float("nan")),
                            "tok_energy_baseline": rr.get("tok_energy_baseline", float("nan")),
                            "tok_energy_excess": rr.get("tok_energy_excess", float("nan")),
                            "c2_var_ratio": checks.get("c2_var_ratio", float("nan")),
                            "c2_var_threshold": checks.get("c2_var_threshold", float("nan")),
                            "c2_var_excess_floor": checks.get("c2_var_excess_floor", float("nan")),
                            "pos_drop_frac_v2": checks.get("pos_drop_frac_v2", float("nan")),
                            "tok_drop_frac_v2": checks.get("tok_drop_frac_v2", float("nan")),
                            "c3_v2_drop_fraction": checks.get("c3_v2_drop_fraction", float("nan")),
                            "principal_median_angle_deg": rr.get("principal_angles_deg", {}).get(
                                "median_angle_deg", float("nan")
                            ),
                            "cross_projection_energy_normalized": rr.get(
                                "cross_projection_energy_normalized", float("nan")
                            ),
                            "position_raw_n_iter_max": dpos.get("n_iter_max", ""),
                            "position_raw_hit_max_iter": to_int_bool(dpos.get("hit_max_iter", False)),
                            "token_raw_n_iter_max": dtok.get("n_iter_max", ""),
                            "token_raw_hit_max_iter": to_int_bool(dtok.get("hit_max_iter", False)),
                            "position_raw_diag_backend": dpos.get("backend", ""),
                            "token_raw_diag_backend": dtok.get("backend", ""),
                            "position_raw_effective_lr": dpos.get("effective_lr", float("nan")),
                            "token_raw_effective_lr": dtok.get("effective_lr", float("nan")),
                            "probe_torch_scheduler": dpos.get(
                                "scheduler", args_obj.get("probe_torch_scheduler", "")
                            ),
                            "git_commit_hash": summary_obj.get("run_metadata", {}).get(
                                "git_commit_hash", args_obj.get("git_commit_hash", "")
                            ),
                            "c2_var_v2_ratio_threshold": summary_obj.get("run_metadata", {}).get(
                                "c2_var_v2_ratio_threshold", checks.get("c2_var_threshold", float("nan"))
                            ),
                            "c2_var_v2_excess_floor": summary_obj.get("run_metadata", {}).get(
                                "c2_var_v2_excess_floor", checks.get("c2_var_excess_floor", float("nan"))
                            ),
                            "c3_v2_drop_fraction_cfg": summary_obj.get("run_metadata", {}).get(
                                "c3_v2_drop_fraction", checks.get("c3_v2_drop_fraction", float("nan"))
                            ),
                            "holdout_source_label": summary_obj.get("run_metadata", {}).get(
                                "holdout_source_label", ""
                            ),
                            "corpus_holdout_dataset_name": summary_obj.get("run_metadata", {}).get(
                                "corpus_holdout_dataset_name", ""
                            ),
                            "source_manifest_hash": summary_obj.get("run_metadata", {}).get(
                                "source_manifest_hash", ""
                            ),
                            "causal_pos_raw_on_spos_auc": rr.get("causal_sanity_frozen", {})
                            .get("position_raw_probe_on_S_pos", {})
                            .get("auc_ovo_macro", float("nan")),
                            "causal_pos_raw_on_spos_perp_auc": rr.get("causal_sanity_frozen", {})
                            .get("position_raw_probe_on_S_pos_perp", {})
                            .get("auc_ovo_macro", float("nan")),
                            "causal_pos_raw_on_stok_auc": rr.get("causal_sanity_frozen", {})
                            .get("position_raw_probe_on_S_tok", {})
                            .get("auc_ovo_macro", float("nan")),
                            "causal_tok_raw_on_stok_top1": rr.get("causal_sanity_frozen", {})
                            .get("token_raw_probe_on_S_tok", {})
                            .get("top1", float("nan")),
                            "causal_tok_raw_on_stok_perp_top1": rr.get("causal_sanity_frozen", {})
                            .get("token_raw_probe_on_S_tok_perp", {})
                            .get("top1", float("nan")),
                            "causal_tok_raw_on_spos_top1": rr.get("causal_sanity_frozen", {})
                            .get("token_raw_probe_on_S_pos", {})
                            .get("top1", float("nan")),
                            "output_dir": out_dir,
                        }
                    )

        status_runs.append(run_status)

    aggregate_rows.sort(key=lambda x: (x["model"], int(x["layer_index"]), int(x["rank"])))
    aggregate_path = os.path.join(args.run_root, args.output_aggregate)
    write_tsv(aggregate_path, aggregate_rows)

    grouped: dict[tuple[str, int], list[dict[str, Any]]] = defaultdict(list)
    for row in aggregate_rows:
        grouped[(str(row["model"]), int(row["layer_index"]))].append(row)

    per_layer_rows: list[dict[str, Any]] = []
    for (model, layer), rows in sorted(grouped.items(), key=lambda x: (x[0][0], x[0][1])):
        best_pos = max(rows, key=lambda r: safe_float(r["pos_auc_recovery"]))
        best_tok = max(rows, key=lambda r: safe_float(r["tok_top1_recovery"]))
        rank_at_pos90 = ""
        rank_budget = ""
        c1_new = 0
        for row in rows:
            rpos = row.get("rank_at_pos90", "")
            if rpos != "":
                rank_at_pos90 = rpos
                rank_budget = row.get("rank_budget_d_over_8", "")
                c1_new = to_int_bool(row.get("c1_new_rank_recovery", 0))
                break

        per_layer_rows.append(
            {
                "model": model,
                "layer_index": layer,
                "n_ranks": len(rows),
                "raw_pos_auc": rows[0].get("raw_pos_auc", float("nan")),
                "raw_tok_top1": rows[0].get("raw_tok_top1", float("nan")),
                "best_pos_auc_recovery": best_pos.get("pos_auc_recovery", float("nan")),
                "best_pos_auc_recovery_rank": best_pos.get("rank", ""),
                "best_tok_top1_recovery": best_tok.get("tok_top1_recovery", float("nan")),
                "best_tok_top1_recovery_rank": best_tok.get("rank", ""),
                "rank_at_pos90": rank_at_pos90,
                "rank_budget_d_over_8": rank_budget,
                "c1_new_rank_recovery": c1_new,
                "max_all_pass": max(to_int_bool(r.get("all_pass", 0)) for r in rows),
                "max_all_pass_alt_c2": max(to_int_bool(r.get("all_pass_alt_c2", 0)) for r in rows),
                "max_all_pass_recovery_var": max(to_int_bool(r.get("all_pass_recovery_var", 0)) for r in rows),
                "max_all_pass_v2": max(to_int_bool(r.get("all_pass_v2", 0)) for r in rows),
            }
        )

    per_layer_path = os.path.join(args.run_root, args.output_per_layer)
    write_tsv(per_layer_path, per_layer_rows)

    # Bootstrap CI tables for key metrics
    ci_rows: list[dict[str, Any]] = []
    metrics_for_ci = ["raw_pos_auc", "c2_var_ratio", "tok_drop_frac_v2", "all_pass_v2"]
    grouped_rank = defaultdict(list)
    for row in aggregate_rows:
        key = (str(row["model"]), int(row["layer_index"]), int(row["rank"]))
        grouped_rank[key].append(row)
    for (model, layer, rank), rows in sorted(grouped_rank.items(), key=lambda x: (x[0][0], x[0][1], x[0][2])):
        for metric in metrics_for_ci:
            vals = [safe_float(r.get(metric, float("nan"))) for r in rows]
            point, lo, hi = bootstrap_mean_ci(
                vals,
                n_boot=int(args.bootstrap_samples),
                alpha=0.05,
                seed=abs(hash((model, layer, rank, metric))) % (2**31 - 1),
            )
            ci_rows.append(
                {
                    "model": model,
                    "layer_index": layer,
                    "rank": rank,
                    "metric": metric,
                    "n": len([v for v in vals if finite(v)]),
                    "mean": point,
                    "ci_lo_95": lo,
                    "ci_hi_95": hi,
                }
            )
    ci_path = os.path.join(args.run_root, args.output_ci)
    write_tsv(ci_path, ci_rows)

    # Threshold sensitivity recomputation (no retraining)
    ratio_grid = [2.5, 3.0, 3.5]
    excess_grid = [0.03, 0.05, 0.07]
    drop_grid = [0.20, 0.25, 0.30]
    sensitivity_rows: list[dict[str, Any]] = []
    for ratio_thr in ratio_grid:
        for excess_floor in excess_grid:
            for drop_thr in drop_grid:
                group_values: dict[tuple[str, int, int], list[int]] = defaultdict(list)
                overall: list[int] = []
                for row in aggregate_rows:
                    c1_new = to_int_bool(row.get("c1_new_rank_recovery", 0)) == 1
                    c4 = to_int_bool(row.get("c4", 0)) == 1
                    c2_new = (
                        finite(row.get("c2_var_ratio", float("nan")))
                        and finite(row.get("tok_energy_excess", float("nan")))
                        and safe_float(row["c2_var_ratio"]) >= ratio_thr
                        and safe_float(row["tok_energy_excess"]) >= excess_floor
                    )
                    c3_new = (
                        finite(row.get("pos_drop_frac_v2", float("nan")))
                        and finite(row.get("tok_drop_frac_v2", float("nan")))
                        and safe_float(row["pos_drop_frac_v2"]) >= drop_thr
                        and safe_float(row["tok_drop_frac_v2"]) >= drop_thr
                    )
                    pass_v = int(c1_new and c2_new and c3_new and c4)
                    key = (str(row["model"]), int(row["layer_index"]), int(row["rank"]))
                    group_values[key].append(pass_v)
                    overall.append(pass_v)
                for (model, layer, rank), vals in sorted(group_values.items(), key=lambda x: (x[0][0], x[0][1], x[0][2])):
                    sensitivity_rows.append(
                        {
                            "scope": "by_model_layer_rank",
                            "model": model,
                            "layer_index": layer,
                            "rank": rank,
                            "c2_var_ratio_threshold": ratio_thr,
                            "c2_var_excess_floor": excess_floor,
                            "c3_v2_drop_fraction": drop_thr,
                            "pass_rate": sum(vals) / max(1, len(vals)),
                            "n": len(vals),
                        }
                    )
                sensitivity_rows.append(
                    {
                        "scope": "overall",
                        "model": "",
                        "layer_index": "",
                        "rank": "",
                        "c2_var_ratio_threshold": ratio_thr,
                        "c2_var_excess_floor": excess_floor,
                        "c3_v2_drop_fraction": drop_thr,
                        "pass_rate": sum(overall) / max(1, len(overall)),
                        "n": len(overall),
                    }
                )
    sensitivity_path = os.path.join(args.run_root, args.output_sensitivity)
    write_tsv(sensitivity_path, sensitivity_rows)

    # Pre-K2 decision artifact
    p160_rows = [
        r
        for r in aggregate_rows
        if str(r.get("model", "")) == "EleutherAI/pythia-160m-deduped"
        and int(r.get("layer_index", -1)) in (3, 4)
        and int(r.get("rank", -1)) in (8, 16, 32)
    ]
    layer_scores: dict[int, dict[str, float]] = {}
    for layer in (3, 4):
        rows = [r for r in p160_rows if int(r["layer_index"]) == layer]
        if not rows:
            continue
        headline_rows = [r for r in rows if int(r["rank"]) in (8, 16)]
        holdout_rows = [r for r in headline_rows if str(r.get("split_mode", "iid")) != "iid"]
        layer_scores[layer] = {
            "headline_pass_rate": sum(to_int_bool(r.get("all_pass_v2", 0)) for r in headline_rows)
            / max(1, len(headline_rows)),
            "holdout_headline_pass_rate": sum(to_int_bool(r.get("all_pass_v2", 0)) for r in holdout_rows)
            / max(1, len(holdout_rows)),
            "raw_pos_auc_mean": sum(safe_float(r.get("raw_pos_auc", float("nan"))) for r in rows) / max(1, len(rows)),
            "r32_pass_rate": sum(
                to_int_bool(r.get("all_pass_v2", 0)) for r in rows if int(r.get("rank", -1)) == 32
            )
            / max(1, len([r for r in rows if int(r.get("rank", -1)) == 32])),
        }

    primary_layer = None
    fallback_layer = None
    if 3 in layer_scores and 4 in layer_scores:
        pair = sorted(
            [(3, layer_scores[3]), (4, layer_scores[4])],
            key=lambda x: (
                x[1]["holdout_headline_pass_rate"],
                x[1]["headline_pass_rate"],
                x[1]["raw_pos_auc_mean"],
            ),
            reverse=True,
        )
        primary_layer = pair[0][0]
        fallback_layer = pair[1][0]
    elif 3 in layer_scores:
        primary_layer = 3
    elif 4 in layer_scores:
        primary_layer = 4

    decision_obj = {
        "generated_at": dt.datetime.now().isoformat(),
        "run_root": args.run_root,
        "primary_layer_recommendation": primary_layer,
        "fallback_layer": fallback_layer,
        "headline_ranks": [8, 16],
        "boundary_rank_diagnostic": 32,
        "layer_scores": layer_scores,
        "gate_policy": "Proceed to K=2 only after this decision artifact is committed and pushed.",
    }
    decision_json_path = os.path.join(args.run_root, args.output_decision_json)
    with open(decision_json_path, "w", encoding="utf-8") as f:
        json.dump(decision_obj, f, indent=2)
    decision_md_path = os.path.join(args.run_root, args.output_decision_md)
    md_lines = [
        "# Pre-K2 Decision",
        "",
        f"- Generated: {decision_obj['generated_at']}",
        f"- Primary Layer Recommendation: L{primary_layer if primary_layer is not None else 'N/A'}",
        f"- Fallback Layer: L{fallback_layer if fallback_layer is not None else 'N/A'}",
        "- Headline ranks: 8 and 16",
        "- Rank 32 is boundary diagnostic only.",
        "",
        "## Layer Scores",
    ]
    for layer in sorted(layer_scores.keys()):
        s = layer_scores[layer]
        md_lines.append(
            f"- L{layer}: holdout_headline_pass_rate={s['holdout_headline_pass_rate']:.3f}, "
            f"headline_pass_rate={s['headline_pass_rate']:.3f}, raw_pos_auc_mean={s['raw_pos_auc_mean']:.4f}, "
            f"r32_pass_rate={s['r32_pass_rate']:.3f}"
        )
    with open(decision_md_path, "w", encoding="utf-8") as f:
        f.write("\n".join(md_lines) + "\n")

    done_count = sum(1 for r in status_runs if r.get("status") == "done")
    running_count = sum(1 for r in status_runs if r.get("status") == "running")
    pending_count = sum(1 for r in status_runs if r.get("status") == "pending")

    status_obj = {
        "run_root": args.run_root,
        "generated_at": dt.datetime.now().isoformat(),
        "runs": status_runs,
        "counts": {
            "total": len(status_runs),
            "done": done_count,
            "running": running_count,
            "pending": pending_count,
        },
        "aggregate_rows": len(aggregate_rows),
        "aggregate_results_tsv": aggregate_path,
        "per_layer_aggregate_tsv": per_layer_path,
        "ci_tsv": ci_path,
        "sensitivity_tsv": sensitivity_path,
        "decision_json": decision_json_path,
        "decision_md": decision_md_path,
    }

    status_path = os.path.join(args.run_root, args.output_status)
    with open(status_path, "w", encoding="utf-8") as f:
        json.dump(status_obj, f, indent=2)

    print(f"[done] wrote {aggregate_path}")
    print(f"[done] wrote {per_layer_path}")
    print(f"[done] wrote {ci_path}")
    print(f"[done] wrote {sensitivity_path}")
    print(f"[done] wrote {decision_json_path}")
    print(f"[done] wrote {decision_md_path}")
    print(f"[done] wrote {status_path}")
    print(
        f"[summary] runs total={len(status_runs)} done={done_count} "
        f"running={running_count} pending={pending_count} rows={len(aggregate_rows)}"
    )


if __name__ == "__main__":
    main()
