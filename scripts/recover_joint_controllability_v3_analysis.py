#!/usr/bin/env python3
"""Analysis-only recovery for the v3 aggregate serialization failure.

This program imports only JSON/JSONL artifacts.  It has no model, tokenizer, CUDA, or training path.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
from typing import Any, Sequence

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SOURCE = ROOT / "results/joint_controllability_benchmark_v3_20260808"
DEFAULT_OUTPUT = ROOT / "results/joint_controllability_benchmark_v3_analysis_recovery_20260808"
CONFIG = ROOT / "configs/joint_controllability_benchmark_v3/run.json"
FREEZE = ROOT / "configs/joint_controllability_benchmark_v3/FREEZE.json"
ORIGINAL_LOG = ROOT / "reports/provenance/joint_controllability_benchmark_v3/aggregate.log"
ORIGINAL_SCRIPT = ROOT / "scripts/joint_controllability_benchmark_v3.py"
INPUT_MANIFEST = ROOT / "configs/joint_controllability_benchmark_v3/RECOVERY_INPUTS.json"
INPUT_MANIFEST_SHA256 = "1ef9e3394b9d9e319e1e0f0c3e26ff98c0d8188f709679d04ec0ad07999804a3"


def sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def loadj(path: Path) -> Any:
    return json.loads(path.read_text())


def stable(seed: int, *parts: Any) -> int:
    material = "|".join(map(str, (seed,) + parts)).encode()
    return int.from_bytes(hashlib.sha256(material).digest()[:8], "little") % (2**32)


def block_interval(values: Sequence[float], blocks: Sequence[str], draws: int, seed: int) -> list[float] | None:
    """Exact pure-NumPy transcription of v2.block_interval at the bound recovery hash."""
    x = np.asarray(values, np.float64); b = np.asarray(blocks)
    finite = np.isfinite(x); x, b = x[finite], b[finite]
    if not len(x):
        return None
    unique = sorted(set(b.tolist()))
    means = np.asarray([np.mean(x[b == key]) for key in unique], np.float64)
    rng = np.random.default_rng(seed)
    boot = np.asarray([np.mean(means[rng.integers(0, len(means), len(means))]) for _ in range(int(draws))])
    return [float(v) for v in np.quantile(boot, [0.025, 0.5, 0.975])]


def native(value: Any) -> Any:
    """Recursively convert NumPy scalars without changing numeric values."""
    if isinstance(value, np.generic):
        return value.item()
    if isinstance(value, dict):
        return {str(k): native(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [native(v) for v in value]
    return value


def exclusive_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    payload = json.dumps(native(value), sort_keys=True, separators=(",", ":"), allow_nan=False)
    with os.fdopen(fd, "w") as f:
        f.write(payload + "\n")


def stage(spec: dict[str, Any], layer: int) -> str:
    layers = list(spec["layers"])
    if len(layers) == 1:
        return "middle"
    return "early" if layer == layers[0] else ("late" if layer == layers[-1] else "middle")


def tree_inventory(source: Path) -> list[dict[str, Any]]:
    return [{"path": p.relative_to(ROOT).as_posix(), "bytes": p.stat().st_size, "sha256": sha(p)} for p in sorted(source.rglob("*")) if p.is_file()]


def require_exact_tree(actual: Sequence[dict[str, Any]], expected: Sequence[dict[str, Any]]) -> None:
    if list(actual) != list(expected):
        raise RuntimeError("preserved v3 source-tree membership or content drift")


def verify_lineage(source: Path) -> tuple[dict[str, Any], dict[str, Any], list[dict[str, Any]], dict[str, str], list[dict[str, Any]]]:
    if sha(INPUT_MANIFEST) != INPUT_MANIFEST_SHA256:
        raise RuntimeError("reviewed recovery-input manifest drift")
    manifest = loadj(INPUT_MANIFEST)
    for record in manifest["files"]:
        path = ROOT / record["path"]
        if not path.is_file() or path.stat().st_size != record["bytes"] or sha(path) != record["sha256"]:
            raise RuntimeError(f"recovery input drift: {record['path']}")
    source_prefix = source.relative_to(ROOT).as_posix() + "/"
    expected_tree = [record for record in manifest["files"] if record["path"].startswith(source_prefix)]
    expected_tree.sort(key=lambda row: row["path"])
    require_exact_tree(tree_inventory(source), expected_tree)
    cfg = loadj(CONFIG)
    freeze = loadj(FREEZE)
    if freeze["config_sha256"] != sha(CONFIG):
        raise RuntimeError("frozen v3 config hash mismatch")
    inventory = {row["path"]: row["sha256"] for row in freeze["candidate_inventory"]}
    script_rel = ORIGINAL_SCRIPT.relative_to(ROOT).as_posix()
    if inventory.get(script_rel) != sha(ORIGINAL_SCRIPT):
        raise RuntimeError("frozen v3 aggregation code drift")
    if source.resolve() != DEFAULT_SOURCE.resolve():
        raise RuntimeError("recovery source must be the preserved v3 namespace")
    failed_result = source / "aggregate/result.json"
    if not failed_result.is_file() or failed_result.stat().st_size != 0:
        raise RuntimeError("original zero-byte result lineage is absent")
    if "Object of type bool_ is not JSON serializable" not in ORIGINAL_LOG.read_text():
        raise RuntimeError("original serialization failure not found")
    expected = [f"{m['key']}_layer{layer}" for m in cfg["models"] for layer in m["layers"]]
    rows: list[dict[str, Any]] = []
    shard_hashes: dict[str, str] = {}
    expected_shards = manifest["expected_shards"]
    actual_shards = {p.name for p in (source / "shards").iterdir() if p.is_dir()}
    if actual_shards != set(expected_shards):
        raise RuntimeError("missing or extra v3 worker shard")
    for name in expected:
        complete_path = source / "shards" / name / "COMPLETE.json"
        metrics_path = source / "shards" / name / "metrics.jsonl"
        complete = loadj(complete_path)
        pinned = expected_shards[name]
        if sha(complete_path) != pinned["complete_sha256"] or complete.get("schema_version") != "joint_control_v3_worker_complete" or complete["status"] != "COMPLETE" or complete["freeze_sha256"] != sha(FREEZE):
            raise RuntimeError(f"invalid completion lineage: {name}")
        if complete["model"] != pinned["model"] or int(complete["layer"]) != int(pinned["layer"]) or int(complete["rows"]) != int(pinned["rows"]):
            raise RuntimeError(f"invalid completion identity: {name}")
        if complete["hook_qa_sha256"] != pinned["hook_qa_sha256"] or complete["metrics_sha256"] != pinned["metrics_sha256"] or sha(metrics_path) != pinned["metrics_sha256"]:
            raise RuntimeError(f"worker metric drift: {name}")
        shard_hashes[name] = complete["metrics_sha256"]
        shard_rows = [json.loads(line) for line in metrics_path.read_text().splitlines() if line]
        if len(shard_rows) != pinned["rows"] or any(r.get("schema_version") != "joint_control_v3_component_metric" or r["model"] != pinned["model"] or int(r["layer"]) != int(pinned["layer"]) for r in shard_rows):
            raise RuntimeError(f"worker row identity drift: {name}")
        rows.extend(shard_rows)
    if len(rows) != int(manifest["expected_metric_rows"]):
        raise RuntimeError("unexpected total metric row count")
    return cfg, freeze, rows, shard_hashes, tree_inventory(source)


def interval(rows: Sequence[dict[str, Any]], name: str, draws: int, seed: int) -> list[float] | None:
    vals = [float(r[name]) for r in rows if r[name] is not None]
    blocks = [r["component_block"] for r in rows if r[name] is not None]
    return block_interval(vals, blocks, draws, seed)


def recover(source: Path, output: Path) -> None:
    if source.resolve() != DEFAULT_SOURCE.resolve():
        raise RuntimeError("source namespace is fixed")
    if output.resolve() != DEFAULT_OUTPUT.resolve():
        raise RuntimeError("output namespace is fixed and must remain separate from v3")
    if output.exists():
        raise FileExistsError(f"recovery namespace exists: {output}")
    cfg, freeze, rows, shard_hashes, before_tree = verify_lineage(source)
    groups: dict[tuple[Any, ...], list[dict[str, Any]]] = {}
    for row in rows:
        key = (row["method"], row["budget"], row["model"], row["layer"], row["fit_source"], row["eval_source"])
        groups.setdefault(key, []).append(row)
    analysis = cfg["analysis"]
    summaries: list[dict[str, Any]] = []
    for key, group in sorted(groups.items()):
        eligibility = np.mean([r["behavior_eligible"] for r in group])
        recovery = interval(group, "behavioral_recovery", analysis["bootstrap_draws"], stable(cfg["seed"], *key, "behavioral_recovery"))
        specificity = interval(group, "signed_sham_specificity", analysis["bootstrap_draws"], stable(cfg["seed"], *key, "signed_sham_specificity"))
        collateral = interval(group, "collateral_kl", analysis["bootstrap_draws"], stable(cfg["seed"], *key, "collateral_kl"))
        ratios = [abs(float(r["natural_sham_effect"])) / max(abs(float(r["full_effect"])), float(analysis["epsilon"])) for r in group]
        blocks = [r["component_block"] for r in group]
        sham = block_interval(ratios, blocks, analysis["bootstrap_draws"], stable(cfg["seed"], *key, "natural_sham_fraction"))
        sham_ok = sham is not None and sham[1] <= analysis["maximum_sham_fraction"] and sham[2] < analysis["maximum_sham_fraction_ci"]
        passed = (
            eligibility >= analysis["minimum_effect_eligibility"]
            and sham_ok
            and recovery is not None and recovery[0] > analysis["minimum_recovery_ci_lower"]
            and specificity is not None and specificity[0] > analysis["minimum_specificity_ci_lower"]
            and collateral is not None and collateral[2] < analysis["maximum_collateral_ci_upper"]
        )
        summaries.append({"method": key[0], "budget": key[1], "model": key[2], "layer": key[3], "fit_source": key[4], "eval_source": key[5], "eligibility": eligibility, "natural_sham_fraction_ci": sham, "recovery_ci": recovery, "specificity_ci": specificity, "collateral_ci": collateral, "passes": passed})
    decisions = []
    for method in sorted({r["method"] for r in rows}):
        for budget in cfg["budgets"]:
            for stage_name in ("early", "middle", "late"):
                passing_models = []
                for model in cfg["models"]:
                    cells = [s for s in summaries if s["method"] == method and s["budget"] == budget and s["model"] == model["key"] and stage(model, s["layer"]) == stage_name]
                    if {s["eval_source"] for s in cells if s["passes"]} == set(cfg["task"]["sources"]):
                        passing_models.append(model["key"])
                decisions.append({"method": method, "budget": budget, "stage": stage_name, "passing_model_families": passing_models, "passes": len(passing_models) >= analysis["minimum_replicating_model_families"]})
    manifest = loadj(INPUT_MANIFEST)
    if len(summaries) != int(manifest["expected_summary_cells"]):
        raise RuntimeError("unexpected summary-cell count")
    after_compute_tree = tree_inventory(source)
    if before_tree != after_compute_tree:
        raise RuntimeError("v3 namespace changed during recovery computation")
    result = {
        "schema_version": "joint_control_v3_analysis_recovery_v1",
        "status": "ANALYSIS_RECOVERED_REQUIRES_CLAIM_REVIEW",
        "recovery_is_scientific_retry": False,
        "new_model_forwards": False,
        "training_authorized": False,
        "within_corpus_transfer": True,
        "cross_domain_replication": False,
        "metric_rows": len(rows),
        "summaries": summaries,
        "method_decisions": decisions,
        "passing_method_decisions": sum(bool(x["passes"]) for x in decisions),
        "lineage": {
            "source_namespace": source.relative_to(ROOT).as_posix(),
            "source_freeze_sha256": sha(FREEZE),
            "source_config_sha256": sha(CONFIG),
            "source_script_sha256": sha(ORIGINAL_SCRIPT),
            "source_aggregate_log_sha256": sha(ORIGINAL_LOG),
            "source_failed_result_sha256": sha(source / "aggregate/result.json"),
            "source_failed_result_bytes": 0,
            "original_failure": "TypeError: Object of type bool_ is not JSON serializable",
            "worker_metric_sha256": shard_hashes,
            "recovery_input_manifest_sha256": sha(INPUT_MANIFEST),
            "source_tree_before": before_tree,
            "source_tree_after_compute": after_compute_tree,
        },
    }
    exclusive_json(output / "result.json", result)
    final_tree = tree_inventory(source)
    require_exact_tree(final_tree, before_tree)
    final_tree_sha256 = hashlib.sha256(json.dumps(final_tree, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    exclusive_json(output / "COMPLETE.json", {"status": "COMPLETE", "result_sha256": sha(output / "result.json"), "source_freeze_sha256": sha(FREEZE), "source_tree_final_sha256": final_tree_sha256, "metric_rows": len(rows)})
    print(json.dumps(native({"status": "COMPLETE", "output": str(output), "metric_rows": len(rows), "passing_method_decisions": result["passing_method_decisions"]}), indent=2))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    recover(args.source, args.output)


if __name__ == "__main__":
    main()
