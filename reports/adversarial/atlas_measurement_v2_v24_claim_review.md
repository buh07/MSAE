CLAIM: SUPPORTED
SUMMARY: The eligible frozen run rejects its conjunctive support rule, but cannot establish K2-wide absence or a causal mechanism.

BLOCKERS
  - None.

REVISIONS
  - `pilot_runs/20260802_atlas_measurement_v2_4/COMPLETE.json` — interpret `K2_broad_position_content_selective_not_supported` only as the frozen v2.4 truth-table outcome for g4/g5/g6, not as proof of a null or impossibility result.
  - `docs/rfc-atlas-v2-execution.md:102-132,539-546` — name the position construct **broad structural/context position**; the context intervention changes attended content and boundary distance, while strict absolute position is ineligible.
  - `docs/rfc-atlas-v2-execution.md:220-224,545-546` — state that the 500-draw intervals condition on frozen discovery/calibration probes and omit training, checkpoint-selection, and model-seed uncertainty.
  - `docs/rfc-atlas-v2-execution.md:43-60,533-538` — limit population language to this ESLSpok transcript-file estimand. Transcript IDs are not proven independent speakers/sessions, repeated utterances are retained, and C2 is public/support-inspected rather than an unopened blind final.
  - `docs/rfc-atlas-v2-execution.md:205-219,311-322` — treat the rank-16 projection/complement only as a non-decision comparator, not an equal-capacity/training-matched baseline or evidence of candidate superiority/equivalence.
  - `reports/k2_postwave_comparison.md` — do not attribute the outcome to the incoherence regularizer, seed, or resume lineage. g4/g5/g6 are three frozen development checkpoints, g6 has different resume history, and g7 is one diagnostic matched-seed negative control.
  - `pilot_runs/20260802_atlas_measurement_v2_4/analysis/results.json` — intervals are pointwise preregistered bootstrap summaries, not multiplicity-adjusted family-wide inference. The fixed conjunctive pass/fail decision is licensed; a general evidence-of-absence claim is not.

EVIDENCE CHECKED
  - `configs/atlas_measurement_v2/run.json` (`1a38042004ae18f34524508dda5d26d836530a16910a42b6259cfaf4cae3b86e`) and `docs/rfc-atlas-v2-execution.md` (`7a493107579416aed86456523e1125a31a4a6336fccd058a2efce845c3c9dd72`) — froze candidates, negative control, tasks, thresholds, data, seed, and the exact conjunctive decision rule before v2.4 scoring.
  - `analysis/results.json` (`c982eade2616cf2bf0fc8f772448b7a0fcad76ce1d57700975054ca1436328cf`) — overall eligibility is `eligible`; all required measurements/counterfactuals are finite and geometry is complete, so the result is not an equivocal missing-data outcome.
  - Independent recomputation from prepared task rows, frozen probe arrays, and C1/C2 representation caches — exactly reproduced 54 point macro-F1 values and 27,000 bootstrap scores/draws (maximum absolute error `0.0`), all 12 localization endpoints, all 8 specificity constructs and their 1,000 draws each, 9 candidate geometry summaries, checkpoint pass states, and the final truth table.
  - The decisive C2 head-distance failures are not merely threshold-edge misses: g4 assigned recovery `0.324 [0.286,0.357]`, selectivity `-0.411 [-0.457,-0.365]`; g5 `0.409 [0.374,0.445]`, `-0.279 [-0.327,-0.235]`; g6 `0.454 [0.419,0.494]`, `-0.335 [-0.384,-0.291]`. Across the 500 stored maps, each candidate's maximum recovery is below `0.65` and every selectivity draw is negative.
  - Relative-quartile localization also fails for all candidates: g4/g5 have negative 95% selectivity intervals; g6 is near zero (`0.003 [-0.058,0.068]`) and fails the positive-LCB rule.
  - Token-identity probe localization passes for all candidates (assigned-recovery points `0.834`–`0.862`, positive selectivity LCBs), licensing the narrower statement that lexical identity is preferentially decodable from the content branch under this probe.
  - Document-context specificity passes for g4/g5/g6, but entity-substitution specificity fails the required cross-family control despite positive within-construct branch margins: control margins are g4 `-0.784 [-0.971,-0.494]`, g5 `-0.555 [-0.711,-0.409]`, and g6 `-1.062 [-1.288,-0.845]`.
  - Candidate geometry passes separately: candidate-pair same-branch CKA minima exceed `0.995`, and all preregistered identity margins are positive, albeit small (minimum `0.000131`). Geometry therefore neither causes nor rescues the functional/localization failures.
  - g7 shows the same overall failure pattern and cannot block or rescue the candidate decision. Its behavior is consistent with a negative control but does not identify the effect of incoherence regularization.
  - Prepared/provenance and terminal artifacts — verified every prepared file digest, all four checkpoint digests, 9 terminal jobs with exit code zero, exact report/manifest hash links, C1/C2 whole-transcript disjointness (436/436 groups; zero main or pair-group overlap), and within-role context/entity disjointness. The signed provenance records 45 repeated content hashes (maximum multiplicity 42), which is a declared sampling limitation rather than hidden leakage.
  - `reports/adversarial/atlas_measurement_v2_v24_claim_review.json` (`1e5b45cb61444229e673bf8cfe59836b005ce8b6d8b3e8a843fe6465630b338e`) — durable independent recomputation summary.

