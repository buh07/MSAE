#!/usr/bin/env python3
"""Prospective controlled-natural context-retrieval joint-control benchmark v4.

No language-model, SAE, K2, dictionary, or ReFT training path exists.  Closed-form development
subspaces are evaluated only after a method-independent opened-development task gate passes.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import time
from pathlib import Path
from typing import Any, Mapping, Sequence

import numpy as np
import torch

import joint_controllability_benchmark_v3 as core
import proxy_control_benchmark_v1 as v1
import proxy_control_benchmark_v2 as v2

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = Path(__file__).resolve()
DEFAULT = ROOT / "configs/joint_controllability_benchmark_v4/run.json"
PLAN = ROOT / "PLAN_JOINT_CONTROLLABILITY_V3_RECOVERY_V4.md"
TEST = ROOT / "tests/test_joint_controllability_benchmark_v4.py"
LAUNCHER = ROOT / "scripts/launch_joint_controllability_benchmark_v4_tmux.sh"
CANDIDATE_REVIEW = ROOT / "reports/adversarial/joint_controllability_v4_candidate_review.md"


def loadj(path: Path) -> Any:
    return json.loads(path.read_text())


def sha(path: Path) -> str:
    return core.sha(path)


def native(value: Any) -> Any:
    if isinstance(value, np.generic):
        return value.item()
    if isinstance(value, dict):
        return {str(k): native(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [native(v) for v in value]
    return value


def exjson(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(native(value), sort_keys=True, separators=(",", ":"), allow_nan=False)
    temporary = path.with_name(path.name + f".tmp.{os.getpid()}.{time.time_ns()}")
    fd = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    try:
        with os.fdopen(fd, "w") as f:
            f.write(payload + "\n"); f.flush(); os.fsync(f.fileno())
        # Same-directory hard-link publication is atomic and refuses to replace an existing terminal.
        os.link(temporary, path)
        directory_fd = os.open(path.parent, os.O_RDONLY)
        try: os.fsync(directory_fd)
        finally: os.close(directory_fd)
    finally:
        temporary.unlink(missing_ok=True)


def publish_failure(path: Path, value: Any) -> None:
    try:
        exjson(path, value)
    except FileExistsError:
        pass


def atomjson(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + f".tmp.{os.getpid()}")
    tmp.write_text(json.dumps(native(value), sort_keys=True, separators=(",", ":"), allow_nan=False) + "\n")
    os.replace(tmp, path)


def writejl(path: Path, rows: Sequence[Mapping[str, Any]]) -> None:
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, "w") as f:
        for row in rows:
            f.write(json.dumps(native(dict(row)), sort_keys=True, separators=(",", ":"), allow_nan=False) + "\n")


def readjl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text().splitlines() if line]


def excluded_v3_documents(cfg: Mapping[str, Any]) -> set[str]:
    rows = readjl(ROOT / cfg["task"]["exclude_v3_rows"])
    return {str(r[name]) for r in rows for name in ("document_id", "donor_base_id", "donor_sham_id")}


def _token_ids(tokenizer: Any, text: str) -> list[int]:
    return list(tokenizer(text, add_special_tokens=False)["input_ids"])


def prepare(config: Path, output: Path | None = None) -> None:
    cfg = loadj(config)
    root = output or ROOT / cfg["runtime"]["prepared_root"]
    if root.exists() and any(root.iterdir()):
        raise FileExistsError(f"prepared namespace nonempty: {root}")
    root.mkdir(parents=True, exist_ok=True)
    tokenizers = core.load_tokenizers(cfg)
    docs = [x for x in core.corpus_documents(cfg) if x[0] not in excluded_v3_documents(cfg)]
    task = cfg["task"]
    total = len(task["sources"]) * (int(task["development_per_source"]) + int(task["test_per_source"]))
    answers = list(task["answer_words"])
    keys = list(task["key_words"])
    if len(keys) < 3 or len(answers) < 2:
        raise RuntimeError("insufficient registered keys or answers")
    rows: list[dict[str, Any]] = []
    selected_document_ids: set[str] = set()
    for document_id, document_words in docs:
        if len(rows) >= total:
            break
        if document_id in selected_document_ids:
            continue
        i = len(rows)
        answer = answers[core.stable(cfg["seed"], document_id, "answer") % len(answers)]
        contrast = answers[(answers.index(answer) + 1 + core.stable(cfg["seed"], document_id, "contrast") % (len(answers) - 1)) % len(answers)]
        q = core.stable(cfg["seed"], document_id, "key") % len(keys)
        query_key, base_key, sham_key = keys[q], keys[(q + 1) % len(keys)], keys[(q + 2) % len(keys)]
        width = int(task["natural_filler_words"])
        room = len(document_words) - width
        if room <= 0:
            continue
        start = core.stable(cfg["seed"], document_id, "filler") % (room + 1)
        filler = " ".join(document_words[start : start + width])
        template = str(task["prompt_template"])
        full = template.format(reference_key=query_key, answer=answer, filler=filler, query_key=query_key)
        base = template.format(reference_key=base_key, answer=answer, filler=filler, query_key=query_key)
        sham = template.format(reference_key=sham_key, answer=answer, filler=filler, query_key=query_key)
        # Conditions differ only in the binding key and must remain exactly length matched for every model.
        encoded = {}
        valid = True
        for model, tokenizer in tokenizers.items():
            prompts = [_token_ids(tokenizer, text) for text in (base, full, sham)]
            target = _token_ids(tokenizer, " " + answer)
            other = _token_ids(tokenizer, " " + contrast)
            if len({len(x) for x in prompts}) != 1 or len(target) != 1 or len(other) != 1 or target == other:
                valid = False
                break
            bos = [tokenizer.bos_token_id] if tokenizer.bos_token_id is not None else []
            prompts = [bos + x for x in prompts]
            if len(prompts[0]) + 1 > int(cfg["runtime"]["maximum_length"]):
                valid = False
                break
            encoded[model] = {"base_prompt_ids": prompts[0], "full_prompt_ids": prompts[1], "sham_prompt_ids": prompts[2], "continuation_ids": target, "target_id": target[0], "contrast_id": other[0]}
        if not valid:
            continue
        rows.append({"document_id": document_id, "component_block": document_id, "answer_word": answer, "contrast_word": contrast, "query_key": query_key, "base_key": base_key, "sham_key": sham_key, "filler": filler, "encoded": encoded})
        selected_document_ids.add(document_id)
    if len(rows) != total:
        raise RuntimeError(f"controlled-natural support {len(rows)} below {total}")
    assignments = [(source, split) for source in task["sources"] for split, count in (("development", task["development_per_source"]), ("test", task["test_per_source"])) for _ in range(int(count))]
    raw_rows = []
    per_model: dict[str, list[dict[str, Any]]] = {m["key"]: [] for m in cfg["models"]}
    for row, (source, split) in zip(rows, assignments, strict=True):
        component_id = f"{source}:{split}:{row['document_id'][:16]}"
        raw_rows.append({k: v for k, v in row.items() if k != "encoded"} | {"source": source, "split": split, "component_id": component_id})
        for model in per_model:
            per_model[model].append({"component_id": component_id, "component_block": row["component_block"], "source": source, "split": split, "document_id": row["document_id"], **row["encoded"][model]})
    writejl(root / "rows.jsonl", raw_rows)
    for model, model_rows in per_model.items():
        writejl(root / f"{model}.jsonl", model_rows)
    manifest = {
        "schema_version": "joint_control_v4_prescore",
        "task_label": task["task_label"],
        "dataset_fingerprint": task["fingerprint"],
        "rows": len(raw_rows),
        "unique_documents": len({r["document_id"] for r in raw_rows}),
        "development_test_disjoint": len({r["document_id"] for r in raw_rows}) == len(raw_rows),
        "v3_document_overlap": len({r["document_id"] for r in raw_rows} & excluded_v3_documents(cfg)),
        "selection_firewall": "LABEL_TOKENIZER_ONLY_NO_MODEL_FORWARD_OR_LOGIT_FILTER",
        "within_corpus_transfer": True,
        "files": {p.name: sha(p) for p in sorted(root.glob("*.jsonl"))},
    }
    exjson(root / "PRESCORE.json", manifest)
    print(json.dumps(manifest, indent=2))


def verify_prepared(cfg: Mapping[str, Any]) -> None:
    root = ROOT / cfg["runtime"]["prepared_root"]
    manifest = loadj(root / "PRESCORE.json")
    if manifest["selection_firewall"] != "LABEL_TOKENIZER_ONLY_NO_MODEL_FORWARD_OR_LOGIT_FILTER":
        raise RuntimeError("preparation firewall failure")
    if not manifest["development_test_disjoint"] or manifest["v3_document_overlap"] != 0:
        raise RuntimeError("document-disjointness failure")
    for name, digest in manifest["files"].items():
        if sha(root / name) != digest:
            raise RuntimeError(f"prepared drift: {name}")


def candidate_files(config: Path, cfg: Mapping[str, Any]) -> list[Path]:
    prepared = ROOT / cfg["runtime"]["prepared_root"]
    paths = [config.resolve(), PLAN, SCRIPT, TEST, LAUNCHER, ROOT / cfg["runtime"]["asset_manifest"], ROOT / cfg["preservation"]["closure"], ROOT / cfg["preservation"]["v3_source_freeze"], ROOT / cfg["preservation"]["v3_recovery"], ROOT / cfg["preservation"]["v3_claim_review"], ROOT / "reports/provenance/joint_controllability_benchmark_v4/deterministic_prepare.json", prepared / "PRESCORE.json", prepared / "rows.jsonl"]
    paths.extend(prepared / f"{m['key']}.jsonl" for m in cfg["models"])
    return paths


def inventory(config: Path, cfg: Mapping[str, Any]) -> list[dict[str, Any]]:
    result = []
    for path in candidate_files(config, cfg):
        if not path.is_file():
            raise RuntimeError(f"candidate absent: {path}")
        result.append({"path": path.relative_to(ROOT).as_posix(), "bytes": path.stat().st_size, "sha256": sha(path)})
    return sorted(result, key=lambda row: row["path"])


def preflight(config: Path) -> None:
    cfg = loadj(config)
    verify_prepared(cfg)
    if cfg["preservation"]["k2_training_authorized"] or cfg["preservation"]["sae_training_authorized"]:
        raise RuntimeError("training authorization drift")
    if sha(ROOT / cfg["preservation"]["closure"]) != cfg["preservation"]["closure_sha256"]:
        raise RuntimeError("architecture closure drift")
    if (ROOT / cfg["runtime"]["output_root"]).exists():
        raise RuntimeError("output namespace exists")
    if (ROOT / cfg["runtime"]["provenance_root"]).exists():
        raise RuntimeError("provenance namespace exists")
    # Reuse only the exact v3-downloaded public assets.
    core.fetch_assets(cfg)
    print(json.dumps({"status": "PASS", "candidate_files": len(inventory(config, cfg)), "training": False}, indent=2))


def freeze(config: Path) -> None:
    cfg = loadj(config)
    preflight(config)
    inv = inventory(config, cfg)
    payload = {"schema_version": "joint_control_v4_freeze", "namespace": cfg["namespace"], "config_sha256": sha(config), "candidate_inventory": inv, "candidate_inventory_sha256": hashlib.sha256(json.dumps(inv, sort_keys=True, separators=(",", ":")).encode()).hexdigest(), "v3_preserved_freeze_sha256": sha(ROOT / cfg["preservation"]["v3_source_freeze"]), "new_k2_training": False, "new_sae_training": False, "task_gate_precedes_test_inference": True, "within_corpus_transfer": True, "retry_authorized": False}
    exjson(ROOT / cfg["runtime"]["freeze"], payload)
    print(json.dumps(payload, indent=2))


def verify_freeze(config: Path, cfg: Mapping[str, Any]) -> dict[str, Any]:
    record = loadj(ROOT / cfg["runtime"]["freeze"])
    if record["config_sha256"] != sha(config) or record["candidate_inventory"] != inventory(config, cfg):
        raise RuntimeError("frozen v4 candidate drift")
    return record


def rows_for(cfg: Mapping[str, Any], model: str) -> list[dict[str, Any]]:
    return readjl(ROOT / cfg["runtime"]["prepared_root"] / f"{model}.jsonl")


def _task_gate_worker(config: Path, key: str) -> None:
    cfg = loadj(config)
    verify_freeze(config, cfg)
    spec = core.model_spec(cfg, key)
    output = ROOT / cfg["runtime"]["output_root"] / "task_gate" / key
    output.mkdir(parents=True, exist_ok=False)
    rows = [r for r in rows_for(cfg, key) if r["split"] == "development"]
    from transformers import AutoModelForCausalLM, AutoTokenizer
    device = torch.device("cuda:0")
    model = AutoModelForCausalLM.from_pretrained(spec["name"], revision=spec["revision"], local_files_only=True, torch_dtype=torch.float32).to(device).eval()
    for parameter in model.parameters():
        parameter.requires_grad_(False)
    tokenizer = AutoTokenizer.from_pretrained(spec["name"], revision=spec["revision"], local_files_only=True)
    pad = tokenizer.pad_token_id if tokenizer.pad_token_id is not None else tokenizer.eos_token_id
    # Layer is irrelevant to output behavior; use the first registered hook only to share the exact runner.
    layer = int(spec["layers"][0])
    base = core.run_panel(model, rows, "base", layer, int(spec["batch_size"]), pad, device, None, False)
    full = core.run_panel(model, rows, "full", layer, int(spec["batch_size"]), pad, device, None, False)
    sham = core.run_panel(model, rows, "sham", layer, int(spec["batch_size"]), pad, device, None, False)
    full_effect = core.logodds(full["logits"], rows) - core.logodds(base["logits"], rows)
    sham_effect = core.logodds(sham["logits"], rows) - core.logodds(base["logits"], rows)
    records = [{"schema_version": "joint_control_v4_task_gate_row", "model": key, "source": row["source"], "component_id": row["component_id"], "component_block": row["component_block"], "full_effect": float(fe), "sham_effect": float(se)} for row, fe, se in zip(rows, full_effect, sham_effect, strict=True)]
    writejl(output / "metrics.jsonl", records)
    exjson(output / "COMPLETE.json", {"schema_version": "joint_control_v4_task_gate_worker_complete", "status": "COMPLETE", "model": key, "rows": len(records), "metrics_sha256": sha(output / "metrics.jsonl"), "freeze_sha256": sha(ROOT / cfg["runtime"]["freeze"]), "gpu_uuid": "GPU-" + str(torch.cuda.get_device_properties(0).uuid)})


def task_gate_worker(config: Path, key: str) -> None:
    cfg = loadj(config)
    root = ROOT / cfg["runtime"]["output_root"] / "task_gate"
    try:
        _task_gate_worker(config, key)
    except BaseException as error:
        freeze_path = ROOT / cfg["runtime"]["freeze"]
        publish_failure(root / f"{key}_FAIL.json", {"status": "FAIL", "model": key, "error_type": type(error).__name__, "error": str(error), "freeze_sha256": sha(freeze_path) if freeze_path.is_file() else None})
        raise


def development_gate_summary(records: Sequence[Mapping[str, Any]], gate: Mapping[str, Any], seed: int) -> dict[str, Any]:
    if not records:
        raise ValueError("empty development gate cell")
    eligible = [float(r["full_effect"]) > float(gate["minimum_full_effect"]) for r in records]
    selected = [r for r, keep in zip(records, eligible, strict=True) if keep]
    eligibility = float(np.mean(eligible))
    ratios = [abs(float(r["sham_effect"])) / abs(float(r["full_effect"])) for r in selected]
    ci = v2.block_interval(ratios, [str(r["component_block"]) for r in selected], int(gate["bootstrap_draws"]), seed)
    passed = len(selected) >= int(gate["minimum_eligible_rows"]) and eligibility >= float(gate["minimum_effect_eligibility"]) and ci is not None and ci[1] <= float(gate["maximum_sham_fraction"]) and ci[2] < float(gate["maximum_sham_fraction_ci"])
    return {"eligibility": eligibility, "eligible_rows": len(selected), "sham_population": "full_effect_eligible_rows_only", "sham_fraction_ci": ci, "passes": bool(passed)}


def _task_gate_aggregate(config: Path) -> None:
    cfg = loadj(config)
    verify_freeze(config, cfg)
    root = ROOT / cfg["runtime"]["output_root"] / "task_gate"
    names = [m["key"] for m in cfg["models"]]
    started = time.monotonic()
    while not all((root / name / "COMPLETE.json").exists() for name in names):
        failures = [root / f"{name}_FAIL.json" for name in names]
        if any(path.exists() for path in failures) or time.monotonic() - started > float(cfg["runtime"]["gate_timeout_seconds"]):
            result = {"schema_version": "joint_control_v4_development_gate", "status": "FAIL", "reason": "WORKER_FAILURE_OR_TIMEOUT", "freeze_sha256": sha(ROOT / cfg["runtime"]["freeze"]), "failed_workers": [path.name for path in failures if path.exists()]}
            exjson(root / "result.json", result); exjson(root / "FAIL.json", result)
            return
        time.sleep(int(cfg["runtime"]["gate_poll_seconds"]))
    gate = cfg["development_gate"]
    summaries = []; worker_complete_sha256 = {}
    for name in names:
        complete = loadj(root / name / "COMPLETE.json")
        path = root / name / "metrics.jsonl"
        if complete.get("schema_version") != "joint_control_v4_task_gate_worker_complete" or complete.get("status") != "COMPLETE" or complete.get("model") != name or complete.get("freeze_sha256") != sha(ROOT / cfg["runtime"]["freeze"]) or int(complete.get("rows", -1)) != len(cfg["task"]["sources"]) * int(cfg["task"]["development_per_source"]) or complete["metrics_sha256"] != sha(path):
            raise RuntimeError(f"task-gate metric drift: {name}")
        worker_complete_sha256[name] = sha(root / name / "COMPLETE.json")
        records = readjl(path)
        if any(r.get("schema_version") != "joint_control_v4_task_gate_row" or r.get("model") != name for r in records):
            raise RuntimeError(f"task-gate row identity drift: {name}")
        for source in cfg["task"]["sources"]:
            rows = [r for r in records if r["source"] == source]
            summary = development_gate_summary(rows, gate, core.stable(cfg["seed"], name, source, "development_task_gate"))
            summaries.append({"model": name, "source": source, **summary})
    passed = all(bool(row["passes"]) for row in summaries)
    result = {"schema_version": "joint_control_v4_development_gate", "status": "PASS" if passed else "FAIL", "opened_development_only": True, "fresh_test_opened": False, "freeze_sha256": sha(ROOT / cfg["runtime"]["freeze"]), "worker_complete_sha256": worker_complete_sha256, "summaries": summaries}
    exjson(root / "result.json", result)
    exjson(root / ("PASS.json" if passed else "FAIL.json"), result)


def task_gate_aggregate(config: Path) -> None:
    cfg = loadj(config); root = ROOT / cfg["runtime"]["output_root"] / "task_gate"
    try:
        _task_gate_aggregate(config)
    except BaseException as error:
        freeze_path = ROOT / cfg["runtime"]["freeze"]
        record = {"schema_version": "joint_control_v4_development_gate", "status": "FAIL", "reason": "AGGREGATE_EXCEPTION", "error_type": type(error).__name__, "error": str(error), "freeze_sha256": sha(freeze_path) if freeze_path.is_file() else None}
        publish_failure(root / "FAIL.json", record)
        raise


def _synthetic(config: Path) -> None:
    cfg = loadj(config)
    verify_freeze(config, cfg)
    out = ROOT / cfg["runtime"]["output_root"] / "synthetic"
    out.mkdir(parents=True, exist_ok=False)
    pc = cfg["positive_control"]
    rng = np.random.default_rng(cfg["seed"])
    n, d, rank = int(pc["rows"]), int(pc["hidden"]), int(pc["rank"])
    basis = np.eye(d)[:rank]
    amplitude = rng.uniform(0.5, 1.5, (n, 1))
    delta = amplitude * basis[0] + rng.normal(0, 0.03, (n, d)) @ basis.T @ basis
    sham = rng.normal(0, 0.5, (n, d)); sham -= sham @ basis.T @ basis
    weight = basis[0]; full = delta @ weight
    def metrics(B: np.ndarray) -> dict[str, float]:
        actual = core.project(delta, B); nuisance = core.project(sham, B)
        recovery = np.mean((actual @ weight) / full); specificity = np.mean(((actual - nuisance) @ weight) / full)
        collateral = np.mean(np.sum(actual[:, rank:] ** 2, axis=1) / (np.sum(actual * actual, axis=1) + 1e-8))
        return {"recovery": float(recovery), "specificity": float(specificity), "collateral": float(collateral)}
    ground = metrics(basis); skyline = metrics(v1.orthonormal_rows(weight[None], rank)); q, _ = np.linalg.qr(rng.normal(size=(d, rank))); random = metrics(q.T)
    passed = ground["recovery"] >= pc["ground_recovery_min"] and ground["specificity"] >= pc["ground_specificity_min"] and ground["collateral"] <= pc["ground_collateral_max"] and skyline["recovery"] >= pc["skyline_recovery_min"] and skyline["specificity"] >= pc["skyline_specificity_min"] and abs(random["specificity"]) <= pc["random_specificity_max"]
    result = {"schema_version": "joint_control_v4_synthetic", "status": "PASS" if passed else "FAIL", "freeze_sha256": sha(ROOT / cfg["runtime"]["freeze"]), "ground": ground, "supervised_skyline": skyline, "random": random}
    exjson(out / "result.json", result); exjson(out / ("PASS.json" if passed else "FAIL.json"), result)


def synthetic(config: Path) -> None:
    cfg = loadj(config); root = ROOT / cfg["runtime"]["output_root"] / "synthetic"
    try:
        _synthetic(config)
    except BaseException as error:
        freeze_path = ROOT / cfg["runtime"]["freeze"]
        publish_failure(root / "FAIL.json", {"schema_version": "joint_control_v4_synthetic", "status": "FAIL", "reason": "EXCEPTION", "error_type": type(error).__name__, "error": str(error), "freeze_sha256": sha(freeze_path) if freeze_path.is_file() else None})
        raise


def wait_gates(cfg: Mapping[str, Any], out: Path) -> None:
    root = ROOT / cfg["runtime"]["output_root"]
    needed = [root / "synthetic/PASS.json", root / "task_gate/PASS.json"]
    failures = [root / "synthetic/FAIL.json", root / "task_gate/FAIL.json"]
    started = time.monotonic()
    while not all(path.exists() for path in needed):
        if any(path.exists() for path in failures):
            raise RuntimeError("blocked by a frozen upstream gate")
        if time.monotonic() - started > float(cfg["runtime"]["gate_timeout_seconds"]):
            raise TimeoutError("upstream gates timed out")
        atomjson(out / "WAITING.json", {"status": "WAITING_FOR_SYNTHETIC_AND_DEVELOPMENT_GATES"})
        time.sleep(int(cfg["runtime"]["gate_poll_seconds"]))
    freeze_sha = sha(ROOT / cfg["runtime"]["freeze"])
    for path in needed:
        record = loadj(path)
        if record.get("status") != "PASS" or record.get("freeze_sha256") != freeze_sha:
            raise RuntimeError(f"invalid upstream gate terminal: {path}")


def _worker(config: Path, key: str, layer: int) -> None:
    cfg = loadj(config); verify_freeze(config, cfg); spec = core.model_spec(cfg, key)
    if layer not in spec["layers"]:
        raise RuntimeError("unregistered layer")
    out = ROOT / cfg["runtime"]["output_root"] / "shards" / f"{key}_layer{layer}"
    out.mkdir(parents=True, exist_ok=False); wait_gates(cfg, out)
    core.seedall(core.stable(cfg["seed"], key, layer)); device = torch.device("cuda:0")
    rows = rows_for(cfg, key)
    from transformers import AutoModelForCausalLM, AutoTokenizer
    model = AutoModelForCausalLM.from_pretrained(spec["name"], revision=spec["revision"], local_files_only=True, torch_dtype=torch.float32).to(device).eval()
    for parameter in model.parameters(): parameter.requires_grad_(False)
    tokenizer = AutoTokenizer.from_pretrained(spec["name"], revision=spec["revision"], local_files_only=True)
    pad = tokenizer.pad_token_id if tokenizer.pad_token_id is not None else tokenizer.eos_token_id
    batch = int(spec["batch_size"])
    smoke = rows[:1]; zeros = np.zeros((1, model.config.hidden_size), np.float32)
    a = core.run_panel(model, smoke, "base", layer, 1, pad, device, None); b = core.run_panel(model, smoke, "base", layer, 1, pad, device, zeros)
    nonzero = zeros.copy(); nonzero[0, 0] = 1e-3; c = core.run_panel(model, smoke, "base", layer, 1, pad, device, nonzero)
    if not np.array_equal(a["logits"], b["logits"]) or not np.isfinite(c["logits"]).all() or np.array_equal(a["logits"], c["logits"]): raise RuntimeError("hook QA failed")
    atomjson(out / "HOOK_QA.json", {"zero_patch_exact": True, "nonzero_finite_change": True})
    base = core.run_panel(model, rows, "base", layer, batch, pad, device); full = core.run_panel(model, rows, "full", layer, batch, pad, device); sham = core.run_panel(model, rows, "sham", layer, batch, pad, device)
    devall = np.concatenate([core.subset_idx(rows, source, "development") for source in cfg["task"]["sources"]])
    gradients = np.zeros_like(base["hidden"]); gradients[devall] = core.base_gradients(model, [rows[i] for i in devall], layer, batch, pad, device)
    saes = core.load_public_saes(cfg, key, layer, device); records = []; epsilon = float(cfg["analysis"]["epsilon"]); methods = list(cfg["methods"]) + [name for name in saes if name != "public_sae_primary"]
    transfers = [(cfg["task"]["sources"][0], cfg["task"]["sources"][1]), (cfg["task"]["sources"][1], cfg["task"]["sources"][0])]
    for fit_source, eval_source in transfers:
        di = core.subset_idx(rows, fit_source, "development"); ei = core.subset_idx(rows, eval_source, "test"); rr = [rows[i] for i in ei]
        natural = full["hidden"][ei] - base["hidden"][ei]; sham_delta = sham["hidden"][ei] - base["hidden"][ei]
        full_effect = core.logodds(full["logits"][ei], rr) - core.logodds(base["logits"][ei], rr); sham_effect = core.logodds(sham["logits"][ei], rr) - core.logodds(base["logits"][ei], rr)
        for method in methods:
            if method.startswith("public_sae") or method.startswith("saebench_"):
                actual, sham_patch, proxy, l0, rank = core.public_patches(saes[method], (base["hidden"][di], full["hidden"][di], sham["hidden"][di]), (base["hidden"][ei], full["hidden"][ei], sham["hidden"][ei]), int(cfg["analysis"]["rank"]), device); proxy_name = "reconstruction_quality"
            else:
                B = core.fit_basis(method, base["hidden"][di], full["hidden"][di], sham["hidden"][di], gradients[di], cfg, core.stable(cfg["seed"], key, layer, fit_source, method)); actual = core.project(natural, B); sham_patch = core.project(sham_delta, B); rank = len(B); l0 = float(rank); proxy = float(np.sum(actual * actual) / max(np.sum(natural * natural), epsilon)); proxy_name = "captured_variance"
            for budget in cfg["budgets"]:
                actual_scaled = core.match_norm(actual, natural, budget, epsilon); sham_scaled = core.match_norm(sham_patch, natural, budget, epsilon)
                patched = core.run_panel(model, rr, "base", layer, batch, pad, device, actual_scaled, False); sham_patched = core.run_panel(model, rr, "base", layer, batch, pad, device, sham_scaled, False); removed = core.run_panel(model, rr, "full", layer, batch, pad, device, -actual_scaled, False)
                unrelated_rows = rr[1:] + rr[:1]; unrelated_base = core.run_panel(model, unrelated_rows, "base", layer, batch, pad, device, None, False); unrelated_patch = core.run_panel(model, unrelated_rows, "base", layer, batch, pad, device, actual_scaled, False)
                patch_effect = core.logodds(patched["logits"], rr) - core.logodds(base["logits"][ei], rr); sham_patch_effect = core.logodds(sham_patched["logits"], rr) - core.logodds(base["logits"][ei], rr); necessity = core.logodds(removed["logits"], rr) - core.logodds(full["logits"][ei], rr)
                eligible = full_effect > float(cfg["analysis"]["minimum_full_effect"]); denominator = np.where(np.abs(full_effect) > epsilon, full_effect, np.nan)
                recovery = np.where(eligible, patch_effect / denominator, np.nan); specificity = np.where(eligible, (patch_effect - sham_patch_effect) / denominator, np.nan); collateral = core.non_target_kl(base["logits"][ei], patched["logits"], rr); unrelated_damage = unrelated_patch["nll"] - unrelated_base["nll"]
                for j, row in enumerate(rr):
                    records.append({"schema_version": "joint_control_v4_component_metric", "model": key, "model_family": key, "layer": layer, "stage": core.stage(spec, layer), "fit_source": fit_source, "eval_source": eval_source, "component_id": row["component_id"], "component_block": row["component_block"], "method": method, "budget": float(budget), "rank": rank, "proxy_name": proxy_name, "proxy_value": proxy, "sparsity": l0, "full_effect": float(full_effect[j]), "natural_sham_effect": float(sham_effect[j]), "behavior_eligible": bool(eligible[j]), "behavioral_recovery": float(recovery[j]) if np.isfinite(recovery[j]) else None, "signed_sham_specificity": float(specificity[j]) if np.isfinite(specificity[j]) else None, "collateral_kl": float(collateral[j]), "unrelated_continuation_damage": float(unrelated_damage[j]), "necessity_effect": float(necessity[j]), "actual_patch_norm_ratio": float(np.linalg.norm(actual_scaled[j]) / max(np.linalg.norm(natural[j]), epsilon))})
    writejl(out / "metrics.jsonl", records)
    exjson(out / "COMPLETE.json", {"schema_version": "joint_control_v4_worker_complete", "status": "COMPLETE", "model": key, "layer": layer, "rows": len(records), "freeze_sha256": sha(ROOT / cfg["runtime"]["freeze"]), "hook_qa_sha256": sha(out / "HOOK_QA.json"), "metrics_sha256": sha(out / "metrics.jsonl"), "runtime": {"device": str(device), "gpu": torch.cuda.get_device_name(0), "gpu_uuid": "GPU-" + str(torch.cuda.get_device_properties(0).uuid), "torch": torch.__version__}})


def worker(config: Path, key: str, layer: int) -> None:
    cfg = loadj(config); root = ROOT / cfg["runtime"]["output_root"] / "failures"
    try:
        _worker(config, key, layer)
    except BaseException as error:
        freeze_path = ROOT / cfg["runtime"]["freeze"]
        publish_failure(root / f"{key}_layer{layer}_FAIL.json", {"status": "FAIL", "model": key, "layer": layer, "error_type": type(error).__name__, "error": str(error), "freeze_sha256": sha(freeze_path) if freeze_path.is_file() else None})
        raise


def expected_method_names(cfg: Mapping[str, Any], model: str) -> list[str]:
    names = list(cfg["methods"]); spec = core.model_spec(cfg, model); sae = spec["sae"]
    if sae["format"] == "dictionary_learning":
        names.extend("saebench_" + arch.lower() for arch in sae["architectures"] if arch != sae["primary"])
    return names


def validate_metric_grid(rows: Sequence[Mapping[str, Any]], cfg: Mapping[str, Any], prepared_rows: Sequence[Mapping[str, Any]], model: str) -> None:
    sources = list(cfg["task"]["sources"]); transfers = [(sources[0], sources[1]), (sources[1], sources[0])]
    test_ids = {source: [r["component_id"] for r in prepared_rows if r["source"] == source and r["split"] == "test"] for source in sources}
    block_by_component = {r["component_id"]: r["component_block"] for r in prepared_rows if r["split"] == "test"}
    expected = {(fit, evaluation, method, float(budget), component) for fit, evaluation in transfers for method in expected_method_names(cfg, model) for budget in cfg["budgets"] for component in test_ids[evaluation]}
    observed = [(r["fit_source"], r["eval_source"], r["method"], float(r["budget"]), r["component_id"]) for r in rows]
    blocks_valid = all(r.get("component_block") == block_by_component.get(r["component_id"]) for r in rows)
    if len(observed) != len(set(observed)) or set(observed) != expected or not blocks_valid:
        raise RuntimeError(f"incomplete or duplicate frozen metric grid: {model}")


def validate_worker_artifacts(root: Path, name: str, freeze_sha: str, cfg: Mapping[str, Any], prepared_rows: Sequence[Mapping[str, Any]]) -> tuple[list[dict[str, Any]], dict[str, str]]:
    model, layer_text = name.rsplit("_layer", 1)
    directory = root / "shards" / name; complete_path = directory / "COMPLETE.json"; metrics_path = directory / "metrics.jsonl"; hook_path = directory / "HOOK_QA.json"
    complete = loadj(complete_path); rows = readjl(metrics_path)
    valid = complete.get("schema_version") == "joint_control_v4_worker_complete" and complete.get("status") == "COMPLETE" and complete.get("model") == model and int(complete.get("layer", -1)) == int(layer_text) and complete.get("freeze_sha256") == freeze_sha and int(complete.get("rows", -1)) == len(rows) and complete.get("hook_qa_sha256") == sha(hook_path) and complete.get("metrics_sha256") == sha(metrics_path)
    if not valid or any(r.get("schema_version") != "joint_control_v4_component_metric" or r.get("model") != model or int(r.get("layer", -1)) != int(layer_text) for r in rows):
        raise RuntimeError(f"worker drift: {name}")
    validate_metric_grid(rows, cfg, prepared_rows, model)
    return rows, {"complete_sha256": sha(complete_path), "metrics_sha256": sha(metrics_path), "hook_qa_sha256": sha(hook_path)}


def method_independent_task_evidence(groups: Mapping[tuple[Any, ...], Sequence[Mapping[str, Any]]], cfg: Mapping[str, Any]) -> dict[tuple[Any, ...], dict[str, Any]]:
    analysis = cfg["analysis"]; evidence: dict[tuple[Any, ...], dict[str, Any]] = {}; signatures: dict[tuple[Any, ...], tuple[Any, ...]] = {}
    for key, group in sorted(groups.items()):
        task_key = (key[2], key[3], key[4], key[5])
        signature = tuple(sorted((r["component_id"], r["component_block"], float(r["full_effect"]), float(r["natural_sham_effect"]), bool(r["behavior_eligible"])) for r in group))
        if task_key in signatures and signatures[task_key] != signature:
            raise RuntimeError(f"method-dependent natural task evidence: {task_key}")
        if task_key not in evidence:
            selected = [r for r in group if bool(r["behavior_eligible"])]
            ratios = [abs(float(r["natural_sham_effect"])) / abs(float(r["full_effect"])) for r in selected]
            sham = v2.block_interval(ratios, [r["component_block"] for r in selected], analysis["bootstrap_draws"], core.stable(cfg["seed"], *task_key, "natural_sham_fraction"))
            eligibility = float(np.mean([r["behavior_eligible"] for r in group]))
            task_pass = len(selected) >= int(analysis["minimum_eligible_rows"]) and eligibility >= analysis["minimum_effect_eligibility"] and sham is not None and sham[1] <= analysis["maximum_sham_fraction"] and sham[2] < analysis["maximum_sham_fraction_ci"]
            evidence[task_key] = {"eligibility": eligibility, "eligible_rows": len(selected), "sham_population": "behavior_eligible_rows_only", "natural_sham_fraction_ci": sham, "task_gate_passes": bool(task_pass)}
            signatures[task_key] = signature
    return evidence


def _aggregate(config: Path) -> None:
    cfg = loadj(config); verify_freeze(config, cfg); root = ROOT / cfg["runtime"]["output_root"]; out = root / "aggregate"; out.mkdir(parents=True, exist_ok=False)
    expected = [f"{m['key']}_layer{layer}" for m in cfg["models"] for layer in m["layers"]]
    started = time.monotonic()
    while not all((root / "shards" / name / "COMPLETE.json").exists() for name in expected):
        if (root / "task_gate/FAIL.json").exists() or (root / "synthetic/FAIL.json").exists():
            exjson(out / "BLOCKED.json", {"status": "BLOCKED_BY_UPSTREAM_GATE", "training_authorized": False}); return
        worker_failures = [root / "failures" / f"{name}_FAIL.json" for name in expected]
        if any(path.exists() for path in worker_failures) or time.monotonic() - started > float(cfg["runtime"]["worker_timeout_seconds"]):
            exjson(out / "FAILED.json", {"status": "WORKER_FAILURE_OR_TIMEOUT", "failed_workers": [path.name for path in worker_failures if path.exists()], "training_authorized": False}); return
        time.sleep(int(cfg["runtime"]["gate_poll_seconds"]))
    freeze_sha = sha(ROOT / cfg["runtime"]["freeze"])
    gate_paths = [root / "task_gate/PASS.json", root / "synthetic/PASS.json"]
    for gate_path in gate_paths:
        gate_record = loadj(gate_path)
        if gate_record.get("status") != "PASS" or gate_record.get("freeze_sha256") != freeze_sha:
            raise RuntimeError(f"invalid upstream gate lineage: {gate_path}")
    rows = []; shard_lineage = {}
    for name in expected:
        model = name.rsplit("_layer", 1)[0]
        shard_rows, shard_lineage[name] = validate_worker_artifacts(root, name, freeze_sha, cfg, rows_for(cfg, model))
        rows.extend(shard_rows)
    groups: dict[tuple[Any, ...], list[dict[str, Any]]] = {}
    for row in rows: groups.setdefault((row["method"], row["budget"], row["model"], row["layer"], row["fit_source"], row["eval_source"]), []).append(row)
    summaries = []; analysis = cfg["analysis"]; task_evidence = method_independent_task_evidence(groups, cfg)
    for key, group in sorted(groups.items()):
        blocks = [r["component_block"] for r in group]
        def ci(name: str) -> list[float] | None:
            vals = [float(r[name]) for r in group if r[name] is not None]; selected_blocks = [blocks[i] for i, r in enumerate(group) if r[name] is not None]
            return v2.block_interval(vals, selected_blocks, analysis["bootstrap_draws"], core.stable(cfg["seed"], *key, name))
        recovery, specificity, collateral = ci("behavioral_recovery"), ci("signed_sham_specificity"), ci("collateral_kl")
        evidence = task_evidence[(key[2], key[3], key[4], key[5])]
        passed = evidence["task_gate_passes"] and recovery is not None and recovery[0] > analysis["minimum_recovery_ci_lower"] and specificity is not None and specificity[0] > analysis["minimum_specificity_ci_lower"] and collateral is not None and collateral[2] < analysis["maximum_collateral_ci_upper"]
        summaries.append({"method": key[0], "budget": key[1], "model": key[2], "layer": key[3], "fit_source": key[4], "eval_source": key[5], **evidence, "recovery_ci": recovery, "specificity_ci": specificity, "collateral_ci": collateral, "passes": bool(passed)})
    decisions = []
    for method in sorted({r["method"] for r in rows}):
        for budget in cfg["budgets"]:
            for stage_name in ("early", "middle", "late"):
                passing = []
                for model in cfg["models"]:
                    cells = [s for s in summaries if s["method"] == method and s["budget"] == budget and s["model"] == model["key"] and core.stage(model, s["layer"]) == stage_name]
                    if {s["eval_source"] for s in cells if s["passes"]} == set(cfg["task"]["sources"]): passing.append(model["key"])
                decisions.append({"method": method, "budget": budget, "stage": stage_name, "passing_model_families": passing, "passes": len(passing) >= analysis["minimum_replicating_model_families"]})
    result = {"schema_version": "joint_control_v4_result", "status": "PROSPECTIVE_COMPLETE_REQUIRES_CLAIM_REVIEW", "task_label": cfg["task"]["task_label"], "within_corpus_transfer": True, "cross_domain_replication": False, "metric_rows": len(rows), "summaries": summaries, "method_decisions": decisions, "passing_method_decisions": sum(bool(x["passes"]) for x in decisions), "training_authorized": False, "lineage": {"freeze_sha256": freeze_sha, "task_gate_sha256": sha(gate_paths[0]), "synthetic_gate_sha256": sha(gate_paths[1]), "shards": shard_lineage}}
    exjson(out / "result.json", result); exjson(out / "COMPLETE.json", {"status": "COMPLETE", "result_sha256": sha(out / "result.json"), "freeze_sha256": freeze_sha, "task_gate_sha256": sha(gate_paths[0]), "synthetic_gate_sha256": sha(gate_paths[1])})


def aggregate(config: Path) -> None:
    cfg = loadj(config); root = ROOT / cfg["runtime"]["output_root"] / "aggregate"
    try:
        _aggregate(config)
    except BaseException as error:
        freeze_path = ROOT / cfg["runtime"]["freeze"]
        if not (root / "COMPLETE.json").exists(): publish_failure(root / "FAILED.json", {"status": "FAIL", "reason": "AGGREGATE_EXCEPTION", "error_type": type(error).__name__, "error": str(error), "freeze_sha256": sha(freeze_path) if freeze_path.is_file() else None})
        raise


def main() -> None:
    parser = argparse.ArgumentParser(); commands = parser.add_subparsers(dest="command", required=True)
    for name in ("prepare", "preflight", "freeze", "synthetic", "task-gate-aggregate", "aggregate"):
        command = commands.add_parser(name); command.add_argument("--config", type=Path, default=DEFAULT)
    command = commands.add_parser("task-gate-worker"); command.add_argument("--config", type=Path, default=DEFAULT); command.add_argument("--model", required=True)
    command = commands.add_parser("worker"); command.add_argument("--config", type=Path, default=DEFAULT); command.add_argument("--model", required=True); command.add_argument("--layer", type=int, required=True)
    args = parser.parse_args()
    if args.command == "prepare": prepare(args.config)
    elif args.command == "preflight": preflight(args.config)
    elif args.command == "freeze": freeze(args.config)
    elif args.command == "synthetic": synthetic(args.config)
    elif args.command == "task-gate-worker": task_gate_worker(args.config, args.model)
    elif args.command == "task-gate-aggregate": task_gate_aggregate(args.config)
    elif args.command == "worker": worker(args.config, args.model, args.layer)
    else: aggregate(args.config)


if __name__ == "__main__":
    main()
