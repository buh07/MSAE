# Prospective owner-origin Markdown approval receipts v1

2026-09-16. The user clarified that production authority is proof of approval FROM
THEM; a manual Markdown edit or equivalent is acceptable. A separate Ed25519 signer
is not required. This approves the trust mechanism, NOT an exact candidate, whole
implementation, real operation, or scientific/training gate. Preserve all62subject
bytes/modes until both active main/extracted runs and exact reviewers have finished.

## Trust boundary and usability
Use the authenticated owner conversation, or the owner's explicit confirmation that
they edited a particular approval document, as the external enrollment channel.
Record that proof in a human-readable Markdown receipt tied to exact release
subjects, scope, review/source bindings and lineage. Whole and source-authority
receipts remain distinct; neither an unsigned catalog, SHIP header nor an agent
checkbox edit establishes owner origin. The outside expected receipt SHA must be
transported from the owner's approval/control-plane record; an agent-selected hash
or discovered file is not enrollment. Runtime checks integrity and exact scope;
it cannot authenticate chat authorship or distinguish human/agent writes sharing
an OS UID. This external provenance assumption MUST be explicit, not a claim of
cryptographic nonrepudiation, same-UID isolation or autonomous authentication.

Receipt grammar: exact fixed Markdown heading, blank line, `Decision: APPROVE`
(or PENDING/REJECT for a non-authorizing request), blank line, one json fence, strict
canonical JSON plus newline, closing fence and terminal newline, no extra objects.
The JSON has exact schema, bounded owner_proof(channel/reference/text), and statement.
Only owner_conversation or owner_manually_edited_document channels; nonempty bounded
control-free reference/text. The statement has owner-approval schema, whole/source
scope, SHIP decision and the same strict subject/receipt/lineage fields as existing
verification. A formatting helper constructs bytes only, does not enroll or approve.
Only APPROVE may validate; PENDING/REJECT, missing proof, wrong pin/scope/schema,
duplicate/noncanonical data, substitutions, floats/bools and mixed signed/owner
arguments fail. Plain integrity pins become approval ONLY with owner-origin external
provenance; do not relabel generic caller SHA as proof.

## Implementation, limits and canonical activation
Add OwnerApprovals reusing current finite retained-subject and actual-authority-pair/
review/custody validation, overriding only receipt authentication/statement parsing.
No production signing key needed. Existing Ed25519 implementation stays optional
and unchanged. Add an explicit --approval-kind owner-markdown|ed25519 CLI selection;
CLI defaults owner-markdown, with legacy direct-call namespaces without the new
field retaining their existing signed behavior. Owner mode rejects all key/signature
arguments; signed mode requires all existing ones. Shared outside placement, actual
per-path FD admission and guard FIRST remain unchanged. No bypass/enroll/discovery/
retry option. No code path automatically fills APPROVE or removes the production guard.
Recovery reports approval_verified/authentication method; signed_approval_verified
is false for owner receipts (true only for the retained Ed25519 implementation).

New finite public inputs: this plan0700, owner module0700, explicit owner test0644.
Owner receipts are OUTSIDE the project/candidate on Jumbo; NEVER add a mutable
approval receipt to the candidate it approves (self-reference). After exact successor
freeze, prepare only a PENDING whole-release request with complete exact subjects.
Its proposed owner_document proof text is explicitly non-authorizing while PENDING.
An owner may later mark APPROVE and confirm that exact document through the owner
channel, or explicitly approve the exact manifest in conversation for a recorded
receipt. Do not treat this policy message as such approval. Independent exact whole
SHIP and mandatory containment/fault readiness remain separate and required;
owner approval cannot turn a bounded SHIP/whole BLOCK into qualification. Existing
negative report inputs remain unchanged; future canonical whole-report replacement
still needs prospective review. Actual source-authority approval is later, separately
bound to the real approved chain, not synthesized now.

## Acceptance and reproducibility
Test-first explicit fresh Jumbo fixtures only. Genuine disposable signed fixtures
may establish synthetic baseline controls, then separate synthetic owner receipts
exercise all actual retained-subject/source-pair/review validators with no outcome
or signature-success mocks. Test normal whole+source receipt, missing/wrong owner
proof, PENDING/REJECT, all malformed/canonical/scope/pin/float/bool/cross-lineage
cases, later subject/pair/review drift and actual late-byte fences, resource monitor/
close interruptions, mixed-mode/incomplete args and every owner transport path.
Guard must still prevent ANY real input observation in both CLI modes. Test actual
fresh full typed recovery via owner receipts without repeated acquisition or scoring;
C2 opaque and scratch historical-byte limitations remain explicit. External proof
origin cannot be self-certified by these tests; fixtures are visibly SYNTHETIC ONLY.

Freeze separate exact65 candidate (62+3inputs), explicit27source-free suites,
39+2new Python syntax checks, main/extracted public-code checkpoint reproduction,
finite changed regions, exact independent scoped+whole reviews and truthful synthesis.
No complete task/canonical authority declaration absent actual exact owner approval,
whole qualification and mandatory matrix/containment. All9groups/all80rows remain
open unless each particular closure gains named firing evidence. All previous
BLOCK/REVISE/bounded SHIP/checkpoints preserved. Jumbo/no-admin/no-real-work and
original science/config/TODO/V10 bytes, AMALGUM exposed-only, all scientific gates
and once-only constraints remain unchanged.
