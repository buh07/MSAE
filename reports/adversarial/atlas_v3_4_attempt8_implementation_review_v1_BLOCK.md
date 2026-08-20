VERDICT: BLOCK
ONE-LINE: Validation can run code not bound by its freeze, and the frozen stage order still names retired ESLSpok.

BLOCKERS

- [critical] `PLAN.md:143`; `scripts/run_atlas_rope_v4.py:216-221,656-669,678-703,853-904` — held-out validation authorization does not bind or reverify the reviewed implementation candidate.
  reasoning — EWT authorization calls `_verify_implementation_candidate`, but the freeze candidate contains no implementation-candidate SHA/inventory, and the validation authorization branch verifies only the freeze JSON and its review. `_validation_caps`, `run_gum`, and `run_gentle` therefore accept modified runner, diagnostic, or metric code after EWT calibration and freeze review.
  impact — fresh GUM or GENTLE could be irreversibly opened with code different from both the implementation reviewed here and the code that produced calibration. This violates the M5 requirement that authorization bind code/tests and breaks calibration-validation comparability.
  fix — bind the implementation-candidate SHA and complete inventory, EWT authorization SHA, verification-report SHA, and test evidence into the freeze candidate and validation authorization. Call `_verify_implementation_candidate()` from validation authorization verification and again immediately before every held-out model call. Add a test that mutates each reviewed path and proves validation is rejected before inference.

- [high] `configs/atlas_rope_v4/prescore.json:181`; `scripts/run_atlas_rope_v4.py:943-976`; `PLAN.md:101,118-120` — the frozen stage order still specifies `run_eslspok_grid`.
  reasoning — ESLSpok was retired and the runner exposes `run-gentle`, not `run-eslspok`. The exact candidate nevertheless binds a configuration whose declared transition graph omits GENTLE and names a nonexistent retired-source stage.
  impact — the claimed frozen stage transitions are internally inconsistent; an orchestrator following the config cannot execute the reviewed protocol.
  fix — replace `run_eslspok_grid` with the exact GENTLE stage name used by the runner, add an assertion that configured stage order equals the controller’s executable transitions, then regenerate the prescore/rebuild/verification/candidate chain.

- [high] `PLAN.md:51`; `scripts/run_atlas_rope_v4.py:619-650`; `tests/test_atlas_rope_v4.py:1-322` — retained attempt-7 EWT evidence is not independently verified to the frozen semantic contract before determining caps.
  reasoning — `_retained_attempt7_pair` verifies the envelope, child hashes, array names/shapes/dtypes, and repeat equality, but never validates the QA schema, model/revision/layer/runtime fields, 48-row manifest and 72-role expansion, permitted family/panel ordering, parent manifest hashes, or reference/candidate row alignment. No test exercises this path. The signed `qa_rows.json` is hashed but never read.
  impact — the retained arrays are calibration-binding. Treating an authentic cache as semantically correct without reconstructing its row and parent lineage falls short of the plan’s explicit independent verification requirement and can derive thresholds from misinterpreted pairs.
  fix — implement a retained-evidence verifier that checks every frozen QA field, parent hash, row record, role expansion, and reference/candidate alignment before returning arrays; independently recompute current metric inputs from that verified mapping; add corruption tests for each invariant.

REVISIONS

- [medium] `scripts/run_atlas_rope_v4.py:481-509,741-785`; `scripts/diagnose_atlas_rope_v4.py:183-286`; `PLAN.md:196` — full runtime/library/GPU attestation occurs only after all forwards in each bundle.
  reasoning — model SDPA and dtype are checked at load, but GPU UUID, required libraries, package versions, and source/runtime details are attested after score-bearing or diagnostic inference.
  impact — a wrong runtime is terminalized, but only after irreversibly consuming held-out activations.
  fix — perform full attestation immediately after model load and before the first forward, retain a post-run attestation, and test that a preflight mismatch prevents `_forward_units`.

NITS

None.

CHECKS RUN

