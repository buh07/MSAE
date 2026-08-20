# RFC — Atlas v3.4 attempt 8: RoPE technical measurement and unchanged atlas

## Status

Implementation candidate. The attempt remains **no-model-calls-authorized** until the exact prescore
bundle, synthetic checks, and an independent `/adversarial` implementation review all pass.

## Decision

Attempt 7 is retired without retry. Attempt 8 treats three properties as distinct endpoints:

1. exact replay of one float32 cache and its row lineage;
2. repeated live inference on identical tensors and batches;
3. approximate representation equivariance under translated position IDs.

Only EWT technical-development evidence chooses tolerance caps. Fresh GUM is opened once after a
signed freeze; outcome-new GENTLE is opened only after GUM passes. Diagnostic hooks execute in a separate
process and cannot tune a cap. The scientific atlas remains unchanged and cannot run without both
technical validation sources passing independently.

## Fixed population and gates

Each grid source has five length bins, 20 sequence-distinct bases per bin, at least ten real
documents per bin, at most two bases from a document in a bin, two selected token positions, and
six global shifts. Each of the 30 cells therefore contains 40 rows and 30,720 coordinates. The
reference schedule is `64+36`; the candidate schedule is `9x64+24`; three reference repeats use
the exact same order, shapes, and right-padding.

All metric reductions are float64 over float32 caches. The coordinate rule is
`abs(c-r) <= atol + 5e-6*abs(r)`. EWT selects `atol`, relative-L2, and cosine caps by multiplying
the union maximum by 1.25 and moving upward on the grids frozen in
`configs/atlas_rope_v4/prescore.json`. Validation permits at most 30 coordinate failures and two
coordinate-failing rows in each cell, but no relative-L2, cosine, nonfinite, missing, duplicate, or
lineage failures. The exact fresh-GUM sentinels are stricter: every pair permits zero failures.

## Firewalls

- EWT technical sentences must be disjoint from final-v3 science by document, component,
  sentence, logical unit, token-sequence hash, and normalized-content hash.
- Previously opened legacy GUM documents and sequences cannot enter the new GUM grid. The exact
  unopened fresh-GUM sentinel remains a separate, non-poolable schedule.
- A label-only audit showed ESLSpok is unusable as held-out validation because every eligible
  dev/test record belongs to a previously exposed document. The audit is retained and ESLSpok is
  not opened by attempt 8. Official GUMReddit was also rejected because all token forms are redacted
  placeholders. Intact official GENTLE at commit `fd7a1bfc82896e362c66f59492b5525940f52fa7`
  replaces both failed candidates. It supplies 26 genuine documents and adequate single-sentence
  support in every bin. The builder proves no prior GENTLE IDs or source URLs and excludes exact
  content/token overlaps with all prior prepared inputs. Windows and truncation are forbidden.

The builder loads only the pinned tokenizer from local files. It never loads model weights.

## Diagnostic boundary

Twenty prespecified EWT bases (four per bin) are run in independent hooked and unhooked processes.
Hooks observe only each layer's `query_key_value` output. Reconstruction reports captured
pre-rotary Q/K, reconstructed float32 post-RoPE Q/K, causal valid-entry logits, and a narrow
float64 rotary reference. The four named residuals are `propagated_pre`, `local_rotary`,
`aligned_total_post`, and `invariant_logits`. Hooked and unhooked hidden-state bytes must match.
No diagnostic statistic is an authorization input.

## No-training and failure policy

Technical paths set evaluation and inference mode, disable gradients, and reject optimizer,
scheduler, backward, estimator, checkpoint, and non-allowlisted outputs. A stage failure creates a
signed no-retry terminal; it never relaxes a threshold or opens the next source. No neural training
is authorized by this protocol, including after a positive atlas.

The full executable contract and milestone acceptance criteria are in `PLAN.md`.
