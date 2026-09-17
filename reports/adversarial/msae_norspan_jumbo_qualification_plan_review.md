VERDICT: BLOCK
ONE-LINE: The frozen plan fails its structural review gate; no implementation or publication-semantic approval is granted.

BLOCKERS
  - [medium] docs/plan-msae-norspan-jumbo-qualification-v1.md:52,96,105 — check-plan reports six failures: missing concrete milestones under "## Milestones", acceptance criteria under "## Definition of done", concrete checks under "## Verification plan", and milestone/definition-of-done/verification checklist items.
    reasoning — the document uses differently named sections and prose/bullet acceptance statements; the active plan validator does not recognize the required reviewable structure.
    impact — Q0 explicitly requires independent plan SHIP before implementation (lines 53-54). The adversarial plan-review contract requires BLOCK when the plan gate fails.
    fix — preserve this frozen candidate as evidence, create a prospectively versioned successor with the required headings and concrete checklists, bind its exact hash, rerun check-plan, and request a fresh semantic plan review. Do not implement under this disposition.

REVISIONS
  - None adjudicated after the plan-gate failure.

NITS
  - None.

CHECKS RUN
  - sha256sum docs/plan-msae-norspan-jumbo-qualification-v1.md and active task PLAN.md; cmp — both match 3b8ad18dd498035891e7de61cbd22e2b626d704da161546bda96c6a615191cc3 and are byte-identical.
  - PYTHONDONTWRITEBYTECODE=1 /jumbo/lisp/f004ndc/.generated/sessions/unleashed-8/modes/unleashed/bin/check-plan --path /jumbo/lisp/f004ndc/experiments/wip/MSAE/docs/plan-msae-norspan-jumbo-qualification-v1.md — PLAN: FAIL, six failures quoted above.
  - Read only the public plan, status, prior reviews, public builder/acquisition source, and separately retained fresh synthetic native probe JSON. No source/private/final-byte access or runtime protocol operation.
  - Native probe is limited same-client evidence: final-name O_EXCL conflict EEXIST, one winner/seven losers, file/parent fsync successful, rename-noreplace EINVAL 22. No multi-host/reboot inference.
  - Supplied plan hash verified immediately before and after this separate report write; unchanged. Only this new mode-0644 report was written; no prior evidence was overwritten or erased.

CONTRACT COVERAGE
  - Frozen exact-plan identification — met; both supplied paths match the requested digest.
  - Structural plan-review gate and Q0 SHIP prerequisite — unmet; six validator failures.
  - Jumbo-only source-free review and preservation — met within this review; read-only public/synthetic inputs, only separate report write.
  - JNC-1 publication/restart/consumption semantics, exhaustive qualification matrix, whole-implementation and authority approval — unadjudicated; plan-gate failure stops this review. This BLOCK is not a finding that O_EXCL is intrinsically unsuitable.
  - Scientific/readiness/prescore/branch/final launch — not granted; outside this plan-review scope.

UNKNOWNS
  - Successor review must resolve the explicit logical commit boundary for fully canonical final-name bytes observed before retained-writer validation or file/parent fsync completes, including writer failure, kill and concurrent/restarted consumers. Byte completeness alone cannot prove prior successful durability calls.
  - Successor review must distinguish producer-owned opaque publication/custody checks from forbidden raw/private consumption before the exact containing manifest/seal; current public preparation performs custody hashing before source_ready/seal publication.
  - Canonical prospective authority replacement must be audited against every literal path/hash binding, not inferred from a separate report's first-line SHIP. Preserved BLOCK reports must remain byte-exact.
  - NFS prior metadata/scratch anomalies, multi-host behavior and hard-crash/server durability are not qualified by the supplied same-client probe.
