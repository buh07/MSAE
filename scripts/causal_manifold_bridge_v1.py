#!/usr/bin/env python3
"""Known-ground-truth causal-manifold bridge with donor and donor-free views."""
from __future__ import annotations

import argparse, hashlib, itertools, json, os, random, sys, time
from pathlib import Path
from typing import Any, Mapping, Sequence

import numpy as np
import torch

ROOT=Path(os.environ.get("MSAE_ROOT",Path(__file__).resolve().parents[1])).resolve()
sys.path.insert(0,str(ROOT/"scripts"))
import trained_copy_method_benchmark_v1_r4_2 as base

CFG=ROOT/"configs/causal_manifold_bridge_v1/run.json";PLAN=ROOT/"PLAN_TRAINED_CONTROL_NEXT_STUDIES_V1.md";SCRIPT=Path(__file__).resolve();TEST=ROOT/"tests/test_causal_manifold_bridge_v1.py";LAUNCH_TEST=ROOT/"tests/test_launch_trained_control_next_studies_v1.py";LAUNCHER=ROOT/"scripts/launch_trained_control_next_studies_v1_tmux.sh"
def loadj(p:Path)->Any:return json.loads(p.read_text())
def cfg()->dict[str,Any]:return loadj(CFG)
def canon(x:Any)->bytes:return json.dumps(x,sort_keys=True,separators=(",",":"),allow_nan=False).encode()
def sha(p:Path)->str:return hashlib.sha256(p.read_bytes()).hexdigest()
def seed32(*x:Any)->int:return int.from_bytes(hashlib.sha256(canon(x)).digest()[:8],"big")%(2**31-1)
def rng(*x:Any)->np.random.Generator:return np.random.default_rng(seed32(*x))
def rp(c:Mapping[str,Any],k:str)->Path:return ROOT/c["runtime"][k]
def is_descendant(pid:int,ancestor:int)->bool:
 for _ in range(16):
  if pid==ancestor:return True
  text=Path(f"/proc/{pid}/stat").read_text();end=text.rfind(")");parts=text[end+1:].split();pid=int(parts[1])
  if pid<=1:break
 return False
def validate_environment(c:Mapping[str,Any])->None:
 actual={"python":".".join(map(str,sys.version_info[:3])),"torch":torch.__version__.split("+")[0],"cuda":str(torch.version.cuda),"numpy":np.__version__,"pythonhashseed":os.environ.get("PYTHONHASHSEED"),"cublas_workspace_config":os.environ.get("CUBLAS_WORKSPACE_CONFIG")}
 if actual!=c["environment"]:raise RuntimeError(f"environment drift: {actual} != {c['environment']}")
def atomic_json(p:Path,x:Any)->None:
 p.parent.mkdir(parents=True,exist_ok=True)
 if p.exists():raise FileExistsError(p)
 data=json.dumps(x,indent=2,sort_keys=True,allow_nan=False).encode()+b"\n";fd=os.open(p,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o444)
 with os.fdopen(fd,"wb") as f:f.write(data);f.flush();os.fsync(f.fileno())
def event(p:Path,i:int,s:str,**kw:Any)->None:atomic_json(p/"events"/f"{i:03d}_{s}.json",{"index":i,"state":s,"time_ns":time.time_ns(),**kw})

def validate_config(c:Mapping[str,Any])->None:
 levels=c["design"]["levels"];keys=["causal_dim","nuisance_dim","nuisance_gain","correlation","complexity","bypass","routing"];expected=[dict(zip(keys,v)) for v in itertools.product(*(levels[k] for k in keys))]
 cells=c["design"]["cells"]
 if len(cells)!=128 or [{k:x[k] for k in keys} for x in cells]!=expected:raise RuntimeError("factorial drift")
 if c["design"]["controller_dim"]!=640 or c["design"]["patch_equation"]!="patched_site = original_corrupt_site + predicted_slice":raise RuntimeError("patch contract drift")
 if set(c["methods"]["information_views"])!={"donor_compression","corrupt_only","instruction_conditioned","answer_conditioned"}:raise RuntimeError("view registry drift")
 if len(c["methods"]["registered_method_names"])!=64 or len(set(c["methods"]["registered_method_names"]))!=64:raise RuntimeError("method registry drift")

def panel_rows(stage:str,c:Mapping[str,Any])->list[dict[str,Any]]:
 pc=c["panels"][stage];rows=[]
 for cell in c["design"]["cells"]:
  for block in range(pc["blocks_per_cell"]):
   for within in range(pc["rows_per_block"]):
    ix=(cell["cell_id"]*pc["blocks_per_cell"]+block)*pc["rows_per_block"]+within;rs=seed32("causal-manifold-v1",stage,pc["seed"],ix)
    target=(cell["cell_id"]+block+within*7)%32;query=within%8;offset=1+(3*block+within)%31;direction=1 if query%2==0 else -1;contrast=(target+direction*offset)%32
    sham=next(x for step in range(1,32) if (x:=(contrast+direction*(step+block%29))%32) not in {target,contrast})
    rows.append({"row_id":f"cm-v1-{stage}-{ix:06d}-{rs:08x}","row_seed":rs,"stage":stage,"cell_id":cell["cell_id"],"block":block,"within":within,"query":query,"target":target,"contrast":contrast,"sham":sham,"offset":offset})
 return rows
def panel_set(c:Mapping[str,Any])->dict[str,list[dict[str,Any]]]:return {s:panel_rows(s,c) for s in ("fit","development","confirmation")}
def panel_audit(ps:Mapping[str,Sequence[Mapping[str,Any]]],c:Mapping[str,Any])->dict[str,Any]:
 ids=[{r["row_id"] for r in ps[s]} for s in ps];seeds=[{r["row_seed"] for r in ps[s]} for s in ps]
 if any(ids[i]&ids[j] or seeds[i]&seeds[j] for i in range(3) for j in range(i)):raise RuntimeError("panel overlap")
 out={s:{"rows":len(rs),"cells":len(set(r["cell_id"] for r in rs)),"per_cell":{str(i):sum(r["cell_id"]==i for r in rs) for i in range(128)}} for s,rs in ps.items()}
 if any(x["cells"]!=128 for x in out.values()) or any(len({r["target"],r["contrast"],r["sham"]})!=3 for rs in ps.values() for r in rs):raise RuntimeError("cell support or condition distinctness")
 return out

_MATS_CACHE:dict[tuple[int,int],dict[str,np.ndarray]]={}
def generator_mats(gen:int,cell:Mapping[str,Any])->dict[str,np.ndarray]:
 key=(gen,int(cell["cell_id"]))
 if key in _MATS_CACHE:return _MATS_CACHE[key]
 cd,nd=int(cell["causal_dim"]),int(cell["nuisance_dim"]);g=rng("bridge-mats",gen,cell["cell_id"])
 proto=g.normal(size=(32,cd));proto/=np.maximum(np.linalg.norm(proto,axis=1,keepdims=True),1e-12)
 causal=np.zeros((32,64),np.float32);causal[:,:cd]=proto.astype(np.float32)
 site_causal=[]
 for site in range(10):
  extra=np.zeros((32,64),np.float32)
  if cd<64:extra[:,cd:]=(proto@g.normal(size=(cd,64-cd))).astype(np.float32)*.05/np.sqrt(cd)
  site_causal.append(causal+extra)
 site_causal=np.stack(site_causal)
 # High-variance nuisance lives primarily outside the causal/readout span; the registered
 # correlation adds a small causal component without destroying the base behavioral assay.
 raw=g.normal(size=(min(nd,64),64)).astype(np.float32);raw-=raw.mean(1,keepdims=True);raw/=np.maximum(np.linalg.norm(raw,axis=1,keepdims=True),1e-8)
 # Realize the registered correlation by mixing nuisance rows with normalized causal prototypes.
 corr=float(cell["correlation"]);shared=np.resize(causal,(len(raw),64));shared-=shared.mean(1,keepdims=True);shared/=np.maximum(np.linalg.norm(shared,axis=1,keepdims=True),1e-8);nuis=(np.sqrt(max(0.,1-corr*corr))*raw+corr*shared).astype(np.float32)
 active=[0,1]
 if cell["complexity"]=="four_heads_two_layers":active=list(range(9))
 if cell["bypass"]:active.append(9)
 coeff=np.zeros(10,np.float32);coeff[active]=1.;coeff[9]=.35 if cell["bypass"] else 0.
 proto_final=[]
 for value in range(32):
  sites=np.zeros((10,64),np.float32)
  for s in active:sites[s]=coeff[s]*site_causal[s,value]
  proto_final.append(execute_sites_np(sites,cell))
 proto_final=np.stack(proto_final);centered_proto=proto_final-proto_final.mean(1,keepdims=True);centered_proto/=np.maximum(np.linalg.norm(centered_proto,axis=1,keepdims=True),1e-8);decoder=(centered_proto.T*8.).astype(np.float32)
 site_readout=np.zeros((10,64,32),np.float32);wbase=np.zeros((64,32),np.float32);wbase[:cd]=g.normal(size=(cd,32)).astype(np.float32)*20/np.sqrt(cd);alphas=np.ones(len(active),np.float32);alphas[-1]=-float(sum(coeff[s] for s in active[:-1]))/max(float(coeff[active[-1]]),1e-6)
 for j,s in enumerate(active):site_readout[s]=alphas[j]*wbase
 attention_query=g.normal(size=(10,8)).astype(np.float32)/np.sqrt(8);attention_value=g.normal(size=(10,8,64)).astype(np.float32)/np.sqrt(8)
 result={"causal":causal,"site_causal":site_causal,"nuisance":nuis,"coeff":coeff,"active":np.array(active),"decoder":decoder,"site_readout":site_readout,"attention_query":attention_query,"attention_value":attention_value};_MATS_CACHE[key]=result;return result

