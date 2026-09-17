VERDICT: BLOCK
ONE-LINE: Local preservation and literal-gate counterexamples are fixed; whole-protocol history, custody, and terminal authority remain blocked.

BLOCKERS
  - [critical, carried forward] scripts/acquire_msae_independent_norspan_v1.py:45-77; scripts/prepare_msae_independent_norspan_v1.py:2029-2057 — exact current-history recensus remains absent.
    reasoning — this bounded change does not add the complete state-relative path/hash recensus identified in the preserved implementation review at lines 9-12. The runner still binds the registry file's hash rather than reenumerating its historical universe before network, and the registry validator still iterates saved rows only. Ignored public additions outside training roots remain undetected.
    impact — the frozen pre-acquisition history/source-family authority is not satisfied. The full implementation BLOCK is not superseded by 99 passing local tests.
    fix — retain NOT READY/no-acquisition status. A later reviewed correction must implement and test the exact baseline-plus-state-additions recensus at the one-way boundaries before seeking whole-implementation SHIP.
  - [critical, carried forward] scripts/prepare_msae_independent_norspan_v1.py:1285-1294,2230,2444-2489; reports/adversarial/msae_independent_norspan_v1_implementation_review.md:17-20,29-36 — residual descriptor, authority, terminal, and fault/restart blockers remain outside this correction.
    reasoning — the initial public directory is still created/chmodded by pathname; raw enumeration remains independently pathname-based. Acquisition rejection verification still compares retained evidence to retained baseline evidence without fresh process/training/porcelain recensus or full authority/review/schema reconstruction. The expanded tests add bounded publisher write-failure checks, not actual prepare/verify replay or the complete marker/publisher fault matrix. Config and runner are unchanged.
    impact — no history/acquisition/raw/scoring/training/launch authorization follows from this bounded review. The user’s independent replacement-payload and experimental-launch outcomes remain incomplete.
    fix — preserve the prior BLOCK report as binding. Close those requirements in a separately bounded, prospectively reviewed implementation and obtain a new full independent verdict before any one-shot gate.
  - [high, carried forward] scripts/prepare_msae_independent_norspan_v1.py:1960-1978 — the private publisher still exception-cleans partial objects without an exact owned-inode ledger.
    reasoning — the bounded preservation changes affect `publish_bytes` and `publish_flat_directory`; `publish_private_roles` retains its exception handler that enumerates/unlinks child objects and removes role/private directories. Its comment claims identity-bound cleanup but it does not prove each deleted object is an owned current-invocation inode or bind the final named directory before rmdir.
    impact — the local result must not be represented as preservation/recovery closure for all publishers or blind-payload custody. Private publication and the overall publisher fault matrix remain unapproved.
    fix — in a later reviewed custody correction, preserve partial private publication as unresolved or implement the exact separately authorized owned-object cleanup protocol, with exchange and interruption tests. Do not create a real private payload now.

REVISIONS
  - [medium] scripts/prepare_msae_independent_norspan_v1.py:1203,1215-1218 — the UTF-8 prefix probe can falsely reject valid public text.
    reasoning — `read_prefix_nofollow(...,65536)` is decoded as a complete UTF-8 string. A synthetic `valid-utf8.dat` with 65,535 ASCII bytes followed by UTF-8 `é` is valid in full but its prefix ends midway through the codepoint; classification raised `unclassifiable_history_binary`. The previous implementation also mishandled this boundary, but the successor now turns that misclassification into a false terminal failure rather than silent omission.
    impact — this is safe fail-closed behavior, not a new unsafe bypass, but can prevent an otherwise readable public-history inventory from completing.
    fix — use an incremental UTF-8 decoder for non-final prefix classification, retaining an incomplete final codepoint until the full adapter read; fail on genuinely invalid bytes. Add just-below/at/above-probe multibyte and late-invalid-byte regressions.

NITS
  - None.

