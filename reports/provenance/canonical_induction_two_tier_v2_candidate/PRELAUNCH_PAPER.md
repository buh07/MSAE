# Potency Is Not Precision: Stable Representations Without Selective Control

## Manuscript status and evidence policy

This manuscript is a complete project-level synthesis of the MSAE position/content program, the
subsequent measurement-only relational investigations, and the prospective proxy-control benchmark
v2. It is not a preregistration, it does not alter any frozen
result, and it does not promote an exploratory or development result to confirmation.

Evidence is divided into four classes. **Valid** results met their applicable technical and
measurement gates. **Exploratory** results are scientifically informative but cannot support a
confirmatory or architecture-selection claim. **Technical-invalid** attempts diagnose the
measurement system and are not effect estimates. **Development-prescore** results concern parser,
support, and lifecycle feasibility before model inference. Every quantitative statement is linked to
the machine-readable claim ledger in `reports/paper_claim_ledger_v1.json`.

## Abstract

Transformer activations can encode a property without organizing it into a component that affords
selective behavioral control. We tested this distinction with linear projections and sparse
decompositions, first in a position/content case study and then in a prospective benchmark spanning
nine model--layer units, two model families, multiple decomposition classes, matched shams, direct
behavioral patching, and collateral-logit evaluation. [C049] The original decompositions reconstructed
well and converged to stable geometry, yet structural and lexical information remained mixed.
Measurement repairs subsequently separated support failure, numerical reproducibility, and genuine
specificity failure. In the prospective benchmark, synthetic ground-truth and oracle controls passed,
but no evaluated method achieved the complete conjunction of effect eligibility, cross-source
recovery, sham specificity, collateral safety, and model replication. [C050] Several components were
nevertheless potent: a behavior-gradient subspace recovered relative-position behavior, and lexical
PCA/delta subspaces moved their intended contrasts. Their collateral damage or weak representational
specificity prevented promotion. Simple position projections showed the opposite pattern—geometric
specificity with little behavioral recovery. Proxy metrics therefore tracked different axes of the
tradeoff: variance capture predicted potency while also predicting worse collateral safety, and
learned probe recovery predicted potency while predicting worse intervention specificity. [C053]
Across depth, behavioral leverage and collateral damage rose together. [C055] Capacity-swapped K2
assignments always followed the larger branch and all K2 variants remained nonspecific. [C056] The
supported conclusion is local rather than universal: stable, decodable directions at the tested sites
did not provide replicated, collateral-safe control. Encoding is not separability, and potency is not
precision.

## 1. Introduction

The original MSAE hypothesis was that a transformer activation could be decomposed into a
position-oriented component and a content-oriented component. This is stronger than saying that a
linear probe can predict token position or identity. A decomposition deserves semantic branch names
only if the assigned component retains the target signal, the nonassigned component excludes it, and
controlled target changes preferentially alter the assigned component.

The project consequently separates four questions:

1. **Encoding:** can a property be decoded from the activation?
2. **Recoverability:** can a reproducible representation or low-dimensional organization retain it?
3. **Selectivity:** is the information preferentially localized relative to leakage, nuisance, sham,
   and cross-family controls?
4. **Architectural warrant:** does the complete evidence justify training and naming separate
   representational branches?

The main empirical lesson is that answers to the first two questions can be positive while answers
to the last two are negative. This distinction resolves an apparent contradiction in the project:
the learned solutions are reproducible, but they are reproducibly mixed.

## 2. Scope and representational object

The main studies examine Pythia-160m-deduped activations at the frozen primary site selected by the
pre-K2 screen. Later studies use exact source, model, activation, and estimator freezes documented in
their own result envelopes. The strongest conclusion is restricted to the examined model, layer or
state, corpora, and linear protocols. The work does not establish a transformer-wide impossibility
result, and it does not test all nonlinear or multilayer organizations.

The original representational object was a single token activation. The K2 model passed the same
activation independently through two top-k sparse branches and summed their reconstructions. The
default position dictionary had 8,192 atoms with eight active atoms per token, whereas the content
dictionary had 32,768 atoms with 24 active atoms per token. The objective was reconstruction plus
sampled cross-decoder Gram incoherence; there was no position label, content label, paired
counterfactual, or branch-invariance term in training. [C004]

This design has two implications. First, “position” and “content” are post hoc names rather than
supervised semantics. Second, the content branch has substantially more dictionary and active-code
capacity. A mixed solution is therefore compatible with both the loss and the capacity allocation.

## 3. Experimental logic

### 3.1 Signal families

The project progressively distinguished:

- absolute token index and coarse absolute buckets;
- relative sequential position and quartile;
- boundary and available-prefix context;
- syntactic depth, dependency relation, and signed child--head distance;
- token and lemma identity, capitalization, named entities, and lexical substitutions;
- counterfactual responses to position shifts, document-context changes, lexical changes, and sham
  interventions.

The later interpretation deliberately avoids treating all of these as one “position” factor.
Absolute index, boundary distance, prior-context accumulation, and syntactic relations can be
correlated while arising from different mechanisms.

### 3.2 Evaluation hierarchy

Raw decodability is a prerequisite, not an endpoint. For task (t), assigned recovery measures how
much of the raw signal remains in the named component. Leakage applies the same frozen estimator to
the nonassigned component. Selectivity is assigned recovery minus leakage. A positive recovery value
with nonpositive selectivity means that the named branch contains the signal but does not own it.

Stability and specificity answer different questions. CKA measures geometric similarity across
checkpoints or sources. Counterfactual specificity asks whether an intended intervention changes the
assigned representation more than an inactive, random, nuisance, or cross-family intervention.
High CKA cannot substitute for specificity.

### 3.3 Resampling and independent support

The early row builders balanced token rows per class but did not guarantee that many independent
documents contained each class. That distinction matters because the inferential unit is the
document or document-disjoint component. Once a bootstrap draw omits a frozen class, the associated
classification statistic is undefined. The repaired protocols therefore treat independent-document
and class support as prescore requirements, preserve fixed folds within resampling, and report
endpoint-specific missingness rather than silently converting missing tasks into zero evidence.

### 3.4 Claim discipline

No favorable submetric can override a frozen conjunction. A positive probe is not promoted when its
matched specificity control fails. A technically invalid attempt is not counted as a negative
scientific result. A simple projection remains the primary comparator unless complete functional
evidence prospectively authorizes a learned representation model.

## 4. Chronological experimental record

### 4.1 Pre-K2 layer and rank screen

