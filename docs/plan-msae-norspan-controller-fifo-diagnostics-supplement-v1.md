# Prospective synthetic FIFO phase diagnostics supplement v1

2026-09-16. Source-free harness change only. Original independent two3-second
subprocess timeouts remain failures; their bootstrap-vs-reader cause is UNKNOWN.
The earlier observation supplement's conditional cause attribution is NOT met.
This separate proposal prospectively qualifies both phases without attributing
those historical failures or weakening the actual reader's3-second deadline.

Start one owned child with bytecode writes disabled, captured stderr and a pipe
for READY. A bounded30-second bootstrap must reach READY after imports, immediately
before the unchanged actual reader. Then the unchanged3-second reader deadline
must complete with GateFailure (return0); success/other exit, missing READY or
EITHER timeout fails. Emit READY once and flush. Drain the small diagnostics, close
owned pipes and kill/reap the same owned child on every exit/error/interrupt; no
retry, masking or treatment of timeout as a rejection. Reuse subprocess.run or
Popen communicate's verified cleanup obligations, with explicit finally kill/wait
when using Popen. Only fresh synthetic FIFO paths and synthetic fake repos.

Freeze the exact public test and this plan in the successor candidate, preserve
old49 and both root/independent results, and requalify all four reader variants.
The30-second bootstrap bound applies only to the test interpreter imports, NOT
production I/O, process containment, scientific scoring or launch authorization.
All unconditional guards remain. Add this finite plan to public signed inputs;
no protected bytes, real census/status/source/payload/model operation is permitted.
