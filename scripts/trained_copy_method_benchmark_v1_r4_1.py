#!/usr/bin/env python3
from __future__ import annotations

import argparse, dataclasses, hashlib, json, math, os, random, shutil, signal, subprocess, sys, time
from pathlib import Path
from typing import Any, Mapping, Sequence

import numpy as np
import torch
import torch.nn.functional as F

sys.path.insert(0, str(Path(__file__).resolve().parent))
import capacity_external_validity_v1_r5 as r5

ROOT=Path(os.environ.get('MSAE_ROOT',Path(__file__).resolve().parents[1])).resolve()
CFG_PATH=ROOT/'configs/trained_copy_method_benchmark_v1_r4_1/run.json'
PLAN=ROOT/'PLAN_TRAINED_COPY_METHOD_BENCHMARK_V1_R4_1.md'
SCRIPT=Path(__file__).resolve()
TEST=ROOT/'tests/test_trained_copy_method_benchmark_v1_r4_1.py'
LAUNCHER=ROOT/'scripts/launch_trained_copy_method_benchmark_v1_r4_1_tmux.sh'

def loadj(p:Path)->Any:return json.loads(p.read_text())
def cfg()->dict[str,Any]:return loadj(CFG_PATH)
def rp(c:Mapping[str,Any],k:str)->Path:return ROOT/c['runtime'][k]
def canon(x:Any)->bytes:return json.dumps(x,sort_keys=True,separators=(',',':'),allow_nan=False).encode()
def sha(p:Path)->str:
 h=hashlib.sha256()
 with p.open('rb') as f:
  for b in iter(lambda:f.read(1<<20),b''):h.update(b)
 return h.hexdigest()
def seed32(*x:Any)->int:return int.from_bytes(hashlib.sha256(canon(x)).digest()[:8],'big')%(2**31-1)
def rng(*x:Any)->np.random.Generator:return np.random.default_rng(seed32(*x))
def atomic_json(p:Path,x:Any)->None:
 p.parent.mkdir(parents=True,exist_ok=True);data=json.dumps(x,indent=2,sort_keys=True,allow_nan=False).encode()+b'\n';tmp=p.parent/f'.{p.name}.{os.getpid()}.{time.time_ns()}'
 fd=os.open(tmp,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o444)
 with os.fdopen(fd,'wb') as f:f.write(data);f.flush();os.fsync(f.fileno())
 os.replace(tmp,p);fd=os.open(p.parent,os.O_RDONLY);os.fsync(fd);os.close(fd)
def create_json(p:Path,x:Any)->None:
 if p.exists():raise FileExistsError(p)
 atomic_json(p,x)
def event(prov:Path,index:int,state:str,**kw:Any)->None:create_json(prov/'events'/f'{index:03d}_{state}.json',{'index':index,'state':state,'time_ns':time.time_ns(),**kw})
def method_table_hash(c:Mapping[str,Any])->str:return hashlib.sha256(canon(c['methods'])).hexdigest()

def parse_proc_stat_ppid(text:str)->int:
 # proc_pid_stat(5): PID, parenthesized comm (which may contain spaces or ')'), state, then PPID.
 close=text.rfind(')')
 if close<0:raise RuntimeError('malformed proc stat: missing comm terminator')
 prefix=text[:close+1];suffix=text[close+1:].strip().split()
 if '(' not in prefix or len(suffix)<2 or len(suffix[0])!=1:raise RuntimeError('malformed proc stat fields')
 try:pid=int(prefix.split('(',1)[0].strip());ppid=int(suffix[1])
 except ValueError as e:raise RuntimeError('malformed proc stat integer') from e
 if pid<=0 or ppid<0:raise RuntimeError('invalid proc stat pid')
 return ppid

def recovery_lineage(c:Mapping[str,Any])->dict[str,Any]:
 rec=c.get('recovery',{});pp=ROOT/rec.get('r4_failure_preservation_path','');ff=ROOT/rec.get('r4_freeze_path','')
 if not pp.is_file() or sha(pp)!=rec.get('r4_failure_preservation_sha256'):raise RuntimeError('R4 failure preservation drift')
 if not ff.is_file() or sha(ff)!=rec.get('r4_freeze_sha256'):raise RuntimeError('R4 freeze drift')
 x=loadj(pp);term=x.get('formal_terminal',{})
 if x.get('no_retry_under_r4_namespace') is not True or x.get('scientific_payload_opened') is not False or term.get('status')!=rec.get('required_terminal_status') or term.get('panel_accessed') is not False or term.get('confirmation_opened') is not False or term.get('no_retry_authorized') is not True:raise RuntimeError('R4 failure preservation semantics drift')
 if rec.get('payloads_must_equal_r4') is not True or rec.get('scientific_changes') is not False:raise RuntimeError('R4.1 recovery scope drift')
 return {'preservation_sha256':sha(pp),'r4_freeze_sha256':sha(ff),'r4_payloads':loadj(ff)['payloads']}

def rows_jsonl_sha256(rows:Sequence[Mapping[str,Any]])->str:
 h=hashlib.sha256()
 for row in rows:h.update(json.dumps(row,sort_keys=True,separators=(',',':')).encode()+b'\n')
 return h.hexdigest()

def validate_config(c:Mapping[str,Any])->None:
 if not TEST.is_file() or not LAUNCHER.is_file():raise RuntimeError('candidate executable inventory missing')
 if c['scope']!={'synthetic_only':True,'counterfactual_donor_required':True,'pretrained_model':False,'natural_language_claim':False,'k2_evaluated':False,'copy_model_retraining':False}:raise RuntimeError('scope drift')
 if c['methods']['global_ranks']!=[4,8,16,32,64] or c['methods']['conditioned_ranks']!=[4,8,16,32]:raise RuntimeError('rank drift')
 pools=[set(c['panels'][s]['offsets']) for s in ('fit','development','confirmation')]
 if pools[0]!=set(range(1,22)) or pools[1]!=set(range(22,27)) or pools[2]!=set(range(27,32)) or any(pools[i]&pools[j] for i in range(3) for j in range(i)):raise RuntimeError('offset partition drift')
 if c['bootstrap']['draws']!=1000 or c['model']['seeds']!=[5101,5102,5103]:raise RuntimeError('bootstrap/model drift')
 if c['panels']['development']['blocks']!=32 or c['panels']['confirmation']['blocks']!=32 or c['panels']['minimum_eval_total']!=248:raise RuntimeError('R2 evaluation support drift')
 r5_source=ROOT/c['r5']['source_path']
 if Path(r5.__file__).resolve()!=r5_source.resolve() or not r5_source.is_file() or sha(r5_source)!=c['r5']['source_sha256']:raise RuntimeError('R5 imported source drift')
 preservation=loadj(ROOT/c['r5']['preservation_path']);matches=[a for a in preservation.get('artifacts',[]) if a.get('path')==c['r5']['source_path']]
 if len(matches)!=1 or matches[0].get('sha256')!=c['r5']['source_sha256'] or matches[0].get('bytes')!=r5_source.stat().st_size:raise RuntimeError('R5 preservation inventory drift')
 for sd,rec in c['r5']['checkpoints'].items():
  p=ROOT/rec['path']
  if not p.is_file() or sha(p)!=rec['sha256']:raise RuntimeError(f'checkpoint lineage {sd}')
 for key in ('config','freeze','preservation'):
  p=ROOT/c['r5'][f'{key}_path']
  if not p.is_file() or sha(p)!=c['r5'][f'{key}_sha256']:raise RuntimeError(f'R5 {key} drift')
 recovery_lineage(c)

def panel_rows(stage:str,c:Mapping[str,Any],avoid_sham:set[tuple[int,int,int]]|None=None)->list[dict[str,Any]]:
 pc=c['panels'][stage];pool=list(pc['offsets']);avoid=set(avoid_sham or set());used_sham:set[tuple[int,int,int]]=set();rows=[]
 for block in range(pc['blocks']):
  for within in range(pc['rows_per_block']):
   ix=block*pc['rows_per_block']+within
   if stage=='fit':
    target=within;query=(target+block)%c['model']['slots'];replicate=block//c['model']['slots']
   else:
    group=block%4;replicate=block//4;query=within;target=8*group+(within+replicate)%8
   off=pool[(target+3*query+replicate)%len(pool)] if stage=='fit' else pool[query%len(pool)];contrast=(target+off)%c['model']['vocab'];choices=[]
   for j in range(1,c['model']['vocab']):
    sham=(target+off+j)%c['model']['vocab'];tup=(query,contrast,sham)
    if sham not in {target,contrast} and tup not in avoid and tup not in used_sham:choices.append((j,sham,tup))
   if not choices:raise RuntimeError(f'no sham choice {stage} {ix}')
   _,sham,sham_tuple=choices[0];used_sham.add(sham_tuple);rs=seed32('trained_copy_methods_r4',stage,pc['seed'],ix);g=rng('rows',rs);vals=g.integers(0,c['model']['vocab'],size=c['model']['slots']).tolist();vals[query]=target;cor=vals.copy();cor[query]=contrast;sv=vals.copy();sv[query]=sham
   rows.append({'row_id':f'tcm-r4-{stage}-{ix:05d}-{rs:08x}','row_seed':rs,'stage':stage,'block':block,'query':query,'target':target,'contrast':contrast,'sham':sham,'offset':off,'clean_values':vals,'corrupt_values':cor,'sham_values':sv})
 return rows

