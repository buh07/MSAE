# PLAN — MSAE independent source v4.2 generated-cache binding correction

Status: prospective technical successor; no v4/v4.1/v4.2 payload exists.

## Goal

Correct one history-snapshot implementation error that treated regenerated,
opaque Python bytecode as historical text drift, then execute the otherwise
unchanged v4.1 source-readiness gates to either seal a replacement outcome-blind
payload or retain the next failure.

## Constraints

- V4.1 is durably rejected at `history_snapshot_binding` with
  `failure_code=history_snapshot_drift`; the only observed class was regenerated
  `scripts/__pycache__/prepare_msae_independent_source_v4.cpython-312.pyc`
  inode/mtime metadata. No source content was reported and no payload, model,
  GPU query, scoring, or training occurred. Rejection SHA-256:
  `758527095279226cc918a5faa98f6ea634d4fc084d6786434ecc169bc0188236`.
- V4.1 plan/review hashes are
  `aad3fb92acf588d18d9fd77a040b47717d07f3e0a97ebcfcdce9e1e650b9f749`
  and `c683e6daf4fcb8a112175390ab9902fe7c66189b1e4a295dcf5d6dae38324d55`.
  Frozen v4.1 builder/test hashes are
  `49b2d12feb61061032839bde092dd49cf743090f3861cc8aabdf4a4bb1909564`
  and `4055cfabca0f13c68afa6570d64d1e33c33d5cdf36ff406938bc614519785feb`.
- The pre-source baseline remains exactly
  `reports/provenance/msae_independent_source_v4/baseline_inventory.json` at
  SHA-256 `4467e76ce0ef016f32f58538df6440257b5765dad688317cf0f43e1592c5128b`.
  No recensus is permitted.
- Source, raw hashes, parser/FEATS semantics, labels, thresholds, role/split
  assignments, license, source-family and overlap rules, payload bytes, custody,
  claims, and ordered gates remain unchanged.
- No model/tokenizer import, GPU query, scoring, K2/branch training, or Stage C.

## Exact correction

The snapshot verifier requires current lstat identity only for baseline entries
with disposition `text_scanned`, `v4_authority`, or `quarantine`. Quarantines use
only the frozen lstat fields and remain unopened. For `binary_unscanned`, the
frozen baseline path/hash/disposition remains the audited evidence and current
regenerated cache bytes are neither reopened nor treated as text history. This
matches the v4 contract's explicit exclusion of opaque binary content from its
positive history-overlap claim.

A fixture creates a baseline with a text file, quarantine, and `.pyc`: changing
text or quarantine lstat must fail, while replacing the `.pyc` inode/mtime must
not. All v4 and v4.1 tests remain passing.

## Artifacts and approach

- New code/test: `scripts/prepare_msae_independent_source_v4_2.py` and
  `tests/test_prepare_msae_independent_source_v4_2.py`.
- New tracked provenance:
  `reports/provenance/msae_independent_source_v4_2/`.
- New ignored payload only on success:
  `data/msae_independent_source_v4_2/private/blind_payload.jsonl` (`0600`).
- Bind every predecessor input before the first source hash; apply only namespace,
  predecessor-binding, and exact verifier-disposition changes; run tests/static
  closure, raw bindings, then the unchanged ordered scientific gates.
- Any subsequent failure is terminal; there is no further repair in this task.

## Milestones

### M1 — reviewed correction

- [ ] This plan receives SHIP before another source read.
- [ ] Acceptance: all three payload paths are absent and predecessor hashes agree.

### M2 — execution

- [ ] Fixture and source-readiness gates pass in their inherited order or retain
  the first failure without later work.
- [ ] Acceptance: no scientific/custody drift and zero model/scoring/training.

### M3 — payload and review

- [ ] On success only, payload and public manifests reconstruct exactly and an
  independent source-readiness review returns SHIP.

## Verification plan

- [ ] Run all v4/v4.1/v4.2 tests with plugin autoload disabled; compile/static scan.
- [ ] Verify the semantic diff allowlist and every predecessor/artifact digest.
- [ ] Opaque-hash and lstat the payload without semantic reads.
- [ ] Run claim review, reproducibility checks, secret scan, and `git diff --check`.

## Definition of done

- [ ] V4/v4.1 remain immutable negatives and v4.2 is either a reviewed retained
  failure or reviewed `independent_source_ready_for_future_prescore_protocol`
  payload seal; model scoring and all training remain unauthorized.

## Risks and one-way doors

The correction cannot widen the positive history claim beyond scanned text and
safe archive members. Any text/quarantine drift or any later source gate stops
v4.2. A positive source-readiness status is not independent model replication.
