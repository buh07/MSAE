VERDICT: SHIP
ONE-LINE: Candidate is safe to freeze; registered scientific and launch firewalls now hold.

BLOCKERS        (must fix before proceeding; empty if none)

REVISIONS       (should fix; not blocking)

NITS            (optional, cap at 5)

CHECKS RUN
  - `.venv-atlas/bin/python -m pytest -q tests/test_behavioral_endpoint_v6.py tests/test_joint_controllability_assay_v5.py` → 36 passed.
  - `.venv-atlas/bin/python -m py_compile scripts/behavioral_endpoint_v6.py scripts/analyze_behavioral_endpoint_v5_templates.py` → pass.
  - `bash -n scripts/launch_behavioral_endpoint_v6_tmux.sh` → pass.
  - `behavioral_endpoint_v6.py preservation-verify` → PASS.
  - `behavioral_endpoint_v6.py cache-preflight` → PASS; frozen content hashes matched.
  - Hostile no-binding/prepared-row audit → 1,152 retrieval rows, zero full-prompt registered-string leaks.
  - Hostile cyclic-incidence audit → every template/set and registered marginal exactly balanced.
  - Streamed V5 projection replay → exact equality with frozen 384 development rows and both 384-hash sealed sets.
  - Heterogeneous crossed-bootstrap oracle → implementation and literal component-product reference matched exactly.
  - Prepared selection audit → zero predecessor, sealed-V5, development, or cross-source accepted-document overlaps.
  - Stable hashes checked → script `9993045e…`, config `b85d329f…`, tests `8282db5c…`, launcher `c6b063b…`, PRESCORE `e2817f81…`, deterministic record `8097b792…`.

CONTRACT COVERAGE
  - Complete V5 preservation → met — `scripts/behavioral_endpoint_v6.py:43-56`; manifest covers the complete frozen inventory and all current V5 artifacts, and confirmation contains only `BLOCKED.json`.
  - V5 analysis-only report → met — `scripts/analyze_behavioral_endpoint_v5_templates.py:19-45`; exact metric/completion/gate/freeze inputs bind, with no model loading or rescoring.
  - Sealed-confirmation projection firewall → met — `scripts/behavioral_endpoint_v6.py:60-77`; ranged binary streaming avoids whole-file reads and deserializes only development rows.
  - Full-width source PRF and V5-compatible text hashing → met — `scripts/behavioral_endpoint_v6.py:25,57-58`; known-vector tests confirm unsigned 64-bit little-endian PRF and lowercase whitespace normalization.
  - Deterministic preparation and exclusions → met — PRESCORE and deterministic attestation bind all 13 prepared files, complete rejection records, fingerprints, and byte-identical preparation.
  - Retrieval no-binding and token gates → met — `scripts/behavioral_endpoint_v6.py:134-146,188-202`; frozen prompts contain no registered keys/candidates and all condition lengths/candidates pass every tokenizer.
  - Agreement cyclic incidence and prompt controls → met — `scripts/behavioral_endpoint_v6.py:147-174,203-215`; frozen rows satisfy role/verb balance, full-rank audit, reciprocal flips, and token-length gates.
  - Exact endpoint estimands → met — `scripts/behavioral_endpoint_v6.py:288-310`; retrieval and agreement effects, nuisance terms, strict directionality, and eligibility match the plan.
  - Cell and crossed hierarchy → met — `scripts/behavioral_endpoint_v6.py:329-359`; support, strict boundaries, higher quantile, infinity handling, and literal template×set×document weights are tested.
  - Stage-specific deterministic seeds → met — `scripts/behavioral_endpoint_v6.py:392-393,416`; development and confirmation are explicit seed components.
  - Outcome classifications → met — `scripts/behavioral_endpoint_v6.py:366-376,394-421`; replication, template-conditioned, endpoint-specific, and final states are explicit.
  - Confirmation firewall and timeout terminals → met — `scripts/behavioral_endpoint_v6.py:312-328,360-365,396-423`; authorization is endpoint/model-specific and timeout, failure, blocked, and scientific terminals remain distinct.
  - GPU mapping and handoff → met — `scripts/launch_behavioral_endpoint_v6_tmux.sh:47-119`; six unique physical UUIDs are bound, reused by fixed queues, runtime-verified, and only live or clean terminals satisfy handoff.
  - No training or representation-method path → met — `scripts/behavioral_endpoint_v6.py:297-311,421`; endpoint-only causal-LM scoring is the sole model path, with training and method authorization false.

UNKNOWNS
  - No GPU model forward or live tmux launch was run during this read-only pre-freeze review.
  - The two temporary double-prepare roots were removed; their signed-off hashes were verified against the accepted prepared root rather than replaying both full corpora.
