from __future__ import annotations

import hashlib
import importlib.util
import json
import subprocess
import sys
from pathlib import Path

import numpy as np
import pytest
import torch

ROOT=Path(__file__).resolve().parents[1]
SPEC=importlib.util.spec_from_file_location("two_tier",ROOT/"scripts/canonical_induction_two_tier_v2.py")
assert SPEC and SPEC.loader
m=importlib.util.module_from_spec(SPEC); SPEC.loader.exec_module(m)
CFG=json.loads((ROOT/"configs/canonical_induction_two_tier_v2/run.json").read_text())


def make_outputs(n=128,circuit=.2,sham=-.6,control=-.8,czero=.4,tzero=.8,clean=1.,corrupt=-1.):
    raw={"clean":clean,"corrupt":corrupt,"full_clean":clean,"full_sham":-1.,"circuit_clean":circuit,"circuit_sham":sham,"control_clean":control,"circuit_zero":czero,"control_zero":tzero}
    return m._raw_outputs(raw,n)


def test_endpoint_seed_exact_contract():
    pre=b"20260822|development|joint_recovery"
    assert m.endpoint_seed(20260822,"development","joint_recovery")==int.from_bytes(hashlib.sha256(pre).digest()[:4],"little")


def test_registry_is_exact_ordered_disjoint_and_layer_matched():
    circuit=CFG["model"]["circuit_heads"]; controls=CFG["model"]["control_heads"]
    assert circuit==[[0,1],[0,10],[3,0],[2,2],[4,11],[5,5],[5,8],[5,9],[6,9]]
    assert controls==[[0,0],[0,2],[3,1],[2,0],[4,0],[5,0],[5,1],[5,2],[6,0]]
    assert [x[0] for x in circuit]==[x[0] for x in controls]
    assert not {tuple(x) for x in circuit}&{tuple(x) for x in controls}


def test_source_pdf_and_transcript_are_bound():
    p=ROOT/CFG["source_registry"]["pdf"]
    assert m.sha(p)==CFG["source_registry"]["pdf_sha256"]
    m.verify_source(CFG)


def test_panels_are_fresh_disjoint_and_well_formed():
    dev=m.generate_rows(CFG,"development"); con=m.generate_rows(CFG,"confirmation")
    assert len(dev)==len(con)==128
    assert {r["block_index"] for r in dev}==set(range(8))
    assert all(len(r["clean_ids"])==31 for r in dev+con)
    assert not {tuple(r["clean_ids"]) for r in dev}&{tuple(r["clean_ids"]) for r in con}
    old=m.readjl(ROOT/"data/canonical_induction_circuit_v1_prepared/development.jsonl")
    assert not {tuple(r["clean_ids"]) for r in dev}&{tuple(r["clean_ids"]) for r in old}


def test_all_position_slice_replacement_zero_and_outside_invariance():
    base=torch.arange(2*3*12,dtype=torch.float32).reshape(2,3,12); donor=torch.full((2,3,2),-7.)
    out=m.apply_head_intervention(base,2,{1:donor},[4])
    assert torch.equal(out[...,2:4],donor)
    assert torch.equal(out[...,8:10],torch.zeros_like(out[...,8:10]))
    mask=torch.ones(12,dtype=torch.bool); mask[2:4]=False; mask[8:10]=False
    assert torch.equal(out[...,mask],base[...,mask])
    assert torch.equal(base,torch.arange(2*3*12,dtype=torch.float32).reshape(2,3,12))


def test_actual_production_hook_callback_path_on_toy_module():
    assert all(m.tiny_hook_integration().values())


def test_simultaneous_disjoint_slices_and_row_permutation_detection():
    base=torch.zeros(3,4,12); d1=torch.arange(3,dtype=torch.float32)[:,None,None].expand(3,4,2).clone(); d2=torch.full((3,4,2),2.)
    out=m.apply_head_intervention(base,2,{1:d1,3:d2},[])
    assert torch.equal(out[...,2:4],d1) and torch.equal(out[...,6:8],d2)
    assert not torch.equal(d1.flip(0),out[...,2:4])


