VERDICT: SHIP
ONE-LINE: Both r2 freezes are exact, payload-continuous, byte-valid over nonpayload inventories, and safe to bind before launch.

BLOCKERS        (must fix before proceeding; empty if none)

REVISIONS       (should fix; not blocking)

NITS            (optional, cap at 5)
  - Recovery `check-bound` is independent of frozen-review bindings and already passes; the launcher separately requires both review bindings on the immediately following gate before GPU enumeration.

CHECKS RUN
  - Both candidate SHIP reports inspected and hash-bound by their generator locks/freezes.
  - Both generator-lock/freeze canonical digests and every listed nonpayload byte count/SHA-256 → PASS; no inventory contains `.jsonl`.
  - `verify-freeze --kind both` → PASS; bridge digest `2e8d462b…`, methods `f77ac18e…`.
  - Generator locks → bridge `0d73edd1…`, methods `cd174056…`; freezes → bridge `47086bb1…`, methods `6d2c8b1b…`.
  - Recovery `check-bound` → PASS, `payloads_accessed=false`, PRELOCK `f21df200…`, continuity `986d8958…`.
  - Old-v1 opaque freeze metadata, r2 PANEL_METADATA, r2 freeze metadata, and continuity → exact stage/basename/bytes/rows/SHA equality across all five panels.
  - Bridge development 316,996 bytes / 1,152 rows / `86026aaf…`; confirmation 319,363 / 1,152 / `a879c530…`.
  - Methods train 143,713 / 512 / `cee6c16a…`; development 56,095 / 192 / `a2af3bc8…`; confirmation 56,463 / 192 / `1a160f36…`.
  - PREPARED records bind lock inventories, state `PREPARED_AFTER_GENERATOR_LOCK`, and `scientific_payloads_opened_for_scoring=false`.
  - Both freezes bind parity, authorization, preservation supplement, superseded index, continuity, configs, source, verifier, launcher, plan, candidate reviews, and appropriate QA artifacts.
  - Same-namespace retry/science change remain unauthorized; old terminals/freezes/bindings verify.
  - Frozen bindings, r2 outputs, and r2 run-provenance paths were absent during audit.
  - Launcher ordering → namespace absence, recovery check, both review bindings, then GPU enumeration.
  - Methods open only after exact confirmed bridge; otherwise `BLOCKED_UNOPENED`; K2 absent.
  - No scientific JSONL or scientific computation accessed.

CONTRACT COVERAGE
  - Generator-before-preparation → met.
  - Exact opaque payload continuity with unopened v1 → met.
  - Bridge/method freeze isolation → met.
  - Parity/recovery and candidate bytes bound → met.
  - Original namespace immutability/no-retry → met.
  - Review-before-launch sequential gates → met.
  - Methods conditionality/no K2 → met.
  - Payload firewall → met.

UNKNOWNS
  - Frozen reviews must still be persisted/bound and live verification rerun.
  - GPU availability, tmux startup, scientific outcomes, and method authorization remain unknown.
