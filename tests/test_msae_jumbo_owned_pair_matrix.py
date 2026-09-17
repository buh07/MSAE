# Maintained copy of retained independent synthetic matrix; original unchanged.
"""Independent source-free synthetic retained-handle counterexamples only."""
import dataclasses
import fcntl
import hashlib
import os
from pathlib import Path
import stat
import sys

import pytest
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import msae_jumbo_pair_commit as j


def fds():
    return set(os.listdir('/proc/self/fd'))


def handle(root, kind):
    if kind == 'writer':
        return j.create_owned_pair(root / 'one', b'alpha', mode=0o600)
    receipt = j.create_pair(root / 'one', b'alpha', mode=0o600)
    return j.open_owned_pair(root / 'one', receipt)


@pytest.mark.parametrize('kind', ['writer', 'reader'])
def test_fd_access_and_original_retention(tmp_path, kind):
    before = fds()
    with handle(tmp_path, kind) as pair:
        expected = os.O_RDWR if kind == 'writer' else os.O_RDONLY
        assert fcntl.fcntl(pair.fd, fcntl.F_GETFL) & os.O_ACCMODE == expected
        inode = pair.receipt.inode
        with j.create_owned_pair(tmp_path / 'two', b'beta', mode=0o600):
            assert os.fstat(pair.fd).st_ino == inode
            assert pair.validate(durable=True) == pair.receipt
    assert fds() == before


@pytest.mark.parametrize('kind', ['writer', 'reader'])
@pytest.mark.parametrize('position', ['owned', 'immediate', 'nonleaf', 'root'])
@pytest.mark.parametrize('failure', [OSError, KeyboardInterrupt])
def test_each_retained_close_position_release_reuse_no_retry(tmp_path, monkeypatch, kind, position, failure):
    before = fds()
    pair = handle(tmp_path, kind)
    candidates = {'owned': pair.fd, 'immediate': pair.parent.descriptors[-1],
                  'nonleaf': pair.parent.descriptors[-2], 'root': pair.parent.descriptors[0]}
    target = candidates[position]
    owned = {pair.fd, *pair.parent.descriptors}
    seen = []
    reused = []
    close = os.close
    def release_fault(fd):
        seen.append(fd)
        close(fd)
        if fd == target and not reused:
            replacement = os.open(tmp_path / 'unrelated-sentinel', os.O_RDWR | os.O_CREAT | os.O_EXCL, 0o600)
            assert replacement == target
            reused.append(replacement)
            raise failure('released-descriptor')
    monkeypatch.setattr(j.os, 'close', release_fault)
    with pytest.raises(failure, match='released-descriptor'):
        pair.close()
    assert pair.closed and set(seen) == owned and len(seen) == len(owned)
    pair.close()
    assert len(seen) == len(owned)
    os.write(reused[0], b'unrelated-owned-byte')
    assert os.fstat(reused[0]).st_size == len(b'unrelated-owned-byte')
    close(reused[0])
    assert fds() == before


@pytest.mark.parametrize('kind', ['writer', 'reader'])
@pytest.mark.parametrize('operation', ['fsync_file', 'fsync_parent', 'hash_before', 'hash_after'])
@pytest.mark.parametrize('failure', [OSError, KeyboardInterrupt])
def test_validate_primary_all_secondary_close_errors(tmp_path, monkeypatch, kind, operation, failure):
    before = fds()
    pair = handle(tmp_path, kind)
    owned = {pair.fd, *pair.parent.descriptors}
    seen = []
    fired = []
    close, fsync, pread = os.close, os.fsync, os.pread
    count = [0]
    def close_fault(fd):
        seen.append(fd)
        close(fd)
        if fd in owned:
            raise OSError('secondary-close')
    def fsync_fault(fd):
        eligible = (fd == pair.fd if operation == 'fsync_file' else fd == pair.parent)
        if operation.startswith('fsync') and eligible:
            fired.append(operation)
            raise failure('primary-fault')
        return fsync(fd)
    def pread_fault(fd, size, offset):
        if fd == pair.fd:
            count[0] += 1
            target = 1 if operation == 'hash_before' else 3
            if operation.startswith('hash') and count[0] == target:
                fired.append(operation)
                raise failure('primary-fault')
        return pread(fd, size, offset)
    monkeypatch.setattr(j.os, 'close', close_fault)
    monkeypatch.setattr(j.os, 'fsync', fsync_fault)
    monkeypatch.setattr(j.os, 'pread', pread_fault)
    with pytest.raises(failure, match='primary-fault') as caught:
        with pair:
            pair.validate(durable=True)
    assert fired == [operation]
    assert set(seen) == owned and len(seen) == len(owned)
    assert len(caught.value.__notes__) == len(owned)
    pair.close()
    assert len(seen) == len(owned) and fds() == before
    assert set(tmp_path.iterdir()) == {tmp_path/'one', tmp_path/'.one.stage'}


