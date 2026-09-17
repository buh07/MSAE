"""Synthetic Jumbo-only client defects; no production/source authorization."""
import os
from pathlib import Path
import signal
import sys
import pytest
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import msae_norspan_jpc_runtime as r
import msae_jumbo_pair_commit as j
import acquire_msae_independent_norspan_v1 as a
import prepare_msae_independent_norspan_v1 as p

def fds(): return set(os.listdir('/proc/self/fd'))

@pytest.mark.parametrize('kind', ['objects', 'depth'])
def test_actual_scratch_admission_bound_preserves_every_object_and_fds(tmp_path, kind):
    before = fds()
    with r.reserve_scratch(tmp_path/'lease', authority_sha256='a'*64, entry_lineage_sha256='b'*64) as lease:
        repo=lease.path/'repo'; repo.mkdir(mode=0o700)
        if kind=='objects':
            for n in range(1025): (repo/str(n)).write_bytes(b'x')
        else:
            leaf=repo
            for n in range(66): leaf=leaf/'d'; leaf.mkdir(mode=0o700)
        with pytest.raises(r.RuntimeBlocked, match='scratch_(object|depth)_admission'):
            lease.snapshot()
        if kind=='objects': assert len(os.listdir(repo))==1025
        else: assert leaf.is_dir()
    assert fds()==before

def test_scanner_uses_incremental_names_closes_on_overcap(tmp_path, monkeypatch):
    with r.reserve_scratch(tmp_path/'lease', authority_sha256='a'*64, entry_lineage_sha256='b'*64) as lease:
        repo=lease.path/'repo'; repo.mkdir(mode=0o700)
        for n in range(1025): (repo/str(n)).write_bytes(b'x')
        actual=os.scandir; counts=[]; closed=[]
        class Iterator:
            def __init__(self, fd): self.inner=actual(fd); self.n=0
            def __iter__(self): return self
            def __next__(self): self.n+=1; return next(self.inner)
            def close(self): counts.append(self.n); closed.append(True); self.inner.close()
        monkeypatch.setattr(os,'scandir',Iterator)
        before=fds()
        with pytest.raises(r.RuntimeBlocked, match='scratch_object_admission'): lease.snapshot()
        assert closed and max(counts)<=1025 and fds()==before

@pytest.mark.parametrize('reader', ['stream', 'bytes', 'prefix'])
@pytest.mark.parametrize('error', [OSError, KeyboardInterrupt])
def test_reader_primary_and_every_owned_release(tmp_path, monkeypatch, reader, error):
    file=tmp_path/'ordinary'; file.write_bytes(b'data'); file.chmod(0o644)
    realopen,realclose,realread=os.open,os.close,os.read
    monitor=os.stat('/proc/self/fd')
    opened=[]; closed=[]; monitors=[]; fired=[]
    def is_monitor(fd):
        observed=os.fstat(fd)
        return (observed.st_dev,observed.st_ino)==(monitor.st_dev,monitor.st_ino)
    def opened_fd(*args,**kwargs):
        fd=realopen(*args,**kwargs)
        if not is_monitor(fd):opened.append(fd)
        return fd
    def close(fd):
        admission=is_monitor(fd)
        if admission:
            realclose(fd);monitors.append(fd);return
        closed.append(fd); realclose(fd); raise error('secondary-'+str(fd))
    def read(*args,**kwargs):
        fired.append(True);raise RuntimeError('original-read-fault')
    before=fds()
    monkeypatch.setattr(os,'open',opened_fd); monkeypatch.setattr(os,'close',close); monkeypatch.setattr(os,'read',read)
    with pytest.raises(RuntimeError, match='original-read-fault') as caught:
        if reader=='stream': p.stream_file_digest(file)
        elif reader=='bytes': p.read_bytes_nofollow(file)
        else: p.read_prefix_nofollow(file,2)
    assert set(opened)==set(closed) and len(closed)==len(opened) and fds()==before
    assert monitors and fired==[True]
    assert all('secondary-'+str(fd) in ' '.join(caught.value.__notes__) for fd in opened)

