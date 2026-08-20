# Canonical Induction Two-Tier v2 — Decoder Ceiling and External Upstream Set

## Goal

Determine whether the intervention stack can (Tier A) exactly reproduce a donor by patching the final residual state and (Tier B) recover a material fraction of that verified ceiling by patching the externally fixed Figure-2 upstream head set. This is a single-model technical study, not a representation-method benchmark.

## Constraints

- Preserve canonical induction v1.1 exactly as its signed `DEVELOPMENT_STOP`; do not change its 0.25 recovery or 0.15 selectivity gates, open its confirmation, add heads within its namespace, or relabel it.
- Bind a closed v1.1 preservation manifest covering its code/config/tests/launcher, prepared data, freeze/reviews/binding, complete runtime/provenance trees, post-result analysis/claim review, and exact C067--C069 paper-claim payloads.
- Update the paper narrowly: v1.1 found complete support, strong edge attention and joint ablation contribution, but materially insufficient donor recovery/selectivity; no SAE, projection, controller, or training was evaluated.
- Use fresh, algorithmically generated repeated-token panels and a new namespace. Current v1.1 development rows are opened and cannot nominate heads or thresholds; its sealed confirmation rows remain unparsed by this study.
- Tier A is a deterministic **decoder-tail identity ceiling**, not evidence that Tier-B head hooks work. It patches the final token immediately before `transformer.ln_f`; clean and sham patches must reproduce their complete donor logit vectors byte-exactly.
- Tier B uses the nine heads printed in the three upstream classes of Figure 2 of Wang et al. (2023), zero-based Layer.Head: duplicate-token `0.1, 0.10, 3.0`; previous-token `2.2, 4.11`; induction `5.5, 5.8, 5.9, 6.9`. Parenthesized/fuzzy membership for `0.10, 5.8, 5.9` is preserved rather than hidden. This is called the **externally fixed Figure-2 upstream head set**, not a complete random-token induction circuit.
- Freeze the published paper version, local PDF SHA-256, exact figure transcription, and indexing convention. No head is selected from v1.1 outcomes.
- The ordered nine-head same-layer control registry is fixed before inference and positionally paired to the circuit list: `0.0, 0.2, 3.1, 2.0, 4.0, 5.0, 5.1, 5.2, 6.0`. It is disjoint from the circuit registry and exactly matches every paired head's layer. Individual/class results are descriptive and cannot change the registry, thresholds, gate, or later head choice.
- Tier-B technical QA must pass before scientific classification: corrupt-to-corrupt all-position self-patches reproduce logits bitwise; registered head slices reproduce exactly; CPU sentinel tests prove layer/head indexing, exact outside-slice invariance, donor-row permutation detection, simultaneous disjoint-slice composition, and all-position zero semantics. A failure is technical-invalid, not circuit evidence.
- Report individual-head and class-wise recovery, joint recovery, joint-versus-individual additivity, joint ablation versus controls, centered full-vocabulary restoration, and collateral movement. Only the frozen nine-head joint set is gated.
- Normalize every target effect by the observed Tier-A ceiling effect on the same row. The primary material minimum is one-half of the ceiling with a 0.40 lower bound, prospectively chosen rather than fit to v1.1.
- Calibration uses frozen raw synthetic condition-level margins/logit vectors. It contains a known 0.60 joint ratio and 0.40 selectivity; a 0.10 negative; support, nonfinite, zero/negative-denominator, and exact below/equal/above cases for every gate; and a separate toy hook-integration fixture. Calibration must pass before freeze.
- Set `CUBLAS_WORKSPACE_CONFIG=:4096:8` before Python imports Torch. Freeze float32, eager attention, batch size 16, no padding, `eval`, inference mode, autocast off, TF32 off, highest float32 matmul precision, deterministic-algorithm error mode, model/cache hashes, and runtime CUDA/cuDNN/driver/device records.
- Freeze QA rows as stage row indices `0..15`. Two fresh interpreter processes independently load the model and serialized stage inputs, share no activation artifacts, and write exact arrays named `clean_logits`, `corrupt_logits`, `sham_logits`, `clean_circuit_heads`, `corrupt_circuit_heads`, `sham_circuit_heads`, `clean_control_heads`, `corrupt_control_heads`, `clean_final_residual`, and `sham_final_residual`. Before either QA process or the worker may load the model, it revalidates the exact attempt schema, launch/config/freeze/review binding, all non-confirmation frozen nodes, and stage-appropriate authorization; confirmation additionally validates its opened payload hash. Their arrays must be bitwise equal before the full worker starts; the full worker independently repeats the same QA once more and must be bitwise equal to **both** reference files for every named array.
- Confirmation is frozen but pre-gate runtime may not open, stat, parse, or recompute its payload hash. It becomes accessible only after recomputing and validating the complete development artifacts and gate hash.
- Even confirmation validates only this GPT-2 study. Representation methods and training are structurally absent; a future method benchmark requires a new freeze and at least two model families.
- Candidate and exact post-freeze `/adversarial` reviews must be first-line `SHIP` and hash-bound before launch.

