# TODO_pcc.md — PCC and Positional-Family Experimental Plan

## Scope
This document now covers a broader bridge program than the original “PCC only” framing.

The old framing asked:
- is there a **position-content crossover (PCC)** signal that is enriched for syntax or relational structure?

The updated framing asks two competing questions:
- is the observed syntax-like “joint” signal a **true shared / crossover / interaction component**?
- or is it partly an artifact of the current K=2 split only isolating **absolute position**, while leaving **relative position / structural position** mixed into the content side?

The revised goal is therefore to distinguish between three possibilities:
- **P1: Broad positional-family hypothesis.**
  - Much of the syntax-looking signal is really positional structure in a broader sense:
    - absolute position
    - relative order
    - signed distance
    - boundary/depth structure
    - local arrangement
- **P2: Genuine PCC hypothesis.**
  - Even after broad positional structure is stripped out, some useful structure remains genuinely shared or interaction-like.
- **P3: Richer multi-branch hypothesis.**
  - The right decomposition may be:
    - absolute position
    - relative/structural position
    - content
  - or:
    - position-private
    - content-private
    - shared/PCC

This document is still a bridge-program execution plan, not a replacement for the main paper roadmap in [TODO.md](/jumbo/lisp/f004ndc/MSAE/TODO.md).

It is grounded in:
- [RESULTS.md](/jumbo/lisp/f004ndc/MSAE/RESULTS.md)
- [ANALYSIS.md](/jumbo/lisp/f004ndc/MSAE/ANALYSIS.md)
- [MSAE_revised.md](/jumbo/lisp/f004ndc/MSAE/MSAE_revised.md)
- [reports/pre_k2_suite_v6/pre_k2_decision.md](/jumbo/lisp/f004ndc/MSAE/reports/pre_k2_suite_v6/pre_k2_decision.md)

### Relationship to the current paper roadmap
- This plan does **not** replace Paper 1.
- This plan does **not** cancel the existing Paper 2 direction.
- This plan does **not** assume a new PCC branch model is already justified.
- This plan adds a new interpretation-tightening layer:
  - first determine whether current PCC-like signal is really **shared interaction**
  - or whether it is better understood as **under-modeled positional-family structure**
  - only then decide between revised `K=2`, `K=3`, or a true PCC branch.

---

## 0. Status Snapshot and Reframing (2026-06-16)

### 0.1 Established by the current project
- [x] The raw-activation pre-K2 suite supports a stable position/content separation on `Pythia-160M`.
- [x] In the final pre-K2 suite, `Pythia-160M` layers `3` and `4` pass the v2 separability gate at headline ranks `8` and `16` across IID, source-holdout, and corpus-holdout conditions.
- [x] The final packaged result reports `92/92` headline passes and `0/46` passes at boundary rank `32`.
- [x] `L3` is the primary K=2 target and `L4` is the fallback.
- [x] The GPU-first K=2 trainer is operational, resumable, and stable enough to support long runs.
- [x] The current wave-2 fastdata-stream run shows that `lambda_inc=1e-2` substantially reduces incoherence relative to the no-inc control.
- [x] The strongest existing claim is about **branch separation** and geometry, not universal reconstruction improvement.

### 0.2 Completed PCC bridge stages
- [x] Stage A0 aggregate decision is complete:
  - `pilot_runs/20260604_184924_pcc_stage_a0/`
  - `pos_ud_ewt` and `deprel_ud_ewt` are stable-positive under the Stage A0 thresholds.
  - `ner_wnut17` is content-private but not strongly crossover-enriched.
- [x] Stage A1 expanded observational audit is complete:
  - `pilot_runs/20260605_013756_pcc_stage_a1/`
  - all four `L3` checkpoints (`g4/g5/g6/g7`) finished successfully.
  - the frozen Stage A1 decision is `proceed_to_stage_b = false`.
- [x] Stage A1b diagnostic follow-up is complete:
  - `pilot_runs/20260605_030600_pcc_stage_a1b/`
  - A1b is diagnostic only and does **not** amend the frozen Stage A1 result.
  - A1b supports a candidate amendment path.
- [x] The PCC state was frozen before confirmation:
  - `prereg/pcc_state_checkpoint_20260605_pre_a1c.md`
- [x] Stage A1c confirmation is complete:
  - `pilot_runs/20260605_034815_pcc_stage_a1c/`
  - NER probe checkpoint selection aligned to validation `macro_f1`.
  - semantic probe budgets increased relative to A1b.
  - `amendment_confirmed = true`
  - `stage_a1r_decision.json` / `stage_a1r_decision.md`
  - amended observational decision is `proceed_to_stage_b = true`.
- [x] Stage B-light control audit is complete:
  - `pilot_runs/20260605_040323_pcc_stage_b_light_controls/`
  - matched-token controls
  - coarse matched-position controls
  - residual-vs-joint comparison
  - matched-seed regularizer sensitivity (`g4` vs `g7`)
  - key readout:
    - `syntax_pos` remains positive under full, token, and coarse position controls
    - `syntax_dep_coarse` remains positive under full and coarse position controls, but weakens sharply under matched-token control
    - `sem_fewnerd_coarse_binary` and `sem_wikineural_en_binary` remain content-private with low joint gain
    - `g7` continues to show larger syntax-crossover signal than `g4`
