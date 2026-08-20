# Atlas v3.5 attempt 9 — JSON-safe technical continuation

## Goal

Complete the user-requested measurement-engineering study and, only after two held-out technical validations pass, run the mechanically unchanged scientific atlas. Attempt 9 must preserve attempt 8 as a signed terminal, reuse no attempt-8 cache as a successful result, disclose its valid signed EWT staging bundle as opened calibration history, diagnose RoPE numerics on EWT only, and never train a neural model.

## Context

Attempt 8 recorded only the EWT calibration grid. It then signed `TERMINAL_EWT_CALIBRATION_INVALID` with `no_retry_authorized=true` because `write_signed()` compared the JSON-reloaded list representation against the original tuple-containing Python payload after already writing a cryptographically valid completion. Independent adversarial review confirmed both that serializer defect and a second prespecified stop: EWT required absolute tolerance `1.3512020111083984e-05`, beyond the frozen `8e-06` grid maximum. No fresh-GUM or GENTLE model call/artifact is recorded and their required output roots are absent; this is not proof against an unlogged historical invocation.

The exact attempt-8 terminal, staging tree, authorization, implementation candidate/review, and prescore evidence are immutable historical inputs. Attempt 9 is a new protocol and namespace, not an attempt-8 retry or promotion.

## Constraints

- Never modify, promote, rename, delete, or rerun any attempt-8 artifact or guarded stage.
- Treat attempt-8 EWT staging as explicitly opened calibration history only. It may be independently verified and imported by hash; it is never called an attempt-8 PASS.
- Do not reuse attempt-8 arrays as held-out data, a validation result, or a new score-bearing forward.
- Do not open fresh GUM or GENTLE before a new signed validation freeze and independent `/adversarial SHIP`.
- Keep the v3.4 metric formulas, `rtol=5e-6`, safety factor `1.25`, relative-L2/cosine grids, cell budgets, panels, batch order, runtime contract, sentinel contract, and sequential held-out gates unchanged.
- The only threshold-grid change is to append absolute-tolerance cap `2e-05`, the smallest calibration-selected and validation-preregistered new cap above `1.25 × 1.3512020111083984e-05 = 1.689002513885498e-05`. Reports retain both the old grid and expanded grid and never describe `2e-05` as pre-calibration.
- Diagnostic values remain descriptive and cannot tune thresholds.
- No neural training, optimizer, scheduler, backward call, parameter update, checkpoint, or technical label/estimator use.

## Approach

1. Fork unsigned attempt-9 implementation/config/test/adapter paths without editing attempt-8 inventory files. Normalize payloads to strict JSON, verify the exact temporary bytes and signature, then atomically create the destination with a same-filesystem hard-link no-clobber operation (`os.link`) that fails on any existing final path. Make library-attestation outputs explicitly JSON-native.
2. Add no-model regression coverage for nested tuples/nonempty library extras, injected verification failure leaving no destination, collision/no-overwrite behavior, valid exactly-once promotion, post-link corruption hard-stop behavior, terminal-before-model-load enforcement, and a synthetic complete grid bundle with a realistic runtime attestation. Implement, test, semantic-diff audit, and inventory the unchanged-science adapter now, before validation. Build and independently rebuild the new label-only prescore under attempt-9 namespaces; mark EWT calibration history as opened and state only that no validation artifacts/model calls are recorded and required roots are absent, with no claim about unlogged historical invocations.
3. Obtain unsigned implementation `/adversarial SHIP` binding the implementation, adapter, prescore, and rebuild. Only then use the repaired signer to create the first signed attempt-9 artifact: retirement/provenance binding the exact attempt-8 terminal and complete run/input lineage.
4. Independently verify the attempt-8 staging signature, exact child inventory, row IDs/order, arrays/dtypes/shapes/finite values, exact cached replay, three byte-identical live references, grid metrics, and raw-cap inputs. Produce a signed attempt-9 `VERIFIED_OPENED_CALIBRATION_HISTORY` import artifact binding both the attempt-8 terminal and staging completion, stored outside all promoted calibration-cache paths.
5. Derive caps mechanically from retained attempt-7 EWT plus imported attempt-8 EWT and sign an immutable calibration-cap candidate before any diagnostic forward. The expanded grid must select `atol=2e-05`; any other result terminalizes attempt 9.
6. Authorize and run only the separate EWT diagnostic unhooked/hooked/observer comparison. Locate propagated pre-Q/K, local rotary, aligned post-Q/K, invariant-logit, and hidden-state residuals; do not use them in caps. Diagnostic authorization and completion bind the pre-diagnostic cap-candidate hash.
7. After diagnostic PASS, obtain a fresh validation-freeze `/adversarial SHIP`. The freeze binds the already-reviewed science adapter and unchanged semantic allowlist, then authorizes fresh GUM sentinel/grid once and, only on GUM PASS, GENTLE once. Any failure terminalizes attempt 9 with no retry.
8. Only dual validation PASS unlocks execution of the already-frozen mechanically unchanged scientific atlas adapter. Run no neural training.

