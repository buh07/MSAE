#!/usr/bin/env python3
"""Frozen endpoint-specific projection analysis for Attempt 14; no model forward or training."""
from __future__ import annotations
import argparse,json
from pathlib import Path
from typing import Any,Callable
import numpy as np
from atlas_context_local_v10 import (ROOT,atomic_json,atomic_jsonl,bootstrap_indices,capture_rows,complement_rows,
    gate4_energy_rows,normalized_pair_delta,normalized_vector_norm,projector,read_json,read_jsonl,sha256_file)


def finite_float(x:Any)->float|None:
    try: y=float(x)
    except (TypeError,ValueError): return None
    return y if np.isfinite(y) else None

def safe_mean(x:np.ndarray)->float|None:
    a=np.asarray(x,float)
    return finite_float(np.mean(a)) if a.size and np.isfinite(a).all() else None

def interval(values:list[float|None],qs:list[float])->dict[str,Any]:
    a=np.asarray([x for x in values if x is not None and np.isfinite(x)],float)
    if not len(a): return {"finite_draws":0,"lower":None,"median":None,"upper":None}
    q=np.quantile(a,qs,method="linear")
    return {"finite_draws":int(len(a)),"lower":float(q[0]),"median":float(q[1]),"upper":float(q[2])}

def gate_state(estimable:bool,passes:bool|None,reasons:list[str])->dict[str,Any]:
    if not estimable: return {"status":"INELIGIBLE","pass":None,"reasons":reasons}
    return {"status":"PASS" if passes else "FAIL","pass":bool(passes),"reasons":[]}

def load_maps(prepared:Path,source:str)->dict[str,np.ndarray]:
    keys=read_json(prepared/f"{source}.bootstrap_map_keys.json")["keys"]
    a=np.load(prepared/f"{source}.bootstrap_maps.uint64.npy",allow_pickle=False)
    if a.shape[0]!=len(keys): raise RuntimeError("bootstrap key/array mismatch")
    return {str(k):a[i] for i,k in enumerate(keys)}

def load_source(prepared:Path,cache:Path,source:str,cfg:dict[str,Any])->dict[str,Any]:
    rows=read_jsonl(prepared/f"{source}.components.jsonl"); z=np.load(cache/f"{source}.representations.npz",allow_pickle=False)
    if [str(x) for x in z["component_ids"].tolist()]!=[x["component_id"] for x in rows]: raise RuntimeError(f"cache row lineage mismatch: {source}")
    t=np.asarray(z["target"],np.float64); c=np.asarray(z["control"],np.float64); expected=(len(rows),5,cfg["model"]["width"])
    if t.shape!=expected or c.shape!=expected: raise RuntimeError("cache shape drift")
    context_condition_finite=np.isfinite(t[:,:4,:]).all(axis=2); context_finite=context_condition_finite.all(axis=1)
    masked=normalized_pair_delta(t[:,0,:],t[:,2,:]); downstream_masked=normalized_pair_delta(c[:,0,:],c[:,2,:])
    masked_failure=context_finite & (masked>cfg["analysis"]["technical_equivalence_threshold"])
    context_failure=(~context_finite)|masked_failure; context_mask=~context_failure
    lex_parts={"original_target":np.isfinite(t[:,1,:]).all(axis=1),"substituted_target":np.isfinite(t[:,4,:]).all(axis=1),
      "original_control":np.isfinite(c[:,1,:]).all(axis=1),"substituted_control":np.isfinite(c[:,4,:]).all(axis=1)}
    lexical_mask=np.logical_and.reduce(list(lex_parts.values())); joint_mask=context_mask&lexical_mask
    dtrue=t[:,1]-t[:,0]; dunrel=t[:,3]-t[:,2]; dcontext=dtrue-dunrel; dlex=t[:,4]-t[:,1]; dlex_control=c[:,4]-c[:,1]
    norms={"dtrue":normalized_vector_norm(dtrue,t[:,1],t[:,0]),"dunrelated":normalized_vector_norm(dunrel,t[:,3],t[:,2]),
      "dcontext":normalized_vector_norm(dcontext,dtrue,dunrel),"dlexical":normalized_vector_norm(dlex,t[:,4],t[:,1]),
      "dlexical_control":normalized_vector_norm(dlex_control,c[:,4],c[:,1])}
    return {"rows":rows,"t":t,"c":c,"context_condition_finite":context_condition_finite,"context_finite":context_finite,
      "masked":masked,"masked_failure":masked_failure,"context_failure":context_failure,"downstream_masked":downstream_masked,"lex_parts":lex_parts,
      "context_idx":np.flatnonzero(context_mask),"lexical_idx":np.flatnonzero(lexical_mask),"joint_idx":np.flatnonzero(joint_mask),
      "dtrue":dtrue,"dunrelated":dunrel,"dcontext":dcontext,"dlexical":dlex,"dlexical_control":dlex_control,"norms":norms,"maps":load_maps(prepared,source)}

