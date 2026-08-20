#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
from collections import defaultdict
from pathlib import Path
from typing import Any

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

ROOT = Path(os.environ.get("MSAE_ROOT", Path(__file__).resolve().parents[1])).resolve()
CAP = ROOT / "results/capacity_controller_diagnostic_v1_20260810r5/final/result.json"
EXT = ROOT / "results/trained_copy_external_v1_20260810r5/final/result.json"
OUT = ROOT / "results/capacity_external_validity_v1_r5_analysis_20260810"
EXPECTED = {
    "capacity": "4b6ecaee10b0c19130b07a445df58e60f84fb6e960889dcdadc0925d3290a927",
    "external": "ae94256e519e5a65fdca585b6787b93d816bff285ff37fe7797772a662f9c83f",
}


def sha(path: Path) -> str:
    h = hashlib.sha256(path.read_bytes()).hexdigest()
    return h


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    cols = sorted({k for row in rows for k in row})
    with path.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cols); w.writeheader(); w.writerows(rows)


def collect(cap: dict[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for instance, stages in cap["instances"].items():
        for stage, rec in stages.items():
            for name, method in rec["methods"].items():
                for estimand in ("native", "matched"):
                    result = method[estimand]
                    row: dict[str, Any] = {
                        "instance": instance, "stage": stage, "name": name,
                        "family": method["family"], "seed": method["seed"],
                        "rank": method["rank"], "estimand": estimand,
                        "all_gates_pass": method["all_gates_pass"],
                    }
                    for metric, value in result.get("metrics", {}).items():
                        row[metric] = value["point"]
                    rows.append(row)
    return rows


def mean(rows: list[dict[str, Any]], field: str) -> float:
    vals = [float(x[field]) for x in rows if field in x]
    return float(np.mean(vals)) if vals else float("nan")


def plot_rank(rows: list[dict[str, Any]], path: Path) -> None:
    fams = ["paired_linear", "reduced_rank_regression", "random", "unpaired_pca"]
    fig, axes = plt.subplots(1, 3, figsize=(12, 3.6))
    for ax, metric in zip(axes, ["recovery", "sham_specificity", "collateral_error"]):
        for prefix in fams:
            pts = []
            for rank in [4, 8, 16, 32, 64]:
                q = [r for r in rows if r["estimand"] == "native" and r["family"] == f"{prefix}_rank{rank}"]
                if q: pts.append((rank, mean(q, metric)))
            if pts: ax.plot(*zip(*pts), marker="o", label=prefix.replace("_", " "))
        ax.set_xscale("log", base=2); ax.set_xticks([4,8,16,32,64]); ax.get_xaxis().set_major_formatter(matplotlib.ticker.ScalarFormatter())
        ax.set_title(metric.replace("_", " ")); ax.set_xlabel("global rank"); ax.grid(alpha=.25)
    axes[0].legend(fontsize=7); fig.tight_layout(); fig.savefig(path, dpi=180); plt.close(fig)


def plot_paired(rows: list[dict[str, Any]], path: Path) -> None:
    fams = ["closed_form_linear_full64", "paired_linear_rank16", "unpaired_pca_rank64", "random_rank64"]
    metrics = ["recovery", "sham_specificity", "full_vocab_recovery", "collateral_error"]
    vals = [[mean([r for r in rows if r["estimand"] == "native" and r["family"] == f], m) for m in metrics] for f in fams]
    x=np.arange(len(metrics)); width=.18; fig,ax=plt.subplots(figsize=(9,4))
    for i,(f,v) in enumerate(zip(fams,vals)):ax.bar(x+(i-1.5)*width,v,width,label=f.replace("_"," "))
    ax.set_xticks(x, [m.replace("_","\n") for m in metrics]); ax.axhline(0,color="black",lw=.6); ax.legend(fontsize=7); ax.set_title("Paired versus unpaired controls"); fig.tight_layout();fig.savefig(path,dpi=180);plt.close(fig)


def plot_pareto(rows: list[dict[str, Any]], path: Path) -> None:
    q=[r for r in rows if r["estimand"]=="native" and "recovery" in r]
    fams=sorted(set(r["family"] for r in q)); fig=plt.figure(figsize=(7,5));ax=fig.add_subplot(111,projection="3d")
    for f in fams:
        z=[r for r in q if r["family"]==f];ax.scatter(mean(z,"recovery"),mean(z,"sham_specificity"),mean(z,"collateral_error"),s=22,label=f)
    ax.set_xlabel("recovery");ax.set_ylabel("specificity");ax.set_zlabel("collateral");ax.set_title("Recovery–specificity–collateral frontier");fig.tight_layout();fig.savefig(path,dpi=180);plt.close(fig)


def plot_potency(rows: list[dict[str, Any]], path: Path) -> None:
    q=[r for r in rows if r["estimand"]=="native" and "recovery" in r];fig,ax=plt.subplots(figsize=(7,5))
    for f in sorted(set(r["family"] for r in q)):
        z=[r for r in q if r["family"]==f];ax.scatter(mean(z,"recovery"),mean(z,"full_vocab_recovery"),s=25,label=f)
    ax.axvline(.7,ls="--",lw=.7,color="gray");ax.axhline(.7,ls="--",lw=.7,color="gray");ax.set_xlabel("target recovery");ax.set_ylabel("full-vocabulary recovery");ax.set_title("Target potency is not full-state restoration");fig.tight_layout();fig.savefig(path,dpi=180);plt.close(fig)


def plot_nonlinear(rows: list[dict[str, Any]], path: Path) -> None:
    q=[r for r in rows if r["estimand"]=="matched" and r["family"] in {"target_nonlinear_rank16","target_nonlinear_rank32"}]
    fig,ax=plt.subplots(figsize=(8,4)); labels=[];vals=[];colors=[]
    for r in q:
        labels.append(f"{r['instance'][-2:]}-{r['stage'][0]}-s{str(r['seed'])[-1:]}-r{r['rank']}");vals.append(r.get("sham_specificity",np.nan));colors.append("#2ca02c" if r["all_gates_pass"] else "#d62728")
    ax.bar(np.arange(len(vals)),vals,color=colors);ax.axhline(.5,ls="--",color="black",lw=.8);ax.set_xticks(np.arange(len(vals)),labels,rotation=90,fontsize=6);ax.set_ylabel("matched sham specificity");ax.set_title("Nonlinear rank-16 instability versus rank-32");fig.tight_layout();fig.savefig(path,dpi=180);plt.close(fig)


def plot_external(ext: dict[str, Any], path: Path) -> None:
    labels=[]; exact=[]; first=[];second=[];alt=[]
    for stage in ["development","confirmation"]:
        for seed,r in sorted(ext[stage].items()):
            labels.append(f"{stage[0]}-{seed}");exact.append(r["metrics"]["recovery"]["point"]);first.append(r["incomplete_masks"]["first_half"]["recovery_point"]);second.append(r["incomplete_masks"]["second_half"]["recovery_point"]);alt.append(r["incomplete_masks"]["alternating"]["recovery_point"])
    x=np.arange(len(labels));w=.2;fig,ax=plt.subplots(figsize=(8,4));
    for i,(name,v) in enumerate([("exact",exact),("first half",first),("second half",second),("alternating",alt)]):ax.bar(x+(i-1.5)*w,v,w,label=name)
    ax.set_xticks(x,labels);ax.set_ylabel("recovery");ax.set_title("Exact versus incomplete trained-copy controllers");ax.legend(fontsize=7);fig.tight_layout();fig.savefig(path,dpi=180);plt.close(fig)


def generate() -> dict[str, Any]:
    if sha(CAP)!=EXPECTED["capacity"] or sha(EXT)!=EXPECTED["external"]:raise RuntimeError("R5 result lineage drift")
    if OUT.exists():raise FileExistsError(OUT)
    OUT.mkdir(parents=True)
    cap=json.loads(CAP.read_text());ext=json.loads(EXT.read_text());rows=collect(cap);write_csv(OUT/"capacity_method_rows.csv",rows)
    ext_rows=[]
    for stage in ["development","confirmation"]:
        for seed,r in ext[stage].items():
            z={"stage":stage,"seed":seed,"all_gates_pass":r["all_gates_pass"],"eligible_total":r["eligible_total"]}
            z.update({k:v["point"] for k,v in r["metrics"].items()});z.update({f"mask_{k}":v["recovery_point"] for k,v in r["incomplete_masks"].items()});ext_rows.append(z)
    write_csv(OUT/"external_rows.csv",ext_rows)
    plots={
      "joint_control_vs_global_rank.png":lambda p:plot_rank(rows,p),
      "paired_vs_unpaired.png":lambda p:plot_paired(rows,p),
      "recovery_specificity_collateral_pareto.png":lambda p:plot_pareto(rows,p),
      "potency_vs_full_vocabulary.png":lambda p:plot_potency(rows,p),
      "nonlinear_seed_sensitivity.png":lambda p:plot_nonlinear(rows,p),
      "exact_vs_incomplete_trained_copy.png":lambda p:plot_external(ext,p),
    }
    for name,fn in plots.items():fn(OUT/name)
    summary={"schema_version":"capacity_external_validity_v1_r5_analysis","status":"ANALYSIS_COMPLETE","new_model_forwards":0,"source_hashes":EXPECTED,"capacity_rows":len(rows),"external_rows":len(ext_rows),"figures":sorted(plots),"headline":{"global_paired_rank8_all":cap["family_pass_all_instances_both_panels"]["paired_linear_rank8"],"global_paired_rank16_all":cap["family_pass_all_instances_both_panels"]["paired_linear_rank16"],"unpaired_pca_rank64_all":cap["family_pass_all_instances_both_panels"]["unpaired_pca_rank64"],"target_nonlinear_rank16_all":cap["family_pass_all_instances_both_panels"]["target_nonlinear_rank16"],"target_nonlinear_rank32_all":cap["family_pass_all_instances_both_panels"]["target_nonlinear_rank32"],"external_all_seeds_both_panels":ext["all_seeds_both_panels_pass"]}}
    (OUT/"summary.json").write_text(json.dumps(summary,indent=2,sort_keys=True)+"\n")
    manifest={"schema_version":"capacity_external_validity_v1_r5_analysis_manifest","source_hashes":EXPECTED,"files":[]}
    for p in sorted(OUT.iterdir()):
        if p.name!="MANIFEST.json":manifest["files"].append({"path":p.name,"bytes":p.stat().st_size,"sha256":sha(p)})
    (OUT/"MANIFEST.json").write_text(json.dumps(manifest,indent=2,sort_keys=True)+"\n")
    return verify()


def verify() -> dict[str, Any]:
    if sha(CAP)!=EXPECTED["capacity"] or sha(EXT)!=EXPECTED["external"]:raise RuntimeError("R5 result lineage drift")
    m=json.loads((OUT/"MANIFEST.json").read_text())
    for r in m["files"]:
        p=OUT/r["path"]
        if not p.is_file() or p.stat().st_size!=r["bytes"] or sha(p)!=r["sha256"]:raise RuntimeError(f"analysis drift {p}")
    s=json.loads((OUT/"summary.json").read_text())
    if s["new_model_forwards"]!=0 or len(s["figures"])!=6:raise RuntimeError("analysis contract mismatch")
    return {"status":"PASS","manifest_sha256":sha(OUT/"MANIFEST.json"),"files":len(m["files"]),"figures":len(s["figures"])}


def main() -> None:
    ap=argparse.ArgumentParser();ap.add_argument("--verify",action="store_true");a=ap.parse_args();print(json.dumps(verify() if a.verify else generate(),sort_keys=True))


if __name__=="__main__":main()