def panel_set(c:Mapping[str,Any])->dict[str,list[dict[str,Any]]]:
 out={};avoid:set[tuple[int,int,int]]=set()
 for st in ('fit','development','confirmation'):
  out[st]=panel_rows(st,c,avoid);avoid|={(r['query'],r['contrast'],r['sham']) for r in out[st]}
 return out
def panel_audit(ps:Mapping[str,Sequence[Mapping[str,Any]]],c:Mapping[str,Any])->dict[str,Any]:
 ids=[];seeds=[];main=[];sh=[];out={}
 for st,rows in ps.items():
  mt=[(r['query'],r['target'],r['contrast']) for r in rows];sht=[(r['query'],r['contrast'],r['sham']) for r in rows]
  if any((r['contrast']-r['target'])%c['model']['vocab']!=r['offset'] for r in rows):raise RuntimeError(f'offset encoding {st}')
  offsets=sorted(set(r['offset'] for r in rows))
  if offsets!=sorted(c['panels'][st]['offsets']):raise RuntimeError(f'offset coverage {st}')
  if len(mt)!=len(set(mt)):raise RuntimeError(f'duplicate main tuple {st}')
  if st!='fit':
   from collections import Counter
   tq=Counter((r['target'],r['query']) for r in rows)
   if set(Counter(r['target'] for r in rows).values())!={8} or set(Counter(r['query'] for r in rows).values())!={32} or len(tq)!=256 or set(tq.values())!={1}:raise RuntimeError(f'counterbalance {st}')
  out[st]={'rows':len(rows),'unique_main_tuples':len(set(mt)),'unique_sham_tuples':len(set(sht)),'max_main_tuple_contribution':max(mt.count(x) for x in set(mt)),'max_sham_tuple_contribution':max(sht.count(x) for x in set(sht)),'target_query_pairs':len(set((r['target'],r['query']) for r in rows)),'offsets_used':offsets,'per_block_unique_main':{str(b):len(set(mt[i] for i,r in enumerate(rows) if r['block']==b)) for b in range(c['panels'][st]['blocks'])},'per_block_unique_sham':{str(b):len(set(sht[i] for i,r in enumerate(rows) if r['block']==b)) for b in range(c['panels'][st]['blocks'])},'main_tuple_sha256':hashlib.sha256(canon(sorted(mt))).hexdigest(),'sham_tuple_sha256':hashlib.sha256(canon(sorted(set(sht)))).hexdigest()}
  ids.append(set(r['row_id'] for r in rows));seeds.append(set(r['row_seed'] for r in rows));main.append(set(mt));sh.append(set(sht))
 for xs,name in [(ids,'id'),(seeds,'seed'),(main,'main'),(sh,'sham')]:
  if any(xs[i]&xs[j] for i in range(3) for j in range(i)):raise RuntimeError(f'cross-panel {name} overlap')
 r5c=loadj(ROOT/c['r5']['config_path']);old=[r for st in ('train','development','confirmation') for r in r5.external_rows(st,r5c)];old_ids={r['row_id'] for r in old};old_seeds={r['row_seed'] for r in old};new_ids=set().union(*ids);new_seeds=set().union(*seeds)
 if new_ids&old_ids or new_seeds&old_seeds:raise RuntimeError('R5 row identity overlap')
 out['cross_r5']={'row_id_overlap':0,'row_seed_overlap':0,'r5_rows_reconstructed_from_frozen_generator':len(old)}
 return out
def write_jsonl(p:Path,rows:Sequence[Mapping[str,Any]])->None:
 if p.exists():raise FileExistsError(p)
 p.parent.mkdir(parents=True,exist_ok=True);fd=os.open(p,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o444)
 with os.fdopen(fd,'w') as f:
  for r in rows:f.write(json.dumps(r,sort_keys=True,separators=(',',':'))+'\n')
  f.flush();os.fsync(f.fileno())
def read_jsonl(p:Path)->list[dict[str,Any]]:
 with p.open() as f:return [json.loads(x) for x in f]

class TopKSAE(torch.nn.Module):
 def __init__(self,d:int,width:int,k:int,seed:int,device:torch.device):
  super().__init__();g=torch.Generator(device=device).manual_seed(seed);self.encoder=torch.nn.Parameter(torch.randn(d,width,generator=g,device=device)/math.sqrt(d));self.decoder=torch.nn.Parameter(torch.randn(width,d,generator=g,device=device)/math.sqrt(width));self.bias=torch.nn.Parameter(torch.zeros(d,device=device));self.k=k
 def encode(self,x:torch.Tensor)->torch.Tensor:
  z=F.relu((x-self.bias)@self.encoder);v,i=torch.topk(z,self.k,dim=1);return torch.zeros_like(z).scatter(1,i,v)
 def decode(self,z:torch.Tensor)->torch.Tensor:return z@self.decoder+self.bias
 def forward(self,x:torch.Tensor)->torch.Tensor:return self.decode(self.encode(x))

@dataclasses.dataclass
class Method:
 name:str;family:str;kind:str;payload:Any;seed:int|None=None;rank:int|None=None;parameters:int=0;comparison_class:str='donor_compression'

def canonical_svd(x:np.ndarray)->tuple[np.ndarray,np.ndarray,np.ndarray]:return r5.svd_canonical(x.astype(np.float64),False)
def oracle_rank_order_valid(x:np.ndarray,basis:np.ndarray,ranks:Sequence[int])->bool:
 _,s,_=canonical_svd(x);total=float(np.sum(x.astype(np.float64)**2));observed=[float(np.sum((x@basis[:k].T)**2)) for k in ranks];optimal=[float(np.sum(s[:k]**2)) for k in ranks];return bool(all(observed[i]<=observed[i+1]+1e-8 for i in range(len(observed)-1)) and all(np.isclose(a,b,rtol=1e-6,atol=1e-7*max(total,1)) for a,b in zip(observed,optimal)))
def train_generic(model:torch.nn.Module,x:torch.Tensor,y:torch.Tensor,t:torch.Tensor,sc:Mapping[str,Any],seed:int)->dict[str,Any]:return r5.train_model(model,x,y,t,sc,seed)
def stable_top(scores:torch.Tensor,k:int)->torch.Tensor:
 a=scores.detach().cpu().numpy();order=np.lexsort((np.arange(len(a)),-a));return torch.tensor(order[:k],dtype=torch.long,device=scores.device)

def fit_unpaired_ambient_basis(states:torch.Tensor)->tuple[torch.Tensor,np.ndarray]:
 mu=states.mean(0);_,_,basis=canonical_svd((states-mu).detach().cpu().numpy());return mu,basis
def select_unpaired_sae_features(codes:torch.Tensor,k:int)->torch.Tensor:return stable_top(codes.var(0,unbiased=False),k)
def select_paired_sae_features(clean_codes:torch.Tensor,corrupt_codes:torch.Tensor,k:int)->torch.Tensor:return stable_top(torch.mean(torch.abs(clean_codes-corrupt_codes),0),k)

def empirical_jacobian_diagnostics(model:r5.TargetMLP,x:torch.Tensor,targets:torch.Tensor,target_count:int,device:torch.device)->dict[str,Any]:
 ranks=[];jacs=[]
 for tv in range(target_count):
  ix=int(torch.nonzero(targets==tv,as_tuple=False)[0].item());sample=x[ix].detach().requires_grad_(True);target=torch.tensor([tv],device=device);jac=torch.autograd.functional.jacobian(lambda q:model(q[None,:],target)[0],sample,vectorize=True).detach().cpu().numpy();jacs.append(jac);ranks.append(int(np.linalg.matrix_rank(jac,tol=1e-5)))
 return {'empirical_jacobian_ranks':ranks,'empirical_jacobian_union_rank':int(np.linalg.matrix_rank(np.concatenate(jacs,axis=1),tol=1e-5))}

def context(model:r5.CopyTransformer,rows:Sequence[Mapping[str,Any]],device:torch.device)->dict[str,torch.Tensor]:
 clean,q,t=r5.rows_tensors(rows,device,'clean_values');cor,_,co=r5.rows_tensors(rows,device,'corrupt_values');sh,_,_=r5.rows_tensors(rows,device,'sham_values')
 with torch.no_grad():oc=model(clean,q);orr=model(cor,q);os=model(sh,q)
 return {'clean':oc['head'],'corrupt':orr['head'],'sham':os['head'],'delta':oc['head']-orr['head'],'sham_delta':os['head']-orr['head'],'logits_clean':oc['logits'],'logits_corrupt':orr['logits'],'weights_clean':oc['weights'],'weights_corrupt':orr['weights'],'values_clean':oc['values'],'values_corrupt':orr['values'],'target':t,'contrast':co,'query':q}

