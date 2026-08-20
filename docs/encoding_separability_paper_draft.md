# Encoding Is Not Separability: Stable but Mixed Structure in Transformer Activations

## Status and claim scope

This is a paper-oriented synthesis of the completed MSAE position/content program through Attempt
14. It is not a preregistration and does not change any frozen experiment. The defensible scope is
Pythia-160m-deduped at the examined layer/state and the corpora and linear protocols reported by the
individual studies. The project did not train a directly supervised context/local comparator.

## Abstract

Transformer activation probes routinely recover lexical, positional, contextual, and syntactic
properties. It is tempting to interpret this recoverability as evidence that the properties occupy
separate manipulable components. We tested that stronger interpretation using sparse decompositions,
cross-checkpoint geometry, document-aware resampling, counterfactual interventions, transferable
linear projections, and matched controls. Conventional decoding and several cross-dataset projection
measurements were positive. Learned two-branch decompositions also converged reproducibly. However,
the learned branches remained functionally mixed: content branches retained substantial structural
information, relational child--head features did not consistently beat matched nonrelation controls,
and a transferable context-difference subspace did not materially prefer coherent prior context over
matched unrelated context. The results separate four questions that are often conflated: whether
information is encoded, recoverable, selective, and sufficient to warrant an architecture. At the
examined layer, encoding and partial recoverability were robust, but clean selective separation was
not demonstrated.

## 1. Research question

The original architectural hypothesis was that a transformer activation could be decomposed into a
position-oriented component and a content-oriented component. A successful result required more than
probe accuracy. The assigned component needed to recover its target family, exclude or reduce the
other family, respond preferentially to target-matched counterfactual changes, and recur across
checkpoints and datasets.

The later program sharpened this into a distinction among:

1. **Encoding:** can an estimator recover a property from the activation?
2. **Recoverability:** does a reproducible low-dimensional organization retain the property?
3. **Selectivity:** does the organization respond more to the intended causal contrast than to
   matched nuisance or cross-family controls?
4. **Architectural warrant:** does the complete evidence justify training and naming separate
   representational branches?

The first two do not entail the latter two.

## 2. Learned K2 decompositions

The K2 models reconstructed the same activation through two summed sparse branches. The nominal
position branch had a smaller dictionary and active budget than the nominal content branch. Training
used reconstruction and sampled decoder-Gram incoherence, not direct position/content supervision.
Consequently, the branch names did not constrain their semantics.

Across regularized checkpoints and a no-incoherence control, the decompositions converged to similar
geometries. This reproducibility initially appeared favorable, but functional audits showed that the
content branch often retained as much or more structural information than the position branch. Higher
cross-checkpoint CKA therefore established stable convergence, not stable selective factorization.
Training more seeds or increasing incoherence would test optimization repeatedly without addressing
the missing semantic constraint.

## 3. Measurement failures and repairs

Several early formal stops were dominated by measurement rather than scientific failure. Token-row
balancing concealed sparse independent-document support. Document bootstraps could omit rare classes,
making many draws undefined. Family-level predicates converted task missingness into apparently total
stability failure. Specificity replay also compared GPU/Torch and CPU/NumPy reduction paths at a
tolerance tighter than their ordinary numerical discrepancy.

The repaired studies introduced document/class support gates, endpoint-specific eligibility, cached
replay, prospective numerical QA, immutable namespaces, and controlled one-shot execution. These
repairs matter to interpretation: early invalid endpoints are not evidence for or against
separability. Later eligible negative results are.

## 4. Relational syntax: Attempt 13

Attempt 13 asked whether true child--head representations isolated dependency depth, coarse
dependency relation, and signed head distance relative to child-only features, matched sham heads,
and matched sequential-offset controls. It retained signed head distance even though earlier results
were unfavorable.

