from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("r2parity", ROOT / "scripts/build_trained_control_r2_protocol_parity.py")
assert SPEC and SPEC.loader
m = importlib.util.module_from_spec(SPEC)
sys.modules["r2parity"] = m
SPEC.loader.exec_module(m)


def test_actual_protocol_parity_is_exact_and_bound():
    record = m.build_record()
    assert record["status"] == "PASS"
    for study in record["studies"].values():
        assert study["config"]["pass"] and study["source"]["pass"]
        assert study["source"]["unified_diff_sha256"] == study["source"]["expected_unified_diff_sha256"]


@pytest.mark.parametrize("mutation", ["run_body", "module_constant"])
def test_source_parity_rejects_unauthorized_mutation(tmp_path, mutation):
    spec = m.STUDIES["sae_capacity"]
    original = (ROOT / spec["r2_source"]).read_text()
    if mutation == "run_body":
        changed = original.replace("def run(physical_index:", "def run(physical_index:", 1).replace(
            "c=cfg();validate_environment(c);verify_frozen();", "c=cfg();validate_environment(c);verify_frozen();assert c['seed']>=0;", 1
        )
    else:
        changed = original.replace('CFG = ROOT / "configs/trained_copy_sae_capacity_v1_r2/run.json"', 'CFG = ROOT / "unauthorized.json"', 1)
    assert changed != original
    candidate = tmp_path / "mutated.py"
    candidate.write_text(changed)
    with pytest.raises(RuntimeError, match="exact authorized recovery patch"):
        m.source_parity(
            ROOT / spec["r1_source"], candidate, spec["allowed_changed_definitions"],
            m.EXPECTED_SOURCE_DIFF_SHA256["sae_capacity"], spec["r1_source"], spec["r2_source"]
        )


def test_config_parity_rejects_scientific_mutation(tmp_path):
    spec = m.STUDIES["causal_manifold"]
    changed = json.loads((ROOT / spec["r2_config"]).read_text())
    changed["gates"]["recovery"]["point_min"] += 0.01
    candidate = tmp_path / "run.json"
    candidate.write_text(json.dumps(changed))
    with pytest.raises(RuntimeError, match="unauthorized scientific config difference"):
        m.config_parity(ROOT / spec["r1_config"], candidate)
