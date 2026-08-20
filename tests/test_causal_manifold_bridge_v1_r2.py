from __future__ import annotations
import copy,importlib.util,sys
from pathlib import Path
import numpy as np,torch
ROOT=Path(__file__).resolve().parents[1];SPEC=importlib.util.spec_from_file_location("cmb",ROOT/"scripts/causal_manifold_bridge_v1_r2.py");assert SPEC and SPEC.loader;m=importlib.util.module_from_spec(SPEC);sys.modules["cmb"]=m;SPEC.loader.exec_module(m)

def test_full_factorial_and_panels():
 c=m.cfg();m.validate_config(c);assert len(c["design"]["cells"])==128
 audit=m.loadj(m.ROOT/c['recovery_lineage']['r1_freezes']['items']['causal_manifold_bridge_v1_r1']['path'])['audit'];assert audit["fit"]["rows"]==16384 and audit["development"]["rows"]==4096 and all(audit[s]["cells"]==128 for s in ('fit','development','confirmation'))

def test_exact_overwrite_and_rejected_replacement_semantics():
 c=m.cfg();rows=m.smoke_rows(0)[:4];gen=c["design"]["generator_seeds"][0];cl=m.trace_np(rows,c,gen,"clean");co=m.trace_np(rows,c,gen,"corrupt");d=(cl["trace"]-co["trace"]).reshape(4,640)
 assert np.allclose(m.patch_trace(co["trace"],d),cl["trace"],atol=c["qa"]["atol"],rtol=c["qa"]["relative_l2"])
 assert not np.array_equal(d.reshape(4,10,64),cl["trace"])
 assert not np.array_equal(m.patch_trace(co["trace"],d),co["trace"]+2*d.reshape(4,10,64))
 correct=m.topological_patch_logits(co["trace"],d,rows,c,gen,"overwrite")
 assert np.allclose(correct,cl["logits"],atol=c["qa"]["atol"],rtol=c["qa"]["relative_l2"])
 assert not np.allclose(correct,m.topological_patch_logits(co["trace"],d,rows,c,gen,"live_add"),atol=c["qa"]["atol"],rtol=c["qa"]["relative_l2"])
 assert not np.allclose(correct,m.topological_patch_logits(co["trace"],d,rows,c,gen,"replacement"),atol=c["qa"]["atol"],rtol=c["qa"]["relative_l2"])

def test_torch_numpy_and_instruction_certificate():
 c=m.cfg();rows=m.smoke_rows(0);q=m.qa_exact(rows,c,c["design"]["generator_seeds"][0],torch.device("cpu"));assert q["pass"] and q["identity_within_tolerance"]

def test_information_views_and_scope():
 c=m.cfg();assert c["methods"]["information_views"]["instruction_conditioned"]==["corrupt_trace","cell_config","query","offset"]
 assert c["scope"]["donor_free_discovery"] and not c["scope"]["k2_evaluated"]
 assert c["methods"]["expected_input_rank"]=={"corrupt":68,"instruction":801,"answer":96}

def test_prepare_is_fail_closed_on_reused_payload_root():
 try:m.prepare();assert False
 except FileExistsError:pass

def test_candidate_has_no_panel_access():
 x=m.candidate("cpu",False);assert x["status"]=="PASS" and not x["scientific_panel_accessed"] and x["factorial_cells"]==128
 assert x["all_cell_exact_checks"]==512 and x["incomplete_mutations_detected"]

def test_view_firewall_and_incomplete_control():
 c=m.cfg();c["bootstrap"]["draws"]=50;rows=m.smoke_rows(127);gen=c["design"]["generator_seeds"][0]
 view=m.view_firewall_qa(rows,c,gen);assert view["pass"] and all(view["allowed_field_sensitivity"].values()) and view["forbidden_perturbation_invariant"]
 assert m.incomplete_qa(rows,c,gen,"smoke")["pass"]

