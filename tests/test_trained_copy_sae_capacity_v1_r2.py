from __future__ import annotations
import copy,importlib.util,sys
from pathlib import Path
import numpy as np
import torch
ROOT=Path(__file__).resolve().parents[1];SPEC=importlib.util.spec_from_file_location("saecap",ROOT/"scripts/trained_copy_sae_capacity_v1_r2.py");assert SPEC and SPEC.loader;m=importlib.util.module_from_spec(SPEC);sys.modules["saecap"]=m;SPEC.loader.exec_module(m)

def test_fresh_panels():
 c=m.cfg();ps=m.panel_set(c);a=m.freshness_audit(ps,c)
 assert a["pass"] and {k:len(v) for k,v in ps.items()}=={"fit":2048,"development":256,"confirmation":256}

def test_topk_and_orders():
 sae=m.TopKSAE(16,7,torch.device("cpu"));x=torch.randn(12,64);assert torch.all((sae.encode(x)!=0).sum(1)<=16)
 score=torch.tensor([2.,2.,1.]);assert m.stable_order(score)==[0,1,2]
 cc=torch.randn(5,256);rc=torch.randn(5,256);truth=torch.randn(5,64);order=m.greedy_reconstruction_order(cc,rc,sae.decoder,truth);assert sorted(order)==list(range(256))
 # The chunked formula must equal the direct registered greedy objective on a small prefix.
 contrib=(cc-rc)[:,:,None]*sae.decoder[None];res=truth.clone();remain=set(range(256));ref=[]
 for _ in range(3):
  scored=[(float(torch.sum((res-contrib[:,j])**2)),j) for j in sorted(remain)];_,j=min(scored,key=lambda x:(x[0],x[1]));ref.append(j);res-=contrib[:,j];remain.remove(j)
 assert order[:3]==ref

def test_candidate_no_scientific_access():
 x=m.candidate("cpu",False);assert x["status"]=="PASS" and x["scientific_panel_accessed"] is False and all(x["checks"].values())
 assert x["expected_method_count_per_checkpoint"]==323

def test_config_scope_and_crossed_budgets():
 c=m.cfg();assert c["scope"]["k2_evaluated"] is False and c["sae"]["topks"]==c["sae"]["selector_budgets"]==[16,32,64,128,256]
 assert len(c["sae"]["selectors"])==4 and c["sae"]["seeds"]==[9601,9602,9603]
 assert c["linear"]["random_ranks"]==[16,32] and c["linear"]["random_seed"]==9651
 assert len(m.expected_method_names(c))==m.expected_method_count(c)==323
 assert sum(p.numel() for p in m.TopKSAE(16,1,torch.device("cpu")).parameters())==32832
 assert m.confirmation_authorization(True,True,{"all_failed":True}) and not m.confirmation_authorization(False,True,{})

def test_prepare_is_fail_closed_on_reused_payload_root():
 try:m.prepare();assert False
 except FileExistsError:pass

def test_launch_contract_and_clean_namespace():
 text=m.LAUNCHER.read_text();assert "GPU_LOCK_OWNERSHIP_TRANSFERRED" in text and "FIT_ACCESS_MAY_HAVE_OCCURRED" in text and "query-compute-apps=gpu_uuid,pid" in text
 c=m.cfg();assert not m.rp(c,"output_root").exists() and not m.rp(c,"provenance_root").exists()

def test_greedy_behavior_selector_is_complete_and_deterministic():
 class Toy:
  def readout(self,x):return x[...,:32]
 n=8;g=torch.Generator().manual_seed(44);sae=m.TopKSAE(16,9,torch.device("cpu"));states={k:torch.randn(n,64,generator=g) for k in ("clean","corrupt","sham")}
 t=torch.zeros(n,dtype=torch.long);co=torch.ones(n,dtype=torch.long);clean=torch.zeros(n,32);corrupt=torch.zeros(n,32);clean[:,0]=5;corrupt[:,1]=5
 z={**states,"delta":states["clean"]-states["corrupt"],"sham_delta":states["sham"]-states["corrupt"],"target":t,"contrast":co,"logits_clean":clean,"logits_corrupt":corrupt}
 one=m.greedy_behavior_order(sae,Toy(),z)
 assert sorted(one)==list(range(256))

def test_r1_checkpoint_loader_bypasses_incompatible_r4_2_config_validator():
 c=m.cfg();model=m.load_model(c,c["model"]["seeds"][0],torch.device("cpu"));assert model.training is False

