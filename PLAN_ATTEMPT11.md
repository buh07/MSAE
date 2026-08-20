# Atlas v3.7 Attempt 11 — endpoint-scoped numerical QA and exploratory atlas

## Goal

Permanently retire Attempt 10, use the already opened EWT/GUM/GENTLE technical artifacts to diagnose RoPE numerical error and calibrate a coherent normalized gate, validate that gate once on two untouched technical panels, and then run the unchanged Atlas v3.3 scientific measurements with endpoint-specific eligibility. Run no neural training.

## Non-goals

- Do not rerun, change, or reinterpret Attempt 10 or its GENTLE result.
- Do not use EWT, GUM, or GENTLE as validation data again; all three are development-only.
- Do not change scientific rows, labels, estimators, projections, interventions, thresholds, result schema, or architecture-decision rules in the frozen Atlas v3.3 study. The frozen result is preserved verbatim; Attempt 11 adds a separate technical-eligibility overlay rather than rewriting it.
- Do not train, fine-tune, or update any model, SAE, probe, or checkpoint. Existing frozen linear probes may be replayed only for technical sensitivity analysis.
- Do not describe the resulting scientific atlas as confirmatory: its EWT/GUM scientific panels are already opened, and the new panels validate numerical behavior rather than scientific hypotheses.

## Constraints and fixed history

- Attempt 10 remains terminal at `pilot_runs/20260803_atlas_rope_technical_v6/TERMINAL.json` (SHA-256 `9e11622335af072f6f273596917fd729fe38cfd4c65dd18b883fd43cc06dc109`) with `no_retry_authorized=true`.
- Attempt 10's exact cached replay passed, repeated live reference inference was byte-identical, and its approximate-equivariance grid failed only the hard cosine cap in two cells because one GENTLE row had cosine distances `5.54e-11` and `9.95e-11`; both relative-L2 errors remained below `2e-5`.
- EWT, GUM, and GENTLE are opened technical-development sources. Any new forward on them is explicitly development, never validation.
- Fresh technical validation sources are label-free for this study and receive no model inference before the reviewed freeze. Their upstream revisions and deterministic selection rules are fixed here; exact raw-file and generated-panel hashes will be bound in the reviewed implementation candidate before inference:
  - English composite: UD English CHILDES commit `92d3cf4c7c567bdebfe412573fecb7ec93332c30` plus UD English CTeTex commit `3d2bda424dcdedb8889aeec9f81ee6401994f7f2`. The exact per-bin allocation appears below; source membership is retained in every row and the composite limitation is disclosed. CHILDES has no upstream `newdoc` markers, so its upstream `corpus_name` and `child_name` metadata define conservative participant-corpus groups; no document-, transcript-, household-, or statistical-independence claim is made.
  - Multilingual stress panel: UD Czech PDT commit `6d206ec7d337a7f76f34ddfc82893389cabbd76d`, explicitly a runtime/numerical stress test rather than evidence that the English scientific constructs generalize cross-lingually.
