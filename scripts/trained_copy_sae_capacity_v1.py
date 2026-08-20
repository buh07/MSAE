#!/usr/bin/env python3
"""Frozen SAE capacity/selection successor for the trained synthetic copy model."""
from __future__ import annotations

import argparse, hashlib, json, os, random, signal, shutil, subprocess, sys, time
from pathlib import Path
from typing import Any, Mapping, Sequence

import numpy as np
import torch
import torch.nn.functional as F

ROOT = Path(os.environ.get("MSAE_ROOT", Path(__file__).resolve().parents[1])).resolve()
sys.path.insert(0, str(ROOT / "scripts"))
import trained_copy_method_benchmark_v1_r4_2 as base

CFG = ROOT / "configs/trained_copy_sae_capacity_v1/run.json"
PLAN = ROOT / "PLAN_TRAINED_CONTROL_NEXT_STUDIES_V1.md"
SCRIPT = Path(__file__).resolve()
TEST = ROOT / "tests/test_trained_copy_sae_capacity_v1.py"
LAUNCH_TEST = ROOT / "tests/test_launch_trained_control_next_studies_v1.py"
LAUNCHER = ROOT / "scripts/launch_trained_control_next_studies_v1_tmux.sh"


def loadj(path: Path) -> Any: return json.loads(path.read_text())
def cfg() -> dict[str, Any]: return loadj(CFG)
def canon(value: Any) -> bytes: return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
def sha(path: Path) -> str: return hashlib.sha256(path.read_bytes()).hexdigest()
def seed32(*parts: Any) -> int: return int.from_bytes(hashlib.sha256(canon(parts)).digest()[:8], "big") % (2**31 - 1)
def rng(*parts: Any) -> np.random.Generator: return np.random.default_rng(seed32(*parts))
def rp(c: Mapping[str, Any], key: str) -> Path: return ROOT / c["runtime"][key]
def confirmation_authorization(exact_identity:bool,technical:bool,_estimated:Any)->bool:return bool(exact_identity and technical)
def expected_method_count(c:Mapping[str,Any])->int:
    sae=len(c["sae"]["topks"])*len(c["sae"]["seeds"])*len(c["sae"]["selectors"])*len(c["sae"]["selector_budgets"])
    # exact + identity; two fitted bases per rank; registered random baselines;
    # random-full-rank identity QA; paired rank grid; parameter-matched paired grid.
    linear=3+2*len(c["linear"]["ranks"])+len(c["linear"]["random_ranks"])+len(c["linear"]["ranks"])*len(c["linear"]["paired_seeds"])+len(c["linear"]["paired_seeds"])
    return sae+linear
def expected_method_names(c:Mapping[str,Any])->set[str]:
    names={"exact_head_delta","identity_full64","random_rank64_identity_qa"}
    for rank in c["linear"]["ranks"]:
        names|={f"output_oracle_rank{rank}",f"ambient_pca_rank{rank}"}
        names|={f"paired_linear_rank{rank}_seed{s}" for s in c["linear"]["paired_seeds"]}
    names|={f"random_rank{rank}" for rank in c["linear"]["random_ranks"]}
    names|={f"paired_latent_width{c['linear']['parameter_match_width']}_parameter_match_seed{s}" for s in c["linear"]["paired_seeds"]}
    names|={f"sae_topk{k}_{sel}_budget{b}_seed{s}" for k in c["sae"]["topks"] for sel in c["sae"]["selectors"] for b in c["sae"]["selector_budgets"] for s in c["sae"]["seeds"]}
    if len(names)!=expected_method_count(c):raise RuntimeError("expected method inventory collision")
    return names
def is_descendant(pid:int,ancestor:int)->bool:
    for _ in range(16):
        if pid==ancestor:return True
        text=Path(f"/proc/{pid}/stat").read_text();end=text.rfind(")");parts=text[end+1:].split();pid=int(parts[1])
        if pid<=1:break
    return False
def validate_environment(c:Mapping[str,Any])->None:
    e=c["environment"];actual={"python":".".join(map(str,sys.version_info[:3])),"torch":torch.__version__.split("+")[0],"cuda":str(torch.version.cuda),"numpy":np.__version__,"pythonhashseed":os.environ.get("PYTHONHASHSEED"),"cublas_workspace_config":os.environ.get("CUBLAS_WORKSPACE_CONFIG")}
    if actual!=e:raise RuntimeError(f"environment drift: {actual} != {e}")


def atomic_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists(): raise FileExistsError(path)
    data = json.dumps(value, indent=2, sort_keys=True, allow_nan=False).encode() + b"\n"
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o444)
    with os.fdopen(fd, "wb") as handle:
        handle.write(data); handle.flush(); os.fsync(handle.fileno())


def event(root: Path, index: int, state: str, **extra: Any) -> None:
    atomic_json(root / "events" / f"{index:03d}_{state}.json", {"index": index, "state": state, "time_ns": time.time_ns(), **extra})


