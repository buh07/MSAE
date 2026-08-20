# Constructed Copy Circuit v1 — Ground-Truth End-to-End Control

## Goal

Run one separately versioned, prospective positive-control study asking whether the existing
capture/patch/score hierarchy can recover a **complete mechanism known by construction**. The study
uses an untrained, deterministic two-stage attention model whose only output path is an explicitly
registered key--value copying circuit. It measures necessity, sufficiency, sham specificity,
matched-control specificity, full-vocabulary restoration, and collateral error relative to a
full-output skyline on fresh development and confirmation panels.

Before this study, update `PAPER.md` and its claim ledger with the completed canonical-induction v2
result, emphasizing that ablation contribution passed while recovery and specificity failed.

## Non-goals

- Do not modify, resume, rescore, or reinterpret canonical-induction v2.
- Do not lower any v2 threshold, open its sealed confirmation panel, or select GPT-2 heads from its
  opened development results.
- Do not evaluate SAEs, projections, LEACE, K2, or any representation method.
- Do not train or tune a model; all constructed weights and graph edges are analytic and frozen.
- Do not claim that success in a constructed model validates any GPT-2 circuit, any representation
  method, or multi-model generality.
- Do not automatically run a method benchmark. Success may justify designing a separately frozen
  benchmark, not opening one under this namespace.
- Do not load a tokenizer, corpus, pretrained checkpoint, or natural-language prompt. The runner
  accepts only frozen, generated integer key--value rows and records `natural_prompt_assay=false`.

## Constraints

- Canonical-induction v2 and its blocked confirmation payload are immutable and read-protected.
- The new model is analytic, untrained, single-model, and has no unregistered output path.
- All estimators, seeds, thresholds, panels, and lifecycle transitions are protocol-hash-bound before
  any model-dependent smoke. Smokes use separate nonpanel fixtures and may repair implementation but
  may not change the locked protocol. The exact reviewed candidate is then frozen before any
  scientific panel is read or forwarded.
- Every live scientific forward runs in one UUID-bound tmux namespace on an available GPU.
- Candidate and exact-frozen adversarial reviews must both be `SHIP` before launch.
- No natural prompt, representation method, optimizer, backward pass, or training code path exists.

## Grounded repository observations

- `scripts/canonical_induction_two_tier_v2.py` already separates a decoder-tail skyline from an
  upstream circuit, uses one common gate cohort, block-paired bootstrap inference, deterministic GPU
  QA, and confirmation authorization only after a development gate.
- `scripts/launch_canonical_induction_two_tier_v2_tmux.sh` selects a free physical GPU, takes a
  UUID-specific lock, rechecks availability after locking, and binds the launcher PID/UUID into the
  run.
- `scripts/verify_paper_claims.py` checks claim markers, exact evidence hashes, and JSON pointers.
- Canonical-induction v2 ended `DEVELOPMENT_UPSTREAM_SET_STOP`; its Tier-A skyline was exactly one,
  its ablation-advantage gate passed, and its recovery, selectivity, and circuit-control-margin gates
  failed. Confirmation and method evaluation remained unopened.

## Constructed model and frozen causal graph

The model is an untrained two-stage causal attention system implemented only with PyTorch tensor
operations:

1. **Previous-token head.** On each value position, a fixed causal edge copies the immediately
   preceding key token into a pair-state key channel. The current value token occupies a disjoint
   pair-state value channel.
2. **Induction head.** At the final query position, an identity query/key comparison constructs an
   exact Boolean equality mask over value positions. Registered pre-softmax mask scores contain
   exactly one finite zero and seven deliberate `-inf` sentinels. Softmax is therefore exactly one on the
   registered edge and exactly zero everywhere else. The head transports that pair's value channel.
3. **Readout.** A frozen `12 * I` unembedding maps the transported value vector to logits. There is
   no MLP, residual bypass, bias, or alternate output path.

The complete registered graph is the predecessor edge, current-value-to-pair edge, the single
query-to-matched-pair edge, pair-value transport edge, and identity readout. The implementation must
raise unless every row has exactly one match. Tests must show that all seven nonmatching attention
weights are exactly zero, removing the registered matched edge destroys the target effect, and no
unregistered path reaches the readout.

This is deliberately a technical skyline model rather than a claim about naturally learned
transformers. It is preferable to expanding the opened GPT-2 head set because completeness is true
by construction instead of inferred post hoc.

