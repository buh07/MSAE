from __future__ import annotations
import ast,base64,hashlib,json,sys
from pathlib import Path
from types import SimpleNamespace
import numpy as np
import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from transformers import AutoTokenizer

ROOT=Path(__file__).resolve().parents[1]; sys.path.insert(0,str(ROOT/'scripts'))
from atlas_context_local_v10 import (bootstrap_indices,capture_rows,complement_rows,gate4_energy_rows,projector,
    production_forward,sign_payload,verify_signed)
from build_atlas_context_local_v10 import reconstruct,token_span_index,exact_tokenize
from analyze_atlas_context_local_v10 import direction,load_source,source_summary
from run_atlas_context_local_v10 import exclusive_json
MODEL='EleutherAI/pythia-160m-deduped'; REV='582159a2dfe3e712a8d47ae83dec95ae3bde8e7e'

def test_mwt_surface_reconstruction_and_internal_exclusion():
    rows=[['1-2','del','_','_','_','_','_','_','_','_'],['1','de','de','ADP','_','_','0','root','_','_'],['2','el','el','DET','_','_','1','det','_','_'],['3','perro','perro','NOUN','_','Number=Sing','1','obj','_','SpaceAfter=No'],['4','.', '.', 'PUNCT','_','_','1','punct','_','_']]
    text,toks,mwts=reconstruct(rows)
    assert text=='del perro.' and [t.in_mwt for t in toks]==[True,True,False,False]
    assert toks[2].span==(4,9) and mwts==[(1,2,'del','_')]

def test_whitespace_aware_offset_is_fail_closed():
    tok=AutoTokenizer.from_pretrained(MODEL,revision=REV,local_files_only=True,use_fast=True)
    ids,offs=exact_tokenize(tok,' El')
    assert len(ids)==1 and token_span_index(' El',offs,(1,3))==0
    assert token_span_index(' El',offs,(1,2)) is None

def test_zero_energy_and_gate4_subfloor_contracts():
    x=np.zeros((2,8)); b=np.eye(8)[:,:2]
    assert np.array_equal(capture_rows(x,b),np.zeros(2)); assert np.array_equal(complement_rows(x,b),np.zeros(2))
    true=np.zeros((1,8)); true[0,0]=5e-7; unrelated=np.zeros_like(true)
    assert gate4_energy_rows(true,unrelated,b,1e-12)[0]==pytest.approx(.25)

def test_rank_projection_and_bootstrap_mapping():
    rng=np.random.default_rng(0); x=rng.normal(size=(32,20)); b,info=projector(x,16,1e-6)
    assert info['eligible'] and b is not None and b.shape==(20,16) and np.allclose(b.T@b,np.eye(16),atol=1e-8)
    u=np.array([[0,np.iinfo(np.uint64).max]],dtype=np.uint64); assert bootstrap_indices(u,7).tolist()==[[0,6]]

def test_production_forward_exact_masks_positions_and_no_cache():
    import torch
    class Fake:
        def __init__(self): self.calls=[]
        def __call__(self,**kw):
            self.calls.append(kw); shape=(*kw['input_ids'].shape,4); h=torch.zeros(shape,dtype=torch.float32)
            h[...,0]=kw['input_ids']; return SimpleNamespace(hidden_states=[h,h,h,h,h])
    row={'true_prefix_ids':[1,2],'unrelated_prefix_ids':[3,4],'target_segment_ids':[5,6,7,8],
         'substituted_target_segment_ids':[5,9,7,8],'target_sequence_index':3,'control_sequence_index':5}
    m=Fake(); t,c=production_forward(m,[row],device='cpu'); call=m.calls[0]
    assert t.shape==c.shape==(1,5,4); assert call['use_cache'] is False and call['output_hidden_states'] is True
    assert call['attention_mask'].tolist()==[[0,0,1,1,1,1],[1]*6,[0,0,1,1,1,1],[1]*6,[1]*6]
    assert call['position_ids'].tolist()==[list(range(6))]*5

def test_signature_algorithm_and_schema_are_immutable(tmp_path:Path):
    key=Ed25519PrivateKey.generate(); raw=key.public_key().public_bytes(serialization.Encoding.Raw,serialization.PublicFormat.Raw); fp=hashlib.sha256(raw).hexdigest()
    p=tmp_path/'signed.json'; sign_payload(p,{'schema_version':'x','value':1},key); assert verify_signed(p,fp)['value']==1
    env=json.loads(p.read_text()); env['signature']['algorithm']='NOT_ED25519'; p.write_text(json.dumps(env))
    with pytest.raises(RuntimeError): verify_signed(p,fp)

def test_exclusive_opening_rejects_second_writer(tmp_path:Path):
    p=tmp_path/'opened.json'; exclusive_json(p,{'a':1}); assert json.loads(p.read_text())=={'a':1}
    with pytest.raises(FileExistsError): exclusive_json(p,{'a':2})

def _maps(source:str,n:int,draws:int,rng:np.random.Generator)->dict[str,np.ndarray]:
    out={}
    for endpoint in ['raw_dtrue','raw_dcontext','raw_dlexical','raw_dunrelated','gate6']:
        out[f'within_{source}__{endpoint}__source']=rng.integers(0,np.iinfo(np.uint64).max,size=(draws,n),dtype=np.uint64)
    for fit,test in [('A','B'),('B','A')]:
        role='fit' if source==fit else 'test'
        for endpoint in ['gate1','gate2','gate3','gate4','gate5']:
            out[f'{fit}_to_{test}__{endpoint}__{role}']=rng.integers(0,np.iinfo(np.uint64).max,size=(draws,n),dtype=np.uint64)
    return out

