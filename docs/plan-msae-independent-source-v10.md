# PLAN — MSAE independent-source v10 terminal-repair continuation

Date: 2026-09-15  
Status: prospectively amended after source-free implementation review; amended plan review required before the repairs below  
Owner: MSAE project  
Candidate: official Universal Dependencies Swedish Talbanken at immutable commit
`c434778d9511be5c35a6a11531f0107a960fb5d6`

## Goal

Finish the independent-evidence readiness obligation without reopening any terminal predecessor.
V10 may re-acquire the same immutable, independently maintained official non-project repository in a
new namespace, run source-family, license, support, cross-role, and full pre-v8 accessible-history
overlap gates before any model scoring, and—only if all gates pass—publish a replacement blind
payload under private custody plus a public no-training seal.

V10 exists for exactly two bounded **scientific** defects/hypotheses exposed by the terminal V9 run:

1. V9 publicly retained only the aggregate failure `missing_or_unknown_field`; a lemma `_` is the
   single prospectively chosen hypothesis to repair, but the source-free record does not establish
   which member of that combined predicate triggered; and
2. V9's B1 zero-work verifier reconstructed the historical scientific-entry inventory against the
   later rejection file and therefore failed with `post_baseline_inventory_path_drift`.

V9 is immutable and non-retriable. V10 is a new one-shot protocol, not a patch or retry inside V9.
A V10 success is described only as
`ready_independently_maintained_non_atis_source_pre_v8_history_screened`. It is not independent
replication, model-pretraining independence, or proof of global content separation.

## Non-goals and hard prohibitions

- Do not modify, clean, retry, or semantically reopen V8 or V9 raw/source/private state.
- Do not open, read, hash, parse, or print Atlas quarantine content. The exact quarantine paths remain
  lstat-only.
- Plan review and source-free implementation review must not open any V8/V9/V10 raw or private bytes.
- No model/tokenizer load, forward pass, scoring, activation extraction, GPU query, K2 restart, branch
  training, or tmux launch is authorized by this plan.
- V10 success still leaves scoring and all training closed pending a separate reviewed prescore plan.
- Do not describe exposed AMALGUM V3 as independent replication.
- Do not stage ignored `data/`, `results/`, `pilot_runs/`, checkpoints, raw, private, or quarantine paths.

## Frozen predecessor authority

The direct predecessor is the V9 terminal failure review:

- V9 plan: `docs/plan-msae-independent-source-v9.md`, SHA-256
  `0607886af9561d8418fd7a153322e6b59cd47404f33174c49b07bec5284cd57e`.
- V9 terminal review: `reports/adversarial/msae_independent_source_v9_terminal_failure_review.md`,
  SHA-256 `bafa2fbcc1c4ba4e6f3ffe9c696e63f4aa846d5b12a8922bbaa3ac36a770af28`,
  verdict `BLOCK`, explicitly requiring a new reviewed protocol.
- V10 carryover authority:
  `reports/provenance/msae_independent_source_v10/v9_carryover_authority.json`, SHA-256
  `da13ae40e64c9828b2d08c29b4ff280bac5c71eeb8578a977f953f2169f7585d`.

The carryover is canonical ASCII JSON plus one LF, mode `0644`, `nlink=1`. Its exact top-level key set
is `gpu_queries,k2_or_branch_training_authorized,model_operations,model_scoring_authorized,opaque_raw_hash_reads_for_this_record,quarantine_content_reads,schema_version,stage_c_authorized,status,training_runs,v9_acquisition_sha256,v9_control_files,v9_control_map_sha256,v9_data_directories,v9_partial_scientific_prefix,v9_raw_file_map_sha256,v9_raw_files,v9_rejection_failure_code,v9_rejection_sha256,v9_scientific_entry_sha256,v9_source_commit,v9_source_content_printed,v9_source_content_semantically_read_by_v9_builder,v9_source_content_semantically_read_for_this_record,v9_terminal_review_sha256,v9_terminal_verify_status`.
It binds exactly 20 V9
control/terminal files, three V9 data directories, four V9 raw-file lstat records plus their
acquisition-reported SHA-256/Git blob IDs, the one-artifact scientific prefix
`document_group_census.json`, acquisition/scientific-entry/rejection/terminal-review hashes, V9
failure `missing_or_unknown_field`, and V9 verifier failure
`failed_post_baseline_inventory_path_drift`. Its status is
`retained_v9_scientific_rejection_and_terminal_verifier_defect`.

