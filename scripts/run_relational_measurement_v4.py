#!/usr/bin/env python3
"""One-shot opened-development measurement-design v4 runner (no model access)."""
from __future__ import annotations

import argparse
from concurrent.futures import ProcessPoolExecutor
import hashlib
import json
import os
from pathlib import Path
import platform
import resource
import sys
import time
from typing import Any,Mapping,Sequence

import numpy as np
import scipy
import sklearn
import transformers
from transformers import AutoTokenizer

from relational_objects_v3 import ROOT, canonical_bytes, exclusive_json, load_json, sha256_file, verify_signed
from scout_relational_objects_v3 import align_sentences, canonical_cap_components as v3_cap, enumerate_by_document as v3_enumerate, load_sentences, match_components as v3_match
from relational_measurement_v4 import design_matrix, diagnostics, enrich, enumerate_pool, match_documents, panel_rows, simulate_panel, support

CONFIG=ROOT/'configs/relational_measurement_v4/run.json'
V3A=ROOT/'reports/provenance/relational_objects_v3_scout_build_a.json'
V3B=ROOT/'reports/provenance/relational_objects_v3_scout_build_b.json'


def verify_identity(config:Mapping[str,Any])->None:
    for name,item in config['identity'].items():
        p=ROOT/item['path']
        if not p.is_file() or sha256_file(p)!=item['sha256']:raise RuntimeError(f'identity drift: {name}:{p}')
    if any(config['permissions'].values()):raise RuntimeError('v4 permissions must all be false')
    if config['namespace']!='relational_measurement_v4_opened_development1':raise RuntimeError('namespace drift')

def stable_cpu_inventory(text:str)->dict[str,Any]:
    stable_keys=('vendor_id','cpu family','model','model name','stepping','microcode','cache size','physical id','core id','siblings','cpu cores','flags','Features','CPU architecture','CPU implementer','CPU part','CPU revision')
    records=[]
    for paragraph in text.split('\n\n'):
        parsed={}
        for line in paragraph.splitlines():
            if ':' in line:
                key,value=(x.strip() for x in line.split(':',1))
                if key in stable_keys:parsed[key]=value
        if parsed:records.append(dict(sorted(parsed.items())))
    if not records:raise RuntimeError('no stable CPU hardware identity available')
    unique=sorted({canonical_bytes(x).decode() for x in records})
    return {'logical_record_count':len(records),'unique_records':[json.loads(x) for x in unique]}

def environment_inventory(config:Mapping[str,Any])->dict[str,Any]:
    cpu=Path('/proc/cpuinfo')
    if not cpu.is_file():raise RuntimeError('supported stable CPU inventory unavailable')
    stable_cpu=stable_cpu_inventory(cpu.read_text())
    return {'python':sys.version,'platform':platform.platform(),'machine':platform.machine(),'processor':platform.processor(),'logical_cpus':os.cpu_count(),'stable_cpu':stable_cpu,'stable_cpu_sha256':hashlib.sha256(canonical_bytes(stable_cpu)).hexdigest(),'numpy':np.__version__,'scipy':scipy.__version__,'scikit_learn':sklearn.__version__,'transformers':transformers.__version__,'tokenizer_name':config['model']['tokenizer_name'],'tokenizer_revision':config['model']['revision'],'blas_threads':config['runtime']['blas_threads'],'pythonhashseed':os.environ.get('PYTHONHASHSEED')}


def exact_reference(config:Mapping[str,Any])->dict[str,Any]:
    if sha256_file(V3A)!=sha256_file(V3B):raise RuntimeError('v3 deterministic reference mismatch')
    a=load_json(V3A);term=load_json(ROOT/config['identity']['v3_terminal']['path'])['payload']
    expected={s:term['sources'][s]['capped'] for s in config['source_selection_order']}
    observed={s:a['sources'][s]['capped'] for s in config['source_selection_order']}
    if canonical_bytes(expected)!=canonical_bytes(observed):raise RuntimeError('v3 terminal/reference support mismatch')
    return {'build_a':{'path':V3A.relative_to(ROOT).as_posix(),'sha256':sha256_file(V3A)},'build_b':{'path':V3B.relative_to(ROOT).as_posix(),'sha256':sha256_file(V3B)},'sources':observed,'byte_identical':True}

