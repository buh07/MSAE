#!/usr/bin/env python3
"""Opened-development matching and synthetic-estimator contracts for relational measurement v4."""
from __future__ import annotations

from collections import Counter, defaultdict
from copy import deepcopy
from dataclasses import asdict
import hashlib
import heapq
import math
import struct
import warnings
from typing import Any, Iterable, Mapping, Sequence

import numpy as np
from scipy.optimize import linear_sum_assignment
from scipy.stats import norm, t as student_t
from sklearn.exceptions import ConvergenceWarning
from sklearn.linear_model import LogisticRegression, Ridge
from sklearn.preprocessing import StandardScaler

from relational_objects_v3 import canonical_bytes, stable_hex
from scout_relational_objects_v3 import Sentence, Token, ancestors, candidate as v3_candidate, morph_signature

ORIENTATIONS=("later_query_is_head","later_query_is_child")
NUMERIC_NAMES=("log2_gap","relative_query","causal_fraction","log2_length")


def parse_feats(feats: str) -> dict[str,str]:
    return {p.split("=",1)[0]:p.split("=",1)[1] for p in feats.split("|") if "=" in p}


def endpoint_rows(row: Mapping[str,Any]) -> tuple[dict[str,Any],dict[str,Any]]:
    """Return (later, earlier) endpoint records from a child/head v3 row."""
    child={"form":row["child_form"],"lemma":row["child_lemma"],"feats":row["child_feats"],"upos":row["child_upos"],"is_punct":row["child_is_punct"],"subtokens":len(row["child_positions"])}
    head={"form":row["head_form"],"lemma":row["head_lemma"],"feats":row["head_feats"],"upos":row["head_upos"],"is_punct":row["head_is_punct"],"subtokens":len(row["head_positions"])}
    return (head,child) if row["orientation"]=="later_query_is_head" else (child,head)


def enrich(row: dict[str,Any], keys: Sequence[str], vocab: Mapping[str,Sequence[str]]) -> dict[str,Any]:
    later,earlier=endpoint_rows(row)
    row=dict(row)
    row["later"]={**later,"morph":morph_signature(later["feats"],keys,vocab),"presence":tuple(k in parse_feats(later["feats"]) for k in keys)}
    row["earlier"]={**earlier,"morph":morph_signature(earlier["feats"],keys,vocab),"presence":tuple(k in parse_feats(earlier["feats"]) for k in keys)}
    L=int(row["sequence_length"])
    row["relative_query"]=float(row["query_index"])/max(1,L-1)
    row["causal_fraction"]=float(row["causal_key_count"])/L
    return row


def core_signature(row: Mapping[str,Any]) -> tuple[Any,...]:
    return (row["orientation"],row["later"]["upos"],row["earlier"]["upos"],bool(row["later"]["is_punct"]),bool(row["earlier"]["is_punct"]),int(row["later"]["subtokens"]),int(row["earlier"]["subtokens"]))


def _gap_bin(x:int)->str:
    return "1" if x==1 else "2" if x==2 else "3-4" if x<=4 else "5-8" if x<=8 else "9+"

def _quartile(x:float)->int:
    if not math.isfinite(x) or not 0.0 <= x <= 1.0:
        raise ValueError("quartile fraction must be finite and in [0,1]")
    return min(3,int(math.floor(4*x)))
def _length_bin(x:int)->str:
    return "1-32" if x<=32 else "33-64" if x<=64 else "65-128" if x<=128 else "129-256"


def coarse_signature(row: Mapping[str,Any]) -> tuple[Any,...]:
    return core_signature(row)+(tuple(row["later"]["presence"]),tuple(row["earlier"]["presence"]),_gap_bin(int(row["surface_gap"])),_quartile(float(row["relative_query"])),_quartile(float(row["causal_fraction"])),_length_bin(int(row["sequence_length"])))


def make_candidate(sentence: Sentence, first: Token, second: Token, *, label:int, orientation:str, relation:str|None, keys:Sequence[str], vocab:Mapping[str,Sequence[str]])->dict[str,Any]:
    row=enrich(v3_candidate(sentence,first,second,label=label,orientation=orientation,relation=relation,morph_keys=keys,morph_vocabulary=vocab),keys,vocab)
    row["source"]=sentence.source
    return row


