#!/usr/bin/env python3
"""Analysis-only template robustness report for frozen v5 development metrics."""
from __future__ import annotations
import argparse,hashlib,json
from pathlib import Path
from typing import Any
import numpy as np
ROOT=Path(__file__).resolve().parents[1]
MODELS=['gpt2','pythia160','gemma2'];SOURCES=['WIKITEXT_FRESH','AGNEWS_FRESH']
def sha(p:Path)->str:
 h=hashlib.sha256()
 with p.open('rb') as f:
  for c in iter(lambda:f.read(1<<20),b''):h.update(c)
 return h.hexdigest()
def readjl(p:Path)->list[dict[str,Any]]:return [json.loads(x) for x in p.read_text().splitlines() if x]
def stats(x:list[float])->dict[str,Any]:
 a=np.asarray(x,float)
 return {'n':len(a),'mean':float(a.mean()),'sd':float(a.std(ddof=1)) if len(a)>1 else 0.0,'minimum':float(a.min()),'q10':float(np.quantile(a,.1)),'q25':float(np.quantile(a,.25)),'median':float(np.median(a)),'q75':float(np.quantile(a,.75)),'q90':float(np.quantile(a,.9)),'maximum':float(a.max())}
def main(out:Path)->None:
 freeze=ROOT/'configs/joint_controllability_assay_v5/FREEZE.json';gate=ROOT/'results/joint_controllability_assay_v5_20260808/development_gate/result.json';rawp=ROOT/'data/joint_controllability_assay_v5_prepared/rows.jsonl';raw={r['component_id']:r for r in readjl(rawp)}
 inputs=[freeze,gate,rawp,ROOT/'reports/provenance/behavioral_endpoint_v6_candidate/V5_PRESERVATION.json'];cells=[];strata={};interactions=[]
 for model in MODELS:
  mp=ROOT/f'results/joint_controllability_assay_v5_20260808/development/{model}/metrics.jsonl';cp=mp.with_name('COMPLETE.json');inputs.extend([mp,cp]);complete=json.loads(cp.read_text())
  if complete['metrics_sha256']!=sha(mp):raise RuntimeError(f'v5 completion/metric hash mismatch {model}')
  rows=readjl(mp)
  cellmap={}
  for source in SOURCES:
   for t in range(3):
    rr=[r for r in rows if r['source']==source and int(r['template_index'])==t];eligible=[r for r in rr if r['eligible']];F=[float(r['full_effect']) for r in rr];S=[float(r['sham_dispersion']) for r in rr];R=[float(r['sham_ratio']) for r in eligible]
    weak=[f<=.25 for f in F];large=[s>.2*max(f,.25) for f,s in zip(F,S,strict=True)]
    dec={'weak_effect_only':sum(w and not l for w,l in zip(weak,large,strict=True)),'large_sham_only':sum(l and not w for w,l in zip(weak,large,strict=True)),'both':sum(w and l for w,l in zip(weak,large,strict=True)),'neither':sum(not w and not l for w,l in zip(weak,large,strict=True))}
    cell={'model':model,'source':source,'template_index':t,'rows':len(rr),'eligible_rows':len(eligible),'eligibility':len(eligible)/len(rr),'full_effect':stats(F),'sham_dispersion':stats(S),'eligible_ratio':stats(R),'ratio_gt_1':sum(x>1 for x in R),'failure_decomposition_at_component_level':dec,'formal_cell_pass':False};cells.append(cell);cellmap[(source,t)]=cell
    by={}
    for r in rr:
     meta=raw[r['component_id']];k=f"key{meta['query_key_index']}:answer{meta['answer_index']}";by.setdefault(k,[]).append(r)
    strata[f'{model}:{source}:template{t}']={k:{'n':len(v),'mean_full_effect':float(np.mean([x['full_effect'] for x in v])),'mean_sham_dispersion':float(np.mean([x['sham_dispersion'] for x in v])),'eligible_fraction':float(np.mean([x['eligible'] for x in v])),'mean_ratio_eligible':float(np.mean([x['sham_ratio'] for x in v if x['eligible']])) if any(x['eligible'] for x in v) else None} for k,v in sorted(by.items())}
  for t in range(3):
   a=cellmap[('AGNEWS_FRESH',t)];w=cellmap[('WIKITEXT_FRESH',t)];interactions.append({'model':model,'template_index':t,'AGNEWS_minus_WIKITEXT':{'eligibility':a['eligibility']-w['eligibility'],'mean_full_effect':a['full_effect']['mean']-w['full_effect']['mean'],'mean_sham_dispersion':a['sham_dispersion']['mean']-w['sham_dispersion']['mean'],'mean_ratio':a['eligible_ratio']['mean']-w['eligible_ratio']['mean']}})
 payload={'schema_version':'behavioral_endpoint_v5_template_analysis','analysis_only':True,'new_model_forwards':False,'v5_rescored':False,'changes_v5_decision':False,'formal_v5_status':'FAIL','inputs':{p.relative_to(ROOT).as_posix():sha(p) for p in inputs},'thresholds_descriptive_reference':{'minimum_full_effect':.25,'maximum_mean_ratio':.2,'maximum_upper_bound':.3},'cells':cells,'key_answer_strata':strata,'template_source_interactions':interactions,'interpretation_limits':['Component categories are descriptive and do not replace the frozen template-stratified mean gate.','Template-specific favorable results cannot be promoted post hoc.','No confirmation or representation method was evaluated.']}
 out.mkdir(parents=True,exist_ok=False);(out/'analysis.json').write_text(json.dumps(payload,sort_keys=True,separators=(',',':'),allow_nan=False)+'\n')
 lines=['# V5 template-robustness analysis','', '**Analysis only. No model forward, no v5 rescoring, and no change to the formal FAIL.**','', '## Summary','', 'All six checkpoint/source aggregates failed the frozen multi-sham specificity gate. Template effects were highly heterogeneous: the original-style template was comparatively selective for GPT-2 and Gemma, whereas the other templates combined weaker matching effects and/or larger unrelated-key dispersion. Selecting the favorable template now would be outcome-conditioned.','', '## Checkpoint × source × template','', '| Checkpoint | Source | T | Eligible | F median | Sham median | Ratio median | Ratio mean | >1 | Failure mix weak/large/both/neither |','|---|---|---:|---:|---:|---:|---:|---:|---:|---|']
 for c in cells:
  d=c['failure_decomposition_at_component_level'];lines.append(f"| {c['model']} | {c['source']} | {c['template_index']} | {c['eligible_rows']}/64 | {c['full_effect']['median']:.3f} | {c['sham_dispersion']['median']:.3f} | {c['eligible_ratio']['median']:.3f} | {c['eligible_ratio']['mean']:.3f} | {c['ratio_gt_1']} | {d['weak_effect_only']}/{d['large_sham_only']}/{d['both']}/{d['neither']} |")
 lines += ['', '## Interpretation', '', '- GPT-2 templates 1–2 show both reduced matching effects and greater unrelated-key dispersion relative to template 0.', '- Gemma retains the largest matching effects but templates 1–2 still show excessive unrelated-key sensitivity.', '- Pythia varies strongly with wording; neither source supports template-general specificity.', '- AG News usually improves matching support, but it does not repair the specificity gate.', '', 'Full key×answer strata, quantiles, tails, and template×source differences are in `analysis.json`.']
 (out/'report.md').write_text('\n'.join(lines)+'\n');print(json.dumps({'status':'COMPLETE','cells':len(cells),'output':str(out),'analysis_sha256':sha(out/'analysis.json')},indent=2))
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);a=p.parse_args();main(a.output)
