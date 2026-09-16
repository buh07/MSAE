# PLAN — MSAE independent source v9 and replacement blind payload

Status: prospective replacement protocol. The v8 acquisition is retained under canonical terminal rejection `6352d5a52628898cbc1c4f91bbd97dfddf0aff48dd4c1422bc5d82517b33ad52`, independently reviewed SHIP as `fd3a40ba2ddd17a5a3464a669de186fdc4266307349751d81b01d6106ad7fc52`; v8 is
terminally rejected before semantic candidate parsing and produced no payload. No v9 data/acquisition/source-clone/payload path exists when this plan is reviewed; the sole pre-existing v9 provenance file is the public plan-time carryover authority record frozen below.

## Goal

Produce one replacement blind payload from an independently maintained, non-ATIS source only after
prospectively checking project history support, source-family/pedigree overlap, license, grouping,
role overlap, and support. The sole candidate remains the official Universal Dependencies Swedish
Talbanken repository at commit `c434778d9511be5c35a6a11531f0107a960fb5d6`. V9 is a new reviewed
protocol, not a repair or retry inside the terminal v8 namespace.

A successful terminal v9 review may establish only `independently_maintained_non_atis_source_payload_ready_for_blind_scoring_after_pre_v8_project_history_screen`. The structured boundary is: independently maintained official non-project repository; non-ATIS source family; no project-source-use evidence before v8 subject to the exact opaque-binary/framework exclusions and the enumerated v8 candidate-control carryover. It explicitly does **not** establish researcher unawareness, model-pretraining independence, global absence of candidate bytes, general content separation, scoring, or independent replication. This task performs no model/tokenizer/GPU/scoring,
K2, branch-training, or Stage-C operation.

## Why v9 is needed

V8 acquired the exact official four-file tree and published acquisition provenance, but its builder
stopped before opening candidate source content because `command_exit_status.hash_object_count` was
frozen to the inherited v7 literal `5` instead of the v8 file count `4`. The retained v8 rejection is
`source_acquisition_exit_status`; the independent terminal review confirms all eleven real command
records exited zero, the source was not semantically parsed, all scientific artifacts and the payload
are absent, all neural authorizations are false, and v8 cannot be retried.

V9 therefore reacquires the same immutable upstream commit into a distinct namespace under a new
reviewed authority. Its only intended deltas are the candidate-count correction, exact circular-history carryover authority, narrower claim vocabulary, and the explicit durable scientific-entry state machine below. It does not mutate, delete, reinterpret, or read the retained v8 raw source.

## Non-goals

- No claim that v3, v8, or v9 is an independent replication result.
- No model scoring, tokenization, GPU query, K2/branch training, Stage C, or training authorization.
- No repair, cleanup, or retry under `data/msae_independent_source_v8/` or its provenance directory.
- No semantic read or publication of v8 raw files; their paths, lstat metadata, and public acquisition
  hashes may be checked opaquely.
- No Atlas quarantine content access. Exactly `data/atlas_v1/private/final.jsonl`, `data/atlas_v1/private/final.records.jsonl`, and `data/atlas_v1/private/final.units.jsonl` are lstat-only quarantines. `data/atlas_v1/private/final_manifest.json` remains an ordinary text-scanned history input. No private-prefix shortcut is allowed.
- No source prose, sentences, tokens, lemmas, or blind records in public artifacts, logs, tests,
  exceptions, stdout, stderr, or reviews.

## Fixed candidate and exact acquisition tree

Repository: `https://github.com/UniversalDependencies/UD_Swedish-Talbanken.git`

Commit: `c434778d9511be5c35a6a11531f0107a960fb5d6`

Exact requested paths, in this order:

1. `sv_talbanken-ud-train.conllu`
2. `sv_talbanken-ud-dev.conllu`
3. `sv_talbanken-ud-test.conllu`
4. `LICENSE.txt`

The runner uses filtered no-checkout clone, sparse checkout, exact HEAD/tree/`ls-tree -z`, and
per-file `git hash-object --no-filters` checks. The success record must contain exactly eleven command
records: two ignore checks, clone, checkout, HEAD, tree, ls-tree, and four hash-object records. Every
actual command exit status is zero. `hash_object_count` must equal `len(config.files)` and therefore
`4`; neither builder nor verifier may use a candidate-independent literal. A focused test must accept
four and reject both three and five.

The v9 raw installation is create-once at
`data/msae_independent_source_v9/raw/<commit>/`, with namespace/raw parents `0700`, commit directory
`0555`, four regular files `0444`, `nlink=1`, exact byte sizes/hashes/blob IDs, and no other entries.
All path traversal and reads use component-wise no-follow descriptors with before/after inode checks.

## Retained-v8 boundary and history meaning

The scientific history question is whether the candidate source family or content occurred in the
project before the candidate protocol was introduced. Candidate-naming v8 control artifacts are not
new evidence of prior source use; treating them as historical source would be circular. V9 therefore
uses an exact, reviewable carryover exclusion and otherwise fails closed. The create-once authority record `reports/provenance/msae_independent_source_v9/v8_carryover_authority.json` is mode `0644`, one link, SHA-256 `00d7cdca4e9893ef1f4e36b6104caf21991ce1ca92e9897d3c5a72d497212f47`; it is a plan-time input, not a later rebindable manifest.

The following existing v8 files are the complete `v8_candidate_control_carryover` set. They are
excluded from history text extraction, directly hash-bound in the v9 predecessor manifest, and may
not be selected by a prefix rule:

