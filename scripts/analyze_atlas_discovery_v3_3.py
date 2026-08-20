#!/usr/bin/env python3
"""Complete frozen no-training analysis for Atlas v3.3 attempt 7."""
from __future__ import annotations
import argparse,hashlib,json,os,platform,time
os.environ.setdefault("CUBLAS_WORKSPACE_CONFIG", ":4096:8")
from collections import Counter,defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any,Mapping,Sequence
import numpy as np
import torch
from atlas_discovery_v3_3 import bootstrap_component_multiplicities,pooled_document_row_weights,sha256_file,terminal_outcome
from atlas_discovery_v3_3_analysis import (CategoricalEncoder,RidgeModel,balanced_accuracy,basis_overlap,choose_alpha,delta_basis,fit_ridge,interval,macro_f1,make_projector,normalized_recovery,prior_chance,row_normalize)
from extract_atlas_discovery_v3_3 import ROOT,_exclusive_lock,_fsync_directory,_fsync_file,_gpu_uuid,_load_source_bundle,_new_staging,_promote,_verify_complete_cache,_verify_qa,load_scoring_config

TASKS=('start_distance','relative_quartile','pair_distance','head_signed_distance','dependency_depth','deprel_coarse','token_identity','lemma_identity','number','upos_coarse','capitalization','word_length','punctuation')
SYNTAX_TASKS=('head_signed_distance','dependency_depth','deprel_coarse')
SEQUENTIAL_TASKS=('start_distance','relative_quartile','pair_distance')
SCREEN_TASKS=('number','upos_coarse','capitalization','word_length','punctuation')
INTERVENTION_CLASSES=('relative_gap','true_context','unrelated_context','proper_noun_substitution')
PROJECTION_ORGANIZATION_GROUPS={
 'broad_position_vs_lexical':{
  'sequential':(('start_distance','task',True),('relative_quartile','task',True)),
  'syntax_child':tuple((task,'task',True) for task in SYNTAX_TASKS),
  'lexical':(('token_identity','task',False),),
 },
 'sequential_context_vs_lexical_plus_relational_syntax':{
  'sequential':(('start_distance','task',True),('relative_quartile','task',True)),
  'lexical':(('token_identity','task',False),),
 },
 'token_local_vs_context_dependent':{
  'sequential':(('start_distance','task',True),('relative_quartile','task',True)),
  'relation':tuple((task,'relation',True) for task in SYNTAX_TASKS),
  'lexical':(('token_identity','task',False),),
 },
}
PROJECTION_CAPTURE_ROLES={
 'broad_position_vs_lexical':{'relative_gap':'P','true_context':'P','unrelated_context':'P','proper_noun_substitution':'Q','relation':'external'},
 'sequential_context_vs_lexical_plus_relational_syntax':{'relative_gap':'P','true_context':'P','unrelated_context':'P','proper_noun_substitution':'Q','relation':'external'},
 'token_local_vs_context_dependent':{'relative_gap':'unassigned','true_context':'P','unrelated_context':'P','proper_noun_substitution':'Q','relation':'P'},
}

def projection_capture_controls(organization:str,kind:str)->tuple[str,...]:
 roles=PROJECTION_CAPTURE_ROLES[organization];role=roles[kind]
 if role not in {'P','Q'}:return ()
 opposite='Q' if role=='P' else 'P'
 return tuple(candidate for candidate,candidate_role in roles.items() if candidate_role==opposite)

def raw_delta_covariance_spectrum(delta:np.ndarray)->dict[str,Any]:
 values=np.asarray(delta,dtype=np.float64)
 if values.ndim!=2 or len(values)<2 or not np.isfinite(values).all():
  raise ValueError('raw delta covariance requires at least two finite rows')
 centered=values-values.mean(axis=0,keepdims=True)
 singular=np.linalg.svd(centered,compute_uv=False)
 eigenvalues=(singular*singular)/float(len(values)-1)
 return {
  'eigenvalues_descending':eigenvalues.tolist(),
  'centering':'column_mean',
  'normalization':'sample_n_minus_1',
  'rows':int(values.shape[0]),
  'width':int(values.shape[1]),
 }

def json_safe(value:Any)->Any:
 if isinstance(value,float) and not np.isfinite(value):return None
 if isinstance(value,np.generic):return json_safe(value.item())
 if isinstance(value,dict):return {str(k):json_safe(v) for k,v in value.items()}
 if isinstance(value,(list,tuple)):return [json_safe(v) for v in value]
 return value

@dataclass
class SourceData:
 source:str;root:Path;x:np.ndarray;rows:list[dict[str,Any]];row_index:dict[str,int];main:dict[str,dict[str,Any]];pairs:list[dict[str,Any]];tasks:dict[str,list[dict[str,Any]]];relations:list[dict[str,Any]];cross:list[dict[str,Any]];verified_inventory:dict[str,str]

def jsonl(path:Path)->list[dict[str,Any]]:return [json.loads(line) for line in path.read_text().splitlines() if line]

def verified_jsonl(path:Path,expected_sha:str,expected_rows:int,label:str)->tuple[list[dict[str,Any]],str]:
 actual=sha256_file(path)
 if actual!=expected_sha:raise RuntimeError(f'analysis child digest drift: {label}')
 values=jsonl(path)
 if len(values)!=int(expected_rows):raise RuntimeError(f'analysis child row-count drift: {label}')
 return values,actual

def load_source(config:Mapping[str,Any],prescore:Mapping[str,Any],manifest:Mapping[str,Any],source:str)->SourceData:
 bundle=_load_source_bundle(prescore,manifest,source);run=ROOT/str(prescore['run_root']);final=run/'activations'/source
 _verify_complete_cache(final,config,prescore,bundle,source)
 side=[json.loads(line)['row_id'] for line in (final/'row_ids.jsonl').read_text().splitlines() if line];rows=bundle['rows']
 if side!=[r['row_id'] for r in rows]:raise RuntimeError('activation sidecar drift')
 x=np.load(final/'activations.float32.npy',mmap_mode='r');idx={row_id:i for i,row_id in enumerate(side)}
 root=ROOT/str(prescore['data_root'])/'prepared'/source;spec=manifest['sources'][source];inventory={}
 expected_task_names=set(TASKS)
 if set(spec['tasks'])!=expected_task_names:raise RuntimeError(f'analysis task manifest inventory drift: {source}')
 task_dir=root/'tasks';expected_task_files={f'{task}.jsonl' for task in TASKS if task!='pair_distance'}
 if {p.name for p in task_dir.iterdir() if p.is_file()}!=expected_task_files or any(p.is_dir() for p in task_dir.iterdir()):raise RuntimeError(f'analysis task file inventory drift: {source}')
 def verified(path:Path,expected_sha:str,expected_rows:int,label:str)->list[dict[str,Any]]:
  values,actual=verified_jsonl(path,expected_sha,expected_rows,f'{source}/{label}');inventory[label]=actual;return values
 tasks={task:verified(root/'tasks'/f'{task}.jsonl',spec['tasks'][task]['sha256'],spec['tasks'][task]['rows'],f'tasks/{task}') for task in TASKS if task!='pair_distance'}
 tasks['pair_distance']=verified(root/'pair_rows.jsonl',spec['tasks']['pair_distance']['sha256'],spec['pair_rows'],'pair_rows')
 relations=verified(root/'relation_rows.jsonl',spec['relation_rows_sha256'],spec['relation_rows'],'relation_rows')
 cross=verified(root/'cross_family_rows.jsonl',spec['cross_family_rows_sha256'],spec['cross_family_rows'],'cross_family_rows')
 main={r['row_id']:r for r in rows if r.get('kind')=='main'}
 known=set(idx);pair_ids={p['pair_id'] for p in bundle['pairs']}
 for task,values in tasks.items():
  for row in values:
   refs=(row['left_row_id'],row['right_row_id']) if task=='pair_distance' else (row['row_id'],)
   if any(ref not in main for ref in refs):raise RuntimeError(f'analysis task foreign-key drift: {source}/{task}')
 for row in relations:
  if any(row[key] not in main for key in ('child_row_id','head_row_id','sham_row_id')):raise RuntimeError(f'analysis relation foreign-key drift: {source}')
 for row in cross:
  if row['pair_id'] not in pair_ids:raise RuntimeError(f'analysis cross-family foreign-key drift: {source}')
 return SourceData(source,root,x,rows,idx,main,bundle['pairs'],tasks,relations,cross,inventory)

def task_rows(data:SourceData,task:str)->list[dict[str,Any]]:
 return data.tasks[task]

