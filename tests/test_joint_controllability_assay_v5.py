import importlib.util,json
from collections import Counter
from pathlib import Path
import numpy as np
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
spec=importlib.util.spec_from_file_location('v5',ROOT/'scripts/joint_controllability_assay_v5.py');v5=importlib.util.module_from_spec(spec);spec.loader.exec_module(v5)
CFG=json.loads((ROOT/'configs/joint_controllability_assay_v5/run.json').read_text())
def test_prescore_exact_grid_and_disjointness():
 p=ROOT/CFG['runtime']['prepared_root'];m=json.loads((p/'PRESCORE.json').read_text());rows=v5.readjl(p/'rows.jsonl')
 assert len(rows)==768==len({r['document_id'] for r in rows})
 assert len({r['content_hash'] for r in rows})==768
 assert len({r['window_hash'] for r in rows})==768
 assert m['incidence_audit']['rank']==31 and m['incidence_audit']['cyclic_negative_control_rank']<31
 assert m['incidence_audit']['smallest_singular_value']>1e-8
 assert set(Counter((r['source'],r['split'],r['template_index']) for r in rows).values())=={64}
 for source in CFG['task']['sources']:
  for split in CFG['task']['splits']:
   rr=[r for r in rows if r['source']==source and r['split']==split]
   assert Counter((r['template_index'],r['answer_index'],r['query_key_index']) for r in rr)==Counter({(t,a,q):1 for t in range(3) for a in range(8) for q in range(8)})
def test_tokenizer_lengths_and_one_token_labels():
 root=ROOT/CFG['runtime']['prepared_root']
 for model in ['gpt2','pythia160','gemma2']:
  rows=v5.readjl(root/f'{model}.jsonl');assert len(rows)==768
  for r in rows:
   lengths={len(r[f'key_{k}_prompt_ids']) for k in range(8)}
   assert len(lengths)==1 and len(r['continuation_ids'])==1 and r['target_id']!=r['contrast_id']
def make_rows(ratio:float,effect:float=1.0):
 return [{'eligible':effect>.25,'full_effect':effect,'sham_ratio':ratio if effect>.25 else None,'template_index':t,'component_block':f'{t}:{i}'} for t in range(3) for i in range(64)]
def test_gate_signed_support_and_thresholds():
 good=v5.summarize(make_rows(.1),CFG,1);assert good['passes']
 wrong=v5.summarize(make_rows(.1,-1),CFG,1);assert not wrong['passes'] and wrong['eligible_rows']==0
 sham=v5.summarize(make_rows(.4),CFG,1);assert not sham['passes']
 sparse=make_rows(.1);[r.update(eligible=False,sham_ratio=None) for r in sparse if int(r['component_block'].split(':')[1])>=54]
 assert not v5.summarize(sparse,CFG,1)['passes']
def test_component_estimand():
 x=np.arange(8,dtype=float);q=3;other=[b for b in range(8) if b!=q]
 F=np.mean([x[q]-x[b] for b in other]);S=np.mean([abs(x[s]-x[b]) for b in other for s in other if s!=b])
 assert np.isclose(F,3-x[other].mean()) and S>0
def test_no_training_or_method_path_and_preservation():
 text=(ROOT/'scripts/joint_controllability_assay_v5.py').read_text().lower()
 for bad in ['optimizer','backward(','load_public_sae','fit_basis(','representation_method_worker']:
  assert bad not in text
 assert CFG['preservation']['k2_training_authorized'] is False
 assert CFG['preservation']['sae_training_authorized'] is False
 assert CFG['preservation']['representation_method_evaluation_authorized'] is False
 v5.preservation_verify(CFG)
def test_confirmation_direction_names_and_own_gate_guard_present():
 text=(ROOT/'scripts/joint_controllability_assay_v5.py').read_text()
 assert "own['eligible_both_sources']" in text
 assert 'WIKITEXT_FRESH_to_AGNEWS_FRESH' in text and 'AGNEWS_FRESH_to_WIKITEXT_FRESH' in text
