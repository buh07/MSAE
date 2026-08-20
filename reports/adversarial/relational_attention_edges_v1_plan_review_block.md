VERDICT: BLOCK
ONE-LINE: The current matching and comparator do not isolate incremental attention-edge information.

BLOCKERS        (must fix before proceeding; empty if none)
  - [critical] PLAN_RELATIONAL_EDGE_V1.md:132-151 — Gate 3 subtracts residual-pair AUC from attention-only AUC.
    reasoning — A higher score from a separate attention-only estimator does not show that attention adds information conditional on the token-pair residual; feature dimension and domain-transfer behavior differ sharply.
    impact — The primary “beyond a linear token-pair residual baseline” claim is not identified.
    fix — Freeze residual-only and combined residual-plus-attention estimators with identical preprocessing/regularization, and gate on combined-minus-residual held-out AUC; retain attention-only recovery as a separate gate.
  - [critical] PLAN_RELATIONAL_EDGE_V1.md:39-42,110-122 — Matching omits exact query position and exact tokenized sequence length even though normalized causal attention probabilities depend on the complete available prefix and softmax denominator.
    reasoning — Exact query-key gap plus a coarse sentence-length bin does not equate the number or identities of competing keys; positive/non-edge attention differences can therefore reflect boundary/prefix opportunity rather than dependency adjacency.
    impact — A passing attention edge gate would not establish relation-specific organization.
    fix — Match exact query selected-subtoken index and exact selected-subtoken sequence length, store them in every row, and require prescore support after these fields; keep residual-pair conditional gain as the lexical/content control and state that unmeasured competing-key content remains a limitation.
  - [critical] PLAN_RELATIONAL_EDGE_V1.md:84-100 — The baseline is the block-input residual although Attempts 13/14 and the stated project conclusion concern hidden-state index 4, the block output.
    reasoning — Attention at block 3 is computed from hidden state 3, while the prior token-local object is hidden state 4. Comparing against input residuals can manufacture an apparent gain from information already present at the examined output layer.
    impact — The study would not test whether the new edge object improves on the representation that actually failed isolation.
    fix — Make the primary residual-pair baseline the exact hidden-state-index-4 child/head object used by the prior program; report block-input residual only descriptively if desired.
  - [high] PLAN_RELATIONAL_EDGE_V1.md:35-42,164-170 — Source freshness is asserted without an executable project-wide exposure/overlap audit.
    reasoning — Label-only external scouting already occurred, and aliases/hashes/text could have appeared in prior caches or source candidates without the treebank names.
    impact — “Fresh” and endpoint-outcome-unseen claims could be false, undermining the separate-program rationale.
    fix — Before authorization, inventory prior source/model-forward/result artifacts by aliases, file hashes, normalized document/sentence hashes, and token hashes; record scouting as label-only development exposure and downgrade or reject any source with prior endpoint/model-forward use according to a frozen rule.
  - [high] PLAN_RELATIONAL_EDGE_V1.md:84-100,166-170 — The tokenization/alignment contract does not require exact natural surface reconstruction.
    reasoning — Ukrainian and Arabic punctuation/clitics plus UD `SpaceAfter=No` make word-list tokenization with inserted spaces scientifically different from the original sentence; earlier project reviews already found this failure mode.
    impact — Attention edges could be measured on synthetic whitespace-corrupted sequences rather than corpus text.
    fix — Require exact `# text`/`SpaceAfter=No` reconstruction, fast-tokenizer offset alignment to every syntactic word, byte-exact surface QA, and fail closed on ambiguous or incomplete alignment.

REVISIONS       (should fix; not blocking)
  - [medium] PLAN_RELATIONAL_EDGE_V1.md:87-91 — Calling the causal orientation “dependency direction role” for non-edges is undefined.
    reasoning — A non-edge has no child/head role; only the matched positive supplies that label.
    impact — Implementations may accidentally leak the positive role or mismatch controls.
    fix — Define an assigned positive-role stratum copied to the negative solely for matching and prohibit it from estimator features.
  - [medium] PLAN_RELATIONAL_EDGE_V1.md:143-151 — The same fixed ridge alpha is used for 12-, 1,536-, and combined-feature models without a scale/capacity justification.
    reasoning — Standardization does not make regularization effects dimension-neutral.
    impact — Comparator differences may partly reflect arbitrary shrinkage.
    fix — Freeze one label-blind dimensionality/regularization strategy or a nested fit-source-only alpha grid applied identically to baseline and combined models, with no held-out-source tuning.

NITS            (optional, cap at 5)
  - PLAN_RELATIONAL_EDGE_V1.md:70 — State explicitly that block 3 is zero-indexed and produces hidden-state index 4.

CHECKS RUN
  - `/jumbo/lisp/f004ndc/.agent-workspace/bin/check-plan --path PLAN_RELATIONAL_EDGE_V1.md` → PASS.
  - `sha256sum PLAN_RELATIONAL_EDGE_V1.md` → `9d7d21a3cc216b084c4111ab15882ff9fd21f8bfa38c70d8572d543ef2a2f883`.
  - Read Attempt-13/14 reports and configs → prior object is hidden-state index 4; Attempt 14 is terminal and training is unauthorized.

CONTRACT COVERAGE
  - Preserve/close Attempts 13/14 → met — explicit immutable checks and exact conclusion.
  - Paper encoding/separability synthesis → met in plan — milestone and claim limits are explicit.
  - Genuinely different relational object → partial — attention edges differ, but the wrong residual baseline prevents the intended comparison.
  - Fresh corpora/support → partial — genuine document floors are specified; exposure and exact-surface contracts are incomplete.
  - Prospective valid decision → unmet — Gate 3 does not test conditional increment and attention-normalization confounding remains.
  - No neural training → met — forbidden throughout.
  - Adversarial-before-inference/tmux free GPU → met in plan — freeze/review/QA/authorization sequence is explicit.

UNKNOWNS
  - Whether exact-position/length/subtoken matching retains adequate support is unknown until a label-only prescore build.
  - Pythia pretraining exposure to the selected corpora is unknown and must remain a claim limitation.