def enumerate_pool(sentences:Sequence[Sentence],keys:Sequence[str],vocab:Mapping[str,Sequence[str]],method:str,positive_cap:int,negative_cap:int)->tuple[dict[str,Any],dict[str,int]]:
    sig_fn=coarse_signature if method=="coarse_exact" else core_signature
    result:dict[str,dict[str,dict[tuple[Any,...],list[dict[str,Any]]]]]=defaultdict(lambda:{"positive":defaultdict(list),"negative":defaultdict(list)})
    needed:{int:set[tuple[Any,...]]}={0:set(),1:set()}
    cached=[]
    trunc=Counter()
    for sentence in sentences:
        by_id={x.token_id:x for x in sentence.tokens}; ancestry={i:ancestors(i,by_id) for i in by_id}
        part=int(stable_hex(sentence.source,sentence.document_id)[:16],16)&1
        cached.append((sentence,by_id,ancestry,part))
        for child in sentence.tokens:
            if child.head and child.head in by_id:
                head=by_id[child.head]; orient="later_query_is_head" if head.order>child.order else "later_query_is_child"
                row=make_candidate(sentence,child,head,label=1,orientation=orient,relation=child.deprel.split(":",1)[0],keys=keys,vocab=vocab)
                sig=sig_fn(row); result[sentence.document_id]["positive"][sig].append(row); needed[part].add(sig)
    for sentence,by_id,ancestry,part in cached:
        want=needed[1-part]
        for i,left in enumerate(sentence.tokens):
            for right in sentence.tokens[i+1:]:
                if left.head==right.token_id or right.head==left.token_id: continue
                if right.token_id in ancestry[left.token_id] or left.token_id in ancestry[right.token_id]: continue
                for orient in ORIENTATIONS:
                    row=make_candidate(sentence,left,right,label=0,orientation=orient,relation=None,keys=keys,vocab=vocab)
                    sig=sig_fn(row)
                    if sig in want: result[sentence.document_id]["negative"][sig].append(row)
    for roles in result.values():
        for label, strata in roles.items():
            cap=positive_cap if label=="positive" else negative_cap
            for sig,rows in list(strata.items()):
                ordered=sorted(rows,key=lambda x:x["candidate_id"])
                trunc[f"{label}_truncated"]+=max(0,len(ordered)-cap)
                strata[sig]=ordered[:cap]
    return result,dict(trunc)


def _pair_record(source:str,edge:Mapping[str,Any],nonedge:Mapping[str,Any],cost:float=0.0)->dict[str,Any]:
    return {"pair_id":stable_hex(source,edge["candidate_id"],nonedge["candidate_id"]),"edge":dict(edge),"nonedge":dict(nonedge),"cost":float(cost)}


def coarse_pairs(source:str,pdoc:str,ndoc:str,pool:Mapping[str,Any],cap:int)->list[dict[str,Any]]:
    pos,neg=pool[pdoc]["positive"],pool[ndoc]["negative"]
    out=[]; used=set()
    for sig in sorted(set(pos)&set(neg),key=canonical_bytes):
        ps=sorted(pos[sig],key=lambda x:x["candidate_id"])
        ns=[x for x in sorted(neg[sig],key=lambda x:x["candidate_id"]) if x["base_pair_id"] not in used]
        for e,n in zip(ps,ns):
            if len(out)>=cap: break
            used.add(n["base_pair_id"]); out.append(_pair_record(source,e,n))
        if len(out)>=cap: break
    return out


def caliper_cost(edge:Mapping[str,Any],nonedge:Mapping[str,Any],cal:Mapping[str,float])->float|None:
    morph=sum(a!=b for a,b in zip(tuple(edge["later"]["morph"])+tuple(edge["earlier"]["morph"]),tuple(nonedge["later"]["morph"])+tuple(nonedge["earlier"]["morph"])))
    lg=abs(math.log2(float(edge["surface_gap"])/float(nonedge["surface_gap"])))
    rq=abs(float(edge["relative_query"])-float(nonedge["relative_query"])); cf=abs(float(edge["causal_fraction"])-float(nonedge["causal_fraction"]))
    le=abs(int(edge["sequence_length"])-int(nonedge["sequence_length"]))/max(int(edge["sequence_length"]),int(nonedge["sequence_length"]))
    if morph>cal["morph_hamming"] or lg>cal["log2_gap"] or rq>cal["relative_query"] or cf>cal["causal_fraction"] or le>cal["relative_length"]: return None
    return morph/16.0+lg+rq+cf+le


def _assign_stratum(source:str,ps:Sequence[Mapping[str,Any]],ns:Sequence[Mapping[str,Any]],cal:Mapping[str,float])->list[dict[str,Any]]:
    """Maximum-cardinality, then exact lexicographic integer-cost bipartite flow."""
    ps=sorted(ps,key=lambda x:x["candidate_id"]); ns=sorted(ns,key=lambda x:x["candidate_id"])
    admiss=[]
    for i,e in enumerate(ps):
        for j,n in enumerate(ns):
            c=caliper_cost(e,n,cal)
            if c is not None:
                digest=hashlib.sha256((e["candidate_id"]+"|"+n["candidate_id"]).encode()).hexdigest()
                admiss.append((i,j,c,digest))
    if not admiss:return []

    ranked=sorted(admiss,key=lambda x:(x[3],x[0],x[1])); rank={(i,j):r for r,(i,j,_,_) in enumerate(ranked)}
    # Any sum of the distinct lower A bits is < 2**A, so one primary
    # rounded-distance quantum always dominates the complete tie objective.
    A=len(admiss); scale=1<<A
    npos,nneg=len(ps),len(ns); source_node=0; pos0=1; neg0=pos0+npos; sink=neg0+nneg; nnode=sink+1
    graph:list[list[list[Any]]]=[[] for _ in range(nnode)]
    def add_edge(u:int,v:int,capacity:int,cost:int)->list[Any]:
        forward:list[Any]=[v,len(graph[v]),capacity,cost]
        reverse:list[Any]=[u,len(graph[u]),0,-cost]
        graph[u].append(forward);graph[v].append(reverse);return forward
    for i in range(npos):add_edge(source_node,pos0+i,1,0)
    for j in range(nneg):add_edge(neg0+j,sink,1,0)
    tracked=[]; costs={}
    for i,j,c,_ in sorted(admiss,key=lambda x:(x[0],x[1])):
        q=int(round(c*1_000_000_000));edge=add_edge(pos0+i,neg0+j,1,q*scale+(1<<rank[(i,j)]));tracked.append((i,j,edge));costs[(i,j)]=c

    # Successive shortest augmenting paths run until no path remains, making
    # cardinality primary. Potentials retain exact Python-int reduced costs.
    potential=[0]*nnode
    while True:
        dist:[int|None]=[None]*nnode;parent:[tuple[int,int]|None]=[None]*nnode;dist[source_node]=0;heap=[(0,source_node)]
        while heap:
            d,u=heapq.heappop(heap)
            if dist[u]!=d:continue
            for ei,e in enumerate(graph[u]):
                v,_,cap,cost=e
                if not cap:continue
                nd=d+cost+potential[u]-potential[v]
                if dist[v] is None or nd<dist[v]:
                    dist[v]=nd;parent[v]=(u,ei);heapq.heappush(heap,(nd,v))
        if dist[sink] is None:break
        for v,d in enumerate(dist):
            if d is not None:potential[v]+=d
        v=sink
        while v!=source_node:
            u,ei=parent[v]  # type: ignore[misc]
            edge=graph[u][ei];edge[2]-=1;graph[v][edge[1]][2]+=1;v=u
    chosen=[(i,j) for i,j,edge in tracked if edge[2]==0]
    return [_pair_record(source,ps[i],ns[j],costs[(i,j)]) for i,j in sorted(chosen)]


