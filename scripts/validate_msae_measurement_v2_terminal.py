#!/usr/bin/env python3
"""Independent semantic and inventory validator for v2 terminal publication."""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import re
import sys
from typing import Any, Mapping
import numpy as np
from collections import Counter


ROLES=("discovery","calibration","C1","C2")
JOBS=("g4","g5","g6","g7")


def _read(path: Path) -> Any:return json.loads(path.read_text(encoding="utf-8"))
def _sha(path: Path) -> str:return hashlib.sha256(path.read_bytes()).hexdigest()
def _command_sha(command: list[str]) -> str:return hashlib.sha256(b"\0".join(os.fsencode(x) for x in command)).hexdigest()
def _finite(value:Any)->bool:
    try:return value is not None and __import__("math").isfinite(float(value))
    except (TypeError,ValueError):return False
def _same(left:Any,right:Any,tolerance:float=1e-10)->bool:
    if left is None or right is None:return left is right
    return _finite(left) and _finite(right) and abs(float(left)-float(right))<=tolerance
def _interval(values:list[Any])->dict[str,Any]:
    finite=np.asarray([float(x) for x in values if _finite(x)],np.float64)
    if len(finite)==0:return {"finite":0,"lower":None,"upper":None,"mean":None}
    return {"finite":len(finite),"lower":float(np.quantile(finite,0.025,method="linear")),
        "upper":float(np.quantile(finite,0.975,method="linear")),"mean":float(finite.mean())}
def _assert_interval(observed:Mapping[str,Any],values:list[Any],label:str)->dict[str,Any]:
    expected=_interval(values)
    if set(observed)!={"finite","lower","upper","mean"} or int(observed["finite"])!=expected["finite"] or any(not _same(observed[key],expected[key]) for key in ("lower","upper","mean")):
        raise RuntimeError(f"interval/draw contradiction: {label}")
    return expected
def _cosine(left:np.ndarray,right:np.ndarray)->float|None:
    a=np.asarray(left,np.float64);b=np.asarray(right,np.float64);denom=float(np.linalg.norm(a)*np.linalg.norm(b))
    if not np.isfinite(a).all() or not np.isfinite(b).all() or denom<=0:return None
    return float(1.0-np.dot(a,b)/denom)
def _specificity_responses(cfg:Mapping[str,Any],run_root:Path,job:str)->dict[str,dict[str,list[dict[str,Any]]]]:
    prepared=Path(cfg["data_root"])/"prepared/C2";pairs=[json.loads(x) for x in (prepared/"pairs.jsonl").read_text().splitlines() if x]
    rows=[json.loads(x) for x in (prepared/"activation_rows.jsonl").read_text().splitlines() if x];index={row["row_id"]:int(row["activation_index"]) for row in rows}
    raw=np.load(run_root/"raw_cache/C2/values.float32.npy",mmap_mode="r");output={}
    for branch in ("pos","content"):
        array=np.load(run_root/f"transforms/{job}/C2/{branch}/values.float32.npy",mmap_mode="r");output[branch]={}
        for construct in ("document_context_anchor","entity_substitution"):
            values=[]
            for pair in [x for x in pairs if x["construct"]==construct]:
                source=[index[x] for x in pair["source_row_ids"]];target=[index[x] for x in pair["target_row_ids"]]
                a=np.asarray(array[source],np.float32).mean(0,dtype=np.float32);b=np.asarray(array[target],np.float32).mean(0,dtype=np.float32)
                ra=np.asarray(raw[source],np.float32).mean(0,dtype=np.float32);rb=np.asarray(raw[target],np.float32).mean(0,dtype=np.float32)
                distance=_cosine(a,b);raw_distance=_cosine(ra,rb)
                ratio=None if distance is None or raw_distance is None or raw_distance<=float(cfg["specificity"]["raw_distance_floor"]) else distance/raw_distance
                values.append({"pair_id":pair["pair_id"],"group":pair["component_group"],"construct":construct,"distance":distance,"raw_distance":raw_distance,"ratio":ratio})
            output[branch][construct]=values
    return output
