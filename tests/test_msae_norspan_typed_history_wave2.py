"""Actual typed synthetic history/controller prefix; NOT whole qualification."""
from pathlib import Path
import hashlib
import json
import os
import stat
import pytest
from msae_norspan_controller_fixture import Fixture,n,r,c
import msae_jumbo_pair_commit as j


def facts(request,**value):
    request.node.user_properties.append(('synthetic_typed_firing',json.dumps(value,sort_keys=True)))


def fdset():
    return set(os.listdir('/proc/self/fd'))


class BaselineFault:
    def __init__(self,f,monkeypatch,edge,primary):
        self.f,self.edge,self.primary=f,edge,primary
        self.fired=[];self.original=None;self.writer=None;self.pin=None;self.reused=[];self.syncs=0;self.open_attempt=None
        self.real={name:getattr(os,name) for name in ('open','write','fchmod','fsync','close')}
        self.link=j._insert_final
        for name in self.real:monkeypatch.setattr(os,name,getattr(self,name))
        monkeypatch.setattr(j,'_insert_final',self.insert)
    def target(self,fd):
        if self.original is None:return False
        s=os.fstat(fd);return (s.st_dev,s.st_ino)==self.original
    def capture(self):
        assert self.f.store.sequence==1  # Registry is already actually checkpointed.
        self.pin=(self.f.store.path,self.f.store.sha256,self.f.store.sequence)
    def fire(self,edge):
        if self.edge==edge and not self.fired:
            self.fired.append(edge);raise self.primary
    def open(self,path,flags,*args,**kwargs):
        target=path=='.baseline.json.stage' and flags & os.O_CREAT
        if target:
            parent=os.fstat(kwargs['dir_fd'])
            self.open_attempt={'parent_dev':parent.st_dev,'parent_ino':parent.st_ino,'stage_name':str(path),'flags':flags}
            self.capture();self.fire('open')
        fd=self.real['open'](path,flags,*args,**kwargs)
        if target:
            s=os.fstat(fd);self.original=(s.st_dev,s.st_ino);self.writer=fd
        return fd
    def write(self,fd,payload):
        if self.target(fd):self.fire('write')
        return self.real['write'](fd,payload)
    def fchmod(self,fd,mode):
        if self.target(fd):self.fire('chmod')
        return self.real['fchmod'](fd,mode)
    def fsync(self,fd):
        if self.target(fd):
            self.syncs+=1
            if self.syncs==1:self.fire('fsync')
        return self.real['fsync'](fd)
    def insert(self,parent,stage,final):
        if final=='baseline.json':self.fire('link')
        return self.link(parent,stage,final)
    def close(self,fd):
        if self.original is not None and self.target(fd) and self.edge=='close' and not self.fired:
            self.real['close'](fd)
            temporary=self.real['open']('/dev/null',os.O_RDONLY)
            if temporary!=fd:
                replacement=os.dup2(temporary,fd);self.real['close'](temporary)
            else:replacement=temporary
            self.reused.append(replacement);self.fired.append('close');raise self.primary
        return self.real['close'](fd)


def test_typed_history_positive_explicit_fresh_recovery(tmp_path,monkeypatch,request):
    before=fdset();f=Fixture(tmp_path,monkeypatch);f.history()
    result=f.fresh().execute('recover')
    assert result['source_work_authorized'] is False and result['production_canonical_authority_established'] is False
    assert result['state']=='baseline'
    assert result['source_acquisition_commands']==0 and result['source_network_operations']==0 and result['model_operations']==0
    assert not n.DATA.exists() and f.store.sequence==2
    assert fdset()==before
    facts(request,command='build-history_then_fresh_recover',typed_state=result['state'],source_work_authorized=False,catalog_sequence=2)


@pytest.mark.parametrize('edge',['open','write','chmod','fsync','link','close'])
@pytest.mark.parametrize('exception',[OSError,KeyboardInterrupt])
def test_typed_registry_complete_baseline_syscall_fault_no_adoption(tmp_path,monkeypatch,request,edge,exception):
    before=fdset();f=Fixture(tmp_path,monkeypatch);primary=exception('typed baseline '+edge)
    hook=BaselineFault(f,monkeypatch,edge,primary)
    try:
        with pytest.raises(exception) as caught:f.history()
        assert caught.value is primary and hook.fired==[edge]
        assert hook.pin is not None and (f.store.path,f.store.sha256,f.store.sequence)==hook.pin
        assert f.controller._failed and not n.DATA.exists()
        assert 'baseline.json' not in f.session._receipts
        assert not (f.store.root/'catalog-000002.json').exists()
        if edge!='open':assert (n.PROV/'.baseline.json.stage').exists()
        with pytest.raises(r.RuntimeBlocked,match='controller_invocation_failed'):f.history()
        old,store=c.CatalogStore.load(hook.pin[0],expected_sha256=hook.pin[1],root=n.PROV,project_root=n.ROOT,lineage_sha256=f.session.lineage)
        with pytest.raises(r.RuntimeBlocked,match='outside_expected_receipt_missing'):old.expected('baseline.json')
        fresh=c.Controller(old,store,f.approvals)
        with pytest.raises((r.RuntimeBlocked,n.GateFailure,j.PairFailure)):fresh.execute('recover')
        for fd in hook.reused:assert os.fstat(fd)
        facts(request,marker='baseline.json',edge=edge,fired=hook.fired,original=hook.original,open_attempt=hook.open_attempt,predecessor_sequence=hook.pin[2],stage_retained=(n.PROV/'.baseline.json.stage').exists(),no_source_namespace=not n.DATA.exists(),original_writer_reused=bool(hook.reused))
    finally:
        for fd in hook.reused:hook.real['close'](fd)
    assert fdset()==before


