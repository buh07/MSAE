#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import statistics
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
import torch
import torch.nn.functional as F
from transformers import AutoModelForCausalLM, AutoTokenizer

from pcc_stage_a1_audit import infer_d_model, load_msae_from_checkpoint, resolve_git_commit_hash, set_seed, write_tsv
from train_msae_k2 import choose_dtype, resolve_hidden_state_index
from raw_activation_separability_pilot import choose_device


@dataclass(frozen=True)
class ContrastPair:
    family: str
    contrast_type: str
    source: str
    target: str
    note: str


CONTRASTS: list[ContrastPair] = [
    # Syntax-changing, semantics-preserving
    ContrastPair("syntax_active_passive", "syntax", "The chef baked the cake for the guests.", "The cake was baked by the chef for the guests.", "active-passive"),
    ContrastPair("syntax_active_passive", "syntax", "The lawyer questioned the witness during the trial.", "The witness was questioned by the lawyer during the trial.", "active-passive"),
    ContrastPair("syntax_active_passive", "syntax", "The teacher praised the student after class.", "The student was praised by the teacher after class.", "active-passive"),
    ContrastPair("syntax_dative", "syntax", "Maya gave the student the book after lunch.", "Maya gave the book to the student after lunch.", "double-object vs prepositional dative"),
    ContrastPair("syntax_dative", "syntax", "Noah sent the manager the report this morning.", "Noah sent the report to the manager this morning.", "double-object vs prepositional dative"),
    ContrastPair("syntax_dative", "syntax", "Ava handed the nurse the chart before rounds.", "Ava handed the chart to the nurse before rounds.", "double-object vs prepositional dative"),
    ContrastPair("syntax_cleft_topicalization", "syntax", "Lena fixed the printer yesterday.", "It was Lena who fixed the printer yesterday.", "cleft"),
    ContrastPair("syntax_cleft_topicalization", "syntax", "The committee approved the budget after lunch.", "After lunch, the committee approved the budget.", "temporal topicalization"),
    ContrastPair("syntax_cleft_topicalization", "syntax", "The analyst reviewed the forecast in the morning.", "In the morning, the analyst reviewed the forecast.", "PP topicalization"),
    ContrastPair("syntax_relative_clause", "syntax", "The scientist who praised the artist smiled.", "The artist that the scientist praised smiled.", "subject/object relative alternation"),
    ContrastPair("syntax_relative_clause", "syntax", "The engineer who advised the intern arrived early.", "The intern that the engineer advised arrived early.", "subject/object relative alternation"),
    ContrastPair("syntax_relative_clause", "syntax", "The author who thanked the editor waved.", "The editor that the author thanked waved.", "subject/object relative alternation"),
    # Semantics-changing, syntax-preserving
    ContrastPair("sem_entity_substitution", "semantic", "Google hired Maria in Berlin last year.", "Microsoft hired Maria in Berlin last year.", "entity substitution"),
    ContrastPair("sem_entity_substitution", "semantic", "Amazon acquired the startup in Seattle on Monday.", "Meta acquired the startup in Seattle on Monday.", "entity substitution"),
    ContrastPair("sem_entity_substitution", "semantic", "Paris hosted the summit in June.", "Rome hosted the summit in June.", "entity substitution"),
    ContrastPair("sem_role_reversal", "semantic", "The dog chased the cat through the garden.", "The cat chased the dog through the garden.", "role reversal"),
    ContrastPair("sem_role_reversal", "semantic", "The prosecutor questioned the senator in public.", "The senator questioned the prosecutor in public.", "role reversal"),
    ContrastPair("sem_role_reversal", "semantic", "The nurse comforted the patient after surgery.", "The patient comforted the nurse after surgery.", "role reversal"),
    ContrastPair("sem_lexical_substitution", "semantic", "The doctor examined the patient in the clinic.", "The doctor comforted the patient in the clinic.", "verb substitution same frame"),
    ContrastPair("sem_lexical_substitution", "semantic", "The manager approved the proposal after lunch.", "The manager rejected the proposal after lunch.", "verb substitution same frame"),
    ContrastPair("sem_lexical_substitution", "semantic", "The reporter described the incident on air.", "The reporter ignored the incident on air.", "verb substitution same frame"),
    ContrastPair("sem_event_substitution", "semantic", "The storm destroyed the bridge near the coast.", "The protest surrounded the bridge near the coast.", "event substitution same skeleton"),
    ContrastPair("sem_event_substitution", "semantic", "The festival filled the plaza on Saturday.", "The fire damaged the plaza on Saturday.", "event substitution same skeleton"),
    ContrastPair("sem_event_substitution", "semantic", "The merger transformed the company in a year.", "The scandal damaged the company in a year.", "event substitution same skeleton"),
]


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Curated Stage B PCC contrast-set audit")
    p.add_argument("--checkpoint_path", required=True)
    p.add_argument("--model_name", type=str, default="EleutherAI/pythia-160m-deduped")
    p.add_argument("--layer_index", type=int, default=3)
    p.add_argument("--seed", type=int, default=42)
    p.add_argument("--device", type=str, default="auto", choices=["auto", "cpu", "cuda"])
    p.add_argument("--dtype", type=str, default="auto", choices=["auto", "fp16", "bf16", "fp32"])
    p.add_argument("--output_dir", required=True)
    p.add_argument("--git_commit_hash", type=str, default="")
    p.add_argument("--context_length", type=int, default=192)
    return p.parse_args()


