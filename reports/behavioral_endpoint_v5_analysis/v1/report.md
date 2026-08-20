# V5 template-robustness analysis

**Analysis only. No model forward, no v5 rescoring, and no change to the formal FAIL.**

## Summary

All six checkpoint/source aggregates failed the frozen multi-sham specificity gate. Template effects were highly heterogeneous: the original-style template was comparatively selective for GPT-2 and Gemma, whereas the other templates combined weaker matching effects and/or larger unrelated-key dispersion. Selecting the favorable template now would be outcome-conditioned.

## Checkpoint × source × template

| Checkpoint | Source | T | Eligible | F median | Sham median | Ratio median | Ratio mean | >1 | Failure mix weak/large/both/neither |
|---|---|---:|---:|---:|---:|---:|---:|---:|---|
| gpt2 | WIKITEXT_FRESH | 0 | 62/64 | 1.739 | 0.291 | 0.168 | 0.185 | 0 | 0/24/2/38 |
| gpt2 | WIKITEXT_FRESH | 1 | 50/64 | 0.654 | 0.466 | 0.509 | 0.692 | 11 | 0/49/14/1 |
| gpt2 | WIKITEXT_FRESH | 2 | 54/64 | 0.854 | 0.375 | 0.386 | 0.543 | 6 | 0/50/10/4 |
| gpt2 | AGNEWS_FRESH | 0 | 64/64 | 2.270 | 0.316 | 0.141 | 0.164 | 0 | 0/17/0/47 |
| gpt2 | AGNEWS_FRESH | 1 | 52/64 | 0.707 | 0.431 | 0.540 | 0.612 | 8 | 0/51/12/1 |
| gpt2 | AGNEWS_FRESH | 2 | 62/64 | 1.110 | 0.406 | 0.318 | 0.452 | 3 | 0/53/2/9 |
| pythia160 | WIKITEXT_FRESH | 0 | 57/64 | 1.186 | 0.452 | 0.375 | 0.466 | 4 | 0/54/7/3 |
| pythia160 | WIKITEXT_FRESH | 1 | 50/64 | 0.638 | 0.426 | 0.611 | 0.685 | 9 | 0/50/14/0 |
| pythia160 | WIKITEXT_FRESH | 2 | 59/64 | 1.130 | 0.336 | 0.280 | 0.318 | 0 | 0/41/5/18 |
| pythia160 | AGNEWS_FRESH | 0 | 63/64 | 1.598 | 0.465 | 0.354 | 0.367 | 0 | 0/48/1/15 |
| pythia160 | AGNEWS_FRESH | 1 | 50/64 | 0.908 | 0.525 | 0.445 | 0.592 | 6 | 0/47/14/3 |
| pythia160 | AGNEWS_FRESH | 2 | 62/64 | 1.519 | 0.312 | 0.207 | 0.266 | 2 | 0/32/2/30 |
| gemma2 | WIKITEXT_FRESH | 0 | 64/64 | 3.033 | 0.357 | 0.117 | 0.129 | 0 | 0/10/0/54 |
| gemma2 | WIKITEXT_FRESH | 1 | 62/64 | 1.399 | 0.609 | 0.461 | 0.527 | 6 | 0/54/2/8 |
| gemma2 | WIKITEXT_FRESH | 2 | 63/64 | 2.242 | 0.840 | 0.421 | 0.548 | 6 | 0/54/1/9 |
| gemma2 | AGNEWS_FRESH | 0 | 64/64 | 3.410 | 0.371 | 0.110 | 0.121 | 0 | 0/5/0/59 |
| gemma2 | AGNEWS_FRESH | 1 | 61/64 | 1.564 | 0.596 | 0.375 | 0.548 | 6 | 0/57/3/4 |
| gemma2 | AGNEWS_FRESH | 2 | 63/64 | 2.975 | 0.726 | 0.319 | 0.385 | 2 | 0/47/1/16 |

## Interpretation

- GPT-2 templates 1–2 show both reduced matching effects and greater unrelated-key dispersion relative to template 0.
- Gemma retains the largest matching effects but templates 1–2 still show excessive unrelated-key sensitivity.
- Pythia varies strongly with wording; neither source supports template-general specificity.
- AG News usually improves matching support, but it does not repair the specificity gate.

Full key×answer strata, quantiles, tails, and template×source differences are in `analysis.json`.
