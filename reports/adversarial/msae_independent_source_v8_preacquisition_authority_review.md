VERDICT: SHIP

ONE-LINE: The v8 authority chain reconstructs exactly, remains source-free, and authorizes only the hash-gated acquisition runner.

BLOCKERS:
- None.

REVISIONS:
- None required before exact v8 source acquisition.

NITS:
- None.

CHECKS RUN:
- Reviewed baseline `reports/provenance/msae_independent_source_v8/baseline_inventory.json` at SHA-256 `c4283d888fb8d5927ff46533bea3a163f582daea08f722656b5f38fcec64ff51`, mode `0644`, link count 1, and authority manifest `reports/provenance/msae_independent_source_v8/preacquisition_authority_manifest.json` at SHA-256 `cd7179c392199aa4934f40878a9faf5b4d7b2ec4b9b149eaaad640619ddfffea`, mode `0644`, link count 1. Both parse with duplicate-member and non-finite-value rejection; both are exact canonical JSON. Their schemas and complete key sets match `msae_independent_source_v8_baseline_inventory_v1` and `msae_independent_source_v8_preacquisition_authority_v1` respectively (`baseline_inventory.json:1`; `preacquisition_authority_manifest.json:1`; enforcement at `scripts/prepare_msae_independent_source_v8.py:2185-2208`).
- Independently rehashed and metadata-checked every one of the 17,937 baseline records against the current filesystem. The exact disposition counts reconstruct as 16,133 `text_scanned`, 1,791 `binary_unscanned`, 10 `v8_authority`, and three `quarantine`; non-quarantine bytes, sizes, modes, devices, inodes, link counts, mtimes, SHA-256 values, and hard-link alias groups match. The three exact Atlas quarantine records were checked with `lstat` only and retain `adapter=quarantine_lstat_only`, `sha256=null`, and `content_reads=0`; no quarantine content was opened. The canonical entries digest is `f05e9289a4a93bbb92d328213f6048f7a525c6ffc3fec86e5156e8e668d65c31` (`baseline_inventory.json:1`; plan inventory contract at `docs/plan-msae-independent-source-v8.md:186-208`).
- Reconstructed the complete 16,133-record, path-sorted `{path,sha256,size}` history array from current `text_scanned` baseline records. It is byte-for-byte equal to the registry `inputs`, has unique sorted paths, and hashes under the frozen serialization to `8070a7cdd536a0dbd6104ff1dfb279ef01fb0acf98e969227625324155227564`. The same count/digest is bound by the baseline, manifest, registry, and screen; the screen binds the registry SHA-256 and reports zero content hits, path hits, source-use evidence, quarantine reads, model operations, GPU queries, and training runs (`docs/plan-msae-independent-source-v8.md:139-167`, `docs/plan-msae-independent-source-v8.md:200-208`).
- Rehashed all 10 manifest authority artifacts and verified exact modes/link counts and current bytes. The manifest map reconstructs exactly:
  - plan `7aec70f8d6f384f2919f5f3086064b437dd34ff7731542aed2d7abe23ac5ae19`;
  - plan review `d159749125a6db4e1dd6a68f2207e4be6b643e2f0d7b8112695cfec98660204d`;
  - historical registry `ff4a36996f58531353dda9ed8fcbedb4c3a615f2d877e8b31f1462ddc8581a97`;
  - alias screen `68a7536c95896087960dd4fc5882df85296baaa1a07aaf910e0e7c257b165e2f`;
  - builder `5b3bf93ed412e480e7d84720b235b104bc571bb63faa16504279cd25cf6bc881`;
  - acquisition runner `07a15235a860296ffb461d2bc065cdb093fb87656b9dbab3918c20293b4159a3`;
  - tests `3baad53b0d863c4139abeaf3fa303f46fad4338d0342d0289ced15ba83bd76cc`;
  - acquisition config `8383d3ba80ac1296887c243e00d09b6b9a5e79b19f771934a1ddd07ceac56df9`;
  - source-free transcript `3629712ae64b00c9e6c9dd2cd1cced774d3a5f328fd72115bf7edbf14e13369b`;
  - implementation review `0bedf94cb578722208e6069f9ee00bf966921fb32317235e777e3a54f6884496`, whose first line is `VERDICT: SHIP`.
