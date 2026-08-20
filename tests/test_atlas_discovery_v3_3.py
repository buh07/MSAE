from __future__ import annotations
import json,sys
from pathlib import Path
import pytest
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts'))
from atlas_discovery_v3_3 import NAMESPACE
from run_atlas_discovery_v3_3 import load_config

def test_attempt7_config_and_namespace():
 c=load_config(ROOT/'configs/atlas_discovery_v3_3/run_final_v3.json')
 assert NAMESPACE=='atlas_discovery_v3_3_attempt7'
 assert c['status']=='attempt7_final_v3_label_only_science_prescore_no_neural_inference'
 assert c['model']['dtype']=='float32'

def test_external_fresh_and_legacy_panels_are_disjoint():
 x=json.loads((ROOT/'configs/atlas_discovery_v3_3/population_split_v3.json').read_text())
 assert x['activation_or_scientific_outcome_used'] is False
 for s,v in x['sources'].items():
  assert set(v['legacy_documents']).isdisjoint(v['fresh_documents'])
  assert set(v['legacy_component_ids']).isdisjoint(v['fresh_component_ids'])
  assert len(v['legacy_pair_ids'])==32 and len(v['fresh_pair_ids'])==16
  assert v['science_excluded_documents']==v['legacy_documents']

def test_science_rows_exclude_legacy_qa_documents():
 root=ROOT/'data/atlas_discovery_v3_3_attempt7_final_v3/prepared'
 if not root.exists():pytest.skip('attempt7 prescore not built')
 split=json.loads((ROOT/'configs/atlas_discovery_v3_3/population_split_v3.json').read_text())
 for s in ('EWT','GUM'):
  bad=set(split['sources'][s]['science_excluded_documents'])
  for name in ('activation_rows.jsonl','pair_rows.jsonl','relation_rows.jsonl','intervention_pairs.jsonl','cross_family_rows.jsonl'):
   for line in (root/s/name).read_text().splitlines():
    row=json.loads(line);assert row.get('document_group') not in bad;assert row.get('donor_document_group') not in bad