def smoke_report(config:Mapping[str,Any],output:Path,config_path:Path=CONFIG)->dict[str,Any]:
    verify_identity(config);ref=exact_reference(config);source='ENGLISH_GENTLE';_,record=source_worker((config,source))
    summary={m:{'support':record['methods'][m]['support'],'truncation':record['methods'][m]['truncation'],'components_sha256':hashlib.sha256(canonical_bytes(record['methods'][m]['components'])).hexdigest()} for m in config['matching']['methods']}
    report={'schema_version':'relational_measurement_v4_smoke_v1','namespace':config['namespace'],'config_sha256':sha256_file(config_path),'reference_sha256':ref['build_a']['sha256'],'source':source,'source_file_hashes':config['sources'][source]['files'],'methods':summary,'method_order':config['matching']['methods'],'dgp_order':config['simulation']['dgps'],'permissions':config['permissions'],'status':'PASS','model_weights_loaded':False,'model_forward_run':False,'fresh_corpus_accessed':False,'training_run':False}
    exclusive_json(output,report);return report


def source_worker(args:tuple[Mapping[str,Any],str])->tuple[str,dict[str,Any]]:
    config,source=args;spec=config['sources'][source]
    paths=[ROOT/x for x in spec['analysis_files']]
    for p in paths:
        rel=p.relative_to(ROOT).as_posix()
        if sha256_file(p)!=spec['files'][rel]:raise RuntimeError(f'source drift: {p}')
    tok=AutoTokenizer.from_pretrained(config['model']['tokenizer_name'],revision=config['model']['revision'],local_files_only=True,use_fast=True)
    loaded=load_sentences(source,paths);sentences,alignment=align_sentences(loaded,tok,config['model']['max_sequence_length']);out={'input_sentences':len(loaded),'alignment':alignment,'methods':{}}
    mc=config['matching'];keys=mc['morph_keys'];vocab=mc['morph_value_vocabulary']
    exact_pool=v3_enumerate(sentences,keys,vocab,mc['coarse_candidate_cap'])
    exact_uncapped=v3_match(source,exact_pool,mc['pairs_per_document_direction'],max(1,len(exact_pool)),2**31-1)
    exact_components=v3_cap(exact_uncapped,mc['maximum_components'],mc['target_pairs'])
    for component in exact_components:
        for field in ('left_positive_pairs','right_positive_pairs'):
            for pair in component[field]:
                for role in ('edge','nonedge'):
                    pair[role]=enrich(pair[role],keys,vocab);pair[role]['source']=source
    exact_support={'source':source,'alignment':alignment,**support(exact_components)}
    exact_support['eligible']=bool(exact_support['components']>=mc['minimum_components'] and exact_support['pairs']>=mc['minimum_pairs'] and all(exact_support['orientations'].get(o,0)>=mc['minimum_pairs_per_orientation'] for o in ('later_query_is_head','later_query_is_child')))
    out['methods']['exact_v3_reference']={'components':exact_components,'support':exact_support,'truncation':{}}
    for method in ('coarse_exact','optimal_caliper'):
        pc=mc['coarse_candidate_cap'] if method=='coarse_exact' else mc['optimal_positive_cap'];nc=mc['coarse_candidate_cap'] if method=='coarse_exact' else mc['optimal_negative_cap']
        pool,trunc=enumerate_pool(sentences,keys,vocab,method,pc,nc);components=match_documents(source,pool,method,mc);out['methods'][method]={'components':components,'support':support(components),'truncation':trunc}
    return source,out


def support_ok(s:Mapping[str,Any],mc:Mapping[str,Any],dc:Mapping[str,Any])->bool:
    required=('components','documents','pairs','orientations','fold_components')
    if any(k not in s for k in required):return False
    counts=[s[k] for k in ('components','documents','pairs')]
    orientations=s['orientations'];folds=s['fold_components']
    if any(isinstance(x,bool) or not isinstance(x,int) or x<0 for x in counts) or not isinstance(orientations,dict) or not isinstance(folds,dict):return False
    if set(orientations)!={'later_query_is_head','later_query_is_child'} or set(folds)!={str(i) for i in range(5)}:return False
    if any(isinstance(x,bool) or not isinstance(x,int) or x<0 for x in [*orientations.values(),*folds.values()]):return False
    if sum(orientations.values())!=s['pairs'] or sum(folds.values())!=s['components']:return False
    return bool(s['components']>=mc['minimum_components'] and s['pairs']>=mc['minimum_pairs'] and all(orientations[o]>=mc['minimum_pairs_per_orientation'] for o in ('later_query_is_head','later_query_is_child')) and min(folds.values())>=dc['minimum_fold_components'])

