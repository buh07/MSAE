# Independent NORSPAN namespace source architecture review

2026-09-17. **VERDICT: SHIP for the SOURCE-ONLY audit and its no-unmodified-launch decision.**

This is not a containment-route SHIP, implementation review, launch binding, probe
approval, or whole qualification. No route is selected, implemented, or launched;
no applicable containment row is closed. Route qualification remains BLOCK pending
prospective exact mechanism and launch reviews. All9groups/80whole rows remain OPEN;
the first/unconditional production guard is unchanged.

## Scope and independently checked identities

Read only the two named analysis/plan documents, the named source-root pointer,
that exact root's `bubblewrap-v0.9.0.c` and `README-v0.9.0.md`, the public
`scripts/msae_norspan_containment_preflight.py` source, and metadata/hash of
`/usr/bin/bwrap`. The sole write is this distinct mode0644 report.

No bwrap execution, test execution/collection/import, source acquisition, network,
Git/source candidate, namespace/cgroup/fork/supervisor probe, process scan, actual
keys/history/private/blind/state access, or denied-write retry was performed.

The pointer identifies:
`/jumbo/lisp/f004ndc/tmp/lisplab1/norspan-namespace-source-audit-p2ewVVv8`.
Local SHA256 checks reproduce:

| Subject | Independently observed SHA256 |
| --- | --- |
| `bubblewrap-v0.9.0.c` (3398 lines) | `6a89bc9b7a794d19e2bdb1e139ab9d5bba84e807b330336f363f88f130cfeab6` |
| `README-v0.9.0.md` | `b5d1774fded9ae05cf6f6d9b6fc277cb6b59b138dd6ccada0372390ad89d39f3` |
| `/usr/bin/bwrap` | `52231e1caf55bcbc667b269f49c63599a6f7db4767ae6a039580d0ff853db712` |

Installed-file metadata also matches the analysis at lines10–14: regular file,
root:root, mode0755, size72160, device66306, inode2268458. No setuid bit is present
in the observed mode. Version/package observations are inherited claims, not
independently re-executed here. File capabilities, distro patches, compiler/build
options, runtime dependencies and equivalence to the retained upstream-labelled
source are NOT qualified. Local hashes verify retained-content identity, not
independently fetched upstream provenance or binary/source equivalence.

Prior successful userns/EACCES observations are reported by the named documents;
this source-only review neither revalidates their excluded result artifacts nor
repeats them.

## Source findings supporting the restricted SHIP

All C references below are to the retained raw C file.

1. **Original initial-process custody is not namespace-child custody.**
   Namespace flags are built at2842–2868; child-wait eventfd is created at2871;
   the initial process calls `raw_clone(clone_flags,NULL)` at2900. No pidfd API,
   atomic pidfd request or pidfd transport appears in this C file. Child numbers
   are exported by info/status at2960–2974, not original child descriptors.
   Therefore a caller's original handle to the initial bwrap process does not,
   by itself, supply an original handle to its namespace child. This supports
   analysis lines30–33 and67–70, without claiming anything about unseen helper
   implementations or declaring all possible external integrations impossible.

2. **Both public block gates are fail-open on EOF relative to the stated nonce
   authorization contract.** The parent ignores the read result at2979 and then
   releases its child via eventfd at2983–2987. The later child ignores the read
   result at3264 and continues toward fork/exec. Neither gate checks a nonce,
   positive read count, strict GO frame or original-owner liveness. A closed
   control pipe is consequently not authorization refusal in these branches.
   Analysis lines34–44 accurately describes these integration gaps. This is
   source reachability, NOT an observed execution, escape or cleanup outcome.

3. **The internal eventfd is not a fail-closed parent-death handshake.** The
   child-side wait at3037–3039 is after the supplied-pidns intermediate-fork
   branches at2992–3015. The ordinary child also has no preceding call to the
   C parent-death handler. Its inherited eventfd reference is not a pipe read
   end whose writer closure is a GO refusal; the C wait supplies no original
   parent pidfd check. Thus early helper ownership and stopped bootstrap cleanup
   cannot be inferred from this gate. No child/monitor death was actually tested.

