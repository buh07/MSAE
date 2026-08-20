# Canonical induction two-tier v2 plan adversarial review 4

**Verdict: BLOCK**

The revised graph still left technical-invalid outcomes unreachable from finalization and exposed two pre-gate/runtime access holes.

## Blocking findings

1. `TECHNICAL_INVALID_STOP` was exhaustive but was not a legal predecessor of `final`.
2. Pre-gate `review-binding` could recursively stat or hash the frozen confirmation payload.
3. Direct QA/worker entry points could perform a forward without a create-once controller attempt marker, leaving an unrecorded post-forward limbo after a crash.

## Revisions requested

- Bind calibration to exact evaluator/config/fixture hashes and recompute it during candidate preflight.
- Replace the ambiguous “four runtime jobs” with one observable tmux session/process chain.
- Do not claim that an unopened payload is externally byte-unchanged when only registered access can be audited.
- Enumerate exact QA array names and clarify the prospectively accepted external-upstream-set scope.

The plan was revised to make technical-invalid terminals finalizable, restrict pre-gate review verification, put all forward-capable subcommands behind an atomic controller token, bind/recompute calibration, define the exact tmux launch condition, narrow the payload-access claim, enumerate QA arrays, and explicitly scope the external set as incomplete GPT-2 circuit coverage.
