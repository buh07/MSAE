# PLAN — Joint controllability v4.1 launch recovery

## Goal

Launch an execution-only successor to the preserved v4 technical failure. Keep every scientific row,
model revision, method, estimator, threshold, seed, task gate, and decision unchanged; correct only
the `TRANSFORMERS_CACHE` path that prevented configuration files from being found before any model
forward.

## Constraints

- Preserve the v4 result and provenance namespaces unchanged.
- Use a new config, freeze, output, provenance, and tmux namespace.
- Bind the v4 freeze, launch manifest, task-gate failure, aggregate block, and traceback by hash.
- Permit no model/SAE/K2/dictionary training and no scientific protocol change.
- Run a local-cache configuration/tokenizer preflight before creating the output namespace.

## Milestones

- [ ] **M1 technical amendment** — bind predecessor failure and correct only cache resolution.
- [ ] **M2 reviewed freeze** — tests, cache smoke, preflight, and `/adversarial` are SHIP.
- [ ] **M3 launch** — development gates and waiting workers are alive in isolated tmux sessions.

## Definition of done

- [ ] The predecessor v4 tree and logs remain unchanged.
- [ ] The v4.1 scientific config fields equal v4 exactly outside runtime/preservation/schema/namespace.
- [ ] Local AutoConfig and tokenizer loads pass for all three pinned revisions under the launcher cache environment.
- [ ] Freeze and candidate review bind all code, rows, assets, predecessor terminals, and closure.
- [ ] No training path exists and fresh test inference remains blocked by the opened-development gate.
- [ ] All tmux sessions and initial logs are alive at handoff.

## Verification plan

- [ ] Run Python compile, launcher `bash -n`, and targeted v4.1 pytest.
- [ ] Compare normalized v4/v4.1 configs and require no scientific diff.
- [ ] Run `cache-preflight` with `TRANSFORMERS_CACHE=$HF_HOME/hub` offline.
- [ ] Run v4.1 preflight, freeze, independent `/adversarial`, and freeze verification.
- [ ] Launch once, record GPU UUIDs, and inspect only liveness/initial logs before returning.

## Risks

- Other assets may be missing despite configs being present; cache preflight checks tokenizers and
  complete snapshot weight files before launch.
- This is a launch recovery, not authorization to alter a failed scientific gate.