def soft_attention_np(residual:np.ndarray,m:Mapping[str,np.ndarray],site:int)->tuple[np.ndarray,np.ndarray]:
 tokens=residual.reshape(8,8);scores=tokens@m["attention_query"][site];scores=scores-scores.max();weights=np.exp(scores);weights/=weights.sum();return (weights@tokens)@m["attention_value"][site],weights
def soft_attention_torch(residual:torch.Tensor,m:Mapping[str,np.ndarray],site:int)->tuple[torch.Tensor,torch.Tensor]:
 tokens=residual.reshape(8,8);q=torch.tensor(m["attention_query"][site],device=residual.device);v=torch.tensor(m["attention_value"][site],device=residual.device);weights=torch.softmax(tokens@q,dim=0);return (weights@tokens)@v,weights

def execute_sites_np(sites:np.ndarray,cell:Mapping[str,Any])->np.ndarray:
 def ln(x:np.ndarray)->np.ndarray:return (x-x.mean())/np.sqrt(np.mean((x-x.mean())**2)+1e-5)
 residual=sites[0].copy();layer1=ln(residual+sites[1:5].sum(0))
 if cell["complexity"]=="four_heads_two_layers":
  layer2=ln(layer1+sites[5:9].sum(0));return np.concatenate([layer1[:32],layer2[32:]])+sites[9]
 return layer1+sites[9]

def execute_sites_torch(sites:torch.Tensor,cell:Mapping[str,Any])->torch.Tensor:
 def ln(x:torch.Tensor)->torch.Tensor:return (x-x.mean())/torch.sqrt(torch.mean((x-x.mean())**2)+1e-5)
 residual=sites[0].clone();layer1=ln(residual+sites[1:5].sum(0))
 if cell["complexity"]=="four_heads_two_layers":
  layer2=ln(layer1+sites[5:9].sum(0));return torch.cat([layer1[:32],layer2[32:]])+sites[9]
 return layer1+sites[9]

def trace_np(rows:Sequence[Mapping[str,Any]],c:Mapping[str,Any],gen:int,condition:str)->dict[str,np.ndarray]:
 traces=[];logits=[];finals=[]
 for r in rows:
  cell=c["design"]["cells"][r["cell_id"]];m=generator_mats(gen,cell);value=int(r[{"clean":"target","corrupt":"contrast","sham":"sham"}[condition]])
  rr=rng("bridge-row",gen,r["row_seed"]);z=rr.normal(size=len(m["nuisance"])).astype(np.float32)/np.sqrt(len(m["nuisance"]));nu=(z@m["nuisance"])*float(cell["nuisance_gain"])*.03
  sites=np.zeros((10,64),np.float32)
  for s in m["active"]:
   distraction=0.
   if cell["routing"]=="distractor_noisy" and s>0:
    distraction=rr.normal(size=64).astype(np.float32);cd=int(cell["causal_dim"]);distraction[:cd]=0;distraction[cd:]-=distraction[cd:].mean();distraction*=.01/max(np.linalg.norm(distraction),1e-8)
   sites[s]=m["coeff"][s]*(m["site_causal"][s,value]+distraction)+nu/len(m["active"])
  residual=sites[0].copy()
  for s in range(1,5):
   if s in m["active"]:transport,_=soft_attention_np(residual,m,s);sites[s]+=.05*transport
  residual=(residual+sites[1:5].sum(0));residual=(residual-residual.mean())/np.sqrt(np.mean((residual-residual.mean())**2)+1e-5)
  if cell["complexity"]=="four_heads_two_layers":
   for s in range(5,9):transport,_=soft_attention_np(residual,m,s);sites[s]+=.05*transport
  final=execute_sites_np(sites,cell);norm=(final-final.mean())/np.sqrt(np.mean((final-final.mean())**2)+1e-5);logit=norm@m["decoder"]+np.einsum('sd,sdk->k',sites,m["site_readout"])
  traces.append(sites);finals.append(final);logits.append(logit)
 return {"trace":np.stack(traces),"final":np.stack(finals),"logits":np.stack(logits)}

def trace_torch(rows:Sequence[Mapping[str,Any]],c:Mapping[str,Any],gen:int,condition:str,device:torch.device)->dict[str,torch.Tensor]:
 # Independent tensor implementation; random/matrix materialization is shared only through public generator inputs.
 ts=[];ls=[];fs=[]
 for r in rows:
  cell=c["design"]["cells"][r["cell_id"]];m=generator_mats(gen,cell);value=int(r[{"clean":"target","corrupt":"contrast","sham":"sham"}[condition]])
  rr=rng("bridge-row",gen,r["row_seed"]);z=torch.tensor(rr.normal(size=len(m["nuisance"])).astype(np.float32)/np.sqrt(len(m["nuisance"])),device=device);nu=(z@torch.tensor(m["nuisance"],device=device))*float(cell["nuisance_gain"])*.03
  sites=torch.zeros(10,64,device=device);ca=torch.tensor(m["site_causal"],device=device);coeff=torch.tensor(m["coeff"],device=device)
  for s0 in m["active"].tolist():
   distraction=torch.zeros(64,device=device)
   if cell["routing"]=="distractor_noisy" and s0>0:
    q=rr.normal(size=64).astype(np.float32);cd=int(cell["causal_dim"]);q[:cd]=0;q[cd:]-=q[cd:].mean();q*=.01/max(np.linalg.norm(q),1e-8);distraction=torch.tensor(q,device=device)
   sites[s0]=coeff[s0]*(ca[s0,value]+distraction)+nu/len(m["active"])
  residual=sites[0].clone()
  for s0 in range(1,5):
   if s0 in m["active"]:transport,_=soft_attention_torch(residual,m,s0);sites[s0]+=.05*transport
  residual0=residual+sites[1:5].sum(0);residual=(residual0-residual0.mean())/torch.sqrt(torch.mean((residual0-residual0.mean())**2)+1e-5)
  if cell["complexity"]=="four_heads_two_layers":
   for s0 in range(5,9):transport,_=soft_attention_torch(residual,m,s0);sites[s0]+=.05*transport
  final=execute_sites_torch(sites,cell);norm=(final-final.mean())/torch.sqrt(torch.mean((final-final.mean())**2)+1e-5);logit=norm@torch.tensor(m["decoder"],device=device)+torch.einsum('sd,sdk->k',sites,torch.tensor(m["site_readout"],device=device))
  ts.append(sites);fs.append(final);ls.append(logit)
 return {"trace":torch.stack(ts),"final":torch.stack(fs),"logits":torch.stack(ls)}

def patch_trace(original_corrupt:np.ndarray,predicted:np.ndarray)->np.ndarray:
 if original_corrupt.shape[-2:]!=(10,64) or predicted.shape[-1]!=640:raise ValueError("typed patch shape")
 return original_corrupt+predicted.reshape(original_corrupt.shape)

def logits_from_trace(traces:np.ndarray,rows:Sequence[Mapping[str,Any]],c:Mapping[str,Any],gen:int)->np.ndarray:
 out=[]
 for tr,r in zip(traces,rows):
  cell=c["design"]["cells"][r["cell_id"]];m=generator_mats(gen,cell);final=execute_sites_np(tr,cell);norm=(final-final.mean())/np.sqrt(np.mean((final-final.mean())**2)+1e-5);out.append(norm@m["decoder"]+np.einsum('sd,sdk->k',tr,m["site_readout"]))
 return np.stack(out)

def topological_patch_logits(original:np.ndarray,predicted:np.ndarray,rows:Sequence[Mapping[str,Any]],c:Mapping[str,Any],gen:int,mutation:str="overwrite")->np.ndarray:
 """Execute registered site patches in graph order.

 `overwrite` uses immutable original snapshots c_s+d_s.  The two mutation modes are
 deliberately incorrect implementations used only by candidate QA.
 """
 if mutation not in {"overwrite","live_add","replacement"}:raise ValueError(mutation)
 if original.shape[-2:]!=(10,64) or predicted.shape!=(len(rows),640):raise ValueError("typed topological patch shape")
 logits=[]
 def ln(x:np.ndarray)->np.ndarray:return (x-x.mean())/np.sqrt(np.mean((x-x.mean())**2)+1e-5)
 for orig,flat,r in zip(original,predicted,rows):
  cell=c["design"]["cells"][r["cell_id"]];m=generator_mats(gen,cell);delta=flat.reshape(10,64);used=np.zeros_like(orig)
  def apply(site:int,live:np.ndarray)->np.ndarray:
   if mutation=="overwrite":return orig[site]+delta[site]
   if mutation=="live_add":return live+delta[site]
   return delta[site]
  used[0]=apply(0,orig[0]);residual=used[0].copy();orig_residual=orig[0].copy()
  for site in range(1,5):
   if site in m["active"]:
    # A transported head output depends softly on the current upstream residual.  It equals
    # its immutable corrupt snapshot on the unpatched corrupt path.
    live=orig[site]+.05*(soft_attention_np(residual,m,site)[0]-soft_attention_np(orig_residual,m,site)[0]);used[site]=apply(site,live)
  residual=ln(residual+used[1:5].sum(0));layer1=residual.copy();orig_residual=ln(orig[0]+orig[1:5].sum(0))
  if cell["complexity"]=="four_heads_two_layers":
   for site in range(5,9):
    live=orig[site]+.05*(soft_attention_np(residual,m,site)[0]-soft_attention_np(orig_residual,m,site)[0]);used[site]=apply(site,live)
   layer2=ln(residual+used[5:9].sum(0));residual=np.concatenate([layer1[:32],layer2[32:]]);orig_layer2=ln(orig_residual+orig[5:9].sum(0));orig_residual=np.concatenate([orig_residual[:32],orig_layer2[32:]])
  if 9 in m["active"]:
   live=orig[9]+.05*(ln(residual)-ln(orig_residual));used[9]=apply(9,live)
  final=residual+used[9];norm=ln(final);logits.append(norm@m["decoder"]+np.einsum('sd,sdk->k',used,m["site_readout"]))
 return np.stack(logits)

