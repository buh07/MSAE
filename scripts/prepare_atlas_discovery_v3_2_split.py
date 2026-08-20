#!/usr/bin/env python3
"""Freeze attempt-6 legacy/fresh numerical-QA and science document split label-only."""
from __future__ import annotations
import argparse, glob, hashlib, json
from pathlib import Path
from typing import Any
ROOT=Path(__file__).resolve().parents[1]
SALT='atlas_discovery_v3_2_attempt6'
SOURCES=('EWT','GUM')
PARENT=ROOT/'data/atlas_discovery_v3_1_attempt5/prepared'
TERMINAL=ROOT/'pilot_runs/20260803_atlas_discovery_v3_1_attempt5/TERMINAL.json'

def sha(path:Path)->str:return hashlib.sha256(path.read_bytes()).hexdigest()
def digest(*parts:Any)->str:return hashlib.sha256('|'.join(map(str,parts)).encode()).hexdigest()
def docs(row:dict[str,Any])->set[str]:return {str(row[k]) for k in ('document_group','donor_document_group') if row.get(k)}
def load_jsonl(path:Path)->list[dict[str,Any]]:return [json.loads(x) for x in path.read_text().splitlines() if x]

def main()->None:
 p=argparse.ArgumentParser();p.add_argument('--output',default='configs/atlas_discovery_v3_2/population_split.json');a=p.parse_args()
 terminal=json.loads(TERMINAL.read_text())['payload']
 if terminal.get('status')!='TERMINAL_TECHNICALLY_INVALID' or terminal.get('retry_attempt5_authorized') is not False:raise RuntimeError('attempt5 terminal invalid')
 sources={}
 for source in SOURCES:
  pairs_path=PARENT/source/'intervention_pairs.jsonl'; pairs=load_jsonl(pairs_path); by={x['pair_id']:x for x in pairs}
  qa_path=ROOT/f'pilot_runs/20260803_atlas_discovery_v3_1_attempt5/failed_numerical_qa/{source}/qa_rows.json'
  legacy_rows=json.loads(qa_path.read_text());legacy_ids=[str(x['pair_id']) for x in legacy_rows]
  if len(legacy_ids)!=32 or len(set(legacy_ids))!=32:raise RuntimeError('legacy QA identity drift')
  legacy=[by[x] for x in legacy_ids]; used=set().union(*(docs(x) for x in legacy))
  legacy_components={str(x['component_id']) for x in legacy}
  fresh=[]; fresh_components=set()
  for construct in ('context_factorial','relative_gap'):
   candidates=sorted((x for x in pairs if x['construct']==construct),key=lambda x:digest(SALT,'fresh-qa',source,construct,x['pair_id']))
   for row in candidates:
    if docs(row)&used or str(row['component_id']) in legacy_components|fresh_components:continue
    fresh.append(row);used.update(docs(row));fresh_components.add(str(row['component_id']))
    if sum(x['construct']==construct for x in fresh)==8:break
   if sum(x['construct']==construct for x in fresh)!=8:raise RuntimeError(f'insufficient fresh QA: {source}/{construct}')
  fresh_docs=set().union(*(docs(x) for x in fresh))
  legacy_docs=set().union(*(docs(x) for x in legacy))
  if legacy_docs&fresh_docs:raise RuntimeError('fresh/legacy document overlap')
  sources[source]={
   'parent_intervention_pairs':{'path':str(pairs_path.relative_to(ROOT)),'sha256':sha(pairs_path)},
   'legacy_qa_rows':{'path':str(qa_path.relative_to(ROOT)),'sha256':sha(qa_path)},
   'legacy_pair_ids':legacy_ids,
   'legacy_component_ids':sorted(legacy_components),
   'legacy_documents':sorted(legacy_docs),
   'fresh_pair_ids':[str(x['pair_id']) for x in fresh],
   'fresh_component_ids':sorted(fresh_components),
   'fresh_documents':sorted(fresh_docs),
   'science_excluded_documents':sorted(legacy_docs|fresh_docs),
   'counts':{'legacy_pairs':len(legacy),'legacy_documents':len(legacy_docs),'fresh_pairs':len(fresh),'fresh_documents':len(fresh_docs),'science_excluded_documents':len(legacy_docs|fresh_docs)},
  }
 out={
  'schema_version':'atlas_discovery_v3_2_attempt6_population_split_v1','salt':SALT,
  'selection_rule':'exact attempt5 QA plus 8 context_factorial then 8 relative_gap pairs per source, each class ordered by salted SHA-256, greedily rejecting any legacy/fresh document or component overlap',
  'attempt5_terminal':{'path':str(TERMINAL.relative_to(ROOT)),'sha256':sha(TERMINAL)},
  'fresh_qa_activation_or_outcome_used':False,'science_documents_selected_using_labels':False,'sources':sources,
 }
 path=ROOT/a.output
 if path.exists():
  if json.loads(path.read_text())!=out:raise RuntimeError('existing split drift')
 else:path.write_text(json.dumps(out,indent=2,sort_keys=True)+'\n')
 print(json.dumps({'path':str(path.relative_to(ROOT)),'sha256':sha(path),'sources':{s:sources[s]['counts'] for s in SOURCES}},indent=2,sort_keys=True))
if __name__=='__main__':main()
