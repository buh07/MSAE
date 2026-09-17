"""Actual adapter fault cells, NOT typed science or whole qualification.

Only fresh synthetic Jumbo controls/catalogs. No acquisition, scoring or keys.
"""
from pathlib import Path
import hashlib
import json
import os
import selectors
import signal
import stat
import subprocess
import sys
import time

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import prepare_msae_independent_norspan_v1 as n
import msae_jumbo_pair_commit as j
import msae_norspan_jpc_controller as c
import msae_norspan_jpc_runtime as r

MARKERS = ('current_history_registry.json', 'baseline.json', 'authority.json',
           'acquisition_entry.json', 'pre_network_ready.json', 'network_started.json',
           'scientific_entry.json', 'pre_raw_ready.json', 'raw_access_started.json',
           'source_acquisition.json', 'seal.json')
EDGES = ('stage_open', 'write', 'chmod', 'file_fsync_1', 'parent_fsync_1', 'link',
         'file_fsync_2', 'parent_fsync_2', 'complete_check_1', 'final_byte_fence',
         'owned_file_close')
ATTACKS = ('stage_replacement', 'racing_final', 'third_alias', 'equal_length_bytes',
           'building_object')
KILL_EDGES = ('stage_opened', 'after_write', 'after_link', 'before_catalog')


def body(marker):
    return {'kind': 'SYNTHETIC adapter qualification only', 'marker': marker}


def observed(request, **values):
    # Persist only source-free numeric firing facts, never actual science/keys.
    request.node.user_properties.append(('synthetic_cell_observation',
        json.dumps(values, sort_keys=True)))


class Direct:
    def __init__(self, tmp_path, monkeypatch, marker):
        assert str(tmp_path).startswith('/jumbo/lisp/f004ndc/tmp/lisplab1/')
        self.root = tmp_path / 'synthetic-project'
        self.root.mkdir(mode=0o700)
        self.prov = self.root / 'controls'
        self.prov.mkdir(mode=0o755)
        self.prov.chmod(0o755)
        monkeypatch.setattr(n, 'ROOT', self.root)
        monkeypatch.setattr(n, 'PROV', self.prov)
        self.marker = marker
        self.path = self.prov / marker
        self.payload = n.canonical_file_bytes(body(marker))
        self.session, self.store = c.CatalogStore.create(
            tmp_path / 'outside-catalogs', self.prov, project_root=self.root,
            lineage_sha256='f' * 64)
        self.old_pin = (self.store.path, self.store.sha256, self.store.sequence)

    def publish(self):
        with n.paired_control_session(self.session):
            return n.publish_json(self.path, body(self.marker))

    def assert_no_adoption(self):
        assert (self.store.path, self.store.sha256, self.store.sequence) == self.old_pin
        assert not (self.store.root / 'catalog-000001.json').exists()
        assert self.marker not in self.session._receipts
        old, _ = c.CatalogStore.load(
            self.old_pin[0], expected_sha256=self.old_pin[1], root=self.prov,
            project_root=self.root, lineage_sha256='f' * 64)
        with pytest.raises(r.RuntimeBlocked, match='outside_expected_receipt_missing'):
            old.expected(self.marker)
        names = set(os.listdir(self.prov))
        if self.marker in names:
            with pytest.raises((r.RuntimeBlocked, j.PairFailure)):
                old.inventory()
        else:
            observation = old.inventory()
            assert observation['logical'] == []
            assert observation['source_work_authorized'] is False
            if names:
                assert observation['partial'] == [self.marker]
        return names