def optimal_pairs(source:str,pdoc:str,ndoc:str,pool:Mapping[str,Any],cap:int,cal:Mapping[str,float])->list[dict[str,Any]]:
    pos,neg=pool[pdoc]["positive"],pool[ndoc]["negative"]
    assigned=[]
    for sig in sorted(set(pos)&set(neg),key=canonical_bytes): assigned.extend(_assign_stratum(source,pos[sig],neg[sig],cal))
    used=set(); out=[]
    for pair in sorted(assigned,key=lambda x:(x["cost"],x["pair_id"])):
        base=pair["nonedge"]["base_pair_id"]
        if base in used: continue
        used.add(base); out.append(pair)
        if len(out)>=cap:break
    return out


def match_documents(source:str,pool:Mapping[str,Any],method:str,cfg:Mapping[str,Any])->list[dict[str,Any]]:
    docs=sorted(pool); left=[d for d in docs if int(stable_hex(source,d)[:16],16)&1==0]; right=[d for d in docs if int(stable_hex(source,d)[:16],16)&1==1]
    cached={}
    for i,ld in enumerate(left):
        for j,rd in enumerate(right):
            if method=="coarse_exact": lr=coarse_pairs(source,ld,rd,pool,cfg["pairs_per_document_direction"]); rl=coarse_pairs(source,rd,ld,pool,cfg["pairs_per_document_direction"])
            else: lr=optimal_pairs(source,ld,rd,pool,cfg["pairs_per_document_direction"],cfg["calipers"]); rl=optimal_pairs(source,rd,ld,pool,cfg["pairs_per_document_direction"],cfg["calipers"])
            if lr and rl: cached[(i,j)]=(lr,rl)
    if not cached:return []
    nr,nc=len(left),len(right); pair_count=nr*nc; max_matches=min(nr,nc); yield_base=max_matches*pair_count+1; card_base=max_matches*(2*cfg["pairs_per_document_direction"]*yield_base+pair_count)+1
    matrix=np.zeros((nr,nc),dtype=np.int64); ranked=sorted(cached,key=lambda ij:stable_hex(left[ij[0]],right[ij[1]]))
    for rank,(i,j) in enumerate(ranked):
        lr,rl=cached[(i,j)]; matrix[i,j]=card_base+(len(lr)+len(rl))*yield_base+(len(ranked)-rank)
    rr,cc=linear_sum_assignment(matrix,maximize=True); comps=[]
    for i,j in zip(rr.tolist(),cc.tolist()):
        if (i,j) not in cached:continue
        lr,rl=cached[(i,j)]; comps.append({"component_id":"component:"+stable_hex(source,left[i],right[j])[:24],"documents":sorted([left[i],right[j]]),"left_positive_pairs":lr,"right_positive_pairs":rl,"pair_count":len(lr)+len(rl)})
    return finalize_components(comps,cfg["maximum_components"],cfg["target_pairs"])


def finalize_components(components:Sequence[Mapping[str,Any]],max_components:int,target_pairs:int)->list[dict[str,Any]]:
    selected=deepcopy(sorted(components,key=lambda x:(-int(x["pair_count"]),str(x["component_id"])))[:max_components])
    mandatory=set(); remaining=[]
    for c in selected:
        for field in ("left_positive_pairs","right_positive_pairs"):
            rows=c[field]
            if rows:mandatory.add(rows[0]["pair_id"])
            remaining.extend(x["pair_id"] for x in rows[1:])
    if sum(int(c["pair_count"]) for c in selected)>=target_pairs and len(mandatory)<=target_pairs:
        keep=set(mandatory)
        for pid in sorted(remaining):
            if len(keep)>=target_pairs:break
            keep.add(pid)
        for c in selected:
            for f in ("left_positive_pairs","right_positive_pairs"):c[f]=[x for x in c[f] if x["pair_id"] in keep]
            c["pair_count"]=len(c["left_positive_pairs"])+len(c["right_positive_pairs"])
    totals=[0]*5
    for c in sorted(selected,key=lambda x:(-int(x["pair_count"]),str(x["component_id"]))):
        f=min(range(5),key=lambda k:(totals[k],k)); c["fold"]=f;totals[f]+=1
    return sorted(selected,key=lambda x:str(x["component_id"]))


