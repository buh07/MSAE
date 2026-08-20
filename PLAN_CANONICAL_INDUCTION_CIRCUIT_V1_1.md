# Canonical Induction Circuit v1.1 — Launch-only Recovery

## Goal

Launch the unchanged canonical induction technical positive control after v1 retired before experiment start because its GPU-selection pipeline returned SIGPIPE status 141 under `set -o pipefail`.

## Constraints

- Preserve the v1 freeze, reviews, binding, and prelaunch failure record exactly.
- Make no scientific change: reuse the exact prepared development/confirmation rows, GPT-2 revision, fixed heads and controls, metrics, equal-block estimand, thresholds, seeds, gates, CUDA QA, and decision logic.
- Change only paths/version labels and the GPU selector: consume all `nvidia-smi` rows rather than exiting `awk` early.
- Keep confirmation unread/unhashed by runtime before a recomputed lineage-valid development PASS.
- Keep IOI v1 exact and the paper statement unchanged.
- Run no representation method or training.
- Require fresh candidate and exact frozen `/adversarial: SHIP` reviews before one-shot tmux launch.

## Design

The scientific design is byte-for-byte equivalent in values to canonical induction v1. The launch repair changes `awk` from an early `exit` (which caused upstream `nvidia-smi` to receive SIGPIPE and made the pipeline fail under `pipefail`) to recording the first eligible row while consuming the full stream. Four jobs remain: development, gated confirmation, development gate, and final aggregation, sharing one UUID-pinned free GPU sequentially through the gate.

## Milestones

- [x] Record and preserve the v1 prelaunch abort with zero model forwards and absent runtime namespaces.
- [x] Implement the isolated selector repair and tests.
- [ ] Obtain candidate and frozen SHIP reviews, bind, and launch.

## Verification plan

- Run the complete v1.1 unit suite without real model forwards.
- Parse Python; syntax-check the launcher.
- Verify IOI preservation, paper claims, cache, prepared data, partial pre-gate firewall, and frozen inventory.
- Reproduce that the v1 selector returns pipeline status 141 and that the v1.1 selector returns 0 while choosing the same free GPU row.
- Recheck output/provenance/session absence and free GPU state at launch.

## Definition of done

- [x] V1 freeze/reviews/binding and abort record are hash-bound in the v1.1 candidate.
- [x] No scientific config value changed apart from schema/namespace/runtime/candidate provenance and explicit recovery metadata.
- [x] The new selector succeeds under `set -euo pipefail` without suppressing `nvidia-smi` errors.
- [x] Tests cover optimized-Python review binding, confirmation firewall, exact IOI preservation, gates, lineage, estimand, and create-once behavior.
- [ ] Fresh candidate and exact frozen reviews are SHIP and hash-bound.
- [ ] Four jobs are live or cleanly terminal after launch on one free UUID-pinned GPU.

## Risks

- GPU state can change between query and use; the launcher revalidates physical index-to-UUID mapping immediately before sessions.
- The positive control may fail its scientific gates; that is a valid result and cannot authorize method evaluation.

## One-way doors

The v1 namespace stays retired. The v1.1 freeze and first model forward are one-way. A development STOP seals confirmation. No result automatically authorizes representation methods or training.
