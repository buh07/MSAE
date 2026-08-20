VERDICT: SHIP
ONE-LINE: R4.2 fixes the rejected lock contract while preserving exact scientific, payload, and recovery lineage.
BOUND_SHA256: 75bbb7b00b9c18d41ea5a6d7ec26aef7798d1f1e4ae2c04bf5e81f0fd5e258d6

BLOCKERS
  - None.

REVISIONS
  - None.

NITS
  - None.

CHECKS RUN
  - Exact SHA-256 verification → freeze, plan, config, source, tests, launcher, candidate, candidate review, generator lock, R4/R4.1 preservation, R4 freeze, R5 lineage, and checkpoints matched.
  - `python -B scripts/trained_copy_method_benchmark_v1_r4_2.py verify-freeze --opaque` → PASS for the exact freeze.
  - Independent metadata audit → candidate SHIP syntax, recovery semantics, scientific parity, opaque payload parity, audit parity, and checkpoint hashes passed.
  - Launcher/worker integration probe → both accepted `msae_trained_copy_methods_v1_r4_2_${uuid}.lockdir`; mocked `gpu_validate` completed.
  - Procfs parser probe → hostile names containing spaces and `)` plus live `/proc/self/stat` passed.
  - `bash -n scripts/launch_trained_copy_method_benchmark_v1_r4_2_tmux.sh` → PASS.
  - Exact absence checks → R4.2 output, provenance, log, review binding, frozen review, tmux session, and GPU lock absent; rejected R4.1 launch namespaces also remain absent.
  - No JSONL payload was opened, read, statted, globbed, or hashed; checkpoints were byte-hash validated only and never loaded.

CONTRACT COVERAGE
  - Exact executable/candidate/review/lock lineage → met — `FREEZE.json:2-7,364,383-385`.
  - Candidate adversarial SHIP → met — exact review hash and unique candidate-bound SHIP line verified.
  - R4 failure preservation → met — `FREEZE.json:365-366`; preserved terminal remains pre-access and non-retryable.
  - R4.1 rejected preservation → met — `run.json:378-379`, validated at `trained_copy_method_benchmark_v1_r4_2.py:55-65`; preservation records `launched=false` and unopened at `PRESERVATION.json:60,418-419`.
  - Scientific parity → met — all scientific configuration matches R4 after excluding recovery, namespaces, and schemas; method-table hash is unchanged.
  - Three opaque payload records → met — `FREEZE.json:175-359`; stage, byte count, hash, and audit metadata exactly match R4 and preserved R4.1 records.
  - Payload unopened state → met — `FREEZE.json:363` and prepared metadata are false.
  - Lock-contract repair → met — launcher line 16 and worker source line 456 use the identical R4.2 basename.
  - Procfs parser repair → met — final-`)` parsing at source lines 44-53 is tested against hostile and live records.
  - One-shot tmux/GPU behavior → met — atomic UUID lock, free-GPU recheck, fixed session, timeout, token check, PID/UUID ownership, ancestry verification, and namespace guards remain integrated.
  - Prelaunch namespace absence → met — configured paths/session/lock at `run.json:400-408` were absent.

UNKNOWNS
  - Opaque payload contents and recorded hashes were intentionally not independently verified.
  - Actual GPU/tmux execution remains deferred to the irreversible one-shot launch.
