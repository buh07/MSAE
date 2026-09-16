VERDICT: SHIP
REVIEW_SCOPE: gen4_plan
FAILED_GEN3_PLAN_SHA256: c4ea59571eacc970cb282a44460367ff25fd67b972fe4a957da165ac3e579ef7
GEN4_PLAN_SHA256: c443a9eba2305a488b9948467676829c4d317cd67d9c4936a339d6af33bd023b
ONE-LINE: The revised plan closes digest direction, authority, durable publication, recovery grammars, namespaces, and pre-model launch gates.

BLOCKERS
- None.

REVISIONS
- None.

NITS
- [clarity] `docs/plan-msae-independent-measurement-v3-post-m4-gen4.md:414-421,546-563` — Read the compact M4 child-set rule with the later authoritative exception permitting a final-output-conditioned empty transaction root after descriptor deletion.
- [verification watch] `docs/plan-msae-independent-measurement-v3-post-m4-gen4.md:186-205` — Freeze timestamped terminal evidence before implementation review, reproduce those exact bytes during setup, and separately revalidate current absence. Reject a fresh setup-time timestamp.
- [verification watch] `docs/plan-msae-independent-measurement-v3-post-m4-gen4.md:565-587` — Require no-replace semantics for cross-directory authorization publication, alongside both directory fsyncs.

CHECKS RUN
- `check-plan --path`: PASS.
- Plan SHA-256: `c443a9eba2305a488b9948467676829c4d317cd67d9c4936a339d6af33bd023b`.
- Frozen gen3 plan, reviews, preflight, code, RFC, and test digests all matched.
- Read current lineage exceptions, controls, schemas, atomic publisher, recovery grammars, nonce namespace, run transitions, and relevant predecessor code.
- Confirmed declared gen4 namespaces remain absent.
- Inspected quarantined payloads only through stat/lstat; did not open or hash them.
- Ran no setup, M4, prescore, signing, launch, model, GPU, tmux, or experiment command.
- Persisted review; transcript hash: `48d959ac10822d13718ea43d2035b917e4987dd19f92f173312755eb17132ca6`.

CONTRACT COVERAGE
- Honest two-invocation gen3 failure preservation → met.
- Disjoint gen4 namespaces and commands → met.
- Acyclic terminal records and implementation-review authority → met.
- Acyclic setup subject/config/completion-manifest lineage → met.
- Setup durability and recovery → met at plan level.
- M4 and signing recovery → met at plan level.
- Exact review schemas and stale-authority rejection → met.
- Exact nonce and run/terminal transitions → met.
- Source containment, quarantine, two-tree reconstruction, and CPU/no-model gates → met.
- Review/prescore/sign/launch ordering and immediate return → met.
- Behavioral failure coverage → met in scope.

UNKNOWNS
- Invocation 1 remains operator-disclosed.
- Invocation 2’s traceback was not opened; its metadata remains asserted.
- No gen4 implementation exists, so parsers, syscall wrappers, recovery, concurrency, closure, and launch behavior await implementation review.
- One-way transitions and live GPU/model/tmux effects remain intentionally unobserved.
