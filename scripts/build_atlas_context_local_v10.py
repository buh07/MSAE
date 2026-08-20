#!/usr/bin/env python3
"""Label/text/tokenizer-only prescore builder for Attempt 14. Never loads model weights."""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import unicodedata
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

import networkx as nx
import numpy as np
from transformers import AutoTokenizer

from atlas_context_local_v10 import NAMESPACE, ROOT, atomic_json, atomic_jsonl, bootstrap_indices, canonical_json_bytes, read_json, sha256_file, stable_hex, stable_u64

@dataclass
class Tok:
    wid: int
    form: str
    lemma: str
    upos: str
    feats: str
    misc: str
    in_mwt: bool = False
    span: tuple[int,int] | None = None

@dataclass
class Sent:
    source: str
    doc_id: str
    sent_id: str
    text: str
    tokens: list[Tok]
    mwt_rows: list[tuple[int,int,str,str]]
    ids: list[int]
    offsets: list[tuple[int,int]]
    target_ids: list[int]
    target_offsets: list[tuple[int,int]]
    split: str
    index_in_doc: int = -1


def norm(s: str) -> str:
    return unicodedata.normalize("NFKC", s).lower()


def cap_class(s: str) -> str:
    letters = [c for c in s if c.isalpha()]
    if not letters: return "noalpha"
    if all(c.islower() for c in letters): return "lower"
    if all(c.isupper() for c in letters): return "upper"
    if s[:1].isupper() and all(not c.isalpha() or c.islower() for c in s[1:]): return "title"
    return "mixed"


def canon_feats(s: str) -> str:
    if s == "_": return ""
    return "|".join(sorted(s.split("|")))


def parse_blocks(path: Path) -> Iterable[tuple[dict[str,str],list[list[str]]]]:
    for block in path.read_text(encoding="utf-8").strip().split("\n\n"):
        meta: dict[str,str] = {}; rows=[]
        for line in block.splitlines():
            if line.startswith("# ") and " = " in line:
                k,v=line[2:].split(" = ",1); meta[k]=v
            elif line and not line.startswith("#"):
                cols=line.split("\t")
                if len(cols)==10: rows.append(cols)
        if rows: yield meta,rows


def reconstruct(rows: list[list[str]]) -> tuple[str,list[Tok],list[tuple[int,int,str,str]]]:
    ints: dict[int,Tok] = {}; mwts=[]; mwt_by_start={}; covered=set()
    for c in rows:
        if "-" in c[0]:
            a,b=map(int,c[0].split("-")); m=(a,b,c[1],c[9]); mwts.append(m); mwt_by_start[a]=m; covered.update(range(a,b+1))
        elif c[0].isdigit():
            i=int(c[0]); ints[i]=Tok(i,c[1],c[2],c[3],canon_feats(c[5]),c[9],i in covered)
    # Re-mark after all MWTs are known.
    for i,t in ints.items(): t.in_mwt=i in covered
    units=[]; i=1; max_i=max(ints) if ints else 0
    while i<=max_i:
        if i in mwt_by_start:
            a,b,form,misc=mwt_by_start[i]; units.append((form,misc,None)); i=b+1
        elif i in covered:
            i+=1
        elif i in ints:
            units.append((ints[i].form,ints[i].misc,ints[i])); i+=1
        else: i+=1
    out=""; prev_misc=None
    for j,(form,misc,tok) in enumerate(units):
        if j and (prev_misc is None or "SpaceAfter=No" not in prev_misc.split("|")):
            out += " "
        start=len(out); out+=form; end=len(out)
        if tok is not None: tok.span=(start,end)
        prev_misc=misc
    return out,[ints[i] for i in sorted(ints)],mwts


def token_span_index(surface: str, offsets: list[tuple[int,int]], span: tuple[int,int]) -> int | None:
    found=[]
    for j,(a,b) in enumerate(offsets):
        aa=a
        while aa < b and surface[aa].isspace(): aa += 1
        if (aa,b)==span: found.append(j)
    return found[0] if len(found)==1 else None


def exact_tokenize(tok: Any, surface: str) -> tuple[list[int],list[tuple[int,int]]]:
    x=tok(surface,add_special_tokens=False,return_offsets_mapping=True)
    return list(map(int,x["input_ids"])),[tuple(map(int,z)) for z in x["offset_mapping"]]