## Frozen rows and paired estimands

Each row samples 18 unique token IDs. With sequence `x[0:16]`, alternate `a`, and sham alternate `s`:

- clean IDs: `x + x[0:15]`;
- corrupt IDs: `x[0:15] + [a] + x[0:15]`;
- sham IDs: `x[0:15] + [s] + x[0:15]`;
- final query position: 30; source-successor position: 15; target: `x[15]`; contrast: `a`; sham token: `s`.

Execution is fixed-length with no padding. Development and confirmation each contain 128 rows in eight 16-row blocks, use different seeds and disjoint token ranges, and are checked for exact prompt overlap with opened v1.1 development only.

For row `i`, define target margin `m_i(z)=z_i[target]-z_i[contrast]`. Behavioral eligibility requires finite logits, `m_i(clean)>0`, `m_i(corrupt)<0`, and `min(m_i(clean),-m_i(corrupt))>0.5`. Define the common positive ceiling denominator

`S_i = m_i(full_clean_patch) - m_i(corrupt)`.

The one common **gate cohort G is exactly** the set intersection of behavioral-eligible rows, rows with `S_i>1e-8`, and rows for which clean, corrupt, full-clean, circuit-clean, circuit-sham, control-clean, circuit-zero, control-zero logits and every derived gate field are finite. No additional or endpoint-specific filtering is permitted for gates. Every normalized effect uses this same denominator:

- clean circuit recovery `R_i=(m_i(circuit_clean)-m_i(corrupt))/S_i`;
- sham circuit recovery `H_i=(m_i(circuit_sham)-m_i(corrupt))/S_i`;
- control recovery `C_i=(m_i(control_clean)-m_i(corrupt))/S_i`;
- circuit selectivity `R_i-H_i`;
- circuit-control margin `R_i-C_i`;
- circuit ablation `A_i=(m_i(clean)-m_i(circuit_zero))/S_i`;
- control ablation `B_i=(m_i(clean)-m_i(control_zero))/S_i`;
- ablation advantage `A_i-B_i`.

The skyline recovery is `(m_i(full_clean_patch)-m_i(corrupt))/S_i=1`; its numeric gate is an implementation-consistency assertion, not independent scientific evidence. Conditions are paired within row before aggregation. At least 96 gate-cohort rows overall and 12 per block are required.

Point estimates are equal-weight means of eight block means over the common gate cohort. The paired hierarchical bootstrap uses 1,000 draws. Each draw samples eight blocks with replacement; for each sampled occurrence of block `b`, it independently resamples exactly `n_b` rows from that block's `n_b` gate-cohort rows. The same sampled row indices are reused for every condition and paired difference within that occurrence. Duplicate occurrences of one block receive independent within-block samples. The draw is the equal-weight mean of the eight resampled block means. For each exact registered endpoint field name, the seed preimage is the UTF-8 bytes of the ASCII string `"<base-10 global_seed>|<stage>|<endpoint>"`; take SHA-256 digest bytes `0:4` and convert with `int.from_bytes(..., byteorder="little", signed=False)`. Registered gate names are exactly `skyline_recovery`, `joint_recovery`, `selectivity`, `circuit_control_margin`, and `ablation_advantage`; descriptive endpoints use their exact serialized metric keys. Intervals use NumPy's linear 0.025 and 0.975 quantiles. Point minima are inclusive; lower-bound minima are strict.