The pre-K2 suite screened candidate layers and low-rank task geometry before branch training. All
headline rank-8 and rank-16 rows passed across the registered split modes, totaling 92/92 passes. [C001]
None of the rank-32 boundary rows passed, totaling 0/46. The frozen primary recommendation was layer [C001]
3, with layer 4 as fallback. [C001]

This established a useful low-rank signal and a primary measurement site. It did not establish a
position/content decomposition, because the screen tested signal availability rather than selective
branch ownership.

### 4.2 Raw separable-information atlas

The raw atlas fit task-derived projections at the primary activation site. Its point diagnostics were
sharply asymmetric: lexical information could be placed in the positional complement, but positional
and structural information was not preferentially localized.

| Candidate | Assigned recovery | Leakage | Selectivity | Evidence class |
|---|---:|---:|---:|---|
| Split absolute position | 0.930 | 1.065 | -0.135 | exploratory [C002] |
| Split structural position | 0.863 | 0.989 | -0.126 | exploratory [C002] |
| Split lexical/semantic | 1.000 | 0.012 | +0.988 | exploratory [C002] |
| Broad absolute position | 0.935 | 1.068 | -0.133 | exploratory [C002] |
| Broad structural position | 0.979 | 0.991 | -0.013 | exploratory [C002] |
| Broad-complement lexical/semantic | 0.999 | 0.070 | +0.929 | exploratory [C002] |

All nine raw tasks were above analytic chance in the fixed-probe diagnostic. Representative
macro-F1 comparisons were 0.1165 versus 0.0623 for absolute-16 position, 0.5342 versus 0.2500 for [C003]
relative quartile, 0.4080 versus 0.1093 for signed head distance, 1.0000 versus 0.0251 for token [C003]
identity, and 0.6584 versus 0.1988 for named entities. The structural intervals nevertheless [C003]
depended on only five LinES documents. [C003]

The formal raw-atlas outcome was equivocal because the production path used fixed-probe document
resampling rather than the mandatory discovery-refit hierarchy and lacked the required collateral
audit. The point estimates were hypothesis-generating: lexical complement localization looked clean,
whereas a clean positional split did not.

### 4.3 K2 training

Four existing checkpoints were compared: three regularized seeds and a matched-seed no-incoherence
control. Their tail diagnostics were:

| Checkpoint | Regularizer | Tail FVU | Tail incoherence | Position active | Content active |
|---|---:|---:|---:|---:|---:|
| g4 | 0.01 | 0.076385 | 0.004643 | 0.8870 | 0.9112 [C004] |
| g5 | 0.01 | 0.071359 | 0.003150 | 0.8973 | 0.9257 [C004] |
| g6 | 0.01 | 0.073543 | 0.002811 | 0.8959 | 0.9346 [C004] |
| g7 | 0 | 0.069778 | 0.015200 | 0.9233 | 0.9298 [C004] |

The regularizer therefore reduced the logged cross-branch decoder incoherence while incurring only a
modest reconstruction cost. Those diagnostics show that optimization succeeded at its stated
objective. They do not show that the two branches acquired the intended semantics.

### 4.4 Initial K2 atlas and functional audit

The initial frozen-C2 fixed-probe audit was unfavorable to the semantic branch interpretation:

| Checkpoint | K2 selectivity | Simple projection | K2 minus simple | Total FVU |
|---|---:|---:|---:|---:|
| g4 | -0.103 | +0.304 | -0.407 | 0.0324 [C005] |
| g5 | -0.107 | +0.304 | -0.411 | 0.0504 [C005] |
| g6 | -0.146 | +0.304 | -0.450 | 0.0208 [C005] |
| g7 | -0.042 | +0.304 | -0.346 | 0.0258 [C005] |

All regularized checkpoints had negative point selectivity, and the no-incoherence control remained
negative as well. Reconstruction quality was not the limiting factor. The functional deletions were
also off-manifold and lacked the matched distance comparator needed for a localization claim, so this
audit remained exploratory rather than a formal negative result.

### 4.5 Atlas completion and the measurement stop

The first completion attempt produced every registered artifact, but only 414/500 draws were [C006]
scientifically finite. Eighty-six draws omitted at least one frozen sentinel class under the shared
document bootstrap. This was a data-support failure, not four independent model failures. [C006]

The calibration task counts exposed the same mechanism:

| Task | Finite draws | Main support issue |
|---|---:|---|
| Absolute position, 16 buckets | 316/500 | tail class concentrated in one document [C007] |
| Absolute position, eight buckets | 438/500 | tail class concentrated in two documents [C007] |
| Lemma identity | 320/500 | retained label in one document [C007] |
| Token identity | 314/500 | retained label in one document [C007] |

All four K2 result series inherited the same C2 bootstrap map and therefore had the identical
414/500 completeness. The joint stability vector required every family to be finite, so no full [C008]
stability draw survived even though individual structural CKA values existed. Specificity replay was
also invalid because independently recomputed Torch/GPU and NumPy/CPU reductions were compared at a
tolerance tighter than their ordinary discrepancy. [C008]

These failures motivated three lasting changes: prescore document/class feasibility, cached replay
through one reduction path, and endpoint-specific validity. The completion stop is evidence about
measurement design, not about whether the scientific decomposition is true.

### 4.6 Eligible measurement study

The repaired measurement v2.4 study was fully eligible and returned
`K2_broad_position_content_selective_not_supported`. [C009]

Relative quartile was strongly recoverable from the nominal position branch, but content retained an
equal or larger normalized signal: for g4, assigned recovery was 0.9318 and leakage was 1.0385. [C011]
same qualitative lack of selective ownership held across the regularized checkpoints. [C011]

Signed head distance localized even more poorly. The position-branch selectivity points ranged from
-0.4112 to -0.3353 across the reported regularized checkpoints, meaning that the nominal content [C010]
branch better supported this relational structural task. [C010]

Token identity was the clearest favorable branch result: content recovery was approximately
0.834--0.862 across the regularized candidates. Yet the required lexical cross-control did not pass, [C012]
so token-level probe localization did not establish complete functional specificity. [C012]

The document-context intervention preferentially affected the nominal position branch and replicated
across the regularized checkpoints. That is meaningful evidence that the branch responds
systematically to some context-linked change. It does not identify that response as absolute index,
boundary distance, coherent context accumulation, or a position-private causal mechanism, because
the cross-family control remained unfavorable. [C030]

Cross-checkpoint geometric similarity was extremely high: the learned mean pairwise CKA was 0.9983 [C013]
in the earlier recorded stability point. In the eligible study, same-branch CKA minima exceeded 0.995 [C031]
and branch-identity margins were positive but as small as 0.000131. These results establish [C031]
reproducible geometry and weak assignment identity, but they do not rescue the failed localization
and counterfactual-specificity conjunction. [C031]

