# PLAN — Relational measurement-design v4

## Goal

Develop and freeze, using only the eight already-opened v3 source files and synthetic outcomes, a
supportable estimator for comparing true dependency edges with matched nonedges.  The study asks a
measurement question only: can nuisance control retain at least two independent source panels while
maintaining prespecified overlap, balance, document-support, null-calibration, and injected-effect
recovery?  A successful result may authorize a separately preregistered fresh-corpus relational-object
study; it does not itself authorize model inference or learned representations.

## Non-goals

- Do not modify, retry, resume, or reinterpret the signed v3 prescore terminal.
- Do not load model weights, run a model forward, compute any representation endpoint, or inspect any
  activation cache in v4.
- Do not access, name, download, or prescore a fresh scientific corpus in v4.
- Do not train K2, an SAE, a context/local model, a shared branch, or any neural representation.
- Do not choose a measurement method using QK, transported-value, attention, probe, or activation
  outcomes.
- Do not make publication of `PAPER.md` conditional on this study.

V4 is explicitly an outcome-informed **measurement-development successor** to the v3 support stop.
All eight sources are already opened development data.  V4 may change the estimand prospectively,
but it may not relabel v3 as passing.

## Constraints and immutable parents

- Signed v3 terminal: `reports/provenance/relational_objects_v3_prescore_terminal_v1.json`, SHA-256
  `b318f2b98de04c639942c8f220ee09d2c1a00f22cad8bbc4d3837611a45c4c76`.
- Exact v3 source pool: `configs/relational_objects_v3/source_pool_manifest.json`, SHA-256
  `7599db848f2e1e8fcdb4e746b31c556169b059e3842d3270e36d4b2a86a5bfcd`.
- Strict parser report: `reports/relational_objects_v3_source_pool_conllu_validation_v1.json`,
  SHA-256 `5af12b21fcc34a42f586152eed261062f521849db0c668ad2a5d242ea3d4faa3`.
- Source exposure manifest: `reports/provenance/relational_objects_v3_source_exposure_v1.json`,
  SHA-256 `20f730d24f9c1b89bf33268bac8b46df83af316bb5dbeff9cff4e25773ebd591`.
- The corrected v3 matcher remains a frozen reference arm.  V4 writes only under
  `configs/relational_measurement_v4`, `data/relational_measurement_v4`,
  `results/relational_measurement_v4`, and new v4 report/provenance paths.
- Every run is config-driven, seeded, create-once, and records source, code, tokenizer, environment,
  and CPU hardware hashes.  The main run uses tmux even though it is CPU/tokenizer-only and exports
  `CUDA_VISIBLE_DEVICES=-1`; model and CUDA access are prohibited in v4.  GPU selection belongs only
  to a later, separately authorized representation study.

## Estimand and invariant candidate rules

The target contrast is the component-equal mean difference between a true direct dependency edge and
a nonedge that is neither a direct edge nor an ancestor/descendant pair.  Positives and negatives
must be from different genuine `newdoc id` documents.  Document pairs form nonoverlapping components;
no document, sentence row, token pair, or negative base pair can be reused.

All candidate methods keep these factors exact:

- causal orientation (`later_query_is_head` or `later_query_is_child`);
- ordered endpoint UPOS;
- ordered punctuation flags;
- ordered endpoint Pythia subtoken counts.

All methods retain the full nuisance vector for diagnostics and later adjustment: complete endpoint
morphology values for the frozen eight-key vocabulary, surface gap, relative query location,
causal-key fraction, sequence length, and ordered lexical identifiers.  Lexical identities are never
used to require equality because that would redefine most true-edge contrasts out of support; they
are used for collision-free group diagnostics and later frozen hashing.

## Candidate matching methods

The following order is frozen before the v4 run.  The first method that passes every simulation and
real-covariate support/balance gate in at least two sources is nominated.

1. **`exact_v3_reference`** — the complete morphology-value and fine sequential-bin matcher copied
   byte-for-byte from v3.  This is descriptive and expected to reproduce the signed v3 support table;
   disagreement fails v4 rather than silently changing the reference.
