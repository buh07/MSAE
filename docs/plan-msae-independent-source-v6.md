# PLAN — MSAE independent source v6 and replacement blind payload

Status: prospective source contract; no ParTUT source blob or v6 payload has been acquired.

## Goal

Acquire one prospectively fixed, previously unused external corpus; establish task support,
source-family separation, cross-role separation, and overlap against all accessible project history
before this protocol authorizes or initiates any neural operation; and create a replacement outcome-blind payload under create-once
custody.

## Prior retained failures and v6 delta

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
No ATIS payload exists. V6 does not repair, rescore, or reinterpret ATIS.

V5 then froze this same candidate and obtained a source-free implementation SHIP review, but it
was rejected before its authority manifest and before any source acquisition. Its create-once
baseline stored `training_root_entries` in global path order while the authority reconstruction
compared a depth-first traversal without a final global sort. Two source-free authority attempts
therefore stopped deterministically at `training_root_delta` even though the 2,116-path set and
every per-path record were identical. The retained baseline, rejection, and independent rejection
review have SHA-256 values `51390650c9d3f7e80cc3810cc3be4b3eae23dc74358c611dca425fe98e31c7a3`,
`06bc319b12d763895d3d7c8038acb8c82b2ad965ef26d0c4cbcb05dd4a097136`, and
`6f83fe07fbb9b12dc7a75fbff2da2490300e0745e0c1fd15ad03b83fd8e5e347`. The review independently
rehashed all 139,663,075,787 training-root bytes with zero mismatch and confirmed that the v5
authority, acquisition entry/outcome, raw source, and private payload paths remained absent. V5 is
not retried. V6 changes the namespace, predecessor binding, and this ordering defect only: both
baseline production, builder authority reconstruction, and acquisition-runner terminal
reconstruction globally sort the complete training-root record list by path before equality
comparison, with source-free regression fixtures that make depth-first and lexical order differ.

## Frozen source and pre-acquisition evidence

The sole v6 candidate is the official Universal Dependencies repository
`https://github.com/UniversalDependencies/UD_English-ParTUT.git` at commit
`5552572ac2c5aac1538e43edb7f7a8d2224f12de`. Before source acquisition, a
case-insensitive scan of all 16,056 safely readable text files in the frozen v4 pre-source
inventory used bare `partut`, the full URL, repository variants, `en_partut`, and the commit. It
found exactly five planning-only mentions: `PLAN_ATTEMPT13.md:280`,
`PLAN_RELATIONAL_EDGE_V1.md:221,412`, and
`reports/provenance/relational_attention_edges_v1_discovery1_plan_snapshot.md:132,316`, whose file
SHA-256 values are respectively `194294213047f528fddcc0374e4a1d4d5a185ce01f5d07eb13bce688f9820db8`,
`8d1d6c172da0d8302410659c8cfff948c59e1df0fbbe03d972adb5c148c49bcd`, and
`5a5e8fb6d1396632c700fa51386711d022a6107bb02572fa7d7c94790bdb0c51`. Those notes considered
ParTUT but rejected it for document-group inference; they contain no evidence of acquisition or
model use. The corrected screen is copied byte-for-byte from the never-entered v5 protocol and bound at
`reports/provenance/msae_independent_source_v6/preacquisition_alias_screen.json`, SHA-256
`c0c17ed89e19b3af611bae43e73095ca4acb4d0a61a01f7c3ef8979cbe2fbd7d`, with zero unexpected
paths, quarantine reads, model operations, and training runs. It supports only
`previously_considered_but_project_source_use_unseen` if the later digest, pedigree, and content
gates pass—not name novelty, document independence, or content separation by itself.

The only post-screen files containing a candidate alias are the exact never-entered v5 authority
artifacts `docs/plan-msae-independent-source-v5.md`, the v5 alias screen and pedigree registry,
the v5 builder, acquisition runner, tests, and acquisition config. Their SHA-256 values are,
respectively, `1c450895bf836b142bc46dced85afd4f109edd68a96f6e4e91dc5719f0b3fc6b`,
`c0c17ed89e19b3af611bae43e73095ca4acb4d0a61a01f7c3ef8979cbe2fbd7d`,
`484a2b8c13798924c159d0e1bf7fbc90d19010111f89b08e7ddb7ceb6780b83f`,
`f78aba1add310c6a76a05cac4ccc159b9c6aa924e888664d3a54f372e0ebb1e8`,
`6b5c78543c9530c98c24ce99f90ac1caff6ca496d111d8b25889ec448402d11f`,
`f2cf4d0b58554d688fb4b601bcc739dc6749833d393b49e275178eedccdcac76`, and
`6b53511b6d0976ada49a7f090b884d7faeb7db3afb55da9a2f593c369af3e66d`.
V6 enumerates those seven frozen files as predecessor authority rather than history because the
reviewed v5 rejection proves zero source acquisition/use; every other post-v4 file remains history.