def _assert_responses(observed:list[Mapping[str,Any]],expected:list[Mapping[str,Any]],label:str)->None:
    if len(observed)!=len(expected):raise RuntimeError(f"specificity response count drift: {label}")
    for left,right in zip(observed,expected,strict=True):
        if any(left.get(key)!=right.get(key) for key in ("pair_id","group","construct")) or any(not _same(left.get(key),right.get(key),1e-8) for key in ("distance","raw_distance","ratio")):
            raise RuntimeError(f"specificity cache-response drift: {label}")
def _multiplicities(groups:list[str],role:str,task:str,source:str,draw:int,seed:int)->dict[str,int]:
    unique=sorted(set(groups),key=lambda x:x.encode());counts=Counter()
    for slot in range(len(unique)):
        payload=f"atlas_measurement_v2|{seed}|{role}|{task}|{source}|{draw}|{slot}".encode()
        counts[unique[int.from_bytes(hashlib.sha256(payload).digest()[:8],"big")%len(unique)]]+=1
    return dict(counts)
def _weighted(rows:list[Mapping[str,Any]],mult:Mapping[str,int])->float|None:
    finite=[row for row in rows if _finite(row.get("ratio"))];weights=np.asarray([mult.get(str(row["group"]),0) for row in finite],np.float64)
    if not finite or weights.sum()<=0:return None
    return float(np.average([float(row["ratio"]) for row in finite],weights=weights))


