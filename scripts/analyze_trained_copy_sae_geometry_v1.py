#!/usr/bin/env python3
"""No-forward geometry analysis for frozen trained-copy SAE R2 artifacts."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
from pathlib import Path
from typing import Any

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import torch

ROOT = Path(__file__).resolve().parents[1]
R2 = ROOT / "results/trained_copy_sae_capacity_v1_r2_20260813"
FINAL = R2 / "final/result.json"
OUT = ROOT / "reports/trained_copy_sae_geometry_v1"
BUDGETS_OBSERVED = (16, 32, 64, 128, 256)
BUDGETS_GEOMETRY = (16, 32, 64, 128, 160, 192, 224, 256)
METHOD_RE = re.compile(r"^sae_topk(\d+)_(.+)_budget(\d+)_seed(\d+)$")


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def canonical_hash(obj: object) -> str:
    return hashlib.sha256(json.dumps(obj, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def row_basis(matrix: np.ndarray) -> tuple[np.ndarray, np.ndarray, int, float | str]:
    a = np.asarray(matrix, dtype=np.float64)
    if a.ndim != 2:
        raise ValueError("matrix must be 2D")
    if min(a.shape) == 0:
        return np.zeros((0, a.shape[1]), dtype=np.float64), np.array([], dtype=np.float64), 0, "infinite"
    _, s, vh = np.linalg.svd(a, full_matrices=False)
    smax = float(s[0]) if len(s) else 0.0
    tol = max(a.shape) * np.finfo(np.float64).eps * smax
    rank = int(np.sum(s > tol))
    if rank == 0:
        return np.zeros((0, a.shape[1]), dtype=np.float64), s, 0, "infinite"
    condition: float | str = float(smax / s[rank - 1])
    return vh[:rank], s, rank, condition


def subspace_geometry(matrix: np.ndarray, target_basis: np.ndarray) -> dict[str, Any]:
    q, s, rank, condition = row_basis(matrix)
    p, _, prank, _ = row_basis(target_basis)
    if rank == 0 or prank == 0:
        angles: list[float] = []
        coverage = 0.0
    else:
        cross = p @ q.T
        vals = np.linalg.svd(cross, compute_uv=False)
        angles = np.arccos(np.clip(vals, 0.0, 1.0)).tolist()
        coverage = float(np.linalg.norm(cross, ord="fro") ** 2 / prank)
    return {
        "numerical_rank": rank,
        "singular_values": [float(x) for x in s],
        "minimum_nonzero_singular_value": None if rank == 0 else float(s[rank - 1]),
        "condition_number": condition,
        "principal_angles_radians": angles,
        "projection_coverage": coverage,
    }


def checkpoint_files() -> list[Path]:
    return sorted(R2.glob("checkpoints/*/sae_topk*_seed*.pt"))


def allowed_inputs() -> list[Path]:
    return [FINAL, *checkpoint_files(), *sorted(R2.glob("checkpoints/*/linear_bases.npz"))]


def assert_input(path: Path) -> None:
    resolved = path.resolve()
    if resolved not in {p.resolve() for p in allowed_inputs()}:
        raise PermissionError(f"artifact read not allowlisted: {path}")


def load_final() -> dict[str, Any]:
    assert_input(FINAL)
    return json.loads(FINAL.read_text())


def load_checkpoint(path: Path) -> dict[str, Any]:
    assert_input(path)
    return torch.load(path, map_location="cpu", weights_only=True)


def load_bases(path: Path) -> dict[str, np.ndarray]:
    assert_input(path)
    with np.load(path, allow_pickle=False) as z:
        return {k: np.asarray(z[k], dtype=np.float64) for k in z.files}


def mean(xs: list[float]) -> float | None:
    return None if not xs else float(np.mean(np.asarray(xs, dtype=np.float64)))


def analyze() -> dict[str, Any]:
    if torch.cuda.is_initialized():
        raise RuntimeError("CUDA already initialized; analysis must be CPU-only")
    final = load_final()
    behavior_groups: dict[tuple[int, str, int], list[dict[str, Any]]] = {}
    for panel in ("development", "confirmation"):
        for model, payload in final[panel].items():
            for name, rec in payload["methods"].items():
                m = METHOD_RE.match(name)
                if not m:
                    continue
                topk, selector, budget, seed = int(m[1]), m[2], int(m[3]), int(m[4])
                if budget not in BUDGETS_OBSERVED:
                    continue
                behavior_groups.setdefault((topk, selector, budget), []).append(
                    {"panel": panel, "model": int(model), "seed": seed, "record": rec}
                )

    observed: list[dict[str, Any]] = []
    for (topk, selector, budget), rows in sorted(behavior_groups.items()):
        metric = lambda e, k: [float(r["record"][e]["metrics"][k]["point"]) for r in rows]
        observed.append(
            {
                "topk": topk,
                "selector": selector,
                "budget": budget,
                "record_count": len(rows),
                "all_gate_pass_count": sum(bool(r["record"][e]["all_gates_pass"]) for r in rows for e in ("native", "matched")),
                "estimand_record_count": 2 * len(rows),
                "recovery_mean": mean(metric("native", "recovery") + metric("matched", "recovery")),
                "full_vocab_recovery_mean": mean(metric("native", "full_vocab_recovery") + metric("matched", "full_vocab_recovery")),
                "collateral_error_mean": mean(metric("native", "collateral_error") + metric("matched", "collateral_error")),
            }
        )

    geometry: list[dict[str, Any]] = []
    overlaps: list[dict[str, Any]] = []
    fits: list[dict[str, Any]] = []
    for cp_path in checkpoint_files():
        cp = load_checkpoint(cp_path)
        model = int(cp_path.parent.name)
        topk, seed = int(cp["topk"]), int(cp["seed"])
        fit_key = f"sae_topk{topk}_seed{seed}"
        fit = final["fits"][str(model)][fit_key]
        fits.append(
            {
                "model": model,
                "topk": topk,
                "seed": seed,
                "ambient_reconstruction_relative_l2": float(fit["ambient_reconstruction_relative_l2"]),
                "full_code_delta_relative_l2": float(fit["full_code_delta_relative_l2"]),
            }
        )
        decoder = cp["state_dict"]["decoder"].detach().cpu().numpy().astype(np.float64, copy=False)
        bases = load_bases(cp_path.parent / "linear_bases.npz")
        targets = {"ambient_pca_rank32": bases["ambient"][:32], "output_oracle_rank32": bases["oracle"][:32]}
        selectors = {k: [int(x) for x in v] for k, v in cp["selectors"].items()}
        for selector, order in sorted(selectors.items()):
            if sorted(order) != list(range(decoder.shape[0])):
                raise ValueError(f"selector is not a permutation: {cp_path}:{selector}")
            for budget in BUDGETS_GEOMETRY:
                subset = decoder[np.asarray(order[:budget], dtype=np.int64)]
                for target_name, target in targets.items():
                    geometry.append(
                        {
                            "model": model,
                            "topk": topk,
                            "seed": seed,
                            "selector": selector,
                            "budget": budget,
                            "target": target_name,
                            **subspace_geometry(subset, target),
                        }
                    )
        selector_names = sorted(selectors)
        for budget in BUDGETS_GEOMETRY:
            for i, a in enumerate(selector_names):
                for b in selector_names[i + 1 :]:
                    sa, sb = set(selectors[a][:budget]), set(selectors[b][:budget])
                    overlaps.append(
                        {
                            "model": model,
                            "topk": topk,
                            "seed": seed,
                            "budget": budget,
                            "selector_a": a,
                            "selector_b": b,
                            "intersection": len(sa & sb),
                            "jaccard": float(len(sa & sb) / len(sa | sb)),
                        }
                    )

    partial = [r for r in observed if r["budget"] <= 128]
    full = [r for r in observed if r["budget"] == 256]
    recon = [r["ambient_reconstruction_relative_l2"] for r in fits]
    coverage64 = [
        r["projection_coverage"]
        for r in geometry
        if r["budget"] == 64 and r["target"] == "ambient_pca_rank32"
    ]
    return {
        "schema_version": "trained_copy_sae_geometry_v1",
        "source_final_sha256": sha256(FINAL),
        "input_hashes": {str(p.relative_to(ROOT)): sha256(p) for p in allowed_inputs()},
        "observed_behavior_budgets": list(BUDGETS_OBSERVED),
        "geometry_only_budgets": list(BUDGETS_GEOMETRY),
        "unobserved_behavior_budgets": [160, 192, 224],
        "example_level_active_set_overlap_available": False,
        "feature_indices_compared_across_sae_fits": False,
        "reconstruction_scope": "one full-code fit diagnostic per model_x_sae_seed_x_topk",
        "key_findings": {
            "full_code_ambient_reconstruction_relative_l2_mean": float(np.mean(recon)),
            "full_code_ambient_reconstruction_relative_l2_min": float(np.min(recon)),
            "full_code_ambient_reconstruction_relative_l2_max": float(np.max(recon)),
            "partial_budget_estimand_pass_count": int(sum(r["all_gate_pass_count"] for r in partial)),
            "partial_budget_estimand_record_count": int(sum(r["estimand_record_count"] for r in partial)),
            "full_budget_estimand_pass_count": int(sum(r["all_gate_pass_count"] for r in full)),
            "full_budget_estimand_record_count": int(sum(r["estimand_record_count"] for r in full)),
            "ambient_pca_rank32_coverage_at_budget64_min": float(np.min(coverage64)),
            "ambient_pca_rank32_coverage_at_budget64_mean": float(np.mean(coverage64)),
            "interpretation": "registered subset spans contain the rank-32 PCA subspace by budget 64, so failure of unweighted SAE-code transplantation is not explained by absent linear span alone",
        },
        "fits": fits,
        "observed_behavior": observed,
        "geometry": geometry,
        "within_sae_selector_overlap": overlaps,
    }


def make_figures(summary: dict[str, Any], out: Path) -> list[str]:
    figdir = out / "figures"
    figdir.mkdir(parents=True, exist_ok=True)
    paths: list[str] = []
    rows = summary["observed_behavior"]
    fig, ax = plt.subplots(figsize=(7.5, 5))
    for selector in sorted({r["selector"] for r in rows}):
        s = [r for r in rows if r["selector"] == selector and r["topk"] == 16]
        by_budget: dict[int, list[dict[str, Any]]] = {}
        for r in s:
            by_budget.setdefault(r["budget"], []).append(r)
        xs = sorted(by_budget)
        ys = [float(np.mean([q["recovery_mean"] for q in by_budget[x]])) for x in xs]
        cs = [float(np.mean([q["collateral_error_mean"] for q in by_budget[x]])) for x in xs]
        ax.plot(ys, cs, marker="o", label=selector)
    ax.set_xlabel("Mean recovery (native + matched)")
    ax.set_ylabel("Mean collateral error")
    ax.set_title("SAE recovery–collateral frontier (TopK 16)")
    ax.legend(fontsize=7)
    fig.tight_layout()
    p = figdir / "recovery_collateral_pareto_topk16.png"
    fig.savefig(p, dpi=180)
    plt.close(fig)
    paths.append(str(p.relative_to(ROOT)))

    fig, ax = plt.subplots(figsize=(7.5, 5))
    geom = summary["geometry"]
    for selector in sorted({r["selector"] for r in geom}):
        s = [r for r in geom if r["selector"] == selector and r["target"] == "ambient_pca_rank32"]
        xs = sorted({r["budget"] for r in s})
        ys = [float(np.mean([r["projection_coverage"] for r in s if r["budget"] == x])) for x in xs]
        ax.plot(xs, ys, marker="o", label=selector)
    ax.set_xlabel("Feature budget")
    ax.set_ylabel("Rank-32 PCA subspace coverage")
    ax.set_ylim(0, 1.02)
    ax.set_title("Causal-subspace coverage by frozen SAE selector")
    ax.legend(fontsize=7)
    fig.tight_layout()
    p = figdir / "pca_coverage_by_budget.png"
    fig.savefig(p, dpi=180)
    plt.close(fig)
    paths.append(str(p.relative_to(ROOT)))
    return paths


def run() -> None:
    if OUT.exists():
        raise FileExistsError(f"analysis namespace exists: {OUT}")
    OUT.mkdir(parents=True)
    summary = analyze()
    summary["summary_without_figures_sha256"] = canonical_hash(summary)
    summary["figures"] = make_figures(summary, OUT)
    (OUT / "summary.json").write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n")
    manifest = {str(p.relative_to(ROOT)): sha256(p) for p in sorted(OUT.rglob("*")) if p.is_file()}
    (OUT / "MANIFEST.json").write_text(json.dumps({"items": manifest}, indent=2, sort_keys=True) + "\n")


def verify() -> None:
    saved = json.loads((OUT / "summary.json").read_text())
    current = analyze()
    expected_hash = saved["summary_without_figures_sha256"]
    if canonical_hash(current) != expected_hash:
        raise RuntimeError("analysis summary does not reproduce")
    manifest = json.loads((OUT / "MANIFEST.json").read_text())["items"]
    for rel, digest in manifest.items():
        if sha256(ROOT / rel) != digest:
            raise RuntimeError(f"analysis artifact hash mismatch: {rel}")
    if not all(math.isfinite(float(r["projection_coverage"])) for r in saved["geometry"]):
        raise RuntimeError("nonfinite geometry")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run", action="store_true")
    parser.add_argument("--verify", action="store_true")
    args = parser.parse_args()
    if args.run == args.verify:
        parser.error("choose exactly one of --run or --verify")
    run() if args.run else verify()


if __name__ == "__main__":
    main()