## Frozen panels

- Use vocabulary size 1,024, eight key--value bindings, one final query, fixed sequence length, and
  no padding.
- Development and confirmation each have 256 rows in eight 32-row blocks.
- Panels use different seeds and disjoint key/value ID ranges, and exact prompt overlap is forbidden.
- Each row has four paired conditions and frozen role-disjoint tokens:
  - clean: queried key binds the target value;
  - corrupt: queried key binds a contrast value;
  - sham: queried key binds another non-target value;
  - matched control donor: a uniformly sampled nonmatching pair index `k`, drawn from a stage-specific
    frozen seed, changes only its value-channel one-hot at the identical pair-node site. Its token is
    disjoint from every key, target, contrast, sham, and distractor role. The donor-patch delta and
    value-channel ablation delta have the same shapes and exact L2 norms as their causal counterparts.
- The confirmation payload is generated and hash-bound before inference but is not statted, parsed,
  or hashed by the runtime until a passing development gate explicitly authorizes access.

## Interventions and estimands

For row `i`, let logits for clean, corrupt, full-output clean patch, clean circuit patch, sham circuit
patch, matched-control patch, matched-edge ablation, causal-source ablation, and control-source
ablation be respectively `z_cl`, `z_co`, `z_F`, `z_C`, `z_H`, `z_K`, `z_E`, `z_S`, and `z_A`. Define

`m_i(z) = z[target] - mean_{u != target}(z[u])`.

Let `j` be the unique queried/matched pair index and `k` the registered control pair index; every row
must satisfy `j != k`. Before cohort construction, registered pre-softmax mask scores are validated
separately as exactly one finite zero at `j` plus seven `-inf` mask sentinels. Those deliberate mask
sentinels are the only permitted nonfinite values. Any nonfinite post-softmax attention weight,
state, vocabulary logit, or derived field makes the whole stage `TECHNICAL_INVALID_STOP`; a nonfinite
row may not be filtered.
Behavioral eligibility requires `m_i(z_cl) > 6.0`, `m_i(z_co) < 0`, and
`m_i(z_cl)-m_i(z_co) > 6.0`. The closed-form clean values are approximately `12` with slack above
these floors, and a prefreeze test requires all 256 rows in each panel to satisfy them. Define
`D_i=m_i(z_F)-m_i(z_co)`. The single common gate cohort `G` is
the intersection of behaviorally eligible rows, `D_i>1e-8`, finiteness of every registered raw and
derived field, and positive centered full-vocabulary scale. No endpoint-specific filtering is
allowed.

Registered interventions are:

- full-output clean patch (Tier-A skyline);
- complete clean source-pair plus registered outgoing-edge patch into corrupt;
- corresponding sham circuit patch into corrupt;
- norm-matched noncausal source-pair patch into corrupt;
- complete matched-edge ablation from clean;
- causal pair-value-channel ablation from clean;
- matched-control pair-value-channel ablation from clean.

The intervention topology is frozen. Baseline construction first validates one and only one hard
query match. Circuit donors patch only tensor slice `[row,j,value_channel,:]`; matched controls patch
only `[row,k,value_channel,:]`, and no control tensor is written at `j`. Routing is then recomputed and
must remain one-hot because no key channel changes. Edge ablation is applied to the validated
post-routing one-hot attention row by clamping its single matched weight to zero **without
renormalization**, so transport is the finite zero vector. Source/control ablations clamp only the
post-pair-construction value channel to zero while leaving the key channel and unique routing
invariant intact. The PyTorch execution and independent oracle must agree exactly on this order.

The per-row primary metrics are

- skyline recovery: `R_F=(m(z_F)-m(z_co))/D`;
- circuit recovery: `R_C=(m(z_C)-m(z_co))/D`;
- sham recovery: `R_H=(m(z_H)-m(z_co))/D`;
- control recovery: `R_K=(m(z_K)-m(z_co))/D`;
- sham specificity: `R_C-R_H`;
- matched-control margin: `R_C-R_K`;
- matched-edge necessity: `N_E=(m(z_cl)-m(z_E))/D`;
- source necessity: `N_S=(m(z_cl)-m(z_S))/D`;
- control-source necessity: `N_K=(m(z_cl)-m(z_A))/D`;
- necessity advantage: `N_S-N_K`.