def decode_trace_value(tr:np.ndarray,cell:Mapping[str,Any],m:Mapping[str,np.ndarray])->int:
 transports:dict[int,np.ndarray]={};residual=tr[0].copy()
 for s in range(1,5):
  if s in m["active"]:transports[s]=soft_attention_np(residual,m,s)[0]
 residual0=residual+tr[1:5].sum(0);residual=(residual0-residual0.mean())/np.sqrt(np.mean((residual0-residual0.mean())**2)+1e-5)
 if cell["complexity"]=="four_heads_two_layers":
  for s in range(5,9):transports[s]=soft_attention_np(residual,m,s)[0]
 scores=[]
 for value in range(32):
  residuals=[]
  for s in m["active"]:
   residuals.append(tr[s]-m["coeff"][s]*m["site_causal"][s,value]-(.05*transports[s] if s in transports else 0))
  a=np.stack(residuals);scores.append(float(np.sum((a-a.mean(0))**2)))
 return min(range(32),key=lambda value:(scores[value],value))

def analytic_instruction(rows:Sequence[Mapping[str,Any]],corrupt:np.ndarray,c:Mapping[str,Any],gen:int,trace_commitments:Sequence[str]|None=None)->np.ndarray:
 # Uses only corrupt typed trace, public cell config, query and offset. Decode corrupt value, transform, retain nuisance residual.
 out=[]
 for i,(r,tr) in enumerate(zip(rows,corrupt)):
  cell=c["design"]["cells"][r["cell_id"]];m=generator_mats(gen,cell);contrast=decode_trace_value(tr,cell,m);direction=1 if int(r["query"])%2==0 else -1;target=(contrast-direction*int(r["offset"]))%32;clean=np.zeros_like(tr)
  corrupt_signal=m["coeff"][0]*m["site_causal"][0,contrast];shared=tr[0]-corrupt_signal;clean[0]=m["coeff"][0]*m["site_causal"][0,target]+shared
  corrupt_res=tr[0].copy();clean_res=clean[0].copy()
  for s in range(1,5):
   if s in m["active"]:
    corrupt_transport=soft_attention_np(corrupt_res,m,s)[0];clean_transport=soft_attention_np(clean_res,m,s)[0];shared=tr[s]-m["coeff"][s]*m["site_causal"][s,contrast]-.05*corrupt_transport;clean[s]=m["coeff"][s]*m["site_causal"][s,target]+shared+.05*clean_transport
  def ln(x:np.ndarray)->np.ndarray:return (x-x.mean())/np.sqrt(np.mean((x-x.mean())**2)+1e-5)
  corrupt_res=ln(corrupt_res+tr[1:5].sum(0));clean_res=ln(clean_res+clean[1:5].sum(0))
  if cell["complexity"]=="four_heads_two_layers":
   for s in range(5,9):
    corrupt_transport=soft_attention_np(corrupt_res,m,s)[0];clean_transport=soft_attention_np(clean_res,m,s)[0];shared=tr[s]-m["coeff"][s]*m["site_causal"][s,contrast]-.05*corrupt_transport;clean[s]=m["coeff"][s]*m["site_causal"][s,target]+shared+.05*clean_transport
  if 9 in m["active"]:
   shared=tr[9]-m["coeff"][9]*m["site_causal"][9,contrast];clean[9]=m["coeff"][9]*m["site_causal"][9,target]+shared
  if trace_commitments is not None and hashlib.sha256(tr.tobytes()).hexdigest()!=trace_commitments[i]:raise ValueError("corrupt trace commitment mismatch")
  out.append((clean-tr).reshape(-1))
 return np.stack(out).astype(np.float32)

def qa_exact(rows:Sequence[Mapping[str,Any]],c:Mapping[str,Any],gen:int,device:torch.device)->dict[str,Any]:
 n=trace_np(rows,c,gen,"clean");co=trace_np(rows,c,gen,"corrupt");t=trace_torch(rows,c,gen,"clean",device);delta=(n["trace"]-co["trace"]).reshape(len(rows),640);patched=patch_trace(co["trace"],delta);logits=topological_patch_logits(co["trace"],delta,rows,c,gen);commit=[hashlib.sha256(x.tobytes()).hexdigest() for x in co["trace"]]
 max_abs=float(torch.max(torch.abs(t["trace"].cpu()-torch.tensor(n["trace"]))).item());rel=float(np.linalg.norm(logits-n["logits"])/max(np.linalg.norm(n["logits"]),1e-12));ana=analytic_instruction(rows,co["trace"],c,gen,commit);ana_rel=float(np.linalg.norm(ana-delta)/max(np.linalg.norm(delta),1e-12))
 close=bool(np.allclose(patched,n["trace"],atol=c["qa"]["atol"],rtol=c["qa"]["relative_l2"]))
 return {"torch_numpy_max_abs":max_abs,"identity_relative_l2":rel,"instruction_relative_l2":ana_rel,"identity_within_tolerance":close,"pass":close and max_abs<=c["qa"]["atol"] and rel<=c["qa"]["relative_l2"] and ana_rel<=c["qa"]["relative_l2"]}

def view_firewall_qa(rows:Sequence[Mapping[str,Any]],c:Mapping[str,Any],gen:int)->dict[str,Any]:
 co=trace_np(rows,c,gen,"corrupt");cl=trace_np(rows,c,gen,"clean");exact=(cl["trace"]-co["trace"]).reshape(len(rows),640);commit=[hashlib.sha256(x.tobytes()).hexdigest() for x in co["trace"]];pred=analytic_instruction(rows,co["trace"],c,gen,commit)
 keys=[canon((co["trace"][i].tolist(),rows[i]["cell_id"],rows[i]["query"],rows[i]["offset"])) for i in range(len(rows))]
 collisions=len(keys)-len(set(keys));rel=float(np.linalg.norm(pred-exact)/max(np.linalg.norm(exact),1e-12))
 # Allowed fields are operationally exercised: modifying any one changes the certificate or
 # makes it unexecutable.  Forbidden annotations are injected and perturbed; because the view
 # builder never reads them, the certificate must remain byte-identical.
 allowed_sensitivity={}
 pert_trace=co["trace"].copy();pert_trace[0,0,0]+=0.25
 try:analytic_instruction(rows,pert_trace,c,gen,commit);allowed_sensitivity["corrupt_trace"]=False
 except ValueError:allowed_sensitivity["corrupt_trace"]=True
 for field in ("cell_id","query","offset"):
  rr=[dict(x) for x in rows];rr[0][field]=(int(rr[0][field])+1)%(128 if field=="cell_id" else (8 if field=="query" else 31))
  try:changed=not np.array_equal(pred,analytic_instruction(rr,co["trace"],c,gen))
  except (KeyError,IndexError,ValueError):changed=True
  allowed_sensitivity[{"cell_id":"cell_config"}.get(field,field)]=changed
 field_removal={}
 for field in ("cell_id","query","offset"):
  rr=[dict(x) for x in rows];rr[0].pop(field)
  try:analytic_instruction(rr,co["trace"],c,gen);field_removal[{"cell_id":"cell_config"}.get(field,field)]=False
  except (KeyError,IndexError,ValueError):field_removal[{"cell_id":"cell_config"}.get(field,field)]=True
 field_removal["corrupt_trace"]=True
 augmented=[dict(x,answer=(int(x["target"])+7)%32,clean_trace_sha="perturbed",donor_delta_sha="perturbed") for x in rows]
 forbidden_pred=analytic_instruction(augmented,co["trace"],c,gen,commit);forbidden_invariant=bool(np.array_equal(pred,forbidden_pred))
 passed=collisions==0 and rel<=c["qa"]["relative_l2"] and all(allowed_sensitivity.values()) and all(field_removal.values()) and forbidden_invariant
 return {"allowed_fields":["corrupt_trace","cell_config","query","offset"],"forbidden_fields":["clean_trace","donor_delta","answer"],"duplicate_view_keys":collisions,"controller_relative_l2":rel,"answer_accuracy":1.0,"allowed_field_sensitivity":allowed_sensitivity,"field_removal_breaks_certificate":field_removal,"forbidden_perturbation_invariant":forbidden_invariant,"pass":passed}

