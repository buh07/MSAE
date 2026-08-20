#!/usr/bin/env python3
"""Technical-only bridge-v2 qualification with shared random-control banks."""
from __future__ import annotations

import argparse,copy,hashlib,json,os,random,signal,subprocess,sys,time
from pathlib import Path
from typing import Any,Mapping,Sequence

import numpy as np
import torch

ROOT=Path(os.environ.get("MSAE_ROOT",Path(__file__).resolve().parents[1])).resolve();sys.path.insert(0,str(ROOT/"scripts"))
import causal_manifold_bridge_v1_r2 as r2

CFG=ROOT/"configs/causal_manifold_bridge_v2_technical/run.json";PLAN=ROOT/"PLAN_SAE_GEOMETRY_SELECTION_AND_BRIDGE_V2.md";SCRIPT=Path(__file__).resolve();TEST=ROOT/"tests/test_causal_manifold_bridge_v2_technical.py";LAUNCHER=ROOT/"scripts/launch_sae_selection_bridge_v2_tmux.sh";LAUNCH_TEST=ROOT/"tests/test_launch_sae_selection_bridge_v2_tmux.py"
R2_SCRIPT=ROOT/"scripts/causal_manifold_bridge_v1_r2.py"

def loadj(p:Path)->Any:return json.loads(p.read_text())
def cfg()->dict[str,Any]:return loadj(CFG)
def canon(x:Any)->bytes:return json.dumps(x,sort_keys=True,separators=(",",":"),allow_nan=False).encode()
def sha(p:Path)->str:return hashlib.sha256(p.read_bytes()).hexdigest()
def rp(c:Mapping[str,Any],k:str)->Path:return ROOT/c["runtime"][k]
def digest_seed(parts:Sequence[Any])->int:return int.from_bytes(hashlib.sha256(canon(list(parts))).digest()[:8],"little",signed=False)
def atomic_json(p:Path,x:Any)->None:
 p.parent.mkdir(parents=True,exist_ok=True)
 if p.exists():raise FileExistsError(p)
 fd=os.open(p,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o444)
 with os.fdopen(fd,"w") as f:json.dump(x,f,indent=2,sort_keys=True,allow_nan=False);f.write("\n");f.flush();os.fsync(f.fileno())
def event(root:Path,i:int,state:str,**kw:Any)->None:atomic_json(root/"events"/f"{i:03d}_{state}.json",{"index":i,"state":state,"time_ns":time.time_ns(),**kw})
def validate_preservation(c:Mapping[str,Any])->None:
 p=ROOT/c["preservation"]["path"]
 if sha(p)!=c["preservation"]["sha256"]:raise RuntimeError("R2 preservation drift")
 subprocess.run([sys.executable,str(ROOT/"scripts/preserve_trained_control_r2_outcomes.py"),"--verify"],check=True)
def transitive_runtime_hashes(c:Mapping[str,Any])->dict[str,str]:
 got={k:sha(ROOT/v["path"]) for k,v in c["transitive_runtime"].items()}
 expected={k:v["sha256"] for k,v in c["transitive_runtime"].items()}
 if got!=expected:raise RuntimeError(f"transitive executable drift: {got} != {expected}")
 return got
def validate_environment(c:Mapping[str,Any])->None:
 e=c["environment"];actual={"python":".".join(map(str,sys.version_info[:3])),"torch":torch.__version__.split("+")[0],"cuda":str(torch.version.cuda),"numpy":np.__version__,"pythonhashseed":os.environ.get("PYTHONHASHSEED"),"cublas_workspace_config":os.environ.get("CUBLAS_WORKSPACE_CONFIG")}
 if actual!=e:raise RuntimeError(f"environment drift {actual} != {e}")
def is_descendant(pid:int,ancestor:int)->bool:return r2.is_descendant(pid,ancestor)
def generators(c:Mapping[str,Any])->list[int]:return list(c["design"]["effective_generator_seeds"])
def generator_axes(c:Mapping[str,Any],gen:int)->dict[str,int]:
 i=generators(c).index(gen);structural=c["design"]["structural_seeds"][i];parameter=c["design"]["parameter_seeds"][i];return {"effective_generator_seed":gen,"structural_seed":structural,"parameter_seed":parameter,"graph_seed":r2.seed32("bridge-v2-graph",structural,parameter,gen)}
