# PLAN — NORSPAN-1 Jumbo Pair Commit qualification v2

Date: 2026-09-16. Status: prospective DRAFT; no real source/data operation permitted.
Supersedes proposed JNC-1 direct-visible semantics only; preserves v1 and its BLOCK.

## Goal
Keep this experiment and all new artifacts on Jumbo. Qualify **Jumbo Pair Commit
JPC-1** with source-free native NFS tests and independent whole-implementation review,
then progress through source, payload, prescore and branch gates only if approved.

## Non-goals and constraints
- DES-0203 / owner: all new experiment/synthetic/evidence artifacts under Jumbo;
  no /scratch or /tmp output, silent root relocation, mounts or admin changes.
- Before source-free qualification and authority SHIP: no real census/provenance/
  acquisition/preparation/source network/model/tokenizer/GPU/tmux/scoring/training/
  K2/branch/final opening. Each later step has its own exact-hash signed gate.
- Never open/hash/print Atlas private finals or V8/V9/V10 raw/source/private bytes.
- Preserve original plan/reviews/logs and before-images. TODO/V10 reference and all
  source/role/support/overlap/scientific branch predicates remain byte-exact.
- Prior 222 local passes and scoped SHIP are not whole-implementation approval.
  V10 terminal; AMALGUM v3 exposed calibration only. Operational IO is not science.

## Design-bank clarification and approach
DES-0203 requires Jumbo. No approved NORSPAN storage alternative exists in the
ledger. Actual NFS4.2 mount rejects rename_noreplace EINVAL22; native exclusive
creation and fsync succeeded, 8 same-client contenders had one winner. No child
compatible mount observed and CapEff0; do not assert an administrator volume exists.
Propose a prospective publication amendment, **JPC-1**, instead of an unsafe runtime
fallback or pretending direct-visible partial files are atomically published.

Each logical final F has exactly one deterministic same-directory stage S named
'.' + F + '.stage'. Create S via O_RDWR|O_CREAT|O_EXCL|O_NOFOLLOW, mode0600 initially;
retain original writer and full named ancestor chain; write complete bytes, fchmod
required mode, fsync writer and parent, and opaque-verify actual SHA/size/fingerprints.
Only then use no-replace hard-link S→F (os.link follow_symlinks=False). There is NO
unlink, overwrite rename, retirement cleanup or fallback. Both names persist.
A terminal pair is regular, exact required mode/size, same dev+inode as retained
original, actual expected bytes, **exact nlink2**, and exactly the two prescribed
names. Initial stage has nlink1. Third links, mismatching aliases, stages without
finals or finals without stages fail. This is an explicit prospective change from
nlink1 single names to exact two-name custody, NOT accepting arbitrary hardlinks or
ignoring the predicate. Final-link creation is the atomic complete-byte visibility
point; durability requires file fsync before link and parent fsync after link.
Revalidate both names/digests/ancestor/cardinality after durability and at complete
publisher return; preserve all objects and reject on any failure.

Consumers never use staging paths. Public control consumers validate exact canonical
schemas, all lineage, paired custody and authority state before progressing. Final
control already visible before the final parent-fsync may be observed only as the
existing atomically published object; no network/raw action happens until its
producer returned from durability validation in that invocation. After restart,
fully reconstructed pre-start entry/ready may resume and must fsync validated
predecessor pairs/directories before proceeding. Any started marker (even partial
or unresolved) forbids repeating network/raw. Complete terminal reconstruction
requires the containing acquisition/scientific seal and all paired artifacts; it
must durably validate all pairs before returning success. This preserves existing
fail-stop restart rules, and does not claim to prove previous fsync calls from
canonical bytes. A failed parent fsync keeps unresolved evidence until an explicit
prospectively reviewed zero-work terminal revalidation, never automatic retry of
source operations. Private/raw consumer access remains forbidden before the exact
complete acquisition/role seal, apart from producer-owned opaque checks needed to
build that seal and the separately documented terminal custody verifier.

Private stage/final pair stays within its isolated role directory, mode0600; root
and role dirs0700. Contained scorers bind only the one final file for authorized
roles: never role directory, stage parent, repository or C2/stage. Four physical
objects each have two names, no cross-role shared inode. Public inventory enumerates
all physical names; exact deterministic valid pairs become logical controls/files.
No broad stage-directory, history, alias or candidate-pedigree exemption is allowed.
Source-free authority amendments explicitly enumerate new path/hash members and
pair names; new canonical full-review member supersedes only the old authority
member prospectively, while old BLOCK bytes remain normal accessible history.

Alternatives: administrator-provided compatible Jumbo volume (valid later option,
not user-provisionable now); old link/unlink retirement (unsafe foreign deletion);
direct O_EXCL final (partial visibility/commit concerns); overwrite rename or relaxed
metadata (rejected). JPC-1 is a single frozen protocol, never a failure-triggered
fallback. If reviewers reject exact pair custody/authority/restart semantics, stop.

