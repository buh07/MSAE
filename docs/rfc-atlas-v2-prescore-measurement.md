# RFC: Atlas v2 prescore measurement protocol

**Status:** implementation plan; not frozen; no scoring authorized  
**Date:** 2026-08-02  
**Scope:** label-only/static feasibility, measurement contracts, and unit-tested analysis utilities  
**Supersedes:** nothing. Atlas completion v1 remains immutable historical evidence.

## Goal

Build a new, additive prescore measurement layer that detects document/class-support failures before any neural scoring, represents endpoint missingness without erasing finite results, and makes numerical replay independent of mixed CPU/GPU reduction paths. Use it to produce a public, label-only audit of the existing calibration and confirmation rows. Do not rerun, relax, or amend the frozen completion.

The work must make an under-supported source or task impossible to promote into a v2 confirmation merely because it has many balanced token rows.

## Non-goals

- No model inference, training, hyperparameter sweep, representation extraction, or GPU job.
- No reinterpretation or promotion of the frozen completion-v1 outcome.
- No access to or inspection of the existing blind-final labels or rows.
- No selection of a replacement confirmation dataset by looking at neural results.
- No K2/K3 trainer change. Modeling options remain blocked on a valid measurement gate.
- No claim that a support-preserving bootstrap creates independent information when there are too few real documents.

## Constraints and preserved invariants

1. Existing `data/atlas_completion_v1`, `configs/atlas_completion`, the files bound by `configs/atlas_completion/freeze_record.json`, and result artifacts are read-only inputs. New work uses v2-named paths.
2. The existing blind final remains locked. It may enter v2 only through a label-blind support attestation prepared without exposing its labels or examples to the analysis team. If it cannot be attested, the protocol requires retirement unopened and a newly preregistered final dataset.
3. Scientific invalidity blocks decision promotion; it does not fabricate `0/500` values for otherwise finite endpoint diagnostics.
4. All thresholds, role assignments, and eligibility logic are fixed in a machine-readable draft before a replacement source is accepted or any representations are scored.
5. The public audit may read only already-public/materialized calibration and confirmation task rows and labels. Inputs are an exact path-and-SHA-256 allowlist; arbitrary manifests are not accepted. A central pre-open resolver canonicalizes every path, requires a regular non-symlink file under an allowed canonical root, and rejects traversal, aliases, special files, and any resolved `final`, `private`, `blind`, or unlock-material component. Output is similarly contained in one new v2 report root. Refusal occurs before opening any row file.

### Public input adapters

The static audit has two explicit, separately digest-bound adapters:

- **Tier 1:** `data/atlas_v1/analysis_rows/{role}.{task}.jsonl`, with digests copied from `configs/atlas/task_row_manifest.json`. These rows do not have a `source` field. Source is assigned only by the exact frozen `document_group` prefix map below; an unmatched or multiply matched prefix is an error.
- **Tier 2:** `data/atlas_completion_v1/{role}.{task}.jsonl`, with digests copied from `configs/atlas_completion/freeze_record.json`. These rows must have a `source` field, and their group prefix must agree with the same exact map.

The permitted roles are exactly `calibration`, `C1`, and `C2`. The frozen prefix map is:

| Role | Document-group prefix | Source |
|---|---|---|
| calibration | `UD_English-GUM:` | `UD_English-GUM` |
| calibration | `flaitenberger/wnut_17:` | `flaitenberger/wnut_17` |
| C1/C2 | `UD_English-LinES:` | `UD_English-LinES` |
| C1/C2 | `Babelscape/wikineural:` | `Babelscape/wikineural` |

The adapter never joins against partitions, examples, transforms, or any blind manifest.

## Design grounding

The project design ledger has no canonical entry for this v2 protocol. The requirements below therefore come from the requested measurement redesign and are made explicit rather than inferred from the v1 implementation.

Static code inspection establishes the failure mechanisms the design must prevent:

- `build_atlas_task_rows.py` and `build_msae_completion_rows.py` balance token rows per label without enforcing independent-document support.
- `calibrate_msae_completion.py` requires every fixed-probe sentinel to have an ordinary retention denominator, even though `source_type` is deterministic at the source level within source-stratified scoring.
- `run_msae_stability.py` requires all families to be present in one draw, turning structurally ineligible families into total-vector invalidity.
- `run_k2_functional_audit.py` pools live Torch/GPU values while `run_msae_specificity.py` may pool transferred/cached arrays in NumPy and, for position shifts, may compare float16-cached values with live values.

