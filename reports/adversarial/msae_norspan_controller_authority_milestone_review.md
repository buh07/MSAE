VERDICT: REVISE
ONE-LINE: Guarded Q1/Q2 need catalog aggregate/namespace fences and strictly typed source-authority receipts before bounded SHIP.

BLOCKERS
  - No production guard removal or launch capability was observed. Whole qualification remains BLOCK; this is a moving, guarded Q1/Q2 milestone, not whole approval.

REVISIONS
  - [medium, Q1] scripts/msae_norspan_jpc_controller.py:122-140 — previously verified latest snapshot drift is not checked after later predecessor/durability work.
    evidence — two genuine synthetic load regressions substitute same-length lineage bytes in catalog-000001.json either after reading catalog-000000.json or during the final catalog-directory fsync. Both load calls return the old pinned store/session instead of rejecting; full-red-pytest.txt records DID NOT RAISE for both named cases.
    reasoning — each ordinary-file reader finishes separately; directory.validate(durable=True) checks directory identity/cardinality, not contents or original named identity of earlier verified files. A change during subsequent validation is outside the earlier reader's observations but inside the load operation.
    impact — the explicit outside catalog pin is not fenced across the containing chain validation. This is not signature forgery or arbitrary-after-final-observation exclusion, but it prevents qualification of current immutable catalog transport.
    fix — retain every bounded ordinary catalog's original FD, outside hash, original fingerprint and ancestry while validating the chain. After predecessor/schema/fsync work, perform expected-byte scans over all originals, then an all-original named/metadata/ancestor fence after the last scan; never rebase expectations or adopt replacement bytes. Preserve all evidence and fail on cleanup faults.
  - [medium, Q1] scripts/msae_norspan_jpc_controller.py:52-68 — final postclose ordinary-file read lacks a subsequent exact catalog-directory namespace fence.
    evidence — test_checkpoint_final_ordinary_read_still_rejects_foreign_catalog_entry inserts outside/foreign immediately before the final ordinary read of catalog-000001.json. session.register succeeds, advancing the catalog, while foreign exists during that final reader. The expected-reject regression fails with DID NOT RAISE.
    reasoning — exact names are checked before parent cleanup, then the ordinary reader verifies only its named file and ancestry. It does not check that its parent still contains precisely the finite expected snapshots.
    impact — checkpoint success can return a catalog directory already contaminated by a foreign object, although the next load rejects it. This is a missed finite validation edge, not a claim that mutations after the last fence can be excluded.
    fix — finish all final catalog-reader work before a final exact-directory cardinality/ancestry fence and preserve original expectations. Propagate any read/fence/close failure so both session and store remain poisoned and no successful pin advances.
  - [medium, Q2] scripts/msae_norspan_jpc_authority.py:139-155 — source-authority nested receipt schema uses Python equality instead of strict receipt parsing.
    evidence — a canonical genuinely signed source_authority statement with every numeric authority_pair field represented as float passes bind_authority and verify_authority. The same record is rejected by j.receipt_from_record. test_source_authority_receipt_types_must_match_pair_schema fails with DID NOT RAISE.
    reasoning — the binder checks only top-level keys; float values compare equal to corresponding integer PairReceipt values in the dict equality at lines 153-155. Cryptographic authenticity does not substitute for the specified typed schema.
    impact — signed source-authority statements are not restricted to the exact receipt schema used by the catalog and live producer. This is a schema qualification gap, not an attacker bypass of the pinned signing key or production guard.
    fix — validate every source-authority SHA/lineage field, parse authority_pair with j.receipt_from_record against the canonical expected authority path, require mode644, and compare the strictly typed canonical record to the session expectation on every use. Add the preserved regression to the maintained suite.

NITS
  - None.

CHECKS RUN
  - Bounded numbered public-source/plan reads only; no real history census, source/acquisition/raw/private payload, protected credential, Atlas or V8/V9/V10 payload, model/GPU/network command or administrator contact.
  - Initial 33 independent synthetic tests against retained exact public copies -> 33 passed in 6.87s. Genuine disposable Ed25519 signatures; exact release subjects/dependency/mode/bytes/hash/scope/verdict/rollback pins; signed duplicate/noncanonical data; unsigned SHIP rejection; source lineage/release/receipt/review/pair-drift rejection; actual OpenSSL child receives three sealed immutable memfds and closed FDs; second-memfd/sealing/close/interruption failures clean up; a real synthetic child timeout kills/reaps the child; actual catalog file/parent fsync and close faults poison the session/store, preserve files and reject stale-pin adoption; production from_arguments guard fires before input reads.
  - Final full frozen attack run -> 4 failed, 33 passed in 10.85s. Only the four findings-related expected-reject cases fail; every failure and synthetic root is retained.
  - Exact executable command: PYTHONPYCACHEPREFIX=/jumbo/lisp/f004ndc/tmp/lisplab1/norspan-q12-review-18GGYp/red-pycache python -m pytest -q /jumbo/lisp/f004ndc/tmp/lisplab1/norspan-q12-review-18GGYp/test_q12_attacks.py --basetemp=/jumbo/lisp/f004ndc/tmp/lisplab1/norspan-q12-review-18GGYp/full-red-basetemp -o cache_dir=/jumbo/lisp/f004ndc/tmp/lisplab1/norspan-q12-review-18GGYp/full-red-cache --junitxml=/jumbo/lisp/f004ndc/tmp/lisplab1/norspan-q12-review-18GGYp/full-red-junit.xml > /jumbo/lisp/f004ndc/tmp/lisplab1/norspan-q12-review-18GGYp/full-red-pytest.txt 2>&1
  - The timeout test substitutes only the command with a fresh sleeping synthetic Python child while retaining the production subprocess.run timeout/kill/reap mechanism; it does not claim actual OpenSSL hung independently. The interruption case injects KeyboardInterrupt at run entry, not after a spawned OpenSSL child.
  - Test script SHA256: db8285f291c925c85e1c0b30a8e53e5d9407a33bd3a54e887e8f6eae7fe999c3.