## Milestones
- [ ] Q0: freeze v2, before-images and design/review evidence; independent plan SHIP.
  Acceptance: structural check-plan PASS, exact hash review, no production access.
- [ ] Q1: fresh Jumbo synthetic diagnostic harness with operation/errno/stat/FD/
  directory listings, environment and optional syscall trace. Reproduce legacy
  publication_metadata and scratch ENOTEMPTY or report non-reproduction honestly;
  isolate held-open-link/cleanup behavior without asserting historical root cause.
  Acceptance: retained evidence, no cleanup of old subjects or false reliability claim.
- [ ] Q2: test-first JPC primitive/publishers, initially separate source-free prototype;
  exclusive stage create, full prelink checks, atomic no-replace link, permanent exact
  pair, postlink durability and retained-FD/cardinality checks. Acceptance: wrong-byte,
  substituted stage, racing final, extra aliases, unlink/rename-forbidden, short-write,
  chmod/write/file+directory fsync/interrupt/ancestor attacks reject/preserve/close.
- [ ] Q3: only after primitive review integrate via a new exact publication config/
  amendment binding, unchanged science. Audit every single-name/nlink1 assertion
  and schema, state inventory/history/authority/raw/private reader/verifier. Keep
  sparse checkout and normal public source/review metadata nlink1 unchanged.
  Acceptance: explicit physical pairs, no generic alias/history exclusion, no staging
  access in prospective scorer, strict actual synthetic success/rejection/restarts.
- [ ] Q4: full synthetic suite on project NFS plus declared fault coverage across
  every entry/ready/started/first subprocess/raw/temp-write/link/fsync/terminal state,
  relevant combined faults and descriptor/process cleanup. Independent exact-byte
  whole-implementation review and canonical authority binding. Acceptance: no false
  terminal success, no evidence deletion or initiated repeat access, all rows covered
  or explicit BLOCK. Single-client tests never certify multi-host/server reboot.
- [ ] Q5: consolidate reproducible reviewed checkpoint; real accessible-history/
  authority only after Q4 SHIP; independent authority review; pinned source acquired
  once. Frozen identity/license/pedigree/history/pruning/roles/cross-role/support gates.
  First failure retained, no adaptive scientific amendment after source exposure.
- [ ] Q6: only eligible source seals blind payload; readiness SHIP; separately freeze,
  contain and prescore-review calibration/C1. C1 once; verify inference; exactly one
  G3 branch or equivocal. Freeze case precedence/M5 and applicable M6. C2 closed.
- [ ] Q7: learned engineering→25M→100M→1B promotion gates or M7 signed N/A; freeze
  representations/configs/claims, M8 C2 once; branch-specific final/statistical/case
  evaluation and reproducibility/manuscript freeze before later-paper training.
  Authorized jobs in tmux, free GPUs only after nvidia-smi authorization, early ETA/
  progress checks without waiting for long jobs. No jobs start on implicit authority.

## Definition of done
- [ ] JPC-1 plan and exact source-free implementation independently approved for Jumbo.
- [ ] Physical pair/cardinality/custody and all strict consumers/restarts exercised.
- [ ] Every declared fault row has retained evidence, or whole launch remains BLOCK.
- [ ] Earlier NFS anomalies diagnosed with evidence or accurately scoped unresolved.
- [ ] Source acquisition, payload and scoring only after separate authority/readiness/
  prescore SHIP; no repeat initiated access, overwrite, evidence deletion or false success.
- [ ] Scientific completion only after Q5-Q7 pass; terminal source failure does not
  satisfy independent confirmation. User request cannot guarantee a qualifying branch.
- [ ] Reproducible consolidated checkpoint, preserved reviews/logs and honest synthesis.
  No automatic commit/push in this task absent an explicit new commit/push request.

## Verification plan
- [ ] check-plan on this exact v2 and active task PLAN; SHA/mode preservation checks.
- [ ] py_compile with PYTHONPYCACHEPREFIX in a fresh Jumbo synthetic run root.
- [ ] PYTHONDONTWRITEBYTECODE=1 pytest -p no:cacheprovider with fresh Jumbo TMPDIR and
  basetemp; prototype, integrated full suite and public-only predecessor subset,
  explicitly deselect protected historical-identity cases instead of faking them.
- [ ] Synthetic strace/errno/FD/metadata records; no source bytes/credentials/network.
- [ ] Fault coverage table maps each declared boundary/attack to test and observed result.
- [ ] git diff --check, frozen review bindings and preserved earlier BLOCK/log hashes.

## Risks / one-way doors
Custody/state/config changes are material and require independent approval before
integration/real selection. Old controls remain immutable; no real source attempt has
started. Actual durable start markers, acquisition, payload and final are create-once.
No hard-crash/server-reboot or multi-client qualification is invented; unavailable
required evidence remains a blocker. No initiated attempt or retained evidence erased.

## Next command
Read and independently review this exact plan; no implementation before scoped SHIP.
