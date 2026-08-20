#!/usr/bin/env python3
"""Signed one-shot lifecycle and inference-only runner for Attempt 14."""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

import numpy as np

from atlas_context_local_v10 import (CANDIDATE_REVIEW, CONFIG, FINAL_FREEZE, NAMESPACE, PLAN, PLAN_REVIEW, ROOT,
    SCIENCE_AUTHORIZATION, atomic_json, canonical_json_bytes, inventory_digest, load_signing_key, production_forward,
    read_json, read_jsonl, recursive_inventory, sha256_file, sign_payload, verify_candidate_review, verify_signed)

BACKEND_QA=ROOT/"configs/atlas_context_local_v10/BACKEND_QA.json"
ATTEMPT13_CLAIM=ROOT/"reports/claim_review/atlas_v3_9_attempt13_post_result_claim_review.md"

def gpu_rows()->list[dict[str,Any]]:
    cp=subprocess.run(["nvidia-smi","--query-gpu=index,uuid,memory.free,memory.total","--format=csv,noheader,nounits"],check=True,text=True,capture_output=True)
    out=[]
    for line in cp.stdout.splitlines():
        a,b,c,d=[x.strip() for x in line.split(",")]; out.append({"index":int(a),"uuid":b,"memory_free_mib":int(c),"memory_total_mib":int(d)})
    return out

def assert_gpu(cfg:dict[str,Any],minimum_free:int=2000)->dict[str,Any]:
    expected=cfg["runtime"]; row=next((x for x in gpu_rows() if x["index"]==expected["physical_gpu_index"]),None)
    if row is None or row["uuid"]!=expected["gpu_uuid"] or row["memory_free_mib"]<minimum_free: raise RuntimeError(f"GPU preflight failed: {row}")
    visible=os.environ.get("CUDA_VISIBLE_DEVICES")
    if visible is not None and visible!=row["uuid"]: raise RuntimeError(f"CUDA_VISIBLE_DEVICES must expose exact UUID: {visible}")
    return row

def torch_runtime_attestation(cfg:dict[str,Any],*,require_tmux:bool)->dict[str,Any]:
    import torch
    if os.environ.get("CUDA_VISIBLE_DEVICES")!=cfg["runtime"]["gpu_uuid"]: raise RuntimeError("exact GPU UUID is not the CUDA visibility selector")
    if os.environ.get("CUBLAS_WORKSPACE_CONFIG")!=cfg["runtime"]["cublas_workspace_config"]: raise RuntimeError("CUBLAS workspace contract mismatch")
    if torch.cuda.device_count()!=1: raise RuntimeError("exactly one CUDA device must be visible")
    props=torch.cuda.get_device_properties(0); actual="GPU-"+str(props.uuid)
    if actual!=cfg["runtime"]["gpu_uuid"]: raise RuntimeError(f"Torch visible GPU UUID mismatch: {actual}")
    session=None
    if require_tmux:
        pane=os.environ.get("TMUX_PANE")
        if not os.environ.get("TMUX") or not pane: raise RuntimeError("science run must execute inside tmux")
        session=subprocess.run(["tmux","display-message","-p","-t",pane,"#S"],check=True,text=True,capture_output=True).stdout.strip()
        if session!=cfg["tmux_session"]: raise RuntimeError(f"tmux session mismatch: {session}")
    return {"visible_device_count":torch.cuda.device_count(),"torch_visible_uuid":actual,"torch_device_name":props.name,
      "cuda_visible_devices":os.environ.get("CUDA_VISIBLE_DEVICES"),"cublas_workspace_config":os.environ.get("CUBLAS_WORKSPACE_CONFIG"),"tmux_session":session}

