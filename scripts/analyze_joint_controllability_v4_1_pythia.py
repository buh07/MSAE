#!/usr/bin/env python3
"""Descriptive, analysis-only diagnosis of frozen v4.1 Pythia development artifacts."""
from __future__ import annotations
import argparse, hashlib, json
from pathlib import Path
from typing import Any
import numpy as np
ROOT=Path(__file__).resolve().parents[1]
INPUTS=[
 ROOT/'configs/joint_controllability_benchmark_v4_1/FREEZE.json',
 ROOT/'results/joint_controllability_benchmark_v4_1_20260808/task_gate/result.json',
 ROOT/'results/joint_controllability_benchmark_v4_1_20260808/task_gate/pythia160/metrics.jsonl',
 ROOT/'data/joint_controllability_benchmark_v4_prepared/rows.jsonl',
 ROOT/'data/joint_controllability_benchmark_v4_prepared/pythia160.jsonl',
 ROOT/'reports/provenance/joint_controllability_assay_v5_candidate/V4_1_PRESERVATION.json',
]
def sha(p:Path)->str:return hashlib.sha256(p.read_bytes()).hexdigest()
def readjl(p:Path)->list[dict[str,Any]]:return [json.loads(x) for x in p.read_text().splitlines() if x]
def cat_r2(y:np.ndarray, vals:list[Any])->float:
 levels=sorted(set(map(str,vals))); X=np.ones((len(y),len(levels)))
 for j,v in enumerate(levels[1:],1): X[:,j]=np.array([str(x)==v for x in vals])
 pred=X@np.linalg.lstsq(X,y,rcond=None)[0]
 return float(1-np.sum((y-pred)**2)/np.sum((y-y.mean())**2))
def main(out:Path)->None:
 raw={r['component_id']:r for r in readjl(INPUTS[3])}
 enc={r['component_id']:r for r in readjl(INPUTS[4])}
 rows=[]
 for m in readjl(INPUTS[2]):
  r=raw[m['component_id']]; e=enc[m['component_id']]; f=float(m['full_effect']); s=float(m['sham_effect'])
  rows.append({**m,**{k:r[k] for k in ('answer_word','query_key','base_key','sham_key','document_id')},'prompt_length':len(e['base_prompt_ids']),'eligible':f>0.25,'ratio':abs(s)/abs(f) if f>0.25 else None})
 eligible=[r for r in rows if r['eligible']]; ratios=np.array([r['ratio'] for r in eligible],float)
 def summary(rs:list[dict[str,Any]])->dict[str,Any]:
  x=np.array([r['ratio'] for r in rs],float); k=max(0,int(.1*len(x))); sx=np.sort(x); tx=sx[k:len(x)-k] if 2*k<len(x) else sx
  return {'n':len(x),'mean':float(x.mean()),'median':float(np.median(x)),'trimmed_mean_10pct':float(tx.mean()),'p75':float(np.quantile(x,.75)),'p90':float(np.quantile(x,.9)),'p95':float(np.quantile(x,.95)),'maximum':float(x.max()),'ratio_gt_1':int(np.sum(x>1))}
 by_source={s:summary([r for r in eligible if r['source']==s]) for s in sorted({r['source'] for r in rows})}
 outliers=[r for r in eligible if r['ratio']>1]
 med_f=float(np.median([abs(r['full_effect']) for r in eligible])); med_s=float(np.median([abs(r['sham_effect']) for r in eligible]))
 for r in outliers:
  r['outlier_diagnostic']=('small_coherent' if abs(r['full_effect'])<med_f else 'not_small_coherent')+'+'+('large_sham' if abs(r['sham_effect'])>med_s else 'not_large_sham')
 y=ratios
 r2={name:cat_r2(y,[r[name] for r in eligible]) for name in ('query_key','base_key','sham_key','answer_word','source','prompt_length')}
 # Query/base/sham keys are deterministically coupled, so these descriptive R2 values cannot be attributed to roles.
 triples={r['query_key']:(r['base_key'],r['sham_key']) for r in rows}
 deterministic_mapping=all((r['base_key'],r['sham_key'])==triples[r['query_key']] for r in rows)
 levels=sorted({r['query_key'] for r in rows}|{r['base_key'] for r in rows}|{r['sham_key'] for r in rows})
 design=np.asarray([[1]+[r['query_key']==k for k in levels[1:]]+[r['base_key']==k for k in levels[1:]]+[r['sham_key']==k for k in levels[1:]] for r in rows],float)
 role_design_rank=int(np.linalg.matrix_rank(design,tol=1e-8)); identifiable=not deterministic_mapping and role_design_rank==design.shape[1]
 payload={'schema_version':'joint_control_v4_1_pythia_diagnostic_v1','analysis_only':True,'new_model_forwards':False,'rescored_v4_1':False,'changes_v4_1_decision':False,'inputs':{p.relative_to(ROOT).as_posix():sha(p) for p in INPUTS},'frozen_claim':'Pythia met signed effect support (59/64 per opened Wikitext partition) but failed both single-sham gates; all-model v4.1 stopped before method evaluation.','all_eligible':summary(eligible),'by_source':by_source,'categorical_r2_descriptive_not_causal':r2,'key_role_attribution_identifiable':identifiable,'deterministic_query_to_base_sham_mapping':deterministic_mapping,'key_role_design_columns':design.shape[1],'key_role_design_rank':role_design_rank,'key_role_warning':'query_key deterministically fixes base_key and sham_key; role-specific key variance is non-identifiable','median_abs_full_effect':med_f,'median_abs_sham_effect':med_s,'outliers_ratio_gt_1':outliers,'document_effect_estimable':False,'document_warning':'one development row per document, so document fixed-effect variance is not separately estimable','estimand_sensitivity_descriptive_only':True}
 out.mkdir(parents=True,exist_ok=False); (out/'diagnostic.json').write_text(json.dumps(payload,sort_keys=True,separators=(',',':'),allow_nan=False)+'\n')
 md=['# Pythia v4.1 opened-development diagnostic','','**Analysis only; no model forward and no v4.1 rescoring.**','',payload['frozen_claim'],'',f"Eligible ratios: mean {payload['all_eligible']['mean']:.3f}, median {payload['all_eligible']['median']:.3f}, 10% trimmed mean {payload['all_eligible']['trimmed_mean_10pct']:.3f}, p90 {payload['all_eligible']['p90']:.3f}; {payload['all_eligible']['ratio_gt_1']} rows exceeded one.",'',payload['key_role_warning']+'.',payload['document_warning']+'.','',f"Exact machine-readable report: `diagnostic.json` ({sha(out/'diagnostic.json')})."]
 (out/'diagnostic.md').write_text('\n'.join(md)+'\n')
 print(json.dumps({'status':'COMPLETE','rows':len(rows),'eligible':len(eligible),'outliers':len(outliers),'output':str(out)},indent=2))
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);a=p.parse_args();main(a.output)
