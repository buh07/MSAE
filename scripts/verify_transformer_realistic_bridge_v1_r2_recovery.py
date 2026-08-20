#!/usr/bin/env python3
"""Payload-blind verification for the v1-r2 prelaunch technical successor."""
from __future__ import annotations
import argparse,ast,hashlib,json,os
from pathlib import Path
from typing import Any
ROOT=Path(os.environ.get('MSAE_ROOT',Path.cwd()))
REC=ROOT/'reports/provenance/transformer_realistic_bridge_v1_r2_recovery'
AUTH=REC/'RECOVERY_AUTHORIZATION.json'
PRELOCK=REC/'PRELOCK_PARITY.json'
CONTINUITY=REC/'PAYLOAD_CONTINUITY.json'
SUPPLEMENT=REC/'REVIEW_BINDING_PRESERVATION_SUPPLEMENT.json'
SUPERSEDED_INDEX=REC/'SUPERSEDED_PARITY_INDEX.json'
def load(p:Path)->Any:return json.loads(p.read_text())
def sha(p:Path)->str:return hashlib.sha256(p.read_bytes()).hexdigest()
def canonical(x:Any)->bytes:return json.dumps(x,sort_keys=True,separators=(',',':'),allow_nan=False).encode()
def atomic(p:Path,x:Any)->None:
 p.parent.mkdir(parents=True,exist_ok=True);tmp=p.with_name(p.name+'.tmp')
 with tmp.open('x') as f:json.dump(x,f,indent=2,sort_keys=True,allow_nan=False);f.write('\n')
 os.replace(tmp,p)
def verify_inventory(p:Path)->None:
 x=load(p)
 for item in x['candidate_inventory']:
  if item['path'].endswith('.jsonl'):raise RuntimeError('payload path in frozen inventory')
  q=ROOT/item['path']
  if not q.is_file() or q.stat().st_size!=item['bytes'] or sha(q)!=item['sha256']:raise RuntimeError(f'inventory drift {q}')
def normalize_config(x:dict[str,Any])->dict[str,Any]:
 x=json.loads(json.dumps(x));x.pop('namespace');x.pop('runtime');x['scope'].pop('technical_successor_of_prelaunch_stop',None);return x
def scientific_ast(s:str)->dict[str,str]:
 excluded={'candidate_paths','candidate_preflight','prepare','experiment_inventory'}
 tree=ast.parse(s);out={}
 for node in tree.body:
  if isinstance(node,(ast.FunctionDef,ast.ClassDef)) and node.name not in excluded:
   out[node.name]=ast.dump(node,include_attributes=False)
 return out
def normalize_launcher(s:str)->str:
 return (s.replace('MSAE_ROOT="$ROOT" python "$ROOT/scripts/verify_transformer_realistic_bridge_v1_r2_recovery.py" check-bound >/dev/null\n','')
  .replace('20260810r2','20260810').replace('transformer_realistic_bridge_v1_r2.py','transformer_realistic_bridge_v1.py').replace('\\$RUN_ROOT','$RUN_ROOT'))
def prelock()->dict[str,Any]:
 a=load(AUTH);unsigned=dict(a);att=unsigned.pop('attestation_sha256')
 if hashlib.sha256(canonical(unsigned)).hexdigest()!=att:raise RuntimeError('authorization attestation digest')
 if a['status']!='AUTHORIZED_NEW_TECHNICAL_SUCCESSOR' or a['same_namespace_retry_authorized'] or a['scientific_protocol_change_authorized']:raise RuntimeError('recovery authorization scope')
 s=load(SUPPLEMENT);unsigned_s=dict(s);att_s=unsigned_s.pop('attestation_sha256')
 if hashlib.sha256(canonical(unsigned_s)).hexdigest()!=att_s or s['authorization_sha256']!=sha(AUTH) or s['same_namespace_retry_authorized']:raise RuntimeError('review-binding supplement digest/scope')
 for item in s['old_review_bindings']:
  p=ROOT/item['path']
  if not p.is_file() or sha(p)!=item['sha256']:raise RuntimeError(f'old review-binding drift {item["kind"]}')
 h=load(SUPERSEDED_INDEX);unsigned_h=dict(h);att_h=unsigned_h.pop('attestation_sha256')
 if hashlib.sha256(canonical(unsigned_h)).hexdigest()!=att_h or h['status']!='AUDIT_ONLY_NONAUTHORITATIVE' or h['authoritative_report']!=PRELOCK.relative_to(ROOT).as_posix():raise RuntimeError('superseded parity index')
 for item in h['historical_reports']:
  if item['status']!='SUPERSEDED_NONAUTHORITATIVE' or sha(ROOT/item['path'])!=item['sha256']:raise RuntimeError('historical parity drift')
 for item in a['prior_terminals']:
  p=ROOT/item['path'];t=load(p)
  if sha(p)!=item['sha256'] or t['status']!=a['required_prior_status']:raise RuntimeError('terminal lineage')
  for k,v in a['required_prior_attestations'].items():
   if t.get(k)!=v:raise RuntimeError(f'prior attestation {k}')
 if sha(ROOT/'configs/transformer_realistic_bridge_v1/FREEZE.json')!=a['old_bridge_freeze_sha256'] or sha(ROOT/'configs/transformer_realistic_methods_v1/FREEZE.json')!=a['old_methods_freeze_sha256']:raise RuntimeError('old freeze drift')
 for kind in ('bridge','methods'):
  verify_inventory(ROOT/f'configs/transformer_realistic_{kind}_v1/GENERATOR_LOCK.json')
  verify_inventory(ROOT/f'configs/transformer_realistic_{kind}_v1/FREEZE.json')
  old=load(ROOT/f'configs/transformer_realistic_{kind}_v1/run.json');new=load(ROOT/f'configs/transformer_realistic_{kind}_v1_r2/run.json')
  if normalize_config(old)!=normalize_config(new):raise RuntimeError(f'scientific config drift {kind}')
 old_src=(ROOT/'scripts/transformer_realistic_bridge_v1.py').read_text();new_src=(ROOT/'scripts/transformer_realistic_bridge_v1_r2.py').read_text()
 if scientific_ast(old_src)!=scientific_ast(new_src):raise RuntimeError('scientific implementation drift')
 old_l=(ROOT/'scripts/launch_transformer_realistic_bridge_v1_tmux.sh').read_text();new_l=(ROOT/'scripts/launch_transformer_realistic_bridge_v1_r2_tmux.sh').read_text()
 if old_l!=normalize_launcher(new_l):raise RuntimeError('launcher has changes beyond lineage and deferred RUN_ROOT fix')
 if 'MSAE_ROOT="\\$RUN_ROOT"' not in new_l or 'tee "\\$RUN_ROOT/' not in new_l:raise RuntimeError('RUN_ROOT is not deferred')
 return {'schema_version':'transformer_realistic_bridge_v1_r2_prelock_parity','status':'PASS','payloads_accessed':False,'same_namespace_retry':False,'authorization_sha256':sha(AUTH),'review_binding_supplement_sha256':sha(SUPPLEMENT),'superseded_parity_index_sha256':sha(SUPERSEDED_INDEX),'old_bridge_freeze_sha256':a['old_bridge_freeze_sha256'],'old_methods_freeze_sha256':a['old_methods_freeze_sha256'],'old_source_sha256':sha(ROOT/'scripts/transformer_realistic_bridge_v1.py'),'new_source_sha256':sha(ROOT/'scripts/transformer_realistic_bridge_v1_r2.py'),'old_launcher_sha256':sha(ROOT/'scripts/launch_transformer_realistic_bridge_v1_tmux.sh'),'new_launcher_sha256':sha(ROOT/'scripts/launch_transformer_realistic_bridge_v1_r2_tmux.sh'),'scientific_config_equal':True,'scientific_implementation_equal_after_lineage_normalization':True,'launcher_only_lineage_and_deferred_expansion':True}
