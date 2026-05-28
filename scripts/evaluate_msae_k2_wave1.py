#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
import math
from pathlib import Path


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Evaluate K2 wave1 runs and produce promotion decision")
    p.add_argument("--run_root", required=True)
    p.add_argument("--manifest", default="run_manifest.tsv")
    p.add_argument("--output_json", default="k2_wave1_decision.json")
    p.add_argument("--output_md", default="k2_wave1_decision.md")
    p.add_argument("--wave1_target_tokens", type=int, default=100_000_000)
    p.add_argument("--wave2_target_tokens", type=int, default=1_000_000_000)
    p.add_argument("--dead_fraction_fail_threshold", type=float, default=0.60)
    return p.parse_args()


def finite(x: float) -> bool:
    return math.isfinite(x)


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
        summary = None
        if summary_path.exists():
            summary = json.loads(summary_path.read_text(encoding="utf-8"))
        jobs.append({"manifest": r, "summary": summary})

    eval_rows = []
    for j in jobs:
        m = j["manifest"]
        s = j["summary"]
        status = m.get("status", "")
        ok = status == "done" and s is not None
        tokens_seen = int(s.get("tokens_seen", 0)) if s else 0
        pos_dead = float(s.get("pos_dead_fraction_final", float("nan"))) if s else float("nan")
        content_dead = float(s.get("content_dead_fraction_final", float("nan"))) if s else float("nan")
        throughput = float(s.get("throughput_tok_s", float("nan"))) if s else float("nan")
        reached = tokens_seen >= int(0.95 * args.wave1_target_tokens)
        stable = (
            ok
            and reached
            and finite(pos_dead)
            and finite(content_dead)
            and pos_dead < args.dead_fraction_fail_threshold
            and content_dead < args.dead_fraction_fail_threshold
            and finite(throughput)
            and throughput > 0.0
        )
        eval_rows.append(
            {
                "job_id": m["job_id"],
                "status": status,
                "layer_index": int(m["layer_index"]),
                "seed": int(m["seed"]),
                "lambda_inc": float(m["lambda_inc"]),
                "tokens_seen": tokens_seen,
                "reached_target": reached,
                "stable": stable,
                "pos_dead_fraction_final": pos_dead,
                "content_dead_fraction_final": content_dead,
                "throughput_tok_s": throughput,
                "final_checkpoint": s.get("checkpoint_final", "") if s else "",
            }
        )

    # Promotion rules
    l3_baselines = [
        r for r in eval_rows if r["layer_index"] == 3 and abs(r["lambda_inc"] - 1e-2) < 1e-12
    ]
    l3_baselines_stable = [r for r in l3_baselines if r["stable"]]
    l4_baseline = [
        r for r in eval_rows if r["layer_index"] == 4 and abs(r["lambda_inc"] - 1e-2) < 1e-12
    ]
    no_inc = [r for r in eval_rows if abs(r["lambda_inc"]) < 1e-12]

    promote = []
    # Default: promote both L3 baseline seeds
    for r in l3_baselines:
        if r["stable"]:
            promote.append(r)

    # Fallback rule: if any L3 baseline unstable, promote L4 fallback if stable
    l3_has_unstable = any(not r["stable"] for r in l3_baselines)
    if l3_has_unstable:
        for r in l4_baseline:
            if r["stable"]:
                promote.append(r)

    # Keep no-inc control if stable
    for r in no_inc:
        if r["stable"]:
            promote.append(r)

    # Deduplicate by job_id
    promote_by_id = {r["job_id"]: r for r in promote}
    promote = [promote_by_id[k] for k in sorted(promote_by_id.keys())]

    decision = {
        "run_root": str(run_root),
        "wave1_target_tokens": args.wave1_target_tokens,
        "wave2_target_tokens": args.wave2_target_tokens,
        "dead_fraction_fail_threshold": args.dead_fraction_fail_threshold,
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
        "",
        "## Job Outcomes",
    ]
    for r in eval_rows:
        lines.append(
            f"- {r['job_id']}: status={r['status']} stable={r['stable']} "
            f"tokens_seen={r['tokens_seen']} pos_dead={r['pos_dead_fraction_final']:.4f} "
            f"content_dead={r['content_dead_fraction_final']:.4f} throughput={r['throughput_tok_s']:.1f}"
        )
    lines.append("")
    lines.append("## Promotion Recommendation (Wave2)")
    if not promote:
        lines.append("- No runs met promotion criteria; investigate stability and relaunch wave1.")
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
