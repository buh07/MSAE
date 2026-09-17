# Maintained copy of retained independent synthetic matrix; original unchanged.
from __future__ import annotations
import dataclasses
import os
from pathlib import Path
import stat
import sys
import pytest
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import msae_jumbo_pair_commit as j


def fds():
    return set(os.listdir('/proc/self/fd'))


def invoke(root):
    return j.create_pair(root/'record', b'alpha', mode=0o600)


@pytest.mark.parametrize('failure', [OSError, KeyboardInterrupt])
def test_second_publisher_file_fsync_failure(tmp_path, monkeypatch, failure):
    before=fds(); original=j.os.fsync; count=[]
    def fsync(fd):
        if stat.S_ISREG(os.fstat(fd).st_mode):
            count.append(fd)
            if len(count)==2: raise failure('second_writer_fsync')
        return original(fd)
    monkeypatch.setattr(j.os, 'fsync', fsync)
    with pytest.raises(failure, match='second_writer_fsync'): invoke(tmp_path)
    assert len(count)==2 and fds()==before
    assert set(os.listdir(tmp_path))=={'.record.stage','record'}
    assert (tmp_path/'record').read_bytes()==b'alpha'


@pytest.mark.parametrize('function,boundary', [('create',1),('create',2),('create',3),('verify',1),('verify',2)])
@pytest.mark.parametrize('failure',[OSError,KeyboardInterrupt])
def test_each_hashing_boundary_error_closes_preserves(tmp_path,monkeypatch,function,boundary,failure):
    receipt=invoke(tmp_path) if function=='verify' else None
    before=fds(); original=j.os.pread; count=[]
    def pread(fd,size,offset):
        if offset==0:
            count.append(fd)
            if len(count)==boundary: raise failure('hashing_boundary_fault')
        return original(fd,size,offset)
    monkeypatch.setattr(j.os,'pread',pread)
    with pytest.raises(failure,match='hashing_boundary_fault'):
        if function=='create':invoke(tmp_path)
        else:j.verify_pair(tmp_path/'record',receipt,durable=True)
    assert len(count)==boundary and fds()==before
    assert set(os.listdir(tmp_path))==({'.record.stage'} if function=='create' and boundary==1 else {'.record.stage','record'})


@pytest.mark.parametrize('function',['create','verify'])
@pytest.mark.parametrize('mutation',['bytes','extra_alias','stage_rename','final_rename','chmod','ancestor_exchange','building'])
def test_custody_mutation_after_terminal_parent_fsync_is_rejected(tmp_path,monkeypatch,function,mutation):
    nested=tmp_path/'parent'/'nested';nested.mkdir(parents=True)
    receipt=invoke(nested) if function=='verify' else None
    before=fds();original=j.os.fsync;fired=[]
    def fsync(fd):
        result=original(fd)
        if stat.S_ISDIR(os.fstat(fd).st_mode) and (nested/'record').exists() and not fired:
            fired.append(fd)
            if mutation=='bytes':(nested/'record').write_bytes(b'xxxxx')
            elif mutation=='extra_alias':os.link(nested/'record',nested/'foreign-alias')
            elif mutation=='stage_rename':(nested/'.record.stage').rename(nested/'retained-stage')
            elif mutation=='final_rename':(nested/'record').rename(nested/'retained-final')
            elif mutation=='chmod':(nested/'record').chmod(0o644)
            elif mutation=='ancestor_exchange':
                (tmp_path/'parent').rename(tmp_path/'retained-parent');nested.mkdir(parents=True)
            elif mutation=='building':(nested/'.record.building').write_bytes(b'foreign')
        return result
    monkeypatch.setattr(j.os,'fsync',fsync)
    with pytest.raises(j.PairFailure):
        if function=='create':invoke(nested)
        else:j.verify_pair(nested/'record',receipt,durable=True)
    assert fired and fds()==before
    retained=tmp_path/'retained-parent'/'nested' if mutation=='ancestor_exchange' else nested
    assert len(list(retained.iterdir()))>=2


@pytest.mark.parametrize('field',['stage_name','final_name'])
@pytest.mark.parametrize('kind',['pathlike','str_subclass'])
def test_literal_name_schema_both_fields(tmp_path,field,kind):
    receipt=invoke(tmp_path);before=fds()
    class Spoof:
        def __eq__(self,other):return True
        def __ne__(self,other):return False
        def __fspath__(self):return 'foreign-alias'
    class SpoofStr(str):
        def __eq__(self,other):return True
        def __ne__(self,other):return False
    name=Spoof() if kind=='pathlike' else SpoofStr('foreign-alias')
    with pytest.raises(j.PairFailure,match='receipt_schema'):
        j.verify_pair(tmp_path/'record',dataclasses.replace(receipt,**{field:name}),durable=True)
    assert fds()==before


@pytest.mark.parametrize('failure',[OSError,KeyboardInterrupt])
def test_pinned_parent_constructor_failure_and_cleanup_fault(tmp_path,monkeypatch,failure):
    before=fds();closed=[];original=j.os.close
    def constructor(*a):raise j.PairFailure('constructor_primary')
    def close(fd):
        closed.append(fd);original(fd)
        if len(closed)<=2:raise failure('constructor_secondary')
    monkeypatch.setattr(j,'_PinnedParent',constructor);monkeypatch.setattr(j.os,'close',close)
    with pytest.raises(j.PairFailure,match='constructor_primary') as caught:invoke(tmp_path)
    assert len(closed)>=3 and len(closed)==len(set(closed)) and fds()==before
    assert len(caught.value.__notes__)==2 and not list(tmp_path.iterdir())


