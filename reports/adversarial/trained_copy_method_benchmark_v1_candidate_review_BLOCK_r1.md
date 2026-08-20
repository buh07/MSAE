VERDICT: BLOCK
ONE-LINE: Repeated sham types, unbound imported code, and non-durable confirmation gating make this candidate unsafe to freeze.

BLOCKERS
  - [critical] scripts/trained_copy_method_benchmark_v1.py:55-84 — the generator does not satisfy the frozen tuple/counterbalance contract: development had 129/192 unique sham tuples, confirmation 125/192, and fit 220/2,048.
  - [critical] scripts/trained_copy_method_benchmark_v1.py:292-298 — development results and fit metadata were not durably written, reread, and reconciled before confirmation access.
  - [critical] scripts/trained_copy_method_benchmark_v1.py:12-13,42-53,209-212 — the imported R5 source was not hash-bound through candidate, freeze, and launch.
  - [critical] scripts/trained_copy_method_benchmark_v1.py:286-300 — timeout, signal, and early technical failures lacked truthful phase-specific terminals.
  - [high] scripts/trained_copy_method_benchmark_v1.py:235-263 — candidate/freeze lineage verification was incomplete and could drift after review.
  - [high] tests/test_trained_copy_method_benchmark_v1.py:16-70 — the test suite omitted mandatory scientific and lifecycle mutations.

REVISIONS
  - [high] scripts/trained_copy_method_benchmark_v1.py:199-206 — reserve structural `not_applicable` for zero; classify collapsed nonzero methods as prediction-incomplete scientific failures.
  - [medium] scripts/trained_copy_method_benchmark_v1.py:187-192 — serialize clean/corrupt accuracy and eligibility exclusions.
  - [medium] scripts/trained_copy_method_benchmark_v1.py:148-160,298 — report full-fit SAE reconstruction, decoded-delta norms, and the complete information-contract table.
  - [medium] configs/trained_copy_method_benchmark_v1/run.json — give the paired SAE selector a distinct paired-donor contract rather than `task_aware`.

CHECKS RUN
  - Exact requested hashes matched.
  - `python -m py_compile scripts/trained_copy_method_benchmark_v1.py` passed.
  - `bash -n scripts/launch_trained_copy_method_benchmark_v1_tmux.sh` passed.
  - `pytest -q tests/test_trained_copy_method_benchmark_v1.py` passed 11 tests, but mutation coverage was incomplete.
  - Candidate manifest inspection confirmed the repeated-sham counts and that no scientific payload existed.

CONTRACT COVERAGE
  - Main tuples/checkpoint hash-before-load/GPU success-path binding/matched-sham norm rule → met.
  - Sham multiplicity, durable authorization, R5 source immutability, truthful failure terminals, strict lineage, and mutation coverage → unmet or partial.
  - Safe to freeze and launch → unmet.

UNKNOWNS
  - No scientific payload existed, so exact freeze payload lineage was not reviewable.
  - Full runtime and SIGTERM behavior were not destructively tested.

This independent review rejected exact candidate manifest SHA-256
`9af7a8e5d4451cbc449a6e02a2039a20d4529e5f7f23649d80adcdcda703b159`.
