"""Actual synthetic application consumers, not fake scientific approval."""
from pathlib import Path
import sys
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import msae_norspan_jpc_runtime as r
import msae_norspan_jpc_controls as c
import prepare_msae_independent_norspan_v1 as p

def configure(tmp_path,monkeypatch):
    for name,path in [('ROOT',tmp_path),('PROV',tmp_path/'reports/provenance/msae_independent_norspan_v1'),('DATA',tmp_path/'data/msae_independent_norspan_v1'),('RAW',tmp_path/'data/msae_independent_norspan_v1/raw'/p.COMMIT),('PRIVATE',tmp_path/'data/msae_independent_norspan_v1/private')]:monkeypatch.setattr(p,name,path)
    return c.ControlSession(p.PROV,lineage_sha256='a'*64)

def test_actual_publisher_canonical_sha_and_logical_inventory(tmp_path,monkeypatch):
    session=configure(tmp_path,monkeypatch)
    value={'schema_version':'synthetic_fixture_v1','status':'fixture'}
    with p.paired_control_session(session):
        p.publish_json(p.PROV/'current_history_registry.json',value)
        p.publish_json(p.PROV/'baseline.json',value)
        assert p.canonical_control(p.PROV/'baseline.json')==value
        assert p.load_json(p.PROV/'baseline.json')==value
        assert p.sha_file(p.PROV/'baseline.json')==session.expected('baseline.json').sha256
        inv=p.protocol_inventory()
        assert inv['public']==['baseline.json','current_history_registry.json']
        assert inv['unknown_public']==[]
        assert len(inv['public_manifest'])==4
        assert p.classify_protocol_state()=='baseline'
    with pytest.raises(p.GateFailure,match='paired_control_session_required'):p.load_json(p.PROV/'baseline.json')

def test_actual_raw_pair_consumer_and_git_identity(tmp_path,monkeypatch):
    import hashlib
    session=configure(tmp_path,monkeypatch)
    files={name:b'opaque synthetic '+name.encode() for name in [*p.SOURCE_FILES.values(),p.LICENSE_FILE]}
    p.ensure_directory(p.DATA,0o700);p.ensure_directory(p.DATA/'raw',0o700)
    manifest=p.publish_flat_directory(p.RAW,files,directory_mode=0o555,file_mode=0o444)
    records={name:{**item,'git_blob_sha1':hashlib.sha1(b'blob '+str(len(files[name])).encode()+b'\0'+files[name]).hexdigest()} for name,item in manifest.items()}
    assert p.load_validated_raw({'files':records})==files
    bad={name:dict(item) for name,item in records.items()};bad[p.LICENSE_FILE]['git_blob_sha1']='0'*40
    with pytest.raises(p.GateFailure,match='raw_identity'):p.load_validated_raw({'files':bad})
    assert len(list(p.RAW.iterdir()))==8

def test_actual_private_opaque_consumer_outside_manifest(tmp_path,monkeypatch):
    configure(tmp_path,monkeypatch);p.ensure_directory(p.DATA,0o700)
    rendered={role:('{"synthetic":"'+role+'"}\n').encode() for role in r.ROLES}
    manifest=r.publish_role_pairs(p.PRIVATE,rendered)
    result=p.verify_private_payload_bytes(rendered,expected_manifest=manifest)
    assert all(x['scientific_open_count']==0 and x['custody_hash_open_count']==1 for x in result.values())
    assert all(result[role]['sha256']==manifest[role]['sha256'] for role in r.ROLES)
    with pytest.raises(p.GateFailure,match='outside_private_manifest_required'):p.verify_private_payload_bytes(rendered)

def test_retained_scratch_not_legacy_deleted_success(tmp_path):
    with r.reserve_scratch(tmp_path/'scratch',authority_sha256='a'*64,entry_lineage_sha256='b'*64) as lease:
        record=lease.snapshot(durable=True);p.validate_scratch_record(record)
        bad=dict(record);bad['budget_monitor_is_hard_quota']=True
        with pytest.raises(p.GateFailure):p.validate_scratch_record(bad)
    with pytest.raises(p.GateFailure):p.validate_scratch_record({'device':1,'inode':2,'cleanup_verified':True})
