# Attempt 13 frozen-candidate adversarial review — blocked candidate v2

- Reviewed freeze payload SHA-256: `6cf24cf7ba1fd78532a1c08972558aceb92380bc80e1bf20e4bdb802bd2ac5d6`
- Reviewed candidate inventory SHA-256: `4b31b606a7d7fc3f4956083c11407c510a729c6ec1f0306e6c035cb6208d423a`
- Reviewer: independent `/adversarial` agent `/root/attempt13_candidate_adversarial_v2`
- Verdict: **BLOCK**
- No model inference was run; no authorization, lifecycle namespace, or scientific opening was created.

## Blocking finding

`scripts/run_atlas_relation_context_v9.py` accepted an arbitrary `--config` so long as its source/model/layer/
protocol study key stayed the same. A read-only adversarial probe changed batch size, hidden-state index, width,
analysis thresholds, and runtime GPU fields; `_verify_config()` and `_verify_freeze()` accepted the variants.
The authorization signed the alternate configuration hash, while execution did not compare all authorization
fields to the canonical frozen configuration. This could consume the one-shot opening and perform altered
forwards before the analyzer detected prepared-manifest drift.

Required fix: require the canonical config path, bind its hash to both the freeze and candidate entry, and
validate all signed authorization lineage/runtime/eligibility/training fields before any lifecycle write.
Regressions must show same-study-key alterations fail before authorization, run-root creation, or study-key
consumption.

## Required revisions

- Bring STARTED signing and global-key consumption under terminal-producing failure handling, with accurate
  pre-opening versus post-opening status.
- Reject unclassified directory symlinks during late-tree reconciliation; `os.walk(..., followlinks=False)`
  previously left them unclassified and unreported.
- Add study-key tests for altered non-key scientific and runtime fields.

## Checks

All 77 candidate entries, 14,151 historical entries, and both detached signatures matched. Compilation, shell
syntax, and 17 tests passed. The relation-row audit, GPU UUID/idle audit, key pinning, review binding,
cache/terminal lineage, safe tmux quoting, endpoint-specific eligibility, no-training guard, and Attempt-12
immutability otherwise passed.

The code was not authorized or run under this blocked freeze.
