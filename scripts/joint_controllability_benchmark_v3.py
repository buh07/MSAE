#!/usr/bin/env python3
"""Prospective natural-text joint controllability benchmark v3.

No SAE or language-model training path exists. Development-only supervised subspaces are closed-form.
"""
from __future__ import annotations
import argparse, hashlib, json, math, os, platform, random, re, sys, time
from pathlib import Path
from typing import Any, Mapping, Sequence
import numpy as np
import torch
import torch.nn.functional as F

import proxy_control_benchmark_v1 as v1
import proxy_control_benchmark_v2 as v2

ROOT=Path(__file__).resolve().parents[1]; SCRIPT=Path(__file__).resolve()
DEFAULT=ROOT/'configs/joint_controllability_benchmark_v3/run.json'
PLAN=ROOT/'PLAN_JOINT_CONTROLLABILITY_V3.md'
PLAN_REVIEW=ROOT/'reports/adversarial/joint_controllability_v3_plan_review.md'
CANDIDATE_REVIEW=ROOT/'reports/adversarial/joint_controllability_v3_candidate_review.md'
TEST=ROOT/'tests/test_joint_controllability_benchmark_v3.py'
LAUNCHER=ROOT/'scripts/launch_joint_controllability_benchmark_v3_tmux.sh'


def canon(x:Any)->bytes:return json.dumps(x,sort_keys=True,separators=(',',':'),allow_nan=False).encode()
def loadj(p:Path)->Any:return json.loads(p.read_text())
def sha(p:Path)->str:
 h=hashlib.sha256();
 with p.open('rb') as f:
  for b in iter(lambda:f.read(1<<20),b''):h.update(b)
 return h.hexdigest()
