VERDICT: REVISE
ONE-LINE: Endpoint-local disjoint pairs fix the collapse, but matching and joint resampling safeguards must be frozen first.

BLOCKERS        (must fix before proceeding; empty if none)

REVISIONS       (should fix; not blocking)
  - [high] scripts/atlas_discovery_v3.py:1302-1326,1415-1498 — current builders cap donor reuse but allow a donor document to become a later target, creating chains.
    reasoning — the proposed two-document components are sound only if source and donor roles share one endpoint-specific `used_documents` set.
    impact — an incomplete role-union implementation recreates the five fold-wide components found in `data/atlas_discovery_v3/preflight.json:12-30,12855-12874`.
    fix — freeze candidate order, when documents enter `used_documents`, unmatched-candidate handling, donor tie-breaking, and canonical component IDs; assert every selected endpoint component has exactly two distinct documents and no document occurs twice within that endpoint.
  - [high] docs/rfc-atlas-v3-discovery-factor-atlas.md:107,192-194 — endpoint-specific components do not account for a document reused across different construct endpoints.
    reasoning — such reuse is fold-safe because document folds are stable, but independently bootstrapping endpoint components treats shared documents as independent in the joint cross-family classifier.
    impact — descriptive lower bounds used by specificity gates can be too narrow.
    fix — retain endpoint-local components for endpoint metrics, but freeze a dependency-aware document-cluster/multiplier bootstrap for analyses pooling constructs, or explicitly form a separate cross-endpoint-disjoint classification sample; add a fixture where one document appears in two endpoints.
  - [high] docs/rfc-atlas-v3-discovery-factor-atlas.md:131,142,192 — the `>=50` overall threshold does not ensure usable five-fold construct support or adequate precision after disjoint matching.
    reasoning — GUM has only 197 documents, so each donor-linked endpoint has a hard maximum of 98 disjoint pairs before exact-match losses; a deterministic greedy matching can also leave feasible pairs unused or concentrate classes by fold. Fifty components per class is not itself a power justification for a `0.02` held-out macro-F1 increment with lower bound `>0`.
    impact — probe tuning or construct classification may become undefined or systematically underpowered despite passing the overall component count, turning low precision into an apparent scientific failure.
    fix — freeze a deterministic maximum-cardinality matching algorithm before rerun, report maximum/achieved cardinality and exclusions per fold, require every tuning fold to retain every intervention class, and prespecify a simulation/precision check for the decision threshold; otherwise label the endpoint underpowered/ineligible rather than failed.
  - [high] configs/atlas_discovery_v3/run.json:2-11 — v3.0 paths and protocol hashes currently identify the failed preparation.
    reasoning — overwriting or silently reusing IDs would make the revised population indistinguishable from the failed graph construction.
    impact — cache lineage and the claim that revision preceded scoring would be unverifiable.
    fix — leave v3.0 immutable with a digest-bound `FAILED_PRESCORE` marker; create a new v3.1 schema/config/protocol, namespace, data root, run root, row/component IDs, manifests, and opened-input ledger; hard-reject v3.0 caches from v3.1.
  - [medium] scripts/atlas_discovery_v3.py:1563-1574 — the global intervention union currently rewrites donor-free relative-gap component IDs.
    reasoning — relative-gap and relational rows depend on one document and gain no leakage protection from donor graphs.
    impact — their effective sample sizes collapse from hundreds of documents to 5–8 artificial components.
    fix — dispatch component construction by endpoint and assert relative-gap/relation component IDs equal their singleton source-document IDs and counts equal their distinct target-document counts.

NITS            (optional, cap at 5)

CHECKS RUN
  - inspected `data/atlas_discovery_v3/preflight.json` → EWT context/proper-noun/relative-gap have 5/5/8 components; GUM has 5/5/5; no representation scoring or neural training was recorded
  - inspected `scripts/atlas_discovery_v3.py` component construction → donor-only reuse sets plus a final global union explain both fold-wide chains and donor-free collapse
  - inspected `configs/atlas_discovery_v3/run.json` → v3.0 uses the original schema, roots, session, and protocol hash

CONTRACT COVERAGE
  - diagnosis of failed support → met — observed counts and global-union code agree
  - endpoint-specific singleton components → met in proposal — correct for relative-gap and relation endpoints
  - disjoint two-document donor components → met in principle — removes within-endpoint chains without using representation outcomes
  - leakage control → partial — folds are safe, but pooled cross-endpoint resampling still needs shared-document handling
  - power/support → partial — threshold is retained, but per-fold support and deterministic matching yield are unspecified
  - prescore-only revision → met — revising after label-only feasibility and before activation scoring is scientifically defensible
  - immutable revision lineage → partial — proposed, but exact terminal marker and namespace rejection rules must be frozen

UNKNOWNS
  - Whether exact-match disjoint matching leaves at least 50 components and adequate per-fold class support in both sources.
  - Whether v3.0 artifacts have remained immutable since the inspected prescore snapshot.
