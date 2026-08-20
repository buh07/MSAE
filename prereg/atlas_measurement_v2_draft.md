# Draft preregistration: Atlas/MSAE measurement v2

**Status:** DRAFT — not frozen and not authorization to score  
**Protocol:** `docs/rfc-atlas-v2-prescore-measurement.md`  
**Machine-readable draft:** `configs/atlas_measurement_v2/prescore.json`  
**Historical experiment:** Atlas completion v1 remains frozen and is not modified or rerun.

## Decision being prepared

The future study will decide whether an MSAE architecture yields reproducible, selective localization after measurement feasibility is established. Prescore feasibility is a necessary gate, not evidence for an architecture.

## Data state

- Calibration and public C1/C2 rows may be used for label/group-only feasibility auditing.
- `UD_English-LinES` is retired from v2 confirmation because it has only four or five document groups in the existing subroles.
- The replacement confirmation source is **unset**. No confirmation scoring is authorized until a separately reviewed candidate has immutable source/revision digests, signed grouping provenance, and passes every prescore gate.
- The existing blind final remains locked. The analysis code must never open it. It is usable only if an independent custodian supplies the signed, digest-bound, label-blind aggregate support attestation defined in the RFC. Missing, invalid, mismatched, or ineligible attestation means `retire_unopened` and requires a new preregistered final dataset.

## Primary prescore gates

For each ordinary applicable role/source/task:

1. at least 25 genuine groups;
2. at least 20 groups per retained class;
3. at most 256 selected rows from a group;
4. at least 490 finite maps among the 500 exact ordinary source-stratified document bootstrap maps;
5. at least two distinct, non-nested measurable constructs per family.

For pooled `source_type`, each source requires 25 groups and the row cap, while each pooled nuisance label requires 20 groups. The task does not require both deterministic source labels within each source.

The map generator, seed, label maps, identity-vocabulary ordering, family representatives, and missingness precedence are fixed in the RFC/config. A support-preserving diagnostic may describe rejection among the same ordinary maps; it may not redraw until all classes appear or rescue an otherwise ineligible task.

Only inputs marked `required_for_task_measurability` enter that endpoint. Historical nested alternatives such as `abs_pos_8` and lemma identity remain diagnostic; they cannot block promotion merely by being present. Missing required distinct constructs (for example controlled position shift or entity substitution) block family readiness explicitly.

## Sentinel hypotheses

- **Retention sentinels:** raw signal must be measurable; later representation retention uses a prespecified finite denominator.
- **Nuisance/non-introduction sentinel:** `source_type` is pooled across applicable sources. Its later estimand is the paired macro-F1 difference `representation - raw`; pass requires the paired 95% bootstrap upper endpoint to be no more than +0.02. Chance-level raw decodability is permitted and no normalized retention denominator is used.

## Endpoint validity

Task measurability, family localization, family stability, collateral validity, counterfactual validity, and overall decision eligibility are stored separately. `ineligible` takes precedence over `not_run`, which takes precedence over `eligible` for required aggregates. Finite subordinate values remain reportable and are never replaced by zero because another task/family is missing. Promotion requires every preregistered required endpoint to be eligible.

## Specificity and replay contract

Future scored work will create one float32 token cache per checkpoint/transform with ordered row IDs, offsets, hashes, and immutable lineage. Parent, actual, sham, and controls use that cache and the same pooling function.

Three checks remain separate:

1. exact cached no-op/hash replay;
2. repeated-inference numerical QA;
3. scientific inactive/sham specificity.

`atol` and `rtol` are intentionally **unset** in this draft. They may be calibrated only from authorized repeated inference on calibration data, then frozen before confirmation. The current completion's `1e-6` comparison is not inherited.

## Stability estimands

Later scoring will report task-level CKA, equal-weight representative-task family CKA, the full K2 cross-branch matrix, branch-identity margin, delta CKA, and nuisance-residualized CKA. Undefined/missing cells remain explicit. Geometry does not by itself establish selectivity; recovery, leakage, localization, and counterfactual response stability remain separate required evidence.

## Modeling hold

No K2/K3 training change is authorized by this draft. If a valid study still shows leakage, the next model choice will be the smallest supported among a simple projection/scrubbing baseline, supervised broad-position K2, absolute/structural/content K3, private/private/shared K3, conditional disentanglement, or a relation-aware representation. All learned comparisons must use controlled position/lexical pairs and equal-capacity/collapse controls.

## Current authorized action

Only run `scripts/audit_msae_measurement_v2.py` with the exact reviewed config. That command reads the digest-bound public Tier-1 and Tier-2 row files, computes label/group support, and writes a new report. It cannot select a dataset, open final data, load representations, score a model, train, download, or promote a decision.
