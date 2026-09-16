VERDICT: SHIP
ONE-LINE: The frozen tree mismatch is honestly retained; v7 is terminal, non-retriable, and authorizes no downstream work.

BLOCKERS        (must fix before proceeding; empty if none)

REVISIONS       (should fix; not blocking)

NITS            (optional, cap at 5)

CHECKS RUN
  - `sha256sum` over the reviewed plan, authority review, acquisition entry, and acquisition rejection → exact requested hashes matched: plan `67053a1b4a222de2fd9de18c534f2f5e58024413224e859c7ddfed4b63261916`; authority review `b37513a325bd9ca6b9b65ccdba2a83ce068d63ee14b44b17d99df35334be89a3`; entry `a5ed3430c081704e2b9dd8e7c53e928ebee21841dea3f5dcf7b823632e9fe7fa`; rejection `e71be14d61b76965423f6c209f3049eef156dc1daa5fdccfae80e5c040701a7e`.
  - Canonical public-JSON reconstruction plus the frozen runner's `validate_entry()` and `validate_rejection_report()` over the public entry/rejection → pass; both files are regular `0644`, one-link finals.
  - Command-record reconstruction → exact ordered prefix `ignore_raw`, `ignore_private`, `clone`, `checkout`, `head`, `tree`, `ls_tree`; all seven exit statuses are zero; every stderr is empty with SHA-256 `e3b0c442...`; clone/checkout stdout is empty; HEAD stdout is exactly 41 bytes and has the digest of the frozen commit plus LF.
  - Frozen tree-file-set diagnosis → requested five canonical `ls-tree` records require 353 bytes, while the retained output is 290 bytes; under Git tree uniqueness, 290 is exactly the four-record set containing train/dev/test/LICENSE and omitting `README.md`. No `hash-object` or installation command followed, matching the `tree_file_set` branch at `scripts/acquire_msae_independent_source_v7.py:841-851`.
  - Terminal process reconstruction → exact schema/counts pass: 43 point-in-time entries, one forbidden identity, status `ineligible`; the sole recorded code is `nvidia-smi` on a `bash` process. This conservative external observation is faithfully retained rather than rewritten as eligible.
  - Independent training-root checksum pass → all 2,116 baseline training-root entries and 139,663,075,787 bytes matched path, type, size, mode, inode, mtime, disposition, and SHA-256; no drift or mutation was detected.
  - Metadata-only cleanup/state check → `/tmp/msae-v7-acquire-u9y84slt`, the v7 data/raw/private namespace, all acquisition named temporaries, acquisition success, payload, and all scientific outputs are absent; rejection reports `partial_raw_metadata=[]` and `raw_namespace_exists=false`.

CONTRACT COVERAGE
  - Exact durable entry and review/authority bindings → met — the canonical entry at `reports/provenance/msae_independent_source_v7/source_acquisition_entry.json:1` binds manifest `9c049d5b...`, downstream authority review `b37513a...`, baseline `4db1c25d...`, config `30fad65a...`, runner `2f684b28...`, exact repo/commit/files, and false downstream authorizations; its SHA is bound identically by the rejection.
  - First frozen failure is `tree_file_set` → met — the retained command list ends after successful `ls_tree`, its 290-byte result cannot contain the exact frozen five unique records, and there are no later `hash_object:*` commands. The reviewed runner raises `tree_file_set` immediately on that set mismatch at `scripts/acquire_msae_independent_source_v7.py:841-851`.
  - Exact command surface, digests, and no source output → met provenance-only — all recorded argv form the validated frozen prefix at `scripts/acquire_msae_independent_source_v7.py:319-340`; stdout/stderr are represented only by byte counts and hashes, all commands exited zero, no shell/model/GPU/trainer command appears, and `source_content_printed=false`.
  - Scratch cleanup and raw custody → met — the scratch parent encoded by the clone argv is absent; raw namespace and partial metadata are absent/empty; no success final exists. This is consistent with mandatory scratch removal before any retained outcome at `scripts/acquire_msae_independent_source_v7.py:869-879`.
  - Honest terminal process evidence → met — the rejection at `reports/provenance/msae_independent_source_v7/source_acquisition_rejection.json:1` records `status=ineligible` and the exact one-token match instead of overstating an eligible snapshot. The plan explicitly allows a retained failure to bind the actually observed eligible or ineligible terminal snapshot at `docs/plan-msae-independent-source-v7.md:579-584`.
  - Unchanged training roots → met independently — a direct read-only checksum over the public baseline's 2,116 enumerated paths revalidated all 139,663,075,787 bytes and every bound metadata field; this independently supports the retained `training_root_status=unchanged`.
  - Zero model/GPU/training work and false authorizations → met — the rejection records runner-initiated model, GPU-query, and training counts as zero; model scoring, K2/branch training, and Stage C are all false; no prohibited operation was invoked in this review.
  - No payload or scientific continuation → met — acquisition success, the entire v7 data namespace, private payload, scientific manifests, scientific rejection, no-training gate, and seal are absent. The failure occurred before persistent raw installation and before the builder's scientific pipeline.
  - Terminal, non-retriable v7 state → met — the rejection's `next_action` is `new_reviewed_protocol_only`; the runner's preflight recognizes exactly the bound entry plus canonical rejection as an idempotent terminal and returns it without subprocesses at `scripts/acquire_msae_independent_source_v7.py:559-575,804-808`. Any changed candidate/file contract therefore requires a new prospectively reviewed namespace/protocol, not a v7 retry.

UNKNOWNS
  - Candidate/source/raw/private and Atlas quarantine contents were not opened. The omitted-`README.md` diagnosis is derived from exact argv, Git unique-path semantics, output length, command stopping point, and frozen code; source text was not inspected.
  - The terminal process snapshot intentionally stores command-line hashes rather than plaintext. Its schema/count/status and forbidden-code derivation reconstruct, but the historical plaintext command line was not and cannot be recovered from this artifact.
  - No network, acquisition, baseline, prepare, model, tokenizer, GPU query, scoring, training, K2, or branch command was run. This SHIP verdict accepts the retained failure only and is not authorization to retry v7.
