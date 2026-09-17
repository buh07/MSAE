# NORSPAN-1 Jumbo JPC integration — 2026-09-16

> Newest source-free follow-up: [no-admin client contract/status](status-msae-norspan-jumbo-client-contract-2026-09-16.md).
> This document below is retained predecessor evidence; administrator contact is now forbidden.

**Whole launch: BLOCK / NOT READY.** This is an uncommitted, source-free engineering
candidate, not an independent scientific result or acquisition authorization.
Everything newly produced remains on Jumbo. No real census/history/authority,
acquisition, raw/private access, payload, model/GPU/tmux experiment, scoring, K2,
branch training, G3 or C2 operation was started.

This supersedes the **current implementation status** in the earlier
[Jumbo qualification checkpoint](status-msae-norspan-jumbo-qualification-2026-09-16.md),
not its retained measurements, failed reviews or before-images.

## Implemented, with bounded qualification only

- Extended the JPC primitive with retained `OwnedPair` writers/readers, exact
  external receipt schemas, bounded original-FD reads, all-once Linux descriptor
  cleanup and a narrow same-inode immediate-parent 0700→0555 transition. Both
  stage and final remain permanently, exact nlink2; no rename/unlink fallback.
  [Independent owned-handle review](../reports/adversarial/msae_norspan_jpc_owned_handle_review.md)
  returned **bounded SHIP** (92 maintained and 81 supplemental passing cases).
  This is not approval of aggregate publication or the whole application.
- Added a separately named
  `configs/msae_independent_norspan_v1/jpc_publication_retention_v1.json` and
  [prospective amendment](amendment-msae-norspan-jpc-publication-retention-v1.md).
  The original `protocol.json` bytes remain unchanged. Runtime checks freeze
  exact original/new config hashes and literal equality of all 16 scientific
  fields. DES-0230 records a **proposed**, not production-approved, choice;
  DES-0203/0221 remain in force.
- Added aggregate flat/four-role publishers and external-receipt opaque consumers
  in `scripts/msae_norspan_jpc_runtime.py`. Actual builder single/public, raw and
  private publication adapters use these interfaces. Earlier aggregate late-digest
  counterexamples now have passing named regressions; aggregate coverage is still
  bounded, not the complete production matrix.
- Removed the runner's default `mkdtemp` placement and recursive initiated-scratch
  deletion. The obsolete cleanup interface now refuses every call. New runner
  wiring reserves an explicit Jumbo scratch lease before entry/start publication,
  binds path/device/inode/mode/authority/entry lineage in JPC phase records, and
  retains scratch on success and failure. It does **not** fake cleanup success.
  Written ordering is covered structurally; actual paired-control fake-Git
  end-to-end success/rejection/restart qualification remains unfinished.
- Added explicit opaque recovery foundation: externally expected catalog and
  lineage, current pair custody/fsync only, no inferred historical success, no
  source-work authorization and no repeat of started source access. This is not
  a complete P5 recovery command integrated with the scientific control chain.
- Every builder command (`build-history`, `build-authority`, `prepare`, `verify`)
  and acquisition `acquire()` calls an **unconditional** qualification BLOCK
  before real state or evidence access. Report filenames/SHIP headers cannot
  remove this guard.
- Builder parent-constructor/finalization faults now close every owned descriptor
  once and preserve a primary error. Historical destructive-cleanup reproductions
  target a verbatim frozen **test-only legacy fixture**; current cleanup refusal
  is separately tested. Earlier BLOCK evidence has not been replaced or erased.

## Latest results: six maintained failures, not acceptance

The explicit 11 source-free suites returned **379 passed, 6 failed in 16.11s**
(exit 1) on fresh Jumbo subjects. Named transcript and JUnit:

`/jumbo/lisp/f004ndc/tmp/lisplab1/norspan-jpc-current-matrix-IhcwJg/{checks.log,tests.xml}`

