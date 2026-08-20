from __future__ import annotations
import inspect,json
from pathlib import Path
import numpy as np
import pytest

import proxy_control_benchmark_v2 as p

ROOT=Path(__file__).resolve().parents[1]
CFG=json.loads((ROOT/'configs/proxy_control_benchmark_v2/run.json').read_text())


def test_controlled_support_templates_and_shams():
    rows=p.make_controlled_rows(CFG)
    assert len(rows)==2*3*(16+32)*4
    assert all(len({r['base_prompt'],r['cf_prompt'],r['sham_prompt']})==3 for r in rows)
    for source in CFG['panels']['controlled_sources']:
        for concept in CFG['panels']['concepts']:
            q=[r for r in rows if r['source']==source and r['concept']==concept]
            dev={r['template_family'] for r in q if r['split']=='development'}
            test={r['template_family'] for r in q if r['split']=='test'}
            assert not dev & test
            assert len({r['component_block'] for r in q if r['split']=='development'})==16
            assert len({r['component_block'] for r in q if r['split']=='test'})==32


def test_position_uses_same_token_multiset():
    rows=[r for r in p.make_controlled_rows(CFG) if r['concept']=='relative_position']
    for r in rows:
        assert sorted(r['base_prompt'].split())==sorted(r['cf_prompt'].split())==sorted(r['sham_prompt'].split())


def test_signed_specificity_aligns_negative_natural_effect():
    full=np.array([2.0,-2.0,1e-12]);patch=np.array([1.0,-1.0,1.0]);sham=np.zeros(3);eligible=np.array([True,True,False])
    got=p.signed_behavioral_specificity(patch,sham,full,eligible,1e-8)
    assert np.allclose(got[:2],[.5,.5])
    assert np.isnan(got[2])


def test_block_interval_uses_blocks_not_surface_rows():
    values=np.array([0.0]*100+[10.0]);blocks=['a']*100+['b']
    ci=p.block_interval(values,blocks,500,7)
    assert ci is not None
    assert 3.0 < ci[1] < 7.0


def test_synthetic_gate_positive_and_negative_controls():
    result=p.synthetic_metrics(CFG,seed=7)
    assert result['status']=='PASS'
    assert result['metrics']['ground_truth']['behavioral_specificity']>.9
    assert result['metrics']['behavior_gradient_oracle']['target_cka']>.9
    assert abs(result['metrics']['random_negative']['behavioral_specificity'])<.25


def test_v1_lineage_and_no_training_path():
    p.verify_imports(CFG,full=False,required=[ROOT/CFG['imported_v1']['root']/'shards/pythia160_layer1/k1_seed101.pt'])
    source=(ROOT/'scripts/proxy_control_benchmark_v2.py').read_text()
    assert 'train_decomposition(' not in source
    worker=inspect.getsource(p.worker)
    assert worker.index('wait_for_synthetic_gate') < worker.index('load_model_and_tokenizer')


def test_failed_gate_blocks_before_forward(tmp_path):
    cfg=json.loads(json.dumps(CFG));cfg['runtime']['output_root']=str((tmp_path/'run').relative_to(ROOT)) if str(tmp_path).startswith(str(ROOT)) else str(tmp_path/'run')
    root=Path(cfg['runtime']['output_root'])
    if not root.is_absolute(): root=ROOT/root
    syn=root/'synthetic';syn.mkdir(parents=True)
    p.exclusive_json(syn/'FAIL.json',{'status':'FAIL'})
    out=root/'shards/job';out.mkdir(parents=True)
    with pytest.raises(RuntimeError,match='synthetic gate failed'):
        p.wait_for_synthetic_gate(cfg,out,'freeze')
    assert (out/'BLOCKED_BY_SYNTHETIC_GATE.json').is_file()


def test_prepared_prescore_is_effect_blind_and_complete():
    root=ROOT/CFG['panels']['prepared_root'];rec=json.loads((root/'PRESCORE.json').read_text())
    assert rec['selection_firewall'].endswith('NO_MODEL_FORWARD_OR_EFFECT_FILTERING')
    assert rec['controlled_rows']==1152 and rec['natural_rows']>=30
    assert all(v['controlled_length_matched'] for v in rec['model_tokenizer_checks'].values())


def test_proxy_classes_are_separate():
    assert set(CFG['analysis']['proxy_classes']['learned']) != set(CFG['analysis']['proxy_classes']['linear'])
    assert 'reconstruction_quality' not in CFG['analysis']['proxy_classes']['linear']


def test_hierarchical_interval_uses_all_frozen_levels():
    pd=pytest.importorskip('pandas')
    rows=[]
    for model,offset in [('a',0.0),('b',2.0)]:
        for layer in [1,2]:
            for seed in [101,202]:
                for direction in [('C','D'),('D','C')]:
                    for block in range(3):
                        for surface in range(4):
                            rows.append({'model':model,'layer':layer,'seed':seed,
                                'assignment_source':direction[0],'evaluation_source':direction[1],
                                'component_block':f'{direction[1]}:{block}',
                                'template_family':f't{surface}','surface_rep':surface,
                                'score':offset+block})
    got=p.hierarchical_interval(pd.DataFrame(rows),'score',200,7)
    assert got['point']==pytest.approx(2.0)
    assert got['models']==2 and got['blocks']==6 and got['finite_draws']==200
    assert got['factors']==CFG['analysis']['hierarchical_bootstrap']['factors']
