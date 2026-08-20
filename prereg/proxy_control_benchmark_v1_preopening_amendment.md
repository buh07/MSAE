# Proxy-to-Control Benchmark v1 — Preopening Amendment

The first candidate freeze was created before any result namespace, controlled-panel model forward,
training run, or scientific opening. Candidate review identified that the per-concept K2 branch
permutation and K1 atom selection were not serialized in metric rows. Without those fields, a
post-result reviewer could not distinguish a consistent branch identity from a different favorable
permutation for each concept.

Before any scientific execution, the runner was amended to record:

- the selected K2 target and complement branch for every seed, concept, and assignment source;
- the selected K1 atom indices and count;
- the fitted rank for each linear basis.

Candidate review of v2 then found a second auditability omission before opening: only evaluation-level
medians, rather than component-level behavioral and specificity rows, would have been serialized.
The runner now retains component IDs, eligibility, raw full effects, norm ratios, specificity,
behavioral recovery, and collateral KL, and computes frozen component-bootstrap intervals. This
changes retention and auditability only; it does not change an estimator or decision threshold.

No metric definition, threshold, source, model, layer, seed, method, training budget, intervention,
or decision rule changed. The original `FREEZE.json` is retained with SHA-256
`175e07227e5cd92f8da7dcb0742a9706c89a49a3f1ad279fe9d0bf975742682a`; `FREEZE_v2.json` is retained
with SHA-256 `8d9baf8f541b73bb35db43e1529e6a5e4933835d5accea229a326478df907913`.
Both are retired preopening candidates. The executable freeze is `FREEZE_v3.json`; only v3 may
authorize launch.
