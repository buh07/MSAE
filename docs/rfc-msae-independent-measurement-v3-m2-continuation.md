# MSAE v3 post-M1 continuation: authenticated and recoverable M2

## Status and scope

M1 completed successfully under base-builder SHA-256
`2d08f380998c796852b19ed2214ec77c212948fb9d1758674ea1b9895dd032bd`
and M0 completion SHA-256
`d370bb8eea01ba2cdbd1c5868a73f56f8e8a9425f3b0cc06af01e8e39181dce0`.
Those bytes and all five M1 artifacts are immutable. The first CPU-only M2
attempt stopped before writing any M2 artifact when the strict parser found
legacy values in selected AMALGUM UPOS columns. It made no model call, GPU
query, GPU job, or tmux session.

This document is prospective for the repaired M2 attempt. It changes no
overlap, source, threshold, task, support, map, or scoring rule. AMALGUM remains
an exposed-source technical replication, not a pristine confirmation source.

## Independently reviewed successful-M1 pin

Before M2, the immutable controller creates
`reports/provenance/msae_independent_measurement_v3/m1_completion_manifest.json`.
The manifest binds canonical path, regular-file type, mode, size, and SHA-256
for all five M1 artifacts; the exact base-builder and M0-completion digests; and
these success assertions:

- 350 selected aliases;
- 40 eligible overlap fixtures;
- 23,658 historical documents, 8,297 candidate pairs, and 24,008 IDF-universe
  documents;
- `history_overlap.status=eligible`, zero blocking collisions, and zero sealed
  payload content reads; and
- all 206 visible v1 rows remain preserved with their historical ineligible
  status.

Construction and every verification rerun the complete M0 verifier at the M1
projection, including protected v1/v2 and lstat-only quarantine checks. An
independent reviewer must report SHIP and freeze the exact completion-manifest
SHA-256. M2 accepts that digest as an explicit CLI argument and checks exact
canonical bytes and semantics before computing and again before installation.

## AMALGUM-only legacy-UPOS correction

The repair applies only when `source_genre` begins with literal `AMALGUM:`.
Unknown tags in historical discovery/calibration or any other source remain
strict errors in the base builder.

1. A registered UD UPOS is unchanged.
2. Only raw tags `''`, `.`, and ```` are candidates.
3. Two exact lexical corrections precede the Unicode rule:
   - raw `''`, FORM `'d`, LEMMA `will`, DEPREL `xcomp` -> `AUX`;
   - raw ```` , FORM `’`, LEMMA `'s`, DEPREL `case` -> `PART`.
4. Otherwise, every non-space FORM code point having Unicode general-category
   prefix `P` maps to `PUNCT`; every prefix `S` maps to `SYM`.
5. Empty, other lexical, mixed-category, or any other unknown-tag case blocks.

The controller freezes three distinct provenance populations rather than
conflating them:

| population | denominator | corrected | exact transition counts |
|---|---:|---:|---|
| raw selected integer-token rows | 290,192 | 36 | `''->AUX` 1; `''->PUNCT` 18; `.->PUNCT` 11; ````->PART` 1; ````->PUNCT` 4; ````->SYM` 1 |
| rows in tokenizer-accepted sentences | 286,938 | 20 | `''->AUX` 1; `''->PUNCT` 7; `.->PUNCT` 6; ````->PART` 1; ````->PUNCT` 4; ````->SYM` 1 |
| rows retained after the 256/document cap | 89,600 | 11 | `''->AUX` 1; `''->PUNCT` 3; `.->PUNCT` 3; ````->PART` 1; ````->PUNCT` 3 |

Each correction entry records role, selected-relative path, sentence ID,
zero-based word index, final base-row ID, FORM, LEMMA, DEPREL, raw UPOS, and
corrected UPOS. Each population records its population-row-ID-set digest,
correction-entry digest, denominator, and exact transition counts. The retained
ledger is checked as a subset of the actual C1/C2 rows used to construct
support and maps. The complete audit and its digest are embedded in
`task_manifest.json`.

## Recoverable M2 construction

All seven M2 outputs (`label_rows.jsonl`, task/support/template JSON, maps,
finite-pass matrix, and protocol imports) are first computed in a newly absent
temporary tree outside the repository. During this computation the real M1
projection has already been authenticated; the temporary projection must
contain exactly the seven regular mode-0644 files before any repository write.

After a second successful-M1 authentication, a create-once mode-0700
`.m2_install_transaction` stages the exact seven payloads at mode 0600 plus a
canonical digest descriptor. Targets are installed with `O_EXCL`, mode 0644,
fsync, and byte/hash verification. The transaction permits deterministic
recovery from interruption at every target boundary, rejects undeclared staged
entries, and rejects any partial target set without its transaction. A fully
installed matching set is idempotent; drift blocks.

## Immutable controller and later closure

`scripts/msae_independent_measurement_v3_post_m1.py` is the mandatory entrypoint
for M2 and every later phase. The create-once M2 task manifest binds canonical
entries for that controller, this RFC, its dedicated test, and the reviewed M1
completion manifest. These bytes become immutable after M2.

Later implementation lives in
`scripts/msae_independent_measurement_v3_post_m1_runtime.py`. Every later
dependency closure must call the immutable controller's
`extend_closure_payload`, passing the current runtime and every further local
dependency. The placeholder runtime always blocks. No authorization, model
call, GPU query/job, or tmux launch is allowed until the complete post-M1
runtime, Stage A, closure, authorization and launch failure paths receive a
fresh prescore adversarial SHIP verdict.
