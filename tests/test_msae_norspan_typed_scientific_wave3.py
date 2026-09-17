"""Forty causal synthetic typed cells; no whole/scientific launch authority."""
from contextlib import contextmanager
import hashlib
import json
import os
import stat
import sys

import pytest
from msae_norspan_controller_fixture import Fixture, n, r, c
import msae_jumbo_pair_commit as j


def fdset():
    return set(os.listdir('/proc/self/fd'))


def identity(s):
    return [s.st_dev, s.st_ino]


def pin(f):
    return [str(f.store.path), f.store.sha256, f.store.sequence]


def observe(evidence, callback, **fields):
    """Failure-safe observations; never replace an already initiating error."""
    primary = sys.exc_info()[1]
    try:
        evidence.update(callback(), **fields)
    except BaseException as exc:
        evidence.setdefault('observation_errors', []).append(repr(exc))
        if primary is not None:
            primary.add_note('wave3 observation failed: ' + repr(exc))
        else:
            raise


@contextmanager
def cell(request):
    before = fdset()
    evidence = {'scope': 'synthetic_typed_wave3_only', 'whole_qualified': False}
    try:
        yield evidence
    finally:
        primary = sys.exc_info()[1]
        def final_facts():
            after = fdset()
            return {'fd_baseline_restored': before == after, 'fd_delta': sorted(after - before),
                    'test_error': None if primary is None else repr(primary)}
        try:
            evidence.update(final_facts())
        except BaseException as exc:
            evidence.setdefault('observation_errors', []).append(repr(exc))
            if primary is not None:
                primary.add_note('wave3 FD observation failed: ' + repr(exc))
        try:
            request.node.user_properties.append(('synthetic_typed_wave3', json.dumps(evidence, sort_keys=True)))
        except BaseException as exc:
            if primary is not None:
                primary.add_note('wave3 causal serialization failed: ' + repr(exc))
            else:
                raise
        if evidence.get('fd_baseline_restored') is not True or evidence.get('observation_errors'):
            if primary is not None:
                primary.add_note('wave3 cleanup/observation not established')
            else:
                pytest.fail('wave3 cleanup/observation not established')


def retained_snapshot(f):
    """Only named synthetic trees; never discover actual project/private state."""
    assert n.ROOT == f.root and str(f.root).startswith('/jumbo/lisp/f004ndc/tmp/lisplab1/')
    rows = {}
    for tag, root in [('control', n.PROV), ('data', n.DATA), ('catalog', f.store.root)]:
        if not root.exists():
            continue
        for path in [root, *sorted(root.rglob('*'))]:
            st = path.lstat()
            row = [st.st_dev, st.st_ino, stat.S_IFMT(st.st_mode), stat.S_IMODE(st.st_mode), st.st_nlink]
            if stat.S_ISREG(st.st_mode):
                row += [st.st_size, hashlib.sha256(path.read_bytes()).hexdigest()]
            elif stat.S_ISLNK(st.st_mode):
                row += [os.readlink(path)]  # Never follow a substituted symbolic link.
            else:
                assert stat.S_ISDIR(st.st_mode)
            rows[tag + '/' + str(path.relative_to(root))] = row
    ordinary = f.root / 'synthetic-history.txt'
    if ordinary.exists():
        rows['ordinary-history'] = [*identity(ordinary.lstat()), hashlib.sha256(ordinary.read_bytes()).hexdigest()]
    return rows


def snapshot_digest(rows):
    return hashlib.sha256(json.dumps(rows, sort_keys=True, separators=(',', ':')).encode()).hexdigest()