## Milestones

### M1 — Unsigned repair and implementation review

- [ ] Create attempt-9-only signer, technical runner, diagnostic, config, tests, and unchanged-science adapter without signing or model inference.
- [ ] Implement strict JSON normalization, pre-link signature verification, atomic hard-link no-clobber creation, JSON-native library results, and fail-closed collision/corruption behavior.
- [ ] Implement and inventory the unchanged-science adapter and semantic allowlist before any validation result exists.
- [ ] Build the attempt-9 label-only prescore twice byte-identically before review; record opened EWT calibration history and bounded absence claims for held-out artifacts.
- [ ] Obtain implementation `/adversarial SHIP` before the first attempt-9 signature.

Acceptance: attempt-8 remains byte-identical; synthetic/CPU and fault-injection tests pass; reviewer binds the exact unsigned candidate inventory; zero attempt-9 signed artifacts or model calls exist before SHIP.

### M2 — Retirement, prescore, import, and pre-diagnostic cap freeze

- [ ] As the first signed attempt-9 artifact, retire attempt 8 with a recursive allowlist of its complete run tree plus every external candidate-bound/config/authorization/review input; enumerate required-absent promoted calibration, diagnostic, freeze, validation, and science paths; reject extras and record the unlogged-invocation caveat.
- [ ] Verify/import the terminal-plus-staging bundle under distinct status `VERIFIED_OPENED_CALIBRATION_HISTORY`, never into a promoted cache path.
- [ ] Derive and sign the calibration-cap candidate selecting `2e-05` before diagnosis; retain old/expanded grids and exact arithmetic.

Acceptance: attempt-8 retirement/input inventory is exact and bounded; new prescore has exact counts/support; calibration import independently recomputes; cap-candidate exists before all diagnostic outputs; held-out roots remain absent.

### M3 — EWT diagnosis

- [ ] Sign EWT-diagnostic-only authorization binding the pre-diagnostic cap-candidate and exact implementation inventory.
- [ ] Run EWT diagnostic unhooked and hooked in separate processes and require byte-identical observer outputs.

Acceptance: signed calibration-import and diagnostic PASS artifacts exist; validation roots remain absent.

### M4 — Held-out freeze and validation

- [ ] Create a validation freeze that binds the pre-diagnostic cap candidate, diagnostic PASS, exact implementation inventory, and pre-reviewed science adapter/semantic allowlist.
- [ ] Obtain freeze `/adversarial SHIP`, then sign validation authorization.
- [ ] Run exact GUM sentinel/grid once; only on PASS run GENTLE once.

Acceptance: both sources independently PASS or a signed terminal stops the study; no pooling, redraw, retry, or post-opening threshold change.

### M5 — Already-frozen unchanged atlas and reviews

- [ ] Only after dual validation PASS, authorize and run the already-reviewed same scientific atlas adapter in a fresh namespace.
- [ ] Run research claim review plus final `/adversarial` review; report technical and scientific missingness separately.

Acceptance: claims bind exact artifacts; no training is authorized or run.

## Definition of done

- [ ] Attempt 8 remains a signed, immutable, no-retry terminal and is never promoted.
- [ ] Exact replay, repeated live inference, approximate equivariance, and EWT diagnostic evidence are separately verified and reported.
- [ ] The serializer cannot leave a final signed artifact before successful verification.
- [ ] The expanded tolerance is calibrated only from disclosed EWT history, labeled calibration-selected/validation-preregistered, and frozen before diagnosis and GUM/GENTLE.
- [ ] Fresh GUM and GENTLE each pass every frozen gate, or attempt 9 terminalizes.
- [ ] The scientific atlas runs only after dual PASS through a reviewed unchanged adapter.
- [ ] No neural training, checkpoints, or technical label/estimator path occurs.
- [ ] Implementation, freeze, result, claim, and adversarial reviews are retained.

## Verification plan

