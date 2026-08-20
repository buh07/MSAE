#!/usr/bin/env python3
from __future__ import annotations
import hashlib,json,os,time
from pathlib import Path
ROOT=Path(os.environ.get('MSAE_ROOT',Path.cwd()))
OUT=ROOT/'reports/provenance/transformer_realistic_bridge_v1_r2_postresult'
def sha(p:Path)->str:return hashlib.sha256(p.read_bytes()).hexdigest()
def files_under(rel:str):
 p=ROOT/rel
 return [q for q in p.rglob('*') if q.is_file()]
def main():
 if OUT.exists():raise RuntimeError('preservation namespace exists')
 OUT.mkdir(parents=True)
 for name,src in [('PAPER_PRE_UPDATE.md',ROOT/'PAPER.md'),('CLAIM_LEDGER_PRE_UPDATE.json',ROOT/'reports/paper_claim_ledger_v1.json')]:
  (OUT/name).write_bytes(src.read_bytes())
 rels=[
  'PLAN_TRANSFORMER_REALISTIC_BRIDGE_V1_R2.md',
  'scripts/transformer_realistic_bridge_v1_r2.py',
  'scripts/launch_transformer_realistic_bridge_v1_r2_tmux.sh',
  'scripts/verify_transformer_realistic_bridge_v1_r2_recovery.py',
  'tests/test_transformer_realistic_bridge_v1_r2.py',
  'reports/claim_review/transformer_realistic_bridge_v1_r2_post_result_claim_review.md',
 ]
 paths=[ROOT/x for x in rels]
 for rel in ('configs/transformer_realistic_bridge_v1_r2','configs/transformer_realistic_methods_v1_r2','data/transformer_realistic_bridge_v1_r2_prepared','data/transformer_realistic_methods_v1_r2_prepared','results/transformer_realistic_bridge_v1_20260810r2','results/transformer_realistic_methods_v1_20260810r2','reports/provenance/transformer_realistic_bridge_v1_run_20260810r2','reports/provenance/transformer_realistic_methods_v1_run_20260810r2','reports/provenance/transformer_realistic_bridge_v1_r2_recovery'):
  paths.extend(files_under(rel))
 paths=sorted(set(paths),key=lambda p:p.relative_to(ROOT).as_posix())
 missing=[str(p) for p in paths if not p.is_file()]
 if missing:raise RuntimeError(missing)
 inv=[{'path':p.relative_to(ROOT).as_posix(),'bytes':p.stat().st_size,'sha256':sha(p)} for p in paths]
 manifest={'schema_version':'transformer_realistic_bridge_v1_r2_postresult_preservation','status':'PRESERVED_COMPLETE_RESULT','bridge_final_status':json.loads((ROOT/'results/transformer_realistic_bridge_v1_20260810r2/final/result.json').read_text())['status'],'methods_final_status':json.loads((ROOT/'results/transformer_realistic_methods_v1_20260810r2/final/result.json').read_text())['status'],'immutable_namespace_modified':False,'paper_and_ledger_snapshotted_before_update':True,'inventory':inv,'created_time_ns':time.time_ns()}
 with (OUT/'PRESERVATION.json').open('x') as f:json.dump(manifest,f,indent=2,sort_keys=True);f.write('\n')
 print(json.dumps({'status':'PASS','files':len(inv),'manifest_sha256':sha(OUT/'PRESERVATION.json')},sort_keys=True))
if __name__=='__main__':main()
