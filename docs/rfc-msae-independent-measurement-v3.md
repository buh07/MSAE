# PLAN — MSAE exposed-source measurement remediation v3

> Prospective successor protocol, 2026-08-20. V1 and v2 remain immutable and failed.
> This v3 may use the same already-exposed AMALGUM partition only as an
> **exposed-source technical/measurement replication**, never as a pristine
> independent-source confirmation.

## Goal

Preserve the failed v1 and v2 records; replace their short-boilerplate-sensitive overlap
criterion with a validated substantive-reuse gate; finish the strict four-role
label/map, provenance, authorization, numerical-QA, and failure-path contracts;
obtain independent prescore `/adversarial` SHIP; build a new Stage A; and launch
only the calibration replay in tmux on a verified free GPU. Return immediately
after a verified live handoff. Confirmation scoring and Stage C remain not-run.

## Non-goals

- Never mutate or reinterpret any v1 config, Stage A, overlap result, review, or
  status. V1 remains exactly `status=stopped_prescore`, 206 collisions,
  `stage_ready=false`, and Stage B/C `not_run`. Before v3 implementation, freeze
  path/type/mode/size/SHA-256 for every file under the v1 config, data, and
  provenance roots plus its RFC, adversarial review, scripts, and tests. Every
  v3 build and launch rehashes that exhaustive protected manifest.
- Never mutate or reinterpret the v2 overlap attempt. It remains exactly
  `status=stopped_prescore_overlap_ineligible`, four cumulative-short-sentence
  collisions, `stage_a_ready=false`, Stage A `not_built`, and Stage B/C
  `not_run`. `protected_v2_manifest.json` freezes every v2 RFC, code, test,
  data, and provenance byte at this terminal boundary. V3 is additive in wholly
  new protocol/schema/config/code/test/data/provenance/review/run namespaces.
- “V1 byte-for-byte preserved” refers to those v1-owned protected roots/files.
  The three external Atlas final payloads are not v1-owned bytes and, after the
  exposure incident, v3 deliberately makes no unverifiable current-content
  claim about them; it preserves their frozen v1 hashes as historical evidence
  and quarantines their identities under metadata checks only.
- Do not call v3 pristine independent evidence, training-data novelty, or a
  paper-result source. Do not select replacement AMALGUM documents after seeing
  v1 collisions.
- Do not open the blind final partition, run C1/C2 neural scoring, build Stage C,
  train a model, choose a paper branch, or wait for calibration results.
- Planning/review commands on 2026-08-20 recursively searched `data/` and therefore
  process-read the three `data/atlas_v1/private/final*` payloads even though no
  payload text was returned to the coordinator. Record this as an exposure
  incident: they can no longer support a pristine/blind confirmation claim and
  must be replaced before any future Stage C. This v3 calibration protocol never
  opens them again and relies only on the pre-incident v1 exclusion evidence.
- A calibration no-ladder-pass is scientific `ineligible`; timeout, OOM,
  authorization/lineage/lease failure is `technical_failure/not_run` and cannot
  build Stage B.

## Design-bank/query clarification

The deterministic query backend rejected this nested repository as an
undeclared boundary, so no backend structural claim is assumed. Directly
reviewed interfaces are `build_stage_a`, `build_stage_b`,
`select_replay_tolerance`, and `payload_sha256` in
`scripts/msae_measurement_remediation_v1.py`. V3 is additive and wraps those
reviewed interfaces; it does not weaken their schema. The exact failed command,
run from `/jumbo/lisp/f004ndc`, was
`/jumbo/lisp/f004ndc/.agent-workspace/bin/query def build_stage_a --lang python --path experiments/wip/MSAE/scripts`;
it reported that `experiments/wip/MSAE` is an undeclared nested repository and
did not return a definition.

## Frozen source decision

Retain the exact 350-document v1 AMALGUM selection, roles, paths, and file hashes.
This is weaker than a genuinely new corpus, but it avoids post-exposure document
substitution and no neural outcomes were observed. The claim is narrowed to
substantive document independence from accessible Atlas text under the v3 gate,
conditional on shared web genres and an AMALGUM/GUM-like annotation pipeline.
A genuinely new corpus remains required before a pristine independent-source
paper claim.

The v2 gate was prospectively applied before v3 and correctly stopped with four
phrasebook-versus-ESL/CHILDES matches. V3 does not relabel v2. An append-only
post-hoc analysis binds v2's digest and the exact shared tuples/ratios; those
four observed rows motivate regression fixtures but are not independent
validation of v3. The independent planted positives/negatives remain the
prospective rule validation.

Alternative rejected: choose later AMALGUM ranks. It would use exposed collision
information to repair source selection. Alternative deferred: select a new
corpus now. No reviewed candidate has yet demonstrated document grouping,
dependency/entity support, licensing, and non-overlap; choosing one merely to
launch would weaken provenance.

## V3 substantive-overlap gate

Canonical lexical tokens are maximal Unicode letter/number sequences after NFC
and lowercase. Five-grams use set semantics. Audit every accessible historical
text record under baseline `data/`, excluding only the exact v3 self-output root,
the exact selected-source aliases below, and the exact frozen sealed entries
below without opening them.
Bind every path, SHA-256, parse outcome, canonical document/source ID, record and
sentence index, and exclusion reason.

The sole self-output exclusion is
`data/msae_independent_measurement_v3/`; no other path containing `v3`, including
every `data/atlas_measurement_v3*` root, is excluded. That root must be absent at
the baseline snapshot and may thereafter contain only the fixed M0--M4 artifact
names in the write allowlist below; lookalike paths, undeclared files, prefix
matches, and symlink escapes block. The sole sealed registry is
`data/atlas_v1/private/final_manifest.json`, SHA-256
`d88fa8b0159b6024a539cd05103cce2466c2f803328542e93d37ac971de16104`, schema
`atlas_v1_private_final`. Its only payload entries are
`final.jsonl=684d48c6fd5fd6a1faec5ca5785eb9a054fc94a603422088c5e9eb6a485c8eee`,
`final.records.jsonl=5d397a7695bb46d1e0700af9af084272fa627ba815ada8b5197bac740510471e`,
and
`final.units.jsonl=3acb17e56fead3c1abc915978ff7733a4ccb0e0c3dcb787410deffbaffc79e23`;
v3 takes their
path/size/hash/status from the frozen v1 overlap rows and only `lstat`s paths,
never opens or rehashes them. No new sealed/private designation is accepted.

`source_exposure.json` has a typed incident schema and is Stage-A-bound. It lists
the three identities above with sizes `49550`, `10172061`, and `29193353`; the
fresh-context review command
`grep -R -l --include='*.json' --include='*.jsonl' '"source_words"\|"target_words"' experiments/wip/MSAE/data`;
`session_date_utc=2026-08-20`; `wall_clock_time_unavailable=true`;
`content_returned_to_coordinator=false`; `blindness_destroyed=true`;
`replacement_required_before_confirmation=true`; and disposition
`exposed_quarantined_not_scanned_by_v3`. Each file has distinct fields
`v1_status_at_v1_audit=excluded_sealed_unopened` and
`v3_current_status=exposed_quarantined_not_scanned`; v3 never copies the former
as a current status. Every Stage-C/confirmation validator rejects these three
identities regardless of signature until a separately reviewed replacement
partition exists.

