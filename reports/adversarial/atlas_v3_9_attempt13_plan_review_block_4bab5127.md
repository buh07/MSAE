# Attempt 13 plan adversarial review — blocked candidate `4bab5127`

- Candidate SHA-256: `4bab512753510558b5b45cc508f345724a4c6c33c831d73fbb6c59fb5a3ecf82`
- Reviewer: independent `/adversarial` agent `/root/attempt13_plan_adversarial_v2`
- Verdict: **BLOCK**
- No model inference was run.

## Blocking findings

1. Sequential donors were not explicitly source-local, permitting transfer leakage.
2. Broad signed-distance bins did not control exact UD or transformer subtoken offsets.
3. The nondependency and donor-reuse contracts did not exclude reverse/ancestor relations or impose a hard cap.
4. The freshness claim lacked a complete prior-exposure inventory and row/content overlap firewall.
5. Intervention endpoints lacked numeric independent-document floors.
6. One-shot protection was namespace-local and lacked a crash-durable authorization-consumption record.
7. The phrase `no-training` conflicted with ephemeral supervised ridge score estimation.
8. The decision rule could infer decodability from a module failure without a separate raw-signal gate.
9. The low-norm denominator and calibration rationale needed to be explicit.

## Disposition

All findings were accepted. `PLAN_ATTEMPT13.md` was revised prospectively before implementation or
fresh-source scientific inference. The superseding candidate requires a new exact-hash adversarial
review; this blocked verdict cannot authorize execution.

