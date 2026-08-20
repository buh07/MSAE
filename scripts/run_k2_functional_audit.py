#!/usr/bin/env python3
"""Counterfactual and suffix-CE diagnostics for one frozen existing K=2 checkpoint."""

from __future__ import annotations

import argparse
import json
import math
import pickle
from collections import defaultdict
from pathlib import Path
from typing import Any

import numpy as np
import torch
import torch.nn.functional as F
from transformers import AutoModelForCausalLM, AutoTokenizer

from atlas_freeze import (artifact_hash, checkpoint_spec, runtime_environment, utc_now,
                          verify_activation_complete, verify_freeze,
                          verify_calibration_sources, verify_layer_trigger, verify_transform_complete)
from train_msae_k2 import K2MSAE


ROOT = Path(__file__).resolve().parents[1]


def cosine_distance(a: np.ndarray, b: np.ndarray) -> float:
    denom = max(float(np.linalg.norm(a) * np.linalg.norm(b)), 1e-12)
    return float(1.0 - float(np.dot(a, b)) / denom)


def load_checkpoint(job: str, device: torch.device) -> tuple[K2MSAE, dict[str, Any]]:
    frozen = checkpoint_spec(job)
    row = frozen["metadata"]
    checkpoint = torch.load(frozen["path"], map_location="cpu", weights_only=False)
    args = checkpoint["args"]
    msae = K2MSAE(768, int(args["m_pos"]), int(args["k_pos"]), int(args["m_content"]), int(args["k_content"]))
    msae.load_state_dict(checkpoint["model"])
    return msae.to(device).eval(), {"metadata": row, "checkpoint_args": args, "checkpoint_sha256": frozen["sha256"]}


