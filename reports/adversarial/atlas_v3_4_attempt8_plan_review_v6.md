VERDICT: BLOCK
ONE-LINE: The batch contract is exact for grids but undefined for the irreversible fresh-GUM sentinel bundle.

BLOCKERS

- [critical] `PLAN.md:21,34,49,77,96-98,139-150,173-175`; `configs/atlas_discovery_v3_3/population_split_v3.json:318-335`; `scripts/extract_atlas_discovery_v3_3.py:406-466,672-694` — line 77 now uniquely specifies the 100-reference/600-candidate five-bin grid schedule, but it also claims to govern all fresh-GUM validation while ordering candidates only by grid shifts `{1,4,8,16,32,64}` and giving grid-specific partial batches `64+36` and `9x64+24`. The mandatory exact fresh-GUM sentinel is a different 16-pair population: eight shift-16 pairs plus eight prefix-position pairs at `{7,9,12,16,17,28,37,41}`. Its reference/candidate order, batching, padding maxima, and partial membership are not defined anywhere.
  reasoning — the frozen attempt-7 QA constructor preserves the exact pair-ID order from `population_split_v3.json`, builds separate reference/candidate lists, and executes each list in contiguous batch-size-64 slices. For the unopened sentinel, that means 16 reference condition units and 16 candidate condition units (one partial batch per pass), with 24 selected rows on each side. The new grid rule cannot be applied literally because seven prefix offsets are absent from its shift-order set and its stated counts do not describe the sentinel. Choosing canonical unit-ID order, frozen pair-ID order, family-major order, or pooling sentinel units with grid batches changes padding/tensor shapes and potentially SDPA dispatch.
  impact — the primary outcome-naive authorization bundle can be opened under multiple numerically different executions while each implementer plausibly claims plan compliance. Because this is the exact irreversible panel retained from attempt 7, its schedule cannot be selected after implementation or inferred after results.
  fix — add a separate literal sentinel schedule before implementation: preserve the 16 pair IDs in the exact signed `population_split_v3.json` order; construct references and candidates exactly as frozen `_qa_panel_units` does; run three identical reference repetitions and one candidate pass as separate one-batch lists of 16 condition units each at batch-size 64; retain the resulting 24 selected rows per side in pair/role order; right-pad each pass exactly as `_forward_units`; forbid pooling with the 100/600 grid lists; and bind ordered pair/unit/row IDs, `[16,max_length]` shapes, padding maxima, hashes, and final-partial membership. Make the source-parameterized executable dispatch explicitly between this signed sentinel schedule and the already-frozen grid schedule, with fixtures that reject order or pooling drift before fresh GUM opens.

REVISIONS

None.

NITS

None.

CHECKS RUN

- `/jumbo/lisp/f004ndc/.agent-workspace/bin/check-plan --path PLAN.md` -> PASS.
- Read-only line-by-line comparison of `PLAN.md` against `reports/adversarial/atlas_v3_4_attempt8_plan_review_v5.md` -> every v5 revision/nit is fixed literally: batch 64, grid order/slicing/padding/final batches, four `true` SDPA flags, required-versus-extra library semantics, reconstructed terminology, and technical-source terminology are present.
- Shell-integer grid count audit -> 100 bases, 30 cells, 100 references/200 reference rows, 600 candidates/1,200 candidate rows, and 700 condition units/1,400 selected rows; `PLAN.md:42-46,77` is internally exact.
- Shell-integer diagnostic count audit -> 20 bases x seven conditions = 140 units and 280 selected rows; `PLAN.md:88` correctly specifies 20/120 units, 40/240 rows, and hooked/unhooked execution of all 140.
- Read-only frozen-sentinel lineage audit -> `population_split_v3.json` contains 16 ordered fresh-GUM pair IDs, and frozen `_qa_panel_units` preserves that order before separate reference/candidate `_forward_units` calls. From the frozen family roles, the sentinel has 16 reference plus 16 candidate condition units and 24 selected rows on each side.
- Read-only prior-review regression audit -> retained/minimal EWT union, document caps, ESL exposure views, literal byte/cosine semantics, exact fresh-GUM offsets/common validity gates, common-frame/local/propagated diagnostics, source hashes, SDPA unification, observer terminalization, and science adapter constraints remain present.
- No model configuration or weights were loaded, no tensor library was imported or tensor executed, no forward pass/experiment was run, and no implementation file was modified.

CONTRACT COVERAGE

- V5 revision: literal five-bin grid batch schedule/order/padding -> met (`PLAN.md:42-47,77,114`).
- V5 revision: all SDPA Boolean values and library allowlist semantics -> met (`PLAN.md:81,88,114`).
- V5 nits: reconstructed/technical-source terminology -> met (`PLAN.md:40,84,88`).
- Exact five-bin grid and diagnostic counts -> met (`PLAN.md:42-46,77,81,88`).
- Retained-EWT plus minimal-EWT calibration union -> met (`PLAN.md:36,49,57,95,134,173`).
- Exact fresh-GUM sentinel scientific gate and numerical validity checks -> partial — mandatory status, offsets, non-pooling at the decision level, cached/live/finite/lineage checks, and per-pair passage are frozen, but the one-shot inference order/batch shape is not (`PLAN.md:49,77,146-150,175`).
- Cross-stage SDPA/runtime lineage -> met for named runtime state and grid/science paths (`PLAN.md:77,81,88,114,155-156`), but cannot yet be evaluated for the underspecified sentinel schedule.
- Diagnostic validity and causal-claim restraint -> met (`PLAN.md:79-88,195,197`).
- Support/exposure/source firewalls -> met in plan (`PLAN.md:23-24,38-49,118,196,198`).
- Fail-closed sequencing before validation/science -> met structurally (`PLAN.md:92-98,128-159,192-198`).
- No-training boundary -> met (`PLAN.md:9-15,120-126,157,177`).
- Safe to implement/open fresh validation -> unmet until the exact sentinel inference schedule is frozen and independently reviewed.

UNKNOWNS

- Whether each `65-128` cell clears the frozen document/exposure support gates; no-inference prescore correctly owns this and must fail closed.
- The historical attempt-7 runtime did not record the concrete PyTorch SDPA kernel choice; the plan's complete environment/dispatcher attestation remains the strongest reconstructable lineage once every inference population, including the sentinel, has a unique batch schedule.
