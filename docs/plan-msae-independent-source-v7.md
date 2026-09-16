# PLAN — MSAE independent source v7 and replacement blind payload

Status: prospective source contract; no Finnish TDT source blob or v7 payload has been acquired.

## Goal

Acquire one prospectively fixed, previously unused external corpus; establish task support,
source-family separation, cross-role separation, and overlap against all accessible project history
before this protocol authorizes or initiates any neural operation; and create a replacement outcome-blind payload under create-once
custody.

## Prior retained failures and v7 delta

The ATIS v4 lineage remains immutable and rejected:

- v4 stopped at `malformed_feats` before payload creation;
- v4.1 corrected only the UD FEATS grammar, then stopped at a generated-bytecode snapshot drift;
- v4.2 corrected only that snapshot policy, then stopped at
  `duplicate_normalized_utterance` before any support, overlap, payload, model, GPU, scoring, or
  training operation.

Their rejection SHA-256 values are respectively
`f9470c92cf659c85eed8f06aa6c85fec4ed357b228ddb12cd4b23378cc2f0fa6`,
`758527095279226cc918a5faa98f6ea634d4fc084d6786434ecc169bc0188236`, and
`4599f41981a3169c53bf83c3a25ead86a4d05b8056fbeee8c44fc0a43101c477`.
No ATIS payload exists. V7 does not repair, rescore, or reinterpret ATIS.

V5 froze ParTUT and obtained a source-free implementation SHIP review, but it was rejected before
its authority manifest and before any source acquisition. Its create-once
baseline stored `training_root_entries` in global path order while the authority reconstruction
compared a depth-first traversal without a final global sort. Two source-free authority attempts
therefore stopped deterministically at `training_root_delta` even though the 2,116-path set and
every per-path record were identical. The retained baseline, rejection, and independent rejection
review have SHA-256 values `51390650c9d3f7e80cc3810cc3be4b3eae23dc74358c611dca425fe98e31c7a3`,
`06bc319b12d763895d3d7c8038acb8c82b2ad965ef26d0c4cbcb05dd4a097136`, and
`6f83fe07fbb9b12dc7a75fbff2da2490300e0745e0c1fd15ad03b83fd8e5e347`. The review independently
rehashed all 139,663,075,787 training-root bytes with zero mismatch and confirmed that the v5
authority, acquisition entry/outcome, raw source, and private payload paths remained absent. V5 is
not retried.

V6 fixed that ordering defect under a new namespace, froze the same ParTUT commit, passed its
source-free implementation and pre-acquisition authority reviews, and acquired exactly the reviewed
five-file tree. Preparation stopped at the prospectively ordered license gate because the frozen
machine-readable predicate did not recognize the upstream README/LICENSE combination. Its baseline,
authority manifest/review, acquisition, license, rejection, and terminal SHIP review SHA-256 values
are, respectively, `16fe87554f9336a19a6355d144b0c823df9a41c4183144148b0aa66a3eff1515`,
`bf7486235379bd8a74608bada43962555bf34cab5ad9836942875bc6ad190fc9`,
`50ac9661a88713a517fc92bb7b4aaf2c8acde157d97f060aa65de8a60098cddb`,
`49445a3e0e000bc48503b479541b80e319a03a9ae1264a51550f3024a8654c57`,
`cfd3544017eb59eed29e5f3d04e1517955baddfe2bec1c90080bccbea816e29d`,
`8b0df4518b349fad9114eaaae62957a6ab0b047232e4bb59b709ad294b03d3f7`, and
`45d6ae6bf1a64addcb32dcfe5e12d66803987bb3186deb0798fa0dcde39d8016`.
No v6 payload, model, GPU, scoring, or training operation exists. V6 is not reinterpreted or
retried. V7 changes the candidate and namespace; it inherits the globally sorted training-root
reconstruction and every applicable one-shot/custody safeguard from reviewed v6. It also freezes a
candidate-independent license grammar and an explicit document-group split before any Finnish
source blob is acquired.

The exact predecessor set below is direct, not transitive: the v7 builder constant, source-free
implementation review, baseline, authority manifest, and terminal outcome must bind every row's
literal path and SHA-256. Files not listed are ordinary history, not predecessor authority.

