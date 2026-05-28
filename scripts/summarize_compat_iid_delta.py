#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
from collections import defaultdict
from pathlib import Path


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Summarize v5-like IID compatibility sweep deltas")
    p.add_argument("--v6_run_root", required=True)
    p.add_argument("--compat_run_root", required=True)
    p.add_argument("--v5_run_root", default="")
    p.add_argument("--output_md", required=True)
    return p.parse_args()


def read_rows(path: Path) -> list[dict[str, str]]:
    with open(path, "r", encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f, delimiter="\t"))


def to_float(x: str, default: float = float("nan")) -> float:
    try:
        return float(x)
    except Exception:
        return default


def group_mean(rows: list[dict[str, str]], layer: int, rank: int) -> float:
    vals = [to_float(r["raw_pos_auc"]) for r in rows if int(r["layer_index"]) == layer and int(r["rank"]) == rank]
    if not vals:
        return float("nan")
    return sum(vals) / len(vals)


def group_std(rows: list[dict[str, str]], layer: int, rank: int) -> float:
    vals = [to_float(r["raw_pos_auc"]) for r in rows if int(r["layer_index"]) == layer and int(r["rank"]) == rank]
    if len(vals) <= 1:
        return 0.0
    m = sum(vals) / len(vals)
    return (sum((v - m) ** 2 for v in vals) / len(vals)) ** 0.5


def main() -> None:
    args = parse_args()

    v6_rows_all = read_rows(Path(args.v6_run_root) / "aggregate_results.tsv")
    compat_rows_all = read_rows(Path(args.compat_run_root) / "aggregate_results.tsv")
    v5_rows_all = []
    if args.v5_run_root:
        p = Path(args.v5_run_root) / "aggregate_results.tsv"
        if p.exists():
            v5_rows_all = read_rows(p)

    v6_p160_all = [
        r for r in v6_rows_all if r["model"] == "EleutherAI/pythia-160m-deduped"
    ]
    v6_p160_iid = [r for r in v6_p160_all if r.get("split_mode", "") == "iid"]
    compat_p160_iid = [
        r for r in compat_rows_all
        if r["model"] == "EleutherAI/pythia-160m-deduped" and r.get("split_mode", "") == "iid"
    ]
    v5_p160 = [r for r in v5_rows_all if r.get("model", "") == "EleutherAI/pythia-160m-deduped"]

    lines = [
        "# v5-Compatible IID vs v6 Balanced-IID Compatibility",
        "",
        "This report decomposes observed raw position AUC differences into:",
        "1. **Data-regime effect** (balanced-manifest IID vs v5-like single-corpus IID at matched seeds/ranks).",
        "2. **Seed/split-composition effect** (v6 mixed all-splits estimate vs v6 IID estimate).",
        "",
    ]

    for layer in [3, 4]:
        lines.append(f"## Layer {layer}")
        lines.append("")
        for rank in [8, 16, 32]:
            m_v6_iid = group_mean(v6_p160_iid, layer, rank)
            s_v6_iid = group_std(v6_p160_iid, layer, rank)
            m_comp = group_mean(compat_p160_iid, layer, rank)
            s_comp = group_std(compat_p160_iid, layer, rank)
            m_v6_mixed = group_mean(v6_p160_all, layer, rank)
            s_v6_mixed = group_std(v6_p160_all, layer, rank)
            data_regime_effect = m_v6_iid - m_comp
            split_comp_effect = m_v6_mixed - m_v6_iid
            lines.append(
                f"- r{rank}: "
                f"v6_iid={m_v6_iid:.4f}±{s_v6_iid:.4f}, "
                f"compat_iid={m_comp:.4f}±{s_comp:.4f}, "
                f"v6_mixed={m_v6_mixed:.4f}±{s_v6_mixed:.4f}, "
                f"data_regime_effect={data_regime_effect:+.4f}, "
                f"split_composition_effect={split_comp_effect:+.4f}"
            )
        lines.append("")

    if v5_p160:
        lines.append("## Historical v5 Reference (context only)")
        lines.append("")
        for layer in [3, 4]:
            for rank in [8, 16, 32]:
                vals = [to_float(r["raw_pos_auc"]) for r in v5_p160 if int(r["layer_index"]) == layer and int(r["rank"]) == rank]
                if vals:
                    m = sum(vals) / len(vals)
                    lines.append(f"- v5 L{layer} r{rank}: mean_raw_pos_auc={m:.4f} (n={len(vals)})")
        lines.append("")

    lines.append("## Interpretation")
    lines.append("")
    lines.append(
        "Use `data_regime_effect` as the direct estimate of balanced-manifest vs v5-like IID shift at matched seeds. "
        "Use `split_composition_effect` to quantify the additional shift introduced when pooling IID with holdout regimes."
    )

    out = Path(args.output_md)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"[done] wrote {out}")


if __name__ == "__main__":
    main()