## Tier A: decoder-tail identity ceiling

Capture clean and sham final-token residuals immediately before final layer normalization, transplant each into corrupt, and require:

- clean-patched logits byte-equal clean logits for every row;
- sham-patched logits byte-equal sham logits for every row;
- skyline recovery point at least 0.999999 and lower bound strictly above 0.99999.

This validates row alignment and decoder-tail patching only. It does not validate Tier-B head indexing or circuit completeness.

## Tier B: external Figure-2 upstream head set

Capture all-position pre-`c_proj` outputs for the nine external heads. Runs are explicit:

1. `circuit_clean`: clean donors patched into the corrupt base at all nine head slices and every token;
2. `circuit_sham`: sham donors patched into the corrupt base;
3. `control_clean`: clean donors from the nine same-layer control heads patched into corrupt;
4. `circuit_zero`: all nine circuit slices zeroed at every token in a clean base;
5. `control_zero`: all nine control slices zeroed at every token in a clean base;
6. nine individual clean-donor circuit patches and three frozen class-wise patches;
7. corrupt circuit/control self-patches for bitwise no-op QA.

The primary gate requires normalized joint recovery point at least 0.50 and lower bound above 0.40; selectivity point at least 0.25 and lower bound above 0.15; circuit-control margin point at least 0.25 and lower bound above 0.15; and ablation advantage point at least 0.05 with lower bound above zero.

Additivity is `joint clean-donor margin movement / sum(individual clean-donor margin movements)` on the paired row, undefined when the absolute sum is at most `1e-8`, and descriptive.

For each individual head or class condition `q`, descriptive normalized recovery is `I_i(q)=(m_i(q)-m_i(corrupt))/S_i` on `G` further intersected only with finiteness of `q`. Additivity is evaluated on `G ∩ {all individual fields finite} ∩ {|sum individual movements|>1e-8}`. Each individual, class, and additivity endpoint reports its exact per-block cohort counts and missingness. It receives an equal-block point and the line-55 paired interval if every block has at least one defined row; otherwise the endpoint is reported unavailable. None affects a gate.

## Full-vocabulary and collateral reporting

For logits `z`, define centered logits `c(z)=z-mean_vocab(z)`. Let `D_i=RMS(c(clean)-c(corrupt))`. For each `q` in `{full_clean, full_sham, circuit_clean, circuit_sham, control_clean}`, full-vocabulary restoration is

`V_i(q)=1-RMS(c(q)-c(clean))/D_i`.

For each such `q` and token `u` in `{target,contrast,sham}`, centered token movement is `T_i(q,u)=c(q)[u]-c(corrupt)[u]`. For each `q` in `{circuit_clean,circuit_sham,control_clean}`, collateral movement excludes those three token IDs and is

`K_i(q)=RMS(c(q)-c(corrupt))_other/max(abs(m_i(q)-m_i(corrupt)),1e-8)`.

Every `V`, `T`, and `K` endpoint is descriptive and has no gate. Its cohort is exactly `G` intersected with finiteness of the named condition and formula; `V` additionally requires `D_i>1e-8`. Each reports exact per-block cohort counts/missingness and receives an equal-block point and line-55 paired interval if every block has at least one defined row, otherwise it is unavailable. This avoids raw-logit constant-shift artifacts while not hiding sham-token movement.

## Synthetic and hook calibration

The frozen raw synthetic fixture supplies complete logits for clean, corrupt, full-clean, full-sham, circuit-clean, circuit-sham, control-clean, circuit-zero, and control-zero. The production evaluator must recover the registered positive values, reject the 0.10 circuit ratio, and return the exact registered decision for support failure, NaN/positive infinity/negative infinity, zero/negative denominator, total/per-block support boundaries, and raw point/lower-bound patterns. Because skyline recovery is algebraically one under its own denominator and some exact decimal equality values are not attainable after binary64 raw-margin subtraction, a separate frozen comparator oracle tests `below`, exact `equal`, and `above` for every inclusive point and strict lower threshold using adjacent representable binary64 values; it may test comparator semantics only and may not substitute for raw estimator calibration. A separate frozen tiny hook fixture has independently hand-authored expected arrays, and a toy module executes the production hook callback path to prove all-position capture, exact slice replacement/zeroing, row order, per-layer registry, simultaneous composition, and outside-slice invariance. Derived metric fields are not accepted as raw estimator calibration inputs. The calibration result records exact SHA-256 hashes of the evaluator/hook implementation, registered config, raw fixture, hook fixture, expected arrays, comparator oracle, and all result payloads. Candidate preflight reruns the raw, comparator, and hook fixtures through the then-current implementation and requires byte-identical outputs and decisions; any stale hash or result blocks freeze.