@pytest.mark.parametrize('fault', ['register', 'limit'])
def test_supervisor_attempts_all_independent_releases_and_keeps_primary(tmp_path, monkeypatch, fault):
    calls=[]
    class Pipe:
        def __init__(self, name): self.name=name; self.fd=os.open(tmp_path/'file',os.O_RDONLY)
        def fileno(self): return self.fd
        def close(self): calls.append(self.name); os.close(self.fd); raise OSError(self.name+'-close')
    class Proc:
        pid=99999999; returncode=None
        def __init__(self): self.stdout=Pipe('stdout'); self.stderr=Pipe('stderr')
        def poll(self): return None
        def wait(self, timeout=None): calls.append('wait'); self.returncode=-9; return -9
    class Selector:
        def register(self,*args):
            if fault=='register': raise RuntimeError('original-register')
        def get_map(self): return {'x':True}
        def select(self,*args): return []
        def close(self): calls.append('selector'); raise OSError('selector-close')
    (tmp_path/'file').write_bytes(b'x')
    before=fds()
    monkeypatch.setattr(a.subprocess,'Popen',lambda *args,**kwargs:Proc())
    monkeypatch.setattr(a.selectors,'DefaultSelector',Selector)
    monkeypatch.setattr(a.os,'waitid',lambda *args:None)
    def kill(*args): calls.append('kill'); raise KeyboardInterrupt('kill-fault')
    monkeypatch.setattr(a.os,'killpg',kill)
    expected=RuntimeError if fault=='register' else a.SupervisionFailure
    with pytest.raises(expected) as caught: a.run(['synthetic'],env={},timeout_seconds=.001)
    assert calls==['kill','wait','selector','stdout','stderr'] and fds()==before
    assert all(x in ' '.join(caught.value.__notes__) for x in ['kill-fault','selector-close','stdout-close','stderr-close'])
    assert caught.value.cleanup_complete is False

@pytest.mark.parametrize('kind', ['success','stdout','stderr','timeout','descendant'])
def test_real_child_supervision_without_source(tmp_path, kind):
    code={'success':"import sys;sys.stdout.write('ok');sys.stderr.write('err')",
          'stdout':"import sys;sys.stdout.write('x'*10000)",
          'stderr':"import sys;sys.stderr.write('x'*10000)",
          'timeout':"import time;time.sleep(20)",
          'descendant':"import os,time;pid=os.fork();time.sleep(20) if pid==0 else None"}[kind]
    before=fds()
    argv=[sys.executable,'-c',code]
    if kind=='success': assert a.run(argv,env={'PATH':'/usr/bin:/bin'},cwd=tmp_path)==(b'ok',b'err',0)
    else:
        with pytest.raises(a.SupervisionFailure) as caught:
            a.run(argv,env={'PATH':'/usr/bin:/bin'},cwd=tmp_path,timeout_seconds=.1,stdout_limit_bytes=32,stderr_limit_bytes=32)
        assert caught.value.cleanup_complete is True
        assert len(caught.value.stdout)<=32 and len(caught.value.stderr)<=32
    assert fds()==before

@pytest.mark.parametrize('kind', ['file','total'])
def test_sparse_read_budgets_before_and_during_read(tmp_path, kind):
    repo=tmp_path/'repo';repo.mkdir();(repo/'.git').mkdir()
    for name in a.FILES: (repo/name).write_bytes(b'1234')
    before=fds()
    with pytest.raises(p.GateFailure,match='sparse_(file|total)_budget'):
        a.read_sparse_files(repo,file_bytes=3 if kind=='file' else 4,total_bytes=16 if kind=='file' else 7)
    assert fds()==before and all((repo/name).read_bytes()==b'1234' for name in a.FILES)
