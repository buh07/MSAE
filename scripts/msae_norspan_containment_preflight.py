"""Restricted synthetic D1a/D2a preflight. NOT a production sandbox or authority.

No target forks, bwrap helpers, network, model or scientific imports. Requires an
exact scoped review binding for CLI launch. All original evidence/nodes retained.
"""
from __future__ import annotations
import argparse
import ctypes
import errno
import hashlib
import json
import os
from pathlib import Path
import select
import selectors
import signal
import stat
import subprocess
import sys
import time

BASE = Path('/jumbo/lisp/f004ndc/tmp/lisplab1')
DELEGATED = Path('/sys/fs/cgroup/user.slice/user-516097.slice/user@516097.service')
SCRIPT = Path(__file__).resolve()
ENV = {'PATH': '/usr/bin', 'LC_ALL': 'C'}
MIGRATION_BYTES = bytes.fromhex('300a')
CGROUP_LIMIT_BYTES = bytes.fromhex('340a')
SETUP_SECONDS, COMMAND_SECONDS, CLEANUP_SECONDS = 30.0, 10.0, 5.0
OUTPUT_LIMIT = 1024**2


class Blocked(RuntimeError):
    pass


def canonical(value):
    return (json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False)+'\n').encode()


def identity(s):
    return {'dev': s.st_dev, 'ino': s.st_ino, 'uid': s.st_uid,
            'mode': stat.S_IMODE(s.st_mode), 'kind': stat.S_IFMT(s.st_mode)}


def fd_snapshot():
    result = {}
    for name in os.listdir('/proc/self/fd'):
        try:
            result[name] = os.readlink('/proc/self/fd/'+name)
        except FileNotFoundError:
            pass  # The directory collector itself has already closed.
    return result


def record_file(path, *, root_owned=True):
    p = Path(path).resolve(strict=True)
    before = p.stat()
    if root_owned and (before.st_uid != 0 or before.st_mode & 0o022):
        raise Blocked('untrusted_public_runtime:'+str(p))
    row = {'path': str(p), **identity(before)}
    if stat.S_ISREG(before.st_mode):
        raw = p.read_bytes()
        after = p.stat()
        if identity(after) != identity(before) or after.st_size != len(raw):
            raise Blocked('runtime_drift:'+str(p))
        row.update(bytes=len(raw), sha256=hashlib.sha256(raw).hexdigest())
    elif not stat.S_ISDIR(before.st_mode):
        raise Blocked('unexpected_runtime_kind:'+str(p))
    return row


def runtime_manifest():
    """Finite imported public modules, not a stdlib/project directory crawl."""
    fixed = ['/usr/bin/python3.12', '/usr/lib/python3.12',
             '/usr/lib/python3.12/encodings', '/etc/ld.so.preload', '/etc/ld.so.cache',
             '/usr/lib/x86_64-linux-gnu/nosetxattr.so']
    # Complete the transitive ELF closure from our OWN finite mapped libraries,
    # without launching ldd, scanning foreign processes or crawling directories.
    for line in Path('/proc/self/maps').read_text().splitlines():
        fields = line.split(None,5)
        if len(fields)==6 and fields[5].startswith('/'):
            mapped=fields[5]
            if not mapped.startswith(('/usr/lib/','/usr/bin/python3.12')):
                raise Blocked('unexpected_mapped_runtime:'+mapped)
            fixed.append(mapped)
    fixed += ['/usr/lib/x86_64-linux-gnu/'+name for name in
              ('libm.so.6','libz.so.1','libexpat.so.1','libc.so.6',
               'ld-linux-x86-64.so.2','libffi.so.8')]
    for module in tuple(sys.modules.values()):
        path = getattr(module, '__file__', None)
        if path and str(path).startswith('/usr/lib/python3.12/'):
            fixed.append(path)
            cached = getattr(module, '__cached__', None)
            if cached and Path(cached).exists():
                fixed.append(cached)
    rows = [record_file(p) for p in sorted({str(Path(p).resolve(strict=True)) for p in fixed})]
    return {'runtime': rows, 'script': record_file(SCRIPT, root_owned=False),
            'builtin_struct': '_struct' in sys.builtin_module_names,
            'loader_preload': Path('/etc/ld.so.preload').read_text(),
            'environment': ENV, 'argv_template': ['/usr/bin/python3.12','-I','-S','-B',str(SCRIPT),'--child','<arm>','<parent-pidfd>','<nonce>','[<cgroup-procs-fd>]'],
            'thread_count': len(os.listdir('/proc/self/task')),
            'sigchld_default': signal.getsignal(signal.SIGCHLD) == signal.SIG_DFL}