## Proposed contract

### 1. Prescore support gate

For every ordinary retention/localization `(dataset role, source, task)` triple before representation scoring:

- at least **25 genuine document groups** overall;
- at least **20 distinct document groups containing each retained class**;
- no more than **256 selected task rows per document group**;
- label-only ordinary hierarchical-bootstrap completeness at least **490/500** frozen maps;
- at least **two measurable, non-nested operationalizations per scientific family**.

These are draft v2 thresholds, deliberately stricter than the old ten-group preflight. They are protocol constants, not values tuned to make an existing source pass.

Pooled nuisance tasks are the explicit exception to the per-source all-class rule. For `source_type`, each source must separately provide at least 25 groups and satisfy the 256-row contribution cap, while the pooled task must contain at least two labels with at least 20 groups per label. A source is not required to contain the other source's deterministic label. Its pooled ordinary-bootstrap maps retain the fixed number of groups from every source stratum, so support is evaluated on the pooled resample. No other task receives this exception.

The audit reports row count, total group count, per-class group counts, maximum group contribution, ordinary-bootstrap finite coverage, and every failed rule. Token balance never substitutes for group support.

`UD_English-LinES` is retired as the v2 confirmation source because four or five real document clusters cannot support confirmation inference. Its replacement remains unspecified until a label-only candidate manifest passes this gate. The software must fail closed while the replacement is unset.

#### Exact bootstrap contract

The primary coverage audit is ordinary, unconditional, source-stratified document resampling:

1. Apply the frozen label map/vocabulary, then the deterministic per-document cap, then recompute support. No post-bootstrap label removal is permitted.
2. Within a `(role, task)`, sort sources and each source's unique document-group IDs by UTF-8 byte order. A source with `n` groups contributes exactly `n` sampled group slots with replacement per draw.
3. Use exactly 500 draws numbered `0..499` and master seed `20260802`. For slot `j`, compute SHA-256 over the UTF-8 string `atlas_measurement_v2|20260802|{role}|{task}|{source}|{draw}|{j}`. Interpret the first eight digest bytes as an unsigned big-endian integer and take modulo `n` as the sampled group index. This defines map order without a library RNG.
4. A source-stratum draw is finite only if every retained class that occurs in that source before resampling occurs in at least one sampled group. A task draw is finite only if every applicable source stratum is finite. Nuisance sentinels use their separately specified pooled/non-introduction metric and do not acquire a retention denominator from this predicate.
5. Primary coverage is the number of finite task draws. A task is bootstrap-complete at `>=490/500`; exactly 489 is ineligible. Hard group/class/contribution rules are evaluated first and cannot be rescued by high bootstrap coverage.

The optional support-preserving diagnostic never redraws. It reports which of these same 500 ordinary maps satisfy coverage, so its rejection rate is exactly `1 - finite_draws/500`. A rejection rate above 10% is ineligible; an implementation that samples until acceptance is forbidden. Synthetic reference fixtures freeze the rare-class omission behavior.

### 2. Row/task rebuilding contract

