from __future__ import annotations

import json
from pathlib import Path
import sys

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import analyze_proxy_control_benchmark_v2 as a

CFG = json.loads((ROOT / "configs/proxy_control_benchmark_v2_analysis/run.json").read_text())


def test_gate_flags_are_conjunctive() -> None:
    frame = pd.DataFrame([{
        "behavior_eligible_fraction": .9,
        "behavioral_recovery_block_ci": [.11, .2, .3],
        "behavioral_specificity_block_ci": [.11, .2, .3],
        "collateral_kl_block_ci": [.001, .01, .019],
    }, {
        "behavior_eligible_fraction": .9,
        "behavioral_recovery_block_ci": [.11, .2, .3],
        "behavioral_specificity_block_ci": [.09, .2, .3],
        "collateral_kl_block_ci": [.001, .01, .019],
    }])
    got = a.add_gate_flags(frame, CFG["thresholds"])
    assert got.joint_row_pass.tolist() == [True, False]


def test_nondominated_prefers_more_potency_and_less_damage() -> None:
    frame = pd.DataFrame({"potency": [.1, .2, .3, .1], "damage": [.01, .02, .04, .03]})
    assert a.nondominated(frame, "potency", "damage").tolist() == [True, True, True, False]


def test_named_records_are_unique() -> None:
    aggregate = json.loads((ROOT / CFG["input_root"] / "aggregate/result.json").read_text())
    assert len(a.named_hierarchical(aggregate)) == len(aggregate["hierarchical_endpoint_summaries"])
    assert len(a.named_associations(aggregate)) == len(aggregate["associations"])


def test_source_has_no_model_or_transformer_import() -> None:
    source = (ROOT / "scripts/analyze_proxy_control_benchmark_v2.py").read_text()
    assert "import torch" not in source
    assert "transformers" not in source
    assert "proxy_control_benchmark_v1" not in source
    assert "proxy_control_benchmark_v2" not in source.splitlines()[0:30]
