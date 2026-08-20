VERDICT: SHIP
ONE-LINE: QK gating, source provenance, confound disclosure, and signed supersession are now internally consistent.

BLOCKERS        (must fix before proceeding; empty if none)
  - None.
REVISIONS       (should fix; not blocking)
  - None.
NITS            (optional, cap at 5)
  - None.

CHECKS RUN
  - `sha256sum PLAN_RELATIONAL_EDGE_V1.md reports/provenance/relational_attention_edges_v1_source_amendment.json` → plan `5a5e8fb6d1396632c700fa51386711d022a6107bb02572fa7d7c94790bdb0c51`; amendment `f7f59cf80d4fcd82d416f047b51eae9b60fd4bc6962a117dadf9ebc44c30f44`.
  - `/jumbo/lisp/f004ndc/.agent-workspace/bin/check-plan --path PLAN_RELATIONAL_EDGE_V1.md` → PLAN: PASS.
  - Canonical amendment payload SHA-256 → `99c123f7936e9bc79a97e64dfe553501cbfe4409c75e4ba01e49bb202f57ace7`, matching the signed envelope.
  - Amendment Ed25519 verification → PASS; public-key fingerprint `1eb6470fb2bd3a114ca4427174a12eb5fb14639ca1e763f75b9afbb564b2e503` matches.
  - Amendment reference verification → PASS; current plan, builder, and raw-provenance files match their bound hashes.
  - Read-only line review of the complete revised plan and signed source amendment → prior QK/attention reachability, relation-feature, unmatched-prefix, and supersession findings are fixed; no model forward, endpoint scoring, artifact mutation, or file edit performed.
  - `/jumbo/lisp/f004ndc/.agent-workspace/bin/record-review --kind plan --origin forked --scope plan --transcript -` → review-record helper was available; this exact transcript was submitted before return.
CONTRACT COVERAGE
  - Signed amendment authenticity and current-plan binding → met — signature, payload digest, key fingerprint, plan, builder, and raw-provenance identities verify.
  - Arabic rejection provenance → met — corrected 62-document/31-component/79-pair population and final support-floor rejection explicitly supersede the preliminary 26-document statement, which is forbidden in result claims.
  - Ukrainian/Latvian source selection → met at label-only prescore level — signed counts clear every document/component/pair/fold/polarity floor and source selection remains conditional on the project exposure audit.
  - No candidate model outcome exposure → met as a signed attestation — weights, forwards, activations, endpoint scores, and neural training are false; tokenizer/matching development exposure is disclosed.
  - Primary QK representational object → met — scaled partial-RoPE QK means are primary; normalized attention and value-derived objects are explicitly descriptive.
  - Decision-feature reachability → met — all gates and paired bootstrap intervals consume only `z`, `r`, and `[r,z]`; a negative test must prove normalized `a` cannot enter a gate.
  - Incremental estimator semantics → met — gate 3 is `[r,z]` minus `r`, with fold-local preprocessing/CV and held-out-source isolation.
  - Conditional bootstrap semantics → met — shared component multiplicities, finite-draw handling, quantiles, paired contrasts, and strict bounds remain exact.
  - Secondary-analysis reproducibility → met — QK relation feature sets are explicit, while `a`, `m`, and `v` receive edge ROC AUC only.
  - Unmatched absolute-prefix confounding → met as a limitation — query-index and sequence-length distributions must be reported by source/class and cannot be described as balanced or gating controls.
  - Matching and scientific claim scope → met — relative gaps, UPOS, subtoken counts, ancestry exclusions, document polarity, and deterministic pairing support only matched predictive association, not isolation or causality.
  - Preservation, one-shot lifecycle, GPU/tmux, no-training, and post-result claim review → met at plan level — prior fail-closed contracts remain unchanged and mandatory.
UNKNOWNS
  - Signed label-only support counts were not independently regenerated; exact-candidate review must verify the frozen prepared artifacts and deterministic rebuild before authorization.
  - Project-wide exposure-audit outcome and Pythia pretraining overlap remain unresolved; the plan correctly blocks source inference on the former and limits claims for the latter.
  - The eventual QKV hook and partial-RoPE reconstruction remain implementation risks; exact synthetic backend QA and candidate SHIP are still required before any source forward.