- Token and lemma identity candidates require at least 20 groups in **every applicable source**. Rank retained candidates by `(minimum source document frequency descending, total document frequency descending, UTF-8 label ascending)` and keep at most 256. No feasible vocabulary or fewer than two labels makes the task ineligible; there is no unknown/other bucket.
- The only v2 absolute-bin map is fixed: original 16-way bins map as `0,1→0; 2,3→1; 4,5→2; 6,7→3; 8,9→4; 10,11→5; 12,13,14,15→6`. It is one `absolute_bucket` operationalization. A separate `controlled_position_shift` task, not another rebinning, is required for two-operation family evidence. If the fixed tail bin still lacks support, the bucket task is ineligible rather than remerged.
- UPOS has the fixed optional coarse map `NOMINAL={NOUN,PROPN,PRON}`, `VERBAL={VERB,AUX}`, `MODIFIER={ADJ,ADV}`, `FUNCTION={ADP,CCONJ,SCONJ,DET,PART}`, `QUANTITY={NUM}`, `PUNCT={PUNCT}`, `OTHER={INTJ,SYM,X}`. Dependency relations have the fixed optional map `CORE={nsubj,csubj,obj,iobj}`, `CLAUSAL_COMPLEMENT={ccomp,xcomp}`, `OBLIQUE={obl,vocative,expl,dislocated}`, `NOMINAL={nmod,appos,nummod,acl,amod,det,clf,case}`, `ADVERBIAL={advcl,advmod,discourse}`, `COORD={conj,cc}`, `FUNCTION={aux,cop,mark}`, `MWE={fixed,flat,compound,list}`, `REPAIR_OTHER={parataxis,orphan,goeswith,reparandum,dep}`, plus separate `root` and `punct`; subtype suffixes are stripped before mapping. Capitalization maps `lower→lower`, `title→title`, `upper,mixed→other`, and `nonalpha→nonalpha`; nonalphabetic tokens remain a distinct control rather than being conflated with unusual casing. Unknown input labels are errors, not silently dropped. Whether a task uses its raw or this coarse label set is fixed in the v2 config before candidate audit.
- An applicable source is one explicitly listed for the task in the v2 source/task manifest; row presence alone cannot create applicability. A required source with no rows makes the task ineligible.
- Within each document group, rows are partitioned by mapped label, ordered by SHA-256 of `atlas_measurement_v2|row-cap|{row_id}`, and selected in UTF-8-label round-robin passes until 256 rows or exhaustion. This preserves at least one row for every label present in the group when the number of labels is at most 256. Duplicate row IDs are errors. Any later per-class limit also round-robins over sorted groups before taking a second row from a group.
- Family evidence uses the frozen construct IDs: `absolute_bucket` and `controlled_position_shift`; `identity` (token/lemma jointly count once) and `entity_substitution`; `token_relative`, `dependency_relation`, and `head_token_contrast`. A family is measurable only when at least two distinct required construct IDs pass in every applicable source. Nested tasks never count twice.

Every audit input declares `required_for_task_measurability`. For the historical-to-v2 projection, required Tier-1 representatives are `abs_pos_16` (after the v2 map), `token_identity_256`, `relative_quartile`, and `head_signed_distance`; all Tier-2 sentinel files are required. `abs_pos_8`, lemma identity, boundary state, dependency depth, and NER label prediction remain visible diagnostics but do not independently block the task-measurability endpoint. The missing controlled-shift and entity-substitution constructs still block their families through family readiness, rather than by treating a legacy nested task as required evidence.

Support-preserving resampling is optional and secondary. If later enabled, the protocol freezes a maximum rejection rate of **10%**. Ordinary unconditional coverage below the completeness threshold makes the task ineligible; the implementation must not repeatedly reject maps until a favorable sample appears.

### 3. Sentinel roles

Sentinels have explicit roles:

- **retention:** raw signal must be measurable and the representation must preserve a prespecified fraction;
- **nuisance/non-introduction:** low raw decodability is allowed or desirable; representation scoring asks only whether the shortcut was introduced or amplified.

`source_type` is fixed as `nuisance/non-introduction`. It cannot invalidate a baseline merely because a normalized retention denominator is undefined inside source strata. Configuration validation rejects an attempt to classify it as an ordinary retention sentinel.

For `source_type` only, raw and representation probes are pooled across the explicitly applicable sources and use the same document-group maps. Both source labels must have at least 20 groups. The reported estimand is the unnormalized paired macro-F1 difference `representation - raw`; there is no division by raw performance. Non-introduction passes when the upper endpoint of the prespecified paired 95% bootstrap interval is at most `+0.02` macro-F1. Low or chance raw decodability is not a measurability failure. Other retention sentinels continue to require a finite raw denominator and their separately preregistered retention threshold.

### 4. Endpoint-specific validity

Every draw/result has independent statuses for:

1. task measurability;
2. family localization;
3. family stability;
4. collateral validity;
5. counterfactual validity;
6. overall decision eligibility.

Each status is one of `eligible`, `ineligible`, or `not_run` and includes machine-readable reasons. Family and task values remain reportable when finite. Overall decision eligibility is a conjunction over preregistered required endpoints, but its failure must not overwrite finite subordinate measurements.

Aggregation is deterministic:

