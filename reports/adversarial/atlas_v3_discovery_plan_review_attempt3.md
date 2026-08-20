VERDICT: BLOCK
ONE-LINE: Held-out labels still select evaluation rows, and the fixed token vocabulary inherits forbidden-source design influence.

BLOCKERS
  - [critical] docs/rfc-atlas-v3-discovery-factor-atlas.md:105,148 — row capping partitions held-out candidates by target label despite claiming target labels only compute metrics and support.
    reasoning — label-round-robin capping determines which held-out examples enter evaluation, so target labels affect the evaluated sample.
    impact — violates the stated target-label firewall and can alter transfer scores through label-aware selection.
    fix — cap rows using label-blind row hashes, then recompute support; alternatively disclose label-stratified evaluation sampling and retract the stronger firewall claim.
  - [high] docs/rfc-atlas-v3-discovery-factor-atlas.md:25,109 — primary token identity reuses the v2.4 vocabulary despite forbidding design choices derived from C1/C2 and ESLSpok.
    reasoning — `scripts/msae_measurement_v2_run.py:361-375,618-620` derives the v2.4 common vocabulary across all v2 roles, including forbidden C1/C2 sources.
    impact — the primary v3 task inventory remains indirectly selected by payloads the non-goal says must not influence design.
    fix — use a source-independent prespecified vocabulary, make token identity direction-specific and fit-only, or explicitly narrow the non-goal and disclose the inherited C1/C2 influence.

REVISIONS
  - [medium] docs/rfc-atlas-v3-discovery-factor-atlas.md:115,139 — proper-noun quartiles are called source-local in one place and fit-source-derived in another.
    reasoning — a source is fit in one transfer direction and held out in the reverse, so “fit-source quartile” does not uniquely define one frozen intervention population.
    impact — donor matching can differ by interpretation.
    fix — state explicitly that each corpus uses its own frozen source-local quartiles in both directions.

NITS

CHECKS RUN
  - `/jumbo/lisp/f004ndc/.agent-workspace/bin/check-plan --path docs/rfc-atlas-v3-discovery-factor-atlas.md` → `PLAN: PASS`

CONTRACT COVERAGE
  - prior projection-coordinate blocker → met — ridge weights convert to raw coordinates
  - prior relational-representation blocker → met — primary representation and block projection are exact
  - sham matching and pair nuisances → met — deterministic exact-stratum rules are frozen
  - deterministic folds/caps/bootstrap → partial — algorithms are exact, but capping uses held-out labels
  - data/design firewall → unmet — primary vocabulary inherits forbidden-role selection
  - total mechanical outcome → met — all terminal cases are covered
  - implementation and synthetic verification → met at plan level — milestones cover required checks

UNKNOWNS
  - Whether all intervention populations retain 50 connected components after exact matching and donor caps.
  - Review persistence was skipped under the coordinator’s immediate-return instruction.
