# Counterfactual Template Review

**Scope:** prescore content review of atlas-v1 C1/C2 templates. This is not a claim that the transformations are perfectly natural or that sentence-mean distances are causal.

## Frozen families and intended contrasts

| Family | Example source → target | Intended change | Preserved by construction | Claim level |
|---|---|---|---|---|
| position shift | same frozen corpus sentence at offset 0 → offset 32 | absolute model-token position | corpus words and word labels | sentence/token rows from identical content |
| lexical/entity | `Keira visited Helsinki today .` → `Liam visited Zurich today .` | entity identity | predicate, slots, tense, adjunct, punctuation | token-level only for 16 C2 aligned pairs; otherwise sentence-level |
| active/passive | `Keira praised the student today .` → `The student was praised by Keira today .` | voice/dependency order | agent, patient, predicate, tense, adjunct | sentence-level |
| punctuation/format | `Keira arrived today .` → `Today , Keira arrived .` | punctuation/fronting | participant, event, time | sentence-level sham/sentinel |

Each family has 32 distinct pairs, split into four template groups of eight. The builder records declared invariants and an automatic check; independent QA requires all checks true, exact group sizes, and pair uniqueness.

## Known limitations and failure actions

1. Active/passive pairs alter token count and introduce function words; they cannot be treated as token-aligned. Context length, continuation, punctuation, and CE sentinels must be reported.
2. Entity substitution changes two lexical items, so it tests lexical/entity sensitivity rather than a pure named-entity factor. The target-minus-random/sham contrast and family mapping are mandatory.
3. Fronting changes both order and punctuation. It is a formatting sentinel, not a clean structural-position label.
4. Synthetic grammar is narrow. Equal-weight template-group aggregation prevents one surface frame from dominating but does not establish natural-language generalization.
5. Position shifts use neutral prefixes; prefix identity and offset sentinels must be checked. A shift effect alone is not evidence of structural position.
6. Missing matched-random/sham comparators, fewer than 24 sentence-level pairs or 16 aligned lexical pairs, any invariant failure, or fewer than three of four template-group directions makes the counterfactual gate invalid/equivocal.
