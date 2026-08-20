from __future__ import annotations

import hashlib
import importlib.util
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("r1preserve", ROOT / "scripts/preserve_trained_control_r1_failures.py")
assert SPEC and SPEC.loader
m = importlib.util.module_from_spec(SPEC)
sys.modules["r1preserve"] = m
SPEC.loader.exec_module(m)


def test_actual_preservation_and_exposure_attestation_verify():
    result = m.verify()
    assert result["status"] == "PASS"
    record = json.loads(m.OUT.read_text())
    assert all(record["absence_audit"].values())
    attestation = json.loads(m.ATTEST.read_text())
    signature = attestation.pop("statement_sha256")
    assert hashlib.sha256(m.canonical(attestation)).hexdigest() == signature
    assert attestation["sae_capacity_r1"]["possible_transient_native_development_scores"] == 1
    assert not attestation["sae_capacity_r1"]["confirmation_opened"]
    assert not attestation["causal_manifold_r1"]["development_opened"]


def test_root_inventory_detects_addition_deletion_and_corruption(tmp_path):
    root = tmp_path / "partial"
    (root / "empty").mkdir(parents=True)
    artifact = root / "a.bin"
    artifact.write_bytes(b"stable")
    original_root, original = m.ROOT, None
    try:
        m.ROOT = tmp_path
        original = m.root_record(root)
        artifact.write_bytes(b"corrupt")
        assert m.root_record(root) != original
        artifact.write_bytes(b"stable")
        (root / "new.bin").write_bytes(b"added")
        assert m.root_record(root) != original
        (root / "new.bin").unlink()
        artifact.unlink()
        assert m.root_record(root) != original
    finally:
        m.ROOT = original_root