After this plan and its independent SHIP review, but still before source acquisition, the v6
builder creates a new full current-worktree inventory. It includes all prior ATIS raw files and all
post-v4 work as history. The exhaustive non-history authority set is exactly:
`docs/plan-msae-independent-source-v6.md`;
`reports/adversarial/msae_independent_source_v6_plan_review.md`;
`reports/provenance/msae_independent_source_v6/{preacquisition_alias_screen,historical_source_registry,preacquisition_authority_manifest,baseline_inventory}.json`;
`scripts/prepare_msae_independent_source_v6.py`;
`scripts/acquire_msae_independent_source_v6.py`;
`tests/test_prepare_msae_independent_source_v6.py`;
`configs/msae_independent_source_v6/acquisition.json`;
`reports/verification/msae_independent_source_v6_source_free_checks.log`; and
`reports/adversarial/msae_independent_source_v6_preacquisition_implementation_review.md`; and
`reports/adversarial/msae_independent_source_v6_preacquisition_authority_review.md`.
The seven exact candidate-bearing v5 predecessor files listed above also receive exactly
`v6_authority`. Each listed path receives exactly `v6_authority`, while only the unpopulated
`data/msae_independent_source_v6/` namespace receives `v6_excluded`; no prefix-based exclusion of
other v6-named paths is allowed. The baseline inventory output path is absent during its own walk and
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
prepare entry the structural recensus has no prefix exception: it permits as content-bearing
additions only the exact five acquired raw file paths and these exact post-baseline public-chain
files: `baseline_inventory.json`, `preacquisition_authority_manifest.json`, the authority-review
Markdown, `source_acquisition_entry.json`, and exactly one valid `source_acquisition.json` outcome.
The v6 namespace itself must contain exactly a non-symlink `0700` namespace, non-symlink `0700`
`raw/` parent, non-symlink `0555` commit directory, and five `0444` one-link regular files, with no
`private/`, extra file, symlink, hard-link alias, or other subtree before payload publication.

Acquisition uses a detached blob-filtered clone, verifies the exact commit/tree, then installs only
`en_partut-ud-train.conllu`, `en_partut-ud-dev.conllu`, `en_partut-ud-test.conllu`, `README.md`,
and `LICENSE.txt` beneath ignored
`data/msae_independent_source_v6/raw/<commit>/`, with files `0444` and the directory `0555`.
Command stdout/stderr are hashed and must contain no source content. Missing paths, revision drift,
malformed UTF-8/CoNLL-U, or license failure are terminal. No fallback source is permitted after
content acquisition.

The only network/process-capable artifact is `scripts/acquire_msae_independent_source_v6.py`; its
SHA-256 is bound directly by the implementation review, authority manifest, acquisition record,
and terminal seal. It requires `--authority-review-sha256` equal to the actual downstream SHIP
review file hash and reconstructs that review's authority-manifest and baseline hashes before any
subprocess. Its subprocess allowlist is exactly the config's `git check-ignore`, clone, checkout,
`rev-parse HEAD`, `rev-parse <commit>^{tree}`, `ls-tree -z`, and per-file `hash-object --no-filters`
argv; no shell, arbitrary command, model, GPU, tokenizer, or trainer executable is permitted.
`reports/provenance/msae_independent_source_v6/source_acquisition.json` is canonical create-once
JSON with schema `msae_independent_source_v6_source_acquisition_v1`. It records authority manifest,
authority review, durable entry marker, config, and runner hashes; the supplied review-hash argument; exact expanded argv
and minimal environment; every exit status; stdout/stderr byte count and SHA-256 for each command;
resolved commit and tree SHA-1; exact five path/blob SHA-1 pairs from `ls-tree`; each installed file's
SHA-256, Git-blob SHA-1, size, mode, and link count; raw-directory device/inode/mode; the two bound
`git check-ignore` results; and `source_content_printed=false`. The builder recomputes local Git-blob
and SHA-256 identities and rejects Boolean-only tree evidence.

