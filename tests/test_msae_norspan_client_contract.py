"""Exact named no-admin proposal and unchanged scientific gates."""
import hashlib
import json
from pathlib import Path
import sys
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import msae_norspan_jpc_runtime as r
import msae_jumbo_pair_commit as j
ROOT=Path(__file__).resolve().parents[1]

def test_new_named_contract_does_not_reinterpret_old_admin_requirement():
    new=r.load_client_contract(ROOT);old=r.load_amendment(ROOT)
    assert old['scratch']['administrator_hard_limits_required'] is True
    assert new['scratch']['administrator_contact'] is False
    assert new['scratch']['hard_aggregate_quota_enforced'] is False
    assert new['assurance']['server_stable_storage']=='UNKNOWN'
    assert new['assurance']['backup_retention']=='UNKNOWN'
    assert new['assurance']['hard_process_limit_512']=='UNVERIFIED'
    assert new['scientific_projection']==old['scientific_projection']
    assert new['activation']['unchanged_hard_containment_waiver'] is False
    with pytest.raises(r.RuntimeBlocked):r.require_whole_qualification()

@pytest.mark.parametrize('file',['config','contract','original'])
def test_literal_drift_rejected_before_activation(tmp_path,file):
    cfg=r.load_client_contract(ROOT)
    selected={r.CLIENT_CONTRACT_PATH:ROOT/r.CLIENT_CONTRACT_PATH,'configs/msae_independent_norspan_v1/protocol.json':ROOT/'configs/msae_independent_norspan_v1/protocol.json',cfg['contract_path']:ROOT/cfg['contract_path']}
    for rel,original in selected.items():
        path=tmp_path/rel;path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(original.read_bytes());path.chmod(0o700 if rel==cfg['contract_path'] else 0o644)
    target={'config':r.CLIENT_CONTRACT_PATH,'contract':cfg['contract_path'],'original':'configs/msae_independent_norspan_v1/protocol.json'}[file]
    with (tmp_path/target).open('ab') as out:out.write(b' ')
    with pytest.raises(r.RuntimeBlocked,match='drift'):r.load_client_contract(tmp_path)

def test_absurd_expected_read_receipt_rejects_without_storage_access(tmp_path):
    record=j.PairReceipt(1,1,0o644,r.FILE_BYTES_LIMIT+1,'a'*64,'.baseline.json.stage','baseline.json')
    with pytest.raises(j.PairFailure):j.open_owned_pair(tmp_path/'baseline.json',record)