def validate_analysis_truth(cfg: Mapping[str,Any],config_path:Path,run_root:Path) -> dict[str,Any]:
    config_sha=_sha(config_path);analysis_dir=run_root/"analysis"
    complete=_read(analysis_dir/"COMPLETE.json");results=_read(analysis_dir/"results.json")
    if complete.get("schema_version")!="atlas_measurement_v2_analysis_complete_v1" or results.get("schema_version")!="atlas_measurement_v2_analysis_v1":
        raise RuntimeError("analysis schema drift")
    if complete.get("config_sha256")!=config_sha or results.get("config_sha256")!=config_sha:
        raise RuntimeError("analysis config drift")
    if complete.get("results_sha256")!=_sha(analysis_dir/"results.json") or complete.get("probe_models_sha256")!=_sha(analysis_dir/"probe_models.npz"):
        raise RuntimeError("analysis artifact hash drift")
    candidates=[row["id"] for row in cfg["checkpoints"] if row["role"]=="candidate"]
    tasks=tuple(cfg["tasks"]["primary"])
    minimum_finite=int(cfg["bootstrap"]["minimum_finite"]);task_complete=True
    for job in candidates+["g7"]:
        localization=results["localization"][job]
        derived_task_pass={}
        for task in tasks:
            row=localization["tasks"][task]
            evaluations=results.get("evaluations");
            if not isinstance(evaluations,dict) or "raw" not in evaluations:raise RuntimeError("underlying probe evaluations absent")
            assigned_name=f"{job}_{'content' if task=='token_identity_v2' else 'pos'}";leak_name=f"{job}_{'pos' if task=='token_identity_v2' else 'content'}"
            raw=evaluations["raw"][task];assigned=evaluations[assigned_name][task];leak=evaluations[leak_name][task]
            if raw["labels"]!=assigned["labels"] or raw["labels"]!=leak["labels"] or len(raw["labels"])<2:raise RuntimeError(f"probe label contract drift: {job}/{task}")
            chance=1.0/len(raw["labels"])
            if not _same(row.get("chance_convention"),chance):raise RuntimeError(f"chance convention drift: {job}/{task}")
            for rep_name,rep in (("raw",raw),("assigned",assigned),("leak",leak)):
                for role in ("C1","C2"):
                    metric=rep["roles"][role];draws=metric["draws"]
                    if len(draws)!=int(cfg["bootstrap"]["draws"]) or any(not _finite(x) or not 0<=float(x)<=1 for x in draws) or not _finite(metric["macro_f1"]) or not 0<=float(metric["macro_f1"])<=1:
                        raise RuntimeError(f"probe metric range/count drift: {job}/{task}/{rep_name}/{role}")
                    _assert_interval(metric["bootstrap"],draws,f"probe:{job}/{task}/{rep_name}/{role}")
            raw_c1=raw["roles"]["C1"];c1_signal=float(raw_c1["macro_f1"])-chance;c1_draws=[float(x)-chance for x in raw_c1["draws"]]
            c1_interval=_interval(c1_draws)
            if not _same(row.get("c1_raw_signal"),c1_signal):raise RuntimeError(f"C1 raw-signal contradiction: {job}/{task}")
            _assert_interval(row["c1_raw_signal_interval"],c1_draws,f"C1 raw signal:{job}/{task}")
            c1_measurable=(c1_signal>=float(cfg["tasks"]["raw_signal_minimum"])
                and _finite(c1_interval.get("lower")) and float(c1_interval["lower"])>0)
            raw_c2=raw["roles"]["C2"];assigned_c2=assigned["roles"]["C2"];leak_c2=leak["roles"]["C2"]
            denom=float(raw_c2["macro_f1"])-chance;floor=float(cfg["probe"]["raw_denominator_floor"])
            assigned_point=None if denom<=floor else (float(assigned_c2["macro_f1"])-chance)/denom
            leak_point=None if denom<=floor else (float(leak_c2["macro_f1"])-chance)/denom
            a_draws=[];l_draws=[];s_draws=[]
            for raw_draw,assigned_draw,leak_draw in zip(raw_c2["draws"],assigned_c2["draws"],leak_c2["draws"],strict=True):
                draw_denom=float(raw_draw)-chance
                if draw_denom<=floor:a_draws.append(None);l_draws.append(None);s_draws.append(None)
                else:
                    ar=(float(assigned_draw)-chance)/draw_denom;lr=(float(leak_draw)-chance)/draw_denom
                    a_draws.append(ar);l_draws.append(lr);s_draws.append(ar-lr)
            if not _same(row["assigned_recovery"].get("point"),assigned_point) or not _same(row["leakage"].get("point"),leak_point) or not _same(row["selectivity"].get("point"),None if assigned_point is None or leak_point is None else assigned_point-leak_point):raise RuntimeError(f"recovery point contradiction: {job}/{task}")
            for name,draws in (("assigned_recovery",a_draws),("leakage",l_draws),("selectivity",s_draws)):_assert_interval(row[name]["interval"],draws,f"recovery:{job}/{task}/{name}")
            intervals=[row[name]["interval"] for name in ("assigned_recovery","leakage","selectivity")]
            if any(not 0<=int(value.get("finite",-1))<=int(cfg["bootstrap"]["draws"]) for value in intervals):raise RuntimeError(f"task finite-count drift: {job}/{task}")
            c2_complete=all(int(value.get("finite",-1))>=minimum_finite for value in intervals)
            localization_pass=(c2_complete and _finite(intervals[0].get("lower"))
                and float(intervals[0]["lower"])>=float(cfg["tasks"]["assigned_recovery_lcb"])
                and _finite(intervals[2].get("lower")) and float(intervals[2]["lower"])>float(cfg["tasks"]["selectivity_lcb"]))
            if row.get("c1_raw_measurable")!=c1_measurable or row.get("c2_finite_complete")!=c2_complete or row.get("measurement_eligible")!=(c1_measurable and c2_complete) or row.get("localization_pass")!=localization_pass:
                raise RuntimeError(f"task endpoint contradiction: {job}/{task}")
            derived_task_pass[task]=localization_pass
            if job in candidates:task_complete &= c1_measurable and c2_complete
        broad=all(derived_task_pass[x] for x in ("relative_quartile","head_signed_distance"));lexical=derived_task_pass["token_identity_v2"]
        if localization["families"]["broad_structural_context_position"].get("probe_pass")!=broad or localization["families"]["lexical_content"].get("probe_pass")!=lexical:
            raise RuntimeError(f"family probe contradiction: {job}")
    counterfactual_complete=True
    for job in candidates+["g7"]:
        recomputed_responses=_specificity_responses(cfg,run_root,job);stored_responses=results["specificity"][job].get("responses")
        if not isinstance(stored_responses,dict):raise RuntimeError(f"specificity responses absent: {job}")
        for branch in ("pos","content"):
            for construct in ("document_context_anchor","entity_substitution"):_assert_responses(stored_responses[branch][construct],recomputed_responses[branch][construct],f"{job}/{branch}/{construct}")
        for construct in ("document_context_anchor","entity_substitution"):
            row=results["specificity"][job]["constructs"][construct];branch=row["branch_margin"];control=row["control_margin"]
            assigned="pos" if construct=="document_context_anchor" else "content";other="content" if assigned=="pos" else "pos"
            control_construct="entity_substitution" if construct=="document_context_anchor" else "document_context_anchor"
            own=recomputed_responses[assigned][construct];leak=recomputed_responses[other][construct];control_rows=recomputed_responses[assigned][control_construct]
            own_map={value["pair_id"]:value for value in own};leak_map={value["pair_id"]:value for value in leak}
            finite_ids=[key for key in own_map if _finite(own_map[key]["ratio"]) and _finite(leak_map[key]["ratio"])]
            paired_own=[own_map[key] for key in finite_ids];paired_leak=[leak_map[key] for key in finite_ids]
            assigned_finite=[value for value in own if _finite(value["ratio"])];control_finite=[value for value in control_rows if _finite(value["ratio"])]
            expected_counts=(len(own),len(finite_ids),len(control_rows),len(control_finite))
            observed_counts=(int(row["pairs"]),int(row["finite_pairs"]),int(row["control_pairs"]),int(row["finite_control_pairs"]))
            if observed_counts!=expected_counts:raise RuntimeError(f"specificity count contradiction: {job}/{construct}")
            expected_fraction=len(finite_ids)/max(1,len(own));expected_control_fraction=len(control_finite)/max(1,len(control_rows))
            if not _same(row["finite_fraction"],expected_fraction) or not _same(row["finite_control_fraction"],expected_control_fraction):raise RuntimeError(f"specificity fraction contradiction: {job}/{construct}")
            point_assigned=float(np.mean([value["ratio"] for value in assigned_finite])) if assigned_finite else None
            point_paired=float(np.mean([own_map[key]["ratio"] for key in finite_ids])) if finite_ids else None
            point_leak=float(np.mean([leak_map[key]["ratio"] for key in finite_ids])) if finite_ids else None
            point_control=float(np.mean([value["ratio"] for value in control_finite])) if control_finite else None
            if not _same(row.get("assigned_response"),point_assigned) or not _same(row.get("paired_assigned_response"),point_paired) or not _same(row.get("leakage_response"),point_leak) or not _same(row.get("cross_family_control_response"),point_control):raise RuntimeError(f"specificity point contradiction: {job}/{construct}")
            branch_draws=[];control_draws=[];source=str(cfg["replacement_source"]["id"])
            for draw in range(int(cfg["bootstrap"]["draws"])):
                own_mult=_multiplicities([str(value["group"]) for value in own],"C2",construct,source,draw,int(cfg["seed"]))
                control_mult=_multiplicities([str(value["group"]) for value in control_rows],"C2",control_construct,source,draw,int(cfg["seed"]))
                ap=_weighted(paired_own,own_mult);lm=_weighted(paired_leak,own_mult);ac=_weighted(own,own_mult);cm=_weighted(control_rows,control_mult)
                branch_draws.append(None if ap is None or lm is None else ap-lm);control_draws.append(None if ac is None or cm is None else ac-cm)
            if branch.get("draws")!=branch_draws or control.get("draws")!=control_draws:raise RuntimeError(f"specificity bootstrap draw contradiction: {job}/{construct}")
            _assert_interval(branch["interval"],branch_draws,f"specificity branch:{job}/{construct}")
            _assert_interval(control["interval"],control_draws,f"specificity control:{job}/{construct}")
            eligible=(int(row["finite_pairs"])>=int(cfg["specificity"]["minimum_finite_pairs"])
                and float(row["finite_fraction"])>=float(cfg["specificity"]["minimum_finite_fraction"])
                and int(row["finite_control_pairs"])>=int(cfg["specificity"]["minimum_finite_pairs"])
                and float(row["finite_control_fraction"])>=float(cfg["specificity"]["minimum_finite_fraction"])
                and int(branch["interval"].get("finite",-1))>=minimum_finite
                and int(control["interval"].get("finite",-1))>=minimum_finite
                and row["cached_noop"].get("status")=="eligible" and row["cached_noop"].get("bit_identical") is True
                and row["cached_noop"].get("distance")==0.0 and int(row["cached_noop"].get("checked",-1))==len(own))
            passed=(eligible and _finite(branch["interval"].get("lower"))
                and float(branch["interval"]["lower"])>=float(cfg["specificity"]["branch_margin_lcb"])
                and _finite(control["interval"].get("lower"))
                and float(control["interval"]["lower"])>float(cfg["specificity"]["control_margin_lcb"]))
            expected_branch=None if point_paired is None or point_leak is None else point_paired-point_leak
            expected_control=None if point_assigned is None or point_control is None else point_assigned-point_control
            if row.get("eligible")!=eligible or row.get("passed")!=passed or not _same(branch.get("point"),expected_branch) or not _same(control.get("point"),expected_control):
                raise RuntimeError(f"specificity endpoint contradiction: {job}/{construct}")
            family="broad_structural_context_position" if construct=="document_context_anchor" else "lexical_content"
            if results["localization"][job]["families"][family].get("counterfactual_pass")!=passed:raise RuntimeError(f"family counterfactual contradiction: {job}/{construct}")
            if job in candidates:counterfactual_complete &= eligible
        expected_selective=all(value["probe_pass"] and value["counterfactual_pass"] for value in results["localization"][job]["families"].values())
        if results["localization"][job].get("selective_k2_posfam_passed")!=expected_selective:raise RuntimeError(f"candidate selectivity contradiction: {job}")
    numerical=bool(results["numerical_qa"] and results["numerical_qa"]["heldout_passed"])
    candidate_pairs={"g4__g5","g4__g6","g5__g6"};geometry=True;geometry_pass=True
    if not candidate_pairs<=set(results["stability"]["pairs"]):raise RuntimeError("candidate CKA pair missing")
    for pair in candidate_pairs:
        pair_tasks=results["stability"]["pairs"][pair]["tasks"]
        if set(pair_tasks)!=set(tasks):raise RuntimeError(f"CKA task inventory drift: {pair}")
        for task,row in pair_tasks.items():
            matrix=row["matrix"]
            if set(matrix)!={"pos__pos","content__content","pos__content","content__pos"}:raise RuntimeError(f"CKA cell inventory drift: {pair}/{task}")
            finite=all(_finite(value) for value in matrix.values());geometry &= finite
            if finite and any(float(value)<-1e-6 or float(value)>1.000001 for value in matrix.values()):raise RuntimeError(f"CKA value out of range: {pair}/{task}")
            margin=None if not finite else (float(matrix["pos__pos"])+float(matrix["content__content"])-float(matrix["pos__content"])-float(matrix["content__pos"]))/2
            if not _same(row.get("identity_margin"),margin):raise RuntimeError(f"CKA identity-margin contradiction: {pair}/{task}")
            geometry_pass &= finite and float(matrix["pos__pos"])>=float(cfg["stability"]["same_branch_minimum"])
            geometry_pass &= finite and float(matrix["content__content"])>=float(cfg["stability"]["same_branch_minimum"])
            geometry_pass &= margin is not None and margin>float(cfg["stability"]["identity_margin_minimum"])
    if results["stability"].get("candidate_geometry_complete")!=geometry or results["stability"].get("candidate_geometry_passed")!=bool(geometry_pass):raise RuntimeError("geometry summary contradiction")
    eligible=numerical and geometry and task_complete and counterfactual_complete
    expected_eligibility="eligible" if eligible else "ineligible"
    selective=all(results["localization"][job]["selective_k2_posfam_passed"] for job in candidates)
    if not eligible:expected_outcome="equivocal"
    elif selective and results["stability"]["candidate_geometry_passed"]:expected_outcome="K2_broad_position_content_selective_supported"
    else:expected_outcome="K2_broad_position_content_selective_not_supported"
    if results.get("overall_decision_eligibility")!=expected_eligibility or results.get("architecture_outcome")!=expected_outcome:
        raise RuntimeError("analysis truth-table mismatch")
    if complete.get("architecture_outcome")!=expected_outcome:
        raise RuntimeError("analysis completion outcome mismatch")
    endpoints=results.get("endpoint_eligibility",{})
    expected_endpoints={"numerical_qa":"eligible" if numerical else "ineligible",
        "counterfactual_validity":"eligible" if counterfactual_complete else "ineligible",
        "geometry_completeness":"eligible" if geometry else "ineligible",
        "signed_grouping_provenance":"eligible","cache_lineage":"eligible"}
    if endpoints!=expected_endpoints:raise RuntimeError("endpoint eligibility record mismatch")
    return {"eligible":eligible,"outcome":expected_outcome,"results_sha256":_sha(analysis_dir/"results.json")}


