# PLAN — MSAE independent measurement v3 post-M9 gen9

Status: prospective successor after gen8 failed before changed-region publication.

## Goal

Complete the already-designed MSAE v3 calibration-only successor without
weakening any scientific, quarantine, source-only, authorization, containment,
capability, setup, M4, prescore, signing, nonce, GPU-lease, or terminal-state
contract. Gen9 exists only because the reviewed gen8 structural change policy
cannot route its registered supervisor command to the permitted new execution
function.

The immediate goal is a mechanically implementable, independently reviewed
control-plane boundary. The eventual goal remains exactly one authorized
calibration run whose Stage-B evidence is durable before any result is treated
as scientific output.

## Non-goals

- Do not read, hash, copy, map, parse, or otherwise inspect the contents of:
  - `data/atlas_v1/private/final.jsonl`;
  - `data/atlas_v1/private/final.records.jsonl`; or
  - `data/atlas_v1/private/final.units.jsonl`.
  Only no-follow metadata inspection is allowed.
- Do not query a GPU, import/call a model, create a scientific tmux session,
  create protocol/M3/M4/signature/authorization/nonce/run state, run
  confirmation scoring, or run Stage C while implementing or reviewing this
  plan.
- Do not reinterpret gen8 as passing. Do not mutate its reviewed plan, plan
  review, or failure review.
- Do not change the scientific Stage-A/Stage-B definitions inherited from the
  frozen lineage.

## Frozen predecessor and honest gen8 failure

Gen8's reviewed plan and later implementation-fit failure are both immutable:

- plan:
  `docs/plan-msae-independent-measurement-v3-post-m8-gen8.md`, SHA-256
  `7bd04a1c466d6a7e5cd6e570eece4e9a19395bf90d5b1e7cf2e4486616c2dfb4`,
  mode 0644;
- plan review:
  `reports/adversarial/msae_independent_measurement_v3_post_m2_gen8_plan.md`,
  SHA-256
  `1a7dd1752694599322c80ad2d7e7bd03d306f7d618198a4cc6cd25a8f72720b1`,
  mode 0644;
- failure review:
  `reports/adversarial/msae_independent_measurement_v3_post_m2_gen8_failure.md`,
  SHA-256
  `45cc9dff4479b9a4a30eb6a84157e786a3e5736751cf0c1564b75f07c1739191`,
  mode 0644.

The frozen failed implementation subject is:

| entry | path | mode | SHA-256 |
|---|---|---:|---|
| controller | `scripts/msae_independent_measurement_v3_post_m2_gen8.py` | 0644 | `30678b56e9304a8c3837cb03138e0993948865f582bb3a61fa7d5fae998434ce` |
| runtime | `scripts/msae_independent_measurement_v3_post_m2_gen8_runtime.py` | 0644 | `0b873cdd2519c532677793d0c1acb0a823512ccd225da84c171fdeeebf46f46d` |
| runner | `scripts/run_msae_independent_calibration_v3_gen8.py` | 0644 | `76b1b6b25cbbc139bab3c17a4dcf763bac113e934cc8f6afcf2ee2658afd6706` |
| launcher | `scripts/launch_msae_independent_calibration_v3_gen8.sh` | 0755 | `149d15cdfaad1ad02ac7a4c00ccb09e7586394a9801fe5bd8073ce0e6f1e8236` |
| tmux supervisor | `scripts/run_msae_independent_measurement_v3_post_m2_gen8_tmux_test.py` | 0644 | `e15abdbf07172f3bca865ddb4a45bbc2105aa575df60555decb20384bd97a9d2` |
| RFC | `docs/rfc-msae-independent-measurement-v3-post-m8-gen8.md` | 0644 | `e210ff486cf4547d40f29b264472399109c590aa0c4a928829d291a0c9f7a9cc` |
| tests | `tests/test_msae_independent_measurement_v3_post_m8_gen8.py` | 0644 | `82f561ad8b95a178fa550a519c84be2efdb2084e748449e26f65e6ffa35d3b24` |

Those bytes are evidence, not authorization and are never used as comparator
baseline. Gen9 is generated from the last trusted source subject, frozen gen7:

| entry | path | mode | SHA-256 |
|---|---|---:|---|
| controller | `scripts/msae_independent_measurement_v3_post_m2_gen7.py` | 0644 | `4c10f5b5bc18ad4ae3828de5b6cebdf32e65c5ddf1f7acdec1aa2a1f8ad99ef9` |
| runtime | `scripts/msae_independent_measurement_v3_post_m2_gen7_runtime.py` | 0644 | `017862e1c433d45fea4e91b60e2f23a62084a1f2c8200a1a8222fddfa7a125bc` |
| runner | `scripts/run_msae_independent_calibration_v3_gen7.py` | 0644 | `c28bec9c4d2c4be61ba0bd6a87df81e9c33a6a196bfecc5a4b778ecc9189df91` |
| launcher | `scripts/launch_msae_independent_calibration_v3_gen7.sh` | 0755 | `21519cf92d0ed1d91d9ac4ad0caa2178cc80572624401952afe629b6fba6ba4b` |
| tmux supervisor | `scripts/run_msae_independent_measurement_v3_post_m2_gen7_tmux_test.py` | 0644 | `cd85077c33b283a5c2bfb767632d5ee29c59d3b16f6f0652e0802393a4fae6a7` |
| RFC | `docs/rfc-msae-independent-measurement-v3-post-m7-gen7.md` | 0644 | `857620e5df9be77aef2315816d9f16b6c1cad885eafcd9b8baf96db0af496f59` |
| tests | `tests/test_msae_independent_measurement_v3_post_m7_gen7.py` | 0644 | `c99fdef8f6ff505986aa81e2dbbf8da0f8f840e232fe1ee7c3c36ea800df258e` |

The structural manifest independently rehashes both tables: gen7 is the sole
trusted code baseline; gen8 is an exact failed historical subject. No gen8 byte
can become authorized merely because gen9 leaves it unchanged.

Gen8 terminal facts are:

- `changed_regions.json`, pre-containment review, containment transaction and
  report, pre-capability review, capability transaction and report,
  implementation review, M3, M4, prescore evidence/review, signature,
  authorization, nonce consumption, and run state were not created;
- no gen8 capability, setup, M4, signing, authorization, launch, model, GPU,
  or scientific tmux action ran;
- the failure is the single critical implementability blocker in the frozen
  failure review;
- the plan-authorized real-tmux containment command did not run for gen8;
- the quarantined payload content-read count remains zero.

Gen9 setup predicts and then publishes create-once `failed_gen8.json`, schema
`msae_v3_gen9_failed_gen8_evidence_v1`. Its exact top-level keys are
`schema_version`, `protocol_id`, `generation`, `writer_generation`, `status`,
`terminal_fields`, `frozen_subject`, `failure_review`, `blockers`, `checks`,
`namespace_absence`, `sealed_payload_metadata`, and `gen9_plan_authority`.

- `protocol_id="msae_independent_measurement_v3"`, `generation="gen8"`,
  `writer_generation="gen9"`, and `status="failed_before_changed_regions"`.
- `terminal_fields` has these exact ordered keys/values:
  `changed_regions`, `pre_containment_review`, `containment_report`,
  `pre_capability_review`, `capability`, `implementation_review`, `m3`, `m4`,
  `stage_a`, and `authorization` equal `not_created`; `gpu_query`,
  `model_call`, `calibration`, `confirmation`, and `stage_c` equal `not_run`.
- `frozen_subject` has exact ordered keys `plan`, `plan_review`, `controller`,
  `runtime`, `runner`, `launcher`, `tmux_test_supervisor`, `rfc`, `tests`, and
  `failure_review`. Rows have exact keys `path`, `type`, `mode`, `uid`, `gid`,
  `nlink`, `size`, `sha256`, and `verification_action`; they require the literal
  paths/digests/modes above, current UID/GID, regular nlink-one files, and
  `verification_action="content_rehash"`.
- `failure_review` has exact keys `path`, `sha256`, `verdict`, `blocker_count`,
  and `origin`; values are the literal frozen path/digest, `BLOCK`, integer one,
  and `not_stated_in_failure_review`.
