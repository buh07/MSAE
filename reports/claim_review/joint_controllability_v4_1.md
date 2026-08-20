# Post-result claim review — joint controllability v4.1

**Verdict: REVISE (claim wording), no code/result modification.**

> On two opened, document-disjoint Wikitext development partitions, the pinned GPT-2 and
> Gemma-2-2B checkpoints passed prespecified effect-support and single matched-sham gates for
> controlled key-value retrieval. Pythia-160M met effect-support requirements but failed both sham
> gates. Because v4.1 required every model-source cell to pass, it terminated before fresh-panel
> inference or representation-method evaluation. Post-result key-pattern observations are diagnostic
> and do not identify a key-role mechanism.

Evidence: GPT-2 had 64/64 eligible rows in both partitions with sham-ratio intervals
[0.119, 0.160, 0.205] and [0.129, 0.168, 0.234]; Gemma had 64/64 with
[0.091, 0.118, 0.152] and [0.084, 0.110, 0.146]. Pythia had 59/64 in both but intervals
[0.315, 0.410, 0.534] and [0.328, 0.452, 0.611]. The downstream `FAIL.json` files are
upstream-gate blocks, not representation-method failures. WIKI_CTX_A/B are within-corpus partitions,
not cross-domain replications. The synthetic positive-control gate only validates its constructed
mechanism. Query key deterministically fixed base and sham keys, so role-specific key attribution is
not identifiable.

Exact input hashes are recorded in the v5 predecessor-preservation manifest. No v4.1 artifact was
changed and this review supplies no permission to rescore or reopen it.

## Bound input hashes

- `configs/joint_controllability_benchmark_v4_1/FREEZE.json`: `d7f1510c95c69abb96dab85733bf2269dc7971ab33aa5f8a8a5eec8f3311e189`
- `results/joint_controllability_benchmark_v4_1_20260808/task_gate/result.json`: `87bd8fdf75a03add835a5c86947c30fa7e1f91a51c48e409309cecf4cff3d746`
- `results/joint_controllability_benchmark_v4_1_20260808/task_gate/gpt2/metrics.jsonl`: `dbbf81797041a61f988ae0a59cf545b7872dc33ea6b4556b347c95cbbd829bf5`
- `results/joint_controllability_benchmark_v4_1_20260808/task_gate/pythia160/metrics.jsonl`: `f959ceafe36c18a2db3ab1430b41623f07e6bdebb887a03f2222221d143c34b2`
- `results/joint_controllability_benchmark_v4_1_20260808/task_gate/gemma2/metrics.jsonl`: `38ddeef9525fcf64d3198dab9673b96abfe7001c9e1ccc4f0d24c1a52bccc094`