The repository write allowlist is also prospective and exact. It contains this
RFC and `TODO.md`; the three v3 entry points
`scripts/msae_independent_measurement_v3.py`,
`scripts/run_msae_independent_calibration_v3.py`, and
`scripts/launch_msae_independent_calibration_v3.sh`; one test
`tests/test_msae_independent_measurement_v3.py`; config files
`configs/msae_independent_measurement_v3/{protocol.json,authorization_commitment.json,ed25519_public.pem}`;
and data files under the sole self-output root named
`{data_baseline_manifest,protected_v1_manifest,protected_v2_manifest,source_exposure,v2_posthoc_boilerplate_analysis,source_alias_manifest,overlap_fixtures,history_census,history_overlap,v1_row_crosswalk,label_rows,task_manifest,support,prefix_templates,maps,finite_pass_matrix,protocol_imports,dependency_closure,endpoint_registry,environment_allowlist}.json`
(each expands to `.json` except that `label_rows` expands only to `.jsonl`). Prescore provenance is exactly
`reports/provenance/msae_independent_measurement_v3/{stage_a,status,prescore_candidate_manifest}.json`
and the external review transcript is exactly
`reports/adversarial/msae_independent_measurement_v3_prescore.md`.

The only live run root is
`pilot_runs/20260820_msae_independent_measurement_v3_calibration/`. Its cache is
the Cartesian expansion
`cache/{main_short,main_long,pair_context,pair_entity}/forward_{0,1,2,3}.npy`;
its logs are `logs/{broker,worker}.log`; and its provenance files are
`{authorization,nonce_consumed,lock_acquired,handoff,observed_environment,status,technical_failure,stage_b,cached_noop_hash_replay,canonical_pooling_qa,counterfactual_cache_alignment_qa,tolerance_selection}.json`.
Exactly one nonce filename is derived as lowercase hex SHA-256 of the signed
canonical envelope. Temporary builds use exactly the initially absent mode-0700
directories `/tmp/msae_independent_measurement_v3_build_primary` and
`/tmp/msae_independent_measurement_v3_build_rebuild`, created with exclusive
`mkdir`, fully removed before M4 installation, and never audit exclusions. Before each phase,
enumerate repository status and reject every new/modified/output path outside
this allowlist; planted `v3` lookalikes, undeclared output, symlink, and sealed-
designation escape attempts must fail.
The external-state write allowlist contains the private key
`/jumbo/lisp/f004ndc/.msae_keys/independent_measurement_v3_ed25519_private.pem`
inside a current-UID-owned mode-`0700` non-symlink directory; create it once at
mode `0600`, never copy its bytes into the candidate/report/log, and bind only
its public-key match, canonical path, device/inode, owner, and mode. It also
contains the nonce/GPU-lock namespaces frozen below. The remaining phase-scoped
external writes are only those two build directories; the two review files
`/tmp/msae_v3_prescore_trace_${M}.log` and
`/tmp/msae_v3_prescore_check_${M}.json`, where `M` is the validated
candidate-manifest digest; the initially absent mode-0700 CPU-test root
`/tmp/msae_independent_measurement_v3_verify`; and the tmux socket
`/tmp/msae_independent_measurement_v3_${A}.sock` where `A` is the validated
v3-Stage-A digest. Build/review/verification paths must be absent before
exclusive creation and are removed after their phase; the tmux socket persists only while the
fixed session `msae-independent-v3-calibration` lives. All Python commands use
interpreter flag `-B` (including under `-I`); runtime commands also set
`CUDA_CACHE_DISABLE=1`,
`TRANSFORMERS_OFFLINE=1`, `HF_HUB_OFFLINE=1`, and reject Python/HF/CUDA cache or
extension-compilation writes. No other non-repository write is allowed.

M0 also installs `data_baseline_manifest.json` before any v3 data output. It
enumerates every then-existing entry under `data/` with canonical path,
type/mode/size and SHA-256 under `content_rehash`, uses only the frozen-v1
metadata plus fresh `lstat` for the three quarantined payloads, and proves the
v3 self-output root absent. M1/M4/reviewer/signer/launcher revalidate it with a
closed projection that permits only the exact declared v3-root files created by
completed milestones; every pre-existing entry must remain byte-identical and
every undeclared addition/removal/replacement blocks.

After the five M0 inputs and final M1 code/RFC/tests exist, M0 creates
`m0_completion_manifest.json`. It binds the exact five M0 artifacts plus the
M1 builder, RFC, and tests. An independent reviewer reports the manifest's
SHA-256, and `audit-overlap` requires that external lowercase digest through
`--reviewed-m0-sha256`; M1 recomputes the complete manifest before and after
installation. Thus the mutable M0 manifests are not self-authenticating trust
roots.

The v1 selected-file manifest is a frozen alias ledger whose domain is exactly
the 350 `.conllu` paths under
`data/msae_independent_measurement_v1/selected_raw/`. Those paths are excluded
only when their bytes equal the corresponding selected-source SHA-256; a
missing, extra, or mismatched `.conllu` ledger entry blocks. The root must have
exactly 352 regular files: those 350 aliases plus `README.md` and
`DEVELOPMENT.md`; the latter two are non-alias historical inputs processed by
the Markdown adapter and counted in its census. Any other entry blocks. Emit
`same_frozen_source_copy` for every exclusion. V3
paths are self-output exclusions. Identical historical files are parsed once at
the lexicographically first path and later paths are aliases. Canonical source
documents deduplicate first by `(source_revision, document_group)` when both are
present, otherwise by `(file_sha256, zero_based_record_index)`. Conflicting bytes
under one identity block. Each canonical source document counts once in `N` and
`df`.

Canonical sentence-aware serialization is binary and length-prefixed:
`u64be(sentence_count)`, then for each sentence `u64be(token_count)`, then for
each token `u64be(UTF8_byte_count)||UTF8`. A second boundary-insensitive
serialization is `u64be(total_token_count)` followed by the same framed tokens
in document order with sentence boundaries removed. Full-document SHA-256 binds
both hashes. Sentence hashes use the sentence-aware framing with sentence count
one. Document five-grams and document-level coverage use the flattened stream
and may cross original sentence/line boundaries; sentence five-grams remain
sentence-local diagnostics. Weighted Jaccard is
exactly `sum(weight[g] for g in intersection) / sum(weight[g] for g in union)`;
an empty union is incomparable. Coverage is the union of selected
document-global token indices touched by shared flattened five-grams.

