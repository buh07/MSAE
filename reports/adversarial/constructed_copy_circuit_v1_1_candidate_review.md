VERDICT: SHIP

ONE-LINE: The launcher-death blocker is fixed; parent-only TERM and KILL now terminate guarded children without continuation.

BLOCKERS
  (none)

REVISIONS
  (none)

NITS
  (none)

CHECKS RUN
  - Launcher shell syntax → PASS
  - Full targeted test suite → 28 passed
  - Candidate preflight → PASS; paper verifier passed 72 claims and 329 bindings

CONTRACT COVERAGE
  - No launcher retry → met
  - No signal continuation → met
  - Durable PID/PGID publication before child release → met
  - ERR reconciliation waits for guarded execution termination → met
  - Launcher-only TERM and SIGKILL regression coverage → met
  - Preopening firewall and prior scientific requirements → met

UNKNOWNS
  - GPU smoke was lineage-checked rather than rerun.
  - No prohibited scientific payload was resolved, statted, hashed, globbed, listed, opened, or read.
