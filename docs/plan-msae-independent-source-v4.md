# PLAN — MSAE independent source v4 and replacement blind payload

Status: revised prospective source contract; no source blob has been acquired.

## Goal

Acquire one prospectively fixed external corpus, test prior source use,
task support, cross-role separation, and accessible-project-history overlap
before any neural operation, and seal a replacement evaluation payload whose
model outcomes remain blind.

## Non-goals

- No model/tokenizer import, weight load, GPU query, representation extraction,
  endpoint scoring, MSAE/K2/branch training, or Stage C.
- No reuse or reinterpretation of AMALGUM, GUM, EWT, Few-NERD, WNUT, or any
  Atlas private payload.
- No claim of speaker-, document-, model-pretraining-, or population-level
  independence. The strongest possible outcome is utterance-level separation
  from the audited accessible project history and official ATIS roles.
- No entity, genre, or neutral-prefix task: those annotations/interventions are
  not supplied by the candidate and may not be synthesized during readiness.
- No fallback after content exposure. Candidate failure is retained and ends
  this source attempt.

## Frozen authority and baseline

The only candidate is the official Universal Dependencies repository
`https://github.com/UniversalDependencies/UD_English-Atis.git` at commit
`3ba83a5ded2c2b6e69ea2fa862806a892ae62a53`. The pre-content baseline is Git
HEAD `7e1a6fc7a26a870a4edcf29c96b7cdf3cdbd7faa`; immediately before acquisition,
the builder records the NUL-delimited `git status --porcelain=v2 -z` bytes and
their SHA-256, plus a project-wide lstat inventory. The source-readiness plan,
its reviews, and v4 program/tests are explicitly tagged `v4_authority` in that
inventory and excluded from the historical-content comparison; no other v4
path is exempt.

Acquisition uses a detached blob-filtered clone, verifies the exact commit and
tree, then checks out only `en_atis-ud-train.conllu`,
`en_atis-ud-dev.conllu`, `en_atis-ud-test.conllu`, `README.md`, and
`LICENSE.txt`. A different license filename, unavailable revision, missing
path, malformed UTF-8, invalid CoNLL-U, or changed tree is terminal.

Before acquisition, the existing `data/` ignore rule is verified to cover the
raw, private, and temporary v4 roots. Raw files are copied to
`data/msae_independent_source_v4/raw/<commit>/` and changed to `0444` only after
hash verification. No source content is printed to stdout/stderr.

## Source-family and license gates

`source_family.json` inventories every pre-acquisition pathname and scans every
classified text file, case-insensitively, for the URL, repository name,
`UD_English-Atis`, `English-Atis`, `en_atis`, the frozen commit, and the token
`ATIS`. Prior name-level consideration is disclosed rather than misclassified as
source use: exactly five `ATIS` hits are allowed, only at
`PLAN_ATTEMPT13.md:280`, `PLAN_RELATIONAL_EDGE_V1.md:221,412`, and
`reports/provenance/relational_attention_edges_v1_discovery1_plan_snapshot.md:132,316`,
whose complete file SHA-256 values are respectively
`194294213047f528fddcc0374e4a1d4d5a185ce01f5d07eb13bce688f9820db8`,
`8d1d6c172da0d8302410659c8cfff948c59e1df0fbbe03d972adb5c148c49bcd`,
and `5a5e8fb6d1396632c700fa51386711d022a6107bb02572fa7d7c94790bdb0c51`.
Those lines record planning-only consideration and rejection for document-group
inference, not acquisition or scoring. Exact `v4_authority` matches are also
expected and listed. `docs/plan-msae-project-completion-2026-09-14.md` is an
additional exact planning-authority exception at SHA-256
`c99e74db5897ec51732795ca27be5bbf9c9c13486d96b37772f0407fdf61e62b`.
Any other family alias, provenance-field, pathname, or whole-file digest match
is terminal; source-content similarity is governed only by the frozen overlap
rules below. Raw source hashes
are compared with every pre-existing safely read file digest. A pass supports
only `previously_considered_but_project_source_use_unseen` plus the audited
utterance separation—not name novelty or researcher-unawareness.

