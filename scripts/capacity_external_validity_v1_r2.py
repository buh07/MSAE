#!/usr/bin/env python3
"""Capacity-controlled synthetic diagnostic and conditional trained-copy bridge v1."""
from __future__ import annotations
import argparse, ast, hashlib, json, math, os, random, secrets, shutil, signal, subprocess, sys, tempfile, time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping, Sequence
import numpy as np
import torch
import torch.nn.functional as F
from unittest import mock

ROOT=Path(os.environ.get('MSAE_ROOT',Path(__file__).resolve().parents[1]))
CAP_CFG=ROOT/'configs/capacity_controller_diagnostic_v1_r2/run.json'
EXT_CFG=ROOT/'configs/trained_copy_external_v1_r2/run.json'
PLAN=ROOT/'PLAN_CAPACITY_EXTERNAL_VALIDITY_V1_R2.md'
PLAN_REVIEW=ROOT/'reports/adversarial/capacity_external_validity_v1_r2_plan_review.md'
PRESERVE=ROOT/'reports/provenance/transformer_realistic_bridge_v1_r2_postresult/PRESERVATION.json'
FAILURE_PRESERVE=ROOT/'reports/provenance/capacity_external_validity_v1_failure_preservation/PRESERVATION.json'
V1_SOURCE=ROOT/'scripts/capacity_external_validity_v1.py'
V1_CAP_CFG=ROOT/'configs/capacity_controller_diagnostic_v1/run.json'
V1_EXT_CFG=ROOT/'configs/trained_copy_external_v1/run.json'
SCRIPT=ROOT/'scripts/capacity_external_validity_v1_r2.py'
LAUNCHER=ROOT/'scripts/launch_capacity_external_validity_v1_r2_tmux.sh'
TEST=ROOT/'tests/test_capacity_external_validity_v1_r2.py'
_ACTIVE_RUN:dict[str,Path]={}

def loadj(p:Path)->Any:return json.loads(p.read_text())
def sha(p:Path)->str:return hashlib.sha256(p.read_bytes()).hexdigest()
def canon(x:Any)->bytes:return json.dumps(x,sort_keys=True,separators=(',',':'),allow_nan=False).encode()
def seed32(*xs:Any)->int:return int.from_bytes(hashlib.sha256(canon(xs)).digest()[:4],'little')
def rng(*xs:Any)->np.random.Generator:return np.random.default_rng(seed32(*xs))
def atomic_json(p:Path,x:Any)->None:
 p.parent.mkdir(parents=True,exist_ok=True)
 if p.exists():raise RuntimeError(f'immutable output exists: {p}')
 t=p.with_name(p.name+f'.tmp.{os.getpid()}'); data=json.dumps(x,indent=2,sort_keys=True,allow_nan=False)+'\n'
 with t.open('x') as f:f.write(data);f.flush();os.fsync(f.fileno())
 os.replace(t,p); d=os.open(p.parent,os.O_DIRECTORY);os.fsync(d);os.close(d)
def atomic_text(p:Path,s:str)->None:
 p.parent.mkdir(parents=True,exist_ok=True)
 if p.exists():raise RuntimeError(f'immutable output exists: {p}')
 with p.open('x') as f:f.write(s);f.flush();os.fsync(f.fileno())
 d=os.open(p.parent,os.O_DIRECTORY);os.fsync(d);os.close(d)
def write_jsonl(p:Path,rows:Sequence[Mapping[str,Any]])->None:
 atomic_text(p,''.join(json.dumps(dict(x),sort_keys=True)+'\n' for x in rows))
def read_jsonl(p:Path)->list[dict[str,Any]]:return [json.loads(x) for x in p.read_text().splitlines() if x]
def cfg(kind:str)->dict[str,Any]:return loadj(CAP_CFG if kind=='capacity' else EXT_CFG)
def rp(c:Mapping[str,Any],key:str)->Path:return ROOT/c['runtime'][key]

def qr_canonical(a:np.ndarray)->np.ndarray:
 q,_=np.linalg.qr(a)
 for j in range(q.shape[1]):
  col=q[:,j]; m=float(np.max(np.abs(col))); ix=int(np.flatnonzero(np.abs(col)==m)[0])
  if m==0:raise RuntimeError('zero QR pivot')
  if col[ix]<0:q[:,j]*=-1
 return q

def svd_canonical(a:np.ndarray,full_matrices:bool=False)->tuple[np.ndarray,np.ndarray,np.ndarray]:
 u,s,vh=np.linalg.svd(a,full_matrices=full_matrices)
 for j in range(len(s)):
  row=vh[j];mx=float(np.max(np.abs(row)));ix=int(np.flatnonzero(np.abs(row)==mx)[0])
  if mx and row[ix]<0:u[:,j]*=-1;vh[j]*=-1
 start=0
 while start<len(s):
  end=start+1
  while end<len(s) and abs(float(s[end]-s[start]))<=1e-12*max(float(s[start]),1.0):end+=1
  if end-start>1:
   order=sorted(range(start,end),key=lambda j:(int(np.argmax(np.abs(vh[j]))),tuple(np.round(vh[j],14))))
   u[:,start:end]=u[:,order];s[start:end]=s[order];vh[start:end]=vh[order]
  start=end
 return u,s,vh

def capacity_mats(instance:int,c:Mapping[str,Any])->dict[str,np.ndarray]:
 d,t=c['dimension'],c['targets']; g=rng('capacity_mats',instance)
 D=qr_canonical(g.normal(size=(d,d)))[:,:t]
 Q1=qr_canonical(g.normal(size=(d,d)));Q2=qr_canonical(g.normal(size=(d,d)))
 s=np.linspace(c['generator']['mix_singular_min'],c['generator']['mix_singular_max'],d)
 M=Q1@np.diag(s)@Q2.T; W=np.linalg.inv(M)
 return {'D':D,'M':M,'W':W}

def make_capacity_rows(instance:int,stage:str,c:Mapping[str,Any],blocks:int|None=None,rows_per:int|None=None,seed:int|None=None)->list[dict[str,Any]]:
 pc=c['panels'][stage] if stage in c['panels'] else {'blocks':blocks,'rows_per_block':rows_per,'seed':seed}
 B=int(blocks or pc['blocks']);R=int(rows_per or pc['rows_per_block']);S=int(seed or pc['seed']); T=c['targets']
 rows=[]
 for b in range(B):
  for r in range(R):
   ix=b*R+r;t=ix%T;cycle=ix//T;off=1+cycle%(T-1);hoff=1+(cycle+7)%(T-1)
   if hoff==off:hoff=1+(hoff%(T-1))
   c1=(t+off)%T;h=(t+hoff)%T
   rs=seed32('capacity_row',instance,S,b,r)
   rows.append({'row_id':f'cap-{instance}-{stage}-{b:04d}-{r:03d}-{rs:08x}','row_seed':rs,'instance':instance,'stage':stage,'block':b,'target':t,'contrast':c1,'sham':h})
 return rows

def capacity_arrays(rows:Sequence[Mapping[str,Any]],instance:int,c:Mapping[str,Any])->dict[str,np.ndarray]:
 m=capacity_mats(instance,c);D,M=m['D'],m['M']; n=len(rows);d=c['dimension'];gcfg=c['generator']
 corrupt=np.zeros((n,d));delta=np.zeros((n,d));sham=np.zeros((n,d))
 target=np.array([x['target'] for x in rows]);contrast=np.array([x['contrast'] for x in rows]);sh=np.array([x['sham'] for x in rows])
 for i,row in enumerate(rows):
  rr=rng('capacity_values',instance,row['row_seed'])
  z=rr.normal(size=d);z=z-D@(D.T@z)
  eps=rr.normal(size=d);eps_s=rr.normal(size=d)
  corrupt[i]=gcfg['corrupt_target']*D[:,target[i]]+gcfg['corrupt_contrast']*D[:,contrast[i]]+gcfg['corrupt_orthogonal_noise']*z
  delta[i]=gcfg['delta_target']*D[:,target[i]]+gcfg['delta_contrast']*D[:,contrast[i]]+gcfg['delta_noise']*eps
  sham[i]=gcfg['delta_target']*D[:,sh[i]]+gcfg['delta_contrast']*D[:,contrast[i]]+gcfg['delta_noise']*eps_s
 x=delta@M;xs=sham@M; hybrid=corrupt+delta
 def logits(s:np.ndarray)->np.ndarray:
  mu=s.mean(1,keepdims=True);var=((s-mu)**2).mean(1,keepdims=True)
  return gcfg['readout_gain']*((s-mu)/np.sqrt(var+gcfg['layernorm_eps']))@D
 return {'x':x,'x_sham':xs,'delta':delta,'delta_sham':sham,'corrupt':corrupt,'hybrid':hybrid,'logits_corrupt':logits(corrupt),'logits_hybrid':logits(hybrid),'D':D,'M':M,'W':m['W'],'target':target,'contrast':contrast,'sham':sh,'blocks':np.array([x['block'] for x in rows]),'logits_fn':logits}

def capacity_basis_check(instance:int,c:Mapping[str,Any])->dict[str,Any]:
 m=capacity_mats(instance,c);I=np.eye(c['dimension']);err=float(np.max(np.abs((I@m['M'])@m['W']-I)))
 return {'instance':instance,'max_abs':err,'pass':err<=c['generator']['basis_atol'],'condition':float(np.linalg.cond(m['M']))}

def row_margin(z:np.ndarray,t:np.ndarray)->np.ndarray:
 v=z.shape[1];return (v*z[np.arange(len(z)),t]-z.sum(1))/(v-1)
def centered(z:np.ndarray)->np.ndarray:return z-z.mean(1,keepdims=True)
def interval(v:np.ndarray,blocks:np.ndarray,c:Mapping[str,Any],tag:str)->dict[str,Any]:
 uniq=np.unique(blocks);groups=[v[blocks==b] for b in uniq];point=float(np.mean([x.mean() for x in groups]));rg=rng(c['seed'],tag)
 draws=[]
 for _ in range(c['bootstrap']['draws']):
  bs=rg.choice(len(groups),len(groups),replace=True); draws.append(float(np.mean([rg.choice(groups[int(j)],len(groups[int(j)]),replace=True).mean() for j in bs])))
 lo,hi=np.quantile(draws,c['bootstrap']['quantiles'],method=c['bootstrap']['method'])
 return {'point':point,'lower':float(lo),'upper':float(hi),'draws':len(draws)}
def gate(name:str,x:Mapping[str,float],g:Mapping[str,Any])->bool:
 q=g[name]
 if name=='collateral_error':return x['point']<=q['point_max'] and x['upper']<q['upper_strict_max']
 return x['point']>=q['point_min'] and x['lower']>q['lower_strict_min']