class Hooks:
    """Target stage identity and publisher ordinals; monitors cannot fire a cell."""
    def __init__(self, f, monkeypatch, *, edge=None, error=None, attack=None,
                 close_error=None):
        self.f, self.edge, self.error = f, edge, error
        self.attack, self.close_error = attack, close_error
        self.fired, self.closed, self.replacements = [], [], []
        self.target_fd, self.identity = None, None
        self.file_syncs = self.parent_syncs = self.complete_checks = 0
        self.real = {name: getattr(os, name) for name in
                     ('open', 'write', 'fchmod', 'fsync', 'close')}
        self.insert, self.check, self.fence = j._insert_final, j._check, j._expected_byte_fence
        for name in self.real:
            monkeypatch.setattr(os, name, getattr(self, name))
        monkeypatch.setattr(j, '_insert_final', self.link)
        monkeypatch.setattr(j, '_check', self.validation)
        monkeypatch.setattr(j, '_expected_byte_fence', self.final_fence)

    def fire(self, edge):
        if edge == self.edge and not self.fired:
            self.fired.append(edge)
            raise self.error

    def target(self, fd):
        if self.identity is None:
            return False
        s = os.fstat(fd)
        return (s.st_dev, s.st_ino) == self.identity

    def open(self, path, flags, *args, **kwargs):
        target = path == '.' + self.f.marker + '.stage' and flags & os.O_CREAT
        if target:
            self.fire('stage_open')
        fd = self.real['open'](path, flags, *args, **kwargs)
        if target:
            s = os.fstat(fd)
            self.target_fd, self.identity = fd, (s.st_dev, s.st_ino)
        return fd

    def write(self, fd, value):
        if self.target(fd):
            self.fire('write')
        return self.real['write'](fd, value)

    def fchmod(self, fd, mode):
        if self.target(fd):
            self.fire('chmod')
        return self.real['fchmod'](fd, mode)

    def fsync(self, fd):
        s = os.fstat(fd)
        if self.target(fd):
            self.file_syncs += 1
            self.fire('file_fsync_' + str(self.file_syncs))
        elif self.identity is not None and stat.S_ISDIR(s.st_mode):
            parent = self.f.prov.stat()
            if (s.st_dev, s.st_ino) == (parent.st_dev, parent.st_ino):
                self.parent_syncs += 1
                self.fire('parent_fsync_' + str(self.parent_syncs))
        return self.real['fsync'](fd)

    def validation(self, parent, owned, receipt, *, complete):
        if self.target(owned) and complete:
            self.complete_checks += 1
            if self.complete_checks == 1:
                self.fire('complete_check_1')
        return self.check(parent, owned, receipt, complete=complete)

    def mutate(self, parent, stage, final):
        assert not self.fired
        self.fired.append(self.attack)
        if self.attack == 'stage_replacement':
            os.rename(stage, 'retained-original', src_dir_fd=parent, dst_dir_fd=parent)
            fd = self.real['open'](stage, os.O_WRONLY | os.O_CREAT | os.O_EXCL,
                                   0o600, dir_fd=parent)
            try:
                self.real['write'](fd, b'foreign-stage; never delete')
            finally:
                self.real['close'](fd)
        elif self.attack == 'racing_final':
            fd = self.real['open'](final, os.O_WRONLY | os.O_CREAT | os.O_EXCL,
                                   0o600, dir_fd=parent)
            try:
                self.real['write'](fd, b'foreign-final; never replace')
            finally:
                self.real['close'](fd)
        elif self.attack == 'third_alias':
            os.link(stage, 'foreign-third-alias', src_dir_fd=parent, dst_dir_fd=parent)
        elif self.attack == 'equal_length_bytes':
            stage_path = self.f.prov / stage
            before = stage_path.stat()
            fd = self.real['open'](stage_path, os.O_WRONLY)
            try:
                self.real['write'](fd, b'x' * len(self.f.payload))
            finally:
                self.real['close'](fd)
            os.utime(stage_path, ns=(before.st_atime_ns, before.st_mtime_ns))
        else:
            (self.f.prov / ('.' + final + '.building')).write_bytes(b'foreign-building')

    def link(self, parent, stage, final):
        self.fire('link')
        if self.attack in {'stage_replacement', 'racing_final', 'third_alias'}:
            self.mutate(parent, stage, final)
        return self.insert(parent, stage, final)

    def final_fence(self, parent, owned, receipt):
        if self.target(owned):
            self.fire('final_byte_fence')
            if self.attack in {'equal_length_bytes', 'building_object'}:
                self.mutate(parent, receipt.stage_name, receipt.final_name)
        return self.fence(parent, owned, receipt)

    def close(self, fd):
        target = fd == self.target_fd and not self.closed
        if target:
            self.closed.append(fd)
        result = self.real['close'](fd)
        if target and (self.edge == 'owned_file_close' or self.close_error is not None):
            replacement = self.real['open']('/dev/null', os.O_RDONLY)
            assert replacement == fd
            self.replacements.append(replacement)
            if self.close_error is not None:
                raise self.close_error
            self.fire('owned_file_close')
        return result

    def release_replacements(self):
        for fd in self.replacements:
            os.fstat(fd)  # no subsequent cleanup may have closed the reused FD
            self.real['close'](fd)

    def assert_retained(self):
        if self.attack == 'stage_replacement':
            assert (self.f.prov / 'retained-original').read_bytes() == self.f.payload
            assert self.f.path.read_bytes() == b'foreign-stage; never delete'
        elif self.attack == 'racing_final':
            assert self.f.path.read_bytes() == b'foreign-final; never replace'
        elif self.attack == 'third_alias':
            assert (self.f.prov / 'foreign-third-alias').read_bytes() == self.f.payload
        elif self.attack == 'building_object':
            assert (self.f.prov / ('.' + self.f.marker + '.building')).read_bytes() == b'foreign-building'
        elif self.attack == 'equal_length_bytes':
            assert self.f.path.read_bytes() == b'x' * len(self.f.payload)


