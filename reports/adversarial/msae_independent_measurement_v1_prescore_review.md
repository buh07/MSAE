# External prescore adversarial review — MSAE independent measurement v1

**Verdict: BLOCK**

**One-line:** Stage A fails closed on 206 accessible-history collisions; this source cannot launch, and the future-launch harness remains incomplete.

## Blocking findings

1. **Source independence (critical).** `history_overlap.json` reports 206 blocking exact/near collisions across 143 selected documents, including exact-Jaccard 1.0 sentences already in historical Atlas records. `stage_a.json` now correctly binds this evidence, reports two `accessible_history_overlap_detected` blockers, and has `stage_ready=false`. Stop this protocol; do not substitute later AMALGUM ranks under the exposed freeze.
2. **Authorization/lease (critical, downstream).** The unfinished harness lacks the RFC's signed Ed25519 envelope, operator-text digest, scope, expiry, consumed nonce, broker-record validation, and complete failure cleanup.
3. **Label/support audit (critical, downstream).** The current adapter has placeholder prefix support and shallow entity parsing, and does not implement the exact four-role support/vocabulary intersection, cap, and finite-map audit.
4. **Immutable config (critical, downstream).** The config does not yet bind the full source/model/tokenizer/environment/checkpoint/scientific execution closure or exact role-applicable G1/G2 registries.
5. **Stage-B QA (critical, downstream).** Cache, pooling, and pair-alignment observations are not yet the required create-once, digest-bound typed checks.
6. **Environment/protected state/tests (high, downstream).** Full runtime closure, protected-state enforcement, and behavioral failure-path tests remain incomplete.

## Checks

- 55 targeted tests passed.
- Python compilation passed.
- `bash -n` passed for the launcher.
- `git diff --check` passed.
- The full upstream/Reddit clone was removed; exactly 350 selected non-Reddit CoNLL-U documents are retained.
- No model, GPU job, or tmux session was launched.

## Decision

The source-independence failure is sufficient to stop. The harness deficiencies need not be repaired for this stopped source, but all must be fixed and re-reviewed before any replacement source is authorized.