def norm_match(x:np.ndarray,ref:np.ndarray)->tuple[np.ndarray,np.ndarray]:
 a=np.linalg.norm(x,axis=1);b=np.linalg.norm(ref,axis=1);ok=np.isfinite(a)&(a>1e-10)&np.isfinite(b)&(b>0);s=np.where(ok,b/np.maximum(a,1e-10),0)
 return x*s[:,None],ok

def direction_metrics(pred:np.ndarray,truth:np.ndarray,train_basis:np.ndarray|None=None,rank:int|None=None)->dict[str,Any]:
 pn=np.linalg.norm(pred,axis=1);tn=np.linalg.norm(truth,axis=1);cos=np.sum(pred*truth,1)/np.maximum(pn*tn,1e-12);rel=np.linalg.norm(pred-truth,axis=1)/np.maximum(tn,1e-12)
 out={'cosine':float(np.mean(cos)),'relative_l2':float(np.mean(rel)),'captured_energy':float(np.mean((pn/np.maximum(tn,1e-12))**2)),'finite':bool(np.all(np.isfinite(cos)) and np.all(np.isfinite(rel)))}
 if train_basis is not None:
  k=min(int(rank or train_basis.shape[0]),train_basis.shape[0]);B=train_basis[:k];out['train_basis_projection_energy']=float(np.sum((truth@B.T)**2)/max(float(np.sum(truth**2)),1e-12));_,s,vh=svd_canonical(pred.astype(np.float64),False);eff=min(k,int(np.sum(s>max(float(s[0]) if len(s) else 0,1e-12)*1e-7)))
  out['predicted_effective_rank']=eff;out['principal_subspace_overlap']=float(np.mean(np.linalg.svd(vh[:eff]@B.T,compute_uv=False)**2)) if eff else 0.0
 return out

def control_delta(pred:np.ndarray,truth:np.ndarray,instance:int,rows:Sequence[Mapping[str,Any]],tag:str)->np.ndarray:
 out=[]
 for i,row in enumerate(rows):
  g=rng('control',instance,row['row_seed'],tag).normal(size=pred.shape[1]);t=truth[i];g-=np.dot(g,t)*t/max(float(np.dot(t,t)),1e-12);g*=np.linalg.norm(pred[i])/max(float(np.linalg.norm(g)),1e-12);out.append(g)
 return np.stack(out)

def score_prediction(name:str,pred:np.ndarray,pred_sham:np.ndarray,a:Mapping[str,Any],rows:Sequence[Mapping[str,Any]],c:Mapping[str,Any],stage:str,estimand:str,complete:bool=True)->dict[str,Any]:
 logits=a['logits_fn'];zc=a['logits_corrupt'];zh=a['logits_hybrid'];t=a['target'];co=a['contrast'];d=row_margin(zh,t)-row_margin(zc,t);scale=np.sqrt(np.mean((centered(zh)-centered(zc))**2,axis=1));e=c['eligibility']
 eligible=(np.argmax(zh,1)==t)&(row_margin(zh,t)>e['hybrid_margin_strict'])&(row_margin(zc,t)<e['corrupt_margin_strict_upper'])&(d>e['effect_strict'])&(d>e['denominator_strict'])&(scale>e['centered_scale_strict'])
 patch=logits(a['corrupt']+pred);sham=logits(a['corrupt']+pred_sham);ctl=logits(a['corrupt']+control_delta(pred,a['delta'],int(rows[0]['instance']),rows,name+estimand));abl=logits(a['hybrid']-pred)
 sd=np.where(d>e['denominator_strict'],d,1);ss=np.where(scale>e['centered_scale_strict'],scale,1)
 rec=(row_margin(patch,t)-row_margin(zc,t))/sd; sr=(row_margin(sham,t)-row_margin(zc,t))/sd;cr=(row_margin(ctl,t)-row_margin(zc,t))/sd;nec=(row_margin(zh,t)-row_margin(abl,t))/sd;fv=1-np.sqrt(np.mean((centered(patch)-centered(zh))**2,axis=1))/ss
 coll=[]
 for i in range(len(rows)):
  mask=np.ones(zh.shape[1],bool);mask[t[i]]=False;mask[co[i]]=False
  coll.append(float(np.sqrt(np.mean((centered(patch)[i,mask]-centered(zh)[i,mask])**2))/ss[i]))
 vals={'recovery':rec,'sham_specificity':rec-sr,'control_margin':rec-cr,'collateral_error':np.array(coll),'necessity':nec,'full_vocab_recovery':fv}
 blocks=a['blocks'];B=c['panels'][stage]['blocks'];per={str(b):int(np.sum(eligible&(blocks==b))) for b in range(B)};ts={}
 for v in range(c['targets']):ts[str(v)]={'eligible_rows':int(np.sum(eligible&(t==v))),'eligible_blocks':len(set(blocks[eligible&(t==v)].tolist()))}
 support=int(eligible.sum())>=c['panels']['minimum_eval_total'] and all(x>=c['panels']['minimum_eval_per_block'] for x in per.values()) and all(x['eligible_rows']>=c['panels']['minimum_eval_rows_per_target'] and x['eligible_blocks']>=c['panels']['minimum_eval_blocks_per_target'] for x in ts.values()) and 1-float(eligible.mean())<=c['panels']['maximum_exclusion_rate']
 sm={k:interval(v[eligible],blocks[eligible],c,f'{stage}:{name}:{estimand}:{k}') for k,v in vals.items()} if support else {};gd={k:gate(k,sm[k],c['gates']) for k in c['gates']} if support else {}
 return {'method':name,'stage':stage,'estimand':estimand,'support_pass':bool(support),'eligible_total':int(eligible.sum()),'per_block':per,'target_support':ts,'metrics':sm,'gate_decisions':gd,'all_gates_pass':bool(complete and support and len(gd)==len(c['gates']) and all(gd.values()))}

@dataclass
class Method:
 name:str;family:str;kind:str;payload:Any;seed:int|None=None;rank:int|None=None;train_basis:np.ndarray|None=None;parameter_count:int=0;effective_rank:Any=None

class FactorLinear(torch.nn.Module):
 def __init__(self,d:int,k:int,seed:int,device:torch.device):
  super().__init__();gen=torch.Generator(device=device).manual_seed(seed);self.u=torch.nn.Parameter(torch.randn(d,k,generator=gen,device=device)*.02);self.v=torch.nn.Parameter(torch.randn(k,d,generator=gen,device=device)*.02)
 def forward(self,x:torch.Tensor,t:torch.Tensor|None=None)->torch.Tensor:return x@self.u@self.v
class TargetLinear(torch.nn.Module):
 def __init__(self,d:int,k:int,T:int,seed:int,device:torch.device):
  super().__init__();gen=torch.Generator(device=device).manual_seed(seed);self.u=torch.nn.Parameter(torch.randn(T,d,k,generator=gen,device=device)*.02);self.v=torch.nn.Parameter(torch.randn(T,k,d,generator=gen,device=device)*.02)
 def forward(self,x:torch.Tensor,t:torch.Tensor)->torch.Tensor:return torch.bmm(torch.bmm(x[:,None,:],self.u[t]),self.v[t])[:,0,:]
class TargetMLP(torch.nn.Module):
 def __init__(self,d:int,k:int,T:int,h:int,seed:int,device:torch.device):
  super().__init__();torch.manual_seed(seed);self.e=torch.nn.Embedding(T,16,device=device);self.enc=torch.nn.Sequential(torch.nn.Linear(d+16,h,device=device),torch.nn.GELU(),torch.nn.Linear(h,k,device=device));self.dec=torch.nn.Sequential(torch.nn.Linear(k+16,h,device=device),torch.nn.GELU(),torch.nn.Linear(h,d,device=device))
 def forward(self,x:torch.Tensor,t:torch.Tensor)->torch.Tensor:
  e=self.e(t);z=self.enc(torch.cat((x,e),1));return self.dec(torch.cat((z,e),1))

def first_true_index(mask:torch.Tensor)->int:
 if mask.dtype is not torch.bool or mask.ndim!=1:raise ValueError('first_true_index requires a 1D bool tensor')
 found=torch.nonzero(mask,as_tuple=False).reshape(-1)
 if found.numel()==0:raise ValueError('first_true_index requires at least one match')
 return int(found[0].detach().cpu())

def empirical_jacobian_ranks(model:TargetMLP,x:torch.Tensor,targets:torch.Tensor,target_count:int,device:torch.device)->list[int]:
 ranks=[]
 for tv in range(target_count):
  ix=first_true_index(targets==tv);sample=x[ix].detach().requires_grad_(True);target=torch.tensor([tv],device=device)
  jac=torch.autograd.functional.jacobian(lambda z:model(z[None,:],target)[0],sample,vectorize=True).detach().cpu().numpy();ranks.append(int(np.linalg.matrix_rank(jac,tol=1e-5)))
 return ranks

def train_model(model:torch.nn.Module,x:torch.Tensor,y:torch.Tensor,t:torch.Tensor,sc:Mapping[str,Any],seed:int)->dict[str,Any]:
 opt=torch.optim.Adam(model.parameters(),lr=sc['learning_rate']);gen=torch.Generator(device=x.device).manual_seed(seed+99);losses=[]
 for step in range(sc['steps']):
  ix=torch.randint(0,len(x),(sc['batch_size'],),generator=gen,device=x.device);pred=model(x[ix],t[ix]);loss=F.mse_loss(pred,y[ix])
  if not torch.isfinite(loss):raise FloatingPointError('nonfinite training loss')
  opt.zero_grad(set_to_none=True);loss.backward();opt.step()
  if step in {0,sc['steps']-1}:losses.append(float(loss.detach().cpu()))
 return {'initial_loss':losses[0],'final_loss':losses[-1],'steps':sc['steps'],'parameters':sum(p.numel() for p in model.parameters())}