def test_raw_positive_metrics_are_registered_values():
    rows,outs=make_outputs(); vals=m.compute_rows(CFG,rows,outs); s=m.summarize(CFG,vals,"calibration")
    assert s["tier_a_pass"] and s["tier_b_pass"]
    assert s["metrics"]["joint_recovery"]["point"]==pytest.approx(.6)
    assert s["metrics"]["selectivity"]["point"]==pytest.approx(.4)
    assert s["metrics"]["circuit_control_margin"]["point"]==pytest.approx(.5)
    assert s["metrics"]["ablation_advantage"]["point"]==pytest.approx(.2)


def test_low_recovery_and_support_stop():
    rows,outs=make_outputs(circuit=-.8); s=m.summarize(CFG,m.compute_rows(CFG,rows,outs),"development")
    assert s["tier_a_pass"] and not s["tier_b_pass"] and s["status"]=="DEVELOPMENT_UPSTREAM_SET_STOP"
    rows,outs=make_outputs(n=80); s=m.summarize(CFG,m.compute_rows(CFG,rows,outs),"development")
    assert not s["support_pass"] and s["status"]=="DEVELOPMENT_SKYLINE_STOP"


def test_nan_is_technical_and_not_complete_case_excluded():
    rows,outs=make_outputs(); outs["circuit_clean"][0,0]=np.nan
    vals=m.compute_rows(CFG,rows,outs); s=m.summarize(CFG,vals,"development")
    assert vals[0]["live_finite"] is False
    assert s["status"]=="TECHNICAL_INVALID_STOP"


def test_denominator_zero_or_negative_excluded_from_g():
    rows,outs=make_outputs(clean=-1.,corrupt=-1.); vals=m.compute_rows(CFG,rows,outs)
    assert not any(r["gate_cohort"] for r in vals)
    rows,outs=make_outputs(clean=-2.,corrupt=-1.); vals=m.compute_rows(CFG,rows,outs)
    assert not any(r["gate_cohort"] for r in vals)


def test_point_thresholds_inclusive_lower_thresholds_strict():
    # Recovery .5 has lower .5 and therefore passes the separate .4 strict lower gate.
    rows,outs=make_outputs(circuit=0.0); s=m.summarize(CFG,m.compute_rows(CFG,rows,outs),"development")
    assert s["metrics"]["joint_recovery"]["point"]==pytest.approx(.5)
    assert s["metrics"]["joint_recovery"]["lower"]>.4


def test_every_threshold_comparator_has_below_equal_above_semantics():
    rows=m.threshold_oracles(CFG)
    assert len(rows)==30 and all(r["pass"] for r in rows)
    for name in {r["name"] for r in rows}:
        got={r["relation"]:r["actual"] for r in rows if r["name"]==name}
        inclusive=next(r["inclusive"] for r in rows if r["name"]==name)
        assert got==({"below":False,"equal":True,"above":True} if inclusive else {"below":False,"equal":False,"above":True})


def test_equal_block_not_row_weighted():
    rows=[]
    for b in range(8):
        n=1 if b==0 else 10
        for i in range(n): rows.append({"block_index":b,"gate_cohort":True,"x":10. if b==0 else 0.})
    got=m.equal_block_interval(rows,"x",CFG,"development")
    assert got and got["point"]==pytest.approx(1.25)


def test_raw_and_hook_calibration_replay_passes_after_prepare():
    root=ROOT/CFG["runtime"]["prepared_root"]
    if not root.exists(): pytest.skip("prepare lifecycle not run yet")
    got=m.replay_calibration(CFG)
    assert got["pass"]
    assert all(x["pass"] for x in got["raw_results"])
    assert all(got["hook_result"].values())
    assert all(got["hook_integration"].values())
    assert all(x["pass"] for x in got["threshold_oracles"])


def test_scope_firewall():
    m.validate_scope(CFG)
    bad=json.loads(json.dumps(CFG)); bad["scope"]["training"]=True
    with pytest.raises(RuntimeError,match="forbidden scope"): m.validate_scope(bad)