def panel_rows(components:Sequence[Mapping[str,Any]])->tuple[list[dict[str,Any]],list[dict[str,Any]]]:
    rows=[];pairs=[]
    for c in sorted(components,key=lambda x:x["component_id"]):
        for field in ("left_positive_pairs","right_positive_pairs"):
            for p in sorted(c[field],key=lambda x:x["pair_id"]):
                rec={"pair_id":p["pair_id"],"component_id":c["component_id"],"fold":int(c["fold"]),"documents":c["documents"],"orientation":p["edge"]["orientation"],"cost":p.get("cost",0.0),"nonedge":p["nonedge"],"edge":p["edge"]}
                pairs.append(rec)
                for treatment,name in ((0,"nonedge"),(1,"edge")):
                    row=dict(p[name]);row.update({"treatment":treatment,"pair_id":p["pair_id"],"component_id":c["component_id"],"fold":int(c["fold"]),"documents":c["documents"]});rows.append(row)
    return rows,pairs


def support(components:Sequence[Mapping[str,Any]])->dict[str,Any]:
    pairs=[p for c in components for f in ("left_positive_pairs","right_positive_pairs") for p in c[f]]
    return {"components":len(components),"documents":len({d for c in components for d in c["documents"]}),"pairs":len(pairs),"orientations":dict(sorted(Counter(p["edge"]["orientation"] for p in pairs).items())),"fold_components":dict(sorted(Counter(str(c["fold"]) for c in components).items()))}


def _encode_parts(parts:Sequence[str])->bytes:
    return b"".join(struct.pack("<Q",len(x.encode()))+x.encode() for x in parts)

def signed_hash(parts:Sequence[tuple[str,str|Sequence[str]]],width:int)->np.ndarray:
    out=np.zeros(width)
    for field,value in parts:
        values=(value,) if isinstance(value,str) else tuple(value)
        d=hashlib.sha256(_encode_parts(("v4",field,*values))).digest(); idx=int.from_bytes(d[:8],"little")%width; out[idx]+=1.0 if (d[8]&1)==0 else -1.0
    return out


def design_matrix(rows:Sequence[Mapping[str,Any]],keys:Sequence[str],vocab:Mapping[str,Sequence[str]],width:int)->tuple[np.ndarray,list[str]]:
    categorical=[]
    fields=["later_upos","earlier_upos","later_punct","earlier_punct","later_subtokens","earlier_subtokens"]+[f"later_{k}" for k in keys]+[f"earlier_{k}" for k in keys]
    vals=[]
    for row in rows:
        late,early=row["later"],row["earlier"]
        parsed={"later_upos":late["upos"],"earlier_upos":early["upos"],"later_punct":str(bool(late["is_punct"])),"earlier_punct":str(bool(early["is_punct"])),"later_subtokens":str(late["subtokens"]),"earlier_subtokens":str(early["subtokens"])}
        parsed.update({f"later_{k}":late["morph"][i].split("=",1)[1] for i,k in enumerate(keys)});parsed.update({f"earlier_{k}":early["morph"][i].split("=",1)[1] for i,k in enumerate(keys)}); vals.append(parsed)
    levels={f:sorted({x[f] for x in vals},key=lambda s:s.encode()) for f in fields}
    names=list(NUMERIC_NAMES)
    for f in fields:
        names.extend(f"{f}={v}" for v in levels[f])
    names.extend(f"lexical_hash_{i}" for i in range(width))
    X=np.zeros((len(rows),len(names)),dtype=np.float64)
    offsets={};o=4
    for f in fields:offsets[f]=o;o+=len(levels[f])
    for i,(row,d) in enumerate(zip(rows,vals)):
        X[i,:4]=[math.log2(1+row["surface_gap"]),row["relative_query"],row["causal_fraction"],math.log2(row["sequence_length"])]
        for f in fields:X[i,offsets[f]+levels[f].index(d[f])]=1
        late,early=row["later"],row["earlier"]
        parts=(("child_form",row["child_form"]),("head_form",row["head_form"]),("child_lemma",row["child_lemma"]),("head_lemma",row["head_lemma"]),("ordered_form_pair",(late["form"],early["form"])),("ordered_lemma_pair",(late["lemma"],early["lemma"])))
        X[i,o:]=signed_hash(parts,width)
    return X,names


def base_weights(rows:Sequence[Mapping[str,Any]])->np.ndarray:
    if not rows:raise RuntimeError("empty weighting rows")
    treatments=[r.get("treatment") for r in rows]
    if any(isinstance(t,bool) or not isinstance(t,int) or t not in (0,1) for t in treatments):raise RuntimeError("invalid treatment labels")
    counts=Counter(r["component_id"] for r in rows if r["treatment"]==1);controls=Counter(r["component_id"] for r in rows if r["treatment"]==0);C=len(counts)
    if C==0 or counts!=controls or any(n<=0 for n in counts.values()):raise RuntimeError("unpaired component rows")
    out=np.asarray([1/(2*C*counts[r["component_id"]]) for r in rows],dtype=float)
    if out.shape!=(len(rows),) or not np.all(np.isfinite(out)) or np.any(out<=0) or not math.isclose(float(out.sum()),1.0,rel_tol=1e-12,abs_tol=1e-12):raise RuntimeError("invalid base weights")
    return out

def treatment_weights(rows:Sequence[Mapping[str,Any]])->np.ndarray:
    return 2*base_weights(rows)

