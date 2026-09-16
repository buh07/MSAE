#!/usr/bin/env python3
"""Execute the frozen, calibration-only numerical replay and build Stage B."""
from __future__ import annotations
import argparse, hashlib, json, os, platform, sys, traceback
from pathlib import Path
from typing import Any
import numpy as np
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts'))
from msae_measurement_remediation_v1 import build_stage_b,payload_sha256,select_replay_tolerance

def cbytes(x):return (json.dumps(x,sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False)+'\n').encode()
def sha_file(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def create(p,x):
 p=Path(p);p.parent.mkdir(parents=True,exist_ok=True)
 fd=os.open(p,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o644)
 with os.fdopen(fd,'wb') as f:f.write(cbytes(x));f.flush();os.fsync(f.fileno())
def forward(model,units,device):
 import torch
 vals=[];rows=[]
 for start in range(0,len(units),8):
  batch=units[start:start+8];m=max(len(x['input_ids']) for x in batch)
  ids=torch.zeros((len(batch),m),dtype=torch.long,device=device);att=torch.zeros_like(ids)
  for i,u in enumerate(batch):
   n=len(u['input_ids']);ids[i,:n]=torch.tensor(u['input_ids'],device=device);att[i,:n]=1
  with torch.inference_mode(): h=model(ids,attention_mask=att,output_hidden_states=True,use_cache=False).hidden_states[3]
  for i,u in enumerate(batch):
   vals.append(h[i,torch.tensor(u['positions'],device=device)].float().cpu().numpy());rows.extend(u['row_ids'])
 return np.ascontiguousarray(np.concatenate(vals,axis=0),dtype=np.float32),rows
def obs(meta,eid,v,rows):
 return {**{k:meta[k] for k in ('stratum_id','source_role','source_revision','partition','model_id','checkpoint_id','code_sha256','environment_sha256','dtype','pooling_path','row_ids_sha256','input_sha256')},'evaluation_id':eid,'row_ids':rows,'values':v,'payload_sha256':payload_sha256(v,rows)}
def evidence(cfgsha,name,status,value,digest=None,reasons=None):
 return {'schema_version':'msae_endpoint_evidence_v1','protocol_config_sha256':cfgsha,'endpoint_name':name,'category':'stage_b','status':status,'reasons':list(reasons or []),'evidence_artifact_sha256':digest,'observed_value':value}
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--run-root',required=True);ap.add_argument('--gpu-uuid',required=True);a=ap.parse_args();run=ROOT/a.run_root
 cfgp=ROOT/'configs/msae_independent_measurement_v1/protocol.json';raw=cfgp.read_bytes();cfgsha=hashlib.sha256(raw).hexdigest();cfg=json.loads(raw)
 stagea=json.loads((ROOT/'reports/provenance/msae_independent_measurement_v1/stage_a.json').read_text())
 auth=json.loads((ROOT/'reports/provenance/msae_independent_measurement_v1/prescore_authorization.json').read_text())
 if auth['verdict']!='SHIP' or auth['protocol_config_sha256']!=cfgsha:raise RuntimeError('prescore authorization mismatch')
 if stagea.get('stage_ready') is not True:raise RuntimeError('Stage A is not ready; model load forbidden')
 if os.environ.get('CUDA_VISIBLE_DEVICES')!=a.gpu_uuid:raise RuntimeError('CUDA UUID binding mismatch')
 import torch
 torch.use_deterministic_algorithms(True);torch.backends.cuda.matmul.allow_tf32=False;torch.backends.cudnn.allow_tf32=False;torch.set_float32_matmul_precision('highest')
 if torch.cuda.device_count()!=1:raise RuntimeError('expected exactly one visible GPU')
 prop=torch.cuda.get_device_properties(0);actual=getattr(prop,'uuid',None)
 if actual is None or str(actual).lower().replace('gpu-','')!=a.gpu_uuid.lower().replace('gpu-',''):raise RuntimeError(f'runtime UUID mismatch: {actual}')
 from transformers import AutoModelForCausalLM
 model=AutoModelForCausalLM.from_pretrained('EleutherAI/pythia-160m-deduped',revision='582159a2dfe3e712a8d47ae83dec95ae3bde8e7e',torch_dtype=torch.float16,local_files_only=True).to('cuda').eval()
 frozen=json.loads((ROOT/'data/msae_independent_measurement_v1/calibration_strata.json').read_text())
 if sha_file(__file__)!=cfg['replay']['strata'][0]['code_sha256']:raise RuntimeError('runner code digest drift')
 for s in cfg['replay']['strata']:
  inp=[{'unit_id':u['unit_id'],'input_ids':u['input_ids'],'positions':u['positions'],'row_ids':u['row_ids']} for u in frozen['strata'][s['stratum_id']]['units']]
  if hashlib.sha256(cbytes(inp)).hexdigest()!=s['input_sha256']:raise RuntimeError('frozen stratum input drift')
 observations={};references={};unit_results={}
 for s in cfg['replay']['strata']:
  sid=s['stratum_id'];units=frozen['strata'][sid]['units'];observations[sid]={}
  for eid in [s['reference_evaluation_id'],*s['repeat_evaluation_ids']]:
   v,rows=forward(model,units,'cuda');observations[sid][eid]=obs(s,eid,v,rows)
   if eid==s['reference_evaluation_id']:references[sid]=(v,rows)
  # Batch/unit QA is an independent forward path.
  pieces=[];urows=[]
  for u in units:
   vv,rr=forward(model,[u],'cuda');pieces.append(vv);urows.extend(rr)
  unit_results[sid]=np.concatenate(pieces,axis=0)
 bundle={'schema_version':'msae_calibration_replay_bundle_v1','protocol_config_sha256':cfgsha,'replay_registry_sha256':hashlib.sha256(cbytes(cfg['replay']['strata'])).hexdigest(),'source_role':'calibration','source_revision':cfg['replay']['source_revision'],'partition':cfg['replay']['partition'],'observations':observations}
 # Save JSON-safe replay evidence without arrays plus NPY payloads.
 for sid,(v,rows) in references.items():np.save(run/f'{sid}.reference.npy',v,allow_pickle=False)
 noop_ok=all(np.array_equal(v,np.load(run/f'{sid}.reference.npy',allow_pickle=False)) for sid,(v,_) in references.items())
 pool_max=max(float(np.max(np.abs(references[s][0].astype(np.float64)-unit_results[s].astype(np.float64)))) for s in references)
 align_ok=True
 for sid in ('pair_context','pair_entity'):
  us=frozen['strata'][sid]['units']
  align_ok &= len(us)==16 and all(us[i]['unit_id'].endswith(':source') and us[i+1]['unit_id'].endswith(':target') and us[i]['unit_id'][:-7]==us[i+1]['unit_id'][:-7] and len(us[i]['row_ids'])==len(us[i+1]['row_ids']) for i in range(0,16,2))
 selection=select_replay_tolerance(raw,cfgsha,bundle);tol=selection['selected_tolerance'];pool_ok=tol is not None and all(np.allclose(references[s][0],unit_results[s],atol=tol['atol'],rtol=tol['rtol']) for s in references)
 evraw={'noop_ok':noop_ok,'pool_max_abs':pool_max,'pool_ok':pool_ok,'alignment_ok':align_ok};evdig=hashlib.sha256(cbytes(evraw)).hexdigest()
 ev={
  'cached_noop_hash_replay':evidence(cfgsha,'cached_noop_hash_replay','eligible' if noop_ok else 'ineligible',{'byte_exact':noop_ok},evdig,[] if noop_ok else ['npy_roundtrip_mismatch']),
  'canonical_pooling_qa':evidence(cfgsha,'canonical_pooling_qa','eligible' if pool_ok else 'ineligible',{'max_abs':pool_max,'selected_tolerance':tol},evdig,[] if pool_ok else ['batch_unit_replay_failed_selected_bound']),
  'counterfactual_cache_alignment_qa':evidence(cfgsha,'counterfactual_cache_alignment_qa','eligible' if align_ok else 'ineligible',{'alignment_valid':align_ok},evdig,[] if align_ok else ['pair_alignment_failure'])}
 stageb=build_stage_b(raw,cfgsha,stagea,bundle,ev)
 create(run/'stage_b.json',stageb);create(run/'terminal.json',{'schema_version':'msae_independent_calibration_terminal_v1','status':'eligible' if stageb['stage_ready'] else 'ineligible','stage_b_sha256':hashlib.sha256(cbytes(stageb)).hexdigest(),'selected':stageb['endpoints']['selected_replay_tolerance']['observed_value']})
if __name__=='__main__':
 try:main()
 except Exception as e:
  try:create(Path(os.environ.get('MSAE_RUN_ROOT','/tmp'))/'technical_failure.json',{'schema_version':'msae_independent_calibration_failure_v1','status':'not_run','error':str(e),'traceback':traceback.format_exc()})
  except Exception:pass
  raise