## Lineage and state machine

The frozen hash DAG is: source-registry/PDF + v1.1 preservation + paper/ledger snapshots + config + implementation + tests + launcher + prepared prescore/synthetic fixture + cache attestation + candidate SHIP -> freeze inventory -> frozen SHIP/binding -> development metrics/QA/reference/completion -> a create-once `DEVELOPMENT_COMPLETION_VALIDATED` marker binding the closed attempt and exact completion/summary hashes -> recomputed development gate -> authorized confirmation metrics/QA/reference/completion -> final. Gate publication and gate reconciliation must validate this marker before creating any gate journal, so a gate-invalid terminal can never precede a completed, controller-validated development stage.

Pre-gate verification checks every frozen artifact except the confirmation payload and does not stat it. Confirmation has two ordered phases implemented only by `authorize-confirmation`. Phase 1 verifies all non-confirmation freeze nodes, development completion artifact hashes, recomputed summary, exact gate hash, and the passing gate without statting the payload. Only after Phase 1 passes, Phase 2 stats and hashes the still-unparsed payload against its freeze-time size/digest. A create-once authorization artifact records both phase results and the payload size/hash. Only then may the confirmation controller parse rows, run the GPU guard, load the model, or start either QA interpreter. If the development gate stops, authorization instead writes a fixed `CONFIRMATION_BLOCKED` artifact with `payload_touched=false` and never stats the payload.

Classification precedence is frozen and ordered. First, any nonfinite value in **any live condition logit, captured registered slice/residual, or derived live field**, any donor byte-identity mismatch, any self-patch mismatch, any worker/reference mismatch, or any hook/indexing inconsistency is `TECHNICAL_INVALID_STOP`; live nonfinite rows may not be excluded through `G`. The finite clauses in `G` are defensive evaluator/calibration assertions for supplied synthetic rows. Second, after all technical checks pass, insufficient eligible/positive-denominator support or a finite Tier-A skyline-ratio gate failure is a scientific `*_SKYLINE_STOP`. Third, only after Tier A passes are finite Tier-B gate failures `*_UPSTREAM_SET_STOP`. Thus identical outputs have one outcome and byte-identity failure is never scientific evidence.

Runtime terminals while the registered launcher remains live:

The immutable-terminal guarantee covers caught command failures, timeouts, child-process death, and transition gaps that the still-live tmux launcher can reconcile while it retains the registered PID and GPU lock. An uncatchable launcher `SIGKILL`, host restart, or loss of the registered lock is outside that guarantee: no alternate command may impersonate the dead launcher, no scientific terminal may be promoted, and the stranded namespace is a technical incident requiring a separately versioned, analysis-only recovery protocol. This explicit boundary favors launch-token/lock integrity over an unsafe dead-launcher resume path.

- before creation of any stage or authorization attempt journal: `PRELAUNCH_BLOCK` (no result namespace and no scientific terminal; a post-freeze abort is recorded only in a separately versioned immutable recovery artifact and requires a new version); every incomplete created attempt is conservatively technical-invalid even if it died before its first forward;
- calibration failure before freeze: `CALIBRATION_BLOCK` (cannot freeze);
- runtime QA, lineage, timeout, nonfinite, hook-identity failure, or incomplete controller attempt after a possible forward: `TECHNICAL_INVALID_STOP` at the affected stage; it permanently blocks every later stage and is accepted by finalization as the immutable technical outcome;
- development Tier-A failure: `DEVELOPMENT_SKYLINE_STOP`;
- development Tier-A pass/Tier-B failure: `DEVELOPMENT_UPSTREAM_SET_STOP`;
- confirmation Tier-A failure: `CONFIRMATION_SKYLINE_STOP`;
- confirmation Tier-A pass/Tier-B failure: `CONFIRMATION_UPSTREAM_SET_STOP`;
- failure during development-gate publication after a completed development stage: `DEVELOPMENT_GATE_TECHNICAL_INVALID_STOP`, bound to a create-once gate-attempt journal; the launcher reconciles a closed-stage/missing-gate gap without rerunning scoring;
- failure during either confirmation authorization phase, including the gap before its phase checks: `CONFIRMATION_AUTHORIZATION_TECHNICAL_INVALID_STOP`, recording whether Phase 1 started/passed and whether the payload was accessed/statted/hashed; it is immutable and cannot be retried;
- both tiers pass both stages: `TWO_TIER_TECHNICAL_CONTROL_CONFIRMED`.

