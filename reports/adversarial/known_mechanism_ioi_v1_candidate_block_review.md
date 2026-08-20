VERDICT: BLOCK
ONE-LINE: Unbounded downstream waiters can hang the one-shot run, and the promised lifecycle tests do not exist.

BLOCKERS
  - [critical] scripts/known_mechanism_ioi_v1.py:689 — `patch_gate` waits without a deadline; `final` repeats this at line 763.
    reasoning — Neither loop consults `gate_timeout_seconds`. A killed worker that produces no terminal causes permanent waiting.
    impact — Violates timeout/failure propagation and makes the one-shot launch unsafe.
    fix — Use a deadline-aware terminal waiter for both loops, emit `FAILED.json` on timeout, and test silent worker death.
  - [high] tests/test_known_mechanism_ioi_v1.py:146 — Remaining tests are static source/config assertions; no failure, timeout, or namespace-isolation test exists.
    reasoning — The suite can pass while the unbounded waiters remain broken.
    impact — Directly leaves the acceptance criterion at `PLAN_KNOWN_MECHANISM_IOI_V1.md:67` unmet.
    fix — Add executable tests for failure terminals, silent-worker timeout, duplicate namespaces, and propagation through both aggregators.

REVISIONS
  - [medium] scripts/known_mechanism_ioi_v1.py:307 — `verify_freeze` hashes every prepared file, including confirmation JSONLs, before workers reach their gates.
    reasoning — This is integrity-only access, not model inference, but conflicts with “workers cannot load them” at `PLAN_KNOWN_MECHANISM_IOI_V1.md:77`.
    impact — The claimed confirmation firewall is weaker than its written contract.
    fix — Split pre-gate verification from confirmation-payload verification, or explicitly define the firewall as prohibiting parsing/model forwarding and test that boundary.
  - [medium] scripts/known_mechanism_ioi_v1.py:695 — Patch aggregation reads metrics without checking the hash in `COMPLETE.json`; final aggregation does likewise at line 770.
    reasoning — Completion manifests contain hashes, but downstream consumers do not validate them.
    impact — Post-completion drift could silently affect gate and final decisions.
    fix — Validate each metrics hash and upstream lineage before summarization.

NITS
  - None.

CHECKS RUN
  - `pytest -q -p no:cacheprovider tests/test_known_mechanism_ioi_v1.py` → 12 passed
  - `scripts/verify_paper_claims.py` → PASS, 63 claims and 272 evidence bindings
  - `preservation-verify` → PASS
  - `preflight` → PASS
  - Python AST parse → PASS
  - `bash -n scripts/launch_known_mechanism_ioi_v1_tmux.sh` → PASS
  - `nvidia-smi` inspection → eight unique 49,140 MiB RTX 6000 Ada GPUs currently available

CONTRACT COVERAGE
  - Exact v6.2 and closure preservation; no v6.3 → met — preservation verification passed and forbidden paths were absent
  - PAPER and claim-ledger scope → met — claim verifier passed
  - Disjoint tokenizer-valid panels → met — prepared hashes and prescore attestations verified
  - Behavior and full-residual positive-control logic → met — signs, strict gates, support, and exact hook replacement are implemented and tested
  - Confirmation firewall → partial — forwarding is gated, but pre-gate integrity reads touch confirmation artifacts
  - Failure/timeout and one-shot lifecycle safety → unmet — two aggregators can wait forever and required tests are absent
  - GPU UUID mapping/concurrency → met — UUID pinning, distinct assignments, and gate-before-load ordering are present
  - No v6.3, method evaluation, or training → met — scope and launcher contain no authorized jobs
  - Candidate and frozen SHIP reviews → unmet — this candidate verdict is BLOCK and no freeze exists

UNKNOWNS
  - Real-model hook behavior and memory use were not exercised because model forwards were prohibited.
  - Frozen inventory, frozen review binding, and tmux handoff cannot be verified before freeze and launch.