LICENSED CLAIMS
  - Under the frozen v2.4 endpoint definitions and truth table, the eligible g4/g5/g6 set does **not** support selective K2 broad-structural/context-position versus lexical-content separation.
  - Every candidate fails the broad-family probe gate, decisively on signed head distance; all three also fail the lexical functional gate because entity response is not specific relative to document-context response.
  - All three candidates nevertheless show selective token-identity decodability, pass the document-context functional endpoint, and pass the separate geometry gate. The result is mixed in components but negative for the required conjunction.
  - The result is conditional on the frozen Pythia-160m layer-3 checkpoints, discovery/calibration fits, v2.4 tasks and thresholds, C2 ESLSpok transcript files, and fixed bootstrap maps.

UNLICENSED CLAIMS
  - K2, MSAEs, or incoherence-regularized models generally cannot yield position/content separation.
  - The study tested or refuted strict absolute-position specialization or authorized a three-family architecture decision.
  - The incoherence penalty, a training seed, checkpoint age, or resume history causally produced the observed leakage/failure.
  - Learned K2 is inferior, superior, or equivalent to a properly capacity-matched baseline; the projection comparator is descriptive and non-decision-bearing.
  - High cross-checkpoint CKA establishes functional specialization, or g7 establishes causal assay validity.
  - The result generalizes to other layers, models, corpora, identity vocabularies, thresholds, checkpoints, or training seeds, or includes training-sample/model-selection uncertainty.

UNKNOWNS
  - Whether additional independently trained K2 seeds/checkpoints, other layers/models, or other confirmation domains reproduce the failure.
  - Whether transcript-file clusters correspond to independent speakers/sessions and how repeated utterances affect effective sample size.
  - Sensitivity of inferential statements (not the frozen decision) to alternative valid task operationalizations, chance conventions, thresholds, resampling seeds, and multiplicity procedures.
  - The causal mechanism behind the leakage and counterfactual control failures; the present interventions and checkpoint comparisons do not identify it.

ARTIFACT HASHES
  - Final report JSON: `e55655b9a7f1b47ac6866ef08c86fed2bed8d9237e5cf3dab33f822299bdcd25`
  - Final report Markdown: `aa06be96aa83617be2031d0f10c39764bfded123742abfbcbc16b90430cc0fa1`
  - Final manifest: `a54a76bf8b923e4cb65f94161965e5409806ef35cb93862851a1fde150cdd7e8`
  - Terminal COMPLETE: `1d48b0f216cc2afa56b6ba99ffe439e8bfa9f6da94f03dcc15a40dd8221b324f`
  - Prepared manifest: `c9c50245c858f9881458dfcb1e935f0f767b070db727f82c2575227d7201ae1e`
  - Probe-model archive: `c90f747082c2a4b116e87365156e7996d62c66732642a41faab46eb90d99cf7c`
