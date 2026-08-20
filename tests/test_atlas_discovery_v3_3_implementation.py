from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from analyze_atlas_discovery_v3_3 import (
    _projection_record,
    bootstrap_metrics,
    delta_for_pair,
    evaluate_relation_direction,
    fit_lemma_vocab,
    nuisance_rows,
    projection_capture_controls,
    projection_direction,
    raw_delta_covariance_spectrum,
    technical_ineligible_result,
    verified_jsonl,
)
from atlas_discovery_v3_3 import pooled_document_row_weights, terminal_outcome
from atlas_discovery_v3_3_analysis import CategoricalEncoder, choose_alpha, fit_ridge
from extract_atlas_discovery_v3_3 import _load_source_bundle, _qa_panel_units, _qa_stat, _recompute_qa_evidence


def test_frozen_qa_pair_order_is_preserved_exactly() -> None:
    split = json.loads((ROOT / "configs/atlas_discovery_v3_3/population_split_v3.json").read_text())
    prescore = json.loads((ROOT / "configs/atlas_discovery_v3_3/run_final_v3.json").read_text())
    parents = {
        "legacy": (
            json.loads((ROOT / "configs/atlas_discovery_v3/run.json").read_text()),
            json.loads((ROOT / "data/atlas_discovery_v3_1_attempt5/prepared/manifest.json").read_text()),
        ),
        "fresh": (
            json.loads((ROOT / "configs/atlas_discovery_v3_3/qa_compact_v3.json").read_text()),
            json.loads((ROOT / "data/atlas_discovery_v3_3_attempt7_qa_compact_v3/prepared/manifest.json").read_text()),
        ),
    }
    for source in ("EWT", "GUM"):
        for panel, (config, manifest) in parents.items():
            bundle = _load_source_bundle(config, manifest, source)
            pair_ids = split["sources"][source][f"{panel}_pair_ids"]
            _, _, rows, segments = _qa_panel_units(bundle, pair_ids, prescore, panel=panel)
            assert [row["pair_id"] for row in rows] == pair_ids
            assert all(segment["indices"] == list(range(segment["start"], segment["stop"])) for segment in segments)


@pytest.mark.parametrize("bad", [np.nan, np.inf, -np.inf])
def test_numerical_qa_rejects_nonfinite_values_and_recomputation(bad: float) -> None:
    reference=np.ones((4,2),dtype=np.float32)
    candidate=reference.copy();candidate[0,0]=bad
    assert _qa_stat(reference,candidate,atol=5e-7,rtol=5e-6)["status"]=="FAIL"
    rows=[
        {"panel":"legacy","family":"uniform_shift","roles":["target"]},
        {"panel":"legacy","family":"prefix_position_only","roles":["target"]},
        {"panel":"fresh","family":"uniform_shift","roles":["target"]},
        {"panel":"fresh","family":"prefix_position_only","roles":["target"]},
    ]
    arrays={"reference":reference,"repeat_1":reference.copy(),"repeat_2":reference.copy(),"candidate":candidate}
    spec={"atol_floor":5e-7,"atol_hard_ceiling":2e-5,"atol_multiplier":2.0,"rtol":5e-6}
    with pytest.raises(RuntimeError,match="non-finite"):
        _recompute_qa_evidence(arrays,rows,spec)


def test_bootstrap_missing_class_draws_are_invalid_not_zero_f1() -> None:
    rows = [{"component_id": "a"}, {"component_id": "b"}]
    labels = np.asarray(["a", "b"])
    report = bootstrap_metrics(
        rows, labels, labels.copy(), labels, ("a", "b"),
        direction="fixture", endpoint="missing-class", seed=9,
    )
    assert report["normalized_recovery"]["finite"] < 490


def test_fit_lemma_vocab_is_fit_source_only_main_metadata() -> None:
    def source(lemma: str):
        return SimpleNamespace(main={
            f"r{i}": {"labels": {"lemma": lemma}, "document_group": f"d{i}"}
            for i in range(30)
        })
    assert fit_lemma_vocab(source("fit_lemma")) == {"fit_lemma"}
    assert fit_lemma_vocab(source("heldout_lemma")) == {"heldout_lemma"}


