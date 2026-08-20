# Atlas-v1 Post-score Completion Amendment

**Evidence class:** `postscore_amended_architecture_evidence`  
**Approved plan:** `docs/rfc-atlas-v1-completion.md`  
**Parent frozen bundle:** `e7c12f4407249ccc556c8f56234c8de36af01d29a89de525deed7506876c8c31`

This additive amendment implements the five missing analyses requested after the
atlas-v1 C1/C2 point scores were known: 500 discovery-refit draws, assigned Tier-2
collateral, cross-checkpoint stability, matched-random/sham specificity controls,
and amended G1a/G2a evaluation. It does not rewrite the original preregistration,
G1, G2, or architecture decision.

All scientific definitions, failure handling, estimator order, inference,
eligibility, resource limits, and decision precedence are normative in
`docs/rfc-atlas-v1-completion.md`. The machine config is
`configs/atlas_completion/analysis.json`. Both files are frozen together with the
implementation and generated public-role manifests before any completion C1/C2
score is produced.

The known four/five-group LinES strata make the corresponding structural
randomization hypothesis underpowered under the amended minimum-cluster rule.
The user's 2026-08-01 request nevertheless authorizes the five analyses as
diagnostic post-score measurements. Consequently the joint planning endpoint has
highest-precedence equivocal status, but the remaining G2 diagnostics are still
run if technical and resource gates pass.

The blind final payload remains locked and unread. No new model training is part
of this amendment.