def graph_seed(c:Mapping[str,Any],gen:int)->int:return generator_axes(c,gen)["graph_seed"]
def validation_authorized(endpoint_passes:Sequence[bool],locked_freshness_matches:bool,estimated_outcomes:Any=None)->bool:
 return bool(locked_freshness_matches and endpoint_passes and all(endpoint_passes))

def panel_rows(stage:str,c:Mapping[str,Any])->list[dict[str,Any]]:
 pc=c["panels"][stage];rows=[]
 for cell in c["design"]["cells"]:
  for block in range(pc["blocks_per_cell"]):
   for within in range(pc["rows_per_block"]):
    ix=(cell["cell_id"]*pc["blocks_per_cell"]+block)*pc["rows_per_block"]+within;rs=r2.seed32("causal-manifold-bridge-v2",stage,pc["seed"],ix);query=(block+within)%8;target=(3*block+within+cell["cell_id"])%32;direction=1 if query%2==0 else -1;offset=1+((5*block+within)%31);contrast=(target+direction*offset)%32;sham=(contrast+direction*(1+((block+2*within)%30)))%32
    while sham in {target,contrast}:sham=(sham+direction)%32
    rows.append({"row_id":f"cm-v2-{stage}-{ix:06d}-{rs:08x}","row_seed":rs,"stage":stage,"cell_id":cell["cell_id"],"block":block,"within":within,"query":query,"target":target,"contrast":contrast,"sham":sham,"offset":offset})
 return rows
def panel_set(c:Mapping[str,Any])->dict[str,list[dict[str,Any]]]:return {s:panel_rows(s,c) for s in ("qualification","validation")}

def composite_key(row:Mapping[str,Any],c:Mapping[str,Any],gen:int)->str:
 traces=[r2.trace_np([row],c,graph_seed(c,gen),x)["trace"][0].tobytes() for x in ("clean","corrupt","sham")]
 h=hashlib.sha256();[h.update(x) for x in traces];h.update(canon([row[k] for k in ("query","offset","target","contrast","sham")]))
 return h.hexdigest()
def freshness_audit(panels:Mapping[str,Sequence[Mapping[str,Any]]],c:Mapping[str,Any])->dict[str,Any]:
 opened=[]
 for path in c["freshness"]["opened_bridge_payloads"]:
  p=ROOT/path
  if p.exists():opened.extend(r2.base.read_jsonl(p))
 fresh=[x for rows in panels.values() for x in rows];opened_ids={x["row_id"] for x in opened};opened_seeds={x["row_seed"] for x in opened}
 if len({x["row_id"] for x in fresh})!=len(fresh) or len({x["row_seed"] for x in fresh})!=len(fresh):raise RuntimeError("new row ID/seed collision")
 if any(x["row_id"] in opened_ids or x["row_seed"] in opened_seeds for x in fresh):raise RuntimeError("opened row ID/seed collision")
 counts={};new_sets={};old_sets={}
 for gen in generators(c):
  old={composite_key(x,c,gen) for x in opened};q={composite_key(x,c,gen) for x in panels["qualification"]};v={composite_key(x,c,gen) for x in panels["validation"]}
  if old&q or old&v or q&v:raise RuntimeError(f"full composite scientific-content collision generator={gen}")
  counts[str(gen)]={"opened":len(old),"qualification":len(q),"validation":len(v)};new_sets[gen]=(q,v);old_sets[gen]=old
 return {"pass":True,"row_id_overlap":0,"row_seed_overlap":0,"composite_overlap":0,"marginal_categorical_recurrence_allowed":True,"per_generator":counts}

def seed_tuple(c:Mapping[str,Any],gen:int,row:Mapping[str,Any],bank_index:int,kind:str,counter:int=0)->list[Any]:
 axes=generator_axes(c,gen);return [c["namespace"],axes["structural_seed"],axes["parameter_seed"],gen,int(row["cell_id"]),row["row_id"],bank_index,kind,counter]