For centered logits `c(z)=z-mean_vocab(z)`, define
`B_i=RMS(c(z_cl)-c(z_co))`, full-vocabulary restoration
`V_i=1-RMS(c(z_C)-c(z_cl))/B_i`, and collateral error
`K_i=RMS_{u not in {target,contrast}}(c(z_C)-c(z_co))/B_i`. Patch-delta norm matching is
`L_i=||pair_control_donor-pair_corrupt||_2 / ||pair_clean-pair_corrupt||_2`; source-ablation norm
matching `Q_i` is the analogous ratio of control-value-channel to causal-value-channel ablation
deltas. Both ratios
must be finite and within the registered interval for **every prepared and live row**, not only `G`.

The point estimate for every endpoint is the equal-weight mean of the eight observed block means on
`G`. Intervals use 2,000 paired hierarchical bootstrap draws. Each draw samples eight blocks with
replacement; each occurrence of block `b` independently resamples its `n_b` cohort rows with
replacement, and the draw is the equal mean of the eight resampled block means. Conditions remain
paired within row. For endpoint name `e`, seed bytes are the UTF-8 encoding of
`"<base-10 global_seed>|<stage>|<e>"`; the seed is SHA-256 digest bytes `0:4` interpreted little-endian
unsigned. The 0.025 and 0.975 quantiles use NumPy's `linear` method. Point minima/maxima are inclusive;
lower/upper interval limits are strict.

## Prospective gates

Each stage requires at least 240 common-cohort rows overall and 28 per block. Inclusive point gates
and strict interval gates are frozen before model execution:

- skyline recovery: point at least 0.999999; lower bound above 0.99999;
- complete-circuit recovery: point at least 0.95; lower bound above 0.90;
- sham specificity: point at least 0.90; lower bound above 0.85;
- matched-control margin: point at least 0.90; lower bound above 0.85;
- matched-edge necessity: point at least 0.90; lower bound above 0.85;
- source necessity: point at least 0.90; lower bound above 0.85;
- necessity advantage: point at least 0.85; lower bound above 0.80;
- centered full-vocabulary restoration: point at least 0.95; lower bound above 0.90;
- collateral error ratio: point at most 0.02; upper bound below 0.05;
- patch-delta norm ratio: every row within `[0.999999, 1.000001]`.
- source-ablation norm ratio: every row within `[0.999999, 1.000001]`.

Skyline recovery is algebraically `D/D=1` and is labeled an estimator-consistency check, not an
independent restoration test. Before scoring, both live passes and the independent oracle must show
`z_F == z_cl` byte-for-byte for every row and the corresponding clean and sham output patches must
reproduce their complete donor logit vectors byte-for-byte.

Calibration includes known passing raw outputs, a selectively degraded circuit, a nonspecific sham,
a potent matched control, high collateral error, insufficient support, nonfinite values, invalid
denominators, mismatched donor-patch norm, mismatched source-ablation norm, and exact comparator
boundary cases. Calibration tests evaluator behavior; it does not
replace live-model positive control.

## Lifecycle and decision rule

1. Create a v2 preservation manifest that hash-binds the v2 plan, code, config, tests, all unsealed
   prepared data, frozen reviews, provenance, results, and post-result claim review. The sealed v2
   confirmation payload is represented **only** by the path/size/digest already recorded in v2's
   immutable freeze plus the signed `CONFIRMATION_BLOCKED` record; the preservation builder and
   verifier must not stat, glob, open, or rehash that path. Verify the manifest before freeze and
   launch, including an access-trap test for the forbidden payload.
2. Prepare development/confirmation rows and calibration fixtures without running the model, then
   write a create-once `PROTOCOL_LOCK.json` binding this plan, config, thresholds, equations, panel
   bytes, calibration expectations, and lifecycle schema.
3. Run CPU model/evaluator smoke tests and a GPU smoke test only on separately hash-bound nonpanel
   fixtures. Neither smoke may stat/read the scientific panel paths. Any fix that changes a
   protocol-locked artifact requires a new version rather than replacement of the lock.
4. Obtain a candidate `/adversarial` SHIP review, freeze the exact candidate inventory, obtain an
   exact frozen `/adversarial` SHIP review, and bind both reviews to the freeze.
