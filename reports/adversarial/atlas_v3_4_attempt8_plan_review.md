VERDICT: BLOCK
ONE-LINE: Validation is not truly held out or stratified, and calibration may contaminate the reused science atlas.

BLOCKERS

- [critical] `PLAN.md:35,46,50,103-109` — the plan calls the exact attempt-7 GUM panel held-out and gates it only as one source, but 32 of its 48 underlying units are the legacy attempt-5 GUM panel whose activation outcomes were already opened. `pilot_runs/20260803_atlas_discovery_v3_1_attempt5/failed_numerical_qa/GUM/QA_COMPLETE.json:3-43` records that signed GUM float16 run and failure, while `configs/atlas_discovery_v3_3/population_split_v3.json` explicitly composes attempt 7 from 32 legacy plus 16 fresh GUM pairs.
  reasoning — changing dtype and tolerance makes the attempt-8 float32 values new, but it does not make the legacy units outcome-naive; pooling legacy and fresh cells also lets familiar rows dilute a failure on the genuinely unopened dev/test rows.
  impact — the primary one-way held-out validation is mislabeled and can authorize science without an independent fresh-GUM pass, violating the leakage-safe GUM+ESLSpok contract.
  fix — classify legacy GUM as opened technical replication/diagnosis, never as held-out. Freeze separate non-poolable roles and require independent PASS gates for (a) fresh GUM dev/test and (b) ESLSpok. Either make legacy GUM non-authorizing or require it as an additional separately reported regression gate; never combine its element/row counts with fresh GUM. Bind the prior attempt-5 GUM envelope and state that none of its metrics may select attempt-8 thresholds.

- [critical] `PLAN.md:44-50,78-90,154` — score-bearing EWT calibration and invasive layerwise/Q/K/logit diagnosis are currently one stage, even though the plan itself admits hooks may change kernel paths or memory and says validation will use a minimal extractor.
  reasoning — a tolerance calibrated on a hooked diagnostic execution is not calibrated for the unhooked validation estimator. Separating diagnostics only from validation does not repair that estimator mismatch; it can shift exactly the tiny errors being gated.
  impact — the signed freeze could authorize validation using thresholds learned on a materially different computation path, defeating the purpose of the calibration/validation firewall.
  fix — define two independently inventoried EWT paths before inference: (1) a minimal score-bearing calibration executable that is byte/code-path identical to the GUM/ESLSpok validation executable except source/panel, and (2) a diagnostic-only executable with hooks. Derive every authorization metric solely from path (1). Run path (2) in a separate process/bundle, forbid it from the threshold derivation, and include a prespecified observer-effect comparison without allowing that comparison to tune validation.

- [critical] `PLAN.md:34,44,69-74,113-118` — the deterministic “expanded EWT-only” calibration grid has no frozen input population boundary and is not required to be disjoint from the retained final-v3 science population that M7 later reuses.
  reasoning — “explicit roles” does not prevent the same retained EWT train document/unit from receiving both calibration and science roles. Opening its activations while designing/calibrating the technical estimator would contaminate the supposedly unchanged later atlas even without labels.
  impact — attempt 8 could select its tolerance and diagnostic narrative on the same representation population used for the scientific organization decision.
  fix — restrict all EWT calibration/diagnostic units to an exact technical-only allowlist: the already reserved attempt-5 EWT challenge documents and/or pinned EWT dev/test documents, never retained final-v3 science documents. Before any model call, freeze and test document, component, sentence, unit, and content-hash disjointness against every final-v3 science row/intervention/relation input. If that pool cannot support the declared shift×length cells, declare prescore infeasible rather than borrowing science units.

- [high] `PLAN.md:48-50,70-74,96-101,103-109` — the validation gate is source-aggregate and leaves the metric contract incomplete: no per-family/shift/length-bin gates, exact cell counts, integer rounding rule for `0.1%`/`5%`, relative-L2 denominator/floor, cosine zero-norm behavior, accumulation dtype, or missing-cell rule is frozen.
  reasoning — correlated failures can be concentrated in the position family, largest shifts, or longest sequences yet be diluted below a source-wide rate; different implementations can also disagree at rate boundaries or near zero while all claiming to follow this plan.
  impact — the one-shot validation decision is neither uniquely executable nor sensitive to the failure modes the expanded grid is meant to diagnose.
  fix — prespecify formulas and float64 accumulation, norm floors/zero handling, exact denominators and `floor`/`ceil` semantics, and complete cell counts. Gate each held-out source separately and also every required family×shift×length cell with no pooling across legacy/fresh roles; any absent/undersupported cell is ineligible. Label the rejection limits as fixed engineering budgets, not inferential error rates, and justify their values/sample-size feasibility before opening validation.

REVISIONS

