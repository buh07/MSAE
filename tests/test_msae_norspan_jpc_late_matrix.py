# Maintained copy of retained independent synthetic matrix; original unchanged.
"""Independent synthetic bounded contract counterexamples, no real operations."""
import hashlib
import os
from pathlib import Path
import sys
import pytest
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import msae_jumbo_pair_commit as j
import msae_norspan_jpc_runtime as r

@pytest.mark.parametrize('kind', ['flat_publish', 'flat_verify', 'role_publish', 'role_verify', 'recovery'])
def test_earlier_pair_mutation_during_last_durable_digest_rejected(tmp_path, monkeypatch, kind):
    root = tmp_path / 'aggregate'
    first = root / 'one'
    final_name = 'two'
    if kind.startswith('role'):
        first = root / 'discovery' / 'payload.jsonl'
        final_name = 'payload.jsonl'
        values = {role: b'aaaa' for role in r.ROLES}
        if kind == 'role_verify':
            values = r.publish_role_pairs(root, values)
        def operation():
            if kind == 'role_verify':
                return r.verify_role_pairs(root, values, durable=True)
            return r.publish_role_pairs(root, values)
    elif kind.startswith('flat'):
        values = {'one': b'aaaa', 'two': b'zzzz'}
        if kind == 'flat_verify':
            values = r.publish_flat_pairs(root, values, directory_mode=0o700, file_mode=0o644)
        def operation():
            if kind == 'flat_verify':
                return r.verify_flat_pairs(root, values, directory_mode=0o700, file_mode=0o644, durable=True)
            return r.publish_flat_pairs(root, values, directory_mode=0o700, file_mode=0o644)
    else:
        root.mkdir(mode=0o700)
        first = root / 'baseline.json'
        final_name = 'authority.json'
        values = {'schema_version': 'norspan_jpc_custody_catalog_v1', 'lineage_sha256': 'a'*64,
                  'controls': {name: j.receipt_record(j.create_pair(root/name, b'aaaa', mode=0o644))
                               for name in ['baseline.json', 'authority.json']}}
        digest = hashlib.sha256(r.canonical_bytes(values)).hexdigest()
        def operation():
            return r.recover_current_custody(root, values, expected_catalog_sha256=digest, lineage_sha256='a'*64)
    real_validate, real_pread = j.OwnedPair.validate, os.pread
    armed, fired = [], []
    def validate(pair, *, durable=False):
        is_last = pair.receipt.final_name == final_name
        if kind.startswith('role'):
            is_last = is_last and os.readlink(f'/proc/self/fd/{pair.fd}').startswith(str(root/'c2')+'/')
        if durable and is_last:
            armed.append(True)
        return real_validate(pair, durable=durable)
    def pread(fd, size, offset):
        result = real_pread(fd, size, offset)
        if armed and not fired:
            fired.append(True)
            first.write_bytes(b'bbbb')
        return result
    monkeypatch.setattr(j.OwnedPair, 'validate', validate)
    monkeypatch.setattr(os, 'pread', pread)
    with pytest.raises((r.RuntimeBlocked, j.PairFailure)):
        result = operation()
        assert fired == [True] and first.read_bytes() == b'bbbb'
        pytest.fail('False current-custody success after earlier retained pair bytes changed: '+repr(result))
    assert fired == [True] and first.read_bytes() == b'bbbb'

@pytest.mark.parametrize('kind', ['late_home_extra', 'late_file_budget'])
def test_scratch_final_scan_late_previous_subtree_mutation_rejected(tmp_path, monkeypatch, kind):
    with r.reserve_scratch(tmp_path/'lease', authority_sha256='a'*64, entry_lineage_sha256='b'*64) as scratch:
        repo = scratch.path/'repo'
        repo.mkdir(mode=0o700)
        first = repo/'one'
        first.write_bytes(b'aaaa')
        (repo/'two').write_bytes(b'zzzz')
        real_validate, real_stat = r._Directory.validate, os.stat
        armed, fired = [], []
        def validate(directory, names=None, *, durable=False):
            result = real_validate(directory, names, durable=durable)
            if directory is scratch and durable:
                armed.append(True)
            return result
        def stat(name, *args, **kwargs):
            result = real_stat(name, *args, **kwargs)
            wanted = (name == 'repo' and kwargs.get('dir_fd') == scratch.fd) if kind == 'late_home_extra' else name == 'two'
            if armed and not fired and wanted:
                fired.append(True)
                if kind == 'late_home_extra':
                    (scratch.path/'home'/'foreign').write_bytes(b'foreign')
                else:
                    first.write_bytes(b'over-budget-synthetic-bytes')
            return result
        monkeypatch.setattr(r._Directory, 'validate', validate)
        monkeypatch.setattr(os, 'stat', stat)
        with pytest.raises((r.RuntimeBlocked, j.PairFailure)):
            result = scratch.snapshot(durable=True, file_bytes=4, total_bytes=8, entries=10)
            assert fired == [True]
            pytest.fail('False bounded pristine scratch success: '+repr(result))
        assert fired == [True]
