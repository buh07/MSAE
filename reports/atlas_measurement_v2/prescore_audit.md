# Atlas measurement v2 — static prescore audit

> Label/group metadata only. No representations were loaded, no neural model was scored, and no final data were opened.

## Decision

- Overall v2 decision eligibility: **ineligible** (`additional_decision_block`).
- `UD_English-LinES` is retired from v2 confirmation; the replacement source is unset.
- The frozen completion-v1 result is unchanged and remains historical evidence.
- Task/source files: 54 (19 support-eligible; 35 ineligible).

## Historical raw-row support diagnostic

This table preserves the pre-rebuild evidence that exposed the v1 failure. It is diagnostic only; v2 eligibility below is recomputed after the frozen label contract and document cap.

| Tier | Role | Task | Source | Raw groups | Rarest raw class | Rarest raw class groups | Raw omission probability | Raw max rows/group |
|---|---|---|---|---:|---|---:|---:|---:|
| tier1 | calibration | abs_pos_16 | UD_English-GUM | 176 | 15 | 8 | 0.028% | 273 |
| tier1 | calibration | abs_pos_16 | flaitenberger/wnut_17 | 500 | 15 | 1 | 36.751% | 128 |
| tier1 | calibration | abs_pos_8 | UD_English-GUM | 176 | 7 | 14 | 0.000% | 286 |
| tier1 | calibration | abs_pos_8 | flaitenberger/wnut_17 | 500 | 7 | 2 | 13.479% | 115 |
| tier1 | calibration | dependency_depth | UD_English-GUM | 176 | 4p | 135 | 0.000% | 481 |
| tier1 | calibration | head_signed_distance | UD_English-GUM | 176 | R5p | 122 | 0.000% | 439 |
| tier1 | calibration | lemma_identity_256 | UD_English-GUM | 174 | his | 13 | 0.000% | 264 |
| tier1 | calibration | lemma_identity_256 | flaitenberger/wnut_17 | 451 | which | 1 | 36.747% | 112 |
| tier1 | calibration | token_identity_256 | UD_English-GUM | 174 | were | 9 | 0.010% | 292 |
| tier1 | calibration | token_identity_256 | flaitenberger/wnut_17 | 453 | which | 1 | 36.747% | 107 |
| tier1 | C1 | abs_pos_16 | UD_English-LinES | 5 | 15 | 4 | 0.032% | 1785 |
| tier1 | C1 | abs_pos_16 | Babelscape/wikineural | 749 | 15 | 17 | 0.000% | 176 |
| tier1 | C1 | abs_pos_8 | UD_English-LinES | 5 | 7 | 4 | 0.032% | 1763 |
| tier1 | C1 | boundary_state | UD_English-LinES | 5 | interior | 5 | 0.000% | 2054 |
| tier1 | C1 | dependency_depth | UD_English-LinES | 5 | 4p | 5 | 0.000% | 4343 |
| tier1 | C1 | head_signed_distance | UD_English-LinES | 5 | ROOT | 5 | 0.000% | 4399 |
| tier1 | C1 | lemma_identity_256 | UD_English-LinES | 5 | " | 1 | 32.768% | 2043 |
| tier1 | C1 | lemma_identity_256 | Babelscape/wikineural | 746 | you | 1 | 36.763% | 61 |
| tier1 | C1 | relative_quartile | UD_English-LinES | 5 | 3 | 5 | 0.000% | 1790 |
| tier1 | C1 | token_identity_256 | UD_English-LinES | 5 | " | 1 | 32.768% | 1924 |
| tier1 | C1 | token_identity_256 | Babelscape/wikineural | 745 | you | 1 | 36.763% | 65 |
| tier1 | C2 | abs_pos_16 | UD_English-LinES | 4 | 15 | 1 | 31.641% | 1693 |
| tier1 | C2 | abs_pos_16 | Babelscape/wikineural | 750 | 15 | 10 | 0.004% | 199 |
| tier1 | C2 | abs_pos_8 | UD_English-LinES | 4 | 7 | 1 | 31.641% | 1699 |
| tier1 | C2 | abs_pos_8 | Babelscape/wikineural | 750 | 7 | 16 | 0.000% | 188 |
| tier1 | C2 | boundary_state | UD_English-LinES | 4 | interior | 4 | 0.000% | 1795 |
| tier1 | C2 | dependency_depth | UD_English-LinES | 4 | 4p | 4 | 0.000% | 5475 |
| tier1 | C2 | head_signed_distance | UD_English-LinES | 4 | ROOT | 4 | 0.000% | 5321 |
| tier1 | C2 | lemma_identity_256 | UD_English-LinES | 4 | ) | 2 | 6.250% | 1822 |
| tier1 | C2 | lemma_identity_256 | Babelscape/wikineural | 750 | you | 3 | 4.949% | 73 |
| tier1 | C2 | relative_quartile | UD_English-LinES | 4 | 3 | 4 | 0.000% | 1682 |
| tier1 | C2 | token_identity_256 | UD_English-LinES | 4 | " | 1 | 31.641% | 1827 |
| tier1 | C2 | token_identity_256 | Babelscape/wikineural | 750 | you | 3 | 4.949% | 70 |
| tier2 | calibration | capitalization | UD_English-GUM | 176 | mixed | 10 | 0.003% | 221 |
| tier2 | calibration | deprel_coarse | UD_English-GUM | 176 | csubj | 16 | 0.000% | 470 |
| tier2 | calibration | frequency_bin | UD_English-GUM | 176 | Q1 | 107 | 0.000% | 258 |
| tier2 | calibration | number | UD_English-GUM | 175 | Plur | 142 | 0.000% | 312 |
| tier2 | calibration | upos | UD_English-GUM | 176 | X | 10 | 0.003% | 504 |
| tier2 | calibration | word_length | UD_English-GUM | 176 | 8p | 158 | 0.000% | 295 |
| tier2 | C1 | capitalization | UD_English-LinES | 5 | mixed | 2 | 7.776% | 1782 |
| tier2 | C1 | context_offset | UD_English-LinES | 5 | 48 | 5 | 0.000% | 1840 |
| tier2 | C1 | continuation_status | UD_English-LinES | 5 | prefix | 5 | 0.000% | 1824 |
| tier2 | C1 | deprel_coarse | UD_English-LinES | 5 | discourse | 3 | 1.024% | 4465 |
| tier2 | C1 | frequency_bin | UD_English-LinES | 5 | Q4 | 5 | 0.000% | 1771 |
| tier2 | C1 | number | UD_English-LinES | 5 | Sing | 5 | 0.000% | 3416 |
| tier2 | C1 | source_type | UD_English-LinES | 5 | UD | 5 | 0.000% | 2182 |
| tier2 | C1 | upos | UD_English-LinES | 5 | INTJ | 3 | 1.024% | 4354 |
| tier2 | C1 | word_length | UD_English-LinES | 5 | 8p | 5 | 0.000% | 1672 |
| tier2 | C2 | capitalization | UD_English-LinES | 4 | mixed | 2 | 6.250% | 1593 |
| tier2 | C2 | context_offset | UD_English-LinES | 4 | 48 | 4 | 0.000% | 1719 |
| tier2 | C2 | continuation_status | UD_English-LinES | 4 | prefix | 4 | 0.000% | 1637 |
| tier2 | C2 | deprel_coarse | UD_English-LinES | 4 | iobj | 2 | 6.250% | 5413 |
| tier2 | C2 | frequency_bin | UD_English-LinES | 4 | Q4 | 4 | 0.000% | 1759 |
| tier2 | C2 | number | UD_English-LinES | 4 | Sing | 4 | 0.000% | 2871 |
| tier2 | C2 | source_type | UD_English-LinES | 4 | UD | 4 | 0.000% | 2647 |
| tier2 | C2 | upos | UD_English-LinES | 4 | X | 2 | 6.250% | 5338 |
| tier2 | C2 | word_length | UD_English-LinES | 4 | 8p | 4 | 0.000% | 1692 |

