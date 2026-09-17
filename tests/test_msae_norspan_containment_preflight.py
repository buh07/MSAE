"""No-fork synthetic preflight harness checks; NEVER real cgroup/userns calls."""
import importlib.util
from pathlib import Path
import pytest

SCRIPT = Path(__file__).resolve().parents[1] / 'scripts/msae_norspan_containment_preflight.py'


def load():
    assert SCRIPT.exists(), 'Missing reviewed no-fork preflight implementation'
    spec = importlib.util.spec_from_file_location('preflight', SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_migration_frame_is_exact_kernel_newline():
    p = load()
    assert p.MIGRATION_BYTES == bytes.fromhex('300a')


def test_namespace_denial_is_not_containment_pass():
    p = load()
    assert p.classify('userns', {'returncode': -1, 'errno': 1}) == 'UNAVAILABLE_USERNS_PREREQUISITE'
    assert p.classify('userns', {'returncode': 0, 'errno': 0}) == 'AVAILABLE_PREREQUISITE_ONLY'

import errno
import json
import os
import selectors
import signal
import subprocess
import sys
import time

NONCE = 'a'*32


def synthetic(tmp_path, body):
    assert str(tmp_path).startswith('/jumbo/lisp/f004ndc/tmp/lisplab1/')
    path=tmp_path/'synthetic-no-fork-child.py'
    path.write_text('import os,sys,time,json\nnonce='+repr(NONCE)+'\n'+body)
    return ['/usr/bin/python3.12','-I','-S','-B',str(path)]


GOOD = '''os.write(1, ('READY '+nonce+'\\n').encode())
payload=sys.stdin.buffer.read()
assert payload==('GO '+nonce+'\\n').encode()
os.write(1, ('RESULT '+nonce+' '+json.dumps({'returncode':-1,'errno':1,'before':'inert','after':'inert'},sort_keys=True,separators=(',',':'))+'\\n').encode())
'''


def test_actual_synthetic_parked_positive_reaps_and_restores_fds(tmp_path):
    p=load();before=p.fd_snapshot()
    result=p.parked('userns',nonce=NONCE,_argv=synthetic(tmp_path,GOOD))
    assert result['status']=='UNAVAILABLE_USERNS_PREREQUISITE'
    assert result['owned_child_reaped'] and result['go_sent']
    assert p.fd_snapshot()==before


@pytest.mark.parametrize('body,match',[
    ("os.write(1,('READY '+nonce+'\\nEXTRA').encode());time.sleep(2)",'pre_go_extra'),
    ("os.write(2,b'bad');time.sleep(2)",'pre_go_stderr'),
    ("os.write(1,b'WRONG\\n')",'no_ready'),
    ("time.sleep(2)",'setup_timeout'),
    ("os.write(1,('READY '+nonce+'\\n').encode());sys.stdin.buffer.read();time.sleep(2)",'command_timeout'),
    (GOOD+"os.write(1,b'EXTRA\\n')",'Extra data'),
    (GOOD.replace("'errno':1","'errno':True"),'bad_syscall_integer'),
    (GOOD.replace("'errno':1","'errno':0"),'inconsistent_syscall_result'),
    (GOOD.replace("'returncode':-1","'returncode':0"),'inconsistent_syscall_result'),
    (GOOD+"os.write(2,b'late-error')",'bad_result_frame'),
    (GOOD+"sys.exit(7)",'child_exit'),
])
def test_actual_protocol_faults_reject_reap_and_restore(tmp_path,body,match):
    p=load();before=p.fd_snapshot()
    with pytest.raises((p.Blocked,ValueError),match=match):
        p.parked('userns',nonce=NONCE,_argv=synthetic(tmp_path,body),setup=.2,command=.2,cleanup=2)
    assert p.fd_snapshot()==before


@pytest.mark.parametrize('stage',['parent_pidfd','popen','target_pidfd','selector','register'])
@pytest.mark.parametrize('exc_type',[OSError,KeyboardInterrupt])
def test_actual_startup_primary_preserved_owned_child_never_gets_GO(tmp_path,monkeypatch,stage,exc_type):
    p=load();before=p.fd_snapshot();primary=exc_type('synthetic startup primary');calls=[]
    argv=synthetic(tmp_path,GOOD)
    real_pidfd=os.pidfd_open;count=0
    def opening(pid,*args):
        nonlocal count
        count+=1
        if (stage=='parent_pidfd' and count==1) or (stage=='target_pidfd' and count==2): raise primary
        return real_pidfd(pid,*args)
    monkeypatch.setattr(os,'pidfd_open',opening)
    original_popen=p.subprocess.Popen
    def popen(*args,**kwargs):
        if stage=='popen':raise primary
        proc=original_popen(*args,**kwargs);calls.append(proc);return proc
    monkeypatch.setattr(p.subprocess,'Popen',popen)
    original_selector=p.selectors.DefaultSelector
    def selecting():
        if stage=='selector':raise primary
        selector=original_selector()
        if stage=='register':
            def fail(*args):raise primary
            selector.register=fail
        return selector
    monkeypatch.setattr(p.selectors,'DefaultSelector',selecting)
    with pytest.raises(exc_type) as caught:p.parked('userns',nonce=NONCE,_argv=argv,cleanup=2)
    assert caught.value is primary
    assert all(proc.returncode is not None for proc in calls)
    assert p.fd_snapshot()==before


@pytest.mark.parametrize('stream',[1,2])
def test_actual_combined_cap_limits_pre_GO_output(tmp_path,stream):
    p=load();before=p.fd_snapshot()
    argv=synthetic(tmp_path,f'os.write({stream},b"X"*65);time.sleep(2)')
    with pytest.raises(p.Blocked,match='combined_output_cap'):
        p.parked('userns',nonce=NONCE,_argv=argv,cap=64,cleanup=2)
    assert p.fd_snapshot()==before


def test_partial_setup_output_does_not_reset_absolute_deadline(tmp_path):
    p=load();before=p.fd_snapshot()
    argv=synthetic(tmp_path,"for byte in ('READY '+nonce+'\\n').encode():\n os.write(1,bytes([byte]));time.sleep(.03)\n")
    started=time.monotonic()
    with pytest.raises(p.Blocked,match='setup_timeout'):
        p.parked('userns',nonce=NONCE,_argv=argv,setup=.12,cleanup=2)
    assert time.monotonic()-started<1 and p.fd_snapshot()==before


@pytest.mark.parametrize('kind',['signal','wait','selector_close'])
@pytest.mark.parametrize('exc_type',[OSError,KeyboardInterrupt])
def test_cleanup_failure_cannot_be_reported_as_diagnostic_success(tmp_path,monkeypatch,kind,exc_type):
    p=load();primary=exc_type('synthetic cleanup error');before=p.fd_snapshot()
    real_signal=p.signal.pidfd_send_signal;real_wait=p.subprocess.Popen.wait
    real_selector=p.selectors.DefaultSelector;fired=[]
    if kind=='signal':
        def fail(fd,sig,*args):
            fired.append(True);raise primary
        monkeypatch.setattr(p.signal,'pidfd_send_signal',fail)
    elif kind=='wait':
        def fail(proc,*args,**kwargs):
            value=real_wait(proc,*args,**kwargs)
            if len(fired)==0:fired.append(True);raise primary
            return value
        monkeypatch.setattr(p.subprocess.Popen,'wait',fail)
    else:
        def selecting():
            selector=real_selector();close=selector.close
            def fail():
                close();fired.append(True);raise primary
            selector.close=fail;return selector
        monkeypatch.setattr(p.selectors,'DefaultSelector',selecting)
    with pytest.raises(exc_type) as caught:
        p.parked('userns',nonce=NONCE,_argv=synthetic(tmp_path,GOOD),cleanup=2)
    assert caught.value is primary and fired
    assert p.fd_snapshot()==before


def test_primary_and_release_after_error_FD_reuse_preserved(tmp_path,monkeypatch):
    p=load();before=p.fd_snapshot();primary=p.Blocked('primary');secondary=OSError('close after release');reused=[]
    real_close=os.close;real_open=os.open;original_selector=p.selectors.DefaultSelector
    def selecting():
        selector=original_selector();close=selector.close
        def failure():
            original_fd=selector.fileno();close()
            temporary=real_open('/dev/null',os.O_RDONLY)
            if temporary!=original_fd:
                replacement=os.dup2(temporary,original_fd);real_close(temporary)
            else:replacement=temporary
            assert replacement==original_fd
            reused.append(replacement);raise secondary
        selector.close=failure;return selector
    monkeypatch.setattr(p.selectors,'DefaultSelector',selecting)
    def on_ready(*args):raise primary
    try:
        with pytest.raises(p.Blocked) as caught:
            p.parked('userns',nonce=NONCE,_argv=synthetic(tmp_path,GOOD),_on_ready=on_ready,cleanup=2)
        assert caught.value is primary and any('close after release' in note for note in primary.__notes__)
        assert reused and os.fstat(reused[0])
    finally:
        for fd in reused:real_close(fd)
    assert p.fd_snapshot()==before


def test_unsafe_coordinator_SIGCHLD_configuration_rejects_before_spawn(monkeypatch):
    p=load();monkeypatch.setattr(p.signal,'getsignal',lambda _:signal.SIG_IGN)
    monkeypatch.setattr(p.subprocess,'Popen',lambda *a,**k:pytest.fail('spawned'))
    with pytest.raises(p.Blocked,match='single_thread'):p.parked('userns')


def test_runtime_manifest_includes_global_loader_preload_not_just_environment():
    p=load();facts=p.runtime_manifest();paths={x['path'] for x in facts['runtime']}
    assert '/etc/ld.so.preload' in paths and '/etc/ld.so.cache' in paths
    assert '/usr/lib/x86_64-linux-gnu/nosetxattr.so' in paths
    assert facts['builtin_struct'] is True and 'LD_PRELOAD' not in facts['environment']


def test_non_reviewed_binding_rejects_before_cgroup_or_userns(tmp_path,monkeypatch):
    p=load();path=tmp_path/'pending.json';raw=p.canonical({'scope':'synthetic_no_fork_preflight_only','decision':'PENDING'})
    path.write_bytes(raw)
    monkeypatch.setattr(p,'cgroup_preflight',lambda *a:pytest.fail('cgroup work'))
    with pytest.raises(p.Blocked,match='exact_preflight_review'):
        p.launch(path,p.hashlib.sha256(raw).hexdigest(),tmp_path/'not-launch')


def test_finite_runtime_manifest_covers_loaded_crypto_dependency():
    p=load();paths={x['path'] for x in p.runtime_manifest()['runtime']}
    mapped=[line.rsplit(' ',1)[-1].strip() for line in Path('/proc/self/maps').read_text().splitlines() if '/libcrypto.so.' in line]
    assert mapped and all(str(Path(path).resolve()) in paths for path in mapped)


def test_two_leaf_cleanup_validates_all_before_closing_any(tmp_path,monkeypatch):
    p=load();before=p.fd_snapshot();delegated=tmp_path/'synthetic-delegated';delegated.mkdir()
    monkeypatch.setattr(p,'DELEGATED',delegated)
    real_read=Path.read_text;real_mkdir=os.mkdir;real_write=os.write
    def read(path,*args,**kwargs):
        if str(path)=='/proc/self/mountinfo':return 'x /sys/fs/cgroup x - cgroup2 x\n'
        return real_read(path,*args,**kwargs)
    monkeypatch.setattr(Path,'read_text',read)
    def mkdir(path,*args,**kwargs):
        real_mkdir(path,*args,**kwargs)
        if 'dir_fd' in kwargs:
            d=delegated/path
            (d/'pids.max').write_bytes(b'max\n');(d/'cgroup.procs').write_bytes(b'')
    monkeypatch.setattr(os,'mkdir',mkdir)
    def write(fd,payload):
        if payload==b'4\n':os.ftruncate(fd,0)
        return real_write(fd,payload)
    monkeypatch.setattr(os,'write',write)
    monkeypatch.setattr(p,'parked',lambda *a,**k:{'status':'UNAVAILABLE_SELF_MIGRATION','result':{'returncode':-1,'errno':13},'owned_child_reaped':True})
    log={};p.cgroup_preflight(log)
    assert log['D1a']['status']=='UNAVAILABLE_SELF_MIGRATION',log
    assert len(log['D1a']['retained_leaves'])==2
    assert all(x['members_after']==[] for x in log['D1a']['retained_leaves'])
    assert p.fd_snapshot()==before


@pytest.mark.parametrize('phase',['early','parked','delayed','transport','kill_failure','bootstrap'])
def test_actual_killed_owner_original_pidfds_no_diagnostic(tmp_path,phase):
    # Every target is INERT, including on delayed/missing kill and transport paths.
    # Only new fixture processes change parent-death/subreaper state.
    p=load();before=p.fd_snapshot();marker=tmp_path/'unexpected-GO'
    target=tmp_path/'inert-parent-death-target.py'
    target.write_text("""import importlib.util,sys,os,select,time
spec=importlib.util.spec_from_file_location('preflight',sys.argv[1])
p=importlib.util.module_from_spec(spec);spec.loader.exec_module(p)
parentfd=int(sys.argv[2]);nonce=sys.argv[3];phase=sys.argv[4]
if phase=='early':
 assert select.select([parentfd],[],[],7)[0]
 try:p._parent_death(parentfd)
 except p.Blocked as exc:
  assert str(exc)=='original_parent_already_dead';os._exit(17)
 os._exit(24)
p._parent_death(parentfd)
os.write(1,('READY '+nonce+'\\n').encode())
payload=sys.stdin.buffer.read()
if payload:
 fd=os.open(sys.argv[5],os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
 os.write(fd,payload);os.close(fd);os._exit(23)
# Do not race parent-death SIGKILL with a cooperative Python exit.
time.sleep(7);os._exit(26)
""")
    owner=tmp_path/'inert-fixture-owner.py'
    owner.write_text("""import importlib.util,sys,socket,array,os
spec=importlib.util.spec_from_file_location('preflight',sys.argv[1])
p=importlib.util.module_from_spec(spec);spec.loader.exec_module(p)
p._parent_death(int(sys.argv[6]))  # Before any target creation.
sock=socket.socket(fileno=int(sys.argv[2]));phase=sys.argv[3]
def send(proc,fd):
 sock.sendmsg([b'P'],[(socket.SOL_SOCKET,socket.SCM_RIGHTS,array.array('i',[fd]))])
 # No duration/scheduling assumption. NEVER return normally toward GO.
 try:message=sock.recv(1)
 except BaseException as exc:raise p.Blocked('transport failed closed') from exc
 raise p.Blocked('barrier failed closed:'+repr(message))
def argv(parentfd,nonce):
 return ['/usr/bin/python3.12','-I','-S','-B',sys.argv[4],sys.argv[1],str(parentfd),nonce,phase,sys.argv[5]]
try:
 if phase=='bootstrap':raise p.Blocked('synthetic bootstrap refusal before target')
 p.parked('userns',_argv=argv,_on_spawn=send if phase=='early' else None,
  _on_ready=None if phase=='early' else send)
except p.Blocked:os._exit(19)
os._exit(25)
""")
    fixture=tmp_path/'inert-fixture-subreaper.py'
    fixture.write_text("""import ctypes,os,socket,array,subprocess,sys,select,signal,json,time,importlib.util
spec=importlib.util.spec_from_file_location('preflight',sys.argv[2])
p=importlib.util.module_from_spec(spec);spec.loader.exec_module(p)
p._parent_death(int(sys.argv[6]))  # Before subreaper or owned-child setup.
libc=ctypes.CDLL('/usr/lib/x86_64-linux-gnu/libc.so.6',use_errno=True)
assert libc.prctl(36,1,0,0,0)==0
left,right=socket.socketpair();left.settimeout(7);parentfd=os.pidfd_open(os.getpid())
proc=subprocess.Popen(['/usr/bin/python3.12','-I','-S','-B',sys.argv[1],sys.argv[2],str(right.fileno()),sys.argv[3],sys.argv[4],sys.argv[5],str(parentfd)],pass_fds=(right.fileno(),parentfd),close_fds=True,env=p.ENV,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
ownerfd=os.pidfd_open(proc.pid);right.close();targetfd=None
try:
 if sys.argv[3]=='delayed':time.sleep(4.1)  # Exceeds the rejected old3s race.
 message,anc,flags,addr=left.recvmsg(1,socket.CMSG_SPACE(array.array('i').itemsize))
 if sys.argv[3]=='bootstrap':
  assert message==b'' and not anc;proc.wait(timeout=5);assert proc.returncode==19
 else:
  assert message==b'P' and not flags and len(anc)==1
  level,kind,data=anc[0];assert level==socket.SOL_SOCKET and kind==socket.SCM_RIGHTS
  fds=array.array('i');fds.frombytes(data);assert len(fds)==1;targetfd=fds[0]
  if sys.argv[3] in ('transport','kill_failure'):
   # No numeric fallback/retry on a refused kill; fail closed at the barrier.
   if sys.argv[3]=='kill_failure':
    try:raise PermissionError('synthetic original-pidfd kill refusal')
    except PermissionError:pass
   left.shutdown(socket.SHUT_WR);proc.wait(timeout=5);assert proc.returncode==19
   assert select.select([targetfd],[],[],5)[0]
   try:os.waitid(os.P_PIDFD,targetfd,os.WEXITED)
   except ChildProcessError:pass  # Target already reaped by its actual owner.
   else:raise AssertionError('unexpected adopted target')
  else:
   signal.pidfd_send_signal(ownerfd,signal.SIGKILL);proc.wait(timeout=5)
   assert select.select([targetfd],[],[],5)[0]
   status=os.waitid(os.P_PIDFD,targetfd,os.WEXITED)
   assert (status.si_code,status.si_status)==((os.CLD_EXITED,17) if sys.argv[3]=='early' else (os.CLD_KILLED,signal.SIGKILL)), (status.si_code,status.si_status)
 assert not os.path.exists(sys.argv[5])
 print(json.dumps({'phase':sys.argv[3],'owner_reaped':True,'target_reaped_or_not_created':True,'no_GO_observed':not os.path.exists(sys.argv[5]),'inert_target_only':True},sort_keys=True))
finally:
 if targetfd is not None:
  try:signal.pidfd_send_signal(targetfd,signal.SIGKILL)
  except ProcessLookupError:pass
  os.close(targetfd)
 try:signal.pidfd_send_signal(ownerfd,signal.SIGKILL)
 except ProcessLookupError:pass
 proc.wait(timeout=5);os.close(ownerfd);os.close(parentfd);left.close();proc.stdout.close();proc.stderr.close()
""")
    parentfd=os.pidfd_open(os.getpid());fixturefd=None;proc=None
    try:
        proc=subprocess.Popen(['/usr/bin/python3.12','-I','-S','-B',str(fixture),str(owner),str(SCRIPT),phase,str(target),str(marker),str(parentfd)],env=p.ENV,close_fds=True,pass_fds=(parentfd,),stdout=subprocess.PIPE,stderr=subprocess.PIPE)
        fixturefd=os.pidfd_open(proc.pid)
        stdout,stderr=proc.communicate(timeout=15)
        assert proc.returncode==0,stderr.decode()
        result=json.loads(stdout)
        assert result['owner_reaped'] and result['target_reaped_or_not_created'] and result['no_GO_observed'] and result['inert_target_only']
        assert not marker.exists()
    finally:
        if fixturefd is not None:
            try:signal.pidfd_send_signal(fixturefd,signal.SIGKILL)
            except ProcessLookupError:pass
        if proc is not None:
            if fixturefd is None and proc.poll() is None:
                # No numeric PID signal: explicit incomplete cleanup, no false PASS.
                raise AssertionError('fixture original handle missing; cleanup unverified')
            proc.wait(timeout=5);proc.stdout.close();proc.stderr.close()
        if fixturefd is not None:os.close(fixturefd)
        os.close(parentfd)
    assert p.fd_snapshot()==before


def fake_cgroups(p,tmp_path,monkeypatch):
    delegated=tmp_path/'synthetic-cgroup-controls';delegated.mkdir()
    monkeypatch.setattr(p,'DELEGATED',delegated)
    realread=Path.read_text;realmkdir=os.mkdir;realwrite=os.write
    def read(path,*args,**kwargs):
        if str(path)=='/proc/self/mountinfo':return 'x /sys/fs/cgroup x - cgroup2 x\n'
        return realread(path,*args,**kwargs)
    def mkdir(path,*args,**kwargs):
        realmkdir(path,*args,**kwargs)
        if 'dir_fd' in kwargs:
            (delegated/path/'pids.max').write_bytes(b'max\n')
            (delegated/path/'cgroup.procs').write_bytes(b'')
    def write(fd,payload):
        if payload==b'4\n':os.ftruncate(fd,0)
        return realwrite(fd,payload)
    monkeypatch.setattr(Path,'read_text',read);monkeypatch.setattr(os,'mkdir',mkdir);monkeypatch.setattr(os,'write',write)
    return delegated,write,mkdir


def test_denied_control_write_plus_close_fault_is_BLOCK_with_primary_secondary(tmp_path,monkeypatch):
    p=load();before=p.fd_snapshot();fake_cgroups(p,tmp_path,monkeypatch)
    primary=PermissionError(13,'synthetic write primary');secondary=PermissionError(13,'synthetic close secondary');target=[];fired=[]
    realopen=os.open;realclose=os.close
    def open(path,flags,*args,**kwargs):
        fd=realopen(path,flags,*args,**kwargs)
        if path=='pids.max' and flags & os.O_WRONLY:target.append(fd)
        return fd
    def write(fd,payload):
        if target and fd==target[0]:raise primary
        pytest.fail('unexpected other write')
    def close(fd):
        realclose(fd)
        if target and fd==target[0] and not fired:fired.append(True);raise secondary
    monkeypatch.setattr(os,'open',open);monkeypatch.setattr(os,'write',write);monkeypatch.setattr(os,'close',close)
    log={};p.cgroup_preflight(log)
    assert log['D1a']['status']=='BLOCKED_UNKNOWN',log
    assert 'write primary' in log['D1a']['error']
    assert any('close secondary' in note for note in log['D1a']['notes'])
    assert p.fd_snapshot()==before


def test_D1_retains_original_parked_secondary_notes(tmp_path,monkeypatch):
    p=load();before=p.fd_snapshot();fake_cgroups(p,tmp_path,monkeypatch)
    primary=p.Blocked('synthetic parked primary');primary.add_note('cleanup incomplete: synthetic target reap failure')
    def fail(*a,**k):raise primary
    monkeypatch.setattr(p,'parked',fail)
    log={};p.cgroup_preflight(log)
    assert log['D1a']['status']=='BLOCKED_UNKNOWN'
    assert log['D1a']['notes']==primary.__notes__ and 'target reap failure' in json.dumps(log)
    assert p.fd_snapshot()==before


def test_D1_original_setup_deadline_stops_after_returned_slow_mkdir(tmp_path,monkeypatch):
    p=load();before=p.fd_snapshot();delegated,write,mkdir=fake_cgroups(p,tmp_path,monkeypatch)
    clock=[10.];writes=[];calls=[]
    monkeypatch.setattr(p.time,'monotonic',lambda:clock[0])
    def slowmkdir(*args,**kwargs):mkdir(*args,**kwargs);clock[0]+=100.
    def countedwrite(*args):writes.append(True);return write(*args)
    monkeypatch.setattr(os,'mkdir',slowmkdir);monkeypatch.setattr(os,'write',countedwrite)
    monkeypatch.setattr(p,'parked',lambda *a,**k:calls.append(True))
    log={};p.cgroup_preflight(log)
    assert log['D1a']['status']=='BLOCKED_UNKNOWN' and 'setup_timeout' in log['D1a']['error']
    assert not writes and not calls
    assert len(log['D1a']['retained_leaves'])==1 and Path(log['D1a']['retained_leaves'][0]['path']).is_dir()
    assert p.fd_snapshot()==before


@pytest.mark.parametrize('observation',['missing','wrong_type'])
def test_active_result_requires_own_before_after_strings(tmp_path,observation):
    p=load();before=p.fd_snapshot()
    body=GOOD.replace(",'before':'inert','after':'inert'",'') if observation=='missing' else GOOD.replace("'before':'inert','after':'inert'","'before':123,'after':123")
    with pytest.raises(p.Blocked,match='result_observation'):
        p.parked('userns',nonce=NONCE,_argv=synthetic(tmp_path,body),cleanup=2)
    assert p.fd_snapshot()==before


def test_cleanup_BLOCK_never_authorizes_second_arm(tmp_path,monkeypatch):
    p=load();before=p.fd_snapshot()
    row=p.record_file(p.SCRIPT,root_owned=False);row['root_owned']=False
    raw=p.canonical({'scope':'synthetic_no_fork_preflight_only','decision':'SHIP','subjects':[row]})
    binding=tmp_path/'synthetic-test-binding.json';binding.write_bytes(raw)
    output=p.BASE/('norspan-inert-sequencing-'+os.urandom(16).hex())
    def blocked(log):
        log['D1a']={'status':'BLOCKED_UNKNOWN','error':'synthetic denial','notes':['cleanup incomplete: synthetic close']}
    monkeypatch.setattr(p,'cgroup_preflight',blocked)
    monkeypatch.setattr(p,'parked',lambda *a,**k:pytest.fail('D2 launched after cleanup BLOCK'))
    result=p.launch(binding,p.hashlib.sha256(raw).hexdigest(),output)
    assert result['D2a']['status']=='NOT_LAUNCHED_UNCLEAN_OR_BLOCKED_D1'
    assert result['fd_baseline_restored'] and json.loads((output/'RESULT.json').read_text())['D1a']['notes']
    assert p.fd_snapshot()==before


def test_original_setup_budget_rechecked_before_child_creation(tmp_path,monkeypatch):
    p=load();before=p.fd_snapshot();clock=[10.];opening=os.pidfd_open
    monkeypatch.setattr(p.time,'monotonic',lambda:clock[0])
    def slow(*a,**k):
        fd=opening(*a,**k);clock[0]+=100.;return fd
    monkeypatch.setattr(os,'pidfd_open',slow)
    monkeypatch.setattr(p.subprocess,'Popen',lambda *a,**k:pytest.fail('child created after expiry'))
    with pytest.raises(p.Blocked,match='setup_timeout'):p.parked('userns')
    assert p.fd_snapshot()==before


def test_original_setup_budget_rechecked_before_GO(tmp_path,monkeypatch):
    p=load();before=p.fd_snapshot();clock=[10.]
    monkeypatch.setattr(p.time,'monotonic',lambda:clock[0])
    def expired(*a):clock[0]+=100.
    with pytest.raises(p.Blocked,match='setup_timeout'):
        p.parked('userns',nonce=NONCE,_argv=synthetic(tmp_path,GOOD),_on_ready=expired)
    assert p.fd_snapshot()==before