def panel_rows(stage: str, c: Mapping[str, Any], avoid_sham: set[tuple[int, int, int]] | None = None) -> list[dict[str, Any]]:
    pc, pool = c["panels"][stage], list(c["panels"][stage]["offsets"])
    avoid, used, rows = set(avoid_sham or set()), set(), []
    for block in range(pc["blocks"]):
        for within in range(pc["rows_per_block"]):
            ix = block * pc["rows_per_block"] + within
            if stage == "fit": target, query, replicate = within, (within + block) % 8, block // 8
            else:
                group, replicate, query = block % 4, block // 4, within
                target = 8 * group + (within + replicate) % 8
            off = pool[(target + 3 * query + replicate) % len(pool)] if stage == "fit" else pool[query % len(pool)]
            contrast = (target + off) % 32
            candidates = []
            for jump in range(1, 32):
                sham = (target + off + jump) % 32; key = (query, contrast, sham)
                if sham not in {target, contrast} and key not in avoid and key not in used: candidates.append((sham, key))
            if not candidates: raise RuntimeError(f"no sham candidate {stage}:{ix}")
            sham, key = candidates[0]; used.add(key)
            row_seed = seed32("trained_copy_sae_capacity_v1", stage, pc["seed"], ix)
            values = rng("row", row_seed).integers(0, 32, size=8).tolist(); values[query] = target
            corrupt, sham_values = values.copy(), values.copy(); corrupt[query] = contrast; sham_values[query] = sham
            rows.append({"row_id": f"tc-sae-v1-{stage}-{ix:05d}-{row_seed:08x}", "row_seed": row_seed, "stage": stage,
                         "block": block, "query": query, "target": target, "contrast": contrast, "sham": sham,
                         "offset": off, "clean_values": values, "corrupt_values": corrupt, "sham_values": sham_values})
    return rows


def panel_set(c: Mapping[str, Any]) -> dict[str, list[dict[str, Any]]]:
    out, avoid = {}, set()
    for stage in ("fit", "development", "confirmation"):
        out[stage] = panel_rows(stage, c, avoid); avoid |= {(r["query"], r["contrast"], r["sham"]) for r in out[stage]}
    return out


def freshness_audit(panels: Mapping[str, Sequence[Mapping[str, Any]]], c: Mapping[str, Any]) -> dict[str, Any]:
    ids, seeds, triples, conditions = set(), set(), set(), set()
    for path_s in c["freshness"]["opened_payloads"]:
        for row in base.read_jsonl(ROOT / path_s):
            ids.add(row["row_id"]); seeds.add(row["row_seed"])
            triples.add(canon((row["clean_values"], row["corrupt_values"], row["sham_values"])))
            conditions.add(canon((row["query"], row["target"], row["contrast"], row["sham"], row["clean_values"])))
    r5c=loadj(ROOT/c["freshness"]["r5_config"])
    for stage in ("train","development","confirmation"):
        for row in base.r5.external_rows(stage,r5c):
            ids.add(row["row_id"]);seeds.add(row["row_seed"])
            triples.add(canon((row["clean_values"],row["corrupt_values"],row["sham_values"])))
            conditions.add(canon((row["query"],row["target"],row["contrast"],row["sham"],row["clean_values"])))
    fresh = [r for rows in panels.values() for r in rows]
    result = {
        "opened_rows": len(ids), "fresh_rows": len(fresh),
        "row_id_overlap": sum(r["row_id"] in ids for r in fresh),
        "row_seed_overlap": sum(r["row_seed"] in seeds for r in fresh),
        "complete_state_triple_overlap": sum(canon((r["clean_values"], r["corrupt_values"], r["sham_values"])) in triples for r in fresh),
        "full_condition_overlap": sum(canon((r["query"], r["target"], r["contrast"], r["sham"], r["clean_values"])) in conditions for r in fresh),
        "marginals_recur_by_design": True,
    }
    result["pass"] = all(result[k] == 0 for k in ("row_id_overlap", "row_seed_overlap", "complete_state_triple_overlap", "full_condition_overlap"))
    if not result["pass"]: raise RuntimeError(f"freshness collision: {result}")
    return result


class TopKSAE(base.TopKSAE):
    def __init__(self, topk: int, seed: int, device: torch.device):
        super().__init__(64,256,topk,seed,device)


def stable_order(scores: torch.Tensor, descending: bool = True) -> list[int]:
    vals = scores.detach().cpu().double().tolist()
    return sorted(range(len(vals)), key=lambda i: ((-vals[i]) if descending else vals[i], i))


