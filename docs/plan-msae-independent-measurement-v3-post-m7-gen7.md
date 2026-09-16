# PLAN — MSAE independent measurement v3 post-M7 gen7

## Status and authority

This is a prospective control-plane recovery generation. It does not revise,
overwrite, or reinterpret any prior plan, review, implementation, protocol,
Stage A, or experimental result. Gen7 has no authority until this exact plan is
independently reviewed `SHIP` and that create-once review binds this plan's
SHA-256.

Gen6 is terminally **failed before capability**. No gen6 capability report,
pre-capability review, implementation review, M3 state, M4 output, Stage A,
authorization, GPU query, model call, calibration, or scientific result was
created. Its plan-authorized CPU/NFS publisher and fake-broker tmux containment
tests were non-scientific checks only.

The terminal gen6 implementation subject is:

- plan `dc5e72ebd015acdeb1bbe472ca0d1a275e976fb07f3b5af51251bec66ca0c6ac`;
- plan review `852d6acd0b6ead8df5b7b4aa316dfa766cee2be799513781bedb9f6d85fcaba5`;
- controller `3a2b22d87be6fe7dcbb74af38a7a44081c8ee135cc49d769e7a77f14bd7d6044`;
- runtime `a17828e2edc64a92dc2b380311cf3893b119342e533e7e3281f92e7e7bae851c`;
- runner `4bd6f7d51acd15b50604416687670cc0e39962ae55eb290ead8011a547542766`;
- launcher `5828e678487babde4e39672fb0cfb3632b57d11b57c151a2f0840e84e4b7f8b3`;
- tmux-test supervisor `bda74348cf2ea151c0cea4b2834a0600712ceef9c147af1a6e73c31f99091399`;
- RFC `0109cf1ff4d1e6b4a676fdf1abe6615df1a7b29910645b42cdbd93ac0616edc3`;
- tests `fec77df62d7e08ec6481df9f376091209a437735b3164cd3200e0571b1579c6b`.

The exact gen6 failure review is
`reports/adversarial/msae_independent_measurement_v3_post_m2_gen6_failure.md`,
SHA-256 `2f79df9b3273cab6d880a525f682e70c589b926109861325a8c9367635d70928`.

## Goal

Produce a disjoint gen7 protocol generation that:

1. preserves gen6 as failed before capability;
2. resolves the impossible gen6 test-pass contract without weakening any
   successful predecessor guard;
3. uses one shared, source-only production tmux start/control implementation in
   both production and the authorized real-process containment test;
4. validates every frozen tmux monitor/start/failure boundary before any
   create-once capability or protocol state;
5. carries forward unchanged scientific source, overlap, calibration, Stage-A,
   Stage-B, endpoint, signed-authorization, nonce, free-GPU, and no-Stage-C
   semantics; and
6. only after all independent reviews and Stage-A/prescore gates, launches the
   calibration replay in tmux on a launcher-selected idle GPU and returns after
   durable live handoff without waiting for results.

## Non-goals

- Do not reinterpret gen5 or gen6 as passing.
- Do not alter the source corpus, overlap decisions, calibration strata,
  checkpoint registry, endpoint registry, thresholds, maps, Stage-A schema,
  Stage-B QA, model, tokenizer, environment, or inference closure.
- Do not run confirmation scoring or build Stage C.
- Do not query GPUs, import/call a model, create a scientific tmux session, sign
  authorization, or consume a nonce before the corresponding reviewed gates.
- Do not content-read, open, or hash the three sealed payloads listed below.
- Do not modify any frozen predecessor file to make its historical tests green.

## Immutable safety constraints

The following payloads are metadata-only forever in this workflow:

- `data/atlas_v1/private/final.jsonl`;
- `data/atlas_v1/private/final.records.jsonl`;
- `data/atlas_v1/private/final.units.jsonl`.

Every verifier, builder, reviewer, signer, launcher, test, and recovery entry is
under the existing sealed-open tripwire and compares exact before/after `lstat`
subjects. Content reads, hashes, same-inode aliases, symlink ancestors, and
link-count drift block.

Only the signed launcher may query GPUs. It selects a GPU satisfying the frozen
idle rule, locks the protocol-independent UUID object, rechecks idleness under
that lock, and passes the held lease through the monitored handoff. No manual
GPU query is authorized.

The only authorized pre-capability tmux activity is the exact fake-broker
containment command registered below. It has process/GPU/model/environment
tripwires and may not touch protocol, capability, GPU-lock, run, key, nonce,
Stage-A, or calibration state.

## Frozen predecessor interpretation

### Passing predecessor suites

“Passing predecessor suite” in gen7 means only a generation whose terminal
authority claims those tests as a success gate. Each suite is run in its own
closed process so Python module caches and monkeypatch state cannot cross
generations:

1. `tests/test_msae_independent_measurement_v1.py`;
2. `tests/test_msae_independent_measurement_v2.py`;
3. `tests/test_msae_independent_measurement_v3.py`;
4. `tests/test_msae_independent_measurement_v3_post_m1.py`;
5. `tests/test_msae_independent_measurement_v3_post_m2_runtime.py`, excluding
   only `failed_handoff_extinction_kills_real_processes_and_socket`, whose
   process/tmux role is superseded by the exact gen7 matrix;
6. `tests/test_msae_measurement_remediation_v1.py`;
7. `tests/test_msae_independent_measurement_v3_post_m4_gen4.py`, excluding only
   its registered real-process/tmux test when the separate exact command is not
   being run.

Every selected test must pass. Combined-process summaries are diagnostic only;
they cannot replace isolated successful-suite evidence.

### Failed-generation suites

The frozen gen5 and gen6 implementations are terminal failed evidence, not
passing predecessors. Their exact source/test hashes are revalidated. Their
whole historical suites are never required to pass and are never cited as
successful verification. If run diagnostically, the full argv, subject hashes,
exit code, and failures are disclosed as historical negative evidence only.

This is not a waiver for gen7: every gen7 test and every passing predecessor
suite above must pass. No `xfail`, collection filter, plugin, environment
mutation, or wrapper may hide a gen7 or successful-predecessor failure.

### Gen6 terminal failure evidence

`failed_gen6.json` has schema `msae_v3_gen7_failed_gen6_evidence_v1` and exact
top-level keys:

`schema_version`, `protocol_id`, `generation`, `writer_generation`, `status`,
`terminal_fields`, `frozen_subject`, `review`, `checks`, `blockers`,
`namespace_absence`, `sealed_payload_metadata`, and `gen7_plan_authority`.

Exact nested schemas are:

- `terminal_fields`: exactly `pre_capability_review`, `capability`,
  `implementation_review`, `m3`, `m4`, `stage_a`, `authorization`, `gpu_query`,
  `model_call`, `calibration`, `confirmation`, and `stage_c`. The first six and
  `authorization` equal `not_created`; the remaining five equal `not_run`.
- `frozen_subject`: exactly the nine names `plan`, `plan_review`, `controller`,
  `runtime`, `runner`, `launcher`, `tmux_test_supervisor`, `rfc`, and `tests`.
  Every value is an exact content entry with keys `path`, `type`, `mode`, `uid`,
  `gid`, `nlink`, `size`, `sha256`, and `verification_action=content_rehash`.
- `review`: exactly `path`, `type`, `mode`, `uid`, `gid`, `nlink`, `size`,
  `sha256`, `verdict`, `blocker_count`, and `origin`; values bind the literal
  failure-review path/digest, `verdict=BLOCK`, `blocker_count=3`, and
  `origin=independent_adversarial_review`.
- `checks`: an ordered array whose row keys are exactly `id`, `evidence_class`,
  `subject_sha256`, `argv`, `cwd`, `environment`, `started_utc`, `ended_utc`,
  `transcript_sha256`, `transcript_available`, `exit_code`, `summary`, and
  `details`.
  Unknown timestamps/transcripts are JSON null with availability false; they
  are never invented. `evidence_class` is one of
  `operator_disclosed_current_subject`, `operator_disclosed_subject_unknown`,
  `independent_review_current_subject`, or `diagnostic_failed_generation`.
  Only exact final-subject runs may use `*_current_subject`; the two historical
  tmux pass summaries are `operator_disclosed_subject_unknown`, have null
  subject/transcript/timestamps, and are not pass-gate evidence. `details` is
  exactly `{}` for ordinary rows. The `pyc_cleanup` row instead uses exactly
  `{"before_present_paths":[...],"after_absent_paths":[...]}`; both arrays are
  the same sorted four literal ignored gen6 `.pyc` paths, proving removal
  without claiming a source change.
- `blockers`: exactly three rows, in review order, with keys `ordinal`,
  `severity`, `citation`, `one_line`, and `failure_review_sha256`. They preserve
  (1) impossible predecessor pass authority, (2) independent test launcher plus
  missing fault boundaries, and (3) post-`START_SERVER` Popen escaping monitor
  terminalization/cleanup. Every row binds the same exact failure-review digest.
- `namespace_absence`: exact ordered rows with keys `path`, `expected`,
  `lexists`, `kind`, and `phase`; it covers every gen6 review/capability/config/
  provenance/M4/key/state/run/build/test root and the complete `m6t_`/`m6b_`
  family projection. Every expected value is `absent`, every `lexists` false.
- `sealed_payload_metadata`: exactly `content_read_attempts` (zero),
  `before`, and `after`. `before` and `after` each have the three literal paths
  mapped to `path`, `type`, `mode`, `uid`, `gid`, `nlink`, `size`, `device`,
  `inode`, `ctime_ns`, and `mtime_ns`; the maps must be byte-equal.
- `gen7_plan_authority`: exactly `plan_path`, `plan_sha256`,
  `plan_review_path`, and `plan_review_sha256`.

The ordered `checks` rows preserve, without upgrading evidence, final-subject
gen6 CPU `161 passed, 1 deselected`, publisher `2 passed`, isolated successful
predecessors `301 passed, 1 deselected`, isolated gen4 `127 passed, 1
deselected`, combined diagnostic `693 passed, 14 failed, 4 deselected`, the
independent frozen-gen5 negative result from the failure review, and two
operator-disclosed non-scientific tmux pass summaries with unavailable subject
and transcript digests. The removed ignored `.pyc` names appear only in that
typed `pyc_cleanup` diagnostic row and make no claim of source mutation.

The payload is predicted before setup and bound by the gen7 implementation
review; setup publishes it create-once as receipt `0002_failed_gen6.json`, only
after receipt `0001_gen7_provenance_root.json` durably creates its parent.

## Gen7 namespaces

Gen7 uses only:

- plan `docs/plan-msae-independent-measurement-v3-post-m7-gen7.md`;
- plan review
  `reports/adversarial/msae_independent_measurement_v3_post_m2_gen7_plan.md`;
- frozen gen6 failure review
  `reports/adversarial/msae_independent_measurement_v3_post_m2_gen6_failure.md`;
- controller `scripts/msae_independent_measurement_v3_post_m2_gen7.py`;
- runtime `scripts/msae_independent_measurement_v3_post_m2_gen7_runtime.py`;
- runner `scripts/run_msae_independent_calibration_v3_gen7.py`;
- launcher `scripts/launch_msae_independent_calibration_v3_gen7.sh`;
- tmux-test supervisor
  `scripts/run_msae_independent_measurement_v3_post_m2_gen7_tmux_test.py`;
- RFC `docs/rfc-msae-independent-measurement-v3-post-m7-gen7.md`;
- tests `tests/test_msae_independent_measurement_v3_post_m7_gen7.py`;
- pre-capability review
  `reports/adversarial/msae_independent_measurement_v3_post_m2_gen7_pre_capability.md`;
- implementation review
  `reports/adversarial/msae_independent_measurement_v3_post_m2_gen7_implementation.md`;
- post-M3 review
  `reports/adversarial/msae_independent_measurement_v3_post_m2_gen7_post_m3.md`;
- prescore review
  `reports/adversarial/msae_independent_measurement_v3_post_m2_gen7_prescore.md`;
- config `configs/msae_independent_measurement_v3_post_m2_gen7/`;
- provenance `reports/provenance/msae_independent_measurement_v3_post_m2_gen7/`;
- M4 data `data/msae_independent_measurement_v3_post_m2_gen7/`;
- run `pilot_runs/20260821_msae_independent_measurement_v3_post_m2_gen7_calibration/`;
- private key
  `/jumbo/lisp/f004ndc/.msae_keys/independent_measurement_v3_post_m2_gen7_ed25519_private.pem`;
- state
  `/jumbo/lisp/f004ndc/.msae_state/independent_measurement_v3_post_m2_gen7/`;
- capability report
  `reports/analysis/msae_independent_measurement_v3_post_m2_gen7/gen7_capability_reproduction.json`;
- capability probe/test/build roots formed by exact `gen7` substitution in the
  gen6 names; and
- three live socket families `/tmp/m7t_<stage-a-sha256>.sock`,
  `/tmp/m7b_<stage-a-sha256>.sock`, and
  `/tmp/m7p_<stage-a-sha256>.sock`, each 78 encoded bytes. They are respectively
  the tmux-control, inherited launcher↔broker gate, and monitor↔pane lease
  channels; no listener serves more than its one typed protocol.

The disjoint containment-test namespace token is SHA-256 of canonical JSON
bytes (UTF-8, sorted keys, separators `(',', ':')`, one terminal LF) for this
exact object:

```text
{"implementation_sha256s":[<controller>,<runtime>,<runner>,<launcher>,<tmux-test-supervisor>,<rfc>,<tests>],"plan_sha256":<plan>,"schema_version":"msae_v3_gen7_test_token_preimage_v1"}\n
```

Every placeholder is a quoted 64-lowerhex string; array order is exactly as
shown. `test_token` is the lowerhex digest of those bytes. It uses only these
exact names:

