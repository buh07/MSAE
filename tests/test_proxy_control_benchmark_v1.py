from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pytest
import torch

from proxy_control_benchmark_v1 import (
    TopKBranch,
    assign_k2_branch,
    bootstrap_interval,
    canonical_json,
    centered_cka,
    classify_equivalence,
    exclusive_json,
    generate_synthetic,
    make_controlled_specs,
)


def test_controlled_specs_are_deterministic_disjoint_and_supported() -> None:
    a = make_controlled_specs(seed=17, source="SOURCE_A", per_concept=20)
    b = make_controlled_specs(seed=17, source="SOURCE_B", per_concept=20)
    assert a == make_controlled_specs(seed=17, source="SOURCE_A", per_concept=20)
    assert len(a) == len(b) == 60
    assert {r["concept"] for r in a} == {"relative_position", "lexical", "context"}
    assert not ({r["component_id"] for r in a} & {r["component_id"] for r in b})
    assert not ({r["base_prompt"] for r in a} & {r["base_prompt"] for r in b})


def test_topk_branch_has_exact_budget_and_finite_reconstruction() -> None:
    torch.manual_seed(3)
    branch = TopKBranch(7, 19, 4)
    x = torch.randn(11, 7)
    recon, code = branch(x)
    assert recon.shape == x.shape
    assert torch.isfinite(recon).all()
    assert torch.all((code != 0).sum(dim=-1) <= 4)


def test_branch_assignment_is_permutation_invariant() -> None:
    a = np.asarray([[0.0, 0.0], [3.0, 0.0]])
    b = np.asarray([[0.0, 0.0], [0.2, 0.0]])
    assert assign_k2_branch(a, b) == 0
    assert assign_k2_branch(b, a) == 1


def test_cka_identity_and_degenerate_handling() -> None:
    rng = np.random.default_rng(2)
    x = rng.normal(size=(32, 8))
    assert centered_cka(x, x) == pytest.approx(1.0)
    assert np.isnan(centered_cka(np.ones((10, 3)), np.ones((10, 3))))


def test_bootstrap_and_equivalence_are_deterministic() -> None:
    x = np.linspace(-0.03, 0.03, 40)
    a = bootstrap_interval(x, draws=100, seed=5)
    b = bootstrap_interval(x, draws=100, seed=5)
    assert a == b
    assert classify_equivalence(a[0], a[2], 0.1) == "EQUIVALENT_SMALL"
    assert classify_equivalence(-0.2, 0.2, 0.1) == "INCONCLUSIVE"
    assert classify_equivalence(0.11, 0.3, 0.1) == "POSITIVE_MATERIAL"


def test_synthetic_generator_has_private_shared_ground_truth() -> None:
    d = generate_synthetic(seed=9, rows=128, width=32, correlation=0.5, shared_scale=0.7, nonlinear=False)
    assert d["x"].shape == (128, 32)
    assert d["position"].shape == d["lexical"].shape == d["shared"].shape == (128, 32)
    np.testing.assert_allclose(d["x"], d["position"] + d["lexical"] + d["shared"] + d["noise"], atol=1e-6)


def test_exclusive_json_is_canonical_and_create_once(tmp_path: Path) -> None:
    p = tmp_path / "x.json"
    exclusive_json(p, {"z": 1, "a": [2, 3]})
    assert p.read_bytes() == canonical_json({"a": [2, 3], "z": 1}) + b"\n"
    with pytest.raises(FileExistsError):
        exclusive_json(p, {"a": 2})
    assert json.loads(p.read_text()) == {"a": [2, 3], "z": 1}