Every gram is encoded as the typed five-string tuple codec defined below and
iterated in encoded-byte ascending order. All IDF/Jaccard arithmetic uses
`decimal.Decimal` under a local context `prec=50`, `ROUND_HALF_EVEN`, with no
binary-float conversion: weight is
`Decimal(N+1).ln()-Decimal(df+1).ln()+Decimal(1)`, each sorted sum uses that
context, division uses that context, serialization is `format(value,'f')`, and
comparison is directly against `Decimal('0.75')`/`Decimal('0.80')`. Golden
`N=3`, intersection `df=1`, and two union-only grams each `df=2` produce weights
`1.6931471805599453094172321214581765680755001343602` and
`1.2876820724517809274392190059938274315035097108978`, and Jaccard
`0.39665987775634884002293696822641755903154537267338`. Separate-process
fixtures under multiple `PYTHONHASHSEED` values must emit identical bytes and
inclusive boundary decisions.

Historical adapters are exact. `.conllu` uses `newdoc id` as document identity
(whole file only if no marker), `sent_id` as sentence identity, and checks
`# text` against FORM reconstruction with CoNLL-U `SpaceAfter=No` and the
standard escaped `SpacesAfter` value (`\\s,\\n,\\t,\\r,\\p,\\\\,\\uXXXX`);
simultaneous `SpaceAfter` and `SpacesAfter` blocks. For strict selected-source
label parsing a mismatch blocks. For heterogeneous historical treebanks the
integer-token FORM stream remains normative and a mismatch is a bound
`historical_text_comment_mismatch` diagnostic rather than discarded text.
`.jsonl` parses each
line as one object at zero-based line index. Rows containing either
`source_words` or `target_words` must contain both as token arrays, contain none
of `words/tokens/text/sentence`, and yield two independently indexed subrecords
whose identity appends literal side `source` or `target`; the two sides are
expected to differ and are never equality-checked against one another. Other
text rows take sentence tokens in priority order `words`, `tokens`, `text`,
`sentence`, with multiple present base fields required to normalize identically,
   and group in encounter order by `(source_revision,document_group)` or fall back
   to `(file_sha256,zero_based_record_index,side)`. Both forms are encoded with
   the typed tuple codec and exposed as a domain-separated SHA-256 identity,
   never delimiter-concatenated text. The canonical document keeps
   the exact ordered source-record-index list; a grouped-document ordinal is
   never reported as a source record index. `.json`
accepts only a top-level list or a top-level `records`, `rows`, or `data` list and
uses the same object adapter and zero-based list index; other JSON is recorded
`non_text_metadata`. Multiple candidate text fields must normalize identically
or block. Invalid UTF-8/JSON/CoNLL-U or a candidate text record without stable
identity blocks. JSON constants `NaN`, `Infinity`, and `-Infinity` are invalid
and block rather than entering the non-text path. Duplicate JSON member names
at any nesting depth also block before field census, including candidate,
identity, and top-level container members. `.md` and `.diff` are each one document whose sentences are its
nonempty physical UTF-8 lines in encounter order after `\r\n`/`\n` terminators
are removed; Unicode line-separator characters are content, not boundaries.
The census binds every physical-line index, normalized sentence hash, and
included/non-text outcome (markup/prefix characters are
left in the line and therefore discarded only if the lexical tokenizer discards
    them). `.npy` and `.npz` are fixed-hash `binary_array_non_text` files: verify
their magic/container structure without loading arrays or treating embedded
strings as corpus text. Before evaluation, inventory every baseline suffix,
file type, and magic value and require it to be one of those seven adapters;
unknown, extensionless, device, socket, FIFO, or future file types block. Bind
every non-text classification rather than silently dropping it. Fixtures cover
Markdown, unified diff, NPY, NPZ, and the selected-root `README.md` and
`DEVELOPMENT.md`. Sealed/private paths come only from the exact registry/hash/
entry set frozen above and are `lstat`-identified against the v1 evidence
without payload content reads. Emit a
schema census for every JSON/JSONL row and every predecessor-recognized text
field (`source_words`, `target_words`, `words`, `tokens`, `text`, `sentence`),
proving each occurrence became a uniquely identified included subrecord or was
named by the pre-existing sealed-final exclusion; all other rows receive a
bound non-text reason. Census arithmetic mismatch blocks.

The JSON text-field grammar is closed. `source_words`, `target_words`, `words`,
and `tokens` are nonempty JSON arrays of nonempty JSON strings; `text` and
`sentence` are JSON strings. Null, bool, number, object, nested array, empty
array, empty token string, invalid surrogate, or any other value at a present
candidate field blocks. An array is one pretokenized sentence: apply the lexical
token regex separately to each element and concatenate results in element order.
A string is one sentence: apply the same regex to the entire string. A
syntactically valid nonempty field from which no lexical token results is bound
as `punctuation_or_redaction_only_non_text` and does not enter overlap
arithmetic; mixed candidate fields must still agree on that empty sequence.
“Normalize identically” means exact equality of those
ordered NFC-lowercase lexical-token lists, not raw strings or implicit
stringification. Fixtures require `words=["A","cat"]`, `tokens=["A cat"]`,
and `text="A cat"` to agree; empty/wrong-type values block, punctuation-only
values take the bound non-text path, and `words=["A","cat"]` versus
`text="A dog"` must block.

The complete prescore rule is:

1. Exact normalized full-document equality under either sentence-aware or
   flattened SHA-256 always blocks.
2. A document is comparable at >=50 lexical tokens and >=20 distinct five-grams.
   Plain Jaccard `>=0.80` or IDF-weighted Jaccard `>=0.75` blocks.
3. IDF is `ln(N+1)-ln(df+1)+1` under the frozen Decimal procedure over the canonical selected plus included
   historical document universe, counting each five-gram once/document. Bind the
   universe and exact weight payload.
4. Exact normalized sentence equality blocks whenever both sentences have >=10
   lexical tokens, independent of gram diversity. For non-exact sentences,
   plain five-gram Jaccard `>=0.80` blocks only when both have >=10 tokens and
   >=6 distinct five-grams.
5. “Short sentence” means <10 lexical tokens. For a document pair, form the set
   intersection of distinct nonempty normalized short-sentence token tuples;
   repeated occurrences do not increase membership or weight. Count each shared
   tuple once and sum its tuple length once in encoded-tuple byte order. Let
   `S` be that unique-tuple token sum and `T` the selected document's flattened
   lexical-token count. Block exactly when `members>=5 && S>=20 && 10*S>=T`.
   This integer inequality is inclusive, selected-oriented, occurrence-
   invariant, and uses no float. Empty/punctuation-only strings are ignored.
   Fixtures cover 4/5 members, 19/20 tokens, below/at 10%, repeat invariance,
   the four observed v2 negatives, and a separately planted substantive positive.
6. Shared-passage coverage blocks exactly when at least four distinct shared
   five-grams cover `C>=20` selected token positions and `10*C>=T`, where `T`
   is the selected document's flattened lexical-token count.
   This diversity floor prevents a single repeated boilerplate gram from
   manufacturing coverage; the planted repeated-heading fixture fixes it.
   Bind hashes of the sorted shared-gram set and sorted covered-position set;
   fixtures cover 3/4 grams, 19/20 positions, and below/at 10%.