The expected upstream license is Universal Dependencies' declared
CC BY-SA 4.0 (`CC-BY-SA-4.0`). Eligibility requires the primary upstream
`LICENSE.txt` at the frozen revision to identify those terms, and the README to
agree. `license.json` records source URL, license path/hash, declared identity,
license URL, attribution/share-alike obligations, and the decision that private
local derivation is permitted while redistributed derivative text would
require attribution and compatible share-alike terms. Missing, contradictory,
unrecognized, or more restrictive terms are terminal before payload creation.
The raw corpus and payload remain ignored local data; only hashes, counts,
license metadata, and provenance are committed.

## Parser and exact label contract

The standard-library parser rejects duplicate JSON members, invalid UTF-8,
malformed CoNLL-U rows, empty sentences, duplicate/missing/NUL/newline-bearing
`sent_id`, noncontiguous integer token IDs, invalid HEAD indices, multiple or
missing roots, dependency cycles, missing FORM/LEMMA/UPOS/DEPREL, and duplicate
normalized utterances. Multiword and empty-node rows are counted but excluded
from all task rows and the payload; only integer-token rows are retained.

For a validated sentence with `n` integer tokens and 1-based token `i`, each
task emits at most one row for that token. FORM and LEMMA are NFC normalized.
Execution requires CPython `sys.version_info[:3] == (3,12,3)` and
`unicodedata.unidata_version == "15.0.0"`; drift is terminal before parsing.
The exact labels are:

| Task | Pure transformation / domain |
|---|---|
| `absolute_bucket` | `str(min(7, i-1))`; positions 8+ share class `7` |
| `relative_quartile` | `str(min(3, 4*(i-1)//n))` |
| `token_identity` | NFC FORM then Unicode `casefold()` |
| `lemma_identity` | NFC LEMMA then Unicode `casefold()`; `_` is missing |
| `capitalization` | `letters=''.join(c for c in FORM if c.isalpha())`; in order: empty→`nonalpha`, `letters.islower()`→`lower`, `letters.isupper()`→`upper`, `letters.istitle()`→`title`, otherwise `mixed` under the pinned Python interpreter |
| `word_length` | number of NFC FORM code points: `1`, `2`, `3_4`, `5_7`, or `8p` |
| `punctuation` | `PUNCT` iff FORM is nonempty and every code point's Unicode category starts `P`; else `NONPUNCT` |
| `sentence_boundary` | `single` if `n=1`; otherwise `initial` for `i=1`, `final` for `i=n`, else `interior` |
| `head_signed_distance` | `ROOT` when HEAD=0; otherwise side `L` for `HEAD-i<0`, `R` for positive, plus magnitude `1_2`, `3_4`, or `5p` |
| `dependency_depth` | number of parent edges to the root, classes `0`, `1`, `2`, `3`, `4p` |
| `upos_coarse` | exact value in `{ADJ,ADP,ADV,AUX,CCONJ,DET,INTJ,NOUN,NUM,PART,PRON,PROPN,PUNCT,SCONJ,SYM,VERB,X}` |
| `deprel_coarse` | substring before the first `:`, in `{acl,advcl,advmod,amod,appos,aux,case,cc,ccomp,clf,compound,conj,cop,csubj,dep,det,discourse,dislocated,expl,fixed,flat,goeswith,iobj,list,mark,nmod,nsubj,nummod,obj,obl,orphan,parataxis,punct,reparandum,root,vocative,xcomp}` |
| `number` | the sole FEATS `Number` value in `{Sing,Plur,Dual,Trial,Pauc,Grpa,Grpl,Inv,Ptan}`; absent otherwise |

FEATS is `_` or a `|`-separated sequence of nonempty `key=value` items. Keys
must be unique; a value may not contain `,`, `|`, or `=`. Duplicate keys,
multi-valued fields, empty items, and a Number value outside the literal table
are terminal. Golden fixtures are frozen in the tests before real source parsing: a
five-token sentence must yield absolute `0..4`, relative `0,0,1,2,3`, boundary
`initial,interior,interior,interior,final`; HEAD values `0,1,2,2,3` must yield
`ROOT,L1_2,L1_2,L1_2,L1_2` and depths `0,1,2,2,3`; forms `A,AB,Ab,a-b,...`
exercise every surface bin. Root, cycle, bad relation, duplicate FEATS, MWT,
empty-node, and missing-lemma fixtures are mandatory.