Control records have exactly `path,device,inode,mode,nlink,size,sha256`; directory records exactly
`path,device,inode,mode,nlink,size`; raw records exactly
`path,device,inode,mode,nlink,size,sha256,git_blob_sha1`. Arrays are strictly lexicographic by unique
POSIX path and duplicates reject. The control-map projection is exactly `{path:sha256}` and has
SHA-256 `d0035594710b62cd9b998367136f2bf02110bf59095d359b0f2dbdd75e1aec3c`.
The raw-map projection is exactly
`{path:{sha256,size,git_blob_sha1,mode,nlink}}` and has SHA-256
`881ac46eab4a9e4ecf50a2afb088d37ac98f060b84a45ede90d79007e216f363`.
Both digest domains use `json.dumps(value,sort_keys=True,ensure_ascii=True,separators=(",",":"),allow_nan=False).encode("utf-8")` with no trailing LF.

Every V10 phase recomputes the carryover file hash, its exact schema and canonical map digests, all 20
public control hashes, and V9 directory/file lstat metadata. V9 raw bytes are never reopened: their
expected content hashes come only from reviewed acquisition/carryover public records. The nested V8
carryover is hash-bound as one of the 20 V9 controls and preserves the historical V8 evidence, but V10
makes no fresh current-state claim about V8 data. Any metadata, control, map, or terminal-status drift
stops V10.

The V9 historical registry and alias screen remain the prospective source-history authority. The V9
files themselves were created after V8, but they preserve the exact input array that V8 froze before
its first candidate acquisition under the reviewed V8 carryover exclusion:

- `reports/provenance/msae_independent_source_v9/historical_source_registry.json`, SHA-256
  `3166d09141374506d7d200fa8d630a66e4a790f5a3f2e81778ed522d4a327863`;
- `reports/provenance/msae_independent_source_v9/preacquisition_alias_screen.json`, SHA-256
  `cdda84035279b78698f98c760c5ce12d5276b9b2afbc8e4218133d8207dccafd`;
- exact history input count `16,133`; canonical inputs digest
  `8070a7cdd536a0dbd6104ff1dfb279ef01fb0acf98e969227625324155227564`;
- zero source-use evidence and zero quarantine reads.

V10 copies these two public objects byte-for-byte into its own provenance namespace, records the V9
source paths/hashes, and verifies byte equality. It does not rescan candidate-contaminated V8/V9
artifacts into the historical source universe and makes no post-V8 global-absence claim.

## Exact candidate and acquisition

The only candidate is:

- repository `https://github.com/UniversalDependencies/UD_Swedish-Talbanken.git`;
- commit `c434778d9511be5c35a6a11531f0107a960fb5d6`;
- files, in this order:
  `sv_talbanken-ud-train.conllu`, `sv_talbanken-ud-dev.conllu`,
  `sv_talbanken-ud-test.conllu`, `LICENSE.txt`.

V10 acquisition is a new one-shot sparse clone into a fresh external scratch directory and installs
exactly those four files into
`data/msae_independent_source_v10/raw/c434778d9511be5c35a6a11531f0107a960fb5d6/`.
The V9 runner's reviewed command/environment/tree/blob/scratch cleanup and create-once publisher
contracts are inherited exactly with V10 path/schema substitutions. V10 uses schema labels prefixed
`msae_independent_source_v10_`, split domain `msae-independent-source-v10/C1C2-group`, token domain
`msae-v10/token\0`, lemma domain `msae-v10/lemma\0`, and process domain `msae-v10/process\0`.
The one deliberate domain inheritance is candidate pedigree: it remains exactly
`b"msae-v9/pedigree\0"` so candidate hashes are comparable with the byte-identical frozen registry.
A durable V10 acquisition-entry
marker precedes every subprocess. Success or rejection is terminal and non-retriable. No source
content is printed.

