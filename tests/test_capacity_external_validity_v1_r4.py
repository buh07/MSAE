from __future__ import annotations
import importlib.util,json,os,sys,tempfile,signal
from unittest import mock
from pathlib import Path
import numpy as np, torch
ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('cev1',ROOT/'scripts/capacity_external_validity_v1_r4.py');m=importlib.util.module_from_spec(spec);sys.modules['cev1']=m;assert spec.loader;spec.loader.exec_module(m)

def test_symbolic_basis_all_instances():
 c=m.cfg('capacity');assert all(m.capacity_basis_check(i,c)['pass'] for i in c['instances'])
def test_capacity_split_balance_and_ids():
 c=m.cfg('capacity')
 for stage in ('train','development','confirmation'):
  rows=m.make_capacity_rows(c['instances'][0],stage,c);assert len({x['row_id'] for x in rows})==len(rows)
  for key in ('target','contrast','sham'):assert len({sum(x[key]==v for x in rows) for v in range(16)})==1
def test_exact_ols_nonpanel():
 c=m.cfg('capacity');rows=m.make_capacity_rows(991,'smoke',c,8,16,992);a=m.capacity_arrays(rows,991,c);w=np.linalg.pinv(a['x'],rcond=1e-12)@a['delta'];assert np.max(np.abs(a['x']@w-a['delta']))<1e-8
def test_observed_input_not_exact_direction():
 c=m.cfg('capacity');rows=m.make_capacity_rows(991,'smoke',c,8,16,992);a=m.capacity_arrays(rows,991,c);assert m.direction_metrics(a['x'],a['delta'])['cosine']<.999
def test_external_factorized_routing_is_value_invariant():
 c=m.cfg('external');rows=m.external_rows('smoke',c,2,8,993);model=m.CopyTransformer(c,1,torch.device('cpu'));clean,q,_=m.rows_tensors(rows,torch.device('cpu'),'clean_values');cor,_,_=m.rows_tensors(rows,torch.device('cpu'),'corrupt_values');assert torch.equal(model(clean,q)['weights'],model(cor,q)['weights'])
def test_external_rows_are_disjoint_and_counterfactual():
 c=m.cfg('external');panels={s:m.external_rows(s,c) for s in ('train','development','confirmation')};assert not ({x['row_id'] for x in panels['development']}&{x['row_id'] for x in panels['confirmation']})
 for a in panels.values():
  assert all(x['clean_values'][x['query']]==x['target'] and x['corrupt_values'][x['query']]==x['contrast'] for x in a)
  for key,n in (('target',32),('contrast',32),('sham',32),('query',8)):assert len({sum(x[key]==v for x in a) for v in range(n)})==1
def test_launcher_render_defers_workdir_and_binds_uuid():
 x=m.launcher_render('GPU-TEST');actual=(ROOT/'scripts/launch_capacity_external_validity_v1_r4_tmux.sh').read_text();assert '$(readlink /proc/self/cwd)' in x;assert 'CUDA_VISIBLE_DEVICES="$GPU_UUID"' in x;assert 'export CUDA_VISIBLE_DEVICES="$chosen_uuid"' in actual;assert 'RUN_ROOT=\\$(readlink /proc/self/cwd)' in actual;assert 'timeout --signal=TERM --kill-after=30s 8h' in actual;assert 'tee -a' in actual
def test_both_locks_are_required_for_payload_creation():
 assert m.payload_creation_allowed(True,True);assert not m.payload_creation_allowed(True,False);assert not m.payload_creation_allowed(False,True)
def test_mutations_execute_real_checks():
 z=m.mutation_suite();assert z['status']=='PASS';assert all(z['checks'].values())
def test_signal_handler_writes_terminals_and_blocks_unopened_external():
 with tempfile.TemporaryDirectory() as td:
  root=Path(td);cp=root/'cp';ep=root/'ep';co=root/'co';eo=root/'eo'
  for p in (cp,ep,co,eo):p.mkdir()
  old=dict(m._ACTIVE_RUN);m._ACTIVE_RUN.clear();m._ACTIVE_RUN.update({'capacity_prov':cp,'external_prov':ep,'capacity_out':co,'external_out':eo})
  try:
   try:m.signal_terminal(signal.SIGTERM,None)
   except SystemExit:pass
   assert (cp/'events/998_TECHNICAL_SIGNAL_TERMINAL.json').is_file();assert json.loads((eo/'final/result.json').read_text())['status']=='BLOCKED_UNOPENED';assert not (ep/'events/021_ACCESS_MAY_HAVE_OCCURRED.json').exists()
  finally:m._ACTIVE_RUN.clear();m._ACTIVE_RUN.update(old)
def test_after_access_failure_writes_truthful_terminal():
 with tempfile.TemporaryDirectory() as td:
  root=Path(td);cp=root/'cp';ep=root/'ep';co=root/'co';eo=root/'eo'
  for p in (cp,ep,co,eo):p.mkdir()
  m.event(ep,21,'ACCESS_MAY_HAVE_OCCURRED');old=dict(m._ACTIVE_RUN);m._ACTIVE_RUN.clear();m._ACTIVE_RUN.update({'capacity_prov':cp,'external_prov':ep,'capacity_out':co,'external_out':eo})
  try:
   m.write_external_failure_terminal('forced');z=json.loads((eo/'final/result.json').read_text());assert z['status']=='TECHNICAL_FAILURE_AFTER_ACCESS';assert z['external_payload_accessed']=='MAY_HAVE_OCCURRED';assert (ep/'events/992_EXTERNAL_TECHNICAL_FAILURE_AFTER_ACCESS.json').is_file()
  finally:m._ACTIVE_RUN.clear();m._ACTIVE_RUN.update(old)
