VERDICT: SHIP

ONE-LINE: V9 now has a coherent source-free authority, one-shot acquisition, scientific-entry, and terminal reconstruction protocol.

BLOCKERS:
  - None.

REVISIONS:
  - None.

NITS:
  - `docs/plan-msae-independent-source-v9.md:228-233` — implementation should literalize the exact key/type variants for directory, deferred-raw, verified-raw, and payload inventory records in constants and goldens; the plan's required evidence and read policy are nevertheless sufficient to constrain behavior.
  - `docs/plan-msae-independent-source-v9.md:289-312` — implementation should treat failure to obtain the inherited process snapshot as pre-entry C rather than attempting B0 without the required canonical snapshot object.
  - `docs/plan-msae-independent-source-v9.md:399` — remove the redundant comma/conjunction before `candidate_pedigree`.

CHECKS RUN:
  - `sha256sum`/`stat` -> reviewed plan SHA-256 `0607886af9561d8418fd7a153322e6b59cd47404f33174c49b07bec5284cd57e`, mode `0644`, one link; carryover authority SHA-256 `00d7cdca4e9893ef1f4e36b6104caf21991ce1ca92e9897d3c5a72d497212f47`, mode `0644`, one link.
  - Strict public/opaque carryover reconstruction -> all 17 current control records, 50 current predecessor hashes, and four opaque retained-v8 raw lstat/SHA records match; control, predecessor, and raw map digests remain `ecfdffb24efac47c4f8b7e7e2435759d10f2f652f60ebc48962c7148f7985f3d`, `1dc8b1f85e6deb20edb63ec86da06e6cda64dca342223ed0d6d3fc9af7169a53`, and `822d7d795020101b1554d5a25d87c229d1bd6cdf1926a42f3dfbf3f230b58e0e`.
  - Metadata-only v9 state check -> all 13 checked v9 data, registry/screen, baseline/authority, acquisition, scientific-entry/outcome, seal/no-training paths are absent; carryover authority is the sole pre-review v9 provenance input.
  - Read-only acquisition state trace against `scripts/acquire_msae_independent_source_v8.py:395-410`, `scripts/acquire_msae_independent_source_v8.py:496-509`, and `scripts/acquire_msae_independent_source_v8.py:881-902` -> the amended acquisition-rejected row now permits exactly either absent data or the inherited rejection's `raw_namespace_exists` plus ordered `partial_raw_metadata`, lstat-only and without cleanup/content/hash reads.
  - Read-only scientific state trace -> pre-entry current raw hashing remains deferred; entry embeds the full eligible process evidence and `scientific_entry` inventory state; B0/B1 schemas are distinct and reconstructible; linked canonical seal recovers only B2 and cannot coexist with rejection.
  - No network, acquisition, baseline, prepare, model, tokenizer, GPU, scoring, training, K2, branch, or Stage-C command was run. No semantic v8 raw, private payload, or Atlas quarantine content was opened.

CONTRACT COVERAGE:
  - Genuine source-maintainer/non-ATIS independence boundary -> met prospectively — the candidate is an official independently maintained non-project repository, while researcher-awareness, pretraining, global-content-absence, general-separation, scoring, and replication claims are explicitly disallowed.
  - Complete pre-v8 history/carryover authority -> met — finite 17-file control and four-file opaque-data exclusions, 50 predecessors, canonical map digests, and exact quarantine treatment are frozen and fail closed.
  - History support/overlap before scoring -> met prospectively — baseline text history is immutable, post-baseline candidate metadata never enters history, history overlap/support precede payload readiness, and this plan authorizes no scoring.
  - One-shot acquisition/custody -> met prospectively — authority review gates the first subprocess; success, absent-data rejection, partial-data rejection, and invalid state are mutually reconstructible without cleanup/retry.
  - Scientific entry before raw read -> met prospectively — pre-entry inspection is lstat/public-metadata only, current raw SHA is unclaimed until the durable entry, and gate 1 performs the first raw reconstruction.
  - A/B0/B1/B2/C terminal behavior -> met prospectively — exact entry/outcome evidence, temp handling, state-based publisher recovery, and seal/rejection exclusivity are coherent.
  - License/source-family/pedigree/dedup/overlap/support/payload order -> met prospectively — inherited exact scientific functions and the fourteen-step order put every eligibility gate before terminal readiness.
  - Capability/no-neural/K2/branch-training closure -> met prospectively — only the runner may use network/subprocess; model/tokenizer/GPU/scoring/training operations and authorizations remain false.
  - M1/M2/M3 and Definition of Done -> met prospectively — each one-way door has a prior independent review, a canonical success/rejection or explicit C state, and a terminal independent review before any later scoring protocol.

UNKNOWNS:
  - No v9 registry, alias screen, implementation, tests, baseline, authority manifest, acquisition, scientific artifacts, or payload exists; each requires its separately ordered independent review.
  - Candidate license, source family, pedigree, grouping, dedup/overlap loss, support, split counts, and payload feasibility remain unknown until the frozen gates run.
  - SHIP authorizes source-free implementation only. It does not authorize network acquisition, source reading, model scoring, K2, or branch training before the later authority gates.
