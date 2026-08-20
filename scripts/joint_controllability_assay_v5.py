#!/usr/bin/env python3
"""Prospective counterbalanced behavioral task-validity assay v5.

No representation-method evaluation or training path exists.
"""
from __future__ import annotations
import argparse, hashlib, json, os, re, time, traceback
from collections import Counter
from pathlib import Path
from typing import Any, Mapping, Sequence
import numpy as np
import torch
import joint_controllability_benchmark_v3 as core
import joint_controllability_benchmark_v4_1 as v41
ROOT=Path(__file__).resolve().parents[1]; SCRIPT=Path(__file__).resolve()
DEFAULT=ROOT/'configs/joint_controllability_assay_v5/run.json'
PLAN=ROOT/'PLAN_JOINT_CONTROLLABILITY_V5.md'
TEST=ROOT/'tests/test_joint_controllability_assay_v5.py'
LAUNCHER=ROOT/'scripts/launch_joint_controllability_assay_v5_tmux.sh'
def loadj(p:Path)->Any:return json.loads(p.read_text())
def sha(p:Path)->str:
 h=hashlib.sha256()
 with p.open('rb') as f:
  for chunk in iter(lambda:f.read(8*1024*1024),b''):h.update(chunk)
 return h.hexdigest()
def canon(x:Any)->bytes:return json.dumps(native(x),sort_keys=True,separators=(',',':'),allow_nan=False).encode()
def native(x:Any)->Any:
 if isinstance(x,np.generic):return x.item()
 if isinstance(x,dict):return {str(k):native(v) for k,v in x.items()}
 if isinstance(x,(list,tuple)):return [native(v) for v in x]
 return x
