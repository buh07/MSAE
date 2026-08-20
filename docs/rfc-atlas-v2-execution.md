# RFC: Atlas/MSAE measurement v2 execution

**Status:** implementation and launch plan; scoring is not yet running  
**Date:** 2026-08-02  
**Run ID:** `20260802_atlas_measurement_v2`  
**Parent:** `docs/rfc-atlas-v2-prescore-measurement.md`

## Goal

Run an additive, config-bound v2 diagnostic of the four already-trained K2 checkpoints on a
replacement confirmation corpus with genuine document support. The run must repair the three
measurement failures seen in completion v1:

1. select labels and rows by natural-document support before scoring;
2. compute functional specificity from a single float32 cache and distinguish exact replay,
   repeat-inference QA, and scientific interventions;
3. report recovery, leakage, task/family stability, the full cross-branch CKA matrix, and
   endpoint missingness independently.

The complete staged pipeline will run under one owned tmux session and fail closed. This run
evaluates frozen checkpoints; it does not train a new MSAE.

## Non-goals

- Do not modify, relax, rerun, or promote the frozen completion-v1 analysis.
- Do not open or attest the existing blind-final payload.
- Do not train K2/K3, choose a new architecture, or claim a final architecture decision.
- Do not treat geometry alone as specialization.
- Do not use artificial sentence IDs as document clusters.
- Do not score any representation until a builder-signed public grouping manifest and a separately
  keyed, independent adversarial-review signature both validate. Formal promotion additionally
  remains out of scope because the existing blind final stays locked.

## Constraints and fixed assumptions

1. The user explicitly authorized running v2 in this turn. Earlier instructions not to run an
   experiment are superseded by that authorization.
2. The design-ledger query
   `/jumbo/lisp/f004ndc/.agent-workspace/bin/design query 'What is the canonical executable
   Atlas/MSAE measurement v2 scope, replacement confirmation source, and promotion contract?'
   --path docs/rfc-atlas-v2-execution.md` returned zero matches. The assumptions below are
   therefore fixed here before neural scoring.
3. The provisional replacement public source is **UD English ESLSpok r2.18**, Git commit
   `f4d0ebe5eae0bc179a988934e15f018dcacfe73b`. Its `sent_id` values identify the source transcript
   file before the final underscore (for example `file01218.txt_144` belongs to natural group
   `file01218.txt`). The three official conllu files are combined before assigning whole transcript
   groups to roles, so an original transcript cannot cross C1/C2.
4. The public label/tokenizer-only reconnaissance found 2,320 sentences and 872 transcript groups. A
   deterministic hash-balanced whole-group split gives 436 groups in each of C1 and C2. On the
   prespecified v2 maps, relative quartile, head distance, dependency depth, UPOS, dependency
   relation, capitalization, and the 24-label cross-role identity vocabulary all pass the fixed
   gates. Disjoint document matching yields 40, 26, and 24 aligned entity-substitution pairs for
   calibration, C1, and C2, and leaves 109, 236, and 211 multi-sentence documents for document-context
   interventions. All scored task audits have 500/500 ordinary
   bootstrap coverage after the cap. A durable JSON reconnaissance artifact will bind these counts,
   exact inputs, tokenizer revision, and algorithm digest. ESLSpok becomes selected—not merely
   provisional—only after this artifact and both grouping-provenance signatures validate.
5. Discovery uses only the public UD English EWT records already materialized in Atlas v1;
   calibration uses only public UD English GUM records. Their natural `newdoc` groups are retained.
   NER sentence rows and LinES are excluded from v2 scoring.
6. The four K2 checkpoints are frozen g4/g5/g6 plus the no-incoherence g7 control already named in
   `configs/atlas_completion/analysis.json`. Every checkpoint and reused artifact is digest-bound
   in the resolved run config.
7. Inference uses `EleutherAI/pythia-160m-deduped` revision
   `582159a2dfe3e712a8d47ae83dec95ae3bde8e7e`, layer 3. New cached representations are float32
   even when model inference uses its existing CUDA fp16 execution path.
8. All formal support thresholds remain those fixed in the prescore RFC: 25 groups, 20 groups per
   retained class, 256 rows per group, and at least 490/500 finite ordinary document bootstraps.

The source-file digests frozen for M1 are:

| File | SHA-256 |
|---|---|
| `en_eslspok-ud-train.conllu` | `2d98d2a9520fbc9e20154ab0b51bb688d704c3c59b0e9ae09d82df0a4b1c6330` |
| `en_eslspok-ud-dev.conllu` | `7034c651d3deec369149139a75da31a61e673b9735ae88589695ab1d2d235000` |
| `en_eslspok-ud-test.conllu` | `7d3b37af353205dc3b2964937e7c511e7763cdca25ec9c830638a2540ffe04be` |