2. **`coarse_exact`** — exact core factors plus endpoint morphology-key *presence* (not value), surface
   gap bins `{1,2,3-4,5-8,9+}`, relative-query quartiles, causal-key-fraction quartiles, and sequence
   length bins `{1-32,33-64,65-128,129-256}`.  The relative-query fraction is exactly
   `query_index/max(1, sequence_length-1)` and the causal-key fraction is exactly
   `causal_key_count/sequence_length`.  Both must be finite in `[0,1]` and use the integer bin
   `min(3,floor(4*x))`: `0.25` enters bin 1, `0.50` bin 2, `0.75` and `1.00` bin 3; an invalid value
   fails the source cell.  Complete morphology values remain diagnostics.
3. **`optimal_caliper`** — exact core factors, followed within every prospective document pair by a
   deterministic minimum-cost one-to-one assignment.  A candidate pair is admissible only when:
   morphology-value Hamming distance across the sixteen ordered endpoint/key cells is at most 4;
   `abs(log2(edge_gap/nonedge_gap)) <= 1`; relative-query and causal-key fractions each differ by at
   most `0.125`; and `abs(edge_length-nonedge_length)/max(edge_length,nonedge_length) <= 0.25`.  A
   morphology cell is `KEY=NONE`, `KEY=OTHER`, or the frozen vocabulary value, ordered first by later
   endpoint then earlier endpoint and then by the eight-key config order.  Cost is the morphology
   mismatch fraction plus `abs(log2(edge_gap/nonedge_gap))`, both fractional-position differences,
   and the relative length difference.

   Within each common exact-core stratum, sort positive and negative rows by `candidate_id`.  Form the
   admissible bipartite graph and first compute its maximum matching cardinality `K`.  Then compute an
   exactly `K`-edge minimum-cost flow with Python arbitrary-precision integer costs.  For `A`
   admissible cells, give the cell at zero-based rank `r` in ascending
   `SHA256(edge_candidate_id || "|" || nonedge_candidate_id)` order the cost
   `round(10^9*cost)*2^A + 2^r`.  Maximum cardinality is therefore the first objective, one unit of
   summed rounded distance dominates the entire lower-order term, and the sum of distinct powers of
   two gives every candidate-edge subset a unique deterministic secondary value.  Retain the unique
   `K`-edge flow.  Equal-cost and one-distance-quantum adversarial tests must confirm both priorities.

   Before graph construction, retain the first at most 32 positives per document/core stratum and the
   first at most 64 negatives per document/core stratum, each by ascending `candidate_id`; report
   truncation.  Run the exact `K`-edge minimum-cost flow separately in every common core stratum for one fixed
   positive-document/negative-document direction, pool all retained admissible real--real assignments
   across those strata, sort them by `(cost, pair_id)`, and greedily retain an assignment only when its
   negative `base_pair_id` has not previously been retained; then keep the first at most 12 for that
   whole document-pair direction in the same order.  This deliberately sacrifices global distance
   optimality to impose one deterministic cross-orientation/base capacity.  Repeat independently with
   the two document roles reversed.  The outer document
   assignment uses the exact v3 integer objective: maximize
   nonempty document-pair component count, then the yield of at most 12 pairs per direction, then the
   stable document-pair digest.  Inner cost does not enter outer selection; balance gates assess the
   resulting panel.  This separation is intentional and deterministic.

No caliper is learned from the eight sources.  A method below a gate is reported, not repaired.

Common panel machinery is bound to the terminal-referenced v3 scout implementation
`scripts/scout_relational_objects_v3.py`, SHA-256
`06f47d9d75909e431ad28fcec8a1e68e9f55f62b6383851e300303ad1d15058a`, and v3 scout config SHA-256
`e85de436935c6a97df05f617ebe9b8132c663aee1cac7baed6d69423c7178ce7`.  Both alternatives reuse its
strict sentence loading/alignment, dependency/ancestry exclusions, stable IDs, stable document
partition, outer `match_components` lexicographic assignment, and `canonical_cap_components` engine.
For `coarse_exact`, only the candidate stratum changes to the equality tuple stated above:
`enumerate_by_document` retains the first 12 rows by `candidate_id` per document/label/coarse stratum;
`orientation_pairs` sorts each shared stratum canonically, zips positive and negative rows, prevents
negative-base reuse, and retains at most 12 pairs for the entire document-pair direction.  For
`optimal_caliper`, only the explicitly specified 32/64 candidate caps and exact inner flow
replace those two coarse within-document-pair operations.