- `docs/plan-msae-independent-source-v8.md`
- `reports/adversarial/msae_independent_source_v8_plan_review.md`
- `scripts/prepare_msae_independent_source_v8.py`
- `scripts/acquire_msae_independent_source_v8.py`
- `tests/test_prepare_msae_independent_source_v8.py`
- `configs/msae_independent_source_v8/acquisition.json`
- `reports/verification/msae_independent_source_v8_source_free_checks.log`
- `reports/adversarial/msae_independent_source_v8_preacquisition_implementation_review.md`
- `reports/adversarial/msae_independent_source_v8_preacquisition_authority_review.md`
- `reports/adversarial/msae_independent_source_v8_terminal_failure_review.md`
- `reports/provenance/msae_independent_source_v8/preacquisition_alias_screen.json`
- `reports/provenance/msae_independent_source_v8/historical_source_registry.json`
- `reports/provenance/msae_independent_source_v8/baseline_inventory.json`
- `reports/provenance/msae_independent_source_v8/preacquisition_authority_manifest.json`
- `reports/provenance/msae_independent_source_v8/source_acquisition_entry.json`
- `reports/provenance/msae_independent_source_v8/source_acquisition.json`
- `reports/provenance/msae_independent_source_v8/rejection.json`

The exact path/SHA-256 table frozen by this plan is:

| path | SHA-256 |
|---|---|
| `docs/plan-msae-independent-source-v8.md` | `7aec70f8d6f384f2919f5f3086064b437dd34ff7731542aed2d7abe23ac5ae19` |
| `reports/adversarial/msae_independent_source_v8_plan_review.md` | `d159749125a6db4e1dd6a68f2207e4be6b643e2f0d7b8112695cfec98660204d` |
| `scripts/prepare_msae_independent_source_v8.py` | `5b3bf93ed412e480e7d84720b235b104bc571bb63faa16504279cd25cf6bc881` |
| `scripts/acquire_msae_independent_source_v8.py` | `07a15235a860296ffb461d2bc065cdb093fb87656b9dbab3918c20293b4159a3` |
| `tests/test_prepare_msae_independent_source_v8.py` | `3baad53b0d863c4139abeaf3fa303f46fad4338d0342d0289ced15ba83bd76cc` |
| `configs/msae_independent_source_v8/acquisition.json` | `8383d3ba80ac1296887c243e00d09b6b9a5e79b19f771934a1ddd07ceac56df9` |
| `reports/verification/msae_independent_source_v8_source_free_checks.log` | `3629712ae64b00c9e6c9dd2cd1cced774d3a5f328fd72115bf7edbf14e13369b` |
| `reports/adversarial/msae_independent_source_v8_preacquisition_implementation_review.md` | `0bedf94cb578722208e6069f9ee00bf966921fb32317235e777e3a54f6884496` |
| `reports/adversarial/msae_independent_source_v8_preacquisition_authority_review.md` | `2567d7db6f72b0a19d66ec36bffd274ebb1e59ffb5f55b90fb688f4ed876f3e6` |
| `reports/adversarial/msae_independent_source_v8_terminal_failure_review.md` | `fd3a40ba2ddd17a5a3464a669de186fdc4266307349751d81b01d6106ad7fc52` |
| `reports/provenance/msae_independent_source_v8/preacquisition_alias_screen.json` | `68a7536c95896087960dd4fc5882df85296baaa1a07aaf910e0e7c257b165e2f` |
| `reports/provenance/msae_independent_source_v8/historical_source_registry.json` | `ff4a36996f58531353dda9ed8fcbedb4c3a615f2d877e8b31f1462ddc8581a97` |
| `reports/provenance/msae_independent_source_v8/baseline_inventory.json` | `c4283d888fb8d5927ff46533bea3a163f582daea08f722656b5f38fcec64ff51` |
| `reports/provenance/msae_independent_source_v8/preacquisition_authority_manifest.json` | `cd7179c392199aa4934f40878a9faf5b4d7b2ec4b9b149eaaad640619ddfffea` |
| `reports/provenance/msae_independent_source_v8/source_acquisition_entry.json` | `091d8472366f9ac8b01462b49f75f33c25bf77caa1569f947ddeda9e49a4140d` |
| `reports/provenance/msae_independent_source_v8/source_acquisition.json` | `6e57111da0b139bb2c4f0333b230b0a72458d7c419d50cfcb6896596b7f62958` |
| `reports/provenance/msae_independent_source_v8/rejection.json` | `6352d5a52628898cbc1c4f91bbd97dfddf0aff48dd4c1422bc5d82517b33ad52` |

For every map digest, reject duplicate paths; build a Python dictionary in lexicographically sorted POSIX-path order; serialize exactly with `json.dumps(value, sort_keys=True, ensure_ascii=True, separators=(",",":"), allow_nan=False).encode("utf-8")` and no final newline. The control map values are SHA-256 strings only. Canonical `{path:sha256}` serialization has SHA-256 `ecfdffb24efac47c4f8b7e7e2435759d10f2f652f60ebc48962c7148f7985f3d`. The exact 50-entry v8 direct predecessor map is embedded in the carryover authority record; its canonical ASCII-JSON serialization has SHA-256 `1dc8b1f85e6deb20edb63ec86da06e6cda64dca342223ed0d6d3fc9af7169a53`. Registry generation, implementation review, baseline, authority, acquisition, prepare, and terminal verify must check all 17 hashes, the 50-entry map itself, and both serialization digests; drift stops rather than rebinding.

The retained v8 data namespace is a separate exact opaque carryover universe, frozen by the same authority record: directories
`data/msae_independent_source_v8/{,raw/,raw/<commit>/}` and exactly the four names above beneath the
commit directory. Directory modes/nlinks/current identities are authority-record fields: namespace `0700`/3 links, raw parent `0700`/3 links, commit directory `0555`/2 links. File authority is:

