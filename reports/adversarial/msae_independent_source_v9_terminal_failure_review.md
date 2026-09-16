VERDICT: BLOCK
ONE-LINE: V9's B1 rejection is non-retriable, but its zero-work verifier rejects that valid state; a reviewed successor is required.

BLOCKERS        (must fix before proceeding; empty if none)
  - [critical] scripts/prepare_msae_independent_source_v9.py:3499-3503,3580 — B1 verification first reconstructs the old `scientific_entry` inventory against the current B1 filesystem.
    reasoning — `_verify_terminal_entry()` calls `_post_baseline_inventory(..., "scientific_entry")`; that state permits the entry but not later scientific-prefix or rejection finals (`scripts/prepare_msae_independent_source_v9.py:2696-2765`). The retained B1 state necessarily also contains `document_group_census.json` and `rejection.json`, so the current managed set has those two paths beyond the embedded entry-state set and deterministically raises `post_baseline_inventory_path_drift` before the B1-specific checks at lines 3581-3610. This exactly explains the reported zero-work verifier failure and is not a scientific-data failure.
    impact — The plan promises zero-work idempotent B1 verification (`docs/plan-msae-independent-source-v9.md:274-280`) and requires terminal verify plus independent review (`docs/plan-msae-independent-source-v9.md:470-480`). Those contracts are unmet even though the rejection artifact itself is structurally coherent. V9 therefore cannot be marked closed/SHIP under its frozen implementation.
    fix — Do not modify, delete, or rerun V9: its durable entry/rejection bind builder SHA `5714f714...` and make the attempt non-retriable. Create a new independently reviewed protocol that treats the embedded entry inventory as a historical snapshot while reconstructing the current B1 row, binds all frozen V9 artifacts and this review, and includes a regression with a one-or-more-item scientific prefix before any further source use. No K2, branch training, scoring, or V9 retry is authorized.

REVISIONS       (should fix; not blocking)
  - [medium] reports/provenance/msae_independent_source_v9/rejection.json:1 — the statement “no scientific prefix” is false for the retained state.
    reasoning — The rejection's `scientific_artifact_inventory` and B1 `post_baseline_inventory` both bind `document_group_census.json` as present, and the current canonical public file has SHA-256 `c2eac0867680bca5a7445a3c56341e978733767853a3c51bf8f7def9e6af361e`. The ordered prefix therefore contains exactly its first item; only later scientific artifacts are absent.
    impact — Calling this “no scientific prefix” misstates gate order and obscures why entry-state reconstruction fails.
    fix — Describe the result as “one-artifact scientific prefix: eligible document-group census; parser then rejected with `missing_or_unknown_field`; all later scientific artifacts and payload are absent.”

NITS            (optional, cap at 5)
  - None.

CHECKS RUN
  - `sha256sum` over the four terminal inputs -> exact matches: acquisition entry `f6489bc5a2813aa20fc0eb7d6257fb9fd97c78aab9ab69b688febdb503ad516a`; acquisition success `d353a5a04d8c853ea255526c20742a5e4c3578f672bc5d8cdd889cb193cff837`; scientific entry `0ccb9df33f63e06dfd610308793bc926aa2be2c4fd71b30d4cf83493d5ef2f05`; rejection `91c1e28f8f6f1e6efebef44875e4460848a5007360287787f715d8dea8a8896b`.
  - Independent canonical-public-JSON and binding reconstruction -> PASS: acquisition entry/success, scientific entry, document-group census, and rejection are canonical; plan/review/builder/runner/config/baseline/authority/acquisition hashes form an exact chain.
  - Acquisition public command reconstruction -> PASS: 11 recorded commands; clone, checkout, head, tree, ls-tree, both ignore checks, and four hash-object operations all exited 0; `hash_object_count=4`; every recorded stderr digest is the empty-byte SHA-256; resolved commit is `c434778d9511be5c35a6a11531f0107a960fb5d6`; tree path/blob maps contain exactly four names; `source_content_printed=false`; model/GPU/training counts are zero.
  - Acquisition custody by lstat only -> PASS: v9 data/raw directories are `0700`, commit directory is `0555`, and all four raw files are regular `0444`, link count 1, with sizes matching acquisition metadata. No raw file was opened or hashed.
  - Scratch-state lstat -> clone directory, empty HOME, and their acquisition scratch root are absent.
  - Scientific-entry evidence reconstruction -> PASS: durable entry SHA binds acquisition entry/success; `raw_file_open_count_before_entry=0`; history/training/process statuses are eligible; history additions/removals/changes are empty; forbidden process count and model/GPU/training counts are zero; all neural authorizations are false.
  - Rejection evidence reconstruction -> PASS as a retained B1 artifact: status `rejected_after_scientific_entry`, failure `missing_or_unknown_field`, raw open count 24, source content not reported, operation counts zero, neural authorizations false, and `next_action=new_reviewed_protocol_only`.
  - Public terminal cardinality reconstruction -> current finals are exactly scientific entry, `document_group_census.json`, and rejection; every named temp, every later scientific final, preflight rejection, seal, no-training gate, private directory, payload final, and payload temp is absent.
  - Baseline lstat recensus -> all 17,955 baseline paths remain present with unchanged regular-file type/device/inode/mode/link-count/size/mtime metadata; this includes all 2,116 training-root entries. No baseline content was opened in this terminal review.
  - Static verifier-path proof -> current B1 managed additions minus the entry's embedded `scientific_entry` additions are exactly `document_group_census.json` and `rejection.json`; `_verify_terminal_entry()` therefore reaches the exact observed `post_baseline_inventory_path_drift` before its caller enters the B1 branch.
  - No v8/v9 raw bytes, private payload, or Atlas quarantine content were opened, read, hashed, parsed, or printed. No network, acquisition, model, tokenizer, GPU, scoring, or training command was run.