For both alternatives, the outer assignment selects at most 150 components by
`(-pair_count,component_id)`.  If at least 500 pairs exist and one mandatory first pair from each
nonempty direction in each selected component requires at most 500 slots, retain all mandatory IDs
and fill to exactly 500 by ascending remaining `pair_id`; otherwise retain every pair and report the
shortfall.  Recompute pair counts.  Allocate five folds by processing components in
`(-pair_count,component_id)` order and assigning each to the fold with smallest current component
count, breaking ties toward the smaller fold index.  Final serialized components sort by
`component_id`.  These are the exact v3 cap/fold rules and are invariant across alternative methods.

## Candidate estimators and synthetic validation

For every matcher with at least two support-eligible source panels, compare two prespecified
continuous-outcome estimators of the same constant edge contrast, plus one descriptive overlap
estimator:

1. **`paired_mean`**: for pair `j` in component `c`, `D_cj=Y_edge-Y_nonedge`,
   `D_c=mean_j(D_cj)`, and `theta_hat=mean_c(D_c)`.
2. **`control_ridge_residualized`**: in each held-out component fold, fit
   `StandardScaler` and `Ridge(alpha=100, fit_intercept=true, solver="lsqr", tol=1e-8,
   max_iter=10000)` on nonedge rows from the other four folds.  Let `m_minus_intercept(x)` be the ridge
   prediction with the fitted intercept removed.  For each held-out pair set
   `D*_cj=(Y_edge-m_minus_intercept(X_edge))-(Y_nonedge-m_minus_intercept(X_nonedge))`; aggregate
   `D*_cj` first within component and then equally across components.  Training-row base weights give
   every training component total one and split that weight equally over its nonedge rows.  Scalers,
   feature levels, and models are never fitted on a held-out component.  Any empty level is retained
   as an all-zero fixed column; a nonconvergence warning, nonfinite coefficient, or rank/shape error
   invalidates the cell.
3. **`overlap_ato_descriptive`**: this targets the overlap population, not the component-equal
   contrast, and can never nominate a design.  Fit in each training fold
   `LogisticRegression(C=1, penalty="l2", solver="lbfgs", fit_intercept=true,
   class_weight=None, max_iter=2000, tol=1e-8, random_state=seed)` after a separate propensity scaler.
   The propensity training set contains both edge and nonedge rows from the four training folds.  For
   a training row in component `c`, let `a_i=1/n_c`, where `n_c` is that component's pair count; rescale
   to `a'_i=a_i*N_train/sum_train(a)` so mean training weight is one.  Fit
   `StandardScaler.fit(X_train,sample_weight=a')` and then
   `LogisticRegression.fit(X_scaled,T,sample_weight=a')`.  Here neither `C` nor a full-panel weight
   enters either fit.  Predict every row in the held-out fold exactly once.  Predict raw held-out propensity `e_i`; numerical calculations clip to
   `[1e-6,1-1e-6]`.  Base row weight is `1/(C*n_c*2)` for each of the `2*n_c` rows in component `c`.
   Multiply treated rows by `1-e_i` and controls by `e_i`, normalize separately to unit total by
   treatment, and report the weighted mean difference.  This arm supplies positivity and weight-tail
   diagnostics only.  Call the two treatment-normalized arrays together `w_final`; the mandatory
   weight-tail ratio is `max(w_final)/median(w_final[w_final>0])` across both groups.  An empty positive
   set, zero median, or nonfinite value fails.

The fixed nuisance design contains complete morphology-value one-hots, ordered UPOS,
punctuation/subtoken features, `log2(1+surface_gap)`, `query_index/max(1,sequence_length-1)`,
`causal_key_count/sequence_length`, `log2(sequence_length)`, and 128-dimensional signed lexical hashes
for ordered FORM, lemma, and FORM/lemma pairs.  Hash index is the first eight bytes of
`SHA256("v4|" || field_name || "|" || value)` modulo 128 and sign is the low bit of byte nine;
bit zero maps to `+1` and bit one maps to `-1`; collisions add.  Every hash input uses canonical
length-prefix encoding: for each UTF-8 part append its byte length as unsigned 64-bit little-endian,
then its bytes; compound identities append their parts in the named order.  The complete column order
is: numeric columns in the exact order listed above; then categorical fields in the order later-UPOS,
earlier-UPOS, later-punctuation, earlier-punctuation, later-subtoken-count, earlier-subtoken-count,
later morphology keys in config order, earlier morphology keys in config order, with each field's
`field=value` columns sorted by UTF-8 bytes; then lexical-hash indices `0..127`.  Category levels are
the union over the frozen panel and therefore fixed before folds; scaling parameters are fit only on
training rows.  No document may cross folds.