For each role and task, count a class by distinct `sent_id`, never token rows.
A class is retained only with at least 20 distinct utterances in that role; a
task is role-eligible only with at least two retained classes. The all-role
intersection must include `absolute_bucket`, `relative_quartile`,
`capitalization`, `word_length`, `punctuation`, `sentence_boundary`,
`head_signed_distance`, and `upos_coarse`, plus at least two of
`dependency_depth`, `deprel_coarse`, `number`, `token_identity`, and
`lemma_identity`. Missing labels emit no task row. Support output contains
literal class names only for the eleven nonlexical tasks. Token/lemma class IDs are
`SHA256(UTF-8("msae-v4/token\0" or "msae-v4/lemma\0") || UTF-8(label))`; only
these domain-separated hashes and counts are public. Schema-aware leak tests
reject tracked/output fields named `form`, `lemma`, `words`, `tokens`, `text`,
or `sentence` outside frozen schema metadata; high-entropy planted FORM/LEMMA
canaries must also be absent from every tracked byte stream and captured output.

## Natural unit, official roles, and cross-role separation

The natural unit is one CoNLL-U sentence/ATIS utterance. Official `train` maps
to discovery, `dev` to calibration, and official `test` to C1/C2. Speaker or
document grouping is not asserted.

Normalize an utterance by NFKC+casefold of each FORM, discard no token, and join
with one U+0020. Exact duplicates across or within official roles are terminal.
After reconstructing the frozen test split in memory, the substantive-overlap
rules below are applied in both orientations to each of the six role pairs among
discovery, calibration, C1, and C2; any match is terminal. Therefore a pass supports utterance-level
exact and template-overlap separation under these rules, not speaker or semantic
independence.

## Full accessible-history inventory and overlap gate

The snapshot covers every regular file under the repository, including top-level
files, `analysis`, `configs`, `data`, `docs`, `pilot_outputs`, `pilot_runs`,
`prereg`, `reports`, `results`, `scripts`, and `tests`. `.git`, `.venv-atlas`,
`.pytest_cache`, and `.generated` are recorded as `generated_environment` by
path rule, not treated as project history. The project-local `.cache`, including
`.cache/huggingface`, is included normally: text is scanned and recognized
archives are inventoried/hashed. Symlinks, changing stat tuples, devices, and
sockets are terminal.

The three exact quarantines are enumerated and lstat-only:

- `data/atlas_v1/private/final.jsonl`;
- `data/atlas_v1/private/final.records.jsonl`;
- `data/atlas_v1/private/final.units.jsonl`.

A tripwire makes an attempted content open fatal and the report must record zero
quarantine reads. V4 raw/private/temp files are `v4_excluded`; the plan, its
reviews, program, and tests are `v4_authority`. All other files receive exactly
one disposition, chosen content-first rather than by an extension filter:

1. `text_scanned`: every file, regardless of suffix, that decodes as strict
   UTF-8 and contains no U+0000;
2. `binary_unscanned`: non-UTF-8 or NUL-bearing files only when their final or
   compound suffix is in the frozen observed binary/archive/object list
   (`.pyc,.so,.a,.pt,.npy,.npz,.pkl,.png,.pdf,.parquet,.feather,.orc,.fits,
   .gz,.zip,.tar,.lock`) after magic/NUL validation; filenames and full SHA-256
   are still included in the source-family byte/name audit. Standard-library
   gzip/zip/tar members are recursively classified and text-scanned when total
   uncompressed bytes are at most 1 GiB, every member is regular, expansion is
   at most 20×, and member count at most 100,000. Larger/opaque object containers
   remain explicitly `binary_unscanned`; or
3. `terminal_unsupported`.

Hard links are not independently opened. Complete `(device,inode)` alias groups
are listed, one non-quarantine representative is hashed/scanned, and its result
is assigned to all aliases. A group is terminal if `st_nlink` exceeds the
enumerated in-repository aliases or if a quarantined inode has another alias.
No `terminal_unsupported` file is permitted. Every non-generated,
non-quarantine regular file has path, size, mode, device/inode, mtime-ns,
SHA-256, disposition, adapter, and extracted-unit count in
`history_manifest.json`. Each quarantine instead records the lstat identity,
`sha256: null`, `adapter: "quarantine_lstat_only"`, and `content_reads: 0`;
census sums must equal the
snapshot. The positive claim is limited to scanned accessible text and safe
archive members; it expressly excludes opaque `binary_unscanned` object content.
Text adapters are: CoNLL-U integer-token sentences; all JSON-family
string literals plus physical-line token streams (streaming, never whole-file
load); and physical lines for other text. CSV/TSV and source/config files use
the same physical-line stream. This deliberately over-includes keys and prose.

