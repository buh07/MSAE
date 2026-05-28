# Control Notes

## GPT-2 Floor Sensitivity

Observed cases where `c2_var_ratio` passed but `tok_energy_excess` floor failed (reported as ratio-pass, floor-fail):
- split=iid layer=4 rank=4: c2_var_ratio=6.2779, tok_energy_excess=0.0275, thresholds=(3.00, 0.05)
- split=iid layer=4 rank=8: c2_var_ratio=5.4312, tok_energy_excess=0.0462, thresholds=(3.00, 0.05)
