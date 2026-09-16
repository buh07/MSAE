VERDICT: SHIP
ONE-LINE: The corrected v6 contract closes both predecessor defects while preserving the source-free, no-training gate sequence.

BLOCKERS        (must fix before proceeding; empty if none)

REVISIONS       (should fix; not blocking)

NITS            (optional, cap at 5)
  - docs/plan-msae-independent-source-v6.md:39-42 — “both” introduces three comparison sites; use “baseline production, builder authority reconstruction, and acquisition-runner terminal reconstruction all...” when next editing prose.
  - docs/plan-msae-independent-source-v6.md:88-90 — the exhaustive authority list contains two successive “; and” joins; this is grammatically awkward but the literal paths remain unambiguous.

CHECKS RUN
  - `sha256sum` over the reviewed prospective inputs → plan `0bba4efcfea868b186f4051faa71d84382b33a8b1f8dc425ed595c7335b515cc`; inherited alias screen `c0c17ed89e19b3af611bae43e73095ca4acb4d0a61a01f7c3ef8979cbe2fbd7d`; inherited pedigree registry `484a2b8c13798924c159d0e1bf7fbc90d19010111f89b08e7ddb7ceb6780b83f` — all requested hashes matched.
  - `cmp` of the v5/v6 screen and registry pairs → both v6 public inputs remain byte-identical to their frozen, never-entered v5 predecessors.
  - Independent canonical-JSON recomputation of the literal two-entry v6 split-manifest golden → `3113f18eec64ba9aa0f8a47bd8d2cb8d55229f531d59d8b2a30053546427a1eb`, exactly matching docs/plan-msae-independent-source-v6.md:302-304.
  - Source-free case-insensitive alias-path census over public non-generated text while pruning `data/**` → before v6 authority files, the only post-screen matches remain exactly the seven frozen v5 predecessor paths at docs/plan-msae-independent-source-v6.md:65-76; the only older matches remain the five planning occurrences in three files.
  - `sha256sum` over the v4/v4.1/v4.2 rejection chain and v5 plan/builder/runner/test/config/baseline/rejection/rejection-review chain → every digest quoted or required by docs/plan-msae-independent-source-v6.md:22-42,65-76,370-386 matched.
  - Direct `lstat`-only checks → v6 baseline/temporary, authority manifest/temporary/review, acquisition entry/success/rejection, complete v6 raw/private namespace, payload, and payload temporary are absent. The prospective builder, runner, tests, config, source-free transcript, and implementation review are also absent.

CONTRACT COVERAGE
  - Prior split-golden blocker → met — docs/plan-msae-independent-source-v6.md:295-304 now binds the v6 schema and independently recomputed v6 digest rather than the incompatible v5 digest.
  - Prior global-order blocker → met prospectively — docs/plan-msae-independent-source-v6.md:28-42 now requires complete global path sorting at baseline production, builder authority reconstruction, and acquisition-runner terminal reconstruction; lines 370-375 require distinct builder and runner regressions whose depth-first and lexical orders differ.
  - Scientific-independence claim boundary → met prospectively — docs/plan-msae-independent-source-v6.md:44-76 limits the claim to previously considered but project source use unseen, disclaims name novelty/document/pretraining independence, and binds the independently reviewed v5 no-acquisition evidence.
  - Exact candidate-bearing v5 authority exclusions → met — docs/plan-msae-independent-source-v6.md:65-76,78-116 individually hash-binds the exact seven source-free v5 alias-bearing files as authority; the public alias census found no omitted post-screen candidate-bearing history file.
  - Complete history, source-family, overlap, support, and no-scoring order → met prospectively — docs/plan-msae-independent-source-v6.md:78-116,186-291 includes prior ATIS raw and all non-authority post-v4 work, freezes pedigree/dedup/cross-role/full-history checks, and completes overlap and support before payload while scoring remains unauthorized.
  - Immutable control-plane sequence → met — docs/plan-msae-independent-source-v6.md:368-386 requires plan review, source-free implementation and tests, exact-hash implementation review, create-once current baseline, authority manifest, and independent authority review before the acquisition hash can be supplied.
  - Acquisition and payload custody/terminal states → met prospectively — docs/plan-msae-independent-source-v6.md:118-184,293-343 preserves durable entry-before-subprocess, exact cardinality, no-replace publication, explicit case-(c), bounded metadata-only failure evidence, and opaque one-link `0600` payload custody.
  - Capability barriers and K2/scoring stop → met prospectively — docs/plan-msae-independent-source-v6.md:126-140,345-364,423-435 confines network/process capability to the separately reviewed runner, freezes no-process builder closure and narrow snapshot claims, and leaves model scoring, K2/branch training, and Stage C unauthorized.
  - V6-M1/M2/M3 and Definition of Done → met prospectively — docs/plan-msae-independent-source-v6.md:368-435 makes implementation review, immutable authority, first-failure retention or reconstructing payload success, provenance review, exact terminal evidence, and continued no-training authorization explicit.
  - Prospective absence gate → met — every requested v6 raw/private/baseline/authority final and temporary remains absent; no source or payload path has been entered.
  - Review restrictions → met — no network, acquisition, baseline, authority, prepare, verify, source/raw/private/quarantine content read, or model/GPU/scoring/training command was used.

UNKNOWNS
  - Candidate source bytes, upstream availability, actual parser/license/source-family/dedup/history/support outcomes, and payload publication remain intentionally untested one-way gates.
  - The v6 implementation does not yet exist; its global-sort helper coverage, custody, capability closure, exact predecessor bindings, and tests require the separately mandated source-free implementation review before baseline creation.
