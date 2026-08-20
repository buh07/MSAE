# VERDICT

**BLOCK**

# ONE-LINE

The estimators and live GPU-lease handoff are substantially improved, but the frozen signed-provenance contract is not actually enforced and the aggregation path can publish `COMPLETE.json` without the RFC's independent terminal validation/lock, while launch/recovery has failure windows that can strand the create-once run.

# BLOCKERS

1. **The signed provenance gate does not bind the accepted artifacts to the exact current configuration or to the preregistered reviewer evidence.** The builder payload contains `config_sha256` (`scripts/msae_measurement_v2_run.py:655-660`), but neither `verify_signed_builder` nor `prepare_data` compares it with the current config (`scripts/msae_measurement_v2_run.py:689-746`), and `verify_prepared` repeats the same omission (`scripts/msae_measurement_v2_run.py:820-838`). Thus a previously valid builder/reviewer pair can be replayed under a changed scoring config when grouping code/reconnaissance remain unchanged. The config freezes only the reviewer key and task identity (`configs/atlas_measurement_v2/run.json:158-162`), not the builder-key fingerprint or dispatcher transcript digest required by the RFC (`docs/rfc-atlas-v2-execution.md:147-165`). The verifier merely accepts syntactically valid transcript/diff digests from the signed payload and never compares either to a frozen expected artifact (`scripts/msae_measurement_v2_run.py:703-730`). The payload also omits the promised Git revision (`scripts/msae_measurement_v2_run.py:655-671`). Consequently `signed_grouping_provenance: eligible` is stronger than what was verified (`scripts/run_msae_measurement_v2.py:787-790`). **Required fix:** pin and verify builder fingerprint, exact current config SHA, transcript/diff evidence, Git revision, and distinct identities before preparation or inference.

2. **`aggregate` is not the independent M6 terminal validator and can certify a semantically inconsistent result.** It checks selected hashes, then copies the stored analysis decision into the report and terminal marker (`scripts/run_msae_measurement_v2.py:801-853`). It never acquires the required terminal-state lock; enumerates/rejects extra or missing stage/job/shard IDs; validates job terminal records, schemas, endpoint reason/value consistency, or final environment/runtime; or independently recomputes the frozen eligibility/outcome truth table. In particular, it does not compare the analysis/analysis-complete `config_sha256` fields with the current config before accepting their content (`scripts/run_msae_measurement_v2.py:811-829`). Its single early `FAILED`/`ABANDONED` check is not locked against terminal-state races (`scripts/run_msae_measurement_v2.py:801-805`). This is materially short of the explicit M6 contract (`docs/rfc-atlas-v2-execution.md:442-453`) and can turn an internally hashed but semantically invalid `results.json` into `COMPLETE.json`. **Required fix:** implement one locked, fail-closed terminal validator that validates exact expected IDs and schemas, re-derives the decision, rehashes all inputs/outputs, records final runtime lineage, and atomically wins exactly one terminal state.

3. **Fresh launch and recovery can permanently strand the create-once run, and recovery does not authenticate committed stages before takeover.** Fresh mode creates the run root before `tmux new-session`; if tmux creation or coordinator startup fails, later fresh launch refuses the directory while recovery/abandonment require `owner.json` (`scripts/launch_msae_measurement_v2_tmux.sh:27-46,79-81`). Recovery similarly moves `owner.json` away before creating the replacement tmux session (`scripts/launch_msae_measurement_v2_tmux.sh:70-77`), so failure in that window leaves no supported recovery path. Before takeover it runs only generic validate/prepare and checks live child PID ticks plus temporary names (`scripts/launch_msae_measurement_v2_tmux.sh:44-69`); it does not validate every committed raw/transform/analysis stage, exact job namespace, command hashes, or recorded lock-file/FD identity as required by the frozen recovery contract (`docs/rfc-atlas-v2-execution.md:350-366`). **Required fix:** retain a recoverable authenticated owner/pending-attempt record until the new coordinator atomically claims ownership, support pre-owner launch failure, and validate the full committed-stage/job inventory before archival/takeover.

# REVISIONS

1. **Prepared/cache verification remains self-authenticating at its root.** `verify_prepared` trusts role/file hashes stored in the mutable prepared manifest rather than reconstructing and comparing the signed source-to-prepared contract (`scripts/msae_measurement_v2_run.py:820-845`); generic cache reuse likewise checks only hashes stored in the cache itself (`scripts/msae_measurement_v2_run.py:848-879`). Later raw/transform validators add useful expected lineage, but the prepared root should be independently regenerated/validated from signed provenance or its manifest digest should itself be frozen by trusted provenance before neural output can depend on it.

2. **The explicit M2/M3 evidence gate is incomplete.** The focused execution test file covers pairing, bootstrap mechanics, macro-F1 missing classes, intervals, one value-cache tamper, parsing, partial residual rank, cached no-op, and whole-group splitting (`tests/test_msae_measurement_v2_run.py:52-147`). It does not contain the RFC-required fake-model smoke extraction/fail-closed marker tests or numeric fixtures for ridge alpha/ties, recovery denominators, specificity margins/missingness, full/delta/partial CKA, terminal aggregation, recovery, FD-200 lifetime, or a CPU synthetic end-to-end report (`docs/rfc-atlas-v2-execution.md:409-422`). These are precisely the areas where independent terminal validation is currently weakest.