def classify(arm, result):
    if type(result) is not dict or set(result) != {'returncode','errno','before','after'}:
        # Pure classification fixtures may omit the observation strings.
        if type(result) is not dict or set(result) != {'returncode','errno'}:
            raise Blocked('bad_syscall_result')
    rc, code = result['returncode'], result['errno']
    if type(rc) is not int or type(code) is not int:
        raise Blocked('bad_syscall_integer')
    if rc == 0 and code == 0:
        return 'AVAILABLE_PREREQUISITE_ONLY'
    if rc != -1 or code <= 0:
        raise Blocked('inconsistent_syscall_result')
    if code in (errno.EPERM, errno.EACCES, errno.ENOSYS):
        return 'UNAVAILABLE_USERNS_PREREQUISITE' if arm == 'userns' else 'UNAVAILABLE_SELF_MIGRATION'
    return 'BLOCKED_UNKNOWN'


def _libc():
    return ctypes.CDLL('/usr/lib/x86_64-linux-gnu/libc.so.6', use_errno=True)


def _parent_death(parent_fd):
    libc = _libc()
    if libc.prctl(1, signal.SIGKILL, 0, 0, 0) != 0:
        raise Blocked('pdeathsig:'+str(ctypes.get_errno()))
    if select.select([parent_fd], [], [], 0)[0]:
        raise Blocked('original_parent_already_dead')


def child(arm, parent_fd, nonce, cgroup_fd=None):
    _parent_death(parent_fd)  # BEFORE READY/GO and any diagnostic operation.
    if len(nonce) != 32 or any(c not in '0123456789abcdef' for c in nonce):
        raise Blocked('bad_nonce')
    os.write(1, ('READY '+nonce+'\n').encode())
    expected = ('GO '+nonce+'\n').encode()
    buf = b''
    while len(buf) < len(expected):
        chunk = os.read(0, len(expected)+1-len(buf))
        if not chunk:
            return 3  # Missing handle setup can cooperatively close input.
        buf += chunk
    if buf != expected or os.read(0, 1) != b'':
        raise Blocked('bad_go')
    if arm == 'cgroup':
        before = Path('/proc/self/cgroup').read_text()
        try:
            count = os.write(cgroup_fd, MIGRATION_BYTES)  # Exactly ONE self-migration.
            if count != len(MIGRATION_BYTES):
                raise Blocked('partial_self_migration')
            result = {'returncode':0, 'errno':0, 'before':before,
                      'after':Path('/proc/self/cgroup').read_text()}
        except OSError as exc:
            result = {'returncode':-1, 'errno':exc.errno, 'before':before,
                      'after':Path('/proc/self/cgroup').read_text()}
    elif arm == 'userns':
        before = os.readlink('/proc/self/ns/user')
        libc = _libc()
        ctypes.set_errno(0)
        rc = libc.unshare(0x10000000)  # CLONE_NEWUSER, once; no payload fallback.
        result = {'returncode':rc, 'errno':ctypes.get_errno() if rc else 0,
                  'before':before, 'after':os.readlink('/proc/self/ns/user')}
    else:
        raise Blocked('unknown_arm')
    os.write(1, ('RESULT '+nonce+' ').encode()+canonical(result))
    return 0