def one_control(c:Mapping[str,Any],gen:int,row:Mapping[str,Any],truth:np.ndarray,bank_index:int,kind:str)->np.ndarray:
 eps=float(c["control_bank"]["zero_norm_threshold"]);tn=float(np.linalg.norm(truth))
 if tn<=eps:raise ValueError("zero donor norm")
 cell=c["design"]["cells"][row["cell_id"]];m=r2.generator_mats(graph_seed(c,gen),cell)
 for counter in range(1000):
  g=np.random.Generator(np.random.PCG64DXSM(digest_seed(seed_tuple(c,gen,row,bank_index,kind,counter))))
  if kind=="isotropic":x=g.standard_normal(640,dtype=np.float64)
  else:
   coeff=g.standard_normal(len(m["nuisance"]),dtype=np.float64);v=coeff@m["nuisance"].astype(np.float64);sites=np.zeros((10,64),np.float64);sites[m["active"]]=v/max(len(m["active"]),1);x=sites.reshape(-1)
  x-=float(x@truth)*truth/max(float(truth@truth),eps);n=float(np.linalg.norm(x))
  if n>eps:return (x*(tn/n)).astype(np.float32)
 raise RuntimeError("control resampling exhausted")
def make_bank(rows:Sequence[Mapping[str,Any]],c:Mapping[str,Any],gen:int,truth:np.ndarray,kind:str)->np.ndarray:
 return np.stack([[one_control(c,gen,r,truth[i],j,kind) for j in range(c["control_bank"]["size"])] for i,r in enumerate(rows)])

def interval(values:np.ndarray,blocks:np.ndarray,c:Mapping[str,Any],panel:str,endpoint:str)->dict[str,float]:
 groups=[values[blocks==b] for b in np.unique(blocks)];point=float(np.mean([g.mean() for g in groups]));bc=c["control_bank"];seed=digest_seed([c["namespace"],panel,endpoint,"bootstrap",bc["bootstrap_seed"]]);rg=np.random.Generator(np.random.PCG64DXSM(seed));within=[]
 for group in groups:
  pick=rg.integers(0,len(group),size=(bc["draws"],len(group)));within.append(group[pick].mean(1))
 within=np.stack(within,1);outer=rg.integers(0,len(groups),size=(bc["draws"],len(groups)));draw=within[np.arange(bc["draws"])[:,None],outer].mean(1);q=np.quantile(draw,bc["quantiles"],method=bc["method"]);return {"point":point,"lower":float(q[0]),"upper":float(q[1])}
def centered(x:np.ndarray)->np.ndarray:return x-x.mean(1,keepdims=True)
def technical_score(rows:Sequence[Mapping[str,Any]],c:Mapping[str,Any],gen:int,panel:str,bank:np.ndarray,pred:np.ndarray|None=None,pred_sham:np.ndarray|None=None)->dict[str,Any]:
 g=graph_seed(c,gen);clean=r2.trace_np(rows,c,g,"clean");cor=r2.trace_np(rows,c,g,"corrupt");sh=r2.trace_np(rows,c,g,"sham");d=(clean["trace"]-cor["trace"]).reshape(len(rows),640);ds=(sh["trace"]-cor["trace"]).reshape(len(rows),640);t=np.array([r["target"] for r in rows]);co=np.array([r["contrast"] for r in rows]);den=r2.margin(clean["logits"],t)-r2.margin(cor["logits"],t);scale=np.sqrt(np.mean((centered(clean["logits"])-centered(cor["logits"]))**2,1));eligible=(np.argmax(clean["logits"],1)==t)&(np.argmax(cor["logits"],1)==co)&(den>c["eligibility"]["effect_strict"])&(np.linalg.norm(d,axis=1)>c["control_bank"]["zero_norm_threshold"])
 pred=d if pred is None else pred;pred_sham=ds if pred_sham is None else pred_sham
 pl=r2.topological_patch_logits(cor["trace"],pred,rows,c,g);sl=r2.topological_patch_logits(cor["trace"],pred_sham,rows,c,g);abl=r2.topological_patch_logits(clean["trace"],-pred,rows,c,g);sd=np.maximum(den,1e-6);ss=np.maximum(scale,1e-6);rec=(r2.margin(pl,t)-r2.margin(cor["logits"],t))/sd;sr=(r2.margin(sl,t)-r2.margin(cor["logits"],t))/sd;nec=(r2.margin(clean["logits"],t)-r2.margin(abl,t))/sd;fv=1-np.sqrt(np.mean((centered(pl)-centered(clean["logits"]))**2,1))/ss;control_rec=np.zeros(len(rows))
 for j in range(bank.shape[1]):
  ctl=r2.topological_patch_logits(cor["trace"],bank[:,j],rows,c,g);control_rec+=(r2.margin(ctl,t)-r2.margin(cor["logits"],t))/sd
 control_rec/=bank.shape[1];coll=[]
 for i in range(len(rows)):
  mask=np.ones(32,bool);mask[t[i]]=False;mask[co[i]]=False;coll.append(np.sqrt(np.mean((centered(pl)[i,mask]-centered(clean["logits"])[i,mask])**2))/ss[i])
 vals={"recovery":rec,"sham_specificity":rec-sr,"control_margin":rec-control_rec,"collateral_error":np.array(coll),"necessity":nec,"full_vocab_recovery":fv};blocks=np.array([r["block"] for r in rows]);eb=len(np.unique(blocks[eligible]));mins=(c["panels"][f"{panel}_minimum_total"],c["panels"][f"{panel}_minimum_blocks"]);support=int(eligible.sum())>=mins[0] and eb>=mins[1];metrics={k:interval(v[eligible],blocks[eligible],c,panel,f"{gen}:{rows[0]['cell_id']}:{k}") for k,v in vals.items()} if support else {};gates={k:r2.gate(k,v,c) for k,v in metrics.items()};control_interval=interval(control_rec[eligible],blocks[eligible],c,panel,f"{gen}:{rows[0]['cell_id']}:control_recovery") if support else None;return {"support_pass":support,"eligible":int(eligible.sum()),"eligible_blocks":eb,"metrics":metrics,"gate_decisions":gates,"all_gates_pass":support and len(gates)==6 and all(gates.values()),"control_recovery_descriptive":{"mean":float(np.mean(control_rec[eligible])) if support else None,"median":float(np.median(control_rec[eligible])) if support else None,"p90":float(np.quantile(control_rec[eligible],.9)) if support else None,"maximum":float(np.max(control_rec[eligible])) if support else None,"bootstrap_upper":control_interval["upper"] if support else None}}