def cosine_distance(a: np.ndarray, b: np.ndarray) -> float:
    denom = (np.linalg.norm(a) * np.linalg.norm(b)) + 1e-8
    return float(1.0 - float(np.dot(a, b) / denom))


def l2_distance(a: np.ndarray, b: np.ndarray) -> float:
    return float(np.linalg.norm(a - b))


def pooled_sentence_representations(
    sentences: list[str],
    model_lm: AutoModelForCausalLM,
    tokenizer: AutoTokenizer,
    msae,
    device: torch.device,
    layer_index: int,
    context_length: int,
) -> list[dict[str, np.ndarray]]:
    enc = tokenizer(sentences, return_tensors="pt", truncation=True, padding=True, max_length=context_length)
    input_ids = enc["input_ids"].to(device)
    attention_mask = enc["attention_mask"].to(device)
    with torch.no_grad():
        out = model_lm(
            input_ids=input_ids,
            attention_mask=attention_mask,
            output_hidden_states=True,
            use_cache=False,
        )
    hs_idx = resolve_hidden_state_index(layer_index, len(out.hidden_states))
    h = out.hidden_states[hs_idx].detach().float()

    reps: list[dict[str, np.ndarray]] = []
    for bi in range(h.shape[0]):
        valid = attention_mask[bi].bool()
        if valid.numel() > 0:
            valid = valid.clone()
            valid[0] = False
        token_h = h[bi, valid]
        with torch.no_grad():
            out_b = msae(token_h)
        raw = token_h.detach().cpu().numpy().astype(np.float32)
        pos = out_b["recon_pos"].detach().cpu().numpy().astype(np.float32)
        content = out_b["recon_content"].detach().cpu().numpy().astype(np.float32)
        resid = (raw - pos - content).astype(np.float32)
        pooled = {
            "raw": raw.mean(axis=0),
            "pos_priv": pos.mean(axis=0),
            "content_priv": content.mean(axis=0),
            "resid_additive": resid.mean(axis=0),
        }
        pooled["joint"] = np.concatenate([pooled["pos_priv"], pooled["content_priv"]], axis=0)
        reps.append(pooled)
    return reps