The relational module was measurable, but not every prespecified task demonstrated the required raw
recovery or isolation in both transfer directions. Some individual constructs contained detectable
information, yet favorable contrasts did not form the complete prespecified vector. Its formal
exploratory conclusion is:

> Cross-corpus relational information was detectable, but strong recovery and relation-specific
> isolation were not demonstrated.

This does not imply that syntax is absent. It suggests that a token-local child/head linear object may
not be the appropriate unit, motivating a separately scoped attention-edge discovery program rather
than relation-aware training under the old architecture.

## 5. Context versus local information: Attempt 14

Attempt 14 was the final targeted falsification of the position/context idea. It used 784 supported
components from two document-disjoint Spanish AnCora source partitions, one exact Pythia revision,
hidden-state index 4, and a frozen rank-16 linear protocol. All retained rows were finite and no
technical replay row was removed.

The fitted context-difference subspace transferred in both directions. Held-out capture was 0.162
from 3LB to CESS and 0.192 from CESS to 3LB, well above the analytic rank-ratio reference of 0.0208.
Context-versus-lexical assignment, reciprocal lexical assignment, lexical localization, and lexical
complement preservation passed.

The decisive specificity gate failed. The projection's coherent-context advantage over matched
unrelated context was 0.0087 in one direction and 0.0136 in the other, below the prospectively frozen
0.05 material margin. Raw genuine-context and unrelated-context effect magnitudes were also nearly
equal within each source. Thus, the transferable subspace captured a reproducible response to
altering prior context, but did not isolate meaningful coherent context accumulation from generic
prefix disruption.

The formal conclusion is:

> Context is encoded, but the proposed projection is not specific enough to serve as a
> context-private component.

Attempt 14 did not train a supervised context/local model. It is therefore incorrect to claim that
the projection matched, beat, or replaced such a learned comparator.

## 6. Synthesis

The combined evidence supports abundant representational information but weak modularity. Absolute
and relative position, lexical identity, context changes, and relational labels can be decoded or
captured under at least some protocols. The models and projections can also recur across seeds or
sources. Nevertheless, controlled counterfactuals and matched controls generally fail the stronger
criterion that one component should respond preferentially and materially to its named construct.

Several mechanisms could produce this pattern:

- position correlates with boundary state, syntax, punctuation, lexical identity, and available
  context;
- causal attention integrates token-local and prior-context information before the examined state;
- syntactic relations are pairwise or edge-based rather than properties of one token vector;
- reconstruction and geometric incoherence do not impose branch semantics;
- a small number of important cross-branch directions can be diluted by average dictionary
  incoherence;
- linear subspaces can support decoding without supporting independent intervention.

The most conservative conclusion is not that transformers lack structure. It is that this structure
does not behave like two clean, independently manipulable linear modules at the examined layer.

## 7. Decision and future work boundary

The K2 and position/context architecture program is closed. Additional seeds, stronger incoherence,
larger branches, supervised context/local training, and private/private/shared training are not
authorized by these results. Attempt-14 Gate 4 remains unfavorable and will not be relaxed.

Future work must change the representational object. The first separate discovery study examines
directed attention-edge probability and transported-value features on new UD sources, against exact
sequential/position matching and the original token-pair residual baseline. That study is
measurement-only. Even a positive result can nominate, but cannot itself constitute, a relation-aware
architecture result.

## 8. Limitations

- Most results concern one small Pythia checkpoint and one examined layer/state.
- Several sources share releases or annotation pipelines and are not fully independent corpus
  replications.
- Reported percentile intervals are marginal rather than multiplicity-adjusted simultaneous
  intervals.
- A failed linear specificity gate does not rule out nonlinear, layer-dependent, larger-model, or
  task-dependent separation.
- Dataset inclusion in Pythia pretraining is generally unknown.
- Attention weights, if studied later, are observational features and do not alone establish a
  causal syntactic mechanism.

## Central conclusion

> These activations contain the information, but containing information is not the same as
> organizing it into clean causal modules.