The eligible study is the central result of the K2 program. It rules out the complete tested
conjunction, not the presence of position. The branch contains positional/contextual signal, but the
signal is not privately localized relative to content.

### 4.7 Numerical-QA attempts and analysis recovery

Several later attempts repaired approximate rotary-position translation QA. Attempts 7, 9, and 10
stopped in the technical protocol before executing the scientific atlas. They must not be counted as
three negative scientific replications. [C014]

Attempt 11 terminated during the science-analysis/overlay stage under a signed no-retry terminal. It
was preserved rather than resumed. [C026]

Attempt 12 was an explicitly exploratory, analysis-only successor that imported frozen caches and
validation artifacts by exact hash. It completed, but its frozen outcome was technically ineligible
and every candidate organization was ineligible. Favorable task-level or relation-level values could
therefore not nominate an architecture. [C015]

The methodological lesson is narrow: numerical replay, repeated live inference, and approximate RoPE
equivariance are distinct technical properties. Repairing them enabled interpretation of later
eligible studies, but did not rescue a failed specificity endpoint.

### 4.8 Relational syntax

Attempt 13 separated relational syntax from broad position. It tested dependency depth, coarse
dependency relation, and signed head distance using true child--head objects against child-only,
matched sham-head, and sequential-offset controls in both transfer directions. Its primary module
was measurable but failed the all-task recovery-and-isolation conjunction, yielding
`RELATIONAL_DECODABILITY_NOT_DEMONSTRATED_FOR_ALL_PRESPECIFIED_TASKS`. [C016]

Coarse dependency relation illustrates the encoding--specificity gap. True-pair macro-F1 was 0.6513 [C027]
from CTETEX to GENTLE, but the sequential-offset control reached 0.6593. In the reverse direction, [C027]
true-pair macro-F1 was 0.6573 while the sham reached 0.6645. [C027]

Thus some relational labels were detectable, but the true relation did not consistently contribute
information beyond matched alternatives. Dependency depth and signed distance also failed their
complete prespecified vector. The appropriate summary is:

> Cross-corpus relational information was detectable, but strong recovery and relation-specific
> isolation were not demonstrated.

This is an exploratory negative for the tested child/head linear representation, not evidence that
syntax is absent from the model.

### 4.9 Final context-versus-local falsification

Attempt 14 asked the strongest remaining position-related question: whether controlled changes in
available prior context preferentially affect a transferable subspace after matching lexical changes
and unrelated-context disruption. It used 136 supported 3LB components and 648 supported CESS
components under the frozen protocol. [C028]

The learned-from-one-source linear subspace transferred in both directions. Context capture was
0.1620 and 0.1917. Context assignment was 0.1256 and 0.1515; reciprocal lexical assignment was [C017]
0.1816 and 0.2406; lexical-complement preservation was 0.9634 and 0.9607. [C017]

The decisive coherent-versus-unrelated specificity margin was only 0.0087 in one direction and [C018]
0.0136 in the other, below the frozen material margin. Gate 4 failed in both directions. [C018]

The raw magnitudes explain why. In 3LB, the median true-context change was 0.2567 and the unrelated [C028]
change was 0.2540. In CESS, the corresponding values were 0.2485 and 0.2456. The projection therefore [C028]
captured a reproducible response to changing the prefix, but nearly the same response occurred when
the supplied context was unrelated. [C028]

The formal decision was
`CONTEXT_DETECTABLE_BUT_NOT_CLEANLY_SEPARABLE_AT_THIS_LAYER`. [C019]

Attempt 14 did not train a supervised context/local model. It is therefore incorrect to say that the
projection matched, beat, or replaced a learned comparator. The valid statement is that the frozen
projection transferred but failed the prerequisite functional-specificity gate.

### 4.10 Exploratory proxy-to-control benchmark

A separately versioned benchmark broadened the evaluation to nine model/layer units spanning two
model families, early/middle/late sites, imported K1 and K2 checkpoints, frozen linear bases, two
controlled transfer directions, and three concepts. It produced 918 method-level rows and explicitly
remained exploratory with no automatic claim. [C042]

Under the frozen v1 metric, probe recovery predicted raw behavioral recovery with rho 0.5391 but not [C043]
sham-adjusted behavioral specificity, rho -0.0865 with a cluster interval crossing zero. CKA similarly [C043]
predicted recovery at rho 0.5032 while its specificity interval crossed zero. [C043]

Post-result review found that the frozen specificity denominator used the absolute natural effect,
reversing the interpretation when the natural effect was negative. A create-once cached companion
left v1 untouched and aligned the score to the signed counterfactual. Within learned methods, probe
recovery then associated with aligned specificity at rho 0.4058, cluster interval [0.2200, 0.5639], [C044]
and CKA at rho 0.3713, interval [0.1889, 0.4982]. These are exploratory sensitivities, not replacements [C044]
for the frozen endpoint. [C044]

The most robust dissociation concerned safety. Within learned methods, probe recovery associated with
collateral safety at rho -0.6005 and CKA at rho -0.7075; both cluster intervals were wholly negative. [C045]
Thus the proxies selected increasingly potent components, but potency came with broader nonanswer-logit
disruption rather than clean precision. [C045]

Depth sharpened the same tradeoff. From early to late sites, probe recovery increased from 0.7266 to [C046]
0.8613 and CKA from 0.6384 to 0.8365, while leakage increased from 0.7105 to 0.9681, selectivity fell [C046]
from 0.0160 to -0.1069, behavioral recovery rose from 0.0073 to 0.1055, and collateral KL rose from [C046]
0.0004 to 0.0502. [C046]

Branch identities exposed the capacity mechanism. The asymmetric and capacity-swapped K2 variants
selected the larger branch in 100% of rows and assigned all three concepts to that same branch. The [C047]
equal-capacity K2 assigned one global branch identity in only 11.1% of model/layer/seed/source cases [C047]
and agreed across assignment sources in 59.3%. [C047]

The companion performed zero new model forwards and labels its eight reconstructed v1 nuisance cycles
as post hoc sensitivity groups rather than independent experimental support. [C048] The formal claim
review therefore rejects the broad statement that standard proxies never predict control. The supported
formulation is narrower:

> **Potency is not precision.** Decoding and stable geometry can identify behaviorally influential
> components while failing to guarantee semantic ownership or collateral-safe manipulation.

### 4.11 Prospective proxy-to-control benchmark v2