- Each fresh panel contains 100 distinct bases: 20 per frozen length bin, at most two bases from any genuine document or disclosed participant-corpus group within a bin, at least ten distinct groups per bin, the six frozen shifts, and the same two selected token positions. Raw file hashes, source commits, row IDs, and selection statistics become immutable when the M3 implementation candidate is reviewed; they are not claimed to exist at plan time.
- The English composite's allowed source is exact by bin: CHILDES for `4-8`; CTeTex for `9-16`, `17-32`, `33-64`, and `65-128`. Czech PDT supplies all five bins in the stress panel.
- Candidate filtering is frozen: parse only integer-token UD sentences with explicit genuine document IDs or the disclosed CHILDES participant-corpus grouping; tokenize with the pinned tokenizer and retain only complete layouts whose tokenized length is in `4..128`; reject placeholder forms, duplicate sentence/sequence identities, and exact document/group, sentence, source-URL, normalized-content, or token-sequence identities found in any prior project prepared/inference cache. Within each allowed source/bin, sort by SHA-256 of the UTF-8 tuple `atlas_rope_v7_attempt11`, source, document/group ID, sentence ID, and token-sequence SHA, breaking ties by UTF-8 sentence ID; greedily retain sequence-distinct rows subject to the two-per-group cap.
- CHILDES group derivation is exact: for every raw sentence block, parse exactly one `sent_id`, `corpus_name`, and `child_name`; strip only surrounding whitespace introduced by CoNLL-U comment framing, preserve internal whitespace and Unicode code points without normalization, and reject missing, empty, duplicate, conflicting, NUL, CR, or LF values. Canonically encode `[corpus_name, child_name]` as UTF-8 JSON with `ensure_ascii=false` and separators `(',', ':')`; the group ID is `childes_group:` plus the first 24 hex characters of its SHA-256. The derived row records raw path/hash, one-based block index, raw-block SHA-256, sentence ID, both exact parsed fields, canonical tuple bytes SHA-256, and group ID. Parser-only `newdoc` markers use this ID in a temporary file; raw bytes are never rewritten, and lineage must reconstruct exactly.
- The validation raw root has an exact top-level allowlist: `UD_English-CHILDES`, `UD_English-CTeTex`, and `UD_Czech-PDT`. Rejected PUD is isolated under `data/atlas_rope_v7_attempt11_rejected_scouting`, bound by a rejection record, and is forbidden from every panel manifest, authorization, command, and runtime-open ledger.
- Runtime/model remain Pythia-160m-deduped revision `582159a2dfe3e712a8d47ae83dec95ae3bde8e7e`, float32, hidden-state index 4, deterministic inference, and the pinned environment in `requirements-atlas.lock.txt`.
- No validation result may change a threshold, row budget, panel, endpoint map, or science definition. Each validation panel is create-once. Failure cannot be retried as Attempt 11.

## Grounded code path

- `scripts/atlas_rope_v6.py` supplies frozen five-bin grid construction, row-error metrics, float64 RoPE helpers, hashing, and signed artifact utilities.
- `scripts/run_atlas_rope_v6.py` supplies the frozen model loader/runtime attestation and demonstrates separate exact-replay and repeated-live checks.
- `scripts/diagnose_atlas_rope_v5.py` already measures pre-rotary Q/K, float32-vs-float64 rotary error, invariant attention-logit error, and layer residual propagation; Attempt 11 narrows this to the opened GENTLE outlier and records row-level rather than only aggregate evidence.
- `scripts/run_atlas_rope_v6_science.py` wraps the byte-frozen Atlas v3.3 extraction/analysis. Attempt 11 will reuse the same frozen scientific functions by hash while replacing only the all-or-nothing QA authorization with endpoint-scoped eligibility metadata.
- `pilot_runs/20260802_atlas_measurement_v2_4/analysis/probe_models.npz` and its signed caches permit a development-only sensitivity replay without fitting an estimator or running a model forward.

## Approach

### A. Permanent retirement and opened-development import

Create an Attempt-11 signed retirement attestation that verifies the Attempt-10 envelope, exact SHA, terminal status, `no_retry_authorized`, and absence of a science authorization/completion. It authorizes no Attempt-10 action. Import the signed EWT/GUM/GENTLE arrays read-only into a development manifest and compute row-level error summaries versus shift, length bin, selected token position, reference activation norm, norm ratio, relative L2, and cosine distance.

### B. Separate three technical checks

1. **Exact cache round-trip integrity:** a saved representation array is reloaded through the same cache/reduction path; bytes, hashes, shapes, dtypes, and row IDs must match exactly, with zero failures. This validates persistence and lineage, not an independent model replay.
2. **Repeated live inference:** three same-input/same-position runs are compared bytewise and reported separately. This is runtime reproducibility, not RoPE equivariance.
3. **Approximate equivariance:** translated-position representations are compared with one primary row criterion:
   - relative L2 `<= 2e-5`; and
   - absolute activation-norm-ratio error `<= 1e-5`.

Cosine and coordinatewise `atol=2e-5, rtol=5e-6` are descriptive. A derived cosine reference ceiling of `2.5e-10` is reported only as a coherence diagnostic; it is not an independent promotion gate. This avoids contradicting a `2e-5` relative-L2 allowance with a much stricter directional metric.

The approximate gate is distributional rather than a global maximum: in each fixed 40-row length-bin/shift cell, at most two rows may exceed the primary criterion, and at most six of 1,200 rows may exceed it panel-wide. No row may exceed catastrophic ceilings of relative L2 `5e-5` or absolute norm-ratio error `2e-5`; all rows must be finite.

These values and rules are fixed now and development cannot change them:

