#!/usr/bin/env python3
"""Extract frozen L3/L4 activations for the atlas analysis sample."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import subprocess
import time
from pathlib import Path
from typing import Any

import numpy as np
import torch
from transformers import AutoModelForCausalLM

from train_msae_k2 import resolve_hidden_state_index
from atlas_freeze import (assert_role_access, utc_now, verify_activation_complete,
                          verify_calibration_sources, verify_freeze, verify_layer_trigger)


ROOT = Path(__file__).resolve().parents[1]


def sha256(path: Path, block: int = 16 << 20) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        while chunk := f.read(block):
            h.update(chunk)
    return h.hexdigest()


def jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text().splitlines() if line]


def git_state() -> dict[str, str]:
    def run(*args: str) -> str:
        return subprocess.check_output(args, cwd=ROOT, text=True, stderr=subprocess.DEVNULL).strip()
    return {"head": run("git", "rev-parse", "HEAD"), "diff_hash": hashlib.sha256(run("git", "diff", "--binary").encode()).hexdigest()}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--role", required=True, choices=["discovery", "calibration", "C1", "C2"])
    parser.add_argument("--run-root", type=Path, default=ROOT / "pilot_runs/20260731_atlas_v1_architecture_selection")
    parser.add_argument("--device", default="cuda:0")
    parser.add_argument("--batch-size", type=int, default=0)
    args = parser.parse_args()
    freeze = verify_freeze()
    assert_role_access(args.role)
    trigger_path = ROOT / "results/atlas/raw_v1/layer_trigger_freeze.json"
    if args.role in {"C1", "C2"}:
        verify_layer_trigger(trigger_path, freeze)
        verify_calibration_sources(trigger_path, args.run_root, freeze)
    config = json.loads((ROOT / "configs/atlas/analysis_run.json").read_text())
    sources = json.loads((ROOT / "configs/atlas/data_sources.json").read_text())
    sample = json.loads((ROOT / "configs/atlas/analysis_sample_manifest.json").read_text())
    selected = set(sample["roles"][args.role]["base_ids"])
    all_records = jsonl(ROOT / f"data/atlas_v1/partitions/{args.role}.records.jsonl")
    records = [row for row in all_records if row["base_id"] in selected]
    records.sort(key=lambda row: row["base_id"])
    record_index = {row["base_id"]: i for i, row in enumerate(records)}
    units = [row for row in jsonl(ROOT / f"data/atlas_v1/partitions/{args.role}.units.jsonl") if row["base_id"] in selected]
    units.sort(key=lambda row: row["variant_id"])
    if len(units) != 4 * len(records):
        raise RuntimeError("sample lost offset variants")
    output = args.run_root / "raw_activations" / args.role
    output.mkdir(parents=True, exist_ok=True)
    if (output / "COMPLETE.json").exists():
        verify_activation_complete(output, args.role, freeze)
        print(f"already complete: {output}")
        return
    if any(output.iterdir()):
        raise RuntimeError(f"incomplete activation directory is not overwritten automatically: {output}")

    started = time.time()
    started_utc = utc_now()
    device = torch.device(args.device)
    if device.type != "cuda" or not torch.cuda.is_available():
        raise RuntimeError("atlas-v1 score-bearing activation extraction requires CUDA fp16; CPU output is refused")
    dtype = torch.float16
    model = AutoModelForCausalLM.from_pretrained(sources["model"]["name"], revision=sources["model"]["revision"],
                                                torch_dtype=dtype).to(device)
    model.eval()
    batch_size = args.batch_size or int(config["batch_size"])
    total_rows = sum(len(unit["input_ids"]) for unit in units)
    first_ids = torch.tensor([units[0]["input_ids"]], device=device)
    with torch.inference_mode():
        first_out = model(first_ids, output_hidden_states=True, use_cache=False)
    layer_indices = {layer: resolve_hidden_state_index(int(layer), len(first_out.hidden_states)) for layer in config["layers"]}
    d_model = int(first_out.hidden_states[next(iter(layer_indices.values()))].shape[-1])
    arrays = {layer: np.lib.format.open_memmap(output / f"L{layer}.float16.npy", mode="w+", dtype=np.float16,
                                               shape=(total_rows, d_model)) for layer in config["layers"]}
    meta = {"record_index": np.empty(total_rows, np.int32), "unit_index": np.empty(total_rows, np.int32),
            "token_index": np.empty(total_rows, np.int16), "word_index": np.full(total_rows, -2, np.int16),
            "abs_pos_16": np.empty(total_rows, np.uint8), "abs_pos_8": np.empty(total_rows, np.uint8),
            "offset": np.empty(total_rows, np.uint8), "continuation_code": np.empty(total_rows, np.int8)}
    continuation_codes = {"prefix": 0, "first": 1, "continuation": 2, "__DROP__": -1}
    cursor = 0
    for start in range(0, len(units), batch_size):
        batch = units[start:start + batch_size]
        max_len = max(len(row["input_ids"]) for row in batch)
        input_ids = torch.zeros((len(batch), max_len), dtype=torch.long, device=device)
        attention = torch.zeros_like(input_ids)
        for bi, row in enumerate(batch):
            n = len(row["input_ids"])
            input_ids[bi, :n] = torch.tensor(row["input_ids"], dtype=torch.long, device=device)
            attention[bi, :n] = 1
        with torch.inference_mode():
            out = model(input_ids, attention_mask=attention, output_hidden_states=True, use_cache=False)
        for bi, unit in enumerate(batch):
            n = len(unit["input_ids"])
            span = slice(cursor, cursor + n)
            for layer, hidden_index in layer_indices.items():
                arrays[layer][span] = out.hidden_states[hidden_index][bi, :n].detach().float().cpu().numpy().astype(np.float16)
            meta["record_index"][span] = record_index[unit["base_id"]]
            meta["unit_index"][span] = start + bi
            meta["token_index"][span] = np.arange(n, dtype=np.int16)
            word_positions = {int(x["model_token_index"]): int(x["word_index"]) for x in unit["first_subword_rows"]}
            for token_position, word_idx in word_positions.items():
                meta["word_index"][cursor + token_position] = word_idx
            meta["abs_pos_16"][span] = np.asarray(unit["absolute_labels"]["abs_pos_16"], dtype=np.uint8)
            meta["abs_pos_8"][span] = np.asarray(unit["absolute_labels"]["abs_pos_8"], dtype=np.uint8)
            meta["offset"][span] = int(unit["offset"])
            meta["continuation_code"][span] = [continuation_codes[x] for x in unit["continuation_status"]]
            cursor += n
        if start % (batch_size * 50) == 0:
            print(json.dumps({"role": args.role, "units": start + len(batch), "total_units": len(units), "rows": cursor,
                              "elapsed_sec": time.time() - started}), flush=True)
    if cursor != total_rows:
        raise RuntimeError(f"row mismatch {cursor} != {total_rows}")
    for array in arrays.values():
        array.flush()
    np.savez_compressed(output / "row_meta.npz", **meta)
    with (output / "records.jsonl").open("w") as f:
        for row in records:
            f.write(json.dumps(row, sort_keys=True, separators=(",", ":")) + "\n")
    unit_public = [{k: row[k] for k in ["variant_id", "base_id", "offset", "prefix_word"]} for row in units]
    (output / "units.json").write_text(json.dumps(unit_public, indent=2, sort_keys=True) + "\n")
    artifacts = {}
    for path in sorted(output.iterdir()):
        if path.is_file() and path.name != "COMPLETE.json":
            artifacts[path.name] = {"sha256": sha256(path), "bytes": path.stat().st_size}
    complete = {"schema_version": "atlas_v1_activation_extract", "role": args.role, "rows": total_rows,
                "records": len(records), "units": len(units), "d_model": d_model, "layers": config["layers"],
                "model": sources["model"], "sample_digest": sample["roles"][args.role]["base_id_digest"],
                "batch_size": batch_size, "device": str(device), "dtype": str(dtype), "elapsed_sec": time.time() - started,
                "started_utc": started_utc, "ended_utc": utc_now(),
                "resolved_config": {"role": args.role, "device": str(device), "batch_size": batch_size,
                                    "seed": config["seed"], "layers": config["layers"], "dtype": config["dtype"]},
                "environment": {"python": platform.python_version(), "torch": torch.__version__, "cuda": torch.version.cuda,
                                "gpu": torch.cuda.get_device_name(device) if device.type == "cuda" else "cpu"},
                "git": git_state(), "prescore_bundle_sha256": freeze["bundle_sha256"], "artifacts": artifacts}
    (output / "COMPLETE.json").write_text(json.dumps(complete, indent=2, sort_keys=True) + "\n")
    verify_activation_complete(output, args.role, freeze)
    print(json.dumps(complete, indent=2))


if __name__ == "__main__":
    os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")
    main()
