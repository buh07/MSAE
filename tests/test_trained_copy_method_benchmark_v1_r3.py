from __future__ import annotations

import importlib.util
import json
import signal
import sys
from pathlib import Path

import numpy as np
import torch

ROOT=Path(__file__).resolve().parents[1]
SPEC=importlib.util.spec_from_file_location('tcm_r3',ROOT/'scripts/trained_copy_method_benchmark_v1_r3.py')
assert SPEC and SPEC.loader
tcm=importlib.util.module_from_spec(SPEC);sys.modules['tcm_r3']=tcm;SPEC.loader.exec_module(tcm)

def test_config_contract():
 c=tcm.cfg();tcm.validate_config(c)
 assert c['scope']['k2_evaluated'] is False and c['scope']['copy_model_retraining'] is False
 assert tcm.method_table_hash(c)==tcm.hashlib.sha256(tcm.canon(c['methods'])).hexdigest()

def test_component_disjoint_panels():
 c=tcm.cfg();ps=tcm.panel_set(c);audit=tcm.panel_audit(ps,c)
 assert {k:len(v) for k,v in ps.items()}=={'fit':2048,'development':256,'confirmation':256}
 assert all(audit[s]['max_main_tuple_contribution']==1 for s in ('fit','development','confirmation'))
 assert all(audit[s]['max_sham_tuple_contribution']==1 for s in ('fit','development','confirmation'))
 assert audit['cross_r5']['row_id_overlap']==audit['cross_r5']['row_seed_overlap']==0
 assert all(audit[s]['offsets_used']==sorted(c['panels'][s]['offsets']) for s in ('fit','development','confirmation'))
 assert all(set(audit[s]['per_block_unique_main'].values())=={c['panels'][s]['rows_per_block']} for s in ('fit','development','confirmation'))
 for a,b in [('fit','development'),('fit','confirmation'),('development','confirmation')]:
  assert not ({(r['query'],r['target'],r['contrast']) for r in ps[a]}&{(r['query'],r['target'],r['contrast']) for r in ps[b]})
  assert not ({(r['query'],r['contrast'],r['sham']) for r in ps[a]}&{(r['query'],r['contrast'],r['sham']) for r in ps[b]})

def test_evaluation_counterbalance():
 from collections import Counter
 for rows in [tcm.panel_set(tcm.cfg())[x] for x in ('development','confirmation')]:
  assert set(Counter(r['target'] for r in rows).values())=={8}
  assert set(Counter(r['query'] for r in rows).values())=={32}
  assert set(Counter(r['contrast'] for r in rows).values())=={8}
  assert set(Counter((r['target'],r['query']) for r in rows).values())=={1}

def test_candidate_does_not_load_checkpoint(monkeypatch):
 monkeypatch.setattr(torch,'load',lambda *a,**k:(_ for _ in ()).throw(AssertionError('checkpoint load forbidden')))
 x=tcm.write_candidate('cpu',False)
 assert x['status']=='PASS' and x['scientific_panel_accessed'] is False and x['r5_checkpoint_loaded'] is False
 assert x['checks']['all_32_targets_jacobian_required']

def test_mutation_suite_detects_overlap():
 x=tcm.mutation_suite();assert x['status']=='PASS' and all(x['checks'].values())

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

def test_nonlinear_union_rank_is_controller_output_space():
 class Asymmetric(torch.nn.Module):
  def forward(self,x,target):
   use0=target[:,None]==0;y0=torch.where(use0,x[:,0:1],x[:,1:2]);return torch.cat([y0,torch.zeros_like(y0)],1)
 x=torch.tensor([[1.,2.],[3.,4.]]);targets=torch.tensor([0,1]);got=tcm.empirical_jacobian_diagnostics(Asymmetric(),x,targets,2,torch.device('cpu'))
 assert got['empirical_jacobian_ranks']==[1,1] and got['empirical_jacobian_union_rank']==1

def test_exact_and_identity_prediction_equal():
 c=tcm.cfg();rows=tcm.panel_set(c)['development'][:8];model=tcm.r5.CopyTransformer(c,12,torch.device('cpu')).eval();z=tcm.context(model,rows,torch.device('cpu'))
 a=tcm.predict(tcm.Method('e','e','exact',None),z,model);b=tcm.predict(tcm.Method('i','i','identity',None),z,model)
 assert torch.equal(a[0],b[0]) and torch.equal(a[1],b[1])

def test_zero_matched_is_structurally_inapplicable():
 c=tcm.cfg();rows=tcm.panel_set(c)['development'];model=tcm.r5.CopyTransformer(c,13,torch.device('cpu')).eval();z=tcm.context(model,rows,torch.device('cpu'));zero=np.zeros_like(z['delta'].detach().numpy());_,ok=tcm.r5.norm_match(zero,z['delta'].detach().numpy())
 assert not ok.any()