def greedy_reconstruction_order(clean_code: torch.Tensor, corrupt_code: torch.Tensor, decoder: torch.Tensor, truth: torch.Tensor) -> list[int]:
    contributions = (clean_code - corrupt_code)[:, :, None] * decoder[None, :, :]
    residual, chosen, remain = truth.clone(), [], set(range(contributions.shape[1]))
    contribution_norm = torch.sum(contributions * contributions, dim=(0,2))
    for _ in range(contributions.shape[1]):
        scores = []
        base_norm=torch.sum(residual*residual)
        candidates=sorted(remain)
        for start in range(0,len(candidates),32):
            js=candidates[start:start+32];cross=torch.einsum("nd,nkd->k",residual,contributions[:,js]);vals=base_norm-2*cross+contribution_norm[js]
            scores.extend((float(v),j) for v,j in zip(vals.detach().cpu(),js))
        _, best = min(scores, key=lambda x: (x[0], x[1])); chosen.append(best); residual -= contributions[:, best]; remain.remove(best)
    return chosen


def point_behavior_score(model: Any, z: Mapping[str, torch.Tensor], actual: torch.Tensor, sham: torch.Tensor) -> float:
    with torch.no_grad():
        ln = lambda x: F.layer_norm(x, (64,), eps=1e-5)
        patch, sham_logits = model.readout(ln(z["corrupt"] + actual)), model.readout(ln(z["corrupt"] + sham))
        clean, corrupt = z["logits_clean"], z["logits_corrupt"]; t, co = z["target"], z["contrast"]
        margin = lambda x: (32 * x[torch.arange(len(x), device=x.device), t] - x.sum(1)) / 31
        den = torch.clamp(margin(clean) - margin(corrupt), min=1e-6)
        recovery = (margin(patch) - margin(corrupt)) / den; sham_response = (margin(sham_logits) - margin(corrupt)) / den
        scale = torch.clamp(torch.sqrt(torch.mean(((clean-clean.mean(1,keepdim=True))-(corrupt-corrupt.mean(1,keepdim=True)))**2,1)), min=1e-6)
        full = 1-torch.sqrt(torch.mean(((patch-patch.mean(1,keepdim=True))-(clean-clean.mean(1,keepdim=True)))**2,1))/scale
        coll=[]
        for i in range(len(t)):
            mask=torch.ones(32,dtype=torch.bool,device=t.device);mask[t[i]]=False;mask[co[i]]=False
            coll.append(torch.sqrt(torch.mean(((patch[i]-patch[i].mean())-(clean[i]-clean[i].mean()))[mask]**2))/scale[i])
        score = torch.mean(recovery + full + (recovery-sham_response) - torch.stack(coll))
        return float(score.detach().cpu()) if torch.isfinite(score) else float("-inf")


def greedy_behavior_order(sae: TopKSAE, model: Any, z: Mapping[str, torch.Tensor]) -> list[int]:
    with torch.no_grad():
        cc, rc, sc = sae.encode(z["clean"]), sae.encode(z["corrupt"]), sae.encode(z["sham"])
        ac = (cc-rc)[:, :, None] * sae.decoder[None, :, :]
        sh = (sc-rc)[:, :, None] * sae.decoder[None, :, :]
    current, current_s, chosen, remain = torch.zeros_like(z["delta"]), torch.zeros_like(z["delta"]), [], set(range(256));n=len(z["delta"]);t=z["target"];co=z["contrast"]
    with torch.no_grad():
        clean,corrupt=z["logits_clean"],z["logits_corrupt"];idx=torch.arange(n,device=t.device);margin=lambda x:(32*x[...,idx,t]-x.sum(-1))/31 if x.ndim==3 else (32*x[idx,t]-x.sum(-1))/31
        den=margin(clean)-margin(corrupt);eligible=(torch.argmax(clean,1)==t)&(torch.argmax(corrupt,1)==co)&(den>1.0)
        if int(eligible.sum()) < int(np.ceil(.95*n)): raise RuntimeError("greedy behavioral selector lacks eligible fit support")
        scale=torch.clamp(torch.sqrt(torch.mean(((clean-clean.mean(1,keepdim=True))-(corrupt-corrupt.mean(1,keepdim=True)))**2,1)),min=1e-6);mask=torch.ones(n,32,dtype=torch.bool,device=t.device);mask[idx,t]=False;mask[idx,co]=False
    for _ in range(256):
        candidates=sorted(remain);all_scores=[]
        js=candidates;A=current[None]+ac[:,js].permute(1,0,2);S=current_s[None]+sh[:,js].permute(1,0,2)
        with torch.no_grad():
            patch=model.readout(F.layer_norm(z["corrupt"][None]+A,(64,),eps=1e-5));sham_logits=model.readout(F.layer_norm(z["corrupt"][None]+S,(64,),eps=1e-5));rec=(margin(patch)-margin(corrupt)[None])/torch.clamp(den[None],min=1e-6);sr=(margin(sham_logits)-margin(corrupt)[None])/torch.clamp(den[None],min=1e-6);full=1-torch.sqrt(torch.mean(((patch-patch.mean(-1,keepdim=True))-(clean[None]-clean.mean(1,keepdim=True)))**2,-1))/scale[None];err=((patch-patch.mean(-1,keepdim=True))-(clean[None]-clean.mean(1,keepdim=True)))**2;coll=torch.sqrt((err*mask[None]).sum(-1)/mask.sum(-1)[None])/scale[None];score=torch.mean((rec+full+(rec-sr)-coll)[:,eligible],1);all_scores.extend((float(v),j) for v,j in zip(score.cpu(),js))
        _, best=max(all_scores,key=lambda x:(x[0],-x[1]));chosen.append(best);current+=ac[:,best];current_s+=sh[:,best];remain.remove(best)
    return chosen


