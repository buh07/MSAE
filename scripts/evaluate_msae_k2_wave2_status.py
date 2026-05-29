#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
import math
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Periodic status evaluator for K2 wave2 runs")
    p.add_argument("--run_root", required=True)
    p.add_argument("--manifest", default="run_manifest.tsv")
    p.add_argument("--output_json", default="reports/wave2_status_snapshot.json")
    p.add_argument("--output_md", default="reports/wave2_status.md")
    p.add_argument("--milestone_tokens", type=int, default=100_000_000)
    p.add_argument("--tail_window", type=int, default=100)
    p.add_argument("--tail_fvu_fail_threshold_l3_baseline", type=float, default=0.20)
    p.add_argument("--tail_incoh_fail_threshold_l3_baseline", type=float, default=0.12)
    p.add_argument("--dead_fraction_fail_threshold", type=float, default=0.35)
    p.add_argument("--util_active_latent_floor", type=float, default=0.03)
    p.add_argument("--util_entropy_floor", type=float, default=0.15)
    p.add_argument("--fallback_resume_path", default="")
    p.add_argument("--fallback_layer_index", type=int, default=4)
    p.add_argument("--fallback_lambda_inc", type=float, default=1e-2)
    p.add_argument("--fallback_seed", type=int, default=42)
    return p.parse_args()


def safe_float(x: Any, default: float = float("nan")) -> float:
    try:
        y = float(x)
    except Exception:
        return default
    return y if math.isfinite(y) else default