- [x] Still out of scope so far:
  - curated contrast-set pack
  - new PCC branch training
  - new K=2 checkpoints

### 0.3 New interpretation pressure introduced by the updated idea
- [ ] The current K=2 “position” branch is best interpreted as a branch anchored to **absolute-position-predictive signal**, not necessarily all positional structure.
- [ ] Syntax may depend strongly on **relative position**, **distance**, **ordering**, **boundary structure**, and **structural depth**, not just absolute token index.
- [ ] Therefore, current positive “joint” syntax gains may be explained in at least two ways:
  - genuine shared interaction between position and content
  - or a too-narrow positional branch that leaves relative/structural position mixed into the content side
- [ ] The next bridge-program priority is now to separate those explanations cleanly.

### 0.4 What remains unresolved
- [ ] Is the current syntax-like joint signal really **PCC**, or mostly **broad positional-family leakage**?
- [ ] Can we isolate a branch that captures **absolute + relative + structural position** and leave behind a more clearly **de-positioned content** representation?
- [ ] If such a branch exists, does the apparent crossover signal shrink materially?
- [ ] If not, does a true shared/interaction component remain after positional-family stripping?
- [ ] Does the right next architecture look more like:
  - revised `K=2` all-position vs content,
  - `K=3` absolute/relative/content,
  - or `K=3` position-private/content-private/shared?

---

## 1. Core Reframing

### 1.1 Old bridge-program framing
The original PCC bridge program assumed:
- the current K=2 result already isolates “position” well enough,
- and the main next question is whether syntax lives in a **shared / crossover** component.

### 1.2 Updated bridge-program framing
The updated bridge program treats the current K=2 result as a **first useful split**, but possibly not the final correct positional split.

The new working question is:
- can we separate **all positional structure** from a **position-minimized content representation**?

This reframing is deliberately broader than “absolute position vs content.”

### 1.3 Safer language for the new target
Do **not** promise “pure content” as an unconditional objective.

Use instead:
- [ ] **de-positioned content**
- [ ] **position-minimized content**
- [ ] **content after broad positional scrubbing**

Reason:
- content in contextual transformer activations is not guaranteed to be independent of order
- some meaning is carried by structural arrangement
- therefore “pure content” may exist only approximately

### 1.4 Main decision tree for the new program
- [ ] **Case A: broad positional-family branch succeeds**
  - syntax-like joint gain shrinks materially after broad positional stripping
  - next move favors revised `K=2` all-position vs content
- [ ] **Case B: absolute and relative/structural position separate from each other**
  - broad position is too heterogeneous for one branch
  - next move favors `K=3` absolute-position + relative/structural-position + content
- [ ] **Case C: genuine PCC remains after broad positional stripping**
  - syntax-like gains survive even after broad positional leakage is removed
  - next move favors true PCC/shared branch work

---

## 2. Main Hypotheses

### 2.1 Primary updated hypotheses
- [ ] **H1 (broad positional-family hypothesis):**
  - much of the currently observed syntax-like “joint” gain reflects positional information broader than absolute token index.
- [ ] **H2 (de-positioned-content hypothesis):**
  - after removing broad positional structure, semantic/content tasks remain strong while recoverable positional information drops sharply.
- [ ] **H3 (residual-PCC hypothesis):**
  - even after broad positional removal, some syntax/relational structure still shows stable positive joint-only or interaction-only gain.
- [ ] **H4 (split-complexity hypothesis):**
  - if H1 holds only partially, the correct model may require more than one positional branch:
    - absolute position
    - relative/structural position
    - content
- [ ] **H5 (regularization hypothesis):**
  - the current K=2 incoherence penalty may be suppressing shared or structurally positional signal that is not well handled by the current private/private setup.

### 2.2 Null / weakening outcomes
- [ ] **N1:** syntax remains mostly content-private even after better positional modeling.
- [ ] **N2:** broad positional-family probes fail to isolate a stable low-rank positional family.
- [ ] **N3:** de-positioned content loses too much semantic utility to be a meaningful target.
- [ ] **N4:** observed “joint” gains disappear under stronger controls and better labeling.

### 2.3 Grounding in the current record
These hypotheses are grounded in current results:
- [x] the pre-K2 suite shows a robust position/content separability regime
- [x] the current K=2 model clearly changes branch geometry
- [x] the completed PCC bridge stages already show that some syntax-like tasks behave differently from semantic tasks
- [x] the matched-seed `g7 > g4` sensitivity suggests some overlap-sensitive signal may be getting suppressed by stronger private/private regularization

---

## 3. Operational Definitions

### 3.1 Position-family
For this updated program, **position-family** means all information whose main job is describing where or how a token is arranged in context.

This includes:
- [ ] absolute position
- [ ] distance to BOS/EOS
- [ ] front/middle/back coarse location
- [ ] relative order within a local window
- [ ] signed distance to an anchor or governing token
- [ ] dependency head direction and distance
- [ ] clause/phrase boundary proximity
- [ ] depth-like structural location
- [ ] repetition distance / previous-occurrence distance