3. **Environment provenance is incomplete for reproducibility.** `runtime_environment` records Python, NumPy, Torch/CUDA, Git HEAD, and a tracked `git diff` hash (`scripts/run_msae_measurement_v2.py:31-45`), but not actual Transformers/tokenizers/cryptography versions or untracked files; `git diff --binary` does not cover untracked execution inputs. The config hashes a lock file and implementation inventory (`configs/atlas_measurement_v2/run.json:163-172`) but does not verify that the installed environment matches that lock.

4. **GPU analysis determinism has no explicit control or repeat check.** The runner fixes `PYTHONHASHSEED` but not deterministic PyTorch/TF32 behavior (`scripts/msae_measurement_v2_gpu_runner.py:114-115`); ridge eigensolves and CKA run in float32 on CUDA (`scripts/run_msae_measurement_v2.py:259-279`; `scripts/msae_measurement_v2_run.py:926-938`). Extraction has a held-out repeat QA, but threshold-bearing analysis does not. Record deterministic settings or add a tolerance/repeat validation for analysis outputs.

# NITS

1. `stage_validate` reports `inputs_valid: true` after checking only existing public records and checkpoints (`scripts/run_msae_measurement_v2.py:856-860`); rename this to reflect its narrower scope or include source/provenance/prepared/environment validation.
2. The cached no-op test computes the same array slice twice in the same process (`scripts/run_msae_measurement_v2.py:479-488`), so it is useful as a cache-path sentinel but should not be described as independent inference reproducibility.

# CHECKS RUN

- Confirmed the reviewed config SHA-256 is `686b7f420e9d61d57ea1716e07a521698ff1c2815365dbeaeab6e57dee46fed5`; all eight requested target hashes matched the stable handoff inventory.
- Config load plus implementation-inventory validation: **PASS**.
- `.venv-atlas/bin/python -m pytest -q tests/test_msae_measurement_v2.py tests/test_msae_measurement_v2_run.py`: **39 passed**.
- `.venv-atlas/bin/python -m py_compile scripts/msae_measurement_v2_run.py scripts/run_msae_measurement_v2.py scripts/msae_measurement_v2_gpu_runner.py`: **PASS**.
- `bash -n scripts/run_msae_measurement_v2_pipeline.sh scripts/launch_msae_measurement_v2_tmux.sh`: **PASS**.
- `shellcheck`: unavailable.
- No neural experiment, tmux launch, or GPU work was run.

# CONTRACT COVERAGE

- **Scientific scope/estimands:** Static implementation matches the narrowed sampled-earlier document-context construct, exact one-token entity substitution, ordinary group bootstrap, C1 diagnostic/C2 confirmation, recovery ratios, specificity branch/control estimands, and frozen outcome truth table. No adjacency claim was found (`docs/rfc-atlas-v2-execution.md:102-110`; `scripts/msae_measurement_v2_run.py:438-499`; `scripts/run_msae_measurement_v2.py:381-550,761-792`).
- **Probe/CKA:** Common discovery scalers, fixed ridge grid/ties, projection baseline, full/cross-branch CKA, counterfactual-delta CKA, and rank-aware partial residualization are implemented (`scripts/run_msae_measurement_v2.py:259-378,553-699,714-758`). Numeric test coverage remains insufficient.
- **Cache lineage:** Raw and transform reuse validates expected config/model/checkpoint/prepared/row lineage (`scripts/run_msae_measurement_v2.py:91-126`), but the prepared trust root and M6 independent validation remain incomplete.
- **Lease lifetime/cancellation:** Child inheritance of FD 200 and TERM-then-KILL behavior are correctly present (`scripts/msae_measurement_v2_gpu_runner.py:108-150`); sibling cancellation is immediate (`scripts/run_msae_measurement_v2_pipeline.sh:118-135`).
- **Launch handoff:** Fresh handoff validates coordinator state, heartbeat, wrapper/child PID start ticks, child FD 200 targets, and nonterminal status before returning (`scripts/launch_msae_measurement_v2_tmux.sh:109-151`). The pre-owner and recovery transition failures above remain blocking.
- **Aggregation eligibility:** Hash checks exist, but exact shard/schema/semantic/terminal-lock enforcement does not; contract not covered.
- **Provenance:** Cryptographic signature primitives and distinct public keys exist, but exact frozen evidence/config binding does not; contract not covered.

# UNKNOWNS

- The external builder/reviewer envelopes and dispatcher transcript were deliberately not inspected because the requested review scope named exactly eight artifacts; therefore this review does not assert that the current external signatures are absent or invalid, only that the reviewed verifier cannot enforce the stated binding.
- Live tmux recovery, wrapper death, orphan refusal, signal escalation, lock contention, disk exhaustion, and concurrent terminal publication were not fault-injected.
- Numerical behavior on the four configured GPUs and real checkpoint/model caches remains untested by this static review.