def task_matrix(data:SourceData,task:str,rows:Sequence[Mapping[str,Any]],projector:np.ndarray|None=None,complement:bool=False)->np.ndarray:
 if task=='pair_distance':
  left=np.asarray([data.x[data.row_index[str(r['left_row_id'])]] for r in rows],dtype=np.float64);right=np.asarray([data.x[data.row_index[str(r['right_row_id'])]] for r in rows],dtype=np.float64)
  if projector is not None:
   p=np.eye(projector.shape[0])-projector if complement else projector;left=left@p;right=right@p
  return np.concatenate([left,right-left],axis=1)
 x=np.asarray([data.x[data.row_index[str(r['row_id'])]] for r in rows],dtype=np.float64)
 if projector is not None:x=x@(np.eye(projector.shape[0])-projector if complement else projector)
 return x

def fit_lemma_vocab(data:SourceData,minimum:int=25,cap:int=128)->set[str]:
 docs:dict[str,set[str]]=defaultdict(set)
 for r in data.main.values():docs[str(r['labels']['lemma'])].add(str(r['document_group']))
 ranked=sorted(((len(v),k) for k,v in docs.items() if len(v)>=minimum),key=lambda x:(-x[0],x[1].encode()))
 return {label for _,label in ranked[:cap]}

def _main_nuisance(meta:Mapping[str,Any],lemma_vocab:set[str])->dict[str,str]:
 lab=meta['labels'];token=lab['token_identity'];lemma=lab['lemma']
 return {'token_class':token if token!='__DROP__' else '__NONRETAINED__','lemma_class':lemma if lemma in lemma_vocab else '__NONRETAINED__','upos_coarse':lab['upos_coarse'],'punctuation':lab['punctuation'],'capitalization':lab['capitalization'],'word_length':lab['word_length'],'sentence_length':lab['sentence_length'],'start_distance':lab['start_distance'],'relative_quartile':lab['relative_quartile']}

def nuisance_rows(data:SourceData,task:str,rows:Sequence[Mapping[str,Any]],lemma_vocab:set[str])->list[dict[str,str]]:
 out=[]
 for r in rows:
  if task=='pair_distance':
   left=_main_nuisance(data.main[str(r['left_row_id'])],lemma_vocab);right=_main_nuisance(data.main[str(r['right_row_id'])],lemma_vocab)
   rec={'sentence_length':left['sentence_length'],'left_start_distance':left['start_distance']}
   for side,val in [('left',left),('right',right)]:
    for key in ('token_class','lemma_class','upos_coarse','punctuation','capitalization','word_length'):rec[f'{side}_{key}']=val[key]
   out.append(rec)
  else:out.append(_main_nuisance(data.main[str(r['row_id'])],lemma_vocab))
 return out

def bootstrap_metrics(rows:Sequence[Mapping[str,Any]],y:np.ndarray,pred:np.ndarray,fit_y:np.ndarray,classes:Sequence[str],*,direction:str,endpoint:str,seed:int,other_pred:np.ndarray|None=None)->dict[str,Any]:
 components=sorted({str(r['component_id']) for r in rows},key=lambda x:x.encode());vals=[];diff=[]
 for draw in range(500):
  mult=bootstrap_component_multiplicities(components,direction=direction,endpoint=endpoint,draw=draw,seed=seed);w=np.asarray([mult.get(str(r['component_id']),0) for r in rows],dtype=np.float64)
  if any(w[y==c].sum()<=0 for c in classes):
   vals.append(float('nan'))
   if other_pred is not None:diff.append(float('nan'))
   continue
  f=macro_f1(y,pred,classes,w);chance=prior_chance(fit_y,y,classes,w);vals.append(normalized_recovery(f,chance))
  if other_pred is not None:diff.append(f-macro_f1(y,other_pred,classes,w))
 return {'normalized_recovery':interval(vals),'paired_f1_difference':interval(diff) if other_pred is not None else None}

def evaluate_direction(fit_data:SourceData,test_data:SourceData,task:str,analysis:Mapping[str,Any],*,projector:np.ndarray|None=None,complement:bool=False,relation_variant:str|None=None,return_internal:bool=False)->tuple[dict[str,Any],RidgeModel]:
 fit_rows=task_rows(fit_data,task);test_rows=task_rows(test_data,task);fit_vocab=fit_lemma_vocab(fit_data)
 if task=='lemma_identity':
  fit_rows=[r for r in fit_rows if r['label'] in fit_vocab];test_rows=[r for r in test_rows if r['label'] in fit_vocab]
 classes=tuple(sorted({str(r['label']) for r in fit_rows},key=lambda x:x.encode()))
 heldout_classes=set(map(lambda r:str(r['label']),test_rows))
 if len(classes)<2 or heldout_classes-set(classes) or (task!='lemma_identity' and heldout_classes!=set(classes)):raise RuntimeError(f'class transfer drift {task}')
 xfit=task_matrix(fit_data,task,fit_rows,projector,complement);xtest=task_matrix(test_data,task,test_rows,projector,complement)
 yfit=np.asarray([r['label'] for r in fit_rows],dtype=str);ytest=np.asarray([r['label'] for r in test_rows],dtype=str);folds=np.asarray([fit_data.main[str(r['left_row_id'] if task=='pair_distance' else r['row_id'])]['fold'] for r in fit_rows])
 nfit=nuisance_rows(fit_data,task,fit_rows,fit_vocab);ntest=nuisance_rows(test_data,task,test_rows,fit_vocab);columns=analysis['nuisance_columns'][task];encoder=CategoricalEncoder.fit(nfit,columns);nf=encoder.transform(nfit);nt=encoder.transform(ntest)
 device=str(analysis['ridge_device']);alphas=analysis['alphas'];floor=float(analysis['scale_floor'])
 raw_alpha,raw_grid=choose_alpha(xfit,yfit,folds,classes,alphas,device=device,scale_floor=floor);raw=fit_ridge(xfit,yfit,classes,raw_alpha,device=device,scale_floor=floor);raw_pred=raw.predict(xtest)
 nuisance_alpha,nuisance_grid=choose_alpha(nf,yfit,folds,classes,alphas,device=device,scale_floor=floor);nuisance=fit_ridge(nf,yfit,classes,nuisance_alpha,device=device,scale_floor=floor);nuisance_pred=nuisance.predict(nt)
 combined_fit=np.concatenate([xfit,nf],axis=1);combined_test=np.concatenate([xtest,nt],axis=1);combined_alpha,combined_grid=choose_alpha(combined_fit,yfit,folds,classes,alphas,device=device,scale_floor=floor);combined=fit_ridge(combined_fit,yfit,classes,combined_alpha,device=device,scale_floor=floor);combined_pred=combined.predict(combined_test)
 f=macro_f1(ytest,raw_pred,classes);chance=prior_chance(yfit,ytest,classes);inc=macro_f1(ytest,combined_pred,classes)-macro_f1(ytest,nuisance_pred,classes);direction=f'{fit_data.source}_to_{test_data.source}'
 boot=bootstrap_metrics(test_rows,ytest,raw_pred,yfit,classes,direction=direction,endpoint=f'task:{task}',seed=int(analysis['seed']))
 incboot=bootstrap_metrics(test_rows,ytest,combined_pred,yfit,classes,direction=direction,endpoint=f'incremental:{task}',seed=int(analysis['seed']),other_pred=nuisance_pred)
 result={'task':task,'direction':direction,'rows_fit':len(fit_rows),'rows_heldout':len(test_rows),'classes':list(classes),'selected_alpha':{'raw':raw_alpha,'nuisance':nuisance_alpha,'combined':combined_alpha},'alpha_grid':{'raw':raw_grid,'nuisance':nuisance_grid,'combined':combined_grid},'raw_macro_f1':f,'balanced_accuracy':balanced_accuracy(ytest,raw_pred,classes),'chance_macro_f1':chance,'normalized_recovery':normalized_recovery(f,chance),'normalized_recovery_interval':boot['normalized_recovery'],'incremental_f1':inc,'incremental_interval':incboot['paired_f1_difference'],'eligible':boot['normalized_recovery']['finite']>=490 and incboot['paired_f1_difference']['finite']>=490,'raw_signal_pass':normalized_recovery(f,chance)>=float(analysis['raw_recovery_min']) and boot['normalized_recovery']['finite']>=490 and boot['normalized_recovery']['lower'] is not None and boot['normalized_recovery']['lower']>0,'incremental_pass':inc>=float(analysis['incremental_f1_min']) and incboot['paired_f1_difference']['finite']>=490 and incboot['paired_f1_difference']['lower'] is not None and incboot['paired_f1_difference']['lower']>0}
 if return_internal:result['_internal']={'rows':test_rows,'yfit':yfit,'ytest':ytest,'pred':raw_pred,'classes':classes}
 return result,raw