Any post-forward repair seals v2 and requires v2.1 with new namespace, panels, freeze, and reviews. Individual/class results cannot alter a terminal.

## Runtime scope firewall

Prepared-input, QA-reference, and scientific-result roots are distinct registered paths. QA references and their comparison live under the immutable provenance run root and never create the scientific stage result root. After the outer pre-gate checks, the locked tmux process atomically creates a launch manifest with random launch token, its PID, selected physical UUID, lock path/inode, and post-lock GPU evidence. Every forward- or state-writing runtime command requires `--launch-token <registered-hex>`, validates the live launcher PID, held UUID-lock inode/owner, `CUDA_VISIBLE_DEVICES==EXPECTED_GPU_UUID==manifest UUID`, and binds the manifest hash into every attempt/completion/gate/authorization/final record. The stage controller is then the sole public runtime orchestrator: before its first child process, it atomically creates a registered attempt record containing a random attempt token and stage. The internal QA/reference/worker commands additionally require that exact attempt token, matching parent controller PID, and expected next transition; direct calls without both tokens fail before model or payload access. It creates both independent references, compares them, then permits the worker only after validating the comparison artifact's registered hash. A partial attempt/reference/comparison artifact is create-once and non-resumable. The only legal reentry is `reconcile-stage`, which acquires the attempt lock, performs no forward or payload read, atomically writes the matching `TECHNICAL_INVALID_STOP`, closes the attempt, and prohibits further stage execution. The launcher invokes reconciliation when a controller exits without a closed attempt.

Development-gate publication and confirmation authorization first validate their immutable existing predecessors (the exact live launch plus the closed-development marker or published gate) before creating a transition journal. A failure in that pre-journal boundary has not started the transition, writes no transition namespace, and is handled by the still-live launcher's registered reconciliation command after the same immutable predecessor validates; only post-journal failures receive a transition technical-invalid terminal. Each create-once journal is written before lock acquisition or transition-specific lineage hashing. The gate journal advances through `VALIDATED` to `CLOSED_GATE_READY`; its result or technical-invalid terminal binds the final journal hash and token. `reconcile-development-gate` converts both a completed-development/missing-journal gap and a journal-without-terminal gap into a bound `DEVELOPMENT_GATE_TECHNICAL_INVALID_STOP` without scoring. Confirmation authorization first records `PRECHECK_JOURNALED` with `payload_accessed=false`; after acquiring the shared lock, the publisher must verify that exact state and its own recorded PID before it may record the launch/freeze/gate hashes and advance by expected-state transitions to `PHASE1_STARTED`. After Phase 1 it durably advances from that exact predecessor to `PHASE1_PASS_BEFORE_PAYLOAD_ACCESS`; before the first Phase-2 filesystem call it durably advances to `PHASE2_ACCESS_AUTHORIZED` and records that access may have occurred. Successful authorization closes the journal with the payload size/hash. A caught failure closes it as `CONFIRMATION_AUTHORIZATION_TECHNICAL_INVALID_STOP`. A missing or unclosed authorization journal after a published gate is handled only by `reconcile-authorization`, which shares the same lock, first creates the missing journal if necessary, requires any pre-existing authorizer PID to be dead, performs no payload access, conservatively records access according to the last durable state, emits that same immutable technical-invalid terminal, and prohibits retry. A journal synthesized by the current reconciler is exempt from its own liveness check.

