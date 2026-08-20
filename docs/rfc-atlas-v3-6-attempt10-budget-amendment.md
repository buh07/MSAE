# Atlas v3.6 Attempt 10: budget-aligned numerical amendment

Attempt 9 remains terminal and is never retried. This amendment repairs one inconsistency: its coordinate criterion allowed up to 30 failing elements and two affected rows per 40-row cell, while relative-L2 and cosine used zero-failure caps selected without that same cell evaluator.

Attempt 10 treats signed EWT Attempt-8 and signed GUM Attempt-9 arrays as opened, label-free calibration. It searches a predeclared ascending Cartesian grid using the unchanged 30-cell evaluator on each source. `atol=2e-5`, `rtol=5e-6`, and all per-cell budgets are unchanged. Attempt-7 family rows are strict replay evidence but are not fabricated into 40-row cells.

The mechanically required cap is `relative_l2=2e-5` and `cosine_distance=5e-11`. GENTLE is the only validation corpus and is authorized once after implementation and freeze reviews. Any failure is terminal and cannot change the cap. EWT and GUM receive no new technical inference.

If GENTLE passes, the byte-frozen Atlas v3.3 scientific extraction and analysis run. Its namespace, authorization gate, and QA bridge change, not its scientific tasks or estimators. Because GUM has both label-free technical-calibration and disjoint scientific roles, all resulting scientific output is exploratory rather than independent confirmation. No neural training is authorized.
