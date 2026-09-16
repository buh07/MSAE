# Independent source v4 prospective-plan review

VERDICT: **SHIP**

ONE-LINE: The prospective contract closes the reviewed source, history, support,
split, custody, licensing, and no-neural gates before any source acquisition.

## Blockers

None.

## Checks

- `check-plan --path docs/plan-msae-independent-source-v4.md`: PASS.
- `git diff --check -- docs/plan-msae-independent-source-v4.md`: PASS.
- Quarantine contract: lstat-only rows use `sha256: null`,
  `adapter: "quarantine_lstat_only"`, and `content_reads: 0`; SHA-256 is required
  only for non-quarantine files.
- Source-use status: `previously_considered_but_project_source_use_unseen`.
- Expected v4 raw/private/results/provenance/config/program/test paths: absent.
- Frozen baseline HEAD: `7e1a6fc7a26a870a4edcf29c96b7cdf3cdbd7faa`.
- Reviewed plan SHA-256:
  `79cfa0bed9140e80dd7fa97f5e6f7133c506d034e01bb0ff8822615cf4889cc2`.
- No network, upstream fetch, source-content read, or quarantined-content read
  occurred during review.

## Contract coverage

Prospective authority, prior source-use disclosure, license obligations, exact
task semantics, full accessible-history and quarantine handling, four-role
bidirectional overlap, deterministic split/payload/role manifests, outcome-blind
custody, and the no-model/no-GPU/no-training boundary are covered. The plan does
not authorize scoring or K2/branch training.

## Remaining unknowns

Upstream availability, exact source bytes/license, corpus support, duplicates,
and overlap remain intentionally unknown until authorized acquisition. Deleted
or out-of-tree historical fetches cannot be proven absent from current filesystem
state.
