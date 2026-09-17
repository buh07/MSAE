VERDICT: SHIP
ONE-LINE: Separate admission-monitor custody from intended reader/parent fault injection, prove each fault fires, and include the missing public test dependency.

BLOCKERS
  - None for the revised exact synthetic-test-custody proposal.

REVISIONS
  - None remaining after the coordinator accepted actual monitor identity separation in both adapters and client repairs.

NITS
  - None.

CHECKS RUN
  - Read bounded public tests/test_msae_norspan_jpc_adapters.py:93-119, tests/test_msae_norspan_client_repairs.py:46-64 and independent monitor fault cells tests/test_msae_norspan_jpc_controller_matrix.py:339-351.
  - Read public tests/test_msae_jumbo_pair_commit.py:184-188 -> direct import of diagnose_msae_jumbo_nfs_v1 and actual synthetic link_case execution.
  - Read only public scripts/diagnose_msae_jumbo_nfs_v1.py:1-48 -> explicitly fresh synthetic diagnostics, no real experiment data; controlled subjects are created by the diagnostic.
  - Read the two named public run pointers and bounded matching sections of their synthetic run.log transcripts -> root successor run5 failed/386 passed in33.76s; extracted reproduction6 failed/385 passed in17.59s. Both reach the admission monitor close before the intended read-primary, and injected KeyboardInterrupt aborts suite execution. Extracted reproduction also records the missing diagnostic import.
  - No tests, runtime changes, real census/status/credential/source/raw/private/payload reads, Git/acquisition/network requests, model/GPU command or administrator contact executed.

CONTRACT COVERAGE
  - Diagnosis grounded in actual failures -> met: adapter IndexError arises at target[0] before the wrapped parent constructor can append a target. Client repair close faults arise in _current_fd_count before original-read-fault. The retained transcripts establish these specific nonfiring test cells; they do not establish a production defect or historical FIFO cause.
  - Adapter fault remains real and specific -> met prospectively under the revised proposal: snapshot actual monitor dev/inode; fstat before realclose; always realclose; record monitor closure separately and exclude only that actual monitor from the old seen/injection list. Guard target access with if target, and assert exactly one intended parent fault plus observed monitor closure.
  - Reader primary and secondary release coverage preserved -> met prospectively: opened/closed fault accounting excludes only actual monitor identities; all monitors still really close. Every nonmonitor owned reader/ancestor close retains the old injected OSError/KeyboardInterrupt behavior and notes checks. Assert the actual original os.read fault fires exactly once.
  - No hidden monitor-failure exemption -> met prospectively: separate maintained monitor-close OSError/KeyboardInterrupt cells remain required and unchanged. Test-only scoping does not suppress real runtime monitor failures or change production behavior.
  - Correct FD lifecycle accounting -> met prospectively: separating monitor generations avoids conflating legitimate numeric FD reuse with double-close. The initial if-target-only revision was insufficient for adapters:117; the accepted monitor-identity separation resolves that flaw without weakening actual subject-release coverage.
  - Reproducible finite public checkpoint -> met prospectively: include the missed PUBLIC TEST-ONLY diagnostic script in a separately named exact successor60freeze/checkpoint. Preserve old59/root/extracted failures and previous frozen candidates/reviews; do not repair an old manifest in place.
  - Scope -> met prospectively: no immutable science/configuration change, guard removal, protected input, production behavior change, retry or timeout-as-pass is proposed. No additional plan document is required for this concrete bounded free-text proposal.

UNKNOWNS
  - Use actual pre-close dev/inode identity, not FD integers, path substring matches or blanket exemption of all pre-reader operations. Track monitor open/close evidence separately; monitors must never be omitted from real release.
  - After applying the revised tests, independently observe exactly-one intended parent/read firing, preserved secondary notes, original-chain release and monitor-close coverage. Current failing runs remain failing evidence, not retroactively green.
  - Freeze the new diagnostic's exact public bytes/mode and ensure its finite public import dependencies are present in the extracted reproduction environment. Adding one script by count alone does not prove closure.
  - Root and extracted full explicit suites must be rerun on the same newly frozen exact candidate with retained transcripts. Aborted prior suite counts cannot demonstrate completion or execution of remaining cells.
  - This prospective test repair does not qualify real history/source authorization, arbitrary helper/network exclusion, hard resource containment, owner trust or production launch. Earlier FIFO timeout causes remain UNKNOWN.