class RawTracker:
    """Mark real loader dynamic extent; intercept only real original raw pairs."""
    def __init__(self, f, monkeypatch, *, ordinal=None, primary=None, mutation=None):
        self.f = f
        self.ordinal, self.primary, self.mutation = ordinal, primary, mutation
        self.calls = 0
        self.role_producer_entries = 0
        self.role_pair_attempts = []
        self.role_producer = n.publish_private_roles
        self.pair_producer = j.create_owned_pair
        monkeypatch.setattr(n, 'publish_private_roles', self.publishing_roles)
        monkeypatch.setattr(j, 'create_owned_pair', self.creating_pair)
        self.active = False
        self.reads, self.completed, self.fired = [], [], []
        self.started_pin = None
        self.load = n.load_validated_raw
        self.read = j.OwnedPair.read_bytes
        monkeypatch.setattr(n, 'load_validated_raw', self.loading)
        def read_original_pair(pair, **kwargs):
            return self.reading(pair, **kwargs)
        monkeypatch.setattr(j.OwnedPair, 'read_bytes', read_original_pair)

    def publishing_roles(self, roles):
        self.role_producer_entries += 1
        return self.role_producer(roles)

    def creating_pair(self, path, *args, **kwargs):
        if path.parent.parent == n.PRIVATE and path.name == 'payload.jsonl':
            self.role_pair_attempts.append(path.parent.name)
        return self.pair_producer(path, *args, **kwargs)

    def loading(self, acquisition):
        self.calls += 1
        assert not self.active
        assert (n.PROV / 'raw_access_started.json').exists()
        self.started_pin = pin(self.f)
        self.active = True
        try:
            return self.load(acquisition)
        finally:
            self.active = False

    def reading(self, pair, **kwargs):
        target = self.active and pair.receipt.final_name in {*n.SOURCE_FILES.values(), n.LICENSE_FILE}
        if target:
            assert identity(os.fstat(pair.fd)) == [pair.receipt.device, pair.receipt.inode]
            row = {'ordinal': len(self.reads) + 1, 'name': pair.receipt.final_name,
                   'original': identity(os.fstat(pair.fd)), 'sha256': pair.receipt.sha256}
            self.reads.append(row)
            if row['ordinal'] == self.ordinal:
                self.fired.append(row)
                if self.mutation is not None:
                    self.mutation()
                if self.primary is not None:
                    raise self.primary
        value = self.read(pair, **kwargs)
        if target:
            self.completed.append(row['name'])
        return value

    def facts(self):
        return {'current_catalog_pin': pin(self.f), 'synthetic_git_commands': len(self.f.calls),
                'loader_invocations': self.calls, 'raw_started_pin': self.started_pin,
                'raw_reads': self.reads, 'raw_completed': self.completed,
                'raw_fired': self.fired, 'private_producer_entries': self.role_producer_entries,
                'private_pair_attempts': self.role_pair_attempts}


def fresh_refusal(f, tracker, evidence, *, catalog_fault=False, partial=False):
    loader_before = tracker.calls
    commands = len(f.calls)
    producers_before = tracker.role_producer_entries
    roles_before = list(tracker.role_pair_attempts)
    producer_pin = pin(f)
    evidence.update(fresh_start_catalog_pin=producer_pin, fresh_start_synthetic_git_commands=commands,
                    fresh_start_loader_calls=loader_before, fresh_start_private_entries=producers_before,
                    fresh_start_private_pair_attempts=roles_before)
    retained = retained_snapshot(f)
    evidence['retained_pre_fresh_sha256'] = snapshot_digest(retained)
    attempts = []
    try:
        for command in ('recover', 'prepare'):
            if catalog_fault:
                with pytest.raises(r.RuntimeBlocked, match='^directory_cardinality$') as caught:
                    f.fresh()  # Explicit predecessor load, never execute after failed load.
                attempts.append({'command_not_executed': command, 'boundary': 'CatalogStore.load',
                                 'reason': str(caught.value)})
            else:
                fresh = f.fresh()  # MUST load successfully; unrelated load errors fail the cell.
                reason = ('started_without_terminal_no_retry' if command == 'recover' else
                          'raw_started_or_partial_unresolved' if partial else 'raw_started_unresolved')
                expected = r.RuntimeBlocked if command == 'recover' else n.GateFailure
                with pytest.raises(expected, match='^' + reason + '$') as caught:
                    fresh.execute(command)
                attempts.append({'command': command, 'boundary': 'Controller.execute', 'reason': str(caught.value)})
            assert pin(f) == producer_pin  # No silent in-memory predecessor rebasing.
            assert retained_snapshot(f) == retained  # AFTER every attempted load/recovery/prepare.
            assert tracker.calls == loader_before == 1
            assert tracker.role_producer_entries == producers_before
            assert tracker.role_pair_attempts == roles_before
            assert len(f.calls) == commands == 8
    finally:
        def final_facts():
            current = retained_snapshot(f)
            return {'fresh_refusals': attempts, 'retained_post_fresh_sha256': snapshot_digest(current),
                    'retained_unchanged_after_fresh': current == retained,
                    'retained_object_count': len(retained), 'synthetic_git_commands': len(f.calls),
                    'current_catalog_pin': pin(f)}
        observe(evidence, final_facts)