def _scoring_fixture():
 c=json.loads(json.dumps(tcm.cfg()));c['bootstrap']['draws']=100;rows=tcm.panel_set(c)['development'];n=len(rows);d=c['model']['width']
 class Model(torch.nn.Module):
  def __init__(self):
   super().__init__();self.readout=torch.nn.Linear(d,c['model']['vocab'],bias=False)
   with torch.no_grad():self.readout.weight.zero_();self.readout.weight[:,:c['model']['vocab']]=torch.eye(c['model']['vocab'])
 model=Model();t=torch.tensor([r['target'] for r in rows]);co=torch.tensor([r['contrast'] for r in rows]);sh=torch.tensor([r['sham'] for r in rows]);clean=torch.zeros(n,d);cor=torch.zeros(n,d);sham=torch.zeros(n,d);clean[torch.arange(n),t]=5;cor[torch.arange(n),co]=5;sham[torch.arange(n),sh]=5
 ln=lambda x:torch.nn.functional.layer_norm(x,(d,),eps=c['model']['layernorm_eps'])
 with torch.no_grad():z={'clean':clean,'corrupt':cor,'sham':sham,'delta':clean-cor,'sham_delta':sham-cor,'logits_clean':model.readout(ln(clean)),'logits_corrupt':model.readout(ln(cor)),'target':t,'contrast':co,'query':torch.tensor([r['query'] for r in rows])}
 return c,rows,model,z

def test_exact_identity_pass_all_gates_and_random_fails():
 c,rows,model,z=_scoring_fixture();exact=tcm.Method('exact_head_delta','exact_head_delta','exact',None)
 for p,ps in (tcm.predict(exact,z,model),tcm.predict(tcm.Method('identity_full64','identity_full64','identity',None),z,model)):
  got=tcm.score(exact,p,ps,z,rows,c,'development',model,'native');assert got['support_pass'] and got['all_gates_pass'] and all(got['gate_decisions'].values())
 q=torch.tensor(tcm.rng('negative-control-test').normal(size=(64,64)),dtype=torch.float32);q=torch.linalg.qr(q).Q[:,:4];proj=q@q.T
 bad=tcm.score(tcm.Method('random_rank4','random_rank4','matrix',proj),z['delta']@proj,z['sham_delta']@proj,z,rows,c,'development',model,'native')
 assert bad['support_pass'] and not bad['all_gates_pass'] and set(bad['metrics'])==set(c['gates'])

def test_actual_sham_swap_and_target_metadata_mutations_fail():
 c,rows,model,z=_scoring_fixture();m=tcm.Method('exact_head_delta','exact_head_delta','exact',None)
 swapped=tcm.score(m,z['sham_delta'],z['delta'],z,rows,c,'development',model,'native');assert swapped['support_pass'] and not swapped['all_gates_pass']
 wrong=dict(z);wrong['target']=torch.tensor([r['sham'] for r in rows]);wrong_target=tcm.score(m,z['delta'],z['sham_delta'],wrong,rows,c,'development',model,'native');assert not wrong_target['support_pass'] and not wrong_target['all_gates_pass']

def test_prediction_incomplete_is_scientific_failure_not_structural_na():
 c,rows,model,z=_scoring_fixture();m=tcm.Method('collapsed','collapsed','matrix',torch.zeros(64,64));got=tcm.score(m,torch.zeros_like(z['delta']),torch.zeros_like(z['sham_delta']),z,rows,c,'development',model,'matched','prediction_incomplete')
 assert got['matched_status']=='prediction_incomplete' and got['support_pass'] and not got['all_gates_pass']

def test_method_inventory_and_information_contracts_are_complete():
 c=tcm.cfg();names=tcm.expected_method_names(c)
 assert len(names)==66 and len(names)==len(set(names))
 assert c['methods']['information_contracts']['topk_sae_unpaired_selector']['selector_fit']==['unordered_ambient_states']
 assert c['methods']['information_contracts']['topk_sae_paired_selector']['selector_fit']==['paired_states']
 assert c['methods']['information_contracts']['topk_sae_paired_selector']['class']=='paired_donor_compression'

def test_confirmation_authorization_ignores_estimated_scientific_outcomes():
 assert tcm.confirmation_authorization(True,True,{'all_estimates_failed':True})
 assert tcm.confirmation_authorization(True,True,{'all_estimates_passed':True})
 assert not tcm.confirmation_authorization(False,True,{'favorable':True})
 assert not tcm.confirmation_authorization(True,False,{'favorable':True})

def test_confirmation_access_guard_blocks_exact_failure_but_not_estimated_failure():
 opened=[];opener=lambda:opened.append('opened') or ['rows']
 assert tcm.confirmation_open_if_authorized({'confirmation_authorized':False},opener) is None and opened==[]
 authorized=tcm.confirmation_authorization(True,True,{'estimated_methods_all_failed':True});assert tcm.confirmation_open_if_authorized({'confirmation_authorized':authorized},opener)==['rows'] and opened==['opened']

