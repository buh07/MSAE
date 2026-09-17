from __future__ import annotations
import dataclasses
import hashlib
import os
from pathlib import Path
import json
import selectors
import signal
import stat
import subprocess
import sys

import pytest
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import msae_jumbo_pair_commit as j


def invoke(root, *, mode=0o600):
    return j.create_pair(root / 'record', b'alpha', mode=mode)


@pytest.mark.parametrize('mode', [0o444, 0o600, 0o644])
def test_native_jumbo_pair_has_exact_owned_aliases_and_bytes(tmp_path, mode):
    before=set(os.listdir('/proc/self/fd'))
    receipt=invoke(tmp_path, mode=mode)
    assert (tmp_path/'record').read_bytes()==b'alpha'
    assert (tmp_path/'.record.stage').read_bytes()==b'alpha'
    assert (tmp_path/'record').stat().st_ino==(tmp_path/'.record.stage').stat().st_ino
    assert (tmp_path/'record').stat().st_nlink==2
    assert stat.S_IMODE((tmp_path/'record').stat().st_mode)==mode
    assert j.verify_pair(tmp_path/'record', receipt, durable=True)==receipt
    assert set(os.listdir('/proc/self/fd'))==before
    with pytest.raises(j.PairFailure): invoke(tmp_path)


def test_visible_pair_alone_is_not_a_manifest_or_consumption_capability(tmp_path):
    invoke(tmp_path)
    with pytest.raises(TypeError): j.verify_pair(tmp_path/'record')


@pytest.mark.parametrize('object_name', ['record','.record.stage','.record.building'])
def test_preexisting_obstruction_preserved_without_creating_other_names(tmp_path, object_name):
    p=tmp_path/object_name;p.write_bytes(b'foreign')
    names=set(os.listdir(tmp_path))
    with pytest.raises(j.PairFailure): invoke(tmp_path)
    assert p.read_bytes()==b'foreign' and set(os.listdir(tmp_path))==names


@pytest.mark.parametrize('attack', ['same_inode_bytes','substituted_stage','racing_final','third_link'])
def test_precise_prelink_attacks_never_succeed_or_erase_foreign_evidence(tmp_path,monkeypatch,attack):
    original=j._insert_final
    observed=[]
    before=set(os.listdir('/proc/self/fd'))
    def insert(fd,stage,final):
        s=os.stat(stage,dir_fd=fd,follow_symlinks=False)
        expected=j.PairReceipt(s.st_dev,s.st_ino,0o600,5,hashlib.sha256(b'alpha').hexdigest(),stage,final)
        observed.append(expected)
        if attack=='same_inode_bytes':
            f=os.open(stage,os.O_WRONLY,dir_fd=fd)
            try: os.write(f,b'xxxxx');os.fsync(f)
            finally:os.close(f)
        elif attack=='substituted_stage':
            os.rename(stage,'retained-original',src_dir_fd=fd,dst_dir_fd=fd)
            f=os.open(stage,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600,dir_fd=fd)
            try:os.write(f,b'foreign-stage')
            finally:os.close(f)
        elif attack=='racing_final':
            f=os.open(final,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600,dir_fd=fd)
            try:os.write(f,b'foreign-final')
            finally:os.close(f)
        original(fd,stage,final)
        if attack=='third_link':os.link(stage,'third-alias',src_dir_fd=fd,dst_dir_fd=fd)
    monkeypatch.setattr(j,'_insert_final',insert)
    with pytest.raises((j.PairFailure,FileExistsError)):invoke(tmp_path)
    assert observed and set(os.listdir('/proc/self/fd'))==before
    with pytest.raises(j.PairFailure):j.verify_pair(tmp_path/'record',observed[0])
    if attack=='substituted_stage':
        assert (tmp_path/'record').read_bytes()==b'foreign-stage'
        assert (tmp_path/'.record.stage').read_bytes()==b'foreign-stage'
        assert (tmp_path/'retained-original').read_bytes()==b'alpha'
    elif attack=='racing_final': assert (tmp_path/'record').read_bytes()==b'foreign-final'
    elif attack=='third_link': assert (tmp_path/'third-alias').exists()


