from __future__ import annotations
import argparse,ast,copy,hashlib,json,math,os,subprocess,threading,time
from pathlib import Path
import sys
import numpy as np
import pytest
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts'))
import relational_measurement_v4 as measurement
import relational_measurement_v4_lifecycle as lifecycle
from relational_measurement_v4 import _assign_stratum,_quartile,base_weights,caliper_cost,coarse_signature,component_interval,core_signature,diagnostics,finalize_components,optimal_pairs,propensity_diagnostics,replicate_draws,ridge_pair_values,sha256_u64,signed_hash,simulate_panel,smd,treatment_weights,weighted_ks
from relational_measurement_v4_lifecycle import REQUIRED_V4_TESTS,_cell_pass,authorize,keygen,recompute_decision,sign_atomic_closure,sign_exclusive,stop_owner_group,supervise,terminalize,verify_lifecycle_closure,write_receipt
from relational_objects_v3 import load_private_key,sha256_file
from run_relational_measurement_v4 import select_benchmark_panel,stable_cpu_inventory,support_ok,validate_benchmark_evidence,validate_prepared_content
from unittest import mock

def wait_payload(path,attempts=1000,sleep=time.sleep):
    for _ in range(attempts):
        try:return json.loads(path.read_text())['payload']
        except (FileNotFoundError,json.JSONDecodeError,KeyError):sleep(.001)
    raise AssertionError(f'signed payload did not become readable: {path}')


def row(cid,base,orientation='later_query_is_head',morph=('Case=Nom',)*8,gap=2,rq=.3,cf=.4,L=20,cost_form='x'):
    endpoint={'form':cost_form,'lemma':cost_form,'feats':'Case=Nom','upos':'NOUN','is_punct':False,'subtokens':1,'morph':morph,'presence':(True,)*8}
    return {'candidate_id':cid,'base_pair_id':base,'orientation':orientation,'later':dict(endpoint),'earlier':dict(endpoint),'surface_gap':gap,'relative_query':rq,'causal_fraction':cf,'sequence_length':L,'label':1,'child_form':'x','head_form':'y','child_lemma':'x','head_lemma':'y','child_feats':'Case=Nom','head_feats':'Case=Nom','child_upos':'NOUN','head_upos':'NOUN','child_is_punct':False,'head_is_punct':False,'child_positions':[1],'head_positions':[2],'query_index':3,'causal_key_count':4,'source':'S'}

def test_caliper_is_inclusive_and_rejects_morphology_tail():
    a=row('a','a');b=row('b','b',gap=4,rq=.425,cf=.525,L=25)
    assert caliper_cost(a,b,{'morph_hamming':4,'log2_gap':1,'relative_query':.125,'causal_fraction':.125,'relative_length':.25}) is not None
    b['later']['morph']=('Case=Acc',)*8
    assert caliper_cost(a,b,{'morph_hamming':4,'log2_gap':1,'relative_query':.125,'causal_fraction':.125,'relative_length':.25}) is None

def test_quartile_boundaries_and_invalid_values_are_exact():
    assert [_quartile(x) for x in (0,.249999,.25,.5,.75,1)]==[0,0,1,2,3,3]
    for x in (-1e-9,1.000001,float('nan'),float('inf')):
        try:_quartile(x)
        except ValueError:pass
        else:raise AssertionError(f'invalid quartile value accepted: {x}')

def test_coarse_matching_keeps_core_and_presence_but_not_morphology_values():
    a=row('a','a');b=copy.deepcopy(a);b['later']['morph']=('Case=Acc',)*8
    assert core_signature(a)==core_signature(b) and coarse_signature(a)==coarse_signature(b)
    b['later']['presence']=(False,)*8;assert coarse_signature(a)!=coarse_signature(b)
    b=copy.deepcopy(a);b['later']['upos']='VERB';assert core_signature(a)!=core_signature(b)

def test_integer_flow_has_unique_digest_tie_break_and_distance_priority():
    cal={'morph_hamming':4,'log2_gap':1,'relative_query':.125,'causal_fraction':.125,'relative_length':.25}
    ps=[row(f'p{i}',f'pb{i}') for i in range(2)];ns=[row(f'n{j}',f'nb{j}') for j in range(2)]
    for n in ns:n['label']=0
    got=_assign_stratum('S',ps,ns,cal);chosen={(x['edge']['candidate_id'],x['nonedge']['candidate_id']) for x in got}
    cells=sorted(((hashlib.sha256((p['candidate_id']+'|'+n['candidate_id']).encode()).hexdigest(),p['candidate_id'],n['candidate_id']) for p in ps for n in ns))
    ranks={(p,n):r for r,(_,p,n) in enumerate(cells)}
    options=[{('p0','n0'),('p1','n1')},{('p0','n1'),('p1','n0')}]
    expected=min(options,key=lambda z:sum(1<<ranks[x] for x in z))
    assert chosen==expected and len(got)==2

    # One 1e-9 primary-distance quantum dominates every secondary bit.
    ps[0]['relative_query']=0.;ps[1]['relative_query']=2e-9;ns[0]['relative_query']=0.;ns[1]['relative_query']=1e-9
    got2=_assign_stratum('S',ps,ns,cal)
    assert sum(round(x['cost']*1e9) for x in got2)==1

def test_optimal_pool_deduplicates_negative_base_across_orientation_strata():
    e1=row('e1','ep1','later_query_is_head');e2=row('e2','ep2','later_query_is_child')
    n1=row('n1','shared','later_query_is_head');n1['label']=0
    n2=row('n2','shared','later_query_is_child');n2['label']=0
    pool={'p':{'positive':{tuple(['h']):[e1],tuple(['c']):[e2]},'negative':{}},'n':{'positive':{},'negative':{tuple(['h']):[n1],tuple(['c']):[n2]}}}
    got=optimal_pairs('S','p','n',pool,12,{'morph_hamming':4,'log2_gap':1,'relative_query':.125,'causal_fraction':.125,'relative_length':.25})
    assert len(got)==1 and got[0]['nonedge']['base_pair_id']=='shared'

def test_final_cap_preserves_direction_then_fills_stably_and_allocates_folds():
    comps=[]
    for i in range(10):
        pair=lambda p:{'pair_id':p,'edge':{'orientation':'later_query_is_head'},'nonedge':{}}
        comps.append({'component_id':f'c{i:02}','documents':[f'a{i}',f'b{i}'],'pair_count':4,'left_positive_pairs':[pair(f'l{i}a'),pair(f'l{i}b')],'right_positive_pairs':[pair(f'r{i}a'),pair(f'r{i}b')]})
    out=finalize_components(comps,10,25)
    assert sum(x['pair_count'] for x in out)==25
    assert set(x['fold'] for x in out)==set(range(5))
    assert all(x['left_positive_pairs'] and x['right_positive_pairs'] for x in out)

def test_weighted_metrics_and_component_interval():
    x=np.array([0.,1.,0.,1.]);t=np.array([0,0,1,1]);w=np.array([.5,.5,.5,.5])
    assert smd(x,t,w)==0 and weighted_ks(x,t,w)==0
    pairs=[{'component_id':'a'},{'component_id':'a'},{'component_id':'b'},{'component_id':'b'}]
    ci=component_interval(np.array([1.,1.,3.,3.]),pairs)
    assert ci['estimate']==2 and ci['components']==2

def test_signed_hash_canonical_sign_and_width():
    a=signed_hash((('f','x'),('g','y')),128);b=signed_hash((('f','x'),('g','y')),128)
    assert np.array_equal(a,b) and a.shape==(128,) and np.abs(a).sum()==2

def test_config_and_ast_prohibit_model_cuda_fresh_and_training_paths():
    cfg=json.loads((ROOT/'configs/relational_measurement_v4/run.json').read_text())
    assert not any(cfg['permissions'].values())
    for name in ('relational_measurement_v4.py','run_relational_measurement_v4.py'):
        text=(ROOT/'scripts'/name).read_text();tree=ast.parse(text)
        imports={alias.name for node in ast.walk(tree) if isinstance(node,(ast.Import,ast.ImportFrom)) for alias in node.names}
        assert not any(x.startswith(('torch','jax','tensorflow')) for x in imports)
        assert 'AutoModel' not in imports and 'AutoModelForCausalLM' not in imports
        calls=[n.func.attr if isinstance(n.func,ast.Attribute) else n.func.id if isinstance(n.func,ast.Name) else '' for n in ast.walk(tree) if isinstance(n,ast.Call)]
        assert not {'backward','step','forward','save_pretrained'}.intersection(calls)

def _authorization_args(tmp_path,passed=True):
    config=ROOT/'configs/relational_measurement_v4/run.json'
    cfg=json.loads(config.read_text());methods={}
    for m in cfg['matching']['methods']:
        methods[m]={'sources':{},'selected_sources':[]}
        for s in cfg['source_selection_order']:
            panel=tmp_path/f'{m}-{s}.json';panel.write_text('{}');methods[m]['sources'][s]={'panel':{'path':str(panel),'sha256':sha256_file(panel)}}
    prepared=tmp_path/'prepared.json';prepared.write_text(json.dumps({'schema_version':'relational_measurement_v4_prepared_v1','namespace':cfg['namespace'],'config_sha256':sha256_file(config),'benchmark':{'passed':passed,'scheduled_panels':0,'projected_seconds':0.0,'peak_rss_bytes':0,'projected_artifact_bytes':0},'methods':methods},sort_keys=True))
    support={'components':1,'documents':2,'pairs':2,'orientations':{'later_query_is_head':1,'later_query_is_child':1},'fold_components':{'0':1}}
    smoke={'schema_version':'relational_measurement_v4_smoke_v1','status':'PASS','config_sha256':sha256_file(config),'source':'ENGLISH_GENTLE','methods':{m:{'support':support,'truncation':{},'components_sha256':'0'*64} for m in cfg['matching']['methods']},'model_weights_loaded':False,'model_forward_run':False,'fresh_corpus_accessed':False,'training_run':False}
    smoke_a=tmp_path/'a.json';smoke_b=tmp_path/'b.json';raw=json.dumps(smoke,sort_keys=True);smoke_a.write_text(raw);smoke_b.write_text(raw)
    n=cfg['runtime']['minimum_test_count'];names=sorted(REQUIRED_V4_TESTS)+[f't{i}' for i in range(max(0,n-len(REQUIRED_V4_TESTS)))];tests=tmp_path/'tests.xml';tests.write_text(f'<testsuites><testsuite tests="{len(names)}" failures="0" errors="0" skipped="0">'+''.join(f'<testcase name="{name}"/>' for name in names)+'</testsuite></testsuites>');review=tmp_path/'review.md';review.write_text('VERDICT: SHIP\n')
    owner=tmp_path/'owner.pem';supervisor=tmp_path/'supervisor.pem';keygen(owner);keygen(supervisor)
    return argparse.Namespace(config=config,prepared=prepared,output=tmp_path/'authorization.json',owner_key=owner,supervisor_key=supervisor,test_report=tests,smoke_a=smoke_a,smoke_b=smoke_b,candidate_review=review,live_verify=False)

