import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from atlas_metrics import (align_components, bh_adjust, chance_score, family_summary, fit_probe, normalized_recovery,
                           principal_angles_degrees, simultaneous_bounds)


def test_undefined_normalization_is_not_epsilon_filled():
    assert normalized_recovery(0.51, 0.51, 0.50, raw_gap_lcb=0.0) is None
    assert np.isclose(normalized_recovery(0.80, 0.90, 0.50, raw_gap_lcb=0.30), 0.75)


def test_family_selectivity_and_leakage():
    row = family_summary([0.9, 0.8], [[0.2, 0.3], [None, 0.1]])
    assert np.isclose(row["assigned_recovery"], 0.85)
    assert np.isclose(row["leakage"], 0.25)
    assert np.isclose(row["selectivity_margin"], 0.60)


def test_bh_reference_values():
    assert np.allclose(bh_adjust([0.01, 0.04, 0.03, 0.20]), [0.04, 0.05333333333333334, 0.05333333333333334, 0.20])


def test_scaler_fits_train_only():
    x = np.array([[0.0, 0.0], [2.0, 2.0]])
    probe = fit_probe(x, np.array([0, 1]), 1.0)
    assert np.allclose(probe.scaler_mean, [1.0, 1.0])
    assert not np.allclose(probe.transform(np.array([[100.0, 100.0]])).mean(), 0)


def test_chance_macro_f1_is_not_majority_floor():
    y_fit = np.array([0, 1] * 50)
    y_eval = np.array([0, 1] * 40)
    assert np.isclose(chance_score(y_fit, y_eval), 0.5)


def test_permutation_sign_alignment():
    reference = np.eye(3, 5)
    candidate = np.stack([-reference[2], reference[0], -reference[1]])
    aligned, score = align_components(reference, candidate)
    assert np.allclose(aligned, reference)
    assert score == 1.0


def test_principal_angles_orthogonal():
    angles = principal_angles_degrees(np.eye(4)[:, :2], np.eye(4)[:, 2:])
    assert np.allclose(angles, 90.0)


def test_simultaneous_bounds_enforce_valid_draw_contract():
    observed = np.array([0.1, -0.02])
    with np.testing.assert_raises_regex(ValueError, "at least 450"):
        simultaneous_bounds(observed, np.zeros((449, 2)))
    bad = np.zeros((450, 2)); bad[0, 0] = np.nan
    with np.testing.assert_raises_regex(ValueError, "finite"):
        simultaneous_bounds(observed, bad)
    lower, upper = simultaneous_bounds(observed, np.tile(observed, (450, 1)))
    assert np.allclose(lower, observed) and np.allclose(upper, observed)