### 3.2 Absolute-position signal
- [ ] index-like signal recoverable from one token’s activation:
  - exact or bucketed slot
  - distance from beginning/end

### 3.3 Relative-position signal
- [ ] relational or offset-like signal:
  - left/right of an anchor
  - signed distance
  - local order
  - head direction
  - same-token distance

### 3.4 Structural-position signal
- [ ] structure-like arrangement information that is still more positional than semantic:
  - parse depth
  - clause boundary distance
  - span membership / BIO boundary context
  - constituent depth

### 3.5 De-positioned content
- [ ] a representation that:
  - preserves lexical/semantic/content performance
  - minimizes recoverable absolute/relative/structural positional information

### 3.6 Residual crossover / PCC
Only call a signal **PCC** if it survives after strong positional-family stripping.

Candidate operationalizations:
- [ ] **PCC-0:** joint-only predictive gain
- [ ] **PCC-1:** residual after removing both private content and broad positional-family signal
- [ ] **PCC-2:** supervised low-rank interaction readout
- [ ] **PCC-3:** learned shared branch

### 3.7 Token-local versus relation-aware settings
This program must distinguish two regimes:
- [ ] **token-local**
  - single-token activation only
- [ ] **relation-aware**
  - pairwise/window features
  - useful if relative-position information is not recoverable from a single token vector alone

Token-local should be tried first because it is closest to the current MSAE setup.
Relation-aware should be added if token-local evidence suggests that relative-position signal is real but too distributed.

---

## 4. Working Representation Families

### 4.1 Existing representations already available
- [x] raw activation `x`
- [x] K=2 position reconstruction `x_pos_priv`
- [x] K=2 content reconstruction `x_content_priv`
- [x] joint concatenation `[x_pos_priv, x_content_priv]`
- [x] residual proxy `x_resid`

### 4.2 New analysis-side candidate representations
- [ ] `S_abs`
  - subspace from absolute-position probe family
- [ ] `S_rel`
  - subspace from relative-position probe family
- [ ] `S_struct`
  - subspace from structural-position probe family
- [ ] `S_posfam`
  - combined positional-family subspace
- [ ] `x_depos_proj`
  - projection residual:
  - `x - Proj_{S_posfam}(x)`
- [ ] `x_depos_regress`
  - residual after direct regression on positional-family labels
- [ ] `x_depos_adv`
  - representation after adversarial linear positional scrubbing
- [ ] `x_pcc_resid`
  - whatever remains after removing both content-private and position-family signal

### 4.3 Candidate model-side branch families
- [ ] `x_abs_priv`
- [ ] `x_rel_priv`
- [ ] `x_struct_priv`
- [ ] `x_posfam_priv`
- [ ] `x_content_depos`
- [ ] `x_shared` / `x_pcc`

---

## 5. Task Battery and Label Families

### 5.1 Absolute-position tasks
- [ ] exact token position bucket over `0..1023`
- [ ] coarse position bucket:
  - front
  - early-mid
  - late-mid
  - back
- [ ] distance to BOS
- [ ] distance to EOS / sequence tail
- [ ] relative fraction through context window

### 5.2 Relative-position tasks
- [ ] signed distance to dependency head
- [ ] head direction:
  - left
  - right
  - self/root/none
- [ ] head-distance bucket
- [ ] signed distance to previous occurrence of same token or lemma
- [ ] local order within a small context window
- [ ] repeated-token offset bucket
- [ ] distance to nearest punctuation/boundary token

### 5.3 Structural-position tasks
- [ ] BIO or boundary tagging
- [ ] clause boundary detection
- [ ] phrase boundary detection
- [ ] parse depth or approximate bracket depth
- [ ] dependency depth from root
- [ ] inside/outside span markers
- [ ] token role in local span:
  - start
  - middle
  - end
  - singleton

### 5.4 Content tasks
- [ ] token identity top-k bucket
- [ ] lemma or lexical cluster where feasible
- [ ] NER type:
  - WNUT17
  - FewNERD coarse
  - WikiNeural entity-vs-nonentity
- [ ] supersense or coarse semantic class where feasible
- [ ] semantic role labels if a clean token-level version is available
- [ ] event/entity type labels

### 5.5 Mixed or ambiguous tasks
These are especially important because they may tell us whether broad positional stripping collapses the apparent PCC signal.

- [ ] POS tagging
- [ ] dependency relation labels
- [ ] agreement features:
  - number
  - tense
  - person
- [ ] argument-role syntax labels where available
- [ ] attachment-sensitive labels
- [ ] scope-sensitive constructions

### 5.6 Current PCC tasks to remap under the new framing
- [x] `syntax_pos`
- [x] `syntax_dep_coarse`
- [x] `head_dir_dist`
- [x] `sem_wnut17_typeonly`
- [x] `sem_fewnerd_coarse_binary`
- [x] `sem_wikineural_en_binary`

For the updated program, each of these should be explicitly tagged as:
- [ ] primarily absolute-position-like
- [ ] primarily relative/structural-position-like
- [ ] primarily content-like
- [ ] mixed/ambiguous

---

## 6. Data Plan