def _authorize(args):
    # Unit lifecycle fixtures are deliberately synthetic; production has no
    # bypass and always invokes the full all-source prepared-content rebuild.
    with mock.patch('run_relational_measurement_v4.validate_prepared_content'):
        authorize(args)

def test_authorization_fails_closed_on_failed_benchmark(tmp_path):
    args=_authorization_args(tmp_path,False)
    try:_authorize(args)
    except RuntimeError as exc:assert 'benchmark' in str(exc)
    else:raise AssertionError('failed benchmark was authorized')
    assert not args.output.exists()

def test_authorization_rejects_shipwreck_prefix_and_static_smoke(tmp_path):
    args=_authorization_args(tmp_path,True);args.candidate_review.write_text('VERDICT: SHIPWRECK\n')
    try:_authorize(args)
    except RuntimeError as exc:assert 'SHIP' in str(exc)
    else:raise AssertionError('SHIPWRECK prefix was accepted')
    assert not args.output.exists()

def test_authorization_binds_prepared_and_prerequisite_evidence(tmp_path):
    args=_authorization_args(tmp_path,True);_authorize(args)
    envelope=json.loads(args.output.read_text());payload=envelope['payload']
    assert payload['prepared']['sha256']==sha256_file(args.prepared)
    assert payload['smoke_a']['sha256']==payload['smoke_b']['sha256']
    assert payload['candidate_review']['sha256']==sha256_file(args.candidate_review)

def _scheduled_benchmark(args):
    cfg=json.loads(args.config.read_text());prep=json.loads(args.prepared.read_text());durations=[.01,.011,.012,.013,.014];median=.012;scheduled=1
    prep['benchmark']={'scheduled_panels':scheduled,'passed':True,'projected_seconds':median*cfg['simulation']['replicates']*scheduled,'peak_rss_bytes':1024,'projected_artifact_bytes':2048,'benchmark_method':'coarse_exact','benchmark_source':'S','benchmark_workload':{'row_count':1000,'feature_count':256,'component_count':100,'pair_count':500,'row_feature_cells':256000,'component_feature_cells':25600,'schedule_index':0},'replicate_seconds':durations,'median_replicate_seconds':median}
    args.prepared.write_text(json.dumps(prep,sort_keys=True));return prep

def test_authorization_rejects_malformed_benchmark_evidence(tmp_path):
    def mutate_pass(x):x['passed']='yes'
    def mutate_duration(x):x['replicate_seconds'][0]=True
    def mutate_rss_negative(x):x['peak_rss_bytes']=-1
    def mutate_artifact_bool(x):x['projected_artifact_bytes']=True
    def mutate_rss_nan(x):x['peak_rss_bytes']=float('nan')
    def mutate_extra(x):x['unexpected']=1
    def mutate_inconsistent_pass(x):
        x['replicate_seconds']=[1000.0]*5;x['median_replicate_seconds']=1000.0;x['projected_seconds']=200000.0;x['passed']=True
    for index,mutate in enumerate((mutate_pass,mutate_duration,mutate_rss_negative,mutate_artifact_bool,mutate_rss_nan,mutate_extra,mutate_inconsistent_pass)):
        root=tmp_path/str(index);root.mkdir();args=_authorization_args(root,True);prep=_scheduled_benchmark(args);mutate(prep['benchmark']);args.prepared.write_text(json.dumps(prep,sort_keys=True))
        try:_authorize(args)
        except RuntimeError:pass
        else:raise AssertionError(f'malformed benchmark authorized: {mutate.__name__}')
        assert not args.output.exists()

def test_terminal_rejects_postauthorization_prepared_mutation(tmp_path):
    args=_authorization_args(tmp_path,True);_authorize(args);nonce='00'*32
    opening=tmp_path/'opening.json';sign_exclusive(opening,{'schema_version':'relational_measurement_v4_opening_v1','namespace':'relational_measurement_v4_opened_development1','nonce':nonce,'authorization_sha256':sha256_file(args.output)},args.owner_key)
    args.prepared.write_text('{"mutated":true}')
    term=argparse.Namespace(authorization=args.output,opening=opening,prepared=args.prepared,result=None,output=tmp_path/'closure.json',key=args.owner_key,nonce=nonce,technical_reason='HASH_DRIFT',partial_root=[])
    try:terminalize(term)
    except RuntimeError as exc:assert 'drift' in str(exc)
    else:raise AssertionError('mutated prepared artifact was terminalized')
    assert not term.output.exists()

def test_terminal_rejects_arbitrary_decision_and_nomination(tmp_path):
    args=_authorization_args(tmp_path,True);_authorize(args);nonce='11'*32
    opening=tmp_path/'opening.json';sign_exclusive(opening,{'schema_version':'relational_measurement_v4_opening_v1','namespace':'relational_measurement_v4_opened_development1','nonce':nonce,'authorization_sha256':sha256_file(args.output)},args.owner_key)
    result=tmp_path/'result.json';result.write_text(json.dumps({'schema_version':'relational_measurement_v4_result_v1','namespace':'relational_measurement_v4_opened_development1','owner_nonce':nonce,'config_sha256':sha256_file(args.config),'prepared':{'sha256':sha256_file(args.prepared)},'decision':'ARBITRARY','nomination':{'anything':True},'model_weights_loaded':False,'model_forward_run':False,'activation_cache_accessed':False,'fresh_corpus_accessed':False,'training_run':False,'learned_model_authorized':False}))
    term=argparse.Namespace(authorization=args.output,opening=opening,prepared=args.prepared,result=result,output=tmp_path/'closure.json',key=args.owner_key,nonce=nonce,technical_reason=None,partial_root=[])
    try:terminalize(term)
    except RuntimeError as exc:assert 'decision' in str(exc)
    else:raise AssertionError('arbitrary decision was terminalized')

def test_supervisor_closes_preopening_owner_failure_with_exit_status(tmp_path):
    auth_args=_authorization_args(tmp_path,True);_authorize(auth_args)
    owner_script=tmp_path/'owner.sh';owner_script.write_text('#!/usr/bin/env bash\nexit 7\n');owner_script.chmod(0o700)
    x=argparse.Namespace(authorization=auth_args.output,ready=tmp_path/'ready.json',start_signal=tmp_path/'start.json',handoff=tmp_path/'handoff.json',opening=tmp_path/'opening.json',closure=tmp_path/'closure.json',terminal=tmp_path/'terminal.json',receipt=tmp_path/'receipt.json',run_root=tmp_path/'run',prepared=auth_args.prepared,result=tmp_path/'result.json',key=auth_args.supervisor_key,owner_key=auth_args.owner_key,owner_script=owner_script,config=auth_args.config,nonce='22'*32,namespace='relational_measurement_v4_opened_development1',candidate_sha256=sha256_file(auth_args.config),launcher_pid=os.getpid(),timeout=2,post_timeout=2)
    thread=threading.Thread(target=supervise,args=(x,));thread.start()
    ready=wait_payload(x.ready)
    sign_exclusive(x.start_signal,{'schema_version':'relational_measurement_v4_launcher_trigger_v1','namespace':x.namespace,'nonce':x.nonce,'launcher_pid':os.getpid(),'supervisor_pid':ready['supervisor_pid'],'authorization_sha256':sha256_file(x.authorization),'supervisor_ready_sha256':sha256_file(x.ready)},auth_args.owner_key)
    thread.join(5);assert not thread.is_alive();receipt=json.loads(x.closure.read_text())['payload']['receipt']
    assert receipt['reason']=='PREOPEN_OWNER_FAILURE' and receipt['status']['exit_status']==7

def test_prepared_validator_rejects_unknown_top_level_before_source_rebuild(tmp_path):
    config=ROOT/'configs/relational_measurement_v4/run.json';cfg=json.loads(config.read_text())
    bad={k:False for k in ('model_weights_loaded','model_forward_run','activation_cache_accessed','fresh_corpus_accessed','training_run')}
    bad.update({'schema_version':'relational_measurement_v4_prepared_v1','namespace':cfg['namespace'],'config_sha256':sha256_file(config),'exact_reference':{},'methods':{},'benchmark':{},'environment':{},'smoke':False,'unexpected':1})
    try:validate_prepared_content(cfg,bad,config)
    except RuntimeError as exc:assert 'identity' in str(exc)
    else:raise AssertionError('unknown prepared field accepted')

def test_stable_cpu_inventory_ignores_runtime_frequency():
    base='vendor_id : GenuineIntel\nmodel name : Example CPU\ncpu cores : 8\ncpu MHz : {mhz}\nbogomips : {bog}\nflags : a b c\n\n'
    assert stable_cpu_inventory(base.format(mhz='1000.1',bog='1'))==stable_cpu_inventory(base.format(mhz='3999.9',bog='9'))