def test_block_support_is_required():
 c=m.cfg();c["bootstrap"]["draws"]=20;rows=[]
 for i in range(32):
  x=dict(m.smoke_rows(0)[i%8]);x.update(row_id=f"dup-{i}",row_seed=m.seed32("dup",i),block=0);rows.append(x)
 cl=m.trace_np(rows,c,1,"clean");co=m.trace_np(rows,c,1,"corrupt");sh=m.trace_np(rows,c,1,"sham")
 rec=m.score("exact",(cl["trace"]-co["trace"]).reshape(32,640),(sh["trace"]-co["trace"]).reshape(32,640),rows,c,1,"smoke")
 assert not rec["support_pass"] and rec["eligible_blocks"]==1

def test_realized_factorial_contrasts():
 q=m.realized_design_qa(m.cfg(),m.cfg()["design"]["generator_seeds"][0]);assert q["pass"] and q["contrast_rank"]==128 and q["contrast_shape"]==[128,128]
 assert q["realized_correlation_separated"] and q["realized_correlation_group_means"]["0.7"]-q["realized_correlation_group_means"]["0.0"]>.25
 assert all("realized_attention_entropy" in x and "realized_distractor_mass" in x and "realized_causal_nuisance_correlation" in x for x in q["cells"])
 assert len(q["repeated_condition_certificates"])==128 and all(x["pass"] and x["offsets"]==31 for x in q["repeated_condition_certificates"])

def test_exact_technical_gate_is_stricter_than_scientific_gate():
 metric=lambda point,lower,upper:{"point":point,"lower":lower,"upper":upper}
 good={"matched_status":"complete","all_gates_pass":True,"native":{"metrics":{"recovery":metric(1,1,1),"full_vocab_recovery":metric(1,1,1),"collateral_error":metric(0,0,0)}},"matched":{"metrics":{"recovery":metric(1,1,1),"full_vocab_recovery":metric(1,1,1),"collateral_error":metric(0,0,0)}}}
 assert m.exact_technical_pass(good)
 bad={**good,"native":{"metrics":dict(good["native"]["metrics"],recovery=metric(.998,.998,.999))}}
 assert not m.exact_technical_pass(bad)

def test_matrix_rank_condition_and_artifact_reconciliation(tmp_path):
 x=np.eye(8);assert m.matrix_qa(x,8,m.cfg())["pass"] and not m.matrix_qa(np.ones((8,8)),8,m.cfg())["pass"]
 root=tmp_path/"artifacts";root.mkdir();(root/"a").write_bytes(b"a");rec=m.tree_inventory(root);assert m.verify_inventory(root,rec);(root/"a").write_bytes(b"b");assert not m.verify_inventory(root,rec)

def test_launch_contract_and_clean_namespace():
 text=m.LAUNCHER.read_text();assert "GPU_LOCK_OWNERSHIP_TRANSFERRED" in text and "FIT_ACCESS_MAY_HAVE_OCCURRED" in text and "query-compute-apps=gpu_uuid,pid" in text
 c=m.cfg();assert not m.rp(c,"output_root").exists() and not m.rp(c,"provenance_root").exists()

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

def _runtime_matrices(rows,c,gen):
 d=[];clean=[];corrupt=[]
 for cell in range(128):
  rr=[r for r in rows if r['cell_id']==cell];cl=m.trace_np(rr,c,gen,'clean')['trace'].reshape(len(rr),640);co=m.trace_np(rr,c,gen,'corrupt')['trace'].reshape(len(rr),640);d.append(cl-co);clean.append(cl);corrupt.append(co)
 delta=np.concatenate(d).astype(np.float32);states=np.concatenate([np.concatenate(clean),np.concatenate(corrupt)]).astype(np.float32)
 return delta,states

