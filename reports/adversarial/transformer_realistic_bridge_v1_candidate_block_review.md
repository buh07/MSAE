# Adversarial candidate review — transformer-realistic bridge v1 (superseded BLOCK)

**Verdict: BLOCK**

This review attacked the first executable candidate after the plan review. It is retained rather than overwritten; the corrected candidate receives a separate review.

## Findings

1. **Critical — tautological positive-control comparison.** The candidate evaluated the direct hybrid graph against itself rather than requiring `ground_truth_delta` to traverse the registered patch insertion and recomputation path. A defect in the insertion machinery could therefore pass the bridge.
2. **High — incomplete controls absent from method registry.** Although bridge omissions existed, the separately frozen method comparison did not register the promised routing/private/shared and pathway-incomplete circuit baselines.
3. **High — tests did not establish the firewall or catch self-comparison/path omissions.** The payload exclusion test inspected an inventory list rather than trapping filesystem access; mutation tests did not break the insertion operator or all incomplete pathways.
4. **Revision — control-path mismatch.** The matched control was inserted at a different source node, confounding causal direction with path attenuation.
5. **Revision — method control margin was descriptive only.** It was computed but absent from the frozen joint gate.
6. **Revision — zero-delta behavior lacked end-to-end coverage.** Only the norm helper was tested.
7. **Revision — preservation field was ambiguous.** It could be misread as claiming that living PAPER/ledger files were unchanged.
8. **Nits.** Strengthen empirical factor-correlation QA, clarify the fixed least-squares readout, and keep GPU idleness semantics consistent.

## Required repair

Use one shared insertion operator for the independent hybrid oracle and all methods; add all incomplete controls; insert orthogonal controls at the same site/path; gate control margin; add anti-tautology, path-omission, access-trap, and zero-method integration tests; clarify the legacy preservation field; then obtain a fresh adversarial verdict before locking data.