| predecessor path | SHA-256 |
|---|---|
| `reports/provenance/msae_independent_source_v4/baseline_inventory.json` | `4467e76ce0ef016f32f58538df6440257b5765dad688317cf0f43e1592c5128b` |
| `reports/provenance/msae_independent_source_v4/source_acquisition.json` | `26766a492aab9044aa93bddf93e4e719372522dc1d63561a6684ae259d93ea2d` |
| `reports/provenance/msae_independent_source_v4/rejection.json` | `f9470c92cf659c85eed8f06aa6c85fec4ed357b228ddb12cd4b23378cc2f0fa6` |
| `reports/provenance/msae_independent_source_v4_1/rejection.json` | `758527095279226cc918a5faa98f6ea634d4fc084d6786434ecc169bc0188236` |
| `reports/provenance/msae_independent_source_v4_2/rejection.json` | `4599f41981a3169c53bf83c3a25ead86a4d05b8056fbeee8c44fc0a43101c477` |
| `docs/plan-msae-independent-source-v5.md` | `1c450895bf836b142bc46dced85afd4f109edd68a96f6e4e91dc5719f0b3fc6b` |
| `reports/adversarial/msae_independent_source_v5_plan_review.md` | `8137a0e7e2dffbf7c4c052e27dc60f5de3f1d1e5568723f5834de5c404aa3abc` |
| `scripts/prepare_msae_independent_source_v5.py` | `f78aba1add310c6a76a05cac4ccc159b9c6aa924e888664d3a54f372e0ebb1e8` |
| `scripts/acquire_msae_independent_source_v5.py` | `6b5c78543c9530c98c24ce99f90ac1caff6ca496d111d8b25889ec448402d11f` |
| `tests/test_prepare_msae_independent_source_v5.py` | `f2cf4d0b58554d688fb4b601bcc739dc6749833d393b49e275178eedccdcac76` |
| `configs/msae_independent_source_v5/acquisition.json` | `6b53511b6d0976ada49a7f090b884d7faeb7db3afb55da9a2f593c369af3e66d` |
| `reports/verification/msae_independent_source_v5_source_free_checks.log` | `87cc02f7ca515a723249091e41116c7d0b0bf6cf58f53c0d45ab741c51b999ef` |
| `reports/adversarial/msae_independent_source_v5_preacquisition_implementation_review.md` | `b098b819f3cc122f4501ccf8465649e070fa46d83484bfc0bc86a283c14a33a2` |
| `reports/provenance/msae_independent_source_v5/baseline_inventory.json` | `51390650c9d3f7e80cc3810cc3be4b3eae23dc74358c611dca425fe98e31c7a3` |
| `reports/provenance/msae_independent_source_v5/preacquisition_control_plane_rejection.json` | `06bc319b12d763895d3d7c8038acb8c82b2ad965ef26d0c4cbcb05dd4a097136` |
| `reports/adversarial/msae_independent_source_v5_preacquisition_control_plane_rejection_review.md` | `6f83fe07fbb9b12dc7a75fbff2da2490300e0745e0c1fd15ad03b83fd8e5e347` |
| `docs/plan-msae-independent-source-v6.md` | `0bba4efcfea868b186f4051faa71d84382b33a8b1f8dc425ed595c7335b515cc` |
| `reports/adversarial/msae_independent_source_v6_plan_review.md` | `e229b167d7cd9c2b93a34a654d57402af35be0533ae1ddbe9f0ae0d32cb7a6d7` |
| `scripts/prepare_msae_independent_source_v6.py` | `af514bf5b701e2814f33085109101da24afc1e735363312f4c447ef0e7b58d65` |
| `scripts/acquire_msae_independent_source_v6.py` | `87df5427acfc5d879eb8546557cb0b7e866f9e9c64ff6e84dadccc811253252f` |
| `tests/test_prepare_msae_independent_source_v6.py` | `c36a64fb9fa12d7face269ba29ed4e4d366f7bce5187220537e7f31f7c578810` |
| `configs/msae_independent_source_v6/acquisition.json` | `9a299aa464a4c8f0765c3d48bc8e225382a8a03734e5c046eb9ef965efeaec22` |
| `reports/verification/msae_independent_source_v6_source_free_checks.log` | `4bda3937addfed1c2d2e133012de44a8f7e4c07a62301949e07b1702edcc22b0` |
| `reports/adversarial/msae_independent_source_v6_preacquisition_implementation_review.md` | `758234c4939c696385fa7a5c6b4679f887aa173ef4c9598aa74a33a67a95d962` |
| `reports/provenance/msae_independent_source_v6/baseline_inventory.json` | `16fe87554f9336a19a6355d144b0c823df9a41c4183144148b0aa66a3eff1515` |
| `reports/provenance/msae_independent_source_v6/preacquisition_authority_manifest.json` | `bf7486235379bd8a74608bada43962555bf34cab5ad9836942875bc6ad190fc9` |
| `reports/adversarial/msae_independent_source_v6_preacquisition_authority_review.md` | `50ac9661a88713a517fc92bb7b4aaf2c8acde157d97f060aa65de8a60098cddb` |
| `reports/provenance/msae_independent_source_v6/source_acquisition_entry.json` | `3057f8f5dd0467ae3e922c3560b41842692391899dda33550fb01f8e29cbef50` |
| `reports/provenance/msae_independent_source_v6/source_acquisition.json` | `49445a3e0e000bc48503b479541b80e319a03a9ae1264a51550f3024a8654c57` |
| `reports/provenance/msae_independent_source_v6/document_group_census.json` | `01bd2e6eebd206d6e4889200760dfaac90a47b80e51f3f339fc3eeeb473c6673` |
| `reports/provenance/msae_independent_source_v6/source_manifest.json` | `05f539b4b21f6e4b039b30332ec296cda5db3f03e3088d1d2d1d600e90a10d1f` |
| `reports/provenance/msae_independent_source_v6/license.json` | `cfd3544017eb59eed29e5f3d04e1517955baddfe2bec1c90080bccbea816e29d` |
| `reports/provenance/msae_independent_source_v6/rejection.json` | `8b0df4518b349fad9114eaaae62957a6ab0b047232e4bb59b709ad294b03d3f7` |
| `reports/adversarial/msae_independent_source_v6_terminal_failure_review.md` | `45d6ae6bf1a64addcb32dcfe5e12d66803987bb3186deb0798fa0dcde39d8016` |

## Frozen source and pre-acquisition evidence