def stable(seed:int,*parts:Any)->int:return int.from_bytes(hashlib.sha256('|'.join(map(str,(seed,)+parts)).encode()).digest()[:8],'little')%(2**32)
def exjson(p:Path,x:Any)->None:
 p.parent.mkdir(parents=True,exist_ok=True);fd=os.open(p,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
 with os.fdopen(fd,'wb') as f:f.write(canon(x)+b'\n')
def atomjson(p:Path,x:Any)->None:
 p.parent.mkdir(parents=True,exist_ok=True);q=p.with_suffix(p.suffix+f'.tmp.{os.getpid()}');q.write_bytes(canon(x)+b'\n');os.replace(q,p)
def writejl(p:Path,rows:Sequence[Mapping[str,Any]])->None:
 fd=os.open(p,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
 with os.fdopen(fd,'wb') as f:
  for r in rows:f.write(canon(dict(r))+b'\n')
def readjl(p:Path)->list[dict[str,Any]]:return [json.loads(x) for x in p.read_text().splitlines() if x]
def seedall(s:int)->None:
 random.seed(s);np.random.seed(s);torch.manual_seed(s);torch.cuda.manual_seed_all(s);torch.use_deterministic_algorithms(True);torch.backends.cudnn.benchmark=False


def model_spec(cfg:Mapping[str,Any],key:str)->dict[str,Any]:return next(dict(x) for x in cfg['models'] if x['key']==key)
def stage(spec:Mapping[str,Any],layer:int)->str:
 ls=list(spec['layers'])
 if len(ls)==1:return 'middle'
 return 'early' if layer==ls[0] else ('late' if layer==ls[-1] else 'middle')


def asset_entries(cfg:Mapping[str,Any])->list[dict[str,Any]]:
 out=[]
 for m in cfg['models']:
  s=m['sae'];repo=s['repo'];rev=s['revision']
  if s['format']=='saelens_topk':
   for layer in m['layers']:
    base=s['path_template'].format(layer=layer)
    for rel in [f'{base}/cfg.json',f'{base}/sae_weights.safetensors']:
     out.append({'model':m['key'],'layer':layer,'architecture':'TopK','repo':repo,'revision':rev,'relative_path':rel})
  elif s['format']=='gemma_scope_jumprelu':
   for layer in m['layers']:out.append({'model':m['key'],'layer':layer,'architecture':'JumpReLU','repo':repo,'revision':rev,'relative_path':s['paths'][str(layer)]})
  else:
   for arch in s['architectures']:
    base=f'{arch}_pythia-160m-deduped__0108/resid_post_layer_{s["layer"]}/trainer_{s["trainer"]}'
    for name in ['config.json','eval_results.json','ae.pt']:
     out.append({'model':m['key'],'layer':s['layer'],'architecture':arch,'repo':repo,'revision':rev,'relative_path':f'{base}/{name}'})
 return out


def fetch_assets(cfg:Mapping[str,Any])->dict[str,Any]:
 from huggingface_hub import hf_hub_download
 rows=[]
 for e in asset_entries(cfg):
  p=Path(hf_hub_download(e['repo'],e['relative_path'],revision=e['revision']))
  rows.append({**e,'cache_path':str(p),'bytes':p.stat().st_size,'sha256':sha(p)})
 payload={'schema_version':'joint_control_v3_public_sae_manifest','assets':rows,'asset_count':len(rows),'no_sae_training':True}
 path=ROOT/cfg['runtime']['asset_manifest']
 if path.exists():
  old=loadj(path)
  if old!=payload:raise RuntimeError('public SAE manifest drift')
 else:exjson(path,payload)
 return payload


def load_tokenizers(cfg:Mapping[str,Any])->dict[str,Any]:
 from transformers import AutoTokenizer
 out={}
 for m in cfg['models']:
  t=AutoTokenizer.from_pretrained(m['name'],revision=m['revision'],local_files_only=True,use_fast=True)
  if t.pad_token_id is None:t.pad_token=t.eos_token
  t.padding_side='right';out[m['key']]=t
 return out

def words(text:str)->list[str]:return re.findall(r"\S+",' '.join(text.split()))
def one_token(tok:Any,w:str)->bool:return len(tok(' '+w,add_special_tokens=False)['input_ids'])==1

def corpus_documents(cfg:Mapping[str,Any])->list[tuple[str,list[str]]]:
 from datasets import load_dataset
 tc=cfg['task'];ds=load_dataset(tc['dataset'],tc['config'],split=tc['split'])
 if ds._fingerprint!=tc['fingerprint']:raise RuntimeError(f'dataset fingerprint drift {ds._fingerprint}')
 docs=[];cur=[];title=''
 def flush():
  nonlocal cur,title
  w=words(' '.join(cur))
  if len(w)>=int(tc['minimum_words']):
   did=hashlib.sha256((title+'\n'+' '.join(w)).encode()).hexdigest();docs.append((did,w))
  cur=[]
 for row in ds:
  text=str(row['text'])
  if re.match(r'^\s*=\s+[^=].*\s=\s*$',text.strip()):flush();title=text.strip();continue
  if text.strip():cur.append(text)
 flush();docs.sort(key=lambda x:x[0]);return docs


def prepare(config:Path,output:Path|None=None)->None:
 cfg=loadj(config);root=output or ROOT/cfg['runtime']['prepared_root']
 if root.exists() and any(root.iterdir()):raise FileExistsError(f'prepared namespace nonempty: {root}')
 root.mkdir(parents=True,exist_ok=True);toks=load_tokenizers(cfg);docs=corpus_documents(cfg);tc=cfg['task']
 need=2*(int(tc['development_per_source'])+int(tc['test_per_source']));selected=[];used=set();cursor=0
 # Each accepted target consumes two unique donor articles. Window choice is hash-derived and label-only.
 while len(selected)<need and cursor+2<len(docs):
  tri=docs[cursor:cursor+3];cursor+=3
  if len({x[0] for x in tri})!=3 or any(x[0] in used for x in tri):continue
  did,w=tri[0];span=int(tc['true_prefix_words'])+int(tc['local_suffix_words']);cont=int(tc['continuation_words'])
  room=len(w)-span-cont-1
  if room<=0:continue
  start=span+(stable(cfg['seed'],did)%room);target=w[start]
  if not all(one_token(t,target) for t in toks.values()):continue
  # Reject markup-like and non-word targets prospectively.
  if not re.match(r"^[A-Za-z][A-Za-z'-]*$",target):continue
  pre=w[start-span:start-int(tc['local_suffix_words'])];suffix=w[start-int(tc['local_suffix_words']):start];continu=w[start:start+cont]
  donor=[]
  ok=True
  for _,dw in tri[1:]:
   # Over-collect natural donor words, then tokenizer-specifically truncate to the exact
   # coherent-prefix token count. This preserves natural text without padding or repetition.
   donor_words=int(tc['true_prefix_words'])*3
   if len(dw)<donor_words+5:ok=False;break
   off=stable(cfg['seed'],did,_[0:8])%(len(dw)-donor_words+1);donor.append(dw[off:off+donor_words])
  if not ok:continue
  selected.append({'document_id':did,'donor_base_id':tri[1][0],'donor_sham_id':tri[2][0],'true_prefix':' '.join(pre),'local_suffix':' '.join(suffix),'continuation':' '.join(continu),'target_word':target,'base_prefix':' '.join(donor[0]),'sham_prefix':' '.join(donor[1])})
  used.update(x[0] for x in tri)
 if len(selected)<need:raise RuntimeError(f'natural support {len(selected)} below {need}')
 # Freeze source/split assignments and morphology-matched natural contrasts.
 assignments=[];i=0
 for source in tc['sources']:
  for split,n in [('development',int(tc['development_per_source'])),('test',int(tc['test_per_source']))]:
   for _ in range(n):assignments.append((source,split));i+=1
 for i,r in enumerate(selected):
  r['source'],r['split']=assignments[i];r['component_id']=f"{r['source']}:{r['split']}:{r['document_id'][:16]}";r['component_block']=r['document_id']
  candidates=[selected[(i+j)%len(selected)]['target_word'] for j in range(1,len(selected))]
  same=[x for x in candidates if x!=r['target_word'] and x[0].isupper()==r['target_word'][0].isupper()]
  r['contrast_word']=(same or [x for x in candidates if x!=r['target_word']])[0]
 writejl(root/'rows.jsonl',selected)
 model_checks={}
 for key,tok in toks.items():
  out=[];maxlen=0
  bos=[tok.bos_token_id] if tok.bos_token_id is not None else []
  for r in selected:
   suffix=tok(' '+r['local_suffix'],add_special_tokens=False)['input_ids'];true=tok(' '+r['true_prefix'],add_special_tokens=False)['input_ids']
   L=len(true);base=tok(' '+r['base_prefix'],add_special_tokens=False)['input_ids'][:L];sham=tok(' '+r['sham_prefix'],add_special_tokens=False)['input_ids'][:L]
   if len(base)!=L or len(sham)!=L:raise RuntimeError('donor token support')
   prompts=[bos+x+suffix for x in (base,true,sham)];lengths=list(map(len,prompts))
   if len(set(lengths))!=1:raise RuntimeError('prompt length mismatch')
   cont=tok(' '+r['continuation'],add_special_tokens=False)['input_ids'][:int(tc['teacher_forced_tokens'])]
   target=tok(' '+r['target_word'],add_special_tokens=False)['input_ids'];contrast=tok(' '+r['contrast_word'],add_special_tokens=False)['input_ids']
   if len(target)!=1 or len(contrast)!=1 or target==contrast or not cont or cont[0]!=target[0]:raise RuntimeError('answer token drift')
   if lengths[0]+len(cont)>int(cfg['runtime']['maximum_length']):raise RuntimeError('maximum length exceeded')
   out.append({'component_id':r['component_id'],'component_block':r['component_block'],'source':r['source'],'split':r['split'],'document_id':r['document_id'],'base_prompt_ids':prompts[0],'full_prompt_ids':prompts[1],'sham_prompt_ids':prompts[2],'continuation_ids':cont,'target_id':target[0],'contrast_id':contrast[0]});maxlen=max(maxlen,lengths[0]+len(cont))
  writejl(root/f'{key}.jsonl',out);model_checks[key]={'rows':len(out),'maximum_tokens':maxlen,'prompt_lengths_exact':True,'one_token_targets':True}
 manifest={'schema_version':'joint_control_v3_prescore','dataset_fingerprint':tc['fingerprint'],'rows':len(selected),'documents_used':len(used),'target_and_donor_disjoint':len(used)==3*len(selected),'selection_firewall':'LABEL_TOKENIZER_ONLY_NO_MODEL_FORWARD_OR_LOGIT_FILTER','within_corpus_transfer':True,'model_checks':model_checks,'files':{p.name:sha(p) for p in sorted(root.glob('*.jsonl'))}}
 exjson(root/'PRESCORE.json',manifest);print(json.dumps(manifest,indent=2))


def verify_prepared(cfg:Mapping[str,Any])->None:
 root=ROOT/cfg['runtime']['prepared_root'];m=loadj(root/'PRESCORE.json')
 if m['selection_firewall']!='LABEL_TOKENIZER_ONLY_NO_MODEL_FORWARD_OR_LOGIT_FILTER' or not m['target_and_donor_disjoint']:raise RuntimeError('prescore firewall failure')
 for n,h in m['files'].items():
  if sha(root/n)!=h:raise RuntimeError(f'prepared drift {n}')
 rows=readjl(root/'rows.jsonl');ids=[r['document_id'] for r in rows]+[r['donor_base_id'] for r in rows]+[r['donor_sham_id'] for r in rows]
 if len(ids)!=len(set(ids)):raise RuntimeError('document reuse')


def candidate_files(config:Path,cfg:Mapping[str,Any])->list[Path]:
 root=ROOT/cfg['runtime']['prepared_root'];paths=[config.resolve(),PLAN,PLAN_REVIEW,SCRIPT,TEST,LAUNCHER,ROOT/cfg['runtime']['asset_manifest'],ROOT/'reports/provenance/joint_controllability_benchmark_v3/technical_hook_smoke.json',ROOT/cfg['preservation']['closure'],root/'PRESCORE.json',root/'rows.jsonl']+[root/f"{m['key']}.jsonl" for m in cfg['models']]
 return paths

def inventory(config:Path,cfg:Mapping[str,Any])->list[dict[str,Any]]:
 out=[]
 for p in candidate_files(config,cfg):
  if not p.is_file():raise RuntimeError(f'candidate absent {p}')
  out.append({'path':p.relative_to(ROOT).as_posix(),'bytes':p.stat().st_size,'sha256':sha(p)})
 return sorted(out,key=lambda x:x['path'])

def preflight(config:Path)->None:
 cfg=loadj(config);verify_prepared(cfg);assets=fetch_assets(cfg)
 if sha(ROOT/cfg['preservation']['closure'])!=cfg['preservation']['closure_sha256']:raise RuntimeError('architecture closure drift')
 if cfg['preservation']['k2_training_authorized'] or cfg['preservation']['sae_training_authorized']:raise RuntimeError('training authorization drift')
 if (ROOT/cfg['runtime']['output_root']).exists():raise RuntimeError('output namespace exists')
 print(json.dumps({'status':'PASS','assets':assets['asset_count'],'inventory':len(inventory(config,cfg))},indent=2))
def freeze(config:Path)->None:
 cfg=loadj(config);preflight(config);inv=inventory(config,cfg)
 payload={'schema_version':'joint_control_v3_freeze','namespace':cfg['namespace'],'config_sha256':sha(config),'candidate_inventory':inv,'candidate_inventory_sha256':hashlib.sha256(canon(inv)).hexdigest(),'public_sae_manifest_sha256':sha(ROOT/cfg['runtime']['asset_manifest']),'prescore_sha256':sha(ROOT/cfg['runtime']['prepared_root']/'PRESCORE.json'),'closure_sha256':cfg['preservation']['closure_sha256'],'new_k2_training':False,'new_sae_training':False,'within_corpus_transfer':True,'retry_authorized':False}
 exjson(ROOT/cfg['runtime']['freeze'],payload);print(json.dumps(payload,indent=2))
def verify_freeze(config:Path,cfg:Mapping[str,Any])->dict[str,Any]:
 f=loadj(ROOT/cfg['runtime']['freeze'])
 if f['config_sha256']!=sha(config) or f['candidate_inventory']!=inventory(config,cfg):raise RuntimeError('frozen candidate drift')
 if sha(ROOT/cfg['preservation']['closure'])!=f['closure_sha256']:raise RuntimeError('closure drift')
 return f


class PublicSAE:
 def __init__(self,name:str,Wenc:torch.Tensor,benc:torch.Tensor,Wdec:torch.Tensor,bdec:torch.Tensor,kind:str,k:int|None=None,threshold:torch.Tensor|None=None,extra:dict[str,torch.Tensor]|None=None,normalize:str='none'):
  self.name=name;self.Wenc=Wenc;self.benc=benc;self.Wdec=Wdec;self.bdec=bdec;self.kind=kind;self.k=k;self.threshold=threshold;self.extra=extra or {};self.normalize=normalize
 def norm(self,x:torch.Tensor)->torch.Tensor:
  return F.layer_norm(x,(x.shape[-1],)) if self.normalize=='layer_norm' else x
 def encode(self,x:torch.Tensor)->torch.Tensor:
  x=self.norm(x)
  if self.kind=='standard':return F.relu((x-self.bdec)@self.Wenc+self.benc)
  if self.kind=='gated':
   a=(x-self.bdec)@self.Wenc;gate=(a+self.extra['gate_bias']>0);return gate*F.relu(self.extra['r_mag'].exp()*a+self.extra['mag_bias'])
  pre=x@self.Wenc+self.benc
  if self.kind=='jumprelu':return F.relu(pre)*(pre>self.threshold)
  z=F.relu(pre);vals,idx=torch.topk(z,min(int(self.k or 1),z.shape[-1]),dim=-1);out=torch.zeros_like(z);out.scatter_(-1,idx,vals);return out
 def decode(self,z:torch.Tensor)->torch.Tensor:return z@self.Wdec+self.bdec

def manifest_path(cfg:Mapping[str,Any],model:str,layer:int,arch:str,suffix:str)->Path:
 rows=loadj(ROOT/cfg['runtime']['asset_manifest'])['assets'];q=[r for r in rows if r['model']==model and int(r['layer'])==layer and r['architecture']==arch and r['relative_path'].endswith(suffix)]
 if len(q)!=1:raise RuntimeError(f'asset lookup {model}/{layer}/{arch}/{suffix}:{len(q)}')
 p=Path(q[0]['cache_path'])
 if sha(p)!=q[0]['sha256']:raise RuntimeError('asset hash drift')
 return p

def load_public_saes(cfg:Mapping[str,Any],key:str,layer:int,device:torch.device)->dict[str,PublicSAE]:
 m=model_spec(cfg,key);s=m['sae'];out={}
 if s['format']=='saelens_topk':
  from safetensors.torch import load_file
  x=load_file(str(manifest_path(cfg,key,layer,'TopK','sae_weights.safetensors')),device=str(device));
  out['public_sae_primary']=PublicSAE('gpt2_oai_topk',x['W_enc'],x['b_enc'],x['W_dec'],x['b_dec'],'topk',int(s['k']),normalize=s['normalize'])
 elif s['format']=='gemma_scope_jumprelu':
  z=np.load(manifest_path(cfg,key,layer,'JumpReLU','params.npz'));t=lambda n:torch.from_numpy(np.asarray(z[n])).to(device)
  out['public_sae_primary']=PublicSAE('gemma_scope_jumprelu',t('W_enc'),t('b_enc'),t('W_dec'),t('b_dec'),'jumprelu',threshold=t('threshold'))
 else:
  for arch in s['architectures']:
   x=torch.load(manifest_path(cfg,key,layer,arch,'ae.pt'),map_location=device,weights_only=True)
   name='public_sae_primary' if arch==s['primary'] else 'saebench_'+arch.lower()
   if arch=='Standard':sae=PublicSAE(arch,x['encoder.weight'].T,x['encoder.bias'],x['decoder.weight'].T,x['bias'],'standard')
   elif arch=='GatedSAE':sae=PublicSAE(arch,x['encoder.weight'].T,torch.zeros_like(x['gate_bias']),x['decoder.weight'].T,x['decoder_bias'],'gated',extra={k:x[k] for k in ['r_mag','gate_bias','mag_bias']})
   elif arch=='JumpRelu':sae=PublicSAE(arch,x['W_enc'],x['b_enc'],x['W_dec'],x['b_dec'],'jumprelu',threshold=x['threshold'])
   elif 'encoder.weight' in x:
    sae=PublicSAE(arch,x['encoder.weight'].T,x['encoder.bias'],x['decoder.weight'].T,x['b_dec'],'topk',int(x['k']))
   else:
    sae=PublicSAE(arch,x['W_enc'],x['b_enc'],x['W_dec'],x['b_dec'],'topk',int(x['k']))
   out[name]=sae
 return out


def rows_for(cfg:Mapping[str,Any],key:str)->list[dict[str,Any]]:return readjl(ROOT/cfg['runtime']['prepared_root']/f'{key}.jsonl')
def batch_tensors(rows:Sequence[Mapping[str,Any]],kind:str,pad:int,device:torch.device)->tuple[torch.Tensor,torch.Tensor,torch.Tensor,list[list[int]]]:
 seq=[];bounds=[];conts=[]
 for r in rows:
  p=list(r[f'{kind}_prompt_ids']);c=list(r['continuation_ids']);seq.append(p+c);bounds.append(len(p)-1);conts.append(c)
 L=max(map(len,seq));ids=torch.full((len(seq),L),pad,dtype=torch.long,device=device);mask=torch.zeros_like(ids)
 for i,s in enumerate(seq):ids[i,:len(s)]=torch.tensor(s,device=device);mask[i,:len(s)]=1
 return ids,mask,torch.tensor(bounds,device=device),conts

def run_panel(model:Any,rows:Sequence[Mapping[str,Any]],kind:str,layer:int,batch:int,pad:int,device:torch.device,patches:np.ndarray|None=None,need_hidden:bool=True)->dict[str,np.ndarray]:
 H=[];L=[];N=[];module=v1._module_for_layer(model,layer)
 for st in range(0,len(rows),batch):
  rr=rows[st:st+batch];ids,mask,bounds,conts=batch_tensors(rr,kind,pad,device);ar=torch.arange(len(rr),device=device);capt=[]
  pt=None if patches is None else torch.from_numpy(np.asarray(patches[st:st+batch],np.float32)).to(device)
  def hook(_m,_i,o):
   h=o[0] if isinstance(o,tuple) else o;capt.append(h.detach())
   if pt is not None:
    z=h.clone();z[ar,bounds]+=pt.to(z.dtype);h=z
   return (h,)+o[1:] if isinstance(o,tuple) else h
  hd=module.register_forward_hook(hook)
  try:
   with torch.no_grad():out=model(input_ids=ids,attention_mask=mask,use_cache=False)
  finally:hd.remove()
  logits=out.logits.float();L.append(logits[ar,bounds].cpu().numpy())
  if need_hidden:H.append(capt[0][ar,bounds].float().cpu().numpy())
  n=[]
  for i,c in enumerate(conts):
   vals=[]
   for j,t in enumerate(c):vals.append(-F.log_softmax(logits[i,bounds[i]+j],dim=-1)[int(t)])
   n.append(torch.stack(vals).mean().item())
  N.append(np.asarray(n))
 return {'hidden':np.concatenate(H) if H else np.zeros((len(rows),0),np.float32),'logits':np.concatenate(L),'nll':np.concatenate(N)}

def base_gradients(model:Any,rows:Sequence[Mapping[str,Any]],layer:int,batch:int,pad:int,device:torch.device)->np.ndarray:
 module=v1._module_for_layer(model,layer);out=[]
 for p in model.parameters():p.requires_grad_(False)
 for st in range(0,len(rows),batch):
  rr=rows[st:st+batch];ids,mask,bounds,_=batch_tensors(rr,'base',pad,device);ar=torch.arange(len(rr),device=device);cap=[]
  def hook(_m,_i,o):
   h=o[0] if isinstance(o,tuple) else o;leaf=h.detach().requires_grad_(True);cap.append(leaf);return (leaf,)+o[1:] if isinstance(o,tuple) else leaf
  hd=module.register_forward_hook(hook)
  try:
   with torch.enable_grad():
    z=model(input_ids=ids,attention_mask=mask,use_cache=False).logits
    lo=torch.stack([z[i,bounds[i],int(r['target_id'])]-z[i,bounds[i],int(r['contrast_id'])] for i,r in enumerate(rr)])
    g=torch.autograd.grad(lo.sum(),cap[0])[0];out.append(g[ar,bounds].float().cpu().numpy())
  finally:hd.remove()
 return np.concatenate(out)

def logodds(logits:np.ndarray,rows:Sequence[Mapping[str,Any]])->np.ndarray:return np.asarray([logits[i,int(r['target_id'])]-logits[i,int(r['contrast_id'])] for i,r in enumerate(rows)],np.float64)
def non_target_kl(a:np.ndarray,b:np.ndarray,rows:Sequence[Mapping[str,Any]])->np.ndarray:return v1.non_target_kl(a,b,[{'answer_base_id':r['contrast_id'],'answer_cf_id':r['target_id']} for r in rows])
def subset_idx(rows:Sequence[Mapping[str,Any]],source:str,split:str)->np.ndarray:return np.asarray([i for i,r in enumerate(rows) if r['source']==source and r['split']==split],int)

def fit_basis(name:str,bh:np.ndarray,fh:np.ndarray,sh:np.ndarray,grad:np.ndarray,cfg:Mapping[str,Any],seed:int)->np.ndarray:
 rank=int(cfg['analysis']['rank']);delta=fh-bh;d=bh.shape[1]
 if name=='diffmean_caa':return v1.orthonormal_rows(delta.mean(0)[None],1)
 if name=='paired_delta_svd':return v1.orthonormal_rows(delta,rank)
 if name=='task_projection':return v1.linear_basis('task_projection',np.r_[bh,fh],bh,fh,rank,seed,cfg['analysis']['ridge_alpha'])
 if name=='leace':return v1.linear_basis('linear_erasure',np.r_[bh,fh],bh,fh,rank,seed,cfg['analysis']['ridge_alpha'])
 if name=='pca':return v1.orthonormal_rows(np.r_[bh,fh]-np.r_[bh,fh].mean(0),rank)
 if name=='random':
  q,_=np.linalg.qr(np.random.default_rng(seed).normal(size=(d,rank)));return q.T.astype(np.float32)
 if name=='reft_style_r1':return v1.orthonormal_rows(grad.mean(0)[None],1)
 if name=='supervised_skyline':
  # Closed-form symmetric behavior-gradient objective with the registered sham penalty.
  M=((delta.T@grad)+(grad.T@delta))/(2*max(1,len(delta)))
  nuisance=sh-bh
  M-=float(cfg['analysis']['nuisance_penalty'])*((nuisance.T@grad)+(grad.T@nuisance))/(2*max(1,len(nuisance)))
  vals,vecs=np.linalg.eigh((M+M.T)/2);order=np.argsort(vals)[::-1]
  keep=[i for i in order if vals[i]>float(cfg['analysis']['minimum_eigenvalue'])][:rank]
  return vecs[:,keep].T.astype(np.float32) if keep else np.zeros((0,d),np.float32)
 raise ValueError(name)
def project(delta:np.ndarray,basis:np.ndarray)->np.ndarray:return (delta@basis.T)@basis if len(basis) else np.zeros_like(delta)
def match_norm(x:np.ndarray,natural:np.ndarray,budget:float,eps:float)->np.ndarray:
 n=np.linalg.norm(x,axis=1);target=float(budget)*np.linalg.norm(natural,axis=1);return x*(target/np.maximum(n,eps))[:,None]

def public_patches(sae:PublicSAE,dev:tuple[np.ndarray,np.ndarray,np.ndarray],ev:tuple[np.ndarray,np.ndarray,np.ndarray],rank:int,device:torch.device)->tuple[np.ndarray,np.ndarray,float,float,int]:
 def enc(x):
  with torch.no_grad():return sae.encode(torch.from_numpy(np.asarray(x,np.float32)).to(device))
 db,df,ds=map(enc,dev);score=(df-db).mean(0).abs()*sae.Wdec.norm(dim=1);idx=torch.topk(score,min(rank,len(score))).indices
 eb,ef,es=map(enc,ev);actual=((ef-eb)[:,idx]@sae.Wdec[idx]).float().cpu().numpy();sham=((es-eb)[:,idx]@sae.Wdec[idx]).float().cpu().numpy()
 with torch.no_grad():
  x=torch.cat([db,df]);raw=torch.from_numpy(np.r_[dev[0],dev[1]].astype(np.float32)).to(device);rec=sae.decode(x);base=sae.norm(raw);fvu=float(((rec-base).pow(2).sum()/((base-base.mean(0)).pow(2).sum()+1e-8)).cpu())
  l0=float((x!=0).sum(1).float().mean().cpu())
 return actual,sham,1-fvu,l0,int(len(idx))


def synthetic(config:Path)->None:
 cfg=loadj(config);verify_freeze(config,cfg);out=ROOT/cfg['runtime']['output_root']/'synthetic';out.mkdir(parents=True,exist_ok=True)
 pc=cfg['positive_control'];rng=np.random.default_rng(cfg['seed']);n=int(pc['rows']);d=int(pc['hidden']);r=int(pc['rank']);u=np.eye(d)[:r];amp=rng.uniform(.5,1.5,(n,1));delta=amp*u[0]+rng.normal(0,.03,(n,d))@u.T@u;sham=rng.normal(0,.5,(n,d));sham-=sham@u.T@u;base=rng.normal(0,1,(n,d));w=u[0];full=delta@w
 def met(B):
  a=project(delta,B);s=project(sham,B);pe=a@w;se=s@w;rec=np.mean(pe/full);spec=np.mean((pe-se)/full);coll=np.mean(np.sum(a[:,r:]**2,1)/(np.sum(a*a,1)+1e-8));return {'recovery':float(rec),'specificity':float(spec),'collateral':float(coll)}
 ground=met(u);sky=met(v1.orthonormal_rows(w[None],r));q,_=np.linalg.qr(rng.normal(size=(d,r)));rand=met(q.T)
 ok=ground['recovery']>=pc['ground_recovery_min'] and ground['specificity']>=pc['ground_specificity_min'] and ground['collateral']<=pc['ground_collateral_max'] and sky['recovery']>=pc['skyline_recovery_min'] and sky['specificity']>=pc['skyline_specificity_min'] and abs(rand['specificity'])<=pc['random_specificity_max']
 rec={'schema_version':'joint_control_v3_synthetic','status':'PASS' if ok else 'FAIL','ground':ground,'supervised_skyline':sky,'random':rand}
 exjson(out/('PASS.json' if ok else 'FAIL.json'),rec);exjson(out/'result.json',rec)
 if not ok:raise RuntimeError('positive control failed')

def wait_gate(cfg:Mapping[str,Any],out:Path)->None:
 gate=ROOT/cfg['runtime']['output_root']/'synthetic'/'PASS.json';fail=gate.with_name('FAIL.json')
 while not gate.exists():
  if fail.exists():raise RuntimeError('blocked by positive control')
  atomjson(out/'WAITING.json',{'status':'WAITING_FOR_POSITIVE_CONTROL'});time.sleep(int(cfg['runtime']['gate_poll_seconds']))

def worker(config:Path,key:str,layer:int)->None:
 cfg=loadj(config);freeze_rec=verify_freeze(config,cfg);spec=model_spec(cfg,key)
 if layer not in spec['layers']:raise RuntimeError('unregistered layer')
 out=ROOT/cfg['runtime']['output_root']/'shards'/f'{key}_layer{layer}';out.mkdir(parents=True,exist_ok=False);wait_gate(cfg,out)
 seedall(stable(cfg['seed'],key,layer));device=torch.device('cuda:0');rows=rows_for(cfg,key)
 from transformers import AutoModelForCausalLM
 model=AutoModelForCausalLM.from_pretrained(spec['name'],revision=spec['revision'],local_files_only=True,torch_dtype=torch.float32).to(device).eval()
 for p in model.parameters():p.requires_grad_(False)
 pad=model.config.pad_token_id
 if pad is None:
  from transformers import AutoTokenizer
  tok=AutoTokenizer.from_pretrained(spec['name'],revision=spec['revision'],local_files_only=True);pad=tok.pad_token_id if tok.pad_token_id is not None else tok.eos_token_id
 batch=int(spec['batch_size'])
 # Architecture-specific technical hook QA is label-blind.
 smoke=rows[:1];z=np.zeros((1,model.config.hidden_size),np.float32);a=run_panel(model,smoke,'base',layer,1,pad,device,None);b=run_panel(model,smoke,'base',layer,1,pad,device,z);nz=z.copy();nz[0,0]=1e-3;c=run_panel(model,smoke,'base',layer,1,pad,device,nz)
 if not np.array_equal(a['logits'],b['logits']) or not np.isfinite(c['logits']).all() or np.array_equal(a['logits'],c['logits']):raise RuntimeError('hook QA failed')
 atomjson(out/'HOOK_QA.json',{'zero_patch_exact':True,'nonzero_finite_change':True})
 base=run_panel(model,rows,'base',layer,batch,pad,device);full=run_panel(model,rows,'full',layer,batch,pad,device);sham=run_panel(model,rows,'sham',layer,batch,pad,device)
 devall=np.r_[subset_idx(rows,'WIKI_A','development'),subset_idx(rows,'WIKI_B','development')];grad=np.zeros_like(base['hidden']);grad[devall]=base_gradients(model,[rows[i] for i in devall],layer,batch,pad,device)
 saes=load_public_saes(cfg,key,layer,device);records=[];eps=float(cfg['analysis']['epsilon']);methods=list(cfg['methods'])+[x for x in saes if x!='public_sae_primary']
 for fit_source,eval_source in [('WIKI_A','WIKI_B'),('WIKI_B','WIKI_A')]:
  di=subset_idx(rows,fit_source,'development');ei=subset_idx(rows,eval_source,'test');rr=[rows[i] for i in ei];natural=full['hidden'][ei]-base['hidden'][ei];shamd=sham['hidden'][ei]-base['hidden'][ei]
  full_eff=logodds(full['logits'][ei],rr)-logodds(base['logits'][ei],rr);sham_eff=logodds(sham['logits'][ei],rr)-logodds(base['logits'][ei],rr)
  for method in methods:
   if method.startswith('public_sae') or method.startswith('saebench_'):
    sae=saes[method];actual,spatch,proxy,l0,rank=public_patches(sae,(base['hidden'][di],full['hidden'][di],sham['hidden'][di]),(base['hidden'][ei],full['hidden'][ei],sham['hidden'][ei]),int(cfg['analysis']['rank']),device);proxy_name='reconstruction_quality'
   else:
    B=fit_basis(method,base['hidden'][di],full['hidden'][di],sham['hidden'][di],grad[di],cfg,stable(cfg['seed'],key,layer,fit_source,method));actual=project(natural,B);spatch=project(shamd,B);rank=len(B);l0=float(rank);proxy=float(np.sum(actual*actual)/max(np.sum(natural*natural),eps));proxy_name='captured_variance'
   for budget in cfg['budgets']:
    ap=match_norm(actual,natural,budget,eps);ssp=match_norm(spatch,natural,budget,eps)
    patched=run_panel(model,rr,'base',layer,batch,pad,device,ap,False);shpatched=run_panel(model,rr,'base',layer,batch,pad,device,ssp,False);removed=run_panel(model,rr,'full',layer,batch,pad,device,-ap,False)
    # Apply each row's patch to a cyclically paired unrelated document.
    cr=rr[1:]+rr[:1];collbase=run_panel(model,cr,'base',layer,batch,pad,device,None,False);collpatch=run_panel(model,cr,'base',layer,batch,pad,device,ap,False)
    plo=logodds(patched['logits'],rr)-logodds(base['logits'][ei],rr);slo=logodds(shpatched['logits'],rr)-logodds(base['logits'][ei],rr);elo=logodds(removed['logits'],rr)-logodds(full['logits'][ei],rr)
    eligible=full_eff>float(cfg['analysis']['minimum_full_effect']);den=np.where(np.abs(full_eff)>eps,full_eff,np.nan)
    recov=np.where(eligible,plo/den,np.nan);specific=np.where(eligible,(plo-slo)/den,np.nan);coll=non_target_kl(base['logits'][ei],patched['logits'],rr);contden=base['nll'][ei]-full['nll'][ei];contre=np.where(np.abs(contden)>eps,(base['nll'][ei]-patched['nll'])/contden,np.nan);unrel=collpatch['nll']-collbase['nll']
    for j,r in enumerate(rr):records.append({'schema_version':'joint_control_v3_component_metric','model':key,'model_family':key,'layer':layer,'stage':stage(spec,layer),'fit_source':fit_source,'eval_source':eval_source,'component_id':r['component_id'],'component_block':r['component_block'],'method':method,'budget':float(budget),'rank':rank,'proxy_name':proxy_name,'proxy_value':proxy,'sparsity':l0,'full_effect':float(full_eff[j]),'natural_sham_effect':float(sham_eff[j]),'behavior_eligible':bool(eligible[j]),'behavioral_recovery':float(recov[j]) if np.isfinite(recov[j]) else None,'signed_sham_specificity':float(specific[j]) if np.isfinite(specific[j]) else None,'collateral_kl':float(coll[j]),'continuation_recovery':float(contre[j]) if np.isfinite(contre[j]) else None,'unrelated_continuation_damage':float(unrel[j]),'necessity_effect':float(elo[j]),'actual_patch_norm_ratio':float(np.linalg.norm(ap[j])/max(np.linalg.norm(natural[j]),eps))})
 writejl(out/'metrics.jsonl',records);complete={'schema_version':'joint_control_v3_worker_complete','status':'COMPLETE','model':key,'layer':layer,'rows':len(records),'freeze_sha256':sha(ROOT/cfg['runtime']['freeze']),'hook_qa_sha256':sha(out/'HOOK_QA.json'),'metrics_sha256':sha(out/'metrics.jsonl'),'runtime':{'device':str(device),'gpu':torch.cuda.get_device_name(0),'gpu_uuid':'GPU-'+str(torch.cuda.get_device_properties(0).uuid),'torch':torch.__version__}}
 exjson(out/'COMPLETE.json',complete)

def ci(vals:Sequence[float],blocks:Sequence[str],draws:int,seed:int)->list[float]|None:return v2.block_interval(vals,blocks,draws,seed)
def aggregate(config:Path)->None:
 cfg=loadj(config);verify_freeze(config,cfg);root=ROOT/cfg['runtime']['output_root'];agg=root/'aggregate';agg.mkdir(parents=True,exist_ok=False)
 expected=[f"{m['key']}_layer{l}" for m in cfg['models'] for l in m['layers']]
 while not all((root/'shards'/x/'COMPLETE.json').exists() for x in expected):time.sleep(int(cfg['runtime']['gate_poll_seconds']))
 rows=[]
 for x in expected:
  c=loadj(root/'shards'/x/'COMPLETE.json');p=root/'shards'/x/'metrics.jsonl'
  if sha(p)!=c['metrics_sha256']:raise RuntimeError('worker drift')
  rows+=readjl(p)
 groups={}
 for r in rows:groups.setdefault((r['method'],r['budget'],r['model'],r['layer'],r['fit_source'],r['eval_source']),[]).append(r)
 summaries=[];a=cfg['analysis']
 for key,rs in sorted(groups.items()):
  elig=np.mean([r['behavior_eligible'] for r in rs]);blocks=[r['component_block'] for r in rs]
  def C(n):return ci([float(r[n]) for r in rs if r[n] is not None],[blocks[i] for i,r in enumerate(rs) if r[n] is not None],a['bootstrap_draws'],stable(cfg['seed'],*key,n))
  rc,sc,kc=C('behavioral_recovery'),C('signed_sham_specificity'),C('collateral_kl')
  sham_ratio=[abs(float(r['natural_sham_effect']))/max(abs(float(r['full_effect'])),float(a['epsilon'])) for r in rs]
  shci=ci(sham_ratio,blocks,a['bootstrap_draws'],stable(cfg['seed'],*key,'natural_sham_fraction'))
  sham_ok=shci is not None and shci[1]<=a['maximum_sham_fraction'] and shci[2]<a['maximum_sham_fraction_ci']
  passed=elig>=a['minimum_effect_eligibility'] and sham_ok and rc is not None and rc[0]>a['minimum_recovery_ci_lower'] and sc is not None and sc[0]>a['minimum_specificity_ci_lower'] and kc is not None and kc[2]<a['maximum_collateral_ci_upper']
  summaries.append({'method':key[0],'budget':key[1],'model':key[2],'layer':key[3],'fit_source':key[4],'eval_source':key[5],'eligibility':elig,'natural_sham_fraction_ci':shci,'recovery_ci':rc,'specificity_ci':sc,'collateral_ci':kc,'passes':passed})
 decisions=[]
 for method in sorted({r['method'] for r in rows}):
  for budget in cfg['budgets']:
   for stg in ['early','middle','late']:
    ms=[]
    for m in cfg['models']:
     layer_pass=[s for s in summaries if s['method']==method and s['budget']==budget and s['model']==m['key'] and stage(m,s['layer'])==stg]
     if {s['eval_source'] for s in layer_pass if s['passes']}==set(cfg['task']['sources']):ms.append(m['key'])
    decisions.append({'method':method,'budget':budget,'stage':stg,'passing_model_families':ms,'passes':len(ms)>=a['minimum_replicating_model_families']})
 result={'schema_version':'joint_control_v3_result','status':'PROSPECTIVE_COMPLETE_REQUIRES_CLAIM_REVIEW','within_corpus_transfer':True,'cross_domain_replication':False,'metric_rows':len(rows),'summaries':summaries,'method_decisions':decisions,'passing_method_decisions':sum(x['passes'] for x in decisions),'training_authorized':False}
 exjson(agg/'result.json',result);exjson(agg/'COMPLETE.json',{'status':'COMPLETE','result_sha256':sha(agg/'result.json'),'freeze_sha256':sha(ROOT/cfg['runtime']['freeze'])})

def main()->None:
 p=argparse.ArgumentParser();sub=p.add_subparsers(dest='cmd',required=True)
 for n in ['prepare','preflight','freeze','synthetic','aggregate']:
  q=sub.add_parser(n);q.add_argument('--config',type=Path,default=DEFAULT)
 q=sub.add_parser('worker');q.add_argument('--config',type=Path,default=DEFAULT);q.add_argument('--model',required=True);q.add_argument('--layer',type=int,required=True)
 q=p.parse_args()
 if q.cmd=='prepare':prepare(q.config)
 elif q.cmd=='preflight':preflight(q.config)
 elif q.cmd=='freeze':freeze(q.config)
 elif q.cmd=='synthetic':synthetic(q.config)
 elif q.cmd=='worker':worker(q.config,q.model,q.layer)
 else:aggregate(q.config)
if __name__=='__main__':main()