def resample(data:dict[str,Any],pop:np.ndarray,draw:int,key:str)->np.ndarray:
    n=len(pop)
    if not n: return np.empty(0,dtype=np.int64)
    u=data["maps"][key]
    if u.shape[1]<n: raise RuntimeError("bootstrap map shorter than population")
    return pop[bootstrap_indices(u[draw:draw+1,:n],n)[0]]

def raw_effect(data:dict[str,Any],source:str,pop_key:str,norm_key:str,map_endpoint:str,cfg:dict[str,Any],decision_role:bool=True)->dict[str,Any]:
    pop=data[pop_key]; vals=data["norms"][norm_key][pop]; point=finite_float(np.median(vals)) if len(vals) else None; boots=[]
    key=f"within_{source}__{map_endpoint}__source"
    for d in range(cfg["analysis"]["bootstrap_draws"]):
        idx=resample(data,pop,d,key); boots.append(finite_float(np.median(data["norms"][norm_key][idx])) if len(idx) else None)
    ci=interval(boots,cfg["analysis"]["quantiles"]); supported=len(pop)>=cfg["intervention"]["minimum_components"]
    passes=bool(point is not None and point>cfg["analysis"]["raw_effect_point_threshold"] and ci["lower"] is not None and ci["lower"]>cfg["analysis"]["raw_effect_ci_threshold"])
    return {"status":("PASS" if passes else "FAIL") if supported else "INELIGIBLE_SUPPORT","pass":passes if supported else None,"decision_role":decision_role,
      "point_median":point,"interval":ci,"small_or_equal_count":int(np.sum(vals<=cfg["analysis"]["scientific_small_delta_threshold"])),"population_count":len(pop)}

def fit_projector(data:dict[str,Any],idx:np.ndarray,cfg:dict[str,Any])->tuple[np.ndarray|None,dict[str,Any]]:
    if len(idx)<cfg["intervention"]["minimum_components"]:
        return None,{"eligible":False,"reason":"population_support","rows":len(idx),"required":cfg["intervention"]["minimum_components"]}
    return projector(data["dcontext"][idx],cfg["analysis"]["rank"],cfg["analysis"]["rank_ratio_floor"])

def fit_lex_projector(data:dict[str,Any],idx:np.ndarray,cfg:dict[str,Any])->tuple[np.ndarray|None,dict[str,Any]]:
    if len(idx)<cfg["intervention"]["minimum_components"]:
        return None,{"eligible":False,"reason":"population_support","rows":len(idx),"required":cfg["intervention"]["minimum_components"]}
    return projector(data["dlexical"][idx],cfg["analysis"]["rank"],cfg["analysis"]["rank_ratio_floor"])

