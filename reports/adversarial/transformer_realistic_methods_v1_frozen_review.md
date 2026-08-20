VERDICT: SHIP
ONE-LINE: Both frozen protocols are byte-bound, separately isolated, unopened, and ready for frozen-review binding.

BLOCKERS        (must fix before proceeding; empty if none)

REVISIONS       (should fix; not blocking)

NITS            (optional, cap at 5)

CHECKS RUN
  - **Bridge frozen verdict** → SHIP.
  - **Methods frozen verdict** → SHIP.
  - Bridge generator lock SHA-256 → `209d5dea28ad43d21b9fbbcc19a7ab5f93f04ca245eb18f28b58549c42eeb942`.
  - Bridge experiment freeze SHA-256 → `59491a943d612f8d394dbfe2263a73bd87edb5e0debb17dec7efc36e20ec841a`.
  - Methods generator lock SHA-256 → `50b2b428a5327312ee10130701cc83cffa74d3ad7e070c371b0807b15b228123`.
  - Methods experiment freeze SHA-256 → `32da54a8eaf2c56d2871ed865a82c700b4e56f165aefdfa2eec0b07ed39f529e`.
  - Every generator-lock and freeze inventory digest → recomputed successfully.
  - Every inventory item → size and SHA-256 verified after first asserting that no inventory path was a scientific `.jsonl` payload.
  - `verify-freeze --kind both` → PASS; bridge inventory `08d5727a9784bee0926b19c0ceda87c27acf28ff65ecd1e2695a9f8177139f95`, methods inventory `96bb24c1adce172ec4c62318f3b8169bc618a24ec416a3163eab85c1eb806ecb`.
  - Candidate SHIP report SHA-256 → `6ab9bc52a922008229a7458c25e9283e26123d08941bd05effb9a0b39cac13c1`; exact report is present in the corresponding bridge and methods generator-lock inventories.
  - Creation ordering → both generator locks at `00:23:17`, metadata/PREPARED records at `00:23:22`, and both freezes at `00:23:24`.
  - PREPARED records → `PREPARED_AFTER_GENERATOR_LOCK` and `scientific_payloads_opened_for_scoring=false`.
  - Frozen opaque metadata → exactly equals each corresponding `PANEL_METADATA.json` record.
  - Bridge and methods output/provenance namespaces → absent.
  - Frozen-review bindings → absent, as required before this review is installed.
  - Python compilation → PASS.
  - Launcher syntax → PASS.
  - Scientific JSONL payloads → not listed, statted, hashed, read, or opened during this audit.

CONTRACT COVERAGE
  - **Bridge freeze is independent** → met — distinct config, lock, freeze, prepared root, output root, provenance root, and candidate inventory.
  - **Methods freeze is independent** → met — distinct config, lock, freeze, prepared root, output root, provenance root, and candidate inventory.
  - Candidate code/config/tests/reviews are bound before panel generation → met.
  - Scientific seeds are locked before payload generation → met.
  - Panels were generated only after both generator locks → met.
  - Experiment freezes contain opaque creation-time metadata without payload bytes → met.
  - Payload paths remain unopened before registered transitions → met.
  - Candidate SHIP evidence is bound into both generator locks → met.
  - Frozen SHIP reports can be bound without changing either freeze → met.
  - Launch validation requires both frozen-review bindings → met.
  - Methods remain unopened unless bridge final status is exactly `TRANSFORMER_REALISTIC_GROUND_TRUTH_CONFIRMED` → met.
  - Methods authorization records the exact bridge-final SHA-256 and methods-freeze SHA-256 → met.
  - A bridge stop produces unopened methods artifacts with no training or method evaluation → met.
  - Existing result/provenance namespaces prevent relaunch or overwrite → met.
  - Tmux launch is one-shot, checks current GPU utilization, acquires a UUID-specific lock, rechecks utilization, pins `CUDA_VISIBLE_DEVICES`, and validates the physical UUID in-process → met.
  - Deterministic CUDA configuration is installed before scientific execution → met.
  - No K2 execution or natural-model claim is authorized → met.

UNKNOWNS
  - The two frozen-review files and resulting bindings do not yet exist; this exact SHIP report must be installed separately at both configured review paths, followed by `bind-reviews` and `verify-review-binding --kind both`.
  - Actual launch-time GPU availability is intentionally deferred to the one-shot launcher.
