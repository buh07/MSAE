# Maintained copy of independent source-free donor; original retained unchanged.
"""Bounded source-free independent primary/iterator/FD-reuse counterexamples."""
import os
import sys
from pathlib import Path
import pytest
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import msae_norspan_jpc_runtime as r
import msae_jumbo_pair_commit as j
import acquire_msae_independent_norspan_v1 as a

@pytest.mark.parametrize('close_type',[OSError,KeyboardInterrupt])
def test_scratch_iteration_interrupt_preserves_primary_closes_iterator_and_owned_fds_once(tmp_path,monkeypatch,close_type):
 before=set(os.listdir('/proc/self/fd'))
 sentinel=tmp_path/'sentinel';sentinel.write_bytes(b'sentinel')
 realopen,realclose,realscan=os.open,os.close,os.scandir
 owned=[];closed=[];reused=[];iter_closed=[]
 with r.reserve_scratch(tmp_path/'lease',authority_sha256='a'*64,entry_lineage_sha256='b'*64) as lease:
  repo=lease.path/'repo';repo.mkdir(mode=0o700);(repo/'one').write_bytes(b'x')
  class Iterator:
   def __init__(self,fd):self.inner=realscan(fd);self.target=os.readlink('/proc/self/fd/'+str(fd))==str(repo)
   def __iter__(self):return self
   def __next__(self):
    if self.target:raise KeyboardInterrupt('original-inventory-interrupt')
    return next(self.inner)
   def close(self):
    self.inner.close()
    if self.target:iter_closed.append(True);raise OSError('secondary-iterator-close')
  def opened(*args,**kwargs):
   fd=realopen(*args,**kwargs)
   if args[0] in ['home','repo']:owned.append(fd)
   return fd
  def close(fd):
   realclose(fd)
   if fd in owned:
    closed.append(fd);reused.append(realopen(sentinel,os.O_RDONLY));raise close_type('secondary-owned-close-'+str(fd))
  try:
   with monkeypatch.context() as patch:
    patch.setattr(os,'scandir',Iterator);patch.setattr(os,'open',opened);patch.setattr(os,'close',close)
    with pytest.raises(KeyboardInterrupt,match='original-inventory-interrupt') as caught:lease.snapshot()
   assert len(owned)==2 and closed==list(reversed(owned)) and iter_closed==[True]
   notes=' '.join(caught.value.__notes__)
   assert 'secondary-iterator-close' in notes and all('secondary-owned-close-'+str(fd) in notes for fd in owned)
   assert all(os.pread(fd,20,0)==b'sentinel' for fd in reused)
   assert (repo/'one').read_bytes()==b'x'
  finally:
   for fd in reused:realclose(fd)
 assert set(os.listdir('/proc/self/fd'))==before

@pytest.mark.parametrize('close_type',[OSError,KeyboardInterrupt])
def test_sparse_primary_and_all_original_ancestor_release_faults_once_no_fd_reuse(tmp_path,monkeypatch,close_type):
 repo=tmp_path/'repo';repo.mkdir(mode=0o700);(repo/'.git').mkdir()
 for name in a.FILES:(repo/name).write_bytes(b'synthetic')
 sentinel=tmp_path/'sentinel';sentinel.write_bytes(b'sentinel')
 realopen,realclose=os.open,os.close
 opened=[];closed=[];reused=[];before=set(os.listdir('/proc/self/fd'))
 def openfd(*args,**kwargs):
  fd=realopen(*args,**kwargs);opened.append(fd);return fd
 def read(*args,**kwargs):raise RuntimeError('original-sparse-read-fault')
 def close(fd):
  closed.append(fd);realclose(fd);reused.append(realopen(sentinel,os.O_RDONLY));raise close_type('secondary-sparse-close-'+str(fd))
 try:
  with monkeypatch.context() as patch:
   patch.setattr(os,'open',openfd);patch.setattr(os,'read',read);patch.setattr(os,'close',close)
   with pytest.raises(RuntimeError,match='original-sparse-read-fault') as caught:a.read_sparse_files(repo)
  assert set(opened)==set(closed) and len(opened)==len(closed)
  assert all('secondary-sparse-close-'+str(fd) in ' '.join(caught.value.__notes__) for fd in opened)
  assert all(os.pread(fd,20,0)==b'sentinel' for fd in reused)
  assert all((repo/name).read_bytes()==b'synthetic' for name in a.FILES)
 finally:
  for fd in reused:realclose(fd)
 assert set(os.listdir('/proc/self/fd'))==before