def _reap(proc, target_fd, cleanup):
    errors = []
    if proc.stdin is not None and not proc.stdin.closed:
        try: proc.stdin.close()
        except BaseException as exc: errors.append(exc)
    if target_fd is not None:
        try: signal.pidfd_send_signal(target_fd, signal.SIGKILL)
        except ProcessLookupError: pass
        except BaseException as exc: errors.append(exc)
    try:
        proc.wait(timeout=cleanup)  # Original direct unreaped child, no numeric signal.
    except BaseException as exc:
        errors.append(exc)
    return errors


def parked(arm, *, cgroup_fd=None, nonce=None, setup=SETUP_SECONDS,
           command=COMMAND_SECONDS, cleanup=CLEANUP_SECONDS, cap=OUTPUT_LIMIT,
           _argv=None, _on_ready=None, _on_spawn=None):
    """Private finite harness; _argv/_on_ready are synthetic fixture hooks only."""
    if len(os.listdir('/proc/self/task')) != 1 or signal.getsignal(signal.SIGCHLD) != signal.SIG_DFL:
        raise Blocked('single_thread_default_sigchld_required')
    nonce = nonce or os.urandom(16).hex()
    parent_fd = target_fd = selector = proc = None
    primary = None
    secondary = []
    result = None
    started = time.monotonic()
    try:
        parent_fd = os.pidfd_open(os.getpid())
        argv = (_argv(parent_fd,nonce) if callable(_argv) else _argv) if _argv is not None else ['/usr/bin/python3.12','-I','-S','-B',str(SCRIPT),'--child',arm,str(parent_fd),nonce]+([] if cgroup_fd is None else [str(cgroup_fd)])
        inherited = (parent_fd,) if cgroup_fd is None else (parent_fd,cgroup_fd)
        if time.monotonic() >= started+setup: raise Blocked('setup_timeout')
        proc = subprocess.Popen(argv, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE, env=ENV, close_fds=True,
                                pass_fds=inherited, bufsize=0)
        target_fd = os.pidfd_open(proc.pid)
        if _on_spawn is not None: _on_spawn(proc,target_fd)
        selector = selectors.DefaultSelector()
        for stream in (proc.stdout,proc.stderr):
            os.set_blocking(stream.fileno(), False)
            selector.register(stream,selectors.EVENT_READ)
        ready = ('READY '+nonce+'\n').encode()
        prefix = ('RESULT '+nonce+' ').encode()
        output = {proc.stdout:bytearray(), proc.stderr:bytearray()}
        total = 0
        go = False
        deadline = started+setup
        while selector.get_map():
            remaining = deadline-time.monotonic()
            if remaining <= 0:
                raise Blocked('command_timeout' if go else 'setup_timeout')
            events = selector.select(min(remaining,0.1))
            for key,_ in events:
                block = os.read(key.fileobj.fileno(), min(65536,cap-total+1))
                if not block:
                    selector.unregister(key.fileobj)
                    continue
                total += len(block)
                if total > cap: raise Blocked('combined_output_cap')
                output[key.fileobj].extend(block)
                if not go and output[proc.stderr]: raise Blocked('pre_go_stderr')
                if not go and len(output[proc.stdout]) > len(ready): raise Blocked('pre_go_extra_bytes')
            if not go and bytes(output[proc.stdout]) == ready:
                # Poll all pipes once more: reject actually available premature output.
                for stream in (proc.stdout,proc.stderr):
                    try: block = os.read(stream.fileno(),min(65536,cap-total+1))
                    except BlockingIOError: block = b''
                    if block: raise Blocked('pre_go_extra_bytes')
                if _on_ready is not None: _on_ready(proc,target_fd)
                if time.monotonic() >= deadline: raise Blocked('setup_timeout')
                payload = ('GO '+nonce+'\n').encode()
                if os.write(proc.stdin.fileno(),payload) != len(payload):
                    raise Blocked('short_go_write')
                proc.stdin.close()  # Child requires exact GO + EOF.
                go = True
                deadline = time.monotonic()+command
        if not go: raise Blocked('no_ready')
        raw = bytes(output[proc.stdout])
        if output[proc.stderr] or not raw.startswith(ready+prefix): raise Blocked('bad_result_frame')
        encoded = raw[len(ready+prefix):]
        parsed = json.loads(encoded)
        if canonical(parsed) != encoded: raise Blocked('extra_noncanonical_result')
        if (type(parsed) is not dict or set(parsed) != {'returncode','errno','before','after'}
                or any(type(parsed[k]) is not str or len(parsed[k])>4096 for k in ('before','after'))):
            raise Blocked('result_observation_required')
        classify(arm,parsed)
        proc.wait(timeout=max(0.001,deadline-time.monotonic()))
        if proc.returncode != 0: raise Blocked('child_exit:'+str(proc.returncode))
        result = {'argv':argv,'result':parsed,'status':classify(arm,parsed),
                  'output_bytes':total,'returncode':proc.returncode,'go_sent':go}
    except BaseException as exc:
        primary = exc
    finally:
        if proc is not None: secondary.extend(_reap(proc,target_fd,cleanup))
        # Release flags/fields BEFORE close; never close a reused integer again.
        objects = [selector] if selector is not None else []
        if proc is not None: objects += [proc.stdin,proc.stdout,proc.stderr]
        for obj in objects:
            if obj is not None:
                try: obj.close()
                except BaseException as exc: secondary.append(exc)
        for fd in (target_fd,parent_fd):
            if fd is not None:
                try: os.close(fd)
                except BaseException as exc: secondary.append(exc)
    if primary is None and secondary: primary = secondary.pop(0)
    if primary is not None:
        for exc in secondary: primary.add_note('cleanup incomplete: '+repr(exc))
        raise primary
    result['owned_child_reaped'] = True
    return result