| file | bytes | SHA-256 | git blob SHA-1 | mode/nlink |
|---|---:|---|---|---|
| `LICENSE.txt` | 21038 | `55d116ac4f9bc34715c7823a5f5ca2e4c0cac4917db9e58a470a3d48033d261c` | `4b4c655063f804ef1942ffcc3e6e36b72f6e1f6e` | `0444`/1 |
| `sv_talbanken-ud-dev.conllu` | 879504 | `e1c14ae088f575d9f5f2d870d456b9e3911a04725f141752bb8c972a81cb6c6c` | `66279f3667b56ba4288d1ba984021b36efc382e9` | `0444`/1 |
| `sv_talbanken-ud-test.conllu` | 1831116 | `f7bc84ce37cd6a71e95b8d8684801da0bb6d2be4e419ba2e865eb109d6cd1bc6` | `9f9ba329b61cfa4158e548c7d01352466fd12e45` | `0444`/1 |
| `sv_talbanken-ud-train.conllu` | 6023121 | `5e3c41f35999453c94a0f66155f695e6699950c44741abe7d98a2305f7f3f63d` | `0d0f4244db1e3267e15641004245db53a4a0e4cf` | `0444`/1 |

The raw map uses each path mapped to exactly the keys `git_blob_sha1,mode,nlink,sha256,size` (no device/inode/mtime), serialized by the same rule. Its digest is `822d7d795020101b1554d5a25d87c229d1bd6cdf1926a42f3dfbf3f230b58e0e`. All values must reconstruct from the create-once carryover record, exact v8 plan/runner/acquisition/rejection/review hashes, current lstat, and opaque SHA reads without source parsing or printing. Any extra v8 data path, symlink,
hardlink, mode drift, size drift, or hash drift blocks v9 before its authority manifest. The v9 code,
tests, reviewer, and baseline/authority phases must never decode or semantically scan those bytes.

Any v8-named path outside the two exact universes above is ordinary history and cannot be silently
excluded. Any future addition to either universe blocks. The carryover exception is justified only
because v8 was prospectively introduced for the same immutable candidate and its SHIP terminal review
proves rejection occurred before semantic source parsing. It does not erase any earlier project
history.

## History registry, alias screen, and normalization

Before implementation review and while all v9 source/data paths are absent, build
`reports/provenance/msae_independent_source_v9/historical_source_registry.json` by rescanning every
regular repository file except generated prefixes, the exact v9 authority set, the exact v8 control
carryover, and the exact opaque v8 data universe. The three Atlas quarantines are lstat-only with
`content_reads=0`. Symlinks, special files, external hardlinks, unreadable paths, unsupported text,
archive ambiguity, or inventory drift stop the protocol.

The inventory and registry retain the v8 frozen text/archive adapters, record schema, normalization
steps, regex byte grammar, Python/Unicode runtime, 1,048,576-byte chunks, 2,048-byte overlap,
overlength handling, and framework exception table. The only lexical-domain changes are
`msae-v9/pedigree\0`, `msae-v9/token\0`, and `msae-v9/lemma\0`. Exact golden inputs, `.git`/`.git/`
equivalence, URL/UD/JSON boundary fixtures, path serialization golden, and representative entries
must recompute in tests.

The v9 alias screen is computed from the same history input set. It must report zero candidate alias
content occurrences, zero pathname occurrences, and zero prior source-use evidence outside the exact
carryover exception. It separately reports the complete carryover paths and their hashes rather than
silently subtracting occurrences. Any candidate alias elsewhere rejects v9 before acquisition.

The baseline inventory binds the full current file census, exact dispositions, history input record
digest, registry hash, alias-screen hash, quarantine read count zero, process snapshot, and full
training-root census. It must demonstrate that deleting the exact carryover exception would expose
candidate aliases, while adding an alias anywhere else stops. This is an audit of the circularity
exception, not a claim that no candidate-related bytes exist after v8.

## Prospective artifacts and authority order

The exact v9 authority set is:

- `docs/plan-msae-independent-source-v9.md`
- `reports/adversarial/msae_independent_source_v9_plan_review.md`
- `reports/provenance/msae_independent_source_v9/v8_carryover_authority.json` (fixed SHA-256 `00d7cdca4e9893ef1f4e36b6104caf21991ce1ca92e9897d3c5a72d497212f47`)
- `reports/provenance/msae_independent_source_v9/preacquisition_alias_screen.json`
- `reports/provenance/msae_independent_source_v9/historical_source_registry.json`
- `scripts/prepare_msae_independent_source_v9.py`
- `scripts/acquire_msae_independent_source_v9.py`
- `tests/test_prepare_msae_independent_source_v9.py`
- `configs/msae_independent_source_v9/acquisition.json`
- `reports/verification/msae_independent_source_v9_source_free_checks.log`
- `reports/adversarial/msae_independent_source_v9_preacquisition_implementation_review.md`
- `reports/provenance/msae_independent_source_v9/baseline_inventory.json`
- `reports/provenance/msae_independent_source_v9/preacquisition_authority_manifest.json`
- `reports/adversarial/msae_independent_source_v9_preacquisition_authority_review.md`

No prefix-based authority exclusion is permitted. The literal expected-absent authority additions are `reports/provenance/msae_independent_source_v9/baseline_inventory.json`, `reports/provenance/msae_independent_source_v9/preacquisition_authority_manifest.json`, and `reports/adversarial/msae_independent_source_v9_preacquisition_authority_review.md`; only those exact paths may be added during their ordered phases.

Required ordering:

1. Prospective plan and independent plan SHIP review.
2. Source-free registry/alias-screen generation, implementation, synthetic tests, and source-free
   implementation SHIP review. No v9 data/acquisition path exists.
3. Full baseline inventory, including exact v8 opaque/control carryover verification, history binding,
   process snapshot, and training-root census.
4. Create-once authority manifest binding the exact baseline bytes/process/training roots, all v9
   implementation artifacts, every prior v4-v8 predecessor required by v8, and all seventeen v8
   carryover files plus opaque v8 data reconstruction.
5. Independent pre-acquisition authority SHIP review. Its exact SHA-256 is a required runner argument.
6. One-shot v9 acquisition.
7. Only after acquisition success, one-shot scientific preparation and terminal review.

The baseline cannot precede the source-free implementation SHIP review. The manifest cannot precede
the baseline. Acquisition cannot precede the independent authority SHIP review.

## Exact post-baseline recensus dispositions

All later full recensus operations compare the current filesystem to the frozen baseline entry-for-entry.
The registry/overlap input set is always exactly the baseline records whose disposition is
`text_scanned`; no post-baseline file is added to the historical source registry. A current baseline
path must retain its exact type/mode/nlink/size/hash/disposition. The only permitted additions are the
following literal state-dependent sets, all classified `v9_generated_protocol` and excluded from text
extraction only because their bytes and states are bound by the named canonical terminal artifact.
There is no v9 prefix exception.

| phase/state | exact permitted additions | read policy and authority |
|---|---|---|
| authority complete | `reports/provenance/msae_independent_source_v9/baseline_inventory.json`, `reports/provenance/msae_independent_source_v9/preacquisition_authority_manifest.json`, `reports/adversarial/msae_independent_source_v9_preacquisition_authority_review.md` | public canonical bytes; exact hashes in authority/review |
| acquisition entered | previous row plus `reports/provenance/msae_independent_source_v9/source_acquisition_entry.json` | public canonical JSON; entry authority |
| acquisition rejected | acquisition-entered row plus `reports/provenance/msae_independent_source_v9/source_acquisition_rejection.json`, and either no v9 data path or exactly the partial namespace/directories/files enumerated by that rejection's `raw_namespace_exists` and ordered `partial_raw_metadata` | public canonical JSON plus lstat-only partial raw reconstruction; acquisition terminal authority; no cleanup, raw hashing, or semantic read |
| acquisition succeeded / prepare pre-entry | acquisition-entered row plus `reports/provenance/msae_independent_source_v9/source_acquisition.json`; directories `data/msae_independent_source_v9`, `data/msae_independent_source_v9/raw`, `data/msae_independent_source_v9/raw/c434778d9511be5c35a6a11531f0107a960fb5d6`; and exactly its four frozen file names | public acquisition JSON read normally; directories and raw files lstat only (type/mode/nlink/size/name); current raw SHA verification is explicitly deferred until after the durable scientific entry; acquisition success supplies the expected hashes |
| B0 | acquisition-success row plus `reports/provenance/msae_independent_source_v9/preflight_rejection.json` | public canonical JSON; B0 binds all other final/temp states absent |
| active post-entry / B1 | acquisition-success row plus `reports/provenance/msae_independent_source_v9/scientific_preparation_entry.json`, a zero-or-more prefix of the ordered scientific finals, `reports/provenance/msae_independent_source_v9/rejection.json`, and optionally directory `data/msae_independent_source_v9/private` plus the final payload if its publisher completed | public finals read normally; entry/rejection bind exact prefix and every absent later final/temp; payload never opened semantically and is opaque-hashed only; any non-prefix set stops |
| B2 | acquisition-success row plus entry, all fifteen ordered scientific finals, directory `data/msae_independent_source_v9/private`, and `data/msae_independent_source_v9/private/blind_payload.jsonl` | seal/no-training gate bind public bytes and opaque payload metadata/hash |

For B1, if failure occurs after a scientific final was canonically linked, that final is included in the
prefix; if it occurs before link and identity-checked cleanup succeeds, the prefix ends before that
artifact. `rejection.json` is not a member of the scientific prefix. B0/B1/B2 valid states contain no
named temp. During a live current invocation, the one current temp is tolerated only inside its frozen
publisher; it is never an allowed recensus addition. B0, B1, and B2 each carry
an ordered `post_baseline_inventory` whose entries are exactly the applicable table row, with
lexicographic path order, disposition, type, mode, nlink, size and SHA for public regular files,
lstat metadata for directories; before entry, raw records contain expected SHA from acquisition plus `sha256_verification_status="deferred_until_post_entry"` and `content_read=false`; after entry, raw records contain verified opaque SHA plus `sha256_verification_status="verified_post_entry"`; payload records use opaque size/SHA only. The containing terminal JSON final is represented non-recursively as exactly `{path,state:"self_canonical_final"}` and its temp as absent; terminal verification checks that final separately against the complete schema. The inherited acquisition rejection schema is unchanged and does not carry this new field; acquisition terminal verification reconstructs its exact acquisition-rejected table row externally from the frozen baseline, entry, and rejection before returning. Missing, extra,
duplicate, reordered, prefix-inconsistent, drifted, or unsupported additions stop. Private payload
bytes never enter the history or text scanner.

Before the scientific entry, the builder compares only the baseline `text_scanned` set to the frozen
registry and separately validates the acquisition-success row using public records and lstat only—no current v9 raw hash or content read is performed or claimed. After entry, overlap still compares
candidate units only against that identical frozen baseline history set; recensus verifies generated
additions structurally but never treats self-generated candidate metadata as prior history. Terminal
verify repeats both comparisons and the exact applicable row.

