#!/usr/bin/env python3
"""Constructed complete-copy-circuit positive control (no training or natural text)."""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import secrets
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Mapping, Sequence

import numpy as np
import torch
import torch.nn.functional as F

ROOT = Path(__file__).resolve().parents[1]
DEFAULT = ROOT / "configs/constructed_copy_circuit_v1/run.json"
STAGES = ("development", "confirmation")
SCOPE = {
    "single_constructed_model": True,
    "general_natural_model_claim": False,
    "representation_methods_evaluated": False,
    "training_performed": False,
    "natural_prompt_assay": False,
    "method_benchmark_automatically_authorized": False,
}
ENDPOINTS = (
    "skyline_recovery", "circuit_recovery", "sham_specificity", "control_margin",
    "edge_necessity", "source_necessity", "necessity_advantage",
    "full_vocab_recovery", "collateral_error",
)


def canon(v: Any) -> bytes:
    return json.dumps(v, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def loadj(path: Path) -> Any:
    return json.loads(path.read_text())


def atomic_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = (json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n").encode()
    atomic_bytes(path,payload)


def atomic_bytes(path:Path,payload:bytes)->None:
    path.parent.mkdir(parents=True,exist_ok=True); tmp=path.with_name(f".{path.name}.tmp.{secrets.token_hex(16)}")
    fd=os.open(tmp,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
    with os.fdopen(fd, "w") as f:
        f.write(payload.decode()); f.flush(); os.fsync(f.fileno())
    try:
        os.link(tmp,path)
    finally:
        try: tmp.unlink()
        except FileNotFoundError: pass
    dfd=os.open(path.parent,os.O_RDONLY|os.O_DIRECTORY)
    try: os.fsync(dfd)
    finally: os.close(dfd)


def replace_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp." + secrets.token_hex(8))
    tmp.write_text(json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n")
    os.replace(tmp, path)
    dfd=os.open(path.parent,os.O_RDONLY|os.O_DIRECTORY)
    try: os.fsync(dfd)
    finally: os.close(dfd)


def write_jsonl(path: Path, rows: Sequence[Mapping[str, Any]]) -> None:
    payload="".join(json.dumps(row,sort_keys=True,separators=(",",":"))+"\n" for row in rows).encode()
    atomic_bytes(path,payload)


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


def rel(path: Path) -> str:
    return str(path.resolve().relative_to(ROOT.resolve()))


def config(path: Path = DEFAULT) -> dict[str, Any]:
    cfg = loadj(path)
    if cfg.get("schema_version") != "constructed_copy_circuit_v1_config":
        raise RuntimeError("bad config schema")
    if cfg.get("scope") != SCOPE or cfg["model"]["learned_parameters"] != 0:
        raise RuntimeError("scope drift")
    if cfg["model"]["kind"] != "analytic_two_stage_hard_attention_copy":
        raise RuntimeError("model kind drift")
    p = cfg["panels"]
    if p["rows_per_stage"] != p["blocks"] * p["rows_per_block"]:
        raise RuntimeError("panel shape mismatch")
    if cfg["bootstrap"]["draws"] != 2000 or tuple(ENDPOINTS) != ENDPOINTS:
        raise RuntimeError("registered estimator drift")
    return cfg


def graph_registry_payload(cfg: Mapping[str,Any]) -> dict[str,Any]:
    nodes=["token_state","predecessor_head","pair_key_state","pair_value_state","query_state","equality_mask","induction_edge","transport","readout_logits"]
    edges=[
        {"id":"token_to_predecessor","source":"token_state","target":"predecessor_head","kind":"fixed_previous_position_attention"},
        {"id":"predecessor_to_pair_key","source":"predecessor_head","target":"pair_key_state","kind":"value_position_slice"},
        {"id":"token_to_pair_value","source":"token_state","target":"pair_value_state","kind":"value_position_slice"},
        {"id":"token_to_query","source":"token_state","target":"query_state","kind":"final_position_slice"},
        {"id":"pair_key_to_mask","source":"pair_key_state","target":"equality_mask","kind":"identity_key"},
        {"id":"query_to_mask","source":"query_state","target":"equality_mask","kind":"identity_query"},
        {"id":"mask_to_induction_edge","source":"equality_mask","target":"induction_edge","kind":"hard_mask_softmax"},
        {"id":"induction_to_transport","source":"induction_edge","target":"transport","kind":"attention_weight"},
        {"id":"pair_value_to_transport","source":"pair_value_state","target":"transport","kind":"value_transport"},
        {"id":"transport_to_readout","source":"transport","target":"readout_logits","kind":"12_times_identity"},
    ]
    return {"schema_version":"constructed_copy_circuit_v1_graph_registry","status":"COMPLETE_BY_CONSTRUCTION","nodes":nodes,"edges":edges,"input_node":"token_state","output_node":"readout_logits","registered_output_bypasses":0,"fixed_sequence_length":18,"leading_sentinel_token_id":0,"padding_positions":[],"key_positions":[1,3,5,7,9,11,13,15],"value_positions":[2,4,6,8,10,12,14,16],"query_position":17,"learned_parameters":0,**SCOPE}


def validate_graph_registry(cfg: Mapping[str,Any], rec: Mapping[str,Any]) -> None:
    if rec != graph_registry_payload(cfg): raise RuntimeError("graph registry drift")
    parents:dict[str,list[str]]={n:[] for n in rec["nodes"]}
    for e in rec["edges"]: parents[e["target"]].append(e["source"])
    if parents["readout_logits"] != ["transport"] or sorted(parents["transport"]) != ["induction_edge","pair_value_state"]:
        raise RuntimeError("unregistered output path")
    seen=set(); stack=[rec["output_node"]]
    while stack:
        node=stack.pop()
        if node in seen: continue
        seen.add(node); stack.extend(parents[node])
    if set(rec["nodes"])-seen or rec["registered_output_bypasses"]!=0: raise RuntimeError("graph not fully reachable")


def create_candidate_attestations(config_path:Path)->None:
    cfg=config(config_path); verify_protocol(cfg); prepared=loadj(ROOT/cfg["runtime"]["prepared_root"]/"PREPARED.json")
    candidate=ROOT/cfg["runtime"]["candidate_root"]; candidate.mkdir(parents=True,exist_ok=True)
    graph=graph_registry_payload(cfg); atomic_json(candidate/"GRAPH_REGISTRY.json",graph); validate_graph_registry(cfg,graph)
    v=cfg["model"]["vocab_size"]; gain=cfg["model"]["readout_gain"]
    clean=float(gain); corrupt=float(-gain/(v-1)); effect=clean-corrupt; e=cfg["eligibility"]
    passed=clean>e["clean_margin_strict"] and corrupt<e["corrupt_margin_strict_upper"] and effect>e["effect_strict"]
    if not passed: raise RuntimeError("analytic eligibility construction")
    atomic_json(candidate/"ANALYTIC_ELIGIBILITY.json",{"schema_version":"constructed_copy_circuit_v1_analytic_eligibility","status":"PASS","derivation":"12_times_one_hot_readout","clean_margin":clean,"corrupt_margin":corrupt,"effect":effect,
        "development_rows_passing":prepared["development"]["rows"],"confirmation_rows_passing":prepared["confirmation"]["rows"],"prepared_attestation_sha256":sha(ROOT/cfg["runtime"]["prepared_root"]/"PREPARED.json"),**SCOPE})


def panel_rows(cfg: Mapping[str, Any], stage: str, *, smoke: bool = False) -> list[dict[str, Any]]:
    if stage not in STAGES and stage not in {"smoke","calibration"}: raise ValueError(stage)
    pc = cfg["panels"]
    if stage == "calibration":
        seed, n, blocks, key_range, value_range = 2026083198, 256, 8, (1,129), (129,513)
    elif smoke:
        seed, n, blocks, key_range, value_range = 2026083199, 16, 4, (1,129), (129,513)
    else:
        seed = pc[f"{stage}_seed"]; n = pc["rows_per_stage"]; blocks = pc["blocks"]
        key_range = tuple(pc[f"{stage}_key_range"]); value_range = tuple(pc[f"{stage}_value_range"])
    rng = np.random.default_rng(seed); bindings = cfg["model"]["bindings"]
    rows: list[dict[str, Any]] = []
    for i in range(n):
        keys = rng.choice(np.arange(*key_range), size=bindings, replace=False).astype(int)
        vals = rng.choice(np.arange(*value_range), size=11, replace=False).astype(int)
        target, contrast, sham, control_alt, control_base = map(int, vals[:5])
        j = int(rng.integers(0, bindings)); choices = [x for x in range(bindings) if x != j]
        k = int(choices[int(rng.integers(0, len(choices)))])
        base = [int(x) for x in vals[5:11]]
        clean = [0] * bindings
        di = iter(base)
        for q in range(bindings):
            if q == j: clean[q] = target
            elif q == k: clean[q] = control_base
            else: clean[q] = next(di)
        corrupt = clean.copy(); corrupt[j] = contrast
        sham_values = clean.copy(); sham_values[j] = sham
        control = corrupt.copy(); control[k] = control_alt
        role_tokens = list(keys) + clean + [contrast, sham, control_alt]
        if len(role_tokens) != len(set(role_tokens)):
            raise RuntimeError("token roles not disjoint")
        rows.append({
            "schema_version": "constructed_copy_circuit_v1_row", "stage": stage,
            "row_id": f"{stage}-{i:04d}", "row_index": i,
            "block": i % blocks, "keys": keys.tolist(), "query_pair_index": j,
            "control_pair_index": k, "query_token": int(keys[j]), "target": target,
            "contrast": contrast, "sham_token": sham, "control_alt": control_alt,
            "clean_values": clean, "corrupt_values": corrupt,
            "sham_values": sham_values, "control_values": control,
            "generated_integer_rows_only": True,
        })
    return rows


def validate_rows(cfg: Mapping[str, Any], rows: Sequence[Mapping[str, Any]], stage: str) -> None:
    n = 16 if stage == "smoke" else cfg["panels"]["rows_per_stage"]
    if len(rows) != n: raise RuntimeError(f"{stage} row count")
    b = cfg["model"]["bindings"]; v = cfg["model"]["vocab_size"]
    seen = set()
    for i,row in enumerate(rows):
        if row.get("stage") != stage or row.get("row_index") != i or row.get("row_id") in seen:
            raise RuntimeError("row identity/order")
        seen.add(row["row_id"])
        if row.get("generated_integer_rows_only") is not True: raise RuntimeError("non-generated row")
        if len(row["keys"]) != b or any(len(row[x]) != b for x in ("clean_values","corrupt_values","sham_values","control_values")):
            raise RuntimeError("binding shape")
        j,k=int(row["query_pair_index"]),int(row["control_pair_index"])
        if not (0 <= j < b and 0 <= k < b and j != k): raise RuntimeError("indices")
        if row["keys"][j] != row["query_token"]: raise RuntimeError("query mismatch")
        if row["clean_values"][j] != row["target"] or row["corrupt_values"][j] != row["contrast"] or row["sham_values"][j] != row["sham_token"]:
            raise RuntimeError("causal roles")
        for q in range(b):
            if q != j and not (row["clean_values"][q] == row["corrupt_values"][q] == row["sham_values"][q]):
                raise RuntimeError("noncausal condition drift")
            if q != k and row["control_values"][q] != row["corrupt_values"][q]: raise RuntimeError("control wrote wrong site")
        if row["control_values"][k] == row["corrupt_values"][k]: raise RuntimeError("zero control delta")
        flat = list(row["keys"])+list(row["clean_values"])+[row["contrast"],row["sham_token"],row["control_alt"]]
        if len(flat) != len(set(flat)) or min(flat)<0 or max(flat)>=v: raise RuntimeError("roles/range")


def prepare(config_path: Path) -> None:
    cfg=config(config_path); root=ROOT/cfg["runtime"]["prepared_root"]
    if root.exists() and any(root.iterdir()): raise RuntimeError("prepared root exists")
    root.mkdir(parents=True,exist_ok=True)
    panels={s:panel_rows(cfg,s) for s in STAGES}; smoke=panel_rows(cfg,"smoke",smoke=True); calibration_rows=panel_rows(cfg,"calibration")
    for s,rows in panels.items(): validate_rows(cfg,rows,s); write_jsonl(root/f"{s}.jsonl",rows)
    validate_rows(cfg,smoke,"smoke"); write_jsonl(root/"smoke_fixture.jsonl",smoke)
    validate_rows(cfg,calibration_rows,"calibration"); write_jsonl(root/"calibration_rows.jsonl",calibration_rows)
    dev_prompts={canon((r["keys"],r["clean_values"],r["query_token"])) for r in panels["development"]}
    con_prompts={canon((r["keys"],r["clean_values"],r["query_token"])) for r in panels["confirmation"]}
    if dev_prompts & con_prompts: raise RuntimeError("panel overlap")
    fixture={"schema_version":"constructed_copy_circuit_v1_calibration_fixture","scenarios":{
        "pass":"PASS", "degraded_recovery":"SCIENTIFIC_STOP", "nonspecific_sham":"SCIENTIFIC_STOP",
        "potent_control":"SCIENTIFIC_STOP", "high_collateral":"SCIENTIFIC_STOP",
        "insufficient_support":"SCIENTIFIC_STOP", "nonfinite":"TECHNICAL_INVALID_STOP",
        "invalid_denominator":"SCIENTIFIC_STOP", "patch_norm_mismatch":"TECHNICAL_INVALID_STOP",
        "ablation_norm_mismatch":"TECHNICAL_INVALID_STOP"},
        "comparator_cases":["below","equal","above"]}
    atomic_json(root/"calibration_fixture.json",fixture)
    atomic_json(root/"PREPARED.json",{
        "schema_version":"constructed_copy_circuit_v1_prepared","status":"PASS",
        "development":{"rows":len(panels["development"]),"sha256":sha(root/"development.jsonl")},
        "confirmation":{"rows":len(panels["confirmation"]),"sha256":sha(root/"confirmation.jsonl")},
        "smoke":{"rows":len(smoke),"sha256":sha(root/"smoke_fixture.jsonl")},
        "calibration_rows":{"rows":len(calibration_rows),"sha256":sha(root/"calibration_rows.jsonl")},
        "calibration_fixture_sha256":sha(root/"calibration_fixture.json"),"prompt_overlap":0,
        **SCOPE})


def verify_prepared(cfg: Mapping[str, Any], *, include_development:bool, include_confirmation: bool) -> dict[str,Any]:
    root=ROOT/cfg["runtime"]["prepared_root"]; rec=loadj(root/"PREPARED.json")
    for stage in (("development",) if include_development else ()):
        p=root/f"{stage}.jsonl"; rows=read_jsonl(p); validate_rows(cfg,rows,stage)
        if rec[stage]!={"rows":len(rows),"sha256":sha(p)}: raise RuntimeError("prepared drift")
    if include_confirmation:
        p=root/"confirmation.jsonl"; rows=read_jsonl(p); validate_rows(cfg,rows,"confirmation")
        if rec["confirmation"]!={"rows":len(rows),"sha256":sha(p)}: raise RuntimeError("confirmation drift")
    smoke=root/"smoke_fixture.jsonl"; validate_rows(cfg,read_jsonl(smoke),"smoke")
    calibration_rows=root/"calibration_rows.jsonl"; validate_rows(cfg,read_jsonl(calibration_rows),"calibration")
    if rec["smoke"]["sha256"]!=sha(smoke) or rec["calibration_rows"]["sha256"]!=sha(calibration_rows) or rec["calibration_fixture_sha256"]!=sha(root/"calibration_fixture.json"):
        raise RuntimeError("fixture drift")
    return rec


def verify_v2_preservation(cfg: Mapping[str, Any]) -> dict[str,Any]:
    p=ROOT/cfg["runtime"]["v2_preservation"]; rec=loadj(p); forbidden=rec["forbidden_confirmation_path"]
    if rec["sealed_confirmation_payload_directly_accessed_by_builder"] is not False: raise RuntimeError("v2 sealed access")
    if any(x["path"]==forbidden for x in rec["files"]): raise RuntimeError("sealed payload in direct inventory")
    if rec["confirmation_blocked"]["payload_touched"] or rec["confirmation_blocked"]["registered_code_path_accessed_confirmation_payload"]:
        raise RuntimeError("v2 confirmation not preserved")
    freeze_path=ROOT/rec["freeze"]["path"]
    if not freeze_path.is_file() or sha(freeze_path)!=rec["freeze"]["sha256"]: raise RuntimeError("v2 freeze drift")
    freeze_rec=loadj(freeze_path)
    if freeze_rec.get("candidate_inventory_sha256")!=rec["freeze"]["candidate_inventory_sha256"]: raise RuntimeError("v2 freeze inventory drift")
    if freeze_rec.get("confirmation_payload")!=rec["sealed_confirmation_payload_from_freeze_only"]: raise RuntimeError("v2 sealed metadata drift")
    v2_cfg_path=ROOT/"configs/canonical_induction_two_tier_v2/run.json"; v2_cfg=loadj(v2_cfg_path)
    required={x["path"] for x in freeze_rec["candidate_inventory"] if x["path"]!=forbidden}
    required.update({rec["freeze"]["path"],"reports/adversarial/canonical_induction_two_tier_v2_frozen_review.md",
        "reports/provenance/canonical_induction_two_tier_v2_candidate/FROZEN_REVIEW_BINDING.json","reports/claim_review/canonical_induction_two_tier_v2_postresult.md"})
    for base in (ROOT/v2_cfg["runtime"]["output_root"],ROOT/v2_cfg["runtime"]["provenance_root"]):
        required.update(rel(x) for x in base.rglob("*") if x.is_file())
    observed={x["path"] for x in rec["files"]}
    if observed!=required or len(observed)!=len(rec["files"]): raise RuntimeError("v2 preservation required-set drift")
    for item in rec["files"]:
        q=ROOT/item["path"]
        if not q.is_file() or q.stat().st_size!=item["bytes"] or sha(q)!=item["sha256"]:
            raise RuntimeError(f"v2 preservation drift {item['path']}")
    if hashlib.sha256(canon(rec["files"])).hexdigest()!=rec["files_sha256"]: raise RuntimeError("v2 list drift")
    for key in ("thresholds_changed","confirmation_opened","development_heads_added","representation_methods_evaluated","training_performed"):
        if rec[key] is not False: raise RuntimeError(f"v2 scope drift {key}")
    return rec


def protocol_lock(config_path: Path) -> None:
    cfg=config(config_path); verify_v2_preservation(cfg); verify_prepared(cfg,include_development=True,include_confirmation=True)
    root=ROOT/cfg["runtime"]["prepared_root"]
    paths=[Path(config_path),ROOT/"PLAN_CONSTRUCTED_COPY_CIRCUIT_V1.md",root/"development.jsonl",root/"confirmation.jsonl",root/"smoke_fixture.jsonl",root/"calibration_rows.jsonl",root/"calibration_fixture.json",root/"PREPARED.json"]
    items=[{"path":rel(p),"bytes":p.stat().st_size,"sha256":sha(p)} for p in paths]
    atomic_json(ROOT/cfg["runtime"]["protocol_lock"],{
        "schema_version":"constructed_copy_circuit_v1_protocol_lock","status":"LOCKED_BEFORE_MODEL_SMOKE",
        "items":items,"items_sha256":hashlib.sha256(canon(items)).hexdigest(),"equations":"PLAN_CONSTRUCTED_COPY_CIRCUIT_V1.md",
        "confirmation_payload":next(x for x in items if x["path"].endswith("confirmation.jsonl")),**SCOPE})


def verify_protocol(cfg: Mapping[str, Any], *, include_development:bool=False, include_confirmation: bool=False) -> dict[str,Any]:
    rec=loadj(ROOT/cfg["runtime"]["protocol_lock"])
    if rec["status"]!="LOCKED_BEFORE_MODEL_SMOKE" or rec["natural_prompt_assay"]: raise RuntimeError("protocol lock")
    if hashlib.sha256(canon(rec["items"])).hexdigest()!=rec["items_sha256"]: raise RuntimeError("protocol digest")
    for item in rec["items"]:
        if item["path"].endswith("development.jsonl") and not include_development: continue
        if item["path"].endswith("confirmation.jsonl") and not include_confirmation: continue
        p=ROOT/item["path"]
        if not p.is_file() or p.stat().st_size!=item["bytes"] or sha(p)!=item["sha256"]: raise RuntimeError(f"protocol drift {item['path']}")
    return rec


def rows_to_tensors(rows: Sequence[Mapping[str,Any]], device: torch.device, vocab: int) -> dict[str,torch.Tensor]:
    def t(name:str): return torch.tensor([r[name] for r in rows],dtype=torch.long,device=device)
    return {"keys":t("keys"),"clean":t("clean_values"),"corrupt":t("corrupt_values"),"sham":t("sham_values"),"control":t("control_values"),
            "j":t("query_pair_index"),"k":t("control_pair_index"),"query":t("query_token"),"target":t("target"),"contrast":t("contrast"),
            "vocab":torch.tensor(vocab,device=device)}


def torch_forward(rows: Sequence[Mapping[str,Any]], cfg: Mapping[str,Any], device: torch.device) -> dict[str,np.ndarray]:
    vocab=int(cfg["model"]["vocab_size"]); gain=float(cfg["model"]["readout_gain"]); x=rows_to_tensors(rows,device,vocab)
    n=len(rows); idx=torch.arange(n,device=device); key_pos=torch.arange(1,16,2,device=device); value_pos=torch.arange(2,17,2,device=device); query_pos=17
    predecessor_edges=torch.zeros((18,18),dtype=torch.float32,device=device); predecessor_edges[value_pos,key_pos]=1
    def sequence(values:torch.Tensor)->tuple[torch.Tensor,torch.Tensor,torch.Tensor,torch.Tensor]:
        ids=torch.zeros((n,18),dtype=torch.long,device=device); ids[:,key_pos]=x["keys"]; ids[:,value_pos]=values; ids[:,query_pos]=x["query"]
        states=F.one_hot(ids,num_classes=vocab).to(torch.float32)
        predecessor=torch.einsum("st,ntv->nsv",predecessor_edges,states)
        return ids,predecessor,predecessor[:,value_pos],states[:,value_pos]
    built={name:sequence(x[name]) for name in ("clean","corrupt","sham","control")}
    seq={name:built[name][0] for name in built}; pred={name:built[name][1] for name in built}
    keys=built["clean"][2]; vals={name:built[name][3] for name in built}
    if not all(torch.equal(built[name][2],keys) for name in built): raise RuntimeError("predecessor key drift")
    def route(pair_keys:torch.Tensor,query_ids:torch.Tensor)->tuple[torch.Tensor,torch.Tensor]:
        query=F.one_hot(query_ids,num_classes=vocab).to(torch.float32); match=(pair_keys*query[:,None,:]).sum(-1)==1
        if not torch.all(match.sum(-1)==1): raise RuntimeError("unique route violation")
        scores=torch.where(match,torch.zeros_like(match,dtype=torch.float32),torch.full_like(match,float("-inf"),dtype=torch.float32))
        weights=torch.softmax(scores,dim=-1)
        if not torch.equal(weights,match.to(torch.float32)): raise RuntimeError("attention not exact one-hot")
        return scores,weights
    routes={name:route(built[name][2],seq[name][:,query_pos]) for name in built}
    pre,attn=routes["clean"]
    if not torch.equal(torch.argmax(attn,dim=1),x["j"]): raise RuntimeError("registered matched index drift")
    # Recompute routing after every pair-value intervention. Key channels are unchanged, so these
    # registered routes must be identical; exporting each one proves the promised execution order.
    pre_circuit,attn_circuit=route(built["corrupt"][2],seq["corrupt"][:,query_pos])
    pre_sham_patch,attn_sham_patch=route(built["corrupt"][2],seq["corrupt"][:,query_pos])
    pre_control_patch,attn_control_patch=route(built["corrupt"][2],seq["corrupt"][:,query_pos])
    pre_source_ablate,attn_source_ablate=route(built["clean"][2],seq["clean"][:,query_pos])
    pre_control_ablate,attn_control_ablate=route(built["clean"][2],seq["clean"][:,query_pos])
    def transport(v:torch.Tensor,a:torch.Tensor): return torch.einsum("nb,nbv->nv",a,v)
    def logits(v:torch.Tensor,a:torch.Tensor): return gain*transport(v,a)
    circuit=vals["corrupt"].clone(); circuit[idx,x["j"]]=vals["clean"][idx,x["j"]]
    sham_patch=vals["corrupt"].clone(); sham_patch[idx,x["j"]]=vals["sham"][idx,x["j"]]
    control_patch=vals["corrupt"].clone(); control_patch[idx,x["k"]]=vals["control"][idx,x["k"]]
    edge_attn=attn.clone(); edge_attn[idx,x["j"]]=0
    source=vals["clean"].clone(); source[idx,x["j"]]=0
    control_ablate=vals["clean"].clone(); control_ablate[idx,x["k"]]=0
    causal_delta=vals["clean"][idx,x["j"]]-vals["corrupt"][idx,x["j"]]
    control_delta=vals["control"][idx,x["k"]]-vals["corrupt"][idx,x["k"]]
    patch_ratio=torch.linalg.vector_norm(control_delta,dim=-1)/torch.linalg.vector_norm(causal_delta,dim=-1)
    ablation_ratio=torch.linalg.vector_norm(vals["clean"][idx,x["k"]],dim=-1)/torch.linalg.vector_norm(vals["clean"][idx,x["j"]],dim=-1)
    out={
        "predecessor_edges":predecessor_edges,"sequence_clean_ids":seq["clean"],"sequence_corrupt_ids":seq["corrupt"],"sequence_sham_ids":seq["sham"],"sequence_control_ids":seq["control"],
        "predecessor_state_clean":pred["clean"],"predecessor_state_corrupt":pred["corrupt"],"predecessor_state_sham":pred["sham"],"predecessor_state_control":pred["control"],
        "pair_keys":keys,"pair_values_clean":vals["clean"],"pair_values_corrupt":vals["corrupt"],
        "pair_values_sham":vals["sham"],"pair_values_control":vals["control"],"pre_scores":pre,"attention":attn,
        "pre_scores_circuit":pre_circuit,"attention_circuit":attn_circuit,"pre_scores_sham_patch":pre_sham_patch,"attention_sham_patch":attn_sham_patch,
        "pre_scores_control_patch":pre_control_patch,"attention_control_patch":attn_control_patch,"pre_scores_source_ablate":pre_source_ablate,"attention_source_ablate":attn_source_ablate,
        "pre_scores_control_ablate":pre_control_ablate,"attention_control_ablate":attn_control_ablate,
        "transport_clean":transport(vals["clean"],routes["clean"][1]),"transport_corrupt":transport(vals["corrupt"],routes["corrupt"][1]),
        "transport_sham":transport(vals["sham"],routes["sham"][1]),"transport_circuit_clean":transport(circuit,attn_circuit),
        "transport_circuit_sham":transport(sham_patch,attn_sham_patch),"transport_control":transport(control_patch,attn_control_patch),
        "transport_edge_ablate":transport(vals["clean"],edge_attn),"transport_source_ablate":transport(source,attn_source_ablate),
        "transport_control_ablate":transport(control_ablate,attn_control_ablate),
        "logits_clean":logits(vals["clean"],routes["clean"][1]),"logits_corrupt":logits(vals["corrupt"],routes["corrupt"][1]),"logits_sham":logits(vals["sham"],routes["sham"][1]),
        "logits_full_clean":logits(vals["clean"],routes["clean"][1]).clone(),"logits_full_sham":logits(vals["sham"],routes["sham"][1]).clone(),
        "logits_circuit_clean":logits(circuit,attn_circuit),"logits_circuit_sham":logits(sham_patch,attn_sham_patch),"logits_control":logits(control_patch,attn_control_patch),
        "logits_edge_ablate":logits(vals["clean"],edge_attn),"logits_source_ablate":logits(source,attn_source_ablate),
        "logits_control_ablate":logits(control_ablate,attn_control_ablate),"patch_norm_ratio":patch_ratio,
        "ablation_norm_ratio":ablation_ratio,"matched_index":x["j"],"control_index":x["k"]}
    if device.type=="cuda": torch.cuda.synchronize(device)
    return {k:v.detach().cpu().numpy() for k,v in out.items()}


def numpy_oracle(rows: Sequence[Mapping[str,Any]], cfg: Mapping[str,Any]) -> dict[str,np.ndarray]:
    n=len(rows); b=cfg["model"]["bindings"]; v=cfg["model"]["vocab_size"]; gain=np.float32(cfg["model"]["readout_gain"])
    key_pos=np.arange(1,16,2); value_pos=np.arange(2,17,2); predecessor_edges=np.zeros((18,18),np.float32); predecessor_edges[value_pos,key_pos]=1
    sequences={q:np.zeros((n,18),np.int64) for q in ("clean","corrupt","sham","control")}
    predecessor={q:np.zeros((n,18,v),np.float32) for q in sequences}; values={q:np.zeros((n,b,v),np.float32) for q in sequences}
    j=np.array([r["query_pair_index"] for r in rows],np.int64); k=np.array([r["control_pair_index"] for r in rows],np.int64)
    for i,r in enumerate(rows):
        for q,name in (("clean","clean_values"),("corrupt","corrupt_values"),("sham","sham_values"),("control","control_values")):
            sequences[q][i,key_pos]=r["keys"]; sequences[q][i,value_pos]=r[name]; sequences[q][i,17]=r["query_token"]
            predecessor[q][i,value_pos,r["keys"]]=1
            values[q][i,np.arange(b),r[name]]=1
    keys=predecessor["clean"][:,value_pos]
    def route(pair_keys:np.ndarray,query_ids:np.ndarray)->tuple[np.ndarray,np.ndarray]:
        query=np.eye(v,dtype=np.float32)[query_ids]; match=np.sum(pair_keys*query[:,None,:],axis=-1)==1
        if not np.all(match.sum(axis=-1)==1): raise RuntimeError("unique route violation")
        scores=np.where(match,np.float32(0),np.float32(-np.inf)).astype(np.float32)
        weights=match.astype(np.float32)
        return scores,weights
    routes={name:route(predecessor[name][:,value_pos],sequences[name][:,17]) for name in sequences}
    pre,attn=routes["clean"]
    pre_circuit,attn_circuit=route(predecessor["corrupt"][:,value_pos],sequences["corrupt"][:,17])
    pre_sham_patch,attn_sham_patch=route(predecessor["corrupt"][:,value_pos],sequences["corrupt"][:,17])
    pre_control_patch,attn_control_patch=route(predecessor["corrupt"][:,value_pos],sequences["corrupt"][:,17])
    pre_source_ablate,attn_source_ablate=route(predecessor["clean"][:,value_pos],sequences["clean"][:,17])
    pre_control_ablate,attn_control_ablate=route(predecessor["clean"][:,value_pos],sequences["clean"][:,17])
    if not np.array_equal(np.argmax(attn,axis=1),j): raise RuntimeError("registered matched index drift")
    def trans(vals,a): return np.sum(a[:,:,None]*vals,axis=1,dtype=np.float32)
    def logits(vals,a): return gain*trans(vals,a)
    circuit=values["corrupt"].copy(); circuit[np.arange(n),j]=values["clean"][np.arange(n),j]
    sham_patch=values["corrupt"].copy(); sham_patch[np.arange(n),j]=values["sham"][np.arange(n),j]
    control_patch=values["corrupt"].copy(); control_patch[np.arange(n),k]=values["control"][np.arange(n),k]
    edge=attn.copy(); edge[np.arange(n),j]=0
    source=values["clean"].copy(); source[np.arange(n),j]=0
    control_ablate=values["clean"].copy(); control_ablate[np.arange(n),k]=0
    causal_delta=values["clean"][np.arange(n),j]-values["corrupt"][np.arange(n),j]
    control_delta=values["control"][np.arange(n),k]-values["corrupt"][np.arange(n),k]
    out={"predecessor_edges":predecessor_edges,"sequence_clean_ids":sequences["clean"],"sequence_corrupt_ids":sequences["corrupt"],"sequence_sham_ids":sequences["sham"],"sequence_control_ids":sequences["control"],
         "predecessor_state_clean":predecessor["clean"],"predecessor_state_corrupt":predecessor["corrupt"],"predecessor_state_sham":predecessor["sham"],"predecessor_state_control":predecessor["control"],
         "pair_keys":keys,"pair_values_clean":values["clean"],"pair_values_corrupt":values["corrupt"],"pair_values_sham":values["sham"],"pair_values_control":values["control"],"pre_scores":pre,"attention":attn,
         "pre_scores_circuit":pre_circuit,"attention_circuit":attn_circuit,"pre_scores_sham_patch":pre_sham_patch,"attention_sham_patch":attn_sham_patch,
         "pre_scores_control_patch":pre_control_patch,"attention_control_patch":attn_control_patch,"pre_scores_source_ablate":pre_source_ablate,"attention_source_ablate":attn_source_ablate,
         "pre_scores_control_ablate":pre_control_ablate,"attention_control_ablate":attn_control_ablate,
         "transport_clean":trans(values["clean"],routes["clean"][1]),"transport_corrupt":trans(values["corrupt"],routes["corrupt"][1]),"transport_sham":trans(values["sham"],routes["sham"][1]),"transport_circuit_clean":trans(circuit,attn_circuit),"transport_circuit_sham":trans(sham_patch,attn_sham_patch),"transport_control":trans(control_patch,attn_control_patch),"transport_edge_ablate":trans(values["clean"],edge),"transport_source_ablate":trans(source,attn_source_ablate),"transport_control_ablate":trans(control_ablate,attn_control_ablate),
         "logits_clean":logits(values["clean"],routes["clean"][1]),"logits_corrupt":logits(values["corrupt"],routes["corrupt"][1]),"logits_sham":logits(values["sham"],routes["sham"][1]),"logits_full_clean":logits(values["clean"],routes["clean"][1]).copy(),"logits_full_sham":logits(values["sham"],routes["sham"][1]).copy(),"logits_circuit_clean":logits(circuit,attn_circuit),"logits_circuit_sham":logits(sham_patch,attn_sham_patch),"logits_control":logits(control_patch,attn_control_patch),"logits_edge_ablate":logits(values["clean"],edge),"logits_source_ablate":logits(source,attn_source_ablate),"logits_control_ablate":logits(control_ablate,attn_control_ablate),
         "patch_norm_ratio":np.linalg.norm(control_delta,axis=-1)/np.linalg.norm(causal_delta,axis=-1),"ablation_norm_ratio":np.linalg.norm(values["clean"][np.arange(n),k],axis=-1)/np.linalg.norm(values["clean"][np.arange(n),j],axis=-1),"matched_index":j,"control_index":k}
    return out


def exact_compare(a: Mapping[str,np.ndarray], b: Mapping[str,np.ndarray]) -> dict[str,Any]:
    if set(a)!=set(b): raise RuntimeError("array registry mismatch")
    fields={}; ok=True
    for k in sorted(a):
        same=a[k].dtype==b[k].dtype and a[k].shape==b[k].shape and np.array_equal(a[k],b[k],equal_nan=False)
        fields[k]={"equal":bool(same),"shape":list(a[k].shape),"dtype":str(a[k].dtype)}; ok &= bool(same)
    if not ok: raise RuntimeError("exact array mismatch")
    return {"pass":True,"fields":fields}


def margin(z: np.ndarray, targets: np.ndarray) -> np.ndarray:
    n,v=z.shape; return (v*z[np.arange(n),targets]-z.sum(axis=1,dtype=np.float64))/(v-1)


def endpoint_seed(base:int,stage:str,name:str)->int:
    d=hashlib.sha256(f"{base}|{stage}|{name}".encode()).digest(); return int.from_bytes(d[:4],"little")


def interval(values:np.ndarray,blocks:np.ndarray,cfg:Mapping[str,Any],stage:str,name:str)->dict[str,Any]:
    uniq=np.arange(cfg["panels"]["blocks"]); block_vals=[values[blocks==b] for b in uniq]
    if any(len(x)==0 for x in block_vals): raise RuntimeError("empty endpoint block")
    point=float(np.mean([x.mean() for x in block_vals])); rng=np.random.default_rng(endpoint_seed(cfg["seed"],stage,name)); draws=[]
    for _ in range(cfg["bootstrap"]["draws"]):
        sampled=rng.choice(uniq,size=len(uniq),replace=True); means=[]
        for b in sampled:
            x=block_vals[int(b)]; means.append(float(rng.choice(x,size=len(x),replace=True).mean()))
        draws.append(float(np.mean(means)))
    lo,hi=np.quantile(np.asarray(draws),cfg["bootstrap"]["quantiles"],method=cfg["bootstrap"]["method"])
    return {"point":point,"lower":float(lo),"upper":float(hi),"draws":len(draws),"weighting":cfg["bootstrap"]["weighting"]}


def gate_pass(name:str, rec:Mapping[str,float], cfg:Mapping[str,Any])->bool:
    gate=cfg["gates"][name]
    if "point_min" in gate: return bool(rec["point"]>=gate["point_min"] and rec["lower"]>gate["lower_strict_min"])
    return bool(rec["point"]<=gate["point_max"] and rec["upper"]<gate["upper_strict_max"])


def row_gate_pass(name:str, values:np.ndarray, cfg:Mapping[str,Any])->bool:
    gate=cfg["gates"][name]
    return bool(np.all((values>=gate["row_min"])&(values<=gate["row_max"])))


def evaluate(arr: Mapping[str,np.ndarray], rows:Sequence[Mapping[str,Any]],cfg:Mapping[str,Any],stage:str)->tuple[list[dict[str,Any]],dict[str,Any],dict[str,Any]]:
    graph=loadj(ROOT/cfg["runtime"]["candidate_root"]/"GRAPH_REGISTRY.json"); validate_graph_registry(cfg,graph)
    # Deliberate -inf mask sentinels are validated separately; all downstream arrays must be finite.
    pre=arr["pre_scores"]; att=arr["attention"]; j=arr["matched_index"].astype(int); k=arr["control_index"].astype(int); n=len(rows); b=cfg["model"]["bindings"]
    expected_pre=np.full((n,b),-np.inf,np.float32); expected_pre[np.arange(n),j]=0
    if not np.array_equal(pre,expected_pre) or not np.all(np.isfinite(pre[np.arange(n),j])): raise FloatingPointError("mask sentinel contract")
    for name,x in arr.items():
        if name.startswith("pre_scores"): continue
        if not np.all(np.isfinite(x)): raise FloatingPointError(f"nonfinite {name}")
    expected_att=np.zeros((n,b),np.float32); expected_att[np.arange(n),j]=1
    if not np.array_equal(att,expected_att) or np.any(j==k): raise RuntimeError("route/control contract")
    for suffix in ("circuit","sham_patch","control_patch","source_ablate","control_ablate"):
        if not np.array_equal(arr[f"pre_scores_{suffix}"],expected_pre) or not np.array_equal(arr[f"attention_{suffix}"],expected_att):
            raise RuntimeError(f"recomputed route drift {suffix}")
    if not np.array_equal(arr["logits_full_clean"],arr["logits_clean"]) or not np.array_equal(arr["logits_full_sham"],arr["logits_sham"]): raise RuntimeError("full-output donor identity")
    norm=cfg["gates"]; pr=arr["patch_norm_ratio"]; ar=arr["ablation_norm_ratio"]
    patch_ok=row_gate_pass("patch_norm_ratio",pr,cfg); ablate_ok=row_gate_pass("ablation_norm_ratio",ar,cfg)
    if not patch_ok or not ablate_ok: raise RuntimeError("norm matching")
    targets=np.array([r["target"] for r in rows]); contrast=np.array([r["contrast"] for r in rows]); blocks=np.array([r["block"] for r in rows])
    names={"cl":"logits_clean","co":"logits_corrupt","F":"logits_full_clean","C":"logits_circuit_clean","H":"logits_circuit_sham","K":"logits_control","E":"logits_edge_ablate","S":"logits_source_ablate","A":"logits_control_ablate"}
    ms={q:margin(arr[name],targets) for q,name in names.items()}; D=ms["F"]-ms["co"]
    ccl=arr["logits_clean"]-arr["logits_clean"].mean(axis=1,keepdims=True,dtype=np.float64)
    cco=arr["logits_corrupt"]-arr["logits_corrupt"].mean(axis=1,keepdims=True,dtype=np.float64)
    cc=arr["logits_circuit_clean"]-arr["logits_circuit_clean"].mean(axis=1,keepdims=True,dtype=np.float64)
    scale=np.sqrt(np.mean((ccl-cco)**2,axis=1))
    e=cfg["eligibility"]
    positive_d=D>e["denominator_strict"]; positive_scale=scale>e["centered_scale_strict"]
    safe_d=np.where(positive_d,D,1.0); safe_scale=np.where(positive_scale,scale,1.0)
    eligible=(ms["cl"]>e["clean_margin_strict"])&(ms["co"]<e["corrupt_margin_strict_upper"])&((ms["cl"]-ms["co"])>e["effect_strict"])&positive_d&positive_scale
    # All derived values are computed before cohort selection; nonfinite is technical invalid.
    metrics={"skyline_recovery":(ms["F"]-ms["co"])/safe_d,"circuit_recovery":(ms["C"]-ms["co"])/safe_d}
    sham=(ms["H"]-ms["co"])/safe_d; control=(ms["K"]-ms["co"])/safe_d
    metrics.update({"sham_specificity":metrics["circuit_recovery"]-sham,"control_margin":metrics["circuit_recovery"]-control,
                    "edge_necessity":(ms["cl"]-ms["E"])/safe_d,"source_necessity":(ms["cl"]-ms["S"])/safe_d})
    control_nec=(ms["cl"]-ms["A"])/safe_d; metrics["necessity_advantage"]=metrics["source_necessity"]-control_nec
    metrics["full_vocab_recovery"]=1-np.sqrt(np.mean((cc-ccl)**2,axis=1))/safe_scale
    collateral=[]
    for i in range(n):
        mask=np.ones(arr["logits_clean"].shape[1],dtype=bool); mask[targets[i]]=False; mask[contrast[i]]=False
        collateral.append(float(np.sqrt(np.mean((cc[i,mask]-cco[i,mask])**2))/safe_scale[i]))
    metrics["collateral_error"]=np.asarray(collateral)
    if any(not np.all(np.isfinite(x)) for x in metrics.values()): raise FloatingPointError("nonfinite derived")
    G=eligible.copy(); per={str(q):int(np.sum(G&(blocks==q))) for q in range(cfg["panels"]["blocks"])}
    support=bool(int(G.sum())>=e["minimum_total"] and all(x>=e["minimum_per_block"] for x in per.values()))
    summaries={name:interval(vals[G],blocks[G],cfg,stage,name) for name,vals in metrics.items()} if support else {}
    decisions={}
    if support:
        for name,rec in summaries.items(): decisions[name]=gate_pass(name,rec,cfg)
    all_pass=bool(support and all(decisions.values()))
    row_records=[]
    for i,r in enumerate(rows):
        row_records.append({"row_id":r["row_id"],"row_index":i,"block":int(blocks[i]),"in_common_cohort":bool(G[i]),
            "clean_margin":float(ms["cl"][i]),"corrupt_margin":float(ms["co"][i]),"denominator":float(D[i]),
            **{name:float(vals[i]) for name,vals in metrics.items()},"sham_recovery":float(sham[i]),"control_recovery":float(control[i]),
            "control_source_necessity":float(control_nec[i]),"patch_norm_ratio":float(pr[i]),"ablation_norm_ratio":float(ar[i])})
    summary={"schema_version":"constructed_copy_circuit_v1_summary","stage":stage,"technical_valid":True,"support_pass":support,
             "common_cohort_total":int(G.sum()),"common_cohort_per_block":per,"metrics":summaries,"gate_decisions":decisions,"all_gates_pass":all_pass,
             "status":f"{stage.upper()}_PASS" if all_pass else f"{stage.upper()}_GROUND_TRUTH_STOP",**SCOPE}
    qa={"schema_version":"constructed_copy_circuit_v1_qa","pre_softmax_mask_contract":True,"attention_exact_one_hot":True,"all_intervention_routes_recomputed":True,
        "full_clean_donor_bitwise":True,"full_sham_donor_bitwise":True,"patch_norm_all_rows":patch_ok,"ablation_norm_all_rows":ablate_ok,
        "learned_parameters":0,"registered_output_bypasses":graph["registered_output_bypasses"],"graph_registry_sha256":sha(ROOT/cfg["runtime"]["candidate_root"]/"GRAPH_REGISTRY.json"),"post_softmax_and_outputs_finite":True,**SCOPE}
    return row_records,summary,qa


def calibration(config_path:Path)->None:
    cfg=config(config_path); verify_protocol(cfg); root=ROOT/cfg["runtime"]["prepared_root"]
    rows=read_jsonl(root/"calibration_rows.jsonl"); base=numpy_oracle(rows,cfg); expected=loadj(root/"calibration_fixture.json")["scenarios"]
    outcomes={}
    def classify(name:str,mutate=None,short=False):
        arr={k:v.copy() for k,v in base.items()}; rr=list(rows)
        try:
            if mutate: mutate(arr)
            if short:
                rr=rr[:8]; arr={k:v[:8] for k,v in arr.items()}
            _,s,_=evaluate(arr,rr,cfg,"development"); result="PASS" if s["all_gates_pass"] else "SCIENTIFIC_STOP"
        except (FloatingPointError,RuntimeError): result="TECHNICAL_INVALID_STOP"
        outcomes[name]=result
    classify("pass")
    classify("degraded_recovery",lambda a:a.__setitem__("logits_circuit_clean",0.5*a["logits_clean"]+0.5*a["logits_corrupt"]))
    classify("nonspecific_sham",lambda a:a.__setitem__("logits_circuit_sham",0.9*a["logits_clean"]+0.1*a["logits_corrupt"]))
    classify("potent_control",lambda a:a.__setitem__("logits_control",0.9*a["logits_clean"]+0.1*a["logits_corrupt"]))
    def collateral(a):
        z=a["logits_clean"].copy(); z[:,0]+=4; a["logits_circuit_clean"]=z
    classify("high_collateral",collateral); classify("insufficient_support",short=True)
    classify("nonfinite",lambda a:a["logits_circuit_clean"].__setitem__((0,0),np.nan))
    classify("invalid_denominator",lambda a:a.__setitem__("logits_corrupt",a["logits_full_clean"].copy()))
    classify("patch_norm_mismatch",lambda a:a["patch_norm_ratio"].__setitem__(0,2.0))
    classify("ablation_norm_mismatch",lambda a:a["ablation_norm_ratio"].__setitem__(0,2.0))
    if outcomes!=expected: raise RuntimeError(f"calibration mismatch {outcomes}")
    comparators={}
    for name,g in cfg["gates"].items():
        if "point_min" in g:
            x=g["point_min"]; l=g["lower_strict_min"]
            comparators[name]={"point_below":gate_pass(name,{"point":np.nextafter(x,-np.inf),"lower":np.nextafter(l,np.inf),"upper":0},cfg),
                "point_equal":gate_pass(name,{"point":x,"lower":np.nextafter(l,np.inf),"upper":0},cfg),"point_above":gate_pass(name,{"point":np.nextafter(x,np.inf),"lower":np.nextafter(l,np.inf),"upper":0},cfg),
                "lower_equal":gate_pass(name,{"point":np.nextafter(x,np.inf),"lower":l,"upper":0},cfg),"lower_above":gate_pass(name,{"point":np.nextafter(x,np.inf),"lower":np.nextafter(l,np.inf),"upper":0},cfg)}
            expected_cmp={"point_below":False,"point_equal":True,"point_above":True,"lower_equal":False,"lower_above":True}
        elif "point_max" in g:
            x=g["point_max"]; u=g["upper_strict_max"]
            comparators[name]={"point_below":gate_pass(name,{"point":np.nextafter(x,-np.inf),"lower":0,"upper":np.nextafter(u,-np.inf)},cfg),
                "point_equal":gate_pass(name,{"point":x,"lower":0,"upper":np.nextafter(u,-np.inf)},cfg),"point_above":gate_pass(name,{"point":np.nextafter(x,np.inf),"lower":0,"upper":np.nextafter(u,-np.inf)},cfg),
                "upper_equal":gate_pass(name,{"point":np.nextafter(x,-np.inf),"lower":0,"upper":u},cfg),"upper_below":gate_pass(name,{"point":np.nextafter(x,-np.inf),"lower":0,"upper":np.nextafter(u,-np.inf)},cfg)}
            expected_cmp={"point_below":True,"point_equal":True,"point_above":False,"upper_equal":False,"upper_below":True}
        elif "row_min" in g:
            lo,hi=g["row_min"],g["row_max"]
            comparators[name]={"below":row_gate_pass(name,np.array([np.nextafter(lo,-np.inf)]),cfg),"lower_equal":row_gate_pass(name,np.array([lo]),cfg),
                "inside":row_gate_pass(name,np.array([(lo+hi)/2]),cfg),"upper_equal":row_gate_pass(name,np.array([hi]),cfg),"above":row_gate_pass(name,np.array([np.nextafter(hi,np.inf)]),cfg)}
            expected_cmp={"below":False,"lower_equal":True,"inside":True,"upper_equal":True,"above":False}
        else: continue
        if comparators[name]!=expected_cmp: raise RuntimeError(f"comparator calibration {name}")
    target=ROOT/cfg["runtime"]["calibration"]
    atomic_json(target,{"schema_version":"constructed_copy_circuit_v1_calibration","status":"PASS","outcomes":outcomes,"comparators":comparators,
                        "fixture_sha256":sha(root/"calibration_fixture.json"),"implementation_sha256":sha(Path(__file__)),**SCOPE})


def smoke(config_path:Path,device_name:str)->None:
    cfg=config(config_path); verify_protocol(cfg); root=ROOT/cfg["runtime"]["prepared_root"]
    rows=read_jsonl(root/"smoke_fixture.jsonl"); device=torch.device(device_name)
    if device.type=="cuda" and not torch.cuda.is_available(): raise RuntimeError("CUDA unavailable")
    out=torch_forward(rows,cfg,device); oracle=numpy_oracle(rows,cfg); comp=exact_compare(out,oracle); _,summary,qa=evaluate(out,rows,cfg,"development")
    # Smoke support is deliberately smaller than the scientific floor; exact execution is the criterion.
    target=ROOT/cfg["runtime"]["smoke_gpu" if device.type=="cuda" else "smoke_cpu"]
    atomic_json(target,{"schema_version":"constructed_copy_circuit_v1_smoke","status":"PASS","device":device.type,"exact_oracle":comp["pass"],
                        "full_clean_donor_bitwise":qa["full_clean_donor_bitwise"],"full_sham_donor_bitwise":qa["full_sham_donor_bitwise"],
                        "scientific_support_expected":summary["support_pass"],"fixture_sha256":sha(root/"smoke_fixture.jsonl"),"implementation_sha256":sha(Path(__file__)),**SCOPE})


def verify_calibration_smokes(cfg:Mapping[str,Any])->None:
    cal=loadj(ROOT/cfg["runtime"]["calibration"])
    if cal["status"]!="PASS" or cal["implementation_sha256"]!=sha(Path(__file__)) or cal["natural_prompt_assay"]: raise RuntimeError("calibration drift")
    for key,dev in (("smoke_cpu","cpu"),("smoke_gpu","cuda")):
        r=loadj(ROOT/cfg["runtime"][key])
        if r["status"]!="PASS" or r["device"]!=dev or not r["exact_oracle"] or r["implementation_sha256"]!=sha(Path(__file__)):
            raise RuntimeError("smoke drift")


def candidate_inventory(config_path:Path,cfg:Mapping[str,Any])->list[dict[str,Any]]:
    paths=[ROOT/p for p in cfg["candidate_files"]]
    paths += [ROOT/cfg["runtime"]["protocol_lock"],ROOT/cfg["runtime"]["calibration"],ROOT/cfg["runtime"]["smoke_cpu"],ROOT/cfg["runtime"]["smoke_gpu"],ROOT/cfg["runtime"]["candidate_root"]/"GRAPH_REGISTRY.json",ROOT/cfg["runtime"]["candidate_root"]/"ANALYTIC_ELIGIBILITY.json"]
    root=ROOT/cfg["runtime"]["prepared_root"]
    paths += [root/x for x in ("development.jsonl","confirmation.jsonl","smoke_fixture.jsonl","calibration_rows.jsonl","calibration_fixture.json","PREPARED.json")]
    paths += [ROOT/cfg["runtime"]["candidate_review"]]
    unique=[]; seen=set()
    for p in paths:
        lexical=str(p.relative_to(ROOT)) if p.is_absolute() else str(p)
        if lexical.endswith("development.jsonl") or lexical.endswith("confirmation.jsonl"):
            if lexical in seen: continue
            seen.add(lexical); locked=loadj(ROOT/cfg["runtime"]["protocol_lock"])["confirmation_payload"]
            if lexical.endswith("development.jsonl"):
                locked=next(x for x in loadj(ROOT/cfg["runtime"]["protocol_lock"])["items"] if x["path"]==lexical)
            if locked["path"]!=lexical: raise RuntimeError("scientific panel metadata path")
            unique.append(dict(locked)); continue
        p=p.resolve()
        if p in seen: continue
        seen.add(p)
        if not p.is_file(): raise RuntimeError(f"candidate absent {p}")
        unique.append({"path":rel(p),"bytes":p.stat().st_size,"sha256":sha(p)})
    return sorted(unique,key=lambda x:x["path"])


def candidate_preflight(config_path:Path)->None:
    cfg=config(config_path); verify_v2_preservation(cfg); verify_protocol(cfg); verify_prepared(cfg,include_development=False,include_confirmation=False); verify_calibration_smokes(cfg)
    validate_graph_registry(cfg,loadj(ROOT/cfg["runtime"]["candidate_root"]/"GRAPH_REGISTRY.json"))
    elig=loadj(ROOT/cfg["runtime"]["candidate_root"]/"ANALYTIC_ELIGIBILITY.json")
    if elig["status"]!="PASS" or elig["development_rows_passing"]!=256 or elig["confirmation_rows_passing"]!=256: raise RuntimeError("eligibility attestation")
    subprocess.run([sys.executable,str(ROOT/"scripts/verify_paper_claims.py")],check=True,cwd=ROOT)
    if (ROOT/cfg["runtime"]["output_root"]).exists() or (ROOT/cfg["runtime"]["provenance_root"]).exists(): raise RuntimeError("runtime namespace exists")
    print(json.dumps({"status":"PASS","implementation_sha256":sha(Path(__file__)),"protocol_lock_sha256":sha(ROOT/cfg["runtime"]["protocol_lock"]),"v2_preservation_sha256":sha(ROOT/cfg["runtime"]["v2_preservation"]),**SCOPE},sort_keys=True))


def freeze(config_path:Path)->None:
    cfg=config(config_path); candidate_preflight(config_path); review=ROOT/cfg["runtime"]["candidate_review"]
    if review.read_text().splitlines()[0]!="VERDICT: SHIP": raise RuntimeError("candidate SHIP required")
    inv=candidate_inventory(config_path,cfg); confirm=next(x for x in inv if x["path"].endswith("confirmation.jsonl"))
    atomic_json(ROOT/cfg["runtime"]["freeze"],{"schema_version":"constructed_copy_circuit_v1_freeze","status":"FROZEN",
        "config_sha256":sha(config_path),"candidate_inventory":inv,"candidate_inventory_sha256":hashlib.sha256(canon(inv)).hexdigest(),
        "confirmation_payload":confirm,"protocol_lock_sha256":sha(ROOT/cfg["runtime"]["protocol_lock"]),"v2_preservation_sha256":sha(ROOT/cfg["runtime"]["v2_preservation"]),**SCOPE})


def verify_freeze(config_path:Path,*,include_development:bool=False,include_confirmation:bool=False)->dict[str,Any]:
    cfg=config(config_path); fr=loadj(ROOT/cfg["runtime"]["freeze"])
    if fr["config_sha256"]!=sha(config_path) or hashlib.sha256(canon(fr["candidate_inventory"])).hexdigest()!=fr["candidate_inventory_sha256"]: raise RuntimeError("freeze digest")
    for item in fr["candidate_inventory"]:
        if item["path"].endswith("development.jsonl") and not include_development: continue
        if item["path"]==fr["confirmation_payload"]["path"] and not include_confirmation: continue
        p=ROOT/item["path"]
        if not p.is_file() or p.stat().st_size!=item["bytes"] or sha(p)!=item["sha256"]: raise RuntimeError(f"freeze drift {item['path']}")
    verify_v2_preservation(cfg); verify_protocol(cfg,include_development=include_development,include_confirmation=include_confirmation)
    return fr


def bind_review(config_path:Path)->None:
    cfg=config(config_path); fr=ROOT/cfg["runtime"]["freeze"]; cr=ROOT/cfg["runtime"]["candidate_review"]; rr=ROOT/cfg["runtime"]["frozen_review"]
    verify_freeze(config_path)
    if cr.read_text().splitlines()[0]!="VERDICT: SHIP" or rr.read_text().splitlines()[0]!="VERDICT: SHIP": raise RuntimeError("SHIP reviews required")
    atomic_json(ROOT/cfg["runtime"]["review_binding"],{"schema_version":"constructed_copy_circuit_v1_review_binding","status":"SHIP","freeze_sha256":sha(fr),"candidate_review_sha256":sha(cr),"frozen_review_sha256":sha(rr)})


def verify_review_binding(config_path:Path,*,include_development:bool=False,include_confirmation:bool=False)->dict[str,Any]:
    cfg=config(config_path); verify_freeze(config_path,include_development=include_development,include_confirmation=include_confirmation)
    b=loadj(ROOT/cfg["runtime"]["review_binding"]); expected={"schema_version":"constructed_copy_circuit_v1_review_binding","status":"SHIP","freeze_sha256":sha(ROOT/cfg["runtime"]["freeze"]),"candidate_review_sha256":sha(ROOT/cfg["runtime"]["candidate_review"]),"frozen_review_sha256":sha(ROOT/cfg["runtime"]["frozen_review"])}
    if b!=expected: raise RuntimeError("review binding drift")
    return b


def launch_manifest(cfg:Mapping[str,Any])->Path: return ROOT/cfg["runtime"]["provenance_root"]/"launch_manifest.json"


def validate_launch(config_path:Path,token:str)->dict[str,Any]:
    cfg=config(config_path); p=launch_manifest(cfg); r=loadj(p)
    required={"schema_version","launch_token","launcher_pid","started_ns","config","config_sha256","freeze_sha256","review_binding_sha256","protocol_lock_sha256","v2_preservation_sha256","gpu","before_lock_evidence","gpu_lock_path","gpu_lock_inode","gpu_lock_held","session","representation_methods_evaluated","training_performed","natural_prompt_assay"}
    if set(r)!=required or r["schema_version"]!="constructed_copy_circuit_v1_launch" or r["launch_token"]!=token: raise RuntimeError("launch schema/token")
    if r["config_sha256"]!=sha(config_path) or r["freeze_sha256"]!=sha(ROOT/cfg["runtime"]["freeze"]) or r["review_binding_sha256"]!=sha(ROOT/cfg["runtime"]["review_binding"]): raise RuntimeError("launch lineage")
    if r["protocol_lock_sha256"]!=sha(ROOT/cfg["runtime"]["protocol_lock"]) or r["v2_preservation_sha256"]!=sha(ROOT/cfg["runtime"]["v2_preservation"]): raise RuntimeError("launch protocol lineage")
    if r["representation_methods_evaluated"] or r["training_performed"] or r["natural_prompt_assay"]: raise RuntimeError("launch scope")
    before=r["before_lock_evidence"]; gpu=r["gpu"]
    if before.get("physical_index")!=gpu.get("physical_index") or before.get("uuid")!=gpu.get("uuid") or before.get("compute_processes")!=0:
        raise RuntimeError("pre-lock GPU evidence")
    if os.environ.get("CUDA_VISIBLE_DEVICES")!=r["gpu"]["uuid"] or os.environ.get("EXPECTED_GPU_UUID")!=r["gpu"]["uuid"]: raise RuntimeError("GPU env")
    try: os.kill(int(r["launcher_pid"]),0)
    except OSError as e: raise RuntimeError("launcher dead") from e
    inode=int(r["gpu_lock_inode"]); held=False
    fdroot=Path(f"/proc/{r['launcher_pid']}/fd")
    for fd in fdroot.iterdir():
        try:
            if fd.stat().st_ino==inode: held=True; break
        except OSError: pass
    if not held: raise RuntimeError("GPU lock not held")
    return r


def gpu_guard(cfg:Mapping[str,Any],launch:Mapping[str,Any])->torch.device:
    if not torch.cuda.is_available() or torch.cuda.device_count()!=1: raise RuntimeError("CUDA visibility")
    line=subprocess.check_output(["nvidia-smi",f"--id={launch['gpu']['physical_index']}","--query-gpu=uuid","--format=csv,noheader,nounits"],text=True).strip()
    if line!=launch["gpu"]["uuid"]: raise RuntimeError("physical GPU UUID drift")
    return torch.device("cuda:0")


def attempt_dir(cfg:Mapping[str,Any],stage:str)->Path: return ROOT/cfg["runtime"]["provenance_root"]/"attempts"/stage


def attempt_events(cfg:Mapping[str,Any],stage:str)->list[Path]: return sorted(attempt_dir(cfg,stage).glob("*.json"))


def new_attempt(cfg:Mapping[str,Any],stage:str,launch_hash:str)->str:
    d=attempt_dir(cfg,stage)
    if d.exists(): raise RuntimeError("attempt exists")
    d.mkdir(parents=True); token=secrets.token_hex(32)
    atomic_json(d/"00_INITIALIZED.json",{"schema_version":"constructed_copy_circuit_v1_attempt_event","stage":stage,"state":"INITIALIZED","attempt_token":token,"launch_manifest_sha256":launch_hash,"time_ns":time.time_ns()})
    return token


def latest_attempt(cfg:Mapping[str,Any],stage:str,token:str,expected:str)->dict[str,Any]:
    ev=attempt_events(cfg,stage)
    if not ev: raise RuntimeError("attempt missing")
    r=loadj(ev[-1])
    if r["attempt_token"]!=token or r["state"]!=expected: raise RuntimeError(f"attempt state {r.get('state')} != {expected}")
    return r


def transition(cfg:Mapping[str,Any],stage:str,token:str,expected:str,state:str)->None:
    latest_attempt(cfg,stage,token,expected); d=attempt_dir(cfg,stage); idx=len(attempt_events(cfg,stage))
    atomic_json(d/f"{idx:02d}_{state}.json",{"schema_version":"constructed_copy_circuit_v1_attempt_event","stage":stage,"state":state,"attempt_token":token,"launch_manifest_sha256":sha(launch_manifest(cfg)),"time_ns":time.time_ns()})


def reference(config_path:Path,stage:str,replicate:int,launch_token:str,attempt_token:str)->None:
    cfg=config(config_path); expected="INITIALIZED" if replicate==1 else "REFERENCE_1_COMPLETE"; latest_attempt(cfg,stage,attempt_token,expected); launch=validate_launch(config_path,launch_token)
    if stage=="confirmation": validate_authorization(config_path,launch_token)
    verify_freeze(config_path,include_development=True,include_confirmation=stage=="confirmation")
    device=gpu_guard(cfg,launch); path=ROOT/cfg["runtime"]["prepared_root"]/f"{stage}.jsonl"; rows=read_jsonl(path); validate_rows(cfg,rows,stage)
    with torch.inference_mode(): out=torch_forward(rows,cfg,device)
    oracle=numpy_oracle(rows,cfg); comp=exact_compare(out,oracle)
    q=ROOT/cfg["runtime"]["provenance_root"]/"qa"/stage; q.mkdir(parents=True,exist_ok=True); target=q/f"reference_{replicate}.npz"
    if target.exists(): raise RuntimeError("reference exists")
    np.savez_compressed(target,**out)
    atomic_json(q/f"reference_{replicate}.json",{"schema_version":"constructed_copy_circuit_v1_reference","stage":stage,"replicate":replicate,"arrays_sha256":sha(target),"oracle_exact":comp["pass"],"fields":len(comp["fields"]),"gpu_uuid":launch["gpu"]["uuid"],"rows_sha256":sha(path),**SCOPE})


def compare_references(config_path:Path,stage:str,launch_token:str,attempt_token:str)->None:
    cfg=config(config_path); latest_attempt(cfg,stage,attempt_token,"REFERENCE_2_COMPLETE"); validate_launch(config_path,launch_token); q=ROOT/cfg["runtime"]["provenance_root"]/"qa"/stage
    with np.load(q/"reference_1.npz") as a, np.load(q/"reference_2.npz") as b:
        comp=exact_compare({k:a[k] for k in a.files},{k:b[k] for k in b.files})
    atomic_json(q/"REFERENCE_COMPARISON.json",{"schema_version":"constructed_copy_circuit_v1_reference_comparison","stage":stage,"status":"PASS","bitwise":comp["pass"],"fields":len(comp["fields"]),"reference_1_sha256":sha(q/"reference_1.npz"),"reference_2_sha256":sha(q/"reference_2.npz"),**SCOPE})


def validate_reference_bundle(q:Path,row_path:Path,stage:str)->dict[str,Any]:
    comp=loadj(q/"REFERENCE_COMPARISON.json")
    if comp.get("schema_version")!="constructed_copy_circuit_v1_reference_comparison" or comp.get("status")!="PASS" or not comp.get("bitwise"): raise RuntimeError("reference comparison")
    for replicate in (1,2):
        npz=q/f"reference_{replicate}.npz"; meta=loadj(q/f"reference_{replicate}.json")
        if sha(npz)!=comp[f"reference_{replicate}_sha256"] or meta.get("arrays_sha256")!=sha(npz) or meta.get("oracle_exact") is not True or meta.get("stage")!=stage or meta.get("replicate")!=replicate or meta.get("rows_sha256")!=sha(row_path):
            raise RuntimeError("reference hash/oracle/row lineage")
        if meta.get("representation_methods_evaluated") or meta.get("training_performed") or meta.get("natural_prompt_assay"): raise RuntimeError("reference scope")
    return comp


def score_stage(config_path:Path,stage:str,launch_token:str,attempt_token:str)->None:
    cfg=config(config_path); latest_attempt(cfg,stage,attempt_token,"ORACLE_AND_REFERENCES_COMPARED"); launch=validate_launch(config_path,launch_token)
    if stage=="confirmation": validate_authorization(config_path,launch_token)
    q=ROOT/cfg["runtime"]["provenance_root"]/"qa"/stage
    row_path=ROOT/cfg["runtime"]["prepared_root"]/f"{stage}.jsonl"
    comp=validate_reference_bundle(q,row_path,stage)
    rows=read_jsonl(row_path)
    with np.load(q/"reference_1.npz") as f: arr={k:f[k] for k in f.files}
    if len(arr)!=comp.get("fields"): raise RuntimeError("reference field registry")
    rr,summary,qa=evaluate(arr,rows,cfg,stage); qa["independent_live_passes_bitwise"]=True; qa["each_live_pass_oracle_exact"]=True
    out=ROOT/cfg["runtime"]["output_root"]/stage
    if out.exists(): raise RuntimeError("stage output exists")
    out.mkdir(parents=True); write_jsonl(out/"metrics.jsonl",rr); atomic_json(out/"SUMMARY.json",summary); atomic_json(out/"QA.json",qa)
    atomic_json(out/"STARTED.json",{"schema_version":"constructed_copy_circuit_v1_stage_runtime","stage":stage,"gpu_uuid":launch["gpu"]["uuid"],"torch":torch.__version__,"cuda":torch.version.cuda,"device":torch.cuda.get_device_name(0),"inference_mode":True,**SCOPE})
    atomic_json(out/"COMPLETE.json",{"schema_version":"constructed_copy_circuit_v1_complete","stage":stage,"status":summary["status"],"metrics_sha256":sha(out/"metrics.jsonl"),"summary_sha256":sha(out/"SUMMARY.json"),"qa_sha256":sha(out/"QA.json"),"freeze_sha256":sha(ROOT/cfg["runtime"]["freeze"]),"launch_manifest_sha256":sha(launch_manifest(cfg)),"attempt_token":attempt_token,**SCOPE})


def technical_terminal(cfg:Mapping[str,Any],stage:str,reason:str,token:str)->None:
    out=ROOT/cfg["runtime"]["output_root"]/stage; out.mkdir(parents=True,exist_ok=True); p=out/"TECHNICAL_INVALID_STOP.json"
    if not p.exists(): atomic_json(p,{"schema_version":"constructed_copy_circuit_v1_technical_invalid","stage":stage,"status":"TECHNICAL_INVALID_STOP","reason":reason,"attempt_token":token,"launch_manifest_sha256":sha(launch_manifest(cfg)),**SCOPE})


def stage_controller(config_path:Path,stage:str,launch_token:str)->None:
    cfg=config(config_path); token=new_attempt(cfg,stage,sha(launch_manifest(cfg))); timeout=cfg["runtime"]["stage_timeout_seconds"]
    base=[sys.executable,str(Path(__file__))]
    try:
        validate_launch(config_path,launch_token); verify_review_binding(config_path,include_development=True,include_confirmation=stage=="confirmation")
        if stage=="confirmation": validate_authorization(config_path,launch_token)
        subprocess.run(base+["reference","--config",str(config_path),"--stage",stage,"--replicate","1","--launch-token",launch_token,"--attempt-token",token],check=True,timeout=timeout); transition(cfg,stage,token,"INITIALIZED","REFERENCE_1_COMPLETE")
        subprocess.run(base+["reference","--config",str(config_path),"--stage",stage,"--replicate","2","--launch-token",launch_token,"--attempt-token",token],check=True,timeout=timeout); transition(cfg,stage,token,"REFERENCE_1_COMPLETE","REFERENCE_2_COMPLETE")
        subprocess.run(base+["compare-references","--config",str(config_path),"--stage",stage,"--launch-token",launch_token,"--attempt-token",token],check=True,timeout=timeout); transition(cfg,stage,token,"REFERENCE_2_COMPLETE","ORACLE_AND_REFERENCES_COMPARED")
        subprocess.run(base+["score-stage","--config",str(config_path),"--stage",stage,"--launch-token",launch_token,"--attempt-token",token],check=True,timeout=timeout); transition(cfg,stage,token,"ORACLE_AND_REFERENCES_COMPARED","WORKER_COMPLETE_PENDING_VALIDATION")
        complete=loadj(ROOT/cfg["runtime"]["output_root"]/stage/"COMPLETE.json"); summary=loadj(ROOT/cfg["runtime"]["output_root"]/stage/"SUMMARY.json")
        if complete["summary_sha256"]!=sha(ROOT/cfg["runtime"]["output_root"]/stage/"SUMMARY.json") or complete["status"]!=summary["status"]: raise RuntimeError("stage completion validation")
        transition(cfg,stage,token,"WORKER_COMPLETE_PENDING_VALIDATION","CLOSED")
    except Exception as e:
        try:
            current=loadj(attempt_events(cfg,stage)[-1])["state"]
            if current not in {"CLOSED","CLOSED_TECHNICAL_INVALID"}: transition(cfg,stage,token,current,"CLOSED_TECHNICAL_INVALID")
        finally: technical_terminal(cfg,stage,f"{type(e).__name__}: {e}",token)
        raise


def gate_paths(cfg:Mapping[str,Any])->tuple[Path,Path]:
    root=ROOT/cfg["runtime"]["output_root"]/"development_gate"; return root,ROOT/cfg["runtime"]["provenance_root"]/"development_gate_events"


def gate_event(events:Path,index:int,state:str,**extra:Any)->None:
    payload={"schema_version":"constructed_copy_circuit_v1_gate_event","state":state,"time_ns":time.time_ns(),**extra}; atomic_json(events/f"{index:02d}_{state}.json",payload)


def validate_stage_complete(cfg:Mapping[str,Any],stage:str)->tuple[dict[str,Any],dict[str,Any]]:
    events=attempt_events(cfg,stage); states=[loadj(p)["state"] for p in events]
    expected=["INITIALIZED","REFERENCE_1_COMPLETE","REFERENCE_2_COMPLETE","ORACLE_AND_REFERENCES_COMPARED","WORKER_COMPLETE_PENDING_VALIDATION","CLOSED"]
    if states!=expected: raise RuntimeError(f"{stage} attempt lineage")
    root=ROOT/cfg["runtime"]["output_root"]/stage; complete=loadj(root/"COMPLETE.json"); summary=loadj(root/"SUMMARY.json"); qa=loadj(root/"QA.json")
    if complete.get("summary_sha256")!=sha(root/"SUMMARY.json") or complete.get("metrics_sha256")!=sha(root/"metrics.jsonl") or complete.get("qa_sha256")!=sha(root/"QA.json"):
        raise RuntimeError(f"{stage} completion hashes")
    if complete.get("status")!=summary.get("status") or complete.get("attempt_token")!=loadj(events[0]).get("attempt_token") or summary.get("technical_valid") is not True:
        raise RuntimeError(f"{stage} completion content")
    if qa.get("independent_live_passes_bitwise") is not True or qa.get("each_live_pass_oracle_exact") is not True: raise RuntimeError(f"{stage} QA")
    return complete,summary


def validate_development_gate_bundle(cfg:Mapping[str,Any])->dict[str,Any]:
    _,summary=validate_stage_complete(cfg,"development")
    root,events=gate_paths(cfg); paths=sorted(events.glob("*.json")); states=[loadj(p)["state"] for p in paths]
    if states!=["INITIALIZED","DEVELOPMENT_VALIDATED","CLOSED_PASS"]: raise RuntimeError("development gate journal")
    result=loadj(root/"result.json"); terminal=loadj(paths[-1]); validated=loadj(paths[1])
    if result.get("status")!="PASS" or result.get("confirmation_authorized") is not True or not summary.get("all_gates_pass") or not all(summary.get("gate_decisions",{}).values()): raise RuntimeError("development gate not all-pass")
    if result.get("development_summary_sha256")!=sha(ROOT/cfg["runtime"]["output_root"]/"development/SUMMARY.json") or validated.get("summary_sha256")!=result["development_summary_sha256"] or terminal.get("result_sha256")!=sha(root/"result.json"):
        raise RuntimeError("development gate hash lineage")
    if result.get("metrics")!=summary.get("metrics") or result.get("gate_decisions")!=summary.get("gate_decisions"): raise RuntimeError("development gate payload")
    return result


def validate_development_stop_bundle(cfg:Mapping[str,Any])->dict[str,Any]:
    _,summary=validate_stage_complete(cfg,"development")
    root,events=gate_paths(cfg); paths=sorted(events.glob("*.json")); states=[loadj(p)["state"] for p in paths]
    if states!=["INITIALIZED","DEVELOPMENT_VALIDATED","CLOSED_STOP"]: raise RuntimeError("development stop gate journal")
    result=loadj(root/"result.json"); terminal=loadj(paths[-1]); validated=loadj(paths[1])
    summary_path=ROOT/cfg["runtime"]["output_root"]/"development/SUMMARY.json"
    if result.get("status")!="STOP" or result.get("confirmation_authorized") is not False or summary.get("all_gates_pass") is not False:
        raise RuntimeError("development stop gate content")
    if result.get("development_summary_sha256")!=sha(summary_path) or validated.get("summary_sha256")!=result["development_summary_sha256"] or terminal.get("result_sha256")!=sha(root/"result.json"):
        raise RuntimeError("development stop gate hash lineage")
    if result.get("metrics")!=summary.get("metrics") or result.get("gate_decisions")!=summary.get("gate_decisions"):
        raise RuntimeError("development stop gate payload")
    auth_root,auth_events=authorization_paths(cfg); auth_paths=sorted(auth_events.glob("*.json"))
    if [loadj(p)["state"] for p in auth_paths] != ["PRECHECK_JOURNALED","CLOSED_BLOCKED_NO_ACCESS"]:
        raise RuntimeError("development stop authorization journal")
    blocked=loadj(auth_root/"CONFIRMATION_BLOCKED.json")
    if blocked.get("status")!="BLOCKED" or blocked.get("reason")!="DEVELOPMENT_GATE_STOP" or blocked.get("payload_touched") is not False:
        raise RuntimeError("development stop confirmation block")
    if (auth_root/"CONFIRMATION_AUTHORIZATION.json").exists(): raise RuntimeError("stop was authorized")
    return result


def development_gate(config_path:Path,launch_token:str)->None:
    cfg=config(config_path); validate_launch(config_path,launch_token); root,events=gate_paths(cfg)
    if root.exists() or events.exists(): raise RuntimeError("development gate exists")
    events.mkdir(parents=True); gate_event(events,0,"INITIALIZED",launch_manifest_sha256=sha(launch_manifest(cfg)))
    try:
        latest=loadj(attempt_events(cfg,"development")[-1]); summary=loadj(ROOT/cfg["runtime"]["output_root"]/"development/SUMMARY.json")
        if latest["state"]!="CLOSED": raise RuntimeError("development not closed")
        gate_event(events,1,"DEVELOPMENT_VALIDATED",summary_sha256=sha(ROOT/cfg["runtime"]["output_root"]/"development/SUMMARY.json"))
        status="PASS" if summary["all_gates_pass"] else "STOP"; root.mkdir(parents=True)
        atomic_json(root/"result.json",{"schema_version":"constructed_copy_circuit_v1_development_gate","status":status,"confirmation_authorized":status=="PASS","development_summary_sha256":sha(ROOT/cfg["runtime"]["output_root"]/"development/SUMMARY.json"),"metrics":summary["metrics"],"gate_decisions":summary["gate_decisions"],**SCOPE})
        gate_event(events,2,"CLOSED_PASS" if status=="PASS" else "CLOSED_STOP",result_sha256=sha(root/"result.json"))
    except Exception as e:
        root.mkdir(parents=True,exist_ok=True); atomic_json(root/"DEVELOPMENT_GATE_TECHNICAL_INVALID_STOP.json",{"status":"DEVELOPMENT_GATE_TECHNICAL_INVALID_STOP","reason":f"{type(e).__name__}: {e}",**SCOPE}); gate_event(events,len(list(events.glob('*.json'))),"CLOSED_TECHNICAL_INVALID"); raise


def authorization_paths(cfg:Mapping[str,Any])->tuple[Path,Path]:
    return ROOT/cfg["runtime"]["output_root"]/"confirmation_authorization",ROOT/cfg["runtime"]["provenance_root"]/"confirmation_authorization_events"


def auth_event(events:Path,index:int,state:str,**extra:Any)->None:
    atomic_json(events/f"{index:02d}_{state}.json",{"schema_version":"constructed_copy_circuit_v1_authorization_event","state":state,"time_ns":time.time_ns(),**extra})


def authorization_access_may_have_occurred(event_records:Sequence[Mapping[str,Any]])->bool:
    return any(r.get("state")=="ACCESS_MAY_HAVE_OCCURRED" or r.get("payload_access_may_have_occurred") is True for r in event_records)


def authorization_reconcile_decision(event_records:Sequence[Mapping[str,Any]],authorized_artifact_valid:bool)->tuple[str,bool]:
    if not event_records: return "NONE",False
    state=str(event_records[-1].get("state")); may=authorization_access_may_have_occurred(event_records)
    if state in {"CLOSED_BLOCKED_NO_ACCESS","CLOSED_TECHNICAL_INVALID"}: return "NONE",may
    if state=="CLOSED_AUTHORIZED" and authorized_artifact_valid: return "NONE",True
    return "SEAL_TECHNICAL_INVALID",may or state=="CLOSED_AUTHORIZED"


def authorize_confirmation(config_path:Path,launch_token:str)->None:
    cfg=config(config_path); validate_launch(config_path,launch_token); root,events=authorization_paths(cfg)
    if root.exists() or events.exists(): raise RuntimeError("authorization exists")
    events.mkdir(parents=True); root.mkdir(parents=True); auth_event(events,0,"PRECHECK_JOURNALED",payload_access_may_have_occurred=False)
    try:
        verify_review_binding(config_path,include_development=True,include_confirmation=False); gate=loadj(ROOT/cfg["runtime"]["output_root"]/"development_gate/result.json")
        if gate["status"]!="PASS":
            auth_event(events,1,"CLOSED_BLOCKED_NO_ACCESS",payload_access_may_have_occurred=False)
            atomic_json(root/"CONFIRMATION_BLOCKED.json",{"schema_version":"constructed_copy_circuit_v1_confirmation_blocked","status":"BLOCKED","reason":"DEVELOPMENT_GATE_STOP","payload_touched":False,"natural_prompt_assay":False})
            return
        gate=validate_development_gate_bundle(cfg)
        auth_event(events,1,"PHASE1_PASS_NO_ACCESS",payload_access_may_have_occurred=False,gate_sha256=sha(ROOT/cfg["runtime"]["output_root"]/"development_gate/result.json"))
        auth_event(events,2,"ACCESS_MAY_HAVE_OCCURRED",payload_access_may_have_occurred=True)
        payload=ROOT/cfg["runtime"]["prepared_root"]/"confirmation.jsonl"; size=payload.stat().st_size; digest=sha(payload)
        fr=loadj(ROOT/cfg["runtime"]["freeze"])
        if size!=fr["confirmation_payload"]["bytes"] or digest!=fr["confirmation_payload"]["sha256"]: raise RuntimeError("confirmation payload drift")
        authorization={"schema_version":"constructed_copy_circuit_v1_confirmation_authorization","status":"AUTHORIZED","phase1_pass":True,"phase2_pass":True,"payload_accessed":True,"payload_bytes":size,"payload_sha256":digest,"gate_sha256":sha(ROOT/cfg["runtime"]["output_root"]/"development_gate/result.json"),**SCOPE}
        atomic_json(root/"CONFIRMATION_AUTHORIZATION.json",authorization)
        auth_event(events,3,"CLOSED_AUTHORIZED",payload_access_may_have_occurred=True,payload_bytes=size,payload_sha256=digest,authorization_sha256=sha(root/"CONFIRMATION_AUTHORIZATION.json"))
    except Exception as e:
        may=any("ACCESS_MAY_HAVE_OCCURRED" in p.name for p in events.glob("*.json")); auth_event(events,len(list(events.glob('*.json'))),"CLOSED_TECHNICAL_INVALID",payload_access_may_have_occurred=may)
        atomic_json(root/"CONFIRMATION_AUTHORIZATION_TECHNICAL_INVALID_STOP.json",{"status":"CONFIRMATION_AUTHORIZATION_TECHNICAL_INVALID_STOP","reason":f"{type(e).__name__}: {e}","payload_access_may_have_occurred":may,**SCOPE}); raise


def validate_authorization(config_path:Path,launch_token:str)->dict[str,Any]:
    cfg=config(config_path); validate_launch(config_path,launch_token); validate_development_gate_bundle(cfg); root,events=authorization_paths(cfg); rec=loadj(root/"CONFIRMATION_AUTHORIZATION.json")
    latest=loadj(sorted(events.glob("*.json"))[-1]); payload=ROOT/cfg["runtime"]["prepared_root"]/"confirmation.jsonl"
    if latest["state"]!="CLOSED_AUTHORIZED" or latest.get("authorization_sha256")!=sha(root/"CONFIRMATION_AUTHORIZATION.json") or rec["status"]!="AUTHORIZED" or rec["payload_sha256"]!=sha(payload) or rec.get("gate_sha256")!=sha(ROOT/cfg["runtime"]["output_root"]/"development_gate/result.json"): raise RuntimeError("authorization validation")
    return rec


def final(config_path:Path,launch_token:str)->None:
    cfg=config(config_path); validate_launch(config_path,launch_token); out=ROOT/cfg["runtime"]["output_root"]; target=out/"final/result.json"
    if target.exists(): raise RuntimeError("final exists")
    devtech=out/"development/TECHNICAL_INVALID_STOP.json"; gatetech=out/"development_gate/DEVELOPMENT_GATE_TECHNICAL_INVALID_STOP.json"; authtech=out/"confirmation_authorization/CONFIRMATION_AUTHORIZATION_TECHNICAL_INVALID_STOP.json"; contech=out/"confirmation/TECHNICAL_INVALID_STOP.json"
    dev=loadj(out/"development/SUMMARY.json") if (out/"development/SUMMARY.json").is_file() else None; conf=loadj(out/"confirmation/SUMMARY.json") if (out/"confirmation/SUMMARY.json").is_file() else None
    validation_error=None
    try:
        if any(p.is_file() for p in (devtech,gatetech,authtech,contech)): status="TECHNICAL_INVALID_STOP"
        elif dev is None: status="TECHNICAL_INVALID_STOP"
        elif not dev["all_gates_pass"]:
            validate_development_stop_bundle(cfg); status="DEVELOPMENT_GROUND_TRUTH_STOP"
        else:
            validate_development_gate_bundle(cfg); validate_authorization(config_path,launch_token)
            if conf is None: status="TECHNICAL_INVALID_STOP"
            else:
                _,validated_conf=validate_stage_complete(cfg,"confirmation")
                if validated_conf!=conf: raise RuntimeError("confirmation summary changed during finalization")
                status="CONFIRMATION_GROUND_TRUTH_STOP" if not conf["all_gates_pass"] else "GROUND_TRUTH_CIRCUIT_CONTROL_CONFIRMED"
    except Exception as e:
        status="TECHNICAL_INVALID_STOP"; validation_error=f"{type(e).__name__}: {e}"
    atomic_json(target,{"schema_version":"constructed_copy_circuit_v1_final","status":status,"development":dev,"confirmation":conf,
        "validation_error":validation_error,
        "technical_pipeline_validated_on_constructed_system":status=="GROUND_TRUTH_CIRCUIT_CONTROL_CONFIRMED",
        "separately_frozen_method_benchmark_design_justified":status=="GROUND_TRUTH_CIRCUIT_CONTROL_CONFIRMED",
        "method_benchmark_automatically_authorized":False,"freeze_sha256":sha(ROOT/cfg["runtime"]["freeze"]),"launch_manifest_sha256":sha(launch_manifest(cfg)),**SCOPE})


def reconcile(config_path:Path,launch_token:str)->None:
    cfg=config(config_path); validate_launch(config_path,launch_token); out=ROOT/cfg["runtime"]["output_root"]
    if (out/"final/result.json").is_file(): return
    # Never execute a model forward. Conservatively close every opened attempt.
    for stage in STAGES:
        ev=attempt_events(cfg,stage)
        if attempt_dir(cfg,stage).exists() and not ev:
            technical_terminal(cfg,stage,"NO_FORWARD_RECONCILER_SEALED_EMPTY_ATTEMPT_JOURNAL","UNRECORDED_ATTEMPT_TOKEN")
            continue
        if ev:
            try: r=loadj(ev[-1]); token=r["attempt_token"]
            except Exception:
                technical_terminal(cfg,stage,"NO_FORWARD_RECONCILER_FOUND_MALFORMED_ATTEMPT_JOURNAL","UNREADABLE_ATTEMPT_TOKEN"); continue
            if r["state"] not in {"CLOSED","CLOSED_TECHNICAL_INVALID"}:
                transition(cfg,stage,token,r["state"],"CLOSED_TECHNICAL_INVALID"); technical_terminal(cfg,stage,"NO_FORWARD_RECONCILER_SEALED_INCOMPLETE_ATTEMPT",token)
    gate_root,gate_events=gate_paths(cfg); gate_files=sorted(gate_events.glob("*.json")) if gate_events.exists() else []
    try: dev_closed=bool(attempt_events(cfg,"development") and loadj(attempt_events(cfg,"development")[-1]).get("state")=="CLOSED")
    except Exception: dev_closed=False
    try: gate_closed=bool(gate_files and loadj(gate_files[-1]).get("state") in {"CLOSED_PASS","CLOSED_STOP","CLOSED_TECHNICAL_INVALID"})
    except Exception: gate_closed=False
    if (gate_files and not gate_closed) or (dev_closed and not gate_files and not (gate_root/"result.json").is_file()):
        gate_events.mkdir(parents=True,exist_ok=True)
        if not gate_files: gate_event(gate_events,0,"INITIALIZED",launch_manifest_sha256=sha(launch_manifest(cfg))); gate_files=sorted(gate_events.glob("*.json"))
        gate_event(gate_events,len(gate_files),"CLOSED_TECHNICAL_INVALID")
        gate_root.mkdir(parents=True,exist_ok=True); p=gate_root/"DEVELOPMENT_GATE_TECHNICAL_INVALID_STOP.json"
        if not p.exists(): atomic_json(p,{"status":"DEVELOPMENT_GATE_TECHNICAL_INVALID_STOP","reason":"NO_FORWARD_RECONCILER_SEALED_INCOMPLETE_GATE","natural_prompt_assay":False,**SCOPE})
    auth_root,auth_events=authorization_paths(cfg)
    auth_files=sorted(auth_events.glob("*.json")) if auth_events.exists() else []
    if auth_files:
        try: records=[loadj(p) for p in auth_files]; state=records[-1]["state"]
        except Exception:
            auth_root.mkdir(parents=True,exist_ok=True); p=auth_root/"CONFIRMATION_AUTHORIZATION_TECHNICAL_INVALID_STOP.json"
            if not p.exists(): atomic_json(p,{"status":"CONFIRMATION_AUTHORIZATION_TECHNICAL_INVALID_STOP","reason":"NO_FORWARD_RECONCILER_FOUND_MALFORMED_AUTHORIZATION_JOURNAL","payload_access_may_have_occurred":True,**SCOPE})
            records=[]; state="CLOSED_TECHNICAL_INVALID"
        authorized_valid=False
        if state=="CLOSED_AUTHORIZED":
            try: validate_authorization(config_path,launch_token); authorized_valid=True
            except Exception: authorized_valid=False
        decision,may=authorization_reconcile_decision(records,authorized_valid)
        if decision=="SEAL_TECHNICAL_INVALID":
            auth_root.mkdir(parents=True,exist_ok=True); auth_event(auth_events,len(auth_files),"CLOSED_TECHNICAL_INVALID",payload_access_may_have_occurred=may)
            p=auth_root/"CONFIRMATION_AUTHORIZATION_TECHNICAL_INVALID_STOP.json"
            if not p.exists(): atomic_json(p,{"status":"CONFIRMATION_AUTHORIZATION_TECHNICAL_INVALID_STOP","reason":"NO_FORWARD_RECONCILER_SEALED_INCOMPLETE_AUTHORIZATION","payload_access_may_have_occurred":may,**SCOPE})
    elif auth_root.exists() or auth_events.exists():
        auth_events.mkdir(parents=True,exist_ok=True); auth_event(auth_events,0,"CLOSED_TECHNICAL_INVALID",payload_access_may_have_occurred=False)
        auth_root.mkdir(parents=True,exist_ok=True); p=auth_root/"CONFIRMATION_AUTHORIZATION_TECHNICAL_INVALID_STOP.json"
        if not p.exists(): atomic_json(p,{"status":"CONFIRMATION_AUTHORIZATION_TECHNICAL_INVALID_STOP","reason":"NO_FORWARD_RECONCILER_SEALED_EMPTY_AUTHORIZATION_JOURNAL","payload_access_may_have_occurred":False,**SCOPE})
    # Any upstream terminal before authorization permanently blocks confirmation without touching it.
    upstream_terminal=any((out/p).is_file() for p in ("development/TECHNICAL_INVALID_STOP.json","development_gate/DEVELOPMENT_GATE_TECHNICAL_INVALID_STOP.json"))
    if upstream_terminal and not auth_files and not (auth_root.exists() or auth_events.exists()):
        auth_events.mkdir(parents=True,exist_ok=True); auth_event(auth_events,0,"CLOSED_BLOCKED_NO_ACCESS",payload_access_may_have_occurred=False)
        auth_root.mkdir(parents=True,exist_ok=True); p=auth_root/"CONFIRMATION_BLOCKED.json"
        if not p.exists(): atomic_json(p,{"schema_version":"constructed_copy_circuit_v1_confirmation_blocked","status":"BLOCKED","reason":"UPSTREAM_TECHNICAL_STOP","payload_touched":False,"natural_prompt_assay":False})
    try: final(config_path,launch_token)
    except Exception: pass


def main()->None:
    ap=argparse.ArgumentParser(); sp=ap.add_subparsers(dest="command",required=True)
    def cmd(name:str):
        p=sp.add_parser(name); p.add_argument("--config",type=Path,default=DEFAULT); return p
    for name in ("prepare","protocol-lock","candidate-attest","calibrate","candidate-preflight","freeze","bind-review"):
        cmd(name)
    p=cmd("smoke"); p.add_argument("--device",choices=("cpu","cuda"),required=True)
    p=cmd("verify-freeze"); p.add_argument("--include-confirmation",action="store_true")
    p=cmd("verify-review-binding"); p.add_argument("--include-confirmation",action="store_true")
    for name in ("stage-controller","reference","compare-references","score-stage"):
        p=cmd(name); p.add_argument("--stage",choices=STAGES,required=True); p.add_argument("--launch-token",required=True)
        if name in ("reference","compare-references","score-stage"): p.add_argument("--attempt-token",required=True)
        if name=="reference": p.add_argument("--replicate",type=int,choices=(1,2),required=True)
    for name in ("development-gate","authorize-confirmation","final","reconcile"):
        p=cmd(name); p.add_argument("--launch-token",required=True)
    a=ap.parse_args(); c=a.command
    if c=="prepare": prepare(a.config)
    elif c=="protocol-lock": protocol_lock(a.config)
    elif c=="candidate-attest": create_candidate_attestations(a.config)
    elif c=="calibrate": calibration(a.config)
    elif c=="smoke": smoke(a.config,a.device)
    elif c=="candidate-preflight": candidate_preflight(a.config)
    elif c=="freeze": freeze(a.config)
    elif c=="verify-freeze": print(json.dumps({"status":"PASS","inventory":verify_freeze(a.config,include_confirmation=a.include_confirmation)["candidate_inventory_sha256"]}))
    elif c=="bind-review": bind_review(a.config)
    elif c=="verify-review-binding": print(json.dumps(verify_review_binding(a.config,include_confirmation=a.include_confirmation),sort_keys=True))
    elif c=="stage-controller": stage_controller(a.config,a.stage,a.launch_token)
    elif c=="reference": reference(a.config,a.stage,a.replicate,a.launch_token,a.attempt_token)
    elif c=="compare-references": compare_references(a.config,a.stage,a.launch_token,a.attempt_token)
    elif c=="score-stage": score_stage(a.config,a.stage,a.launch_token,a.attempt_token)
    elif c=="development-gate": development_gate(a.config,a.launch_token)
    elif c=="authorize-confirmation": authorize_confirmation(a.config,a.launch_token)
    elif c=="final": final(a.config,a.launch_token)
    else: reconcile(a.config,a.launch_token)

if __name__=="__main__": main()