The checkpoint digests are g4
`00714ca209027d418156f65dda55b90e6f1887a75ef412acb43a61359d711e97`, g5
`933120800d5861dddbe99f725c04467c0684bbd069b6d9f345d2b202a43003ef`, g6
`d4cd3ac52805f70bbcec60857a3c4afd6361248038a541f63a0cfcfe1b5b3e43`, and g7
`76474c4576e024d13d6ae9a3b43f38ac51918c84db1b75121932709d5f8dbc49`.

## Experimental design

### Data and grouping

- Download only the three immutable ESLSpok conllu URLs named in the config and verify their
  SHA-256 digests before parsing.
- Parse the transcript group as the anchored regex `^(file[0-9]+\.txt)_[0-9]+$`; a malformed or
  duplicate `sent_id`, unknown label, or cross-role group is fatal. Repeated utterance text is valid
  spoken-corpus content, remains in its transcript group, and is reported by content-hash multiplicity;
  content hashes never define sampling units or deduplication.
- Combine the official train/dev/test files, then order natural groups by SHA-256 of
  `atlas-measurement-v2|C1C2|<group>` and alternate whole groups into C1 and C2.
- Deterministically retain at most two sentences per natural group for neural inference while
  keeping every group. Sentence selection is hash-based and independent of labels.
- Tokenize each original sentence with no prefix or special token and truncate at 128. A target word
  is complete only if all its subwords occur below 128; only its first subword enters probes. No
  artificial offset or global position-ID translation is used: GPT-NeoX/RoPE makes uniform absolute
  translation a symmetry, so treating it as a functional intervention would measure numerical error.
- For the broad-position/context counterfactual, choose one unused document with two sampled source
  records whose numeric `sent_id` suffixes establish original order. The hash-tie-broken smallest-gap
  ordered pair `(earlier,later)` is frozen. The source encodes `later` alone; the target encodes
  `earlier`, one literal EOS token ID `0`, then the identical `later`. Pool only exactly aligned
  complete words from `later`, and require the concatenation to fit within 128 tokens. ESLSpok is a
  sentence sample, so this is explicitly a **sampled earlier-document context anchor**, not a claim
  that the utterances were adjacent. It deliberately changes available document-matched context and
  target distance from the causal boundary; its construct is `document_context_anchor`, not isolated
  absolute position. A same-input sham uses the later-alone cache twice and must have zero distance.
- Apply the prespecified coarse maps and document-round-robin 256-row cap before the support audit.
- Retain alphabetic token-identity labels only when each label occurs in at least 20 natural groups
  in every applicable role (discovery, calibration, C1, C2), then keep at most 256 by the frozen
  document-frequency ordering. No OOV class is introduced.

### Independent operationalizations

The scored task constructs are fixed before inference:

| Family | Construct | Operationalization |
|---|---|---|
| broad structural/context position | `token_relative` | sentence-relative quartile |
| broad structural/context position | `dependency_relation` | signed head distance and coarse dependency relation |
| broad structural/context position | `document_context_anchor` | same target sentence alone versus after an earlier sampled same-document sentence plus EOS |
| lexical/content | `identity` | document-frequency-filtered token identity |
| lexical/content | `entity_substitution` | aligned, deterministic single-token PROPN substitution |

The parent draft's strict `absolute_position` construct is explicitly
`ineligible/model_architecture_symmetry` and is not replaced by a confounded attended-prefix claim.
This execution amendment therefore asks the narrower, prespecified K2-posfam question: does the
nominal pos branch preferentially encode **broad structural/context position** versus lexical
content? It cannot promote a three-family absolute/structural/content architecture decision.

Entity substitutions are constructed without neural values. Hash-order eligible documents, match
adjacent documents once without replacement, use the first as source and the second only as donor,
and discard a pair if its deterministic first eligible source/donor PROPNs are equal or fail exact
tokenizer-word alignment. No document may occur in two pairs or in the role's document-context
set. The target changes exactly one single-token PROPN; it keeps source dependency/position metadata
only as an intervention annotation and is never treated as newly parsed gold syntax. The independent
sampling unit and bootstrap group is the two-document pair component. Each calibration/C1/C2 role
requires at least 20 valid disjoint components. Document-context pairs are then selected from unused
documents with two retained sentences, at most one pair per document, and use that document as their
bootstrap group.

