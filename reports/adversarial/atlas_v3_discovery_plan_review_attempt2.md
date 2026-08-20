VERDICT: BLOCK
ONE-LINE: Projection coordinates and relational representation rules remain mathematically underdefined, preventing deterministic nomination.

BLOCKERS
  - [critical] docs/rfc-atlas-v3-discovery-factor-atlas.md:140,191-196 — standardized ridge weights and raw activation/delta directions are combined into one projection.
    reasoning — ridge coefficients live in standardized coordinates, while intervention SVD directions and `xP` are specified in raw activation coordinates. These directions are not interchangeable under featurewise scaling.
    impact — the projection, recovery, capture, and nomination results depend on an unstated coordinate conversion.
    fix — freeze one fit-source coordinate system for all blocks and evaluation; either standardize activations/deltas before every basis operation and project standardized held-out states, or transform ridge weights back into raw coordinates explicitly.
  - [high] docs/rfc-atlas-v3-discovery-factor-atlas.md:112-113,164-170,201-205 — difference and concatenation relational representations lack separate pass and projection rules.
    reasoning — the plan does not state whether difference, concatenation, either, or both determines relational advantage. Concatenation is `2d`, whereas the shared projection `P` is `d×d`; “paired representations” does not specify whether to use block-diagonal projection, difference only, or another mapping.
    impact — syntax eligibility, candidate recovery, and outcomes can differ between conforming implementations, defeating the total truth table.
    fix — freeze representation-specific gates and designate the selection representation; define exactly how `P/Q` acts on child/head concatenations or exclude concatenation from nomination.

REVISIONS
  - [medium] docs/rfc-atlas-v3-discovery-factor-atlas.md:130,164-168 — matched-non-head matching remains “where possible.”
    reasoning — no match priority, distance forfeit rule, reuse cap, or unmatched-row disposition is specified.
    impact — relational advantage can change with implementation-specific sham selection.
    fix — freeze lexicographic matching keys, exact/fallback strata, tie-breaker, reuse policy, and prescore ineligibility thresholds.
  - [medium] docs/rfc-atlas-v3-discovery-factor-atlas.md:142,150-158 — pair-distance nuisance encoding is not endpoint-explicit.
    reasoning — “token and lemma vocabulary class” does not state whether both ordered endpoints and their remaining surface covariates are encoded.
    impact — incremental pair signal may reflect uncontrolled endpoint identity.
    fix — enumerate left/right endpoint columns and their ordering, with no interactions unless explicitly frozen.

NITS

CHECKS RUN
  - `/jumbo/lisp/f004ndc/.agent-workspace/bin/check-plan --path docs/rfc-atlas-v3-discovery-factor-atlas.md` → `PLAN: PASS`
  - `sha256sum` on the pinned EWT/GUM CoNLL-U files → both hashes match the revised allowlist
  - read-only consistency review of revised firewall, interventions, nuisance table, projections, and outcome rules → prior firewall, vocabulary, context-control, donor-component, and total-outcome blockers are fixed

CONTRACT COVERAGE
  - source-pure firewall → met — only exact EWT/GUM CoNLL-U paths are allowed
  - fit-only identity vocabulary → met — held-out labels cannot select or rerank classes
  - complete prefix factorial → met — position-only and separator-only controls are explicit
  - donor leakage/pseudoreplication control → met — same-fold donors, reuse caps, and connected-component resampling are specified
  - exact nuisance/chance procedure → partial — single-token tasks are specified; pair endpoints remain ambiguous
  - proper-noun interpretation → met — matching and non-semantic scope are explicit
  - valid cross-source basis comparison → met — feature-space overlap replaces unaligned-row CKA
  - exact projection construction → unmet — coordinate system and concatenated relational projection are unresolved
  - rank sensitivity and total outcome rule → met — sensitivity gates and exhaustive pass-count outcomes are explicit
  - deterministic implementation/testing completeness → partial — relational matching and representation fixtures need expansion

UNKNOWNS
  - Whether 50 eligible connected components remain per intervention after exact-length, same-fold, donor-once matching.
  - Review persistence was skipped under the coordinator’s immediate-return instruction.
