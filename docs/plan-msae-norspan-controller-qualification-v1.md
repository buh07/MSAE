# PLAN — NORSPAN controller, authority and recovery qualification v1

2026-09-16. Prospective source-free successor; no production authorization.

## Goal
Complete the controller/catalog transport and authenticated approval verifier,
exercise real synthetic history/acquisition/scientific/terminal reconstruction,
and close only fault-matrix cells supported by named executable evidence.

## Constraints and non-goals
- Jumbo only; no administrator contact. DES-0203/0221 unchanged. DES-0231 remains
  proposed client-only conditional storage, not a server/backup/hard-quota claim.
- All new synthetic outputs/cache/evidence under /jumbo/lisp/f004ndc/tmp/lisplab1.
  Never read/hash/print .msae_keys, Atlas private finals, real V8/V9/V10 or NORSPAN
  source/raw/private. No real census/acquisition/payload/scoring/model/GPU/tmux,
  K2/branch/G3/C2, initiated retry, destructive cleanup or automatic commit/push.
- Original science protocol/config/TODO/V10 reference byte-identical. Science
  predicates unchanged. V10 terminal; AMALGUM v3 exposed calibration only.
- Preserve v5, old exact candidates/checkpoints and all BLOCK/REVISE reviews.
  Production guard remains UNCONDITIONAL throughout this implementation task.
  Synthetic tests override the guard only after asserting their root is a newly
  created synthetic Jumbo directory, never by a production command-line switch.

## Design-bank clarification
Queries for NORSPAN/controller/canonical authority/recovery returned no matching
active choice; DES-0203/0221 determine topology, proposed DES-0231 limits guarantees.
Query backend rejects undeclared nested repository; bounded public source reads
establish wiring. Owner was asked which existing signer/trust root authenticates
approval. No answer/root exists yet: real authenticated canonical authority cannot
be established by this agent. Implement verification against explicit externally
pinned Ed25519 public-key DER and release-statement hashes, tested with disposable
synthetic keys only. Production trust enrollment and signed approval remain BLOCK.

## Approach and alternatives
Use a single explicit Controller around existing actual commands/context session.
Catalog snapshots are outside the scientific project root but on Jumbo. They are
canonical ordinary nlink1 mode644 files, reserved O_EXCL, written/fsynced and their
parent fsynced, never replaced/deleted. Each registered successful producer receipt
is checkpointed BEFORE publication returns. A catalog write/fsync/close failure
fails the invocation; visible unregistered/partial objects are never adopted.
Fresh invocations take an explicit prior catalog path/hash/lineage, never discover
latest. A partial catalog is not usable evidence. Snapshot v2 includes bounded
outside live raw/private manifests so fresh full inventory works. Catalog transport
pins custody only; signed approvals separately authenticate exact finite candidates.

New verifier uses /usr/bin/openssl Ed25519 pkeyutl -verify -rawin against bounded,
sealed Linux memfd copies (no path reopen of mutable keys/statement/signature).
Require fixed Ed25519 DER encoding, 64-byte signature, canonical duplicate-free
JSON, exact schema/scope/verdict, explicit pinned statement digest for rollback
protection, finite path/mode/hash subjects including ALL runtime dependencies.
Whole-release approval and later source-authority approval are separate statements;
the latter binds the actual current authority receipt. No agent-generated key or
SHIP header establishes owner trust. No signing/enrollment production API.
OpenSSL 3.0 docs checked: https://docs.openssl.org/3.0/man1/openssl-pkeyutl/ .
Release manifests are outside their subjects to avoid self-hash cycles.

Fresh recovery invokes actual config/history/authority/phase/acquisition validators.
Prestart reports only validated current observation; initiated incomplete states
never resume. Acquisition success validates metadata/raw opaque custody WITHOUT
scientific raw access. Complete scientific success/rejection uses existing explicit
terminal raw-reconstruction exception once per recovery invocation, records it,
recomputes science, verifies private roles opaquely (C2 scientific reads zero),
then final inventory/history/evidence fences. No historical invocation success is
inferred and no source/network/model/training capability is returned.
Incomplete/IO/custody problems are operational BLOCK, not scientific negatives.

Bound eager descriptor/history enumeration with incremental admission: 65536
objects and depth64 per census, failure before overflow; overflow BLOCKS the full
accessible-history gate, NEVER silently drops history. Protected lstat accounting
and original exemptions are unchanged. File/total limits stay monitored, not quotas.