def _expected_commands(config_arg:str) -> dict[str,list[str]]:
    py=".venv-atlas/bin/python";stage="scripts/run_msae_measurement_v2.py"
    result={f"extract_{role}":[py,stage,"--config",config_arg,"--stage","extract","--role",role,"--device","cuda:0","--batch-size","24"] for role in ROLES}
    result.update({f"transform_{job}":[py,stage,"--config",config_arg,"--stage","transform","--job",job,"--device","cuda:0","--batch-size","512"] for job in JOBS})
    result["analyze"]=[py,stage,"--config",config_arg,"--stage","analyze","--device","cuda:0","--batch-size","512"]
    return result


def _validate_producer(run_root:Path,config_sha:str,producer:Mapping[str,Any],expected_short:str) -> None:
    job=producer.get("producer_job");digest=producer.get("producer_command_sha256")
    if not isinstance(job,str) or re.fullmatch(rf"attempt[1-9][0-9]*_{re.escape(expected_short)}",job) is None:raise RuntimeError(f"artifact producer job drift: {expected_short}")
    started=_read(run_root/"jobs"/f"{job}.started.json");terminal=_read(run_root/"jobs"/f"{job}.terminal.json");lease=_read(run_root/"leases"/f"{job}.json")
    if started!=lease or started.get("command_sha256")!=digest or terminal.get("command_sha256")!=digest or terminal.get("exit_code")!=0 or started.get("config_sha256")!=config_sha or terminal.get("config_sha256")!=config_sha:
        raise RuntimeError(f"artifact producer record mismatch: {job}")


