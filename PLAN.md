# PLAN — Atlas v3.4 attempt 8: separate numerical QA from the position/context atlas

> Revised 2026-08-03 through nine independent plan reviews. Review v9 returned `SHIP`; implementation may proceed, but no neural inference may begin until the separate implementation review also returns `SHIP`.

## Goal

Freeze the current evidence from terminal Atlas v3.3 attempt 7 without retry; run a new calibration/validation-firewalled technical study that distinguishes exact cached replay, repeated live inference, and approximate RoPE translation equivariance; diagnose the layerwise float32 error path in a separate non-score-bearing process; freeze uniquely executable tolerances and engineering failure budgets before opening genuinely outcome-naive fresh GUM and outcome-new GENTLE validation panels; and, only after both validation sources pass separately, run the unchanged no-training scientific position/context atlas in a new attempt-8 namespace.

## Non-goals

- Do not modify, retry, promote, or continue attempt 7. Do not run its GUM command or create its full-extraction authorization.
- Do not use any GUM/GENTLE validation activation, the previously opened attempt-5 legacy GUM metrics, or hooked diagnostic metrics to select attempt-8 thresholds.
- Do not change the scientific tasks, nuisance controls, 500-draw bootstraps, thresholds, projection organizations, or decision rule frozen for attempt 7.
- Do not train an SAE, MSAE, or any neural model. Technical stages load no labels or estimators. Scientific ridge probes remain closed-form, fit-source-only, and frozen.
- Do not call technical evidence evidence for or against a decomposition, or treat an exploratory atlas nomination as confirmation.

## Constraints and grounded evidence

- Attempt 7 has a signed `TERMINAL_TECHNICALLY_INELIGIBLE` with `no_retry_authorized=true`. EWT float32 QA was opened; attempt-7 GUM, full extraction, and scientific analysis were not.
- Attempt-5 **legacy GUM** float16 QA was previously opened. Attempt 8 therefore classifies those 32 legacy units as familiar non-authorizing replication and never pools them with fresh GUM.
- The 16 attempt-7 **fresh GUM dev/test** pairs and all new GUM dev/test grid outcomes remain unopened. Fresh GUM alone is the primary GUM authorization gate.
- The EWT attempt-7 failure arrays are finite float32 `(72,768)` with bit-identical live references and median translated-path relative L2 about `9e-7`. They are calibration history, not validation.
- All new EWT calibration and diagnostics are restricted to pinned EWT dev/test and already-reserved attempt-5 technical challenge documents. Before inference, document, component, sentence, unit, token-sequence, and normalized-content hashes must be disjoint from every retained final-v3 science input, relation, and intervention unit. Insufficient cells make prescore ineligible; science units cannot fill them.
- The no-inference implementation prescore found that ESLSpok cannot be a held-out supplement: prior measurement roles already contain 872 ESLSpok documents and every otherwise eligible dev/test record was excluded by prior document identity (442/442). This audit is retained; ESLSpok is retired before any attempt-8 model call and cannot be used to authorize science.
- Official UD English GUMReddit at commit `b23cca5d4f8732b35cbbec070bb2b1d7abe750e1` was then audited and rejected without model calls: all 16,364 integer-token forms are redacted `_` placeholders and only 18 genuine documents exist. It remains a non-authorizing failed-source audit and is never tokenized for attempt-8 inference.
- The replacement supplement is intact official UD English GENTLE at commit `fd7a1bfc82896e362c66f59492b5525940f52fa7`, file SHA-256 `42d12cdef99bcd3160a3241ba1811fe9e7fd4b37a77f9b9e8c2852f04d69f3fa`. It has 0/17,799 placeholder token forms, 26 genuine documents, and label-only tokenizer support of 23/24/26/25/14 documents with 352/352/350/133/28 sentence candidates in the five bins before cross-source exposure exclusions. Only intact complete single sentences are eligible; no concatenated window, truncation, synthetic boundary, or fallback is allowed. Before selection, the builder inventories all prior prepared inference units and opened-input ledgers, excludes exact token-sequence and normalized-content matches, and rejects any GENTLE document ID, sentence ID, or source URL found in a prior input. It publishes pre/post exclusion support per bin and fails closed if any bin loses the fixed 20 bases, ten per-bin documents, or the source loses its 20-document overall floor. The source is described only as outcome-new technical validation, not model-held-out or broadly unseen.
- Pythia-160M-deduped revision, layer 3/hidden-state index 4, float32, tokenizer, batch size, deterministic algorithms, CUBLAS setting, GPU UUID, TF32/autocast off, and no-training rules are fixed.
- One physical GPU executes every model stage serially under one attempt-wide lock. Create-once bundles use exact allowlists, hashes, signed authorization/terminal envelopes, fsync, and atomic promotion.
- The repository is highly dirty; do not reset, clean, or change unrelated work.