The sole v7 candidate is the official Universal Dependencies repository
`https://github.com/UniversalDependencies/UD_Finnish-TDT.git` at commit
`bfaae13719f249573d940edda6a0d7aa8eec620f`. Before source acquisition, a
normalized alias scan of all 16,117 safely readable current project-history text files used the
contiguous token sequences `ud finnish tdt`, `finnish tdt`, `fi tdt`,
`https github com universaldependencies ud finnish tdt git`, and the commit. Input is strict UTF-8,
NFKC-normalized, casefolded, and tokenized into maximal Unicode Letter/Number runs, so ordinary
space, hyphen, underscore, slash, dot, and compatible Unicode separator variants are equivalent.
The same rule is applied to paths. It found zero content occurrences, zero pathname occurrences,
and zero project-source-use evidence. The screen pins CPython 3.12.3/Unicode 15.0.0 and stores
ASCII-separator, no-break-space, fullwidth-compatibility, underscore, and embedded-word
normalization goldens. The exact 16,117 sorted `{path,sha256,size}` records are
embedded in the registry below and have SHA-256
`545cf2ed68a657ae45a753b3f022bc91ad35e4e60c7587d5803957cad4953533`.
The digest serialization is `json.dumps(records,sort_keys=True,ensure_ascii=True,
separators=(',', ':'),allow_nan=False)`, UTF-8, no final LF, and no domain prefix; each record has
exactly UTF-8 relative-POSIX-string `path`, 64-lowercase-hex `sha256`, and nonnegative-integer
`size`, with unique paths Python-codepoint sorted. The embedded two-record golden hashes to
`2921d955bf00ae2cb8aed787f67c74bde1f62997d7994d484f30cc2de634de61`.
They include all safely readable v5/v6 public/raw text as history, exclude only the exact enumerated
v7 authority/generated paths, and lstat but do not read the three Atlas quarantines. Candidate
discovery used one metadata-only
`git ls-remote --refs ... refs/heads/master` operation to fix the commit, acquired zero source
blobs, and read no source content. These facts are bound at
`reports/provenance/msae_independent_source_v7/preacquisition_alias_screen.json`, SHA-256
`336a3a4082a1096201ae897715629aff870939d003fc9c6650de748ef16df3d7`, schema
`msae_independent_source_v7_preacquisition_alias_screen_v2`, with zero
quarantine reads, model operations, GPU queries, and training runs. It supports only
`project_source_use_unseen_before_v7` if the later digest, pedigree, and full-content gates pass—not
researcher-unawareness, pretraining independence, or content separation by itself. After the
screen, any new candidate alias is permitted only in the exact enumerated v7 authority artifacts;
all v4/v5/v6 artifacts and raw files remain history, never v7 authority.

After this plan and its independent SHIP review, but still before source acquisition, the v7
builder creates a new full current-worktree inventory. It includes all prior ATIS raw files and all
post-v4 work as history. The exhaustive non-history authority set is exactly:
`docs/plan-msae-independent-source-v7.md`;
`reports/adversarial/msae_independent_source_v7_plan_review.md`;
`reports/provenance/msae_independent_source_v7/{preacquisition_alias_screen,historical_source_registry,preacquisition_authority_manifest,baseline_inventory}.json`;
`scripts/prepare_msae_independent_source_v7.py`;
`scripts/acquire_msae_independent_source_v7.py`;
`tests/test_prepare_msae_independent_source_v7.py`;
`configs/msae_independent_source_v7/acquisition.json`;
`reports/verification/msae_independent_source_v7_source_free_checks.log`; and
`reports/adversarial/msae_independent_source_v7_preacquisition_implementation_review.md`; and
`reports/adversarial/msae_independent_source_v7_preacquisition_authority_review.md`.
Each listed path receives exactly `v7_authority`, while only the unpopulated
`data/msae_independent_source_v7/` namespace receives `v7_excluded`; no prefix-based exclusion of
other v7-named paths is allowed. The baseline inventory output path is absent during its own walk and
is bound immediately on atomic publication. The three Atlas
quarantines remain lstat-only and must report zero reads. `.git`, `.venv-atlas`, `.pytest_cache`,
`.generated`, and Python `__pycache__` directories are generated environment, not project history.
Every other regular file is strict UTF-8/NUL classified as `text_scanned`, a safely expandable
archive, or a recognized opaque binary at the frozen suffix list. ZIP, TAR, and GZIP containers are
magic-validated and expanded at one level only when every member is regular/non-encrypted/path-safe,
member count is at most 100,000, cumulative uncompressed bytes at most 1 GiB, and cumulative
expansion at most 20x. A nested archive member is terminal rather than recursively guessed. Every
qualifying UTF-8, NUL-free member is assigned the schema-aware adapter selected by its exact frozen
suffix; a qualifying non-text member must match the recognized opaque-binary magic/suffix policy.
Archives outside the safe bounds are explicitly `binary_unscanned`; archives within them may not
silently hide unscanned text. Classification is content-first, while structured adapter dispatch is
the exact suffix/schema policy.
Unsupported types, symlinks, special files, external hard links, or mutation are terminal. The
positive overlap claim expressly excludes only enumerated opaque `binary_unscanned` content. At
baseline creation the builder derives from exact `text_scanned` history dispositions the same
sorted `{path,sha256,size}` array contract above and must equal the registry's 16,117 `inputs`
byte-for-byte and reproduce
`545cf2ed68a657ae45a753b3f022bc91ad35e4e60c7587d5803957cad4953533`. The frozen registry contains zero archive-member input
records, so any newly safe-expanded history archive/member is drift rather than an implicit
addition. A mismatch is terminal and requires a regenerated screen/registry, amended plan, and new
independent plan review. Authority reconstruction, acquisition-runner preflight, prepare
reconstruction, rejection/success verification, and the terminal seal independently repeat this
exact array equality; merely binding two unequal snapshot hashes is forbidden. At
prepare entry the structural recensus has no prefix exception: it permits as content-bearing
additions only the exact five acquired raw file paths and these exact post-baseline public-chain
files: `baseline_inventory.json`, `preacquisition_authority_manifest.json`, the authority-review
Markdown, `source_acquisition_entry.json`, and exactly one valid `source_acquisition.json` outcome.
The v7 namespace itself must contain exactly a non-symlink `0700` namespace, non-symlink `0700`
`raw/` parent, non-symlink `0555` commit directory, and five `0444` one-link regular files, with no
`private/`, extra file, symlink, hard-link alias, or other subtree before payload publication.

Acquisition uses a detached blob-filtered clone, verifies the exact commit/tree, then installs only
`fi_tdt-ud-train.conllu`, `fi_tdt-ud-dev.conllu`, `fi_tdt-ud-test.conllu`, `README.md`,
and `LICENSE.txt` beneath ignored
`data/msae_independent_source_v7/raw/<commit>/`, with files `0444` and the directory `0555`.
Command stdout/stderr are hashed and must contain no source content. Missing paths, revision drift,
malformed UTF-8/CoNLL-U, or license failure are terminal. No fallback source is permitted after
content acquisition.