- `blockers` is a one-row array. Its row has exact keys `ordinal`, `severity`,
  `citation`, `one_line`, and `failure_review_sha256`; values are integer one,
  `critical`,
  `docs/plan-msae-independent-measurement-v3-post-m8-gen8.md:378-390; scripts/run_msae_independent_measurement_v3_post_m2_gen7_tmux_test.py:1779-1780; scripts/msae_independent_measurement_v3_post_m2_gen8_runtime.py:4360-4378`,
  `The reviewed supervisor change map cannot produce the registered executable gen8 entrypoint.`,
  and the frozen failure-review digest. The `one_line` source is exactly the
  raw `ONE-LINE:` control (including LF) whose SHA-256 is
  `8da9f2ada119de86d61c039f8aff2291a782a9f97f3f604bd56cb8b126a23c01`.
  A second/missing/changed blocker or control blocks.
- `checks` has exactly these ordered IDs:
  `frozen_subject_rehash`, `honest_entrypoint_comparator`,
  `permitted_main_insertion_comparator`, `gen8_analysis_absence`,
  `sealed_metadata_lstat`, and `prohibited_action_attestation`. Rows have exact
  keys `id`, `evidence_class`, `subject_sha256`, `argv`, `cwd`, `environment`,
  `started_utc`, `ended_utc`, `transcript_sha256`, `transcript_available`,
  `exit_code`, `summary`, and `details`. Evidence class is
  `primary_audit_current_subject`; subject digest is the failure-review digest;
  `argv`, `cwd`, `environment`, both timestamps, transcript digest, and exit
  code are JSON null; transcript availability is false. `details` has exact
  keys `source_line_sha256` and `fact`. The six `(summary, fact,
  source_line_sha256)` triples are, in ID order:
  1. (`matched_frozen_controls`, `reviewed plan and plan-review digests matched`,
     `72f149f6a4b458483ae187fa282f1d17c0f09ba55b182bbd1dd66caf97025ec9`);
  2. (`rejected_function_main_gen8_matrix`, `honest function/call replacement was rejected`,
     `ac99fcdd69fbea0c5ad4feb3bfd99271bc2c0b25b8b7833276803b7c1e0a0800`);
  3. (`rejected_statement_if`, `permitted-main insertion shifted and rejected the executable statement`,
     `ac99fcdd69fbea0c5ad4feb3bfd99271bc2c0b25b8b7833276803b7c1e0a0800`);
  4. (`analysis_root_absent`, `gen8 analysis root and one-way evidence were absent`,
     `5540d80fcea5acadbc2cb8ff588f4e2ab4eeb14bf7b2bc84144dd0f6de4a4aed`);
  5. (`metadata_only_zero_reads`, `quarantined payload contents were not accessed`,
     `85b36a07c3e4d39abdc433e6ac35b521912ab83838c19927b7a5bb7c0014a5a1`);
  6. (`prohibited_actions_not_run`, `no listed scientific or one-way action ran`,
     `4f98de2170155a93bede7c06823546ada915eb81cb46ad45566ef209fd0333fc`).
  No command, timestamp, transcript, or zero exit code is invented.
- `namespace_absence` is path-sorted rows with exact keys `path`, `expected`,
  `lexists`, `kind`, and `phase`. The exact-path registry is the literal value
  of these frozen-gen8 constant names (aliases resolving to the same path are
  one row): `PRE_CONTAINMENT_REVIEW`, `PRE_CAPABILITY_REVIEW`,
  `IMPLEMENTATION_REVIEW`, `POST_M3_REVIEW`, `PRESCORE_REVIEW`,
  `CONTAINMENT_ANALYSIS_ROOT`, `CHANGE_MANIFEST`,
  `CHANGE_MANIFEST_TRANSACTION`, `CONTAINMENT_REPORT`,
  `CONTAINMENT_TRANSACTION`, `CAPABILITY_TRANSACTION`, `CAPABILITY_REPORT`,
  `CAPABILITY_PROBE_ROOT`, `ACTIVE_CONFIG`, `ACTIVE_PROV`, `ACTIVE_M4_DATA`,
  `M4_TRANSACTION`, `SETUP_JOURNAL`, `SETUP_MANIFEST`,
  `SETUP_KEY_TRANSACTION`, `ACTIVE_PRIVATE_KEY`, `ACTIVE_STATE`,
  `ACTIVE_NONCE_DIR`, `ACTIVE_RUN_ROOT`, `M4_PRIMARY`, and `M4_REBUILD`.
  The verifier additionally enumerates the absent `ACTIVE_RUN_ROOT` parent
  prefix and rejects any gen8-named sibling, thereby covering sign/intent/log/
  terminal children without inventing nonexistent child rows. Closed-family
  rows cover all seven `m8t_/m8b_/m8p_/m8x_/m8a_/m8c_/m8s_` prefixes. Values
  are `absent`, false, `exact_path|closed_family`, and
  `failed_before_changed_regions`. The present plan, plan review, seven files,
  and failure review occur only in `frozen_subject`, never this array.
