VERDICT: SHIP
ONE-LINE: R4.2 fixes the lock integration defect while preserving scientific parity, procfs correctness, and isolated one-shot lineage.
BOUND_SHA256: 7bbb4a828c371053717e550ff1a24f85ddac8127e8b4d7ca7332475a38f3c729

BLOCKERS
  - None.

REVISIONS
  - None.

NITS
  - None.

CHECKS RUN
  - Exact SHA-256 verification → candidate, plan, config, source, tests, launcher, R4 failure preservation, and R4.1 rejection preservation matched.
  - Targeted parser/lock tests → 2 passed; mocked `gpu_validate` accepted the exact launcher-compatible R4.2 lock basename.
  - `bash -n scripts/launch_trained_copy_method_benchmark_v1_r4_2_tmux.sh` → passed.
  - Scientific-config comparison against R4 → all scientific fields are exactly equal.
  - Canonical method-table check → unchanged hash `affe6667d4c9adf276b4907fdef23d1d8862355ea9185dd226f7d44f0d216ff2`.
  - Source/config/test/launcher diffs → only recovery lineage, isolated namespaces/schemas, and the lock-contract repair differ from R4.1.
  - No JSONL payload was opened, read, statted, globbed, or hashed; no checkpoint was loaded.

CONTRACT COVERAGE
  - R4.1 lock mismatch → met — launcher and worker both require `msae_trained_copy_methods_v1_r4_2_${uuid}.lockdir`.
  - Procfs ancestry parser → met — final-`)` parsing is unchanged and directly tested.
  - R4.1 rejection binding → met — exact preservation hash and blocked/unlaunched/unopened semantics are validated; config binding propagates through candidate, lock, freeze, and launch.
  - R4 failure binding → met — exact preservation, freeze, and pre-access terminal semantics remain enforced.
  - Scientific parity → met — methods, estimators, thresholds, seeds, panels, model, R5 lineage, and method-table hash are unchanged.
  - Payload parity → met — generated records must match the exact opaque R4 freeze hashes, with prepare/freeze also enforcing byte counts.
  - Executable lineage → met — source, tests, launcher, plan, config, candidate, reviews, and recovery records are transitively hash-bound.
  - Namespace isolation → met — runtime roots, reviews, locks, logs, tmux session, schemas, and launcher paths are R4.2-specific.

UNKNOWNS
  - Live GPU/tmux behavior remains intentionally deferred to the frozen one-shot launch gate.
