# PLAN — MSAE independent source v4.1 parser correction and payload

Status: prospective technical successor after the source-content-safe v4 parser
stop; no v4 or v4.1 payload exists.

## Goal

Correct one overly restrictive FEATS grammar in the already reviewed v4 source-
readiness builder, rerun the unchanged source-use, license, overlap, support,
split, custody, and no-neural gates in a new namespace, and either seal a
replacement outcome-blind payload or retain the next first failed gate.

## Constraints

- Authority inherited unchanged from
  `docs/plan-msae-independent-source-v4.md` SHA-256
  `79cfa0bed9140e80dd7fa97f5e6f7133c506d034e01bb0ff8822615cf4889cc2`
  and its SHIP review SHA-256
  `f082ff9485964057cca7f13ae6688a48ba3e628e015dd9042c895c96de03db4e`.
- V4 acquired the exact ATIS revision and then stopped at
  `first_failed_gate=source_parser`, `failure_code=malformed_feats`; no source
  text was reported, no payload was created, and no model/GPU/training operation
  occurred. Its rejection JSON SHA-256 is
  `f9470c92cf659c85eed8f06aa6c85fec4ed357b228ddb12cd4b23378cc2f0fa6`.
- V4.1 reuses only the five immutable `0444` raw files already acquired. It must
  verify their exact paths, sizes, modes, and SHA-256 values against
  `reports/provenance/msae_independent_source_v4/source_acquisition.json`
  (SHA-256
  `26766a492aab9044aa93bddf93e4e719372522dc1d63561a6684ae259d93ea2d`)
  before the first semantic read.
- The mutable predecessor implementation inputs are frozen before the successor:
  `scripts/prepare_msae_independent_source_v4.py` SHA-256
  `4cae36aef9b910426226da5d4bf649f5df2ef0ddb791e64c8d60c2454ac38238`,
  `tests/test_prepare_msae_independent_source_v4.py` SHA-256
  `c8b661a9635cb79fe81f469209fe64fd9a204de373875bb5727e69801a146c12`,
  and pre-acquisition
  `reports/provenance/msae_independent_source_v4/baseline_inventory.json`
  SHA-256
  `4467e76ce0ef016f32f58538df6440257b5765dad688317cf0f43e1592c5128b`.
  V4.1 reruns source-family and history gates against exactly that pre-v4
  baseline; it does not recensus or treat successor artifacts as historical
  evidence.
- All thresholds, candidate/source revision, task labels, role assignments,
  source-family exceptions, license rule, history baseline, overlap algorithms,
  split bytes, payload schema, custody, and claims remain byte-for-byte semantic
  equivalents of v4. Only the FEATS grammar and v4.1 output/code paths change.
- No model/tokenizer import, GPU query, scoring, K2/branch training, or Stage C.

## Exact correction

The v4 rule wrongly rejected every comma inside any FEATS value. V4.1 implements
UD FEATS as `_` or `|`-separated unique nonempty keys, each with `=` followed by
one or more comma-separated nonempty values. Keys and values may contain neither
`|` nor `=`; no empty value or duplicate value is allowed. Comma-separated
values are sorted lexicographically with no duplicate and the raw serialization
must already be in that order. For the sole scored morphology task `number`, the
field is emitted only when `Number` has exactly one value in
`{Sing,Plur,Dual,Trial,Pauc,Grpa,Grpl,Inv,Ptan}`. A multi-valued or unknown
Number is a terminal parser error; multi-valued non-Number attributes are valid
and ignored by readiness support.

Golden fixtures require `PronType=Int,Rel` to pass; `PronType=Rel,Int`,
`PronType=Int,,Rel`, `PronType=Int,Int`, duplicate keys, multi-valued Number, and
unknown Number to fail. All twelve original v4 tests remain passing.

## Isolation and artifacts

- Implementation: `scripts/prepare_msae_independent_source_v4_1.py`.
- Tests: `tests/test_prepare_msae_independent_source_v4_1.py`.
- Tracked provenance:
  `reports/provenance/msae_independent_source_v4_1/`, using the same exact
  artifact schemas as v4 plus `predecessor_rejection.json` and with schema IDs
  changed only from `v4` to `v4_1`.
- Ignored private payload:
  `data/msae_independent_source_v4_1/private/blind_payload.jsonl`, mode `0600`.
- V4 files, provenance, rejection, and absent v4 payload are immutable inputs.
  V4.1 never writes beneath a v4 path.

## Approach

1. Freeze and independently review this plan before any further source semantic
   read.
2. Copy the rejected builder/tests into v4.1 namespaces; make only the registered
   FEATS/parser and namespace/input-binding changes; verify an AST/source diff
   allowlist.
3. Re-run tests and static no-neural checks, then verify the raw acquisition
   binding.
4. Run the unchanged license, source-family, bidirectional four-role overlap,
   full accessible-history, and support gates in the frozen order.
5. Only if all pass, create-once publish and opaque-hash-verify the v4.1 payload;
   otherwise retain the first gate failure and stop.
6. Obtain a fresh source-readiness and claim review. Neither can authorize model
   scoring or training.

## Milestones

### M1 — prospective correction

- [ ] Exact predecessor rejection/raw bindings and sole semantic correction are
  reviewed SHIP before another semantic read.
- [ ] Acceptance: v4 payload remains absent; source bytes have not been printed
  or manually inspected.

### M2 — corrected readiness execution

- [ ] Original plus new FEATS fixtures, static closure, raw binding, and every
  inherited ordered gate pass, or the first failure is retained.
- [ ] Acceptance: no threshold/task/source/split/custody drift and zero model,
  GPU, scoring, or training operations.

### M3 — payload and review

- [ ] On all-gate success only, v4.1 role/split manifests and payload reconstruct
  exactly; payload is one-link `0600` and content never enters Git/output/review.
- [ ] Fresh independent source-readiness review returns SHIP.

## Verification plan

- [ ] Run both v4 and v4.1 test files with plugin autoload disabled.
- [ ] Assert the implementation diff is limited to namespace constants, raw
  predecessor binding, the exact FEATS function, and schema IDs.
- [ ] Strict-parse and rehash every tracked artifact; reconstruct role/split
  manifests and opaque-hash/count the payload.
- [ ] Verify the quarantines remain lstat-only and v4 payload remains absent.
- [ ] Run `git diff --check`, secret scan, reproducibility review, and claim review.

## Definition of done

- [ ] V4 remains a durable negative; v4.1 either has a reviewed retained failure
  or a reviewed `independent_source_ready_for_future_prescore_protocol` seal and
  replacement outcome-blind payload. In neither case are model scoring, K2,
  branch training, or Stage C authorized.

## Risks and one-way doors

This successor is informed only by the parser error class, not by source labels,
statistics, support, overlap, or model outcomes. Reusing the same source cannot
restore source-selection blindness and does not claim it. A second parser or any
later gate failure is terminal for v4.1; no additional repair, candidate change,
threshold change, or payload overwrite occurs in this task.
