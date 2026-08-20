VERDICT: BLOCK
ONE-LINE: Unanchored completion manifests can let altered artifacts drive gate decisions and final claims.

BLOCKERS
  - [high] scripts/known_mechanism_ioi_v1.py:653-659 — `behavior_gate` waits for `COMPLETE.json` but reads `metrics.jsonl` without validating its recorded hash, model, row count, freeze hash, or inventory hash.
    reasoning — Although behavior completions record these fields at lines 605-606, neither the gate nor `run_patch` anchors them to the active freeze; coordinated completion/artifact drift propagates into later lineage.
    impact — A development gate can be computed from unverified artifacts, violating the exact-manifest and completion-lineage safety required before downstream model forwards.
    fix — Validate every behavior completion’s schema/model/rows, metrics and activation hashes, active freeze hash, and inventory hash before summarization or patch authorization; add a tamper-rejection test.
  - [high] scripts/known_mechanism_ioi_v1.py:778 — Confirmation `COMPLETE.json` omits the patch-gate and freeze lineage recorded only in `STARTED.json`; `final` at lines 800-805 validates metric hashes but not that confirmation ran under the gate it summarizes.
    reasoning — The current patch-gate result and confirmation metrics have no validated cryptographic ancestry.
    impact — Final status can combine confirmation outputs with a different or altered authorization state, defeating end-to-end lineage.
    fix — Put patch-gate hash, freeze hash, and inventory hash in confirmation completion and validate all three in `final`.

REVISIONS
  - [medium] tests/test_known_mechanism_ioi_v1.py:183-206 — Aggregator tests exercise explicit `FAILED.json` propagation only; silent-worker timeout is tested solely on the helper at lines 154-167.
    reasoning — The promised executable timeout propagation through both aggregators is not directly exercised, and the patch test name incorrectly says “silent.”
    impact — `PLAN_KNOWN_MECHANISM_IOI_V1.md:67` remains only partially covered.
    fix — Invoke both `patch_gate` and `final` with silent worker roots and zero deadlines, asserting their `FAILED.json` timeout terminals.

NITS
  - None.

CHECKS RUN
  - `python -m pytest -q -p no:cacheprovider tests/test_known_mechanism_ioi_v1.py` → 16 passed
  - Python AST parse → PASS
  - `bash -n scripts/launch_known_mechanism_ioi_v1_tmux.sh` → PASS
  - `preservation-verify` → PASS
  - `preflight` → PASS
  - `scripts/verify_paper_claims.py` → PASS, 63 claims and 272 evidence bindings
  - Direct preservation/prepared SHA-256 audit → all registered hashes matched
  - `nvidia-smi` audit → eight distinct idle 49,140 MiB RTX 6000 Ada GPUs
  - Plan checker → unavailable

CONTRACT COVERAGE
  - Exact v6.2 and closure preservation; no v6.3 → met — preservation and direct hash audits passed; forbidden paths absent
  - PAPER and claim-ledger scope → met — claim verifier passed
  - Disjoint tokenizer-valid panels → met — prepared attestations and hashes matched; tests passed
  - Behavior and full-residual scientific gates → met — signs, strict thresholds, support, family logic, and exact final-token block-output replacement are implemented and tested
  - Confirmation firewall → met — pre-gate workers use `include_confirmation=False`; parsing and full confirmation verification occur only after patch authorization
  - Deadline waiters → met — both aggregators use deadline-aware `wait_for_terminals`
  - Failure/timeout executable coverage → partial — explicit failures propagate through both aggregators, but silent timeout does not
  - Completion hash lineage → unmet — behavior is unvalidated at its gate and confirmation lacks authorization ancestry
  - Handoff gate-path classification → met — gate suffixes are classified before generic worker paths
  - GPU isolation/concurrency → met — three distinct UUIDs are selected; later same-GPU stages wait before model loading
  - No v6.3, method evaluation, or training → met — scope and launcher authorize none
  - Safe to freeze → unmet — lineage blockers remain

UNKNOWNS
  - Real-model hook behavior and peak GPU memory were not exercised because model forwards were prohibited.
  - Frozen inventory, frozen-review binding, and live tmux handoff cannot be verified before freeze and launch.
