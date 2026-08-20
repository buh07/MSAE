from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pytest

import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from msae_measurement_v2_run import (
    build_pair_population,
    cache_manifest,
    group_multiplicities,
    interval,
    parse_esl_files,
    split_esl,
    weighted_macro_f1,
    write_vector_cache,
)
from run_msae_measurement_v2 import _cached_noop_qa, _fit_ridge, _partial_residuals
from validate_msae_measurement_v2_terminal import validate_analysis_truth


class Encoding(dict):
    def __init__(self, ids: list[int], word_ids: list[int]):
        super().__init__(input_ids=ids)
        self._word_ids = word_ids

    def word_ids(self) -> list[int]:
        return self._word_ids


class WordTokenizer:
    def encode(self, word: str, add_special_tokens: bool = False) -> list[int]:
        del add_special_tokens
        return [sum(map(ord, word)) % 1000 + 1]

    def __call__(self, words: list[str], **kwargs: object) -> Encoding:
        del kwargs
        return Encoding([self.encode(word)[0] for word in words], list(range(len(words))))


def _record(group: str, order: int, propn: str, upos: str = "PROPN") -> dict[str, object]:
    return {
        "base_id": f"{group}-{order}", "source_record_id": f"{group}-{order}",
        "document_group": group, "source_order": order, "words": [propn, "runs"],
        "labels": {"upos": [upos, "VERB"]},
    }


def test_entity_pairs_are_disjoint_and_context_uses_unused_documents() -> None:
    records = []
    for index in range(16):
        upos = "PROPN" if index < 8 else "NOUN"
        records.extend((_record(f"g{index:02d}", 1, f"Name{index}", upos), _record(f"g{index:02d}", 3, f"Other{index}", upos)))
    population = build_pair_population("C2", records, WordTokenizer(), 128)
    entity_groups = [g for row in population.entity for g in (row["source_document_group"], row["donor_document_group"])]
    assert len(entity_groups) == len(set(entity_groups))
    assert all(sum(a != b for a, b in zip(row["source_input_ids"], row["target_input_ids"], strict=True)) == 1
               for row in population.entity)
    assert population.context
    assert not set(entity_groups) & {row["document_group"] for row in population.context}
    assert all(row["separator_token_id"] == 0 for row in population.context)
    assert all(row["source_order_gap"] == 2 for row in population.context)


def test_group_bootstrap_is_deterministic_and_fixed_size() -> None:
    groups = ["a", "b", "c", "d"]
    first = group_multiplicities(groups, role="C2", task="x", source="UD_X", draw=7, seed=20260802)
    second = group_multiplicities(list(reversed(groups)), role="C2", task="x", source="UD_X", draw=7, seed=20260802)
    assert first == second
    assert sum(first.values()) == 4


def test_weighted_macro_f1_keeps_missing_class_as_zero() -> None:
    y = np.asarray([0, 1, 2])
    pred = np.asarray([0, 0, 0])
    score = weighted_macro_f1(y, pred, np.ones(3), 3)
    assert score == pytest.approx((0.5 + 0.0 + 0.0) / 3)


def test_interval_uses_finite_values_only() -> None:
    row = interval([None, 1.0, 2.0, float("nan")])
    assert row["finite"] == 2
    assert row["lower"] == pytest.approx(1.025)
    assert row["upper"] == pytest.approx(1.975)


def test_vector_cache_rejects_tampering(tmp_path: Path) -> None:
    output = tmp_path / "cache"
    write_vector_cache(output, np.ones((3, 2), np.float32), ["a", "b", "c"], {"x": 1})
    assert cache_manifest(output)["shape"] == [3, 2]
    with (output / "values.float32.npy").open("ab") as handle:
        handle.write(b"x")
    with pytest.raises(RuntimeError, match="digest mismatch"):
        cache_manifest(output)


def test_esl_parser_requires_anchored_sentence_ids(tmp_path: Path) -> None:
    conllu = tmp_path / "x.conllu"
    conllu.write_text("# sent_id = bad\n# text = Hi\n1\tHi\t_\tINTJ\t_\t_\t0\troot\t_\t_\n\n")
    with pytest.raises(RuntimeError, match="malformed"):
        parse_esl_files([conllu], "UD_English-ESLSpok", "r")


