# PLAN — NORSPAN-1 Jumbo Pair Commit qualification v3

Date: 2026-09-16. Status: prospective DRAFT; no real source/data operation permitted.
Supersedes proposed JNC-1 direct-visible semantics only; preserves v1/v2 and both BLOCK reviews.

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
fallback or pretending direct-visible partial files are committed by mere namespace visibility.

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
ignoring the predicate. Final-link creation is ONLY atomic no-replace namespace insertion. The nominal
stage is complete/fsynced before insertion, but path-based stage substitution can
expose a foreign/partial final before postlink checks reject it. A visible final
or even structurally paired names are NOT custody/consumption approval. Successful
postlink retained-original-FD byte/identity validation and applicable containing
control/manifest/seal approval are mandatory. Durability additionally requires
file fsync before link and parent fsync after link.
Revalidate both names/digests/ancestor/cardinality after durability and at complete
publisher return; preserve all objects and reject on any failure.

Consumers never use staging paths. Public control consumers validate complete
strict canonical schemas, expected predecessor hashes, exact pair custody, and
applicable authority/containing state before progressing. Raw consumer requires
complete acquisition; role/scoring consumer requires the complete scientific seal,
readiness and its signed capability. A substituted/partial visible final/pair is
rejected before source or model access. Producer checks before exposing later
containing controls ensure its own failed postlink validation cannot authorize use.
This is not a proof against arbitrary same-UID reconstruction of all controls.

Recovery is explicitly a prospective authorization of this plan and must be
implemented and reviewed, not inferred from prior successful fsync calls:
1. Incomplete/mismatched pair or malformed canonical control: unresolved, no source
   work, no overwriting/recreating any existing stage/final. Preserve all evidence.
2. Complete fully reconstructed PRE-START entry/ready pairs after kill OR durability
   error: approved zero-source-work recovery may revalidate exact bytes/identities/
   lineage and fsync each retained file and containing directory, then revalidate
   again. Only current successful durability/custody validation permits first
   network/raw operation, and its create-once started marker must itself complete
   successfully first. No claim about earlier durability calls is made.
3. Any started marker without fully reconstructed complete terminal: unresolved,
   zero repeated network/raw operations, regardless of pair completeness or error.
4. Fully reconstructed COMPLETE terminal: approved zero-source-work recovery may
   perform only schema/lineage/opaque custody and current file/directory durability
   revalidation; success asserts current validated terminal custody, not prior
   invocation success or inferred historical fsync. It cannot reacquire source,
   repeat scientific raw access, rebuild payloads or authorize scoring/training.
   Existing explicitly declared terminal raw reconstruction remains a separate
   reviewed exception, never private semantic consumption or a new raw attempt.
The original invocation always propagates its error. No automatic recovery in the
same failed invocation. Only the fresh explicit zero-source-work recovery path,
reviewed under Q3/Q4, may apply cases2/4; every other failure stays stopped.
Producer-owned opaque checks used to construct a containing manifest/seal are not
consumer scoring access. Each producer, terminal custody checker and scoring open
has its own declared counter; none are silently relabeled or omitted.

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
- [ ] Q0: freeze v3, before-images and design/review evidence; independent plan SHIP.
  Acceptance: structural check-plan PASS, exact hash review, no production access.
- [ ] Q1: fresh Jumbo synthetic diagnostic harness with operation/errno/stat/FD/
  directory listings, environment and optional syscall trace. Reproduce legacy
  publication_metadata and scratch ENOTEMPTY or report non-reproduction honestly;
  isolate held-open-link/cleanup behavior without asserting historical root cause.
  Acceptance: retained evidence, no cleanup of old subjects or false reliability claim.
- [ ] Q2: test-first JPC primitive/publishers, initially separate source-free prototype;
  exclusive stage create, full prelink checks, atomic no-replace link, permanent exact
  pair, postlink durability and retained-FD/cardinality checks. Acceptance: wrong-byte,
  precise prelink substituted stage and rejected-visible-final consumption, racing final, extra aliases, unlink/rename-forbidden, short-write,
  chmod/write/file+directory fsync/interrupt/ancestor attacks reject/preserve/close.
- [ ] Q3: only after primitive review integrate via a new exact publication config/
  amendment binding, unchanged science. Audit every single-name/nlink1 assertion
  and schema, state inventory/history/authority/raw/private reader/verifier. Keep
  sparse checkout and normal public source/review metadata nlink1 unchanged.
  Acceptance: explicit physical pairs, no generic alias/history exclusion, no staging
  access in prospective scorer, explicit case1-4 durability-error/kill recovery,
  strict actual synthetic success/rejection/restarts and no false consumption.
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
- [ ] check-plan on this exact v3 and active task PLAN; SHA/mode preservation checks.
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