def test_run_pipeline_preflight_failure_writes_both_terminals():
 with tempfile.TemporaryDirectory() as td:
  root=Path(td);cc={'seed':1,'runtime':{'provenance_root':str(root/'cp'),'output_root':str(root/'co')}};ec={'runtime':{'provenance_root':str(root/'ep'),'output_root':str(root/'eo')}};old=dict(m._ACTIVE_RUN)
  with mock.patch.object(m,'cfg',side_effect=lambda kind:cc if kind=='capacity' else ec),mock.patch.object(m,'launch_preflight',side_effect=RuntimeError('forced preflight')),mock.patch.object(signal,'signal'):
   try:m.run_pipeline(0,'GPU-X','token',123,str(root/'lock'))
   except RuntimeError:pass
   else:raise AssertionError('forced preflight failure did not propagate')
  assert (root/'cp/events/999_TECHNICAL_TERMINAL.json').is_file();assert (root/'ep/events/999_TECHNICAL_TERMINAL.json').is_file();assert json.loads((root/'eo/final/result.json').read_text())['status']=='BLOCKED_UNOPENED';m._ACTIVE_RUN.clear();m._ACTIVE_RUN.update(old)
def test_paper_and_preservation_bindings():
 z=m.preservation_verify();assert z['status']=='PASS_NONPAYLOAD_MANIFEST_ONLY';assert not z['inventory_traversed'];assert m.paper_verify()['status']=='PASS'
def test_plan_declares_k2_closed():
 text=(ROOT/'PLAN_CAPACITY_EXTERNAL_VALIDITY_V1_R4.md').read_text();assert 'No K2 path exists' in text


def test_r3_config_and_source_parity():
 z=m.verify_parity();assert z['status']=='PASS';assert z['restore_paths_forbidden']
 with tempfile.TemporaryDirectory() as td:
  bad=Path(td)/'bad.py';bad.write_text((ROOT/'scripts/capacity_external_validity_v1_r4.py').read_text().replace("rcond=c['methods']['svd_rtol'])@Y.astype",'rcond=0.5)@Y.astype',1));old=m.SCRIPT;m.SCRIPT=bad
  try:
   try:m.verify_parity()
   except RuntimeError:pass
   else:raise AssertionError('fit_methods mutation passed parity')
  finally:m.SCRIPT=old

def test_v1_failure_preservation_and_access_facts():
 z=m.failure_preservation_verify();assert z['partial_checkpoints']==27;assert z['facts']['capacity_development_opened'];assert not z['facts']['capacity_confirmation_opened'];assert z['facts']['external_status']=='BLOCKED_UNOPENED'

def test_first_true_index_installed_torch_compatibility():
 assert m.first_true_index(torch.tensor([False,True,True],dtype=torch.bool))==1
 for bad in (torch.tensor([False,False],dtype=torch.bool),torch.tensor([[True]],dtype=torch.bool),torch.tensor([0,1])):
  try:m.first_true_index(bad)
  except ValueError:pass
  else:raise AssertionError('invalid mask accepted')

def test_real_target_mlp_jacobian_all_targets_cpu():
 c=m.cfg('capacity');rows=m.make_capacity_rows(98701,'smoke',c,16,16,98702);a=m.capacity_arrays(rows,98701,c);x=torch.tensor(a['x'],dtype=torch.float32);t=torch.tensor(a['target'],dtype=torch.long);model=m.TargetMLP(64,4,16,16,98703,torch.device('cpu'));seen=[];forward=model.forward
 def recording_forward(xv,tv):seen.extend(int(v) for v in tv.detach().cpu().tolist());return forward(xv,tv)
 model.forward=recording_forward;r=m.empirical_jacobian_ranks(model,x,t,16,torch.device('cpu'));assert r==[4]*16;assert set(seen)==set(range(16))

def test_capacity_stage_access_event_precedes_read_and_opened_follows():
 c={'instances':[1,2]};calls=[]
 with mock.patch.object(m,'event',side_effect=lambda _p,_i,state,**_kw:calls.append(state)),mock.patch.object(m,'open_rows',side_effect=lambda _k,stage,inst:calls.append(f'read:{stage}:{inst}') or []):
  m.open_capacity_stage(c,'confirmation',Path('/unused'),15,16)
 assert calls==['CAPACITY_CONFIRMATION_ACCESS_MAY_HAVE_OCCURRED','read:confirmation:1','read:confirmation:2','CAPACITY_CONFIRMATION_OPENED']

def test_recovery_forbids_v1_checkpoint_reuse():
 for kind in ('capacity','external'):
  c=m.cfg(kind);assert c['recovery']['payloads_preexisting'];assert c['recovery']['fresh_checkpoint_initialization'];assert not c['recovery']['v1_checkpoint_reuse']

def test_all_jsonl_guard_blocks_access_surfaces():
 p=Path('/tmp/forbidden.jsonl')
 with m.no_jsonl_access_guard():
  for fn in (lambda:p.read_text(),lambda:p.read_bytes(),lambda:p.stat(),lambda:p.open(),lambda:os.open(p,os.O_RDONLY),lambda:list(Path('/tmp').glob('*.jsonl')),lambda:os.scandir('/tmp/not-allowlisted'),lambda:os.listdir('/tmp')):
   try:fn()
   except AssertionError:pass
   else:raise AssertionError('JSONL access surface was not blocked')