| Inputs for a required aggregate | Aggregate status |
|---|---|
| any `ineligible` | `ineligible` |
| otherwise, any `not_run` | `not_run` |
| all `eligible` | `eligible` |
| empty required set | `ineligible` (`no_required_endpoints`) |

A task that fails prescore support is `ineligible`, whether or not an old finite score exists; the old score remains in a separate `observed_value` field and is not promoted. An authorized, prescore-eligible task without a computed score is `not_run`. A family first applies the table to every required task/construct, then additionally requires two distinct eligible construct IDs; otherwise it is `ineligible`. The overall decision applies the table only to endpoints marked `required_for_decision`. Optional endpoint status never changes the overall status. These rules are covered by mixed finite/missing reference fixtures.

Execution authorization is separate from decision promotion. Already-authorized diagnostics may run and be reported even when an architecture decision is forced equivocal; promotion remains fail-closed.

### 5. Specificity cache and replay

The v2 utility contract creates one float32 array file per `(transform, checkpoint)` with a first axis aligned to an ordered row-ID sidecar; token matrices have explicit per-row lengths/offsets. It derives parent, actual, sham, and control statistics from that same cache and one canonical pooling function.

- Cache lineage is validated using schema version, checkpoint/transform identifiers, ordered row IDs, shapes, dtypes, and SHA-256 hashes.
- An **exact cached no-op replay** validates identity/lineage.
- A **numerical reproducibility check** compares repeated calibration-only inference and produces separate technical-QA metrics using preregistered `atol + rtol * |reference|` bounds.
- A **scientific sham/inactive intervention** is evaluated independently; it is not treated as a floating-point replay test.
- Tolerances remain unset in the protocol draft until repeated calibration-only inference is authorized and run. The scoring code must refuse to freeze a tolerance inferred from confirmation/final results.

Random scientific controls should be covariance-shaped or sampled from matched natural deltas. A sentence-mean ambient-space direction added to every token is not accepted as the sole random control.

### 6. Stability reporting

The utility layer must support, without requiring every family to be finite at once:

- task-level and family-level linear CKA;
- the full branch matrix (`pos↔pos`, `content↔content`, and cross-branch cells);
- a branch-identity margin defined as the same-assignment mean minus the best swapped-assignment mean;
- CKA over counterfactual deltas;
- residual/conditional CKA after projecting out prespecified nuisance covariates;
- explicit missingness rather than numerical zeros.

Linear CKA for aligned real matrices `X,Y` with the same `n>=2` rows is
`||XcᵀYc||F² / sqrt(||XcᵀXc||F² ||YcᵀYc||F²)`, where each feature column is centered over rows. Non-finite input, row misalignment, fewer than two rows, or either zero Frobenius denominator returns an explicit undefined reason, never zero. The K2 branch matrix applies this formula to every left/right branch pair. The branch-identity margin is `mean(pos↔pos, content↔content) - mean(pos↔content, content↔pos)` and is undefined if any required cell is undefined.

Residual CKA takes a finite, prespecified numeric nuisance matrix `Z`, adds an intercept, and uses `numpy.linalg.lstsq(..., rcond=None)` separately for every column of `X` and `Y`; CKA is applied to the residuals. Categorical nuisance columns must be one-hot encoded by the frozen caller with one reference level dropped. Row IDs must align exactly, `n` must exceed `matrix_rank([1,Z]) + 1`, and degeneracy follows the same undefined rule. Delta CKA uses the same estimator on aligned `post - pre` matrices.

Feature matching, active-set overlap, and stability of recovery/leakage/selectivity are specified for a later scored implementation. They are documented now but are not computed in this no-experiment change.

Family CKA is an equal-weight macro mean of preregistered representative task CKAs, never a concatenation of rows from different tasks. One representative task is frozen per construct ID; nested variants cannot increase its weight. The primary `complete_value` (and each complete family branch-matrix cell) is defined only when every required representative task is finite and row-aligned within that task. A separate descriptive `available_task_mean` averages only finite representatives and always reports `tasks_available/tasks_required`; it may be shown when the family status is `ineligible` or `not_run`, but cannot enter promotion. Missing tasks are omitted from this descriptive mean, explicitly listed, and never imputed as zero.

### Blind-final attestation contract

