#!/usr/bin/env python3
"""Two-tier canonical induction technical control; no representation methods or training."""
from __future__ import annotations

import argparse
import builtins
import contextlib
import fcntl
import hashlib
import io
import json
import os
import random
import secrets
import subprocess
import sys
import time
import traceback
from pathlib import Path
from typing import Any, Mapping, Sequence

import numpy as np
import torch

ROOT = Path(__file__).resolve().parents[1]
DEFAULT = ROOT / "configs/canonical_induction_two_tier_v2/run.json"
QA_ARRAYS = (
    "clean_logits", "corrupt_logits", "sham_logits",
    "clean_circuit_heads", "corrupt_circuit_heads", "sham_circuit_heads",
    "clean_control_heads", "corrupt_control_heads",
    "clean_final_residual", "sham_final_residual",
)
GATE_FIELDS = ("skyline_recovery", "joint_recovery", "selectivity", "circuit_control_margin", "ablation_advantage")


def registered_descriptive_fields(cfg:Mapping[str,Any])->list[str]:
    fields=[f"individual_{a}_{b}_recovery" for a,b in cfg["model"]["circuit_heads"]]
    fields += [f"class_{name}_recovery" for name in cfg["model"]["classes"]]
    fields += ["additivity_ratio"]
    fields += [f"vocab_restoration_{q}" for q in ("full_clean","full_sham","circuit_clean","circuit_sham","control_clean")]
    fields += [f"token_movement_{q}_{u}" for q in ("full_clean","full_sham","circuit_clean","circuit_sham","control_clean") for u in ("target","contrast","sham")]
    fields += [f"collateral_{q}" for q in ("circuit_clean","circuit_sham","control_clean")]
    return sorted(fields)


def native(value: Any) -> Any:
    if isinstance(value, np.generic): return value.item()
    if isinstance(value, np.ndarray): return value.tolist()
    if isinstance(value, dict): return {str(k): native(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)): return [native(v) for v in value]
    return value


def canon(value: Any) -> bytes:
    return json.dumps(native(value), sort_keys=True, separators=(",", ":"), allow_nan=False).encode()


def loadj(path: Path) -> Any: return json.loads(path.read_text())


def sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(8 << 20), b""): h.update(chunk)
    return h.hexdigest()


def endpoint_seed(seed: int, stage: str, endpoint: str) -> int:
    preimage = f"{int(seed)}|{stage}|{endpoint}".encode("utf-8")
    return int.from_bytes(hashlib.sha256(preimage).digest()[:4], "little", signed=False)


def exjson(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + f".tmp.{os.getpid()}.{time.time_ns()}")
    fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    try:
        with os.fdopen(fd, "wb") as f:
            f.write(canon(value) + b"\n"); f.flush(); os.fsync(f.fileno())
        os.link(tmp, path)
    finally:
        tmp.unlink(missing_ok=True)


def replace_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + f".tmp.{os.getpid()}.{time.time_ns()}")
    with tmp.open("wb") as f:
        f.write(canon(value) + b"\n"); f.flush(); os.fsync(f.fileno())
    os.replace(tmp, path)


def publish(path: Path, value: Any) -> None:
    try: exjson(path, value)
    except FileExistsError: pass