- cast rows to float64 for reduction;
- let `a` be reference, `b` translated candidate, `na=||a||2`, `nb=||b||2`, and require `na>1e-12`; otherwise the row is primary and catastrophic failure;
- `relative_l2=||b-a||2/na` and `norm_ratio_error=abs(nb/na-1)`;
- do not divide when `na<=1e-12`; an invalid reference norm is explicitly both a primary and catastrophic failure;
- a primary row failure is the Boolean OR of nonfinite input/metric, `na<=1e-12`, `relative_l2>2e-5`, or `norm_ratio_error>1e-5`;
- a catastrophic row failure is the Boolean OR of nonfinite input/metric, `na<=1e-12`, `relative_l2>5e-5`, or `norm_ratio_error>2e-5`;
- a cell passes iff primary failures are at most two and catastrophic failures are zero;
- each panel records two separate Booleans: `integrity_runtime_pass` requires exact cache round-trip, three byte-identical live references, all reference/candidate arrays finite, exact reviewed implementation/panel/runtime lineage, and matching pre/post runtime attestations; `approximate_equivariance_pass` requires `integrity_runtime_pass`, all 30 cell rules, at most six total primary failures, and zero catastrophic failures;
- cross-panel `baseline_runtime_pass` is true only when `integrity_runtime_pass` is true for both English and Czech panels; cross-panel `rope_translation_pass` is true only when `approximate_equivariance_pass` is true for both panels;
- cosine uses product floor `1e-24`; `2.5e-10` is a fixed descriptive reference only;
- coordinate diagnostics use fixed `atol=2e-5`, `rtol=5e-6` and never gate promotion.

The hook-study earliest-entry report uses three fixed, separately reported floors: max absolute error `>1e-7`, relative L2 `>1e-8`, and cosine distance `>1e-12`. No development outcome may alter any gate, floor, budget, panel membership rule, shift, or selected-position rule.

### C. Development-only causal/numerical diagnosis and sensitivity

- Reanalyze all opened caches without model inference.
- On the already opened GENTLE outlier only, run a new development hook study at shifts 0/1/4/8/16/32/64, batch size one, capturing per layer:
  - pre-rotary Q/K;
  - float32 rotated Q/K versus a NumPy float64 reference;
  - inverse-transported post-rotary Q/K;
  - causal-valid attention logits;
  - hidden/residual states.
- Identify the earliest stage at which error exceeds predeclared reporting floors. Do not treat observer-instrumented output as the validation reference; an unhooked live repeat is separate.
- Replay existing Atlas measurement-v2.4 linear probes on C2 caches under deterministic, norm-matched directions from the opened technical deltas at primary `2e-5` and catastrophic `5e-5` scales. Construct the fixed direction set by taking the 32 largest-relative-L2 finite deltas plus 32 SHA-256-smallest remaining finite deltas after exact byte deduplication; normalize each in float64 and test both signs. For each scale/direction, perturb every C2 raw row by `epsilon*||row||2*direction`, derive the simple projection through its frozen linear map, and replay frozen raw/simple probes without refitting. Report the worst prediction-flip fraction, macro-F1 change, retention/selectivity threshold comparison, and pre-existing projection-baseline label. For each raw linear probe, also report the fraction whose top-one margin exceeds the exact dual-norm logit bound for every alternative class. A supported endpoint is `decision_stable` only if every tested direction/sign changes macro F1 by at most `0.001` and no frozen threshold comparison or label changes. Learned-branch and nonlinear Atlas v3.3 endpoints are explicitly `not_certified_by_v2_4_sensitivity`; this study is supporting development evidence, not a universal guarantee.

### D. Fresh, one-shot validation

After implementation verification, the development report, and `/adversarial SHIP` of an exact freeze candidate:

1. run the English CHILDES+CTeTex composite once;
2. run Czech PDT once as a second independent runtime/numerical stress panel.

Each run records exact cache round-trip integrity, three live repeats, the translated grid, normalized/descriptive metrics, runtime attestation, frozen implementation lineage, finite arrays, and no-training attestations. Baseline lexical/relational/token-local paths are eligible only when cross-panel `baseline_runtime_pass=true`; translation-dependent paths additionally require `rope_translation_pass=true`. A failure of only approximate equivariance leaves baseline paths eligible, while any cache/runtime failure makes all scientific claim paths ineligible. Any failure is permanent for Attempt 11 but does not erase finite frozen measurements.

