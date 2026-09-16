# PLAN — MSAE independent measurement v3 post-M8 gen8

## Status and authority

This is a prospective, disjoint recovery generation. It does not revise or
reinterpret any predecessor. It authorizes implementation work only after an
independent `SHIP` review binds the SHA-256 of this exact plan. It authorizes no
capability, setup, M4, signature, GPU query, model import/call, scientific tmux
session, calibration, confirmation, or Stage C.

Gen7 is terminally **failed before capability**. Its frozen subject is:

| subject | SHA-256 |
|---|---|
| plan | `d612a86b3c33f774e51f649f1b87dc4977d6d91d2734e27729e84eb9a4867d5d` |
| plan review | `f3e3117e8331849c18f1520626e50edfed5c9602aa7b09ccd24bae434e016354` |
| controller | `4c10f5b5bc18ad4ae3828de5b6cebdf32e65c5ddf1f7acdec1aa2a1f8ad99ef9` |
| runtime | `017862e1c433d45fea4e91b60e2f23a62084a1f2c8200a1a8222fddfa7a125bc` |
| runner | `c28bec9c4d2c4be61ba0bd6a87df81e9c33a6a196bfecc5a4b778ecc9189df91` |
| launcher | `21519cf92d0ed1d91d9ac4ad0caa2178cc80572624401952afe629b6fba6ba4b` |
| tmux-test supervisor | `cd85077c33b283a5c2bfb767632d5ee29c59d3b16f6f0652e0802393a4fae6a7` |
| RFC | `857620e5df9be77aef2315816d9f16b6c1cad885eafcd9b8baf96db0af496f59` |
| tests | `c99fdef8f6ff505986aa81e2dbbf8da0f8f840e232fe1ee7c3c36ea800df258e` |

Its independent failure review is
`reports/adversarial/msae_independent_measurement_v3_post_m2_gen7_failure.md`,
SHA-256 `5b056100599fe16db207f4717d57600d624988886b0188cf3cab0a7a78d28d4d`.
It records four blockers: missing pre-action scenario proof, missing immutable
overall tmux transcript, a whole-file hash allowlist mislabeled as a typed
delta classifier, and synthetic cleanup-mutation evidence. No gen7
pre-capability review, capability report, M3, M4, authorization, GPU query,
model call, or calibration exists. Earlier real-tmux passes were
non-scientific iterative containment checks on nonterminal bytes and are not
upgraded to final-subject verification.

## Goal

Produce a reviewable gen8 control-plane successor that:

1. preserves gen7 honestly as failed before capability;
2. preserves all scientific inputs, projections, Stage-A/Stage-B semantics,
   authorization semantics, and the prohibition on confirmation/Stage C;
3. retains the foreground tmux server, persistent monitor, short socket paths,
   lease supervision, and complementary monitor/pane cleanup introduced by
   gen7;
4. replaces gen7's unimplemented exhaustive proof claims with a smaller,
   explicit set of real lifecycle cases and a durable canonical transcript;
5. mechanically proves that every non-control-plane AST change is only a
   generation/path substitution, while an independent review—not an in-file
   self-allowlist—authorizes the exact control-plane bytes; and
6. keeps capability, setup, M4, external prescore review, signing, and launch
   as separate reviewed one-way transitions.

## Non-goals

- Do not make gen5, gen6, or gen7 pass retroactively.
- Do not modify any frozen predecessor plan, review, source, test, protocol, or
  result.
- Do not change the corpus, overlap decisions, task/family strata, checkpoint
  registry, endpoint registry, thresholds, map sets, model snapshot, tokenizer,
  Stage-A schema, Stage-B QA, or calibration computation.
- Do not claim exhaustive proof for every syscall, source line, cleanup
  sub-action, signal interleaving, or tmux implementation behavior.
- Do not run confirmation scoring or create Stage C.
- Do not accept a passing test solely because an emergency cleanup hid a
  production cleanup failure.

## Immutable safety constraints

The following exact payload paths are metadata-only forever in this workflow:

- `data/atlas_v1/private/final.jsonl`;
- `data/atlas_v1/private/final.records.jsonl`;
- `data/atlas_v1/private/final.units.jsonl`.

No gen8 code, test, builder, signer, reviewer command, recovery path, or helper
may open, read, mmap, copy, or hash their content or a same-inode alias. Every
entry point runs under the inherited sealed-open tripwire and compares exact
before/after no-follow `lstat` subjects. Symlink-ancestor, ownership, mode,
link-count, device/inode, size, or timestamp drift blocks.

Only the reviewed signed launcher may query GPUs. It selects an idle GPU by the
inherited exact rule, takes the protocol-independent UUID lease, rechecks
idleness while holding it, and transfers the lease to the persistent monitor.
No manual GPU query is authorized.

The only pre-capability tmux action is the exact registered fake-broker
containment command. It uses no GPU, no model, no protocol/run/key/nonce state,
and no scientific data. Active process, environment, model-import, and
sealed-payload tripwires surround the whole command. No INET/NETLINK/PACKET
surface is authorized: the exact static and CPU closure must retain
`allowed_network_families=[AF_UNIX]` and the finite registered AF_UNIX endpoint
mapping. Gen8 does not misdescribe that source/behavioral closure as exhaustive
live syscall tracing.

All local Python entry points are source-only. Ignored timestamp/sourceless
`.pyc` and local extension-module shadows cannot execute. The scripts directory
is removed from ordinary `sys.path` before deferred third-party imports.

## Grounding and design choice

The workspace query backend is unavailable, so the plan was grounded by direct
read-only inspection of the frozen gen7 plan, failure review, and definitions
of `foreground_tmux_start_v1`, `_containment_monitor_cleanup`,
`_g7_scenario_action_projection`, the capability gate, setup, M4, signer, and
launcher. No project design-bank entry was available for this recovery choice.

Chosen approach: keep the working gen7 production containment architecture,
remove claims the implementation cannot substantiate, add a durable real-test
transcript, and use a closed AST-region comparator plus exact external review
for the gen7-to-gen8 change. This is preferable to completing gen7's frozen
75-hook × two-mode plus 12-scenario proof because that plan required global
pre-action evidence and per-cleanup mutation semantics that were not present
in the reviewed implementation and repeatedly created unverifiable
self-attestation cycles.

Alternative considered: abandon tmux and run the worker directly under a
single foreground supervisor. Rejected because the requested launcher must
return after durable handoff while calibration continues, and predecessor
authorization, lease, terminal, and operational expectations already bind a
tmux session.

Low-risk assumption: gen8 may narrow a predecessor's prospective proof claim
without weakening runtime fail-closed behavior, because gen7 created no
authority or scientific state. Any material scientific or authorization change
requires a new plan rather than implementation-review discretion.

## Exact gen8 files and namespaces

The implementation subject contains exactly these seven new entries:

1. `scripts/msae_independent_measurement_v3_post_m2_gen8.py`;
2. `scripts/msae_independent_measurement_v3_post_m2_gen8_runtime.py`;
3. `scripts/run_msae_independent_calibration_v3_gen8.py`;
4. `scripts/launch_msae_independent_calibration_v3_gen8.sh`;
5. `scripts/run_msae_independent_measurement_v3_post_m2_gen8_tmux_test.py`;
6. `docs/rfc-msae-independent-measurement-v3-post-m8-gen8.md`;
7. `tests/test_msae_independent_measurement_v3_post_m8_gen8.py`.

Reviews are create-once regular mode-0644 files:

- plan review:
  `reports/adversarial/msae_independent_measurement_v3_post_m2_gen8_plan.md`;
- pre-containment review:
  `reports/adversarial/msae_independent_measurement_v3_post_m2_gen8_pre_containment.md`;
- pre-capability review:
  `reports/adversarial/msae_independent_measurement_v3_post_m2_gen8_pre_capability.md`;
- implementation review:
  `reports/adversarial/msae_independent_measurement_v3_post_m2_gen8_implementation.md`;
- post-M3 review:
  `reports/adversarial/msae_independent_measurement_v3_post_m2_gen8_post_m3.md`;
- prescore review:
  `reports/adversarial/msae_independent_measurement_v3_post_m2_gen8_prescore.md`.

Pre-capability evidence lives only under the closed analysis root
`reports/analysis/msae_independent_measurement_v3_post_m2_gen8/`:

- `tmux_containment.json`;
- `gen8_capability_reproduction.json`;
- `changed_regions.json`;
- `.changed_regions_transaction/`, whose only legal children are
  `transaction.json`, `manifest.payload`, and their three registered attempt
  markers;
- `.tmux_containment_transaction/`, whose only legal children are
  `transaction.json`, `case-C00-start.json` through
  `case-C09-start.json`, and for each C00–C09 the suffixes
  `-boundary-attempt.json`, `-boundary.json`, `-before.json`,
  `-action-attempt.json`, `-action-result.json`,
  `-owner-ledger.json`, and `-result.json`, plus `failure.json`,
  `interruption.json`, `report.payload`, and for every
  registered regular child at most the three exact publisher markers
  `.<name>.attempt-1`, `.<name>.attempt-2`, and `.<name>.attempt-3`; and
- `.capability_report_transaction/`, whose only legal children are
  `transaction.json`, `check-01-start.json` through `check-06-start.json`,
  `check-01-result.json` through `check-06-result.json`, `failure.json`,
  `interruption.json`, `report.payload`, and the same three exact per-name
  attempt-marker forms.

