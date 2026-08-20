# PLAN — Counterbalanced key–value retrieval assay v5

## Goal

Run one separately versioned, task-only assay that tests whether the v4.1 Pythia sham failure
survives complete key/answer/template counterbalancing and aggregation over multiple unrelated-key
shams.  Eligibility is model-specific; replication still requires two model families.  The assay
must stop before any representation-method evaluation or training.

## Non-goals

- Do not alter, resume, reinterpret, or write inside the v4.1 result namespace.
- Do not lower v4.1 thresholds, drop Pythia, or use post-result Pythia diagnostics for v4.1 scoring.
- Do not evaluate SAEs, K2, projections, dictionaries, or learned relational models.
- Do not claim cross-model method controllability from a task-validity assay.

## Constraints and grounded design

- Preserve the complete v4.1 result tree, freeze, config, prepared rows, and launch provenance by
  exact hash in a read-only preservation manifest.
- The v4.1 claim is limited to two opened, document-disjoint Wikitext development partitions; its
  single-sham key roles are non-identifiable because query key fixed base and sham keys.
- Use eight keys, eight answers, and three frozen templates. Within each source/split, the 8×8
  query-key/answer grid occurs once per template (192 document components). Each component scores all
  eight binding keys. For query key `q`, every other key is used once as baseline `b`; for each
  baseline, all six remaining unrelated keys `s` are shams. Thus within every answer/template stratum
  each key occurs once as query, seven times as baseline, and 42 times as sham. Tests freeze incidence
  tables. The identifiability matrix has one row per ordered `(q,b,s,answer,template)` contrast and
  reference-coded columns: intercept, seven indicators for each of q/b/s/answer, and two template
  indicators (31 columns). It must have rank 31 with smallest singular value >1e-8; the v4 cyclic
  schedule must have rank <31.
- For component `i`, let `L_i(k)` be target-versus-contrast log odds under binding key `k`,
  `F_i = mean_{b != q}[L_i(q)-L_i(b)]`, and
  `S_i = mean_{b != q} mean_{s not in {q,b}} |L_i(s)-L_i(b)|`. A component is eligible iff
  `F_i > 0.25`; for eligible components `R_i=S_i/max(F_i,1e-8)`. Wrong-direction effects are
  ineligible, preserving the predecessor's signed support semantics.
- For each model/source, require at least 55/64 eligible components within each template, at least 165/192 overall, and
  overall eligibility >=0.85. The gate
  point is mean `R_i`. Its 95% percentile interval uses 500 deterministic draws resampling document
  components independently within each template stratum and averaging strata equally. Pass requires
  point `<=0.20` and upper bound `<0.30`. These retain v4.1's numeric thresholds without claiming the
  new multi-sham estimand is retrospectively equivalent.
- Conditions must have identical tokenizer lengths for all pinned model revisions.  Every component
  uses a distinct natural document and development/confirmation documents are disjoint.
- Wikitext and pinned AG News train (`fancyzhx/ag_news` revision
  `eb185aade064a813bc0b7f42de02595523103ca4`) provide two source domains. AG News had no project
  reference before v5 and supplies one article per component. Preparation is label/tokenizer-only.
- Build an exclusion universe from all v3/v4 prepared predecessor document/donor IDs and normalized
  filler hashes. Reject matching Wikitext IDs and exact normalized-content/window hashes across the
  exclusion universe, both new sources and the new development and confirmation pools. Freeze accepted and rejected ID/hash manifests.
- Model family is the configured checkpoint family (`gpt2`, `pythia`, `gemma`). A model opens no
  confirmation output unless it passes both development sources and at least one other family does.
  The future method-eligibility matrix records Wikitext-fit→AG-News-eval and AG-News-fit→Wikitext-eval. A direction is eligible only when its fit-source development and
  opposite-source confirmation cells pass; a positive family requires both directions. The final
  assay passes only if at least two families satisfy both directions.
- No network access, model training, outcome-conditioned exclusion, or automatic method launch.
- Output, provenance, and gate-root creation is exclusive; any pre-existing namespace aborts before
  inference, so the frozen assay is one-shot.

## Approach

