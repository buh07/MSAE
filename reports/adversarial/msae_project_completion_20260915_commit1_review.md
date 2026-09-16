VERDICT: SHIP
ONE-LINE: The 117-path index exactly preserves the bounded calibration control-plane record and its terminal gen9 rejection.

BLOCKERS
  - None.

REVISIONS
  - None.

NITS
  - None.

CHECKS RUN
  - `git diff --cached --name-only` plus an unstaged-path intersection check → exactly 117 staged paths; zero staged/unstaged overlap.
  - Independent reconstruction of `reports/provenance/msae_project_completion_20260915/porcelain_classification.json` → inventory SHA-256 `c40aef57f9a917e7fae403c06a0d965540fd580be8918ff17ad5375843376c55`; exact path-set equality; 117/117 SHA-256, byte-size, and index-mode records match; recomputed logical-commit digest `a1397552d7cd9780873ce7da4babf0ebb8014b20ddf40f417f8f218dc9aaf679` matches the recorded `01_calibration_control_plane` digest and message.
  - `git diff --cached --check` → pass.
  - Exact-index Python `compile()` over all 48 staged Python files → 0 syntax errors.
  - Exact-index `bash -n` over all 10 staged shell launchers → pass.
  - Strict UTF-8 JSON parsing with duplicate-key rejection over all 21 staged JSON files → pass; all staged text artifacts are UTF-8 and newline-terminated.
  - `openssl pkey -pubin -noout` over both staged Ed25519 public keys → pass.
  - Exact-index mode audit → 91 regular `100644` files and 26 executable `100755` files; no symlink, submodule, or other non-regular mode. All ten calibration launchers, including `scripts/launch_msae_independent_calibration_v3_gen9.sh`, are executable.
  - Staged path-policy scan → no staged path under `data/`, `results/`, `raw/`, `private/`, or `quarantine`; no staged `final*.jsonl` path.
  - High-confidence staged-blob secret scan (private-key headers, AWS/GitHub/Slack/OpenAI tokens, bearer credentials) and sensitive-filename scan → 0 findings.
  - Gen9 transcript verification → exact staged SHA-256 `ce26f149a75fee060eff7f92780c3ce0575e8e41a79d8b0da7b6136c4b1c148b`, mode `100644`; its section totals and exit codes at `reports/verification/msae_gen9_safe_checks_20260914.log:2-5499` agree with the rejection table.
  - Gen9 terminal-path metadata check → changed-region, containment, capability, downstream implementation-review, and named M3/M4 artifacts remain absent; no protected content was opened.
  - Remediation evidence inspection → `FINAL_STATIC_VERIFICATION.json` records zero experiment commands/artifacts, blank GPU-compute-process output, 50 passing targeted tests, successful compile/diff/plan gates, and an independent SHIP review.

CONTRACT COVERAGE
  - Exact logical commit and message → met — the index is the 117-path `01_calibration_control_plane` set recorded at `reports/provenance/msae_project_completion_20260915/porcelain_classification.json:1`, with exact per-entry bindings and digest.
  - Durable gen9 evidence and modes → met — `.gitattributes:1-5` preserves immutable evidence whitespace; the transcript is staged at the rejection-bound digest; all launchers preserve the executable bit while Python runtime/helper modules retain their recorded non-executable modes.
  - Gen9 implementation finished or rejected → met — `reports/adversarial/msae_independent_measurement_v3_post_m2_gen9_rejection.md:3-20` binds the plan/review and durable log; lines 24-77 enumerate the failed safe gates and concrete defects; lines 79-93 freeze the stop before changed-region publication and all later one-way doors. The independent review returns SHIP and reconstructs those facts at `reports/adversarial/msae_independent_measurement_v3_post_m2_gen9_rejection_review.md:1-36`.
  - V3 exposed-calibration-only boundary → met — the frozen protocol describes AMALGUM as exposed rather than an independent-source confirmation and permits only calibration replay (`docs/rfc-msae-independent-measurement-v3.md:1-15`); both authorization commitments have `allowed_scope="calibration_replay_only"` and `contains_execution_authorization=false`; the terminal disposition states that v3 is exposed-source calibration, never independent replication or confirmation (`reports/adversarial/msae_independent_measurement_v3_post_m2_gen9_rejection.md:95-100`).
  - No model/GPU/scoring/training/K2 execution → met — gen9's contract bars GPU/model/scientific execution before its safe gates (`docs/plan-msae-independent-measurement-v3-post-m9-gen9.md:19-33,476-500`), and the rejection records no v3 scoring and no K2/branch training (`reports/adversarial/msae_independent_measurement_v3_post_m2_gen9_rejection.md:79-100`). Earlier v3 preflight evidence is `failed_before_stage_a`, with `model_gpu_tmux="not_run"` and no signature; remediation evidence records zero experiment commands and artifacts (`reports/provenance/msae_measurement_remediation_v1/FINAL_STATIC_VERIFICATION.json:102-115`). Metadata-only process snapshots are not scientific GPU operations.
  - Remediation readiness evidence → met — the RFC is explicitly additive/no-experiment and prohibits model, GPU, training, sweep, and tmux work (`docs/rfc-msae-measurement-remediation-readiness-v1.md:1-24`); its completed DoD and deviations log preserve the CPU-only static outcome rather than an empirical result (`docs/rfc-msae-measurement-remediation-readiness-v1.md:337-400,443-502`). The draft remains fail-closed with absent source, replay, threshold, and Stage-C registries (`configs/msae_measurement_remediation_v1/draft.json:8-66`).
  - Clean staged scope and reproducibility → met — path/mode/content bindings are exact, no protected or generated result payload is staged, strict syntax/data/key checks pass, and no staged path has unstaged divergence.

UNKNOWNS
  - The intentionally failing predecessor/gen9 suites were not rerun: doing so is unnecessary for an evidence-preservation commit and could cross the review's no-experiment boundary. The staged durable transcript and independent rejection review are the authoritative disposition, not a claim that the historical candidate now passes.
  - Repository evidence and current namespace absence cannot prove that no unauthorized artifact ever existed transiently; the durable control records contain no indication that one did.
  - This review evaluates logical commit 1 only. The unstaged synthesis, claim ledger, independent-source record, and handoff artifacts require their separately assigned commit reviews.