def weighted_mean_var(x:np.ndarray,w:np.ndarray)->tuple[float,float]:
    x=np.asarray(x,float);w=np.asarray(w,float)
    if x.ndim!=1 or w.shape!=x.shape or x.size==0 or not np.all(np.isfinite(x)) or not np.all(np.isfinite(w)) or np.any(w<0) or not math.isfinite(float(w.sum())) or w.sum()<=0:raise RuntimeError("invalid weighted moment inputs")
    w=w/w.sum();m=float(w@x);v=float(w@((x-m)**2))
    if not math.isfinite(m) or not math.isfinite(v) or v<0:raise RuntimeError("nonfinite weighted moments")
    return m,v
def smd(x:np.ndarray,t:np.ndarray,w:np.ndarray)->float:
    x=np.asarray(x,float);t=np.asarray(t);w=np.asarray(w,float)
    if x.ndim!=1 or t.shape!=x.shape or w.shape!=x.shape or set(np.unique(t))!={0,1}:raise RuntimeError("invalid SMD inputs")
    m=[];v=[]
    for g in (0,1):
        mg,vg=weighted_mean_var(x[t==g],w[t==g]);m.append(mg);v.append(vg)
    den=math.sqrt((v[0]+v[1])/2)
    return 0.0 if den==0 and m[0]==m[1] else math.inf if den==0 else abs(m[1]-m[0])/den
def weighted_ks(x:np.ndarray,t:np.ndarray,w:np.ndarray)->float:
    x=np.asarray(x,float);t=np.asarray(t);w=np.asarray(w,float)
    if x.ndim!=1 or t.shape!=x.shape or w.shape!=x.shape or x.size==0 or not np.all(np.isfinite(x)) or not np.all(np.isfinite(w)) or np.any(w<0) or set(np.unique(t))!={0,1}:raise RuntimeError("invalid weighted KS inputs")
    grid=np.unique(x);vals=[]
    for g in (0,1):
        wg=w[t==g]
        if not math.isfinite(float(wg.sum())) or wg.sum()<=0:raise RuntimeError("invalid weighted KS denominator")
        wg=wg/wg.sum();xg=x[t==g];vals.append(np.asarray([wg[xg<=z].sum() for z in grid]))
    out=float(np.max(np.abs(vals[1]-vals[0])))
    if not math.isfinite(out) or not 0<=out<=1:raise RuntimeError("nonfinite weighted KS")
    return out


def propensity_diagnostics(X:np.ndarray,rows:Sequence[Mapping[str,Any]],seed:int,estimators:Mapping[str,Any],diagnostic_cfg:Mapping[str,Any])->dict[str,Any]:
    X=np.asarray(X,float)
    if X.ndim!=2 or X.shape[0]!=len(rows) or len(rows)==0 or not np.all(np.isfinite(X)):raise RuntimeError("nonfinite or malformed propensity design")
    t=np.asarray([r["treatment"] for r in rows]);fold=np.asarray([r["fold"] for r in rows]);comp=np.asarray([r["component_id"] for r in rows]);prop=np.full(len(rows),np.nan)
    if set(np.unique(t))!={0,1} or set(np.unique(fold))!=set(range(5)):raise RuntimeError("invalid propensity treatment/fold support")
    counts=Counter(comp[t==1])
    for f in range(5):
        tr=fold!=f;te=~tr
        if not np.any(te) or any(c not in counts or counts[c]<=0 for c in comp[tr]):raise RuntimeError("invalid propensity fold support")
        a=np.asarray([1/counts[c] for c in comp[tr]],float);a*=a.size/a.sum()
        if not np.all(np.isfinite(a)) or np.any(a<=0) or not math.isclose(float(a.mean()),1.0,rel_tol=1e-12,abs_tol=1e-12):raise RuntimeError("invalid propensity training weights")
        sc=StandardScaler().fit(X[tr],sample_weight=a);Z=sc.transform(X[tr]);Zte=sc.transform(X[te])
        if not np.all(np.isfinite(Z)) or not np.all(np.isfinite(Zte)):raise RuntimeError("nonfinite propensity scaling")
        with warnings.catch_warnings():
            warnings.simplefilter("error",ConvergenceWarning);model=LogisticRegression(C=estimators["logistic_c"],penalty="l2",solver="lbfgs",fit_intercept=True,class_weight=None,max_iter=estimators["logistic_max_iter"],tol=estimators["logistic_tol"],random_state=seed).fit(Z,t[tr],sample_weight=a)
        predicted=np.asarray(model.predict_proba(Zte))
        if predicted.shape!=(int(te.sum()),2) or not np.all(np.isfinite(predicted)):raise RuntimeError("nonfinite or malformed propensity predictions")
        prop[te]=predicted[:,1]
    if prop.shape!=(len(rows),) or not np.all(np.isfinite(prop)) or np.any((prop<0)|(prop>1)):raise RuntimeError("nonfinite or malformed propensity predictions")
    p=np.clip(prop,1e-6,1-1e-6);base=base_weights(rows);wf=np.where(t==1,base*(1-p),base*p)
    for g in (0,1):
        total=float(wf[t==g].sum())
        if not math.isfinite(total) or total<=0:raise RuntimeError("invalid overlap weight denominator")
        wf[t==g]/=total
    positive=wf[wf>0]
    if positive.size==0 or not np.all(np.isfinite(wf)) or np.median(positive)<=0:raise RuntimeError("nonfinite overlap weights")
    out={"raw_min":float(prop.min()),"raw_max":float(prop.max()),"central_fraction":float(np.mean((prop>=diagnostic_cfg["propensity_min"])&(prop<=diagnostic_cfg["propensity_max"]))),"weight_ratio":float(wf.max()/np.median(positive)),"propensities":prop,"weights":wf}
    if not all(math.isfinite(out[k]) for k in ("raw_min","raw_max","central_fraction","weight_ratio")) or not 0<=out["raw_min"]<=out["raw_max"]<=1 or not 0<=out["central_fraction"]<=1 or out["weight_ratio"]<=0:raise RuntimeError("invalid propensity diagnostics")
    return out