@pytest.mark.parametrize('stage',['open','chmod','write','file_fsync','prelink_parent_fsync','link','postlink_parent_fsync'])
@pytest.mark.parametrize('failure',[OSError,KeyboardInterrupt])
def test_faults_propagate_preserve_obstruction_close_owned_descriptors(tmp_path,monkeypatch,stage,failure):
    originals={x:getattr(j.os,x) for x in ('open','fchmod','write','fsync')}
    insert=j._insert_final; fired=[];before=set(os.listdir('/proc/self/fd'))
    operation='fsync' if 'fsync' in stage else ('fchmod' if stage=='chmod' else stage)
    def fault(*args,**kwargs):
        eligible=not fired
        if operation=='open':eligible &= bool(args[1]&os.O_CREAT)
        if operation=='fsync':
            s=os.fstat(args[0])
            eligible &= stat.S_ISREG(s.st_mode) if stage=='file_fsync' else stat.S_ISDIR(s.st_mode)
            if stage=='prelink_parent_fsync':eligible &= not (tmp_path/'record').exists()
            if stage=='postlink_parent_fsync':eligible &= (tmp_path/'record').exists()
        if eligible:
            fired.append(stage);raise failure('synthetic_pair_fault')
        return originals[operation](*args,**kwargs)
    if operation=='link':
        def interrupted(*a):fired.append(stage);raise failure('synthetic_pair_fault')
        monkeypatch.setattr(j,'_insert_final',interrupted)
    else:monkeypatch.setattr(j.os,operation,fault)
    with pytest.raises(failure,match='synthetic_pair_fault'):invoke(tmp_path)
    assert fired==[stage] and set(os.listdir('/proc/self/fd'))==before
    if operation=='link':monkeypatch.setattr(j,'_insert_final',insert)
    else:monkeypatch.setattr(j.os,operation,originals[operation])
    if (tmp_path/'.record.stage').exists():
        with pytest.raises(j.PairFailure):invoke(tmp_path)


def test_short_writes_are_completed_and_zero_write_is_preserved(tmp_path,monkeypatch):
    original=j.os.write
    monkeypatch.setattr(j.os,'write',lambda fd,p:original(fd,p[:1]))
    receipt=invoke(tmp_path)
    assert j.verify_pair(tmp_path/'record',receipt)==receipt
    other=tmp_path/'other';other.mkdir()
    monkeypatch.setattr(j.os,'write',lambda *a:0)
    with pytest.raises(j.PairFailure):invoke(other)
    assert (other/'.record.stage').exists() and not (other/'record').exists()


def test_publisher_has_no_unlink_or_overwrite_rename_fallback(tmp_path,monkeypatch):
    def forbidden(*a,**kw):pytest.fail('publisher attempted destructive operation')
    for name in ('unlink','rename','replace'):monkeypatch.setattr(j.os,name,forbidden)
    receipt=invoke(tmp_path)
    assert j.verify_pair(tmp_path/'record',receipt)==receipt


def test_late_legacy_building_extra_rejects_and_preserves_pair(tmp_path,monkeypatch):
    original=j.os.fsync;fired=[]
    def fsync(fd):
        result=original(fd)
        if stat.S_ISDIR(os.fstat(fd).st_mode) and (tmp_path/'record').exists() and not fired:
            fired.append(True);(tmp_path/'.record.building').write_bytes(b'foreign-extra')
        return result
    monkeypatch.setattr(j.os,'fsync',fsync)
    with pytest.raises(j.PairFailure):invoke(tmp_path)
    assert fired and (tmp_path/'.record.building').read_bytes()==b'foreign-extra'
    assert (tmp_path/'record').read_bytes()==b'alpha' and (tmp_path/'.record.stage').exists()