def relation_matrix(data:SourceData,rows:Sequence[Mapping[str,Any]],variant:str,projector:np.ndarray|None=None,complement:bool=False)->np.ndarray:
 child=np.asarray([data.x[data.row_index[str(r['child_row_id'])]] for r in rows],dtype=np.float64);head=np.asarray([data.x[data.row_index[str(r['head_row_id'])]] for r in rows],dtype=np.float64);sham=np.asarray([data.x[data.row_index[str(r['sham_row_id'])]] for r in rows],dtype=np.float64)
 if projector is not None:
  p=np.eye(projector.shape[0])-projector if complement else projector;child=child@p;head=head@p;sham=sham@p
 return child if variant=='child' else np.concatenate([child,(head if variant=='true' else sham)-child],axis=1)

def evaluate_relation_direction(fit:SourceData,test:SourceData,task:str,analysis:Mapping[str,Any],projector:np.ndarray|None=None,complement:bool=False,return_internal:bool=False)->dict[str,Any]:
 fr=fit.relations;tr=test.relations;classes=tuple(sorted({r['labels'][task] for r in fr},key=lambda x:x.encode()));heldout_classes={r['labels'][task] for r in tr}
 if len(classes)<2 or heldout_classes!=set(classes):
  return {'direction':f'{fit.source}_to_{test.source}','task':task,'status':'ineligible','reasons':['relation_class_transfer_mismatch'],'fit_classes':list(classes),'heldout_classes':sorted(heldout_classes),'eligible':False,'pass':False}
 yf=np.asarray([r['labels'][task] for r in fr]);yt=np.asarray([r['labels'][task] for r in tr]);folds=np.asarray([fit.main[r['child_row_id']]['fold'] for r in fr]);pred={};scores={};models={}
 for variant in ('child','true','sham'):
  xf=relation_matrix(fit,fr,variant,projector,complement);xt=relation_matrix(test,tr,variant,projector,complement);alpha,grid=choose_alpha(xf,yf,folds,classes,analysis['alphas'],device=analysis['ridge_device'],scale_floor=analysis['scale_floor']);model=fit_ridge(xf,yf,classes,alpha,device=analysis['ridge_device'],scale_floor=analysis['scale_floor']);models[variant]=model;pred[variant]=model.predict(xt);scores[variant]=macro_f1(yt,pred[variant],classes)
 direction=f'{fit.source}_to_{test.source}';a=bootstrap_metrics(tr,yt,pred['true'],yf,classes,direction=direction,endpoint=f'relation-child:{task}',seed=analysis['seed'],other_pred=pred['child'])['paired_f1_difference'];b=bootstrap_metrics(tr,yt,pred['true'],yf,classes,direction=direction,endpoint=f'relation-sham:{task}',seed=analysis['seed'],other_pred=pred['sham'])['paired_f1_difference']
 result={'direction':direction,'task':task,'macro_f1':scores,'true_minus_child':scores['true']-scores['child'],'true_minus_child_interval':a,'true_minus_sham':scores['true']-scores['sham'],'true_minus_sham_interval':b,'eligible':a['finite']>=490 and b['finite']>=490,'pass':scores['true']>scores['child'] and b['finite']>=490 and b['lower'] is not None and b['lower']>0}
 if return_internal:result['_internal']={'rows':tr,'yfit':yf,'ytest':yt,'classes':classes,'pred':pred['true'],'folds':folds}
 return result

def delta_for_pair(data:SourceData,pair:Mapping[str,Any],kind:str)->tuple[np.ndarray,np.ndarray|None]:
 r=pair['rows'];get=lambda row:np.asarray(data.x[data.row_index[str(row)]],dtype=np.float64)
 if kind=='relative_gap':return get(r['relative_gap']['post'])-get(r['bare']['post']),get(r['relative_gap']['pre'])-get(r['bare']['pre'])
 if kind=='true_context':return get(r['true_prefix'])-get(r['unrelated_prefix']),None
 if kind=='unrelated_context':return get(r['unrelated_prefix'])-get(r['separator_only']),None
 if kind=='proper_noun_substitution':return get(r['target']['changed'])-get(r['source']['changed']),get(r['target']['control'])-get(r['source']['control'])
 raise KeyError(kind)

def state_pair_for(data:SourceData,pair:Mapping[str,Any],kind:str)->tuple[np.ndarray,np.ndarray]:
 r=pair['rows'];get=lambda row:np.asarray(data.x[data.row_index[str(row)]],dtype=np.float64)
 if kind=='relative_gap':return get(r['bare']['post']),get(r['relative_gap']['post'])
 if kind=='true_context':return get(r['unrelated_prefix']),get(r['true_prefix'])
 if kind=='unrelated_context':return get(r['separator_only']),get(r['unrelated_prefix'])
 if kind=='proper_noun_substitution':return get(r['source']['changed']),get(r['target']['changed'])
 raise KeyError(kind)

def intervention_atlas(data:SourceData,analysis:Mapping[str,Any])->dict[str,Any]:
 by_class={k:[] for k in INTERVENTION_CLASSES};meta={k:[] for k in INTERVENTION_CLASSES};control={k:[] for k in INTERVENTION_CLASSES};state_pairs={k:[] for k in INTERVENTION_CLASSES}
 for p in data.pairs:
  kinds=['relative_gap'] if p['construct']=='relative_gap' else (['true_context','unrelated_context'] if p['construct']=='context_factorial' else ['proper_noun_substitution'])
  for kind in kinds:
   delta,ctrl=delta_for_pair(data,p,kind);by_class[kind].append(delta);meta[kind].append(p);state_pairs[kind].append(state_pair_for(data,p,kind))
   if ctrl is not None:control[kind].append(ctrl)
 out={};bases={}
 for kind in INTERVENTION_CLASSES:
  d=np.asarray(by_class[kind]);basis,diag=delta_basis(d,int(analysis['delta_basis_rank']),float(analysis['singular_floor']));bases[kind]=basis
  norm=np.linalg.norm(d,axis=1);before=np.asarray([row[0] for row in state_pairs[kind]]);after=np.asarray([row[1] for row in state_pairs[kind]]);den=np.maximum(np.linalg.norm(before,axis=1),float(analysis['scale_floor']));cosden=np.maximum(np.linalg.norm(before,axis=1)*np.linalg.norm(after,axis=1),float(analysis['scale_floor']));cosine=1-np.sum(before*after,axis=1)/cosden;control_norm=np.linalg.norm(np.asarray(control[kind]),axis=1) if control[kind] else None
  out[kind]={'rows':len(d),'mean_delta_norm':float(norm.mean()),'median_delta_norm':float(np.median(norm)),'mean_relative_l2':float(np.mean(norm/den)),'median_relative_l2':float(np.median(norm/den)),'mean_cosine_distance':float(np.mean(cosine)),'median_cosine_distance':float(np.median(cosine)),'delta_basis':diag,'raw_delta_covariance_spectrum':raw_delta_covariance_spectrum(d),'control_mean_norm':float(control_norm.mean()) if control_norm is not None else None,'mean_target_minus_control_norm':float(np.mean(norm-control_norm)) if control_norm is not None else None,'mean_adjusted_target_minus_control_vector_norm':float(np.mean(np.linalg.norm(d-np.asarray(control[kind]),axis=1))) if control_norm is not None else None}
 return {'summaries':out,'deltas':by_class,'metadata':meta,'bases':bases}

