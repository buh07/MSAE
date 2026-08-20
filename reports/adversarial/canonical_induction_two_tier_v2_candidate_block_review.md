VERDICT: BLOCK
ONE-LINE: Calibration, authorization, crash closure, lineage, and fail-closed state semantics did not satisfy the frozen protocol.

BLOCKERS
  - Calibration omitted several boundaries and used a circular hook oracle.
  - Confirmation authorization was raceable and did not validate the development gate.
  - Runtime terminals/completions were accepted by existence rather than full lineage.
  - Crash closure and configured timeouts were incomplete.
  - Runtime did not revalidate frozen model-cache bytes.
  - Common-cohort derived finiteness and descriptive counts/missingness were incomplete.
  - V1.1 prepared data were absent from the preservation manifest.
  - A global parser accepted forbidden command flags.
  - The candidate-preflight attestation was absent.
  - Tests did not execute enough hook/state/tamper/CLI failure paths.

REVISIONS
  - Use explicit inference mode and record the CUDA driver.

The candidate was revised with raw/comparator boundary coverage, independent hook arrays and a production-hook toy integration, locked journaled authorization with exact gate recomputation, strict predecessor validators, journal-first crash closure and timeouts, live cache rehashing, common-cohort finiteness plus descriptive counts, complete v1.1 prepared-data preservation, command-specific parsers, a create-once candidate attestation, executable tamper/CLI/hook tests, inference mode, and driver provenance.