def fit_methods(model:r5.CopyTransformer,rows:Sequence[Mapping[str,Any]],c:Mapping[str,Any],model_seed:int,device:torch.device,out:Path)->tuple[list[Method],dict[str,Any]]:
 out.mkdir(parents=True,exist_ok=False);z=context(model,rows,device);d=z['delta'];t=z['target'];D=d.shape[1];m=[];fits={};classes=c['methods']['information_contracts']
 m.extend([Method('exact_head_delta','exact_head_delta','exact',None,comparison_class='donor_compression'),Method('identity_full64','identity_full64','identity',None,rank=64,comparison_class='donor_compression')])
 _,_,vh=canonical_svd(d.detach().cpu().numpy())
 for k in c['methods']['global_ranks']:
  P=(vh[:k].T@vh[:k]).astype(np.float32);m.append(Method(f'output_oracle_rank{k}',f'output_oracle_rank{k}','matrix',torch.tensor(P,device=device),rank=k,parameters=D*k));
 states=torch.cat([z['clean'],z['corrupt'],z['sham']],0);_mu,vha=fit_unpaired_ambient_basis(states)
 for k in c['methods']['global_ranks']:
  P=(vha[:k].T@vha[:k]).astype(np.float32);m.append(Method(f'ambient_pca_rank{k}',f'ambient_pca_rank{k}','matrix',torch.tensor(P,device=device),rank=k,parameters=D*k))
 for k in c['methods']['global_ranks']:
  q=r5.qr_canonical(rng('random',c['methods']['random_seed'],model_seed,k).normal(size=(D,D)))[:,:k];P=torch.tensor((q@q.T).astype(np.float32),device=device);m.append(Method(f'random_rank{k}',f'random_rank{k}','matrix',P,rank=k,comparison_class='negative_control'))
 m.append(Method('readout_task_projection','readout_task_projection','readout',None,comparison_class='task_aware'))
 means=torch.stack([d[t==v].mean(0) for v in range(c['model']['vocab'])]);m.append(Method('target_mean_delta','target_mean_delta','target_mean',means,parameters=c['model']['vocab']*D,comparison_class='label_mean_no_donor'))
 rg=rng('perm',c['methods']['permutation_seed'],model_seed);xp=d.detach().cpu().numpy().copy();tn=t.detach().cpu().numpy()
 for v in range(c['model']['vocab']):
  ix=np.flatnonzero(tn==v);xp[ix]=xp[rg.permutation(ix)]
 W=np.linalg.pinv(xp.astype(np.float64),rcond=c['methods']['svd_rtol'])@d.detach().cpu().numpy().astype(np.float64);m.append(Method('within_target_permutation','within_target_permutation','matrix',torch.tensor(W.astype(np.float32),device=device),rank=int(np.linalg.matrix_rank(W)),parameters=D*D,comparison_class='negative_control'))
 m.append(Method('zero','zero','zero',None,comparison_class='negative_control'))
 xt=d.detach();yt=d.detach();tt=t.detach()
 for family,cls,ranks in [('paired_linear',r5.FactorLinear,c['methods']['global_ranks']),('target_linear',r5.TargetLinear,c['methods']['conditioned_ranks']),('target_nonlinear',r5.TargetMLP,c['methods']['conditioned_ranks'])]:
  sc=c['methods'][family]
  for k in ranks:
   for sd in sc['seeds']:
    mdl=cls(D,k,sd,device) if family=='paired_linear' else (cls(D,k,c['model']['vocab'],sd,device) if family=='target_linear' else cls(D,k,c['model']['vocab'],sc['hidden'],sd,device))
    rec=train_generic(mdl,xt,yt,tt,sc,seed32(model_seed,sd,k));extra={}
    if family=='paired_linear':extra={'effective_rank':int(np.linalg.matrix_rank((mdl.u@mdl.v).detach().cpu().numpy()))}
    elif family=='target_linear':
     mats=torch.bmm(mdl.u,mdl.v).detach().cpu().numpy();extra={'per_target_ranks':[int(np.linalg.matrix_rank(a)) for a in mats],'union_rank':int(np.linalg.matrix_rank(np.concatenate(mats,axis=0)))}
    else:
     extra=empirical_jacobian_diagnostics(mdl,xt,tt,c['model']['vocab'],device)
    name=f'{family}_rank{k}_seed{sd}';p=out/f'{name}.pt';torch.save({'state_dict':mdl.state_dict(),'model_seed':model_seed,'method_seed':sd,'rank':k,'config':sc,'method_table_sha256':method_table_hash(c),'diagnostics':extra},p);fits[name]={**rec,**extra,'sha256':sha(p)};m.append(Method(name,f'{family}_rank{k}',family,mdl,sd,k,rec['parameters'],classes[family]['class']))
 sc=c['methods']['sae'];sae_states=states.detach()
 for sd in sc['seeds']:
  sae=TopKSAE(D,sc['width'],sc['topk'],sd,device);opt=torch.optim.Adam(sae.parameters(),lr=sc['learning_rate']);g=torch.Generator(device=device).manual_seed(seed32(model_seed,sd,'sae'));losses=[]
  for step in range(sc['steps']):
   ix=torch.randint(0,len(sae_states),(sc['batch_size'],),generator=g,device=device);loss=F.mse_loss(sae(sae_states[ix]),sae_states[ix]);
   if not torch.isfinite(loss):raise FloatingPointError('SAE nonfinite')
   opt.zero_grad(set_to_none=True);loss.backward();opt.step()
   if step in {0,sc['steps']-1}:losses.append(float(loss.detach().cpu()))
  with torch.no_grad():
   codes=sae.encode(sae_states);un=select_unpaired_sae_features(codes,sc['selected_features']);paired=select_paired_sae_features(sae.encode(z['clean']),sae.encode(z['corrupt']),sc['selected_features']);full_fit_reconstruction_loss=float(F.mse_loss(sae(sae_states),sae_states).cpu());zc=sae.encode(z['corrupt']);base=sae.decode(zc);delta_norms={}
   for label,sel in [('unpaired',un),('paired',paired)]:
    za=zc.clone();za[:,sel]=sae.encode(z['clean'])[:,sel];delta_norms[label]=float(torch.linalg.vector_norm(sae.decode(za)-base,dim=1).mean().cpu())
  p=out/f'topk_sae_seed{sd}.pt';torch.save({'state_dict':sae.state_dict(),'model_seed':model_seed,'method_seed':sd,'config':sc,'unpaired_selected':un.cpu().tolist(),'paired_selected':paired.cpu().tolist(),'method_table_sha256':method_table_hash(c)},p);fits[f'topk_sae_seed{sd}']={'initial_loss':losses[0],'final_loss':losses[-1],'full_fit_reconstruction_loss':full_fit_reconstruction_loss,'mean_decoded_delta_norm':delta_norms,'sha256':sha(p),'unpaired_selected':un.cpu().tolist(),'paired_selected':paired.cpu().tolist()};params=sum(x.numel() for x in sae.parameters());m.extend([Method(f'topk_sae_unpaired_selector_seed{sd}','topk_sae_unpaired_selector','sae',(sae,un),sd,parameters=params),Method(f'topk_sae_paired_selector_seed{sd}','topk_sae_paired_selector','sae',(sae,paired),sd,parameters=params,comparison_class='paired_donor_compression')])
 np.savez(out/'nonlearned.npz',oracle_basis=vh,ambient_basis=vha,target_means=means.detach().cpu().numpy(),permutation_W=W);fits['nonlearned_sha256']=sha(out/'nonlearned.npz')
 return m,{'model_seed':model_seed,'method_table_sha256':method_table_hash(c),'fits':fits,'method_inventory':[{'name':x.name,'family':x.family,'seed':x.seed,'rank':x.rank,'parameters':x.parameters,'comparison_class':x.comparison_class} for x in m]}

def predict(method:Method,z:Mapping[str,torch.Tensor],model:r5.CopyTransformer)->tuple[torch.Tensor,torch.Tensor]:
 d,ds,t=z['delta'],z['sham_delta'],z['target']
 if method.kind in {'exact','identity'}:return d,ds
 if method.kind=='matrix':return d@method.payload,ds@method.payload
 if method.kind in {'paired_linear','target_linear','target_nonlinear'}:return method.payload(d,t),method.payload(ds,t)
 if method.kind=='target_mean':q=method.payload[t];return q,q.clone()
 if method.kind=='zero':return torch.zeros_like(d),torch.zeros_like(ds)
 if method.kind=='readout':
  W=model.readout.weight;out=[];sh=[]
  for i in range(len(d)):
   B=torch.stack([W[t[i]],W[z['contrast'][i]]],1);Q=torch.linalg.qr(B,mode='reduced').Q;P=Q@Q.T;out.append(d[i]@P);sh.append(ds[i]@P)
  return torch.stack(out),torch.stack(sh)
 if method.kind=='sae':
  sae,sel=method.payload;zc=sae.encode(z['corrupt']);za=zc.clone();zs=zc.clone();za[:,sel]=sae.encode(z['clean'])[:,sel];zs[:,sel]=sae.encode(z['sham'])[:,sel];base=sae.decode(zc);return sae.decode(za)-base,sae.decode(zs)-base
 raise RuntimeError(method.kind)