- `check-plan` and `/adversarial PLAN_ATTEMPT9.md` until `SHIP` before implementation.
- Exact recursive SHA-256 inventories for attempt-8 retirement and attempt-9 prescore/rebuild.
- `py_compile`; attempt-9 synthetic/CPU tests; all 44 attempt-7 regressions; static forbidden-training scan.
- Fault-injection tests around signing temporary-file verification, atomic hard-link no-clobber creation, collisions, and post-link corruption terminalization.
- Independent recomputation of attempt-8 EWT staging arrays, rows, repeats, score cells, and cap inputs.
- Runtime preflight before every neural forward and runtime postflight comparison.
- Fresh `/adversarial SHIP` on the complete unsigned implementation including the science adapter, then on held-out freeze and final claims.

## Risks and one-way doors

- **Attempt-8 contamination:** any mutation or promotion would invalidate the audit. Mitigation: read-only hash binding and distinct paths.
- **Tolerance overfit:** EWT is now opened calibration. Mitigation: freeze the single calibration-selected `2e-05` extension before diagnosis and validation; do not use diagnostics or held-out outcomes to tune.
- **Held-out opening:** irreversible. Mitigation: exact implementation/freeze inventories, signed authorization, GUM-first order, and no retry.
- **Serializer partial success:** a write error can create ambiguous evidence. Mitigation: verify exact bytes/signature in a same-directory temporary, fsync it, atomically hard-link to a nonexisting destination with `os.link`, fsync the directory, verify the final path is the same inode/size/hash as the already-verified temporary, then remove the temporary link. Collision never overwrites. Any post-link identity mismatch creates a separate no-clobber `SIGNING_FAULT.json` hard-stop with `O_EXCL`, preserves both paths for audit, and every controller stage refuses to continue.
- **Diagnostic observer effects:** mandatory hooked/unhooked byte equality; any mismatch terminalizes before validation.
- **Scientific drift:** bind and import the byte-frozen scientific functions, require semantic-diff allowlist and regression tests.

## Deviations log

- 2026-08-03: Initial attempt-9 amendment drafted after the signed attempt-8 EWT terminal and post-failure adversarial `BLOCK`. No attempt-8 retry, held-out activation opening, or training was performed.
- 2026-08-03: First attempt-9 plan review returned `BLOCK`. Reordered the first signature after unsigned serializer/adapter review; froze the calibration-selected cap before diagnosis; replaced overwrite-capable replacement with preverified atomic hard-link no-clobber signing and a `SIGNING_FAULT` hard stop; moved science-adapter implementation/review before validation; made retirement/absence/import contracts exhaustive and bounded; and corrected calibration-selected terminology.
- 2026-08-03: Second attempt-9 plan review returned `SHIP`. Implemented attempt-9-only code, tests, science adapter, runtime probe, and twice-byte-identical label-only prescore without signing, loading model weights, running a neural forward, or opening held-out artifacts. Attempt 8 remains byte-unchanged and terminal.
- 2026-08-03: First unsigned implementation review returned `BLOCK` on candidate `cc16ea8fc13beb2bf2afcdf7b331f499e0db86c4d7e02eba30e94871988b1777`. Archived that unsigned candidate without creating the attempt-9 run root or any signature/model call. Rejected EWT grid execution even with populated caps; replaced the post-validation all-coordinate QA bridge with exact frozen-budget signed-score translation; restored exact attempt-7 panel/family segmentation; added the missing bridge regressions and exact science-cache child inventory check; then prepared a replacement candidate for re-review.
- 2026-08-03: Withdrew and archived replacement candidate `44ac6b12dd93b4efdeab369f85e4368222a295fc42d4257d1f8a7cd4b919be51` before review/signing after a local pre-review audit found that the imported attempt-8 bridge passed its expanded 1,200-row reference to the 200-row `score_grid` interface. Corrected the call to use the exact 200-row base reference and added an end-to-end imported-history bridge regression. No model call or signed attempt-9 artifact occurred.
- 2026-08-03: Follow-up review `BLOCK`ed candidate `295ac69a9eb70dce82dafa4a365b3763501a839b6544a26d8775512fc29f7099` for a reported plan-hash mismatch. The quoted `37901fc3…` hash was in fact from the already archived `44ac…` candidate, while both the reviewed `295ac…` inventory and its report contained current plan hash `0f9646c9…`. Nevertheless, archived `295ac…` unsigned and adopted the stronger fail-closed requirement: candidate creation and verification now reject unless the report's full implementation-hash map exactly equals the candidate inventory, with a regression test. No attempt-9 signature, run root, or model call existed.