def attempt13_attestation()->dict[str,Any]:
    run=ROOT/"pilot_runs/20260803_atlas_relation_context_v9_attempt13"; result=ROOT/"results/atlas_relation_context_v9_attempt13"
    term=verify_signed(run/"TERMINAL.json","1eb6470fb2bd3a114ca4427174a12eb5fb14639ca1e763f75b9afbb564b2e503",allow_legacy_envelope=True)
    if term.get("status")!="TERMINAL_COMPLETE" or not term.get("no_retry_authorized") or term.get("neural_training_run") or term.get("representation_training_run"):
        raise RuntimeError("Attempt13 terminal contract mismatch")
    ri=recursive_inventory(run,exclude=["TERMINAL.json"]); oi=recursive_inventory(result)
    if inventory_digest(ri)!=term["run_inventory_excluding_terminal"]["digest"] or inventory_digest(oi)!=term["result_inventory"]["digest"]:
        raise RuntimeError("Attempt13 inventory drift")
    wording="Cross-corpus relational information was detectable, but strong recovery and relation-specific isolation were not demonstrated."
    return {"terminal_sha256":sha256_file(run/"TERMINAL.json"),"run_inventory_digest":inventory_digest(ri),"result_inventory_digest":inventory_digest(oi),
        "claim_review_sha256":sha256_file(ATTEMPT13_CLAIM),"formal_wording":wording,"decision":term["decision"],"unchanged":True}

def candidate_paths(cfg:dict[str,Any])->list[Path]:
    paths=[PLAN,PLAN_REVIEW,ROOT/"requirements-atlas.lock.txt",ROOT/"configs/atlas_context_local_v10/run.json",
      ROOT/"scripts/atlas_context_local_v10.py",ROOT/"scripts/build_atlas_context_local_v10.py",ROOT/"scripts/analyze_atlas_context_local_v10.py",ROOT/"scripts/run_atlas_context_local_v10.py",
      ROOT/"scripts/run_atlas_context_local_v10_pipeline.sh",ROOT/"scripts/launch_atlas_context_local_v10_tmux.sh",ROOT/"tests/test_atlas_context_local_v10.py",
      ROOT/"reports/provenance/atlas_v3_10_attempt14_corrected_source_census_v2.json",ROOT/"reports/provenance/atlas_v3_10_attempt14_source_selection_v4.json",
      ROOT/"reports/provenance/atlas_v3_10_attempt14_preacquisition_manifest.json",ROOT/"reports/provenance/atlas_v3_10_attempt14_exposure_supplement_v1.json",
      ROOT/"reports/provenance/atlas_v3_10_attempt14_prescore_rebuild_attestation.json"]
    raw=ROOT/cfg["raw_root"]; paths += sorted(raw.glob("*.conllu"))
    prepared=ROOT/cfg["paths"]["prepared_root"]; paths += sorted(p for p in prepared.iterdir() if p.is_file())
    return paths

def entries(paths:list[Path])->list[dict[str,Any]]:
    out=[]
    for p in paths:
        if not p.is_file() or p.is_symlink(): raise RuntimeError(f"candidate path invalid: {p}")
        out.append({"path":p.relative_to(ROOT).as_posix(),"bytes":p.stat().st_size,"sha256":sha256_file(p)})
    out.sort(key=lambda x:x["path"].encode()); return out

def create_freeze(key_path:Path)->None:
    if FINAL_FREEZE.exists(): raise RuntimeError("FINAL_FREEZE already exists")
    cfg=read_json(CONFIG); key=load_signing_key(key_path,cfg["signer"]); manifest=read_json(ROOT/cfg["paths"]["prepared_root"]/"manifest.json")
    if manifest["status"]!="PRESCORE_ELIGIBLE" or manifest["model_inference_performed"]: raise RuntimeError("prescore not eligible/clean")
    cand=entries(candidate_paths(cfg)); att=attempt13_attestation()
    payload={"schema_version":"atlas_context_local_v10_attempt14_final_freeze_v1","status":"FROZEN_AWAITING_ADVERSARIAL_REVIEW",
      "namespace":NAMESPACE,"config_sha256":sha256_file(CONFIG),"plan_sha256":sha256_file(PLAN),"plan_review_sha256":sha256_file(PLAN_REVIEW),
      "candidate_inventory":cand,"candidate_inventory_sha256":inventory_digest(cand),"prescore_manifest_sha256":sha256_file(ROOT/cfg["paths"]["prepared_root"]/"manifest.json"),
      "attempt13_attestation":att,"calibration":{"fresh_source_activations_used":False,"technical_equivalence_threshold":1e-5,"raw_effect_point_threshold":1e-4,"raw_effect_ci_threshold":1e-5,
        "gate4_common_denominator":True,"gate5_zero_energy_complement":0.0,"haar_reference":16/768},
      "training_authorized":False,"retry_authorized":False,"created_unix":time.time()}
    sign_payload(FINAL_FREEZE,payload,key); print(json.dumps({"freeze":str(FINAL_FREEZE.relative_to(ROOT)),"sha256":sha256_file(FINAL_FREEZE),"candidate_inventory_sha256":payload["candidate_inventory_sha256"]},indent=2))