CONTRACT COVERAGE
  - Explicit bounded catalog chain, no latest discovery, genesis reservation, pin/lineage/schema checks, registration-before-return, poisoned current syscall failures and no stale-pin adoption -> met on exercised edges; partial overall due final chain/namespace findings.
  - v1 readable / v2 manifests schema checked and transported -> inspected; manifest transport is not independent approval or live scientific payload validation. Complete raw/private recovery is outside this review.
  - Genuine pinned Ed25519 DER/signature verification against sealed bounded copies, clean environment, bounded subprocess output and owned descriptor cleanup -> met on named exercised edges; actual spawned-OpenSSL interruption/hang qualification is not claimed.
  - Exact finite ordinary release subject set including prepare/acquire/pair/runtime/controls/controller/verifier/storage config and TODO/V10 public-reference paths, strict release subject mode/bytes/hash schema, stale approval rejection -> met in source and independent fully synthetic-subject tests. No real public V10 reference file content was read or copied by these attacks: the synthetic subject at that pathname contains dummy text only.
  - Separate signed source-authority receipt, release/lineage/review binding and fresh containing authority-pair validation -> partial: genuine bindings and mutation rejection pass, but malformed numeric receipt types still pass.
  - Canonical implementation/authority lookup routed through session.approvals and fed into acquire/authority/phase/scientific validators -> inspected. Legacy review files remain finite release/history subjects, not fallback cryptographic authority; state classifier's existence check is not approval. Full application pipeline was not independently executed in this bounded attack run.
  - Unconditional production guard before CLI inputs and execute/state observations, no enrollment/signing production API, no capability from synthetic keys/catalogs -> met in source and guard test. Production trust enrollment is open.
  - Q3 full recovery, Q4 complete named fault matrix/all80 audit rows, Q5 exact whole independent approval/containment -> not reviewed or closed. Whole remains BLOCK; tests/counts do not authorize scientific work.

UNKNOWNS
  - Coordinator was modifying Q3 while this review ran. Tests import only the retained exact public copies below; they do not qualify successor hashes or unreviewed new recovery code. Any fix needs a separate exact successor review/run. Existing negative reports and failing transcripts must be preserved.
  - Arbitrary same-UID future writes, atomic snapshots, server stable storage/failover/backup/restore, hard quotas/process containment and production owner trust enrollment are not established by finite observations or these tests.
  - Root's earlier 8 crypto + 7 catalog + 15 legacy controls and in-progress full pipeline tests were reported as context, not independently rerun or used as proof here.

REVIEWED EXACT SNAPSHOT
  - Retained source directory: /jumbo/lisp/f004ndc/tmp/lisplab1/norspan-q12-review-18GGYp/public-before/
  - acquire_msae_independent_norspan_v1.py: 1e441abe3535523c01626d3e4d91d8ae4285f74e945ff7f99e26e2f32e7fac12
  - msae_jumbo_pair_commit.py: 94e948385bb8ebe40a5c3447b50cbf12a50cc4aa1b2347b7f73db2ca50f559f7
  - msae_norspan_jpc_authority.py: e45fe2898dd654ce9968d47ac76cd140cc0e84f574293691e07d5f68f05ebea7
  - msae_norspan_jpc_controller.py: 9312f0ebd867867cf4c6cbb677ea16ca55db81ad8397d88c485f740d057a5b5c
  - msae_norspan_jpc_controls.py: 5639c3ebf35cb532872053835ab02ea72abd2f8eab8bd4c72ce138ae0b2bb7f4
  - msae_norspan_jpc_runtime.py: 865bd6fe80d6e469669ddadf3b6e1806275d1572ab9b622695d65eefa8ddabfb
  - prepare_msae_independent_norspan_v1.py: 2e7a812bd68cce427db7f9731efc9ada72e45fad440d285ad1c0e9d369d6600a
  - Source-copy hashes: before-sha256.txt. Later moving working-tree hashes: current-after-sha256.txt. Review report copied to the specifically requested public report path only; all tests, caches, keys, synthetic subjects and execution outputs remain under this fresh Jumbo tmp root.
