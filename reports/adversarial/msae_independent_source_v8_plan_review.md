VERDICT: SHIP
ONE-LINE: The amended plan closes both prior gaps and preserves the source-free gate before irreversible acquisition.

BLOCKERS        (must fix before proceeding; empty if none)
  - None.

REVISIONS       (should fix; not blocking)
  - None.

NITS            (optional, cap at 5)
  - None.

CHECKS RUN
  - `sha256sum docs/plan-msae-independent-source-v8.md` plus `stat` → exact reviewed SHA-256 `7aec70f8d6f384f2919f5f3086064b437dd34ff7731542aed2d7abe23ac5ae19`; regular one-link mode `0644`.
  - `sha256sum reports/provenance/msae_independent_source_v8/{preacquisition_alias_screen,historical_source_registry}.json` → exact frozen hashes `68a7536c95896087960dd4fc5882df85296baaa1a07aaf910e0e7c257b165e2f` and `ff4a36996f58531353dda9ed8fcbedb4c3a615f2d877e8b31f1462ddc8581a97`.
  - Python strict JSON/input-contract reconstruction over the public screen and registry → 16,133 unique Python-codepoint-sorted records; canonical digest independently recomputed as `8070a7cdd536a0dbd6104ff1dfb279ef01fb0acf98e969227625324155227564`; registry/screen bindings agree; recorded content/path/source-use/quarantine/model/GPU/training counts are all zero.
  - Python SHA-256 reconstruction of all 50 public predecessor-table rows → every path exists and every bound hash is exact.
  - Metadata-only lstat/existence checks for the v8 data/raw/private namespace, baseline, authority, acquisition entry/outcomes, builder, runner, tests, and config → all remain absent; no candidate or payload content was accessed.
  - `grep` of amended closure clauses → M1 directly enumerates the complete immediate-v7 chain at lines 560-563; the all-suite check includes v7 at line 611; candidate pedigree covers all four raw files and per-partition URL/`UD_*` fixtures at lines 346-360.
  - `git diff --check -- docs/plan-msae-independent-source-v8.md` → clean.
  - `.agent-workspace/bin/check-plan` / `bin/check-plan` availability check → no plan-check backend exists in this repository, so no automated plan-gate result was available.

CONTRACT COVERAGE
  - Prospectively fixed, previously unused candidate without pre-acquisition source access → met — exact official repo/commit and the single metadata-only discovery operation are bound at docs/plan-msae-independent-source-v8.md:136-165; the v8 source namespace is absent.
  - Complete accessible-history binding → met prospectively — the exact 16,133-record array and digest must reconstruct at baseline, authority, acquisition preflight, prepare, outcome verification, and seal at docs/plan-msae-independent-source-v8.md:169-208.
  - Direct predecessor and immediate-v7 closure → met — all 50 predecessor rows hash exactly, every row is mandatory at lines 77-79, the full v7 chain is explicit at lines 560-563, and v7 is included in the all-suite command at line 611.
  - Source-family and pedigree separation → met — history extraction is exhaustive under the frozen grammar at lines 306-344; candidate extraction applies the same grammar to all four raw files, including all three CoNLL-U partitions, with stop-before-later-gates fixtures at lines 346-362.
  - Exact four-file tree and LICENSE-only eligibility → met — repo/commit/path identities, Git-blob checks, source-output prohibition, exact license grammar, contradiction rules, and terminal no-fallback behavior are fixed at lines 217-239 and 364-388.
  - Grouping, deduplication, role overlap, and support → met — explicit-newdoc/fallback semantics, cross-partition exclusion, group-preserving C1/C2 assignment, bidirectional overlap, and support floors are deterministic at lines 400-441.
  - Full history overlap before scoring → met — all retained roles are checked against every scanned history unit with symmetric rules before support and payload at lines 443-462 and in the literal gate order at lines 294-304.
  - One-shot custody, cardinality, and publisher recovery → met — durable entry, mutually exclusive canonical finals, zero-subprocess idempotence, case-(c) obstruction, and state-based full-final recovery are coherent at lines 241-290 and 488-528.
  - Capability closure and K2/branch stop → met — network/process capability is runner-only, builder process APIs are closed, point snapshots and training-root deltas are bounded honestly, and every scoring/training authorization remains false at lines 530-549 and 625-632.
  - V8 M1/M2/M3 and definition of done → met prospectively — source-free reviews and authority precede acquisition; the literal 15 scientific gates precede any payload; success or first retained failure ends v8 without authorizing scoring or training at lines 553-632.

UNKNOWNS
  - Candidate tree contents, raw hashes, license evidence, document-marker branch, dedup counts, task support, overlap results, and payload feasibility remain intentionally unknown until the reviewed one-shot acquisition and ordered scientific gates.
  - Full current-worktree equality to the frozen 16,133-record history registry remains for the future create-once baseline and independent authority review to establish.
