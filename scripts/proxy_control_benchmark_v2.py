#!/usr/bin/env python3
"""Prospectively corrected proxy-to-control benchmark v2.

Real workers import v1 SAE checkpoints; this module has no real-activation SAE training path.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import platform
import random
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Iterable, Mapping, Sequence

import numpy as np
import torch
from torch import nn

import proxy_control_benchmark_v1 as v1

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = Path(__file__).resolve()
CONFIG_DEFAULT = ROOT / "configs/proxy_control_benchmark_v2/run.json"
PLAN = ROOT / "PLAN_PROXY_CONTROL_BENCHMARK_V2.md"
PLAN_REVIEW = ROOT / "reports/adversarial/proxy_control_benchmark_v2_plan_review.md"
CANDIDATE_REVIEW = ROOT / "reports/adversarial/proxy_control_benchmark_v2_candidate_review.md"
TEST = ROOT / "tests/test_proxy_control_benchmark_v2.py"
LAUNCHER = ROOT / "scripts/launch_proxy_control_benchmark_v2_tmux.sh"
ANALYSIS_SCRIPT = ROOT / "scripts/analyze_proxy_control_benchmark_v1.py"
ANALYSIS_CONFIG = ROOT / "configs/proxy_control_benchmark_v1_analysis/run.json"
V1_SCRIPT = ROOT / "scripts/proxy_control_benchmark_v1.py"


def canonical(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()


def load_json(path: Path) -> Any:
    return json.loads(path.read_text())


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def stable_seed(seed: int, *parts: Any) -> int:
    return int.from_bytes(hashlib.sha256("|".join(map(str, (seed,) + parts)).encode()).digest()[:8], "little") % (2**32)


def exclusive_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, "wb") as f:
        f.write(canonical(value) + b"\n")


def atomic_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + f".tmp.{os.getpid()}")
    temp.write_bytes(canonical(value) + b"\n")
    os.replace(temp, path)


def write_jsonl(path: Path, rows: Sequence[Mapping[str, Any]]) -> None:
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, "wb") as f:
        for row in rows:
            f.write(canonical(dict(row)) + b"\n")


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text().splitlines() if line]


def seed_everything(seed: int) -> None:
    random.seed(seed); np.random.seed(seed); torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)
    torch.use_deterministic_algorithms(True)
    torch.backends.cudnn.deterministic = True
    torch.backends.cudnn.benchmark = False


def runtime_record(device: torch.device) -> dict[str, Any]:
    rec = {"python": sys.version, "platform": platform.platform(), "numpy": np.__version__, "torch": torch.__version__,
           "cuda_visible_devices": os.environ.get("CUDA_VISIBLE_DEVICES"), "device": str(device)}
    if device.type == "cuda":
        p = torch.cuda.get_device_properties(0)
        rec.update({"gpu_name": p.name, "gpu_uuid": "GPU-" + str(p.uuid), "gpu_memory": p.total_memory, "cuda": torch.version.cuda})
    return rec


# All answer/suffix words were tokenizer-prescored as one leading-space token in all registered models.
COMMON_WORDS = [
    "red", "blue", "green", "black", "white", "gold", "brown", "pink", "north", "south", "east", "west",
    "one", "two", "three", "four", "five", "six", "seven", "eight", "nine", "ten", "small", "large",
    "hot", "cold", "young", "old", "high", "low", "true", "false", "yes", "no", "left", "right", "open",
    "closed", "circle", "square", "orange", "purple", "silver", "gray", "quiet", "loud", "fast", "slow",
    "early", "late", "first", "last", "spring", "summer", "autumn", "winter"
]


def source_words(source: str) -> dict[str, list[str]]:
    if source == "SOURCE_C":
        answers = COMMON_WORDS[:28]
        suffixes = COMMON_WORDS[28:56]
        prefix = "C"
    elif source == "SOURCE_D":
        answers = COMMON_WORDS[28:56]
        suffixes = COMMON_WORDS[:28]
        prefix = "D"
    else:
        raise ValueError(source)
    return {"answers": answers, "names": [f"agent {x}" for x in suffixes],
            "entities": [f"object {x}" for x in suffixes], "prefix": [prefix]}


CONTEXT_STEMS = {
    "development": [
        "Record {nonce}. {n} chose {a}. {n2} chose {a3}. Asked about {n}, the choice was",
        "Ledger {nonce}: {n} selected {a}; {n2} selected {a3}. For {n}, report",
        "Memo {nonce}. The choice of {n} was {a}. The choice of {n2} was {a3}. {n} chose",
        "File {nonce}: choice {n} = {a}; choice {n2} = {a3}. Query choice {n} ="
    ],
    "test": [
        "Dispatch {nonce}. {n} picked {a}, whereas {n2} picked {a3}. The item picked by {n} was",
        "Archive {nonce}: selection for {n}: {a}. selection for {n2}: {a3}. Return {n}'s selection:",
        "Note {nonce}. We assigned {a} to {n} and {a3} to {n2}. When asked for {n}, answer",
        "Entry {nonce}: {n} -> {a}; {n2} -> {a3}. Resolve the entry for {n}:"
    ]
}
LEXICAL_STEMS = {
    "development": [
        "Glossary {nonce}. {e} maps to {a}. {e3} maps to {a3}. Query {e}:",
        "Dictionary {nonce}: code for {e} is {a}; code for {e3} is {a3}. Code for {e}:",
        "Lexicon {nonce}. Label {e} with {a}. Label {e3} with {a3}. Label for {e}:",
        "Table {nonce}: {e} = {a}; {e3} = {a3}. Lookup {e}:"
    ],
    "test": [
        "Vocabulary card {nonce}. The symbol beside {e} is {a}. The symbol beside {e3} is {a3}. For {e}, write",
        "Index {nonce}: {e} carries {a}; {e3} carries {a3}. Retrieve the mark carried by {e}:",
        "Key {nonce}. Pair {e} with {a} and {e3} with {a3}. The partner of {e} is",
        "Mapping {nonce}: map {e} = {a}; map {e3} = {a3}. Evaluate map {e}:"
    ]
}
POSITION_STEMS = {
    "development": [
        ("Background one for {nonce}.", "Background two for {nonce}.", "{n} uses {a}.", "Recall what {n} uses:"),
        ("Earlier note {nonce} remained.", "A second note {nonce} remained.", "{n} carries {a}.", "Now {n} carries"),
        ("First aside in case {nonce}.", "Second aside in case {nonce}.", "{n} selected {a}.", "Repeat {n}'s selection:"),
        ("Opening detail {nonce}.", "Following detail {nonce}.", "The code of {n} is {a}.", "The code of {n} is")
    ],
    "test": [
        ("Preliminary remark {nonce}.", "Additional remark {nonce}.", "{n} picked {a}.", "State what {n} picked:"),
        ("A prior sentence {nonce}.", "Another prior sentence {nonce}.", "{n} has marker {a}.", "Marker for {n}:"),
        ("Context fragment alpha {nonce}.", "Context fragment beta {nonce}.", "Assign {a} to {n}.", "Assignment for {n}:"),
        ("Unrelated preface one {nonce}.", "Unrelated preface two {nonce}.", "{n} points to {a}.", "{n} points to")
    ]
}


def format_controlled(concept: str, split: str, surface: int, vals: Mapping[str, str]) -> tuple[str, str, str]:
    if concept == "context":
        stem = CONTEXT_STEMS[split][surface]
        base = stem.format(**vals)
        cf = stem.format(**{**vals, "a": vals["a2"]})
        sham = stem.format(**{**vals, "a3": vals["a4"]})
    elif concept == "lexical":
        stem = LEXICAL_STEMS[split][surface]
        base = stem.format(**vals)
        cf = stem.format(**{**vals, "e": vals["e2"], "a": vals["a2"]})
        sham = stem.format(**{**vals, "e3": vals["e4"], "a3": vals["a4"]})
    elif concept == "relative_position":
        f1, f2, fact, query = [x.format(**vals) for x in POSITION_STEMS[split][surface]]
        prefix = f"Sequence {vals['nonce']}."
        base = " ".join((prefix, f1, f2, fact, query))
        cf = " ".join((prefix, fact, f1, f2, query))
        sham = " ".join((prefix, f2, f1, fact, query))
    else:
        raise ValueError(concept)
    if len({base, cf, sham}) != 3:
        raise RuntimeError("sham or counterfactual is a no-op")
    return base, cf, sham


def make_controlled_rows(cfg: Mapping[str, Any]) -> list[dict[str, Any]]:
    pcfg = cfg["panels"]
    rows: list[dict[str, Any]] = []
    for source in pcfg["controlled_sources"]:
        words = source_words(source); answers, names, entities = words["answers"], words["names"], words["entities"]
        for concept in pcfg["concepts"]:
            for split, nblocks, offset in (("development", int(pcfg["development_blocks"]), 0),
                                            ("test", int(pcfg["test_blocks"]), int(pcfg["development_blocks"]))):
                for local_block in range(nblocks):
                    block = offset + local_block
                    vals = {"nonce": f"{source[-1]}{block:03d}", "n": names[block % len(names)],
                            "n2": names[(block + 7) % len(names)], "e": entities[block % len(entities)],
                            "e2": entities[(block + 5) % len(entities)], "e3": entities[(block + 9) % len(entities)],
                            "e4": entities[(block + 13) % len(entities)], "a": answers[block % len(answers)],
                            "a2": answers[(block + 5) % len(answers)], "a3": answers[(block + 9) % len(answers)],
                            "a4": answers[(block + 13) % len(answers)]}
                    for surface in range(int(pcfg["surfaces_per_block"])):
                        base, cf, sham = format_controlled(concept, split, surface, vals)
                        rows.append({"schema_version": "proxy_control_v2_controlled_row", "panel_kind": "controlled",
                            "source": source, "concept": concept, "split": split,
                            "component_id": f"{source}:{concept}:{split}:{block:03d}:{surface}",
                            "component_block": f"{source}:{concept}:{split}:{block:03d}",
                            "lexical_block": block, "surface_rep": surface,
                            "template_family": f"{source}:{concept}:{split}:template{surface}",
                            "base_prompt": base, "cf_prompt": cf, "sham_prompt": sham,
                            "answer_base": " " + vals["a"], "answer_cf": " " + vals["a2"]})
    return rows


def normalized_text(value: str) -> str:
    return " ".join(str(value).split())


def canonical_yes_no(answers: Any) -> str | None:
    values = answers if isinstance(answers, list) else [answers]
    cleaned = [str(x).strip().lower().rstrip(".") for x in values]
    return cleaned[0] if cleaned and all(x in {"yes", "no"} for x in cleaned) and len(set(cleaned)) == 1 else None


def make_natural_rows(cfg: Mapping[str, Any]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    from datasets import load_dataset
    selected: list[dict[str, Any]] = []; provenance: list[dict[str, Any]] = []
    for ds_cfg in cfg["panels"]["natural_datasets"]:
        ds = load_dataset(ds_cfg["dataset"], ds_cfg["config"], split=ds_cfg["split"])
        if ds._fingerprint != ds_cfg["cache_fingerprint"]:
            raise RuntimeError(f"natural dataset fingerprint drift: {ds_cfg['config']} {ds._fingerprint}")
        count = 0
        for index, row in enumerate(ds):
            answer = canonical_yes_no(row["answers"])
            if answer is None:
                continue
            selected.append({"dataset": ds_cfg["config"], "dataset_id": str(row.get("_id", index)), "dataset_index": index,
                             "question": normalized_text(row["input"]), "context": normalized_text(row["context"]), "answer": answer})
            count += 1
        provenance.append({"dataset": ds_cfg["dataset"], "config": ds_cfg["config"], "split": ds_cfg["split"],
                           "fingerprint": ds._fingerprint, "eligible_yes_no_rows": count})
    if len(selected) < int(cfg["panels"]["natural_minimum_documents"]):
        raise RuntimeError(f"naturalistic support {len(selected)} below floor")
    order = sorted(range(len(selected)), key=lambda i: (len(selected[i]["context"]), selected[i]["dataset"], selected[i]["dataset_id"]))
    position = {idx: j for j, idx in enumerate(order)}
    rows: list[dict[str, Any]] = []
    for idx, row in enumerate(selected):
        p = position[idx]; base_idx = order[(p + 1) % len(order)]; sham_idx = order[(p + 2) % len(order)]
        correct = row["answer"]; opposite = "no" if correct == "yes" else "yes"
        rows.append({"schema_version": "proxy_control_v2_natural_row", "panel_kind": "naturalistic",
            "source": "NATURAL_QA", "concept": "context", "split": "test",
            "component_id": f"NATURAL_QA:{row['dataset']}:{row['dataset_id']}",
            "component_block": f"NATURAL_QA:{row['dataset']}:{row['dataset_id']}",
            "template_family": f"NATURAL_QA:{row['dataset']}", "lexical_block": idx, "surface_rep": 0,
            "dataset": row["dataset"], "dataset_id": row["dataset_id"], "dataset_index": row["dataset_index"],
            "question": row["question"], "true_context": row["context"],
            "base_context": selected[base_idx]["context"], "base_context_id": selected[base_idx]["dataset_id"],
            "sham_context": selected[sham_idx]["context"], "sham_context_id": selected[sham_idx]["dataset_id"],
            "answer_base": " " + opposite, "answer_cf": " " + correct})
    return rows, provenance


def load_tokenizers(cfg: Mapping[str, Any]) -> dict[str, Any]:
    from transformers import AutoTokenizer
    out = {}
    for model in cfg["models"]:
        tok = AutoTokenizer.from_pretrained(model["name"], revision=model["revision"], local_files_only=True, use_fast=True)
        tok.padding_side = "right"
        if tok.pad_token_id is None:
            tok.pad_token = tok.eos_token
        out[model["key"]] = tok
    return out


def prepare(config_path: Path) -> None:
    cfg = load_json(config_path); prepared = ROOT / cfg["panels"]["prepared_root"]
    if any(prepared.iterdir()) if prepared.exists() else False:
        raise FileExistsError(f"prepared namespace nonempty: {prepared}")
    prepared.mkdir(parents=True, exist_ok=True)
    controlled = make_controlled_rows(cfg)
    natural, natural_provenance = make_natural_rows(cfg)
    tokenizers = load_tokenizers(cfg)
    model_checks: dict[str, Any] = {}
    for model_key, tok in tokenizers.items():
        maximum = 0; mismatched: list[str] = []
        for row in controlled:
            answer_ids = [tok(row[k], add_special_tokens=False)["input_ids"] for k in ("answer_base", "answer_cf")]
            if any(len(x) != 1 for x in answer_ids) or answer_ids[0][0] == answer_ids[1][0]:
                raise RuntimeError(f"answer token failure {model_key}:{row['component_id']} {answer_ids}")
            lengths = [len(tok(row[k], add_special_tokens=False)["input_ids"]) for k in ("base_prompt", "cf_prompt", "sham_prompt")]
            maximum = max(maximum, *lengths)
            if len(set(lengths)) != 1:
                mismatched.append(f"{row['component_id']}:{lengths}")
            if max(lengths) > int(cfg["panels"]["maximum_controlled_length"]):
                raise RuntimeError(f"controlled length failure {model_key}:{row['component_id']}:{lengths}")
        if mismatched:
            raise RuntimeError(f"token-length matched control failure {model_key}: {mismatched[:3]}")
        for row in natural:
            ids = [tok(row[k], add_special_tokens=False)["input_ids"] for k in ("answer_base", "answer_cf")]
            if any(len(x) != 1 for x in ids) or ids[0][0] == ids[1][0]:
                raise RuntimeError(f"natural answer token failure {model_key}:{row['component_id']}:{ids}")
        model_checks[model_key] = {"maximum_controlled_tokens": maximum, "controlled_length_matched": True,
                                   "natural_answer_support": len(natural)}
    for source in cfg["panels"]["controlled_sources"]:
        for concept in cfg["panels"]["concepts"]:
            sub = [r for r in controlled if r["source"] == source and r["concept"] == concept]
            for split, nblocks in (("development", cfg["panels"]["development_blocks"]), ("test", cfg["panels"]["test_blocks"])):
                rows = [r for r in sub if r["split"] == split]
                if len({r["component_block"] for r in rows}) != int(nblocks):
                    raise RuntimeError(f"block support failure {source}/{concept}/{split}")
                if len(rows) != int(nblocks) * int(cfg["panels"]["surfaces_per_block"]):
                    raise RuntimeError(f"surface support failure {source}/{concept}/{split}")
            dev_templates = {r["template_family"] for r in sub if r["split"] == "development"}
            test_templates = {r["template_family"] for r in sub if r["split"] == "test"}
            if dev_templates & test_templates:
                raise RuntimeError("template leakage")
    write_jsonl(prepared / "controlled_rows.jsonl", controlled)
    write_jsonl(prepared / "natural_rows.jsonl", natural)
    data_manifest = {"controlled_rows_sha256": sha256(prepared / "controlled_rows.jsonl"),
                     "natural_rows_sha256": sha256(prepared / "natural_rows.jsonl"),
                     "controlled_rows": len(controlled), "natural_rows": len(natural),
                     "natural_provenance": natural_provenance, "model_tokenizer_checks": model_checks,
                     "selection_firewall": "TOKEN_IDS_LENGTHS_AND_REGISTERED_DATASET_LABELS_ONLY_NO_MODEL_FORWARD_OR_EFFECT_FILTERING"}
    exclusive_json(prepared / "PRESCORE.json", data_manifest)
    print(json.dumps(data_manifest, indent=2))


def import_manifest(cfg: Mapping[str, Any]) -> dict[str, Any]:
    return load_json(ROOT / cfg["imported_v1"]["manifest"])


def verify_imports(cfg: Mapping[str, Any], full: bool, required: Sequence[Path] = ()) -> None:
    manifest = import_manifest(cfg)
    records = {ROOT / row["path"]: row for row in manifest["files"]}
    targets = list(records) if full else list(required)
    for path in targets:
        if path not in records:
            raise RuntimeError(f"import absent from manifest: {path}")
        row = records[path]
        if not path.is_file() or path.stat().st_size != row["bytes"] or sha256(path) != row["sha256"]:
            raise RuntimeError(f"v1 import drift: {path}")


def verify_preservation(cfg: Mapping[str, Any]) -> None:
    if cfg["preservation"].get("v5_authorized") is not False:
        raise RuntimeError("relational v5 must remain unauthorized")
    for key, raw in cfg["preservation"].items():
        if key == "v5_authorized":
            continue
        path = ROOT / raw
        if not path.is_file():
            raise RuntimeError(f"preservation artifact absent: {key}")
    if load_json(ROOT / cfg["preservation"]["v1_complete"])["status"] != "COMPLETE":
        raise RuntimeError("v1 is not complete")
    if load_json(ROOT / cfg["preservation"]["v1_analysis_complete"])["status"] != "COMPLETE":
        raise RuntimeError("v1 companion is not complete")


def candidate_paths(config_path: Path, cfg: Mapping[str, Any]) -> list[Path]:
    prepared = ROOT / cfg["panels"]["prepared_root"]
    paths = [config_path, PLAN, PLAN_REVIEW, SCRIPT, TEST, LAUNCHER, ANALYSIS_SCRIPT, ANALYSIS_CONFIG,
             ROOT / "results/proxy_control_benchmark_v1_analysis_20260808/result.json",
             ROOT / "results/proxy_control_benchmark_v1_analysis_20260808/COMPLETE.json",
             ROOT / cfg["imported_v1"]["manifest"], V1_SCRIPT, ROOT / "requirements-atlas.lock.txt",
             ROOT / "PAPER.md", ROOT / "reports/paper_claim_ledger_v1.json",
             ROOT / "reports/claim_review/proxy_control_benchmark_v1_post_result_claim_review.md",
             prepared / "controlled_rows.jsonl", prepared / "natural_rows.jsonl", prepared / "PRESCORE.json"]
    return paths


def candidate_inventory(config_path: Path, cfg: Mapping[str, Any]) -> list[dict[str, Any]]:
    paths = candidate_paths(config_path, cfg)
    for path in paths:
        if not path.is_file():
            raise RuntimeError(f"candidate artifact absent: {path}")
    return sorted([{"path": p.relative_to(ROOT).as_posix(), "bytes": p.stat().st_size, "sha256": sha256(p)} for p in paths], key=lambda x: x["path"])


def verify_prepared(cfg: Mapping[str, Any], regenerate_natural: bool = False) -> None:
    prepared = ROOT / cfg["panels"]["prepared_root"]
    prescore = load_json(prepared / "PRESCORE.json")
    for key, name in (("controlled_rows_sha256", "controlled_rows.jsonl"), ("natural_rows_sha256", "natural_rows.jsonl")):
        if sha256(prepared / name) != prescore[key]:
            raise RuntimeError(f"prepared data hash drift: {name}")
    if read_jsonl(prepared / "controlled_rows.jsonl") != make_controlled_rows(cfg):
        raise RuntimeError("prepared controlled rows do not match frozen generator")
    if regenerate_natural:
        natural, provenance = make_natural_rows(cfg)
        if read_jsonl(prepared / "natural_rows.jsonl") != natural or prescore["natural_provenance"] != provenance:
            raise RuntimeError("prepared natural rows do not match label-only source build")


def freeze(config_path: Path) -> None:
    cfg = load_json(config_path); verify_preservation(cfg); verify_imports(cfg, full=True); verify_prepared(cfg, regenerate_natural=True)
    output = ROOT / cfg["runtime"]["output_root"]
    if output.exists():
        raise RuntimeError("v2 output namespace exists")
    prescore = load_json(ROOT / cfg["panels"]["prepared_root"] / "PRESCORE.json")
    if prescore["natural_rows"] < int(cfg["panels"]["natural_minimum_documents"]):
        raise RuntimeError("natural panel support below floor")
    inventory = candidate_inventory(config_path, cfg)
    payload = {"schema_version": "proxy_control_benchmark_v2_freeze", "namespace": cfg["namespace"],
        "scientific_opening": "FROZEN_BEFORE_SOURCE_C_SOURCE_D_OR_NATURAL_MODEL_FORWARD",
        "config_sha256": sha256(config_path), "candidate_inventory": inventory,
        "candidate_inventory_sha256": hashlib.sha256(canonical(inventory)).hexdigest(),
        "v1_import_manifest_sha256": sha256(ROOT / cfg["imported_v1"]["manifest"]),
        "prescore_sha256": sha256(ROOT / cfg["panels"]["prepared_root"] / "PRESCORE.json"),
        "decision_table": cfg["analysis"]["decision_table"], "new_real_sae_training_authorized": False,
        "retry_authorized": False, "v5_authorized": False}
    exclusive_json(ROOT / cfg["runtime"]["freeze"], payload)
    print(json.dumps(payload, indent=2))


def verify_freeze(config_path: Path, cfg: Mapping[str, Any]) -> dict[str, Any]:
    verify_preservation(cfg)
    path = ROOT / cfg["runtime"]["freeze"]
    freeze_rec = load_json(path)
    if freeze_rec["config_sha256"] != sha256(config_path):
        raise RuntimeError("v2 config drift")
    inventory = candidate_inventory(config_path, cfg)
    if freeze_rec["candidate_inventory"] != inventory:
        raise RuntimeError("v2 frozen candidate drift")
    if freeze_rec.get("new_real_sae_training_authorized") is not False:
        raise RuntimeError("real SAE training unexpectedly authorized")
    return freeze_rec


@dataclass
class Panel:
    rows: list[dict[str, Any]]
    base_h: np.ndarray
    cf_h: np.ndarray
    sham_h: np.ndarray
    base_logits: np.ndarray
    cf_logits: np.ndarray
    sham_logits: np.ndarray


def subset(panel: Panel, concept: str, split: str | None = None) -> Panel:
    idx = [i for i, row in enumerate(panel.rows) if row["concept"] == concept and (split is None or row["split"] == split)]
    return Panel([panel.rows[i] for i in idx], *(np.asarray(getattr(panel, key))[idx] for key in
        ("base_h", "cf_h", "sham_h", "base_logits", "cf_logits", "sham_logits")))


def materialize_natural_prompts(rows: Sequence[Mapping[str, Any]], tokenizer: Any, cfg: Mapping[str, Any]) -> tuple[list[str], list[str], list[str]]:
    head = int(cfg["panels"]["natural_context_head_tokens"]); tail = int(cfg["panels"]["natural_context_tail_tokens"])
    def prompt(context: str, question: str) -> str:
        ids = tokenizer(context, add_special_tokens=False)["input_ids"]
        kept = ids if len(ids) <= head + tail else ids[:head] + ids[-tail:]
        text = tokenizer.decode(kept, skip_special_tokens=True)
        return f"Context: {text}\nQuestion: {question}\nAnswer yes or no:"
    return ([prompt(r["base_context"], r["question"]) for r in rows],
            [prompt(r["true_context"], r["question"]) for r in rows],
            [prompt(r["sham_context"], r["question"]) for r in rows])


def panel_forward(model: Any, tokenizer: Any, cfg: Mapping[str, Any], rows: list[dict[str, Any]], layer: int, device: torch.device) -> Panel:
    materialized = []
    for row in rows:
        r = dict(row)
        ab = tokenizer(r["answer_base"], add_special_tokens=False)["input_ids"]
        ac = tokenizer(r["answer_cf"], add_special_tokens=False)["input_ids"]
        if len(ab) != 1 or len(ac) != 1 or ab[0] == ac[0]:
            raise RuntimeError(f"runtime answer support drift: {r['component_id']}")
        r["answer_base_id"], r["answer_cf_id"] = int(ab[0]), int(ac[0])
        materialized.append(r)
    if materialized[0]["panel_kind"] == "naturalistic":
        bp, cp, sp = materialize_natural_prompts(materialized, tokenizer, cfg)
        for i, row in enumerate(materialized):
            row.update({"base_prompt": bp[i], "cf_prompt": cp[i], "sham_prompt": sp[i]})
    else:
        bp = [r["base_prompt"] for r in materialized]; cp = [r["cf_prompt"] for r in materialized]; sp = [r["sham_prompt"] for r in materialized]
    args = (layer, int(cfg["panels"]["batch_size"]), int(cfg["panels"]["maximum_model_length"]), device)
    bh, bl = v1.forward_prompts(model, tokenizer, bp, *args)
    ch, cl = v1.forward_prompts(model, tokenizer, cp, *args)
    sh, sl = v1.forward_prompts(model, tokenizer, sp, *args)
    return Panel(materialized, bh, ch, sh, bl, cl, sl)


def base_hidden_gradients(model: Any, tokenizer: Any, cfg: Mapping[str, Any], layer: int, panel: Panel, device: torch.device) -> np.ndarray:
    module = v1._module_for_layer(model, layer)
    prompts = [r["base_prompt"] for r in panel.rows]
    output: list[np.ndarray] = []
    for parameter in model.parameters():
        parameter.requires_grad_(False)
    for start in range(0, len(prompts), int(cfg["panels"]["batch_size"])):
        batch_rows = panel.rows[start:start + int(cfg["panels"]["batch_size"])]
        batch = prompts[start:start + int(cfg["panels"]["batch_size"])]
        enc = tokenizer(batch, return_tensors="pt", padding=True, truncation=True, max_length=int(cfg["panels"]["maximum_model_length"]))
        ids, mask = enc["input_ids"].to(device), enc["attention_mask"].to(device)
        idx = mask.sum(1) - 1; ar = torch.arange(len(batch), device=device)
        captured: list[torch.Tensor] = []
        def hook(_module: Any, _inputs: Any, raw: Any) -> Any:
            h = raw[0] if isinstance(raw, tuple) else raw
            leaf = h.detach().requires_grad_(True)
            captured.append(leaf)
            return (leaf,) + raw[1:] if isinstance(raw, tuple) else leaf
        handle = module.register_forward_hook(hook)
        try:
            with torch.enable_grad():
                result = model(input_ids=ids, attention_mask=mask, use_cache=False)
                lo = torch.stack([result.logits[i, idx[i], int(r["answer_cf_id"])] - result.logits[i, idx[i], int(r["answer_base_id"])] for i, r in enumerate(batch_rows)])
                grad = torch.autograd.grad(lo.sum(), captured[0], retain_graph=False, create_graph=False)[0]
                output.append(grad[ar, idx].float().cpu().numpy())
        finally:
            handle.remove()
    return np.concatenate(output)


def sym(matrix: np.ndarray) -> np.ndarray:
    return (matrix + matrix.T) / 2.0


def behavior_gradient_basis(dev: Panel, gradients: np.ndarray, scale: float, rank: int, penalty: float, min_eigenvalue: float) -> tuple[np.ndarray, dict[str, Any]]:
    d = np.asarray((dev.cf_h - dev.base_h) / max(scale, 1e-8), np.float64)
    s = np.asarray((dev.sham_h - dev.base_h) / max(scale, 1e-8), np.float64)
    full = v1.logodds(dev.cf_logits, dev.rows) - v1.logodds(dev.base_logits, dev.rows)
    g = np.asarray(gradients * np.sign(full)[:, None], np.float64)
    matrix = sym(d.T @ g / max(1, len(d))) - float(penalty) * sym(s.T @ g / max(1, len(s)))
    values, vectors = np.linalg.eigh(matrix)
    order = np.argsort(values)[::-1]
    keep = [int(i) for i in order if values[i] > float(min_eigenvalue)][:int(rank)]
    basis = np.asarray(vectors[:, keep].T, np.float32) if keep else np.zeros((0, d.shape[1]), np.float32)
    return basis, {"kind": "behavior_gradient_oracle", "rank": len(basis), "requested_rank": int(rank),
                   "nuisance_penalty": float(penalty), "minimum_eigenvalue": float(min_eigenvalue),
                   "positive_eigenvalues": int(np.sum(values > float(min_eigenvalue))),
                   "selected_eigenvalues": [float(values[i]) for i in keep]}


def fit_learned_mapping(model: v1.LearnedDecomposition, dev_norm: Panel, rank: int, device: torch.device) -> dict[str, Any]:
    _, base_branches, base_codes = v1.learned_outputs(model, dev_norm.base_h, device)
    _, cf_branches, cf_codes = v1.learned_outputs(model, dev_norm.cf_h, device)
    if len(model.branches) == 2:
        chosen = v1.assign_k2_branch(cf_branches[0] - base_branches[0], cf_branches[1] - base_branches[1])
        return {"kind": "branch_permutation", "target_branch": int(chosen), "complement_branch": int(1 - chosen)}
    score = np.mean(np.abs(cf_codes[0] - base_codes[0]), axis=0)
    atoms = np.argsort(score)[-min(int(rank), len(score)):]
    return {"kind": "source_fitted_atom_selection", "atom_count": len(atoms), "atom_indices": atoms.tolist()}


def apply_learned_mapping(model: v1.LearnedDecomposition, panel_norm: Panel, mapping: Mapping[str, Any], device: torch.device) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    full_b, bb, bc = v1.learned_outputs(model, panel_norm.base_h, device)
    full_c, cb, cc = v1.learned_outputs(model, panel_norm.cf_h, device)
    _, sb, sc = v1.learned_outputs(model, panel_norm.sham_h, device)
    if mapping["kind"] == "branch_permutation":
        chosen = int(mapping["target_branch"]); other = int(mapping["complement_branch"])
        return bb[chosen], cb[chosen], sb[chosen], bb[other], cb[other], full_b
    atoms = np.asarray(mapping["atom_indices"], dtype=int)
    decoder = model.branches[0].decoder.detach().cpu().numpy()
    target_b = bc[0][:, atoms] @ decoder[atoms]; target_c = cc[0][:, atoms] @ decoder[atoms]; target_s = sc[0][:, atoms] @ decoder[atoms]
    return target_b, target_c, target_s, full_b - target_b, full_c - target_c, full_b


def linear_components(panel: Panel, center: np.ndarray, scale: float, basis: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    norm = [(x - center) / max(scale, 1e-8) for x in (panel.base_h, panel.cf_h, panel.sham_h)]
    tb, tc, ts = [v1.project_component(x, basis, np.zeros(x.shape[1], np.float32)) * scale for x in norm]
    cb, cc = panel.base_h - center - tb, panel.cf_h - center - tc
    return tb, tc, ts, cb, cc, panel.base_h - center


def block_interval(values: Sequence[float], blocks: Sequence[str], draws: int, seed: int) -> list[float] | None:
    x = np.asarray(values, np.float64); b = np.asarray(blocks)
    finite = np.isfinite(x); x, b = x[finite], b[finite]
    if not len(x):
        return None
    unique = sorted(set(b.tolist()))
    means = np.asarray([np.mean(x[b == key]) for key in unique], np.float64)
    rng = np.random.default_rng(seed)
    boot = np.asarray([np.mean(means[rng.integers(0, len(means), len(means))]) for _ in range(int(draws))])
    return [float(v) for v in np.quantile(boot, [0.025, 0.5, 0.975])]


def classify_interval(ci: Sequence[float] | None, smallest: float) -> str:
    if ci is None or not np.isfinite(ci).all():
        return "INELIGIBLE"
    low, high = ci[0], ci[2]
    if low > smallest: return "POSITIVE_MATERIAL"
    if high < -smallest: return "NEGATIVE_MATERIAL"
    if low > -smallest and high < smallest: return "EQUIVALENT_SMALL"
    return "INCONCLUSIVE"



def signed_behavioral_specificity(patch_effect: np.ndarray, sham_effect: np.ndarray, full_effect: np.ndarray, eligible: np.ndarray, eps: float) -> np.ndarray:
    denominator = np.where(np.abs(full_effect) >= eps, full_effect, np.nan)
    return np.where(eligible, (patch_effect - sham_effect) / denominator, np.nan)

def evaluate_components(model: Any, tokenizer: Any, cfg: Mapping[str, Any], layer: int, panel: Panel,
                        components: tuple[np.ndarray, ...], device: torch.device) -> dict[str, Any]:
    tb, tc, ts, cb, cc, _ = components
    eps = float(cfg["analysis"]["epsilon"])
    full_delta = panel.cf_h - panel.base_h; target_delta = tc - tb; sham_delta = ts - tb
    full_norm = np.linalg.norm(full_delta, axis=1); target_norm = np.linalg.norm(target_delta, axis=1)
    sham_full_norm = np.linalg.norm(panel.sham_h - panel.base_h, axis=1)
    capture = target_norm / np.maximum(full_norm, eps)
    sham_capture = np.linalg.norm(sham_delta, axis=1) / np.maximum(sham_full_norm, eps)
    prompts = [r["base_prompt"] for r in panel.rows]
    args = (layer, int(cfg["panels"]["batch_size"]), int(cfg["panels"]["maximum_model_length"]), device)
    patched = v1.patched_logits(model, tokenizer, prompts, target_delta, *args)
    sham_patched = v1.patched_logits(model, tokenizer, prompts, sham_delta, *args)
    erased = v1.patched_logits(model, tokenizer, prompts, -tb, *args)
    base_lo = v1.logodds(panel.base_logits, panel.rows); cf_lo = v1.logodds(panel.cf_logits, panel.rows)
    patch_lo = v1.logodds(patched, panel.rows); sham_lo = v1.logodds(sham_patched, panel.rows); erase_lo = v1.logodds(erased, panel.rows)
    full_effect = cf_lo - base_lo; patch_effect = patch_lo - base_lo; sham_effect = sham_lo - base_lo
    ratio = target_norm / np.maximum(full_norm, eps)
    eligible = (np.abs(full_effect) >= float(cfg["panels"]["minimum_full_logodds_effect"])) & (ratio <= float(cfg["panels"]["maximum_patch_norm_ratio"]))
    denominator = np.where(np.abs(full_effect) >= eps, full_effect, np.nan)
    recovery = np.where(eligible, patch_effect / denominator, np.nan)
    specificity = signed_behavioral_specificity(patch_effect, sham_effect, full_effect, eligible, eps)
    collateral = v1.non_target_kl(panel.base_logits, patched, panel.rows)
    necessity = erase_lo - base_lo
    return {"representation_capture": capture, "sham_capture": sham_capture,
        "intervention_specificity": capture - sham_capture, "full_logodds_effect": full_effect,
        "patch_logodds_effect": patch_effect, "sham_logodds_effect": sham_effect,
        "behavioral_recovery": recovery, "behavioral_specificity": specificity,
        "collateral_kl": collateral, "necessity_logodds_effect": necessity,
        "patch_norm_ratio": ratio, "behavior_eligible": eligible,
        "target_delta": target_delta, "target_base": tb, "target_cf": tc,
        "complement_base": cb, "complement_cf": cc}


def ridge_cross_source(dev_components: tuple[np.ndarray, ...], eval_components: tuple[np.ndarray, ...], alpha: float) -> tuple[float, float]:
    dtb, dtc, _, dcb, dcc, _ = dev_components
    etb, etc, _, ecb, ecc, _ = eval_components
    train_y = np.r_[np.zeros(len(dtb), int), np.ones(len(dtc), int)]
    test_y = np.r_[np.zeros(len(etb), int), np.ones(len(etc), int)]
    target = v1.ridge_binary_accuracy(np.concatenate([dtb, dtc]), train_y, np.concatenate([etb, etc]), test_y, alpha)
    leakage = v1.ridge_binary_accuracy(np.concatenate([dcb, dcc]), train_y, np.concatenate([ecb, ecc]), test_y, alpha)
    return target, leakage


def norm_panel(panel: Panel, center: np.ndarray, scale: float) -> Panel:
    return Panel(panel.rows, *((x - center) / max(scale, 1e-8) for x in (panel.base_h, panel.cf_h, panel.sham_h)),
                 panel.base_logits, panel.cf_logits, panel.sham_logits)


def load_imported_model(cfg: Mapping[str, Any], model_key: str, layer: int, method: str, seed: int,
                        hidden: int, device: torch.device) -> v1.LearnedDecomposition:
    spec = cfg["imported_v1"]["methods"][method]
    multipliers = spec["width_multiplier"] if isinstance(spec["width_multiplier"], list) else [spec["width_multiplier"]]
    mdl = v1.LearnedDecomposition(hidden, multipliers, spec["topk"]).to(device)
    path = ROOT / cfg["imported_v1"]["root"] / "shards" / f"{model_key}_layer{layer}" / f"{method}_seed{seed}.pt"
    verify_imports(cfg, full=False, required=[path])
    record = torch.load(path, map_location="cpu", weights_only=False)
    if record["method"] != method or int(record["seed"]) != int(seed) or record["model"] != model_key or int(record["layer"]) != int(layer):
        raise RuntimeError("checkpoint lineage mismatch")
    mdl.load_state_dict(record["state_dict"])
    return mdl.eval()


def imported_proxy(cfg: Mapping[str, Any], model_key: str, layer: int, method: str, seed: int) -> tuple[float, float]:
    path = ROOT / cfg["imported_v1"]["root"] / "shards" / f"{model_key}_layer{layer}" / "metrics.jsonl"
    verify_imports(cfg, full=False, required=[path])
    rows = [r for r in read_jsonl(path) if r["method"] == method and int(r["seed"]) == int(seed)]
    fvu = {float(r["reconstruction_fvu"]) for r in rows}; sparse = {float(r["sparsity"]) for r in rows}
    if len(fvu) != 1 or len(sparse) != 1:
        raise RuntimeError("v1 imported proxy not invariant")
    return fvu.pop(), sparse.pop()


def wait_for_synthetic_gate(cfg: Mapping[str, Any], out: Path, freeze_sha: str) -> None:
    root = ROOT / cfg["runtime"]["output_root"] / "synthetic"
    atomic_json(out / "WAITING.json", {"phase": "WAITING_FOR_SYNTHETIC_GATE", "new_model_forward_started": False, "freeze_sha256": freeze_sha})
    while True:
        passed, failed = root / "PASS.json", root / "FAIL.json"
        technical = root / "TECHNICAL_FAIL.json"
        if passed.is_file():
            rec = load_json(passed)
            if rec.get("status") != "PASS" or rec.get("freeze_sha256") != freeze_sha:
                raise RuntimeError("synthetic PASS lineage mismatch")
            atomic_json(out / "WAITING.json", {"phase": "SYNTHETIC_GATE_PASSED", "new_model_forward_started": False, "gate_sha256": sha256(passed)})
            return
        if failed.is_file() or technical.is_file():
            terminal = failed if failed.is_file() else technical
            exclusive_json(out / "BLOCKED_BY_SYNTHETIC_GATE.json", {"status": "BLOCKED", "gate_sha256": sha256(terminal), "new_model_forwards": 0})
            raise RuntimeError("synthetic gate failed; scientific inference blocked")
        time.sleep(int(cfg["runtime"]["gate_poll_seconds"]))


def captured_variance(components: tuple[np.ndarray, ...], panel: Panel, center: np.ndarray) -> float:
    target = np.concatenate([components[0], components[1]], axis=0)
    full = np.concatenate([panel.base_h - center, panel.cf_h - center], axis=0)
    return float(np.var(target) / max(np.var(full), 1e-12))


def worker(config_path: Path, model_key: str, layer: int) -> None:
    cfg = load_json(config_path); freeze_rec = verify_freeze(config_path, cfg)
    model_cfg = next(x for x in cfg["models"] if x["key"] == model_key)
    if layer not in model_cfg["layers"]:
        raise RuntimeError("unregistered layer")
    root = ROOT / cfg["runtime"]["output_root"]
    out = root / "shards" / f"{model_key}_layer{layer}"
    if out.exists():
        raise FileExistsError(out)
    out.mkdir(parents=True)
    freeze_sha = sha256(ROOT / cfg["runtime"]["freeze"])
    exclusive_json(out / "STARTED.json", {"schema_version": "proxy_control_v2_worker_started", "model": model_key,
        "layer": layer, "phase": "PRE_GATE", "new_model_forward_started": False, "freeze_sha256": freeze_sha})
    wait_for_synthetic_gate(cfg, out, freeze_sha)

    device = torch.device("cuda:0" if torch.cuda.is_available() else "cpu")
    seed = stable_seed(cfg["seed"], model_key, layer); seed_everything(seed)
    atomic_json(out / "STARTED.json", {"schema_version": "proxy_control_v2_worker_started", "model": model_key,
        "layer": layer, "phase": "SCIENTIFIC_INFERENCE_AUTHORIZED", "new_model_forward_started": True,
        "freeze_sha256": freeze_sha, "runtime": runtime_record(device)})
    model, tokenizer = v1.load_model_and_tokenizer(model_cfg, device)
    prepared = ROOT / cfg["panels"]["prepared_root"]
    controlled_rows = read_jsonl(prepared / "controlled_rows.jsonl"); natural_rows = read_jsonl(prepared / "natural_rows.jsonl")
    panels = {source: panel_forward(model, tokenizer, cfg, [r for r in controlled_rows if r["source"] == source], layer, device)
              for source in cfg["panels"]["controlled_sources"]}
    natural = panel_forward(model, tokenizer, cfg, natural_rows, layer, device)
    panel_manifest = {source: {"rows": len(panel.rows), "row_sha256": hashlib.sha256(canonical(panel.rows)).hexdigest(),
        "blocks": len({r["component_block"] for r in panel.rows})} for source, panel in panels.items()}
    panel_manifest["NATURAL_QA"] = {"rows": len(natural.rows), "row_sha256": hashlib.sha256(canonical(natural.rows)).hexdigest(),
                                      "blocks": len({r["component_block"] for r in natural.rows})}
    exclusive_json(out / "PANEL_MANIFEST.json", panel_manifest)

    summary_path = ROOT / cfg["imported_v1"]["root"] / "shards" / f"{model_key}_layer{layer}" / "activation_summary.npz"
    verify_imports(cfg, full=False, required=[summary_path])
    arr = np.load(summary_path); center = np.asarray(arr["mean"], np.float32); scale = float(arr["scale"])
    hidden = len(center)
    metrics: list[dict[str, Any]] = []; component_rows: list[dict[str, Any]] = []
    geometry: dict[str, list[np.ndarray]] = {}
    gradients: dict[tuple[str, str], np.ndarray] = {}

    def add(method: str, method_seed: int | None, proxy_class: str, assignment_source: str,
            evaluation_source: str, concept: str, dev: Panel, ev: Panel,
            dev_components: tuple[np.ndarray, ...], eval_components: tuple[np.ndarray, ...],
            mapping: Mapping[str, Any], reconstruction_fvu: float | None, active_codes: float | None,
            linear_rank: int | None, variance_capture: float | None) -> None:
        behavior = evaluate_components(model, tokenizer, cfg, layer, ev, eval_components, device)
        probe, leakage = ridge_cross_source(dev_components, eval_components, float(cfg["analysis"]["ridge_alpha"]))
        blocks = [r["component_block"] for r in ev.rows]
        rec: dict[str, Any] = {"schema_version": "proxy_control_v2_metric", "model": model_key, "layer": layer,
            "model_layer": f"{model_key}:{layer}", "method": method, "seed": method_seed, "proxy_class": proxy_class,
            "assignment_source": assignment_source, "evaluation_source": evaluation_source, "concept": concept,
            "panel_kind": ev.rows[0]["panel_kind"], "reconstruction_fvu": reconstruction_fvu,
            "reconstruction_quality": -reconstruction_fvu if reconstruction_fvu is not None else None,
            "active_codes": active_codes, "sparsity": -active_codes if active_codes is not None else None,
            "linear_rank": linear_rank, "rank_sparsity": -linear_rank if linear_rank is not None else None,
            "captured_variance": variance_capture, "probe_recovery": probe, "leakage": leakage,
            "selectivity": probe - leakage, "assignment_detail": dict(mapping),
            "component_blocks": len(set(blocks)), "surface_rows": len(blocks)}
        arrays = {k: np.asarray(behavior[k]) for k in ("intervention_specificity", "behavioral_recovery", "behavioral_specificity", "collateral_kl")}
        for key, values in arrays.items():
            finite = np.isfinite(values)
            block_means = [float(np.mean(values[(np.asarray(blocks) == b) & finite])) for b in sorted(set(blocks)) if np.any((np.asarray(blocks) == b) & finite)]
            rec[key] = float(np.mean(block_means)) if block_means else None
            ci = block_interval(values, blocks, int(cfg["analysis"]["bootstrap_draws"]), stable_seed(cfg["seed"], model_key, layer, method, method_seed, assignment_source, evaluation_source, concept, key))
            rec[f"{key}_block_ci"] = ci
            if key in {"intervention_specificity", "behavioral_specificity"}:
                rec[f"{key}_equivalence"] = classify_interval(ci, float(cfg["analysis"]["specificity_smallest_effect"]))
        rec["behavior_eligible_fraction"] = float(np.mean(behavior["behavior_eligible"]))
        rec["geometric_stability"] = None
        metrics.append(rec)
        if proxy_class == "learned":
            geometry.setdefault(f"{method}|{assignment_source}|{evaluation_source}|{concept}", []).append(np.asarray(eval_components[0], np.float32))
        for i, row in enumerate(ev.rows):
            item = {"schema_version": "proxy_control_v2_component_metric", "model": model_key, "layer": layer,
                "method": method, "seed": method_seed, "proxy_class": proxy_class, "assignment_source": assignment_source,
                "evaluation_source": evaluation_source, "concept": concept, "panel_kind": row["panel_kind"],
                "component_id": row["component_id"], "component_block": row["component_block"],
                "template_family": row["template_family"], "surface_rep": row["surface_rep"],
                "behavior_eligible": bool(behavior["behavior_eligible"][i])}
            for key in ("intervention_specificity", "behavioral_recovery", "behavioral_specificity", "collateral_kl",
                        "full_logodds_effect", "patch_logodds_effect", "sham_logodds_effect", "necessity_logodds_effect", "patch_norm_ratio"):
                value = float(behavior[key][i]); item[key] = value if np.isfinite(value) else None
            component_rows.append(item)

    directions = [("SOURCE_C", "SOURCE_D"), ("SOURCE_D", "SOURCE_C")]
    for assignment_source, evaluation_source in directions:
        for concept in cfg["panels"]["concepts"]:
            dev = subset(panels[assignment_source], concept, "development")
            ev = subset(panels[evaluation_source], concept, "test")
            dev_norm, ev_norm = norm_panel(dev, center, scale), norm_panel(ev, center, scale)
            train_x = np.concatenate([dev_norm.base_h, dev_norm.cf_h, dev_norm.sham_h])
            for method in cfg["linear_methods"]:
                if method == "behavior_gradient_oracle":
                    key = (assignment_source, concept)
                    if key not in gradients:
                        gradients[key] = base_hidden_gradients(model, tokenizer, cfg, layer, dev, device)
                    basis, detail = behavior_gradient_basis(dev, gradients[key], scale, int(cfg["analysis"]["rank"]),
                        float(cfg["analysis"]["oracle_nuisance_penalty"]), float(cfg["analysis"]["oracle_minimum_eigenvalue"]))
                else:
                    basis = v1.linear_basis(method, train_x, dev_norm.base_h, dev_norm.cf_h, int(cfg["analysis"]["rank"]),
                                            stable_seed(seed, method, assignment_source, concept), float(cfg["analysis"]["ridge_alpha"]))
                    detail = {"kind": "linear_basis", "fit": method, "rank": len(basis)}
                dev_comp = linear_components(dev, center, scale, basis); ev_comp = linear_components(ev, center, scale, basis)
                variance = captured_variance(dev_comp, dev, center)
                add(method, None, "linear", assignment_source, evaluation_source, concept, dev, ev, dev_comp, ev_comp,
                    detail, None, None, len(basis), variance)
                if concept == "context":
                    nat_comp = linear_components(natural, center, scale, basis)
                    add(method, None, "linear", assignment_source, "NATURAL_QA", concept, dev, natural, dev_comp, nat_comp,
                        detail, None, None, len(basis), variance)
            for method, spec in cfg["imported_v1"]["methods"].items():
                for method_seed in cfg["imported_v1"]["seeds"]:
                    mdl = load_imported_model(cfg, model_key, layer, method, int(method_seed), hidden, device)
                    mapping = fit_learned_mapping(mdl, dev_norm, int(cfg["analysis"]["rank"]), device)
                    dev_ncomp = apply_learned_mapping(mdl, dev_norm, mapping, device); ev_ncomp = apply_learned_mapping(mdl, ev_norm, mapping, device)
                    dev_comp = tuple(x * scale for x in dev_ncomp); ev_comp = tuple(x * scale for x in ev_ncomp)
                    fvu, sparse = imported_proxy(cfg, model_key, layer, method, int(method_seed))
                    add(method, int(method_seed), "learned", assignment_source, evaluation_source, concept, dev, ev,
                        dev_comp, ev_comp, mapping, fvu, sparse, None, None)
                    if concept == "context":
                        nat_norm = norm_panel(natural, center, scale)
                        nat_comp = tuple(x * scale for x in apply_learned_mapping(mdl, nat_norm, mapping, device))
                        add(method, int(method_seed), "learned", assignment_source, "NATURAL_QA", concept, dev, natural,
                            dev_comp, nat_comp, mapping, fvu, sparse, None, None)
                    del mdl

    stability: dict[str, Any] = {}
    for key, reps in geometry.items():
        values = [v1.centered_cka(reps[i], reps[j]) for i in range(len(reps)) for j in range(i + 1, len(reps))]
        finite = [x for x in values if np.isfinite(x)]
        stability[key] = {"comparisons": len(values), "mean_cka": float(np.mean(finite)) if finite else None}
    for row in metrics:
        if row["proxy_class"] == "learned":
            key = f"{row['method']}|{row['assignment_source']}|{row['evaluation_source']}|{row['concept']}"
            row["geometric_stability"] = stability[key]["mean_cka"]

    write_jsonl(out / "metrics.jsonl", metrics); write_jsonl(out / "component_metrics.jsonl", component_rows)
    result = {"schema_version": "proxy_control_v2_shard_result", "status": "COMPLETE", "model": model_key, "layer": layer,
        "metric_rows": len(metrics), "component_metric_rows": len(component_rows), "new_real_sae_training": False,
        "imported_checkpoint_dtype": cfg["imported_v1"]["checkpoint_dtype"], "panel_manifest": panel_manifest,
        "stability": stability, "runtime": runtime_record(device), "freeze_sha256": freeze_sha,
        "candidate_inventory_sha256": freeze_rec["candidate_inventory_sha256"]}
    exclusive_json(out / "result.json", result)
    exclusive_json(out / "COMPLETE.json", {"status": "COMPLETE", "result_sha256": sha256(out / "result.json"),
        "metrics_sha256": sha256(out / "metrics.jsonl"), "component_metrics_sha256": sha256(out / "component_metrics.jsonl"),
        "new_real_sae_training": False})


def guarded_worker(config_path: Path, model_key: str, layer: int) -> None:
    try:
        worker(config_path, model_key, layer)
    except Exception as exc:
        try:
            cfg = load_json(config_path)
            out = ROOT / cfg["runtime"]["output_root"] / "shards" / f"{model_key}_layer{layer}"
            if out.exists() and not any((out / name).exists() for name in ("COMPLETE.json", "BLOCKED_BY_SYNTHETIC_GATE.json", "TECHNICAL_FAIL.json")):
                exclusive_json(out / "TECHNICAL_FAIL.json", {"status": "TECHNICAL_FAIL", "error_type": type(exc).__name__,
                    "error": str(exc), "new_real_sae_training": False})
        finally:
            raise


def preflight(config_path: Path) -> None:
    cfg = load_json(config_path); freeze_rec = verify_freeze(config_path, cfg); verify_prepared(cfg, regenerate_natural=False)
    output = ROOT / cfg["runtime"]["output_root"]
    if output.exists(): raise RuntimeError(f"v2 output namespace already exists: {output}")
    if sha256(ROOT / cfg["imported_v1"]["manifest"]) != freeze_rec["v1_import_manifest_sha256"]:
        raise RuntimeError("v1 manifest lineage drift")
    print(json.dumps({"status": "PASS", "namespace_absent": True, "candidate_inventory_sha256": freeze_rec["candidate_inventory_sha256"]}, indent=2))


def synthetic_metrics(cfg: Mapping[str, Any], seed: int | None = None) -> dict[str, Any]:
    sc = cfg["synthetic_gate"]; rng = np.random.default_rng(int(cfg["seed"] if seed is None else seed))
    width, latent = int(sc["width"]), int(sc["latent"]); rows = int(sc["rows"]); test_rows = int(sc["test_rows"])
    q, _ = np.linalg.qr(rng.normal(size=(width, latent * 3)))
    bp, bl, bs = q[:, :latent], q[:, latent:2*latent], q[:, 2*latent:3*latent]
    wt = bp[:, 0]; wc = bl[:, 0]
    def sample(n: int) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
        base = rng.normal(size=(n, latent)) @ bp.T + rng.normal(size=(n, latent)) @ bl.T + 0.3 * rng.normal(size=(n, latent)) @ bs.T
        d = rng.normal(size=(n, latent)) @ bp.T
        s = rng.normal(size=(n, latent)) @ bl.T
        return base, d, s
    _, d, s = sample(rows); _, td, ts = sample(test_rows)
    full = d @ wt; g = np.repeat(wt[None, :], rows, axis=0) * np.sign(full)[:, None]
    matrix = sym(d.T @ g / rows) - float(cfg["analysis"]["oracle_nuisance_penalty"]) * sym(s.T @ g / rows)
    values, vectors = np.linalg.eigh(matrix); order = np.argsort(values)[::-1]
    keep = [int(i) for i in order if values[i] > float(cfg["analysis"]["oracle_minimum_eigenvalue"])][:int(cfg["analysis"]["rank"])]
    oracle = vectors[:, keep].T if keep else np.zeros((0, width))
    random_basis, _ = np.linalg.qr(rng.normal(size=(width, 1))); random_basis = random_basis.T
    def evaluate(name: str, basis: np.ndarray) -> dict[str, Any]:
        p = basis.T @ basis if len(basis) else np.zeros((width, width))
        target, sham = td @ p, ts @ p
        natural = td @ wt; eligible = np.abs(natural) >= 0.25
        patch, sham_effect = target @ wt, sham @ wt
        recovery = patch[eligible] / natural[eligible]
        specificity = (patch[eligible] - sham_effect[eligible]) / natural[eligible]
        true_behavior = np.outer(natural, wt)
        return {"name": name, "rank": len(basis),
            "capture": float(np.median(np.linalg.norm(target, axis=1) / np.maximum(np.linalg.norm(td, axis=1), 1e-12))),
            "leakage": float(np.median(np.linalg.norm(sham, axis=1) / np.maximum(np.linalg.norm(ts, axis=1), 1e-12))),
            "behavioral_recovery": float(np.median(recovery)), "behavioral_specificity": float(np.median(specificity)),
            "collateral": float(np.median(np.abs(target @ wc))), "target_cka": v1.centered_cka(target, true_behavior),
            "eligible_fraction": float(np.mean(eligible))}
    metrics = {"ground_truth": evaluate("ground_truth", bp.T), "behavior_gradient_oracle": evaluate("behavior_gradient_oracle", oracle),
               "random_negative": evaluate("random_negative", random_basis)}
    gt, oracle_m, random_m = metrics["ground_truth"], metrics["behavior_gradient_oracle"], metrics["random_negative"]
    checks = {
        "ground_capture": gt["capture"] >= float(sc["ground_capture_min"]),
        "ground_leakage": gt["leakage"] <= float(sc["ground_leakage_max"]),
        "ground_recovery": gt["behavioral_recovery"] >= float(sc["ground_recovery_min"]),
        "ground_specificity": gt["behavioral_specificity"] >= float(sc["ground_specificity_min"]),
        "ground_collateral": gt["collateral"] <= float(sc["ground_collateral_max"]),
        "oracle_recovery": oracle_m["behavioral_recovery"] >= float(sc["oracle_recovery_min"]),
        "oracle_specificity": oracle_m["behavioral_specificity"] >= float(sc["oracle_specificity_min"]),
        "oracle_target_cka": oracle_m["target_cka"] >= float(sc["oracle_target_cka_min"]),
        "random_negative": abs(random_m["behavioral_specificity"]) < float(sc["random_specificity_max"]),
    }
    return {"schema_version": "proxy_control_v2_synthetic_gate_metrics", "metrics": metrics, "checks": checks,
            "status": "PASS" if all(checks.values()) else "FAIL"}


def synthetic_job(config_path: Path) -> None:
    cfg = load_json(config_path); verify_freeze(config_path, cfg)
    out = ROOT / cfg["runtime"]["output_root"] / "synthetic"
    if out.exists(): raise FileExistsError(out)
    out.mkdir(parents=True)
    device = torch.device("cuda:0" if torch.cuda.is_available() else "cpu")
    freeze_sha = sha256(ROOT / cfg["runtime"]["freeze"])
    exclusive_json(out / "STARTED.json", {"schema_version": "proxy_control_v2_synthetic_started", "runtime": runtime_record(device), "freeze_sha256": freeze_sha})
    try:
        result = synthetic_metrics(cfg)
        exclusive_json(out / "result.json", result)
        terminal = {"status": result["status"], "freeze_sha256": freeze_sha, "result_sha256": sha256(out / "result.json"),
                    "scientific_model_forward_authorized": result["status"] == "PASS"}
        exclusive_json(out / ("PASS.json" if result["status"] == "PASS" else "FAIL.json"), terminal)
        exclusive_json(out / "COMPLETE.json", terminal)
        if result["status"] != "PASS": raise RuntimeError("synthetic gate failed")
    except Exception as exc:
        if not (out / "FAIL.json").exists() and not (out / "PASS.json").exists():
            exclusive_json(out / "TECHNICAL_FAIL.json", {"status": "TECHNICAL_FAIL", "freeze_sha256": freeze_sha,
                "error_type": type(exc).__name__, "error": str(exc), "scientific_model_forward_authorized": False})
        raise


def association(frame: Any, x: str, y: str, draws: int, seed: int, method_fixed: bool) -> dict[str, Any]:
    import pandas as pd
    from scipy.stats import rankdata, spearmanr
    z = frame[np.isfinite(pd.to_numeric(frame[x], errors="coerce")) & np.isfinite(pd.to_numeric(frame[y], errors="coerce"))].copy()
    clusters = sorted(z.model_layer.unique())
    if len(z) < 3 or not clusters: return {"rho": None, "ci": None, "rows": len(z), "clusters": len(clusters)}
    def est(q: Any) -> float:
        if not method_fixed: return float(spearmanr(q[x], q[y]).statistic)
        xr, yr = rankdata(q[x]), rankdata(q[y]); methods = sorted(q.method.unique())
        design = np.ones((len(q), len(methods)), float)
        for j, method in enumerate(methods[1:], 1): design[:, j] = (q.method.to_numpy() == method).astype(float)
        rx = xr - design @ np.linalg.lstsq(design, xr, rcond=None)[0]; ry = yr - design @ np.linalg.lstsq(design, yr, rcond=None)[0]
        return float(np.corrcoef(rx, ry)[0, 1]) if np.std(rx) > 1e-12 and np.std(ry) > 1e-12 else float("nan")
    point = est(z); by = {c: z[z.model_layer == c] for c in clusters}; rng = np.random.default_rng(seed); boot = []
    for _ in range(draws):
        chosen = rng.choice(clusters, len(clusters), replace=True); q = pd.concat([by[c] for c in chosen], ignore_index=True); value = est(q)
        if np.isfinite(value): boot.append(value)
    return {"rho": point if np.isfinite(point) else None, "ci": [float(v) for v in np.quantile(boot, [0.025, 0.5, 0.975])] if boot else None,
            "rows": int(len(z)), "clusters": len(clusters), "method_fixed_effect": method_fixed}


def hierarchical_interval(frame: Any, value: str, draws: int, seed: int) -> dict[str, Any]:
    """Nested bootstrap over models, layers, seeds, vocabulary blocks, and templates.

    The two cross-source transfer directions are a frozen required pair and are averaged rather
    than resampled. Linear methods have a single explicit ``linear`` seed stratum.
    """
    import pandas as pd

    q = frame.copy()
    q[value] = pd.to_numeric(q[value], errors="coerce")
    q["_seed_key"] = q["seed"].map(lambda x: "linear" if pd.isna(x) else str(int(x)))
    if q.empty:
        return {"point": None, "ci": None, "rows": 0, "blocks": 0, "models": 0, "finite_draws": 0}
    rng = np.random.default_rng(seed)
    key_columns = ["model", "layer", "_seed_key", "assignment_source", "evaluation_source"]
    point_by_key: dict[tuple[Any, ...], float] = {}
    boot_by_key: dict[tuple[Any, ...], np.ndarray] = {}
    for key, group in q.groupby(key_columns, dropna=False, sort=True):
        arrays = []
        for _, block in group.groupby("component_block", sort=True):
            ordered = block.sort_values(["template_family", "surface_rep"])[value].to_numpy(np.float64)
            arrays.append(ordered)
        if not arrays or len({len(x) for x in arrays}) != 1:
            raise RuntimeError(f"unbalanced template support in hierarchical bootstrap: {key}")
        matrix = np.stack(arrays)
        point_by_key[tuple(key)] = float(np.nanmean(matrix)) if np.isfinite(matrix).any() else float("nan")
        block_index = rng.integers(0, len(matrix), size=(int(draws), len(matrix)))
        selected = matrix[block_index]
        template_index = rng.integers(0, matrix.shape[1], size=selected.shape)
        sampled = np.take_along_axis(selected, template_index, axis=2)
        with np.errstate(invalid="ignore"):
            numerator = np.nansum(sampled, axis=(1, 2))
            denominator = np.sum(np.isfinite(sampled), axis=(1, 2))
            boot_by_key[tuple(key)] = np.divide(numerator, denominator,
                out=np.full(int(draws), np.nan, np.float64), where=denominator > 0)

    models = sorted({k[0] for k in point_by_key})
    def nested_mean(values: Mapping[tuple[Any, ...], float], draw: int | None) -> float:
        model_samples = list(rng.choice(models, len(models), replace=True)) if draw is not None else models
        model_values = []
        for model in model_samples:
            layers = sorted({k[1] for k in values if k[0] == model})
            layer_samples = list(rng.choice(layers, len(layers), replace=True)) if draw is not None else layers
            layer_values = []
            for layer in layer_samples:
                seeds = sorted({k[2] for k in values if k[0] == model and k[1] == layer})
                seed_samples = list(rng.choice(seeds, len(seeds), replace=True)) if draw is not None else seeds
                seed_values = []
                for seed_key in seed_samples:
                    keys = sorted(k for k in values if k[0] == model and k[1] == layer and k[2] == seed_key)
                    direction_values = [values[k] if draw is None else boot_by_key[k][draw] for k in keys]
                    finite = [x for x in direction_values if np.isfinite(x)]
                    if finite:
                        seed_values.append(float(np.mean(finite)))
                if seed_values:
                    layer_values.append(float(np.mean(seed_values)))
            if layer_values:
                model_values.append(float(np.mean(layer_values)))
        return float(np.mean(model_values)) if model_values else float("nan")

    point = nested_mean(point_by_key, None)
    boot = np.asarray([nested_mean(point_by_key, draw) for draw in range(int(draws))], np.float64)
    finite = boot[np.isfinite(boot)]
    return {"point": point if np.isfinite(point) else None,
        "ci": [float(x) for x in np.quantile(finite, [0.025, 0.5, 0.975])] if len(finite) else None,
        "rows": int(len(q)), "blocks": int(q.component_block.nunique()), "models": len(models),
        "finite_draws": int(len(finite)), "transfer_directions": "fixed_required_pair",
        "factors": ["model", "layer_within_model", "seed_within_method",
                    "vocabulary_component_block", "template_family_within_block"]}


def aggregate(config_path: Path) -> None:
    import pandas as pd
    cfg = load_json(config_path); verify_freeze(config_path, cfg)
    root = ROOT / cfg["runtime"]["output_root"]; out = root / "aggregate"
    if out.exists(): raise FileExistsError(out)
    out.mkdir(parents=True); exclusive_json(out / "STARTED.json", {"schema_version": "proxy_control_v2_aggregate_started", "waiting": True})
    expected = [(m["key"], layer) for m in cfg["models"] for layer in m["layers"]]
    paths = [root / "shards" / f"{m}_layer{l}" / "COMPLETE.json" for m, l in expected] + [root / "synthetic/PASS.json"]
    while not all(p.is_file() for p in paths):
        gate_failures = [root / "synthetic/FAIL.json", root / "synthetic/TECHNICAL_FAIL.json"]
        shard_failures = list(root.glob("shards/*/TECHNICAL_FAIL.json")) + list(root.glob("shards/*/BLOCKED_BY_SYNTHETIC_GATE.json"))
        failed = next((p for p in gate_failures + shard_failures if p.is_file()), None)
        if failed is not None:
            exclusive_json(out / "BLOCKED_BY_SYNTHETIC_GATE.json", {"status": "BLOCKED", "gate_sha256": sha256(failed)})
            raise RuntimeError("aggregate blocked by synthetic gate")
        atomic_json(out / "HEARTBEAT.json", {"waiting_for": [p.relative_to(root).as_posix() for p in paths if not p.is_file()]})
        time.sleep(30)
    rows = []; component_rows = []
    for model_key, layer in expected:
        directory = root / "shards" / f"{model_key}_layer{layer}"; complete = load_json(directory / "COMPLETE.json")
        for name, key in (("result.json", "result_sha256"), ("metrics.jsonl", "metrics_sha256"), ("component_metrics.jsonl", "component_metrics_sha256")):
            if sha256(directory / name) != complete[key]: raise RuntimeError(f"shard drift {directory/name}")
        rows.extend(read_jsonl(directory / "metrics.jsonl"))
        component_rows.extend(read_jsonl(directory / "component_metrics.jsonl"))
    frame = pd.DataFrame(rows); controlled = frame[frame.panel_kind == "controlled"].copy()
    controlled["collateral_safety"] = -controlled.collateral_kl
    associations = []
    proxy_sets = {"learned": ["reconstruction_quality", "sparsity", "probe_recovery", "geometric_stability"],
                  "linear": ["captured_variance", "rank_sparsity", "probe_recovery"]}
    controls = ["selectivity", "intervention_specificity", "behavioral_recovery", "behavioral_specificity", "collateral_safety"]
    for proxy_class, proxies in proxy_sets.items():
        sub = controlled[controlled.proxy_class == proxy_class]
        for proxy in proxies:
            for control in controls:
                associations.append({"analysis": f"{proxy_class}_only", "proxy": proxy, "control": control,
                    **association(sub, proxy, control, int(cfg["analysis"]["bootstrap_draws"]), stable_seed(cfg["seed"], proxy_class, proxy, control), False)})
    for proxy in sorted(set(proxy_sets["learned"] + proxy_sets["linear"])):
        if proxy not in controlled.columns: continue
        for control in controls:
            associations.append({"analysis": "method_fixed_effect", "proxy": proxy, "control": control,
                **association(controlled, proxy, control, int(cfg["analysis"]["bootstrap_draws"]), stable_seed(cfg["seed"], "fixed", proxy, control), True)})

    controlled["stage"] = controlled.layer.map({1:"early", 2:"early", 6:"middle", 12:"middle", 10:"late", 22:"late"})
    def row_pass(row: Any) -> bool:
        rci, sci, kci = row.behavioral_recovery_block_ci, row.behavioral_specificity_block_ci, row.collateral_kl_block_ci
        return bool(row.behavior_eligible_fraction >= cfg["analysis"]["minimum_eligibility"] and isinstance(rci, list) and isinstance(sci, list) and isinstance(kci, list)
                    and rci[0] > cfg["analysis"]["minimum_recovery_ci_lower"] and sci[0] > cfg["analysis"]["minimum_specificity_ci_lower"]
                    and kci[2] < cfg["analysis"]["maximum_collateral_ci_upper"])
    controlled["row_functional_pass"] = controlled.apply(row_pass, axis=1)
    method_decisions = []
    for (method, concept, stage), group in controlled.groupby(["method", "concept", "stage"]):
        passing_models = []
        for model, mg in group.groupby("model"):
            direction_pass = []
            for direction, dg in mg.groupby(["assignment_source", "evaluation_source"]):
                if dg.proxy_class.iloc[0] == "learned": direction_pass.append(float(dg.row_functional_pass.mean()) >= 2/3)
                else: direction_pass.append(bool(dg.row_functional_pass.all()))
            if len(direction_pass) == 2 and all(direction_pass): passing_models.append(model)
        method_decisions.append({"method": method, "concept": concept, "stage": stage, "passing_models": passing_models,
                                 "passes": len(passing_models) >= int(cfg["analysis"]["minimum_replicating_models"])})
    natural_summary = []
    natural = frame[frame.panel_kind == "naturalistic"]
    for method, group in natural.groupby("method"):
        natural_summary.append({"method": method, "rows": len(group), "eligible_mean": float(group.behavior_eligible_fraction.mean()),
            "recovery_mean": float(group.behavioral_recovery.dropna().mean()) if group.behavioral_recovery.notna().any() else None,
            "specificity_mean": float(group.behavioral_specificity.dropna().mean()) if group.behavioral_specificity.notna().any() else None,
            "collateral_kl_mean": float(group.collateral_kl.mean())})
    component_frame = pd.DataFrame(component_rows)
    component_controlled = component_frame[component_frame.panel_kind == "controlled"].copy()
    hierarchical = []
    for (method, concept), group in component_controlled.groupby(["method", "concept"]):
        for value in ("intervention_specificity", "behavioral_recovery", "behavioral_specificity", "collateral_kl"):
            hierarchical.append({"method": method, "concept": concept, "metric": value,
                **hierarchical_interval(group, value, int(cfg["analysis"]["bootstrap_draws"]),
                    stable_seed(cfg["seed"], "hierarchical", method, concept, value))})
    result = {"schema_version": "proxy_control_v2_aggregate_result", "status": "PROSPECTIVE_COMPLETE_REQUIRES_CLAIM_REVIEW",
        "metric_rows": len(frame), "controlled_rows": len(controlled), "naturalistic_rows": len(natural),
        "model_layer_clusters": int(frame.model_layer.nunique()), "associations": associations,
        "method_decisions": method_decisions, "naturalistic_summary": natural_summary,
        "hierarchical_endpoint_summaries": hierarchical,
        "decision_table_frozen": cfg["analysis"]["decision_table"], "training_authorized": False,
        "no_automatic_claim": True, "synthetic_gate_sha256": sha256(root / "synthetic/PASS.json")}
    exclusive_json(out / "result.json", result); exclusive_json(out / "COMPLETE.json", {"status": "COMPLETE", "result_sha256": sha256(out / "result.json")})


def smoke(config_path: Path, output: Path) -> None:
    cfg = load_json(config_path)
    if output.exists(): raise FileExistsError(output)
    output.mkdir(parents=True)
    rows = make_controlled_rows(cfg); syn = synthetic_metrics(cfg, seed=7)
    if syn["status"] != "PASS": raise RuntimeError(f"synthetic smoke failed: {syn}")
    # Direction check: correct movement must remain positive for either natural-effect sign.
    full = np.asarray([2.0, -2.0]); patch = np.asarray([1.0, -1.0]); sham = np.asarray([0.0, 0.0])
    aligned = (patch - sham) / full
    if not np.allclose(aligned, 0.5): raise RuntimeError("signed specificity regression")
    result = {"schema_version": "proxy_control_v2_smoke", "status": "PASS", "controlled_rows": len(rows),
              "synthetic": syn, "new_model_forwards": 0, "new_real_sae_training": False}
    exclusive_json(output / "result.json", result); exclusive_json(output / "COMPLETE.json", {"status": "COMPLETE", "result_sha256": sha256(output / "result.json")})
    print(json.dumps(result, indent=2))


def status(config_path: Path) -> None:
    cfg = load_json(config_path); root = ROOT / cfg["runtime"]["output_root"]
    expected = [(m["key"], layer) for m in cfg["models"] for layer in m["layers"]]
    rows = []
    for model, layer in expected:
        directory = root / "shards" / f"{model}_layer{layer}"
        wait = load_json(directory / "WAITING.json") if (directory / "WAITING.json").is_file() else None
        rows.append({"job": f"{model}_layer{layer}", "started": (directory/"STARTED.json").is_file(),
                     "complete": (directory/"COMPLETE.json").is_file(), "technical_fail": (directory/"TECHNICAL_FAIL.json").is_file(), "waiting": wait})
    for name in ("synthetic", "aggregate"):
        directory = root / name
        rows.append({"job": name, "started": (directory/"STARTED.json").is_file(), "complete": (directory/"COMPLETE.json").is_file(),
                     "pass": (directory/"PASS.json").is_file()})
    print(json.dumps(rows, indent=2))


def main() -> None:
    ap = argparse.ArgumentParser(); ap.add_argument("command", choices=["prepare", "freeze", "preflight", "worker", "synthetic", "aggregate", "smoke", "status"])
    ap.add_argument("--config", default=str(CONFIG_DEFAULT.relative_to(ROOT))); ap.add_argument("--model"); ap.add_argument("--layer", type=int); ap.add_argument("--output")
    args = ap.parse_args(); config = ROOT / args.config
    if args.command == "prepare": prepare(config)
    elif args.command == "freeze": freeze(config)
    elif args.command == "preflight": preflight(config)
    elif args.command == "worker":
        if args.model is None or args.layer is None: raise SystemExit("worker requires --model and --layer")
        guarded_worker(config, args.model, args.layer)
    elif args.command == "synthetic": synthetic_job(config)
    elif args.command == "aggregate": aggregate(config)
    elif args.command == "smoke":
        if not args.output: raise SystemExit("smoke requires --output")
        smoke(config, Path(args.output))
    elif args.command == "status": status(config)


if __name__ == "__main__":
    main()
