from __future__ import annotations
import importlib.util,sys
from pathlib import Path
import numpy as np,torch
ROOT=Path(__file__).resolve().parents[1];SPEC=importlib.util.spec_from_file_location("cmb",ROOT/"scripts/causal_manifold_bridge_v1_r1.py");assert SPEC and SPEC.loader;m=importlib.util.module_from_spec(SPEC);sys.modules["cmb"]=m;SPEC.loader.exec_module(m)

def test_full_factorial_and_panels():
 c=m.cfg();m.validate_config(c);assert len(c["design"]["cells"])==128
 ps=m.panel_set(c);a=m.panel_audit(ps,c);assert a["fit"]["rows"]==16384 and a["development"]["rows"]==4096 and all(x["cells"]==128 for x in a.values())

def test_exact_overwrite_and_rejected_replacement_semantics():
 c=m.cfg();rows=m.panel_rows("development",c)[:4];gen=c["design"]["generator_seeds"][0];cl=m.trace_np(rows,c,gen,"clean");co=m.trace_np(rows,c,gen,"corrupt");d=(cl["trace"]-co["trace"]).reshape(4,640)
 assert np.allclose(m.patch_trace(co["trace"],d),cl["trace"],atol=c["qa"]["atol"],rtol=c["qa"]["relative_l2"])
 assert not np.array_equal(d.reshape(4,10,64),cl["trace"])
 assert not np.array_equal(m.patch_trace(co["trace"],d),co["trace"]+2*d.reshape(4,10,64))
 correct=m.topological_patch_logits(co["trace"],d,rows,c,gen,"overwrite")
 assert np.allclose(correct,cl["logits"],atol=c["qa"]["atol"],rtol=c["qa"]["relative_l2"])
 assert not np.allclose(correct,m.topological_patch_logits(co["trace"],d,rows,c,gen,"live_add"),atol=c["qa"]["atol"],rtol=c["qa"]["relative_l2"])
 assert not np.allclose(correct,m.topological_patch_logits(co["trace"],d,rows,c,gen,"replacement"),atol=c["qa"]["atol"],rtol=c["qa"]["relative_l2"])

def test_torch_numpy_and_instruction_certificate():
 c=m.cfg();rows=m.panel_rows("development",c)[:8];q=m.qa_exact(rows,c,c["design"]["generator_seeds"][0],torch.device("cpu"));assert q["pass"] and q["identity_within_tolerance"]

def test_information_views_and_scope():
 c=m.cfg();assert c["methods"]["information_views"]["instruction_conditioned"]==["corrupt_trace","cell_config","query","offset"]
 assert c["scope"]["donor_free_discovery"] and not c["scope"]["k2_evaluated"]
 assert c["methods"]["expected_input_rank"]=={"corrupt":68,"instruction":801,"answer":96}

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