- tmux socket `/tmp/m7x_<test-token>.sock` (78 bytes);
- ACK socket `/tmp/m7a_<test-token>.sock` (78 bytes);
- pane-lease socket `/tmp/m7c_<test-token>.sock` (78 bytes);
- scratch root `/tmp/m7s_<test-token>`;
- session `msae-independent-v3-gen7-containment`;
- children `monitor.json`, `process.json`, `.process.json.partial`,
  `monitor.log`, `server.log`, `lease.test`, `pane_arm.json`, `terminal.claim.test`,
  `technical_failure.test.json`, and ledger
  `case-<two-decimal-index>-<literal-hook-id>-<injection-kind>.json` for hook
  cases 01–75, where shared-helper cases are 01–52, fake-process cases are
  53–75, and `injection-kind` is exactly `crash` or `exception`; and the twelve
  literal scenario ledgers `scenario-S01_monitor_death.json`,
  `scenario-S02_server_death.json`, `scenario-S03_pane_death.json`,
  `scenario-S04_broker_death.json`, `scenario-S05_worker_death.json`,
  `scenario-S06_duplicate_frame.json`, `scenario-S07_late_frame.json`,
  `scenario-S08_monitor_death_after_launcher_eof.json`,
  `scenario-S09_child_timeout.json`,
  `scenario-S10_term_resistant_descendant.json`,
  `scenario-S11_kill_escalation.json`, and
  `scenario-S12_final_absence_probe.json`.

The full `m7x_`, `m7a_`, `m7c_`, and `m7s_` families are closed. Test objects exist only
during the exact registered test, are current-UID/GID with socket modes
0700/0600 as typed below and scratch mode-0700, and are absent before the next
fault case and at supervisor exit. They never overlap config/provenance/run/
capability/key/state/GPU-lock namespaces.

Every phase enumerates all `gen7`, `m7t_`, `m7b_`, `m7p_`, `m7x_`, `m7a_`, `m7c_`, and `m7s_`
family entries no-follow
and rejects undeclared siblings, broken symlinks, non-regular parents, and
ignored extras. All new regular files are UID/GID-owned, nlink-1, no-symlink,
mode-0644 unless explicitly private mode-0600 or executable mode-0755. All new
private directories are mode-0700.

## Design: exact gen6 substitution and allowed deltas

The seven gen7 implementation entries start from byte-for-byte gen6 copies.
The comparator processes each source as bytes, rejects non-UTF-8, then performs
these literal replacements **simultaneously by longest-match at each original
input offset** (replacement output is never rescanned):

1. `post_m2_gen6` → `post_m2_gen7`;
2. `post-m6-gen6` → `post-m7-gen7`;
3. `post_m6_gen6` → `post_m7_gen7`;
4. `post-m6` → `post-m7`;
5. `post_m6` → `post_m7`;
6. `gen6` → `gen7`;
7. `m6t_` → `m7t_`;
8. `m6b_` → `m7b_`.

The pattern set is prefix-overlapping by design; longest-match plus no output
rescan is the only legal algorithm. The comparator records replacement counts
per pattern/path, rejects any remaining standalone `gen6`, `post-m6`,
`post_m6`, `m6t_`, or `m6b_` token except literal frozen-predecessor registry
rows, and independently requires every resulting registered gen7 path. A typed
AST/JSON/line comparator then permits only these semantic deltas:

1. new immutable failed-gen6 bindings/evidence and one additional setup
   publication/receipt;
2. the explicit passing-vs-failed predecessor test policy above;
3. the shared tmux control/start helper and the complete real-process fault
   matrix below; and
4. corresponding static-closure, candidate, review, RFC, and test bindings.

Any scientific, model, data, overlap, Stage-A, Stage-B, endpoint, authorization,
nonce, GPU-idle, or terminal-output delta blocks.

Alternative rejected: changing frozen gen5 files or weakening pytest would
fabricate success and violate failed-attempt preservation. Alternative rejected:
keeping a separate test-only tmux implementation would repeat the gen6 proof
gap. Alternative rejected: launching a real model/GPU smoke test before review
would violate the requested pre-experiment adversarial gate.

## Shared tmux helper contract

The gen7 runtime owns one source-only helper,
`foreground_tmux_start_v1(config, fault_control)`. The production launcher,
persistent production monitor, and in-pane production supervisor each call
these exact bytes with different typed roles; the registered fake-broker test
runs all three roles over real socketpairs. No adapter methods or callbacks
exist. All production file/socket/process/tmux/frame/terminal/cleanup side
effects are in the shared helper; callers may supply only canonical data and
held FDs. The outer test supervisor may only inject the registered signal,
observe/reopen evidence, and perform explicitly failing emergency containment.

`config` has exact schema `msae_v3_gen7_foreground_tmux_config_v1` and keys:
`schema_version`, `variant`, `role`, `tmp_parent_binding`, `tmux_socket_path`,
`broker_socket_path`, `pane_socket_path`, `scratch_root`, `session`, `monitor_record_path`,
`monitor_record_sha256`, `control_fd`, `broker_cleanup_fd`,
`broker_socket_binding`, `pane_listener_fd`, `monitor_log_path`,
`server_log_path`, `monitor_log_fd`, `server_log_fd`, `monitor_log_binding`,
`server_log_binding`, `broker_argv`, `lease_fd`, `gpu`, `lease_binding`,
`evidence_retention`,
`expected_uid`, `expected_gid`, `umask`,
`start_deadline_monotonic_ns`, `terminal_deadline_unix`, `cleanup_budget`,
`fault_event_fd`, and `fault_event_binding`.

Only two variants and three roles exist. `role=launcher` owns monitor-record
publication plus outbound frames 2/4 and inbound frames 1/3/5/7; `role=monitor`
owns inbound frames 2/4/6, outbound frames 1/3/5/7, foreground tmux/server/
client side effects, persistent lease supervision, and monitor teardown.
`role=pane_supervisor` runs inside the tmux pane, descriptor-validates its exact
broker/control endpoint and the durable pane-arm/handoff subject, supervises
broker/worker plus monitor/server liveness, and invokes the same terminal-claim
and non-short-circuiting cleanup primitive when it becomes the registered
complementary owner. It never constructs tmux argv or starts a server/session.
All three roles share the same frame/record/path/process validators, terminal
claim, and cleanup primitive. The long-lived pytest child is only a coordinator:
for each case it starts one dedicated source-only launcher-role process in a new
session/group; that process calls the actual helper, starts the actual monitor
role with the exact reviewed isolated monitor vector, and starts the actual
pane-supervisor role in the exact reviewed fake pane.
Their permitted
variant field differences are:

| field | `production` | `containment_test` |
|---|---|---|
| tmux path | exact `/tmp/m7t_<stage-a>.sock` | exact `/tmp/m7x_<test-token>.sock` |
| broker path | exact `/tmp/m7b_<stage-a>.sock` | exact `/tmp/m7a_<test-token>.sock` |
| pane-lease path | exact `/tmp/m7p_<stage-a>.sock` | exact `/tmp/m7c_<test-token>.sock` |
| scratch | exact signed run root | exact `/tmp/m7s_<test-token>` |
| session | `msae-independent-v3-gen7-calibration` | `msae-independent-v3-gen7-containment` |
| monitor record | exact run-root `tmux_monitor.json` | exact scratch `monitor.json` |
| logs | exact run-root `logs/monitor.log` and `logs/tmux_server.log` | exact scratch `monitor.log` and `server.log` |
| broker argv | exact signed isolated gen7 supervisor argv | exact reviewed isolated fake argv |
| GPU/lease | signed `{uuid,index}` plus exact shared UUID-lock binding | literal `{uuid:"GPU-00000000-0000-0000-0000-000000000000",index:-1}` plus scratch `lease.test` binding; no GPU query/lock namespace |
| evidence retention | literal `retain_run_logs` | literal `delete_test_logs_after_hash` |
| helper start deadline | inherited signed production deadline | case-start monotonic + exactly 8 seconds; outer watchdog is 24 seconds |
| cleanup budget | exact production budget below; every tmux client capped at 15 seconds | exact containment budget below; every tmux client capped at 1 second |
| fault event | both FD/binding JSON null | one inherited FD >=3 for an unnamed `AF_UNIX/SOCK_DGRAM` socketpair endpoint plus exact typed binding |

All other fields and all validation/control/start/cleanup code paths are
identical. `cleanup_budget` has schema `msae_v3_gen7_cleanup_budget_v1` and exact
keys `tmux_client_timeout_ns`, `term_wait_ns`, `kill_wait_ns`, `max_groups`,
`max_tmux_client_calls`, `nfs_settle_ns`, `evidence_finalize_ns`,
`scheduling_margin_ns`, and `total_ns`. Production values are respectively
15,000,000,000; 1,000,000,000; 1,000,000,000; 4; 4; 6,000,000,000;
10,000,000,000; 10,000,000,000; and 94,000,000,000. Containment values are
1,000,000,000; 250,000,000; 250,000,000; 4; 4; 1,000,000,000;
2,000,000,000; 3,000,000,000; and 12,000,000,000. The helper checks the exact
sum `(term_wait_ns+kill_wait_ns)*max_groups +
tmux_client_timeout_ns*max_tmux_client_calls + nfs_settle_ns +
evidence_finalize_ns + scheduling_margin_ns == total_ns`; exceeding any
component is a technical failure, not permission to overrun the outer watchdog.
Role applicability is exact:

| field | `launcher` | `monitor` | `pane_supervisor` |
|---|---|---|---|
| `control_fd` | launcher↔monitor endpoint, nonnegative FD >=3 | matching monitor endpoint, nonnegative FD >=3 | JSON null on entry; helper creates/connects the pane endpoint itself |
| `broker_cleanup_fd` / `broker_socket_binding` | JSON null on entry; helper creates listener then derives/retains both | inherited duplicate FD >=3 plus exact binding, cleanup-only; `accept` is forbidden | both JSON null |
| `pane_listener_fd` | JSON null on entry; helper creates/binds/listens and retains an authority duplicate | inherited same listener FD >=3; only this role accepts | JSON null |
| `monitor_log_path` / `server_log_path` | exact registered paths | same exact paths | same exact paths |
| `monitor_log_fd` / `server_log_fd` | JSON null on entry; helper exclusively creates/opens/binds both | inherited distinct FDs >=3 | both JSON null |
| `monitor_log_binding` / `server_log_binding` | JSON null on entry; helper derives after creation | exact non-null bindings matching FDs | both JSON null |
| `broker_argv` | exact to-be-started pane-supervisor argv | same exact argv | JSON null |
| `lease_fd` | held/locked FD >=3 | duplicate for same open lock object, FD >=3 | JSON null on entry; received once inside helper as typed SCM_RIGHTS FD >=3 |
| `gpu` / `lease_binding` | exact non-null pair | same exact pair | same exact pair |
| `monitor_record_path` | exact non-null path | same exact path | same exact path |
| `monitor_record_sha256` | JSON null on entry; helper derives after HELLO/publication | JSON null on entry; accepted only from validated frame 2 and independently reconstructed | JSON null on entry; accepted only in pane frame 1 and independently reconstructed |
| `fault_event_fd` / `fault_event_binding` | null/null in production; FD >=3 plus binding in test | null/null in production; same FD/binding in test | null/null in production; both null on entry, received in test pane frame 1 |

Every other config field is non-null and equal across the three roles except the
literal `role`; all held non-null FDs are mutually distinct where they coexist.
Null entry fields can become live only at the exact helper-owned transition in
this table and are then carried in a private typed state object; callers may not
prepopulate them. The launcher-role helper creates the mode-0600 monitor/server
logs plus distinct mode-0700 broker and pane listeners under held parents,
fsyncs and identity-binds them, creates the launcher↔monitor socketpair, and
starts the source-only monitor with only the exact monitor-side FDs. The
launcher role alone accepts/revalidates broker/runner gate peers on
`broker_socket_path`, preserving the inherited pre-model identity/readiness/gate
exchange without extra monitor frames. The monitor-role helper accepts exactly
one pane peer only from the separate inherited `pane_socket_path` listener after
validating its tmux/pane lineage.
The pane-role helper itself creates and connects its `SOCK_SEQPACKET` client to
the exact `pane_socket_path`; no pane control FD is inherited through tmux.
The monitor holds the exact broker-listener duplicate solely as descriptor
authority for fstat, shutdown/close, path-identity recheck, and unlink after
launcher death; static and behavioral process/socket tripwires reject any
monitor `accept` on it. Thus hooks 1–7 leave a surviving, descriptor-authorized
monitor cleanup path without creating a second broker-gate consumer.
`gpu` is exactly `{uuid,index}`. `lease_binding` is exactly
`{path,device,inode,uid,gid,mode,nlink,payload_sha256,gpu_uuid}` and must match
the descriptor before every role transition and before release. In production,
the launcher acquires/rechecks the registered GPU first, duplicates the held FD
into monitor inheritance, and keeps its own copy until frame 7. The monitor-role
helper passes one further duplicate to the validated pane-role helper over its
held `SOCK_SEQPACKET` endpoint using the exact pane-lease protocol below; tmux
inheritance is never trusted to preserve an arbitrary FD. After frame 7 the
monitor and pane copies ensure that death of either one
cannot release the lease while the other still has descendants to extinguish.
The final surviving authority closes the last copy only after exact terminal
claim and process/session/socket extinction. In the containment variant all
three FDs refer only to the mode-0600 scratch `lease.test` inode under a real
cross-process flock; any GPU query or protocol-independent GPU-lock access trips
the test.
In containment only, the outer supervisor creates one unnamed
`AF_UNIX/SOCK_DGRAM|SOCK_CLOEXEC` socketpair per case and retains the read
endpoint with `SO_PASSCRED=1`. Its exact binding schema is `msae_v3_gen7_fault_event_binding_v1`
with keys `schema_version`, `family`, `type`, `path`, `supervisor_endpoint`,
`writer_endpoint`, `supervisor_pid`, `pytest_pid`, and `case_id`.
`supervisor_endpoint` and `writer_endpoint` are each the exact fstat object
`{device,inode,uid,gid,mode,nlink}` for their distinct socketpair endpoint;
literal values are `AF_UNIX`, `SOCK_DGRAM`, JSON null path, current identities,
the canonical requested case ID, and the two independently validated live PIDs.
The outer retains/revalidates only `supervisor_endpoint`; frame 2 transfers a
duplicate of `writer_endpoint`, and every later role validates that same open
socket object before using or duplicating it.
Frame 3 separately binds the later-created launcher PID. Pytest passes only a duplicate of the
write endpoint to the per-case launcher; launcher passes it to monitor; monitor
passes it as the second and final SCM_RIGHTS FD in pane frame 1. Server and fake
children may retain it only through their registered pre-exec hook, then close
it before any non-test exec. Every event is one canonical JSON datagram with
schema `msae_v3_gen7_fault_event_v1` and exact common keys `schema_version`,
`event_type`, `test_token`, `case_id`, `reporter_role`, `reporter_kind`, `pid`,
`start_ticks`, `ppid`, `pgid`, and `payload`. The only event variants are:

- `HOOK_REACHED`, whose payload keys are exactly `case_index`, `hook_id`, and
  `injection_kind`;
- `SCENARIO_BOUNDARY_REACHED`, whose payload keys are exactly `scenario_id`,
  `boundary_id`, and `reporter_process`; `reporter_process` is only the reporter's
  own exact process row and never a global prefix/target supplied by that role;
- `SCENARIO_ACTION_OBSERVED`, used only by S06/S07/S09 and whose payload keys
  are exactly `scenario_id`, `boundary_event_sha256`, `action_enum`,
  `observer_role`, `observer_process`, and `observation`; and
- `OWNER_LEDGER_READY`, whose payload keys are exactly `ledger_path`,
  `ledger_sha256`, `pre_exit_absence_sha256`, and
  `expected_outer_final_descriptor_sha256`.

Every datagram is maximum 4096 bytes, carries no ancillary data except the one
required credentials record, is untruncated, and has a reported PID/start-tick/
ancestry matching a continuously captured descendant. `recvmsg` must yield
exactly one kernel `SCM_CREDENTIALS` tuple `{pid,uid,gid}` matching the payload
PID, current UID/GID, and captured start-tick; missing, duplicate, or wrong
credentials block before any signal. Production rejects
any non-null fault FD/binding. The static FD closure and case ledger bind every
duplicate/open/close; no pipe or pathname event channel exists.
No field is silently ignored. Production-only path/session/argv rules are
mutation-tested directly with `variant=production`; the containment variant may
not weaken shared type/mode/UID/GID/nlink/deadline/frame/process constraints.

The production monitor record and successful seven-frame wire protocol inherit
the complete exact schemas and canonical digest preimages from the frozen gen6
plan (SHA-256 bound above), section `Monitor record and control protocol`, after
the simultaneous gen6→gen7 substitutions, with one exact control-plane schema
delta for the helper-owned pane listener. The record schema is
`msae_v3_gen7_tmux_monitor_v2`; its gen6-substituted top-level keys are unchanged,
but `inherited_fds` is exactly
`{control,lease,monitor_log,server_log,pane_listener,broker_cleanup}` with six mutually
distinct integers >=3, and `control` additionally has exact nested key
`pane_listener_binding` plus `broker_socket_binding`, each exactly
`{path,device,inode,uid,gid,mode,nlink}` for the respective mode-0700 socket.
The record-subject `inherited_fd_bindings` has the same fifth and sixth exact entries. The
launcher helper creates/binds/listens on the distinct mode-0700
`pane_socket_path` before spawning the monitor, retains its
authority duplicate through frame 7, and passes the only accept-capable duplicate
to the monitor; the pane receives no inherited socket FD.

The containment record alone uses schema
`msae_v3_gen7_tmux_monitor_containment_v1`: it has the identical top-level and
nested production projection plus exact top-level keys `fault_event_binding`
and `fault_control`,
and `inherited_fds`/record-subject bindings add exactly `fault_event` as the
seventh FD. Production rejects that schema/key/FD. This is instrumentation only;
the test also mutation-checks the production six-FD schema and exact log/
listener bindings.

The seven launcher↔monitor frames retain schema
`msae_v3_gen7_monitor_frame_v1`; frame directions, common keys, sequence,
prior-frame chaining, exact payload keys, socketpair framing/credential rules,
and derived subject preimages are unchanged except that every inherited-FD/
control subject includes both the fifth typed pane-listener binding and the
sixth typed broker-cleanup binding above. In particular, the handoff
`control_channel_transcript_sha256` is still canonical frames 1–5 only; frame 6
contains the handoff digest and frame 7 contains the takeover subject, so neither
may enter that preimage. The shared helper reconstructs every inherited digest
from its typed subject rather than accepting a caller-supplied hash. A schema,
key, direction, preimage, or frame-order delta is outside the allowed change set
and blocks the typed comparator.

The monitor↔pane lease channel is separate from the seven launcher↔monitor
frames and is exact. It is `AF_UNIX/SOCK_SEQPACKET`, stable `SO_PEERCRED`, one
canonical JSON datagram per frame, maximum 65,536 bytes, and exactly one
SCM_RIGHTS FD only on frame 1. Common keys are exactly `schema_version`
(`msae_v3_gen7_pane_lease_frame_v1`), `protocol_id`, `generation`,
`frame_type`, `sequence`, `prior_frame_sha256`, and `payload`. Frame 1 is
monitor→pane `PANE_LEASE_HANDOFF`, sequence 1, null prior, payload keys exactly
`monitor_record_sha256`, `lease_binding`, `pane_process`, and
`terminal_deadline_unix`; production carries exactly one FD and it must
fstat/flock-identify as that binding. Containment adds exact payload key
`fault_control`, whose canonical value must match the containment monitor
record, and carries exactly two FDs in
fixed order: the same lease FD then the fault-event FD matching the containment
record/config binding. No other variant or FD count is legal.
Frame 2 is pane→monitor `PANE_LEASE_ACK`, sequence 2, prior equal to frame-1
SHA-256, no ancillary FDs, payload keys exactly `lease_handoff_sha256`,
`pane_process`, `pane_arm_entry`, and `pane_arm_subject_sha256`.
`lease_handoff_sha256` is the canonical frame-1 digest. `pane_arm_entry` is
exactly `{path,device,inode,uid,gid,mode,nlink,size,sha256}` for canonical
mode-0600 `pane_supervisor_armed.json` in production or `pane_arm.json` in the
test scratch. `pane_arm_subject_sha256` hashes exact keys `schema_version`
(`msae_v3_gen7_pane_arm_subject_v1`), `monitor_record_sha256`,
`lease_handoff_sha256`, `lease_binding`, `pane_process`, `broker_process`,
`worker_process`, and `terminal_deadline_unix`; unavailable broker/worker values
are JSON null only before their exact validated frames and are re-bound later.
Frame 7 `TAKEOVER_ACK` cannot be sent until frame 2 and the descriptor-reopened
pane-arm subject validate. Wrong credential, FD count/type/identity, frame,
digest, timeout, EOF, or extra datagram enters the shared cleanup path.

The pane supervisor deliberately does **not** arm parent-death signal to the
tmux server and does not die on pty HUP; it owns a dedicated validated process
group, retains its lease duplicate, and watches monitor/server liveness. Its
broker and worker children do arm and verify parent-death to the pane supervisor.
The persistent monitor likewise does not arm parent-death to the launcher: a
launcher death before frame 7 is a failure it must terminalize, while the exact
launcher EOF after frame 7 is the normal return transition. Conversely, the
monitor watches the pane supervisor. Monitor death therefore
leaves the pane authority alive to extinguish broker/worker/session/socket and
claim failure; pane death leaves the monitor authority alive to extinguish the
server/session/descendants and claim failure. Both owners race the same
create-once terminal claim, and neither may report success until the other's
durable bindings and lease ownership are proven. A real-process matrix case
kills each authority after frame 7 and independently proves the complementary
path, including last-lease-FD closure only after extinction.

`fault_control` is exact schema `msae_v3_gen7_fault_control_v2` with keys
`schema_version`, `enabled`, `mode`, `selected_hook_id`,
`selected_scenario_id`, `action`, `test_token`, `case_index`, `scenario_trigger`,
`cleanup_trigger`, `fault_event_binding_sha256`, `case_start_monotonic_ns`,
`helper_start_deadline_monotonic_ns`, and `outer_case_deadline_monotonic_ns`.
Production requires the exact values
`false,none,null,null,none,null,null,none,none,null,null,null,null` after
`schema_version`. A hook
test requires `true,hook,<one-literal-hook-01..75>,null,<injection-action>,
<test-token>,<1..75>,none,<cleanup-trigger>,<binding-sha256>,<start>,<start+8s>,
<start+24s>`;
`action` is exactly
`report_then_sigstop_crash` or `report_then_raise_after_resume`, the index is the
hook ordinal, and `cleanup_trigger` is `none` for hooks 1–41 and 53–75 and exactly
`post_takeover_technical_failure_deadline_1s` for hooks 42–52. A scenario test
requires `true,scenario,null,<one-literal-S01..S12>,run_registered_scenario,
<test-token>,null,<table-trigger>,<cleanup-trigger>,<binding-sha256>,<start>,
<start+8s>,<start+24s>`. `scenario_trigger` is the exact literal trigger in its
S01–S12 row. Scenario `cleanup_trigger` is `none` for S01–S08/S11,
`launcher_receive_timeout_at_helper_deadline` for S09, `outer_sigusr1_pane` for S10, and
`outer_case_deadline_minus_14s` for S12. No other combination or value is legal.

The launcher constructs this object only from the exact registered test CLI.
In containment the monitor-record schema has exact additional top-level key
`fault_control`, and every record subject and derived launcher↔monitor frame
subject binds its canonical digest. The monitor independently reconstructs it
from the descriptor-reopened record. Containment pane frame 1 has exact
additional payload key `fault_control`; the pane requires byte equality with
the record-bound object before accepting the event FD. The exact fake-process
control object below carries the same scenario ID/trigger into a fake broker or
worker. Production record/frame/fake schemas reject these containment-only
fields. Thus launcher, monitor, pane, broker, and worker never inspect an
unregistered global or raw `argv` to select a scenario.

The canonical fault-control object never contains a process-local descriptor
number. Each role instead creates an ephemeral local projection with schema
`msae_v3_gen7_local_fault_endpoint_v1` and exact keys `schema_version`, `role`,
`local_fd`, and `fault_event_binding_sha256`; `local_fd` is that process's own
integer >=3 and its fstat identity must match the binding before every use.
Launcher and monitor local FDs equal their role-local config; pane entry has
config FD null and creates its projection only from the typed frame-1 SCM_RIGHTS
FD; fake processes create the same projection from their exact inherited FD.
No local FD integer enters a cross-process digest or byte-equality comparison.
For a hook, the helper writes exactly one canonical
`HOOK_REACHED` event through the held event FD and SIGSTOPs its own current
process. The hook table statically assigns one exact reporter role/kind; every
other role traversing the same shared primitive treats that selected hook as
inactive. The reporter sets an in-memory one-shot bit before sending the event,
so exception resumption cannot inject the same hook again; a crash loses the bit
only with the reporter, while the complementary role is ineligible to inject.
For hooks 42–52, after valid frame 7 and expected launcher EOF the
monitor arms the exact one-second `cleanup_trigger`; its expiry commits the
registered technical failure and enters the ordinary production cleanup path,
where the selected cleanup hook is then reached. This trigger must occur and
production cleanup must finish before the outer 24-second watchdog; an outer
watchdog action is emergency containment and fails the case.
`reporter_role` is the helper role; `reporter_kind` is the same literal except
hooks 10–11, where role is `monitor` and kind is `server_child`. Hooks cannot replace, skip, retry,
mutate, or mock an operation. In `crash` mode the surviving external test
supervisor validates PID/start-tick/ancestry/PGID against already-held parent
authority and SIGKILLs only that stopped reporter; the complementary production
authority in the table below must complete terminalization and cleanup before
the test supervisor performs any emergency action. In `exception` mode the test
supervisor sends SIGCONT only; the same helper call then raises the literal
private `_InjectedFault` at the selected point, and the reporter's real
`except/finally` must terminalize and clean up. Before-fork hooks authorize only
the already-bound launcher or monitor; after-fork/pre-exec hooks are reported
from the child over the inherited event FD before it can exec; after-exec
authority comes only from continuously captured `/proc` lineage plus exact tmux
identity output.

The literal ordered hook registry and action/authority/state table is exact.
`pre` means the named operation has not occurred and the durable prefix ends
before it; `post` means it has occurred, all durability required by the name
has completed, and the prefix includes it. Child/parent barriers force this
table order even across the server fork and pane-lease transfer. Every hook is
run twice: once with crash action `SIGKILL` and once with exception action
`SIGCONT` followed synchronously by `_InjectedFault`.