def cross_family_direction(fit:SourceData,test:SourceData,fit_atlas:Mapping[str,Any],test_atlas:Mapping[str,Any],analysis:Mapping[str,Any])->dict[str,Any]:
 def build(data:SourceData,atlas:Mapping[str,Any]):
  pair={p['pair_id']:p for p in data.pairs};deltas=[];nuis=[]
  for r in data.cross:
   d,_=delta_for_pair(data,pair[r['pair_id']],r['class_label']);deltas.append(d);s=dict(r['stratum']);s['joint']='|'.join(s[k] for k in ('start_distance','upos_coarse','capitalization','word_length'));nuis.append(s)
  return row_normalize(np.asarray(deltas)),np.asarray([r['class_label'] for r in data.cross]),nuis
 xf,yf,nf=build(fit,fit_atlas);xt,yt,nt=build(test,test_atlas);classes=INTERVENTION_CLASSES;folds=np.asarray([r['fold'] for r in fit.cross]);cols=('start_distance','upos_coarse','capitalization','word_length','joint');enc=CategoricalEncoder.fit(nf,cols);nfx=enc.transform(nf);ntx=enc.transform(nt)
 nalpha,ngrid=choose_alpha(nfx,yf,folds,classes,analysis['alphas'],device=analysis['ridge_device']);nmodel=fit_ridge(nfx,yf,classes,nalpha,device=analysis['ridge_device']);npred=nmodel.predict(ntx);cf=np.concatenate([xf,nfx],1);ct=np.concatenate([xt,ntx],1);calpha,cgrid=choose_alpha(cf,yf,folds,classes,analysis['alphas'],device=analysis['ridge_device']);cmodel=fit_ridge(cf,yf,classes,calpha,device=analysis['ridge_device']);cpred=cmodel.predict(ct);direction=f'{fit.source}_to_{test.source}';full_inc=macro_f1(yt,cpred,classes)-macro_f1(yt,npred,classes)
 fit_cells={r['joint'] for r in nf};common=np.asarray([r['joint'] in fit_cells for r in nt]);common_inc=macro_f1(yt[common],cpred[common],classes)-macro_f1(yt[common],npred[common],classes)
 documents=sorted({d for r in test.cross for d in (r['document_group'],r.get('donor_document_group')) if d},key=lambda x:x.encode());improvements=[];recoveries={c:[] for c in classes}
 for draw in range(500):
  mult=bootstrap_component_multiplicities(documents,direction=direction,endpoint='cross_family_specificity',draw=draw,seed=analysis['seed']);w=pooled_document_row_weights(test.cross,mult);improvements.append(macro_f1(yt,cpred,classes,w)-macro_f1(yt,npred,classes,w))
  if any(w[yt==c].sum()<=0 for c in classes):
   improvements[-1]=float('nan')
   for c in classes:recoveries[c].append(float('nan'))
   continue
  for c in classes:
   binary=np.where(yt==c,c,'__OTHER__');bp=np.where(cpred==c,c,'__OTHER__');recoveries[c].append(normalized_recovery(macro_f1(binary,bp,(c,'__OTHER__'),w),prior_chance(np.where(yf==c,c,'__OTHER__'),binary,(c,'__OTHER__'),w)))
 point_recovery={}
 for c in classes:
  binary=np.where(yt==c,c,'__OTHER__');bp=np.where(cpred==c,c,'__OTHER__');point_recovery[c]=normalized_recovery(macro_f1(binary,bp,(c,'__OTHER__')),prior_chance(np.where(yf==c,c,'__OTHER__'),binary,(c,'__OTHER__')))
 improvement_interval=interval(improvements);class_intervals={c:interval(recoveries[c]) for c in classes};eligible=improvement_interval['finite']>=490 and all(class_intervals[c]['finite']>=490 for c in classes)
 return {'direction':direction,'macro_f1':macro_f1(yt,cpred,classes),'nuisance_macro_f1':macro_f1(yt,npred,classes),'incremental_f1':full_inc,'incremental_interval':improvement_interval,'common_subset_rows':int(common.sum()),'common_subset_incremental_f1':common_inc,'common_subset_same_positive_sign':full_inc>0 and common_inc>0,'class_normalized_recovery':{c:{'point':point_recovery[c],'interval':class_intervals[c]} for c in classes},'selected_alpha':{'nuisance':nalpha,'combined':calpha},'eligible':eligible,'pass':eligible and full_inc>=analysis['incremental_f1_min'] and improvement_interval['lower'] is not None and improvement_interval['lower']>0 and common_inc>0 and all(point_recovery[c]>=analysis['raw_recovery_min'] and class_intervals[c]['lower'] is not None and class_intervals[c]['lower']>0 for c in classes)}

def _projection_record(
    rows: Sequence[Mapping[str, Any]],
    yfit: np.ndarray,
    ytest: np.ndarray,
    classes: Sequence[str],
    raw_pred: np.ndarray,
    p_pred: np.ndarray,
    q_pred: np.ndarray,
    *,
    assigned_to_p: bool,
    direction: str,
    endpoint: str,
    seed: int,
    denominator_floor: float,
) -> dict[str, Any]:
    chance = prior_chance(yfit, ytest, classes)
    raw_f1 = macro_f1(ytest, raw_pred, classes)
    p_f1 = macro_f1(ytest, p_pred, classes)
    q_f1 = macro_f1(ytest, q_pred, classes)
    denominator = raw_f1 - chance
    eligible = bool(np.isfinite(denominator) and denominator > denominator_floor)
    recovery_p = (p_f1 - chance) / denominator if eligible else float("nan")
    recovery_q = (q_f1 - chance) / denominator if eligible else float("nan")
    assigned = recovery_p if assigned_to_p else recovery_q
    leakage = recovery_q if assigned_to_p else recovery_p
    components = sorted({str(row["component_id"]) for row in rows}, key=lambda value: value.encode())
    draws: list[float] = []
    for draw in range(500):
        multiplicities = bootstrap_component_multiplicities(
            components, direction=direction, endpoint=endpoint, draw=draw, seed=seed
        )
        weights = np.asarray(
            [multiplicities.get(str(row["component_id"]), 0) for row in rows], dtype=np.float64
        )
        if any(weights[ytest == class_label].sum() <= 0 for class_label in classes):
            draws.append(float("nan")); continue
        draw_chance = prior_chance(yfit, ytest, classes, weights)
        draw_raw = macro_f1(ytest, raw_pred, classes, weights)
        draw_denominator = draw_raw - draw_chance
        if not np.isfinite(draw_denominator) or draw_denominator <= denominator_floor:
            draws.append(float("nan")); continue
        draw_p = (macro_f1(ytest, p_pred, classes, weights) - draw_chance) / draw_denominator
        draw_q = (macro_f1(ytest, q_pred, classes, weights) - draw_chance) / draw_denominator
        draws.append((draw_p - draw_q) if assigned_to_p else (draw_q - draw_p))
    selectivity_interval = interval(draws)
    return {
        "raw_macro_f1": raw_f1,
        "chance_macro_f1": chance,
        "projected_macro_f1": p_f1,
        "complement_macro_f1": q_f1,
        "recovery_P": recovery_p,
        "recovery_Q": recovery_q,
        "assigned_recovery": assigned,
        "leakage": leakage,
        "selectivity": assigned - leakage,
        "selectivity_interval": selectivity_interval,
        "eligible": eligible and selectivity_interval["finite"] >= 490,
        "_selectivity_draws": draws,
    }


def _projected_task_record(
    fit: SourceData,
    test: SourceData,
    task: str,
    projector: np.ndarray,
    raw_internal: Mapping[str, Any],
    analysis: Mapping[str, Any],
    *,
    assigned_to_p: bool,
    endpoint: str,
) -> dict[str, Any]:
    fit_rows = task_rows(fit, task); test_rows = task_rows(test, task)
    classes = tuple(raw_internal["classes"])
    xfit_p = task_matrix(fit, task, fit_rows, projector, False)
    xtest_p = task_matrix(test, task, test_rows, projector, False)
    xfit_q = task_matrix(fit, task, fit_rows, projector, True)
    xtest_q = task_matrix(test, task, test_rows, projector, True)
    yfit = np.asarray([row["label"] for row in fit_rows], dtype=str)
    ytest = np.asarray([row["label"] for row in test_rows], dtype=str)
    if not np.array_equal(ytest, raw_internal["ytest"]):
        raise RuntimeError(f"projected task held-out row/label drift: {task}")
    folds = np.asarray([
        fit.main[str(row["left_row_id"] if task == "pair_distance" else row["row_id"])]["fold"]
        for row in fit_rows
    ])
    alpha_p, _ = choose_alpha(xfit_p, yfit, folds, classes, analysis["alphas"], device=analysis["ridge_device"], scale_floor=analysis["scale_floor"])
    alpha_q, _ = choose_alpha(xfit_q, yfit, folds, classes, analysis["alphas"], device=analysis["ridge_device"], scale_floor=analysis["scale_floor"])
    pred_p = fit_ridge(xfit_p, yfit, classes, alpha_p, device=analysis["ridge_device"], scale_floor=analysis["scale_floor"]).predict(xtest_p)
    pred_q = fit_ridge(xfit_q, yfit, classes, alpha_q, device=analysis["ridge_device"], scale_floor=analysis["scale_floor"]).predict(xtest_q)
    record = _projection_record(
        test_rows, yfit, ytest, classes, np.asarray(raw_internal["pred"]), pred_p, pred_q,
        assigned_to_p=assigned_to_p, direction=f"{fit.source}_to_{test.source}", endpoint=endpoint,
        seed=int(analysis["seed"]), denominator_floor=float(analysis["raw_denominator_floor"]),
    )
    record["selected_alpha"] = {"P": alpha_p, "Q": alpha_q}
    record["representation"] = "token_or_pair"
    return record


