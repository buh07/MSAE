VERDICT: BLOCK
BOUND_SHA256: 85c8f17c1f6d89da5c6a121f536c89e0490ecee9b05cd4584d4d283caf39b04c

ONE-LINE: Prior fixes pass, but stale-lock reacquisition can overwrite and delete a live competing owner.

BLOCKERS
  - [critical] scripts/launch_trained_control_next_studies_v1_r2_tmux.sh:45-53 — stale-lock reacquisition ignores failure of the second `mkdir`.
    reasoning — `reserve_lock` is called in an `if`, disabling effective `errexit` inside the function. After moving the stale directory, line 50 executes `mkdir "$d"; acquired=1` without checking success. If another coordinator wins that race, this launcher overwrites its token/owner at line 52 and later deletes its lock.
    impact — violates exclusive GPU ownership and can authorize concurrent experiments on one GPU.
    fix — require `mkdir "$d" || return 1` before setting `acquired=1`; never write metadata unless this invocation’s atomic mkdir succeeded. Add a stale-reacquisition race mock with a live replacement PID and assert its token, owner, and directory survive unchanged.

REVISIONS
  - None.

NITS
  - None.

CHECKS RUN
  - Candidate SHA-256 → matched `85c8f17…`.
  - Protocol parity `--verify` → PASS, SHA `c70d5cf6…`.
  - R1 preservation `--verify` → PASS, SHA `006985fb…`.
  - Shared non-panel suite → `18 passed in 5.29s`.
  - `bash -n` → PASS.
  - Candidate transitive source/config/test/plan/launcher/parity hashes → PASS.
  - Token-generation and metadata-failure tests → PASS.
  - Adversarial stale-reacquisition mock → replacement PID remained live, but its lock was overwritten and deleted.
  - Scientific panels → not accessed.

CONTRACT COVERAGE
  - SAE no-grad and native/matched value preservation → met by exact bound tests.
  - Scientific config/source parity → met.
  - R1 lineage and prior failure preservation → met.
  - Ordinary failure, signal, manifest, PID-remap, and replacement-owner cleanup → met.
  - Token-generation/metadata failure cleanup → met.
  - Atomic stale-lock reacquisition → unmet.
  - Candidate transitive binding → met.

UNKNOWNS
  - The reported 42-test and CUDA passes were not rerun because this review was instructed not to access scientific panels.
  - Superseded 235dfbdd candidate exists, but no filesystem review transcript bound to that exact hash was found; only its supersession record exists.
  - Freeze, lock, and frozen-review artifacts remain pending.