### E. Endpoint-specific scientific validity

The frozen Atlas v3.3 computation still runs after both validation panels reach signed terminal results. The original `result.json`, `candidate_statuses`, and `outcome` are saved without mutation. Attempt 11 creates a separate signed `technical_eligibility_overlay.json` with `eligible`, `ineligible`, or `not_applicable` for exact JSON-path patterns. It never recomputes or promotes a candidate after dropping an ineligible dependency.

The field-level dependency matrix is:

| Frozen result JSON path | Dependency | Failure propagation in separate overlay |
|---|---|---|
| `schema_version`, `status`, `lineage`, `environment`, `neural_training_run` | artifact integrity/runtime attestation | mark overlay lineage invalid; do not interpret any result |
| `task_results.*.*` | cross-panel `baseline_runtime_pass`, finite science cache, cache lineage | eligible only if `baseline_runtime_pass`; no approximate-translation dependency |
| `relational_advantage.*.*` | cross-panel `baseline_runtime_pass`, finite science cache, cache lineage | eligible only if `baseline_runtime_pass`; no approximate-translation dependency |
| `numerical_null_qa.*` | superseded historical QA | `not_applicable` for Attempt-11 promotion; retain verbatim for provenance |
| `interventions.*.summaries.relative_gap` | approximate position-ID translation | ineligible if either fresh panel fails |
| `interventions.*.summaries.true_context` and `.unrelated_context` | approximate position-ID translation because the frozen sham is `prefix_position_only` | ineligible if either fresh panel fails |
| `interventions.*.summaries.proper_noun_substitution` | cross-panel `baseline_runtime_pass`, finite cache, cache lineage | eligible only if `baseline_runtime_pass` |
| `cross_family_specificity.*` | all intervention classes | ineligible if any translation-dependent intervention is ineligible |
| `delta_basis_overlap.relative_gap`, `.true_context`, `.unrelated_context` (all children) | corresponding translation-dependent intervention plus cross comparisons | ineligible if either fresh panel fails |
| `delta_basis_overlap.proper_noun_substitution.within` | proper-noun intervention plus `baseline_runtime_pass` | eligible only if `baseline_runtime_pass` |
| `delta_basis_overlap.proper_noun_substitution.cross`, `.max_cross`, `.pass` | proper-noun plus translation-dependent cross comparisons | ineligible if either fresh panel fails |
| `projections.*.*` including every organization/rank/status | task, relation, every capture intervention, cross-family specificity, and basis overlap | mixed output; entire subtree ineligible if either fresh panel fails; no partial recomputation |
| `candidate_statuses.*`, `outcome`, `technical_failure`, `technical_failure_reasons` | all projection/specificity dependencies under the frozen aggregator | frozen values retained, but overlay architecture promotion is `technically_ineligible` if either fresh panel fails; otherwise interpret the frozen vocabulary unchanged |

The frozen `prefix_position_only` control is itself a global translation of identical target tokens by the prefix length, so context summaries remain translation-dependent. This is more conservative than the proposed broad context independence and preserves the existing mapping at `scripts/analyze_atlas_discovery_v3_3.py:730-755`.

For scientific interpretation, the endpoint classes therefore are:

| Endpoint class | Frozen constructs | Technical dependency | Eligibility rule |
|---|---|---|---|
| RoPE translation | uniform position-ID translations and relative-gap/position-translation controls | approximate equivariance | eligible only if both fresh panels pass |
| Context | true-context and unrelated-context prefix interventions | approximate translation through the frozen `prefix_position_only` sham | eligible only if both fresh panels pass |
| Lexical | proper-noun/entity substitutions and token-local lexical probes | cache integrity + repeated live runtime | independently eligible if integrity/repeat checks pass |
| Relational syntax | child-head/dependency probes and relation-aware contrasts | cache integrity + repeated live runtime | independently eligible if integrity/repeat checks pass |
| Boundary/other token-local decoding | decoding without uniform position translation | cache integrity + repeated live runtime | independently eligible if integrity/repeat checks pass |

Finite frozen results remain reportable as measurements even when the overlay marks their claim path ineligible. If a required dependency is ineligible, the overlay uses the existing frozen vocabulary `technically_ineligible` for architecture promotion while preserving the original frozen `outcome` unchanged; no result is promoted by silently dropping a failed class. The science output is always labeled exploratory. A single top-level signed Attempt-11 `COMPLETE.json` and rendered `report.md` bind the hashes of the unmodified frozen result and the overlay, display overlay/promotion status before any frozen outcome, and state that the frozen result alone is non-promotable.