def test_structural_support_precedence_and_complete_nomination_traversal():
    cfg=json.loads((ROOT/'configs/relational_measurement_v4/run.json').read_text());sources=cfg['source_selection_order'][:2]
    def prepared(two_structural=False,two_real=False):
        methods={}
        for method in cfg['matching']['methods']:
            cells={s:{'support_eligible':bool(two_structural and method=='coarse_exact' and s in sources)} for s in cfg['source_selection_order']}
            selected=sources if two_real and method=='coarse_exact' else []
            methods[method]={'sources':cells,'eligible_sources':selected,'selected_sources':selected}
        return {'methods':methods,'benchmark':{'x':1}}
    p=prepared();r={'methods':p['methods'],'benchmark':p['benchmark'],'simulations':{}}
    assert recompute_decision(r,p,cfg)[0]=='STOP_MEASUREMENT_DESIGN_UNDER_SUPPORTED'
    p=prepared(True);r={'methods':p['methods'],'benchmark':p['benchmark'],'simulations':{}}
    assert recompute_decision(r,p,cfg)[0]=='STOP_MEASUREMENT_DESIGN_UNCALIBRATED'
    p=prepared(True,True);sim={}
    for source in sources:
        sim[source]={}
        for dgp in cfg['simulation']['dgps']:
            positive=dgp.endswith('positive');primary={'replicates':cfg['simulation']['replicates'],'bias':0.,'coverage':.95,'rejection':.05 if not positive else .9,'power':.9 if positive else None,'finite':True}
            overlap={'replicates':cfg['simulation']['replicates'],'mean_estimate':0.,'mean_true_target':0.,'bias':0.,'finite':True,'nominating':False}
            sim[source][dgp]={'paired_mean':dict(primary),'control_ridge_residualized':dict(primary),'overlap_ato_descriptive':overlap}
    r={'methods':p['methods'],'benchmark':p['benchmark'],'simulations':{'coarse_exact':sim}}
    decision,nomination=recompute_decision(r,p,cfg)
    assert decision=='NOMINATE_MEASUREMENT_DESIGN_FOR_FRESH_PREREGISTRATION' and nomination=={'matcher':'coarse_exact','estimator':'paired_mean','sources':sources}
    del r['simulations']['coarse_exact'][sources[0]][cfg['simulation']['dgps'][0]]['control_ridge_residualized']['bias']
    try:recompute_decision(r,p,cfg)
    except RuntimeError as exc:assert 'cell' in str(exc)
    else:raise AssertionError('malformed nonwinning estimator cell bypassed complete validation')

def test_propensity_is_cross_fitted_finite_and_balanced_on_paired_covariates():
    cfg=json.loads((ROOT/'configs/relational_measurement_v4/run.json').read_text());rows=[];values=[]
    for c in range(20):
        for treatment in (0,1):rows.append({'component_id':f'c{c}','fold':c%5,'treatment':treatment});values.append([c%7,c%3])
    got=propensity_diagnostics(np.asarray(values,float),rows,cfg['seed'],cfg['estimators'],cfg['diagnostics'])
    assert np.all(np.isfinite(got['propensities'])) and np.allclose(got['propensities'],.5) and got['central_fraction']==1

def test_synthetic_dgps_are_deterministic_and_overlap_is_non_nominating():
    cfg=json.loads((ROOT/'configs/relational_measurement_v4/run.json').read_text());cfg=copy.deepcopy(cfg);cfg['estimators']['lexical_hash_width']=8;rows=[];pairs=[];base=[]
    rng=np.random.default_rng(7)
    for c in range(20):
        pid=f'p{c}';pairs.append({'pair_id':pid,'component_id':f'c{c}'})
        z=rng.normal(size=20)
        for treatment in (0,1):
            rr=row(f'r{c}{treatment}',pid);rr.update({'source':'S','component_id':f'c{c}','fold':c%5,'treatment':treatment,'pair_id':pid});rows.append(rr);base.append(z)
    X=np.concatenate([np.asarray(base),np.zeros((len(rows),8))],axis=1);names=[f'x{i}' for i in range(20)]+[f'lexical_hash_{i}' for i in range(8)]
    a=simulate_panel(X,names,rows,pairs,'coarse_exact',cfg,cfg['seed'],replicates=1);b=simulate_panel(X,names,rows,pairs,'coarse_exact',cfg,cfg['seed'],replicates=1)
    assert a==b and set(a)==set(cfg['simulation']['dgps'])
    assert all(cell['overlap_ato_descriptive']['nominating'] is False and cell['overlap_ato_descriptive']['finite'] for cell in a.values())

def _complete_technical_chain(tmp_path):
    tmp_path.mkdir(parents=True,exist_ok=True)
    args=_authorization_args(tmp_path,True);_authorize(args);auth=json.loads(args.output.read_text())['payload'];nonce='33'*32;launcher=12345;supervisor=23456;owner=34567
    ready=tmp_path/'ready.json';start=tmp_path/'start.json';handoff=tmp_path/'handoff.json';opening=tmp_path/'opening.json';closure=tmp_path/'closure.json'
    sign_exclusive(ready,{'schema_version':'relational_measurement_v4_supervisor_ready_v1','namespace':auth['namespace'],'nonce':nonce,'supervisor_pid':supervisor,'launcher_pid':launcher,'candidate_sha256':sha256_file(args.config),'authorization_sha256':sha256_file(args.output)},args.supervisor_key)
    sign_exclusive(start,{'schema_version':'relational_measurement_v4_launcher_trigger_v1','namespace':auth['namespace'],'nonce':nonce,'launcher_pid':launcher,'supervisor_pid':supervisor,'authorization_sha256':sha256_file(args.output),'supervisor_ready_sha256':sha256_file(ready)},args.owner_key)
    sign_exclusive(handoff,{'schema_version':'relational_measurement_v4_owner_handoff_v1','namespace':auth['namespace'],'nonce':nonce,'launcher_pid':launcher,'supervisor_pid':supervisor,'owner_pid':owner,'authorization_sha256':sha256_file(args.output),'supervisor_ready_sha256':sha256_file(ready),'launcher_trigger_sha256':sha256_file(start)},args.owner_key)
    sign_exclusive(opening,{'schema_version':'relational_measurement_v4_opening_v1','namespace':auth['namespace'],'nonce':nonce,'launcher_pid':launcher,'supervisor_pid':supervisor,'owner_pid':owner,'authorization_sha256':sha256_file(args.output),'supervisor_ready_sha256':sha256_file(ready),'launcher_trigger_sha256':sha256_file(start),'handoff_sha256':sha256_file(handoff)},args.owner_key)
    term=argparse.Namespace(authorization=args.output,opening=opening,prepared=args.prepared,result=None,output=closure,key=args.owner_key,nonce=nonce,technical_reason='FIT_FAILURE',partial_root=[]);terminalize(term)
    state=argparse.Namespace(authorization=args.output,ready=ready,start_signal=start,handoff=handoff,opening=opening,closure=closure,prepared=args.prepared,result=tmp_path/'result.json',config=args.config,namespace=auth['namespace'],nonce=nonce,run_root=tmp_path/'run')
    return args,state

def test_strict_verifier_accepts_complete_technical_chain_and_suppresses_loser(tmp_path):
    args,state=_complete_technical_chain(tmp_path);assert verify_lifecycle_closure(state)=='TECHNICAL_TERMINAL';before=sha256_file(state.closure)
    write_receipt(state,load_private_key(args.supervisor_key),'OWNER_TERMINALIZATION_FAILURE',{'owner_pid':34567,'exit_status':1,'detail_code':'TERMINAL_MISSING','observed_error':None})
    assert sha256_file(state.closure)==before and verify_lifecycle_closure(state)=='TECHNICAL_TERMINAL'

def test_strict_verifier_rejects_transitive_handoff_mutation(tmp_path):
    args,state=_complete_technical_chain(tmp_path);state.handoff.unlink();sign_exclusive(state.handoff,{'schema_version':'relational_measurement_v4_owner_handoff_v1','namespace':state.namespace,'nonce':state.nonce,'launcher_pid':12345,'supervisor_pid':23456,'owner_pid':999,'authorization_sha256':sha256_file(state.authorization),'supervisor_ready_sha256':sha256_file(state.ready),'launcher_trigger_sha256':sha256_file(state.start_signal)},args.owner_key)
    try:verify_lifecycle_closure(state)
    except RuntimeError:pass
    else:raise AssertionError('mutated transitive handoff accepted')

def test_scientific_closure_and_result_use_one_exact_schema_validator(tmp_path):
    args,state=_complete_technical_chain(tmp_path);state.closure.unlink();prep=json.loads(args.prepared.read_text());result=state.result
    body={'schema_version':'relational_measurement_v4_result_v1','namespace':state.namespace,'owner_nonce':state.nonce,'config_sha256':sha256_file(args.config),'prepared':{'path':str(args.prepared),'sha256':sha256_file(args.prepared)},'decision':'STOP_MEASUREMENT_DESIGN_UNDER_SUPPORTED','nomination':None,'simulations':{},'methods':prep['methods'],'benchmark':prep['benchmark'],'model_weights_loaded':False,'model_forward_run':False,'activation_cache_accessed':False,'fresh_corpus_accessed':False,'training_run':False,'learned_model_authorized':False};result.write_text(json.dumps(body,sort_keys=True))
    terminalize(argparse.Namespace(authorization=args.output,opening=state.opening,prepared=args.prepared,result=result,output=state.closure,key=args.owner_key,nonce=state.nonce,technical_reason=None,partial_root=[]))
    assert verify_lifecycle_closure(state)=='SCIENTIFIC_TERMINAL'
    closure=json.loads(state.closure.read_text())['payload'];state.closure.unlink();body['UNFROZEN_EXTRA']=1;result.write_text(json.dumps(body,sort_keys=True));closure['terminal']['result']['sha256']=sha256_file(result)
    from relational_measurement_v4_lifecycle import sign_atomic_closure
    sign_atomic_closure(state.closure,closure,args.owner_key)
    try:verify_lifecycle_closure(state)
    except RuntimeError as exc:assert 'schema' in str(exc)
    else:raise AssertionError('extra scientific-result field accepted')