### 6.1 Primary model/layer sites
- [ ] Primary site: `Pythia-160M`, `L3`
- [ ] Secondary site: `Pythia-160M`, `L4`
- [ ] Optional layer add-ons after initial read:
  - `L2`
  - `L5`
  - `L6`

### 6.2 Reuse of current project assets
- [x] Reuse the existing pre-K2 activation/probe infrastructure wherever possible.
- [x] Reuse the current `L3` checkpoints:
  - `g4`
  - `g5`
  - `g6`
  - `g7`
- [x] Reuse current `x_pos_priv`, `x_content_priv`, and residual outputs.
- [ ] Build new derived label tables and contrast metadata on top of existing activation dumps before launching any new model training.

### 6.3 Annotation sources
#### Gold / high-quality labeled corpora
- [ ] Universal Dependencies for POS, head direction, head distance, dependency labels, depth-like approximations
- [ ] OntoNotes or equivalent for syntax + NER + SRL if available in current environment
- [ ] WNUT17
- [ ] FewNERD
- [ ] WikiNeural
- [ ] BLiMP / SyntaxGym / controlled contrast data

#### Silver-scale labels
- [ ] Stanza or spaCy parses/tags for larger held-out corpora
- [ ] automatic NER / semantic tags where gold is too small
- [ ] keep a gold subset for calibration

### 6.4 Split design
- [ ] IID split
- [ ] source-holdout split
- [ ] corpus-holdout split
- [ ] matched-token split
- [ ] matched-position split
- [ ] matched-length split
- [ ] matched-template split for contrast sets

---

## 7. Track R — Reinterpret the Existing PCC Evidence

### Goal
- [ ] Re-read the completed A0/A1/A1b/A1c/B-light outputs through the new positional-family lens before launching new experiments.

### Key questions
- [ ] Which current “syntax” tasks are actually strongest candidates for **relative/structural positional** readouts?
- [ ] Does `syntax_pos` look more like true crossover or like undercaptured broad position?
- [ ] Does the sharp weakening of `syntax_dep_coarse` under matched-token control suggest lexical shortcut dependence, or does it suggest that current representations are missing the right relative-position abstraction?
- [ ] Does `g7 > g4` imply that stronger private/private regularization suppresses useful shared structure, or that it suppresses broad positional leakage the current K=2 split has not allocated correctly?

### Concrete outputs
- [ ] Write `analysis/pcc_reinterpretation_20260616.md`
- [ ] Build a task mapping table:
  - task
  - current family
  - likely absolute-position load
  - likely relative/structural-position load
  - likely content load
  - ambiguity note
- [ ] Record a short decision memo:
  - “position-family reinterpretation favored”
  - “genuine PCC still favored”
  - or “both remain plausible”

### Why this stage matters
- [ ] It prevents the project from running a large new experiment while still interpreting all joint gain as “shared syntax” by default.

---

## 8. Track P — Position-Family Observational Program (No New MSAE Training)

### Stage P0 — Label inventory and positional-family probe design

#### Goal
- [ ] Define the target families for the broadened positional program before any new gate or architecture claim.

#### Deliverables
- [ ] `prereg/pcc_positional_family_revision_v2.md`
- [ ] `analysis/position_family_labels/`
- [ ] `configs/pcc/position_family_probe_suite.yaml`

#### Concrete tasks
- [ ] finalize absolute-position label set
- [ ] finalize relative-position label set
- [ ] finalize structural-position label set
- [ ] finalize content label set
- [ ] tag each current PCC task into one or more of those families
- [ ] declare which labels are token-local only and which require relation-aware features

#### Minimum acceptance criteria
- [ ] every label family has:
  - a definition
  - a data source
  - a split policy
  - a shortcut-risk note

---

### Stage P1 — Raw-activation positional-family gate

#### Goal
- [ ] Test whether raw activations admit a broader **position-family vs content** separation than the current absolute-position-only gate.

#### Question
- [ ] Can a low-rank or modest-rank positional-family subspace explain:
  - absolute position
  - relative order
  - structural-position tasks
  while leaving behind a representation that is much better at content than at position-family prediction?

#### Inputs
- [ ] raw activations `x`
- [ ] absolute-position probes
- [ ] relative-position probes
- [ ] structural-position probes
- [ ] content probes

#### Candidate subspace construction methods
- [ ] stack probe weight vectors and run PCA/SVD
- [ ] CCA/PLS across positional tasks
- [ ] supervised multi-task linear encoder for positional-family labels
- [ ] compare separate `S_abs`, `S_rel`, `S_struct`, and combined `S_posfam`

#### Core comparisons
- [ ] `Proj_{S_abs}(x)`
- [ ] `Proj_{S_rel}(x)`
- [ ] `Proj_{S_struct}(x)`
- [ ] `Proj_{S_posfam}(x)`
- [ ] orthogonal complements of each

#### Primary outputs
- [ ] positional-family recovery curves
- [ ] content retention in positional complements
- [ ] principal angles between `S_posfam` and content subspaces
- [ ] cross-projection energy
- [ ] rank window where position-family is strongest and content leakage is lowest

#### Success signals
- [ ] broad position-family tasks are much better recovered from `S_posfam` than from the complement
- [ ] content tasks are much better recovered from the complement than from `S_posfam`
- [ ] syntax-like tasks move materially toward the positional-family side relative to the old absolute-position-only split