def fit_sae(model: Any, rows: Sequence[Mapping[str, Any]], c: Mapping[str, Any], topk: int, seed: int, device: torch.device) -> tuple[TopKSAE, dict[str, Any]]:
    z = base.context(model, rows, device); states = torch.cat([z["clean"], z["corrupt"], z["sham"]]).detach()
    sae = TopKSAE(topk, seed, device); opt = torch.optim.Adam(sae.parameters(), lr=c["sae"]["learning_rate"])
    gen = torch.Generator(device=device).manual_seed(seed32("sae-fit", seed, topk)); losses=[]
    for step in range(c["sae"]["steps"]):
        ix=torch.randint(0,len(states),(c["sae"]["batch_size"],),generator=gen,device=device); loss=F.mse_loss(sae(states[ix]),states[ix])
        if not torch.isfinite(loss): raise FloatingPointError("nonfinite SAE loss")
        opt.zero_grad(set_to_none=True);loss.backward();opt.step()
        if step in {0,c["sae"]["steps"]-1}: losses.append(float(loss.detach().cpu()))
    with torch.no_grad():
        cc,rc=sae.encode(z["clean"]),sae.encode(z["corrupt"]); ambient=sae.encode(states)
        orders={"variance":stable_order(ambient.var(0,unbiased=False)),"paired_change":stable_order(torch.mean(torch.abs(cc-rc),0)),
                "greedy_paired_reconstruction":greedy_reconstruction_order(cc,rc,sae.decoder,z["delta"])}
    orders["greedy_fit_behavior"] = greedy_behavior_order(sae, model, z)
    with torch.no_grad():
        reconstruction=sae(states);ambient_rel=float(torch.linalg.norm(reconstruction-states)/torch.clamp(torch.linalg.norm(states),min=1e-12))
        full_actual,_=sae_prediction(sae,list(range(256)),z);delta_rel=float(torch.linalg.norm(full_actual-z["delta"])/torch.clamp(torch.linalg.norm(z["delta"]),min=1e-12))
    return sae,{"initial_loss":losses[0],"final_loss":losses[-1],"ambient_reconstruction_relative_l2":ambient_rel,"full_code_delta_relative_l2":delta_rel,"trainable_parameters":sum(p.numel() for p in sae.parameters()),"selectors":orders}


def sae_prediction(sae: TopKSAE, selected: Sequence[int], z: Mapping[str, torch.Tensor]) -> tuple[torch.Tensor, torch.Tensor]:
    sel=torch.tensor(selected,device=z["clean"].device);zc=sae.encode(z["corrupt"]);base_dec=sae.decode(zc);za=zc.clone();zs=zc.clone();za[:,sel]=sae.encode(z["clean"])[:,sel];zs[:,sel]=sae.encode(z["sham"])[:,sel]
    return sae.decode(za)-base_dec,sae.decode(zs)-base_dec


def create_lock() -> dict[str,Any]:
    c=cfg();candidate_sha=sha(rp(c,"candidate_manifest"));verify_review(rp(c,"candidate_review"),candidate_sha)
    payload={"schema_version":"trained_copy_sae_capacity_v1_generator_lock","source_sha256":sha(SCRIPT),"config_sha256":sha(CFG),"plan_sha256":sha(PLAN),"tests_sha256":{"study":sha(TEST),"launcher":sha(LAUNCH_TEST)},"launcher_sha256":sha(LAUNCHER),"candidate_sha256":candidate_sha,"candidate_review_sha256":sha(rp(c,"candidate_review")),"method_table_sha256":hashlib.sha256(canon({"sae":c["sae"],"linear":c["linear"]})).hexdigest()};atomic_json(rp(c,"generator_lock"),payload);return payload

def prepare() -> dict[str, Any]:
    c=cfg(); root=rp(c,"prepared_root")
    if root.exists(): raise FileExistsError(root)
    lock=loadj(rp(c,"generator_lock"))
    if lock["source_sha256"]!=sha(SCRIPT) or lock["config_sha256"]!=sha(CFG) or lock["candidate_sha256"]!=sha(rp(c,"candidate_manifest")) or lock["candidate_review_sha256"]!=sha(rp(c,"candidate_review")):raise RuntimeError("generator lock drift")
    panels=panel_set(c); audit=freshness_audit(panels,c); root.mkdir(parents=True)
    payload=[]
    for stage,rows in panels.items():
        path=root/f"{stage}.jsonl";base.write_jsonl(path,rows);payload.append({"stage":stage,"path":path.relative_to(ROOT).as_posix(),"rows":len(rows),"sha256":sha(path)})
    out={"schema_version":"trained_copy_sae_capacity_v1_prepared","status":"PREPARED_UNOPENED","freshness":audit,"payloads":payload}
    atomic_json(root/"PREPARED.json",out);return out


