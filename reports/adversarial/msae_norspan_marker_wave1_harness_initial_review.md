VERDICT: BLOCK
ONE-LINE: Initial marker harness leaked owned resources on selector faults and accepted real target publication before its GO handshake.

BLOCKERS
  - [bounded harness safety] tests/test_msae_norspan_marker_fault_wave1.py:475-479 (INITIAL snapshot SHA256 a7567ac8a918648ea9764c341244693d1d9479d11177f98e714aa9611ee987d0; retained /jumbo/lisp/f004ndc/tmp/lisplab1/norspan-marker-wave1-independent-_ugrnynx/candidate-test-before.py) — actual cleanup-negative fixture creates an owned Popen and then allocates/registers selector outside protected cleanup. Independent OSError/KeyboardInterrupt injected at actual selector allocation or register leaves the real synthetic child LIVE, stdin/stdout OPEN and caller FD baseline unrestored: four genuine red assertions.
    reasoning — acquisition-independent test helper resources are not released on setup failure; after-release cleanup-cell positives do not exercise this earlier path. Existing setup-negative tests simulated a direct raise instead of invoking the allocation/register path and missed it.
    impact — violates wave1 W3 owned child/pipe/selector cleanup acceptance and can leak synthetic children/descriptors when the qualification harness fails.
    fix — protect actual selector allocation/register and the whole cleanup-test body with finally cleanup using a None-capable selector. Exercise real patched allocation/register calls for both exception types. Preserve primary object and attach secondary notes; externally kill/reap/release any real resources leaked by a failing diagnostic.

  - [bounded qualification correctness] tests/test_msae_norspan_marker_fault_wave1.py:420-425 (same INITIAL snapshot) — main SIGKILL harness validates SETUP_READY.expected=None but not buffered target output or physical publication before granting GO. Four actual worker mutations perform real target publication BEFORE SETUP_READY at stage_opened/after_write/after_link/before_catalog, then emit coalesced setup+target frames. The unmodified initial parent harness PASSES all four, including real SIGKILL/reap and current custody/no-adoption assertions: four genuine red sensitivity assertions.
    reasoning — the target phase was reached before the purported setup/GO boundary; no mocked receipt/primitive/catalog success was used. Accurate later kill/custody assertions do not prove the required ordering. A synthetic worker's expected=None assertion is not an independent check that no target publication happened.
    impact — cannot qualify W3 import/setup then GO then target budgets/ordering or the no-intermediate-publication-before-GO contract.
    fix — after parsing setup, reject any buffered target diagnostics and independently assert the fresh control directory is empty BEFORE sending GO. Test real pre-GO publication mutants, not just malformed pure framing. Retain genuine killed partial/complete-looking objects without adoption.

REVISIONS
  - No production repair is requested by these findings. These are test-only harness defects. Before-release kill/wait failure edges are not qualified by after-release cleanup cases; they must stay explicitly OPEN, not be upgraded to universal resource guarantees.

NITS
  - None.

CHECKS RUN
  - Read prospective docs/plan-msae-norspan-marker-fault-qualification-wave1.md SHA256 ab9caa0c60758865691268b84e6fa9362ce30419c479da8e15f1ddc5612f9457 and initial new named test. Original owner65 finite public subjects independently checked:65/65 SHA/bytes/modes/nlink1/ordinary identities match; no production edits.
  - Evidence root R=/jumbo/lisp/f004ndc/tmp/lisplab1/norspan-marker-wave1-independent-_ugrnynx. Initial test source copied before independent execution as candidate-test-before.py; exact a7567… SHA above,25968bytes.
  - PYTHONDONTWRITEBYTECODE=1 /usr/bin/python -m pytest -q -o cache_dir=R/cache tests/test_msae_norspan_marker_fault_wave1.py --basetemp=R/base --junitxml=R/results.xml →427 PASS,30.16s,exit0. Exact command/log/JUnit/exit retained in R/{command.json,run.log,results.xml,exit_code.txt}. This initial suite green is not evidence that the two missing boundaries are sound.
  - Actual corrected reviewer attacks: R/test_initial_harness_attacks.py, R/attacks-correct-command.json/log/XML/exit →8 FAIL,1.11s. Four resource setup failures and four premature-publication failures described above. Named public setup-resource-observation.json and premature-publication-observation.json metadata files retain each result; source bodies in synthetic basetemp are not public companion inputs.
  - All leaked real synthetic children were externally killed/reaped and every owned pipe/selector released in independent diagnostic finally; caller FD baseline restored AFTER external cleanup. Initial fixture observations explicitly record BEFORE-external-cleanup leakage. Each real premature-publication worker was killed/reaped by the original SIGKILL harness; no child left running. No repeated real operation or destructive evidence cleanup.
  - Initial reviewer placement run retained separately as initial-placement-{attacks.log,attacks.xml,attacks-exit.txt,test_initial_harness_attacks.py}:4 resource FAIL +4 apparent premature-mutant PASS,0.84s. The apparent passes were NONFIRING: copied module __file__ located a nonexistent public-script import directory, so children failed import/EOF before actual target. Corrected ONLY the reviewer copy's dependency-location __file__ to the unchanged original public scripts; rerun produces all8 genuine FAIL. Do not cite those first4 apparent passes as qualification.
  - Root first/second/observed wave suites are different artifacts from these independent diagnostics. Root first12 failed+385 passed (stale gen0 load expected success and wrong guard exception class) is preserved; this report does not attribute those earlier harness failures to production. Later root427/427 green before repair does not close the newly demonstrated paths.
  - No blanket pytest, legacy real-identity test collection/import, protected keys/real source/raw/private/Atlas/V8/V9/V10 evidence, Git/status/network/science/scoring/model/GPU/tmux/administrator operation or production guard change. All independent artifacts/cache/basetemp/JUnit under fresh Jumbo root R.

CONTRACT COVERAGE
  - W1/W2 inspected target-inode/ordinal actual fault and retained original/foreign evidence cells → bounded initial positives, not invalidated by these independent W3 defects; no whole matrix closure.
  - W3 actual SIGKILL/reap, old explicit catalog no-adoption vs permitted current physical custody → exercised; no fake outcomes. Setup/GO phase ordering → unmet in INITIAL harness. All-path fixture setup resource cleanup → unmet in INITIAL harness.
  - Actual resource release-after-error, primary/secondary handling → bounded after-release cases only; failures BEFORE kill/wait remain OPEN.
  - Owner65 production/public identities and unconditional production guard → unchanged. Whole9 groups/all80/semantic producer/science/terminal/recovery/hard containment/exact final owner authorization → remain OPEN/BLOCK, not certified by427 green tests.
  - This is an immutable negative review of a7567… INITIAL snapshot, NOT a judgment on a later corrected/frozen candidate. Any successor must receive a separate exact review and rerun these real witnesses.

UNKNOWNS
  - No universal process/descriptor containment, before-release kill/wait cleanup guarantee, real acquisition or full typed scientific/control-flow qualification is established.
  - Historical first-run causes are limited to retained traces supplied by root; they do not prove anything about real storage/server failures.
  - Lint/type/static checks, server/multiclient/reboot/retention/quota guarantees and genuine exact owner FINAL APPROVE remain absent. No separate external signer requirement is introduced.