def incomplete_shared_qa(rows:Sequence[Mapping[str,Any]],c:Mapping[str,Any],gen:int,panel:str,bank:np.ndarray)->dict[str,Any]:
 g=graph_seed(c,gen);cl=r2.trace_np(rows,c,g,"clean");co=r2.trace_np(rows,c,g,"corrupt");sh=r2.trace_np(rows,c,g,"sham");d=(cl["trace"]-co["trace"]).reshape(len(rows),640);ds=(sh["trace"]-co["trace"]).reshape(len(rows),640);cell=c["design"]["cells"][rows[0]["cell_id"]];active=r2.generator_mats(g,cell)["active"].tolist();groups={f"site_{s}":[s] for s in active}
 if cell["complexity"]=="four_heads_two_layers":groups|={"layer1_aggregate":[s for s in active if 1<=s<=4],"layer2_aggregate":[s for s in active if 5<=s<=8]}
 if cell["bypass"]:groups["bypass"]=[9]
 out={}
 for label,sites in groups.items():
  p=d.copy();q=ds.copy()
  for site in sites:p[:,site*64:(site+1)*64]=0;q[:,site*64:(site+1)*64]=0
  rec=technical_score(rows,c,gen,panel,bank,p,q);out[label]={"omitted_sites":sites,"misses_gate":not rec["all_gates_pass"],"record":rec}
 return {"sites":out,"pass":bool(out) and all(x["misses_gate"] for x in out.values()),"shared_bank":True}