Rejected: trust by filename/header/caller SHA alone; unsigned catalog as approval;
implicit latest/adoption/retry; weakening histories or science; invented crypto;
third-party Python crypto dependency; server guarantees inferred from fsync success.
OpenSSL already installed; its runtime dependency is explicit and failure blocks.

## Milestones
- [ ] Q0 preserve exact prior public candidate; check-plan and independent plan SHIP.
- [ ] Q1 controller + bounded v2 catalogs + transport across actual command boundaries.
  Acceptance: live and fresh synthetic sessions preserve actual receipts/manifests;
  checkpoint failures fail closed; no discovery/adoption/repeated initiated work.
- [ ] Q2 signed exact finite approval verification and explicit canonical binding.
  Acceptance: genuine synthetic signatures pass; wrong key/scope/digest/subject/mode,
  stale approval, duplicate/noncanonical data, missing dependency and unsigned SHIP
  fail before privileged access. Real trust-root enrollment remains explicitly open.
- [ ] Q3 full synthetic prestart/acquisition/scientific/terminal recovery and bounded
  census integration. Acceptance: actual gates and first-failure replay run; extra,
  substituted/partial/foreign objects and current fsync/close failure cannot yield
  success; recovery does not rerun Git or initiate scientific raw access; terminal
  raw reconstruction counted separately; opaque C2 verification never parses C2.
- [ ] Q4 qualify every declared matrix group/cell and classify all80 audit rows.
  Acceptance: named actual firing tests + retained transcripts for each closed cell;
  combined interruption/substitution/extra/syscall faults across markers, subprocess,
  raw, roles, seals, history, ancestors and recovery. Unexercised cells remain OPEN,
  external storage/hard-containment cells remain BLOCK; counts never prove closure.
- [ ] Q5 independent exact-candidate whole review; finite public checkpoint and
  current synthesis/handoff. Acceptance: exact subject hashes before/after review,
  reproducible source-free tests, all negative reports preserved, truthful open list.

## Definition of done
- Controller and paired consumers work across explicit fresh catalog checkpoints.
- Authenticated verifier is tested; real canonical authority is marked established
  ONLY with an enrolled owner trust root and exact independent whole approval.
- Full accessible-history/phase/scientific/terminal recovery is actually exercised
  with synthetic data, no source/network retry, cleanup or model authorization.
- Each matrix closure cites executable named evidence; absent coverage is OPEN.
- No false successful terminal state, destructive cleanup, repeated initiated
  acquisition/raw access, child/descriptor leak or C2 scientific access.
- Exact whole review and reproducible checkpoint, or explicit scoped completion
  with unresolved whole qualification BLOCK. No declaration of full task completion
  if authority, mandatory matrix cells or containment remain unmet.

## Risks and one-way doors
Catalog and approval schemas are prospective new versions; v1 readers/catalogs
remain readable and earlier evidence immutable. Crash after pair publication but
before outside checkpoint is intentionally unresolved, not repaired by adoption.
Controlled-writer finite observations are not atomic snapshots or same-UID adversary
exclusion. Key enrollment/revocation, server crashes/backups, hard resource bounds
and whole scientific authorization are NOT resolved by this code. Never open real
subjects to validate the implementation. No production guard removal this task.

## Verification plan
Write focused failing synthetic tests before each implementation slice. Explicit
22 maintained suites plus separately named new controller/authority/recovery/matrix
suites only, fresh Jumbo basetemp/cache/JUnit/log per run; never blanket pytest.
Actual fake-Git fixture replaces only synthetic transport/process/evidence producers,
NOT config, census, state, authority, acquisition/science/terminal gate outcomes.
Supervisor actual child tests remain required. Compile finite scripts into Jumbo
cache; report missing lint/typecheck tools honestly. Independent reviewer may add
source-free attacks; preserve every failing transcript and reviewed candidate.

- [ ] Run `python -m pytest -q tests/test_msae_norspan_jpc_controller.py` with a fresh Jumbo basetemp, log and JUnit.
- [ ] Run the explicit maintained22 suite paths from the prior frozen tests.json.
- [ ] Compile only the finite public candidate scripts using `python -m py_compile` and a fresh Jumbo PYTHONPYCACHEPREFIX.
