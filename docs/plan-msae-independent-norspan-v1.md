# PLAN — NORSPAN-1 independent source, outcome-blind roles, and paper-completion launch

Date: 2026-09-16
Status: prospective; source bytes, labels, and outcomes have not been inspected
Owner: MSAE project

## Goal

Create a genuinely new architecture-confirmation source under the separately named
**NORSPAN-1** protocol, establish every source and leakage gate before model scoring,
seal a replacement blind payload, and then use a separately frozen scoring decision to
select exactly one G3 paper-completion branch.  Contained calibration/C1 scoring is the
sole pre-G3 GPU/tmux operation and requires its own prescore SHIP review.  Only after G3,
M5, and M6 may the applicable branch-training/final matrix be launched.

The sole source candidate is the independently maintained official Universal
Dependencies repository
`https://github.com/UniversalDependencies/UD_Norwegian-Bokmaal.git` at immutable
commit `396d11f0c2bd290a2a2711015c04ac25bc3dcc06`.  The only pre-plan access was
`git ls-remote ... HEAD`; no repository tree or source-content byte was opened.

## Non-goals and hard boundaries

- NORSPAN-1 does not repair, retry, or reinterpret V8, V9, or V10.
- AMALGUM v3 remains exposed-source calibration and is never independent replication.
- Atlas quarantine and all predecessor raw/private payloads remain unopened.
- No model, tokenizer, CUDA, GPU inventory, K2 restart, branch training, C1/C2 scoring,
  or final-test opening occurs before the exact state machine below authorizes it.
- Source-maintainer independence is not model-pretraining independence and does not
  establish researcher unawareness or general content independence.
- The private blind payload is never printed and is not semantically reopened after
  create-once publication except by the later signed scoring runner.
- An unfavorable gate or scientific outcome stops or narrows the program; thresholds,
  source, roles, records, or branch rules are not changed after exposure.

## Immutable dependencies and history scope

This plan binds the current G1/G2/G3, M5--M10, inference, final-test, and claim
rules in `TODO.md` at SHA-256
`42ebc8f4db324305f5481a25d5a7db16af163ce45bf4ead4da27ce5a1678e217`.
The implementation copies the complete applicable decision tables into a canonical
machine-readable config; the copied values and this digest must agree.  A later edit to
`TODO.md` cannot alter NORSPAN-1.

The V10 normalization/overlap reference is
`scripts/prepare_msae_independent_source_v10.py` at SHA-256
`637492e7ed4c1836704542deebe19b91ac38101bf6edf060fb4804868a45d088`.
NORSPAN-1's source-free implementation must literalize and test the referenced
normalization and overlap functions; it does not import or execute V10 against V10 data.

Before acquisition, the builder creates a complete current-history inventory of every
safely readable regular public file under the repository root.  It records path, mode,
nlink, size, SHA-256, adapter, and extracted-unit count.  Exclusions are exact:
`.git/`, `.cache/`, `.venv-atlas/`, `.pytest_cache/`, `.generated/`, checkpoints and
model binaries, every `private/` directory, the three Atlas quarantine paths, and V8--V10
raw/source roots.  Excluded paths receive lstat-only records and no content reads.
All other text/JSON/JSONL/CSV/TSV/Markdown/Python/config/log/archive inputs, including
post-V8 additions, are adapter-expanded into the overlap registry.  The temporal scope
is therefore **all policy-accessible current history frozen immediately before
acquisition**, not all bytes ever present.

V8--V10 raw/source/private bytes have no reviewed normalized-unit projection and are
policy-inaccessible.  NORSPAN-1 makes no content-overlap claim about them; it binds their
public source-identity/blob/hash records and reports this explicit coverage gap.  It may
claim full *accessible-history* screening only with that qualifier.  If any other
regular public file cannot be safely classified or read, the history gate fails.

