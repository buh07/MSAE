VERDICT: REVISE
ONE-LINE: Fold-balanced sampling is defensible, but it changes the estimand and needs frozen overlap safeguards.

BLOCKERS        (must fix before proceeding; empty if none)

REVISIONS       (should fix; not blocking)
  - [high] docs/rfc-atlas-v3-1-discovery-factor-atlas.md:227-238 — replacing exact-cell matching with class-balanced-per-fold sampling no longer compares identical nuisance strata across constructs.
    reasoning — the larger sample estimates cross-source incremental predictive information after modeled adjustment, not intervention specificity among exactly matched token contexts. Reporting overlap without an eligibility rule leaves unrestricted nuisance extrapolation, especially when a held-out joint stratum was absent from the fit source.
    impact — representation features that proxy an unseen or poorly modeled nuisance cell could produce the required `>=0.02` increment without construct-specific delta geometry.
    fix — explicitly rename the estimand as adjusted predictive specificity; freeze `__UNKNOWN__` handling and a common-support safeguard before the attempt-4 preflight (for example, a maximum held-out unseen-joint-cell rate per class/direction plus minimum common-support documents). Require the adjusted result to retain its sign on the fit-observed-joint-stratum subset, and never describe it as exact-matched or causal specificity.
  - [high] docs/rfc-atlas-v3-1-discovery-factor-atlas.md:227; proposed attempt-4 nuisance model — “plus individual frozen nuisance columns if planned” is not a frozen model specification.
    reasoning — a joint-cell one-hot, marginal one-hots, and their duplicated combination induce different ridge penalties and different behavior for unseen cells. Choosing among them after activations are available would directly alter the primary endpoint.
    impact — the `combined - nuisance_only` gate would not be reproducible and could be tuned toward a favorable result.
    fix — freeze one exact design now: the four marginal categorical blocks plus one joint-interaction block, fit-source-only vocabularies, explicit marginal and joint `__UNKNOWN__` columns, identical nuisance columns/scaling/penalty in nuisance-only and combined models, fit-source-only alpha selection, and paired evaluation rows/bootstrap maps. Add a nuisance-only planted fixture that must not pass when activations merely recode these columns.
  - [medium] data/atlas_discovery_v3_1_attempt3_prescore/FAILED_PRESCORE.json:1-11 — attempt 4 is another support-informed protocol revision and needs independent lineage.
    reasoning — attempt 3 correctly records that exact matching retained only 22 EWT and 6 GUM rows per class, with GUM at 463/500 finite draws (`preflight.json:41-85,13015-13059`). Reusing its namespace would obscure which estimand generated later rows.
    impact — a later positive adjusted result could be mistaken for a repaired execution of the stronger exact-matched test.
    fix — preserve attempt 3 unchanged; create an attempt-4 protocol/config/schema/data namespace and candidate-row hashes; record that only label/nuisance support was inspected; require byte-identical repeated preflights and no further support-rule changes if any `>=50`, `>=25 documents`, `>=5/fold`, or `>=490/500` gate fails.

NITS            (optional, cap at 5)
  - Proposed attempt-4 selection rule — call the within-class ordering “outcome/activation-blind”; construct class is necessarily used to compute `m`, so “class-label-blind” is potentially misleading.

CHECKS RUN
  - inspected attempt-3 terminal marker → `FAILED_PRESCORE`, with representation scoring and neural training both false.
  - inspected attempt-3 preflight support → exact matching retained 22 rows/class in EWT and 6 rows/class in GUM; GUM pooled completeness was 463/500.
  - inspected frozen shared-node bootstrap contract → the same document map weights all classes and donor-linked rows use the product of target/donor multiplicities.

CONTRACT COVERAGE
  - preserves existing support thresholds → met in proposal — no threshold is lowered.
  - deterministic fold-balanced sample → met in principle — per-source/fold minimum and hash ordering are outcome-independent.
  - shared-document dependence → met — the frozen node bootstrap remains applicable.
  - nuisance control → partial — joint categorical adjustment is reasonable, but exact columns and unseen-cell behavior are not frozen.
  - positivity/common support → partial — distributions and overlap are reported, but no decision safeguard is specified.
  - scientific interpretation → partial — adjusted predictive specificity is defensible, but it is weaker than the retired exact-matched estimand.
  - prospective revision lineage → partial — no activation has been opened, but attempt-4 namespace/retirement requirements must be explicit.

UNKNOWNS
  - Per-class/fold counts and 500-draw completeness under the proposed attempt-4 cap.
  - Cross-source rates of unseen combined strata and the size of the fit-observed common-support subset.
  - Whether a nuisance-only synthetic regime remains null under the final hierarchical categorical encoding.
