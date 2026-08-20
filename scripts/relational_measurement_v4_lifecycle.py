#!/usr/bin/env python3
"""Signed create-once lifecycle for relational measurement v4."""
from __future__ import annotations
import argparse,hashlib,math,os,signal,subprocess,sys,tempfile,time,xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any,Mapping
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from relational_objects_v3 import ROOT, canonical_bytes, exclusive_json, load_json, load_private_key, sha256_file, signed_payload, verify_signed

TECH_REASONS={'REFERENCE_DRIFT','HASH_DRIFT','SOURCE_ERROR','FIT_FAILURE','NONFINITE','RESOURCE_LIMIT','UNEXPECTED_EXCEPTION'}
REQUIRED_V4_TESTS={
    'test_primary_simulation_probability_schema_is_strict',
    'test_terminal_and_verifier_reject_impossible_probability_summaries',
    'test_strict_receipt_status_schema_and_pid_binding',
    'test_supervisor_trigger_timeout_closes_with_strict_preopen_receipt',
    'test_supervisor_closes_preopening_owner_failure_with_exit_status',
    'test_supervisor_invalid_handoff_publishes_verifiable_prefix_receipt',
    'test_supervisor_invalid_opening_publishes_verifiable_prefix_receipt',
    'test_supervisor_missing_opening_publishes_verifiable_prefix_receipt',
    'test_supervisor_times_out_hung_opened_owner_and_writes_receipt',
    'test_supervisor_missing_terminal_after_opening_writes_receipt',
    'test_supervisor_rejects_invalid_immutable_postopening_terminal',
    'test_supervisor_accepts_valid_owner_technical_closure',
    'test_supervisor_accepts_terminal_published_at_deadline_boundary',
    'test_preexisting_valid_receipt_is_preserved',
    'test_preexisting_malformed_receipt_is_preserved_and_rejected',
    *{f'test_chain_rejects_artifact_mutation[{artifact}-{mutation}]' for artifact in ('trigger','handoff','opening') for mutation in ('signature','replay','nonce','pid','hash')},
    'test_balance_and_ess_thresholds_fail_closed',
    'test_support_and_diagnostics_reject_nonfinite_values_in_every_position',
    'test_propensity_clipping_and_tail_gate_fail_closed',
    'test_cross_fitted_scalers_and_models_never_fit_held_out_components',
    'test_component_and_weighted_scaler_weights_are_exact',
    'test_canonical_null_positive_draw_attachment_identity',
    'test_authorization_rejects_malformed_benchmark_evidence',
}

def _strict_number(value:Any)->bool:
    return not isinstance(value,bool) and isinstance(value,(int,float)) and math.isfinite(value)

def _positive_int(value:Any)->bool:
    return not isinstance(value,bool) and isinstance(value,int) and value>0

def _exit_status(value:Any)->bool:
    return value is None or (not isinstance(value,bool) and isinstance(value,int))

def _optional_string(value:Any)->bool:
    return value is None or isinstance(value,str)

def _sha256_hex(value:Any)->bool:
    return isinstance(value,str) and len(value)==64 and all(c in '0123456789abcdef' for c in value)

def _nonce_hex(value:Any)->bool:
    return _sha256_hex(value)