1. Write an analysis-only v4.1 diagnostic that imports exact frozen artifacts, reports heavy-tail
   summaries and outliers, and explicitly reports that role-specific key effects are not identifiable.
2. Prepare counterbalanced development and confirmation panels and freeze their exact bytes with the
   code/config/tests/launcher, v4.1 preservation tree, closure, model-cache attestation, and reviews.
3. Launch one development GPU worker per model. A coordinator publishes the two-family gate.
   Separate confirmation workers do not load a model unless the global barrier and that model's own
   two-source eligibility pass. A final CPU aggregator publishes the directional matrix.

The simpler alternative—rerun v4.1 with several shams—was rejected because it would retain the
deterministic role/key confound and reuse opened rows.  A full method benchmark was rejected because
task validity is the prerequisite still under test.

## Milestones

- [ ] **M1 preservation and claim review:** exact v4.1 manifest and independent claim review saved;
  analysis-only Pythia diagnostic completes without model loading.
- [ ] **M2 prospective v5 candidate:** config, prepared panels, assay runner, launcher, tests, cache
  attestation, and immutable freeze exist in new namespaces.
- [ ] **M3 adversarial correction:** independent review attacks counterbalancing, leakage, gates,
  lineage, GPU mapping, failure handling, and absence of training; every BLOCK/REVISE item is fixed.
- [ ] **M4 launch:** workers run in tmux on free physical GPUs and the coordinator returns after
  liveness/initial-log checks, without waiting for results.

## Definition of done

- [ ] Every v4.1 preserved file still matches its pre-v5 size and SHA-256.
- [ ] The claim review binds exact v4.1 freeze/result/metric hashes and uses only the narrow
  opened-development claim. The diagnosis hashes inputs, loads no model, does not rescore v4.1, and
  cannot alter any v5 row, estimator, threshold, or decision.
- [ ] Every v5 source/split has exactly 192 unique-document components, all 64 query-key/answer pairs
  under each of three templates, and six distinct non-query/non-baseline shams per baseline (42 ordered contrasts per component).
- [ ] Key×role×answer×template incidence is exactly balanced; the frozen main-effects matrix has the
  expected rank and an explicit v4 cyclic negative control is rejected.
- [ ] All condition prompts are length-matched for every model and continuation labels are one token.
- [ ] Development and confirmation have zero ID/content/window-hash overlap with predecessors or each
  other; AG News uses 192 unique articles per split at the pinned revision and fingerprint.
- [ ] Eligibility is per model/source, while confirmation access and a positive final decision both
  require at least two model families passing both sources.
- [ ] No representation method, training code, fresh-row outcome filter, or v4.1 continuation exists.
- [ ] Freeze verification, targeted tests, compile, launcher syntax, cache checks, and adversarial
  review pass before launch.
- [ ] tmux launch records physical GPU UUIDs; handoff accepts a live session or validated clean terminal.
- [ ] Atomic terminals distinguish worker `COMPLETE`/`FAILED`, scientific `PASS`/`FAIL`, upstream
  `BLOCKED`, and timeouts. Nonzero exits propagate and waiters terminate after a frozen timeout.

## Risks and one-way doors

- AG News documents are freshly pinned for this protocol; claims must still say cross-corpus task
  replication, not unseen-distribution replication.
- Template semantics can differ despite perfect length balance; template blocking and stratified
  output retain this heterogeneity.
- Forty-two correlated ordered sham contrasts do not create independent samples; aggregation occurs
  inside the document component before the template-stratified document bootstrap.
- Opening confirmation model outputs is a one-way door, so the two-family development barrier is
  enforced before the model is loaded for confirmation.

## Verification plan

- `python -m py_compile scripts/joint_controllability_assay_v5.py`
- `bash -n scripts/launch_joint_controllability_assay_v5_tmux.sh`
- `pytest -q tests/test_joint_controllability_assay_v5.py`
- deterministic double-prepare hash comparison and `preflight`/`cache-preflight`
- independent `/adversarial` review of the complete frozen candidate; rerun checks after fixes
- launch once; inspect `tmux ls`, GPU processes, launch manifest, and first log lines only