- `sealed_payload_metadata` has exact keys `content_read_attempts`, `before`,
  and `after`; reads are zero. Before/after maps contain only the three literal
  quarantined paths. Rows have exact keys `path`, `type`, `mode`, `uid`, `gid`,
  `nlink`, `size`, `device`, `inode`, `ctime_ns`, and `mtime_ns`; maps
  byte-equal.
- `gen9_plan_authority` has exact keys `plan_path`, `plan_sha256`,
  `plan_review_path`, and `plan_review_sha256` and binds the reviewed gen9 plan.

One builder constructs those typed bytes. A separate verifier does not call the
builder: it independently reparses the failure review, rehashes the ten frozen
files, enumerates the literal exact-path/family table, and repeats quarantine
metadata under the content-open tripwire. Exact canonical byte equality is
required before the first setup write. Any unknown/duplicate/missing fact or
downstream gen8 state blocks.

## Canonical gen9 files and namespaces

The seven prospective implementation files are:

1. `scripts/msae_independent_measurement_v3_post_m2_gen9.py`;
2. `scripts/msae_independent_measurement_v3_post_m2_gen9_runtime.py`;
3. `scripts/run_msae_independent_calibration_v3_gen9.py`;
4. `scripts/launch_msae_independent_calibration_v3_gen9.sh`;
5. `scripts/run_msae_independent_measurement_v3_post_m2_gen9_tmux_test.py`;
6. `docs/rfc-msae-independent-measurement-v3-post-m9-gen9.md`; and
7. `tests/test_msae_independent_measurement_v3_post_m9_gen9.py`.

Reviews are these exact create-once mode-0644 regular files:

- `reports/adversarial/msae_independent_measurement_v3_post_m2_gen9_plan.md`;
- `reports/adversarial/msae_independent_measurement_v3_post_m2_gen9_pre_containment.md`;
- `reports/adversarial/msae_independent_measurement_v3_post_m2_gen9_pre_capability.md`;
- `reports/adversarial/msae_independent_measurement_v3_post_m2_gen9_implementation.md`;
- `reports/adversarial/msae_independent_measurement_v3_post_m2_gen9_post_m3.md`;
- `reports/adversarial/msae_independent_measurement_v3_post_m2_gen9_prescore.md`.

Pre-capability evidence lives only under mode-0700
`reports/analysis/msae_independent_measurement_v3_post_m2_gen9/` with exact
children `changed_regions.json`, `tmux_containment.json`,
`gen9_capability_reproduction.json`, and the three exact hidden transaction
directories and child registries inherited from the gen8 plan after ordered
substitution. All final/transaction files are mode 0600, current UID/GID,
nlink one except the exact publisher pair state.

Production short families are `/tmp/m9t_`, `/tmp/m9b_`, `/tmp/m9p_` and test
families are `/tmp/m9x_`, `/tmp/m9a_`, `/tmp/m9c_`, `/tmp/m9s_`. Every family
uses the exact 64-lowerhex token and suffix/type from gen8. Every gate closes
all seven families, not merely named expected paths.

## Ordered baseline and plan substitutions

For each frozen gen7 implementation source, apply these replacements globally
and in order:

1. `post_m7_gen7→post_m9_gen9`;
2. `post-m7-gen7→post-m9-gen9`;
3. `msae-independent-v3-gen7→msae-independent-v3-gen9`;
4. `m7t_→m9t_`, `m7b_→m9b_`, `m7p_→m9p_`, `m7x_→m9x_`,
   `m7a_→m9a_`, `m7c_→m9c_`, and `m7s_→m9s_`, in that order;
5. `Gen7→Gen9`;
6. `gen7→gen9`.

Each source token is applied once to the output of the previous row. Any
remaining gen7/m7 successor token or double substitution blocks. The resulting
trusted bytes are baseline `B9`.

The phrase **standard gen8→gen9 plan substitutions** means this separate exact
ordered map, used only to render inherited plan clauses: `post_m8_gen8` to
`post_m9_gen9`, `post-m8-gen8` to `post-m9-gen9`,
`msae-independent-v3-gen8` to `msae-independent-v3-gen9`, each m8 family to its
m9 peer in t/b/p/x/a/c/s order, then `Gen8→Gen9`, then `gen8→gen9`.

## Corrected structural change authority

The gen8 defect is closed mechanically, not by an import-time rebinding trick.
The gen9 comparator parses `B9` and candidate `C9` with the frozen stdlib AST.
Top-level keys are:

- function, async-function, class, and simple assignment:
  `(node_kind, defined_or_assigned_name, zero_based_same_name_occurrence)`;
- every other statement:
  `(statement:<AST-class>, normalized_AST_SHA256,
  zero_based_same_digest_occurrence)`.

Normalized statement AST excludes location attributes but includes every
semantic field. Inserting an allowed definition therefore does not rename an
unchanged bottom `if __name__ == "__main__"` statement. Changing that
statement changes its digest and blocks. Duplicate named definitions or simple
assignments block. Bytes between allowed source segments must remain exact
baseline bytes apart from whitespace that is consumed as the prefix of a new
allowed definition.

The controller, runner, and launcher must equal `B9` byte for byte.

Runtime may change only the exact gen8 regions already enumerated in the frozen
gen8 plan, after gen9 substitution, plus:

- `R9_FAILURE`: replace the gen7-baseline failure builder with exact
  `FAILED_GEN8_*` constants, failed-gen8 builder, and independent verifier;
- `R9_CHANGE_POLICY`: `_normalized_gen9_baseline_bytes`,
  `_normalized_top_level_node`, `_gen9_changed_region_rows`, and
  `_gen7_to_gen9_change_manifest` implement this corrected keying, trusted
  gen7 baseline, and separate frozen gen8 failure subject;
- `R9_CONSTANTS`: exact gen9 paths, current plan/review pins, static/site
  digests, public entry tuple, substitutions, and literal policy table;
- `R9_SETUP` and `R9_CLOSURE`: replace `failed_gen7.json` with
  `failed_gen8.json` and carry the gen8 failure review as a frozen local input;
- every function in the exact gen8 runtime region map at frozen-plan lines
  331–368 may be added/changed after the standard plan substitutions, but only
  under that same named region and the canonical rendered contracts below.

Supervisor changes are limited to the substituted gen8 map
`_g9_case_table`, `_g9_process_row`, `_g9_boundary_event`,
`_g9_validate_boundary_event`, `_g9_owner_result`,
`_g9_validate_owner_result`, `_g9_outer_result`, `_g9_attempt_descriptor`,
`_g9_case_start_record`, `_g9_case_journal`,
`_g9_recover_interrupted_attempt`, `_g9_publish_report`, `_g9_run_case`,
`_g9_run_all`, `_g9_emergency_containment`, and the **actual inherited
executable definition** `main_gen9_matrix`.

The bottom executable statement remains byte-exact after substitution and
continues to call `main_gen9_matrix()`. The comparator must accept insertion of
the listed helpers plus replacement of that function and must reject changing
the bottom call, adding a second executable statement, leaving any helper dead,
or changing any unlisted predecessor function. New/changed definitions have no
decorators and no default/annotation expressions with calls, comprehensions,
attribute writes, walrus assignments, or other evaluation side effects.
Import-time rebinding of `main_gen9_matrix`, `globals()`/`locals()` mutation,
monkeypatching a predecessor function, or a default/decorator side effect is a
hard failure.