def direction(fit_name:str,test_name:str,all_data:dict[str,dict[str,Any]],cfg:dict[str,Any])->dict[str,Any]:
    fit,test=all_data[fit_name],all_data[test_name]; A=cfg["analysis"]; minimum=cfg["intervention"]["minimum_components"]
    fc,tc,fj,tj=fit["context_idx"],test["context_idx"],fit["joint_idx"],test["joint_idx"]
    context_support=len(fc)>=minimum and len(tc)>=minimum; joint_support=len(fj)>=minimum and len(tj)>=minimum
    pc,pcinfo=fit_projector(fit,fc,cfg) if context_support else (None,{"eligible":False,"reason":"population_support","fit_rows":len(fc),"test_rows":len(tc),"required":minimum})
    pjc,pjcinfo=fit_projector(fit,fj,cfg) if joint_support else (None,{"eligible":False,"reason":"population_support","fit_rows":len(fj),"test_rows":len(tj),"required":minimum})
    pjl,pjlinfo=fit_lex_projector(fit,fj,cfg) if joint_support else (None,{"eligible":False,"reason":"population_support","fit_rows":len(fj),"test_rows":len(tj),"required":minimum})
    points:dict[str,float|None]={"gate1_capture":None,"gate1_minus_haar":None,"gate2_context_assignment":None,"gate3_lexical_assignment":None,"gate4_unrelated_energy_margin":None,"gate5_lexical_complement":None}
    if pc is not None:
        points["gate1_capture"]=safe_mean(capture_rows(test["dcontext"][tc],pc,A["representation_norm_floor"])); points["gate1_minus_haar"]=points["gate1_capture"]-A["haar_reference"] if points["gate1_capture"] is not None else None
        points["gate4_unrelated_energy_margin"]=safe_mean(gate4_energy_rows(test["dtrue"][tc],test["dunrelated"][tc],pc,A["representation_norm_floor"]))
    if pjc is not None and pjl is not None:
        points["gate2_context_assignment"]=safe_mean(capture_rows(test["dcontext"][tj],pjc)-capture_rows(test["dcontext"][tj],pjl))
        points["gate3_lexical_assignment"]=safe_mean(capture_rows(test["dlexical"][tj],pjl)-capture_rows(test["dlexical"][tj],pjc))
        points["gate5_lexical_complement"]=safe_mean(complement_rows(test["dlexical"][tj],pjc,A["representation_norm_floor"]))
    direction_name=f"{fit_name}_to_{test_name}"; boots={k:[] for k in points}
    # Each endpoint has its own prospectively materialized fit/test map namespace.
    for endpoint in ["gate1","gate4","gate2","gate3","gate5"]:
        popfit,poptest=(fc,tc) if endpoint in {"gate1","gate4"} else (fj,tj)
        if len(popfit)<minimum or len(poptest)<minimum: continue
        fkey=f"{direction_name}__{endpoint}__fit"; tkey=f"{direction_name}__{endpoint}__test"
        for d in range(A["bootstrap_draws"]):
            fi=resample(fit,popfit,d,fkey); ti=resample(test,poptest,d,tkey)
            bc,_=fit_projector(fit,fi,cfg)
            if endpoint=="gate1" and bc is not None:
                v=safe_mean(capture_rows(test["dcontext"][ti],bc,A["representation_norm_floor"])); boots["gate1_capture"].append(v); boots["gate1_minus_haar"].append(v-A["haar_reference"] if v is not None else None)
            elif endpoint=="gate4" and bc is not None:
                boots["gate4_unrelated_energy_margin"].append(safe_mean(gate4_energy_rows(test["dtrue"][ti],test["dunrelated"][ti],bc,A["representation_norm_floor"])))
            else:
                bl,_=fit_lex_projector(fit,fi,cfg)
                if bc is None or bl is None: continue
                if endpoint=="gate2": boots["gate2_context_assignment"].append(safe_mean(capture_rows(test["dcontext"][ti],bc)-capture_rows(test["dcontext"][ti],bl)))
                elif endpoint=="gate3": boots["gate3_lexical_assignment"].append(safe_mean(capture_rows(test["dlexical"][ti],bl)-capture_rows(test["dlexical"][ti],bc)))
                elif endpoint=="gate5": boots["gate5_lexical_complement"].append(safe_mean(complement_rows(test["dlexical"][ti],bc,A["representation_norm_floor"])))
    cis={k:interval(v,A["quantiles"]) for k,v in boots.items()}; mf=A["minimum_finite_draws"]
    def context_reasons(metric:str)->list[str]:
        if not context_support: return ["context_population_support"]
        if pc is None: return ["context_projector_"+str(pcinfo.get("reason","rank"))]
        if cis[metric]["finite_draws"]<mf: return [metric+"_draws"]
        return []
    def joint_reasons(metric:str)->list[str]:
        if not joint_support: return ["joint_population_support"]
        if pjc is None: return ["joint_context_projector_"+str(pjcinfo.get("reason","rank"))]
        if pjl is None: return ["joint_lexical_projector_"+str(pjlinfo.get("reason","rank"))]
        if cis[metric]["finite_draws"]<mf: return [metric+"_draws"]
        return []
    r1=context_reasons("gate1_minus_haar"); r4=context_reasons("gate4_unrelated_energy_margin")
    r2=joint_reasons("gate2_context_assignment"); r3=joint_reasons("gate3_lexical_assignment"); r5=joint_reasons("gate5_lexical_complement")
    specs={
      "gate1":(not r1, points["gate1_capture"] is not None and points["gate1_capture"]>=A["context_capture_minimum"] and cis["gate1_minus_haar"]["lower"] is not None and cis["gate1_minus_haar"]["lower"]>0,r1),
      "gate2":(not r2, points["gate2_context_assignment"] is not None and points["gate2_context_assignment"]>=A["assignment_margin"] and cis["gate2_context_assignment"]["lower"] is not None and cis["gate2_context_assignment"]["lower"]>0,r2),
      "gate3":(not r3, points["gate3_lexical_assignment"] is not None and points["gate3_lexical_assignment"]>=A["assignment_margin"] and cis["gate3_lexical_assignment"]["lower"] is not None and cis["gate3_lexical_assignment"]["lower"]>0,r3),
      "gate4":(not r4, points["gate4_unrelated_energy_margin"] is not None and points["gate4_unrelated_energy_margin"]>=A["unrelated_energy_margin"] and cis["gate4_unrelated_energy_margin"]["lower"] is not None and cis["gate4_unrelated_energy_margin"]["lower"]>0,r4),
      "gate5":(not r5, points["gate5_lexical_complement"] is not None and points["gate5_lexical_complement"]>=A["lexical_complement_minimum"] and cis["gate5_lexical_complement"]["lower"] is not None and cis["gate5_lexical_complement"]["lower"]>=A["lexical_complement_minimum"],r5)}
    gates={k:gate_state(*v) for k,v in specs.items()}
    return {"fit_source":fit_name,"test_source":test_name,"populations":{"fit_context":len(fc),"test_context":len(tc),"fit_joint":len(fj),"test_joint":len(tj)},
      "projector_eligibility":{"context":pcinfo,"joint_context":pjcinfo,"joint_lexical":pjlinfo},"points":points,"intervals":cis,"gates":gates}