@pytest.mark.parametrize('marker', MARKERS)
def test_marker_adapter_positive_actual_pair_registration_catalog(tmp_path, monkeypatch, marker, request):
    f = Direct(tmp_path, monkeypatch, marker)
    baseline = set(os.listdir('/proc/self/fd'))
    receipt = f.publish()
    assert f.session.expected(marker) == receipt
    assert f.session.read(marker) == f.payload
    assert f.store.sequence == 1
    assert f.path.stat().st_nlink == 2
    # A stale pin is correctly rejected when the explicit catalog namespace
    # has advanced; load() never discovers/adopts the newer generation.
    with pytest.raises(r.RuntimeBlocked, match='directory_cardinality'):
        c.CatalogStore.load(f.old_pin[0], expected_sha256=f.old_pin[1],
            root=f.prov, project_root=f.root, lineage_sha256='f' * 64)
    current, _ = c.CatalogStore.load(f.store.path, expected_sha256=f.store.sha256,
        root=f.prov, project_root=f.root, lineage_sha256='f' * 64)
    assert current.read(marker) == f.payload
    observed(request, marker=marker, kind='positive', catalog_sequence=1,
             device=receipt.device, inode=receipt.inode, current_pair=True)
    assert set(os.listdir('/proc/self/fd')) == baseline


@pytest.mark.parametrize('marker', MARKERS)
@pytest.mark.parametrize('edge', EDGES)
@pytest.mark.parametrize('error_type', [OSError, KeyboardInterrupt])
def test_marker_adapter_named_syscall_fault_no_receipt_catalog_advance(tmp_path, monkeypatch, marker, edge, error_type, request):
    f = Direct(tmp_path, monkeypatch, marker)
    baseline = set(os.listdir('/proc/self/fd'))
    error = error_type('SYNTHETIC target publisher:' + edge)
    hooks = Hooks(f, monkeypatch, edge=edge, error=error)
    try:
        with pytest.raises(error_type) as caught:
            f.publish()
        assert caught.value is error and hooks.fired == [edge]
        if hooks.target_fd is not None:
            assert hooks.closed == [hooks.target_fd]
        names = f.assert_no_adoption()
        if edge == 'stage_open':
            assert names == set()
        else:
            assert '.' + marker + '.stage' in names
        observed(request, marker=marker, edge=edge, error=error_type.__name__,
                 fired=hooks.fired, target_identity=hooks.identity,
                 target_fd=hooks.target_fd, closed_original_fds=hooks.closed,
                 file_sync_ordinal=hooks.file_syncs, parent_sync_ordinal=hooks.parent_syncs,
                 catalog_sequence=0, retained_names=sorted(names))
    finally:
        hooks.release_replacements()
    assert set(os.listdir('/proc/self/fd')) == baseline