All commands require the one registered config path; no alternate config or generic output-root flag is accepted. The exact command/state table is:

| Command and only legal arguments | Required predecessor | Create-once successor / reentry |
|---|---|---|
| `preservation-verify --config` | candidate/frozen/run, read-only | none; repeatable |
| `cache-preflight --config` | candidate, runtime absent | fixed cache attestation; existing exact payload may be reverified |
| `prepare --config` | prepared root absent | fixed prescore, stage payloads, raw calibration fixture; no reentry |
| `calibrate --config` | prepared complete, calibration absent | fixed calibration result; no reentry |
| `preflight --config --candidate` | prepared/calibration/cache/preservation valid; absent paths are exactly output root, provenance run root, GPU lock, freeze, binding, and candidate-preflight attestation | reruns both calibrations with current implementation, requires all recorded hashes and byte-identical outputs/decisions, and writes fixed `CANDIDATE_PREFLIGHT_ATTESTATION.json` binding their current hashes/results; no reentry |
| `preflight --config --pre-gate` | freeze/binding valid; absent paths are exactly output root, provenance run root, and GPU lock (immutable candidate/binding/cache provenance is expressly allowed) | none; repeatable; never stats, hashes, opens, or parses confirmation payload |
| `freeze --config` | candidate SHIP, calibration pass, exact current candidate-preflight attestation, runtime/freeze absent | revalidates attestation hashes and reruns both calibrations before atomically writing fixed freeze; no reentry |
| `verify-freeze --config --pre-gate` | freeze exists | none; repeatable; never stats, hashes, opens, or parses confirmation payload |
| `bind-review --config` | freeze plus exact candidate and frozen first-line `SHIP` reviews exist, binding absent | fixed review binding containing all three hashes; no reentry |
| `review-binding --config` | binding exists | validates only binding bytes/hash, freeze-inventory digest, reviews, and all non-confirmation bound nodes; it traps/fails any confirmation-path `open`, `stat`, or hash call; none; repeatable read-only verifier |
| `qa-reference --config --stage development\|confirmation --replicate 1\|2 --launch-token <registered-hex> --attempt-token <registered-hex>` | internal-only: matching live launch and controller attempt token/PID/lock/UUID and next transition; binding valid; registered QA-reference file and scientific stage root absent; confirmation additionally requires a valid two-phase passing authorization | one registered provenance `qa/<stage>/QA_REFERENCE_<replicate>.npz`; advances attempt transition; no reentry or arbitrary output path |
| `qa-compare --config --stage development\|confirmation --launch-token <registered-hex> --attempt-token <registered-hex>` | internal-only: matching live launch and controller attempt token/PID/lock/UUID and next transition; both registered reference NPZs exist, comparison/stage result absent | bitwise validates every named array and writes one registered `qa/<stage>/QA_COMPARISON.json` with reference hashes; advances attempt transition; no reentry |
| `worker --config --stage development\|confirmation --launch-token <registered-hex> --attempt-token <registered-hex>` | internal-only: matching live launch and controller attempt token/PID/lock/UUID and next transition; binding/freeze and registered QA comparison validate; scientific stage root absent; confirmation additionally requires a valid passing authorization | fixed scientific stage completion candidate; controller moves to `WORKER_COMPLETE_PENDING_VALIDATION`, validates the exact candidate, and only then closes; any failure is stage technical-invalid; no reentry |
| `stage-controller --config --stage development\|confirmation --launch-token <registered-hex>` | matching live launch token/PID/lock/UUID, binding valid, and all stage attempt/QA/scientific outputs absent; confirmation additionally requires a valid passing authorization | atomically creates the registered attempt before spawning only the two registered `qa-reference` processes, `qa-compare`, then `worker` in order; after worker return it validates exact completion while pending and only then writes `CLOSED`; development then idempotently publishes `DEVELOPMENT_COMPLETION_VALIDATED` binding that closed attempt and exact completion/summary; any earlier failure is stage technical-invalid; no reentry |
| `reconcile-stage --config --stage development\|confirmation --launch-token <registered-hex>` | matching live launch plus either (a) one existing incomplete attempt whose controller PID is dead and no validated `CLOSED` completion, allowing a `COMPLETE.json` candidate from any pre-`CLOSED` state, or (b) development state `CLOSED` with exact valid completion and a missing/exact marker | under an exclusive attempt lock, performs no forward/payload access; case (a) atomically orphans any unvalidated completion candidate so it can never be promoted and writes one fixed stage technical-invalid terminal; case (b) idempotently validates/publishes the missing marker, while an invalid closed completion becomes stage technical-invalid; repeat calls only verify the matching terminal or exact marker |
| `development-gate --config --launch-token <registered-hex>` | matching live launch and exact `DEVELOPMENT_COMPLETION_VALIDATED` predecessor; gate journal/result absent | validates the predecessor before journal creation, then writes the journal before transition-specific checks/locking and publishes a fixed gate result binding its final hash/token; any caught post-journal failure closes with gate technical-invalid; no reentry |
| `reconcile-development-gate --config --launch-token <registered-hex>` | matching live launch, exact `DEVELOPMENT_COMPLETION_VALIDATED` predecessor, and missing/incomplete gate terminal; any pre-existing gate-controller PID must be dead | validates the predecessor before creating a synthetic journal, then under the same exclusive lock performs no scoring or model forward and closes one fixed gate technical-invalid terminal; a synthetic journal is exempt from its own liveness check, a live publisher is rejected, and expected-state transitions prevent dual terminals; repeat calls only validate the terminal |
| `authorize-confirmation --config --launch-token <registered-hex>` | exact validated live launch and exact published development gate, authorization journal/terminal absent | validates those predecessors before journal creation, creates the journal, then on pass performs ordered Phase 1/Phase 2 and closes with fixed authorization; on development stop closes with fixed blocked artifact; on caught post-journal failure closes with fixed authorization technical-invalid terminal; no reentry |
| `reconcile-authorization --config --launch-token <registered-hex>` | exact validated live launch and exact published development gate plus missing/incomplete authorization journal and no authorization terminal; any pre-existing authorizer PID must be dead | validates both predecessors before writing state, then under the shared authorization lock performs no payload access; creates a missing journal if needed (the synthetic journal is exempt from the liveness check), closes it and a fixed authorization technical-invalid terminal conservatively; a live publisher is rejected and exact expected-state transitions prevent dual terminals; repeat calls only verify identical closed terminal |
| `final --config --launch-token <registered-hex>` | matching live launch, final absent, and exactly one of (a) validated development technical-invalid terminal, (b) validated development completion plus gate technical-invalid, (c) validated development scientific stop plus matching `CONFIRMATION_BLOCKED`, (d) validated development completion and gate result (PASS or STOP) plus validated confirmation-authorization technical-invalid terminal, (e) validated development pass plus validated confirmation technical-invalid terminal, or (f) validated development pass plus matching validated confirmation completion | fixed final result binding launch manifest and repeating the exact immutable outcome; prohibits every later stage; no reentry |