For either primary estimator, construct a 95% interval from the `C` component contrasts using
`theta_hat +/- scipy.stats.t.ppf(0.975,C-1)*s_D/sqrt(C)`, where `s_D` is the sample standard deviation
with `ddof=1`.  `C<2`, zero/nonfinite standard error, a nonfinite bound, or any fit failure invalidates
the cell.  The first of the two primary estimators in the simplicity order that passes every
synthetic gate is nominated; the overlap arm cannot nominate.

Synthetic outcomes are generated on fixed real covariate panels without activation data, using 200
deterministic replicates for each of six frozen DGPs.  Let `X_dgp` be the fixed nuisance matrix without
lexical hashes.  Drop zero-variance columns and standardize remaining columns on the complete panel.
All DGP centering and SD operations use the same component-and-treatment-equal population weights:
for either row of pair `j` in component `c`, `w_i=1/(2*C*n_c)`, so weights sum to one.  For vector
`z`, `mean_w(z)=sum_i(w_i*z_i)` and
`SD_w(z)=sqrt(sum_i(w_i*(z_i-mean_w(z))^2))` with population divisor (`ddof=0`).  Standardization is
`(z-mean_w(z))/SD_w(z)`; score rescaling means subtracting `mean_w` and multiplying by
`0.50/SD_w`.  Zero or nonfinite SD fails.  Every later reference to population SD, including
`std_population(Y0)`, means exactly `SD_w` over all edge and nonedge rows of the capped panel.
For each source/matcher/coefficient-family, generate a coefficient vector once with NumPy
`PCG64(sha256_u64(seed,source,matcher,coefficient_family,"linear_coef"))`, draw iid standard normals,
and rescale the linear score to population SD `0.50`.  For the `nonlinear` family, take the first 16
nonconstant columns in lexicographic feature-name order, form eight adjacent products, generate a
second vector with the analogous `"interaction_coef"` seed, and rescale the interaction score to SD
`0.50`; nuisance mean is linear plus interaction score.

For the `lexical` family, start with the same construction as the `linear` family and add a lexical
score independent of the estimator's 128-bin hash.  For each of ordered child/head FORM, child/head
lemma, ordered FORM pair, and ordered lemma pair, map the complete UTF-8 identity through
`SHA256("v4-dgp-lexical|" || field || "|" || value)`.  Assert no complete 256-bit digest collision in
the panel.  Convert the first eight digest bytes to unsigned little-endian integer `z`; map
`(z+0.5)/2^64` through `scipy.stats.norm.ppf`, sum the six field scores, divide by `sqrt(6)`, center,
and rescale to population SD `0.50`.  The lexical nuisance mean is linear plus lexical score.  Failure
to obtain any required nonzero finite SD invalidates the cell.

For replicate `r`, use `PCG64(sha256_u64(seed,source,matcher,coefficient_family,effect_role,r,
"noise"))`.  Draw component intercepts `u_c` and row errors `epsilon_i`; set
`Y0_i=mu_i+u_component(i)+epsilon_i`.  When the table specifies a positive effect, set
`tau=0.20*std_population(Y0)` before treatment and draw component treatment deviations `v_c`; observed
`Y_i=Y0_i+T_i*(tau+v_c)`, with true target equal to the component-equal realized mean of `tau+v_c`.
For null rows `tau=v_c=0`, so the true target is exactly zero.  A null/positive pair shares the exact
same coefficient family and construction; only replicate noise seeds and the table's effect role
differ.  `sha256_u64` is the unsigned little-endian integer represented by the first eight SHA-256
digest bytes of UTF-8 pipe-joined inputs.  Canonical draw attachment is: components sorted by
`component_id`; within them pairs sorted by `pair_id`; within each pair nonedge row then edge row.
From the one replicate generator draw, in order, `C` standard normals for `u`, then `2*N_pairs`
standard normals for row errors in that row order, then—only for a positive DGP—`C` standard normals
for `v`.  Multiply by the table SDs after drawing.  No other call advances that generator.