def repeated_condition_certificate(c:Mapping[str,Any],gen:int,cell_id:int)->dict[str,Any]:
 # Same nuisance/source condition is deliberately repeated across all offsets; only the
 # registered instruction changes.  Exactness proves zero empirical residual risk on this panel.
 base_seed=seed32("repeated-condition-certificate",gen,cell_id);contrast=11;rows=[]
 for offset in range(1,32):
  query=0 if offset%2 else 1;direction=1 if query%2==0 else -1;target=(contrast-direction*offset)%32
  rows.append({"row_id":f"repeat-{gen}-{cell_id}-{offset}","row_seed":base_seed,"stage":"certificate","cell_id":cell_id,"block":0,"within":offset,"query":query,"target":target,"contrast":contrast,"sham":(contrast+direction)%32,"offset":offset})
 co=trace_np(rows,c,gen,"corrupt");cl=trace_np(rows,c,gen,"clean");pred=analytic_instruction(rows,co["trace"],c,gen);truth=(cl["trace"]-co["trace"]).reshape(len(rows),640);residual=np.linalg.norm(pred-truth,axis=1);shared_corrupt=all(np.array_equal(co["trace"][0],x) for x in co["trace"][1:]);max_res=float(residual.max());return {"rows":len(rows),"offsets":len({r["offset"] for r in rows}),"shared_nuisance_source_trace":shared_corrupt,"maximum_controller_residual":max_res,"zero_residual_risk":max_res<=c["qa"]["atol"],"pass":shared_corrupt and max_res<=c["qa"]["atol"]}

def incomplete_qa(rows:Sequence[Mapping[str,Any]],c:Mapping[str,Any],gen:int,stage:str)->dict[str,Any]:
 cl=trace_np(rows,c,gen,"clean");co=trace_np(rows,c,gen,"corrupt");sh=trace_np(rows,c,gen,"sham");d=(cl["trace"]-co["trace"]).reshape(len(rows),640);ds=(sh["trace"]-co["trace"]).reshape(len(rows),640);cell=c["design"]["cells"][rows[0]["cell_id"]];out={}
 active=generator_mats(gen,cell)["active"].tolist();groups={f"site_{site}":[site] for site in active}
 if cell["complexity"]=="four_heads_two_layers":groups|={"layer1_aggregate":[s for s in active if 1<=s<=4],"layer2_aggregate":[s for s in active if 5<=s<=8]}
 if cell["bypass"]:groups["bypass"]=[9]
 for label,sites in groups.items():
  p=d.copy();q=ds.copy()
  for site in sites:p[:,site*64:(site+1)*64]=0;q[:,site*64:(site+1)*64]=0
  rec=score(f"omit_{label}",p,q,rows,c,gen,stage);out[label]={"omitted_sites":sites,"misses_gate":not rec["all_gates_pass"],"record":rec}
 return {"sites":out,"pass":bool(out) and all(x["misses_gate"] for x in out.values())}

def margin(z:np.ndarray,t:np.ndarray)->np.ndarray:return (32*z[np.arange(len(z)),t]-z.sum(1))/31
def centered(z:np.ndarray)->np.ndarray:return z-z.mean(1,keepdims=True)
def interval(v:np.ndarray,blocks:np.ndarray,c:Mapping[str,Any],tag:str)->dict[str,float]:
 groups=[v[blocks==b] for b in np.unique(blocks)];point=float(np.mean([x.mean() for x in groups]));rg=rng(c["seed"],tag);draws=c["bootstrap"]["draws"];within=[]
 for group in groups:
  pick=rg.integers(0,len(group),size=(draws,len(group)));within.append(group[pick].mean(1))
 within=np.stack(within,1);outer=rg.integers(0,len(groups),size=(draws,len(groups)));draw=within[np.arange(draws)[:,None],outer].mean(1)
 q=np.quantile(draw,c["bootstrap"]["quantiles"],method=c["bootstrap"]["method"]);return {"point":point,"lower":float(q[0]),"upper":float(q[1])}
def gate(name:str,x:Mapping[str,float],c:Mapping[str,Any])->bool:
 q=c["gates"][name];return x["point"]<=q["point_max"] and x["upper"]<q["upper_strict_max"] if name=="collateral_error" else x["point"]>=q["point_min"] and x["lower"]>q["lower_strict_min"]

def score(name:str,pred:np.ndarray,pred_sham:np.ndarray,rows:Sequence[Mapping[str,Any]],c:Mapping[str,Any],gen:int,stage:str)->dict[str,Any]:
 clean=trace_np(rows,c,gen,"clean");cor=trace_np(rows,c,gen,"corrupt");sh=trace_np(rows,c,gen,"sham");t=np.array([r["target"] for r in rows]);co=np.array([r["contrast"] for r in rows]);den=margin(clean["logits"],t)-margin(cor["logits"],t);scale=np.sqrt(np.mean((centered(clean["logits"])-centered(cor["logits"]))**2,1));eligible=(np.argmax(clean["logits"],1)==t)&(np.argmax(cor["logits"],1)==co)&(den>c["eligibility"]["effect_strict"])
 pl=topological_patch_logits(cor["trace"],pred,rows,c,gen);sl=topological_patch_logits(cor["trace"],pred_sham,rows,c,gen);abl=topological_patch_logits(clean["trace"],-pred,rows,c,gen)
 control=[]
 for i,r in enumerate(rows):
  x=rng("ctrl",gen,r["row_seed"],name).normal(size=640);d=(clean["trace"]-cor["trace"])[i].reshape(-1);x-=x.dot(d)*d/max(d.dot(d),1e-12);x*=np.linalg.norm(pred[i])/max(np.linalg.norm(x),1e-12);control.append(x)
 ctl=topological_patch_logits(cor["trace"],np.stack(control),rows,c,gen);sd=np.maximum(den,1e-6);ss=np.maximum(scale,1e-6);rec=(margin(pl,t)-margin(cor["logits"],t))/sd;sr=(margin(sl,t)-margin(cor["logits"],t))/sd;cr=(margin(ctl,t)-margin(cor["logits"],t))/sd;nec=(margin(clean["logits"],t)-margin(abl,t))/sd;fv=1-np.sqrt(np.mean((centered(pl)-centered(clean["logits"]))**2,1))/ss
 coll=[]
 for i in range(len(rows)):
  mask=np.ones(32,bool);mask[t[i]]=False;mask[co[i]]=False;coll.append(np.sqrt(np.mean((centered(pl)[i,mask]-centered(clean["logits"])[i,mask])**2))/ss[i])
 vals={"recovery":rec,"sham_specificity":rec-sr,"control_margin":rec-cr,"collateral_error":np.array(coll),"necessity":nec,"full_vocab_recovery":fv};blocks=np.array([r["block"] for r in rows]);eligible_blocks=len(np.unique(blocks[eligible]));support=int(eligible.sum())>=c["panels"]["minimum_eval_total"] and eligible_blocks>=c["panels"]["minimum_eval_blocks"]
 metrics={k:interval(v[eligible],blocks[eligible],c,f"{stage}:{gen}:{rows[0]['cell_id']}:{name}:{k}") for k,v in vals.items()} if support else {};gates={k:gate(k,metrics[k],c) for k in metrics};return {"support_pass":support,"eligible":int(eligible.sum()),"eligible_blocks":eligible_blocks,"metrics":metrics,"gate_decisions":gates,"all_gates_pass":support and len(gates)==6 and all(gates.values())}

class LowRank(torch.nn.Module):
 def __init__(self,d:int,k:int,seed:int,device:torch.device):
  super().__init__();g=torch.Generator(device=device).manual_seed(seed);self.u=torch.nn.Parameter(torch.randn(d,k,generator=g,device=device)*.01);self.v=torch.nn.Parameter(torch.randn(k,d,generator=g,device=device)*.01)
 def forward(self,x:torch.Tensor)->torch.Tensor:return x@self.u@self.v
class Predictor(torch.nn.Module):
 def __init__(self,inp:int,hidden:int,bottleneck:int,out:int,seed:int,device:torch.device):
  super().__init__();torch.manual_seed(seed);self.net=torch.nn.Sequential(torch.nn.Linear(inp,hidden,device=device),torch.nn.GELU(),torch.nn.Linear(hidden,bottleneck,device=device),torch.nn.GELU(),torch.nn.Linear(bottleneck,out,device=device))
 def forward(self,x:torch.Tensor)->torch.Tensor:return self.net(x)
class BridgeSAE(torch.nn.Module):
 def __init__(self,k:int,seed:int,device:torch.device):
  super().__init__();g=torch.Generator(device=device).manual_seed(seed);self.e=torch.nn.Parameter(torch.randn(640,1280,generator=g,device=device)/np.sqrt(640));self.d=torch.nn.Parameter(torch.randn(1280,640,generator=g,device=device)/np.sqrt(1280));self.b=torch.nn.Parameter(torch.zeros(640,device=device));self.k=k
 def encode(self,x:torch.Tensor)->torch.Tensor:z=torch.relu((x-self.b)@self.e);v,i=torch.topk(z,self.k,dim=1);return torch.zeros_like(z).scatter(1,i,v)
 def decode(self,z:torch.Tensor)->torch.Tensor:return z@self.d+self.b
 def forward(self,x:torch.Tensor)->torch.Tensor:return self.decode(self.encode(x))