def test_runtime_float64_basis_spectrum_rank_condition_and_serialization_match_all_generators(tmp_path):
 c=m.cfg();rows=m.base.read_jsonl(m.ROOT/c['runtime']['prepared_root']/'fit.jsonl');audit=m.loadj(m.ROOT/c['recovery_lineage']['r1_freezes']['items']['causal_manifold_bridge_v1_r1']['path'])['audit']['fit_matrix_qa'];mismatches=0
 for gen in c['design']['generator_seeds']:
  delta,states=_runtime_matrices(rows,c,gen);basis=m.donor_basis_qa(delta,states,c);dq=basis['donor_matrix_qa'];aq=basis['ambient_matrix_qa'];ref=audit[str(gen)];_,sd,vd=np.linalg.svd(delta.astype(np.float64),full_matrices=False);_,sa,va=np.linalg.svd(states.astype(np.float64),full_matrices=False)
  assert dq['rank']==ref['donor_delta']['rank']==640 and aq['rank']==ref['ambient_states']['rank']==640
  assert np.isclose(dq['condition'],ref['donor_delta']['condition'],rtol=0,atol=1e-10)
  assert np.isclose(aq['condition'],ref['ambient_states']['condition'],rtol=0,atol=1e-10)
  np.testing.assert_allclose(basis['delta_singular'],sd,rtol=0,atol=0);np.testing.assert_allclose(basis['ambient_singular'],sa,rtol=0,atol=0)
  for rank in c['methods']['ranks']:
   np.testing.assert_allclose(basis['delta_basis'][:rank].T@basis['delta_basis'][:rank],vd[:rank].astype(np.float32).T@vd[:rank].astype(np.float32),rtol=1e-6,atol=1e-6)
   np.testing.assert_allclose(basis['ambient_basis'][:rank].T@basis['ambient_basis'][:rank],va[:rank].astype(np.float32).T@va[:rank].astype(np.float32),rtol=1e-6,atol=1e-6)
  ck=tmp_path/str(gen);ck.mkdir();record=m.write_donor_basis(ck,basis);saved=np.load(ck/'bases.npz');np.testing.assert_array_equal(saved['delta_singular'],sd);np.testing.assert_array_equal(saved['ambient_singular'],sa);assert record['donor_matrix_qa']==dq and record['ambient_matrix_qa']==aq
  mismatches+=int(np.linalg.matrix_rank(delta)!=dq['rank'])+int(np.linalg.matrix_rank(states)!=aq['rank'])
 assert mismatches>0

def test_fit_registry_crosses_repaired_qa_and_preserves_basis_values(tmp_path,monkeypatch):
 c=copy.deepcopy(m.cfg());rows=m.base.read_jsonl(m.ROOT/c['runtime']['prepared_root']/'fit.jsonl');gen=c['design']['generator_seeds'][0];delta,states=_runtime_matrices(rows,c,gen)
 c['methods']['ranks']=[640];c['methods']['paired_seeds']=[9101];c['methods']['sae']['topks']=[];c['methods']['sae']['seeds']=[]
 for arch in c['methods']['mlp']['architectures'].values():arch['seeds']=[]
 monkeypatch.setattr(m,'train_torch',lambda *args,**kwargs:{'initial_loss':0.0,'final_loss':0.0,'parameters':sum(p.numel() for p in args[0].parameters())})
 rec=m.fit_registry(rows,c,gen,torch.device('cpu'),tmp_path/'ck');saved=np.load(tmp_path/'ck/bases.npz');_,sd,vd=np.linalg.svd(delta.astype(np.float64),full_matrices=False);_,sa,va=np.linalg.svd(states.astype(np.float64),full_matrices=False)
 np.testing.assert_allclose(saved['delta_singular'],sd,rtol=0,atol=0);np.testing.assert_allclose(saved['ambient_singular'],sa,rtol=0,atol=0)
 np.testing.assert_allclose(saved['delta_basis'].T@saved['delta_basis'],vd.astype(np.float32).T@vd.astype(np.float32),rtol=0,atol=0)
 np.testing.assert_allclose(saved['ambient_basis'].T@saved['ambient_basis'],va.astype(np.float32).T@va.astype(np.float32),rtol=0,atol=0)
 assert rec['bases']['delta_rank']==rec['bases']['ambient_rank']==640 and (tmp_path/'ck/paired_rank640_seed9101.pt').is_file()
