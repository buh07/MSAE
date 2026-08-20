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
CFG_PATH=ROOT/'configs/trained_copy_method_benchmark_v1/run.json'
PLAN=ROOT/'PLAN_TRAINED_COPY_METHOD_BENCHMARK_V1.md'
SCRIPT=Path(__file__).resolve()

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

def validate_config(c:Mapping[str,Any])->None:
 if c['scope']!={'synthetic_only':True,'counterfactual_donor_required':True,'pretrained_model':False,'natural_language_claim':False,'k2_evaluated':False,'copy_model_retraining':False}:raise RuntimeError('scope drift')
 if c['methods']['global_ranks']!=[4,8,16,32,64] or c['methods']['conditioned_ranks']!=[4,8,16,32]:raise RuntimeError('rank drift')
 pools=[set(c['panels'][s]['offsets']) for s in ('fit','development','confirmation')]
 if pools[0]!=set(range(1,22)) or pools[1]!=set(range(22,27)) or pools[2]!=set(range(27,32)) or any(pools[i]&pools[j] for i in range(3) for j in range(i)):raise RuntimeError('offset partition drift')
 if c['bootstrap']['draws']!=1000 or c['model']['seeds']!=[5101,5102,5103]:raise RuntimeError('bootstrap/model drift')
 for sd,rec in c['r5']['checkpoints'].items():
  p=ROOT/rec['path']
  if not p.is_file() or sha(p)!=rec['sha256']:raise RuntimeError(f'checkpoint lineage {sd}')
 for key in ('config','freeze','preservation'):
  p=ROOT/c['r5'][f'{key}_path']
  if not p.is_file() or sha(p)!=c['r5'][f'{key}_sha256']:raise RuntimeError(f'R5 {key} drift')