| DGP | coefficient family | interactions | lexical score | `sigma_u` | `sigma_epsilon` | `sigma_v` | effect |
|---|---|---:|---:|---:|---:|---:|---:|
| `linear_null` | `linear` | no | no | 0.50 | 1.00 | 0 | 0 |
| `linear_positive` | `linear` | no | no | 0.50 | 1.00 | 0.10 | `0.20*SD(Y0)` |
| `nonlinear_null` | `nonlinear` | yes | no | 0.50 | 1.00 | 0 | 0 |
| `nonlinear_positive` | `nonlinear` | yes | no | 0.50 | 1.00 | 0.10 | `0.20*SD(Y0)` |
| `lexical_null` | `lexical` | no | yes | 0.50 | 1.00 | 0 | 0 |
| `lexical_positive` | `lexical` | no | yes | 0.50 | 1.00 | 0.10 | `0.20*SD(Y0)` |

Across 200 replicates per DGP, bias is `mean(theta_hat-true_target)`, coverage is the fraction of inclusive
intervals containing `true_target`, null rejection is the fraction whose inclusive interval excludes
zero, and positive power is the fraction whose inclusive interval excludes zero in the correct
direction.  For all three null DGPs, absolute bias must be at most `0.03`, coverage must be in
`[0.90,0.99]`, and rejection must be at most `0.10`.  For all three positive DGPs, absolute bias must be at
most `0.04`, coverage must be in `[0.90,0.99]`, and power must be at least `0.80`.  All 200 replicates
must be finite and valid; no replicate is dropped.

## Real-covariate gates

Eligibility is recomputed on the final deterministic cap of at most 150 components and exactly 500
pairs.  Every eligible source must have:

- at least 100 document-disjoint components and 500 pairs;
- at least 20 pairs in each causal orientation;
- all five folds containing at least 18 components;
- zero mismatches on every exact-core factor;
- absolute standardized mean difference at most `0.10` for every numeric nuisance and every
  morphology-value indicator with pooled prevalence at least `0.05`;
- weighted KS distance at most `0.10` for surface gap, relative query position, causal-key fraction,
  and sequence length;
- effective component sample size at least 100 and effective pair sample size at least 400;
- maximum component weight at most `0.02` and maximum document contribution at most `0.01`;
- 99% of cross-fitted raw propensities in the inclusive interval `[0.05,0.95]` and maximum overlap
  row weight at most ten times the positive median overlap row weight.

For each treatment separately, base weights sum to one: a row in component `c` with `n_c` pairs has
weight `1/(C*n_c)`.  Weighted mean is `sum(w*x)`.  Weighted population variance is
`sum(w*(x-mean)^2)`.  Absolute SMD is `abs(mean_1-mean_0)/sqrt((var_1+var_0)/2)`; when the denominator
is zero it is zero only if the means are exactly equal and `+inf` otherwise.  Weighted KS is the
supremum over the sorted union of observed values of the absolute difference between treatment
weighted empirical CDFs.  Pair ESS is `1/sum_j((1/(C*n_component(j)))^2)`; component ESS is `C`.
Component contribution is `1/C`; each of its two documents contributes `1/(2*C)`.  Thresholds are
inclusive; NaN, infinity, an empty denominator, or ambiguity fails closed.  Missing morphology values
are explicit `NONE` levels.  Indicator SMD gates apply only when unweighted pooled row prevalence is
at least `0.05`; every excluded indicator and prevalence is reported.

Run and report every matcher/source support and balance cell.  For each matcher in the frozen order,
fix its first two sources in the frozen v3 source order that pass every real-covariate gate.  Run all
two-primary-estimator x two-source x six-DGP simulation cells for every matcher having two fixed
sources; run the descriptive overlap arm for the same cells.  After all scheduled cells finish,
traverse matcher order and then primary-estimator order and nominate the first combination for which
both fixed sources pass every real-covariate gate and all twelve source/DGP simulation cells.  A fit or
metric failure fails that combination; it is never omitted.  Weight-tail and propensity gates apply
to every panel because they diagnose overlap, but overlap ATO estimates never enter nomination.