- `sha256sum configs/atlas_rope_v4/implementation_candidate.json` → `cc62c33e706891de4b980214613ce9de3defd03b8acda3ce1aa183566f0daef5`, exactly matching the requested candidate.
- Exact candidate inventory recomputation → all 11 bound files matched their declared byte counts and SHA-256 values.
- Candidate evidence-binding recomputation → retirement, prescore manifest, rebuild report, runtime probe, source provenance, and verification-report hashes matched.
- `.venv-atlas/bin/python -m py_compile scripts/atlas_rope_v4.py scripts/build_atlas_rope_v4.py scripts/probe_atlas_rope_v4_runtime.py scripts/run_atlas_rope_v4.py scripts/diagnose_atlas_rope_v4.py tests/test_atlas_rope_v4.py` → PASS.
- `.venv-atlas/bin/python -m pytest -q tests/test_atlas_rope_v4.py` → 22 passed.
- `.venv-atlas/bin/python -m pytest -q tests/test_atlas_discovery_v3_3.py tests/test_atlas_discovery_v3_3_implementation.py tests/test_atlas_discovery_v3_3_scoring.py` → 44 passed.
- `/jumbo/lisp/f004ndc/.agent-workspace/bin/check-plan --path PLAN.md` → PASS.
- No-inference `_verify_prescore()` and `_verify_implementation_candidate()` → `PASS_NO_MODEL_CALLS` and `READY_FOR_IMPLEMENTATION_ADVERSARIAL_REVIEW`.
- Prescore rebuild audit → primary and rebuild inventories both `62e32017b07138668e71eff07818843345f8c061655456a48370a8013640f1ad`, with zero mismatched paths.
- Stage-root audit → EWT authorization, calibration, diagnostic, freeze, validation authorization, validation, and science roots were absent.
- No model weights were loaded and no neural forward or experiment was run.

CONTRACT COVERAGE

- M1 attempt-7 retirement and immutable inventory → met — signed retirement and exact tree/binding hashes verify.
- M2 exact rebuilt panels and exposure firewalls → met — byte-identical rebuild, exact panel counts, GENTLE support, and absent validation roots verify.
- Score/row ordering and exact batch schedules → met — canonical reference ordering, aligned row manifests, base-major shift traversal, and `64+36`/`9×64+24` checks are enforced and tested.
- Cached replay, live repeatability, and approximate equivariance separation → met in bundle logic — separate arrays, replay checks, three live references, and separate candidate scoring exist.
- Metric formulas and integer budgets → met — float64 reductions, `atol + rtol*abs(reference)`, zero handling, 30-element/two-row cell budgets, and strict sentinel budgets are tested.
- Fresh-GUM sentinel lineage and non-pooling → met — literal pair order, 16-unit schedules, 24 expanded rows, offsets, per-pair scoring, and digests are enforced.
- Diagnostic Q/K reconstruction and observer validity → met structurally — separate hooked/unhooked paths, fixed Q/K shapes, reconstructed rotations, four residual families, causal logits, and byte-level observer comparison exist.
- Forbidden training/checkpoint paths → met for the frozen candidate — static scan passes, runtime flags forbid training, and exact output allowlists reject checkpoint suffixes.
- Retained-EWT calibration-union verification → unmet — semantic rows and parent lineage are not independently reconstructed.
- Immutable code/tests across validation → unmet — the validation freeze does not bind or reverify the implementation candidate.
- Exact held-out stage order → unmet — frozen config names retired ESLSpok instead of GENTLE.
- Tests would catch the identified failures → unmet — no authorization code-drift, retained-evidence semantic-lineage, configured-stage-order, or pre-forward runtime-guard tests exist.
- Safe to authorize EWT and proceed toward held-out opening → unmet until all blockers and the revision are fixed and a new exact candidate is reviewed.

UNKNOWNS

- Live GPU/runtime behavior, byte-identical repeated inference, and diagnostic observer equality remain intentionally unverified because this review performed no model loading or neural inference.
- No calibration, diagnostic, freeze, or validation result bundle exists yet, so result-level recomputation is outside this implementation review.
- Upstream provenance beyond the locally pinned files and hashes was not network-reverified.
