# PCC Gate Revision v1

## Status
This document is a **prospective amendment draft** for the PCC observational gate.

It is derived from the completed A1b diagnostic run:
- [20260605_030600_pcc_stage_a1b](/jumbo/lisp/f004ndc/MSAE/pilot_runs/20260605_030600_pcc_stage_a1b)

It does **not** retroactively alter the frozen Stage A1 decision:
- [20260605_013756_pcc_stage_a1](/jumbo/lisp/f004ndc/MSAE/pilot_runs/20260605_013756_pcc_stage_a1)
- frozen result: `proceed_to_stage_b = false`

If this amendment is adopted, it should be treated as a **new, versioned gate policy** for an amended A1 reevaluation, not as a reinterpretation of the original A1 outcome.

## Scope
This amendment only changes the **PCC observational gate definition** for the existing `L3` checkpoint family:
- `g4`: regularized, seed `42`
- `g5`: regularized, seed `43`
- `g6`: regularized, seed `44`
- `g7`: no-inc control, seed `42`

This amendment does **not**:
- change K=2 training
- change the checkpoint set
- launch Stage B / PCC branch training
- change the probe backend or extraction pipeline
- change the current probe-selection regime

## Frozen Baseline Record
The original Stage A1 gate remains part of the permanent record.

### Frozen A1 Result
- Run root:
  - [20260605_013756_pcc_stage_a1](/jumbo/lisp/f004ndc/MSAE/pilot_runs/20260605_013756_pcc_stage_a1)
- Decision:
  - passed syntax families: `syntax_pos`
  - passed semantic families: `sem_wnut`
  - `proceed_to_stage_b = false`

### Why a Revision Is Being Considered
The A1b diagnostic pass showed that two parts of the frozen A1 gate were likely misaligned with the intended PCC question:

1. `syntax_dep` mixed together:
   - `deprel_coarse_ud_ewt`
   - `head_dir_dist_ud_ewt`

2. BIO-tagged NER was used as a semantic sentinel even though boundary structure can inject position-sensitive signal into the target.

The A1b diagnostic root is:
- [20260605_030600_pcc_stage_a1b](/jumbo/lisp/f004ndc/MSAE/pilot_runs/20260605_030600_pcc_stage_a1b)

Its aggregate verdict was:
- `candidate_amendment_supported = true`

## Amendment Goals
The amendment is intended to do three things:

1. Preserve the original governance principle:
   - require signal in both syntax-facing and semantics-facing families before any Stage B preparation

2. Remove the clearest task-design mismatches:
   - split `deprel_coarse` from `head_dir_dist`
   - use semantic label variants that reduce BIO-boundary confounding

3. Preserve comparability:
   - keep thresholds unchanged unless there is a separate amendment
   - keep the checkpoint family unchanged
   - keep the run as analysis-only

## Proposed Non-Threshold Changes

### 1. Syntax Family Revision
Replace the frozen Stage A1 syntax families with the following gated syntax families:

- `syntax_pos`
  - `pos_ud_ewt`
  - `pos_ambig_ud_ewt`

- `syntax_dep_coarse`
  - `deprel_coarse_ud_ewt`

- `syntax_morph`
  - `number_ud_ewt`

Track but do **not** gate on the following exploratory family:
- `syntax_dep_head_dir`
  - `head_dir_dist_ud_ewt`

### 2. Semantic Family Revision
Replace the frozen Stage A1 semantic families with the following gated semantic diagnostic families:

- `sem_wnut17_typeonly`
  - WNUT17 with `B-X` and `I-X` collapsed to `X`

- `sem_fewnerd_coarse_binary`
  - FewNERD coarse labels collapsed to `ENTITY` vs `O`

- `sem_wikineural_en_binary`
  - WikiNeural English labels collapsed to `ENTITY` vs `O`

These families were selected because they best isolate a content-private semantic diagnostic under the A1b evidence while reducing the most obvious BIO-boundary confound.

## Proposed Threshold Policy
This amendment does **not** change the numerical thresholds used in Stage A1.