def artifact_path(path:Path)->str:return path.relative_to(ROOT).as_posix() if path.is_relative_to(ROOT) else str(path)
def keygen(path:Path)->str:
    key=Ed25519PrivateKey.generate();raw=key.private_bytes(serialization.Encoding.PEM,serialization.PrivateFormat.PKCS8,serialization.NoEncryption());path.parent.mkdir(parents=True,exist_ok=True);fd=os.open(path,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
    try:os.write(fd,raw);os.fsync(fd)
    finally:os.close(fd)
    pub=key.public_key().public_bytes(serialization.Encoding.Raw,serialization.PublicFormat.Raw);return hashlib.sha256(pub).hexdigest()
def fingerprint(key_or_path:Ed25519PrivateKey|Path)->str:
    key=load_private_key(key_or_path) if isinstance(key_or_path,Path) else key_or_path;pub=key.public_key().public_bytes(serialization.Encoding.Raw,serialization.PublicFormat.Raw);return hashlib.sha256(pub).hexdigest()
def sign_exclusive(path:Path,payload:Mapping[str,Any],key_or_path:Ed25519PrivateKey|Path)->None:
    key=load_private_key(key_or_path) if isinstance(key_or_path,Path) else key_or_path;exclusive_json(path,signed_payload(dict(payload),key))
def sign_atomic_closure(path:Path,payload:Mapping[str,Any],key_or_path:Ed25519PrivateKey|Path)->None:
    key=load_private_key(key_or_path) if isinstance(key_or_path,Path) else key_or_path;raw=canonical_bytes(signed_payload(dict(payload),key))+b'\n';path.parent.mkdir(parents=True,exist_ok=True)
    fd,tmp=tempfile.mkstemp(dir=path.parent,prefix=f'.{path.name}.closure.')
    try:
        with os.fdopen(fd,'wb',closefd=True) as stream:stream.write(raw);stream.flush();os.fsync(stream.fileno())
        os.link(tmp,path);directory=os.open(path.parent,os.O_DIRECTORY);os.fsync(directory);os.close(directory)
    finally:
        try:os.unlink(tmp)
        except FileNotFoundError:pass

def inventory(paths:list[Path])->list[dict[str,Any]]:
    files=[]
    for root in paths:
        if root.is_file():files.append(root)
        elif root.is_dir():files.extend(p for p in root.rglob('*') if p.is_file())
    return [{'path':p.relative_to(ROOT).as_posix() if p.is_relative_to(ROOT) else str(p),'sha256':sha256_file(p),'bytes':p.stat().st_size} for p in sorted(set(files))]
def write_receipt(args:Any,key:Ed25519PrivateKey,reason:str,status:dict[str,Any])->None:
    if args.closure.exists():
        verify_lifecycle_closure(args)
        return
    status={'authorization_present':args.authorization.exists(),'ready_present':args.ready.exists(),'trigger_present':args.start_signal.exists(),'handoff_present':args.handoff.exists(),'opening_present':args.opening.exists(),'owner_pid':status.get('owner_pid'),'exit_status':status.get('exit_status'),'owner_alive':False,'postopening_timeout':bool(status.get('postopening_timeout',False)),'detail_code':status['detail_code'],'observed_error':status.get('observed_error')}
    receipt={'schema_version':'relational_measurement_v4_supervisor_receipt_v1','reason':reason,'status':status,'partial_artifacts':inventory([args.run_root,args.prepared,args.authorization,args.ready,args.start_signal,args.handoff,args.opening]),'scientific_result':False,'retry_authorized':False}
    sign_atomic_closure(args.closure,{'schema_version':'relational_measurement_v4_closure_v1','kind':'SUPERVISOR_RECEIPT','namespace':args.namespace,'nonce':args.nonce,'authorization_sha256':sha256_file(args.authorization),'signer_fingerprint':fingerprint(key),'receipt':receipt},key)
    verify_lifecycle_closure(args)

def stop_owner_group(child:subprocess.Popen[Any],grace:float=5.0)->int:
    pgid=child.pid
    try:os.killpg(child.pid,signal.SIGTERM)
    except ProcessLookupError:pass
    try:status=child.wait(timeout=grace)
    except subprocess.TimeoutExpired:
        try:os.killpg(child.pid,signal.SIGKILL)
        except ProcessLookupError:pass
        status=child.wait(timeout=grace)
    deadline=time.monotonic()+grace
    while time.monotonic()<deadline:
        try:os.killpg(pgid,0)
        except ProcessLookupError:return status
        time.sleep(.05)
    try:os.killpg(pgid,signal.SIGKILL)
    except ProcessLookupError:return status
    deadline=time.monotonic()+grace
    while time.monotonic()<deadline:
        try:os.killpg(pgid,0)
        except ProcessLookupError:return status
        time.sleep(.05)
    raise RuntimeError('owner process group survived SIGKILL')

def verify_lifecycle_closure(x:Any)->str:
    auth0=verify_signed(x.authorization);auth=verify_signed(x.authorization,auth0['owner_fingerprint'])
    auth_keys={'schema_version','namespace','config','prepared','benchmark','tests','smoke_a','smoke_b','candidate_review','owner_fingerprint','supervisor_fingerprint','retry_authorized'}
    if set(auth)!=auth_keys or auth.get('schema_version')!='relational_measurement_v4_authorization_v1' or auth.get('namespace')!=x.namespace or auth['retry_authorized'] is not False or set(auth['config'])!={'path','sha256'} or set(auth['prepared'])!={'path','sha256'}:raise RuntimeError('invalid authorization closure binding')
    config_path=ROOT/auth['config']['path'] if not Path(auth['config']['path']).is_absolute() else Path(auth['config']['path']);prepared_path=ROOT/auth['prepared']['path'] if not Path(auth['prepared']['path']).is_absolute() else Path(auth['prepared']['path'])
    if config_path!=x.config or prepared_path!=x.prepared or sha256_file(config_path)!=auth['config']['sha256'] or sha256_file(prepared_path)!=auth['prepared']['sha256']:raise RuntimeError('authorized config/prepared drift')
    for field in ('tests','smoke_a','smoke_b','candidate_review'):
        ref=auth[field]
        if set(ref)!={'path','sha256'}:raise RuntimeError('invalid authorization reference schema')
        path=ROOT/ref['path'] if not Path(ref['path']).is_absolute() else Path(ref['path'])
        if not path.is_file() or sha256_file(path)!=ref['sha256']:raise RuntimeError('authorization prerequisite drift')
    if canonical_bytes(auth['benchmark'])!=canonical_bytes(load_json(prepared_path)['benchmark']):raise RuntimeError('authorization benchmark drift')
    def chain(level:int)->tuple[dict[str,Any]|None,dict[str,Any]|None,dict[str,Any]|None,dict[str,Any]|None]:
        ready=trigger=handoff=opening=None
        if level>=1:
            if not x.ready.exists():raise RuntimeError('required ready absent')
            ready=verify_signed(x.ready,auth['supervisor_fingerprint'])
            if set(ready)!={'schema_version','namespace','nonce','supervisor_pid','launcher_pid','candidate_sha256','authorization_sha256'} or ready.get('schema_version')!='relational_measurement_v4_supervisor_ready_v1' or ready['namespace']!=auth['namespace'] or ready['nonce']!=x.nonce or not _nonce_hex(ready['nonce']) or not _positive_int(ready['supervisor_pid']) or not _positive_int(ready['launcher_pid']) or ready['authorization_sha256']!=sha256_file(x.authorization) or ready['candidate_sha256']!=auth['config']['sha256']:raise RuntimeError('invalid ready chain')
        if level>=2:
            if not x.start_signal.exists():raise RuntimeError('required trigger absent')
            trigger=verify_signed(x.start_signal,auth['owner_fingerprint'])
            if set(trigger)!={'schema_version','namespace','nonce','launcher_pid','supervisor_pid','authorization_sha256','supervisor_ready_sha256'} or trigger.get('schema_version')!='relational_measurement_v4_launcher_trigger_v1' or trigger['namespace']!=auth['namespace'] or trigger['nonce']!=x.nonce or not _nonce_hex(trigger['nonce']) or not _positive_int(trigger['launcher_pid']) or not _positive_int(trigger['supervisor_pid']) or trigger['authorization_sha256']!=sha256_file(x.authorization) or trigger['supervisor_ready_sha256']!=sha256_file(x.ready) or trigger['launcher_pid']!=ready['launcher_pid'] or trigger['supervisor_pid']!=ready['supervisor_pid']:raise RuntimeError('invalid trigger chain')
        if level>=3:
            if not x.handoff.exists():raise RuntimeError('required handoff absent')
            handoff=verify_signed(x.handoff,auth['owner_fingerprint'])
            if set(handoff)!={'schema_version','namespace','nonce','launcher_pid','supervisor_pid','owner_pid','authorization_sha256','supervisor_ready_sha256','launcher_trigger_sha256'} or handoff.get('schema_version')!='relational_measurement_v4_owner_handoff_v1' or handoff['namespace']!=auth['namespace'] or handoff['nonce']!=x.nonce or not _nonce_hex(handoff['nonce']) or not _positive_int(handoff['launcher_pid']) or not _positive_int(handoff['supervisor_pid']) or not _positive_int(handoff['owner_pid']) or handoff['authorization_sha256']!=sha256_file(x.authorization) or handoff['supervisor_ready_sha256']!=sha256_file(x.ready) or handoff['launcher_trigger_sha256']!=sha256_file(x.start_signal) or handoff['launcher_pid']!=ready['launcher_pid'] or handoff['supervisor_pid']!=ready['supervisor_pid']:raise RuntimeError('invalid handoff chain')
        if level>=4:
            if not x.opening.exists():raise RuntimeError('required opening absent')
            opening=verify_signed(x.opening,auth['owner_fingerprint'])
            if set(opening)!={'schema_version','namespace','nonce','launcher_pid','supervisor_pid','owner_pid','authorization_sha256','supervisor_ready_sha256','launcher_trigger_sha256','handoff_sha256'} or opening.get('schema_version')!='relational_measurement_v4_opening_v1' or opening['namespace']!=auth['namespace'] or opening['nonce']!=x.nonce or not _nonce_hex(opening['nonce']) or not _positive_int(opening['launcher_pid']) or not _positive_int(opening['supervisor_pid']) or not _positive_int(opening['owner_pid']) or opening['authorization_sha256']!=sha256_file(x.authorization) or opening['supervisor_ready_sha256']!=sha256_file(x.ready) or opening['launcher_trigger_sha256']!=sha256_file(x.start_signal) or opening['handoff_sha256']!=sha256_file(x.handoff) or opening['launcher_pid']!=ready['launcher_pid'] or opening['supervisor_pid']!=ready['supervisor_pid'] or opening['owner_pid']!=handoff['owner_pid']:raise RuntimeError('invalid opening chain')
        return ready,trigger,handoff,opening
    if not x.closure.exists():raise RuntimeError('authoritative closure absent')
    unsigned=verify_signed(x.closure);kind=unsigned.get('kind')
    if kind=='OWNER_TERMINAL':
        closure=verify_signed(x.closure,auth['owner_fingerprint']);chain(4)
        if set(closure)!={'schema_version','kind','namespace','nonce','authorization_sha256','signer_fingerprint','terminal'} or closure['schema_version']!='relational_measurement_v4_closure_v1' or closure['namespace']!=auth['namespace'] or closure['nonce']!=x.nonce or closure['authorization_sha256']!=sha256_file(x.authorization) or closure['signer_fingerprint']!=auth['owner_fingerprint']:raise RuntimeError('invalid owner closure')
        term=closure['terminal'];common={'schema_version','namespace','nonce','authorization_sha256','opening_sha256','prepared_sha256','retry_authorized','fresh_corpus_accessed','model_forward_run','training_run','status','scientific_result'};scientific=common|{'result','decision','nomination'};technical=common|{'reason','quarantined_partial_artifacts'}
        if set(term) not in (scientific,technical) or term['schema_version']!='relational_measurement_v4_terminal_v1' or term['namespace']!=auth['namespace'] or term['nonce']!=x.nonce or term['authorization_sha256']!=sha256_file(x.authorization) or term['opening_sha256']!=sha256_file(x.opening) or term['prepared_sha256']!=auth['prepared']['sha256'] or term['retry_authorized'] is not False or term['fresh_corpus_accessed'] is not False or term['model_forward_run'] is not False or term['training_run'] is not False:raise RuntimeError('invalid terminal body binding')
        if term['status']=='TERMINAL_COMPLETE' and set(term)==scientific and term['scientific_result'] is True:
            result_path=ROOT/term['result']['path'] if not Path(term['result']['path']).is_absolute() else Path(term['result']['path'])
            if sha256_file(result_path)!=term['result']['sha256']:raise RuntimeError('terminal result drift')
            result=load_json(result_path);decision,nomination=validate_scientific_result(result,auth,x.nonce,x.prepared)
            if set(term['result'])!={'path','sha256'} or term['result']['path']!=artifact_path(result_path):raise RuntimeError('invalid terminal result reference')
            if result.get('decision')!=decision or canonical_bytes(result.get('nomination'))!=canonical_bytes(nomination) or term['decision']!=decision or canonical_bytes(term['nomination'])!=canonical_bytes(nomination):raise RuntimeError('terminal decision mismatch')
            return 'SCIENTIFIC_TERMINAL'
        if term['status']=='TERMINAL_TECHNICAL_FAILURE' and set(term)==technical and term['scientific_result'] is False and term['reason'] in TECH_REASONS:
            if canonical_bytes(term['quarantined_partial_artifacts'])!=canonical_bytes(inventory([x.run_root,x.prepared])):raise RuntimeError('technical quarantine inventory incomplete or drifted')
            return 'TECHNICAL_TERMINAL'
        raise RuntimeError('invalid terminal body')
    if kind!='SUPERVISOR_RECEIPT':raise RuntimeError('unknown closure kind')
    closure=verify_signed(x.closure,auth['supervisor_fingerprint'])
    if set(closure)!={'schema_version','kind','namespace','nonce','authorization_sha256','signer_fingerprint','receipt'} or closure['schema_version']!='relational_measurement_v4_closure_v1' or closure['namespace']!=auth['namespace'] or closure['nonce']!=x.nonce or closure['authorization_sha256']!=sha256_file(x.authorization) or closure['signer_fingerprint']!=auth['supervisor_fingerprint']:raise RuntimeError('invalid supervisor closure')
    receipt=closure['receipt'];expected_status={'authorization_present','ready_present','trigger_present','handoff_present','opening_present','owner_pid','exit_status','owner_alive','postopening_timeout','detail_code','observed_error'}
    if set(receipt)!={'schema_version','reason','status','partial_artifacts','scientific_result','retry_authorized'} or receipt['schema_version']!='relational_measurement_v4_supervisor_receipt_v1' or set(receipt['status'])!=expected_status or receipt['status']['owner_alive'] is not False or receipt['scientific_result'] is not False or receipt['retry_authorized'] is not False:raise RuntimeError('invalid receipt body')
    status=receipt['status']
    if any(not isinstance(status[k],bool) for k in ('authorization_present','ready_present','trigger_present','handoff_present','opening_present','owner_alive','postopening_timeout')) or not _exit_status(status['exit_status']) or not _optional_string(status['observed_error']):raise RuntimeError('invalid receipt status types')
    for name,path in (('authorization',x.authorization),('ready',x.ready),('trigger',x.start_signal),('handoff',x.handoff),('opening',x.opening)):
        if receipt['status'][name+'_present'] is not path.exists():raise RuntimeError('receipt presence truth-table mismatch')
    detail=status['detail_code'];levels={'TRIGGER_TIMEOUT':1,'HANDOFF_MISSING':2,'HANDOFF_INVALID':2,'OPENING_MISSING':3,'OPENING_INVALID':3,'TERMINAL_MISSING':4}
    if detail not in levels:raise RuntimeError('unknown receipt detail code')
    if not status['authorization_present'] or not status['ready_present'] or (detail!='TRIGGER_TIMEOUT' and not status['trigger_present']):raise RuntimeError('invalid receipt artifact prefix')
    if detail.endswith('_INVALID') and (not isinstance(status['observed_error'],str) or not status['observed_error']):raise RuntimeError('invalid transition lacks error evidence')
    if detail in {'HANDOFF_MISSING','OPENING_MISSING','TERMINAL_MISSING'} and status['observed_error'] is not None:raise RuntimeError('missing transition has spurious error evidence')
    _,_,handoff,opening=chain(levels[detail])
    if detail=='TRIGGER_TIMEOUT':
        if status['owner_pid'] is not None or status['exit_status'] is not None or status['postopening_timeout'] or x.handoff.exists() or x.opening.exists():raise RuntimeError('invalid trigger-timeout status')
        if x.start_signal.exists():
            try:chain(2)
            except Exception:pass
            else:raise RuntimeError('trigger-timeout receipt follows a valid trigger')
    else:
        if not _positive_int(status['owner_pid']) or not isinstance(status['exit_status'],int) or isinstance(status['exit_status'],bool):raise RuntimeError('invalid spawned-owner status')
        if status['postopening_timeout'] and detail!='TERMINAL_MISSING':raise RuntimeError('preopening receipt marked postopening timeout')
    if detail=='HANDOFF_MISSING' and x.handoff.exists():raise RuntimeError('missing handoff receipt has handoff artifact')
    if detail=='HANDOFF_INVALID' and not x.handoff.exists():raise RuntimeError('invalid handoff receipt lacks artifact')
    if detail=='HANDOFF_INVALID':
        try:_,_,candidate_handoff,_=chain(3)
        except Exception:pass
        else:
            if candidate_handoff['owner_pid']==status['owner_pid']:raise RuntimeError('invalid-handoff receipt follows a valid handoff')
    if detail.startswith('HANDOFF_') and x.opening.exists():raise RuntimeError('opening after failed handoff')
    if detail=='OPENING_MISSING' and x.opening.exists():raise RuntimeError('missing opening receipt has opening artifact')
    if detail=='OPENING_INVALID' and not x.opening.exists():raise RuntimeError('invalid opening receipt lacks artifact')
    if detail=='OPENING_INVALID':
        try:_,_,_,candidate_opening=chain(4)
        except Exception:pass
        else:
            if candidate_opening['owner_pid']==status['owner_pid']:raise RuntimeError('invalid-opening receipt follows a valid opening')
    if handoff is not None and status['owner_pid']!=handoff['owner_pid']:raise RuntimeError('receipt/handoff owner PID mismatch')
    if opening is not None and status['owner_pid']!=opening['owner_pid']:raise RuntimeError('receipt/opening owner PID mismatch')
    if levels[detail]==4:
        if receipt['reason']!='OWNER_TERMINALIZATION_FAILURE':raise RuntimeError('opened receipt reason mismatch')
    elif receipt['reason']!='PREOPEN_OWNER_FAILURE':raise RuntimeError('preopen receipt reason mismatch')
    expected_inventory=inventory([x.run_root,x.prepared,x.authorization,x.ready,x.start_signal,x.handoff,x.opening])
    if canonical_bytes(receipt['partial_artifacts'])!=canonical_bytes(expected_inventory):raise RuntimeError('receipt inventory incomplete or drifted')
    return 'SUPERVISOR_RECEIPT'

def _cell_pass(cell:Mapping[str,Any],positive:bool,cfg:Mapping[str,Any])->bool:
    required={'replicates','bias','coverage','rejection','power','finite'}
    if set(cell)!=required or isinstance(cell['replicates'],bool) or not isinstance(cell['replicates'],int) or cell['replicates']!=cfg['replicates'] or not isinstance(cell['finite'],bool) or any(not _strict_number(cell[k]) for k in ('bias','coverage','rejection')) or not 0<=cell['coverage']<=1 or not 0<=cell['rejection']<=1:raise RuntimeError('invalid primary simulation cell')
    if positive:
        if not _strict_number(cell['power']) or not 0<=cell['power']<=1:raise RuntimeError('invalid positive simulation power')
    elif cell['power'] is not None:raise RuntimeError('null simulation power must be null')
    fractions=[cell['coverage'],cell['rejection']]+([cell['power']] if positive else [])
    if any(not math.isclose(value*cell['replicates'],round(value*cell['replicates']),rel_tol=0.0,abs_tol=1e-9) for value in fractions):raise RuntimeError('simulation fraction is off the replicate lattice')
    if positive:
        if cell['power']>cell['rejection']+1e-12:raise RuntimeError('positive power exceeds total rejection')
    elif not math.isclose(cell['coverage']+cell['rejection'],1.0,rel_tol=0.0,abs_tol=1e-12):raise RuntimeError('null coverage and rejection are not complementary')
    return bool(cell['finite'] and abs(cell['bias'])<=(cfg['positive_max_abs_bias'] if positive else cfg['null_max_abs_bias']) and cfg['coverage_min']<=cell['coverage']<=cfg['coverage_max'] and ((cell['power'] is not None and cell['power']>=cfg['positive_min_power']) if positive else cell['power'] is None and cell['rejection']<=cfg['null_max_rejection']))

def recompute_decision(result:Mapping[str,Any],prepared:Mapping[str,Any],cfg:Mapping[str,Any])->tuple[str,dict[str,Any]|None]:
    if canonical_bytes(result.get('methods'))!=canonical_bytes(prepared.get('methods')) or canonical_bytes(result.get('benchmark'))!=canonical_bytes(prepared.get('benchmark')):raise RuntimeError('result/prepared content mismatch')
    expected_methods={m for m in ('coarse_exact','optimal_caliper') if len(prepared['methods'][m]['selected_sources'])==2}
    if set(result.get('simulations',{}))!=expected_methods:raise RuntimeError('simulation schedule mismatch')
    pass_table={}
    for method in expected_methods:
        selected=prepared['methods'][method]['selected_sources']
        if len(set(selected))!=2 or any(s not in cfg['sources'] for s in selected) or set(result['simulations'][method])!=set(selected):raise RuntimeError('selected source mismatch')
        for source in selected:
            cells=result['simulations'][method][source]
            if set(cells)!=set(cfg['simulation']['dgps']):raise RuntimeError('DGP schedule mismatch')
            for dgp in cfg['simulation']['dgps']:
                if set(cells[dgp])!=set(cfg['estimators']['order'])|{'overlap_ato_descriptive'}:raise RuntimeError('estimator schedule mismatch')
                overlap=cells[dgp]['overlap_ato_descriptive']
                if set(overlap)!= {'replicates','mean_estimate','mean_true_target','bias','finite','nominating'} or overlap.get('nominating') is not False or isinstance(overlap.get('replicates'),bool) or not isinstance(overlap.get('replicates'),int) or overlap.get('replicates')!=cfg['simulation']['replicates'] or overlap.get('finite') is not True or any(not _strict_number(overlap[k]) for k in ('mean_estimate','mean_true_target','bias')):raise RuntimeError('invalid overlap cell')
                for estimator in cfg['estimators']['order']:
                    pass_table[(method,source,dgp,estimator)]=_cell_pass(cells[dgp][estimator],dgp.endswith('positive'),cfg['simulation'])
    nomination=None
    for method in cfg['matching']['methods']:
        if method not in expected_methods:continue
        selected=prepared['methods'][method]['selected_sources']
        for estimator in cfg['estimators']['order']:
            if all(pass_table[(method,source,dgp,estimator)] for source in selected for dgp in cfg['simulation']['dgps']):nomination={'matcher':method,'estimator':estimator,'sources':selected};break
        if nomination:break
    if nomination:return 'NOMINATE_MEASUREMENT_DESIGN_FOR_FRESH_PREREGISTRATION',nomination
    structurally_supported=any(sum(bool(x.get('support_eligible')) for x in prepared['methods'][m]['sources'].values())>=2 for m in cfg['matching']['methods'])
    return ('STOP_MEASUREMENT_DESIGN_UNCALIBRATED' if structurally_supported else 'STOP_MEASUREMENT_DESIGN_UNDER_SUPPORTED'),None

def validate_scientific_result(result:Mapping[str,Any],auth:Mapping[str,Any],nonce:str,prepared_path:Path)->tuple[str,dict[str,Any]|None]:
    allowed={'NOMINATE_MEASUREMENT_DESIGN_FOR_FRESH_PREREGISTRATION','STOP_MEASUREMENT_DESIGN_UNDER_SUPPORTED','STOP_MEASUREMENT_DESIGN_UNCALIBRATED'};keys={'schema_version','namespace','owner_nonce','config_sha256','prepared','decision','nomination','simulations','methods','benchmark','model_weights_loaded','model_forward_run','activation_cache_accessed','fresh_corpus_accessed','training_run','learned_model_authorized'}
    if set(result)!=keys or set(result.get('prepared',{}))!={'path','sha256'} or result.get('schema_version')!='relational_measurement_v4_result_v1' or result.get('namespace')!=auth['namespace'] or result.get('decision') not in allowed:raise RuntimeError('invalid result schema/decision')
    expected_path=artifact_path(prepared_path)
    if result['owner_nonce']!=nonce or result['config_sha256']!=auth['config']['sha256'] or result['prepared']!={'path':expected_path,'sha256':auth['prepared']['sha256']}:raise RuntimeError('result/auth binding mismatch')
    if any(result.get(k) is not False for k in ('model_weights_loaded','model_forward_run','activation_cache_accessed','fresh_corpus_accessed','training_run','learned_model_authorized')):raise RuntimeError('forbidden result flag')
    cfg_path=ROOT/auth['config']['path'] if not Path(auth['config']['path']).is_absolute() else Path(auth['config']['path'])
    if sha256_file(cfg_path)!=auth['config']['sha256'] or sha256_file(prepared_path)!=auth['prepared']['sha256']:raise RuntimeError('result provenance drift')
    decision,nomination=recompute_decision(result,load_json(prepared_path),load_json(cfg_path))
    if result['decision']!=decision or canonical_bytes(result.get('nomination'))!=canonical_bytes(nomination):raise RuntimeError('result decision does not follow frozen gates')
    return decision,nomination

def authorize(x:Any)->None:
    cfg=load_json(x.config)
    for name,item in cfg['identity'].items():
        p=ROOT/item['path']
        if not p.is_file() or sha256_file(p)!=item['sha256']:raise RuntimeError(f'identity drift: {name}')
    prep=load_json(x.prepared)
    if prep.get('config_sha256')!=sha256_file(x.config):raise RuntimeError('unbound prepared artifact')
    from run_relational_measurement_v4 import validate_benchmark_evidence
    validate_benchmark_evidence(prep.get('benchmark'),cfg)
    if prep.get('schema_version')!='relational_measurement_v4_prepared_v1' or prep.get('namespace')!=cfg['namespace'] or set(prep.get('methods',{}))!=set(cfg['matching']['methods']):raise RuntimeError('invalid prepared schema')
    for method in cfg['matching']['methods']:
        if set(prep['methods'][method].get('sources',{}))!=set(cfg['source_selection_order']):raise RuntimeError('incomplete prepared sources')
        for source,item in prep['methods'][method]['sources'].items():
            panel=ROOT/item['panel']['path'] if not Path(item['panel']['path']).is_absolute() else Path(item['panel']['path'])
            if not panel.is_file() or sha256_file(panel)!=item['panel']['sha256']:raise RuntimeError('prepared panel drift')
    bench=prep['benchmark']
    if sha256_file(x.smoke_a)!=sha256_file(x.smoke_b):raise RuntimeError('smoke reports differ')
    smoke=load_json(x.smoke_a)
    if smoke.get('schema_version')!='relational_measurement_v4_smoke_v1' or smoke.get('status')!='PASS' or smoke.get('config_sha256')!=sha256_file(x.config) or smoke.get('source')!='ENGLISH_GENTLE' or set(smoke.get('methods',{}))!=set(cfg['matching']['methods']) or any(smoke.get(k) for k in ('model_weights_loaded','model_forward_run','fresh_corpus_accessed','training_run')):raise RuntimeError('invalid smoke evidence')
    for method,item in smoke['methods'].items():
        if set(item)!= {'support','truncation','components_sha256'} or not isinstance(item['support'],dict) or not {'components','documents','pairs','orientations','fold_components'}<=set(item['support']) or len(item['components_sha256'])!=64 or any(c not in '0123456789abcdef' for c in item['components_sha256']):raise RuntimeError('invalid matcher smoke body')
    root=ET.parse(x.test_report).getroot();suites=[root] if root.tag=='testsuite' else list(root.iter('testsuite'))
    tests=sum(int(s.attrib.get('tests',0)) for s in suites if s is not root or root.tag=='testsuite');fail=sum(int(s.attrib.get('failures',0))+int(s.attrib.get('errors',0)) for s in suites if s is not root or root.tag=='testsuite');cases=list(root.iter('testcase'))
    if tests<int(cfg['runtime']['minimum_test_count']) or len(cases)!=tests or fail!=0 or any(list(c.iter('failure')) or list(c.iter('error')) for c in cases):raise RuntimeError('invalid test evidence')
    case_names={c.attrib.get('name') for c in cases}
    if not REQUIRED_V4_TESTS<=case_names:raise RuntimeError(f'missing required v4 tests: {sorted(REQUIRED_V4_TESTS-case_names)}')
    if x.candidate_review.read_text().splitlines()[0].strip()!='VERDICT: SHIP':raise RuntimeError('candidate review did not SHIP')
    from run_relational_measurement_v4 import validate_prepared_content
    validate_prepared_content(cfg,prep,x.config)
    if getattr(x,'live_verify',True):
        with tempfile.TemporaryDirectory(dir=x.output.parent,prefix='.v4-live-evidence.') as td:
            live_xml=Path(td)/'tests.xml';env=os.environ.copy();env['PYTHONPATH']=f'{ROOT}:{ROOT/"scripts"}'
            subprocess.run([sys.executable,'-m','pytest','-q',f'--junitxml={live_xml}','tests/test_relational_measurement_v4.py','tests/test_relational_objects_v3_scout.py','tests/test_relational_objects_v2.py','tests/test_conllu_spec.py'],cwd=ROOT,env=env,check=True,stdout=subprocess.DEVNULL)
            live_root=ET.parse(live_xml).getroot();live_cases={(c.attrib.get('classname'),c.attrib.get('name')) for c in live_root.iter('testcase')};evidence_cases={(c.attrib.get('classname'),c.attrib.get('name')) for c in cases}
            if live_cases!=evidence_cases or any(list(c.iter('failure')) or list(c.iter('error')) for c in live_root.iter('testcase')):raise RuntimeError('live tests disagree with evidence')
            live_smoke=Path(td)/'smoke.json';subprocess.run([sys.executable,'scripts/run_relational_measurement_v4.py','--config',str(x.config),'--mode','smoke','--output',str(live_smoke)],cwd=ROOT,env=env,check=True,stdout=subprocess.DEVNULL)
            if sha256_file(live_smoke)!=sha256_file(x.smoke_a):raise RuntimeError('live smoke disagrees with evidence')
    probe=x.output.parent/f'.{x.output.name}.probe';fd=os.open(probe,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600);os.write(fd,b'probe');os.fsync(fd);os.close(fd);probe.unlink()
    key=load_private_key(x.owner_key);sign_probe=x.output.parent/f'.{x.output.name}.sign-probe';sign_exclusive(sign_probe,{'probe':True},key);verify_signed(sign_probe,fingerprint(key));sign_probe.unlink();test={'path':artifact_path(x.test_report),'sha256':sha256_file(x.test_report)}
    payload={'schema_version':'relational_measurement_v4_authorization_v1','namespace':cfg['namespace'],'config':{'path':artifact_path(x.config),'sha256':sha256_file(x.config)},'prepared':{'path':artifact_path(x.prepared),'sha256':sha256_file(x.prepared)},'benchmark':prep['benchmark'],'tests':test,'smoke_a':{'path':artifact_path(x.smoke_a),'sha256':sha256_file(x.smoke_a)},'smoke_b':{'path':artifact_path(x.smoke_b),'sha256':sha256_file(x.smoke_b)},'candidate_review':{'path':artifact_path(x.candidate_review),'sha256':sha256_file(x.candidate_review)},'owner_fingerprint':fingerprint(key),'supervisor_fingerprint':fingerprint(x.supervisor_key),'retry_authorized':False}
    sign_exclusive(x.output,payload,key)

def supervise(x:Any)->None:
    supkey=load_private_key(x.key);auth=verify_signed(x.authorization)
    if auth.get('schema_version')!='relational_measurement_v4_authorization_v1' or auth['supervisor_fingerprint']!=fingerprint(supkey) or x.namespace!=auth['namespace'] or x.candidate_sha256!=auth['config']['sha256']:raise RuntimeError('supervisor authorization mismatch')
    sign_exclusive(x.ready,{'schema_version':'relational_measurement_v4_supervisor_ready_v1','namespace':x.namespace,'nonce':x.nonce,'supervisor_pid':os.getpid(),'launcher_pid':x.launcher_pid,'candidate_sha256':x.candidate_sha256,'authorization_sha256':sha256_file(x.authorization)},supkey)
    deadline=time.monotonic()+x.timeout;start=None;start_error=None
    while time.monotonic()<deadline:
        if x.start_signal.exists():
            try:start=verify_signed(x.start_signal,auth['owner_fingerprint']);break
            except Exception as exc:start_error=type(exc).__name__
        time.sleep(.1)
    if start is None or start.get('schema_version')!='relational_measurement_v4_launcher_trigger_v1' or start.get('namespace')!=auth['namespace'] or start.get('nonce')!=x.nonce or start.get('launcher_pid')!=x.launcher_pid or start.get('supervisor_pid')!=os.getpid() or start.get('supervisor_ready_sha256')!=sha256_file(x.ready) or start.get('authorization_sha256')!=sha256_file(x.authorization):
        write_receipt(x,supkey,'PREOPEN_OWNER_FAILURE',{'owner_pid':None,'exit_status':None,'detail_code':'TRIGGER_TIMEOUT','observed_error':start_error});return
    env=os.environ.copy();env.update({'V4_NONCE':x.nonce,'V4_AUTH':str(x.authorization),'V4_READY':str(x.ready),'V4_START':str(x.start_signal),'V4_HANDOFF':str(x.handoff),'V4_OPENING':str(x.opening),'V4_CLOSURE':str(x.closure),'V4_PREPARED':str(x.prepared),'V4_RESULT':str(x.result),'V4_RUNROOT':str(x.run_root),'V4_OWNER_KEY':str(x.owner_key),'V4_CONFIG':str(x.config)})
    child=subprocess.Popen(['bash',str(x.owner_script)],cwd=ROOT,env=env,start_new_session=True);handoff=None;handoff_error=None
    while time.monotonic()<deadline and child.poll() is None:
        if x.handoff.exists():
            try:handoff=verify_signed(x.handoff,auth['owner_fingerprint']);break
            except Exception as exc:handoff_error=type(exc).__name__
        time.sleep(.1)
    if handoff is None and x.handoff.exists():
        try:handoff=verify_signed(x.handoff,auth['owner_fingerprint'])
        except Exception as exc:handoff_error=type(exc).__name__
    if handoff is None:
        status=stop_owner_group(child)
        detail='HANDOFF_INVALID' if x.handoff.exists() else 'HANDOFF_MISSING'
        write_receipt(x,supkey,'PREOPEN_OWNER_FAILURE',{'owner_pid':child.pid,'exit_status':status,'detail_code':detail,'observed_error':handoff_error});return
    if handoff.get('schema_version')!='relational_measurement_v4_owner_handoff_v1' or handoff['owner_pid']!=child.pid or handoff['supervisor_pid']!=os.getpid() or handoff['launcher_pid']!=x.launcher_pid or handoff['nonce']!=x.nonce or handoff['namespace']!=auth['namespace'] or handoff['authorization_sha256']!=sha256_file(x.authorization) or handoff['supervisor_ready_sha256']!=sha256_file(x.ready) or handoff['launcher_trigger_sha256']!=sha256_file(x.start_signal):status=stop_owner_group(child);write_receipt(x,supkey,'PREOPEN_OWNER_FAILURE',{'owner_pid':child.pid,'exit_status':status,'detail_code':'HANDOFF_INVALID','observed_error':'SEMANTIC_INVALID'});return
    opening=None;opening_error=None
    while time.monotonic()<deadline and child.poll() is None:
        if x.opening.exists():
            try:opening=verify_signed(x.opening,auth['owner_fingerprint']);break
            except Exception as exc:opening_error=type(exc).__name__
        time.sleep(.1)
    if opening is None and x.opening.exists():
        try:opening=verify_signed(x.opening,auth['owner_fingerprint'])
        except Exception as exc:opening_error=type(exc).__name__
    if opening is None:
        status=stop_owner_group(child)
        detail='OPENING_INVALID' if x.opening.exists() else 'OPENING_MISSING'
        write_receipt(x,supkey,'PREOPEN_OWNER_FAILURE',{'owner_pid':child.pid,'exit_status':status,'detail_code':detail,'observed_error':opening_error});return
    if opening.get('schema_version')!='relational_measurement_v4_opening_v1' or opening['nonce']!=x.nonce or opening['namespace']!=auth['namespace'] or opening['owner_pid']!=child.pid or opening['supervisor_pid']!=os.getpid() or opening['launcher_pid']!=x.launcher_pid or opening['authorization_sha256']!=sha256_file(x.authorization) or opening['supervisor_ready_sha256']!=sha256_file(x.ready) or opening['launcher_trigger_sha256']!=sha256_file(x.start_signal) or opening['handoff_sha256']!=sha256_file(x.handoff):status=stop_owner_group(child);write_receipt(x,supkey,'PREOPEN_OWNER_FAILURE',{'owner_pid':child.pid,'exit_status':status,'detail_code':'OPENING_INVALID','observed_error':'SEMANTIC_INVALID'});return
    post_deadline=time.monotonic()+x.post_timeout
    while child.poll() is None and time.monotonic()<post_deadline:time.sleep(.1)
    timed_out=child.poll() is None
    status=stop_owner_group(child)
    if x.closure.exists():
        try:
            verify_lifecycle_closure(x)
            return
        except Exception as exc:
            raise RuntimeError('invalid immutable owner closure') from exc
    write_receipt(x,supkey,'OWNER_TERMINALIZATION_FAILURE',{'owner_pid':child.pid,'exit_status':status,'detail_code':'TERMINAL_MISSING','observed_error':None,'postopening_timeout':timed_out})

def terminalize(x:Any)->None:
    auth=verify_signed(x.authorization);opening=verify_signed(x.opening,auth['owner_fingerprint']);x.namespace=auth['namespace']
    if opening.get('schema_version')!='relational_measurement_v4_opening_v1' or opening.get('namespace')!=auth['namespace'] or opening['nonce']!=x.nonce or opening['authorization_sha256']!=sha256_file(x.authorization) or auth['prepared']['sha256']!=sha256_file(x.prepared):raise RuntimeError('terminal input drift')
    payload={'schema_version':'relational_measurement_v4_terminal_v1','namespace':auth['namespace'],'nonce':x.nonce,'authorization_sha256':sha256_file(x.authorization),'opening_sha256':sha256_file(x.opening),'prepared_sha256':sha256_file(x.prepared),'retry_authorized':False,'fresh_corpus_accessed':False,'model_forward_run':False,'training_run':False}
    if x.technical_reason:
        payload.update({'status':'TERMINAL_TECHNICAL_FAILURE','reason':x.technical_reason,'scientific_result':False,'quarantined_partial_artifacts':inventory(x.partial_root+[x.prepared])})
    else:
        if x.result is None:raise RuntimeError('result required')
        result=load_json(x.result);decision,nomination=validate_scientific_result(result,auth,x.nonce,x.prepared)
        payload.update({'status':'TERMINAL_COMPLETE','result':{'path':artifact_path(x.result),'sha256':sha256_file(x.result)},'decision':result['decision'],'nomination':result['nomination'],'scientific_result':True})
    key=load_private_key(x.key) if isinstance(x.key,Path) else x.key
    sign_atomic_closure(x.output,{'schema_version':'relational_measurement_v4_closure_v1','kind':'OWNER_TERMINAL','namespace':auth['namespace'],'nonce':x.nonce,'authorization_sha256':sha256_file(x.authorization),'signer_fingerprint':fingerprint(key),'terminal':payload},key)

def main()->None:
    p=argparse.ArgumentParser();sub=p.add_subparsers(dest='cmd',required=True)
    k=sub.add_parser('keygen');k.add_argument('--path',type=Path,required=True)
    a=sub.add_parser('authorize');
    for n in ('config','prepared','output','owner_key','supervisor_key','test_report','smoke_a','smoke_b','candidate_review'):a.add_argument('--'+n.replace('_','-'),dest=n,type=Path,required=True)
    h=sub.add_parser('handoff');h.add_argument('--authorization',type=Path,required=True);h.add_argument('--ready',type=Path,required=True);h.add_argument('--trigger',type=Path,required=True);h.add_argument('--output',type=Path,required=True);h.add_argument('--key',type=Path,required=True);h.add_argument('--nonce',required=True);h.add_argument('--owner-pid',type=int,required=True)
    g=sub.add_parser('trigger');g.add_argument('--authorization',type=Path,required=True);g.add_argument('--ready',type=Path,required=True);g.add_argument('--output',type=Path,required=True);g.add_argument('--key',type=Path,required=True);g.add_argument('--nonce',required=True);g.add_argument('--launcher-pid',type=int,required=True)
    o=sub.add_parser('opening');
    for n in ('authorization','ready','trigger','handoff','output','key'):o.add_argument('--'+n,type=Path,required=True)
    o.add_argument('--nonce',required=True);o.add_argument('--owner-pid',type=int,required=True)
    t=sub.add_parser('terminal');
    for n in ('authorization','opening','prepared','output','key'):t.add_argument('--'+n,type=Path,required=True)
    t.add_argument('--result',type=Path);t.add_argument('--nonce',required=True);t.add_argument('--technical-reason',choices=sorted(TECH_REASONS));t.add_argument('--partial-root',type=Path,action='append',default=[])
    s=sub.add_parser('supervise')
    for n in ('authorization','ready','start_signal','handoff','opening','closure','run_root','prepared','result','key','owner_key','owner_script','config'):s.add_argument('--'+n.replace('_','-'),dest=n,type=Path,required=True)
    s.add_argument('--nonce',required=True);s.add_argument('--namespace',required=True);s.add_argument('--candidate-sha256',required=True);s.add_argument('--launcher-pid',type=int,required=True);s.add_argument('--timeout',type=int,default=60);s.add_argument('--post-timeout',type=int,default=28800)
    v=sub.add_parser('verify')
    for n in ('authorization','ready','start_signal','handoff','opening','closure','prepared','result','config','run_root'):v.add_argument('--'+n.replace('_','-'),dest=n,type=Path,required=True)
    v.add_argument('--nonce',required=True);v.add_argument('--namespace',required=True)
    x=p.parse_args()
    if x.cmd=='keygen':print(keygen(x.path));return
    if x.cmd=='authorize':authorize(x);return
    if x.cmd=='supervise':supervise(x);return
    if x.cmd=='verify':print(verify_lifecycle_closure(x));return
    if x.cmd=='trigger':
        auth=verify_signed(x.authorization);ready=verify_signed(x.ready,auth['supervisor_fingerprint'])
        if auth.get('schema_version')!='relational_measurement_v4_authorization_v1' or ready.get('schema_version')!='relational_measurement_v4_supervisor_ready_v1' or ready['namespace']!=auth['namespace'] or ready['nonce']!=x.nonce or ready['launcher_pid']!=x.launcher_pid or ready['authorization_sha256']!=sha256_file(x.authorization) or ready['candidate_sha256']!=auth['config']['sha256']:raise RuntimeError('ready trigger binding mismatch')
        sign_exclusive(x.output,{'schema_version':'relational_measurement_v4_launcher_trigger_v1','namespace':auth['namespace'],'nonce':x.nonce,'launcher_pid':x.launcher_pid,'supervisor_pid':ready['supervisor_pid'],'authorization_sha256':sha256_file(x.authorization),'supervisor_ready_sha256':sha256_file(x.ready)},x.key);return
    if x.cmd=='handoff':
        auth=verify_signed(x.authorization);ready=verify_signed(x.ready,auth['supervisor_fingerprint']);trigger=verify_signed(x.trigger,auth['owner_fingerprint'])
        if ready.get('schema_version')!='relational_measurement_v4_supervisor_ready_v1' or trigger.get('schema_version')!='relational_measurement_v4_launcher_trigger_v1' or ready['nonce']!=x.nonce or ready['namespace']!=auth['namespace'] or ready['authorization_sha256']!=sha256_file(x.authorization) or ready['candidate_sha256']!=auth['config']['sha256'] or trigger['nonce']!=x.nonce or trigger['namespace']!=auth['namespace'] or trigger['authorization_sha256']!=sha256_file(x.authorization) or trigger['supervisor_ready_sha256']!=sha256_file(x.ready) or trigger['supervisor_pid']!=ready['supervisor_pid'] or trigger['launcher_pid']!=ready['launcher_pid']:raise RuntimeError('ready/trigger binding mismatch')
        sign_exclusive(x.output,{'schema_version':'relational_measurement_v4_owner_handoff_v1','namespace':auth['namespace'],'nonce':x.nonce,'launcher_pid':ready['launcher_pid'],'supervisor_pid':ready['supervisor_pid'],'owner_pid':x.owner_pid,'authorization_sha256':sha256_file(x.authorization),'supervisor_ready_sha256':sha256_file(x.ready),'launcher_trigger_sha256':sha256_file(x.trigger)},x.key);return
    if x.cmd=='opening':
        auth=verify_signed(x.authorization);ready=verify_signed(x.ready,auth['supervisor_fingerprint']);trigger=verify_signed(x.trigger,auth['owner_fingerprint']);handoff=verify_signed(x.handoff,auth['owner_fingerprint'])
        if ready.get('schema_version')!='relational_measurement_v4_supervisor_ready_v1' or trigger.get('schema_version')!='relational_measurement_v4_launcher_trigger_v1' or handoff.get('schema_version')!='relational_measurement_v4_owner_handoff_v1' or ready['nonce']!=x.nonce or trigger['nonce']!=x.nonce or handoff['nonce']!=x.nonce or handoff['owner_pid']!=x.owner_pid or handoff['authorization_sha256']!=sha256_file(x.authorization) or handoff['supervisor_ready_sha256']!=sha256_file(x.ready) or handoff['launcher_trigger_sha256']!=sha256_file(x.trigger) or handoff['supervisor_pid']!=ready['supervisor_pid'] or handoff['launcher_pid']!=ready['launcher_pid']:raise RuntimeError('preopening binding mismatch')
        sign_exclusive(x.output,{'schema_version':'relational_measurement_v4_opening_v1','namespace':auth['namespace'],'nonce':x.nonce,'launcher_pid':ready['launcher_pid'],'supervisor_pid':ready['supervisor_pid'],'owner_pid':x.owner_pid,'authorization_sha256':sha256_file(x.authorization),'supervisor_ready_sha256':sha256_file(x.ready),'launcher_trigger_sha256':sha256_file(x.trigger),'handoff_sha256':sha256_file(x.handoff)},x.key);return
    terminalize(x)
if __name__=='__main__':main()
