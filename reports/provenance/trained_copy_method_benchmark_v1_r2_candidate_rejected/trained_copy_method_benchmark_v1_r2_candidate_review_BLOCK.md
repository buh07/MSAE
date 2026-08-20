VERDICT: BLOCK
ONE-LINE: Fit omits registered components, rank diagnostics are wrong, and review authorization is bypassable.

BLOCKERS
  - [critical] scripts/trained_copy_method_benchmark_v1_r2.py:65-69 — fit used offsets 1–15 and omitted registered offsets 16–21.
  - [critical] scripts/trained_copy_method_benchmark_v1_r2.py:126-130 — nonlinear Jacobians were concatenated on the wrong axis for controller-output union rank.
  - [critical] scripts/trained_copy_method_benchmark_v1_r2.py:325-332,363-366 — review authorization accepted a `VERDICT: SHIP` substring anywhere in a BLOCK report.
  - [high] scripts/trained_copy_method_benchmark_v1_r2.py:423-434 — lifecycle/artifact/confirmation mutations did not exercise the irreversible boundary strongly enough.

NITS
  - The launcher hard-coded eight hours rather than validating the serialized timeout.
  - Panel audit omitted promised per-block tuple counts.

CHECKS RUN
  - All six supplied hashes matched, including candidate SHA-256 `1a9c70672f64249cff9a3deab61dc66de7ae1de29e2040e57b92df9eb2fd1c90`.
  - Read-only generator probe found fit offsets 1–15 only.
  - Asymmetric Jacobian probe showed the source union rank could be 2 when controller-output union rank was 1.
  - No scientific JSONL payload existed or was opened.

CONTRACT COVERAGE
  - R5 lineage, evaluation crossing, tuple multiplicity, scoring semantics, SAE contracts, durable preconfirmation, and no-retraining scope → met.
  - Complete fit component coverage, nonlinear output-rank diagnostics, canonical review parsing, and hostile lifecycle mutations → unmet.
  - Safe to freeze and launch → unmet.

UNKNOWNS
  - Frozen payload lineage was unavailable because no generator lock or payload existed.
