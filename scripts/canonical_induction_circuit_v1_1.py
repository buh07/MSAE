#!/usr/bin/env python3
"""Canonical repeated-token induction circuit technical positive control."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import random
import time
import traceback
from pathlib import Path
from typing import Any, Mapping, Sequence

import numpy as np
import torch

ROOT = Path(__file__).resolve().parents[1]
DEFAULT = ROOT / "configs/canonical_induction_circuit_v1_1/run.json"


def native(value: Any) -> Any:
    if isinstance(value, np.generic):
        return value.item()
    if isinstance(value, dict):
        return {str(k): native(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [native(v) for v in value]
    return value


def canon(value: Any) -> bytes:
    return json.dumps(native(value), sort_keys=True, separators=(",", ":"), allow_nan=False).encode()


def loadj(path: Path) -> Any:
    return json.loads(path.read_text())


def sha(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(8 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def stable(seed: int, *parts: Any) -> int:
    return int.from_bytes(hashlib.sha256("|".join(map(str, (seed,) + parts)).encode()).digest()[:8], "little") % (2**32)


def exjson(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + f".tmp.{os.getpid()}.{time.time_ns()}")
    fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(canon(value) + b"\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.link(tmp, path)
    finally:
        tmp.unlink(missing_ok=True)


def publish(path: Path, value: Any) -> None:
    try:
        exjson(path, value)
    except FileExistsError:
        pass


def writejl(path: Path, rows: Sequence[Mapping[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, "w") as handle:
        for row in rows:
            handle.write(canon(dict(row)).decode() + "\n")
        handle.flush()
        os.fsync(handle.fileno())


def readjl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text().splitlines() if line]


def require_offline() -> None:
    for key in ("HF_DATASETS_OFFLINE", "HF_HUB_OFFLINE", "TRANSFORMERS_OFFLINE"):
        if os.environ.get(key) != "1":
            raise RuntimeError(f"offline environment required: {key}=1")


def preservation_verify(cfg: Mapping[str, Any]) -> None:
    manifest_path = ROOT / cfg["preservation"]["ioi_v1_manifest"]
    if sha(manifest_path) != cfg["preservation"]["ioi_v1_manifest_sha256"]:
        raise RuntimeError("IOI v1 preservation manifest drift")
    manifest = loadj(manifest_path)
    expected_files = {record["path"] for record in manifest["files"]}
    for tree_root in manifest["tree_roots"]:
        tree = ROOT / tree_root
        actual = {path.relative_to(ROOT).as_posix() for path in tree.rglob("*") if path.is_file()}
        expected = {path for path in expected_files if path == tree_root or path.startswith(tree_root + "/")}
        if actual != expected:
            raise RuntimeError(
                f"IOI v1 tree inventory drift: {tree_root}; "
                f"extra={sorted(actual - expected)} missing={sorted(expected - actual)}"
            )
    for record in manifest["files"]:
        path = ROOT / record["path"]
        if not path.is_file() or path.stat().st_size != record["bytes"] or sha(path) != record["sha256"]:
            raise RuntimeError(f"IOI v1 preservation drift: {record['path']}")
    result_root = ROOT / "results/known_mechanism_ioi_v1_20260809"
    result = loadj(result_root / "final/result.json")
    behavior = loadj(result_root / "gates/behavior/result.json")
    patch_gate = loadj(result_root / "gates/patch/result.json")
    expected = manifest["expected"]
    if (
        manifest.get("status") != "PRESERVED_FORMAL_DEVELOPMENT_STOP"
        or result["status"] != cfg["preservation"]["required_ioi_final_status"]
        or result["status"] != expected["final_status"]
        or behavior["status"] != "STOP"
        or patch_gate["status"] != "STOP"
        or len(behavior["eligible_models"]) != expected["behavior_eligible_models"]
        or result["representation_methods_evaluated"] != expected["methods_evaluated"]
        or result["training_performed"] != expected["training_performed"]
        or result["future_method_benchmark_automatically_authorized"]
        or expected["ioi_v1_retry_authorized"]
    ):
        raise RuntimeError("IOI v1 formal outcome drift")
    patch_complete = list(result_root.glob("development/patch/*/COMPLETE.json"))
    patch_blocked = list(result_root.glob("development/patch/*/BLOCKED.json"))
    confirmation_complete = list(result_root.glob("confirmation/*/COMPLETE.json"))
    confirmation_blocked = list(result_root.glob("confirmation/*/BLOCKED.json"))
    behavior_complete = list(result_root.glob("development/behavior/*/COMPLETE.json"))
    if (
        len(patch_complete) != expected["patch_complete_files"]
        or len(patch_blocked) != expected["patch_blocked_files"]
        or len(confirmation_complete) != expected["confirmation_complete_files"]
        or len(confirmation_blocked) != expected["confirmation_blocked_files"]
        or len(behavior_complete) != 3
    ):
        raise RuntimeError("IOI v1 blocked stage was opened")
    if any(loadj(path).get("model_loaded") is not False for path in patch_blocked + confirmation_blocked):
        raise RuntimeError("IOI v1 blocked-stage model-load record drift")
    if any(loadj(path).get("confirmation_rows_loaded") is not False for path in confirmation_blocked):
        raise RuntimeError("IOI v1 confirmation firewall record drift")
    if any(loadj(path).get("representation_methods") is not False or loadj(path).get("training") is not False for path in behavior_complete):
        raise RuntimeError("IOI v1 behavior completion scope drift")
    migration = ROOT / cfg["preservation"]["post_result_paper_migration"]
    if sha(migration) != cfg["preservation"]["post_result_paper_migration_sha256"]:
        raise RuntimeError("post-result paper migration drift")
    migration_record = loadj(migration)
    original_freeze_path = ROOT / "configs/known_mechanism_ioi_v1/FREEZE.json"
    original_freeze = loadj(original_freeze_path)
    original_inventory = original_freeze["candidate_inventory"]
    if hashlib.sha256(canon(original_inventory)).hexdigest() != original_freeze["candidate_inventory_sha256"]:
        raise RuntimeError("IOI v1 original freeze inventory digest drift")
    migrated = {record["original_path"]: record for record in migration_record["records"]}
    for record in original_inventory:
        if record["path"] in migrated:
            replacement = migrated[record["path"]]
            snapshot = ROOT / replacement["snapshot_path"]
            if (
                replacement["frozen_sha256"] != record["sha256"]
                or replacement["snapshot_sha256"] != record["sha256"]
                or not snapshot.is_file()
                or snapshot.stat().st_size != record["bytes"]
                or sha(snapshot) != record["sha256"]
            ):
                raise RuntimeError(f"IOI v1 migrated frozen input drift: {record['path']}")
            continue
        path = ROOT / record["path"]
        if not path.is_file() or path.stat().st_size != record["bytes"] or sha(path) != record["sha256"]:
            raise RuntimeError(f"IOI v1 original frozen input drift: {record['path']}")
    prepared_root = "data/known_mechanism_ioi_v1_prepared"
    expected_prepared = {record["path"] for record in original_inventory if record["path"].startswith(prepared_root + "/")}
    actual_prepared = {path.relative_to(ROOT).as_posix() for path in (ROOT / prepared_root).rglob("*") if path.is_file()}
    if actual_prepared != expected_prepared:
        raise RuntimeError(
            f"IOI v1 original prepared-tree inventory drift; "
            f"extra={sorted(actual_prepared - expected_prepared)} missing={sorted(expected_prepared - actual_prepared)}"
        )


def generate_rows(cfg: Mapping[str, Any], stage: str) -> list[dict[str, Any]]:
    panel, spec = cfg["panel"], cfg["panel"][stage]
    rng = np.random.default_rng(int(spec["seed"]))
    rows = []
    for index in range(int(panel["rows_per_stage"])):
        tokens = rng.choice(np.arange(int(spec["token_id_low"]), int(spec["token_id_high_exclusive"])), int(panel["unique_tokens_per_row"]), replace=False).tolist()
        sequence, alt1, alt2 = tokens[: int(panel["sequence_length"])], tokens[-2], tokens[-1]
        clean = sequence + sequence[:-1]
        corrupt = sequence[:-1] + [alt1] + sequence[:-1]
        sham = sequence[:-1] + [alt2] + sequence[:-1]
        rows.append({
            "stage": stage, "row_index": index, "block_index": index // int(panel["rows_per_block"]),
            "component_id": f"{stage}:b{index // int(panel['rows_per_block'])}:r{index}",
            "clean_ids": clean, "corrupt_ids": corrupt, "sham_ids": sham,
            "target_id": sequence[-1], "contrast_id": alt1, "sham_id": alt2,
            "query_id": sequence[-2], "query_position": len(clean) - 1,
            "induction_source_position": len(sequence) - 1,
        })
    return rows


def prepare(config: Path, output: Path | None = None) -> None:
    cfg = loadj(config)
    preservation_verify(cfg)
    root = output or ROOT / cfg["runtime"]["prepared_root"]
    if root.exists():
        raise FileExistsError(root)
    root.mkdir(parents=True)
    stages = {stage: generate_rows(cfg, stage) for stage in ("development", "confirmation")}
    for stage, rows in stages.items():
        writejl(root / f"{stage}.jsonl", rows)
    dev_tokens = {token for row in stages["development"] for key in ("clean_ids", "corrupt_ids", "sham_ids") for token in row[key]}
    con_tokens = {token for row in stages["confirmation"] for key in ("clean_ids", "corrupt_ids", "sham_ids") for token in row[key]}
    if dev_tokens & con_tokens:
        raise RuntimeError("development/confirmation token overlap")
    for rows in stages.values():
        for row in rows:
            if len(row["clean_ids"]) != cfg["panel"]["prompt_length"] or len(row["corrupt_ids"]) != len(row["clean_ids"]) or len(row["sham_ids"]) != len(row["clean_ids"]):
                raise RuntimeError("prompt length drift")
            original = row["clean_ids"][: cfg["panel"]["sequence_length"]]
            if len(set(original + [row["contrast_id"], row["sham_id"]])) != cfg["panel"]["unique_tokens_per_row"]:
                raise RuntimeError("within-row token uniqueness drift")
    files = {f"{stage}.jsonl": sha(root / f"{stage}.jsonl") for stage in stages}
    exjson(root / "PRESCORE.json", {"schema_version": "canonical_induction_circuit_v1_prescore", "selection_firewall": "ALGORITHMIC_TOKEN_IDS_NO_MODEL_FORWARD", "rows": {k: len(v) for k, v in stages.items()}, "blocks": cfg["panel"]["blocks"], "rows_per_block": cfg["panel"]["rows_per_block"], "development_confirmation_token_overlap": 0, "files": files})


def verify_prepared(cfg: Mapping[str, Any], include_confirmation: bool = True) -> None:
    root = ROOT / cfg["runtime"]["prepared_root"]
    record = loadj(root / "PRESCORE.json")
    if record["selection_firewall"] != "ALGORITHMIC_TOKEN_IDS_NO_MODEL_FORWARD" or record["rows"] != {"development": 128, "confirmation": 128}:
        raise RuntimeError("prepared prescore drift")
    for name, digest in record["files"].items():
        if not include_confirmation and name == "confirmation.jsonl":
            continue
        if sha(root / name) != digest:
            raise RuntimeError(f"prepared payload drift: {name}")


def cache_preflight(config: Path) -> None:
    cfg = loadj(config)
    require_offline()
    from huggingface_hub import snapshot_download
    from transformers import AutoConfig, AutoTokenizer

    model = cfg["model"]
    snapshot = Path(snapshot_download(model["name"], revision=model["revision"], local_files_only=True))
    AutoConfig.from_pretrained(model["name"], revision=model["revision"], local_files_only=True)
    AutoTokenizer.from_pretrained(model["name"], revision=model["revision"], local_files_only=True)
    names = {"config.json", "generation_config.json", "tokenizer.json", "tokenizer_config.json", "special_tokens_map.json", "vocab.json", "merges.txt", "pytorch_model.bin", "model.safetensors"}
    files = []
    for path in sorted((p for p in snapshot.iterdir() if p.is_file() and p.name in names), key=lambda p: p.name):
        files.append({"name": path.name, "bytes": path.stat().st_size, "sha256": sha(path), "resolved_blob": str(path.resolve())})
    if not any(record["name"].endswith((".bin", ".safetensors")) for record in files):
        raise RuntimeError("cached model weight absent")
    payload = {"schema_version": "canonical_induction_circuit_v1_cache", "status": "PASS", "model": model["key"], "revision": model["revision"], "snapshot": str(snapshot), "files": files}
    target = ROOT / cfg["runtime"]["cache_attestation"]
    if target.exists():
        if loadj(target) != payload:
            raise RuntimeError("cache attestation drift")
    else:
        exjson(target, payload)


def candidate_inventory(config: Path, cfg: Mapping[str, Any]) -> list[dict[str, Any]]:
    paths = [ROOT / value for value in cfg["candidate_files"]]
    paths.extend(sorted(p for p in (ROOT / cfg["runtime"]["prepared_root"]).rglob("*") if p.is_file()))
    records = []
    for path in sorted(set(paths), key=lambda p: p.relative_to(ROOT).as_posix()):
        if not path.is_file():
            raise RuntimeError(f"candidate artifact absent: {path.relative_to(ROOT)}")
        records.append({"path": path.relative_to(ROOT).as_posix(), "bytes": path.stat().st_size, "sha256": sha(path)})
    return records


def preflight(config: Path, require_review: bool = False, include_confirmation: bool = True) -> None:
    cfg = loadj(config)
    preservation_verify(cfg)
    verify_prepared(cfg, include_confirmation=include_confirmation)
    if cfg["model"]["known_heads"] != [[5, 5], [6, 9]] or cfg["model"]["matched_control_heads"] != [[5, 0], [6, 0]]:
        raise RuntimeError("prespecified head registry drift")
    if cfg["gate"].get("estimand_weighting") != "equal_block":
        raise RuntimeError("registered equal-block estimand drift")
    if any(cfg["scope"][key] for key in ("general_method_claim", "representation_methods", "training", "natural_language_prompt_endpoint", "ioi_v1_retry", "automatic_future_method_authorization")):
        raise RuntimeError("scope authorization drift")
    if (ROOT / cfg["runtime"]["output_root"]).exists() or (ROOT / cfg["runtime"]["provenance_root"]).exists():
        raise RuntimeError("one-shot runtime namespace exists")
    review = ROOT / cfg["runtime"]["candidate_review"]
    if require_review and (not review.is_file() or review.read_text().splitlines()[0] != "VERDICT: SHIP"):
        raise RuntimeError("candidate SHIP review required")
    if require_review:
        candidate_inventory(config, cfg)
    else:
        for value in cfg["candidate_files"]:
            if value != cfg["runtime"]["candidate_review"] and not (ROOT / value).is_file():
                raise RuntimeError(f"candidate artifact absent: {value}")


def freeze(config: Path) -> None:
    cfg = loadj(config)
    preflight(config, require_review=True, include_confirmation=True)
    inventory = candidate_inventory(config, cfg)
    exjson(ROOT / cfg["runtime"]["freeze"], {"schema_version": "canonical_induction_circuit_v1_freeze", "namespace": cfg["namespace"], "config_sha256": sha(config), "candidate_inventory": inventory, "candidate_inventory_sha256": hashlib.sha256(canon(inventory)).hexdigest(), "technical_positive_control_only": True, "prespecified_heads": True, "single_model": True, "general_method_claim": False, "representation_methods": False, "training": False, "one_shot": True})


def verify_freeze(config: Path, cfg: Mapping[str, Any] | None = None, include_confirmation: bool = True) -> dict[str, Any]:
    cfg = cfg or loadj(config)
    record = loadj(ROOT / cfg["runtime"]["freeze"])
    if record["config_sha256"] != sha(config):
        raise RuntimeError("freeze config drift")
    if hashlib.sha256(canon(record["candidate_inventory"])).hexdigest() != record["candidate_inventory_sha256"]:
        raise RuntimeError("freeze inventory digest drift")
    if include_confirmation:
        if record["candidate_inventory"] != candidate_inventory(config, cfg):
            raise RuntimeError("frozen candidate drift")
    else:
        confirmation = cfg["runtime"]["prepared_root"].rstrip("/") + "/confirmation.jsonl"
        for item in record["candidate_inventory"]:
            if item["path"] == confirmation:
                continue
            path = ROOT / item["path"]
            if not path.is_file() or path.stat().st_size != item["bytes"] or sha(path) != item["sha256"]:
                raise RuntimeError(f"frozen candidate drift: {item['path']}")
    preservation_verify(cfg)
    verify_prepared(cfg, include_confirmation=include_confirmation)
    return record


def validate_review_binding(freeze: Path, candidate: Path, frozen: Path, binding: Path) -> dict[str, Any]:
    candidate_lines = candidate.read_text().splitlines() if candidate.is_file() else []
    frozen_lines = frozen.read_text().splitlines() if frozen.is_file() else []
    if not candidate_lines or candidate_lines[0] != "VERDICT: SHIP":
        raise RuntimeError("candidate first-line SHIP review required")
    if not frozen_lines or frozen_lines[0] != "VERDICT: SHIP":
        raise RuntimeError("frozen first-line SHIP review required")
    value = loadj(binding)
    expected = {
        "status": "SHIP",
        "candidate_verdict": "SHIP",
        "frozen_verdict": "SHIP",
        "freeze_sha256": sha(freeze),
        "candidate_review_sha256": sha(candidate),
        "frozen_review_sha256": sha(frozen),
    }
    if value != expected:
        raise RuntimeError("review binding mismatch")
    return value


def seed_all(seed: int) -> None:
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)
    torch.use_deterministic_algorithms(True)


def gpu_guard(cfg: Mapping[str, Any]) -> torch.device:
    if os.environ.get("CUBLAS_WORKSPACE_CONFIG") != cfg["qa"]["cublas_workspace_config"]:
        raise RuntimeError("registered CUBLAS_WORKSPACE_CONFIG must be set before Python startup")
    expected, visible = os.environ.get("EXPECTED_GPU_UUID"), os.environ.get("CUDA_VISIBLE_DEVICES")
    if not expected or visible != expected or not torch.cuda.is_available() or torch.cuda.device_count() != 1:
        raise RuntimeError("exactly one UUID-pinned CUDA device required")
    return torch.device("cuda:0")


def load_model(cfg: Mapping[str, Any], device: torch.device) -> Any:
    require_offline()
    from transformers import AutoModelForCausalLM

    spec = cfg["model"]
    model = AutoModelForCausalLM.from_pretrained(spec["name"], revision=spec["revision"], local_files_only=True, torch_dtype=torch.float32, attn_implementation="eager").to(device).eval()
    model.config.use_cache = False
    return model


def batch_ids(rows: Sequence[Mapping[str, Any]], condition: str, device: torch.device) -> tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
    values = torch.tensor([row[f"{condition}_ids"] for row in rows], dtype=torch.long, device=device)
    mask = torch.ones_like(values)
    final = torch.full((len(rows),), values.shape[1] - 1, dtype=torch.long, device=device)
    return values, mask, final


@torch.no_grad()
def run_condition(model: Any, cfg: Mapping[str, Any], rows: Sequence[Mapping[str, Any]], condition: str, capture_heads: Sequence[Sequence[int]], zero_heads: Sequence[Sequence[int]] = (), replacement: Mapping[str, np.ndarray] | None = None) -> dict[str, Any]:
    spec = cfg["model"]
    logits_out, attention_out = [], {f"{layer}.{head}": [] for layer, head in capture_heads}
    head_out = {f"{layer}.{head}": [] for layer, head in capture_heads}
    by_layer: dict[int, set[int]] = {}
    for layer, head in list(capture_heads) + list(zero_heads):
        by_layer.setdefault(int(layer), set()).add(int(head))
    if replacement:
        for key in replacement:
            layer, head = map(int, key.split(".")); by_layer.setdefault(layer, set()).add(head)
    batch_size = int(spec["batch_size"])
    for start in range(0, len(rows), batch_size):
        batch = rows[start : start + batch_size]
        ids, mask, final = batch_ids(batch, condition, next(model.parameters()).device)
        arange = torch.arange(len(batch), device=ids.device)
        handles = []
        for layer, heads in by_layer.items():
            def hook(_module: Any, inputs: tuple[Any, ...], layer: int = layer, heads: set[int] = heads) -> tuple[Any, ...]:
                value = inputs[0]
                changed = None
                for head in sorted(heads):
                    key = f"{layer}.{head}"; sl = slice(head * int(spec["head_size"]), (head + 1) * int(spec["head_size"]))
                    if [layer, head] in capture_heads:
                        head_out[key].append(value[arange, final, sl].detach().float().cpu().numpy())
                    if [layer, head] in zero_heads or replacement is not None and key in replacement:
                        if changed is None:
                            changed = value.clone()
                        if [layer, head] in zero_heads:
                            changed[arange, final, sl] = 0
                        else:
                            donor = torch.from_numpy(np.asarray(replacement[key][start : start + len(batch)], np.float32)).to(value.device)
                            changed[arange, final, sl] = donor.to(value.dtype)
                return ((changed if changed is not None else value),) + inputs[1:]
            handles.append(model.transformer.h[layer].attn.c_proj.register_forward_pre_hook(hook))
        try:
            output = model(input_ids=ids, attention_mask=mask, use_cache=False, output_attentions=True)
        finally:
            for handle in handles:
                handle.remove()
        logits_out.append(output.logits[arange, final].float().cpu().numpy())
        for layer, head in capture_heads:
            key = f"{layer}.{head}"
            scores = output.attentions[layer][arange, head, final, torch.tensor([row["induction_source_position"] for row in batch], device=ids.device)]
            attention_out[key].append(scores.float().cpu().numpy())
    return {"logits": np.concatenate(logits_out), "head_outputs": {key: np.concatenate(value) for key, value in head_out.items()}, "attention": {key: np.concatenate(value) for key, value in attention_out.items()}}


def margin(logits: np.ndarray, rows: Sequence[Mapping[str, Any]]) -> np.ndarray:
    return np.asarray([logits[index, row["target_id"]] - logits[index, row["contrast_id"]] for index, row in enumerate(rows)], dtype=np.float64)


def compute_metrics(cfg: Mapping[str, Any], rows: Sequence[Mapping[str, Any]], outputs: Mapping[str, Any]) -> list[dict[str, Any]]:
    clean = margin(outputs["clean"]["logits"], rows)
    corrupt_target = margin(outputs["corrupt"]["logits"], rows)
    known_zero = margin(outputs["known_zero"]["logits"], rows)
    control_zero = margin(outputs["control_zero"]["logits"], rows)
    patched = margin(outputs["patched_clean"]["logits"], rows)
    sham_patched = margin(outputs["patched_sham"]["logits"], rows)
    known_keys = [f"{a}.{b}" for a, b in cfg["model"]["known_heads"]]
    control_keys = [f"{a}.{b}" for a, b in cfg["model"]["matched_control_heads"]]
    result = []
    for index, row in enumerate(rows):
        effect = min(clean[index], -corrupt_target[index])
        informative = bool(clean[index] > 0 and corrupt_target[index] < 0 and effect > cfg["gate"]["behavior_effect_floor_strict"])
        denominator = clean[index] - corrupt_target[index]
        attention_known = float(np.mean([outputs["clean"]["attention"][key][index] for key in known_keys]))
        attention_control = float(np.mean([outputs["clean"]["attention"][key][index] for key in control_keys]))
        recovery = (patched[index] - corrupt_target[index]) / denominator if informative and denominator > 0 else None
        sham_recovery = (sham_patched[index] - corrupt_target[index]) / denominator if informative and denominator > 0 else None
        result.append({k: row[k] for k in ("stage", "row_index", "block_index", "component_id")} | {
            "clean_margin": float(clean[index]), "corrupt_target_margin": float(corrupt_target[index]), "effect": float(effect), "informative": informative,
            "attention_known": attention_known, "attention_control": attention_control, "attention_margin": attention_known - attention_control,
            "known_zero_margin": float(known_zero[index]), "control_zero_margin": float(control_zero[index]),
            "necessity_known": float(clean[index] - known_zero[index]), "necessity_control": float(clean[index] - control_zero[index]),
            "necessity_margin": float((clean[index] - known_zero[index]) - (clean[index] - control_zero[index])),
            "patched_margin": float(patched[index]), "sham_patched_margin": float(sham_patched[index]),
            "recovery": None if recovery is None else float(recovery), "sham_recovery": None if sham_recovery is None else float(sham_recovery),
            "selectivity": None if recovery is None or sham_recovery is None else float(recovery - sham_recovery),
        })
    return result


def interval(rows: Sequence[Mapping[str, Any]], field: str, draws: int, seed: int) -> dict[str, Any] | None:
    valid = [row for row in rows if row.get("informative") and row.get(field) is not None and np.isfinite(row[field])]
    if not valid:
        return None
    blocks = sorted({int(row["block_index"]) for row in valid})
    grouped = {block: [float(row[field]) for row in valid if int(row["block_index"]) == block] for block in blocks}
    rng = np.random.default_rng(seed); samples = []
    for _ in range(draws):
        chosen = rng.choice(blocks, len(blocks), replace=True); block_means = []
        for block in chosen:
            source = grouped[int(block)]
            block_means.append(float(np.mean(rng.choice(source, len(source), replace=True))))
        samples.append(float(np.mean(block_means)))
    point = float(np.mean([np.mean(grouped[block]) for block in blocks]))
    return {"point": point, "lower": float(np.quantile(samples, 0.025)), "upper": float(np.quantile(samples, 0.975)), "draws": draws, "weighting": "equal_block"}


def summarize(cfg: Mapping[str, Any], rows: Sequence[Mapping[str, Any]], stage: str) -> dict[str, Any]:
    gate = cfg["gate"]; counts = {str(block): sum(bool(row["informative"]) for row in rows if row["block_index"] == block) for block in range(cfg["panel"]["blocks"])}
    metrics = {field: interval(rows, field, gate["bootstrap_draws"], stable(cfg["seed"], stage, field)) for field in ("attention_known", "attention_margin", "necessity_known", "necessity_margin", "recovery", "selectivity")}
    support = sum(counts.values()) >= gate["minimum_informative_total"] and all(value >= gate["minimum_informative_per_block"] for value in counts.values())
    passed = bool(support and all(value is not None for value in metrics.values())
        and metrics["attention_known"]["point"] >= gate["attention_known_point_min_inclusive"] and metrics["attention_known"]["lower"] > gate["attention_known_lower_strict"]
        and metrics["attention_margin"]["point"] >= gate["attention_margin_point_min_inclusive"] and metrics["attention_margin"]["lower"] > gate["attention_margin_lower_strict"]
        and metrics["necessity_known"]["point"] >= gate["necessity_known_point_min_inclusive"]
        and metrics["necessity_margin"]["point"] >= gate["necessity_margin_point_min_inclusive"] and metrics["necessity_margin"]["lower"] > gate["necessity_margin_lower_strict"]
        and metrics["recovery"]["point"] >= gate["sufficiency_recovery_point_min_inclusive"] and metrics["recovery"]["lower"] > gate["sufficiency_recovery_lower_strict"]
        and metrics["selectivity"]["point"] >= gate["selectivity_point_min_inclusive"] and metrics["selectivity"]["lower"] > gate["selectivity_lower_strict"])
    return {"stage": stage, "informative_per_block": counts, "informative_total": sum(counts.values()), "metrics": metrics, "pass": passed}


def run_stage(cfg: Mapping[str, Any], model: Any, rows: Sequence[Mapping[str, Any]]) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    known, control = cfg["model"]["known_heads"], cfg["model"]["matched_control_heads"]
    qa_rows = rows[: cfg["qa"]["rows"]]
    qa1 = run_condition(model, cfg, qa_rows, "clean", known)
    qa2 = run_condition(model, cfg, qa_rows, "clean", known)
    qa_logits = float(np.max(np.abs(qa1["logits"] - qa2["logits"])))
    qa_heads = max(float(np.max(np.abs(qa1["head_outputs"][key] - qa2["head_outputs"][key]))) for key in qa1["head_outputs"])
    qa = {"rows": len(qa_rows), "logits_max_abs_difference": qa_logits, "known_head_outputs_max_abs_difference": qa_heads, "exact_logits": bool(np.array_equal(qa1["logits"], qa2["logits"])), "exact_known_head_outputs": bool(all(np.array_equal(qa1["head_outputs"][key], qa2["head_outputs"][key]) for key in qa1["head_outputs"])), "pass": bool(qa_logits <= cfg["qa"]["max_abs_difference"] and qa_heads <= cfg["qa"]["max_abs_difference"])}
    if not qa["pass"]:
        raise RuntimeError(f"repeated live inference QA failed: {qa}")
    clean = run_condition(model, cfg, rows, "clean", list(known) + list(control))
    corrupt = run_condition(model, cfg, rows, "corrupt", [])
    sham = run_condition(model, cfg, rows, "sham", known)
    known_zero = run_condition(model, cfg, rows, "clean", [], zero_heads=known)
    control_zero = run_condition(model, cfg, rows, "clean", [], zero_heads=control)
    known_keys = {f"{layer}.{head}" for layer, head in known}
    clean_donor = {key: value for key, value in clean["head_outputs"].items() if key in known_keys}
    patched_clean = run_condition(model, cfg, rows, "corrupt", [], replacement=clean_donor)
    patched_sham = run_condition(model, cfg, rows, "corrupt", [], replacement=sham["head_outputs"])
    metrics = compute_metrics(cfg, rows, {"clean": clean, "corrupt": corrupt, "known_zero": known_zero, "control_zero": control_zero, "patched_clean": patched_clean, "patched_sham": patched_sham})
    return metrics, qa


def wait_for_terminals(roots: Sequence[Path], allowed: Sequence[str], timeout: int, poll: int) -> dict[Path, Path]:
    deadline = time.monotonic() + timeout
    while True:
        found = {}
        for root in roots:
            if (root / "FAILED.json").is_file():
                raise RuntimeError(f"upstream failure: {root / 'FAILED.json'}")
            hits = [root / name for name in allowed if (root / name).is_file()]
            if len(hits) > 1:
                raise RuntimeError(f"multiple terminals: {root}")
            if hits:
                found[root] = hits[0]
        if len(found) == len(roots):
            return found
        if time.monotonic() >= deadline:
            raise TimeoutError(f"timeout waiting for terminals: {[str(root) for root in roots if root not in found]}")
        time.sleep(poll)


def validate_complete(cfg: Mapping[str, Any], root: Path, stage: str, freeze_record: Mapping[str, Any], gate_hash: str | None = None) -> dict[str, Any]:
    record = loadj(root / "COMPLETE.json")
    expected = {"schema_version": "canonical_induction_circuit_v1_complete", "stage": stage, "rows": 128, "freeze_sha256": sha(ROOT / cfg["runtime"]["freeze"]), "freeze_inventory_sha256": freeze_record["candidate_inventory_sha256"], "representation_methods": False, "training": False}
    if gate_hash is not None:
        expected["development_gate_sha256"] = gate_hash
    if any(record.get(key) != value for key, value in expected.items()) or sha(root / "metrics.jsonl") != record.get("metrics_sha256") or sha(root / "QA.json") != record.get("qa_sha256"):
        raise RuntimeError(f"completion lineage mismatch: {stage}")
    return record


def validate_development_gate(cfg: Mapping[str, Any], output: Path, freeze_record: Mapping[str, Any]) -> dict[str, Any]:
    gate_path = output / "development_gate/result.json"
    gate = loadj(gate_path)
    validate_complete(cfg, output / "development", "development", freeze_record)
    recomputed = summarize(cfg, readjl(output / "development/metrics.jsonl"), "development")
    authorized = bool(recomputed["pass"])
    expected = {
        "schema_version": "canonical_induction_circuit_v1_development_gate",
        "status": "PASS" if authorized else "STOP",
        "summary": recomputed,
        "confirmation_authorized": authorized,
        "technical_positive_control_only": True,
        "general_method_claim_authorized": False,
        "representation_methods_authorized": False,
        "training_authorized": False,
        "freeze_sha256": sha(ROOT / cfg["runtime"]["freeze"]),
        "freeze_inventory_sha256": freeze_record["candidate_inventory_sha256"],
    }
    if gate != expected:
        raise RuntimeError("development gate lineage or recomputation mismatch")
    return gate


def validate_blocked_confirmation(cfg: Mapping[str, Any], root: Path, freeze_record: Mapping[str, Any], gate_hash: str) -> dict[str, Any]:
    record = loadj(root / "BLOCKED.json")
    expected = {
        "schema_version": "canonical_induction_circuit_v1_blocked",
        "stage": "confirmation",
        "reason": "DEVELOPMENT_GATE_STOP",
        "model_loaded": False,
        "confirmation_rows_loaded": False,
        "freeze_sha256": sha(ROOT / cfg["runtime"]["freeze"]),
        "freeze_inventory_sha256": freeze_record["candidate_inventory_sha256"],
        "development_gate_sha256": gate_hash,
    }
    if record != expected:
        raise RuntimeError("blocked confirmation lineage mismatch")
    return record


def worker(config: Path, stage: str) -> None:
    cfg = loadj(config); freeze_record = verify_freeze(config, cfg, include_confirmation=False)
    output = ROOT / cfg["runtime"]["output_root"]; root = output / stage
    if root.exists():
        raise FileExistsError(root)
    root.mkdir(parents=True)
    try:
        gate_hash = None
        if stage == "confirmation":
            gate_path = output / "development_gate/result.json"
            wait_for_terminals([gate_path.parent], ["result.json"], cfg["runtime"]["gate_timeout_seconds"], cfg["runtime"]["gate_poll_seconds"])
            gate = validate_development_gate(cfg, output, freeze_record)
            gate_hash = sha(gate_path)
            if not gate["confirmation_authorized"]:
                exjson(root / "BLOCKED.json", {
                    "schema_version": "canonical_induction_circuit_v1_blocked",
                    "stage": stage,
                    "reason": "DEVELOPMENT_GATE_STOP",
                    "model_loaded": False,
                    "confirmation_rows_loaded": False,
                    "freeze_sha256": sha(ROOT / cfg["runtime"]["freeze"]),
                    "freeze_inventory_sha256": freeze_record["candidate_inventory_sha256"],
                    "development_gate_sha256": gate_hash,
                })
                return
            freeze_record = verify_freeze(config, cfg, include_confirmation=True)
        device = gpu_guard(cfg); seed_all(stable(cfg["seed"], stage)); model = load_model(cfg, device)
        rows = readjl(ROOT / cfg["runtime"]["prepared_root"] / f"{stage}.jsonl")
        exjson(root / "STARTED.json", {"stage": stage, "runtime": {"gpu": torch.cuda.get_device_name(0), "cuda": torch.version.cuda, "torch": torch.__version__, "cublas_workspace_config": os.environ.get("CUBLAS_WORKSPACE_CONFIG"), "gpu_uuid": os.environ.get("EXPECTED_GPU_UUID")}})
        metrics, qa = run_stage(cfg, model, rows); writejl(root / "metrics.jsonl", metrics); exjson(root / "QA.json", qa)
        payload = {"schema_version": "canonical_induction_circuit_v1_complete", "stage": stage, "rows": len(rows), "metrics_sha256": sha(root / "metrics.jsonl"), "qa_sha256": sha(root / "QA.json"), "freeze_sha256": sha(ROOT / cfg["runtime"]["freeze"]), "freeze_inventory_sha256": freeze_record["candidate_inventory_sha256"], "representation_methods": False, "training": False}
        if gate_hash is not None:
            payload["development_gate_sha256"] = gate_hash
        exjson(root / "COMPLETE.json", payload)
    except Exception as exc:
        publish(root / "FAILED.json", {"stage": stage, "error_type": type(exc).__name__, "error": str(exc), "traceback": traceback.format_exc()}); raise


def development_gate(config: Path) -> None:
    cfg = loadj(config); freeze_record = verify_freeze(config, cfg, include_confirmation=False); output = ROOT / cfg["runtime"]["output_root"]; target = output / "development_gate/result.json"
    try:
        wait_for_terminals([output / "development"], ["COMPLETE.json"], cfg["runtime"]["gate_timeout_seconds"], cfg["runtime"]["gate_poll_seconds"])
        validate_complete(cfg, output / "development", "development", freeze_record)
        summary = summarize(cfg, readjl(output / "development/metrics.jsonl"), "development")
        exjson(target, {"schema_version": "canonical_induction_circuit_v1_development_gate", "status": "PASS" if summary["pass"] else "STOP", "summary": summary, "confirmation_authorized": summary["pass"], "technical_positive_control_only": True, "general_method_claim_authorized": False, "representation_methods_authorized": False, "training_authorized": False, "freeze_sha256": sha(ROOT / cfg["runtime"]["freeze"]), "freeze_inventory_sha256": freeze_record["candidate_inventory_sha256"]})
    except Exception as exc:
        publish(target.parent / "FAILED.json", {"stage": "development_gate", "error_type": type(exc).__name__, "error": str(exc), "traceback": traceback.format_exc()}); raise


def final(config: Path) -> None:
    cfg = loadj(config); freeze_record = verify_freeze(config, cfg, include_confirmation=False); output = ROOT / cfg["runtime"]["output_root"]; target = output / "final/result.json"
    try:
        gate_path = output / "development_gate/result.json"; wait_for_terminals([gate_path.parent], ["result.json"], cfg["runtime"]["gate_timeout_seconds"], cfg["runtime"]["gate_poll_seconds"]); gate = validate_development_gate(cfg, output, freeze_record)
        wait_for_terminals([output / "confirmation"], ["COMPLETE.json", "BLOCKED.json"], cfg["runtime"]["gate_timeout_seconds"], cfg["runtime"]["gate_poll_seconds"])
        if (output / "confirmation/BLOCKED.json").is_file():
            if gate["confirmation_authorized"]:
                raise RuntimeError("authorized confirmation unexpectedly blocked")
            validate_blocked_confirmation(cfg, output / "confirmation", freeze_record, sha(gate_path))
            confirmation = None; confirmed = False; status = "DEVELOPMENT_STOP"
        else:
            if not gate["confirmation_authorized"]:
                raise RuntimeError("unauthorized confirmation was executed")
            validate_complete(cfg, output / "confirmation", "confirmation", freeze_record, gate_hash=sha(gate_path)); confirmation = summarize(cfg, readjl(output / "confirmation/metrics.jsonl"), "confirmation"); confirmed = bool(gate["confirmation_authorized"] and confirmation["pass"]); status = "TECHNICAL_POSITIVE_CONTROL_CONFIRMED" if confirmed else "CONFIRMATION_STOP"
        exjson(target, {"schema_version": "canonical_induction_circuit_v1_final", "status": status, "development": gate["summary"], "confirmation": confirmation, "technical_positive_control_confirmed": confirmed, "claim_scope": "SINGLE_MODEL_GPT2_CANONICAL_INDUCTION_PIPELINE_ONLY", "general_method_claim": False, "minimum_families_for_future_general_claim": cfg["scope"]["minimum_families_for_any_future_general_claim"], "representation_methods_evaluated": False, "training_performed": False, "future_methods_automatically_authorized": False, "ioi_v1_modified": False})
    except Exception as exc:
        publish(target.parent / "FAILED.json", {"stage": "final", "error_type": type(exc).__name__, "error": str(exc), "traceback": traceback.format_exc()}); raise


def main() -> None:
    parser = argparse.ArgumentParser(); parser.add_argument("command", choices=["prepare", "preservation-verify", "cache-preflight", "preflight", "freeze", "verify-freeze", "review-binding", "worker", "development-gate", "final"]); parser.add_argument("--config", type=Path, default=DEFAULT); parser.add_argument("--output", type=Path); parser.add_argument("--stage", choices=["development", "confirmation"]); parser.add_argument("--pre-gate", action="store_true"); args = parser.parse_args()
    if args.command == "prepare": prepare(args.config, args.output)
    elif args.command == "preservation-verify": preservation_verify(loadj(args.config)); print(json.dumps({"status": "PASS"}))
    elif args.command == "cache-preflight": cache_preflight(args.config)
    elif args.command == "preflight": preflight(args.config, include_confirmation=not args.pre_gate); print(json.dumps({"status": "PASS", "confirmation_payload_verified": not args.pre_gate}))
    elif args.command == "freeze": freeze(args.config)
    elif args.command == "verify-freeze": print(json.dumps({"status": "PASS", "inventory": verify_freeze(args.config, include_confirmation=not args.pre_gate)["candidate_inventory_sha256"], "confirmation_payload_verified": not args.pre_gate}, indent=2))
    elif args.command == "review-binding":
        cfg = loadj(args.config)
        validate_review_binding(ROOT / cfg["runtime"]["freeze"], ROOT / cfg["runtime"]["candidate_review"], ROOT / cfg["runtime"]["frozen_review"], ROOT / cfg["runtime"]["review_binding"])
        print(json.dumps({"status": "PASS"}))
    elif args.command == "worker": worker(args.config, args.stage or "")
    elif args.command == "development-gate": development_gate(args.config)
    else: final(args.config)


if __name__ == "__main__":
    main()