def candidate(device: str, record: bool) -> dict[str, Any]:
    c=cfg(); dev=torch.device(device); torch.manual_seed(1); x=torch.randn(32,64,device=dev);sae=TopKSAE(16,1,dev);z=sae.encode(x)
    cc=torch.randn(12,256,device=dev);rc=torch.randn(12,256,device=dev);truth=torch.randn(12,64,device=dev)
    order=greedy_reconstruction_order(cc,rc,sae.decoder,truth)
    names=expected_method_names(c);result={"schema_version":"trained_copy_sae_capacity_v1_candidate","status":"PASS","scientific_panel_accessed":False,"expected_method_count_per_checkpoint":len(names),"method_inventory_sha256":hashlib.sha256(canon(sorted(names))).hexdigest(),
            "checks":{"topk":bool(torch.all((z!=0).sum(1)<=16)),"selector_permutation":sorted(order)==list(range(256)),"finite":bool(torch.isfinite(z).all()),"sae_parameter_count":sum(p.numel() for p in sae.parameters())==32832,"authorization_outcome_independent":confirmation_authorization(True,True,{"fail":True}) and confirmation_authorization(True,True,{"pass":True})},
            "source_sha256":sha(SCRIPT),"config_sha256":sha(CFG),"plan_sha256":sha(PLAN),"tests_sha256":{"study":sha(TEST),"launcher":sha(LAUNCH_TEST)},"launcher_sha256":sha(LAUNCHER)}
    if record: atomic_json(rp(c,"candidate_manifest"),result)
    return result


def freeze() -> dict[str, Any]:
    c=cfg(); prepared=loadj(rp(c,"prepared_root")/"PREPARED.json")
    frozen={"schema_version":"trained_copy_sae_capacity_v1_freeze","generator_lock_sha256":sha(rp(c,"generator_lock")),"payloads":prepared["payloads"],"freshness":prepared["freshness"]}
    atomic_json(rp(c,"freeze"),frozen);return frozen


def verify_review(path: Path, bound: str) -> None:
    text=path.read_text(); verdicts=[x.strip() for x in text.splitlines() if x.startswith("VERDICT:")]
    if verdicts != ["VERDICT: SHIP"] or f"BOUND_SHA256: {bound}" not in text: raise RuntimeError(f"review not SHIP/bound: {path}")


def verify_frozen() -> dict[str, Any]:
    c=cfg(); lock=loadj(rp(c,"generator_lock")); frozen=loadj(rp(c,"freeze"))
    if lock["source_sha256"]!=sha(SCRIPT) or lock["config_sha256"]!=sha(CFG) or lock["candidate_sha256"]!=sha(rp(c,"candidate_manifest")) or lock["candidate_review_sha256"]!=sha(rp(c,"candidate_review")) or frozen["generator_lock_sha256"]!=sha(rp(c,"generator_lock")):raise RuntimeError("freeze drift")
    for rec in frozen["payloads"]:
        p=ROOT/rec["path"]
        if sha(p)!=rec["sha256"]:raise RuntimeError("payload drift")
    binding=loadj(rp(c,"review_binding"));verify_review(rp(c,"candidate_review"),binding["candidate_bound_sha256"]);verify_review(rp(c,"frozen_review"),binding["freeze_bound_sha256"])
    if binding["candidate_bound_sha256"]!=sha(rp(c,"candidate_manifest")) or binding["freeze_bound_sha256"]!=sha(rp(c,"freeze")):raise RuntimeError("review binding drift")
    return {"status":"PASS","payloads":len(frozen["payloads"])}


def load_model(c: Mapping[str, Any], seed: int, device: torch.device) -> Any:
    return base.load_model(c,seed,device)