## Authority order and exact additions

The mandatory order is:

1. this plan;
2. independent source-free plan review with `VERDICT: SHIP`;
3. V10 builder, acquisition runner, config, tests, copied history registry/screen, and source-free log;
4. independent source-free implementation review with `VERDICT: SHIP` while V10 data/acquisition
   paths are absent;
5. full current-history baseline plus process/training snapshot;
6. no-replace authority manifest;
7. independent provenance-only authority review with `VERDICT: SHIP`;
8. one-shot acquisition using the exact authority-review SHA on argv;
9. one-shot scientific preparation;
10. terminal verification (zero-work for B0/B1; deterministic model-free reconstruction for B2)
    and independent readiness/failure review;
11. paper/claim-ledger/synthesis updates, final verification, explicit safe staging, and commit.

There is no V10 prefix exception in history recensus. The only pre-acquisition post-baseline public
additions are, in order:

- `reports/provenance/msae_independent_source_v10/baseline_inventory.json`;
- `reports/provenance/msae_independent_source_v10/preacquisition_authority_manifest.json`;
- `reports/adversarial/msae_independent_source_v10_preacquisition_authority_review.md`.

Acquisition then adds exactly entry plus success or rejection. Preparation adds exactly a B0
preflight rejection, or a scientific entry followed by an ordered scientific prefix and B1 rejection,
or the complete B2 success set. Named `.building` temps are never valid finals. Unknown files,
prefix-lookalike sibling directories, symlinks, hardlinks, special files, mode/nlink drift, ancestor
exchange, or extra raw/private entries stop.

## Baseline, containment, and capabilities

The baseline inventories every accessible repository path through pinned directory descriptors. It
hashes supported public files through no-follow descriptors, records archives under the inherited
bounded one-level policy, and records exact Atlas quarantine paths by lstat only with
`content_reads=0`. Current V9 data state is verified only through the direct carryover authority and
excluded from content traversal; nested V8 evidence is historical/hash-bound rather than freshly
recensused. The V10 namespace must be absent.

The process snapshot is the exact sorted `/proc` schema inherited from V9. It must be `eligible` with
zero forbidden identities before baseline publication and scientific entry. The training-root census
must bind every results/checkpoint/train-metrics path and be unchanged before acquisition,
preparation, and terminal closure. Capability fields remain false/zero for model, GPU, scoring,
training, K2, branch, and Stage C.

Public writes use exclusive temp creation, complete short-write loops, file fsync, hard-link
no-replace publication, inode-identity cleanup, cleanup parent fsync, and final parent fsync. All
ancestor opens are component-by-component `O_DIRECTORY|O_NOFOLLOW`; final files use `O_NOFOLLOW`.
Publisher fault injection covers temp create/write/fsync/link/unlink/parent-fsync and restart recovery.

## Scientific preparation: inherited contracts and exact deltas

Except for the two scientific deltas below, the prospectively specified source-free control-plane
repairs below, and V9-to-V10 path/schema/domain substitutions, V10 inherits the
exact V9 scientific contracts: parser structure, document grouping, task inventory, role mapping,
deduplication, group-level C1/C2 split, support floors, candidate pedigree scanner, license evidence,
source-family comparison, cross-role overlap, accessible-history overlap predicates, artifact order,
payload schema/custody, recensus schemas, and no-training seal. Tests compare normalized ASTs of all
unchanged named functions against the frozen V9 builder SHA
`5714f714039ecf29f1203000ec628984ff22abe62703946891cb5eaf781fc5fa`.
No threshold, task requirement, history predicate, source-family predicate, or publication order may
change silently.

### Source-free control-plane conformance amendment

The first source-free implementation review returned `BLOCK` before any V10 baseline, authority,
acquisition, raw, private, or scientific state existed. This amendment prospectively authorizes only
the following control-plane corrections. They do not add a scientific hypothesis, relax a gate,
change a threshold, or authorize source/model work:

1. restore exact V9 non-lemma failure taxonomy (in particular, `DEPREL="_"` reaches the inherited
   `unknown_deprel` failure rather than the combined missing-field failure), and reject an observed
   V10 data namespace at baseline even when that namespace is an empty directory;