The RFC and tests are complete exact-byte review subjects. They are never
treated as proof of scientific equivalence.

The canonical changed-region manifest is the gen8 schema after substitution,
but its `baseline_subjects` is the exact trusted gen7 seven-entry table above;
the frozen gen8 table is carried only by `failed_gen8.json` and later review
bindings. Its comparator-policy object contains the stable statement-key rule. A
regression must:

1. insert every registered new helper before `main_gen9_matrix` and show the
   unchanged bottom statement retains the same key;
2. change `main_gen9_matrix` and show its one allowed row;
3. change the bottom call and require rejection;
4. add a decorator/default side effect and require rejection;
5. modify bytes immediately outside each allowed node and require rejection;
6. update a literal allowlist/hash in memory and still require semantic
   rejection of the forbidden mutations.

Only after all seven bytes and every safe check are final may the exact
`build-changed-regions` route publish the create-once manifest. Any later byte
change terminates gen9.

## Inherited containment and capability contract

The following exact line ranges from the frozen gen8 plan are normative after
deterministic rendering:

| source lines (inclusive) | contract | extra replacements after the standard plan substitutions | rendered SHA-256 |
|---:|---|---|---|
| 414–804 | changed-region writer/recovery and production/authorized containment | none; every `gen7` denotes the trusted inherited production helper/schema and stays literal | `00ec03779d302a3a28b4e83ec2102744f0bfdd12da18dfa817be28ba07c4186d` |
| 805–955 | capability | `failed_gen7→failed_gen8`, `failed-gen7→failed-gen8`, `gen7_failure→gen8_failure`, `frozen-gen7→frozen-gen8`, `frozen gen7→frozen gen8`, `m8t→m9t`, `m8b→m9b`, `m8p→m9p`, in order | `ac0221957c0afc07e258d5585bc2a813bb8b134bdafb048e07830176ff8dfcd4` |
| 956–1054 | reviews and exact one-way sequence | `GEN7_FAILURE_REVIEW_SHA256→GEN8_FAILURE_REVIEW_SHA256`; each of the seven exact current-subject controls `GEN8_{CONTROLLER,RUNTIME,RUNNER,LAUNCHER,TMUX_TEST_SUPERVISOR,RFC,TESTS}_SHA256→GEN9_*`; `PREDICTED_FAILED_GEN7_SHA256→PREDICTED_FAILED_GEN8_SHA256`; literal shorthand `GEN8_*_SHA256→GEN9_*_SHA256`, in that order | `0888b32e29be8a8a8e8c159d9dee61222538a247e14ab6e4b23ca5094e21dca8` |
| 1055–1106 | setup/downstream inheritance | the same five capability replacements | `01ea1fc872fb8753e3ba04b147ca12e384bb7b2238eefbdcc242d93d092f5278` |

In the review row, the brace notation expands literally and in this order to
`GEN8_CONTROLLER_SHA256→GEN9_CONTROLLER_SHA256`,
`GEN8_RUNTIME_SHA256→GEN9_RUNTIME_SHA256`,
`GEN8_RUNNER_SHA256→GEN9_RUNNER_SHA256`,
`GEN8_LAUNCHER_SHA256→GEN9_LAUNCHER_SHA256`,
`GEN8_TMUX_TEST_SUPERVISOR_SHA256→GEN9_TMUX_TEST_SUPERVISOR_SHA256`,
`GEN8_RFC_SHA256→GEN9_RFC_SHA256`, and
`GEN8_TESTS_SHA256→GEN9_TESTS_SHA256`. Replacement output is not rescanned.

Extraction retains the original LF after every included line. Concatenating the
four rendered ranges in table order produces 44,503 bytes with SHA-256
`119b960f6c5e489b19f82d06c52f382fac27c12ad8a7aac637799e7fce5476e9`.
That rendered byte stream—not semantic heading lookup—is the incorporated
contract. The corrected baseline/comparator/main rules and failed-gen8 schema
in this plan take precedence only where explicitly stated; no other exception
exists. All numeric cases, schemas, keys, deadlines, journals, complete/unknown
tripwire variants, command environments, capability check order, writer/NFS
recovery rules, review controls, setup receipts, and downstream scientific
contracts remain exact.