CONTRACT COVERAGE
  - One-shot acquisition authenticity and custody -> met — public acquisition records bind the reviewed authority hash, runner/config, immutable commit/tree/four-file set, successful command surface, empty stderr digests, raw lstat custody, and removed scratch.
  - Durable scientific entry before source read -> met — `scientific_preparation_entry.json` binds zero pre-entry raw opens and the retained rejection binds 24 post-entry opens; implementation order is explicit at `scripts/prepare_msae_independent_source_v9.py:2915-2919`.
  - First scientific failure retained -> met within the frozen evidence boundary — `missing_or_unknown_field` is an explicit parser gate at `scripts/prepare_msae_independent_source_v9.py:692-753`; the B1 artifact is canonical and binds the durable entry, acquisition, one-item prefix, and all absent later states.
  - History/support/overlap before scoring -> met by non-reachability — parsing stopped before source-family, pedigree, dedup, history-overlap, support, payload, or any scoring/training authorization; none of those later artifacts exists.
  - Exact B1 terminal cardinality -> met — the current state matches the plan's entry + zero-or-more ordered prefix + rejection rule (`docs/plan-msae-independent-source-v9.md:221-228`), with the prefix equal to `[document_group_census.json]` and no temp/payload.
  - Zero neural operations/authorizations -> met — acquisition, entry, and rejection consistently record zero model/GPU/training operations and false scoring/K2/branch/Stage-C authorizations; no seal or readiness artifact exists.
  - Zero-work terminal reconstruction -> unmet — the verifier rejects its own valid B1 state before B1 validation because it compares a historical entry-state inventory with later B1 additions (`scripts/prepare_msae_independent_source_v9.py:3499-3503,3580`).
  - V9 non-retry and next action -> met — the durable scientific entry plus B1 rejection is a one-way terminal state; the artifact says `new_reviewed_protocol_only`, consistent with `docs/plan-msae-independent-source-v9.md:351-364,484-490`.
  - V9 Definition of Done -> unmet — the first scientific failure is retained and non-retriable, but the required successful terminal verification and SHIP failure review cannot be supplied under the defective frozen verifier.

UNKNOWNS
  - Because source access was prohibited, this review did not independently inspect which candidate field triggered `missing_or_unknown_field`; it verifies that the recorded code is a reachable frozen parser failure, not the semantic raw byte that caused it.
  - Raw SHA-256 and Git-blob claims were not recomputed; only public acquisition bindings and current lstat custody were checked.
  - The retained entry's point-in-time process snapshot and content-hash recensuses cannot be historically re-observed. Their canonical evidence is internally consistent; current baseline metadata is unchanged, but current content was not rehashed under the public-JSON/lstat-only review boundary.
  - The new protocol's form is intentionally not designed here. It must receive prospective plan and implementation review before consuming this frozen V9 state or accessing source; an in-place V9 patch/retry would invalidate bound hashes and violate the one-shot contract.