## V2-projected support findings

| Tier | Role | Task | Decision role | Source | Groups | Rarest selected class groups | Omission probability | Raw max rows/group | Selected max rows/group | Task-wide finite maps | Status |
|---|---|---|---|---|---:|---:|---:|---:|---:|---:|---|
| tier1 | calibration | abs_pos_16 | required | UD_English-GUM | 176 | 29 | 0.000% | 273 | 256 | 500/500 | eligible |
| tier1 | calibration | abs_pos_16 | required | flaitenberger/wnut_17 | 500 | 27 | 0.000% | 128 | 128 | 500/500 | eligible |
| tier1 | calibration | abs_pos_8 | diagnostic | UD_English-GUM | 176 | 14 | 0.000% | 286 | 256 | 419/500 | ineligible |
| tier1 | calibration | abs_pos_8 | diagnostic | flaitenberger/wnut_17 | 500 | 2 | 13.479% | 115 | 115 | 419/500 | ineligible |
| tier1 | calibration | boundary_state | diagnostic | UD_English-GUM | 176 | 173 | 0.000% | 203 | 203 | 500/500 | eligible |
| tier1 | calibration | boundary_state | diagnostic | flaitenberger/wnut_17 | 500 | 485 | 0.000% | 59 | 59 | 500/500 | eligible |
| tier1 | calibration | dependency_depth | diagnostic | UD_English-GUM | 176 | 135 | 0.000% | 481 | 256 | 500/500 | eligible |
| tier1 | calibration | head_signed_distance | required | UD_English-GUM | 176 | 122 | 0.000% | 439 | 256 | 500/500 | eligible |
| tier1 | calibration | lemma_identity_256 | diagnostic | UD_English-GUM | 173 | 25 | 0.000% | 264 | 224 | 500/500 | eligible |
| tier1 | calibration | lemma_identity_256 | diagnostic | flaitenberger/wnut_17 | 434 | 22 | 0.000% | 112 | 112 | 500/500 | eligible |
| tier1 | calibration | ner_coarse | diagnostic | flaitenberger/wnut_17 | 500 | 28 | 0.000% | 151 | 151 | 500/500 | eligible |
| tier1 | calibration | relative_quartile | required | UD_English-GUM | 176 | 171 | 0.000% | 225 | 225 | 500/500 | eligible |
| tier1 | calibration | relative_quartile | required | flaitenberger/wnut_17 | 499 | 450 | 0.000% | 89 | 89 | 500/500 | eligible |
| tier1 | calibration | token_identity_256 | required | UD_English-GUM | 173 | 22 | 0.000% | 292 | 248 | 500/500 | eligible |
| tier1 | calibration | token_identity_256 | required | flaitenberger/wnut_17 | 449 | 26 | 0.000% | 107 | 99 | 500/500 | eligible |
| tier1 | C1 | abs_pos_16 | required | UD_English-LinES | 5 | 5 | 0.000% | 1785 | 256 | 500/500 | ineligible |
| tier1 | C1 | abs_pos_16 | required | Babelscape/wikineural | 749 | 90 | 0.000% | 176 | 176 | 500/500 | ineligible |
| tier1 | C1 | abs_pos_8 | diagnostic | UD_English-LinES | 5 | 4 | 0.032% | 1763 | 256 | 500/500 | ineligible |
| tier1 | C1 | abs_pos_8 | diagnostic | Babelscape/wikineural | 750 | 30 | 0.000% | 177 | 177 | 500/500 | ineligible |
| tier1 | C1 | boundary_state | diagnostic | UD_English-LinES | 5 | 5 | 0.000% | 2054 | 256 | 500/500 | ineligible |
| tier1 | C1 | boundary_state | diagnostic | Babelscape/wikineural | 750 | 739 | 0.000% | 32 | 32 | 500/500 | ineligible |
| tier1 | C1 | dependency_depth | diagnostic | UD_English-LinES | 5 | 5 | 0.000% | 4343 | 256 | 500/500 | ineligible |
| tier1 | C1 | head_signed_distance | required | UD_English-LinES | 5 | 5 | 0.000% | 4399 | 256 | 500/500 | ineligible |
| tier1 | C1 | lemma_identity_256 | diagnostic | UD_English-LinES | 0 | — | — | 2043 | 0 | 0/500 | ineligible |
| tier1 | C1 | lemma_identity_256 | diagnostic | Babelscape/wikineural | 0 | — | — | 61 | 0 | 0/500 | ineligible |
| tier1 | C1 | ner_coarse | diagnostic | Babelscape/wikineural | 750 | 181 | 0.000% | 149 | 149 | 500/500 | eligible |
| tier1 | C1 | relative_quartile | required | UD_English-LinES | 5 | 5 | 0.000% | 1790 | 256 | 500/500 | ineligible |
| tier1 | C1 | relative_quartile | required | Babelscape/wikineural | 749 | 709 | 0.000% | 53 | 53 | 500/500 | ineligible |
| tier1 | C1 | token_identity_256 | required | UD_English-LinES | 0 | — | — | 1924 | 0 | 0/500 | ineligible |
| tier1 | C1 | token_identity_256 | required | Babelscape/wikineural | 0 | — | — | 65 | 0 | 0/500 | ineligible |
| tier1 | C2 | abs_pos_16 | required | UD_English-LinES | 4 | 2 | 6.250% | 1693 | 256 | 472/500 | ineligible |
| tier1 | C2 | abs_pos_16 | required | Babelscape/wikineural | 750 | 77 | 0.000% | 199 | 199 | 472/500 | ineligible |
| tier1 | C2 | abs_pos_8 | diagnostic | UD_English-LinES | 4 | 1 | 31.641% | 1699 | 256 | 344/500 | ineligible |
| tier1 | C2 | abs_pos_8 | diagnostic | Babelscape/wikineural | 750 | 16 | 0.000% | 188 | 188 | 344/500 | ineligible |
| tier1 | C2 | boundary_state | diagnostic | UD_English-LinES | 4 | 4 | 0.000% | 1795 | 256 | 500/500 | ineligible |
| tier1 | C2 | boundary_state | diagnostic | Babelscape/wikineural | 750 | 742 | 0.000% | 42 | 42 | 500/500 | ineligible |
| tier1 | C2 | dependency_depth | diagnostic | UD_English-LinES | 4 | 4 | 0.000% | 5475 | 256 | 500/500 | ineligible |
| tier1 | C2 | head_signed_distance | required | UD_English-LinES | 4 | 4 | 0.000% | 5321 | 256 | 500/500 | ineligible |
| tier1 | C2 | lemma_identity_256 | diagnostic | UD_English-LinES | 0 | — | — | 1822 | 0 | 0/500 | ineligible |
| tier1 | C2 | lemma_identity_256 | diagnostic | Babelscape/wikineural | 0 | — | — | 73 | 0 | 0/500 | ineligible |
| tier1 | C2 | ner_coarse | diagnostic | Babelscape/wikineural | 750 | 163 | 0.000% | 92 | 92 | 500/500 | eligible |
| tier1 | C2 | relative_quartile | required | UD_English-LinES | 4 | 4 | 0.000% | 1682 | 256 | 500/500 | ineligible |
| tier1 | C2 | relative_quartile | required | Babelscape/wikineural | 750 | 732 | 0.000% | 60 | 60 | 500/500 | ineligible |
| tier1 | C2 | token_identity_256 | required | UD_English-LinES | 0 | — | — | 1827 | 0 | 0/500 | ineligible |
| tier1 | C2 | token_identity_256 | required | Babelscape/wikineural | 0 | — | — | 70 | 0 | 0/500 | ineligible |
| tier2 | calibration | capitalization | required | UD_English-GUM | 176 | 81 | 0.000% | 221 | 221 | 500/500 | eligible |
| tier2 | calibration | capitalization | required | flaitenberger/wnut_17 | 499 | 188 | 0.000% | 89 | 89 | 500/500 | eligible |
| tier2 | calibration | context_offset | required | UD_English-GUM | 176 | 173 | 0.000% | 183 | 183 | 500/500 | eligible |
| tier2 | calibration | context_offset | required | flaitenberger/wnut_17 | 500 | 497 | 0.000% | 51 | 51 | 500/500 | eligible |
| tier2 | calibration | continuation_status | required | UD_English-GUM | 176 | 169 | 0.000% | 190 | 190 | 500/500 | eligible |
| tier2 | calibration | continuation_status | required | flaitenberger/wnut_17 | 500 | 500 | 0.000% | 57 | 57 | 500/500 | eligible |
| tier2 | calibration | deprel_coarse | required | UD_English-GUM | 176 | 48 | 0.000% | 470 | 256 | 500/500 | eligible |
| tier2 | calibration | frequency_bin | required | UD_English-GUM | 176 | 107 | 0.000% | 258 | 256 | 500/500 | eligible |
| tier2 | calibration | frequency_bin | required | flaitenberger/wnut_17 | 499 | 176 | 0.000% | 90 | 90 | 500/500 | eligible |
| tier2 | calibration | number | required | UD_English-GUM | 175 | 142 | 0.000% | 312 | 256 | 500/500 | eligible |
| tier2 | calibration | source_type | required | UD_English-GUM | 176 | 176 | 0.000% | 233 | 233 | 500/500 | eligible |
| tier2 | calibration | source_type | required | flaitenberger/wnut_17 | 499 | 499 | 0.000% | 76 | 76 | 500/500 | eligible |
| tier2 | calibration | upos | required | UD_English-GUM | 176 | 42 | 0.000% | 504 | 256 | 500/500 | eligible |
| tier2 | calibration | word_length | required | UD_English-GUM | 176 | 158 | 0.000% | 295 | 256 | 500/500 | eligible |
| tier2 | calibration | word_length | required | flaitenberger/wnut_17 | 498 | 264 | 0.000% | 79 | 79 | 500/500 | eligible |
| tier2 | C1 | capitalization | required | UD_English-LinES | 5 | 5 | 0.000% | 1782 | 256 | 500/500 | ineligible |
| tier2 | C1 | capitalization | required | Babelscape/wikineural | 750 | 179 | 0.000% | 57 | 57 | 500/500 | ineligible |
| tier2 | C1 | context_offset | required | UD_English-LinES | 5 | 5 | 0.000% | 1840 | 256 | 500/500 | ineligible |
| tier2 | C1 | context_offset | required | Babelscape/wikineural | 750 | 730 | 0.000% | 54 | 54 | 500/500 | ineligible |
| tier2 | C1 | continuation_status | required | UD_English-LinES | 5 | 5 | 0.000% | 1824 | 256 | 500/500 | ineligible |
| tier2 | C1 | continuation_status | required | Babelscape/wikineural | 750 | 747 | 0.000% | 58 | 58 | 500/500 | ineligible |
| tier2 | C1 | deprel_coarse | required | UD_English-LinES | 5 | 5 | 0.000% | 4465 | 256 | 500/500 | ineligible |
| tier2 | C1 | frequency_bin | required | UD_English-LinES | 5 | 5 | 0.000% | 1771 | 256 | 500/500 | ineligible |
| tier2 | C1 | frequency_bin | required | Babelscape/wikineural | 748 | 348 | 0.000% | 73 | 73 | 500/500 | ineligible |
| tier2 | C1 | number | required | UD_English-LinES | 5 | 5 | 0.000% | 3416 | 256 | 500/500 | ineligible |
| tier2 | C1 | source_type | required | UD_English-LinES | 5 | 5 | 0.000% | 2182 | 256 | 500/500 | ineligible |
| tier2 | C1 | source_type | required | Babelscape/wikineural | 749 | 749 | 0.000% | 51 | 51 | 500/500 | ineligible |
| tier2 | C1 | upos | required | UD_English-LinES | 5 | 3 | 1.024% | 4354 | 256 | 493/500 | ineligible |
| tier2 | C1 | word_length | required | UD_English-LinES | 5 | 5 | 0.000% | 1672 | 256 | 500/500 | ineligible |
| tier2 | C1 | word_length | required | Babelscape/wikineural | 750 | 661 | 0.000% | 54 | 54 | 500/500 | ineligible |
| tier2 | C2 | capitalization | required | UD_English-LinES | 4 | 4 | 0.000% | 1593 | 256 | 500/500 | ineligible |
| tier2 | C2 | capitalization | required | Babelscape/wikineural | 750 | 173 | 0.000% | 77 | 77 | 500/500 | ineligible |
| tier2 | C2 | context_offset | required | UD_English-LinES | 4 | 4 | 0.000% | 1719 | 256 | 500/500 | ineligible |
| tier2 | C2 | context_offset | required | Babelscape/wikineural | 750 | 744 | 0.000% | 47 | 47 | 500/500 | ineligible |
| tier2 | C2 | continuation_status | required | UD_English-LinES | 4 | 4 | 0.000% | 1637 | 256 | 500/500 | ineligible |
| tier2 | C2 | continuation_status | required | Babelscape/wikineural | 750 | 748 | 0.000% | 57 | 57 | 500/500 | ineligible |
| tier2 | C2 | deprel_coarse | required | UD_English-LinES | 4 | 4 | 0.000% | 5413 | 256 | 500/500 | ineligible |
| tier2 | C2 | frequency_bin | required | UD_English-LinES | 4 | 4 | 0.000% | 1759 | 256 | 500/500 | ineligible |
| tier2 | C2 | frequency_bin | required | Babelscape/wikineural | 750 | 345 | 0.000% | 60 | 60 | 500/500 | ineligible |
| tier2 | C2 | number | required | UD_English-LinES | 4 | 4 | 0.000% | 2871 | 256 | 500/500 | ineligible |
| tier2 | C2 | source_type | required | UD_English-LinES | 4 | 4 | 0.000% | 2647 | 256 | 500/500 | ineligible |
| tier2 | C2 | source_type | required | Babelscape/wikineural | 749 | 749 | 0.000% | 49 | 49 | 500/500 | ineligible |
| tier2 | C2 | upos | required | UD_English-LinES | 4 | 4 | 0.000% | 5338 | 256 | 500/500 | ineligible |
| tier2 | C2 | word_length | required | UD_English-LinES | 4 | 4 | 0.000% | 1692 | 256 | 500/500 | ineligible |
| tier2 | C2 | word_length | required | Babelscape/wikineural | 750 | 653 | 0.000% | 63 | 63 | 500/500 | ineligible |