In particular:

- containment runs exactly C00–C09, one per-case launcher group, through the
  inherited production helper/cleanup path;
- the surviving outer supervisor journals descriptor, start, boundary
  attempt/result, before, action attempt/result, owner ledger, and result in
  exact order before advancing;
- a descriptor-durable interruption is terminal negative and preserves every
  durable preimage; it never reruns an uncertain action;
- pass requires ten ordered results, zero tripwire counters, exact process/
  group/session/socket/scratch extinction, lease reacquisition, and no
  emergency cleanup;
- capability runs six ordered checks only after a passing containment report
  and exact pre-capability review; a completed failure/interruption is terminal
  negative;
- neither containment nor capability reads protocol state, queries a GPU, or
  imports/calls a model.

The registered supervisor command must exercise the sole
`main_gen9_matrix`. Static tests require that candidate definitions and name
loads contain neither `main_gen7_matrix` nor `main_gen8_matrix`, require exactly
one definition and one bottom-statement call of `main_gen9_matrix`, and reject
any alias/rebinding. A runtime call trace proves that registered route invokes
`main_gen9_matrix` and each new `_g9_*` helper.

## Reviews and one-way sequence

The exact order is:

1. freeze this plan and obtain its registered independent plan SHIP review;
2. create/finish all seven gen9 implementation files;
3. run in-memory compilation, shell syntax, static closure, all safe predecessor
   and gen9 CPU tests, and publisher/recovery matrices, explicitly excluding
   the registered real-tmux node;
4. publish `changed_regions.json` once after its complete preflight;
5. create the registered pre-containment SHIP review binding the manifest,
   exact seven bytes, and exact CPU-only check rows;
6. run the registered real-tmux containment command exactly once and publish
   its report; a negative result terminates gen9;
7. create the pre-capability review binding the passing containment report;
8. run/publish capability once; a negative result terminates gen9;
9. create the final implementation review binding plan, plan review, failure
   record prediction, changed-region manifest, containment, capability, seven
   files, closure, and check transcripts;
10. only then run create-once setup M3;
11. obtain a fresh post-M3 review, build M4 once, obtain prescore evidence and
    review, sign once, and invoke the launcher under their separate gates.

No later step may be used as evidence for an earlier review. Recovery may only
finish exact durable bytes; it may not repeat an uncertain observation.

## Milestones

### P0 — plan authority

- [ ] Freeze this plan and obtain an independent SHIP review.
- [ ] Rehash the gen8 plan/reviews/frozen seven files and verify all gen8 analysis,
  protocol, and short-family paths absent.
- [ ] Acceptance: no gen9 implementation file or one-way artifact exists before
  the plan review.

### P1 — structural authority and honest failure

- [ ] Generate the seven gen9 baselines from the trusted frozen gen7 bytes; bind
  the frozen gen8 bytes only as failure evidence.
- [ ] Implement the stable statement-key comparator and exact changed-region
  publisher/recovery.
- [ ] Implement and independently reconstruct `failed_gen8.json`.
- [ ] Acceptance: all six comparator mutations above pass/reject as specified;
  current manifest deterministic; quarantine content reads zero.

### P2 — containment

- [ ] Complete the ten-case durable supervisor journal/report via
  `main_gen9_matrix`.
- [ ] Run pure schema/recovery and safe process tests first.
- [ ] After changed-region publication and pre-containment review, run the exact registered
  non-scientific real-tmux command once.
- [ ] Acceptance: ten ordered cases, zero tripwires, no emergency cleanup, complete
  final extinction, no `/tmp/m9*` sibling, passing report reconstructed.

### P3 — capability and reviews

- [ ] Complete six-check capability journal/recovery and exact namespace gate.
- [ ] Acceptance: descriptor/start/result prefixes reconstruct; stale/extra/
  interrupted/failing variants block; pass binds current manifest,
  containment, failed-gen8 prediction, implementation bytes, and reviews.

### P4 — setup and downstream gates

