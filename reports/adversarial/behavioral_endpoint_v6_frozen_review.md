VERDICT: BLOCK
ONE-LINE: Two executable local imports are outside every launch-verified manifest, so the freeze is not immutable.

BLOCKERS        (must fix before proceeding; empty if none)
  - [critical] scripts/joint_controllability_benchmark_v3.py:14-15 — `behavioral_endpoint_v6.py:10` imports v3, which imports `proxy_control_benchmark_v1.py` and `proxy_control_benchmark_v2.py`; neither appears in the 33-path freeze inventory nor the 47-file V5 preservation manifest.
    reasoning — Python executes both project-local modules before v6 preflight or freeze verification. `candidate_files()` at `scripts/behavioral_endpoint_v6.py:243-248` omits them, and `verify_freeze()` at lines 266-269 checks only that incomplete inventory.
    impact — either dependency can drift while preflight and `verify-freeze` still pass, violating the one-shot requirement that executable candidate code be hash-bound. A post-freeze blocker permanently invalidates v6.
    fix — create a new versioned candidate and namespace that either removes these transitive imports or includes and launch-verifies both exact files before refreezing and rereviewing.

REVISIONS       (should fix; not blocking)

NITS            (optional, cap at 5)

CHECKS RUN
  - `sha256sum configs/behavioral_endpoint_v6/FREEZE.json` → exact required SHA256 `02acbb51d5c550fc0b6c28a074347ba2b29d3466ae1bfe120bea8671a1782976`.
  - Independent inventory audit → all 33 unique sorted paths matched exact byte counts and SHA256; canonical inventory hash matched `4cd40d…`.
  - Candidate-review audit → `reports/adversarial/behavioral_endpoint_v6_candidate_review.md:1` is `VERDICT: SHIP` and its frozen hash matches.
  - `behavioral_endpoint_v6.py preservation-verify` → PASS; 47 V5 files and the nested 23-path V5 inventory matched, with only `BLOCKED.json` in each V5 confirmation directory.
  - `behavioral_endpoint_v6.py cache-preflight` → PASS for all three pinned revisions and cached asset hashes.
  - `behavioral_endpoint_v6.py preflight` → PASS; reported 33 candidate files, training false, methods false.
  - `behavioral_endpoint_v6.py verify-freeze` → PASS before and after focused tests.
  - Deterministic-preparation audit → all 13 prepared artifacts matched the attestation and freeze; `byte_identical=true`, two preparations.
  - Hostile prepared-row audit → all 1,152 retrieval rows had zero no-binding registered-string leaks; all 1,152 agreement rows satisfied the registered verb formula and all 72 source/template/set cells were exactly balanced.
  - `.venv-atlas/bin/python -m pytest -q -p no:cacheprovider tests/test_behavioral_endpoint_v6.py tests/test_joint_controllability_assay_v5.py` → 36 passed.
  - `bash -n scripts/launch_behavioral_endpoint_v6_tmux.sh` → PASS.
  - Launcher static audit → six distinct UUID requirement, six fixed endpoint/model assignments, same-UUID confirmation reuse, and runtime UUID guards present.
  - Namespace audit → configured output and run-provenance roots absent.
  - Local dependency-closure audit → FAIL; two launch-executed project modules are outside both verified manifests.

CONTRACT COVERAGE
  - Exact frozen inventory contents → met — 33/33 byte/hash matches and canonical inventory hash match.
  - Candidate review is SHIP → met — frozen review artifact line 1 and digest match.
  - V5 preservation and sealed confirmation → met — 47/47 preserved files; three confirmation directories contain only `BLOCKED.json`.
  - Prepared hashes and deterministic preparation → met — 13/13 artifacts match both attestations and freeze.
  - No-binding firewall → met — exhaustive 1,152-row full-prompt audit.
  - Agreement Latin firewall → met — exact formula and balance across 72 frozen cells.
  - Bootstrap, strict boundary, timeout, and outcome firewalls → met — focused oracle and unhappy-path tests pass.
  - Launcher syntax and six-UUID scheduling → met — syntax and static assignment checks pass.
  - One-shot output/provenance absence → met — both configured namespaces are absent.
  - All executable candidate code hash-bound → unmet — v3 imports two unverified project-local modules before launch verification.
  - Safe immutable launch authorization → unmet — the dependency-closure hole invalidates frozen v6 permanently.

UNKNOWNS
  - No model forward, tmux launch, or live GPU allocation was attempted, as required.