def test_frozen_classifier_deltas_are_raw_targets_with_separate_controls() -> None:
    row_index = {name: index for index, name in enumerate(
        ("bare_pre", "bare_post", "gap_pre", "gap_post", "src_changed", "dst_changed", "src_control", "dst_control")
    )}
    activations = np.asarray([[0., 0.], [1., 0.], [0., 2.], [4., 0.], [0., 0.], [3., 0.], [0., 0.], [0., 5.]])
    data = SimpleNamespace(x=activations, row_index=row_index)
    relative = {"rows": {"bare": {"pre": "bare_pre", "post": "bare_post"}, "relative_gap": {"pre": "gap_pre", "post": "gap_post"}}}
    lexical = {"rows": {"source": {"changed": "src_changed", "control": "src_control"}, "target": {"changed": "dst_changed", "control": "dst_control"}}}
    delta, control = delta_for_pair(data, relative, "relative_gap")
    np.testing.assert_array_equal(delta, [3., 0.]); np.testing.assert_array_equal(control, [0., 2.])
    delta, control = delta_for_pair(data, lexical, "proper_noun_substitution")
    np.testing.assert_array_equal(delta, [3., 0.]); np.testing.assert_array_equal(control, [0., 5.])


def test_verified_analysis_child_rejects_digest_and_count_tampering(tmp_path: Path) -> None:
    path = tmp_path / "rows.jsonl"; path.write_text('{"x":1}\n')
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    assert verified_jsonl(path, digest, 1, "fixture")[0] == [{"x": 1}]
    with pytest.raises(RuntimeError, match="row-count drift"):
        verified_jsonl(path, digest, 2, "fixture")
    path.write_text('{"x":2}\n')
    with pytest.raises(RuntimeError, match="digest drift"):
        verified_jsonl(path, digest, 1, "fixture")


def test_shared_document_node_weights_multiply_donor_and_target() -> None:
    rows = [
        {"document_group": "A", "component_id": "A"},
        {"document_group": "A", "donor_document_group": "B", "component_id": "AB"},
    ]
    weights = pooled_document_row_weights(rows, {"A": 2, "B": 3})
    np.testing.assert_array_equal(weights, [2, 6])


def test_relation_transfer_does_not_filter_heldout_only_class() -> None:
    fit = SimpleNamespace(source="EWT", relations=[{"labels": {"deprel_coarse": "a"}}, {"labels": {"deprel_coarse": "b"}}])
    test = SimpleNamespace(source="GUM", relations=[{"labels": {"deprel_coarse": "a"}}, {"labels": {"deprel_coarse": "c"}}])
    result = evaluate_relation_direction(fit, test, "deprel_coarse", {})
    assert result["status"] == "ineligible"
    assert result["heldout_classes"] == ["a", "c"]


def test_projection_selectivity_uses_class_complete_draws() -> None:
    labels = np.asarray(["a", "b"] * 50)
    rows = [{"component_id": f"d{i}"} for i in range(len(labels))]
    wrong = np.where(labels == "a", "b", "a")
    record = _projection_record(
        rows, labels, labels, ("a", "b"), labels, labels, wrong,
        assigned_to_p=True, direction="fixture", endpoint="projection", seed=7, denominator_floor=1e-6,
    )
    assert record["eligible"] is True
    assert record["selectivity"] > 0
    assert record["selectivity_interval"]["finite"] >= 490


def test_production_nuisance_builder_explains_nuisance_only_signal() -> None:
    main = {}
    task_rows = []
    metadata = []
    for i in range(100):
        label = "a" if i % 2 else "b"; row_id = f"r{i}"
        labels = {
            "lemma": "shared", "token_identity": label, "upos_coarse": "VERBAL" if label == "a" else "NOMINAL",
            "punctuation": "no", "capitalization": "lower", "word_length": "1",
            "sentence_length": "5-8", "start_distance": "0", "relative_quartile": "Q1",
        }
        main[row_id] = {"labels": labels, "document_group": f"d{i}"}
        task_rows.append({"row_id": row_id, "label": label, "document_group": f"d{i}", "component_id": f"d{i}"})
    data = SimpleNamespace(main=main)
    built = nuisance_rows(data, "token_identity", task_rows, {"shared"})
    encoder = CategoricalEncoder.fit(built, ("upos_coarse",))
    nuisance = encoder.transform(built); representation = np.zeros((100, 3)); labels = np.asarray([row["label"] for row in task_rows]); folds = np.arange(100) % 5
    alpha_n, _ = choose_alpha(nuisance, labels, folds, ("a", "b"), (.1, 1., 10., 100.))
    combined = np.concatenate([representation, nuisance], axis=1)
    alpha_c, _ = choose_alpha(combined, labels, folds, ("a", "b"), (.1, 1., 10., 100.))
    np.testing.assert_array_equal(
        fit_ridge(nuisance, labels, ("a", "b"), alpha_n).predict(nuisance),
        fit_ridge(combined, labels, ("a", "b"), alpha_c).predict(combined),
    )