@pytest.mark.parametrize('marker', MARKERS)
@pytest.mark.parametrize('attack', ATTACKS)
def test_marker_adapter_actual_substitution_extra_or_bytes_retained(tmp_path, monkeypatch, marker, attack, request):
    f = Direct(tmp_path, monkeypatch, marker)
    baseline = set(os.listdir('/proc/self/fd'))
    hooks = Hooks(f, monkeypatch, attack=attack)
    with pytest.raises((j.PairFailure, FileExistsError)):
        f.publish()
    assert hooks.fired == [attack] and hooks.closed == [hooks.target_fd]
    hooks.assert_retained()
    names = f.assert_no_adoption()
    observed(request, marker=marker, attack=attack, fired=hooks.fired,
             target_identity=hooks.identity, closed_original_fds=hooks.closed,
             catalog_sequence=0, retained_names=sorted(names))
    assert set(os.listdir('/proc/self/fd')) == baseline


@pytest.mark.parametrize('marker', MARKERS)
@pytest.mark.parametrize('attack', ['third_alias', 'equal_length_bytes'])
@pytest.mark.parametrize('error_type', [OSError, KeyboardInterrupt])
def test_marker_adapter_combined_primary_close_fd_reuse_preserves_evidence(tmp_path, monkeypatch, marker, attack, error_type, request):
    f = Direct(tmp_path, monkeypatch, marker)
    baseline = set(os.listdir('/proc/self/fd'))
    secondary = error_type('SYNTHETIC actual close after release')
    hooks = Hooks(f, monkeypatch, attack=attack, close_error=secondary)
    try:
        with pytest.raises(j.PairFailure) as caught:
            f.publish()
        assert hooks.fired == [attack] and hooks.closed == [hooks.target_fd]
        assert hooks.replacements == [hooks.target_fd]
        assert any('pair_secondary_close:' + error_type.__name__ in note
                   for note in caught.value.__notes__)
        hooks.assert_retained()
        names = f.assert_no_adoption()
        observed(request, marker=marker, attack=attack, fired=hooks.fired,
                 target_identity=hooks.identity, closed_original_fds=hooks.closed,
                 reused_live_fds=hooks.replacements, secondary=error_type.__name__,
                 primary=type(caught.value).__name__, catalog_sequence=0,
                 retained_names=sorted(names))
    finally:
        hooks.release_replacements()
    assert set(os.listdir('/proc/self/fd')) == baseline


WORKER = r'''
from pathlib import Path
import hashlib,json,os,sys
import prepare_msae_independent_norspan_v1 as n
import msae_jumbo_pair_commit as j
import msae_norspan_jpc_controller as c
root,prov,pin,pinsha,marker,edge,nonce=sys.argv[1:]
root,prov=Path(root),Path(prov)
assert str(root).startswith('/jumbo/lisp/f004ndc/tmp/lisplab1/')
n.ROOT,n.PROV=root,prov
session,store=c.CatalogStore.load(Path(pin),expected_sha256=pinsha,root=prov,project_root=root,lineage_sha256='f'*64)
value={'kind':'SYNTHETIC adapter qualification only','marker':marker}
payload=n.canonical_file_bytes(value);captured=[]
realopen,realwrite=os.open,os.write
insert,snapshot=j._insert_final,c._write_snapshot
def ready(phase):
    print(json.dumps({'nonce':nonce,'phase':phase,'expected':captured[0] if captured else None},sort_keys=True),flush=True)
def park(phase):
    ready(phase)
    # Parent sends nothing else. Genuine process kill is required.
    if os.read(0,1):raise AssertionError('unexpected release of parked synthetic child')
    raise AssertionError('synthetic child EOF instead of actual SIGKILL')
def opening(path,flags,*args,**kwargs):
    fd=realopen(path,flags,*args,**kwargs)
    if path=='.'+marker+'.stage' and flags&os.O_CREAT:
        s=os.fstat(fd);captured.append(j.receipt_record(j.PairReceipt(s.st_dev,s.st_ino,0o644,len(payload),hashlib.sha256(payload).hexdigest(),path,marker)))
        if edge=='stage_opened':park(edge)
    return fd
def writing(fd,raw):
    count=realwrite(fd,raw)
    if captured and (os.fstat(fd).st_dev,os.fstat(fd).st_ino)==(captured[0]['device'],captured[0]['inode']) and edge=='after_write':park(edge)
    return count
def link(*args):
    result=insert(*args)
    if edge=='after_link':park(edge)
    return result
def checkpoint(*args):
    if edge=='before_catalog':park(edge)
    return snapshot(*args)
os.open,os.write,j._insert_final,c._write_snapshot=opening,writing,link,checkpoint
ready('SETUP_READY')
assert os.read(0,1)==b'G'
with n.paired_control_session(session):n.publish_json(prov/marker,value)
raise AssertionError('target READY did not park child')
'''