def _projected_relation_record(
    fit: SourceData,
    test: SourceData,
    task: str,
    projector: np.ndarray,
    raw_internal: Mapping[str, Any],
    analysis: Mapping[str, Any],
    *,
    endpoint: str,
) -> dict[str, Any]:
    fit_rows = fit.relations; test_rows = test.relations
    classes = tuple(raw_internal["classes"])
    yfit = np.asarray([row["labels"][task] for row in fit_rows], dtype=str)
    ytest = np.asarray([row["labels"][task] for row in test_rows], dtype=str)
    if not np.array_equal(ytest, raw_internal["ytest"]):
        raise RuntimeError(f"projected relation held-out row/label drift: {task}")
    folds = np.asarray([fit.main[row["child_row_id"]]["fold"] for row in fit_rows])
    xfit_p = relation_matrix(fit, fit_rows, "true", projector, False)
    xtest_p = relation_matrix(test, test_rows, "true", projector, False)
    xfit_q = relation_matrix(fit, fit_rows, "true", projector, True)
    xtest_q = relation_matrix(test, test_rows, "true", projector, True)
    alpha_p, _ = choose_alpha(xfit_p, yfit, folds, classes, analysis["alphas"], device=analysis["ridge_device"], scale_floor=analysis["scale_floor"])
    alpha_q, _ = choose_alpha(xfit_q, yfit, folds, classes, analysis["alphas"], device=analysis["ridge_device"], scale_floor=analysis["scale_floor"])
    pred_p = fit_ridge(xfit_p, yfit, classes, alpha_p, device=analysis["ridge_device"], scale_floor=analysis["scale_floor"]).predict(xtest_p)
    pred_q = fit_ridge(xfit_q, yfit, classes, alpha_q, device=analysis["ridge_device"], scale_floor=analysis["scale_floor"]).predict(xtest_q)
    record = _projection_record(
        test_rows, yfit, ytest, classes, np.asarray(raw_internal["pred"]), pred_p, pred_q,
        assigned_to_p=True, direction=f"{fit.source}_to_{test.source}", endpoint=endpoint,
        seed=int(analysis["seed"]), denominator_floor=float(analysis["raw_denominator_floor"]),
    )
    record["selected_alpha"] = {"P": alpha_p, "Q": alpha_q}
    record["representation"] = "paired_[child,head-child]_block_diagonal_projection"
    return record


def projection_direction(
    fit: SourceData,
    test: SourceData,
    raw_models: Mapping[str, RidgeModel],
    raw_internal: Mapping[str, Any],
    fit_atlas: Mapping[str, Any],
    test_atlas: Mapping[str, Any],
    relation_results: Mapping[str, Any],
    relation_internal: Mapping[str, Any],
    task_results: Mapping[str, Any],
    cross_result: Mapping[str, Any],
    analysis: Mapping[str, Any],
) -> dict[str, Any]:
    weights: dict[str, np.ndarray] = {}
    for task, model in raw_models.items():
        if model.coef.shape[1] != fit.x.shape[1]:
            continue
        block = (model.coef / model.scale[None, :])
        block = block - block.mean(0, keepdims=True)
        norm = np.linalg.norm(block)
        if not np.isfinite(norm) or norm <= float(analysis["singular_floor"]):
            raise RuntimeError(f"rank-zero/non-finite probe block: {task}")
        weights[task] = block / norm
    relation_delta = np.asarray([
        np.asarray(fit.x[fit.row_index[row["head_row_id"]]], dtype=np.float64)
        - np.asarray(fit.x[fit.row_index[row["child_row_id"]]], dtype=np.float64)
        for row in fit.relations
    ])
    test_relation_delta = np.asarray([
        np.asarray(test.x[test.row_index[row["head_row_id"]]], dtype=np.float64)
        - np.asarray(test.x[test.row_index[row["child_row_id"]]], dtype=np.float64)
        for row in test.relations
    ])
    blocks = {
        "sequential": np.concatenate([weights[task] for task in ("start_distance", "relative_quartile")]),
        "syntax_child": np.concatenate([weights[task] for task in SYNTAX_TASKS]),
        "relative_gap": fit_atlas["bases"]["relative_gap"],
        "context": np.concatenate([fit_atlas["bases"]["true_context"], fit_atlas["bases"]["unrelated_context"]], axis=1),
        "relation": delta_basis(relation_delta, int(analysis["delta_basis_rank"]), float(analysis["singular_floor"]))[0],
    }
    organization_groups = PROJECTION_ORGANIZATION_GROUPS
    required_tasks = ("start_distance", "relative_quartile", "pair_distance", "token_identity", *SYNTAX_TASKS)
    measurement_eligible = all(task_results[task].get("eligible") is True for task in required_tasks) and cross_result.get("eligible") is True
    measurement_pass = all(task_results[task]["raw_signal_pass"] and task_results[task]["incremental_pass"] for task in required_tasks) and cross_result.get("pass") is True
    relation_eligible = all(relation_results[task].get("eligible") is True for task in SYNTAX_TASKS)
    relation_pass = all(relation_results[task].get("pass") is True for task in SYNTAX_TASKS)
    output: dict[str, Any] = {}
    for organization, names in analysis["organizations"].items():
        if organization not in organization_groups:
            raise RuntimeError(f"unknown projection organization: {organization}")
        ranks: dict[str, Any] = {}
        ineligible_reasons: list[str] = []
        construct_positive_all_ranks = True
        for rank in analysis["projection_ranks"]:
            try:
                projector, diagnostic = make_projector(
                    [blocks[name] for name in names], int(rank), float(analysis["singular_floor"])
                )
            except ValueError as error:
                ineligible_reasons.append(f"rank_{rank}:{error}"); break
            if diagnostic["rank"] < int(analysis.get("minimum_usable_rank", 8)):
                ineligible_reasons.append(f"rank_{rank}:projector_rank_below_8"); break
            task_records: dict[str, Any] = {}
            construct_records: dict[str, Any] = {}
            for construct, members in organization_groups[organization].items():
                records = []
                for task, kind, assigned_to_p in members:
                    endpoint = f"projection:{organization}:{rank}:{kind}:{task}"
                    if kind == "task":
                        record = _projected_task_record(
                            fit, test, task, projector, raw_internal[task], analysis,
                            assigned_to_p=assigned_to_p, endpoint=endpoint,
                        )
                    else:
                        if task not in relation_internal:
                            record = {"eligible": False, "selectivity": float("nan"), "assigned_recovery": float("nan"), "_selectivity_draws": [float("nan")] * 500}
                        else:
                            record = _projected_relation_record(
                                fit, test, task, projector, relation_internal[task], analysis, endpoint=endpoint
                            )
                    task_records[f"{kind}:{task}"] = record
                    records.append(record)
                draws = [
                    float(np.mean([record["_selectivity_draws"][draw] for record in records]))
                    if all(np.isfinite(record["_selectivity_draws"][draw]) for record in records)
                    else float("nan")
                    for draw in range(500)
                ]
                construct_records[construct] = {
                    "members": [f"{kind}:{task}" for task, kind, _ in members],
                    "assigned_recovery": float(np.mean([record["assigned_recovery"] for record in records])),
                    "selectivity": float(np.mean([record["selectivity"] for record in records])),
                    "selectivity_interval": interval(draws),
                    "eligible": all(record["eligible"] for record in records),
                    "_draws": draws,
                }
            if not all(record["eligible"] for record in construct_records.values()):
                ineligible_reasons.append(f"rank_{rank}:branch_recovery_or_bootstrap_ineligible")
            construct_positive = all(record["selectivity"] > 0 for record in construct_records.values())
            construct_positive_all_ranks = construct_positive_all_ranks and construct_positive
            macro_draws = [
                float(np.mean([record["_draws"][draw] for record in construct_records.values()]))
                if all(np.isfinite(record["_draws"][draw]) for record in construct_records.values())
                else float("nan")
                for draw in range(500)
            ]
            captures: dict[str, Any] = {}
            capture_margins: dict[str, Any] = {}
            capture_deltas = {kind: np.asarray(test_atlas["deltas"][kind]) for kind in INTERVENTION_CLASSES}
            capture_deltas["relation"] = test_relation_delta
            capture_metadata = {kind: test_atlas["metadata"][kind] for kind in INTERVENTION_CLASSES}
            capture_metadata["relation"] = test.relations
            for kind, delta in capture_deltas.items():
                total = np.sum(delta * delta, axis=1)
                if np.any(total <= float(analysis["singular_floor"])):
                    ineligible_reasons.append(f"rank_{rank}:{kind}_zero_delta")
                    capture = np.full(len(delta), np.nan)
                else:
                    capture = np.sum((delta @ projector) ** 2, axis=1) / total
                captures[kind] = {"P": float(np.mean(capture)), "Q": float(np.mean(1 - capture))}
            if int(rank) == int(analysis["primary_rank"]):
                all_documents = sorted({
                    document
                    for kind in capture_metadata
                    for row in capture_metadata[kind]
                    for document in (row["document_group"], row.get("donor_document_group"))
                    if document
                }, key=lambda value: value.encode())
                capture_values = {}
                for kind, delta in capture_deltas.items():
                    total = np.sum(delta * delta, axis=1)
                    capture_values[kind] = np.sum((delta @ projector) ** 2, axis=1) / total
                for kind in capture_deltas:
                    role = PROJECTION_CAPTURE_ROLES[organization][kind]
                    if role not in {"P", "Q"}:
                        capture_margins[kind] = {"finite": 0, "lower": None, "upper": None, "role": f"{role}_diagnostic"}
                        continue
                    assigned_p = role == "P"
                    controls = list(projection_capture_controls(organization, kind))
                    values: list[float] = []
                    for draw in range(500):
                        multiplicities = bootstrap_component_multiplicities(
                            all_documents, direction=f"{fit.source}_to_{test.source}",
                            endpoint=f"projection-capture:{organization}:{kind}", draw=draw, seed=int(analysis["seed"]),
                        )
                        own_weights = pooled_document_row_weights(capture_metadata[kind], multiplicities)
                        own = capture_values[kind] if assigned_p else 1 - capture_values[kind]
                        if own_weights.sum() <= 0:
                            values.append(float("nan")); continue
                        own_mean = float(np.average(own, weights=own_weights))
                        other_means = []
                        for control in controls:
                            control_weights = pooled_document_row_weights(capture_metadata[control], multiplicities)
                            control_values = capture_values[control] if assigned_p else 1 - capture_values[control]
                            if control_weights.sum() > 0:
                                other_means.append(float(np.average(control_values, weights=control_weights)))
                        values.append(own_mean - max(other_means) if other_means else float("nan"))
                    capture_margins[kind] = interval(values)
            serial_tasks = {}
            for key, record in task_records.items():
                serial_tasks[key] = {name: value for name, value in record.items() if not name.startswith("_")}
            serial_constructs = {}
            for key, record in construct_records.items():
                serial_constructs[key] = {name: value for name, value in record.items() if not name.startswith("_")}
            ranks[str(rank)] = {
                "projector": diagnostic,
                "tasks": serial_tasks,
                "constructs": serial_constructs,
                "captures": captures,
                "capture_margin_intervals": capture_margins,
                "macro_assigned_recovery": float(np.mean([record["assigned_recovery"] for record in construct_records.values()])),
                "macro_selectivity": float(np.mean([record["selectivity"] for record in construct_records.values()])),
                "macro_selectivity_interval": interval(macro_draws),
                "all_construct_selectivities_positive": construct_positive,
            }
        if not measurement_eligible:
            ineligible_reasons.append("required_task_or_cross_family_endpoint_ineligible")
        if not relation_eligible:
            ineligible_reasons.append("required_relation_endpoint_ineligible")
        primary = ranks.get(str(analysis["primary_rank"]))
        if primary is None:
            ineligible_reasons.append("primary_rank_unavailable")
        required_capture_rows = [] if primary is None else [
            row for kind,row in primary["capture_margin_intervals"].items()
            if PROJECTION_CAPTURE_ROLES[organization][kind] in {"P","Q"}
        ]
        capture_lcb = bool(required_capture_rows) and all(
            row["finite"] >= 490 and row["lower"] is not None and row["lower"] > 0
            for row in required_capture_rows
        )
        macro_selectivity_lcb = bool(primary) and primary["macro_selectivity_interval"]["finite"] >= 490 and primary["macro_selectivity_interval"]["lower"] is not None and primary["macro_selectivity_interval"]["lower"] > 0
        relation_requirement = (not relation_pass) if organization == "broad_position_vs_lexical" else relation_pass
        passed = bool(
            not ineligible_reasons and measurement_pass and relation_requirement and primary
            and primary["macro_assigned_recovery"] >= float(analysis["assigned_recovery_min"])
            and macro_selectivity_lcb and capture_lcb and construct_positive_all_ranks
        )
        status = "ineligible" if ineligible_reasons else ("passed" if passed else "eligible_not_passed")
        output[organization] = {
            "ranks": ranks,
            "required_measurements_eligible": measurement_eligible,
            "required_measurements_pass": measurement_pass,
            "relation_requirement_pass": relation_requirement,
            "rank_sensitivity_construct_sign_pass": construct_positive_all_ranks,
            "macro_selectivity_lcb_pass": macro_selectivity_lcb,
            "capture_lcb_pass": capture_lcb,
            "status": status,
            "ineligible_reasons": sorted(set(ineligible_reasons)),
        }
    return output

