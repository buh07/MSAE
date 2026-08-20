# Atlas-v1 Post-score Completion Attempt

**Run:** `pilot_runs/20260801_atlas_completion_v1/`  
**Evidence class:** `postscore_amended_architecture_evidence`  
**Completion freeze:** `0aac744d4d10f56cafae645fdc71ea8348bec743a5c20561d4649aedac0503ee`  
**Parent freeze:** `e7c12f4407249ccc556c8f56234c8de36af01d29a89de525deed7506876c8c31`  
**Status:** partial completion with a frozen inferential-invalidity stop; no planning branch selected

## Bottom line

The prespecified completion pipeline was implemented, piloted, adversarially
reviewed, frozen, and launched in tmux on launch-time-free GPUs. The
calibration-only baseline stage and both 500-draw raw-refit stages ran. The
primary L3 raw-refit stage then made the registered stop because only `414/500`
draws were scientifically finite, below the frozen minimum of `450`. The
descriptive L4 stage had `500/500` finite draws, but it cannot replace the frozen
L3 primary site.

The root upstream-stop record therefore names K2 refits, cross-checkpoint
stability, matched-random/sham specificity, merge, strict verification, and
rendering as not launched. No `planning_decision_v2` or promoted completion
result was created. Original `G1=equivocal`, `G2=equivocal`, and
`architecture_decision=equivocal_no_decision` remain unchanged. No new model
training is authorized. Because the frozen amendment separately authorized the
diagnostics after deterministic G1a invalidity, this is a partial execution that
requires a separately frozen additive diagnostic continuation; it is not the
completed five-analysis attempt.

## What ran

| Stage | State | Result |
|---|---|---|
| GPU pilot v10 | complete | numerical and budget gates passed; projected `43.8532` total GPU-hours; only discovery/calibration roles read |
| Prescore implementation review | `SHIP` | 134 tests passed; exact reviewed-candidate digest `2d2e50f013411f63aea6e0e4f38900c25a6a677dc4d8df7c43fba5b8a47bc36c` |
| Completion freeze | complete | additive bundle digest `0aac744d4d10f56cafae645fdc71ea8348bec743a5c20561d4649aedac0503ee` |
| Calibration baseline/Tier-2 eligibility | complete, selection failed | fallback `projection_broad16`; `baseline_selection_failed=true` |
| Raw L3 point plus draws `0..499` | frozen stop | point finite; `414/500` draws finite; required `>=450` |
| Descriptive raw L4 point plus draws `0..499` | complete | point finite; `500/500` draws finite |

The baseline consumed `0.1761` recorded GPU-hours. The L3 and L4 raw stages
recorded `6.5213` and `4.0190` worker GPU-hours, respectively.

## Calibration findings

Eight of nine Tier-2 sentinels passed calibration denominator eligibility.
`source_type` failed: its point raw-minus-chance gap was `-0.06552`, its 2.5th
percentile was `-0.07483`, and the threshold was `0.02`.

Only five of nine Tier-1 tasks passed the frozen calibration eligibility rule:
`boundary_state`, `dependency_depth`, `head_signed_distance`, `ner_coarse`, and
`relative_quartile`. The other four had fewer than 450 finite calibration draws:

| Task | Finite draws |
|---|---:|
| `abs_pos_16` | 316 |
| `abs_pos_8` | 438 |
| `lemma_identity_256` | 320 |
| `token_identity_256` | 314 |

Consequently no simple candidate was admissible. The registered fallback
`projection_broad16` was retained only so later diagnostics would have a fixed
comparator; the failed selection is itself a highest-precedence equivocal gate.

## Why L3 stopped

All 500 registered L3 draw artifacts were produced and no worker draw failed
technically. However, 86 draws were scientifically nonfinite because a
document/source bootstrap omitted at least one frozen truth class in a required
Tier-2 sentinel evaluation. The affected-sentinel counts were UPOS `36`,
capitalization `32`, and coarse dependency relation `21`; three draws omitted
classes for two sentinels, so these counts overlap. This left `414` complete
scientifically finite draws.

The terminal artifact records:

- `stop_code=insufficient_scientifically_finite_draws`;
- `failed_gate=minimum_complete_draws`;
- `scientific_retry_allowed=false`;
- `decision_promotion_allowed=false`.

This is an inferential-design limitation, not a GPU crash or missing output.
Relaxing the complete-case threshold, changing class rules, compacting draw IDs,
or substituting descriptive L4 after seeing the result would violate the frozen
protocol.

## What did not run