def test_pinned_nonleaf_ancestor_exchange_rejects_without_leak(tmp_path,monkeypatch):
    nested=tmp_path/'parent'/'nested';nested.mkdir(parents=True)
    original=j._insert_final;changed=[];before=set(os.listdir('/proc/self/fd'))
    def exchange(fd,stage,final):
        if not changed:
            changed.append(True);(tmp_path/'parent').rename(tmp_path/'retained-parent');nested.mkdir(parents=True)
        return original(fd,stage,final)
    monkeypatch.setattr(j,'_insert_final',exchange)
    with pytest.raises(j.PairFailure):invoke(nested)
    assert (tmp_path/'retained-parent/nested/.record.stage').exists()
    assert set(os.listdir('/proc/self/fd'))==before


def test_native_eight_process_pair_race_exactly_one_winner(tmp_path):
    code='''import sys
sys.path.insert(0,sys.argv[1])
import msae_jumbo_pair_commit as j
from pathlib import Path
try:j.create_pair(Path(sys.argv[2]),b"race",mode=0o600)
except (j.PairFailure,FileExistsError):sys.exit(3)
'''
    ps=[subprocess.Popen([sys.executable,'-c',code,str(Path(j.__file__).parent),str(tmp_path/'record')],stdout=subprocess.PIPE,stderr=subprocess.PIPE,env={**os.environ,'PYTHONDONTWRITEBYTECODE':'1'}) for _ in range(8)]
    statuses=[]
    for p in ps:
        out,err=p.communicate(timeout=30);statuses.append(p.returncode);assert not out and not err
    assert statuses.count(0)==1 and statuses.count(3)==7
    assert (tmp_path/'record').read_bytes()==b'race' and (tmp_path/'record').stat().st_nlink==2


@pytest.mark.parametrize('field,value',[('mode',True),('byte_count',True),('sha256','wrong'),('inode',-1)])
def test_receipt_schema_drift_rejected(tmp_path,field,value):
    receipt=invoke(tmp_path)
    with pytest.raises(j.PairFailure):j.verify_pair(tmp_path/'record',dataclasses.replace(receipt,**{field:value}))


def test_outside_jumbo_is_refused_before_creation():
    with pytest.raises(j.PairFailure):j.create_pair(Path('/tmp/forbidden-jpc-output'),b'alpha',mode=0o600)


def test_diagnostic_size_floor_is_derived_not_false_positive(tmp_path):
    import diagnose_msae_jumbo_nfs_v1 as d
    result=d.link_case(tmp_path/'diagnostic',held=False)
    assert result['status']=='pass'
    assert result['events'][-1]['final']['size']==len(b'fixed synthetic diagnostic payload\n')