def test_supervisor_trigger_timeout_closes_with_strict_preopen_receipt(tmp_path):
    auth_args=_authorization_args(tmp_path,True);_authorize(auth_args)
    x=argparse.Namespace(authorization=auth_args.output,ready=tmp_path/'ready.json',start_signal=tmp_path/'start.json',handoff=tmp_path/'handoff.json',opening=tmp_path/'opening.json',closure=tmp_path/'closure.json',terminal=tmp_path/'terminal.json',receipt=tmp_path/'receipt.json',run_root=tmp_path/'run',prepared=auth_args.prepared,result=tmp_path/'result.json',key=auth_args.supervisor_key,owner_key=auth_args.owner_key,owner_script=tmp_path/'never.sh',config=auth_args.config,nonce='44'*32,namespace='relational_measurement_v4_opened_development1',candidate_sha256=sha256_file(auth_args.config),launcher_pid=os.getpid(),timeout=.05,post_timeout=1)
    supervise(x);payload=json.loads(x.closure.read_text())['payload']['receipt']
    assert payload['reason']=='PREOPEN_OWNER_FAILURE' and payload['status']['detail_code']=='TRIGGER_TIMEOUT' and verify_lifecycle_closure(x)=='SUPERVISOR_RECEIPT'

def test_stop_owner_group_kills_foreground_descendant_before_it_can_write(tmp_path):
    marker=tmp_path/'orphan-marker';script=tmp_path/'group.sh';script.write_text(f"#!/usr/bin/env bash\npython -c 'import time,pathlib;time.sleep(1);pathlib.Path({str(marker)!r}).write_text(\"late\")'\n");script.chmod(0o700)
    child=subprocess.Popen(['bash',str(script)],start_new_session=True);time.sleep(.1);stop_owner_group(child,.2);time.sleep(1.1)
    assert not marker.exists()

def _run_supervisor_script(tmp_path,body,post_timeout=2,expect_error=False):
    auth_args=_authorization_args(tmp_path,True);_authorize(auth_args);owner_script=tmp_path/'owner-custom.sh';owner_script.write_text('#!/usr/bin/env bash\nset -euo pipefail\n'+body);owner_script.chmod(0o700)
    x=argparse.Namespace(authorization=auth_args.output,ready=tmp_path/'ready.json',start_signal=tmp_path/'start.json',handoff=tmp_path/'handoff.json',opening=tmp_path/'opening.json',closure=tmp_path/'closure.json',run_root=tmp_path/'run',prepared=auth_args.prepared,result=tmp_path/'result.json',key=auth_args.supervisor_key,owner_key=auth_args.owner_key,owner_script=owner_script,config=auth_args.config,nonce='55'*32,namespace='relational_measurement_v4_opened_development1',candidate_sha256=sha256_file(auth_args.config),launcher_pid=os.getpid(),timeout=2,post_timeout=post_timeout)
    errors=[]
    def run():
        try:supervise(x)
        except Exception as exc:errors.append(exc)
    thread=threading.Thread(target=run);thread.start()
    ready=wait_payload(x.ready);sign_exclusive(x.start_signal,{'schema_version':'relational_measurement_v4_launcher_trigger_v1','namespace':x.namespace,'nonce':x.nonce,'launcher_pid':os.getpid(),'supervisor_pid':ready['supervisor_pid'],'authorization_sha256':sha256_file(x.authorization),'supervisor_ready_sha256':sha256_file(x.ready)},auth_args.owner_key)
    thread.join(8);assert not thread.is_alive()
    if expect_error:assert errors
    else:assert not errors
    x.supervisor_errors=errors
    return auth_args,x

def test_supervisor_invalid_handoff_publishes_verifiable_prefix_receipt(tmp_path):
    py=ROOT/'.venv-atlas/bin/python';life=ROOT/'scripts/relational_measurement_v4_lifecycle.py'
    body=f'"{py}" "{life}" handoff --authorization "$V4_AUTH" --ready "$V4_READY" --trigger "$V4_START" --output "$V4_HANDOFF" --key "$V4_OWNER_KEY" --nonce "$V4_NONCE" --owner-pid 999\nexit 7\n'
    _,x=_run_supervisor_script(tmp_path,body);closure=json.loads(x.closure.read_text())['payload']
    assert closure['receipt']['status']['detail_code']=='HANDOFF_INVALID' and verify_lifecycle_closure(x)=='SUPERVISOR_RECEIPT'

def test_supervisor_quiesces_lingering_group_after_early_owner_exit(tmp_path):
    py=ROOT/'.venv-atlas/bin/python';life=ROOT/'scripts/relational_measurement_v4_lifecycle.py';marker=tmp_path/'late.json'
    body=f'"{py}" "{life}" handoff --authorization "$V4_AUTH" --ready "$V4_READY" --trigger "$V4_START" --output "$V4_HANDOFF" --key "$V4_OWNER_KEY" --nonce "$V4_NONCE" --owner-pid $$\n"{py}" "{life}" opening --authorization "$V4_AUTH" --ready "$V4_READY" --trigger "$V4_START" --handoff "$V4_HANDOFF" --output "$V4_OPENING" --key "$V4_OWNER_KEY" --nonce "$V4_NONCE" --owner-pid $$\n(sleep 1; printf late > "{marker}") &\nexit 7\n'
    _,x=_run_supervisor_script(tmp_path,body);time.sleep(1.2)
    assert not marker.exists() and verify_lifecycle_closure(x)=='SUPERVISOR_RECEIPT'

def test_supervisor_times_out_hung_opened_owner_and_writes_receipt(tmp_path):
    py=ROOT/'.venv-atlas/bin/python';life=ROOT/'scripts/relational_measurement_v4_lifecycle.py'
    body=f'"{py}" "{life}" handoff --authorization "$V4_AUTH" --ready "$V4_READY" --trigger "$V4_START" --output "$V4_HANDOFF" --key "$V4_OWNER_KEY" --nonce "$V4_NONCE" --owner-pid $$\n"{py}" "{life}" opening --authorization "$V4_AUTH" --ready "$V4_READY" --trigger "$V4_START" --handoff "$V4_HANDOFF" --output "$V4_OPENING" --key "$V4_OWNER_KEY" --nonce "$V4_NONCE" --owner-pid $$\nsleep 10\n'
    _,x=_run_supervisor_script(tmp_path,body,.2);receipt=json.loads(x.closure.read_text())['payload']['receipt']
    assert receipt['status']['postopening_timeout'] is True and receipt['reason']=='OWNER_TERMINALIZATION_FAILURE' and verify_lifecycle_closure(x)=='SUPERVISOR_RECEIPT'

def test_supervisor_accepts_valid_owner_technical_closure(tmp_path):
    py=ROOT/'.venv-atlas/bin/python';life=ROOT/'scripts/relational_measurement_v4_lifecycle.py'
    body=f'"{py}" "{life}" handoff --authorization "$V4_AUTH" --ready "$V4_READY" --trigger "$V4_START" --output "$V4_HANDOFF" --key "$V4_OWNER_KEY" --nonce "$V4_NONCE" --owner-pid $$\n"{py}" "{life}" opening --authorization "$V4_AUTH" --ready "$V4_READY" --trigger "$V4_START" --handoff "$V4_HANDOFF" --output "$V4_OPENING" --key "$V4_OWNER_KEY" --nonce "$V4_NONCE" --owner-pid $$\n"{py}" "{life}" terminal --authorization "$V4_AUTH" --opening "$V4_OPENING" --prepared "$V4_PREPARED" --output "$V4_CLOSURE" --key "$V4_OWNER_KEY" --nonce "$V4_NONCE" --technical-reason FIT_FAILURE\n'
    _,x=_run_supervisor_script(tmp_path,body)
    assert verify_lifecycle_closure(x)=='TECHNICAL_TERMINAL'

def test_strict_verifier_rejects_extra_signed_schema_and_prepared_drift(tmp_path):
    args,state=_complete_technical_chain(tmp_path);ready=json.loads(state.ready.read_text())['payload'];state.ready.unlink();ready['UNFROZEN_EXTRA']=1;sign_exclusive(state.ready,ready,args.supervisor_key)
    try:verify_lifecycle_closure(state)
    except RuntimeError as exc:assert 'ready' in str(exc)
    else:raise AssertionError('extra signed ready field accepted')
    args2,state2=_complete_technical_chain(tmp_path/'drift');state2.prepared.write_text('{"mutated":true}')
    try:verify_lifecycle_closure(state2)
    except RuntimeError as exc:assert 'drift' in str(exc)
    else:raise AssertionError('prepared drift accepted for technical closure')

