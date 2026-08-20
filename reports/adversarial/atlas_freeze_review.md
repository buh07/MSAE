# Atlas-v1 Final Adversarial Freeze Review

**Verdict: SHIP**  
**Reviewed prescore bundle:** `e7c12f4407249ccc556c8f56234c8de36af01d29a89de525deed7506876c8c31` (38 files)

The independent reviewer verified an exact `compute_bundle`/freeze-record match, 16 passing tests, deterministic synthetic output (`0c19199cca4b45a39fbb92b9080343e03d2d1756c23c8297716f5323c002ef04`), passing data QA, compilation of all score/freeze drivers, and an independent full-tokenization audit. The latter found zero retained partial-tail word rows, zero position-shift visibility violations, zero lexical alignment-flag mismatches, and exactly 16 genuinely token-aligned C2 lexical pairs.

## Issues found and resolved during review

- Document groups initially crossed confirmation roles; C1/C2 are now document-group disjoint.
- Counterfactual pairs repeated content and later included truncation/alignment errors; templates now have 32 unique pairs/family, complete offset visibility, exact `word_ids()` alignment flags, and independent QA.
- Label eligibility and source sentinels were incorrectly scoped; eligibility now intersects all four public roles and source is UD/NER.
- The synthetic gate originally omitted production refits and negative regimes; it now performs 500 refit draws and covers overlap, absence, near-zero gaps, shuffle, source reversal, decision precedence, and firewall failures.
- Prescore, trigger, calibration, activation, checkpoint, transform, and result artifacts were mutable or only existence-checked; all entry points now validate content digests and create-once terminal markers.
- Private-final integrity was unchecked after unlock; an M8 unlock now also verifies every private payload hash.
- Calibration could open C1 before a stable layer decision; L3 is now fixed primary, L4 descriptive, and the unavailable fallback estimator cannot select a layer.
- Mandatory refit/simultaneous inference, Tier-2 collateral, stability, and matched random/sham counterfactual evidence remain unimplemented. The code reports those as invalid/missing and forces G1/G2 equivocal; it emits no proxy p-values.
- Undefined summaries and nonfinite simultaneous draws now fail closed (`None` or error) and primary JSON writers reject NaNs.

## Reviewer conclusion

The freeze is internally consistent, fail-closed, provenance-bound, and honest about evidence that remains unavailable. Neural runtime feasibility and realized scores were not part of the prescore review; the four large checkpoints are rehashed by `checkpoint_spec` before use.