@pytest.mark.parametrize('terminal', ['success', 'rejection'])
def test_typed_scientific_positive_terminal_recovery(tmp_path, monkeypatch, request, terminal):
    with cell(request) as evidence:
        f = Fixture(tmp_path, monkeypatch)
        f.acquire(monkeypatch, license_bytes=b'unacceptable synthetic terms\n' if terminal == 'rejection' else None)
        tracker = RawTracker(f, monkeypatch)
        try:
            if terminal == 'rejection':
                with pytest.raises(n.ScientificGateFailure):
                    f.fresh().execute('prepare')
            else:
                f.fresh().execute('prepare')
            assert tracker.calls == 1 and len(tracker.completed) == 4
            result = f.fresh().execute('recover')
            assert result['state'] == 'scientific_terminal'
            assert result['source_work_authorized'] is False
            assert result['historical_success_inferred'] is False
            assert result['C2_scientific_opens'] == result['model_operations'] == 0
            assert result['terminal_raw_reconstruction_attempts'] == 1
            assert tracker.calls == 2 and len(f.calls) == 8
            evidence.update(terminal=terminal, recovery=result, synthetic_git_commands=len(f.calls))
        finally:
            observe(evidence, tracker.facts)


@pytest.mark.parametrize('ordinal', [1, 2, 3, 4])
@pytest.mark.parametrize('error', [OSError, KeyboardInterrupt])
def test_typed_raw_original_read_fault_no_retry(tmp_path, monkeypatch, request, ordinal, error):
    with cell(request) as evidence:
        f = Fixture(tmp_path, monkeypatch); f.acquire(monkeypatch)
        primary = error('synthetic-original-raw-read')
        tracker = RawTracker(f, monkeypatch, ordinal=ordinal, primary=primary)
        try:
            with pytest.raises(error) as caught:
                f.fresh().execute('prepare')
            assert caught.value is primary
            assert len(tracker.fired) == 1 and len(tracker.completed) == ordinal - 1
            assert not any((n.PROV / x).exists() for x in ['seal.json', 'rejection.json', 'source_ready.json'])
            fresh_refusal(f, tracker, evidence)
        finally:
            observe(evidence, tracker.facts, error_class=error.__name__, raw_ordinal=ordinal)