def test_family_gate_counts_unique_and_rejects_duplicate_registry():
 models=[{'family':'a','ok':True},{'family':'a','ok':True},{'family':'b','ok':False}]
 assert v5.family_count(models,'ok')==1
 bad=json.loads(json.dumps(CFG));bad['models'][1]['family']=bad['models'][0]['family']
 import pytest
 with pytest.raises(RuntimeError,match='one-to-one'):v5.validate_family_registry(bad)
def test_confirmation_authorization_is_global_and_model_specific():
 gate={'status':'PASS','models':[{'model':'a','eligible_both_sources':True},{'model':'b','eligible_both_sources':False}]}
 assert v5.confirmation_authorized(gate,'a')
 assert not v5.confirmation_authorized(gate,'b') and not v5.confirmation_authorized({'status':'FAIL','models':gate['models']},'a')
def test_offline_and_cache_content_attestation(monkeypatch):
 import pytest
 monkeypatch.delenv('HF_DATASETS_OFFLINE',raising=False)
 with pytest.raises(RuntimeError,match='offline'):v5.require_offline()
 att=json.loads((ROOT/CFG['runtime']['cache_attestation']).read_text())
 assert att['content_hashed'] and all(all(len(f['sha256'])==64 and f['bytes']>0 for f in m['files']) for m in att['models'])
def test_gpu_uuid_normalization_and_mismatch(monkeypatch):
 import pytest
 class P: uuid='abc'
 monkeypatch.setattr(v5.torch.cuda,'device_count',lambda:1);monkeypatch.setattr(v5.torch.cuda,'get_device_properties',lambda _:P())
 monkeypatch.setenv('EXPECTED_GPU_UUID','GPU-abc');assert v5.validate_runtime_gpu()=='GPU-abc'
 monkeypatch.setenv('EXPECTED_GPU_UUID','GPU-def')
 with pytest.raises(RuntimeError,match='mismatch'):v5.validate_runtime_gpu()
def test_weight_index_is_hashed_and_mutation_detected(tmp_path):
 shard=tmp_path/'model-00001-of-00001.safetensors';shard.write_bytes(b'weights')
 idx=tmp_path/'model.safetensors.index.json';idx.write_text('{"weight_map":{"x":"model-00001-of-00001.safetensors"}}')
 (tmp_path/'config.json').write_text('{}')
 a={r['name']:r['sha256'] for r in v5.cached_asset_records(tmp_path)}
 assert 'model.safetensors.index.json' in a
 idx.write_text('{"weight_map":{"y":"model-00001-of-00001.safetensors"}}')
 b={r['name']:r['sha256'] for r in v5.cached_asset_records(tmp_path)}
 assert a['model.safetensors.index.json']!=b['model.safetensors.index.json']
def test_confirmation_worker_never_scores_when_ineligible(tmp_path,monkeypatch):
 cfg=json.loads(json.dumps(CFG));cfg['runtime']['output_root']='out';cfg['runtime']['freeze']='freeze.json';v5.ROOT=tmp_path
 (tmp_path/'freeze.json').write_text('{}')
 gate=tmp_path/'out/development_gate';gate.mkdir(parents=True);(gate/'result.json').write_text(json.dumps({'status':'PASS','models':[{'model':'gpt2','eligible_both_sources':False}]}))
 original=v5.loadj;monkeypatch.setattr(v5,'loadj',lambda p:cfg if Path(p).name=='config.json' else original(Path(p)))
 monkeypatch.setattr(v5,'verify_freeze',lambda *a: {})
 called=[];monkeypatch.setattr(v5,'score_rows',lambda *a:called.append(True))
 v5.worker(tmp_path/'config.json','gpt2','confirmation')
 assert called==[] and (tmp_path/'out/confirmation/gpt2/BLOCKED.json').exists()