def writejl(path: Path, rows: Sequence[Mapping[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, "w") as f:
        for row in rows: f.write(canon(dict(row)).decode() + "\n")
        f.flush(); os.fsync(f.fileno())


def readjl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(x) for x in path.read_text().splitlines() if x]


def require_config(config: Path) -> dict[str, Any]:
    if config.resolve() != DEFAULT.resolve(): raise RuntimeError("only registered config path is legal")
    return loadj(config)


def require_offline() -> None:
    for key in ("HF_DATASETS_OFFLINE", "HF_HUB_OFFLINE", "TRANSFORMERS_OFFLINE"):
        if os.environ.get(key) != "1": raise RuntimeError(f"offline environment required: {key}=1")


@contextlib.contextmanager
def deny_path_access(forbidden:Path):
    """Fail closed on Python-level open/stat access to the sealed confirmation payload."""
    target=forbidden.absolute()
    original_builtin_open,original_io_open,original_stat,original_lstat=builtins.open,io.open,os.stat,os.lstat
    def check(value:Any)->None:
        if isinstance(value,(str,bytes,os.PathLike)):
            try: candidate=Path(os.fsdecode(value)).absolute()
            except (TypeError,ValueError): return
            if candidate==target: raise RuntimeError("sealed confirmation payload access attempted")
    def guarded_open(file,*args,**kwargs): check(file); return original_builtin_open(file,*args,**kwargs)
    def guarded_io_open(file,*args,**kwargs): check(file); return original_io_open(file,*args,**kwargs)
    def guarded_stat(path,*args,**kwargs): check(path); return original_stat(path,*args,**kwargs)
    def guarded_lstat(path,*args,**kwargs): check(path); return original_lstat(path,*args,**kwargs)
    builtins.open=guarded_open; io.open=guarded_io_open; os.stat=guarded_stat; os.lstat=guarded_lstat
    try: yield
    finally:
        builtins.open=original_builtin_open; io.open=original_io_open; os.stat=original_stat; os.lstat=original_lstat


def verify_source(cfg: Mapping[str, Any]) -> None:
    src = cfg["source_registry"]
    pdf, reg = ROOT / src["pdf"], ROOT / src["path"]
    if not pdf.is_file() or sha(pdf) != src["pdf_sha256"]: raise RuntimeError("source PDF drift")
    value = loadj(reg)
    circuit = [f"{a}.{b}" for a, b in cfg["model"]["circuit_heads"]]
    controls = [f"{a}.{b}" for a, b in cfg["model"]["control_heads"]]
    if value["ordered_circuit"] != circuit or value["ordered_same_layer_controls"] != controls:
        raise RuntimeError("external registry/config drift")
    if len(set(circuit)) != 9 or len(set(controls)) != 9 or set(circuit) & set(controls): raise RuntimeError("invalid head registry")
    if [x.split(".")[0] for x in circuit] != [x.split(".")[0] for x in controls]: raise RuntimeError("ordered control layer mismatch")


def preservation_verify(cfg: Mapping[str, Any]) -> None:
    p = ROOT / cfg["preservation"]["v1_1_manifest"]
    if sha(p) != cfg["preservation"]["v1_1_manifest_sha256"]: raise RuntimeError("v1.1 preservation manifest drift")
    manifest = loadj(p); expected_paths = {x["path"] for x in manifest["files"]}
    for tree_root in manifest["tree_roots"]:
        actual = {x.relative_to(ROOT).as_posix() for x in (ROOT / tree_root).rglob("*") if x.is_file()}
        expected = {x for x in expected_paths if x == tree_root or x.startswith(tree_root + "/")}
        if actual != expected: raise RuntimeError(f"v1.1 tree inventory drift: {tree_root}")
    for item in manifest["files"]:
        x = ROOT / item["path"]
        if not x.is_file() or x.stat().st_size != item["bytes"] or sha(x) != item["sha256"]:
            raise RuntimeError(f"v1.1 preserved file drift: {item['path']}")
    freeze = ROOT / "configs/canonical_induction_circuit_v1_1/FREEZE.json"
    fr = loadj(freeze)
    if sha(freeze) != manifest["freeze_sha256"] or hashlib.sha256(canon(fr["candidate_inventory"])).hexdigest() != manifest["freeze_inventory_sha256"]:
        raise RuntimeError("v1.1 freeze drift")
    out = ROOT / "results/canonical_induction_circuit_v1_1_20260809"
    final = loadj(out / "final/result.json"); gate = loadj(out / "development_gate/result.json")
    blocked = loadj(out / "confirmation/BLOCKED.json")
    e = manifest["expected"]
    if final["status"] != e["final_status"] or gate["confirmation_authorized"] != e["confirmation_authorized"]:
        raise RuntimeError("v1.1 outcome drift")
    if blocked.get("model_loaded") is not False or blocked.get("confirmation_rows_loaded") is not False:
        raise RuntimeError("v1.1 confirmation opened")
    if final["representation_methods_evaluated"] or final["training_performed"] or final["technical_positive_control_confirmed"]:
        raise RuntimeError("v1.1 scope drift")
    snap = loadj(ROOT / "reports/provenance/canonical_induction_two_tier_v2_candidate/V1_1_CLAIMS.json")
    if snap["ids"] != cfg["preservation"]["required_claim_ids"] or [x["id"] for x in snap["claims"]] != snap["ids"]:
        raise RuntimeError("v1.1 claim snapshot drift")
    verify_source(cfg)


def generate_rows(cfg: Mapping[str, Any], stage: str) -> list[dict[str, Any]]:
    panel, spec = cfg["panel"], cfg["panel"][stage]
    rng = np.random.default_rng(int(spec["seed"])); rows = []
    for i in range(int(panel["rows_per_stage"])):
        vals = rng.choice(np.arange(spec["token_id_low"], spec["token_id_high_exclusive"]), panel["unique_tokens_per_row"], replace=False).tolist()
        seq, alt, sham = vals[: panel["sequence_length"]], vals[-2], vals[-1]
        clean = seq + seq[:-1]; corrupt = seq[:-1] + [alt] + seq[:-1]; sham_ids = seq[:-1] + [sham] + seq[:-1]
        rows.append({
            "stage": stage, "row_index": i, "block_index": i // panel["rows_per_block"],
            "component_id": f"{stage}:b{i // panel['rows_per_block']}:r{i}",
            "clean_ids": clean, "corrupt_ids": corrupt, "sham_ids": sham_ids,
            "target_id": seq[-1], "contrast_id": alt, "sham_id": sham,
            "query_position": len(clean) - 1, "source_successor_position": len(seq) - 1,
        })
    return rows


def raw_scenarios(cfg: Mapping[str, Any]) -> dict[str, Any]:
    # Raw scalar margins are expanded to full condition logits by calibration.
    def s(name: str, circuit: float=.2, sham: float=-.6, control: float=-.8, czero: float=.4, zzero: float=.8, clean: float=1., corrupt: float=-1., expected: str="PASS", rows: int=128):
        return {"name":name,"rows":rows,"raw_margins":{"clean":clean,"corrupt":corrupt,"full_clean":clean,"full_sham":-1.,"circuit_clean":circuit,"circuit_sham":sham,"control_clean":control,"circuit_zero":czero,"control_zero":zzero},"expected":expected}
    g=cfg["gate"]; cases=[s("positive_0_60_recovery_0_40_selectivity"),s("negative_0_10_recovery",circuit=-.8,expected="UPSTREAM_STOP"),s("support_total_below",rows=95,expected="SKYLINE_STOP"),s("support_per_block_below_total_equal",rows=96,expected="SKYLINE_STOP"),s("support_total_and_per_block_equal",rows=96,expected="PASS"),s("support_total_and_per_block_above",rows=104,expected="PASS"),s("zero_denominator",clean=-1.,expected="SKYLINE_STOP"),s("negative_denominator",clean=-2.,expected="SKYLINE_STOP")]
    cases[2]["block_counts"]=[11,12,12,12,12,12,12,12]
    cases[3]["block_counts"]=[11,13,12,12,12,12,12,12]
    cases[4]["block_counts"]=[12]*8
    cases[5]["block_counts"]=[13]*8
    # Exact below/equal/above raw-margin cases for every finite primary threshold.
    specs=[("joint_recovery",g["joint_recovery_point_min_inclusive"]),("selectivity",g["selectivity_point_min_inclusive"]),("circuit_control_margin",g["circuit_control_point_min_inclusive"]),("ablation_advantage",g["ablation_advantage_point_min_inclusive"])]
    for field,t in specs:
        for label,val in (("below",t-1e-6),("equal",t),("above",t+1e-6)):
            kw={}
            if field=="joint_recovery": kw["circuit"]=-1+2*val
            elif field=="selectivity": kw.update(circuit=.2,sham=.2-2*val)
            elif field=="circuit_control_margin": kw.update(circuit=.2,control=.2-2*val)
            else: kw.update(czero=1-2*.3,zzero=1-2*(.3-val))
            case=s(f"{field}_{label}",expected="PASS" if label!="below" else "UPSTREAM_STOP",**kw)
            if field=="ablation_advantage" and label=="equal":
                # Power-of-two-compatible raw arithmetic: 1/20 is exactly the
                # same binary64 value as the registered JSON float 0.05.
                case["raw_margins"].update({"clean":1.0,"corrupt":-19.0,"full_clean":1.0,"full_sham":-19.0,"circuit_clean":-7.0,"circuit_sham":-15.0,"control_clean":-17.0,"circuit_zero":0.0,"control_zero":1.0})
            cases.append(case)
    # Strict-lower-bound cases use a hard-coded 4-low/4-high block pattern.
    # Under the registered seeds its 0.025 bootstrap quantile is exactly the
    # affine value at base quantile 0.125; all raw margins remain inputs.
    lower_specs=[("joint_recovery",.6,g["joint_recovery_lower_strict"]),("selectivity",.35,g["selectivity_lower_strict"]),("circuit_control_margin",.35,g["circuit_control_lower_strict"]),("ablation_advantage",.1,g["ablation_advantage_lower_strict"])]
    for field,point,lower in lower_specs:
        for label,target in (("below",lower-1e-6),("equal",lower),("above",lower+1e-6)):
            scale=(point-target)/(.5-.125); low=point-.5*scale; high=low+scale
            block={}
            if field=="joint_recovery":
                rv=[low]*4+[high]*4; block["circuit_clean"]=[-1+2*x for x in rv]; block["circuit_sham"]=[-1+2*(x-.4) for x in rv]; block["control_clean"]=[-1+2*(x-.5) for x in rv]
            elif field=="selectivity": block["circuit_sham"]=[-1+2*(.6-x) for x in [low]*4+[high]*4]
            elif field=="circuit_control_margin": block["control_clean"]=[-1+2*(.6-x) for x in [low]*4+[high]*4]
            else:
                vals=[low]*4+[high]*4; block["circuit_zero"]=[.4]*8; block["control_zero"]=[1-2*(.3-x) for x in vals]
            case=s(f"{field}_lower_{label}_raw",expected="PASS" if label=="above" or (label=="equal" and field in {"selectivity","circuit_control_margin","ablation_advantage"}) else "UPSTREAM_STOP")
            case["block_raw_margins"]=block; cases.append(case)
    for name,value in (("nan_raw_condition",None),("positive_infinity_raw_condition","pos_inf"),("negative_infinity_raw_condition","neg_inf")):
        case=s(name,expected="TECHNICAL_INVALID"); case["raw_margins"]["circuit_clean"]=value; cases.append(case)
    return {"schema_version":"canonical_induction_two_tier_v2_raw_fixture","scenarios":cases}


def threshold_oracles(cfg:Mapping[str,Any])->list[dict[str,Any]]:
    g=cfg["gate"]; specs=[("skyline_point",g["skyline_point_min_inclusive"],True),("skyline_lower",g["skyline_lower_strict"],False),("joint_point",g["joint_recovery_point_min_inclusive"],True),("joint_lower",g["joint_recovery_lower_strict"],False),("selectivity_point",g["selectivity_point_min_inclusive"],True),("selectivity_lower",g["selectivity_lower_strict"],False),("circuit_control_point",g["circuit_control_point_min_inclusive"],True),("circuit_control_lower",g["circuit_control_lower_strict"],False),("ablation_point",g["ablation_advantage_point_min_inclusive"],True),("ablation_lower",g["ablation_advantage_lower_strict"],False)]
    out=[]
    for name,t,inclusive in specs:
        for relation,value in (("below",np.nextafter(t,-np.inf)),("equal",t),("above",np.nextafter(t,np.inf))):
            actual=bool(value>=t) if inclusive else bool(value>t); expected=relation in ({"equal","above"} if inclusive else {"above"})
            out.append({"name":name,"relation":relation,"threshold":t,"value":float(value),"inclusive":inclusive,"actual":actual,"expected":expected,"pass":actual==expected})
    return out


def apply_head_intervention(base: torch.Tensor, head_size: int, replacements: Mapping[int, torch.Tensor], zero_heads: Sequence[int]) -> torch.Tensor:
    changed = base.clone() if replacements or zero_heads else base
    for head, donor in replacements.items(): changed[..., head*head_size:(head+1)*head_size] = donor
    for head in zero_heads: changed[..., head*head_size:(head+1)*head_size] = 0
    return changed


def hook_fixture() -> tuple[dict[str, Any], dict[str, np.ndarray]]:
    base=np.arange(2*3*12,dtype=np.float32).reshape(2,3,12); donor=np.full((2,3,2),-7,dtype=np.float32)
    fixture={"schema_version":"canonical_induction_two_tier_v2_hook_fixture","shape":[2,3,12],"head_size":2,"replacement_heads":[1],"zero_heads":[4],"donor_value":-7.0}
    expected=base.copy(); expected[...,2:4]=-7.0; expected[...,8:10]=0.0
    return fixture,{"base":base,"donor":donor,"expected":expected}


def tiny_hook_integration() -> dict[str,bool]:
    from types import SimpleNamespace
    class TinyAttn(torch.nn.Module):
        def __init__(self): super().__init__(); self.c_proj=torch.nn.Identity()
        def forward(self,x): return self.c_proj(x)
    class TinyLayer(torch.nn.Module):
        def __init__(self): super().__init__(); self.attn=TinyAttn()
        def forward(self,x): return self.attn(x)
    class TinyTransformer(torch.nn.Module):
        def __init__(self): super().__init__(); self.h=torch.nn.ModuleList([TinyLayer(),TinyLayer()]); self.ln_f=torch.nn.Identity()
    class TinyModel(torch.nn.Module):
        def __init__(self): super().__init__(); self.transformer=TinyTransformer(); self.anchor=torch.nn.Parameter(torch.zeros(()))
        def forward(self,input_ids,**_kwargs):
            x=input_ids.float()[...,None]+torch.arange(12,device=input_ids.device,dtype=torch.float32)
            for layer in self.transformer.h: x=layer(x)
            return SimpleNamespace(logits=self.transformer.ln_f(x)+self.anchor)
    cfg={"model":{"batch_size":2,"head_size":2}}
    rows=[{"clean_ids":[1,2,3],"corrupt_ids":[7,8,9]},{"clean_ids":[4,5,6],"corrupt_ids":[10,11,12]}]
    model=TinyModel().eval(); heads=[[0,1],[1,3]]
    clean=run_condition(model,cfg,rows,"clean",capture_heads=heads,capture_residual=True)
    corrupt=run_condition(model,cfg,rows,"corrupt",capture_heads=heads)
    donors={f"{a}.{b}":clean["heads"][f"{a}.{b}"] for a,b in heads}
    patched=run_condition(model,cfg,rows,"corrupt",replacement=donors)
    zeroed=run_condition(model,cfg,rows,"corrupt",zero_heads=heads)
    manual=corrupt["logits"].copy(); manual[:,2:4]=clean["logits"][:,2:4]; manual[:,6:8]=clean["logits"][:,6:8]
    manual_zero=corrupt["logits"].copy(); manual_zero[:,2:4]=0; manual_zero[:,6:8]=0
    perm={k:v[::-1].copy() for k,v in donors.items()}; permuted=run_condition(model,cfg,rows,"corrupt",replacement=perm)
    return {"capture_exact":bool(np.array_equal(clean["heads"]["0.1"],np.asarray([[[3,4],[4,5],[5,6]],[[6,7],[7,8],[8,9]]],dtype=np.float32))),"layer_registry_and_composition":bool(np.array_equal(patched["logits"],manual)),"all_position_zero":bool(np.array_equal(zeroed["logits"],manual_zero)),"row_permutation_detected":bool(not np.array_equal(permuted["logits"],manual)),"residual_capture":bool(np.array_equal(clean["residual"],clean["logits"]))}


def prepare(config: Path) -> None:
    cfg=require_config(config); preservation_verify(cfg); root=ROOT/cfg["runtime"]["prepared_root"]
    if root.exists(): raise FileExistsError(root)
    root.mkdir(parents=True)
    stages={x:generate_rows(cfg,x) for x in ("development","confirmation")}
    for stage,rows in stages.items(): writejl(root/f"{stage}.jsonl",rows)
    if {tuple(x["clean_ids"]) for x in stages["development"]} & {tuple(x["clean_ids"]) for x in stages["confirmation"]}: raise RuntimeError("stage overlap")
    old=readjl(ROOT/"data/canonical_induction_circuit_v1_prepared/development.jsonl")
    if {tuple(x["clean_ids"]) for x in old} & {tuple(x["clean_ids"]) for x in stages["development"]}: raise RuntimeError("opened v1.1 overlap")
    (root/"RAW_CALIBRATION.json").write_bytes(canon(raw_scenarios(cfg))+b"\n")
    (root/"THRESHOLD_ORACLES.json").write_bytes(canon({"schema_version":"canonical_induction_two_tier_v2_threshold_oracles","oracles":threshold_oracles(cfg)})+b"\n")
    fixture,arrays=hook_fixture(); (root/"HOOK_FIXTURE.json").write_bytes(canon(fixture)+b"\n"); np.savez(root/"HOOK_EXPECTED.npz",**arrays)
    files={x.name:sha(x) for x in sorted(root.iterdir()) if x.is_file()}
    exjson(root/"PRESCORE.json",{"schema_version":"canonical_induction_two_tier_v2_prescore","selection_firewall":"ALGORITHMIC_FRESH_TOKEN_IDS_NO_MODEL_FORWARD","rows":{"development":128,"confirmation":128},"blocks":8,"rows_per_block":16,"v1_1_development_prompt_overlap":0,"stage_prompt_overlap":0,"files":files})


def verify_prepared(cfg: Mapping[str, Any], include_confirmation: bool=True) -> None:
    root=ROOT/cfg["runtime"]["prepared_root"]; rec=loadj(root/"PRESCORE.json")
    if rec["selection_firewall"]!="ALGORITHMIC_FRESH_TOKEN_IDS_NO_MODEL_FORWARD" or rec["rows"]!={"development":128,"confirmation":128}: raise RuntimeError("prescore drift")
    for name,digest in rec["files"].items():
        if not include_confirmation and name=="confirmation.jsonl": continue
        if sha(root/name)!=digest: raise RuntimeError(f"prepared drift: {name}")


def _raw_outputs(m: Mapping[str, Any], n: int, block_counts:Sequence[int]|None=None, block_margins:Mapping[str,Sequence[Any]]|None=None) -> tuple[list[dict[str, Any]],dict[str,np.ndarray]]:
    if block_counts is None:
        block_counts=[16]*8 if n==128 else [16]*(n//16)+([n%16] if n%16 else [])
    if sum(block_counts)!=n: raise ValueError("raw block counts do not sum to n")
    rows=[]
    for b,count in enumerate(block_counts):
        for _ in range(count):
            i=len(rows); rows.append({"stage":"calibration","row_index":i,"block_index":b,"component_id":f"cal:b{b}:r{i}","target_id":0,"contrast_id":1,"sham_id":2})
    outputs={}
    for key,val in m.items():
        values=[]
        for b,count in enumerate(block_counts):
            raw=(block_margins or {}).get(key,[val]*len(block_counts))[b]
            if raw is None: x=np.nan
            elif raw=="pos_inf": x=np.inf
            elif raw=="neg_inf": x=-np.inf
            else: x=float(raw)
            values.extend([x]*count)
        a=np.zeros((n,3),dtype=np.float64); a[:,0]=values; outputs[key]=a
    return rows,outputs


def margin(logits: np.ndarray, rows: Sequence[Mapping[str, Any]]) -> np.ndarray:
    return np.asarray([logits[i,int(row["target_id"])]-logits[i,int(row["contrast_id"])] for i,row in enumerate(rows)],dtype=np.float64)


def compute_rows(cfg: Mapping[str, Any], rows: Sequence[Mapping[str, Any]], outputs: Mapping[str,np.ndarray], extras: Mapping[str,np.ndarray]|None=None) -> list[dict[str,Any]]:
    ms={k:margin(v,rows) for k,v in outputs.items()}
    result=[]
    for i,row in enumerate(rows):
        live=[float(ms[k][i]) for k in ("clean","corrupt","full_clean","full_sham","circuit_clean","circuit_sham","control_clean","circuit_zero","control_zero")]
        finite=all(np.isfinite(x) for x in live); effect=min(ms["clean"][i],-ms["corrupt"][i]); eligible=bool(finite and ms["clean"][i]>0 and ms["corrupt"][i]<0 and effect>cfg["gate"]["behavior_effect_floor_strict"])
        denom=ms["full_clean"][i]-ms["corrupt"][i]; candidate=bool(eligible and np.isfinite(denom) and denom>cfg["gate"]["positive_denominator_strict"])
        def norm(a,b="corrupt"): return float((ms[a][i]-ms[b][i])/denom) if candidate else None
        r=norm("circuit_clean"); h=norm("circuit_sham"); c=norm("control_clean")
        aa=float((ms["clean"][i]-ms["circuit_zero"][i])/denom) if candidate else None
        bb=float((ms["clean"][i]-ms["control_zero"][i])/denom) if candidate else None
        derived=(norm("full_clean"),r,h,c,aa,bb,None if r is None or h is None else r-h,None if r is None or c is None else r-c,None if aa is None or bb is None else aa-bb)
        derived_finite=all(x is not None and np.isfinite(x) for x in derived) if candidate else True
        finite=bool(finite and derived_finite); in_g=bool(candidate and derived_finite)
        item={k:row[k] for k in ("stage","row_index","block_index","component_id")}|{
            "live_finite":finite,"behavior_eligible":eligible,"gate_cohort":in_g,"effect":float(effect) if np.isfinite(effect) else None,"ceiling_denominator":float(denom) if np.isfinite(denom) else None,
            "clean_margin":float(ms["clean"][i]) if np.isfinite(ms["clean"][i]) else None,"corrupt_margin":float(ms["corrupt"][i]) if np.isfinite(ms["corrupt"][i]) else None,
            "skyline_recovery":norm("full_clean"),"joint_recovery":r,"sham_recovery":h,"control_recovery":c,
            "selectivity":None if r is None or h is None else r-h,"circuit_control_margin":None if r is None or c is None else r-c,
            "circuit_ablation":aa,"control_ablation":bb,"ablation_advantage":None if aa is None or bb is None else aa-bb,
        }
        result.append(item)
    return result


def equal_block_interval(rows: Sequence[Mapping[str,Any]], field: str, cfg: Mapping[str,Any], stage: str, gate_only: bool=True) -> dict[str,Any]|None:
    valid=[r for r in rows if (not gate_only or r.get("gate_cohort")) and r.get(field) is not None and np.isfinite(r[field])]
    grouped={b:[float(r[field]) for r in valid if int(r["block_index"])==b] for b in range(8)}
    if any(not grouped[b] for b in range(8)): return None
    point=float(np.mean([np.mean(grouped[b]) for b in range(8)])); rng=np.random.default_rng(endpoint_seed(cfg["seed"],stage,field)); draws=[]
    for _ in range(cfg["gate"]["bootstrap_draws"]):
        chosen=rng.choice(np.arange(8),8,replace=True); vals=[]
        for b0 in chosen:
            b=int(b0); arr=np.asarray(grouped[b]); idx=rng.integers(0,len(arr),size=len(arr)); vals.append(float(np.mean(arr[idx])))
        draws.append(float(np.mean(vals)))
    return {"point":point,"lower":float(np.quantile(draws,.025,method="linear")),"upper":float(np.quantile(draws,.975,method="linear")),"draws":len(draws),"weighting":"equal_block_paired_hierarchical"}


def summarize(cfg: Mapping[str,Any], rows: Sequence[Mapping[str,Any]], stage: str) -> dict[str,Any]:
    counts={str(b):sum(bool(r.get("gate_cohort")) for r in rows if int(r["block_index"])==b) for b in range(8)}
    technical=all(bool(r.get("live_finite")) for r in rows)
    support=sum(counts.values())>=cfg["gate"]["minimum_gate_rows_total"] and all(v>=cfg["gate"]["minimum_gate_rows_per_block"] for v in counts.values())
    metrics={f:equal_block_interval(rows,f,cfg,stage) for f in GATE_FIELDS}
    g=cfg["gate"]
    skyline=bool(technical and support and metrics["skyline_recovery"] and metrics["skyline_recovery"]["point"]>=g["skyline_point_min_inclusive"] and metrics["skyline_recovery"]["lower"]>g["skyline_lower_strict"])
    upstream=bool(skyline and all(metrics[f] is not None for f in GATE_FIELDS[1:]) and metrics["joint_recovery"]["point"]>=g["joint_recovery_point_min_inclusive"] and metrics["joint_recovery"]["lower"]>g["joint_recovery_lower_strict"] and metrics["selectivity"]["point"]>=g["selectivity_point_min_inclusive"] and metrics["selectivity"]["lower"]>g["selectivity_lower_strict"] and metrics["circuit_control_margin"]["point"]>=g["circuit_control_point_min_inclusive"] and metrics["circuit_control_margin"]["lower"]>g["circuit_control_lower_strict"] and metrics["ablation_advantage"]["point"]>=g["ablation_advantage_point_min_inclusive"] and metrics["ablation_advantage"]["lower"]>g["ablation_advantage_lower_strict"])
    if not technical: status="TECHNICAL_INVALID_STOP"
    elif not skyline: status=f"{stage.upper()}_SKYLINE_STOP"
    elif not upstream: status=f"{stage.upper()}_UPSTREAM_SET_STOP"
    else: status="PASS"
    return {"stage":stage,"technical_valid":technical,"gate_cohort_total":sum(counts.values()),"gate_cohort_per_block":counts,"support_pass":support,"metrics":metrics,"tier_a_pass":skyline,"tier_b_pass":upstream,"status":status,"external_set_scope":"FIGURE2_UPSTREAM_SET_NOT_COMPLETE_RANDOM_TOKEN_CIRCUIT"}


def replay_calibration(cfg: Mapping[str,Any]) -> dict[str,Any]:
    root=ROOT/cfg["runtime"]["prepared_root"]; fixture=loadj(root/"RAW_CALIBRATION.json"); raw_results=[]
    for scenario in fixture["scenarios"]:
        rows,outs=_raw_outputs(scenario["raw_margins"],scenario["rows"],scenario.get("block_counts"),scenario.get("block_raw_margins")); metrics=compute_rows(cfg,rows,outs); summary=summarize(cfg,metrics,"calibration")
        if not all(x["live_finite"] for x in metrics): actual="TECHNICAL_INVALID"
        elif not summary["tier_a_pass"]: actual="SKYLINE_STOP"
        elif not summary["tier_b_pass"]: actual="UPSTREAM_STOP"
        else: actual="PASS"
        raw_results.append({"name":scenario["name"],"expected":scenario["expected"],"actual":actual,"pass":actual==scenario["expected"]})
    with np.load(root/"HOOK_EXPECTED.npz") as z: base=z["base"].copy(); donor=z["donor"].copy(); expected=z["expected"].copy()
    actual=apply_head_intervention(torch.from_numpy(base),2,{1:torch.from_numpy(donor)},[4]).numpy()
    outside=np.ones(base.shape[-1],dtype=bool); outside[2:4]=False; outside[8:10]=False
    hook={"bitwise_against_independent_expected":bool(np.array_equal(actual,expected)),"outside_slice_invariant":bool(np.array_equal(actual[...,outside],base[...,outside])),"replacement_exact":bool(np.array_equal(actual[...,2:4],donor)),"zero_exact":bool(np.array_equal(actual[...,8:10],np.zeros_like(actual[...,8:10])))}
    integration=tiny_hook_integration(); thresholds=loadj(root/"THRESHOLD_ORACLES.json")["oracles"]
    if thresholds!=threshold_oracles(cfg): raise RuntimeError("threshold comparator fixture drift")
    return {"raw_results":raw_results,"threshold_oracles":thresholds,"hook_result":hook,"hook_integration":integration,"pass":all(x["pass"] for x in raw_results) and all(x["pass"] for x in thresholds) and all(hook.values()) and all(integration.values())}


def calibrate(config: Path) -> None:
    cfg=require_config(config); verify_prepared(cfg); target=ROOT/cfg["runtime"]["calibration"]
    if target.exists(): raise FileExistsError(target)
    replay=replay_calibration(cfg); root=ROOT/cfg["runtime"]["prepared_root"]
    payload={"schema_version":"canonical_induction_two_tier_v2_calibration","status":"PASS" if replay["pass"] else "CALIBRATION_BLOCK","implementation_sha256":sha(Path(__file__)),"config_sha256":sha(config),"raw_fixture_sha256":sha(root/"RAW_CALIBRATION.json"),"threshold_fixture_sha256":sha(root/"THRESHOLD_ORACLES.json"),"hook_fixture_sha256":sha(root/"HOOK_FIXTURE.json"),"hook_expected_sha256":sha(root/"HOOK_EXPECTED.npz"),"raw_result_sha256":hashlib.sha256(canon(replay["raw_results"])).hexdigest(),"threshold_result_sha256":hashlib.sha256(canon(replay["threshold_oracles"])).hexdigest(),"hook_result_sha256":hashlib.sha256(canon(replay["hook_result"])).hexdigest(),"hook_integration_result_sha256":hashlib.sha256(canon(replay["hook_integration"])).hexdigest(),"replay":replay}
    exjson(target,payload)
    if not replay["pass"]: raise RuntimeError("calibration failed")


def validate_calibration(config: Path,cfg: Mapping[str,Any]) -> dict[str,Any]:
    root=ROOT/cfg["runtime"]["prepared_root"]; rec=loadj(ROOT/cfg["runtime"]["calibration"]); replay=replay_calibration(cfg)
    expected={"schema_version":"canonical_induction_two_tier_v2_calibration","status":"PASS" if replay["pass"] else "CALIBRATION_BLOCK","implementation_sha256":sha(Path(__file__)),"config_sha256":sha(config),"raw_fixture_sha256":sha(root/"RAW_CALIBRATION.json"),"threshold_fixture_sha256":sha(root/"THRESHOLD_ORACLES.json"),"hook_fixture_sha256":sha(root/"HOOK_FIXTURE.json"),"hook_expected_sha256":sha(root/"HOOK_EXPECTED.npz"),"raw_result_sha256":hashlib.sha256(canon(replay["raw_results"])).hexdigest(),"threshold_result_sha256":hashlib.sha256(canon(replay["threshold_oracles"])).hexdigest(),"hook_result_sha256":hashlib.sha256(canon(replay["hook_result"])).hexdigest(),"hook_integration_result_sha256":hashlib.sha256(canon(replay["hook_integration"])).hexdigest(),"replay":replay}
    if rec!=expected or not replay["pass"]: raise RuntimeError("calibration stale or failed")
    return rec


def cache_preflight(config: Path) -> None:
    cfg=require_config(config); require_offline(); from huggingface_hub import snapshot_download
    from transformers import AutoConfig, AutoTokenizer
    m=cfg["model"]; snapshot=Path(snapshot_download(m["name"],revision=m["revision"],local_files_only=True)); AutoConfig.from_pretrained(m["name"],revision=m["revision"],local_files_only=True); AutoTokenizer.from_pretrained(m["name"],revision=m["revision"],local_files_only=True)
    names={"config.json","generation_config.json","tokenizer.json","tokenizer_config.json","special_tokens_map.json","vocab.json","merges.txt","pytorch_model.bin","model.safetensors"}
    files=[{"name":p.name,"bytes":p.stat().st_size,"sha256":sha(p),"resolved_blob":str(p.resolve())} for p in sorted(snapshot.iterdir()) if p.is_file() and p.name in names]
    if not any(x["name"].endswith((".bin",".safetensors")) for x in files): raise RuntimeError("cached weights absent")
    payload={"schema_version":"canonical_induction_two_tier_v2_cache","status":"PASS","revision":m["revision"],"snapshot":str(snapshot),"files":files}
    target=ROOT/cfg["runtime"]["cache_attestation"]
    if target.exists():
        if loadj(target)!=payload: raise RuntimeError("cache attestation drift")
    else: exjson(target,payload)


def verify_cache(cfg: Mapping[str,Any]) -> dict[str,Any]:
    target=ROOT/cfg["runtime"]["cache_attestation"]; rec=loadj(target)
    if rec.get("status")!="PASS" or rec.get("revision")!=cfg["model"]["revision"]: raise RuntimeError("cache attestation metadata drift")
    snapshot=Path(rec["snapshot"])
    if not snapshot.is_dir(): raise RuntimeError("attested snapshot absent")
    for item in rec["files"]:
        p=Path(item["resolved_blob"])
        if not p.is_file() or p.stat().st_size!=item["bytes"] or sha(p)!=item["sha256"]: raise RuntimeError(f"cached blob drift: {item['name']}")
        linked=snapshot/item["name"]
        if not linked.is_file() or linked.resolve()!=p.resolve(): raise RuntimeError(f"snapshot resolution drift: {item['name']}")
    return rec


def candidate_inventory(config: Path,cfg: Mapping[str,Any]) -> list[dict[str,Any]]:
    paths=[ROOT/x for x in cfg["candidate_files"]]; paths += [p for p in (ROOT/cfg["runtime"]["prepared_root"]).rglob("*") if p.is_file()]
    records=[]
    for p in sorted(set(paths),key=lambda x:x.relative_to(ROOT).as_posix()):
        if not p.is_file(): raise RuntimeError(f"candidate artifact absent: {p.relative_to(ROOT)}")
        records.append({"path":p.relative_to(ROOT).as_posix(),"bytes":p.stat().st_size,"sha256":sha(p)})
    return records


def validate_scope(cfg: Mapping[str,Any]) -> None:
    if cfg["model"]["circuit_heads"] != [[0,1],[0,10],[3,0],[2,2],[4,11],[5,5],[5,8],[5,9],[6,9]]: raise RuntimeError("circuit registry drift")
    if cfg["model"]["control_heads"] != [[0,0],[0,2],[3,1],[2,0],[4,0],[5,0],[5,1],[5,2],[6,0]]: raise RuntimeError("control registry drift")
    for k in ("general_method_claim","representation_methods","training","automatic_method_authorization","v1_1_retry"):
        if cfg["scope"][k]: raise RuntimeError(f"forbidden scope: {k}")


def candidate_preflight(config: Path) -> None:
    cfg=require_config(config); preservation_verify(cfg); verify_prepared(cfg); verify_source(cfg); validate_scope(cfg); rec=validate_calibration(config,cfg)
    for key in ("output_root","provenance_root","freeze","review_binding"):
        if (ROOT/cfg["runtime"][key]).exists(): raise RuntimeError(f"must be absent: {key}")
    target=ROOT/cfg["runtime"]["candidate_preflight_attestation"]
    if target.exists(): raise FileExistsError(target)
    cache=ROOT/cfg["runtime"]["cache_attestation"]; verify_cache(cfg)
    exjson(target,{"schema_version":"canonical_induction_two_tier_v2_candidate_preflight","status":"PASS","implementation_sha256":sha(Path(__file__)),"config_sha256":sha(config),"calibration_sha256":sha(ROOT/cfg["runtime"]["calibration"]),"calibration_replay_sha256":hashlib.sha256(canon(rec["replay"])).hexdigest(),"preservation_sha256":sha(ROOT/cfg["preservation"]["v1_1_manifest"]),"source_registry_sha256":sha(ROOT/cfg["source_registry"]["path"]),"cache_attestation_sha256":sha(cache)})


def validate_candidate_attestation(config: Path,cfg: Mapping[str,Any]) -> None:
    target=ROOT/cfg["runtime"]["candidate_preflight_attestation"]; rec=loadj(target); cal=validate_calibration(config,cfg); cache=ROOT/cfg["runtime"]["cache_attestation"]
    exp={"schema_version":"canonical_induction_two_tier_v2_candidate_preflight","status":"PASS","implementation_sha256":sha(Path(__file__)),"config_sha256":sha(config),"calibration_sha256":sha(ROOT/cfg["runtime"]["calibration"]),"calibration_replay_sha256":hashlib.sha256(canon(cal["replay"])).hexdigest(),"preservation_sha256":sha(ROOT/cfg["preservation"]["v1_1_manifest"]),"source_registry_sha256":sha(ROOT/cfg["source_registry"]["path"]),"cache_attestation_sha256":sha(cache)}
    if rec!=exp: raise RuntimeError("candidate preflight attestation drift")


def freeze(config: Path) -> None:
    cfg=require_config(config); validate_candidate_attestation(config,cfg); preservation_verify(cfg); validate_scope(cfg)
    review=ROOT/cfg["runtime"]["candidate_review"]
    if not review.is_file() or review.read_text().splitlines()[0]!="VERDICT: SHIP": raise RuntimeError("candidate SHIP required")
    target=ROOT/cfg["runtime"]["freeze"]
    if target.exists(): raise FileExistsError(target)
    inv=candidate_inventory(config,cfg)
    exjson(target,{"schema_version":"canonical_induction_two_tier_v2_freeze","namespace":cfg["namespace"],"config_sha256":sha(config),"candidate_inventory":inv,"candidate_inventory_sha256":hashlib.sha256(canon(inv)).hexdigest(),"confirmation_payload":next(x for x in inv if x["path"].endswith("confirmation.jsonl")),"representation_methods":False,"training":False,"one_shot":True})


def verify_freeze(config: Path,cfg:Mapping[str,Any]|None=None,include_confirmation:bool=False) -> dict[str,Any]:
    cfg=cfg or require_config(config); p=ROOT/cfg["runtime"]["freeze"]; rec=loadj(p)
    if rec["config_sha256"]!=sha(config) or hashlib.sha256(canon(rec["candidate_inventory"])).hexdigest()!=rec["candidate_inventory_sha256"]: raise RuntimeError("freeze digest drift")
    confirmation=(ROOT/cfg["runtime"]["prepared_root"]/"confirmation.jsonl").relative_to(ROOT).as_posix()
    for item in rec["candidate_inventory"]:
        if not include_confirmation and item["path"]==confirmation: continue
        x=ROOT/item["path"]
        if not x.is_file() or x.stat().st_size!=item["bytes"] or sha(x)!=item["sha256"]: raise RuntimeError(f"frozen drift: {item['path']}")
    preservation_verify(cfg); validate_scope(cfg)
    return rec


def bind_review(config: Path) -> None:
    cfg=require_config(config); fr=ROOT/cfg["runtime"]["freeze"]; c=ROOT/cfg["runtime"]["candidate_review"]; f=ROOT/cfg["runtime"]["frozen_review"]; target=ROOT/cfg["runtime"]["review_binding"]
    if target.exists(): raise FileExistsError(target)
    if c.read_text().splitlines()[0]!="VERDICT: SHIP" or f.read_text().splitlines()[0]!="VERDICT: SHIP": raise RuntimeError("both first-line SHIP required")
    exjson(target,{"status":"SHIP","candidate_verdict":"SHIP","frozen_verdict":"SHIP","freeze_sha256":sha(fr),"candidate_review_sha256":sha(c),"frozen_review_sha256":sha(f)})


def review_binding(config: Path) -> None:
    cfg=require_config(config); sealed=ROOT/cfg["runtime"]["prepared_root"]/"confirmation.jsonl"
    with deny_path_access(sealed):
        rec=verify_freeze(config,cfg,include_confirmation=False); fr=ROOT/cfg["runtime"]["freeze"]; c=ROOT/cfg["runtime"]["candidate_review"]; f=ROOT/cfg["runtime"]["frozen_review"]; b=ROOT/cfg["runtime"]["review_binding"]
        exp={"status":"SHIP","candidate_verdict":"SHIP","frozen_verdict":"SHIP","freeze_sha256":sha(fr),"candidate_review_sha256":sha(c),"frozen_review_sha256":sha(f)}
        if loadj(b)!=exp or hashlib.sha256(canon(rec["candidate_inventory"])).hexdigest()!=rec["candidate_inventory_sha256"]: raise RuntimeError("review binding drift")


def pre_gate(config: Path) -> None:
    cfg=require_config(config)
    for key in ("output_root","provenance_root"):
        if (ROOT/cfg["runtime"][key]).exists(): raise RuntimeError(f"runtime exists: {key}")
    sealed=ROOT/cfg["runtime"]["prepared_root"]/"confirmation.jsonl"
    with deny_path_access(sealed): review_binding(config); verify_freeze(config,cfg,include_confirmation=False); verify_cache(cfg)


def verify_freeze_pre_gate(config:Path)->dict[str,Any]:
    cfg=require_config(config); sealed=ROOT/cfg["runtime"]["prepared_root"]/"confirmation.jsonl"
    with deny_path_access(sealed): return verify_freeze(config,cfg,include_confirmation=False)


def seed_all(seed:int)->None:
    random.seed(seed); np.random.seed(seed); torch.manual_seed(seed); torch.cuda.manual_seed_all(seed)
    torch.backends.cuda.matmul.allow_tf32=False; torch.backends.cudnn.allow_tf32=False; torch.set_float32_matmul_precision("highest"); torch.use_deterministic_algorithms(True)


def validate_launch(cfg: Mapping[str,Any],token:str) -> dict[str,Any]:
    p=ROOT/cfg["runtime"]["provenance_root"]/"launch_manifest.json"; rec=loadj(p)
    keys={"schema_version","launch_token","launcher_pid","started_ns","config","config_sha256","freeze_sha256","review_binding_sha256","cache_attestation_sha256","gpu","gpu_lock_path","gpu_lock_inode","gpu_lock_held","before_lock_evidence","post_lock_recheck","selection_nonce","session","representation_methods","training","external_set_scope"}
    gpu_keys={"physical_index","uuid","memory_used_mib","memory_total_mib","utilization_percent","compute_processes"}
    def is_hex(value:Any,length:int)->bool:
        try: return isinstance(value,str) and len(value)==length and int(value,16)>=0
        except ValueError: return False
    if set(rec)!=keys or rec.get("schema_version")!="canonical_induction_two_tier_v2_launch" or set(rec.get("gpu",{}))!=gpu_keys or set(rec.get("before_lock_evidence",{}))!={"index","uuid","memory_used_mib","memory_total_mib","utilization_percent","compute_processes"}: raise RuntimeError("launch manifest schema mismatch")
    gpu,before=rec["gpu"],rec["before_lock_evidence"]
    if not is_hex(rec.get("launch_token"),64) or not is_hex(rec.get("selection_nonce"),32) or not isinstance(rec.get("launcher_pid"),int) or rec["launcher_pid"]<=0 or not isinstance(rec.get("started_ns"),int) or rec["started_ns"]<=0 or rec.get("session")!=cfg["runtime"]["tmux_session"] or rec.get("post_lock_recheck") is not True or rec.get("representation_methods") is not False or rec.get("training") is not False or rec.get("external_set_scope")!="FIGURE2_UPSTREAM_SET_NOT_COMPLETE_RANDOM_TOKEN_CIRCUIT": raise RuntimeError("launch manifest fixed-field mismatch")
    if not isinstance(gpu["physical_index"],int) or gpu["physical_index"]<0 or not isinstance(gpu["uuid"],str) or not gpu["uuid"].startswith("GPU-") or gpu["memory_total_mib"]<=0 or gpu["memory_used_mib"]<0 or gpu["memory_used_mib"]>=cfg["runtime"]["gpu_memory_used_max_mib_exclusive"] or gpu["utilization_percent"]<0 or gpu["utilization_percent"]>=cfg["runtime"]["gpu_utilization_max_percent_exclusive"] or gpu["compute_processes"]!=0: raise RuntimeError("launch post-lock GPU evidence invalid")
    if before["index"]!=gpu["physical_index"] or before["uuid"]!=gpu["uuid"] or before["memory_total_mib"]!=gpu["memory_total_mib"] or before["memory_used_mib"]<0 or before["memory_used_mib"]>=cfg["runtime"]["gpu_memory_used_max_mib_exclusive"] or before["utilization_percent"]<0 or before["utilization_percent"]>=cfg["runtime"]["gpu_utilization_max_percent_exclusive"] or before["compute_processes"]!=0: raise RuntimeError("launch pre-lock GPU evidence invalid")
    registered_lock=Path(cfg["runtime"]["gpu_lock_root"])/f"{gpu['uuid']}.lock"
    if not isinstance(rec.get("gpu_lock_path"),str) or Path(rec["gpu_lock_path"])!=registered_lock or not isinstance(rec.get("gpu_lock_inode"),int) or rec["gpu_lock_inode"]<=0 or rec.get("gpu_lock_held") is not True: raise RuntimeError("launch GPU lock evidence invalid")
    expected_config=DEFAULT.relative_to(ROOT).as_posix()
    if rec.get("config")!=expected_config or rec.get("config_sha256")!=sha(DEFAULT): raise RuntimeError("launch config binding mismatch")
    if rec.get("launch_token")!=token or not rec.get("gpu_lock_held") or os.environ.get("CUDA_VISIBLE_DEVICES")!=rec["gpu"]["uuid"] or os.environ.get("EXPECTED_GPU_UUID")!=rec["gpu"]["uuid"]: raise RuntimeError("launch token/UUID mismatch")
    if rec.get("freeze_sha256")!=sha(ROOT/cfg["runtime"]["freeze"]) or rec.get("review_binding_sha256")!=sha(ROOT/cfg["runtime"]["review_binding"]) or rec.get("cache_attestation_sha256")!=sha(ROOT/cfg["runtime"]["cache_attestation"]): raise RuntimeError("launch frozen-lineage hash mismatch")
    verify_cache(cfg)
    pid=int(rec["launcher_pid"])
    try: os.kill(pid,0)
    except OSError as e: raise RuntimeError("launcher PID not live") from e
    lock=Path(rec["gpu_lock_path"])
    if not lock.is_file() or lock.stat().st_ino!=int(rec["gpu_lock_inode"]): raise RuntimeError("GPU lock inode drift")
    held=False
    for fd in Path(f"/proc/{pid}/fd").iterdir():
        try:
            if fd.resolve()==lock.resolve(): held=True; break
        except FileNotFoundError: continue
    if not held: raise RuntimeError("launcher no longer holds registered GPU lock descriptor")
    rows=subprocess.check_output(["nvidia-smi","--query-gpu=index,uuid","--format=csv,noheader,nounits"],text=True).splitlines()
    mapping={int(x.split(",")[0].strip()):x.split(",")[1].strip() for x in rows}
    if mapping.get(int(rec["gpu"]["physical_index"]))!=rec["gpu"]["uuid"]: raise RuntimeError("physical GPU UUID mapping drift")
    if os.environ.get("CUBLAS_WORKSPACE_CONFIG")!=cfg["qa"]["cublas_workspace_config"]: raise RuntimeError("CUBLAS config drift")
    return rec


def gpu_guard(cfg: Mapping[str,Any],launch:Mapping[str,Any]) -> torch.device:
    if not torch.cuda.is_available() or torch.cuda.device_count()!=1: raise RuntimeError("one UUID-pinned CUDA device required")
    return torch.device("cuda:0")


def load_model(cfg:Mapping[str,Any],device:torch.device)->Any:
    require_offline(); verify_cache(cfg); from transformers import AutoModelForCausalLM
    m=cfg["model"]; model=AutoModelForCausalLM.from_pretrained(m["name"],revision=m["revision"],local_files_only=True,torch_dtype=torch.float32,attn_implementation="eager").to(device).eval(); model.config.use_cache=False; return model


def batch_ids(rows:Sequence[Mapping[str,Any]],condition:str,device:torch.device)->torch.Tensor:
    return torch.tensor([r[f"{condition}_ids"] for r in rows],dtype=torch.long,device=device)


@torch.inference_mode()
def run_condition(model:Any,cfg:Mapping[str,Any],rows:Sequence[Mapping[str,Any]],condition:str,capture_heads:Sequence[Sequence[int]]=(),replacement:Mapping[str,np.ndarray]|None=None,zero_heads:Sequence[Sequence[int]]=(),capture_residual:bool=False,residual_replacement:np.ndarray|None=None)->dict[str,Any]:
    replacement=replacement or {}; logits=[]; head_out={f"{a}.{b}":[] for a,b in capture_heads}; residual=[]; bs=cfg["model"]["batch_size"]; hs=cfg["model"]["head_size"]
    layers=sorted(set([a for a,_ in capture_heads]+[a for a,_ in zero_heads]+[int(k.split('.')[0]) for k in replacement]))
    for start in range(0,len(rows),bs):
        batch=rows[start:start+bs]; ids=batch_ids(batch,condition,next(model.parameters()).device); handles=[]
        for layer in layers:
            cap=[h for l,h in capture_heads if l==layer]; zeros=[h for l,h in zero_heads if l==layer]; reps={int(k.split('.')[1]):torch.as_tensor(v[start:start+len(batch)],device=ids.device) for k,v in replacement.items() if int(k.split('.')[0])==layer}
            def hook(_module,args,layer=layer,cap=cap,zeros=zeros,reps=reps):
                x=args[0]
                for h in cap: head_out[f"{layer}.{h}"].append(x[...,h*hs:(h+1)*hs].detach().float().cpu().numpy())
                return (apply_head_intervention(x,hs,reps,zeros),)+tuple(args[1:]) if reps or zeros else None
            handles.append(model.transformer.h[layer].attn.c_proj.register_forward_pre_hook(hook))
        if capture_residual or residual_replacement is not None:
            rep=None if residual_replacement is None else torch.as_tensor(residual_replacement[start:start+len(batch)],device=ids.device)
            def rhook(_module,args,rep=rep):
                x=args[0]
                if capture_residual: residual.append(x[:,-1,:].detach().float().cpu().numpy())
                if rep is None: return None
                y=x.clone(); y[:,-1,:]=rep; return (y,)+tuple(args[1:])
            handles.append(model.transformer.ln_f.register_forward_pre_hook(rhook))
        try: out=model(input_ids=ids,attention_mask=torch.ones_like(ids),use_cache=False,output_attentions=False,return_dict=True)
        finally:
            for h in handles: h.remove()
        logits.append(out.logits[:,-1,:].detach().float().cpu().numpy())
    return {"logits":np.concatenate(logits),"heads":{k:np.concatenate(v) for k,v in head_out.items()},"residual":np.concatenate(residual) if residual else None}


def stack_heads(values:Mapping[str,np.ndarray],registry:Sequence[Sequence[int]])->np.ndarray:
    return np.stack([values[f"{a}.{b}"] for a,b in registry],axis=2)


def qa_arrays(cfg:Mapping[str,Any],model:Any,rows:Sequence[Mapping[str,Any]])->dict[str,np.ndarray]:
    circuit,control=cfg["model"]["circuit_heads"],cfg["model"]["control_heads"]
    clean=run_condition(model,cfg,rows,"clean",capture_heads=circuit+control,capture_residual=True)
    corrupt=run_condition(model,cfg,rows,"corrupt",capture_heads=circuit+control)
    sham=run_condition(model,cfg,rows,"sham",capture_heads=circuit,capture_residual=True)
    return {"clean_logits":clean["logits"],"corrupt_logits":corrupt["logits"],"sham_logits":sham["logits"],"clean_circuit_heads":stack_heads(clean["heads"],circuit),"corrupt_circuit_heads":stack_heads(corrupt["heads"],circuit),"sham_circuit_heads":stack_heads(sham["heads"],circuit),"clean_control_heads":stack_heads(clean["heads"],control),"corrupt_control_heads":stack_heads(corrupt["heads"],control),"clean_final_residual":clean["residual"],"sham_final_residual":sham["residual"]}


def attempt_paths(cfg:Mapping[str,Any],stage:str)->tuple[Path,Path]:
    prov=ROOT/cfg["runtime"]["provenance_root"]; q=prov/"qa"/stage; return q,prov/f"{stage}_ATTEMPT.json"


def validate_attempt(cfg:Mapping[str,Any],stage:str,launch_token:str,attempt_token:str,expected_state:str)->dict[str,Any]:
    validate_launch(cfg,launch_token); _,p=attempt_paths(cfg,stage); rec=loadj(p)
    keys={"schema_version","stage","attempt_token","controller_pid","launch_manifest_sha256","state","updated_ns"}
    if set(rec)!=keys or rec.get("schema_version")!="canonical_induction_two_tier_v2_stage_attempt" or rec["attempt_token"]!=attempt_token or rec["stage"]!=stage or rec["state"]!=expected_state or not isinstance(rec.get("controller_pid"),int) or rec["controller_pid"]!=os.getppid() or not isinstance(rec.get("updated_ns"),int) or rec["updated_ns"]<=0 or rec.get("launch_manifest_sha256")!=sha(ROOT/cfg["runtime"]["provenance_root"]/"launch_manifest.json"): raise RuntimeError("attempt schema/token/state/PID/launch mismatch")
    return rec


def qa_reference(config:Path,stage:str,replicate:int,launch_token:str,attempt_token:str)->None:
    cfg=require_config(config); expected="INITIALIZED" if replicate==1 else "REFERENCE_1_COMPLETE"; validate_attempt(cfg,stage,launch_token,attempt_token,expected)
    if stage=="confirmation": validate_authorization(cfg,launch_token)
    q,_=attempt_paths(cfg,stage); target=q/f"QA_REFERENCE_{replicate}.npz"
    if target.exists(): raise FileExistsError(target)
    review_binding(config); verify_freeze(config,cfg,include_confirmation=stage=="confirmation")
    device=gpu_guard(cfg,validate_launch(cfg,launch_token)); seed_all(endpoint_seed(cfg["seed"],stage,f"qa_reference_{replicate}")); model=load_model(cfg,device)
    rows=readjl(ROOT/cfg["runtime"]["prepared_root"]/f"{stage}.jsonl")[:cfg["qa"]["rows"]]; arrays=qa_arrays(cfg,model,rows)
    if tuple(arrays)!=QA_ARRAYS or any(not np.isfinite(v).all() for v in arrays.values()): raise RuntimeError("QA array schema/nonfinite")
    np.savez(target,**arrays)


def qa_compare(config:Path,stage:str,launch_token:str,attempt_token:str)->None:
    cfg=require_config(config); validate_attempt(cfg,stage,launch_token,attempt_token,"REFERENCE_2_COMPLETE"); q,_=attempt_paths(cfg,stage); target=q/"QA_COMPARISON.json"
    if target.exists(): raise FileExistsError(target)
    with np.load(q/"QA_REFERENCE_1.npz") as a,np.load(q/"QA_REFERENCE_2.npz") as b:
        shapes=expected_qa_shapes(cfg)
        if set(a.files)!=set(QA_ARRAYS) or set(b.files)!=set(QA_ARRAYS): raise RuntimeError("QA reference array set mismatch")
        if any(list(a[k].shape)!=shapes[k] or str(a[k].dtype)!="float32" or list(b[k].shape)!=shapes[k] or str(b[k].dtype)!="float32" or not np.isfinite(a[k]).all() or not np.isfinite(b[k]).all() for k in QA_ARRAYS): raise RuntimeError("QA reference registered shape/dtype/nonfinite mismatch")
        fields={k:{"shape":list(a[k].shape),"dtype":str(a[k].dtype),"bitwise_equal":bool(np.array_equal(a[k],b[k]))} for k in QA_ARRAYS}
    if not all(x["bitwise_equal"] for x in fields.values()): raise RuntimeError("independent process QA mismatch")
    exjson(target,{"schema_version":"canonical_induction_two_tier_v2_qa_comparison","stage":stage,"fields":fields,"reference_1_sha256":sha(q/"QA_REFERENCE_1.npz"),"reference_2_sha256":sha(q/"QA_REFERENCE_2.npz"),"pass":True})


def all_finite(outputs:Mapping[str,Any])->bool:
    def check(obj:Any)->bool:
        if obj is None: return True
        if isinstance(obj,np.ndarray): return bool(np.isfinite(obj).all())
        if isinstance(obj,Mapping): return all(check(x) for x in obj.values())
        if isinstance(obj,(float,np.floating)): return bool(np.isfinite(obj))
        return True
    return all(check(obj) for obj in outputs.values())


def build_descriptive_reports(cfg:Mapping[str,Any],metrics:Sequence[Mapping[str,Any]],stage:str)->dict[str,Any]:
    """Recompute the complete, registered descriptive report set from row metrics."""
    blocks=int(cfg["panel"]["blocks"])
    reports={}
    for field in registered_descriptive_fields(cfg):
        cohort={str(b):sum(bool(r.get("gate_cohort")) for r in metrics if int(r["block_index"])==b) for b in range(blocks)}
        finite={str(b):sum(bool(r.get("gate_cohort")) and r.get(field) is not None and np.isfinite(r[field]) for r in metrics if int(r["block_index"])==b) for b in range(blocks)}
        reports[field]={
            "interval":equal_block_interval(metrics,field,cfg,stage,gate_only=True),
            "cohort_per_block":finite,
            "missing_per_block":{str(b):cohort[str(b)]-finite[str(b)] for b in range(blocks)},
            "cohort_total":sum(finite.values()),
            "missing_total":sum(cohort.values())-sum(finite.values()),
        }
    return reports


def run_full_stage(cfg:Mapping[str,Any],model:Any,rows:Sequence[Mapping[str,Any]])->tuple[list[dict[str,Any]],dict[str,Any]]:
    cir,ctl=cfg["model"]["circuit_heads"],cfg["model"]["control_heads"]
    clean=run_condition(model,cfg,rows,"clean",capture_heads=cir+ctl,capture_residual=True)
    corrupt=run_condition(model,cfg,rows,"corrupt",capture_heads=cir+ctl)
    sham=run_condition(model,cfg,rows,"sham",capture_heads=cir,capture_residual=True)
    if not all(all_finite(x) for x in (clean,corrupt,sham)): raise RuntimeError("nonfinite captured live state")
    cirkeys={f"{a}.{b}" for a,b in cir}; ctlkeys={f"{a}.{b}" for a,b in ctl}
    cdon={k:v for k,v in clean["heads"].items() if k in cirkeys}; sdon=sham["heads"]; tdon={k:v for k,v in clean["heads"].items() if k in ctlkeys}
    full_clean=run_condition(model,cfg,rows,"corrupt",residual_replacement=clean["residual"]); full_sham=run_condition(model,cfg,rows,"corrupt",residual_replacement=sham["residual"])
    circuit_clean=run_condition(model,cfg,rows,"corrupt",replacement=cdon); circuit_sham=run_condition(model,cfg,rows,"corrupt",replacement=sdon); control_clean=run_condition(model,cfg,rows,"corrupt",replacement=tdon)
    circuit_zero=run_condition(model,cfg,rows,"clean",zero_heads=cir); control_zero=run_condition(model,cfg,rows,"clean",zero_heads=ctl)
    self_c=run_condition(model,cfg,rows,"corrupt",replacement={k:v for k,v in corrupt["heads"].items() if k in cirkeys}); self_t=run_condition(model,cfg,rows,"corrupt",replacement={k:v for k,v in corrupt["heads"].items() if k in ctlkeys})
    if not np.array_equal(full_clean["logits"],clean["logits"]) or not np.array_equal(full_sham["logits"],sham["logits"]): raise RuntimeError("decoder-tail donor byte identity failed")
    if not np.array_equal(self_c["logits"],corrupt["logits"]) or not np.array_equal(self_t["logits"],corrupt["logits"]): raise RuntimeError("all-position self patch failed")
    main={"clean":clean["logits"],"corrupt":corrupt["logits"],"full_clean":full_clean["logits"],"full_sham":full_sham["logits"],"circuit_clean":circuit_clean["logits"],"circuit_sham":circuit_sham["logits"],"control_clean":control_clean["logits"],"circuit_zero":circuit_zero["logits"],"control_zero":control_zero["logits"]}
    if not all_finite(main): raise RuntimeError("nonfinite live condition")
    metrics=compute_rows(cfg,rows,main)
    # Descriptive individual/class recoveries and additivity.
    individual={};
    for a,b in cir:
        key=f"individual_{a}_{b}"; o=run_condition(model,cfg,rows,"corrupt",replacement={f"{a}.{b}":cdon[f"{a}.{b}"]}); individual[key]=o["logits"]
    classouts={}
    for name,heads in cfg["model"]["classes"].items():
        repl={f"{a}.{b}":cdon[f"{a}.{b}"] for a,b in heads}; classouts[f"class_{name}"]=run_condition(model,cfg,rows,"corrupt",replacement=repl)["logits"]
    if not all(np.isfinite(x).all() for x in list(individual.values())+list(classouts.values())): raise RuntimeError("nonfinite descriptive live condition")
    mm={k:margin(v,rows) for k,v in main.items()}; im={k:margin(v,rows) for k,v in individual.items()}; cm={k:margin(v,rows) for k,v in classouts.items()}
    for i,r in enumerate(metrics):
        if not r["gate_cohort"]: continue
        den=r["ceiling_denominator"]
        for k,v in im.items(): r[k+"_recovery"]=float((v[i]-mm["corrupt"][i])/den)
        for k,v in cm.items(): r[k+"_recovery"]=float((v[i]-mm["corrupt"][i])/den)
        isum=sum(v[i]-mm["corrupt"][i] for v in im.values()); r["additivity_ratio"]=None if abs(isum)<=1e-8 else float((mm["circuit_clean"][i]-mm["corrupt"][i])/isum)
        cc={k:v[i]-np.mean(v[i]) for k,v in main.items()}; D=float(np.sqrt(np.mean((cc["clean"]-cc["corrupt"])**2)))
        for q in ("full_clean","full_sham","circuit_clean","circuit_sham","control_clean"):
            r[f"vocab_restoration_{q}"]=None if D<=1e-8 else float(1-np.sqrt(np.mean((cc[q]-cc["clean"])**2))/D)
            for u,idkey in (("target","target_id"),("contrast","contrast_id"),("sham","sham_id")): r[f"token_movement_{q}_{u}"]=float(cc[q][int(rows[i][idkey])]-cc["corrupt"][int(rows[i][idkey])])
        mask=np.ones(cc["clean"].shape[0],dtype=bool); mask[[rows[i]["target_id"],rows[i]["contrast_id"],rows[i]["sham_id"]]]=False
        for q in ("circuit_clean","circuit_sham","control_clean"):
            r[f"collateral_{q}"]=float(np.sqrt(np.mean((cc[q][mask]-cc["corrupt"][mask])**2))/max(abs(mm[q][i]-mm["corrupt"][i]),1e-8))
    if any(isinstance(v,(float,np.floating)) and not np.isfinite(v) for r in metrics for v in r.values()): raise RuntimeError("nonfinite derived live field")
    descriptive=build_descriptive_reports(cfg,metrics,rows[0]["stage"])
    return metrics,{"decoder_clean_bitwise":True,"decoder_sham_bitwise":True,"circuit_self_patch_bitwise":True,"control_self_patch_bitwise":True,"descriptive":descriptive}


def worker(config:Path,stage:str,launch_token:str,attempt_token:str)->None:
    cfg=require_config(config); validate_attempt(cfg,stage,launch_token,attempt_token,"REFERENCES_COMPARED"); q,_=attempt_paths(cfg,stage); comp=validate_reference_comparison(cfg,stage)
    if stage=="confirmation": validate_authorization(cfg,launch_token)
    review_binding(config)
    root=ROOT/cfg["runtime"]["output_root"]/stage
    if root.exists(): raise FileExistsError(root)
    root.mkdir(parents=True)
    launch=validate_launch(cfg,launch_token); freeze_rec=verify_freeze(config,cfg,include_confirmation=stage=="confirmation")
    device=gpu_guard(cfg,launch); seed_all(endpoint_seed(cfg["seed"],stage,"worker")); model=load_model(cfg,device); rows=readjl(ROOT/cfg["runtime"]["prepared_root"]/f"{stage}.jsonl")
    repeated=qa_arrays(cfg,model,rows[:cfg["qa"]["rows"]]); matches={}
    for rep in (1,2):
        with np.load(q/f"QA_REFERENCE_{rep}.npz") as ref:
            matches[str(rep)]={k:bool(np.array_equal(repeated[k],ref[k])) for k in QA_ARRAYS}
    if not all(all(v.values()) for v in matches.values()): raise RuntimeError("worker QA differs from independent reference")
    driver=subprocess.check_output(["nvidia-smi","--query-gpu=driver_version","--format=csv,noheader,nounits","--id",str(launch["gpu"]["physical_index"])],text=True).strip()
    exjson(root/"STARTED.json",{"stage":stage,"launch_manifest_sha256":sha(ROOT/cfg["runtime"]["provenance_root"]/"launch_manifest.json"),"gpu_uuid":launch["gpu"]["uuid"],"runtime":{"torch":torch.__version__,"cuda":torch.version.cuda,"cudnn":torch.backends.cudnn.version(),"driver":driver,"device":torch.cuda.get_device_name(0),"inference_mode":True}})
    metrics,qa=run_full_stage(cfg,model,rows); summary=summarize(cfg,metrics,stage); qa["worker_reference_matches"]=matches; qa["independent_comparison_sha256"]=sha(q/"QA_COMPARISON.json"); qa["pass"]=True
    writejl(root/"metrics.jsonl",metrics); exjson(root/"QA.json",qa); exjson(root/"SUMMARY.json",summary)
    payload={"schema_version":"canonical_induction_two_tier_v2_complete","stage":stage,"rows":len(rows),"metrics_sha256":sha(root/"metrics.jsonl"),"qa_sha256":sha(root/"QA.json"),"summary_sha256":sha(root/"SUMMARY.json"),"freeze_sha256":sha(ROOT/cfg["runtime"]["freeze"]),"freeze_inventory_sha256":freeze_rec["candidate_inventory_sha256"],"launch_manifest_sha256":sha(ROOT/cfg["runtime"]["provenance_root"]/"launch_manifest.json"),"cache_attestation_sha256":sha(ROOT/cfg["runtime"]["cache_attestation"]),"attempt_token":attempt_token,"status":summary["status"],"representation_methods":False,"training":False,"external_set_scope":"FIGURE2_UPSTREAM_SET_NOT_COMPLETE_RANDOM_TOKEN_CIRCUIT"}
    if stage=="confirmation": payload["confirmation_authorization_sha256"]=sha(authorization_paths(cfg)[2])
    exjson(root/"COMPLETE.json",payload)


def technical_terminal(cfg:Mapping[str,Any],stage:str,reason:str,launch_token:str)->None:
    root=ROOT/cfg["runtime"]["output_root"]/stage; root.mkdir(parents=True,exist_ok=True)
    observed=[{"name":p.name,"bytes":p.stat().st_size,"sha256":sha(p)} for p in sorted(root.iterdir()) if p.is_file() and p.name!="TECHNICAL_INVALID_STOP.json"]
    q,attempt=attempt_paths(cfg,stage); qa=[{"name":p.name,"bytes":p.stat().st_size,"sha256":sha(p)} for p in sorted(q.iterdir()) if p.is_file()] if q.exists() else []
    ar=loadj(attempt)
    if ar.get("state")!="CLOSED_TECHNICAL_INVALID": raise RuntimeError("technical terminal requires a closed matching attempt")
    publish(root/"TECHNICAL_INVALID_STOP.json",{"schema_version":"canonical_induction_two_tier_v2_technical_invalid","stage":stage,"status":"TECHNICAL_INVALID_STOP","reason":reason,"observed_artifacts":observed,"qa_artifacts":qa,"attempt_token":ar["attempt_token"],"attempt_sha256":sha(attempt),"freeze_sha256":sha(ROOT/cfg["runtime"]["freeze"]),"cache_attestation_sha256":sha(ROOT/cfg["runtime"]["cache_attestation"]),"launch_manifest_sha256":sha(ROOT/cfg["runtime"]["provenance_root"]/"launch_manifest.json"),"representation_methods":False,"training":False})


def orphan_open_attempt_completion(cfg:Mapping[str,Any],stage:str)->None:
    root=ROOT/cfg["runtime"]["output_root"]/stage; complete=root/"COMPLETE.json"; orphan=root/"ORPHANED_COMPLETE.json"
    if complete.exists():
        if orphan.exists(): raise RuntimeError("both complete and orphaned complete exist")
        os.replace(complete,orphan)


def update_attempt(path:Path,state:str)->None:
    rec=loadj(path); rec["state"]=state; rec["updated_ns"]=time.time_ns(); replace_json(path,rec)


def stage_controller(config:Path,stage:str,launch_token:str)->None:
    cfg=require_config(config); launch=validate_launch(cfg,launch_token); review_binding(config)
    if stage=="confirmation": validate_authorization(cfg,launch_token)
    q,attempt=attempt_paths(cfg,stage); out=ROOT/cfg["runtime"]["output_root"]/stage
    if attempt.exists() or q.exists() or out.exists(): raise FileExistsError("stage namespace exists")
    token=secrets.token_hex(32)
    exjson(attempt,{"schema_version":"canonical_induction_two_tier_v2_stage_attempt","stage":stage,"attempt_token":token,"controller_pid":os.getpid(),"launch_manifest_sha256":sha(ROOT/cfg["runtime"]["provenance_root"]/"launch_manifest.json"),"state":"INITIALIZED","updated_ns":time.time_ns()})
    q.mkdir(parents=True)
    base=[sys.executable,str(Path(__file__).resolve())]
    try:
        timeout=int(cfg["runtime"]["stage_timeout_seconds"])
        subprocess.run(base+["qa-reference","--config",str(config),"--stage",stage,"--replicate","1","--launch-token",launch_token,"--attempt-token",token],check=True,timeout=timeout); update_attempt(attempt,"REFERENCE_1_COMPLETE")
        subprocess.run(base+["qa-reference","--config",str(config),"--stage",stage,"--replicate","2","--launch-token",launch_token,"--attempt-token",token],check=True,timeout=timeout); update_attempt(attempt,"REFERENCE_2_COMPLETE")
        subprocess.run(base+["qa-compare","--config",str(config),"--stage",stage,"--launch-token",launch_token,"--attempt-token",token],check=True,timeout=timeout); update_attempt(attempt,"REFERENCES_COMPARED")
        subprocess.run(base+["worker","--config",str(config),"--stage",stage,"--launch-token",launch_token,"--attempt-token",token],check=True,timeout=timeout); update_attempt(attempt,"WORKER_COMPLETE_PENDING_VALIDATION"); validate_complete(cfg,stage,attempt_state="WORKER_COMPLETE_PENDING_VALIDATION"); update_attempt(attempt,"CLOSED"); publish_development_validated(cfg) if stage=="development" else None
    except Exception as e:
        orphan_open_attempt_completion(cfg,stage); update_attempt(attempt,"CLOSED_TECHNICAL_INVALID"); technical_terminal(cfg,stage,f"{type(e).__name__}: {e}",launch_token)


def reconcile_stage(config:Path,stage:str,launch_token:str)->None:
    cfg=require_config(config); validate_launch(cfg,launch_token); prov=ROOT/cfg["runtime"]["provenance_root"]; q,attempt=attempt_paths(cfg,stage); lock=prov/f"{stage}_ATTEMPT.lock"
    with lock.open("a+") as handle:
        fcntl.flock(handle,fcntl.LOCK_EX)
        if not attempt.exists():
            if q.exists() or (ROOT/cfg["runtime"]["output_root"]/stage).exists():
                exjson(attempt,{"schema_version":"canonical_induction_two_tier_v2_stage_attempt","stage":stage,"attempt_token":"reconciled-"+secrets.token_hex(24),"controller_pid":os.getpid(),"launch_manifest_sha256":sha(ROOT/cfg["runtime"]["provenance_root"]/"launch_manifest.json"),"state":"CLOSED_TECHNICAL_INVALID","updated_ns":time.time_ns()})
                technical_terminal(cfg,stage,"JOURNALLESS_PARTIAL_STAGE_RECONCILED",launch_token)
            else: raise RuntimeError("no stage attempt to reconcile")
            return
        rec=loadj(attempt)
        if rec["state"]=="CLOSED":
            try:
                validate_complete(cfg,stage)
                if stage=="development": publish_development_validated(cfg)
                return
            except Exception as e:
                orphan_open_attempt_completion(cfg,stage); update_attempt(attempt,"CLOSED_TECHNICAL_INVALID"); technical_terminal(cfg,stage,f"CLOSED_STAGE_VALIDATION_FAILED_RECONCILED: {type(e).__name__}: {e}",launch_token); return
        if rec["state"]=="CLOSED_TECHNICAL_INVALID":
            terminal=ROOT/cfg["runtime"]["output_root"]/stage/"TECHNICAL_INVALID_STOP.json"
            if terminal.exists(): validate_technical_terminal(cfg,stage)
            else: technical_terminal(cfg,stage,"MISSING_TECHNICAL_TERMINAL_RECONCILED",launch_token)
            return
        try: os.kill(int(rec["controller_pid"]),0); raise RuntimeError("controller is still live")
        except ProcessLookupError: pass
        orphan_open_attempt_completion(cfg,stage); update_attempt(attempt,"CLOSED_TECHNICAL_INVALID"); technical_terminal(cfg,stage,"INCOMPLETE_CONTROLLER_ATTEMPT_RECONCILED",launch_token)


def expected_qa_shapes(cfg:Mapping[str,Any])->dict[str,list[int]]:
    rows=int(cfg["qa"]["rows"]); prompt=int(cfg["panel"]["prompt_length"]); heads=len(cfg["model"]["circuit_heads"])
    control=len(cfg["model"]["control_heads"]); head_size=int(cfg["model"]["head_size"])
    return {
        "clean_logits":[rows,int(cfg["model"]["vocab_size"])],
        "corrupt_logits":[rows,int(cfg["model"]["vocab_size"])],
        "sham_logits":[rows,int(cfg["model"]["vocab_size"])],
        "clean_circuit_heads":[rows,prompt,heads,head_size],
        "corrupt_circuit_heads":[rows,prompt,heads,head_size],
        "sham_circuit_heads":[rows,prompt,heads,head_size],
        "clean_control_heads":[rows,prompt,control,head_size],
        "corrupt_control_heads":[rows,prompt,control,head_size],
        "clean_final_residual":[rows,int(cfg["model"]["hidden_size"])],
        "sham_final_residual":[rows,int(cfg["model"]["hidden_size"])],
    }


def validate_reference_comparison(cfg:Mapping[str,Any],stage:str)->dict[str,Any]:
    q,_=attempt_paths(cfg,stage); comp_path=q/"QA_COMPARISON.json"; comp=loadj(comp_path)
    keys={"schema_version","stage","fields","reference_1_sha256","reference_2_sha256","pass"}
    if set(comp)!=keys or comp["schema_version"]!="canonical_induction_two_tier_v2_qa_comparison" or comp["stage"]!=stage or comp["pass"] is not True or set(comp["fields"])!=set(QA_ARRAYS): raise RuntimeError("QA comparison schema drift")
    shapes=expected_qa_shapes(cfg); refs=[]
    for rep in (1,2):
        path=q/f"QA_REFERENCE_{rep}.npz"
        if comp[f"reference_{rep}_sha256"]!=sha(path): raise RuntimeError("QA reference hash drift")
        refs.append(np.load(path))
    try:
        if set(refs[0].files)!=set(QA_ARRAYS) or set(refs[1].files)!=set(QA_ARRAYS): raise RuntimeError("QA reference array set mismatch")
        for key in QA_ARRAYS:
            a,b=refs[0][key],refs[1][key]; expected={"shape":shapes[key],"dtype":"float32","bitwise_equal":True}
            if comp["fields"][key]!=expected or not np.array_equal(a,b) or not np.isfinite(a).all(): raise RuntimeError(f"QA reference mismatch: {key}")
    finally:
        for ref in refs: ref.close()
    return comp


def validate_qa_bundle(cfg:Mapping[str,Any],stage:str,qa:Mapping[str,Any],metrics:Sequence[Mapping[str,Any]])->None:
    expected_keys={"decoder_clean_bitwise","decoder_sham_bitwise","circuit_self_patch_bitwise","control_self_patch_bitwise","descriptive","worker_reference_matches","independent_comparison_sha256","pass"}
    if set(qa)!=expected_keys or any(qa[k] is not True for k in ("decoder_clean_bitwise","decoder_sham_bitwise","circuit_self_patch_bitwise","control_self_patch_bitwise","pass")): raise RuntimeError("QA schema/identity failure")
    q,_=attempt_paths(cfg,stage); comp_path=q/"QA_COMPARISON.json"; comp=validate_reference_comparison(cfg,stage)
    if qa["independent_comparison_sha256"]!=sha(comp_path): raise RuntimeError("QA comparison hash drift")
    expected_matches={str(rep):{key:True for key in QA_ARRAYS} for rep in (1,2)}
    if qa["worker_reference_matches"]!=expected_matches: raise RuntimeError("worker/reference QA mismatch")
    expected_descriptive=build_descriptive_reports(cfg,metrics,stage)
    if qa["descriptive"]!=expected_descriptive: raise RuntimeError("descriptive QA set/recomputation drift")


def validate_complete(cfg:Mapping[str,Any],stage:str,attempt_state:str="CLOSED")->dict[str,Any]:
    root=ROOT/cfg["runtime"]["output_root"]/stage; allowed={"STARTED.json","metrics.jsonl","QA.json","SUMMARY.json","COMPLETE.json"}; actual={p.name for p in root.iterdir() if p.is_file()}
    if actual!=allowed: raise RuntimeError(f"unexpected/missing completion artifacts: {actual^allowed}")
    rec=loadj(root/"COMPLETE.json"); metrics=readjl(root/"metrics.jsonl"); prepared=readjl(ROOT/cfg["runtime"]["prepared_root"]/f"{stage}.jsonl")
    expected_rows=int(cfg["panel"]["rows_per_stage"]); blocks=int(cfg["panel"]["blocks"]); rows_per_block=int(cfg["panel"]["rows_per_block"])
    if len(metrics)!=expected_rows or len(prepared)!=expected_rows: raise RuntimeError("metrics/prepared row-count mismatch")
    base_fields={"stage","row_index","block_index","component_id","live_finite","behavior_eligible","gate_cohort","effect","ceiling_denominator","clean_margin","corrupt_margin","skyline_recovery","joint_recovery","sham_recovery","control_recovery","selectivity","circuit_control_margin","circuit_ablation","control_ablation","ablation_advantage"}
    descriptive=set(registered_descriptive_fields(cfg)); block_counts={b:0 for b in range(blocks)}
    for i,(row,source) in enumerate(zip(metrics,prepared)):
        identity={k:source[k] for k in ("stage","row_index","block_index","component_id")}
        if {k:row.get(k) for k in identity}!=identity or int(row["row_index"])!=i: raise RuntimeError("metric row identity/order mismatch")
        block=int(row["block_index"])
        if block not in block_counts: raise RuntimeError("metric block out of range")
        block_counts[block]+=1
        extras=set(row)-base_fields
        if extras-descriptive: raise RuntimeError("unregistered metric field")
        if bool(row["gate_cohort"]):
            if extras!=descriptive: raise RuntimeError("gate-cohort descriptive field set incomplete")
        elif extras: raise RuntimeError("noncohort row contains descriptive fields")
    if any(v!=rows_per_block for v in block_counts.values()): raise RuntimeError("metric block support mismatch")
    summary=summarize(cfg,metrics,stage); qa=loadj(root/"QA.json"); started=loadj(root/"STARTED.json"); fr=loadj(ROOT/cfg["runtime"]["freeze"]); _,attempt=attempt_paths(cfg,stage); ar=loadj(attempt)
    expected={"schema_version":"canonical_induction_two_tier_v2_complete","stage":stage,"rows":expected_rows,"metrics_sha256":sha(root/"metrics.jsonl"),"qa_sha256":sha(root/"QA.json"),"summary_sha256":sha(root/"SUMMARY.json"),"freeze_sha256":sha(ROOT/cfg["runtime"]["freeze"]),"freeze_inventory_sha256":fr["candidate_inventory_sha256"],"launch_manifest_sha256":sha(ROOT/cfg["runtime"]["provenance_root"]/"launch_manifest.json"),"cache_attestation_sha256":sha(ROOT/cfg["runtime"]["cache_attestation"]),"attempt_token":ar["attempt_token"],"status":summary["status"],"representation_methods":False,"training":False,"external_set_scope":"FIGURE2_UPSTREAM_SET_NOT_COMPLETE_RANDOM_TOKEN_CIRCUIT"}
    if stage=="confirmation": expected["confirmation_authorization_sha256"]=sha(authorization_paths(cfg)[2])
    validate_qa_bundle(cfg,stage,qa,metrics)
    launch=loadj(ROOT/cfg["runtime"]["provenance_root"]/"launch_manifest.json")
    if set(started)!={"stage","launch_manifest_sha256","gpu_uuid","runtime"} or set(started.get("runtime",{}))!={"torch","cuda","cudnn","driver","device","inference_mode"} or started["stage"]!=stage or started["gpu_uuid"]!=launch.get("gpu",{}).get("uuid") or started["launch_manifest_sha256"]!=expected["launch_manifest_sha256"] or started["runtime"]["inference_mode"] is not True or any(str(started["runtime"][k]) in {"","None"} for k in ("torch","cuda","cudnn","driver","device")):
        raise RuntimeError("STARTED runtime provenance mismatch")
    expected_attempt_keys={"schema_version","stage","attempt_token","controller_pid","launch_manifest_sha256","state","updated_ns"}
    if attempt_state not in {"CLOSED","WORKER_COMPLETE_PENDING_VALIDATION"}: raise RuntimeError("illegal completion-validation attempt state")
    if rec!=expected or summary!=loadj(root/"SUMMARY.json") or set(ar)!=expected_attempt_keys or ar.get("state")!=attempt_state or ar.get("stage")!=stage or ar.get("launch_manifest_sha256")!=expected["launch_manifest_sha256"]:
        raise RuntimeError("completion lineage/scope/attempt mismatch")
    return rec


def development_validated_path(cfg:Mapping[str,Any])->Path:
    return ROOT/cfg["runtime"]["provenance_root"]/"DEVELOPMENT_COMPLETION_VALIDATED.json"


def development_validated_payload(cfg:Mapping[str,Any])->dict[str,Any]:
    out=ROOT/cfg["runtime"]["output_root"]; _,attempt=attempt_paths(cfg,"development")
    rec=validate_complete(cfg,"development")
    return {"schema_version":"canonical_induction_two_tier_v2_development_validated","status":"VALIDATED","development_complete_sha256":sha(out/"development/COMPLETE.json"),"development_summary_sha256":sha(out/"development/SUMMARY.json"),"development_attempt_sha256":sha(attempt),"launch_manifest_sha256":rec["launch_manifest_sha256"],"representation_methods":False,"training":False}


def publish_development_validated(cfg:Mapping[str,Any])->dict[str,Any]:
    target=development_validated_path(cfg); expected=development_validated_payload(cfg)
    if target.exists():
        if loadj(target)!=expected: raise RuntimeError("development validated marker drift")
    else: exjson(target,expected)
    return expected


def validate_development_predecessor(cfg:Mapping[str,Any])->dict[str,Any]:
    target=development_validated_path(cfg); expected=development_validated_payload(cfg)
    if not target.is_file() or loadj(target)!=expected: raise RuntimeError("validated development predecessor absent/drifted")
    return expected


def validate_technical_terminal(cfg:Mapping[str,Any],stage:str)->dict[str,Any]:
    root=ROOT/cfg["runtime"]["output_root"]/stage; path=root/"TECHNICAL_INVALID_STOP.json"; rec=loadj(path); _,attempt=attempt_paths(cfg,stage)
    if not attempt.is_file(): raise RuntimeError("technical terminal has no attempt journal")
    ar=loadj(attempt)
    expected_keys={"schema_version","stage","status","reason","observed_artifacts","qa_artifacts","attempt_token","attempt_sha256","freeze_sha256","cache_attestation_sha256","launch_manifest_sha256","representation_methods","training"}
    if set(rec)!=expected_keys or rec["schema_version"]!="canonical_induction_two_tier_v2_technical_invalid" or rec["stage"]!=stage or rec["status"]!="TECHNICAL_INVALID_STOP" or rec["launch_manifest_sha256"]!=sha(ROOT/cfg["runtime"]["provenance_root"]/"launch_manifest.json") or rec["freeze_sha256"]!=sha(ROOT/cfg["runtime"]["freeze"]) or rec["cache_attestation_sha256"]!=sha(ROOT/cfg["runtime"]["cache_attestation"]) or rec["representation_methods"] or rec["training"]:
        raise RuntimeError("technical terminal lineage mismatch")
    expected_attempt_keys={"schema_version","stage","attempt_token","controller_pid","launch_manifest_sha256","state","updated_ns"}
    if set(ar)!=expected_attempt_keys or ar.get("schema_version")!="canonical_induction_two_tier_v2_stage_attempt" or ar.get("stage")!=stage or ar.get("state")!="CLOSED_TECHNICAL_INVALID" or not isinstance(ar.get("controller_pid"),int) or ar["controller_pid"]<=0 or not isinstance(ar.get("updated_ns"),int) or ar["updated_ns"]<=0 or ar.get("launch_manifest_sha256")!=rec["launch_manifest_sha256"] or ar.get("attempt_token")!=rec.get("attempt_token") or sha(attempt)!=rec.get("attempt_sha256"):
        raise RuntimeError("technical attempt binding/schema mismatch")
    if (root/"COMPLETE.json").exists(): raise RuntimeError("conflicting stage terminals")
    observed=[{"name":p.name,"bytes":p.stat().st_size,"sha256":sha(p)} for p in sorted(root.iterdir()) if p.is_file() and p.name!="TECHNICAL_INVALID_STOP.json"]
    if rec["observed_artifacts"]!=observed: raise RuntimeError("technical partial-artifact inventory drift")
    q,_=attempt_paths(cfg,stage); qa=[{"name":p.name,"bytes":p.stat().st_size,"sha256":sha(p)} for p in sorted(q.iterdir()) if p.is_file()] if q.exists() else []
    if rec["qa_artifacts"]!=qa: raise RuntimeError("technical QA-artifact inventory drift")
    return rec


def path_hash_or_none(path:Path)->str|None:
    try: return sha(path) if path.is_file() else None
    except OSError: return None


def gate_paths(cfg:Mapping[str,Any])->tuple[Path,Path,Path,Path,Path]:
    out=ROOT/cfg["runtime"]["output_root"]; root=out/"development_gate"
    return root,out/"DEVELOPMENT_GATE_ATTEMPT.json",root/"result.json",root/"DEVELOPMENT_GATE_TECHNICAL_INVALID_STOP.json",out/"DEVELOPMENT_GATE.lock"


def new_gate_attempt(cfg:Mapping[str,Any],launch_token:str,reason_prefix:str="live")->dict[str,Any]:
    return {"schema_version":"canonical_induction_two_tier_v2_development_gate_attempt","attempt_token":reason_prefix+"-"+secrets.token_hex(24),"controller_pid":os.getpid(),"launch_token_sha256":hashlib.sha256(launch_token.encode()).hexdigest(),"state":"PRECHECK_JOURNALED","launch_manifest_sha256":None,"freeze_sha256":None,"development_complete_sha256":None,"updated_ns":time.time_ns()}


def transition_gate_attempt(path:Path,expected_state:str,new_state:str,updates:Mapping[str,Any]|None=None)->dict[str,Any]:
    rec=loadj(path)
    if rec.get("state")!=expected_state: raise RuntimeError(f"illegal development-gate transition: {rec.get('state')} -> {new_state}")
    rec.update(dict(updates or {})); rec.update({"state":new_state,"updated_ns":time.time_ns()}); replace_json(path,rec); return rec


def close_gate_invalid(cfg:Mapping[str,Any],attempt:Path,invalid:Path,reason:str,last_state:str)->None:
    out=ROOT/cfg["runtime"]["output_root"]; rec=loadj(attempt)
    rec.update({"state":"CLOSED_TECHNICAL_INVALID","launch_manifest_sha256":path_hash_or_none(ROOT/cfg["runtime"]["provenance_root"]/"launch_manifest.json"),"freeze_sha256":path_hash_or_none(ROOT/cfg["runtime"]["freeze"]),"development_complete_sha256":path_hash_or_none(out/"development/COMPLETE.json"),"updated_ns":time.time_ns()}); replace_json(attempt,rec)
    invalid.parent.mkdir(parents=True,exist_ok=True)
    exjson(invalid,{"schema_version":"canonical_induction_two_tier_v2_development_gate_invalid","status":"DEVELOPMENT_GATE_TECHNICAL_INVALID_STOP","reason":reason,"last_state":last_state,"attempt_token":rec["attempt_token"],"attempt_sha256":sha(attempt),"launch_manifest_sha256":rec["launch_manifest_sha256"],"freeze_sha256":rec["freeze_sha256"],"development_complete_sha256":rec["development_complete_sha256"],"representation_methods_authorized":False,"training_authorized":False})


def development_gate(config:Path,launch_token:str)->None:
    cfg=require_config(config); root,attempt,target,invalid,lock=gate_paths(cfg)
    if attempt.exists() or root.exists(): raise FileExistsError("development-gate namespace exists")
    validate_launch(cfg,launch_token); validate_development_predecessor(cfg)
    exjson(attempt,new_gate_attempt(cfg,launch_token))
    with lock.open("a+") as handle:
        fcntl.flock(handle,fcntl.LOCK_EX)
        try:
            initial=validate_gate_attempt(cfg,attempt,"PRECHECK_JOURNALED",launch_token)
            if initial["controller_pid"]!=os.getpid(): raise RuntimeError("development-gate controller PID mismatch")
            validate_launch(cfg,launch_token); validate_development_predecessor(cfg); out=ROOT/cfg["runtime"]["output_root"]
            transition_gate_attempt(attempt,"PRECHECK_JOURNALED","VALIDATED",{"launch_manifest_sha256":sha(ROOT/cfg["runtime"]["provenance_root"]/"launch_manifest.json"),"freeze_sha256":sha(ROOT/cfg["runtime"]["freeze"]),"development_complete_sha256":sha(out/"development/COMPLETE.json")})
            summary=loadj(out/"development/SUMMARY.json"); authorized=bool(summary["tier_a_pass"] and summary["tier_b_pass"] and summary["technical_valid"])
            rec=transition_gate_attempt(attempt,"VALIDATED","CLOSED_GATE_READY"); root.mkdir(parents=True)
            exjson(target,{"schema_version":"canonical_induction_two_tier_v2_development_gate","status":"PASS" if authorized else "STOP","development_status":summary["status"],"summary":summary,"confirmation_authorized":authorized,"development_complete_sha256":rec["development_complete_sha256"],"launch_manifest_sha256":rec["launch_manifest_sha256"],"attempt_token":rec["attempt_token"],"attempt_sha256":sha(attempt),"representation_methods_authorized":False,"training_authorized":False})
        except Exception as e:
            close_gate_invalid(cfg,attempt,invalid,f"{type(e).__name__}: {e}",loadj(attempt)["state"])


def validate_gate_attempt(cfg:Mapping[str,Any],attempt:Path,state:str,launch_token:str|None=None)->dict[str,Any]:
    rec=loadj(attempt); keys={"schema_version","attempt_token","controller_pid","launch_token_sha256","state","launch_manifest_sha256","freeze_sha256","development_complete_sha256","updated_ns"}
    if set(rec)!=keys or rec["schema_version"]!="canonical_induction_two_tier_v2_development_gate_attempt" or rec["state"]!=state or not isinstance(rec["controller_pid"],int) or rec["controller_pid"]<=0 or not isinstance(rec["updated_ns"],int) or rec["updated_ns"]<=0: raise RuntimeError("development-gate attempt schema/state mismatch")
    bound_token=launch_token
    if bound_token is None:
        manifest=ROOT/cfg["runtime"]["provenance_root"]/"launch_manifest.json"
        if manifest.is_file(): bound_token=str(loadj(manifest)["launch_token"])
    if bound_token is not None and rec["launch_token_sha256"]!=hashlib.sha256(bound_token.encode()).hexdigest(): raise RuntimeError("development-gate launch-token binding mismatch")
    return rec


def validate_development_gate(cfg:Mapping[str,Any])->dict[str,Any]:
    out=ROOT/cfg["runtime"]["output_root"]; root,attempt,path,invalid,_=gate_paths(cfg)
    if invalid.exists() or not path.is_file(): raise RuntimeError("development-gate terminal conflict/absence")
    rec=loadj(path); ar=validate_gate_attempt(cfg,attempt,"CLOSED_GATE_READY"); validate_development_predecessor(cfg)
    summary=summarize(cfg,readjl(out/"development/metrics.jsonl"),"development"); authorized=bool(summary["tier_a_pass"] and summary["tier_b_pass"] and summary["technical_valid"])
    expected={"schema_version":"canonical_induction_two_tier_v2_development_gate","status":"PASS" if authorized else "STOP","development_status":summary["status"],"summary":summary,"confirmation_authorized":authorized,"development_complete_sha256":sha(out/"development/COMPLETE.json"),"launch_manifest_sha256":sha(ROOT/cfg["runtime"]["provenance_root"]/"launch_manifest.json"),"attempt_token":ar["attempt_token"],"attempt_sha256":sha(attempt),"representation_methods_authorized":False,"training_authorized":False}
    if rec!=expected or ar["launch_manifest_sha256"]!=expected["launch_manifest_sha256"] or ar["freeze_sha256"]!=sha(ROOT/cfg["runtime"]["freeze"]) or ar["development_complete_sha256"]!=expected["development_complete_sha256"]: raise RuntimeError("development gate lineage/recomputation mismatch")
    return rec


def validate_gate_invalid(cfg:Mapping[str,Any])->dict[str,Any]:
    out=ROOT/cfg["runtime"]["output_root"]; _,attempt,result,invalid,_=gate_paths(cfg)
    if result.exists() or not invalid.is_file(): raise RuntimeError("development-gate invalid terminal conflict/absence")
    rec=loadj(invalid); ar=validate_gate_attempt(cfg,attempt,"CLOSED_TECHNICAL_INVALID")
    keys={"schema_version","status","reason","last_state","attempt_token","attempt_sha256","launch_manifest_sha256","freeze_sha256","development_complete_sha256","representation_methods_authorized","training_authorized"}
    if set(rec)!=keys or rec["schema_version"]!="canonical_induction_two_tier_v2_development_gate_invalid" or rec["status"]!="DEVELOPMENT_GATE_TECHNICAL_INVALID_STOP" or rec["last_state"] not in {"PRECHECK_JOURNALED","VALIDATED","CLOSED_GATE_READY","CLOSED_TECHNICAL_INVALID"} or rec["attempt_token"]!=ar["attempt_token"] or rec["attempt_sha256"]!=sha(attempt) or any(rec[k]!=ar[k] for k in ("launch_manifest_sha256","freeze_sha256","development_complete_sha256")) or rec["representation_methods_authorized"] or rec["training_authorized"]: raise RuntimeError("development-gate invalid lineage mismatch")
    for key,path in (("launch_manifest_sha256",ROOT/cfg["runtime"]["provenance_root"]/"launch_manifest.json"),("freeze_sha256",ROOT/cfg["runtime"]["freeze"]),("development_complete_sha256",out/"development/COMPLETE.json")):
        if rec[key] is not None and rec[key]!=sha(path): raise RuntimeError("development-gate invalid hash drift")
    return rec


def reconcile_development_gate(config:Path,launch_token:str)->None:
    cfg=require_config(config); validate_launch(cfg,launch_token); validate_development_predecessor(cfg); root,attempt,result,invalid,lock=gate_paths(cfg); synthetic=False
    if not attempt.exists() and not result.exists() and not invalid.exists(): exjson(attempt,new_gate_attempt(cfg,launch_token,"reconciled")); synthetic=True
    with lock.open("a+") as handle:
        fcntl.flock(handle,fcntl.LOCK_EX)
        if result.exists(): validate_development_gate(cfg); return
        if invalid.exists(): validate_gate_invalid(cfg); return
        if not attempt.exists(): raise RuntimeError("development-gate attempt absent")
        rec=loadj(attempt)
        if rec["launch_token_sha256"]!=hashlib.sha256(launch_token.encode()).hexdigest(): raise RuntimeError("development-gate reconcile token mismatch")
        if not synthetic:
            try: os.kill(int(rec["controller_pid"]),0); raise RuntimeError("development-gate controller is still live")
            except ProcessLookupError: pass
        if rec.get("state") not in {"PRECHECK_JOURNALED","VALIDATED","CLOSED_GATE_READY","CLOSED_TECHNICAL_INVALID"}: raise RuntimeError("illegal development-gate reconcile state")
        last=rec["state"]
        close_gate_invalid(cfg,attempt,invalid,"INCOMPLETE_DEVELOPMENT_GATE_RECONCILED",last)


def authorization_paths(cfg:Mapping[str,Any])->tuple[Path,Path,Path,Path,Path]:
    out=ROOT/cfg["runtime"]["output_root"]; root=out/"confirmation_authorization"; return root,out/"CONFIRMATION_AUTHORIZATION_ATTEMPT.json",root/"CONFIRMATION_AUTHORIZATION.json",root/"CONFIRMATION_AUTHORIZATION_TECHNICAL_INVALID_STOP.json",out/"CONFIRMATION_AUTHORIZATION.lock"


def new_authorization_attempt(launch_token:str,prefix:str="live")->dict[str,Any]:
    return {"schema_version":"canonical_induction_two_tier_v2_authorization_attempt","attempt_token":prefix+"-"+secrets.token_hex(24),"state":"PRECHECK_JOURNALED","authorizer_pid":os.getpid(),"launch_token_sha256":hashlib.sha256(launch_token.encode()).hexdigest(),"launch_manifest_sha256":None,"freeze_sha256":None,"gate_sha256":None,"payload_accessed":False,"payload_bytes":None,"payload_sha256":None,"updated_ns":time.time_ns()}


def validate_authorization_attempt(cfg:Mapping[str,Any],attempt:Path,state:str,launch_token:str|None=None)->dict[str,Any]:
    rec=loadj(attempt); keys={"schema_version","attempt_token","state","authorizer_pid","launch_token_sha256","launch_manifest_sha256","freeze_sha256","gate_sha256","payload_accessed","payload_bytes","payload_sha256","updated_ns"}
    if set(rec)!=keys or rec["schema_version"]!="canonical_induction_two_tier_v2_authorization_attempt" or rec["state"]!=state or not isinstance(rec["authorizer_pid"],int) or rec["authorizer_pid"]<=0 or not isinstance(rec["updated_ns"],int) or rec["updated_ns"]<=0: raise RuntimeError("authorization attempt schema/state mismatch")
    bound_token=launch_token
    if bound_token is None:
        manifest=ROOT/cfg["runtime"]["provenance_root"]/"launch_manifest.json"
        if manifest.is_file(): bound_token=str(loadj(manifest)["launch_token"])
    if bound_token is not None and rec["launch_token_sha256"]!=hashlib.sha256(bound_token.encode()).hexdigest(): raise RuntimeError("authorization launch-token binding mismatch")
    return rec


def transition_authorization_attempt(path:Path,expected_state:str,new_state:str,updates:Mapping[str,Any]|None=None)->dict[str,Any]:
    rec=loadj(path)
    if rec.get("state")!=expected_state: raise RuntimeError(f"illegal authorization transition: {rec.get('state')} -> {new_state}")
    rec.update(dict(updates or {})); rec.update({"state":new_state,"updated_ns":time.time_ns()}); replace_json(path,rec); return rec


def close_authorization_invalid(cfg:Mapping[str,Any],attempt:Path,invalid:Path,reason:str,last_state:str)->None:
    out=ROOT/cfg["runtime"]["output_root"]; rec=loadj(attempt); may=bool(rec.get("payload_accessed")) or last_state in {"PHASE2_ACCESS_AUTHORIZED","CLOSED_AUTHORIZED"}
    rec.update({"state":"CLOSED_TECHNICAL_INVALID","payload_accessed":may,"launch_manifest_sha256":path_hash_or_none(ROOT/cfg["runtime"]["provenance_root"]/"launch_manifest.json"),"freeze_sha256":path_hash_or_none(ROOT/cfg["runtime"]["freeze"]),"gate_sha256":path_hash_or_none(out/"development_gate/result.json"),"updated_ns":time.time_ns()}); replace_json(attempt,rec)
    invalid.parent.mkdir(parents=True,exist_ok=True)
    exjson(invalid,{"schema_version":"canonical_induction_two_tier_v2_authorization_invalid","status":"CONFIRMATION_AUTHORIZATION_TECHNICAL_INVALID_STOP","reason":reason,"last_state":last_state,"payload_accessed_may_have_occurred":may,"attempt_token":rec["attempt_token"],"attempt_sha256":sha(attempt),"freeze_sha256":rec["freeze_sha256"],"gate_sha256":rec["gate_sha256"],"launch_manifest_sha256":rec["launch_manifest_sha256"]})


def authorize_confirmation(config:Path,launch_token:str)->None:
    cfg=require_config(config); root,attempt,auth,invalid,lock=authorization_paths(cfg); blocked=root/"CONFIRMATION_BLOCKED.json"; out=ROOT/cfg["runtime"]["output_root"]
    if attempt.exists() or root.exists(): raise FileExistsError("authorization namespace exists")
    validate_launch(cfg,launch_token); validate_development_gate(cfg)
    exjson(attempt,new_authorization_attempt(launch_token))
    with lock.open("a+") as handle:
        fcntl.flock(handle,fcntl.LOCK_EX)
        try:
            initial=validate_authorization_attempt(cfg,attempt,"PRECHECK_JOURNALED",launch_token)
            if initial["authorizer_pid"]!=os.getpid(): raise RuntimeError("authorization publisher PID mismatch")
            validate_launch(cfg,launch_token); gate_path=out/"development_gate/result.json"; launch_hash=sha(ROOT/cfg["runtime"]["provenance_root"]/"launch_manifest.json"); freeze_hash=sha(ROOT/cfg["runtime"]["freeze"]); gate_hash=sha(gate_path)
            transition_authorization_attempt(attempt,"PRECHECK_JOURNALED","PHASE1_STARTED",{"launch_manifest_sha256":launch_hash,"freeze_sha256":freeze_hash,"gate_sha256":gate_hash}); root.mkdir(parents=True)
            sealed=ROOT/cfg["runtime"]["prepared_root"]/"confirmation.jsonl"
            with deny_path_access(sealed):
                gate=validate_development_gate(cfg); verify_freeze(config,cfg,include_confirmation=False); validate_complete(cfg,"development")
            if not gate["confirmation_authorized"]:
                ar=transition_authorization_attempt(attempt,"PHASE1_STARTED","CLOSED_BLOCKED"); exjson(blocked,{"schema_version":"canonical_induction_two_tier_v2_confirmation_blocked","status":"BLOCKED","reason":"DEVELOPMENT_GATE_STOP","payload_touched":False,"registered_code_path_accessed_confirmation_payload":False,"attempt_token":ar["attempt_token"],"attempt_sha256":sha(attempt),"gate_sha256":sha(gate_path),"launch_manifest_sha256":sha(ROOT/cfg["runtime"]["provenance_root"]/"launch_manifest.json")}); return
            transition_authorization_attempt(attempt,"PHASE1_STARTED","PHASE1_PASS_BEFORE_PAYLOAD_ACCESS"); transition_authorization_attempt(attempt,"PHASE1_PASS_BEFORE_PAYLOAD_ACCESS","PHASE2_ACCESS_AUTHORIZED")
            fr=verify_freeze(config,cfg,include_confirmation=True); payload=ROOT/cfg["runtime"]["prepared_root"]/"confirmation.jsonl"; size=payload.stat().st_size; digest=sha(payload); expected=fr["confirmation_payload"]
            if size!=expected["bytes"] or digest!=expected["sha256"]: raise RuntimeError("confirmation payload mismatch")
            ar=transition_authorization_attempt(attempt,"PHASE2_ACCESS_AUTHORIZED","CLOSED_AUTHORIZED",{"payload_accessed":True,"payload_bytes":size,"payload_sha256":digest}); exjson(auth,{"schema_version":"canonical_induction_two_tier_v2_confirmation_authorization","status":"AUTHORIZED","phase1_pass":True,"phase2_pass":True,"payload_accessed":True,"payload_bytes":size,"payload_sha256":digest,"attempt_token":ar["attempt_token"],"attempt_sha256":sha(attempt),"gate_sha256":gate_hash,"development_complete_sha256":sha(out/"development/COMPLETE.json"),"freeze_sha256":freeze_hash,"launch_manifest_sha256":launch_hash})
        except Exception as e:
            close_authorization_invalid(cfg,attempt,invalid,f"{type(e).__name__}: {e}",loadj(attempt)["state"])


def reconcile_authorization(config:Path,launch_token:str)->None:
    cfg=require_config(config); validate_launch(cfg,launch_token); validate_development_gate(cfg); root,attempt,auth,invalid,lock=authorization_paths(cfg); blocked=root/"CONFIRMATION_BLOCKED.json"
    synthetic=False
    if not attempt.exists() and not any(p.exists() for p in (auth,invalid,blocked)):
        exjson(attempt,new_authorization_attempt(launch_token,"reconciled")); synthetic=True
    with lock.open("a+") as handle:
        fcntl.flock(handle,fcntl.LOCK_EX)
        terminals=[p for p in (auth,invalid,blocked) if p.exists()]
        if terminals:
            if len(terminals)!=1: raise RuntimeError("conflicting authorization terminals")
            if auth.exists(): validate_authorization(cfg,launch_token)
            elif invalid.exists(): validate_authorization_invalid(cfg)
            else: validate_blocked_authorization(cfg)
            return
        if not attempt.exists(): raise RuntimeError("authorization attempt absent")
        rec=loadj(attempt); last_state=rec["state"]
        if rec["launch_token_sha256"]!=hashlib.sha256(launch_token.encode()).hexdigest(): raise RuntimeError("authorization reconcile token mismatch")
        if not synthetic:
            try: os.kill(int(rec["authorizer_pid"]),0); raise RuntimeError("authorizer still live")
            except ProcessLookupError: pass
        close_authorization_invalid(cfg,attempt,invalid,"PREJOURNAL_AUTHORIZATION_GAP_RECONCILED" if synthetic else "INCOMPLETE_AUTHORIZATION_RECONCILED",last_state)


def validate_authorization(cfg:Mapping[str,Any],launch_token:str)->dict[str,Any]:
    validate_launch(cfg,launch_token); root,attempt,auth,invalid,_=authorization_paths(cfg); blocked=root/"CONFIRMATION_BLOCKED.json"
    if invalid.exists() or blocked.exists() or not auth.is_file(): raise RuntimeError("confirmation authorization terminal conflict/absence")
    gate=validate_development_gate(cfg); rec=loadj(auth); payload=ROOT/cfg["runtime"]["prepared_root"]/"confirmation.jsonl"; a=validate_authorization_attempt(cfg,attempt,"CLOSED_AUTHORIZED",launch_token)
    expected={"schema_version":"canonical_induction_two_tier_v2_confirmation_authorization","status":"AUTHORIZED","phase1_pass":True,"phase2_pass":True,"payload_accessed":True,"payload_bytes":payload.stat().st_size,"payload_sha256":sha(payload),"attempt_token":a["attempt_token"],"attempt_sha256":sha(attempt),"gate_sha256":sha(ROOT/cfg["runtime"]["output_root"]/"development_gate/result.json"),"development_complete_sha256":sha(ROOT/cfg["runtime"]["output_root"]/"development/COMPLETE.json"),"freeze_sha256":sha(ROOT/cfg["runtime"]["freeze"]),"launch_manifest_sha256":sha(ROOT/cfg["runtime"]["provenance_root"]/"launch_manifest.json")}
    if rec!=expected or a.get("state")!="CLOSED_AUTHORIZED" or a.get("payload_accessed") is not True or a.get("payload_bytes")!=payload.stat().st_size or a.get("payload_sha256")!=sha(payload) or a.get("freeze_sha256")!=expected["freeze_sha256"] or a.get("gate_sha256")!=expected["gate_sha256"] or a.get("launch_manifest_sha256")!=expected["launch_manifest_sha256"] or not gate["confirmation_authorized"]: raise RuntimeError("confirmation authorization lineage mismatch")
    return rec


def validate_blocked_authorization(cfg:Mapping[str,Any])->dict[str,Any]:
    root,attempt,auth,invalid,_=authorization_paths(cfg); blocked=root/"CONFIRMATION_BLOCKED.json"
    if auth.exists() or invalid.exists() or not blocked.is_file(): raise RuntimeError("blocked authorization conflict/absence")
    gate=validate_development_gate(cfg); rec=loadj(blocked); ar=validate_authorization_attempt(cfg,attempt,"CLOSED_BLOCKED")
    expected={"schema_version":"canonical_induction_two_tier_v2_confirmation_blocked","status":"BLOCKED","reason":"DEVELOPMENT_GATE_STOP","payload_touched":False,"registered_code_path_accessed_confirmation_payload":False,"attempt_token":ar["attempt_token"],"attempt_sha256":sha(attempt),"gate_sha256":sha(ROOT/cfg["runtime"]["output_root"]/"development_gate/result.json"),"launch_manifest_sha256":sha(ROOT/cfg["runtime"]["provenance_root"]/"launch_manifest.json")}
    if rec!=expected or ar.get("state")!="CLOSED_BLOCKED" or ar.get("payload_accessed") is not False or ar.get("freeze_sha256")!=sha(ROOT/cfg["runtime"]["freeze"]) or ar.get("gate_sha256")!=expected["gate_sha256"] or gate["confirmation_authorized"]: raise RuntimeError("blocked authorization lineage mismatch")
    return rec


def validate_authorization_invalid(cfg:Mapping[str,Any])->dict[str,Any]:
    root,attempt,auth,invalid,_=authorization_paths(cfg); blocked=root/"CONFIRMATION_BLOCKED.json"
    if auth.exists() or blocked.exists() or not invalid.is_file(): raise RuntimeError("authorization-invalid conflict/absence")
    rec=loadj(invalid); ar=validate_authorization_attempt(cfg,attempt,"CLOSED_TECHNICAL_INVALID")
    required={"schema_version","status","reason","last_state","payload_accessed_may_have_occurred","attempt_token","attempt_sha256","freeze_sha256","gate_sha256","launch_manifest_sha256"}
    gate_path=ROOT/cfg["runtime"]["output_root"]/"development_gate/result.json"
    if set(rec)!=required or rec["schema_version"]!="canonical_induction_two_tier_v2_authorization_invalid" or rec["status"]!="CONFIRMATION_AUTHORIZATION_TECHNICAL_INVALID_STOP" or rec["last_state"] not in {"PRECHECK_JOURNALED","PHASE1_STARTED","PHASE1_PASS_BEFORE_PAYLOAD_ACCESS","PHASE2_ACCESS_AUTHORIZED","CLOSED_AUTHORIZED","CLOSED_BLOCKED","CLOSED_TECHNICAL_INVALID"} or rec["launch_manifest_sha256"]!=sha(ROOT/cfg["runtime"]["provenance_root"]/"launch_manifest.json") or rec["freeze_sha256"]!=sha(ROOT/cfg["runtime"]["freeze"]) or not gate_path.is_file() or rec["gate_sha256"]!=sha(gate_path) or rec["gate_sha256"]!=ar.get("gate_sha256") or rec["attempt_token"]!=ar.get("attempt_token") or rec["attempt_sha256"]!=sha(attempt) or bool(ar.get("payload_accessed"))!=bool(rec["payload_accessed_may_have_occurred"]): raise RuntimeError("authorization-invalid lineage mismatch")
    return rec


def final(config:Path,launch_token:str)->None:
    cfg=require_config(config); validate_launch(cfg,launch_token); out=ROOT/cfg["runtime"]["output_root"]; target=out/"final/result.json"
    if target.exists(): raise FileExistsError(target)
    devtech=out/"development/TECHNICAL_INVALID_STOP.json"; gateinvalid=out/"development_gate/DEVELOPMENT_GATE_TECHNICAL_INVALID_STOP.json"; authroot=out/"confirmation_authorization"; contech=out/"confirmation/TECHNICAL_INVALID_STOP.json"; auth,invalid=authroot/"CONFIRMATION_AUTHORIZATION.json",authroot/"CONFIRMATION_AUTHORIZATION_TECHNICAL_INVALID_STOP.json"; blocked=authroot/"CONFIRMATION_BLOCKED.json"
    development=confirmation=None; confirmed=False; lineage={}
    if devtech.exists():
        development=validate_technical_terminal(cfg,"development"); status="TECHNICAL_INVALID_STOP"; lineage["development_technical_sha256"]=sha(devtech)
        if (out/"development_gate").exists() or authroot.exists() or (out/"confirmation").exists(): raise RuntimeError("later stage exists after development technical stop")
    elif gateinvalid.exists():
        validate_development_predecessor(cfg); validate_gate_invalid(cfg); development=loadj(out/"development/SUMMARY.json"); status="DEVELOPMENT_GATE_TECHNICAL_INVALID_STOP"; lineage.update({"development_complete_sha256":sha(out/"development/COMPLETE.json"),"development_validated_sha256":sha(development_validated_path(cfg)),"development_gate_invalid_sha256":sha(gateinvalid)})
        if authroot.exists() or (out/"confirmation").exists(): raise RuntimeError("later stage exists after development-gate technical stop")
    else:
        validate_development_predecessor(cfg); development=loadj(out/"development/SUMMARY.json"); lineage.update({"development_complete_sha256":sha(out/"development/COMPLETE.json"),"development_validated_sha256":sha(development_validated_path(cfg))})
        lineage["development_gate_sha256"]=sha(out/"development_gate/result.json")
        auth_terms=[p for p in (auth,invalid,blocked) if p.exists()]
        if len(auth_terms)!=1: raise RuntimeError("exactly one authorization terminal required")
        if invalid.exists():
            validate_authorization_invalid(cfg); status="CONFIRMATION_AUTHORIZATION_TECHNICAL_INVALID_STOP"; lineage["authorization_invalid_sha256"]=sha(invalid)
            if (out/"confirmation").exists(): raise RuntimeError("confirmation exists after invalid authorization")
        elif blocked.exists():
            validate_development_gate(cfg); validate_blocked_authorization(cfg); status=development["status"]; lineage["confirmation_blocked_sha256"]=sha(blocked)
            if (out/"confirmation").exists(): raise RuntimeError("confirmation exists after blocked authorization")
        elif contech.exists():
            validate_development_gate(cfg); validate_authorization(cfg,launch_token); confirmation=validate_technical_terminal(cfg,"confirmation"); status="TECHNICAL_INVALID_STOP"; lineage.update({"confirmation_authorization_sha256":sha(auth),"confirmation_technical_sha256":sha(contech)})
        else:
            validate_development_gate(cfg); validate_authorization(cfg,launch_token); validate_complete(cfg,"confirmation"); confirmation=loadj(out/"confirmation/SUMMARY.json"); lineage.update({"confirmation_authorization_sha256":sha(auth),"confirmation_complete_sha256":sha(out/"confirmation/COMPLETE.json")})
            confirmed=bool(development["tier_a_pass"] and development["tier_b_pass"] and confirmation["tier_a_pass"] and confirmation["tier_b_pass"]); status="TWO_TIER_TECHNICAL_CONTROL_CONFIRMED" if confirmed else confirmation["status"]
    exjson(target,{"schema_version":"canonical_induction_two_tier_v2_final","status":status,"development":development,"confirmation":confirmation,"lineage":lineage,"technical_control_confirmed":confirmed,"claim_scope":"SINGLE_MODEL_GPT2_DECODER_SKYLINE_AND_EXTERNAL_FIGURE2_UPSTREAM_SET","external_set_complete_random_token_circuit":False,"representation_methods_evaluated":False,"training_performed":False,"future_methods_automatically_authorized":False,"v1_1_modified":False,"freeze_sha256":sha(ROOT/cfg["runtime"]["freeze"]),"cache_attestation_sha256":sha(ROOT/cfg["runtime"]["cache_attestation"]),"launch_manifest_sha256":sha(ROOT/cfg["runtime"]["provenance_root"]/"launch_manifest.json")})


def main()->None:
    normalized=[token.split("=",1)[0] if token.startswith("--") else token for token in sys.argv[1:]]
    for flag in ("--config","--candidate","--pre-gate","--stage","--replicate","--launch-token","--attempt-token"):
        if normalized.count(flag)>1: raise RuntimeError(f"duplicated option forbidden: {flag}")
    parser=argparse.ArgumentParser(); sub=parser.add_subparsers(dest="command",required=True)
    def command(name:str,*,stage:bool=False,launch:bool=False,attempt:bool=False,replicate:bool=False):
        p=sub.add_parser(name); p.add_argument("--config",type=Path,required=True)
        if stage: p.add_argument("--stage",choices=["development","confirmation"],required=True)
        if replicate: p.add_argument("--replicate",type=int,choices=[1,2],required=True)
        if launch: p.add_argument("--launch-token",required=True)
        if attempt: p.add_argument("--attempt-token",required=True)
        return p
    for name in ("prepare","preservation-verify","cache-preflight","calibrate","freeze","bind-review","review-binding"): command(name)
    p=command("preflight"); group=p.add_mutually_exclusive_group(required=True); group.add_argument("--candidate",action="store_true"); group.add_argument("--pre-gate",action="store_true")
    p=command("verify-freeze"); p.add_argument("--pre-gate",action="store_true",required=True)
    command("qa-reference",stage=True,launch=True,attempt=True,replicate=True); command("qa-compare",stage=True,launch=True,attempt=True); command("worker",stage=True,launch=True,attempt=True)
    command("stage-controller",stage=True,launch=True); command("reconcile-stage",stage=True,launch=True)
    for name in ("development-gate","reconcile-development-gate","authorize-confirmation","reconcile-authorization","final"): command(name,launch=True)
    a=parser.parse_args(); cfg=require_config(a.config)
    if a.command=="prepare": prepare(a.config)
    elif a.command=="preservation-verify": preservation_verify(cfg); print('{"status":"PASS"}')
    elif a.command=="cache-preflight": cache_preflight(a.config)
    elif a.command=="calibrate": calibrate(a.config)
    elif a.command=="preflight":
        candidate_preflight(a.config) if a.candidate else pre_gate(a.config)
    elif a.command=="freeze": freeze(a.config)
    elif a.command=="verify-freeze":
        print(json.dumps({"status":"PASS","inventory":verify_freeze_pre_gate(a.config)["candidate_inventory_sha256"]}))
    elif a.command=="bind-review": bind_review(a.config)
    elif a.command=="review-binding": review_binding(a.config); print('{"status":"PASS"}')
    elif a.command=="qa-reference": qa_reference(a.config,a.stage or "",a.replicate or 0,a.launch_token,a.attempt_token)
    elif a.command=="qa-compare": qa_compare(a.config,a.stage or "",a.launch_token,a.attempt_token)
    elif a.command=="worker": worker(a.config,a.stage or "",a.launch_token,a.attempt_token)
    elif a.command=="stage-controller": stage_controller(a.config,a.stage or "",a.launch_token)
    elif a.command=="reconcile-stage": reconcile_stage(a.config,a.stage or "",a.launch_token)
    elif a.command=="development-gate": development_gate(a.config,a.launch_token)
    elif a.command=="reconcile-development-gate": reconcile_development_gate(a.config,a.launch_token)
    elif a.command=="authorize-confirmation": authorize_confirmation(a.config,a.launch_token)
    elif a.command=="reconcile-authorization": reconcile_authorization(a.config,a.launch_token)
    else: final(a.config,a.launch_token)

if __name__=="__main__": main()
