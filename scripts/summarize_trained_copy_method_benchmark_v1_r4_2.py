#!/usr/bin/env python3
"""Create a compact claim-ledger source from the immutable R4.2 final result."""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
from typing import Any

ROOT = Path(os.environ.get("MSAE_ROOT", Path(__file__).resolve().parents[1])).resolve()
SOURCE = ROOT / "results/trained_copy_method_benchmark_v1_20260810r4_2/final/result.json"
OUT = ROOT / "reports/trained_copy_method_benchmark_v1_r4_2_postresult_summary.json"
EXPECTED = "817afa4c2c2bccc543d92ec0975f3e1db619d5e78b29883c269fe07aca5e22f8"


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def metric_range(result: dict[str, Any], prefix: str, metric: str, estimand: str = "native") -> dict[str, float]:
    values: list[float] = []
    for stage in ("development", "confirmation"):
        for seed_data in result[stage].values():
            for name, record in seed_data["methods"].items():
                if name.startswith(prefix):
                    values.append(float(record[estimand]["metrics"][metric]["point"]))
    if not values:
        raise RuntimeError(f"no metrics for {prefix}:{estimand}:{metric}")
    return {"min": min(values), "max": max(values)}


def build() -> dict[str, Any]:
    if sha(SOURCE) != EXPECTED:
        raise RuntimeError("R4.2 result drift")
    result = json.loads(SOURCE.read_text())
    family = result["family_pass_all_checkpoints_both_panels"]
    passed = sorted(name for name, value in family.items() if value)
    return {
        "schema_version": "trained_copy_method_benchmark_v1_r4_2_postresult_summary",
        "source_path": SOURCE.relative_to(ROOT).as_posix(),
        "source_sha256": EXPECTED,
        "status": result["status"],
        "confirmation_opened": result["confirmation_opened"],
        "estimated_controller_evaluated_on_trained_copy": True,
        "family_pass_all_checkpoints_both_panels": family,
        "passed_families": passed,
        "sufficient_global_rank_bracket": {"lower_exclusive": 16, "upper_inclusive": 32},
        "random_rank64_identity_equivalent": True,
        "sae_scope": {"token_topk": 16, "selected_features": 16, "width": 256},
        "target_nonlinear_rank16": {
            "recovery": metric_range(result, "target_nonlinear_rank16_", "recovery"),
            "sham_specificity": metric_range(result, "target_nonlinear_rank16_", "sham_specificity"),
            "collateral_error": metric_range(result, "target_nonlinear_rank16_", "collateral_error"),
        },
        "target_nonlinear_rank32": {
            "recovery": metric_range(result, "target_nonlinear_rank32_", "recovery"),
            "full_vocab_recovery": metric_range(result, "target_nonlinear_rank32_", "full_vocab_recovery"),
            "collateral_error": metric_range(result, "target_nonlinear_rank32_", "collateral_error"),
        },
        "scope": result["scope"],
        "information_contracts": result["method_table"]["information_contracts"],
    }


def main() -> None:
    payload = build()
    if OUT.exists():
        if json.loads(OUT.read_text()) != payload:
            raise RuntimeError("summary exists with different content")
    else:
        OUT.write_text(json.dumps(payload, indent=2, sort_keys=True, allow_nan=False) + "\n")
    print(json.dumps({"status": "PASS", "path": OUT.relative_to(ROOT).as_posix(), "sha256": sha(OUT)}, sort_keys=True))


if __name__ == "__main__":
    main()