@pytest.mark.parametrize('kind', ['create', 'open'])
@pytest.mark.parametrize('failure', [OSError, KeyboardInterrupt])
def test_handle_constructor_failure_preserves_primary_and_all_fd_cleanup(tmp_path, monkeypatch, kind, failure):
    receipt = j.create_pair(tmp_path/'one', b'alpha', mode=0o600) if kind == 'open' else None
    before = fds()
    close = os.close
    seen = []
    class FailedHandle:
        def __init__(self, *args):
            raise failure('constructor-fault')
    def close_fault(fd):
        seen.append(fd)
        close(fd)
        raise OSError('constructor-secondary')
    monkeypatch.setattr(j, 'OwnedPair', FailedHandle)
    monkeypatch.setattr(j.os, 'close', close_fault)
    with pytest.raises(failure, match='constructor-fault') as caught:
        if kind == 'create':
            j.create_owned_pair(tmp_path/'one', b'alpha', mode=0o600)
        else:
            j.open_owned_pair(tmp_path/'one', receipt, durable=True)
    assert seen and len(seen) == len(set(seen))
    assert len(caught.value.__notes__) == len(seen) and fds() == before
    assert set(tmp_path.iterdir()) == {tmp_path/'one', tmp_path/'.one.stage'}


@pytest.mark.parametrize('phase', ['prevalidate', 'copy', 'postvalidate'])
@pytest.mark.parametrize('fault', ['error', 'interrupt', 'short', 'bytes', 'third', 'ancestor'])
def test_bounded_reader_each_phase_has_no_false_success(tmp_path, monkeypatch, phase, fault):
    root = tmp_path/'ancestor'/'dest'
    root.mkdir(parents=True)
    receipt = j.create_pair(root/'one', b'alpha', mode=0o600)
    before = fds()
    original = os.pread
    fired = []
    count = [0]
    observed_phase = ['prevalidate']
    validate_count = [0]
    real_validate = j.OwnedPair.validate
    def validate(handle, *, durable=False):
        validate_count[0] += 1
        observed_phase[0] = 'prevalidate' if validate_count[0] == 1 else 'postvalidate'
        result = real_validate(handle, durable=durable)
        observed_phase[0] = 'copy'
        return result
    with j.open_owned_pair(root/'one', receipt) as pair:
        def pread(fd, size, offset):
            if fd != pair.fd:
                return original(fd, size, offset)
            count[0] += 1
            result = original(fd, size, offset)
            if not fired and observed_phase[0] == phase and offset == 0:
                fired.append(fault)
                if fault == 'error':
                    raise OSError('reader-fault')
                if fault == 'interrupt':
                    raise KeyboardInterrupt('reader-fault')
                if fault == 'short':
                    return b''
                if fault == 'bytes':
                    (root/'one').write_bytes(b'xxxxx')
                elif fault == 'third':
                    os.link(root/'one', root/'foreign-third')
                else:
                    os.rename(root.parent, tmp_path/'retained-ancestor')
                    root.mkdir(parents=True)
            return result
        monkeypatch.setattr(j.OwnedPair, 'validate', validate)
        monkeypatch.setattr(j.os, 'pread', pread)
        expected = OSError if fault == 'error' else KeyboardInterrupt if fault == 'interrupt' else j.PairFailure
        with pytest.raises(expected):
            pair.read_bytes(max_bytes=5)
    assert fired == [fault] and fds() == before


@pytest.mark.parametrize('kind', ['writer', 'reader'])
@pytest.mark.parametrize('payload', [b'', b'alpha', b'ab' * (1024*1024+13)])
def test_bounded_reader_actual_bytes_empty_and_multichunk(tmp_path, kind, payload):
    before = fds()
    with j.create_owned_pair(tmp_path/'one', payload, mode=0o600) as writer:
        if kind == 'writer':
            assert writer.read_bytes(max_bytes=len(payload)) == payload
        else:
            with j.open_owned_pair(tmp_path/'one', writer.receipt, durable=True) as reader:
                assert reader.read_bytes(max_bytes=len(payload)) == payload
        if payload:
            with pytest.raises(j.PairFailure, match='large'):
                writer.read_bytes(max_bytes=len(payload)-1)
    assert fds() == before