All overlap text is NFKC+casefolded into Unicode alphanumeric lexical tokens.
For candidate/history pairs the candidate is always the ATIS unit. For each
source-to-source role pair, run the rules twice, once with each side as the
candidate. Block on any of:

1. exact normalized full-unit equality at any nonzero length;
2. candidate length 1--9: its full token sequence occurs contiguously inside a
   longer extracted history unit;
3. both lengths at least 10: 5-gram Jaccard `>=0.80`;
4. at least four shared distinct 5-grams covering at least 20 candidate token
   positions and at least 10% of candidate tokens.

Thresholds are inclusive. Planted exact/contained/boundary/near-overlap,
punctuation-only, JSON-string, long-line streaming, alias, binary-magic, changing
file, and quarantine fixtures must pass. Any collision terminates the source
attempt before support publication or payload construction.

## Deterministic C1/C2 split and payload byte contract

For each official-test utterance, construct canonical UTF-8 JSON bytes for the
array `["msae-independent-source-v4/C1C2", sent_id, normalized_utterance]` with
`ensure_ascii=false`, separators `(',', ':')`, no trailing space/newline, and
reject U+0000 in either string. Let `h=SHA256(bytes)`. Sort by the tuple
`(h lowercase hex, UTF-8 sent_id bytes)` and assign even zero-based ranks to C1,
odd ranks to C2. A golden vector with non-ASCII and punctuation is fixture-bound.

The payload is UTF-8 JSON Lines in that same sorted order. Every line is a
canonical object (`sort_keys=true`, `ensure_ascii=false`, separators
`(',', ':')`) with exactly:

- `schema_version="msae_independent_source_v4_payload_v1"`;
- `source_repo`, `source_commit`, `upstream_partition="test"`;
- `panel` (`C1` or `C2`), `split_key_sha256`, `sent_id`; `split_key_sha256` is exactly
  this record's `h` defined above, not a manifest digest;
- `tokens`, an ordered array of objects containing exactly integer `id`, string
  `form`, `lemma`, `upos`, integer `head`, string `deprel`, and string `feats`.

Every record including the final record ends with LF; MWT/empty-node rows and
comments are absent. Public split metadata exposes only IDs, panels, ranks,
counts, byte counts, and hashes—never forms, lemmas, labels, or normalized text.
`split_manifest.json` is one canonical (`sort_keys=true`, `ensure_ascii=false`,
compact separators, final LF) object with
`schema_version="msae_independent_source_v4_split_manifest_v1"`, the exact
`source_commit`,
`split_algorithm="sha256-canonical-json-array-v1-even-C1-odd-C2"`,
`record_count`, `C1_count`, `C2_count`, and `entries`; each entry has exactly
`sent_id`, `panel`, `zero_based_rank`, and the record-level
`split_key_sha256`, in rank order. The two-row serialization golden object uses
source commit forty `0` characters, entries (`é`,`C1`, rank 0, 64-zero key) and
(`x!`,`C2`, rank 1, 64-`f` key), counts 2/1/1, and has canonical-file SHA-256
`bee7c051e64b1a8b113843da9200928503ab5a58fc85aff9af61700ece70b128`.

`role_manifest.json` is canonical under the same JSON byte rules and has exactly
`schema_version="msae_independent_source_v4_role_manifest_v1"`,
`source_commit`, and `roles`. `roles` has exactly `discovery` and `calibration`;
each value has `upstream_partition` (`train` or `dev`), `record_count`, and
`entries` in upstream sentence order. Each entry has `zero_based_rank`,
`sent_id`, and `source_record_sha256`, the SHA-256 of the canonical token-object
array used in the private payload. It exposes no token content and binds the
future prescore input boundary.

“Blind” throughout this contract means outcome-blind: no neural scores exist and
the sealed payload will not be semantically inspected after construction. It
does not mean source-content-blind, since the public upstream corpus and its
labels are necessarily inspected once for readiness.

## Blind custody and no-neural enforcement

