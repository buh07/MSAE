VERDICT: SHIP
ONE-LINE: Exact candidates satisfy compatibility, parity, isolation, lineage, GPU ownership, and terminal-state requirements.

CAPACITY_CANDIDATE_SHA256: 6d20c743018271b3e61c40d36b3c58d5e6181a062b6663c9c778488d7bd0225c
EXTERNAL_CANDIDATE_SHA256: 8c5da60136460fa7250701dfa28e36a58b95f7f5458f4c7bb59a6fa201014b30

BLOCKERS
  - None.
REVISIONS
  - None.
CHECKS RUN
  - All 15 inventoried nonpayload files matched both exact manifests; no JSONL inspected.
  - Python compilation and launcher syntax passed; exact candidate records attest 22/22 tests plus CPU/CUDA smoke PASS.
CONTRACT COVERAGE
  - JSONL guard, exact derived AST parity, outer terminals, state machine, GPU ownership, lineage/no restore, and phase isolation -> met.
UNKNOWNS
  - None blocking.