## One-shot acquisition publication

V9 inherits the reviewed v8 runner’s durable-entry-before-subprocess, config-before-argv,
component-wise no-follow, create-once publication, restart-state table, current-temp identity cleanup,
parent fsync, scratch containment, and terminal success/rejection reconstruction contracts. All schema
literals and paths change to v9. A durable `source_acquisition_entry.json` is published and parent
fsynced before any git subprocess.

Acquisition is terminal in the v9 namespace. A valid success or acquisition rejection is idempotently
verifiable; an invalid final/temp/cardinality state is case (c), causes zero new subprocesses, and is
not repaired. Synchronous publisher failures use identity-checked cleanup plus parent fsync where the
frozen state table allows it; async interruption may leave case (c). Scratch is removed before
success/rejection publication and its absence is verified. No runner output may contain source bytes.

## Scientific preparation entry and terminal behavior

The complete builder-owned final universe is:

- pre-entry terminal: `preflight_rejection.json`;
- one-way marker: `scientific_preparation_entry.json`;
- post-entry terminal: `rejection.json` or the success pair `seal.json` plus
  `no_training_gate.json`;
- scientific finals, in order: `document_group_census.json`, `source_manifest.json`,
  `license.json`, `source_family.json`, `candidate_pedigree.json`, `dedup.json`,
  `cross_role_overlap.json`, `history_manifest.json`, `history_overlap.json`, `support.json`,
  `role_manifest.json`, `split_manifest.json`, `post_process_snapshot.json`,
  `no_training_gate.json`, `seal.json`; and
- private final: `data/msae_independent_source_v9/private/blind_payload.jsonl`.

Each JSON/payload final has exactly one same-directory temp named `.<basename>.building`. No other v9
public or private temp is allowed. Before every invocation, the builder lstat-enumerates this literal
final/temp universe without opening payload bytes and classifies exactly:

| state | required paths | behavior |
|---|---|---|
| A clean | every listed final and temp absent | source-free prechecks may run; raw-read count remains zero |
| B0 preflight terminal | only one canonical `preflight_rejection.json` final; every temp, entry, scientific, post-entry outcome, and payload path absent | zero-work idempotent terminal verify; zero raw reads |
| B1 post-entry rejection | one canonical entry plus one canonical `rejection.json`; no temp; every scientific/payload final exactly matches the rejection's ordered inventory | zero-work idempotent terminal verify; no new raw read |
| B2 success | one canonical entry, the complete canonical success scientific set, one canonical payload, no rejection/preflight final, and no temp | zero-work idempotent terminal verify; no new raw read |
| C invalid/incomplete | every other cardinality, schema, mode, link, hash, or final/temp state, including entry-only at process start | stop with zero raw read, zero cleanup, zero publication, and no retry |

In state A the builder first strictly validates the already-authorized immutable prerequisites:
the plan/reviews, carryover authority and every bound predecessor, registry/alias screen, baseline,
authority manifest/review, acquisition entry, and acquisition success. Missing, malformed, unreadable,
mode/link-drifted, or hash-drifted immutable prerequisite is C: zero raw read, zero publication, and no
retry. B0 is reachable only after those prerequisites validate, so every authority/acquisition hash
required by B0 is the exact already-validated non-null 64-hex value.

The remaining dynamic prechecks always produce canonical evidence objects before a B0 decision:

- `history_recensus` has exactly
  `schema_version,status,failure_code,expected_entries_sha256,observed_entries_sha256,expected_history_inputs_sha256,observed_history_inputs_sha256,added_paths,removed_paths,changed_paths,quarantine_content_reads`.
  Schema is `msae_independent_source_v9_history_recensus_v1`; status is `eligible`, `drift`, or
  `boundary_failure`; `failure_code` is null only when eligible; expected hashes are 64-hex;
  observed hashes are 64-hex after a complete census or null after boundary failure; path arrays are
  sorted unique POSIX strings (empty when unavailable); quarantine reads is always integer zero.
- `training_recensus` has exactly
  `schema_version,status,failure_code,expected_entries_sha256,observed_entries_sha256,expected_entry_count,observed_entry_count`.
  Schema is `msae_independent_source_v9_training_recensus_v1`; status/failure/null rules match history;
  expected values are non-null; observed hash/count are non-null only after a complete census.
- `pre_entry_process_snapshot` is the complete existing v8 process-snapshot schema: exactly
  `schema_version,observation_scope,forbidden_tokens,process_count,forbidden_identity_count,status,entries`;
  entries are PID/start-ticks/executable-basename/command-SHA/ordered-forbidden-codes records, and
  status is `eligible` iff forbidden count is zero.

A dynamic precheck is eligible only if history and training are eligible and the process snapshot is
eligible. Otherwise the builder publishes B0 and ends v9. `preflight_rejection.json` schema
`msae_independent_source_v9_preflight_rejection_v1` has exactly:
`schema_version,status,failure_code,plan_sha256,plan_review_sha256,builder_sha256,carryover_authority_sha256,baseline_inventory_sha256,authority_manifest_sha256,authority_review_sha256,source_acquisition_entry_sha256,source_acquisition_sha256,history_inputs_sha256,history_recensus,training_recensus,pre_entry_process_snapshot,pre_entry_process_snapshot_sha256,post_baseline_inventory,scientific_artifact_inventory,payload_state,raw_file_open_count,source_content_reported,model_operations_initiated_by_builder,gpu_queries_initiated_by_builder,training_runs_initiated_by_builder,model_scoring_authorized,k2_or_branch_training_authorized,stage_c_authorized,next_action`.
Status is `rejected_before_scientific_entry`; failure code is the first dynamic precheck failure; raw
opens/operation counts are integer zero; all authorization/content booleans are false; next action is
`new_reviewed_protocol_only`; the process digest is SHA-256 of the exact canonical process object.