def _write_once(fd, payload):
    if os.write(fd,payload) != len(payload): raise Blocked('partial_control_write')


def _error_record(exc):
    return {'error':repr(exc),'notes':list(getattr(exc,'__notes__',[]))}


def _close_fd_once(fd, primary=None):
    # Ownership is relinquished before this single attempt: never retry close.
    try:
        os.close(fd)
    except BaseException as secondary:
        note = 'cleanup incomplete: control close: '+repr(secondary)
        if primary is not None:
            primary.add_note(note)
        else:
            secondary.add_note(note)
            raise


def _read_at(directory, name):
    fd = os.open(name,os.O_RDONLY|os.O_NOFOLLOW,dir_fd=directory)
    primary = None
    try:
        raw = os.read(fd,4097)
        if len(raw)>4096: raise Blocked('oversize_kernel_control')
        return raw.decode('ascii')
    except BaseException as exc:
        primary = exc
        raise
    finally: _close_fd_once(fd, primary)


def cgroup_preflight(log):
    """Only exact delegated service; two intentionally retained leaves, no fork."""
    parent = None
    leaves = []
    outcome = {'status':'BLOCKED_UNKNOWN','retained_leaves':[],'operations':[]}
    deadline = time.monotonic()+SETUP_SECONDS
    def budget():
        if time.monotonic() >= deadline: raise Blocked('setup_timeout')
    def observed(label,fn):
        try:
            budget()
            value = fn()
            outcome['operations'].append({'operation':label,'ok':True})
            return value
        except BaseException as exc:
            outcome['operations'].append({'operation':label,'ok':False,'errno':getattr(exc,'errno',None),'error':repr(exc)})
            raise
    def named_check():
        if identity(DELEGATED.stat()) != identity(os.fstat(parent)): raise Blocked('delegated_replacement')
        for name,fd,snapshot in leaves:
            if identity(os.fstat(fd)) != snapshot or identity(os.stat(name,dir_fd=parent,follow_symlinks=False)) != snapshot:
                raise Blocked('leaf_replacement')
    try:
        budget()
        if os.getuid()!=516097 or DELEGATED.resolve()!=DELEGATED: raise Blocked('unexpected_delegated_topology')
        mount = Path('/proc/self/mountinfo').read_text()
        if ' /sys/fs/cgroup ' not in mount or ' - cgroup2 ' not in mount: raise Blocked('cgroup2_unverified')
        parent = observed('open_delegated',lambda:os.open(DELEGATED,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW))
        if os.fstat(parent).st_uid != 516097: raise Blocked('delegated_owner')
        outcome['delegated_identity']=identity(os.fstat(parent))
        nonce=os.urandom(16).hex()
        for suffix in ('a','b'):
            name='msae-norspan-preflight-'+nonce+'-'+suffix
            named_check()
            observed('mkdir_'+suffix,lambda:os.mkdir(name,0o700,dir_fd=parent))
            # Retain pathname even if subsequent open fails: never delete/retry.
            entry={'path':str(DELEGATED/name)};outcome['retained_leaves'].append(entry)
            leaf=observed('open_leaf_'+suffix,lambda:os.open(name,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW,dir_fd=parent))
            snapshot=identity(os.fstat(leaf));leaves.append((name,leaf,snapshot));entry['identity']=snapshot
            named_check()
            budget()
            if _read_at(leaf,'cgroup.procs').strip(): raise Blocked('unexpected_initial_members')
            limit=observed('open_pids_max_'+suffix,lambda:os.open('pids.max',os.O_WRONLY|os.O_NOFOLLOW,dir_fd=leaf))
            primary = None
            try:
                entry['pids_control_identity']=identity(os.fstat(limit))
                observed('write_pids_max_'+suffix,lambda:_write_once(limit,CGROUP_LIMIT_BYTES))
            except BaseException as exc:
                primary = exc
                raise
            finally: _close_fd_once(limit, primary)
            budget()
            if _read_at(leaf,'pids.max').strip()!='4': raise Blocked('pids_readback')
            entry['pids_max']='4'
        named_check()
        control=observed('open_original_migration_control',lambda:os.open('cgroup.procs',os.O_WRONLY|os.O_NOFOLLOW,dir_fd=leaves[0][1]))
        primary = None
        try:
            outcome['migration_control_identity']=identity(os.fstat(control))
            named=os.stat('cgroup.procs',dir_fd=leaves[0][1],follow_symlinks=False)
            if identity(named)!=identity(os.fstat(control)): raise Blocked('migration_control_replacement')
            budget()
            outcome['child']=parked('cgroup',cgroup_fd=control,setup=deadline-time.monotonic())
        except BaseException as exc:
            primary = exc
            raise
        finally: _close_fd_once(control, primary)
        outcome['status']=outcome['child']['status']
        if outcome['status']=='AVAILABLE_PREREQUISITE_ONLY' and not outcome['child']['result']['after'].strip().endswith('/'+leaves[0][0]):
            raise Blocked('self_migration_membership_unverified')
        named_check()
    except OSError as exc:
        outcome['notes']=list(getattr(exc,'__notes__',[]))
        known_setup_denial=not outcome['notes'] and bool(outcome['operations']) and outcome['operations'][-1]['ok'] is False
        outcome['status']='UNAVAILABLE_CGROUP_SETUP' if known_setup_denial and exc.errno in (errno.EPERM,errno.EACCES,errno.ENOENT,errno.EROFS) else 'BLOCKED_UNKNOWN'
        outcome['error']=repr(exc)
    except BaseException as exc:
        outcome['status']='BLOCKED_UNKNOWN';outcome['error']=repr(exc);outcome['notes']=list(getattr(exc,'__notes__',[]))
    finally:
        close_errors=[]
        # Validate the whole retained namespace BEFORE releasing ANY original leaf.
        try:
            if parent is not None: named_check()
        except BaseException as exc: close_errors.append(_error_record(exc))
        for name,fd,snapshot in leaves:
            entry=next(x for x in outcome['retained_leaves'] if x['path']==str(DELEGATED/name))
            try:
                entry['members_after']=_read_at(fd,'cgroup.procs').strip().splitlines()
                if entry['members_after']: raise Blocked('retained_leaf_not_empty')
            except BaseException as exc: close_errors.append(_error_record(exc))
            try: os.close(fd)
            except BaseException as exc: close_errors.append(_error_record(exc))
        if parent is not None:
            try: os.close(parent)
            except BaseException as exc: close_errors.append(_error_record(exc))
        if close_errors: outcome['status']='BLOCKED_UNKNOWN';outcome['cleanup_errors']=close_errors
    log['D1a']=outcome
    return outcome