The pre-source alias allowlist is a finite state-dependent path/hash table.  Its only
possible members are this plan; its plan reviews; the protocol config; acquisition and
preparation programs; tests; source-free verification log; implementation review;
`current_history_registry.json`; `baseline.json`; `authority.json`; authority review;
and `acquisition_entry.json`.  The baseline records absent future members.  Each later
record binds every predecessor hash; the final pre-network recensus freezes actual
path/hash entries and proves that these are the only post-baseline additions.  Candidate
aliases in any other path or adapter-expanded content reject source identity/use.
Inventory self-records use the literal state `self_canonical_final` and never hash their
own bytes.  There is no wildcard "planning" exemption.

The exact state rows are cumulative and no other public/protocol path is permitted:

| State | Newly permitted paths/state |
|---|---|
| `clean_reviewed` | plan, plan review, config, programs, tests, verification log, implementation review, and current-history registry; all hash-bound |
| `baseline` | `baseline.json=self_canonical_final`; every later row absent |
| `authority` | `authority.json=self_canonical_final` and exact hash-bound authority review |
| `acquisition_entered` | `acquisition_entry.json=self_canonical_final`; network/raw/source/private paths absent |
| `network_ready` | `pre_network_ready.json=self_canonical_final`; `network_started.json` absent |
| `network_started` | `network_started.json=self_canonical_final`; no acquisition terminal yet |
| `acquisition_terminal` | exact four raw finals plus `source_acquisition.json`, or `rejection.json`; no temp/extra path |
| `scientific_entered` | success acquisition plus `scientific_entry.json=self_canonical_final`; later markers/private objects absent |
| `raw_ready` | `pre_raw_ready.json=self_canonical_final`; `raw_access_started.json` absent |
| `raw_started` | `raw_access_started.json=self_canonical_final`; no scientific terminal yet |
| `scientific_terminal` | exact ordered public scientific prefix, four isolated private finals, `source_ready.json`, `no_training_gate.json`, and `seal.json`; or the first canonical `rejection.json`; no temp/extra path |

Every transition reconstructs the preceding row, adds exactly its named self-final, and
parent-fsyncs it.  The last check before the first subprocess or raw open must match the
`network_started` or `raw_started` row byte-for-byte.  Acquisition/scientific terminal
records replace no prior marker and bind all predecessor hashes.  Synthetic transitions
exercise every valid row and reject missing, reordered, extra, final-plus-temp, and
success-plus-rejection states.

Archive adapters accept magic-verified ZIP, uncompressed TAR, gzip-compressed TAR, or a
single gzip text member, with one expansion level only.  They reject nested archives,
duplicate/absolute/empty/`..`/backslash/NUL names, links, devices, encrypted members,
unknown compression, non-UTF-8 text, more than 10,000 members, any member over 64 MiB,
or more than 512 MiB decompressed total.  Unsupported or overbound public archives make
the history gate ineligible rather than silently omitted.

## Frozen source and acquisition state machine

Acquire exactly these paths, in this order, with a detached sparse clone:

1. `no_bokmaal-ud-train.conllu`
2. `no_bokmaal-ud-dev.conllu`
3. `no_bokmaal-ud-test.conllu`
4. `LICENSE.txt`

Exact namespaces are:

- config: `configs/msae_independent_norspan_v1/protocol.json`;
- raw: `data/msae_independent_norspan_v1/raw/<commit>/`;
- isolated private role objects:
  `data/msae_independent_norspan_v1/private/{discovery,calibration,c1,c2}/payload.jsonl`;
- public control records: `reports/provenance/msae_independent_norspan_v1/`;
- temporary files/directories: a `.<final-name>.building` sibling only.

Before network access, the builder must have an independently reviewed source-free
implementation, then publish `baseline.json`, `authority.json`, an independent
authority review, and durable `acquisition_entry.json`.  Before the first source-byte
read it publishes `scientific_entry.json`.  Each entry binds the plan/reviews,
code/config/test hashes, expected paths/schemas, pre-state inventory, process state,
and zero model/GPU/scoring/training counts.  It then publishes and parent-fsyncs
`pre_network_ready.json`, followed by `network_started.json` **before** the first
subprocess.  Scientific preparation analogously publishes `pre_raw_ready.json`, then
`raw_access_started.json` before the first raw open.  These create-once phase markers
make an initiated operation observable even if the process is killed immediately.