def interval(v:np.ndarray,b:np.ndarray,c:Mapping[str,Any],tag:str)->dict[str,Any]:return r5.interval(v,b,c,tag)
def gate(name:str,x:Mapping[str,float],c:Mapping[str,Any])->bool:return r5.gate(name,x,c['gates'])
def score(method:Method,p:torch.Tensor,ps:torch.Tensor,z:Mapping[str,torch.Tensor],rows:Sequence[Mapping[str,Any]],c:Mapping[str,Any],stage:str,model:r5.CopyTransformer,estimand:str,matched_status:str='complete')->dict[str,Any]:
 with torch.no_grad():
  patch=model.readout(F.layer_norm(z['corrupt']+p,(p.shape[1],),eps=c['model']['layernorm_eps']));sham=model.readout(F.layer_norm(z['corrupt']+ps,(p.shape[1],),eps=c['model']['layernorm_eps']));abl=model.readout(F.layer_norm(z['clean']-p,(p.shape[1],),eps=c['model']['layernorm_eps']))
  ctr=[]
  for i,r in enumerate(rows):
   g=torch.tensor(rng('control',r['row_seed'],method.name,estimand).normal(size=p.shape[1]),dtype=torch.float32,device=p.device);truth=z['delta'][i];g-=torch.dot(g,truth)*truth/torch.clamp(torch.dot(truth,truth),min=1e-12);g*=torch.linalg.vector_norm(p[i])/torch.clamp(torch.linalg.vector_norm(g),min=1e-12);ctr.append(g)
  ctrl=torch.stack(ctr);ctl=model.readout(F.layer_norm(z['corrupt']+ctrl,(p.shape[1],),eps=c['model']['layernorm_eps']))
 zh=z['logits_clean'].cpu().numpy();zc=z['logits_corrupt'].cpu().numpy();zp=patch.cpu().numpy();zs=sham.cpu().numpy();za=abl.cpu().numpy();zctl=ctl.cpu().numpy();tn=z['target'].cpu().numpy();co=z['contrast'].cpu().numpy();den=r5.row_margin(zh,tn)-r5.row_margin(zc,tn);scale=np.sqrt(np.mean((r5.centered(zh)-r5.centered(zc))**2,1));e=c['eligibility'];clean_ok=np.argmax(zh,1)==tn;corrupt_ok=np.argmax(zc,1)==co;effect_ok=den>e['effect_strict'];eligible=clean_ok&corrupt_ok&effect_ok;sd=np.where(den>1e-6,den,1);ss=np.where(scale>1e-6,scale,1)
 rec=(r5.row_margin(zp,tn)-r5.row_margin(zc,tn))/sd;sr=(r5.row_margin(zs,tn)-r5.row_margin(zc,tn))/sd;cr=(r5.row_margin(zctl,tn)-r5.row_margin(zc,tn))/sd;nec=(r5.row_margin(zh,tn)-r5.row_margin(za,tn))/sd;fv=1-np.sqrt(np.mean((r5.centered(zp)-r5.centered(zh))**2,1))/ss;coll=[]
 for i in range(len(rows)):
  mask=np.ones(zh.shape[1],bool);mask[tn[i]]=False;mask[co[i]]=False;coll.append(float(np.sqrt(np.mean((r5.centered(zp)[i,mask]-r5.centered(zh)[i,mask])**2))/ss[i]))
 vals={'recovery':rec,'sham_specificity':rec-sr,'control_margin':rec-cr,'collateral_error':np.array(coll),'necessity':nec,'full_vocab_recovery':fv};blocks=np.array([r['block'] for r in rows]);B=c['panels'][stage]['blocks'];per={str(b):int(np.sum(eligible&(blocks==b))) for b in range(B)};vs={str(v):int(np.sum(eligible&(tn==v))) for v in range(c['model']['vocab'])};qs=np.array([r['query'] for r in rows]);qsu={str(v):int(np.sum(eligible&(qs==v))) for v in range(c['model']['slots'])};clean_accuracy=float(np.mean(clean_ok));corrupt_accuracy=float(np.mean(corrupt_ok));accuracy_pass=clean_accuracy>=e['clean_accuracy_min'] and corrupt_accuracy>=e['corrupt_accuracy_min'];support=accuracy_pass and int(eligible.sum())>=c['panels']['minimum_eval_total'] and all(x>=c['panels']['minimum_per_block'] for x in per.values()) and all(x>=c['panels']['minimum_per_value_marginal'] for x in vs.values()) and all(x>=c['panels']['minimum_per_query_marginal'] for x in qsu.values())
 metrics={k:interval(v[eligible],blocks[eligible],c,f'{stage}:{method.name}:{estimand}:{k}') for k,v in vals.items()} if support else {};gd={k:gate(k,metrics[k],c) for k in c['gates']} if support else {};complete=matched_status=='complete' and support and len(gd)==len(c['gates']);return {'estimand':estimand,'support_pass':bool(support),'eligible_total':int(eligible.sum()),'eligibility':{'clean_accuracy':clean_accuracy,'corrupt_accuracy':corrupt_accuracy,'accuracy_pass':bool(accuracy_pass),'clean_prediction_exclusions':int(np.sum(~clean_ok)),'corrupt_prediction_exclusions':int(np.sum(~corrupt_ok)),'effect_exclusions':int(np.sum(~effect_ok)),'total_exclusions':int(np.sum(~eligible))},'per_block':per,'value_support':vs,'query_support':qsu,'metrics':metrics,'gate_decisions':gd,'matched_status':matched_status,'all_gates_pass':bool(complete and all(gd.values()))}

def eval_methods(model:r5.CopyTransformer,rows:Sequence[Mapping[str,Any]],methods:Sequence[Method],c:Mapping[str,Any],stage:str,device:torch.device)->dict[str,Any]:
 z=context(model,rows,device);hc=torch.einsum('bs,bsd->bd',z['weights_corrupt'],z['values_clean']);hr=torch.einsum('bs,bsd->bd',z['weights_clean'],z['values_corrupt']);routing={'weights_exact':bool(torch.equal(z['weights_clean'],z['weights_corrupt'])),'clean_hybrid_pass':bool(torch.allclose(hc,z['clean'],atol=c['routing_qa']['hybrid_atol'],rtol=c['routing_qa']['hybrid_rtol'])),'corrupt_hybrid_pass':bool(torch.allclose(hr,z['corrupt'],atol=c['routing_qa']['hybrid_atol'],rtol=c['routing_qa']['hybrid_rtol']))};routing['all_pass']=all(routing.values());out={}
 for m in methods:
  with torch.no_grad():p,ps=predict(m,z,model)
  native=score(m,p,ps,z,rows,c,stage,model,'native')
  if m.kind=='zero':matched={'estimand':'matched','support_pass':native['support_pass'],'eligible_total':native['eligible_total'],'eligibility':native['eligibility'],'metrics':{},'gate_decisions':{},'matched_status':'structural_not_applicable','all_gates_pass':False};pm=p
  else:
   pm,ok=r5.norm_match(p.detach().cpu().numpy(),z['delta'].cpu().numpy());psm,oks=r5.norm_match(ps.detach().cpu().numpy(),z['delta'].cpu().numpy());ms='complete' if bool(np.all(ok&oks)) else 'prediction_incomplete';matched=score(m,torch.tensor(pm,device=device),torch.tensor(psm,device=device),z,rows,c,stage,model,'matched',ms)
  direction=r5.direction_metrics(p.detach().cpu().numpy(),z['delta'].cpu().numpy());out[m.name]={'family':m.family,'seed':m.seed,'rank':m.rank,'parameters':m.parameters,'comparison_class':m.comparison_class,'direction':direction,'native':native,'matched':matched,'all_gates_pass':bool(native['all_gates_pass'] and matched['all_gates_pass'])}
 fam={}
 for f in sorted(set(x.family for x in methods)):
  names=[x.name for x in methods if x.family==f];fam[f]=bool(names and all(out[n]['all_gates_pass'] for n in names))
 complete=bool(routing['all_pass'] and all(np.isfinite(x['direction']['cosine']) and x['native'].get('support_pass') and x['matched'].get('matched_status') in {'complete','prediction_incomplete','structural_not_applicable'} and (x['matched'].get('matched_status')=='structural_not_applicable' or x['matched'].get('support_pass')) and all(np.isfinite(v['point']) and np.isfinite(v['lower']) and np.isfinite(v['upper']) for est in ('native','matched') for v in x[est].get('metrics',{}).values()) for x in out.values()))
 return {'stage':stage,'routing_qa':routing,'eligibility_qa':next(iter(out.values()))['native']['eligibility'] if out else {},'methods':out,'family_pass_every_seed':fam,'technical_complete':complete}

def load_model(c:Mapping[str,Any],seed:int,device:torch.device)->r5.CopyTransformer:
 validate_config(c);rec=c['r5']['checkpoints'][str(seed)];p=ROOT/rec['path'];
 if sha(p)!=rec['sha256']:raise RuntimeError('checkpoint drift')
 model=r5.CopyTransformer(c,seed,device);ck=torch.load(p,map_location=device,weights_only=False);model.load_state_dict(ck['state_dict'],strict=True);return model.eval()