def frame(proc, selector, buffer, budget, *, phase, nonce, deadline):
    """One monotonic phase budget and bounded raw reads, never readline."""
    while b'\n' not in buffer:
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise AssertionError('SYNTHETIC handshake deadline:' + phase)
        if not selector.select(remaining):
            raise AssertionError('SYNTHETIC handshake timeout:' + phase)
        block = os.read(proc.stdout.fileno(), min(65536, 1024**2 + 1 - budget['received']))
        budget['received'] += len(block)
        buffer.extend(block)
        if budget['received'] > 1024**2:
            raise AssertionError('SYNTHETIC diagnostic cap')
        if not block:
            raise AssertionError('SYNTHETIC child EOF:' + buffer.decode(errors='replace'))
    line, _, suffix = bytes(buffer).partition(b'\n')
    buffer[:] = suffix
    value = json.loads(line)
    assert set(value) == {'nonce', 'phase', 'expected'}
    assert value['nonce'] == nonce and value['phase'] == phase
    return value


def check_setup(setup, buffer, prov):
    assert setup['expected'] is None
    assert not buffer, 'SYNTHETIC premature diagnostic before GO'
    assert os.listdir(prov) == [], 'SYNTHETIC premature publication before GO'


def finish_child(proc, selector, *, primary=None):
    """Always attempt kill/reap and every owned pipe/selector release."""
    errors = []
    for operation in [lambda: proc.kill() if proc.poll() is None else None,
                      lambda: proc.wait(timeout=5),
                      lambda: selector.close() if selector is not None else None,
                      proc.stdin.close, proc.stdout.close]:
        try:
            operation()
        except BaseException as exc:
            errors.append(exc)
    if primary is not None:
        for error in errors:
            primary.add_note('synthetic_child_secondary:' + type(error).__name__)
    elif errors:
        for error in errors[1:]:
            errors[0].add_note('synthetic_child_secondary:' + type(error).__name__)
        raise errors[0]


@pytest.mark.parametrize('marker', MARKERS)
@pytest.mark.parametrize('edge', KILL_EDGES)
def test_marker_adapter_real_sigkill_no_old_pin_adoption_current_custody_distinct(tmp_path, monkeypatch, marker, edge, request):
    f = Direct(tmp_path, monkeypatch, marker)
    baseline = set(os.listdir('/proc/self/fd'))
    worker = tmp_path / 'synthetic-worker.py'
    worker.write_text(WORKER)
    nonce = hashlib.sha256(str(tmp_path).encode()).hexdigest()
    argv = [sys.executable, str(worker), str(f.root), str(f.prov),
            str(f.old_pin[0]), f.old_pin[1], marker, edge, nonce]
    proc = subprocess.Popen(argv, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT, cwd=f.root, env={'PATH':'/usr/bin:/bin',
        'HOME':str(tmp_path), 'LC_ALL':'C', 'PYTHONDONTWRITEBYTECODE':'1',
        'PYTHONPATH':str(Path(__file__).resolve().parents[1] / 'scripts')})
    selector, primary, buffer = None, None, bytearray()
    budget = {'received': 0}
    try:
        selector = selectors.DefaultSelector()
        os.set_blocking(proc.stdout.fileno(), False)
        selector.register(proc.stdout, selectors.EVENT_READ)
        setup = frame(proc, selector, buffer, budget, phase='SETUP_READY', nonce=nonce,
                      deadline=time.monotonic() + 30)
        check_setup(setup, buffer, f.prov)
        proc.stdin.write(b'G')
        proc.stdin.flush()
        target = frame(proc, selector, buffer, budget, phase=edge, nonce=nonce,
                       deadline=time.monotonic() + 10)
        assert not buffer
        assert proc.poll() is None
        proc.kill()
        assert proc.wait(timeout=5) == -signal.SIGKILL
        expected = j.receipt_from_record(f.path, target['expected'])
        assert expected.sha256 == hashlib.sha256(f.payload).hexdigest()
        assert expected.byte_count == len(f.payload)
        names = f.assert_no_adoption()
        assert '.' + marker + '.stage' in names
        if edge in {'after_link', 'before_catalog'}:
            # Independently transported SYNTHETIC expected original identity.
            # Physical current custody is allowed; no adapter/catalog authority.
            assert j.verify_pair(f.path, expected) == expected
            assert f.path.read_bytes() == f.payload
        else:
            assert marker not in names
            with pytest.raises(j.PairFailure):
                j.verify_pair(f.path, expected)
        observation = {
            'marker':marker, 'edge':edge, 'returncode':proc.returncode,
            'setup_budget_seconds':30, 'target_budget_seconds':10,
            'retained_names':sorted(names), 'outside_pin_advanced':False,
            'publication_adapter_completion':False, 'semantic_completion':False,
            'current_physical_custody':edge in {'after_link','before_catalog'},
            'no_source_model_operations':True, 'device':expected.device,
            'inode':expected.inode, 'received_diagnostic_bytes':budget['received']}
        observed(request, **observation)
        (tmp_path / 'kill-observation.json').write_text(json.dumps(
            observation, sort_keys=True) + '\n')
    except BaseException as exc:
        primary = exc
        raise
    finally:
        finish_child(proc, selector, primary=primary)
    assert proc.returncode == -signal.SIGKILL
    assert proc.stdin.closed and proc.stdout.closed
    assert set(os.listdir('/proc/self/fd')) == baseline