All ancestor walks use directory FDs and `O_NOFOLLOW`; files must be regular, mode
`0444` raw or `0600` private, `nlink=1`, and under pinned directory identities.  Every
publisher uses exclusive mode-0600 temp creation, complete writes, file fsync,
no-replace hard-link publication, temp unlink, and parent fsync.  The private root and
role directories are mode `0700`.  Symlinks, hardlinks, special files, unexpected
children, multiple finals, final-plus-temp, rejection-plus-success, or ancestor
exchange are invalid terminal states.

The acquisition record binds repository URL, commit, tree, Git blob IDs, SHA-256,
sizes, exact argv, minimal environment, exit status, and stdout/stderr digests.  It
publishes no source text.  A failed acquisition is terminal for NORSPAN-1.  Within the
same invocation, forward progress follows the fsynced phase markers.  After process
restart, entry plus `pre_network_ready` but no `network_started` may proceed; any
`network_started` without a complete acquisition is terminal unresolved and makes no
second network call.  Any partial raw final or `.building` object is terminal.  A
complete final is verified without reacquisition.  Scientific restart is identical:
`pre_raw_ready` without `raw_access_started` may proceed; `raw_access_started` without a
complete terminal state is unresolved and no raw byte is reopened.  A complete
four-object private root plus success seal may be verified without semantic private
reads.  Fault/kill tests cover every interval from entry through first phase marker,
first subprocess/raw open, temp-create, write, fsync, link, unlink, parent-fsync, and
terminal publication.

Exactly one terminal public state is valid: `rejection.json`, or the complete set
`source_ready.json`, `no_training_gate.json`, and `seal.json`.  A zero-work terminal
verifier reconstructs authority, ordering, file cardinality, modes/links, public
artifacts, process/training deltas, and terminal status.  Success reconstruction may
read NORSPAN raw bytes but never predecessor raw/private bytes; it compares private
objects only by independently reconstructed SHA-256, byte count, record count, mode,
and nlink.

`LICENSE.txt` must be strict UTF-8, nonempty, at most 131,072 bytes, and contain at
least one casefolded whole-token phrase `cc by-sa 4.0`, `creative commons attribution
sharealike 4.0`, or `attribution-sharealike 4.0 international`, or an exact URL in
`{http,https}://creativecommons.org/licenses/by-sa/4.0[/]`.  Tokenization is the pinned
Unicode lexical rule below; punctuation/hyphen separators are equivalent.  Any whole-
token `all rights reserved`, `no redistribution`, or `non-commercial use only`, or an
exact case-insensitive identifier in
`{GPL-2.0,GPL-3.0,AGPL-3.0,CC-BY-NC-4.0,CC-BY-ND-4.0,PROPRIETARY}` makes the license
ineligible.  Identifier candidates are maximal ASCII runs matching
`[A-Za-z][A-Za-z0-9]*(?:[.-][A-Za-z0-9]+)*` with non-ASCII-alphanumeric boundaries;
identifiers outside the enumerated contradictory set are neutral.  An accepted URL is
recognized only when the immediately preceding/following character is absent or not in
`ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789._~:/?#[]@!$&'()*+,;=%-`.
Zero accepted matches fails; one or more repetitions of the same accepted license pass;
any accepted-plus-contradictory mixture fails; contradictory-only fails.  Invalid
encoding or NUL fails.  The public artifact contains only the file digest, byte count,
matched accepted/contradictory phrase/identifier counts, and URL counts.

