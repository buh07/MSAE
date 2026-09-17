"""Externally enrolled owner-origin Markdown receipts; no signing key required.

Integrity/scope verification only. Expected receipt pins MUST be enrolled through
an authenticated owner conversation or confirmation of an owner-edited document.
This code cannot prove chat authorship or distinguish human/agent same-UID writes.
An agent-created proof string, discovered file or caller-selected hash is NOT
production enrollment. PENDING requests never authorize; the launch guard remains.
"""
from __future__ import annotations

from pathlib import Path
import hashlib

import msae_norspan_jpc_authority as a
import msae_norspan_jpc_runtime as r

HEADER = b'# NORSPAN owner approval receipt v1\n\nDecision: '
FENCE = b'\n\n```json\n'
END = b'```\n'
CHANNELS = {'owner_conversation','owner_manually_edited_document'}


def owner_receipt_bytes(decision: str, *, proof: dict, statement: dict) -> bytes:
    """Format bytes only; never enroll, infer approval, change a decision or write."""
    if type(decision) is not str or decision not in {'APPROVE','PENDING','REJECT'}:
        raise r.RuntimeBlocked('owner_approval_decision')
    value = {'schema_version':'norspan_owner_approval_receipt_v1',
             'owner_proof':proof,'statement':statement}
    return HEADER + decision.encode('ascii') + FENCE + r.canonical_bytes(value) + b'\n' + END


class OwnerApprovals(a.Approvals):
    """All existing retained candidate/source custody validators, no crypto claim.

    External owner enrollment of FINAL APPROVE receipt bytes/pins is required.
    owner_proof.reference is context, not an independently verified artifact table.
    Inherited verification checks the finite production subjects, not all files in
    any milestone checkpoint mentioned in that reference. No launch capability.
    """
    authentication_method = 'owner_origin_pinned_markdown'

    def __init__(self, root: Path, *, release: bytes, release_sha256: str):
        self.root = root
        self.release,self.release_sha256 = release,release_sha256
        self.release_signature = None
        self._authority = None
        self.verify_release()

    def _statement(self, raw, signature, expected_sha256, scope):
        r._sha_literal(expected_sha256,'owner_approval_receipt')
        if (signature is not None or type(raw) is not bytes
                or not 1 <= len(raw) <= a.MAX_STATEMENT_BYTES):
            raise r.RuntimeBlocked('owner_approval_input')
        if hashlib.sha256(raw).hexdigest() != expected_sha256:
            raise r.RuntimeBlocked('owner_approval_receipt_pin')
        prefix = HEADER + b'APPROVE' + FENCE
        if not raw.startswith(prefix) or not raw.endswith(END):
            raise r.RuntimeBlocked('owner_approval_decision_format')
        body = raw[len(prefix):-len(END)]
        value = r._json(body)
        if (type(value) is not dict or body != r.canonical_bytes(value)+b'\n'
                or set(value) != {'schema_version','owner_proof','statement'}
                or value['schema_version'] != 'norspan_owner_approval_receipt_v1'):
            raise r.RuntimeBlocked('owner_approval_receipt_schema_canonical')
        proof = value['owner_proof']
        if (type(proof) is not dict or set(proof) != {'channel','reference','text'}
                or type(proof['channel']) is not str or proof['channel'] not in CHANNELS):
            raise r.RuntimeBlocked('owner_approval_proof_schema')
        for field in ['reference','text']:
            text = proof[field]
            if (type(text) is not str or not 1 <= len(text) <= 2048 or not text.strip()
                    or any(not char.isprintable() for char in text)):
                raise r.RuntimeBlocked('owner_approval_proof_text')
        statement = value['statement']
        if (type(statement) is not dict
                or statement.get('schema_version') != 'norspan_owner_approval_statement_v1'
                or statement.get('scope') != scope or statement.get('verdict') != 'SHIP'):
            raise r.RuntimeBlocked('owner_approval_statement_schema_scope')
        return statement
