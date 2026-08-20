# Raw L3/L4 Separable-Information Atlas — Results

**G1 outcome: EQUIVOCAL.** L3 is the frozen primary layer; L4 is descriptive. Both layers completed, but the production driver implements fixed-probe document resampling rather than the mandatory 500-draw discovery-refit hierarchical bootstrap. It therefore reports point diagnostics and cannot promote a broad or split architecture.

## Primary-site L3 diagnostics

| Family / candidate | Assigned recovery | Leakage | Selectivity margin |
|---|---:|---:|---:|
| split absolute position | 0.930 | 1.065 | -0.135 |
| split structural position | 0.863 | 0.989 | -0.126 |
| split lexical/semantic | 1.000 | 0.012 | +0.988 |
| broad absolute position | 0.935 | 1.068 | -0.133 |
| broad structural position | 0.979 | 0.991 | -0.013 |
| broad-complement lexical/semantic | 0.999 | 0.070 | +0.929 |

The split and broad positional macro-selectivity diagnostics are `-0.131` and `-0.073`. Thus the point estimates do **not** show selective absolute/structural localization: the nonassigned positional representation often decodes the task as well as or better than the assigned representation. In contrast, lexical/semantic content is cleanly retained in the positional complement in this task-derived linear diagnostic.

All nine raw tasks were decodable above analytic chance under the fixed-probe diagnostic. Examples: absolute-16 macro-F1 `0.1165` vs chance `0.0623`; relative quartile `0.5342` vs `0.2500`; head signed distance `0.4080` vs `0.1093`; token identity `1.0000` vs `0.0251`; NER `0.6584` vs `0.1988`. Dependency-depth and head-distance intervals, however, resample only **five LinES documents**, so token counts do not remove the power limitation.

The eight absolute-vs-structural principal angles range from `49.5°` to `89.0°`; this indicates neither identical nor uniformly orthogonal spans, but geometry alone is non-decisive.

## L4 descriptive sensitivity

L4 is qualitatively similar: split absolute/structural margins `-0.050/-0.119`, broad margins `-0.178/-0.009`, and lexical margins `+0.977` (split complement) and `+0.905` (broad complement). Its positional point diagnostics do not rescue L3, as required by the fixed-layer policy.

## Calibration limitation

All three Tier-1 families retained their prescore task counts on calibration at both layers. Nevertheless, none of the simple candidates could formally pass selection because the mandatory Tier-2 collateral probe audit is not implemented. The frozen default is therefore `projection_broad16` with `baseline_selection_failed=true`; it is a comparator, not a validated winner.

Machine-readable evidence: `results/atlas/raw_v1/L3_raw_atlas.json`, `L4_raw_atlas.json`, per-layer calibration freezes, and `COMPLETE.json`.