2. classify the post-entry private directory independently from the payload final. In B1 the
   classifier may prove exactly one of: no private directory, an empty mode-`0700` private directory,
   or a mode-`0700` private directory containing only the valid mode-`0600`, `nlink=1` payload. In B2
   only the last state is valid. The exact classifier-proven directory state is supplied to historical
   entry reconstruction; no caller-chosen subtraction is permitted; and
3. use filesystem-independent generated-directory records in every V10 post-baseline inventory.
   Such a record has exactly `path,state,disposition,type,mode,child_names`, with
   `type="directory"`, canonical lexicographically sorted direct child names, and no directory
   `st_size` or `st_nlink`. Historical scientific-entry reconstruction records data-root
   `child_names=["raw"]`, omits the later private-directory record, and retains the raw-root and
   immutable-commit child-name records exactly. Current B1/B2 inventories record the actual validated
   private-directory child set. No verifier may infer historical directory metadata by arithmetic on
   current `st_size` or `st_nlink`.

B2 additionally needs a finite representation of the gate/seal dependency: the seal's
post-baseline inventory represents its own final as exactly
`{path:"reports/provenance/msae_independent_source_v10/seal.json",state:"self_canonical_final"}`
and represents the already-published no-training gate as exactly
`{path:"reports/provenance/msae_independent_source_v10/no_training_gate.json",state:"dependent_canonical_final"}`.
`dependent_canonical_final` is valid only for that path in B2. Its bytes are not accepted from that
record: terminal verification reconstructs the expected seal, reconstructs the gate from the
expected seal hash, and compares both canonical files. History-recensus addition projection includes
regular finals plus both nonrecursive final states, so the gate cannot be omitted as drift.

### Delta 1 — CoNLL-U unavailable lemma

For an integer-token row, `LEMMA="_"` is accepted as the CoNLL-U unavailable marker. The literal `_`
is retained in the `Token` object, source-record hash, and private payload. Only public label
construction maps it to `lemma_identity=None`, so it contributes no lemma-identity class. Existing
support logic already ignores `None`; `lemma_identity` remains optional. Empty FORM, empty LEMMA,
unknown or unavailable UPOS, empty DEPREL, malformed HEAD, unavailable or unknown coarse DEPREL,
invalid FEATS, and malformed columns remain fail-closed exactly as in V9.

Synthetic goldens must show: an otherwise valid row with lemma `_` parses; payload preserves `_`;
its public lemma label is `None`; it is absent from lemma-class support; and the named still-invalid
field cases reject. No V8/V9/V10 raw bytes may be used in these tests.

### Delta 2 — state-relative entry reconstruction

Terminal classification occurs before historical entry reconstruction and first proves an exact B0,
B1, or B2 current-state universe, ordered-prefix rule, temp absence, and payload cardinality.

`_verify_terminal_entry` receives the already classified terminal state and the exact set of later
protocol additions. Its reconstruction of the historical `scientific_entry` inventory subtracts only
that exact, classifier-proven set before comparing the current protocol universe to the entry-time
universe. The allowed-later set is not caller-chosen:

- B1: exactly the validated scientific prefix plus `rejection.json`, an optional already-bound
  payload final, and the independently classified optional private-directory state (including a
  valid empty directory left by a pre-link payload-publisher failure);
- B2: exactly all later scientific finals plus the payload/private directory state;
- any extra, missing, non-prefix, rejection+seal, preflight+entry, or temp state fails before entry
  reconstruction.

All entry-time records themselves—common authority/acquisition files, filesystem-independent
generated-directory records, raw file lstat records, entry self record, file modes/nlinks/sizes,
acquisition-provided expected hashes, deferred raw read marker, and zero operations—must reconstruct
exactly. Current B1/B2 post-baseline inventory is
then reconstructed separately and must equal the retained terminal. History/training recensuses bind
all unrelated additions, so the state-relative subtraction cannot hide non-V10 drift.