def load_sentences(config: dict[str,Any], tokenizer: Any) -> tuple[dict[str,dict[str,list[Sent]]],dict[str,Any]]:
    root=ROOT/config["raw_root"]
    docs={s:{} for s in config["sources"]}; exact_fail=[]; seen_docs=set(); current_doc=None
    counts=Counter()
    for filename in config["raw_files"]:
        path=root/filename
        if sha256_file(path)!=config["raw_files"][filename]: raise RuntimeError(f"raw hash drift: {filename}")
        for meta,rows in parse_blocks(path):
            if "newdoc id" in meta: current_doc=meta["newdoc id"]
            if not current_doc or current_doc in seen_docs and current_doc not in {d for sd in docs.values() for d in sd}:
                pass
            source=next((s for s,v in config["sources"].items() if current_doc.startswith(v["newdoc_prefix"])),None)
            if source is None: continue
            surface,tokens,mwts=reconstruct(rows); text=meta.get("text","")
            if surface != text:
                exact_fail.append({"doc_id":current_doc,"sent_id":meta.get("sent_id"),"surface":surface,"text":text}); continue
            ids,offs=exact_tokenize(tokenizer,surface); tids,toffs=exact_tokenize(tokenizer," "+surface)
            sent=Sent(source,current_doc,meta.get("sent_id",f"{filename}:{counts[source]}"),surface,tokens,mwts,ids,offs,tids,toffs,filename)
            docs[source].setdefault(current_doc,[]).append(sent); counts[source]+=1; seen_docs.add(current_doc)
    for source,sd in docs.items():
        for did,ss in sd.items():
            for i,s in enumerate(ss): s.index_in_doc=i
    return docs,{"exact_surface_failure_count":len(exact_fail),"exact_surface_failures":exact_fail[:20],"sentence_counts":dict(counts)}


def collision_filter(docs: dict[str,dict[str,list[Sent]]]) -> tuple[set[tuple[str,str]],set[tuple[str,str,str]],dict[str,Any]]:
    sigmap=defaultdict(list)
    for source,sd in docs.items():
        for did,ss in sd.items():
            for s in ss:
                sigs=["forms:"+json.dumps([t.form for t in s.tokens],ensure_ascii=False,separators=(",",":")),
                      "text:"+" ".join(norm(s.text).split()),
                      "ids:"+json.dumps(s.ids,separators=(",",":"))]
                for sig in sigs: sigmap[sig].append((source,did,s.sent_id,s.text))
    collisions={k:v for k,v in sigmap.items() if len({x[0] for x in v})>1}
    identities=defaultdict(set); rows=[]
    for sig,occ in collisions.items():
        ident=hashlib.sha256(sig.encode()).hexdigest()
        for source,did,sid,text in occ: identities[(source,did)].add(ident)
        rows.append({"identity":ident,"kind":sig.split(":",1)[0],"occurrences":[list(x[:3]) for x in occ],"normalized_length":max(len(" ".join(norm(x[3]).split())) for x in occ)})
    remove_docs=set(); remove_sents=set()
    # Whole-document canonical text equality.
    docmap=defaultdict(list)
    for source,sd in docs.items():
        for did,ss in sd.items(): docmap[tuple(norm(s.text) for s in ss)].append((source,did))
    for occ in docmap.values():
        if len({x[0] for x in occ})>1: remove_docs.update(occ)
    for row in rows:
        occ=[tuple(x) for x in row["occurrences"]]
        if row["normalized_length"]>=20: remove_docs.update((a,b) for a,b,_ in occ)
    for key,ids in identities.items():
        if len(ids)>=2: remove_docs.add(key)
    for row in rows:
        if row["normalized_length"]<20:
            for source,did,sid in map(tuple,row["occurrences"]):
                if (source,did) not in remove_docs: remove_sents.add((source,did,sid))
    return remove_docs,remove_sents,{"collision_identity_count":len(rows),"rows":rows,"removed_documents":[list(x) for x in sorted(remove_docs)],"removed_sentences":[list(x) for x in sorted(remove_sents)]}