Literal goldens are: `CC BY-SA 4.0` -> eligible; the exact accepted HTTPS URL followed
by newline -> eligible; the accepted URL embedded between `x` characters -> no URL
match/ineligible; two accepted URL occurrences -> eligible; `CC BY-SA 4.0` plus
`GPL-3.0` -> ineligible; `GPL-3.0` alone -> ineligible; `MIT` alone -> ineligible;
`CC-BY-SA-4.0ish` -> no accepted identifier/ineligible; invalid UTF-8 and NUL ->
ineligible.  Split-chunk tests must reproduce the same results.

The one canonical source-family/pedigree rule scans both paths and adapter-expanded
content from the complete current public registry, excluding only the exact frozen
authority table above.  Candidate identifiers are derived only from the already public
URL, commit, and four filenames: token sequences `ud norwegian bokmaal`, `norwegian
bokmaal`, `no bokmaal`, the normalized repository URL with optional `.git`, the exact
40-hex commit, and each exact filename/stem.  Normalize with the pinned NFKC/casefold
lexical rule, serialize the token sequence with canonical JSON, and hash
`b"norspan-1/pedigree\0" || serialized_identifier`.  Any equality with a historical
path/content identifier is blocking.  Pathname/content occurrences, source-use versus
prospective-authority occurrences, and a planted matching-identifier stop golden are
reported separately.  This identity gate is distinct from later sentence-contamination
removal and must pass first.

## Outcome-blind source-role construction

NORSPAN-1 does not inherit upstream train/dev/test as experimental roles.  All three
files form one source pool.  Role assignment is computed without model calls or model
outcomes as follows:

1. Strictly parse CoNLL-U and preserve official partition only as provenance.
2. Require globally unique `(partition, sent_id)` identities and valid document-group
   metadata.  The exact accepted marker is `# newdoc id = ` at a sentence boundary;
   it must precede the first sentence, identify at least one sentence, be unique within
   its upstream partition after NFKC/casefold/strip, and contain no NUL/newline.  A
   missing, malformed, empty, duplicate, or orphan grouping is terminal.  There is no
   sentence-singleton fallback.  The typed `group_key` is the two-element JSON array
   `[upstream_partition, normalized_newdoc_id]`; it is never pre-serialized or inserted
   as a JSON string.
3. Normalize sentence lexical tokens using NFKC plus casefold and the V10 lexical-token
   rule.  Exact duplicate normalized sentences retain the lexicographically first
   `(partition, sent_id)` only.
4. Run the full accessible-current-history scan frozen immediately before acquisition,
   using the V10/pre-v8 registry plus every eligible post-V8 public input and the
   literalized structured-text adapters.  Record every blocking
   exact/short-containment/five-gram witness and remove every implicated candidate
   sentence **before role assignment**.  This is a contamination filter, not a passing
   result hidden by role selection.  Candidate-level collision counts remain public.
5. Apply deterministic internal overlap pruning before role assignment.  Visit remaining
   sentences by `(sha256(normalized lexical tokens), partition, sent_id)` and retain a
   sentence only if neither direction of the frozen V10 overlap predicate matches any
   earlier retained sentence.  Publish counts and ID digests, not text.
6. Drop groups left with zero sentences.  Canonical JSON is exactly
   `json.dumps(value,sort_keys=True,separators=(",",":"),ensure_ascii=False,allow_nan=False).encode("utf-8")`
   with no newline.  Compute
   `sha256(canonical_json(["norspan-1/role-v1", source_commit, group_key]))`; interpret
   digest bytes 0--7 as an unsigned big-endian integer `u`.  Assign discovery when
   `u < 11068046444225730969`, calibration when
   `u < 14757395258967641292`, C1 when
   `u < 16602069666338596454`, otherwise C2.  Whole groups stay in one role.
7. Re-run the complete cross-role overlap predicate.  Any witness is a terminal protocol
   failure; no record may be adaptively moved or removed after assignment.

This construction is outcome-blind but not a source-native random sample.  The paper
must disclose the history filter, overlap pruning, role ratios, and all removal counts.