def diagnostics(rows:Sequence[Mapping[str,Any]],pairs:Sequence[Mapping[str,Any]],X:np.ndarray,names:Sequence[str],cfg:Mapping[str,Any],estimators:Mapping[str,Any],seed:int)->dict[str,Any]:
    X=np.asarray(X,float)
    if not rows or not pairs or X.ndim!=2 or X.shape[0]!=len(rows) or X.shape[1]!=len(names) or not np.all(np.isfinite(X)):raise RuntimeError("nonfinite or malformed diagnostic panel")
    t=np.asarray([r["treatment"] for r in rows]);w=treatment_weights(rows); C=len({r["component_id"] for r in rows});pc=Counter(p["component_id"] for p in pairs)
    if set(np.unique(t))!={0,1} or C<=0 or any(n<=0 for n in pc.values()) or not np.all(np.isfinite(w)) or np.any(w<=0) or any(not math.isclose(float(w[t==g].sum()),1.0,rel_tol=1e-12,abs_tol=1e-12) for g in (0,1)):raise RuntimeError("invalid diagnostic weights")
    numeric={"surface_gap":np.asarray([r["surface_gap"] for r in rows],float),"relative_query":np.asarray([r["relative_query"] for r in rows]),"causal_fraction":np.asarray([r["causal_fraction"] for r in rows]),"sequence_length":np.asarray([r["sequence_length"] for r in rows],float)}
    if any(v.shape!=(len(rows),) or not np.all(np.isfinite(v)) for v in numeric.values()):raise RuntimeError("nonfinite numeric diagnostic")
    smds={k:smd(v,t,w) for k,v in numeric.items()};ks={k:weighted_ks(v,t,w) for k,v in numeric.items()}
    indicator={};excluded={};lexical_width=int(estimators["lexical_hash_width"])
    for j,name in enumerate(names[4:-lexical_width],start=4):
        prev=float(np.mean(X[:,j]>0))
        if not math.isfinite(prev) or not 0<=prev<=1:raise RuntimeError("invalid indicator prevalence")
        if prev>=cfg["minimum_indicator_prevalence"]:indicator[name]={"prevalence":prev,"smd":smd(X[:,j],t,w)}
        else:excluded[name]={"prevalence":prev,"reason":"POOLED_PREVALENCE_BELOW_FROZEN_MINIMUM"}
    core_mismatch=sum(core_signature(p["edge"])!=core_signature(p["nonedge"]) for p in pairs)
    pairw=np.asarray([1/(C*pc[p["component_id"]]) for p in pairs]);prop=propensity_diagnostics(X,rows,seed,estimators,cfg)
    values={"core_mismatches":core_mismatch,"numeric_smd":smds,"numeric_ks":ks,"indicator_smd":indicator,"excluded_indicator_smd":excluded,"component_ess":float(C),"pair_ess":float(1/np.sum(pairw**2)),"max_component_weight":1/C,"max_document_contribution":1/(2*C),"propensity":{k:v for k,v in prop.items() if k not in {"propensities","weights"}}}
    reported=[*smds.values(),*ks.values(),*(x["smd"] for x in indicator.values()),*(x["prevalence"] for x in indicator.values()),*(x["prevalence"] for x in excluded.values()),values["component_ess"],values["pair_ess"],values["max_component_weight"],values["max_document_contribution"],*values["propensity"].values()]
    if not np.all(np.isfinite(np.asarray(reported,float))) or not np.all(np.isfinite(pairw)) or np.any(pairw<=0):raise RuntimeError("nonfinite diagnostic metric")
    values["eligible"]=bool(core_mismatch==0 and max(smds.values(),default=math.inf)<=cfg["maximum_smd"] and max((x["smd"] for x in indicator.values()),default=0)<=cfg["maximum_smd"] and max(ks.values(),default=math.inf)<=cfg["maximum_ks"] and C>=cfg["minimum_component_ess"] and values["pair_ess"]>=cfg["minimum_pair_ess"] and values["max_component_weight"]<=cfg["maximum_component_weight"] and values["max_document_contribution"]<=cfg["maximum_document_contribution"] and prop["central_fraction"]>=cfg["propensity_central_fraction"] and prop["weight_ratio"]<=cfg["maximum_overlap_weight_ratio"])
    return values


