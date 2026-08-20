#!/usr/bin/env python3
"""Prospective IOI behavior and full-residual intervention positive control."""
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
DEFAULT = ROOT / "configs/known_mechanism_ioi_v1/run.json"


def native(x: Any) -> Any:
    if isinstance(x, np.generic):
        return x.item()
    if isinstance(x, dict):
        return {str(k): native(v) for k, v in x.items()}
    if isinstance(x, (list, tuple)):
        return [native(v) for v in x]
    return x


def canon(x: Any) -> bytes:
    return json.dumps(native(x), sort_keys=True, separators=(",", ":"), allow_nan=False).encode()


def loadj(path: Path) -> Any:
    return json.loads(path.read_text())


def sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(8 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def stable(seed: int, *parts: Any) -> int:
    value = "|".join(map(str, (seed,) + parts)).encode()
    return int.from_bytes(hashlib.sha256(value).digest()[:8], "little") % (2**32)


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


def write_npz(path: Path, **arrays: np.ndarray) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + f".tmp.{os.getpid()}.{time.time_ns()}")
    fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    try:
        with os.fdopen(fd, "wb") as handle:
            np.savez_compressed(handle, **arrays)
            handle.flush()
            os.fsync(handle.fileno())
        os.link(tmp, path)
    finally:
        tmp.unlink(missing_ok=True)


def require_offline() -> None:
    for key in ("HF_DATASETS_OFFLINE", "HF_HUB_OFFLINE", "TRANSFORMERS_OFFLINE"):
        if os.environ.get(key) != "1":
            raise RuntimeError(f"offline environment required: {key}=1")


def model_spec(cfg: Mapping[str, Any], key: str) -> dict[str, Any]:
    matches = [dict(x) for x in cfg["models"] if x["key"] == key]
    if len(matches) != 1:
        raise RuntimeError(f"unregistered model: {key}")
    return matches[0]


def preservation_verify(cfg: Mapping[str, Any]) -> None:
    for record in cfg["preservation"]["records"]:
        path = ROOT / record["path"]
        if not path.is_file() or sha(path) != record["sha256"]:
            raise RuntimeError(f"preservation drift: {record['path']}")
    closure = loadj(ROOT / "reports/naturalistic_endpoint_program_closure_v1.json")
    if closure["status"] != cfg["preservation"]["required_closure_status"]:
        raise RuntimeError("endpoint closure status drift")
    for path in cfg["preservation"]["forbid_paths"]:
        if (ROOT / path).exists():
            raise RuntimeError(f"forbidden endpoint retry exists: {path}")


def _prompt(template: str, a: str, b: str, place: str, obj: str) -> str:
    return template.format(A=a, B=b, place=place, object=obj)