def fit_methods(rows:Sequence[Mapping[str,Any]],instance:int,c:Mapping[str,Any],device:torch.device,ckpt:Path)->tuple[list[Method],dict[str,Any]]:
 a=capacity_arrays(rows,instance,c);X=a['x'];Y=a['delta'];T=a['target'];d=c['dimension'];u,s,vh=svd_canonical(X.astype(np.float64),full_matrices=False);cond=float(s[0]/s[-1])
 if s[-1]<=c['generator']['sample_singular_min'] or cond>=c['generator']['sample_condition_max']:raise RuntimeError(f'train conditioning failed {s[-1]} {cond}')
 W=np.linalg.pinv(X.astype(np.float64),rcond=c['methods']['svd_rtol'])@Y.astype(np.float64);pred=X@W
 if np.max(np.abs(pred-Y))>c['generator']['sample_atol']:raise RuntimeError('closed form row recovery failed')
 methods=[Method('exact_delta_gt','exact_delta_gt','exact',None),Method('observed_input_transplant','observed_input_transplant','input',None),Method('closed_form_linear_full64','closed_form_linear_full64','matrix',W.astype(np.float32),rank=64)]
 _,_,vhy=svd_canonical(pred.astype(np.float64),full_matrices=False)
 for k in c['ranks']:
  Vk=vhy[:k].T;methods.append(Method(f'reduced_rank_regression_rank{k}',f'reduced_rank_regression_rank{k}','matrix',(W@Vk@Vk.T).astype(np.float32),rank=k))
 mu=X.mean(0);_,_,vpx=svd_canonical(X-mu,full_matrices=False)
 for k in c['ranks']:
  P=vpx[:k].T@vpx[:k];methods.append(Method(f'unpaired_pca_rank{k}',f'unpaired_pca_rank{k}','pca',(mu.astype(np.float32),P.astype(np.float32)),rank=k))
 methods.append(Method('label_only','label_only','label_mean',np.stack([Y[T==q].mean(0) for q in range(c['targets'])]).astype(np.float32)))
 rg=rng(c['methods']['permutation_seed'],instance);Xp=X.copy()
 for q in range(c['targets']):
  ix=np.flatnonzero(T==q);Xp[ix]=X[rg.permutation(ix)]
 Wp=np.linalg.pinv(Xp.astype(np.float64),rcond=c['methods']['svd_rtol'])@Y.astype(np.float64);methods.append(Method('within_target_delta_permutation','within_target_delta_permutation','matrix',Wp.astype(np.float32)))
 methods.append(Method('zero','zero','zero',None))
 for k in c['ranks']:
  q=qr_canonical(rng(c['methods']['random_seed'],instance,k).normal(size=(d,d)))[:,:k];methods.append(Method(f'random_rank{k}',f'random_rank{k}','matrix',(q@q.T).astype(np.float32),rank=k))
 xt=torch.tensor(X,dtype=torch.float32,device=device);yt=torch.tensor(Y,dtype=torch.float32,device=device);tt=torch.tensor(T,dtype=torch.long,device=device);fits={}
 ckpt.mkdir(parents=True,exist_ok=False)
 for family,cls,ranks in [('paired_linear',FactorLinear,c['ranks']),('target_linear',TargetLinear,c['methods']['target_linear']['ranks']),('target_nonlinear',TargetMLP,c['methods']['target_nonlinear']['ranks'])]:
  sc=c['methods'][family]
  for k in ranks:
   for sd in sc['seeds']:
    model=cls(d,k,sd,device) if cls is FactorLinear else (cls(d,k,c['targets'],sd,device) if cls is TargetLinear else cls(d,k,c['targets'],sc['hidden'],sd,device))
    rec=train_model(model,xt,yt,tt,sc,sd+instance+k);name=f'{family}_rank{k}_seed{sd}';extra:dict[str,Any]={}
    if family=='paired_linear':
     mat=(model.u@model.v).detach().cpu().numpy();extra={'effective_rank':int(np.linalg.matrix_rank(mat))}
    elif family=='target_linear':
     mats=torch.bmm(model.u,model.v).detach().cpu().numpy();extra={'per_target_ranks':[int(np.linalg.matrix_rank(x)) for x in mats],'union_rank':int(np.linalg.matrix_rank(np.concatenate(mats,axis=0)))}
    else:
     jr=empirical_jacobian_ranks(model,xt,tt,c['targets'],device)
     extra={'empirical_jacobian_ranks':jr,'empirical_jacobian_union_rank':int(max(jr))}
    path=ckpt/f'{name}.pt';torch.save({'state_dict':model.state_dict(),'config':dict(sc),'resolved_capacity_config_sha256':sha(CAP_CFG),'train_row_ids_sha256':hashlib.sha256(canon([r['row_id'] for r in rows])).hexdigest(),'instance':instance,'rank':k,'diagnostics':extra},path);fits[name]={**rec,**extra,'sha256':sha(path),'rank':k,'seed':sd};methods.append(Method(name,f'{family}_rank{k}',family,model,sd,k,parameter_count=rec['parameters'],effective_rank=extra))
 for method in methods:method.train_basis=vhy.copy()
 return methods,{'condition':cond,'smallest_singular':float(s[-1]),'closed_form_max_abs':float(np.max(np.abs(pred-Y))),'fits':fits,'information_access':c['fit_information'],'capacity_config_sha256':sha(CAP_CFG),'train_row_ids_sha256':hashlib.sha256(canon([r['row_id'] for r in rows])).hexdigest()}

def predict(m:Method,a:Mapping[str,Any],device:torch.device)->tuple[np.ndarray,np.ndarray]:
 X,XS,T=a['x'],a['x_sham'],a['target']
 if m.kind=='exact':return a['delta'],a['delta_sham']
 if m.kind=='input':return X,XS
 if m.kind=='matrix':return X@m.payload,XS@m.payload
 if m.kind=='pca':mu,P=m.payload;return mu+(X-mu)@P,mu+(XS-mu)@P
 if m.kind=='label_mean':q=m.payload[T];return q,q.copy()
 if m.kind=='zero':return np.zeros_like(X),np.zeros_like(XS)
 with torch.no_grad():
  x=torch.tensor(X,dtype=torch.float32,device=device);xs=torch.tensor(XS,dtype=torch.float32,device=device);t=torch.tensor(T,dtype=torch.long,device=device)
  return m.payload(x,t).cpu().numpy(),m.payload(xs,t).cpu().numpy()

def eval_methods(rows:Sequence[Mapping[str,Any]],instance:int,c:Mapping[str,Any],models:Sequence[Method],stage:str,device:torch.device)->dict[str,Any]:
 a=capacity_arrays(rows,instance,c);out={}
 for m in models:
  p,ps=predict(m,a,device);pm,ok=norm_match(p,a['delta']);psm,oks=norm_match(ps,a['delta'])
  native=score_prediction(m.name,p,ps,a,rows,c,stage,'native',True);matched=score_prediction(m.name,pm,psm,a,rows,c,stage,'matched',bool(np.all(ok&oks)))
  dm=direction_metrics(p,a['delta'],m.train_basis,m.rank);direction_pass=dm['finite'] and (m.name not in {'exact_delta_gt','closed_form_linear_full64'} or (dm['cosine']>=c['direction_gates']['cosine_min'] and dm['relative_l2']<=c['direction_gates']['relative_l2_max']))
  out[m.name]={'family':m.family,'seed':m.seed,'rank':m.rank,'parameter_count':m.parameter_count,'effective_rank':m.effective_rank,'direction':dm,'native':native,'matched':matched,'direction_pass':direction_pass,'all_gates_pass':bool(native['all_gates_pass'] and matched['all_gates_pass'] and direction_pass)}
 families={}
 for family in sorted(set(x.family for x in models)):
  names=[x.name for x in models if x.family==family];families[family]=bool(names and all(out[n]['all_gates_pass'] for n in names))
 return {'stage':stage,'instance':instance,'methods':out,'family_pass_every_seed':families,'technical_valid':all(np.isfinite(x['direction']['cosine']) for x in out.values())}

def external_rows(stage:str,c:Mapping[str,Any],blocks:int|None=None,rows_per:int|None=None,seed:int|None=None)->list[dict[str,Any]]:
 pc=c['panels'][stage] if stage in c['panels'] else {'blocks':blocks,'rows_per_block':rows_per,'seed':seed};B=int(blocks or pc['blocks']);R=int(rows_per or pc['rows_per_block']);S=int(seed or pc['seed']);V=c['model']['vocab'];slots=c['model']['slots'];rows=[]
 for b in range(B):
  for r in range(R):
   ix=b*R+r;q=ix%slots;t=ix%V;cycle=ix//V;off=1+cycle%(V-1);hoff=1+(cycle+11)%(V-1)
   if hoff==off:hoff=1+(hoff%(V-1))
   co=(t+off)%V;sh=(t+hoff)%V
   rr=rng('external_row',S,b,r);vals=rr.integers(0,V,size=slots).tolist();vals[q]=t;cor=vals.copy();cor[q]=co;sv=vals.copy();sv[q]=sh;rs=seed32('external',S,b,r)
   rows.append({'row_id':f'ext-{stage}-{b:04d}-{r:03d}-{rs:08x}','row_seed':rs,'stage':stage,'block':b,'query':q,'target':t,'contrast':co,'sham':sh,'clean_values':vals,'corrupt_values':cor,'sham_values':sv})
 return rows

class CopyTransformer(torch.nn.Module):
 def __init__(self,c:Mapping[str,Any],seed:int,device:torch.device):
  super().__init__();torch.manual_seed(seed);m=c['model'];d=m['width'];self.pos=torch.nn.Embedding(m['slots'],d,device=device);self.query=torch.nn.Embedding(m['slots'],d,device=device);self.value=torch.nn.Embedding(m['vocab'],d,device=device);self.q=torch.nn.Linear(d,d,bias=False,device=device);self.k=torch.nn.Linear(d,d,bias=False,device=device);self.v=torch.nn.Linear(d,d,bias=False,device=device);self.readout=torch.nn.Linear(d,m['vocab'],bias=False,device=device);self.eps=m['layernorm_eps']
 def forward(self,values:torch.Tensor,query:torch.Tensor,head_override:torch.Tensor|None=None)->dict[str,torch.Tensor]:
  B,S=values.shape;pos=torch.arange(S,device=values.device);q=self.q(self.query(query));k=self.k(self.pos(pos))[None,:,:].expand(B,-1,-1);vv=self.v(self.value(values));w=torch.softmax(torch.einsum('bd,bsd->bs',q,k)/math.sqrt(q.shape[1]),dim=1);head=torch.einsum('bs,bsd->bd',w,vv);use=head if head_override is None else head_override;logits=self.readout(F.layer_norm(use,(use.shape[1],),eps=self.eps));return {'logits':logits,'head':head,'weights':w,'values':vv}

def rows_tensors(rows:Sequence[Mapping[str,Any]],device:torch.device,key:str='clean_values')->tuple[torch.Tensor,torch.Tensor,torch.Tensor]:
 return torch.tensor([r[key] for r in rows],dtype=torch.long,device=device),torch.tensor([r['query'] for r in rows],dtype=torch.long,device=device),torch.tensor([r['target'] if key=='clean_values' else (r['contrast'] if key=='corrupt_values' else r['sham']) for r in rows],dtype=torch.long,device=device)
