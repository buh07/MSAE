#!/usr/bin/env python3
"""Frozen numerical/statistical primitives for Atlas v3.3 attempt 7.

All probe fitting is deterministic closed-form ridge. No neural parameter is accepted.
"""
from __future__ import annotations
from dataclasses import dataclass
from typing import Any,Mapping,Sequence
import numpy as np
import torch


def macro_f1(y:np.ndarray,pred:np.ndarray,classes:Sequence[str],weights:np.ndarray|None=None)->float:
 y=np.asarray(y);pred=np.asarray(pred);w=np.ones(len(y),dtype=np.float64) if weights is None else np.asarray(weights,dtype=np.float64)
 if y.shape!=pred.shape or w.shape!=(len(y),) or not np.isfinite(w).all() or np.any(w<0) or w.sum()<=0:return float('nan')
 vals=[]
 for c in classes:
  tp=w[(y==c)&(pred==c)].sum();fp=w[(y!=c)&(pred==c)].sum();fn=w[(y==c)&(pred!=c)].sum();den=2*tp+fp+fn
  vals.append(0.0 if den==0 else 2*tp/den)
 return float(np.mean(vals))


def balanced_accuracy(y:np.ndarray,pred:np.ndarray,classes:Sequence[str],weights:np.ndarray|None=None)->float:
 y=np.asarray(y);pred=np.asarray(pred);w=np.ones(len(y),dtype=np.float64) if weights is None else np.asarray(weights,dtype=np.float64)
 vals=[]
 for c in classes:
  den=w[y==c].sum()
  if den<=0:return float('nan')
  vals.append(w[(y==c)&(pred==c)].sum()/den)
 return float(np.mean(vals))


def prior_chance(y_fit:np.ndarray,y_test:np.ndarray,classes:Sequence[str],weights:np.ndarray|None=None)->float:
 p=np.asarray([np.mean(y_fit==c) for c in classes],dtype=np.float64)
 w=np.ones(len(y_test),dtype=np.float64) if weights is None else np.asarray(weights,dtype=np.float64)
 if w.sum()<=0:return float('nan')
 q=np.asarray([w[y_test==c].sum()/w.sum() for c in classes]);d=p+q
 return float(np.divide(2*p*q,d,out=np.zeros_like(d),where=d>0).mean())


def normalized_recovery(score:float,chance:float)->float:
 return float((score-chance)/(1-chance)) if np.isfinite(score) and np.isfinite(chance) and chance<1 else float('nan')


@dataclass
class RidgeModel:
 classes:tuple[str,...];mean:np.ndarray;scale:np.ndarray;coef:np.ndarray;intercept:np.ndarray;alpha:float
 def predict(self,x:np.ndarray)->np.ndarray:
  z=(np.asarray(x,dtype=np.float64)-self.mean)/self.scale
  score=z@self.coef.T+self.intercept
  return np.asarray(self.classes,dtype=object)[np.argmax(score,axis=1)].astype(str)


def _targets(y:np.ndarray,classes:Sequence[str])->np.ndarray:
 return np.stack([np.where(y==c,1.0,-1.0) for c in classes],axis=1)


def fit_ridge(x:np.ndarray,y:np.ndarray,classes:Sequence[str],alpha:float,*,device:str='cpu',scale_floor:float=1e-8)->RidgeModel:
 a=np.asarray(x,dtype=np.float64);labels=np.asarray(y,dtype=str);classes=tuple(map(str,classes))
 if a.ndim!=2 or len(a)!=len(labels) or not np.isfinite(a).all() or alpha<=0:raise ValueError('invalid ridge inputs')
 if set(labels)-set(classes):raise ValueError('training label outside classes')
 mean=a.mean(0);scale=a.std(0);scale=np.where(scale<scale_floor,1.0,scale);z=(a-mean)/scale
 design=np.concatenate([z,np.ones((len(z),1))],axis=1);target=_targets(labels,classes)
 d=torch.as_tensor(design,dtype=torch.float64,device=device);t=torch.as_tensor(target,dtype=torch.float64,device=device)
 gram=d.T@d;pen=torch.eye(gram.shape[0],dtype=torch.float64,device=device)*float(alpha);pen[-1,-1]=0
 solution=torch.linalg.solve(gram+pen,d.T@t).cpu().numpy()
 return RidgeModel(classes,mean,scale,solution[:-1].T,solution[-1],float(alpha))