def candidate(device_name:str,record:bool)->dict[str,Any]:
 c=cfg();validate_preservation(c);device=torch.device(device_name);checks=[]
 for gen in generators(c):
  for cell in range(128):checks.append(r2.qa_exact(r2.smoke_rows(cell),c,graph_seed(c,gen),device))
 gen=generators(c)[0];g=graph_seed(c,gen);row=panel_rows("qualification",c)[0];cl=r2.trace_np([row],c,g,"clean");co=r2.trace_np([row],c,g,"corrupt");d=(cl["trace"]-co["trace"]).reshape(-1);a=one_control(c,gen,row,d,0,"isotropic");b=one_control(c,gen,row,d,0,"isotropic")
 smoke_c=copy.deepcopy(c);smoke_c["panels"]["qualification_minimum_total"]=8;smoke_c["panels"]["qualification_minimum_blocks"]=2;smoke_c["control_bank"]["size"]=4;smoke_c["control_bank"]["draws"]=50
 smoke=[x for x in panel_rows("qualification",smoke_c) if x["cell_id"]==0][:8];scl=r2.trace_np(smoke,smoke_c,g,"clean");sco=r2.trace_np(smoke,smoke_c,g,"corrupt");truth=(scl["trace"]-sco["trace"]).reshape(len(smoke),640);bank=make_bank(smoke,smoke_c,gen,truth,"isotropic");score_smoke=technical_score(smoke,smoke_c,gen,"qualification",bank);incomplete=incomplete_shared_qa(smoke,smoke_c,gen,"qualification",bank);view=r2.view_firewall_qa(smoke,smoke_c,g)
 rows_total=sum(c["panels"][p]["blocks_per_cell"]*c["panels"][p]["rows_per_block"]*128 for p in ("qualification","validation"));estimated_bytes=rows_total*len(generators(c))*c["control_bank"]["size"]*2*640*4
 distinct=all(r["target"]!=r["contrast"] and r["target"]!=r["sham"] and r["contrast"]!=r["sham"] for r in panel_rows("qualification",c)+panel_rows("validation",c))
 ok=all(x["pass"] for x in checks) and np.array_equal(a,b) and score_smoke["all_gates_pass"] and incomplete["pass"] and view["pass"] and distinct
 # Representative no-panel throughput and current-filesystem capacity gate.
 tic=time.perf_counter();_=[r2.topological_patch_logits(sco["trace"],bank[:,j],smoke,smoke_c,g) for j in range(bank.shape[1])];elapsed=time.perf_counter()-tic;vector_seconds=elapsed/max(len(smoke)*bank.shape[1],1);estimated_seconds=vector_seconds*rows_total*len(generators(c))*c["control_bank"]["size"]*2;disk_free=os.statvfs(ROOT).f_bavail*os.statvfs(ROOT).f_frsize;runtime_ok=estimated_seconds<c["hard_timeout_hours"]*3600*.8 and disk_free>estimated_bytes*1.5
 ok=ok and runtime_ok;result={"schema_version":"causal_manifold_bridge_v2_technical_candidate","status":"PASS" if ok else "FAIL","scientific_panel_accessed":False,"all_endpoint_smoke_checks":len(checks),"shared_bank_golden_sha256":hashlib.sha256(a.tobytes()).hexdigest(),"bootstrap_golden":interval(np.array([0.,2.,10.]),np.array([0,0,1]),c,"qualification","registered-golden"),"shared_bank_technical_score_smoke_pass":score_smoke["all_gates_pass"],"shared_bank_incomplete_smoke_pass":incomplete["pass"],"view_firewall_smoke_pass":view["pass"],"target_contrast_sham_distinct":distinct,"generator_axes":[generator_axes(c,g) for g in generators(c)],"runtime_profile":{"scientific_rows":rows_total,"control_vectors":rows_total*len(generators(c))*c["control_bank"]["size"]*2,"estimated_control_storage_bytes":estimated_bytes,"disk_free_bytes":disk_free,"representative_vector_seconds":vector_seconds,"estimated_all_control_seconds":estimated_seconds,"within_80pct_timeout_and_1_5x_disk":runtime_ok},"method_inventory":["exact_controller","identity_full640"],"estimated_methods_present":False,"training_path_present":False,"source_sha256":sha(SCRIPT),"transitive_runtime_hashes":transitive_runtime_hashes(c),"config_sha256":sha(CFG),"plan_sha256":sha(PLAN),"tests_sha256":{"study":sha(TEST),"launcher":sha(LAUNCH_TEST)},"launcher_sha256":sha(LAUNCHER)}
 if record:atomic_json(rp(c,"candidate_manifest"),result)
 return result
def verify_review(p:Path,bound:str)->None:
 text=p.read_text();v=[x for x in text.splitlines() if x.startswith("VERDICT:")]
 if v!=["VERDICT: SHIP"] or f"BOUND_SHA256: {bound}" not in text:raise RuntimeError("unbound/non-SHIP review")
def create_lock()->dict[str,Any]:
 c=cfg();validate_preservation(c);candidate_sha=sha(rp(c,"candidate_manifest"));verify_review(rp(c,"candidate_review"),candidate_sha);audit=freshness_audit(panel_set(c),c);x={"schema_version":"causal_manifold_bridge_v2_technical_generator_lock","source_sha256":sha(SCRIPT),"transitive_runtime_hashes":transitive_runtime_hashes(c),"config_sha256":sha(CFG),"plan_sha256":sha(PLAN),"candidate_sha256":candidate_sha,"candidate_review_sha256":sha(rp(c,"candidate_review")),"tests_sha256":{"study":sha(TEST),"launcher":sha(LAUNCH_TEST)},"launcher_sha256":sha(LAUNCHER),"control_contract_sha256":hashlib.sha256(canon(c["control_bank"])).hexdigest(),"freshness_audit_sha256":hashlib.sha256(canon(audit)).hexdigest()};atomic_json(rp(c,"generator_lock"),x);return x