def test_marker_wave_production_guard_remains_first_and_unconditional():
    controller = c.Controller.__new__(c.Controller)
    with pytest.raises(n.GateFailure, match='jpc_whole_qualification_pending'):
        controller.execute('acquire')


@pytest.mark.parametrize('operation', ['kill', 'wait', 'selector', 'stdin', 'stdout'])
@pytest.mark.parametrize('error_type', [OSError, KeyboardInterrupt])
@pytest.mark.parametrize('existing_primary', [False, True])
def test_marker_child_cleanup_actual_release_fault_all_owned_resources(tmp_path, operation, error_type, existing_primary):
    from types import SimpleNamespace
    assert str(tmp_path).startswith('/jumbo/lisp/f004ndc/tmp/lisplab1/')
    baseline = set(os.listdir('/proc/self/fd'))
    proc = subprocess.Popen([sys.executable, '-c', 'import os;os.read(0,1)'],
        stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
        cwd=tmp_path, env={'PATH':'/usr/bin:/bin', 'PYTHONDONTWRITEBYTECODE':'1'})
    selector, completed = None, False
    try:
        selector = selectors.DefaultSelector()
        selector.register(proc.stdout, selectors.EVENT_READ)
        calls, error = [], error_type('SYNTHETIC cleanup after actual release:' + operation)
        def wrap(name, actual):
            def call(*args, **kwargs):
                calls.append(name)
                result = actual(*args, **kwargs)
                if name == operation:
                    raise error
                return result
            return call
        owned = SimpleNamespace(poll=proc.poll, kill=wrap('kill', proc.kill),
            wait=wrap('wait', proc.wait),
            stdin=SimpleNamespace(close=wrap('stdin', proc.stdin.close)),
            stdout=SimpleNamespace(close=wrap('stdout', proc.stdout.close)))
        selected = SimpleNamespace(close=wrap('selector', selector.close))
        primary = AssertionError('SYNTHETIC original primary') if existing_primary else None
        if primary is None:
            with pytest.raises(error_type) as caught:
                finish_child(owned, selected)
            assert caught.value is error
        else:
            finish_child(owned, selected, primary=primary)
            assert primary.__notes__ == ['synthetic_child_secondary:' + error_type.__name__]
        assert calls == ['kill', 'wait', 'selector', 'stdin', 'stdout']
        assert proc.returncode == -signal.SIGKILL
        assert proc.stdin.closed and proc.stdout.closed
        assert set(os.listdir('/proc/self/fd')) == baseline
        completed = True
    finally:
        if not completed:
            finish_child(proc, selector, primary=sys.exc_info()[1])