Required regressions include the exact observed V9 shape (entry + one-artifact prefix + rejection),
zero-prefix B1, longer-prefix B1, complete B2, prefix gap, extra protocol file, V10-prefix sibling,
rejection+seal, final+temp, ancestor exchange, and every real publisher fault/restart row.

Delta 2 also closes V9's uncalled success reconstructor. Only after the classifier has proved exact
B2 may terminal verification authorize reads of the four **V10** raw files. It must invoke the
deterministic model-free reconstruction routine from those raw bytes and the frozen algorithms,
reconstruct every deterministic source/history-derived public object and the expected canonical
payload bytes, and compare each such public artifact byte-for-byte. The retained historical
point-in-time process snapshot is instead validated for canonical schema, digest, eligibility, zero
forbidden identities, and exact dependency bindings; a fresh terminal process snapshot must be
eligible under the frozen recensus rule. No-training and seal bytes are then reconstructed from the
independently reconstructed deterministic artifacts plus that validated retained snapshot and fresh
recensus evidence. The private final is never semantically reopened: compare it only by the
independently reconstructed payload SHA-256, byte count, record count, mode, and nlink.
The seal's own payload fields are not accepted as reconstruction evidence. Raw access is denied for
A, B0, B1, C, and any not-yet-classified state; V8/V9 raw and every predecessor payload remain
unreadable in all states. Regressions must reject a schema-valid but scientifically false public
artifact, a false payload hash/count, mutated V10 raw, corrupt retained process evidence, a fresh
ineligible terminal process snapshot, and any attempt to call reconstruction outside classified B2.

Candidate pedigree extraction and the frozen registry both hash normalized identifiers with exactly
`b"msae-v9/pedigree\0"`; any registry-domain mismatch fails closed. A synthetic golden places one
normalized identifier in both history and candidate and must block. All other V10 salts/domains are
the literal fresh values listed in the acquisition section.

## Source/history gates before scoring

After durable scientific entry and only then, V10 may read its own newly acquired raw files. It must
run, in the inherited order:

1. raw custody, official commit/tree/blob/hash reconstruction, and acquisition-command checks;
2. document/group support census;
3. strict CoNLL-U parse with the lemma delta and source-manifest publication (train, dev, and test
   roles are assigned internally here, but their public role manifest remains step 11);
4. license gate from `LICENSE.txt` only;
5. source-family gate;
6. candidate pedigree scan on all four raw files;
7. within-role exact deduplication;
8. cross-role exact normalized-text overlap removal;
9. full accessible-history support and normalized-content overlap against **all units deterministically
   extracted by the inherited V9 adapters from the 16,133 frozen text-source input records**;
10. support thresholds: all required tasks and at least two optional tasks in every role;
11. public deterministic source-native role manifest: train=discovery, dev=calibration, test=blind
    split input;
12. deterministic group-preserving C1/C2 split of retained test records;
13. fresh V10 private payload publication;
14. final process/history/training recensus, public no-training gate, and terminal seal.

The history gate rechecks the exact registry array/count/digest and its provenance as the input
universe frozen before V8 acquisition (not as files created before V8), records the inherited adapter census
and derived `history_unit_count`, and compares against every extracted unit rather than treating an
input file as one unit. Synthetic coverage includes a single frozen input that expands into multiple
physical-line/structured units. A short-circuit golden for every ordered gate proves the exact first
failure code and exact retained scientific prefix; no later artifact is published after failure.

Any ineligible gate publishes a canonical B1 rejection and stops. No model scoring occurs in any V10
branch.

## Claim boundary

A B2 seal uses exact terminal status
`ready_independently_maintained_non_atis_source_pre_v8_history_screened` and binds:

- `source_maintenance_relation="independently_maintained_official_non_project_repository"`;
- `history_screen_temporal_scope="project_accessible_history_frozen_before_first_v8_candidate_acquisition"`;
- `same_candidate_predecessor_attempts=["v8","v9"]`;
- `v9_semantic_parse_predecessor=true`;
- `independent_replication_claimed=false`;
- `researcher_unawareness_claimed=false`;
- `model_pretraining_independence_claimed=false`;
- `global_candidate_content_absence_claimed=false`;
- `general_content_separation_claimed=false`;
- `model_scoring_completed=false`;
- all model/GPU/training counts zero and all authorizations false.