def reconcile_records(c:Mapping[str,Any],out:Path,fits:Mapping[str,Any],dev:Mapping[str,Any])->dict[str,Any]:
 seeds={str(x) for x in c['model']['seeds']};expected_names=expected_method_names(c)
 if set(fits)!=seeds or set(dev)!=seeds:raise RuntimeError('seed record cardinality')
 artifacts=[];expected_paths:set[Path]=set()
 for model_seed in c['model']['seeds']:
  sk=str(model_seed);fr=fits[sk];dr=dev[sk]
  if fr.get('method_table_sha256')!=method_table_hash(c):raise RuntimeError('fit method table drift')
  inv=fr.get('method_inventory',[]);names=[x.get('name') for x in inv]
  if names!=expected_names or len(names)!=len(set(names)):raise RuntimeError('fit method inventory mismatch')
  if any(x.get('parameters')!=expected_parameter_count(x['name'],c) for x in inv):raise RuntimeError('method parameter count mismatch')
  if set(dr.get('methods',{}))!=set(expected_names) or dr.get('stage')!='development':raise RuntimeError('development method inventory mismatch')
  if not finite_tree(fr) or not finite_tree(dr):raise RuntimeError('nonfinite durable record')
  for name,mr in dr['methods'].items():
   if set(('family','seed','rank','parameters','comparison_class','direction','native','matched','all_gates_pass'))-set(mr):raise RuntimeError(f'method schema {name}')
   if mr['parameters']!=expected_parameter_count(name,c):raise RuntimeError(f'evaluation parameter count {name}')
   if mr['native'].get('estimand')!='native' or mr['matched'].get('estimand')!='matched':raise RuntimeError(f'estimand schema {name}')
   status=mr['matched'].get('matched_status')
   if (name=='zero' and status!='structural_not_applicable') or (name!='zero' and status=='structural_not_applicable'):raise RuntimeError(f'matched status {name}')
   if mr['native'].get('support_pass') and set(mr['native'].get('metrics',{}))!=set(c['gates']):raise RuntimeError(f'native metric schema {name}')
   if status!='structural_not_applicable' and mr['matched'].get('support_pass') and set(mr['matched'].get('metrics',{}))!=set(c['gates']):raise RuntimeError(f'matched metric schema {name}')
  learned=[]
  for family,ranks in [('paired_linear',c['methods']['global_ranks']),('target_linear',c['methods']['conditioned_ranks']),('target_nonlinear',c['methods']['conditioned_ranks'])]:learned.extend((f'{family}_rank{k}_seed{sd}',f'{family}_rank{k}_seed{sd}.pt') for k in ranks for sd in c['methods'][family]['seeds'])
  learned.extend((f'topk_sae_seed{sd}',f'topk_sae_seed{sd}.pt') for sd in c['methods']['sae']['seeds'])
  for fit_key,filename in learned:
   p=out/'checkpoints'/sk/filename;expected_paths.add(p)
   rec=fr.get('fits',{}).get(fit_key,{})
   if not p.is_file() or rec.get('sha256')!=sha(p):raise RuntimeError(f'fit artifact mismatch {sk} {fit_key}')
   artifacts.append({'model_seed':model_seed,'fit_key':fit_key,'path':p.relative_to(out).as_posix(),'bytes':p.stat().st_size,'sha256':sha(p)})
  p=out/'checkpoints'/sk/'nonlearned.npz';expected_paths.add(p)
  if not p.is_file() or fr.get('fits',{}).get('nonlearned_sha256')!=sha(p):raise RuntimeError(f'nonlearned artifact mismatch {sk}')
  artifacts.append({'model_seed':model_seed,'fit_key':'nonlearned','path':p.relative_to(out).as_posix(),'bytes':p.stat().st_size,'sha256':sha(p)})
 actual={p for p in (out/'checkpoints').rglob('*') if p.is_file()}
 if actual!=expected_paths:raise RuntimeError('unexpected or missing fit artifacts')
 exact_ok=all(dev[str(sd)]['routing_qa']['all_pass'] and dev[str(sd)]['methods'][name]['all_gates_pass'] for sd in c['model']['seeds'] for name in ('exact_head_delta','identity_full64'))
 technical=all(dev[str(sd)]['technical_complete'] for sd in c['model']['seeds'])
 return {'artifacts':sorted(artifacts,key=lambda x:(x['model_seed'],x['path'])),'exact_identity_authorized':bool(exact_ok),'technical_complete':bool(technical),'expected_method_count':len(expected_names)}

def confirmation_authorization(exact_identity_authorized:bool,technical_complete:bool,_estimated_method_outcomes:Any)->bool:return bool(exact_identity_authorized and technical_complete)

def seal_preconfirmation(c:Mapping[str,Any],out:Path,fits:Mapping[str,Any],dev:Mapping[str,Any])->dict[str,Any]:
 sealed=out/'sealed';sealed.mkdir(exist_ok=False);fit_path=sealed/'fit_records.json';dev_path=sealed/'development_results.json';create_json(fit_path,fits);create_json(dev_path,dev)
 fits_disk=loadj(fit_path);dev_disk=loadj(dev_path);rec=reconcile_records(c,out,fits_disk,dev_disk)
 pre={'schema_version':'trained_copy_method_benchmark_v1_r4_1_preconfirmation','config_sha256':sha(CFG_PATH),'source_sha256':sha(SCRIPT),'freeze_sha256':sha(rp(c,'freeze')),'review_binding_sha256':sha(rp(c,'review_binding')),'r5_source_sha256':c['r5']['source_sha256'],'method_table_sha256':method_table_hash(c),'method_table':c['methods'],'fit_records':{'path':fit_path.relative_to(out).as_posix(),'bytes':fit_path.stat().st_size,'sha256':sha(fit_path)},'development_results':{'path':dev_path.relative_to(out).as_posix(),'bytes':dev_path.stat().st_size,'sha256':sha(dev_path)},'artifacts':rec['artifacts'],'expected_method_count':rec['expected_method_count'],'exact_identity_authorized':rec['exact_identity_authorized'],'technical_complete':rec['technical_complete'],'estimated_method_outcomes_used_for_authorization':False,'confirmation_authorized':confirmation_authorization(rec['exact_identity_authorized'],rec['technical_complete'],None)};create_json(out/'PRECONFIRMATION.json',pre);return verify_preconfirmation(c,out)

def verify_preconfirmation(c:Mapping[str,Any],out:Path)->dict[str,Any]:
 p=out/'PRECONFIRMATION.json';pre=loadj(p);expected={'config_sha256':sha(CFG_PATH),'source_sha256':sha(SCRIPT),'freeze_sha256':sha(rp(c,'freeze')),'review_binding_sha256':sha(rp(c,'review_binding')),'r5_source_sha256':c['r5']['source_sha256'],'method_table_sha256':method_table_hash(c),'method_table':c['methods'],'estimated_method_outcomes_used_for_authorization':False}
 if any(pre.get(k)!=v for k,v in expected.items()):raise RuntimeError('preconfirmation lineage drift')
 records=[]
 for key in ('fit_records','development_results'):
  rec=pre[key];q=out/rec['path']
  if not q.is_file() or q.stat().st_size!=rec['bytes'] or sha(q)!=rec['sha256']:raise RuntimeError(f'{key} durable drift')
  records.append(loadj(q))
 chk=reconcile_records(c,out,records[0],records[1])
 if pre.get('artifacts')!=chk['artifacts'] or pre.get('expected_method_count')!=chk['expected_method_count'] or pre.get('exact_identity_authorized')!=chk['exact_identity_authorized'] or pre.get('technical_complete')!=chk['technical_complete'] or pre.get('confirmation_authorized')!=confirmation_authorization(chk['exact_identity_authorized'],chk['technical_complete'],None):raise RuntimeError('preconfirmation authorization drift')
 return pre

def compatibility_smoke(c:Mapping[str,Any],ps:Mapping[str,Sequence[Mapping[str,Any]]],device:torch.device)->dict[str,Any]:
 sc=json.loads(json.dumps(c));sc['methods']['global_ranks']=[4,64];sc['methods']['conditioned_ranks']=[4]
 for k in ('paired_linear','target_linear','target_nonlinear','sae'):
  sc['methods'][k]['seeds']=sc['methods'][k]['seeds'][:1];sc['methods'][k]['steps']=1
 sc['model']['seeds']=[99993];model=r5.CopyTransformer(sc,99993,device).eval();td=Path('/tmp')/f'tcm_v1_r4_smoke_{os.getpid()}_{str(device).replace(":","_")}'
 if td.exists():raise RuntimeError(f'smoke path exists {td}')
 try:
  ck=td/'checkpoints'/'99993';methods,fit=fit_methods(model,ps['fit'][:256],sc,99993,device,ck);z=context(model,ps['development'][:32],device);finite=True
  for m in methods:
   with torch.no_grad():p,q=predict(m,z,model)
   finite &= bool(torch.isfinite(p).all() and torch.isfinite(q).all())
  by_name={m.name:m for m in methods};p4,_=predict(by_name['output_oracle_rank4'],z,model);p64,_=predict(by_name['output_oracle_rank64'],z,model);truth=z['delta'];e4=float(torch.sum(p4*p4).cpu());e64=float(torch.sum(p64*p64).cpu());oracle64_identity=bool(torch.allclose(p64,truth,atol=1e-6,rtol=1e-6));oracle_rank_ordering=bool(e64+1e-8>=e4)
  jac=fit['fits']['target_nonlinear_rank4_seed8301']['empirical_jacobian_ranks'];dev=eval_methods(model,ps['development'],methods,sc,'development',device);reconciled=reconcile_records(sc,td,{'99993':fit},{'99993':dev});victim=td/reconciled['artifacts'][0]['path'];victim.chmod(0o644)
  with victim.open('ab') as f:f.write(b'corruption-mutation')
  corruption_detected=False
  try:reconcile_records(sc,td,{'99993':fit},{'99993':dev})
  except RuntimeError:corruption_detected=True
  return {'families':sorted(set(m.family for m in methods)),'methods':len(methods),'prediction_finite':finite,'jacobian_targets':len(jac),'fit_artifacts':len(reconciled['artifacts']),'record_reconciliation_pass':reconciled['expected_method_count']==len(methods),'artifact_corruption_detected':corruption_detected,'fitted_output_oracle_rank64_equals_identity':oracle64_identity,'fitted_output_oracle_energy_rank4':e4,'fitted_output_oracle_energy_rank64':e64,'fitted_output_oracle_rank_ordering':oracle_rank_ordering}
 finally:shutil.rmtree(td,ignore_errors=True)

def expected_method_names(c:Mapping[str,Any])->list[str]:
 names=['exact_head_delta','identity_full64']
 for f in ('output_oracle','ambient_pca','random'):names.extend(f'{f}_rank{k}' for k in c['methods']['global_ranks'])
 names.extend(['readout_task_projection','target_mean_delta','within_target_permutation','zero'])
 for f,ranks in [('paired_linear',c['methods']['global_ranks']),('target_linear',c['methods']['conditioned_ranks']),('target_nonlinear',c['methods']['conditioned_ranks'])]:names.extend(f'{f}_rank{k}_seed{sd}' for k in ranks for sd in c['methods'][f]['seeds'])
 for sd in c['methods']['sae']['seeds']:names.extend([f'topk_sae_unpaired_selector_seed{sd}',f'topk_sae_paired_selector_seed{sd}'])
 return names