def test_candidate_ineligibility_forces_technical_terminal() -> None:
    assert terminal_outcome({"a": "ineligible", "b": "eligible_not_passed"}, technical_failure=False) == "technically_ineligible"


def test_projection_organization_assignments_are_exact_and_construct_weighted() -> None:
    from analyze_atlas_discovery_v3_3 import PROJECTION_CAPTURE_ROLES,PROJECTION_ORGANIZATION_GROUPS
    broad=PROJECTION_ORGANIZATION_GROUPS['broad_position_vs_lexical']
    assert set(broad)=={'sequential','syntax_child','lexical'}
    assert len(broad['sequential'])==2 and len(broad['syntax_child'])==3 and len(broad['lexical'])==1
    token_local=PROJECTION_ORGANIZATION_GROUPS['token_local_vs_context_dependent']
    assert {kind for _,kind,_ in token_local['relation']}=={'relation'}
    assert PROJECTION_CAPTURE_ROLES['token_local_vs_context_dependent']=={
        'relative_gap':'unassigned','true_context':'P','unrelated_context':'P',
        'proper_noun_substitution':'Q','relation':'P',
    }
    assert projection_capture_controls('token_local_vs_context_dependent','proper_noun_substitution')==(
        'true_context','unrelated_context','relation',
    )
    assert projection_capture_controls('token_local_vs_context_dependent','relative_gap')==()


def test_raw_delta_covariance_spectrum_is_sample_covariance() -> None:
    delta=np.asarray([[0.,0.],[2.,0.],[4.,0.]])
    report=raw_delta_covariance_spectrum(delta)
    assert report['normalization']=='sample_n_minus_1'
    np.testing.assert_allclose(report['eigenvalues_descending'],[4.,0.])