## Alternative considered

Raising Attempt 10's cosine cap to exceed the observed GENTLE maximum would be much simpler, but it would reuse an opened validation panel, chase an extreme value, retain an incoherent dual metric, and preserve the all-or-nothing endpoint failure. It is rejected. A wholly new scientific protocol is also rejected because the scientific atlas definitions need not change; only technical QA and missingness semantics are amended.

## Milestones

### M1 — Plan review

- [ ] Validate this plan structurally.
- [ ] Obtain independent `/adversarial SHIP`; revise and repeat if necessary.

Acceptance: no new model inference or Attempt-11 signature exists before SHIP.

### M2 — Offline preparation and implementation

- [ ] Copy only pinned fresh UD raw files into a versioned Attempt-11 data root and record raw hashes/commits.
- [ ] Implement deterministic document-capped panel construction, three-way QA, normalized gate, opened-cache diagnosis, outlier hook study, sensitivity replay, endpoint mapping, signing/terminal guards, tmux pipeline, and tests/smoke path.
- [ ] Build fresh panels without model inference, verify support/lineage, and bind their exact manifests in the implementation candidate.

Acceptance: tests cover source support, row order, all primary/catastrophic budgets, zero/tiny reference norms, nonfinite values, cache round-trip integrity, separate baseline/translation cross-panel propagation, no-retry behavior, and no-training scan. CHILDES-specific tests cover metadata completeness/uniqueness, exact canonical group IDs, raw-block lineage reconstruction, raw-byte immutability, two-per-group and ten-group rules; inventory tests require zero PUD paths in validation manifests, authorizations, commands, runtime-open ledgers, and the exact raw-root allowlist.

### M3 — Implementation review

- [ ] Run syntax, targeted tests, frozen Attempt-10/9/7 regression checks, source hash checks, and reproducibility/no-training scans.
- [ ] Materialize an exact implementation candidate inventory.
- [ ] Obtain `/adversarial SHIP` of that inventory and diff; fix and re-review all findings.

Acceptance: reviewer SHIPs the exact code/config/data-manifest candidate before any Attempt-11 inference.

### M4 — Opened technical development

- [ ] Sign Attempt-10 retirement and opened-source import.
- [ ] Run cached distribution analysis, GENTLE outlier hooks, and downstream sensitivity in an Attempt-11 development namespace.
- [ ] Produce a freeze candidate binding the already fixed thresholds/budgets/formulas, field-level endpoint map, source manifests, runtime, implementation hashes, and development evidence. Development results may only be summarized; they cannot change the freeze contract.
- [ ] Obtain `/adversarial SHIP` of the exact freeze candidate; fix issues without inspecting fresh validation outputs.

Acceptance: development outputs use only opened sources; fresh validation cache/result roots remain absent.

### M5 — Asynchronous one-shot execution

- [ ] Select a currently free GPU by UUID, bind it in the signed authorization, and launch one tmux pipeline.
- [ ] Run English validation, Czech validation, endpoint authorization, then the endpoint-scoped frozen exploratory atlas.
- [ ] Observe a live authorized GPU child (or a legitimate signed fast terminal/completion) and never relaunch a terminal outcome.

Acceptance: tmux session, pane command/PID, GPU UUID, logs, signed authorization, and live/terminal state are recorded; no training path exists.

## Definition of done

- [ ] Attempt 10 is unchanged and signed as permanently retired by Attempt 11.
- [ ] EWT/GUM/GENTLE are explicitly development-only; neither fresh panel influenced gate selection.
- [ ] Cache round-trip integrity, repeated live inference, and normalized/distributional approximate equivariance are separate in code and output.
- [ ] The GENTLE outlier has stage-by-stage and float64-reference diagnostics.
- [ ] Downstream sensitivity is quantified with limitations and cannot silently certify unsupported nonlinear behavior.
- [ ] Two pinned, document-supported, untouched panels are frozen before their first inference and each is one-shot.
- [ ] Scientific eligibility and missingness are endpoint-specific in a separate overlay; required missing dependencies mark architecture promotion `technically_ineligible` without mutating or deleting finite frozen results.
- [ ] The frozen scientific result, schema, status vocabulary, and outcome are unchanged and separately labeled exploratory.
- [ ] A reviewed, authorized tmux pipeline is running on a free GPU or has already produced a signed legitimate terminal/completion.
- [ ] No neural training, optimizer, backward pass, parameter update, or checkpoint creation occurs.