def test_cli_is_command_specific_and_rejects_irrelevant_flags():
    run=ROOT/"scripts/canonical_induction_two_tier_v2.py"; cfg=ROOT/"configs/canonical_induction_two_tier_v2/run.json"
    bad=subprocess.run([sys.executable,str(run),"preservation-verify","--config",str(cfg),"--stage","confirmation"],capture_output=True,text=True)
    assert bad.returncode!=0 and "unrecognized arguments" in bad.stderr
    dup=subprocess.run([sys.executable,str(run),"preservation-verify","--config",str(cfg),"--config",str(cfg)],capture_output=True,text=True)
    assert dup.returncode!=0 and "duplicated option forbidden" in dup.stderr
    dup_equal=subprocess.run([sys.executable,str(run),"preservation-verify",f"--config={cfg}","--config",str(cfg)],capture_output=True,text=True)
    assert dup_equal.returncode!=0 and "duplicated option forbidden" in dup_equal.stderr
    help_text=subprocess.run([sys.executable,str(run),"--help"],capture_output=True,text=True,check=True).stdout
    assert "train" not in help_text and "representation-method" not in help_text


def test_confirmation_pre_gate_skips_payload_in_freeze_verifier_source():
    text=(ROOT/"scripts/canonical_induction_two_tier_v2.py").read_text()
    assert 'if not include_confirmation and item["path"]==confirmation: continue' in text
    assert 'verify_freeze(config,cfg,include_confirmation=False)' in text


def test_v11_preservation_manifest_and_formal_outcome():
    m.preservation_verify(CFG)
    manifest=json.loads((ROOT/CFG["preservation"]["v1_1_manifest"]).read_text())
    assert "data/canonical_induction_circuit_v1_prepared" in manifest["tree_roots"]
    assert {x["path"] for x in manifest["files"] if x["path"].startswith("data/canonical_induction_circuit_v1_prepared/")}


def test_qa_schema_is_exact():
    assert tuple(CFG["qa"]["named_arrays"])==m.QA_ARRAYS


def test_attempt_and_authorization_reconciliation_are_present_and_forward_free():
    text=(ROOT/"scripts/canonical_induction_two_tier_v2.py").read_text()
    rec=text[text.index("def reconcile_stage"):text.index("def validate_complete")]
    assert "load_model" not in rec and "run_condition" not in rec
    auth=text[text.index("def reconcile_authorization"):text.index("def validate_authorization")]
    assert "confirmation.jsonl" not in auth and "include_confirmation=True" not in auth and "verify_freeze" not in auth


def test_cache_blob_hashes_are_revalidated():
    rec=m.verify_cache(CFG)
    assert rec["status"]=="PASS" and any(x["name"].endswith((".bin",".safetensors")) for x in rec["files"])


def test_validate_complete_rejects_skeletal_qa_and_started_payloads(tmp_path,monkeypatch):
    cfg=json.loads(json.dumps(CFG)); cfg["runtime"].update({"output_root":"results","provenance_root":"prov","prepared_root":"prepared","freeze":"config/FREEZE.json","cache_attestation":"candidate/cache.json"})
    monkeypatch.setattr(m,"ROOT",tmp_path)
    root=tmp_path/"results/development"; root.mkdir(parents=True); (tmp_path/"prov").mkdir(); (tmp_path/"config").mkdir(); (tmp_path/"candidate").mkdir()
    (tmp_path/"prov/launch_manifest.json").write_text('{}\n'); (tmp_path/"candidate/cache.json").write_text('{}\n')
    freeze={"candidate_inventory_sha256":"inventory"}; (tmp_path/"config/FREEZE.json").write_text(json.dumps(freeze)+'\n')
    rows,outs=make_outputs(); metrics=m.compute_rows(cfg,rows,outs)
    for r in metrics: r["stage"]="development"
    (tmp_path/"prepared").mkdir(); m.writejl(tmp_path/"prepared/development.jsonl",[{"stage":r["stage"],"row_index":r["row_index"],"block_index":r["block_index"],"component_id":r["component_id"]} for r in metrics])
    m.writejl(root/"metrics.jsonl",metrics); summary=m.summarize(cfg,metrics,"development"); m.exjson(root/"SUMMARY.json",summary); m.exjson(root/"QA.json",{"pass":True}); m.exjson(root/"STARTED.json",{"launch_manifest_sha256":m.sha(tmp_path/"prov/launch_manifest.json")})
    m.exjson(tmp_path/"prov/development_ATTEMPT.json",{"attempt_token":"tok","state":"CLOSED","stage":"development"})
    complete={"schema_version":"canonical_induction_two_tier_v2_complete","stage":"development","rows":128,"metrics_sha256":m.sha(root/"metrics.jsonl"),"qa_sha256":m.sha(root/"QA.json"),"summary_sha256":m.sha(root/"SUMMARY.json"),"freeze_sha256":m.sha(tmp_path/"config/FREEZE.json"),"freeze_inventory_sha256":"inventory","launch_manifest_sha256":m.sha(tmp_path/"prov/launch_manifest.json"),"cache_attestation_sha256":m.sha(tmp_path/"candidate/cache.json"),"attempt_token":"tok","status":summary["status"],"representation_methods":False,"training":False,"external_set_scope":"FIGURE2_UPSTREAM_SET_NOT_COMPLETE_RANDOM_TOKEN_CIRCUIT"}
    m.exjson(root/"COMPLETE.json",complete)
    with pytest.raises(RuntimeError,match="descriptive field|QA schema"): m.validate_complete(cfg,"development")