def source_summary(source:str,d:dict[str,Any],cfg:dict[str,Any])->dict[str,Any]:
    A=cfg["analysis"]; n=len(d["rows"]); union=int(np.sum(d["context_failure"])); nonfinite=int(np.sum(~d["context_finite"])); masked=int(np.sum(d["masked_failure"])); lex_union=int(np.sum(~np.logical_and.reduce(list(d["lex_parts"].values()))))
    pop=d["lexical_idx"]; vals=d["norms"]["dlexical"][pop]-d["norms"]["dlexical_control"][pop]; boots=[]; key=f"within_{source}__gate6__source"
    for draw in range(A["bootstrap_draws"]):
        idx=resample(d,pop,draw,key); boots.append(safe_mean(d["norms"]["dlexical"][idx]-d["norms"]["dlexical_control"][idx]))
    ci=interval(boots,A["quantiles"]); point=safe_mean(vals); supported=len(pop)>=cfg["intervention"]["minimum_components"]
    reasons=[]
    if not supported: reasons.append("lexical_population_support")
    elif ci["finite_draws"]<A["minimum_finite_draws"]: reasons.append("lexical_localization_draws")
    estimable=not reasons
    g6=gate_state(estimable,point is not None and ci["lower"] is not None and ci["lower"]>0,reasons)
    tm=d["masked"][np.isfinite(d["masked"])]; dm=d["downstream_masked"][np.isfinite(d["downstream_masked"])]
    return {"label_text_count":n,"context_count":len(d["context_idx"]),"lexical_count":len(d["lexical_idx"]),"joint_count":len(d["joint_idx"]),
      "removals":{"context_condition_nonfinite_union":nonfinite,"context_nonfinite_by_condition":{name:int(np.sum(~d["context_condition_finite"][:,i])) for i,name in enumerate(["true_masked","true_unmasked","unrelated_masked","unrelated_unmasked"])},
        "masked_equivalence_failure_among_finite":masked,"context_failure_union":union,"lexical_nonfinite_union":lex_union,
        "lexical_nonfinite_by_condition":{k:int(np.sum(~v)) for k,v in d["lex_parts"].items()}},
      "target_technical_failure_rate":union/n,"target_masked_max_finite":finite_float(np.max(tm)) if len(tm) else None,"downstream_masked_descriptive_max_finite":finite_float(np.max(dm)) if len(dm) else None,
      "raw_dtrue":raw_effect(d,source,"context_idx","dtrue","raw_dtrue",cfg),"raw_dcontext":raw_effect(d,source,"context_idx","dcontext","raw_dcontext",cfg),
      "raw_dlexical":raw_effect(d,source,"lexical_idx","dlexical","raw_dlexical",cfg),"raw_dunrelated_descriptive":raw_effect(d,source,"context_idx","dunrelated","raw_dunrelated",cfg,False),
      "gate6":{"point":point,"interval":ci,**g6}}