def select_benchmark_panel(scheduled:Sequence[tuple[str,str]],methods:Mapping[str,Any],config:Mapping[str,Any])->tuple[str,str,dict[str,Any],np.ndarray,list[str],dict[str,int]]:
    candidates=[]
    for index,(method,source) in enumerate(scheduled):
        ref=methods[method]['sources'][source]['panel'];path=Path(ref['path']) if Path(ref['path']).is_absolute() else ROOT/ref['path'];panel=load_json(path)
        X,names=design_matrix(panel['rows'],config['matching']['morph_keys'],config['matching']['morph_value_vocabulary'],config['estimators']['lexical_hash_width'])
        descriptor={'row_count':len(panel['rows']),'feature_count':int(X.shape[1]),'component_count':len(panel['components']),'pair_count':len(panel['pairs']),'row_feature_cells':int(X.shape[0]*X.shape[1]),'component_feature_cells':int(len(panel['components'])*X.shape[1]),'schedule_index':index}
        workload=(descriptor['row_feature_cells'],descriptor['component_feature_cells'],descriptor['feature_count'],descriptor['row_count'],descriptor['component_count'],descriptor['pair_count'],-index)
        candidates.append((workload,method,source,panel,X,names,descriptor))
    if not candidates:raise RuntimeError('no scheduled benchmark panel')
    _,method,source,panel,X,names,descriptor=max(candidates,key=lambda x:x[0])
    return method,source,panel,X,names,descriptor

def validate_benchmark_evidence(benchmark:Mapping[str,Any],config:Mapping[str,Any],expected_scheduled:int|None=None,expected_choice:tuple[str,str,Mapping[str,Any]]|None=None)->None:
    if not isinstance(benchmark,dict):raise RuntimeError('invalid benchmark schema')
    empty_keys={'scheduled_panels','passed','projected_seconds','peak_rss_bytes','projected_artifact_bytes'}
    scheduled_keys=empty_keys|{'benchmark_method','benchmark_source','benchmark_workload','replicate_seconds','median_replicate_seconds'}
    scheduled=benchmark.get('scheduled_panels')
    if isinstance(scheduled,bool) or not isinstance(scheduled,int) or scheduled<0 or (expected_scheduled is not None and scheduled!=expected_scheduled):raise RuntimeError('invalid benchmark schedule')
    if benchmark.get('passed') is not True:raise RuntimeError('benchmark did not pass exactly')
    if scheduled==0:
        if set(benchmark)!=empty_keys or not isinstance(benchmark['projected_seconds'],float) or benchmark['projected_seconds']!=0.0 or isinstance(benchmark['peak_rss_bytes'],bool) or not isinstance(benchmark['peak_rss_bytes'],int) or benchmark['peak_rss_bytes']!=0 or isinstance(benchmark['projected_artifact_bytes'],bool) or not isinstance(benchmark['projected_artifact_bytes'],int) or benchmark['projected_artifact_bytes']!=0:raise RuntimeError('invalid empty benchmark evidence')
        return
    if set(benchmark)!=scheduled_keys:raise RuntimeError('invalid scheduled benchmark schema')
    if not isinstance(benchmark['benchmark_method'],str) or not isinstance(benchmark['benchmark_source'],str):raise RuntimeError('invalid benchmark panel identity')
    workload=benchmark['benchmark_workload'];workload_keys={'row_count','feature_count','component_count','pair_count','row_feature_cells','component_feature_cells','schedule_index'}
    if not isinstance(workload,dict) or set(workload)!=workload_keys or any(isinstance(workload[k],bool) or not isinstance(workload[k],int) for k in workload_keys):raise RuntimeError('invalid benchmark workload schema')
    if any(workload[k]<=0 for k in workload_keys-{'schedule_index'}) or not 0<=workload['schedule_index']<scheduled or workload['row_feature_cells']!=workload['row_count']*workload['feature_count'] or workload['component_feature_cells']!=workload['component_count']*workload['feature_count']:raise RuntimeError('invalid benchmark workload values')
    if expected_choice is not None:
        method,source,descriptor=expected_choice
        if benchmark['benchmark_method']!=method or benchmark['benchmark_source']!=source or canonical_bytes(workload)!=canonical_bytes(descriptor):raise RuntimeError('benchmark panel is not the largest frozen workload')
    durations=benchmark['replicate_seconds']
    if not isinstance(durations,list) or len(durations)!=5 or any(not isinstance(v,float) or not np.isfinite(v) or v<=0 for v in durations):raise RuntimeError('invalid benchmark durations')
    median=float(__import__('statistics').median(durations));reported_median=benchmark['median_replicate_seconds'];projected=benchmark['projected_seconds']
    if not isinstance(reported_median,float) or not np.isfinite(reported_median) or reported_median<=0 or not isinstance(projected,float) or not np.isfinite(projected) or projected<=0:raise RuntimeError('invalid benchmark timing summary')
    expected_projected=median*config['simulation']['replicates']*scheduled
    if not np.isclose(reported_median,median,rtol=1e-12,atol=1e-12) or not np.isclose(projected,expected_projected,rtol=1e-12,atol=1e-12):raise RuntimeError('inconsistent benchmark timing summary')
    rss=benchmark['peak_rss_bytes'];artifact=benchmark['projected_artifact_bytes']
    if isinstance(rss,bool) or not isinstance(rss,int) or rss<0 or isinstance(artifact,bool) or not isinstance(artifact,int) or artifact<=0:raise RuntimeError('invalid benchmark resource summary')
    expected_pass=projected<=config['runtime']['max_projected_seconds'] and rss<=config['runtime']['max_peak_rss_bytes'] and artifact<=config['runtime']['max_artifact_bytes']
    if benchmark['passed'] is not expected_pass:raise RuntimeError('inconsistent benchmark pass flag')