@pytest.mark.parametrize('ordinal', [1, 3])
def test_typed_mid_raw_history_drift_blocks_terminal(tmp_path, monkeypatch, request, ordinal):
    with cell(request) as evidence:
        f = Fixture(tmp_path, monkeypatch)
        path = f.root / 'synthetic-history.txt'
        before = b'bounded historic surface alpha beta gamma delta epsilon\n'
        after = before.replace(b'alpha', b'omega')
        assert len(before) == len(after) and before != after
        path.write_bytes(before); path.chmod(0o644)
        f.acquire(monkeypatch)
        registry = f.session.canonical('current_history_registry.json')
        row = next(x for x in registry['entries'] if x['path'] == path.name)
        assert row['sha256'] == hashlib.sha256(before).hexdigest()
        assert row['adapter'] == 'text' and row['extracted_unit_count'] > 0
        assert n.lexical_tokens(before.decode())
        def mutate():
            path.write_bytes(after)
            assert path.read_bytes() == after
        tracker = RawTracker(f, monkeypatch, ordinal=ordinal, mutation=mutate)
        try:
            with pytest.raises(n.GateFailure, match=r'^history_drift:synthetic-history\.txt$') as caught:
                f.fresh().execute('prepare')
            assert len(tracker.fired) == 1 and tracker.calls == 1 and len(tracker.completed) == 4
            evidence['initiating_drift_reason'] = str(caught.value)
            assert not (n.PROV / 'seal.json').exists()
            assert not (n.PROV / 'rejection.json').exists()
            assert not (n.PROV / 'source_ready.json').exists()
            assert path.read_bytes() == after
            fresh_refusal(f, tracker, evidence)
            assert path.read_bytes() == after
        finally:
            observe(evidence, lambda: {**tracker.facts(), 'physical_seal': (n.PROV / 'seal.json').exists()}, history_registry_row=row,
                            retained_history_before=before.decode(), retained_history_after=after.decode(),
                            raw_ordinal=ordinal)


class PublishFault:
    def __init__(self, f, monkeypatch, path, edge, primary):
        self.f, self.path, self.edge, self.primary = f, path, edge, primary
        self.stage = '.' + path.name + '.stage'
        self.original = self.writer = self.predecessor = self.catalog_original = None
        self.fired = []; self.open_facts = None; self.promotion = False
        self.open, self.write, self.insert = os.open, os.write, j._insert_final
        monkeypatch.setattr(os, 'open', self.opening)
        monkeypatch.setattr(os, 'write', self.writing)
        monkeypatch.setattr(j, '_insert_final', self.inserting)

    def own_parent(self, fd):
        try:
            expected = identity(self.path.parent.stat())
        except FileNotFoundError:
            return False
        return identity(os.fstat(fd)) == expected

    def opening(self, path, flags, *args, **kwargs):
        parent = kwargs.get('dir_fd')
        stage = parent is not None and path == self.stage and flags & os.O_CREAT and self.own_parent(parent)
        catalog = (self.promotion and self.edge == 'catalog' and parent is not None
                   and path == c.CatalogStore._name(self.predecessor[2] + 1)
                   and flags & os.O_CREAT
                   and identity(os.fstat(parent)) == identity(self.f.store.root.stat()))
        fd = self.open(path, flags, *args, **kwargs)
        if stage:
            self.original = identity(os.fstat(fd)); self.writer = fd
            self.open_facts = {'parent': identity(os.fstat(parent)), 'name': str(path), 'flags': flags}
        if catalog:
            assert flags & os.O_EXCL
            assert self.path.exists() and self.path.stat().st_nlink == 2
            self.catalog_original = identity(os.fstat(fd))
        return fd

    def fire(self, edge, original):
        if self.edge == edge and not self.fired:
            self.fired.append({'edge': edge, 'original': original, 'ordinal': 1})
            raise self.primary

    def writing(self, fd, payload):
        original = identity(os.fstat(fd))
        if original == self.original and self.edge == 'write':
            self.predecessor = pin(self.f)
            self.fire('write', original)
        if original == self.catalog_original:
            self.fire('catalog', original)
        return self.write(fd, payload)

    def inserting(self, parent, stage, final):
        if final == self.path.name and stage == self.stage and self.own_parent(parent):
            assert self.original == identity(os.stat(stage, dir_fd=parent, follow_symlinks=False))
            self.predecessor = pin(self.f)
            self.fire('link', self.original)
            self.promotion = True
        return self.insert(parent, stage, final)

    def facts(self):
        return {'fault_edge': self.edge, 'fault_path': str(self.path), 'publication_fired': self.fired,
                'original_stage': self.original, 'stage_open': self.open_facts,
                'catalog_original': self.catalog_original, 'predecessor': self.predecessor,
                'stage_retained': (self.path.parent / self.stage).exists(), 'final_retained': self.path.exists()}


