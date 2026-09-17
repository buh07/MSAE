"""Explicit catalog transport; never a source/scoring launch override."""
from pathlib import Path
import hashlib
import os
import sys
import pytest
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import msae_jumbo_pair_commit as j
import msae_norspan_jpc_runtime as r
import msae_norspan_jpc_controller as c


def test_catalog_transport_records_successful_receipt_before_return(tmp_path):
    root = tmp_path / 'synthetic-project'
    root.mkdir(); prov = root / 'controls'; prov.mkdir(); prov.chmod(0o755)
    store = tmp_path / 'outside-catalogs'
    session, catalog = c.CatalogStore.create(store, prov, project_root=root, lineage_sha256='a' * 64)
    receipt = j.create_pair(prov / 'baseline.json', b'{}\n', mode=0o644)
    session.register('baseline.json', receipt)
    assert catalog.sequence == 1
    fresh, recovered = c.CatalogStore.load(catalog.path, expected_sha256=catalog.sha256,
        root=prov, project_root=root, lineage_sha256='a' * 64)
    assert fresh.canonical('baseline.json') == {}
    assert recovered.sha256 == catalog.sha256
    assert fresh.source_work_authorized is False
    assert len(list(store.iterdir())) == 2


@pytest.mark.parametrize('fault', ['wrong_pin', 'extra', 'stale', 'partial', 'inside'])
def test_catalog_recovery_never_discovers_or_adopts(tmp_path, fault):
    root = tmp_path / 'synthetic-project'; root.mkdir()
    prov = root / 'controls'; prov.mkdir(); prov.chmod(0o755)
    session, store = c.CatalogStore.create(tmp_path / 'outside', prov, project_root=root, lineage_sha256='a' * 64)
    path, pin = store.path, store.sha256
    if fault == 'wrong_pin': pin = 'b' * 64
    elif fault == 'extra': (store.root / 'foreign').write_bytes(b'evidence')
    elif fault == 'stale': session.register('baseline.json', j.create_pair(prov / 'baseline.json', b'{}\n', mode=0o644))
    elif fault == 'partial': path.write_bytes(b'{')
    elif fault == 'inside': path = root / 'catalog.json'; path.write_bytes(b'{}\n'); path.chmod(0o644)
    with pytest.raises((r.RuntimeBlocked, j.PairFailure)):
        c.CatalogStore.load(path, expected_sha256=pin, root=prov, project_root=root, lineage_sha256='a' * 64)
    assert path.exists()


def test_checkpoint_failure_retains_pair_and_poisoned_session(tmp_path, monkeypatch):
    root = tmp_path / 'synthetic-project'; root.mkdir()
    prov = root / 'controls'; prov.mkdir(); prov.chmod(0o755)
    session, store = c.CatalogStore.create(tmp_path / 'outside', prov, project_root=root, lineage_sha256='a' * 64)
    def fail(*args, **kwargs): raise OSError('synthetic-fsync-failure')
    monkeypatch.setattr(c, '_write_snapshot', fail)
    receipt = j.create_pair(prov / 'network_started.json', b'{}\n', mode=0o644)
    with pytest.raises(OSError): session.register('network_started.json', receipt)
    assert (prov / 'network_started.json').exists()
    with pytest.raises(r.RuntimeBlocked, match='poisoned'): session.expected('network_started.json')


@pytest.mark.parametrize('boundary',['predecessor_read','directory_fsync'])
def test_latest_catalog_mutated_inside_final_chain_work_is_rejected(tmp_path,monkeypatch,boundary):
    root=tmp_path/'synthetic-project';root.mkdir();prov=root/'controls';prov.mkdir();prov.chmod(0o755)
    session,store=c.CatalogStore.create(tmp_path/'outside',prov,project_root=root,lineage_sha256='a'*64)
    session.register('baseline.json',j.create_pair(prov/'baseline.json',b'{}\n',mode=0o644))
    path,pin=store.path,store.sha256
    original=c._CatalogReader.read if boundary=='predecessor_read' else os.fsync
    fired=[]
    def mutate():
        raw=path.read_bytes();path.write_bytes(raw.replace(b'a'*64,b'b'*64,1));fired.append(True)
    def read(self,*args,**kwargs):
        value=original(self,*args,**kwargs)
        if self.path.name=='catalog-000000.json' and not fired:mutate()
        return value
    def fsync(fd):
        value=original(fd)
        if os.fstat(fd).st_ino==store.root.stat().st_ino and not fired:mutate()
        return value
    monkeypatch.setattr(c._CatalogReader,'read',read) if boundary=='predecessor_read' else monkeypatch.setattr(os,'fsync',fsync)
    with pytest.raises((r.RuntimeBlocked,j.PairFailure)):
        c.CatalogStore.load(path,expected_sha256=pin,root=prov,project_root=root,lineage_sha256='a'*64)
    assert fired and path.exists()


def test_foreign_catalog_entry_during_final_writer_read_poisoned_not_cleaned(tmp_path,monkeypatch):
    root=tmp_path/'synthetic-project';root.mkdir();prov=root/'controls';prov.mkdir();prov.chmod(0o755)
    session,store=c.CatalogStore.create(tmp_path/'outside',prov,project_root=root,lineage_sha256='a'*64)
    original=r.read_ordinary_file
    fired=[]
    def read(path,**kwargs):
        if path.name=='catalog-000001.json' and not fired:
            (path.parent/'foreign').write_bytes(b'retain me');fired.append(True)
        return original(path,**kwargs)
    monkeypatch.setattr(r,'read_ordinary_file',read)
    with pytest.raises((r.RuntimeBlocked,j.PairFailure)):
        session.register('baseline.json',j.create_pair(prov/'baseline.json',b'{}\n',mode=0o644))
    assert fired and (store.root/'foreign').read_bytes()==b'retain me'
    assert store.sequence==0
    with pytest.raises(r.RuntimeBlocked,match='poisoned'):session.catalog()