#### Failure signals
- [ ] `S_posfam` cannot be made meaningfully cleaner than the raw representation
- [ ] content collapses when broad positional-family is removed
- [ ] relative/structural position does not behave as a coherent family

#### Decision use
- [ ] If P1 is strongly positive, prioritize revised `K=2` all-position vs content before full PCC branch training.

---

### Stage P2 — Leakage audit on existing K=2 checkpoints

#### Goal
- [ ] Quantify how much absolute, relative, and structural positional information is still present in `x_content_priv` and `x_resid`.

#### Inputs
- [ ] `x`
- [ ] `x_pos_priv`
- [ ] `x_content_priv`
- [ ] `[x_pos_priv, x_content_priv]`
- [ ] `x_resid`
- [ ] positional-family labels from P0
- [ ] content labels from P0

#### Core questions
- [ ] How much absolute-position information is left in `x_content_priv`?
- [ ] How much relative-position information is left in `x_content_priv`?
- [ ] How much structural-position information is left in `x_content_priv`?
- [ ] How much semantic/content information is left in `x_pos_priv`?
- [ ] Does `x_resid` look more like missed position-family signal or like genuine interaction signal?

#### Metrics
- [ ] position leakage from `x_content_priv`
- [ ] content leakage from `x_pos_priv`
- [ ] residual selectivity index
- [ ] broad-position joint gain vs old absolute-position joint gain

#### Interpretation rules
- [ ] If `x_content_priv` retains strong relative/structural positional signal, then the current K=2 split is likely too narrow on the position side.
- [ ] If `x_content_priv` is already low-leakage on broad position but syntax joint gains remain, then genuine PCC becomes more plausible.

---

### Stage P3 — Shift-based counterfactual invariance suite

#### Goal
- [ ] Test whether the candidate content representation is stable under transformations that mainly move position, and whether the candidate positional-family representation moves in the expected direction.

#### Concrete transformation families
##### Mostly position-changing, semantics-preserving
- [ ] prepend neutral prefix tokens to shift absolute positions
- [ ] insert punctuation or formatting tokens that preserve broad proposition
- [ ] add or remove neutral appositive or filler phrases
- [ ] reorder clauses when broad meaning is preserved
- [ ] active/passive alternations where semantics is approximately preserved
- [ ] dative alternations

##### Mostly semantics-changing, structure-preserving
- [ ] entity substitutions under fixed template
- [ ] lexical substitutions matched on POS and inflection
- [ ] event/entity type substitutions with same surface skeleton
- [ ] role reversals in matched templates

#### Measurements
- [ ] branch activation shift magnitude
- [ ] cosine stability within each representation family
- [ ] positional-family probe shifts
- [ ] content-task probe shifts
- [ ] selectivity of change:
  - how much does candidate content move under positional-only transformations?
  - how much does candidate positional representation move under content-only transformations?

#### Success pattern for de-positioned content
- [ ] low change under mostly positional shifts
- [ ] higher change under content substitutions
- [ ] low recoverable position-family signal after transformation

#### Success pattern for a true positional-family branch
- [ ] high sensitivity to positional shifts
- [ ] lower sensitivity to lexical substitutions when structure is held fixed

---

### Stage P4 — Linear residualization and adversarial scrubbing baselines

#### Goal
- [ ] Test whether simple non-generative baselines can already create a useful de-positioned content representation.

#### Baseline families
- [ ] projection residual:
  - `x_depos_proj = x - Proj_{S_posfam}(x)`
- [ ] linear regression residual:
  - regress broad positional-family labels from `x`
- [ ] branch residualization:
  - regress broad positional-family labels from `x_content_priv`
- [ ] adversarial linear scrubber:
  - train a representation to retain content while suppressing positional-family labels

#### Why this matters
- [ ] If a simple baseline already removes most positional-family leakage while keeping semantic utility, then the project should not rush into a new PCC architecture.
- [ ] If simple baselines fail, that strengthens the case for a learned multi-branch model.

#### Concrete comparisons
- [ ] compare `x_content_priv` to `x_depos_proj`
- [ ] compare `x_content_priv` to `x_depos_regress`
- [ ] compare `x_content_priv` to `x_depos_adv`
- [ ] compare all of them on:
  - position leakage
  - semantic retention
  - syntax joint gain

---

### Stage P5 — Residual crossover audit after broad positional stripping

#### Goal
- [ ] Decide whether a real PCC signal remains after positional-family removal.

#### Representations to evaluate
- [ ] `x_depos_*`
- [ ] joint of `x_posfam` and `x_depos_*`
- [ ] low-rank bilinear interaction readouts over those representations
- [ ] residual proxy after subtracting both broad position and content models

#### Decision rule
- [ ] If syntax/relational tasks still show stable positive joint-only or bilinear-only gain after broad positional stripping, call that surviving signal a real PCC candidate.
- [ ] If the gains largely vanish, treat the original PCC story as mostly under-modeled positional structure.

---

## 9. Track C — Controlled Contrast and Counterfactual Audit

### Goal
- [ ] Use cleaner controlled transformations to distinguish:
  - syntax / structure changes
  - positional-family changes
  - content/semantic changes

