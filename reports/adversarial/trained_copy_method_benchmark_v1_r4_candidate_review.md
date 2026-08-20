VERDICT: SHIP
ONE-LINE: R4 closes prior blockers with coherent scientific scoring, complete lineage, durable gating, and fail-closed launch controls.
BOUND_SHA256: f7c2edf62e05443849da390fc76038c8b1f43449d7c1af38a3510de832792b74

BLOCKERS
  - None.

REVISIONS
  - None.

NITS
  - PLAN_TRAINED_COPY_METHOD_BENCHMARK_V1_R4.md:124-127 — says four comparison classes, while the config intentionally defines five by separating `paired_donor_compression`.

CHECKS RUN
  - Exact SHA-256 verification → candidate, source, config, plan, tests, and launcher all matched supplied hashes.
  - Independent method-table hash matched candidate `affe6667d4c9adf276b4907fdef23d1d8862355ea9185dd226f7d44f0d216ff2`.
  - Namespace absence check → no payload, freeze, lock, review binding, output, run provenance, or launcher log existed.
  - Parameter formulas matched instantiated tensors; source/test/launcher/plan/config bind through candidate, lock, freeze, and launch.
  - Scientific inspection covered transforms, both estimands, oracle basis, nonlinear output-union rank, unpaired selectors, and controls.
  - Lifecycle inspection covered durable preconfirmation, access markers, checkpoint drift, UUID/lock/PID ancestry, signals, timeout, and tmux.
  - Host evidence → 26 tests, mutation suite, CPU smoke, and CUDA smoke passed without checkpoint or panel access.

CONTRACT COVERAGE
  - R1-R3 blockers → met.
  - Scientific methods/scoring and irreversible confirmation gate → met.
  - Candidate no-access and GPU/tmux lifecycle → met.

UNKNOWNS
  - Frozen payload lineage and live launch behavior remain intentionally unverifiable until the freeze and launch gates.