For both rejection schemas, `post_baseline_inventory` has exact schema
`msae_independent_source_v9_post_baseline_inventory_v1` and keys `schema_version,state,entries`; state
is exactly one of `scientific_entry`, `B0`, `B1`, or `B2`. The entry embeds state `scientific_entry`, the acquisition-success row, and its own final as `self_canonical_final`; B0/B1/B2 use their matching state; entries use the exact phase row above. `scientific_artifact_inventory` has exact
schema `msae_independent_source_v9_scientific_artifact_inventory_v1` and keys
`schema_version,entries`. It orders the entry final/temp, preflight/post-entry outcome finals/temps,
and every fifteen scientific final/temp pair exactly as the universe list; the containing outcome
final is represented by `{path,state:"self_canonical_final"}`, its own temp by `{path,state:"absent"}`.
Every other absent entry is exactly `{path,state:"absent"}`. A present public final is exactly
`{path,state:"present",type:"regular",mode,nlink,size,sha256}`. Valid B0 has every non-self entry
absent. `payload_state` is an ordered two-item list for final then temp; absent is the same two-key
record, while a present opaque final has exactly
`path,state,type,mode,nlink,size,sha256`; no valid B0/B1 contains a payload temp. Paths are literal,
POSIX relative, unique, and order-sensitive. Canonical JSON everywhere is UTF-8, sorted keys, compact
separators, `ensure_ascii=False`, `allow_nan=False`, plus one final LF.

If all dynamic prechecks pass, the same invocation publishes
`scientific_preparation_entry.json` as regular `0644`, `nlink=1` using exclusive temp, complete write,
file fsync, no-replace link, temp unlink, and parent fsync. Its schema
`msae_independent_source_v9_scientific_preparation_entry_v1` has exactly:
`schema_version,status,plan_sha256,plan_review_sha256,builder_sha256,carryover_authority_sha256,baseline_inventory_sha256,authority_manifest_sha256,authority_review_sha256,source_acquisition_entry_sha256,source_acquisition_sha256,source_commit,files,history_inputs_sha256,history_registry_sha256,history_recensus,training_recensus,pre_entry_process_snapshot,pre_entry_process_snapshot_sha256,training_root_entries_sha256,post_baseline_inventory,raw_file_open_count_before_entry,source_content_reported,model_operations_initiated,gpu_queries_initiated,training_runs_initiated,model_scoring_authorized,k2_or_branch_training_authorized,stage_c_authorized`.
Status is `entered_before_first_v9_raw_open`; `files` is the ordered four-name list, each exact object
`path,size,sha256,git_blob_sha1,mode,nlink`; history/training/process objects are the same exact eligible
objects computed above and their digests are reconstructible; counts are zero and booleans false. No
v9 raw file may be opened—even for hashing—before this final has returned from successful parent fsync
in the current invocation.

Publisher failure semantics are state-based. Before a B0 or entry final link, a current-invocation
temp may be removed only after device/inode identity equality, followed by parent fsync; successful
cleanup leaves state A and is safely rerunnable because raw-open count is zero. Cleanup failure leaves
C. After link, all content validation has completed. For B0 publication, a canonical final with absent
temp is recovered as B0 regardless of why the publisher raised; final+temp or temp-only is C. For
entry publication, any raised write/fsync/link/unlink/parent-fsync operation causes no raw open: state
A is safely rerunnable, while canonical entry-only or entry+temp is C. Only a no-exception return from
every entry publication/durability step in the current invocation permits the first raw open. On later
invocations entry-only is always C, so interruption after entry and before an outcome cannot reread
source.

After the first raw open, every caught gate/boundary failure attempts post-entry B1.
`rejection.json` schema `msae_independent_source_v9_rejection_v1` has exactly:
`schema_version,status,failure_code,plan_sha256,plan_review_sha256,builder_sha256,carryover_authority_sha256,baseline_inventory_sha256,authority_manifest_sha256,authority_review_sha256,source_acquisition_entry_sha256,source_acquisition_sha256,scientific_preparation_entry_sha256,history_inputs_sha256,history_recensus,training_recensus,pre_entry_process_snapshot,pre_entry_process_snapshot_sha256,post_baseline_inventory,scientific_artifact_inventory,payload_state,raw_file_open_count,source_content_reported,model_operations_initiated_by_builder,gpu_queries_initiated_by_builder,training_runs_initiated_by_builder,model_scoring_authorized,k2_or_branch_training_authorized,stage_c_authorized,next_action`.
Status is `rejected_after_scientific_entry`; entry SHA is non-null 64-hex; raw-file-open count is the
actual nonnegative integer; other counts are zero, booleans false, and next action is
`new_reviewed_protocol_only`.

For a failed pre-seal scientific/payload publisher before its final link, successful
identity-checked temp cleanup plus parent fsync leaves the already-published entry/prefix, then B1
publication is attempted; cleanup failure is C. If that target final linked canonically and its temp
was durably removed, the final remains in the B1 prefix/inventory and B1 is attempted. Target
temp-only or final+temp is C. For the B1 publisher itself, pre-link failure with successful temp
cleanup leaves entry/prefix without an outcome and is C (never state A); a canonical B1 final with
absent temp is recovered as B1 regardless of cause; temp-only or final+temp is C.

