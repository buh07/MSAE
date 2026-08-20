from __future__ import annotations
import importlib.util,json,os,sys
from pathlib import Path
import numpy as np
import pytest
import torch

ROOT=Path(__file__).parents[1]
os.environ['MSAE_ROOT']=str(ROOT)
spec=importlib.util.spec_from_file_location('bridge',ROOT/'scripts/transformer_realistic_bridge_v1.py')
b=importlib.util.module_from_spec(spec);sys.modules['bridge']=b;spec.loader.exec_module(b)
CFG=json.loads((ROOT/'configs/transformer_realistic_bridge_v1/run.json').read_text())
MCFG=json.loads((ROOT/'configs/transformer_realistic_methods_v1/run.json').read_text())

def rows(seed=410): return b.make_rows('test',seed,b.REGIME_ORDER,24,8,16)

def test_rows_have_independent_support_and_balance():
    r=rows(); assert len(r)==1152
    for regime in b.REGIME_ORDER:
        q=[x for x in r if x['regime']==regime]
        assert len({x['block'] for x in q})==24
        assert all(sum(x['block']==block for x in q)==8 for block in range(24))
        assert all(sum(x['target']==target for x in q)==12 for target in range(16))

def test_transformer_realistic_invariants_and_oracle():
    r=rows(411)
    for regime in b.REGIME_ORDER:
        q=[x for x in r if x['regime']==regime]
        a=b.torch_forward(q,CFG,regime,torch.device('cpu'))
        c=b.numpy_forward(q,CFG,regime)
        qa=b.compare_qa(a,b.torch_forward(q,CFG,regime,torch.device('cpu')),c,CFG)
        assert qa['repeated_live_exact'] and qa['oracle_pass']
        # The registered insertion path reconstructs an independently computed factor hybrid.
        assert not np.shares_memory(a['logits_ground_truth_patch'],a['logits_hybrid'])
        assert np.allclose(a['logits_ground_truth_patch'],a['logits_hybrid'],atol=2e-5,rtol=2e-5)
        assert a['hybrid_nuisance_preserved'].all()
        assert np.array_equal(a['logits_state_skyline'],a['logits_clean'])

def test_mutating_registered_insertion_breaks_ground_truth_gate(monkeypatch):
    q=[x for x in rows(4111) if x['regime']=='realistic_noisy']
    cfg=json.loads(json.dumps(CFG)); cfg['bootstrap']['draws']=20
    original=b.insert_delta_torch
    def noop(keys,values,delta,indices,sign=1.0): return keys.clone(),values.clone()
    monkeypatch.setattr(b,'insert_delta_torch',noop)
    a=b.torch_forward(q,CFG,'realistic_noisy',torch.device('cpu'))
    _,summary=b.evaluate_regime(a,q,cfg,'mutation_insert','realistic_noisy')
    assert not summary['gate_decisions']['ground_truth_recovery']
    monkeypatch.setattr(b,'insert_delta_torch',original)

def test_all_nonpanel_regime_gates_pass_and_mutations_fail():
    r=rows(412)
    cfg=json.loads(json.dumps(CFG)); cfg['bootstrap']['draws']=20
    for regime in b.REGIME_ORDER:
        q=[x for x in r if x['regime']==regime]
        a=b.torch_forward(q,cfg,regime,torch.device('cpu'))
        _,summary=b.evaluate_regime(a,q,cfg,'test',regime)
        assert summary['all_gates_pass']
        bad={k:v.copy() for k,v in a.items()};bad['logits_routing_omitted']=bad['logits_hybrid'].copy()
        _,s=b.evaluate_regime(bad,q,cfg,'mutation',regime); assert not s['gate_decisions']['routing_necessity']
        for field in ('routing_only','private_only','shared_only','routing_private','routing_shared'):
            bad={k:v.copy() for k,v in a.items()};bad['logits_'+field]=bad['logits_hybrid'].copy()
            _,s=b.evaluate_regime(bad,q,cfg,'mutation_'+field,regime)
            assert not s['gate_decisions']['incomplete_gap']
        if regime in {'residual_bypass','layernorm','correlated_superposition','realistic_noisy'}:
            for field in ('attention_only','bypass_only'):
                bad={k:v.copy() for k,v in a.items()};bad['logits_'+field]=bad['logits_hybrid'].copy()
                _,s=b.evaluate_regime(bad,q,cfg,'mutation_'+field,regime)
                assert not s['gate_decisions']['incomplete_gap']

def test_soft_attention_is_neither_hard_nor_uniform():
    q=[x for x in rows(413) if x['regime']=='realistic_noisy']
    a=b.torch_forward(q,CFG,'realistic_noisy',torch.device('cpu'));w=a['weights_hybrid'];j=a['j']
    causal=w[np.arange(len(q)),j]
    assert np.all((causal>=.30)&(causal<=.90)); assert np.all(w>0)
    assert np.all(((w-np.eye(8,dtype=np.float32)[j]*w)>.01).sum(1)>=3)

def test_superposition_is_overcomplete_and_full_row_rank():
    m=b.model_matrices(CFG,'realistic_noisy')['value_mix']
    latent=CFG['model']['private_dim']+CFG['model']['shared_dim']+CFG['model']['value_nuisance_dim']
    assert latent>m.shape[0] and np.linalg.matrix_rank(m)==m.shape[0]