V2 preserved the exploratory v1 result and prospectively corrected its main limitations. It froze
signed alignment to the natural counterfactual, nontrivial shams, disjoint development/test template
families, component-block resampling, method-class-specific proxy definitions, a behavior-gradient
oracle, and a synthetic precondition. The synthetic ground-truth and behavior-oracle controls passed,
while the random negative remained below its cap. Across nine model--layer clusters, v2 produced
1,296 metric rows: 972 controlled and 324 naturalistic summaries. [C049]

The primary result was a joint failure rather than an absence of signal. None of 90 [C050]
method--concept--stage decisions passed, and none of 972 controlled method summaries simultaneously [C050]
cleared effect eligibility, recovery, signed sham specificity, and collateral safety. [C050] This
zero is not an equivalence claim: several component effects were materially positive, but no method
replicated the complete conjunction across both transfer directions and the required models.

Relative position exposed the tradeoff most directly. The behavior-gradient oracle recovered 0.330 [C051]
of the natural behavioral effect, hierarchical interval [0.104, 0.620], and its signed behavioral [C051]
specificity was 0.319 [0.090, 0.673]. Its collateral KL was 0.058 [0.019, 0.131], above the frozen [C051]
safety cap. [C051] Task projection and linear erasure instead achieved representational intervention
specificity of 0.234 and 0.239, respectively, with collateral KL near 0.005, but behavioral recovery [C052]
was only 0.008 and 0.011. [C052] The same activation therefore admitted precise but behaviorally weak
directions and potent but behaviorally broad directions.

Proxy associations sharpened that distinction. Within linear methods, captured variance associated
with behavioral recovery at rho 0.389 and signed behavioral specificity at rho 0.391, but with [C053]
collateral safety at rho -0.568; all three hierarchical cluster intervals excluded zero. [C053]
Within learned methods, probe recovery associated with behavioral recovery at rho 0.241 but with [C054]
intervention specificity at rho -0.321. Geometric stability associated negatively with behavioral [C054]
recovery, rho -0.254, and intervention specificity, rho -0.492. [C054] Reconstruction-quality
intervals were inconclusive. Learned sparsity was undefined as an association because every imported
method had the same total active-code budget; it is unavailable rather than null.

Depth produced a potency--damage gradient. Learned-method recovery increased from 0.001 at early sites [C055]
to 0.089 at late sites while collateral KL increased from 0.002 to 0.059. Linear-method recovery rose [C055]
from 0.003 to 0.142 while collateral KL rose from 0.001 to 0.042. [C055] Later states offered more
behavioral leverage, but that leverage was less collateral-safe.

Equalizing capacity did not rescue K2. Relative-position intervention specificity was -0.409 for [C056]
equal K2, -0.636 for asymmetric K2, and -0.636 after swapping capacities. The asymmetric and swapped [C056]
variants selected whichever branch was larger in every assignment. [C056] The capacity asymmetry
therefore explains branch identity, but its removal does not create semantic ownership.

The naturalistic QA endpoint was descriptive rather than confirmatory. Its mean effect eligibility
was 0.654, below the frozen 0.80 requirement. [C057] It cannot establish natural-domain replication,
even though some descriptive recovery was positive. The formal closure consequently authorizes no
new K2, shared-branch, context/local, or supervised-controller training under the current program.
[C058]

![Frozen v2 gate waterfall](results/proxy_control_benchmark_v2_analysis_20260808/gate_failure_waterfall.png)

![V2 recovery--collateral frontier](results/proxy_control_benchmark_v2_analysis_20260808/recovery_collateral_pareto.png)


### 4.12 Released-method joint-controllability benchmark v3

The separately frozen v3 benchmark compared released public SAEs, DiffMean/CAA, paired-delta SVD,
task projection, LEACE, PCA, random subspaces, a rank-one behavior-gradient comparator, and a
closed-form supervised skyline across GPT-2, Pythia-160M, and Gemma-2-2B. Seven model-layer workers
completed 51,456 component-level measurements. The prespecified synthetic positive-control gate
passed: the constructed ground projector and skyline achieved recovery and specificity of 1.0, [C062]
while the random control's specificity was 0.0585. [C062] This validates recovery of that constructed
linear mechanism, not the natural task or the complete real-model evaluator.

The naturalistic continuation endpoint was structurally ineligible. Across the 14 unique
model-layer/transfer task cells, only 60.9--78.9% of examples exceeded the frozen behavioral-effect [C063]
floor, versus 80% required, and every cell failed the frozen matched-sham rule. [C063] Unrelated natural
prefixes often moved the output nearly as much as coherent prefixes. Consequently, zero method-level
joint decisions passed, but this is not evidence that all evaluated methods failed: the common task
gate failed before they could be adjudicated.

The method measurements remain exploratory. Across 134 matched low-to-high budget triplets,
collateral damage increased in all 134, while recovery increased in 90 and signed specificity in
105. We therefore describe an exploratory potency/specificity--collateral-safety association, not a
confirmed potency--precision law. WIKI_A and WIKI_B are document-disjoint partitions of Wikitext,
so their transfer is within-corpus rather than cross-domain. The original aggregate crashed only
while serializing a NumPy Boolean; an analysis-only, exact-hash recovery reproduced the frozen
calculation without model forwards and preserved the failed namespace unchanged. The recovery also
records that the bootstrap helper was omitted from the original freeze and bound only after the
crash; the bootstrap-independent task-ineligibility conclusion does not depend on that omission.

### 4.13 Prospective naturalistic endpoint qualification v6.2

A separately versioned endpoint study tested counterbalanced arbitrary key--value retrieval and
controlled subject--verb agreement before permitting any representation-method comparison. The
technically repaired run completed all six development workers under the exact freeze. Retrieval
failed all model--source--template cells and qualified zero model families; confirmation therefore
remained closed. [C059]

Agreement produced high development-panel target potency: 745/768 GPT-2 rows, 621/768 Pythia rows, [C060]
and 663/768 Gemma rows met the registered directional and effect floor. [C060] Potency did not yield
prompt-robust precision. Only the GPT-2 ``beside'' template passed in both opened sources, while the
source-level nuisance-ratio points were 0.219 and 0.233 for GPT-2, 0.365 and 0.432 for Pythia, and [C060]
0.356 and 0.407 for Gemma. [C060] Agreement was consequently `TEMPLATE_CONDITIONED`, and no model
family cleared the all-source/all-template hierarchy. [C060]

