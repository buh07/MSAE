VERDICT: BLOCK
ONE-LINE: Exact persistent pairs are viable to qualify, but recovery authorization and atomic-visibility wording remain contradictory.

BLOCKERS
  - [high] docs/plan-msae-norspan-jumbo-qualification-v2.md:51-59 — complete pre-start entry/ready pairs may resume after reconstruction and fsync, but any failed parent fsync must remain unresolved until explicitly reviewed zero-work terminal revalidation.
    reasoning — write/fsync/link a complete pre_network_ready pair, then let its final parent fsync raise OSError. Both names, canonical bytes and nlink2 remain. On restart this is observationally identical to a pair linked before a kill; no bytes or metadata prove the previous fsync outcome. Lines 51-53 permit reconstruction, current fsync and first network access; lines 58-59 prohibit progression pending a different terminal-revalidation authority. The artifact does not define which rule controls this real one-way gate. The coordinator clarified an intended pre-start zero-source-work recovery carve-out, but that carve-out is not unambiguously expressed in the frozen plan.
    impact — consumers cannot implement a single fail-stop recovery contract without choosing their own source-access authority. This prevents approving Q2/Q3 semantics as frozen.
    fix — version a successor with a normative recovery table. Explicitly distinguish complete pre-start pairs eligible for approved zero-source-work re-fsync/revalidation before FIRST access; stage-only/final-only/incomplete pairs that remain unresolved; ANY started-stage/final without complete terminal state that permits ZERO repeat access; and complete terminal states eligible only for approved zero-source-work durability/custody reconstruction. State whether pre-start recovery applies after both kill and known fsync failure, which exact reviewed implementation/controls authorize it, and that it never proves prior successful durability calls. Add synthetic fsync-error-plus-restart and kill-at-identical-boundary tests with exact source-call counts.

  - [medium] docs/plan-msae-norspan-jumbo-qualification-v2.md:29,35,42-45 — path-based os.link(S,F) is described as an atomic complete-byte visibility point, while Q2 explicitly requires substituted-stage rejection at lines 90-92.
    reasoning — after the last prelink named-stage validation, substitute S with a foreign or partial inode before os.link resolves its source pathname. The link can atomically expose THAT inode at F. O_NOFOLLOW at stage creation and follow_symlinks=False at link do not bind the later pathname lookup to the retained original descriptor. Postlink original-FD checks can correctly reject and preserve evidence, but they cannot make the already-visible foreign final never have existed. This is a reasoning counterexample, not a newly executed mutation experiment.
    impact — the claimed visibility guarantee is stronger than the proposed operation provides under its own declared custody attacks. Consumers/restart rules must not derive committed status from that overstatement.
    fix — describe link as atomic NO-REPLACE NAMESPACE INSERTION. A valid publication requires successful retained-original identity/byte and both-name checks after link and durability, plus complete containing-control validation for consumers. Explicitly allow rejected visible finals as retained obstruction evidence, never consumable merely because two names exist. Require Q2/Q4 tests injecting substitution precisely BETWEEN last prelink validation and link, then exercising concurrent/restarted consumers with zero unauthorized access. Do not assume an unqualified descriptor-link primitive exists on Jumbo.

REVISIONS
  - None beyond the blocking semantic clarifications.

NITS
  - None.

CHECKS RUN
  - sha256sum docs/plan-msae-norspan-jumbo-qualification-v2.md and active task PLAN.md; cmp — both match 06bac835578c3f59b8d6fea3d9e4854ad3b3b38a244bf1ef39024b8a30046a2b and are byte-identical.
  - PYTHONDONTWRITEBYTECODE=1 .../bin/check-plan --path /jumbo/lisp/f004ndc/experiments/wip/MSAE/docs/plan-msae-norspan-jumbo-qualification-v2.md — PLAN: PASS.
  - Read-only public builder/acquisition/history/control/private-publisher paths and canonical scientific/containment plan — identified current single-name/nlink1 assertions requiring Q3 integration; no production function was invoked.
  - Read separately retained native pair probe /jumbo/lisp/f004ndc/tmp/lisplab1/norspan-jumbo-pair-probe-1hzgl_h7/probe.json, SHA-256 09a893f1580c38ed310519b41c43f0d3697460b8b95cd78471e42d18a745d490 — same project device, retained stage/final same inode, nlink1 to nlink2, expected bytes, existing-final EEXIST preserved, no retirement unlink. Capability evidence only, not qualified JPC implementation or durability proof.
  - V1 plan remains 3b8ad18dd498035891e7de61cbd22e2b626d704da161546bda96c6a615191cc3; initial separate BLOCK report remains f70419db482f4f600b9abc42c1f301bb1e2fc725d58262460c8dfba77ca0c0c2.
  - V2 hash and prior-plan/report hashes checked immediately before/after report persistence; unchanged. Only reports/adversarial/msae_norspan_jumbo_pair_plan_review.md was newly written, mode0644, no overwrite.

CONTRACT COVERAGE
  - Structural exact-hash plan gate — met; validator PASS and active task byte-identical.
  - Jumbo-only source-free review, protected-byte prohibition and evidence preservation — met within review scope.
  - Prospective exact TWO-name/nlink2 custody instead of generic hardlink relaxation — specified coherently at lines 31-45,64-72; native capability positive. Not yet implemented or qualified.
  - No overwrite, retirement unlink or fallback — specified; permanent-pair approach removes the publisher's dangerous retirement operation.
  - Strict consumption/restart authority — partial; the two blocking findings require an unambiguous normative contract before implementation.
  - Pair inventory/history/authority/raw/private/scorer integration and unchanged science — explicitly sequenced in Q3 and later gates; unimplemented, no approval inferred.
  - Full NFS fault matrix and whole implementation/canonical authority — pending Q2-Q4, not certified by capability probes or finite prior local tests.
  - Source/readiness/prescore/G3/training/final/release — outside this scoped review; no launch or scientific SHIP granted.

UNKNOWNS
  - Actual JPC implementation, all original-FD/name/fingerprint/cardinality intervals, ownership cleanup and pair-aware reader behavior remain to be tested and independently reviewed.
  - Ordinary public code/review/source metadata must remain nlink1 while only explicitly enumerated JPC artifacts accept exact pairs. Generic hardlink acceptance or stage/history exemptions would violate this plan.
  - Superseding a canonical full-review authority member must not retrospectively approve retained BLOCK bytes or exempt their normal accessible-history content. Frozen history/identity gates may honestly reject; no source success is promised.
  - Source-stage substitution analysis does not assume malicious access to protected data and did not execute any filesystem mutation. Arbitrary post-observation mutation and permanent hostile same-UID interference cannot be disproved by finite tests.
  - Prior NFS metadata/scratch anomalies, hard crash/server reboot and multi-client behavior remain unqualified; the plan appropriately forbids inferring them from same-client probes.
