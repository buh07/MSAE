CLAIM: REVISE
SUMMARY: The bridge fixed control QA, but the SAE successor primarily reveals severe fit-to-held-out generalization failure.

BLOCKERS
  - `configs/trained_copy_sae_basis_selection_v1/run.json` and `configs/trained_copy_sae_capacity_v1_r2/run.json` — the new SAE study used 64 fit rows versus 2,048 in R2, while also changing SAE and panel seeds — it cannot cleanly attribute its disagreement with R2 to basis quality or selection.
  - `results/trained_copy_sae_basis_selection_v1_20260814/final/result.json` — every registered selected-span oracle had empirical rank 64 — their success proves ambient expressibility but not low-dimensional causal localization or selector quality.
  - `results/causal_manifold_bridge_v2_technical_20260814/PREVALIDATION.json` — 20/512 endpoints missed the frozen behavioral-support floor, so validation and all scientific method comparisons remained unopened.

REVISIONS
  - Keep the R2 result as the primary SAE capacity result: with the adequately sized fit panel, all sub-full code subsets failed while full-code SAE and rank-32 linear baselines passed.
  - Describe the new SAE successor as a generalization warning, not a basis indictment: mean fit reconstruction relative L2 was 0.00411, but a descriptive replay from signed caches gave approximately 0.606 held-out reconstruction relative L2 and approximately 0.588–0.596 held-out donor-delta error.
  - Treat selected-span success as an identity-equivalent full-ambient expressibility check because every selected span had rank 64.
  - Describe bridge v2 as a successful technical repair on eligible endpoints: QA, firewall and incomplete-controller checks passed 512/512, while the exact controller passed all joint-control gates in each of the 492/512 endpoints that met support.
  - Do not claim that bridge methods, factorial effects, or validation performance were evaluated.

EVIDENCE CHECKED
  - `reports/provenance/trained_copy_sae_basis_selection_v1_run_20260814/TERMINAL.json` — complete terminal and final SHA matched.
  - `results/trained_copy_sae_basis_selection_v1_20260814/final/result.json` — confirmation completed across three model checkpoints, three SAE seeds and three TopK settings.
  - New SAE fit diagnostics — fit reconstruction relative L2 mean 0.00411, range 0.00275–0.00678; fit donor-delta error mean 0.00273.
  - Signed activation/code caches and frozen SAE checkpoints — descriptive held-out reconstruction relative L2 was 0.607 on selector-fit, 0.606 on development and 0.607 on confirmation; held-out donor-delta error was 0.596, 0.595 and 0.588 respectively.
  - New SAE formal gates — ambient PCA rank 32 passed 6/6 checkpoint-panel records; full-code SAE passed 0/54; partial code patches passed 0/1,296; supervised OMP coefficient patches passed 0/270; selected-span and full-decoder-span oracles passed all records with rank 64.
  - `reports/provenance/causal_manifold_bridge_v2_technical_run_20260814/TERMINAL.json` and `PREVALIDATION.json` — qualification technical stop; validation unopened.
  - Bridge qualification shards — exact QA, view firewall and incomplete-controller QA passed 512/512; 492/512 endpoints met support and all 492 passed exact joint-control gates; the 20 misses had 97–119 eligible rows against the frozen minimum of 120.

UNKNOWNS
  - Whether fresh SAEs trained on an adequately sized fit panel reproduce the R2 full-code success.
  - Whether any decoder subset at or below the 32-dimensional causal scale provides a well-conditioned controller span.
  - Whether code-coordinate calibration, rather than feature selection or basis learning, explains failures once held-out reconstruction is adequate.
