VERDICT: SHIP
BOUND_SHA256: f7d0760dbb9c4fbd07493c25f113150960beca4f34eb511f052f5c86a6ef8047

ONE-LINE: The bridge freeze is byte-identical to R1 scientifically and binds the exact reviewed technical recovery.

BLOCKERS
  - None.

REVISIONS
  - None.

NITS
  - None.

CHECKS RUN
  - Freeze, candidate, candidate-review, generator-lock, payload, prepared-metadata, source/config/plan/tests/launcher/parity, method-table, factorial, and R1-preservation hashes matched.
  - R2 versus R1 payload records and the entire factorial/matrix audit are exactly equal; panel contents were not parsed.
  - Output, provenance, manifest, log, and tmux namespaces were absent.

CONTRACT COVERAGE
  - Exact R1 payload/audit reuse, reviewed-candidate binding, transitive artifact binding, method/factorial binding, no regeneration/semantic access, clean namespace, and launcher authorization: met.

UNKNOWNS
  - GPU availability remains time-varying and must be re-established at reservation time.