def raw_rows(cfg: Mapping[str, Any], stage: str) -> list[dict[str, Any]]:
    panel = cfg["panel"][stage]
    names, places, objects = panel["names"], panel["places"], panel["objects"]
    sets, per_set = int(panel["sets"]), int(panel["rows_per_set"])
    if sets != 4 or per_set != 16 or len(names) != sets * 8:
        raise RuntimeError("registered panel dimensions drift")
    rows: list[dict[str, Any]] = []
    for template_index, template in enumerate(panel["templates"]):
        for set_index in range(sets):
            block = names[set_index * 8 : (set_index + 1) * 8]
            for row_index in range(per_set):
                a = block[row_index % 8]
                b = block[(row_index + 1 + row_index // 8) % 8]
                place_index = (row_index + template_index + set_index) % len(places)
                object_index = (2 * row_index + template_index + set_index) % len(objects)
                sham_place_index = (place_index + 1) % len(places)
                sham_object_index = (object_index + 3) % len(objects)
                base = _prompt(template, a, b, places[place_index], objects[object_index])
                counter = _prompt(template, b, a, places[place_index], objects[object_index])
                sham = _prompt(template, a, b, places[sham_place_index], objects[sham_object_index])
                component_id = f"{stage}:t{template_index}:s{set_index}:r{row_index}:{a}:{b}"
                rows.append(
                    {
                        "stage": stage,
                        "template_index": template_index,
                        "set_index": set_index,
                        "row_index": row_index,
                        "component_id": component_id,
                        "component_block": f"{stage}:t{template_index}:s{set_index}",
                        "answer_a": a,
                        "answer_b": b,
                        "place": places[place_index],
                        "object": objects[object_index],
                        "sham_place": places[sham_place_index],
                        "sham_object": objects[sham_object_index],
                        "base_prompt": base,
                        "counterfactual_prompt": counter,
                        "sham_prompt": sham,
                    }
                )
    return rows


def load_tokenizers(cfg: Mapping[str, Any]) -> dict[str, Any]:
    require_offline()
    from transformers import AutoTokenizer

    result = {}
    for spec in cfg["models"]:
        tokenizer = AutoTokenizer.from_pretrained(
            spec["name"], revision=spec["revision"], local_files_only=True, use_fast=True
        )
        if tokenizer.pad_token_id is None:
            tokenizer.pad_token = tokenizer.eos_token
        tokenizer.padding_side = "right"
        result[spec["key"]] = tokenizer
    return result


def prepare(config: Path, output: Path | None = None) -> None:
    cfg = loadj(config)
    preservation_verify(cfg)
    root = output or ROOT / cfg["runtime"]["prepared_root"]
    if root.exists():
        raise FileExistsError(root)
    root.mkdir(parents=True)
    tokenizers = load_tokenizers(cfg)
    raw = {stage: raw_rows(cfg, stage) for stage in ("development", "confirmation")}
    dev, confirmation = cfg["panel"]["development"], cfg["panel"]["confirmation"]
    for field in ("names", "places", "objects", "templates"):
        if set(dev[field]) & set(confirmation[field]):
            raise RuntimeError(f"development/confirmation {field} overlap")
    files: dict[str, str] = {}
    for stage, rows in raw.items():
        raw_path = root / f"{stage}_raw.jsonl"
        writejl(raw_path, rows)
        files[raw_path.name] = sha(raw_path)
        for model, tokenizer in tokenizers.items():
            encoded = []
            for row in rows:
                prompt_ids = {
                    name: list(tokenizer(row[f"{name}_prompt"], add_special_tokens=False)["input_ids"])
                    for name in cfg["panel"]["conditions"]
                }
                answer_a = list(tokenizer(" " + row["answer_a"], add_special_tokens=False)["input_ids"])
                answer_b = list(tokenizer(" " + row["answer_b"], add_special_tokens=False)["input_ids"])
                lengths = {len(ids) for ids in prompt_ids.values()}
                if len(lengths) != 1 or next(iter(lengths)) > cfg["panel"]["maximum_length"]:
                    raise RuntimeError(f"condition token length mismatch: {model}/{row['component_id']}")
                if len(answer_a) != 1 or len(answer_b) != 1 or answer_a == answer_b:
                    raise RuntimeError(f"answer token gate: {model}/{row['component_id']}")
                prefix = [tokenizer.bos_token_id] if tokenizer.bos_token_id is not None else []
                encoded.append(
                    row
                    | {f"{name}_prompt_ids": prefix + ids for name, ids in prompt_ids.items()}
                    | {"answer_a_id": answer_a[0], "answer_b_id": answer_b[0]}
                )
            path = root / f"{stage}_{model}.jsonl"
            writejl(path, encoded)
            files[path.name] = sha(path)
    audit = {
        "schema_version": "known_mechanism_ioi_v1_prescore",
        "selection_firewall": "TOKENIZER_ONLY_NO_MODEL_FORWARD",
        "rows": {stage: len(rows) for stage, rows in raw.items()},
        "development_confirmation_disjoint": True,
        "all_conditions_equal_token_length": True,
        "all_answers_single_token_all_models": True,
        "counts_per_template_set": 16,
        "files": files,
    }
    exjson(root / "PRESCORE.json", audit)
    print(json.dumps(audit, indent=2))


def verify_prepared(cfg: Mapping[str, Any], include_confirmation: bool = True) -> None:
    root = ROOT / cfg["runtime"]["prepared_root"]
    audit = loadj(root / "PRESCORE.json")
    if audit["selection_firewall"] != "TOKENIZER_ONLY_NO_MODEL_FORWARD":
        raise RuntimeError("prepared selection firewall drift")
    if audit["rows"] != {"development": 256, "confirmation": 128}:
        raise RuntimeError("prepared row-count drift")
    for name, digest in audit["files"].items():
        if not include_confirmation and name.startswith("confirmation_"):
            continue
        if sha(root / name) != digest:
            raise RuntimeError(f"prepared artifact drift: {name}")


def _cached_records(snapshot: Path) -> list[dict[str, Any]]:
    indexes = [p for p in (snapshot / "model.safetensors.index.json", snapshot / "pytorch_model.bin.index.json") if p.is_file()]
    weights: set[str] = set()
    for index in indexes:
        weights.update(loadj(index)["weight_map"].values())
    if not weights:
        weights.update(p.name for p in snapshot.iterdir() if p.name.endswith((".safetensors", ".bin")))
    metadata_names = {
        "config.json", "generation_config.json", "tokenizer.json", "tokenizer_config.json",
        "special_tokens_map.json", "vocab.json", "merges.txt", "added_tokens.json",
    }
    selected = set(weights) | {p.name for p in indexes} | {p.name for p in snapshot.iterdir() if p.name in metadata_names}
    if not weights:
        raise RuntimeError(f"no cached model weights: {snapshot}")
    records = []
    for name in sorted(selected):
        path = snapshot / name
        if not path.is_file():
            raise RuntimeError(f"cached asset absent: {name}")
        records.append({"name": name, "bytes": path.stat().st_size, "sha256": sha(path), "resolved_blob": str(path.resolve())})
    return records


def cache_preflight(config: Path) -> None:
    cfg = loadj(config)
    require_offline()
    from huggingface_hub import snapshot_download
    from transformers import AutoConfig, AutoTokenizer

    expected = (Path(os.environ["HF_HOME"]) / "hub").resolve()
    actual = Path(os.environ.get("TRANSFORMERS_CACHE", "")).resolve()
    if actual != expected or cfg["runtime"]["model_cache_root"] != "${HF_HOME}/hub":
        raise RuntimeError("cache root mismatch")
    models = []
    for spec in cfg["models"]:
        snapshot = Path(snapshot_download(spec["name"], revision=spec["revision"], local_files_only=True))
        AutoConfig.from_pretrained(spec["name"], revision=spec["revision"], local_files_only=True)
        AutoTokenizer.from_pretrained(spec["name"], revision=spec["revision"], local_files_only=True)
        models.append({"model": spec["key"], "revision": spec["revision"], "snapshot": str(snapshot), "files": _cached_records(snapshot)})
    payload = {"schema_version": "known_mechanism_ioi_v1_cache", "status": "PASS", "content_hashed": True, "model_cache_root": str(actual), "models": models}
    path = ROOT / cfg["runtime"]["cache_attestation"]
    if path.exists():
        if loadj(path) != payload:
            raise RuntimeError("cache attestation drift")
    else:
        exjson(path, payload)
    print(json.dumps(payload, indent=2))


def inventory(config: Path, cfg: Mapping[str, Any]) -> list[dict[str, Any]]:
    paths = [ROOT / path for path in cfg["candidate_files"]]
    prepared = ROOT / cfg["runtime"]["prepared_root"]
    paths.extend(sorted(p for p in prepared.rglob("*") if p.is_file()))
    paths.append(ROOT / cfg["runtime"]["cache_attestation"])
    unique = sorted(set(paths), key=lambda p: p.relative_to(ROOT).as_posix())
    records = []
    for path in unique:
        if not path.is_file():
            raise RuntimeError(f"candidate artifact absent: {path.relative_to(ROOT)}")
        records.append({"path": path.relative_to(ROOT).as_posix(), "bytes": path.stat().st_size, "sha256": sha(path)})
    return records


def preflight(config: Path, require_review: bool = False) -> None:
    cfg = loadj(config)
    preservation_verify(cfg)
    verify_prepared(cfg)
    keys = [m["key"] for m in cfg["models"]]
    families = [m["family"] for m in cfg["models"]]
    if len(keys) != len(set(keys)) or len(families) != len(set(families)):
        raise RuntimeError("models must map one-to-one to distinct families")
    if any(cfg["scope"][key] for key in ("representation_methods", "training", "v6_3_prompt_retry", "future_method_authorization_in_this_run", "full_residual_patch_is_sparse_circuit_evidence")):
        raise RuntimeError("scope authorization drift")
    if (ROOT / cfg["runtime"]["output_root"]).exists() or (ROOT / cfg["runtime"]["provenance_root"]).exists():
        raise RuntimeError("one-shot runtime namespace exists")
    review = ROOT / cfg["runtime"]["candidate_review"]
    if require_review and (not review.is_file() or review.read_text().splitlines()[0] != "VERDICT: SHIP"):
        raise RuntimeError("candidate SHIP review required")
    if require_review:
        inventory(config, cfg)
    else:
        review_path = cfg["runtime"]["candidate_review"]
        for relative in cfg["candidate_files"]:
            if relative != review_path and not (ROOT / relative).is_file():
                raise RuntimeError(f"candidate artifact absent: {relative}")
        if not (ROOT / cfg["runtime"]["cache_attestation"]).is_file():
            raise RuntimeError("cache attestation absent")
    print(json.dumps({"status": "PASS", "models": keys, "families": families, "prepared": True, "preserved": True}, indent=2))


def freeze(config: Path) -> None:
    cfg = loadj(config)
    preflight(config, require_review=True)
    records = inventory(config, cfg)
    payload = {
        "schema_version": "known_mechanism_ioi_v1_freeze",
        "namespace": cfg["namespace"],
        "config_sha256": sha(config),
        "candidate_inventory": records,
        "candidate_inventory_sha256": hashlib.sha256(canon(records)).hexdigest(),
        "established_task": "indirect_object_identification",
        "full_residual_positive_control_only": True,
        "model_specific_eligibility": True,
        "two_family_barrier": True,
        "representation_methods": False,
        "training": False,
        "one_shot": True,
    }
    exjson(ROOT / cfg["runtime"]["freeze"], payload)
    print(json.dumps(payload, indent=2))


def verify_freeze(config: Path, cfg: Mapping[str, Any] | None = None, include_confirmation: bool = True) -> dict[str, Any]:
    cfg = cfg or loadj(config)
    record = loadj(ROOT / cfg["runtime"]["freeze"])
    if record["config_sha256"] != sha(config):
        raise RuntimeError("frozen candidate drift")
    if include_confirmation:
        if record["candidate_inventory"] != inventory(config, cfg):
            raise RuntimeError("frozen candidate drift")
    else:
        prepared_prefix = cfg["runtime"]["prepared_root"].rstrip("/") + "/confirmation_"
        for item in record["candidate_inventory"]:
            if item["path"].startswith(prepared_prefix):
                continue
            path = ROOT / item["path"]
            if not path.is_file() or path.stat().st_size != item["bytes"] or sha(path) != item["sha256"]:
                raise RuntimeError(f"frozen candidate drift: {item['path']}")
    preservation_verify(cfg)
    verify_prepared(cfg, include_confirmation=include_confirmation)
    return record


def seed_all(seed: int) -> None:
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)
    torch.use_deterministic_algorithms(True, warn_only=True)


def gpu_guard() -> torch.device:
    expected = os.environ.get("EXPECTED_GPU_UUID")
    visible = os.environ.get("CUDA_VISIBLE_DEVICES")
    if not expected or visible != expected:
        raise RuntimeError("UUID-pinned CUDA_VISIBLE_DEVICES/EXPECTED_GPU_UUID required")
    if not torch.cuda.is_available() or torch.cuda.device_count() != 1:
        raise RuntimeError("exactly one visible CUDA device required")
    return torch.device("cuda:0")


def load_model(spec: Mapping[str, Any], device: torch.device) -> Any:
    require_offline()
    from transformers import AutoModelForCausalLM

    model = AutoModelForCausalLM.from_pretrained(
        spec["name"], revision=spec["revision"], local_files_only=True,
        torch_dtype=torch.float32, attn_implementation="eager",
    ).to(device).eval()
    model.config.use_cache = False
    return model


def transformer_block(model: Any, layer: int) -> Any:
    if hasattr(model, "gpt_neox"):
        return model.gpt_neox.layers[layer]
    if hasattr(model, "model") and hasattr(model.model, "layers"):
        return model.model.layers[layer]
    if hasattr(model, "transformer") and hasattr(model.transformer, "h"):
        return model.transformer.h[layer]
    raise RuntimeError("unsupported transformer block layout")


def batch_inputs(rows: Sequence[Mapping[str, Any]], condition: str, pad: int, device: torch.device) -> tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
    seqs = [list(row[f"{condition}_prompt_ids"]) for row in rows]
    length = max(map(len, seqs))
    ids = torch.full((len(seqs), length), pad, dtype=torch.long, device=device)
    mask = torch.zeros_like(ids)
    for index, seq in enumerate(seqs):
        ids[index, : len(seq)] = torch.tensor(seq, dtype=torch.long, device=device)
        mask[index, : len(seq)] = 1
    final = mask.sum(1) - 1
    return ids, mask, final


@torch.no_grad()
def forward_condition(model: Any, rows: Sequence[Mapping[str, Any]], condition: str, layer: int, batch_size: int, pad: int, device: torch.device, donor: np.ndarray | None = None) -> tuple[np.ndarray, np.ndarray]:
    logits_out, hidden_out = [], []
    module = transformer_block(model, layer)
    for start in range(0, len(rows), batch_size):
        batch = rows[start : start + batch_size]
        ids, mask, final = batch_inputs(batch, condition, pad, device)
        arange = torch.arange(len(batch), device=device)
        captured: list[torch.Tensor] = []
        replacement = None if donor is None else torch.from_numpy(np.asarray(donor[start : start + len(batch)], np.float32)).to(device)

        def hook(_module: Any, _inputs: Any, output: Any) -> Any:
            hidden = output[0] if isinstance(output, tuple) else output
            captured.append(hidden.detach()[arange, final].float().cpu())
            if replacement is None:
                return output
            changed = hidden.clone()
            changed[arange, final] = replacement.to(changed.dtype)
            return (changed,) + output[1:] if isinstance(output, tuple) else changed

        handle = module.register_forward_hook(hook)
        try:
            output = model(input_ids=ids, attention_mask=mask, use_cache=False)
        finally:
            handle.remove()
        if len(captured) != 1:
            raise RuntimeError("transformer block capture count drift")
        logits_out.append(output.logits[arange, final].float().cpu().numpy())
        hidden_out.append(captured[0].numpy())
    return np.concatenate(logits_out), np.concatenate(hidden_out)


def advantages(logits: np.ndarray, rows: Sequence[Mapping[str, Any]]) -> np.ndarray:
    return np.asarray([logits[i, row["answer_a_id"]] - logits[i, row["answer_b_id"]] for i, row in enumerate(rows)], dtype=np.float64)


def behavior_metrics(rows: Sequence[Mapping[str, Any]], base: np.ndarray, counter: np.ndarray, sham: np.ndarray, effect_floor: float) -> list[dict[str, Any]]:
    base_adv = advantages(base, rows)
    counter_a_minus_b = advantages(counter, rows)
    sham_adv = advantages(sham, rows)
    output = []
    for index, row in enumerate(rows):
        counter_adv = -counter_a_minus_b[index]
        effect = min(base_adv[index], counter_adv)
        informative = bool(base_adv[index] > 0 and counter_adv > 0 and effect > effect_floor)
        ratio = abs(sham_adv[index] - base_adv[index]) / effect if informative else None
        output.append({k: row[k] for k in ("stage", "template_index", "set_index", "row_index", "component_id", "component_block")} | {
            "base_advantage": float(base_adv[index]), "counterfactual_advantage": float(counter_adv),
            "counterfactual_a_minus_b": float(counter_a_minus_b[index]), "sham_advantage": float(sham_adv[index]),
            "effect": float(effect), "informative": informative, "sham_ratio": None if ratio is None else float(ratio),
        })
    return output


def patch_metrics(rows: Sequence[Mapping[str, Any]], behavior: Sequence[Mapping[str, Any]], counter_patch: np.ndarray, sham_patch: np.ndarray) -> list[dict[str, Any]]:
    counter_patch_adv = advantages(counter_patch, rows)
    sham_patch_adv = advantages(sham_patch, rows)
    output = []
    for index, (row, metric) in enumerate(zip(rows, behavior, strict=True)):
        denom = metric["base_advantage"] - metric["counterfactual_a_minus_b"]
        informative = bool(metric["informative"] and denom > 0)
        recovery = (metric["base_advantage"] - counter_patch_adv[index]) / denom if informative else None
        sham_movement = abs(metric["base_advantage"] - sham_patch_adv[index]) / denom if informative else None
        output.append({k: row[k] for k in ("stage", "template_index", "set_index", "row_index", "component_id", "component_block")} | {
            "informative": informative, "denominator": float(denom), "counter_patch_advantage": float(counter_patch_adv[index]),
            "sham_patch_advantage": float(sham_patch_adv[index]), "recovery": None if recovery is None else float(recovery),
            "sham_movement": None if sham_movement is None else float(sham_movement),
        })
    return output


def hierarchical_interval(rows: Sequence[Mapping[str, Any]], field: str, draws: int, seed: int) -> dict[str, float] | None:
    valid = [row for row in rows if row.get(field) is not None and np.isfinite(row[field])]
    if not valid:
        return None
    groups = sorted({int(row["set_index"]) for row in valid})
    by_group = {group: [float(row[field]) for row in valid if int(row["set_index"]) == group] for group in groups}
    rng = np.random.default_rng(seed)
    samples = []
    for _ in range(draws):
        chosen = rng.choice(groups, len(groups), replace=True)
        values = []
        for group in chosen:
            source = by_group[int(group)]
            values.extend(rng.choice(source, len(source), replace=True).tolist())
        samples.append(float(np.mean(values)))
    return {"point": float(np.mean([float(row[field]) for row in valid])), "lower": float(np.quantile(samples, 0.025)), "upper": float(np.quantile(samples, 0.975)), "draws": draws}


def summarize_behavior(rows: Sequence[Mapping[str, Any]], gate: Mapping[str, Any], seed: int) -> dict[str, Any]:
    templates = sorted({int(row["template_index"]) for row in rows})
    summaries = []
    for template in templates:
        subset = [row for row in rows if int(row["template_index"]) == template]
        counts = {str(group): sum(bool(row["informative"]) for row in subset if int(row["set_index"]) == group) for group in range(4)}
        total = sum(counts.values())
        interval = hierarchical_interval(subset, "sham_ratio", int(gate["bootstrap_draws"]), stable(seed, "behavior", template))
        passed = bool(
            all(count >= int(gate["minimum_informative_per_set"]) for count in counts.values())
            and total >= int(gate["minimum_informative_per_template"])
            and interval is not None
            and interval["point"] <= float(gate["sham_ratio_point_max_inclusive"])
            and interval["upper"] < float(gate["sham_ratio_upper_strict"])
        )
        summaries.append({"template_index": template, "informative_per_set": counts, "informative_total": total, "sham_ratio": interval, "pass": passed})
    return {"templates": summaries, "pass": bool(summaries and all(row["pass"] for row in summaries))}


def summarize_patch(rows: Sequence[Mapping[str, Any]], gate: Mapping[str, Any], seed: int) -> dict[str, Any]:
    templates = sorted({int(row["template_index"]) for row in rows})
    summaries = []
    for template in templates:
        subset = [row for row in rows if int(row["template_index"]) == template]
        counts = {str(group): sum(bool(row["informative"]) for row in subset if int(row["set_index"]) == group) for group in range(4)}
        total = sum(counts.values())
        recovery = hierarchical_interval(subset, "recovery", int(gate["bootstrap_draws"]), stable(seed, "patch_recovery", template))
        sham = hierarchical_interval(subset, "sham_movement", int(gate["bootstrap_draws"]), stable(seed, "patch_sham", template))
        passed = bool(
            all(count >= int(gate["minimum_informative_per_set"]) for count in counts.values())
            and total >= int(gate["minimum_informative_per_template"])
            and recovery is not None and sham is not None
            and recovery["point"] >= float(gate["recovery_point_min_inclusive"])
            and recovery["lower"] > float(gate["recovery_lower_strict"])
            and sham["point"] <= float(gate["sham_movement_point_max_inclusive"])
            and sham["upper"] < float(gate["sham_movement_upper_strict"])
        )
        summaries.append({"template_index": template, "informative_per_set": counts, "informative_total": total, "recovery": recovery, "sham_movement": sham, "pass": passed})
    return {"templates": summaries, "pass": bool(summaries and all(row["pass"] for row in summaries))}


def runtime_record(device: torch.device) -> dict[str, Any]:
    return {"device": str(device), "gpu_name": torch.cuda.get_device_name(0), "cuda_visible_devices": os.environ.get("CUDA_VISIBLE_DEVICES"), "expected_gpu_uuid": os.environ.get("EXPECTED_GPU_UUID"), "torch": torch.__version__}


def run_behavior(config: Path, model_key: str) -> None:
    cfg = loadj(config)
    freeze_record = verify_freeze(config, cfg, include_confirmation=False)
    spec = model_spec(cfg, model_key)
    out = ROOT / cfg["runtime"]["output_root"] / "development" / "behavior" / model_key
    if out.exists():
        raise FileExistsError(out)
    out.mkdir(parents=True)
    try:
        device = gpu_guard()
        seed_all(stable(cfg["seed"], "development_behavior", model_key))
        exjson(out / "STARTED.json", {"model": model_key, "freeze_sha256": sha(ROOT / cfg["runtime"]["freeze"]), "runtime": runtime_record(device)})
        rows = readjl(ROOT / cfg["runtime"]["prepared_root"] / f"development_{model_key}.jsonl")
        model = load_model(spec, device)
        from transformers import AutoTokenizer
        tokenizer = AutoTokenizer.from_pretrained(spec["name"], revision=spec["revision"], local_files_only=True)
        if tokenizer.pad_token_id is None:
            tokenizer.pad_token = tokenizer.eos_token
        results = {}
        hidden = {}
        for condition in cfg["panel"]["conditions"]:
            results[condition], hidden[condition] = forward_condition(model, rows, condition, int(spec["patch_layer"]), int(spec["batch_size"]), int(tokenizer.pad_token_id), device)
        metrics = behavior_metrics(rows, results["base"], results["counterfactual"], results["sham"], float(cfg["behavior_gate"]["effect_floor_strict"]))
        writejl(out / "metrics.jsonl", metrics)
        write_npz(out / "activations.npz", base=hidden["base"], counterfactual=hidden["counterfactual"], sham=hidden["sham"])
        complete = {"schema_version": "known_mechanism_ioi_v1_behavior_complete", "model": model_key, "rows": len(rows), "metrics_sha256": sha(out / "metrics.jsonl"), "activations_sha256": sha(out / "activations.npz"), "freeze_sha256": sha(ROOT / cfg["runtime"]["freeze"]), "freeze_inventory_sha256": freeze_record["candidate_inventory_sha256"], "model_forwards": True, "training": False, "representation_methods": False}
        exjson(out / "COMPLETE.json", complete)
    except Exception as exc:
        publish(out / "FAILED.json", {"schema_version": "known_mechanism_ioi_v1_failure", "stage": "development_behavior", "model": model_key, "error_type": type(exc).__name__, "error": str(exc), "traceback": traceback.format_exc()})
        raise


def wait_for(paths: Sequence[Path], timeout: int, poll: int) -> None:
    deadline = time.monotonic() + timeout
    while True:
        if all(path.is_file() for path in paths):
            return
        for path in paths:
            parent = path.parent
            if (parent / "FAILED.json").is_file():
                raise RuntimeError(f"upstream failure: {parent / 'FAILED.json'}")
        if time.monotonic() >= deadline:
            raise TimeoutError(f"timeout waiting for {[str(path) for path in paths]}")
        time.sleep(poll)


def wait_for_terminals(roots: Sequence[Path], allowed: Sequence[str], timeout: int, poll: int) -> dict[Path, Path]:
    deadline = time.monotonic() + timeout
    while True:
        found: dict[Path, Path] = {}
        for root in roots:
            failure = root / "FAILED.json"
            if failure.is_file():
                raise RuntimeError(f"upstream failure: {failure}")
            hits = [root / name for name in allowed if (root / name).is_file()]
            if len(hits) > 1:
                raise RuntimeError(f"multiple terminal artifacts: {root}")
            if hits:
                found[root] = hits[0]
        if len(found) == len(roots):
            return found
        if time.monotonic() >= deadline:
            missing = [str(root) for root in roots if root not in found]
            raise TimeoutError(f"timeout waiting for terminal artifacts: {missing}")
        time.sleep(poll)


def validate_behavior_completion(cfg: Mapping[str, Any], model_key: str, root: Path, freeze_record: Mapping[str, Any]) -> dict[str, Any]:
    complete = loadj(root / "COMPLETE.json")
    expected_freeze = sha(ROOT / cfg["runtime"]["freeze"])
    checks = {
        "schema_version": "known_mechanism_ioi_v1_behavior_complete",
        "model": model_key,
        "rows": 256,
        "freeze_sha256": expected_freeze,
        "freeze_inventory_sha256": freeze_record["candidate_inventory_sha256"],
        "model_forwards": True,
        "training": False,
        "representation_methods": False,
    }
    if any(complete.get(key) != value for key, value in checks.items()):
        raise RuntimeError(f"behavior completion metadata mismatch: {model_key}")
    if sha(root / "metrics.jsonl") != complete.get("metrics_sha256") or sha(root / "activations.npz") != complete.get("activations_sha256"):
        raise RuntimeError(f"behavior completion artifact mismatch: {model_key}")
    return complete


def behavior_gate(config: Path) -> None:
    cfg = loadj(config)
    freeze_record = verify_freeze(config, cfg, include_confirmation=False)
    out = ROOT / cfg["runtime"]["output_root"]
    target = out / "gates" / "behavior" / "result.json"
    try:
        paths = [out / "development" / "behavior" / spec["key"] / "COMPLETE.json" for spec in cfg["models"]]
        wait_for(paths, int(cfg["runtime"]["gate_timeout_seconds"]), int(cfg["runtime"]["gate_poll_seconds"]))
        models = []
        for spec in cfg["models"]:
            root = out / "development" / "behavior" / spec["key"]
            validate_behavior_completion(cfg, spec["key"], root, freeze_record)
            rows = readjl(root / "metrics.jsonl")
            summary = summarize_behavior(rows, cfg["behavior_gate"], stable(cfg["seed"], "behavior_gate", spec["key"]))
            models.append({"model": spec["key"], "family": spec["family"], **summary})
        eligible = [row["model"] for row in models if row["pass"]]
        families = [row["family"] for row in models if row["pass"]]
        general = len(set(families)) >= int(cfg["behavior_gate"]["minimum_families"])
        exjson(target, {"schema_version": "known_mechanism_ioi_v1_behavior_gate", "status": "PASS" if general else "STOP", "models": models, "eligible_models": eligible, "eligible_families": families, "general_gate_pass": general, "patch_stage_authorized": general, "freeze_sha256": sha(ROOT / cfg["runtime"]["freeze"]), "freeze_inventory_sha256": freeze_record["candidate_inventory_sha256"], "training_authorized": False, "representation_methods_authorized": False})
    except Exception as exc:
        publish(target.parent / "FAILED.json", {"stage": "behavior_gate", "error_type": type(exc).__name__, "error": str(exc), "traceback": traceback.format_exc()})
        raise


def run_patch(config: Path, model_key: str) -> None:
    cfg = loadj(config)
    freeze_record = verify_freeze(config, cfg, include_confirmation=False)
    output = ROOT / cfg["runtime"]["output_root"]
    out = output / "development" / "patch" / model_key
    if out.exists():
        raise FileExistsError(out)
    out.mkdir(parents=True)
    try:
        gate_path = output / "gates" / "behavior" / "result.json"
        wait_for([gate_path], int(cfg["runtime"]["gate_timeout_seconds"]), int(cfg["runtime"]["gate_poll_seconds"]))
        gate = loadj(gate_path)
        if not gate["general_gate_pass"] or model_key not in gate["eligible_models"]:
            exjson(out / "BLOCKED.json", {"stage": "development_patch", "model": model_key, "reason": "MODEL_OR_GENERAL_BEHAVIOR_GATE_INELIGIBLE", "model_loaded": False})
            return
        behavior_dir = output / "development" / "behavior" / model_key
        complete = validate_behavior_completion(cfg, model_key, behavior_dir, freeze_record)
        device = gpu_guard()
        spec = model_spec(cfg, model_key)
        seed_all(stable(cfg["seed"], "development_patch", model_key))
        exjson(out / "STARTED.json", {"model": model_key, "behavior_complete_sha256": sha(behavior_dir / "COMPLETE.json"), "runtime": runtime_record(device)})
        rows = readjl(ROOT / cfg["runtime"]["prepared_root"] / f"development_{model_key}.jsonl")
        behavior = readjl(behavior_dir / "metrics.jsonl")
        with np.load(behavior_dir / "activations.npz") as cache:
            counter_donor, sham_donor = np.asarray(cache["counterfactual"], np.float32), np.asarray(cache["sham"], np.float32)
        model = load_model(spec, device)
        from transformers import AutoTokenizer
        tokenizer = AutoTokenizer.from_pretrained(spec["name"], revision=spec["revision"], local_files_only=True)
        if tokenizer.pad_token_id is None:
            tokenizer.pad_token = tokenizer.eos_token
        counter_logits, _ = forward_condition(model, rows, "base", int(spec["patch_layer"]), int(spec["batch_size"]), int(tokenizer.pad_token_id), device, donor=counter_donor)
        sham_logits, _ = forward_condition(model, rows, "base", int(spec["patch_layer"]), int(spec["batch_size"]), int(tokenizer.pad_token_id), device, donor=sham_donor)
        metrics = patch_metrics(rows, behavior, counter_logits, sham_logits)
        writejl(out / "metrics.jsonl", metrics)
        exjson(out / "COMPLETE.json", {"schema_version": "known_mechanism_ioi_v1_patch_complete", "model": model_key, "rows": len(rows), "metrics_sha256": sha(out / "metrics.jsonl"), "behavior_complete_sha256": sha(behavior_dir / "COMPLETE.json"), "behavior_gate_sha256": sha(gate_path), "freeze_sha256": sha(ROOT / cfg["runtime"]["freeze"]), "freeze_inventory_sha256": freeze_record["candidate_inventory_sha256"], "full_residual_positive_control_only": True, "training": False, "representation_methods": False})
    except Exception as exc:
        publish(out / "FAILED.json", {"stage": "development_patch", "model": model_key, "error_type": type(exc).__name__, "error": str(exc), "traceback": traceback.format_exc()})
        raise


def patch_gate(config: Path) -> None:
    cfg = loadj(config)
    freeze_record = verify_freeze(config, cfg, include_confirmation=False)
    out = ROOT / cfg["runtime"]["output_root"]
    target = out / "gates" / "patch" / "result.json"
    try:
        behavior_path = out / "gates" / "behavior" / "result.json"
        wait_for([behavior_path], int(cfg["runtime"]["gate_timeout_seconds"]), int(cfg["runtime"]["gate_poll_seconds"]))
        behavior = loadj(behavior_path)
        terminals = [out / "development" / "patch" / spec["key"] for spec in cfg["models"]]
        wait_for_terminals(terminals, ["COMPLETE.json", "BLOCKED.json"], int(cfg["runtime"]["gate_timeout_seconds"]), int(cfg["runtime"]["gate_poll_seconds"]))
        models = []
        for spec, root in zip(cfg["models"], terminals, strict=True):
            if (root / "BLOCKED.json").is_file():
                models.append({"model": spec["key"], "family": spec["family"], "pass": False, "blocked": True, "templates": []})
            else:
                complete = loadj(root / "COMPLETE.json")
                behavior_complete = out / "development" / "behavior" / spec["key"] / "COMPLETE.json"
                expected = {"schema_version": "known_mechanism_ioi_v1_patch_complete", "model": spec["key"], "rows": 256, "behavior_gate_sha256": sha(behavior_path), "freeze_sha256": sha(ROOT / cfg["runtime"]["freeze"]), "freeze_inventory_sha256": freeze_record["candidate_inventory_sha256"], "full_residual_positive_control_only": True, "training": False, "representation_methods": False}
                if any(complete.get(key) != value for key, value in expected.items()) or sha(root / "metrics.jsonl") != complete.get("metrics_sha256") or sha(behavior_complete) != complete.get("behavior_complete_sha256"):
                    raise RuntimeError(f"patch completion lineage mismatch: {spec['key']}")
                rows = readjl(root / "metrics.jsonl")
                summary = summarize_patch(rows, cfg["patch_gate"], stable(cfg["seed"], "patch_gate", spec["key"]))
                models.append({"model": spec["key"], "family": spec["family"], "blocked": False, **summary})
        eligible = [row["model"] for row in models if row["pass"]]
        families = [row["family"] for row in models if row["pass"]]
        general = bool(behavior["general_gate_pass"] and len(set(families)) >= int(cfg["patch_gate"]["minimum_families"]))
        exjson(target, {"schema_version": "known_mechanism_ioi_v1_patch_gate", "status": "PASS" if general else "STOP", "models": models, "eligible_models": eligible, "eligible_families": families, "general_gate_pass": general, "confirmation_authorized": general, "behavior_gate_sha256": sha(behavior_path), "freeze_sha256": sha(ROOT / cfg["runtime"]["freeze"]), "freeze_inventory_sha256": freeze_record["candidate_inventory_sha256"], "full_residual_positive_control_only": True, "training_authorized": False, "representation_methods_authorized": False})
    except Exception as exc:
        publish(target.parent / "FAILED.json", {"stage": "patch_gate", "error_type": type(exc).__name__, "error": str(exc), "traceback": traceback.format_exc()})
        raise


def run_confirmation(config: Path, model_key: str) -> None:
    cfg = loadj(config)
    verify_freeze(config, cfg, include_confirmation=False)
    output = ROOT / cfg["runtime"]["output_root"]
    out = output / "confirmation" / model_key
    if out.exists():
        raise FileExistsError(out)
    out.mkdir(parents=True)
    try:
        gate_path = output / "gates" / "patch" / "result.json"
        wait_for([gate_path], int(cfg["runtime"]["gate_timeout_seconds"]), int(cfg["runtime"]["gate_poll_seconds"]))
        gate = loadj(gate_path)
        if not gate["confirmation_authorized"] or model_key not in gate["eligible_models"]:
            exjson(out / "BLOCKED.json", {"stage": "confirmation", "model": model_key, "reason": "MODEL_OR_GENERAL_PATCH_GATE_INELIGIBLE", "model_loaded": False, "confirmation_rows_loaded": False})
            return
        freeze_record = verify_freeze(config, cfg, include_confirmation=True)
        device = gpu_guard()
        spec = model_spec(cfg, model_key)
        seed_all(stable(cfg["seed"], "confirmation", model_key))
        exjson(out / "STARTED.json", {"model": model_key, "patch_gate_sha256": sha(gate_path), "runtime": runtime_record(device)})
        rows = readjl(ROOT / cfg["runtime"]["prepared_root"] / f"confirmation_{model_key}.jsonl")
        model = load_model(spec, device)
        from transformers import AutoTokenizer
        tokenizer = AutoTokenizer.from_pretrained(spec["name"], revision=spec["revision"], local_files_only=True)
        if tokenizer.pad_token_id is None:
            tokenizer.pad_token = tokenizer.eos_token
        logits, hidden = {}, {}
        for condition in cfg["panel"]["conditions"]:
            logits[condition], hidden[condition] = forward_condition(model, rows, condition, int(spec["patch_layer"]), int(spec["batch_size"]), int(tokenizer.pad_token_id), device)
        behavior = behavior_metrics(rows, logits["base"], logits["counterfactual"], logits["sham"], float(cfg["behavior_gate"]["effect_floor_strict"]))
        counter_patch, _ = forward_condition(model, rows, "base", int(spec["patch_layer"]), int(spec["batch_size"]), int(tokenizer.pad_token_id), device, donor=hidden["counterfactual"])
        sham_patch, _ = forward_condition(model, rows, "base", int(spec["patch_layer"]), int(spec["batch_size"]), int(tokenizer.pad_token_id), device, donor=hidden["sham"])
        patch = patch_metrics(rows, behavior, counter_patch, sham_patch)
        writejl(out / "behavior_metrics.jsonl", behavior)
        writejl(out / "patch_metrics.jsonl", patch)
        exjson(out / "COMPLETE.json", {"schema_version": "known_mechanism_ioi_v1_confirmation_complete", "model": model_key, "rows": len(rows), "behavior_metrics_sha256": sha(out / "behavior_metrics.jsonl"), "patch_metrics_sha256": sha(out / "patch_metrics.jsonl"), "patch_gate_sha256": sha(gate_path), "freeze_sha256": sha(ROOT / cfg["runtime"]["freeze"]), "freeze_inventory_sha256": freeze_record["candidate_inventory_sha256"], "training": False, "representation_methods": False})
    except Exception as exc:
        publish(out / "FAILED.json", {"stage": "confirmation", "model": model_key, "error_type": type(exc).__name__, "error": str(exc), "traceback": traceback.format_exc()})
        raise


def final(config: Path) -> None:
    cfg = loadj(config)
    freeze_record = verify_freeze(config, cfg, include_confirmation=False)
    out = ROOT / cfg["runtime"]["output_root"]
    target = out / "final" / "result.json"
    try:
        patch_gate_path = out / "gates" / "patch" / "result.json"
        wait_for([patch_gate_path], int(cfg["runtime"]["gate_timeout_seconds"]), int(cfg["runtime"]["gate_poll_seconds"]))
        patch_gate_result = loadj(patch_gate_path)
        roots = [out / "confirmation" / spec["key"] for spec in cfg["models"]]
        wait_for_terminals(roots, ["COMPLETE.json", "BLOCKED.json"], int(cfg["runtime"]["gate_timeout_seconds"]), int(cfg["runtime"]["gate_poll_seconds"]))
        confirmation_models = []
        for spec, root in zip(cfg["models"], roots, strict=True):
            if (root / "BLOCKED.json").is_file():
                confirmation_models.append({"model": spec["key"], "family": spec["family"], "behavior_pass": False, "patch_pass": False, "pass": False, "blocked": True})
                continue
            complete = loadj(root / "COMPLETE.json")
            expected = {"schema_version": "known_mechanism_ioi_v1_confirmation_complete", "model": spec["key"], "rows": 128, "patch_gate_sha256": sha(patch_gate_path), "freeze_sha256": sha(ROOT / cfg["runtime"]["freeze"]), "freeze_inventory_sha256": freeze_record["candidate_inventory_sha256"], "training": False, "representation_methods": False}
            if any(complete.get(key) != value for key, value in expected.items()) or sha(root / "behavior_metrics.jsonl") != complete.get("behavior_metrics_sha256") or sha(root / "patch_metrics.jsonl") != complete.get("patch_metrics_sha256"):
                raise RuntimeError(f"confirmation completion lineage mismatch: {spec['key']}")
            behavior = summarize_behavior(readjl(root / "behavior_metrics.jsonl"), cfg["behavior_gate"], stable(cfg["seed"], "confirmation_behavior", spec["key"]))
            patch = summarize_patch(readjl(root / "patch_metrics.jsonl"), cfg["patch_gate"], stable(cfg["seed"], "confirmation_patch", spec["key"]))
            confirmation_models.append({"model": spec["key"], "family": spec["family"], "behavior": behavior, "patch": patch, "behavior_pass": behavior["pass"], "patch_pass": patch["pass"], "pass": bool(behavior["pass"] and patch["pass"]), "blocked": False})
        families = [row["family"] for row in confirmation_models if row["pass"]]
        general = bool(patch_gate_result["general_gate_pass"] and len(set(families)) >= int(cfg["confirmation_gate"]["minimum_families"]))
        status = "CONFIRMED_POSITIVE_CONTROL" if general else ("DEVELOPMENT_STOP" if not patch_gate_result["general_gate_pass"] else "CONFIRMATION_NOT_REPLICATED")
        exjson(target, {"schema_version": "known_mechanism_ioi_v1_final", "status": status, "development_patch_gate": patch_gate_result["status"], "confirmation_models": confirmation_models, "eligible_confirmation_families": families, "general_positive_control": general, "claim_scope": "IOI_BEHAVIOR_AND_FULL_RESIDUAL_END_TO_END_POSITIVE_CONTROL_ONLY", "sparse_circuit_identified": False, "representation_methods_evaluated": False, "training_performed": False, "future_method_benchmark_automatically_authorized": False, "v6_2_modified": False, "v6_3_created": False})
    except Exception as exc:
        publish(target.parent / "FAILED.json", {"stage": "final", "error_type": type(exc).__name__, "error": str(exc), "traceback": traceback.format_exc()})
        raise


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=["prepare", "preservation-verify", "cache-preflight", "preflight", "freeze", "verify-freeze", "behavior-worker", "behavior-gate", "patch-worker", "patch-gate", "confirmation-worker", "final"])
    parser.add_argument("--config", type=Path, default=DEFAULT)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--model")
    args = parser.parse_args()
    if args.command == "prepare":
        prepare(args.config, args.output)
    elif args.command == "preservation-verify":
        preservation_verify(loadj(args.config))
        print(json.dumps({"status": "PASS"}))
    elif args.command == "cache-preflight":
        cache_preflight(args.config)
    elif args.command == "preflight":
        preflight(args.config)
    elif args.command == "freeze":
        freeze(args.config)
    elif args.command == "verify-freeze":
        record = verify_freeze(args.config)
        print(json.dumps({"status": "PASS", "candidate_inventory_sha256": record["candidate_inventory_sha256"]}, indent=2))
    elif args.command == "behavior-worker":
        run_behavior(args.config, args.model or "")
    elif args.command == "behavior-gate":
        behavior_gate(args.config)
    elif args.command == "patch-worker":
        run_patch(args.config, args.model or "")
    elif args.command == "patch-gate":
        patch_gate(args.config)
    elif args.command == "confirmation-worker":
        run_confirmation(args.config, args.model or "")
    else:
        final(args.config)


if __name__ == "__main__":
    main()
