VERDICT: BLOCK
ONE-LINE: Target-label leakage and undefined projection/delta comparisons make the nomination rule non-executable.

BLOCKERS
  - [high] docs/rfc-atlas-v3-discovery-factor-atlas.md:104,137 — identity labels are selected jointly from both EWT and GUM, while the transfer contract says target labels never select the vocabulary.
    reasoning — in either transfer direction, the held-out corpus determines which token/lemma classes survive and their ranking, so the purported fit-source-only pipeline is contradicted by the data contract.
    impact — cross-corpus performance and the nomination gate can be improved by inspecting target-label support; M4's acceptance criterion is impossible to satisfy as written.
    fix — freeze direction-specific fit-source vocabularies, map held-out rows only through that vocabulary, and make insufficient held-out support an ineligible direction without altering the vocabulary.
  - [high] docs/rfc-atlas-v3-discovery-factor-atlas.md:170-188 — the plan never defines how task and delta bases are combined, orthogonalized, or converted into the two representations whose recovery and leakage are gated.
    reasoning — independently fitted rank-16 task bases generally overlap and do not form an additive decomposition; `assigned recovery`, `opposite-side leakage`, and `selectivity` therefore have no unique computable meaning.
    impact — all three architecture nominations can change under an unstated projection ordering or complement choice, violating the mechanical-outcome contract.
    fix — specify one exact projector construction, tie-breaking/truncation/conditioning rule, and assigned/opposite representation for every organization, or remove organization nomination and limit v3 to factor ranking.
  - [high] docs/rfc-atlas-v3-discovery-factor-atlas.md:166 — cross-construct CKA and within-construct similarity are requested for unaligned intervention populations.
    reasoning — linear CKA requires the same aligned observation axis; relative-gap, context, and entity deltas use different examples and counts. Equalizing array length would not create meaningful row correspondence.
    impact — the specificity gate can be numerically defined in multiple invalid ways and may promote an artifact of arbitrary row ordering.
    fix — prohibit cross-construct CKA; compare feature-space delta bases with principal angles/projection overlap, using source-specific bases and an exact within-construct-across-source basis-overlap definition.
  - [high] docs/rfc-atlas-v3-discovery-factor-atlas.md:106,128,131 — pair ownership covers target documents but not donor-linked connected components.
    reasoning — context and entity units use donor documents. If a donor appears in a fit pair and later as a held-out target/donor, lexical or context material crosses folds even though each target document appears in one fold.
    impact — intervention classifiers, delta bases, and bootstrap intervals can be pseudoreplicated or leak donor content across fit and evaluation.
    fix — build a graph over every target/source/donor document, assign whole connected components to folds and bootstrap groups, and cap donor reuse.

REVISIONS
  - [medium] docs/rfc-atlas-v3-discovery-factor-atlas.md:86,224 — optional v2 cache reuse conflicts with using the full EWT/GUM record sets and adds avoidable lineage branches.
    reasoning — v2.4 caches contain only deterministically selected subsets (941 EWT and 382 GUM records), while the allowlisted partition files contain 3,875 and 1,474 UD records.
    impact — support, intervention, and probe populations can silently differ depending on whether reuse succeeds.
    fix — freeze one population and extraction path; the simpler option is fresh v3 caches over the complete allowlisted UD records.
  - [medium] docs/rfc-atlas-v3-discovery-factor-atlas.md:126 — "adjacent" document context is not operationalized against selected records and raw CoNLL-U order.
    reasoning — the normalized records are a subset of the raw corpora; selected records need not be adjacent to another selected record.
    impact — implementations may use nearest selected text rather than the immediately preceding same-document sentence.
    fix — define the target from normalized records and the prefix as the immediately preceding same-document CoNLL-U sentence, with exact document/sentence-ID joins and exclusion at document start.
  - [medium] docs/rfc-atlas-v3-discovery-factor-atlas.md:141 — "appropriate" nuisances and prohibited descendants are analyst-discretion hooks.
    reasoning — nuisance columns can materially change the incremental-F1 gate and no exact task-to-covariate map or unknown-level policy is frozen.
    impact — the nomination can be tuned after seeing results.
    fix — enumerate the nuisance columns, encodings, reference levels, unknown handling, and exclusions per target in the config before extraction.
  - [medium] docs/rfc-atlas-v3-discovery-factor-atlas.md:166 — delta-direction classification can exploit unmatched target positions, token categories, pooling counts, or intervention-specific row construction.
    reasoning — normalization removes magnitude but not these design shortcuts.
    impact — apparent construct specificity may reflect population construction rather than response direction.
    fix — freeze matched target-position/pooling strata, report nuisance-only construct classification, and require representation deltas to improve over that baseline.
  - [medium] docs/rfc-atlas-v3-discovery-factor-atlas.md:188 — the multiple-candidate rule covers only candidates within 0.02 but does not say what happens when multiple pass farther apart.
    reasoning — the terminal outcome still requires exactly one result, yet no deterministic winner rule is provided for that case.
    impact — an analyst must choose the winner after seeing results.
    fix — either always return `multiple_discovery_candidates` when more than one passes, or freeze an exact lexicographic scoring/tie rule with uncertainty handling.

NITS
  - docs/rfc-atlas-v3-discovery-factor-atlas.md:163 — replace `masked/no-visible-prefix` with the exact uniform-shift/bare condition used by the intervention inventory.
  - docs/rfc-atlas-v3-discovery-factor-atlas.md:216 — the inventory contains five model-input interventions plus one relational contrast; say that explicitly instead of "all five" without identifying which five.

CHECKS RUN
  - `/jumbo/lisp/f004ndc/.agent-workspace/bin/check-plan --path docs/rfc-atlas-v3-discovery-factor-atlas.md` → PLAN: PASS.
  - static EWT/GUM prescore inspection → EWT 3,875 UD records/508 groups; GUM 1,474 UD records/194 groups; exact CoNLL-U word joins for every record.
  - tokenizer-only feasibility inspection → single-token-PROPN support in 213 EWT and 129 GUM groups; no neural inference.

CONTRACT COVERAGE
  - Discovery-only/no neural training → met — non-goals and firewall are explicit.
  - Separate position/context/syntax/lexical constructs → met — tasks and interventions are enumerated.
  - Fit-source-only cross-corpus evaluation → unmet — joint target-dependent identity vocabulary contradicts it.
  - Controlled interventions and relational controls → partial — populations exist, but donor-component leakage and delta matching are unresolved.
  - Simple projection/scrubbing baseline → unmet — projector and branch semantics are undefined.
  - Mechanical single outcome → unmet — multiple-pass behavior and underlying metrics are incomplete.
  - Reproducible/data-firewalled execution → partial — exact hashes/config are planned, but optional subset-cache reuse leaves two populations.

UNKNOWNS
  - The independent forked critic did not return before the harness timeout; this is the skill's documented fallback fresh-pass review.
  - No representation scoring, GPU inference, or neural training was run.