The runtime is exactly CPython 3.12.3 with Unicode database 15.0.0.  NFKC and casefold
are applied in that order; document IDs strip ASCII space and tab only and reject any
remaining leading/trailing Unicode whitespace.  Lexical tokens use Python `re.UNICODE`
with the literal pattern `[^\W_]+` and maximal matches; alphabetic and punctuation
labels use that pinned Unicode database.  Source-free goldens bind normalization-
sensitive IDs, regex boundaries, the three integer cutpoints, and these role preimages:

- `['train','doc-0']` -> digest `16e0447098358da636236389dbe7f00a015bd3a39919ccdd579df1888b7344de`
  -> `1648392713998273958` -> discovery;
- `['train','doc-2']` -> `c1cfc78bbdcd68e0dcc4d80d0a30567559c4995250f42cc56861f1f12ddce013`
  -> `13965600372497934560` -> calibration;
- `['train','doc-7']` -> `e3adef2ce9f161f82467f2037cb514a6786249c6e9e4cda27e8e149fdbf6e28e`
  -> `16406031993763095032` -> C1;
- `['train','doc-20']` -> `fe379fa55a3e9847f70c9b18cc0eca7be681a65ec96b4d6c58a964f27c39ddbc`
  -> `18318285541885253703` -> C2.

## Pre-scoring gates and support

The exact order is:

1. acquisition custody and repository/tree/blob identity;
2. strict parse and source manifest;
3. license eligibility;
4. source-family absence and candidate pedigree;
5. exact deduplication;
6. exhaustive accessible-history overlap and removal;
7. deterministic internal-overlap pruning;
8. deterministic group-preserving role assignment;
9. zero cross-role overlap;
10. task support in discovery, calibration, C1, and C2;
11. deterministic payload construction and private create-once seal;
12. final no-training/process/porcelain recensus and independent readiness review.

The **required** tasks are `absolute_bucket`, `relative_quartile`, `capitalization`,
`word_length`, `punctuation`, `sentence_boundary`, `head_signed_distance`, and
`upos_coarse`.  The **optional** tasks are `dependency_depth`, `deprel_coarse`,
`number`, `token_identity`, and `lemma_identity`.

Ontologies are fixed as follows: absolute bucket `min(7,i-1)`; relative quartile
`min(3,4*(i-1)//n)`; capitalization in
`{nonalpha,lower,upper,title,mixed}`; NFC codepoint-length buckets
`{1,2,3_4,5_7,8p}`; Unicode-punctuation-only versus nonpunctuation; sentence boundary
in `{single,initial,final,interior}`; head distance in `ROOT` or signed
`L/R` crossed with `{1_2,3_4,5p}`; the frozen 17-value UD UPOS set; dependency depth
in `{0,1,2,3,4p}`; coarse DEPREL before `:` from the frozen UD inventory; UD Number;
and NFKC/casefold token or lemma identity.  Lemma `_` and missing Number are null and
excluded from that task only.  UPOS is exactly
`{ADJ,ADP,ADV,AUX,CCONJ,DET,INTJ,NOUN,NUM,PART,PRON,PROPN,PUNCT,SCONJ,SYM,VERB,X}`.
Coarse DEPREL is exactly
`{acl,advcl,advmod,amod,appos,aux,case,cc,ccomp,clf,compound,conj,cop,csubj,dep,det,discourse,dislocated,expl,fixed,flat,goeswith,iobj,list,mark,nmod,nsubj,nummod,obj,obl,orphan,parataxis,punct,reparandum,root,vocative,xcomp}`.
Number is exactly `{Sing,Plur,Dual,Trial,Pauc,Grpa,Grpl,Inv,Ptan}`.  Public identity
classes are `sha256(b"norspan-1/token\0" || value_utf8)` and
`sha256(b"norspan-1/lemma\0" || value_utf8)`.

For each `(role,task,class)`, support is the count of distinct retained sentence IDs
with at least one token in that class.  A class is retained at count `>=20`; a task is
eligible with at least two retained classes.  Each of all four roles must have all eight
required tasks plus at least two optional tasks eligible, and the reported all-role task
intersection is recomputed.  Any cross-language ontology value outside the frozen sets
fails parsing rather than changing the ontology.