@pytest.mark.parametrize('error_type', [OSError, KeyboardInterrupt])
@pytest.mark.parametrize('edge', ['allocation', 'registration'])
def test_marker_child_selector_setup_failure_still_kills_reaps_closes(tmp_path, monkeypatch, error_type, edge):
    baseline = set(os.listdir('/proc/self/fd'))
    proc = subprocess.Popen([sys.executable, '-c', 'import os;os.read(0,1)'],
        stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
        cwd=tmp_path, env={'PATH':'/usr/bin:/bin', 'PYTHONDONTWRITEBYTECODE':'1'})
    selector, primary = None, error_type('SYNTHETIC selector setup failure')
    fired = []
    def fail(*args, **kwargs):
        fired.append(edge)
        raise primary
    try:
        if edge == 'allocation':
            monkeypatch.setattr(selectors, 'DefaultSelector', fail)
        selector = selectors.DefaultSelector()
        if edge == 'registration':
            monkeypatch.setattr(selector, 'register', fail)
        selector.register(proc.stdout, selectors.EVENT_READ)
        raise AssertionError('SYNTHETIC setup hook did not fire')
    except error_type as caught:
        assert caught is primary and fired == [edge]
    finally:
        finish_child(proc, selector, primary=primary)
    assert proc.returncode == -signal.SIGKILL
    assert proc.stdin.closed and proc.stdout.closed
    assert set(os.listdir('/proc/self/fd')) == baseline


@pytest.mark.parametrize('case', ['bad_json', 'bad_nonce', 'bad_phase', 'extra_key',
                                  'eof', 'timeout', 'expired', 'combined_cap'])
def test_marker_child_handshake_invalid_timeout_and_combined_cap(monkeypatch, case):
    from types import SimpleNamespace
    baseline = set(os.listdir('/proc/self/fd'))
    reader, writer = os.pipe()
    value = {'nonce':'synthetic-nonce', 'phase':'SETUP_READY', 'expected':None}
    if case == 'bad_nonce':
        value['nonce'] = 'foreign-nonce'
    if case == 'bad_phase':
        value['phase'] = 'foreign-phase'
    if case == 'extra_key':
        value['extra'] = True
    raw = b'not JSON\n' if case == 'bad_json' else (json.dumps(value)+'\n').encode()
    proc = SimpleNamespace(stdout=SimpleNamespace(fileno=lambda: reader))
    selected = SimpleNamespace(select=lambda remaining: [] if case == 'timeout' else [True])
    buffer, budget = bytearray(), {'received':0}
    monkeypatch.setattr(time, 'monotonic', lambda: 10)
    try:
        if case != 'eof':
            os.write(writer, raw)
        if case == 'eof':
            os.close(writer)
            writer = None
        if case == 'combined_cap':
            # Real first-frame read then independent second-frame arrival. The
            # already consumed setup bytes still count toward the shared cap.
            setup = frame(proc, selected, buffer, budget, phase='SETUP_READY',
                          nonce='synthetic-nonce', deadline=20)
            assert setup == value and budget['received'] == len(raw)
            budget['received'] = 1024**2  # simulate bounded prior diagnostics
            os.write(writer, b'x')
        with pytest.raises((AssertionError, json.JSONDecodeError)):
            frame(proc, selected, buffer, budget, phase='SETUP_READY',
                  nonce='synthetic-nonce', deadline=10 if case == 'expired' else 20)
        if case == 'combined_cap':
            assert budget['received'] == 1024**2 + 1
    finally:
        os.close(reader)
        if writer is not None:
            os.close(writer)
    assert set(os.listdir('/proc/self/fd')) == baseline


@pytest.mark.parametrize('edge', ['premature_frame', 'premature_object'])
def test_marker_child_setup_denies_buffered_target_or_publication(tmp_path, edge):
    prov = tmp_path / 'synthetic-controls'
    prov.mkdir()
    setup = {'nonce':'synthetic-nonce', 'phase':'SETUP_READY', 'expected':None}
    buffer = bytearray()
    if edge == 'premature_frame':
        buffer.extend(b'{"phase":"after_link"}\n')
    else:
        (prov / '.synthetic.stage').write_bytes(b'SYNTHETIC retained')
    with pytest.raises(AssertionError, match='premature'):
        check_setup(setup, buffer, prov)
    if edge == 'premature_object':
        assert (prov / '.synthetic.stage').read_bytes() == b'SYNTHETIC retained'
