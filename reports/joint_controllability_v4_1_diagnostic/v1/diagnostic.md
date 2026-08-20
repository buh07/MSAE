# Pythia v4.1 opened-development diagnostic

**Analysis only; no model forward and no v4.1 rescoring.**

Pythia met signed effect support (59/64 per opened Wikitext partition) but failed both single-sham gates; all-model v4.1 stopped before method evaluation.

Eligible ratios: mean 0.435, median 0.242, 10% trimmed mean 0.335, p90 1.068; 13 rows exceeded one.

query_key deterministically fixes base_key and sham_key; role-specific key variance is non-identifiable.
one development row per document, so document fixed-effect variance is not separately estimable.

Exact machine-readable report: `diagnostic.json` (b6f3335c0dcf7a0a887816701d8e7fbe39f7d2ffc624bf4b3e3461300a438a3c).
