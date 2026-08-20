VERDICT: SHIP
ONE-LINE: Hash-bound recovery preserves Attempt 11, isolates one-shot ridge analysis, and sharply limits claims.

BLOCKERS        (must fix before proceeding; empty if none)
  - None.
REVISIONS       (should fix; not blocking)
  - None.
NITS            (optional, cap at 5)
  - None.

CHECKS RUN
  - `/jumbo/lisp/f004ndc/.agent-workspace/bin/check-plan --path /jumbo/lisp/f004ndc/experiments/wip/MSAE/PLAN_ATTEMPT12.md` → PLAN: PASS.
  - `sha256sum PLAN_ATTEMPT12.md` → `905a7545db682c473a4dad0904a18fbab19be49d5e6d86de099efccc34f2d067`, exact requested plan.
  - `sha256sum` on Attempt-11 terminal, science authorization, adapter, validation completions, frozen analyzer/config files, and cache/QA completions → all inspected hashes match the plan and signed lineage.
  - `nvidia-smi --query-gpu=index,uuid,name --format=csv,noheader` → physical 0 is `GPU-ec526219-fb07-e57e-a30d-5d2ab843fb15`; physical 1 is `GPU-9b529a09-92a6-caea-fee2-6b2bf07b0e4e`.
  - `CUDA_VISIBLE_DEVICES=0 .venv-atlas/bin/python` Torch device query → exactly one visible device; visible `cuda:0` UUID is `ec526219-fb07-e57e-a30d-5d2ab843fb15`; no model was loaded or run.
  - Validation completion payload inspection → both panels are `COMPLETE` with `integrity_runtime_pass=true` and `approximate_equivariance_pass=true`.
  - Attempt-12 namespace inventory → only `PLAN_ATTEMPT12.md` exists; config, run, and result namespaces are absent.
  - Read-only inspection of `TERMINAL.json`, Attempt-11 science config/controller/wrapper, EWT/GUM cache and QA envelopes, frozen adapter, prepared manifest contract, analyzer loader/runtime guard, and overlay function → plan premises and proposed unchanged invocation are grounded.

CONTRACT COVERAGE
  - Forbidden Attempt-11 continuation → met — PLAN_ATTEMPT12.md:9,17,37,102,149 preserve the signed terminal, prohibit old stages/writes, and reject the old analyze stage.
  - Exact cache/source lineage → met — PLAN_ATTEMPT12.md:22,45,59-60,151 bind signed completions, bytes/hashes, row IDs, canonical arrays, manifest, and every analyzer-opened EWT/GUM child.
  - Physical/visible GPU mapping → met — PLAN_ATTEMPT12.md:23-24,54-58,74,84,164 require physical index, UUID, visibility-count, adapter, extraction-role, and live pre-run agreement.
  - Output isolation → met — PLAN_ATTEMPT12.md:30-37,61,75,86-88,149-156 require new roots, absence guards, atomic create-once promotion, and before/after Attempt-11 preservation.
  - One-shot semantics → met — PLAN_ATTEMPT12.md:70-76,78,88,117,133-138,162,165 require create-once authorization/start, one attempt, permanent closure, terminalization, and no retry.
  - No model forward or training → met — PLAN_ATTEMPT12.md:10,48,62,64,76,120,152-158,177 forbid and audit model loading/forward, extraction, validation execution, optimization, and training.
  - Unchanged scientific protocol → met — PLAN_ATTEMPT12.md:11,45-48,80-86,102,154-156,167 bind frozen code/settings/data and limit monkeypatches to verified loading callbacks.
  - Claim scope → met — PLAN_ATTEMPT12.md:12-13,43,86,92-98,142-145,163 keep the outcome exploratory/non-promotable and require independent post-result claim review before any nomination is interpreted.

UNKNOWNS
  - Attempt-12 code, tests, implementation candidate, signed preflight, freeze candidate, authorization, run, and claim review do not yet exist; their exact evidence remains for M2-M5 and the mandatory freeze-candidate review.
  - The freeze review must confirm that the no-model audit proves no reachable Attempt-12 dispatch path into the legacy extraction CLI imported transitively by the frozen analyzer.
  - The freeze review must confirm atomic exclusive creation and failure-only terminal reconciliation for abrupt runner death; it must never re-enter analysis after `STARTED.json`.
