VERDICT: SHIP
ONE-LINE: Revised plan closes all five prior blockers with explicit, testable lifecycle and lineage requirements.

PLAN_SHA256: 958b38611e27b426b62bf2ebcaa621de24d583c4e3895afe5d047a09f66afd08

BLOCKERS
  - None.

REVISIONS
  - None.

CHECKS RUN
  - check-plan --path PLAN_CAPACITY_EXTERNAL_VALIDITY_V1_R3.md -> PLAN: PASS
  - Read-only line-numbered review of the revised plan -> no JSONL accessed.

CONTRACT COVERAGE
  - Guard all M1-M4 JSONL access surfaces -> met.
  - Durable external authorization/state and post-access terminal -> met.
  - Deterministic v1-derived AST rewrite -> met.
  - Phase-indexed namespaces and exact lock/process ownership -> met.
  - V1 lineage revalidation and no restore path -> met.

UNKNOWNS
  - Implementation compliance remains to be established by candidate, mutation, parity, freeze, CUDA, and launch checks.