7. Every threshold is inclusive. Fixtures cover 49/50 tokens, 19/20 document
   grams, 9/10 sentence tokens, 5/6 sentence grams, 19/20 positions, exact
   `20/201`/`20/200` selected coverage, and exact discrete below/at Jaccard
   values (`43/56`/`0.80` plain and `41/57`/`0.75` unit-weighted). Each
   fixture asserts both the recorded exact value and presence or absence of the
   individual reason under test, even if a different reason blocks the pair.
8. Any parse failure, identity conflict, nonfinite weight, incomplete manifest,
   or additional sealed-payload content access by the v3 builder/audit invalidates
   the audit; the recorded planning exposure is a confirmation-firewall failure,
   not silently rewritten as an overlap result. Nothing is dropped.

Before AMALGUM evaluation, frozen planted fixtures include exact document, 20%
edited document, copied 15-token sentence, fragmented 25-token copying,
Unicode/whitespace normalization, unrelated documents, repeated `Steps`, `Buy`,
`By car`, `Yes`, and punctuation-only headings. Positive segmentation fixtures
flatten an identical 100-token stream into 25 four-token sentences and alter
line/sentence boundaries without changing tokens; both must block by the
flattened hash/gram gate. A multi-sentence fixture lands exactly at 19/20
document-global covered positions. Exact 10-, 15-, and 19-token alternating-
token low-diversity sentences embedded in unrelated documents must block. All substantive positives block;
boilerplate/unrelated negatives pass.

M1 computes all five canonical output payloads before creating any destination.
It then uses a recoverable mode-0700 transaction under the v3 provenance root:
all staged payloads and their digest descriptor are fsynced before target
creation. A rerun recomputes all payloads and may only resume exact matching
staged/target bytes; missing staged bytes are reconstructed, while any mismatch
blocks. Only after every mode-0644 target is byte/digest verified are staging
entries removed and both directories fsynced. A complete exact target set is
idempotently accepted; an orphaned partial target set without the transaction
blocks.

The v3-only `v1_row_crosswalk.json` is a
`v3_visible_legacy_row_crosswalk_v1`, not a v1 replay or reclassification. The
frozen v1 rows do not contain record/sentence identities and the exhaustive v1
protected bytes contain no overlap-audit generator; inventing those identities
would be false provenance. The crosswalk therefore preserves every legacy row
and verdict verbatim in frozen order, binds the legacy artifact digest, hashes
each complete visible row, and assigns an occurrence ordinal and total
multiplicity within each identical visible-row signature. It states
`exact_v1_identity_replay_available=false` and binds the independently rebuilt
v3 result digest. Require the projected legacy fields and visible-signature
multiplicities to equal all 206 frozen rows. V3's full census and overlap audit,
not this diagnostic crosswalk, provide prospective evidence for the v3 gate.

## Strict four-role label and map freeze

- Strict CoNLL-U parsing requires exactly ten fields on integer rows, unique
  contiguous integer IDs per sentence, valid integer heads in `{0} union IDs`,
  nonempty FORM/LEMMA/UPOS/DEPREL, and well-formed MISC key/value fields.
  Multiword and empty nodes are retained in source provenance but excluded from
  probe rows. Any other malformed row blocks.
- `|` separates MISC attributes and never Entity events. An `Entity` value is
  consumed left-to-right by adjacent events matching typed/identity-bearing
  open `(TYPE-ID`, close `TYPE-ID)`, or singleton `(TYPE-ID)`, where `TYPE`
  matches `[A-Za-z][A-Za-z0-9_-]*` and `ID` is a positive decimal integer.
  Opens push a distinct mention instance `(document_token_index,event_ordinal)`
  onto a LIFO stack keyed by `(TYPE,ID)`; repeated active opens of the same key
  are valid. A close must match a nonempty same-key stack and pops its most
  recent instance, emitting that inclusive document-token span. This per-key
  LIFO rule coexists with arbitrary close order across keys and therefore
  supports nested/overlapping mentions. Singletons emit one-token spans without
  changing a stack. Stacks intentionally carry across sentence boundaries and
  must be empty only at `newdoc`/file-document end. Duplicate MISC keys,
  unmatched/type-mismatched closes, unconsumed bytes, or nonempty document-end
  stacks block; identical adjacent events are not duplicate keys and are parsed
  separately. Coreference IDs may be reused for later mentions after close.
  Fixtures include `(place-1)`, `(substance-14(place-1)`,
  `place-1)person-5)abstract-6)place-7)(place-9)`, the two same-key opens
  `Entity=(place-7(place-7` closed at tokens 44 and 47 of
  `AMALGUM_voyage_bahn-10`, and the cross-sentence `abstract-51` span from
  `AMALGUM_voyage_phrasebook-20` into `-21`; malformed close underflow and
  document-end leftovers block. `entity_binary` is the union of all covering
  spans. Diagnostic coarse type chooses covering spans by `(start ascending,
  end descending, TYPE UTF-8, ID ascending, event_ordinal ascending)` and records
  every overlap; it is not mislabeled as a unique outermost type.
- Discovery/calibration use the frozen Atlas-v1 record files and their separate
  UD/NER source strata. C1/C2 use the unchanged AMALGUM documents. The exact
  applicability matrix is: absolute bucket, relative quartile, prefix offset,
  token identity, lemma identity, capitalization, word length, punctuation, and
  boundary apply to every source; head distance, dependency depth, UPOS,
  dependency relation, and Number apply only to discovery/calibration UD and
  AMALGUM; entity binary/type apply only to discovery/calibration NER and
  AMALGUM; source/genre applies pooled by role. An applicable missing label
  blocks rather than becoming `__DROP__`.
- Model first-subtoken index `p` is zero-based in the realized unpadded
  length-<=128 input. `absolute_bucket` is `floor(p/16)` with the closed classes
  string `0..7`. Word index `j` is zero-based among integer-token rows and
  sentence length is `n`: relative quartile is
  `min(3,floor(4*j/n))`; head distance is `ROOT` for head 0, otherwise signed
  distance binned `L5p,L3_4,L1_2,R1_2,R3_4,R5p`; dependency depth is parent-edge
  count binned `0,1,2,3,4p`, with cycles invalid.
- All remaining label semantics are closed. FORM and LEMMA are NFC first;
  `token_identity` is `FORM.lower()` and `lemma_identity` is `LEMMA.lower()`
  (NER-without-lemma uses `FORM.lower()`). Only labels in the common frozen
  vocabulary are applicable rows; OOV is typed `not_applicable`, never a class.
  Vocabulary document frequency counts each physical `document_group` at most
  once per label. `capitalization` filters FORM to Unicode alphabetic code
  points then applies in order `nonalpha` if empty, `lower` if `.islower()`,
  `upper` if `.isupper()`, `title` if `.istitle()`, else `mixed`.
  `word_length` counts NFC Unicode code points into `1,2,3_4,5_7,8p`.
  `punctuation` is `PUNCT` iff FORM is nonempty and every code point's Unicode
  category begins `P`, else `NONPUNCT`. `sentence_boundary` is `single` for
  `n=1`, else `initial` at `j=0`, `final` at `j=n-1`, else `interior`.
