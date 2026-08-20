VERDICT: BLOCK
ONE-LINE: Attempt 8 is terminal; the tuple/list bug is real, and its calibration is independently out-of-grid.

BLOCKERS
  - [critical] `pilot_runs/20260803_atlas_rope_technical_v4/TERMINAL.json` — the valid signed payload declares `TERMINAL_EWT_CALIBRATION_INVALID` and `no_retry_authorized=true`.
    reasoning — `scripts/run_atlas_rope_v4.py:93-96` rejects every guarded attempt-8 stage when this terminal exists. The exception occurred before `promote()` at `scripts/run_atlas_rope_v4.py:561`, leaving the completion only under staging.
    impact — retrying, manually promoting staging, freezing thresholds, opening validation, or authorizing science in attempt 8 would violate the signed terminal and prespecified controller.
    fix — preserve the terminal and staging tree byte-for-byte. Any repair must use a new attempt namespace, prescore, implementation inventory, authorization, and adversarial review. The staging evidence may be retained for postmortem or explicitly disclosed future calibration, but never promoted or represented as a successful attempt-8 bundle.

  - [high] `scripts/atlas_rope_v4.py:198-204,839-852` — the proposed serialization diagnosis is correct.
    reasoning — `verify_library_attestation()` constructs tuple-valued `missing_required`, conflict entries, and `extra_observed`. `write_signed()` serializes those tuples as JSON arrays, then compares the reloaded list-valued payload against the original tuple-valued payload. The signed staging bundle has nonempty `extra_observed`, so signature verification succeeds while Python structural equality fails.
    impact — a valid signed artifact is durably written before `write_signed()` raises, producing an ambiguous partial-success state and terminalizing otherwise valid execution.
    fix — in the new attempt, normalize the payload through strict JSON serialization before signing and comparison. Verify the serialized temporary artifact before atomically promoting it to the final path; a failed pre-promotion verification must leave no final artifact. Prefer also making `verify_library_attestation()` return JSON-native lists explicitly.

  - [critical] `pilot_runs/20260803_atlas_rope_technical_v4/staging/minimal-EWT_calibration-67f720a9b43d-2654766/COMPLETE.json#/payload/score/raw_cap_inputs` — the calibration is scientifically ineligible independently of the signing bug.
    reasoning — the signed bundle reports `required_atol=1.3512020111083984e-05`, while the frozen grid ends at `8e-06`; consequently `caps.atol=null` and `status=INELIGIBLE`. `scripts/run_atlas_rope_v4.py:795-800` would terminalize the attempt when the EWT union remains outside the frozen grids.
    impact — fixing serialization and rerunning unchanged would not make this protocol eligible. Treating the failure as merely administrative would conceal a second, substantive stop condition.
    fix — do not rerun unchanged. A new prescore must explicitly incorporate attempt-8 EWT as opened calibration history and either preregister a justified expanded grid before any still-unopened validation or conclude that this technical test is infeasible. Threshold changes require a new attempt and cannot be backported to attempt 8.

REVISIONS
  - [medium] `tests/test_atlas_rope_v4.py:288-325` — signing tests do not exercise JSON round-tripping of nested tuples or nonempty library extras.
    reasoning — the retirement test reads an already-JSON-native artifact, the terminal test replaces `write_signed()` with a stub, and the library test checks only PASS/FAIL status.
    impact — the exact production failure passed the implementation suite.
    fix — add an ephemeral-key round-trip test with nested tuples and nonempty `extra_observed`; assert the persisted payload equals its JSON-normalized form and verifies cryptographically.

  - [medium] `scripts/atlas_rope_v4.py:198-205` — post-write failure behavior lacks a regression test.
    reasoning — current verification occurs only after `atomic_json()` has replaced the destination.
    impact — future serialization or verification faults can again leave apparently failed yet valid create-once artifacts.
    fix — test that malformed/non-serializable or failed-verification payloads never create the final path, while a valid normalized payload is verified before atomic promotion.

  - [medium] `tests/test_atlas_rope_v4.py:298-315` — terminal testing checks payload construction but not controller enforcement.
    reasoning — it monkeypatches `write_signed()` and never exercises `_assert_not_terminal()` or model-load prevention.
    impact — a later stage could accidentally bypass terminality without failing this test.
    fix — add parameterized tests proving every attempt stage rejects a valid terminal before model loading, forward execution, signing, or promotion.

  - [medium] `scripts/run_atlas_rope_v4.py:502-562` — the repaired path needs a no-model end-to-end promotion test.
    reasoning — unit-level signing normalization alone would not demonstrate that a runtime attestation containing nonempty extras survives bundle writing, verification, and promotion exactly once.
    impact — the same type-boundary defect could remain in another nested bundle field.
    fix — use synthetic arrays and stubbed forwards/runtime attestations to exercise completion writing and promotion without loading weights or running neural inference.

NITS
  - `scripts/atlas_rope_v4.py:839-852` — annotate the attestation result as JSON-native data rather than returning tuple-containing `dict[str, Any]`.

CHECKS RUN
  - Exact terminal inspection and `verify_envelope()` → signature valid; status `TERMINAL_EWT_CALIBRATION_INVALID`; `no_retry_authorized=true`; SHA-256 `3e152d2f5397d805af53a3ab7e358275990bbf4881b30f3706ad3e1a2901f180`.
  - Staging `COMPLETE.json` inspection and `verify_envelope()` → signature valid; status `COMPLETE`; SHA-256 `cb258db29525c444b4a2b451521365e3e6932413da4ca8b2f22273658d67081a`.
  - Staging child audit → all six declared files matched exact byte counts and SHA-256 hashes.
  - JSON type inspection → persisted `required_library_check.extra_observed` entries are lists; source construction uses tuples.
  - Static controller inspection → terminal check precedes guarded stages; failure occurs before staging promotion.
  - No model inference, signing, mutation, promotion, training, git, or network operation was performed.

CONTRACT COVERAGE
  - Diagnosis explains the raised exception → met — tuple-to-list JSON normalization makes the post-write Python equality false.
  - Signed artifact integrity → met — both terminal and staging completion independently verify; staging children match.
  - Attempt-8 no-retry enforcement → met — signed terminal plus `_assert_not_terminal()` forbid continuation.
  - Attempt-8 promotion or scientific use → unmet — staging was never promoted and its calibration is out-of-grid.
  - Fail-safe signed-write semantics → unmet — final artifact replacement precedes post-write verification.
  - Unchanged frozen-threshold eligibility → unmet — required absolute tolerance exceeds the frozen grid maximum.
  - Regression coverage for the production failure → unmet — no JSON-roundtrip, pre-promotion failure, or terminal-before-model-load test exists.
  - Fresh new-attempt path → partial — GUM/GENTLE activations remain unopened, but a new prescore and authorization chain are required before using that remaining firewall.

UNKNOWNS
  - The numerical mechanism producing the `1.3512e-05` required tolerance was not diagnosed here.
  - No claim is made that a widened threshold grid would validate on GUM or GENTLE.