@pytest.mark.parametrize('role', r.ROLES)
@pytest.mark.parametrize('edge', ['write', 'link'])
@pytest.mark.parametrize('error', [OSError, KeyboardInterrupt])
def test_typed_private_role_partial_successor_retained(tmp_path, monkeypatch, request, role, edge, error):
    with cell(request) as evidence:
        f = Fixture(tmp_path, monkeypatch); f.acquire(monkeypatch)
        tracker = RawTracker(f, monkeypatch)
        hook = PublishFault(f, monkeypatch, n.PRIVATE / role.lower() / 'payload.jsonl', edge, error('synthetic-private-role'))
        try:
            with pytest.raises(error) as caught:
                f.fresh().execute('prepare')
            assert caught.value is hook.primary and len(hook.fired) == 1
            assert tracker.calls == 1 and len(tracker.completed) == 4
            index = r.ROLES.index(role)
            retained = []
            for prior in r.ROLES[:index]:
                pair = n.PRIVATE / prior.lower() / 'payload.jsonl'
                assert pair.stat().st_nlink == 2
                assert pair.stat().st_ino == (pair.parent / '.payload.jsonl.stage').stat().st_ino
                retained.append(prior)
            assert (hook.path.parent / hook.stage).exists() and not hook.path.exists()
            assert all(not (n.PRIVATE / later.lower()).exists() for later in r.ROLES[index + 1:])
            assert not (n.PROV / 'seal.json').exists() and not (n.PROV / 'source_ready.json').exists()
            evidence.update(prior_complete_roles=retained, later_roles_absent=list(r.ROLES[index + 1:]))
            assert tracker.role_producer_entries == 1
            assert tracker.role_pair_attempts == [x.lower() for x in r.ROLES[:index + 1]]
            fresh_refusal(f, tracker, evidence, partial=True)
        finally:
            observe(evidence, lambda: {**hook.facts(), **tracker.facts()}, error_class=error.__name__, role=role)


@pytest.mark.parametrize('terminal', ['success', 'rejection'])
@pytest.mark.parametrize('edge', ['write', 'link', 'catalog'])
@pytest.mark.parametrize('error', [OSError, KeyboardInterrupt])
def test_typed_terminal_publication_fault_not_success(tmp_path, monkeypatch, request, terminal, edge, error):
    with cell(request) as evidence:
        f = Fixture(tmp_path, monkeypatch)
        f.acquire(monkeypatch, license_bytes=b'unacceptable synthetic terms\n' if terminal == 'rejection' else None)
        tracker = RawTracker(f, monkeypatch)
        name = 'seal.json' if terminal == 'success' else 'rejection.json'
        hook = PublishFault(f, monkeypatch, n.PROV / name, edge, error('synthetic-terminal-publication'))
        try:
            with pytest.raises(error) as caught:
                f.fresh().execute('prepare')
            assert caught.value is hook.primary and len(hook.fired) == 1
            assert pin(f) == hook.predecessor
            assert tracker.calls == 1 and len(tracker.completed) == 4
            assert (hook.path.parent / hook.stage).exists()
            assert hook.path.exists() == (edge == 'catalog')
            if edge == 'catalog':
                assert hook.catalog_original is not None
                snapshot = f.store.root / c.CatalogStore._name(hook.predecessor[2] + 1)
                assert identity(snapshot.stat()) == hook.catalog_original and snapshot.stat().st_size == 0
                evidence.update(partial_catalog_retained=str(snapshot))
            fresh_refusal(f, tracker, evidence, catalog_fault=edge == 'catalog', partial=edge != 'catalog')
        finally:
            observe(evidence, lambda: {**hook.facts(), **tracker.facts()}, error_class=error.__name__, terminal=terminal)
