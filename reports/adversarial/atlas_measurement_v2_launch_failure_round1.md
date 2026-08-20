# VERDICT

**SHIP — conditional on the evidence and environment checks below**

# ONE-LINE

This is a bias-independent execution-environment repair before any neural cache or scientific value was committed, so the frozen config/grouping provenance need not be amended or re-signed; recovery may proceed only after the exact CuBLAS environment change and failed-attempt state are durably recorded and verified in the attempt-2 children.

# BLOCKERS

None if every requirement below is satisfied. **BLOCK** if any neural cache/transform/analysis artifact exists, the config/code hash changes, attempt-1 processes remain live, or the exact environment cannot be proven in attempt 2.

# REQUIREMENTS

1. Before recovery, create a create-once run-root amendment for attempt 1 containing:
   - config SHA-256 `852c7ce9f5b4660adf07829335ecf084e4b1ec2d1c8679841cdd082b05fc73e2` and current Git/code inventory;
   - UTC time, exact CuBLAS exception/error-log digests, attempt-1 owner/job/lease/terminal/`FAILED.json` digests, and exit codes;
   - explicit observations that `raw_cache`, `transforms`, and `analysis` have no committed artifacts, all recorded wrapper/child PID-start-time pairs are dead, the tmux session is absent, and configured GPUs are idle;
   - cause and remedy: deterministic PyTorch matmul requires `CUBLAS_WORKSPACE_CONFIG=:4096:8` before interpreter/process start; no threshold, estimator, data, model, checkpoint, seed, or code is changed.
2. Create/start the tmux server, set `CUBLAS_WORKSPACE_CONFIG=:4096:8` in its global environment, and fail closed unless `tmux show-environment -g CUBLAS_WORKSPACE_CONFIG` returns that exact value. Record this output/digest. Be aware this is server-global; ensure unrelated tmux workloads are not unintentionally affected, or use a dedicated server/socket.
3. Invoke only the existing authenticated `scripts/launch_msae_measurement_v2_tmux.sh --recover`. Its current recovery path authenticates the launch/config and failed job history, archives rather than deletes `FAILED`/owner records, and advances the namespace to attempt 2 (`scripts/launch_msae_measurement_v2_tmux.sh:44-87`). Do not manually remove or rewrite attempt-1 records.
4. At live handoff, verify every attempt-2 GPU child's `/proc/<pid>/environ` contains the exact `CUBLAS_WORKSPACE_CONFIG=:4096:8`, alongside the existing PID/start-time/FD-200 checks. Persist a second create-once verification record bound to the amendment and `HANDOFF_READY.json` digests. If children fail before this can be proven, stop and review the new failure rather than iterating environment values.
5. Preserve the amendment and verification records through final claim review. The successful cache lineage already records deterministic-algorithm/TF32 state (`scripts/run_msae_measurement_v2.py:31-40,62-67`), while the amendment supplies the otherwise-unrecorded CuBLAS variable.

# REVISIONS

For a future clean rerun, pin, validate, and record `CUBLAS_WORKSPACE_CONFIG` in the launcher/GPU-runner rather than relying on tmux server state. That would modify the frozen implementation/config inventory and would require a new config SHA and renewed exact provenance review before that future run.

# NITS

Unset the server-global variable after the attempt-2 coordinator has inherited it if the tmux server is shared; record that cleanup. Any later authenticated recovery must set and verify it again before creating the next coordinator.

# CHECKS RUN

- Static review of deterministic setup, environment recording, GPU child inheritance, and authenticated recovery paths.
- No neural, GPU, tmux, or recovery command was run by this reviewer.

# CONTRACT COVERAGE

- `_configure_torch` deliberately enables deterministic algorithms and disables TF32 (`scripts/run_msae_measurement_v2.py:62-67`); the missing CuBLAS prerequisite prevented the intended computation rather than defining an alternative estimand.
- The GPU runner derives each child environment from its parent environment (`scripts/msae_measurement_v2_gpu_runner.py:112-116`), so a correctly configured tmux-owned coordinator propagates the variable without a code change.
- Existing recovery is specifically designed to retain failed attempts and create a namespaced new attempt (`scripts/launch_msae_measurement_v2_tmux.sh:44-87`; `scripts/validate_msae_measurement_v2_terminal.py:314-353`).
- Because attempt 1 committed no neural cache and exposed no scientific endpoint, this repair cannot select among observed results or mix numerical environments within the scored dataset.

# RE-SIGNING DECISION

**No re-signing is required for this recovery as specified.** The grouping reviewer attested to the exact config/Git/grouping artifacts; none changes. The execution amendment documents a prerequisite environment correction before measurement. If any tracked execution code, config, grouping artifact, data selection, or scientific rule is edited, the implementation inventory/config hash changes and the exact builder/reviewer binding must be regenerated and re-signed before relaunch.

# UNKNOWNS

- The stated absence of committed neural caches, dead attempt-1 processes, idle GPUs, and exact observed exception were supplied by the coordinator and must be independently captured in the amendment before recovery.