Payload publication creates four isolated create-once custody objects.  Discovery,
calibration, and C1 may be mounted into the pre-G3 scorer; C2 is never opened, hashed,
or mounted there.  The C1 scoring launcher runs under `bwrap` with a read-only closure
and explicit bind mounts for exactly those three payloads, model/cache requirements,
and selected GPU devices; the repository root and C2 parent are absent.  The generated
`bwrap` argv uses `--unshare-all --die-with-parent --new-session --clearenv`, a fresh
`/proc`, tmpfs `/tmp`, no network or host IPC/socket mount, exact read-only closure,
model/cache and discovery/calibration/C1 mounts, one empty bounded writable run
directory, and only manifest-listed `/dev/nvidia*` nodes for the leased GPU plus its
required control nodes.  Environment is an allowlist containing locale, deterministic
flags, CUDA lease, and closure paths.  Synthetic negative tests must fail C2,
repository, network, host-path, and host-socket access.  An externally captured
`strace -f -yy` audit records paths/return codes with payload text redacted and passes
only if all successful opens fall in the exact mount/output allowlist and no C2 lookup
occurs.  M8 uses a separate signed C2 capability after all branch prerequisites.  Each
role object has an independent open counter and terminal technical-invalidity record.

The writable run directory is enforced with `prlimit` ceilings of 8 GiB per regular
file, 4,096 open files, and 512 processes, plus a supervisor that samples the no-follow
tree each second and terminates the namespace before accepting any result if total
regular-file bytes exceed 64 GiB or entry count exceeds 65,536.  The terminal verifier
independently applies the same ceilings; an over-limit synthetic writer must terminate
and may not yield a scientific artifact.

Public artifacts contain only hashes, counts, class hashes, manifests, removal
summaries, and provenance.

## Prospective scoring and G3 rule

Source readiness does not itself authorize scoring.  After a readiness SHIP review, a
separate immutable C1 scoring manifest and independent prescore SHIP review must bind
code, environment, model/checkpoint,
representation registry, task registry, metrics, resampling maps, case-study choices,
and this plan.  That review is the first point at which `nvidia-smi`, GPU allocation,
the contained scorer, or a scoring tmux session may run.  Calibration may select only
the registered numerical tolerance and primary simple baseline.  C1 is opened exactly
once for architecture confirmation; C2 is reserved for M8.

The frozen decision is deliberately conservative:

- A learned-model branch requires every hash-bound G1/G2 learned-superiority condition,
  at least two confirmable families, an explicit branch-to-family hypothesis, a reason
  the next-smaller K cannot represent the geometry, a capacity-matched comparison plan,
  and a falsifiable prediction for each added branch.  Valid finite inference and
  stability are mandatory.
- A simple/existing branch requires the primary simple baseline to satisfy every
  registered equivalence margin with valid inference and stability.
- A negative-atlas branch is available only when C1 is technically valid, every required
  endpoint has at least `450/500` scientifically finite refit draws, the null direction
  is stable under the registered resampling, no family passes G1, and simultaneous
  one-sided 95% upper bounds exclude the material selectivity margin `0.20` for every
  registered candidate.  Its signed plan must retain power/sensitivity reporting.
- Conflicting metrics, interval overlap with a decision boundary, fewer than the required
  finite draws, failed stability/specificity, or inadequate power retain
  `equivocal_no_decision`; they do not select the negative branch and authorize neither
  C2 nor training.

The G1 thresholds remain: broad-position recovery `>=0.75`, leakage `<=0.55`,
selectivity margin `>=0.20`, and upper one-sided 95% bound on split-family advantage
`<0.05`; split positional families require lower one-sided 95% bound `>=0.05` plus
unique advantage `>=0.05`.  The G2 learned-first precedence and margins remain:
selectivity `0.05`, assigned retention `0.02`, collateral `0.02`, stability `0.05`,
with reconstruction applicable only to common total-reconstruction definitions.
The canonical G3 output is one of
`learned_model`, `existing_or_simple`, `negative_atlas`, or
`equivocal_no_decision`, with every predicate and bound embedded.