## Family measurability

### calibration

- **absolute_position: not_run** — 1 eligible distinct constructs; missing/ineligible: controlled_position_shift.
- **lexical_semantic_content: not_run** — 1 eligible distinct constructs; missing/ineligible: entity_substitution.
- **relative_structural_position: eligible** — 2 eligible distinct constructs; missing/ineligible: none.

### C1

- **absolute_position: ineligible** — 0 eligible distinct constructs; missing/ineligible: absolute_bucket, controlled_position_shift.
- **lexical_semantic_content: ineligible** — 0 eligible distinct constructs; missing/ineligible: identity, entity_substitution.
- **relative_structural_position: ineligible** — 0 eligible distinct constructs; missing/ineligible: token_relative, dependency_relation.

### C2

- **absolute_position: ineligible** — 0 eligible distinct constructs; missing/ineligible: absolute_bucket, controlled_position_shift.
- **lexical_semantic_content: ineligible** — 0 eligible distinct constructs; missing/ineligible: identity, entity_substitution.
- **relative_structural_position: ineligible** — 0 eligible distinct constructs; missing/ineligible: token_relative, dependency_relation.

## Historical code context (not part of the label-only estimand)

Static inspection of `scripts/run_msae_refit_worker.py:408-430` shows that paired K2 workers reuse the corresponding raw C2 bootstrap maps. The historical identical 414/500 counts therefore are not independent model failures.

## Interpretation boundary

This audit diagnoses support and eligibility only. Bootstrap finiteness does not create independent documents, and a finite task is not evidence of selective localization. Specificity-cache and stability utilities were unit-tested but not applied to model representations in this work.