def test_strict_receipt_requires_complete_recomputed_inventory(tmp_path):
    args=_authorization_args(tmp_path,True);_authorize(args);nonce='66'*32;ready=tmp_path/'ready.json';closure=tmp_path/'closure.json'
    sign_exclusive(ready,{'schema_version':'relational_measurement_v4_supervisor_ready_v1','namespace':'relational_measurement_v4_opened_development1','nonce':nonce,'supervisor_pid':1,'launcher_pid':2,'candidate_sha256':sha256_file(args.config),'authorization_sha256':sha256_file(args.output)},args.supervisor_key)
    status={'authorization_present':True,'ready_present':True,'trigger_present':False,'handoff_present':False,'opening_present':False,'owner_pid':None,'exit_status':None,'owner_alive':False,'postopening_timeout':False,'detail_code':'TRIGGER_TIMEOUT','observed_error':None}
    from relational_measurement_v4_lifecycle import sign_atomic_closure
    sign_atomic_closure(closure,{'schema_version':'relational_measurement_v4_closure_v1','kind':'SUPERVISOR_RECEIPT','namespace':'relational_measurement_v4_opened_development1','nonce':nonce,'authorization_sha256':sha256_file(args.output),'signer_fingerprint':json.loads(args.output.read_text())['payload']['supervisor_fingerprint'],'receipt':{'schema_version':'relational_measurement_v4_supervisor_receipt_v1','reason':'PREOPEN_OWNER_FAILURE','status':status,'partial_artifacts':[],'scientific_result':False,'retry_authorized':False}},args.supervisor_key)
    state=argparse.Namespace(authorization=args.output,ready=ready,start_signal=tmp_path/'start',handoff=tmp_path/'handoff',opening=tmp_path/'opening',closure=closure,prepared=args.prepared,result=tmp_path/'result',config=args.config,run_root=tmp_path/'run',namespace='relational_measurement_v4_opened_development1',nonce=nonce)
    try:verify_lifecycle_closure(state)
    except RuntimeError as exc:assert 'inventory' in str(exc)
    else:raise AssertionError('empty receipt inventory accepted')

def test_primary_simulation_cell_schema_is_not_conflated_with_gate_failure():
    cfg=json.loads((ROOT/'configs/relational_measurement_v4/run.json').read_text())['simulation'];bad={'replicates':cfg['replicates'],'coverage':.95,'rejection':0.,'power':None,'finite':True}
    try:_cell_pass(bad,False,cfg)
    except RuntimeError as exc:assert 'cell' in str(exc)
    else:raise AssertionError('malformed primary cell treated as an ordinary failure')

def test_support_and_numeric_failures_fail_closed():
    cfg=json.loads((ROOT/'configs/relational_measurement_v4/run.json').read_text());support={'components':99,'pairs':500,'orientations':{'later_query_is_head':250,'later_query_is_child':250},'fold_components':{str(i):20 for i in range(5)}}
    assert support_ok(support,cfg['matching'],cfg['diagnostics']) is False
    try:component_interval(np.array([float('nan'),1.]),[{'component_id':'a'},{'component_id':'b'}])
    except RuntimeError as exc:assert 'nonfinite' in str(exc)
    else:raise AssertionError('nonfinite component values accepted')

def test_primary_simulation_probability_schema_is_strict():
    cfg=json.loads((ROOT/'configs/relational_measurement_v4/run.json').read_text())['simulation']
    null={'replicates':cfg['replicates'],'bias':0.0,'coverage':.95,'rejection':.05,'power':None,'finite':True}
    positive={**null,'rejection':.8,'power':.8}
    assert _cell_pass(null,False,cfg) and _cell_pass(positive,True,cfg)
    mutations=[(null,'coverage',-1.0,False),(null,'rejection',1.01,False),(null,'bias',False,False),(null,'power',.5,False),(null,'coverage',.901,False),(null,'rejection',.10,False),(positive,'power',2.0,True),(positive,'power',True,True),(positive,'power',.801,True),(positive,'rejection',0.0,True),(positive,'rejection',999.0,True)]
    for base,key,value,is_positive in mutations:
        bad=dict(base);bad[key]=value
        try:_cell_pass(bad,is_positive,cfg)
        except RuntimeError:pass
        else:raise AssertionError(f'invalid probability/type accepted: {key}={value!r}')

def _nominating_open_chain(tmp_path):
    tmp_path.mkdir(parents=True,exist_ok=True);args=_authorization_args(tmp_path,True);cfg=json.loads(args.config.read_text());prep=json.loads(args.prepared.read_text());sources=cfg['source_selection_order'][:2]
    for method,block in prep['methods'].items():
        block['eligible_sources']=sources if method=='coarse_exact' else [];block['selected_sources']=list(block['eligible_sources'])
        for source,item in block['sources'].items():item.update({'support':{},'support_eligible':source in sources and method=='coarse_exact','diagnostics':None,'real_eligible':source in sources and method=='coarse_exact'})
    args.prepared.write_text(json.dumps(prep,sort_keys=True));_authorize(args);auth=json.loads(args.output.read_text())['payload'];nonce='ab'*32;launcher=12345;supervisor=23456;owner=34567
    ready=tmp_path/'ready.json';start=tmp_path/'start.json';handoff=tmp_path/'handoff.json';opening=tmp_path/'opening.json';closure=tmp_path/'closure.json';result=tmp_path/'result.json'
    sign_exclusive(ready,{'schema_version':'relational_measurement_v4_supervisor_ready_v1','namespace':auth['namespace'],'nonce':nonce,'supervisor_pid':supervisor,'launcher_pid':launcher,'candidate_sha256':sha256_file(args.config),'authorization_sha256':sha256_file(args.output)},args.supervisor_key)
    sign_exclusive(start,{'schema_version':'relational_measurement_v4_launcher_trigger_v1','namespace':auth['namespace'],'nonce':nonce,'launcher_pid':launcher,'supervisor_pid':supervisor,'authorization_sha256':sha256_file(args.output),'supervisor_ready_sha256':sha256_file(ready)},args.owner_key)
    sign_exclusive(handoff,{'schema_version':'relational_measurement_v4_owner_handoff_v1','namespace':auth['namespace'],'nonce':nonce,'launcher_pid':launcher,'supervisor_pid':supervisor,'owner_pid':owner,'authorization_sha256':sha256_file(args.output),'supervisor_ready_sha256':sha256_file(ready),'launcher_trigger_sha256':sha256_file(start)},args.owner_key)
    sign_exclusive(opening,{'schema_version':'relational_measurement_v4_opening_v1','namespace':auth['namespace'],'nonce':nonce,'launcher_pid':launcher,'supervisor_pid':supervisor,'owner_pid':owner,'authorization_sha256':sha256_file(args.output),'supervisor_ready_sha256':sha256_file(ready),'launcher_trigger_sha256':sha256_file(start),'handoff_sha256':sha256_file(handoff)},args.owner_key)
    simulations={'coarse_exact':{}}
    for source in sources:
        simulations['coarse_exact'][source]={}
        for dgp in cfg['simulation']['dgps']:
            positive=dgp.endswith('positive');primary={'replicates':cfg['simulation']['replicates'],'bias':0.,'coverage':.95,'rejection':.9 if positive else .05,'power':.9 if positive else None,'finite':True};overlap={'replicates':cfg['simulation']['replicates'],'mean_estimate':0.,'mean_true_target':0.,'bias':0.,'finite':True,'nominating':False}
            simulations['coarse_exact'][source][dgp]={'paired_mean':dict(primary),'control_ridge_residualized':dict(primary),'overlap_ato_descriptive':overlap}
    body={'schema_version':'relational_measurement_v4_result_v1','namespace':auth['namespace'],'owner_nonce':nonce,'config_sha256':sha256_file(args.config),'prepared':{'path':str(args.prepared),'sha256':sha256_file(args.prepared)},'decision':'NOMINATE_MEASUREMENT_DESIGN_FOR_FRESH_PREREGISTRATION','nomination':{'matcher':'coarse_exact','estimator':'paired_mean','sources':sources},'simulations':simulations,'methods':prep['methods'],'benchmark':prep['benchmark'],'model_weights_loaded':False,'model_forward_run':False,'activation_cache_accessed':False,'fresh_corpus_accessed':False,'training_run':False,'learned_model_authorized':False}
    state=argparse.Namespace(authorization=args.output,ready=ready,start_signal=start,handoff=handoff,opening=opening,closure=closure,prepared=args.prepared,result=result,config=args.config,namespace=auth['namespace'],nonce=nonce,run_root=tmp_path/'run')
    return args,state,body

def test_terminal_and_verifier_reject_impossible_probability_summaries(tmp_path):
    mutations=[('linear_positive','coverage',-0.1),('linear_positive','rejection',1.1),('linear_positive','bias',False),('linear_positive','power',None),('linear_positive','coverage',.901),('linear_positive','rejection',.05),('linear_null','rejection',.10)]
    for index,(dgp,field,value) in enumerate(mutations):
        args,state,body=_nominating_open_chain(tmp_path/str(index));cell=body['simulations']['coarse_exact'][body['nomination']['sources'][0]][dgp]['paired_mean'];cell[field]=value
        state.result.write_text(json.dumps(body,sort_keys=True))
        terminal_args=argparse.Namespace(authorization=state.authorization,opening=state.opening,prepared=state.prepared,result=state.result,output=state.closure,key=args.owner_key,nonce=state.nonce,technical_reason=None,partial_root=[])
        try:terminalize(terminal_args)
        except RuntimeError:pass
        else:raise AssertionError(f'terminalizer accepted invalid {field}')
        term={'schema_version':'relational_measurement_v4_terminal_v1','namespace':state.namespace,'nonce':state.nonce,'authorization_sha256':sha256_file(state.authorization),'opening_sha256':sha256_file(state.opening),'prepared_sha256':sha256_file(state.prepared),'retry_authorized':False,'fresh_corpus_accessed':False,'model_forward_run':False,'training_run':False,'status':'TERMINAL_COMPLETE','result':{'path':str(state.result),'sha256':sha256_file(state.result)},'decision':body['decision'],'nomination':body['nomination'],'scientific_result':True}
        auth=json.loads(state.authorization.read_text())['payload'];sign_atomic_closure(state.closure,{'schema_version':'relational_measurement_v4_closure_v1','kind':'OWNER_TERMINAL','namespace':state.namespace,'nonce':state.nonce,'authorization_sha256':sha256_file(state.authorization),'signer_fingerprint':auth['owner_fingerprint'],'terminal':term},args.owner_key)
        try:verify_lifecycle_closure(state)
        except RuntimeError:pass
        else:raise AssertionError(f'verifier accepted invalid {field}')