def test_zero_method_delta_is_retained_as_method_failure():
    q=[x for x in rows(414) if x['regime']=='realistic_noisy']
    z=b.MethodModel('zero','zero','matrix',torch.zeros(64,64))
    cfg=json.loads(json.dumps(MCFG)); cfg['bootstrap']['draws']=20
    records,summary=b.score_methods(q,[z],CFG,cfg,'development',torch.device('cpu'))
    assert len(records)==2*len(q)
    assert summary['methods']['zero']['technical_valid']
    assert summary['methods']['zero']['native']['metrics']['recovery']['point']==0.0
    assert not summary['methods']['zero']['matched']['matched_complete']
    assert not summary['methods']['zero']['matched']['all_gates_pass']
    assert not summary['family_pass_every_seed']['zero']

def test_registered_incomplete_method_controls_are_complete():
    names={m.name for m in b.base_method_models()}
    assert names=={'ground_truth','incomplete_routing_only','incomplete_private_only',
        'incomplete_shared_only','incomplete_routing_private','incomplete_routing_shared',
        'incomplete_attention_only','incomplete_bypass_only'}

def test_methods_training_target_support_construction():
    pc=MCFG['panels']['train'];r=b.make_rows('methods_train_test',pc['seed'],('realistic_noisy',),pc['blocks'],pc['rows_per_block'],16)
    for target in range(16):
        q=[x for x in r if x['target']==target]
        assert len(q)==32 and len({x['block'] for x in q})==32

def test_v1_1_preservation_and_paper_bindings_pass():
    assert b.run_preservation_verify()['status']=='PASS'
    assert b.paper_verify()['status']=='PASS'

def test_candidate_preflight_does_not_need_scientific_payloads(monkeypatch,tmp_path):
    forbidden={str(ROOT/'data/transformer_realistic_bridge_v1_prepared'/x) for x in ('development.jsonl','confirmation.jsonl')}
    forbidden|={str(ROOT/'data/transformer_realistic_methods_v1_prepared'/x) for x in ('train.jsonl','development.jsonl','confirmation.jsonl')}
    attempted=[]
    original_stat,original_read_text,original_read_bytes,original_open=Path.stat,Path.read_text,Path.read_bytes,Path.open
    def deny(self,operation):
        if str(self) in forbidden:
            attempted.append((operation,str(self))); raise AssertionError('candidate review touched scientific payload')
    def guarded_stat(self,*args,**kwargs):
        deny(self,'stat')
        return original_stat(self,*args,**kwargs)
    def guarded_read_text(self,*args,**kwargs): deny(self,'read_text'); return original_read_text(self,*args,**kwargs)
    def guarded_read_bytes(self,*args,**kwargs): deny(self,'read_bytes'); return original_read_bytes(self,*args,**kwargs)
    def guarded_open(self,*args,**kwargs): deny(self,'open'); return original_open(self,*args,**kwargs)
    monkeypatch.setattr(Path,'stat',guarded_stat)
    monkeypatch.setattr(Path,'read_text',guarded_read_text)
    monkeypatch.setattr(Path,'read_bytes',guarded_read_bytes)
    monkeypatch.setattr(Path,'open',guarded_open)
    b.candidate_preflight()
    for kind in ('bridge','methods'):
        assert all('development.jsonl' not in x['path'] and 'confirmation.jsonl' not in x['path'] and 'train.jsonl' not in x['path'] for x in b.inventory(b.candidate_paths(kind)))
    assert attempted==[]

def test_scope_forbids_k2_and_natural_claims():
    assert not CFG['scope']['k2_evaluated'] and not CFG['scope']['natural_model_claim']
    assert not MCFG['scope']['k2_evaluated'] and not MCFG['scope']['natural_model_claim']

def test_bridge_stop_blocks_methods_without_panel_access_or_training(monkeypatch,tmp_path):
    bc=json.loads(json.dumps(CFG)); mc=json.loads(json.dumps(MCFG))
    bc['runtime']['output_root']=str(tmp_path/'bridge')
    mc['runtime']['output_root']=str(tmp_path/'methods')
    bridge_final=tmp_path/'bridge'/'final'/'result.json'; bridge_final.parent.mkdir(parents=True)
    bridge_final.write_text(json.dumps({'status':'DEVELOPMENT_BRIDGE_STOP'})+'\n')
    original=b.config
    monkeypatch.setattr(b,'config',lambda p: bc if p==b.BRIDGE_CONFIG else (mc if p==b.METHODS_CONFIG else original(p)))
    b.block_methods({'status':'DEVELOPMENT_BRIDGE_STOP'},'BRIDGE_DID_NOT_CONFIRM')
    blocked=json.loads((tmp_path/'methods'/'METHODS_BLOCKED.json').read_text())
    final=json.loads((tmp_path/'methods'/'final'/'result.json').read_text())
    assert blocked['train_payload_touched'] is False
    assert blocked['development_payload_touched'] is False
    assert blocked['confirmation_payload_touched'] is False
    assert blocked['training_performed'] is False and final['training_performed'] is False
    assert blocked['representation_methods_evaluated'] is False
    assert final['representation_methods_evaluated'] is False
    assert not (tmp_path/'methods'/'train').exists()
