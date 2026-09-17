# NORSPAN namespace route: source-only architecture audit v1
2026-09-17. **No launch authority; no containment row closed.**

## Observations and authority limits
The exactly reviewed prerequisite diagnostic established one successful userns
creation and one EACCES self-migration. It did not exercise PID/mount/network
namespaces, descendant lifetime, fork limits, writable-volume bounds or escape.
The denied write is not repeated. No administrator contact or host fallback.

Installed `/usr/bin/bwrap`: root:root, mode0755, 72,160bytes,
SHA256 `52231e1caf55bcbc667b269f49c63599a6f7db4767ae6a039580d0ff853db712`;
device66306/inode2268458 observed. Version output0.9.0; dpkg package
`bubblewrap 0.9.0-1ubuntu0.1`. These observations are not binary/source equivalence.
No setuid bit was observed; file capabilities and distro patches remain unqualified.

A finite public source-only download is retained under the path in
`reports/verification/msae_norspan_namespace_source_audit_root.txt`:
- upstream v0.9.0 `bubblewrap.c`: SHA256
  `6a89bc9b7a794d19e2bdb1e139ab9d5bba84e807b330336f363f88f130cfeab6`;
- upstream v0.9.0 README: SHA256
  `b5d1774fded9ae05cf6f6d9b6fc277cb6b59b138dd6ccada0372390ad89d39f3`.

[Upstream source](https://github.com/containers/bubblewrap/blob/v0.9.0/bubblewrap.c)
and [README](https://github.com/containers/bubblewrap/blob/v0.9.0/README.md).
Line numbers below refer to the retained raw3398-line C file, not a web renderer.
No fetched source is compiled/executed. No installed bwrap sandbox is launched.
No real NORSPAN source, Git candidate, protected content or model is touched.

## Relevant upstream lifecycle, not a binary equivalence claim
1. Initial process builds namespace clone flags and child-wait eventfd, then creates
   a child using `raw_clone(clone_flags,NULL)` at line2900. The outer Python caller
   could own an original pidfd of the initial process; that is not a pidfd of this
   newly created child. No pidfd API/transport appears in this C source.
2. Initial process observes namespace IDs/maps, drops privileges, installs its
   parent-death setting at2958, reports child PID/status, and optionally reads
   userns-block-fd at2976–2980. It releases child-wait at2983–2987, then monitors.
   The block read's result is ignored; EOF is not a strict nonce GO authorization.
3. Child setup performs namespace/mount/root construction; supplied pidns mode can
   introduce intermediate forks. Privileged setup has another fork at3123. These
   paths must be excluded or independently owned; installed mode alone does not
   establish the privilege configuration or observed helper graph.
4. Later block-fd is read at3261–3265, after root construction/privilege drops.
   Its read result is likewise ignored. Closing a control pipe is not a fail-closed
   substitute for a bootstrap authorization protocol.
5. Default PID-namespace path forks the command at3317. PID1 closes selected FDs,
   reaps in do_init, and reports initial-command status. Command calls the
   parent-death handler at3362 before capability/seccomp/exec setup at3383.
   As-pid-1 avoids this command fork, but does not remove the initial clone or
   prove monitor/bootstrap death behavior or before-release cleanup.
6. Parent-death handler378–382 sets PR_SET_PDEATHSIG but contains no original
   parent-pidfd poll/handshake. Linux documents that the setting is cleared on
   fork and can be cleared by credential changes; setting it after a parent has
   already died does not retroactively signal the child.
   [Linux parent-death semantics](https://man7.org/linux/man-pages/man2/PR_SET_PDEATHSIG.2const.html).

These are protocol integration gaps, not a claim that bubblewrap is generally
unsafe or that a successful escape occurred. Its monitor/init/wait logic provides
useful lifecycle machinery, but it has not been shown to satisfy NORSPAN's exact
original-handle ownership and fail-closed release contract under killed supervisors.
Namespace-init death can contain descendants after ownership is established;
that does not establish early bootstrap custody or original descriptor cleanup.

## Prospective route decision and missing proof
**Do not launch an unmodified installed-bwrap route as qualified containment.**
No option combination has yet been reviewed to close the early-child custody and
EOF-release gaps, nor exact patched-binary provenance and runtime dependencies.
A numeric child PID from info-fd is observation, not authenticated original custody.
Pidfd-opening by an observed number after an uncontrolled process has run/exited
is not equivalent to a pidfd supplied at creation; generic descendant scans and
killpg are not substitutes. Nor does die-with-parent alone close the stated race.

Next implementation must prospectively choose and review ONE exact mechanism:
- owned bootstrap that performs no uncontrolled work/fork before the original-child
  handle and strict release handshake; creates namespace-init with atomic original
  handle custody (e.g. reviewed CLONE_PIDFD route), transfers it before release,
  retains an original owner-parent pidfd across every credential/setup boundary,
  and proves every helper edge; OR
- a reviewed instrumented/package-reproduced bwrap integration providing equivalent
  custody, strict EOF rejection, parent-death race closure and explicit helper graph.

This audit does not select or authorize either implementation. A concrete launch
plan must bind source/compiler/binary/runtime, args, minimal mounts, environment,
FD allowlist, deadlines, original handles and before-release failure semantics.
It must separate facilities from enforcement and attempted escape detection. Synthetic
forbidden host objects and inherited-FD controls must be capable of detecting escape.

Resource proof remains independent: PID/mount/net namespaces do not enforce
512 family processes,4096 aggregate descriptors or64GiB aggregate writable disk.
UID-wide RLIMIT_NPROC, per-process NOFILE and per-file FSIZE do not by themselves
establish these family-wide bounds. Writable tmpfs sizing also needs retention/
durable-output and exhaustion analysis; evidence custody remains on Jumbo. Any
changed enforceable contract must be prospectively reviewed, not inferred here.

## Unchanged status
All9 qualification groups/80 whole rows remain OPEN; guard stays first/unconditional.
No real history/source/raw/private/payload/scoring/K2/branch/G3/C2 operations.
All old BLOCK/scoped SHIP reports and failed roots remain. Whole technical approval,
canonical binding and exact final owner receipt precede independent-source eligibility.