- `upos_coarse` is the exact UPOS field and must be one of
  `ADJ,ADP,ADV,AUX,CCONJ,DET,INTJ,NOUN,NUM,PART,PRON,PROPN,PUNCT,SCONJ,SYM,VERB,X`.
  `deprel_coarse` is DEPREL before the first colon and must be one of
  `acl,advcl,advmod,amod,appos,aux,case,cc,ccomp,clf,compound,conj,cop,csubj,dep,det,discourse,dislocated,expl,fixed,flat,goeswith,iobj,list,mark,nmod,nsubj,nummod,obj,obl,orphan,parataxis,punct,reparandum,root,vocative,xcomp`.
  `number` reads exactly one `Number=` FEATS value from
  `Sing,Plur,Dual,Trial,Pauc,Grpa,Grpl,Inv,Ptan`; an absent Number makes only that row
  typed `not_applicable`, while duplicate/unknown values block. Aside from the
  explicitly source-inapplicable, vocabulary-OOV, and Number-absent cases,
  `__DROP__`, missing, or unknown labels block.
- `entity_binary` has `O,ENTITY`. `entity_type` has `O,PER,ORG,LOC,MISC`:
  AMALGUM `person->PER`, `organization->ORG`, `place->LOC`, and every other
  syntactically valid TYPE maps to `MISC`; historical NER B/I prefixes are
  removed and `person/per->PER`, `organization/org/corporation/group->ORG`,
  `location/loc/building->LOC`, `o/0->O`, else `MISC`. When multiple spans cover
  a token, binary is `ENTITY` and coarse type uses the deterministic span order
  already frozen above. `source_genre` labels are exactly
  `UD_English-EWT:UD,DFKI-SLT/few-nerd:NER` for discovery;
  `UD_English-GUM:UD,flaitenberger/wnut_17:NER` for calibration; and
  `AMALGUM:{academic,bio,fiction,interview,news,voyage,whow}` for each C role.
  Existing Atlas labels are inputs to be recomputed/checked against these rules,
  not trusted as alternate semantics. Golden fixtures cover every closed class,
  bin boundary, Unicode case/punctuation edge, missing-feature path, and source.
- Prefix-offset is real, not placeholder. Tokenize the four standalone literals
  `""`, `"In fact, "`, `"As a result, "`, and
  `"According to the report, "` with the frozen tokenizer, no special tokens;
  require four distinct prefix-token lengths. Prepend those exact token-ID
  arrays to an unchanged base input-ID array, score original rows only, and
  shift every original first-subtoken position by that realized length. A base
  sentence is eligible only if it has >=2 integer words, every word has a
  first-subtoken under `is_split_into_words=True`, no truncation occurs, and all
  four variants are length <=128. Bind literal, token IDs, base/variant IDs,
  word IDs, offsets, and row IDs. All four classes occur once per eligible base.
  The closed label is template ordinal `P0,P1,P2,P3` in listed order; realized
  token length is bound as evidence but never silently merges two classes.
- Every “u64-length-prefixed tuple” below uses one typed codec. A tuple begins
  `u64be(element_count)`. A string element is byte tag `0x01`, then
  `u64be(UTF8_byte_count)`, then NFC UTF-8 bytes; a non-NFC input blocks. An
  integer element is byte tag `0x02` then an unsigned `u64be`, and values outside
  `[0,2^64-1]` or bools block. No implicit stringification, signed integer,
  null, or other type exists; tuple-byte lexicographic order is the tie-breaker.
  Golden cap tuple
  `("msae_exposed_source_measurement_v3","C1","amalgum:academic","doc-1","sent-1",7,"row-1")`
  hashes to `702c0042f05b90c085930fa69cfebba10d72b5d66f34de8992f97a9382a9be8a`;
  golden map tuple
  `("msae_exposed_source_measurement_v3","20260820","calibration","absolute_bucket","gum",0,0)`
  hashes to `ca3ff78f94a1375a397676ea7042323554e88b5688f446bd18e1ff84a63bc9a7`.
- Apply one 256-**base-row** cap per physical document before four-template
  expansion. Order candidates by SHA-256 of the u64-length-prefixed tuple
  `(protocol_id,role,source_stratum,document_id,sentence_id,word_index,row_id)`,
  then its encoded tuple bytes; retain the first 256. Freeze one common
  token and lemma vocabulary from labels with document frequency `>=20` in every
  applicable discovery, calibration, C1, and C2 role; order by minimum-role DF
  descending, total DF descending, then UTF-8 label ascending. Maximum 256.
- Each applicable task/role needs >=25 groups, every retained class >=20 groups,
  >=2 classes, and no role overlap. Freeze 500 unconditional source/genre-
  stratified maps for **all four roles**. For each
  `(role,task,stratum,draw=0..499,slot=0..n-1)`, take the first eight bytes of
  SHA-256 over the u64-length-prefixed tuple
  `("msae_exposed_source_measurement_v3","20260820",role,task,stratum,draw,slot)`
  as unsigned big-endian modulo `n`, indexing UTF-8-sorted physical group IDs;
  there is no redraw. Multiplicity is sample weight. A draw is finite only when
  every frozen class has positive weight in >=2 distinct physical groups and
  the pooled class-prior macro-F1 denominator is finite and positive. Let
  integer multiplicity-weighted class counts be `w_c`, `W=sum(w_c)`, `K` the
  frozen class count, and `m` the UTF-8-smallest class among those with maximum
  count. The locked
  majority-class chance predictor has `chance_macro_f1 =
  2*w_m/(K*(W+w_m))` and denominator `1-chance_macro_f1`, evaluated as exact
  rational integers before Decimal serialization. A zero count, `K<2`, `W=0`,
  denominator `<=0` or `>=1`, overflow beyond unsigned 64-bit counts, or missing
  group evidence is nonfinite/ineligible. Golden counts `[2,1]` give chance
  `2/5` and denominator `3/5`. Each task/role
  needs >=490/500 finite maps. Bind every map and the complete per-draw class,
  group, denominator, pass, and reason matrix.

## Immutable execution closure and endpoint registry

A canonical v3 protocol manifest binds path, size, mode, and SHA-256 for:

- this RFC; v1 failure/status/overlap; v3 source, overlap fixtures/results,
  row/task/support/template/map manifests; remediation/v3/replay/launcher code;
- all selected source files and every discovery/calibration prepared/raw input;
- all four g4/g5/g6/g7 checkpoints and training summaries, with exact paths,
  run IDs, seeds, roles, and the already verified digests;
- Pythia model config/weight shards/generation config and tokenizer files at
  revision `582159a2dfe3e712a8d47ae83dec95ae3bde8e7e`;
- Python executable, requirements lock, installed package versions, Torch/CUDA,
  driver, allowed GPU UUID inventory, deterministic flags, dtype, layer, and
  first-subtoken path;
- exact tolerance ladder, safety factor, four strata, tasks/families,
  thresholds, baseline candidates/locked robustness transforms, counterfactual
  cells, 500-map estimator, randomization/CI/max-stat rules from the reviewed v1
  RFC, and operator authorization text/digest.

