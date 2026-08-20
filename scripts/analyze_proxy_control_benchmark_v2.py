#!/usr/bin/env python3
"""Create-only cached analysis companion for proxy-control benchmark v2.

This module intentionally imports no transformer, Torch, checkpoint, or training code.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CONFIG = ROOT / "configs/proxy_control_benchmark_v2_analysis/run.json"


def canonical(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def load_json(path: Path) -> Any:
    return json.loads(path.read_text())


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text().splitlines() if line]


def exclusive_bytes(path: Path, value: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, "wb") as stream:
        stream.write(value)


def exclusive_json(path: Path, value: Any) -> None:
    exclusive_bytes(path, canonical(value) + b"\n")


def exclusive_csv(path: Path, frame: pd.DataFrame) -> None:
    exclusive_bytes(path, frame.to_csv(index=False, lineterminator="\n", float_format="%.12g").encode())


def verify_inputs(cfg: Mapping[str, Any]) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    root = ROOT / cfg["input_root"]
    fixed = {
        root / "aggregate/result.json": cfg["aggregate_result_sha256"],
        root / "aggregate/COMPLETE.json": cfg["aggregate_complete_sha256"],
        root / "synthetic/result.json": cfg["synthetic_result_sha256"],
        root / "synthetic/PASS.json": cfg["synthetic_pass_sha256"],
        ROOT / cfg["freeze"]: cfg["freeze_sha256"],
    }
    manifest: list[dict[str, Any]] = []
    for path, expected in fixed.items():
        observed = sha256(path)
        if observed != expected:
            raise RuntimeError(f"frozen input drift: {path}: {observed} != {expected}")
        manifest.append({"path": path.relative_to(ROOT).as_posix(), "bytes": path.stat().st_size, "sha256": observed})
    aggregate = load_json(root / "aggregate/result.json")
    complete = load_json(root / "aggregate/COMPLETE.json")
    if complete.get("status") != "COMPLETE" or complete.get("result_sha256") != sha256(root / "aggregate/result.json"):
        raise RuntimeError("aggregate terminal lineage failure")
    expected_shards = sorted((root / "shards").glob("*"))
    if len(expected_shards) != 9:
        raise RuntimeError(f"expected nine shards, found {len(expected_shards)}")
    for directory in expected_shards:
        terminal = load_json(directory / "COMPLETE.json")
        for name, key in (("result.json", "result_sha256"), ("metrics.jsonl", "metrics_sha256"),
                          ("component_metrics.jsonl", "component_metrics_sha256")):
            path = directory / name
            if sha256(path) != terminal[key]:
                raise RuntimeError(f"shard lineage failure: {path}")
        for path in (directory / "COMPLETE.json", directory / "result.json", directory / "metrics.jsonl",
                     directory / "component_metrics.jsonl"):
            manifest.append({"path": path.relative_to(ROOT).as_posix(), "bytes": path.stat().st_size, "sha256": sha256(path)})
    failures = list(root.glob("**/TECHNICAL_FAIL.json")) + list(root.glob("**/FAIL.json")) + list(root.glob("**/BLOCKED_BY_SYNTHETIC_GATE.json"))
    if failures:
        raise RuntimeError(f"failure terminal present: {failures[0]}")
    return aggregate, sorted(manifest, key=lambda row: row["path"])


def ci_bound(value: Any, index: int) -> float:
    return float(value[index]) if isinstance(value, list) and len(value) == 3 else float("nan")


def add_gate_flags(frame: pd.DataFrame, thresholds: Mapping[str, float]) -> pd.DataFrame:
    out = frame.copy()
    out["eligibility_pass"] = out.behavior_eligible_fraction >= float(thresholds["minimum_eligibility"])
    out["recovery_pass"] = out.behavioral_recovery_block_ci.map(lambda x: ci_bound(x, 0)) > float(thresholds["minimum_recovery_ci_lower"])
    out["specificity_pass"] = out.behavioral_specificity_block_ci.map(lambda x: ci_bound(x, 0)) > float(thresholds["minimum_specificity_ci_lower"])
    out["collateral_pass"] = out.collateral_kl_block_ci.map(lambda x: ci_bound(x, 2)) < float(thresholds["maximum_collateral_ci_upper"])
    out["joint_row_pass"] = out[["eligibility_pass", "recovery_pass", "specificity_pass", "collateral_pass"]].all(axis=1)
    return out


def nondominated(frame: pd.DataFrame, potency: str, damage: str) -> pd.Series:
    values = frame[[potency, damage]].to_numpy(np.float64)
    keep = np.ones(len(frame), dtype=bool)
    for i, (p, d) in enumerate(values):
        if not np.isfinite([p, d]).all():
            keep[i] = False
            continue
        dominates = (values[:, 0] >= p) & (values[:, 1] <= d) & ((values[:, 0] > p) | (values[:, 1] < d))
        if np.any(dominates):
            keep[i] = False
    return pd.Series(keep, index=frame.index)


def named_hierarchical(aggregate: Mapping[str, Any]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for row in aggregate["hierarchical_endpoint_summaries"]:
        key = "|".join((row["method"], row["concept"], row["metric"]))
        out[key] = {"point": row["point"], "ci": row["ci"], "models": row["models"],
                    "blocks": row["blocks"], "finite_draws": row["finite_draws"]}
    return out


def named_associations(aggregate: Mapping[str, Any]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for row in aggregate["associations"]:
        key = "|".join((row["analysis"], row["proxy"], row["control"]))
        out[key] = {"rho": row.get("rho"), "ci": row.get("ci"), "rows": row.get("rows"), "clusters": row.get("clusters")}
    return out


def save_figure(path: Path, build: Any) -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    if path.exists():
        raise FileExistsError(path)
    fig = build(plt)
    fig.savefig(path, dpi=180, bbox_inches="tight", metadata={"Software": "MSAE cached analysis"})
    plt.close(fig)


def analyze(config_path: Path, output_override: Path | None = None) -> dict[str, Any]:
    cfg = load_json(config_path)
    aggregate, manifest = verify_inputs(cfg)
    input_root = ROOT / cfg["input_root"]
    output = output_override if output_override is not None else ROOT / cfg["output_root"]
    if output.exists():
        raise FileExistsError(f"analysis namespace exists: {output}")
    output.mkdir(parents=True)

    metric_rows: list[dict[str, Any]] = []
    component_rows: list[dict[str, Any]] = []
    for directory in sorted((input_root / "shards").glob("*")):
        metric_rows.extend(read_jsonl(directory / "metrics.jsonl"))
        component_rows.extend(read_jsonl(directory / "component_metrics.jsonl"))
    metrics = pd.DataFrame(metric_rows)
    components = pd.DataFrame(component_rows)
    controlled = add_gate_flags(metrics[metrics.panel_kind == "controlled"].copy(), cfg["thresholds"])
    natural = metrics[metrics.panel_kind == "naturalistic"].copy()
    controlled["stage"] = controlled.layer.astype(str).map(cfg["stage_map"])
    natural["stage"] = natural.layer.astype(str).map(cfg["stage_map"])

    gates = []
    gate_columns = ["eligibility_pass", "recovery_pass", "specificity_pass", "collateral_pass", "joint_row_pass"]
    for (method, concept), group in controlled.groupby(["method", "concept"], sort=True):
        for gate in gate_columns:
            gates.append({"method": method, "concept": concept, "gate": gate,
                          "passes": int(group[gate].sum()), "rows": int(len(group)),
                          "fraction": float(group[gate].mean())})
    gate_frame = pd.DataFrame(gates)

    hierarchical = pd.DataFrame(aggregate["hierarchical_endpoint_summaries"])
    points = hierarchical.pivot_table(index=["method", "concept"], columns="metric", values="point").reset_index()
    points["recovery_pareto"] = nondominated(points, "behavioral_recovery", "collateral_kl")
    points["specificity_pareto"] = nondominated(points, "behavioral_specificity", "collateral_kl")

    depth_metrics = ["probe_recovery", "selectivity", "intervention_specificity", "behavioral_recovery",
                     "behavioral_specificity", "collateral_kl"]
    depth = controlled.groupby(["proxy_class", "stage"], sort=False)[depth_metrics].mean().reset_index()
    depth["stage"] = pd.Categorical(depth.stage, ["early", "middle", "late"], ordered=True)
    depth = depth.sort_values(["proxy_class", "stage"])

    k2 = controlled[controlled.method.isin(["k2_equal", "k2_asymmetric", "k2_swapped"])].copy()
    k2["target_branch"] = k2.assignment_detail.map(lambda row: int(row["target_branch"]))
    k2["larger_branch_selected"] = k2.apply(
        lambda row: None if row.method == "k2_equal" else bool(row.target_branch == (1 if row.method == "k2_asymmetric" else 0)), axis=1)
    k2_assign = k2.groupby(["method", "concept", "target_branch"], dropna=False).size().rename("assignments").reset_index()
    k2_larger = k2[k2.method != "k2_equal"].groupby(["method", "concept"]).larger_branch_selected.mean().rename("larger_branch_fraction").reset_index()
    k2_specificity = hierarchical[(hierarchical.metric == "intervention_specificity") & hierarchical.method.str.startswith("k2_")][
        ["method", "concept", "point", "ci"]].rename(columns={"point": "intervention_specificity"})
    k2_summary = k2_assign.merge(k2_larger, on=["method", "concept"], how="left").merge(k2_specificity, on=["method", "concept"], how="left")

    strat_columns = ["model", "layer", "stage", "method", "seed", "proxy_class", "assignment_source", "evaluation_source", "concept",
        "behavior_eligible_fraction", "probe_recovery", "leakage", "selectivity", "intervention_specificity",
        "behavioral_recovery", "behavioral_specificity", "collateral_kl", *gate_columns]
    stratified = controlled[strat_columns].sort_values(["model", "layer", "method", "concept", "assignment_source", "seed"])
    natural_summary = natural.groupby(["method", "model", "stage"], dropna=False)[
        ["behavior_eligible_fraction", "behavioral_recovery", "behavioral_specificity", "collateral_kl"]].mean().reset_index()
    natural_overall = natural.groupby("method")[["behavior_eligible_fraction", "behavioral_recovery", "behavioral_specificity", "collateral_kl"]].mean().reset_index()

    exclusive_csv(output / "gate_failure_waterfall.csv", gate_frame)
    exclusive_csv(output / "pareto_points.csv", points)
    exclusive_csv(output / "depth_tradeoff.csv", depth)
    exclusive_csv(output / "k2_capacity_following.csv", k2_summary)
    exclusive_csv(output / "stratified_metrics.csv", stratified)
    exclusive_csv(output / "naturalistic_descriptive.csv", natural_summary)
    exclusive_csv(output / "naturalistic_overall.csv", natural_overall)
    exclusive_csv(output / "associations.csv", pd.DataFrame(aggregate["associations"]))
    exclusive_json(output / "IMPORT_MANIFEST.json", {"schema_version": "proxy_control_v2_analysis_import_manifest", "files": manifest})

    method_order = sorted(gate_frame.method.unique())
    gate_order = gate_columns
    def gate_plot(plt: Any) -> Any:
        fig, ax = plt.subplots(figsize=(12, 5.8)); width = 0.15; x = np.arange(len(method_order))
        collapsed = gate_frame.groupby(["method", "gate"]).fraction.mean().unstack()
        for j, gate in enumerate(gate_order): ax.bar(x + (j - 2) * width, collapsed.loc[method_order, gate], width, label=gate.replace("_pass", ""))
        ax.set_xticks(x, method_order, rotation=35, ha="right"); ax.set_ylim(0, 1.02); ax.set_ylabel("Fraction of controlled summaries passing")
        ax.legend(ncol=3, fontsize=8); ax.set_title("Frozen gate waterfall (joint pass is zero for every method)"); return fig
    save_figure(output / "gate_failure_waterfall.png", gate_plot)

    colors = {"context": "#4C78A8", "lexical": "#F58518", "relative_position": "#54A24B"}
    def pareto_plot(potency: str, title: str) -> Any:
        def build(plt: Any) -> Any:
            fig, ax = plt.subplots(figsize=(8.5, 6.2))
            for _, row in points.iterrows():
                ax.scatter(row.collateral_kl, row[potency], color=colors[row.concept], marker="*" if row[f"{potency.split('_')[1]}_pareto"] else "o", s=85 if row[f"{potency.split('_')[1]}_pareto"] else 35)
                if row[f"{potency.split('_')[1]}_pareto"] or row.method in {"behavior_gradient_oracle", "k2_equal"}:
                    ax.annotate(f"{row.method}\n{row.concept}", (row.collateral_kl, row[potency]), fontsize=6, xytext=(3, 3), textcoords="offset points")
            ax.axvline(float(cfg["thresholds"]["maximum_collateral_ci_upper"]), color="black", linestyle="--", linewidth=1, label="frozen collateral cap")
            ax.set_xlabel("Collateral KL (lower is safer)"); ax.set_ylabel(potency.replace("_", " ").title()); ax.set_title(title); ax.legend(fontsize=8); return fig
        return build
    save_figure(output / "recovery_collateral_pareto.png", pareto_plot("behavioral_recovery", "Potency–damage frontier"))
    save_figure(output / "specificity_collateral_pareto.png", pareto_plot("behavioral_specificity", "Sham-specific behavior–damage frontier"))

    def depth_plot(plt: Any) -> Any:
        fig, axes = plt.subplots(1, 2, figsize=(10.5, 4.2), sharex=True)
        for proxy_class, group in depth.groupby("proxy_class"):
            axes[0].plot(group.stage.astype(str), group.behavioral_recovery, marker="o", label=proxy_class)
            axes[1].plot(group.stage.astype(str), group.collateral_kl, marker="o", label=proxy_class)
        axes[0].set_ylabel("Behavioral recovery"); axes[1].set_ylabel("Collateral KL")
        for ax in axes: ax.set_xlabel("Stage"); ax.legend(); ax.grid(alpha=.2)
        fig.suptitle("Potency and collateral damage increase with depth"); return fig
    save_figure(output / "depth_tradeoff.png", depth_plot)

    def k2_plot(plt: Any) -> Any:
        fig, axes = plt.subplots(1, 2, figsize=(11, 4.2))
        larger_plot = k2_larger.pivot(index="concept", columns="method", values="larger_branch_fraction")
        larger_plot.plot.bar(ax=axes[0], ylim=(0, 1.05), legend=True); axes[0].set_ylabel("Larger branch selected"); axes[0].set_title("Capacity-following assignments")
        spec_plot = k2_specificity.pivot(index="concept", columns="method", values="intervention_specificity")
        spec_plot.plot.bar(ax=axes[1], legend=True); axes[1].axhline(0, color="black", linewidth=1); axes[1].set_ylabel("Intervention specificity"); axes[1].set_title("All K2 variants remain nonspecific")
        fig.tight_layout(); return fig
    save_figure(output / "k2_capacity_following.png", k2_plot)

    def natural_plot(plt: Any) -> Any:
        fig, ax = plt.subplots(figsize=(10, 4.5)); ordered = natural_overall.sort_values("behavior_eligible_fraction")
        ax.bar(ordered.method, ordered.behavior_eligible_fraction, color="#72B7B2"); ax.axhline(float(cfg["thresholds"]["minimum_eligibility"]), color="black", linestyle="--", label="frozen eligibility floor")
        ax.set_ylim(0, 1); ax.set_ylabel("Natural-QA eligibility"); ax.tick_params(axis="x", rotation=35); ax.legend(); ax.set_title("Natural endpoint is descriptive: every method remains below eligibility floor"); return fig
    save_figure(output / "naturalistic_eligibility.png", natural_plot)

    joint_rows = int(controlled.joint_row_pass.sum())
    method_decisions = pd.DataFrame(aggregate["method_decisions"])
    result = {
        "schema_version": "proxy_control_benchmark_v2_analysis_result",
        "status": "ANALYSIS_ONLY_COMPLETE",
        "input_aggregate_sha256": sha256(input_root / "aggregate/result.json"),
        "import_manifest_sha256": sha256(output / "IMPORT_MANIFEST.json"),
        "new_model_forwards": 0,
        "new_training_runs": 0,
        "frozen_scores_modified": False,
        "formal": {"metric_rows": int(aggregate["metric_rows"]), "controlled_metric_rows": int(len(controlled)),
                   "naturalistic_metric_rows": int(len(natural)), "method_decisions": int(len(method_decisions)),
                   "passing_method_decisions": int(method_decisions.passes.sum()), "joint_controlled_row_passes": joint_rows,
                   "model_layer_clusters": int(aggregate["model_layer_clusters"])},
        "gate_pass_counts": {gate: int(controlled[gate].sum()) for gate in gate_columns},
        "hierarchical": named_hierarchical(aggregate),
        "associations": named_associations(aggregate),
        "depth_means": {f"{row.proxy_class}|{row.stage}": {metric: float(getattr(row, metric)) for metric in depth_metrics}
                        for row in depth.itertuples(index=False)},
        "k2": {"asymmetric_larger_branch_fraction": float(k2_larger[k2_larger.method == "k2_asymmetric"].larger_branch_fraction.mean()),
               "swapped_larger_branch_fraction": float(k2_larger[k2_larger.method == "k2_swapped"].larger_branch_fraction.mean())},
        "naturalistic": {"eligibility_mean": float(natural.behavior_eligible_fraction.mean()),
                         "frozen_eligibility_floor": float(cfg["thresholds"]["minimum_eligibility"]),
                         "eligible": bool(natural.behavior_eligible_fraction.mean() >= float(cfg["thresholds"]["minimum_eligibility"]))},
        "interpretation_guard": "POSITIVE_POTENCY_WITHOUT_ANY_JOINT_REPLICATED_COLLATERAL_SAFE_PASS",
    }
    exclusive_json(output / "result.json", result)
    products = sorted(p for p in output.iterdir() if p.name != "COMPLETE.json")
    terminal = {"schema_version": "proxy_control_benchmark_v2_analysis_complete", "status": "COMPLETE",
                "result_sha256": sha256(output / "result.json"), "files":
                [{"path": p.name, "bytes": p.stat().st_size, "sha256": sha256(p)} for p in products]}
    exclusive_json(output / "COMPLETE.json", terminal)
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default=str(DEFAULT_CONFIG.relative_to(ROOT)))
    parser.add_argument("--output")
    args = parser.parse_args()
    output = Path(args.output) if args.output else None
    result = analyze(ROOT / args.config, output)
    print(json.dumps(result["formal"], indent=2))


if __name__ == "__main__":
    main()