| # | literal hook id | reporter_kind | state | crash terminal owner | exception terminal owner |
|---:|---|---|---|---|---|
| 01 | `before_monitor_record_write` | `launcher` | `pre` | `monitor` | `launcher` |
| 02 | `after_monitor_record_file_fsync` | `launcher` | `post` | `monitor` | `launcher` |
| 03 | `after_monitor_record_parent_fsync` | `launcher` | `post` | `monitor` | `launcher` |
| 04 | `after_monitor_record_committed_send` | `launcher` | `post` | `monitor` | `launcher` |
| 05 | `before_monitor_record_ack_receive` | `launcher` | `pre` | `monitor` | `launcher` |
| 06 | `after_monitor_record_ack_receive` | `launcher` | `post` | `monitor` | `launcher` |
| 07 | `before_start_server_send` | `launcher` | `pre` | `monitor` | `launcher` |
| 08 | `after_start_server_receive` | `monitor` | `post` | `launcher` | `monitor` |
| 09 | `before_server_fork` | `monitor` | `pre` | `launcher` | `monitor` |
| 10 | `server_child_before_pdeath_arm` | `server_child` | `pre` | `monitor` | `monitor` |
| 11 | `server_child_after_pdeath_arm_before_exec` | `server_child` | `post` | `monitor` | `monitor` |
| 12 | `parent_after_server_fork` | `monitor` | `post` | `launcher` | `monitor` |
| 13 | `after_socket_publication` | `monitor` | `post` | `launcher` | `monitor` |
| 14 | `before_socket_mode_promotion` | `monitor` | `pre` | `launcher` | `monitor` |
| 15 | `after_socket_mode_promotion_before_tmp_fsync` | `monitor` | `post` | `launcher` | `monitor` |
| 16 | `after_tmp_fsync` | `monitor` | `post` | `launcher` | `monitor` |
| 17 | `before_new_session_client` | `monitor` | `pre` | `launcher` | `monitor` |
| 18 | `after_new_session_client` | `monitor` | `post` | `launcher` | `monitor` |
| 19 | `before_set_exit_empty_client` | `monitor` | `pre` | `launcher` | `monitor` |
| 20 | `after_set_exit_empty_client` | `monitor` | `post` | `launcher` | `monitor` |
| 21 | `before_show_exit_empty_client` | `monitor` | `pre` | `launcher` | `monitor` |
| 22 | `after_show_exit_empty_client` | `monitor` | `post` | `launcher` | `monitor` |
| 23 | `before_display_identity_client` | `monitor` | `pre` | `launcher` | `monitor` |
| 24 | `after_display_identity_client_before_parse` | `monitor` | `post` | `launcher` | `monitor` |
| 25 | `after_display_identity_parse` | `monitor` | `post` | `launcher` | `monitor` |
| 26 | `before_pane_lease_handoff_send` | `monitor` | `pre` | `launcher` | `monitor` |
| 27 | `after_pane_lease_handoff_send` | `monitor` | `post` | `launcher` | `monitor` |
| 28 | `after_pane_lease_handoff_receive` | `pane_supervisor` | `post` | `monitor` | `pane_supervisor` |
| 29 | `after_pane_arm_file_fsync` | `pane_supervisor` | `post` | `monitor` | `pane_supervisor` |
| 30 | `after_pane_arm_parent_fsync` | `pane_supervisor` | `post` | `monitor` | `pane_supervisor` |
| 31 | `before_pane_lease_ack_send` | `pane_supervisor` | `pre` | `monitor` | `pane_supervisor` |
| 32 | `after_pane_lease_ack_send` | `pane_supervisor` | `post` | `monitor` | `pane_supervisor` |
| 33 | `after_pane_lease_ack_receive` | `monitor` | `post` | `launcher` | `monitor` |
| 34 | `before_server_ready_send` | `monitor` | `pre` | `launcher` | `monitor` |
| 35 | `after_server_ready_send` | `monitor` | `post` | `launcher` | `monitor` |
| 36 | `before_handoff_committed_receive` | `monitor` | `pre` | `launcher` | `monitor` |
| 37 | `after_handoff_committed_receive` | `monitor` | `post` | `launcher` | `monitor` |
| 38 | `before_takeover_ack_send` | `monitor` | `pre` | `launcher` | `monitor` |
| 39 | `after_takeover_ack_send` | `monitor` | `post` | `pane_supervisor` | `monitor` |
| 40 | `before_peer_eof_wait` | `monitor` | `pre` | `pane_supervisor` | `monitor` |
| 41 | `after_peer_eof` | `monitor` | `post` | `pane_supervisor` | `monitor` |
| 42 | `cleanup_before_kill_session` | `monitor` | `pre` | `pane_supervisor` | `monitor` |
| 43 | `cleanup_after_kill_session` | `monitor` | `post` | `pane_supervisor` | `monitor` |
| 44 | `cleanup_before_descendant_term` | `monitor` | `pre` | `pane_supervisor` | `monitor` |
| 45 | `cleanup_before_descendant_kill` | `monitor` | `pre` | `pane_supervisor` | `monitor` |
| 46 | `cleanup_before_server_term` | `monitor` | `pre` | `pane_supervisor` | `monitor` |
| 47 | `cleanup_before_server_kill` | `monitor` | `pre` | `pane_supervisor` | `monitor` |
| 48 | `cleanup_before_socket_unlink` | `monitor` | `pre` | `pane_supervisor` | `monitor` |
| 49 | `cleanup_before_final_has_session` | `monitor` | `pre` | `pane_supervisor` | `monitor` |
| 50 | `cleanup_after_final_has_session` | `monitor` | `post` | `pane_supervisor` | `monitor` |
| 51 | `cleanup_before_terminal_claim` | `monitor` | `pre` | `pane_supervisor` | `monitor` |
| 52 | `cleanup_after_terminal_claim` | `monitor` | `post` | `monitor` | `monitor` |
For every row, the canonical case ledger is mode-0600, current-UID/GID,
regular nlink-1 and has exact keys `schema_version`, `test_token`,
`case_index`, `hook_id`, `injection_kind`, `reporter_role`, `reporter_pid`,
`reporter_kind`, `reporter_start_ticks`, `reporter_pgid`, `boundary_state`,
`expected_terminal_owner`, `expected_cleanup_owner`, `evidence_publisher`,
`production_cleanup_complete`,
`emergency_cleanup_used`, `terminal_claim_sha256`,
`evidence_projection_sha256`, `pre_exit_absence_sha256`,
`expected_outer_final_descriptor_sha256`, and
`outcome`. Its schema is `msae_v3_gen7_tmux_fault_case_v1`;
`boundary_state` and terminal owner equal the table; `outcome` is exactly
`contained_expected_failure`; passing requires `production_cleanup_complete`
true and `emergency_cleanup_used` false. For every case except crash row 52,
`expected_cleanup_owner` and `evidence_publisher` equal the selected table owner.
Crash row 52 is the sole post-claim death: its already durable create-once claim
must remain owned by `monitor`, while `expected_cleanup_owner` and
`evidence_publisher` are exactly `pane_supervisor`; replacement or a second claim
blocks. After completing terminalization,
cleanup, and operational-absence reconstruction, the exact evidence publisher
publishes/fsyncs this ledger under the exact filename, sends exactly one
`OWNER_LEDGER_READY` event matching its descriptor-reopened bytes, and exits; a
killed reporter never fabricates its own final row. The ledger's pre-exit
subject requires all resources except that one live evidence publisher/group
to be extinct. Pytest waits only for and reaps its direct per-case launcher
child, descriptor-safely validates the exact ledger, and sends control frame 5
`CASE_RESULT`; it never calls `waitpid` on a monitor/pane evidence publisher.
The outer subreaper validates the matching owner event and frame-5 launcher
wait status, reaps every adopted per-case descendant (including any non-launcher
publisher), and independently proves the publisher/group extinct. When the
launcher itself published the ledger, pytest's exact frame-5 wait status is the
only reap authority and the outer instead proves that bound PID/start-tick and
group extinct. It then descriptor-safely reopens/hashes the ledger and
performs the only permitted evidence teardown: unlink that exact validated
ledger and rmdir/fsync the now-empty scratch root. It then constructs the
outer-final subject/digest and sends control frame 6 `CASE_RELEASE`; that digest
is stored in the immutable overall test transcript, not retroactively in the
owner ledger. Evidence teardown may not signal a process,
kill a session, unlink a socket/terminal artifact, or remove any extra child;
needing any such emergency containment forces the case and entire command to
fail.

`evidence_projection_sha256` hashes canonical schema
`msae_v3_gen7_test_retired_evidence_v1` with exact keys `schema_version`,
`monitor_log`, `server_log`, `process_record`, `pane_arm`, `terminal_claim`, and
`technical_failure`; each value is the exact pre-deletion regular-entry object
`{path,type,mode,uid,gid,nlink,size,sha256}` or JSON null only when the selected
pre-boundary state proves it was never created. With
`evidence_retention=delete_test_logs_after_hash`, the production cleanup
primitive validates/hashes these test-only objects, descriptor-safely unlinks
them, fsyncs parents, and leaves only the ledger. With
`retain_run_logs`, it never unlinks production logs or monotone run evidence and
instead binds them into the inherited terminal projection. Both branches use
the same primitive and an exact two-value policy switch; mutation tests require
production retention and test retirement independently.

`pre_exit_absence_sha256` is the SHA-256 of canonical JSON (UTF-8, sorted keys,
separators `(',', ':')`, one LF) with schema
`msae_v3_gen7_test_pre_exit_absence_v1` and exact keys `schema_version`,
`test_token`, `case_or_scenario_id`, `captured_processes`, `process_groups`,
`session`, `socket_paths`, `short_family_entries`, `lease`, `staging_entries`,
`terminal_evidence`, `scratch_projection`, and `tripwires`.
`captured_processes` is the PID-sorted complete per-case capture, each exact row
`{role,pid,start_ticks,ppid,pgid,uid,gid,live}`; only the exact evidence
publisher has `live:true`, every other row is false. `process_groups` is the
PGID-sorted complete set; only the publisher group has
`members:[<publisher-pid>]`, every other exact row is `{pgid,members:[]}`.
`session` is
`{name,has_session_returncode}` with the registered name and nonzero integer.
`socket_paths` maps the exact m7x/m7a/m7c paths to `{lexists:false}`.
`short_family_entries` maps literal prefixes `m7t_`, `m7b_`, `m7p_`, `m7x_`,
`m7a_`, and `m7c_` to empty sorted arrays from one held `/tmp` scan and maps
`m7s_` to the singleton exact scratch basename.
`lease` is exactly `{path,open_holder_count:0,contender_acquired:true,lexists:false}`
for test `lease.test`. `staging_entries` is an exact sorted map with literal
keys `process_record_partial`, `monitor_record`, `pane_arm`, `monitor_log`,
`server_log`, `process_record`, `lease`, `terminal_claim`, and
`technical_failure`; each value is exactly `{path,lexists:false}` with its
registered scratch path after hashes enter `evidence_projection_sha256`.
`terminal_evidence` is exactly
`{claim_sha256,technical_failure_sha256}` copied from that projection.
`scratch_projection` is exactly `{path,mode,uid,gid,nlink,children:[<ledger
basename>]}` describing the state after ledger publication. `tripwires` is
exactly `{gpu_queries:0,model_imports:0,model_calls:0,forbidden_env_mutations:0,
forbidden_processes:0,sealed_payload_content_reads:0}`. The preimage contains
only the ledger basename, never its size/inode/content/digest, so the ledger may
contain this digest without a cycle. Independent mutations that omit or mark
live every row/key/family/staging/tripwire component must fail reconstruction.

`expected_outer_final_descriptor_sha256` hashes canonical schema
`msae_v3_gen7_test_outer_final_derivation_v1` with exact keys
`schema_version`, `test_token`, `case_or_scenario_id`, `evidence_publisher`,
`ledger_path`, `pre_exit_absence_sha256`, and `required_transitions`; the final
array is exactly `publisher_exit`, `publisher_group_empty`,
`ledger_descriptor_reopen`, `ledger_unlink`, `scratch_rmdir`,
`all_seven_families_empty`. It predicts rules only and contains no final observed
digest.

After those transitions the outer supervisor constructs canonical schema
`msae_v3_gen7_test_outer_final_absence_v1`, exact keys `schema_version`,
`test_token`, `case_or_scenario_id`, `ledger_sha256`,
`pre_exit_absence_sha256`, `captured_processes`, `process_groups`, `session`,
`socket_paths`, `short_family_entries`, `lease`, `staging_entries`,
`scratch`, and `tripwires`. It repeats the exact projections above with every
captured process `live:false`, every group empty, all seven family arrays empty,
and `scratch={path,lexists:false}`; all other values must equal the pre-exit
subject. Its digest is `outer_final_extinction_sha256` in control frame 6 and
the final test transcript. Mutation tests make every omitted/live component,
publisher survival, group survival, substituted ledger, or undeleted scratch
fail.

Frame 7 cannot be sent until the durable pane-arm subject is validated. The
terminal-claim schema permits exactly the expected terminal owner for that case; any
other owner, multiple claim, missing terminal, wrong state, or wrong action
blocks.

The helper also has typed non-hook scenarios for duplicate/late frame, monitor death after expected launcher EOF,
monitor/server/pane/broker/worker death, global child timeout, and TERM-resistant
descendant. A static AST test requires every registered operation and only these
hook IDs in the shared helper; a mutation test replaces each side effect and
must make the real-process matrix fail.

No test copy of tmux command construction, socket mode promotion, client
timeout, identity parsing, session setup, frame handling, terminal claim, or
cleanup is allowed.

The helper:

1. descriptor-validates held `/tmp`, closed umask 0077, exact 78-byte socket
   names, absent closed families, server log FD, monitor identity, and deadline;
2. writes/fsyncs/publishes or revalidates the exact durable monitor-record
   subject and processes the ordered
   `MONITOR_HELLO`, `MONITOR_RECORD_COMMITTED`, `MONITOR_RECORD_ACK`, and
   `START_SERVER` frames before forking tmux;
3. starts exact foreground server argv
   `[/usr/bin/tmux,-D,-f,/dev/null,-S,<socket>]` in a dedicated captured group,
   with parent-death/subreaper lineage;
4. continuously captures every descendant PID/start-tick/PPID/PGID/UID/GID;
5. waits boundedly for the exact socket, descriptor-safely promotes the owned
   installed-tmux mode-0600 socket to required mode-0700, fsyncs `/tmp`, and
   rebinds device/inode/uid/gid/mode/nlink;
6. uses the exact bounded clients:
   - `new-session -d -s <typed-session> ...`;
   - `set-option -s exit-empty on`;
   - `show-options -s -v exit-empty`, requiring `on\n`;
   - `display-message -p -t ... '#{pid} #{pane_pid}'`, requiring two decimal
     PIDs and exact foreground-server/pane lineage;