def validate_current_job_inventory(cfg:Mapping[str,Any],config_path:Path,run_root:Path) -> dict[str,Any]:
    config_sha=_sha(config_path);owner=_read(run_root/"owner.json");attempt=int(owner["attempt"])
    if owner.get("config_sha256")!=config_sha:raise RuntimeError("owner config drift")
    expected=_expected_commands(str(config_path.relative_to(Path.cwd())))
    required={f"attempt{attempt}_{name}" for name in expected}
    started_paths={p.name.removesuffix(".started.json"):p for p in (run_root/"jobs").glob(f"attempt{attempt}_*.started.json")}
    terminal_paths={p.name.removesuffix(".terminal.json"):p for p in (run_root/"jobs").glob(f"attempt{attempt}_*.terminal.json")}
    if set(started_paths)!=required or set(terminal_paths)!=required:raise RuntimeError("current attempt job inventory mismatch")
    lease_keys={"schema_version","job","host","gpu_uuid","gpu_index","lock_path","fd","wrapper_pid","wrapper_start_ticks",
        "child_pid","child_start_ticks","command","command_sha256","config_sha256","started_unix"}
    terminal_keys={"schema_version","job","exit_code","wrapper_pid","wrapper_start_ticks","child_pid","command_sha256","config_sha256","ended_unix"}
    gpu_for={f"extract_{role}":cfg["gpu_uuids"][i] for i,role in enumerate(ROLES)}
    gpu_for.update({f"transform_{job}":cfg["gpu_uuids"][i] for i,job in enumerate(JOBS)});gpu_for["analyze"]=cfg["gpu_uuids"][0]
    for full_name in sorted(required):
        short=full_name.removeprefix(f"attempt{attempt}_");started=_read(started_paths[full_name]);terminal=_read(terminal_paths[full_name])
        lease=_read(run_root/"leases"/f"{full_name}.json");command=expected[short];digest=_command_sha(command)
        if started.get("schema_version")!="atlas_measurement_v2_gpu_lease_v1" or terminal.get("schema_version")!="atlas_measurement_v2_job_terminal_v1":raise RuntimeError(f"job schema drift: {full_name}")
        if set(started)!=lease_keys or set(terminal)!=terminal_keys:raise RuntimeError(f"job field schema drift: {full_name}")
        if started!=lease:raise RuntimeError(f"lease/start record mismatch: {full_name}")
        if started.get("job")!=full_name or terminal.get("job")!=full_name or started.get("gpu_uuid")!=gpu_for[short] or started.get("fd")!=200:raise RuntimeError(f"job identity/GPU drift: {full_name}")
        for key in ("wrapper_pid","wrapper_start_ticks","child_pid"):
            if terminal.get(key)!=started.get(key):raise RuntimeError(f"job PID lineage drift: {full_name}/{key}")
        if started.get("command")!=command or started.get("command_sha256")!=digest or terminal.get("command_sha256")!=digest:raise RuntimeError(f"job command drift: {full_name}")
        if started.get("config_sha256")!=config_sha or terminal.get("config_sha256")!=config_sha or terminal.get("exit_code")!=0:raise RuntimeError(f"job terminal failure/drift: {full_name}")
    unknown=[]
    for path in (run_root/"jobs").glob("*.json"):
        if re.fullmatch(r"attempt[1-9][0-9]*_(extract_(discovery|calibration|C1|C2)|transform_g[4-7]|analyze)\.(started|terminal)\.json",path.name) is None:unknown.append(path.name)
    if unknown:raise RuntimeError(f"unknown job IDs: {sorted(unknown)}")
    lease_names={p.name.removesuffix(".json") for p in (run_root/"leases").glob("*.json")}
    all_started={p.name.removesuffix(".started.json") for p in (run_root/"jobs").glob("*.started.json")}
    if lease_names!=all_started:raise RuntimeError("exact lease/start inventory mismatch")
    return {"attempt":attempt,"jobs":sorted(required)}