def save(path, value):
    raw=canonical(value)
    fd=os.open(path,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600)
    try:
        view=memoryview(raw)
        while view:
            count=os.write(fd,view)
            if count<=0: raise Blocked('evidence_write')
            view=view[count:]
        os.fsync(fd)
    finally: os.close(fd)
    parent=os.open(Path(path).parent,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW)
    try: os.fsync(parent)
    finally: os.close(parent)


def launch(binding_path, binding_sha256, output):
    raw=Path(binding_path).read_bytes()
    if hashlib.sha256(raw).hexdigest()!=binding_sha256: raise Blocked('launch_binding_hash')
    binding=json.loads(raw)
    if binding.get('scope')!='synthetic_no_fork_preflight_only' or binding.get('decision')!='SHIP': raise Blocked('exact_preflight_review_required')
    for row in binding['subjects']:
        actual=record_file(row['path'],root_owned=row.get('root_owned',True))
        if {k:v for k,v in row.items() if k!='root_owned'}!=actual: raise Blocked('launch_subject_drift:'+row['path'])
    if not any(x['path']==str(SCRIPT) for x in binding['subjects']): raise Blocked('unbound_script')
    output=Path(output)
    if output.parent!=BASE or output.name in ('','.', '..'): raise Blocked('fresh_jumbo_root_required')
    before=fd_snapshot()
    os.mkdir(output,0o700)  # Exclusive, never reopen/adopt an old run.
    log={'scope':'synthetic_no_fork_preflight_only','binding_sha256':binding_sha256,
         'runtime_manifest':runtime_manifest(),'production_launch_authorized':False,
         'containment_qualified':False,'whole_matrix_closed':False,
         'no_real_source_payload_model_work':True}
    save(output/'STARTED.json',log)
    cgroup_preflight(log)
    if fd_snapshot()!=before or log['D1a']['status']=='BLOCKED_UNKNOWN':
        log['D2a']={'status':'NOT_LAUNCHED_UNCLEAN_OR_BLOCKED_D1'}
    else:
        try: log['D2a']=parked('userns')
        except BaseException as exc: log['D2a']={'status':'BLOCKED_UNKNOWN','error':repr(exc),'notes':getattr(exc,'__notes__',[])}
    log['fd_baseline_restored']=fd_snapshot()==before
    log['full_D1_fork_escape_and_D2_bwrap_not_launched']=True
    save(output/'RESULT.json',log)
    return log


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--facts',action='store_true')
    parser.add_argument('--child',choices=('cgroup','userns'))
    parser.add_argument('child_args',nargs='*')
    parser.add_argument('--run',action='store_true')
    parser.add_argument('--binding');parser.add_argument('--binding-sha256');parser.add_argument('--output')
    args=parser.parse_args()
    if args.child:
        if len(args.child_args)!=(3 if args.child=='cgroup' else 2): parser.error('exact child arguments required')
        return child(args.child,int(args.child_args[0]),args.child_args[1],None if args.child=='userns' else int(args.child_args[2]))
    if args.facts:
        sys.stdout.buffer.write(canonical(runtime_manifest()));return 0
    if args.run and args.binding and args.binding_sha256 and args.output:
        result=launch(args.binding,args.binding_sha256,args.output)
        print(json.dumps({'output':args.output,'D1a':result['D1a']['status'],'D2a':result['D2a']['status'],'containment_qualified':False},sort_keys=True))
        return 0 if result['fd_baseline_restored'] and not any(result[x]['status'].startswith(('BLOCKED','NOT_LAUNCHED')) for x in ('D1a','D2a')) else 2
    parser.error('facts or exact reviewed binding required; no unreviewed launch')


if __name__=='__main__':
    raise SystemExit(main())
