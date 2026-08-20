VERDICT: SHIP
ONE-LINE: Frozen inventory, firewalls, lineage, launch isolation, and prerequisites are exact; bind this review before launch.

BLOCKERS
  - None.

REVISIONS
  - None.

NITS
  - None.

CHECKS RUN
  - SHA-256 of `configs/known_mechanism_ioi_v1/FREEZE.json` → exact `d208922048cb60dc215371682ae2bad4a24215b848f98ba981e5069c4e87e60c`
  - Direct 26-entry inventory audit → every byte count and SHA-256 matched; paths canonical and sorted
  - Canonical inventory recomputation → exact `642ca656ccb2f0723969bb11c6b97e7d44af1607a6274762965c5feb7ff8e91c`
  - Config audit → exact `5994bb4c2df74e48de1ff27e2f84f48d0177a9ed8dca1c3b439339d7cd4a233b`
  - Candidate review audit → `VERDICT: SHIP`; exact frozen hash `3409d9e5f7f3aeba0fba0f08b5823e01fb8d64a2d50685b5f683846b62877b0c`
  - `preservation-verify` → PASS
  - Direct v6.2 frozen-inventory audit → all 88 registered artifacts matched
  - `scripts/verify_paper_claims.py` → PASS, 63 claims and 272 evidence bindings
  - Direct prepared-panel audit → all eight payload hashes matched; 256/128 row counts, IDs, and encoded constraints passed
  - Direct cache audit → all 21 records matched, totaling 11,403,071,857 bytes
  - `preflight` → PASS for GPT-2, Pythia, and Gemma families
  - `verify-freeze` → PASS with exact canonical inventory hash
  - `.venv-atlas/bin/python -m pytest -q -p no:cacheprovider tests/test_known_mechanism_ioi_v1.py` → 19 passed
  - Python AST parse of `scripts/known_mechanism_ioi_v1.py` → PASS
  - `bash -n scripts/launch_known_mechanism_ioi_v1_tmux.sh` → PASS
  - Forbidden v6.3 search → no paths found
  - Runtime namespace audit → output and provenance namespaces absent
  - tmux audit → no matching `msae_known_ioi_v1_*` sessions
  - GPU audit → eight distinct idle 49,140 MiB GPUs; launcher requires three below 4 GiB used

CONTRACT COVERAGE
  - Immutable freeze and canonical inventory → met — freeze, 26 files, config, and canonical inventory hashes matched exactly
  - Candidate SHIP binding → met — exact candidate review and hash are frozen
  - v6.2 and closure preservation → met — preservation verification and 88-entry direct audit passed
  - PAPER and claim-ledger closure scope → met — claim verifier passed
  - Prepared panels and cache → met — all hashes, counts, disjointness, encoded constraints, and cached assets passed
  - Confirmation firewall → met — pre-gate workers exclude confirmation payload verification; parsing and model loading occur only after patch authorization at `scripts/known_mechanism_ioi_v1.py:764-785`
  - Completion lineage → met — behavior, patch, and confirmation completions validate artifact, upstream-gate, freeze, and inventory hashes at `scripts/known_mechanism_ioi_v1.py:647-663,743-751,821-824`
  - Deadline and tamper rejection → met — executable timeout/failure and artifact-tamper tests passed at `tests/test_known_mechanism_ioi_v1.py:154-249`
  - UUID/session/handoff safety → met — distinct UUID assignment, one-visible-GPU guard, expected-session collision checks, and live-or-clean terminal classification are present
  - Launch prerequisites → met — namespaces and matching sessions are absent; sufficient idle GPUs are available
  - No v6.3, representation methods, or training → met — forbidden paths absent and launcher schedules only registered positive-control stages
  - Safe to launch after frozen-review binding → met — no immutable-freeze blocker remains

UNKNOWNS
  - Real-model hook behavior and peak GPU memory were not exercised because model forwards were prohibited.
  - This exact review and its SHA-256 must be persisted and bound to freeze SHA-256 `d208922048cb60dc215371682ae2bad4a24215b848f98ba981e5069c4e87e60c` before launch.
