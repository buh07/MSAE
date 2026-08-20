CLAIM: REVISE
SUMMARY: Task-gate failure is supported; narrow synthetic validity and treat the potency/collateral pattern as exploratory.

BLOCKERS
  - None for the narrow task-ineligibility conclusion.

REVISIONS
  - State that the prespecified synthetic positive-control gate passed, not that the entire evaluator was validated.
  - Report the naturalistic endpoint/task as ineligible, not the methods as failed.
  - Across the 14 unique model-layer/transfer task cells, eligibility was 0.609375--0.7890625 versus 0.80 required; every cell also failed the frozen sham rule.
  - Describe the secondary pattern as an exploratory potency/specificity--collateral-safety association. Across 134 matched 0.25-to-1.0 budget triplets, collateral increased in 134/134, recovery in 90/134, and specificity in 105/134. These correlated, ineligible-panel comparisons are hypothesis-generating only.
  - Retain `within_corpus_transfer=true`; WIKI_A/B do not establish cross-domain replication.
  - Disclose that `proxy_control_benchmark_v2.py` was omitted from the original freeze and hash-bound only for recovery. This does not affect the bootstrap-independent eligibility failure.

EVIDENCE CHECKED
  - Frozen config and freeze SHA-256 `395aa2829a4763c972f1381069e0461e6b458f81995e6aad34c41f248a3b1f24`.
  - Synthetic gate: ground and skyline recovery/specificity 1.0/1.0; random specificity 0.0585.
  - Seven worker completions: 51,456 rows with exact metrics and hook-QA hashes.
  - Original aggregate traceback: failure occurred while serializing NumPy `bool_`.
  - Analysis recovery: 402 summaries, zero joint passes, zero method decisions, zero eligibility or sham passes.
  - Gate audit: recovery passed in 82/402 summaries, specificity in 91/402, collateral safety in 179/402.
  - Prescore: 384 rows and 1,152 disjoint target/donor documents.

UNKNOWNS
  - Exact historical bytes of the originally unfrozen bootstrap dependency cannot be proven.
  - The study does not establish why unrelated prefixes were influential.
  - No eligible naturalistic panel, cross-corpus replication, or method-level joint-control comparison has completed.

origin: independent research-claim reviewer
