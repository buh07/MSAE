VERDICT: BLOCK
ONE-LINE: Frozen prompts and panels violate registered hashing, no-binding, balance, preservation, and outcome rules.

BLOCKERS
  - [critical] scripts/behavioral_endpoint_v6.py:25,54,100 — 64-bit selection hashing and the text-hash convention required correction and known-vector tests.
  - [critical] scripts/behavioral_endpoint_v6.py:129-138,182-191 — no-binding prompts leaked the query key and filler candidate strings.
  - [high] scripts/behavioral_endpoint_v6.py:139-164 — random balanced shuffles did not satisfy the registered cyclic Latin verb incidence.
  - [high] scripts/behavioral_endpoint_v6.py:371 — one all-template family was incorrectly classified TEMPLATE_CONDITIONED instead of INSUFFICIENT_MODEL_REPLICATION.
  - [high] reports/provenance/behavioral_endpoint_v6_candidate/V5_PRESERVATION.json:1 — seven V5 frozen candidate dependencies were absent.
  - [high] tests/test_behavioral_endpoint_v6.py:151-180 — estimator, hierarchy, boundary, timeout, and outcome tests were incomplete.

REVISIONS
  - Freeze minimum-length rejection records.
  - Bind V5 COMPLETE terminals directly in the analysis-only report.
  - Publish TIMEOUT terminals distinctly.
  - Accept a fast launcher stage only with a validated clean terminal.

CHECKS RUN
  - py_compile → pass.
  - pytest tests/test_behavioral_endpoint_v6.py → 15 passed, but coverage gaps remained.
  - bash -n launcher → pass.
  - frozen-row audits → no-binding leakage and agreement-incidence imbalance reproduced.
  - V5 freeze-inventory comparison → seven omissions reproduced.

CONTRACT COVERAGE
  - V5 preservation → partial.
  - V5 analysis-only report → partial.
  - fresh selection/exclusions → partial.
  - retrieval no-binding condition → unmet.
  - agreement incidence → unmet.
  - confirmation firewall/GPU mapping/no training → met.
  - outcome table/terminal tests → unmet.

UNKNOWNS
  - No GPU model forward was run.

FOLLOW-UP NOTE
  - The review's statement that V5 text hashes were case-sensitive was itself incorrect: V5 `norm()` lowercases text. The fix retains V5-compatible lowercased normalized hashes while adopting the registered full 64-bit v6 selection PRF.