### Signed grouping-provenance gate

Before row audit or inference, the builder emits canonical JSON bound to the source URLs, three file
digests, Git revision, tokenizer/model revision, grouping regex/code digest, 2,320-to-872 mapping,
whole-group split digest, dependence rationale, and reconnaissance digest. It signs the payload with
an ephemeral Ed25519 builder key and stores only the public key and signature. A fresh adversarial
reviewer first generates an Ed25519 trust key **before grouping implementation or row audit**, stores
the private key only in its agent-scoped tool store, and returns only the public key/fingerprint for
the base config. After implementation, the same canonical reviewer task independently
downloads/verifies the source, reviews grouping code and official metadata, and signs a review
payload bound to the builder-payload digest with decision `pass`. The reviewer assignment is created
by the collaboration dispatcher in a fresh canonical agent task; its dispatcher-issued task/parent
identity and delivered transcript supplement the preregistered cryptographic trust key. The reviewer
private key is never given to the builder. Configuration freezes the reviewer trust-key fingerprint.
The reviewer-signed payload freezes the ephemeral builder-key fingerprint, exact config/Git/grouping-
code/builder-payload digests, and the fixed paths and digests of durable reviewer-transcript and
grouping-code-diff artifacts. The verifier requires distinct builder/reviewer keys and identities,
valid signatures, exact artifact digests, and a passing review before
  creating the scored run root. Any absent/failed signature keeps the candidate provisional and makes
  inference impossible. These are machine-review signatures and are reported as such; they do not
  pretend to establish speaker/session independence beyond the public source evidence. The review
  payload also binds the canonical agent task identity, review transcript SHA-256, review timestamp,
  grouping-code diff SHA-256, and exact builder payload digest.

### Cached extraction and numerical QA

- One extraction stage writes the raw layer-3 vector for every ordered target row and every
  counterfactual source/target row. A sidecar binds row ID, natural group, source record, input kind,
  selected token positions, shapes, dtype, model revision, and file hashes.
- Each K2 transform reads that raw cache once and writes float32 `pos` and `content` arrays with the
  identical ordered row IDs. It refuses checkpoint, lineage, shape, dtype, or digest drift.
- Parent, actual, no-op, and cross-family matched-natural controls are derived from these caches and
  the canonical pooling function. An exact cached no-op must be bit-identical.
- Calibration-only repeat inference uses two disjoint hash-ordered GUM sets of 16 items. Three
  repeats on set A estimate `atol = max(5e-7, 2 * set_A_max_abs_error)` with fixed `rtol = 5e-6`;
  `atol > 2e-5` is an immediate failure. Three fresh repeats on held-out set B must satisfy the
  estimated bound. Set B never changes it. Confirmation values never set or validate the tolerance.
  Both empirical errors, the hard ceiling, and pass/fail are reported. This is technical QA, not a
  scientific sham gate. For each set, repeat 0 is the reference; repeats 1 and 2 are compared
  elementwise against it over every selected layer-3 float32 target-vector element in row-ID then
  feature-index order. `set_A_max_abs_error` is the maximum absolute difference over those two
  comparisons. Set B passes only if every element satisfies
  `abs(repeat-reference) <= atol + rtol*abs(reference)`; reductions use NumPy float64 maximum in the
  stated order. K2 transforms are deterministic functions of the accepted raw cache and are covered
  separately by exact lineage/no-op checks.

### Probes, recovery, and leakage

- For every representation, fit one common scaler on the UTF-8-sorted union of unique discovery
  row IDs from the five scored probe tasks (three required plus two diagnostics):
  `z=(x-mean)/scale`, replacing a discovery standard
  deviation below `1e-8` by `1`. Every task for that representation uses this same coordinate
  system. Add an
  unpenalized intercept column. With one-hot `Y` and unit discovery-row weights, fit
  `argmin_(W,b) sum_i ||Y_i-(z_i W+b)||_2^2 + alpha ||W||_F^2` for alphas
  `[0.1,1,10,100]`. Predict the largest score; UTF-8 label order breaks score ties. Choose alpha by
  calibration unweighted macro-F1, with the largest alpha winning exact ties. Macro-F1 is the
  arithmetic mean of per-class F1 over the full frozen label set; an absent true or predicted class
  contributes zero rather than being dropped. Freeze scaler, intercept, decoder, label order, and
  alpha before C1/C2.
