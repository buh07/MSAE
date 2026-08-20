from __future__ import annotations
import json,sys
from pathlib import Path
import numpy as np
import torch
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts'))
import joint_controllability_benchmark_v3 as j
CFG=json.loads((ROOT/'configs/joint_controllability_benchmark_v3/run.json').read_text())

def test_stage_single_layer_is_middle():
 assert j.stage({'layers':[8]},8)=='middle'
 assert [j.stage({'layers':[1,6,10]},x) for x in [1,6,10]]==['early','middle','late']

def test_matched_budget_is_exact():
 x=np.array([[3.,4.,0.],[0.,2.,0.]],np.float32);natural=np.array([[0.,10.,0.],[6.,8.,0.]],np.float32)
 z=j.match_norm(x,natural,.5,1e-8)
 assert np.allclose(np.linalg.norm(z,axis=1)/np.linalg.norm(natural,axis=1),.5)

def test_public_sae_topk_and_jumprelu_are_finite():
 W=torch.eye(4);b=torch.zeros(4)
 top=j.PublicSAE('t',W,b,W,b,'topk',2);jump=j.PublicSAE('j',W,b,W,b,'jumprelu',threshold=torch.ones(4)*.5)
 x=torch.tensor([[1.,.7,.2,-1.]])
 assert torch.count_nonzero(top.encode(x))==2
 assert torch.isfinite(jump.decode(jump.encode(x))).all()

def test_config_preserves_closure_and_has_no_k2_method():
 assert CFG['preservation']['k2_training_authorized'] is False
 assert CFG['preservation']['sae_training_authorized'] is False
 assert all('k2' not in x for x in CFG['methods'])
 src=(ROOT/'scripts/joint_controllability_benchmark_v3.py').read_text()
 assert 'train_msae' not in src and 'train_decomposition(' not in src

def test_sources_are_explicitly_within_corpus():
 assert CFG['task']['within_corpus_transfer'] is True
 assert CFG['claim_limits']['cross_domain_replication'] is False

def test_prepared_documents_and_splits_are_disjoint():
 rows=j.readjl(ROOT/CFG['runtime']['prepared_root']/'rows.jsonl')
 ids=[r[k] for r in rows for k in ('document_id','donor_base_id','donor_sham_id')]
 assert len(ids)==len(set(ids))==3*len(rows)
 counts={(s,sp):sum(r['source']==s and r['split']==sp for r in rows) for s in CFG['task']['sources'] for sp in ('development','test')}
 assert all(counts[(s,'development')]==CFG['task']['development_per_source'] for s in CFG['task']['sources'])
 assert all(counts[(s,'test')]==CFG['task']['test_per_source'] for s in CFG['task']['sources'])