def component_interval(pair_values:np.ndarray,pairs:Sequence[Mapping[str,Any]])->dict[str,float]:
    if pair_values.shape!=(len(pairs),) or not np.all(np.isfinite(pair_values)):raise RuntimeError("nonfinite or malformed pair values")
    grouped=defaultdict(list)
    for x,p in zip(pair_values,pairs):grouped[p["component_id"]].append(float(x))
    d=np.asarray([np.mean(grouped[c]) for c in sorted(grouped)]); C=len(d); est=float(d.mean());se=float(d.std(ddof=1)/math.sqrt(C))
    if C<2 or not np.isfinite(se) or se==0:raise RuntimeError("invalid component interval")
    q=float(student_t.ppf(.975,C-1));lower=est-q*se;upper=est+q*se
    if not all(math.isfinite(x) for x in (est,q,lower,upper)):raise RuntimeError("nonfinite component interval")
    return {"estimate":est,"lower":lower,"upper":upper,"se":se,"components":C}


def ridge_pair_values(X:np.ndarray,y:np.ndarray,rows:Sequence[Mapping[str,Any]],pairs:Sequence[Mapping[str,Any]],cfg:Mapping[str,Any])->np.ndarray:
    t=np.asarray([r["treatment"] for r in rows]);fold=np.asarray([r["fold"] for r in rows]);comp=np.asarray([r["component_id"] for r in rows]);adjust=np.full(len(rows),np.nan);counts=Counter(comp[t==0])
    for f in range(5):
        tr=(fold!=f)&(t==0);te=fold==f;a=np.asarray([1/counts[c] for c in comp[tr]])
        sc=StandardScaler().fit(X[tr],sample_weight=a)
        with warnings.catch_warnings():
            warnings.simplefilter("error",ConvergenceWarning);m=Ridge(alpha=cfg["ridge_alpha"],fit_intercept=True,solver="lsqr",tol=cfg["ridge_tol"],max_iter=cfg["ridge_max_iter"]).fit(sc.transform(X[tr]),y[tr],sample_weight=a)
        coef=np.asarray(m.coef_);pred=sc.transform(X[te])@coef
        if coef.shape!=(X.shape[1],) or pred.shape!=(int(te.sum()),) or not np.all(np.isfinite(coef)) or not np.all(np.isfinite(pred)):raise RuntimeError("nonfinite or malformed ridge fit")
        adjust[te]=pred
    index={(r["pair_id"],r["treatment"]):i for i,r in enumerate(rows)}
    out=np.asarray([(y[index[(p["pair_id"],1)]]-adjust[index[(p["pair_id"],1)]])-(y[index[(p["pair_id"],0)]]-adjust[index[(p["pair_id"],0)]]) for p in pairs])
    if out.shape!=(len(pairs),) or not np.all(np.isfinite(out)):raise RuntimeError("nonfinite or malformed ridge pair values")
    return out


def lexical_dgp_score(rows:Sequence[Mapping[str,Any]],w:np.ndarray)->np.ndarray:
    values=[];digests={}
    for row in rows:
        late,early=row["later"],row["earlier"]
        entries=(("child_form",(row["child_form"],)),("head_form",(row["head_form"],)),("child_lemma",(row["child_lemma"],)),("head_lemma",(row["head_lemma"],)),("ordered_form_pair",(late["form"],early["form"])),("ordered_lemma_pair",(late["lemma"],early["lemma"])))
        s=0.0
        for field,value_parts in entries:
            identity=(field,*value_parts);d=hashlib.sha256(_encode_parts(("v4-dgp-lexical",*identity))).digest()
            if d in digests and digests[d]!=identity:raise RuntimeError("lexical SHA-256 collision")
            digests[d]=identity;z=int.from_bytes(d[:8],"little");s+=norm.ppf((z+.5)/(2**64))
        values.append(s/math.sqrt(6))
    x=np.asarray(values);m=float(w@x);sd=math.sqrt(float(w@((x-m)**2)))
    if not np.isfinite(sd) or sd==0:raise RuntimeError("invalid lexical score")
    return (x-m)*(.5/sd)


def sha256_u64(*parts:object)->int:return int.from_bytes(hashlib.sha256("|".join(map(str,parts)).encode()).digest()[:8],"little")

def replicate_draws(rows:Sequence[Mapping[str,Any]],matcher:str,family:str,positive:bool,seed:int,replicate:int,cfg:Mapping[str,Any])->tuple[list[str],np.ndarray,np.ndarray,np.ndarray|None]:
    if not rows:raise RuntimeError("empty synthetic panel")
    sources={r["source"] for r in rows}
    if len(sources)!=1:raise RuntimeError("mixed-source synthetic panel")
    components=sorted({r["component_id"] for r in rows});row_order=sorted(range(len(rows)),key=lambda i:(rows[i]["component_id"],rows[i]["pair_id"],rows[i]["treatment"]))
    if len({(r["component_id"],r["pair_id"],r["treatment"]) for r in rows})!=len(rows):raise RuntimeError("non-unique canonical synthetic row identity")
    rng=np.random.Generator(np.random.PCG64(sha256_u64(seed,next(iter(sources)),matcher,family,"positive" if positive else "null",replicate,"noise")))
    u=rng.standard_normal(len(components))*cfg["component_intercept_sd"];eps_canonical=rng.standard_normal(len(rows))*cfg["row_noise_sd"];eps=np.empty(len(rows),float);eps[np.asarray(row_order)]=eps_canonical
    v=rng.standard_normal(len(components))*cfg["component_treatment_sd"] if positive else None
    if not np.all(np.isfinite(u)) or not np.all(np.isfinite(eps)) or (v is not None and not np.all(np.isfinite(v))):raise RuntimeError("nonfinite synthetic draw")
    return components,u,eps,v