def representations(h: torch.Tensor, msae: K2MSAE) -> dict[str, np.ndarray]:
    with torch.inference_mode():
        out = msae(h.reshape(-1, h.shape[-1]).float())
    pos = out["recon_pos"].reshape(h.shape).mean(dim=(0, 1)).detach().cpu().numpy()
    content = out["recon_content"].reshape(h.shape).mean(dim=(0, 1)).detach().cpu().numpy()
    raw = h.float().mean(dim=(0, 1)).detach().cpu().numpy()
    return {"raw": raw, "pos": pos, "content": content, "joint": np.concatenate([pos, content]),
            "resid": raw - pos - content}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--job", required=True)
    parser.add_argument("--device", default="cuda:0")
    parser.add_argument("--output", type=Path, default=ROOT / "results/atlas/k2_v1")
    parser.add_argument("--raw-results", type=Path, default=ROOT / "results/atlas/raw_v1")
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    result_path = args.output / f"{args.job}_functional.json"
    marker_path = args.output / f"{args.job}_functional_COMPLETE.json"
    if result_path.exists() or marker_path.exists():
        raise RuntimeError(f"functional audit is create-once and is not overwritten: {args.job}")
    started = __import__("time").time()
    started_utc = utc_now()
    freeze = verify_freeze()
    trigger_path = args.raw_results / "layer_trigger_freeze.json"
    verify_layer_trigger(trigger_path, freeze)
    device = torch.device(args.device)
    if device.type != "cuda" or not torch.cuda.is_available():
        raise RuntimeError("atlas-v1 functional audit requires CUDA fp16; CPU output is refused")
    sources = json.loads((ROOT / "configs/atlas/data_sources.json").read_text())
    tokenizer = AutoTokenizer.from_pretrained(sources["model"]["name"], revision=sources["model"]["revision"], use_fast=True)
    lm = AutoModelForCausalLM.from_pretrained(sources["model"]["name"], revision=sources["model"]["revision"],
                                              torch_dtype=torch.float16).to(device).eval()
    msae, checkpoint_info = load_checkpoint(args.job, device)
    with (args.raw_results / "L3_calibration_bundle.pkl").open("rb") as f:
        raw_bundle = pickle.load(f)
    mean = torch.tensor(raw_bundle["mean"], dtype=torch.float32, device=device)
    scale = torch.tensor(raw_bundle["scale"], dtype=torch.float32, device=device)
    broad = torch.tensor(raw_bundle["bases"]["broad_position"], dtype=torch.float32, device=device)
    transforms = [json.loads(line) for line in (ROOT / "data/atlas_v1/transforms/C2.jsonl").read_text().splitlines()]

    # Frozen raw/K2 offset variants are used directly for position-shift counterfactuals.
    run_root = ROOT / "pilot_runs/20260731_atlas_v1_architecture_selection"
    verify_calibration_sources(trigger_path, run_root, freeze)
    verify_activation_complete(run_root / "raw_activations/C2", "C2", freeze)
    transform_dir = run_root / f"k2_transforms/{args.job}"
    verify_transform_complete(transform_dir, args.job, freeze)
    source_transform_complete_sha256 = artifact_hash(transform_dir / "COMPLETE.json")
    meta_npz = np.load(run_root / "raw_activations/C2/row_meta.npz")
    meta = {key: meta_npz[key] for key in meta_npz.files}
    raw_arr = np.load(run_root / "raw_activations/C2/L3.float16.npy", mmap_mode="r")
    pos_arr = np.load(run_root / f"k2_transforms/{args.job}/C2/pos.float16.npy", mmap_mode="r")
    content_arr = np.load(run_root / f"k2_transforms/{args.job}/C2/content.float16.npy", mmap_mode="r")
    records = [json.loads(line) for line in (run_root / "raw_activations/C2/records.jsonl").read_text().splitlines()]
    base_to_index = {row["base_id"]: i for i, row in enumerate(records)}

    rows = []
    family_values: dict[str, dict[str, list[float]]] = defaultdict(lambda: defaultdict(list))
    for transform in transforms:
        family = transform["family"]
        if family == "position_shift":
            record_index = base_to_index.get(transform["base_id"])
            if record_index is None:
                continue
            rep_pairs = {}
            for offset in [transform["source_offset"], transform["target_offset"]]:
                idx = np.flatnonzero((meta["record_index"] == record_index) & (meta["offset"] == offset))
                raw = np.asarray(raw_arr[idx], dtype=np.float32).mean(axis=0)
                pos = np.asarray(pos_arr[idx], dtype=np.float32).mean(axis=0)
                content = np.asarray(content_arr[idx], dtype=np.float32).mean(axis=0)
                rep_pairs[offset] = {"raw": raw, "pos": pos, "content": content,
                                     "joint": np.concatenate([pos, content]), "resid": raw - pos - content}
            distances = {rep: cosine_distance(rep_pairs[transform["source_offset"]][rep], rep_pairs[transform["target_offset"]][rep])
                         for rep in rep_pairs[transform["source_offset"]]}
        else:
            pair_reps = []
            for words in [transform["source_words"], transform["target_words"]]:
                encoded = tokenizer(words, is_split_into_words=True, add_special_tokens=False, return_tensors="pt")
                with torch.inference_mode():
                    out = lm(encoded["input_ids"].to(device), output_hidden_states=True, use_cache=False)
                pair_reps.append(representations(out.hidden_states[4], msae))
            distances = {rep: cosine_distance(pair_reps[0][rep], pair_reps[1][rep]) for rep in pair_reps[0]}
        for rep, value in distances.items():
            family_values[family][rep].append(value)
        rows.append({"transform_id": transform["transform_id"], "family": family,
                     "token_aligned": transform.get("token_aligned"), "distances": distances})

    # CE interventions use hooks at block index 3, the training representation site.
    modes = ["raw", "k2_reconstruction", "remove_pos", "remove_content", "simple_remove_broad", "matched_random"]
    ce_rows = []
    generator = torch.Generator(device=device).manual_seed(20260731)

    def ce_for(ids: torch.Tensor, mode: str) -> float:
        if mode == "raw":
            with torch.inference_mode():
                logits = lm(ids, use_cache=False).logits
        else:
            def hook(_module: Any, _inputs: Any, output: Any) -> Any:
                hidden = output[0] if isinstance(output, tuple) else output
                flat = hidden.reshape(-1, hidden.shape[-1]).float()
                transformed = msae(flat)
                pos, content = transformed["recon_pos"], transformed["recon_content"]
                if mode == "k2_reconstruction":
                    replacement = pos + content
                elif mode == "remove_pos":
                    replacement = content
                elif mode == "remove_content":
                    replacement = pos
                elif mode == "simple_remove_broad":
                    standardized = (flat - mean) / scale
                    replacement = flat - ((standardized @ broad @ broad.T) * scale)
                elif mode == "matched_random":
                    error = pos + content - flat
                    noise = torch.randn(flat.shape, generator=generator, device=flat.device)
                    noise = noise / noise.norm(dim=1, keepdim=True).clamp_min(1e-8) * error.norm(dim=1, keepdim=True)
                    replacement = flat + noise
                else:
                    raise ValueError(mode)
                replacement = replacement.reshape_as(hidden).to(hidden.dtype)
                if isinstance(output, tuple):
                    return (replacement,) + output[1:]
                return replacement
            handle = lm.gpt_neox.layers[3].register_forward_hook(hook)
            try:
                with torch.inference_mode():
                    logits = lm(ids, use_cache=False).logits
            finally:
                handle.remove()
        if ids.shape[1] < 2:
            return float("nan")
        loss = F.cross_entropy(logits[:, :-1].float().reshape(-1, logits.shape[-1]), ids[:, 1:].reshape(-1), reduction="mean")
        return float(loss.item())

    text_transforms = [row for row in transforms if "source_words" in row]
    for transform in text_transforms:
        for side in ["source_words", "target_words"]:
            ids = tokenizer(transform[side], is_split_into_words=True, add_special_tokens=False, return_tensors="pt")["input_ids"].to(device)
            values = {mode: ce_for(ids, mode) for mode in modes}
            ce_rows.append({"transform_id": transform["transform_id"], "family": transform["family"], "side": side, "ce": values})

    summary = {}
    for family, reps in family_values.items():
        summary[family] = {rep: {"mean": float(np.mean(values)), "median": float(np.median(values)), "n": len(values)}
                           for rep, values in reps.items()}
    ce_summary = {mode: {"mean_ce": float(np.mean([row["ce"][mode] for row in ce_rows])),
                         "delta_vs_raw": float(np.mean([row["ce"][mode] - row["ce"]["raw"] for row in ce_rows]))}
                  for mode in modes}
    result = {"schema_version": "atlas_v1_k2_functional", "job_id": args.job,
              "prescore_bundle_sha256": freeze["bundle_sha256"],
              "layer_trigger_sha256": __import__("hashlib").sha256(trigger_path.read_bytes()).hexdigest(),
              "source_transform_complete_sha256": source_transform_complete_sha256,
              "checkpoint": checkpoint_info["metadata"]["checkpoint_relpath"], "counterfactual_rows": rows,
              "checkpoint_sha256": checkpoint_info["checkpoint_sha256"],
              "counterfactual_summary": summary, "ce_rows": ce_rows, "ce_summary": ce_summary,
              "counterfactual_gate_valid": False,
              "counterfactual_gate_invalid_reason": "matched-random and sham representation-distance comparators are not implemented",
              "limitations": ["sentence-mean cosine is descriptive", "only frozen token_aligned rows may support token-aligned claims",
                              "CE hook interventions are off-manifold unless matched-random collateral is comparable",
                              "descriptive distances cannot satisfy the preregistered counterfactual-specificity gate"]}
    result_path.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    marker = {"schema_version": "atlas_v1_k2_functional_complete", "job_id": args.job,
              "prescore_bundle_sha256": freeze["bundle_sha256"], "result_sha256": artifact_hash(result_path),
              "source_transform_complete_sha256": source_transform_complete_sha256,
              "resolved_config": {"device": str(device)}, "started_utc": started_utc, "ended_utc": utc_now(),
              "elapsed_sec": __import__("time").time() - started, "environment": runtime_environment(str(device))}
    marker_path.write_text(json.dumps(marker, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"job": args.job, "counterfactual_rows": len(rows), "ce_rows": len(ce_rows), "output": str(result_path)}, indent=2))


if __name__ == "__main__":
    main()