def _trigger_timeout_state(tmp_path):
    tmp_path.mkdir(parents=True,exist_ok=True)
    auth_args=_authorization_args(tmp_path,True);_authorize(auth_args)
    x=argparse.Namespace(authorization=auth_args.output,ready=tmp_path/'ready.json',start_signal=tmp_path/'start.json',handoff=tmp_path/'handoff.json',opening=tmp_path/'opening.json',closure=tmp_path/'closure.json',run_root=tmp_path/'run',prepared=auth_args.prepared,result=tmp_path/'result.json',key=auth_args.supervisor_key,owner_key=auth_args.owner_key,owner_script=tmp_path/'never.sh',config=auth_args.config,nonce='88'*32,namespace='relational_measurement_v4_opened_development1',candidate_sha256=sha256_file(auth_args.config),launcher_pid=os.getpid(),timeout=.01,post_timeout=1)
    supervise(x);assert verify_lifecycle_closure(x)=='SUPERVISOR_RECEIPT'
    return auth_args,x

def _resign_closure(path,payload,key):
    if path.exists():path.unlink()
    sign_atomic_closure(path,payload,key)

def test_strict_receipt_status_schema_and_pid_binding(tmp_path):
    args,state=_trigger_timeout_state(tmp_path/'trigger');base=json.loads(state.closure.read_text())['payload']
    for key,value in [('owner_pid',1),('exit_status','bad'),('postopening_timeout','bad'),('observed_error',{}),('ready_present',1)]:
        bad=copy.deepcopy(base);bad['receipt']['status'][key]=value;_resign_closure(state.closure,bad,args.supervisor_key)
        try:verify_lifecycle_closure(state)
        except RuntimeError:pass
        else:raise AssertionError(f'type-invalid receipt status accepted: {key}')
    args2,state2=_complete_technical_chain(tmp_path/'pid');state2.closure.unlink();write_receipt(state2,load_private_key(args2.supervisor_key),'OWNER_TERMINALIZATION_FAILURE',{'owner_pid':34567,'exit_status':7,'detail_code':'TERMINAL_MISSING','observed_error':None});good=json.loads(state2.closure.read_text())['payload'];good['receipt']['status']['owner_pid']=999;_resign_closure(state2.closure,good,args2.supervisor_key)
    try:verify_lifecycle_closure(state2)
    except RuntimeError as exc:assert 'PID' in str(exc)
    else:raise AssertionError('receipt owner PID not bound to handoff/opening')

def test_supervisor_missing_opening_publishes_verifiable_prefix_receipt(tmp_path):
    py=ROOT/'.venv-atlas/bin/python';life=ROOT/'scripts/relational_measurement_v4_lifecycle.py'
    body=f'"{py}" "{life}" handoff --authorization "$V4_AUTH" --ready "$V4_READY" --trigger "$V4_START" --output "$V4_HANDOFF" --key "$V4_OWNER_KEY" --nonce "$V4_NONCE" --owner-pid $$\nexit 9\n'
    _,x=_run_supervisor_script(tmp_path,body);receipt=json.loads(x.closure.read_text())['payload']['receipt']
    assert receipt['status']['detail_code']=='OPENING_MISSING' and receipt['status']['owner_pid'] is not None and verify_lifecycle_closure(x)=='SUPERVISOR_RECEIPT'

def test_supervisor_invalid_opening_publishes_verifiable_prefix_receipt(tmp_path):
    py=ROOT/'.venv-atlas/bin/python';life=ROOT/'scripts/relational_measurement_v4_lifecycle.py';bad=tmp_path/'bad-opening.py'
    bad.write_text('''import os,sys\nfrom pathlib import Path\nfrom relational_objects_v3 import verify_signed,sha256_file\nfrom relational_measurement_v4_lifecycle import sign_exclusive\na=Path(os.environ["V4_AUTH"]);r=Path(os.environ["V4_READY"]);t=Path(os.environ["V4_START"]);h=Path(os.environ["V4_HANDOFF"]);o=Path(os.environ["V4_OPENING"]);auth=verify_signed(a);ready=verify_signed(r,auth["supervisor_fingerprint"]);pid=int(sys.argv[1])\nsign_exclusive(o,{"schema_version":"relational_measurement_v4_opening_v1","namespace":auth["namespace"],"nonce":os.environ["V4_NONCE"],"launcher_pid":ready["launcher_pid"],"supervisor_pid":ready["supervisor_pid"],"owner_pid":pid+1,"authorization_sha256":sha256_file(a),"supervisor_ready_sha256":sha256_file(r),"launcher_trigger_sha256":sha256_file(t),"handoff_sha256":sha256_file(h)},Path(os.environ["V4_OWNER_KEY"]))\n''')
    body=f'"{py}" "{life}" handoff --authorization "$V4_AUTH" --ready "$V4_READY" --trigger "$V4_START" --output "$V4_HANDOFF" --key "$V4_OWNER_KEY" --nonce "$V4_NONCE" --owner-pid $$\n"{py}" "{bad}" $$\nexit 8\n'
    _,x=_run_supervisor_script(tmp_path,body);receipt=json.loads(x.closure.read_text())['payload']['receipt']
    assert receipt['status']['detail_code']=='OPENING_INVALID' and receipt['status']['observed_error']=='SEMANTIC_INVALID' and verify_lifecycle_closure(x)=='SUPERVISOR_RECEIPT'

def test_supervisor_missing_terminal_after_opening_writes_receipt(tmp_path):
    py=ROOT/'.venv-atlas/bin/python';life=ROOT/'scripts/relational_measurement_v4_lifecycle.py'
    body=f'"{py}" "{life}" handoff --authorization "$V4_AUTH" --ready "$V4_READY" --trigger "$V4_START" --output "$V4_HANDOFF" --key "$V4_OWNER_KEY" --nonce "$V4_NONCE" --owner-pid $$\n"{py}" "{life}" opening --authorization "$V4_AUTH" --ready "$V4_READY" --trigger "$V4_START" --handoff "$V4_HANDOFF" --output "$V4_OPENING" --key "$V4_OWNER_KEY" --nonce "$V4_NONCE" --owner-pid $$\nexit 7\n'
    _,x=_run_supervisor_script(tmp_path,body);receipt=json.loads(x.closure.read_text())['payload']['receipt']
    assert receipt['status']['detail_code']=='TERMINAL_MISSING' and receipt['status']['postopening_timeout'] is False and verify_lifecycle_closure(x)=='SUPERVISOR_RECEIPT'

def test_supervisor_rejects_invalid_immutable_postopening_terminal(tmp_path):
    py=ROOT/'.venv-atlas/bin/python';life=ROOT/'scripts/relational_measurement_v4_lifecycle.py'
    body=f'"{py}" "{life}" handoff --authorization "$V4_AUTH" --ready "$V4_READY" --trigger "$V4_START" --output "$V4_HANDOFF" --key "$V4_OWNER_KEY" --nonce "$V4_NONCE" --owner-pid $$\n"{py}" "{life}" opening --authorization "$V4_AUTH" --ready "$V4_READY" --trigger "$V4_START" --handoff "$V4_HANDOFF" --output "$V4_OPENING" --key "$V4_OWNER_KEY" --nonce "$V4_NONCE" --owner-pid $$\nprintf malformed > "$V4_CLOSURE"\nexit 6\n'
    _,x=_run_supervisor_script(tmp_path,body,expect_error=True)
    assert x.closure.read_text()=='malformed' and isinstance(x.supervisor_errors[0],RuntimeError)

def test_supervisor_accepts_terminal_published_at_deadline_boundary(tmp_path):
    auth_args=_authorization_args(tmp_path,True);_authorize(auth_args);x=argparse.Namespace(authorization=auth_args.output,ready=tmp_path/'ready.json',start_signal=tmp_path/'start.json',handoff=tmp_path/'handoff.json',opening=tmp_path/'opening.json',closure=tmp_path/'closure.json',run_root=tmp_path/'run',prepared=auth_args.prepared,result=tmp_path/'result.json',key=auth_args.supervisor_key,owner_key=auth_args.owner_key,owner_script=tmp_path/'unused.sh',config=auth_args.config,nonce='5a'*32,namespace='relational_measurement_v4_opened_development1',candidate_sha256=sha256_file(auth_args.config),launcher_pid=os.getpid(),timeout=100,post_timeout=1)
    real_sleep=time.sleep
    class Clock:
        now=0.0
        @classmethod
        def monotonic(cls):return cls.now
        @classmethod
        def sleep(cls,seconds):cls.now+=seconds;real_sleep(.0005)
    class FakeOwner:
        pid=34567
        def __init__(self,argv,cwd=None,env=None,start_new_session=None):
            self.env=env;self.publish_at=Clock.now+.95;self.published=False;auth=json.loads(x.authorization.read_text())['payload'];ready=json.loads(x.ready.read_text())['payload'];trigger=json.loads(x.start_signal.read_text())['payload']
            sign_exclusive(x.handoff,{'schema_version':'relational_measurement_v4_owner_handoff_v1','namespace':auth['namespace'],'nonce':x.nonce,'launcher_pid':ready['launcher_pid'],'supervisor_pid':ready['supervisor_pid'],'owner_pid':self.pid,'authorization_sha256':sha256_file(x.authorization),'supervisor_ready_sha256':sha256_file(x.ready),'launcher_trigger_sha256':sha256_file(x.start_signal)},auth_args.owner_key)
            sign_exclusive(x.opening,{'schema_version':'relational_measurement_v4_opening_v1','namespace':auth['namespace'],'nonce':x.nonce,'launcher_pid':ready['launcher_pid'],'supervisor_pid':ready['supervisor_pid'],'owner_pid':self.pid,'authorization_sha256':sha256_file(x.authorization),'supervisor_ready_sha256':sha256_file(x.ready),'launcher_trigger_sha256':sha256_file(x.start_signal),'handoff_sha256':sha256_file(x.handoff)},auth_args.owner_key)
        def poll(self):
            if not self.published and Clock.now>=self.publish_at:
                terminalize(argparse.Namespace(authorization=x.authorization,opening=x.opening,prepared=x.prepared,result=None,output=x.closure,key=auth_args.owner_key,nonce=x.nonce,technical_reason='FIT_FAILURE',partial_root=[]));self.published=True
            return None
    errors=[]
    def run():
        try:supervise(x)
        except Exception as exc:errors.append(exc)
    with mock.patch.object(lifecycle.time,'monotonic',Clock.monotonic),mock.patch.object(lifecycle.time,'sleep',Clock.sleep),mock.patch.object(lifecycle.subprocess,'Popen',FakeOwner),mock.patch.object(lifecycle,'stop_owner_group',return_value=0):
        thread=threading.Thread(target=run);thread.start()
        ready=wait_payload(x.ready,sleep=real_sleep);sign_exclusive(x.start_signal,{'schema_version':'relational_measurement_v4_launcher_trigger_v1','namespace':x.namespace,'nonce':x.nonce,'launcher_pid':x.launcher_pid,'supervisor_pid':ready['supervisor_pid'],'authorization_sha256':sha256_file(x.authorization),'supervisor_ready_sha256':sha256_file(x.ready)},auth_args.owner_key)
        thread.join(5)
    assert not thread.is_alive() and not errors and Clock.now>=.95
    assert verify_lifecycle_closure(x)=='TECHNICAL_TERMINAL'