The only network/process-capable artifact is `scripts/acquire_msae_independent_source_v7.py`; its
SHA-256 is bound directly by the implementation review, authority manifest, acquisition record,
and terminal seal. It requires `--authority-review-sha256` equal to the actual downstream SHIP
review file hash and reconstructs that review's authority-manifest and baseline hashes before any
subprocess. Its subprocess allowlist is exactly the config's `git check-ignore`, clone, checkout,
`rev-parse HEAD`, `rev-parse <commit>^{tree}`, `ls-tree -z`, and per-file `hash-object --no-filters`
argv; no shell, arbitrary command, model, GPU, tokenizer, or trainer executable is permitted.
`reports/provenance/msae_independent_source_v7/source_acquisition.json` is canonical create-once
JSON with schema `msae_independent_source_v7_source_acquisition_v1`. It records authority manifest,
authority review, durable entry marker, config, and runner hashes; the supplied review-hash argument; exact expanded argv
and minimal environment; every exit status; stdout/stderr byte count and SHA-256 for each command;
resolved commit and tree SHA-1; exact five path/blob SHA-1 pairs from `ls-tree`; each installed file's
SHA-256, Git-blob SHA-1, size, mode, and link count; raw-directory device/inode/mode; the two bound
`git check-ignore` results; and `source_content_printed=false`. The builder recomputes local Git-blob
and SHA-256 identities and rejects Boolean-only tree evidence.

The ignored v7 namespace, raw parents, commit directory, files, acquisition entry marker,
acquisition report, acquisition rejection, and all three named temporaries must be absent at the
clean-state entry gate and are
lstat/no-follow checked. The acquisition cardinality table is: (a) the all-absent state enters the
one-shot protocol; (b) exactly one already-valid canonical success or rejection final plus its
valid bound entry marker, with no
conflicting final/temporary and with all of its schema/mode/link/raw bindings reconstructing,
returns that terminal idempotently with zero subprocesses; (c) every other preexisting final,
temporary, or namespace combination is `invalid_preacquisition_state`, runs zero subprocesses,
does not enter or resume a v7 acquisition attempt and requires a new reviewed protocol without
cleanup or mutation under v7. Every named temporary, whether apparently complete, partial, or
malformed, is case (c) and is never finished, removed, or promoted by this runner. This explicit
non-entry state is not claimed as a retained v7 outcome because no
filesystem protocol can publish into an already-obstructed evidence namespace safely. Immediately
after the clean gate and before the first `git check-ignore` or other subprocess, the runner
atomically publishes and parent-fsyncs create-once
`reports/provenance/msae_independent_source_v7/source_acquisition_entry.json` (schema
`msae_independent_source_v7_source_acquisition_entry_v1`) binding the authority manifest/review,
config, runner, baseline, exact candidate repo/commit/files, false model/K2/Stage-C authorizations,
and `subprocesses_started=0`. Entry publication/durability failure runs zero subprocesses. If no
object was created, or the runner identity-checks and successfully unlinks only the exclusive
temporary created by this invocation and parent-fsyncs that cleanup, the state is all-absent and a
later invocation may enter. If an entry final/temporary remains or cleanup/durability is uncertain,
the state is case (c). The installed entry marker is never removed. Both success and rejection bind
its SHA-256. Therefore
any interruption after entry is visibly non-absent and can never silently re-enter case (a). After
durable entry, the runner creates each directory/file once,
installs every file with exclusive no-follow creation, write-all/fsync, final `0444`/one-link checks,
then makes the commit directory `0555` and fsyncs it and its parent. Public success publication is
atomic no-replace via an exclusive same-directory temporary, write-all/fsync, hard-link install,
unlink, and parent fsync. A caught failure before outcome publication invokes one atomic attempt to retain the first
`source_acquisition_rejection.json`, including the stable code, review/config/runner bindings,
whether any raw path exists, a metadata-only census of partial raw paths, command exit/output hashes
available so far, and `source_content_printed=false`; success and rejection are mutually exclusive,
and any partial namespace or malformed temporary observed by a later invocation is case (c), never
a retry authorization. If the rejection publication succeeds, the runner-detected failure is
terminal. A synchronous failure of success/rejection create, write, file fsync, link, unlink,
final check, parent-directory fsync, or identity-checked cleanup may leave case (c), exactly like
asynchronous power loss or termination outside the handled exception boundary. Recovery is defined
only by the later filesystem state, never by an unverifiable remembered cause: a later invocation
may return an already-installed canonical success or rejection with zero subprocesses only when the
named temporary is absent and the entire final, entry, authority, raw-state, schema, hash, mode,
link-count, and zero-authorization contract reconstructs. This is recovery of complete no-replace
final bytes, not a retry, temporary promotion, or authorization to recreate a missing final. If the
final is absent, a named temporary remains, or any reconstruction fails, the durable entry keeps the
state in case (c). Every non-reconstructing publisher failure is unresolved/blocked and is not
overstated as either a new attempt or a completed retained outcome. The runner never cleans up an
object observed at entry; on a current-invocation error it may unlink only the exact temporary it
exclusively created, and cleanup failure is case (c) unless its later state independently satisfies
the same absent-temporary/full-final recovery rule.

## Source-family, license, and parser gates

The post-acquisition scientific order is literal and has no alternate branch: (1) reconstruct the
baseline/authority/acquisition and perform the no-prefix structural recensus plus pre-process
snapshot; (2) publish `document_group_census.json`; (3) parse all three CoNLL-U files and publish
`source_manifest.json`; (4) publish/check `license.json`; (5) publish/check `source_family.json`;
(6) publish/check `candidate_pedigree.json`; (7) publish/check `dedup.json`; (8) publish/check
`cross_role_overlap.json`; (9) publish/check `history_manifest.json` then `history_overlap.json`;
(10) publish/check `support.json`; (11) publish/check `role_manifest.json` then
`split_manifest.json`; (12) create-once publish and opaquely verify the blind payload; (13) publish
`post_process_snapshot.json`; (14) publish `no_training_gate.json`; and (15) publish/verify
`seal.json`. The first ineligible or failed step is retained and later steps are absent. This one
table defines “first frozen gate” for rejection, inventory, milestones, and tests.