def expected_parameter_count(name:str,c:Mapping[str,Any])->int:
 d=c['model']['width'];v=c['model']['vocab']
 if name.startswith(('output_oracle_rank','ambient_pca_rank')):return d*int(name.split('rank',1)[1].split('_',1)[0])
 if name.startswith('paired_linear_rank'):return 2*d*int(name.split('rank',1)[1].split('_',1)[0])
 if name.startswith('target_linear_rank'):return v*2*d*int(name.split('rank',1)[1].split('_',1)[0])
 if name.startswith('target_nonlinear_rank'):
  k=int(name.split('rank',1)[1].split('_',1)[0]);h=c['methods']['target_nonlinear']['hidden'];e=c['methods']['target_nonlinear']['target_embedding'];return v*e+(d+e)*h+h+h*k+k+(k+e)*h+h+h*d+d
 if name.startswith('topk_sae_'):return 2*d*c['methods']['sae']['width']+d
 if name=='target_mean_delta':return v*d
 if name=='within_target_permutation':return d*d
 return 0

def finite_tree(x:Any)->bool:
 if isinstance(x,Mapping):return all(finite_tree(v) for v in x.values())
 if isinstance(x,(list,tuple)):return all(finite_tree(v) for v in x)
 if isinstance(x,(float,np.floating)):return bool(np.isfinite(x))
 return True

def verify_ship_review(path:Path,bound_sha256:str)->None:
 if not path.is_file():raise RuntimeError('missing adversarial review')
 lines=path.read_text().splitlines();verdicts=[x.strip() for x in lines if x.strip().startswith('VERDICT:')];bindings=[x.strip() for x in lines if x.strip().startswith('BOUND_SHA256:')]
 if not lines or lines[0].strip()!='VERDICT: SHIP' or verdicts!=['VERDICT: SHIP'] or bindings!=[f'BOUND_SHA256: {bound_sha256}']:raise RuntimeError('adversarial review verdict/binding invalid')

def verify_candidate_lineage(c:Mapping[str,Any],require_review:bool=False,require_lock:bool=False)->dict[str,Any]:
 validate_config(c);p=rp(c,'candidate_manifest')
 if not p.is_file():raise RuntimeError('missing candidate')
 x=loadj(p);expected={'source_sha256':sha(SCRIPT),'test_sha256':sha(TEST),'launcher_sha256':sha(LAUNCHER),'config_sha256':sha(CFG_PATH),'plan_sha256':sha(PLAN),'method_table_sha256':method_table_hash(c),'r5_source_sha256':c['r5']['source_sha256'],'r4_failure_preservation_sha256':recovery_lineage(c)['preservation_sha256'],'r4_freeze_sha256':recovery_lineage(c)['r4_freeze_sha256']}
 if x.get('status')!='PASS' or any(x.get(k)!=v for k,v in expected.items()):raise RuntimeError('candidate lineage drift')
 if x.get('expected_method_count')!=len(expected_method_names(c)):raise RuntimeError('candidate method inventory drift')
 if require_review:
  review=rp(c,'candidate_review');verify_ship_review(review,sha(p))
 if require_lock:
  lock=rp(c,'generator_lock')
  if not lock.is_file():raise RuntimeError('missing generator lock')
  z=loadj(lock);now={'config_sha256':sha(CFG_PATH),'source_sha256':sha(SCRIPT),'test_sha256':sha(TEST),'launcher_sha256':sha(LAUNCHER),'plan_sha256':sha(PLAN),'candidate_sha256':sha(p),'candidate_review_sha256':sha(rp(c,'candidate_review')),'method_table_sha256':method_table_hash(c),'r5_source_sha256':c['r5']['source_sha256'],'r4_failure_preservation_sha256':recovery_lineage(c)['preservation_sha256'],'r4_freeze_sha256':recovery_lineage(c)['r4_freeze_sha256']}
  if any(z.get(k)!=v for k,v in now.items()):raise RuntimeError('generator lock drift')
 return x

def write_candidate(device_name:str,record:bool)->dict[str,Any]:
 c=cfg();validate_config(c);ps=panel_set(c);audit=panel_audit(ps,c);device=torch.device(device_name);model=r5.CopyTransformer(c,99991,device).eval();rows=ps['development'];z=context(model,rows,device);m=Method('exact_head_delta','exact_head_delta','exact',None);p,px=predict(m,z,model);direction=r5.direction_metrics(p.detach().cpu().numpy(),z['delta'].detach().cpu().numpy());smoke=compatibility_smoke(c,ps,device);checks={'exact_direction_finite':direction['finite'] and direction['cosine']>.999999,'zero_direction_finite':r5.direction_metrics(np.zeros_like(z['delta'].detach().cpu().numpy()),z['delta'].detach().cpu().numpy())['finite'],'fitted_output_oracle_rank64_identity':smoke['fitted_output_oracle_rank64_equals_identity'],'fitted_output_oracle_rank_ordering':smoke['fitted_output_oracle_rank_ordering'],'all_32_targets_jacobian_required':c['model']['vocab']==32,'smoke_predictions_finite':smoke['prediction_finite'] and smoke['jacobian_targets']==32,'smoke_record_reconciliation':smoke['record_reconciliation_pass'],'smoke_artifact_corruption_detected':smoke['artifact_corruption_detected'],'tuple_multiplicity_one':all(audit[s]['max_main_tuple_contribution']==1 and audit[s]['max_sham_tuple_contribution']==1 for s in ('fit','development','confirmation')),'complete_registered_offset_coverage':all(audit[s]['offsets_used']==sorted(c['panels'][s]['offsets']) for s in ('fit','development','confirmation')),'evaluation_full_target_query_grid':all(audit[s]['target_query_pairs']==256 for s in ('development','confirmation')),'r5_row_identity_disjoint':audit['cross_r5']['row_id_overlap']==0 and audit['cross_r5']['row_seed_overlap']==0,'r4_payloads_byte_identical':all(rows_jsonl_sha256(ps[st])==next(x['sha256'] for x in recovery_lineage(c)['r4_payloads'] if x['stage']==st) for st in ('fit','development','confirmation'))};payload={'schema_version':'trained_copy_method_benchmark_v1_r4_1_candidate','status':'PASS' if all(checks.values()) else 'FAIL','device':str(device),'source_sha256':sha(SCRIPT),'test_sha256':sha(TEST),'launcher_sha256':sha(LAUNCHER),'config_sha256':sha(CFG_PATH),'plan_sha256':sha(PLAN),'method_table_sha256':method_table_hash(c),'expected_method_count':len(expected_method_names(c)),'panel_audit':audit,'compatibility_smoke':smoke,'r5_source_path':c['r5']['source_path'],'r5_source_sha256':c['r5']['source_sha256'],'r5_preservation_sha256':c['r5']['preservation_sha256'],'r4_failure_preservation_sha256':recovery_lineage(c)['preservation_sha256'],'r4_freeze_sha256':recovery_lineage(c)['r4_freeze_sha256'],'r5_checkpoint_hashes':{k:v['sha256'] for k,v in c['r5']['checkpoints'].items()},'scientific_panel_accessed':False,'r5_checkpoint_loaded':False,'checks':checks}
 if record:
  pth=rp(c,'candidate_manifest');create_json(pth,payload);payload['manifest_sha256']=sha(pth)
 return payload

def create_lock()->dict[str,Any]:
 c=cfg();verify_candidate_lineage(c,True);p=rp(c,'candidate_manifest');review=rp(c,'candidate_review');out={'schema_version':'trained_copy_method_benchmark_v1_r4_1_generator_lock','config_sha256':sha(CFG_PATH),'source_sha256':sha(SCRIPT),'test_sha256':sha(TEST),'launcher_sha256':sha(LAUNCHER),'plan_sha256':sha(PLAN),'candidate_sha256':sha(p),'candidate_review_sha256':sha(review),'method_table_sha256':method_table_hash(c),'r5_source_sha256':c['r5']['source_sha256'],'r4_failure_preservation_sha256':recovery_lineage(c)['preservation_sha256'],'r4_freeze_sha256':recovery_lineage(c)['r4_freeze_sha256'],'created_ns':time.time_ns()};create_json(rp(c,'generator_lock'),out);return out
def prepare()->dict[str,Any]:
 c=cfg();verify_candidate_lineage(c,True,True);lock=rp(c,'generator_lock');
 root=rp(c,'prepared_root');
 if root.exists():raise FileExistsError(root)
 ps=panel_set(c);audit=panel_audit(ps,c);root.mkdir(parents=True)
 old_payloads={x['stage']:x for x in recovery_lineage(c)['r4_payloads']}
 for st,rows in ps.items():
  p=root/f'{st}.jsonl';write_jsonl(p,rows)
  if sha(p)!=old_payloads[st]['sha256'] or p.stat().st_size!=old_payloads[st]['bytes']:raise RuntimeError(f'R4 payload parity drift {st}')
 atomic_json(root/'PREPARED.json',{'schema_version':'trained_copy_method_benchmark_v1_prepared','generator_lock_sha256':sha(lock),'panel_audit':audit,'payload_opened':False});return audit