def test_preexisting_valid_receipt_is_preserved(tmp_path):
    args,state=_trigger_timeout_state(tmp_path);before=sha256_file(state.closure)
    write_receipt(state,load_private_key(args.supervisor_key),'PREOPEN_OWNER_FAILURE',{'owner_pid':None,'exit_status':None,'detail_code':'TRIGGER_TIMEOUT','observed_error':None})
    assert sha256_file(state.closure)==before and verify_lifecycle_closure(state)=='SUPERVISOR_RECEIPT'

def test_preexisting_malformed_receipt_is_preserved_and_rejected(tmp_path):
    args,state=_trigger_timeout_state(tmp_path);payload=json.loads(state.closure.read_text())['payload'];payload['receipt']['status']['owner_alive']=True;_resign_closure(state.closure,payload,args.supervisor_key);before=sha256_file(state.closure)
    try:write_receipt(state,load_private_key(args.supervisor_key),'PREOPEN_OWNER_FAILURE',{'owner_pid':None,'exit_status':None,'detail_code':'TRIGGER_TIMEOUT','observed_error':None})
    except RuntimeError:pass
    else:raise AssertionError('malformed pre-existing receipt was accepted')
    assert sha256_file(state.closure)==before

CHAIN_MUTATIONS=[(artifact,mutation) for artifact in ('trigger','handoff','opening') for mutation in ('signature','replay','nonce','pid','hash')]

@pytest.mark.parametrize('artifact,mutation',CHAIN_MUTATIONS,ids=[f'{a}-{m}' for a,m in CHAIN_MUTATIONS])
def test_chain_rejects_artifact_mutation(tmp_path,artifact,mutation):
    args,state=_complete_technical_chain(tmp_path);paths={'trigger':state.start_signal,'handoff':state.handoff,'opening':state.opening};path=paths[artifact]
    if mutation=='replay':
        replay_root=tmp_path/'distinct-valid-lineage';replay_root.mkdir();nonce='77'*32;ready=replay_root/'ready.json';trigger=replay_root/'trigger.json';handoff=replay_root/'handoff.json';opening=replay_root/'opening.json';auth=json.loads(state.authorization.read_text())['payload']
        sign_exclusive(ready,{'schema_version':'relational_measurement_v4_supervisor_ready_v1','namespace':state.namespace,'nonce':nonce,'supervisor_pid':22334,'launcher_pid':11223,'candidate_sha256':sha256_file(state.config),'authorization_sha256':sha256_file(state.authorization)},args.supervisor_key)
        sign_exclusive(trigger,{'schema_version':'relational_measurement_v4_launcher_trigger_v1','namespace':state.namespace,'nonce':nonce,'launcher_pid':11223,'supervisor_pid':22334,'authorization_sha256':sha256_file(state.authorization),'supervisor_ready_sha256':sha256_file(ready)},args.owner_key)
        sign_exclusive(handoff,{'schema_version':'relational_measurement_v4_owner_handoff_v1','namespace':state.namespace,'nonce':nonce,'launcher_pid':11223,'supervisor_pid':22334,'owner_pid':33445,'authorization_sha256':sha256_file(state.authorization),'supervisor_ready_sha256':sha256_file(ready),'launcher_trigger_sha256':sha256_file(trigger)},args.owner_key)
        sign_exclusive(opening,{'schema_version':'relational_measurement_v4_opening_v1','namespace':state.namespace,'nonce':nonce,'launcher_pid':11223,'supervisor_pid':22334,'owner_pid':33445,'authorization_sha256':sha256_file(state.authorization),'supervisor_ready_sha256':sha256_file(ready),'launcher_trigger_sha256':sha256_file(trigger),'handoff_sha256':sha256_file(handoff)},args.owner_key)
        replay={'trigger':trigger,'handoff':handoff,'opening':opening}[artifact];path.unlink();path.write_bytes(replay.read_bytes())
    elif mutation=='signature':
        envelope=json.loads(path.read_text());sig=envelope['signature']['signature_base64'];envelope['signature']['signature_base64']=('A' if sig[:1]!='A' else 'B')+sig[1:];path.write_text(json.dumps(envelope,sort_keys=True))
    else:
        payload=json.loads(path.read_text())['payload']
        if mutation=='nonce':payload['nonce']='99'*32
        elif mutation=='pid':
            if artifact=='trigger':payload['launcher_pid']=999
            else:payload['owner_pid']=999
        elif mutation=='hash':payload[{'trigger':'supervisor_ready_sha256','handoff':'launcher_trigger_sha256','opening':'handoff_sha256'}[artifact]]='0'*64
        path.unlink();sign_exclusive(path,payload,args.owner_key)
    if artifact=='trigger':
        payload=json.loads(state.handoff.read_text())['payload'];payload['launcher_trigger_sha256']=sha256_file(state.start_signal);state.handoff.unlink();sign_exclusive(state.handoff,payload,args.owner_key)
    if artifact in ('trigger','handoff'):
        payload=json.loads(state.opening.read_text())['payload'];payload['launcher_trigger_sha256']=sha256_file(state.start_signal);payload['handoff_sha256']=sha256_file(state.handoff);state.opening.unlink();sign_exclusive(state.opening,payload,args.owner_key)
    closure=json.loads(state.closure.read_text())['payload'];closure['terminal']['opening_sha256']=sha256_file(state.opening);_resign_closure(state.closure,closure,args.owner_key)
    with pytest.raises(Exception):verify_lifecycle_closure(state)

def _diagnostic_panel(components,pairs_per_component,imbalanced=False):
    rows=[];pairs=[]
    for c in range(components):
        for j in range(pairs_per_component):
            pid=f'p{c}-{j}';edge=row(f'e{c}-{j}',pid);nonedge=copy.deepcopy(edge);edge['label']=1;nonedge['label']=0
            pairs.append({'pair_id':pid,'component_id':f'c{c}','edge':edge,'nonedge':nonedge})
            for treatment in (0,1):
                rows.append({'component_id':f'c{c}','pair_id':pid,'fold':c%5,'treatment':treatment,'surface_gap':(8+j%2) if imbalanced and treatment else 2+j%2,'relative_query':.4,'causal_fraction':.5,'sequence_length':20})
    X=np.zeros((len(rows),5));names=['surface_gap','relative_query','causal_fraction','sequence_length','lexical_hash_0']
    return rows,pairs,X,names

def test_balance_and_ess_thresholds_fail_closed():
    cfg=json.loads((ROOT/'configs/relational_measurement_v4/run.json').read_text());est=copy.deepcopy(cfg['estimators']);est['lexical_hash_width']=1
    good_prop={'raw_min':.5,'raw_max':.5,'central_fraction':1.,'weight_ratio':1.,'propensities':np.full(1,.5),'weights':np.full(1,.5)}
    with mock.patch.object(measurement,'propensity_diagnostics',return_value=good_prop):
        rows,pairs,X,names=_diagnostic_panel(100,5,True);bad_balance=diagnostics(rows,pairs,X,names,cfg['diagnostics'],est,cfg['seed'])
        rows,pairs,X,names=_diagnostic_panel(100,1,False);bad_ess=diagnostics(rows,pairs,X,names,cfg['diagnostics'],est,cfg['seed'])
    assert bad_balance['numeric_smd']['surface_gap']>cfg['diagnostics']['maximum_smd'] and bad_balance['eligible'] is False
    assert bad_ess['pair_ess']<cfg['diagnostics']['minimum_pair_ess'] and bad_ess['eligible'] is False

def test_support_and_diagnostics_reject_nonfinite_values_in_every_position():
    cfg=json.loads((ROOT/'configs/relational_measurement_v4/run.json').read_text());base={'components':100,'documents':200,'pairs':500,'orientations':{'later_query_is_head':250,'later_query_is_child':250},'fold_components':{str(i):20 for i in range(5)}}
    mutations=[]
    for key in ('0','4'):
        bad=copy.deepcopy(base);bad['fold_components'][key]=float('nan');mutations.append(bad)
    for key in ('later_query_is_head','later_query_is_child'):
        bad=copy.deepcopy(base);bad['orientations'][key]=float('inf');mutations.append(bad)
    bad=copy.deepcopy(base);bad['pairs']=True;mutations.append(bad)
    assert all(support_ok(x,cfg['matching'],cfg['diagnostics']) is False for x in mutations)
    rows,pairs,X,names=_diagnostic_panel(100,5,False);est=copy.deepcopy(cfg['estimators']);est['lexical_hash_width']=1;good_prop={'raw_min':.5,'raw_max':.5,'central_fraction':1.,'weight_ratio':1.,'propensities':np.full(len(rows),.5),'weights':np.full(len(rows),1/len(rows))}
    for key in ('surface_gap','relative_query','causal_fraction','sequence_length'):
        for index,value in ((0,float('nan')),(-1,float('inf'))):
            bad_rows=copy.deepcopy(rows);bad_rows[index][key]=value
            with mock.patch.object(measurement,'propensity_diagnostics',return_value=good_prop):
                with pytest.raises(RuntimeError):diagnostics(bad_rows,pairs,X,names,cfg['diagnostics'],est,cfg['seed'])
    bad_X=X.copy();bad_X[-1,-1]=float('nan')
    with pytest.raises(RuntimeError):diagnostics(rows,pairs,bad_X,names,cfg['diagnostics'],est,cfg['seed'])

