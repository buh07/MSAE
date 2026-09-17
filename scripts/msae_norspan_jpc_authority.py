"""Detached exact-candidate approval verification; enrollment is outside this code.

No signing or trust-on-first-use. Caller pins MUST come from an authenticated
owner channel. Disposable synthetic test keys do not establish real authority.
This module never removes the unconditional production qualification guard.
"""
from __future__ import annotations

import fcntl
import hashlib
import os
from pathlib import Path
import subprocess

import msae_jumbo_pair_commit as j
import msae_norspan_jpc_runtime as r

MAX_STATEMENT_BYTES = 4 * 1024**2
ED25519_DER_PREFIX = bytes.fromhex('302a300506032b6570032100')
IMPLEMENTATION_REVIEW = 'reports/adversarial/msae_norspan_controller_whole_review.md'
AUTHORITY_REVIEW = 'reports/adversarial/msae_independent_norspan_v1_authority_review.md'
# Explicit prospective finite additions; no directory/prefix alias exemptions.
INTEGRATION_MODES = {
    'scripts/msae_jumbo_pair_commit.py': 0o644,
    'scripts/msae_norspan_jpc_runtime.py': 0o700,
    'scripts/msae_norspan_jpc_controls.py': 0o700,
    'scripts/msae_norspan_jpc_controller.py': 0o700,
    'scripts/msae_norspan_jpc_authority.py': 0o700,
    'configs/msae_independent_norspan_v1/jumbo_client_storage_v1.json': 0o644,
    'docs/contract-msae-norspan-jumbo-client-storage-v3.md': 0o700,
    'docs/plan-msae-norspan-controller-qualification-v1.md': 0o700,
    'docs/plan-msae-norspan-controller-recovery-metadata-supplement-v1.md': 0o700,
    'docs/plan-msae-norspan-controller-history-custody-supplement-v1.md': 0o700,
    'docs/plan-msae-norspan-controller-credential-stop-supplement-v1.md': 0o700,
    'docs/plan-msae-norspan-controller-observation-supplement-v1.md': 0o700,
    'docs/plan-msae-norspan-controller-descriptor-admission-supplement-v1.md': 0o700,
    'docs/plan-msae-norspan-controller-fifo-diagnostics-supplement-v1.md': 0o700,
    'docs/plan-msae-norspan-controller-aggregate-admission-supplement-v1.md': 0o700,
    'docs/plan-msae-norspan-controller-authority-admission-supplement-v1.md': 0o700,
    'docs/plan-msae-norspan-owner-approval-receipt-v1.md': 0o700,
    'scripts/msae_norspan_owner_approval.py': 0o700,
    'tests/test_msae_norspan_owner_approval.py': 0o644,
    'tests/test_msae_norspan_jpc_controller.py': 0o644,
    'tests/test_msae_norspan_jpc_authority.py': 0o644,
    'tests/msae_norspan_controller_fixture.py': 0o644,
    'tests/test_msae_norspan_jpc_full_recovery.py': 0o644,
    'tests/test_msae_norspan_jpc_controller_matrix.py': 0o644,
    IMPLEMENTATION_REVIEW: 0o644,
}


def _sealed_bytes(value: bytes) -> int:
    fd = os.memfd_create('norspan-approval-input', os.MFD_CLOEXEC | os.MFD_ALLOW_SEALING)
    try:
        view = memoryview(value)
        while view:
            count = os.write(fd, view)
            if count <= 0:
                raise r.RuntimeBlocked('approval_memfd_short_write')
            view = view[count:]
        os.lseek(fd, 0, os.SEEK_SET)
        seals = fcntl.F_SEAL_WRITE | fcntl.F_SEAL_GROW | fcntl.F_SEAL_SHRINK | fcntl.F_SEAL_SEAL
        fcntl.fcntl(fd, fcntl.F_ADD_SEALS, seals)
        if fcntl.fcntl(fd, fcntl.F_GET_SEALS) != seals:
            raise r.RuntimeBlocked('approval_memfd_seals')
        return fd
    except BaseException as exc:
        j._close_fds([fd], primary=exc)
        raise


def verify_signature(key: bytes, statement: bytes, signature: bytes, *, key_sha256: str) -> None:
    r._sha_literal(key_sha256, 'approval_key')
    if (type(key) is not bytes or len(key) != 44 or not key.startswith(ED25519_DER_PREFIX)
            or hashlib.sha256(key).hexdigest() != key_sha256
            or type(statement) is not bytes or not 1 <= len(statement) <= MAX_STATEMENT_BYTES
            or type(signature) is not bytes or len(signature) != 64):
        raise r.RuntimeBlocked('approval_signature_input')
    r.admit_observation_fds(additional=3)
    fds = []
    primary = None
    try:
        for value in (key, statement, signature):
            fds.append(_sealed_bytes(value))
        key_fd, statement_fd, signature_fd = fds
        result = subprocess.run([
            '/usr/bin/openssl', 'pkeyutl', '-verify', '-rawin', '-pubin', '-keyform', 'DER',
            '-inkey', '/proc/self/fd/' + str(key_fd), '-in', '/proc/self/fd/' + str(statement_fd),
            '-sigfile', '/proc/self/fd/' + str(signature_fd)],
            stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            close_fds=True, pass_fds=tuple(fds), timeout=10,
            env={'PATH': '/usr/bin:/bin', 'OPENSSL_CONF': '/dev/null', 'LC_ALL': 'C'})
        if result.returncode != 0:
            raise r.RuntimeBlocked('approval_signature_invalid')
    except BaseException as exc:
        primary = exc
        raise
    finally:
        j._close_fds(list(reversed(fds)), primary=primary)


