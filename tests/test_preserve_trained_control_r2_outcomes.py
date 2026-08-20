from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("preserve_r2", ROOT / "scripts/preserve_trained_control_r2_outcomes.py")
assert SPEC and SPEC.loader
M = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(M)


def test_inventory_is_deterministic_and_has_terminals() -> None:
    a = M.inventory()
    assert a == M.inventory()
    assert "results/trained_copy_sae_capacity_v1_r2_20260813/final/result.json" in a
    assert "reports/provenance/causal_manifold_bridge_v1_r2_run_20260813/TERMINAL.json" in a


def test_forbidden_bridge_outputs_absent() -> None:
    assert all(not (ROOT / p).exists() for p in M.FORBIDDEN)


def test_verify_rejects_inventory_change(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    items = M.inventory()
    fake = tmp_path / "manifest.json"
    fake.write_text('{"items": {}}')
    monkeypatch.setattr(M, "OUT", fake)
    with pytest.raises(RuntimeError, match="preservation mismatch"):
        M.verify()