7. completes the exact pane-lease FD transfer, durable pane arm, and ACK before
   it may emit/revalidate `SERVER_READY`;
8. emits/revalidates exact `SERVER_READY`, `HANDOFF_COMMITTED`, and
   `TAKEOVER_ACK` frames and their canonical digest preimages;
9. returns a typed live authority only after all gates; and
10. after valid frame 7, treats launcher control EOF as the one expected
   nonterminal transition into persistent monitor/pane supervision; and
11. on every exception, signal, unexpected EOF before frame 7,
   monitor/server/pane/broker/worker death,
   registered role-specific failure deadline, or terminal outcome, performs non-short-circuiting bounded
   TERM/wait/KILL/wait cleanup of every validated group, bounded tmux session and
   server probes, descriptor-safe exact socket cleanup, lease release only after
   extinction, exact terminal claim, and final PID/PGID/session/socket/family
   absence verification.

The only non-failure deadline is S09's monitor-side helper-start boundary: the
scenario-aware monitor must keep LM5 unsent at and after that instant and wait
for launcher cleanup/EOF. The same numeric instant is a registered receive-
timeout failure only in the launcher role, which alone claims/cleans. Any monitor
terminal claim for S09, any early/late launcher deadline, or any other role-
specific reinterpretation blocks.

The helper never signals an unvalidated frame-supplied PID/PGID and never sends
a tmux command through an absent, substituted, or unbound socket. Cleanup errors
accumulate while all independent cleanup actions continue.
The monitor-role `try/except/finally` begins before the `START_SERVER` receive
and encloses server `Popen` itself. Thus Popen failure, child-setup failure, and
every later exception first race/commit the exact technical-failure terminal,
then execute unconditional control/descendant/server/socket cleanup. There is no
post-START pre-finally gap.

## Authorized real-process tmux test

Exact command:

```text
/usr/bin/env -i PATH=/usr/bin:/bin HOME=/thayerfs/home/f004ndc LANG=C.UTF-8 LC_ALL=C.UTF-8 /jumbo/lisp/f004ndc/experiments/wip/MSAE/.venv-atlas/bin/python -S -B -I scripts/run_msae_independent_measurement_v3_post_m2_gen7_tmux_test.py
```

The supervisor has one exact pytest child, one global 4200-second deadline,
one 24-second deadline per fault case, a self-pipe selector, and sole authority
for the table's registered fault-injection signals, adopted-child reaping,
independent observation, and final validated ledger/scratch teardown. The shared
helper remains the sole owner of production TERM/KILL/session/socket cleanup and
operational-evidence retirement; any outer use of those actions is emergency
containment and fails the command. No per-case deadline extends the global
deadline. Before creating any case object or spawning pytest, the supervisor
calls `prctl(PR_SET_CHILD_SUBREAPER,1)` and requires
`prctl(PR_GET_CHILD_SUBREAPER)==1`; failure blocks the test. The one pytest
process is its direct child. Each per-case launcher is a direct pytest child,
but after that launcher or an intermediate parent exits, every orphaned
monitor/server/pane/broker/worker/evidence-publisher descendant reparents to the
outer subreaper. The outer continuously captures and alone `waitpid`s those
adopted exact PID/start-tick identities; pytest reaps only its direct launcher
and eventually itself is reaped by the outer. Before spawning pytest the
supervisor creates one unnamed
`AF_UNIX/SOCK_SEQPACKET|SOCK_CLOEXEC` control socketpair, passes exactly the
pytest endpoint using `pass_fds`, and adds only
`MSAE_GEN7_TEST_CONTROL_FD=<decimal>` to the otherwise exact closed pytest child
environment. Pytest descriptor-validates that endpoint and closes every
unregistered FD. The control schema is `msae_v3_gen7_test_control_frame_v1`
with exact keys `schema_version`, `test_token`, `case_id`, `sequence`,
`prior_frame_sha256`, `frame_type`, and `payload`; sequence resets to 1 for each
case, prior is null only at 1, and every datagram is canonical, <=65,536 bytes,
untruncated, credential-stable, with no extra data. The exact exchange is:

| Seq | Direction/type | Exact payload keys / ancillary rule |
|---:|---|---|
| 1 | pytest→supervisor `CASE_REQUEST` | `case_index`, `hook_id`, `injection_kind`, `scenario_id`; exactly one of hook tuple or scenario is non-null, no FD |
| 2 | supervisor→pytest `CASE_EVENT_CHANNEL` | `fault_event_binding`, `case_start_monotonic_ns`, `helper_start_deadline_monotonic_ns`, `outer_case_deadline_monotonic_ns`; exactly one SCM_RIGHTS write endpoint matching the binding |
| 3 | pytest→supervisor `CASE_LAUNCHER_IDENTITY` | `pid`, `start_ticks`, `ppid`, `pgid`, `argv_sha256`, `environment_sha256`, no FD |
| 4 | supervisor→pytest `CASE_LAUNCHER_AUTHORIZED` | `launcher_identity_sha256`, no FD |
| 5 | pytest→supervisor `CASE_RESULT` | `launcher_returncode`, `ledger_path`, `ledger_sha256`, `outcome`, no FD |
| 6 | supervisor→pytest `CASE_RELEASE` | `ledger_sha256`, `outer_final_extinction_sha256`, no FD |

The supervisor creates the per-case datagram pair only after frame 1, samples
`case_start_monotonic_ns` once, derives helper deadline = start + exactly
8,000,000,000 and outer deadline = start + exactly 24,000,000,000, and sends
those values plus its write endpoint only in frame 2. Pytest passes that FD to the one registered
per-case launcher together with one private start-barrier read FD, then closes
its local event duplicate immediately after spawn. The launcher reports identity
but blocks on that barrier before helper entry. Pytest sends frame 3, requires
frame 4 with the exact identity digest, writes exactly one byte `B` to the
barrier, closes it, and the launcher then closes its read end before entering
the helper. Frame 5 arrives only after pytest has reaped its direct launcher and
descriptor-safely validated the durable owner ledger; adopted descendants may
still include only the exact exiting/zombie evidence publisher at that point.
Frame 6 arrives only after the outer has reaped every adopted per-case
descendant and completed independent extinction/evidence teardown.
Duplicate/late/wrong-case frames, credentials,
FDs, or EOF block and enter emergency containment (which fails the command).
This persistent channel is unnamed and distinct from every m7* protocol socket.

The child imports the reviewed
gen7 runtime source-only but never acts as the launcher reporter. For each hook
case it starts exactly this finite-vector template with a closed inherited-FD
set and `start_new_session=true`:

```text
/jumbo/lisp/f004ndc/experiments/wip/MSAE/.venv-atlas/bin/python -S -B -I scripts/msae_independent_measurement_v3_post_m2_gen7.py internal-tmux-test-role --role launcher --test-token <64-lowerhex> --case-index <01..75> --hook-id <registered-literal> --injection-kind <crash|exception> --event-fd <decimal-fd> --start-barrier-fd <decimal-fd> --case-start-monotonic-ns <decimal-ns> --helper-start-deadline-monotonic-ns <decimal-ns> --outer-case-deadline-monotonic-ns <decimal-ns>
```

For each scenario it substitutes the suffix
`--scenario-id <registered-S-id> --event-fd <decimal-fd> --start-barrier-fd <decimal-fd> --case-start-monotonic-ns <decimal-ns> --helper-start-deadline-monotonic-ns <decimal-ns> --outer-case-deadline-monotonic-ns <decimal-ns>` and omits case/hook/
injection arguments. Placeholders are data-only and must match the current
table/token/held datagram endpoint; no shell parses the vector. The coordinator
uses the same exact closed environment and repository cwd as the outer command,
with no additional key and only the event and start-barrier FDs inheritable. It
publishes the child PID/start-tick/PPID/PGID to the outer supervisor in exact
`msae_v3_gen7_test_control_frame_v1` frame 3 before the child may enter the
helper. The launcher child calls
`foreground_tmux_start_v1` with the exact `containment_test` schema. Hooks 1–7
therefore kill only this per-case launcher group, never the persistent pytest
leader. The exact fake
broker/pane argv and source literals plus SHA-256 constants are implementation-
review subjects.

The matrix selects each of the 52 literal shared-helper hooks exactly twice,
once per registered injection kind, for 104 shared-helper cases. Crash cases
must be cleaned by the complementary production authority in the table;
exception cases must return through the reporting helper's actual
`except/finally`. The supervisor observes both and performs no passing cleanup.
The exact fake-process control schema is
`msae_v3_gen7_fake_fault_control_v2`, with the same exact keys and canonical
values as `msae_v3_gen7_fault_control_v2`; for a fake-hook case its
`selected_hook_id` is one literal row 53–75 and `case_index` is that global
index, while for a scenario it carries the same selected scenario and trigger
as the helper control. Disabled production values are the same exact disabled
projection. Fake code may only emit the registered event then stop/raise or
perform the exact selected-scenario action from the table; it contains no
cleanup. For a scenario whose reporter is not a fake process, fake code only
validates the scenario object and executes its ordinary baseline path. The
pane-supervisor shared-helper role must
observe the exit/exception and run production terminalization/cleanup.

| global # | fake hook id | reporter_kind | state | crash owner | exception owner |
|---:|---|---|---|---|---|
| 53 | `before_fake_broker_fork` | `pane_supervisor` | `pre` | `monitor` | `pane_supervisor` |
| 54 | `fake_broker_child_before_pdeath_arm` | `fake_broker_child` | `pre` | `pane_supervisor` | `pane_supervisor` |
| 55 | `fake_broker_child_after_pdeath_arm_before_exec` | `fake_broker_child` | `post` | `pane_supervisor` | `pane_supervisor` |
| 56 | `pane_after_fake_broker_fork` | `pane_supervisor` | `post` | `monitor` | `pane_supervisor` |
| 57 | `before_process_record_partial_write` | `fake_broker` | `pre` | `pane_supervisor` | `pane_supervisor` |
| 58 | `after_process_record_partial_write` | `fake_broker` | `post` | `pane_supervisor` | `pane_supervisor` |
| 59 | `after_process_record_file_fsync` | `fake_broker` | `post` | `pane_supervisor` | `pane_supervisor` |
| 60 | `after_process_record_hardlink` | `fake_broker` | `post` | `pane_supervisor` | `pane_supervisor` |
| 61 | `after_process_record_source_unlink` | `fake_broker` | `post` | `pane_supervisor` | `pane_supervisor` |
| 62 | `before_identity_ack_send` | `fake_broker` | `pre` | `pane_supervisor` | `pane_supervisor` |
| 63 | `after_identity_ack_send` | `fake_broker` | `post` | `pane_supervisor` | `pane_supervisor` |
| 64 | `before_barrier_release_receive` | `fake_broker` | `pre` | `pane_supervisor` | `pane_supervisor` |
| 65 | `after_barrier_release_receive` | `fake_broker` | `post` | `pane_supervisor` | `pane_supervisor` |
| 66 | `before_resistance_arm` | `fake_broker` | `pre` | `pane_supervisor` | `pane_supervisor` |
| 67 | `after_resistance_arm` | `fake_broker` | `post` | `pane_supervisor` | `pane_supervisor` |
| 68 | `before_fake_handoff_commit_send` | `fake_broker` | `pre` | `pane_supervisor` | `pane_supervisor` |
| 69 | `after_fake_handoff_commit_send` | `fake_broker` | `post` | `pane_supervisor` | `pane_supervisor` |
| 70 | `before_fake_takeover_ack_receive` | `fake_broker` | `pre` | `pane_supervisor` | `pane_supervisor` |
| 71 | `after_fake_takeover_ack_receive` | `fake_broker` | `post` | `pane_supervisor` | `pane_supervisor` |
| 72 | `before_fake_worker_fork` | `fake_broker` | `pre` | `pane_supervisor` | `pane_supervisor` |
| 73 | `fake_worker_child_before_pdeath_arm` | `fake_worker_child` | `pre` | `pane_supervisor` | `pane_supervisor` |
| 74 | `fake_worker_child_after_pdeath_arm_before_exec` | `fake_worker_child` | `post` | `pane_supervisor` | `pane_supervisor` |
| 75 | `fake_broker_after_worker_fork` | `fake_broker` | `post` | `pane_supervisor` | `pane_supervisor` |

Each row runs crash and exception, so the complete hook matrix is 150 cases.
The same case-ledger schema/filename/state rules apply, and `reporter_role` may
add only `fake_broker` or `fake_worker` for rows 53–75. Child rows use exact
`reporter_kind` shown while their owning helper role remains their parent.

Non-hook lifecycle scenarios are exact. `LM1`–`LM7` below name the seven
launcher↔monitor frames and `PL1`–`PL2` the pane-lease frames; they never name
the outer supervisor control frames.