def _configure_analysis_runtime(analysis: Mapping[str, Any]) -> None:
    device = torch.device(str(analysis["ridge_device"]))
    if device.type != "cuda" or not torch.cuda.is_available():
        raise RuntimeError("attempt7 frozen ridge analysis requires its pinned CUDA device")
    if _gpu_uuid(device) != str(analysis["ridge_gpu_uuid"]):
        raise RuntimeError("analysis GPU UUID differs from frozen config")
    if os.environ.get("CUBLAS_WORKSPACE_CONFIG") != ":4096:8":
        raise RuntimeError("analysis CUBLAS workspace configuration drift")
    torch.use_deterministic_algorithms(True)
    torch.backends.cuda.matmul.allow_tf32 = False
    torch.backends.cudnn.allow_tf32 = False

def _prescore_task_eligible(manifest: Mapping[str, Any], task: str) -> bool:
    if task == "lemma_identity":
        return True
    return all(manifest["sources"][source]["support"][task]["status"] == "eligible" for source in ("EWT", "GUM"))


def run(config_path: Path) -> dict[str, Any]:
    config, prescore, manifest = load_scoring_config(config_path)
    analysis = config["analysis"]
    _configure_analysis_runtime(analysis)
    sources = {source: load_source(config, prescore, manifest, source) for source in ("EWT", "GUM")}
    directions = (("EWT", "GUM"), ("GUM", "EWT"))
    task_results: dict[str, Any] = {}; raw_models: dict[str, Any] = {}; raw_internal: dict[str, Any] = {}
    for fit_source, test_source in directions:
        key = f"{fit_source}_to_{test_source}"
        task_results[key] = {}; raw_models[key] = {}; raw_internal[key] = {}
        for task in TASKS:
            if not _prescore_task_eligible(manifest, task):
                task_results[key][task] = {
                    "task": task, "direction": key, "status": "ineligible",
                    "eligible": False, "raw_signal_pass": False, "incremental_pass": False,
                    "reasons": ["prescore_screen_ineligible"],
                }
                continue
            try:
                result, model = evaluate_direction(
                    sources[fit_source], sources[test_source], task, analysis, return_internal=True
                )
            except ValueError as error:
                task_results[key][task] = {
                    "task": task, "direction": key, "status": "ineligible",
                    "eligible": False, "raw_signal_pass": False, "incremental_pass": False,
                    "reasons": [f"fit_or_metric_ineligible:{error}"],
                }
                continue
            raw_internal[key][task] = result.pop("_internal")
            result["status"] = "eligible" if result.get("eligible") is True else "ineligible"
            task_results[key][task] = result; raw_models[key][task] = model
    relation: dict[str, Any] = {}; relation_internal: dict[str, Any] = {}
    for fit_source, test_source in directions:
        key = f"{fit_source}_to_{test_source}"; relation[key] = {}; relation_internal[key] = {}
        for task in SYNTAX_TASKS:
            try:
                result = evaluate_relation_direction(
                    sources[fit_source], sources[test_source], task, analysis, return_internal=True
                )
            except ValueError as error:
                result = {
                    "direction": key, "task": task, "status": "ineligible", "eligible": False,
                    "pass": False, "reasons": [f"fit_or_metric_ineligible:{error}"],
                }
            internal = result.pop("_internal", None)
            if internal is not None:
                relation_internal[key][task] = internal
                result["status"] = "eligible"
            relation[key][task] = result
    interventions = {source: intervention_atlas(sources[source], analysis) for source in ("EWT", "GUM")}
    cross: dict[str, Any] = {}
    for fit_source, test_source in directions:
        key = f"{fit_source}_to_{test_source}"
        cross[key] = cross_family_direction(
            sources[fit_source], sources[test_source], interventions[fit_source], interventions[test_source], analysis
        )
    overlap: dict[str, Any] = {}
    for kind in INTERVENTION_CLASSES:
        within = basis_overlap(interventions["EWT"]["bases"][kind], interventions["GUM"]["bases"][kind])
        cross_rows = []
        for other in INTERVENTION_CLASSES:
            if other == kind:
                continue
            cross_rows.append({
                "other": other,
                "mean_reverse_symmetric": float(np.mean([
                    basis_overlap(interventions["EWT"]["bases"][kind], interventions["GUM"]["bases"][other]),
                    basis_overlap(interventions["GUM"]["bases"][kind], interventions["EWT"]["bases"][other]),
                ])),
            })
        maximum = max(row["mean_reverse_symmetric"] for row in cross_rows)
        overlap[kind] = {"within": within, "cross": cross_rows, "max_cross": maximum, "pass": within > maximum}
    projections: dict[str, Any] = {}
    primary_needed = {"start_distance", "relative_quartile", "token_identity", *SYNTAX_TASKS}
    for fit_source, test_source in directions:
        key = f"{fit_source}_to_{test_source}"
        if not primary_needed.issubset(raw_models[key]) or not set(SYNTAX_TASKS).issubset(relation_internal[key]):
            projections[key] = {
                organization: {"status": "ineligible", "ineligible_reasons": ["required_raw_or_relation_model_unavailable"], "ranks": {}}
                for organization in analysis["organizations"]
            }
        else:
            projections[key] = projection_direction(
                sources[fit_source], sources[test_source], raw_models[key], raw_internal[key],
                interventions[fit_source], interventions[test_source], relation[key], relation_internal[key],
                task_results[key], cross[key], analysis,
            )
    specificity_complete = all(row["pass"] for row in overlap.values())
    statuses: dict[str, str] = {}
    for organization in analysis["organizations"]:
        direction_statuses = [projections[key][organization]["status"] for key in projections]
        if "ineligible" in direction_statuses:
            statuses[organization] = "ineligible"
        elif specificity_complete and all(status == "passed" for status in direction_statuses):
            statuses[organization] = "passed"
        else:
            statuses[organization] = "eligible_not_passed"
    technical_failure=False
    outcome = terminal_outcome(statuses, technical_failure=technical_failure)
    verified_inventory = {source: sources[source].verified_inventory for source in sources}
    qa_envelopes = {
        source: _verify_qa(ROOT / str(prescore["run_root"]) / "numerical_qa" / source / "QA_COMPLETE.json", config, source)
        for source in sources
    }
    qa_summary = {
        source: {
            "qa_complete_sha256": sha256_file(ROOT / str(prescore["run_root"]) / "numerical_qa" / source / "QA_COMPLETE.json"),
            "tolerance": qa_envelopes[source]["payload"]["tolerance"],
            "panels": qa_envelopes[source]["payload"]["panels"],
        }
        for source in sources
    }
    qa_family_for_intervention={
        "relative_gap":"uniform_shift",
        "true_context":"prefix_position_only",
        "unrelated_context":"prefix_position_only",
        "proper_noun_substitution":None,
    }
    serial_interventions={}
    for source in interventions:
        summaries=interventions[source]["summaries"]
        for kind,summary in summaries.items():
            family=qa_family_for_intervention[kind]
            stats=[
                stat
                for panel in qa_summary[source]["panels"].values()
                for candidate_family,stat in panel.items()
                if family is None or candidate_family==family
            ]
            summary["numerical_noop_error"]={
                "status":"PASS",
                "qa_family":family,
                "applicability":"intervention_family_matched" if family is not None else "global_technical_only_no_lexical_noop_frozen",
                "max_abs_error":max(float(stat["max_abs_error"]) for stat in stats),
                "max_bound_ratio":max(float(stat["max_bound_ratio"]) for stat in stats),
                "qa_complete_sha256":qa_summary[source]["qa_complete_sha256"],
            }
        serial_interventions[source]={"summaries":summaries}
    result = {
        "schema_version": "atlas_discovery_v3_3_attempt7_result_v2",
        "status": "COMPLETE",
        "outcome": outcome,
        "technical_failure":technical_failure,
        "technical_failure_reasons":[],
        "candidate_statuses": statuses,
        "task_results": task_results,
        "relational_advantage": relation,
        "numerical_null_qa": qa_summary,
        "interventions": serial_interventions,
        "cross_family_specificity": cross,
        "delta_basis_overlap": overlap,
        "projections": projections,
        "lineage": {
            "scoring_config_sha256": config["_resolved_sha256"],
            "prescore_config_sha256": config["prescore_config"]["sha256"],
            "prepared_manifest_sha256": config["prepared_manifest_sha256"],
            "verified_analysis_child_inventory": verified_inventory,
            "qa_complete_sha256": {source: qa_summary[source]["qa_complete_sha256"] for source in sources},
            "activation_complete_sha256": {
                source: sha256_file(ROOT / str(prescore["run_root"]) / "activations" / source / "COMPLETE.json")
                for source in sources
            },
        },
        "neural_training_run": False,
        "environment": {
            "python": platform.python_version(), "numpy": np.__version__, "torch": torch.__version__,
            "ridge_device": analysis["ridge_device"], "ridge_gpu_uuid": _gpu_uuid(torch.device(analysis["ridge_device"])),
            "gpu_name": torch.cuda.get_device_name(torch.device(analysis["ridge_device"])),
            "cuda": torch.version.cuda, "cudnn": torch.backends.cudnn.version(),
            "cublas_workspace_config": os.environ["CUBLAS_WORKSPACE_CONFIG"],
            "deterministic_algorithms": torch.are_deterministic_algorithms_enabled(), "tf32": False,
        },
    }
    return json_safe(result)