The analysis code never opens a final payload. A future attestation is produced by an independent data custodian whose Ed25519 public-key fingerprint is frozen in the preregistration. The signed canonical-JSON artifact contains only: schema/protocol version, protocol-config SHA-256, sealed dataset-bundle SHA-256, grouping-code SHA-256, role/source/task identifiers, total group count, minimum anonymous-class group count, maximum rows per group, bootstrap finite count, eligibility boolean/reasons, creation time, producer ID, public-key fingerprint, and signature. It must contain no label names, per-class vector, row IDs, examples, tokens, or paths.

Validation checks the signature, producer/key allowlist, exact protocol/grouping/payload digests, unique task keys, permitted fields, and all gates. A missing field, extra disclosure field, signature failure, digest mismatch, source substitution, or ineligible task permanently marks that sealed final `retire_unopened`; it cannot be repaired by opening it. Cryptographic production/verification is a later custodian integration, not performed in this static audit.

Every replacement-source candidate also requires a signed public grouping-provenance manifest bound to its exact dataset revision and bundle digest. Required fields are dataset/source ID, immutable revision, bundle SHA-256, natural sampling-unit type and source field, grouping-code SHA-256, the mapping cardinality from original units to groups, a dependence rationale, builder identity, independent provenance-reviewer identity, review decision/time, and separate builder and reviewer signatures/key fingerprints. The reviewer must be distinct from the builder and attest that group IDs represent the stated natural sampling units rather than row/sentence IDs invented to pass support. Missing/inconsistent fields, digest drift, a failed review, or artificial splitting makes the candidate ineligible before row audit.

## Alternatives considered

1. **Patch and rerun completion v1.** Rejected: it would weaken a frozen protocol after seeing failures and would mix historical and new inference.
2. **Class-preserving bootstrap on the existing LinES rows.** Rejected: finiteness would be manufactured by duplicating the same four or five documents, understating uncertainty.
3. **Only loosen the `1e-6` replay threshold.** Rejected: it retains mismatched reduction paths and conflates lineage, technical reproducibility, and scientific specificity.
4. **Train more K2 seeds immediately.** Rejected: current evidence cannot distinguish stable specialization from a stable mixed solution, and the measurement gate is invalid.
5. **Immediately adopt K3.** Rejected: shared/K3, conditional, or relation-aware models require evidence from the repaired measurement study.

## Milestones

### M1 — Contracts and failing tests

- Add a v2 configuration schema/draft with thresholds, exact input paths/digests and source-prefix adapters, frozen label/family maps, sentinel roles, endpoint requirements, source replacement state, and blind-final policy.
- Add tests first for group support, class support, contribution caps, exact bootstrap fixtures, canonical path refusal, sentinel roles, and endpoint missingness.
- Acceptance: tests fail against the absent implementation for the intended reasons; no model/data job is launched.

### M2 — Pure prescore and selection utilities

- Implement deterministic, side-effect-free support auditing and group-aware selection helpers.
- Implement ordinary label-only bootstrap coverage and bounded support-preserving rejection diagnostics without using constrained draws for eligibility.
- Acceptance: synthetic tests prove that many rows from one document fail, adequate multi-document data pass, a rare class produces the frozen omission count, and Tier-1 prefix mapping is exact.

### M3 — Replay and stability utilities

- Implement canonical float32 cache serialization/validation and one pooling path.
- Implement exact no-op replay metadata, separate numerical-agreement reporting, CKA matrix, branch identity margin, residualization, and endpoint-specific status aggregation.
- Acceptance: tests cover dtype/hash/row-order tampering, scale-aware numerical bounds, cross-branch swaps, constant/undefined CKA, and partial-family reporting.

### M4 — Static public audit and protocol draft

- Run only the label/group audit over both manifest-bound Tier-1 analysis rows and Tier-2 completion rows for calibration and C1/C2.
- Emit JSON and Markdown reports under a new v2 report directory.
- Draft a prescore preregistration that records current-source retirement, replacement-source acceptance criteria, the unresolved replay tolerance, and the locked-final attestation rule.
- Acceptance: the report exposes WNUT tail/identity sparsity and LinES cluster sparsity, makes no neural claim, and contains no final/private records.

### M5 — Review and verification