The analysis root and live transaction directories are current-UID/GID
mode-0700 directories with nlink determined by the exact child projection.
Every transaction child and each of the three final JSON artifacts is a
current-UID/GID mode-0600 regular file; source/destination publication pairs
are the registered same-inode nlink-2 exception, and terminal files are nlink
1. No symlink ancestor, special file, hard-link alias, or permissive mode is
accepted.

The exact short socket families are `/tmp/m8t_<64-lowerhex>.sock` (tmux),
`/tmp/m8b_<64-lowerhex>.sock` (broker), and
`/tmp/m8p_<64-lowerhex>.sock` (pane/lease). The containment test uses disjoint
families `/tmp/m8x_`, `/tmp/m8a_`, and `/tmp/m8c_` plus scratch `/tmp/m8s_`.
Every phase enumerates `/tmp` no-follow and rejects any undeclared sibling in
all seven `m8t_/m8b_/m8p_/m8x_/m8a_/m8c_/m8s_` families. All names fit Linux
`sun_path` before implementation review. Outside an active authorized
publication/containment attempt, all three transaction directories and all seven families are
absent. During an attempt, the phase-specific exact child prefix below is the
only exception.

The containment scratch is exactly the frozen gen7 containment scratch path and
closed child registry after the ordered substitutions, including its literal
`terminal.claim.test`, `technical_failure.test.json`, partial publication,
identity, monitor/pane/process, lease, and log names. Gen8 adds no scratch child.
The owner cleans that inherited registry; the outer embeds the descriptor-read
owner ledger in the analysis transaction, performs only the inherited
descriptor-safe ledger unlink/rmdir sequence, and proves the whole `/tmp/m8s_`
family empty before the next case.

All other config/provenance/M4/key/state/run/build paths are the exact gen7
paths after this longest-token-first ordered byte substitution table:

1. `post_m7_gen7→post_m8_gen8`;
2. `post-m7-gen7→post-m8-gen8`;
3. `msae-independent-v3-gen7→msae-independent-v3-gen8`;
4. `m7t_→m8t_`, `m7b_→m8b_`, `m7p_→m8p_`, `m7x_→m8x_`,
   `m7a_→m8a_`, `m7c_→m8c_`, and `m7s_→m8s_`, in that order;
5. `Gen7→Gen8`;
6. `gen7→gen8`.

Each source token is applied once as a global replacement to the result of the
prior row. An unchanged gen7/m7-family token or a double substitution blocks.

## Honest gen7 failure record

Gen8 setup predicts and then publishes create-once `failed_gen7.json` with
schema `msae_v3_gen8_failed_gen7_evidence_v1`. Its exact top-level keys are
`schema_version`, `protocol_id`, `generation`, `writer_generation`, `status`,
`terminal_fields`, `frozen_subject`, `failure_review`, `blockers`,
`checks`, `namespace_absence`, `sealed_payload_metadata`, and
`gen8_plan_authority`.

- `protocol_id="msae_independent_measurement_v3"`, `generation="gen7"`,
  `writer_generation="gen8"`, and `status="failed_before_capability"`.
- `terminal_fields` has exactly the ordered keys `pre_containment_review`,
  `containment_report`, `pre_capability_review`, `capability`,
  `implementation_review`, `m3`, `m4`, `stage_a`, `authorization`,
  `gpu_query`, `model_call`, `calibration`, `confirmation`, and `stage_c`.
  The first nine equal `not_created`; the last five equal `not_run`.
- `frozen_subject` has exactly the ordered keys `plan`, `plan_review`,
  `controller`, `runtime`, `runner`, `launcher`, `tmux_test_supervisor`, `rfc`,
  `tests`, and `failure_review`. Each value has exact keys `path`, `type`,
  `mode`, `uid`, `gid`, `nlink`, `size`, `sha256`, and
  `verification_action`; it requires a UID/GID-owned nlink-1 regular file,
  registered mode, current size/digest, and `content_rehash`.
- `failure_review` has exact keys `path`, `sha256`, `verdict`, `blocker_count`,
  and `origin`; values are the literal path/digest above, `BLOCK`, integer 4,
  and `independent_adversarial_review`.
- `blockers` is an ordinal-sorted four-row array. Row keys are exactly
  `ordinal`, `severity`, `citation`, `one_line`, and
  `failure_review_sha256`. Values are parsed from the four review bullets;
  ordinals are 1–4, severities are `critical,critical,high,high`, and every row
  binds the failure-review digest. Unknown/duplicate/missing bullets block.
- `checks` is an ordered array with exact row keys `id`, `evidence_class`,
  `subject_sha256`, `argv`, `cwd`, `environment`, `started_utc`, `ended_utc`,
  `transcript_sha256`, `transcript_available`, `exit_code`, `summary`, and
  `details`. The exact IDs are `critic_targeted_pytest`, `in_memory_compile`,
  `bash_syntax`, `diff_check`, `schema_search`, and `namespace_lstat`. Only the
  first is `independent_review_current_subject`; the remainder are
  `independent_review_current_subject` when the failure review gives exact
  current-byte evidence and otherwise `independent_review_observation`.
  Any argv/cwd/environment/timestamp/transcript/exit-code field not stated in
  the independent review is JSON null (and transcript availability false),
  never invented; a stated zero exit code remains integer zero;
  `details` contains only literal facts stated in the failure review.
- `namespace_absence` is a path-sorted array of exact rows `path`, `expected`,
  `lexists`, `kind`, and `phase`. The present gen7 plan review and failure
  review are excluded because they are frozen content entries above. The exact
  expected-absent constant-name set is `PRE_CAPABILITY_REVIEW`,
  `IMPLEMENTATION_REVIEW`, `POST_M3_REVIEW`, `PRESCORE_REVIEW`,
  `CAPABILITY_ANALYSIS_ROOT`, `CAPABILITY_TRANSACTION`, `CAPABILITY_REPORT`,
  `CAPABILITY_PROBE_ROOT`, `ACTIVE_CONFIG`, `ACTIVE_PROV`, `ACTIVE_M4_DATA`,
  `M4_TRANSACTION`, `SETUP_JOURNAL`, `SETUP_MANIFEST`,
  `SETUP_KEY_TRANSACTION`, `ACTIVE_PRIVATE_KEY`, `ACTIVE_STATE`,
  `ACTIVE_NONCE_DIR`, `ACTIVE_RUN_ROOT`, `M4_PRIMARY`, and `M4_REBUILD`, plus
  the complete seven-family projection. Values are `absent`, false,
  `exact_path|closed_family`, and `failed_before_capability`.
- `sealed_payload_metadata` has exactly `content_read_attempts`, `before`, and
  `after`. Reads equal zero. Each map has only the three literal sealed paths;
  rows have exact keys `path`, `type`, `mode`, `uid`, `gid`, `nlink`, `size`,
  `device`, `inode`, `ctime_ns`, and `mtime_ns`. Before/after maps byte-equal.
- `gen8_plan_authority` has exact keys `plan_path`, `plan_sha256`,
  `plan_review_path`, and `plan_review_sha256` and binds the reviewed gen8 plan.

One builder constructs the payload from typed objects. A separate verifier does
not call that builder: it reparses the literal failure review, enumerates the
literal frozen paths/namespaces, performs fresh no-follow metadata/content
checks subject to the quarantine tripwire, and constructs the same canonical
JSON from its own projection. Exact byte equality is required before the first
setup write. Any contradiction or downstream gen7 artifact blocks gen8.
The verifier builds a typed expected-state table, not an untyped set equality:
the ten `frozen_subject` paths are `present_frozen`; only the constant-name and
family rows enumerated above are `absent`. A path occurring in both classes,
an unregistered gen7-prefixed sibling, or any observed state different from its
typed expected state blocks.

## Mechanical change boundary

Gen8 does **not** call a whole-file hash registry a semantic classifier. The
plan freezes this policy; the later reviews bind the comparator implementation.
Start with exact gen7 bytes and apply only the ordered substitutions above to
produce baseline `B`. Parse `B` and candidate `C` with Python's frozen
stdlib-AST. A top-level node key is `(node-kind, defined/assigned-name,
zero-based occurrence)`. Duplicate definitions/assignments, parse failures, or
node-key drift outside the lists below block.

The controller, runner, and launcher candidate bytes must equal `B` byte for
byte. No exceptions exist. For the runtime, changed top-level assignments are
limited to these exact names under region `R8_CONSTANTS`:

`PLAN_PATH`, `PLAN_REVIEW`, `PRE_CONTAINMENT_REVIEW`,
`PRE_CAPABILITY_REVIEW`, `IMPLEMENTATION_REVIEW`, `POST_M3_REVIEW`,
`PRESCORE_REVIEW`, `FAILURE_REVIEW`, `RUNTIME_RFC`, `RUNTIME_TEST`,
`TMUX_TEST_SUPERVISOR`, `CONTAINMENT_ANALYSIS_ROOT`, `CHANGE_MANIFEST`,
`CHANGE_MANIFEST_TRANSACTION`, `CONTAINMENT_REPORT`,
`CONTAINMENT_TRANSACTION`, `FAILED_GEN7_RECORD`, `CAPABILITY_REPORT`,
`CAPABILITY_TRANSACTION`, `CAPABILITY_PROBE_ROOT`, `SETUP_JOURNAL`,
`SETUP_MANIFEST`, `SETUP_KEY_TRANSACTION`, `SETUP_RECEIPT_NAMES`,
`FROZEN_PLAN_SHA256`, `FROZEN_PLAN_REVIEW_SHA256`,
`FROZEN_STATIC_SURFACE_SET_SHA256`, `FROZEN_DYNAMIC_FILE_SITE_SET_SHA256`,
`FROZEN_LOCAL_VALUE_FLOW_AST_SHA256`,
`FROZEN_DYNAMIC_FILE_SITE_BINDING_IDS`,
`FROZEN_NONFILE_SURFACE_SITE_BINDING_IDS`,
`PUBLIC_EXECUTION_ENTRYPOINTS`,
`GEN8_SUBSTITUTIONS`, `GEN8_ALLOWED_CHANGE_POLICY`, `FAILED_GEN7_PLAN`,
`FAILED_GEN7_PLAN_REVIEW`, `FAILED_GEN7_FAILURE_REVIEW`,
`FAILED_GEN7_PLAN_SHA256`, `FAILED_GEN7_PLAN_REVIEW_SHA256`,
`FAILED_GEN7_FAILURE_REVIEW_SHA256`, `FAILED_GEN7_CONTROLLER_SHA256`,
`FAILED_GEN7_RUNTIME_SHA256`, `FAILED_GEN7_RUNNER_SHA256`,
`FAILED_GEN7_LAUNCHER_SHA256`, `FAILED_GEN7_TMUX_TEST_SHA256`,
`FAILED_GEN7_RFC_SHA256`, and `FAILED_GEN7_TESTS_SHA256`.

Changed/new runtime definitions are limited to this exact map:

- `R8_CHANGE_POLICY`: `_normalized_gen8_baseline_bytes`,
  `_normalized_top_level_node`, `_gen8_changed_region_rows`,
  `_gen7_to_gen8_change_manifest`, `_changed_regions_transaction_descriptor`,
  `_validate_changed_regions_transaction`, `_publish_changed_regions`,
  `_build_changed_regions`, and `build_changed_regions`;
- `R8_FAILURE`: `_failed_gen7_entries`, `_failed_gen7_terminal_payload`, and
  `_verify_failed_gen7_terminal_payload`;
- `R8_REVIEWS`: `_review_control_lines`, `_review_check_rows`,
  `_pre_containment_review_binding`, `_pre_capability_review_binding`,
  `_implementation_review_binding`, and `_validate_gen8_review_namespace`;
- `R8_CONTAINMENT_REPORT`: `_containment_attempt_descriptor`,
  `_containment_case_start`, `_containment_case_result`,
  `_validate_containment_report`, `_recover_interrupted_containment`, and
  `_publish_containment_report`;
- `R8_CAPABILITY`: `_pre_capability_namespace_gate`,
  `_validate_capability_report`, `_perform_gen8_capability_probe`, and
  `probe_gen8_capability`;
- `R8_TRACE`: `_surface_file_registry`, `_finite_process_registry`, and
  `cpu_no_model_public_entry_trace`; these add only the exact changed-regions
  paths/transaction/public-entry realization and the three exact outer command
  vectors/environments registered below;
- `R8_SETUP`: `_setup_transaction_payloads`, `_setup_receipt_value`,
  `_setup_manifest_payload`, `_setup_m3_gen8_impl`, and `setup_m3_gen8`;
- `R8_CLOSURE`: `_closure_local_relative_names` and `_candidate_relatives`;
  these may only replace the failed-gen6 path with the
  exact failed-gen7 path and add the gen8 failure review, pre-containment and
  pre-capability reviews, implementation review, changed-regions manifest,
  passing containment report, and passing capability report to the local
  closure. Candidate/protected directory projections also bind exact absence of
  `.changed_regions_transaction`, `.tmux_containment_transaction`, and
  `.capability_report_transaction`; Stage-A and scientific payload definitions
  may not change;
- `R8_DISPATCH`: `_require_exact_command_shape` and `dispatch`.

`PUBLIC_EXECUTION_ENTRYPOINTS` is the substituted inherited tuple with exactly
one insertion, `build_changed_regions`, immediately before
`probe_gen8_capability`. The CPU/no-model trace calls that function under the
existing surface mocks and requires its first allowed request map to the exact
analysis/transaction registry. `_finite_process_registry` adds the literal
outer `/usr/bin/env` vectors and exact environments for changed-regions,
containment, and capability; the runtime does not spawn those vectors and the
corresponding review/report row proves each operator invocation.
Unknown command spellings, relative argv, extra environment keys, output drift,
or a trace that omits the new entry blocks. Static surface/value-flow/site
digests are refrozen only after these reviewed nodes settle.

Changed/new tmux-test-supervisor definitions are limited to this exact map:

- `T8_PROTOCOL`: `_g8_case_table`, `_g8_process_row`, `_g8_boundary_event`,
  `_g8_validate_boundary_event`, `_g8_owner_result`,
  `_g8_validate_owner_result`, and `_g8_outer_result`;
- `T8_ATTEMPT`: `_g8_attempt_descriptor`, `_g8_case_start_record`,
  `_g8_case_journal`, `_g8_recover_interrupted_attempt`, and
  `_g8_publish_report`;
- `T8_EXECUTION`: `_g8_run_case`, `_g8_run_all`, and `main`;
- `T8_EMERGENCY`: `_g8_emergency_containment`.

No other assignment, import, class, function, async function, or top-level
statement may differ from `B`. An allowed definition is compared as its full
source segment including decorators, signature, defaults, annotations, and
body. Bytes between allowed source segments must equal `B`; therefore comments,
imports, module docstrings, and whitespace outside an allowed node cannot drift.
Every changed source byte belongs to exactly one nonoverlapping listed node and
region. The comparator implementation and the literal policy tables are not
self-excluded: pre-containment review binds their exact bytes, and a mutation
test changes each policy/comparator node and requires the manifest digest to
change or validation to fail.

The inherited names `FROZEN_GEN7_TYPED_DELTA_SHA256S`,
`_typed_gen7_delta_projection`, and `gen6_to_gen7_substitution_evidence` remain
dead compatibility diagnostics after substitution. No capability, setup,
review, candidate, dispatch, or public execution route calls them. Every live
gate calls `_gen7_to_gen8_change_manifest`. A regression replaces each legacy
diagnostic with a raising stub and requires all live safe gates still pass,
then stubs the gen8 manifest path and requires every such gate fail. The old
whole-file registry therefore cannot become an alternate authorization path.

The RFC and test file are reviewed as complete exact bytes; they are not
misrepresented as scientific-equivalence evidence. Tests may differ freely,
but cannot contribute executable closure outside the registered real-test
entry. The RFC is documentation only.

The canonical manifest schema `msae_v3_gen8_changed_regions_v1` has exact keys
`schema_version`, `baseline_subjects`, `candidate_subjects`, `policy`, `rows`,
and `manifest_sha256_excluded`. Each row has exact keys `path`, `node_kind`,
`qualified_name`, `occurrence`, `old_start`, `old_end`, `new_start`, `new_end`,
`old_sha256`, `new_sha256`, and `region_id`, sorted by candidate path/start.
Subject maps bind all seven bytes. `policy` is the literal maps above.
`manifest_sha256_excluded=true` is the sole self-hash exclusion.
After the seven implementation entries freeze, these deterministic bytes are
NFS-hard-link published as `changed_regions.json` using
`.changed_regions_transaction`; its descriptor embeds `manifest.payload`, so
an interruption exactly recovers. No timestamp enters the payload. A later
implementation-byte change makes the manifest stale and terminates gen8 rather
than permitting replacement.
Independent pre-containment and implementation reviews inspect this manifest
and authorize the exact seven candidate file hashes. This external review is
the authority for allowed control-plane semantics.

The sole writer route is controller command `build-changed-regions`. Its exact
outer command vector is:

`/usr/bin/env -i HOME=/tmp LANG=C LC_ALL=C PATH=/usr/bin:/bin PYTHONDONTWRITEBYTECODE=1 PYTHONHASHSEED=0 TZ=UTC /jumbo/lisp/f004ndc/experiments/wip/MSAE/.venv-atlas/bin/python -S -B -I /jumbo/lisp/f004ndc/experiments/wip/MSAE/scripts/msae_independent_measurement_v3_post_m2_gen8.py build-changed-regions --output /jumbo/lisp/f004ndc/experiments/wip/MSAE/reports/analysis/msae_independent_measurement_v3_post_m2_gen8/changed_regions.json`

Cwd is the repository root and the Python process requires the same exact
seven-key environment map later frozen for capability. It runs only after the
seven entries, plan, and plan review are exact and after all 13 safe check rows
exist, but before pre-containment review. Preflight requires: exact plan review;
the seven candidate bytes; analysis root empty or one exact recoverable changed-
regions transaction; all later reviews/evidence/protocol/run namespaces absent;
all seven short families absent; and the three quarantine lstat rows unchanged
with zero content reads. Unexpected children block before a write.

The first writer bootstraps the analysis root descriptor-safely: create exactly
the UID/GID-owned mode-0700 root, fsync `reports/analysis`, create exactly the
mode-0700 changed-regions transaction, and fsync the root. A crash leaving only
the empty exact root, or root plus empty exact transaction before descriptor
fsync, is restartable after the full preflight repeats; no implementation byte,
review, probe, child, or external syscall outcome has changed. It may remove
only that identity-bound empty transaction or continue to the descriptor. Any
nonempty pre-descriptor child or metadata drift blocks. Once the descriptor is
fsynced, only the exact recovery below is legal and the root remains the closed
analysis authority for later phases.