The frozen outcome was `BOTH_ENDPOINTS_STOP`. Confirmation was not opened, representation methods
were not evaluated, and no training occurred. [C061] This is an endpoint-qualification result, not a
method-level negative: it shows that these two candidate behaviors did not provide a sufficiently
replicated, sham-specific adjudication target at the pinned checkpoints. The current retrieval and
agreement endpoint-development line is closed; a future study must change to an established
mechanism/task or a separately versioned representational object rather than tune another prompt
variant. [C061]

### 4.14 Established-task qualification: IOI v1

A separately frozen successor replaced retrieval/agreement prompt development with an
indirect-object-identification task and a prospective end-to-end full-residual positive control.
IOI counterfactual behavior was substantial: 227/256 GPT-2 rows, 172/256 Pythia-160M rows, and all [C064]
256/256 Gemma-2-2B rows met the registered bidirectional effect criterion. [C064] Complete
directional support did not imply cross-template sham robustness. GPT-2 and Gemma each qualified
one of four development templates, Pythia qualified none, and the registered every-template
hierarchy consequently qualified no checkpoint or model family. [C064]

The formal outcome is an upstream development qualification stop, not a failure of the causal
pipeline. All full-residual patch workers stopped before model loading, confirmation remained
sealed, and neither representation methods nor training were run. [C065] Thus intervention
recovery, intervention specificity, and performance of released methods remain unknown.

All three model logs also emitted PyTorch warnings that exact CuBLAS determinism was not guaranteed
because `CUBLAS_WORKSPACE_CONFIG` was unset. [C066] The multiple-template overall stop was not a
single borderline comparison, but exact bitwise reproducibility of the reported forward-derived
metrics must not be claimed. Future GPU studies set this variable before Python starts and require
repeated-inference agreement prospectively.

### 4.15 Canonical induction-head qualification v1.1

A separately frozen repeated-token study replaced natural-language prompt qualification with an
externally fixed GPT-2 induction-head pair and exact deterministic CUDA QA. All 128 development [C067]
rows were informative, and every one of the eight generated-token blocks contributed 16 rows. [C067]
The pair's source-edge attention was 0.908 with an attention advantage of 0.632 over the frozen [C067]
same-layer controls. Repeated logits and captured head outputs were bitwise identical on the [C067]
registered QA rows. [C067]

Jointly zeroing the pair reduced the clean target-versus-contrast margin by 0.702, with a 0.666 [C068]
differential contribution relative to zeroing the control pair. These are pair-level, graded
logit-margin effects: they do not establish that either head is individually necessary. [C068]

Clean-donor patching produced positive but materially insufficient recovery. The normalized [C069]
recovery point was 0.140 against the frozen 0.25 requirement, and clean-versus-sham selectivity was [C069]
0.086 against the frozen 0.15 requirement. The formal result was therefore `DEVELOPMENT_STOP`; [C069]
confirmation remained sealed and no representation method or training was evaluated. [C069]

The correct interpretation is narrow. On a fully supported assay, the prespecified pair exhibited
strong source-edge attention and a clear joint ablation contribution, while its final-token output
patch was reliably helpful but insufficiently potent and selective to validate the complete
technical positive control. This is evidence that causal contribution need not imply sufficient
control; it is not evidence against SAEs, projections, or linear controllers, which were untested.

## 5. Integrated interpretation

### 5.1 What is positive

The project contains several genuine positive results:

- low-rank positional, lexical, and syntactic task signals are available at the examined state;
- relative-quartile information is highly recoverable from the nominal position branch;
- token identity is highly recoverable from the nominal content branch;
- document-context interventions cause a reproducible branch-asymmetric response;
- learned decompositions converge to nearly identical checkpoint geometry;
- across the exploratory multi-model benchmark, recovery and CKA predict behavioral potency;
- in prospective v2, relative-position and lexical subspaces produced genuine behavioral movement;
- simple relative-position projections showed geometric specificity with low collateral damage;
- a frozen context-difference subspace transfers across two sources;
- some true child--head objects decode dependency relation well.

These results exclude the trivial explanation that the learned branches are random or that the
activation lacks position/context/syntax information.

### 5.2 What is negative

The failures concern ownership and functional specificity:

- structural information often appears more recoverable from content than from position;
- relative position leaks at least as strongly into content;
- lexical localization does not survive every cross-family functional control;
- same-branch geometric recurrence was not distinguished from branch swapping or shared geometry;
- true child--head representations did not consistently beat sequential or sham controls;
- coherent prior context did not materially beat unrelated-prefix disruption;
- proxy-selected potency increased together with leakage and collateral behavioral disruption.
- no v2 method jointly passed recovery, signed sham specificity, collateral safety, transfer, and
  model replication;
- the behavior-gradient oracle gained relative-position potency without collateral-safe precision;
- equal-capacity and capacity-swapped K2 variants remained nonspecific.

The strongest supported conclusion is therefore conditional and local:

> At the examined Pythia activation site and under the tested linear objects, robustly encoded
> positional, contextual, and syntactic information did not form clean, independently manipulable
> position/content modules.

### 5.3 Why a stable mixed solution is plausible

**The objective does not name the factors.** Reconstruction requires the sum of both branches to
match the activation. Decoder incoherence reduces average geometric overlap, but it does not penalize
code dependence, branch-output covariance, conditional structural leakage, or the use of a small
number of functionally important shared directions.

**Capacity is asymmetric.** The larger content dictionary and active budget can cheaply absorb
structural correlates. Increasing incoherence or adding more content capacity would not correct the
absence of semantic supervision.

**The candidate factors are statistically coupled.** Token identity predicts punctuation,
morphology, typical syntactic role, and sentence position. Available context depends on index and
boundary distance. Syntax is expressed through relations between tokens. Zero marginal leakage is
therefore neither realistic nor necessarily desirable; conditional and counterfactual selectivity is
the more informative target.

**The activation is already integrated.** By the examined layer, attention and residual mixing have
combined token-local and prior-context information. A linear projection may capture directions that
respond to any prefix disruption without distinguishing coherent accumulation from unrelated input.

**The representational object may be wrong.** Dependency relation is a property of an ordered pair or
attention edge, not solely of one token vector. Concatenating two residuals can still leave lexical
and sequential shortcuts dominant. Link logits, transported values, or attention-head outputs are
more direct relational candidates, though none is automatically causal.

**Decoding is permissive.** A probe needs only a predictive direction. A module requires privileged
response under intervention, exclusion of matched alternatives, transfer, and preservation of other
functions. The latter is a much stronger requirement.