- AST-extracted the builder's literal predecessor map and established exact equality with the manifest: 50 unique direct predecessors, all still present at their bound hashes. This includes the complete 15-item direct v7 chain required by `docs/plan-msae-independent-source-v8.md:555-563`: plan `67053a1b...`, plan review `3f8ceedb...`, registry `a5edbe04...`, screen `336a3a40...`, builder `ffa487d2...`, runner `2f684b28...`, tests `51bf834e...`, config `30fad65a...`, source-free log `785a4c48...`, implementation review `68cd4493...`, baseline `4db1c25d...`, authority manifest `9c049d5b...`, authority review `b37513a3...`, acquisition entry `a5ed3430...`, acquisition rejection `e71be14d...`, and terminal review `a9ffad68...`.
- Reconstructed the baseline process snapshot canonical digest `5293cf9906af3f53a78adf5e07f791e519a97ebd5b6f020a1ba7457c28272c3c`: schema `msae_independent_source_v8_process_snapshot_v1`, scope `point_in_time_proc_snapshot`, 33 schema-valid entries, zero forbidden identities, status `eligible`. This supports exactly the point-in-time claim, not an interval claim (`baseline_inventory.json:1`).
- Reconstructed all 2,116 path-sorted training-root records from the baseline under the frozen predicate, verified exact equality with the embedded array, and independently checked their present metadata/content bindings. The digest is `2e655873dee4824cda59ca18bfbbde3b3f62e86f454860fbf2d1af4235779fc5`, equal in baseline and manifest (`baseline_inventory.json:1`; `preacquisition_authority_manifest.json:1`).
- Performed a source-free current structural recensus. Before writing this review, the worktree differed from the 17,937-path baseline only by the two expected create-once outputs, `baseline_inventory.json` and `preacquisition_authority_manifest.json`; the authority-review path was absent. Metadata-only `lstat` checks confirmed the entire `data/msae_independent_source_v8` namespace, all v8 raw/private paths, every acquisition entry/success/rejection/preflight final, and every corresponding `.building` temporary were absent.
- Verified authority bits exactly: `authority_review_required=true`, `source_acquisition_authorized=true`, while `model_scoring_authorized=false`, `k2_or_branch_training_authorized=false`, and model/GPU/training operation counts are all zero (`preacquisition_authority_manifest.json:1`; enforcement at `scripts/prepare_msae_independent_source_v8.py:2185-2208`).
- Verified downstream use cannot precede this independent review. The builder requires a SHIP review containing the exact manifest and baseline hashes (`scripts/prepare_msae_independent_source_v8.py:2209-2211`). The runner requires `--authority-review-sha256`, exact equality to the current review bytes, a SHIP first line, both authority hashes in the report, and exact runner/config bindings before history validation, entry publication, scratch creation, or any subprocess (`scripts/acquire_msae_independent_source_v8.py:785-817`; frozen config validation at `scripts/prepare_msae_independent_source_v8.py:385-414`).
- The comprehensive validator completed with `status=PASS`: 10 artifacts, 50 predecessors (15 v7), 17,937 baseline entries, 16,133 history inputs, three lstat-only quarantines, 33 process entries/zero forbidden identities, 2,116 training-root entries, and all neural authorizations false. No network, acquisition, model, tokenizer, GPU, scoring, training, K2, or branch command was invoked.

CONTRACT COVERAGE:
- **Exact authority inputs and schemas:** covered; hashes, canonical representations where required, key sets, mode/link metadata, and create-once chain all reconstruct.
- **Full accessible history:** covered; all 16,133 current history records reproduce the frozen array and digest, including prior public/raw history within the plan's eligible scope.
- **Predecessor chain:** covered; all 50 literal paths and hashes reconstruct, including every required v7 authority/terminal item.
- **Quarantine containment:** covered; three quarantines were `lstat`-checked only, with zero content reads.
- **Process/training containment:** covered; the frozen eligible process snapshot and all 2,116 training-root bindings reconstruct exactly.
- **Pre-acquisition state:** covered; v8 source/raw/private/payload and every acquisition final/temp remain absent.
- **Capability and sequencing:** covered; only exact source acquisition is authorized, contingent on passing this report's hash to the reviewed runner. Model scoring, K2/branch training, and neural operations remain unauthorized.

UNKNOWNS:
- Candidate bytes, source-tree compliance, license eligibility, pedigree, deduplication, overlap, task support, split suitability, and payload construction remain intentionally unknown until the exact reviewed acquisition and ordered scientific gates run.
- The baseline process evidence is a frozen point-in-time snapshot only. This review makes no claim that unobserved ephemeral processes did not exist outside that snapshot.
- SHIP authorizes only one invocation of the exact hash-bound v8 acquisition runner with this review's final SHA-256. It does not authorize model scoring, K2, branch training, payload inspection, or a retry after a terminal outcome.
