import importlib.util
import json
import os
import signal
import subprocess
import time
from pathlib import Path

import numpy as np
import pytest
import torch

ROOT=Path(__file__).resolve().parents[1]
SPEC=importlib.util.spec_from_file_location('constructed_copy',ROOT/'scripts/constructed_copy_circuit_v1_1.py')
assert SPEC and SPEC.loader
M=importlib.util.module_from_spec(SPEC); SPEC.loader.exec_module(M)
CFG=M.config(ROOT/'configs/constructed_copy_circuit_v1_1/run.json')


def calibration_rows():
    rows=M.panel_rows(CFG,'calibration'); M.validate_rows(CFG,rows,'calibration'); return rows


def test_locked_panel_metadata_records_fresh_disjoint_construction():
    prepared=json.loads((ROOT/CFG['runtime']['prepared_root']/'PREPARED.json').read_text())
    protocol=json.loads((ROOT/CFG['runtime']['protocol_lock']).read_text())
    assert prepared['development']['rows']==prepared['confirmation']['rows']==256
    assert prepared['prompt_overlap']==0
    assert CFG['panels']['development_seed']!=CFG['panels']['confirmation_seed']
    assert CFG['panels']['development_key_range'][1] <= CFG['panels']['confirmation_key_range'][0]
    assert CFG['panels']['development_value_range'][1] <= CFG['panels']['confirmation_value_range'][0]
    locked={x['path']:x['sha256'] for x in protocol['items']}
    for stage in ('development','confirmation'):
        path=f"data/constructed_copy_circuit_v1_1_prepared/{stage}.jsonl"
        assert locked[path]==prepared[stage]['sha256']


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
    for suffix in ('circuit','sham_patch','control_patch','source_ablate','control_ablate'):
        assert np.array_equal(out[f'attention_{suffix}'],out['attention'])
        assert np.array_equal(out[f'pre_scores_{suffix}'],out['pre_scores'])


def test_routing_is_derived_from_query_and_rejects_key_channel_corruption():
    rows=M.panel_rows(CFG,'smoke',smoke=True)
    bad=[dict(r) for r in rows]; bad[0]=dict(bad[0]); bad[0]['query_token']=0
    with pytest.raises(RuntimeError,match='unique route violation'):
        M.torch_forward(bad,CFG,torch.device('cpu'))
    with pytest.raises(RuntimeError,match='unique route violation'):
        M.numpy_oracle(bad,CFG)


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
    source=(ROOT/'scripts/constructed_copy_circuit_v1_1.py').read_text()
    assert 'torch.optim' not in source and '.backward(' not in source
    assert 'transformers' not in source and 'datasets' not in source and 'tokenizer' not in source.lower()
    assert M.SCOPE['representation_methods_evaluated'] is False
    assert M.SCOPE['training_performed'] is False and M.SCOPE['natural_prompt_assay'] is False
    assert CFG['model']['learned_parameters']==0


def test_lifecycle_registers_irreversible_authorization_before_payload_access():
    source=(ROOT/'scripts/constructed_copy_circuit_v1_1.py').read_text()
    before=source.index('auth_event(events,2,"ACCESS_MAY_HAVE_OCCURRED"')
    access=source.index('payload.stat().st_size')
    assert before < access
    for state in ['INITIALIZED','REFERENCE_1_COMPLETE','REFERENCE_2_COMPLETE','ORACLE_AND_REFERENCES_COMPARED','WORKER_COMPLETE_PENDING_VALIDATION','CLOSED_TECHNICAL_INVALID']:
        assert state in source
    assert not M.authorization_access_may_have_occurred([{'state':'PRECHECK_JOURNALED'},{'state':'PHASE1_PASS_NO_ACCESS'}])
    assert M.authorization_access_may_have_occurred([{'state':'PHASE1_PASS_NO_ACCESS'},{'state':'ACCESS_MAY_HAVE_OCCURRED'}])
    dev_before=source.index('development_auth_event(events,2,"ACCESS_MAY_HAVE_OCCURRED"')
    dev_access=source.index('payload=ROOT/cfg["runtime"]["prepared_root"]/"development.jsonl"; size=payload.stat().st_size')
    assert dev_before < dev_access


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
    comp={'schema_version':'constructed_copy_circuit_v1_1_reference_comparison','status':'PASS','bitwise':True,'fields':1,'reference_1_sha256':M.sha(q/'reference_1.npz'),'reference_2_sha256':M.sha(q/'reference_2.npz'),**M.SCOPE}
    (q/'REFERENCE_COMPARISON.json').write_text(json.dumps(comp))
    assert M.validate_reference_bundle(q,row_path,'development')['bitwise']
    with (q/'reference_1.npz').open('ab') as f: f.write(b'tamper')
    with pytest.raises(RuntimeError,match='reference hash'):
        M.validate_reference_bundle(q,row_path,'development')