The bound root record
`pilot_runs/20260801_atlas_completion_v1/NOT_LAUNCHED_UPSTREAM_STOP.json` lists:

1. K2 500-draw refits;
2. cross-checkpoint stability;
3. matched-random/sham specificity;
4. merge;
5. strict completion verification;
6. decision rendering.

Thus the requested C2 Tier-2 collateral/stability/specificity evidence is not available in this base root,
and G1a/G2a were not rendered. Partial raw draw values are retained for audit and
design diagnosis but cannot support a simple-baseline, learned-model, or
supported-negative claim.

## Additive diagnostic continuation and summary recovery

The paragraph above remains the correct record of the base root. A separately
reviewed diagnostic-only continuation subsequently executed the work that the
base launcher skipped, without editing the base root, relaxing a threshold, or
granting decision-promotion authority.

**Continuation run:**
`pilot_runs/20260802_atlas_completion_diagnostic_continuation_v1/`  
**Recovered canonical summary:** `results/atlas/completion_diagnostic_v1/`  
**Execution status:** all 16 registered GPU scoring jobs exited successfully;
scientific stages retained their frozen complete/stop outcomes

| Diagnostic | Technical execution | Scientific disposition |
|---|---|---|
| Four K2 point/refit series | four points and `4 × 500` draws produced | every series `414/500` scientifically finite; stopped below `>=450` |
| Tier-2 collateral | computed in the K2 outputs | not confirmatory because the complete-case gate failed |
| Cross-checkpoint stability | point plus 500 draws produced | point nonfinite and `0/500` jointly finite; stopped |
| Matched-random/sham specificity | four computations completed | all four `counterfactual_gate_valid=false` |

The relative/structural stability point recorded learned mean pairwise CKA
`0.9982635047210163` and simple A/B CKA `1.0`. These values are descriptive only:
the full registered point was scientifically nonfinite and there was no valid
draw-level stability distribution.

The continuation consumed `17.021625942461668` actual GPU-hours and `54.2`
observed reserved GPU-hours. Candidate replay reproduced the summary bytes. An
independent result review and an independent scientific-claim review both
returned `SHIP`; the promotion freeze was then created, the canonical root was
published in tmux with terminal state `frozen_equivocal_stop`, and final
`verify-only` passed.

This closes the requested execution obligation, not the scientific gate. Original
G1/G2 remain equivocal. G1a is invalid/unrendered; G2a is not
promotable/unrendered. The paper branch remains unselected, training is not
warranted by current evidence, and the blind final remains locked.

## Next action

Do not retry the frozen completion with relaxed thresholds and do not start new
model training. Draft and independently review a new prescore
independent-evidence plan that fixes document/source bootstrap class coverage
using discovery/calibration only, then evaluates once on a new
architecture-confirmation source or dataset. Descriptive L4 cannot replace L3.
The blind final remains locked until a valid independent gate selects and freezes
one paper branch.

## Authoritative artifacts

- Pilot: `pilot_runs/20260801_atlas_completion_v1/pilot_v10/pilot.json`
- Review: `reports/adversarial/atlas_completion_implementation_review_20260801.md`
- Freeze: `configs/atlas_completion/freeze_record.json`
- Baseline: `pilot_runs/20260801_atlas_completion_v1/baseline/MEASUREMENT_COMPLETE.json`
- L3 stop: `pilot_runs/20260801_atlas_completion_v1/raw_refit/L3/FROZEN_EQUIVOCAL_STOP.json`
- L4 completion: `pilot_runs/20260801_atlas_completion_v1/raw_refit/L4/MEASUREMENT_COMPLETE.json`
- Downstream record: `pilot_runs/20260801_atlas_completion_v1/NOT_LAUNCHED_UPSTREAM_STOP.json`
- Diagnostic continuation collection: `pilot_runs/20260802_atlas_completion_diagnostic_continuation_v1/COLLECTION_COMPLETE.json`
- Recovered canonical report: `results/atlas/completion_diagnostic_v1/diagnostic_results.md`
- Recovered canonical terminal: `results/atlas/completion_diagnostic_v1/FROZEN_EQUIVOCAL_STOP.json`
- Recovery provenance: `results/atlas/completion_diagnostic_v1/RECOVERY_PROVENANCE.json`
- Recovery success closures: `pilot_runs/20260802_atlas_completion_summary_recovery_v1/job_manifests/{candidate,publish}.success.json`
- Recovery reviews: `reports/adversarial/atlas_completion_summary_recovery_{implementation,result,claim}_review_20260802.md`
