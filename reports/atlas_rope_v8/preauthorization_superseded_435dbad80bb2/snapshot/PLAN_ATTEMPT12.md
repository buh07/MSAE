# Atlas v3.8 Attempt 12 — analysis-only recovery of Attempt 11 caches

## Goal

Run a single, explicitly exploratory, analysis-only successor that imports the signed Attempt-11 technical validation, EWT/GUM activation caches, numerical-QA bridges, and frozen Atlas v3.3 scientific contract by exact hash; executes the unchanged ridge analysis on the originally pinned physical GPU 0; writes only to a new Attempt-12 namespace; and produces the same endpoint-specific technical-eligibility overlay intended by Attempt 11.

## Non-goals

- Do not remove, edit, resume, relaunch, or reinterpret Attempt 11. Its signed terminal remains the formal outcome, and its failed staging directory remains untouched.
- Do not perform any model forward, activation extraction, fresh-panel validation, neural training, checkpointing, optimizer work, threshold calibration, or scientific protocol change.
- Do not change scientific rows, labels, sources, estimators, ridge alphas, thresholds, interventions, projections, bootstrap rules, organizations, or decision logic.
- Do not make a confirmatory claim or authorize neural training. EWT and GUM are reused/opened exploratory sources.
- Do not use the recovered outcome to silently promote an architecture. A separate post-result claim review must scope any nomination.

## Fixed history and inputs

- Attempt 11 remains terminal at `pilot_runs/20260803_atlas_rope_technical_v7/TERMINAL.json`, SHA-256 `ad7fd3b4de265879737774df38220956a4947298f3122f37b207c2bea46285d1`, with `no_retry_authorized=true`.
- Attempt-11 science authorization is `configs/atlas_rope_v7/SCIENCE_AUTHORIZATION.json`, SHA-256 `e2a0eb1650e61ea0bb74645e55ce3e01681ac07da78024cfab9ba4b8161305b4`.
- The prospective validation completions are imported without rerunning them:
  - English CHILDES+CTeTex: `bf5b79715655bb5b32e26ba6918f25568464288103d95f35bf3c538033fab0bf`.
  - Czech PDT: `b226437653617a1c0df5be6acb2fadac33b12da450f9e32c6fd76f230b1dbce4`.
- Attempt-11 EWT/GUM `COMPLETE.json`, activation arrays, row-ID files, and QA envelopes are imported by an exact path/hash/byte inventory frozen before analysis. Their signed payloads, row identities, shapes, dtypes, finite values, canonical array hashes, prepared-manifest binding, science-authorization binding, and extraction runtime attestations must all verify.
- The frozen adapter is `configs/atlas_rope_v6/science_adapter.json`, SHA-256 `c1bd69b44b84ffb250d8e50df12534657307a0b9135c904cb1ad041526a10ef0`. It pins ridge device `cuda:0` to physical GPU UUID `GPU-ec526219-fb07-e57e-a30d-5d2ab843fb15`.
- Cache extraction occurred on physical GPU UUID `GPU-9b529a09-92a6-caea-fee2-6b2bf07b0e4e` (physical GPU 1). Analysis occurs on physical GPU UUID `GPU-ec526219-fb07-e57e-a30d-5d2ab843fb15` (physical GPU 0). These are distinct frozen roles, not an amendment.

## Approach

### A. New isolated successor

Use new namespaces only:

- config: `configs/atlas_rope_v8/`;
- run/provenance: `pilot_runs/20260803_atlas_rope_analysis_recovery_v8/`;
- result: `results/atlas_rope_v8_attempt12_analysis_recovery/`;
- tmux: `atlas_rope_v8_attempt12_20260803`.

Attempt 12 verifies Attempt 11 as an immutable imported terminal experiment. It never calls an Attempt-11 controller stage, never writes below Attempt-11 run/config/result roots, and never removes the pre-existing failed Attempt-11 staging directory.

### B. Frozen recovery contract and lineage

Create a static recovery config that records:

- exploratory claim class and `reuse_decision_frozen_before_outcome=true`;
- exact extraction and analysis GPU roles;
- exact imported file inventory for Attempt-11 terminal, validation, cache, QA, adapter, scientific configs, frozen analyzer code, and all EWT/GUM prepared scientific rows opened by the analyzer;
- forbidden operations and protocol fields;
- new run/result namespaces;
- zero authorization for model forwards, extraction, fresh validation, neural training, outcome-conditioned config changes, or retry.

Create an implementation candidate binding the config, recovery runner, launch/pipeline scripts, frozen runtime dependencies, imported inventory, verification report, absence of the new result/run namespace, and a static no-model/no-training audit. This is preparation, not an experimental run.

### C. Hard preflight before authorization

Under exactly `CUDA_VISIBLE_DEVICES=0`, create one signed preflight artifact before authorization. Before any scoring it must verify:

