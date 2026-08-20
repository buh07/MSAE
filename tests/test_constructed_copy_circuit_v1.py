import importlib.util
import json
from pathlib import Path

import numpy as np
import pytest
import torch

ROOT=Path(__file__).resolve().parents[1]
SPEC=importlib.util.spec_from_file_location('constructed_copy',ROOT/'scripts/constructed_copy_circuit_v1.py')
assert SPEC and SPEC.loader
M=importlib.util.module_from_spec(SPEC); SPEC.loader.exec_module(M)
CFG=M.config(ROOT/'configs/constructed_copy_circuit_v1/run.json')


def calibration_rows():
    rows=M.panel_rows(CFG,'calibration'); M.validate_rows(CFG,rows,'calibration'); return rows


def test_generated_panels_are_role_disjoint_and_cross_stage_disjoint():
    dev=M.panel_rows(CFG,'development'); con=M.panel_rows(CFG,'confirmation')
    M.validate_rows(CFG,dev,'development'); M.validate_rows(CFG,con,'confirmation')
    assert {x for r in dev for x in r['keys']}.isdisjoint({x for r in con for x in r['keys']})
    assert {x for r in dev for x in r['clean_values']}.isdisjoint({x for r in con for x in r['clean_values']})
    for r in dev+con:
        j,k=r['query_pair_index'],r['control_pair_index']; assert j!=k
        assert sum(a!=b for a,b in zip(r['control_values'],r['corrupt_values']))==1
        assert r['control_values'][j]==r['corrupt_values'][j]


def test_torch_matches_independent_oracle_and_graph_is_complete():
    rows=M.panel_rows(CFG,'smoke',smoke=True)
    out=M.torch_forward(rows,CFG,torch.device('cpu')); oracle=M.numpy_oracle(rows,CFG)
    assert M.exact_compare(out,oracle)['pass']
    j=out['matched_index']
    assert np.all(out['attention'][np.arange(len(rows)),j]==1)
    assert np.count_nonzero(out['attention'])==len(rows)
    assert np.all(np.isneginf(out['pre_scores'][out['attention']==0]))
    assert np.array_equal(out['logits_circuit_clean'],out['logits_clean'])
    assert np.array_equal(out['logits_control'],out['logits_corrupt'])
    assert np.count_nonzero(out['logits_edge_ablate'])==0
    assert np.count_nonzero(out['logits_source_ablate'])==0
    assert np.array_equal(out['logits_control_ablate'],out['logits_clean'])
    assert np.all(out['patch_norm_ratio']==1) and np.all(out['ablation_norm_ratio']==1)
    assert out['predecessor_edges'].shape==(18,18)
    for pos in range(2,17,2): assert out['predecessor_edges'][pos,pos-1]==1
    assert np.count_nonzero(out['predecessor_edges'])==8
    assert np.array_equal(out['pair_keys'],out['predecessor_state_clean'][:,np.arange(2,17,2)])
    for name in ('sequence_clean_ids','sequence_corrupt_ids','sequence_sham_ids','sequence_control_ids'):
        assert np.all(out[name][:,0]==0)
    graph=json.loads((ROOT/CFG['runtime']['candidate_root']/'GRAPH_REGISTRY.json').read_text())
    assert graph['leading_sentinel_token_id']==0 and graph['padding_positions']==[]
    M.validate_graph_registry(CFG,graph)


def test_positive_control_passes_all_registered_gates():
    rows=calibration_rows(); out=M.numpy_oracle(rows,CFG)
    records,summary,qa=M.evaluate(out,rows,CFG,'development')
    assert len(records)==256 and summary['common_cohort_total']==256
    assert summary['all_gates_pass'] and all(summary['gate_decisions'].values())
    assert qa['registered_output_bypasses']==0 and qa['learned_parameters']==0
    assert summary['metrics']['circuit_recovery']['point']==pytest.approx(1)
    assert summary['metrics']['sham_specificity']['point']==pytest.approx(1)
    assert summary['metrics']['control_margin']['point']==pytest.approx(1)
    assert summary['metrics']['collateral_error']['point']==pytest.approx(0)


