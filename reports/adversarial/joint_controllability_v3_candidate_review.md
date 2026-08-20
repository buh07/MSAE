VERDICT: SHIP
ONE-LINE: The frozen candidate preserves K2 closure, gates real inference behind controls, and labels its within-corpus and heterogeneous-SAE limits.

freeze_sha256: 395aa2829a4763c972f1381069e0461e6b458f81995e6aad34c41f248a3b1f24

BLOCKERS        (must fix before proceeding; empty if none)

REVISIONS       (should fix; not blocking)
  - [medium] configs/joint_controllability_benchmark_v3/run.json:158 — task projection and DiffMean are estimator-equivalent in this one-factor task.
    reasoning — both reduce to a rank-one paired mean direction.
    impact — they cannot be counted as independent method evidence.
    fix — preserve both registered names but group them as one equivalence class in multiplicity and narrative reporting.
  - [medium] configs/joint_controllability_benchmark_v3/run.json:160 — `public_sae_primary` changes architecture across GPT-2, Pythia, and Gemma.
    reasoning — the releases provide TopK, TopK, and JumpReLU objects respectively.
    impact — replication supports a released-SAE class, not a particular SAE architecture.
    fix — report class-level replication only; keep Pythia architecture variants descriptive.
  - [medium] scripts/joint_controllability_benchmark_v3.py:175 — WIKI_A and WIKI_B share Wikitext-103.
    reasoning — document-disjoint hash partitions are not corpus-independent sources.
    impact — cross-domain language would overstate external validity.
    fix — retain the frozen `within_corpus_transfer=true` and `cross_domain_replication=false` flags and require a later corpus-level confirmation.

NITS            (optional, cap at 5)
  - scripts/joint_controllability_benchmark_v3.py:324 — the ReFT-style comparator is correctly disclaimed as not reproducing ReFT-r1 training; keep this exact label in results.
  - scripts/joint_controllability_benchmark_v3.py:396 — teacher-forced continuation recovery remains descriptive rather than a joint gate.

CHECKS RUN
  - `python -m py_compile scripts/joint_controllability_benchmark_v3.py tests/test_joint_controllability_benchmark_v3.py` → pass before final config label change; rerun required before freeze.
  - `pytest -q tests/test_joint_controllability_benchmark_v3.py` → 6 passed before final config label change; rerun required before freeze.
  - v3 preflight → PASS with 24 pinned public-SAE assets and 14 candidate artifacts before final candidate hash; rerun required.
  - public SAE format smoke → finite encode/decode for all 9 registered SAE objects/layers.
  - label-blind architecture hook smoke → exact zero replay and finite nonzero change for GPT-2, Pythia, and Gemma.
  - prescore audit → 384 rows, 1,152 unique target/donor documents, exact tokenizer prompt lengths, one-token targets.
  - closure SHA-256 → `98b914d177d1ce9989c0c66e00c1434a1ce6c99aeb6ae0dfd2a5466a084d541a`, matching config.

CONTRACT COVERAGE
  - no additional K2 or SAE training → met — config denies both and source contains no training entry point.
  - standard released methods → met — pinned GPT-2 OAI, SAEBench Pythia, and Gemma Scope assets plus linear comparators.
  - natural task with support → met — document-disjoint Wikitext continuation rows, explicitly within-corpus.
  - matched intervention strength → met — 0.25/0.5/1.0 budgets with exact per-row norm matching.
  - causal positive control before model load → met — workers wait for PASS before `from_pretrained`.
  - necessity/sufficiency/collateral/multi-token outcomes → met — component records include each, with multi-token outcome descriptive.
  - supervised skyline prospective → met — closed-form development-only subspace and no model/SAE optimization.
  - output isolation and one-shot lifecycle → met — absent namespace preflight, exclusive terminals, new v3 namespace.

UNKNOWNS
  - Scientific task eligibility cannot be known before the frozen model-forward gate and may validly fail.
  - Wall-clock completion time depends on Gemma worker throughput and is not assessed here.