1. physical GPU index 0 has UUID `GPU-ec526219-fb07-e57e-a30d-5d2ab843fb15` according to `nvidia-smi`;
2. the process sees exactly one CUDA device, visible `cuda:0` resolves to that UUID, and the frozen adapter pins the same device/UUID;
3. imported extraction attestations resolve to GPU-1 UUID `GPU-9b529a09-92a6-caea-fee2-6b2bf07b0e4e`;
4. every terminal, validation, cache, QA, adapter, analyzer, config, manifest, and prepared-source hash/size matches the frozen inventory;
5. all signed envelopes verify against the frozen signer, both validation gates pass, cache row IDs and arrays match the prepared source bundles, arrays are finite float32 with width 768, and canonical hashes match;
6. the Attempt-12 result namespace, authorization, start marker, and terminal are absent;
7. no Attempt-11 path is writable by the recovery code, no model-forward/extraction/validation/training CLI exists, and the reviewed implementation inventory is unchanged.

The preflight writes only the new Attempt-12 signed provenance artifact and explicitly records `scientific_scoring_performed=false`, `model_forward_performed=false`, and `neural_training_run=false`.

After preflight, create a recovery freeze candidate binding its hash and the implementation candidate. Obtain `/adversarial SHIP` on the exact freeze candidate and its code inventory before authorization.

### D. One-shot authorization and analysis

Authorization is create-once and requires:

- an exact-SHA `SHIP` review of the recovery freeze candidate;
- unchanged preflight, config, implementation, and imported inventories;
- a fresh live GPU mapping check;
- absent result/start/terminal namespaces;
- explicit `analysis_attempts=1`, `exploratory=true`, `model_forward_authorized=false`, `fresh_validation_authorized=false`, `activation_extraction_authorized=false`, `neural_training_authorized=false`, and `retry_authorized=false`.

The analysis runner creates a signed, create-once `STARTED.json`, repeats the complete hash and GPU preflight, then lazily loads the byte-frozen analyzer. It supplies the same effective context that Attempt 11 intended:

- unchanged frozen scoring/prescore/prepared manifest;
- unchanged adapter `frozen_analysis_settings`;
- Attempt-11 science cache root;
- verified cache and QA callbacks;
- unchanged `frozen.run(FROZEN_ADAPTER)` ridge analysis on visible `cuda:0`/physical GPU 0.

The wrapper writes the returned frozen result verbatim, creates the existing Attempt-11 endpoint-specific overlay from the imported passed panels, and adds only an Attempt-12 exploratory report/lineage/completion envelope. The frozen result is non-promotable by itself. The runner never changes the analyzer settings or recomputes eligibility after dropping an endpoint.

The new result directory is atomically promoted once. Success or failure creates a signed Attempt-12 terminal with `no_retry_authorized=true`. Any failure after `STARTED.json` permanently closes Attempt 12.

### E. Post-result claim review

After a complete recovered result exists, run the independent `research-claim-review` skill. The review must distinguish:

- what the passed fresh technical validation supports;
- what the reused/opened EWT/GUM atlas measures only exploratorily;
- whether any organization is merely nominated versus scientifically established;
- whether simpler projection, position/context, token-local/context-dependent, relational-syntax, or private/private/shared work is justified;
- what requires a fresh confirmatory scientific dataset before training.

## Alternative considered

Running the existing Attempt-11 `analyze` stage with `CUDA_VISIBLE_DEVICES=0` is simpler, but it would violate the signed no-retry terminal and write under the old namespace. Re-extracting EWT/GUM on GPU 0 is unnecessary, would introduce new model inference, and would confound recovery with a cache change. A new scientific protocol is also unnecessary because the failure occurred before source loading/scoring. Therefore the narrow hash-bound, analysis-only successor is the least invasive valid recovery.

## Milestones

### M1 — Plan and independent review

- [ ] Verify the grounded Attempt-11 paths, terminal, cache inventory, GPU UUIDs, and frozen analyzer entry point.
- [ ] Obtain `/adversarial SHIP` of this plan; revise until SHIP.

Acceptance: no Attempt-12 config/code/run/result artifact exists before plan SHIP except this plan.

### M2 — Config, implementation, and tests

- [ ] Add the Attempt-12 frozen recovery config and exact import/source inventory.
- [ ] Add recovery controller, analysis wrapper, pipeline/tmux launcher, and focused tests.
- [ ] Test immutable Attempt-11 preservation, hash/signature verification, cache/source row alignment, static forbidden-path/operation audit, GPU mapping failure cases, absent result enforcement, authorization/review binding, one-shot start/terminal behavior, output isolation, overlay identity, and unchanged analyzer invocation.
- [ ] Run the full relevant test suite and static/shell checks; write a machine-readable PASS report.

Acceptance: implementation tests pass; no model forward, scientific scoring, authorization, start marker, terminal, or result exists.

### M3 — Signed preflight and exact code review