### Contrast families
#### Structure-changing, broad-content-preserving
- [ ] active/passive
- [ ] dative alternation
- [ ] clefting
- [ ] topicalization
- [ ] relative clause movement
- [ ] constituent reordering

#### Position-changing, structure-minimizing
- [ ] neutral prefix insertion
- [ ] neutral suffix insertion
- [ ] paragraph-format padding
- [ ] sentence index shift within a concatenated context

#### Content-changing, structure-preserving
- [ ] entity substitutions
- [ ] event substitutions
- [ ] role reversals in fixed frame
- [ ] lexical substitutions matched on POS and morphology

### Measurements
- [ ] branch activation shift magnitude
- [ ] probe-score deltas by branch
- [ ] joint gain deltas
- [ ] causal branch-ablation effects on contrast discrimination

### Key interpretation goals
- [ ] determine whether current “syntax gain” is more sensitive to **broad positional-family changes** than to genuine meaning changes
- [ ] determine whether semantic families remain primarily content-private under the same controls

---

## 10. Track D — Model-Side Candidate Experiments

### Decision principle
Do **not** launch a new model family until the no-new-training observational program makes one of the candidate stories clearly preferable.

### D1 — Revised K=2: all-position vs de-positioned content

#### When to choose
- [ ] choose this if broad positional-family stripping explains most of the earlier syntax-like joint gain
- [ ] choose this if de-positioned content remains semantically useful

#### Model sketch
- [ ] branch 1:
  - `D_posfam`
  - smaller dictionary
  - low/moderate `TopK`
- [ ] branch 2:
  - `D_content`
  - larger dictionary
  - higher `TopK`

#### Concrete experiment
- [ ] initialize or regularize branch 1 using `S_posfam`
- [ ] compare directly against the current absolute-position K=2 model
- [ ] report:
  - broad position leakage
  - semantic retention
  - syntax joint gain
  - incoherence / FVU tradeoff

### D2 — K=3: absolute-position + relative/structural-position + content

#### When to choose
- [ ] choose this if broad positional-family is real, but clearly not well modeled as one coherent branch
- [ ] especially choose this if `S_abs` and `S_rel/S_struct` are only weakly aligned

#### Model sketch
- [ ] branch 1:
  - absolute-position
- [ ] branch 2:
  - relative/structural-position
- [ ] branch 3:
  - content

#### Concrete experiment
- [ ] compare whether syntax-like signal moves primarily into branch 2
- [ ] test whether content branch becomes cleaner than under revised K=2

### D3 — Interaction-on-top readout on frozen branches

#### When to choose
- [ ] choose this if broad positional stripping does not erase the residual joint signal, but a full additive shared branch still feels too assumption-heavy

#### Model sketch
- [ ] freeze existing K=2 or revised K=2 branches
- [ ] fit low-rank bilinear or factorized interaction readouts on top

#### Why this is attractive
- [ ] low-risk
- [ ] cheap
- [ ] directly tests whether interaction structure exists without changing the generative model

### D4 — Shared/private PCC model

#### When to choose
- [ ] choose this only if residual PCC survives broad positional-family stripping and interaction-on-top evidence is strong

#### Model sketch
- [ ] `x = x_pos_priv + x_content_priv + x_shared`
- [ ] `x_shared` is interpreted as shared/interaction-like only after evaluation

### D5 — Hierarchical content split

#### When to choose
- [ ] choose this if the evidence suggests the current content branch is a mixture of:
  - semantic-private content
  - structure-sensitive but not purely positional content

#### Model sketch
- [ ] stage 1:
  - broad positional-family vs content
- [ ] stage 2:
  - split the content side into semantic-private and structure-sensitive/shared subcomponents

---

## 11. Regularization Design

### Principle
- [ ] Do **not** assume the current K=2 symmetric private/private incoherence penalty is the right default for every revised architecture.

### Updated rationale
- [ ] Strong regularization may be appropriate between:
  - broad positional-family branch
  - content branch
- [ ] But if a real shared/PCC branch exists, forcing it to be strongly orthogonal to both private branches may destroy the very signal the branch is supposed to carry.

### Candidate regularization schemes
#### For revised K=2 all-position vs content
- [ ] no regularizer
- [ ] current quadratic incoherence
- [ ] smaller `lambda_inc` sweep:
  - `0`
  - `1e-3`
  - `1e-2`
- [ ] optionally:
  - `3e-2` if under/over-regularization becomes the question

#### For K=3 absolute/relative/content
- [ ] strong `lambda(abs, content)`
- [ ] moderate `lambda(rel, content)`
- [ ] weak or tuned `lambda(abs, rel)` because these branches may be related but not identical

#### For shared/private PCC
- [ ] strong private/private regularization
- [ ] weak or zero shared/private orthogonality
- [ ] optional usage incentives if shared branch collapses

### Required ablations
- [ ] no regularizer
- [ ] current quadratic cross-branch baseline
- [ ] revised pairwise penalty scope
- [ ] regularizer-strength sensitivity after the candidate architecture is stable

---

## 12. Causal and Counterfactual Tests