def freq_quartiles(source_docs: dict[str,list[Sent]]) -> dict[str,int]:
    df=Counter()
    for ss in source_docs.values():
        forms={norm(t.form) for s in ss for t in s.tokens}
        df.update(forms)
    ordered=sorted(df,key=lambda x:(df[x],x)); n=len(ordered)
    return {f:min(3,(4*i)//max(n,1)) for i,f in enumerate(ordered)}


def eligible_token(sent: Sent, token: Tok, target_segment: bool=True) -> int | None:
    if token.in_mwt or token.span is None or token.upos not in {"NOUN","VERB","ADJ","ADV","PROPN"}: return None
    surface=(" "+sent.text) if target_segment else sent.text
    offsets=sent.target_offsets if target_segment else sent.offsets
    span=(token.span[0]+1,token.span[1]+1) if target_segment else token.span
    return token_span_index(surface,offsets,span)


def replacement(sent: Sent, token: Tok, donor_form: str, tokenizer: Any, control: Tok) -> tuple[list[int],int,int] | None:
    assert token.span is not None and control.span is not None
    sub_text=sent.text[:token.span[0]]+donor_form+sent.text[token.span[1]:]
    ids,offs=exact_tokenize(tokenizer," "+sub_text)
    if len(ids)!=len(sent.target_ids): return None
    diffs=[i for i,(a,b) in enumerate(zip(ids,sent.target_ids)) if a!=b]
    ti=eligible_token(sent,token,True)
    if ti is None or diffs!=[ti]: return None
    shift=len(donor_form)-len(token.form); cspan=(control.span[0]+shift+1,control.span[1]+shift+1)
    ci=token_span_index(" "+sub_text,offs,cspan)
    old_ci=eligible_token(sent,control,True)
    if ci is None or ci!=old_ci: return None
    return ids,ti,ci


def build_source(source: str, docs: dict[str,list[Sent]], remove_docs:set[tuple[str,str]], remove_sents:set[tuple[str,str,str]], tokenizer:Any, config:dict[str,Any]) -> tuple[list[dict[str,Any]],dict[str,Any]]:
    good={d:ss for d,ss in docs.items() if (source,d) not in remove_docs}
    q=freq_quartiles(good); open_set=set(config["intervention"]["open_class_upos"])
    prefix_by_len=defaultdict(lambda:defaultdict(list)); donor_by_attr=defaultdict(lambda:defaultdict(list))
    for did,ss in good.items():
        for s in ss:
            if (source,did,s.sent_id) in remove_sents: continue
            if s.ids: prefix_by_len[len(s.ids)][did].append(s)
            for t in s.tokens:
                j=eligible_token(s,t,False)
                if j is None or t.upos not in open_set: continue
                attr=(t.upos,t.feats,cap_class(t.form),q.get(norm(t.form),-1))
                donor_by_attr[attr][did].append((s,t,j))
    # Every eligible adjacent target option. Removed sentences create gaps.
    options=defaultdict(list)
    for did,ss in good.items():
        for i in range(1,len(ss)):
            prev,target=ss[i-1],ss[i]
            if (source,did,prev.sent_id) in remove_sents or (source,did,target.sent_id) in remove_sents: continue
            if prev.index_in_doc+1 != target.index_in_doc: continue
            if len(prev.ids)+len(target.target_ids)>config["model"]["max_positions"]: continue
            # Natural-boundary identity for true prefix.
            combo,_=exact_tokenize(tokenizer,prev.text+" "+target.text)
            if combo != prev.ids+target.target_ids: continue
            for pos,t in enumerate(target.tokens):
                ti=eligible_token(target,t,True)
                if ti is None: continue
                control=None
                for off in range(1,9):
                    if pos+off>=len(target.tokens): break
                    c=target.tokens[pos+off]
                    if c.upos!="PUNCT" and eligible_token(target,c,True) is not None:
                        control=c; break
                if control is None or control.wid-t.wid not in range(1,9): continue
                attr=(t.upos,t.feats,cap_class(t.form),q.get(norm(t.form),-1))
                if attr not in donor_by_attr: continue
                options[did].append((stable_hex(config["seed"],source,"target",did,target.sent_id,t.wid),prev,target,t,control,attr))
        options[did].sort(key=lambda x:x[0])
    edges: dict[tuple[str,str],dict[str,Any]]={}; selected_target_docs=0
    for target_doc in sorted(options):
        chosen_edges=[]
        for _,prev,target,t,control,attr in options[target_doc]:
            possible_docs=set(prefix_by_len[len(prev.ids)]) & set(donor_by_attr[attr]); possible_docs.discard(target_doc)
            local=[]
            for donor_doc in sorted(possible_docs):
                prefix_candidates=sorted(prefix_by_len[len(prev.ids)][donor_doc],key=lambda s:stable_hex(config["seed"],source,"prefix",target_doc,donor_doc,s.sent_id))
                occs=sorted(donor_by_attr[attr][donor_doc],key=lambda x:stable_hex(config["seed"],source,"donor",target_doc,donor_doc,x[0].sent_id,x[1].wid))
                best=None
                for up in prefix_candidates:
                    combo,_=exact_tokenize(tokenizer,up.text+" "+target.text)
                    if combo != up.ids+target.target_ids: continue
                    upforms={norm(x.form) for x in up.tokens}; trueforms={norm(x.form) for x in prev.tokens}; targetforms={norm(x.form) for x in target.tokens if x.wid!=t.wid}
                    for ds,dt,_ in occs:
                        if norm(dt.form)==norm(t.form) or norm(dt.lemma)==norm(t.lemma): continue
                        if norm(dt.form) in upforms or norm(dt.form) in trueforms or norm(dt.form) in targetforms: continue
                        rep=replacement(target,t,dt.form,tokenizer,control)
                        if rep is None: continue
                        subids,ti,ci=rep
                        subtext=target.text[:t.span[0]]+dt.form+target.text[t.span[1]:]  # type: ignore[index]
                        subcombo,_=exact_tokenize(tokenizer,prev.text+" "+subtext)
                        if subcombo != prev.ids+subids: continue
                        cand=(stable_hex(config["seed"],source,"edge",target_doc,donor_doc,prev.sent_id,target.sent_id,t.wid,up.sent_id,ds.sent_id,dt.wid),up,ds,dt,subids,ti,ci)
                        if best is None or cand[0]<best[0]: best=cand
                if best is not None:
                    _,up,ds,dt,subids,ti,ci=best
                    comp={"source":source,"target_doc_id":target_doc,"donor_doc_id":donor_doc,
                          "true_prefix_sent_id":prev.sent_id,"target_sent_id":target.sent_id,"unrelated_prefix_sent_id":up.sent_id,
                          "lexical_donor_sent_id":ds.sent_id,"target_word_id":t.wid,"control_word_id":control.wid,
                          "donor_word_id":dt.wid,"target_form":t.form,"target_lemma":t.lemma,"donor_form":dt.form,"donor_lemma":dt.lemma,
                          "upos":t.upos,"feats":t.feats,"capitalization":cap_class(t.form),"document_frequency_quartile":attr[3],
                          "true_prefix_text":prev.text,"unrelated_prefix_text":up.text,"target_text":target.text,
                          "true_prefix_ids":prev.ids,"unrelated_prefix_ids":up.ids,"target_segment_ids":target.target_ids,
                          "substituted_target_segment_ids":subids,"target_sequence_index":len(prev.ids)+ti,
                          "control_sequence_index":len(prev.ids)+ci,"prefix_length":len(prev.ids),"sequence_length":len(prev.ids)+len(target.target_ids),
                          "target_to_control_word_offset":control.wid-t.wid,
                          "edge_hash":best[0]}
                    comp["component_id"]=stable_hex(config["seed"],source,target_doc,donor_doc,comp["edge_hash"])
                    local.append(comp)
            if local:
                chosen_edges=local; selected_target_docs+=1; break
        for comp in chosen_edges:
            pair=tuple(sorted((comp["target_doc_id"],comp["donor_doc_id"])))
            if pair not in edges or comp["edge_hash"]<edges[pair]["edge_hash"]: edges[pair]=comp
    # Undirected document matching enforces no document reuse across either role.
    graph=nx.Graph()
    candidates=sorted(edges.values(),key=lambda x:x["edge_hash"])
    for rank,c in enumerate(candidates):
        # Higher weight favors earlier salted edge; cardinality is primary.
        graph.add_edge(c["target_doc_id"],c["donor_doc_id"],weight=len(candidates)-rank,component=c)
    matching=nx.algorithms.matching.max_weight_matching(graph,maxcardinality=True,weight="weight")
    comps=[]
    for a,b in matching:
        c=graph.get_edge_data(a,b)["component"]
        comps.append(c)
    comps.sort(key=lambda x:x["component_id"])
    report={"source":source,"documents_after_collision":len(good),"multi_sentence_documents_after_collision":sum(len(x)>=2 for x in good.values()),
            "target_docs_with_options":len(options),"target_docs_with_at_least_one_edge":selected_target_docs,"candidate_document_edges":len(candidates),
            "matched_components":len(comps),"unique_target_docs":len({x["target_doc_id"] for x in comps}),
            "unique_donor_docs":len({x["donor_doc_id"] for x in comps}),"unique_all_docs":len({y for x in comps for y in (x["target_doc_id"],x["donor_doc_id"])})}
    return comps,report


def main() -> None:
    ap=argparse.ArgumentParser(); ap.add_argument("--config",default="configs/atlas_context_local_v10/run.json"); ap.add_argument("--output",required=True)
    args=ap.parse_args(); config=read_json(ROOT/args.config); out=ROOT/args.output
    tokenizer=AutoTokenizer.from_pretrained(config["model"]["name"],revision=config["model"]["revision"],local_files_only=True,use_fast=True)
    if tokenizer.eos_token_id!=0 or tokenizer.__class__.__name__!="GPTNeoXTokenizerFast": raise RuntimeError("tokenizer contract drift")
    docs,parse_report=load_sentences(config,tokenizer)
    if parse_report["exact_surface_failure_count"]: raise RuntimeError(f"surface reconstruction failures: {parse_report['exact_surface_failure_count']}")
    remove_docs,remove_sents,collision=collision_filter(docs)
    all_components={}; source_reports={}
    for source in config["sources"]:
        comps,rep=build_source(source,docs[source],remove_docs,remove_sents,tokenizer,config); all_components[source]=comps; source_reports[source]=rep
    out.mkdir(parents=True,exist_ok=True)
    files={}
    for source,comps in all_components.items():
        p=out/f"{source}.components.jsonl"; h,n=atomic_jsonl(p,comps); files[p.name]={"sha256":h,"rows":n}
        specs=[]
        for endpoint in ["raw_dtrue","raw_dcontext","raw_dlexical","raw_dunrelated","gate6"]:
            specs.append((f"within_{source}",endpoint,"source"))
        names=list(config["sources"])
        for fit,test in [(names[0],names[1]),(names[1],names[0])]:
            direction=f"{fit}_to_{test}"; role="fit" if source==fit else "test"
            for endpoint in ["gate1","gate2","gate3","gate4","gate5"]: specs.append((direction,endpoint,role))
        maps={}; min_distinct=10**9; support_draws={}
        for direction,endpoint,role in specs:
            key=f"{direction}__{endpoint}__{role}"
            u=np.empty((config["analysis"]["bootstrap_draws"],len(comps)),dtype=np.uint64)
            for d in range(u.shape[0]):
                for slot in range(u.shape[1]):
                    u[d,slot]=stable_u64(NAMESPACE,config["seed"],direction,endpoint,source,role,d,slot)
            maps[key]=u
            mapped=bootstrap_indices(u,len(comps)) if len(comps) else np.empty_like(u,dtype=np.int64)
            distinct=np.array([len(set(map(int,row))) for row in mapped],dtype=int) if len(comps) else np.zeros(u.shape[0],int)
            min_distinct=min(min_distinct,int(distinct.min()) if len(distinct) else 0)
            support_draws[key]=int(np.sum(distinct>=config["intervention"]["minimum_distinct_bootstrap_components"]))
        keys=list(maps); bp=out/f"{source}.bootstrap_maps.uint64.npy"; np.save(bp,np.stack([maps[k] for k in keys]),allow_pickle=False)
        kp=out/f"{source}.bootstrap_map_keys.json"; atomic_json(kp,{"schema_version":"atlas_context_local_v10_attempt14_bootstrap_keys_v1","keys":keys})
        files[bp.name]={"sha256":sha256_file(bp),"map_count":len(maps),"shape":[len(maps),config["analysis"]["bootstrap_draws"],len(comps)]}
        files[kp.name]={"sha256":sha256_file(kp),"keys":len(keys)}
        source_reports[source]["bootstrap_namespace_support_draws"] = support_draws
        source_reports[source]["minimum_distinct_components_across_all_maps"] = min_distinct
    vocab=tokenizer.get_vocab(); tok_contract={"class":tokenizer.__class__.__name__,"name":config["model"]["name"],"revision":config["model"]["revision"],
        "vocab_sha256":hashlib.sha256(canonical_json_bytes(vocab)).hexdigest(),"vocab_size":len(vocab),"eos_token_id":tokenizer.eos_token_id,
        "natural_boundary":" ","add_special_tokens":False}
    support_ok=all(r["documents_after_collision"]>=config["intervention"]["minimum_documents"]
        and r["matched_components"]>=config["intervention"]["minimum_components"]
        and all(v>=config["intervention"]["minimum_bootstrap_support_draws"] for v in r["bootstrap_namespace_support_draws"].values())
        for r in source_reports.values())
    manifest={"schema_version":"atlas_context_local_v10_attempt14_prescore_v1","status":"PRESCORE_ELIGIBLE" if support_ok else "PRESCORE_INELIGIBLE_STOP_NO_TRAINING",
        "model_inference_performed":False,"neural_training_performed":False,"config_sha256":sha256_file(ROOT/args.config),"raw_files":config["raw_files"],
        "parse_report":parse_report,"collision_report":collision,"tokenizer_contract":tok_contract,"source_reports":source_reports,"files":files,
        "no_backfill":True,"full_matching_not_truncated":True}
    atomic_json(out/"manifest.json",manifest)
    print(json.dumps(manifest,indent=2,ensure_ascii=False))

if __name__=="__main__": main()
