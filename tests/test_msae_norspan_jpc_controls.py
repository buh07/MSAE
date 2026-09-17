"""Actual synthetic paired consumer/session tests, never authority approval."""
import copy
import hashlib
import os
from pathlib import Path
import sys
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import msae_jumbo_pair_commit as j
import msae_norspan_jpc_runtime as r
import msae_norspan_jpc_controls as c

def test_live_receipts_canonical_reads_and_explicit_catalog(tmp_path):
    root=tmp_path/'controls';root.mkdir(mode=0o755);root.chmod(0o755)
    session=c.ControlSession(root,lineage_sha256='a'*64)
    value={'schema_version':'synthetic_control_v1','status':'fixture','source_operations':0}
    receipt=j.create_pair(root/'baseline.json',r.canonical_bytes(value)+b'\n',mode=0o644)
    session.register('baseline.json',receipt)
    assert session.canonical('baseline.json')==value
    catalog=session.catalog();pin=hashlib.sha256(r.canonical_bytes(catalog)).hexdigest()
    reopened=c.ControlSession.from_catalog(root,catalog,expected_sha256=pin,lineage_sha256='a'*64)
    assert reopened.canonical('baseline.json')==value
    assert reopened.inventory()['logical']==['baseline.json']
    assert reopened.source_work_authorized is False

@pytest.mark.parametrize('kind',['missing','wrong_pin','lineage','unknown','bool_inode'])
def test_outside_expected_prerequisites_not_namespace_discovery(tmp_path,kind):
    root=tmp_path/'controls';root.mkdir(mode=0o755);root.chmod(0o755)
    session=c.ControlSession(root,lineage_sha256='a'*64)
    receipt=j.create_pair(root/'baseline.json',b'{}\n',mode=0o644)
    if kind=='missing':
        with pytest.raises(r.RuntimeBlocked,match='outside_expected_receipt_missing'):session.canonical('baseline.json')
        return
    session.register('baseline.json',receipt);cat=session.catalog();lineage='a'*64
    if kind=='lineage':lineage='b'*64
    if kind=='unknown':cat['controls']['foreign.json']=cat['controls'].pop('baseline.json')
    if kind=='bool_inode':cat['controls']['baseline.json']['inode']=True
    pin=hashlib.sha256(r.canonical_bytes(cat)).hexdigest()
    if kind=='wrong_pin':pin='b'*64
    with pytest.raises((r.RuntimeBlocked,j.PairFailure)):
        c.ControlSession.from_catalog(root,cat,expected_sha256=pin,lineage_sha256=lineage)

@pytest.mark.parametrize('kind',['duplicate','nonfinite','noncanonical','extra_key'])
def test_strict_control_bytes_against_actual_outside_pair(tmp_path,kind):
    root=tmp_path/'controls';root.mkdir(mode=0o755);root.chmod(0o755);session=c.ControlSession(root,lineage_sha256='a'*64)
    raw={'duplicate':b'{"a":1,"a":2}\n','nonfinite':b'{"a":NaN}\n','noncanonical':b'{ "a":1}\n','extra_key':b'{"a":1,"extra":2}\n'}[kind]
    session.register('baseline.json',j.create_pair(root/'baseline.json',raw,mode=0o644))
    with pytest.raises(r.RuntimeBlocked):session.canonical('baseline.json',keys={'a'})

@pytest.mark.parametrize('kind',['partial','extra','third','substituted','bytes'])
def test_physical_catalog_drift_preserved_not_retry(tmp_path,kind):
    root=tmp_path/'controls';root.mkdir(mode=0o755);root.chmod(0o755);session=c.ControlSession(root,lineage_sha256='a'*64)
    if kind=='partial':
        (root/'.network_started.json.stage').write_bytes(b'partial')
        result=session.inventory();assert result['status']=='unresolved';assert result['initiated_no_retry'] is True
        assert (root/'.network_started.json.stage').read_bytes()==b'partial';return
    session.register('baseline.json',j.create_pair(root/'baseline.json',b'{}\n',mode=0o644))
    if kind=='extra':(root/'foreign').write_bytes(b'x')
    elif kind=='third':os.link(root/'baseline.json',root/'third')
    elif kind=='substituted':os.rename(root/'baseline.json',root/'original');(root/'baseline.json').write_bytes(b'{}\n')
    else:(root/'baseline.json').write_bytes(b'xx\n')
    with pytest.raises((r.RuntimeBlocked,j.PairFailure)):session.inventory()
    assert list(root.iterdir())