- The raw representation, each checkpoint's pos/content branch, and a no-training broad-position
  projection/complement baseline are evaluated under the same rows and labels. Its exact inputs are
  raw discovery decoders for `relative_quartile`, `head_signed_distance`, `deprel_coarse`, and
  `dependency_depth`. All raw probe tasks use one common raw scaler fit over the UTF-8-sorted
  union of their unique discovery row IDs, so every decoder lives in the same standardized
  coordinate system. Within each task, subtract the mean class-weight vector, L2-normalize every
  nonzero class direction, and scale the block by `1/sqrt(number_of_nonzero_directions)` so tasks
  have equal Frobenius weight. Concatenate blocks in that task order and compute a float64 SVD. Take
  the first 16 left singular vectors only when there are 16 values above `1e-8` and the frozen gap
  rule `(s16-s17) > 1e-6*s1` holds (missing `s17` counts as infinite gap); otherwise the projection
  baseline is explicitly `not_run_rank_or_gap` and cannot affect candidate or run eligibility. Fix
  each retained vector's sign so its largest-magnitude entry (lowest index on ties) is positive. For
  common raw standardized `z`,
  simple-pos is `z B B^T` and simple-content is `z-simple_pos`; both get their own discovery-only
  probe scaler like every representation.
- C1 is a visible internal diagnostic. C2 is the primary confirmation estimate. Five hundred
  ordinary, unconditional document bootstraps resample C2 groups with replacement and evaluate the
  already-frozen probes. A sampled group multiplicity becomes the sample weight of every row in that
  group; rows are never physically expanded. The estimand is conditional on the frozen
  discovery/calibration fit and does not claim training-sample uncertainty.

For a task with `C` frozen labels, the preregistered chance convention is exactly `1/C`. For every
point or draw:

- `raw_signal = F1_raw - chance`;
- `recovery(rep) = (F1_rep-chance)/raw_signal` only when `raw_signal > 1e-6`;
- assigned recovery is the recovery of pos for broad structural/context tasks and content for lexical;
- leakage is recovery of the opposite branch;
- `selectivity = assigned_recovery - leakage`.

Here `1/C` is the frozen chance convention (not a claim about every finite random-prediction
realization). Values are never clipped. An undefined raw denominator makes recovery/leakage/selectivity undefined
with reason `raw_signal_not_positive`, but preserves all F1 values. The C1 task-measurability gate is
required and fixed: raw point signal at least `0.02` and its 2.5th percentile bootstrap endpoint
strictly above zero. The localization gate is also required: assigned-recovery 2.5th percentile at
least `0.65` and selectivity 2.5th percentile strictly above zero. `relative_quartile` and
`head_signed_distance` are equal-weight representatives of broad structural localization;
`token_identity_v2` represents lexical
probe localization while `entity_substitution` supplies the separately required lexical functional
construct. `deprel_coarse` is a required prescore/visible diagnostic but is not a third family weight.

### Functional specificity and stability

- Pool only aligned changed/target token rows with the one canonical float32 path. For sampled
  document-context-anchor changes, assigned response is pos and leakage is content; for entity substitution,
  assigned response is content and leakage is pos. Cross-family natural deltas are the matched
  control; no ambient sentence-mean direction is injected.
- For pair `i` and representation `r`, define `d_r(i)=1-cos(pool(source_i),pool(target_i))` in
  float64 after canonical float32 pooling. A pair is finite when all vectors are finite/nonzero and
  `d_raw(i)>1e-8`; otherwise it is retained with an undefined reason. Define response
  `q_r(i)=d_r(i)/d_raw(i)`, branch margin `q_assigned(i)-q_unassigned(i)`, and construct-level means
  over pair components. The cross-family control margin is mean assigned-branch response on its own
  construct minus mean of that same branch's response on the other construct. Position and entity
  intervention sets use disjoint documents, so their ordinary bootstrap maps are independent within
  the same draw ID. At least 20 and 90% of frozen pair components must be finite. Counterfactual
  validity is required and passes only when both the branch-margin 2.5th percentile is at least
  `0.05` and the cross-family-control-margin 2.5th percentile is strictly above zero.
- All 95% intervals are the 2.5th and 97.5th quantiles of exactly 500 fixed SHA-256 document maps,
  using NumPy `quantile(method="linear")`. Point values use unit group multiplicities. A draw missing
  a frozen class/pair endpoint is explicitly nonfinite; at least 490/500 finite draws are required.
