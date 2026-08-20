VERDICT: SHIP
ONE-LINE: GENTLE is intact, sufficiently supported, exposure-firewalled, and fail-closed before any validation inference.

BLOCKERS

None.

REVISIONS

None.

NITS

- `PLAN.md:26,122,202` — In the implementation manifest, label the 20-document whole-source count explicitly as selected-panel union support, not only candidate-pool support.

CHECKS RUN

- `/jumbo/lisp/f004ndc/.agent-workspace/bin/check-plan --path PLAN.md` -> PASS.
- Read-only GENTLE raw-file audit of `data/atlas_rope_v4_raw/UD_English-GENTLE/fd7a1bfc82896e362c66f59492b5525940f52fa7/en_gentle-ud-test.conllu` -> SHA-256 `42d12cdef99bcd3160a3241ba1811fe9e7fd4b37a77f9b9e8c2852f04d69f3fa`; 17,799 integer-token forms, zero `FORM == "_"`; 26/26 unique document IDs, 1,334/1,334 unique sentence IDs, and 26/26 unique document source URLs.
- Label-only local-tokenizer audit using pinned Pythia revision `582159a2dfe3e712a8d47ae83dec95ae3bde8e7e`, `add_special_tokens=false`, the frozen `parse_conllu`/`token_layout` pretokenized-word path, and no model weights -> candidate sentences by bin `352/352/350/133/28` and supporting documents `23/24/26/25/14`, exactly matching `PLAN.md:26`.
- Read-only pre-exclusion deterministic selection audit -> all five bins select exactly 20 sequence-distinct bases under the two-per-document cap; selected documents by bin are `12/13/14/13/14`, and the 100-base panel uses 24 documents in union. The sparse `65-128` bin has 28 unique sequences and cap-two capacity 21, so the plan correctly requires post-exclusion fail-closed eligibility rather than fallback.
- Read-only failed-source regression audit -> official GUMReddit still has 16,364/16,364 underscore token forms and only 18 documents; prior measurement artifacts still contain 872 ESLSpok documents across C1/C2. Their rejection at `PLAN.md:24-25` remains justified.
- Read-only plan regression against v8 findings -> GENTLE permits complete single sentences only; windows, truncation, synthetic boundaries, and fallback are forbidden; document/sentence/source-URL plus exact prepared-sequence/content exclusions run before deterministic selection; pre/post support is published; and any deficient bin or whole source fails closed (`PLAN.md:26,44-49,97,122,202`).
- Read-only stage audit -> validation, science, and attempt-8 prescore roots are absent. Fresh GUM still runs first; GENTLE remains unopened unless GUM passes; both sources must pass independently; thresholds cannot change after either opens (`PLAN.md:73,99-102,140-154`).
- No model configuration or weights were loaded, no tensor or neural inference was executed, and no implementation file was edited.

CONTRACT COVERAGE

- V8 blocker: redacted GUMReddit used as authorizing validation -> met — GUMReddit is rejected and never tokenized; intact official GENTLE replaces it (`PLAN.md:25-26,36,97,151-152`).
- V8 blocker: underdefined multi-sentence windows and constituent exposure -> met — only complete single sentences are allowed, eliminating window enumeration and embedded-constituent ambiguity (`PLAN.md:26`).
- GENTLE integrity and fixed provenance -> met — commit, file hash, token-form audit, genuine-document count, and label-only bin support are frozen and independently reproduced (`PLAN.md:26`).
- Per-bin and whole-source support -> met in plan — exact 20-base, ten-document-per-bin, two-base-per-document, and 20-document overall floors fail closed after exposure exclusion (`PLAN.md:26,42-49,122,202`).
- Cross-source freshness firewall -> met in plan — all prior prepared inference units/opened-input ledgers are inventoried and document, sentence, URL, exact token-sequence, and normalized-content matches are excluded before selection (`PLAN.md:26,97,122,202`).
- No post-inference rescue or favorable resampling -> met — no truncation, windows, fallback, redraw, pooling, retry, or threshold change is allowed (`PLAN.md:26,49,73,154`).
- Sequential held-out validation -> met — fresh GUM gates GENTLE, each must pass every cell independently, and only dual PASS authorizes science (`PLAN.md:51,73,101-102,150-154,177-180`).
- Prior numerical/runtime/count/no-training contracts -> met and unchanged (`PLAN.md:42-92,124-163,174-182`).
- Safe to resume implementation without opening validation -> met — M2 remains no-inference, implementation and freeze each require later adversarial SHIP, and validation roots are presently absent (`PLAN.md:116-146`).

UNKNOWNS

- The local path and file hash were verified, but official upstream commit provenance was not independently network-verified in this read-only review.
- Post-firewall GENTLE support is intentionally not known until M2 inventories every prior opened input. The `65-128` bin has only one candidate of cap-two slack; any loss beyond that must make the source ineligible, exactly as planned.
- The future implementation must record the selected-panel union document count and every pre/post exposure exclusion in its signed manifest; this plan review does not review that code or artifact.