Any other flag (including plain/full runtime `preflight` or `verify-freeze`), path, stage, repeat, predecessor, transition, command, or unexpected result file fails closed. A command encountering its own existing terminal cannot resume or overwrite except the read-only closed-terminal verification allowed for `reconcile-stage`. The only legal pre-authorization runtime verification forms are the explicit `--pre-gate` forms. Confirmation-capable invocations require the internally validated authorization artifact and gate hash. Runtime scope assertions require `representation_methods=false`, `training=false`, and `automatic_method_authorization=false`; completion/gate/final records repeat those fields. The launcher is an explicit state dispatcher: pre-gate checks -> development controller; if its validated outcome is technical-invalid, `final` immediately; otherwise development gate -> authorization/block; if authorization is technical-invalid or blocked, `final` immediately; otherwise confirmation controller; whether confirmation completes or is technical-invalid, `final` immediately. A crashed child/controller is reconciled before dispatch only while the registered launcher remains live; abrupt launcher/host loss invokes the explicit stranded-namespace boundary above. A development-stop branch never runs the confirmation stage controller; when normal blocking completes, `final` verifies only the auditable claim `registered_code_path_accessed_confirmation_payload=false` plus the blocked artifact and freeze-time metadata, without asserting external byte integrity and without statting the payload. If authorization itself is interrupted after a STOP gate, its technical-invalid terminal takes precedence and remains distinct from the underlying scientific STOP.

