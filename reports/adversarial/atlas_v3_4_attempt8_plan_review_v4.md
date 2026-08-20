VERDICT: BLOCK
ONE-LINE: SDPA attestation omits cuDNN dispatch, and the observer count covers only 20 of 140 diagnostic units.

BLOCKERS

- [critical] `PLAN.md:25,81,88,114,173`; `requirements-atlas.lock.txt:11,14` — the revised plan unifies the named Transformers backend as `sdpa`, but its supposedly exact runtime attestation is neither accurate nor complete. It requires `torch==2.7.0+cu128`, while both installed package metadata and `torch.__version__` are exactly `2.7.0` and the lock says `torch==2.7.0`; CUDA is separately `torch.version.cuda == "12.8"`. More importantly, the plan binds only the flash, memory-efficient, and math SDPA enable flags. Installed Torch 2.7 also exposes `CUDNN_ATTENTION`, and `torch.backends.cuda.cudnn_sdp_enabled()` is currently `True` alongside the other three flags.
  reasoning — `_attn_implementation == "sdpa"` selects the Transformers integration, not a unique PyTorch SDPA kernel. PyTorch may dispatch among flash, efficient, math, and cuDNN attention according to enabled flags, inputs, hardware, and compiled runtime. Omitting an enabled backend from the frozen state leaves the exact reduction path under test unattested. Conversely, a literal assertion of the nonexistent `2.7.0+cu128` package version makes every compliant run fail before scoring or encourages an ad hoc interpretation of an “exact” contract.
  impact — the v3 eager/SDPA mixing blocker is narrowed but not fully closed. Calibration, held-out validation, and byte-frozen science could use different compiled attention kernels while all satisfying the current plan, reopening the same numerical-lineage ambiguity at the irreversible validation gate.
  fix — bind `torch.__version__ == importlib.metadata.version("torch") == "2.7.0"` and `torch.version.cuda == "12.8"` as separate fields. Freeze and assert all four Torch 2.7 CUDA SDPA flags, including `torch.backends.cuda.cudnn_sdp_enabled()`, to their intended values in calibration, every validation bundle, diagnostic/observer processes, and science. Bind the complete enabled-backend vector and relevant compiled dispatcher/library hashes before EWT. Fail closed on any backend member/flag drift, and add a synthetic fixture proving the attestation detects cuDNN-flag drift.

- [high] `PLAN.md:81,88,124,131,195` — the hooked diagnostic runs 20 bases at an ordinary reference plus six shifts, i.e. 140 distinct model input/position-ID units, but the observer clause says only “The same 20 inputs are also run unhooked.”
  reasoning — the shift changes `position_ids`, so the six candidates are distinct inference inputs even when their token IDs equal the reference. Comparing only 20 ordinary-position bases cannot detect a hook effect restricted to shifted calls, later batches, or a particular shift/length cell. The plan then makes a valid observer comparison mandatory before validation, so “20” cannot safely stand in for the 140 executed units.
  impact — an incomplete observer can certify a hooked diagnostic as valid and permit irreversible validation even though up to 120 shifted diagnostic executions were never checked for observer effects. It also violates the requested post-bin count consistency.
  fix — require the unhooked process to execute the exact same hashed 140-unit manifest: 20 ordinary-position references plus 120 shifted candidates. Compare every returned hidden-state tensor needed by the diagnostic, with identical unit order, shapes, dtype, batch schedule, and byte semantics; any missing/mismatched unit signs `TERMINAL_TECHNICAL_DIAGNOSTIC_INVALID`.

REVISIONS

- [medium] `PLAN.md:42-47,61,77,114-118` — the five-bin candidate arithmetic is correct, but the exact population contract states only candidate counts. Freeze the corresponding 100 reference units/200 selected reference rows and 700 distinct reference-plus-candidate units/1,400 selected rows per source. Also freeze the stable unit order, reference/candidate batching schedule, padding maxima, and final partial-batch rule. The inherited batch size and batching layout affect SDPA dispatch and floating-point output and therefore cannot remain implicit in a numerical-estimator study.
- [medium] `PLAN.md:88,114` — define whether `/proc/self/maps` attestation requires equality of the loaded Torch/CUDA library *set* across processes or only equality of hashes for a frozen required allowlist. Diagnostic and scientific processes may load different supersets. Prefer a prescore-frozen required library path/SONAME/hash allowlist plus rejection of conflicting duplicate SONAMEs; otherwise “drift is ineligible” is not uniquely executable.
- [low] `PLAN.md:88` — `local_rotary` still says “native float32” although every post-RoPE tensor is reconstructed out of band. Rename this occurrence to “reconstructed float32” so the report cannot imply that executed post-RoPE Q/K were captured.