After acquisition, every raw-file SHA-256 is compared with the pre-acquisition inventory. Every
pre-acquisition history text file/member is scanned again for the frozen aliases and must have zero
matches. The exact enumerated `v7_authority` paths are non-history and audited separately; their
candidate mentions must match the reviewed plan/implementation chain. Any history alias, pathname,
or whole-file digest match
is terminal. The source-free historical pedigree registry is regenerated over the same exact
16,117 current-history inputs and frozen at
`reports/provenance/msae_independent_source_v7/historical_source_registry.json`, SHA-256
`a5edbe04ce5ca083aa16cc4cade9d64beffe4a0541d67cd7a42dc05e7ec6712f`, schema
`msae_independent_source_v7_historical_source_registry_v1`. Its exhaustive input rule is every
record in that embedded history input manifest; the registry and alias screen mutually bind its
canonical SHA-256.
It extracts (a) bounded HTTP(S) URL tokens, (b) bounded `UD_*` tokens, and (c) unescaped JSON string
values under the exact case-insensitive keys `source_repo,source_url,repo_url,repository,url,
source_revision,source_commit,commit,revision,dataset,dataset_id,dataset_name,source_name,source_id,
corpus,treebank`. The JSON grammar permits zero through 256 whitespace bytes before the colon and
zero through 256 after it; any source-key construct with 257 consecutive whitespace bytes in either
position is terminal rather than silently omitted. With the 1,024-byte capture maximum, every
accepted complete match is shorter than the carry. Cross-chunk goldens place the longest accepted
form on both sides of a chunk boundary and place both rejected 257-byte forms across it. The
registry freezes CPython 3.12.3/Unicode 15.0.0, Python bytes-regex
`IGNORECASE`, 1,048,576-byte chunks with a 2,048-byte overlap (an occurrence whose end is wholly in
the carried tail is not counted again),
and the exact pattern bytes. A captured byte string is strict-UTF-8 decoded; NFKC normalized;
casefolded; collapsed by `" ".join(value.split())` with `sep=None`; stripped at both boundaries by
the exact codepoint sequence stored in `boundary_strip_codepoints`; then, in order, an initial
`http://` is replaced by `https://`, one terminal slash is removed, a terminal `.git` is removed,
and one remaining terminal slash is removed. Empty/invalid history captures are omitted; the same on candidate metadata is terminal.
Public entries store only `SHA256(domain_utf8 || byte(0x00) || UTF8(normalized_identifier))`, kinds,
counts, and a digest of sorted occurrence paths. The registry records `domain_utf8`,
`separator_hex="00"` with domain `msae-v7/pedigree`, ordered steps, strip codepoints, regex flags/runtime/chunking, and five
input/output/hash goldens, including `.git` and `.git/` spellings required to yield the same
normalized identifier and hash. For every entry, occurrence paths are exact-string deduplicated,
Python-Unicode-codepoint sorted, serialized as a JSON array with `sort_keys=true`,
`ensure_ascii=true`, compact separators, `allow_nan=false`, UTF-8, no final LF and no domain, then
SHA-256 hashed. The registry freezes a duplicate/multi-path golden with SHA-256
`ee69f1b7839d9eaba43b743baa065b321c154e13577dc6dd2a21816b9b2aea65`. It contains 4,052 identifiers and binds its regex bytes, normalization,
complete input records/digest, and runtime, covering all prior sources matched by this deterministic grammar
rather than a hand-maintained shortlist.

Candidate pedigree extraction applies exactly that same grammar to README/LICENSE and also injects
the normalized frozen repo URL, commit, repo name, `fi_tdt`, and source filenames. Exact candidate
repo, commit, dataset identifier, raw digest, or extracted declared-upstream identifier match is
terminal; the three literal normalized values `https://universaldependencies.org`,
`https://creativecommons.org/licenses/by-sa/4.0`, and `cc-by-sa-4.0` are the only allowed shared
non-source exceptions; their NUL-domain hashes and literals are frozen in the registry. Invalid UTF-8, overlength/unescaped candidate identifier syntax, or ambiguous source-line
syntax is terminal rather than ignored. The candidate report records hashes/counts, not source prose.
A pass supports only `project_source_use_unseen_before_v7` plus later audited
utterance separation, not researcher-unawareness or pretraining independence.

The sole eligible upstream license identity is `CC-BY-SA-4.0`; its canonical URL is
`https://creativecommons.org/licenses/by-sa/4.0/`. The v7 grammar is frozen independently of the
candidate bytes. Both `README.md` and `LICENSE.txt` are strict UTF-8, NUL-free, NFKC-normalized, and
casefolded for this gate. URL tokens are maximal runs from the exact ASCII URL-character class
`[A-Za-z0-9._~:/?#\[\]@!$&'()*+,;=%-]`; a positive URL is an entire token exactly equal to
`http://creativecommons.org/licenses/by-sa/4.0`, the same with one terminal slash, or either HTTPS
form. The Unicode code point immediately before and after that maximal ASCII token, when present,
must not have Unicode category Letter or Number. Start/end of input and punctuation delimiters are
eligible; query strings, fragments, extra suffixes, ASCII embedded prefixes, and non-ASCII
Letter/Number prefixes or suffixes are not. Separately,
text is tokenized into maximal Unicode Letter/Number runs. A positive phrase is an exact contiguous
token-array window equal to `['cc','by','sa','4','0']`,
`['creative','commons','attribution','sharealike','4','0']`, or
`['attribution','sharealike','4','0','international']`; adjacent letters/numbers remain in the same
token and therefore cannot satisfy a window. Both files must independently supply at least one
positive URL or phrase occurrence. Contradictions use the same Letter/Number tokens and exact
contiguous arrays `['all','rights','reserved']`, `['no','redistribution']`, and
`['non','commercial','use','only']`. The union is ineligible if any contradiction occurs. Frozen
positive/negative tests include punctuation/case and start/end variants and reject
`prefixhttps://...`, `éhttps://...`, `.../4.0é`, `4.01`, `4.0evil`, URL queries/fragments, adjacent
Unicode letters/numbers, `xcc ...`, and `... 0commercial`.
The public report records each file's SHA-256,
the evidence-kind set and counts (never excerpts), contradiction identifiers/count, canonical
license identity/URL, attribution/share-alike obligations, and that raw/payload text remains
ignored. Missing, ambiguous, or contradictory evidence stops before payload creation.