def exjson(p:Path,x:Any)->None:
 p.parent.mkdir(parents=True,exist_ok=True); data=canon(x)+b'\n'; tmp=p.with_name(p.name+f'.tmp.{os.getpid()}.{time.time_ns()}')
 fd=os.open(tmp,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
 try:
  with os.fdopen(fd,'wb') as f:f.write(data);f.flush();os.fsync(f.fileno())
  os.link(tmp,p)
 finally:tmp.unlink(missing_ok=True)
def publish_failure(p:Path,x:Any)->None:
 try:exjson(p,x)
 except FileExistsError:pass
def writejl(p:Path,rows:Sequence[Mapping[str,Any]])->None:
 p.parent.mkdir(parents=True,exist_ok=True);fd=os.open(p,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
 with os.fdopen(fd,'w') as f:
  for r in rows:f.write(canon(dict(r)).decode()+'\n')
def readjl(p:Path)->list[dict[str,Any]]:return [json.loads(x) for x in p.read_text().splitlines() if x]
def norm(text:str)->str:return ' '.join(re.findall(r'\S+',text)).strip().lower()
def text_hash(text:str)->str:return hashlib.sha256(norm(text).encode()).hexdigest()
def stable(seed:int,*parts:Any)->int:return core.stable(seed,*parts)

def preservation_verify(cfg:Mapping[str,Any])->None:
 manifest=loadj(ROOT/cfg['preservation']['v4_1_tree'])
 for r in manifest['files']:
  p=ROOT/r['path']
  if not p.is_file() or p.stat().st_size!=r['bytes'] or sha(p)!=r['sha256']:raise RuntimeError(f"v4.1 preservation drift: {r['path']}")
 if sha(ROOT/cfg['preservation']['closure'])!=cfg['preservation']['closure_sha256']:raise RuntimeError('closure drift')

def predecessor_exclusions(cfg:Mapping[str,Any])->tuple[set[str],set[str]]:
 ids:set[str]=set(); windows:set[str]=set()
 for rel in cfg['task']['predecessor_rows']:
  for r in readjl(ROOT/rel):
   for k,v in r.items():
    if (k.endswith('_id') or k in {'document_id','component_block'}) and isinstance(v,str):ids.add(v)
   if isinstance(r.get('filler'),str):windows.add(text_hash(r['filler']))
 return ids,windows

def require_offline()->None:
 for name in ('HF_DATASETS_OFFLINE','HF_HUB_OFFLINE','TRANSFORMERS_OFFLINE'):
  if os.environ.get(name)!='1':raise RuntimeError(f'offline environment required: {name}=1')

def wiki_docs(cfg:Mapping[str,Any])->list[dict[str,Any]]:
 require_offline();from datasets import load_dataset
 s=cfg['task']['wikitext'];ds=load_dataset(s['dataset'],s['config'],split=s['split'],revision=s['revision'])
 if ds._fingerprint!=s['fingerprint']:raise RuntimeError(f"Wikitext fingerprint drift: {ds._fingerprint}")
 docs=[];cur=[];title=''
 def flush()->None:
  nonlocal cur,title
  words=re.findall(r'\S+',' '.join(cur))
  if len(words)>=cfg['task']['minimum_filler_words']:
   did=hashlib.sha256((title+'\n'+' '.join(words)).encode()).hexdigest();docs.append({'dataset_id':did,'config':'wikitext','words':words,'content_hash':text_hash(' '.join(words))})
  cur=[]
 for row in ds:
  text=str(row['text'])
  if re.match(r'^\s*=\s+[^=].*\s=\s*$',text.strip()):flush();title=text.strip()
  elif text.strip():cur.append(text)
 flush();return sorted(docs,key=lambda r:r['dataset_id'])

def agnews_docs(cfg:Mapping[str,Any])->list[dict[str,Any]]:
 require_offline();from datasets import load_dataset
 s=cfg['task']['ag_news'];ds=load_dataset(s['dataset'],split=s['split'],revision=s['revision'])
 if ds._fingerprint!=s['fingerprint']:raise RuntimeError(f"AG News fingerprint drift: {ds._fingerprint}")
 out=[]
 for i,row in enumerate(ds):
  words=re.findall(r'\S+',norm(str(row['text'])))
  if len(words)>=cfg['task']['minimum_filler_words']:
   out.append({'dataset_id':f'agnews:{i}','config':'ag_news','words':words,'content_hash':text_hash(' '.join(words))})
 return sorted(out,key=lambda r:r['dataset_id'])

def choose_window(rec:Mapping[str,Any],cfg:Mapping[str,Any])->tuple[str,str]:
 words=list(rec['words']);width=int(cfg['task']['filler_words']);room=len(words)-width
 if room<0:return '',''
 start=stable(cfg['seed'],rec['dataset_id'],'window')%(room+1);f=' '.join(words[start:start+width]);return f,text_hash(f)

def incidence_audit(keys:Sequence[str],answers:Sequence[str],templates:Sequence[str])->dict[str,Any]:
 rows=[]
 for t in range(len(templates)):
  for a in range(len(answers)):
   for q in range(len(keys)):
    for b in range(len(keys)):
     if b==q:continue
     for s in range(len(keys)):
      if s in (q,b):continue
      rows.append((q,b,s,a,t))
 X=[]
 for q,b,s,a,t in rows:X.append([1]+[q==j for j in range(1,8)]+[b==j for j in range(1,8)]+[s==j for j in range(1,8)]+[a==j for j in range(1,8)]+[t==j for j in range(1,3)])
 X=np.asarray(X,float);sv=np.linalg.svd(X,compute_uv=False);rank=int(np.linalg.matrix_rank(X,tol=1e-8))
 cyc=[]
 for t in range(3):
  for a in range(8):
   for q in range(8):
    b=(q+1)%8;s=(q+2)%8;cyc.append([1]+[q==j for j in range(1,8)]+[b==j for j in range(1,8)]+[s==j for j in range(1,8)]+[a==j for j in range(1,8)]+[t==j for j in range(1,3)])
 cr=int(np.linalg.matrix_rank(np.asarray(cyc,float),tol=1e-8))
 if rank!=31 or sv[-1]<=1e-8 or cr>=31:raise RuntimeError(f'incidence rank failure {rank}/{sv[-1]}/{cr}')
 role_counts={'query':Counter(keys[q] for q,_,_,_,_ in rows),'baseline':Counter(keys[b] for _,b,_,_,_ in rows),'sham':Counter(keys[s] for _,_,s,_,_ in rows)}
 if any(len(set(c.values()))!=1 for c in role_counts.values()):raise RuntimeError('role marginal imbalance')
 return {'ordered_contrasts':len(rows),'columns':31,'rank':rank,'smallest_singular_value':float(sv[-1]),'cyclic_negative_control_rank':cr,'role_counts':{k:dict(v) for k,v in role_counts.items()}}

def prepare(config:Path,output:Path|None=None)->None:
 cfg=loadj(config);root=output or ROOT/cfg['runtime']['prepared_root']
 if root.exists():raise FileExistsError(f'prepared namespace exists: {root}')
 root.mkdir(parents=True);toks=core.load_tokenizers(cfg);ids0,win0=predecessor_exclusions(cfg);used_ids=set(ids0);used_content=set();used_windows=set(win0);rejected=[]
 wiki=[]
 for rec in wiki_docs(cfg):
  filler,wh=choose_window(rec,cfg);reason=None
  if rec['dataset_id'] in used_ids:reason='predecessor_id'
  elif rec['content_hash'] in used_content:reason='duplicate_content'
  elif wh in used_windows:reason='predecessor_or_duplicate_window'
  if reason:rejected.append({'source':'WIKITEXT_FRESH','dataset_id':rec['dataset_id'],'reason':reason});continue
  rec={**rec,'filler':filler,'window_hash':wh};wiki.append(rec);used_ids.add(rec['dataset_id']);used_content.add(rec['content_hash']);used_windows.add(wh)
  if len(wiki)==384:break
 if len(wiki)!=384:raise RuntimeError(f'Wikitext support {len(wiki)}/384')
 ag=[]
 for rec in agnews_docs(cfg):
  filler,wh=choose_window(rec,cfg);reason=None
  if rec['dataset_id'] in used_ids:reason='duplicate_id'
  elif rec['content_hash'] in used_content:reason='cross_source_or_duplicate_content'
  elif wh in used_windows:reason='cross_source_or_predecessor_window'
  if reason:rejected.append({'source':'AGNEWS_FRESH','dataset_id':rec['dataset_id'],'reason':reason});continue
  ag.append({**rec,'filler':filler,'window_hash':wh});used_ids.add(rec['dataset_id']);used_content.add(rec['content_hash']);used_windows.add(wh)
  if len(ag)==384:break
 if len(ag)!=384:raise RuntimeError(f'AG News support {len(ag)}/384')
 keys=list(cfg['task']['keys']);answers=list(cfg['task']['answers']);templates=list(cfg['task']['templates']);audit=incidence_audit(keys,answers,templates)
 raw=[];per={m['key']:[] for m in cfg['models']};wiki_cursor=0;ag_cursor=0
 for source in cfg['task']['sources']:
  for split in cfg['task']['splits']:
   for t,template in enumerate(templates):
    for a,answer in enumerate(answers):
     for q,query in enumerate(keys):
      if source=='WIKITEXT_FRESH':rec=wiki[wiki_cursor];wiki_cursor+=1
      else:rec=ag[ag_cursor];ag_cursor+=1
      contrast=answers[(a+1)%len(answers)];texts=[template.format(reference_key=k,answer=answer,filler=rec['filler'],query_key=query) for k in keys];encoded={};valid=True
      for model,tok in toks.items():
       prompts=[list(tok(x,add_special_tokens=False)['input_ids']) for x in texts];target=list(tok(' '+answer,add_special_tokens=False)['input_ids']);other=list(tok(' '+contrast,add_special_tokens=False)['input_ids']);bos=[tok.bos_token_id] if tok.bos_token_id is not None else []
       if len({len(x) for x in prompts})!=1 or len(target)!=1 or len(other)!=1 or target==other or len(bos+prompts[0])+1>cfg['runtime']['maximum_length']:valid=False;break
       encoded[model]={f'key_{i}_prompt_ids':bos+p for i,p in enumerate(prompts)}|{'continuation_ids':target,'target_id':target[0],'contrast_id':other[0],'prompt_length':len(bos+prompts[0])}
      if not valid:raise RuntimeError(f'tokenizer-length/label failure at {source}/{split}/{t}/{a}/{q}')
      cid=f"{source}:{split}:t{t}:a{a}:q{q}:{rec['dataset_id']}";base={'component_id':cid,'component_block':rec['dataset_id'],'document_id':rec['dataset_id'],'content_hash':rec['content_hash'],'window_hash':rec['window_hash'],'corpus_config':rec['config'],'source':source,'split':split,'template_index':t,'answer_index':a,'answer_word':answer,'contrast_word':contrast,'query_key_index':q,'query_key':query,'filler':rec['filler']}
      raw.append(base)
      for model in per:per[model].append({k:v for k,v in base.items() if k not in {'filler'}}|encoded[model])
 writejl(root/'rows.jsonl',raw)
 for model,rows in per.items():writejl(root/f'{model}.jsonl',rows)
 writejl(root/'rejected_documents.jsonl',rejected)
 accepted=[{'component_id':r['component_id'],'document_id':r['document_id'],'content_hash':r['content_hash'],'window_hash':r['window_hash'],'source':r['source'],'split':r['split'],'corpus_config':r['corpus_config']} for r in raw];writejl(root/'accepted_documents.jsonl',accepted)
 counts=Counter((r['source'],r['split'],r['template_index']) for r in raw);configs=Counter((r['split'],r['corpus_config']) for r in raw if r['source']=='AGNEWS_FRESH')
 if any(v!=64 for v in counts.values()) or any(v!=192 for v in configs.values()) or len({r['document_id'] for r in raw})!=len(raw):raise RuntimeError('prepared balance/disjointness failure')
 manifest={'schema_version':'joint_control_assay_v5_prescore','selection_firewall':'LABEL_TOKENIZER_ONLY_NO_MODEL_FORWARD_OR_LOGIT_FILTER','rows':len(raw),'unique_documents':len({r['document_id'] for r in raw}),'source_split_template_counts':{str(k):v for k,v in sorted(counts.items())},'agnews_config_split_counts':{str(k):v for k,v in sorted(configs.items())},'predecessor_ids':len(ids0),'predecessor_window_hashes':len(win0),'zero_predecessor_or_cross_split_overlap':True,'incidence_audit':audit,'files':{p.name:sha(p) for p in sorted(root.glob('*.jsonl'))}}
 exjson(root/'PRESCORE.json',manifest);print(json.dumps(manifest,indent=2))

def verify_prepared(cfg:Mapping[str,Any])->None:
 root=ROOT/cfg['runtime']['prepared_root'];m=loadj(root/'PRESCORE.json')
 if m['selection_firewall']!='LABEL_TOKENIZER_ONLY_NO_MODEL_FORWARD_OR_LOGIT_FILTER' or m['rows']!=768 or not m['zero_predecessor_or_cross_split_overlap']:raise RuntimeError('prescore semantic drift')
 for name,d in m['files'].items():
  if sha(root/name)!=d:raise RuntimeError(f'prepared drift {name}')

def candidate_files(config:Path,cfg:Mapping[str,Any])->list[Path]:
 p=ROOT/cfg['runtime']['prepared_root'];paths=[config.resolve(),PLAN,SCRIPT,TEST,LAUNCHER,ROOT/'scripts/analyze_joint_controllability_v4_1_pythia.py',ROOT/'reports/joint_controllability_v4_1_diagnostic/v1/diagnostic.md',ROOT/'reports/provenance/joint_controllability_assay_v5_candidate/deterministic_prepare.json',ROOT/cfg['runtime']['cache_attestation'],ROOT/cfg['preservation']['v4_1_tree'],ROOT/cfg['preservation']['v4_1_claim_review'],ROOT/cfg['preservation']['v4_1_diagnostic'],ROOT/cfg['preservation']['closure'],ROOT/'scripts/joint_controllability_benchmark_v3.py',ROOT/'scripts/joint_controllability_benchmark_v4_1.py',p/'PRESCORE.json',p/'rows.jsonl',p/'accepted_documents.jsonl',p/'rejected_documents.jsonl']
 paths += [p/f"{m['key']}.jsonl" for m in cfg['models']]
 review=cfg['runtime'].get('candidate_review')
 if review:paths.append(ROOT/review)
 return paths
def inventory(config:Path,cfg:Mapping[str,Any])->list[dict[str,Any]]:
 out=[]
 for p in candidate_files(config,cfg):
  if not p.is_file():raise RuntimeError(f'candidate absent {p}')
  out.append({'path':p.relative_to(ROOT).as_posix(),'bytes':p.stat().st_size,'sha256':sha(p)})
 return sorted(out,key=lambda r:r['path'])
def preflight(config:Path)->None:
 cfg=loadj(config);preservation_verify(cfg);verify_prepared(cfg);validate_family_registry(cfg)
 if any(cfg['preservation'][x] for x in ('k2_training_authorized','sae_training_authorized','representation_method_evaluation_authorized','automatic_method_launch')):raise RuntimeError('unauthorized training/method path')
 for key in ('output_root','provenance_root'):
  if (ROOT/cfg['runtime'][key]).exists():raise RuntimeError(f"one-shot namespace exists: {key}")
 print(json.dumps({'status':'PASS','candidate_files':len(inventory(config,cfg)),'training':False,'methods':False},indent=2))
def cached_asset_records(snap:Path)->list[dict[str,Any]]:
 required=v41.cached_weight_records(snap);weight_names={r['name'] for r in required}
 index_names={name for name in ('model.safetensors.index.json','pytorch_model.bin.index.json') if (snap/name).is_file()}
 metadata={p.name for p in snap.iterdir() if p.is_file() and p.name in {'config.json','generation_config.json','tokenizer.json','tokenizer_config.json','special_tokens_map.json','vocab.json','merges.txt','added_tokens.json'}}
 files=[]
 for name in sorted(weight_names|index_names|metadata):
  fp=snap/name
  if not fp.is_file():raise RuntimeError(f'cached asset absent {name}')
  files.append({'name':name,'bytes':fp.stat().st_size,'sha256':sha(fp),'resolved_blob':str(fp.resolve())})
 return files

def cache_preflight(config:Path)->None:
 cfg=loadj(config);require_offline()
 from huggingface_hub import snapshot_download
 from transformers import AutoConfig,AutoTokenizer
 expected=(Path(os.environ['HF_HOME'])/'hub').resolve();actual=Path(os.environ.get('TRANSFORMERS_CACHE','')).resolve()
 if actual!=expected or cfg['runtime']['model_cache_root']!='${HF_HOME}/hub':raise RuntimeError('cache root mismatch')
 records=[]
 for m in cfg['models']:
  snap=Path(snapshot_download(m['name'],revision=m['revision'],local_files_only=True))
  AutoConfig.from_pretrained(m['name'],revision=m['revision'],local_files_only=True);AutoTokenizer.from_pretrained(m['name'],revision=m['revision'],local_files_only=True)
  files=cached_asset_records(snap)
  records.append({'model':m['key'],'revision':m['revision'],'snapshot':str(snap),'files':files})
 payload={'schema_version':'joint_control_assay_v5_cache_attestation','status':'PASS','model_cache_root':str(actual),'content_hashed':True,'models':records}
 att=ROOT/cfg['runtime']['cache_attestation']
 if att.exists():
  if loadj(att)!=payload:raise RuntimeError('cache content attestation drift')
 else:exjson(att,payload)
 print(json.dumps(payload,indent=2))
def freeze(config:Path)->None:
 cfg=loadj(config);preflight(config);inv=inventory(config,cfg);payload={'schema_version':'joint_control_assay_v5_freeze','namespace':cfg['namespace'],'config_sha256':sha(config),'candidate_inventory':inv,'candidate_inventory_sha256':hashlib.sha256(canon(inv)).hexdigest(),'v4_1_tree_sha256':sha(ROOT/cfg['preservation']['v4_1_tree']),'task_assay_only':True,'model_specific_eligibility':True,'two_family_barrier':True,'new_training':False,'method_evaluation':False,'one_shot':True,'retry_authorized':False}
 exjson(ROOT/cfg['runtime']['freeze'],payload);print(json.dumps(payload,indent=2))
def verify_freeze(config:Path,cfg:Mapping[str,Any])->dict[str,Any]:
 f=loadj(ROOT/cfg['runtime']['freeze'])
 if f['config_sha256']!=sha(config) or f['candidate_inventory']!=inventory(config,cfg):raise RuntimeError('frozen candidate drift')
 preservation_verify(cfg);verify_prepared(cfg);return f

def validate_family_registry(cfg:Mapping[str,Any])->None:
 models=list(cfg['models']);keys=[m['key'] for m in models];families=[m['family'] for m in models]
 if len(keys)!=len(set(keys)) or len(families)!=len(set(families)):raise RuntimeError('model keys and families must be one-to-one')

def family_count(models:Sequence[Mapping[str,Any]],field:str)->int:
 return len({str(m['family']) for m in models if bool(m[field])})

def normalized_gpu_uuid(value:Any)->str:
 x=str(value);return x if x.startswith('GPU-') else 'GPU-'+x

def validate_runtime_gpu()->str:
 expected=os.environ.get('EXPECTED_GPU_UUID')
 if not expected:raise RuntimeError('EXPECTED_GPU_UUID is required')
 if torch.cuda.device_count()!=1:raise RuntimeError(f'exactly one visible GPU required, got {torch.cuda.device_count()}')
 actual=normalized_gpu_uuid(torch.cuda.get_device_properties(0).uuid)
 if actual!=expected:raise RuntimeError(f'GPU UUID mismatch expected={expected} actual={actual}')
 return actual

def confirmation_authorized(gate:Mapping[str,Any],key:str)->bool:
 own=next((x for x in gate.get('models',[]) if x['model']==key),None)
 return gate.get('status')=='PASS' and own is not None and bool(own['eligible_both_sources'])

def model_rows(cfg:Mapping[str,Any],key:str,split:str)->list[dict[str,Any]]:return [r for r in readjl(ROOT/cfg['runtime']['prepared_root']/f'{key}.jsonl') if r['split']==split]
def score_rows(cfg:Mapping[str,Any],key:str,rows:list[dict[str,Any]])->list[dict[str,Any]]:
 from transformers import AutoModelForCausalLM,AutoTokenizer
 spec=core.model_spec(cfg,key);validate_runtime_gpu();device=torch.device('cuda:0');model=AutoModelForCausalLM.from_pretrained(spec['name'],revision=spec['revision'],local_files_only=True,torch_dtype=torch.float32).to(device).eval()
 for p in model.parameters():p.requires_grad_(False)
 tok=AutoTokenizer.from_pretrained(spec['name'],revision=spec['revision'],local_files_only=True);pad=tok.pad_token_id if tok.pad_token_id is not None else tok.eos_token_id;layer=int(spec['layers'][0]);vals=[]
 for j in range(8):
  result=core.run_panel(model,rows,f'key_{j}',layer,int(spec['batch_size']),pad,device,None,False);vals.append(core.logodds(result['logits'],rows))
 L=np.stack(vals,axis=1);out=[]
 for r,x in zip(rows,L,strict=True):
  q=int(r['query_key_index']);other=[b for b in range(8) if b!=q];f=float(np.mean([x[q]-x[b] for b in other]));ss=[abs(float(x[s]-x[b])) for b in other for s in other if s!=b];S=float(np.mean(ss));eligible=f>float(cfg['gate']['minimum_full_effect']);ratio=S/max(f,float(cfg['gate']['epsilon'])) if eligible else None
  out.append({'schema_version':'joint_control_assay_v5_component','model':key,'family':spec['family'],'source':r['source'],'split':r['split'],'template_index':r['template_index'],'component_id':r['component_id'],'component_block':r['component_block'],'query_key_index':q,'answer_index':r['answer_index'],'corpus_config':r['corpus_config'],'binding_logodds':[float(z) for z in x],'full_effect':f,'sham_dispersion':S,'eligible':eligible,'sham_ratio':ratio})
 del model;torch.cuda.empty_cache();return out

def worker(config:Path,key:str,split:str)->None:
 cfg=loadj(config);root=ROOT/cfg['runtime']['output_root'];stage='development' if split=='development' else 'confirmation';out=root/stage/key
 try:
  verify_freeze(config,cfg)
  if split=='confirmation':
   gate_path=root/'development_gate/result.json';start=time.monotonic()
   while not gate_path.exists():
    if (root/'development_gate/FAILED.json').exists():
     out.mkdir(parents=True,exist_ok=False);exjson(out/'BLOCKED.json',{'status':'BLOCKED','reason':'DEVELOPMENT_GATE_TECHNICAL_FAILURE','model':key,'model_loaded':False,'freeze_sha256':sha(ROOT/cfg['runtime']['freeze'])});return
    if time.monotonic()-start>cfg['runtime']['gate_timeout_seconds']:raise TimeoutError('development gate timeout')
    time.sleep(cfg['runtime']['gate_poll_seconds'])
   gate=loadj(gate_path)
   if not confirmation_authorized(gate,key):
    out.mkdir(parents=True,exist_ok=False);exjson(out/'BLOCKED.json',{'status':'BLOCKED','reason':'GLOBAL_OR_OWN_DEVELOPMENT_INELIGIBLE','model':key,'model_loaded':False,'freeze_sha256':sha(ROOT/cfg['runtime']['freeze'])});return
  out.mkdir(parents=True,exist_ok=False);rows=model_rows(cfg,key,split);metrics=score_rows(cfg,key,rows);writejl(out/'metrics.jsonl',metrics);exjson(out/'COMPLETE.json',{'status':'COMPLETE','model':key,'split':split,'rows':len(metrics),'metrics_sha256':sha(out/'metrics.jsonl'),'freeze_sha256':sha(ROOT/cfg['runtime']['freeze']),'gpu_uuid':normalized_gpu_uuid(torch.cuda.get_device_properties(0).uuid)})
 except BaseException as e:
  publish_failure(root/stage/f'{key}_FAILED.json',{'status':'FAILED','model':key,'split':split,'error_type':type(e).__name__,'error':str(e),'traceback':traceback.format_exc(),'freeze_sha256':sha(ROOT/cfg['runtime']['freeze']) if (ROOT/cfg['runtime']['freeze']).is_file() else None});raise

def stratified_interval(rows:Sequence[Mapping[str,Any]],cfg:Mapping[str,Any],seed:int)->list[float]|None:
 selected=[r for r in rows if r['eligible']];by={t:[float(r['sham_ratio']) for r in selected if int(r['template_index'])==t] for t in range(3)}
 if any(not x for x in by.values()):return None
 point=float(np.mean([np.mean(x) for x in by.values()]));rng=np.random.default_rng(seed);draw=[]
 for _ in range(int(cfg['gate']['bootstrap_draws'])):draw.append(float(np.mean([np.mean(rng.choice(x,size=len(x),replace=True)) for x in by.values()])))
 return [float(np.quantile(draw,.025)),point,float(np.quantile(draw,.975))]
def summarize(rows:Sequence[Mapping[str,Any]],cfg:Mapping[str,Any],seed:int)->dict[str,Any]:
 per=[sum(bool(r['eligible']) for r in rows if int(r['template_index'])==t) for t in range(3)];n=sum(per);ci=stratified_interval(rows,cfg,seed);passed=all(x>=cfg['gate']['minimum_eligible_per_template'] for x in per) and n>=cfg['gate']['minimum_eligible_total'] and n/len(rows)>=cfg['gate']['minimum_effect_eligibility'] and ci is not None and ci[1]<=cfg['gate']['maximum_sham_fraction'] and ci[2]<cfg['gate']['maximum_sham_fraction_ci']
 return {'rows':len(rows),'eligible_rows':n,'eligible_per_template':per,'eligibility':n/len(rows),'sham_fraction_ci':ci,'passes':bool(passed)}
def wait_terminals(root:Path,names:list[str],stage:str,timeout:float,poll:float)->None:
 start=time.monotonic()
 while True:
  done=[]
  for n in names:done.append(any((root/stage/n/x).exists() for x in ('COMPLETE.json','BLOCKED.json')) or (root/stage/f'{n}_FAILED.json').exists())
  if all(done):return
  if time.monotonic()-start>timeout:raise TimeoutError(f'{stage} workers timeout')
  time.sleep(poll)
def development_aggregate(config:Path)->None:
 cfg=loadj(config);root=ROOT/cfg['runtime']['output_root'];names=[m['key'] for m in cfg['models']];out=root/'development_gate';out.mkdir(parents=True,exist_ok=False)
 try:
  verify_freeze(config,cfg);manifest=loadj(ROOT/cfg['runtime']['provenance_root']/'launch_manifest.json');expected_gpu={x['model']:x['uuid'] for x in manifest['assignments']}
  wait_terminals(root,names,'development',cfg['runtime']['worker_timeout_seconds'],cfg['runtime']['gate_poll_seconds'])
  failed=[n for n in names if (root/'development'/f'{n}_FAILED.json').exists()]
  if failed:raise RuntimeError(f'development worker failures: {failed}')
  models=[]
  for n in names:
   p=root/'development'/n/'metrics.jsonl';c=loadj(root/'development'/n/'COMPLETE.json');rows=readjl(p)
   if c['metrics_sha256']!=sha(p) or len(rows)!=384 or c['gpu_uuid']!=expected_gpu[n]:raise RuntimeError(f'development artifact or GPU drift {n}')
   cells=[]
   for source in cfg['task']['sources']:
    rr=[r for r in rows if r['source']==source];cells.append({'source':source,**summarize(rr,cfg,stable(cfg['seed'],n,source,'development'))})
   models.append({'model':n,'family':core.model_spec(cfg,n)['family'],'cells':cells,'eligible_both_sources':all(x['passes'] for x in cells)})
  eligible=family_count(models,'eligible_both_sources');status='PASS' if eligible>=cfg['gate']['minimum_replicating_model_families'] else 'FAIL';result={'schema_version':'joint_control_assay_v5_development_gate','status':status,'models':models,'eligible_model_families':eligible,'confirmation_authorized_for_eligible_models':status=='PASS','freeze_sha256':sha(ROOT/cfg['runtime']['freeze'])};exjson(out/'result.json',result);exjson(out/f'{status}.json',result)
 except BaseException as e:publish_failure(out/'FAILED.json',{'status':'FAILED','error':str(e),'traceback':traceback.format_exc()});raise

def final_aggregate(config:Path)->None:
 cfg=loadj(config);root=ROOT/cfg['runtime']['output_root'];names=[m['key'] for m in cfg['models']];out=root/'final';out.mkdir(parents=True,exist_ok=False)
 try:
  verify_freeze(config,cfg);manifest=loadj(ROOT/cfg['runtime']['provenance_root']/'launch_manifest.json');expected_gpu={x['model']:x['uuid'] for x in manifest['assignments']}
  wait_terminals(root,names,'confirmation',cfg['runtime']['worker_timeout_seconds'],cfg['runtime']['gate_poll_seconds']);dev=loadj(root/'development_gate/result.json');failed=[n for n in names if (root/'confirmation'/f'{n}_FAILED.json').exists()]
  if failed:raise RuntimeError(f'confirmation worker failures: {failed}')
  models=[]
  for dm in dev['models']:
   n=dm['model'];blocked=(root/'confirmation'/n/'BLOCKED.json').exists();cells=[]
   if not blocked:
    p=root/'confirmation'/n/'metrics.jsonl';c=loadj(root/'confirmation'/n/'COMPLETE.json');rows=readjl(p)
    if c['metrics_sha256']!=sha(p) or len(rows)!=384 or c['gpu_uuid']!=expected_gpu[n]:raise RuntimeError(f'confirmation artifact or GPU drift {n}')
    for source in cfg['task']['sources']:cells.append({'source':source,**summarize([r for r in rows if r['source']==source],cfg,stable(cfg['seed'],n,source,'confirmation'))})
   devmap={x['source']:x['passes'] for x in dm['cells']};cmap={x['source']:x['passes'] for x in cells};directions={'WIKITEXT_FRESH_to_AGNEWS_FRESH':bool(devmap.get('WIKITEXT_FRESH') and cmap.get('AGNEWS_FRESH')),'AGNEWS_FRESH_to_WIKITEXT_FRESH':bool(devmap.get('AGNEWS_FRESH') and cmap.get('WIKITEXT_FRESH'))};models.append({'model':n,'family':dm['family'],'development_eligible':dm['eligible_both_sources'],'confirmation_blocked':blocked,'confirmation_cells':cells,'future_method_direction_eligibility':directions,'passes_both_directions':all(directions.values())})
  positive=family_count(models,'passes_both_directions');status='PASS' if positive>=cfg['gate']['minimum_replicating_model_families'] else 'FAIL';result={'schema_version':'joint_control_assay_v5_final','status':status,'task_assay_only':True,'representation_methods_evaluated':False,'training_performed':False,'models':models,'positive_model_families':positive,'minimum_required':cfg['gate']['minimum_replicating_model_families'],'freeze_sha256':sha(ROOT/cfg['runtime']['freeze'])};exjson(out/'result.json',result);exjson(out/f'{status}.json',result)
 except BaseException as e:publish_failure(out/'FAILED.json',{'status':'FAILED','error':str(e),'traceback':traceback.format_exc()});raise

def main()->None:
 p=argparse.ArgumentParser();p.add_argument('command',choices=['prepare','preservation-verify','cache-preflight','preflight','freeze','verify-freeze','worker','development-aggregate','final-aggregate']);p.add_argument('--config',type=Path,default=DEFAULT);p.add_argument('--output',type=Path);p.add_argument('--model');p.add_argument('--split',choices=['development','confirmation']);a=p.parse_args();cfg=loadj(a.config)
 if a.command=='prepare':prepare(a.config,a.output)
 elif a.command=='preservation-verify':preservation_verify(cfg);print('PASS')
 elif a.command=='cache-preflight':cache_preflight(a.config)
 elif a.command=='preflight':preflight(a.config)
 elif a.command=='freeze':freeze(a.config)
 elif a.command=='verify-freeze':verify_freeze(a.config,cfg);print('PASS')
 elif a.command=='worker':
  if not a.model or not a.split:p.error('worker requires --model and --split')
  worker(a.config,a.model,a.split)
 elif a.command=='development-aggregate':development_aggregate(a.config)
 else:final_aggregate(a.config)
if __name__=='__main__':main()