NITS

- `PLAN.md:40` — EWT is calibration, not an authorizing validation source; rename “each authorizing source” to “each technical source” to match the role firewall.

CHECKS RUN

- `/jumbo/lisp/f004ndc/.agent-workspace/bin/check-plan --path PLAN.md` -> PASS.
- Read-only line-by-line review of `PLAN.md` against `reports/adversarial/atlas_v3_4_attempt8_plan_review_v3.md` -> the retained/minimal EWT union wording, exact fresh-GUM common gates, mandatory diagnostic terminal, reconstructed tensor label, transport arithmetic, direct source hashes, and cross-stage `sdpa` assertion are now present.
- Static source-hash audit in `.venv-atlas` -> all hashes at `PLAN.md:81` match the installed source, including `_autoset_attn_implementation=574b00831199f419a24669d08d9bbd16d239024f2c979d03085df3a2ccbe56fb` and `sdpa_attention_forward=601d992611ca2f1854db8559f146f7b4165af30456e2a686c9f1e741eb77e04b`.
- Static runtime-metadata audit without model loading -> installed/package-lock Torch is `2.7.0`, `torch.version.cuda` is `12.8`, cuDNN is `90800`; `torch==2.7.0+cu128` is not the installed package version.
- Static Torch SDPA audit without tensor execution -> `SDPBackend` includes `MATH`, `FLASH_ATTENTION`, `EFFICIENT_ATTENTION`, and `CUDNN_ATTENTION`; flash, memory-efficient, math, and cuDNN SDPA flags all report enabled, but the plan records only the first three.
- Arithmetic count audit for five bins -> 100 bases, 30 shift×length cells, 600 candidates, 1,200 candidate rows, 100 references, 200 reference rows, 700 unique units, and 1,400 unique selected rows per source. The explicit candidate/cell counts at `PLAN.md:43-46` are correct.
- Arithmetic diagnostic audit -> five bins × four bases = 20 bases; reference plus six shifts = 140 inference units, not 20 observer inputs.
- No model configuration or weights were loaded, no tensors or forward passes were executed, no experiment was run, and no implementation file was modified.

CONTRACT COVERAGE

- V3 blocker: one SDPA backend across retained calibration, new calibration/validation, diagnosis, and science -> partial — all paths now assert Transformers `sdpa`, but the enabled cuDNN SDPA backend and exact Torch-version semantics are missing from the runtime attestation (`PLAN.md:81,88,114,155-156`).
- V3 revision: retained-EWT plus minimal-EWT union wording -> met (`PLAN.md:36,49,57,95,134,173`).
- V3 revision: exact fresh-GUM cached/live/finite/lineage/completeness gates -> met (`PLAN.md:49,146-150,175`).
- V3 revision: diagnostic-invalid state transition -> met in intent (`PLAN.md:88,195`), but the observer input population is incomplete.
- V3 revision: reconstructed tensor naming and exact transport arithmetic -> met except one residual “native” label (`PLAN.md:81-88,116`).
- V3 nit: direct integration/autoselection source hashes -> met and independently verified (`PLAN.md:81`).
- Five-bin cell/count consistency -> met for stated candidate counts; partial for total reference-plus-candidate and observer counts (`PLAN.md:42-49,81,88`).
- Document diversity and prescore-ineligibility -> met (`PLAN.md:42-47`).
- ESLSpok exposure firewall -> met in plan (`PLAN.md:23-24,118,198`).
- Cellwise coordinate/L2/cosine validity and fail-closed source order -> met (`PLAN.md:53-71,144-150`).
- Mechanically unchanged science adapter -> met structurally (`PLAN.md:152-159`), conditional on completing the effective-SDPA runtime contract.
- No-training/no-inference planning boundary -> met (`PLAN.md:9-15,120-126,177`).
- Safe to begin implementation or irreversible inference -> unmet until complete SDPA dispatch attestation and full 140-unit observer replay are frozen and reviewed.

UNKNOWNS

- The exact PyTorch SDPA kernel chosen in the historical attempt-7 calls was not contemporaneously recorded. A complete frozen dispatcher state reproduces the strongest available lineage; the current three-flag state does not.
- The numerical minimal-path batch size/order/padding schedule is described as fixed but is not literal in `PLAN.md`; it must be resolved before implementation because it can affect SDPA dispatch.
- Whether the added `65-128` cells satisfy the document/support/exposure rules for all three sources; prescore must measure this without inference and fail closed if any cell is infeasible.
