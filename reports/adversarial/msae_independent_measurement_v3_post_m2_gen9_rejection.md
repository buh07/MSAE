# Gen9 control-plane implementation rejection

Date: 2026-09-14  
Decision: **REJECT the current gen9 implementation; do not publish, contain, probe, set up M3/M4, sign, or launch it.**

## Scope and authority

This decision applies to the seven-file gen9 candidate governed by
`docs/plan-msae-independent-measurement-v3-post-m9-gen9.md` (SHA-256
`135f313fdad7299a69b8b04268f4168e168a1be30ba5e80d408e43b7f5690a30`) and its
registered plan review (SHA-256
`9398a0356c8f5e8d1cf11cbcdeca4b01dc7f68c2fb04a4d61194a780ef47491e`).
The plan requires every safe predecessor/gen9 check to pass before the
create-once changed-region publication. That prerequisite is not met.

The exact safe-check matrix was run with the closed environment and argv encoded
by `_pre_capability_check_rows`, excluding the sole registered real-tmux node.
The complete transcript is retained at
`reports/verification/msae_gen9_safe_checks_20260914.log` with SHA-256
`ce26f149a75fee060eff7f92780c3ce0575e8e41a79d8b0da7b6136c4b1c148b`.

## Test results

| Check | Result |
|---|---:|
| predecessor v1 | 5 passed |
| predecessor v2 | 47 passed |
| predecessor v3 | 102 passed |
| predecessor post-M1 | 26 passed |
| predecessor post-M2 runtime | **1 failed, 70 passed, 1 deselected** |
| remediation v1 | 50 passed |
| predecessor gen4 | **4 failed, 123 passed, 1 deselected** |
| gen9 CPU | **24 failed, 161 passed, 1 deselected** |
| gen9 publisher unit nodes | 2 passed |

The predecessor failures are not cosmetic: the frozen M2/quarantine projection
rejects current filesystem identity (`device` drift), and the historical
preflight private-key lstat identity also drifts. Gen9 therefore cannot prove
the predecessor authority on which its M3/M4 path depends.

## Independent reasons for rejection

1. **The gen9 authority test is internally stale.**
   `tests/test_msae_independent_measurement_v3_post_m9_gen9.py:50-54` expects the
   failed-gen8 plan/review hashes, not the registered gen9 plan/review hashes.
2. **Changed-region construction rejects the candidate.**
   `_gen9_changed_region_rows` correctly rejects unregistered top-level changes
   at `scripts/msae_independent_measurement_v3_post_m2_gen9_runtime.py:4463-4467`;
   the current candidate changes `_failed_gen7_entries` outside its allowlist.
   Consequently the required manifest cannot be constructed or published.
3. **The gen9 reconstruction misbinds the failed-gen7 review.**
   All ten actual frozen gen7 files still match their recorded digests, but the
   candidate aliases `FAILED_GEN7_FAILURE_REVIEW` to the gen8 failure-review
   path while expecting the gen7 digest
   (`scripts/msae_independent_measurement_v3_post_m2_gen9_runtime.py:184,240-245`).
   `_failed_gen7_entries()` therefore raises `immutable failed-gen7 subject
   drift`; this is a gen9 path-binding defect, not historical-byte drift.
4. **Static closure does not close.**
   The gen9 CPU matrix rejects unreviewed dynamic file sites (beginning with
   `_source_only_bytes` in the controller), plus related file/network/import and
   caller-value-flow closure tests.
5. **The real containment route is inconsistent before execution.**
   The descriptor points at nonexistent pytest node
   `test_gen9_registered_real_tmux_containment`
   (`scripts/msae_independent_measurement_v3_post_m2_gen9_runtime.py:5340-5344`),
   while the registered supervisor points at
   `test_failed_handoff_extinction_kills_real_processes_and_socket`
   (`scripts/run_msae_independent_measurement_v3_post_m2_gen9_tmux_test.py:463-465`).
6. **A gen7 socket namespace remains in gen9.**
   `_promote_tmux_socket_mode` accepts `m7[tx]_...` rather than gen9 paths at
   `scripts/msae_independent_measurement_v3_post_m2_gen9_runtime.py:19065-19074`;
   its gen9 regression fails.
7. **Required publication/recovery bindings are absent.**
   The allowed-change policy names `_pre_containment_review_binding`,
   `_recover_interrupted_containment`, and `_publish_containment_report`, but no
   definition exists in the candidate. This is inconsistent with the plan's
   durable containment-report contract.

## One-way gate disposition

Because the safe gate failed, no attempt was made to create or use:

- `reports/analysis/msae_independent_measurement_v3_post_m2_gen9/changed_regions.json`;
- the pre-containment review;
- the real-tmux containment report;
- the pre-capability review or capability report;
- the implementation review;
- gen9 M3/M4 setup, authorization, signature, or launcher invocation.

This is a terminal rejection of the **current** gen9 candidate, not evidence that
the calibration result failed and not permission to bypass the gate. Any
successor must receive a new name/namespace and a newly frozen, independently
reviewed contract; it must not mutate or resume gen9.

## Consequence for exposed-source calibration

No v3 model scoring was launched. The requested v3 run remains explicitly an
**exposed-source calibration**, never an independent replication or confirmation,
but the rejected control plane means its frozen launch sequence cannot be used.
No K2 or branch training was started.
