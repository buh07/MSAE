VERDICT: BLOCK
ONE-LINE: Official GUMReddit is lexically redacted, and its windows do not define a fresh natural-text validation population.

BLOCKERS

- [critical] `PLAN.md:7,25,35,41-50,72,121,150-151,176-179,201`; `data/atlas_rope_v4_raw/UD_English-GUMReddit/b23cca5d4f8732b35cbbec070bb2b1d7abe750e1/en_gumreddit-ud-dev.conllu:27-30` — the pinned official GUMReddit files do not contain Reddit word forms. A read-only audit of all three files found 16,364 integer-token rows and exactly 16,364 `FORM == "_"`; the `# text` fields likewise contain only underscores, spacing, and underscore runs. The lexical text is intentionally redacted.
  reasoning — tokenizing these files does not produce outcome-new natural Reddit sequences. It produces a narrow family of underscore/spacing patterns; multi-sentence windows merely concatenate more placeholder patterns. “Normalized-content” hashes then encode redaction geometry rather than original content, and apparent sequence distinctness can be created by token count or `SpaceAfter` patterns without lexical diversity. Hidden-state numerical behavior depends on token embeddings and activation values, so an underscore-only corpus does not independently test the score path over realistic source variation.
  impact — GUMReddit can pass every document/count gate while providing a degenerate activation challenge, yet its PASS is mandatory to authorize science. Calling this an outcome-new validation source would overstate the evidence and could make the experiment depend on a scientifically irrelevant gate.
  fix — do not use the pinned redacted UD files as an authorizing natural-corpus supplement. Before implementation, choose and freeze an outcome-new source whose exact redistribution permits intact text and whose integer-token `FORM` audit passes a prespecified non-placeholder rule, with at least 20-30 genuine documents if it is to be described as source-level replication. Alternatively, treat the underscore data only as a named synthetic/placeholder stress challenge that cannot authorize science. Do not reconstruct deleted Reddit text from live URLs without a separate provenance, licensing, privacy, and exposure review.

- [high] `PLAN.md:25,43-48,96,117-121,185-186,201` — even if a text-bearing replacement were supplied, “deterministic contiguous same-document multi-sentence windows may fill” does not uniquely specify the 65-128 population or close its exposure firewall.
  reasoning — the plan does not freeze sentence ordering across files/splits, which contiguous start/end spans are enumerated, whether all spans or a shortest/maximal span is used, how sentence boundaries are serialized, whether component token IDs are concatenated or joined text is retokenized, how single sentences are prioritized over windows, or how overlapping windows are deduplicated. These choices change BPE IDs, length bins, selected hashes, and SDPA shapes. Exact whole-window content/sequence exclusion is also insufficient: a previously opened sentence can be embedded inside a longer new window without matching the window hash.
  impact — multiple materially different GUMReddit panels satisfy the prose, and a window can be labeled fresh while containing an exposed constituent. Those choices would be frozen only after the replacement source had been inspected and would become irreversible once GUMReddit inference opened.
  fix — freeze a literal builder contract before any model call: official document/sentence order and globally unique IDs; exact `(document,start_sentence,end_sentence)` enumeration; full-sentence/no-truncation policy; one canonical boundary serialization and tokenize-once rule; exact single-sentence-versus-window priority; overlap/deduplication rules; and stable SHA ordering after exclusions. Bind every constituent ID and hash. Apply document, sentence/source-record, source-URL, normalized-content, exact-token, and bidirectional contiguous-subsequence/prefix/suffix exposure checks to every constituent and the complete window against every prior opened inference unit. Forbid cross-document/cross-split joins, redraws, and post-inference fallback.

REVISIONS

- [medium] `PLAN.md:25,43-48,121,201` — all three official GUMReddit splits contain only 18 genuine documents (14 train, 2 dev, 2 test). Although the current per-bin minimum of ten can be met by reusing up to two bases per document, this is below the originally recommended 20-30-document source-support gate and cannot establish broad source independence. Report the total 18-document ceiling explicitly; if retained for a non-authorizing challenge, publish unique documents across the whole selected panel and constituent-overlap counts, not only per-bin support.
- [medium] `PLAN.md:25,121,201` — a repository-wide source-name search is not a sufficient freshness proof because prior records may use another source label. Require cross-source comparison of GUMReddit document IDs, sentence IDs, Reddit source URLs, normalized intact content, and token sequences against signed prior opened-input ledgers. Label the source only “outcome-new to this experiment,” not broadly unseen or model-held-out.

NITS

- `PLAN.md:72,145,176` — “GUMReddit remains unopened” should mean model activations/outcomes remain unopened; its raw files and support were already opened during no-inference method development.

CHECKS RUN

- `/jumbo/lisp/f004ndc/.agent-workspace/bin/check-plan --path PLAN.md` -> PASS.
- Read-only ESLSpok support audit -> the retained exposure artifact contains 872 prior ESLSpok documents across C1/C2; the pinned dev/test files contain 464 records, consistent with the plan's report that all 442 otherwise length-eligible records failed document freshness. Retiring ESLSpok before inference is justified.
- Read-only GUMReddit raw-file audit -> 16,364/16,364 integer token rows have `FORM == "_"`; zero token forms are lexical. All `# text` fields contain no characters other than underscores/whitespace patterns.
- Read-only GUMReddit support audit -> 895 unique sentences in 18 unique documents across all splits: train 686 sentences/14 documents, dev 104/2, and test 105/2; no duplicate document or sentence IDs across splits.
- Read-only repository identity audit -> no prior `GUM_reddit_*` document-ID occurrence was found outside the newly downloaded raw source/planning artifacts, but source-name absence alone cannot prove cross-source content non-exposure.
- Read-only regression audit of the unchanged plan -> fresh-GUM-first sequencing, immutable thresholds, cellwise gates, exact sentinel schedule, EWT calibration firewall, diagnostic isolation, SDPA runtime binding, and no-training constraints remain intact.
- No model configuration or weights were loaded, no tensor or neural inference was executed, and no implementation file was edited.

CONTRACT COVERAGE

- ESLSpok infeasibility and retirement -> met (`PLAN.md:24,35,96,121,151,201`).
- Replacement source has outcome-new model activations -> met in history — no GUMReddit model call/outcome is recorded — but natural-text validation fitness is unmet because the pinned source is redacted (`PLAN.md:25`).
- GUMReddit document support -> partial — 18 real documents can clear the weaker ten-per-bin rule but not the recommended 20-30-document source gate (`PLAN.md:43-48`).
- Deterministic 65-128 window construction -> unmet — intent and document boundary are stated, but enumeration, boundary tokenization, selection priority, deduplication, and constituent firewall are not executable (`PLAN.md:25`).
- Cross-source freshness -> partial — exact full-sequence/content exclusion and source-name inventory are planned, but document/sentence/URL identity and embedded constituent views are missing (`PLAN.md:25,121,201`).
- Sequential held-out validation -> met structurally — fresh GUM gates GUMReddit and both gate science (`PLAN.md:35,72,93-101,139-153,176-179`).
- Prior v7 numerical/runtime/count contracts -> met and unchanged (`PLAN.md:39-91,115-180`).
- Safe before any model inference -> unmet — the supplementary authorizing source and its long-window population must be replaced or redefined and reviewed before implementation resumes.

UNKNOWNS

- Whether an intact, legally usable version of these exact Reddit documents can be obtained without creating new privacy/licensing or historical-exposure problems.
- Whether a different intact outcome-new corpus can provide five bins with 20 sequence-distinct bases, at least 20-30 documents, and no prior opened-input overlap. This must be answered label-only and fail closed before model inference.