The mode-0600 transaction descriptor schema is
`msae_v3_gen8_changed_regions_transaction_v1`, exact keys `schema_version`,
`plan_sha256`, `plan_review_sha256`, `implementation_entries`, `manifest`,
`manifest_sha256`, `argv`, `python_argv`, `cwd`, `environment`, and
`status=prepared`. It embeds the complete canonical manifest, so the legal
prefixes are descriptor only; descriptor plus exact `manifest.payload`; final
hard link to that same inode/content; and cleanup complete. Re-entry validates
every descriptor field and namespace child before mutation, materializes or
links only the embedded bytes, and removes only its exact transaction. A crash
before descriptor fsync is restartable; any post-descriptor drift, extra child,
wrong link identity, changed implementation byte, or negative recovery is
terminal and never authorizes replacement.

## Production containment contract

Gen8 inherits gen7's source-only foreground-server architecture after literal
substitution:

- launcher creates and descriptor-binds the broker listener, selects and locks
  a GPU, starts a dedicated monitor in a new process group, and performs the
  bounded monitor handshake;
- monitor is a subreaper, owns the transferred GPU lease, creates the tmux
  foreground server with exact `/usr/bin/tmux -D -f /dev/null -S <socket>`,
  uses separate bounded clients for `set-option -s exit-empty on`,
  `show-options -s -v exit-empty`, `new-session -d`, and
  `display-message -p`, and remains alive after launcher return;
- pane supervisor validates the pane/monitor/lease handoff before starting the
  broker and worker; broker and worker retain their inherited pre-model gates;
- monitor and pane supervisor are complementary cleanup authorities. Monitor
  handles pane death; pane handles monitor/server death. Both use the same
  create-once terminal claim so only one terminal owner may publish;
- all tmux/GPU/process/socket operations are bounded. Only fully validated
  PID/start-tick/PPID/PGID/peer-credential and held-descriptor identities grant
  signal or unlink authority;
- cleanup is non-short-circuiting, records every action/error, performs
  TERM/wait/KILL/wait for validated groups, bounded final `has-session`, and a
  final post-probe absence scan before releasing the lease;
- launcher returns only after the durable monitor record, pane/worker lineage,
  readiness, nonce/authorization, two-phase model gate, and monitor takeover
  acknowledgement are all validated. A live tmux socket remains while the
  session runs; broker and pane handoff sockets are gone before return.

The complete gen7 production monitor/frame/record/worker schemas and production
helper/cleanup definitions are byte/AST inherited after literal substitution.
This plan changes only containment-test control/evidence and later review/
failure/setup projections; it does not authorize a production frame, identity,
deadline, durability, or cleanup change. A discovered production defect
requires a new reviewed plan.

## Authorized real-process containment evidence

The registered test invokes the byte/AST-inherited production start/control/
cleanup functions with the inherited containment variant. Its fault transport
remains the gen7 `AF_UNIX/SOCK_DGRAM` socketpair and exact schemas after ordered
substitution: `msae_v3_gen8_fault_event_binding_v1`,
`msae_v3_gen8_fault_control_v2`, `msae_v3_gen8_fault_event_v1`, the inherited
hook/scenario owner-ledger schemas, and the inherited terminal-test schemas.
No runtime hook, event, role, helper, cleanup, scratch, or production config
schema changes in gen8. Test-only inputs remain data: disjoint paths, fake
GPU/lease identity, fake broker argv, registered deadline budget, selected
existing hook/scenario, and the held fault-event endpoint.

Exactly these ten already-reachable frozen-gen7 cases are selected; no
exhaustive claim is made:

| case | kind/registry literal | exact injected action | reporter | expected terminal/cleanup owner |
|---|---|---|---|---|
| C00 | hook 1 `before_monitor_record_write` | `report_then_sigstop_crash` | launcher | monitor |
| C01 | hook 9 `before_server_fork` | `report_then_sigstop_crash` | monitor | launcher |
| C02 | hook 13 `after_socket_publication` | `report_then_sigstop_crash` | monitor | launcher |
| C03 | hook 18 `after_new_session_client` | `report_then_sigstop_crash` | monitor | launcher |
| C04 | scenario `S03_pane_death` | `sigkill_pane_group_after_takeover` | pane supervisor | monitor |
| C05 | scenario `S08_monitor_death_after_launcher_eof` | `sigkill_monitor_after_expected_eof` | monitor | pane supervisor |
| C06 | scenario `S04_broker_death` | `sigkill_broker_after_takeover` | fake broker | pane supervisor |
| C07 | scenario `S05_worker_death` | `sigkill_worker_after_pre_model_gate` | fake worker | pane supervisor |
| C08 | scenario `S01_monitor_death` | `sigkill_monitor_before_handoff` | monitor | launcher |
| C09 | scenario `S09_child_timeout` | `observe_lm5_receive_timeout` | launcher; launcher emits receiver observation | launcher |

For hook cases the inherited `HOOK_REACHED` datagram fixes hook ID, case index,
reporter role/kind, PID/start-tick/PPID/PGID, and `crash|exception`. The outer
validates SCM credentials and `/proc`. It SIGKILLs the stopped reporter for all
four selected hook cases. Exception-mode hooks remain safe unit-schema/cleanup
tests only; gen8 does not claim a credentialed post-resume exception observation
that the inherited protocol does not emit.
For scenarios, the inherited `SCENARIO_BOUNDARY_REACHED` event, literal
`TMUX_SCENARIOS` row, and supervisor action function are the sole action
authority. C09 additionally requires the inherited credentialed
`SCENARIO_ACTION_OBSERVED` from the launcher; its action enum is
`observe_lm5_receive_timeout`, its exact zero-byte timeout observation binds
the boundary digest, and no caller-supplied label substitutes for that receiver observation. The other
scenarios use independently validated signals/process state already required by
their frozen row. Unknown/duplicate events, reporter or target drift, wrong
claimant, missing receiver event, early terminalization, or emergency cleanup
fails the case.

Each case runs in its own per-case launcher group under one outer supervisor.
The inherited reporter stops at its boundary, so the outer constructs the
pre-action subject before injecting/resuming. Schema
`msae_v3_gen8_outer_before_v1` has exact keys `schema_version`, `case_id`,
`registry_row`, `boundary_event_sha256`, `reporter`, `target`, `processes`,
`groups`, `session`, `sockets`, `lease`, and `deadlines`. Reporter/process rows
use exact schema `msae_v3_gen8_process_v1`, keys `schema_version`, `role`,
`pid`, `start_ticks`, `ppid`, `pgid`, `uid`, `gid`. `target` is one exact
tagged union: that generic process schema for a hook reporter; inherited
`msae_v3_gen8_scenario_process_v1`, exact keys `schema_version`, `kind`
(`process`), `role`, `pid`, `start_ticks`, `ppid`, `pgid`, `uid`, and `gid` for
a direct-process scenario target; inherited
`msae_v3_gen8_scenario_process_group_v1`, keys `schema_version`, `kind`
(`process_group`), `role`, `pgid`, `leader_pid`, `leader_start_ticks`, and
`members`, with PID-sorted process rows; or inherited
`msae_v3_gen8_scenario_deadline_v1`, keys `schema_version`, `kind` (`deadline`),
`owner_process`, `deadline_monotonic_ns`, and `source`. C04 requires the group
variant for the exact live pane group. C09 requires the deadline variant,
`owner_process` equal to the launcher reporter, deadline equal case start plus
8,000,000,000 ns, and source `receive_timeout_lm5_at_helper_deadline`. All
other selected scenarios use the process variant. The separate `groups` array
uses exact keys
`schema_version`, `role`, `pgid`, `leader`, `members`, with PID-sorted members.
`registry_row` is the complete literal hook/scenario tuple. `session` is exact
`name`, `has_session_returncode`, `server`, `pane`. `sockets` is the exact
no-follow projection of inherited containment ACK/tmux/broker/pane paths.
`lease` is the inherited fake lease binding. `deadlines` is the inherited
containment budget: helper start = case start + 8 seconds, outer deadline = case
start + 24 seconds, tmux clients 1 second, TERM/KILL 250 ms each.

The action observation schema is `msae_v3_gen8_outer_action_v1`, exact keys
`schema_version`, `case_id`, `boundary_event_sha256`, `action_enum`, `target`,
`steps`, `receiver_event_sha256`, `started_monotonic_ns`, and
`ended_monotonic_ns`. Each element of `steps` has exact keys `ordinal`,
`initiator`, `operation`, `signal`, `target`, and `observation`. Ordinals start
at one and are contiguous. `signal` is an integer only for `send_signal` and is
otherwise null. `observation` is the full canonical receiver observation for
an observation step and null for a signal step. The exact step
registry is:

- C00: outer `send_signal(SIGKILL)` to the launcher;
- C01: outer `send_signal(SIGKILL)` to the monitor;
- C02: outer `send_signal(SIGKILL)` to the monitor;
- C03: outer `send_signal(SIGKILL)` to the monitor;
- C04: outer `send_signal(SIGKILL)` to the pane process group;
- C05: outer `send_signal(SIGKILL)` to the monitor;
- C06: outer `send_signal(SIGKILL)` to the broker;
- C07: outer `send_signal(SIGKILL)` to the worker;
- C08: outer `send_signal(SIGKILL)` to the monitor; and
- C09: outer `send_signal(SIGCONT)` to the launcher, then launcher
  `observe_lm5_receive_timeout` with the credentialed exact zero-byte receiver
  observation.

