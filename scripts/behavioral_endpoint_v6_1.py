#!/usr/bin/env python3
"""Prospective endpoint-only retrieval/agreement behavioral validity study v6."""
from __future__ import annotations
import argparse,ast,hashlib,heapq,json,math,os,re,time,traceback
from collections import Counter
from pathlib import Path
from typing import Any,Mapping,Sequence
import numpy as np
import torch
import joint_controllability_benchmark_v3 as core
import joint_controllability_assay_v5 as v5
ROOT=Path(__file__).resolve().parents[1];SCRIPT=Path(__file__).resolve();DEFAULT=ROOT/'configs/behavioral_endpoint_v6_1/run.json';PLAN=ROOT/'PLAN_BEHAVIORAL_ENDPOINT_V6_1.md';TEST=ROOT/'tests/test_behavioral_endpoint_v6_1.py';LAUNCHER=ROOT/'scripts/launch_behavioral_endpoint_v6_1_tmux.sh'
def native(x:Any)->Any:
 if isinstance(x,np.generic):return x.item()
 if isinstance(x,dict):return {str(k):native(v) for k,v in x.items()}
 if isinstance(x,(list,tuple)):return [native(v) for v in x]
 return x
def canon(x:Any)->bytes:return json.dumps(native(x),sort_keys=True,separators=(',',':'),allow_nan=False).encode()
def loadj(p:Path)->Any:return json.loads(p.read_text())
def sha(p:Path)->str:
 h=hashlib.sha256()
 with p.open('rb') as f:
  for c in iter(lambda:f.read(8<<20),b''):h.update(c)
 return h.hexdigest()