def verify_freeze(cfg:dict[str,Any])->dict[str,Any]:
    f=verify_signed(FINAL_FREEZE,cfg["signer"]["public_key_fingerprint_sha256"])
    if f["config_sha256"]!=sha256_file(CONFIG) or f["plan_sha256"]!=sha256_file(PLAN) or entries(candidate_paths(cfg))!=f["candidate_inventory"]: raise RuntimeError("frozen candidate drift")
    if attempt13_attestation()!=f["attempt13_attestation"]: raise RuntimeError("Attempt13 changed")
    verify_candidate_review(CANDIDATE_REVIEW,sha256_file(FINAL_FREEZE),f["candidate_inventory_sha256"])
    return f

def load_model(cfg:dict[str,Any])->Any:
    import torch
    from transformers import AutoModelForCausalLM
    torch.use_deterministic_algorithms(True)
    m=AutoModelForCausalLM.from_pretrained(cfg["model"]["name"],revision=cfg["model"]["revision"],local_files_only=True,
        torch_dtype=torch.float32,attn_implementation="eager").to("cuda:0")
    m.eval()
    return m

def backend_qa(key_path:Path)->None:
    if BACKEND_QA.exists(): raise RuntimeError("BACKEND_QA already exists")
    cfg=read_json(CONFIG); freeze=verify_freeze(cfg); key=load_signing_key(key_path,cfg["signer"]); gpu=assert_gpu(cfg)
    model=load_model(cfg); runtime=torch_runtime_attestation(cfg,require_tmux=False)
    rows=[]
    for k in range(3):
        p=5+k; true=[1000+17*k+i for i in range(p)]; other=[5000+19*k+i for i in range(p)]; target=[9000+13*k+i for i in range(8)]
        sub=target.copy(); sub[2]=sub[2]+41
        rows.append({"true_prefix_ids":true,"unrelated_prefix_ids":other,"target_segment_ids":target,"substituted_target_segment_ids":sub,
          "target_sequence_index":p+2,"control_sequence_index":p+5})
    t,c=production_forward(model,rows)
    masked=np.linalg.norm(t[:,0]-t[:,2],axis=1)/np.maximum(np.maximum(np.linalg.norm(t[:,0],axis=1),np.linalg.norm(t[:,2],axis=1)),1e-12)
    active=np.linalg.norm(t[:,1]-t[:,0],axis=1)/np.maximum(np.maximum(np.linalg.norm(t[:,1],axis=1),np.linalg.norm(t[:,0],axis=1)),1e-12)
    passed=bool(np.isfinite(t).all() and np.isfinite(c).all() and np.max(masked)<=cfg["analysis"]["technical_equivalence_threshold"] and np.min(active)>cfg["analysis"]["technical_equivalence_threshold"])
    payload={"schema_version":"atlas_context_local_v10_attempt14_backend_qa_v1","status":"PASS" if passed else "FAIL_NO_SCIENCE_AUTHORIZATION",
      "freeze_sha256":sha256_file(FINAL_FREEZE),"candidate_inventory_sha256":freeze["candidate_inventory_sha256"],"gpu":gpu,"runtime":runtime,"synthetic_only":True,"AnCora_token_used":False,
      "masked_normalized":masked.tolist(),"active_normalized":active.tolist(),"target_shape":list(t.shape),"dtype":str(t.dtype),"training_run":False}
    sign_payload(BACKEND_QA,payload,key); print(json.dumps(payload,indent=2))
    if not passed: raise RuntimeError("backend QA failed")