`receiver_event_sha256` is non-null exactly for C09 and equals the digest of
that second-step observation. `before.target` and `action.target` byte-equal.
Each step target is the exact signal/observation object: normally the global
target; for C09's SIGCONT step it is `action.target.owner_process`, while the
timeout-observation step uses the deadline target. No step may substitute a
caller label or a post-cleanup reconstruction.
The inherited owner ledger is deliberately a post-cleanup projection and is
not falsely required to byte-equal the live pre-action target:

- for C00-C03, the inherited hook ledger has no target object. The outer
  compares only immutable reporter tuple `(role,pid,start_ticks,pgid)` across
  boundary, before, action, and owner ledger;
- for a process scenario target, the outer compares immutable
  `(kind,role,pid,start_ticks,pgid)` and ignores post-cleanup `ppid/live` drift;
- for C04's process group, it compares
  `(kind,role,pgid,leader_pid,leader_start_ticks)` and requires every owner
  member identity `(pid,start_ticks,pgid)` to have appeared in the pre-action
  member set, while independently proving the complete pre-action group empty;
- for C09's deadline, it compares `(kind,source,deadline_monotonic_ns)` plus
  immutable owner-process `(pid,start_ticks,pgid)` and ignores post-cleanup
  liveness/parent drift.

C02 additionally requires the exact socket identity captured before reporter
kill. All cases bind the exact live target before the first action step and its
required extinction/timeout result afterward.

The production cleanup owner publishes the exact inherited canonical owner
ledger; gen8 does not add fields to it. The supervisor validates that ledger with
the inherited independent table/schema validator, then embeds the full canonical
object. The outer constructs `msae_v3_gen8_case_outer_result_v1`, exact keys
`schema_version`, `case_id`, `before`, `action`, `owner_ledger_sha256`,
`processes_extinct`, `groups_empty`, `session_absent`, `socket_paths_absent`,
`scratch_entries`, `lease_reacquired`, `tripwires`,
`emergency_cleanup_used`, and `outcome`. It proves every captured PID/start-tick
extinct, every captured PGID empty, final bounded `has-session` nonzero, all
registered paths absent after that probe, fake lease reacquirable, inherited
scratch empty after ledger consumption, and the exact six tripwire counters
`gpu_query`, `model_import`, `model_call`, `sealed_open`,
`unregistered_process`, and `environment_activation` in the complete-count
schema below are zero. It compares
case/registry/boundary/action/claimant/terminal digest, action event where
applicable, TERM/KILL facts, socket/session absence, and tripwires against the
owner ledger using the case/type-specific immutable comparisons above. The
inherited ledger's six legacy tripwire facts are compared to their mapped gen8
counters. The owner never supplies the outer pre-action or final-extinction
subject. A pass requires
`emergency_cleanup_used=false`.

Before the first child release or tmux action, the supervisor fsync-publishes
mode-0600 `.tmux_containment_transaction/transaction.json`, schema
`msae_v3_gen8_containment_attempt_v1`, exact keys `schema_version`,
`test_token`, `plan_sha256`, `plan_review_sha256`,
`pre_containment_review_sha256`, `implementation_entries`, `command`,
`python_argv`, `environment`, `cases`, `started_utc`, and `status=started`.
`test_token` is the
lowercase SHA-256 of canonical JSON with exact keys `plan_sha256`,
`plan_review_sha256`, `pre_containment_review_sha256`, and
`implementation_entries`; the last is the path-sorted seven-entry content map.
Creation/fsync of the empty exact mode-0700 transaction directory may precede
the descriptor. A crash in that empty pre-descriptor state is restartable after
full review/namespace revalidation and may remove only that held, still-empty
directory; a nonempty or substituted pre-descriptor directory blocks.

Before releasing each launcher from its inherited start barrier, the outer
fsync-publishes `case-CXX-start.json`, exact keys `schema_version`, `test_token`,
`case_id`, `launcher`, `paths`, `started_monotonic_ns`, `started_utc`,
`outer_deadline_monotonic_ns`, and `status=started`. Each later irreversible or
otherwise unrecoverable observation is journaled before the next one:

1. before releasing the inherited start barrier, the outer fsync-publishes
   `case-CXX-boundary-attempt.json`, exact keys `schema_version`, `case_id`,
   `expected_registry_row`, `expected_reporter`, `fault_endpoint_binding`,
   `state=attempt_not_released`, and `started_utc`; it then releases the child;
2. the credentialed boundary datagram is fsync-published as
   `case-CXX-boundary.json` before reconstructing the live subject;
3. the complete `outer_before` is fsync-published as `case-CXX-before.json`;
4. before the first signal/resume, `case-CXX-action-attempt.json` is
   fsync-published with exact keys `schema_version`, `case_id`,
   `boundary_event_sha256`, `before_sha256`, `action_enum`, `target`,
   `intended_steps`, `state=attempt_not_released`, and `started_utc`;
5. the completed action object is fsync-published as
   `case-CXX-action-result.json`;
6. the descriptor-reopened canonical owner ledger is fsync-published as
   `case-CXX-owner-ledger.json` before the inherited scratch ledger may be
   unlinked; and
7. only then is `case-CXX-result.json` published with exact keys
   `schema_version`, `case_id`, `boundary_event`, `before`, `action`,
   `owner_ledger`, `outer_result`, `ended_utc`, and `status=passed`.

These files form one exact per-case prefix, and completed case results form a
C00-C09 prefix. No next start is permitted before the prior result fsync.

An interruption before the attempt descriptor is durable is restartable because
no child barrier or tmux action may be released. Any interruption afterward is
terminally negative and no case may rerun. A child spawned before its start row
remains behind the inherited barrier and exits on parent/control EOF; after a
start row, only its validated launcher/record identities authorize emergency
extinction. Recovery publishes `interruption.json`, schema
`msae_v3_gen8_containment_interruption_v1`, exact keys `schema_version`,
`test_token`, `completed_case_ids`, `active_case_id`, `validated_cleanup`,
`active_evidence`, `tripwires`, `namespace_absence`, `detected_utc`, and `outcome`, where
outcome is `interrupted_overall_fail`. `active_case_id` and `active_evidence`
are both null exactly when no start row follows the durable completed-result
prefix: descriptor-only before C00, between two cases, or after C09 result.
That is the exact `no_active_case` state; cleanup is an identity-bound no-op
process action transcript plus full namespace/lease absence verification. A
complete C00-C09 result prefix without durable `report.payload` is conservatively
terminal interruption, not pass; an exact already-durable pass payload is
finished by the hard-link recovery below.

When a start row does follow the completed prefix, `active_case_id` is that
literal next case and `active_evidence` has exact keys `phase`,
`boundary_attempt`, `boundary_event`, `before`, `action_attempt`, `action`, and
`owner_ledger`. Phase is exactly `before_release`,
`boundary_attempted_unknown`, `after_boundary`, `after_before`,
`action_attempted_unknown`, `after_action`, or `after_owner_ledger`. A durable
boundary-attempt row without a boundary row is preserved with
`state=attempted_unknown`; it means only that release/observation may have
started. It makes no claim about the reporter's pre-crash state; recovery uses
the start-row launcher authority plus descriptor-reopened inherited durable
identity records and descriptor-safe current `/proc` observations, proves final
extinction, and proves no post-boundary action was
released. A durable action-attempt row without an
action-result row is preserved as the full tagged attempt object with
`state=attempted_unknown`; recovery never claims whether its first syscall
occurred and never retries it. Every other present member is its full canonical
typed preimage, never a bare digest. `before_release` has a start row but no
boundary-attempt row and therefore proves the barrier remained closed.
`validated_cleanup` has the same exact eight-key schema as
`failure.emergency_cleanup` below and must be completed true.

The terminal containment report always has exact keys `schema_version`,
`terminal_variant`, `plan_sha256`, `plan_review_sha256`,
`pre_containment_review_sha256`, `implementation_entries`, `command`,
`python_argv`, `environment`, `case_results`, `outer_results`, `interruption`, `failure`,
`tripwires`, `started_utc`, `ended_utc`, and `overall_pass`.
`schema_version` is the literal `msae_v3_gen8_tmux_containment_v1`.
`case_results` elements are exact `case-CXX-result.json` objects;
`outer_results` elements are their exact `outer_result` members in the same
order. `tripwires` is one exact tagged union. For pass or caught case failure,
schema `msae_v3_gen8_tripwire_counts_v1` has exact keys `schema_version`,
`gpu_query`, `model_import`, `model_call`, `sealed_open`,
`unregistered_process`, and `environment_activation`; integer counters equal
the completed-case sum plus the active caught-failure snapshot. For process
interruption, schema `msae_v3_gen8_tripwire_interruption_v1` has exact keys
`schema_version`, `completed_prefix_counts`, and `active_case_state`;
`completed_prefix_counts` is the exact complete six-counter sum of durable case
results and `active_case_state` is `no_active_case` exactly when active case/evidence
are null, otherwise `unknown_after_interruption`. It never claims a transient
active count that was not durably journaled. Nested failure uses the
complete-count schema; nested interruption uses the interruption schema.

- `terminal_variant=pass`: both arrays contain C00–C09 in order;
  `interruption`/`failure` are null; complete tripwire counters are zero;
  overall pass is true.