- On C2, report task-level full CKA matrices for each of the six unordered distinct checkpoint
  pairs `(g4,g5),(g4,g6),(g4,g7),(g5,g6),(g5,g7),(g6,g7)`: pos-pos, content-content,
  pos-content, content-pos; branch-identity margins; and counterfactual-delta CKA. The identity
  margin is `mean(pos-pos,content-content)-mean(pos-content,content-pos)`. Geometry is a required,
  separate status only for completeness: every same-branch CKA must be at least `0.90` and every
  identity margin strictly above zero. It never substitutes for selective recovery.
- Each task's CKA population is a frozen maximum of 4,096 rows selected before loading
  representations by UTF-8 group/label round-robin; within each cell the exact same ordered row IDs
  are used for both checkpoints. Counterfactual-delta CKA uses every finite frozen pair component.
- Partial CKA is diagnostic, not decision-bearing. Its nuisance matrix uses the frozen coarse-UPOS
  levels, punctuation indicator, word-length bins `1,2,3_4,5_7,8p`, and the 24 retained identity
  labels plus `__NONRETAINED__`. Each categorical block is UTF-8 ordered with its first level dropped;
  an intercept is added. More than 128 nuisance columns, `n <= rank([1,Z])+1`, a zero residual
  denominator, or fewer than two rows yields an explicit undefined reason. Nuisance levels are
  frozen from discovery and unknown C1/C2 values map only to the prespecified catchall shown above.

### Endpoint and sentinel contract

Required endpoint statuses are: prescore task/construct measurability, held-out numerical QA,
raw-signal measurability, localization, counterfactual validity, geometry completeness, cache
lineage, and signed grouping provenance. The formal `overall_decision_eligibility` is their
conjunction using the parent v2 status table; it can be eligible even though no architecture is
promoted or blind final opened. Finite subordinate values survive any failed gate.

Required probe tasks are `relative_quartile`, `head_signed_distance`, and `token_identity_v2`;
`deprel_coarse` and `dependency_depth` are support-required and diagnostic.
Optional collateral diagnostics are coarse UPOS, capitalization, word length, and punctuation.
`source_type` has status `ineligible` and reason `not_applicable_single_source`: every role contains
only UD, so it has one label, it is not silently omitted, and it is not required for the overall decision.
All optional diagnostics preserve their values/statuses without changing overall eligibility.

The aggregation hierarchy is frozen as follows:

1. A task measurement is `eligible` only when prescore support, C1 raw-signal measurability, C2
   finite-value completeness, and cache lineage pass. C1 localization is reported but never selects,
   thresholds, or suppresses C2; already-authorized C2 diagnostics still run after a scientific C1
   failure.
2. For candidate checkpoint g4/g5/g6, the broad structural/context family passes only when both
   `relative_quartile` and `head_signed_distance` pass the C2 assigned-recovery/selectivity gates and
   its document-context counterfactual passes. Lexical passes only when `token_identity_v2` and the
   entity counterfactual pass. A candidate checkpoint passes selective K2-posfam only when both
   families pass. The strict absolute-position endpoint remains visibly ineligible by architecture
   and is outside this revised question rather than being imputed.
3. Geometry completeness is required across the three candidate pairs g4-g5, g4-g6, and g5-g6.
   Its scientific stability hypothesis passes only under the `0.90`/positive-margin gates above.
   Cells involving g7 are diagnostic.
4. g7 is a negative-control checkpoint and the projection/complement is a comparator; neither can
   block measurement eligibility or rescue a failed candidate. Their missingness remains explicit.
5. `overall_decision_eligibility` is `eligible` only if signed provenance, all prescore-required
   constructs, held-out numerical QA, cache lineage, all three required candidate task measurements
   for all g4/g5/g6, both counterfactual endpoints separately for each of g4, g5, and g6, and
   candidate-pair geometry completeness are
   eligible. It is an eligibility status, not a hypothesis result.
6. If overall eligibility is not eligible, the architecture outcome is `equivocal`. If it is
   eligible and all three candidates pass selective K2-posfam plus candidate geometry passes, the
   outcome is `K2_broad_position_content_selective_supported`; otherwise it is
   `K2_broad_position_content_selective_not_supported`. No other combination,
   majority vote, g7 value, or baseline comparison changes this truth table.

## Staged tmux execution

The sole launcher is `scripts/launch_msae_measurement_v2_tmux.sh`. It creates the session named by
the frozen config and starts one coordinator process which owns the full DAG:

1. `prepare`: revalidate the already downloaded, digest-checked, independently signed public-source
   grouping; build roles/pairs/rows, run prescore gates, and freeze the input inventory; inference
   refuses to start unless both grouping signatures validate;