The launcher considers a GPU available only when `nvidia-smi` reports zero compute processes, memory used below 2,048 MiB, and utilization below 10%. It acquires an atomic UUID-scoped `flock` under `/tmp/msae-gpu-locks`, reruns both checks after locking, records before/after evidence and the physical-index-to-UUID mapping, and holds the lock for the tmux session lifetime. A failed recheck releases the lock and tries the next device.

## Milestones

- [x] Preserve v1.1 and update PAPER/claim ledger narrowly.
- [ ] Implement panels, raw calibration, Tier-A ceiling, Tier-B external-set/control interventions, full-vocabulary metrics, technical QA, gates, lineage, and one-shot launcher.
- [ ] Obtain candidate and frozen `/adversarial: SHIP`, bind, and launch tmux jobs on one free UUID-pinned GPU.

## Verification plan

- Unit tests for row formulas/freshness, exact nine-head registry, PDF binding, raw positive/negative/boundary calibration, denominator/nonfinite/support policy, equal-block paired bootstrap, residual and all-position head hooks, full-vocabulary equations, all gates/state terminals, independent-process QA comparison, lineage tampering, confirmation-before-load firewall, timeouts, unexpected artifacts, and duplicate namespaces.
- Python compile, shell syntax, paper claim verification, exact v1.1 preservation, cache/model hashes, prepared-data verification, and freeze verification.
- Candidate and exact frozen adversarial reviews before any real forward.

## Definition of done

### Implementation and launch completion

- [ ] V1.1 trees, freeze inventory, terminals, analysis, claim review, and C067--C069 payloads verify exactly.
- [ ] PAPER and ledger report v1.1 without method-level overclaim.
- [ ] Raw synthetic estimator fixtures and toy hook integration pass every positive, negative, boundary, support, and nonfinite oracle before freeze.
- [ ] Fresh stages contain 128 rows in eight blocks, no stage overlap, and no overlap with opened v1.1 development.
- [ ] Hook and independent-process QA tests cover residual and all-position head capture/replacement/zero semantics.
- [ ] Candidate and exact frozen reviews are SHIP and hash-bound.
- [ ] The one registered tmux session `msae_induction_two_tier_v2` is live or already cleanly terminal, with its shell PID, selected free physical GPU UUID, held UUID lock, active controller attempt artifact (once the first controller begins), and fixed log `reports/provenance/canonical_induction_two_tier_v2_run_20260809/launcher.log` observable; its single state-dispatched chain follows the runtime firewall and reconciles incomplete controller attempts before finalization. No method/training starts.

### Scientific completion

- [ ] If the registered launcher remains live through terminalization, a lineage-valid final terminal records exactly one frozen state-machine outcome. This is assessed after the requested launch handoff and is not required before returning control to the user; abrupt launcher/host loss instead leaves a non-promotable technical-incident namespace as specified above.

## Risks

- The requested second tier allowed either a known ground-truth small model or an externally fixed more-complete circuit description. This v2 prospectively chooses the latter as an accepted scope decision: the nine-head set is complete only as a transcription of the three upstream classes in the cited IOI diagram; it is not guaranteed to be the complete random-token induction mechanism. A Tier-A pass/Tier-B failure localizes the result to this upstream set/site, not to patching or linear control generally, and even a pass is only upstream-set coverage rather than proof of a complete GPT-2 induction circuit.
- Tier A is intentionally tautological decoder-tail identity. It validates that narrow path only; Tier-B self-patch and sentinel QA separately validate head plumbing.
- Whole-sequence head replacement is stronger than v1.1 final-token replacement and is reported as a distinct intervention.
- Same-layer controls are not function-matched. Sham donors, self-patches, ablation comparison, and the ceiling supplement but do not eliminate that limitation.
- Full-vocabulary collateral metrics may penalize legitimate copying and remain descriptive.
- One model and generated task limit generality. Success is technical validation only; failure is local.

## One-way doors

The v1.1 namespace stays sealed. The v2 freeze and first GPT-2 forward are one-way. Any development stop permanently seals v2 confirmation. Any post-forward repair requires v2.1. No v2 outcome automatically launches or authorizes representation methods or training.