- `terminal_variant=case_failure`: arrays contain the completed passing prefix
  only and have equal length; `interruption` is null; `failure` equals canonical
  `failure.json`, with exact keys `schema_version`, `case_id`, `phase`,
  `error_code`, `boundary_attempt`, `boundary_event`, `before`, `action_attempt`, `action`,
  `owner_ledger`, `tripwires`, `emergency_cleanup`, and `namespace_absence`. Phase is one of
  the seven phases above. Its evidence members obey the same exact
  prefix/null/`attempted_unknown` rules as `active_evidence`.
  `emergency_cleanup` has exact keys `actions`, `errors`, `processes_extinct`,
  `groups_empty`, `session_absent`, `paths_absent`, `lease_reacquired`, and
  `completed`; actions/errors preserve the full ordered emergency transcript.
  It is non-null and completed true before terminal publication. Overall pass is
  false.
- `terminal_variant=interrupted`: arrays contain only the completed prefix;
  `interruption` equals the canonical interruption row with every available
  active typed preimage plus full `validated_cleanup` action/error transcript;
  its and the report's tripwire objects equal the interruption variant above;
  `failure` is null;
  overall pass is false.

No other lengths/null combinations are legal. Emergency fallback while the
original outer remains live in a caught case produces `case_failure`, never
pass. Recovery-owned validated cleanup after outer/process interruption
produces `interrupted`, never `case_failure`; mutations exchanging those
variants must fail. The attempt descriptor plus its ordered journal
reconstructs the one terminal report. It is written as `report.payload`,
NFS-hard-link published as `tmux_containment.json`, then the exact transaction
is removed. A completed negative report terminates gen8; a report with stale
implementation hashes cannot authorize capability.

The sole authorized command is:

`/usr/bin/env -i HOME=/tmp LANG=C LC_ALL=C PATH=/usr/bin:/bin PYTHONDONTWRITEBYTECODE=1 PYTHONHASHSEED=0 PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 TMPDIR=/tmp TZ=UTC /jumbo/lisp/f004ndc/experiments/wip/MSAE/.venv-atlas/bin/python -B -I -m pytest -q -p no:cacheprovider /jumbo/lisp/f004ndc/experiments/wip/MSAE/tests/test_msae_independent_measurement_v3_post_m8_gen8.py::test_gen8_registered_real_tmux_containment`

`command` binds that full outer vector and `python_argv` binds its absolute
suffix beginning with the venv Python. Its cwd is
`/jumbo/lisp/f004ndc/experiments/wip/MSAE`; the Python environment is exactly
`HOME=/tmp`, `LANG=C`, `LC_ALL=C`, `PATH=/usr/bin:/bin`,
`PYTHONDONTWRITEBYTECODE=1`, `PYTHONHASHSEED=0`,
`PYTEST_DISABLE_PLUGIN_AUTOLOAD=1`, `TMPDIR=/tmp`, and `TZ=UTC`. No inherited
variable is allowed. Active tripwires reject GPU/model/sealed access,
unregistered process vectors, or forbidden environment activation.

Unit tests inject an exception into each inherited cleanup operation ID and
assert later operations still run. This is unit evidence only; it is not
misdescribed as every-boundary real-process proof.

## Capability report contract

Capability is one create-once observation, separate from containment.
Immediately before any write or probe syscall, `_pre_capability_namespace_gate`
reopens and validates the plan, plan review, failure review, changed-regions
manifest, pre-containment review, passing containment report, and
pre-capability review; requires the seven implementation bytes and every
embedded digest current; closes the adversarial and analysis roots to their
exact phase child sets; requires every downstream gen8 config/provenance/M4/
key/state/run/build path absent; enumerates all seven short families absent;
requires the capability probe root absent; and repeats the exact quarantine
lstat subject with zero reads. A future/malformed review, stale evidence,
transaction sibling, downstream artifact, or family sibling blocks before a
write. `_validate_capability_report` repeats the same current-subject gate when
reconstructing a final report.

Before its first syscall observation it fsync-publishes mode-0600
`.capability_report_transaction/transaction.json`, schema
`msae_v3_gen8_capability_attempt_v1`, exact keys `schema_version`,
`plan_sha256`, `plan_review_sha256`, `pre_containment_review_sha256`,
`pre_capability_review_sha256`, `implementation_entries`,
`change_manifest_sha256`, `tmux_containment_sha256`, `failed_gen7_sha256`,
`argv`, `python_argv`, `cwd`, `environment`, `started_utc`, and
`status=started`.
Creation/fsync of the empty exact mode-0700 capability transaction may precede
the descriptor. A crash there is restartable after the entire pre-capability
gate repeats and may remove only that held, still-empty directory; any child or
identity drift blocks.

The sole exact outer capability command is the following token vector (the
review digest is substituted as one 64-lowerhex token):

`/usr/bin/env -i HOME=/tmp LANG=C LC_ALL=C PATH=/usr/bin:/bin PYTHONDONTWRITEBYTECODE=1 PYTHONHASHSEED=0 TZ=UTC /jumbo/lisp/f004ndc/experiments/wip/MSAE/.venv-atlas/bin/python -S -B -I /jumbo/lisp/f004ndc/experiments/wip/MSAE/scripts/msae_independent_measurement_v3_post_m2_gen8.py probe-gen8-capability --pre-capability-review-sha256 <review-sha256> --output /jumbo/lisp/f004ndc/experiments/wip/MSAE/reports/analysis/msae_independent_measurement_v3_post_m2_gen8/gen8_capability_reproduction.json`

`argv` records that entire absolute vector including `/usr/bin/env`; the exact
`python_argv` is the suffix beginning with the absolute venv Python path. Cwd
is `/jumbo/lisp/f004ndc/experiments/wip/MSAE`. The Python entrypoint requires
`os.environ` to equal exactly the seven-key sorted map `HOME=/tmp`, `LANG=C`,
`LC_ALL=C`, `PATH=/usr/bin:/bin`, `PYTHONDONTWRITEBYTECODE=1`,
`PYTHONHASHSEED=0`, and `TZ=UTC`, with no `LD_PRELOAD`, `PYTHONPATH`, or other
inherited entry. The attempt descriptor, report, review row, and independent
reconstruction all bind the full map. It never reads protocol/M3 state,
invokes tmux, queries a GPU, or imports/calls a model.

Six checks run in this literal order. Before the first syscall of a check, the
probe fsync-publishes `check-0N-start.json`, exact keys `schema_version`, `id`,
`started_utc`, `intended_observation`, and `state=attempt_not_released`. It then
releases that syscall. On completion it fsync-publishes
`check-0N-result.json`; only then may the next start row be published:

`intended_observation` has exact keys `schema_version`, `check_id`, `operation`,
`registered_targets`, and `result_schema_version`. Operations in order are
`invoke_renameat2_capability`, `attempt_overlength_bind`,
`round_trip_short_sockets`, `reconstruct_changed_regions`,
`reconstruct_containment`, and `reconstruct_failed_gen7`. Targets are the
literal path/object rows named by the corresponding check below, path-sorted;
result schema versions are the exact inherited or gen8 row schemas below.

1. `gen4_nfs_renameat2_reproduction`: exact inherited gen7 observation schema
   and syscall semantics;
2. `gen5_overlength_socket_rejections`: exact two inherited observations for
   the frozen 119-byte tmux and 129-byte broker paths;
3. `gen8_short_socket_round_trips`: exact three inherited Python-created socket
   observations for m8t/m8b/m8p, each full encoded path length 78;
4. `gen8_changed_region_manifest_reconstruction`;
5. `gen8_containment_report_reconstruction`;
6. `gen7_failure_reconstruction`.

Every check row has exact keys `id`, `outcome`, `reason_codes`, and
`observations`; outcome is `pass|fail`, and reason codes are empty exactly on
pass. Rows 1–3 retain their frozen nested observation schemas after ordered
substitution. Rows 4–6 each contain exactly one observation with exact keys
`id`, `path`, `entry_sha256`, `reconstructed_sha256`, `subject_sha256`, and
`outcome`. For row 4, path is the canonical changed-region manifest path,
entry/reconstructed digests match, and subject is the seven-entry map digest.
For row 5, path is `tmux_containment.json`, the descriptor-reopened entry and
independent terminal-report reconstruction match, terminal variant is pass,
and the embedded implementation subject matches current bytes. For row 6, path
is the predicted `failed_gen7.json` target, entry SHA is the predicted canonical
payload digest (not a nonexistent file read), independent reconstruction
matches, and subject is the ten-entry frozen-gen7 map digest.

The terminal capability report schema is
`msae_v3_gen8_capability_reproduction_v1`, exact keys `schema_version`,
`terminal_variant`, `protocol_id`, `writer_generation`, `argv`, `python_argv`,
`cwd`, `environment`,
`started_utc`, `ended_utc`, `plan_entry`, `plan_review_entry`,
`pre_containment_review_entry`, `pre_capability_review_entry`,
`implementation_entries`, `change_manifest`, `tmux_containment_entry`,
`failed_gen7_entries`, `tmp_parent_binding`, `checks`, `failure`,
`interruption`, `overall_pass`, `probe_root`, `protocol_path_used`,
`model_gpu_tmux`, and `sealed_payload_content_reads`.

- `terminal_variant=pass`: all six complete rows are present and pass;
  failure/interruption are null; overall pass true.
- `terminal_variant=check_failure`: checks contain the completed prefix through
  the failing full row; `failure` has exact keys `schema_version`, `check_id`,
  `observation`, `reason_codes`, `validated_cleanup`, and
  `namespace_absence`; interruption is null; overall pass false.