- [high] `PLAN.md:44,71,78,90,155` — “pre/post-rotary Q/K,” “attention-logit,” and “first meaningful divergence” are not operationally unique. Freeze the attention backend (for example, eager rather than SDPA/fused), exact module/tensor capture points, head/token axes, masking/scaling convention, cast/device policy, array inventory, and memory-safe batch plan. Define the float64 reference narrowly as applying the identical rotary formula/phase convention to the same captured pre-rotary Q/K in float64. Replace “first meaningful divergence” with a prespecified first threshold-exceeding capture site and prohibit causal localization from later-layer propagation alone.
- [high] `PLAN.md:60-64,130,152` — the destination of `RETIRED.json` is unspecified. Writing it into the attempt-7 run root would mutate the inventory being retired. Put it in a new attempt-8 provenance root, recursively hash the read-only attempt-7 tree, and enforce that no attempt-7 path is writable by the attempt-8 runner. Also describe this as a signed freeze of current evidence/operator attestation, not cryptographic proof that no historical unlogged invocation ever occurred, consistent with the prior post-result review.
- [high] `PLAN.md:13,113-118,146` — “unchanged science implementation” is not mechanically defined, while attempt-7 extraction authorization cannot simply accept attempt-8 validation signatures. Freeze which scientific files/functions must be byte-identical, permit only a narrow reviewed authorization/namespace adapter, and require a semantic-diff allowlist plus all attempt-7 science fixtures and deterministic label-only rebuild hashes. Otherwise “unchanged” is only narrative.
- [medium] `PLAN.md:36,70,103-109,157` — ESLSpok was already used in the earlier measurement study. Inventory any overlap between the proposed dev/test units and earlier opened activation units, label ESLSpok as outcome-new-for-this-metric rather than broadly fresh/independent, and keep its gate separate. Specify fail-closed order: if fresh GUM fails, do not open ESLSpok; if ESLSpok fails, do not authorize science.
- [medium] `PLAN.md:14,79,114-118` — make the no-training boundary executable rather than terminological: technical validation must not load labels or instantiate any estimator; scientific closed-form ridge probes remain fit-source-only under the frozen attempt-7 code; autograd is disabled; optimizer/scheduler/checkpoint modules and outputs are forbidden by exact allowlists and terminal checks.

NITS

None.

CHECKS RUN

- `/jumbo/lisp/f004ndc/.agent-workspace/bin/check-plan --path PLAN.md` → PASS; structural plan gate passed.
- Read-only line-by-line review of `PLAN.md`, the signed attempt-7 terminal, and `reports/adversarial/atlas_v3_3_attempt7_post_result_review.md` → attempt-7 no-retry/scientific-null boundary is correctly stated, subject to the retirement-location revision above.
- Read-only attempt-5/attempt-7 GUM lineage audit → found a signed opened attempt-5 GUM QA bundle (`float16_inference_float32_cache`, 32 underlying units, FAIL) and confirmed the attempt-7 split reuses 32 legacy GUM pair IDs plus 16 fresh pair IDs.
- Static inspection of the attempt-7 QA translation/extraction and authorization path → exact translations preserve tokens/masks/selected positions; full authorization requires both QA sources; no neural inference was run.
- Filesystem inspection of pinned ESLSpok inputs and prior project references → dev/test/train files exist at the stated revision, but ESLSpok was previously used by Atlas measurement v2, supporting only the narrower supplementary role.

CONTRACT COVERAGE

- User-requested separation of cached replay, live repeatability, approximate translation, layer diagnostics, and float64 reference → partial — all concepts are named (`PLAN.md:42-50,76-83`), but score-bearing versus hooked diagnostic paths and exact Q/K/logit/reference definitions are unresolved.
- Attempt-7 signed retirement/no retry → partial — non-goals and sequencing respect the terminal (`PLAN.md:11,20,52,58-64`), but retirement placement and the strength of the negative provenance claim are unspecified.
- Leakage-safe EWT calibration and frozen validation → unmet — expanded EWT calibration is not explicitly disjoint from science, and the GUM gate includes already opened legacy units.
- Numerical/statistical validity and unique gate execution → unmet — aggregate rates can hide cell failures and boundary/metric semantics are undefined.
- Feasible Q/K/logit/float64 diagnosis → partial — risks are recognized, but backend, capture, isolation, reference, resource, and attribution contracts are not frozen.
- Held-out GUM plus ESLSpok roles → unmet — fresh GUM is not isolated from opened legacy GUM; ESLSpok's prior exposure is acknowledged but not inventoried at unit level.
- Unchanged scientific atlas → partial — tasks/thresholds/population are declared unchanged, but code identity and the required authorization adapter are not bounded.
- No-neural-training boundary → met in intent — explicit throughout (`PLAN.md:14-16,79,116,126,136`), with executable allowlists/assertions still requested as a revision.
- One-way-door sequencing → partial — implementation and freeze reviews precede validation, and validation precedes science, but the current gates are not safe enough to open validation.

UNKNOWNS

- Whether the technical-only EWT pool can supply adequate independent units in every proposed shift×length×family cell without touching retained science.
- Whether the installed Pythia/Transformers attention backend exposes the proposed native Q/K/logit sites without patching or changing the score-bearing kernel path; this needs a no-model static prototype and synthetic shape tests before authorization.
- Which exact ESLSpok dev/test units or representation outcomes were opened in prior Atlas v2 work; source-level familiarity is known, unit-level overlap is not yet inventoried.