- [ ] Complete gen9 setup receipt DAG, closure/static trace, RFC, dispatch, and
  review schemas without changing scientific payload definitions.
- [ ] Acceptance: safe suites pass; static/site/value-flow digests match final
  bytes; exact setup transaction is recoverable; no one-way setup action occurs
  before final implementation SHIP.

## Verification plan

All commands use absolute paths, repository cwd, source-only local loading, and
closed environments. Before any one-way transition run, record canonical argv,
cwd, exact environment, timestamps, exit code, stdout/stderr digests, and
subject digest.

Safe pre-review checks include:

- in-memory `compile()` for every Python entry; `bash -n` for the launcher;
- `git diff --check` for the exact seven files, plan, and reviews;
- the complete predecessor CPU suites, with an honest typed exception for the
  terminal failed-gen8 tests rather than a false all-predecessors-pass claim;
- all gen9 CPU/no-model/static/value-flow/closure/candidate tests;
- publisher bootstrap/crash/recovery matrices on registered non-protocol test
  roots;
- containment schema, journal, process-extinction, mutation, and namespace
  tests without real tmux first;
- the registered real-tmux containment command only at P2, with the exact six
  inherited GPU/model/sealed/process/environment tripwire counters, static
  AF_UNIX-only closure, and quarantine tripwire;
- independent reconstruction of the changed-region, containment, capability,
  failed-gen8, setup, M4, and review subjects at their respective phases.

No safe check may query `nvidia-smi`, import a model stack, open a quarantined
payload, or invoke a scientific controller transition.

## Definition of done

Gen9 is ready for create-once M3 only when:

- [ ] Plan and plan review are immutable and exact.
- [ ] Honest failed-gen8 evidence independently reconstructs.
- [ ] All seven gen9 implementation bytes are final and structurally authorized.
- [ ] The executable supervisor route is mechanically proven to call the reviewed
   `main_gen9_matrix`, with no import-time alias trick;
- [ ] Changed-region manifest, passing ten-case containment report, passing
   six-check capability report, pre-containment review, pre-capability review,
   and final implementation review all exist and mutually bind;
- [ ] Static closure, dynamic file/nonfile site registries, exact process vectors,
   source-only imports, quarantine tripwire, and safe test transcripts reproduce;
- [ ] Every gen9 downstream protocol/run path and all seven short families remain
   absent;
- [ ] No GPU query, model import/call, scientific tmux launch, M3, M4, signature,
   authorization, nonce consumption, confirmation scoring, or Stage C has yet
   run.

M4, prescore, signing, nonce consumption, launch, Stage-B completion, and final
terminal validation remain separately reviewed one-way doors after this point.

## Alternatives considered

- **Retroactively edit the gen8 plan/review.** Rejected: they are create-once
  authority and changing them would erase the reason later evidence was gated.
- **Use a decorator/default-expression side effect to rebind
  `main_gen8_matrix`.** Rejected: it exploits the allowed-node checker and
  creates import-time authority not described by the reviewed control flow.
- **Nest all new helpers inside the inherited main.** Rejected: it defeats the
  per-function manifest and static closure required for review.
- **Discard the frozen partial gen8 subject and silently resume gen7.**
  Rejected: it would omit real operator/implementation history. Gen9 binds the
  failed gen8 bytes honestly while retaining the older scientific definitions.

## Risks and one-way doors

- The plan review, changed-region manifest, containment report, capability
  report, all later reviews, M3 receipts, M4 outputs, signature, and nonce are
  create-once. A stale or negative artifact terminates gen9.
- Real tmux containment is non-scientific but still creates real processes and
  sockets. It runs only after exact byte review and under the surviving outer
  cleanup authority.
- NFS hard-link publication has uncertain crash outcomes. Every writer embeds
  exact bytes in a durable descriptor and recovers only registered prefixes.
- PID reuse, socket substitution, hard-link aliasing, and permissive metadata
  can turn cleanup into collateral damage. Only descriptor-bound identities and
  validated PID/start-tick/PGID/peer lineage grant signal/unlink authority.
- The corrected comparator itself is security-critical. Its policy bytes and
  mutation regressions are independently reviewed before publication.
