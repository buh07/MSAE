from __future__ import annotations

import importlib.util
import subprocess
import sys
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("sae_geometry", ROOT / "scripts/analyze_trained_copy_sae_geometry_v1.py")
assert SPEC and SPEC.loader
M = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(M)


def test_known_subspace_angles_rank_and_condition() -> None:
    d = np.array([[1.0, 0, 0], [0, 2.0, 0]])
    target = np.array([[1.0, 0, 0], [0, 1.0, 0]])
    g = M.subspace_geometry(d, target)
    assert g["numerical_rank"] == 2
    assert g["condition_number"] == pytest.approx(2.0)
    assert g["projection_coverage"] == pytest.approx(1.0)
    assert g["principal_angles_radians"] == pytest.approx([0.0, 0.0])


def test_rank_zero_sentinel() -> None:
    g = M.subspace_geometry(np.zeros((2, 3)), np.eye(3)[:2])
    assert g["numerical_rank"] == 0
    assert g["condition_number"] == "infinite"
    assert g["principal_angles_radians"] == []
    assert g["projection_coverage"] == 0.0


def test_artifact_firewall_rejects_panel_and_no_model_import() -> None:
    with pytest.raises(PermissionError):
        M.assert_input(ROOT / "data/trained_copy_sae_capacity_v1_prepared/development.jsonl")
    code=f"import runpy,sys;runpy.run_path({str(ROOT / 'scripts/analyze_trained_copy_sae_geometry_v1.py')!r},run_name='analysis_import_only');assert 'capacity_external_validity_v1_r5' not in sys.modules"
    subprocess.run([sys.executable,"-c",code],check=True)


def test_observed_and_geometry_budget_contracts() -> None:
    assert M.BUDGETS_OBSERVED == (16, 32, 64, 128, 256)
    assert M.BUDGETS_GEOMETRY == (16, 32, 64, 128, 160, 192, 224, 256)
