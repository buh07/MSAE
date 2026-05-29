#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
import math
from pathlib import Path
from typing import Any


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Evaluate K2 wave1 runs and produce promotion decision")
    p.add_argument("--run_root", required=True)
    p.add_argument("--manifest", default="run_manifest.tsv")
    p.add_argument("--output_json", default="k2_wave1_decision.json")
    p.add_argument("--output_md", default="k2_wave1_decision.md")
    p.add_argument("--wave1_target_tokens", type=int, default=100_000_000)
    p.add_argument("--wave2_target_tokens", type=int, default=1_000_000_000)

    # Legacy/basic stability gate
    p.add_argument("--dead_fraction_fail_threshold", type=float, default=0.35)

    # Balanced quality-gate defaults
    p.add_argument("--tail_fvu_fail_threshold_l3_baseline", type=float, default=0.20)
    p.add_argument("--tail_incoh_fail_threshold_l3_baseline", type=float, default=0.12)
    p.add_argument("--util_active_latent_floor", type=float, default=0.03)
    p.add_argument("--util_entropy_floor", type=float, default=0.15)

    return p.parse_args()


def finite(x: float) -> bool:
    return math.isfinite(x)


def safe_float(x: Any, default: float = float("nan")) -> float:
    try:
        val = float(x)
    except Exception:
        return default
    return val if math.isfinite(val) else default