### Syntax Family Pass Rule
A gated syntax family passes if:
- mean `joint_gain > 0.003`
- median `joint_gain > 0`
- positive-count `>= 3/4`

### Semantic Family Pass Rule
A gated semantic family passes if:
- `content_priv_metric > pos_priv_metric` in all `4/4` checkpoints
- mean `joint_gain < 0.005`

### Stage-B Proceed Rule
Proceed beyond the observational gate only if:
- at least `2` gated syntax families pass, and
- at least `2` gated semantic families pass

## A1b Evidence Supporting This Amendment

### Gated Syntax Families Under the Proposed Revision
| family | mean_joint_gain | median_joint_gain | positive_count | pass |
|---|---:|---:|---:|---|
| `syntax_pos` | `0.004530` | `0.004734` | `3/4` | yes |
| `syntax_dep_coarse` | `0.004873` | `0.004446` | `4/4` | yes |
| `syntax_morph` | `-0.002758` | `-0.000748` | `1/4` | no |

### Exploratory Syntax Family
| family | mean_joint_gain | median_joint_gain | positive_count | gated? |
|---|---:|---:|---:|---|
| `syntax_dep_head_dir` | `0.003875` | `0.005795` | `3/4` | no |

### Gated Semantic Families Under the Proposed Revision
| family | mean_joint_gain | content_private_all_runs | pass |
|---|---:|---|---|
| `sem_wnut17_typeonly` | `-0.002920` | `True` | yes |
| `sem_fewnerd_coarse_binary` | `0.002237` | `True` | yes |
| `sem_wikineural_en_binary` | `0.000380` | `True` | yes |

### Relevant A1b Non-Passing Diagnostics
These remain useful context but are not part of the proposed gated set:

| family | mean_joint_gain | content_private_all_runs | proposed role |
|---|---:|---|---|
| `sem_fewnerd_coarse_typeonly` | `0.010393` | `True` | diagnostic only |
| `sem_wikineural_en_typeonly` | `0.005077` | `True` | diagnostic only |
| `sem_wnut17_binary` | `0.020584` | `True` | diagnostic only |

## Technical Caveat Preserved
This amendment does **not** resolve the current probe-selection mismatch:
- the current probe workflow restores the best checkpoint by validation `top1`
- NER headline reporting still uses `macro_f1`

This caveat should be carried into any amended Stage A1 reevaluation.
It should **not** be silently changed inside this amendment.
If the project wants to change that behavior, it should be recorded in a separate tooling amendment.

## Operational Caveat Preserved
The A1b matrix had one early startup failure on `g4` under a shared-cache launch path.

This was resolved by:
- moving A1b launcher cache paths to per-job directories
- relaunching `g4`

The final A1b aggregate is based on all four completed jobs.

## Recommended Procedural Use
If this amendment is adopted, the recommended next step is:

1. Keep the frozen A1 no-go unchanged.
2. Commit this amendment as a new prereg artifact.
3. Produce a new amended observational decision artifact on the same checkpoint family.
   - recommended names:
     - `stage_a1r_decision.json`
     - `stage_a1r_decision.md`
4. Only if that amended evaluation passes should the project decide whether any Stage B preparation is warranted.

The project should **not** proceed directly from A1b diagnostics into Stage B.

## Non-Retroactivity Clause
This amendment must be interpreted prospectively.

It does **not** imply:
- the frozen A1 result was invalid
- the project had already passed the original gate
- or the A1b diagnostic should be substituted for the A1 decision

Instead, it means:
- the original A1 result remains the official frozen no-go
- A1b provides enough evidence to justify considering a revised gate definition
- any new proceed/no-go decision must be recorded under a new amended evaluation artifact

## Bottom Line
This draft amendment preserves the frozen A1 no-go while proposing a narrower and better-aligned observational gate:
- split `deprel_coarse` from `head_dir_dist`
- replace BIO semantic sentinels with revised semantic diagnostics
- keep thresholds unchanged
- require a fresh amended evaluation before any Stage B decision
