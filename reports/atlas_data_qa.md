# Atlas-v1 Data Freeze and QA

**Status:** prescore freeze candidate, rebuilt twice byte-identically. Discovery, calibration, C1, and C2 are public analysis roles; final is locally materialized under `data/atlas_v1/private/`, Git-ignored, mode `0700` with files mode `0600`, and guarded by the absent `.atlas_final_unlock` token. No neural C1/C2 scoring occurred before this freeze.

## Realized partitions

| Role | Base sentences | Offset units | Sources | Document groups | Use |
|---|---:|---:|---|---:|---|
| discovery | 11,850 | 47,400 | EWT 3,875; FewNERD 7,975 | 8,483 | fit scalers/probes/subspaces/vocab |
| calibration | 2,479 | 9,916 | GUM 1,474; WNUT 1,005 | 1,199 | select alpha/simple baseline/L4 trigger |
| C1 | 1,389 | 5,556 | LinES 639; WikiNeural 750 | 755 | raw G1 topology only |
| C2 | 1,231 | 4,924 | LinES 481; WikiNeural 750 | 754 | existing K=2/simple G2 only |
| final | 3,000 | 12,000 | PUD 1,000; WikiNeural 2,000 | — | M8 once; unopened here |

Counts are below nominal caps because canonical duplicates were removed with role precedence. C1/C2 were assigned by whole `document_group`; base-ID, content-hash, and document-group intersections are zero. **Power caveat:** LinES contributes only five C1 and four C2 documents. Structural-task inference must resample those document groups, so its effective sample size is 5/4 rather than its token count and may force an equivocal result.

## Packing, labels, and exact analysis rows

- Pythia tokenizer revision `582159a2dfe3e712a8d47ae83dec95ae3bde8e7e`; no special tokens; max length 128; offsets `{0,16,32,48}`.
- Every role-specific neutral prefix is exactly one model token. Four variants of every base stay together.
- Absolute-position labels cover every nonpadding token; word tasks use first subwords only. Prefixes and incomplete tail words are excluded from word tasks; independent QA retokenizes every length-128 unit and rejects a word whose final subword crosses the cutoff.
- `reports/atlas_label_counts.json` requires class support in **all four** public roles. All nine Tier-1 tasks retain at least two prescore-eligible classes.
- `configs/atlas/task_row_manifest.json` materializes every exact task-row ID and digest; runtime resampling is forbidden. Its digest is `55e6255cf4e75d3d3b42d119443cbb657d2838b402bec654c66a8b8da7ca14aa`.
- Source sentinel labels are `UD`/`NER`, not corpus names. The complete shortcut inventory is `analysis/label_inventory/shortcut_risks.tsv`.

## Counterfactual QA

Each public role has 32 examples in each of four families. Every family has four template groups of eight, 32 unique content pairs, unique IDs, and zero automatic invariant failures. Lexicons are role-disjoint. Only rows marked `token_aligned=true` may support token-level comparisons; C2 has exactly 16 such lexical/entity rows under exact equality of source/target tokenizer `word_ids()` sequences (not merely equal token counts). Unaligned transforms are sentence-level only. Representative human-readable examples and limitations are in `reports/counterfactual_template_review.md`; the independent `/adversarial` review is retained in `reports/adversarial/atlas_freeze_review.md` after the digest review.

## Reproduction evidence

The build/QA/sample/task-row pipeline was run twice. The aggregate SHA-256 over `partition_hashes.json`, `analysis_sample_manifest.json`, and `task_row_manifest.json` was identical on both builds: `c036aa5232150aa5d179f1f02fd49382b5b2cbac6a7fb858847139c3f06f53b3`. Automated QA passed, including a fixture proving the production firewall rejects a cloned cross-role document group.

```bash
export HF_HOME=$PWD/.cache/huggingface XDG_CACHE_HOME=$PWD/.cache
.venv-atlas/bin/python scripts/build_atlas_data.py --rebuild
.venv-atlas/bin/python scripts/qa_atlas_data.py
.venv-atlas/bin/python scripts/build_atlas_analysis_sample.py
.venv-atlas/bin/python scripts/build_atlas_task_rows.py
```