The token parser and label functions are byte-for-byte inherited from the frozen v4.2 builder except
for v7 namespaces, candidate paths, predecessor bindings, generated-directory exclusion, explicit
document-group capture, and the deduplication rule below. It pins CPython 3.12.3 and Unicode 15.0.0; validates CoNLL-U IDs, roots,
heads, acyclicity, UPOS, DEPREL, and UD FEATS; permits canonical sorted comma multi-values only for
non-`Number` features; and requires `Number` to have at most one recognized value. The task set,
label transformations, missing-label behavior, public lexical-label hashing, and support floor are
unchanged from v4.2, with lexical domains changed exactly to `msae-v7/token\0` and
`msae-v7/lemma\0`. `neutral_prefix_offset`, `entity_binary`, `entity_type`, and `source_genre` are
explicitly unsupported in support, seal, and readiness artifacts. No source values are printed.

## Prospective duplicate and role policy

The natural scoring/support unit is one CoNLL-U sentence, while an explicit upstream document is the
atomic C1/C2 split group. Before role construction the builder publishes a `newdoc id` census.
Only exact comment syntax `# newdoc id = <value>` is recognized; `<value>` is stripped of leading
and trailing Unicode whitespace, must be nonempty, contain no NUL, then is NFKC-normalized and
casefolded to form the canonical group ID. Canonical IDs must be unique within an upstream file and
disjoint across train/dev/test; any cross-partition reuse is terminal before role construction,
independent of later utterance-overlap results. A
marker applies to all following sentences until the next marker. Consecutive markers, a marker with
no sentence before EOF, and any sentence before the first marker in a marker-bearing file are
terminal. If test contains any
marker, one must precede its first sentence and every test sentence must receive exactly one explicit
document ID. If test contains none, each test `sent_id` is prospectively its own group under literal
fallback `sent_id_as_group`. Train/dev groups are censused but do not change their fixed upstream
roles. No filename, topic, speaker, cluster, or document grouping is inferred. The census records
per-file marker/sentence/group counts, duplicate/orphan/empty counts, a SHA-256 of the sorted
canonical explicit-ID hashes per partition, cross-partition intersection count, and the selected
test-group policy, but no document ID or text.

Normalize each sentence by NFKC+casefold of every integer-token FORM joined with one ASCII space.
Before any support calculation or split:

1. within each official partition, group by exact normalized utterance and keep only the sentence
   with lexicographically smallest `(UTF-8 sent_id, source index)`;
2. if a normalized utterance occurs in more than one official partition, exclude every member of
   that group from every role;
3. publish only per-partition input/retained/within-dropped/cross-partition-dropped counts and a
   SHA-256 of the sorted excluded `sent_id` list, never normalized text or token content.

This rule is frozen before Finnish TDT content acquisition. It is a leakage-control transform, not a
claim that duplicates did not exist. Official train maps to discovery, dev to calibration, and the
filtered official test groups are split into C1/C2 without separating a group. Remaining cross-role pairs are checked in both
orientations for: exact normalized equality; a 1--9-token candidate contained in a longer unit;
5-gram Jaccard at least 0.80 when both have at least 10 tokens; or at least four shared distinct
5-grams covering at least 20 and at least 10% of candidate tokens. Any remaining match is terminal.

For every role/task, class support is counted by distinct retained `sent_id`; a class needs at least
20 utterances and a task at least two retained classes. The four-role intersection must include
`absolute_bucket`, `relative_quartile`, `capitalization`, `word_length`, `punctuation`,
`sentence_boundary`, `head_signed_distance`, and `upos_coarse`, plus at least two of
`dependency_depth`, `deprel_coarse`, `number`, `token_identity`, and `lemma_identity`.

## Full history overlap before scoring

The pre-acquisition inventory is immutable after acquisition. For every retained candidate
utterance in discovery, calibration, C1, and C2, apply the same four overlap rules against every
unit extracted from every scanned history file/member. CoNLL-U uses integer-token sentences.
JSONL strictly parses one object per physical line with duplicate-member and nonfinite-constant
rejection; `source_words` and `target_words` must coexist alone and become distinct source/target
subrecords; otherwise `words`, `tokens`, `text`, and `sentence` are applied in that priority order,
and multiple present base fields must normalize identically. JSON accepts only a top-level list or
exactly one list under `records`, `rows`, or `data` and uses the same field adapter. Every structured
row/field has an included or named non-text census outcome, and census arithmetic must close.
Physical lines are additionally scanned as an over-inclusive stream for JSON/JSONL, never used as
a replacement for isolated fields; Markdown, diff, source, config, CSV/TSV, and other strict text
use physical lines. Safe archive members use these same suffix/schema rules. Regression fixtures
include an exact 10--19-token candidate embedded in a much longer JSON line that must be caught by
the isolated-field adapter even when physical-line Jaccard fails. Classification is content-first; structured adapter dispatch follows the exact frozen suffix/schema
policy. Candidate/history comparisons are bidirectional where asymmetric. Any
collision is terminal before support publication or payload construction. The report records
history unit count, candidate count, collision count/reasons/paths/IDs, inventory digest, excluded
binary count, and zero quarantine reads, but no source or history text.

## Split, payload, and custody

