#!/usr/bin/env python3
"""Create-once, analysis-only companion for proxy-control benchmark v1.

This module deliberately never imports transformers or torch and performs no model forward.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
from pathlib import Path
from typing import Any, Callable, Iterable, Mapping, Sequence

import numpy as np
import pandas as pd
from scipy.stats import rankdata, spearmanr

ROOT = Path(__file__).resolve().parents[1]
KEYS = ["model", "layer", "method", "seed", "assignment_source", "evaluation_source", "concept"]
CONTROLS = ["selectivity", "intervention_specificity", "behavioral_recovery", "aligned_behavioral_specificity", "collateral_safety"]


def canonical(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def load_json(path: Path) -> Any:
    return json.loads(path.read_text())


def write_json(path: Path, value: Any) -> None:
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, "wb") as f:
        f.write(canonical(value) + b"\n")


def stable_seed(seed: int, *parts: Any) -> int:
    text = "|".join(map(str, (seed,) + parts))
    return int.from_bytes(hashlib.sha256(text.encode()).digest()[:8], "little") % (2**32)


def verify_and_manifest(v1: Path) -> list[dict[str, Any]]:
    if not (v1 / "aggregate/COMPLETE.json").is_file():
        raise RuntimeError("v1 aggregate terminal absent")
    expected: list[Path] = []
    for complete in sorted(v1.glob("shards/*/COMPLETE.json")):
        rec = load_json(complete)
        directory = complete.parent
        declared = {
            "result.json": rec["result_sha256"],
            "metrics.jsonl": rec["metrics_sha256"],
            "component_metrics.jsonl": rec["component_metrics_sha256"],
        }
        for name, digest in declared.items():
            if sha256(directory / name) != digest:
                raise RuntimeError(f"v1 declared hash drift: {directory/name}")
        expected.extend(sorted(p for p in directory.iterdir() if p.is_file()))
    syn = load_json(v1 / "synthetic/COMPLETE.json")
    for name, key in (("result.json", "result_sha256"), ("metrics.jsonl", "metrics_sha256")):
        if sha256(v1 / "synthetic" / name) != syn[key]:
            raise RuntimeError(f"v1 synthetic hash drift: {name}")
    agg = load_json(v1 / "aggregate/COMPLETE.json")
    if sha256(v1 / "aggregate/result.json") != agg["result_sha256"]:
        raise RuntimeError("v1 aggregate hash drift")
    expected.extend(sorted((v1 / "synthetic").glob("*")))
    expected.extend(sorted((v1 / "aggregate").glob("*")))
    files = sorted({p for p in expected if p.is_file()}, key=lambda p: p.relative_to(ROOT).as_posix())
    return [{"path": p.relative_to(ROOT).as_posix(), "bytes": p.stat().st_size, "sha256": sha256(p)} for p in files]


def read_jsonl(paths: Iterable[Path]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for path in paths:
        out.extend(json.loads(line) for line in path.read_text().splitlines() if line)
    return out


def factor_cycle(component_id: str, cycles: int) -> int:
    return int(component_id.rsplit(":", 1)[1]) % cycles


def cycle_interval(values: pd.DataFrame, value: str, draws: int, seed: int) -> list[float] | None:
    finite = values[np.isfinite(values[value].astype(float))]
    if finite.empty:
        return None
    cycle_means = finite.groupby("factor_cycle")[value].mean().to_numpy(float)
    if not len(cycle_means):
        return None
    rng = np.random.default_rng(seed)
    boot = np.asarray([np.mean(cycle_means[rng.integers(0, len(cycle_means), len(cycle_means))]) for _ in range(draws)])
    return [float(x) for x in np.quantile(boot, [0.025, 0.5, 0.975])]


def finite_pairs(frame: pd.DataFrame, x: str, y: str) -> pd.DataFrame:
    return frame[np.isfinite(pd.to_numeric(frame[x], errors="coerce")) & np.isfinite(pd.to_numeric(frame[y], errors="coerce"))]


def residualized_rank_correlation(frame: pd.DataFrame, x: str, y: str) -> float:
    if len(frame) < 3:
        return float("nan")
    xr, yr = rankdata(frame[x].to_numpy(float)), rankdata(frame[y].to_numpy(float))
    methods = sorted(frame.method.unique())
    design = np.ones((len(frame), 1 + max(0, len(methods) - 1)), np.float64)
    for j, method in enumerate(methods[1:], 1):
        design[:, j] = (frame.method.to_numpy() == method).astype(float)
    rx = xr - design @ np.linalg.lstsq(design, xr, rcond=None)[0]
    ry = yr - design @ np.linalg.lstsq(design, yr, rcond=None)[0]
    if np.std(rx) < 1e-12 or np.std(ry) < 1e-12:
        return float("nan")
    return float(np.corrcoef(rx, ry)[0, 1])


def cluster_association(frame: pd.DataFrame, x: str, y: str, draws: int, seed: int,
                        fixed_method: bool) -> dict[str, Any]:
    z = finite_pairs(frame, x, y)
    clusters = sorted(z.model_layer.unique())
    if len(z) < 3 or not clusters:
        return {"rho": None, "cluster_bootstrap_ci": None, "rows": int(len(z)), "clusters": len(clusters), "method_fixed_effect": fixed_method}
    by_cluster = {cluster: z[z.model_layer == cluster] for cluster in clusters}
    estimator: Callable[[pd.DataFrame], float]
    if fixed_method:
        estimator = lambda q: residualized_rank_correlation(q, x, y)
    else:
        estimator = lambda q: float(spearmanr(q[x], q[y]).statistic) if len(q) >= 3 else float("nan")
    point = estimator(z)
    rng = np.random.default_rng(seed)
    boot: list[float] = []
    for _ in range(draws):
        chosen = rng.choice(clusters, len(clusters), replace=True)
        sample = pd.concat([by_cluster[c] for c in chosen], ignore_index=True)
        value = estimator(sample)
        if np.isfinite(value):
            boot.append(value)
    ci = [float(v) for v in np.quantile(boot, [0.025, 0.5, 0.975])] if boot else None
    return {"rho": point if np.isfinite(point) else None, "cluster_bootstrap_ci": ci,
            "rows": int(len(z)), "clusters": len(clusters), "method_fixed_effect": fixed_method}


def weighted_bin_summary(c: pd.DataFrame, bins: Sequence[float], methods: Sequence[str]) -> pd.DataFrame:
    eligible = c[(c.behavior_eligible == True) & (c.patch_norm_ratio >= bins[0]) & (c.patch_norm_ratio < bins[-1])].copy()  # noqa: E712
    eligible["norm_bin"] = pd.cut(eligible.patch_norm_ratio, bins=bins, right=False, labels=False)
    output: list[dict[str, Any]] = []
    for concept, sub in eligible.groupby("concept"):
        counts = sub.groupby(["method", "norm_bin"]).size().unstack(fill_value=0).reindex(index=methods, fill_value=0)
        common = [b for b in counts.columns if bool((counts[b] > 0).all())]
        if not common:
            continue
        target = counts[common].min(axis=0).to_numpy(float)
        target /= target.sum()
        for method in methods:
            m = sub[sub.method == method]
            record: dict[str, Any] = {"concept": concept, "method": method, "common_bins": len(common),
                                      "rows": int(len(m[m.norm_bin.isin(common)]))}
            for metric in ("behavioral_recovery", "aligned_behavioral_specificity", "collateral_kl"):
                means = m[m.norm_bin.isin(common)].groupby("norm_bin")[metric].mean().reindex(common).to_numpy(float)
                record[metric] = float(np.sum(target * means))
            output.append(record)
    result = pd.DataFrame(output)
    if not result.empty:
        result["pareto_recovery_kl"] = False
        for concept, indices in result.groupby("concept").groups.items():
            for i in indices:
                dominated = any((result.loc[j, "behavioral_recovery"] >= result.loc[i, "behavioral_recovery"] and
                                 result.loc[j, "collateral_kl"] <= result.loc[i, "collateral_kl"] and
                                 (result.loc[j, "behavioral_recovery"] > result.loc[i, "behavioral_recovery"] or
                                  result.loc[j, "collateral_kl"] < result.loc[i, "collateral_kl"])) for j in indices if j != i)
                result.loc[i, "pareto_recovery_kl"] = not dominated
    return result


def save_figures(out: Path, assoc: pd.DataFrame, metrics: pd.DataFrame, pareto: pd.DataFrame) -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    show = assoc[(assoc.analysis == "learned_only") & assoc.proxy.isin(["probe_recovery", "geometric_stability"])]
    fig, ax = plt.subplots(figsize=(10, 5))
    labels, vals, lo, hi = [], [], [], []
    for _, row in show.iterrows():
        if row.rho is None or not isinstance(row.cluster_bootstrap_ci, list):
            continue
        labels.append(f"{row.proxy}\n→ {row.control}")
        vals.append(row.rho); lo.append(row.rho-row.cluster_bootstrap_ci[0]); hi.append(row.cluster_bootstrap_ci[2]-row.rho)
    ax.errorbar(range(len(vals)), vals, yerr=[lo, hi], fmt="o", capsize=3)
    ax.axhline(0, color="black", lw=0.8); ax.set_xticks(range(len(labels)), labels, rotation=45, ha="right")
    ax.set_ylabel("Spearman rho (model/layer cluster CI)"); ax.set_title("V1 learned-only proxy associations")
    fig.tight_layout(); fig.savefig(out / "proxy_associations.png", dpi=180); plt.close(fig)

    stage_order = ["early", "middle", "late"]
    g = metrics.groupby("stage")[["probe_recovery", "leakage", "geometric_stability", "behavioral_recovery", "collateral_kl"]].mean().reindex(stage_order)
    fig, axes = plt.subplots(1, 2, figsize=(10, 4))
    axes[0].plot(stage_order, g.probe_recovery, marker="o", label="probe recovery")
    axes[0].plot(stage_order, g.leakage, marker="o", label="leakage")
    axes[0].plot(stage_order, g.geometric_stability, marker="o", label="CKA")
    axes[0].legend(); axes[0].set_title("Encoding and geometry with depth")
    axes[1].plot(stage_order, g.behavioral_recovery, marker="o", label="behavioral recovery")
    axes[1].plot(stage_order, g.collateral_kl, marker="o", label="collateral KL")
    axes[1].legend(); axes[1].set_title("Potency and collateral change")
    fig.tight_layout(); fig.savefig(out / "depth_tradeoff.png", dpi=180); plt.close(fig)

    if not pareto.empty:
        concepts = sorted(pareto.concept.unique())
        fig, axes = plt.subplots(1, len(concepts), figsize=(5 * len(concepts), 4), squeeze=False)
        for ax, concept in zip(axes[0], concepts):
            q = pareto[pareto.concept == concept]
            for _, row in q.iterrows():
                ax.scatter(row.collateral_kl, row.behavioral_recovery, marker="*" if row.pareto_recovery_kl else "o")
                ax.annotate(row.method, (row.collateral_kl, row.behavioral_recovery), fontsize=7)
            ax.set_title(concept); ax.set_xlabel("norm-standardized collateral KL"); ax.set_ylabel("behavioral recovery")
        fig.tight_layout(); fig.savefig(out / "patch_norm_pareto.png", dpi=180); plt.close(fig)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default="configs/proxy_control_benchmark_v1_analysis/run.json")
    ap.add_argument("--output")
    args = ap.parse_args()
    cfg_path = ROOT / args.config
    cfg = load_json(cfg_path)
    v1 = ROOT / cfg["v1_root"]
    out = Path(args.output) if args.output else ROOT / cfg["output_root"]
    if not out.is_absolute():
        out = ROOT / out
    if out.exists():
        raise FileExistsError(out)
    out.mkdir(parents=True)

    manifest = verify_and_manifest(v1)
    write_json(out / "V1_IMPORT_MANIFEST.json", {"schema_version": "proxy_control_v1_import_manifest",
               "files": manifest, "manifest_sha256": hashlib.sha256(canonical(manifest)).hexdigest()})
    rows = read_jsonl(sorted(v1.glob("shards/*/metrics.jsonl")))
    components = read_jsonl(sorted(v1.glob("shards/*/component_metrics.jsonl")))
    m = pd.DataFrame(rows)
    c = pd.DataFrame(components)
    learned = set(cfg["learned_methods"]); linear = set(cfg["linear_methods"])
    m["proxy_class"] = np.where(m.method.isin(learned), "learned", "linear")
    m["stage"] = m.layer.map({1: "early", 2: "early", 6: "middle", 12: "middle", 10: "late", 22: "late"})
    c["factor_cycle"] = c.component_id.apply(lambda x: factor_cycle(x, int(cfg["factor_cycles"])))
    c["aligned_behavioral_specificity"] = c.behavioral_specificity.astype(float) * np.sign(c.full_logodds_effect.astype(float))
    c["collateral_safety"] = -c.collateral_kl.astype(float)

    aligned_rows: list[dict[str, Any]] = []
    for key, group in c.groupby(KEYS, dropna=False):
        finite = group.aligned_behavioral_specificity.dropna().to_numpy(float)
        rec = dict(zip(KEYS, key))
        rec.update({"aligned_behavioral_specificity": float(np.median(finite)) if len(finite) else None,
                    "factor_cycle_mean": float(np.mean(finite)) if len(finite) else None,
                    "factor_cycle_sensitivity_ci": cycle_interval(group, "aligned_behavioral_specificity", int(cfg["bootstrap_draws"]), stable_seed(cfg["seed"], *key)),
                    "factor_cycles": int(group.factor_cycle.nunique()),
                    "interpretation": "POSTHOC_FACTOR_CYCLE_SENSITIVITY_NOT_INDEPENDENT_COMPONENT_INFERENCE"})
        aligned_rows.append(rec)
    aligned = pd.DataFrame(aligned_rows)
    m = m.merge(aligned[KEYS + ["aligned_behavioral_specificity"]], on=KEYS, how="left", validate="one_to_one")
    m["collateral_safety"] = -m.collateral_kl.astype(float)

    proxies = {"reconstruction_quality": -m.reconstruction_fvu, "sparsity": -m.sparsity,
               "probe_recovery": m.probe_recovery, "geometric_stability": m.geometric_stability}
    for name, values in proxies.items():
        m[name] = values
    association_rows: list[dict[str, Any]] = []
    analyses = [("learned_only", m[m.proxy_class == "learned"], False),
                ("linear_only", m[m.proxy_class == "linear"], False),
                ("method_fixed_effect_all", m, True)]
    for analysis, frame, fixed in analyses:
        for proxy in proxies:
            for control in CONTROLS:
                rec = cluster_association(frame, proxy, control, int(cfg["bootstrap_draws"]), stable_seed(cfg["seed"], analysis, proxy, control), fixed)
                association_rows.append({"analysis": analysis, "proxy": proxy, "control": control, **rec})
    associations = pd.DataFrame(association_rows)

    group_cols = ["proxy_class", "method", "concept", "model", "layer", "stage", "assignment_source", "evaluation_source", "seed"]
    summary_metrics = ["reconstruction_fvu", "sparsity", "probe_recovery", "leakage", "selectivity", "intervention_specificity",
                       "behavioral_recovery", "aligned_behavioral_specificity", "collateral_kl", "behavior_eligible_fraction", "geometric_stability"]
    stratified = m.groupby(group_cols, dropna=False)[summary_metrics].mean().reset_index()
    pareto = weighted_bin_summary(c, cfg["patch_norm_bins"], sorted(learned | linear))

    branch = m[m.method.isin(["k2_equal", "k2_asymmetric", "k2_swapped"])].copy()
    branch["target_branch"] = branch.assignment_detail.apply(lambda x: x.get("target_branch") if isinstance(x, dict) else None)
    sizes = {"k2_asymmetric": {0: 8, 1: 24}, "k2_swapped": {0: 24, 1: 8}, "k2_equal": {0: 16, 1: 16}}
    branch["target_topk"] = branch.apply(lambda r: sizes[r.method][int(r.target_branch)], axis=1)
    branch["target_is_larger"] = branch.apply(lambda r: bool(r.target_topk == max(sizes[r.method].values()) and len(set(sizes[r.method].values())) > 1), axis=1)
    pivot = branch.pivot_table(index=["model", "layer", "method", "seed", "assignment_source"], columns="concept", values="target_branch", aggfunc="first").dropna()
    pivot["all_concepts_same_branch"] = pivot.nunique(axis=1) == 1
    source_pivot = branch.pivot_table(index=["model", "layer", "method", "seed", "concept"], columns="assignment_source", values="target_branch", aggfunc="first").dropna()
    source_pivot["same_across_assignment_sources"] = source_pivot.nunique(axis=1) == 1
    branch_summary = []
    for method, group in branch.groupby("method"):
        branch_summary.append({"method": method, "rows": int(len(group)), "branch1_fraction": float(group.target_branch.mean()),
            "larger_branch_fraction": float(group.target_is_larger.mean()),
            "global_identity_fraction": float(pivot.loc[pivot.index.get_level_values("method") == method, "all_concepts_same_branch"].mean()),
            "cross_source_identity_fraction": float(source_pivot.loc[source_pivot.index.get_level_values("method") == method, "same_across_assignment_sources"].mean())})

    for name, frame in (("sign_aligned_sensitivity.csv", aligned), ("associations.csv", associations),
                        ("stratified_metrics.csv", stratified), ("patch_norm_standardized_pareto.csv", pareto)):
        frame.to_csv(out / name, index=False, float_format="%.12g")
    write_json(out / "branch_capacity.json", {"schema_version": "proxy_control_v1_branch_capacity_analysis", "methods": branch_summary})
    save_figures(out, associations, m, pareto)

    learned_assoc = associations[associations.analysis == "learned_only"]
    lookup = {(r.proxy, r.control): r for _, r in learned_assoc.iterrows()}
    stage = m.groupby("stage")[["probe_recovery", "leakage", "selectivity", "geometric_stability", "behavioral_recovery", "aligned_behavioral_specificity", "collateral_kl"]].mean().to_dict("index")
    result = {"schema_version": "proxy_control_v1_analysis_companion_result", "status": "ANALYSIS_ONLY_COMPLETE",
        "v1_namespace_preserved": True, "new_model_forwards": 0, "metric_rows": len(m), "component_rows": len(c),
        "model_layer_clusters": int(m.model_layer.nunique()), "factor_cycle_warning": "POSTHOC_EIGHT_CYCLE_SENSITIVITY_NOT_INDEPENDENT_SUPPORT",
        "learned_associations": {f"{p}|{q}": {"rho": lookup[(p,q)].rho if np.isfinite(lookup[(p,q)].rho) else None,
            "ci": lookup[(p,q)].cluster_bootstrap_ci} for p in ("probe_recovery", "geometric_stability") for q in ("behavioral_recovery", "aligned_behavioral_specificity", "collateral_safety")},
        "stage_means": stage, "branch_capacity": branch_summary,
        "config_sha256": sha256(cfg_path), "v1_import_manifest_sha256": sha256(out / "V1_IMPORT_MANIFEST.json")}
    write_json(out / "result.json", result)
    products = [p for p in out.iterdir() if p.is_file() and p.name != "COMPLETE.json"]
    write_json(out / "COMPLETE.json", {"status": "COMPLETE", "files": {p.name: sha256(p) for p in sorted(products)}})
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