def authorize(key_path:Path)->None:
    if SCIENCE_AUTHORIZATION.exists(): raise RuntimeError("authorization already exists")
    cfg=read_json(CONFIG); freeze=verify_freeze(cfg); key=load_signing_key(key_path,cfg["signer"]); qa=verify_signed(BACKEND_QA,cfg["signer"]["public_key_fingerprint_sha256"])
    if qa["status"]!="PASS" or qa["freeze_sha256"]!=sha256_file(FINAL_FREEZE): raise RuntimeError("backend QA invalid")
    gpu=assert_gpu(cfg)
    for rel in [cfg["paths"]["run_root"],cfg["paths"]["result_root"],cfg["paths"]["global_opening"]]:
        if (ROOT/rel).exists(): raise RuntimeError(f"one-shot namespace already exists: {rel}")
    opening=ROOT/cfg["paths"]["global_opening"]; failure_record=opening.with_name(opening.stem.replace(".OPENED","")+".FAILURE.json")
    if failure_record.exists(): raise RuntimeError("one-shot failure namespace already exists")
    payload={"schema_version":"atlas_context_local_v10_attempt14_science_authorization_v1","status":"AUTHORIZED_ONCE","freeze_sha256":sha256_file(FINAL_FREEZE),
      "candidate_inventory_sha256":freeze["candidate_inventory_sha256"],"candidate_review_sha256":sha256_file(CANDIDATE_REVIEW),"backend_qa_sha256":sha256_file(BACKEND_QA),
      "gpu":gpu,"training_authorized":False,"retry_authorized":False,"authorized_unix":time.time()}
    sign_payload(SCIENCE_AUTHORIZATION,payload,key); print(json.dumps(payload,indent=2))