def freeze()->dict[str,Any]:
 c=cfg();verify_candidate_lineage(c,True,True);root=rp(c,'prepared_root');prep=loadj(root/'PREPARED.json');payloads=[]
 old_payloads={x['stage']:x for x in recovery_lineage(c)['r4_payloads']}
 for st in ('fit','development','confirmation'):
  p=root/f'{st}.jsonl';record={'stage':st,'path':p.relative_to(ROOT).as_posix(),'bytes':p.stat().st_size,'sha256':sha(p),'audit':prep['panel_audit'][st]}
  if record['sha256']!=old_payloads[st]['sha256'] or record['bytes']!=old_payloads[st]['bytes']:raise RuntimeError(f'R4 payload parity drift {st}')
  payloads.append(record)
 f={'schema_version':'trained_copy_method_benchmark_v1_r4_1_freeze','config_sha256':sha(CFG_PATH),'source_sha256':sha(SCRIPT),'test_sha256':sha(TEST),'launcher_sha256':sha(LAUNCHER),'plan_sha256':sha(PLAN),'generator_lock_sha256':sha(rp(c,'generator_lock')),'candidate_sha256':sha(rp(c,'candidate_manifest')),'candidate_review_sha256':sha(rp(c,'candidate_review')),'method_table_sha256':method_table_hash(c),'r5_source_sha256':c['r5']['source_sha256'],'r5_preservation_sha256':c['r5']['preservation_sha256'],'r4_failure_preservation_sha256':recovery_lineage(c)['preservation_sha256'],'r4_freeze_sha256':recovery_lineage(c)['r4_freeze_sha256'],'r5_checkpoints':c['r5']['checkpoints'],'payloads':payloads,'payloads_opened':False};create_json(rp(c,'freeze'),f);return f
def verify_freeze(opaque:bool)->dict[str,Any]:
 c=cfg();verify_candidate_lineage(c,True,True);f=loadj(rp(c,'freeze'));expected={'config_sha256':sha(CFG_PATH),'source_sha256':sha(SCRIPT),'test_sha256':sha(TEST),'launcher_sha256':sha(LAUNCHER),'plan_sha256':sha(PLAN),'generator_lock_sha256':sha(rp(c,'generator_lock')),'candidate_sha256':sha(rp(c,'candidate_manifest')),'candidate_review_sha256':sha(rp(c,'candidate_review')),'method_table_sha256':method_table_hash(c),'r5_source_sha256':c['r5']['source_sha256'],'r5_preservation_sha256':c['r5']['preservation_sha256'],'r4_failure_preservation_sha256':recovery_lineage(c)['preservation_sha256'],'r4_freeze_sha256':recovery_lineage(c)['r4_freeze_sha256'],'r5_checkpoints':c['r5']['checkpoints']}
 if any(f.get(k)!=v for k,v in expected.items()):raise RuntimeError('freeze drift')
 if not opaque:
  for rec in f['payloads']:
   p=ROOT/rec['path'];
   if sha(p)!=rec['sha256'] or p.stat().st_size!=rec['bytes']:raise RuntimeError('payload drift')
 return {'status':'PASS','freeze_sha256':sha(rp(c,'freeze')),'opaque':opaque}
def bind_review()->dict[str,Any]:
 c=cfg();verify_freeze(True);f=rp(c,'freeze');r=rp(c,'frozen_review')
 verify_ship_review(r,sha(f))
 x={'schema_version':'trained_copy_method_benchmark_v1_review_binding','freeze_sha256':sha(f),'review_path':r.relative_to(ROOT).as_posix(),'review_sha256':sha(r)};create_json(rp(c,'review_binding'),x);return x
def open_stage(c:Mapping[str,Any],stage:str,prov:Path,index:int,state:dict[str,Any]|None=None)->list[dict[str,Any]]:
 if state is not None:state['panel_accessed']=True;state['phase']=f'{stage}_access'
 event(prov,index,f'{stage.upper()}_ACCESS_MAY_HAVE_OCCURRED');f=loadj(rp(c,'freeze'));rec=next(x for x in f['payloads'] if x['stage']==stage);p=ROOT/rec['path'];
 if sha(p)!=rec['sha256']:raise RuntimeError('payload drift')
 rows=read_jsonl(p);event(prov,index+1,f'{stage.upper()}_OPENED');
 if state is not None:state['phase']=f'{stage}_opened';state[f'{stage}_opened']=True
 return rows
def launch_preflight(index:int,uuid:str,allow_provenance:bool=False)->None:
 c=cfg();validate_config(c);verify_freeze(True);b=loadj(rp(c,'review_binding')); 
 review=rp(c,'frozen_review')
 if b.get('review_path')!=review.relative_to(ROOT).as_posix() or b.get('freeze_sha256')!=sha(rp(c,'freeze')) or b.get('review_sha256')!=sha(review):raise RuntimeError('review binding drift')
 verify_ship_review(review,sha(rp(c,'freeze')))
 if rp(c,'output_root').exists():raise RuntimeError('preexisting output_root')
 if rp(c,'provenance_root').exists() and not allow_provenance:raise RuntimeError('preexisting provenance_root')
 got=subprocess.check_output(['nvidia-smi','--query-gpu=index,uuid','--format=csv,noheader']).decode().splitlines();m={int(x.split(',')[0]):x.split(',')[1].strip() for x in got}
 if m.get(index)!=uuid:raise RuntimeError('GPU UUID mismatch')
def gpu_validate(index:int,uuid:str,pane_pid:int,lockdir:str,token:str)->torch.device:
 if os.environ.get('CUDA_VISIBLE_DEVICES')!=uuid:raise RuntimeError('CUDA visibility mismatch')
 if Path(lockdir).name!=f'msae_trained_copy_methods_v1_r4_{uuid}.lockdir' or (Path(lockdir)/'token').read_text().strip()!=token:raise RuntimeError('GPU lock mismatch')
 d=torch.device('cuda:0');x=torch.ones(1,device=d);torch.cuda.synchronize();pid=os.getpid();rows=subprocess.check_output(['nvidia-smi','--query-compute-apps=gpu_uuid,pid','--format=csv,noheader']).decode().splitlines()
 if not any(a.strip()==uuid and int(b.strip())==pid for a,b in (r.split(',')[:2] for r in rows)):raise RuntimeError('worker PID not on UUID')
 anc=[];cur=pid
 while cur>1:
  anc.append(cur);cur=parse_proc_stat_ppid(Path(f'/proc/{cur}/stat').read_text())
 if pane_pid not in anc:raise RuntimeError('pane ancestry mismatch')
 return d

def write_terminal(c:Mapping[str,Any],prov:Path,state:dict[str,Any],status:str,error:str|None=None,**kw:Any)->None:
 if state.get('terminal_written'):return
 payload={'schema_version':'trained_copy_method_benchmark_v1_r4_1_terminal','status':status,'phase':state.get('phase'),'panel_accessed':bool(state.get('panel_accessed')),'confirmation_opened':bool(state.get('confirmation_opened')),'no_retry_authorized':True,'config_sha256':sha(CFG_PATH),'source_sha256':sha(SCRIPT),'freeze_sha256':sha(rp(c,'freeze')),'time_ns':time.time_ns(),**kw}
 if error is not None:payload['error']=error
 create_json(prov/'TERMINAL.json',payload);state['terminal_written']=True

def technical_failure_status(state:Mapping[str,Any])->str:return 'TECHNICAL_FAILURE_AFTER_ACCESS' if state.get('panel_accessed') else 'TECHNICAL_FAILURE_BEFORE_ACCESS'
def make_signal_handler(c:Mapping[str,Any],prov:Path,state:dict[str,Any]):
 def handler(signum:int,_frame:Any)->None:
  write_terminal(c,prov,state,technical_failure_status(state),f'signal {signal.Signals(signum).name}');raise SystemExit(128+signum)
 return handler
def confirmation_open_if_authorized(pre:Mapping[str,Any],opener):
 if not pre.get('confirmation_authorized'):return None
 return opener()

