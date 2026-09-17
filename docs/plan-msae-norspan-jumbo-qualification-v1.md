# PLAN — NORSPAN-1 Jumbo qualification / JNC-1 prospective publication

Date: 2026-09-16. Status: DRAFT, requires independent plan SHIP before implementation.

## Goal
Keep every new experiment, synthetic scratch, evidence and canonical artifact on
Jumbo; qualify a no-overwrite, evidence-preserving publication protocol and whole
implementation before a single real acquisition. Complete science only if all
subsequent source/readiness/prescore/branch gates pass. No promise that a source or
G3 branch will qualify.

## Constraints and current facts
- DES-0203 and owner: canonical repository/artifacts stay under /jumbo/lisp/f004ndc.
  No /scratch, /tmp experiment output, hidden relocation, mount or administrator change.
- Project is NFS4.2; actual renameat2(RENAME_NOREPLACE) returns EINVAL 22. Existing
  frozen builder remains fail-closed; 222 passing local tests are not NFS approval.
- No real protocol census/publication/acquisition/source bytes/model/tokenizer/GPU/
  tmux/scoring/training/final access during source-free qualification.
- Never open/hash/print Atlas final.jsonl/final.records.jsonl/final.units.jsonl or
  V8/V9/V10 raw/source/private bytes. No initiated attempt cleanup or retry.
- Preserve old plan, reviews, logs, before-images and BLOCK dispositions byte-exact.
  Do not edit TODO.md or V10 reference, source/roles/support/overlap/branch predicates.
- Source and final-gate operations require their own exact-hash authority/readiness/
  prescore/M5-M8 review. User request is not permission to bypass those conditions.

## Design-bank clarification and alternatives
DES-0203 keeps Jumbo canonical. No ledger entry approves a NORSPAN publisher for
this NFS mount. Owner has explicitly reaffirmed Jumbo. First assess native operations
using new synthetic roots and verify no user-provisioned compatible volume is available.
An administrator compatible volume remains a valid separate future route, but cannot
be provisioned or asserted by an unprivileged user.
Proposed alternative: **Jumbo Native Commit JNC-1**, a prospectively selected single
publication protocol, NOT a runtime fallback. Reserve the final name atomically with
O_CREAT|O_EXCL|O_NOFOLLOW, write through the retained original O_RDWR descriptor,
verify actual bytes/hash/mode/nlink/named ancestors, fsync file and parent, and keep
all partial or foreign objects on any failure. Never use overwrite rename, hardlink,
unlink retirement or deletion. nlink remains exactly 1. Direct visible object is
NOT automatically committed: all consumers must validate the complete strict object,
predecessor lineage and applicable containing acquisition/role seal before use.
Private/raw objects cannot be consumed before their exact complete manifest/seal.
Incomplete controls, partial raw/private sets or initiated phase without terminal
state are unresolved and cannot repeat network/raw access. Fully reconstructed
pre-start entry/ready controls alone may resume. Return from a publisher is allowed
only after retained-FD digest/metadata/ancestry/cardinality checks and successful
file/parent durability calls. This explicitly changes the original atomic-complete
hardlink/unlink contract; both plan and implementation must review the changed
visibility/consumption semantics before any production selection.
Reject: exists-check then overwrite rename, deleting temp after a checked unlink,
relaxing nlink/modes, changing only TMPDIR, or declaring success because NFS faults
were not seen in a finite test run.

## Ordered milestones and acceptance
- Q0: inspect public code and mount/capacity/identity; freeze this plan, before-images;
  independent plan SHIP. Diagnostic roots under /jumbo/lisp/f004ndc/tmp/lisplab1 only.
- Q1: reproducible source-free diagnostic harness. Fresh synthetic roots for each run,
  trace operation/error/stat/descriptor/listing observations without source bytes;
  run legacy link/unlink metadata patterns and strict current scratch removal,
  verify racing exclusive-create behavior and file/directory fsync. Preserve all
  evidence. Diagnose reproduced failures only; explicitly record non-reproduction
  and unproved causes. No deletion of pre-existing/retained evidence. A cleanup
  scenario may delete only its newly constructed fake Git scratch as its subject.
- Q2: independently reviewed JNC-1 primitive plus test-first regressions, initially
  separate from production builder. Synthetic incomplete/competing finals, write/
  chmod/file-fsync/parent-fsync/digest/ancestor/cardinality failures, descriptor
  substitution, wrong bytes, short writes, interrupts and no descriptor leaks.
  Competing process creates have exactly one winner; no foreign object overwritten
  or deleted. Explicit consumed-uncommitted-object negatives required.
- Q3: integrate only after Q2 review; new prospective publication amendment binds
  unchanged scientific protocol and JNC-1 code/config paths. Preserve original plan
  and config before-images; bind amendment review separately and replace canonical
  implementation authority member only prospectively, never overwrite prior BLOCK.
  Exact finite authority path/hash changes must be justified; no wildcard aliases.
  If this cannot pass custody/history semantics, leave production BLOCK.
- Q4: full source-free suite ON PROJECT NFS, fault coverage table across every
  declared entry/ready/started/first subprocess/raw/publication/terminal boundary;
  actual synthetic acquisition→prepare→verify and rejection, restarted started
  states zero repeat access, children/FDs closed, evidence preserved. Capture failures
  and gaps honestly. Independent whole-implementation review of frozen code/config/
  tests/log/amendment. Only whole SHIP plus authority review may start Q5.
- Q5: consolidate reviewed reproducible checkpoint; build real accessible-history
  and authority only after Q4, independently review exact controls; acquire pinned
  candidate once. Run frozen identity/license/pedigree/history/internal pruning/
  group roles/cross-role/support gates. First deterministic rejection is terminal;
  operational failure unresolved. No changed thresholds or replacement after exposure.
- Q6: seal four blind role payloads only if gates pass; independent readiness SHIP;
  build/freeze/review contained calibration/C1 implementation before model operations.
  C2 inaccessible. Calibration and C1 once, verify inference, sign exactly one G3
  branch or no-decision; freeze case precedence, M5 and applicable M6.
- Q7: applicable learned engineering→25M→100M→1B gates in sequence, otherwise M7
  signed N/A; freeze representations/configs/claims; signed M8 opens C2 once;
  final functional/causal/stability/statistical/single-case evaluation; evidence,
  manuscript and reproducibility release freeze before later-paper training.
  Actual authorized jobs use tmux, free GPUs only after nvidia-smi authorization,
  fresh configs/run dirs and early progress/ETA checks; do not wait for long jobs.

## Definition of done and limits
Jumbo qualification requires actual native positive/negative evidence, all declared
fault-matrix rows covered or explicit BLOCK, whole implementation and authority SHIP,
no overwrite/deletion/repeat access/false success, frozen reproducible checkpoint.
Scientific completion additionally needs every Q5-Q7 gate; a terminal source failure
is honest operational closure but does NOT complete independent confirmation.
Scope SHIP is not whole SHIP. Infrastructure IO failure is never scientific negative.
No automatic commit/push: user requested consolidation, not an explicit new commit.

## Verification / one-way doors
Compile and source-free pytest under new Jumbo basetemp/TMPDIR roots; no cache writes
in real history; syscall traces restricted to fresh synthetic subjects; exact input
hash/mode/nlink binding; git diff --check. Preserve all prior evidence. A real phase
marker/acquisition/private payload/final opening is create-once; do not enter without
new independently approved canonical authority. No hard power-crash/server-reboot or
multi-host support is inferred from single-client synthetic tests; any required
unavailable qualification remains a blocker rather than invented evidence.