2. `extract`: launch discovery, calibration, C1, and C2 cache jobs on separate GPUs and wait;
3. `transform`: launch one all-role transform job for each of g4/g5/g6/g7 on separate GPUs and wait;
4. `analyze`: in one config-bound GPU job, fit/freeze probes and the projection baseline, then run
   C1/C2 document bootstraps, specificity, and stability;
5. `aggregate`: validate every lineage hash, render JSON and Markdown into an atomic final bundle,
   rerun the frozen-input comparison, and create the terminal `COMPLETE.json` only after publication.

Every subprocess is launched inside the tmux-owned coordinator, logs to the create-once run root,
records command/config/environment/GPU/seed metadata, and writes an atomic terminal marker. The
resolved config binds GPU UUIDs `GPU-ec526219-fb07-e57e-a30d-5d2ab843fb15`,
`GPU-9b529a09-92a6-caea-fee2-6b2bf07b0e4e`,
`GPU-6af2c6b0-92ad-e10e-33d2-8345f38dc9a8`, and
`GPU-0782e780-b5b4-d703-844d-91b15b873591`. Before every child, the coordinator verifies the UUID is
present. A dedicated wrapper verifies by `lstat` that `/tmp/msae_atlas_gpu_locks` is a current-user
owned, mode-0700 real directory and its UUID-keyed lock is a current-user owned, mode-0600 regular
nonsymlink file. It opens the lock on non-CLOEXEC FD 200, obtains a nonblocking exclusive `flock`,
then checks GPU idleness below 1 GiB while holding the lease. It records wrapper/child PID-start-time
and command hash, launches exactly one child **with FD 200 inherited**, and waits. The coordinator
never owns the FD. On normal exit the child closes first and the wrapper's EXIT trap closes second;
if the wrapper dies, the surviving child retains the same open-file-description lease until it exits.
Children use UUID-based `CUDA_VISIBLE_DEVICES` and receive TERM then KILL after a 60-second
cancellation grace. Recovery validates `/proc/<wrapper-or-child>/fd/200`, the lock record, and lock
ownership. A
prelaunch disk estimator requires twice projected cache bytes free.

The coordinator writes a heartbeat every 30 seconds with host, PID, Linux `/proc/<pid>/stat` start
ticks, config hash, current stage, and child PIDs. Child output is written to a unique temporary
directory and atomically renamed only after its manifest verifies. A failed child cancels later
stages and produces `FAILED.json`; partial values cannot become an overall decision. An authenticated
`--recover` launcher is the only exception to create-once launch: it requires the same host/config,
a missing or stale owner PID+start-time and valid hashes for every committed stage. It is deliberately
fail-closed around orphans: every still-live recorded wrapper or child is refused and no recovery
command sends it a signal. After every PID/start-time pair is proven dead, recovery archives (never
deletes) prior owner, handoff, and failure records, increments the attempt namespace for create-once
job records, revalidates committed stages, and resumes at the first absent stage. `--abandon`
similarly refuses live processes and any already terminal run. Live-owner recovery, completed-run
relaunch, hash drift, unknown files, or ambiguous child identity is refused.

The user's requested Codex handoff occurs only after the launcher verifies a fresh heartbeat, the
tmux coordinator, the current real GPU stage, every wrapper/child PID-start-time pair, and each
child's inherited UUID-lock FD 200, with no terminal failure. The coordinator then continues
unattended. Experimental completion is stricter: aggregation atomically publishes a final bundle
and only then creates `COMPLETE.json`; it refuses `FAILED` or `ABANDONED`. A later result claim still requires `research-claim-review`; `COMPLETE.json` means
the run and report are validly materialized, not that their scientific conclusion has been endorsed.

## Alternatives considered

1. **Rerun completion v1 with a looser tolerance.** Rejected because it changes a frozen analysis
   and leaves the support and endpoint-coupling problems intact.
2. **Use GENTLE or GUMReddit as replacement confirmation.** Rejected because the official r2.18
   public files expose only 26 and 18 natural documents respectively, below or too near the fixed
   25-group floor and unable to provide two disjoint 25-group confirmation roles.
3. **Keep WikiNeural sentence IDs as clusters.** Rejected because a sentence identifier is not a
   justified natural document sampling unit.
4. **Class-preserving bootstrap on LinES.** Rejected because four/five real documents cannot be
   made well-powered by favorable resampling.
5. **Launch new K2/K3 training now.** Rejected because v2 must first determine whether the existing
   solution is selectively localized or reliably mixed.
6. **Reuse float16 v1 transforms.** Rejected for specificity because it recreates the mixed
   precision/reduction path failure; the new scored cache is float32 and v2-namespaced.