The terminal seal publisher is a distinct state transition. If it fails before seal link and its
current temp is identity-cleaned plus parent-fsynced, the already-published no-training gate remains
the last scientific-prefix item and B1 is attempted with seal absent. If seal has linked and the seal
temp is absent, the complete final reconstructs B2 regardless of unlink/parent-fsync exception cause;
B1 publication is forbidden. Seal temp-only or seal final+temp is C. Thus a valid seal and rejection
can never coexist. Any uncatchable interruption is C, not a retained rejection. Success B2 binds the
full entry object/digest and entry SHA in both seal and no-training gate. Goldens
cover missing/malformed/drifted immutable prerequisites as C; each history/training/process dynamic
status as B0; exact B0/B1 bytes; and every fault/recovery/A/B0/B1/B2/C row.

## Frozen scientific gates and payload

After the durable scientific entry, run in this order:

1. Raw custody, official commit/tree/blob/hash reconstruction, and source-acquisition command checks.
2. Document/group support census.
3. Strict CoNLL-U parse and source manifest.
4. License gate: `LICENSE.txt` only, exact reviewed public-license predicates; no license prose emitted.
5. Source-family gate.
6. Candidate pedigree scan on all four raw files using the exact registry byte-regex/chunk/overlap,
   overlength, pending-tail, strict UTF-8, JSON, normalization, and hash grammar.
7. Within-role exact dedup.
8. Cross-role exact normalized-text overlap removal.
9. Full history support and exact normalized-content overlap against the frozen pre-v8 history set.
10. Support thresholds.
11. Deterministic source-native roles: train=discovery, dev=calibration, test=blind split input.
12. Deterministic group-preserving C1/C2 split.
13. Fresh v9 private payload publication.
14. Post-process/training recensus, public no-training gate, and terminal seal.

Any ineligible gate stops immediately and retains a terminal rejection. No later manifest or payload
is created after a failed gate.

The parser, normalization, task inventory, dedup, support, license, source-family, and payload row contracts are inherited from the exact v8 builder SHA `5b3bf93ed412e480e7d84720b235b104bc571bb63faa16504279cd25cf6bc881`. Normalized-AST equality tests cover `parse_feats`, `canonical_group_id`, `_finish_sentence`, `parse_conllu`, `sentence_labels`, `normalized_sentence`, `lexical_tokens`, `fivegrams`, `overlap_reason`, `assign_split`, `build_split_manifest`, `payload_record`, `_history_text_units`, `_history_units`, `deduplicate_roles`, `_role_overlap`, `_history_overlap`, `_support`, `license_evidence`, `_license`, `_group_census_one`, `document_group_census`, `_source_family`, `normalize_pedigree`, and `candidate_pedigree_identifiers`, and `candidate_pedigree`. Permitted changes inside that equality normalizer are only v8-to-v9 schema/domain/path literals and the v9 raw path; control-flow, predicates, regexes, flags, thresholds, field sets, and publication order must remain equal. Wrapper/orchestration changes are limited to the exact carryover checks, count-from-config correction, narrower claim fields, v9 authority bindings, and scientific state machine named here. Split domains change to `msae-independent-source-v9/C1C2-group`; schema/domain strings
change to v9. The payload is canonical UTF-8 JSONL at
`data/msae_independent_source_v9/private/blind_payload.jsonl`, regular `0600`, `nlink=1`, published
create-once without replacement, and never opened semantically by the coordinator or reviewers.
Public artifacts contain counts, hashes, role/source-record digests, group hashes, and eligibility
only—never source text or payload rows.

The terminal seal binds every public scientific artifact, exact schemas/hashes/modes/nlinks, opaque
payload path/hash/size/record count, authority/acquisition/scientific-entry chain, history/training
recensus, process snapshot, source-content publication false, model/GPU/training operation counts zero,
and all authorizations false. It also has exact claim-boundary fields:
`source_maintenance_relation="independently_maintained_official_non_project_repository"`,
`source_family_relation="non_atis"`,
`project_history_boundary="no_project_source_use_evidence_before_v8_subject_to_enumerated_exclusions"`,
`v8_candidate_control_carryover_authority_sha256="00d7cdca4e9893ef1f4e36b6104caf21991ce1ca92e9897d3c5a72d497212f47"`, and false booleans
`researcher_unawareness_claimed`, `model_pretraining_independence_claimed`,
`global_candidate_content_absence_claimed`, `general_content_separation_claimed`,
`independent_replication_claimed`, and `model_scoring_completed`. Terminal status is the narrow
`ready_independently_maintained_non_atis_source_pre_v8_history_screened`, never generic
`independent_source_ready`. The no-training gate remains pending until an independent terminal
readiness review verifies the seal. That review may authorize a later separately reviewed blind
scoring protocol; this plan itself does not score.

## Tests and containment checks

Source-free tests use synthetic fixtures only and must cover:

- v8 carryover exact-set classification, unexpected v8 path stop, opaque raw-universe extra/mode/hash
  stop, and proof that carryover alias subtraction is explicit;
- registry normalization/goldens/framework exceptions/path digest and candidate byte-scanner boundary,
  left-context, deferred-tail, exact-limit, overlimit, strict-UTF8, and JSON cases;
- exact four-file tree and `hash_object_count == len(files) == 4`, accepting 4 and rejecting 3/5;
- full config validation before subprocess; runner argv/environment, no-output policy, durable entry,
  scratch cleanup, no-follow ancestor swaps, hardlinks, modes, identity-checked temp cleanup and fsync;
- acquisition restart table and injected faults at entry/temp/write/fsync/link/unlink/parent-fsync;
- scientific entry durability before any raw open, zero raw read if entry publication fails, and
  non-retry case(c) after incomplete entry;