def validate_prepared_content(config:Mapping[str,Any],prep:Mapping[str,Any],config_path:Path=CONFIG)->None:
    expected_top={'schema_version','namespace','config_sha256','exact_reference','methods','benchmark','model_weights_loaded','model_forward_run','activation_cache_accessed','fresh_corpus_accessed','training_run','environment','smoke'}
    if set(prep)!=expected_top or prep.get('schema_version')!='relational_measurement_v4_prepared_v1' or prep.get('namespace')!=config['namespace'] or prep.get('config_sha256')!=sha256_file(config_path):raise RuntimeError('prepared identity invalid')
    if any(prep.get(k) is not False for k in ('model_weights_loaded','model_forward_run','activation_cache_accessed','fresh_corpus_accessed','training_run')):raise RuntimeError('prepared forbidden flag')
    ref=exact_reference(config)
    if canonical_bytes(prep['exact_reference'])!=canonical_bytes(ref) or canonical_bytes(prep['environment'])!=canonical_bytes(environment_inventory(config)) or prep['smoke'] is not False:raise RuntimeError('prepared provenance invalid')
    derived_selected={};rebuilt={s:source_worker((config,s))[1] for s in config['source_selection_order']}
    for method in config['matching']['methods']:
        block=prep['methods'][method]
        if set(block)!={'sources','eligible_sources','selected_sources'}:raise RuntimeError('prepared method schema invalid')
        if set(block['sources'])!=set(config['source_selection_order']):raise RuntimeError('prepared source coverage invalid')
        eligible=[]
        for source in config['source_selection_order']:
            item=block['sources'][source]
            if set(item)!={'support','support_eligible','diagnostics','real_eligible','panel'} or set(item['panel'])!={'path','sha256'}:raise RuntimeError('prepared source schema invalid')
            path=ROOT/item['panel']['path'] if not Path(item['panel']['path']).is_absolute() else Path(item['panel']['path'])
            if sha256_file(path)!=item['panel']['sha256']:raise RuntimeError('panel hash drift')
            panel=load_json(path)
            if set(panel)!={'source','method','components','rows','pairs','feature_names','alignment','truncation'} or panel.get('source')!=source or panel.get('method')!=method:raise RuntimeError('panel identity invalid')
            rebuilt_method=rebuilt[source]['methods'][method]
            if canonical_bytes(panel['components'])!=canonical_bytes(rebuilt_method['components']) or canonical_bytes(panel['alignment'])!=canonical_bytes(rebuilt[source]['alignment']) or canonical_bytes(panel['truncation'])!=canonical_bytes(rebuilt_method['truncation']) or canonical_bytes(item['support'])!=canonical_bytes(rebuilt_method['support']):raise RuntimeError('panel does not reproduce frozen source/matcher')
            rows,pairs=panel_rows(panel['components'])
            if canonical_bytes(rows)!=canonical_bytes(panel['rows']) or canonical_bytes(pairs)!=canonical_bytes(panel['pairs']):raise RuntimeError('panel rows do not derive from components')
            observed=support(panel['components']);reported=item['support']
            for key in ('components','documents','pairs','orientations','fold_components'):
                if observed[key]!=reported[key]:raise RuntimeError('support does not derive from panel')
            if method=='exact_v3_reference' and canonical_bytes(reported)!=canonical_bytes(ref['sources'][source]):raise RuntimeError('exact reference panel mismatch')
            X,names=design_matrix(rows,config['matching']['morph_keys'],config['matching']['morph_value_vocabulary'],config['estimators']['lexical_hash_width']) if rows else (None,[])
            if canonical_bytes(names)!=canonical_bytes(panel['feature_names']):raise RuntimeError('feature-name drift')
            sok=support_ok(reported,config['matching'],config['diagnostics']);diag=None;real=False
            if sok:
                diag=diagnostics(rows,pairs,X,names,config['diagnostics'],config['estimators'],config['seed']);real=bool(diag['eligible'])
            if item['support_eligible'] is not sok or canonical_bytes(item.get('diagnostics'))!=canonical_bytes(diag) or item['real_eligible'] is not real:raise RuntimeError('diagnostic/eligibility mismatch')
            if real:eligible.append(source)
        if block['eligible_sources']!=eligible or block['selected_sources']!=eligible[:2]:raise RuntimeError('selected source mismatch')
        derived_selected[method]=eligible[:2]
    scheduled=sum(len(derived_selected[m]) for m in ('coarse_exact','optimal_caliper') if len(derived_selected[m])==2)
    if scheduled:
        schedule=[(m,s) for m in ('coarse_exact','optimal_caliper') if len(derived_selected[m])==2 for s in derived_selected[m]]
        method,source,_,_,_,descriptor=select_benchmark_panel(schedule,prep['methods'],config)
        validate_benchmark_evidence(prep['benchmark'],config,scheduled,(method,source,descriptor))
    else:validate_benchmark_evidence(prep['benchmark'],config,0)