V1 import precedence is explicit. The source RFC SHA-256 is
`4e92e3086056ce55bb87fd64e9e49c8040f34a1eb3aebd62d12e9627f620cde5`.
`protocol_imports.json` imports only byte slices (1-indexed inclusive lines)
`V1.CALIBRATION_REPLAY=104:139` digest
`4d2d61a8047d11ea9ddf6201a86b3211aeb041ba4d885f6399476310d5b8a83a`,
`V1.CHECKPOINT_LINEAGES=140:176` digest
`4b134bf7af818f1cde864f4bb83d1574adc58e121b3af98ef6f2647783b767ef`,
`V1.ENDPOINT_REGISTRY=254:341` digest
`d10ab2ad8b260ce410e0f22931d7adc913ea0db23609ae3beb05e5336d84d137`,
and `V1.ESTIMATOR_INFERENCE=342:405` digest
`8ec387f1b6b9532922822301d9fb976960ec5fcab3eb342e7cfd65e0e0a52eaa`.
No other v1 scientific rule is imported. In particular, v3's genuine
eight-class `absolute_bucket=floor(first_subtoken_index/16)` explicitly
supersedes the v1 seven-way wording and all v1 label/parser/support/map schemas;
an imported endpoint task ID is resolved only through the v3 task manifest, and
any embedded v1 cardinality/schema causes rejection.

Every manifest/closure/history entry also has a closed-enum
`verification_action`. Accessible bytes use `content_rehash`; exactly the three
exposed-quarantined payloads use `lstat_only_against_frozen_v1_evidence` and bind
their M0 and M4 device/inode/type/mode/size/nlink/ctime_ns/mtime_ns plus the
frozen v1 hashes without opening them; `nlink` must equal one and any metadata
drift or same-inode in-tree alias blocks. These fields prove identity/metadata
stability, not current content equality. No other entry may use metadata-only verification. The builder, final
review checker, signer, and launcher install an open/read/hash tripwire for those
three realpaths, report all three metadata comparisons and
`sealed_payload_content_reads=0`, and block on any requested content access.

Closure enumeration is mechanical rather than a hand-picked import list. Parse
all local Python entry points recursively, resolve every local import from the
repository root without importing it, and reject dynamic local-module imports;
bind every reachable `.py`, package `__init__.py`, data/template file opened by
those modules, symlink target, shell entry point, and executable. For each
third-party distribution in the resolved import graph, bind distribution name,
version, metadata and `RECORD` bytes, verify every `RECORD` hash available, and
bind each actually loaded native library plus its resolved real path and bytes.
Bind the interpreter and ELF/shared-library closure reported by `ldd`, rejecting
missing or path-changing entries. The model/tokenizer allowlist is exact: bind
every file enumerated by the local snapshot manifest and reject an extra,
missing, symlinked-outside, or network-resolved model file. The replay records
the runtime import/native-library manifest and actual GPU UUID/driver, and Stage
B requires it to be a subset/equal realization of the frozen allowed closure.
Any unresolved/dynamic dependency blocks Stage A rather than being ignored.

Static closure analysis also walks every `open`/`Path` file operation,
config/path field, `subprocess`/`os.exec*`/`os.system` target, shell command, and
`ctypes`/`dlopen` site. A literal is resolved immediately; a dynamic value is
allowed only when its complete finite mapping from a typed frozen config field
to canonical realpaths/argv is enumerated in the manifest. A plugin/network/
PATH-search/process/library target outside that mapping blocks. A CPU/no-model
trace harness monkeypatches file/process/library/network surfaces and exercises
every public v3 entry point; observed requests must be a subset of the static
allowlist, and planted indirect-open, dynamic subprocess, shell expansion, and
`dlopen` escapes must fail. Third-party native libraries are prospectively
allowed only by verified distribution `RECORD`/ELF closure; after real import,
the runner snapshots `/proc/self/maps`, and Stage B requires every actually
loaded library to be in that allowed set. Runtime realization may narrow but
never extend the prescore closure.

An exhaustive role-applicable registry is generated from a declarative matrix
and validated against independently generated expected cells: C1 contains only
raw/simple G1 operands; C2 contains g4/g5/g6 plus descriptive g7 and locked
baselines for G2; raw never receives learned K2 branch names; g7 is registered
as matched negative control, never a replicate. Stage A evidence binds the
entire manifest digest. Any closure drift blocks before model import.

The generic remediation builders are treated as untrusted schema primitives,
not proof of v3 readiness. A v3-only wrapper constructs each evidence category
from typed overlap, parser, support, map, closure, endpoint, authorization, and
dependency objects; callers cannot inject opaque name/digest evidence. The
wrapper recomputes those objects and their digests, embeds the base artifact,
and emits a distinct v3 Stage-A schema. The v3 runner and launcher accept only
that wrapper schema and revalidate it, never a standalone base `ready` artifact.
Tests forge otherwise-valid generic/base artifacts, substitute each typed
object and digest, omit each required endpoint, and require wrapper and launcher
rejection.

Here `authorization` at Stage A means only a typed **pre-review authorization
commitment**: protocol/operator-instruction digest, public key bytes/fingerprint,
allowed `calibration_replay_only` scope, envelope algorithm/schema, maximum
24-hour lifetime, and nonce-directory canonical realpath
`/jumbo/lisp/f004ndc/.msae_state/independent_measurement_v3/nonces`, expected device/inode,
current UID ownership, non-symlink type, and exact mode `0700`. It contains no verdict,
nonce, issue/expiry time, or signature and cannot authorize execution. The
post-SHIP signed envelope is external to Stage A, names the exact commitment and
v3 Stage-A digests, supplies those remaining fields, and is accepted by the
runner only if it refines rather than changes the frozen commitment.

## Typed Stage-B replay QA

Use the four frozen public-GUM strata, one reference plus three fresh forwards,
all six unordered pairs, the existing eight-entry ladder, and safety factor 2.
Before `torch` import/model load verify Stage A ready, closure hashes, review
seal, operator digest/scope/expiry, unused nonce, GPU lease, config, runner, and
local model/tokenizer blobs.

- Create every NPY and JSON with `O_EXCL`; NPY bytes use `BytesIO` then one
  create-once write. Cached no-op reload requires identical NPY SHA-256,
  remediation payload SHA-256, dtype/shape, and ordered-row digest.
- Unit-by-unit replay must reproduce the exact registered batch row order. Apply
  the selected tolerance with the selector inequality
  `2*abs(a-b) <= atol + rtol*max(abs(a),abs(b))` in float64 with overflow and
  nonfinite rejection; do not use `np.allclose`.
- Pair alignment reconstructs exact pair IDs, source/target local indices,
  input/word/row IDs, coverage, and payload hashes from observations. Counts or
  suffixes alone never pass.
- Persist each typed QA evidence artifact separately and bind its digest into
  Stage B. Stage B exists only after a complete replay; technical failures write
  create-once `not_run` and no Stage B.

## Review, authorization, GPU, and tmux

