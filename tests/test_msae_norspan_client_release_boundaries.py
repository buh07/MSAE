"""Fresh source-free owned-release/admission/entry guard checks."""
import os
from pathlib import Path
import sys
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import prepare_msae_independent_norspan_v1 as p
import msae_norspan_jpc_runtime as r
import msae_jumbo_pair_commit as j

@pytest.mark.parametrize('operation',['descriptor_tree','history'])
@pytest.mark.parametrize('error',[OSError,KeyboardInterrupt])
def test_tree_and_history_primary_retained_all_releases_once(tmp_path,monkeypatch,operation,error):
    (tmp_path/'a').mkdir();(tmp_path/'a/b').mkdir();(tmp_path/'a/b/ordinary.txt').write_bytes(b'x')
    sentinel=tmp_path/'unrelated';sentinel.write_bytes(b'sentinel')
    monkeypatch.setattr(p,'ROOT',tmp_path)
    realopen,realclose,realstat=os.open,os.close,os.stat
    opened=[];closed=[];reused=[];faulted=[];before=set(os.listdir('/proc/self/fd'))
    monitor=os.stat('/proc/self/fd')
    def opened_fd(*args,**kwargs):
        fd=realopen(*args,**kwargs);opened.append(fd);return fd
    def stat(name,*args,**kwargs):
        if name=='ordinary.txt':raise RuntimeError('original-tree-fault')
        return realstat(name,*args,**kwargs)
    def close(fd):
        info=os.fstat(fd);closed.append(fd);realclose(fd)
        # This cell injects tree-unwind faults AFTER original-tree-fault. A new
        # admission-monitor close occurs before that primary; qualify it in its
        # own cell, rather than accidentally changing this cell's firing point.
        if (info.st_dev,info.st_ino)==(monitor.st_dev,monitor.st_ino):return
        faulted.append(fd);reused.append(realopen(sentinel,os.O_RDONLY));raise error('secondary-tree-close-'+str(fd))
    try:
        monkeypatch.setattr(os,'open',opened_fd);monkeypatch.setattr(os,'stat',stat);monkeypatch.setattr(os,'close',close)
        with pytest.raises(RuntimeError,match='original-tree-fault') as caught:
            if operation=='descriptor_tree':p._descriptor_tree(tmp_path/'a')
            else:list(p._history_objects())
        assert set(opened)==set(closed) and len(opened)==len(closed)
        assert faulted and all('secondary-tree-close-'+str(fd) in ' '.join(caught.value.__notes__) for fd in faulted)
        for fd in reused:assert os.pread(fd,20,0)==b'sentinel'
    finally:
        for fd in reused:realclose(fd)
    assert set(os.listdir('/proc/self/fd'))==before

def test_process_fd_admission_counts_existing_unrelated_fds_and_retains(tmp_path):
    sentinel=tmp_path/'unrelated';sentinel.write_bytes(b'x');fds=[]
    with r.reserve_scratch(tmp_path/'lease',authority_sha256='a'*64,entry_lineage_sha256='b'*64) as lease:
        try:
            for _ in range(4096):fds.append(os.open(sentinel,os.O_RDONLY))
            with pytest.raises(r.RuntimeBlocked,match='scratch_fd_admission'):lease.snapshot()
            assert lease.path.exists()
        finally:
            for fd in fds:os.close(fd)

def test_new_recovery_entry_guard_before_any_catalog_read(monkeypatch):
    def poison(*args,**kwargs):raise AssertionError('catalog accessed')
    monkeypatch.setattr(p,'read_bytes_nofollow',poison)
    with pytest.raises(p.GateFailure,match='whole_qualification_pending'):p.cmd_recover(object())