@pytest.mark.parametrize('panel',['development.jsonl','confirmation.jsonl'])
def test_prelaunch_preflight_does_not_touch_scientific_panels(monkeypatch,panel):
    forbidden=str((ROOT/CFG['runtime']['prepared_root']/panel).absolute())
    orig_file=Path.is_file; orig_stat=Path.stat; orig_read=Path.read_bytes; orig_text=Path.read_text
    def guard(path):
        if str(path.absolute())==forbidden: raise AssertionError('constructed confirmation accessed')
    def is_file(self): guard(self); return orig_file(self)
    def stat(self,*a,**k): guard(self); return orig_stat(self,*a,**k)
    def read_bytes(self): guard(self); return orig_read(self)
    def read_text(self,*a,**k): guard(self); return orig_text(self,*a,**k)
    monkeypatch.setattr(Path,'is_file',is_file); monkeypatch.setattr(Path,'stat',stat)
    monkeypatch.setattr(Path,'read_bytes',read_bytes); monkeypatch.setattr(Path,'read_text',read_text)
    M.candidate_preflight(ROOT/'configs/constructed_copy_circuit_v1_1/run.json')


@pytest.mark.parametrize('panel',['development.jsonl','confirmation.jsonl'])
def test_candidate_inventory_uses_locked_panel_metadata_only(monkeypatch,panel):
    forbidden=str((ROOT/CFG['runtime']['prepared_root']/panel).absolute()); original=Path.read_bytes
    def read_bytes(self):
        if str(self.absolute())==forbidden: raise AssertionError('scientific panel accessed')
        return original(self)
    monkeypatch.setattr(Path,'read_bytes',read_bytes)
    cfg=json.loads(json.dumps(CFG)); cfg['runtime']['candidate_review']='reports/adversarial/constructed_copy_circuit_v1_1_plan_review.md'
    inventory=M.candidate_inventory(ROOT/'configs/constructed_copy_circuit_v1_1/run.json',cfg)
    item=next(x for x in inventory if x['path'].endswith(panel))
    locked=next(x for x in json.loads((ROOT/CFG['runtime']['protocol_lock']).read_text())['items'] if x['path']==item['path'])
    assert item==locked


def test_atomic_json_is_create_once_and_fully_parseable(tmp_path):
    target=tmp_path/'record.json'; M.atomic_json(target,{'state':'COMPLETE','value':7})
    assert json.loads(target.read_text())=={'state':'COMPLETE','value':7}
    with pytest.raises(FileExistsError): M.atomic_json(target,{'state':'REPLACED'})
    assert json.loads(target.read_text())=={'state':'COMPLETE','value':7}


@pytest.mark.parametrize('launcher_signal',[signal.SIGTERM,signal.SIGKILL])
def test_launcher_signal_kills_guarded_child_before_post_signal_marker(tmp_path,launcher_signal):
    marker=tmp_path/'post_signal_marker'; guard=tmp_path/'guard'; env=dict(os.environ, SUPERVISOR_TEST_ROOT=str(guard))
    proc=subprocess.Popen([str(ROOT/'scripts/launch_constructed_copy_circuit_v1_1_tmux.sh'),'--supervisor-signal-smoke',str(marker)],cwd=ROOT,env=env)
    active=guard/'signal_smoke.active.json'
    deadline=time.time()+10
    while time.time()<deadline and not active.is_file():
        if proc.poll() is not None: pytest.fail(f'supervisor smoke exited early: {proc.returncode}')
        time.sleep(.02)
    assert active.is_file(); child_pid=json.loads(active.read_text())['child_pid']
    os.kill(proc.pid,launcher_signal); proc.wait(timeout=10)
    assert proc.returncode!=0 and not marker.exists()
    deadline=time.time()+5
    while time.time()<deadline:
        stat=Path(f'/proc/{child_pid}/stat')
        if not stat.exists() or stat.read_text().split()[2]=='Z': break
        time.sleep(.02)
    else: pytest.fail('guarded child survived launcher termination')
    time.sleep(.1); assert not marker.exists()