def main() -> None:
    args = parse_args()
    set_seed(args.seed)
    device = choose_device(args.device)
    dtype = choose_dtype(args.dtype)
    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    git_hash = resolve_git_commit_hash(args.git_commit_hash)

    tokenizer = AutoTokenizer.from_pretrained(args.model_name, use_fast=True)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token
    model_lm = AutoModelForCausalLM.from_pretrained(args.model_name, torch_dtype=dtype, low_cpu_mem_usage=True).to(device)
    model_lm.eval()
    model_lm.config.use_cache = False

    d_model = infer_d_model(model_lm, tokenizer, device, args.layer_index)
    msae, ckpt = load_msae_from_checkpoint(Path(args.checkpoint_path), device, d_model)

    sentences = []
    pair_meta = []
    for pair in CONTRASTS:
        pair_meta.append(pair)
        sentences.extend([pair.source, pair.target])

    t0 = time.time()
    pooled = pooled_sentence_representations(sentences, model_lm, tokenizer, msae, device, args.layer_index, args.context_length)
    extract_elapsed = time.time() - t0

    pair_rows: list[dict[str, Any]] = []
    family_buckets: dict[str, list[dict[str, float]]] = {}
    for i, pair in enumerate(pair_meta):
        a = pooled[2 * i]
        b = pooled[2 * i + 1]
        metrics = {}
        for rep in ["raw", "pos_priv", "content_priv", "joint", "resid_additive"]:
            metrics[f"cosdist_{rep}"] = cosine_distance(a[rep], b[rep])
            metrics[f"l2_{rep}"] = l2_distance(a[rep], b[rep])
        metrics["joint_minus_content"] = metrics["cosdist_joint"] - metrics["cosdist_content_priv"]
        metrics["content_minus_pos"] = metrics["cosdist_content_priv"] - metrics["cosdist_pos_priv"]
        metrics["resid_minus_content"] = metrics["cosdist_resid_additive"] - metrics["cosdist_content_priv"]
        row = {
            "family": pair.family,
            "contrast_type": pair.contrast_type,
            "note": pair.note,
            "source": pair.source,
            "target": pair.target,
            **metrics,
        }
        pair_rows.append(row)
        family_buckets.setdefault(pair.family, []).append(metrics)

    family_rows = []
    passed_families = []
    for family, rows in sorted(family_buckets.items()):
        contrast_type = "syntax" if family.startswith("syntax_") else "semantic"
        mean = lambda k: float(statistics.mean(r[k] for r in rows))
        med = lambda k: float(statistics.median(r[k] for r in rows))
        summary = {
            "family": family,
            "contrast_type": contrast_type,
            "n_pairs": len(rows),
            "mean_cosdist_raw": mean("cosdist_raw"),
            "mean_cosdist_pos_priv": mean("cosdist_pos_priv"),
            "mean_cosdist_content_priv": mean("cosdist_content_priv"),
            "mean_cosdist_joint": mean("cosdist_joint"),
            "mean_cosdist_resid_additive": mean("cosdist_resid_additive"),
            "mean_joint_minus_content": mean("joint_minus_content"),
            "median_joint_minus_content": med("joint_minus_content"),
            "mean_content_minus_pos": mean("content_minus_pos"),
            "median_content_minus_pos": med("content_minus_pos"),
            "mean_resid_minus_content": mean("resid_minus_content"),
        }
        if contrast_type == "syntax":
            family_pass = summary["mean_joint_minus_content"] > 0.0
        else:
            family_pass = summary["mean_content_minus_pos"] > 0.0
        summary["family_pass"] = family_pass
        if family_pass:
            passed_families.append(family)
        family_rows.append(summary)

    summary = {
        "stage": "pcc_stage_b_contrasts",
        "checkpoint_path": str(args.checkpoint_path),
        "model_name": args.model_name,
        "layer_index": int(args.layer_index),
        "seed": int(args.seed),
        "device": str(device),
        "dtype": str(dtype),
        "git_commit_hash": git_hash,
        "checkpoint_git_commit_hash": str(ckpt.get("args", {}).get("git_commit_hash", "")),
        "checkpoint_tokens_seen": int(ckpt.get("tokens_seen", 0)),
        "checkpoint_step": int(ckpt.get("step", 0)),
        "extract_elapsed_sec": float(extract_elapsed),
        "n_pairs": len(pair_rows),
        "pair_rows": pair_rows,
        "families": {row["family"]: row for row in family_rows},
        "passed_families": passed_families,
        "notes": {
            "interpretation": [
                "syntax families pass when joint pooled shift exceeds content pooled shift",
                "semantic families pass when content pooled shift exceeds position pooled shift",
                "this is a conservative Stage B contrast audit, not yet a causal ablation pack",
            ]
        },
    }

    with open(out_dir / "pcc_stage_b_contrasts_summary.json", "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)
    write_tsv(out_dir / "pcc_stage_b_contrasts_pairs.tsv", pair_rows)
    write_tsv(out_dir / "pcc_stage_b_contrasts_families.tsv", family_rows)
    print(json.dumps({
        "output_dir": str(out_dir),
        "summary": str(out_dir / "pcc_stage_b_contrasts_summary.json"),
        "pairs_tsv": str(out_dir / "pcc_stage_b_contrasts_pairs.tsv"),
        "families_tsv": str(out_dir / "pcc_stage_b_contrasts_families.tsv"),
        "passed_families": passed_families,
    }, indent=2))


if __name__ == "__main__":
    main()