def choose_alpha(x:np.ndarray,y:np.ndarray,folds:np.ndarray,classes:Sequence[str],alphas:Sequence[float],*,device:str='cpu',scale_floor:float=1e-8)->tuple[float,dict[str,float]]:
 folds=np.asarray(folds,dtype=int);scores={str(float(a)):[] for a in alphas}
 if set(folds)!=set(range(5)):raise ValueError('all five fit folds required')
 for fold in range(5):
  train=folds!=fold;valid=~train
  if set(np.asarray(y)[train])!=set(classes):raise ValueError('fit-fold training partition missing class')
  for alpha in alphas:
   model=fit_ridge(x[train],np.asarray(y)[train],classes,float(alpha),device=device,scale_floor=scale_floor)
   scores[str(float(alpha))].append(macro_f1(np.asarray(y)[valid],model.predict(x[valid]),classes))
 means={key:float(np.mean(value)) for key,value in scores.items()};best=max(means.values())
 chosen=min(float(key) for key,value in means.items() if np.isclose(value,best,rtol=0,atol=1e-12))
 return chosen,means


@dataclass
class CategoricalEncoder:
 columns:tuple[str,...];levels:dict[str,tuple[str,...]]
 @classmethod
 def fit(cls,rows:Sequence[Mapping[str,str]],columns:Sequence[str])->'CategoricalEncoder':
  levels={}
  for col in columns:
   observed=sorted({str(row[col]) for row in rows},key=lambda x:x.encode())
   observed=[x for x in observed if x!='__UNKNOWN__']+['__UNKNOWN__']
   levels[str(col)]=tuple(observed)
  return cls(tuple(map(str,columns)),levels)
 def transform(self,rows:Sequence[Mapping[str,str]])->np.ndarray:
  blocks=[]
  for col in self.columns:
   levels=self.levels[col];reference=min((x for x in levels if x!='__UNKNOWN__'),key=lambda x:x.encode(),default='__UNKNOWN__')
   kept=[x for x in levels if x!=reference];known=set(levels)-{'__UNKNOWN__'}
   vals=[str(row[col]) if str(row[col]) in known else '__UNKNOWN__' for row in rows]
   blocks.append(np.asarray([[float(v==level) for level in kept] for v in vals],dtype=np.float64))
  return np.concatenate(blocks,axis=1) if blocks else np.empty((len(rows),0),dtype=np.float64)


def interval(values:Sequence[float])->dict[str,Any]:
 a=np.asarray([x for x in values if np.isfinite(x)],dtype=np.float64)
 return {'finite':int(len(a)),'lower':float(np.quantile(a,.025)) if len(a) else None,'upper':float(np.quantile(a,.975)) if len(a) else None}


def row_normalize(x:np.ndarray,floor:float=1e-12)->np.ndarray:
 a=np.asarray(x,dtype=np.float64);norm=np.linalg.norm(a,axis=1,keepdims=True)
 if np.any(norm<floor):raise ValueError('zero delta row')
 return a/norm


def delta_basis(delta:np.ndarray,rank:int,floor:float)->tuple[np.ndarray,dict[str,Any]]:
 x=row_normalize(delta);x=x-x.mean(0,keepdims=True);_,s,vt=np.linalg.svd(x,full_matrices=False);r=min(rank,int(np.sum(s>floor)))
 if r==0:raise ValueError('rank-zero delta basis')
 return vt[:r].T,{'rank':r,'singular_values':s.tolist()}


def basis_overlap(left:np.ndarray,right:np.ndarray)->float:
 q1=np.linalg.qr(np.asarray(left,dtype=np.float64))[0];q2=np.linalg.qr(np.asarray(right,dtype=np.float64))[0];s=np.linalg.svd(q1.T@q2,compute_uv=False)
 return float(np.sum(s*s)/min(q1.shape[1],q2.shape[1]))


def make_projector(blocks:Sequence[np.ndarray],rank:int,floor:float)->tuple[np.ndarray,dict[str,Any]]:
 bases=[];ranks=[]
 for block in blocks:
  a=np.asarray(block,dtype=np.float64)
  # Blocks may be class-weight rows or already column bases.
  row_block=a.T if a.shape[0]>a.shape[1] else a
  _,s,vt=np.linalg.svd(row_block,full_matrices=False);r=int(np.sum(s>floor))
  if r==0:raise ValueError('rank-zero projector block')
  basis=vt[:r];bases.append(basis/np.sqrt(r));ranks.append(r)
 stacked=np.concatenate(bases);_,s,vt=np.linalg.svd(stacked,full_matrices=False);nr=int(np.sum(s>floor));keep=min(rank,nr)
 if keep==0:raise ValueError('rank-zero projector')
 b=vt[:keep].T;return b@b.T,{'rank':keep,'numerical_rank':nr,'block_ranks':ranks,'singular_values':s.tolist()}
