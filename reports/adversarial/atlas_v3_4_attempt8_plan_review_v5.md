VERDICT: REVISE
ONE-LINE: Core gates are safe, but numerical batching and library-attestation semantics remain non-executable.

BLOCKERS

None.

REVISIONS

- [high] `PLAN.md:25,46,61,77,114-118`; `configs/atlas_discovery_v3_3/scoring.json:175` — the plan now freezes total five-bin unit/row counts but still calls the score-bearing “batch size” and “batching” fixed without stating the inherited value `64`, unit order, reference/candidate separation, padding grouping, or final partial-batch rule.
  reasoning — frozen `_forward_units` pads every slice to that slice's maximum length, so order and membership determine tensor shapes presented to SDPA. The same 700 logical conditions can therefore exercise different shapes/kernels under different legitimate interpretations of the current text. Source-parameterization only guarantees that one implementation is reused; it does not specify what that implementation must do.
  impact — implementation review would have no plan-level oracle for detecting a changed numerical estimator, and calibration/validation could be internally consistent while differing from the inherited batch-64 science runtime the technical gate is intended to authorize.
  fix — state score-bearing batch size `64`; freeze a canonical stable order over hashed unit IDs, separate ordered reference and candidate passes matching the frozen QA structure, exact contiguous batch slicing, right-padding behavior, and the final partial batch. Bind the resulting per-batch unit-ID lists, shapes, and maxima in every panel/result and require the science adapter to attest the same inherited rules.

- [medium] `PLAN.md:88,114` — all four SDPA flag names are now present, but their required Boolean values and the meaning of `/proc/self/maps` “drift” remain unstated.
  reasoning — recording a flag is not the same as requiring its prespecified value. Likewise, separate minimal, diagnostic, observer, and scientific processes may load different harmless library supersets, so exact loaded-set equality and required-library hash equality are different contracts.
  impact — two implementations can both satisfy the prose while enforcing different SDPA states or either spuriously terminalizing on harmless process-specific libraries or overlooking a missing required library.
  fix — freeze the four explicit Boolean values prescore (the retained environment audit found all four enabled) and assert them at every model stage. Replace the ambiguous loaded-set rule with a prescore-frozen required path/SONAME/hash allowlist, reject missing or conflicting duplicate SONAMEs, and record extra libraries without making unrelated extras cross-process drift unless explicitly forbidden.

NITS

- `PLAN.md:88` — rename the remaining `local_rotary` phrase “native float32” to “reconstructed float32”; the surrounding contract correctly says post-RoPE Q/K are reconstructed.
- `PLAN.md:40` — call EWT/GUM/ESLSpok “technical sources,” not all “authorizing sources”; EWT calibrates but does not authorize held-out validity.

CHECKS RUN

- `/jumbo/lisp/f004ndc/.agent-workspace/bin/check-plan --path PLAN.md` -> PASS.
- Read-only line-by-line comparison of `PLAN.md` with `reports/adversarial/atlas_v3_4_attempt8_plan_review_v4.md` -> both v4 blockers are fixed literally: Torch is `2.7.0` with CUDA `12.8`, cuDNN attention is included in the SDPA flags, and observer replay covers all 140 diagnostic condition units.
- Shell-integer count audit without Python/model imports -> five bins produce 100 bases, 30 cells, 600 candidates, 1,200 candidate rows, 100 references, 200 reference rows, 700 total condition units, and 1,400 total selected rows per source; `PLAN.md:42-46` matches exactly.
- Shell-integer diagnostic count audit -> 20 bases x (one reference + six shifts) = 140 condition units and 280 selected rows; `PLAN.md:88` matches exactly and applies both hooked and unhooked execution to all 140.
- Read-only check of the frozen scientific scoring config -> inherited score-bearing `batch_size` is `64` at `configs/atlas_discovery_v3_3/scoring.json:175`, but that value/schedule is not literal in the plan.
- Read-only verification of prior review coverage -> retained-EWT calibration union, exact fresh-GUM offsets and common gates, common-frame/local/propagated diagnostics, document caps, ESL exposure views, byte/cosine semantics, source hashes, diagnostic terminalization, and SDPA cross-stage assertion remain present.
- No model configuration or weights were loaded, no tensor library was imported or tensor executed, no forward pass/experiment was run, and no implementation file was modified.

CONTRACT COVERAGE

- V4 blocker: complete SDPA backend family and accurate Torch/CUDA identity -> met (`PLAN.md:81,88,114,155-156`).
- V4 blocker: full hooked/unhooked observer population -> met (`PLAN.md:81,88,124,131,195`).
- V4 revision: five-bin reference/candidate totals -> met (`PLAN.md:42-47`).
- V4 revision: exact numerical batch schedule -> unmet — batch 64 exists in the inherited config but is not stated or bound in the plan/result contract (`PLAN.md:25,77,114-118`).
- V4 revision: loaded-library allowlist semantics -> unmet (`PLAN.md:88,114`).
- V4 revision: reconstructed diagnostic naming -> partial — the main tensor name is fixed, but `local_rotary` retains one “native” occurrence (`PLAN.md:84,88`).
- Retained-EWT plus minimal-EWT calibration union -> met (`PLAN.md:36,49,57,95,134,173`).
- Exact fresh-GUM mandatory/non-poolable gate -> met (`PLAN.md:49,146-150,175`).
- Diagnostic frame arithmetic, local/propagated separation, and fail-closed observer validity -> met (`PLAN.md:81-88,195`).
- Document/class-support and exposure firewalls -> met in plan (`PLAN.md:23-24,42-47,118,196,198`).
- Endpoint/source fail-closed order and one-way validation freeze -> met (`PLAN.md:63-71,136-150,192-198`).
- Mechanically unchanged science and no-training boundary -> met structurally (`PLAN.md:152-159,170-178`).
- Safe to implement against an unambiguous numerical runtime contract -> partial — no irreversible inference is authorized prematurely, but batching and library-attestation rules still need literal prescore semantics.

UNKNOWNS

- Whether each added `65-128` cell satisfies document diversity and ESL exposure exclusions; the plan correctly assigns this to no-inference prescore and fails closed.
- The historical attempt-7 call did not record the concrete PyTorch SDPA kernel choice. The revised complete backend/environment contract is the strongest reconstructable lineage, provided the final four Boolean flag values and batch schedule are made literal.