## Decision and lifecycle

The v4 scientific result has exactly three mutually exclusive decisions, evaluated in this order:

- `NOMINATE_MEASUREMENT_DESIGN_FOR_FRESH_PREREGISTRATION`: one frozen matcher-estimator combination
  passes all gates in at least two opened sources;
- `STOP_MEASUREMENT_DESIGN_UNDER_SUPPORTED`: no matcher has two **structurally supported** sources,
  where structural support means the component, pair, causal-orientation, and five-fold count gates
  before any balance, propensity, or estimator gate;
- `STOP_MEASUREMENT_DESIGN_UNCALIBRATED`: at least one matcher has two structurally supported sources,
  but no complete matcher-estimator combination passes the real-covariate and synthetic gates in two
  sources.  This includes the case where structural support exists but balance or overlap fails.

Any postauthorization execution, hash, parser-reference, fit, nonfinite, or resource failure instead
produces signed `TERMINAL_TECHNICAL_FAILURE` with exactly one of the reason
codes `REFERENCE_DRIFT`, `HASH_DRIFT`, `SOURCE_ERROR`, `FIT_FAILURE`, `NONFINITE`,
`RESOURCE_LIMIT`, or `UNEXPECTED_EXCEPTION`.  It cannot be
reported as a scientific decision or retried under the same namespace.  The owner process creates an
`O_EXCL` opening containing a random 256-bit nonce before the run root, repeats that nonce in every
artifact, and is the only process permitted to create the `O_EXCL` terminal.  On failure it atomically
inventories and hashes all partial artifacts, marks them quarantined, and then writes the technical
terminal.  A nonowner or pre-existing path fails without mutation.

All lifecycle signatures use Ed25519 over the v3 canonical JSON byte encoding.  Owner and supervisor
keys are distinct, key-load/signature failure fails closed, and their SHA-256 public-key fingerprints
are pinned in the signed authorization.  Every signed artifact has a frozen schema tag and payload;
verification rejects an unknown schema, invalid signature, fingerprint mismatch, nonce/PID mismatch,
or transitive hash mismatch.

Before authorization, the launcher creates/deletes an `O_EXCL` write probe and signs/verifies a
temporary payload with the owner key.  At launch, the launcher generates the nonce, starts a
separately keyed supervisor with that nonce, and waits for an fsynced, `O_EXCL`, supervisor-signed
`SUPERVISOR_READY` acknowledgment containing the nonce, supervisor PID, launcher PID, namespace, and
frozen-candidate hash.  The launcher verifies the acknowledgment and writes an fsynced, `O_EXCL`,
owner-key-signed `LAUNCHER_TRIGGER` binding the launcher PID, nonce, authorization, and exact ready
hash.  Only after independently verifying that trigger does the supervisor spawn the owner, which
lets the supervisor observe the exact owner PID and exit status.  The owner independently verifies
the exact trigger and ready artifact before its signed handoff.  The handoff binds authorization,
ready hash, trigger hash, nonce, launcher PID, supervisor PID, and owner PID.  The owner is forbidden
to create the opening unless that exact chain exists; the opening repeats those identities and binds
the handoff hash.  The supervisor spawns the owner in its own process group.  There is exactly one
authoritative fsynced `O_EXCL` closure path, and its complete signed payload has a discriminant of
`OWNER_TERMINAL` or `SUPERVISOR_RECEIPT`; there is no separate claim or required alias.  Each writer
fully constructs and signs its payload before the one no-replace publication, so a crash before
publication leaves the path absent and a crash after publication leaves a complete closure.  The owner
terminal body binds the exact opening hash; the supervisor-receipt body binds every preceding artifact
that exists.  If the owner exits after opening without a valid terminal, the
supervisor writes an `O_EXCL`, supervisor-signed `SUPERVISOR_RECEIPT` closure containing owner PID,
exit status, nonce, reason `OWNER_TERMINALIZATION_FAILURE`, and the hashable partial-artifact inventory;
that receipt permanently closes the namespace but is not a scientific result.  If storage failure
also prevents the supervisor receipt, the pre-existing opening is an immutable unterminated external
failure: every claim verifier must reject the namespace, and no retry or result claim is permitted.

