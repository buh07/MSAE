VERDICT: BLOCK
ONE-LINE: Eager validation mixes with SDPA history and cannot certify the byte-frozen science runtime.

BLOCKERS

- [critical] `PLAN.md:25,49,57,77,81,152-159`; `scripts/extract_atlas_discovery_v3_3.py:278-282` — attempt 8 explicitly pins the minimal calibration/validation and diagnostic paths to `eager`, but the retained attempt-7 EWT arrays and the byte-frozen scientific inference path were produced by a loader that did not pin an attention implementation. In the frozen `transformers==4.53.2` / `torch==2.7.0` environment, GPT-NeoX advertises SDPA support and the Transformers automatic attention-selection classmethod resolves an otherwise unpinned GPT-NeoX configuration to `sdpa`. The attempt-7 signed QA lineage does not attest the effective backend.
  reasoning — the calibration maximum is now intentionally the union of retained attempt-7 arrays and new minimal-path arrays. That union is valid only if its members estimate the same numerical process. Combining likely-SDPA retained arrays with forced-eager new arrays makes the frozen cap backend-dependent without representing either one estimator. The conflict then continues into M7: reusing byte-frozen `_forward_units` with its original automatic dispatch means eager validation does not certify the SDPA science runtime, while overriding it to eager changes the supposedly mechanically unchanged scientific computation. Attention backends are permitted to use different kernels and reduction orders, precisely the quantity this technical study is trying to bound.
  impact — the irreversible GUM/ESLSpok opening could be authorized by thresholds calibrated on a mixed estimator and then used to authorize a different science runtime. A later result could not distinguish RoPE error from backend drift, and the claimed attempt-7 lineage/unchanged-science guarantees would be false or unverifiable.
  fix — choose one effective backend before any new model call and make the retained calibration, minimal EWT, exact fresh-GUM pairs, GUM grid, ESLSpok grid, diagnostic observer, and scientific extraction refer to that same runtime contract. The clean lineage-preserving repair is to pin `sdpa` everywhere, require a runtime assertion that `model.config._attn_implementation == "sdpa"`, and bind the Transformers auto-selection/SDPA integration source hashes plus Torch/CUDA/cuDNN versions, relevant SDPA backend flags, determinism/TF32/autocast state, GPU identity, and loaded-library hashes into every authorization/result bundle. If `eager` is instead the intended new estimator, retained attempt-7 arrays cannot set its caps: rerun the exact EWT calibration conditions under eager and label old SDPA arrays historical-only, then explicitly acknowledge that science inference has changed. Do not open validation until one alternative is frozen and independently reviewed.

REVISIONS

- [high] `PLAN.md:49,57,95,134,173` — the population definition correctly says the retained attempt-7 EWT arrays and new minimal EWT grid jointly determine every cap, but the approach and M4 acceptance still say thresholds/only metrics come from “minimal calibration” or “only minimal metrics.” Replace these phrases with the exact verified union. State that only hooked diagnostic metrics are excluded; otherwise an implementer can legally omit the retained arrays despite the repaired rule.
- [medium] `PLAN.md:49,60-61,69,146-150,175` — the exact fresh-GUM bundle is correctly mandatory and fixes its true offsets, coordinate, L2, cosine, and zero-failure requirements, but its paragraph does not literally import the cached-replay, three-live-repeat, finite/dtype, duplicate, completeness, and lineage gates used by the grid. Require every exact pair to pass those common gates too and bind their individual row/pair digests; “each pass the frozen coordinate/L2/cosine rules” is narrower than the complete technical contract.
- [medium] `PLAN.md:88,128-142` — hooked/unhooked disagreement makes the diagnostic bundle invalid, but the state transition after that invalidity is unspecified. Decide before EWT whether a valid diagnosis is mandatory for this five-step technical study (then terminalize before validation) or is an independently missing descriptive endpoint (then sign `DIAGNOSTIC_UNAVAILABLE` and permit only the already-valid score path). Do not silently proceed with an invalid bundle.
- [medium] `PLAN.md:84,88,116` — line 84 still calls the reconstructed tensors “native post-rotary Q/K,” while line 88 correctly says no executed post-RoPE tensors are captured. Rename them consistently to “reconstructed float32 post-rotary Q/K.” At prescore, also freeze the inverse-transport arithmetic dtype, rotary/non-rotary dimension handling, operation order, and exact residual reductions for `local_rotary` and `aligned_total_post`; source hashes alone do not uniquely specify the new out-of-band comparison.

NITS