def stable(seed:int,*parts:Any)->int:return int.from_bytes(hashlib.sha256('|'.join(map(str,(seed,)+parts)).encode()).digest()[:8],'little')
def exjson(p:Path,x:Any)->None:
 p.parent.mkdir(parents=True,exist_ok=True);tmp=p.with_name(p.name+f'.tmp.{os.getpid()}.{time.time_ns()}');fd=os.open(tmp,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
 try:
  with os.fdopen(fd,'wb') as f:f.write(canon(x)+b'\n');f.flush();os.fsync(f.fileno())
  os.link(tmp,p)
 finally:tmp.unlink(missing_ok=True)
def publish_failure(p:Path,x:Any)->None:
 try:exjson(p,x)
 except FileExistsError:pass
def writejl(p:Path,rows:Sequence[Mapping[str,Any]])->None:
 p.parent.mkdir(parents=True,exist_ok=True);fd=os.open(p,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
 with os.fdopen(fd,'w') as f:
  for r in rows:f.write(canon(dict(r)).decode()+'\n')
def readjl(p:Path)->list[dict[str,Any]]:return [json.loads(x) for x in p.read_text().splitlines() if x]
def require_offline()->None:
 for n in ('HF_DATASETS_OFFLINE','HF_HUB_OFFLINE','TRANSFORMERS_OFFLINE'):
  if os.environ.get(n)!='1':raise RuntimeError(f'offline environment required {n}=1')
def preservation_verify(cfg:Mapping[str,Any])->None:
 m=loadj(ROOT/cfg['preservation']['v5_manifest'])
 listed={r['path'] for r in m['files']};vf=loadj(ROOT/cfg['preservation']['v5_freeze'])
 for r in m['files']:
  p=ROOT/r['path']
  if not p.is_file() or p.stat().st_size!=r['bytes'] or sha(p)!=r['sha256']:raise RuntimeError(f"v5 preservation drift {r['path']}")
 for r in vf['candidate_inventory']:
  p=ROOT/r['path']
  if r['path'] not in listed or not p.is_file() or p.stat().st_size!=r['bytes'] or sha(p)!=r['sha256']:raise RuntimeError(f"nested v5 freeze drift {r['path']}")
 conf=ROOT/'results/joint_controllability_assay_v5_20260808/confirmation'
 for model in ('gpt2','pythia160','gemma2'):
  files=sorted(p.name for p in (conf/model).iterdir() if p.is_file())
  if files!=['BLOCKED.json']:raise RuntimeError(f'v5 confirmation opened/drifted {model}:{files}')
 if sha(ROOT/cfg['preservation']['architecture_closure'])!=cfg['preservation']['architecture_closure_sha256']:raise RuntimeError('closure drift')
def normalize(text:str)->str:return ' '.join(re.findall(r'\S+',text)).strip()
def th(text:str)->str:return hashlib.sha256(normalize(text).lower().encode()).hexdigest()
def in_ranges(i:int,ranges:Sequence[Sequence[int]])->bool:return any(int(a)<=i<=int(b) for a,b in ranges)
def ranged_lines(path:Path,ranges:Sequence[Sequence[int]]):
 with path.open('rb') as f:
  for i,line in enumerate(f,1):
   if in_ranges(i,ranges):yield i,line.rstrip(b'\r\n')
def development_projection(cfg:Mapping[str,Any])->tuple[list[dict[str,Any]],dict[str,set[str]]]:
 rows=[]
 for i,line in ranged_lines(ROOT/cfg['panel']['v5_rows'],cfg['panel']['v5_development_line_ranges']):
  r=json.loads(line)
  if r['split']!='development':raise RuntimeError(f'dev projection split drift line {i}')
  source={'WIKITEXT_FRESH':'WIKITEXT_DEV_OPENED','AGNEWS_FRESH':'AGNEWS_DEV_OPENED'}[r['source']];rows.append({**r,'source':source,'original_v5_line':i})
 if len(rows)!=384:raise RuntimeError(f'dev projection rows {len(rows)}')
 sealed={'content_hash':set(),'window_hash':set()}
 for i,line in ranged_lines(ROOT/cfg['panel']['v5_accepted'],cfg['panel']['v5_confirmation_line_ranges']):
  for name in sealed:
   m=re.search(rb'"'+name.encode()+rb'":"([0-9a-f]{64})"',line)
   if not m:raise RuntimeError(f'sealed hash absent {name}/{i}')
   sealed[name].add(m.group(1).decode('ascii'))
 if any(len(v)!=384 for v in sealed.values()):raise RuntimeError('sealed v5 confirmation hash count drift')
 return rows,sealed
def predecessor_exclusions(cfg:Mapping[str,Any])->tuple[dict[str,set[str]],list[dict[str,Any]]]:
 out={'document_id':set(),'content_hash':set(),'window_hash':set()};audit=[]
 for spec in cfg['panel']['opened_predecessor_rows']:
  p=ROOT/spec['path'];rows=readjl(p);before={k:len(v) for k,v in out.items()}
  for r in rows:
   for field in spec['id_fields']:
    value=str(r.get(field,''))
    if value:out['document_id'].add(value)
    if re.fullmatch(r'[0-9a-f]{64}',value):out['content_hash'].add(value)
   for field in spec['text_fields']:
    words=re.findall(r'\S+',normalize(str(r.get(field,''))))
    for i in range(max(0,len(words)-31)):out['window_hash'].add(th(' '.join(words[i:i+32])))
  audit.append({'path':spec['path'],'sha256':sha(p),'rows':len(rows),'new_exclusions':{k:len(out[k])-before[k] for k in out}})
 return out,audit
def confirmation_documents(cfg:Mapping[str,Any],excluded:dict[str,set[str]],rejection_path:Path)->tuple[dict[str,list[dict[str,Any]]],list[dict[str,Any]]]:
 require_offline();from datasets import load_dataset
 out={};audits=[];used_id=set(excluded['document_id']);used_content=set(excluded['content_hash']);used_window=set(excluded['window_hash']);rejection_path.parent.mkdir(parents=True,exist_ok=True);fd=os.open(rejection_path,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
 with os.fdopen(fd,'w') as rejected:
  for spec in cfg['panel']['confirmation_corpora']:
   ds=load_dataset(spec['dataset'],spec['config'],split=spec['split'],revision=spec['revision'])
   if ds._fingerprint!=spec['fingerprint']:raise RuntimeError(f"fingerprint drift {spec['key']}:{ds._fingerprint}")
   prior_id=used_id.copy();prior_content=used_content.copy();prior_window=used_window.copy();heap=[];short=overlap=eligible=0
   def record(idx:int,row:Mapping[str,Any])->dict[str,Any]|None:
    text=spec['separator'].join(str(row.get(f,'')) for f in spec['fields']);words=re.findall(r'\S+',normalize(text))
    if len(words)<cfg['panel']['filler_words']:return None
    ch=th(' '.join(words));start=stable(cfg['seed'],spec['dataset'],spec['split'],idx,'window')%(len(words)-cfg['panel']['filler_words']+1);filler=' '.join(words[start:start+cfg['panel']['filler_words']]);wh=th(filler);order=int(hashlib.sha256(f"{cfg['seed']}|{spec['dataset']}|{spec['split']}|{idx}".encode()).hexdigest(),16)
    return {'document_id':f"{spec['key']}:{idx}",'source':spec['key'],'content_hash':ch,'window_hash':wh,'filler':filler,'row_index':idx,'order_sha256':f'{order:064x}'}
   for idx,row in enumerate(ds):
    rec=record(idx,row)
    if rec is None:short+=1;continue
    eligible+=1
    if rec['document_id'] in prior_id or rec['content_hash'] in prior_content or rec['window_hash'] in prior_window:overlap+=1;continue
    order=int(rec['order_sha256'],16);item=(-order,idx,rec)
    if len(heap)<512:heapq.heappush(heap,item)
    elif order < -heap[0][0]:heapq.heapreplace(heap,item)
   candidates=[x[2] for x in sorted(heap,key=lambda z:-z[0])];chosen=[]
   for r in candidates:
    if r['document_id'] in used_id or r['content_hash'] in used_content or r['window_hash'] in used_window:continue
    chosen.append(r);used_id.add(r['document_id']);used_content.add(r['content_hash']);used_window.add(r['window_hash'])
    if len(chosen)==192:break
   if len(chosen)!=192:raise RuntimeError(f"confirmation support {spec['key']}:{len(chosen)}")
   selected={r['row_index'] for r in chosen};rejected_rows=short_rejected=0;source_ids=set();source_content=set();source_windows=set()
   for idx,row in enumerate(ds):
    rec=record(idx,row)
    if rec is None:
     text=spec['separator'].join(str(row.get(f,'')) for f in spec['fields']);word_count=len(re.findall(r'\S+',normalize(text)));order=hashlib.sha256(f"{cfg['seed']}|{spec['dataset']}|{spec['split']}|{idx}".encode()).hexdigest();compact={'document_id':f"{spec['key']}:{idx}",'source':spec['key'],'content_hash':th(text),'window_hash':None,'row_index':idx,'order_sha256':order,'word_count':word_count,'reason':'MINIMUM_LENGTH_INELIGIBLE'};rejected.write(canon(compact).decode()+'\n');rejected_rows+=1;short_rejected+=1;continue
    source_ids.add(rec['document_id']);source_content.add(rec['content_hash']);source_windows.add(rec['window_hash'])
    if idx in selected:continue
    reason='PREDECESSOR_OR_EARLIER_SOURCE_OVERLAP' if rec['document_id'] in prior_id or rec['content_hash'] in prior_content or rec['window_hash'] in prior_window else 'BELOW_DETERMINISTIC_SELECTION_CUTOFF_OR_DUPLICATE'
    compact={k:rec[k] for k in ('document_id','source','content_hash','window_hash','row_index','order_sha256')}|{'reason':reason};rejected.write(canon(compact).decode()+'\n');rejected_rows+=1
   used_id.update(source_ids);used_content.update(source_content);used_window.update(source_windows);out[spec['key']]=chosen;audits.append({'source':spec['key'],'dataset_rows':len(ds),'minimum_length_ineligible':short,'minimum_length_rejection_records':short_rejected,'length_eligible':eligible,'preselection_overlap':overlap,'accepted':len(chosen),'rejected_records':rejected_rows,'selection_heap':512,'all_length_eligible_hashes_excluded_from_later_sources':True})
  rejected.flush();os.fsync(rejected.fileno())
 return out,audits
def _tok_ids(tok:Any,text:str)->list[int]:return list(tok(text,add_special_tokens=False)['input_ids'])
def table_text(keys:list[str],mapping:list[int],values:list[str])->str:return 'Table: '+'; '.join(f'{k}={values[mapping[i]]}' for i,k in enumerate(keys))+'.'
def retrieval_conditions(keys:list[str],q:int,v:int,values:list[str],null_table:str)->tuple[list[str],list[int],list[str]]:
 def mapping(w:int)->list[int]:return [(w+i-q)%4 for i in range(4)]
 base=mapping(v);wrong=[x for x in range(4) if x!=v];tables=[table_text(keys,base,values)];correct=[v];names=['match']
 for w in wrong:tables.append(table_text(keys,mapping(w),values));correct.append(w);names.append(f'counterfactual_{w}')
 others=[i for i in range(4) if i!=q];assigned=[base[i] for i in others]
 for shift in (1,2):
  m=base.copy()
  for j,i in enumerate(others):m[i]=assigned[(j+shift)%3]
  tables.append(table_text(keys,m,values));correct.append(v);names.append(f'sham_{shift}')
 tables.append(null_table);correct.append(4);names.append('no_binding');return tables,correct,names
def sanitize_retrieval_filler(text:str,forbidden:set[str])->tuple[str,int]:
 pattern=re.compile(r'(?<![A-Za-z])('+('|'.join(sorted(map(re.escape,forbidden),key=len,reverse=True)))+r')(?![A-Za-z])',re.IGNORECASE)
 return pattern.sub('neutral',text),len(pattern.findall(text))
def agreement_assignments(seed:int,stage:str,t:int,set_idx:int)->dict[str,list[int]]:
 del seed;offset=0 if stage=='development' else 1;attr=[];lexs=[];lexa=[];verb=[]
 for subj in range(4):
  for sn in range(2):
   for an in range(2):
    a=(subj+1+((2*sn+an+t+set_idx+offset)%3))%4;attr.append(a);lexs.append((subj+1+((sn+2*an+2*t+set_idx+offset)%3))%4);lexa.append((a+1+((2*sn+an+t+2*set_idx+offset)%3))%4);verb.append((subj+2*sn+an+t+set_idx+offset)%4)
 return {'attractor':attr,'lexical_subject':lexs,'lexical_attractor':lexa,'verb':verb}
def agreement_design_audit(seed:int,stage:str,templates:int)->dict[str,Any]:
 rows=[]
 for t in range(templates):
  for st in range(4):
   a=agreement_assignments(seed,stage,t,st)
   for subj in range(4):
    for sn in range(2):
     for an in range(2):
      j=subj*4+sn*2+an;rows.append((st,subj,a['attractor'][j],a['lexical_subject'][j],a['lexical_attractor'][j],sn,an,t,a['verb'][j]))
 levels=[4,4,4,4,4,2,2,templates,4];X=[]
 for r in rows:X.append([1]+[r[k]==j for k,n in enumerate(levels) for j in range(1,n)])
 X=np.asarray(X,float);sv=np.linalg.svd(X,compute_uv=False);rank=int(np.linalg.matrix_rank(X,tol=1e-8));checks=[]
 for t in range(templates):
  for st in range(4):checks.append(Counter(r[8] for r in rows if r[7]==t and r[0]==st))
 for factor in (1,5,6):
  for value in sorted({r[factor] for r in rows}):checks.append(Counter(r[8] for r in rows if r[factor]==value))
 balanced=all(set(c.keys())==set(range(4)) and len(set(c.values()))==1 for c in checks)
 return {'rows':len(rows),'columns':X.shape[1],'rank':rank,'smallest_singular_value':float(sv[-1]),'full_rank':rank==X.shape[1],'cyclic_latin_incidence_balanced':balanced,'incidence_checks':len(checks)}
def assigned_doc(docs:list[dict[str,Any]],t:int,set_idx:int,j:int,templates:int)->dict[str,Any]:
 if len(docs)!=192:raise RuntimeError('document pool must be 192')
 block=t%3;return docs[set_idx*48+block*16+j]
def prepare(config:Path,output:Path|None=None)->None:
 cfg=loadj(config);preservation_verify(cfg);require_offline();root=output or ROOT/cfg['runtime']['prepared_root']
 if root.exists():raise FileExistsError(root)
 root.mkdir(parents=True);toks=core.load_tokenizers(cfg);dev,sealed=development_projection(cfg);prior,prior_audit=predecessor_exclusions(cfg)
 dev_by={s:sorted([r for r in dev if r['source']==s],key=lambda r:r['document_id']) for s in cfg['panel']['development_sources']}
 exclusions={'document_id':set(prior['document_id'])|{r['document_id'] for r in dev},'content_hash':set(prior['content_hash'])|set(sealed['content_hash'])|{r['content_hash'] for r in dev},'window_hash':set(prior['window_hash'])|set(sealed['window_hash'])|{r['window_hash'] for r in dev}}
 conf,conf_audit=confirmation_documents(cfg,exclusions,root/'CONFIRMATION_REJECTIONS.jsonl')
 writejl(root/'V5_DEVELOPMENT_PROJECTION.jsonl',dev);exjson(root/'SEALED_V5_CONFIRMATION_HASHES.json',{k:sorted(v) for k,v in sealed.items()})
 accepted_conf=[r for s in cfg['panel']['confirmation_sources'] for r in conf[s]];writejl(root/'CONFIRMATION_DOCUMENTS.jsonl',accepted_conf)
 per={(e,m['key']):[] for e in cfg['endpoints'] for m in cfg['models']};raw={'retrieval':[],'agreement':[]}
 for stage,sources,nt in [('development',cfg['panel']['development_sources'],cfg['panel']['development_templates']),('confirmation',cfg['panel']['confirmation_sources'],cfg['panel']['confirmation_templates'])]:
  for source in sources:
   docs=dev_by[source] if stage=='development' else conf[source]
   # Retrieval
   rcfg=cfg['retrieval'];keysets=rcfg[f'{stage}_key_sets'];templates=rcfg[f'{stage}_templates'];values=rcfg['ordinary_values'];candidates=values+[rcfg['null_value']];forbidden={x.lower() for ks in keysets for x in ks}|{x.lower() for x in candidates}
   if rcfg['filler_sanitization_replacement']!='neutral' or rcfg['no_binding_query'].lower() in forbidden:raise RuntimeError('retrieval sanitation config drift')
   for t,template in enumerate(templates):
    for st,keys in enumerate(keysets):
     for q in range(4):
      for v in range(4):
       j=q*4+v;doc=assigned_doc(docs,t,st,j,nt);null_table=' '.join(['unavailable']*int(rcfg[f'{stage}_no_binding_scaffold_words'][t]));tables,correct,names=retrieval_conditions(keys,q,v,values,null_table);safe_filler,replacements=sanitize_retrieval_filler(doc['filler'],forbidden);texts=[template.format(filler=safe_filler,table=tb,query=(keys[q] if i<6 else rcfg['no_binding_query'])) for i,tb in enumerate(tables)];_,no_binding_leaks=sanitize_retrieval_filler(texts[-1],forbidden)
       if no_binding_leaks:raise RuntimeError(f'no-binding registered-string leakage {stage}/{source}/{t}/{st}/{q}/{v}')
       cid=f'retrieval:{stage}:{source}:t{t}:s{st}:q{q}:v{v}:{doc["document_id"]}';base={'endpoint':'retrieval','stage':stage,'source':source,'template_index':t,'set_index':st,'component_id':cid,'component_block':doc['document_id'],'document_id':doc['document_id'],'query_index':q,'value_index':v,'query_key':keys[q],'keys':keys,'candidate_words':candidates,'retrieval_filler':safe_filler,'filler_sanitization_count':replacements,'condition_names':names,'condition_tables':tables,'condition_prompts':texts,'correct_candidate_indices':correct}
       raw['retrieval'].append(base)
       for model,tok in toks.items():
        prompts=[_tok_ids(tok,x) for x in texts];cand=[_tok_ids(tok,' '+x) for x in candidates];bos=[tok.bos_token_id] if tok.bos_token_id is not None else []
        if len({len(x) for x in prompts})!=1 or any(len(x)!=1 for x in cand) or len(bos+prompts[0])+1>cfg['runtime']['maximum_length']:raise RuntimeError(f'retrieval token gate {stage}/{source}/{t}/{st}/{q}/{v}/{model}:{[len(x) for x in prompts]}/{cand}')
        enc={f'condition_{i}_prompt_ids':bos+x for i,x in enumerate(prompts)}|{'candidate_ids':[x[0] for x in cand],'continuation_ids':[cand[v][0]],'target_id':cand[v][0],'contrast_id':cand[(v+1)%4][0]};per[('retrieval',model)].append(base|enc)
   # Agreement
   acfg=cfg['agreement'];vocabs=acfg[f'{stage}_vocab_sets'];verbs=acfg[f'{stage}_verb_pairs'];templates=acfg[f'{stage}_templates']
   for t,construction_template in enumerate(templates):
    for st,vocab in enumerate(vocabs):
     for subj in range(4):
      for sn in range(2):
       for an in range(2):
        j=subj*4+sn*2+an;doc=assigned_doc(docs,t,st,j,nt);a=agreement_assignments(cfg['seed'],stage,t,st);attr=a['attractor'][j];lexs=a['lexical_subject'][j];lexa=a['lexical_attractor'][j];verb_i=a['verb'][j];pair=verbs[verb_i];target=pair[sn];contrast=pair[1-sn]
        surfaces=[(vocab[subj][sn],vocab[attr][an]),(vocab[subj][1-sn],vocab[attr][an]),(vocab[subj][sn],vocab[attr][1-an]),(vocab[lexs][sn],vocab[lexa][an])];texts=[acfg['prompt_template'].format(filler=doc['filler'],construction=construction_template.format(subject=a,attractor=b)) for a,b in surfaces];cid=f'agreement:{stage}:{source}:t{t}:s{st}:n{subj}:sn{sn}:an{an}:{doc["document_id"]}';base={'endpoint':'agreement','stage':stage,'source':source,'template_index':t,'set_index':st,'component_id':cid,'component_block':doc['document_id'],'document_id':doc['document_id'],'subject_lemma_index':subj,'attractor_lemma_index':attr,'lexical_subject_index':lexs,'lexical_attractor_index':lexa,'subject_number':sn,'attractor_number':an,'verb_pair_index':verb_i,'target_word':target,'contrast_word':contrast,'condition_surfaces':surfaces,'condition_prompts':texts,'condition_names':['original','subject_flip','attractor_flip','lexical_sham']};raw['agreement'].append(base)
        for model,tok in toks.items():
         prompts=[_tok_ids(tok,x) for x in texts];tar=_tok_ids(tok,' '+target);con=_tok_ids(tok,' '+contrast);bos=[tok.bos_token_id] if tok.bos_token_id is not None else []
         if len({len(x) for x in prompts})!=1 or len(tar)!=1 or len(con)!=1 or tar==con or len(bos+prompts[0])+1>cfg['runtime']['maximum_length']:raise RuntimeError(f'agreement token gate {stage}/{source}/{t}/{st}/{subj}/{sn}/{an}/{model}:{[len(x) for x in prompts]}/{tar}/{con}')
         enc={f'condition_{i}_prompt_ids':bos+x for i,x in enumerate(prompts)}|{'continuation_ids':tar,'target_id':tar[0],'contrast_id':con[0]};per[('agreement',model)].append(base|enc)
 for e,rows in raw.items():writejl(root/f'{e}_rows.jsonl',rows)
 for (e,m),rows in per.items():writejl(root/f'{e}_{m}.jsonl',rows)
 # audits
 counts={e:Counter((r['stage'],r['source'],r['template_index']) for r in rows) for e,rows in raw.items()}
 if any(set(c.values())!={64} for c in counts.values()):raise RuntimeError(f'panel count failure {counts}')
 dev_ids={r['document_id'] for r in dev};conf_ids={r['document_id'] for r in accepted_conf}
 if dev_ids&conf_ids or len(conf_ids)!=384:raise RuntimeError('development/confirmation ID disjointness failure')
 audit={'schema_version':'behavioral_endpoint_v6_prescore','selection_firewall':'LABEL_TOKENIZER_ONLY_NO_MODEL_FORWARD','rows':{e:len(x) for e,x in raw.items()},'development_projection_rows':len(dev),'sealed_v5_confirmation_hashes':{k:len(v) for k,v in sealed.items()},'predecessor_exclusions':prior_audit,'confirmation_selection':conf_audit,'confirmation_documents':len(accepted_conf),'zero_dev_confirmation_id_overlap':True,'counts':{e:{str(k):v for k,v in sorted(c.items())} for e,c in counts.items()},'agreement_design':{'development':agreement_design_audit(cfg['seed'],'development',6),'confirmation':agreement_design_audit(cfg['seed'],'confirmation',3)},'source_fingerprints':{x['key']:x['fingerprint'] for x in cfg['panel']['confirmation_corpora']},'files':{p.name:sha(p) for p in sorted(root.glob('*.jsonl'))}|{'SEALED_V5_CONFIRMATION_HASHES.json':sha(root/'SEALED_V5_CONFIRMATION_HASHES.json')}}
 if any(not x['full_rank'] or not x['cyclic_latin_incidence_balanced'] for x in audit['agreement_design'].values()):raise RuntimeError(f"agreement design failure {audit['agreement_design']}")
 exjson(root/'PRESCORE.json',audit);print(json.dumps(audit,indent=2))
def verify_prepared(cfg:Mapping[str,Any])->None:
 root=ROOT/cfg['runtime']['prepared_root'];m=loadj(root/'PRESCORE.json')
 if m['selection_firewall']!='LABEL_TOKENIZER_ONLY_NO_MODEL_FORWARD' or not m['zero_dev_confirmation_id_overlap']:raise RuntimeError('prescore semantic drift')
 for n,d in m['files'].items():
  if sha(root/n)!=d:raise RuntimeError(f'prepared drift {n}')
def cache_payload(cfg:Mapping[str,Any])->dict[str,Any]:
 require_offline();from huggingface_hub import snapshot_download
 records=[]
 for m in cfg['models']:
  snap=Path(snapshot_download(m['name'],revision=m['revision'],local_files_only=True));records.append({'model':m['key'],'revision':m['revision'],'snapshot':str(snap),'files':v5.cached_asset_records(snap)})
 return {'schema_version':'behavioral_endpoint_v6_cache','status':'PASS','models':records}
def cache_preflight(config:Path)->None:
 cfg=loadj(config);payload=cache_payload(cfg);p=ROOT/cfg['runtime']['cache_attestation']
 if p.exists():
  if loadj(p)!=payload:raise RuntimeError('cache drift')
 else:exjson(p,payload)
 print(json.dumps(payload,indent=2))
def recovery_verify(config:Path,cfg:Mapping[str,Any])->dict[str,Any]:
 r=cfg.get('recovery',{})
 if r.get('type')!='DEPENDENCY_CLOSURE_ONLY_NO_SCIENTIFIC_CHANGE' or r.get('new_model_forwards_before_recovery') is not False or r.get('scientific_protocol_changed') is not False:raise RuntimeError('recovery contract drift')
 old_freeze=ROOT/r['invalidated_v6_freeze'];old_review=ROOT/r['invalidated_v6_review']
 if sha(old_freeze)!=r['invalidated_v6_freeze_sha256'] or sha(old_review)!=r['invalidated_v6_review_sha256']:raise RuntimeError('invalidated-v6 provenance drift')
 if old_review.read_text().splitlines()[0]!='VERDICT: BLOCK':raise RuntimeError('invalidated v6 review is not BLOCK')
 prior=loadj(old_freeze)
 for rec in prior['candidate_inventory']:
  p=ROOT/rec['path']
  if not p.is_file() or p.stat().st_size!=rec['bytes'] or sha(p)!=rec['sha256']:raise RuntimeError(f"invalidated-v6 inventory drift: {rec['path']}")
 # Scientific configuration must be byte-for-byte equivalent after removing only
 # recovery provenance and the paths/schema that isolate this successor.
 old_config=loadj(ROOT/'configs/behavioral_endpoint_v6/run.json');new_config=json.loads(json.dumps(cfg))
 old_config['schema_version']=new_config['schema_version']='VERSIONED_RECOVERY_CONFIG'
 old_config['namespace']=new_config['namespace']='VERSIONED_RECOVERY_NAMESPACE'
 new_config.pop('recovery',None)
 for key in ('cache_attestation','candidate_review','freeze','output_root','provenance_root','tmux_prefix'):
  old_config['runtime'][key]=new_config['runtime'][key]='VERSIONED_RECOVERY_PATH'
 if old_config!=new_config:raise RuntimeError('scientific config changed from invalidated v6')
 # Compare every non-lifecycle function AST against v6. Lifecycle differences
 # are the only permitted code changes in this dependency-closure recovery.
 excluded={'recovery_verify','local_dependency_closure','candidate_files','inventory','preflight','freeze','verify_freeze','main'}
 def functions(path:Path)->dict[str,str]:
  tree=ast.parse(path.read_text());return {n.name:ast.dump(n,include_attributes=False) for n in tree.body if isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef)) and n.name not in excluded}
 if functions(ROOT/'scripts/behavioral_endpoint_v6.py')!=functions(SCRIPT):raise RuntimeError('scientific implementation changed from invalidated v6')
 return prior
def local_dependency_closure(entrypoints:Sequence[Path])->list[Path]:
 """Return recursive imports that resolve to project-local scripts/*.py files."""
 scripts=ROOT/'scripts';pending=[p.resolve() for p in entrypoints];seen:set[Path]=set()
 while pending:
  path=pending.pop()
  if path in seen:continue
  if not path.is_file():raise RuntimeError(f'local dependency absent {path}')
  seen.add(path)
  for node in ast.walk(ast.parse(path.read_text())):
   names=[]
   if isinstance(node,ast.Import):names=[x.name.split('.')[0] for x in node.names]
   elif isinstance(node,ast.ImportFrom) and node.level==0 and node.module:names=[node.module.split('.')[0]]
   for name in names:
    candidate=(scripts/f'{name}.py').resolve()
    if candidate.is_file() and candidate not in seen:pending.append(candidate)
 return sorted(seen)
def candidate_files(config:Path,cfg:Mapping[str,Any])->list[Path]:
 recovery_verify(config,cfg);p=ROOT/cfg['runtime']['prepared_root'];old=loadj(ROOT/cfg['recovery']['invalidated_v6_freeze'])
 paths=[ROOT/x['path'] for x in old['candidate_inventory']]
 paths += [ROOT/cfg['recovery']['invalidated_v6_freeze'],ROOT/cfg['recovery']['invalidated_v6_review'],config.resolve(),PLAN,SCRIPT,TEST,LAUNCHER,ROOT/'scripts/analyze_behavioral_endpoint_v5_templates.py',ROOT/cfg['preservation']['v5_manifest'],ROOT/cfg['preservation']['v5_freeze'],ROOT/cfg['preservation']['v5_development_gate'],ROOT/cfg['preservation']['v5_final'],ROOT/cfg['preservation']['v5_analysis'],ROOT/cfg['runtime']['cache_attestation'],ROOT/'reports/behavioral_endpoint_v5_analysis/v1/report.md',ROOT/'reports/adversarial/behavioral_endpoint_v6_candidate_review_block1.md',ROOT/'reports/provenance/behavioral_endpoint_v6_candidate/deterministic_prepare.json',p/'PRESCORE.json',p/'SEALED_V5_CONFIRMATION_HASHES.json',p/'V5_DEVELOPMENT_PROJECTION.jsonl',p/'CONFIRMATION_DOCUMENTS.jsonl',p/'CONFIRMATION_REJECTIONS.jsonl']
 deps=local_dependency_closure([SCRIPT,ROOT/'scripts/behavioral_endpoint_v6.py',ROOT/'scripts/joint_controllability_benchmark_v3.py',ROOT/'scripts/joint_controllability_assay_v5.py'])
 paths += deps
 expected={ROOT/x for x in cfg['recovery']['added_transitive_dependencies']}
 if not expected.issubset(set(deps)):raise RuntimeError('declared transitive dependency absent from computed closure')
 paths += [ROOT/x['path'] for x in cfg['panel']['opened_predecessor_rows']]
 paths += [p/f'{e}_rows.jsonl' for e in cfg['endpoints']]+[p/f'{e}_{m["key"]}.jsonl' for e in cfg['endpoints'] for m in cfg['models']]
 if cfg['runtime'].get('candidate_review'):paths.append(ROOT/cfg['runtime']['candidate_review'])
 return sorted(set(paths))
def inventory(config:Path,cfg:Mapping[str,Any])->list[dict[str,Any]]:
 out=[]
 for p in candidate_files(config,cfg):
  if not p.is_file():raise RuntimeError(f'candidate absent {p}')
  out.append({'path':p.relative_to(ROOT).as_posix(),'bytes':p.stat().st_size,'sha256':sha(p)})
 return sorted(out,key=lambda x:x['path'])
def family_check(cfg:Mapping[str,Any])->None:
 keys=[x['key'] for x in cfg['models']];fam=[x['family'] for x in cfg['models']]
 if len(set(keys))!=len(keys) or len(set(fam))!=len(fam) or set(keys)!={'gpt2','pythia160','gemma2'}:raise RuntimeError('checkpoint/family panel drift')
def preflight(config:Path)->None:
 cfg=loadj(config);recovery_verify(config,cfg);preservation_verify(cfg);verify_prepared(cfg);family_check(cfg)
 if cfg['preservation']['training_authorized'] or cfg['preservation']['representation_methods_authorized'] or cfg['preservation']['v5_confirmation_open_authorized']:raise RuntimeError('authorization drift')
 for k in ('output_root','provenance_root'):
  if (ROOT/cfg['runtime'][k]).exists():raise RuntimeError(f'one-shot namespace exists {k}')
 print(json.dumps({'status':'PASS','candidate_files':len(inventory(config,cfg)),'training':False,'methods':False},indent=2))
def freeze(config:Path)->None:
 cfg=loadj(config);preflight(config);inv=inventory(config,cfg);x={'schema_version':'behavioral_endpoint_v6_1_freeze','namespace':cfg['namespace'],'config_sha256':sha(config),'candidate_inventory':inv,'candidate_inventory_sha256':hashlib.sha256(canon(inv)).hexdigest(),'v5_preservation_sha256':sha(ROOT/cfg['preservation']['v5_manifest']),'invalidated_v6_freeze_sha256':cfg['recovery']['invalidated_v6_freeze_sha256'],'invalidated_v6_review_sha256':cfg['recovery']['invalidated_v6_review_sha256'],'dependency_closure_only':True,'scientific_protocol_changed':False,'endpoint_only':True,'training':False,'methods':False,'model_specific_confirmation':True,'two_family_barrier':True,'one_shot':True,'retry_authorized':False};exjson(ROOT/cfg['runtime']['freeze'],x);print(json.dumps(x,indent=2))
def verify_freeze(config:Path,cfg:Mapping[str,Any])->dict[str,Any]:
 f=loadj(ROOT/cfg['runtime']['freeze'])
 if f['config_sha256']!=sha(config) or f['candidate_inventory']!=inventory(config,cfg):raise RuntimeError('freeze drift')
 recovery_verify(config,cfg);preservation_verify(cfg);verify_prepared(cfg);return f
def normalized_uuid(x:Any)->str:
 s=str(x);return s if s.startswith('GPU-') else 'GPU-'+s
def runtime_gpu()->str:
 exp=os.environ.get('EXPECTED_GPU_UUID')
 if not exp or torch.cuda.device_count()!=1:raise RuntimeError('one expected GPU UUID required')
 act=normalized_uuid(torch.cuda.get_device_properties(0).uuid)
 if act!=exp:raise RuntimeError(f'GPU UUID mismatch {exp}/{act}')
 return act
def model_rows(cfg:Mapping[str,Any],endpoint:str,model:str,stage:str)->list[dict[str,Any]]:return [r for r in readjl(ROOT/cfg['runtime']['prepared_root']/f'{endpoint}_{model}.jsonl') if r['stage']==stage]
def logmeanexp(x:np.ndarray,axis:int=-1)->np.ndarray:
 m=np.max(x,axis=axis,keepdims=True);return np.squeeze(m,axis)+np.log(np.mean(np.exp(x-m),axis=axis))
def condition_logits(model:Any,rows:list[dict[str,Any]],kind:str,batch:int,pad:int,device:torch.device)->np.ndarray:
 out=[]
 for st in range(0,len(rows),batch):
  rr=rows[st:st+batch];ids,mask,bounds,_=core.batch_tensors(rr,kind,pad,device);ar=torch.arange(len(rr),device=device)
  with torch.no_grad():z=model(input_ids=ids,attention_mask=mask,use_cache=False).logits.float()
 out.append(z[ar,bounds].cpu().numpy())
 return np.concatenate(out)
def component_metric(endpoint:str,r:Mapping[str,Any],scores:np.ndarray)->tuple[float,float,bool,dict[str,Any]]:
 if endpoint=='retrieval':
  Z=np.asarray(scores,float);correct=list(r['correct_candidate_indices']);C=[];M=[]
  for i,c in enumerate(correct):
   others=[k for k in range(5) if k!=c];C.append(float(Z[i,c]-logmeanexp(Z[i,others])));M.append(float(Z[i,c]-np.max(Z[i,others])))
  v=int(r['value_index']);T=[float(Z[i,v]-logmeanexp(Z[i,[k for k in range(5) if k!=v]])) for i in range(7)];F=float(min(T[0]-T[i] for i in (1,2,3,6)));N=float(max(abs(T[i]-T[0]) for i in (4,5)));directional=all(x>0 for x in M);extra={'correct_advantages':C,'top1_margins':M,'original_target_advantages':T}
 else:
  A=[float(x) for x in np.asarray(scores,float)];F=float(A[0]-A[1]);N=float(max(abs(A[0]-A[2]),abs(A[0]-A[3])));directional=A[0]>0 and A[1]<0 and A[2]>0 and A[3]>0;extra={'grammatical_advantages':A}
 return F,N,directional,extra
def score(cfg:Mapping[str,Any],endpoint:str,key:str,rows:list[dict[str,Any]])->list[dict[str,Any]]:
 from transformers import AutoModelForCausalLM,AutoTokenizer
 spec=core.model_spec(cfg,key);runtime_gpu();device=torch.device('cuda:0');model=AutoModelForCausalLM.from_pretrained(spec['name'],revision=spec['revision'],local_files_only=True,torch_dtype=torch.float32).to(device).eval()
 for p in model.parameters():p.requires_grad_(False)
 tok=AutoTokenizer.from_pretrained(spec['name'],revision=spec['revision'],local_files_only=True);pad=tok.pad_token_id if tok.pad_token_id is not None else tok.eos_token_id;all_condition=[];ncond=7 if endpoint=='retrieval' else 4
 for i in range(ncond):
  z=condition_logits(model,rows,f'condition_{i}',int(spec['batch_size']),pad,device)
  if endpoint=='retrieval':all_condition.append(np.asarray([[z[j,k] for k in r['candidate_ids']] for j,r in enumerate(rows)],np.float64))
  else:all_condition.append(core.logodds(z,rows))
 out=[]
 for j,r in enumerate(rows):
  F,N,directional,extra=component_metric(endpoint,r,np.stack([x[j] for x in all_condition]))
  if not all(math.isfinite(x) for x in [F,N,*[z for values in extra.values() for z in values]]):raise RuntimeError(f'nonfinite metric {endpoint}/{key}/{r["component_id"]}')
  eligible=bool(directional and F>cfg['gate']['minimum_effect']);ratio=float(N/max(F,1e-8)) if eligible else None;out.append({'schema_version':'behavioral_endpoint_v6_metric','endpoint':endpoint,'model':key,'family':spec['family'],'stage':r['stage'],'source':r['source'],'template_index':r['template_index'],'set_index':r['set_index'],'component_id':r['component_id'],'component_block':r['component_block'],'full_effect':float(F),'nuisance':float(N),'directionally_correct':bool(directional),'eligible':eligible,'ratio':ratio,**extra})
 del model;torch.cuda.empty_cache();return out
def endpoint_authorized(gate:Mapping[str,Any],key:str)->bool:
 own=next((x for x in gate.get('models',[]) if x['model']==key),None);return gate.get('status')=='PASS' and own is not None and own['eligible_all_sources_templates']
def worker(config:Path,endpoint:str,key:str,stage:str)->None:
 cfg=loadj(config);root=ROOT/cfg['runtime']['output_root'];out=root/stage/endpoint/key
 try:
  verify_freeze(config,cfg)
  if stage=='confirmation':
   gp=root/'development_gate'/endpoint/'result.json';fail=root/'development_gate'/endpoint/'FAILED.json';timeout=root/'development_gate'/endpoint/'TIMEOUT.json';start=time.monotonic()
   while not gp.exists():
    if fail.exists():out.mkdir(parents=True,exist_ok=False);exjson(out/'BLOCKED.json',{'status':'BLOCKED','reason':'DEVELOPMENT_GATE_FAILED','model_loaded':False,'endpoint':endpoint,'model':key});return
    if timeout.exists():out.mkdir(parents=True,exist_ok=False);exjson(out/'BLOCKED.json',{'status':'BLOCKED','reason':'DEVELOPMENT_GATE_TIMEOUT','model_loaded':False,'endpoint':endpoint,'model':key});return
    if time.monotonic()-start>cfg['runtime']['gate_timeout_seconds']:raise TimeoutError('development gate timeout')
    time.sleep(cfg['runtime']['gate_poll_seconds'])
   if not endpoint_authorized(loadj(gp),key):out.mkdir(parents=True,exist_ok=False);exjson(out/'BLOCKED.json',{'status':'BLOCKED','reason':'ENDPOINT_OR_MODEL_INELIGIBLE','model_loaded':False,'endpoint':endpoint,'model':key});return
  out.mkdir(parents=True,exist_ok=False);rows=model_rows(cfg,endpoint,key,stage);metrics=score(cfg,endpoint,key,rows);writejl(out/'metrics.jsonl',metrics);exjson(out/'COMPLETE.json',{'status':'COMPLETE','endpoint':endpoint,'model':key,'stage':stage,'rows':len(metrics),'metrics_sha256':sha(out/'metrics.jsonl'),'freeze_sha256':sha(ROOT/cfg['runtime']['freeze']),'gpu_uuid':normalized_uuid(torch.cuda.get_device_properties(0).uuid)})
 except TimeoutError as e:publish_failure(root/stage/endpoint/f'{key}_TIMEOUT.json',{'status':'TIMEOUT','endpoint':endpoint,'model':key,'stage':stage,'error':str(e),'traceback':traceback.format_exc()});raise
 except BaseException as e:publish_failure(root/stage/endpoint/f'{key}_FAILED.json',{'status':'FAILED','endpoint':endpoint,'model':key,'stage':stage,'error_type':type(e).__name__,'error':str(e),'traceback':traceback.format_exc()});raise
def qhigher(values:list[float],q:float)->float:
 a=sorted(values);return a[max(0,math.ceil(q*len(a))-1)]
def display_num(x:float)->float|str:return 'INFINITY' if not math.isfinite(x) else float(x)
def cell_summary(rows:list[dict[str,Any]],cfg:Mapping[str,Any],seed:int)->dict[str,Any]:
 if len(rows)!=cfg['gate']['sets_per_template']*cfg['gate']['components_per_set']:raise RuntimeError(f'cell row count {len(rows)}')
 sets=[[r for r in rows if int(r['set_index'])==s] for s in range(cfg['gate']['sets_per_template'])]
 if any(len(x)!=cfg['gate']['components_per_set'] for x in sets):raise RuntimeError('cell set-size drift')
 per=[sum(r['eligible'] for r in rr) for rr in sets];support=all(x>=cfg['gate']['minimum_eligible_per_set'] for x in per) and sum(per)>=cfg['gate']['minimum_eligible_per_template'];means=[]
 for rr in sets:
  x=[r['ratio'] for r in rr if r['eligible']];means.append(float(np.mean(x)) if x else math.inf)
 point=float(np.mean(means));rng=np.random.default_rng(seed);draws=[]
 for _ in range(cfg['gate']['bootstrap_draws']):
  vals=[]
  for s in rng.integers(0,len(sets),len(sets)):
   rr=sets[int(s)];sample=[rr[i] for i in rng.integers(0,len(rr),len(rr))];x=[r['ratio'] for r in sample if r['eligible']];vals.append(float(np.mean(x)) if x else math.inf)
  draws.append(float(np.mean(vals)))
 lo=qhigher(draws,1-cfg['gate']['quantile']);hi=qhigher(draws,cfg['gate']['quantile']);passed=support and math.isfinite(point) and point<=cfg['gate']['maximum_ratio_point'] and math.isfinite(hi) and hi<cfg['gate']['maximum_ratio_upper']
 return {'rows':len(rows),'eligible_rows':sum(per),'eligible_per_set':per,'ratio_interval':[display_num(lo),display_num(point),display_num(hi)],'passes':bool(passed)}
def overall_summary(rows:list[dict[str,Any]],templates:int,cfg:Mapping[str,Any],seed:int)->dict[str,Any]:
 groups={(t,s):[r for r in rows if int(r['template_index'])==t and int(r['set_index'])==s] for t in range(templates) for s in range(4)};point=float(np.mean([np.mean([r['ratio'] for r in rr if r['eligible']]) if any(r['eligible'] for r in rr) else math.inf for rr in groups.values()]));docs=sorted({r['component_block'] for r in rows});rng=np.random.default_rng(seed);draws=[]
 for _ in range(cfg['gate']['bootstrap_draws']):
  tm=Counter(map(int,rng.integers(0,templates,templates)));sm=Counter(map(int,rng.integers(0,4,4)));dm=Counter(docs[int(i)] for i in rng.integers(0,len(docs),len(docs)));numerator=denominator=0.0;valid=True
  for t,tw in tm.items():
   for s,sw in sm.items():
    rr=groups[(t,s)];cell_weight=0
    for r in rr:
     ww=tw*sw*dm.get(r['component_block'],0)
     if ww and r['eligible']:numerator+=ww*r['ratio'];denominator+=ww;cell_weight+=ww
    if not cell_weight:valid=False
  draws.append(float(numerator/denominator) if valid and denominator else math.inf)
 lo=qhigher(draws,1-cfg['gate']['quantile']);hi=qhigher(draws,cfg['gate']['quantile']);passed=math.isfinite(point) and point<=cfg['gate']['maximum_ratio_point'] and math.isfinite(hi) and hi<cfg['gate']['maximum_ratio_upper'];return {'templates':templates,'documents':len(docs),'ratio_interval':[display_num(lo),display_num(point),display_num(hi)],'passes':bool(passed)}
def wait_workers(root:Path,stage:str,endpoint:str,names:list[str],cfg:Mapping[str,Any])->None:
 start=time.monotonic()
 while True:
  if all((root/stage/endpoint/n/'COMPLETE.json').exists() or (root/stage/endpoint/n/'BLOCKED.json').exists() or (root/stage/endpoint/f'{n}_FAILED.json').exists() or (root/stage/endpoint/f'{n}_TIMEOUT.json').exists() for n in names):return
  if time.monotonic()-start>cfg['runtime']['worker_timeout_seconds']:raise TimeoutError(f'{stage}/{endpoint} timeout')
  time.sleep(cfg['runtime']['gate_poll_seconds'])
def family_count(models:list[dict[str,Any]],field:str)->int:return len({m['family'] for m in models if m[field]})
def development_classification(families:int,any_template:bool,minimum:int)->tuple[str,str]:
 if families>=minimum:return 'PASS','PASS'
 if families==1:return 'FAIL','INSUFFICIENT_MODEL_REPLICATION'
 return 'FAIL',('TEMPLATE_CONDITIONED' if any_template else 'FAIL')
def final_decision(passed:list[str],development_passed:list[str])->str:
 if passed==['retrieval']:return 'RETRIEVAL_CONFIRMED'
 if passed==['agreement']:return 'AGREEMENT_CONFIRMED'
 if len(passed)==2:return 'BOTH_CONFIRMED'
 if not development_passed:return 'BOTH_ENDPOINTS_STOP'
 return 'STOP_NATURALISTIC_CONTROL'
def development_gate(config:Path,endpoint:str)->None:
 cfg=loadj(config);root=ROOT/cfg['runtime']['output_root'];out=root/'development_gate'/endpoint;out.mkdir(parents=True,exist_ok=False);names=[m['key'] for m in cfg['models']]
 try:
  verify_freeze(config,cfg);manifest=loadj(ROOT/cfg['runtime']['provenance_root']/'launch_manifest.json');expected={x['model']:x['uuid'] for x in manifest['assignments'] if x['endpoint']==endpoint};wait_workers(root,'development',endpoint,names,cfg)
  timed=[n for n in names if (root/'development'/endpoint/f'{n}_TIMEOUT.json').exists()]
  if timed:raise TimeoutError(f'worker timeout {timed}')
  failed=[n for n in names if (root/'development'/endpoint/f'{n}_FAILED.json').exists()]
  if failed:raise RuntimeError(f'worker failure {failed}')
  models=[]
  for n in names:
   p=root/'development'/endpoint/n/'metrics.jsonl';c=loadj(root/'development'/endpoint/n/'COMPLETE.json');rows=readjl(p)
   if c['metrics_sha256']!=sha(p) or c['gpu_uuid']!=expected[n] or len(rows)!=768:raise RuntimeError(f'artifact/GPU drift {n}')
   sources=[]
   for source in cfg['panel']['development_sources']:
    rr=[r for r in rows if r['source']==source];cells=[]
    for t in range(6):cells.append({'template_index':t,**cell_summary([r for r in rr if int(r['template_index'])==t],cfg,stable(cfg['seed'],'development',endpoint,n,source,t,'cell'))})
    overall=overall_summary(rr,6,cfg,stable(cfg['seed'],'development',endpoint,n,source,'overall'));sources.append({'source':source,'cells':cells,'overall':overall,'passes':all(x['passes'] for x in cells) and overall['passes']})
   models.append({'model':n,'family':core.model_spec(cfg,n)['family'],'sources':sources,'eligible_all_sources_templates':all(x['passes'] for x in sources)})
  families=family_count(models,'eligible_all_sources_templates');any_template=any(c['passes'] for m in models for s in m['sources'] for c in s['cells']);status,classification=development_classification(families,any_template,cfg['gate']['minimum_families']);result={'schema_version':'behavioral_endpoint_v6_development_gate','endpoint':endpoint,'status':status,'classification':classification,'models':models,'eligible_families':families,'confirmation_authorized':status=='PASS','freeze_sha256':sha(ROOT/cfg['runtime']['freeze'])};exjson(out/'result.json',result);exjson(out/f'{classification}.json',result)
 except TimeoutError as e:publish_failure(out/'TIMEOUT.json',{'status':'TIMEOUT','endpoint':endpoint,'error':str(e),'traceback':traceback.format_exc()});raise
 except BaseException as e:publish_failure(out/'FAILED.json',{'status':'FAILED','endpoint':endpoint,'error':str(e),'traceback':traceback.format_exc()});raise
def final_aggregate(config:Path)->None:
 cfg=loadj(config);root=ROOT/cfg['runtime']['output_root'];out=root/'final';out.mkdir(parents=True,exist_ok=False);names=[m['key'] for m in cfg['models']]
 try:
  verify_freeze(config,cfg);manifest=loadj(ROOT/cfg['runtime']['provenance_root']/'launch_manifest.json');expected={(x['endpoint'],x['model']):x['uuid'] for x in manifest['assignments']}
  for e in cfg['endpoints']:wait_workers(root,'confirmation',e,names,cfg)
  endpoint_results=[]
  for e in cfg['endpoints']:
   timed=[n for n in names if (root/'confirmation'/e/f'{n}_TIMEOUT.json').exists()]
   if timed:raise TimeoutError(f'confirmation timeout {e}/{timed}')
   failed=[n for n in names if (root/'confirmation'/e/f'{n}_FAILED.json').exists()]
   if failed:raise RuntimeError(f'confirmation failure {e}/{failed}')
   dev=loadj(root/'development_gate'/e/'result.json');models=[]
   for dm in dev['models']:
    n=dm['model'];blocked=(root/'confirmation'/e/n/'BLOCKED.json').exists();sources=[]
    if not blocked:
     p=root/'confirmation'/e/n/'metrics.jsonl';c=loadj(root/'confirmation'/e/n/'COMPLETE.json');rows=readjl(p)
     if c['metrics_sha256']!=sha(p) or c['gpu_uuid']!=expected[(e,n)] or len(rows)!=384:raise RuntimeError(f'confirmation drift {e}/{n}')
     for source in cfg['panel']['confirmation_sources']:
      rr=[r for r in rows if r['source']==source];cells=[{'template_index':t,**cell_summary([r for r in rr if int(r['template_index'])==t],cfg,stable(cfg['seed'],'confirmation',e,n,source,t,'cell'))} for t in range(3)];overall=overall_summary(rr,3,cfg,stable(cfg['seed'],'confirmation',e,n,source,'overall'));sources.append({'source':source,'cells':cells,'overall':overall,'passes':all(x['passes'] for x in cells) and overall['passes']})
    passed=bool(not blocked and all(x['passes'] for x in sources));models.append({'model':n,'family':dm['family'],'blocked':blocked,'sources':sources,'passes_all_confirmation':passed})
   families=family_count(models,'passes_all_confirmation');endpoint_results.append({'endpoint':e,'development_status':dev['status'],'development_classification':dev['classification'],'models':models,'confirmation_families':families,'confirmation_passes':families>=cfg['gate']['minimum_families']})
  passed=[x['endpoint'] for x in endpoint_results if x['confirmation_passes']];devpassed=[x['endpoint'] for x in endpoint_results if x['development_status']=='PASS']
  decision=final_decision(passed,devpassed)
  result={'schema_version':'behavioral_endpoint_v6_final','status':'PASS' if passed else 'FAIL','decision':decision,'endpoints':endpoint_results,'future_method_authorization':False,'representation_methods_evaluated':False,'training_performed':False,'freeze_sha256':sha(ROOT/cfg['runtime']['freeze'])};exjson(out/'result.json',result);exjson(out/f"{result['status']}.json",result)
 except TimeoutError as e:publish_failure(out/'TIMEOUT.json',{'status':'TIMEOUT','error':str(e),'traceback':traceback.format_exc()});raise
 except BaseException as e:publish_failure(out/'FAILED.json',{'status':'FAILED','error':str(e),'traceback':traceback.format_exc()});raise
def main()->None:
 p=argparse.ArgumentParser();p.add_argument('command',choices=['prepare','preservation-verify','cache-preflight','preflight','freeze','verify-freeze','worker','development-gate','final']);p.add_argument('--config',type=Path,default=DEFAULT);p.add_argument('--output',type=Path);p.add_argument('--endpoint',choices=['retrieval','agreement']);p.add_argument('--model');p.add_argument('--stage',choices=['development','confirmation']);a=p.parse_args();cfg=loadj(a.config)
 if a.command=='prepare':prepare(a.config,a.output)
 elif a.command=='preservation-verify':preservation_verify(cfg);print('PASS')
 elif a.command=='cache-preflight':cache_preflight(a.config)
 elif a.command=='preflight':preflight(a.config)
 elif a.command=='freeze':freeze(a.config)
 elif a.command=='verify-freeze':verify_freeze(a.config,cfg);print('PASS')
 elif a.command=='worker':
  if not a.endpoint or not a.model or not a.stage:p.error('worker requires endpoint/model/stage')
  worker(a.config,a.endpoint,a.model,a.stage)
 elif a.command=='development-gate':
  if not a.endpoint:p.error('development-gate requires endpoint')
  development_gate(a.config,a.endpoint)
 else:final_aggregate(a.config)
if __name__=='__main__':main()
