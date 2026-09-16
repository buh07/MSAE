#!/usr/bin/env python3
"""Prepare and freeze the independent MSAE measurement-v1 source and config."""
from __future__ import annotations
import argparse, array, collections, fcntl, hashlib, json, os, platform, signal, socket, subprocess, time, unicodedata
from pathlib import Path
from typing import Any
ROOT=Path(__file__).resolve().parents[1]
PROTOCOL='msae_independent_measurement_v1'
GENRES=('academic','bio','fiction','interview','news','whow','voyage')
TASKS={
 'absolute_position':['absolute_bucket','neutral_prefix_offset'],
 'relative_structural_position':['relative_quartile','head_signed_distance','dependency_depth'],
 'lexical_semantic_content':['token_identity','lemma_identity','entity_binary'],
}
TIER2=['upos_coarse','deprel_coarse','number','capitalization','word_length','punctuation','sentence_boundary','source_genre','lm_cross_entropy','reconstruction_fvu','non_target_retention']

def cbytes(x:Any)->bytes:return (json.dumps(x,sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False)+'\n').encode()
def sha_bytes(x:bytes)->str:return hashlib.sha256(x).hexdigest()
def sha_file(p:Path)->str:
 h=hashlib.sha256()
 with p.open('rb') as f:
  for b in iter(lambda:f.read(1<<20),b''):h.update(b)
 return h.hexdigest()
def write_json(p:Path,x:Any)->None:
 p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(cbytes(x))
def tuple_hash(*parts:str)->str:
 h=hashlib.sha256()
 for s in parts:
  b=unicodedata.normalize('NFC',s).encode();h.update(len(b).to_bytes(8,'big'));h.update(b)
 return h.hexdigest()
def parse_conllu(p:Path):
 sentences=[]; sent=[]
 for line in p.read_text(encoding='utf-8').splitlines()+['']:
  if not line:
   if sent: sentences.append(sent);sent=[]
   continue
  if line.startswith('#'):continue
  f=line.split('\t')
  if len(f)!=10 or '-' in f[0] or '.' in f[0]:continue
  sent.append(f)
 return sentences