CHECKS RUN
  - Exact current input hashes/modes: builder ac342ddbf93a2dceeab5a96dc8e276eabed1375a7b6e28060f8ae2a5d8b69a54 (0755); tests 134aa964f616edaaf747f3a2c7cc38b217db51e913ea67c1bc4bbdc7f1d86b8c (0644); unchanged runner 447856a730cda54ef37898059bb11655ca38dbd0fe0043593a56fe39034155cc (0755); unchanged config 21964577964c15087ac0b4eee96dbc2ae3e7e5dcdc0442aa10c205de674c300c (0644).
  - Prior reviewed candidate: builder 3dd33ff0ce5f05768af19b252c397cb00d21910011aef066a6b60730f03bd91b; tests 36b887eb841b3020601f64f4e73b92ba4b02a2f7302542deacb51cbf5560ee99. Preserved prior implementation BLOCK report SHA-256 3cc1f07361beb0a3f4d7523df1636de3bb4de5871f02c2b1950412be137bf6f6 (0644), checked before/after this review and not modified.
  - Unchanged governing plan 7e063dcac878623c7f1f293b77294e4c3d006d839d8df184f6814157fe17d7c9; SHIP plan review f6a24f10d1a95c1687a81f5cd472c56c0c7ea119b671c558582955c8972d24dc. These are prospective plan evidence, not whole-implementation approval.
  - Current regenerated public verification log e5c40fb831fdbd29734ff3b2fb3b443e30c8f4bff7023bfddd34212ab27d6412 -> exact current code/test bindings, explicit BLOCK/NOT READY, prior-candidate distinction, incomplete full-control-plane coverage, and red/NFS-failure/final-green dispositions are recorded. Its report of 99 passed in 1.31s and isolated predecessor 167 passed in 16.38s is retained evidence; I did not rerun the predecessor suite or reproduce the historical NFS failure. The log records prior log SHA-256 5a77576f170159268de068073c9b5d93a779365f194cb54c0f760a7c0d2b2b80 as preserved.
  - `PYTHONDONTWRITEBYTECODE=1 pytest -q -p no:cacheprovider tests/test_prepare_msae_independent_norspan_v1.py` -> 99 passed in 1.38s against frozen ac342dd.../134aa964...; hashes unchanged afterward.
  - Bounded synthetic gate replay -> fullwidth-punctuation URL ineligible; `garbage-range` rejected with `malformed_conllu_row_id`; mid-sentence marker rejected with `document_group_mid_sentence`.
  - Bounded synthetic UTF-8 probe replay -> full text validates as UTF-8, but classification raises `unclassifiable_history_binary` when its final probe codepoint is incomplete.
  - Source-free suite preservation checks -> pre-existing public temp/final directory and their inodes/content survive create-once rejection; injected public/flat write failures leave interruption evidence rather than deleting it. Canonical MWT and empty-node positive fixtures pass.
  - Scope audit -> only public control/code/config/test/review/log reads, the NORSPAN source-free suite, and bounded temporary synthetic gate checks were performed. No real history census/baseline/authority/acquisition/prepare/terminal verification, candidate/provenance namespace access, V8/V9/V10 raw/source/private byte open/hash/parse/print, Atlas quarantine/private access, network, GPU inventory, model/tokenizer, scoring/training/K2/branch, or tmux command occurred.

CONTRACT COVERAGE
  - Bounded public/flat publisher preservation -> met locally — old deletion counterexamples are fixed; pre-existing objects are untouched on rejection and partial writes remain observable/unresolved (builder lines 284-334,608-648; tests lines 608-652). This does not approve private cleanup, ancestor exchange, or every publication interval.
  - Unknown non-model binary fail-closed policy -> met locally — NUL/non-UTF-8 unknown files raise instead of becoming silent exclusions; full text adapters reject NUL. UTF-8 probe false-positive remains a revision, not a safety bypass.
  - Literal license URLs -> met locally — matching uses original decoded text and original-character boundaries (lines 1585-1641); fullwidth and uppercase nonliteral URL negatives and approved original goldens pass.
  - Canonical row IDs/basic skipped-row consistency and boundary grouping -> met locally — original malformed-ID and manufactured-boundary failures are fixed; range/node checks and canonical MWT/node positive fixtures pass (lines 1398-1504). This is not exhaustive CoNLL-U conformance or evidence about the actual candidate.
  - Directory descriptor object identity amendment -> met in its bounded `_descriptor_tree` scope — root/child opens compare device/inode/type/mode, not mutable directory nlink/size (lines 665-705); census records still retain metadata. No real NFS/history validation was performed.
  - Prior entire implementation review -> partial, not superseded — local counterexamples are closed as above; exact history recensus, residual public/raw custody, private cleanup/opaque streaming, authority/terminal schemas/evidence, recovery, bounded Git IO, and full fault/prepare/verify coverage remain unclosed.
  - Honest verification and claim boundary -> met for this follow-up — current log calls the program BLOCK/NOT READY and bounds its evidence; prior full BLOCK report is unchanged. No independent replication, model result, replacement payload, G3 branch, or scientific launch result is claimed.
  - Whole-protocol/source acquisition/model/GPU/scoring/training/tmux authorization -> unmet and intentionally withheld — first-line BLOCK is binding; no real one-way gate or launch is permitted by this bounded review.

UNKNOWNS
  - Actual candidate tree/content, license, groups, overlap, support, and attainable blind-payload role counts remain intentionally uninspected.
  - Candidate/provenance namespace absence is supplied-log evidence only; this review did not access those namespaces to independently verify it.
  - Historical red results and the NFS directory metadata diagnosis were read as recorded dispositions, not recreated or accepted as independent scientific evidence.
  - No new unsafe regression was found in the inspected bounded public-preservation/binary/license/parser subset; this is not a fresh whole-protocol safety audit or a guarantee about unreviewed branches.
  - Current process/training eligibility and all later prescore/containment/G3/C1/C2/M5-M10 prerequisites remain unqueried and unauthorized.