- `terminal_variant=interrupted`: checks contain only the durable completed
  prefix; `interruption` has exact keys `schema_version`, `completed_check_ids`,
  `active_check_id`, `active_check_start`, `active_observation`, `validated_cleanup`,
  `namespace_absence`, and `detected_utc`; failure is null; overall pass false.

In both negative variants, `validated_cleanup` has exact keys
`probe_root_absent`, `socket_paths_absent`, `tmp_parent_unchanged`, `errors`,
and `completed`; the first three and `completed` are true before publication,
and `errors` is the ordered full canonical cleanup-error array (empty on clean
recovery). `active_check_id`, `active_check_start`, and `active_observation`
are all null when no start row
follows the completed-result prefix: descriptor-only, between checks, or after
check 06. A start row with no result makes the ID/start non-null and yields the
exact tagged `active_observation={"state":"attempted_unknown"}`; the validator
never claims whether the first syscall occurred and recovery never reruns the
check. A completed failing observation is the full typed check preimage, not a
digest. Six passing results without durable `report.payload` recover as terminal
interruption; an exact durable pass payload is linked and remains pass.

`protocol_id` and writer generation are the gen8 literals. Entries are exact
regular content entries. `change_manifest` is the full canonical manifest,
`failed_gen7_entries` is the ten-entry frozen subject, timestamps are strict UTC
seconds, probe root is the exact registered gen8 capability root,
`protocol_path_used=false`, `model_gpu_tmux=false`, and sealed reads zero.
`overall_pass` is true iff terminal variant is pass, all six rows pass, current
pre-capability namespace/short families are exact, probe root is absent, and all
evidence bindings reconstruct.

An interruption before the attempt descriptor is durable is restartable because
no observation has run. After it is durable, checks never rerun. The only legal
journal states are descriptor only; a completed result prefix; that prefix plus
the next start row; `failure.json`/`interruption.json`; `report.payload`; or the
final report hard-linked to that same inode/content. Re-entry validates the
exact prefix and cleans only descriptor-bound probe/socket objects. A
start-without-result is preserved as `attempted_unknown`, writes
`interruption.json`, and publishes a terminal false report. Final absent plus
exact payload is completed
by linking; final present must be the same inode/content before transaction
cleanup. Drift, holes, reordered rows, or extra children block without write.
A durable failing result takes precedence: re-entry reconstructs and writes
`failure.json`/`terminal_variant=check_failure` from that full row. Only a
start-without-result, or a process interruption after a passing result prefix
and before the next start, becomes `attempted_unknown`/`interrupted`; a passing
prefix continues only inside the original uninterrupted invocation. The final
canonical bytes are written to `report.payload`,
NFS-hard-link published create-once, then the transaction is removed. A separate
validator does not call the report builder: it reparses the exact journal,
reopens review/evidence entries, independently reconstructs change/failure/
containment projections, validates inherited observation schemas and current
absence, and requires canonical byte equality. Any negative report terminates
gen8.

## Reviews and one-way sequence

Every review is canonical UTF-8, LF, final newline, mode 0644, current UID/GID,
nlink 1, no symlink ancestor, and starts with one contiguous exact control
block. Control lines use literal `KEY: VALUE`; unknown, duplicate, malformed,
indented, conflicting, or out-of-order control-like lines block. Prose may
follow one blank line but may not contain a line whose stripped text begins
with any registered control key.

The reusable command evidence row is one-line canonical JSON after literal
`CHECK_ROW_JSON: `. Schema `msae_v3_gen8_review_check_v1` has exact keys
`schema_version`, `id`, `subject_sha256`, `argv`, `cwd`, `environment`,
`started_utc`, `ended_utc`, `exit_code`, `stdout_sha256`, `stderr_sha256`, and
`summary`. `environment` is an exact sorted map, not a digest of ambient state.
Timestamps are strict UTC seconds. Unknown values are JSON null only when the
scope below expressly permits them; passing gate rows require non-null argv,
cwd, environment, times, exit code zero, and both transcript digests.
`CHECKS_SHA256` is the SHA-256 of the canonical ordered row array, and the
number of subsequent rows equals `CHECK_COUNT`.

The exact control blocks are:

1. `gen8_plan`: `VERDICT`, `REVIEW_SCOPE`, `PLAN_SHA256`,
   `SEALED_CONTENT_READS`; values are `SHIP`, `gen8_plan`, this plan digest, and
   `0`. No check rows.
2. `gen8_pre_containment`: `VERDICT`, `REVIEW_SCOPE`, `PLAN_SHA256`,
   `PLAN_REVIEW_SHA256`, `GEN7_FAILURE_REVIEW_SHA256`, `GEN8_CONTROLLER_SHA256`,
   `GEN8_RUNTIME_SHA256`, `GEN8_RUNNER_SHA256`, `GEN8_LAUNCHER_SHA256`,
   `GEN8_TMUX_TEST_SUPERVISOR_SHA256`, `GEN8_RFC_SHA256`, `GEN8_TESTS_SHA256`,
   `CHANGE_MANIFEST_SHA256`, `SAFE_CHECKS_SHA256`, `NAMESPACE_SHA256`,
   `SEALED_LSTAT_SHA256`, `SEALED_CONTENT_READS`, `CHECKS_SHA256`, and
   `CHECK_COUNT`, followed by exactly 14 rows in ID order `v1`, `v2`, `v3`,
   `post_m1`, `post_m2`, `remediation`, `gen4`, `gen8_cpu`, `gen8_publisher`,
   `gen8_source_only`, `in_memory_compile`, `bash_syntax`, `diff_check`, and
   `changed_regions_publication`. `SAFE_CHECKS_SHA256` is the digest of the
   first 13-row prefix; `CHECKS_SHA256` is the digest of all 14 rows. The final
   row binds the literal writer argv/environment above, exit zero, canonical
   stdout/stderr transcripts, and the published manifest digest.
3. `gen8_pre_capability`: `VERDICT`, `REVIEW_SCOPE`, `PLAN_SHA256`,
   `PLAN_REVIEW_SHA256`, `PRE_CONTAINMENT_REVIEW_SHA256`, the same seven
   `GEN8_*_SHA256` controls in the same order, `CHANGE_MANIFEST_SHA256`,
   `TMUX_CONTAINMENT_SHA256`, `NAMESPACE_SHA256`, `SEALED_LSTAT_SHA256`,
   `SEALED_CONTENT_READS`, `CHECKS_SHA256`, and `CHECK_COUNT`, followed by one
   passing row `tmux_containment` whose argv/environment equal the literal
   command above and whose subject is the canonical seven-entry map digest.
4. `gen8_implementation`: `VERDICT`, `REVIEW_SCOPE`, `PLAN_SHA256`,
   `PLAN_REVIEW_SHA256`, `PRE_CONTAINMENT_REVIEW_SHA256`,
   `PRE_CAPABILITY_REVIEW_SHA256`, the same seven `GEN8_*_SHA256` controls,
   `CHANGE_MANIFEST_SHA256`, `TMUX_CONTAINMENT_SHA256`,
   `CAPABILITY_REPORT_SHA256`, `PREDICTED_FAILED_GEN7_SHA256`,
   `NAMESPACE_SHA256`, `SEALED_LSTAT_SHA256`, `SEALED_CONTENT_READS`,
   `CHECKS_SHA256`, and `CHECK_COUNT`, followed by one passing row
   `capability_reconstruction`.
5. `gen8_post_m3`: `VERDICT`, `REVIEW_SCOPE`, `PLAN_SHA256`,
   `PLAN_REVIEW_SHA256`, `IMPLEMENTATION_REVIEW_SHA256`,
   `M3_SUBJECT_SHA256`, `PRIVATE_KEY_LSTAT_SHA256`, `NAMESPACE_SHA256`,
   `SEALED_LSTAT_SHA256`, `SEALED_CONTENT_READS`, `CHECKS_SHA256`, and
   `CHECK_COUNT`, followed by one passing row `m3_reconstruction`. The private
   key content remains unread.
6. `gen8_prescore`: `VERDICT`, `REVIEW_SCOPE`, `PLAN_SHA256`,
   `PLAN_REVIEW_SHA256`, `POST_M3_REVIEW_SHA256`, `STAGE_A_SHA256`,
   `CLOSURE_SHA256`, `CANDIDATE_MANIFEST_SHA256`, `PRESCORE_CHECK_SHA256`,
   `PRESCORE_TRACE_SHA256`, `NAMESPACE_SHA256`, `SEALED_LSTAT_SHA256`,
   `SEALED_CONTENT_READS`, `CHECKS_SHA256`, and `CHECK_COUNT`, followed by one
   passing row `external_prescore` with the exact isolated reviewer argv.

All SHA controls are lowercase 64-hex and reconstruct from descriptor-opened
canonical inputs. Scope names and control order above are literal. The phase
validator closes the shared adversarial directory to this exact gen8-prefixed
sibling progression: before plan review `{}`; after plan review `{plan}`; after
pre-containment `{plan,pre_containment}`; after pre-capability
`{plan,pre_containment,pre_capability}`; after implementation
`{plan,pre_containment,pre_capability,implementation}`; after post-M3 add only
`post_m3`; after prescore add only `prescore`. A future review, backup, symlink,
or similarly prefixed sibling blocks before any write.

The one-way order is:

1. Plan review alone authorizes creation of the seven gen8 implementation files
   and safe CPU/NFS tests.
2. Freeze seven implementation bytes. Run the exact 13 safe checks.
3. Run the sole `build-changed-regions` command once; recover only its exact
   descriptor-bound prefix and require its final manifest reconstructs.