def validate_for_aggregation(cfg:Mapping[str,Any],config_path:Path,run_root:Path) -> dict[str,Any]:
    if any((run_root/name).exists() for name in ("FAILED.json","ABANDONED.json")):raise RuntimeError("non-complete terminal marker exists")
    prepared=_read(Path(cfg["data_root"])/"prepared/manifest.json")
    if prepared.get("config_sha256")!=_sha(config_path):raise RuntimeError("prepared config drift")
    for role in ROLES:
        for task in tuple(cfg["tasks"]["primary"])+tuple(cfg["tasks"]["diagnostic"]):
            if prepared["roles"][role]["support"][task]["status"]!="eligible":raise RuntimeError(f"prepared support ineligible: {role}/{task}")
    raw_root=run_root/"raw_cache";transform_root=run_root/"transforms"
    if not raw_root.is_dir() or {p.name for p in raw_root.iterdir()}!=set(ROLES):raise RuntimeError("exact raw-cache inventory mismatch")
    if not transform_root.is_dir() or {p.name for p in transform_root.iterdir()}!=set(JOBS):raise RuntimeError("exact transform inventory mismatch")
    config_sha=_sha(config_path)
    for role in ROLES:
        manifest=_read(raw_root/role/"manifest.json");_validate_producer(run_root,config_sha,manifest["lineage"],f"extract_{role}")
    for job in JOBS:
        complete=_read(transform_root/job/"COMPLETE.json");_validate_producer(run_root,config_sha,complete,f"transform_{job}")
        for role in ROLES:
            for branch in ("pos","content"):
                manifest=_read(transform_root/job/role/branch/"manifest.json")
                if manifest["lineage"].get("producer_job")!=complete.get("producer_job") or manifest["lineage"].get("producer_command_sha256")!=complete.get("producer_command_sha256"):raise RuntimeError(f"transform producer lineage drift: {job}/{role}/{branch}")
    analysis_complete=_read(run_root/"analysis/COMPLETE.json");analysis_results=_read(run_root/"analysis/results.json")
    _validate_producer(run_root,config_sha,analysis_complete,"analyze")
    if analysis_results.get("producer_job")!=analysis_complete.get("producer_job") or analysis_results.get("producer_command_sha256")!=analysis_complete.get("producer_command_sha256"):raise RuntimeError("analysis producer lineage drift")
    return {"analysis":validate_analysis_truth(cfg,config_path,run_root),
            "job_inventory":validate_current_job_inventory(cfg,config_path,run_root)}