def run(physical_index: int, gpu_uuid: str, pane_pid:int, lockdir: str, token: str) -> None:
    c=cfg();validate_environment(c);verify_frozen(); out=rp(c,"output_root");prov=rp(c,"provenance_root")
    if out.exists() or prov.exists():raise FileExistsError("scientific namespace exists")
    if os.environ.get("CUDA_VISIBLE_DEVICES")!=gpu_uuid:raise RuntimeError("GPU UUID visibility mismatch")
    if Path(lockdir).name!=f"msae_gpu_{gpu_uuid}.lockdir" or (Path(lockdir)/"token").read_text().strip()!=token:raise RuntimeError("GPU lock mismatch")
    manifest=loadj(rp(c,"launch_manifest"))
    if manifest!={"gpu_uuid":gpu_uuid,"physical_index":physical_index,"pane_pid":pane_pid,"session":c["runtime"]["tmux_session"],"token_sha256":hashlib.sha256(token.encode()).hexdigest()}:raise RuntimeError("launch manifest mismatch")
    if not is_descendant(os.getpid(),pane_pid):raise RuntimeError("worker is not pane descendant")
    device=torch.device("cuda:0");torch.use_deterministic_algorithms(True);random.seed(c["seed"]);np.random.seed(c["seed"]);torch.manual_seed(c["seed"]);torch.ones(1,device=device).sum().item();torch.cuda.synchronize()
    out.mkdir(parents=True);prov.mkdir(parents=True);state={"panel_accessed":False,"confirmation_opened":False}
    event(prov,0,"RUN_START_NO_PANEL_ACCESS",physical_index=physical_index,gpu_uuid=gpu_uuid,pid=os.getpid());event(prov,1,"GPU_LOCK_OWNERSHIP_TRANSFERRED",lockdir=lockdir)
    freeze_rec=loadj(rp(c,"freeze"));payloads={r["stage"]:ROOT/r["path"] for r in freeze_rec["payloads"]}
    event(prov,10,"FIT_ACCESS_MAY_HAVE_OCCURRED");state["panel_accessed"]=True;fit=base.read_jsonl(payloads["fit"]);event(prov,11,"FIT_OPENED",rows=len(fit))
    models, fit_records={},{}
    for model_seed in c["model"]["seeds"]:
        model=load_model(c,model_seed,device);models[model_seed]=model;zfit=base.context(model,fit,device);entries={}
        ck=out/"checkpoints"/str(model_seed);ck.mkdir(parents=True)
        delta=zfit["delta"].detach();_,_,oracle=base.canonical_svd(delta.cpu().numpy());states=torch.cat([zfit["clean"],zfit["corrupt"],zfit["sham"]]);_,ambient=base.fit_unpaired_ambient_basis(states)
        np.savez(ck/"linear_bases.npz",oracle=oracle,ambient=ambient);entries["linear_bases"]={"sha256":sha(ck/"linear_bases.npz")}
        linear_cfg={"steps":c["linear"]["steps"],"batch_size":c["linear"]["batch_size"],"learning_rate":c["linear"]["learning_rate"]}
        for width in c["linear"]["ranks"]+[c["linear"]["parameter_match_width"]]:
            label=f"rank{width}" if width in c["linear"]["ranks"] else f"latent_width{width}_parameter_match"
            for method_seed in c["linear"]["paired_seeds"]:
                mdl=base.r5.FactorLinear(64,width,method_seed,device);rec=base.train_generic(mdl,delta,delta,zfit["target"],linear_cfg,seed32("paired",model_seed,width,method_seed));path=ck/f"paired_{label}_seed{method_seed}.pt"
                torch.save({"state_dict":mdl.state_dict(),"width":width,"seed":method_seed},path);entries[f"paired_{label}_seed{method_seed}"]={**rec,"sha256":sha(path),"empirical_rank":int(np.linalg.matrix_rank((mdl.u@mdl.v).detach().cpu().numpy()))}
        for topk in c["sae"]["topks"]:
            for method_seed in c["sae"]["seeds"]:
                sae,rec=fit_sae(model,fit,c,topk,method_seed,device);path=ck/f"sae_topk{topk}_seed{method_seed}.pt"
                torch.save({"state_dict":sae.state_dict(),"topk":topk,"seed":method_seed,"selectors":rec["selectors"]},path)
                entries[f"sae_topk{topk}_seed{method_seed}"]={**rec,"sha256":sha(path)}
        fit_records[str(model_seed)]=entries;atomic_json(out/"fit"/f"model_{model_seed}.json",entries)
    event(prov,20,"DEVELOPMENT_ACCESS_MAY_HAVE_OCCURRED");dev_rows=base.read_jsonl(payloads["development"]);event(prov,21,"DEVELOPMENT_OPENED",rows=len(dev_rows))
    def evaluate(stage:str,rows:Sequence[Mapping[str,Any]])->dict[str,Any]:
        all_models={}
        for model_seed,model in models.items():
            z=base.context(model,rows,device);methods={}
            bases=np.load(out/"checkpoints"/str(model_seed)/"linear_bases.npz")
            def add_scored(name:str,p:torch.Tensor,ps:torch.Tensor,rank:int|None=None,role:str="scientific") -> None:
                obj=base.Method(name,name,"matrix",None,rank=rank);native=base.score(obj,p,ps,z,rows,c,stage,model,"native")
                pm,ok=base.r5.norm_match(p.detach().cpu().numpy(),z["delta"].detach().cpu().numpy());sm,ok2=base.r5.norm_match(ps.detach().cpu().numpy(),z["delta"].detach().cpu().numpy());status="complete" if bool(ok.all() and ok2.all()) else "prediction_incomplete"
                matched=base.score(obj,torch.tensor(pm,dtype=torch.float32,device=device),torch.tensor(sm,dtype=torch.float32,device=device),z,rows,c,stage,model,"matched",status)
                pn=torch.linalg.norm(p,dim=1);tn=torch.linalg.norm(z["delta"],dim=1);methods[name]={"rank":rank,"role":role,"direction_cosine":float(torch.mean(torch.sum(p*z["delta"],1)/torch.clamp(pn*tn,min=1e-12)).cpu()),"relative_l2":float(torch.mean(torch.linalg.norm(p-z["delta"],dim=1)/torch.clamp(tn,min=1e-12)).cpu()),"mean_patch_norm":float(torch.mean(pn).cpu()),"empirical_output_rank":int(np.linalg.matrix_rank(p.detach().cpu().numpy(),tol=1e-6)),"native":native,"matched":matched,"all_gates_pass":native["all_gates_pass"] and matched["all_gates_pass"]}
            for rank in c["linear"]["ranks"]:
                for family,key in (("output_oracle","oracle"),("ambient_pca","ambient")):
                    B=torch.tensor(bases[key][:rank],dtype=torch.float32,device=device);add_scored(f"{family}_rank{rank}",z["delta"]@B.T@B,z["sham_delta"]@B.T@B,rank)
                for method_seed in c["linear"]["paired_seeds"]:
                    mdl=base.r5.FactorLinear(64,rank,method_seed,device);saved=torch.load(out/"checkpoints"/str(model_seed)/f"paired_rank{rank}_seed{method_seed}.pt",map_location=device,weights_only=False);mdl.load_state_dict(saved["state_dict"]);mdl.eval()
                    with torch.no_grad():p=mdl(z["delta"],z["target"]);ps=mdl(z["sham_delta"],z["target"])
                    add_scored(f"paired_linear_rank{rank}_seed{method_seed}",p,ps,rank)
            for rank in c["linear"]["random_ranks"]:
                q=base.r5.qr_canonical(rng("random",c["linear"]["random_seed"],model_seed,rank).normal(size=(64,64)))[:,:rank];B=torch.tensor(q.T,dtype=torch.float32,device=device);add_scored(f"random_rank{rank}",z["delta"]@B.T@B,z["sham_delta"]@B.T@B,rank)
            q=base.r5.qr_canonical(rng("random",c["linear"]["random_seed"],model_seed,64).normal(size=(64,64)));B=torch.tensor(q.T,dtype=torch.float32,device=device);add_scored("random_rank64_identity_qa",z["delta"]@B.T@B,z["sham_delta"]@B.T@B,64,"identity_equivalent_qa")
            width=c["linear"]["parameter_match_width"]
            for method_seed in c["linear"]["paired_seeds"]:
                mdl=base.r5.FactorLinear(64,width,method_seed,device);saved=torch.load(out/"checkpoints"/str(model_seed)/f"paired_latent_width{width}_parameter_match_seed{method_seed}.pt",map_location=device,weights_only=False);mdl.load_state_dict(saved["state_dict"]);mdl.eval()
                with torch.no_grad():p=mdl(z["delta"],z["target"]);ps=mdl(z["sham_delta"],z["target"])
                add_scored(f"paired_latent_width{width}_parameter_match_seed{method_seed}",p,ps,int(np.linalg.matrix_rank((mdl.u@mdl.v).detach().cpu().numpy())))
            for topk in c["sae"]["topks"]:
                for method_seed in c["sae"]["seeds"]:
                    saved=torch.load(out/"checkpoints"/str(model_seed)/f"sae_topk{topk}_seed{method_seed}.pt",map_location=device,weights_only=False);sae=TopKSAE(topk,method_seed,device);sae.load_state_dict(saved["state_dict"]);sae.eval()
                    for selector,order in saved["selectors"].items():
                        for budget in c["sae"]["selector_budgets"]:
                            p,ps=sae_prediction(sae,order[:budget],z);name=f"sae_topk{topk}_{selector}_budget{budget}_seed{method_seed}"
                            native=base.score(base.Method(name,name,"sae",None),p,ps,z,rows,c,stage,model,"native")
                            pm,ok=base.r5.norm_match(p.cpu().numpy(),z["delta"].cpu().numpy());sm,ok2=base.r5.norm_match(ps.cpu().numpy(),z["delta"].cpu().numpy());status="complete" if bool(ok.all() and ok2.all()) else "prediction_incomplete"
                            matched=base.score(base.Method(name,name,"sae",None),torch.tensor(pm,device=device),torch.tensor(sm,device=device),z,rows,c,stage,model,"matched",status)
                            pn=torch.linalg.norm(p,dim=1);tn=torch.linalg.norm(z["delta"],dim=1)
                            methods[name]={"topk":topk,"budget":budget,"selector":selector,"seed":method_seed,"primary":budget>=topk,"trainable_parameters":sum(x.numel() for x in sae.parameters()),"selector_decoder_storage_coordinates":budget*64,"decoded_empirical_rank":int(np.linalg.matrix_rank(p.cpu().numpy(),tol=1e-6)),"mean_patch_norm":float(torch.mean(pn).cpu()),"direction_cosine":float(torch.mean(torch.sum(p*z["delta"],1)/torch.clamp(pn*tn,min=1e-12)).cpu()),"relative_l2":float(torch.mean(torch.linalg.norm(p-z["delta"],dim=1)/torch.clamp(tn,min=1e-12)).cpu()),"native":native,"matched":matched,"all_gates_pass":native["all_gates_pass"] and matched["all_gates_pass"]}
            exact=base.Method("exact_head_delta","exact_head_delta","exact",None);p,ps=base.predict(exact,z,model);add_scored("exact_head_delta",p,ps,64);add_scored("identity_full64",p,ps,64)
            if set(methods)!=expected_method_names(c):raise RuntimeError(f"method inventory mismatch: missing={expected_method_names(c)-set(methods)} extra={set(methods)-expected_method_names(c)}")
            all_models[str(model_seed)]={"methods":methods}
            atomic_json(out/stage/f"model_{model_seed}.json",all_models[str(model_seed)])
        return all_models
    dev=evaluate("development",dev_rows)
    exact_ok=all(v["methods"][name]["all_gates_pass"] for v in dev.values() for name in ("exact_head_delta","identity_full64"));pre={"exact_identity_authorized":exact_ok,"estimated_method_outcomes_used_for_authorization":False,"confirmation_authorized":confirmation_authorization(exact_ok,True,None)}
    atomic_json(out/"PRECONFIRMATION.json",pre);event(prov,30,"PRECONFIRMATION_SEALED",confirmation_authorized=exact_ok)
    if not exact_ok:atomic_json(prov/"TERMINAL.json",{"status":"DEVELOPMENT_TECHNICAL_STOP","no_retry_authorized":True});return
    event(prov,40,"CONFIRMATION_ACCESS_MAY_HAVE_OCCURRED");state["confirmation_opened"]=True;conf_rows=base.read_jsonl(payloads["confirmation"]);event(prov,41,"CONFIRMATION_OPENED",rows=len(conf_rows));conf=evaluate("confirmation",conf_rows)
    def family(name:str)->str:
        return name.rsplit("_seed",1)[0] if "_seed" in name else name
    scientific_names={n for panel in (dev,conf) for model_rec in panel.values() for n,r in model_rec["methods"].items() if r.get("role","scientific")=="scientific"}
    family_pass={fam:all(panel[str(ms)]["methods"][n]["all_gates_pass"] for panel in (dev,conf) for ms in c["model"]["seeds"] for n in scientific_names if family(n)==fam) for fam in sorted({family(n) for n in scientific_names})}
    final={"schema_version":"trained_copy_sae_capacity_v1_final","status":"SAE_CAPACITY_COMPLETE","confirmation_opened":True,"fits":fit_records,"development":dev,"confirmation":conf,"family_pass_all_panels_checkpoints_method_seeds_estimands":family_pass,"random_rank64_classification":"identity_equivalent_qa_not_random_baseline","scope":c["scope"]}
    atomic_json(out/"final"/"result.json",final);event(prov,50,"TERMINAL_COMPLETE",final_sha256=sha(out/"final"/"result.json"));atomic_json(prov/"TERMINAL.json",{"status":"SAE_CAPACITY_COMPLETE","no_retry_authorized":True,"final_sha256":sha(out/"final"/"result.json")})