- Run focused tests and static import/CLI checks.
- Verify every entry in `configs/atlas_completion/freeze_record.json` before the audit, include that freeze-record trust-root file itself in an exhaustive baseline digest inventory, and reverify every entry plus the trust root and baseline inventory after the audit.
- Run `/adversarial` against the implementation and artifacts; fix all blockers and material revisions, then rerun review.
- Acceptance: independent verdict is `SHIP`, tests pass, the exhaustive v1 hash comparison is clean, the IO inventory contains only allowlisted inputs/new v2 outputs, and no experiment process was launched.

## Definition of done

- [ ] New code is additive and v2-namespaced; frozen completion-v1 files are unchanged.
- [ ] Current public rows fail for the scientifically correct group-support reasons.
- [ ] An unset replacement confirmation source blocks v2 confirmation scoring.
- [ ] `source_type` is a nuisance sentinel and cannot demand a retention denominator.
- [ ] Endpoint missingness does not erase finite task/family values.
- [ ] Cache lineage and exact replay are hash/ID based; numerical agreement and scientific sham are distinct.
- [ ] Stability utilities report a cross-branch matrix and identity margin task by task.
- [ ] Blind-final paths are refused and the protocol records attestation-or-retire behavior.
- [ ] No training, inference, extraction, download, or blind-final access occurs.
- [ ] Targeted verification passes and final adversarial verdict is `SHIP`.

## Verification plan

Planned commands (software/static only):

```bash
./.venv-atlas/bin/python -m pytest -q tests/test_msae_measurement_v2.py
./.venv-atlas/bin/python -m py_compile scripts/msae_measurement_v2.py scripts/audit_msae_measurement_v2.py
env -u CUDA_VISIBLE_DEVICES CUDA_VISIBLE_DEVICES='' \
  HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 NO_PROXY='*' \
  ./.venv-atlas/bin/python scripts/audit_msae_measurement_v2.py \
    --config configs/atlas_measurement_v2/prescore.json
```

The command is label-only and CPU-only. The CLI has no arbitrary row-root, role, manifest, or output arguments: exact inputs, roles, SHA-256 values, and the dedicated absent-at-start `reports/atlas_measurement_v2` output root come from the reviewed v2 config. It verifies all completion freeze-record members before any row open, resolves and validates the entire input/output plan before reading rows, writes to a newly created sibling temporary directory, and atomically renames it only after success. An existing output, symlinked root/parent/file, traversal, absolute alias outside the repository, digest mismatch, or special file is a hard pre-open failure.

Safety tests monkeypatch/deny `open`, `socket.socket`, `subprocess.Popen`, and common process/network helpers to prove refusal occurs before row access and that the utility has no network/process path. Static dependency checks reject imports of Torch, Transformers, datasets, requests, subprocess, and socket. The report records ordered opened-input and created-output inventories with digests. Before/after process listings and new-file inventories under `pilot_runs`, `results`, `data`, and `configs/atlas_completion` provide evidence that no experiment artifact or job was created. These checks cannot prove facts outside the host, but they enforce and record the relevant program boundary.

## Risks and mitigations

- **Thresholds still arbitrary.** They are conservative draft constants and must remain fixed before candidate-source inspection; sensitivity may be reported later without changing primary eligibility.
- **Document IDs may not correspond to genuinely independent documents.** Candidate manifests require provenance and grouping semantics; a large count of sentence IDs is not automatically accepted as document support.
- **Coarsening can change the construct.** Mappings must be prespecified and justified per task; the audit utility never invents a mapping.
- **Bootstrap coverage can look strong with few clusters.** The hard 25-group and 20-groups-per-class rules precede and dominate coverage.
- **A shared cache can hide repeat-inference nondeterminism.** Repeated inference is retained as separate technical QA, with tolerance calibrated only on calibration data.
- **Identity margin can be high for nonselective branches.** It is reported alongside recovery, leakage, and localization rather than used alone.
- **The replacement source remains unknown.** This is intentional fail-closed behavior; selecting a corpus is a separate label-only data-design decision.
- **Modulo indexing is not perfectly uniform when group count does not divide `2^64`.** For `n` groups, each index's absolute probability error is at most `2^-64` and total-variation distance is at most `n/2^65`; this bound is recorded and accepted in exchange for a version-independent exact map. Coverage eligibility is also dominated by the hard support gates.

## One-way doors

None in this implementation. The v2 protocol remains a draft, the replacement source is unset, replay tolerance is unset, and no final data are opened. Freezing this draft later will be an explicit one-way preregistration event requiring a new review.
