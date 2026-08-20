VERDICT: SHIP
ONE-LINE: Atomic authoritative closure removes the final race while preserving fail-closed scientific and lifecycle boundaries.

BLOCKERS        (must fix before proceeding; empty if none)
  - None.

REVISIONS       (should fix; not blocking)
  - None.

NITS            (optional, cap at 5)
  - PLAN_RELATIONAL_MEASUREMENT_V4.md:350-354 — add the missing “If” before “the launcher dies.”
  - PLAN_RELATIONAL_MEASUREMENT_V4.md:360-368 — the verifier truth table could state explicitly that `OWNER_TERMINALIZATION_FAILURE` requires a complete opening chain while `PREOPEN_OWNER_FAILURE` requires no valid opening; the surrounding clauses already imply this.
  - PLAN_RELATIONAL_MEASUREMENT_V4.md:140-142 — “constant edge contrast” is slightly narrower than the component-varying positive DGP; “component-equal average edge contrast” would match the target exactly.

CHECKS RUN
  - `/jumbo/lisp/f004ndc/.agent-workspace/bin/check-plan --path experiments/wip/MSAE/PLAN_RELATIONAL_MEASUREMENT_V4.md` → PLAN: PASS.
  - `sha256sum experiments/wip/MSAE/PLAN_RELATIONAL_MEASUREMENT_V4.md` → `1cf3b4f331d2a92453fec8654de34c6d166bb816e71ba354efcc1b5a6b7d2036`.
  - Rehashed the v3 terminal, source pool, parser report, exposure manifest, scout implementation, and scout config → all six match their frozen bindings.
  - Traced prepublication crash, postpublication crash, concurrent owner/supervisor publication, timeout-at-terminal, invalid closure, missing closure, preopening failure, process-group descendant, and storage-failure states → no state can publish two authoritative closures or promote an incomplete closure.
  - Re-read the exact matching, estimator, DGP, balance, selection, decision, authorization, and promotion clauses → all outcome-determining choices remain frozen and fail closed.
  - Inspected isolation clauses → no representation outcome, model load/forward, activation cache, CUDA computation, fresh corpus, optimizer, backward, checkpoint, or learned-representation path is authorized.
  - No implementation files were modified; no tests, source builds, benchmark, simulation, model inference, or experiment code was run.

CONTRACT COVERAGE
  - Immutable v3 provenance and signed parent stop → met — lines 27-43; every stated parent/engine hash matches current bytes.
  - Opened-data, synthetic-outcome-only measurement boundary → met — lines 5-25 and 370-374 prohibit representation outcomes, fresh corpora, and training.
  - Exact matching, caps, nonreuse, folds, and deterministic tie objective → met — lines 45-136 are fully prespecified.
  - Primary estimand, estimators, null controls, DGPs, intervals, and overlap diagnostics → met — lines 138-249 are component-aware and fail closed.
  - Balance, support, source selection, nomination order, and scientific decision precedence → met — lines 251-300 define exhaustive gates and mutually exclusive decisions.
  - Ed25519 trigger/handoff/opening provenance → met — lines 312-329 bind schemas, keys, nonces, PIDs, authorization, ready, trigger, handoff, and opening.
  - Atomic unique closure → met — lines 329-340 define one complete signed discriminated closure, constructed before a single fsynced no-replace publication with no separate claim or required alias.
  - Timeout and process containment → met — lines 342-351 require termination or killing of the isolated owner process group, confirmed group death, then full closure verification before supervisor fallback.
  - Incomplete and invalid closure handling → met — prepublication crash leaves an absent fail-closed namespace; postpublication crash leaves a complete closure; invalid or unwritable closure is immutable and claim-ineligible.
  - Single lifecycle/claim verifier → met — lines 360-368 require exact schema, signature, identity, provenance, result, decision, and atomic-closure validation and reject incomplete or invalid states.
  - M5 and definition of done → met — lines 410-432 distinguish preopening/opened branches and explicitly cover at most one closure plus absent/invalid external failure.
  - No model/fresh-data/training path and v5 promotion boundary → met — nomination permits only a separately reviewed fresh-data preregistration, never a relational effect or learned model.

UNKNOWNS
  - Implementation conformance, atomic publication on the target filesystem, subprocess behavior, full tests, smoke determinism, source support, and benchmark resources remain intentionally deferred to exact-candidate review and preauthorization checks.