def train_copy(rows:Sequence[Mapping[str,Any]],c:Mapping[str,Any],seed:int,device:torch.device,out:Path)->dict[str,Any]:
 model=CopyTransformer(c,seed,device);tr=c['training'];opt=torch.optim.AdamW(model.parameters(),lr=tr['learning_rate'],weight_decay=tr['weight_decay']);gen=torch.Generator(device=device).manual_seed(tr['sampling_seed_offset']+seed);clean,q,yt=rows_tensors(rows,device,'clean_values');cor,_,yc=rows_tensors(rows,device,'corrupt_values');losses=[]
 for step in range(tr['steps']):
  ix=torch.randint(0,len(rows),(tr['batch_size'],),generator=gen,device=device);lc=model(clean[ix],q[ix])['logits'];lr=model(cor[ix],q[ix])['logits'];loss=F.cross_entropy(lc,yt[ix])+F.cross_entropy(lr,yc[ix]);
  if not torch.isfinite(loss):raise FloatingPointError('copy nonfinite')
  opt.zero_grad(set_to_none=True);loss.backward();torch.nn.utils.clip_grad_norm_(model.parameters(),tr['grad_clip']);opt.step()
  if step in {0,tr['steps']-1}:losses.append(float(loss.detach().cpu()))
 torch.save({'state_dict':model.state_dict(),'seed':seed,'model_config':c['model'],'training_config':c['training'],'resolved_external_config_sha256':sha(EXT_CFG),'train_row_ids_sha256':hashlib.sha256(canon([r['row_id'] for r in rows])).hexdigest()},out)
 return {'model':model,'initial_loss':losses[0],'final_loss':losses[-1],'checkpoint_sha256':sha(out)}

def external_metric_summary(values:Mapping[str,np.ndarray],eligible:np.ndarray,rows:Sequence[Mapping[str,Any]],c:Mapping[str,Any],tag:str)->tuple[dict[str,Any],dict[str,bool]]:
 blocks=np.array([r['block'] for r in rows]);summaries={k:interval(v[eligible],blocks[eligible],c,f'{tag}:{k}') for k,v in values.items()};decisions={k:gate(k,summaries[k],c['gates']) for k in c['gates']};return summaries,decisions

