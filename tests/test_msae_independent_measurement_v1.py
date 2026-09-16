import hashlib,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts'))
from msae_measurement_remediation_v1 import build_stage_a,validate_draft_config

def test_frozen_config_is_ready_and_stage_a_ready():
 p=ROOT/'configs/msae_independent_measurement_v1/protocol.json';raw=p.read_bytes();d=hashlib.sha256(raw).hexdigest()
 assert validate_draft_config(raw,d)['status']=='ready'
 a=json.loads((ROOT/'reports/provenance/msae_independent_measurement_v1/stage_a.json').read_text())
 assert a['stage']=='A' and a['stage_ready'] is False and a['protocol_config_sha256']==d
 assert 'candidate_confirmation_source:accessible_history_overlap_detected' in a['aggregate']['overall']['blocking_reasons']

def test_source_partition_is_disjoint_and_complete():
 x=json.loads((ROOT/'data/msae_independent_measurement_v1/source_partition.json').read_text());s=x['selected']
 assert len(s)==350
 assert all(sum(z['genre']==g and z['role']==r for z in s)==25 for g in x['genres'] for r in ('C1','C2'))
 assert len({z['path'] for z in s})==350
 assert all(x['support'][r][t]['status']=='eligible' for r in ('C1','C2') for t in ('absolute_bucket','neutral_prefix_offset','relative_quartile','head_signed_distance','dependency_depth','token_identity','lemma_identity','entity_binary'))

def test_strata_and_registry_are_exact():
 cfg=json.load(open(ROOT/'configs/msae_independent_measurement_v1/protocol.json'));f=json.load(open(ROOT/'data/msae_independent_measurement_v1/calibration_strata.json'))
 assert [x['stratum_id'] for x in cfg['replay']['strata']]==['main_short','main_long','pair_context','pair_entity']
 assert len(f['strata']['main_short']['units'])==8 and len(f['strata']['main_long']['units'])==8
 assert len(f['strata']['pair_context']['units'])==16 and len(f['strata']['pair_entity']['units'])==16
 assert all(len(x['repeat_evaluation_ids'])==3 for x in cfg['replay']['strata'])
 assert cfg['replay']['safety_factor']==2.0 and len(cfg['replay']['tolerance_ladder'])==8

def test_endpoint_inventory_and_lineages():
 cfg=json.load(open(ROOT/'configs/msae_independent_measurement_v1/protocol.json'));c=cfg['stages']['C']['required_by_category']
 assert {k:len(v) for k,v in c.items()}=={'localization':1200,'functional_reproducibility':9,'collateral':264,'counterfactual':96,'baseline':44}
 ck=cfg['functional_reproducibility']['checkpoints'];assert [x['seed'] for x in ck]==[42,43,44]
 assert len({x['checkpoint_sha256'] for x in ck})==3

def test_launcher_is_same_fd_and_timeout_scoped():
 s=(ROOT/'scripts/msae_independent_measurement_v1.py').read_text();r=(ROOT/'scripts/run_msae_independent_calibration_v1.py').read_text()
 assert 'SCM_RIGHTS' in s and "fcntl.LOCK_EX|fcntl.LOCK_NB" in s
 assert "'--kill-after=60s','6h'" in s and 'CUDA_VISIBLE_DEVICES' in s
 assert "local_files_only=True" in r and "build_stage_b" in r
