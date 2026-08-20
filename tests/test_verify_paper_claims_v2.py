import importlib.util
import json
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "verify_paper_claims", ROOT / "scripts/verify_paper_claims.py"
)
assert SPEC and SPEC.loader
MOD = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MOD)


def test_v2_rendered_numbers_are_bound() -> None:
    ledger = json.loads((ROOT / "reports/paper_claim_ledger_v1.json").read_text())
    paper = (ROOT / "PAPER.md").read_text()
    assert MOD.verify_claims(ledger, paper, ROOT)["status"] == "PASS"

    mutations = [
        ("Clean and sham patches reproduced", "Clean and sham patches did not reproduce", "C070"),
        ("1.000 [1.000, 1.000]", "0.999 [1.000, 1.000]", "C070"),
        ("0.093 [0.049, 0.137]", "0.093 [0.000, 0.137]", "C071"),
        ("0.166 [0.145, 0.188]", "0.199 [0.145, 0.188]", "C071"),
        ("0.101 [0.081, 0.122]", "0.101 [0.000, 0.122]", "C071"),
        ("0.084 [0.069, 0.100]", "0.084 [0.069, 0.999]", "C071"),
        ("not enough to satisfy the prospective control gates", "enough to satisfy every prospective control gate", "C071"),
    ]
    for old, new, claim_id in mutations:
        mutated = paper.replace(old, new, 1)
        with pytest.raises(SystemExit, match=f"paper selector drift {claim_id}"):
            MOD.verify_claims(ledger, mutated, ROOT)