def tail_median(rows: list[dict[str, Any]], key: str, window: int) -> float:
    vals = [safe_float(r.get(key, float("nan"))) for r in rows]
    vals = [v for v in vals if math.isfinite(v)]
    if not vals:
        return float("nan")
    tail = sorted(vals[-window:])
    n = len(tail)
    if n % 2 == 1:
        return float(tail[n // 2])
    return float(0.5 * (tail[n // 2 - 1] + tail[n // 2]))


def tail_slope(rows: list[dict[str, Any]], key: str, window: int) -> float:
    vals = [safe_float(r.get(key, float("nan"))) for r in rows]
    vals = [v for v in vals if math.isfinite(v)]
    if len(vals) < 2:
        return float("nan")
    tail = vals[-window:]
    n = len(tail)
    if n < 2:
        return float("nan")
    # simple least squares slope on integer x = [0..n-1]
    x_mean = 0.5 * (n - 1)
    y_mean = sum(tail) / n
    num = 0.0
    den = 0.0
    for i, y in enumerate(tail):
        dx = i - x_mean
        num += dx * (y - y_mean)
        den += dx * dx
    if den <= 0.0:
        return float("nan")
    return float(num / den)


def load_json(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def load_metrics_rows(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    rows: list[dict[str, Any]] = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                rows.append(json.loads(line))
            except Exception:
                continue
    return rows


def find_latest_checkpoint(output_dir: Path) -> str:
    ckpt_dir = output_dir / "checkpoints"
    if not ckpt_dir.exists():
        return ""
    ckpts = sorted(ckpt_dir.glob("*.pt"), key=lambda p: p.stat().st_mtime)
    return str(ckpts[-1]) if ckpts else ""


def main() -> None:
    args = parse_args()
    run_root = Path(args.run_root)
    manifest_path = run_root / args.manifest
    output_json = run_root / args.output_json
    output_md = run_root / args.output_md
    output_json.parent.mkdir(parents=True, exist_ok=True)

    prev_snapshot = load_json(output_json) or {}
    prev_fail_streak = prev_snapshot.get("fail_streak_by_job", {})
    prev_milestone = prev_snapshot.get("milestone_by_job", {})

    with open(manifest_path, "r", encoding="utf-8", newline="") as f:
        manifest_rows = list(csv.DictReader(f, delimiter="\t"))

    wave2_rows = [r for r in manifest_rows if r.get("stage") == "wave2"]

    job_states = []
    fail_streak_by_job: dict[str, int] = {}
    milestone_by_job: dict[str, int] = {}

    for r in wave2_rows:
        out_dir = Path(r["output_dir"])
        summary = load_json(out_dir / "train_summary.json") or {}
        metrics_rows = load_metrics_rows(out_dir / "train_metrics.jsonl")
        tokens_seen = int(summary.get("tokens_seen", 0))
        if tokens_seen <= 0 and metrics_rows:
            last_tok = metrics_rows[-1].get("tokens_seen", 0)
            try:
                tokens_seen = int(last_tok)
            except Exception:
                tokens_seen = 0
        status = r.get("status", "")
        layer_index = int(r["layer_index"])
        lam = float(r["lambda_inc"])
        is_l3_baseline = layer_index == 3 and abs(lam - 1e-2) < 1e-12
        has_reached_first_milestone = tokens_seen >= args.milestone_tokens

        tail100_fvu = safe_float(
            summary.get("tail100_fvu_total_median", tail_median(metrics_rows, "fvu_total", args.tail_window))
        )
        tail100_incoh = safe_float(
            summary.get(
                "tail100_incoh_loss_est_median",
                tail_median(metrics_rows, "incoh_loss_est", args.tail_window),
            )
        )
        tail100_active_pos = safe_float(
            summary.get(
                "tail100_active_latent_frac_pos_median",
                tail_median(metrics_rows, "active_latent_frac_pos", args.tail_window),
            )
        )
        tail100_active_content = safe_float(
            summary.get(
                "tail100_active_latent_frac_content_median",
                tail_median(metrics_rows, "active_latent_frac_content", args.tail_window),
            )
        )
        tail100_entropy_pos = safe_float(
            summary.get(
                "tail100_usage_entropy_pos_median",
                tail_median(metrics_rows, "usage_entropy_pos", args.tail_window),
            )
        )
        tail100_entropy_content = safe_float(
            summary.get(
                "tail100_usage_entropy_content_median",
                tail_median(metrics_rows, "usage_entropy_content", args.tail_window),
            )
        )
        tail100_fvu_slope = safe_float(
            summary.get("tail100_fvu_total_slope", tail_slope(metrics_rows, "fvu_total", args.tail_window))
        )
        tail100_incoh_slope = safe_float(
            summary.get("tail100_incoh_loss_est_slope", tail_slope(metrics_rows, "incoh_loss_est", args.tail_window))
        )

        pos_dead = safe_float(summary.get("pos_dead_fraction_final", float("nan")))
        content_dead = safe_float(summary.get("content_dead_fraction_final", float("nan")))

        quality_fail_reasons: list[str] = []
        warnings: list[str] = []

        if math.isfinite(pos_dead) and pos_dead > args.dead_fraction_fail_threshold:
            quality_fail_reasons.append(
                f"pos_dead>{args.dead_fraction_fail_threshold:.3f} ({pos_dead:.4f})"
            )
        if math.isfinite(content_dead) and content_dead > args.dead_fraction_fail_threshold:
            quality_fail_reasons.append(
                f"content_dead>{args.dead_fraction_fail_threshold:.3f} ({content_dead:.4f})"
            )

        if is_l3_baseline and has_reached_first_milestone:
            if math.isfinite(tail100_fvu) and tail100_fvu > args.tail_fvu_fail_threshold_l3_baseline:
                quality_fail_reasons.append(
                    f"tail100_fvu>{args.tail_fvu_fail_threshold_l3_baseline:.3f} ({tail100_fvu:.4f})"
                )
            if math.isfinite(tail100_incoh) and tail100_incoh > args.tail_incoh_fail_threshold_l3_baseline:
                quality_fail_reasons.append(
                    f"tail100_incoh>{args.tail_incoh_fail_threshold_l3_baseline:.3f} ({tail100_incoh:.4f})"
                )

        if math.isfinite(tail100_active_pos) and tail100_active_pos < args.util_active_latent_floor:
            warnings.append(
                f"active_latent_pos<{args.util_active_latent_floor:.3f} ({tail100_active_pos:.4f})"
            )
        if math.isfinite(tail100_active_content) and tail100_active_content < args.util_active_latent_floor:
            warnings.append(
                f"active_latent_content<{args.util_active_latent_floor:.3f} ({tail100_active_content:.4f})"
            )
        if math.isfinite(tail100_entropy_pos) and tail100_entropy_pos < args.util_entropy_floor:
            warnings.append(
                f"usage_entropy_pos<{args.util_entropy_floor:.3f} ({tail100_entropy_pos:.4f})"
            )
        if math.isfinite(tail100_entropy_content) and tail100_entropy_content < args.util_entropy_floor:
            warnings.append(
                f"usage_entropy_content<{args.util_entropy_floor:.3f} ({tail100_entropy_content:.4f})"
            )

        quality_ok = len(quality_fail_reasons) == 0
        jid = r["job_id"]
        prev_streak = int(prev_fail_streak.get(jid, 0))
        fail_streak = (prev_streak + 1) if not quality_ok else 0
        fail_streak_by_job[jid] = fail_streak

        milestone = tokens_seen // args.milestone_tokens
        milestone_by_job[jid] = milestone
        prev_ms = int(prev_milestone.get(jid, -1))
        milestone_advanced = milestone > prev_ms

        latest_ckpt = summary.get("checkpoint_final", "") or find_latest_checkpoint(out_dir)

        job_states.append(
            {
                "job_id": jid,
                "status": status,
                "layer_index": layer_index,
                "seed": int(r["seed"]),
                "lambda_inc": lam,
                "tokens_seen": tokens_seen,
                "milestone": int(milestone),
                "milestone_advanced": bool(milestone_advanced),
                "tail100_fvu_total_median": tail100_fvu,
                "tail100_incoh_loss_est_median": tail100_incoh,
                "tail100_fvu_total_slope": tail100_fvu_slope,
                "tail100_incoh_loss_est_slope": tail100_incoh_slope,
                "tail100_active_latent_frac_pos_median": tail100_active_pos,
                "tail100_active_latent_frac_content_median": tail100_active_content,
                "tail100_usage_entropy_pos_median": tail100_entropy_pos,
                "tail100_usage_entropy_content_median": tail100_entropy_content,
                "pos_dead_fraction_final": pos_dead,
                "content_dead_fraction_final": content_dead,
                "quality_ok": quality_ok,
                "has_reached_first_milestone": has_reached_first_milestone,
                "quality_fail_reasons": quality_fail_reasons,
                "warnings": warnings,
                "fail_streak": fail_streak,
                "latest_checkpoint": latest_ckpt,
                "metrics_schema_version": summary.get("metrics_schema_version", "legacy"),
            }
        )

    l3_baseline_wave2 = [
        r
        for r in job_states
        if r["layer_index"] == 3
        and abs(float(r["lambda_inc"]) - 1e-2) < 1e-12
        and bool(r.get("has_reached_first_milestone", False))
    ]
    l3_all_regressing_twice = bool(l3_baseline_wave2) and all(r["fail_streak"] >= 2 for r in l3_baseline_wave2)

    fallback_resume = args.fallback_resume_path.strip()
    if not fallback_resume:
        # Try to infer from same manifest (if wave1 rows are present).
        for row in manifest_rows:
            if row.get("stage") != "wave1":
                continue
            if int(row.get("layer_index", "-1")) != args.fallback_layer_index:
                continue
            if abs(float(row.get("lambda_inc", "nan")) - args.fallback_lambda_inc) > 1e-12:
                continue
            out_dir = Path(row["output_dir"])
            summary = load_json(out_dir / "train_summary.json") or {}
            fallback_resume = summary.get("checkpoint_final", "") or find_latest_checkpoint(out_dir)
            if fallback_resume:
                break

    fallback_template = None
    if l3_all_regressing_twice and fallback_resume:
        fallback_template = {
            "job_id": "k2_wave2_fallback_L4_s42_inc1e2",
            "stage": "wave2",
            "model": "EleutherAI/pythia-160m-deduped",
            "seed": args.fallback_seed,
            "layer_index": args.fallback_layer_index,
            "lambda_inc": args.fallback_lambda_inc,
            "resume_path": fallback_resume,
            "note": "Launch on GPU6 or first free GPU if both L3 baselines regress twice consecutively.",
        }

    snapshot = {
        "generated_at": now_iso(),
        "run_root": str(run_root),
        "manifest": str(manifest_path),
        "milestone_tokens": args.milestone_tokens,
        "gate_thresholds": {
            "tail_fvu_fail_threshold_l3_baseline": args.tail_fvu_fail_threshold_l3_baseline,
            "tail_incoh_fail_threshold_l3_baseline": args.tail_incoh_fail_threshold_l3_baseline,
            "dead_fraction_fail_threshold": args.dead_fraction_fail_threshold,
            "util_active_latent_floor": args.util_active_latent_floor,
            "util_entropy_floor": args.util_entropy_floor,
        },
        "job_states": job_states,
        "fail_streak_by_job": fail_streak_by_job,
        "milestone_by_job": milestone_by_job,
        "l3_all_regressing_twice": l3_all_regressing_twice,
        "fallback_template": fallback_template,
    }
    output_json.write_text(json.dumps(snapshot, indent=2), encoding="utf-8")

    lines = [
        "# K2 Wave2 Status Snapshot",
        "",
        f"- Generated: {snapshot['generated_at']}",
        f"- Run root: `{run_root}`",
        f"- Regression trigger (both L3 baselines fail twice): `{l3_all_regressing_twice}`",
        "",
        "## Job Status",
    ]
    for r in job_states:
        fail_note = ",".join(r["quality_fail_reasons"]) if r["quality_fail_reasons"] else "-"
        warn_note = ",".join(r["warnings"]) if r["warnings"] else "-"
        lines.append(
            f"- {r['job_id']}: status={r['status']} tokens={r['tokens_seen']} milestone={r['milestone']} "
            f"quality_ok={r['quality_ok']} fail_streak={r['fail_streak']} "
            f"tail100_fvu={r['tail100_fvu_total_median']:.4f} tail100_incoh={r['tail100_incoh_loss_est_median']:.4f} "
            f"slope_fvu={r['tail100_fvu_total_slope']:.6f} slope_incoh={r['tail100_incoh_loss_est_slope']:.6f} "
            f"fail={fail_note} warn={warn_note}"
        )
    lines.append("")
    lines.append("## Fallback Recommendation")
    if fallback_template is None:
        lines.append("- No fallback launch recommended at this time.")
    else:
        lines.append(
            f"- Launch fallback `{fallback_template['job_id']}` from `{fallback_template['resume_path']}` "
            f"(L{fallback_template['layer_index']}, seed={fallback_template['seed']}, "
            f"lambda_inc={fallback_template['lambda_inc']})."
        )
        lines.append(f"- Note: {fallback_template['note']}")

    output_md.write_text("\n".join(lines) + "\n", encoding="utf-8")

    print(f"[done] wrote {output_json}")
    print(f"[done] wrote {output_md}")


if __name__ == "__main__":
    main()