@pytest.mark.parametrize('limit', [True, -1, 1.5, '5', None])
def test_invalid_read_limit_rejected_before_any_pread(tmp_path, monkeypatch, limit):
    with handle(tmp_path, 'reader') as pair:
        def forbidden(*args):
            pytest.fail('invalid budget performed read')
        monkeypatch.setattr(j.os, 'pread', forbidden)
        with pytest.raises(j.PairFailure, match='limit_schema'):
            pair.read_bytes(max_bytes=limit)


@pytest.mark.parametrize('fault', ['bytes', 'third', 'missing_stage', 'ancestor', 'error', 'interrupt'])
def test_parent_transition_rolls_back_binding_on_owned_validation_failure(tmp_path, monkeypatch, fault):
    root = tmp_path/'ancestor'/'raw'
    root.mkdir(parents=True, mode=0o700)
    before = fds()
    with j.create_owned_pair(root/'one', b'alpha', mode=0o600) as pair:
        old = pair.parent.links
        if fault == 'bytes':
            (root/'one').write_bytes(b'xxxxx')
        elif fault == 'third':
            os.link(root/'one', root/'third')
        elif fault == 'missing_stage':
            os.rename(root/'.one.stage', root/'retained-stage')
        os.chmod(root, 0o555)
        if fault == 'ancestor':
            os.rename(root.parent, tmp_path/'retained-ancestor')
            root.mkdir(parents=True, mode=0o555)
        if fault in {'error', 'interrupt'}:
            failure = OSError if fault == 'error' else KeyboardInterrupt
            def pread(*args):
                raise failure('transition-read-fault')
            monkeypatch.setattr(j.os, 'pread', pread)
        else:
            failure = j.PairFailure
        with pytest.raises(failure):
            pair.accept_readonly_parent()
        assert pair.parent.links == old
        assert pair.parent.links[-1][3][3] == 0o700
    assert fds() == before


@pytest.mark.parametrize('kind', ['writer', 'reader'])
def test_transition_exact_inode_then_nonimmediate_modes_still_frozen(tmp_path, kind):
    root = tmp_path/'ancestor'/'raw'
    root.mkdir(parents=True, mode=0o700)
    with handle(root, kind) as pair:
        os.chmod(root, 0o555)
        pair.accept_readonly_parent()
        pair.validate(durable=True)
        with pytest.raises(j.PairFailure, match='transition'):
            pair.accept_readonly_parent()
        os.chmod(root.parent, 0o700 if stat.S_IMODE(root.parent.stat().st_mode) != 0o700 else 0o755)
        with pytest.raises(j.PairFailure, match='chain'):
            pair.validate()


@pytest.mark.parametrize('kind', ['writer', 'reader'])
def test_no_primary_multiple_close_errors_first_propagated_and_notes_complete(tmp_path, monkeypatch, kind):
    before = fds()
    pair = handle(tmp_path, kind)
    owned = {pair.fd, *pair.parent.descriptors}
    close = os.close
    seen = []
    def failed(fd):
        close(fd)
        seen.append(fd)
        raise OSError('close-' + str(fd))
    monkeypatch.setattr(j.os, 'close', failed)
    with pytest.raises(OSError, match='close-' + str(pair.fd)) as caught:
        with pair:
            pair.validate()
    assert set(seen) == owned and len(seen) == len(owned)
    assert len(caught.value.__notes__) == len(owned)-1
    assert fds() == before
    pair.close()
    assert len(seen) == len(owned)


@pytest.mark.parametrize('method', ['validate', 'read', 'transition', 'enter'])
def test_closed_handle_refuses_before_descriptor_reuse(tmp_path, method):
    pair = handle(tmp_path, 'writer')
    pair.close()
    sentinel = os.open(tmp_path/'unrelated', os.O_RDWR|os.O_CREAT|os.O_EXCL, 0o600)
    try:
        with pytest.raises(j.PairFailure, match='closed'):
            if method == 'validate':
                pair.validate(durable=True)
            elif method == 'read':
                pair.read_bytes(max_bytes=5)
            elif method == 'transition':
                pair.accept_readonly_parent()
            else:
                pair.__enter__()
        os.write(sentinel, b'unrelated')
        assert os.fstat(sentinel).st_size == 9
    finally:
        os.close(sentinel)
