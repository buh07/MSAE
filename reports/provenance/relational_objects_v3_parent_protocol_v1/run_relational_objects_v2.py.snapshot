#!/usr/bin/env python3
"""One-shot opened-development extraction and analysis for relational objects v2."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from importlib.metadata import version as package_version
from pathlib import Path
import secrets
import signal
import subprocess
import sys
import tempfile
import traceback
from typing import Any, Mapping, Sequence

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from analyze_relational_objects_v2 import analyze
from relational_objects_v2 import (CONFIG, NAMESPACE, ROOT, atomic_json, canonical_bytes, exclusive_json,
    load_json, load_jsonl, load_private_key, recursive_inventory, sha256_file, sign_json, study_key, verify_signed)

KEY_DEFAULT=Path('/jumbo/lisp/f004ndc/.generated/sessions/unleashed-3/modes/unleashed/.secrets/attempt13_ed25519.pem')
ACTIVE_OWNER_NONCE: str | None = None
IMPLEMENTATION_PATHS=(
 'PLAN_RELATIONAL_OBJECTS_V2.md','configs/relational_objects_v2/run.json','scripts/conllu_spec.py',
 'scripts/validate_opened_conllu.py','scripts/relational_objects_v2.py','scripts/build_relational_objects_v2.py',
 'scripts/analyze_relational_objects_v2.py','scripts/run_relational_objects_v2.py',
 'scripts/launch_relational_objects_v2_tmux.sh','tests/test_conllu_spec.py','tests/test_relational_objects_v2.py',
 'requirements-atlas.lock.txt','reports/relational_objects_v2_prescore_source_amendment_v1.json',
 'reports/provenance/relational_objects_v2_development2_prescore_rebuild_v2.json',
)


def _inventory() -> list[dict[str,Any]]:
    out=[]
    for value in IMPLEMENTATION_PATHS:
        path=ROOT/value
        if not path.is_file() or path.is_symlink(): raise RuntimeError(f'implementation input absent/symlink: {value}')
        out.append({'path':value,'bytes':path.stat().st_size,'sha256':sha256_file(path)})
    return out


def _inventory_digest(rows: Sequence[Mapping[str,Any]]) -> str:
    return hashlib.sha256(canonical_bytes(list(rows))).hexdigest()


def _nvidia_rows() -> list[dict[str,Any]]:
    raw=subprocess.check_output(['nvidia-smi','--query-gpu=index,uuid,memory.used,memory.free,utilization.gpu,mig.mode.current','--format=csv,noheader,nounits'],text=True)
    out=[]
    for line in raw.splitlines():
        i,u,used,free,util,mig=[x.strip() for x in line.split(',')]
        out.append({'index':int(i),'uuid':u,'memory_used_mib':int(used),'memory_free_mib':int(free),'utilization_percent':int(util),'mig_mode':mig if mig.startswith('[') else f'[{mig}]'})
    return out


def _apps() -> list[tuple[str,int]]:
    raw=subprocess.check_output(['nvidia-smi','--query-compute-apps=gpu_uuid,pid','--format=csv,noheader,nounits'],text=True)
    return [(a.strip(),int(b.strip())) for line in raw.splitlines() if line.strip() and 'No running' not in line for a,b in [line.split(',')]]


def assert_gpu(config: Mapping[str,Any]) -> dict[str,Any]:
    runtime=config['runtime']; rows=[x for x in _nvidia_rows() if x['index']==int(runtime['physical_gpu_index'])]
    if len(rows)!=1: raise RuntimeError('physical GPU missing')
    row=rows[0]
    if row['uuid']!=runtime['gpu_uuid'] or any(uuid==row['uuid'] and pid!=os.getpid() for uuid,pid in _apps()): raise RuntimeError('frozen GPU busy or identity drift')
    if row['memory_used_mib']>runtime['maximum_memory_used_mib'] or row['memory_free_mib']<runtime['minimum_memory_free_mib'] or row['utilization_percent']!=runtime['required_utilization_percent'] or row['mig_mode']!=runtime['mig_mode']:
        raise RuntimeError(f'GPU availability gate failed: {row}')
    return row


def assert_visible(config: Mapping[str,Any]) -> None:
    import torch
    if not torch.cuda.is_available() or torch.cuda.device_count()!=1: raise RuntimeError('exactly one visible CUDA GPU required')
    uuid=str(torch.cuda.get_device_properties(0).uuid); uuid=uuid if uuid.startswith('GPU-') else 'GPU-'+uuid
    if uuid!=config['runtime']['gpu_uuid']: raise RuntimeError(f'visible GPU UUID drift: {uuid}')


def verify_config(config: Mapping[str,Any]) -> None:
    if config.get('namespace')!=NAMESPACE or not config.get('exploratory'): raise RuntimeError('namespace/scope drift')
    if any(value is not False for value in config['permissions'].values()): raise RuntimeError('all training/fresh/retry permissions must be false')
    for spec in [config['identity']['plan'],config['identity']['source_amendment'],config['parser_validation'],{'path':config['parser_validation']['manifest_path'],'sha256':config['parser_validation']['manifest_sha256']},{'path':config['parser_validation']['freeze_path'],'sha256':config['parser_validation']['freeze_sha256']},*config['preservation'].values()]:
        path=ROOT/spec['path']
        if not path.is_file() or sha256_file(path)!=spec['sha256']: raise RuntimeError(f'frozen identity drift: {path}')
    validation=load_json(ROOT/config['parser_validation']['path'])
    if validation.get('eligible_for_development_forward') is not True: raise RuntimeError('parser validation not eligible')
    for source,spec in config['sources'].items():
        for name,digest in spec['files'].items():
            if sha256_file(ROOT/spec['root']/name)!=digest: raise RuntimeError(f'source drift: {source}:{name}')
    env=config['environment']
    if sha256_file(ROOT/env['lock_path'])!=env['lock_sha256']: raise RuntimeError('environment lock drift')
    observed={name:package_version(name) for name in env['versions']}
    if observed!=env['versions']: raise RuntimeError(f'environment version drift: {observed}')


def verify_prepared(config: Mapping[str,Any]) -> dict[str,Any]:
    root=ROOT/config['paths']['prepared_root']; path=root/'manifest.json'; manifest=load_json(path)
    if manifest.get('eligible') is not True or manifest.get('config_sha256')!=sha256_file(CONFIG) or manifest.get('model_forward_run') is not False or manifest.get('neural_training_run') is not False:
        raise RuntimeError('prepared manifest not eligible/frozen')
    for source,record in manifest['sources'].items():
        for name,spec in record['files'].items():
            if sha256_file(root/source/name)!=spec['sha256']: raise RuntimeError(f'prepared drift: {source}/{name}')
    return manifest


def synthetic_smoke(config: Mapping[str,Any]) -> dict[str,Any]:
    import torch
    torch.manual_seed(int(config['seed']))
    heads,width=12,64
    logits=torch.randn(heads,7,dtype=torch.float32)
    probabilities=torch.softmax(logits,dim=-1)
    values=torch.randn(heads,7,width,dtype=torch.float32)
    output_weight=torch.randn(heads*width,heads*width,dtype=torch.float32)/np.sqrt(heads*width)
    effects=_effects(probabilities,values,[1,2],output_weight,float(config['analysis']['head_mass_epsilon']))
    if not effects['eligible']: raise RuntimeError('synthetic intervention unexpectedly ineligible')
    modified=probabilities.clone(); mass=modified[:,[1,2]].sum(-1); modified[:,[1,2]]=0; modified=modified/(1-mass)[:,None]
    if not torch.allclose(modified.sum(-1),torch.ones(heads),atol=1e-6) or not torch.equal(modified[:,[1,2]],torch.zeros_like(modified[:,[1,2]])):
        raise RuntimeError('synthetic probability redistribution failed')
    original=(probabilities[:,:,None]*values).sum(1); changed=(modified[:,:,None]*values).sum(1)
    explicit=torch.nn.functional.linear((changed-original).reshape(1,-1),output_weight,bias=None).square().mean().sqrt().item()
    if not np.isclose(explicit,effects['e_abs'],atol=config['qa']['intervention_atol'],rtol=config['qa']['intervention_rtol']): raise RuntimeError('synthetic E_abs mismatch')
    boundary=probabilities.clone(); boundary[0]=0; boundary[0,1]=float(config['analysis']['head_mass_epsilon']); boundary[0,0]=1-boundary[0,1]
    if _effects(boundary,values,[1],output_weight,float(config['analysis']['head_mass_epsilon']))['eligible']:
        raise RuntimeError('mass boundary was not rejected')
    return {'status':'PASS','probability_conservation':True,'explicit_e_abs':explicit,'analytic_e_abs':effects['e_abs'],'neural_model_loaded':False}


def create_freeze(config: Mapping[str,Any],key_path: Path) -> dict[str,Any]:
    verify_config(config); manifest=verify_prepared(config); gpu=assert_gpu(config); smoke=synthetic_smoke(config)
    for field in ('final_freeze','reviewed_ship','backend_qa','authorization'):
        if (ROOT/config['paths'][field]).exists(): raise RuntimeError(f'{field} already exists')
    for field in ('run_root','result_root','opening'):
        if (ROOT/config['paths'][field]).exists(): raise RuntimeError(f'one-shot destination already exists: {field}')
    inventory=_inventory()
    payload={'schema_version':'relational_objects_v2_freeze_v1','status':'FROZEN_PRE_FORWARD','study_key':study_key(config),'config_sha256':sha256_file(CONFIG),'implementation':inventory,'implementation_sha256':_inventory_digest(inventory),'prepared_manifest_sha256':sha256_file(ROOT/config['paths']['prepared_root']/'manifest.json'),'prepared_sources':{k:v['support'] for k,v in manifest['sources'].items()},'gpu':gpu,'synthetic_smoke':smoke,'model_forward_run':False,'endpoint_scores_computed':False,'neural_training_run':False,'retry_authorized':False}
    sign_json(ROOT/config['paths']['final_freeze'],payload,load_private_key(key_path),exclusive=True); return payload


def verify_freeze(config: Mapping[str,Any]) -> dict[str,Any]:
    path=ROOT/config['paths']['final_freeze']; payload=verify_signed(path,config['signer']['public_key_fingerprint_sha256'])
    if payload.get('status')!='FROZEN_PRE_FORWARD' or payload.get('study_key')!=study_key(config) or payload.get('config_sha256')!=sha256_file(CONFIG): raise RuntimeError('freeze identity drift')
    inventory=_inventory()
    if inventory!=payload['implementation'] or _inventory_digest(inventory)!=payload['implementation_sha256']: raise RuntimeError('implementation drift')
    if payload['prepared_manifest_sha256']!=sha256_file(ROOT/config['paths']['prepared_root']/'manifest.json'): raise RuntimeError('prepared freeze drift')
    verify_config(config); verify_prepared(config); return payload


def create_reviewed(config: Mapping[str,Any],key_path: Path) -> dict[str,Any]:
    freeze=verify_freeze(config); path=ROOT/config['paths']['candidate_review']; text=path.read_text()
    lines=[x.strip() for x in text.splitlines() if x.strip()]
    expected=f"FREEZE_SHA256: {sha256_file(ROOT/config['paths']['final_freeze'])}"
    if not lines or lines[0]!='VERDICT: SHIP' or [x for x in lines if x.startswith('VERDICT:')]!=['VERDICT: SHIP'] or [x for x in lines if x.startswith('FREEZE_SHA256:')]!=[expected]: raise RuntimeError('candidate review is not exact-bound SHIP')
    payload={'schema_version':'relational_objects_v2_review_v1','status':'REVIEWED_SHIP','freeze_sha256':sha256_file(ROOT/config['paths']['final_freeze']),'review_path':config['paths']['candidate_review'],'review_sha256':sha256_file(path),'implementation_sha256':freeze['implementation_sha256'],'model_forward_run':False}
    sign_json(ROOT/config['paths']['reviewed_ship'],payload,load_private_key(key_path),exclusive=True); return payload


def verify_reviewed(config: Mapping[str,Any]) -> dict[str,Any]:
    payload=verify_signed(ROOT/config['paths']['reviewed_ship'],config['signer']['public_key_fingerprint_sha256']); freeze=verify_freeze(config)
    review=ROOT/payload['review_path']
    if payload.get('status')!='REVIEWED_SHIP' or payload['freeze_sha256']!=sha256_file(ROOT/config['paths']['final_freeze']) or payload['review_sha256']!=sha256_file(review) or payload['implementation_sha256']!=freeze['implementation_sha256']: raise RuntimeError('review marker drift')
    return payload


def create_backend_qa(config: Mapping[str,Any],key_path: Path) -> dict[str,Any]:
    """Synthetic-token, model-loaded QA; never reads an opened corpus row."""
    import torch
    verify_reviewed(config); assert_gpu(config)
    path=ROOT/config['paths']['backend_qa']
    if path.exists(): raise RuntimeError('backend QA already exists')
    model=_load_model(config); block=int(config['model']['block_index']); layer=model.gpt_neox.layers[block]; attention=layer.attention
    ids=torch.tensor([[10,11,12,13,14,15]],device='cuda:0',dtype=torch.long)
    outputs,block_input,qkv_input,query,key,value,logits,probabilities=_capture(model,ids,config)
    with torch.inference_mode():
        expected_input=layer.input_layernorm(block_input)
        qkv=attention.query_key_value(expected_input)
    input_abs=float((qkv_input-expected_input).abs().max().item())
    qkv_abs=float((qkv-attention.query_key_value(qkv_input)).abs().max().item())
    shaped=qkv.reshape(1,ids.shape[1],12,3*64).permute(0,2,1,3); raw_q,raw_k,_=shaped.chunk(3,dim=-1)
    position=torch.arange(ids.shape[1],device='cuda:0')[None,:]; cos,sin=model.gpt_neox.rotary_emb(expected_input,position); cos,sin=cos[:,None],sin[:,None]; rotary=cos.shape[-1]
    def rotate_half(x: Any):
        left,right=x.chunk(2,dim=-1); return torch.cat([-right,left],dim=-1)
    independent_q=torch.cat([raw_q[...,:rotary]*cos+rotate_half(raw_q[...,:rotary])*sin,raw_q[...,rotary:]],-1)
    independent_k=torch.cat([raw_k[...,:rotary]*cos+rotate_half(raw_k[...,:rotary])*sin,raw_k[...,rotary:]],-1)
    independent_logits=independent_q@independent_k.transpose(2,3)*float(attention.scaling)
    query_abs=float((query-independent_q).abs().max().item()); key_abs=float((key-independent_k).abs().max().item()); logit_abs=float((logits-independent_logits).abs().max().item())
    pooled=_pool_objects(logits[0],probabilities[0],value[0],block_input[0],4,[1,2],[0,1],[3,4])
    checks={'qkv_input':input_abs<=config['qa']['qk_atol'],'qkv_replay':qkv_abs==0.0,'query_rotary':query_abs<=config['qa']['qk_atol'],'key_rotary':key_abs<=config['qa']['qk_atol'],'qk_logits':logit_abs<=config['qa']['qk_atol'],'hidden_state_index':block_input.data_ptr()==outputs.hidden_states[int(config['model']['block_input_hidden_state_index'])].data_ptr(),'object_shapes':{key:tuple(value.shape) for key,value in pooled.items()}=={'residual_concat':(1536,),'residual_difference':(768,),'qk':(12,),'mass':(12,),'transport':(768,),'head_output':(768,),'query_value_norm':(12,),'key_value_norm':(12,)}}
    if not all(checks.values()): raise RuntimeError(f'backend QA failed: {checks}')
    payload={'schema_version':'relational_objects_v2_backend_qa_v1','status':'PASS','study_key':study_key(config),'freeze_sha256':sha256_file(ROOT/config['paths']['final_freeze']),'review_sha256':sha256_file(ROOT/config['paths']['candidate_review']),'synthetic_token_ids_only':True,'opened_source_rows_read':0,'metrics':{'qkv_input_max_abs':input_abs,'qkv_replay_max_abs':qkv_abs,'query_rotary_max_abs':query_abs,'key_rotary_max_abs':key_abs,'qk_logit_max_abs':logit_abs},'checks':checks,'model_forward_run':True,'opened_source_model_forward_run':False,'neural_training_run':False,'retry_authorized':False}
    sign_json(path,payload,load_private_key(key_path),exclusive=True); del model; torch.cuda.empty_cache(); return payload


def verify_backend_qa(config: Mapping[str,Any]) -> dict[str,Any]:
    payload=verify_signed(ROOT/config['paths']['backend_qa'],config['signer']['public_key_fingerprint_sha256'])
    if payload.get('status')!='PASS' or payload.get('study_key')!=study_key(config) or payload.get('freeze_sha256')!=sha256_file(ROOT/config['paths']['final_freeze']) or payload.get('opened_source_rows_read')!=0:
        raise RuntimeError('backend QA identity drift')
    verify_reviewed(config); return payload


def create_authorization(config: Mapping[str,Any],key_path: Path) -> dict[str,Any]:
    reviewed=verify_reviewed(config); backend=verify_backend_qa(config); gpu=assert_gpu(config); smoke=synthetic_smoke(config)
    if (ROOT/config['paths']['authorization']).exists(): raise RuntimeError('authorization exists')
    payload={'schema_version':'relational_objects_v2_authorization_v1','status':'AUTHORIZED_ONE_SHOT_OPENED_DEVELOPMENT','study_key':study_key(config),'freeze_sha256':reviewed['freeze_sha256'],'review_sha256':reviewed['review_sha256'],'backend_qa_sha256':sha256_file(ROOT/config['paths']['backend_qa']),'gpu':gpu,'synthetic_smoke':smoke,'neural_training_authorized':False,'fresh_source_authorized':False,'retry_authorized':False}
    sign_json(ROOT/config['paths']['authorization'],payload,load_private_key(key_path),exclusive=True); return payload


def verify_authorization(config: Mapping[str,Any]) -> dict[str,Any]:
    payload=verify_signed(ROOT/config['paths']['authorization'],config['signer']['public_key_fingerprint_sha256']); review=verify_reviewed(config)
    if payload.get('status')!='AUTHORIZED_ONE_SHOT_OPENED_DEVELOPMENT' or payload.get('study_key')!=study_key(config) or payload['freeze_sha256']!=review['freeze_sha256'] or payload['review_sha256']!=review['review_sha256'] or payload['backend_qa_sha256']!=sha256_file(ROOT/config['paths']['backend_qa']): raise RuntimeError('authorization drift')
    verify_backend_qa(config)
    return payload


def _load_model(config: Mapping[str,Any]):
    import torch
    from transformers import AutoModelForCausalLM
    assert_visible(config)
    model=AutoModelForCausalLM.from_pretrained(config['model']['name'],revision=config['model']['revision'],local_files_only=True,torch_dtype=torch.float32,attn_implementation='eager').to('cuda:0').eval()
    if model.config._attn_implementation!='eager': raise RuntimeError('eager attention not honored')
    attention=model.gpt_neox.layers[int(config['model']['block_index'])].attention
    if model.config.num_attention_heads!=config['model']['num_heads'] or attention.head_size!=config['model']['head_size']: raise RuntimeError('attention geometry drift')
    return model


def _capture(model: Any,input_ids: Any,config: Mapping[str,Any]):
    import torch
    from transformers.models.gpt_neox.modeling_gpt_neox import apply_rotary_pos_emb
    block=int(config['model']['block_index']); attention=model.gpt_neox.layers[block].attention; captured={}
    def hook(_module:Any,inputs:tuple[Any,...],output:Any)->None: captured.update(hidden=inputs[0],qkv=output)
    handle=attention.query_key_value.register_forward_hook(hook)
    try:
        with torch.inference_mode(): outputs=model(input_ids=input_ids,attention_mask=torch.ones_like(input_ids),use_cache=False,output_attentions=True,output_hidden_states=True,return_dict=True)
    finally: handle.remove()
    qkv=captured['qkv'].view(1,input_ids.shape[1],-1,3*attention.head_size).transpose(1,2)
    query,key,value=qkv.chunk(3,dim=-1); position=torch.arange(input_ids.shape[1],device=input_ids.device)[None,:]
    cos,sin=model.gpt_neox.rotary_emb(captured['hidden'],position); query,key=apply_rotary_pos_emb(query,key,cos,sin)
    logits=query@key.transpose(2,3)*attention.scaling
    qlen=input_ids.shape[1]; mask=torch.arange(qlen,device=input_ids.device)[None,:]<=torch.arange(qlen,device=input_ids.device)[:,None]
    manual=torch.softmax(logits.masked_fill(~mask[None,None],torch.finfo(logits.dtype).min),dim=-1,dtype=torch.float32)
    returned=outputs.attentions[block]
    if not torch.allclose(manual,returned,atol=config['qa']['attention_probability_atol'],rtol=config['qa']['attention_probability_rtol']):
        raise RuntimeError(f'attention probability QA failed max_abs={(manual-returned).abs().max().item()}')
    block_input=outputs.hidden_states[int(config['model']['block_input_hidden_state_index'])]
    return outputs,block_input,captured['hidden'],query,key,value,logits,returned


def _effects(probabilities: Any,values: Any,key_positions: Sequence[int],output_weight: Any,eps: float)->dict[str,Any]:
    import torch
    keys=list(map(int,key_positions))
    if keys!=sorted(set(keys)) or not keys or keys[-1]>=probabilities.shape[1]:
        raise ValueError('intervention keys must be unique and increasing')
    mass=probabilities[:,keys].sum(-1)
    eligible=bool(torch.all((mass>eps)&(mass<1-eps)).item())
    if not eligible: return {'eligible':False,'e_local':np.nan,'e_abs':np.nan,'e_abs64':np.nan}
    # The live intervention path stays float32; the authoritative normalized
    # effect is independently reduced from cached float32 inputs in float64.
    # Literal float32 intervention: zero the selected link, renormalize the
    # remaining causal row, recompute the head outputs, then apply W_o.
    modified=probabilities.clone(); modified[:,keys]=0.0; modified=modified/(1-mass)[:,None]
    original=(probabilities[:,:,None]*values).sum(1)
    changed=(modified[:,:,None]*values).sum(1)
    projected=torch.nn.functional.linear((changed-original).reshape(1,-1),output_weight,bias=None)
    eabs=float(projected.square().mean().sqrt().item())
    probabilities64,values64=probabilities.double(),values.double()
    mass64=torch.zeros(probabilities.shape[0],dtype=torch.float64,device=probabilities.device)
    inside64=torch.zeros_like(values64[:,0]); total64=torch.zeros_like(values64[:,0])
    for key in range(probabilities.shape[1]):
        contribution=probabilities64[:,key,None]*values64[:,key]
        total64=total64+contribution
        if key in keys:
            mass64=mass64+probabilities64[:,key]
            inside64=inside64+contribution
    delta64=(total64-inside64)/(1-mass64)[:,None]-inside64/mass64[:,None]
    elocal64=float(delta64.square().mean().sqrt().item())
    projected64=torch.nn.functional.linear((mass64[:,None]*delta64).reshape(1,-1),output_weight.double(),bias=None)
    eabs64=float(projected64.square().mean().sqrt().item())
    return {'eligible':True,'e_local':elocal64,'e_abs':eabs,'e_abs64':eabs64}


def _pool_objects(logits: Any, probabilities: Any, values: Any, residual: Any, query: int,
                  keys: Sequence[int], child: Sequence[int], head: Sequence[int]) -> dict[str, Any]:
    """Pool the six frozen relational objects from validated single-sentence tensors."""
    import torch
    key_list=list(map(int,keys)); child_list=list(map(int,child)); head_list=list(map(int,head))
    if not key_list or max(key_list)>query or not child_list or not head_list:
        raise ValueError('invalid relational-object pooling indices')
    child_r=residual[child_list].mean(0); head_r=residual[head_list].mean(0)
    mass=probabilities[:,query,key_list].sum(-1)
    transport=(probabilities[:,query,key_list,None]*values[:,key_list]).sum(1)
    all_output=(probabilities[:,query,:,None]*values).sum(1)
    return {
        'residual_concat':torch.cat([child_r,head_r]), 'residual_difference':head_r-child_r,
        'qk':logits[:,query,key_list].mean(-1), 'mass':mass,
        'transport':transport.reshape(-1), 'head_output':all_output.reshape(-1),
        'query_value_norm':values[:,query].square().mean(-1).sqrt(),
        'key_value_norm':values[:,key_list].square().mean(-1).sqrt().mean(-1),
    }


def _atomic_npz(path: Path,arrays: Mapping[str,np.ndarray])->str:
    path.parent.mkdir(parents=True,exist_ok=True)
    with tempfile.NamedTemporaryFile(dir=path.parent,prefix='.'+path.name+'.',suffix='.npz',delete=False) as h:
        temporary=Path(h.name)
        np.savez(h,**arrays); h.flush(); os.fsync(h.fileno())
    os.replace(temporary,path); return sha256_file(path)


def extract_source(model: Any,name: str,config: Mapping[str,Any],cache_root: Path)->dict[str,Any]:
    import torch
    prepared=ROOT/config['paths']['prepared_root']/name; examples=load_jsonl(prepared/'examples.jsonl'); units=load_jsonl(prepared/'inference_units.jsonl'); n=len(examples)
    arrays={
      'residual_concat':np.empty((n,1536),np.float32),'residual_difference':np.empty((n,768),np.float32),'qk':np.empty((n,12),np.float32),'mass':np.empty((n,12),np.float32),'transport':np.empty((n,768),np.float32),'head_output':np.empty((n,768),np.float32),'query_value_norm':np.empty((n,12),np.float32),'key_value_norm':np.empty((n,12),np.float32),'attention_output_norm':np.empty(n,np.float32),'block_input_rms':np.empty(n,np.float32),'e_local':np.empty(n,np.float64),'e_abs':np.empty(n,np.float32),'e_abs64':np.empty(n,np.float64),'functional_eligible':np.empty(n,np.uint8),'example_index':np.arange(n,dtype=np.int64),'label':np.asarray([r['label'] for r in examples],np.int64),'fold':np.asarray([r['fold'] for r in examples],np.int64),'example_id_sha256':np.asarray([hashlib.sha256(r['example_id'].encode()).digest() for r in examples],dtype='|S32')}
    seen=set(); block=int(config['model']['block_index']); attention=model.gpt_neox.layers[block].attention; weight=attention.dense.weight
    for unit_number,unit in enumerate(units,1):
        ids=torch.tensor([unit['input_ids']],device='cuda:0',dtype=torch.long)
        outputs,block_input,_qkv_input,_query,_key,value,logits,probabilities=_capture(model,ids,config)
        for index in unit['example_indices']:
            if index in seen: raise RuntimeError('duplicate unit/example lineage')
            seen.add(index); row=examples[index]; q=int(row['query_index']); keys=list(map(int,row['key_positions'])); child=list(map(int,row['child_positions'])); head=list(map(int,row['head_positions']))
            residual=block_input[0]
            pooled=_pool_objects(logits[0],probabilities[0],value[0],residual,q,keys,child,head)
            for field in ('residual_concat','residual_difference','qk','mass','transport','head_output','query_value_norm','key_value_norm'):
                arrays[field][index]=pooled[field].detach().cpu().numpy()
            mass=pooled['mass']; all_output=pooled['head_output'].reshape(12,64)
            projected=torch.nn.functional.linear(all_output.reshape(1,-1),weight,bias=attention.dense.bias); arrays['attention_output_norm'][index]=projected.square().mean().sqrt().item(); arrays['block_input_rms'][index]=block_input[0,q].square().mean().sqrt().item()
            effects=_effects(probabilities[0,:,q,:q+1],value[0,:,:q+1],keys,weight,float(config['analysis']['head_mass_epsilon']))
            arrays['functional_eligible'][index]=int(effects['eligible']); arrays['e_local'][index]=effects['e_local']; arrays['e_abs'][index]=effects['e_abs']; arrays['e_abs64'][index]=effects['e_abs64']
        if unit_number%100==0: print(f'EXTRACT_PROGRESS source={name} units={unit_number}/{len(units)}',flush=True)
    if seen!=set(range(n)): raise RuntimeError('unit/example coverage not bijective')
    eligible_mask=arrays['functional_eligible'].astype(bool)
    for key,value in arrays.items():
        if key in {'functional_eligible','e_local','e_abs','e_abs64'}:
            continue
        if not np.isfinite(value).all(): raise RuntimeError(f'nonfinite extracted tensor {name}:{key}')
    for key in ('e_local','e_abs','e_abs64'):
        if not np.isfinite(arrays[key][eligible_mask]).all() or not np.isnan(arrays[key][~eligible_mask]).all():
            raise RuntimeError(f'functional missingness contract failure {name}:{key}')
    path=cache_root/f'{name}.features.npz'; digest=_atomic_npz(path,arrays)
    precision=np.abs(arrays['e_abs'][eligible_mask].astype(np.float64)-arrays['e_abs64'][eligible_mask])
    return {'source':name,'examples':n,'units':len(units),'cache_path':path.relative_to(ROOT).as_posix(),'cache_sha256':digest,'functional_eligible':int(arrays['functional_eligible'].sum()),'max_e_abs_precision_difference':float(np.max(precision)) if precision.size else None}


def run(config: Mapping[str,Any],key_path: Path)->dict[str,Any]:
    global ACTIVE_OWNER_NONCE
    verify_authorization(config); assert_gpu(config); verify_prepared(config)
    run_root=ROOT/config['paths']['run_root']; result_root=ROOT/config['paths']['result_root']; opening=ROOT/config['paths']['opening']
    if run_root.exists() or result_root.exists() or opening.exists(): raise RuntimeError('one-shot namespace already consumed')
    print('RUNNER_READY',flush=True)
    key=load_private_key(key_path); owner=secrets.token_hex(16)
    opening_payload={'schema_version':'relational_objects_v2_opening_v1','status':'DEVELOPMENT_OPENED','study_key':study_key(config),'owner_nonce':owner,'sources':{name:'PERMANENTLY_OPENED_DEVELOPMENT_ONLY' for name in config['sources']},'freeze_sha256':sha256_file(ROOT/config['paths']['final_freeze']),'authorization_sha256':sha256_file(ROOT/config['paths']['authorization']),'fresh_scientific_source_accessed':False,'model_forward_run':False,'neural_training_run':False,'retry_authorized':False}
    sign_json(opening,opening_payload,key,exclusive=True); ACTIVE_OWNER_NONCE=owner
    run_root.mkdir(parents=True,exist_ok=False); cache_root=run_root/'cache'; cache_root.mkdir()
    model=_load_model(config); extraction=[extract_source(model,name,config,cache_root) for name in sorted(config['sources'])]; del model
    import torch; torch.cuda.empty_cache()
    result=analyze(config,cache_root); result.update({'study_key':study_key(config),'config_sha256':sha256_file(CONFIG),'opening_sha256':sha256_file(opening),'extraction':extraction})
    result_root.mkdir(parents=True,exist_ok=False); result_sha=atomic_json(result_root/'result.json',result)
    manifest={'schema_version':'relational_objects_v2_result_manifest_v1','result_sha256':result_sha,'result_inventory':recursive_inventory(result_root),'cache_inventory':recursive_inventory(cache_root),'neural_training_run':False}
    atomic_json(result_root/'manifest.json',manifest)
    terminal={'schema_version':'relational_objects_v2_terminal_v1','status':'TERMINAL_COMPLETE','study_key':study_key(config),'owner_nonce':owner,'opening_sha256':sha256_file(opening),'result_sha256':result_sha,'decision':result['decision'],'nominated_paths':result['nominated_paths'],'neural_training_run':False,'representation_training_run':False,'fresh_scientific_source_accessed':False,'retry_authorized':False,'learned_model_authorized':False}
    sign_json(run_root/'TERMINAL.json',terminal,key,exclusive=True); return terminal


def failure(config: Mapping[str,Any],key_path: Path,exc: BaseException)->None:
    try:
        run_root=ROOT/config['paths']['run_root']; opening_path=ROOT/config['paths']['opening']
        # Preopening validation is repairable and must not consume the namespace.
        # A process that lost O_EXCL ownership likewise cannot mutate the winner.
        if not opening_path.exists() or ACTIVE_OWNER_NONCE is None:
            return
        opening=verify_signed(opening_path,config['signer']['public_key_fingerprint_sha256'])
        if opening.get('owner_nonce')!=ACTIVE_OWNER_NONCE:
            return
        run_root.mkdir(parents=True,exist_ok=True); path=run_root/'TERMINAL.json'
        if not path.exists(): sign_json(path,{'schema_version':'relational_objects_v2_terminal_v1','status':'TERMINAL_FAILED_POSTOPENING' if opening_path.exists() else 'TERMINAL_FAILED_PREOPENING','owner_nonce':ACTIVE_OWNER_NONCE,'error_type':type(exc).__name__,'error':str(exc),'traceback':traceback.format_exc(),'neural_training_run':False,'retry_authorized':False},load_private_key(key_path),exclusive=True)
    except Exception as nested:
        print(f'FAILED_TO_WRITE_TERMINAL {nested}',file=sys.stderr)


def main()->None:
    parser=argparse.ArgumentParser(); parser.add_argument('command',choices=('smoke','freeze','reviewed','backend-qa','authorize','run')); parser.add_argument('--signing-key',type=Path,default=KEY_DEFAULT); args=parser.parse_args(); config=load_json(CONFIG)
    functions={'smoke':lambda c,k:synthetic_smoke(c),'freeze':create_freeze,'reviewed':create_reviewed,'backend-qa':create_backend_qa,'authorize':create_authorization,'run':run}
    if args.command=='run':
        signal.signal(signal.SIGTERM,lambda s,f: (_ for _ in ()).throw(RuntimeError(f'terminated by signal {s}'))); signal.signal(signal.SIGINT,lambda s,f: (_ for _ in ()).throw(RuntimeError(f'interrupted by signal {s}')))
    try: output=functions[args.command](config,args.signing_key)
    except BaseException as exc:
        if args.command=='run': failure(config,args.signing_key,exc)
        raise
    print(json.dumps(output,sort_keys=True,indent=2),flush=True)

if __name__=='__main__': main()
