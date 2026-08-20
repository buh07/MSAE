from __future__ import annotations
import importlib.util,json,sys,tempfile,signal
from pathlib import Path
import numpy as np, torch
ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('cev1',ROOT/'scripts/capacity_external_validity_v1.py');m=importlib.util.module_from_spec(spec);sys.modules['cev1']=m;assert spec.loader;spec.loader.exec_module(m)

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
 x=m.launcher_render('GPU-TEST');actual=(ROOT/'scripts/launch_capacity_external_validity_v1_tmux.sh').read_text();assert '$(readlink /proc/self/cwd)' in x;assert 'GPU-TEST' in x;assert 'CUDA_VISIBLE_DEVICES="$PHYSICAL_INDEX"' in x;assert 'RUN_ROOT=\\$(readlink /proc/self/cwd)' in actual;assert 'timeout --signal=TERM --kill-after=30s 8h' in actual;assert 'tee -a' in actual
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
def test_paper_and_preservation_bindings():
 assert m.preservation_verify()['status']=='PASS';assert m.paper_verify()['status']=='PASS'
def test_plan_declares_k2_closed():
 text=(ROOT/'PLAN_CAPACITY_EXTERNAL_VALIDITY_V1.md').read_text();assert 'Neither study evaluates or trains K2' in text