Pointer: `reports/verification/msae_norspan_jpc_current_matrix_path.txt`.
An independent fresh rerun returned **379 passed, 6 failed in 17.80s**, exit 1,
under `msae-jpc-whole-independent-JivbAVAj` on the same Jumbo synthetic base.
These are engineering tests, not model evaluations or independent-source evidence.

All six failures are in `tests/test_msae_norspan_jpc_second_pass_matrix.py`:

1. Foreign content added to the previously checked `home` during the second final
   inventory walk is missed, both with and without durability checks.
2. An earlier repository file grown beyond the frozen per-file budget during that
   walk is missed, both with and without durability checks.
3. Combined late budget mutation plus multiple close-after-release faults leaves
   an OSError or KeyboardInterrupt as primary instead of detecting/preserving the
   required scratch validation failure (two cases).

The [initial runtime BLOCK](../reports/adversarial/msae_norspan_jpc_runtime_review.md)
exposed seven late aggregate/scratch counterexamples after a passing maintained
suite. Its bytes and failed subjects remain intact. Repairs closed those seven
named cases, but the
[successor runtime review](../reports/adversarial/msae_norspan_jpc_runtime_successor_review.md)
retains **BLOCK**: an added inventory walk merely moved the scratch race.
**Do not add another walk, relax the assertions, erase evidence or reinterpret
these in-call mutations as a successful snapshot.** A genuinely different custody/
consistency solution requires prospective review and named qualification.

The known suite is 385 cases total; it does not close the declared full fault
matrix. Original 222-case compatible-local results and predecessor scoped SHIPs
are historical evidence, not passing qualification of this changed candidate.
The [exact whole-candidate independent review](../reports/adversarial/msae_norspan_jpc_whole_candidate_review.md)
returned **BLOCK**, with eight required closure findings. Report SHA256:
`f31166d80f77751af828df6a18bc62ea71cba1e1fd36a4d949156267d939ffac`.
Its 29 designated public code/config/test/plan/amendment/request/review subjects
were unchanged before/after the run and report persistence. This ordinary retained
BLOCK is **not** the future canonical whole-implementation approval; no canonical
whole SHIP or storage approval has been obtained.

## Still open in production integration

| Area | Current disposition |
|---|---|
| P1 authority amendment | New config/projection and proposed ledger entry written; finite current test/review/control inventory and approved trust root still incomplete |
| P2 owned publishers/consumers | Primitive bounded SHIP and actual publication adapters; aggregate qualification is bounded, not whole acceptance |
| P3 paired protocol | Predecessor state/control/raw/private readers still expect nlink1, single-name cardinality and old schemas; canonical outside-receipt/control trust graph and exact history/authority integration are not wired |
| P4 scratch/supervisor | Explicit reservation/binding and no-deletion wiring written; six late scanner failures and actual end-to-end qualification remain open; interval monitoring is not a hard quota |
| P5 recovery | Zero-source-work opaque foundation only; four actual application restart cases, complete schema/lineage replay and separately reviewed terminal-raw exception remain open |
| P6 full fault matrix | Named primitive/aggregate/opaque/guard tests retained; actual phase-marker/subprocess/raw/readiness/terminal/history combined matrix not closed |
| P7 authority/storage | Whole candidate remains BLOCK; no administrator facts, approved storage review, whole SHIP or canonical authority binding |

The whole-candidate reviewer also identifies latent predecessor defects behind the
guard: supervisor `finally` close/wait errors can mask a primary and skip later
owned releases; some ordinary/raw readers similarly abandon parent cleanup after
file-close failure; sparse-file open lacks nonblocking protection before rejecting
a substituted FIFO. These are static findings requiring test-first fixes and
independent qualification, not newly exercised scientific outcomes.

## Storage/admin facts are not available

DES-0203 keeps canonical storage on Jumbo. Existing observations still concern
`jumbo.thayer.dartmouth.edu:/mnt/storage/lisp`, NFS4.2/device65 on `lisplab1`.
Native rename-no-replace returns EINVAL22; same-client exclusive-create/hardlink/
file-and-directory fsync probes passed. The changed candidate uses the explicitly
named JPC pair contract, not a runtime fallback to unsupported rename semantics.
Neither these calls nor `/tmp` results establish server persistence or recovery.