| ID | literal `boundary_id` | required durable prefix | literal initiator | literal trigger | literal `action` enum | exact action / target kind | reporter role / kind | terminal / cleanup / evidence owner |
|---|---|---|---|---|---|---|---|---|
| `S01_monitor_death` | `monitor_after_lm5_pane_arm_before_lm6` | LM5+PL2+pane arm, before LM6 while launcher live | `outer_supervisor` | `kill_monitor_before_handoff` | `sigkill_monitor_before_handoff` | SIGKILL stopped monitor / `process` | `monitor` / `monitor` | `launcher` |
| `S02_server_death` | `monitor_proxy_after_lm5_before_lm6` | LM5+PL2+pane arm, before LM6 | `outer_supervisor` | `kill_server_before_handoff` | `resume_monitor_then_sigkill_server_group` | resume monitor proxy, then SIGKILL foreground-server group / `process_group` | `monitor` / `monitor` | `monitor` |
| `S03_pane_death` | `pane_after_lm7_expected_eof` | LM7+EOF, live monitor/lease/session | `outer_supervisor` | `kill_pane_after_takeover` | `sigkill_pane_group_after_takeover` | SIGKILL stopped pane group / `process_group` | `pane_supervisor` / `pane_supervisor` | `monitor` |
| `S04_broker_death` | `broker_after_lm7_before_worker_terminal` | LM7+EOF and durable broker identity, before worker terminal | `outer_supervisor` | `kill_broker_after_takeover` | `sigkill_broker_after_takeover` | SIGKILL stopped broker / `process` | `fake_broker` / `fake_broker` | `pane_supervisor` |
| `S05_worker_death` | `worker_after_pre_model_gate` | LM7+EOF and durable worker pre-model identity | `outer_supervisor` | `kill_worker_after_pre_model_gate` | `sigkill_worker_after_pre_model_gate` | SIGKILL stopped worker / `process` | `fake_worker` / `fake_worker` | `pane_supervisor` |
| `S06_duplicate_frame` | `launcher_after_lm3_before_lm4` | LM1–LM3 accepted, before LM4 | `per_case_launcher` | `duplicate_monitor_frame_2` | `send_duplicate_lm2` | after resume send identical canonical LM2 bytes / `monitor_frame` | `launcher` / `launcher` | `monitor` |
| `S07_late_frame` | `launcher_after_lm5_before_lm6` | LM5 accepted, before LM6 | `per_case_launcher` | `replay_stale_monitor_frame_4` | `replay_stale_lm4` | after resume replay canonical LM4 bytes with stale sequence/prior / `monitor_frame` | `launcher` / `launcher` | `monitor` |
| `S08_monitor_death_after_launcher_eof` | `monitor_after_lm7_expected_eof` | LM7+launcher return/EOF, live monitor+pane+lease+session | `outer_supervisor` | `kill_monitor_after_expected_eof` | `sigkill_monitor_after_expected_eof` | SIGKILL stopped monitor / `process` | `monitor` / `monitor` | `pane_supervisor` |
| `S09_child_timeout` | `launcher_waiting_lm5_after_lm4` | LM4/START_SERVER plus PL2+pane arm, before LM5 | `per_case_launcher` | `receive_timeout_lm5_at_helper_deadline` | `observe_lm5_receive_timeout` | after resume launcher receives no LM5 through exact 8-second helper deadline; monitor keeps LM5 unsent / `deadline` | `launcher` / `launcher` | `launcher` |
| `S10_term_resistant_descendant` | `worker_sigterm_ignored_after_lm7` | LM7+EOF, durable worker identity and exact `/proc` SIGTERM-ignore proof | `outer_supervisor` | `sigusr1_pane_after_resistance_prefix` | `resume_worker_then_sigusr1_pane` | resume worker to running state, then SIGUSR1 pane self-pipe to commit technical failure / `process` | `fake_worker` / `fake_worker` | `pane_supervisor` |
| `S11_kill_escalation` | `broker_with_stopped_resistant_worker_after_lm7` | LM7+EOF, broker leader plus stopped resistant same-PGID worker | `fake_broker` | `exit_broker_leave_resistant_group` | `resume_worker_then_exit_broker_97` | after resume broker SIGCONTs/proves worker running, then exits 97; pane must rediscover/TERM/KILL leaderless group / `process_group` | `fake_broker` / `fake_broker` | `pane_supervisor` |
| `S12_final_absence_probe` | `monitor_live_baseline_after_expected_eof` | uninjected LM7+EOF live baseline | `monitor` | `expire_at_outer_deadline_minus_14s` | `expire_monitor_at_outer_minus_14s` | after resume monitor waits until exact outer-case deadline minus 14,000,000,000 ns / `deadline` | `monitor` / `monitor` | `monitor` |

These twelve boundary IDs and twelve action enums are pairwise unique closed
sets mapped one-to-one to the scenario ID in the same row. Unknown, duplicated,
cross-row substituted, extra, or case-mismatched values block before action;
mutation tests exercise each failure. `scenario_action_observation.action` is
the row's quoted action enum byte-for-byte, never the prose action cell.

S06/S07/S09 also require one credentialed `SCENARIO_ACTION_OBSERVED` event from
the production receiver/owner before cleanup can retire operational evidence.
For S06/S07 the observer is the monitor and `observation` has schema
`msae_v3_gen7_monitor_frame_rejection_v1`, exact keys `schema_version`,
`original_frame`, `current_prior_frame`, `rejected_frame`, `violation_code`,
`expected_sequence`, `expected_prior_sha256`, and `peer_process`. Each frame is
the complete exact canonical `msae_v3_gen7_monitor_frame_v1` object, not merely
a caller label; outer canonicalization must reproduce its digest. In S06 the
original and rejected objects are byte-identical LM2, current prior is LM3,
expected sequence is 4, and violation is `duplicate_sequence`. In S07 the
original and rejected objects are byte-identical LM4, current prior is LM5,
expected sequence is 6, and violation is `stale_sequence_prior`; in both rows
the expected prior is the current-prior digest and peer is the exact launcher
process. The combined event must fit the already-frozen 4096-byte datagram cap;
the uninjected size assertion and an oversized mutation both fail closed.
For S09 the observer is the launcher receiver and `observation` has schema
`msae_v3_gen7_monitor_frame_receive_timeout_v1`, exact keys `schema_version`,
`expected_frame_type` (`SERVER_READY`), `expected_sequence` (5),
`current_prior_frame` (the complete canonical LM4 object), `channel_peer` (the
exact monitor process), `wait_started_monotonic_ns`, `deadline_monotonic_ns`,
`observation_monotonic_ns`, `poll_result` (`timeout`), and
`received_bytes_count` (0). It is emitted from the actual receiver only after
the exact helper deadline and before launcher-owned technical-failure cleanup;
any queued/readable frame makes the scenario fail instead. The outer retains the canonical action-event bytes
through final result construction. Unknown observer, wrong credential, wrong
frame/object/digest/sequence/prior/action, missing/duplicate event, or an event
for any other scenario blocks.

For every row the three listed owner roles are identical. `target_identity` is
one of four exact tagged schemas. `msae_v3_gen7_scenario_process_v1` has keys
`schema_version`, `kind` (`process`), `role`, `pid`, `start_ticks`, `ppid`,
`pgid`, `uid`, and `gid`. `msae_v3_gen7_scenario_process_group_v1` has keys
`schema_version`, `kind` (`process_group`), `role`, `pgid`, `leader_pid`,
`leader_start_ticks`, and `members`; `members` is a PID-sorted nonempty array of
the exact process rows with no duplicate PID/start-tick. A leader may already be
dead only for S11 after its acknowledged action, never in the prefix.
`msae_v3_gen7_scenario_monitor_frame_v1` has keys `schema_version`, `kind`
(`monitor_frame`), `direction`, `frame_type`, `sequence`, `frame_sha256`, and
`peer_process`; `peer_process` is the exact monitor process row.
`msae_v3_gen7_scenario_deadline_v1` has keys `schema_version`, `kind`
(`deadline`), `owner_process`, `deadline_monotonic_ns`, and `source`; source is
the row's literal trigger. Rows S01/S04/S05/S08 use `process`; S02/S03/S11 use
`process_group`; S06/S07 use `monitor_frame`; S09/S12 use `deadline`; S10 uses
the pane-supervisor `process`. No target field is null or implementation chosen.

The required prefix is reconstructed as canonical schema
`msae_v3_gen7_scenario_prefix_v2` with exact keys `schema_version`,
`scenario_id`, `boundary_event_sha256`, `durable_entries`, `live_processes`,
`lease_binding`, `session`, `deadlines`, and `signal_dispositions`.
`boundary_event_sha256` is the exact observed canonical
`SCENARIO_BOUNDARY_REACHED` datagram digest. The outer does not claim to observe
private LM/PL bytes; the table's LM/PL notation identifies the shared-helper
boundary whose literal `boundary_id` and reporter credentials are mutation-
tested. `durable_entries` has exact keys
`monitor_record`, `pane_arm`, `process_record`, and `terminal_claim`; each is
the descriptor-reopened regular entry `{path,type,mode,uid,gid,nlink,size,
sha256}` or null only when the table prefix proves it absent, and
`terminal_claim` is always null before the scenario action. Exact barrier rules
make `monitor_record` present in all rows; `pane_arm` absent only in S06 and
present otherwise; and `process_record` present only in S03–S05, S08, and
S10–S12 and absent in S01/S02/S06/S07/S09. Any other presence projection blocks.
`live_processes` is
a PID-sorted array of exact process rows containing every then-live per-case
launcher/monitor/server/pane/broker/worker descendant and no other process.
`lease_binding` is the exact already-defined binding. `session` has exact keys
`name`, `state`, `has_session_returncode`, `server_process`, and `pane_process`.
For S06 its state is `absent`, return code is a nonzero integer, and both process
fields are null; for every other row its state is `live`, return code is zero,
and both fields are exact process rows (S09 uses the continuously captured pane
row even though LM5 is deliberately withheld). `deadlines` has exact keys
`case_start_monotonic_ns`, `helper_start_deadline_monotonic_ns`,
`post_takeover_failure_deadline_monotonic_ns`, and
`outer_case_deadline_monotonic_ns`. The first, second, and fourth equal the
frame-2 supervisor values exactly, with second = first + 8,000,000,000 and
fourth = first + 24,000,000,000. The post-takeover value is null for S01–S11
and for S12 equals the outer-case deadline minus exactly 14,000,000,000 ns,
leaving the exact 12-second cleanup budget plus a 2-second outer margin.
`signal_dispositions` has the sole exact key `term_resistant_worker`, null except
in S10/S11. Its non-null value is schema
`msae_v3_gen7_signal_disposition_v1` with exact keys `schema_version`, `pid`,
`start_ticks`, `proc_status_sha256`, `state`, `sigign_hex`, `sigterm_number`,
`sigterm_mask_hex`, and `sigterm_ignored`; it binds a descriptor-stable raw
`/proc/<pid>/status` read, requires state `T`, signal number 15, the exact
1-based signal-15 bit mask, and `sigterm_ignored=true`. Arrays are sorted
as stated; maps have only the stated keys; every null is independently
reconstructed.

No reporter is required or permitted to construct this global prefix. At its
one local registered boundary, the designated reporter sends canonical
`SCENARIO_BOUNDARY_REACHED` and SIGSTOPs itself. The outer validates credentials,
the exact local boundary and reporter process, then independently reconstructs the
complete prefix from the observed boundary event, descriptor-reopened entries,
continuous process capture, `/proc`, lease, session, and deadlines. Only after
that digest exists may it acknowledge the boundary. For S01/S03–S05/S08, the
registered SIGKILL of the stopped reporter/target is both acknowledgement and
action. For S02 the monitor is an explicit proxy reporter: the outer SIGCONTs
it and then SIGKILLs the separately validated server group. For S06/S07/S09/
S11/S12 the outer SIGCONTs only the stopped reporter, which then performs the
literal action. For S10 the outer first SIGCONTs the exact worker, requires the
same PID/start-tick to reach a non-stopped, non-zombie state while retaining the
same signal-15 ignore bit, and only then sends SIGUSR1 to the validated
pane-supervisor. The containment-only handler writes one byte to its existing
helper self-pipe, commits the registered technical failure, and enters the
ordinary pane cleanup path. Pane cleanup sends TERM, waits exactly 250,000,000
ns, and binds that the same running worker remains live with signal 15 ignored
before escalating to KILL and proving extinction. For S06/S07 the receiving
monitor emits the exact rejected-frame action event; for S09 the launcher emits
the exact receive-timeout action event at deadline;
the outer must receive and validate it before `OWNER_LEDGER_READY`.
Missing prefix, resume, action, technical-failure trigger, or completion before the outer
24-second watchdog fails the case. No extra supervisor-control frame is added.
Each has a canonical ledger named
`scenario-<literal-id>.json`, schema
`msae_v3_gen7_tmux_fault_scenario_v1`, and exact keys `schema_version`,
`test_token`, `scenario_id`, `reporter_role`, `reporter_kind`, `reporter_pid`,
`reporter_start_ticks`, `reporter_pgid`, `boundary_event_sha256`,
`action_event_sha256`, `initiator`, `target_identity`, `trigger`,
`expected_terminal_owner`, `expected_cleanup_owner`, `evidence_publisher`,
`production_cleanup_complete`, `emergency_cleanup_used`,
`terminal_claim_sha256`, `scenario_action_observation_sha256`,
`evidence_projection_sha256`,
`pre_exit_absence_sha256`, `expected_outer_final_descriptor_sha256`, and
`outcome`; initiator, target, trigger, reporter, boundary event, and the three
owner fields equal the table. The evidence publisher independently reconstructs
the canonical boundary-event bytes from the selected control plus its durable
reporter/target bindings; the outer rejects any digest mismatch with the
datagram it actually received. In the ledger, action observation, and outer
result alike, `action_event_sha256` must equal the digest of the one validated
credentialed event the outer actually received for S06/S07/S09 and must be JSON
null for every other scenario; no caller-supplied substitute is accepted. The
evidence publisher reconstructs canonical
`msae_v3_gen7_scenario_action_observation_v1`, exact keys `schema_version`,
`scenario_id`, `boundary_event_sha256`, `action_event_sha256`, `initiator`, `trigger`,
`target_identity`, `pre_action_processes`, `action`, `post_action_processes`,
and `term_escalation`. Process arrays are PID-sorted exact process rows;
`action_event_sha256` is the observed credentialed event digest for S06/S07/S09
and null for every other row. `action` is the table's literal quoted action
enum. `term_escalation` is null except S10/S11;
there it has exact keys `term_sent_monotonic_ns`, `term_grace_ns` (250,000,000),
`post_term_process`, `sigterm_ignored`, `kill_sent_monotonic_ns`, and
`post_kill_live`; the post-TERM row is the same live PID/start-tick in a
non-stopped/non-zombie state, `sigterm_ignored` is true, and `post_kill_live` is
false. Specifically, `post_term_process` is not the ordinary identity row: it
has schema `msae_v3_gen7_post_term_observation_v1` and exact keys
`schema_version`, `pid`, `start_ticks`, `observation_monotonic_ns`,
`proc_stat_sha256`, `proc_status_sha256`, `state`, `live`, `sigign_hex`, and
`sigterm_ignored`. It descriptor-stably binds both raw `/proc` reads, requires
the same PID/start-tick, `live=true`, state one of `R`,`S`,`D`,`I` (never
`T`,`t`,`Z`,`X`), the same signal-15 ignore bit, and an observation ordered
after `term_sent_monotonic_ns` plus the exact grace and before
`kill_sent_monotonic_ns`.
After outer-final teardown the supervisor constructs canonical
`msae_v3_gen7_scenario_outer_result_v1` with exact keys `schema_version`,
`test_token`, `scenario_id`, `boundary_event_sha256`,
`action_event_sha256`, `required_prefix_sha256`,
`scenario_action_observation_sha256`, `ledger_sha256`,
and `outer_final_extinction_sha256`. It independently recomputes the owner
observation and binds this result into the immutable overall test transcript;
the evidence publisher never supplies or predicts the global prefix digest.
The owner must
complete production cleanup with no emergency action before the next scenario.
For S08 specifically, the coordinator first requires frame 7, launcher return,
expected control EOF, and a still-live monitor/pane/lease/session subject; only
then it SIGKILLs the validated monitor. Ordinary expected post-frame-7 EOF has
no terminal claim and no cleanup, and is separately asserted in the uninjected
baseline.

