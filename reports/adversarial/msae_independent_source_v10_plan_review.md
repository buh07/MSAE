VERDICT: SHIP
ONE-LINE: The amendment closes the identified terminal-reconstruction defects without weakening gates, custody, or claim boundaries.

BLOCKERS        (must fix before proceeding; empty if none)
  - None.

REVISIONS       (should fix; not blocking)
  - None.

NITS            (optional, cap at 5)
  - docs/plan-msae-independent-source-v10.md:17-23,172-175 — “scientific defects/hypotheses” and “two scientific deltas” include the terminal-verifier repair; “scientific-preparation protocol deltas” would distinguish the control-plane correction from the single scientific parser hypothesis.

CHECKS RUN
  - `sha256sum docs/plan-msae-independent-source-v10.md reports/provenance/msae_independent_source_v10/v9_carryover_authority.json` → exact matches: plan `47a19df3e70f17df63c2ef676877d07bc7e473736977067a3a3e64911a57436e`; carryover `da13ae40e64c9828b2d08c29b4ff280bac5c71eeb8578a977f953f2169f7585d`.
  - `stat` on the plan and carryover → both are regular mode `0644`, link count 1.
  - Full line-numbered plan read → the finite B2 dependency, private-directory classification, filesystem-independent directory records, restored failure taxonomy, empty-namespace rejection, gate order, capability closure, M0–M4, and Definition of Done are mutually consistent.
  - Canonical carryover reconstruction using public controls and lstat-only data metadata → PASS: canonical ASCII JSON plus one LF; exactly 20 unique path-sorted control records hash-current; three directory and four raw-file lstat records match; control-map digest `d0035594710b62cd9b998367136f2bf02110bf59095d359b0f2dbdd75e1aec3c`; raw-map digest `881ac46eab4a9e4ecf50a2afb088d37ac98f060b84a45ede90d79007e216f363`. Raw bytes were not opened or hashed.
  - Public V9/V10 registry and alias-screen binding → both V10 copies are byte-identical to V9; hashes are `3166d09141374506d7d200fa8d630a66e4a790f5a3f2e81778ed522d4a327863` and `cdda84035279b78698f98c760c5ce12d5276b9b2afbc8e4218133d8207dccafd`; each binds 16,133 inputs and digest `8070a7cdd536a0dbd6104ff1dfb279ef01fb0acf98e969227625324155227564` with zero quarantine reads.
  - Targeted lstat-only future-state check → V10 data namespace, baseline, authority manifest/review, acquisition entry/outcomes, scientific entry/outcomes, payload, no-training gate, and seal are absent.
  - `bin/check-plan` / `.agent-workspace/bin/check-plan` availability check → neither backend exists in this project; canonical headings, checklist milestones, ordering, and Definition of Done were inspected directly.
  - Prohibited-operation audit → no V8/V9/V10 raw or private bytes and no Atlas quarantine content were opened, read, hashed, parsed, or printed; no network, acquisition, baseline, authority, model, tokenizer, GPU, scoring, training, K2, or branch command was run.

CONTRACT COVERAGE
  - Prospective one-way-door order → met — amended plan and this independent review precede a new implementation review, baseline, authority, acquisition, scientific entry, or raw read (docs/plan-msae-independent-source-v10.md:121-137,339-357).
  - Exact carryover and historical authority → met — the plan binds the canonical V9 terminal chain and byte-identical 16,133-input pre-V8 registry/screen, while making no fresh V8 or post-V8 global-absence claim (docs/plan-msae-independent-source-v10.md:42-96).
  - Prior B2 recensus blocker → met prospectively — the gate has one path-specific `dependent_canonical_final` placeholder, the seal has the existing self placeholder, terminal verification reconstructs both canonical objects, and both states enter the recensus projection (docs/plan-msae-independent-source-v10.md:209-217).
  - Prior B1 empty-private-directory blocker → met prospectively — exact no-directory, empty-directory, and payload-directory states are independently classified before reconstruction; the classifier-proven state, not a caller choice, controls subtraction (docs/plan-msae-independent-source-v10.md:195-199,232-258).
  - Prior filesystem-dependent directory revision → met prospectively — generated-directory records use exact sorted direct child names and omit directory size/nlink; historical entry reconstruction explicitly restores the pre-private child set without arithmetic (docs/plan-msae-independent-source-v10.md:200-207,249-254).
  - Prior DEPREL and empty-namespace blockers → met prospectively — the amendment restores V9’s `DEPREL="_"` taxonomy and requires rejection of any observed V10 namespace, including an empty directory (docs/plan-msae-independent-source-v10.md:192-194).
  - Scientific delta and ordered gates → met prospectively — only unavailable LEMMA is relaxed; all other parser failures remain exact, and custody, support, family, pedigree, dedup, role overlap, full adapter-expanded history, role/split, payload, and closure remain ordered before any scoring (docs/plan-msae-independent-source-v10.md:219-230,282-313).
  - B2 deterministic assurance and blindness → met prospectively — V10 raw access is classified-B2-only during terminal reconstruction; public artifacts and expected payload bytes/counts are recomputed, while the published private payload is compared only opaquely and predecessor raw/private remains unreadable (docs/plan-msae-independent-source-v10.md:260-275,332-335).
  - Containment, publication, and capability barriers → met prospectively — no-follow descriptor traversal, no-replace/fsynced publication, identity-checked cleanup, process/training recensuses, zero neural operations, and false authorizations are explicit (docs/plan-msae-independent-source-v10.md:152-170,317-330).
  - Narrow claims and non-retry semantics → met — neither V10 readiness nor rejection claims independent replication or training authorization; V9 stays immutable, V10 is one-shot, and a verification/review BLOCK is retained as incomplete for a new successor (docs/plan-msae-independent-source-v10.md:25-39,315-335,374-388).
  - M0 plan quality → met — the carryover reconstructs source-free, all future one-way artifacts are absent, and this review returns SHIP.
  - M1–M4 execution → prospective — each remains explicitly gated on implementation, source-free tests/review, eligible authority, one-shot acquisition/preparation, terminal reconstruction/review, evidence integration, and controlled commit (docs/plan-msae-independent-source-v10.md:344-372).

UNKNOWNS
  - The amended builder, runner, tests, configuration, and source-free log have not yet passed the required new implementation review; this SHIP verdict authorizes only that source-free implementation step.
  - Actual V10 acquisition availability and candidate license, source-family, pedigree, support, overlap, split, and payload outcomes remain prospective.
  - The exact V9 raw field that caused `missing_or_unknown_field` remains intentionally unknown source-free; the plan correctly treats unavailable lemma as a bounded hypothesis and retains the next first failure if wrong.
  - V8/V9/V10 raw/private bytes and Atlas quarantine contents were deliberately not inspected; only permitted public controls and lstat metadata were used.