Private directory mode is `0700`. The builder uses an unnamed/private `0600`
temporary under that directory, fsyncs it and the directory, and installs with
Linux `renameat2(RENAME_NOREPLACE)` or a hard-link create-once equivalent;
existing destination, abandoned named temporary, symlink, hard link, signal, or
exception is terminal. Exception records contain only error codes, path aliases,
row numbers, and hashes—never source lines, forms, lemmas, or labels. Captured
stdout/stderr leak tests plant canary text and require it absent. After sealing,
only lstat and streaming opaque-byte hashing are allowed; these are explicitly
not semantic content reads. Reviewers receive provenance only, never payload.

The preparation program imports only a frozen standard-library allowlist and
contains no subprocess, socket, HTTP, dynamic import, `torch`, `transformers`,
CUDA, ROCm, `nvidia-smi`, model, tokenizer, or training symbol. Acquisition is a
separate exact `git` command transcript run before the builder; command argv and
environment are closed, stdout/stderr are hash-recorded, and no source content is
echoed. A process inventory from `/proc` is inspected in memory before and after
and checked for newly launched forbidden command names; it is not a GPU query.
The published form contains only PID, kernel process start time, executable
basename, forbidden-match code, and a domain-separated command-line hash—never
raw arguments, environments, or unrelated paths. PID plus start time defines
identity. Negative fixtures
must make AST dynamic-import/subprocess/socket and forbidden command strings
fail. The seal's zero-operation counters are backed by this transcript and
static/fixture evidence, not self-report alone.

## Artifacts

Tracked:

- `scripts/prepare_msae_independent_source_v4.py` and its tests;
- `reports/provenance/msae_independent_source_v4/{baseline_inventory,source_acquisition,source_family,license,history_manifest,history_overlap,cross_role_overlap,support,role_manifest,split_manifest,seal,no_training_gate}.json`;
- a fresh source-readiness review.

Ignored local: immutable raw files and the create-once private
`blind_payload.jsonl`. The seal binds the plan/review, program/tests, upstream
tree and raw/license hashes, every provenance artifact, payload hash/size/count
and mode, unsupported tasks, and independently evidenced zero model/GPU/training
operations.

## Milestones

### S1 — prospective authority

- [ ] Corrected plan and independent SHIP review exist before source blobs.
- [ ] Baseline HEAD/status/inventory, source/revision, license criteria, exact
  labels, overlap rules, split bytes, payload bytes, and custody are frozen.

### S2 — implementation and source gate

- [ ] Fixture tests, compile, AST allowlist, and output-leak tests pass.
- [ ] Exact upstream revision/license are acquired and hashed without content
  output; source-family audit passes or a terminal failure is retained.

### S3 — history, support, and payload

- [ ] Full inventory closes with zero quarantine reads/unsupported files.
- [ ] Historical and official-role overlap have zero blockers.
- [ ] Four-role support passes the frozen intersection.
- [ ] C1/C2 reconstruction agrees; payload is create-once `0600` and sealed.

### S4 — independent review and stop

- [ ] A fresh reviewer checks provenance without payload content.
- [ ] `no_training_gate.json` reports
  `independent_source_ready_for_future_prescore_protocol` or the exact retained
  failure. It cannot authorize model scoring or training.

## Verification plan

- [ ] `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python -m pytest -q tests/test_prepare_msae_independent_source_v4.py` passes.
- [ ] `python -m py_compile` plus the frozen AST/command/network scan passes.
- [ ] Strict-parse JSON/JSONL outputs; recompute every artifact/source hash,
  history census, support count, split assignment, and payload byte hash.
- [ ] Verify payload only by lstat/opaque streaming hash: regular, one link,
  `0600`, expected bytes/records/hash; captured output contains no canary/source
  text.
- [ ] Run `git diff --check`, secret scan, claim review, and an independent
  source-readiness review before committing.

## Definition of done

- [ ] The candidate is either durably rejected at its first failed frozen gate, or raw
source/license provenance, source-family audit, full-history/cross-role overlap,
support, deterministic payload, custody, and no-neural evidence agree and an
independent reviewer returns SHIP. The only positive status is
`independent_source_ready_for_future_prescore_protocol`; it is not an independent
model result and authorizes neither scoring nor K2/branch training.

## Risks and one-way doors

ATIS may be formulaic, historically present, inadequately supported, or
license-ineligible; any is a valid terminal negative. Public upstream text may
have appeared in pretraining, which remains unknown. Source download, support
observation, split, and payload sealing are one-way, so no threshold, adapter,
task, license policy, or fallback changes after acquisition. The project is
113+ GiB; all scans are streaming and must fail closed on mutation rather than
silently omit large artifacts.