def test_review_parser_rejects_block_with_ship_substring_and_conflicts(tmp_path):
 p=tmp_path/'review.md';p.write_text('VERDICT: BLOCK\nmentions VERDICT: SHIP\nBOUND_SHA256: abc\n')
 for content in [p.read_text(),'VERDICT: SHIP\nVERDICT: BLOCK\nBOUND_SHA256: abc\n','VERDICT: SHIP\nBOUND_SHA256: wrong\n']:
  p.write_text(content)
  try:tcm.verify_ship_review(p,'abc')
  except RuntimeError:pass
  else:raise AssertionError('invalid review authorized')
 p.write_text('VERDICT: SHIP\nBOUND_SHA256: abc\n');tcm.verify_ship_review(p,'abc')

def test_checkpoint_drift_stops_before_torch_load(monkeypatch):
 c=tcm.cfg();monkeypatch.setattr(tcm,'validate_config',lambda _c:None);monkeypatch.setattr(tcm,'sha',lambda _p:'wrong');called=False
 def forbidden(*_a,**_k):
  nonlocal called;called=True;raise AssertionError('torch.load must remain unreachable')
 monkeypatch.setattr(torch,'load',forbidden)
 try:tcm.load_model(c,5101,torch.device('cpu'))
 except RuntimeError as e:assert 'checkpoint drift' in str(e)
 else:raise AssertionError('checkpoint drift accepted')
 assert not called

def test_gpu_visibility_mismatch_fails_before_cuda(monkeypatch,tmp_path):
 monkeypatch.setenv('CUDA_VISIBLE_DEVICES','wrong');lock=tmp_path/'msae_trained_copy_methods_v1_r3_expected.lockdir';lock.mkdir();(lock/'token').write_text('x')
 try:tcm.gpu_validate(0,'expected',1,str(lock),'x')
 except RuntimeError as e:assert 'visibility' in str(e)
 else:raise AssertionError('bad UUID visibility accepted')

def test_phase_specific_terminal_is_durable_and_single(monkeypatch,tmp_path):
 c=tcm.cfg();freeze=tmp_path/'FREEZE.json';freeze.write_text('{}')
 original=tcm.rp;monkeypatch.setattr(tcm,'rp',lambda _c,k:freeze if k=='freeze' else original(_c,k));state={'phase':'fit_opened','panel_accessed':True,'confirmation_opened':False,'terminal_written':False};prov=tmp_path/'prov';prov.mkdir();tcm.write_terminal(c,prov,state,'TECHNICAL_FAILURE_AFTER_ACCESS','forced timeout');x=json.loads((prov/'TERMINAL.json').read_text())
 assert x['panel_accessed'] is True and x['status']=='TECHNICAL_FAILURE_AFTER_ACCESS' and x['no_retry_authorized'] is True
 tcm.write_terminal(c,prov,state,'WRONG');assert json.loads((prov/'TERMINAL.json').read_text())['status']=='TECHNICAL_FAILURE_AFTER_ACCESS'

def test_signal_handler_writes_pre_and_post_access_terminals(monkeypatch,tmp_path):
 c=tcm.cfg();freeze=tmp_path/'FREEZE.json';freeze.write_text('{}');original=tcm.rp;monkeypatch.setattr(tcm,'rp',lambda _c,k:freeze if k=='freeze' else original(_c,k))
 for accessed,expected in [(False,'TECHNICAL_FAILURE_BEFORE_ACCESS'),(True,'TECHNICAL_FAILURE_AFTER_ACCESS')]:
  prov=tmp_path/f'prov-{accessed}';prov.mkdir();state={'phase':'forced','panel_accessed':accessed,'confirmation_opened':False,'terminal_written':False};handler=tcm.make_signal_handler(c,prov,state)
  try:handler(signal.SIGTERM,None)
  except SystemExit as e:assert e.code==128+signal.SIGTERM
  else:raise AssertionError('signal did not terminate')
  assert json.loads((prov/'TERMINAL.json').read_text())['status']==expected

def test_open_stage_marks_access_before_read_and_records_open(monkeypatch,tmp_path):
 rows=[{'row_id':'x'}];payload=tmp_path/'confirmation.jsonl';payload.write_text(json.dumps(rows[0])+'\n');freeze=tmp_path/'FREEZE.json';freeze.write_text(json.dumps({'payloads':[{'stage':'confirmation','path':payload.as_posix(),'sha256':tcm.sha(payload)}]}));prov=tmp_path/'prov';prov.mkdir();state={'panel_accessed':False,'phase':'before'};original=tcm.rp;monkeypatch.setattr(tcm,'rp',lambda _c,k:freeze if k=='freeze' else original(_c,k));monkeypatch.setattr(tcm,'ROOT',Path('/'))
 assert tcm.open_stage(tcm.cfg(),'confirmation',prov,16,state)==rows
 assert state['panel_accessed'] and state['confirmation_opened'] and (prov/'events/016_CONFIRMATION_ACCESS_MAY_HAVE_OCCURRED.json').is_file() and (prov/'events/017_CONFIRMATION_OPENED.json').is_file()

def test_no_scientific_namespace_exists_before_launch():
 c=tcm.cfg()
 for k in ('prepared_root','freeze','review_binding','output_root','provenance_root','launcher_log'):
  assert not tcm.rp(c,k).exists()