V7 inherits the v4.2 manifest, payload, and custody byte contract with these enumerated split
changes: group domain `msae-independent-source-v7/C1C2-group`; schema literals
`msae_independent_source_v7_{split_manifest,role_manifest,payload}_v1`; Finnish TDT repo/commit,
`upstream_partition="test"`, the census-selected test-group policy, and filtered/deduplicated
sentence records. Canonical JSON is `sort_keys=true`, `ensure_ascii=false`, compact separators
`(',', ':')`, `allow_nan=false`, UTF-8, and final LF for every file/record. A group key hashes the
no-LF canonical array `[domain,source_commit,group_id]`. Groups sort by lowercase key then UTF-8
group ID. The ranked universe is exactly the nonempty retained test groups after both within- and
cross-partition deduplication. An explicit or fallback group from which deduplication removes every
sentence is deterministically omitted before ranking and counted in the split manifest; it cannot
shift later ranks. At least two retained groups and one group in each panel are required. Even/odd
zero-based group ranks map the entire group to C1/C2. Rows sort by group rank then
UTF-8 `sent_id`; `within_group_rank` is zero-based in that order. The public manifest stores only
`group_id_sha256=SHA256(UTF8(group_id))`, never the group ID itself. It exposes `sent_id`, panel,
group key/hash/rank, within-group rank, source-record hash, counts, and upstream partition, never
forms, lemmas, normalized text, or un-hashed document IDs. The role manifest uses the same row order.
A closing identity requires `pre_dedup_group_count = retained_group_count +
fully_removed_group_count`, the sum of per-group retained row counts equals `record_count`, every
retained group occurs in exactly one panel, and all published counts/digests reconstruct. A literal
two-group/three-row manifest golden and its SHA-256 are fixed in the source-free test
before implementation review and are then bound in the implementation transcript.

The private payload path is
`data/msae_independent_source_v7/private/blind_payload.jsonl`. Each row has exactly
`schema_version`, `source_repo`, `source_commit`, `upstream_partition`, `panel`,
`group_key_sha256`, `group_id_sha256`, `group_rank`, `within_group_rank`, `sent_id`, and `tokens`;
`tokens` is the ordered array of exactly integer `id`,
string `form/lemma/upos/deprel/feats`, and integer `head`. Before use, `git check-ignore` must bind
the raw/private roots. Directory and target are lstat/no-follow checked; private directory is a
non-symlink `0700`; target and named temporary must be absent. Temporary creation is exclusive
`0600`; exceptions and catchable signals remove it, while any abandoned temporary observed on
restart is a terminal retained failure without overwrite; file and directory are fsynced, and atomic no-replace
hard-link installation refuses symlinks, hard-link aliases, path-identity changes, or preexistence.
Final lstat requires a regular one-link `0600` target under the same directory identity. It is then
verified only by streaming opaque SHA-256 and lstat. Reviewers never receive payload content.
“Blind” means model-outcome blind: readiness necessarily parses public source text, but no neural
score is generated and the sealed payload is not semantically reopened. On a scientific-gate
failure, `rejection.json` binds `scientific_artifact_inventory` under schema
`msae_independent_source_v7_scientific_artifact_inventory_v1`. Its ordered universe is every final
and same-directory `.<name>.building` path for: `document_group_census.json`,
`source_manifest.json`, `license.json`, `source_family.json`, `candidate_pedigree.json`,
`dedup.json`, `cross_role_overlap.json`, `history_manifest.json`, `history_overlap.json`,
`support.json`, `role_manifest.json`, `split_manifest.json`, `post_process_snapshot.json`,
`no_training_gate.json`, and `seal.json`. For each listed name in that literal order, the array
appends the final and then its named temporary. Every path has exactly either
`{"path":...,"state":"absent"}` or a `present` entry with exact relative path,
`state="present"`, lstat `type` from `regular|directory|symlink|other`, and literal keys
`device`, `inode`, `mode`, `nlink`, `size`, and `mtime_ns`;
only a non-symlink regular final also has SHA-256, while named temporaries are never opened. The
separate `payload_state` uses the same explicit absent/present and lstat fields for
`blind_payload.jsonl` and `.blind_payload.jsonl.building`; only a final regular one-link `0600`
payload receives an opaque SHA-256. No private temporary or quarantine content is read. The
rejection final and its publisher temporary are outside the self-referential inventory; any later
invocation that observes that temporary treats it as the explicit invalid non-entry state described
above and never opens, finishes, removes, or promotes it. Rejection verification reproduces the
literal ordered inventory and payload state byte-for-byte. Thus, when `rejection.json` publication
succeeds, a scientific publisher failure at any earlier named public boundary, including a pending
`no_training_gate.json`, is bound. A later invocation may recover a rejection or seal after any
publisher exception only from an absent named temporary plus a fully reconstructing canonical
final, with zero continuation of scientific work; the recovery decision is state-based because the
filesystem does not preserve the failure cause. An absent or non-reconstructing final, or any
remaining publisher temporary, is unresolved case (c). Therefore an abandoned payload temporary or
invalid/symlink target is a reconstructable retained failure rather than an unverifiable state.

The separately reviewed networked acquisition runner is frozen to a detached, blob-filtered `git` fetch and
five-path checkout with a minimal `PATH`, `HOME` set to a fresh empty temporary, prompts and hooks
disabled, no credentials/proxies, quiet output, and exact argv/environment hashes. The builder runs
post-acquisition with proxy variables removed and no network/process capability. Its AST allowlist
rejects socket/HTTP/process/dynamic-loading modules, `ctypes`, dynamic import/eval/exec, and every
`os` process primitive (`system`, `popen`, `spawn*`, `exec*`, `fork*`, `posix_spawn*`). Negative
fixtures exercise indirect process/network/dynamic-load spellings. Before acquisition and after
payload/rejection, a point-in-time `/proc` inventory records only PID, kernel start time, executable basename,
forbidden-name code, and domain-separated command-line hash; either snapshot containing any
forbidden trainer/model/GPU-worker identity is terminal. These observations support only
builder-initiated zero-operation claims plus the two explicit point snapshots; they do not claim to
observe ephemeral external processes between snapshots. The pre-acquisition inventory separately binds every `results/`, checkpoint-like,
`train_metrics.jsonl`, and registered training-root entry; the final comparison requires zero delta.
These external observations and the statically process-free builder support the narrowly stated
builder-initiated zero model/GPU/scoring/training claims. No GPU API or `nvidia-smi` is invoked.

