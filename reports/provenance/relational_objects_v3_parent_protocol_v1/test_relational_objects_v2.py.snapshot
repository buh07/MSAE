from __future__ import annotations
import ast
import json
from pathlib import Path
import sys
import numpy as np
import torch

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from analyze_relational_objects_v2 import _coarse, _component_weights, _fit_classifier, _interval, _signed_hash, _weighted_auc
from build_relational_objects_v2 import morph_signature
from relational_objects_v2 import load_json
from run_relational_objects_v2 import _effects, _pool_objects, synthetic_smoke


def test_signed_hash_is_deterministic_signed_and_fixed_width():
    a=_signed_hash(['a','b','a'],32,7); b=_signed_hash(['a','b','a'],32,7)
    assert a.shape==(32,) and np.array_equal(a,b)
    assert np.count_nonzero(a)<=2 and np.abs(a).sum()==3


def test_morphology_matching_and_nuisance_encoding_distinguish_values():
    config=load_json(ROOT/'configs/relational_objects_v2/run.json'); keys=config['matching']['morph_keys']; vocabulary=config['matching']['morph_value_vocabulary']
    assert morph_signature('Case=Nom|Number=Sing',keys,vocabulary)!=morph_signature('Case=Acc|Number=Sing',keys,vocabulary)
    base={'child_feats':'Case=Nom|Number=Sing','head_feats':'_','child_is_punct':False,'head_is_punct':False}
    changed={**base,'child_feats':'Case=Acc|Number=Sing'}
    assert not np.array_equal(_coarse(base,keys,vocabulary),_coarse(changed,keys,vocabulary))


def test_component_weights_give_each_component_total_one():
    components=np.asarray(['a','a','a','b'])
    weights=_component_weights(components)
    assert np.isclose(weights[components=='a'].sum(),1)
    assert np.isclose(weights[components=='b'].sum(),1)
    resampled=_component_weights(components,{'a':2,'b':0})
    assert np.isclose(resampled[components=='a'].sum(),2) and resampled[components=='b'].sum()==0


def test_interval_requires_exactly_500_finite_draws():
    assert _interval(np.arange(500,dtype=float),.025,'linear')['eligible']
    assert not _interval(np.arange(499,dtype=float),.025,'linear')['eligible']
    values=np.arange(500,dtype=float); values[7]=np.nan
    assert not _interval(values,.025,'linear')['eligible']


def test_weighted_ridge_smoke_separates_balanced_component_rows():
    config=load_json(ROOT/'configs/relational_objects_v2/run.json')
    rng=np.random.default_rng(3); y=np.tile([0,1],20); X=rng.normal(size=(40,5)); X[:,0]+=3*y
    components=np.asarray([f'c{i}' for i in range(20) for _ in range(2)])
    weights=_component_weights(components)
    scaler,model=_fit_classifier(X,y,weights,10,config)
    score=model.decision_function(scaler.transform(X))
    assert _weighted_auc(y,score,weights)>.95


def test_intervention_matches_explicit_redistribution_and_rejects_one_bad_head():
    torch.manual_seed(4)
    p=torch.softmax(torch.randn(12,9),-1); v=torch.randn(12,9,64); w=torch.randn(768,768)
    result=_effects(p,v,[1,2],w,1e-6)
    assert result['eligible'] and result['e_local']>0 and result['e_abs']>0
    mass=p[:,[1,2]].sum(-1); p2=p.clone(); p2[:,[1,2]]=0; p2=p2/(1-mass)[:,None]
    old=(p[:,:,None]*v).sum(1); new=(p2[:,:,None]*v).sum(1)
    explicit=torch.nn.functional.linear((new-old).reshape(1,-1),w,bias=None).square().mean().sqrt().item()
    assert np.isclose(result['e_abs'],explicit,rtol=1e-5,atol=1e-6)
    bad=p.clone(); bad[5]=0; bad[5,1]=1e-6; bad[5,0]=1-1e-6
    assert not _effects(bad,v,[1],w,1e-6)['eligible']
    try: _effects(p,v,[2,1],w,1e-6)
    except ValueError: pass
    else: raise AssertionError('unordered intervention keys were accepted')


def test_relational_object_tensor_axes_match_literal_reference():
    torch.manual_seed(8)
    logits=torch.randn(12,6,6); probabilities=torch.softmax(logits.masked_fill(~torch.tril(torch.ones(6,6,dtype=torch.bool))[None],-torch.inf),-1)
    values=torch.randn(12,6,64); residual=torch.randn(6,768)
    pooled=_pool_objects(logits,probabilities,values,residual,4,[1,2],[0,1],[3,4])
    assert pooled['residual_concat'].shape==(1536,) and torch.equal(pooled['residual_concat'][:768],residual[[0,1]].mean(0))
    assert torch.equal(pooled['residual_difference'],residual[[3,4]].mean(0)-residual[[0,1]].mean(0))
    assert torch.equal(pooled['qk'],(logits[:,4,1]+logits[:,4,2])/2)
    assert torch.equal(pooled['mass'],probabilities[:,4,[1,2]].sum(-1))
    manual=torch.stack([sum(probabilities[h,4,k]*values[h,k] for k in (1,2)) for h in range(12)]).reshape(-1)
    assert torch.allclose(pooled['transport'],manual)


def test_cpu_synthetic_smoke_loads_no_neural_model():
    config=load_json(ROOT/'configs/relational_objects_v2/run.json')
    assert synthetic_smoke(config)['status']=='PASS'


def test_config_and_scripts_forbid_neural_training_and_fresh_science():
    config=json.loads((ROOT/'configs/relational_objects_v2/run.json').read_text())
    assert config['exploratory'] is True
    assert all(value is False for value in config['permissions'].values())
    assert set(config['sources'])=={'ENGLISH_EWT','LATVIAN_LVTB'}
    for name in ('run_relational_objects_v2.py','analyze_relational_objects_v2.py'):
        tree=ast.parse((ROOT/'scripts'/name).read_text())
        calls=[]
        for node in ast.walk(tree):
            if isinstance(node,ast.Call):
                f=node.func
                calls.append(f.attr if isinstance(f,ast.Attribute) else f.id if isinstance(f,ast.Name) else '')
        assert 'backward' not in calls and 'step' not in calls and 'save' not in calls


def test_prepared_pair_rows_are_balanced_document_disjoint_and_no_reuse():
    root=ROOT/'data/relational_objects_v2_opened_development2/prepared'
    if not (root/'manifest.json').exists(): return
    for source in ('ENGLISH_EWT','LATVIAN_LVTB'):
        examples=[json.loads(x) for x in (root/source/'examples.jsonl').read_text().splitlines()]
        pairs=[json.loads(x) for x in (root/source/'pairs.jsonl').read_text().splitlines()]
        seen=set()
        for pair in pairs:
            edge,nonedge=examples[pair['edge_index']],examples[pair['nonedge_index']]
            assert edge['label']==1 and nonedge['label']==0
            assert edge['document_id']!=nonedge['document_id']
            assert pair['edge_index'] not in seen and pair['nonedge_index'] not in seen
            seen.update((pair['edge_index'],pair['nonedge_index']))
        assert seen==set(range(len(examples)))
