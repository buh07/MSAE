# Atlas-v1 Initial Adversarial Freeze Review

**Verdict: BLOCK** (independent reviewer, before neural scoring).

The reviewer identified five primary blockers:

1. LinES document groups crossed C1/C2 because the parser discarded `newdoc id` state.
2. Counterfactual IDs were unique but the generated content repeated too few underlying pairs.
3. Label eligibility ignored calibration/C2, and the source sentinel encoded corpus identity rather than the intended UD/NER source type.
4. The synthetic gate did not exercise the production refit path, contained a nondeterministic runtime field, and omitted required negative/decision regimes.
5. The freeze was not executable: no immutable bundle/digest enforcement, private-final safeguards, or calibration-before-C1 phase boundary.

Required fixes included numerical counterfactual/stability/sensitivity rules, exact frozen task rows, a production firewall duplicate fixture, direct bundle hashing, and an L4 trigger frozen before C1.

All items were treated as blocking. The corrected bundle is reviewed separately in `atlas_freeze_review.md`; this file is retained so the review history is not overwritten.
