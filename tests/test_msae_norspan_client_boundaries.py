"""Fresh synthetic FIFO and timestamp-blind regressions, never real data."""
import os
from pathlib import Path
import subprocess
import sys
import select
import time
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import msae_jumbo_pair_commit as j
import msae_norspan_jpc_runtime as r
import acquire_msae_independent_norspan_v1 as a


def _run_fifo_child(argv,tmp_path,*,bootstrap_seconds=30,reader_seconds=3):
    assert 0 < bootstrap_seconds <= 30 and 0 < reader_seconds <= 3
    child=None;primary=None;diagnostics=b'';errors=[]
    stderr=(tmp_path/'child-stderr.log').open('xb+')
    started=time.monotonic()
    try:
        child=subprocess.Popen(argv,cwd=tmp_path,
            env={'PATH':'/usr/bin:/bin','PYTHONDONTWRITEBYTECODE':'1'},
            stdin=subprocess.DEVNULL,stdout=subprocess.PIPE,stderr=stderr,bufsize=0)
        remaining=bootstrap_seconds-(time.monotonic()-started)
        if remaining<=0 or not select.select([child.stdout],[],[],remaining)[0]:
            raise TimeoutError('FIFO bootstrap deadline before READY')
        if os.read(child.stdout.fileno(),64)!=b'READY\n':
            raise RuntimeError('FIFO bootstrap invalid READY')
        output,_=child.communicate(timeout=reader_seconds)
        assert output==b'', 'unexpected reader stdout'
    except BaseException as exc:
        primary=exc
        raise
    finally:
        # Attempt every owned release once; preserve an active primary failure.
        if child is not None:
            try:
                if child.poll() is None:child.kill()
            except BaseException as exc:errors.append(exc)
            try:child.wait()
            except BaseException as exc:errors.append(exc)
            try:
                if child.stdout is not None and not child.stdout.closed:child.stdout.close()
            except BaseException as exc:errors.append(exc)
        try:
            stderr.seek(0);diagnostics=stderr.read(1024**2+1)
            if len(diagnostics)>1024**2:raise RuntimeError('FIFO diagnostic admission limit')
        except BaseException as exc:errors.append(exc)
        try:stderr.close()
        except BaseException as exc:errors.append(exc)
        if errors:
            if primary is not None:
                for error in errors:primary.add_note('FIFO cleanup: '+repr(error))
            else:
                for error in errors[1:]:errors[0].add_note('FIFO cleanup: '+repr(error))
                raise errors[0]
    assert child.returncode==0,diagnostics


@pytest.mark.parametrize('phase',['bootstrap','reader','marker'])
def test_fifo_phase_failure_is_not_rejection_and_owned_child_is_reaped(tmp_path,phase):
    before=set(os.listdir('/proc/self/fd'))
    children=Path('/proc/self/task/'+str(os.getpid())+'/children')
    initial=children.read_text()
    code="import time;time.sleep(20)" if phase=='bootstrap' else (
        "import time;print('READY',flush=True);time.sleep(20)" if phase=='reader' else
        "print('INVALID',flush=True)")
    error=TimeoutError if phase=='bootstrap' else subprocess.TimeoutExpired if phase=='reader' else RuntimeError
    with pytest.raises(error):
        _run_fifo_child([sys.executable,'-c',code],tmp_path,bootstrap_seconds=.2,reader_seconds=.2)
    assert children.read_text()==initial and set(os.listdir('/proc/self/fd'))==before
    assert (tmp_path/'child-stderr.log').exists()

@pytest.mark.parametrize('reader',['stream','bytes','prefix','sparse'])
def test_actual_fifo_rejected_without_blocking(tmp_path,reader):
    fifo=tmp_path/'fifo';os.mkfifo(fifo)
    repo=tmp_path/'repo';repo.mkdir();(repo/'.git').mkdir()
    for name in a.FILES:(repo/name).write_bytes(b'x')
    (repo/a.FILES[0]).unlink();os.mkfifo(repo/a.FILES[0]) # disposable synthetic setup only
    code="""import sys
from pathlib import Path
sys.path.insert(0,sys.argv[1])
import prepare_msae_independent_norspan_v1 as p
import acquire_msae_independent_norspan_v1 as a
kind=sys.argv[2];path=Path(sys.argv[3]);repo=Path(sys.argv[4])
print('READY',flush=True)
try:
    if kind=='stream':p.stream_file_digest(path)
    elif kind=='bytes':p.read_bytes_nofollow(path)
    elif kind=='prefix':p.read_prefix_nofollow(path,2)
    else:a.read_sparse_files(repo)
except p.GateFailure:sys.exit(0)
sys.exit(4)
"""
    _run_fifo_child([sys.executable,'-c',code,str(Path(__file__).resolve().parents[1]/'scripts'),reader,str(fifo),str(repo)],tmp_path)
    assert fifo.exists()