### Goal
- [ ] Move beyond probes and test whether candidate branches cause selective behavior changes.

### Ablation tests
- [ ] ablate broad positional-family branch
- [ ] ablate de-positioned content branch
- [ ] ablate residual/shared branch if one exists
- [ ] measure effect on:
  - absolute-position tasks
  - relative-position tasks
  - structural-position tasks
  - semantic/content tasks
  - mixed syntax tasks

### Transplant tests
- [ ] transplant positional-family codes across matched sentences
- [ ] transplant de-positioned content codes across matched frames
- [ ] transplant shared/PCC codes if a credible shared candidate is available

### Expected selectivity patterns
- [ ] positional-family transplant changes order/structure-sensitive behavior strongly
- [ ] de-positioned content transplant changes semantic content strongly
- [ ] shared/PCC transplant, if it exists, changes relational/syntax-sensitive behavior more than bare lexical identity or bare position

---

## 13. Metrics and Reporting

### 13.1 Observational metrics
- [ ] private-branch probe performance
- [ ] joint performance
- [ ] joint-only gain
- [ ] residual performance
- [ ] bilinear/interacting readout gain
- [ ] rank-recovery curves for:
  - absolute position
  - relative position
  - structural position
  - content
- [ ] principal angles among:
  - `S_abs`
  - `S_rel`
  - `S_struct`
  - `S_posfam`
  - content subspace
- [ ] CCA / PLS overlap among candidate representations

### 13.2 New key bridge metrics
- [ ] **position leakage score**
  - how much position-family signal can be recovered from the candidate content representation?
- [ ] **content retention score**
  - how much semantic/content performance remains after positional stripping?
- [ ] **shift invariance score**
  - how stable is the candidate content representation under mostly positional transformations?
- [ ] **structure sensitivity ratio**
  - how much more do candidate positional-family representations move under structure-changing than under content-changing transformations?
- [ ] **residual PCC score**
  - how much syntax/relational gain remains after broad positional stripping?

### 13.3 Training metrics
- [ ] total FVU
- [ ] branch-only error ratios
- [ ] branch energy ratios
- [ ] incoherence metrics between private branches
- [ ] overlap metrics involving any shared branch
- [ ] active latent fractions
- [ ] usage entropy / gini
- [ ] revival rate per M tokens

### 13.4 Causal metrics
- [ ] syntax drop under branch removal
- [ ] semantics drop under branch removal
- [ ] position-family drop under branch removal
- [ ] selectivity index for each branch
- [ ] transplant success / degradation scores

### 13.5 Reporting principles
- [ ] Keep the already-established Paper 1 result separate from new positional-family and PCC claims.
- [ ] Do **not** overstate the current K=2 result as already proving broad positional-family separation.
- [ ] Use “de-positioned content” rather than “pure content” unless the evidence becomes unusually strong.
- [ ] Do **not** call something a “syntax branch” unless the evidence clearly shows branch-level selectivity beyond general positional-family effects.

---

## 14. Seed, Holdout, and Stability Requirements

### Minimum standards before claiming broad positional-family separation
- [ ] at least `3` seeds for observational audits
- [ ] IID + source-holdout required
- [ ] corpus-holdout strongly preferred
- [ ] matched-token and matched-position controls required for publication-facing claims

### Minimum standards before claiming residual PCC
- [ ] broad positional-family stripping must already be in place
- [ ] residual joint/bilinear gain must survive:
  - seeds
  - holdouts
  - matched-token controls
  - matched-position controls

### Stability outputs
- [ ] pass/fail tables by:
  - task family
  - split
  - seed
  - rank
  - layer
  - representation family
- [ ] bootstrap CIs for key metrics
- [ ] threshold sensitivity for any new gates

---

## 15. Proposed Experiment Order

### Phase 0 — Freeze historical record
- [x] Freeze and archive the final outputs of the completed K=2 fastdata-stream wave.
- [x] Freeze the completed PCC A0/A1/A1b/A1c/B-light artifacts.
- [ ] Write a reinterpretation memo before any new model-side claims.

### Phase 1 — No-new-training reinterpretation and label build
- [ ] Track R reinterpretation memo
- [ ] Stage P0 positional-family label inventory
- [ ] task-family remapping of current PCC results

### Phase 2 — No-new-training positional-family audits
- [ ] Stage P1 raw-activation positional-family gate
- [ ] Stage P2 K=2 leakage audit
- [ ] Stage P3 shift-based counterfactual suite
- [ ] Stage P4 residualization/adversarial baselines
- [ ] Stage P5 residual-PCC audit after broad positional stripping

### Phase 3 — Minimal new model work
- [ ] D3 interaction-on-top readout on frozen branches if residual PCC survives
- [ ] D1 revised K=2 all-position vs content if broad positional-family explanation dominates

### Phase 4 — Higher-complexity model work
- [ ] D2 K=3 absolute/relative/content if broad positional-family exists but does not look single-branch
- [ ] D4 shared/private PCC model only if genuine residual PCC remains after broad positional stripping
- [ ] D5 hierarchical content split only if the content side still looks internally mixed after revised K=2

### Phase 5 — Regularization follow-up
- [ ] run targeted regularization studies only after a candidate architecture is justified

---