5. Launch once in tmux on a UUID-locked free GPU. The launcher writes a manifest before any forward.
6. Run two independent exact GPU passes for development, compare all registered tensors bitwise,
   and compare each pass against a separately implemented NumPy closed-form oracle for pair states,
   one-hot attention edges, transport states, every intervention, and logits. Exact agreement is
   required before scoring; the statistical gates are secondary comparability checks.
7. If development fails, write a permanent stop and a confirmation-block artifact without touching
   the payload. If it passes, authorize payload access by its frozen hash, run confirmation once with
   the same QA, and finalize.

Development-gate publication has a locked create-once journal with `INITIALIZED`,
`DEVELOPMENT_VALIDATED`, and `CLOSED_PASS`, `CLOSED_STOP`, or `CLOSED_TECHNICAL_INVALID`. Confirmation
authorization has a separate locked create-once journal. It records `PRECHECK_JOURNALED`, performs
all lineage/gate checks without touching the payload, then records `PHASE1_PASS_NO_ACCESS`. Immediately
before the first payload filesystem call it durably transitions to `ACCESS_MAY_HAVE_OCCURRED`; only
then may it stat and hash the payload, followed by `CLOSED_AUTHORIZED`. A blocked gate closes
`CLOSED_BLOCKED_NO_ACCESS`. A crash before `ACCESS_MAY_HAVE_OCCURRED` is reconciled without payload
access; a crash at or after it seals `CONFIRMATION_AUTHORIZATION_TECHNICAL_INVALID_STOP` with
`payload_access_may_have_occurred=true` and never retries or reopens the payload.

Prospective interpretation:

- Both panels pass exact live-oracle QA and statistical gates:
  `GROUND_TRUTH_CIRCUIT_CONTROL_CONFIRMED`; the intervention/evaluator is valid on
  the constructed complete circuit, and designing a separately frozen method benchmark is justified.
- Development passes but confirmation fails: the technical construction or generalization across
  fresh generated panels is not established; no method benchmark is justified.
- Even development fails with exact QA: repair the intervention/evaluator; do not test methods.
- Any lineage, nonfinite, repeatability, GPU-mapping, or authorization failure is technical-invalid,
  not scientific evidence.

Each stage has a create-once attempt journal with states `INITIALIZED`, `REFERENCE_1_COMPLETE`,
`REFERENCE_2_COMPLETE`, `ORACLE_AND_REFERENCES_COMPARED`, `WORKER_COMPLETE_PENDING_VALIDATION`, and
one of `CLOSED` or `CLOSED_TECHNICAL_INVALID`. Child death, timeout, launcher error, or a crash after a
possible forward prohibits retry. While the original launcher PID and GPU lock remain live, a
no-forward reconciler may only validate already-complete artifacts or seal a technical-invalid
terminal; it may never rerun inference. If the launcher is killed or the host restarts, the namespace
is stranded and can only be handled by a separately versioned analysis-only recovery that records
whether confirmation access may have occurred.

## Milestones

### M1 — Paper integration and v2 preservation

- Add a narrow v2 section to `PAPER.md` and evidence-bound claims to the ledger. Bind the clean and
  sham full-residual byte identities; skyline `1.000 [1.000,1.000]`; ablation advantage
  `0.093 [0.049,0.137]`; joint recovery `0.166 [0.145,0.188]`; sham specificity
  `0.101 [0.081,0.122]`; circuit-control margin `0.084 [0.069,0.100]`; development stop; untouched
  confirmation; and method/training absence. Every number/field must be tied to an exact JSON
  pointer and evidence hash.
- Add exact `paper_selectors` to the new ledger rows and extend `scripts/verify_paper_claims.py` to
  require each rendered selector exactly once. A mutation test changing one reported v2 number must
  fail verification even when its claim marker remains.
- Prominently distinguish positive ablation advantage from insufficient recovery/specificity.
- Generate and validate the closed v2 preservation manifest.

Acceptance: paper claim verifier passes; every preserved v2 hash matches before and after all later
work.

### M2 — Configured ground-truth harness

- Add config, analytic model, panel generator, evaluator, calibration, lifecycle, and output schema.
- Add unit tests for graph completeness, intervention semantics, matched norms, all failure cases,
  common-cohort bootstrap, panel separation, confirmation firewall, and no-training/no-method scope.