def prepare()->dict[str,Any]:
 up=ROOT/'data/msae_independent_measurement_v1/amalgum_upstream'
 rev=subprocess.check_output(['git','-C',str(up),'rev-parse','HEAD'],text=True).strip()
 selected=[]; supports={}; role_docs={'C1':[],'C2':[]}; file_counts={}
 for genre in GENRES:
  paths=sorted((up/'amalgum'/genre/'dep').glob('*.conllu'))
  file_counts[genre]=len(paths)
  if len(paths)<50: raise RuntimeError(f'{genre}: fewer than 50 docs')
  ranked=sorted((tuple_hash(PROTOCOL,rev,p.relative_to(up).as_posix()),p.relative_to(up).as_posix(),p) for p in paths)
  for rank,(_,rel,p) in enumerate(ranked[:50]):
   role='C1' if rank%2==0 else 'C2'; sents=parse_conllu(p)
   if not sents:raise RuntimeError(f'empty selected {rel}')
   item={'genre':genre,'role':role,'rank':rank,'path':rel,'sha256':sha_file(p),'bytes':p.stat().st_size,'sentences':len(sents),'tokens':sum(map(len,sents))}
   selected.append(item);role_docs[role].append((item,sents))
 for role,docs in role_docs.items():
  classdocs={t:collections.defaultdict(set) for ts in TASKS.values() for t in ts}
  totals=collections.Counter(); entity_docs=set()
  for item,sents in docs:
   doc=item['path']; n_sent=len(sents)
   for si,sent in enumerate(sents):
    n=len(sent)
    heads={int(f[0]):int(f[6]) for f in sent}
    def depth(i):
     seen=set();d=0
     while i and i not in seen and d<20:seen.add(i);i=heads.get(i,0);d+=1
     return min(d,4)
    for j,f in enumerate(sent):
     tok,lemma,upos,feats,misc=f[1],f[2],f[3],f[5],f[9]
     vals={
      'absolute_bucket':str(min(6,j*7//max(1,n))),
      'neutral_prefix_offset':'planned_4way',
      'relative_quartile':str(min(3,j*4//max(1,n))),
      'head_signed_distance':str(max(-4,min(4,int(f[6])-int(f[0])))),
      'dependency_depth':str(depth(int(f[0]))),
      'token_identity':tok.lower(),'lemma_identity':lemma.lower(),
      'entity_binary':'ENTITY' if 'Entity=' in misc and misc.split('Entity=',1)[1].split('|',1)[0] not in ('','_') else 'O'}
     for t,v in vals.items():classdocs[t][v].add(doc)
     if vals['entity_binary']=='ENTITY':entity_docs.add(doc)
     totals['tokens']+=1
  audit={}
  for t,d in classdocs.items():
   kept={k:len(v) for k,v in d.items() if len(v)>=20}
   # token/lemma may have many labels; other tasks need >=2; planned prefix is structurally generated.
   ok=(t=='neutral_prefix_offset') or len(kept)>=2
   audit[t]={'status':'eligible' if ok else 'ineligible','retained_class_document_counts':dict(sorted(kept.items())),'all_class_count':len(d)}
  audit['entity_document_count']=len(entity_docs);audit['groups']=len(docs);audit['tokens']=totals['tokens']
  supports[role]=audit
  bad=[t for t in classdocs if audit[t]['status']!='eligible']
  if bad: raise RuntimeError(f'{role} unsupported: {bad}')
 split={'schema_version':'msae_independent_partition_v1','protocol_id':PROTOCOL,'source_revision':rev,'genres':list(GENRES),'file_counts':file_counts,'selected':selected,'support':supports}
 split['selected_sha256']=sha_bytes(cbytes(selected));split['partition_sha256']=sha_bytes(cbytes({k:v for k,v in split.items() if k!='partition_sha256'}))
 write_json(ROOT/'data/msae_independent_measurement_v1/source_partition.json',split)
 # Freeze all 500 unconditional per-role/task document maps.
 maps=[]
 for role in ('C1','C2'):
  bygenre={g:sorted(x[0]['path'] for x in role_docs[role] if x[0]['genre']==g) for g in GENRES}
  for task in [x for xs in TASKS.values() for x in xs]+TIER2[:8]:
   for draw in range(500):
    m={}
    for g,docs in bygenre.items():
     m[g]=[docs[int.from_bytes(hashlib.sha256(f'{PROTOCOL}|20260820|{role}|{task}|{g}|{draw}|{j}'.encode()).digest()[:8],'big')%len(docs)] for j in range(len(docs))]
    maps.append({'role':role,'task':task,'draw':draw,'documents':m})
 write_json(ROOT/'data/msae_independent_measurement_v1/bootstrap_maps.json',{'schema_version':'msae_independent_maps_v1','maps':maps})
 # Source inventory/license limitation.
 inv={'schema_version':'msae_independent_source_inventory_v1','remote':'https://github.com/gucorpling/amalgum.git','revision':rev,'license_file_sha256':sha_file(up/'README.md'),'selected_files':selected,'machine_annotations':True,'pretraining_overlap_unknown':True,'sealed_final_overlap':'unknown_not_opened'}
 write_json(ROOT/'data/msae_independent_measurement_v1/source_inventory.json',inv)
 return split

def endpoints():
 out={k:[] for k in ('localization','functional_reproducibility','collateral','counterfactual','baseline')}
 tasks=[(f,t) for f,ts in TASKS.items() for t in ts]
 for role in ('C1','C2'):
  for ck in ('raw','g4','g5','g6','g7'):
   for fam,t in tasks:
    for comp in ('assigned','nonassigned','joint','complement','residual'):
     for metric in ('recovery','leakage','selectivity'):
      out['localization'].append(f'{role}.{ck}.{fam}.{t}.{comp}.{metric}.L3')
 for fam in TASKS:
  for metric in ('recovery','leakage','selectivity'):
   out['functional_reproducibility'].append(f'g4_g5_g6.{fam}.{metric}.spread')
 for role in ('C1','C2'):
  for ck in ('g4','g5','g6','g7'):
   for t in TIER2:
    for metric in ('recovery','retention','leakage'):
     out['collateral'].append(f'{role}.{ck}.{t}.{metric}.L3')
 for ck in ('g4','g5','g6','g7'):
  for tr in ('neutral_prefix_shift','within_document_context_anchor','single_token_lexical_substitution','single_token_entity_substitution'):
   for ctrl in ('actual','matched_random','inactive_branch_sham','exact_noop','specificity','mapping'):
    out['counterfactual'].append(f'C2.{ck}.{tr}.{ctrl}.L3')
 for role in ('discovery','calibration','C1','C2'):
  for b in ('raw','projection_broad16_content8','projection_split8_8_content8','pca16_8','random16_8','ridge_position_residual','inlp_fixed16','shuffled','chance','K1_not_applicable','unregularized_not_applicable'):
   out['baseline'].append(f'{role}.{b}.registered')
 return out

def finalize()->dict[str,Any]:
 from msae_measurement_remediation_v1 import build_stage_a
 cal=ROOT/'data/atlas_measurement_v2_4/prepared/calibration/inference_units.jsonl'
 units=[json.loads(x) for x in cal.read_text().splitlines()]
 pairs=[json.loads(x) for x in (cal.parent/'pairs.jsonl').read_text().splitlines()]
 byid={u['unit_id']:u for u in units}
 main=[u for u in units if u['kind']=='main']; med=sorted(len(u['input_ids']) for u in main)[len(main)//2]
 def choose(name,xs,n=8):return sorted(xs,key=lambda x:(tuple_hash(PROTOCOL,name,x.get('unit_id',x.get('pair_id'))),x.get('unit_id',x.get('pair_id'))))[:n]
 chosen={
  'main_short':choose('main_short',[u for u in main if len(u['input_ids'])<=med]),
  'main_long':choose('main_long',[u for u in main if len(u['input_ids'])>med]),
 }
 for construct,sid in [('document_context_anchor','pair_context'),('entity_substitution','pair_entity')]:
  ps=choose(sid,[p for p in pairs if p['construct']==construct])
  chosen[sid]=[byid[f"pair:{p['pair_id']}:{side}"] for p in ps for side in ('source','target')]
 env={'schema_version':'msae_independent_environment_v1','python':subprocess.check_output(['.venv-atlas/bin/python','-c','import platform;print(platform.python_version())'],cwd=ROOT,text=True).strip(),'model_revision':'582159a2dfe3e712a8d47ae83dec95ae3bde8e7e','deterministic':True,'tf32':False,'dtype':'float16','cache_dtype':'float32'}
 write_json(ROOT/'data/msae_independent_measurement_v1/environment.json',env);envsha=sha_file(ROOT/'data/msae_independent_measurement_v1/environment.json')
 code_sha=sha_file(ROOT/'scripts/run_msae_independent_calibration_v1.py');srcsha=sha_file(cal);partition='atlas_measurement_v2_4:calibration'
 strata=[];frozen={'schema_version':'msae_independent_calibration_strata_v1','source_path':str(cal.relative_to(ROOT)),'source_sha256':srcsha,'strata':{}}
 for sid,us in chosen.items():
  rows=[r for u in us for r in u['row_ids']];inputs=[{'unit_id':u['unit_id'],'input_ids':u['input_ids'],'positions':u['positions'],'row_ids':u['row_ids']} for u in us]
  rowsha=sha_bytes(json.dumps(rows,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode())
  insha=sha_bytes(cbytes(inputs));meta={'stratum_id':sid,'source_role':'calibration','source_revision':srcsha,'partition':partition,'model_id':'EleutherAI/pythia-160m-deduped@582159a2dfe3e712a8d47ae83dec95ae3bde8e7e','checkpoint_id':'pythia160m-deduped-base','code_sha256':code_sha,'environment_sha256':envsha,'dtype':'float32','pooling_path':'hidden_states[3]:registered_first_subtoken_rows','row_ids_sha256':rowsha,'input_sha256':insha,'reference_evaluation_id':f'{sid}.reference','repeat_evaluation_ids':[f'{sid}.repeat{i}' for i in range(1,4)]}
  strata.append(meta);frozen['strata'][sid]={'units':us,'row_ids':rows,'input_sha256':insha,'alignment_valid':True,'selected_unit_or_pair_count':8}
 write_json(ROOT/'data/msae_independent_measurement_v1/calibration_strata.json',frozen)
 dep=sha_file(ROOT/'scripts/msae_measurement_v2.py');e=endpoints()
 ck=[]
 vals=[('g4',42,'c2e09c1b82eacd36c012cfe3b58f2d399f2a3fd557a2be7d47f180ada2c09a8f','00714ca209027d418156f65dda55b90e6f1887a75ef412acb43a61359d711e97'),('g5',43,'82e15a585103ce9d1366402e9f0d84606d2437e427e1acecd5f85fa69fdf2121','933120800d5861dddbe99f725c04467c0684bbd069b6d9f345d2b202a43003ef'),('g6',44,'30d070528818d4342525e5247f76340317dc2c4b8717fcfbc941e44d975bf32a','d4cd3ac52805f70bbcec60857a3c4afd6361248038a541f63a0cfcfe1b5b3e43')]
 for x,seed,runsha,cksha in vals:ck.append({'model_id':'pythia160m-deduped-L3-K2','training_run_id':f'k2_wave2_fast_{x}_L3_s{seed}_inc1e2','training_run_digest':runsha,'checkpoint_id':x,'checkpoint_sha256':cksha,'seed':seed})
 cfg={'schema_version':'msae_measurement_remediation_config_v1','protocol_id':PROTOCOL,'artifact_schema_version':'msae_measurement_remediation_artifact_v1','endpoint_schema_version':'msae_endpoint_evidence_v1','replay_bundle_schema_version':'msae_calibration_replay_bundle_v1','dependency':{'path':'scripts/msae_measurement_v2.py','sha256':dep},'replay':{'source_role':'calibration','source_revision':srcsha,'partition':partition,'strata':strata,'tolerance_ladder':[[5e-7,0.0],[5e-7,1e-6],[5e-7,5e-6],[1e-6,5e-6],[2e-6,5e-6],[5e-6,5e-6],[1e-5,5e-6],[2e-5,5e-6]],'safety_factor':2.0},'functional_reproducibility':{'minimum_checkpoints':3,'checkpoints':ck,'families':TASKS,'maximum_spread':{'recovery':0.05,'leakage':0.05,'selectivity':0.05}},'stages':{'A':{'purpose':'calibration_replay_candidate','required':['candidate_confirmation_source','immutable_source_revision','independent_grouping_provenance','label_support_audit','construct_inventory','counterfactual_template_specification','tolerance_ladder_frozen','dependency_attestation'],'optional':[]},'B':{'purpose':'confirmation_scoring_candidate','required':['calibration_replay','selected_replay_tolerance','cached_noop_hash_replay','canonical_pooling_qa','counterfactual_cache_alignment_qa'],'optional':[]},'C':{'purpose':'decision_review_candidate','required_by_category':e,'optional':[]}}}
 cp=ROOT/'configs/msae_independent_measurement_v1/protocol.json';write_json(cp,cfg);raw=cp.read_bytes();cfgsha=sha_bytes(raw)
 partition_obj=json.loads((ROOT/'data/msae_independent_measurement_v1/source_partition.json').read_text())
 history_path=ROOT/'reports/provenance/msae_independent_measurement_v1/history_overlap.json';history=json.loads(history_path.read_text()) if history_path.exists() else {'status':'ineligible','blocking_collisions':[]};arts={'candidate_confirmation_source':history_path if history_path.exists() else ROOT/'data/msae_independent_measurement_v1/source_inventory.json','immutable_source_revision':ROOT/'data/msae_independent_measurement_v1/source_inventory.json','independent_grouping_provenance':history_path if history_path.exists() else ROOT/'data/msae_independent_measurement_v1/source_partition.json','label_support_audit':ROOT/'data/msae_independent_measurement_v1/source_partition.json','construct_inventory':ROOT/'docs/rfc-msae-independent-measurement-v1.md','counterfactual_template_specification':ROOT/'docs/rfc-msae-independent-measurement-v1.md','tolerance_ladder_frozen':cp}
 ev={}
 for n,p in arts.items():
  independence=n in ('candidate_confirmation_source','independent_grouping_provenance');ok=(not independence) or history.get('status')=='eligible';ev[n]={'schema_version':'msae_endpoint_evidence_v1','protocol_config_sha256':cfgsha,'endpoint_name':n,'category':'stage_a','status':'eligible' if ok else 'ineligible','reasons':[] if ok else ['accessible_history_overlap_detected'],'evidence_artifact_sha256':sha_file(p),'observed_value':{'artifact_path':str(p.relative_to(ROOT)),'artifact_sha256':sha_file(p),'source_revision':partition_obj['source_revision'],'partition_sha256':partition_obj['partition_sha256'],'blocking_collision_count':len(history.get('blocking_collisions',[])) if independence else 0}}
 stage=build_stage_a(raw,cfgsha,ev);write_json(ROOT/'reports/provenance/msae_independent_measurement_v1/stage_a.json',stage)
 out={'schema_version':'msae_independent_freeze_v1','protocol_config_sha256':cfgsha,'stage_a_sha256':sha_bytes(cbytes(stage)),'stage_a_ready':stage['stage_ready'],'source_partition_sha256':partition_obj['partition_sha256'],'calibration_strata_sha256':sha_file(ROOT/'data/msae_independent_measurement_v1/calibration_strata.json'),'endpoint_counts':{k:len(v) for k,v in e.items()},'checkpoint_registry':ck}
 write_json(ROOT/'reports/provenance/msae_independent_measurement_v1/freeze.json',out);return out

def _start_tick(pid:int)->str:
 return Path(f'/proc/{pid}/stat').read_text().split()[21]
def worker(sock_path:str,run_root:str,gpu_uuid:str)->None:
 sock=socket.socket(socket.AF_UNIX,socket.SOCK_STREAM);sock.connect(sock_path)
 msg=cbytes({'pid':os.getpid(),'start_tick':_start_tick(os.getpid()),'pgid':os.getpgrp()});sock.sendall(len(msg).to_bytes(4,'big')+msg)
 _,anc,_,_=sock.recvmsg(1,socket.CMSG_LEN(array.array('i',[0]).itemsize));fds=[]
 for level,typ,data in anc:
  if level==socket.SOL_SOCKET and typ==socket.SCM_RIGHTS:
   a=array.array('i');a.frombytes(data[:len(data)-(len(data)%a.itemsize)]);fds.extend(a)
 if len(fds)!=1:raise RuntimeError('lease FD transfer failed')
 fd=fds[0];fcntl.flock(fd,fcntl.LOCK_EX|fcntl.LOCK_NB);os.set_inheritable(fd,True)
 env=os.environ.copy();env.update({'CUDA_VISIBLE_DEVICES':gpu_uuid,'MSAE_RUN_ROOT':str(ROOT/run_root),'MSAE_LEASE_FD':str(fd)})
 cmd=['timeout','--signal=TERM','--kill-after=60s','6h',str(ROOT/'.venv-atlas/bin/python'),str(ROOT/'scripts/run_msae_independent_calibration_v1.py'),'--run-root',run_root,'--gpu-uuid',gpu_uuid]
 os.execvpe(cmd[0],cmd,env)
def launch()->dict[str,Any]:
 run_rel='pilot_runs/20260820_msae_independent_measurement_v1_calibration';run=ROOT/run_rel
 if run.exists():raise RuntimeError('create-once run root already exists')
 q=subprocess.check_output(['nvidia-smi','--query-gpu=index,uuid,memory.used,utilization.gpu','--format=csv,noheader,nounits'],text=True)
 busy=subprocess.check_output(['nvidia-smi','--query-compute-apps=gpu_uuid,pid','--format=csv,noheader,nounits'],text=True).strip()
 busyids={x.split(',')[0].strip() for x in busy.splitlines() if x.strip()}
 cand=[]
 for line in q.splitlines():
  i,u,m,v=[x.strip() for x in line.split(',')];m=int(m);v=int(v)
  if u not in busyids and m<1024 and v<=5:cand.append((m,v,u,i))
 if not cand:raise RuntimeError('no idle GPU satisfies frozen rule')
 _,_,uuid,index=min(cand);lock=Path('/tmp')/f'msae-{uuid}.lock';fd=os.open(lock,os.O_RDWR|os.O_CREAT,0o600);fcntl.flock(fd,fcntl.LOCK_EX|fcntl.LOCK_NB);os.set_inheritable(fd,True)
 # Recheck while holding the UUID lock.
 q2=subprocess.check_output(['nvidia-smi','--id='+index,'--query-gpu=uuid,memory.used,utilization.gpu','--format=csv,noheader,nounits'],text=True).strip().split(',')
 if q2[0].strip()!=uuid or int(q2[1])>=1024 or int(q2[2])>5:raise RuntimeError('GPU drift after lock')
 run.mkdir(parents=True);sockpath=str(run/'lease.sock');srv=socket.socket(socket.AF_UNIX,socket.SOCK_STREAM);srv.bind(sockpath);srv.listen(1);srv.settimeout(10)
 session='msae_independent_calibration_v1';
 if subprocess.run(['tmux','has-session','-t',session],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL).returncode==0:raise RuntimeError('tmux session exists')
 cmd=f"exec {ROOT/'.venv-atlas/bin/python'} {ROOT/'scripts/msae_independent_measurement_v1.py'} worker --socket {sockpath} --run-root {run_rel} --gpu-uuid {uuid} >> {run/'worker.log'} 2>&1"
 subprocess.check_call(['tmux','new-session','-d','-s',session,cmd]);conn,_=srv.accept();n=int.from_bytes(conn.recv(4),'big');hello=json.loads(conn.recv(n));rfd,wfd=os.pipe()
 pid=os.fork()
 if pid==0:
  os.close(rfd)
  try:
   conn.sendmsg([b'L'],[(socket.SOL_SOCKET,socket.SCM_RIGHTS,array.array('i',[fd]))])
   rec={'schema_version':'msae_gpu_lease_v1','gpu_uuid':uuid,'gpu_index':int(index),'broker_pid':os.getpid(),'broker_start_tick':_start_tick(os.getpid()),'worker_pid':hello['pid'],'worker_start_tick':hello['start_tick'],'worker_pgid':hello['pgid'],'lock_path':str(lock),'config_sha256':sha_file(ROOT/'configs/msae_independent_measurement_v1/protocol.json')}
   write_json(run/'lock_acquired.json',rec);os.write(wfd,b'1')
   while True:
    try:os.kill(int(hello['pid']),0);time.sleep(2)
    except ProcessLookupError:break
  finally:os._exit(0)
 os.close(wfd);os.read(rfd,1);os.close(rfd);conn.close();srv.close();os.close(fd)
 pane=int(subprocess.check_output(['tmux','display-message','-p','-t',session,'#{pane_pid}'],text=True).strip())
 out={'schema_version':'msae_independent_launch_v1','session':session,'run_root':run_rel,'gpu_uuid':uuid,'gpu_index':int(index),'pane_pid':pane,'worker_pid':hello['pid'],'broker_pid':pid,'status':'handed_off_no_result_wait'}
 write_json(run/'launch.json',out);print(json.dumps(out,indent=2));return out

def main():
 ap=argparse.ArgumentParser();sub=ap.add_subparsers(dest='command',required=True);sub.add_parser('prepare');sub.add_parser('finalize');sub.add_parser('launch');w=sub.add_parser('worker');w.add_argument('--socket',required=True);w.add_argument('--run-root',required=True);w.add_argument('--gpu-uuid',required=True);a=ap.parse_args()
 if a.command=='prepare': print(json.dumps(prepare(),indent=2)[:2000])
 elif a.command=='finalize': print(json.dumps(finalize(),indent=2))
 elif a.command=='launch':launch()
 else:worker(a.socket,a.run_root,a.gpu_uuid)
if __name__=='__main__':main()