def main() -> None:
    ap=argparse.ArgumentParser();sp=ap.add_subparsers(dest="cmd",required=True)
    q=sp.add_parser("candidate");q.add_argument("--device",default="cpu");q.add_argument("--record",action="store_true")
    sp.add_parser("create-lock");sp.add_parser("prepare");sp.add_parser("freeze");sp.add_parser("verify-frozen")
    q=sp.add_parser("run");q.add_argument("--physical-index",type=int,required=True);q.add_argument("--gpu-uuid",required=True);q.add_argument("--pane-pid",type=int,required=True);q.add_argument("--gpu-lockdir",required=True);q.add_argument("--launch-token",required=True)
    a=ap.parse_args()
    if a.cmd=="candidate":print(json.dumps(candidate(a.device,a.record),sort_keys=True))
    elif a.cmd=="create-lock":print(json.dumps(create_lock(),sort_keys=True))
    elif a.cmd=="prepare":print(json.dumps(prepare(),sort_keys=True))
    elif a.cmd=="freeze":print(json.dumps(freeze(),sort_keys=True))
    elif a.cmd=="verify-frozen":print(json.dumps(verify_frozen(),sort_keys=True))
    else:run(a.physical_index,a.gpu_uuid,a.pane_pid,a.gpu_lockdir,a.launch_token)


if __name__=="__main__":main()