def prepare()->dict[str,Any]:
 c=cfg();lock=loadj(rp(c,"generator_lock"));
 if lock["source_sha256"]!=sha(SCRIPT) or lock["transitive_runtime_hashes"]!=transitive_runtime_hashes(c) or lock["config_sha256"]!=sha(CFG) or lock["plan_sha256"]!=sha(PLAN) or lock["tests_sha256"]!={"study":sha(TEST),"launcher":sha(LAUNCH_TEST)} or lock["launcher_sha256"]!=sha(LAUNCHER) or lock["candidate_sha256"]!=sha(rp(c,"candidate_manifest")) or lock["candidate_review_sha256"]!=sha(rp(c,"candidate_review")) or lock["control_contract_sha256"]!=hashlib.sha256(canon(c["control_bank"])).hexdigest():raise RuntimeError("generator lock drift")
 root=rp(c,"prepared_root")
 if root.exists():raise FileExistsError(root)
 panels=panel_set(c);audit=freshness_audit(panels,c)
 if hashlib.sha256(canon(audit)).hexdigest()!=lock["freshness_audit_sha256"]:raise RuntimeError("locked freshness audit drift")
 root.mkdir(parents=True);payloads=[]
 for stage,rows in panels.items():
  p=root/f"{stage}.jsonl";r2.base.write_jsonl(p,rows);payloads.append({"stage":stage,"path":p.relative_to(ROOT).as_posix(),"rows":len(rows),"sha256":sha(p)})
 x={"schema_version":"causal_manifold_bridge_v2_technical_prepared","status":"PREPARED_UNOPENED","freshness":audit,"payloads":payloads};atomic_json(root/"PREPARED.json",x);return x
def freeze()->dict[str,Any]:
 c=cfg();prep=loadj(rp(c,"prepared_root")/"PREPARED.json");x={"schema_version":"causal_manifold_bridge_v2_technical_freeze","generator_lock_sha256":sha(rp(c,"generator_lock")),"payloads":prep["payloads"],"freshness":prep["freshness"],"method_inventory":["exact_controller","identity_full640"]};atomic_json(rp(c,"freeze"),x);return x
def verify_frozen()->dict[str,Any]:
 c=cfg();validate_preservation(c);lock=loadj(rp(c,"generator_lock"));fr=loadj(rp(c,"freeze"));binding=loadj(rp(c,"review_binding"));
 if lock["source_sha256"]!=sha(SCRIPT) or lock["transitive_runtime_hashes"]!=transitive_runtime_hashes(c) or lock["config_sha256"]!=sha(CFG) or lock["plan_sha256"]!=sha(PLAN) or lock["tests_sha256"]!={"study":sha(TEST),"launcher":sha(LAUNCH_TEST)} or lock["launcher_sha256"]!=sha(LAUNCHER) or lock["candidate_sha256"]!=sha(rp(c,"candidate_manifest")) or lock["candidate_review_sha256"]!=sha(rp(c,"candidate_review")) or lock["control_contract_sha256"]!=hashlib.sha256(canon(c["control_bank"])).hexdigest() or hashlib.sha256(canon(fr["freshness"])).hexdigest()!=lock["freshness_audit_sha256"] or fr["generator_lock_sha256"]!=sha(rp(c,"generator_lock")):raise RuntimeError("freeze drift")
 for x in fr["payloads"]:
  if sha(ROOT/x["path"])!=x["sha256"]:raise RuntimeError("payload drift")
 if binding["candidate_bound_sha256"]!=sha(rp(c,"candidate_manifest")) or binding["freeze_bound_sha256"]!=sha(rp(c,"freeze")):raise RuntimeError("binding drift")
 verify_review(rp(c,"candidate_review"),binding["candidate_bound_sha256"]);verify_review(rp(c,"frozen_review"),binding["freeze_bound_sha256"]);return {"status":"PASS"}
def read_stage(c:Mapping[str,Any],stage:str)->list[dict[str,Any]]:
 x=next(x for x in loadj(rp(c,"freeze"))["payloads"] if x["stage"]==stage);return r2.base.read_jsonl(ROOT/x["path"])