def numerical_rows(source:str,d:dict[str,Any],cfg:dict[str,Any])->list[dict[str,Any]]:
    small=cfg["analysis"]["scientific_small_delta_threshold"]; out=[]; cset=set(map(int,d["context_idx"])); lset=set(map(int,d["lexical_idx"])); jset=set(map(int,d["joint_idx"]))
    for i,row in enumerate(d["rows"]):
        vals={k:finite_float(v[i]) for k,v in d["norms"].items()}
        out.append({"source":source,"component_id":row["component_id"],"masked_target_normalized":finite_float(d["masked"][i]),"masked_downstream_descriptive_normalized":finite_float(d["downstream_masked"][i]),
          "norms":vals,"low_norm_flags":{k:(v is not None and v<=small) for k,v in vals.items()},"context_nonfinite":bool(not d["context_finite"][i]),"masked_equivalence_failure":bool(d["masked_failure"][i]),
          "lexical_nonfinite":bool(i not in lset),"in_context_population":i in cset,"in_lexical_population":i in lset,"in_joint_population":i in jset})
    return out

def fmt(x:Any)->str: return "NA" if x is None else f"{float(x):.6g}"
def main()->None:
    ap=argparse.ArgumentParser(); ap.add_argument("--config",required=True); ap.add_argument("--cache",required=True); ap.add_argument("--output",required=True)
    args=ap.parse_args(); cfg=read_json(ROOT/args.config); prepared=ROOT/cfg["paths"]["prepared_root"]; cache=ROOT/args.cache; out=ROOT/args.output; out.mkdir(parents=True,exist_ok=True)
    sources=list(cfg["sources"]); data={s:load_source(prepared,cache,s,cfg) for s in sources}; summaries={s:source_summary(s,data[s],cfg) for s in sources}
    qa=[row for s in sources for row in numerical_rows(s,data[s],cfg)]; qa_sha,qa_n=atomic_jsonl(out/"numerical_qa.jsonl",qa)
    directions=[direction(sources[0],sources[1],data,cfg),direction(sources[1],sources[0],data,cfg)]; A=cfg["analysis"]; minimum=cfg["intervention"]["minimum_components"]
    technical_ok=all(r["context_count"]>=minimum and r["target_technical_failure_rate"]<=A["technical_max_failure_rate"] for r in summaries.values())
    context_raw_ok=all(r["raw_dtrue"]["status"]=="PASS" and r["raw_dcontext"]["status"]=="PASS" for r in summaries.values())
    gate1_states=[d["gates"]["gate1"]["status"] for d in directions]; gate1_estimable=all(x!="INELIGIBLE" for x in gate1_states); gate1_ok=all(x=="PASS" for x in gate1_states)
    specificity_pop_ok=all(r["lexical_count"]>=minimum and r["joint_count"]>=minimum for r in summaries.values()); lexical_raw_ok=all(r["raw_dlexical"]["status"]=="PASS" for r in summaries.values())
    spec_states=[d["gates"][f"gate{i}"]["status"] for d in directions for i in [2,3,4,5]]+[r["gate6"]["status"] for r in summaries.values()]
    specificity_estimable=all(x!="INELIGIBLE" for x in spec_states); specificity_pass=all(x=="PASS" for x in spec_states)
    causes=[]
    for s,r in summaries.items():
        if r["context_count"]<minimum or r["target_technical_failure_rate"]>A["technical_max_failure_rate"]: causes.append({"endpoint":"context_technical","source":s,"reason":"support_or_failure_rate"})
        if r["lexical_count"]<minimum or r["joint_count"]<minimum: causes.append({"endpoint":"specificity_population","source":s,"reason":"support"})
        if r["gate6"]["status"]=="INELIGIBLE": causes.append({"endpoint":"gate6","source":s,"reason":r["gate6"]["reasons"]})
    for d in directions:
        for g,state in d["gates"].items():
            if state["status"]=="INELIGIBLE": causes.append({"endpoint":g,"direction":f"{d['fit_source']}_to_{d['test_source']}","reason":state["reasons"]})
    if not technical_ok: decision="CONTEXT_TECHNICALLY_INELIGIBLE_STOP_NO_TRAINING"
    elif not context_raw_ok: decision="CONTEXT_RAW_EFFECT_NOT_DEMONSTRATED_AT_THIS_LAYER"
    elif not gate1_estimable: decision="CONTEXT_ORGANIZATION_UNESTIMABLE_AT_FROZEN_RANK"
    elif not gate1_ok: decision="CONTEXT_NOT_REPRODUCIBLE_ACROSS_SOURCES_AT_THIS_LAYER"
    elif not specificity_pop_ok: decision="CONTEXT_REPRODUCIBLE_SPECIFICITY_TECHNICALLY_INELIGIBLE"
    elif not lexical_raw_ok: decision="CONTEXT_REPRODUCIBLE_LEXICAL_CONTROL_EFFECT_NOT_DEMONSTRATED"
    elif not specificity_estimable: decision="CONTEXT_REPRODUCIBLE_SPECIFICITY_ESTIMATOR_INELIGIBLE"
    elif not specificity_pass: decision="CONTEXT_DETECTABLE_BUT_NOT_CLEANLY_SEPARABLE_AT_THIS_LAYER"
    else: decision="NOMINATE_LATER_EQUAL_CAPACITY_SUPERVISED_COMPARISON"
    result={"schema_version":"atlas_context_local_v10_attempt14_result_v2","exploratory":True,"decision":decision,"training_authorized":False,
      "claim_scope":"Spanish AnCora 3LB/CESS; Pythia-160m-deduped layer 3; frozen rank-16 linear protocol","source_results":summaries,"directions":directions,
      "estimator_ineligibility_causes":causes,"numerical_qa":{"path":"numerical_qa.jsonl","sha256":qa_sha,"rows":qa_n},"config_sha256":sha256_file(ROOT/args.config),"cache_files":{p.name:sha256_file(p) for p in sorted(cache.glob("*.npz"))}}
    atomic_json(out/"result.json",result)
    lines=["# Attempt 14 final context/local falsification","",f"**Decision:** `{decision}`","","Exploratory scope: Spanish AnCora 3LB/CESS, Pythia-160m-deduped layer 3, frozen rank-16 linear protocol.","","No neural or representation training was run or authorized.",""]
    for s,r in summaries.items(): lines += [f"## {s}",f"- components: {r['label_text_count']} (context {r['context_count']}, lexical {r['lexical_count']}, joint {r['joint_count']})",f"- context technical union failures: {r['removals']['context_failure_union']} (rate {r['target_technical_failure_rate']:.6g})",f"- raw median d_true/context/lexical/unrelated: {fmt(r['raw_dtrue']['point_median'])} / {fmt(r['raw_dcontext']['point_median'])} / {fmt(r['raw_dlexical']['point_median'])} / {fmt(r['raw_dunrelated_descriptive']['point_median'])}",f"- lexical localization: {fmt(r['gate6']['point'])}, status {r['gate6']['status']}",""]
    for d in directions: lines += [f"## {d['fit_source']} → {d['test_source']}",f"- points: `{json.dumps(d['points'],sort_keys=True,allow_nan=False)}`",f"- gates: `{json.dumps(d['gates'],sort_keys=True,allow_nan=False)}`",""]
    (out/"report.md").write_text("\n".join(lines)+"\n"); print(json.dumps(result,indent=2,allow_nan=False))
if __name__=="__main__": main()