- [ ] Create the implementation candidate.
- [ ] Run signed preflight on physical GPU 0 without scoring.
- [ ] Create the exact recovery freeze candidate.
- [ ] Run `/adversarial` against the freeze candidate and bound code; fix every blocker/revision and repeat preflight/candidate preparation only before authorization.

Acceptance: final verdict is SHIP and cites the exact freeze-candidate SHA; Attempt-12 result/start/authorization/terminal remain absent.

### M4 — One-shot exploratory recovery

- [ ] Sign create-once authorization.
- [ ] Launch the analysis-only pipeline on physical GPU 0.
- [ ] Monitor it to a signed terminal; do not retry on failure.
- [ ] Verify the new result allowlist, signatures, hashes, lineage, overlay, report, and unchanged Attempt-11 terminal/tree.

Acceptance: either one signed complete result plus signed success terminal, or one signed failure terminal; never a retry or old-namespace mutation.

### M5 — Claim review and research recommendation

- [ ] Run independent post-result claim review.
- [ ] Report the formal status, scoped findings, limitations, and next research decision without authorizing training.

Acceptance: claim verdict is recorded and conclusions do not exceed the exploratory evidence.

## Definition of done

- [ ] Attempt-11 terminal SHA remains `ad7fd3b4de265879737774df38220956a4947298f3122f37b207c2bea46285d1`, and no Attempt-11 file is changed, removed, resumed, or relaunched.
- [ ] Attempt 12 has new config/run/result/session namespaces and is explicitly exploratory.
- [ ] Exact hashes bind the imported validation, activation arrays, row IDs, cache completions, QA artifacts, adapter, frozen code/config, prepared manifest, and every EWT/GUM prepared scientific child used in analysis.
- [ ] Preflight occurs before authorization and proves physical/visible GPU mapping, GPU-role separation, signatures/hashes, cache/source alignment, result absence, and absence of forbidden execution paths.
- [ ] An exact-candidate `/adversarial` review returns SHIP before authorization.
- [ ] The only outcome-bearing computation is the unchanged frozen ridge analysis on physical GPU 0 using existing Attempt-11 caches; no model forward, extraction, validation, or neural training occurs.
- [ ] Output is create-once and isolated to the Attempt-12 namespace, with signed start, completion/failure terminal, and `no_retry_authorized=true`.
- [ ] The recovered frozen result is preserved verbatim, and the technical-eligibility overlay is generated from the exact passed Attempt-11 validation artifacts without changing decision logic.
- [ ] Relevant tests/static checks pass, provenance captures environment/seed/hardware/data hashes, and a post-result claim review scopes interpretation.
- [ ] No new neural training is started or authorized.

## Risks and one-way doors

- **One-shot start:** signing `STARTED.json` permanently consumes Attempt 12. Mitigation: full preflight, tests, and SHIP review before authorization/start.
- **Outcome leakage:** EWT/GUM were opened and caches exist. Mitigation: freeze cache reuse and all analysis semantics before the result; label the recovery exploratory; require fresh scientific data for confirmation.
- **GPU aliasing:** `cuda:0` changes meaning under visibility masks. Mitigation: verify physical GPU 0 via `nvidia-smi`, require `CUDA_VISIBLE_DEVICES=0`, require one visible device, and compare the visible UUID to the adapter before scoring.
- **Partial result:** a process failure after start could leave staging. Mitigation: deterministic isolated staging, atomic promotion, signed terminal on trap, and no retry.
- **Accidental old-namespace mutation:** reuse callbacks point at Attempt-11 caches. Mitigation: read-only open patterns, exact write-root allowlist, before/after Attempt-11 tree inventory, and no call to Attempt-11 controller stages.
- **Protocol drift through wrapper monkeypatching:** callbacks are necessary to import external caches. Mitigation: bind exact frozen function/code hashes, constrain patches to config/cache/QA loading, assert the effective analysis settings equal the adapter byte-for-byte, and restore patched functions in `finally`.

## Verification plan

- `python -m pytest -q tests/test_atlas_rope_v8.py tests/test_atlas_rope_v7.py`.
- `python -m pytest -q` for the full project suite.
- `python -m py_compile` on all Attempt-12 Python files and frozen analyzer dependencies.
- `bash -n` on the Attempt-12 pipeline and tmux launcher.
- machine-readable candidate/preflight verification commands that hash every imported artifact and source child.
- `nvidia-smi --query-gpu=index,uuid` plus a `CUDA_VISIBLE_DEVICES=0` Torch UUID/device-count preflight.
- static AST/shell audit for model-loading/forward, extraction, validation execution, optimizer/backpropagation, training, old-namespace writes, and non-analysis CLI stages.
- post-run verifier for signed completion, exact result allowlist, imported lineage, overlay equality, new-namespace isolation, and unchanged Attempt-11 terminal/tree.
- independent `/adversarial` review before authorization and `research-claim-review` after result creation.
