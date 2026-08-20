# Minimal Synthetic Metric Smoke

**Verdict: PASS.** Machine-readable result: `results/synthetic/atlas_v1_smoke.json` (SHA-256 `0c19199cca4b45a39fbb92b9080343e03d2d1756c23c8297716f5323c002ef04`). The output was generated twice byte-identically. Test gate: **16 passed** (`tests/test_atlas_metrics.py`, `tests/test_atlas_data.py`).

## Planted regimes

| Regime | Required behavior | Observed |
|---|---|---|
| three orthogonal families | high assigned recovery, low leakage | recovery `1.0`; leakage `0.031`, `-0.059`, `-0.098`; abs/struct angles `89.1°/89.4°` |
| overlapping assignment | fail selectivity | recovery/leakage `0.89/0.89`; margin `0.0` |
| absent or near-zero family | undefined denominator; no epsilon | undefined |
| shuffled labels | no promotion | macro-F1 `0.480` vs analytic prior-chance `0.499`; undefined recovery |
| source-confound reversal | fail transfer | macro-F1 `0.0` |
| duplicate cross-role document | production firewall rejects it | detected |
| label-vocabulary leakage | unseen label maps to `__DROP__` | passed |
| train-only standardization | evaluation cannot change scaler | discovery mean preserved |
| permutation/sign ambiguity | alignment restores planted ordering | mean similarity `1.0` |
| exhaustive G1/G2 decision renderer | every terminal branch reachable | equivocal/simple/learned/negative fixtures passed |
| fallback-rule helper | true/false unit fixtures (production fallback is disabled) | both passed |

The shuffled fixture found a design flaw before freeze: majority macro-F1 is not an appropriate normalized no-information denominator. Atlas-v1 now uses analytic discovery-prior chance macro-F1 and reports majority only descriptively.

## Statistics and production-path exercise

- 500 bootstrap draws **refit the scaler, ridge probes, and task-derived subspaces** (eight refits per draw); planted selectivity CI `[0.8043, 1.3602]`.
- Grouped effect CI `[0.2383, 0.2650]` has the planted positive direction.
- 9,999 sign flips give `p=0.0001`; worst-case Monte Carlo SE `0.00500 < 0.01`.
- BH reference result is `[0.04, 0.05333, 0.05333, 0.20]`.
- Single-step centered max-stat simultaneous bounds are exercised on a two-coordinate vector.

This gate validates metric behavior and determinism on a small fixture, not neural compute feasibility or statistical power of the realized C1/C2 document groups. Those limitations remain capable of forcing an equivocal result.