## 16. Decision Gates

### Gate PF-1: Is the current PCC story mostly under-modeled broad position?
Proceed toward revised `K=2` all-position vs content if:
- [ ] broad positional-family probes recover much more syntax/structure-sensitive signal than the old absolute-position-only setup
- [ ] `x_content_priv` shows substantial relative/structural position leakage
- [ ] simple broad positional stripping materially reduces the earlier syntax-like joint gain

Otherwise:
- [ ] do not conclude this yet

### Gate PF-2: Does a useful de-positioned content representation exist?
Proceed only if:
- [ ] semantic/content tasks remain strong after broad positional stripping
- [ ] broad position leakage drops sharply
- [ ] the representation remains stable under positional shifts

Otherwise:
- [ ] record that “pure” or strongly de-positioned content may not be a meaningful target at this site

### Gate PF-3: Does residual PCC survive after broad positional stripping?
Proceed toward true PCC/shared modeling only if:
- [ ] syntax/relational tasks still show stable positive joint-only or bilinear-only gain
- [ ] that gain survives controls and holdouts
- [ ] the gain is not obviously explained by leftover positional-family leakage

Otherwise:
- [ ] stop before launching shared-branch training

### Gate PF-4: Is one positional branch enough?
Proceed toward revised `K=2` if:
- [ ] `S_abs`, `S_rel`, and `S_struct` behave like one coherent family

Proceed toward `K=3 absolute/relative/content` if:
- [ ] absolute and relative/structural position separate materially from each other
- [ ] one position-family branch looks too compressed or unstable

### Gate PF-5: Is a trained new model justified?
Proceed only if:
- [ ] no-new-training evidence is already strong
- [ ] a concrete architecture choice is supported by the decision tree above
- [ ] the planned model comparison is specific enough to falsify the chosen story

---

## 17. Risks and Failure Modes

### Conceptual risks
- [ ] “pure content” may not exist cleanly in contextual residual activations.
- [ ] relative position may not be token-local and may require pairwise/window-aware features.
- [ ] syntax may not reduce to broad positional-family structure even if position matters a lot.
- [ ] broad positional-family stripping may remove useful semantic/contextual information accidentally.

### Experimental risks
- [ ] lexical shortcuts may masquerade as relative-position signal
- [ ] structural labels may be noisy or parser-dependent
- [ ] contrast-set transformations may accidentally change semantics while intended to change only structure or position
- [ ] prefix/suffix shift tests may introduce distribution shift artifacts

### Modeling risks
- [ ] forcing all broad positional structure into one branch may be too restrictive
- [ ] K=3 may be necessary but harder to stabilize than the current K=2 regime
- [ ] over-regularization may destroy shared or structurally positional signal

### Reporting risks
- [ ] overclaiming “syntax branch” when evidence only supports “position-family-sensitive” structure
- [ ] overclaiming “pure content” when evidence only supports “reduced position leakage”
- [ ] treating the existing PCC results as already decisive when they were collected under the narrower absolute-position framing

---

## 18. Immediate Next Actions

1. [ ] Write a short reinterpretation memo:
   - `analysis/pcc_reinterpretation_20260616.md`
   - map the completed A0/A1/A1b/A1c/B-light findings onto:
     - absolute-position-like
     - relative/structural-position-like
     - content-like
     - ambiguous
2. [ ] Create a prereg amendment / extension file:
   - `prereg/pcc_positional_family_revision_v2.md`
   - record that the bridge program now tests “broad positional-family vs de-positioned content” alongside classical PCC.
3. [ ] Build the Stage P0 label inventory and task manifest.
4. [ ] Launch Stage P1 raw-activation positional-family gate on:
   - primary `L3`
   - fallback `L4`
5. [ ] Run Stage P2 leakage audit on current checkpoints:
   - `g4`
   - `g5`
   - `g6`
   - `g7`
6. [ ] Build the Stage P3 shift/counterfactual pack:
   - neutral prefix insertion
   - neutral suffix insertion
   - active/passive
   - dative alternation
   - fixed-frame entity substitutions
7. [ ] Run Stage P4 linear residualization and adversarial scrubbing baselines.
8. [ ] Only after P1–P4 finish, decide whether Phase 3 should launch:
   - revised `K=2` all-position vs content
   - `K=3 absolute/relative/content`
   - interaction-on-top
   - true shared/private PCC model

---

## 19. Deliverables

- [ ] `analysis/pcc_reinterpretation_20260616.md`
- [ ] `analysis/position_family_labels/`
- [ ] `analysis/position_family_gate/`
- [ ] `analysis/position_leakage_audit/`
- [ ] `analysis/shift_counterfactuals/`
- [ ] `analysis/deposition_baselines/`
- [ ] `analysis/residual_pcc_audit/`
- [ ] `analysis/pcc_candidate_comparison/`
- [ ] `configs/pcc/`
- [ ] `prereg/pcc_positional_family_revision_v2.md`
- [ ] `reports/pcc_stageR.md`
- [ ] `reports/pcc_stageP.md`
- [ ] `reports/pcc_stageCounterfactual.md`
- [ ] `reports/pcc_model_decision.md`
- [ ] `reports/pcc_final_decision.md`
