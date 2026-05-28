# Pre-K2 Suite v6 Results Digest

- Source run: `20260528_001543_v6_prek2_fullsuite`
- Primary recommendation: `L3`
- Fallback recommendation: `L4`
- Headline ranks: `[8, 16]`
- Boundary diagnostic rank: `32`

## Gate Outcomes (Pythia-160M)

- Headline all-pass-v2 rate (`r8/r16`, all split modes): `1.000` (92/92)
- Boundary all-pass-v2 rate (`r32`, all split modes): `0.000` (0/46)

## Split Coverage (Pythia-160M rows)

- IID rows: `30`
- Source-holdout rows: `90`
- Corpus-holdout rows: `18`

## Notes

- Split-specific CI tables are included (`ci_metrics_iid.tsv`, `ci_metrics_source_holdout.tsv`, `ci_metrics_corpus_holdout.tsv`).
- Convergence diagnostics are included in `convergence_quality.tsv`.
- GPT-2 floor sensitivity notes are in `control_notes.md`.
- Compatibility sweep delta report is expected at `compatibility_iid_v5_vs_v6.md` after compat run completion.


## Compatibility Check

- v5-like IID compatibility run: 
- Delta report: 