- every scientific gate, order, short-circuit, public no-prose contract, group-preserving split,
  deterministic reconstruction, private payload custody, and success/rejection terminal cardinality;
- full history/training recensus invoked by prepare and terminal verify;
- retained failure and success verification under final/temp/mode/nlink/hash/schema drift;
- AST closure: no model/tokenizer/GPU/training import/call and only runner contains subprocess/network.

Run with plugin autoload disabled all frozen v4, v4.1, v4.2, v5, v6, v7, v8, and v9 suites,
`py_compile` on v9 builder/runner/tests, exact static AST closure, and prospective hash checks. The
source-free log records commands, runtime versions, exit statuses, test count, and hashes without
source content.

## Milestones

### V9-M1 — plan and source-free control plane

- [ ] This plan is independently reviewed SHIP while v9 data/acquisition paths are absent.
- [ ] Registry and alias screen are regenerated under the exact carryover/history rule.
- [ ] Builder, runner, config, tests, and source-free log satisfy the frozen contracts.
- [ ] Independent source-free implementation review returns SHIP.

Acceptance: v9 namespace absent; quarantine reads zero; all source-free suites and goldens pass; review
binds exact artifact hashes.

### V9-M2 — baseline, authority, and acquisition

- [ ] Full current baseline/process/training inventory is eligible and create-once.
- [ ] Authority manifest directly binds all implementation, predecessor, v8 carryover, and baseline
  bytes and leaves all neural authorizations false.
- [ ] Independent authority review returns SHIP and its exact hash gates the runner.
- [ ] One-shot acquisition produces exactly one valid success or retained acquisition rejection.

Acceptance: no model/GPU/training operation; official commit/tree/files reconstruct; raw custody and
scratch containment pass; no source bytes are printed.

### V9-M3 — scientific gates and replacement payload

- [ ] Durable scientific entry exists before the first raw open.
- [ ] Source-family, pedigree, history support/overlap, license, group, dedup, cross-role, and support
  gates all pass, or the first failure is retained and v9 ends.
- [ ] On success, a fresh blind payload and all public manifests reconstruct from source while the
  coordinator/reviewer never sees semantic payload/source content.
- [ ] Terminal verify and independent readiness/failure review return SHIP.

Acceptance: terminal seal/rejection is canonical; history/training/process recensus matches; all
operation counters are zero; all authorizations remain false until the external readiness review.

## Definition of done

V9 is done only when either:

1. **Ready:** official immutable source, exact pre-candidate history support and overlap, all scientific
   gates, fresh replacement payload custody, terminal seal, and independent readiness review all pass;
   no replication claim or scoring has occurred; or
2. **Rejected:** the first failure is retained canonically, independent failure review returns SHIP,
   payload is absent or its exact non-authoritative failure state is recorded, and v9 is non-retriable.

In both cases v8 remains unchanged, quarantines have zero content reads, no source/payload content is
published, no model/tokenizer/GPU/scoring/K2/branch-training/Stage-C operation occurs, and the paper,
claim ledger, `RESULTS.md`, `ANALYSIS.md`, TODO/RFC status, and final consolidated commit state the
outcome without overclaiming.

## Risks, alternatives, and one-way doors

- **Circular-history exception:** excluding v8 candidate-control artifacts could hide real prior use.
  Mitigation: exact finite set, direct hashes, opaque exact data universe, zero prefix rules, carryover
  occurrence reporting, and reliance on the pre-candidate v8 frozen registry. Any other alias stops.
- **Same-candidate reacquisition:** a retry inside v8 would violate its canonical terminal rejection `6352d5a5...` and SHIP failure review `fd3a40ba...`. V9 instead uses
  a distinct plan, namespace, authority, acquisition entry, salts, and payload, and binds the v8
  failure. Alternative reuse of v8 raw was rejected because a fresh official reacquisition gives a
  cleaner custody chain and keeps v8 entirely immutable/opaque.
- **Another inherited candidate-count bug:** derive all count predicates and command lists from the
  frozen config and test nonmatching counts.
- **Blindness loss:** source/payload content could leak via diagnostics or review. Enforce hash-only
  runner output, aggregate public artifacts, strict reviewer prohibitions, and opaque payload handling.
- **Crash ambiguity:** acquisition or scientific publication can leave case(c). These states are
  deliberately terminal; no cleanup or retry occurs after a subprocess or raw read.
- **One-way doors:** first git subprocess after acquisition entry, first raw open after scientific
  entry, and final payload publication. Each requires prior durable authority and fault-injected tests.

## Verification commands

The implementation review must record exact commands equivalent to:

```bash
PYTHONDONTWRITEBYTECODE=1 python -m py_compile \
  scripts/prepare_msae_independent_source_v9.py \
  scripts/acquire_msae_independent_source_v9.py \
  tests/test_prepare_msae_independent_source_v9.py
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 pytest -q \
  tests/test_prepare_msae_independent_source_v4.py \
  tests/test_prepare_msae_independent_source_v4_1.py \
  tests/test_prepare_msae_independent_source_v4_2.py \
  tests/test_prepare_msae_independent_source_v5.py \
  tests/test_prepare_msae_independent_source_v6.py \
  tests/test_prepare_msae_independent_source_v7.py \
  tests/test_prepare_msae_independent_source_v8.py \
  tests/test_prepare_msae_independent_source_v9.py
```

Baseline, authority, acquisition, prepare, and terminal verify are separate ordered commands. Only the
acquisition runner may use network/subprocess. `prepare` and `verify` are standard-library, model-free,
and network-free. Final claim/repro/secret checks and explicit safe staging occur only after the
terminal v9 review; ignored `data/`, result, pilot, or quarantine paths are never staged.