def test_qa_bundle_executes_reference_hash_schema_and_bitwise_validation(tmp_path,monkeypatch):
    cfg=json.loads(json.dumps(CFG)); cfg["runtime"]["provenance_root"]="prov"; cfg["qa"]["rows"]=2; cfg["panel"]["prompt_length"]=3; cfg["model"].update({"vocab_size":3,"head_size":2,"hidden_size":3}); monkeypatch.setattr(m,"ROOT",tmp_path)
    q=tmp_path/"prov/qa/development"; q.mkdir(parents=True)
    arrays={k:np.zeros(shape,dtype=np.float32) for k,shape in m.expected_qa_shapes(cfg).items()}
    np.savez(q/"QA_REFERENCE_1.npz",**arrays); np.savez(q/"QA_REFERENCE_2.npz",**arrays)
    fields={k:{"shape":list(v.shape),"dtype":"float32","bitwise_equal":True} for k,v in arrays.items()}
    comp={"schema_version":"canonical_induction_two_tier_v2_qa_comparison","stage":"development","fields":fields,"reference_1_sha256":m.sha(q/"QA_REFERENCE_1.npz"),"reference_2_sha256":m.sha(q/"QA_REFERENCE_2.npz"),"pass":True}; m.exjson(q/"QA_COMPARISON.json",comp)
    metrics=[]
    for b in range(8):
        row={"stage":"development","row_index":b,"block_index":b,"component_id":f"d:{b}","gate_cohort":True}
        row.update({name:0.0 for name in m.registered_descriptive_fields(cfg)}); metrics.append(row)
    qa={"decoder_clean_bitwise":True,"decoder_sham_bitwise":True,"circuit_self_patch_bitwise":True,"control_self_patch_bitwise":True,"descriptive":m.build_descriptive_reports(cfg,metrics,"development"),"worker_reference_matches":{str(rep):{k:True for k in m.QA_ARRAYS} for rep in (1,2)},"independent_comparison_sha256":m.sha(q/"QA_COMPARISON.json"),"pass":True}
    m.validate_qa_bundle(cfg,"development",qa,metrics)
    bad=arrays.copy(); bad[m.QA_ARRAYS[0]]=np.ones(m.expected_qa_shapes(cfg)[m.QA_ARRAYS[0]],dtype=np.float32); (q/"QA_REFERENCE_2.npz").unlink(); np.savez(q/"QA_REFERENCE_2.npz",**bad)
    with pytest.raises(RuntimeError,match="reference hash"): m.validate_qa_bundle(cfg,"development",qa,metrics)


def test_open_attempt_completion_is_orphaned_before_technical_closure(tmp_path,monkeypatch):
    cfg=json.loads(json.dumps(CFG)); cfg["runtime"]["output_root"]="results"; monkeypatch.setattr(m,"ROOT",tmp_path)
    root=tmp_path/"results/development"; root.mkdir(parents=True); (root/"COMPLETE.json").write_text('{}\n')
    m.orphan_open_attempt_completion(cfg,"development")
    assert not (root/"COMPLETE.json").exists() and (root/"ORPHANED_COMPLETE.json").is_file()