The ignored v6 namespace, raw parents, commit directory, files, acquisition entry marker,
acquisition report, acquisition rejection, and all three named temporaries must be absent at the
clean-state entry gate and are
lstat/no-follow checked. The acquisition cardinality table is: (a) the all-absent state enters the
one-shot protocol; (b) exactly one already-valid canonical success or rejection final plus its
valid bound entry marker, with no
conflicting final/temporary and with all of its schema/mode/link/raw bindings reconstructing,
returns that terminal idempotently with zero subprocesses; (c) every other preexisting final,
temporary, or namespace combination is `invalid_preacquisition_state`, runs zero subprocesses,
does not enter or resume a v6 acquisition attempt and requires a new reviewed protocol without
cleanup or mutation under v6. Every named temporary, whether apparently complete, partial, or
malformed, is case (c) and is never finished, removed, or promoted by this runner. This explicit
non-entry state is not claimed as a retained v6 outcome because no
filesystem protocol can publish into an already-obstructed evidence namespace safely. Immediately
after the clean gate and before the first `git check-ignore` or other subprocess, the runner
atomically publishes and parent-fsyncs create-once
`reports/provenance/msae_independent_source_v6/source_acquisition_entry.json` (schema
`msae_independent_source_v6_source_acquisition_entry_v1`) binding the authority manifest/review,
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
terminal. A synchronous failure of success/rejection create, write, fsync, link, unlink, final check,
or parent fsync, or failure of identity-checked cleanup of the current invocation's temporary, may
instead leave case (c), exactly like asynchronous power loss or termination outside the handled
exception boundary. The protocol reports that state as unresolved/blocked and does not overstate it
as either a new attempt or a completed retained outcome. It never cleans up an object observed at
entry; on a current-invocation error it may unlink only the exact temporary it exclusively created,
and cleanup failure is case (c).

## Source-family, license, and parser gates

After acquisition, every raw-file SHA-256 is compared with the pre-acquisition inventory. Every
pre-acquisition text file is scanned again for the frozen aliases; only the five bound planning hits
may match. The exact enumerated `v6_authority` paths are non-history and audited separately. Any unexpected alias, pathname, or whole-file digest match
is terminal. The source-free historical pedigree registry is copied byte-for-byte from the
unentered v5 protocol and frozen at
`reports/provenance/msae_independent_source_v6/historical_source_registry.json`, SHA-256
`484a2b8c13798924c159d0e1bf7fbc90d19010111f89b08e7ddb7ceb6780b83f`. Its exhaustive input rule is
every `text_scanned` v4-baseline file plus the exact v4 ATIS acquisition JSON (16,057 files total).
It extracts (a) bounded HTTP(S) URL tokens, (b) bounded `UD_*` tokens, and (c) unescaped JSON string
values under the exact case-insensitive keys `source_repo,source_url,repo_url,repository,url,
source_revision,source_commit,commit,revision,dataset,dataset_id,dataset_name,source_name,source_id,
corpus,treebank`. The registry freezes CPython 3.12.3/Unicode 15.0.0, Python bytes-regex
`IGNORECASE`, 1,048,576-byte chunks with a 2,048-byte overlap (overlap occurrences are counted),
and the exact pattern bytes. A captured byte string is strict-UTF-8 decoded; NFKC normalized;
casefolded; collapsed by `" ".join(value.split())` with `sep=None`; stripped at both boundaries by
the exact codepoint sequence stored in `boundary_strip_codepoints`; then, in order, an initial
`http://` is replaced by `https://`, one terminal slash is removed, a terminal `.git` is removed,
and one remaining terminal slash is removed. Empty/invalid history captures are omitted; the same on candidate metadata is terminal.
Public entries store only `SHA256(domain_utf8 || byte(0x00) || UTF8(normalized_identifier))`, kinds,
counts, and a digest of sorted occurrence paths. The registry records `domain_utf8`,
`separator_hex="00"`, ordered steps, strip codepoints, regex flags/runtime/chunking, and five
input/output/hash goldens, including `.git` and `.git/` spellings required to yield the same
normalized identifier and hash. For every entry, occurrence paths are exact-string deduplicated,
Python-Unicode-codepoint sorted, serialized as a JSON array with `sort_keys=true`,
`ensure_ascii=true`, compact separators, `allow_nan=false`, UTF-8, no final LF and no domain, then
SHA-256 hashed. The registry freezes a duplicate/multi-path golden with SHA-256
`ee69f1b7839d9eaba43b743baa065b321c154e13577dc6dd2a21816b9b2aea65`. It contains 4,029 identifiers and binds its regex bytes, normalization,
baseline, and added-input hash, covering all prior sources matched by this deterministic grammar
rather than a hand-maintained shortlist.