**Behavioral leverage is not ownership.** A direction aligned with an output gradient can move the
target log-odds while also moving many unregistered logits. Conversely, a low-dimensional projection
can isolate a counterfactual activation difference yet be ignored by the downstream computation.
V2 observes both cases, making potency and precision separate empirical axes rather than synonyms.

## 6. Measurement engineering lessons

### 6.1 Rows are not independent support

Large balanced token tables can hide a class that occurs in one document. Resampling such a table at
the document level makes finite-draw failure nearly deterministic. Future protocols must prescore
documents containing each retained class, cap each document's contribution, and make low coverage an
eligibility failure rather than repeatedly reject-sampling favorable maps.

### 6.2 Missingness is not instability

A missing position task should block a global position/content architecture decision, but it should
not relabel a finite structural CKA as zero stability. Task measurability, family localization,
family stability, collateral validity, and counterfactual validity should be independently reported.

### 6.3 Replay is not equivariance

Exact cached replay validates hashes, row alignment, and analysis replay. Repeated inference measures
kernel reproducibility. A translated RoPE position-ID run measures approximate equivariance. These
should not share one exact coordinatewise tolerance, and an endpoint that does not depend on position
translation should not be erased by a failure of that control.

### 6.4 Gates must track scientific impact

One benign numerical tail should not invalidate many unrelated endpoints merely because the panel is
large. Numerical criteria should be normalized, prospectively calibrated on development data, and
connected to downstream nomination stability. Fresh validation must remain untouched after the gate
is frozen.

### 6.5 Support is not covariate overlap

Document-disjoint component counts and pair counts establish that an estimator has independent raw
material. They do not establish that true edges and controls are comparable. Relational measurement
v4 recovered structural support under less restrictive matching, yet morphology-value imbalance and
poor propensity overlap remained. The study therefore distinguishes two failure modes that a single
“eligible” flag can obscure: insufficient observations versus failure of the target/control
positivity and balance assumptions.

## 7. Relational-object successor

### 7.1 Why the successor is a new question

The position/context architecture line is formally closed, and no learned projection-comparator claim
is authorized. [C020]

The new question is whether changing the object from one token to an ordered dependency edge yields
cross-source recovery and relation-specific local functional evidence. It is not another K2 retry and
cannot alter Attempts 13 or 14.

Relational Attention-Edge Discovery 1 retired at prescore because an overbroad exposure audit
propagated hashes from already-excluded short-sentence collisions. It performed no model forward,
endpoint scoring, or training and therefore produced no representation result. [C032]

Its signed terminal was not retried. Discovery 2 then exposed a different parser defect: it rejected a valid
sentence-initial `0.1` enhanced empty node and stopped before any scientific forward or score. [C021]

### 7.2 Specification-conformant parser

A new isolated CoNLL-U parser now distinguishes integer token IDs, multiword-token ranges, and empty
nodes, including sentence-initial and ordinary decimal IDs. The test matrix covers malformed and
nonmonotone IDs, missing sentence separators, truncated files, reference validity, tree constraints,
line endings, and clean-EOF behavior under separately named strict and reader profiles.

The strict parser passed all 14 hashes in the opened-development manifest and both exact files in the
planned forward panel. [C022]

The parser and relational harness suites passed 53 tests before the prescore decision. [C023]

Opened corpora are development-only. Parser validation is technical evidence and cannot serve as
scientific confirmation.

### 7.3 Planned relational objects and controls

The prospectively reviewed study compares ordered child--head residual concatenations, ordered
differences, scaled rotary query--key link features, attention mass, and transported values. The
primary baseline is a frozen deterministic combination of token-pair residuals, lexical hashes,
morphology, punctuation, and sequential geometry. Learned representation training is prohibited
unless a complete nonlearned path first passes cross-source recovery, incremental value, and matched
functional edge specificity. [C029]

Matched nonedges exclude direct and ancestor/descendant relations and are balanced on causal
orientation, surface gap, endpoint grammatical features, tokenization geometry, and context length.
Functional tests compare true edges with matched nonedges after conditioning on original attention
mass and lexical/geometry nuisances. Attention features remain observational unless an explicitly
local intervention demonstrates a specific effect.

### 7.4 Adversarial fix and prescore stop

The first prepared matcher encoded morphology attribute presence but not values, allowing, for
example, nominative and accusative endpoints to match. Adversarial review blocked the run. The matcher
and nuisance baseline were corrected to use fixed morphology values before any model load.

Under the corrected control, English EWT retained 150 document-disjoint components and 500 balanced
pairs, but Latvian-LVTB retained only 77 components and 196 pairs. The latter failed the frozen
cross-source support floor, so the signed terminal stopped the study before model inference. [C024]

No opening, model-weight load, model forward, endpoint score, neural training, representation
training, or fresh scientific-corpus access occurred. A third opened source could not be substituted
after the prespecified source choice, and no retry is authorized. [C025]

This is the correct result of the additional research program: the parser and analysis harness are
ready for future use, but the intended two-source development experiment is scientifically
under-supported after proper nuisance control. There are no relational-object effect estimates to
report.

### 7.5 Relational Objects v3: broader source-pool feasibility

A separately versioned, explicitly outcome-informed successor then tested whether the support problem
could be resolved without changing the corrected matcher. It froze eight already-opened development
files spanning Czech, Spanish, English, Latvian, Ukrainian, and Arabic sources. All eight exact files
passed strict CoNLL-U parsing with no parser failure. [C033]

The label/tokenizer-only feasibility scout was rebuilt twice and the canonical reports were
byte-identical. It loaded no model weights and computed no activation or endpoint outcome. [C036]

The final capped support was:

| Opened-development source | Components | Balanced pairs | Eligible |
|---|---:|---:|---:|
| Czech PDT | 150 | 405 | no [C034] |
| Spanish AnCora | 150 | 356 | no [C034] |
| English EWT | 150 | 500 | yes [C034] |
| English GUM | 97 | 500 | no [C034] |
| Latvian LVTB | 77 | 196 | no [C034] |
| Ukrainian IU | 14 | 43 | no [C034] |
| Arabic PADT | 8 | 16 | no [C034] |
| English GENTLE | 12 | 219 | no [C034] |

Only EWT cleared every frozen support floor. Czech and Spanish had many document-disjoint components
but still produced fewer than 500 exact-stratum pairs; GUM produced 500 pairs but only 97 independent
components. The remaining sources were substantially below one or both floors. [C034]

Because the protocol required two eligible sources, v3 terminated at prescore. No study opening,
model-weight load, model forward, endpoint score, training, or fresh-source access occurred. [C035]

