VERDICT: SHIP
ONE-LINE: Retain original accessible-history custody through final aggregate fences; stricter admission must block, never sample or hide history.

BLOCKERS
  - None for this prospective guarded, source-free history-custody supplement.

REVISIONS
  - None required before implementation.

NITS
  - None.

CHECKS RUN
  - Read docs/plan-msae-norspan-controller-history-custody-supplement-v1.md:1-28 -> exact prospective contract inspected.
  - sha256sum of that named public supplement -> 74b84afa9617da288c28ad6a1ca0cbd945e9c5e573db33ea3548d77a6088724f.
  - Bounded reads of current public history walker/consumers, shared fingerprint and current-FD monitor -> prepare:1170-1263,1470-1523,2252-2335; pair helper:149-151; runtime:201-211.
  - Read only the named synthetic red root's run.log/results.xml -> two actual failing cells, earlier_file_bytes and earlier_directory_extra, both DID NOT RAISE; 2 failed, 48 deselected. The red transcript's test body is also present at public tests/test_msae_norspan_jpc_controller_matrix.py:119-134.
  - No tests, scientific/history runtime, real census, Git/source acquisition, private/raw/source/credential reads, network requests, models/GPU commands or administrator contact executed.

CONTRACT COVERAGE
  - Earlier-object late drift -> met prospectively: supplement:5-10 retains admitted originals, initial fingerprints/digests/names and final aggregate checks without rebasing. The red cells mutate an earlier object at the final yielded file, after the existing walker has closed the earlier directory at prepare:1244-1245. Both recorded failures are direct evidence of the targeted gap, not fabricated gate outcomes.
  - Held originals rather than merely reopening visible paths -> met prospectively: supplement:7-10 explicitly requires original FDs plus named aliases and exact directory names. Existing full fingerprint at pair helper:149-151 includes device/inode/mode/link count/size/mtime/ctime, unlike prepare:_identity's reduced fields.
  - Protected/quarantined/model-binary content and ordinary/pair semantics -> met prospectively: supplement:11-14 preserves lstat-only protected accounting, forbids new exemptions, keeps ordinary nlink1 inputs and admits nlink2 only for exact prescribed paired phase aliases with outside expectations.
  - Finite admission without false full coverage -> met prospectively: supplement:16-21 describes current-process FD4096, observed-byte8GiB/64GiB, object65536 and depth64 as operational admissions, not quotas. A stricter resource stop explicitly prevents a successful full-history claim; 65536 is an outer limit, not guaranteed usable capacity.
  - Cleanup and retained evidence -> met prospectively: supplement:21-22 requires single release on success/error/interruption/generator close and prohibits deleting subjects. The design is reversible and does not repair custody by adoption.
  - Honest conditional guarantees and synthetic acceptance -> met prospectively: supplement:24-28 excludes atomic-snapshot/same-UID guarantees, requires both demonstrated red cells plus cleanup/protection faults, and preserves the unconditional production guard. This report is not an implementation or whole-qualification SHIP.

UNKNOWNS
  - Implementation must reserve headroom for temporary ancestry-reader, scandir, digest and FD-monitor descriptors, not merely retained child FDs. runtime:201-211 itself opens a monitoring FD; current consumers can open additional ancestry/read descriptors while the generator is suspended. Exhaustion must fail operationally and clean up all owned resources.
  - Consumer exceptions must deterministically close the aggregate generator. prepare:1476 and 2284 currently use direct for-loops; tests must cover a failing consumer as well as explicit close/throw and walker-internal failure. Do not rely solely on eventual garbage collection, or let secondary close faults replace the primary failure.
  - Protected/model-binary no-content assertions must cover initial digest capture and final digest sweeps, not just the original consumers. Holding custody must not become an excuse to hash excluded subjects.
  - Final digest/name/original/named checks must use the captured original expectations, detect earlier-directory additions as well as earlier-file changes, and finish before either full-history consumer can return success. The recorded red evidence has not yet demonstrated green behavior.
  - No hard FD/kernel quota, guaranteed65536-object capacity, atomic whole-tree snapshot, production canonical authority, storage guarantee or production scientific authorization follows from this supplement.