Candidate pedigree extraction applies exactly that same grammar to README/LICENSE and also injects
the normalized frozen repo URL, commit, repo name, `en_partut`, and source filenames. Exact candidate
repo, commit, dataset identifier, raw digest, or extracted declared-upstream identifier match is
terminal; the three literal normalized values `https://universaldependencies.org`,
`https://creativecommons.org/licenses/by-sa/4.0`, and `cc-by-sa-4.0` are the only allowed shared
non-source exceptions; their NUL-domain hashes and literals are frozen in the registry. Invalid UTF-8, overlength/unescaped candidate identifier syntax, or ambiguous source-line
syntax is terminal rather than ignored. The candidate report records hashes/counts, not source prose.
A pass supports only `previously_considered_but_project_source_use_unseen` plus later audited
utterance separation, not researcher-unawareness or pretraining independence.

The required upstream license artifact identifier is exactly `CC-BY-SA-4.0` and canonical URL is
exactly `https://creativecommons.org/licenses/by-sa/4.0/`. `LICENSE.txt` must identify those terms
and README must agree. Public provenance records hashes, license identity/URL, attribution/share-alike
obligations, and that raw/payload text remains ignored. Contradictory or missing terms stop before
payload creation.

The parser and label functions are byte-for-byte inherited from the frozen v4.2 builder except for
v6 namespaces, candidate paths, predecessor bindings, generated-directory exclusion, the explicit
terminal `newdoc id` marker check, and the deduplication rule below. It pins CPython 3.12.3 and Unicode 15.0.0; validates CoNLL-U IDs, roots,
heads, acyclicity, UPOS, DEPREL, and UD FEATS; permits canonical sorted comma multi-values only for
non-`Number` features; and requires `Number` to have at most one recognized value. The task set,
label transformations, missing-label behavior, public lexical-label hashing, and support floor are
unchanged from v4.2, with lexical domains changed exactly to `msae-v6/token\0` and
`msae-v6/lemma\0`. `neutral_prefix_offset`, `entity_binary`, `entity_type`, and `source_genre` are
explicitly unsupported in support, seal, and readiness artifacts. No source values are printed.

## Prospective duplicate and role policy

The natural unit is one CoNLL-U sentence. Before role construction the builder publishes a
`newdoc id`/document-group census. Any `newdoc id` marker is terminal as unsupported; therefore the
only permitted branch is the exact sentence-only split. A zero-marker census is required and all
document-, speaker-, or cluster-level inference is forbidden. Normalize by NFKC+casefold of each
integer-token FORM and join with one ASCII space. Before any support calculation or split:

1. within each official partition, group by exact normalized utterance and keep only the sentence
   with lexicographically smallest `(UTF-8 sent_id, source index)`;
2. if a normalized utterance occurs in more than one official partition, exclude every member of
   that group from every role;
3. publish only per-partition input/retained/within-dropped/cross-partition-dropped counts and a
   SHA-256 of the sorted excluded `sent_id` list, never normalized text or token content.

This rule is frozen before ParTUT content acquisition. It is a leakage-control transform, not a
claim that duplicates did not exist. Official train maps to discovery, dev to calibration, and the
filtered official test set is split into C1/C2. Remaining cross-role pairs are checked in both
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