def continuity()->dict[str,Any]:
 pre=prelock();out={}
 for kind in ('bridge','methods'):
  old=load(ROOT/f'configs/transformer_realistic_{kind}_v1/FREEZE.json')['opaque_panel_metadata']
  new=load(ROOT/f'data/transformer_realistic_{kind}_v1_r2_prepared/PANEL_METADATA.json')['panels']
  if set(old)!=set(new):raise RuntimeError(f'panel set drift {kind}')
  for stage in old:
   for field in ('bytes','rows','sha256'):
    if old[stage][field]!=new[stage][field]:raise RuntimeError(f'payload continuity drift {kind}:{stage}:{field}')
   if Path(old[stage]['path']).name!=Path(new[stage]['path']).name:raise RuntimeError('panel basename drift')
  out[kind]={stage:{field:new[stage][field] for field in ('bytes','rows','sha256')} for stage in new}
 return {'schema_version':'transformer_realistic_bridge_v1_r2_payload_continuity','status':'PASS','payloads_accessed':False,'comparison_source':'opaque v1 freeze metadata versus r2 PANEL_METADATA only','prelock_parity_sha256':sha(PRELOCK),'panels':out}
def check_bound()->dict[str,Any]:
 expected=prelock();p=load(PRELOCK)
 if p!=expected:raise RuntimeError('prelock parity report drift')
 c=continuity()
 if load(CONTINUITY)!=c:raise RuntimeError('continuity report drift')
 for kind in ('bridge','methods'):
  f=load(ROOT/f'configs/transformer_realistic_{kind}_v1_r2/FREEZE.json')
  paths={x['path']:x for x in f['candidate_inventory']}
  for q in (PRELOCK,CONTINUITY,AUTH):
   rel=q.relative_to(ROOT).as_posix()
   if rel not in paths or paths[rel]['sha256']!=sha(q):raise RuntimeError(f'recovery artifact not freeze-bound {kind}:{rel}')
 return {'status':'PASS','payloads_accessed':False,'prelock_sha256':sha(PRELOCK),'continuity_sha256':sha(CONTINUITY)}
def check_prelock()->dict[str,Any]:
 expected=prelock()
 if load(PRELOCK)!=expected:raise RuntimeError('prelock parity report drift')
 return {'status':'PASS','payloads_accessed':False,'prelock_sha256':sha(PRELOCK)}
def main()->None:
 ap=argparse.ArgumentParser();ap.add_argument('mode',choices=('write-prelock','check-prelock','write-continuity','check-bound'));a=ap.parse_args()
 if a.mode=='write-prelock':
  if PRELOCK.exists():raise RuntimeError('prelock report exists')
  atomic(PRELOCK,prelock());print(json.dumps({'status':'PASS','path':str(PRELOCK)}))
 elif a.mode=='check-prelock': print(json.dumps(check_prelock(),sort_keys=True))
 elif a.mode=='write-continuity':
  if CONTINUITY.exists():raise RuntimeError('continuity report exists')
  atomic(CONTINUITY,continuity());print(json.dumps({'status':'PASS','path':str(CONTINUITY)}))
 else: print(json.dumps(check_bound(),sort_keys=True))
if __name__=='__main__':main()