def validate_final_report(report:Mapping[str,Any],terminal_validation:Mapping[str,Any],cfg:Mapping[str,Any]) -> None:
    if report.get("schema_version")!="atlas_measurement_v2_report_v1" or report.get("claim_scope")!=cfg["claim_scope"]:raise RuntimeError("report schema/scope drift")
    analysis=report.get("analysis",{})
    if analysis.get("architecture_outcome")!=terminal_validation["analysis"]["outcome"]:raise RuntimeError("report outcome drift")
    if report.get("claim_review_status")!="not_run_required_before_claim":raise RuntimeError("claim-review status drift")


def validate_recovery_state(cfg:Mapping[str,Any],config_path:Path,run_root:Path) -> dict[str,Any]:
    """Authenticate every committed stage and recorded job before takeover."""
    from msae_measurement_v2_run import verify_prepared
    from run_msae_measurement_v2 import _validated_raw_cache,_validated_transform
    verify_prepared(cfg,config_path);config_sha=_sha(config_path)
    raw_root=run_root/"raw_cache"
    if raw_root.exists():
        unknown={p.name for p in raw_root.iterdir()}-set(ROLES)
        if unknown:raise RuntimeError(f"unknown raw-cache IDs: {sorted(unknown)}")
        for role in ROLES:
            if (raw_root/role).exists():
                manifest=_validated_raw_cache(cfg,config_path,role);_validate_producer(run_root,config_sha,manifest["lineage"],f"extract_{role}")
    transform_root=run_root/"transforms"
    if transform_root.exists():
        unknown={p.name for p in transform_root.iterdir()}-set(JOBS)
        if unknown:raise RuntimeError(f"unknown transform IDs: {sorted(unknown)}")
        for job in JOBS:
            if (transform_root/job).exists():
                complete=_validated_transform(cfg,config_path,job);_validate_producer(run_root,config_sha,complete,f"transform_{job}")
    if (run_root/"analysis").exists():
        validate_analysis_truth(cfg,config_path,run_root);_validate_producer(run_root,config_sha,_read(run_root/"analysis/COMPLETE.json"),"analyze")
    expected=_expected_commands(str(config_path.relative_to(Path.cwd())))
    for started_path in (run_root/"jobs").glob("*.started.json"):
        match=re.fullmatch(r"attempt([1-9][0-9]*)_(extract_(?:discovery|calibration|C1|C2)|transform_g[4-7]|analyze)\.started\.json",started_path.name)
        if match is None:raise RuntimeError(f"unknown recovery job ID: {started_path.name}")
        attempt,short=int(match.group(1)),match.group(2);full=f"attempt{attempt}_{short}";row=_read(started_path)
        command=expected[short];digest=_command_sha(command)
        if row.get("config_sha256")!=config_sha or row.get("command")!=command or row.get("command_sha256")!=digest:raise RuntimeError(f"recovery job drift: {full}")
        lease_path=run_root/"leases"/f"{full}.json"
        if not lease_path.is_file() or _read(lease_path)!=row:raise RuntimeError(f"recovery lease drift: {full}")
        terminal_path=run_root/"jobs"/f"{full}.terminal.json"
        if terminal_path.exists():
            terminal=_read(terminal_path)
            if terminal.get("config_sha256")!=config_sha or terminal.get("command_sha256")!=digest:raise RuntimeError(f"recovery terminal drift: {full}")
    started_names={p.name.removesuffix(".started.json") for p in (run_root/"jobs").glob("*.started.json")}
    for path in (run_root/"jobs").glob("*.terminal.json"):
        if path.name.removesuffix(".terminal.json") not in started_names:raise RuntimeError(f"orphan terminal record: {path.name}")
    lease_names={p.name.removesuffix(".json") for p in (run_root/"leases").glob("*.json")}
    if lease_names!=started_names:raise RuntimeError("lease/job inventory mismatch")
    return {"config_sha256":config_sha,"authenticated_jobs":sorted(started_names)}


if __name__=="__main__":
    import argparse
    parser=argparse.ArgumentParser();parser.add_argument("--recovery",action="store_true")
    parser.add_argument("--config",type=Path,required=True);parser.add_argument("--run-root",type=Path,required=True)
    args=parser.parse_args();sys.path.insert(0,str(Path(__file__).resolve().parent))
    from msae_measurement_v2_run import load_config
    config_path=args.config.resolve(strict=True);cfg=load_config(config_path)
    if not args.recovery:parser.error("--recovery required")
    print(json.dumps(validate_recovery_state(cfg,config_path,args.run_root.resolve(strict=True)),indent=2,sort_keys=True))
