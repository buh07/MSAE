"""Aggregate mutation of an earlier held original FD with cached metadata."""
import hashlib
import os
from pathlib import Path
import sys
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import msae_jumbo_pair_commit as j
import msae_norspan_jpc_runtime as r

@pytest.mark.parametrize('kind,durable',[('flat_publish',True),('flat_verify',False),('flat_verify',True),('role_publish',True),('role_verify',False),('role_verify',True),('recovery',True)])
def test_last_existing_aggregate_validation_mutates_earlier_bytes_cached_metadata(tmp_path,monkeypatch,kind,durable):
    root=tmp_path/'subjects';fired=[];cached={}
    if kind.startswith('flat'):
        files={'one':b'alpha','two':b'bravo'};first=root/'one';last=root/'two'
        if kind=='flat_verify':manifest=r.publish_flat_pairs(root,files,directory_mode=0o700,file_mode=0o600)
        invoke=lambda:r.publish_flat_pairs(root,files,directory_mode=0o700,file_mode=0o600) if kind=='flat_publish' else r.verify_flat_pairs(root,manifest,directory_mode=0o700,file_mode=0o600,durable=durable)
    elif kind.startswith('role'):
        files={role:b'alpha' for role in r.ROLES};first=root/'discovery'/'payload.jsonl';last=root/'c2'/'payload.jsonl'
        if kind=='role_verify':manifest=r.publish_role_pairs(root,files)
        invoke=lambda:r.publish_role_pairs(root,files) if kind=='role_publish' else r.verify_role_pairs(root,manifest,durable=durable)
    else:
        root.mkdir(mode=0o755);root.chmod(0o755)
        rec={name:j.receipt_record(j.create_pair(root/name,b'{}\n',mode=0o644)) for name in ['baseline.json','authority.json']}
        first=root/'baseline.json';last=root/'authority.json'
        catalog={'schema_version':'norspan_jpc_custody_catalog_v1','lineage_sha256':'a'*64,'controls':rec}
        pin=hashlib.sha256(r.canonical_bytes(catalog)).hexdigest()
        invoke=lambda:r.recover_current_custody(root,catalog,expected_catalog_sha256=pin,lineage_sha256='a'*64)
    realvalidate,realfstat,realstat=j.OwnedPair.validate,os.fstat,os.stat
    def validate(pair,*,durable=False):
        result=realvalidate(pair,durable=durable)
        if not fired and Path(os.readlink('/proc/self/fd/'+str(pair.fd))) in {last,last.with_name('.'+last.name+'.stage')}:
            cached['before']=first.stat();fired.append(True)
            first.write_bytes(b'xxxxx' if kind!='recovery' else b'xx\n')
        return result
    def fstat(fd):
        result=realfstat(fd)
        if cached and (result.st_dev,result.st_ino)==(cached['before'].st_dev,cached['before'].st_ino):return cached['before']
        return result
    def stat(name,*args,**kwargs):
        result=realstat(name,*args,**kwargs)
        if cached and (result.st_dev,result.st_ino)==(cached['before'].st_dev,cached['before'].st_ino):return cached['before']
        return result
    monkeypatch.setattr(j.OwnedPair,'validate',validate);monkeypatch.setattr(os,'fstat',fstat);monkeypatch.setattr(os,'stat',stat)
    try:
        with pytest.raises((j.PairFailure,r.RuntimeBlocked)):invoke()
    finally:
        assert fired==[True], "Injection did not fire"
    assert fired==[True] and first.read_bytes()==(b'xxxxx' if kind!='recovery' else b'xx\n')