class Approvals:
    """Caller-authenticated key + independently pinned signed approval statements.

    Pin enrollment is an external obligation. Constructing this object does not
    grant launch capability or certify where a caller obtained their pins.
    """
    authentication_method = 'ed25519_detached'

    def __init__(self, root: Path, *, key: bytes, key_sha256: str,
                 release: bytes, release_signature: bytes, release_sha256: str):
        self.root = root
        self.key, self.key_sha256 = key, key_sha256
        self.release, self.release_signature, self.release_sha256 = release, release_signature, release_sha256
        self._authority = None
        self.verify_release()

    def _statement(self, raw, signature, expected_sha256, scope):
        r._sha_literal(expected_sha256, 'approval_statement')
        if type(raw) is not bytes or not 1 <= len(raw) <= MAX_STATEMENT_BYTES:
            raise r.RuntimeBlocked('approval_statement_size')
        if hashlib.sha256(raw).hexdigest() != expected_sha256:
            raise r.RuntimeBlocked('approval_statement_pin')
        verify_signature(self.key, raw, signature, key_sha256=self.key_sha256)
        value = r._json(raw)
        if (type(value) is not dict or raw != r.canonical_bytes(value) + b'\n'
                or value.get('schema_version') != 'norspan_signed_approval_v1'
                or value.get('scope') != scope or value.get('verdict') != 'SHIP'):
            raise r.RuntimeBlocked('approval_statement_schema_scope')
        return value

    def verify_release(self):
        import prepare_msae_independent_norspan_v1 as p
        value = self._statement(self.release,self.release_signature,self.release_sha256,'whole_implementation')
        modes = {rel:mode for rel,mode in p.AUTHORITY_CONTROL_MODES.items()
                 if not rel.startswith('reports/provenance/')}
        modes.update({'TODO.md':0o644, 'scripts/prepare_msae_independent_source_v10.py':0o755})
        if set(value) != {'schema_version','scope','verdict','subjects'} or type(value['subjects']) is not dict or set(value['subjects']) != set(modes):
            raise r.RuntimeBlocked('approval_candidate_subjects')
        from msae_norspan_jpc_controller import _CatalogReader
        resources=[];primary=None
        try:
            for rel, mode in modes.items():
                subject = value['subjects'][rel]
                if type(subject) is not dict or set(subject) != {'sha256','bytes','mode'}:
                    raise r.RuntimeBlocked('approval_subject_schema')
                r._sha_literal(subject['sha256'],'approval_subject')
                if type(subject['bytes']) is not int or not 0 <= subject['bytes'] <= r.FILE_BYTES_LIMIT or type(subject['mode']) is not int or subject['mode'] != mode:
                    raise r.RuntimeBlocked('approval_subject_literals')
                reader = _CatalogReader(self.root/rel,subject['sha256'],mode=mode,expected_count=subject['bytes'])
                resources.append(reader)
            for reader in resources:reader.validate()
            for reader in resources:reader.fence()
        except BaseException as exc:
            primary=exc
            raise
        finally:
            r._close_resources(resources,primary=primary)
        return self.root / IMPLEMENTATION_REVIEW

    def bind_authority(self, raw: bytes, signature: bytes, *, expected_sha256: str):
        # Verify cryptography/schema now, containing receipt/current pair at each use.
        value = self._statement(raw,signature,expected_sha256,'source_authority')
        if set(value) != {'schema_version','scope','verdict','release_sha256','lineage_sha256','authority_pair','review_sha256'}:
            raise r.RuntimeBlocked('approval_authority_schema')
        for field in ['release_sha256','lineage_sha256','review_sha256']:
            r._sha_literal(value[field],'authority_'+field)
        receipt = j.receipt_from_record(self.root/'reports/provenance/msae_independent_norspan_v1/authority.json',
                                        value['authority_pair'])
        if receipt.mode != 0o644:
            raise r.RuntimeBlocked('approval_authority_mode')
        self._authority = (raw, signature, expected_sha256)

    def verify_authority(self, session):
        self.verify_release()
        if self._authority is None:
            raise r.RuntimeBlocked('authenticated_source_authority_pending')
        value = self._statement(*self._authority,'source_authority')
        if value['release_sha256'] != self.release_sha256 or value['lineage_sha256'] != session.lineage:
            raise r.RuntimeBlocked('approval_authority_lineage')
        receipt = session.expected('authority.json')
        signed_receipt = j.receipt_from_record(session.root/'authority.json',value['authority_pair'])
        if r.canonical_bytes(j.receipt_record(signed_receipt)) != r.canonical_bytes(j.receipt_record(receipt)):
            raise r.RuntimeBlocked('approval_authority_receipt')
        r.admit_observation_fds(session.root/'authority.json')
        with j.open_owned_pair(session.root/'authority.json',receipt) as pair:
            pair.validate()
        r._sha_literal(value['review_sha256'],'authority_review')
        review = self.root / AUTHORITY_REVIEW
        r.admit_observation_fds(review)
        if hashlib.sha256(r.read_ordinary_file(review)).hexdigest() != value['review_sha256']:
            raise r.RuntimeBlocked('approval_authority_review_drift')
        return review
