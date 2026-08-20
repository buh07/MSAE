VERDICT: SHIP
ONE-LINE: The immutable recovery freeze closes v6’s dependency hole without scientific, lineage, or launch drift.

BLOCKERS        (must fix before proceeding; empty if none)

REVISIONS       (should fix; not blocking)

NITS            (optional, cap at 5)

CHECKS RUN
  - `sha256sum configs/behavioral_endpoint_v6_1/FREEZE.json` → exact required SHA256 `df66957ca97e05dc963b606bd428bc84cc9aada19fb2da9964e76cebf5eb741e`.
  - Independent v6.1 inventory audit → 45 unique sorted paths; 45/45 byte counts and SHA256 hashes matched; canonical hash matched `044530b0af70125f2ddcf234fc3920f7b90c3045973f352ca643001305893674`.
  - Independent invalidated-v6 audit → exact freeze hash `02acbb…`; 33/33 inventory entries and canonical hash matched; bound review hash `9e0063…` begins `VERDICT: BLOCK`.
  - Independent v5 audit → 47/47 preservation entries and nested 23/23 freeze entries matched; each confirmation directory contains only `BLOCKED.json`.
  - Independent prepared/cache audit → 12/12 internally registered prepared hashes matched; all 21 cached assets across three pinned revisions matched.
  - Independent normalized config and AST comparison → configs equal after permitted recovery/path normalization; all 49 non-lifecycle function ASTs equal.
  - Independent recursive AST-import audit → seven-file closure includes v5→v4.1 and v3/v4.1→proxy1/proxy2.
  - `bash -n scripts/launch_behavioral_endpoint_v6_1_tmux.sh` → PASS.
  - Namespace/session audit → configured output and run-provenance roots absent; no v6/v6.1 tmux sessions found.
  - AST parsing of all seven frozen local executable dependencies → PASS.

CONTRACT COVERAGE
  - Exact immutable v6.1 freeze → met — `configs/behavioral_endpoint_v6_1/FREEZE.json:1` has the required digest, exact 45-file inventory, and matching canonical inventory hash.
  - Candidate review is SHIP → met — `reports/adversarial/behavioral_endpoint_v6_1_candidate_review.md:1` is `VERDICT: SHIP`, and its frozen hash matches.
  - Invalidated v6/BLOCK lineage → met — `configs/behavioral_endpoint_v6_1/run.json:375-378` binds the exact v6 freeze and BLOCK review; every old inventory entry reverified.
  - Scientific configuration and function equivalence → met — normalized configs compare equal and `scripts/behavioral_endpoint_v6_1.py:253-267` preserves all 49 non-lifecycle function ASTs.
  - Recursive executable dependency closure → met — `scripts/behavioral_endpoint_v6_1.py:269-296` resolves and freezes all seven local modules, including every required v5/v4.1/proxy edge.
  - V5 preservation, prepared rows, and cache → met — 47 preserved files, 23 nested freeze entries, 13 frozen prepared artifacts, and 21 cache assets match exact hashes.
  - Confirmation firewall and family barrier → met — `scripts/behavioral_endpoint_v6_1.py:360-374` gates each endpoint/model before loading; `configs/behavioral_endpoint_v6_1/run.json:215` retains the two-family threshold.
  - One-shot paths and review gating → met — `scripts/launch_behavioral_endpoint_v6_1_tmux.sh:22-45` requires both SHIP reviews, exact frozen-review binding, absent namespaces, preflight, and freeze verification.
  - Fifteen-job UUID-pinned launcher → met — `scripts/launch_behavioral_endpoint_v6_1_tmux.sh:37-96` defines six development workers, six confirmation waiters, two gates, and one final aggregator across six distinct sub-4-GiB UUIDs.
  - Runtime GPU mapping guard → met — `scripts/launch_behavioral_endpoint_v6_1_tmux.sh:47-72` records and rechecks physical-index/UUID mappings; `scripts/behavioral_endpoint_v6_1.py:318-325` rejects remapping.
  - No training or representation benchmark → met — launcher invokes only behavioral workers/gates/final; config and freeze deny both, and the endpoint execution path contains neither training nor representation methods.
  - Output/provenance namespace absence → met — `results/behavioral_endpoint_v6_1_20260809` and `reports/provenance/behavioral_endpoint_v6_1_run_20260809` do not exist.

UNKNOWNS
  - This read-only review was not persisted or hash-bound; the maintainer must store this exact report and create the required binding before launch.
  - Current launch-time GPU availability cannot be known until invocation; no model forward or tmux launch was attempted.