This is again not a negative result about QK logits, transported values, or attention heads: those
objects remain unmeasured. It is stronger feasibility evidence that the current combination of exact
morphology-value, tokenization, sequential-geometry, causal-orientation, and document-disjoint
matching is unusually demanding across available corpora. Repeated source substitution under this
same design is therefore unlikely to be an efficient route to strengthening the scientific paper.

### 7.6 Relational measurement v4: support recovered, overlap failed

Relational measurement v4 was a separately frozen, opened-development comparison of the exact-v3
reference matcher, prespecified coarser morphology strata, and optimal caliper matching. It preserved
the v3 scientific objects and did not inspect any representation outcome. The exact reference left
only English EWT structurally eligible, whereas both alternative matchers recovered the frozen
component and pair support in Czech PDT, English EWT, Latvian LVTB, Spanish AnCora, and Ukrainian IU:
one versus five supported sources. [C037]

| Matcher | Sources clearing structural support | Sources clearing all balance and overlap gates | Synthetic panels scheduled |
|---|---:|---:|---:|
| Exact-v3 reference | 1 [C037] | 0 [C038] | 0 [C038] |
| Coarse exact | 5 [C037] | 0 [C038] | 0 [C038] |
| Optimal caliper | 5 [C037] | 0 [C038] | 0 [C038] |

The alternative matchers solved a sample-quantity problem, not the comparability problem. Coarse
exact matching continued to fail prespecified morphology-indicator balance and propensity-overlap
criteria. Optimal caliper matching produced substantially better continuous-covariate balance, but
every structurally supported source still failed at least one morphology-indicator and propensity
criterion. [C039]

The signed terminal was `STOP_MEASUREMENT_DESIGN_UNCALIBRATED`: no source was selected, the
nomination remained null, and the simulation map was empty. “Uncalibrated” here means that no real
panel was eligible to calibrate the estimator; it does not mean that a synthetic estimator was run
and failed. [C038]

The study accessed neither model weights nor activation caches, ran no model forward or training,
and did not authorize a learned model or fresh-data relational scoring. [C040] Six scaler warnings
were retained in the execution record. They occurred during panel preparation and diagnostic
reconstruction; all serialized scientific outputs passed the frozen finite-value checks and the
signed terminal verifier, so they are a disclosed numerical-QA observation rather than a reason to
reinterpret the stop. [C041]

V4 is therefore a measurement-development result, not evidence for or against child--head
concatenations, differences, rotary QK links, attention-head outputs, or transported values. It also
closes the proposed v5 route under the frozen rule: because the prerequisite was two independently
eligible development sources and the observed count was zero, fresh relational science and learned
relational training are not authorized. [C038] [C040]

## 8. Decisions and future work

### 8.1 Decisions supported now

1. Stop training the existing K2 architecture. More seeds would repeatedly test convergence to a
   mixed solution rather than repair semantic supervision.
2. Preserve all unfavorable gates and signed terminals. Do not drop signed head distance, low-norm
   rows, morphology values, or matched controls after seeing their effects.
3. Do not train a supervised context/local or private/private/shared model. The functional evidence
   required to justify those architectures is absent.
4. Write the main paper around the encoding--separability distinction.
5. Preserve relational measurement v4 unchanged and do not authorize v5 relational science. Its
   formal result is a balance/overlap stop, not a representation outcome. [C038] [C040]
6. Preserve proxy-control v2 unchanged and close the current architecture program. Its positive
   potency estimates do not override the complete joint failure, and no current-program training is
   authorized. [C058]
7. Preserve behavioral endpoint v6.2 and close the current retrieval/agreement endpoint-development
   line. Do not promote one template, change the gates, open confirmation, or evaluate methods under
   that namespace. [C061]
8. Preserve IOI v1 as a development-qualification stop. Do not promote its favorable templates,
   run the blocked patch stage, open confirmation, or describe the positive-control pipeline as
   failed. [C064] [C065]
9. Preserve canonical induction v1.1 as a formal development stop. Do not lower its recovery or [C069]
   selectivity gates, open confirmation, add heads based on its opened rows, or authorize methods. [C069]

### 8.2 Conditions for any new edge program

V4 has now tested the prespecified coarser-stratum and optimal-caliper alternatives. They recovered
structural support but did not yield a single balance-and-overlap-eligible source. [C037] [C038]
Neither lowering the frozen gates nor adding corpora until two pass is a legitimate continuation.
There is no authorized v5 relational study.

Any further edge program must pose a genuinely new estimand rather than retry v4. A possible route is
prospective conditional adjustment, residualization, or overlap weighting with explicit positivity
diagnostics, first calibrated on synthetic known-positive and known-negative data and developed only
on already opened corpora. It must explain how morphology and lexical imbalance are controlled, cap
per-document influence, and demonstrate recovery without depending on a few documents. If that work
cannot produce two independently adequate development sources, the available corpora cannot answer
the question cleanly and the program should stop.

Only a separately versioned study that clears that development prerequisite may reserve fresh
scientific corpora and freeze the parser profile, pair builder, object equations, nuisance baseline,
bootstrap, thresholds, implementation hashes, and lifecycle before model inference. Confirmation
would still require both transfer directions, true-edge improvement over child-only features,
matched nonedges and sequential-distance controls, and local functional specificity with lexical and
unrelated-context invariance. Only that complete evidence could authorize an equal-capacity learned
relational model.

### 8.3 Later hypotheses

Multi-layer and nonlinear studies remain legitimate, but they should follow rather than precede the
edge-object test. A multi-layer study asks whether separability emerges elsewhere; a nonlinear study
asks whether the linear object is too restrictive. Neither should be described as a retry of the
closed position/content program.

If edge objects also show decodability without specificity, the project should stop architecture
search and report that these signals are distributed at the tested sites. If edge objects pass, the
next comparison should be the frozen nonlearned baseline against a directly supervised,
equal-capacity relational model—not another unsupervised branch naming exercise.

The attempted naturalistic retrieval/agreement qualification now has a terminal answer: retrieval
failed the cross-template support gate, and agreement was potent but template-conditioned and
nonspecific. [C059] [C060] That endpoint-development line is closed. A future external-validity
study must instead use a separately versioned established mechanism/task with an end-to-end causal
positive control, or change the representational object. It must preserve model-specific eligibility,
two-family replication for general claims, and sealed confirmation; it cannot promote the favorable
agreement template or retune the v6.2 gates. [C061]