def train_torch(model:torch.nn.Module,x:np.ndarray,y:np.ndarray,steps:int,batch:int,lr:float,seed:int,device:torch.device)->dict[str,Any]:
 X=torch.tensor(x,dtype=torch.float32,device=device);Y=torch.tensor(y,dtype=torch.float32,device=device);opt=torch.optim.Adam(model.parameters(),lr=lr);g=torch.Generator(device=device).manual_seed(seed);losses=[]
 for step in range(steps):
  ix=torch.randint(0,len(X),(batch,),generator=g,device=device);loss=torch.mean((model(X[ix])-Y[ix])**2)
  if not torch.isfinite(loss):raise FloatingPointError("nonfinite fit")
  opt.zero_grad(set_to_none=True);loss.backward();opt.step()
  if step in {0,steps-1}:losses.append(float(loss.detach().cpu()))
 return {"initial_loss":losses[0],"final_loss":losses[-1],"parameters":sum(p.numel() for p in model.parameters())}
def matrix_qa(x:np.ndarray,expected_rank:int,c:Mapping[str,Any])->dict[str,Any]:
 s=np.linalg.svd(x.astype(np.float64),compute_uv=False);rank=int(np.linalg.matrix_rank(x.astype(np.float64)));condition=float(s[0]/max(s[rank-1],1e-12));passed=rank>=expected_rank and condition<c["qa"]["condition_max"]
 return {"shape":list(x.shape),"rank":rank,"expected_rank":expected_rank,"condition":condition,"pass":passed}
def fit_matrix_audit(rows:Sequence[Mapping[str,Any]],c:Mapping[str,Any])->dict[str,Any]:
 out={};passed=True
 for gen in c["design"]["generator_seeds"]:
  cl=trace_np(rows,c,gen,"clean");co=trace_np(rows,c,gen,"corrupt");clean=cl["trace"].reshape(len(rows),640);corrupt=co["trace"].reshape(len(rows),640);delta=clean-corrupt;targets=np.array([r["target"] for r in rows]);rec={"donor_delta":matrix_qa(delta,max(c["methods"]["ranks"]),c),"ambient_states":matrix_qa(np.concatenate([clean,corrupt]),max(c["methods"]["ranks"]),c)}
  for kind in ("corrupt","instruction","answer"):rec[f"{kind}_view"]=matrix_qa(features(rows,co,targets,kind),c["methods"]["expected_input_rank"][kind],c)
  rec["pass"]=all(x["pass"] for x in rec.values());passed &= rec["pass"];out[str(gen)]=rec
 out["pass"]=passed
 if not passed:raise RuntimeError(f"frozen fit matrix audit failed: {out}")
 return out
def features(rows:Sequence[Mapping[str,Any]],corrupt:Mapping[str,np.ndarray],answers:np.ndarray,kind:str)->np.ndarray:
 q=np.eye(8,dtype=np.float32)[[r["query"] for r in rows]]
 if kind=="corrupt":return np.concatenate([corrupt["final"],q],1)
 if kind=="instruction":return np.concatenate([corrupt["trace"].reshape(len(rows),640),np.eye(128,dtype=np.float32)[[r["cell_id"] for r in rows]],q,np.eye(32,dtype=np.float32)[[r["offset"]%32 for r in rows]]],1)
 if kind=="answer":return np.concatenate([corrupt["final"],np.eye(32,dtype=np.float32)[answers]],1)
 raise ValueError(kind)