def technical_ineligible_result(config_path:Path,error:BaseException)->dict[str,Any]:
    raw=json.loads(config_path.read_text())
    scoring_sha=sha256_file(config_path)
    statuses={str(name):"ineligible" for name in raw.get("analysis",{}).get("organizations",{})}
    reason={"type":type(error).__name__,"message":str(error)}
    return json_safe({
        "schema_version":"atlas_discovery_v3_3_attempt7_result_v2",
        "status":"TERMINAL_TECHNICALLY_INELIGIBLE",
        "outcome":terminal_outcome(statuses,technical_failure=True),
        "candidate_statuses":statuses,
        "technical_failure":True,
        "technical_failure_reasons":[reason],
        "task_results":{},"relational_advantage":{},"numerical_null_qa":{},
        "interventions":{},"cross_family_specificity":{},"delta_basis_overlap":{},"projections":{},
        "lineage":{
            "scoring_config_sha256":scoring_sha,
            "prescore_config_sha256":raw.get("prescore_config",{}).get("sha256"),
            "prepared_manifest_sha256":raw.get("prepared_manifest_sha256"),
        },
        "neural_training_run":False,
        "environment":{
            "python":platform.python_version(),"numpy":np.__version__,"torch":torch.__version__,
            "cublas_workspace_config":os.environ.get("CUBLAS_WORKSPACE_CONFIG"),
        },
    })