The supervisor actually monitors from `SUPERVISOR_READY`, not only after opening: the launcher must
send the signed trigger within 60 seconds and the supervisor must then observe a valid owner handoff
and opening within the same deadline.  After a valid opening, a separate monotonic deadline of 28,800
seconds applies.  On expiry the supervisor terminates or kills the entire owner process group,
confirms group death, then re-reads and fully
verifies any owner terminal.  A valid terminal correctly bound to the complete chain remains the sole
closure.  Only when the closure is absent does the supervisor record
`postopening_timeout=true` and write `OWNER_TERMINALIZATION_FAILURE` with the partial inventory.  If
an invalid closure already occupies the path, it is immutable and claim-ineligible; it is never
replaced or supplemented.
the launcher dies, no valid trigger arrives, the owner
exits, or 60 seconds elapse before a valid opening appears, the
supervisor writes a signed `SUPERVISOR_RECEIPT` closure with reason
`PREOPEN_OWNER_FAILURE`, the authorization/ready/opening presence truth table, observed PIDs/statuses,
nonce, and partial inventory.  After a valid opening the reason changes to
`OWNER_TERMINALIZATION_FAILURE`.  Either closure permanently closes the authorized namespace.  Tests
must cover trigger timeout, owner exit before handoff, invalid handoff, invalid opening, a valid owner
terminal, invalid or missing terminal after opening, a live hung owner after opening, an owner that
writes a valid terminal immediately before the deadline but exits after it, pre-existing
valid or malformed receipts, and trigger/handoff/opening signature, replay, nonce, PID, and hash
mutations.  One strict verifier used by both the supervisor and post-result claim review must validate
exact schemas, signatures, key fingerprints, PIDs, nonces, transitive hashes, config/prepared/result
bindings, semantic decision recomputation, and atomic closure discrimination.  Its truth table must
require exactly one valid authoritative closure, and an owner terminal additionally requires the
complete authorization/ready/trigger/handoff/opening chain; any incomplete chain, unmatched opening,
invalid closure, or authorization without an eventual close
is claim-ineligible.

A nomination authorizes only drafting and adversarially reviewing a separately versioned v5 protocol.
It does not authorize accessing fresh data, model inference, or learned models.  V5 must name and hash
fresh sources before model inference, run label-only feasibility once, freeze the relational objects
and functional gates, and use a new namespace.  Learned models remain prohibited until a nonlearned
object passes recovery and edge-specific functional evidence on fresh data.

Before authorization, a five-replicate full-width benchmark runs every estimator/fold on the largest
synthetic panel without writing a scientific result.  It measures peak RSS and median wall time and
extrapolates the frozen scheduled cell count.  Authorization requires projected wall time at most six
hours on the recorded CPU, peak RSS at most 16 GiB, and projected artifacts at most 2 GiB.  The
implementation reuses fixed design matrices and fold indices but refits every required estimator per
replicate; parallelism is fixed at at most four source processes and one BLAS thread per process.

V4 order is: freeze plan/config/code/source hashes; adversarial plan review; tests, benchmark, and two byte-identical
smoke builds; exact-candidate diff review; signed authorization; create-once tmux run; deterministic
simulation and covariate study; write-once signed terminal; independent claim review; update `PAPER.md`
and its claim ledger.  No outcome-conditioned retry is permitted after authorization.

## Approach and alternatives considered

The design separates matching from estimation: matching establishes overlap and independent support,
while synthetic outcomes select an estimator without inspecting real representations.  This is
preferred to lowering v3's 500-pair or 100-component floors, which would retroactively rescue a failed
protocol, and to immediately using a flexible propensity model, which could manufacture apparent
overlap while hiding extrapolation.  Exact lexical matching was rejected because it changes the
scientific population to repeated lexical pairs and eliminates most true edges.  Searching additional
corpora under the current v3 matcher was rejected as outcome-informed source shopping.

## Milestones

- [ ] **M1 — Freeze and reference reproduction.**  Acceptance: immutable parent hashes pass; strict
  parser identities match; `exact_v3_reference` reproduces all eight v3 capped support rows exactly.
- [ ] **M2 — Matchers and diagnostics.**  Acceptance: unit tests cover core equality, morphology
  values, calipers, no reuse, deterministic tie breaking, component caps, balance, ESS, and failure
  cases; two independent builds are byte-identical.
