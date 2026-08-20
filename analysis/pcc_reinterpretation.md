# PCC Reinterpretation Under a Broader Positional-Family Hypothesis

## Conclusion

The historical PCC work does **not** justify a shared/PCC branch. Its strongest repeatable observation is a small joint benefit on some POS and dependency-relation readouts. That observation is compatible with at least three mechanisms the old experiments cannot distinguish: (1) genuine information that is only useful jointly, (2) relative/structural position split across the two private branches because the “position” objective emphasized absolute position, or (3) probe/regularizer sensitivity. The matched-token and controlled-contrast results make the second and third explanations serious enough that “PCC” is not the default interpretation.

The frozen A1 no-go remains the governing historical decision. A1b diagnosed a metric/label-framing problem, and the independently run A1c supported the **prospective** gate revision; A1r therefore allowed analysis-only Stage B work. Neither record rewrites A1. Stage B-light used existing checkpoints, and the 24-pair contrast audit then stopped before Stage C.

All numbers below are regenerated from source JSON with hashes in [`reports/pcc_historical_synthesis.json`](../reports/pcc_historical_synthesis.json).

## What the stages established

| Stage | Observation | Correct disposition now |
|---|---|---|
| A0 | Mean joint gain: POS `0.00567`, deprel `0.00601`; 3/4 positive for each. WNUT remained content-private. | Useful screen only; same-corpus EWT probes and old absolute-position framing cannot identify shared interaction. |
| Frozen A1 | POS passed the syntax rule (`0.00453`, 3/4 positive), but dependency (`-0.00065`) and morphology (`-0.00276`) did not. Only one syntax and one semantic family passed, so `proceed_to_stage_b=false`. Several probes hit their iteration cap. | The original PCC expansion stopped. This is not superseded. |
| A1b | Coarse deprel became positive (`0.00487`, 4/4); head-direction/distance was `0.00388`, 3/4. NER behavior changed materially when framed as entity-binary versus type-only. | Diagnosed label/selection-metric sensitivity; not confirmation and not permission to train. |
| A1c/A1r | Metric-aligned independent confirmation supported the preregistered revision; A1r passed POS, coarse deprel, and three semantic sentinels. | Supports the revised observational gate only. It does not establish causal sharing. |
| B-light | Full coarse-deprel joint gain averaged `0.00694`, and an absolute-position-matched control remained `0.00635`; a matched-token control fell to `0.00096` with only 2/4 positive. Full POS was `0.00567`, position-control `0.00611`, token-control `0.00339` with 2/4 positive. | Absolute index alone does not explain the signal, but lexical identity/ambiguity explains or destabilizes much of the dependency effect. |
| Curated contrasts | Zero syntax families and four semantic families passed the sign rule over four checkpoints; `proceed_to_stage_c=false`. | Negative for the proposed syntax interaction bridge, but only exploratory because there were three hand-written sentence pairs per family and sentence-mean pooling. |

## Information-load reinterpretation

| Historical task | Primary load | Secondary/confounded load | Reinterpretation |
|---|---|---|---|
| absolute-position probe / position controls | absolute position | length, prefix, boundary | Direct absolute-position evidence only. |
| head direction + signed distance | relative/structural position | dependency relation, POS, lexical valency | A direct test of structure-relative coordinates; it should not be called generic syntax or PCC. |
| coarse dependency relation | relative/structural + syntax | token identity, POS, head geometry, corpus/parser artifacts | Plausible structural-position signal; token-control collapse shows lexical shortcuts matter. |
| POS / ambiguous-token POS | syntax/morphology | lexical identity, capitalization, frequency, local order | Mixed. Persistence after absolute-position matching does not rule out relative position or lexical ambiguity. |
| Number morphology | morphology | suffix/token identity, agreement context | Mostly content-side morphology; its negative/unstable joint gain argues against broad PCC. |
| WNUT/FewNERD/WikiNeural NER | lexical/semantic | surface form, capitalization, domain, label imbalance | Strong content-private sentinels. Binary/type-only changes show metric and label vocabulary can dominate small joint gains. |
| active/passive, dative, topicalization, relative-clause contrasts | structural/syntax | length, token alignment, punctuation, sentence-mean pooling | The zero-family pass is evidence against the old contrast gate, not a precise null estimate. |
| entity/event/lexical substitutions and role reversal | lexical/semantic or relational | tokenizer and sentence-length changes | They confirm content sensitivity under a weak sign rule, not private-component causal specificity. |

## Competing explanations and evidence

### Plausibly unallocated structural position

- Coarse-dependency gains survived the full-versus-absolute-position-matched comparison (`0.00694` vs `0.00635`). That rules out a simple “only exact token index” account, not the broader structural-position account.
- Head direction/distance itself showed a small A1b joint gain (`0.00388`, 3/4 positive), directly demonstrating that the old “position” branch did not make a clean absolute/relative distinction.
- POS gains also survived absolute-position matching. POS correlates with sentence and dependency location, so this remains compatible with a broad or split positional family.

### Plausibly genuine shared interaction

- A joint readout sometimes beats both private readouts, repeatedly enough to motivate a better test.
- Evidence is nevertheless insufficient: the effect is small, the raw-to-private gap is larger, training and evaluation often share a corpus, and no analysis first removes a discovery-frozen broad positional subspace. Joint decodability is not causal shared computation.

### Plausibly regularizer suppression

- Historical summaries report greater syntax gain for the matched-seed no-incoherence `g7` than regularized `g4` in some audits, while the regularizer strongly lowers incoherence and worsens reconstruction. This is consistent with suppression of useful shared structure **or** forcing under-modeled structural position into the content branch.
- One matched seed and mixed resume lineage cannot distinguish those accounts; it is a sensitivity control, not model-level replication.

### Probe/metric sensitivity

- Several frozen A1 probe families hit the iteration cap in all four checkpoints.
- A1b/A1c outcomes changed when NER checkpoint selection was aligned to macro-F1 and labels were reframed as type-only versus entity-binary.
- Effects at the `0.001–0.01` scale are not interpretable without grouped uncertainty, multiplicity control, denominator eligibility, and source transfer.

## Predictions for the new atlas and K=2 audit

1. **Structural-position prediction:** a discovery-frozen relative/structural subspace should recover head-distance, depth/boundary, and coarse-dependency tasks across a different UD treebank. If the old PCC signal was unallocated position, broad/split position projection should absorb most deprel/POS joint gain.
2. **Lexical-shortcut prediction:** matched-token or discovery-vocabulary-transfer tests should weaken deprel/POS effects more than absolute-position matching does. A signal that disappears is shortcut-sensitive, not a family assignment.
3. **Genuine-interaction prediction:** after broad-position stripping, joint or bilinear readouts should retain `>=0.05` normalized gain on at least two held-out task variants with grouped confidence above zero. Otherwise no PCC/shared branch is warranted.
4. **Regularizer prediction:** if incoherence suppresses useful structure, matched g7 should improve structural retention after controlling reconstruction/collateral without merely increasing cross-family leakage. If it only relaxes separation, its apparent gain should track leakage.
5. **Semantic-sentinel prediction:** content-private should retain NER/lexical utility, while position removal should not improve it through source or capitalization shortcuts. Entity-binary and type-only results must remain separately reported.

**Action:** use these as preregistered discriminators in G1/G2. Do not train or even prototype a PCC branch from the historical evidence.
