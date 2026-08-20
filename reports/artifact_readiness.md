# M0 Artifact-Readiness Decision

**Decision:** **conditionally ready for architecture-selection analysis; not ready for a fresh-training or data-order-reproducibility claim.**  The four terminal 1B checkpoints are classified `development_existing_checkpoint`.

## What was reconstructed

- The authoritative completed run is `pilot_runs/20260601_132158_k2_msae_wave2_fastdata_stream/` with four terminal jobs (`g4`, `g5`, `g6`, `g7`). The reconstructed manifest is both restored in that run directory and preserved at `reports/provenance/reconstructed_fastdata_run_manifest.tsv`.
- Every final checkpoint embeds `git_commit_hash=1cef38e-dirty`, the intended Pythia-160M layer-3 K=2 architecture, final step/token counts, seed, incoherence coefficient, source list, and its resume path. Extracted metadata are in `reports/provenance/final_checkpoint_metadata.json`.
- The working-tree bytes that most plausibly produced the fastdata continuation are preserved in `reports/provenance/source_snapshot_20260601/`; their hashes and the scoped binary diff against `1cef38e` are preserved. Their filesystem modification times precede launch, but no immutable historical commit proves those bytes, so this identification is **high-confidence reconstruction**, not certainty.
- Final and resume checkpoints are hashed in place. Historical run families and evidence classes are enumerated in `experiments/registry.csv`. Frozen historical JSON/checkpoint paths are not rewritten; `reports/provenance/path_map.json` gives the read-time mapping.

## Critical lineage limitation

These are **continuations, not clean corrected-loader runs**. `g4`, `g5`, and `g7` resumed at 400,016,486 tokens; `g6` resumed at 300,016,447 tokens from the superseded 2026-05-29 pipeline. The fastdata code restores Python, NumPy, Torch, and CUDA RNG state, but it does not serialize and restore the streaming dataset iterator/cursor. Therefore the model/optimizer/RNG state is recoverable while exact example order across the resume boundary is not.

This permits a development audit of the already-learned representations. It does **not** support claims that the four models are fresh corrected-loader replications, exact bitwise training reproductions, or four exchangeable independent seeds (`g7` is the matched-seed no-incoherence control).

## Gate G0 checklist

| Requirement | Status | Evidence / limitation |
|---|---|---|
| Authoritative checkpoints, configs, logs, summaries locatable | PASS | Four terminal rows and checkpoint metadata/hashes |
| Stale absolute paths repaired or mapped | PASS for active entry points | Shell launchers are script-relative; frozen JSON/checkpoint args use `path_map.json` |
| Corrected loader reproducible | PARTIAL | Source bytes/diff captured; exact historical streaming cursor absent |
| Dirty-code differences reconstructed and reviewed | PASS with high-confidence qualifier | snapshots, SHA-256 list, binary patch, environment capture |
| Suitable for existing-checkpoint architecture audit | PASS | audit is explicitly development evidence |
| Suitable for final training/model-generalization claim | FAIL | resumed mixed-lineage data and no exact iterator state |

## Path policy and verification

Active launchers use `SCRIPT_DIR` and repository-relative paths. Run:

```bash
python scripts/check_msae_paths.py
sha256sum -c reports/provenance/dirty_source_sha256.txt
sha256sum -c reports/provenance/final_checkpoint_sha256.txt
sha256sum -c reports/provenance/resume_checkpoint_sha256.txt
```

The path checker intentionally excludes frozen run outputs, archived documents, checkpoint-embedded arguments, and provenance snapshots; changing them would falsify the historical record.

## Consequence for the requested work

Proceed with the raw atlas and the **existing-checkpoint** K=2 audit. Do not launch new training merely to repair provenance. After G1/G2, require a clean from-zero corrected-loader replication only if the learned-model path remains warranted; treat it as a later training prerequisite rather than evidence already obtained.
