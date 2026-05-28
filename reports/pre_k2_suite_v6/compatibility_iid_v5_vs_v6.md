# v5-Compatible IID vs v6 Balanced-IID Compatibility

This report decomposes observed raw position AUC differences into:
1. **Data-regime effect** (balanced-manifest IID vs v5-like single-corpus IID at matched seeds/ranks).
2. **Seed/split-composition effect** (v6 mixed all-splits estimate vs v6 IID estimate).

## Layer 3

- r8: v6_iid=0.8026±0.0040, compat_iid=0.8241±0.0035, v6_mixed=0.7911±0.0306, data_regime_effect=-0.0215, split_composition_effect=-0.0115
- r16: v6_iid=0.8026±0.0040, compat_iid=0.8241±0.0035, v6_mixed=0.7911±0.0306, data_regime_effect=-0.0215, split_composition_effect=-0.0115
- r32: v6_iid=0.8026±0.0040, compat_iid=0.8241±0.0035, v6_mixed=0.7911±0.0306, data_regime_effect=-0.0215, split_composition_effect=-0.0115

## Layer 4

- r8: v6_iid=0.7946±0.0076, compat_iid=0.8247±0.0018, v6_mixed=0.7805±0.0358, data_regime_effect=-0.0301, split_composition_effect=-0.0141
- r16: v6_iid=0.7946±0.0076, compat_iid=0.8247±0.0018, v6_mixed=0.7805±0.0358, data_regime_effect=-0.0301, split_composition_effect=-0.0141
- r32: v6_iid=0.7946±0.0076, compat_iid=0.8247±0.0018, v6_mixed=0.7805±0.0358, data_regime_effect=-0.0301, split_composition_effect=-0.0141

## Interpretation

Use `data_regime_effect` as the direct estimate of balanced-manifest vs v5-like IID shift at matched seeds. Use `split_composition_effect` to quantify the additional shift introduced when pooling IID with holdout regimes.
