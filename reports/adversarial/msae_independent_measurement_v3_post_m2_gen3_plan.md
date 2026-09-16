VERDICT: SHIP
REVIEW_SCOPE: plan
PLAN_SHA256: c4ea59571eacc970cb282a44460367ff25fd67b972fe4a957da165ac3e579ef7
ONE-LINE: The revised plan closes the protocol, namespace, review-gate, testing, and execution-order gaps.

BLOCKERS        (must fix before proceeding; empty if none)

REVISIONS       (should fix; not blocking)

NITS            (optional, cap at 5)

CHECKS RUN
  - `check-plan --path docs/plan-msae-independent-measurement-v3-post-m4-gen3.md` → `PLAN: PASS`.
  - Reviewed all 285 plan lines from scratch.
  - Hashed the frozen plan → `c4ea59571eacc970cb282a44460367ff25fd67b972fe4a957da165ac3e579ef7`.
  - Compared predecessor config construction, verifier ownership, closure extension, candidate classification, and M4 paths → revised plan closes each inherited contract.
  - All named gen3 review/config/data/provenance/run/M4-root namespaces are absent before P0.
  - Quarantined payloads received lstat-only metadata checks; no content open/hash.
  - No GPU, model, tmux, experiment, or gen2 M4 command was run.

CONTRACT COVERAGE
  - Gen2 preservation without overstating historical evidence → met.
  - Disjoint, exhaustive gen3 namespaces → met.
  - Root-independent reconstruction bound to actual gen3 code → met.
  - Immutable M1/M2 verifier and closure duties → met.
  - Machine-enforced plan, implementation, and post-M3 reviews → met.
  - Closed candidate/static/process/failure surfaces → met.
  - M4/prescore/sign/launch ordering → met.
  - No premature GPU/model/tmux access → met.
  - Confirmation scoring and Stage C remain excluded → met.
  - Definition of done is observable and bounded → met.

UNKNOWNS
  - Gen3 implementation and RFC bytes do not yet exist; P1/P2 checks will review them.
  - The original failed-M4 transcript remains unavailable and is correctly recorded as such.
  - Eventual P5 handoff depends on external GPU availability.