## Design-bank clarification and assumptions

- Deterministic query found attempt-7 `run_qa` only in its extractor CLI; attempt 8 leaves that code/config byte-unchanged.
- The design ledger returned no entry for post-failure calibration/validation separation.
- A1: calibration uses only technical EWT units described above; any new EWT inference is attempt-8 method development, not attempt-7 continuation.
- A2: authorizing validation consists of mandatory exact fresh-GUM sentinels plus the fresh-GUM grid, followed by the exposure-audited GENTLE grid, all gated separately and sequentially. Legacy GUM, infeasible ESLSpok, and redacted GUMReddit are non-authorizing and are not run before science authorization.
- A3: the attempt-7 final-v3 science population may be reused only because no attempt-7 science activation was opened; attempt 8 binds that history and remains exploratory reused-public evidence.
- A4: diagnostic hooks are descriptive only. Every threshold is derived solely from the verified union of retained attempt-7 EWT arrays and a minimal EWT executable identical to validation except for source/panel.

## Frozen technical population and cells

For each technical source (`EWT_calibration`, `GUM_fresh_validation`, `GENTLE_validation`):

- Tokenize with the frozen tokenizer, `add_special_tokens=false`, and retain sequences in five token-length bins: `4–8`, `9–16`, `17–32`, `33–64`, `65–128`.
- Select exactly **20 distinct base sequences per bin** by UTF-8 SHA-256 order after all role/exposure exclusions: 100 base sequences/source. Each bin must contain at least 10 genuine documents and no document may contribute more than two bases; otherwise that source is prescore-ineligible and is described only as an unsupported fixed-sequence challenge.
- For each base, use the two deterministic selected tokens `floor((L-1)/3)` and `L-1`.
- Run the reference at ordinary position IDs and six translated candidates with shifts `{1,4,8,16,32,64}`.
- Thus every required `source × length_bin × shift` cell has 20 bases, 40 representation rows, and `40×768=30,720` coordinate elements. Each source has 100 reference units/200 selected reference rows plus 600 candidate units/1,200 selected candidate rows: 700 condition units and 1,400 representation rows per reference/candidate pass. Live replay evaluates the 100 reference units three times but does not create new logical rows. Each source has 30 required candidate cells.
- Missing a base, row, shift, bin, hash, or exact count makes that source ineligible. No redraw after inference and no pooling across cells or sources.

The **calibration population is the union** of (a) every signed retained attempt-7 EWT row and (b) every new minimal-path EWT grid row. All three caps are maxima over that union after the old arrays' signature, rows, dtype, shapes, formula semantics, and lineage independently recompute. The exact 16 fresh attempt-7 GUM pairs are a second, non-poolable mandatory validation bundle in addition to all 30 new GUM grid cells: all eight `uniform_shift` pairs at shift 16 and all eight `prefix_position_only` pairs at actual offsets `{7,9,12,16,17,28,37,41}` must each pass the frozen coordinate/L2/cosine rules with zero failing coordinates or rows; family summaries are reported separately. Opened legacy GUM is reported only from its existing attempt-5 artifact and never enters an authorization denominator. Science authorization binds PASS digests for the fresh-GUM sentinel bundle, all 30 fresh-GUM grid cells, and all 30 GENTLE cells.

## Uniquely executable metrics and freeze rule

All differences and reductions cast inputs to float64; caches remain float32.

