VERDICT: BLOCK
ONE-LINE: R4.1’s launcher creates a lock basename the worker rejects, so every launch fails before access.

BLOCKERS
  - [critical] scripts/trained_copy_method_benchmark_v1_r4_1.py:453 — worker requires `msae_trained_copy_methods_v1_r4_${uuid}.lockdir`, but launcher creates `msae_trained_copy_methods_v1_r4_1_${uuid}.lockdir` at scripts/launch_trained_copy_method_benchmark_v1_r4_1_tmux.sh:16.
    reasoning — an exact probe using the launcher-produced basename returned `RuntimeError: GPU lock mismatch` before CUDA validation.
    impact — every one-shot R4.1 launch deterministically terminates before payload access, violating the launch-recovery contract.
    fix — preserve this frozen candidate and create a successor using the R4.1 lock basename consistently; add a mocked `gpu_validate` regression test.

REVISIONS
  - None.

NITS
  - None.

CHECKS RUN
  - Exact SHA-256 verification → freeze, plan, config, source, tests, launcher, candidate, candidate review, generator lock, R4 freeze/preservation, R5 lineage, and checkpoint byte hashes matched.
  - `python -B scripts/trained_copy_method_benchmark_v1_r4_1.py verify-freeze --opaque` → PASS for the exact freeze.
  - Independent metadata audit → R4 failure semantics, scientific-config parity, method-table parity, and all three opaque payload byte/hash/audit records matched R4.
  - Procfs parser hostile cases plus live `/proc/self/stat` → PASS.
  - Launcher-compatible lock-name probe against `gpu_validate` → `RuntimeError: GPU lock mismatch`.
  - Exact absence checks → R4.1 output, provenance, log, review binding, frozen review, tmux session, and GPU lock absent.
  - `bash -n scripts/launch_trained_copy_method_benchmark_v1_r4_1_tmux.sh` → PASS.
  - No JSONL payload was opened, read, statted, globbed, or hashed; checkpoints were hash-validated only and never loaded.

CONTRACT COVERAGE
  - Exact executable and review lineage → met — `FREEZE.json:2-7,364,383-385`.
  - R4 failure preservation and terminal semantics → met — `PRESERVATION.json:81-94,450-455`.
  - R4 freeze binding → met — `FREEZE.json:365-366`.
  - Opaque payload parity with R4 → met — `FREEZE.json:175-359`; byte counts, hashes, and audits match R4 metadata.
  - Scientific configuration parity → met — all scientific fields match R4 after excluding recovery, namespaces, and schemas.
  - Procfs parser repair → met — `trained_copy_method_benchmark_v1_r4_1.py:44-53`.
  - R4.1 prelaunch namespace absence → met — configured paths/session/lock at `run.json:398-406` were absent.
  - One-shot tmux/GPU behavior → unmet — launcher/source lock namespaces conflict at launcher line 16 and source line 453.

UNKNOWNS
  - Opaque payload contents and recorded hashes were intentionally not independently verified.
  - Checkpoint semantic contents were intentionally not inspected.