@pytest.mark.parametrize('function',['create','verify'])
@pytest.mark.parametrize('primary',[False,True])
@pytest.mark.parametrize('failure',[OSError,KeyboardInterrupt])
def test_multiple_close_faults_release_all_once_preserve_primary(tmp_path,monkeypatch,function,primary,failure):
    receipt=invoke(tmp_path) if function=='verify' else None
    before=fds();closed=[];original=j.os.close
    def close(fd):
        closed.append(fd);original(fd)
        if len(closed)<=2:raise failure('terminal_secondary_close')
    monkeypatch.setattr(j.os,'close',close)
    if primary:
        def fsync(fd):raise OSError('primary_durability_failure')
        monkeypatch.setattr(j.os,'fsync',fsync)
    with pytest.raises(OSError if primary else failure,match='primary_durability_failure' if primary else 'terminal_secondary_close') as caught:
        if function=='create':invoke(tmp_path)
        else:j.verify_pair(tmp_path/'record',receipt,durable=True)
    assert len(closed)>=3 and len(closed)==len(set(closed)) and fds()==before
    assert len(caught.value.__notes__)==(2 if primary else 1)
    assert (tmp_path/'.record.stage').exists()


@pytest.mark.parametrize('function',['create','verify'])
def test_close_error_never_retries_reused_unrelated_fd(tmp_path,monkeypatch,function):
    receipt=invoke(tmp_path) if function=='verify' else None
    before=fds();original_close=j.os.close;original_open=j.os.open;fired=[];reused=[]
    marker=tmp_path/'unrelated-marker';marker.write_bytes(b'unrelated')
    def close(fd):
        original_close(fd)
        if not fired:
            fired.append(fd);new=original_open(marker,os.O_RDONLY);reused.append(new)
            assert new==fd
            raise OSError('released_and_reused_fd')
    monkeypatch.setattr(j.os,'close',close)
    try:
        with pytest.raises(OSError,match='released_and_reused_fd'):
            if function=='create':invoke(tmp_path)
            else:j.verify_pair(tmp_path/'record',receipt,durable=True)
        assert os.pread(reused[0],20,0)==b'unrelated'
    finally:
        for fd in reused:original_close(fd)
    assert fds()==before


@pytest.mark.parametrize('function,boundary',[('create',1),('create',2),('create',3),('verify',1),('verify',2)])
def test_readtime_inode_mutation_rejects(tmp_path,monkeypatch,function,boundary):
    receipt=invoke(tmp_path) if function=='verify' else None
    before=fds();original=j.os.pread;count=[];fired=[]
    def pread(fd,size,offset):
        result=original(fd,size,offset)
        if offset==0:
            count.append(fd)
            if len(count)==boundary:
                fired.append(fd);(tmp_path/'.record.stage').write_bytes(b'xxxxx')
        return result
    monkeypatch.setattr(j.os,'pread',pread)
    with pytest.raises(j.PairFailure):
        if function=='create':invoke(tmp_path)
        else:j.verify_pair(tmp_path/'record',receipt,durable=True)
    assert fired and fds()==before


@pytest.mark.parametrize('payload',[b'',b'a'*(2*1024*1024+5)])
def test_empty_and_multi_chunk_actual_bytes(tmp_path,payload):
    before=fds();receipt=j.create_pair(tmp_path/'record',payload,mode=0o600)
    assert j.verify_pair(tmp_path/'record',receipt,durable=True)==receipt
    assert (tmp_path/'record').read_bytes()==payload and fds()==before


def test_parent_symlink_refused_before_creation(tmp_path):
    actual=tmp_path/'actual';actual.mkdir();alias=tmp_path/'alias';alias.symlink_to(actual,target_is_directory=True)
    before=fds()
    with pytest.raises((j.PairFailure,OSError)):invoke(alias)
    assert not list(actual.iterdir()) and fds()==before


def test_nonregular_final_fifo_rejected_without_blocking(tmp_path):
    receipt=invoke(tmp_path);(tmp_path/'record').rename(tmp_path/'retained-final');os.mkfifo(tmp_path/'record',mode=0o600)
    before=fds()
    with pytest.raises(j.PairFailure):j.verify_pair(tmp_path/'record',receipt,durable=True)
    assert fds()==before and stat.S_ISFIFO((tmp_path/'record').stat().st_mode)


@pytest.mark.parametrize('replacement',['same_bytes_new_inode','symlink','fifo'])
def test_precise_stage_substitution_rejects_publisher_and_external_receipt(tmp_path,monkeypatch,replacement):
    before=fds();original=j._insert_final;expected=[]
    def insert(fd,stage,final):
        s=os.stat(stage,dir_fd=fd,follow_symlinks=False)
        expected.append(j.PairReceipt(s.st_dev,s.st_ino,0o600,5,__import__('hashlib').sha256(b'alpha').hexdigest(),stage,final))
        os.rename(stage,'retained-original',src_dir_fd=fd,dst_dir_fd=fd)
        if replacement=='same_bytes_new_inode':
            target=os.open(stage,os.O_CREAT|os.O_EXCL|os.O_WRONLY,0o600,dir_fd=fd)
            try:os.write(target,b'alpha')
            finally:os.close(target)
        elif replacement=='symlink':os.symlink('retained-original',stage,dir_fd=fd)
        else:os.mkfifo(stage,0o600,dir_fd=fd)
        original(fd,stage,final)
    monkeypatch.setattr(j,'_insert_final',insert)
    with pytest.raises(j.PairFailure):invoke(tmp_path)
    assert expected and fds()==before
    with pytest.raises((j.PairFailure,OSError)):j.verify_pair(tmp_path/'record',expected[0],durable=True)
    assert fds()==before and (tmp_path/'retained-original').read_bytes()==b'alpha'
    assert set(os.listdir(tmp_path))=={'.record.stage','record','retained-original'}