- `difference = abs(candidate-reference)`.
- Coordinate bound: `difference <= atol + rtol*abs(reference)`, with frozen `rtol=5e-6`.
- Calibration `required_atol = max(max(0, difference-rtol*abs(reference)))` over the union of independently verified retained attempt-7 EWT arrays and the **minimal EWT score-bearing path only**. Multiply by `1.25`, then choose the smallest grid value in `{5e-7,1e-6,2e-6,4e-6,8e-6}` greater than or equal to it. No value means technical ineligibility.
- Row relative L2: `||candidate-reference||₂ / max(||reference||₂, 1e-12)`. Select the cap by `1.25×` EWT maximum and next grid value in `{2e-6,5e-6,1e-5}`.
- Cosine distance: if both row norms are zero, distance is `0`; if exactly one is zero, the row fails; otherwise `1-clip(dot/max(norm_ref*norm_candidate,1e-24),-1,1)`. Select by `1.25×` EWT maximum and next grid value in `{1e-11,5e-11,1e-10}`.
- Exact cached replay requires identical row IDs and canonical child hashes; float32 dtype, exact shape, C-contiguous strides/order; `np.array_equal`; and equality of `array.tobytes(order='C')`. Value equality alone is not called byte equality.
- Three live reference repetitions must be finite float32 and byte-identical on the pinned runtime; otherwise that source fails before equivariance scoring.

Validation gates apply **to every required shift×length cell separately** and then to the source:

- coordinate failing elements `<= floor(0.001×30,720)=30`;
- coordinate failing rows `<= floor(0.05×40)=2`;
- zero rows above the frozen relative-L2 cap;
- zero rows above the frozen cosine cap;
- zero nonfinite, missing, duplicate, or lineage-invalid rows.

The `0.1%` element and `5%` row limits are fixed engineering budgets, not inferential error rates. A source passes only if all 30 cells pass. Fresh GUM runs first; on failure GENTLE activations remain unopened. GENTLE runs only after a signed fresh-GUM PASS and must independently pass all 30 cells. Thresholds never change after either validation source is opened.

## Separate score-bearing and diagnostic paths

### Minimal score-bearing executable

One source-parameterized function handles EWT calibration, fresh GUM validation, and GENTLE validation. Score-bearing batch size is exactly `64`. Reference and candidate conditions are always separate forward passes: references are in canonical UTF-8 `unit_id` order; candidates are ordered by the same base order and then frozen shift order `{1,4,8,16,32,64}`. Each pass is sliced into exact contiguous batches `[0:64], [64:128], ...`; references therefore use `64+36` and candidates use nine full batches plus a final `24`. Every slice is right-padded to that slice's maximum sequence length with input ID `0`, attention-mask `0`, and padded position ID `0`; no length bucketing/reordering occurs. Three reference repetitions reuse the identical batch lists and shapes. Every bundle binds per-batch ordered unit IDs, `[batch,max_length]` tensor shapes, maxima, and final-partial membership. The science adapter attests the inherited same rules—manifest order, contiguous size-64 slices, identical right-padding, and explicit final partial batch—for every science source. The implementation, model path, attention backend, inference function, selected tokens, array format, and metric code are otherwise identical; only a signed panel/source specification changes. No hooks, attentions, labels, or estimators are allowed.

The mandatory exact fresh-GUM sentinel is a separate non-grid schedule. It uses the literal `fresh_pair_ids` order in `configs/atlas_discovery_v3_3/population_split_v3.json`: 16 ordered reference units and their 16 ordered candidates, each side executed as one separate partial batch of size 16, right-padded independently by the same `0/0/0` rules. The eight relative pairs contribute two selected rows and the eight context pairs one, for exactly 24 reference rows and 24 candidate rows. References execute three times with the identical unit order, batch membership, padding, and shape. Its bundle binds pair IDs, underlying unit IDs, role-expanded row IDs, both batch shapes/maxima, and all three repeat schedules. No sentinel unit/row/count or metric is pooled with the five-bin grid.

### Diagnostic-only EWT executable

A separate process and bundle runs only on 20 prespecified EWT technical bases (four per length bin) and all six shifts. It freezes attention backend `sdpa`, installed `modeling_gpt_neox.py` SHA-256 `8747c839bf7a3bceb05d7f80aad62a67cb83f95cb4ad0535f76eab6c83a84a54`, and source hashes `GPTNeoXAttention=46a09756ea4c6804a205ec754f4fbf7f6df47b819d199006c6024990d0b01b0e`, `GPTNeoXRotaryEmbedding=b8650f86b61c6f7ca0b8b692e7d40e08a9be37bbf70724812036ea13ba40080e`, `apply_rotary_pos_emb=473b44bd10c3afd9bb8eb2bd7d383b4848606f44dd9c958225d65e8df63d5503`, and `rotate_half=f714a4b1160c694e270d9191a9f133e53856e2a1c62f5cd2f85740f7c2692397`, Transformers `_autoset_attn_implementation=574b00831199f419a24669d08d9bbd16d239024f2c979d03085df3a2ccbe56fb`, and `sdpa_attention_forward=601d992611ca2f1854db8559f146f7b4165af30456e2a686c9f1e741eb77e04b`. The retained attempt-7 loader statically resolves to SDPA under the frozen environment, and the minimal, diagnostic, validation, and scientific paths all require a runtime assertion `model.config._attn_implementation == "sdpa"`. The diagnostic path installs forward hooks only on each layer's `query_key_value` linear output. It reconstructs, out of band:

