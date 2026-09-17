# Restricted preflight runtime/fixture closure v2
2026-09-17. Prospective successor supplement; NOT launch or production authority.
Keep the v1 contract and initial implementation BLOCK immutable. v1's host runtime
closure applies unchanged. Only the following public implementation repairs follow:

- Single-attempt control/read FD close preserves the original initiating exception.
  Secondary close notes force BLOCK even when the physical FD baseline is restored.
  D1 serializes primary and original cleanup notes; blocked D1 cannot authorize D2.
- One D1 setup deadline starts at arm entry. Each observed setup operation checks the
  original budget; successful mkdir is recorded BEFORE the next deadline check. Partial
  nodes remain. Parked receives only the remaining budget; before child creation and
  GO, parked rechecks its original deadline. Uninterruptible calls are not hard bounds.
- Active RESULT requires exactly returncode, errno, before, after. Integer types are
  exact; observation strings bounded4096. Simplified pure classifier fixtures are NOT
  active protocol evidence. Inert children return explicitly inert observations.
- Killed-owner fixtures have no userns/cgroup handler in their target. Targets invoke
  only the actual parent-death primitive, protocol output/input and local marker write
  if unexpected GO occurs. A marker is inspected, not a constant printed no-GO claim.
- Original pidfds are transferred by SCM_RIGHTS. Owner transfer callback then waits on
  the anonymous peer barrier and ALWAYS raises on message/EOF/error; no sleep/normal
  return can reach GO. Fixture coordinator and target bind their original parents
  before creating children. Only a fresh fixture helper becomes child-subreaper.
- Outer fixture is Popen + original pidfd, not subprocess.run numeric timeout kill.
  Original handles signal/reap only this fixture family. Missing outer pidfd is an
  explicit incomplete-cleanup failure, not a numeric fallback. Inner simultaneous
  supervisor death/family containment is NOT whole qualified by these fixtures.
- Six synthetic killed-owner conditions: early parent death before prctl, parked parent
  death, receiver delayed4.1s, barrier EOF/transport refusal, injected kill refusal with
  fail-closed barrier (not real kernel permission proof), bootstrap refusal before target.
  Every path's target is inert. No real namespace or cgroup operation in this suite.

Only D1a/D2a preflight may be considered after an exact successor implementation SHIP
and frozen runtime/argv/evidence binding. Full fork/escape/bwrap, descendants, mounts,
network, protected-content exclusions, source/science/production authority stay pending.
Earlier BLOCK/scoped SHIP reports remain in force in their own scopes; no9/80 closure.
