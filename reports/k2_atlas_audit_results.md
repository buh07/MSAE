# Existing K=2 Atlas Audit — Results

**G2 outcome: EQUIVOCAL.** All four existing 1B checkpoints were transformed and audited on frozen C2. These are resumed, development-class checkpoints. The audit lacks the mandatory refit-bootstrap simultaneous bounds, Tier-2 sentinel collateral, cross-checkpoint CKA stability, and matched-random/sham representation-distance comparator, so it cannot establish superiority, equivalence, or a supported negative result.

## Point diagnostics

| Checkpoint | K=2 macro selectivity | Frozen simple comparator | K=2 − simple | C2 total FVU |
|---|---:|---:|---:|---:|
| g4, regularized seed 42 | -0.103 | +0.304 | -0.407 | 0.0324 |
| g5, regularized seed 43 | -0.107 | +0.304 | -0.411 | 0.0504 |
| g6, regularized seed 44 | -0.146 | +0.304 | -0.450 | 0.0208 |
| g7, no-incoherence seed 42 | -0.042 | +0.304 | -0.346 | 0.0258 |

The point pattern is unfavorable to the existing branch interpretation. Across g4/g5/g6, absolute-position recovery is only `0.396–0.514` with leakage `0.920–0.947`; structural recovery is `0.544–0.639` with leakage `0.890–0.909`. Lexical/content assignment is better (`0.880–0.905` recovery), but still leaks materially into the position branch (`0.388–0.528`). g7 improves positional point selectivity relative to the regularized checkpoints but remains negative. These are fixed-probe development diagnostics, not confidence-bounded comparisons.

The simple comparator's `+0.304` point selectivity is useful evidence that a non-generative projection may be competitive, but it is **not formal equivalence** because its calibration selection failed without Tier-2 collateral and no simultaneous equivalence bounds were computed.

## Functional diagnostics

Every checkpoint produced all 128 frozen counterfactual rows and 192 CE rows. Sentence-mean branch cosine distances are descriptive and fail the preregistered specificity gate because matched random/sham distance comparators are absent. The learned reconstructions are nearly invariant to the synthetic sentence transforms, while residual distances are large; this scale-sensitive pattern is not interpretable as causal specificity.

Suffix-LM interventions are clearly disruptive: K=2 reconstruction raises mean CE by `0.63–0.85`, removing position raises it by `2.57–3.63`, and removing content by `4.87–12.90`; matched random raises it by `0.68–1.02`. The frozen simple broad removal raises CE by `0.228`. These off-manifold diagnostics show that branch deletion is harmful, not that the branches uniquely implement the assigned family.

Machine-readable evidence: `results/atlas/k2_v1/k2_audit.json`, four `*_audit.json`, four `*_functional.json`, and their terminal markers.