- pre-rotary Q/K after the exact model reshape/chunk;
- reconstructed float32 post-rotary Q/K using the model-provided float32 cosine/sine tensors;
- unmasked scaled logits `QKᵀ/sqrt(head_size)`, summarized only over valid causal `(query,key)` entries with `key<=query`;
- a narrow float64 rotary reference using the same captured pre-rotary Q/K, model `inv_freq`, rotary dimension, phase convention, `rotate_half`, positions, and scaling, all cast to float64 before phase/trigonometric arithmetic.

Axes are `[batch, head, token, head_dim]`; batch size is 1; maximum length is 128; summaries are per layer/head/shift/length and arrays have an exact size cap fixed prescore. No attention backend switch or `output_attentions` is permitted. Every bundle binds `transformers==4.53.2`, installed/locked package `torch==2.7.0`, CUDA `12.8`, cuDNN `90800`, SDPA flags `flash_sdp_enabled=true`, `mem_efficient_sdp_enabled=true`, `math_sdp_enabled=true`, and `cudnn_sdp_enabled=true`, deterministic-algorithm and TF32/autocast states, GPU UUID, `requirements-atlas.lock.txt`, and a prescore-frozen required `(canonical_path, SONAME, SHA-256)` allowlist built from `torch._C` and the Torch/CUDA/cuDNN libraries loaded by a no-weight/no-forward CUDA runtime probe. Every model stage must contain every required entry with the frozen hash and must reject a conflicting duplicate SONAME or an explicitly forbidden alternate Torch/CUDA library. Process-specific extra libraries are recorded and hashed but are not cross-process drift unless on the forbidden list; missing required entries or conflicting duplicates are ineligible. The rotary dimension is exactly `int((768/12)*0.25)=16`; non-rotary dimensions pass through unchanged. Reconstructed float32 rotation follows the pinned HF order `(q_rot*cos)+(rotate_half(q_rot)*sin)` on GPU float32. Float64 reference and inverse transport cast captured/reconstructed tensors, `inv_freq`, and positions to float64 before phase, trig, multiply, and add; inverse transport applies `R(-delta)` only to the first 16 dimensions and concatenates unchanged pass-through dimensions. All residual norms/dots/maxima accumulate in float64 with the same L2/cosine floors as the technical metrics. For a global shift `delta`, diagnostic comparisons never use raw unaligned post-RoPE Q/K. They report four named residuals: (1) `propagated_pre`, actual shifted pre-Q/K minus reference pre-Q/K; (2) `local_rotary`, reconstructed float32 versus float64 rotations of the **same captured reference pre-Q/K** at each position/shift; (3) `aligned_total_post`, actual shifted reconstructed post-Q/K transported by the inverse common rotation `R(-delta)` into the reference RoPE frame minus reference post-Q/K; and (4) `invariant_logits`, causal valid-entry shifted logits minus reference logits. Out-of-band post-RoPE tensors are labeled `reconstructed`, and fixtures bind their operation ordering to the pinned Transformers source. The diagnostic population is exactly 20 reference units plus their 120 shifted units (140 condition units; 40 reference and 240 candidate selected rows). All 140 condition units are run both hooked and unhooked in separate processes; hooked versus unhooked hidden states must be byte-identical or the diagnostic study signs `TERMINAL_TECHNICAL_DIAGNOSTIC_INVALID` and stops before validation; a valid diagnosis is mandatory for this user-requested study. Diagnostic reporting uses fixed floors `relative_L2>1e-8` or cosine distance `>1e-12` and reports the earliest layer separately for `propagated_pre`, `local_rotary`, `aligned_total_post`, `invariant_logits`, and hidden state. These are localization summaries, not causal claims. No diagnostic value can enter threshold derivation or authorization.