The private payload is
`data/msae_independent_source_v10/private/blind_payload.jsonl`, mode `0600`, `nlink=1`, published
no-replace and never semantically reopened after publication. Public artifacts expose hashes, counts,
support, overlap, and provenance—not blind test content.

## Milestones

### M0 — prospective plan and carryover

- [ ] Carryover authority exact schema/maps/metadata reconstruct source-free.
- [ ] Independent plan review returns SHIP while V10 data/baseline/authority/acquisition paths are absent.

### M1 — source-free implementation

- [ ] Builder/runner/config/tests implement exact V9 scientific inheritance plus only the two
  scientific deltas and the explicitly enumerated source-free control-plane conformance repairs.
- [ ] Copied historical registry/screen are byte-identical to V9 and retain pre-v8 temporal scope.
- [ ] Pycompile, all V4–V10 source-free suites, AST equality, containment, capability, and publisher
  fault/recovery tests pass.
- [ ] Independent implementation review returns SHIP with no raw/private/quarantine/network/neural access.

### M2 — authority and acquisition

- [ ] Eligible full baseline and unchanged 2,116-entry training-root digest are published.
- [ ] No-replace authority manifest and independent authority review return SHIP.
- [ ] One-shot exact acquisition reaches canonical success or retained rejection.

### M3 — scientific gate and payload

- [ ] One-shot preparation reaches canonical B0, B1, or B2.
- [ ] Zero-work B0/B1 verifier reconstructs the exact terminal state; B2 verification performs the
  separately authorized deterministic model-free V10-raw reconstruction and byte-exact public checks.
- [ ] If B2, support/source-family/history/role gates precede payload and the replacement payload has
  mode `0600`, `nlink=1` with all scoring/training authorizations false.

### M4 — integration and reproducibility

- [ ] Independent terminal readiness/failure review returns SHIP.
- [ ] Paper, claim ledger, RESULTS, ANALYSIS, TODO, and RFC reflect V3 calibration-only status, V9/V10
  outcomes, August basis-selection/bridge-v2 evidence, and continued K2/training closure.
- [ ] Final tests, claim/citation checks, secret scan, explicit staging, and one consolidated commit pass.

## Definition of done

V10 is complete in exactly one of two states:

1. **Ready, not scored:** B2 seal and replacement payload reconstruct; narrow readiness claim only;
   no independent-replication claim; no model scoring/training; independent terminal review SHIP.
2. **Rejected:** first acquisition/scientific failure is retained canonically; V10 is non-retriable;
   zero-work terminal verification succeeds and independent terminal review returns SHIP.

If terminal verification or terminal review is BLOCK, V10 remains non-retriable but **incomplete**:
retain the evidence, do not mark M4 or Definition of Done complete, and require a new reviewed
successor.

Neither state authorizes K2 or branch training. Those remain closed until a separate prospective
prescore protocol passes independent review.

## Verification commands

Source-free only before M2:

```bash
PYTHONPYCACHEPREFIX=/tmp/msae-v10-pycache PYTHONDONTWRITEBYTECODE=1 \
  python -m py_compile scripts/prepare_msae_independent_source_v10.py \
  scripts/acquire_msae_independent_source_v10.py \
  tests/test_prepare_msae_independent_source_v10.py
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 PYTHONDONTWRITEBYTECODE=1 pytest -q -p no:cacheprovider \
  tests/test_prepare_msae_independent_source_v4.py \
  tests/test_prepare_msae_independent_source_v4_1.py \
  tests/test_prepare_msae_independent_source_v4_2.py \
  tests/test_prepare_msae_independent_source_v5.py \
  tests/test_prepare_msae_independent_source_v6.py \
  tests/test_prepare_msae_independent_source_v7.py \
  tests/test_prepare_msae_independent_source_v8.py \
  tests/test_prepare_msae_independent_source_v9.py \
  tests/test_prepare_msae_independent_source_v10.py
```

Baseline, authority, acquisition, prepare, terminal verify, and each independent review are separate
ordered commands. Never use `git add -A`; ignored research data and payloads remain unstaged.