For every case, the supervisor—not pytest emergency cleanup—must prove before
namespace reuse: every per-case monitor/server/pane/broker/worker process group
empty; captured monitor/server/pane/broker/worker PID/start-ticks extinct; the
one exact pytest leader remains live with no unregistered member in its
dedicated group; session absent; ACK, broker, and tmux
sockets plus the pane-lease socket absent; scratch and terminal-test artifacts
absent; all seven production/test short families closed; no
GPU/model/import/environment tripwire fired. The test fails
if any production cleanup action is stubbed. Each fake-broker-only case likewise
has the two typed realizations above; no independently coded cleanup may make it
pass. Emergency cleanup is reported as a test failure, never as passing
evidence. A mutation test stubs each registered production cleanup operation in
turn and requires both its crash and exception case to fail before emergency
cleanup protects the host.
After the final case pytest must return zero; only then may the outer supervisor
observe/reap that one pytest process and require its whole group empty. No
intermediate case may signal or reap the long-lived pytest leader.

Process tripwires cover `subprocess` call/Popen/run/check*, `os.system`,
`posix_spawn*`, and `exec*`; environment tripwires reject transient or persistent
CUDA/HIP/ROCR/preload/library/PYTHONPATH changes; imports reject torch,
transformers, model modules, and GPU libraries; no `nvidia-smi` vector is
allowed. The only process vectors are exact reviewed Python/pytest/fake vectors
and exact helper-generated tmux vectors.

## Exact review schemas

Every review is create-once, canonical UTF-8/LF with one terminal newline,
mode-0644, current UID/GID, regular nlink-1, no symlink ancestor, and has exactly
one `VERDICT: SHIP` plus one exact `REVIEW_SCOPE`. Control-like malformed,
indented, duplicated, conflicting, extra, or reordered lines block. Each
`*_SHA256` line is lowerhex and the controls below occur in this exact order;
free prose may not lexically resemble a control. Every review ends with exactly
one `SEALED_PAYLOAD_CONTENT_READS: 0` when listed.

1. Plan review, scope `gen7_plan`:
   `GEN6_PLAN_SHA256`, `GEN6_PLAN_REVIEW_SHA256`,
   `GEN6_FAILURE_REVIEW_SHA256`, `GEN7_PLAN_SHA256`.
2. Pre-capability review, scope `gen7_pre_capability`:
   `GEN7_PLAN_SHA256`, `GEN7_PLAN_REVIEW_SHA256`,
   `GEN7_CONTROLLER_SHA256`, `GEN7_RUNTIME_SHA256`, `GEN7_RUNNER_SHA256`,
   `GEN7_LAUNCHER_SHA256`, `GEN7_TMUX_TEST_SUPERVISOR_SHA256`,
   `GEN7_RFC_SHA256`, `GEN7_TESTS_SHA256`, then the sealed-read control. Its
   `CHECKS RUN` section additionally contains the exact ordered command-evidence
   rows from the verification plan; a summary without argv/cwd/env/subject and
   exit status is not valid.
3. Implementation review, scope `gen7_implementation`:
   `M1_COMPLETION_SHA256`, `M2_COMPLETION_SHA256`,
   `GEN6_PLAN_SHA256`, `GEN6_PLAN_REVIEW_SHA256`,
   `GEN6_FAILURE_REVIEW_SHA256`, `GEN6_CONTROLLER_SHA256`,
   `GEN6_RUNTIME_SHA256`, `GEN6_RUNNER_SHA256`, `GEN6_LAUNCHER_SHA256`,
   `GEN6_TMUX_TEST_SUPERVISOR_SHA256`, `GEN6_RFC_SHA256`,
   `GEN6_TESTS_SHA256`, `GEN7_CAPABILITY_REPRODUCTION_SHA256`,
   `PREDICTED_GEN7_FAILED_GEN6_SHA256`, `GEN7_PLAN_SHA256`,
   `GEN7_PLAN_REVIEW_SHA256`, `GEN7_PRE_CAPABILITY_REVIEW_SHA256`,
   `GEN7_CONTROLLER_SHA256`, `GEN7_RUNTIME_SHA256`, `GEN7_RUNNER_SHA256`,
   `GEN7_LAUNCHER_SHA256`, `GEN7_TMUX_TEST_SUPERVISOR_SHA256`,
   `GEN7_RFC_SHA256`, `GEN7_TESTS_SHA256`, then the sealed-read control. The
   parser reconstructs `overall_pass=true` capability and the predicted failure
   payload; hashing malformed/negative bytes cannot authorize setup.
4. Post-M3 review, scope `gen7_post_m3`:
   `GEN7_IMPLEMENTATION_REVIEW_SHA256`, `POST_M3_SUBJECT_SHA256`,
   `GEN7_PROTOCOL_SHA256`, `GEN7_AUTHORIZATION_COMMITMENT_SHA256`,
   `GEN7_PUBLIC_KEY_SHA256`, `GEN7_CPU_TRACE_SHA256`,
   `GEN7_SETUP_MANIFEST_SHA256`, `GEN7_FAILED_GEN6_SHA256`,
   `GEN7_FAILED_GEN5_SHA256`, `GEN7_FAILED_GEN4_SHA256`,
   `GEN7_FAILED_GEN3_SHA256`, `GEN7_FAILED_GEN2_SHA256`,
   `M2_COMPLETION_SHA256`, then the sealed-read control.
5. Prescore review, scope `gen7_prescore`:
   `GEN7_IMPLEMENTATION_REVIEW_SHA256`, `GEN7_POST_M3_REVIEW_SHA256`,
   `GEN7_STAGE_A_SHA256`, `GEN7_CANDIDATE_MANIFEST_SHA256`,
   `GEN7_PRESCORE_CHECK_SHA256`, `GEN7_PRESCORE_TRACE_SHA256`,
   `GEN7_PROTOCOL_SHA256`, `GEN7_DEPENDENCY_CLOSURE_SHA256`,
   `GEN7_STATUS_SHA256`, then the sealed-read control.

The exact plan review authorizes implementation only. Pre-capability review
authorizes one capability observation. Implementation review authorizes setup.
Post-M3 review authorizes M4. Prescore review authorizes the grouped
sign-and-launch calibration transition; signer and launcher each independently
revalidate all preceding bytes, live namespaces, nonce state, and review
controls. There are no promised but unregistered post-sign or pre-launch review
artifacts.

## Capability and review sequence

This exact order is mandatory:

1. finish all seven implementation entries;
2. run isolated passing predecessors, gen7 CPU/static/source-only tests, NFS
   publisher matrix, exact real-tmux test, syntax, Bash, diff, namespace,
   sealed-lstat, and subject-hash checks;
3. obtain create-once pre-capability adversarial `SHIP` binding plan, plan
   review, seven implementation entries, exact check transcripts, and
   `SEALED_PAYLOAD_CONTENT_READS: 0`;
4. run the create-once gen7 capability reproduction only once;
5. require canonical `overall_pass=true`, exact descriptor recovery/cleanup,
   and no downstream state;
6. obtain create-once final implementation adversarial `SHIP` binding the
   capability report, predicted failed-gen6 payload, predecessor subjects,
   seven gen7 entries, and zero sealed reads;
7. only then run setup M3; obtain external post-M3 `SHIP`;
8. build M4 as two complete independent trees with no live-root fallback,
   compare all inputs/outputs, recoverably install six Stage-A artifacts, and
   obtain external prescore `SHIP`;
9. sign the single calibration authorization and publish its unused nonce, then
   call only the launcher; the caller never pre-consumes it; and
10. launcher selects/locks an idle GPU, creates the monitored tmux calibration,
    waits for durable live handoff/takeover ACK, then returns immediately without
    waiting for Stage B.

Capability is non-scientific and uses no model/GPU. A canonical completed
negative capability report terminates gen7. A crash after a durable descriptor
recovers exact sealed report bytes without rerunning observation. No
pre-capability interruption may be cherry-picked after report authority exists.

Only the launched, fully validated runner atomically consumes the nonce, after
authorization/config/closure/lease/readiness validation and immediately before
the durable pre-model gate. Any failure before that gate leaves no model import;
any replay after consumption blocks. The launcher never consumes on behalf of
the runner.

Setup carries forward the gen6 DAG with provenance-root creation first. The
exact 24 sequential receipts are:

| index/name | exact step | exact action | literal `target` |
|---|---|---|---|
| `0001_gen7_provenance_root.json` | `gen7_provenance_root` | `mkdir` | `/jumbo/lisp/f004ndc/experiments/wip/MSAE/reports/provenance/msae_independent_measurement_v3_post_m2_gen7` |
| `0002_failed_gen6.json` | `failed_gen6` | `publish` | `/jumbo/lisp/f004ndc/experiments/wip/MSAE/reports/provenance/msae_independent_measurement_v3_post_m2_gen7/failed_gen6.json` |
| `0003_failed_gen5.json` | `failed_gen5` | `publish` | `/jumbo/lisp/f004ndc/experiments/wip/MSAE/reports/provenance/msae_independent_measurement_v3_post_m2_gen7/failed_gen5.json` |
| `0004_failed_gen4.json` | `failed_gen4` | `publish` | `/jumbo/lisp/f004ndc/experiments/wip/MSAE/reports/provenance/msae_independent_measurement_v3_post_m2_gen7/failed_gen4.json` |
| `0005_failed_gen3.json` | `failed_gen3` | `publish` | `/jumbo/lisp/f004ndc/experiments/wip/MSAE/reports/provenance/msae_independent_measurement_v3_post_m2_gen7/failed_gen3.json` |
| `0006_failed_gen2.json` | `failed_gen2` | `publish` | `/jumbo/lisp/f004ndc/experiments/wip/MSAE/reports/provenance/msae_independent_measurement_v3_post_m2_gen7/failed_gen2.json` |
| `0007_gen7_m4_data_root.json` | `gen7_m4_data_root` | `mkdir` | `/jumbo/lisp/f004ndc/experiments/wip/MSAE/data/msae_independent_measurement_v3_post_m2_gen7` |
| `0008_gen7_config_root.json` | `gen7_config_root` | `mkdir` | `/jumbo/lisp/f004ndc/experiments/wip/MSAE/configs/msae_independent_measurement_v3_post_m2_gen7` |
| `0009_gen7_state_root.json` | `gen7_state_root` | `mkdir` | `/jumbo/lisp/f004ndc/.msae_state/independent_measurement_v3_post_m2_gen7` |
| `0010_gen7_nonce_root.json` | `gen7_nonce_root` | `mkdir` | `/jumbo/lisp/f004ndc/.msae_state/independent_measurement_v3_post_m2_gen7/nonces` |
| `0011_key_staging_root.json` | `key_staging_root` | `mkdir` | `/jumbo/lisp/f004ndc/.msae_keys/.independent_measurement_v3_post_m2_gen7_setup` |
| `0012_key_payload.json` | `key_payload` | `publish` | `/jumbo/lisp/f004ndc/.msae_keys/.independent_measurement_v3_post_m2_gen7_setup/private_key.payload` |
| `0013_key_binding.json` | `key_binding` | `publish` | `/jumbo/lisp/f004ndc/.msae_keys/.independent_measurement_v3_post_m2_gen7_setup/key_binding.json` |
| `0014_final_private_key.json` | `final_private_key` | `publish` | `/jumbo/lisp/f004ndc/.msae_keys/independent_measurement_v3_post_m2_gen7_ed25519_private.pem` |
| `0015_setup_subject.json` | `setup_subject` | `bind` | `virtual://setup_subject` |
| `0016_public_key.json` | `public_key` | `publish` | `/jumbo/lisp/f004ndc/experiments/wip/MSAE/configs/msae_independent_measurement_v3_post_m2_gen7/ed25519_public.pem` |
| `0017_authorization_commitment.json` | `authorization_commitment` | `publish` | `/jumbo/lisp/f004ndc/experiments/wip/MSAE/configs/msae_independent_measurement_v3_post_m2_gen7/authorization_commitment.json` |
| `0018_cpu_no_model_trace.json` | `cpu_no_model_trace` | `publish` | `/jumbo/lisp/f004ndc/experiments/wip/MSAE/configs/msae_independent_measurement_v3_post_m2_gen7/cpu_no_model_public_entry_trace.json` |
| `0019_protocol_config.json` | `protocol_config` | `publish` | `/jumbo/lisp/f004ndc/experiments/wip/MSAE/configs/msae_independent_measurement_v3_post_m2_gen7/protocol.json` |
| `0020_key_binding_deleted.json` | `key_binding_deleted` | `unlink` | `/jumbo/lisp/f004ndc/.msae_keys/.independent_measurement_v3_post_m2_gen7_setup/key_binding.json` |
| `0021_key_payload_deleted.json` | `key_payload_deleted` | `unlink` | `/jumbo/lisp/f004ndc/.msae_keys/.independent_measurement_v3_post_m2_gen7_setup/private_key.payload` |
| `0022_key_staging_root_removed.json` | `key_staging_root_removed` | `rmdir` | `/jumbo/lisp/f004ndc/.msae_keys/.independent_measurement_v3_post_m2_gen7_setup` |
| `0023_pre_manifest_projection.json` | `pre_manifest_projection` | `verify` | `virtual://pre_manifest_projection` |
| `0024_setup_manifest.json` | `setup_manifest` | `publish` | `/jumbo/lisp/f004ndc/experiments/wip/MSAE/reports/provenance/msae_independent_measurement_v3_post_m2_gen7/setup_m3_gen7_manifest.json` |

