# Prospective recovery metadata supplement v1

2026-09-16. Supplement to frozen controller qualification v1, not production authority.

The phrase "recovery does not rerun Git" in Q3 means no acquisition Git command,
network/source operation, clone/checkout/object acquisition or producer retry.
It does NOT prohibit the existing local `git status --porcelain` repository-status evidence census
used by actual evidence_snapshot and its unchanged evidence/compatibility predicates.
Skipping that census would remove a gate; reimplementing Git index/status is rejected.

Full recovery will retain current actual history/config/authority/phase/evidence
validators. A context records local repository-status evidence census attempts and completions, and
reports these separately from zero source/network/acquisition/model operations.
No total-zero-subprocess claim is permitted. The local status operation
must be made bounded in duration/output before qualification; current unbounded subprocess.run is NOT already qualified. Git status may inspect worktree content and is NOT guaranteed payload-free. It must not acquire remote source. No invocation on a real repository is permitted in this task. Failures remain
operational BLOCK. Synthetic fixtures replace only the local process/status producer,
not validators; supervisor child-cleanup tests and explicit zero acquisition-command
assertions remain mandatory. Guard remains unconditional. No real recovery is run.