Externality is the fresh-context `/adversarial` review transcript, not a false
cryptographic identity claim. Generate an Ed25519 keypair *before* the final
prescore review, store the private key create-once with mode `0600`, and freeze
the public key, fingerprint, algorithms, and private-key path/mode in the
closure; the key alone conveys no authorization. After those exact bytes and
Stage A receive SHIP, use that pre-reviewed key to create a coordinator integrity
seal. The signed canonical envelope binds the SHIP transcript and transcript
digest, closure/config/v3-Stage-A hashes, exact current user instruction and
digest, calibration-only scope, unique nonce, issue/24-hour expiry, and
single-use nonce path. The runner verifies signature/fingerprint, review digest,
scope, time, operator digest, and opens/verifies the committed nonce directory
with `O_DIRECTORY|O_NOFOLLOW`. Holding that directory FD, it atomically creates
the nonce-consumption record relative to it with
`openat(O_CREAT|O_EXCL|O_NOFOLLOW,0600)`, writes the envelope/Stage-A digests,
`fsync`s file and directory, and rechecks path versus FD device/inode/link count
before any model/GPU action and at handoff. A pre-existing, unlinked, renamed,
symlink-swapped, foreign-owned, permissive, or ambiguous record/directory is
terminal and requires a new reviewed authorization. This signature proves byte integrity,
while the recorded forked review supplies independence.

M3 creates once, before Stage A, the current-UID-owned non-symlink directories
`/jumbo/lisp/f004ndc/.msae_state`,
`.../independent_measurement_v3`, and `.../nonces`, all exact mode `0700`, then
binds their canonical device/inode/owner/mode. The signed-envelope canonical
bytes determine the sole record name as lowercase
`sha256(envelope_bytes).consumed`; only that relative regular-file name is
allowed, at mode `0600`. The external atomic record is authoritative replay
state. The separate live-run `nonce_consumed.json` is a create-once attestation
of its device/inode/hash and is never used to decide freshness. M4 requires the
directory empty; post-review/signature projections still require the derived
record absent; only the runner's consume transition may create it.

The one shared GPU-lock namespace for every MSAE launcher is
`/jumbo/lisp/f004ndc/.msae_state/gpu_locks`, created/verified current-UID-owned,
non-symlink, exact mode `0700` during M3 and bound in Stage A. A validated
`nvidia-smi` UUID's ASCII bytes map to
`sha256(uuid_ascii).lock`; the persistent record is protocol-independent and
stores only schema `msae_gpu_uuid_lock_v1` plus the exact UUID. Protocol/run/
holder PID/start-ticks identity lives in this run's create-once
`lock_acquired.json`, not the shared lock-file payload.
Open only relative to the held directory FD using
`O_RDWR|O_CREAT|O_NOFOLLOW|O_CLOEXEC`, mode `0600`; require one-link regular file,
current UID, exact mode, contents empty or an exact matching record, and stable
device/inode before taking nonblocking exclusive `flock`. A mismatched/stale-
format object blocks; a valid unlocked object is reusable. Broker and worker
inherit the same open-file description, never reopen it. Contention tests use a
separate real process and the same namespace/UUID-derived filename.

The launcher chooses a GPU with no compute process, <1024 MiB used, utilization
<=5%, ordered by `(memory, utilization, UUID)`. Recheck after acquiring the UUID
flock. Transfer the same open-file description with `SCM_RIGHTS` to the worker;
broker and worker both retain it. The worker validates the create-once broker
record, PID/start ticks, FD target/ownership, config, nonce, and UUID-scoped CUDA
identity before model import. Use one process group. Broker enforces a six-hour
deadline, TERM then KILL after 60 seconds, and create-once technical-failure
status. Any failed handoff kills/verifies the entire group and tmux session.

After `tmux -S /tmp/msae_independent_measurement_v3_${A}.sock new-session -d -s msae-independent-v3-calibration`,
make only the bounded handoff checks needed to prove
live session/pane/worker/broker/FD/config/nonce lineage. Return session, run, and
log paths immediately; do not poll a heartbeat or result.

Final review never relies on ordinary `git diff`, which omits untracked files.
M4 emits create-once `prescore_candidate_manifest.json` containing the candidate
root realpath; `candidate_files` containing every then-existing candidate path
except the manifest itself with path/type/mode/size/SHA-256 and verification
action; every closure entry; v3 Stage-A and closure digests; and the complete
porcelain-v3 repository status with every pre-existing dirty/untracked path
classified as protected baseline or candidate. It also contains
`required_absent_post_review_outputs`: exactly the adversarial transcript path
and the entire live-run root, plus `required_external_state` binding key/state/
nonce/GPU-lock directories and requiring both build directories, both
digest-derived review files, the digest-derived tmux socket, and every nonce
record absent. Its schema explicitly excludes self-hashing; the
reviewer independently hashes the final manifest bytes and reports that digest.

The exact CPU/no-model reviewer command first sets
`M=$(sha256sum reports/provenance/msae_independent_measurement_v3/prescore_candidate_manifest.json | awk '{print $1}')`
and requires `M` to full-match lowercase `[0-9a-f]{64}`. It then runs
`.venv-atlas/bin/python -B -I scripts/msae_independent_measurement_v3.py prescore-traced-check --manifest reports/provenance/msae_independent_measurement_v3/prescore_candidate_manifest.json --output /tmp/msae_v3_prescore_check_${M}.json --trace /tmp/msae_v3_prescore_trace_${M}.log`,
followed by
`.venv-atlas/bin/python -B -I scripts/msae_independent_measurement_v3.py verify-prescore-trace --manifest reports/provenance/msae_independent_measurement_v3/prescore_candidate_manifest.json --check /tmp/msae_v3_prescore_check_${M}.json --trace /tmp/msae_v3_prescore_trace_${M}.log`.
`prescore-traced-check` opens both absent outputs itself with
`O_CREAT|O_EXCL|O_NOFOLLOW|O_CLOEXEC`, mode `0600`, verifies path/FD device and
inode, makes exactly those two FDs inheritable, and invokes pinned `/usr/bin/strace`
`-f -qq -yy -e trace=open,openat,openat2,creat -o /proc/self/fd/<trace_fd>` on
the internal `prescore-check --output-fd <check_fd>`; after child exit it re-verifies path/FD identity,
fsyncs, and closes. Thus collision prevention occurs before strace opens its
already-held FD rather than being falsely attributed to `strace -o`. Both
`/tmp` files are removed
after their hashes are captured in the transcript. `prescore-check` output is
canonical JSON with protocol/checker-code/manifest/candidate-tree/closure/
Stage-A/status digests, every entry action/result, complete porcelain-status
projection, quarantined metadata results, `sealed_payload_content_reads=0`, and
`eligible`; any mismatch exits nonzero. `verify-prescore-trace` resolves `-yy`
FD paths, rejects any open/openat/openat2/creat touching a quarantined payload,
requires the check JSON eligible and all expected digests, and prints one
canonical digest line for the critic to quote. Planted tripwire tests prove an
indirect sealed open is observed and rejected.
The wrapper invokes its inner Python as the same pinned executable with `-B -I`
before importing any local module; `-B` rather than the environment variable is
the bytecode-write control because isolated mode ignores Python environment
settings.