## Verification plan

- Plan: `check-plan --path PLAN_ATTEMPT11.md` and independent `/adversarial` review.
- Static: `python -m py_compile` for all new Python, shell `bash -n`, JSON parse, implementation inventory hashes, and a token-level no-training scan.
- Tests: targeted Attempt-11 tests plus frozen Attempt-10, Attempt-9, and Attempt-7 suites.
- Data: exact git commit, raw SHA-256, parser counts, document/bin support, document cap, unique bases/rows, and no prior sequence/content-hash overlap.
- Development: signed input/output hashes; independent recomputation of cached metrics, outlier lineage, earliest-stage logic, and sensitivity decisions. Sensitivity contextualizes but cannot alter the already-fixed thresholds.
- Freeze: exact artifact SHA in the adversarial review and create-once signed authorization.
- Launch: `nvidia-smi`, tmux session/pane/PID, `CUDA_VISIBLE_DEVICES`, log tail, and signed status verification.

## Risks and one-way doors

- **Post-hoc gate selection:** all three old sources are development. Mitigation: thresholds are frozen before development, then contextualized by metric geometry and downstream sensitivity before two fresh panels; fresh output never feeds back.
- **Composite English panel:** different corpora supply different length bins, and CHILDES groups repeated observations by participant/corpus rather than an upstream document marker. Mitigation: preserve source/grouping and raw-block lineage per row, cap each group at two bases per bin, report per-source/bin composition, and make no document, transcript, household, statistical-independence, single-population, or scientific-inference claim.
- **Cross-language runtime scope:** Czech is a numerical stress panel, not scientific generalization evidence.
- **Distributional budget:** allowing two failures per cell can hide a localized tail. Mitigation: also impose a six-row panel budget, catastrophic maxima, per-cell reporting, and endpoint ineligibility on failure.
- **Sensitivity scope:** existing v2.4 linear-probe replay cannot certify every v3.3 nonlinear/intervention endpoint. Mitigation: label it bounded supporting evidence, report unsupported endpoints, and never use it alone to promote an architecture claim.
- **Hooks perturb execution:** hooked diagnosis never supplies validation representations; unhooked repeated inference is separate.
- **Freshness claims:** metadata/source-support inspection occurred before freeze. Mitigation: disclose it; no model inference or representation/metric output is inspected before validation authorization.
- **One-shot validation:** opening either fresh representation cache is irreversible for confirmation. Mitigation: exact freeze review and create-once staging/terminal guards.
- **Partial pipeline failure:** signed stage terminals and endpoint-specific results prevent accidental rerun or silent promotion.
- **Detached frozen report:** a consumer could miss the overlay and read a nominative frozen outcome alone. Mitigation: the only Attempt-11 top-level report binds both hashes, leads with technical promotion eligibility, and explicitly prohibits promotion from the frozen artifact alone.

## Deviations log

- 2026-08-03: Fresh-source scouting inspected only public UD metadata and label-free document/length support; no model inference was run.
- 2026-08-03: M2's exact prior-exposure firewall showed that all otherwise eligible PUD rows overlapped previously opened project document identities, so PUD was rejected before any Attempt-11 inference. The English panel was amended to CHILDES `4-8` participant-corpus groups plus CTeTex `9-128`; this source amendment requires a renewed `/adversarial` plan SHIP and exact manifest review before inference.
- 2026-08-03: After implementation candidate `81507aa3590a7c743aad4a55e1dbf7f707ce87d8e5cd15ecf52f3d33ad252df9` received `/adversarial SHIP`, its signed development authorization was created, but `retire-attempt10` then failed before development or model inference because the controller treated `verify_attempt10_terminal()`'s verified payload as though it still contained the envelope signature. The candidate, authorization, empty lock-only run root, verification, and review are preserved under `reports/atlas_rope_v7/preinference_superseded_81507aa3590a/`; signed `SUPERSESSION.json` records zero model inference, zero fresh-value inspection, and prohibits reuse of the old authorization. The two-line envelope/payload repair and this provenance record require a fresh exact implementation candidate and `/adversarial SHIP` before any development execution.