@pytest.mark.parametrize("organization",[
    'broad_position_vs_lexical',
    'sequential_context_vs_lexical_plus_relational_syntax',
    'token_local_vs_context_dependent',
])
def test_projection_direction_can_pass_each_exact_capture_contract(monkeypatch: pytest.MonkeyPatch, organization: str) -> None:
    import analyze_atlas_discovery_v3_3 as module
    width=16
    p=np.eye(width)[:,:8]
    monkeypatch.setattr(module,'make_projector',lambda blocks,rank,floor:(p,{'rank':8,'singular_values':[1.]*8}))
    monkeypatch.setattr(module,'delta_basis',lambda delta,rank,floor:(p[:,:1],{'rank':1,'singular_values':[1.]}))
    good=lambda *args,**kwargs:{'eligible':True,'assigned_recovery':1.0,'leakage':0.0,'selectivity':1.0,'selectivity_interval':{'finite':500,'lower':1.0,'upper':1.0},'_selectivity_draws':[1.0]*500}
    monkeypatch.setattr(module,'_projected_task_record',good)
    monkeypatch.setattr(module,'_projected_relation_record',good)
    x=np.zeros((4,width));x[1,0]=1.;x[3,0]=2.
    relations=[
        {'child_row_id':'c1','head_row_id':'h1','document_group':'d1','component_id':'d1'},
        {'child_row_id':'c2','head_row_id':'h2','document_group':'d2','component_id':'d2'},
    ]
    source=lambda name:SimpleNamespace(source=name,x=x,row_index={'c1':0,'h1':1,'c2':2,'h2':3},relations=relations)
    fit=source('EWT');test=source('GUM')
    tasks=('start_distance','relative_quartile','pair_distance','token_identity','head_signed_distance','dependency_depth','deprel_coarse')
    raw_models={task:SimpleNamespace(coef=np.vstack([np.ones(width),-np.ones(width)]),scale=np.ones(width)) for task in tasks}
    raw_internal={task:{} for task in tasks}
    task_results={task:{'eligible':True,'raw_signal_pass':True,'incremental_pass':True} for task in tasks}
    relation_pass=organization!='broad_position_vs_lexical'
    relation_results={task:{'eligible':True,'pass':relation_pass} for task in ('head_signed_distance','dependency_depth','deprel_coarse')}
    relation_internal={task:{} for task in relation_results}
    e0=np.eye(1,width,0)[0];e15=np.eye(1,width,15)[0]
    relative=e15 if organization=='token_local_vs_context_dependent' else e0
    deltas={'relative_gap':np.asarray([relative,relative]),'true_context':np.asarray([e0,e0]),'unrelated_context':np.asarray([e0,e0]),'proper_noun_substitution':np.asarray([e15,e15])}
    metadata={kind:[{'document_group':'d1','component_id':'d1'},{'document_group':'d2','component_id':'d2'}] for kind in deltas}
    atlas={'bases':{'relative_gap':p[:,:1],'true_context':p[:,:1],'unrelated_context':p[:,:1]},'deltas':deltas,'metadata':metadata}
    organization_blocks={
        'broad_position_vs_lexical':['sequential','syntax_child','relative_gap','context'],
        'sequential_context_vs_lexical_plus_relational_syntax':['sequential','relative_gap','context'],
        'token_local_vs_context_dependent':['sequential','context','relation'],
    }
    analysis={'organizations':{organization:organization_blocks[organization]},'projection_ranks':[8],'primary_rank':8,'minimum_usable_rank':8,'delta_basis_rank':1,'singular_floor':1e-8,'seed':3,'assigned_recovery_min':.65}
    result=projection_direction(fit,test,raw_models,raw_internal,atlas,atlas,relation_results,relation_internal,task_results,{'eligible':True,'pass':True},analysis)[organization]
    assert result['status']=='passed'
    assert result['capture_lcb_pass'] is True


def test_expected_analysis_failure_materializes_total_technical_result(tmp_path: Path) -> None:
    config=tmp_path/'scoring.json'
    config.write_text(json.dumps({'analysis':{'organizations':{'candidate':[]}},'prescore_config':{'sha256':'p'},'prepared_manifest_sha256':'m'}))
    result=technical_ineligible_result(config,RuntimeError('lineage drift'))
    assert result['status']=='TERMINAL_TECHNICALLY_INELIGIBLE'
    assert result['outcome']=='technically_ineligible'
    assert result['candidate_statuses']=={'candidate':'ineligible'}
    assert result['technical_failure_reasons']==[{'type':'RuntimeError','message':'lineage drift'}]


def test_planted_true_head_relation_beats_child_and_matched_sham() -> None:
    def make_source(name: str):
        activations=[];row_index={};main={};relations=[]
        for i in range(100):
            label='a' if i%2 else 'b';signal=1.0 if label=='a' else -1.0
            ids={role:f'{name}:{role}:{i}' for role in ('child','head','sham')}
            for role,value in [('child',[0.,0.]),('head',[signal,0.]),('sham',[0.,0.])]:
                row_index[ids[role]]=len(activations);activations.append(value)
            main[ids['child']]={'fold':i%5}
            relations.append({'child_row_id':ids['child'],'head_row_id':ids['head'],'sham_row_id':ids['sham'],'component_id':f'{name}:d{i}','labels':{'deprel_coarse':label}})
        return SimpleNamespace(source=name,x=np.asarray(activations),row_index=row_index,main=main,relations=relations)
    analysis={'alphas':(.1,1.,10.,100.),'ridge_device':'cpu','scale_floor':1e-8,'seed':7}
    result=evaluate_relation_direction(make_source('EWT'),make_source('GUM'),'deprel_coarse',analysis)
    assert result['eligible'] is True and result['pass'] is True
    assert result['true_minus_child']>0 and result['true_minus_sham_interval']['lower']>0