def run_pipeline(index:int,uuid:str,pane_pid:int,lockdir:str,token:str)->None:
 c=cfg();prov=rp(c,'provenance_root');out=rp(c,'output_root')
 if prov.exists() or out.exists():raise RuntimeError('run namespace already exists')
 prov.mkdir(parents=True,exist_ok=False);state={'phase':'run_start','panel_accessed':False,'confirmation_opened':False,'terminal_written':False};event(prov,0,'RUN_START_NO_PANEL_ACCESS',worker_pid=os.getpid())
 old_handlers={}
 on_signal=make_signal_handler(c,prov,state)
 for sig in (signal.SIGTERM,signal.SIGINT,signal.SIGHUP):old_handlers[sig]=signal.getsignal(sig);signal.signal(sig,on_signal)
 try:
  state['phase']='launch_preflight';launch_preflight(index,uuid,True);device=gpu_validate(index,uuid,pane_pid,lockdir,token);out.mkdir(parents=True,exist_ok=False);atomic_json(prov/'LAUNCH.json',{'physical_index':index,'gpu_uuid':uuid,'worker_pid':os.getpid(),'pane_pid':pane_pid,'freeze_sha256':sha(rp(c,'freeze')),'r5_source_sha256':c['r5']['source_sha256'],'time_ns':time.time_ns()});torch.use_deterministic_algorithms(True);torch.manual_seed(c['seed']);np.random.seed(c['seed']);random.seed(c['seed'])
  fitrows=open_stage(c,'fit',prov,10,state);devrows=open_stage(c,'development',prov,12,state);models={};methods={};fits={};dev={};ckroot=out/'checkpoints';ckroot.mkdir()
  for sd in c['model']['seeds']:
   state['phase']=f'fit_model_{sd}'
   model=load_model(c,sd,device);models[sd]=model;ms,fr=fit_methods(model,fitrows,c,sd,device,ckroot/str(sd));methods[sd]=ms;fits[str(sd)]=fr;dev[str(sd)]=eval_methods(model,devrows,ms,c,'development',device)
  state['phase']='development_complete';event(prov,14,'DEVELOPMENT_COMPLETE');pre=seal_preconfirmation(c,out,fits,dev);event(prov,15,'PRECONFIRMATION_SEALED',manifest_sha256=sha(out/'PRECONFIRMATION.json'),confirmation_authorized=pre['confirmation_authorized'])
  if not pre['confirmation_authorized']:
   event(prov,16,'CONFIRMATION_BLOCKED_UNOPENED');final={'schema_version':'trained_copy_method_benchmark_v1_r4_1_final','status':'DEVELOPMENT_NOT_AUTHORIZED','confirmation_opened':False,'preconfirmation':pre,'preconfirmation_sha256':sha(out/'PRECONFIRMATION.json')};create_json(out/'final/result.json',final);write_terminal(c,prov,state,'DEVELOPMENT_NOT_AUTHORIZED',final_sha256=sha(out/'final/result.json'));return
  state['phase']='preconfirmation_reverify';pre=verify_preconfirmation(c,out)
  if not pre['confirmation_authorized']:raise RuntimeError('durable confirmation authorization false')
  confrows=confirmation_open_if_authorized(pre,lambda:open_stage(c,'confirmation',prov,16,state))
  if confrows is None:raise RuntimeError('confirmation access guard blocked')
  state['confirmation_opened']=True;conf={str(sd):eval_methods(models[sd],confrows,methods[sd],c,'confirmation',device) for sd in c['model']['seeds']};families=sorted(set(v.family for ms in methods.values() for v in ms));dev_disk=loadj(out/pre['development_results']['path']);fits_disk=loadj(out/pre['fit_records']['path']);family_all={f:all(dev_disk[str(sd)]['family_pass_every_seed'].get(f,False) and conf[str(sd)]['family_pass_every_seed'].get(f,False) for sd in c['model']['seeds']) for f in families};final={'schema_version':'trained_copy_method_benchmark_v1_r4_1_final','status':'METHOD_BENCHMARK_COMPLETE','confirmation_opened':True,'conditional_on_r5_qualified_checkpoints':True,'method_table_sha256':method_table_hash(c),'method_table':c['methods'],'fits':fits_disk,'development':dev_disk,'confirmation':conf,'family_pass_all_checkpoints_both_panels':family_all,'scope':c['scope'],'preconfirmation':{'exact_identity_authorized':pre['exact_identity_authorized'],'technical_complete':pre['technical_complete'],'estimated_method_outcomes_used_for_authorization':pre['estimated_method_outcomes_used_for_authorization'],'confirmation_authorized':pre['confirmation_authorized']},'lineage':{'config_sha256':sha(CFG_PATH),'source_sha256':sha(SCRIPT),'freeze_sha256':sha(rp(c,'freeze')),'review_binding_sha256':sha(rp(c,'review_binding')),'r5_source_sha256':c['r5']['source_sha256'],'r5_checkpoint_hashes':{k:v['sha256'] for k,v in c['r5']['checkpoints'].items()},'preconfirmation_sha256':sha(out/'PRECONFIRMATION.json')}};create_json(out/'final/result.json',final);state['phase']='complete';event(prov,18,'TERMINAL_COMPLETE',status=final['status'],final_sha256=sha(out/'final/result.json'));write_terminal(c,prov,state,'METHOD_BENCHMARK_COMPLETE',final_sha256=sha(out/'final/result.json'))
 except BaseException as e:
  write_terminal(c,prov,state,technical_failure_status(state),f'{type(e).__name__}: {e}');raise
 finally:
  for sig,handler in old_handlers.items():signal.signal(sig,handler)

def mutation_suite()->dict[str,Any]:
 c=cfg();ps=panel_set(c);a=panel_audit(ps,c);bad=json.loads(json.dumps(c));bad['panels']['development']['offsets']=[21,22,23,24,25];overlap=False;duplicate_sham=False;missing_pair=False
 try:validate_config(bad)
 except RuntimeError:overlap=True
 badps=json.loads(json.dumps(ps));badps['development'][-1]['sham']=badps['development'][0]['sham'];badps['development'][-1]['query']=badps['development'][0]['query'];badps['development'][-1]['contrast']=badps['development'][0]['contrast']
 try:panel_audit(badps,c)
 except RuntimeError:duplicate_sham=True
 badps=json.loads(json.dumps(ps));badps['development'][-1]['target']=badps['development'][0]['target'];badps['development'][-1]['query']=badps['development'][0]['query']
 try:panel_audit(badps,c)
 except RuntimeError:missing_pair=True
 component_mutations={}
 for st in ('fit','development','confirmation'):
  for off in c['panels'][st]['offsets']:
   badps=json.loads(json.dumps(ps));replacement=next(x for x in c['panels'][st]['offsets'] if x!=off)
   for row in badps[st]:
    if row['offset']==off:row['offset']=replacement
   caught=False
   try:panel_audit(badps,c)
   except RuntimeError:caught=True
   component_mutations[f'{st}:{off}']=caught
 td=Path('/tmp')/f'tcm_r4_1_review_mutation_{os.getpid()}';td.mkdir(exist_ok=False);review=td/'review.md';review.write_text('VERDICT: BLOCK\nThe required text is VERDICT: SHIP\nBOUND_SHA256: abc\n');review_bypass=False
 try:
  try:verify_ship_review(review,'abc')
  except RuntimeError:review_bypass=True
 finally:shutil.rmtree(td)
 probe=rng('oracle-rank-mutation').normal(size=(128,c['model']['width']));_,_,basis=canonical_svd(probe);rank_mutation=oracle_rank_order_valid(probe,basis,[4,64]) and not oracle_rank_order_valid(probe,basis[::-1].copy(),[4,64]);states=torch.tensor(rng('unpaired-trap').normal(size=(97,c['model']['width'])),dtype=torch.float32);perm=torch.tensor(rng('unpaired-perm').permutation(len(states)));_,b1=fit_unpaired_ambient_basis(states);_,b2=fit_unpaired_ambient_basis(states[perm]);codes=torch.tensor(rng('unpaired-codes').normal(size=(97,c['methods']['sae']['width'])),dtype=torch.float32);unpaired_invariant=bool(np.allclose(b1[:8].T@b1[:8],b2[:8].T@b2[:8],atol=1e-6,rtol=1e-6) and torch.equal(select_unpaired_sae_features(codes,16),select_unpaired_sae_features(codes[perm],16)))
 checks={'offset_overlap_detected':overlap,'duplicate_sham_detected':duplicate_sham,'missing_target_query_pair_detected':missing_pair,'every_offset_deletion_detected':all(component_mutations.values()),'conflicting_review_verdict_rejected':review_bypass,'oracle_rank_order_mutation_detected':rank_mutation,'unpaired_selectors_permutation_invariant':unpaired_invariant,'all_tuple_multiplicities_one':all(a[s]['max_main_tuple_contribution']==1 and a[s]['max_sham_tuple_contribution']==1 for s in ('fit','development','confirmation')),'complete_offset_coverage':all(a[s]['offsets_used']==sorted(c['panels'][s]['offsets']) for s in ('fit','development','confirmation')),'expected_method_inventory_nonempty':len(expected_method_names(c))==66,'r5_source_bound':sha(ROOT/c['r5']['source_path'])==c['r5']['source_sha256'],'r5_row_identity_disjoint':a['cross_r5']['row_id_overlap']==0 and a['cross_r5']['row_seed_overlap']==0}
 return {'status':'PASS' if all(checks.values()) else 'FAIL','checks':checks,'component_mutations':component_mutations,'panel_audit':a}
def main()->None:
 ap=argparse.ArgumentParser();sp=ap.add_subparsers(dest='cmd',required=True);q=sp.add_parser('candidate-preflight');q.add_argument('--device',default='cpu');q.add_argument('--record',action='store_true');sp.add_parser('mutation-suite');sp.add_parser('create-lock');sp.add_parser('prepare');sp.add_parser('freeze');q=sp.add_parser('verify-freeze');q.add_argument('--opaque',action='store_true');sp.add_parser('bind-review');q=sp.add_parser('launch-preflight');q.add_argument('--physical-index',type=int,required=True);q.add_argument('--gpu-uuid',required=True);q=sp.add_parser('run-pipeline');q.add_argument('--physical-index',type=int,required=True);q.add_argument('--gpu-uuid',required=True);q.add_argument('--pane-pid',type=int,required=True);q.add_argument('--gpu-lockdir',required=True);q.add_argument('--launch-token',required=True);a=ap.parse_args()
 if a.cmd=='candidate-preflight':x=write_candidate(a.device,a.record)
 elif a.cmd=='mutation-suite':x=mutation_suite()
 elif a.cmd=='create-lock':x=create_lock()
 elif a.cmd=='prepare':x=prepare()
 elif a.cmd=='freeze':x=freeze()
 elif a.cmd=='verify-freeze':x=verify_freeze(a.opaque)
 elif a.cmd=='bind-review':x=bind_review()
 elif a.cmd=='launch-preflight':launch_preflight(a.physical_index,a.gpu_uuid);x={'status':'PASS'}
 else:run_pipeline(a.physical_index,a.gpu_uuid,a.pane_pid,a.gpu_lockdir,a.launch_token);x={'status':'COMPLETE'}
 print(json.dumps(x,sort_keys=True,default=str))
if __name__=='__main__':main()
