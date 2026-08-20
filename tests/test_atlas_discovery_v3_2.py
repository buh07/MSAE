from __future__ import annotations
import json
import sys
from pathlib import Path
import pytest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from scripts.atlas_discovery_v3_2 import NAMESPACE, stable_fold
from scripts.run_atlas_discovery_v3_2 import load_config


def test_attempt6_namespace_and_config_forbid_neural_scoring() -> None:
    assert NAMESPACE=='atlas_discovery_v3_2_attempt6'
    config=load_config(ROOT/'configs/atlas_discovery_v3_2/run.json')
    assert config['status']=='attempt6_label_only_prescore_authorized_no_neural_inference'
    assert config['model']['dtype']=='float32'
    assert config['data_root']=='data/atlas_discovery_v3_2_attempt6'


def test_population_split_is_document_and_component_disjoint() -> None:
    split=json.loads((ROOT/'configs/atlas_discovery_v3_2/population_split.json').read_text())
    assert split['fresh_qa_activation_or_outcome_used'] is False
    for source,row in split['sources'].items():
        legacy_docs=set(row['legacy_documents']);fresh_docs=set(row['fresh_documents'])
        assert legacy_docs.isdisjoint(fresh_docs)
        assert set(row['legacy_component_ids']).isdisjoint(row['fresh_component_ids'])
        assert len(row['legacy_pair_ids'])==32 and len(set(row['legacy_pair_ids']))==32
        assert len(row['fresh_pair_ids'])==16 and len(set(row['fresh_pair_ids']))==16
        assert set(row['science_excluded_documents'])==legacy_docs|fresh_docs


def test_fold_is_deterministic_and_source_specific() -> None:
    assert stable_fold('EWT','doc',seed=20260803,folds=5)==stable_fold('EWT','doc',seed=20260803,folds=5)
    assert stable_fold('EWT','doc',seed=20260803,folds=5) in range(5)


def test_existing_science_rows_exclude_every_qa_document() -> None:
    root=ROOT/'data/atlas_discovery_v3_2_attempt6/prepared'
    if not root.exists(): pytest.skip('attempt6 prescore has not run')
    split=json.loads((ROOT/'configs/atlas_discovery_v3_2/population_split.json').read_text())
    for source in ('EWT','GUM'):
        forbidden=set(split['sources'][source]['science_excluded_documents'])
        for filename in ('activation_rows.jsonl','pair_rows.jsonl','relation_rows.jsonl','intervention_pairs.jsonl','cross_family_rows.jsonl'):
            for line in (root/source/filename).read_text().splitlines():
                row=json.loads(line)
                assert row.get('document_group') not in forbidden
                assert row.get('donor_document_group') not in forbidden