def test_esl_parser_retains_repeated_utterance_text_in_distinct_transcripts(tmp_path: Path) -> None:
    conllu=tmp_path/"x.conllu"
    conllu.write_text(
        "# sent_id = file00001.txt_1\n# text = Hi\n1\tHi\t_\tINTJ\t_\t_\t0\troot\t_\t_\n\n"
        "# sent_id = file00002.txt_1\n# text = Hi\n1\tHi\t_\tINTJ\t_\t_\t0\troot\t_\t_\n\n",encoding="utf-8")
    rows=parse_esl_files([conllu],"UD_English-ESLSpok","r")
    assert len(rows)==2 and rows[0]["content_hash"]==rows[1]["content_hash"]


def test_partial_residuals_use_rank_basis_with_redundant_nuisance_columns() -> None:
    rng=np.random.default_rng(5);n=20
    selected=[{"activation_index":i} for i in range(n)]
    metadata={i:{"labels":{"upos_coarse":"PUNCT" if i%2 else "NOMINAL",
                           "punctuation":"punct" if i%2 else "nonpunct",
                           "word_length":"1" if i%3 else "2",
                           "token_identity_nuisance":"__NONRETAINED__" if i%4 else "the"}}
              for i in range(n)}
    levels={field:sorted({row["labels"][field] for row in metadata.values()})
            for field in ("upos_coarse","punctuation","word_length","token_identity_nuisance")}
    residual,status=_partial_residuals(rng.normal(size=(n,4)).astype(np.float32),selected,metadata,levels,128)
    assert residual is not None and status["status"]=="eligible"
    assert status["rank"]<status["columns"]
    assert np.allclose(residual.mean(0),0,atol=1e-6)


def test_cached_noop_is_bit_identical_and_zero_distance() -> None:
    array=np.arange(12,dtype=np.float32).reshape(3,4)
    result=_cached_noop_qa(array,[{"source_row_ids":["a","b"]}],{"a":0,"b":1,"c":2})
    assert result=={"status":"eligible","bit_identical":True,"distance":0.0,"checked":1}


def test_fit_ridge_accepts_compact_integer_label_arrays() -> None:
    x=np.asarray([[0.0,0.0],[0.0,1.0],[1.0,0.0],[1.0,1.0]],dtype=np.float32)
    labels=np.asarray([0,1,1,0],dtype=np.int32)
    result=_fit_ridge(x,labels,2,[0.1,1.0],x,labels,"cpu")
    weight,bias,alpha,grid=result
    assert weight.shape==(2,2) and bias.shape==(2,)
    assert alpha in {0.1,1.0} and set(grid)=={"0.1","1.0"}
    wide=_fit_ridge(x,labels.astype(np.int64),2,[0.1,1.0],x,labels.astype(np.int64),"cpu")
    np.testing.assert_array_equal(result[0],wide[0]);np.testing.assert_array_equal(result[1],wide[1])
    assert result[2:]==wide[2:]


@pytest.mark.parametrize("target,labels",[
    ("train",np.asarray([-1,1],dtype=np.int32)),
    ("train",np.asarray([0,2],dtype=np.int32)),
    ("train",np.asarray([0.0,1.0],dtype=np.float32)),
    ("train",np.asarray([False,True],dtype=np.bool_)),
    ("train",np.asarray([[0],[1]],dtype=np.int32)),
    ("train",np.asarray([0],dtype=np.int32)),
    ("calibration",np.asarray([-1,1],dtype=np.int32)),
    ("calibration",np.asarray([0,2],dtype=np.int32)),
    ("calibration",np.asarray([0.0,1.0],dtype=np.float32)),
    ("calibration",np.asarray([False,True],dtype=np.bool_)),
    ("calibration",np.asarray([[0],[1]],dtype=np.int32)),
    ("calibration",np.asarray([0],dtype=np.int32)),
])
def test_fit_ridge_rejects_invalid_label_contracts(target: str,labels: np.ndarray) -> None:
    x=np.eye(2,dtype=np.float32);valid=np.asarray([0,1],dtype=np.int32)
    train=labels if target=="train" else valid
    calibration=labels if target=="calibration" else valid
    with pytest.raises(ValueError,match="in-range integer"):
        _fit_ridge(x,train,2,[1.0],x,calibration,"cpu")


def test_runtime_namespace_is_derived_from_config() -> None:
    root=Path(__file__).resolve().parents[1]
    pipeline=(root/"scripts/run_msae_measurement_v2_pipeline.sh").read_text()
    runner=(root/"scripts/run_msae_measurement_v2.py").read_text()
    assert 'data/atlas_measurement_v2/prepared/manifest.json' not in pipeline
    assert '"session":"msae_atlas_measurement_v2_20260802"' not in pipeline
    assert 'Path(str(cfg["run_root"])).name' in runner