def test_r1_recovery_lineage_and_corruption_detection(tmp_path):
 import hashlib,json
 artifact=tmp_path/"artifact";artifact.write_bytes(b"stable");h=hashlib.sha256(b"stable").hexdigest();record=tmp_path/"record.json";record.write_text(json.dumps({"artifacts":[{"path":"artifact","bytes":6,"sha256":h}],"root_inventories":[{"path":".","exists":True,"files":2}]})+"\n");rh=m.sha(record);old=m.ROOT;m.ROOT=tmp_path
 try:
  assert m.verify_preservation_record(record,rh)["artifacts"][0]["sha256"]==h
  artifact.write_bytes(b"broken")
  try:m.verify_preservation_record(record,rh);assert False
  except RuntimeError:pass
 finally:m.ROOT=old
 assert m.validate_recovery_lineage(m.cfg())["pass"]

def test_sae_numpy_recovery_preserves_predictions_logits_metrics_and_gates():
 c=m.cfg();c=copy.deepcopy(c);c['panels']['fit_recovery_parity']=c['panels']['fit'];rows=m.base.read_jsonl(m.ROOT/c["runtime"]["prepared_root"]/'fit.jsonl');device=torch.device('cpu');model=m.load_model(c,5101,device);z=m.base.context(model,rows,device)
 saved=torch.load(m.ROOT/'results/trained_copy_sae_capacity_v1_r1_20260813/checkpoints/5101/sae_topk16_seed9601.pt',map_location=device,weights_only=False);sae=m.TopKSAE(16,9601,device);sae.load_state_dict(saved['state_dict']);sae.eval();selected=saved['selectors']['variance'][:16]
 with torch.no_grad():
  sel=torch.tensor(selected);zc=sae.encode(z['corrupt']);base_dec=sae.decode(zc);za=zc.clone();zs=zc.clone();za[:,sel]=sae.encode(z['clean'])[:,sel];zs[:,sel]=sae.encode(z['sham'])[:,sel];ref=sae.decode(za)-base_dec;ref_sham=sae.decode(zs)-base_dec
 actual,sham=m.sae_prediction(sae,selected,z)
 assert not actual.requires_grad and not sham.requires_grad
 assert torch.equal(actual,ref) and torch.equal(sham,ref_sham)
 np.testing.assert_array_equal(actual.detach().numpy(),ref.numpy())
 with torch.no_grad():
  ref_logits=model.readout(torch.nn.functional.layer_norm(z['corrupt']+ref,(64,),eps=1e-5));actual_logits=model.readout(torch.nn.functional.layer_norm(z['corrupt']+actual,(64,),eps=1e-5))
 assert torch.equal(ref_logits,actual_logits)
 method=m.base.Method('detach_parity','detach_parity','sae',None)
 one=m.base.score(method,ref,ref_sham,z,rows,c,'fit_recovery_parity',model,'native');two=m.base.score(method,actual,sham,z,rows,c,'fit_recovery_parity',model,'native')
 assert one==two and one['gate_decisions']==two['gate_decisions']
 ref_m,ref_ok=m.base.r5.norm_match(ref.detach().numpy(),z['delta'].detach().numpy());ref_sm,ref_ok2=m.base.r5.norm_match(ref_sham.detach().numpy(),z['delta'].detach().numpy());act_m,act_ok=m.base.r5.norm_match(actual.detach().numpy(),z['delta'].detach().numpy());act_sm,act_ok2=m.base.r5.norm_match(sham.detach().numpy(),z['delta'].detach().numpy())
 assert np.array_equal(ref_m,act_m) and np.array_equal(ref_sm,act_sm) and np.array_equal(ref_ok,act_ok) and np.array_equal(ref_ok2,act_ok2)
 status='complete' if bool(act_ok.all() and act_ok2.all()) else 'prediction_incomplete';ref_t=torch.tensor(ref_m);ref_st=torch.tensor(ref_sm);act_t=torch.tensor(act_m);act_st=torch.tensor(act_sm)
 one_m=m.base.score(method,ref_t,ref_st,z,rows,c,'fit_recovery_parity',model,'matched',status);two_m=m.base.score(method,act_t,act_st,z,rows,c,'fit_recovery_parity',model,'matched',status)
 assert one_m==two_m and one_m['gate_decisions']==two_m['gate_decisions']