def score_copy_model(model:CopyTransformer,rows:Sequence[Mapping[str,Any]],c:Mapping[str,Any],seed:int,stage:str,device:torch.device)->dict[str,Any]:
 clean,q,t=rows_tensors(rows,device,'clean_values');cor,_,co=rows_tensors(rows,device,'corrupt_values');sham,_,_=rows_tensors(rows,device,'sham_values')
 with torch.no_grad():
  oc=model(clean,q);or_=model(cor,q);os=model(sham,q)
  routing_exact=bool(torch.equal(oc['weights'],or_['weights']))
  head_clean_from_corrupt_routing=torch.einsum('bs,bsd->bd',or_['weights'],oc['values'])
  head_corrupt_from_clean_routing=torch.einsum('bs,bsd->bd',oc['weights'],or_['values'])
  qa_clean=bool(torch.allclose(head_clean_from_corrupt_routing,oc['head'],atol=c['routing_qa']['hybrid_atol'],rtol=c['routing_qa']['hybrid_rtol']))
  qa_corrupt=bool(torch.allclose(head_corrupt_from_clean_routing,or_['head'],atol=c['routing_qa']['hybrid_atol'],rtol=c['routing_qa']['hybrid_rtol']))
  delta=oc['head']-or_['head'];dsh=os['head']-or_['head'];patch=model(cor,q,or_['head']+delta)['logits'];sh=model(cor,q,or_['head']+dsh)['logits'];abl=model(clean,q,oc['head']-delta)['logits']
  controls=[]
  for i,row in enumerate(rows):
   g=torch.tensor(rng('external_control',seed,row['row_seed']).normal(size=delta.shape[1]),dtype=torch.float32,device=device);dv=delta[i];g-=torch.dot(g,dv)*dv/torch.clamp(torch.dot(dv,dv),min=1e-12);g*=torch.linalg.vector_norm(dv)/torch.clamp(torch.linalg.vector_norm(g),min=1e-12);controls.append(g)
  ctl_delta=torch.stack(controls);ctl=model(cor,q,or_['head']+ctl_delta)['logits']
 zc=or_['logits'].cpu().numpy();zh=oc['logits'].cpu().numpy();zp=patch.cpu().numpy();zs=sh.cpu().numpy();za=abl.cpu().numpy();zctl=ctl.cpu().numpy();tn=t.cpu().numpy();cn=co.cpu().numpy();blocks=np.array([r['block'] for r in rows]);margin_h=row_margin(zh,tn);margin_c=row_margin(zc,tn);den=margin_h-margin_c;scale=np.sqrt(np.mean((centered(zh)-centered(zc))**2,axis=1));e=c['eligibility']
 eligible=(np.argmax(zh,1)==tn)&(np.argmax(zc,1)==cn)&(den>e['effect_strict']);sd=np.where(den>1e-6,den,1);ss=np.where(scale>1e-6,scale,1);rec=(row_margin(zp,tn)-margin_c)/sd;sr=(row_margin(zs,tn)-margin_c)/sd;cr=(row_margin(zctl,tn)-margin_c)/sd;nec=(margin_h-row_margin(za,tn))/sd;fv=1-np.sqrt(np.mean((centered(zp)-centered(zh))**2,axis=1))/ss
 coll=[]
 for i in range(len(rows)):
  mask=np.ones(zh.shape[1],bool);mask[tn[i]]=False;mask[cn[i]]=False;coll.append(float(np.sqrt(np.mean((centered(zp)[i,mask]-centered(zh)[i,mask])**2))/ss[i]))
 vals={'recovery':rec,'sham_specificity':rec-sr,'control_margin':rec-cr,'collateral_error':np.array(coll),'necessity':nec,'full_vocab_recovery':fv};B=c['panels'][stage]['blocks'];per={str(b):int(np.sum(eligible&(blocks==b))) for b in range(B)};value_support={str(v):int(np.sum(eligible&(tn==v))) for v in range(c['model']['vocab'])};queries=np.array([r['query'] for r in rows]);query_support={str(v):int(np.sum(eligible&(queries==v))) for v in range(c['model']['slots'])};support=int(eligible.sum())>=e['minimum_eval_total'] and all(x>=e['minimum_per_block'] for x in per.values()) and all(x>=e['minimum_per_value_marginal'] for x in value_support.values()) and all(x>=e['minimum_per_query_marginal'] for x in query_support.values())
 summaries,decisions=external_metric_summary(vals,eligible,rows,c,f'{stage}:{seed}:exact') if support else ({},{})
 masks={}
 d=delta.shape[1]
 for name,mask in {'first_half':torch.arange(d,device=device)<d//2,'second_half':torch.arange(d,device=device)>=d//2,'alternating':torch.arange(d,device=device)%2==0}.items():
  with torch.no_grad():zm=model(cor,q,or_['head']+delta*mask[None,:])['logits'].cpu().numpy()
  masks[name]={'recovery_point':float(np.mean(((row_margin(zm,tn)-margin_c)/sd)[eligible])),'descriptive_only':True}
 exact_pass=bool(support and len(decisions)==len(c['gates']) and all(decisions.values()));routing_pass=routing_exact and qa_clean and qa_corrupt
 return {'seed':seed,'stage':stage,'clean_accuracy':float(np.mean(np.argmax(zh,1)==tn)),'corrupt_accuracy':float(np.mean(np.argmax(zc,1)==cn)),'eligible_total':int(eligible.sum()),'support_pass':bool(support),'per_block':per,'value_support':value_support,'query_support':query_support,'routing_qa':{'weights_exact':routing_exact,'clean_hybrid_pass':qa_clean,'corrupt_hybrid_pass':qa_corrupt,'all_pass':routing_pass},'metrics':summaries,'gate_decisions':decisions,'incomplete_masks':masks,'all_gates_pass':external_qualification(exact_pass,routing_pass,masks)}

def event(root:Path,index:int,state:str,**extra:Any)->None:atomic_json(root/'events'/f'{index:03d}_{state}.json',{'index':index,'state':state,'time_ns':time.time_ns(),**extra})
def safe_event(root:Path,index:int,state:str,**extra:Any)->None:
 p=root/'events'/f'{index:03d}_{state}.json'
 if p.exists():return
 try:event(root,index,state,**extra)
 except RuntimeError:
  if not p.exists():raise
def write_external_failure_if_unopened(reason:str)->None:
 ep=_ACTIVE_RUN.get('external_prov');eo=_ACTIVE_RUN.get('external_out')
 if ep is None or eo is None:return
 accessed=(ep/'events'/'021_ACCESS_MAY_HAVE_OCCURRED.json').exists()
 if not accessed:
  safe_event(ep,990,'PRECHECK_NO_ACCESS',reason=reason)
  final=eo/'final/result.json'
  if not final.exists():atomic_json(final,{'status':'BLOCKED_UNOPENED','capacity_authorized':False,'external_payload_accessed':False,'training_performed':False,'reason':reason})
  safe_event(ep,991,'EXTERNAL_BLOCKED_UNOPENED',reason=reason)
def signal_terminal(signum:int,_frame:Any)->None:
 reason=f'signal_{signum}'
 for key in ('capacity_prov','external_prov'):
  if key in _ACTIVE_RUN:safe_event(_ACTIVE_RUN[key],998,'TECHNICAL_SIGNAL_TERMINAL',reason=reason)
 write_external_failure_if_unopened(reason)
 raise SystemExit(128+signum)

def preservation_verify()->dict[str,Any]:
 x=loadj(PRESERVE);bad=[]
 for e in x['inventory']:
  p=ROOT/e['path'];
  if not p.is_file() or sha(p)!=e['sha256'] or p.stat().st_size!=e['bytes']:bad.append(e['path'])
 if bad:raise RuntimeError(f'preservation drift {bad[:3]}')
 return {'status':'PASS','files':len(x['inventory']),'manifest_sha256':sha(PRESERVE)}
def failure_preservation_verify()->dict[str,Any]:
 x=loadj(FAILURE_PRESERVE);bad=[]
 for e in x['inventory']:
  p=ROOT/e['path']
  if not p.is_file() or sha(p)!=e['sha256'] or p.stat().st_size!=e['bytes']:bad.append(e['path'])
 if bad:raise RuntimeError(f'v1 failure preservation drift {bad[:3]}')
 expected={'capacity_train_opened':True,'capacity_development_opened':True,'capacity_development_complete':False,'capacity_confirmation_opened':False,'capacity_final_exists':False,'external_access_may_have_occurred':False,'external_train_opened':False,'external_status':'BLOCKED_UNOPENED','external_payload_accessed':False,'external_training_performed':False}
 if x['facts']!=expected or x['partial_checkpoints']!=27:raise RuntimeError('v1 failure facts drift')
 return {'status':'PASS','files':len(x['inventory']),'partial_checkpoints':27,'manifest_sha256':sha(FAILURE_PRESERVE),'facts':x['facts']}
def _functions(path:Path)->dict[str,str]:
 tree=ast.parse(path.read_text());return {n.name:ast.dump(n,include_attributes=False) for n in tree.body if isinstance(n,(ast.FunctionDef,ast.ClassDef))}
def verify_parity()->dict[str,Any]:
 pairs=[]
 for oldp,newp in ((V1_CAP_CFG,CAP_CFG),(V1_EXT_CFG,EXT_CFG)):
  old,new=loadj(oldp),loadj(newp);old_science={k:v for k,v in old.items() if k not in {'namespace','runtime','recovery'}};new_science={k:v for k,v in new.items() if k not in {'namespace','runtime','recovery'}}
  if old_science!=new_science:raise RuntimeError(f'scientific config drift {newp}')
  if old['runtime']['prepared_root']!=new['runtime']['prepared_root']:raise RuntimeError('prepared payload root changed')
  pairs.append({'old':oldp.relative_to(ROOT).as_posix(),'new':newp.relative_to(ROOT).as_posix(),'scientific_sha256':hashlib.sha256(canon(old_science)).hexdigest(),'allowed_pointer_prefixes':['/namespace','/runtime','/recovery']})
 oldf,newf=_functions(V1_SOURCE),_functions(SCRIPT);scientific=['capacity_mats','make_capacity_rows','capacity_arrays','row_margin','centered','interval','gate','norm_match','direction_metrics','control_delta','score_prediction','FactorLinear','TargetLinear','TargetMLP','train_model','predict','eval_methods','external_rows','CopyTransformer','rows_tensors','train_copy','external_metric_summary','score_copy_model']
 drift=[name for name in scientific if oldf.get(name)!=newf.get(name)]
 if drift:raise RuntimeError(f'nonallowlisted source drift {drift}')
 old_tree=ast.parse(V1_SOURCE.read_text());new_tree=ast.parse(SCRIPT.read_text());is_torch_flat=lambda n:isinstance(n,ast.Attribute) and n.attr=='flatnonzero' and isinstance(n.value,ast.Name) and n.value.id=='torch';old_flat=any(is_torch_flat(n) for n in ast.walk(old_tree));new_flat=any(is_torch_flat(n) for n in ast.walk(new_tree));new_jac=any(isinstance(n,ast.Call) and isinstance(n.func,ast.Name) and n.func.id=='empirical_jacobian_ranks' for n in ast.walk(new_tree))
 if not old_flat or new_flat or not new_jac:raise RuntimeError('compatibility diff contract failed')
 return {'status':'PASS','config_pairs':pairs,'scientific_symbols_verified':scientific,'source_allowlist':{'compatibility':['first_true_index','empirical_jacobian_ranks','fit_methods jacobian call'],'recovery_lifecycle':['constants','preservation/parity/candidate/binding/freeze/main']},'v1_source_sha256':sha(V1_SOURCE),'r2_source_sha256':sha(SCRIPT)}
def paper_verify()->dict[str,Any]:
 sys.path.insert(0,str(ROOT/'scripts'));import verify_paper_claims as v
 ledger=loadj(ROOT/'reports/paper_claim_ledger_v1.json');paper=(ROOT/'PAPER.md').read_text();z=v.verify_claims(ledger,paper,ROOT);ids={x['id'] for x in ledger['claims']}
 if not set(f'C{i:03d}' for i in range(76,81))<=ids:raise RuntimeError('required paper claims absent')
 return z

def candidate_files()->list[Path]:return [PLAN,PLAN_REVIEW,PRESERVE,FAILURE_PRESERVE,ROOT/'scripts/preserve_capacity_external_validity_v1_failure.py',ROOT/'PAPER.md',ROOT/'reports/paper_claim_ledger_v1.json',CAP_CFG,EXT_CFG,SCRIPT,LAUNCHER,TEST]
def inventory(paths:Sequence[Path])->list[dict[str,Any]]:
 return [{'path':p.relative_to(ROOT).as_posix(),'bytes':p.stat().st_size,'sha256':sha(p)} for p in sorted(set(paths))]
def timed_smoke(device_name:str)->dict[str,Any]:
 device=torch.device(device_name);start=time.time();c=cfg('capacity');rows=make_capacity_rows(99991,'smoke',c,8,16,99992);a=capacity_arrays(rows,99991,c);X=a['x'].astype(np.float64);Y=a['delta'].astype(np.float64);W=np.linalg.pinv(X,rcond=c['methods']['svd_rtol'])@Y;_,_,vh=svd_canonical(X@W,full_matrices=False);rank_errors={str(k):float(np.mean((X@(W@vh[:k].T@vh[:k])-Y)**2)) for k in c['ranks']}
 ec=json.loads(json.dumps(cfg('external')));ec['training']['steps']=100;ec['training']['batch_size']=64;er=external_rows('smoke',ec,8,32,99994);tmp=Path('/tmp')/f'capacity_external_v1_smoke_{os.getpid()}.pt'
 if device.type=='cuda':torch.cuda.reset_peak_memory_stats(device)
 fit=train_copy(er,ec,99995,device,tmp);disk=tmp.stat().st_size;tmp.unlink()
 peak=int(torch.cuda.max_memory_allocated(device)) if device.type=='cuda' else 0
 return {'device':str(device),'wall_seconds':time.time()-start,'peak_gpu_bytes':peak,'checkpoint_bytes':disk,'projected_disk_bytes':disk*3+150_000_000,'rank_sweep_mse':rank_errors,'external_100_steps_final_loss':fit['final_loss']}

def compatibility_smoke(device_name:str)->dict[str,Any]:
 device=torch.device(device_name);c=json.loads(json.dumps(cfg('capacity')));c['ranks']=[4];c['methods']['paired_linear']['seeds']=[97101];c['methods']['target_linear']['seeds']=[97201];c['methods']['target_linear']['ranks']=[4];c['methods']['target_nonlinear']['seeds']=[97301];c['methods']['target_nonlinear']['ranks']=[4]
 for key in ('paired_linear','target_linear','target_nonlinear'):
  c['methods'][key]['steps']=2;c['methods'][key]['batch_size']=32
 rows=make_capacity_rows(97991,'smoke',c,16,16,97992);dev=make_capacity_rows(97991,'smoke',c,24,8,97993)
 with tempfile.TemporaryDirectory() as td:
  models,fit=fit_methods(rows,97991,c,device,Path(td)/'checkpoints');scored=eval_methods(dev,97991,c,models,'development',device)
 nonlinear=next(v for k,v in fit['fits'].items() if k.startswith('target_nonlinear_'));jr=nonlinear['empirical_jacobian_ranks']
 if len(jr)!=c['targets'] or any(not isinstance(x,int) or x<0 for x in jr):raise RuntimeError('all-target jacobian compatibility smoke failed')
 mask=torch.tensor([False,True,True],dtype=torch.bool,device=device)
 if first_true_index(mask)!=1:raise RuntimeError('first_true_index compatibility failed')
 return {'device':str(device),'all_target_jacobian_ranks':jr,'fit_families':sorted(set(m.family for m in models)),'scored_methods':len(scored['methods']),'technical_valid':scored['technical_valid'],'torch_version':torch.__version__,'numpy_version':np.__version__}

def candidate_preflight(write:bool=True,device_name:str='cpu')->dict[str,Any]:
 if 'VERDICT: SHIP' not in PLAN_REVIEW.read_text():raise RuntimeError('plan review not SHIP')
 pv=preservation_verify();fp=failure_preservation_verify();parity=verify_parity();pap=paper_verify();c=cfg('capacity');checks=[capacity_basis_check(x,c) for x in c['instances']]
 if not all(x['pass'] for x in checks):raise RuntimeError('basis check failed')
 rows=make_capacity_rows(99991,'smoke',c,4,16,99992);a=capacity_arrays(rows,99991,c);W=np.linalg.pinv(a['x'].astype(np.float64),rcond=c['methods']['svd_rtol'])@a['delta'].astype(np.float64);err=float(np.max(np.abs(a['x']@W-a['delta'])))
 if err>c['generator']['sample_atol']:raise RuntimeError(f'smoke OLS {err}')
 smoke=timed_smoke(device_name);compatibility={'cpu':compatibility_smoke('cpu')}
 if device_name!='cpu':compatibility['cuda']=compatibility_smoke(device_name)
 absent=[]
 for kind in ('capacity','external'):
  q=cfg(kind)
  for key in ('candidate_review','generator_lock','freeze','frozen_review','output_root','provenance_root'):
   p=rp(q,key);absent.append({'path':p.relative_to(ROOT).as_posix(),'absent':not p.exists()})
 extras=[ROOT/'reports/provenance/capacity_external_validity_v1_r2_REVIEW_BINDING.json',ROOT/'reports/provenance/capacity_external_validity_v1_r2_launcher_20260810r2.log']
 absent.extend({'path':p.relative_to(ROOT).as_posix(),'absent':not p.exists()} for p in extras)
 if not all(x['absent'] for x in absent):raise RuntimeError(f'r2 namespace preexists {[x for x in absent if not x["absent"]]}')
 result={'status':'PASS','preservation':pv,'failure_preservation':fp,'parity':parity,'paper':pap,'basis_checks':checks,'nonpanel_ols_max_abs':err,'timed_smoke':smoke,'compatibility_smoke':compatibility,'r2_absence_checks':absent,'scientific_payload_accessed':False,'files':inventory(candidate_files())}
 if write:
  for kind in ('capacity','external'):
   out=rp(cfg(kind),'candidate_root')
   if out.exists():shutil.rmtree(out)
   out.mkdir(parents=True);atomic_json(out/'CANDIDATE_PREFLIGHT.json',{**result,'kind':kind})
 return result

def mutation_suite()->dict[str,Any]:
 c=cfg('capacity');rows=make_capacity_rows(99991,'smoke',c,24,8,99992);a=capacity_arrays(rows,99991,c);checks={}
 bad=a['W'].copy();bad[0,0]+=.01;checks['basis_perturbation_detected']=bool(np.max(np.abs((np.eye(64)@a['M'])@bad-np.eye(64)))>c['generator']['basis_atol'])
 counts=lambda key:[sum(r[key]==v for r in rows) for v in range(c['targets'])];checks['capacity_exact_marginal_balance']=len(set(counts('target')))==1 and len(set(counts('contrast')))==1 and len(set(counts('sham')))==1
 checks['observed_swap_direction_detected']=direction_metrics(a['x'],a['delta'])['cosine']<c['direction_gates']['cosine_min']
 z=np.zeros_like(a['delta']);sm=score_prediction('zero',z,z,a,rows,c,'development','native',True);checks['zero_fails_with_metrics']=not sm['all_gates_pass'] and sm['support_pass'] and len(sm['metrics'])==len(c['gates'])
 instance_controls=[]
 for inst in c['instances']:
  tr=make_capacity_rows(inst,'train',c,32,16,99001);ev=make_capacity_rows(inst,'development',c,24,8,99002);ta=capacity_arrays(tr,inst,c);ea=capacity_arrays(ev,inst,c);W=np.linalg.pinv(ta['x'],rcond=c['methods']['svd_rtol'])@ta['delta'];exact=score_prediction('exact',ea['delta'],ea['delta_sham'],ea,ev,c,'development','native',True);ols=score_prediction('ols',ea['x']@W,ea['x_sham']@W,ea,ev,c,'development','native',True);dm=direction_metrics(ea['x']@W,ea['delta']);instance_controls.append(exact['all_gates_pass'] and ols['all_gates_pass'] and dm['cosine']>=c['direction_gates']['cosine_min'] and dm['relative_l2']<=c['direction_gates']['relative_l2_max'])
 checks['every_instance_exact_and_ols_pass']=all(instance_controls)
 tr=make_capacity_rows(99991,'train',c,32,16,99003);ta=capacity_arrays(tr,99991,c);T=ta['target'];Y=ta['delta'];X=ta['x'];q=qr_canonical(rng('mutation_random').normal(size=(64,64)))[:,:8];P=q@q.T;random_score=score_prediction('random8',a['x']@P,a['x_sham']@P,a,rows,c,'development','native',True);checks['random_fails_with_complete_metrics']=random_score['support_pass'] and len(random_score['metrics'])==len(c['gates']) and not random_score['all_gates_pass']
 rrr_zero=score_prediction('rrr_zero',z,z,a,rows,c,'development','native',True);checks['rrr_to_zero_detected']=rrr_zero['support_pass'] and not rrr_zero['all_gates_pass']
 means=np.stack([Y[T==v].mean(0) for v in range(c['targets'])]);label_score=score_prediction('label_only',means[a['target']],means[a['target']],a,rows,c,'development','native',True);rg=rng('mutation_perm');Xp=X.copy()
 for v in range(c['targets']):
  ix=np.flatnonzero(T==v);Xp[ix]=X[rg.permutation(ix)]
 Wp=np.linalg.pinv(Xp,rcond=c['methods']['svd_rtol'])@Y;perm_score=score_prediction('permutation',a['x']@Wp,a['x_sham']@Wp,a,rows,c,'development','native',True);checks['label_and_permutation_fail_joint']=not label_score['all_gates_pass'] and not perm_score['all_gates_pass'] and label_score['support_pass'] and perm_score['support_pass']
 ext=cfg('external');er=external_rows('smoke',ext,32,8,99993);marg=lambda key,n:[sum(r[key]==v for r in er) for v in range(n)];checks['external_exact_marginal_balance']=len(set(marg('target',ext['model']['vocab'])))==1 and len(set(marg('contrast',ext['model']['vocab'])))==1 and len(set(marg('sham',ext['model']['vocab'])))==1 and len(set(marg('query',ext['model']['slots'])))==1
 model=CopyTransformer(ext,99994,torch.device('cpu'));clean,q,_=rows_tensors(er,torch.device('cpu'),'clean_values');cor,_,_=rows_tensors(er,torch.device('cpu'),'corrupt_values');oc=model(clean,q);orr=model(cor,q);checks['routing_invariance_real']=bool(torch.equal(oc['weights'],orr['weights']));qbad=(q+1)%ext['model']['slots'];checks['routing_query_mutation_detected']=not bool(torch.equal(oc['weights'],model(cor,qbad)['weights']));wrong=torch.einsum('bs,bsd->bd',oc['weights'],oc['values']);checks['routing_formula_swap_detected']=not bool(torch.allclose(wrong,orr['head'],atol=ext['routing_qa']['hybrid_atol'],rtol=ext['routing_qa']['hybrid_rtol']))
 cap_stages=[make_capacity_rows(99991,s,c,2,16,seed) for s,seed in zip(('train','development','confirmation'),(99101,99102,99103))];ext_stages=[external_rows(s,ext,2,32,seed) for s,seed in zip(('train','development','confirmation'),(99201,99202,99203))];checks['cross_stage_ids_and_seeds_disjoint']=all(not ({x['row_id'] for x in cap_stages[i]}&{x['row_id'] for x in cap_stages[j]}) and not ({x['row_seed'] for x in cap_stages[i]}&{x['row_seed'] for x in cap_stages[j]}) and not ({x['row_id'] for x in ext_stages[i]}&{x['row_id'] for x in ext_stages[j]}) and not ({x['row_seed'] for x in ext_stages[i]}&{x['row_seed'] for x in ext_stages[j]}) for i in range(3) for j in range(i+1,3))
 checks['mask_qualification_invariant']=external_qualification(True,True,{'mask':{'recovery':1.0}}) and external_qualification(True,True,{'mask':{'recovery':0.0}}) and not external_qualification(False,True,{})
 with tempfile.TemporaryDirectory() as td:
  root=Path(td);prov=root/'prov';out=root/'out';prov.mkdir();out.mkdir();external_blocked(prov,out,{});checks['forced_stop_production_path']=not (prov/'events/021_ACCESS_MAY_HAVE_OCCURRED.json').exists() and loadj(out/'final/result.json')['status']=='BLOCKED_UNOPENED'
 with tempfile.TemporaryDirectory() as td:
  base=Path(td);cc=json.loads(json.dumps(c));ec=json.loads(json.dumps(ext));cc['runtime']['generator_lock']=str(base/'cap.lock');ec['runtime']['generator_lock']=str(base/'ext.lock');cc['runtime']['prepared_root']=str(base/'cap_prepared');ec['runtime']['prepared_root']=str(base/'ext_prepared');orig_cfg=cfg
  def fake_cfg(kind:str)->dict[str,Any]:return cc if kind=='capacity' else ec
  with mock.patch.object(sys.modules[__name__],'cfg',side_effect=fake_cfg):
   atomic_json(Path(cc['runtime']['generator_lock']),{'config_sha256':sha(CAP_CFG),'both_locks_before_payload':True,'candidate_manifests':[],'candidate_reviews':[]})
   failed=False
   try:prepare()
   except (FileNotFoundError,RuntimeError):failed=True
   checks['actual_prepare_blocks_missing_external_lock']=failed and not Path(cc['runtime']['prepared_root']).exists() and not Path(ec['runtime']['prepared_root']).exists()
  Path(cc['runtime']['generator_lock']).unlink();atomic_json(Path(ec['runtime']['generator_lock']),{'config_sha256':sha(EXT_CFG),'both_locks_before_payload':True,'candidate_manifests':[],'candidate_reviews':[]})
  with mock.patch.object(sys.modules[__name__],'cfg',side_effect=fake_cfg):
   failed=False
   try:prepare()
   except (FileNotFoundError,RuntimeError):failed=True
   checks['actual_prepare_blocks_missing_capacity_lock']=failed and not Path(cc['runtime']['prepared_root']).exists() and not Path(ec['runtime']['prepared_root']).exists()
 orig_read_text,orig_read_bytes,orig_stat,orig_glob=Path.read_text,Path.read_bytes,Path.stat,Path.glob
 def guard(method):
  def wrapped(self,*args,**kwargs):
   if self.suffix=='.jsonl' and ('capacity_controller_diagnostic_v1_prepared' in str(self) or 'trained_copy_external_v1_prepared' in str(self)):raise AssertionError(f'new payload accessed by prelock operation: {self}')
   return method(self,*args,**kwargs)
  return wrapped
 with mock.patch.object(Path,'read_text',guard(orig_read_text)),mock.patch.object(Path,'read_bytes',guard(orig_read_bytes)),mock.patch.object(Path,'stat',guard(orig_stat)),mock.patch.object(Path,'glob',guard(orig_glob)),mock.patch.object(sys.modules[__name__],'timed_smoke',return_value={'trapped_nonpanel_smoke':True}):
  candidate_preflight(write=False,device_name='cpu');payload_records_from_metadata({'panels':[{'path':'never-open.jsonl','sha256':'abc'}]});checks['candidate_and_freeze_payload_traps']=True
 env=dict(os.environ);env['MSAE_LAUNCH_DRY_RUN']='1';rendered=subprocess.check_output(['bash',str(LAUNCHER)],env=env,text=True);fd,tmp_name=tempfile.mkstemp(prefix='cev1_launcher_',suffix='.sh');os.close(fd);tmp=Path(tmp_name);tmp.write_text(rendered)
 try:syntax=subprocess.run(['bash','-n',str(tmp)],capture_output=True).returncode==0
 finally:tmp.unlink()
 checks['launcher_executed_set_u_render']=syntax and 'RUN_ROOT=$(readlink /proc/self/cwd)' in rendered and 'timeout --signal=TERM --kill-after=30s 8h' in rendered
 if not all(checks.values()):raise RuntimeError(checks)
 return {'status':'PASS','checks':checks,'scientific_payload_accessed':False}
def payload_creation_allowed(capacity_lock:bool,external_lock:bool)->bool:return bool(capacity_lock and external_lock)
def external_qualification(exact_pass:bool,routing_qa_pass:bool,_mask_results:Mapping[str,Any]|None=None)->bool:return bool(exact_pass and routing_qa_pass)
def payload_records_from_metadata(metadata:Mapping[str,Any])->list[dict[str,Any]]:return [{'path':x['path'],'sha256':x['sha256']} for x in metadata['panels']]
def launcher_render(uuid:str)->str:
 return f'export CUDA_VISIBLE_DEVICES="$PHYSICAL_INDEX"\n[[ "$GPU_UUID" == "{uuid}" ]]\ncd "$ROOT"\nRUN_ROOT=$(readlink /proc/self/cwd)\nMSAE_ROOT="$RUN_ROOT" python "$RUN_ROOT/scripts/capacity_external_validity_v1_r2.py" run-pipeline --physical-index "$PHYSICAL_INDEX" --gpu-uuid "$GPU_UUID" --launch-token "$TOKEN"'

def verify_review(path:Path,candidate_manifest:Path|None=None)->dict[str,Any]:
 txt=path.read_text();
 if 'VERDICT: SHIP' not in txt:raise RuntimeError(f'review not SHIP {path}')
 if candidate_manifest is not None and sha(candidate_manifest) not in txt:raise RuntimeError(f'review lacks manifest hash {sha(candidate_manifest)}')
 return {'path':path.relative_to(ROOT).as_posix(),'sha256':sha(path)}
def verify_candidate_manifest(p:Path)->dict[str,Any]:
 x=loadj(p);bad=[]
 for e in x['files']:
  q=ROOT/e['path']
  if not q.is_file() or q.stat().st_size!=e['bytes'] or sha(q)!=e['sha256']:bad.append(e['path'])
 if bad:raise RuntimeError(f'reviewed candidate drift {bad[:3]}')
 return {'path':p.relative_to(ROOT).as_posix(),'sha256':sha(p),'files':len(x['files'])}
def create_locks()->dict[str,Any]:
 cc,ec=cfg('capacity'),cfg('external');cp=rp(cc,'candidate_root')/'CANDIDATE_PREFLIGHT.json';ep=rp(ec,'candidate_root')/'CANDIDATE_PREFLIGHT.json'
 if not cp.is_file() or not ep.is_file():raise RuntimeError('both candidate manifests required')
 cm=verify_candidate_manifest(cp);em=verify_candidate_manifest(ep);cr=verify_review(rp(cc,'candidate_review'),cp);er=verify_review(rp(ec,'candidate_review'),ep)
 if rp(cc,'generator_lock').exists() or rp(ec,'generator_lock').exists():raise RuntimeError('lock exists')
 failure=failure_preservation_verify();v1={'capacity_lock_sha256':sha(ROOT/'configs/capacity_controller_diagnostic_v1/GENERATOR_LOCK.json'),'external_lock_sha256':sha(ROOT/'configs/trained_copy_external_v1/GENERATOR_LOCK.json'),'capacity_freeze_sha256':sha(ROOT/'configs/capacity_controller_diagnostic_v1/FREEZE.json'),'external_freeze_sha256':sha(ROOT/'configs/trained_copy_external_v1/FREEZE.json'),'v1_review_binding_sha256':sha(ROOT/'reports/provenance/capacity_external_validity_v1_REVIEW_BINDING.json')}
 shared={'created_ns':time.time_ns(),'candidate_reviews':[cr,er],'candidate_manifests':[cm,em],'payloads_preexisting':True,'recovery_binding':True,'both_bindings_before_r2_access':True,'failure_preservation_sha256':failure['manifest_sha256'],'v1_lineage':v1,'v1_partial_checkpoints_reused':False}
 atomic_json(rp(cc,'generator_lock'),{'schema_version':'capacity_recovery_binding_v1_r2',**shared,'config_sha256':sha(CAP_CFG)});atomic_json(rp(ec,'generator_lock'),{'schema_version':'external_recovery_binding_v1_r2',**shared,'config_sha256':sha(EXT_CFG)})
 return {'status':'PASS','capacity_lock':sha(rp(cc,'generator_lock')),'external_lock':sha(rp(ec,'generator_lock'))}
def locks_valid()->None:
 cc,ec=cfg('capacity'),cfg('external')
 for c,p in [(cc,CAP_CFG),(ec,EXT_CFG)]:
  x=loadj(rp(c,'generator_lock'))
  if x.get('config_sha256')!=sha(p) or not x.get('payloads_preexisting') or not x.get('recovery_binding') or not x.get('both_bindings_before_r2_access') or x.get('v1_partial_checkpoints_reused') is not False:raise RuntimeError('invalid recovery binding')
  if x.get('failure_preservation_sha256')!=sha(FAILURE_PRESERVE):raise RuntimeError('failure preservation binding drift')
  for rec in x.get('candidate_manifests',[]):
   q=ROOT/rec['path']
   if sha(q)!=rec['sha256']:raise RuntimeError('candidate manifest drift after lock')
   verify_candidate_manifest(q)
  for rec in x.get('candidate_reviews',[]):
   if sha(ROOT/rec['path'])!=rec['sha256']:raise RuntimeError('candidate review drift after lock')

def support(rows:Sequence[Mapping[str,Any]],blocks:int,rows_per:int)->dict[str,Any]:
 ids=[x['row_id'] for x in rows];return {'rows':len(rows),'unique_row_ids':len(set(ids)),'blocks':len(set(x['block'] for x in rows)),'rows_per_block':{str(b):sum(x['block']==b for x in rows) for b in range(blocks)},'pass':len(rows)==blocks*rows_per and len(ids)==len(set(ids))}
def prepare()->dict[str,Any]:
 locks_valid();cc,ec=cfg('capacity'),cfg('external');roots=[rp(cc,'prepared_root'),rp(ec,'prepared_root')]
 if any(x.exists() for x in roots):raise RuntimeError('prepared root exists')
 for x in roots:x.mkdir(parents=True)
 capmeta=[];allids=set()
 for inst in cc['instances']:
  for stage in ('train','development','confirmation'):
   rows=make_capacity_rows(inst,stage,cc);ids={x['row_id'] for x in rows}
   if allids&ids:raise RuntimeError('capacity split overlap')
   allids|=ids;p=rp(cc,'prepared_root')/f'instance_{inst}_{stage}.jsonl';write_jsonl(p,rows);capmeta.append({'instance':inst,'stage':stage,'path':p.relative_to(ROOT).as_posix(),'sha256':sha(p),'support':support(rows,cc['panels'][stage]['blocks'],cc['panels'][stage]['rows_per_block'])})
 extmeta=[];eids=set()
 for stage in ('train','development','confirmation'):
  rows=external_rows(stage,ec);ids={x['row_id'] for x in rows}
  if eids&ids:raise RuntimeError('external split overlap')
  eids|=ids;p=rp(ec,'prepared_root')/f'{stage}.jsonl';write_jsonl(p,rows);extmeta.append({'stage':stage,'path':p.relative_to(ROOT).as_posix(),'sha256':sha(p),'support':support(rows,ec['panels'][stage]['blocks'],ec['panels'][stage]['rows_per_block'])})
 atomic_json(rp(cc,'prepared_root')/'PANEL_METADATA.json',{'schema_version':'capacity_panel_metadata','panels':capmeta,'payload_opened':False});atomic_json(rp(ec,'prepared_root')/'PANEL_METADATA.json',{'schema_version':'external_panel_metadata','panels':extmeta,'payload_opened':False})
 atomic_json(rp(cc,'prepared_root')/'PREPARED.json',{'status':'PREPARED_UNOPENED','time_ns':time.time_ns()});atomic_json(rp(ec,'prepared_root')/'PREPARED.json',{'status':'PREPARED_UNOPENED','time_ns':time.time_ns()})
 return {'status':'PASS','capacity_panels':len(capmeta),'external_panels':len(extmeta)}
def freeze_one(kind:str)->dict[str,Any]:
 c=cfg(kind);p=CAP_CFG if kind=='capacity' else EXT_CFG;prep=rp(c,'prepared_root');metadata=loadj(prep/'PANEL_METADATA.json');payload=payload_records_from_metadata(metadata);base=[PLAN,PLAN_REVIEW,PRESERVE,FAILURE_PRESERVE,ROOT/'scripts/preserve_capacity_external_validity_v1_failure.py',p,SCRIPT,LAUNCHER,TEST,rp(c,'generator_lock'),prep/'PANEL_METADATA.json',prep/'PREPARED.json']
 access={'train':'PRIORLY_OPENED_TECHNICAL_RECOVERY','development':'PRIORLY_OPENED_TECHNICAL_RECOVERY','confirmation':'UNOPENED'} if kind=='capacity' else {'train':'UNOPENED','development':'UNOPENED','confirmation':'UNOPENED'}
 f=rp(c,'freeze');atomic_json(f,{'schema_version':f'{kind}_recovery_freeze_v1_r2','status':'FROZEN_PANEL_SPECIFIC_RECOVERY','kind':kind,'panel_access_state':access,'payloads_preexisting':True,'recovery_binding_sha256':sha(rp(c,'generator_lock')),'failure_preservation_sha256':sha(FAILURE_PRESERVE),'v1_partial_checkpoints_reused':False,'inventory':inventory(base),'payloads':payload,'payload_hash_source':'existing v1 PANEL_METADATA.json; r2 freeze did not stat/glob/hash/read payloads','created_ns':time.time_ns()});return {'kind':kind,'sha256':sha(f),'files':len(base)}
def freeze_both()->dict[str,Any]:
 locks_valid()
 if rp(cfg('capacity'),'freeze').exists() or rp(cfg('external'),'freeze').exists():raise RuntimeError('freeze exists')
 return {'status':'PASS','freezes':[freeze_one('capacity'),freeze_one('external')]}
def verify_freeze(kind:str)->dict[str,Any]:
 c=cfg(kind);f=loadj(rp(c,'freeze'));bad=[]
 for e in f['inventory']:
  p=ROOT/e['path']
  if not p.is_file() or sha(p)!=e['sha256'] or p.stat().st_size!=e['bytes']:bad.append(e['path'])
 if bad:raise RuntimeError(f'{kind} freeze drift {bad[:3]}')
 return {'kind':kind,'status':'PASS','freeze_sha256':sha(rp(c,'freeze')),'files':len(f['inventory']),'payloads_opened':False}
def bind_reviews()->dict[str,Any]:
 rows=[]
 for kind in ('capacity','external'):
  c=cfg(kind);fr=rp(c,'freeze');review=rp(c,'frozen_review');verify_review(review,fr);rows.append({'kind':kind,'freeze_sha256':sha(fr),'review_path':review.relative_to(ROOT).as_posix(),'review_sha256':sha(review)})
 out=rp(cfg('capacity'),'provenance_root').parent/'capacity_external_validity_v1_r2_REVIEW_BINDING.json';atomic_json(out,{'schema_version':'capacity_external_review_binding','reviews':rows,'created_ns':time.time_ns()});return {'status':'PASS','path':out.relative_to(ROOT).as_posix(),'sha256':sha(out)}
def binding_path()->Path:return rp(cfg('capacity'),'provenance_root').parent/'capacity_external_validity_v1_r2_REVIEW_BINDING.json'
def verify_binding()->dict[str,Any]:
 x=loadj(binding_path())
 for e in x['reviews']:
  c=cfg(e['kind'])
  if sha(rp(c,'freeze'))!=e['freeze_sha256'] or sha(ROOT/e['review_path'])!=e['review_sha256']:raise RuntimeError('review binding drift')
 return {'status':'PASS','sha256':sha(binding_path())}
def gpu_validate(index:int,uuid:str)->torch.device:
 line=subprocess.check_output(['nvidia-smi','--query-gpu=index,uuid','--format=csv,noheader,nounits','-i',str(index)],text=True).strip();a,b=[x.strip() for x in line.split(',')]
 if int(a)!=index or b!=uuid:raise RuntimeError(f'GPU mismatch {line}')
 if os.environ.get('CUDA_VISIBLE_DEVICES')!=str(index):raise RuntimeError('CUDA_VISIBLE_DEVICES does not match physical index')
 if not torch.cuda.is_available() or torch.cuda.device_count()!=1:raise RuntimeError('CUDA visibility not exactly one')
 return torch.device('cuda:0')
def launch_preflight(index:int,uuid:str)->dict[str,Any]:
 for k in ('capacity','external'):verify_freeze(k)
 verify_binding();cc,ec=cfg('capacity'),cfg('external')
 for c in (cc,ec):
  if rp(c,'output_root').exists() or rp(c,'provenance_root').exists():raise RuntimeError('result/provenance namespace exists')
 return {'status':'PASS','physical_index':index,'gpu_uuid':uuid}

def open_rows(kind:str,stage:str,instance:int|None=None)->list[dict[str,Any]]:
 c=cfg(kind);name=f'instance_{instance}_{stage}.jsonl' if kind=='capacity' else f'{stage}.jsonl';p=rp(c,'prepared_root')/name;f=loadj(rp(c,'freeze'));rec=next(x for x in f['payloads'] if x['path']==p.relative_to(ROOT).as_posix())
 if sha(p)!=rec['sha256']:raise RuntimeError('payload drift')
 return read_jsonl(p)
def capacity_pipeline(device:torch.device,prov:Path,out:Path)->dict[str,Any]:
 c=cfg('capacity');event(prov,10,'CAPACITY_TRAIN_OPENED');train={i:open_rows('capacity','train',i) for i in c['instances']};event(prov,11,'CAPACITY_DEVELOPMENT_OPENED');dev={i:open_rows('capacity','development',i) for i in c['instances']}
 summaries={};models={};fits={}
 for inst in c['instances']:
  m,fit=fit_methods(train[inst],inst,c,device,out/'checkpoints'/str(inst));models[inst]=m;fits[str(inst)]=fit;summaries.setdefault(str(inst),{})['development']=eval_methods(dev[inst],inst,c,m,'development',device)
 event(prov,12,'CAPACITY_DEVELOPMENT_COMPLETE');event(prov,13,'CAPACITY_CONFIRMATION_OPENED');conf={i:open_rows('capacity','confirmation',i) for i in c['instances']}
 for inst in c['instances']:summaries[str(inst)]['confirmation']=eval_methods(conf[inst],inst,c,models[inst],'confirmation',device)
 required=('exact_delta_gt','closed_form_linear_full64');auth=True
 for inst in c['instances']:
  for st in ('development','confirmation'):
   rec=summaries[str(inst)][st];auth &= rec['technical_valid'] and all(rec['methods'][m]['all_gates_pass'] for m in required)
 all_families=sorted(set(f for rec in summaries.values() for st in rec.values() for f in st['family_pass_every_seed']))
 family_all={f:all(summaries[str(inst)][st]['family_pass_every_seed'].get(f,False) for inst in c['instances'] for st in ('development','confirmation')) for f in all_families}
 freeze=loadj(rp(c,'freeze'));lineage={'capacity_config_sha256':sha(CAP_CFG),'external_config_sha256':sha(EXT_CFG),'capacity_freeze_sha256':sha(rp(c,'freeze')),'external_freeze_sha256':sha(rp(cfg('external'),'freeze')),'panel_hashes':freeze['payloads'],'review_binding_sha256':sha(binding_path())}
 final={'schema_version':'capacity_controller_diagnostic_v1_final','status':'CAPACITY_DIAGNOSTIC_COMPLETE','external_authorized':bool(auth),'instances':summaries,'family_pass_all_instances_both_panels':family_all,'fits':fits,'lineage':lineage,'scope':c['scope']};atomic_json(out/'final/result.json',final);event(prov,14,'CAPACITY_COMPLETE',external_authorized=bool(auth),final_sha256=sha(out/'final/result.json'));return final

def external_blocked(prov:Path,out:Path,cap:Mapping[str,Any])->None:
 atomic_json(out/'final/result.json',{'status':'BLOCKED_UNOPENED','capacity_authorized':False,'external_payload_accessed':False,'training_performed':False});event(prov,21,'EXTERNAL_BLOCKED_UNOPENED')
def external_pipeline(device:torch.device,prov:Path,out:Path,cap:Mapping[str,Any])->None:
 event(prov,20,'PRECHECK_NO_ACCESS',capacity_final_sha256=sha(rp(cfg('capacity'),'output_root')/'final/result.json'))
 if not cap['external_authorized']:external_blocked(prov,out,cap);return
 event(prov,21,'ACCESS_MAY_HAVE_OCCURRED');c=cfg('external');train=open_rows('external','train');event(prov,22,'EXTERNAL_TRAIN_OPENED');(out/'checkpoints').mkdir(parents=True,exist_ok=False);fits={};models={}
 for sd in c['model']['seeds']:
  z=train_copy(train,c,sd,device,out/'checkpoints'/f'model_seed{sd}.pt');models[sd]=z.pop('model');fits[str(sd)]=z
 # The scientific external scorer is deliberately conditional and writes a bounded technical result if model eligibility is not reached.
 event(prov,23,'EXTERNAL_DEVELOPMENT_OPENED');dev=open_rows('external','development');development={str(sd):score_copy_model(models[sd],dev,c,sd,'development',device) for sd in c['model']['seeds']};event(prov,24,'EXTERNAL_DEVELOPMENT_COMPLETE')
 event(prov,25,'EXTERNAL_CONFIRMATION_OPENED');conf=open_rows('external','confirmation');confirmation={str(sd):score_copy_model(models[sd],conf,c,sd,'confirmation',device) for sd in c['model']['seeds']}
 qualified=all(development[str(sd)]['all_gates_pass'] and confirmation[str(sd)]['all_gates_pass'] for sd in c['model']['seeds'])
 result={'schema_version':'trained_copy_external_v1_final','status':'TRAINED_COPY_EXTERNAL_QUALIFIED' if qualified else 'TRAINED_COPY_EXTERNAL_NOT_QUALIFIED','training_performed':True,'payload_accessed':True,'fits':fits,'development':development,'confirmation':confirmation,'all_seeds_both_panels_pass':qualified,'scope':c['scope']};atomic_json(out/'final/result.json',result);event(prov,26,'EXTERNAL_TERMINAL',status=result['status'],final_sha256=sha(out/'final/result.json'))
def run_pipeline(index:int,uuid:str,token:str)->None:
 launch_preflight(index,uuid);device=gpu_validate(index,uuid);torch.use_deterministic_algorithms(True);torch.manual_seed(cfg('capacity')['seed']);np.random.seed(cfg('capacity')['seed']);random.seed(cfg('capacity')['seed']);cc,ec=cfg('capacity'),cfg('external');cp,ep=rp(cc,'provenance_root'),rp(ec,'provenance_root');co,eo=rp(cc,'output_root'),rp(ec,'output_root')
 for p in (cp,ep,co,eo):p.mkdir(parents=True,exist_ok=False)
 _ACTIVE_RUN.update({'capacity_prov':cp,'external_prov':ep,'capacity_out':co,'external_out':eo})
 signal.signal(signal.SIGTERM,signal_terminal);signal.signal(signal.SIGINT,signal_terminal)
 atomic_json(cp/'LAUNCH.json',{'physical_index':index,'gpu_uuid':uuid,'launch_token_sha256':hashlib.sha256(token.encode()).hexdigest(),'time_ns':time.time_ns(),'freeze_sha256':sha(rp(cc,'freeze'))});atomic_json(ep/'LAUNCH.json',{'physical_index':index,'gpu_uuid':uuid,'launch_token_sha256':hashlib.sha256(token.encode()).hexdigest(),'time_ns':time.time_ns(),'freeze_sha256':sha(rp(ec,'freeze'))})
 try:
  cap=capacity_pipeline(device,cp,co);external_pipeline(device,ep,eo,cap)
 except BaseException as e:
  write_external_failure_if_unopened(f'{type(e).__name__}: {e}')
  for p in (cp,ep):
   try:safe_event(p,999,'TECHNICAL_TERMINAL',error=f'{type(e).__name__}: {e}')
   except Exception:pass
  raise

def main()->None:
 ap=argparse.ArgumentParser();sp=ap.add_subparsers(dest='cmd',required=True)
 q=sp.add_parser('candidate-preflight');q.add_argument('--device',default='cpu');sp.add_parser('mutation-suite');sp.add_parser('verify-parity');q=sp.add_parser('launcher-render');q.add_argument('--gpu-uuid',required=True);sp.add_parser('create-recovery-bindings');sp.add_parser('freeze');q=sp.add_parser('verify-freezes');q.add_argument('--opaque',action='store_true');sp.add_parser('bind-reviews');sp.add_parser('verify-review-binding');q=sp.add_parser('launch-preflight');q.add_argument('--physical-index',type=int,required=True);q.add_argument('--gpu-uuid',required=True);q=sp.add_parser('run-pipeline');q.add_argument('--physical-index',type=int,required=True);q.add_argument('--gpu-uuid',required=True);q.add_argument('--launch-token',required=True)
 a=ap.parse_args()
 if a.cmd=='candidate-preflight':print(json.dumps(candidate_preflight(device_name=a.device),sort_keys=True))
 elif a.cmd=='mutation-suite':print(json.dumps(mutation_suite(),sort_keys=True))
 elif a.cmd=='verify-parity':print(json.dumps(verify_parity(),sort_keys=True))
 elif a.cmd=='launcher-render':print(launcher_render(a.gpu_uuid))
 elif a.cmd=='create-recovery-bindings':print(json.dumps(create_locks(),sort_keys=True))
 elif a.cmd=='freeze':print(json.dumps(freeze_both(),sort_keys=True))
 elif a.cmd=='verify-freezes':print(json.dumps({'status':'PASS','freezes':[verify_freeze('capacity'),verify_freeze('external')],'opaque':a.opaque},sort_keys=True))
 elif a.cmd=='bind-reviews':print(json.dumps(bind_reviews(),sort_keys=True))
 elif a.cmd=='verify-review-binding':print(json.dumps(verify_binding(),sort_keys=True))
 elif a.cmd=='launch-preflight':print(json.dumps(launch_preflight(a.physical_index,a.gpu_uuid),sort_keys=True))
 elif a.cmd=='run-pipeline':run_pipeline(a.physical_index,a.gpu_uuid,a.launch_token)
if __name__=='__main__':main()