def _render_markdown(result: Mapping[str, Any]) -> str:
    def fmt(value:Any)->str:
        return "NA" if value is None else (f"{value:.6g}" if isinstance(value,(int,float)) and not isinstance(value,bool) else str(value))
    lines = [
        "# Atlas v3.3 attempt 7 discovery atlas", "",
        f"- Outcome: `{result['outcome']}`",
        "- Scope: reused-public exploratory discovery; no learned architecture is authorized.",
        "- Neural training run: `false`", "",
        "## Candidate organizations", "",
        "| organization | status |", "|---|---|",
    ]
    lines.extend(f"| `{name}` | `{status}` |" for name, status in result["candidate_statuses"].items())
    if result.get("technical_failure"):
        lines.extend(["", "## Technical ineligibility", ""])
        lines.extend(f"- `{row['type']}`: {row['message']}" for row in result.get("technical_failure_reasons",[]))
    lines.extend(["", "## Numerical null QA", "", "| source | panel | family | status | rows | max abs error | max bound ratio |", "|---|---|---|---:|---:|---:|---:|"])
    for source,qa in result.get("numerical_null_qa",{}).items():
        for panel,families in qa["panels"].items():
            for family,row in families.items():
                lines.append(f"| `{source}` | `{panel}` | `{family}` | `{row['status']}` | {row['rows']} | {fmt(row['max_abs_error'])} | {fmt(row['max_bound_ratio'])} |")
    lines.extend(["", "## Cross-corpus task atlas", ""])
    for direction, tasks in result["task_results"].items():
        lines.extend([f"### {direction}", "", "| task | eligibility | raw recovery | incremental F1 |", "|---|---:|---:|---:|"])
        for task, row in tasks.items():
            lines.append(
                f"| `{task}` | `{row.get('status', 'eligible')}` | "
                f"{row.get('normalized_recovery', 'NA')} | {row.get('incremental_f1', 'NA')} |"
            )
        lines.append("")
    lines.extend(["## Relational advantages", "", "| direction | task | eligible | pass | true-child | true-sham |", "|---|---|---:|---:|---:|---:|"])
    for direction,tasks in result.get("relational_advantage",{}).items():
        for task,row in tasks.items():
            lines.append(f"| `{direction}` | `{task}` | `{row.get('eligible')}` | `{row.get('pass')}` | {fmt(row.get('true_minus_child'))} | {fmt(row.get('true_minus_sham'))} |")
    lines.extend(["", "## Cross-family predictive specificity", "", "| direction | eligible | pass | incremental F1 | interval | common rows | common incremental F1 |", "|---|---:|---:|---:|---|---:|---:|"])
    for direction,row in result.get("cross_family_specificity",{}).items():
        interval_row=row.get("incremental_interval",{})
        interval_text=f"[{fmt(interval_row.get('lower'))}, {fmt(interval_row.get('upper'))}], finite={interval_row.get('finite')}"
        lines.append(f"| `{direction}` | `{row.get('eligible')}` | `{row.get('pass')}` | {fmt(row.get('incremental_f1'))} | {interval_text} | {row.get('common_subset_rows','NA')} | {fmt(row.get('common_subset_incremental_f1'))} |")
    lines.extend(["", "## Delta-basis specificity", "", "| family | within-source-transfer overlap | maximum cross-family overlap | pass |", "|---|---:|---:|---:|"])
    for family,row in result.get("delta_basis_overlap",{}).items():
        lines.append(f"| `{family}` | {fmt(row.get('within'))} | {fmt(row.get('max_cross'))} | `{row.get('pass')}` |")
    lines.extend(["## Intervention fingerprints", ""])
    for source, payload in result["interventions"].items():
        lines.append(f"### {source}")
        for kind, row in payload["summaries"].items():
            lines.append(
                f"- `{kind}`: n={row['rows']}, mean cosine distance={row['mean_cosine_distance']:.6g}, "
                f"mean relative L2={row['mean_relative_l2']:.6g}, basis rank={row['delta_basis']['rank']}, "
                f"raw covariance normalization={row['raw_delta_covariance_spectrum']['normalization']}, "
                f"no-op max error={row['numerical_noop_error']['max_abs_error']:.6g} "
                f"({row['numerical_noop_error']['applicability']})"
            )
        lines.append("")
    lines.extend(["## Projection organizations", ""])
    for direction,organizations in result.get("projections",{}).items():
        lines.extend([f"### {direction}", "", "| organization | status | rank | assigned recovery | selectivity interval | capture gate | rank-sign gate | reasons |", "|---|---|---:|---:|---|---:|---:|---|"])
        for organization,row in organizations.items():
            ranks=row.get("ranks",{})
            if not ranks:
                lines.append(f"| `{organization}` | `{row.get('status')}` | NA | NA | NA | `{row.get('capture_lcb_pass')}` | `{row.get('rank_sensitivity_construct_sign_pass')}` | {', '.join(row.get('ineligible_reasons',[]))} |")
            for rank,rank_row in ranks.items():
                selectivity=rank_row.get("macro_selectivity_interval",{})
                selectivity_text=f"[{fmt(selectivity.get('lower'))}, {fmt(selectivity.get('upper'))}], finite={selectivity.get('finite')}"
                lines.append(f"| `{organization}` | `{row.get('status')}` | {rank} | {fmt(rank_row.get('macro_assigned_recovery'))} | {selectivity_text} | `{row.get('capture_lcb_pass')}` | `{row.get('rank_sensitivity_construct_sign_pass')}` | {', '.join(row.get('ineligible_reasons',[]))} |")
        lines.append("")
    lines.extend([
        "## Interpretation boundary", "",
        "This atlas nominates at most one later confirmatory question. It is not confirmation, "
        "does not demonstrate a learned decomposition, and does not authorize neural training.", "",
    ])
    return "\n".join(lines)


def _analysis_inventory(root: Path) -> dict[str, dict[str, Any]]:
    return {
        path.name: {"sha256": sha256_file(path), "bytes": path.stat().st_size}
        for path in sorted(root.iterdir()) if path.is_file() and path.name != "COMPLETE.json"
    }


def _verify_analysis_bundle(root: Path, scoring_sha: str) -> dict[str, Any]:
    expected = {"COMPLETE.json", "result.json", "report.md", "lineage.json", "RERUN.txt"}
    entries=list(root.iterdir())
    if {path.name for path in entries} != expected or any(not path.is_file() or path.is_symlink() for path in entries):
        raise RuntimeError("analysis bundle allowlist drift")
    complete = json.loads((root / "COMPLETE.json").read_text())
    valid_statuses={"COMPLETE","TERMINAL_TECHNICALLY_INELIGIBLE"}
    if complete.get("schema_version") != "atlas_discovery_v3_3_attempt7_analysis_complete_v2" or complete.get("status") not in valid_statuses or complete.get("scoring_config_sha256") != scoring_sha or complete.get("neural_training_run") is not False:
        raise RuntimeError("analysis completion identity drift")
    if complete.get("artifacts") != _analysis_inventory(root):
        raise RuntimeError("analysis completion inventory drift")
    result = json.loads((root / "result.json").read_text())
    if result.get("lineage", {}).get("scoring_config_sha256") != scoring_sha or result.get("neural_training_run") is not False:
        raise RuntimeError("analysis result lineage drift")
    if complete["status"]=="TERMINAL_TECHNICALLY_INELIGIBLE" and (result.get("outcome")!="technically_ineligible" or result.get("technical_failure") is not True):
        raise RuntimeError("analysis technical terminal drift")
    lineage = json.loads((root / "lineage.json").read_text())
    if lineage != result["lineage"]:
        raise RuntimeError("analysis lineage sidecar drift")
    return complete


def main() -> None:
    parser = argparse.ArgumentParser(); parser.add_argument("--config", default="configs/atlas_discovery_v3_3/scoring.json"); args = parser.parse_args()
    config_path = (ROOT / args.config).resolve(strict=True); raw_config = json.loads(config_path.read_text())
    out = ROOT / raw_config["analysis"]["output_path"]; run_root = ROOT / json.loads((ROOT / raw_config["prescore_config"]["path"]).read_text())["run_root"]
    scoring_sha = sha256_file(config_path)
    with _exclusive_lock(run_root, "analysis-global"):
        if out.exists():
            complete = _verify_analysis_bundle(out, scoring_sha); print(json.dumps(complete, indent=2, sort_keys=True)); return
        stage = _new_staging(run_root, "analysis", scoring_sha); started = time.time()
        try:
            result = run(config_path)
        except (RuntimeError,ValueError,FloatingPointError,OSError,np.linalg.LinAlgError) as error:
            result = technical_ineligible_result(config_path,error)
        except Exception as error:
            (stage/"FAILED.json").write_text(json.dumps({
                "schema_version":"atlas_discovery_v3_3_attempt7_analysis_programmer_failure_v1",
                "status":"FAILED_UNHANDLED","scoring_config_sha256":scoring_sha,
                "error":{"type":type(error).__name__,"message":str(error)},
                "neural_training_run":False,
            },indent=2,sort_keys=True)+"\n")
            _fsync_file(stage/"FAILED.json");_fsync_directory(stage)
            raise
        (stage / "result.json").write_text(json.dumps(result, indent=2, sort_keys=True, allow_nan=False) + "\n")
        (stage / "report.md").write_text(_render_markdown(result))
        (stage / "lineage.json").write_text(json.dumps(result["lineage"], indent=2, sort_keys=True) + "\n")
        (stage / "RERUN.txt").write_text(f".venv-atlas/bin/python scripts/analyze_atlas_discovery_v3_3.py --config {args.config}\n")
        complete_status="TERMINAL_TECHNICALLY_INELIGIBLE" if result.get("technical_failure") is True else "COMPLETE"
        complete = {
            "schema_version": "atlas_discovery_v3_3_attempt7_analysis_complete_v2",
            "status": complete_status, "scoring_config_sha256": scoring_sha,
            "outcome": result["outcome"], "elapsed_seconds": time.time() - started,
            "neural_training_run": False, "artifacts": _analysis_inventory(stage),
        }
        (stage / "COMPLETE.json").write_text(json.dumps(complete, indent=2, sort_keys=True) + "\n")
        _verify_analysis_bundle(stage, scoring_sha); _promote(stage, out); complete = _verify_analysis_bundle(out, scoring_sha)
        print(json.dumps(complete, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