- Tests also require generated integer-row input only, `natural_prompt_assay=false` in immutable
  runtime/final artifacts, and the absence of tokenizer/corpus/pretrained-checkpoint paths.

Acceptance: targeted tests pass on CPU; deterministic smoke output passes; source contains no
optimizer/backward/training or representation-method execution path.

### M3 — Adversarial candidate and exact freeze

- Run candidate preflight and `/adversarial` review.
- Fix every blocker/revision, rerun checks, freeze the exact inventory, and perform an exact frozen
  `/adversarial` review.
- Bind review hashes to the freeze.

Acceptance: both recorded reviews begin `VERDICT: SHIP`; the review binding and freeze inventory
validate exactly.

### M4 — One-shot tmux launch

- Select and lock a free physical GPU by UUID.
- Launch the frozen study once in tmux and return after recording a live/clean-terminal handoff.

Acceptance: launch manifest records PID, GPU UUID, config/freeze/review hashes, no training, and no
methods; tmux is live or has already produced a clean immutable terminal. Do not wait for scientific
results.

## Definition of done

- [ ] Canonical-induction v2 hashes are unchanged and confirmation remains blocked/unopened.
- [ ] `PAPER.md` contains the requested narrow statement and the ablation/recovery distinction, backed
   by exact claim-ledger evidence.
- [ ] The constructed model has a finite, explicitly enumerated complete causal graph with no output
   bypass and no learned parameters.
- [ ] Development and confirmation panels are fresh, disjoint, block-structured, immutable, and subject
   to a confirmation access firewall.
- [ ] Necessity, sufficiency, sham, matched controls, skyline normalization, full-vocabulary recovery,
   collateral error, and exact delta-norm matching are all registered and tested.
- [ ] Calibration and tests reject degraded, nonspecific, unmatched, unsupported, nonfinite, and
   high-collateral cases.
- [ ] Candidate and frozen `/adversarial` reviews both say `SHIP` and are hash-bound.
- [ ] The study is launched once in tmux on a free UUID-locked GPU; no method is evaluated and no model
   is trained.

## Risks & one-way doors

- **Tautological positive control.** The skyline model is intentionally constructed to pass, so the
  claim is limited to an end-to-end positive control in this constructed system. It cannot
  distinguish GPT-2 circuit incompleteness, hook/site mismatch, task mismatch, or model mismatch.
- **Circuit patch collapses into output patch.** The primary circuit intervention patches the
  upstream pair node and registered edge, then recomputes transport/readout. The downstream full
  output patch remains a separate Tier-A identity skyline.
- **Unmatched controls.** Control donors change an identically shaped pair node by exactly the same
  one-hot L2 norm; a hard per-row norm-ratio gate prevents potency comparisons against zero-size
  controls.
- **Metric cherry-picking.** All potency, specificity, necessity, full-vocabulary, and collateral
  endpoints are jointly gated prospectively on both panels.
- **Confirmation leakage.** Runtime access to the confirmation path is guarded until development
  authorization; tests monkeypatch file APIs to detect premature stat/read/hash.
- **Overclaiming.** The final schema states `single_constructed_model=true`,
  `representation_methods_evaluated=false`, `training_performed=false`, and
  `general_natural_model_claim=false`.
- **GPU race or wrong device.** The launcher uses physical UUID evidence, a UUID-specific `flock`, a
  post-lock recheck, and `CUDA_VISIBLE_DEVICES`/runtime UUID validation.

- **Irreversible panel opening.** Opening either scientific panel is a one-way door. Development is
  opened only after freeze/review binding; confirmation is opened only after the durable
  authorization transition described above. Scientific result namespaces and lifecycle terminals
  are create-once and never reused.

## Verification plan

- `python scripts/verify_paper_claims.py`
- `python -m pytest -q tests/test_constructed_copy_circuit_v1.py`
- `python -m py_compile scripts/constructed_copy_circuit_v1.py`
- `bash -n scripts/launch_constructed_copy_circuit_v1_tmux.sh`
- candidate preflight/calibration/smoke commands defined by the new runner
- `/adversarial PLAN_CONSTRUCTED_COPY_CIRCUIT_V1.md`
- `/adversarial` on the exact candidate and exact frozen inventory
- prelaunch v2 preservation, freeze, review-binding, namespace-absence, and GPU guards