The seal binds the plan/review, builder/acquisition-runner/tests, pre-acquisition screen and inventory, source tree/raw
hashes, license, family/dedup/role/history/support/split artifacts, and payload path/hash/size/count/
mode/link count. `no_training_gate.json` must keep model scoring, K2/branch training, and Stage C
unauthorized. A readiness pass is not an independent model result.

## Milestones

### V7-M1 — prospective plan and source-free implementation

- [ ] Independent plan review returns SHIP while all v7 source/payload paths remain absent.
- [ ] Implement and test every source-free parser, adapter, archive, dedup, split, custody, pedigree,
      capability, inventory, and separately reviewed acquisition-runner/validation path; bind the exact
      v4/v4.1/v4.2 rejection chain, v5 control-plane rejection chain, and v6
      plan/reviews/builder/runner/test/config/baseline/authority/acquisition/license/rejection chain.
      Regression-test both builder and runner global training-root
      ordering with fixtures whose depth-first walk order differs from lexical path order.
- [ ] Obtain an independent source-free implementation diff SHIP review binding the exact
      builder/acquisition-runner/test, acquisition config, pedigree-registry reconstruction, and test/static transcript.
- [ ] Only after that review, create the full current pre-acquisition inventory with zero quarantine
      reads/unsupported files, zero forbidden baseline processes, unchanged training/checkpoint roots,
      and prior ATIS raw included as history.
- [ ] Then create a no-replace pre-acquisition authority manifest binding exact plan/plan-review,
      corrected screen, pedigree registry, every predecessor, builder/acquisition-runner/test/acquisition config,
      source-free transcript and implementation review, the exact baseline-inventory SHA-256, and the
      zero-process/training-root evidence. Obtain an independent provenance-only authority-manifest
      SHIP review. Source acquisition remains unavailable until that final review exists and its hash
      is passed explicitly to the frozen acquisition command.

### V7-M2 — source and scientific gates

- [ ] Exact commit/tree/files/license are acquired without content output.
- [ ] The literal 15-step post-acquisition table above—structural recensus/snapshot, document
      census, parser/source manifest, license, source family, pedigree, dedup, cross-role overlap,
      history, support, role/split, payload, post snapshot, no-training gate, and seal—passes in
      order, or the first failure is retained and ends v7.

### V7-M3 — payload, review, and stop

- [ ] On success only, public manifests reconstruct, private payload is create-once `0600`, and all
      hashes/counts agree.
- [ ] An independent provenance-only source-readiness review returns SHIP.
- [ ] The reviewed v7 builder/runner initiated no model, tokenizer, GPU, scoring, K2/branch training,
      or Stage C operation; both point snapshots contain zero forbidden identities and bound project
      training roots have zero delta.

## Verification plan

- [ ] Before acquisition, test-first fixtures cover parser/FEATS, exact labels, dedup precedence/
      exclusion, explicit-newdoc and sent-ID-fallback group branches, no group split across panels,
      overlap directions/boundaries, isolated structured fields,
      safe and nested archive policy, split golden, inventory/quarantine/generated-cache handling,
      create-once/abandoned-temp custody, output canaries, and static no-neural imports.
- [ ] Before acquisition, negative capability fixtures reject indirect process/network/dynamic-load/
      `ctypes` paths; exact acquisition argv/environment validates; `/proc` has zero forbidden
      identities; GPU APIs are not queried; and results/checkpoint/training-root baseline is bound.
- [ ] Source-free fault injection covers create/write/fsync/link/unlink/final-check/parent-fsync for
      acquisition success, acquisition rejection, scientific artifacts, and scientific rejection;
      preflight→entry-marker→first-subprocess tests prove the marker is durable before any `git`, and
      real re-entry/terminal-verifier tests distinguish a successfully retained terminal, state-based
      recovery of any temporary-absent fully reconstructing canonical final after publisher uncertainty,
      and unresolved case (c), without retry or temporary promotion.
- [ ] All v4/v4.1/v4.2/v5/v6/v7 tests pass with plugin autoload disabled; `py_compile` and AST closure pass.
- [ ] Strict-parse every public JSON; recompute bindings and payload lstat/opaque hash only.
- [ ] Run claim review, reproducibility checks, secret scan, forbidden-claim scan, and
      `git diff --check` before commit.

## Definition of done

- [ ] After the all-absent acquisition entry gate, a successfully published outcome is either a
      reviewed retained failure at its first frozen gate or a reviewed
      `independent_source_ready_for_future_prescore_protocol` seal with a replacement payload.
      Outcome-publisher I/O/cleanup failure or asynchronous interruption may instead leave the
      explicitly blocked case-(c) state and is never silently retried. The only recovery is later
      zero-work acceptance of an already-installed, temporary-absent canonical terminal final after
      publisher uncertainty, and only after its complete contract reconstructs; cause is irrelevant.
- [ ] Every public artifact and the opaque payload binding reconstructs exactly with zero quarantine
      content reads and zero builder/runner-initiated model/GPU/scoring operations or K2/branch
      training runs. A readiness success has zero forbidden identities in both point snapshots and
      zero bound training-root delta; a retained failure binds the actually observed eligible or
      ineligible terminal snapshot and unchanged/changed/unavailable training-root status while
      keeping every authorization false.
- [ ] The terminal gate keeps model scoring, K2/branch training, and Stage C unauthorized; an actual
      independent replication requires a separate future reviewed prescore protocol and blind scoring.

## One-way doors

Source download, parsing, dedup counts, support, overlap, and payload publication are one-way:
thresholds, roles, tasks, adapters, and candidate cannot change afterward.