@pytest.mark.parametrize('boundary',['write','chmod','file_fsync','prelink_parent_fsync','link','postlink_parent_fsync'])
def test_actual_sigkill_retains_initiated_pair_and_never_recreates(tmp_path,boundary):
    # Real process termination, not a caught exception. The parent's expected
    # receipt is synthetic test authority, NOT production recovery authorization.
    code='''import json,os,signal,stat,sys
from pathlib import Path
sys.path.insert(0,sys.argv[1])
import msae_jumbo_pair_commit as j
path=Path(sys.argv[2]);boundary=sys.argv[3]
operation='fsync' if 'fsync' in boundary else ('fchmod' if boundary=='chmod' else boundary)
original=j._insert_final if operation=='link' else getattr(j.os,operation)
def wrapper(*a,**kw):
    result=original(*a,**kw)
    eligible=True
    if operation=='fsync':
        s=os.fstat(a[0]);eligible=stat.S_ISREG(s.st_mode) if boundary=='file_fsync' else stat.S_ISDIR(s.st_mode)
        if boundary=='prelink_parent_fsync':eligible &= not path.exists()
        if boundary=='postlink_parent_fsync':eligible &= path.exists()
    if eligible:
        s=(path.parent/('.'+path.name+'.stage')).stat()
        print(json.dumps({'device':s.st_dev,'inode':s.st_ino}),flush=True)
        signal.pause()
    return result
if operation=='link':j._insert_final=wrapper
else:setattr(j.os,operation,wrapper)
j.create_pair(path,b'alpha',mode=0o600)
'''
    p=subprocess.Popen([sys.executable,'-c',code,str(Path(j.__file__).parent),str(tmp_path/'record'),boundary],stdout=subprocess.PIPE,stderr=subprocess.PIPE,env={**os.environ,'PYTHONDONTWRITEBYTECODE':'1'})
    selector=selectors.DefaultSelector()
    try:
        selector.register(p.stdout,selectors.EVENT_READ)
        assert selector.select(timeout=30),'child did not reach declared boundary'
        observed=json.loads(p.stdout.readline())
        p.kill();out,err=p.communicate(timeout=30)
        assert p.returncode==-signal.SIGKILL and not out and not err
    finally:
        selector.close()
        if p.poll() is None:p.kill()
        p.wait(timeout=30)
        p.stdout.close();p.stderr.close()
    names=set(os.listdir(tmp_path));assert '.record.stage' in names
    with pytest.raises(j.PairFailure):invoke(tmp_path)
    assert set(os.listdir(tmp_path))==names
    expected=j.PairReceipt(observed['device'],observed['inode'],0o600,5,hashlib.sha256(b'alpha').hexdigest(),'.record.stage','record')
    if boundary in {'link','postlink_parent_fsync'}:
        assert j.verify_pair(tmp_path/'record',expected,durable=True)==expected
    else:
        with pytest.raises(j.PairFailure):j.verify_pair(tmp_path/'record',expected,durable=True)


@pytest.mark.parametrize('kind',['file','parent'])
@pytest.mark.parametrize('failure',[OSError,KeyboardInterrupt])
def test_current_custody_durability_failure_propagates_closes_and_retains(tmp_path,monkeypatch,kind,failure):
    receipt=invoke(tmp_path);before=set(os.listdir('/proc/self/fd'));original=j.os.fsync
    def fsync(fd):
        s=os.fstat(fd)
        if (stat.S_ISREG(s.st_mode) if kind=='file' else stat.S_ISDIR(s.st_mode)):
            raise failure('current_durability_fault')
        return original(fd)
    monkeypatch.setattr(j.os,'fsync',fsync)
    with pytest.raises(failure,match='current_durability_fault'):j.verify_pair(tmp_path/'record',receipt,durable=True)
    assert set(os.listdir('/proc/self/fd'))==before
    assert set(os.listdir(tmp_path))=={'record','.record.stage'}


@pytest.mark.parametrize('mutation',['stage_absent','final_absent','wrong_mode','same_inode_wrong_bytes','unknown_link','stage_directory','final_symlink'])
def test_consumer_rejects_changed_aliases_before_approval(tmp_path,mutation):
    receipt=invoke(tmp_path);stage=tmp_path/'.record.stage';final=tmp_path/'record'
    if mutation=='stage_absent':stage.rename(tmp_path/'retained-stage')
    elif mutation=='final_absent':final.rename(tmp_path/'retained-final')
    elif mutation=='wrong_mode':final.chmod(0o644)
    elif mutation=='same_inode_wrong_bytes':final.write_bytes(b'xxxxx')
    elif mutation=='unknown_link':os.link(final,tmp_path/'foreign-alias')
    elif mutation=='stage_directory':stage.rename(tmp_path/'retained-stage');stage.mkdir()
    elif mutation=='final_symlink':final.rename(tmp_path/'retained-final');final.symlink_to('retained-final')
    names=set(os.listdir(tmp_path));before=set(os.listdir('/proc/self/fd'))
    with pytest.raises((j.PairFailure,OSError)):j.verify_pair(final,receipt,durable=True)
    assert set(os.listdir(tmp_path))==names and set(os.listdir('/proc/self/fd'))==before


