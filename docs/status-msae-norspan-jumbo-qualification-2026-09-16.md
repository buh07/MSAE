# Jumbo-only NORSPAN qualification — 2026-09-16

**Historical engineering checkpoint.** The newer
[JPC integration status](status-msae-norspan-jpc-integration-2026-09-16.md)
supersedes current-code statements below: production publication adapters and
explicit no-deletion scratch wiring are now partially implemented, but strict
paired application consumers/recovery are not complete. Latest source-free matrix
is **379 passed, 6 failed** and launch remains BLOCK. References below to unchanged
rename/default-mkdtemp/recursive cleanup concern the retained predecessor.

**Whole launch: BLOCK / NOT READY.** No real source attempt, protected-content
read, payload, scoring, GPU/tmux experiment, K2/branch training, G3 or C2 opening.
This checkpoint records source-free infrastructure work, not external validation.

## Placement: remain on Jumbo

DES-0203 is retained. No `/scratch` or `/tmp` output, root relocation, mount or
administrator provisioning was performed. New synthetic subjects, before-images,
traces, run transcripts and caches are all under
`/jumbo/lisp/f004ndc/tmp/lisplab1`; tracked candidate code/reviews remain under
`/jumbo/lisp/f004ndc/experiments/wip/MSAE`.

Metadata-only observation at **2026-09-16 18:30:58 UTC**:

| Item | Observation / prospective requirement |
|---|---|
| Mount | `/jumbo/lisp`, `jumbo.thayer.dartmouth.edu:/mnt/storage/lisp`, NFS4.2, device65 |
| Client | `lisplab1`, Linux6.8.0-137-generic; `hard,proto=tcp,sec=krb5,local_lock=none` |
| Ownership/access | uid516097/gid168108; project and new synthetic base mode0700, no group/other access in observed ACLs |
| Available capacity | `df` reported 8,024,066,048 KiB filesystem-wide free; **not a reservation, quota or retention guarantee** |
| Admin capability | nonroot, effective capability mask0; no compatible child mount observed |
| Proposed canonical public controls | project `reports/provenance/msae_independent_norspan_v1`, directory0755, files0644; containing project ancestor0700 remains |
| Proposed canonical data | project `data/msae_independent_norspan_v1`, root0700; raw root0700/commit directory0555/files0444; private root and four role directories0700/files0600 |
| Proposed acquisition scratch | prospective explicit fresh child of `/jumbo/lisp/f004ndc/tmp/lisplab1`; current runner still uses unchecked default `mkdtemp` and must be changed/reviewed before launch |
| Evidence retention | retain every initiated stage/final/foreign obstruction, before-image and failed review; no automatic retries, cleanup or replacement |
| Physical durability/backup | native file/directory fsync calls succeed; server stable-storage, snapshot/backup policy, quota, disaster recovery and multi-client/reboot behavior remain **unverified** |

Exact mount/ACL/identity/capacity transcript:
`/jumbo/lisp/f004ndc/tmp/lisplab1/norspan-jumbo-placement-TCw0FK/storage-observations.txt`,
SHA256 `facf13ca3575860bde690a7c7a3cd2d87fcad803de3cb64a65645518c50ee07e`.
Prospective paths/modes above are **not production storage approval**. No real
data/provenance directory was created to obtain these observations.

### Native operation and prospective contract