def test_propensity_clipping_and_tail_gate_fail_closed():
    cfg=json.loads((ROOT/'configs/relational_measurement_v4/run.json').read_text());rows=[];values=[]
    for c in range(20):
        for treatment in (0,1):
            for j in range(2):
                rows.append({'component_id':f'c{c}','fold':c%5,'treatment':treatment});values.append([0.0 if (treatment==1 and c==0 and j==0) else 1.0 if treatment==1 else 1.0 if (c==0 and j==0) else 0.0])
    class IdentityScaler:
        def fit(self,X,sample_weight=None):return self
        def transform(self,X):return np.asarray(X,float)
    class ExtremeLogistic:
        def __init__(self,**kwargs):pass
        def fit(self,X,y,sample_weight=None):return self
        def predict_proba(self,X):
            p=np.where(np.asarray(X)[:,0]<.5,1e-12,1-1e-12);return np.column_stack([1-p,p])
    with mock.patch.object(measurement,'StandardScaler',IdentityScaler),mock.patch.object(measurement,'LogisticRegression',ExtremeLogistic):
        got=propensity_diagnostics(np.asarray(values),rows,cfg['seed'],cfg['estimators'],cfg['diagnostics'])
    assert np.all(np.isfinite(got['weights'])) and got['raw_min']==1e-12 and got['raw_max']==1-1e-12
    assert got['central_fraction']<cfg['diagnostics']['propensity_central_fraction'] and got['weight_ratio']>cfg['diagnostics']['maximum_overlap_weight_ratio']

def test_cross_fitted_scalers_and_models_never_fit_held_out_components():
    cfg=json.loads((ROOT/'configs/relational_measurement_v4/run.json').read_text());rows=[];pairs=[];X=[];y=[]
    for c in range(20):
        pid=f'p{c}';pairs.append({'pair_id':pid,'component_id':f'c{c}'})
        for treatment in (0,1):rows.append({'component_id':f'c{c}','pair_id':pid,'fold':c%5,'treatment':treatment});X.append([float(c%5),float(treatment)]);y.append(float(c+treatment))
    scaler_fits=[];logistic_fits=[];ridge_fits=[]
    class SpyScaler:
        def fit(self,X,sample_weight=None):scaler_fits.append(set(np.asarray(X)[:,0]));return self
        def transform(self,X):return np.asarray(X,float)
    class SpyLogistic:
        def __init__(self,**kwargs):pass
        def fit(self,X,y,sample_weight=None):logistic_fits.append(len(y));return self
        def predict_proba(self,X):return np.tile([.5,.5],(len(X),1))
    class SpyRidge:
        def __init__(self,**kwargs):self.coef_=None
        def fit(self,X,y,sample_weight=None):ridge_fits.append(len(y));self.coef_=np.zeros(np.asarray(X).shape[1]);return self
    with mock.patch.object(measurement,'StandardScaler',SpyScaler),mock.patch.object(measurement,'LogisticRegression',SpyLogistic),mock.patch.object(measurement,'Ridge',SpyRidge):
        propensity_diagnostics(np.asarray(X),rows,cfg['seed'],cfg['estimators'],cfg['diagnostics']);ridge_pair_values(np.asarray(X),np.asarray(y),rows,pairs,cfg['estimators'])
    assert len(scaler_fits)==10 and all(len(folds)==4 for folds in scaler_fits)
    assert sorted({tuple(sorted(x)) for x in scaler_fits})==[(0.0,1.0,2.0,3.0),(0.0,1.0,2.0,4.0),(0.0,1.0,3.0,4.0),(0.0,2.0,3.0,4.0),(1.0,2.0,3.0,4.0)]
    assert logistic_fits==[32]*5 and ridge_fits==[16]*5

def test_component_and_weighted_scaler_weights_are_exact():
    cfg=json.loads((ROOT/'configs/relational_measurement_v4/run.json').read_text());rows=[];pairs=[];X=[];y=[];pair_counts={}
    for c in range(10):
        n=1+c%3;pair_counts[f'c{c}']=n
        for j in range(n):
            pid=f'p{c}-{j}';pairs.append({'pair_id':pid,'component_id':f'c{c}'})
            for treatment in (0,1):rows.append({'component_id':f'c{c}','pair_id':pid,'fold':c%5,'treatment':treatment});X.append([float(c),float(treatment),float(j)]);y.append(float(c+j+treatment))
    bw=base_weights(rows);tw=treatment_weights(rows);expected=np.asarray([1/(2*len(pair_counts)*pair_counts[r['component_id']]) for r in rows])
    assert np.array_equal(bw,expected) and np.array_equal(tw,2*expected)
    assert all(math.isclose(float(tw[np.asarray([r['treatment']==g for r in rows])].sum()),1.0) for g in (0,1))
    RealScaler=measurement.StandardScaler;scaler_records=[];logistic_weights=[];ridge_weights=[]
    class WeightedSpyScaler:
        def __init__(self):self.inner=RealScaler()
        def fit(self,X,sample_weight=None):
            self.inner.fit(X,sample_weight=sample_weight);scaler_records.append((np.asarray(X).copy(),np.asarray(sample_weight).copy(),self.inner.mean_.copy()));return self
        def transform(self,X):return self.inner.transform(X)
    class WeightSpyLogistic:
        def __init__(self,**kwargs):pass
        def fit(self,X,y,sample_weight=None):logistic_weights.append(np.asarray(sample_weight).copy());return self
        def predict_proba(self,X):return np.tile([.5,.5],(len(X),1))
    class WeightSpyRidge:
        def __init__(self,**kwargs):self.coef_=None
        def fit(self,X,y,sample_weight=None):ridge_weights.append(np.asarray(sample_weight).copy());self.coef_=np.zeros(np.asarray(X).shape[1]);return self
    with mock.patch.object(measurement,'StandardScaler',WeightedSpyScaler),mock.patch.object(measurement,'LogisticRegression',WeightSpyLogistic),mock.patch.object(measurement,'Ridge',WeightSpyRidge):
        propensity_diagnostics(np.asarray(X),rows,cfg['seed'],cfg['estimators'],cfg['diagnostics']);ridge_pair_values(np.asarray(X),np.asarray(y),rows,pairs,cfg['estimators'])
    assert len(scaler_records)==10 and len(logistic_weights)==5 and len(ridge_weights)==5
    for i,(fit_X,weights,mean) in enumerate(scaler_records):
        components=fit_X[:,0].astype(int);raw=np.asarray([1/pair_counts[f'c{c}'] for c in components])
        expected_weights=raw*(len(raw)/raw.sum()) if i<5 else raw
        assert np.allclose(weights,expected_weights) and np.allclose(mean,np.average(fit_X,axis=0,weights=expected_weights))
        assert np.allclose(weights,logistic_weights[i] if i<5 else ridge_weights[i-5])

def test_canonical_null_positive_draw_attachment_identity():
    cfg=json.loads((ROOT/'configs/relational_measurement_v4/run.json').read_text())['simulation'];rows=[]
    for c in ('b','a'):
        for p in ('z','y'):
            for treatment in (1,0):rows.append({'source':'S','component_id':c,'pair_id':f'{c}-{p}','treatment':treatment})
    shuffled=[rows[i] for i in (5,0,7,2,1,6,3,4)]
    for positive in (False,True):
        comps,u,eps,v=replicate_draws(shuffled,'coarse_exact','linear',positive,17,3,cfg);rng=np.random.Generator(np.random.PCG64(sha256_u64(17,'S','coarse_exact','linear','positive' if positive else 'null',3,'noise')))
        expected_u=rng.standard_normal(2)*cfg['component_intercept_sd'];expected_eps=rng.standard_normal(len(shuffled))*cfg['row_noise_sd'];order=sorted(range(len(shuffled)),key=lambda i:(shuffled[i]['component_id'],shuffled[i]['pair_id'],shuffled[i]['treatment']))
        assert comps==['a','b'] and np.array_equal(u,expected_u) and np.array_equal(eps[np.asarray(order)],expected_eps)
        if positive:assert np.array_equal(v,rng.standard_normal(2)*cfg['component_treatment_sd'])
        else:assert v is None

def test_benchmark_selects_largest_full_width_panel_with_stable_tie_break(tmp_path):
    cfg=json.loads((ROOT/'configs/relational_measurement_v4/run.json').read_text());methods={'coarse_exact':{'sources':{}},'optimal_caliper':{'sources':{}}};scheduled=[('coarse_exact','A'),('optimal_caliper','B')]
    for index,(method,source) in enumerate(scheduled):
        rows=[]
        for i in range(2):
            r=row(f'{source}{i}',f'p{i}');r.update({'component_id':f'c{i}','pair_id':f'p{i}','fold':i,'treatment':i%2,'source':source});rows.append(r)
        if index:rows[1]['later']['upos']='VERB'
        panel={'rows':rows,'pairs':[{}]*(index+1),'components':[{}]*(index+1)};path=tmp_path/f'{source}.json';path.write_text(json.dumps(panel));methods[method]['sources'][source]={'panel':{'path':str(path)}}
    method,source,_,_,_,descriptor=select_benchmark_panel(scheduled,methods,cfg)
    assert (method,source)==('optimal_caliper','B') and descriptor['feature_count']>0 and descriptor['schedule_index']==1