V6 inherits the v4.2 split, manifest, payload, and custody byte contract with only these enumerated
changes: domain `msae-independent-source-v6/C1C2`; schema literals
`msae_independent_source_v6_{split_manifest,role_manifest,payload}_v1`; ParTUT repo/commit,
`upstream_partition="test"`, and filtered/deduplicated sentence records. Any group marker has already
terminated, so no conditional group split exists. Canonical JSON is `sort_keys=true`, `ensure_ascii=false`, compact
separators `(',', ':')`, `allow_nan=false`, UTF-8, and final LF for every file/record. Split keys hash
the no-LF canonical array `[domain,sent_id,normalized_utterance]`; rows sort by lowercase hash then
UTF-8 sent_id and even/odd ranks map C1/C2. The two-entry manifest golden using commit forty zeroes,
`é`/C1/rank0/zero-key and `x!`/C2/rank1/f-key has v6 SHA-256
`3113f18eec64ba9aa0f8a47bd8d2cb8d55229f531d59d8b2a30053546427a1eb`. The public split and role
manifests expose IDs, ranks, panels, counts, hashes, upstream partitions, source-record hashes only, never forms/lemmas/normalized text.

The private payload path is
`data/msae_independent_source_v6/private/blind_payload.jsonl`. Each row has exactly
`schema_version`, `source_repo`, `source_commit`, `upstream_partition`, `panel`,
`split_key_sha256`, `sent_id`, and `tokens`; `tokens` is the ordered array of exactly integer `id`,
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
`msae_independent_source_v6_scientific_artifact_inventory_v1`. Its ordered universe is every final
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
`no_training_gate.json`, is bound; failure of the rejection publisher itself is unresolved case (c); and
therefore an abandoned payload temporary or invalid/symlink target is a reconstructable retained
failure rather than an unverifiable state.

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

### V6-M1 — prospective plan and source-free implementation

- [ ] Independent plan review returns SHIP while all v6 source/payload paths remain absent.
- [ ] Implement and test every source-free parser, adapter, archive, dedup, split, custody, pedigree,
      capability, inventory, and separately reviewed acquisition-runner/validation path; bind the exact v5
      plan/builder/runner/test/config/baseline/rejection/rejection-review predecessor chain and the
      v4/v4.1/v4.2 rejections. Regression-test both builder and runner global training-root
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

### V6-M2 — source and scientific gates

- [ ] Exact commit/tree/files/license are acquired without content output.
- [ ] Parser, source-family, prospective dedup, four-role separation, full-history overlap, and
      support gates pass in order, or the first failure is retained and ends v6.

### V6-M3 — payload, review, and stop

- [ ] On success only, public manifests reconstruct, private payload is create-once `0600`, and all
      hashes/counts agree.
- [ ] An independent provenance-only source-readiness review returns SHIP.
- [ ] The reviewed v6 builder/runner initiated no model, tokenizer, GPU, scoring, K2/branch training,
      or Stage C operation; both point snapshots contain zero forbidden identities and bound project
      training roots have zero delta.

## Verification plan

- [ ] Before acquisition, test-first fixtures cover parser/FEATS, exact labels, dedup precedence/
      exclusion, zero-group-only behavior, overlap directions/boundaries, isolated structured fields,
      safe and nested archive policy, split golden, inventory/quarantine/generated-cache handling,
      create-once/abandoned-temp custody, output canaries, and static no-neural imports.
- [ ] Before acquisition, negative capability fixtures reject indirect process/network/dynamic-load/
      `ctypes` paths; exact acquisition argv/environment validates; `/proc` has zero forbidden
      identities; GPU APIs are not queried; and results/checkpoint/training-root baseline is bound.
- [ ] Source-free fault injection covers create/write/fsync/link/unlink/final-check/parent-fsync for
      acquisition success, acquisition rejection, scientific artifacts, and scientific rejection;
      preflight→entry-marker→first-subprocess tests prove the marker is durable before any `git`, and
      tests distinguish a successfully retained terminal from unresolved case (c) without retry.
- [ ] All v4/v4.1/v4.2/v6 tests pass with plugin autoload disabled; `py_compile` and AST closure pass.
- [ ] Strict-parse every public JSON; recompute bindings and payload lstat/opaque hash only.
- [ ] Run claim review, reproducibility checks, secret scan, forbidden-claim scan, and
      `git diff --check` before commit.

## Definition of done

- [ ] After the all-absent acquisition entry gate, a successfully published outcome is either a
      reviewed retained failure at its first frozen gate or a reviewed
      `independent_source_ready_for_future_prescore_protocol` seal with a replacement payload.
      Outcome-publisher I/O/cleanup failure or asynchronous interruption may instead leave the
      explicitly blocked case-(c) state and is never reported as a completed outcome or silently retried.
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
