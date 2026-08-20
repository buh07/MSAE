# Atlas-v1 Label and Shortcut Inventory

The TSVs are the human-readable contract; `configs/atlas/task_manifest.json` is the executable equivalent frozen by the data builder.

## Separation target

The atlas asks whether three Tier-1 families are separable at raw Pythia-160M L3: **absolute model-token position**, **relative/structural position**, and **lexical/semantic content**. Syntax/morphology and surface/format/domain are Tier-2 sentinels because they can either reveal collateral damage or explain an apparent Tier-1 split. A family is an operational collection of held-out tasks, not a natural ontology.

Absolute tasks label every non-padding, non-special model token. Word-level tasks label only the first subword of corpus words. Neutral prefix words receive absolute labels but never corpus word labels. This prevents repeated subwords from changing the inferential weight of a word while preserving the true model-token coordinate.

## Modes

All primary atlas tasks are token-local, matching the current MSAE training site. Relation-aware pair/window tasks are not silently mixed in; they require a later preregistered activation if token-local structural tasks fail while a positive relation-aware control succeeds.

## What “content” means

`token_identity_256` and `lemma_identity_256` are deliberately narrow lexical probes. `ner_coarse` is the semantic sentinel transferred from FewNERD to WikiNeural using `O/PER/ORG/LOC/MISC`. The component should be described as **position-minimized content**, never pure content.

## Eligibility and failure semantics

Macro-F1 is primary for every multiclass task. The no-information denominator is the analytic expected macro-F1 of a classifier sampling discovery label priors; a discovery-majority classifier is reported descriptively but is not used as the macro-F1 chance denominator because balanced random predictions can beat majority macro-F1 without signal. Normalized recovery is undefined unless the raw-over-chance lower confidence bound exceeds the locked floor. Missing/unknown labels remain missing; they are never converted to a favorable class. A failure, undefined denominator, source-confounded result, or boundary-near interval makes the affected gate equivocal rather than negative evidence.
