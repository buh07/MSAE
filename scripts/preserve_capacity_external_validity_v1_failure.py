#!/usr/bin/env python3
from __future__ import annotations
import hashlib,json,os,time
from pathlib import Path
ROOT=Path(os.environ.get('MSAE_ROOT',Path(__file__).resolve().parents[1]));OUT=ROOT/'reports/provenance/capacity_external_validity_v1_failure_preservation'
def sha(p:Path)->str:return hashlib.sha256(p.read_bytes()).hexdigest()
def add_tree(rel:str,out:list[Path])->None:
 p=ROOT/rel
 if p.exists():out.extend(q for q in p.rglob('*') if q.is_file() and q.suffix!='.jsonl')
def main()->None:
 if OUT.exists():raise RuntimeError('failure preservation exists')
 cap_freeze=ROOT/'configs/capacity_controller_diagnostic_v1/FREEZE.json';ext_freeze=ROOT/'configs/trained_copy_external_v1/FREEZE.json';cf=json.loads(cap_freeze.read_text());ef=json.loads(ext_freeze.read_text())
 required=[
  'PLAN_CAPACITY_EXTERNAL_VALIDITY_V1.md','scripts/capacity_external_validity_v1.py','scripts/launch_capacity_external_validity_v1_tmux.sh','tests/test_capacity_external_validity_v1.py',
  'configs/capacity_controller_diagnostic_v1/run.json','configs/capacity_controller_diagnostic_v1/GENERATOR_LOCK.json','configs/capacity_controller_diagnostic_v1/FREEZE.json',
  'configs/trained_copy_external_v1/run.json','configs/trained_copy_external_v1/GENERATOR_LOCK.json','configs/trained_copy_external_v1/FREEZE.json',
  'data/capacity_controller_diagnostic_v1_prepared/PANEL_METADATA.json','data/capacity_controller_diagnostic_v1_prepared/PREPARED.json',
  'data/trained_copy_external_v1_prepared/PANEL_METADATA.json','data/trained_copy_external_v1_prepared/PREPARED.json',
  'reports/adversarial/capacity_controller_diagnostic_v1_candidate_review.md','reports/adversarial/trained_copy_external_v1_candidate_review.md',
  'reports/adversarial/capacity_controller_diagnostic_v1_frozen_review.md','reports/adversarial/trained_copy_external_v1_frozen_review.md',
  'reports/provenance/capacity_external_validity_v1_REVIEW_BINDING.json','reports/provenance/capacity_external_validity_v1_launcher_20260810.log']
 paths=[ROOT/x for x in required]
 for rel in ('reports/provenance/capacity_controller_diagnostic_v1_candidate','reports/provenance/trained_copy_external_v1_candidate','results/capacity_controller_diagnostic_v1_20260810','results/trained_copy_external_v1_20260810','reports/provenance/capacity_controller_diagnostic_v1_run_20260810','reports/provenance/trained_copy_external_v1_run_20260810'):add_tree(rel,paths)
 paths=sorted(set(paths),key=lambda p:p.relative_to(ROOT).as_posix());missing=[str(p) for p in paths if not p.is_file()]
 if missing:raise RuntimeError(missing)
 cp=ROOT/'reports/provenance/capacity_controller_diagnostic_v1_run_20260810/events';ep=ROOT/'reports/provenance/trained_copy_external_v1_run_20260810/events';ext_result=json.loads((ROOT/'results/trained_copy_external_v1_20260810/final/result.json').read_text())
 facts={
  'capacity_train_opened':(cp/'010_CAPACITY_TRAIN_OPENED.json').is_file(),'capacity_development_opened':(cp/'011_CAPACITY_DEVELOPMENT_OPENED.json').is_file(),'capacity_development_complete':(cp/'012_CAPACITY_DEVELOPMENT_COMPLETE.json').is_file(),'capacity_confirmation_opened':(cp/'013_CAPACITY_CONFIRMATION_OPENED.json').is_file(),'capacity_final_exists':(ROOT/'results/capacity_controller_diagnostic_v1_20260810/final/result.json').exists(),
  'external_access_may_have_occurred':(ep/'021_ACCESS_MAY_HAVE_OCCURRED.json').is_file(),'external_train_opened':(ep/'022_EXTERNAL_TRAIN_OPENED.json').is_file(),'external_status':ext_result['status'],'external_payload_accessed':ext_result['external_payload_accessed'],'external_training_performed':ext_result['training_performed']}
 expected={'capacity_train_opened':True,'capacity_development_opened':True,'capacity_development_complete':False,'capacity_confirmation_opened':False,'capacity_final_exists':False,'external_access_may_have_occurred':False,'external_train_opened':False,'external_status':'BLOCKED_UNOPENED','external_payload_accessed':False,'external_training_performed':False}
 if facts!=expected:raise RuntimeError({'facts':facts,'expected':expected})
 ckpts=sorted((ROOT/'results/capacity_controller_diagnostic_v1_20260810/checkpoints').rglob('*.pt'))
 if len(ckpts)!=27:raise RuntimeError(f'expected 27 partial checkpoints, got {len(ckpts)}')
 inv=[{'path':p.relative_to(ROOT).as_posix(),'bytes':p.stat().st_size,'sha256':sha(p)} for p in paths]
 manifest={'schema_version':'capacity_external_validity_v1_failure_preservation','status':'PRESERVED_TECHNICAL_FAILURE','created_time_ns':time.time_ns(),'facts':facts,'failure':'AttributeError: module torch has no attribute flatnonzero','partial_checkpoints':len(ckpts),'partial_checkpoint_hashes':[{'path':p.relative_to(ROOT).as_posix(),'sha256':sha(p)} for p in ckpts],'capacity_freeze_sha256':sha(cap_freeze),'external_freeze_sha256':sha(ext_freeze),'capacity_payload_hash_records':cf['payloads'],'external_payload_hash_records':ef['payloads'],'scientific_jsonl_accessed_during_preservation':False,'inventory':inv}
 OUT.mkdir(parents=True)
 with (OUT/'PRESERVATION.json').open('x') as f:json.dump(manifest,f,indent=2,sort_keys=True);f.write('\n')
 print(json.dumps({'status':'PASS','files':len(inv),'checkpoints':len(ckpts),'sha256':sha(OUT/'PRESERVATION.json')},sort_keys=True))
if __name__=='__main__':main()