4. Pre-containment review alone authorizes the single exact real-tmux command.
5. The command creates its attempt descriptor before process/tmux action and
   publishes one terminal containment report. A completed/interrupted negative
   report ends gen8.
6. Pre-capability review alone authorizes the create-once capability
   observation. A completed negative report ends gen8.
7. Implementation review alone authorizes setup.
8. Post-M3 review alone authorizes M4.
9. Prescore review alone authorizes one signature; only that signature and the
   exact unused nonce authorize launcher entry. The runner alone consumes the
   nonce after its pre-model gate.

No review authorizes a later door by implication. Code changes after
pre-containment review make the create-once containment report stale and
terminate gen8; they do not authorize rewriting it.

## Setup and downstream inheritance

Gen8 setup keeps gen7's exact 24-receipt DAG and manifest schema after ordered
generation substitution. The only step substitution is receipt 0002: its name
is `0002_failed_gen7.json`, step is `failed_gen7`, action is `publish`, and
target is the gen8 provenance-root `failed_gen7.json`. It replaces rather than
supplements gen7's prospective `failed_gen6` receipt because the canonical
failed-gen7 payload transitively binds the frozen gen7 plan and its failure
review; no extra receipt or ordinal shift exists.

Receipts 0001 and 0003–0024 retain their gen7 step/action ordering after
generation substitution. The exact setup manifest remains
`msae_v3_gen8_setup_manifest_v1` with keys `schema_version`, `protocol_id`,
`generation`, `status`, `lineage`, `transaction_sha256`,
`receipt_sha256_through_0023`, `receipt_0024_derivation`, `setup_subject`, `setup_subject_sha256`,
`final_entries`, and `exact_child_sets`. Its receipt map contains literal names
0001–0023, including `0002_failed_gen7.json`; `receipt_0024_derivation` has
exact schema `msae_v3_gen8_setup_receipt_0024_derivation_v1` and keys
`schema_version`, `index`, `step`, `action`, `target`,
`predecessor_receipt_sha256`, and
`payload_is_setup_manifest_sha256`. It binds index 24, the literal receipt-0024
table row, receipt-0023 digest, and JSON true. Receipt 0024
then binds the manifest digest; the manifest never binds receipt 0024, avoiding
a cycle.

`final_entries` is the exact gen7-substituted typed projection with the sole
record replacement `failed_gen6→failed_gen7`: same position, mode, owner, and
verification action, but gen8 failed-gen7 canonical bytes/digest. No
`failed_gen6` output is published. `exact_child_sets` is the exact substituted
gen7 root projection with provenance child `failed_gen6.json` replaced by
`failed_gen7.json` and no other addition/removal. `status`, `lineage`, setup
subject, final entries, and child sets otherwise retain the inherited exact
values after substitution.

Every descriptor embeds non-recomputable payload bytes. Unexpected prefix
states or namespace children block before a write. Recovery accepts only exact
ordered publication prefixes and performs descriptor-safe reverse cleanup when
required.

M3, M4, Stage A, closure, prescore, authorization, nonce, GPU lease, runner,
terminal-success, and terminal-failure schemas otherwise inherit gen7 after
literal substitution. Candidate construction uses two complete independent
sparse roots, source-only local loading, exact five-file model snapshot, exact
executable/ELF closure, deterministic environment, full status/directory
projection, and no live-repository fallback. Private-key content is confined to
setup agreement and signing; public verification never opens it.

The runner exposes exactly one of terminal success or technical failure. A
successful terminal contains the inherited six files and durable cache
directories; failure never masquerades as scientific ineligibility. Stage B
QA is mechanically reconstructed. Confirmation and Stage C remain absent.

## Milestones

### M0 — freeze failure evidence and obtain plan authority

- [x] Freeze exact gen7 subject and independent BLOCK review.
- [x] Confirm gen7 capability/scientific namespaces remain absent using lstat
  and no sealed content reads.
- [ ] Obtain create-once independent `SHIP` review of this exact plan.

Acceptance: plan/review SHA pair exists; no gen8 implementation or one-way
state exists before review.

### M1 — structural successor and safe gates

- [ ] Create exactly seven gen8 files by controlled substitution.
- [ ] Implement the changed-region comparator and honest failed-gen7 payload.
- [ ] Implement exact review/namespace/short-family gates.
- [ ] Keep scientific and authorization nodes identical under normalization.

Acceptance: structural manifest covers every delta exactly once; mutation tests
reject scientific drift, unclassified control drift, stale reviews, extra
names, PYC/extension shadows, and sealed-path access.

### M2 — durable containment evidence

- [ ] Implement transactional canonical containment report.
- [ ] Implement C00–C09 through the actual production helper.
- [ ] Add active tripwires and named cleanup-phase mutation tests.
- [ ] Run safe suites, freeze bytes, publish/reconstruct the changed-regions
  manifest once, obtain pre-containment `SHIP`, then run the one authorized
  real-tmux command.

Acceptance: `tmux_containment.json` is canonical, `overall_pass=true`, bound to
the exact seven hashes, emergency cleanup false for every case, all test
namespaces absent afterward, and no GPU/model/protocol state created.

### M3 — capability and setup

- [ ] Obtain pre-capability `SHIP` on unchanged bytes/evidence.
- [ ] Run create-once capability; require overall pass.
- [ ] Obtain implementation `SHIP`.
- [ ] Run recoverable setup and validate all 24 receipts plus M3.

Acceptance: capability and M3 independently reconstruct; the failed-gen7
record is honest and transitively preserves gen6; private key is mode 0600 and thereafter content-unread
outside signing; no M4/run/nonce output exists.

### M4 — independent build and external prescore

- [ ] Obtain post-M3 `SHIP`.
- [ ] Build/compare two sparse roots and install M4 recoverably.
- [ ] Run exact isolated traced prescore check and obtain external `SHIP`.

Acceptance: both trees and all M4 bytes match, no live fallback/undeclared
surface occurs, build roots disappear, and prescore revalidates complete
candidate/protected/quarantine/current-state projections.

### M5 — sign and launch

- [ ] Sign once after prescore SHIP.
- [ ] Launch once through the exact signed envelope.
- [ ] Return after durable live handoff; do not wait for results.

Acceptance: launcher-selected idle GPU is locked/rechecked, the runner alone
consumes the nonce, model import occurs only after both durable gate phases,
the persistent monitor owns the lease after return, and no confirmation/Stage C
is run.

## Verification plan

Before pre-containment review, run in separate closed processes:

1. the seven passing predecessor suites registered by gen7 (with only their
   already-registered real-tmux exclusions);
2. the complete gen8 CPU/static suite excluding only the exact real-tmux node;
3. exact NFS publisher and local-mount rejection nodes;
4. source-only malicious timestamp-PYC, sourceless-PYC, and extension-shadow
   regressions;
5. in-memory compilation (never `py_compile`) of the five Python entries;
6. `bash -n` on the launcher and `git diff --check`;
7. direct structural-manifest reconstruction and exact namespace/sealed lstat
   checks.

After those 13 rows pass on frozen bytes, run only the exact
`build-changed-regions` command, record its fourteenth review row, and require
descriptor-independent manifest reconstruction before pre-containment review.

After pre-containment SHIP, run only the registered real-tmux pytest node under
the exact closed environment and record exact argv/cwd/start/end/exit/transcript
in the containment report. No other tmux command is review evidence.

Every milestone includes negative tests for malformed schemas, duplicate
controls, symlink/hardlink/mode/owner drift, partial writes, unexpected
children, short writes, process-identity forgery, socket substitution, timeout,
and transaction recovery appropriate to that slice.

## Definition of done

- Gen7 remains byte-identical and is preserved as failed before capability.
- Independent reviews bind this plan and every later one-way transition.
- Every gen7→gen8 source delta is covered by the structural comparator, and no
  unreviewed scientific/authorization AST changes.
- Safe predecessor/gen8/publisher/source-only checks pass on final bytes.
- C00–C09 run through production helper bytes and produce a durable passing
  transcript with no emergency cleanup, GPU, model, or protocol mutation.
- Capability and setup are performed only after their exact reviews; all
  recovery paths are prefix-exact and descriptor-safe.
- M4 is a two-tree no-live-fallback realization and receives external prescore
  SHIP before signing.
- Launcher returns after durable monitored handoff on a selected idle locked
  GPU; terminal output is unambiguous; confirmation and Stage C remain absent.

## Risks and one-way doors

- **Plan review:** freezes this scope. A material change requires gen9.
- **Containment report:** completed negative or stale report terminates gen8.
- **Capability report:** completed negative terminates gen8.
- **Setup receipts/M3, M4, review files, signature, nonce consumption, and
  launch:** create-once transitions; recovery may complete an authenticated
  prefix but never rewrite history.
- **External review dependence:** the structural comparator proves scope, not
  semantic safety of control-plane nodes. Independent exact-byte review is
  deliberately required and must not be described as an automated proof.
- **Tmux/process races:** mitigated by foreground server ownership, bounded
  clients, peer credentials, start ticks/PGIDs, complementary authorities,
  lease-last cleanup, real-process cases, and fail-closed emergency handling.
- **NFS publication:** mitigated by content-embedding descriptors, identity-
  bound hard-link publication, parent-directory fsync, NFS settling, and exact
  crash recovery.

No one-way door is crossed merely because tests pass. The next authorized
action after this plan is independent plan review, not implementation.
