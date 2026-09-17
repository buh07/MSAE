# Restricted preflight runtime closure
2026-09-17. Prospective exact implementation-review input; NOT production authority.
The wave1-v2 reviewed implementation slice is retained. This supplement clarifies:
- Child argv includes the fresh nonce immediately after original parent-pidfd.
- Finite own /proc/self/maps root-owned ELF paths complete transitive dependencies,
  including libcrypto.so.3. No ldd subprocess, foreign maps or broad directory crawl.
- Freeze the public interpreter, imported stdlib source and existing cache, loader
  preload/cache/object, finite mapped ELF files, script, tests and exact reviews.
  Directory identities do not attest every descendant. Host loader/preload behavior
  is observed, NOT a sandbox/network/FD/content exclusion guarantee.
- Private synthetic _argv/_on_spawn/_on_ready fixture hooks are absent from the CLI;
  actual active arms use only the fixed frozen no-fork child command.
- Killed-owner fixtures use a dedicated new subreaper and an anonymous socketpair
  to convey ORIGINAL pidfds. Fixture-only transport/forks never access real cgroups,
  namespaces, source, raw/private/payload or model. Root/agent process settings unchanged.
- All original scientific hard containment and9/80 closures stay OPEN. No bwrap
  mount or fork-family launch is authorized by the no-fork preflight scope.
