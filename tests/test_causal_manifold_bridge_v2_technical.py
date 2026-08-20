from __future__ import annotations
import copy,importlib.util,json
from pathlib import Path
import numpy as np

ROOT=Path(__file__).resolve().parents[1]
SPEC=importlib.util.spec_from_file_location('bridge_v2',ROOT/'scripts/causal_manifold_bridge_v2_technical.py');assert SPEC and SPEC.loader
M=importlib.util.module_from_spec(SPEC);SPEC.loader.exec_module(M)

def test_panels_ids_seeds_and_labels_are_globally_distinct():
 c=M.cfg();p=M.panel_set(c);rows=p['qualification']+p['validation']
 assert len({r['row_id'] for r in rows})==len(rows)
 assert len({r['row_seed'] for r in rows})==len(rows)
 assert all(len({r['target'],r['contrast'],r['sham']})==3 for r in rows)
 sample=p['qualification'][:16]+p['validation'][:16]
 gen=c['design']['generator_seeds'][0]
 assert len({M.composite_key(r,c,gen) for r in sample})==len(sample)

def test_structural_parameter_and_effective_seeds_are_fresh_axes():
 c=M.cfg();old={10101,10102,10103,10104}
 for key in ('structural_seeds','parameter_seeds','effective_generator_seeds'):
  assert len(set(c['design'][key]))==4 and not (set(c['design'][key])&old)
 assert len({tuple(M.seed_tuple(c,g,M.panel_rows('qualification',c)[0],0,'isotropic')) for g in M.generators(c)})==4
 changed=copy.deepcopy(c);changed['design']['structural_seeds'][0]+=1
 assert M.graph_seed(changed,M.generators(c)[0])!=M.graph_seed(c,M.generators(c)[0])

def test_shared_isotropic_control_is_deterministic_norm_matched_and_orthogonal():
 c=M.cfg();r=M.panel_rows('qualification',c)[0];gen=c['design']['generator_seeds'][0]
 g=M.graph_seed(c,gen);cl=M.r2.trace_np([r],c,g,'clean');co=M.r2.trace_np([r],c,g,'corrupt');d=(cl['trace']-co['trace']).reshape(-1)
 a=M.one_control(c,gen,r,d,0,'isotropic');b=M.one_control(c,gen,r,d,0,'isotropic')
 assert np.array_equal(a,b)
 assert np.isclose(np.linalg.norm(a),np.linalg.norm(d),rtol=1e-6,atol=1e-7)
 assert abs(float(a@d))/(np.linalg.norm(a)*np.linalg.norm(d))<1e-6
 import hashlib
 assert hashlib.sha256(a.tobytes()).hexdigest()=='ef9ca3a8a0c30c3eb207c336c932de2d39eae6b9b8e7b1fd1d04f478aabc6ff7'

def test_bootstrap_is_deterministic_and_equal_block_weighted():
 c=M.cfg();v=np.array([0.,2.,10.]);blocks=np.array([0,0,1])
 got=M.interval(v,blocks,c,'qualification','registered-golden')
 assert got=={'point':5.5,'lower':0.0,'upper':10.0}

def test_authorization_is_outcome_independent_and_conjunctive():
 assert M.validation_authorized([True,True],True,{'estimated':'fail'})
 assert M.validation_authorized([True,True],True,{'estimated':'pass'})
 assert not M.validation_authorized([True,False],True,None)
 assert not M.validation_authorized([True],False,None)

def test_no_estimated_method_or_training_inventory():
 c=M.cfg();assert c['methods']['registered_method_names']==['exact_controller','identity_full640']
 assert not c['methods']['estimated_methods_present'] and not c['methods']['training_path_present']

def test_failure_terminal_is_one_shot_and_forensic(tmp_path,monkeypatch):
 monkeypatch.setattr(M,'ROOT',tmp_path);c={'runtime':{'provenance_root':'prov'}}
 M.write_failure_terminal(c,TimeoutError('deadline'))
 rec=json.loads((tmp_path/'prov/TERMINAL.json').read_text())
 assert rec['status']=='TECHNICAL_FAILURE' and rec['partial_artifacts']=='FORENSIC_ONLY_NOT_SCIENTIFIC'
 M.write_failure_terminal(c,RuntimeError('later'))
 assert json.loads((tmp_path/'prov/TERMINAL.json').read_text())['error']=='deadline'