def panel_rows(stage:str,c:Mapping[str,Any],avoid_sham:set[tuple[int,int,int]]|None=None)->list[dict[str,Any]]:
 pc=c['panels'][stage];n=pc['blocks']*pc['rows_per_block'];pool=list(pc['offsets']);avoid=avoid_sham or set();rows=[]
 for ix in range(n):
  target=ix%c['model']['vocab'];cycle=ix//c['model']['vocab'];query=(target+cycle)%c['model']['slots'];off=pool[(target+2*cycle)%len(pool)];contrast=(target+off)%c['model']['vocab']
  choices=[]
  for j in range(1,len(pool)):
   so=pool[(target+2*cycle+j)%len(pool)];sham=(target+so)%c['model']['vocab'];tup=(query,contrast,sham)
   if tup not in avoid:choices.append((so,sham,tup))
  if not choices:raise RuntimeError(f'no sham choice {stage} {ix}')
  _,sham,_=choices[0];rs=seed32('trained_copy_methods',stage,pc['seed'],ix);g=rng('rows',rs);vals=g.integers(0,c['model']['vocab'],size=c['model']['slots']).tolist();vals[query]=target;cor=vals.copy();cor[query]=contrast;sv=vals.copy();sv[query]=sham
  rows.append({'row_id':f'tcm-{stage}-{ix:05d}-{rs:08x}','row_seed':rs,'stage':stage,'block':ix//pc['rows_per_block'],'query':query,'target':target,'contrast':contrast,'sham':sham,'offset':off,'clean_values':vals,'corrupt_values':cor,'sham_values':sv})
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
  if len(mt)!=len(set(mt)):raise RuntimeError(f'duplicate main tuple {st}')
  if st!='fit':
   from collections import Counter
   if set(Counter(r['target'] for r in rows).values())!={6} or set(Counter(r['query'] for r in rows).values())!={24}:raise RuntimeError(f'counterbalance {st}')
  out[st]={'rows':len(rows),'unique_main_tuples':len(set(mt)),'unique_sham_tuples':len(set(sht)),'max_main_tuple_contribution':max(mt.count(x) for x in set(mt)),'main_tuple_sha256':hashlib.sha256(canon(sorted(mt))).hexdigest(),'sham_tuple_sha256':hashlib.sha256(canon(sorted(set(sht)))).hexdigest()}
  ids.append(set(r['row_id'] for r in rows));seeds.append(set(r['row_seed'] for r in rows));main.append(set(mt));sh.append(set(sht))
 for xs,name in [(ids,'id'),(seeds,'seed'),(main,'main'),(sh,'sham')]:
  if any(xs[i]&xs[j] for i in range(3) for j in range(i)):raise RuntimeError(f'cross-panel {name} overlap')
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
def train_generic(model:torch.nn.Module,x:torch.Tensor,y:torch.Tensor,t:torch.Tensor,sc:Mapping[str,Any],seed:int)->dict[str,Any]:return r5.train_model(model,x,y,t,sc,seed)
def stable_top(scores:torch.Tensor,k:int)->torch.Tensor:
 a=scores.detach().cpu().numpy();order=np.lexsort((np.arange(len(a)),-a));return torch.tensor(order[:k],dtype=torch.long,device=scores.device)

def context(model:r5.CopyTransformer,rows:Sequence[Mapping[str,Any]],device:torch.device)->dict[str,torch.Tensor]:
 clean,q,t=r5.rows_tensors(rows,device,'clean_values');cor,_,co=r5.rows_tensors(rows,device,'corrupt_values');sh,_,_=r5.rows_tensors(rows,device,'sham_values')
 with torch.no_grad():oc=model(clean,q);orr=model(cor,q);os=model(sh,q)
 return {'clean':oc['head'],'corrupt':orr['head'],'sham':os['head'],'delta':oc['head']-orr['head'],'sham_delta':os['head']-orr['head'],'logits_clean':oc['logits'],'logits_corrupt':orr['logits'],'weights_clean':oc['weights'],'weights_corrupt':orr['weights'],'values_clean':oc['values'],'values_corrupt':orr['values'],'target':t,'contrast':co,'query':q}

def fit_methods(model:r5.CopyTransformer,rows:Sequence[Mapping[str,Any]],c:Mapping[str,Any],model_seed:int,device:torch.device,out:Path)->tuple[list[Method],dict[str,Any]]:
 out.mkdir(parents=True,exist_ok=False);z=context(model,rows,device);d=z['delta'];t=z['target'];D=d.shape[1];m=[];fits={};classes=c['methods']['information_contracts']
 m.extend([Method('exact_head_delta','exact_head_delta','exact',None,comparison_class='donor_compression'),Method('identity_full64','identity_full64','identity',None,rank=64,comparison_class='donor_compression')])
 _,_,vh=canonical_svd(d.detach().cpu().numpy())
 for k in c['methods']['global_ranks']:
  P=(vh[:k].T@vh[:k]).astype(np.float32);m.append(Method(f'output_oracle_rank{k}',f'output_oracle_rank{k}','matrix',torch.tensor(P,device=device),rank=k));
 states=torch.cat([z['clean'],z['corrupt'],z['sham']],0);mu=states.mean(0);_,_,vha=canonical_svd((states-mu).detach().cpu().numpy())
 for k in c['methods']['global_ranks']:
  P=(vha[:k].T@vha[:k]).astype(np.float32);m.append(Method(f'ambient_pca_rank{k}',f'ambient_pca_rank{k}','matrix',torch.tensor(P,device=device),rank=k))
 for k in c['methods']['global_ranks']:
  q=r5.qr_canonical(rng('random',c['methods']['random_seed'],model_seed,k).normal(size=(D,D)))[:,:k];P=torch.tensor((q@q.T).astype(np.float32),device=device);m.append(Method(f'random_rank{k}',f'random_rank{k}','matrix',P,rank=k,comparison_class='negative_control'))
 m.append(Method('readout_task_projection','readout_task_projection','readout',None,comparison_class='task_aware'))
 means=torch.stack([d[t==v].mean(0) for v in range(c['model']['vocab'])]);m.append(Method('target_mean_delta','target_mean_delta','target_mean',means,comparison_class='label_mean_no_donor'))
 rg=rng('perm',c['methods']['permutation_seed'],model_seed);xp=d.detach().cpu().numpy().copy();tn=t.detach().cpu().numpy()
 for v in range(c['model']['vocab']):
  ix=np.flatnonzero(tn==v);xp[ix]=xp[rg.permutation(ix)]
 W=np.linalg.pinv(xp.astype(np.float64),rcond=c['methods']['svd_rtol'])@d.detach().cpu().numpy().astype(np.float64);m.append(Method('within_target_permutation','within_target_permutation','matrix',torch.tensor(W.astype(np.float32),device=device),rank=int(np.linalg.matrix_rank(W)),comparison_class='negative_control'))
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
     jr=r5.empirical_jacobian_ranks(mdl,xt,tt,c['model']['vocab'],device);extra={'empirical_jacobian_ranks':jr,'empirical_jacobian_union_rank':max(jr)}
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
   codes=sae.encode(sae_states);un=stable_top(codes.var(0,unbiased=False),sc['selected_features']);paired=stable_top(torch.mean(torch.abs(sae.encode(z['clean'])-sae.encode(z['corrupt'])),0),sc['selected_features'])
  p=out/f'topk_sae_seed{sd}.pt';torch.save({'state_dict':sae.state_dict(),'model_seed':model_seed,'method_seed':sd,'config':sc,'unpaired_selected':un.cpu().tolist(),'paired_selected':paired.cpu().tolist(),'method_table_sha256':method_table_hash(c)},p);fits[f'topk_sae_seed{sd}']={'initial_loss':losses[0],'final_loss':losses[-1],'sha256':sha(p),'unpaired_selected':un.cpu().tolist(),'paired_selected':paired.cpu().tolist()};params=sum(x.numel() for x in sae.parameters());m.extend([Method(f'topk_sae_unpaired_selector_seed{sd}','topk_sae_unpaired_selector','sae',(sae,un),sd,parameters=params),Method(f'topk_sae_paired_selector_seed{sd}','topk_sae_paired_selector','sae',(sae,paired),sd,parameters=params,comparison_class='task_aware')])
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
def score(method:Method,p:torch.Tensor,ps:torch.Tensor,z:Mapping[str,torch.Tensor],rows:Sequence[Mapping[str,Any]],c:Mapping[str,Any],stage:str,model:r5.CopyTransformer,estimand:str,matched_complete:bool=True)->dict[str,Any]:
 with torch.no_grad():
  patch=model.readout(F.layer_norm(z['corrupt']+p,(p.shape[1],),eps=c['model']['layernorm_eps']));sham=model.readout(F.layer_norm(z['corrupt']+ps,(p.shape[1],),eps=c['model']['layernorm_eps']));abl=model.readout(F.layer_norm(z['clean']-p,(p.shape[1],),eps=c['model']['layernorm_eps']))
  ctr=[]
  for i,r in enumerate(rows):
   g=torch.tensor(rng('control',r['row_seed'],method.name,estimand).normal(size=p.shape[1]),dtype=torch.float32,device=p.device);truth=z['delta'][i];g-=torch.dot(g,truth)*truth/torch.clamp(torch.dot(truth,truth),min=1e-12);g*=torch.linalg.vector_norm(p[i])/torch.clamp(torch.linalg.vector_norm(g),min=1e-12);ctr.append(g)
  ctrl=torch.stack(ctr);ctl=model.readout(F.layer_norm(z['corrupt']+ctrl,(p.shape[1],),eps=c['model']['layernorm_eps']))
 zh=z['logits_clean'].cpu().numpy();zc=z['logits_corrupt'].cpu().numpy();zp=patch.cpu().numpy();zs=sham.cpu().numpy();za=abl.cpu().numpy();zctl=ctl.cpu().numpy();tn=z['target'].cpu().numpy();co=z['contrast'].cpu().numpy();den=r5.row_margin(zh,tn)-r5.row_margin(zc,tn);scale=np.sqrt(np.mean((r5.centered(zh)-r5.centered(zc))**2,1));e=c['eligibility'];eligible=(np.argmax(zh,1)==tn)&(np.argmax(zc,1)==co)&(den>e['effect_strict']);sd=np.where(den>1e-6,den,1);ss=np.where(scale>1e-6,scale,1)
 rec=(r5.row_margin(zp,tn)-r5.row_margin(zc,tn))/sd;sr=(r5.row_margin(zs,tn)-r5.row_margin(zc,tn))/sd;cr=(r5.row_margin(zctl,tn)-r5.row_margin(zc,tn))/sd;nec=(r5.row_margin(zh,tn)-r5.row_margin(za,tn))/sd;fv=1-np.sqrt(np.mean((r5.centered(zp)-r5.centered(zh))**2,1))/ss;coll=[]
 for i in range(len(rows)):
  mask=np.ones(zh.shape[1],bool);mask[tn[i]]=False;mask[co[i]]=False;coll.append(float(np.sqrt(np.mean((r5.centered(zp)[i,mask]-r5.centered(zh)[i,mask])**2))/ss[i]))
 vals={'recovery':rec,'sham_specificity':rec-sr,'control_margin':rec-cr,'collateral_error':np.array(coll),'necessity':nec,'full_vocab_recovery':fv};blocks=np.array([r['block'] for r in rows]);B=c['panels'][stage]['blocks'];per={str(b):int(np.sum(eligible&(blocks==b))) for b in range(B)};vs={str(v):int(np.sum(eligible&(tn==v))) for v in range(c['model']['vocab'])};qs=np.array([r['query'] for r in rows]);qsu={str(v):int(np.sum(eligible&(qs==v))) for v in range(c['model']['slots'])};support=int(eligible.sum())>=c['panels']['minimum_eval_total'] and all(x>=c['panels']['minimum_per_block'] for x in per.values()) and all(x>=c['panels']['minimum_per_value_marginal'] for x in vs.values()) and all(x>=c['panels']['minimum_per_query_marginal'] for x in qsu.values())
 metrics={k:interval(v[eligible],blocks[eligible],c,f'{stage}:{method.name}:{estimand}:{k}') for k,v in vals.items()} if support else {};gd={k:gate(k,metrics[k],c) for k in c['gates']} if support else {};complete=matched_complete and support and len(gd)==len(c['gates']);return {'estimand':estimand,'support_pass':bool(support),'eligible_total':int(eligible.sum()),'per_block':per,'value_support':vs,'query_support':qsu,'metrics':metrics,'gate_decisions':gd,'matched_status':'complete' if matched_complete else 'not_applicable','all_gates_pass':bool(complete and all(gd.values()))}

def eval_methods(model:r5.CopyTransformer,rows:Sequence[Mapping[str,Any]],methods:Sequence[Method],c:Mapping[str,Any],stage:str,device:torch.device)->dict[str,Any]:
 z=context(model,rows,device);hc=torch.einsum('bs,bsd->bd',z['weights_corrupt'],z['values_clean']);hr=torch.einsum('bs,bsd->bd',z['weights_clean'],z['values_corrupt']);routing={'weights_exact':bool(torch.equal(z['weights_clean'],z['weights_corrupt'])),'clean_hybrid_pass':bool(torch.allclose(hc,z['clean'],atol=c['routing_qa']['hybrid_atol'],rtol=c['routing_qa']['hybrid_rtol'])),'corrupt_hybrid_pass':bool(torch.allclose(hr,z['corrupt'],atol=c['routing_qa']['hybrid_atol'],rtol=c['routing_qa']['hybrid_rtol']))};routing['all_pass']=all(routing.values());out={}
 for m in methods:
  with torch.no_grad():p,ps=predict(m,z,model)
  native=score(m,p,ps,z,rows,c,stage,model,'native')
  if m.kind=='zero':matched={'estimand':'matched','support_pass':native['support_pass'],'eligible_total':native['eligible_total'],'metrics':{},'gate_decisions':{},'matched_status':'not_applicable','all_gates_pass':False};mc=False;pm=p
  else:
   pm,ok=r5.norm_match(p.detach().cpu().numpy(),z['delta'].cpu().numpy());psm,oks=r5.norm_match(ps.detach().cpu().numpy(),z['delta'].cpu().numpy());mc=bool(np.all(ok&oks));matched=score(m,torch.tensor(pm,device=device),torch.tensor(psm,device=device),z,rows,c,stage,model,'matched',mc)
  direction=r5.direction_metrics(p.detach().cpu().numpy(),z['delta'].cpu().numpy());out[m.name]={'family':m.family,'seed':m.seed,'rank':m.rank,'parameters':m.parameters,'comparison_class':m.comparison_class,'direction':direction,'native':native,'matched':matched,'all_gates_pass':bool(native['all_gates_pass'] and matched['all_gates_pass'])}
 fam={}
 for f in sorted(set(x.family for x in methods)):
  names=[x.name for x in methods if x.family==f];fam[f]=bool(names and all(out[n]['all_gates_pass'] for n in names))
 complete=bool(routing['all_pass'] and all(np.isfinite(x['direction']['cosine']) and x['native'].get('support_pass') and x['matched'].get('matched_status') in {'complete','not_applicable'} and (x['matched'].get('matched_status')=='not_applicable' or x['matched'].get('support_pass')) and all(np.isfinite(v['point']) and np.isfinite(v['lower']) and np.isfinite(v['upper']) for est in ('native','matched') for v in x[est].get('metrics',{}).values()) for x in out.values()))
 return {'stage':stage,'routing_qa':routing,'methods':out,'family_pass_every_seed':fam,'technical_complete':complete}

def load_model(c:Mapping[str,Any],seed:int,device:torch.device)->r5.CopyTransformer:
 rec=c['r5']['checkpoints'][str(seed)];p=ROOT/rec['path'];
 if sha(p)!=rec['sha256']:raise RuntimeError('checkpoint drift')
 model=r5.CopyTransformer(c,seed,device);ck=torch.load(p,map_location=device,weights_only=False);model.load_state_dict(ck['state_dict'],strict=True);return model.eval()

def compatibility_smoke(c:Mapping[str,Any],ps:Mapping[str,Sequence[Mapping[str,Any]]],device:torch.device)->dict[str,Any]:
 sc=json.loads(json.dumps(c));sc['methods']['global_ranks']=[4];sc['methods']['conditioned_ranks']=[4]
 for k in ('paired_linear','target_linear','target_nonlinear','sae'):
  sc['methods'][k]['seeds']=sc['methods'][k]['seeds'][:1];sc['methods'][k]['steps']=1
 model=r5.CopyTransformer(sc,99993,device).eval();td=Path('/tmp')/f'tcm_v1_smoke_{os.getpid()}_{str(device).replace(":","_")}'
 if td.exists():raise RuntimeError(f'smoke path exists {td}')
 try:
  methods,fit=fit_methods(model,ps['fit'][:256],sc,99993,device,td);z=context(model,ps['development'][:32],device);finite=True
  for m in methods:
   with torch.no_grad():p,q=predict(m,z,model)
   finite &= bool(torch.isfinite(p).all() and torch.isfinite(q).all())
  jac=fit['fits']['target_nonlinear_rank4_seed8301']['empirical_jacobian_ranks']
  return {'families':sorted(set(m.family for m in methods)),'methods':len(methods),'prediction_finite':finite,'jacobian_targets':len(jac),'fit_artifacts':len([p for p in td.iterdir() if p.is_file()])}
 finally:shutil.rmtree(td,ignore_errors=True)

def write_candidate(device_name:str,record:bool)->dict[str,Any]:
 c=cfg();validate_config(c);ps=panel_set(c);audit=panel_audit(ps,c);device=torch.device(device_name);model=r5.CopyTransformer(c,99991,device).eval();rows=ps['development'];z=context(model,rows,device);m=Method('exact_head_delta','exact_head_delta','exact',None);p,px=predict(m,z,model);direction=r5.direction_metrics(p.detach().cpu().numpy(),z['delta'].detach().cpu().numpy());rank64=np.eye(c['model']['width'],dtype=np.float32);smoke=compatibility_smoke(c,ps,device);checks={'exact_direction_finite':direction['finite'] and direction['cosine']>.999999,'zero_direction_finite':r5.direction_metrics(np.zeros_like(z['delta'].detach().cpu().numpy()),z['delta'].detach().cpu().numpy())['finite'],'rank64_identity':bool(np.allclose(z['delta'].detach().cpu().numpy()@rank64,z['delta'].detach().cpu().numpy(),atol=1e-6,rtol=1e-6)),'all_32_targets_jacobian_required':c['model']['vocab']==32,'smoke_predictions_finite':smoke['prediction_finite'] and smoke['jacobian_targets']==32};payload={'schema_version':'trained_copy_method_benchmark_v1_candidate','status':'PASS' if all(checks.values()) else 'FAIL','device':str(device),'source_sha256':sha(SCRIPT),'config_sha256':sha(CFG_PATH),'plan_sha256':sha(PLAN),'method_table_sha256':method_table_hash(c),'panel_audit':audit,'compatibility_smoke':smoke,'r5_checkpoint_hashes':{k:v['sha256'] for k,v in c['r5']['checkpoints'].items()},'scientific_panel_accessed':False,'r5_checkpoint_loaded':False,'checks':checks}
 if record:
  pth=rp(c,'candidate_manifest');create_json(pth,payload);payload['manifest_sha256']=sha(pth)
 return payload

def create_lock()->dict[str,Any]:
 c=cfg();p=rp(c,'candidate_manifest');review=rp(c,'candidate_review');
 if not p.is_file() or not review.is_file() or 'VERDICT: SHIP' not in review.read_text() or sha(p) not in review.read_text():raise RuntimeError('candidate review binding invalid')
 out={'schema_version':'trained_copy_method_benchmark_v1_generator_lock','config_sha256':sha(CFG_PATH),'source_sha256':sha(SCRIPT),'plan_sha256':sha(PLAN),'candidate_sha256':sha(p),'candidate_review_sha256':sha(review),'method_table_sha256':method_table_hash(c),'created_ns':time.time_ns()};create_json(rp(c,'generator_lock'),out);return out
def prepare()->dict[str,Any]:
 c=cfg();lock=rp(c,'generator_lock');
 if not lock.is_file():raise RuntimeError('missing generator lock')
 root=rp(c,'prepared_root');
 if root.exists():raise FileExistsError(root)
 ps=panel_set(c);audit=panel_audit(ps,c);root.mkdir(parents=True)
 for st,rows in ps.items():write_jsonl(root/f'{st}.jsonl',rows)
 atomic_json(root/'PREPARED.json',{'schema_version':'trained_copy_method_benchmark_v1_prepared','generator_lock_sha256':sha(lock),'panel_audit':audit,'payload_opened':False});return audit
def freeze()->dict[str,Any]:
 c=cfg();root=rp(c,'prepared_root');prep=loadj(root/'PREPARED.json');payloads=[]
 for st in ('fit','development','confirmation'):
  p=root/f'{st}.jsonl';payloads.append({'stage':st,'path':p.relative_to(ROOT).as_posix(),'bytes':p.stat().st_size,'sha256':sha(p),'audit':prep['panel_audit'][st]})
 f={'schema_version':'trained_copy_method_benchmark_v1_freeze','config_sha256':sha(CFG_PATH),'source_sha256':sha(SCRIPT),'plan_sha256':sha(PLAN),'generator_lock_sha256':sha(rp(c,'generator_lock')),'candidate_sha256':sha(rp(c,'candidate_manifest')),'candidate_review_sha256':sha(rp(c,'candidate_review')),'method_table_sha256':method_table_hash(c),'r5_checkpoints':c['r5']['checkpoints'],'payloads':payloads,'payloads_opened':False};create_json(rp(c,'freeze'),f);return f
def verify_freeze(opaque:bool)->dict[str,Any]:
 c=cfg();f=loadj(rp(c,'freeze'))
 if f['config_sha256']!=sha(CFG_PATH) or f['source_sha256']!=sha(SCRIPT) or f['method_table_sha256']!=method_table_hash(c):raise RuntimeError('freeze drift')
 if not opaque:
  for rec in f['payloads']:
   p=ROOT/rec['path'];
   if sha(p)!=rec['sha256'] or p.stat().st_size!=rec['bytes']:raise RuntimeError('payload drift')
 return {'status':'PASS','freeze_sha256':sha(rp(c,'freeze')),'opaque':opaque}
def bind_review()->dict[str,Any]:
 c=cfg();f=rp(c,'freeze');r=rp(c,'frozen_review')
 if not r.is_file() or 'VERDICT: SHIP' not in r.read_text() or sha(f) not in r.read_text():raise RuntimeError('freeze review invalid')
 x={'schema_version':'trained_copy_method_benchmark_v1_review_binding','freeze_sha256':sha(f),'review_path':r.relative_to(ROOT).as_posix(),'review_sha256':sha(r)};create_json(rp(c,'review_binding'),x);return x
def open_stage(c:Mapping[str,Any],stage:str,prov:Path,index:int)->list[dict[str,Any]]:
 event(prov,index,f'{stage.upper()}_ACCESS_MAY_HAVE_OCCURRED');f=loadj(rp(c,'freeze'));rec=next(x for x in f['payloads'] if x['stage']==stage);p=ROOT/rec['path'];
 if sha(p)!=rec['sha256']:raise RuntimeError('payload drift')
 rows=read_jsonl(p);event(prov,index+1,f'{stage.upper()}_OPENED');return rows
def launch_preflight(index:int,uuid:str)->None:
 c=cfg();validate_config(c);verify_freeze(True);b=loadj(rp(c,'review_binding')); 
 if b['freeze_sha256']!=sha(rp(c,'freeze')) or b['review_sha256']!=sha(ROOT/b['review_path']):raise RuntimeError('review binding drift')
 for k in ('output_root','provenance_root'):
  if rp(c,k).exists():raise RuntimeError(f'preexisting {k}')
 got=subprocess.check_output(['nvidia-smi','--query-gpu=index,uuid','--format=csv,noheader']).decode().splitlines();m={int(x.split(',')[0]):x.split(',')[1].strip() for x in got}
 if m.get(index)!=uuid:raise RuntimeError('GPU UUID mismatch')
def gpu_validate(index:int,uuid:str,pane_pid:int,lockdir:str,token:str)->torch.device:
 if os.environ.get('CUDA_VISIBLE_DEVICES')!=uuid:raise RuntimeError('CUDA visibility mismatch')
 if Path(lockdir).name!=f'msae_trained_copy_methods_v1_{uuid}.lockdir' or (Path(lockdir)/'token').read_text().strip()!=token:raise RuntimeError('GPU lock mismatch')
 d=torch.device('cuda:0');x=torch.ones(1,device=d);torch.cuda.synchronize();pid=os.getpid();rows=subprocess.check_output(['nvidia-smi','--query-compute-apps=gpu_uuid,pid','--format=csv,noheader']).decode().splitlines()
 if not any(a.strip()==uuid and int(b.strip())==pid for a,b in (r.split(',')[:2] for r in rows)):raise RuntimeError('worker PID not on UUID')
 anc=[];cur=pid
 while cur>1:
  anc.append(cur);s=Path(f'/proc/{cur}/stat').read_text().split();cur=int(s[3])
 if pane_pid not in anc:raise RuntimeError('pane ancestry mismatch')
 return d

def run_pipeline(index:int,uuid:str,pane_pid:int,lockdir:str,token:str)->None:
 c=cfg();launch_preflight(index,uuid);device=gpu_validate(index,uuid,pane_pid,lockdir,token);prov=rp(c,'provenance_root');out=rp(c,'output_root');prov.mkdir(parents=True,exist_ok=False);out.mkdir(parents=True,exist_ok=False);atomic_json(prov/'LAUNCH.json',{'physical_index':index,'gpu_uuid':uuid,'worker_pid':os.getpid(),'pane_pid':pane_pid,'freeze_sha256':sha(rp(c,'freeze')),'time_ns':time.time_ns()});torch.use_deterministic_algorithms(True);torch.manual_seed(c['seed']);np.random.seed(c['seed']);random.seed(c['seed'])
 try:
  fitrows=open_stage(c,'fit',prov,10);devrows=open_stage(c,'development',prov,12);models={};methods={};fits={};dev={};ckroot=out/'checkpoints';ckroot.mkdir()
  for sd in c['model']['seeds']:
   model=load_model(c,sd,device);models[sd]=model;ms,fr=fit_methods(model,fitrows,c,sd,device,ckroot/str(sd));methods[sd]=ms;fits[str(sd)]=fr;dev[str(sd)]=eval_methods(model,devrows,ms,c,'development',device)
  event(prov,14,'DEVELOPMENT_COMPLETE');art=[]
  for p in sorted(ckroot.rglob('*')):
   if p.is_file():art.append({'path':p.relative_to(out).as_posix(),'bytes':p.stat().st_size,'sha256':sha(p)})
  exact_ok=all(dev[str(sd)]['routing_qa']['all_pass'] and dev[str(sd)]['methods'][name]['all_gates_pass'] for sd in c['model']['seeds'] for name in ('exact_head_delta','identity_full64'));technical=all(dev[str(sd)]['technical_complete'] and len(dev[str(sd)]['methods'])==len(methods[sd]) for sd in c['model']['seeds']);pre={'schema_version':'trained_copy_method_benchmark_v1_preconfirmation','method_table_sha256':method_table_hash(c),'artifacts':art,'method_inventory':{str(sd):fits[str(sd)]['method_inventory'] for sd in c['model']['seeds']},'development_result_sha256':hashlib.sha256(canon(dev)).hexdigest(),'exact_identity_authorized':exact_ok,'technical_complete':technical,'confirmation_authorized':bool(exact_ok and technical)};atomic_json(out/'PRECONFIRMATION.json',pre);event(prov,15,'PRECONFIRMATION_SEALED',manifest_sha256=sha(out/'PRECONFIRMATION.json'),confirmation_authorized=pre['confirmation_authorized'])
  if not pre['confirmation_authorized']:
   event(prov,16,'CONFIRMATION_BLOCKED_UNOPENED');atomic_json(out/'final/result.json',{'status':'DEVELOPMENT_NOT_AUTHORIZED','confirmation_opened':False,'development':dev,'fits':fits,'preconfirmation_sha256':sha(out/'PRECONFIRMATION.json')});return
  confrows=open_stage(c,'confirmation',prov,16);conf={str(sd):eval_methods(models[sd],confrows,methods[sd],c,'confirmation',device) for sd in c['model']['seeds']};families=sorted(set(v.family for ms in methods.values() for v in ms));family_all={f:all(dev[str(sd)]['family_pass_every_seed'].get(f,False) and conf[str(sd)]['family_pass_every_seed'].get(f,False) for sd in c['model']['seeds']) for f in families};final={'schema_version':'trained_copy_method_benchmark_v1_final','status':'METHOD_BENCHMARK_COMPLETE','confirmation_opened':True,'conditional_on_r5_qualified_checkpoints':True,'method_table_sha256':method_table_hash(c),'fits':fits,'development':dev,'confirmation':conf,'family_pass_all_checkpoints_both_panels':family_all,'scope':c['scope'],'lineage':{'config_sha256':sha(CFG_PATH),'freeze_sha256':sha(rp(c,'freeze')),'review_binding_sha256':sha(rp(c,'review_binding')),'r5_checkpoint_hashes':{k:v['sha256'] for k,v in c['r5']['checkpoints'].items()},'preconfirmation_sha256':sha(out/'PRECONFIRMATION.json')}};atomic_json(out/'final/result.json',final);event(prov,18,'TERMINAL_COMPLETE',status=final['status'],final_sha256=sha(out/'final/result.json'))
 except BaseException as e:
  atomic_json(prov/'TECHNICAL_FAILURE_AFTER_ACCESS.json',{'status':'TECHNICAL_FAILURE_AFTER_ACCESS','error':f'{type(e).__name__}: {e}','time_ns':time.time_ns()});raise

def mutation_suite()->dict[str,Any]:
 c=cfg();ps=panel_set(c);a=panel_audit(ps,c);bad=json.loads(json.dumps(c));bad['panels']['development']['offsets']=[21,22,23,24,25];caught=False
 try:validate_config(bad)
 except RuntimeError:caught=True
 return {'status':'PASS' if caught and all(v['max_main_tuple_contribution']==1 for k,v in a.items() if k!='fit') else 'FAIL','offset_overlap_detected':caught,'panel_audit':a}
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