def test_degraded_nonspecific_control_collateral_and_norm_failures_are_rejected():
    rows=calibration_rows(); base=M.numpy_oracle(rows,CFG)
    def classify(change):
        x={k:v.copy() for k,v in base.items()}; change(x)
        try: return M.evaluate(x,rows,CFG,'development')[1]
        except (RuntimeError,FloatingPointError): return None
    s=classify(lambda a:a.__setitem__('logits_circuit_clean',.5*a['logits_clean']+.5*a['logits_corrupt']))
    assert s and not s['gate_decisions']['circuit_recovery']
    s=classify(lambda a:a.__setitem__('logits_circuit_sham',.9*a['logits_clean']+.1*a['logits_corrupt']))
    assert s and not s['gate_decisions']['sham_specificity']
    s=classify(lambda a:a.__setitem__('logits_control',.9*a['logits_clean']+.1*a['logits_corrupt']))
    assert s and not s['gate_decisions']['control_margin']
    def collateral(a): a['logits_circuit_clean'][:,0]+=4
    s=classify(collateral); assert s and (not s['gate_decisions']['full_vocab_recovery'] or not s['gate_decisions']['collateral_error'])
    assert classify(lambda a:a['patch_norm_ratio'].__setitem__(0,2)) is None
    assert classify(lambda a:a['ablation_norm_ratio'].__setitem__(0,2)) is None
    assert classify(lambda a:a['logits_circuit_clean'].__setitem__((0,0),np.nan)) is None


def test_bootstrap_is_deterministic_and_equal_block_weighted():
    values=np.arange(256,dtype=float); blocks=np.arange(256)%8
    a=M.interval(values,blocks,CFG,'development','circuit_recovery')
    b=M.interval(values,blocks,CFG,'development','circuit_recovery')
    assert a==b and a['draws']==2000
    assert a['point']==pytest.approx(np.mean([values[blocks==q].mean() for q in range(8)]))


def test_v2_preservation_verifier_never_accesses_sealed_payload(monkeypatch):
    rec=json.loads((ROOT/CFG['runtime']['v2_preservation']).read_text()); forbidden=str((ROOT/rec['forbidden_confirmation_path']).absolute())
    orig_file=Path.is_file; orig_stat=Path.stat; orig_read=Path.read_bytes; orig_text=Path.read_text
    def guard(path):
        if str(path.absolute())==forbidden: raise AssertionError('sealed v2 confirmation accessed')
    def is_file(self): guard(self); return orig_file(self)
    def stat(self,*a,**k): guard(self); return orig_stat(self,*a,**k)
    def read_bytes(self): guard(self); return orig_read(self)
    def read_text(self,*a,**k): guard(self); return orig_text(self,*a,**k)
    monkeypatch.setattr(Path,'is_file',is_file); monkeypatch.setattr(Path,'stat',stat)
    monkeypatch.setattr(Path,'read_bytes',read_bytes); monkeypatch.setattr(Path,'read_text',read_text)
    assert M.verify_v2_preservation(CFG)['confirmation_opened'] is False


def test_v2_preservation_rejects_freeze_metadata_mutation(monkeypatch):
    manifest=ROOT/CFG['runtime']['v2_preservation']; original=M.loadj
    def mutated(path):
        value=original(path)
        if Path(path)==manifest:
            value['freeze']['sha256']='0'*64
        return value
    monkeypatch.setattr(M,'loadj',mutated)
    with pytest.raises(RuntimeError,match='v2 freeze drift'):
        M.verify_v2_preservation(CFG)


def test_v2_preservation_rejects_self_consistent_required_file_omission(monkeypatch):
    manifest=ROOT/CFG['runtime']['v2_preservation']; original=M.loadj
    def mutated(path):
        value=original(path)
        if Path(path)==manifest:
            value['files']=[x for x in value['files'] if x['path']!='PLAN_CANONICAL_INDUCTION_TWO_TIER_V2.md']
            value['files_sha256']=M.hashlib.sha256(M.canon(value['files'])).hexdigest()
        return value
    monkeypatch.setattr(M,'loadj',mutated)
    with pytest.raises(RuntimeError,match='required-set drift'):
        M.verify_v2_preservation(CFG)


def test_scope_has_no_training_method_or_natural_prompt_execution_path():
    source=(ROOT/'scripts/constructed_copy_circuit_v1.py').read_text()
    assert 'torch.optim' not in source and '.backward(' not in source
    assert 'transformers' not in source and 'datasets' not in source and 'tokenizer' not in source.lower()
    assert M.SCOPE['representation_methods_evaluated'] is False
    assert M.SCOPE['training_performed'] is False and M.SCOPE['natural_prompt_assay'] is False
    assert CFG['model']['learned_parameters']==0


def test_lifecycle_registers_irreversible_authorization_before_payload_access():
    source=(ROOT/'scripts/constructed_copy_circuit_v1.py').read_text()
    before=source.index('auth_event(events,2,"ACCESS_MAY_HAVE_OCCURRED"')
    access=source.index('payload.stat().st_size')
    assert before < access
    for state in ['INITIALIZED','REFERENCE_1_COMPLETE','REFERENCE_2_COMPLETE','ORACLE_AND_REFERENCES_COMPARED','WORKER_COMPLETE_PENDING_VALIDATION','CLOSED_TECHNICAL_INVALID']:
        assert state in source
    assert not M.authorization_access_may_have_occurred([{'state':'PRECHECK_JOURNALED'},{'state':'PHASE1_PASS_NO_ACCESS'}])
    assert M.authorization_access_may_have_occurred([{'state':'PHASE1_PASS_NO_ACCESS'},{'state':'ACCESS_MAY_HAVE_OCCURRED'}])