def prepare(config:Mapping[str,Any],output:Path,smoke:bool=False,config_path:Path=CONFIG)->dict[str,Any]:
    verify_identity(config);ref=exact_reference(config)
    sources=config['source_selection_order'][:1] if smoke else config['source_selection_order']
    records={}
    workers=1 if smoke else config['runtime']['source_processes']
    with ProcessPoolExecutor(max_workers=workers) as ex:
        for source,record in ex.map(source_worker,[(config,s) for s in sources]):records[source]=record
    methods={method:{'sources':{}} for method in config['matching']['methods']}
    prepared_root=ROOT/config['paths']['prepared_root']
    if prepared_root!=output.parent/'panels':raise RuntimeError('prepared root/config mismatch')
    prepared_root.mkdir(parents=True,exist_ok=False)
    for method in config['matching']['methods']:
        for source in sources:
            rec=records[source]['methods'][method]; rows,pairs=panel_rows(rec['components']); X,names=design_matrix(rows,config['matching']['morph_keys'],config['matching']['morph_value_vocabulary'],config['estimators']['lexical_hash_width']) if rows else (None,[])
            if method=='exact_v3_reference':
                expected=ref['sources'][source]
                if canonical_bytes(rec['support'])!=canonical_bytes(expected):raise RuntimeError(f'exact v3 reference drift: {source}')
            sok=support_ok(rec['support'],config['matching'],config['diagnostics']);diag=None;real=False
            if sok:
                diag=diagnostics(rows,pairs,X,names,config['diagnostics'],config['estimators'],config['seed']);real=bool(diag['eligible'])
            panel={'source':source,'method':method,'components':rec['components'],'rows':rows,'pairs':pairs,'feature_names':names,'alignment':records[source]['alignment'],'truncation':rec['truncation']}
            p=prepared_root/f'{method}__{source}.json';exclusive_json(p,panel)
            methods[method]['sources'][source]={'support':rec['support'],'support_eligible':sok,'diagnostics':diag,'real_eligible':real,'panel':{'path':p.relative_to(ROOT).as_posix() if p.is_relative_to(ROOT) else str(p),'sha256':sha256_file(p)}}
    selected={}
    for method in config['matching']['methods']:
        eligible=[s for s in config['source_selection_order'] if s in methods[method]['sources'] and methods[method]['sources'][s]['real_eligible']]
        methods[method]['eligible_sources']=eligible;methods[method]['selected_sources']=eligible[:2];selected[method]=eligible[:2]
    scheduled=[(m,s) for m in ('coarse_exact','optimal_caliper') if len(selected[m])==2 for s in selected[m]]
    bench={'scheduled_panels':len(scheduled),'passed':True,'projected_seconds':0.0,'peak_rss_bytes':0,'projected_artifact_bytes':0}
    if scheduled:
        m,s,panel,X,names,descriptor=select_benchmark_panel(scheduled,methods,config)
        durations=[]
        for _ in range(5):
            start=time.monotonic();simulate_panel(X,names,panel['rows'],panel['pairs'],m,config,config['seed'],replicates=1);durations.append(time.monotonic()-start)
        elapsed=float(__import__('statistics').median(durations));peak=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024
        projected=elapsed*config['simulation']['replicates']*len(scheduled);panel_bytes=sum(p.stat().st_size for p in prepared_root.glob('*.json'));artifact=panel_bytes+len(scheduled)*len(config['simulation']['dgps'])*3*2048
        bench.update({'benchmark_method':m,'benchmark_source':s,'benchmark_workload':descriptor,'replicate_seconds':durations,'median_replicate_seconds':elapsed,'projected_seconds':projected,'peak_rss_bytes':peak,'projected_artifact_bytes':artifact,'passed':projected<=config['runtime']['max_projected_seconds'] and peak<=config['runtime']['max_peak_rss_bytes'] and artifact<=config['runtime']['max_artifact_bytes']})
    report={'schema_version':'relational_measurement_v4_prepared_v1','namespace':config['namespace'],'config_sha256':sha256_file(config_path),'exact_reference':ref,'methods':methods,'benchmark':bench,'model_weights_loaded':False,'model_forward_run':False,'activation_cache_accessed':False,'fresh_corpus_accessed':False,'training_run':False,'environment':environment_inventory(config),'smoke':smoke}
    exclusive_json(output,report);return report