@pytest.mark.parametrize('kind',['pathlike','string_subclass'])
def test_receipt_alias_must_be_literal_string_not_equality_path_spoof(tmp_path,kind):
    receipt=invoke(tmp_path)
    (tmp_path/'.record.stage').rename(tmp_path/'foreign-stage')
    class Spoof:
        def __eq__(self,other):return True
        def __fspath__(self):return 'foreign-stage'
    class StringSpoof(str):
        def __eq__(self,other):return True
        def __ne__(self,other):return False
    alias=Spoof() if kind=='pathlike' else StringSpoof('foreign-stage')
    with pytest.raises(j.PairFailure,match='receipt_schema'):
        j.verify_pair(tmp_path/'record',dataclasses.replace(receipt,stage_name=alias),durable=True)


@pytest.mark.parametrize('function',['create','verify'])
@pytest.mark.parametrize('kind',['writer','ancestor'])
@pytest.mark.parametrize('failure',[OSError,KeyboardInterrupt])
def test_close_error_after_linux_release_closes_every_other_fd_once(tmp_path,monkeypatch,function,kind,failure):
    receipt=invoke(tmp_path) if function=='verify' else None
    before=set(os.listdir('/proc/self/fd'));original=j.os.close;fired=[];called=[]
    def close(fd):
        s=os.fstat(fd);called.append(fd);original(fd)
        if not fired and (stat.S_ISREG(s.st_mode) if kind=='writer' else stat.S_ISDIR(s.st_mode)):
            fired.append(fd);raise failure('linux_close_error_after_release')
    monkeypatch.setattr(j.os,'close',close)
    with pytest.raises(failure,match='linux_close_error_after_release'):
        if function=='create':invoke(tmp_path)
        else:j.verify_pair(tmp_path/'record',receipt,durable=True)
    assert fired and len(called)==len(set(called))
    assert set(os.listdir('/proc/self/fd'))==before
    assert set(os.listdir(tmp_path))=={'record','.record.stage'}


@pytest.mark.parametrize('failure',[OSError,KeyboardInterrupt])
def test_combined_ancestor_open_and_close_failures_preserve_primary_and_close_chain(tmp_path,monkeypatch,failure):
    nested=tmp_path/'break-parent'/'nested';nested.mkdir(parents=True)
    before=set(os.listdir('/proc/self/fd'));open_=j.os.open;close_=j.os.close;fired=[]
    def open_fault(path,*args,**kwargs):
        if path=='break-parent':raise OSError('primary_ancestor_open_failure')
        return open_(path,*args,**kwargs)
    def close_fault(fd):
        close_(fd)
        if not fired:fired.append(fd);raise failure('secondary_close_failure')
    monkeypatch.setattr(j.os,'open',open_fault);monkeypatch.setattr(j.os,'close',close_fault)
    with pytest.raises(OSError,match='primary_ancestor_open_failure') as caught:invoke(nested)
    assert fired and set(os.listdir('/proc/self/fd'))==before
    assert not list(nested.iterdir())
    assert any('secondary_close_failure' in note for note in getattr(caught.value,'__notes__',[]))


@pytest.mark.parametrize('function',['create','verify'])
def test_unrelated_caller_exception_does_not_swallow_close_failure(tmp_path,monkeypatch,function):
    receipt=invoke(tmp_path) if function=='verify' else None
    original=j.os.close;fired=[];before=set(os.listdir('/proc/self/fd'))
    def close(fd):
        original(fd)
        if not fired:fired.append(fd);raise OSError('own_close_failure')
    monkeypatch.setattr(j.os,'close',close)
    try:raise ValueError('unrelated_caller_exception')
    except ValueError:
        with pytest.raises(OSError,match='own_close_failure'):
            if function=='create':invoke(tmp_path)
            else:j.verify_pair(tmp_path/'record',receipt,durable=True)
    assert fired and set(os.listdir('/proc/self/fd'))==before