7. **Uniformly shift GPT-NeoX position IDs while holding tokens fixed.** Rejected before scoring:
   RoPE attention is invariant to a shared phase translation, so any measured delta would be
   numerical noise. The run narrows its claim to broad structural/context position and records strict
   absolute position as unavailable.

## Milestones

### M1 — Freeze the executable protocol and source inventory

- Add the execution config, exact ESLSpok file digests, role/grouping contract, task constructs,
  checkpoint digests, and run-root/session identity.
- Add a durable source/tokenizer-only preflight proving all required task supports, a 24-label
  cross-role identity vocabulary, disjoint 40/26/24 entity-pair populations, and 109/236/211 aligned
  document-context pair populations (including exact EOS/alignment/length checks) as well as 872
  natural groups and disjoint 436/436 roles.
- Obtain and verify distinct builder and adversarial-review Ed25519 signatures over exact provenance
  and grouping digests.
- **Acceptance:** config validation, preflight, and both signatures pass; no neural inference has run.

### M2 — Build/test deterministic data and cache lineage

- Implement the data builder, task rows, controlled pairs, cache format, and validators.
- Add synthetic tests for grouping regex, whole-group split, cap, identity intersection,
  counterfactual alignment, cache tampering, and fail-closed stage markers.
- **Acceptance:** focused tests and smoke extraction with a fake model/cache pass; all real output
  roots remain absent.

### M3 — Build/test extraction, transforms, probes, specificity, and stability

- Implement config-only stage CLIs and aggregation.
- Add numeric fixtures for ridge selection, bootstrap group weights, recovery denominators,
  specificity margins, cross-branch/delta/partial CKA, and endpoint missingness.
- **Acceptance:** CPU synthetic smoke pipeline finishes and produces a lineage-valid report.

### M4 — Adversarial/reproducibility gate

- Run `/adversarial` on the implementation, experiment design, launch script, and config; fix all
  blockers and material revisions and obtain `SHIP`.
- Check fixed seeds, pinned environment/model/data/checkpoints, no secret material, no hardcoded
  personal paths, create-once artifacts, and exact command logging.
- **Acceptance:** focused tests pass, scripts compile, shell syntax passes, config/input digests
  validate, reviewer says `SHIP`, and no real v2 process has yet started.

### M5 — Launch the whole DAG under tmux

- Invoke the sole launcher once.
- Verify the tmux owner marker, coordinator PID/command, live first-stage children, run config hash,
  logs, and absence of an immediate failure marker.
- **Acceptance:** the complete stage DAG is owned by the config-declared tmux session, the
  coordinator is live, at least one real stage is running,
  and the session can proceed without Codex.

### M6 — Automated terminal validation (runs after the Codex handoff)

- The coordinator waits for all exact stages/shards, rehashes the frozen inputs and every output,
  rejects extra/missing IDs, validates report schemas and endpoint reason/value consistency, records
  final environment/runtime/lineage, obtains a terminal-state lock, verifies that no
  `FAILED.json`/`ABANDONED.json` exists, and writes exactly one terminal artifact. An earlier
  abandonment or failure is immutable and cannot be overwritten by late child completion.
- A failure writes `FAILED.json` and no completion marker; recovery/abandonment follows the frozen
  owner protocol. A successful run writes `COMPLETE.json`. Scientific interpretation remains blocked
  on a later `research-claim-review` of the resulting claims.
- **Acceptance:** eventually either lineage-valid `COMPLETE.json`, reviewed `FAILED.json`, or
  authenticated `ABANDONED.json` exists; merely starting tmux never counts as experiment completion.

## Definition of done

### Codex implementation/launch handoff (this user request)

- [ ] V2 is additive; frozen completion-v1 and blind-final artifacts are not modified or opened.
- [ ] ESLSpok revision/files and natural transcript grouping are digest-bound and C1/C2 are
      whole-group disjoint with 436 groups each.
- [ ] Every scored task passes the fixed prescore group/class/cap/bootstrap gates or is explicitly
      ineligible before inference/promotion.
- [ ] Broad structural/context and lexical families each have an actually distinct functional
      operationalization; strict absolute translation is explicitly excluded as a RoPE symmetry.
- [ ] All raw/K2/counterfactual values used together share float32 cache lineage and canonical
      pooling; repeated inference is separate QA.
- [ ] Raw, four K2 checkpoints, no-incoherence control, and a no-training projection baseline are
      compared on identical rows.
- [ ] Recovery, leakage, specificity, task/family CKA, cross-branch matrices, delta/partial CKA, and
      endpoint missingness are independently reportable.