def _terminal_analysis_fixture(tmp_path: Path) -> tuple[dict[str, object], Path, Path, dict[str, object]]:
    root=Path(__file__).resolve().parents[1];config_path=root/"configs/atlas_measurement_v2/run.json"
    cfg=json.loads(config_path.read_text());run=tmp_path/"run";(run/"analysis").mkdir(parents=True)
    tasks=cfg["tasks"]["primary"];jobs=[row["id"] for row in cfg["checkpoints"]]
    localization={}
    for job in jobs:
        task_rows={task:{"c1_raw_signal":0.5,"c1_raw_signal_interval":{"lower":0.4},
            "c1_raw_measurable":True,"c2_finite_complete":True,"measurement_eligible":True,
            "assigned_recovery":{"interval":{"finite":500,"lower":0.8}},
            "leakage":{"interval":{"finite":500,"lower":0.1}},
            "selectivity":{"interval":{"finite":500,"lower":0.7}},"localization_pass":True} for task in tasks}
        localization[job]={"tasks":task_rows,"families":{
            "broad_structural_context_position":{"probe_pass":True,"counterfactual_pass":True},
            "lexical_content":{"probe_pass":True,"counterfactual_pass":True}},"selective_k2_posfam_passed":True}
    construct={"pairs":20,"finite_pairs":20,"finite_fraction":1.0,"control_pairs":20,"finite_control_pairs":20,
        "finite_control_fraction":1.0,"assigned_response":0.5,"paired_assigned_response":0.5,"leakage_response":0.3,
        "cross_family_control_response":0.2,"cached_noop":{"status":"eligible","bit_identical":True,"distance":0.0},
        "branch_margin":{"point":0.2,"interval":{"finite":500,"lower":0.1}},
        "control_margin":{"point":0.3,"interval":{"finite":500,"lower":0.1}},"eligible":True,"passed":True}
    specificity={job:{"constructs":{"document_context_anchor":dict(construct),"entity_substitution":dict(construct)}} for job in jobs}
    pairs={}
    for left,right in (("g4","g5"),("g4","g6"),("g5","g6")):
        pairs[f"{left}__{right}"]={"tasks":{task:{"matrix":{"pos__pos":1.0,"content__content":1.0,"pos__content":0.0,"content__pos":0.0},"identity_margin":1.0} for task in tasks}}
    results={"schema_version":"atlas_measurement_v2_analysis_v1","config_sha256":__import__("hashlib").sha256(config_path.read_bytes()).hexdigest(),
        "localization":localization,"specificity":specificity,"stability":{"pairs":pairs,"candidate_geometry_complete":True,"candidate_geometry_passed":True},
        "numerical_qa":{"heldout_passed":True},"endpoint_eligibility":{"signed_grouping_provenance":"eligible","cache_lineage":"eligible",
            "numerical_qa":"eligible","counterfactual_validity":"eligible","geometry_completeness":"eligible"},
        "overall_decision_eligibility":"eligible","architecture_outcome":"K2_broad_position_content_selective_supported"}
    result_path=run/"analysis/results.json";result_path.write_text(json.dumps(results))
    probe=run/"analysis/probe_models.npz";probe.write_bytes(b"probe")
    complete={"schema_version":"atlas_measurement_v2_analysis_complete_v1","config_sha256":results["config_sha256"],
        "results_sha256":__import__("hashlib").sha256(result_path.read_bytes()).hexdigest(),
        "probe_models_sha256":__import__("hashlib").sha256(probe.read_bytes()).hexdigest(),
        "architecture_outcome":results["architecture_outcome"]}
    (run/"analysis/COMPLETE.json").write_text(json.dumps(complete))
    return cfg,config_path,run,results


def test_terminal_validator_rejects_summary_without_underlying_probe_evaluations(tmp_path: Path) -> None:
    cfg,config_path,run,_=_terminal_analysis_fixture(tmp_path)
    with pytest.raises(RuntimeError,match="underlying probe evaluations absent"):
        validate_analysis_truth(cfg,config_path,run)


def test_split_keeps_groups_whole() -> None:
    records = []
    for group in range(8):
        for sentence in range(2):
            records.append({"document_group": f"s:g{group}", "source_record_id": f"g{group}_{sentence}"})
    split = split_esl(records)
    left = {row["document_group"] for row in split["C1"]}
    right = {row["document_group"] for row in split["C2"]}
    assert not left & right
    assert len(left) == len(right) == 4
