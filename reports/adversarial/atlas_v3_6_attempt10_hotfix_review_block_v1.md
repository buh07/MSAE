VERDICT: BLOCK
ONE-LINE: The code fix is correct, but the signed hotfix chain does not cryptographically bind the reviewed candidate file.

BLOCKERS
  - [high] configs/atlas_rope_v6/hotfix/run_atlas_rope_v6.proposed.py:193-204 — the verifier never compares `hotfix_candidate_sha256` with the actual hotfix candidate.
    reasoning — it checks only that the signed payload’s arbitrary `hotfix_candidate_sha256` string appears in the review. It never hashes `configs/atlas_rope_v6/hotfix_candidate.json`, nor verifies that candidate’s target, old/new hashes, patch hash, and proposed-file hash.
    impact — the signed/reviewed chain is incomplete where the previously reviewed inventory is relaxed.
    fix — freeze `HOTFIX_CANDIDATE`; verify its SHA, schema, base, target, old/new, proposed, and patch hashes; require the review to contain the computed SHA.

REVISIONS
  - None.

NITS
  - Remove the generated hotfix `__pycache__`.
  - Make the freeze hotfix SHA unconditional.

CHECKS RUN
  - Exact reviewed candidate SHA `138f71dd7075928aabe13cfcbd3abb6fe0e7a5e1a7018ab2f646ef7fff9cc199`.
  - Old/proposed/patch hashes and live diff matched; no validation/science artifacts or model calls existed.

CONTRACT COVERAGE
  - Code correction and preservation of prior signed artifacts → met.
  - Complete signed/reviewed hotfix chain → unmet.

UNKNOWNS
  - GPU/runtime behavior was not exercised.