- [ ] The run is config/seed/data/checkpoint bound, create-once, resumable only by the coordinator,
      and writes terminal success/failure artifacts.
- [ ] Tests/compile/shell checks pass and final prelaunch `/adversarial` verdict is `SHIP`.
- [ ] The complete pipeline is live in the owned tmux session with no immediate terminal failure.

### Experiment terminal state (enforced after Codex exits)

- [ ] Both grouping-provenance signatures and the resolved input inventory still verify byte for
      byte.
- [ ] All expected stage/shard artifacts exist, no unexpected shard enters aggregation, and all
      cache/report lineages and endpoint schemas pass.
- [ ] Exactly one of `COMPLETE.json`, `FAILED.json`, or `ABANDONED.json` records the final state;
      only `COMPLETE.json` denotes a successfully completed experiment.
- [ ] No architecture or publication claim is made until the completed report receives a separate
      `research-claim-review`.

## Verification plan

Before launch:

```bash
./.venv-atlas/bin/python -m pytest -q tests/test_msae_measurement_v2.py \
  tests/test_msae_measurement_v2_run.py
./.venv-atlas/bin/python -m py_compile \
  scripts/msae_measurement_v2_run.py scripts/run_msae_measurement_v2.py
bash -n scripts/run_msae_measurement_v2_pipeline.sh \
  scripts/launch_msae_measurement_v2_tmux.sh
./.venv-atlas/bin/python scripts/run_msae_measurement_v2.py \
  --config configs/atlas_measurement_v2/run.json --stage validate
```

After launch (observation only):

```bash
readarray -t RUN_IDENTITY < <(.venv-atlas/bin/python - <<'PY'
import json
from pathlib import Path
cfg=json.load(open('configs/atlas_measurement_v2/run.json'))
print(cfg['session'])
print((Path.cwd()/cfg['run_root']).resolve())
PY
)
SESSION=${RUN_IDENTITY[0]}; RUN_ROOT=${RUN_IDENTITY[1]}
tmux list-windows -t "$SESSION" \
  -F '#I #W #{pane_pid} #{pane_current_command}'
tmux capture-pane -pt "$SESSION":coordinator -S -80
cat "$RUN_ROOT/owner.json"
.venv-atlas/bin/python - "$RUN_ROOT" <<'PY'
import json, os, sys
from pathlib import Path
p=json.load(open(Path(sys.argv[1])/'owner.json'))
os.kill(int(p['pid']), 0)
assert p['config_sha256'] and p['session']
PY
test ! -e "$RUN_ROOT/FAILED.json"
```

## Risks and mitigations

- **Transcript IDs may not equal statistically independent speakers.** The official corpus calls
  them source files, grouping never splits a file, and the signed independent machine review must
  accept the stated sampling-unit rationale before inference. Results still limit claims to source
  transcript files rather than asserting one speaker/session per ID.
- **ESLSpok is learner/spoken English, not the original confirmation domain.** This is desirable as
  a domain-generalization stress test but limits population claims; all results name the domain.
- **Natural-context pairs change attended content as well as boundary distance.** The construct is
  explicitly broad contextual position, not pure absolute position; same target rows are aligned,
  document clusters are disjoint from entity pairs, and strict absolute claims remain unavailable.
- **Proper-name replacement can be contextually awkward.** It is a controlled lexical
  intervention, not a natural-language quality claim; alignment and unchanged non-target tokens are
  enforced, and results are reported separately from token-identity decoding.
- **Fixed-probe bootstrap omits training-sample uncertainty.** The estimand and limitation are
  explicit; the run does not overclaim unconditional model-selection uncertainty.
- **Float32 caches consume disk.** The builder estimates bytes and refuses launch unless at least
  twice the projected requirement is free. Intermediate cache deletion is forbidden before the
  terminal report.
- **A tmux coordinator can die.** Atomic temp/rename stages, PID-start-time heartbeats, UUID leases,
  authenticated recovery, and explicit abandonment prevent an unowned nonterminal root from being
  mistaken for a result.

## One-way doors

1. Selecting ESLSpok r2.18 and freezing its group split before inference is a scientific one-way
   door for this run. Selection remains provisional until full tokenizer-aware preflight and both
   provenance signatures pass, then requires `/adversarial` review before launch.
2. Starting neural inference is the scoring one-way door. It is permitted only after the resolved
   config/input inventory is frozen, verification passes, and the final prelaunch adversarial verdict
   is `SHIP`.
3. The existing blind final remains closed; this run creates no mechanism to unlock it.