def dgp_mean(X:np.ndarray,names:Sequence[str],rows:Sequence[Mapping[str,Any]],matcher:str,family:str,seed:int,cfg:Mapping[str,Any])->np.ndarray:
    w=base_weights(rows);Xd=X[:,:-int(cfg["lexical_hash_width"])]; keep=[]
    for j in range(Xd.shape[1]):
        m=float(w@Xd[:,j]);sd=math.sqrt(float(w@((Xd[:,j]-m)**2)))
        if sd>0 and np.isfinite(sd):keep.append((names[j],(Xd[:,j]-m)/sd))
    if not keep:raise RuntimeError("no finite DGP columns")
    keep.sort(key=lambda z:z[0]);Z=np.stack([x for _,x in keep],axis=1);rng=np.random.Generator(np.random.PCG64(sha256_u64(seed,rows[0]["source"],matcher,family,"linear_coef")))
    score=Z@rng.standard_normal(Z.shape[1]);m=float(w@score);sd=math.sqrt(float(w@((score-m)**2)))
    if not math.isfinite(sd) or sd<=0:raise RuntimeError("invalid linear DGP scale")
    score=(score-m)*(cfg["linear_sd"]/sd)
    if family=="nonlinear":
        if Z.shape[1]<16:raise RuntimeError("too few nonlinear columns")
        I=np.stack([Z[:,2*k]*Z[:,2*k+1] for k in range(8)],axis=1);r=np.random.Generator(np.random.PCG64(sha256_u64(seed,rows[0]["source"],matcher,family,"interaction_coef")));q=I@r.standard_normal(8);qm=float(w@q);qs=math.sqrt(float(w@((q-qm)**2)))
        if not math.isfinite(qs) or qs<=0:raise RuntimeError("invalid nonlinear DGP scale")
        score=score+(q-qm)*(cfg["interaction_sd"]/qs)
    elif family=="lexical":score=score+lexical_dgp_score(rows,w)*(cfg["lexical_sd"]/.5)
    return score


def simulate_panel(X:np.ndarray,names:Sequence[str],rows:Sequence[Mapping[str,Any]],pairs:Sequence[Mapping[str,Any]],matcher:str,config:Mapping[str,Any],seed:int,replicates:int|None=None)->dict[str,Any]:
    cfg=config["simulation"];estimators=config["estimators"];reps=replicates or cfg["replicates"];t=np.asarray([r["treatment"] for r in rows]);w=base_weights(rows); overlap_w=propensity_diagnostics(X,rows,seed,estimators,config["diagnostics"])["weights"]; components=sorted({r["component_id"] for r in rows});ci={c:i for i,c in enumerate(components)};out={}
    lexical_width=int(estimators["lexical_hash_width"])
    for dgp in cfg["dgps"]:
        family=dgp.split("_",1)[0];positive=dgp.endswith("positive");mu=dgp_mean(X,names,rows,matcher,family,seed,{**cfg,"lexical_hash_width":lexical_width});metrics={e:[] for e in ("paired_mean","control_ridge_residualized")};truth=[];ato_est=[];ato_truth=[]
        for r in range(reps):
            draw_components,u,eps,v=replicate_draws(rows,matcher,family,positive,seed,r,cfg)
            if draw_components!=components:raise RuntimeError("synthetic component order drift")
            y0=mu+np.asarray([u[ci[x["component_id"]]] for x in rows])+eps
            if positive:
                ym=float(w@y0);sd=math.sqrt(float(w@((y0-ym)**2)))
                if not math.isfinite(sd) or sd<=0:raise RuntimeError("invalid positive-effect scale")
                if v is None:raise RuntimeError("missing positive treatment draw")
                tau=cfg["effect_sd"]*sd;effect=np.asarray([tau+v[ci[x["component_id"]]] for x in rows]);true=float(np.mean(tau+v))
            else:effect=np.zeros(len(rows));true=0.0
            y=y0+t*effect;idx={(x["pair_id"],x["treatment"]):i for i,x in enumerate(rows)};pd=np.asarray([y[idx[(p["pair_id"],1)]]-y[idx[(p["pair_id"],0)]] for p in pairs]);metrics["paired_mean"].append(component_interval(pd,pairs));rd=ridge_pair_values(X,y,rows,pairs,estimators);metrics["control_ridge_residualized"].append(component_interval(rd,pairs));truth.append(true);ato_est.append(float(overlap_w[t==1]@y[t==1]-overlap_w[t==0]@y[t==0]));ato_truth.append(float(overlap_w[t==1]@effect[t==1]))
        cell={}
        for est,vals in metrics.items():
            estimates=np.asarray([x["estimate"] for x in vals]);lo=np.asarray([x["lower"] for x in vals]);hi=np.asarray([x["upper"] for x in vals]);tr=np.asarray(truth);coverage=float(np.mean((lo<=tr)&(tr<=hi)));reject=float(np.mean((lo>0)|(hi<0)));power=float(np.mean(lo>0)) if positive else None
            cell[est]={"replicates":reps,"bias":float(np.mean(estimates-tr)),"coverage":coverage,"rejection":reject,"power":power,"finite":bool(np.all(np.isfinite(estimates)))}
        ae=np.asarray(ato_est);at=np.asarray(ato_truth);cell["overlap_ato_descriptive"]={"replicates":reps,"mean_estimate":float(ae.mean()),"mean_true_target":float(at.mean()),"bias":float(np.mean(ae-at)),"finite":bool(np.all(np.isfinite(ae))),"nominating":False}
        out[dgp]=cell
    return out
