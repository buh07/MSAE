# Maintained copy of retained independent synthetic matrix; original unchanged.
"""Independent close/control/started tests against frozen foundation."""
import copy
import hashlib
import os
from pathlib import Path
import sys
import pytest
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import msae_jumbo_pair_commit as j
import msae_norspan_jpc_runtime as r

@pytest.mark.parametrize('kind',['flat', 'roles', 'recover'])
@pytest.mark.parametrize('primary_type',[None, OSError, KeyboardInterrupt])
@pytest.mark.parametrize('close_type',[OSError, KeyboardInterrupt])
def test_all_combined_aggregate_closes_release_once_preserve_primary_and_reuse(tmp_path, monkeypatch, kind, primary_type, close_type):
    root=tmp_path/'subjects'
    sentinel=tmp_path/'unrelated'; sentinel.write_bytes(b'unrelated')
    if kind=='recover':
        root.mkdir(mode=0o700)
        catalog={'schema_version':'norspan_jpc_custody_catalog_v1','lineage_sha256':'a'*64,
                 'controls':{name:j.receipt_record(j.create_pair(root/name,b'fresh-synthetic',mode=0o644)) for name in ['baseline.json','authority.json']}}
    def operation():
        if kind=='flat': return r.publish_flat_pairs(root, {'one':b'one','two':b'two'},directory_mode=0o700,file_mode=0o644)
        if kind=='roles': return r.publish_role_pairs(root,{role:role.encode() for role in r.ROLES})
        digest=hashlib.sha256(r.canonical_bytes(catalog)).hexdigest()
        return r.recover_current_custody(root,catalog,expected_catalog_sha256=digest,lineage_sha256='a'*64)
    real_validate=j.OwnedPair.validate
    def validate(pair,*,durable=False):
        result=real_validate(pair,durable=durable)
        if primary_type and durable: raise primary_type('primary-operation')
        return result
    monkeypatch.setattr(j.OwnedPair,'validate',validate)
    real_finalize, real_close=r._close_resources, os.close
    expected,attempts,reused=[],[],[]
    def finalize(resources,*,primary):
        for resource in reversed(resources): expected.extend([resource.fd,*reversed(resource.parent.descriptors)])
        def fail_close(fd):
            attempts.append(fd)
            real_close(fd)
            reused.append(os.open(sentinel,os.O_RDONLY))
            raise close_type('secondary-close-'+str(fd))
        with monkeypatch.context() as patch:
            patch.setattr(os,'close',fail_close)
            return real_finalize(resources,primary=primary)
    monkeypatch.setattr(r,'_close_resources',finalize)
    try:
        with pytest.raises(primary_type or close_type) as caught: operation()
        assert attempts==expected and len(set(expected))==len(expected)
        for fd in reused: assert os.pread(fd,20,0)==b'unrelated'
        notes=' '.join(getattr(caught.value,'__notes__',[]))
        if primary_type:
            assert str(caught.value)=='primary-operation'
            assert all('secondary-close-'+str(fd) in notes for fd in expected)
        else:
            assert str(caught.value)=='secondary-close-'+str(expected[0])
            assert all('secondary-close-'+str(fd) in notes for fd in expected[1:])
        assert root.exists()
    finally:
        for fd in reused: real_close(fd)

@pytest.mark.parametrize('field,value',[('device',True),('inode',1.0),('mode',448.0),('cleanup_attempts',False),('authority_sha256','A'*64),('entry_lineage_sha256','x')])
def test_malformed_scratch_binding_literals_reject(tmp_path,field,value):
    with r.reserve_scratch(tmp_path/'lease',authority_sha256='a'*64,entry_lineage_sha256='b'*64) as lease:
        binding=copy.deepcopy(lease.binding); binding[field]=value
        with pytest.raises((r.RuntimeBlocked,j.PairFailure)): r.reopen_scratch(binding)

@pytest.mark.parametrize('field,value',[('nlink',2.0),('bytes',True),('mode',644.0),('sha256','A'*64),('pair',{})])
def test_malformed_manifest_literals_reject(tmp_path,field,value):
    manifest=r.publish_flat_pairs(tmp_path/'pairs',{'one':b'one'},directory_mode=0o700,file_mode=0o644)
    manifest['one'][field]=value
    with pytest.raises((r.RuntimeBlocked,j.PairFailure)): r.verify_flat_pairs(tmp_path/'pairs',manifest,directory_mode=0o700,file_mode=0o644)

@pytest.mark.parametrize('marker',['network_started.json','.network_started.json.stage','raw_access_started.json','.raw_access_started.json.stage'])
@pytest.mark.parametrize('terminal',['none','source_acquisition.json','seal.json'])
def test_started_names_never_authorize_source_or_retry(tmp_path,marker,terminal):
    controls={'baseline.json':j.receipt_record(j.create_pair(tmp_path/'baseline.json',b'fresh',mode=0o644))}
    is_final=not marker.startswith('.')
    if is_final: controls[marker]=j.receipt_record(j.create_pair(tmp_path/marker,b'fresh',mode=0o644))
    else: (tmp_path/marker).write_bytes(b'partial')
    if terminal!='none': controls[terminal]=j.receipt_record(j.create_pair(tmp_path/terminal,b'fresh',mode=0o644))
    catalog={'schema_version':'norspan_jpc_custody_catalog_v1','lineage_sha256':'a'*64,'controls':controls}
    digest=hashlib.sha256(r.canonical_bytes(catalog)).hexdigest()
    names=set(os.listdir(tmp_path))
    valid_terminal=is_final and (terminal=='seal.json' or terminal=='source_acquisition.json' and marker=='network_started.json')
    if valid_terminal:
        result=r.recover_current_custody(tmp_path,catalog,expected_catalog_sha256=digest,lineage_sha256='a'*64)
        assert result['source_work_authorized'] is False
        assert result['source_operations']==0 and result['model_operations']==0
        assert result['historical_producer_success_inferred'] is False
    else:
        with pytest.raises((r.RuntimeBlocked,j.PairFailure)): r.recover_current_custody(tmp_path,catalog,expected_catalog_sha256=digest,lineage_sha256='a'*64)
    assert names==set(os.listdir(tmp_path))