## Approach

1. Freeze current attempt-7 evidence from a new attempt-8 provenance root; do not write inside attempt 7.
2. Build and independently rebuild the EWT/GUM/GENTLE technical panels and all role/exposure firewalls without inference; retain the label-only ESLSpok and GUMReddit rejection audits.
3. Implement and adversarially review the minimal score-bearing path and separate diagnostic path.
4. Run EWT minimal calibration and EWT diagnosis; derive thresholds mechanically from the verified retained-EWT plus minimal-EWT union only, excluding every hooked diagnostic metric.
5. Sign/freeze thresholds and obtain a fresh adversarial `SHIP` before validation.
6. Run fresh GUM once; if it passes, run GENTLE once. Any failure signs a technical terminal.
7. Only dual validation PASS authorizes the unchanged scientific atlas through a narrow reviewed namespace/authorization adapter.

**Rejected alternative:** changing attempt-7 `atol` and continuing is an impermissible retry. **Rejected simpler option:** cosine-only QA can hide localized corruption; the combined gates retain coordinate completeness.

## Milestones

### M1 — Attempt-7 evidence retirement

- [x] In new root `pilot_runs/20260803_atlas_rope_technical_v4/provenance/`, create signed `ATTEMPT7_RETIRED.json` binding a recursive attempt-7 tree inventory, terminal, QA children, scoring config, claim review, and post-result adversarial review.
- [x] Record that this freezes current retained evidence/operator intent, not proof against an unlogged historical invocation.
- [x] Assert the attempt-8 runner rejects all attempt-7 output paths and that GUM/full/science/training artifacts are absent.

Acceptance: signature/inventory verify; attempt-7 tree and executable inputs remain byte-unchanged.

### M2 — No-inference technical prescore

- [x] Add the attempt-8 RFC/config, build exact cell panels, prior-exposure inventory, and source/science firewalls; freeze effective backend `sdpa`, all four required SDPA Boolean values, exact batch-64/order/padding/final-partial schedules, and the required/forbidden Transformer/Torch/CUDA/cuDNN shared-library attestations above before any weight load.
- [x] Rebuild independently and compare every child byte/hash.
- [x] Freeze the exact metric formulas, counts, hooks, capture axes, array cap, backend, grids, signer, environment, and stage transitions.

Acceptance: all three sources have exactly 20 bases per length bin; no EWT technical/science overlap; no selected GENTLE identity/URL/sequence/content overlap with prior opened inputs; the ESLSpok and GUMReddit rejection audits are explicit; validation/run roots are absent.

### M3 — Harness and synthetic verification

- [x] Implement minimal cached/live/equivariance executable and separate diagnostic executable.
- [x] Enforce inference mode, `requires_grad=false`, no label loading, and AST/runtime/output allowlists forbidding `torch.optim`, schedulers, backward/grad updates, checkpoint modules/files, and estimator construction in technical stages.
- [x] Add fixtures for metric floors/zeros, exact integer budgets, cell concentration, missing cells, nonfinite values, grid boundaries, role leakage, prior exposure, Q/K shapes, causal-logit indices, float64 rotary invariance, observer comparison, signatures, stale staging, and terminalization.

Acceptance: synthetic/CPU tests pass; draft config forbids model calls; implementation inventory is exact.

### M4 — Review and EWT calibration/diagnosis

- [ ] Obtain independent implementation `/adversarial SHIP`, then sign EWT-only authorization.
- [ ] Run minimal EWT calibration once; separately run diagnostic and unhooked observer comparison.
- [ ] Report retained attempt-7 history and new EWT results without reading validation activations.

Acceptance: minimal and diagnostic bundles are independently inventoried; only the retained-EWT plus minimal-EWT union feeds freeze; validation roots remain absent.

### M5 — Immutable validation freeze

- [ ] Apply only frozen grid/safety rules; out-of-grid or invalid calibration signs a terminal.
- [ ] Otherwise sign validation authorization binding thresholds, every exact cell, both panel hashes, calibration hashes, code/tests, engineering budgets, and fail-closed order.
- [ ] Obtain a fresh adversarial freeze `SHIP`.

Acceptance: authorization predates all fresh-GUM/GENTLE model calls and independently recomputes.

### M6 — Sequential held-out validation