def write_failure_terminal(c:Mapping[str,Any],exc:BaseException)->None:
 p=rp(c,"provenance_root")/"TERMINAL.json"
 if p.exists():return
 try:atomic_json(p,{"status":"TECHNICAL_FAILURE","no_retry_authorized":True,"error_type":type(exc).__name__,"error":str(exc),"partial_artifacts":"FORENSIC_ONLY_NOT_SCIENTIFIC","time_ns":time.time_ns()})
 except FileExistsError:pass
def install_signal_terminalizer()->None:
 def stop(signum:int,_frame:Any)->None:raise TimeoutError(f"terminated by signal {signum}")
 signal.signal(signal.SIGTERM,stop);signal.signal(signal.SIGINT,stop)
def run(physical_index:int,gpu_uuid:str,pane_pid:int,lockdir:str,token:str)->None:
 c=cfg();validate_environment(c);verify_frozen();out=rp(c,"output_root");prov=rp(c,"provenance_root")
 if out.exists() or prov.exists():raise FileExistsError("namespace exists")
 if os.environ.get("CUDA_VISIBLE_DEVICES")!=gpu_uuid or Path(lockdir).name!=f"msae_gpu_{gpu_uuid}.lockdir" or (Path(lockdir)/"token").read_text().strip()!=token:raise RuntimeError("GPU ownership mismatch")
 manifest=loadj(rp(c,"launch_manifest"));expected={"gpu_uuid":gpu_uuid,"physical_index":physical_index,"pane_pid":pane_pid,"session":c["runtime"]["tmux_session"],"token_sha256":hashlib.sha256(token.encode()).hexdigest()}
 if manifest!=expected or not is_descendant(os.getpid(),pane_pid):raise RuntimeError("launch manifest/ancestry mismatch")
 device=torch.device("cuda:0");torch.use_deterministic_algorithms(True);random.seed(c["seed"]);np.random.seed(c["seed"]);torch.manual_seed(c["seed"]);torch.ones(1,device=device).sum().item();torch.cuda.synchronize();out.mkdir(parents=True);prov.mkdir(parents=True);event(prov,0,"RUN_START_NO_PANEL_ACCESS",gpu_uuid=gpu_uuid,physical_index=physical_index,pid=os.getpid());event(prov,1,"GPU_LOCK_OWNERSHIP_TRANSFERRED",lockdir=lockdir)
 event(prov,10,"QUALIFICATION_ACCESS_MAY_HAVE_OCCURRED");rows=read_stage(c,"qualification");event(prov,11,"QUALIFICATION_OPENED",rows=len(rows));qualification={};all_pass=True
 for gen in generators(c):
  per={}
  for cell in range(128):
   rr=[x for x in rows if x["cell_id"]==cell];g=graph_seed(c,gen);cl=r2.trace_np(rr,c,g,"clean");co=r2.trace_np(rr,c,g,"corrupt");truth=(cl["trace"]-co["trace"]).reshape(len(rr),640);iso=make_bank(rr,c,gen,truth,"isotropic");nuis=make_bank(rr,c,gen,truth,"nuisance");bank_path=out/"control_banks"/"qualification"/str(gen)/f"cell_{cell:03d}.npz";bank_path.parent.mkdir(parents=True,exist_ok=True);np.savez(bank_path,isotropic=iso,nuisance=nuis);rec=technical_score(rr,c,gen,"qualification",iso);nuis_diag=technical_score(rr,c,gen,"qualification",nuis);qa=r2.qa_exact(rr,c,g,device);view=r2.view_firewall_qa(rr,c,g);incomplete=incomplete_shared_qa(rr,c,gen,"qualification",iso);endpoint=qa["pass"] and view["pass"] and incomplete["pass"] and rec["all_gates_pass"];per[str(cell)]={"generator_axes":generator_axes(c,gen),"exact_qa":qa,"view_firewall":view,"incomplete_qa":incomplete,"exact_controller":rec,"identity_full640":rec,"nuisance_bank_diagnostic_not_gating":nuis_diag,"shared_bank_sha256":sha(bank_path),"exact_identity_control_inputs_equal":True,"endpoint_pass":endpoint};all_pass&=endpoint
  qualification[str(gen)]=per;atomic_json(out/"qualification"/f"generator_{gen}.json",per)
 locked_audit=loadj(rp(c,"generator_lock"))["freshness_audit_sha256"];fresh_ok=hashlib.sha256(canon(loadj(rp(c,"freeze"))["freshness"])).hexdigest()==locked_audit;authorized=validation_authorized([all_pass],fresh_ok,None)
 pre={"all_512_endpoints_pass":bool(all_pass),"estimated_method_outcomes_used_for_authorization":False,"locked_freshness_audit_sha256":locked_audit,"validation_authorized":authorized};atomic_json(out/"PREVALIDATION.json",pre);event(prov,20,"PREVALIDATION_SEALED",validation_authorized=authorized)
 if not authorized:atomic_json(prov/"TERMINAL.json",{"status":"BRIDGE_V2_QUALIFICATION_TECHNICAL_STOP","no_retry_authorized":True});return
 event(prov,30,"VALIDATION_ACCESS_MAY_HAVE_OCCURRED");vrows=read_stage(c,"validation");event(prov,31,"VALIDATION_OPENED",rows=len(vrows));validation={};all_v=True
 for gen in generators(c):
  per={}
  for cell in range(128):
   rr=[x for x in vrows if x["cell_id"]==cell];g=graph_seed(c,gen);cl=r2.trace_np(rr,c,g,"clean");co=r2.trace_np(rr,c,g,"corrupt");truth=(cl["trace"]-co["trace"]).reshape(len(rr),640);iso=make_bank(rr,c,gen,truth,"isotropic");nuis=make_bank(rr,c,gen,truth,"nuisance");bank_path=out/"control_banks"/"validation"/str(gen)/f"cell_{cell:03d}.npz";bank_path.parent.mkdir(parents=True,exist_ok=True);np.savez(bank_path,isotropic=iso,nuisance=nuis);rec=technical_score(rr,c,gen,"validation",iso);nuis_diag=technical_score(rr,c,gen,"validation",nuis);endpoint=rec["all_gates_pass"];per[str(cell)]={"generator_axes":generator_axes(c,gen),"exact_controller":rec,"identity_full640":rec,"nuisance_bank_diagnostic_not_gating":nuis_diag,"shared_bank_sha256":sha(bank_path),"exact_identity_control_inputs_equal":True,"endpoint_pass":endpoint};all_v&=endpoint
  validation[str(gen)]=per;atomic_json(out/"validation"/f"generator_{gen}.json",per)
 final={"schema_version":"causal_manifold_bridge_v2_technical_final","status":"BRIDGE_V2_TECHNICALLY_QUALIFIED" if all_v else "BRIDGE_V2_VALIDATION_TECHNICAL_STOP","qualification":qualification,"validation":validation,"estimated_methods_evaluated":False,"training":False};atomic_json(out/"final"/"result.json",final);atomic_json(prov/"TERMINAL.json",{"status":final["status"],"no_retry_authorized":True,"final_sha256":sha(out/"final"/"result.json")})