The first established-task qualification, IOI v1, likewise stopped upstream: substantial target
behavior did not clear its cross-template sham hierarchy, so its intervention stage was never
measured. [C064] [C065] We therefore stop constructing additional natural-language prompt families.
The subsequent canonical induction assay recovered strong edge attention and a pair-level causal
contribution, but its donor patch missed the frozen material recovery and selectivity magnitudes. [C067]
[C068] [C069] A successor must therefore separate a trivial full-residual pipeline skyline from an
externally fixed complete-circuit intervention and normalize circuit recovery by that skyline.
Single-model circuit reproduction remains technical validation only; any general method claim still
requires prospective replication in at least two model families.

A collateral-constrained supervised controller is a later, separately versioned hypothesis. Its
purpose would be to ask whether explicit safety supervision moves the recovery--damage Pareto
frontier, not to rescue or rename K2. V2 does not authorize that experiment.

## 9. Limitations

- The strongest original architecture results concern one relatively small transformer checkpoint and
  selected activation sites; the broader proxy benchmark is exploratory and has only nine model/layer
  clusters. [C042]
- Proxy-control v2 still contains only three model units, two from the Pythia family; layers within a
  model are not independent model replications. [C049]
- SOURCE_C and SOURCE_D use disjoint vocabularies and templates but share one controlled generator;
  their transfer is not natural-domain confirmation.
- The naturalistic QA endpoint did not meet its frozen effect-eligibility floor and remains
  descriptive. [C057]
- The behavior-gradient oracle is one rank-limited development estimator, not the optimum over every
  supervised linear or nonlinear controller.
- Several datasets share annotation conventions or releases and are not model-level replications.
- Early fixed-probe studies are exploratory; their point estimates do not have the inferential status
  of later eligible protocols.
- Bootstrap intervals quantify sampling within frozen sources and do not establish generalization to
  fresh corpora, models, seeds, or analysis choices.
- Linear failures do not rule out nonlinear, multilayer, larger-model, or task-dependent separation.
- Attention weights and transported values are candidate relational objects, not proof of a causal
  syntactic mechanism.
- Pretraining inclusion for evaluated text may be unknown, so corpus transfer is not necessarily
  training-data independence.
- The v3 relational-object successor stopped at prescore, and the v4 measurement-design study stopped
  after real-panel balance and overlap evaluation. Neither contributes a positive or negative
  relational-representation result. [C038] [C040]

## 10. Reproducibility and artifact map

The quantitative claim ledger and verifier are:

- `reports/paper_claim_ledger_v1.json`
- `scripts/verify_paper_claims.py`

Primary evidence artifacts are:

- `reports/pre_k2_suite_v6/RESULTS.md`
- `reports/raw_atlas_results.md`
- `reports/k2_postwave_comparison.md`
- `reports/k2_atlas_audit_results.md`
- `reports/atlas_completion_results.md`
- `pilot_runs/20260802_atlas_measurement_v2_4/analysis/results.json`
- `results/atlas_rope_v8_attempt12_analysis_recovery/frozen_result.json`
- `results/atlas_relation_context_v9_attempt13/result.json`
- `results/atlas_context_local_v10_attempt14/result.json`
- `reports/architecture_program_closure_v1.json`
- `reports/provenance/relational_attention_edges_v1_discovery1_retirement.json`
- `reports/opened_development_conllu_validation_v1.json`
- `reports/opened_development2_forward_conllu_validation_v1.json`
- `reports/provenance/relational_objects_v2_development2_prescore_terminal_v2.json`
- `reports/provenance/relational_objects_v3_prescore_terminal_v1.json`
- `reports/relational_objects_v3_source_pool_conllu_validation_v1.json`
- `data/relational_measurement_v4/prepared.json`
- `results/relational_measurement_v4_opened_development1/result.json`
- `reports/provenance/relational_measurement_v4_closure_v1.json`
- `reports/claim_review/relational_objects_v2_and_paper_post_result_claim_review.md`
- `reports/claim_review/relational_objects_v3_prescore_and_paper_review.md`
- `reports/claim_review/relational_measurement_v4_post_result_claim_review.md`
- `results/proxy_control_benchmark_v1_20260808/aggregate/result.json`
- `results/proxy_control_benchmark_v1_analysis_20260808/result.json`
- `reports/claim_review/proxy_control_benchmark_v1_post_result_claim_review.md`
- `configs/proxy_control_benchmark_v2/FREEZE.json`
- `results/proxy_control_benchmark_v2_20260808/synthetic/result.json`
- `results/proxy_control_benchmark_v2_20260808/aggregate/result.json`
- `results/proxy_control_benchmark_v2_analysis_20260808/result.json`
- `reports/claim_review/proxy_control_benchmark_v2_post_result_claim_review.md`
- `reports/architecture_program_closure_v2.json`
- `configs/joint_controllability_benchmark_v3/FREEZE.json`
- `configs/joint_controllability_benchmark_v3/RECOVERY_INPUTS.json`
- `results/joint_controllability_benchmark_v3_analysis_recovery_20260808/result.json`
- `reports/claim_review/joint_controllability_v3_analysis_recovery.md`
- `results/canonical_induction_circuit_v1_1_20260809/final/result.json`
- `reports/canonical_induction_circuit_v1_1_analysis/result.json`
- `reports/claim_review/canonical_induction_circuit_v1_1_post_result_claim_review.md`
- `prereg/proxy_control_naturalistic_confirmation_v1_draft.md`

## 11. Conclusion

The MSAE program began with a plausible observation: position, syntax, and lexical content are all
decodable, and learned sparse branches can converge reproducibly. The completed experiments show why
that observation is insufficient. Structural information remained in the content branch, context
subspaces responded almost equally to coherent and unrelated prefixes, and relation-aware token-pair
features did not consistently beat matched controls. Stable geometry was therefore compatible with
stable mixing. The prospective proxy benchmark then localized the problem across methods and depths:
some components moved behavior, and others isolated counterfactual geometry, but none provided the
complete replicated combination of potency, sham specificity, and collateral safety. [C050]

The scientific contribution is the separation of representation content from representation
organization. A model can contain a signal, a probe can recover it, and a learned geometry can recur,
without any component being a clean causal module. The current architecture program is closed, and
the additional relational-object work correctly stopped before inference when adversarially corrected
controls exposed inadequate independent support. A final measurement-design study showed that
coarser and optimal matchers could restore structural sample support, but not complete balance and
overlap; it therefore stopped before synthetic estimator calibration or relational representation
evaluation. This strengthens the measurement lesson without adding a representation result.

> **Central conclusion:** These activations contain behaviorally relevant information, but neither
> stable encoding nor intervention potency guarantees precise, collateral-safe control.
