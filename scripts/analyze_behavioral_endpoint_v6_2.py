#!/usr/bin/env python3
"""Analysis-only, hash-bound summary of the completed behavioral endpoint v6.2 gate."""
from __future__ import annotations
import hashlib,json,os
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parents[1]
RUN=ROOT/'results/behavioral_endpoint_v6_2_20260809'
OUT=ROOT/'reports/behavioral_endpoint_v6_2_analysis/result.json'
def sha(p:Path)->str:return hashlib.sha256(p.read_bytes()).hexdigest()
def loadj(p:Path):return json.loads(p.read_text())
def readjl(p:Path):return [json.loads(x) for x in p.read_text().splitlines() if x]
def main()->None:
 inputs={}
 for p in sorted(RUN.rglob('*')):
  if p.is_file():inputs[p.relative_to(ROOT).as_posix()]=sha(p)
 final=loadj(RUN/'final/result.json');endpoints={}
 for endpoint in ('retrieval','agreement'):
  gate=loadj(RUN/'development_gate'/endpoint/'result.json');models=[]
  for model in gate['models']:
   metrics=readjl(RUN/'development'/endpoint/model['model']/'metrics.jsonl')
   cells=[c for s in model['sources'] for c in s['cells']]
   models.append({'model':model['model'],'family':model['family'],'rows':len(metrics),'eligible_rows':sum(bool(x['eligible']) for x in metrics),'directionally_correct_rows':sum(bool(x['directionally_correct']) for x in metrics),'mean_full_effect':float(np.mean([x['full_effect'] for x in metrics])),'passing_cells':sum(bool(x['passes']) for x in cells),'total_cells':len(cells),'source_overall_ratio_points':{s['source']:s['overall']['ratio_interval'][1] for s in model['sources']},'eligible_all_sources_templates':model['eligible_all_sources_templates']})
  endpoints[endpoint]={'status':gate['status'],'classification':gate['classification'],'eligible_families':gate['eligible_families'],'confirmation_authorized':gate['confirmation_authorized'],'models':models}
 payload={'schema_version':'behavioral_endpoint_v6_2_analysis','analysis_only':True,'new_model_forwards':False,'rescored':False,'development_only':True,'scope':'three pinned checkpoints, two opened development sources, six registered templates','freeze_sha256':final['freeze_sha256'],'decision':final['decision'],'future_method_authorization':final['future_method_authorization'],'representation_methods_evaluated':final['representation_methods_evaluated'],'training_performed':final['training_performed'],'endpoints':endpoints,'inputs':inputs}
 OUT.parent.mkdir(parents=True,exist_ok=True);data=(json.dumps(payload,sort_keys=True,separators=(',',':'))+'\n').encode();fd=os.open(OUT,os.O_WRONLY|os.O_CREAT|os.O_TRUNC,0o600)
 with os.fdopen(fd,'wb') as f:f.write(data)
 print(json.dumps({'status':'PASS','output':str(OUT),'sha256':sha(OUT)},indent=2))
if __name__=='__main__':main()