def tail_median_from_rows(rows: list[dict[str, Any]], key: str, window: int) -> float:
    vals = [safe_float(r.get(key, float("nan"))) for r in rows]
    vals = [v for v in vals if math.isfinite(v)]
    if not vals:
        return float("nan")
    tail = vals[-window:]
    tail_sorted = sorted(tail)
    n = len(tail_sorted)
    if n % 2 == 1:
        return float(tail_sorted[n // 2])
    return float(0.5 * (tail_sorted[n // 2 - 1] + tail_sorted[n // 2]))


def load_metrics_rows(metrics_path: Path) -> list[dict[str, Any]]:
    if not metrics_path.exists():
        return []
    out: list[dict[str, Any]] = []
    with open(metrics_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                out.append(json.loads(line))
            except Exception:
                continue
    return out


def main() -> None:
    args = parse_args()
    run_root = Path(args.run_root)
    manifest_path = run_root / args.manifest

    with open(manifest_path, "r", encoding="utf-8", newline="") as f:
        rows = list(csv.DictReader(f, delimiter="\t"))

    jobs = []
    for r in rows:
        out_dir = Path(r["output_dir"])
        summary_path = out_dir / "train_summary.json"
        metrics_path = out_dir / "train_metrics.jsonl"
        summary = None
        if summary_path.exists():
            summary = json.loads(summary_path.read_text(encoding="utf-8"))
        metrics_rows = load_metrics_rows(metrics_path)
        jobs.append({"manifest": r, "summary": summary, "metrics_rows": metrics_rows})

    eval_rows = []
    for j in jobs:
        m = j["manifest"]
        s = j["summary"] or {}
        metrics_rows = j["metrics_rows"]

        status = m.get("status", "")
        ok = status == "done" and bool(s)
        layer_index = int(m["layer_index"])
        lam = float(m["lambda_inc"])
        is_l3_baseline = layer_index == 3 and abs(lam - 1e-2) < 1e-12

        tokens_seen = int(s.get("tokens_seen", 0))
        pos_dead = safe_float(s.get("pos_dead_fraction_final", float("nan")))
        content_dead = safe_float(s.get("content_dead_fraction_final", float("nan")))
        throughput = safe_float(s.get("throughput_tok_s", float("nan")))

        tail100_fvu = safe_float(
            s.get("tail100_fvu_total_median", tail_median_from_rows(metrics_rows, "fvu_total", 100))
        )
        tail100_incoh = safe_float(
            s.get(
                "tail100_incoh_loss_est_median",
                tail_median_from_rows(metrics_rows, "incoh_loss_est", 100),
            )
        )
        tail100_active_pos = safe_float(
            s.get(
                "tail100_active_latent_frac_pos_median",
                tail_median_from_rows(metrics_rows, "active_latent_frac_pos", 100),
            )
        )
        tail100_active_content = safe_float(
            s.get(
                "tail100_active_latent_frac_content_median",
                tail_median_from_rows(metrics_rows, "active_latent_frac_content", 100),
            )
        )
        tail100_entropy_pos = safe_float(
            s.get(
                "tail100_usage_entropy_pos_median",
                tail_median_from_rows(metrics_rows, "usage_entropy_pos", 100),
            )
        )
        tail100_entropy_content = safe_float(
            s.get(
                "tail100_usage_entropy_content_median",
                tail_median_from_rows(metrics_rows, "usage_entropy_content", 100),
            )
        )

        reached = tokens_seen >= int(0.95 * args.wave1_target_tokens)
        stable_basic = (
            ok
            and reached
            and finite(pos_dead)
            and finite(content_dead)
            and pos_dead < args.dead_fraction_fail_threshold
            and content_dead < args.dead_fraction_fail_threshold
            and finite(throughput)
            and throughput > 0.0
        )

        warnings: list[str] = []
        quality_fail_reasons: list[str] = []

        if not stable_basic:
            quality_fail_reasons.append("failed_basic_gate")

        if finite(tail100_active_pos) and tail100_active_pos < args.util_active_latent_floor:
            warnings.append(
                f"active_latent_frac_pos_below_floor({tail100_active_pos:.4f}<{args.util_active_latent_floor:.4f})"
            )
        if finite(tail100_active_content) and tail100_active_content < args.util_active_latent_floor:
            warnings.append(
                f"active_latent_frac_content_below_floor({tail100_active_content:.4f}<{args.util_active_latent_floor:.4f})"
            )
        if finite(tail100_entropy_pos) and tail100_entropy_pos < args.util_entropy_floor:
            warnings.append(
                f"usage_entropy_pos_below_floor({tail100_entropy_pos:.4f}<{args.util_entropy_floor:.4f})"
            )
        if finite(tail100_entropy_content) and tail100_entropy_content < args.util_entropy_floor:
            warnings.append(
                f"usage_entropy_content_below_floor({tail100_entropy_content:.4f}<{args.util_entropy_floor:.4f})"
            )

        # Hard quality gate for L3 baseline candidates only.
        if is_l3_baseline:
            if finite(tail100_fvu) and tail100_fvu > args.tail_fvu_fail_threshold_l3_baseline:
                quality_fail_reasons.append(
                    f"tail100_fvu_total>{args.tail_fvu_fail_threshold_l3_baseline:.3f} ({tail100_fvu:.4f})"
                )
            if finite(tail100_incoh) and tail100_incoh > args.tail_incoh_fail_threshold_l3_baseline:
                quality_fail_reasons.append(
                    f"tail100_incoh>{args.tail_incoh_fail_threshold_l3_baseline:.3f} ({tail100_incoh:.4f})"
                )

        stable_quality = stable_basic and not quality_fail_reasons

        eval_rows.append(
            {
                "job_id": m["job_id"],
                "status": status,
                "layer_index": layer_index,
                "seed": int(m["seed"]),
                "lambda_inc": lam,
                "tokens_seen": tokens_seen,
                "reached_target": reached,
                "stable_basic": stable_basic,
                "stable_quality": stable_quality,
                "quality_fail_reasons": quality_fail_reasons,
                "warnings": warnings,
                "pos_dead_fraction_final": pos_dead,
                "content_dead_fraction_final": content_dead,
                "throughput_tok_s": throughput,
                "tail100_fvu_total_median": tail100_fvu,
                "tail100_incoh_loss_est_median": tail100_incoh,
                "tail100_active_latent_frac_pos_median": tail100_active_pos,
                "tail100_active_latent_frac_content_median": tail100_active_content,
                "tail100_usage_entropy_pos_median": tail100_entropy_pos,
                "tail100_usage_entropy_content_median": tail100_entropy_content,
                "final_checkpoint": s.get("checkpoint_final", ""),
                "metrics_schema_version": s.get("metrics_schema_version", "legacy"),
            }
        )

    # Promotion rules
    l3_baselines = [
        r for r in eval_rows if r["layer_index"] == 3 and abs(r["lambda_inc"] - 1e-2) < 1e-12
    ]
    l4_baseline = [
        r for r in eval_rows if r["layer_index"] == 4 and abs(r["lambda_inc"] - 1e-2) < 1e-12
    ]
    no_inc = [r for r in eval_rows if abs(r["lambda_inc"]) < 1e-12]

    promote = []
    for r in l3_baselines:
        if r["stable_quality"]:
            promote.append(r)

    l3_has_unstable = any(not r["stable_quality"] for r in l3_baselines)
    if l3_has_unstable:
        for r in l4_baseline:
            if r["stable_quality"]:
                promote.append(r)

    for r in no_inc:
        if r["stable_basic"]:
            promote.append(r)

    promote_by_id = {r["job_id"]: r for r in promote}
    promote = [promote_by_id[k] for k in sorted(promote_by_id.keys())]

    decision = {
        "run_root": str(run_root),
        "wave1_target_tokens": args.wave1_target_tokens,
        "wave2_target_tokens": args.wave2_target_tokens,
        "dead_fraction_fail_threshold": args.dead_fraction_fail_threshold,
        "tail_fvu_fail_threshold_l3_baseline": args.tail_fvu_fail_threshold_l3_baseline,
        "tail_incoh_fail_threshold_l3_baseline": args.tail_incoh_fail_threshold_l3_baseline,
        "util_active_latent_floor": args.util_active_latent_floor,
        "util_entropy_floor": args.util_entropy_floor,
        "jobs": eval_rows,
        "l3_has_unstable": l3_has_unstable,
        "promote_jobs": [
            {
                "job_id": r["job_id"],
                "layer_index": r["layer_index"],
                "seed": r["seed"],
                "lambda_inc": r["lambda_inc"],
                "resume_path": r["final_checkpoint"],
                "target_tokens": args.wave2_target_tokens,
            }
            for r in promote
        ],
    }

    out_json = run_root / args.output_json
    out_json.write_text(json.dumps(decision, indent=2), encoding="utf-8")

    lines = [
        "# K2 Wave1 Decision",
        "",
        f"- Run root: `{run_root}`",
        f"- Wave1 target tokens: {args.wave1_target_tokens}",
        f"- Wave2 target tokens: {args.wave2_target_tokens}",
        f"- Dead-fraction fail threshold: {args.dead_fraction_fail_threshold}",
        f"- L3 baseline tail100 FVU fail threshold: {args.tail_fvu_fail_threshold_l3_baseline}",
        f"- L3 baseline tail100 incoh fail threshold: {args.tail_incoh_fail_threshold_l3_baseline}",
        f"- Util active-latent floor: {args.util_active_latent_floor}",
        f"- Util entropy floor: {args.util_entropy_floor}",
        "",
        "## Job Outcomes",
    ]
    for r in eval_rows:
        fail_note = ",".join(r["quality_fail_reasons"]) if r["quality_fail_reasons"] else "-"
        warn_note = ",".join(r["warnings"]) if r["warnings"] else "-"
        lines.append(
            f"- {r['job_id']}: status={r['status']} stable_basic={r['stable_basic']} stable_quality={r['stable_quality']} "
            f"tokens_seen={r['tokens_seen']} tail100_fvu={r['tail100_fvu_total_median']:.4f} "
            f"tail100_incoh={r['tail100_incoh_loss_est_median']:.4f} "
            f"pos_dead={r['pos_dead_fraction_final']:.4f} content_dead={r['content_dead_fraction_final']:.4f} "
            f"throughput={r['throughput_tok_s']:.1f} fail={fail_note} warn={warn_note}"
        )
    lines.append("")
    lines.append("## Promotion Recommendation (Wave2)")
    if not promote:
        lines.append("- No runs met promotion criteria; investigate stability/quality and relaunch wave1.")
    else:
        for r in promote:
            lines.append(
                f"- Promote {r['job_id']} (L{r['layer_index']}, seed={r['seed']}, "
                f"lambda_inc={r['lambda_inc']}) resume=`{r['final_checkpoint']}`"
            )

    out_md = run_root / args.output_md
    out_md.write_text("\n".join(lines) + "\n", encoding="utf-8")

    print(f"[done] wrote {out_json}")
    print(f"[done] wrote {out_md}")


if __name__ == "__main__":
    main()