- `PLAN.md:81` — the whole `modeling_gpt_neox.py` hash transitively covers its eager/SDPA integration function, but a direct function hash is easier to audit and should accompany the other named source hashes after the backend decision.

CHECKS RUN

- `/jumbo/lisp/f004ndc/.agent-workspace/bin/check-plan --path PLAN.md` -> PASS.
- Read-only, line-by-line comparison of revised `PLAN.md` with `reports/adversarial/atlas_v3_4_attempt8_plan_review_v2.md` -> both v2 blockers and all four v2 revisions are now represented literally, subject to the narrower follow-ups above.
- Static no-inference audit of the frozen fresh-GUM records -> all 16 exact pairs are now mandatory and non-poolable; the eight `prefix_position_only` offsets are exactly `{7,9,12,16,17,28,37,41}`.
- Static no-inference audit of installed source hashes -> every literal hash at `PLAN.md:81` matches the installed file/function source (`modeling_gpt_neox.py`, `GPTNeoXAttention`, `GPTNeoXRotaryEmbedding`, `apply_rotary_pos_emb`, and `rotate_half`).
- Static no-weight-load/no-forward-pass inspection of `transformers==4.53.2`, `torch==2.7.0`, GPT-NeoX backend support, Transformers attention autoset behavior, and the frozen loader at `scripts/extract_atlas_discovery_v3_3.py:278-282` -> GPT-NeoX supports SDPA; an unpinned configuration is automatically selected as `sdpa`, whereas the revised plan requires `eager`.
- Read-only audit of the revised diagnostics -> `propagated_pre`, `local_rotary`, common-frame `aligned_total_post`, and `invariant_logits` now avoid the v2 raw-frame error; all out-of-band tensors are described as reconstructed at `PLAN.md:88`.
- Read-only audit of support/exposure/replay rules -> minimum documents and per-document caps, bidirectional ESLSpok exact/subsequence/truncation/prefix/suffix exposure views, literal cosine denominator, and byte replay semantics are present.
- No neural model weights were loaded, no forward pass or experiment was run, and no implementation file was modified.

CONTRACT COVERAGE

- V2 blocker: retained-EWT calibration union and mandatory exact fresh-GUM pairs -> met in the governing population/gate clauses (`PLAN.md:49,57,146-150,173-175`); wording and common-gate follow-ups remain.
- V2 blocker: common-frame/local/propagated diagnostic semantics -> met (`PLAN.md:81-88`); reconstructed naming and arithmetic freeze follow-ups remain.
- V2 revision: genuine-document support and maximum contribution -> met (`PLAN.md:42-47`).
- V2 revision: ESLSpok exposure identities and bidirectional sequence views -> met (`PLAN.md:23-24,114-118,198`).
- V2 revision: executable cosine and byte-equality semantics -> met (`PLAN.md:53-61`).
- V2 revision: named backend and installed Transformer source hashes -> met literally but invalid as a cross-stage lineage choice; `eager` conflicts with the frozen automatic-SDPA history.
- Attempt-7 retirement/no retry -> met (`PLAN.md:9-13,19-23,92,104-110,170,193`).
- Cellwise validation, missingness, and fail-closed source order -> met for grid panels (`PLAN.md:38-71,144-150`).
- Minimal-versus-diagnostic isolation -> met (`PLAN.md:73-88`), with diagnostic-invalid state transition unresolved.
- Mechanically unchanged scientific atlas -> unmet as a runtime contract because its unpinned frozen loader and the new eager path cannot both satisfy estimator identity (`PLAN.md:152-159`).
- Effective attention/backend lineage across calibration, validation, diagnosis, and science -> unmet; this is a validation-opening one-way-door blocker.
- No-training boundary -> met in plan (`PLAN.md:12-15,120-126,157,177`).
- Safe to begin implementation or inference -> unmet until the backend/runtime contract is unified and independently reviewed.

UNKNOWNS

- The attempt-7 signed QA envelope omitted the effective attention backend and Transformers version. Static inspection of its frozen loader under the frozen requirements resolves to SDPA, but there is no contemporaneous runtime attestation; this uncertainty is itself why retained arrays cannot be mixed with a forced-eager estimator without repair.
- Whether the fixed EWT, GUM, and exposure-filtered ESLSpok panels remain feasible after all source/document/cell exclusions; prescore must answer this without inference and must fail closed.
- Whether all required Torch SDPA kernel controls and loaded CUDA libraries can be reproduced on the pinned GPU. Runtime attestations and synthetic equivalence fixtures must settle this before EWT authorization.