@pytest.mark.parametrize('edge',['write','chmod','fsync'])
@pytest.mark.parametrize('exception',[OSError,KeyboardInterrupt])
def test_typed_baseline_catalog_actual_syscall_fault_predecessor_retained(tmp_path,monkeypatch,request,edge,exception):
    before=fdset();f=Fixture(tmp_path,monkeypatch);primary=exception('actual catalog '+edge)
    realopen,realwrite,realchmod,realsync=os.open,os.write,os.fchmod,os.fsync
    target=[];pin=[];fired=[]
    def open(path,flags,*args,**kwargs):
        fd=realopen(path,flags,*args,**kwargs)
        if path=='catalog-000002.json' and flags & os.O_CREAT:
            s=os.fstat(fd);target.append((s.st_dev,s.st_ino));pin.append((f.store.path,f.store.sha256,f.store.sequence))
        return fd
    def invoke(label,fn,fd,*args):
        s=os.fstat(fd)
        if target and (s.st_dev,s.st_ino)==target[0] and label==edge and not fired:
            fired.append(label);raise primary
        return fn(fd,*args)
    monkeypatch.setattr(os,'open',open)
    monkeypatch.setattr(os,'write',lambda fd,*args:invoke('write',realwrite,fd,*args))
    monkeypatch.setattr(os,'fchmod',lambda fd,*args:invoke('chmod',realchmod,fd,*args))
    monkeypatch.setattr(os,'fsync',lambda fd,*args:invoke('fsync',realsync,fd,*args))
    with pytest.raises(exception) as caught:f.history()
    assert caught.value is primary and fired==[edge] and len(target)==1 and len(pin)==1
    assert f.store._poisoned and f.session._poisoned and f.controller._failed
    assert (f.store.path,f.store.sha256,f.store.sequence)==pin[0] and pin[0][2]==1
    assert (n.PROV/'baseline.json').stat().st_nlink==2 and (n.PROV/'.baseline.json.stage').exists()
    assert (f.store.root/'catalog-000002.json').exists() and not n.DATA.exists()
    with pytest.raises(r.RuntimeBlocked) as recovery_refusal:
        c.CatalogStore.load(pin[0][0],expected_sha256=pin[0][1],root=n.PROV,project_root=n.ROOT,lineage_sha256=f.session.lineage)
    assert fdset()==before
    facts(request,marker='baseline.json',catalog_name='catalog-000002.json',edge=edge,original=target[0],fired=fired,predecessor_sequence=1,physical_baseline_pair_retained=True,partial_catalog_retained=True,no_source_namespace=True,explicit_predecessor_refusal=str(recovery_refusal.value))


@pytest.mark.parametrize('attack',['equal_length_baseline','extra_control_object','extra_catalog_object'])
def test_typed_fresh_recovery_retains_rewrite_or_foreign_object(tmp_path,monkeypatch,request,attack):
    before=fdset();f=Fixture(tmp_path,monkeypatch);f.history();pin=(f.store.path,f.store.sha256,f.store.sequence)
    if attack=='equal_length_baseline':
        path=n.PROV/'baseline.json';raw=path.read_bytes();assert b'"eligible"' in raw
        changed=raw.replace(b'"eligible"',b'"ineligib"',1);assert len(changed)==len(raw)
        original=path.stat();path.write_bytes(changed);os.utime(path,ns=(original.st_atime_ns,original.st_mtime_ns))
    elif attack=='extra_control_object':path=n.PROV/'foreign-unbound.json';path.write_bytes(b'foreign synthetic evidence')
    else:path=f.store.root/'foreign-unbound.json';path.write_bytes(b'foreign synthetic evidence')
    retained=hashlib.sha256(path.read_bytes()).hexdigest()
    with pytest.raises((r.RuntimeBlocked,n.GateFailure,j.PairFailure)):f.fresh().execute('recover')
    assert path.exists() and hashlib.sha256(path.read_bytes()).hexdigest()==retained
    assert (f.store.path,f.store.sha256,f.store.sequence)==pin and not n.DATA.exists()
    assert fdset()==before
    facts(request,attack=attack,predecessor_sequence=pin[2],retained_foreign_or_modified=True,no_source_namespace=True)