@pytest.mark.parametrize('boundary',['create','open_false','open_true','verify_false','verify_true','validate_false','validate_true'])
def test_last_existing_pair_check_same_length_mutation_with_unchanged_metadata(tmp_path,monkeypatch,boundary):
    path=tmp_path/'record';receipt=None
    if boundary!='create':receipt=j.create_pair(path,b'alpha',mode=0o600)
    realcheck,realstat,realfstat=j._check,os.stat,os.fstat
    calls=[];fired=[];cached={}
    checks=3 if boundary=='create' else 2 if boundary.endswith('true') else 1
    def check(parent,owned,expected,*,complete):
        calls.append(True)
        result=realcheck(parent,owned,expected,complete=complete)
        if len(calls)==checks:
            cached['st']=realfstat(owned);cached['fd']=owned
            path.write_bytes(b'xxxxx')
            fired.append(True)
        return result
    def fstat(fd):return cached['st'] if cached and fd==cached['fd'] else realfstat(fd)
    def stat(name,*args,**kwargs):
        if cached and name in {'record','.record.stage'} and kwargs.get('dir_fd') is not None:return cached['st']
        return realstat(name,*args,**kwargs)
    pair=j.open_owned_pair(path,receipt) if boundary.startswith('validate') else None
    monkeypatch.setattr(j,'_check',check);monkeypatch.setattr(os,'stat',stat);monkeypatch.setattr(os,'fstat',fstat)
    try:
        with pytest.raises(j.PairFailure):
            if boundary=='create':j.create_pair(path,b'alpha',mode=0o600)
            elif boundary.startswith('open'):
                with j.open_owned_pair(path,receipt,durable=boundary.endswith('true')):pass
            elif boundary.startswith('verify'):j.verify_pair(path,receipt,durable=boundary.endswith('true'))
            else:pair.validate(durable=boundary.endswith('true'))
        assert fired==[True] and path.read_bytes()==b'xxxxx'
    finally:
        if pair is not None:pair.close()

def test_late_scratch_foreign_name_with_unchanged_directory_metadata(tmp_path,monkeypatch):
    with r.reserve_scratch(tmp_path/'lease',authority_sha256='a'*64,entry_lineage_sha256='b'*64) as lease:
        repo=lease.path/'repo';repo.mkdir(mode=0o700);(repo/'one').write_bytes(b'aaaa');(repo/'two').write_bytes(b'zzzz')
        realstat,realfstat,realvalidate=os.stat,os.fstat,r._Directory.validate
        armed=[];hits=[];fired=[];home_before=(lease.path/'home').stat()
        def validate(self,names=None,*,durable=False):
            result=realvalidate(self,names,durable=durable)
            if self is lease and names=={'home','repo'}:armed.append(True)
            return result
        def stat(name,*args,**kwargs):
            result=realstat(name,*args,**kwargs)
            if armed and name=='two':
                hits.append(True)
                if len(hits)==2:(lease.path/'home'/'foreign').write_bytes(b'evidence');fired.append(True)
            if name=='home' and kwargs.get('dir_fd') is not None:return home_before
            return result
        def fstat(fd):
            if os.readlink('/proc/self/fd/'+str(fd))==str(lease.path/'home'):return home_before
            return realfstat(fd)
        monkeypatch.setattr(r._Directory,'validate',validate);monkeypatch.setattr(os,'stat',stat);monkeypatch.setattr(os,'fstat',fstat)
        with pytest.raises((r.RuntimeBlocked,j.PairFailure)):lease.snapshot(file_bytes=4,total_bytes=8,entries=10)
        assert fired==[True] and (lease.path/'home'/'foreign').read_bytes()==b'evidence'