The config's prospective canonical scratch base is
`/jumbo/lisp/f004ndc/experiments/wip/MSAE/acquisition_scratch/norspan-1`;
it was **not provisioned or used**. Synthetic subjects remain under
`/jumbo/lisp/f004ndc/tmp/lisplab1`. Per-file 8GiB, total 64GiB and 65,536-entry
checks are monitors, not administrative hard quotas/reservations.

[Administrator request](storage-msae-jumbo-administrator-request.md) is prepared
but **not submitted, answered or approved**. Need exact canonical destinations,
filesystem identities/ACLs, capacity/quota/reservation, retention, stable-storage/
directory durability, recovery/backup and required multi-client/reboot facts. No
administrator identity/contact or authorized submission channel is available.
The [prepared JPC follow-up](storage-msae-jumbo-jpc-followup-request.md) asks about
the explicit scratch base, enforceable limits and any actual Jumbo snapshot/writer
quiescence facilities without assuming their availability or approval.

Historical NFS attribution remains **unproven**. Introduced open-holder synthetic
controls reproduce `publication_metadata`/ENOTEMPTY mechanisms; the harness's own
length bug and the separately proven legacy destructive-cleanup defect do not
establish the cause of earlier uninstrumented failures.

## Required next order

1. Prospectively review a real solution to late scratch consistency; fix/test the
   retained counterexamples and bounded-read/primary-preservation cleanup defects.
2. Complete strict paired state/schema/readers, finite ordinary-history/authority
   and trusted outside receipt binding; actual no-retry application recovery.
3. Close every applicable declared fault row with named evidence. Obtain actual
   administrator facts and independently approved Jumbo placement/limits/recovery.
4. Obtain exact whole-implementation SHIP and approved canonical authority binding.
   Only that reviewed successor may replace the unconditional guard; preserve
   every earlier BLOCK as ordinary accessible history.
5. Freeze accessible history/authority; acquire the pinned NORSPAN candidate once;
   check repository/license/pedigree, full history overlap, deterministic group-role
   separation and task/label support. Eligibility remains **UNKNOWN**.
6. Only after all eligibility gates, construct/seal four replacement roles and
   controls and obtain independent readiness approval. Freeze, contain and review
   calibration/C1 scoring while keeping C2 inaccessible.
7. Run permitted calibration and C1 once; a justified decision may sign exactly
   one G3 branch and case-study precedence. Equivocal means no-decision, not a
   negative result or training permission.
8. Applicable M5/M6; learned branch only: engineering→25M→100M→1B sequential gates.
   Otherwise M7 not applicable. Then freeze representations/configs/claims, open C2
   once, complete branch-specific functional/causal/stability/case-study evaluation,
   and freeze final decision/claims/manuscript/audits/reproducibility before later
   paper training.

V10 stays terminal; AMALGUM v3 is exposed-source calibration only. K2 and branch
training remain prohibited. No scientific completion ETA can be justified before
software/storage qualification and source eligibility.

## Reproducibility and handoff

All changes remain uncommitted; main HEAD is `75653a7`. No automatic commit/push.
The maintained and independent failed roots, legacy original/foreign before-images,
earlier plans/reviews and original scientific config are retained. New binding,
fault-progress and checkpoint records live in `reports/verification/` with explicit
source-free scope; they do not constitute canonical science authority.

- `msae_norspan_jpc_fault_matrix_progress.json`: nine declared boundary groups,
  named bounded test/transcript evidence, every whole row explicitly **open**.
- `msae_norspan_jpc_integration_audit_progress.json`: all 80 original audit rows
  classified against the bound before-image, remaining requirements explicit.
  Original line numbers are not claimed to match moved current code.

Next command (read-only public engineering state):

```sh
cd /jumbo/lisp/f004ndc/experiments/wip/MSAE
cat docs/status-msae-norspan-jpc-integration-2026-09-16.md \
  reports/adversarial/msae_norspan_jpc_runtime_successor_review.md
```