4. **Helper graph remains conditional and unqualified.** Supplied-pidns mode
   invokes `fork_intermediate_child` at2998 and3007, and selects a reported
   numeric PID at2924–2928; subreaper setup occurs at2893–2897. Setuid-privileged
   mode forks an unprivileged setup helper at3123, performs setup at3130–3133,
   serves privileged requests at3147–3155, and waits at3157. The ordinary
   nonprivileged path calls setup directly at3163. `acquire_privs` distinguishes
   modes at839–896; credential changes occur in the routines at899–947 and
   subsequent namespace setup at3206–3259. Observed mode0755 alone must not be
   substituted for an exact frozen runtime/helper graph. Included helper/build
   dependencies at20 and39–41 are outside this finite audit; complete compiled
   helper behavior is not certified.

5. **Parent-death signal, init lifetime and family-drained success are distinct.**
   `handle_die_with_parent` at378–382 only conditionally sets PR_SET_PDEATHSIG;
   there is no original-parent pidfd poll/handshake there. Calls occur in the
   initial parent at2958, init at618, and command at3362—not immediately on every
   child/helper creation. The analysis's fork/credential-reset and already-dead
   parent warning at50–54 is consistent with the absence of race closure in this
   handler; its external manual was not fetched under this review's restrictions.
   The command fork is at3317; init closes selected descriptors at3325–3339 and
   enters `do_init` at3341. `do_init` reports initial-command exit at627–641 and
   continues waiting until ECHILD at644–650; `monitor_child` can return on that
   initial-command report at544–554. A reported command status is therefore not
   itself proof of full-family drain and original-descriptor cleanup. Qualified
   PID-namespace-init death can be useful lifecycle machinery, but its effect
   and early custody remain untested here. `--as-pid-1` skips the final fork via
  3309; it does not remove clone2900 or install an earlier race-closing handshake.
   Analysis lines45–61 does not overclaim these mechanisms.

6. **The earlier no-fork preflight must not be silently extended.** Its child
   sets parent-death behavior and polls an inherited original parent pidfd at
   scripts/msae_norspan_containment_preflight.py:126–135, rejects premature EOF
   at142–147, and requires exact GO plus EOF. Its parent requires single-thread/
   default SIGCHLD at192–193, creates a direct child at205–207, obtains its pidfd
   at208, and uses original-descriptor signal/direct-child wait at172–185.
   A post-creation pidfd for a constrained, original unreaped direct child is
   not the same identity situation as opening a reported number for a potentially
   running/exited/reparented downstream child. Conversely this bounded direct-child
   source does not establish handle custody, race closure or helper cleanup for
   bubblewrap descendants. The prospective atomic-original-handle obligation
   applies to the next route; this report does not reopen or broaden any prior
   scoped preflight approval.

7. **Security policy and resources remain separate.** The retained README
   at53–69 and176–179 places sandbox-policy responsibility on the argument
   constructor, not the tool name. No frozen args/mounts/environment/FD policy,
   actual mandatory PID/mount/net facility results, escape-capable synthetic
   control, or family-wide512-process/4096-descriptor/64GiB-write enforcement
   is supplied by this source audit. Analysis lines81–92 and plan lines26–51
   correctly leave those obligations open. No successful escape is asserted.

## Decision and prospective obligations

No material revision is needed to the narrowed source-only analysis to retain
its decision at analysis lines63–85: **do not launch unmodified installed bwrap
as qualified containment on the current evidence.** This is a missing-proof
stop decision, not a universal claim that bubblewrap is unsafe or cannot be
integrated safely.

The plan at20–25 calls for a route decision or BLOCK. This source-only SHIP does
not complete that stronger milestone: an exact owned-bootstrap or reviewed
instrumented/package-reproduced integration must still be selected prospectively,
with all early children/helpers and original handles accounted for. Distro/source/
build/runtime binding, strict EOF refusal, parent-death race closure across setup/
credential boundaries, bounded before-release cleanup, exact minimal args/mounts/
FD allowlists, causal facilities/enforcement/escape diagnostics, independent
resource-contract proof, and exact implementation/frozen-launch review remain
required before any broader namespace/fork/helper probe. No such probe is approved.

The scientific/whole gates stated at analysis lines94–98 and plan lines53–65 remain
unchanged: no real history/source/raw/private/payload/model/scoring/GPU/K2/branch/
G3/C2 operations; prior BLOCK reports and failed roots remain; whole technical
approval, canonical binding and exact final owner receipt precede eligibility.