def simulation_pass(cell:Mapping[str,Any],positive:bool,cfg:Mapping[str,Any])->bool:
    return bool(cell['finite'] and abs(cell['bias'])<=(cfg['positive_max_abs_bias'] if positive else cfg['null_max_abs_bias']) and cfg['coverage_min']<=cell['coverage']<=cfg['coverage_max'] and ((cell['power'] is not None and cell['power']>=cfg['positive_min_power']) if positive else cell['rejection']<=cfg['null_max_rejection']))

def classify_failure(exc:Exception)->str:
    message=str(exc).lower()
    if 'reference' in message:return 'REFERENCE_DRIFT'
    if 'drift' in message or 'authorization' in message:return 'HASH_DRIFT'
    if 'source' in message or 'sentence' in message or 'parser' in message:return 'SOURCE_ERROR'
    if 'nonfinite' in message or 'nan' in message or 'interval' in message:return 'NONFINITE'
    if 'fit' in message or 'converg' in message or 'ridge' in message or 'logistic' in message:return 'FIT_FAILURE'
    if isinstance(exc,(MemoryError,TimeoutError)):return 'RESOURCE_LIMIT'
    return 'UNEXPECTED_EXCEPTION'


def execute(config:Mapping[str,Any],prepared_path:Path,output:Path,nonce:str,authorization:Path,opening:Path,config_path:Path=CONFIG)->dict[str,Any]:
    verify_identity(config);auth=verify_signed(authorization);opened=verify_signed(opening,auth['owner_fingerprint']);prep=load_json(prepared_path)
    if auth['config']['sha256']!=sha256_file(config_path) or auth['prepared']['sha256']!=sha256_file(prepared_path) or opened['authorization_sha256']!=sha256_file(authorization) or opened['nonce']!=nonce:raise RuntimeError('authorization/opening drift')
    if prep['config_sha256']!=sha256_file(config_path):raise RuntimeError('prepared/config invalid')
    validate_benchmark_evidence(prep['benchmark'],config)
    simulations={}
    for method in ('coarse_exact','optimal_caliper'):
        selected=prep['methods'][method]['selected_sources']
        if len(selected)!=2:continue
        simulations[method]={}
        for source in selected:
            item=prep['methods'][method]['sources'][source];p=ROOT/item['panel']['path']
            if sha256_file(p)!=item['panel']['sha256']:raise RuntimeError('panel drift')
            panel=load_json(p);X,names=design_matrix(panel['rows'],config['matching']['morph_keys'],config['matching']['morph_value_vocabulary'],config['estimators']['lexical_hash_width']);simulations[method][source]=simulate_panel(X,names,panel['rows'],panel['pairs'],method,config,config['seed'])
    nomination=None
    for method in config['matching']['methods']:
        selected=prep['methods'][method]['selected_sources']
        if len(selected)!=2 or method not in simulations:continue
        for est in config['estimators']['order']:
            ok=True
            for source in selected:
                for dgp in config['simulation']['dgps']:
                    ok &= simulation_pass(simulations[method][source][dgp][est],dgp.endswith('positive'),config['simulation'])
            if ok:nomination={'matcher':method,'estimator':est,'sources':selected};break
        if nomination:break
    structurally_supported=any(sum(bool(x.get('support_eligible')) for x in prep['methods'][m]['sources'].values())>=2 for m in config['matching']['methods'])
    decision='NOMINATE_MEASUREMENT_DESIGN_FOR_FRESH_PREREGISTRATION' if nomination else 'STOP_MEASUREMENT_DESIGN_UNCALIBRATED' if structurally_supported else 'STOP_MEASUREMENT_DESIGN_UNDER_SUPPORTED'
    result={'schema_version':'relational_measurement_v4_result_v1','namespace':config['namespace'],'owner_nonce':nonce,'config_sha256':sha256_file(config_path),'prepared':{'path':prepared_path.relative_to(ROOT).as_posix(),'sha256':sha256_file(prepared_path)},'decision':decision,'nomination':nomination,'simulations':simulations,'methods':prep['methods'],'benchmark':prep['benchmark'],'model_weights_loaded':False,'model_forward_run':False,'activation_cache_accessed':False,'fresh_corpus_accessed':False,'training_run':False,'learned_model_authorized':False}
    exclusive_json(output,result);return result