@pytest.mark.parametrize(('states','artifact_valid','expected'),[
    (['PRECHECK_JOURNALED'],False,('SEAL_TECHNICAL_INVALID',False)),
    (['PRECHECK_JOURNALED','PHASE1_PASS_NO_ACCESS'],False,('SEAL_TECHNICAL_INVALID',False)),
    (['PRECHECK_JOURNALED','PHASE1_PASS_NO_ACCESS','ACCESS_MAY_HAVE_OCCURRED'],False,('SEAL_TECHNICAL_INVALID',True)),
    (['PRECHECK_JOURNALED','PHASE1_PASS_NO_ACCESS','ACCESS_MAY_HAVE_OCCURRED','CLOSED_AUTHORIZED'],False,('SEAL_TECHNICAL_INVALID',True)),
    (['PRECHECK_JOURNALED','PHASE1_PASS_NO_ACCESS','ACCESS_MAY_HAVE_OCCURRED','CLOSED_AUTHORIZED'],True,('NONE',True)),
    (['PRECHECK_JOURNALED','CLOSED_BLOCKED_NO_ACCESS'],False,('NONE',False)),
])
def test_authorization_reconciliation_is_conservative(states,artifact_valid,expected):
    records=[{'state':s,'payload_access_may_have_occurred':s in {'ACCESS_MAY_HAVE_OCCURRED','CLOSED_AUTHORIZED'}} for s in states]
    assert M.authorization_reconcile_decision(records,artifact_valid)==expected


@pytest.mark.parametrize('name',['patch_norm_ratio','ablation_norm_ratio'])
def test_norm_gate_boundaries_are_inclusive_only_inside(name):
    gate=CFG['gates'][name]; lo=gate['row_min']; hi=gate['row_max']
    assert not M.row_gate_pass(name,np.asarray([np.nextafter(lo,-np.inf)]),CFG)
    assert M.row_gate_pass(name,np.asarray([lo,(lo+hi)/2,hi]),CFG)
    assert not M.row_gate_pass(name,np.asarray([np.nextafter(hi,np.inf)]),CFG)


def test_reference_bundle_rejects_post_comparison_substitution(tmp_path):
    row_path=tmp_path/'rows.jsonl'; row_path.write_text('{}\n')
    q=tmp_path/'qa'; q.mkdir()
    for replicate in (1,2):
        np.savez_compressed(q/f'reference_{replicate}.npz',x=np.arange(4))
        (q/f'reference_{replicate}.json').write_text(json.dumps({'arrays_sha256':M.sha(q/f'reference_{replicate}.npz'),'oracle_exact':True,'stage':'development','replicate':replicate,'rows_sha256':M.sha(row_path),**M.SCOPE}))
    comp={'schema_version':'constructed_copy_circuit_v1_reference_comparison','status':'PASS','bitwise':True,'fields':1,'reference_1_sha256':M.sha(q/'reference_1.npz'),'reference_2_sha256':M.sha(q/'reference_2.npz'),**M.SCOPE}
    (q/'REFERENCE_COMPARISON.json').write_text(json.dumps(comp))
    assert M.validate_reference_bundle(q,row_path,'development')['bitwise']
    with (q/'reference_1.npz').open('ab') as f: f.write(b'tamper')
    with pytest.raises(RuntimeError,match='reference hash'):
        M.validate_reference_bundle(q,row_path,'development')


def test_prelaunch_preflight_does_not_touch_constructed_confirmation(monkeypatch):
    forbidden=str((ROOT/CFG['runtime']['prepared_root']/'confirmation.jsonl').absolute())
    orig_file=Path.is_file; orig_stat=Path.stat; orig_read=Path.read_bytes; orig_text=Path.read_text
    def guard(path):
        if str(path.absolute())==forbidden: raise AssertionError('constructed confirmation accessed')
    def is_file(self): guard(self); return orig_file(self)
    def stat(self,*a,**k): guard(self); return orig_stat(self,*a,**k)
    def read_bytes(self): guard(self); return orig_read(self)
    def read_text(self,*a,**k): guard(self); return orig_text(self,*a,**k)
    monkeypatch.setattr(Path,'is_file',is_file); monkeypatch.setattr(Path,'stat',stat)
    monkeypatch.setattr(Path,'read_bytes',read_bytes); monkeypatch.setattr(Path,'read_text',read_text)
    M.candidate_preflight(ROOT/'configs/constructed_copy_circuit_v1/run.json')