The unchanged production publisher requires `renameat2(RENAME_NOREPLACE)` and
still fails on this NFS with EINVAL22. Native O_EXCL and no-replace hardlink
insertion work in retained same-client probes. [Linux rename documentation](https://man7.org/linux/man-pages/man2/rename.2.html)
requires filesystem support for the rename flag; [fsync documentation](https://man7.org/linux/man-pages/man2/fsync.2.html)
requires a containing-directory sync in addition to file sync for namespace durability.

An administrator-provisioned compatible volume **under Jumbo** remains an option;
none is available to this nonroot process. Instead of adding a failure-triggered
fallback, [reviewed plan v3](plan-msae-norspan-jumbo-qualification-v3.md) proposes a
single new contract: **Jumbo Pair Commit JPC-1**. The writer reserves deterministic
stage `.F.stage` exclusively, retains its original FD, writes/chmods/fsyncs/checks
complete expected bytes, inserts final `F` by no-replace hardlink, then performs
original-FD/pair/ancestor/durability checks. Both names persist, exactly nlink2.
There is **no stage unlink, overwrite rename or cleanup fallback**. This explicitly
replaces the old link/unlink retirement and unsupported-rename semantics, rather
than silently satisfying their single-name/nlink1 schemas.

Path substitution can expose an invalid final before postchecks reject it.
Namespace visibility, or even two matching names alone, is **not approval**.
Future consumers require the reviewed containing authority/manifest/seal and
opaque pair checks against expected receipts; stage paths never grant scoring
access. Private scorers must bind only authorized final files, never the role
directory, stage or C2 before its separate gate.

Plan versions v1/v2 and their **BLOCK** reports remain immutable. V3 received
independent **SHIP only for the prospective source-free qualification plan**.
The separate prototype does not alter production or supply whole approval.

## Synthetic investigation

Corrected diagnostic run:
`/jumbo/lisp/f004ndc/tmp/lisplab1/norspan-jumbo-diagnostics-corrected-elVXdR`.
The actual current acquisition scratch cleanup was invoked only on freshly
created fake subjects. Strace records syscall results, FD targets, identity,
directory state and environment; no real source or protected bytes are present.

| Case | Observed result |
|---|---|
| Closed writer, legacy link/unlink | 128/128 passed strict metadata check |
| Closed reader, actual scratch cleanup | 128/128 passed |
| Deliberately held writer through unlink | reproduced `publication_metadata`, nlink2 and `.nfs` entry |
| Deliberately held reader through cleanup | reproduced `ENOTEMPTY`39 with `.nfs` entry; **no cleanup retry** |

The introduced-holder controls establish plausible **mechanisms**, not the cause
of earlier unexplained failures. The [unlink documentation](https://man7.org/linux/man-pages/man2/unlink.2.html)
describes active-inode NFS silly-renaming. Historical attribution still requires
matching captured evidence; no absence-of-defect or reliability claim is made.

The new diagnostic initially had its own expected-length bug (34 versus actual35),
falsely labeling 128 closed-writer cases. Fixed to derive `len(payload)` and added
a regression. Initial script/report/trace remain at
`/jumbo/lisp/f004ndc/tmp/lisplab1/norspan-jumbo-diagnostics-ZG7QdQ`.
This new harness bug is **not** claimed to explain historical production failures.

## Qualification and remaining integration

Initial separate prototype: **53 passing tests in 2.18s on actual Jumbo**, compile
PASS. Frozen evidence:
`reports/verification/msae_norspan_jumbo_pair_prototype_bindings.json` and
`reports/verification/msae_norspan_jumbo_pair_prototype_checks.log`.
Tests include precise prelink source substitution/rejected visible foreign final,
same-inode wrong bytes, racing final/third aliases, file/directory fsync failures,
interruptions, real SIGKILL at six boundaries, eight same-client process contenders,
ancestor exchange, schema/consumer mutations, evidence and owned-FD checks.
These counts do **not** close the full production fault matrix.

Independent Q2 primitive review is a separate gate. Coordinator probes found
two candidate defects despite the green suite: untyped receipt alias fields can
redirect a custody check, and an inherited directory-close error can abandon
other retained ancestor FDs. The [independent initial review](../reports/adversarial/msae_norspan_jumbo_pair_primitive_review.md)
reproduced both and returned **BLOCK**, preserved unchanged. The original frozen
code/tests remain in `norspan-jumbo-pair-before-repair-20liw_40` on Jumbo.

Test-first repair-red observed seven failures/four passes then aborted on masked
secondary KeyboardInterrupt; it did not complete all new rows. Standalone pinned
ancestry now closes each owned FD once through constructor and finalization errors,
preserves primary failures and attaches secondary notes, and rejects nonliteral
alias strings. An intermediate 65-case suite passed, but an additional real negative
showed an unrelated active caller exception could mask close failure (two failed).
Explicit locally tracked primary exceptions repaired that defect. Final successor:
**67 passed in 1.98s on fresh actual Jumbo; compile PASS**. Logs, intermediate
module and failed roots are retained. [Linux close documentation](https://man7.org/linux/man-pages/man2/close.2.html)
explains why a released FD must not be retried; this remains a Linux-specific
qualification, not cross-platform or server-crash proof.
The [successor exact-byte independent review](../reports/adversarial/msae_norspan_jumbo_pair_successor_review.md)
returned **SHIP only for the separate Q2 primitive**: its own frozen suite passed
67 cases in1.99s and independent supplemental matrix passed54 in1.25s. Reviewed
code SHA256 `2873a1b8be1e6298ad3d923eac7e2ecd33b2470ad5e1cddc4e2cb319ae5e5deb`;
review SHA256 `20173448d327281df24486d7f66df03a9549ac32bdaee7465e90941bf6f66890`.
The supplemental rows are retained for incorporation into the maintained Q3/Q4
matrix; do not label the67 frozen tests exhaustive. No production integration,
recovery, canonical authority, whole approval or science capability is granted.

### New scratch-custody defect, not a storage-only limitation

Fresh synthetic probe `scripts/diagnose_msae_scratch_custody_v1.py` invokes only the
unchanged runner's actual scratch cleanup, with dummy original/foreign before-images
retained outside the subject. Run:
`/jumbo/lisp/f004ndc/tmp/lisplab1/norspan-jumbo-scratch-custody-NyqBll`,
report SHA256 `f0915a9839b4b5c56da6e34429e1903b970381c2c4a6417f35269676a9a63d37`.

- A newly introduced foreign extra is silently deleted and cleanup reports success.
- A synthetic file substituted between checked stat and unlink is deleted; the
  retained original remains, so final rmdir reports ENOTEMPTY39 **after foreign loss**.

This deterministically exposes a latent cleanup custody problem and another
possible ENOTEMPTY mechanism. It does **not** identify the old failure's cause.
No old or real evidence was cleaned/retried; these were new throwaway subjects with
retained before-images and syscall traces. The production runner was not modified.
The [independent scratch review](../reports/adversarial/msae_norspan_jumbo_scratch_custody_review.md)
reproduced both defects and retains **BLOCK for production cleanup**, report
SHA256 `0962ba96e885cbff2ca5350acc9be24a522e92c1a24868d9b17e73c566f46c89`.
Four separate diagnostic-harness checks passed; two intentionally assert the
unchanged production's destructive counterexamples, not repaired safety.
Future Q3 must prospectively review preserving initiated scratch instead of deleting
ambiguous/partial/foreign contents, with exact schemas, bounded storage/quota,
retention, recovery and authority changes. No unchecked cleanup algorithm or
`cleanup_verified=True` bypass is approved. Whole launch remains BLOCK.

Prospective [JPC integration/scratch-retention plan v1](plan-msae-norspan-jpc-integration-v1.md)
passes check-plan and received independent **plan-only SHIP** in its
[new separate review](../reports/adversarial/msae_norspan_jpc_integration_plan_review.md).
Plan SHA256 `248d015a0600749b4a57eb18cc439417333a40711c809cd843da4e7b4198de2a`;
review SHA256 `fff22cd8d4773efd77ce0661c71665deb22d1b30b4766d3bd114184754409a5f`.
It declares the full boundary/fault groups before implementation, explicit new
schema/authority/ledger bindings, owned-FD retention through aggregate publication,
Jumbo scratch reservation/retention and separate recovery. No P1/P2 production
changes have been made; plan approval cannot substitute for exact Q4 whole approval.
The review specifically requires durable **pre-start** scratch path/dev/inode/
lineage binding (not terminal metadata alone), a non-circular self-control receipt
trust root, actual enforced quotas/storage facts and evidence for every fault row.
P1–P7 remain unimplemented; Q2 primitive SHIP only permits this ordered source-free
work. No full storage, acquisition or launch approval has been obtained.

Static production integration audit has **80 rows**:
`reports/verification/msae_norspan_jumbo_pair_integration_audit.json`.
Every row still needs classification, implementation and regression evidence:

| Area / current functions | Required Q3 work |
|---|---|
| `_publish_owned_file`, `_validate_publication`, single/flat/private publishers | replace only explicit protocol artifacts; retain owned writers through **aggregate** complete boundary; exact two-name cardinality after final durability; no unlink |
| `protocol_inventory`, `classify_protocol_state` | enumerate all physical names, finite paired logical names; partial/mismatched/extra aliases unresolved; four raw/four private **objects**, eight prescribed names each |
| `canonical_control`, `control_record`, `control_manifest` | paired protocol-control checks; ordinary config/code/reviews remain nlink1; strict canonical schema and lineage unchanged |
| Authority construction/replay and config | new exact amendment/whole-review bindings, no broad alias exemptions; original primary BLOCK report preserved and no longer silently treated as authority |
| `validate_history_registry`, phase additions | enumerate only exact prospective pair additions; ordinary accessible history/reviews remain checked; scientific pedigree/overlap predicates unchanged |
| Acquisition/raw metadata and loader | explicit paired receipt schema, observed original identities/bytes; sparse checkout remains nlink1; strict logical inventory and access counters |
| Private writer/verifier and future containment | expected pair receipts; four distinct role objects; no stage semantic consumption; only authorized final-file binds |
| Acquisition placement/cleanup | explicit validated Jumbo scratch root before initiated work; close/reap before removal; unexplained/hard faults preserve evidence and remain stopped |
| Recovery | implement separately reviewed explicit zero-source-work entrypoint: incomplete unresolved; valid pre-start current fsync/recheck may permit **first** access; any started incomplete state prohibits repeat; terminal only current custody reconstruction, never payload/scoring restart |

Q4 must exercise every entry/ready/started boundary, first subprocess/raw access,
write/link/fsync/terminal publication, interruptions, substitutions, extra objects
and relevant combined faults, including descriptor and owned-child failures.
Each row needs observed evidence, not a test-count substitute. Independent exact
whole-implementation approval and canonical authority binding follow; the earlier
bounded compatible-local SHIP and new plan/prototype verdicts cannot replace them.

## Scientific sequence stays gated

1. Q4 whole approval and explicit authority, then freeze accessible history and
   acquire the pinned candidate once. Identity/license/pedigree/history/roles/
   cross-role/task-label support eligibility remains UNKNOWN.
2. Only eligible source can construct/seal replacement four-role payload and
   receive independent readiness SHIP.
3. Separately implement/freeze/contain/review scorer, representations, metrics,
   inference and decision rules; C2 inaccessible. Calibration then C1 once.
4. Exactly one justified G3 branch, or equivocal no-decision with no training/final
   authorization. Freeze case precedence/M5 and applicable M6.
5. Conditional learned engineering ->25M ->100M ->1B gates, or M7 signed N/A.
6. Frozen representations/configs/claims then C2 once; branch-specific complete
   functional/causal/sham/stability/robustness/statistical/case evaluation.
7. Decision/claims/manuscript/audits/reproducibility freeze before later-paper training.

V10 remains terminal. AMALGUM v3 is exposed-source calibration, not independent
confirmation. Source failure is not scientific confirmation or branch authority.
No honest wall-clock ETA for gated science/training is available yet: source
eligibility, branch choice and measured runtime are unknown. Authorized future jobs
will use tmux and then-permitted `nvidia-smi`, with ETA and early progress checks.

## Consolidated engineering checkpoint

An immutable, explicitly PUBLIC/source-free snapshot and exact hash manifest are
kept on Jumbo. Resolve archive/path/SHA through
`reports/verification/msae_norspan_jumbo_checkpoint_v2_binding.json`; the earlier
v1 snapshot remains retained. It includes exact qualified code/tests/reviews,
original production before-image bindings, plans, status and independent fault
test code. Native diagnostic JSON/trace files remain at their retained evidence
roots; controlled summaries are packaged. No real source/private data is included.
This is a reproducible **engineering checkpoint**, not the final release artifact
or whole-implementation/storage/authority approval. Current changes remain
uncommitted; no new commit or push occurred.