- [ ] **M3 — Synthetic estimators.**  Acceptance: tests cover fold isolation, scaler fitting,
  component weights, propensity clipping, component-t interval construction, null/positive DGP identity, and
  decision truth tables; smoke mode finishes without model access.
- [ ] **M4 — Adversarial release review.**  Acceptance: independent reviewer returns SHIP for the
  exact config/code candidate and confirms no model/fresh-data/training path.
- [ ] **M5 — One-shot tmux run.**  Acceptance: launcher exports `CUDA_VISIBLE_DEVICES=-1`; exactly one
  authorization and owner nonce are created.  A preopening failure has no opening/run root and closes
  with one `SUPERVISOR_RECEIPT` closure.  An opened branch has exactly one opening and run root,
  followed by the single authoritative closure containing either a scientific owner terminal plus
  result, an owner technical terminal without a scientific result, or a post-opening supervisor
  receipt.  A crash before closure publication may leave the absent closure claim-ineligible; no retry
  or overwrite occurs.
- [ ] **M6 — Claims and successor boundary.**  Acceptance: independent post-result claim review,
  `PAPER.md` and claim-ledger update, and either a v5-plan authorization boundary or a permanent stop.

## Definition of done

- V3 and all earlier signed artifacts are byte-unchanged.
- The paper remains the main deliverable and does not imply that v4 tested representations.
- The v4 config, implementation, source files, tokenizer revision, environment, seeds, simulation
  DGPs, reports, and terminal are hash-bound.
- Exact v3 support is reproduced, all alternative methods are reported, and selection follows the
  frozen method/source/estimator order.
- No model weight, forward, activation endpoint, fresh corpus, optimizer, backward, checkpoint, or
  representation-training path is reachable from v4.
- The run is deterministic and tmux-launched; it ends in at most one complete authoritative owner or
  supervisor closure, while an absent, invalid, or externally unwritable closure is permanently
  claim-ineligible.
- A nomination is described only as permission to preregister v5; it is not a relational effect.

## Verification plan

- Plan: `/jumbo/lisp/f004ndc/.agent-workspace/bin/check-plan --path
  PLAN_RELATIONAL_MEASUREMENT_V4.md` and independent `/adversarial` review.
- Tests: `.venv-atlas/bin/python -m pytest -q` on the v4, v3, v2, and strict-parser suites;
  `.venv-atlas/bin/python -m py_compile` on every new Python file; `bash -n` on launcher/pipeline.
- Preservation: rehash the v3 terminal, pool, parser, exposure, Attempt-13/14 preservation, and
  architecture closure before authorization and after terminalization.
- Determinism: run smoke/scout twice into isolated roots and compare canonical reports byte-for-byte.
- Static isolation: AST/import/command scan fails on `AutoModel`, model loading/forward, CUDA use,
  optimizers, `.backward`, checkpoints, activation-cache paths, or unmanifested corpus paths.
- Reproducibility: record Python, NumPy, SciPy, scikit-learn, tokenizer, OS, and CPU
  inventory; set Python/NumPy seeds and deterministic hashes from config; use exact data hashes.
- Result: independently recompute support, balance, simulation gates, selection, and terminal decision;
  run a post-result claim review and `scripts/verify_paper_claims.py`.

## Risks and one-way doors

- **Synthetic DGP dependence:** passing simulations does not prove unconfounded real comparisons.
  The DGP suite therefore includes nonlinear interactions and component effects, and claims remain
  measurement-development only.
- **Coarsening residual confounding:** morphology values are no longer exact in `coarse_exact`.
  Hard balance gates and adjusted estimators are mandatory; a favorable support count cannot override
  failed balance.
- **Propensity overfit:** all transforms and propensity models are cross-fitted by component; positivity
  and weight-tail gates fail closed.
- **Large candidate graphs:** candidate caps and deterministic document partitioning bound memory;
  truncation counts are reported.
- **Outcome-informed succession:** v4 follows a known v3 support failure.  It is exploratory development,
  and only a new fresh-data protocol can support a relational claim.
- The v4 authorization is a one-way door: after it is written, code, config, gates, source order, or
  DGPs cannot change under the same namespace.