def _analysis_cfg(draws:int,w:int,minimum:int=64)->dict:
    return {'model':{'width':w},'intervention':{'minimum_components':minimum},'analysis':{'rank':16,'rank_ratio_floor':1e-8,'representation_norm_floor':1e-12,
      'technical_equivalence_threshold':1e-5,'technical_max_failure_rate':.005,'scientific_small_delta_threshold':1e-4,'raw_effect_point_threshold':1e-4,
      'raw_effect_ci_threshold':1e-5,'haar_reference':16/w,'bootstrap_draws':draws,'quantiles':[.025,.5,.975],'minimum_finite_draws':max(2,draws-1),
      'context_capture_minimum':0.0,'assignment_margin':-1.0,'unrelated_energy_margin':-1.0,'lexical_complement_minimum':0.0}}

def test_projection_refits_and_minimum_population_suppression():
    rng=np.random.default_rng(7); draws=3; w=20
    def source(name,n):
        dc=rng.normal(size=(n,w)); dl=rng.normal(size=(n,w)); return {'context_idx':np.arange(n),'joint_idx':np.arange(n),'dcontext':dc,'dlexical':dl,
          'dtrue':dc+rng.normal(scale=.1,size=(n,w)),'dunrelated':rng.normal(scale=.1,size=(n,w)),'maps':_maps(name,n,draws,rng)}
    cfg=_analysis_cfg(draws,w)
    good=direction('A','B',{'A':source('A',64),'B':source('B',64)},cfg)
    assert good['projector_eligibility']['context']['eligible'] and good['intervals']['gate1_capture']['finite_draws']==draws
    small=direction('A','B',{'A':source('A',63),'B':source('B',63)},cfg)
    assert all(x['status']=='INELIGIBLE' for x in small['gates'].values())

def _write_cache_fixture(tmp_path:Path,all_nan:bool=False):
    prepared=tmp_path/'prepared'; cache=tmp_path/'cache'; prepared.mkdir(parents=True); cache.mkdir(parents=True); n=64; w=4; draws=3; source='S'; rng=np.random.default_rng(1)
    rows=[{'component_id':f'{i:064x}'} for i in range(n)]; (prepared/f'{source}.components.jsonl').write_text(''.join(json.dumps(x)+'\n' for x in rows))
    maps=_maps(source,n,draws,rng); keys=list(maps); np.save(prepared/f'{source}.bootstrap_maps.uint64.npy',np.stack([maps[k] for k in keys])); (prepared/f'{source}.bootstrap_map_keys.json').write_text(json.dumps({'keys':keys}))
    t=rng.normal(size=(n,5,w)).astype('float32'); c=rng.normal(size=(n,5,w)).astype('float32'); t[:,2]=t[:,0]
    if all_nan: t[:]=np.nan
    else: t[0,1,0]=np.nan
    np.savez(cache/f'{source}.representations.npz',target=t,control=c,component_ids=np.asarray([x['component_id'] for x in rows],dtype='U64'))
    return prepared,cache,source,_analysis_cfg(draws,w)

def test_inclusive_nonfinite_technical_failure_and_null_serialization(tmp_path:Path):
    prepared,cache,source,cfg=_write_cache_fixture(tmp_path); d=load_source(prepared,cache,source,cfg); summary=source_summary(source,d,cfg)
    assert summary['removals']['context_condition_nonfinite_union']==1 and summary['removals']['context_failure_union']==1
    assert summary['target_technical_failure_rate']==pytest.approx(1/64)
    prepared2,cache2,source2,cfg2=_write_cache_fixture(tmp_path/'all',all_nan=True); d2=load_source(prepared2,cache2,source2,cfg2); summary2=source_summary(source2,d2,cfg2)
    assert summary2['context_count']==0 and summary2['raw_dtrue']['point_median'] is None
    json.dumps(summary2,allow_nan=False)

def test_attempt14_has_no_training_reachability():
    forbidden_calls={'train','backward','step','zero_grad'}
    for name in ['atlas_context_local_v10.py','build_atlas_context_local_v10.py','analyze_atlas_context_local_v10.py','run_atlas_context_local_v10.py']:
        tree=ast.parse((ROOT/'scripts'/name).read_text())
        for node in ast.walk(tree):
            if isinstance(node,ast.Call) and isinstance(node.func,ast.Attribute): assert node.func.attr not in forbidden_calls,(name,node.lineno,node.func.attr)
        text=(ROOT/'scripts'/name).read_text().lower(); assert 'torch.optim' not in text and 'optimizer(' not in text and 'scheduler(' not in text

def test_attempt13_formal_wording_and_postflight_enforcement():
    plan=(ROOT/'PLAN_ATTEMPT14.md').read_text(); runner=(ROOT/'scripts/run_atlas_context_local_v10.py').read_text()
    assert 'Cross-corpus relational information was detectable, but strong recovery and relation-specific\n> isolation were not demonstrated.' in plan
    assert 'Attempt13 postflight immutability failure' in runner and '"attempt13_unchanged":True' in runner
