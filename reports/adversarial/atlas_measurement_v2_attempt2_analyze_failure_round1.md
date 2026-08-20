# VERDICT

**BLOCK**

# ONE-LINE

The `np.int32`→`torch.long` cast is a scientifically neutral bug fix, but it changes an implementation-inventory-pinned file; the existing config, signed grouping/prepared provenance, run-root ownership, and strict cache lineage therefore cannot support an in-place authenticated `--recover` without a new reviewed config/provenance and an explicit cache-migration design.

# BLOCKERS

1. **The proposed source edit necessarily creates a new config/provenance identity.** The observed exception is exactly at `one_hot(torch.as_tensor(labels, ...))` (`pilot_runs/20260802_atlas_measurement_v2/logs/attempt2_analyze.log:2-17`; `scripts/run_msae_measurement_v2.py:286-306`). `scripts/run_msae_measurement_v2.py` is pinned in `implementation_inventory` (`configs/atlas_measurement_v2/run.json:163-173`), and `load_config` rehashes every pinned file (`scripts/msae_measurement_v2_run.py:167-194`). Editing `_fit_ridge` while retaining config SHA `852c7c…` makes the program fail before recovery. Updating the inventory changes the config SHA; the builder payload is explicitly bound to `852c7c…`, the reviewer verifier requires the builder config digest to equal the current config, and the prepared manifest also requires the exact config (`scripts/msae_measurement_v2_run.py:705-751,841-859`). **Required:** finalize/test the dtype-only fix, mint a new config SHA, rebuild the non-neural grouping/prepared manifest deterministically, and obtain new builder/reviewer signatures bound to that exact config. The grouping split/estimand need not change, but the exact cryptographic provenance must be renewed.

2. **Existing authenticated recovery cannot cross the config boundary.** The current run's `launch.json`, owner, attempt-1/2 job records, raw caches, transforms, and `FAILED.json` are all bound to `852c7c…`. Recovery refuses launch/owner config drift (`scripts/launch_msae_measurement_v2_tmux.sh:44-64`), raw validation requires the current config and current prepared-manifest digest, and transform validation repeats that requirement (`scripts/run_msae_measurement_v2.py:114-149`). Therefore changing the config and then invoking the existing `--recover` is not a valid path. Use a new create-once run root/session under the new config, or first implement and independently review an explicit parent-run migration protocol.

3. **The present old run is not currently recoverable even before the code change.** The failed analysis left `.analysis.1903618.tmp`; recovery rejects every hidden temporary output (`scripts/launch_msae_measurement_v2_tmux.sh:68-79`). The recorded owner PID `1900537` still exists with the matching start tick as a zombie owned by the shared tmux server, so `pid_matches` treats it as live and blocks recovery (`scripts/launch_msae_measurement_v2_tmux.sh:17-20,55-63`). Do not bypass these checks or delete evidence ad hoc. Record and quarantine the empty temp directory, and preserve the zombie/process evidence in an immutable failure amendment. A new run root avoids both hazards; changing zombie handling would itself be another pinned implementation change requiring review.

# REVISIONS

1. **The minimal code fix is appropriate but must be test-first and explicit.** Convert categorical indices to `np.int64`/`torch.long` at the `one_hot` boundary, validate `0 <= label < classes`, and add a CPU numeric regression showing `np.int32` and `np.int64` label inputs yield the same weights, bias, alpha selection, and grid. No current focused test exercises `_fit_ridge` or this dtype contract.
2. **Committed raw/transform values are scientifically reusable, but not under the current validator as-is.** The dtype fix is analysis-only; all four raw caches and four transform bundles committed successfully under attempt 2, with old-config/prepared/producer lineage. Reuse is valid only through a reviewed carry-forward/import mechanism that independently verifies every old value/row-ID/manifest/COMPLETE/job/lease/terminal digest, proves the new prepared row files and all model/checkpoint/data/numerical settings are identical, and emits new manifests binding both parent and new config identities. The final validator/report must retain the parent config and producer lineage. Without that machinery, rerun extraction/transforms in the new root; do not relabel old manifests as if newly produced.
3. Prefer rerunning raw/transform stages in the clean new root unless reuse is operationally important. The completed stages were short relative to the experiment, while a trustworthy migration path adds substantial code, schema, testing, and review surface.

# NITS

The failed analysis temp directory is empty, but its emptiness and path should still be captured before quarantine/removal because the recovery protocol deliberately treats unknown temporaries as evidence requiring review.

# CHECKS RUN

- Read `attempt2_analyze.log`; confirmed failure occurs at the first ridge `one_hot` call because labels are `np.int32` and PyTorch requires `LongTensor`.
- Confirmed current config SHA-256 remains `852c7ce9f5b4660adf07829335ecf084e4b1ec2d1c8679841cdd082b05fc73e2` and current pinned execution file hashes match it before the proposed edit.
- Inspected run state: four raw cache manifests and g4/g5/g6/g7 transform `COMPLETE.json` files exist; attempt-2 extract/transform terminals are exit 0; attempt-2 analyze terminal and canonical `FAILED.json` are exit 1; no committed `analysis/COMPLETE.json` exists; `.analysis.1903618.tmp` is empty.
- Confirmed the experiment tmux session is absent, analyze wrapper/child are dead, but owner PID `1900537` remains a matching-start-tick zombie.
- No files other than this report were edited; no tests, neural computation, GPU command, cleanup, or recovery was run.

# CONTRACT COVERAGE

- **Scientific estimand:** the cast changes tensor representation only; it does not change labels, ridge objective, alpha grid, tie rule, thresholds, or data. The fix itself is scientifically acceptable.
- **Config/provenance:** renewal is mandatory because exact code/config binding is an enforced contract, not optional bookkeeping.
- **Cache reuse:** content reuse is scientifically defensible because the failure occurs after raw/transform publication and before analysis publication, but only with explicit cross-config lineage. Existing validators intentionally reject silent reuse.
- **Recovery:** the old failed run should remain an immutable parent record. A clean new run or reviewed migration is required; ordinary same-config `--recover` is not valid after the source/config change.

# REQUIRED IMMUTABLE AMENDMENTS / VALIDATION

1. Create a create-once attempt-2 failure amendment containing the old config/Git/code/provenance/prepared hashes; exact failure-log and traceback digest; all raw/transform manifest/value/row-ID/COMPLETE and successful producer-record digests; failed analyze job/lease/terminal and `FAILED.json` digests; absence of committed analysis/final output; empty-temp inventory; owner-zombie evidence; GPU/tmux state; and a statement that no probe result or scientific endpoint was published.
2. Freeze the exact dtype-only diff and its regression-test results before generating the replacement config.
3. Generate new builder/reviewer envelopes and a new prepared manifest under the replacement config; require byte-identical grouping mapping, role assignments, identity vocabulary, pair populations, row IDs, and task-file digests (apart from manifests' provenance/config fields).
4. If importing caches, create a signed/create-once carry-forward inventory binding old/new configs, old/new prepared manifests, every immutable cache byte digest, parent producer commands/jobs, and the whitelisted config/code diff. Update the new validator to reject any imported artifact outside that inventory and to report parent lineage in the final bundle.
5. Launch the replacement config in a new authenticated run root/session. Preserve the old run root and canonical failure records; never rewrite old cache manifests, job records, or terminal markers.

# UNKNOWNS

- GPU idleness and all historical artifact hashes were sampled statically, not exhaustively captured into an amendment by this reviewer.
- Availability of the original reviewer private key is unknown; if unavailable, preregister a new independent reviewer trust key in the replacement config before the new review/signature flow.
