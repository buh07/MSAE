from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import numpy as np
import torch

ROOT=Path(__file__).resolve().parents[1]
SPEC=importlib.util.spec_from_file_location('tcm',ROOT/'scripts/trained_copy_method_benchmark_v1.py')
assert SPEC and SPEC.loader
tcm=importlib.util.module_from_spec(SPEC);sys.modules['tcm']=tcm;SPEC.loader.exec_module(tcm)

def test_config_contract():
 c=tcm.cfg();tcm.validate_config(c)
 assert c['scope']['k2_evaluated'] is False and c['scope']['copy_model_retraining'] is False
 assert tcm.method_table_hash(c)==tcm.hashlib.sha256(tcm.canon(c['methods'])).hexdigest()

def test_component_disjoint_panels():
 c=tcm.cfg();ps=tcm.panel_set(c);audit=tcm.panel_audit(ps,c)
 assert {k:len(v) for k,v in ps.items()}=={'fit':2048,'development':192,'confirmation':192}
 assert all(audit[s]['max_main_tuple_contribution']==1 for s in audit)
 for a,b in [('fit','development'),('fit','confirmation'),('development','confirmation')]:
  assert not ({(r['query'],r['target'],r['contrast']) for r in ps[a]}&{(r['query'],r['target'],r['contrast']) for r in ps[b]})
  assert not ({(r['query'],r['contrast'],r['sham']) for r in ps[a]}&{(r['query'],r['contrast'],r['sham']) for r in ps[b]})

def test_evaluation_counterbalance():
 from collections import Counter
 for rows in [tcm.panel_set(tcm.cfg())[x] for x in ('development','confirmation')]:
  assert set(Counter(r['target'] for r in rows).values())=={6}
  assert set(Counter(r['query'] for r in rows).values())=={24}
  assert min(Counter(r['contrast'] for r in rows).values())>=5

def test_candidate_does_not_load_checkpoint(monkeypatch):
 monkeypatch.setattr(torch,'load',lambda *a,**k:(_ for _ in ()).throw(AssertionError('checkpoint load forbidden')))
 x=tcm.write_candidate('cpu',False)
 assert x['status']=='PASS' and x['scientific_panel_accessed'] is False and x['r5_checkpoint_loaded'] is False
 assert x['checks']['all_32_targets_jacobian_required']

def test_mutation_suite_detects_overlap():
 assert tcm.mutation_suite()['status']=='PASS'

def test_stable_top_tie_breaks_low_index():
 got=tcm.stable_top(torch.tensor([1.,2.,2.,0.]),2).cpu().tolist()
 assert got==[1,2]

def test_sae_shapes_and_sparse_budget():
 m=tcm.TopKSAE(64,256,16,7,torch.device('cpu'));x=torch.randn(5,64);z=m.encode(x)
 assert z.shape==(5,256) and torch.all((z!=0).sum(1)<=16) and m.decode(z).shape==x.shape

def test_all_target_jacobians_are_reported():
 mdl=tcm.r5.TargetMLP(64,4,32,128,9,torch.device('cpu'));x=torch.randn(32,64);targets=torch.arange(32)
 ranks=tcm.r5.empirical_jacobian_ranks(mdl,x,targets,32,torch.device('cpu'))
 assert len(ranks)==32 and all(0<=r<=4 for r in ranks)

def test_exact_and_identity_prediction_equal():
 c=tcm.cfg();rows=tcm.panel_set(c)['development'][:8];model=tcm.r5.CopyTransformer(c,12,torch.device('cpu')).eval();z=tcm.context(model,rows,torch.device('cpu'))
 a=tcm.predict(tcm.Method('e','e','exact',None),z,model);b=tcm.predict(tcm.Method('i','i','identity',None),z,model)
 assert torch.equal(a[0],b[0]) and torch.equal(a[1],b[1])

def test_zero_matched_is_structurally_inapplicable():
 c=tcm.cfg();rows=tcm.panel_set(c)['development'];model=tcm.r5.CopyTransformer(c,13,torch.device('cpu')).eval();z=tcm.context(model,rows,torch.device('cpu'));zero=np.zeros_like(z['delta'].detach().numpy());_,ok=tcm.r5.norm_match(zero,z['delta'].detach().numpy())
 assert not ok.any()

def test_no_scientific_namespace_exists_before_launch():
 c=tcm.cfg()
 for k in ('prepared_root','freeze','review_binding','output_root','provenance_root','launcher_log'):
  assert not tcm.rp(c,k).exists()