def test_technical_terminal_is_bound_to_closed_attempt(tmp_path,monkeypatch):
    cfg=json.loads(json.dumps(CFG)); cfg["runtime"].update({"output_root":"results","provenance_root":"prov","freeze":"config/FREEZE.json","cache_attestation":"candidate/cache.json"}); monkeypatch.setattr(m,"ROOT",tmp_path)
    (tmp_path/"prov").mkdir(); (tmp_path/"config").mkdir(); (tmp_path/"candidate").mkdir()
    (tmp_path/"prov/launch_manifest.json").write_text('{"launch":true}\n'); (tmp_path/"config/FREEZE.json").write_text('{"freeze":true}\n'); (tmp_path/"candidate/cache.json").write_text('{"cache":true}\n')
    _,attempt=m.attempt_paths(cfg,"development")
    m.exjson(attempt,{"schema_version":"canonical_induction_two_tier_v2_stage_attempt","stage":"development","attempt_token":"tok","controller_pid":123,"launch_manifest_sha256":m.sha(tmp_path/"prov/launch_manifest.json"),"state":"CLOSED_TECHNICAL_INVALID","updated_ns":1})
    m.technical_terminal(cfg,"development","fixture","launch")
    assert m.validate_technical_terminal(cfg,"development")["attempt_token"]=="tok"
    ar=m.loadj(attempt); ar["updated_ns"]=2; m.replace_json(attempt,ar)
    with pytest.raises(RuntimeError,match="attempt binding"): m.validate_technical_terminal(cfg,"development")


def test_transition_journals_precede_runtime_validation_in_source():
    text=(ROOT/"scripts/canonical_induction_two_tier_v2.py").read_text()
    gate=text[text.index("def development_gate("):text.index("def validate_gate_attempt(")]
    auth=text[text.index("def authorize_confirmation("):text.index("def reconcile_authorization(")]
    assert gate.index("validate_development_predecessor")<gate.index("exjson(attempt,new_gate_attempt")<gate.index("initial=validate_gate_attempt")
    assert auth.index("validate_development_gate")<auth.index("exjson(attempt,new_authorization_attempt")<auth.index("initial=validate_authorization_attempt")


def test_confirmation_path_guard_blocks_open_stat_and_hash(tmp_path):
    sealed=tmp_path/"confirmation.jsonl"; sealed.write_text("sealed\n")
    operations=(lambda:open(sealed).read(),lambda:sealed.stat(),lambda:m.sha(sealed))
    for operation in operations:
        with pytest.raises(RuntimeError,match="sealed confirmation payload access"):
            with m.deny_path_access(sealed): operation()


def test_gate_transition_requires_exact_predecessor(tmp_path):
    attempt=tmp_path/"attempt.json"
    m.exjson(attempt,{"state":"PRECHECK_JOURNALED","updated_ns":1})
    assert m.transition_gate_attempt(attempt,"PRECHECK_JOURNALED","VALIDATED")["state"]=="VALIDATED"
    with pytest.raises(RuntimeError,match="illegal development-gate transition"):
        m.transition_gate_attempt(attempt,"PRECHECK_JOURNALED","CLOSED_GATE_READY")


def test_authorization_transition_requires_exact_predecessor(tmp_path):
    attempt=tmp_path/"attempt.json"
    m.exjson(attempt,{"state":"PRECHECK_JOURNALED","updated_ns":1})
    assert m.transition_authorization_attempt(attempt,"PRECHECK_JOURNALED","PHASE1_STARTED")["state"]=="PHASE1_STARTED"
    with pytest.raises(RuntimeError,match="illegal authorization transition"):
        m.transition_authorization_attempt(attempt,"PRECHECK_JOURNALED","PHASE2_ACCESS_AUTHORIZED")


def test_authorization_publisher_and_reconciler_share_liveness_guard_in_source():
    text=(ROOT/"scripts/canonical_induction_two_tier_v2.py").read_text()
    publisher=text[text.index("def authorize_confirmation("):text.index("def reconcile_authorization(")]
    reconciler=text[text.index("def reconcile_authorization("):text.index("def validate_authorization(")]
    assert "validate_authorization_attempt(cfg,attempt,\"PRECHECK_JOURNALED\"" in publisher
    assert 'initial["authorizer_pid"]!=os.getpid()' in publisher
    assert 'os.kill(int(rec["authorizer_pid"]),0)' in reconciler
    assert "if not synthetic" in reconciler