def main()->None:
    ap=argparse.ArgumentParser();ap.add_argument('--config',type=Path,default=CONFIG);ap.add_argument('--mode',choices=('smoke','prepare','execute'),required=True);ap.add_argument('--output',type=Path,required=True);ap.add_argument('--prepared',type=Path);ap.add_argument('--nonce');ap.add_argument('--authorization',type=Path);ap.add_argument('--opening',type=Path);a=ap.parse_args();cfg=load_json(a.config)
    try:result=smoke_report(cfg,a.output,a.config) if a.mode=='smoke' else prepare(cfg,a.output,False,a.config) if a.mode=='prepare' else execute(cfg,a.prepared,a.output,a.nonce,a.authorization,a.opening,a.config)
    except Exception as exc:
        if a.mode=='execute':exclusive_json(a.output.parent/'failure.json',{'schema_version':'relational_measurement_v4_failure_v1','namespace':cfg['namespace'],'nonce':a.nonce,'config_sha256':sha256_file(a.config),'authorization_sha256':sha256_file(a.authorization) if a.authorization and a.authorization.is_file() else None,'opening_sha256':sha256_file(a.opening) if a.opening and a.opening.is_file() else None,'reason':classify_failure(exc),'error_type':type(exc).__name__,'message':str(exc),'scientific_result':False})
        raise
    print(json.dumps({k:result.get(k) for k in ('schema_version','decision','nomination','benchmark')},sort_keys=True))
if __name__=='__main__':main()