def main()->None:
 ap=argparse.ArgumentParser();sp=ap.add_subparsers(dest="cmd",required=True);q=sp.add_parser("candidate");q.add_argument("--device",default="cpu");q.add_argument("--record",action="store_true");sp.add_parser("create-lock");sp.add_parser("prepare");sp.add_parser("freeze");sp.add_parser("verify-frozen");q=sp.add_parser("run");q.add_argument("--physical-index",type=int,required=True);q.add_argument("--gpu-uuid",required=True);q.add_argument("--pane-pid",type=int,required=True);q.add_argument("--gpu-lockdir",required=True);q.add_argument("--launch-token",required=True);a=ap.parse_args()
 if a.cmd=="candidate":print(json.dumps(candidate(a.device,a.record),sort_keys=True))
 elif a.cmd=="create-lock":print(json.dumps(create_lock(),sort_keys=True))
 elif a.cmd=="prepare":print(json.dumps(prepare(),sort_keys=True))
 elif a.cmd=="freeze":print(json.dumps(freeze(),sort_keys=True))
 elif a.cmd=="verify-frozen":print(json.dumps(verify_frozen(),sort_keys=True))
 else:
  install_signal_terminalizer()
  try:run(a.physical_index,a.gpu_uuid,a.pane_pid,a.gpu_lockdir,a.launch_token)
  except BaseException as exc:
   write_failure_terminal(cfg(),exc)
   raise
if __name__=="__main__":main()