Exactly one signed G3/M5 record names the branch and, using source-free fixtures plus
discovery/calibration/C1 technical eligibility only, freezes exactly one case-study enum:
`ioi` **or** `controlled_relation_position`.  It also freezes that case's technical-
invalidity rule.  C2 mounts and evaluates only the named case.  A C2 technical failure
is retained and cannot activate the other case; after any C2 opening there is no case-
study amendment or switch.  Selection precedence is fixed: choose `ioi` whenever it
passes every pre-C2 technical-eligibility check; choose `controlled_relation_position`
only when IOI is technically ineligible and the controlled case passes; if neither
passes, G3 remains `equivocal_no_decision` and C2 stays closed.

## Conditional tmux execution

The executable state order is:

`source_ready + readiness_SHIP -> C1_manifest + prescore_SHIP -> nvidia-smi/GPU lease
-> contained calibration/C1 tmux -> C1 terminal verification -> signed G3`.

After G3, every branch freezes M5.  Learned-model M5 includes architecture,
comparators, widths/sparsity/activation, seeds/data order, promotion thresholds, and
conditional M7e/M7f activation.  M6 implements and passes all hash-bound common and
learned-path tests before M7a.  Then:

- **Learned-model:** run and *complete* M7a engineering, M7b 25M, M7c 100M, and M7d
  1B in sequence, applying every frozen promotion stop before launching the next stage.
  Complete activated M7e scale extension and M7f warmdown; then freeze selected
  checkpoints, representations, code, configs, metrics, resampling, case study, and
  claim wording before M8.
- **Simple/existing or negative-atlas:** publish M7 `not_applicable`; launch only the
  branch-specific M6 validation, freeze the winning representation/fit/resampling,
  comparators, case study, and claim wording, then authorize M8.
- **Technical invalidity:** launch nothing beyond diagnostics explicitly allowed by the
  scoring manifest.

Only the M8 authorization may mount/open C2.  M8 then launches the complete
branch-specific functional, causal/sham, stability, robustness, and single frozen
case-study jobs.  M9 uses the registered independent unit, paired comparisons,
document-level resampling, 10,000 nested resamples where applicable, and training seed
outermost for learned results.  M10 integrates only the single pre-C2 frozen case study.
Technical invalidity is reported under its predeclared rule and never permits a second
case.

Every experiment runs in a named tmux session, under an immutable resolved config and
fresh run directory.  At each applicable scoring/training authorization (C1 prescore
SHIP or post-M6/M7/M8 authority), query `nvidia-smi`, choose only devices with no
compute process and adequate free memory, record UUID/index/memory, and set
`CUDA_VISIBLE_DEVICES` per session.  Launchers record Git SHA, config and payload
hashes, seeds, environment, hardware, PID, start time, progress counters, and an ETA
based on smoke/early throughput.
The current operator checks only that sessions, logs, heartbeat, throughput, and GPU
processes are healthy; it does not wait for completion.

## Milestones

### N0 — Prospective authority

- [ ] Plan stored mode `0644` before source-tree/content access.
- [ ] Independent plan review returns `SHIP`.
- [ ] Candidate alias/current-history registry, exact exclusions, and pre-source state
  are frozen.

### N1 — Source-free implementation

- [ ] Config-driven acquisition and preparation programs are implemented.
- [ ] Synthetic tests cover parsing, dedup, history filtering, deterministic roles,
  cross-role rejection, support, payload custody, and fail-closed ordering.
- [ ] Independent implementation review returns `SHIP` before acquisition.

### N2 — Acquisition and gates