Receipt schema is `msae_v3_gen7_setup_receipt_v1` with exact keys
`schema_version`, `protocol_id`, `generation`, `index`, `step`, `action`,
`target`, `transaction_sha256`, `predecessor_receipt_sha256`, and
`payload_sha256`. Receipt 0001 has JSON null predecessor; every later receipt
binds the exact SHA-256 of the immediately preceding canonical receipt.
`payload_sha256` is JSON null exactly for `mkdir`, `unlink`, `rmdir`, and
`verify`; `bind` contains the setup-subject digest and `publish` contains the
published regular-file digest. Each file action uses the already-registered NFS
descriptor/payload publication primitive, exact target mode/UID/GID/nlink/type,
parent fsync, and recovery matrix.

The setup manifest schema is exactly `msae_v3_gen7_setup_manifest_v1` and its
top-level keys are exactly `schema_version`, `protocol_id`, `generation`,
`status`, `lineage`, `transaction_sha256`,
`receipt_sha256_through_0023`, `receipt_0024_derivation`, `setup_subject`,
`setup_subject_sha256`, `final_entries`, and `exact_child_sets`. The receipt map
has exactly the literal receipt-name keys 0001–0023 from the table and each
value is the lowercase SHA-256 of that canonical receipt. `final_entries` is
the exact gen6-substituted typed file projection plus `failed_gen6`; the private
key remains lstat-only. `exact_child_sets` is exactly the gen6-substituted root
projection with `failed_gen6.json` inserted in the provenance set. No timestamp,
random ordering, receipt 0024 digest, or inferred child is permitted.

`receipt_0024_derivation` has exact schema
`msae_v3_gen7_setup_receipt_0024_derivation_v1` and exact keys
`schema_version`, `index`, `step`, `action`, `target`,
`predecessor_receipt_sha256`, and `payload_is_setup_manifest_sha256`. Values are
respectively that schema, integer `24`, `setup_manifest`, `publish`, the literal
receipt-0024 target in the table, the receipt-0023 digest, and JSON `true`.
These canonical manifest bytes are constructed and hashed first. Receipt 0024
is then constructed with the receipt schema above, index 24, the same
step/action/target, the same transaction digest, predecessor receipt-0023
digest, and `payload_sha256` equal to the manifest digest. The manifest never
binds receipt 0024. Validators reconstruct the manifest first and derive the
only legal receipt 0024 second; reverse cleanup may delete authority only after
both reconstruct exactly. No implementation may infer ordinals, targets, or
preimages.

## Scientific inheritance

Gen7 mechanically reproduces and independently validates all immutable M1/M2
science and the gen6 generic projection:

- redesigned document/sentence/boilerplate overlap gate and selected source;
- strict CoNLL-U/entity parsing and actual generated prefix-task examples;
- discovery, calibration, C1, and C2 support;
- all four 500-map sets and finite-pass matrices;
- frozen calibration strata, seeds, examples, thresholds, and replay bundle;
- full model/tokenizer/checkpoint/environment/executable/library/native-map
  closure;
- exact g4/g5/g6/g7 roles and checkpoint lineages;
- complete localization, collateral, counterfactual, reproducibility, baseline,
  uncertainty, and status endpoint products;
- typed digest-based Stage-B pair, forward, pooling, selector, alignment, and
  terminal QA; and
- mutually exclusive terminal success or technical-failure-not-run artifacts.

Stage A contains no experimental result and cannot be ready unless every typed
M1/M2/support/map/closure/endpoint/replay invariant reconstructs. Stage B is
calibration only. Confirmation scoring and Stage C remain unreachable and
absent.

## Milestones

### P0 — plan authority

- [x] Bind the final gen6 failure-review digest.
- [ ] Verify frozen gen6 subject hashes and all gen6 downstream absences.
- [ ] Obtain independent plan `SHIP`; write the canonical create-once review.

Acceptance: no code or gen7 non-plan artifact exists before plan `SHIP`.

### P1 — implementation and CPU verification

- [ ] Create exactly seven gen7 implementation entries.
- [ ] Implement typed substitution comparator and failed-gen6 payload.
- [ ] Implement shared tmux helper and complete fault matrix test.
- [ ] Complete RFC and static/candidate/review closure updates.
- [ ] Run every registered safe command on final bytes.

Acceptance: every gen7 and successful-predecessor test passes in isolated closed
processes; real tmux test passes; failed-generation suites are only exact-hash
negative evidence; no capability/protocol/GPU/model state exists.

### P2 — adversarial capability and M3

- [ ] Obtain pre-capability `SHIP`.
- [ ] Run capability once; require `overall_pass=true`.
- [ ] Obtain final implementation `SHIP`.
- [ ] Run setup M3 once; obtain post-M3 `SHIP`.

Acceptance: all create-once reviews/reports/config/provenance are canonical,
fully revalidated, and non-authorizing until their next gate.

### P3 — Stage A and external prescore

- [ ] Build two complete M4 trees and recoverably install exactly six outputs.
- [ ] Run traced prescore verification with zero sealed reads.
- [ ] Obtain genuinely external prescore `SHIP`.

Acceptance: Stage A is ready and exact closure/candidate/absence projections
reconstruct; no model, GPU query/call, or scientific/production-calibration tmux
has run. The already-required registered nonexperimental containment-test tmux
activity is the sole exception and is bound by its final-absence transcript.

### P4 — calibration launch only

- [ ] Sign the one calibration authorization and publish one unused nonce.
- [ ] Invoke launcher; it chooses a free GPU and launches the validated runner,
  which alone consumes the nonce at its durable pre-model gate.
- [ ] Return after durable live handoff without waiting for results.

Acceptance: live handoff binds monitor/server/pane/broker/worker/lease/sockets/
nonce/config/Stage-A identities; launcher has returned; Stage C remains absent.

## Verification plan

All commands use the exact environment prefix
`/usr/bin/env -i PATH=/usr/bin:/bin HOME=/thayerfs/home/f004ndc LANG=C.UTF-8 LC_ALL=C.UTF-8`.
Direct source-only commands use `-S -B -I`. Installed pytest cannot import
under `-S`, so exactly ten registered pytest invocations omit `-S` and use
`-B -I -m pytest -q -p no:cacheprovider` plus
`PYTEST_DISABLE_PLUGIN_AUTOLOAD=1`: seven isolated passing-predecessor
invocations, one gen7 CPU invocation, one publisher invocation, and the one
pytest child of the source-only real-tmux supervisor. No other command may omit
`-S`. The exact file/selector suffixes are:

1. `tests/test_msae_independent_measurement_v1.py`;
2. `tests/test_msae_independent_measurement_v2.py`;
3. `tests/test_msae_independent_measurement_v3.py`;
4. `tests/test_msae_independent_measurement_v3_post_m1.py`;
5. `tests/test_msae_independent_measurement_v3_post_m2_runtime.py -k not\ failed_handoff_extinction_kills_real_processes_and_socket`;
6. `tests/test_msae_measurement_remediation_v1.py`;
7. `tests/test_msae_independent_measurement_v3_post_m4_gen4.py -k not\ failed_handoff_extinction_kills_real_processes_and_socket`;
8. `tests/test_msae_independent_measurement_v3_post_m7_gen7.py -k not\ failed_handoff_extinction_kills_real_processes_and_socket`;
9. the two literal node IDs
   `tests/test_msae_independent_measurement_v3_post_m7_gen7.py::test_nfs_publisher_fault_matrix`
   and
   `tests/test_msae_independent_measurement_v3_post_m7_gen7.py::test_local_mount_rejection_precedes_protocol_mutation`;
10. the supervisor child node ID
    `tests/test_msae_independent_measurement_v3_post_m7_gen7.py::test_failed_handoff_extinction_kills_real_processes_and_socket`.

The shell backslashes above only display the single argv token passed after
`-k`; implementation records argv as a JSON string array, never reparses a
shell command. The real-tmux outer command remains the exact `-S -B -I` command
registered earlier. The RFC must list these literal argv arrays rather than
using “etc.” or a glob.

Required evidence includes:

- isolated passing-suite summaries and transcripts;
- gen7 safe suite summary;
- exact publisher matrix summary;
- exact real-tmux matrix summary and per-boundary ledger;
- static surface/site/value-flow/import/process/network/file registry digests;
- source-only malicious `.pyc`/sourceless/extension-shadow regressions;
- Python in-memory compilation with no bytecode writes, `bash -n`, and
  `git diff --check`;
- exact seven file path/mode/uid/gid/nlink/size/SHA-256 rows;
- exact frozen predecessor rehash rows;
- complete namespace/short-socket-family absence rows;
- three sealed before/after `lstat` rows and zero content reads; and
- adversarial transcripts at every one-way door.

Concrete checks:

1. `sha256sum` and `stat -c` every frozen predecessor, plan/review, and seven
   gen7 implementation entry; compare to literal registries.
2. Run each passing predecessor test file in its own exact closed-environment
   `pytest -q -p no:cacheprovider` process and require exit zero.
3. Run the complete gen7 CPU suite with plugins/cache disabled and require zero
   failed, errored, xfailed, or unexpectedly skipped tests other than explicitly
   registered real-process selection.
4. Run the two exact NFS/local publisher tests and require `2 passed`, then
   descriptor-safely prove both test roots absent.
5. Run the exact registered `-S -B -I` real-tmux command and require exit zero,
   a complete per-boundary ledger, and final PID/PGID/session/socket/scratch
   absence.
6. Call the gen7 static-closure validator and require the frozen file/process/
   network/library/dynamic-import/value-flow/AST digests and source-only policy
   reproduce exactly.
7. Compile the five Python entries in memory with `compile(...)` (never
   `py_compile`), run `bash -n` on the launcher, and run `git diff --check`.
8. Under the sealed-open tripwire, enumerate every one-way namespace and all
   seven literal `m7t_`, `m7b_`, `m7p_`, `m7x_`, `m7a_`, `m7c_`, and `m7s_`
   short-family prefixes no-follow, then compare the three exact payload
   before/after `lstat` subjects and require zero content-read attempts.
9. Before each create-once transition, rehash the exact current subject and
   obtain the specified independent adversarial `SHIP`.

## Definition of done

- [ ] Gen6 remains exactly failed before capability; no claim says its frozen
  gen5 suite passed or its independent tmux test proved production helper paths.
- [ ] The exact gen6 failure-review digest is bound and the exact gen7 plan is
  reviewed `SHIP` before code.
- [ ] All seven gen7 implementation entries match the allowed substitution
  contract and no scientific semantics changed.
- [ ] Every successful predecessor and gen7 test passes in isolated closed
  processes; no failed-generation suite is used as pass evidence.
- [ ] The exact real-tmux test calls shared production helper bytes and exercises
  every registered monitor/start/cleanup/timeout boundary non-tautologically.
- [ ] Capability is `overall_pass=true`, then final implementation review is
  `SHIP`, then M3/post-M3/M4/prescore gates pass in order.
- [ ] Stage A binds full provenance, support/maps, calibration, closure, and all
  registered endpoints; no experiment ran before prescore `SHIP`.
- [ ] The signed launcher alone selects a free GPU and creates the calibration
  tmux session; the assistant returns immediately after durable handoff.
- [ ] No confirmation scoring or Stage C is run.
- [ ] All protocol/test temporary roots and broker sockets obey their exact
  lifetimes; live tmux socket persists only while the monitored session lives.
- [ ] The three sealed payload contents were never opened or hashed.

## Risks and one-way doors

- Publishing plan review freezes this plan; any material change requires a new
  generation.
- Publishing pre-capability review freezes all seven implementation entries.
- Publishing a completed negative capability report terminates gen7.
- Setup and M4 are separate one-way doors authorized respectively by the final
  implementation and post-M3 reviews. Prescore review is the one fresh external
  review immediately before the grouped sign-and-launch transition; signer,
  launcher, and runner then independently revalidate it and all live bindings.
  Nonce consumption remains an irreversible runner-only substep, not a separate
  review artifact.
- NFS link/fsync uncertainty is handled only by descriptor-authorized bounded
  recovery; path appearance alone is never authority.
- Tmux daemonization, delayed socket publication, PID reuse, peer spoofing,
  process-group escape, and monitor/pane death are controlled by the shared
  foreground helper and exact real-process matrix, not by optimistic sleeps.
- The calibration may take hours; returning after launch is intentional, but a
  persistent monitor retains the lease and terminal-cleanup authority.

## Design clarification record

The governing user decisions are already explicit: adversarially fix all issues
before experiments; use tmux and a free GPU; return without waiting once the
experiment is running. No user clarification is needed. The low-risk assumption
is that a new disjoint generation is preferable to modifying or reinterpreting
frozen failed authority; this is required by the prior one-way contracts.

`GEN6_FAILURE_REVIEW_SHA256: 2f79df9b3273cab6d880a525f682e70c589b926109861325a8c9367635d70928`