def test_reconcilers_do_not_write_before_registered_predecessors(tmp_path,monkeypatch):
    cfg=json.loads(json.dumps(CFG)); cfg["runtime"].update({"output_root":"results","provenance_root":"prov"}); monkeypatch.setattr(m,"ROOT",tmp_path)
    monkeypatch.setattr(m,"require_config",lambda _path:cfg); monkeypatch.setattr(m,"validate_launch",lambda *_args:{})
    monkeypatch.setattr(m,"validate_development_predecessor",lambda _cfg:(_ for _ in ()).throw(RuntimeError("missing development")))
    with pytest.raises(RuntimeError,match="missing development"): m.reconcile_development_gate(Path("config"),"token")
    assert not (tmp_path/"results/DEVELOPMENT_GATE_ATTEMPT.json").exists()
    monkeypatch.setattr(m,"validate_development_gate",lambda _cfg:(_ for _ in ()).throw(RuntimeError("missing gate")))
    with pytest.raises(RuntimeError,match="missing gate"): m.reconcile_authorization(Path("config"),"token")
    assert not (tmp_path/"results/CONFIRMATION_AUTHORIZATION_ATTEMPT.json").exists()


def test_validate_launch_rejects_nonexact_manifest_before_runtime_checks(tmp_path,monkeypatch):
    cfg=json.loads(json.dumps(CFG)); cfg["runtime"]["provenance_root"]="prov"; monkeypatch.setattr(m,"ROOT",tmp_path)
    (tmp_path/"prov").mkdir(); (tmp_path/"prov/launch_manifest.json").write_text('{"schema_version":"canonical_induction_two_tier_v2_launch","extra":true}\n')
    with pytest.raises(RuntimeError,match="manifest schema"): m.validate_launch(cfg,"token")


def test_closed_development_reconciliation_publishes_missing_marker(tmp_path,monkeypatch):
    cfg=json.loads(json.dumps(CFG)); cfg["runtime"].update({"output_root":"results","provenance_root":"prov"}); monkeypatch.setattr(m,"ROOT",tmp_path)
    monkeypatch.setattr(m,"require_config",lambda _path:cfg); monkeypatch.setattr(m,"validate_launch",lambda *_args:{})
    _,attempt=m.attempt_paths(cfg,"development")
    m.exjson(attempt,{"schema_version":"canonical_induction_two_tier_v2_stage_attempt","stage":"development","attempt_token":"tok","controller_pid":999999,"launch_manifest_sha256":"launch","state":"CLOSED","updated_ns":1})
    calls=[]
    monkeypatch.setattr(m,"validate_complete",lambda _cfg,stage:calls.append(("validate",stage)) or {})
    monkeypatch.setattr(m,"publish_development_validated",lambda _cfg:calls.append(("publish","development")) or {})
    m.reconcile_stage(Path("config"),"development","launch")
    assert calls==[("validate","development"),("publish","development")]


def test_development_marker_publication_is_idempotent(tmp_path,monkeypatch):
    cfg=json.loads(json.dumps(CFG)); cfg["runtime"]["provenance_root"]="prov"; monkeypatch.setattr(m,"ROOT",tmp_path)
    payload={"schema_version":"fixture","status":"VALIDATED"}; monkeypatch.setattr(m,"development_validated_payload",lambda _cfg:payload)
    assert m.publish_development_validated(cfg)==payload
    digest=m.sha(m.development_validated_path(cfg))
    assert m.publish_development_validated(cfg)==payload and m.sha(m.development_validated_path(cfg))==digest


def test_every_forward_command_revalidates_frozen_binding_in_source():
    text=(ROOT/"scripts/canonical_induction_two_tier_v2.py").read_text()
    qa=text[text.index("def qa_reference("):text.index("def qa_compare(")]
    worker=text[text.index("def worker("):text.index("def technical_terminal(")]
    assert qa.index("review_binding(config)")<qa.index("load_model")
    assert qa.index("verify_freeze")<qa.index("load_model")
    assert worker.index("review_binding(config)")<worker.index("load_model")
    assert worker.index("verify_freeze")<worker.index("load_model")