- [ ] Exact source commit is acquired once.
- [ ] All 12 pre-scoring gates pass, or the first failure is retained terminally.
- [ ] A passing run creates four mode-0600, nlink-1 isolated role payloads and public
  no-training seal with zero model/GPU/training operations.
- [ ] Independent readiness review returns `SHIP`.

### N3 — Independent scoring and G3

- [ ] Freeze and independently review the prescore manifest.
- [ ] Run calibration and C1 once; verify finite inference and registered endpoints.
- [ ] Sign exactly one G3 branch, or retain technical `equivocal_no_decision`.
- [ ] Freeze exactly one technically eligible case study and its evaluation plan.

### N4 — Conditional experiments

- [ ] Query GPUs for C1 only after the C1 prescore SHIP review and record the lease.
- [ ] After G3, freeze M5 and pass M6 before any M7 launch.
- [ ] Complete each applicable M7 promotion gate before starting the next; otherwise
  publish M7-not-applicable.
- [ ] Freeze the branch, then open C2 once at M8 and launch branch-specific final jobs.
- [ ] Record per-session ETA and confirm healthy early progress without waiting.

### N5 — Release closure

- [ ] After jobs finish in a later session, freeze decision gate, evidence table,
  manuscript, and reproducibility bundle before any later-paper training.

## Definition of done

Scientific completion requires every checked item below.  A terminal source/acquisition
failure is valid operational closure but leaves the user's replacement-payload and
experiment-launch request explicitly **blocked/incomplete**.

- [ ] All safely readable current public history is inventoried and adapter-expanded;
  policy-protected gaps are exact and disclosed.
- [ ] License, repository identity, source family, pedigree, history overlap, internal
  overlap, group-preserving roles, cross-role separation, and support all pass.
- [ ] Four isolated payloads exist; C2 has not been opened or mounted before M8; the
  source-ready seal and independent readiness review are SHIP.
- [ ] Calibration/C1 run once under reviewed containment and yield a canonical valid G3
  branch, or canonical `equivocal_no_decision` with no later launch.
- [ ] The applicable M5/M6/M7 prerequisites complete in order before M8.
- [ ] C2 opens once under M8 authority and all branch-specific jobs launch in tmux with
  immutable configs, GPU evidence, ETAs, and observed healthy early progress.
- [ ] No failed or incomplete predecessor gate is bypassed, and monitoring/release
  handoff records the exact next commands.

## Alternatives considered

- Reusing V10 or changing its role assignment was rejected because V10 is terminal and
  the user explicitly requires a new protocol.
- Reusing AMALGUM was rejected because it is exposed-source calibration.
- Keeping upstream source splits was rejected because the V10 failure showed that source
  roles do not guarantee cross-role separation.
- Choosing roles after inspecting overlap outcomes was rejected as adaptive.  The
  history filter, internal pruning order, group hash, and role intervals are fixed here.
- Immediately restarting K2 was rejected because it would cross the independent/G3 gate.

## Risks and one-way doors

- Acquisition, payload publication, C1 opening, G3 signature, and C2 opening are
  one-way doors.  Each uses a new namespace and create-once record.
- Common short sentences may cause material deterministic pruning and reduce support.
- The source may fail strict parse or license gates; failure ends NORSPAN-1 rather than
  triggering an unreviewed fallback.
- Hash-role imbalance may make a role unsupported.  Intervals are not adjusted after
  source access.
- A passing source gate may still yield technical-invalidity C1; this never authorizes
  training or C2.

## Verification plan

- Source-free: `py_compile`, targeted pytest, capability/static scans, and deterministic
  synthetic replay.
- Source gates: independent reconstruction of repo/tree/blob/digests, role assignment,
  history/cross-role counts, support, payload digest/count/mode/nlink, and process state.
- Scoring: smoke run before C1, exact config/payload bindings, repeated no-op hash replay,
  finite-draw requirements, and independent claim review.
- Launch: tmux session/pane presence, process/GPU match, nonempty logs, heartbeat advance,
  and at least two progress observations before reporting healthy status.