- [ ] Run the exact fresh-GUM sentinel bundle plus fresh-GUM grid only. Every sentinel pair must also pass canonical cached-byte replay, three byte-identical live references, finite float32/dtype/shape/order, unique row/pair IDs, exact completeness, signed lineage, and individual row/pair digest checks, in addition to zero coordinate/L2/cosine failures; require every sentinel and every grid cell to pass separately, then sign PASS or terminal.
- [ ] Only on fresh-GUM PASS, run exposure-audited GENTLE and sign PASS or terminal.
- [ ] On sentinel-GUM PASS, grid-GUM PASS, and GENTLE PASS, sign science authorization binding all three digests/statuses; do not run legacy GUM, ESLSpok, or GUMReddit as an authorizing source.

Acceptance: two separate signed PASS bundles or a signed terminal; no pooling, retry, redraw, or threshold change.

### M7 — Mechanically unchanged scientific atlas

- [ ] Bind exact final-v3 prescore/rebuild hashes and import the byte-frozen scientific functions from `scripts/atlas_discovery_v3_3_analysis.py` and `scripts/analyze_atlas_discovery_v3_3.py` without editing them.
- [ ] Permit a new adapter to change only config schema, run/result namespace, technical-QA verification, authorization verification, and a post-load assertion that the frozen loader resolved to `sdpa`; it may not override the backend. Freeze a semantic-diff allowlist; task/relation/intervention/projection/statistical functions and thresholds must resolve to the original source hashes/objects, with all 44 attempt-7 regression tests plus adapter tests passing.
- [ ] Reuse the byte-frozen `_forward_units` inference function for science extraction; new code may only adapt authorization/cache namespace and must attest identical model inputs/outputs on synthetic fixtures.
- [ ] Extract EWT then GUM science caches sequentially and run the same atlas. Technical validation loads no labels; science keeps fit-source-only ridge behavior.

Acceptance: dual technical authorization, both new science caches, exact analysis bundle, frozen outcome, no checkpoint/training artifacts, and no attempt-7 cache reuse.

### M8 — Claim/adversarial review and handoff

- [ ] Run research claim review and final adversarial audit on technical and scientific outcomes.
- [ ] Report exact artifacts and limitations; authorize no neural training.

Acceptance: claims match executed evidence and all histories/missingness remain explicit.

## Definition of done

- [ ] Attempt 7 is frozen without retry from outside its run tree.
- [ ] Cached replay, live repeatability, and approximate equivariance have separate artifacts and gates.
- [ ] Minimal calibration/validation and hooked diagnosis are separate processes; diagnostic data cannot tune thresholds.
- [ ] Retained EWT failure arrays and the new minimal EWT grid jointly determine caps under one SDPA runtime contract; all new EWT units are science-disjoint; exact fresh-GUM sentinels, the fresh-GUM grid, and exposure-audited GENTLE activations stay unopened until signed freeze.
- [ ] Every source×shift×length cell has exact counts and uniquely executable coordinate/L2/cosine gates.
- [ ] Every exact fresh-GUM sentinel pair, every fresh-GUM grid cell, and every GENTLE grid cell passes separately or a technical terminal stops science.
- [ ] Only dual PASS can launch the byte-frozen scientific computation through the narrow adapter.
- [ ] No neural training, optimizer, scheduler, checkpoint, or technical label/estimator use occurs.
- [ ] Independent implementation, freeze, result, claim, and adversarial reviews are retained.

## Verification plan

- `check-plan`, then `/adversarial PLAN.md` until `SHIP`.
- Rebuild panels twice; byte/hash compare; exact cell-count, science-disjointness, and prior-exposure audits.
- New synthetic tests plus all attempt-7 tests; `py_compile`; static forbidden-import/call scan.
- Stage guards, signed role authorizations, one GPU lock, absent downstream roots before each one-way opening.
- Independent recomputation of every signed calibration/validation cell and threshold grid choice.
- Semantic-diff allowlist and object/source hashes for frozen scientific functions; full final-v3 lineage/rebuild verification.
- Post-result research claim review and adversarial audit.

## Risks and one-way doors