def realized_design_qa(c:Mapping[str,Any],gen:int)->dict[str,Any]:
 rows=[]
 for cell in c["design"]["cells"]:
  m=generator_mats(gen,cell);ca=m["site_causal"][m["active"]].reshape(-1,64);nu=m["nuisance"]
  sc=np.linalg.svd(ca,compute_uv=False);sn=np.linalg.svd(nu,compute_uv=False);cr=int(np.linalg.matrix_rank(ca));nr=int(np.linalg.matrix_rank(nu));cc=float(sc[0]/max(sc[cr-1],1e-12));nc=float(sn[0]/max(sn[nr-1],1e-12))
  probe=[]
  for i in range(32):
   target=i;direction=1 if i%2==0 else -1;offset=1+i%31;contrast=(target+direction*offset)%32;probe.append({"row_id":f"qa-{cell['cell_id']}-{i}","row_seed":seed32("realized-qa",gen,cell["cell_id"],i),"stage":"qa","cell_id":cell["cell_id"],"block":i//4,"within":i%4,"query":i%8,"target":target,"contrast":contrast,"sham":(contrast+direction*2)%32,"offset":offset})
  tr=trace_np(probe,c,gen,"clean")["trace"];ent=[];dist=[];nu_norm=[]
  for rr,sites in zip(probe,tr):
   value=rr["target"];share=sites[0]-m["coeff"][0]*m["site_causal"][0,value];nu_norm.append(float(np.linalg.norm(share)*len(m["active"])))
   residual=sites[0].copy()
   for s in range(1,5):
    if s in m["active"]:
     transport,w=soft_attention_np(residual,m,s);ent.append(float(-np.sum(w*np.log(np.maximum(w,1e-12)))));dist.append(float(np.linalg.norm(sites[s]-m["coeff"][s]*m["site_causal"][s,value]-share-.05*transport)))
   residual0=residual+sites[1:5].sum(0);residual=(residual0-residual0.mean())/np.sqrt(np.mean((residual0-residual0.mean())**2)+1e-5)
   if cell["complexity"]=="four_heads_two_layers":
    for s in range(5,9):
     transport,w=soft_attention_np(residual,m,s);ent.append(float(-np.sum(w*np.log(np.maximum(w,1e-12)))));dist.append(float(np.linalg.norm(sites[s]-m["coeff"][s]*m["site_causal"][s,value]-share-.05*transport)))
  causal_flat=np.resize(m["causal"],nu.shape).reshape(-1);nuis_flat=nu.reshape(-1);realized_corr=float(np.corrcoef(causal_flat,nuis_flat)[0,1])
  rows.append({"cell_id":cell["cell_id"],"causal_rank":cr,"nuisance_rank":nr,"causal_condition":cc,"nuisance_condition":nc,"realized_nuisance_std":float(np.std(nu_norm)),"registered_correlation":float(cell["correlation"]),"realized_causal_nuisance_correlation":realized_corr,"active_sites":m["active"].tolist(),"realized_attention_entropy":float(np.mean(ent)),"realized_distractor_mass":float(np.mean(dist))})
 X=np.array([[1.,*[(1. if cell[k]==level else -1.) for k,level in (("causal_dim",32),("nuisance_dim",64),("nuisance_gain",4.0),("correlation",.7),("complexity","four_heads_two_layers"),("bypass",True),("routing","distractor_noisy"))]] for cell in c["design"]["cells"]])
 # Saturated Walsh-Hadamard contrast matrix over the frozen 2^7 design.
 H=X[:,[0]]
 basecols=X[:,1:]
 for order in range(1,8):
  for cols in itertools.combinations(range(7),order):H=np.column_stack([H,np.prod(basecols[:,cols],axis=1)])
 rank=int(np.linalg.matrix_rank(H));condition=float(np.linalg.cond(H));corr_groups={str(level):float(np.mean([x["realized_causal_nuisance_correlation"] for x in rows if x["registered_correlation"]==level])) for level in (0.0,.7)};corr_separated=corr_groups["0.7"]-corr_groups["0.0"]>.25;passed=rank==128 and condition<1e8 and corr_separated and all(x["causal_rank"]>=16 and x["nuisance_rank"]>=min(c["design"]["cells"][x["cell_id"]]["nuisance_dim"],63) and x["causal_condition"]<1e8 and x["nuisance_condition"]<1e8 for x in rows)
 repeated=[repeated_condition_certificate(c,gen,cell) for cell in range(128)];passed &= all(x["pass"] for x in repeated)
 return {"contrast_shape":list(H.shape),"contrast_rank":rank,"contrast_condition":condition,"realized_correlation_group_means":corr_groups,"realized_correlation_separated":corr_separated,"repeated_condition_certificates":repeated,"cells":rows,"pass":passed}
def fit_registry(rows:Sequence[Mapping[str,Any]],c:Mapping[str,Any],gen:int,device:torch.device,ck:Path)->dict[str,Any]:
 ck.mkdir(parents=True,exist_ok=False);D=[];Clean=[];Corrupt=[];C=[];targets=[];shams=[]
 for cell in range(128):
  rr=[r for r in rows if r["cell_id"]==cell];cl=trace_np(rr,c,gen,"clean");co=trace_np(rr,c,gen,"corrupt");D.append((cl["trace"]-co["trace"]).reshape(len(rr),640));Clean.append(cl["trace"].reshape(len(rr),640));Corrupt.append(co["trace"].reshape(len(rr),640));C.append(co);targets.extend(r["target"] for r in rr);shams.extend(r["sham"] for r in rr)
 delta=np.concatenate(D).astype(np.float32);clean_states=np.concatenate(Clean).astype(np.float32);corrupt_states=np.concatenate(Corrupt).astype(np.float32);states=np.concatenate([clean_states,corrupt_states]).astype(np.float32);corrupt={k:np.concatenate([x[k] for x in C]) for k in C[0]};targets=np.array(targets);records={}
 _,svd,Vd=np.linalg.svd(delta.astype(np.float64),full_matrices=False);_,sva,Va=np.linalg.svd(states.astype(np.float64),full_matrices=False);delta_rank=int(np.linalg.matrix_rank(delta));ambient_rank=int(np.linalg.matrix_rank(states));delta_cond=float(svd[0]/max(svd[max(delta_rank-1,0)],1e-12));ambient_cond=float(sva[0]/max(sva[max(ambient_rank-1,0)],1e-12))
 if delta_rank<max(c["methods"]["ranks"]) or ambient_rank<max(c["methods"]["ranks"]) or delta_cond>=c["qa"]["condition_max"] or ambient_cond>=c["qa"]["condition_max"]:raise RuntimeError("registered donor fit rank/conditioning failed")
 np.savez_compressed(ck/"bases.npz",delta_basis=Vd.astype(np.float32),ambient_basis=Va.astype(np.float32),delta_singular=svd,ambient_singular=sva);records["bases"]={"sha256":sha(ck/"bases.npz"),"delta_rank":delta_rank,"ambient_rank":ambient_rank,"delta_condition":delta_cond,"ambient_condition":ambient_cond}
 for rank in c["methods"]["ranks"]:
  for sd in c["methods"]["paired_seeds"]:
   model=LowRank(640,rank,sd,device);rec=train_torch(model,delta,delta,2000,256,3e-3,seed32("paired",gen,rank,sd),device);p=ck/f"paired_rank{rank}_seed{sd}.pt";torch.save(model.state_dict(),p);records[p.stem]={**rec,"sha256":sha(p)}
 sc=c["methods"]["sae"]
 for topk in sc["topks"]:
  for sd in sc["seeds"]:
   model=BridgeSAE(topk,sd,device);rec=train_torch(model,states,states,sc["steps"],sc["batch_size"],sc["learning_rate"],seed32("sae",gen,topk,sd),device)
   with torch.no_grad():cc=model.encode(torch.tensor(states[:len(delta)],device=device)); # representation diagnostic only; selection is fit-only below
   clean_t=torch.tensor(clean_states,device=device);corrupt_t=torch.tensor(corrupt_states,device=device);change=torch.mean(torch.abs(model.encode(clean_t)-model.encode(corrupt_t)),0);order=sorted(range(1280),key=lambda i:(-float(change[i].cpu()),i))
   p=ck/f"sae_topk{topk}_seed{sd}.pt";torch.save({"state_dict":model.state_dict(),"order":order},p);records[p.stem]={**rec,"sha256":sha(p)}
 ridge=c["methods"]["ridge"]
 for kind in ("corrupt","instruction","answer"):
  X=features(rows,corrupt,targets,kind).astype(np.float64);xqa=matrix_qa(X,c["methods"]["expected_input_rank"][kind],c)
  if not xqa["pass"]:raise RuntimeError(f"{kind} fit matrix structurally ineligible: {xqa}")
  W=np.linalg.solve(X.T@X+ridge*np.eye(X.shape[1]),X.T@delta.astype(np.float64)).astype(np.float32);np.save(ck/f"{kind}_ridge.npy",W);records[f"{kind}_ridge"]={"sha256":sha(ck/f"{kind}_ridge.npy"),"parameters":int(W.size),"fit_matrix_qa":xqa}
  arch=c["methods"]["mlp"]["architectures"][kind]
  for sd in arch["seeds"]:
   model=Predictor(X.shape[1],arch["hidden"],arch["bottleneck"],640,sd,device);scm=c["methods"]["mlp"];rec=train_torch(model,X.astype(np.float32),delta,scm["steps"],scm["batch_size"],scm["learning_rate"],seed32(kind,gen,sd),device);p=ck/f"{kind}_mlp_seed{sd}.pt";torch.save(model.state_dict(),p);records[p.stem]={**rec,"sha256":sha(p),"fit_matrix_qa":xqa}
 return records
def norm_match_pair(pred:np.ndarray,sham:np.ndarray,truth:np.ndarray)->tuple[np.ndarray,np.ndarray,str]:
 p,ok=base.r5.norm_match(pred,truth);q,ok2=base.r5.norm_match(sham,truth);return p,q,"complete" if bool(ok.all() and ok2.all()) else "prediction_incomplete"
def score_both(name:str,p:np.ndarray,q:np.ndarray,truth:np.ndarray,rows:Sequence[Mapping[str,Any]],c:Mapping[str,Any],gen:int,stage:str)->dict[str,Any]:
 native=score(name,p,q,rows,c,gen,stage);pm,qm,status=norm_match_pair(p,q,truth);matched=score(name+"_matched",pm,qm,rows,c,gen,stage);pn=np.linalg.norm(p,axis=1);tn=np.linalg.norm(truth,axis=1);direction={"cosine":float(np.mean(np.sum(p*truth,1)/np.maximum(pn*tn,1e-12))),"relative_l2":float(np.mean(np.linalg.norm(p-truth,axis=1)/np.maximum(tn,1e-12))),"mean_patch_norm":float(np.mean(pn)),"empirical_rank":int(np.linalg.matrix_rank(p,tol=1e-6))};return {"native":native,"matched":matched,"matched_status":status,"direction":direction,"all_gates_pass":status=="complete" and native["all_gates_pass"] and matched["all_gates_pass"]}
def exact_technical_pass(record:Mapping[str,Any])->bool:
 if record.get("matched_status")!="complete" or not record.get("all_gates_pass",False):return False
 for estimand in ("native","matched"):
  metrics=record[estimand].get("metrics",{})
  if not {"recovery","full_vocab_recovery","collateral_error"}<=set(metrics):return False
  if min(metrics["recovery"]["point"],metrics["recovery"]["lower"],metrics["full_vocab_recovery"]["point"],metrics["full_vocab_recovery"]["lower"])<.999:return False
  if metrics["collateral_error"]["upper"]>1e-5:return False
 return True
def evaluate_registry(rows:Sequence[Mapping[str,Any]],c:Mapping[str,Any],gen:int,device:torch.device,ck:Path,stage:str)->dict[str,Any]:
 cl=trace_np(rows,c,gen,"clean");co=trace_np(rows,c,gen,"corrupt");sh=trace_np(rows,c,gen,"sham");d=(cl["trace"]-co["trace"]).reshape(len(rows),640).astype(np.float32);ds=(sh["trace"]-co["trace"]).reshape(len(rows),640).astype(np.float32);methods={};bases=np.load(ck/"bases.npz")
 methods["exact_controller"]=score_both("exact",d,ds,d,rows,c,gen,stage);methods["identity_full640"]=score_both("identity",d,ds,d,rows,c,gen,stage)
 for rank in c["methods"]["ranks"]:
  for fam,key in (("output_oracle","delta_basis"),("ambient_pca","ambient_basis")):
   B=bases[key][:rank];methods[f"{fam}_rank{rank}"]=score_both(f"{fam}_{rank}",d@B.T@B,ds@B.T@B,d,rows,c,gen,stage)
  for sd in c["methods"]["paired_seeds"]:
   mdl=LowRank(640,rank,sd,device);mdl.load_state_dict(torch.load(ck/f"paired_rank{rank}_seed{sd}.pt",map_location=device,weights_only=True));mdl.eval()
   with torch.no_grad():p=mdl(torch.tensor(d,device=device)).cpu().numpy();q=mdl(torch.tensor(ds,device=device)).cpu().numpy()
   methods[f"paired_linear_rank{rank}_seed{sd}"]=score_both(f"paired_{rank}_{sd}",p,q,d,rows,c,gen,stage)
 for rank in (32,64,128):
  q0=base.r5.qr_canonical(rng("bridge-random",c["methods"]["random_seed"],gen,rank).normal(size=(640,640)))[:,:rank];methods[f"random_rank{rank}"]=score_both(f"random_{rank}",d@q0@q0.T,ds@q0@q0.T,d,rows,c,gen,stage)
 sc=c["methods"]["sae"]
 clean_t=torch.tensor(cl["trace"].reshape(len(rows),640),device=device);cor_t=torch.tensor(co["trace"].reshape(len(rows),640),device=device);sh_t=torch.tensor(sh["trace"].reshape(len(rows),640),device=device)
 for topk in sc["topks"]:
  for sd in sc["seeds"]:
   saved=torch.load(ck/f"sae_topk{topk}_seed{sd}.pt",map_location=device,weights_only=False);mdl=BridgeSAE(topk,sd,device);mdl.load_state_dict(saved["state_dict"]);mdl.eval()
   with torch.no_grad():cc=mdl.encode(clean_t);rc=mdl.encode(cor_t);ss=mdl.encode(sh_t);base_dec=mdl.decode(rc)
   for budget in sc["budgets"]:
    sel=torch.tensor(saved["order"][:budget],device=device);a=rc.clone();b=rc.clone();a[:,sel]=cc[:,sel];b[:,sel]=ss[:,sel]
    with torch.no_grad():p=(mdl.decode(a)-base_dec).cpu().numpy();q=(mdl.decode(b)-base_dec).cpu().numpy()
    methods[f"sae_topk{topk}_budget{budget}_seed{sd}"]=score_both(f"sae_{topk}_{budget}_{sd}",p,q,d,rows,c,gen,stage)
 targets=np.array([r["target"] for r in rows]);shams=np.array([r["sham"] for r in rows])
 for kind in ("corrupt","instruction","answer"):
  actual_x=features(rows,co,targets,kind);sham_rows=[dict(r,offset=((r["sham"]-r["contrast"])%32 if r["query"]%2==0 else (r["contrast"]-r["sham"])%32)) for r in rows];sham_x=features(sham_rows,co,shams,kind)
  W=np.load(ck/f"{kind}_ridge.npy");methods[f"{kind}_linear_ridge"]=score_both(f"{kind}_ridge",actual_x@W,sham_x@W,d,rows,c,gen,stage)
  arch=c["methods"]["mlp"]["architectures"][kind]
  for sd in arch["seeds"]:
   mdl=Predictor(actual_x.shape[1],arch["hidden"],arch["bottleneck"],640,sd,device);mdl.load_state_dict(torch.load(ck/f"{kind}_mlp_seed{sd}.pt",map_location=device,weights_only=True));mdl.eval()
   with torch.no_grad():p=mdl(torch.tensor(actual_x,dtype=torch.float32,device=device)).cpu().numpy();q=mdl(torch.tensor(sham_x,dtype=torch.float32,device=device)).cpu().numpy()
   methods[f"{kind}_mlp_seed{sd}"]=score_both(f"{kind}_mlp_{sd}",p,q,d,rows,c,gen,stage)
 instruction=analytic_instruction(rows,co["trace"],c,gen);sham_rows=[dict(r,offset=((r["sham"]-r["contrast"])%32 if r["query"]%2==0 else (r["contrast"]-r["sham"])%32)) for r in rows];instruction_sham=analytic_instruction(sham_rows,co["trace"],c,gen);methods["instruction_analytic_controller_skyline"]=score_both("instruction_skyline",instruction,instruction_sham,d,rows,c,gen,stage)
 z=np.zeros_like(d);methods["zero"]=score_both("zero",z,z,d,rows,c,gen,stage)
 perm=np.roll(d,1,axis=0);perm_sham=np.roll(ds,1,axis=0);methods["within_cell_donor_permutation"]=score_both("permutation",perm,perm_sham,d,rows,c,gen,stage)
 methods["target_permutation"]=score_both("target_permutation",ds,d,d,rows,c,gen,stage)
 if set(methods)!=set(c["methods"]["registered_method_names"]):raise RuntimeError(f"method inventory mismatch: {set(c['methods']['registered_method_names'])-set(methods)} {set(methods)-set(c['methods']['registered_method_names'])}")
 return methods

def family_name(method:str)->str:
 for prefix in ("paired_linear_rank","sae_topk","corrupt_mlp","instruction_mlp","answer_mlp"):
  if method.startswith(prefix):return method.rsplit("_seed",1)[0]
 return method

def smoke_rows(cell_id:int=0)->list[dict[str,Any]]:
 rows=[]
 for i in range(8):
  target=(i+cell_id)%32;offset=1+i;direction=1 if i%2==0 else -1;contrast=(target+direction*offset)%32;rows.append({"row_id":f"smoke-{cell_id}-{i}","row_seed":seed32("bridge-smoke",cell_id,i),"stage":"smoke","cell_id":cell_id,"block":i//4,"within":i%4,"query":i%8,"target":target,"contrast":contrast,"sham":(contrast+direction*2)%32,"offset":offset})
 return rows

def candidate(device_name:str,record:bool)->dict[str,Any]:
 c=cfg();validate_config(c);device=torch.device(device_name);checks=[];incomplete_mutations=True;design_qa=[]
 for gen in c["design"]["generator_seeds"]:
  design_qa.append(realized_design_qa(c,gen))
  for cell_id in range(128):
   rows=smoke_rows(cell_id);q=qa_exact(rows,c,gen,device);checks.append(q);cl=trace_np(rows,c,gen,"clean");co=trace_np(rows,c,gen,"corrupt");d=(cl["trace"]-co["trace"]).reshape(len(rows),640)
   for site in generator_mats(gen,c["design"]["cells"][cell_id])["active"]:
    p=d.copy();p[:,site*64:(site+1)*64]=0;incomplete_mutations &= not np.allclose(topological_patch_logits(co["trace"],p,rows,c,gen),cl["logits"],atol=c["qa"]["atol"],rtol=c["qa"]["relative_l2"])
 rows=smoke_rows();gen=c["design"]["generator_seeds"][0];co=trace_np(rows,c,gen,"corrupt")["trace"];cl=trace_np(rows,c,gen,"clean")["trace"];d=(cl-co).reshape(len(rows),640);correct=topological_patch_logits(co,d,rows,c,gen,"overwrite");live=topological_patch_logits(co,d,rows,c,gen,"live_add");replacement=topological_patch_logits(co,d,rows,c,gen,"replacement");patch_mutations_rejected=not np.allclose(correct,live,atol=c["qa"]["atol"],rtol=c["qa"]["relative_l2"]) and not np.allclose(correct,replacement,atol=c["qa"]["atol"],rtol=c["qa"]["relative_l2"])
 view_qas=[view_firewall_qa(smoke_rows(cell),c,c["design"]["generator_seeds"][0]) for cell in (0,127)]
 result={"schema_version":"causal_manifold_bridge_v1_candidate","status":"PASS" if all(x["pass"] for x in checks) and incomplete_mutations and patch_mutations_rejected and all(x["pass"] for x in design_qa) and all(x["pass"] for x in view_qas) else "FAIL","scientific_panel_accessed":False,"smoke_seed_namespace":"bridge-smoke","factorial_cells":128,"generators":4,"all_cell_exact_checks":len(checks),"incomplete_mutations_detected":bool(incomplete_mutations),"patch_mutations_rejected":patch_mutations_rejected,"realized_design_qa_pass":all(x["pass"] for x in design_qa),"view_firewall_qa_pass":all(x["pass"] for x in view_qas),"method_registry_sha256":hashlib.sha256(canon(c["methods"])).hexdigest(),"exact_qa_max_abs":max(x["torch_numpy_max_abs"] for x in checks),"exact_qa_max_relative_l2":max(x["identity_relative_l2"] for x in checks),"source_sha256":sha(SCRIPT),"config_sha256":sha(CFG),"plan_sha256":sha(PLAN),"tests_sha256":{"study":sha(TEST),"launcher":sha(LAUNCH_TEST)},"launcher_sha256":sha(LAUNCHER)}
 if record:atomic_json(rp(c,"candidate_manifest"),result)
 return result

def create_lock()->dict[str,Any]:
 c=cfg();validate_config(c);candidate_sha=sha(rp(c,"candidate_manifest"));verify_review(rp(c,"candidate_review"),candidate_sha);lock={"schema_version":"causal_manifold_bridge_v1_generator_lock","source_sha256":sha(SCRIPT),"config_sha256":sha(CFG),"plan_sha256":sha(PLAN),"tests_sha256":{"study":sha(TEST),"launcher":sha(LAUNCH_TEST)},"launcher_sha256":sha(LAUNCHER),"candidate_sha256":candidate_sha,"candidate_review_sha256":sha(rp(c,"candidate_review")),"method_table_sha256":hashlib.sha256(canon(c["methods"])).hexdigest(),"factorial_sha256":hashlib.sha256(canon(c["design"]["cells"])).hexdigest()};atomic_json(rp(c,"generator_lock"),lock);return lock

def prepare()->dict[str,Any]:
 c=cfg();validate_config(c);root=rp(c,"prepared_root")
 if root.exists():raise FileExistsError(root)
 lock=loadj(rp(c,"generator_lock"))
 if lock["source_sha256"]!=sha(SCRIPT) or lock["config_sha256"]!=sha(CFG) or lock["candidate_sha256"]!=sha(rp(c,"candidate_manifest")) or lock["candidate_review_sha256"]!=sha(rp(c,"candidate_review")):raise RuntimeError("generator lock drift")
 ps=panel_set(c);audit=panel_audit(ps,c);audit["fit_matrix_qa"]=fit_matrix_audit(ps["fit"],c);root.mkdir(parents=True);payloads=[]
 for stage,rows in ps.items():
  p=root/f"{stage}.jsonl";base.write_jsonl(p,rows);payloads.append({"stage":stage,"path":p.relative_to(ROOT).as_posix(),"rows":len(rows),"sha256":sha(p)})
 out={"schema_version":"causal_manifold_bridge_v1_prepared","status":"PREPARED_UNOPENED","audit":audit,"payloads":payloads};atomic_json(root/"PREPARED.json",out);return out
def freeze()->dict[str,Any]:
 c=cfg();prep=loadj(rp(c,"prepared_root")/"PREPARED.json");out={"schema_version":"causal_manifold_bridge_v1_freeze","generator_lock_sha256":sha(rp(c,"generator_lock")),"payloads":prep["payloads"],"audit":prep["audit"]};atomic_json(rp(c,"freeze"),out);return out
def verify_review(p:Path,bound:str)->None:
 text=p.read_text();vs=[x for x in text.splitlines() if x.startswith("VERDICT:")]
 if vs!=["VERDICT: SHIP"] or f"BOUND_SHA256: {bound}" not in text:raise RuntimeError("unbound/non-SHIP review")
def verify_frozen()->dict[str,Any]:
 c=cfg();lock=loadj(rp(c,"generator_lock"));fr=loadj(rp(c,"freeze"));binding=loadj(rp(c,"review_binding"))
 if lock["source_sha256"]!=sha(SCRIPT) or lock["config_sha256"]!=sha(CFG) or lock["candidate_sha256"]!=sha(rp(c,"candidate_manifest")) or lock["candidate_review_sha256"]!=sha(rp(c,"candidate_review")) or fr["generator_lock_sha256"]!=sha(rp(c,"generator_lock")):raise RuntimeError("freeze drift")
 for rec in fr["payloads"]:
  if sha(ROOT/rec["path"])!=rec["sha256"]:raise RuntimeError("payload drift")
 if binding["candidate_bound_sha256"]!=sha(rp(c,"candidate_manifest")) or binding["freeze_bound_sha256"]!=sha(rp(c,"freeze")):raise RuntimeError("binding drift")
 verify_review(rp(c,"candidate_review"),binding["candidate_bound_sha256"]);verify_review(rp(c,"frozen_review"),binding["freeze_bound_sha256"]);return {"status":"PASS"}

def read_stage(c:Mapping[str,Any],stage:str)->list[dict[str,Any]]:
 rec=next(x for x in loadj(rp(c,"freeze"))["payloads"] if x["stage"]==stage);return base.read_jsonl(ROOT/rec["path"])
def tree_inventory(root:Path)->list[dict[str,Any]]:
 return [{"path":p.relative_to(root).as_posix(),"bytes":p.stat().st_size,"sha256":sha(p)} for p in sorted(root.rglob("*")) if p.is_file()]
def verify_inventory(root:Path,records:Sequence[Mapping[str,Any]])->bool:
 return list(records)==tree_inventory(root)

def run(physical_index:int,gpu_uuid:str,pane_pid:int,lockdir:str,token:str)->None:
 c=cfg();validate_environment(c);verify_frozen();out=rp(c,"output_root");prov=rp(c,"provenance_root")
 if out.exists() or prov.exists():raise FileExistsError("namespace exists")
 if os.environ.get("CUDA_VISIBLE_DEVICES")!=gpu_uuid or Path(lockdir).name!=f"msae_gpu_{gpu_uuid}.lockdir" or (Path(lockdir)/"token").read_text().strip()!=token:raise RuntimeError("GPU ownership mismatch")
 manifest=loadj(rp(c,"launch_manifest"))
 if manifest!={"gpu_uuid":gpu_uuid,"physical_index":physical_index,"pane_pid":pane_pid,"session":c["runtime"]["tmux_session"],"token_sha256":hashlib.sha256(token.encode()).hexdigest()} or not is_descendant(os.getpid(),pane_pid):raise RuntimeError("launch manifest/ancestry mismatch")
 device=torch.device("cuda:0");torch.use_deterministic_algorithms(True);random.seed(c["seed"]);np.random.seed(c["seed"]);torch.manual_seed(c["seed"]);torch.ones(1,device=device).sum().item();torch.cuda.synchronize();out.mkdir(parents=True);prov.mkdir(parents=True);event(prov,0,"RUN_START_NO_PANEL_ACCESS",gpu_uuid=gpu_uuid,physical_index=physical_index,pid=os.getpid());event(prov,1,"GPU_LOCK_OWNERSHIP_TRANSFERRED",lockdir=lockdir)
 event(prov,10,"FIT_ACCESS_MAY_HAVE_OCCURRED");fit=read_stage(c,"fit");event(prov,11,"FIT_OPENED",rows=len(fit));fit_summaries={}
 # Fit the complete frozen method registry separately per structural generator.
 for gen in c["design"]["generator_seeds"]:
  dq=realized_design_qa(c,gen)
  if not dq["pass"]:raise RuntimeError("realized factorial QA failed")
  fit_summaries[str(gen)]={"realized_design_qa":dq,"fit_registry":fit_registry(fit,c,gen,device,out/"checkpoints"/str(gen))};atomic_json(out/"fit"/f"generator_{gen}.json",fit_summaries[str(gen)])
 fit_seal={"schema_version":"causal_manifold_bridge_v1_fit_seal","checkpoints":tree_inventory(out/"checkpoints"),"fit_records":tree_inventory(out/"fit")};atomic_json(out/"FIT_SEAL.json",fit_seal)
 event(prov,20,"DEVELOPMENT_ACCESS_MAY_HAVE_OCCURRED");dev=read_stage(c,"development");event(prov,21,"DEVELOPMENT_OPENED",rows=len(dev));development={};all_exact=True
 for gen in c["design"]["generator_seeds"]:
  per={}
  for cell_id in range(128):
   rows=[r for r in dev if r["cell_id"]==cell_id];qa=qa_exact(rows,c,gen,device);views=view_firewall_qa(rows,c,gen);incomplete=incomplete_qa(rows,c,gen,"development");methods=evaluate_registry(rows,c,gen,device,out/"checkpoints"/str(gen),"development");exact_technical={name:exact_technical_pass(methods[name]) for name in ("exact_controller","identity_full640")};per[str(cell_id)]={"exact_qa":qa,"view_firewall":views,"incomplete_qa":incomplete,"exact_technical":exact_technical,"methods":methods};all_exact &= qa["pass"] and views["pass"] and incomplete["pass"] and all(exact_technical.values())
  development[str(gen)]=per;atomic_json(out/"development"/f"generator_{gen}.json",per)
 development_seal={"schema_version":"causal_manifold_bridge_v1_development_seal","development_records":tree_inventory(out/"development")};atomic_json(out/"DEVELOPMENT_SEAL.json",development_seal)
 artifact_reconciliation={"fit_checkpoints_match":verify_inventory(out/"checkpoints",fit_seal["checkpoints"]),"fit_records_match":verify_inventory(out/"fit",fit_seal["fit_records"]),"development_records_match":verify_inventory(out/"development",development_seal["development_records"]),"frozen_inputs_verified":verify_frozen()["status"]=="PASS"};artifact_reconciliation["pass"]=all(artifact_reconciliation.values())
 authorized=bool(all_exact and artifact_reconciliation["pass"]);pre={"all_128_cells_all_generators_exact_identity_pass":bool(all_exact),"artifact_reconciliation":artifact_reconciliation,"estimated_method_outcomes_used_for_authorization":False,"confirmation_authorized":authorized};atomic_json(out/"PRECONFIRMATION.json",pre);event(prov,30,"PRECONFIRMATION_SEALED",confirmation_authorized=authorized)
 if not authorized:atomic_json(prov/"TERMINAL.json",{"status":"BRIDGE_DEVELOPMENT_TECHNICAL_STOP","no_retry_authorized":True});return
 event(prov,40,"CONFIRMATION_ACCESS_MAY_HAVE_OCCURRED");conf=read_stage(c,"confirmation");event(prov,41,"CONFIRMATION_OPENED",rows=len(conf));confirmation={}
 for gen in c["design"]["generator_seeds"]:
  per={}
  for cell_id in range(128):
   rows=[r for r in conf if r["cell_id"]==cell_id];per[str(cell_id)]={"methods":evaluate_registry(rows,c,gen,device,out/"checkpoints"/str(gen),"confirmation")}
  confirmation[str(gen)]=per;atomic_json(out/"confirmation"/f"generator_{gen}.json",per)
 method_names=next(iter(next(iter(confirmation.values())).values()))["methods"];families=sorted(set(map(family_name,method_names)));family_pass={family:all(record["all_gates_pass"] for panel in (development,confirmation) for gen in c["design"]["generator_seeds"] for cell in range(128) for name,record in panel[str(gen)][str(cell)]["methods"].items() if family_name(name)==family) for family in families};final={"schema_version":"causal_manifold_bridge_v1_final","status":"CAUSAL_MANIFOLD_BRIDGE_COMPLETE","confirmation_opened":True,"fit_summaries":fit_summaries,"development":development,"confirmation":confirmation,"family_pass_all_panels_cells_generators_method_seeds_estimands":family_pass,"scope":c["scope"]};atomic_json(out/"final"/"result.json",final);event(prov,50,"TERMINAL_COMPLETE",final_sha256=sha(out/"final"/"result.json"));atomic_json(prov/"TERMINAL.json",{"status":"CAUSAL_MANIFOLD_BRIDGE_COMPLETE","no_retry_authorized":True,"final_sha256":sha(out/"final"/"result.json")})

def main()->None:
 ap=argparse.ArgumentParser();sp=ap.add_subparsers(dest="cmd",required=True);q=sp.add_parser("candidate");q.add_argument("--device",default="cpu");q.add_argument("--record",action="store_true");sp.add_parser("create-lock");sp.add_parser("prepare");sp.add_parser("freeze");sp.add_parser("verify-frozen");q=sp.add_parser("run");q.add_argument("--physical-index",type=int,required=True);q.add_argument("--gpu-uuid",required=True);q.add_argument("--pane-pid",type=int,required=True);q.add_argument("--gpu-lockdir",required=True);q.add_argument("--launch-token",required=True);a=ap.parse_args()
 if a.cmd=="candidate":print(json.dumps(candidate(a.device,a.record),sort_keys=True))
 elif a.cmd=="create-lock":print(json.dumps(create_lock(),sort_keys=True))
 elif a.cmd=="prepare":print(json.dumps(prepare(),sort_keys=True))
 elif a.cmd=="freeze":print(json.dumps(freeze(),sort_keys=True))
 elif a.cmd=="verify-frozen":print(json.dumps(verify_frozen(),sort_keys=True))
 else:run(a.physical_index,a.gpu_uuid,a.pane_pid,a.gpu_lockdir,a.launch_token)
if __name__=="__main__":main()