def exclusive_json(path:Path,value:dict[str,Any])->None:
    path.parent.mkdir(parents=True,exist_ok=True); raw=canonical_json_bytes(value)+b"\n"
    fd=os.open(path,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
    try:
        view=memoryview(raw)
        while view:
            written=os.write(fd,view)
            if written<=0: raise OSError("short exclusive write")
            view=view[written:]
        os.fsync(fd)
    finally: os.close(fd)
    dfd=os.open(path.parent,os.O_RDONLY|os.O_DIRECTORY)
    try: os.fsync(dfd)
    finally: os.close(dfd)

def run(key_path:Path)->None:
    cfg=read_json(CONFIG); freeze=verify_freeze(cfg); key=load_signing_key(key_path,cfg["signer"]); auth=verify_signed(SCIENCE_AUTHORIZATION,cfg["signer"]["public_key_fingerprint_sha256"])
    if auth["status"]!="AUTHORIZED_ONCE" or auth["freeze_sha256"]!=sha256_file(FINAL_FREEZE): raise RuntimeError("authorization invalid")
    gpu=assert_gpu(cfg); runtime=torch_runtime_attestation(cfg,require_tmux=True)
    run_root=ROOT/cfg["paths"]["run_root"]; result_root=ROOT/cfg["paths"]["result_root"]; opening=ROOT/cfg["paths"]["global_opening"]
    failure_record=opening.with_name(opening.stem.replace(".OPENED","")+".FAILURE.json")
    if run_root.exists() or result_root.exists() or opening.exists() or failure_record.exists(): raise RuntimeError("one-shot namespace already exists")
    opened=False
    try:
        exclusive_json(opening,{"schema_version":"atlas_context_local_v10_attempt14_global_opening_v1","namespace":NAMESPACE,"freeze_sha256":sha256_file(FINAL_FREEZE),"opened_unix":time.time(),"retry_authorized":False})
        opened=True
        run_root.mkdir(parents=True); cache=run_root/"cache"; cache.mkdir()
        sign_payload(run_root/"STARTED.json",{"schema_version":"atlas_context_local_v10_attempt14_started_v1","status":"STARTED","opening_sha256":sha256_file(opening),"gpu":gpu,"runtime":runtime,"training_authorized":False},key)
        model=load_model(cfg); runtime_after_model=torch_runtime_attestation(cfg,require_tmux=True); prepared=ROOT/cfg["paths"]["prepared_root"]; cache_completes={}
        for source in cfg["sources"]:
            rows=read_jsonl(prepared/f"{source}.components.jsonl"); t,c=production_forward(model,rows)
            p=cache/f"{source}.representations.npz"
            np.savez(p,target=t,control=c,component_ids=np.asarray([x["component_id"] for x in rows],dtype="U64"))
            payload={"schema_version":"atlas_context_local_v10_attempt14_cache_complete_v1","status":"CACHE_COMPLETE","source":source,"rows":len(rows),"shape":list(t.shape),"npz_sha256":sha256_file(p),"training_run":False}
            sign_payload(cache/f"{source}.COMPLETE.json",payload,key); cache_completes[source]=sha256_file(cache/f"{source}.COMPLETE.json")
        del model
        import torch; torch.cuda.empty_cache()
        env=os.environ.copy(); env["PYTHONPATH"]=str(ROOT/"scripts")
        subprocess.run([sys.executable,str(ROOT/"scripts/analyze_atlas_context_local_v10.py"),"--config",str(CONFIG.relative_to(ROOT)),"--cache",str(cache.relative_to(ROOT)),"--output",str(result_root.relative_to(ROOT))],cwd=ROOT,env=env,check=True)
        result=read_json(result_root/"result.json")
        post=attempt13_attestation()
        if post!=freeze["attempt13_attestation"]: raise RuntimeError("Attempt13 postflight immutability failure")
        result_entries=recursive_inventory(result_root)
        sign_payload(result_root/"COMPLETE.json",{"schema_version":"atlas_context_local_v10_attempt14_result_complete_v1","status":"RESULT_COMPLETE","decision":result["decision"],"result_inventory_before_complete":result_entries,"digest_before_complete":inventory_digest(result_entries),"attempt13_unchanged":True,"training_run":False},key)
        run_entries=recursive_inventory(run_root,exclude=["TERMINAL.json"]); final_result_entries=recursive_inventory(result_root)
        terminal={"schema_version":"atlas_context_local_v10_attempt14_terminal_v1","status":"TERMINAL_COMPLETE","decision":result["decision"],"no_retry_authorized":True,
          "neural_training_run":False,"representation_training_run":False,"supervised_model_training_run":False,"checkpoint_created":False,"optimizer_created":False,
          "cache_complete_sha256":cache_completes,"run_inventory_excluding_terminal":{"entries":run_entries,"digest":inventory_digest(run_entries)},
          "result_inventory":{"entries":final_result_entries,"digest":inventory_digest(final_result_entries)},"attempt13_unchanged":True,"gpu":gpu,"runtime":runtime_after_model}
        sign_payload(run_root/"TERMINAL.json",terminal,key); print(json.dumps(terminal,indent=2,allow_nan=False))
    except Exception as e:
        if opened:
            fail={"schema_version":"atlas_context_local_v10_attempt14_terminal_failure_v1","status":"TERMINAL_FAILURE_NO_RETRY","opening_sha256":sha256_file(opening) if opening.exists() else None,
              "error_type":type(e).__name__,"error":str(e),"no_retry_authorized":True,"training_run":False,"gpu":gpu,"runtime":runtime}
            sign_payload(failure_record,fail,key)
            if run_root.is_dir() and not (run_root/"TERMINAL.json").exists(): sign_payload(run_root/"TERMINAL.json",fail,key)
        raise

def main()->None:
    ap=argparse.ArgumentParser(); ap.add_argument("command",choices=["create-freeze","backend-qa","authorize","run"]); ap.add_argument("--signing-key",required=True)
    args=ap.parse_args(); key=Path(args.signing_key).resolve()
    {"create-freeze":create_freeze,"backend-qa":backend_qa,"authorize":authorize,"run":run}[args.command](key)
if __name__=="__main__": main()