- **Validation opening:** irreversible; require signed freeze and `SHIP` first.
- **Attempt-7 mutation/retry:** irreversible contamination; write retirement outside its tree and reject its paths.
- **Tolerance overfit:** mitigate with fixed cells/formulas/grids/safety factor, two separately gated validation sources, and no edits after opening.
- **Hook observer effects:** hooks never share the score-bearing process; byte-identical observer comparison is mandatory, and disagreement terminalizes before validation.
- **Science contamination:** technical EWT/science hashes must be disjoint; no exception for sparse cells.
- **Float64 overclaim:** reference covers rotary arithmetic on captured Q/K only, not a float64 model or causal proof.
- **Supplement freshness:** retain the ESLSpok and GUMReddit rejection audits rather than weakening their gates. For GENTLE, bind the official commit/file hash and intact-token audit; inventory prior IDs/URLs and all prior prepared sequences; exclude exact cross-corpus sequence/content matches; require at least 20 total and ten per-bin real documents; and describe it only as outcome-new supplementary technical validation.
- **Dirty worktree:** touch only attempt-8 paths and explicit planning/archive/review artifacts; never reset or clean.

## Deviations log

- 2026-08-03: Initial plan; design ledger silent.
- 2026-08-03: First adversarial review `BLOCK`. Revised to isolate fresh GUM, separate hooked/minimal paths, firewall EWT from science, freeze exact per-cell metrics/counts, move retirement outside attempt 7, bound the science adapter, inventory ESLSpok exposure, and enforce no-training structurally.
- 2026-08-03: Second adversarial review `BLOCK`. Revised to make retained EWT evidence calibration-binding, require exact fresh-GUM sentinels, align RoPE frames, separate local/propagated residuals, add document diversity and strong ESL exposure filters, and define byte semantics literally.
- 2026-08-03: Third adversarial review `BLOCK`. Replaced invalid eager mixing with one explicit SDPA runtime across retained calibration, new calibration/validation, diagnosis, and science; pinned backend/library attestations; made sentinel common gates and diagnostic validity mandatory; and froze reconstruction/transport arithmetic.
- 2026-08-03: Fourth adversarial review `BLOCK`. Corrected the Torch package identity, added the enabled cuDNN SDPA flag, and made observer replay cover all 140 diagnostic condition units; recorded full five-bin logical counts.
- 2026-08-03: Fifth adversarial review `REVISE`. Froze literal batch-64 ordering/slicing/padding/final batches, all four true SDPA flags, and required-versus-extra shared-library semantics; corrected remaining terminology.
- 2026-08-03: Sixth adversarial review `BLOCK`. Added the separate exact fresh-GUM sentinel schedule: frozen pair order, 16+16 partial batches, 24+24 expanded rows, three repeats, exact padding/shapes/IDs, and no grid pooling.
- 2026-08-03: No-inference implementation prescore found ESLSpok structurally ineligible as a supplement: all 442 otherwise eligible dev/test records belonged to 872 documents already exposed in prior measurement roles. Retired ESLSpok without a model call and replaced it with official outcome-new GUMReddit, using deterministic within-document windows only to supply the sparse 65–128 bin. This source change requires a new plan `/adversarial SHIP` before implementation resumes.
- 2026-08-03: Eighth plan review `BLOCK`: official GUMReddit was wholly redacted (16,364/16,364 token forms `_`), offered only 18 documents, and the proposed window construction was not uniquely executable. Rejected it without inference. Replaced it with intact single-sentence-only GENTLE (`fd7a1b...`): 26 documents, no placeholder forms, and label-only support above the frozen per-bin floor. Added complete prior-ID/URL/sequence/content exposure inventory and a 20-document whole-source floor.
- 2026-08-03: Ninth plan review returned `SHIP` for the GENTLE replacement and required the implementation manifest to bind the selected-panel document-union floor. The no-inference harness audit then found that `rows.jsonl` preserved pre-sort selection order while reference caches used canonical unit-ID order. Archived both affected no-inference builds, changed the builder/verifier to align rows after canonical sorting, rebuilt twice byte-identically, and added a regression test. No model weights or neural forward were opened during this repair.
- 2026-08-03: First implementation review returned `BLOCK`. Archived the exact blocked candidate and inventory snapshot, then made held-out validation authorizations bind and reverify the implementation candidate and exact inventory; removed the retired ESLSpok stage in favor of GENTLE; added independent semantic, lineage, row-order, dtype/shape, and numerical recomputation of the retained attempt-7 EWT bundle; and moved runtime attestation to a mandatory pre-forward gate with a postflight comparison. Added mutation and preflight regression tests and rebuilt the no-inference prescore. No model weights or neural forward were opened during this repair.