The fresh-context reviewer receives that explicit manifest, rehashes every
`content_rehash` byte, performs only the three typed quarantined `lstat` checks,
recomputes the closure and Stage-A digests, proves zero sealed content reads,
requires no status entry or candidate file to be unenumerated, verifies every
required-absent output is absent, and states all exact digests in its SHIP
transcript. Installing the transcript create-once triggers a canonical
`post_review` status projection that permits only that exact new path and binds
its type/mode/size/SHA-256/SHIP digest; everything else must equal M4. Signing
then triggers `post_signature`, which additionally permits only the exact
authorization file and otherwise requires the live-run root empty. The launcher
repeats that projection immediately prelaunch; nonce, lock, logs, cache, QA,
status, failure, and Stage-B paths remain required absent until their respective
create-once runtime transitions. Any other untracked, staged, unstaged, mode,
symlink, or byte drift blocks. Transcript and envelope are post-candidate
external evidence that bind back to, but do not mutate, the reviewed candidate.
The critic's exact returned report is canonicalized only as
`report.rstrip("\n")+"\n"`, UTF-8 encoded, and installed with `O_EXCL` mode
`0644`; its SHA-256 must equal the digest used by the signed envelope. Missing
`VERDICT: SHIP`, any expected digest line, or byte-preserving rehash blocks.

## Milestones

- [ ] **M0 — V1/v2 preservation and v3 plan.** Hash both terminal attempts; plan gets
  adversarial SHIP. Acceptance: exhaustive v1 and v2 protected manifests are
  installed, every predecessor byte is unchanged, both exact terminal failures
  remain explicit, the v2 post-hoc analysis is separately labeled, the complete
  pre-v3 `data/` baseline manifest is create-once with v3 root absent, and the
  exact M0 completion-manifest digest is independently reviewed and supplied to M1.
- [ ] **M1 — Overlap remediation.** Implement fixtures and v3 audit. Acceptance:
  all planted cases pass and unchanged AMALGUM split has a complete result.
- [ ] **M2 — Strict labels/maps.** Produce four-role rows/support/templates/maps.
  Acceptance: strict parser and >=490/500 finite requirements pass or Stage A
  remains blocked.
- [ ] **M3 — Replay/authorization/launcher implementation.** Implement typed QA,
  the pre-review authorization commitment and post-review envelope verifier,
  generate the create-once Ed25519 keypair, and implement nonce, FD/PGID cleanup,
  and launcher behavioral tests. Acceptance: all CPU/no-model checks pass and
  public key/private path+mode are final; no authorization envelope exists.
- [ ] **M4 — Final closure/registry/Stage A.** Only after every bound M3 code/test/
  key byte is final, freeze the full manifest and build twice. Construct the
  complete candidate tree twice in separate temporary roots;
  acceptance requires identical relative path/type/mode/size/SHA-256 manifests
  and byte-identical Stage A. M4 descriptor-safely rehashes every exact M0--M3
  destination and accepts but never replaces it; any mismatch blocks. Only the
  enumerated M4-new destinations (`dependency_closure.json`,
  `endpoint_registry.json`, `environment_allowlist.json`, `stage_a.json`,
  `status.json`, and `prescore_candidate_manifest.json`) are installed with
  `O_EXCL`. Stage A is ready with no self-asserted evidence.
- [ ] **M5 — Prescore and live handoff.** The manifest-complete exported
  candidate receives adversarial SHIP with independently recomputed manifest,
  closure, Stage-A, and repository-status digests; sign/consume authorization;
  launch on free GPU in tmux; return without results.
  No bound byte may change between M4 freeze, this review, signing, and launch.

## Definition of done

- V1 remains failed and every v1-owned protected byte is preserved; the three
  non-v1 Atlas final payload identities are exposed/quarantined with metadata
  stability only and no false current-content/blindness claim.
- V3 is explicitly exposed-source, uses unchanged documents, and passes a
  fixture-validated substantive-overlap audit without hiding boilerplate.
- Exact four-role support, vocabulary, templates, 500 maps, and pass matrix are
  frozen and valid.
- Full transitive execution closure, four lineages including descriptive g7,
  and exact role-applicable scientific registry are hash-bound.
- Stage A is reproducibly ready; no Stage B exists before a real replay; no
  confirmation/Stage C is run.
- Authorization, nonce, GPU FD/UUID/PGID containment, technical-failure
  separation, and typed replay QA have behavioral failure-path tests.
- Final exact prescore bytes receive `/adversarial` SHIP before any model/GPU/
  tmux action.
- A verified tmux calibration handoff occurs on a free GPU and the response does
  not claim or await its result.

## Risks and one-way doors

AMALGUM content is already exposed and cannot become pristine again. A revised
overlap rule can be overfit to known boilerplate; planted positive/negative
fixtures, unchanged split, fixed thresholds, and independent review mitigate but
do not erase this. Source/annotation-family dependence remains a paper
limitation. Signing/nonce consumption and GPU launch are one-way; both occur
only after ready Stage A and prescore SHIP.

## Verification plan

- From the repository root run one `bash -euo pipefail` block that sets
  `V=/tmp/msae_independent_measurement_v3_verify`, requires it absent, creates it
  mode `0700`, installs `trap 'rm -rf -- "$V"' EXIT`, creates mode-0700
  `$V/tmp`, and exports `TMPDIR=$V/tmp`. Inside that block run
  `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 .venv-atlas/bin/python -B -m pytest -q -p no:cacheprovider --basetemp=$V/pytest tests/test_msae_measurement_remediation_v1.py tests/test_msae_independent_measurement_v1.py tests/test_msae_independent_measurement_v3.py`;
  then in-memory syntax compilation (no `py_compile` output) with
  `.venv-atlas/bin/python -B -c 'from pathlib import Path; ps=["scripts/msae_measurement_remediation_v1.py","scripts/msae_independent_measurement_v1.py","scripts/run_msae_independent_calibration_v1.py","scripts/msae_independent_measurement_v3.py","scripts/run_msae_independent_calibration_v3.py"]; [compile(Path(p).read_bytes(),p,"exec") for p in ps]'`;
  then `bash -n scripts/launch_msae_independent_calibration_v1.sh scripts/launch_msae_independent_calibration_v3.sh` and `git diff --check`.
- Test malformed CoNLL-U/entity events, exact/near/fragmented/boilerplate overlap,
  exact audit-exclusion/write-allowlist escapes, tuple-codec golden vectors,
  multi-process/multi-`PYTHONHASHSEED` weighted-gate byte equality,
  manifest-complete prescore candidate/status rehashing,
  role/vocabulary/map failures, closure drift, endpoint applicability, cache
  bytes/payload/row reorder, selector boundary/overflow, pair alignment,
  signature/fingerprint/operator/scope/expiry/nonce replay, GPU contention,
  foreign/permissive nonce directory, nonce unlink/rename/symlink swap,
  delayed/missing handoff, broker/worker death, timeout, and PGID cleanup.
- Run no model, GPU, or tmux command before final prescore SHIP.
