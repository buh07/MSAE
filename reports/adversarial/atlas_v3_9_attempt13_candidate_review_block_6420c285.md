# Attempt 13 frozen-candidate adversarial review — blocked candidate

- Reviewed freeze payload SHA-256: `6420c2851751b3232e557b2ee803c17afcb8537d7b5e430ca2832e4ce0a51032`
- Reviewed candidate inventory SHA-256: `a3054627f427d6d03143b165d86e925f8889f7bf40d0d1752f6869ac186fbae4`
- Reviewer: independent `/adversarial` agent `/root/attempt13_candidate_adversarial`
- Verdict: **BLOCK**
- No model inference was run and no scientific source opening was consumed.

## Blockers

1. **The irreversible runner trusted a declared SHIP.**
   `scripts/run_atlas_relation_context_v9.py:86-96` checked the authorization's
   `candidate_review_verdict` and review-file hash, but did not parse the review or bind its actual verdict
   to the frozen payload and candidate inventory. A signed authorization could therefore claim SHIP while
   binding a BLOCK review. The reviewer required a strict structured review contract, a reviewed
   authorization command, and a regression that a BLOCK review cannot be promoted.

2. **The lifecycle signing key was not pinned before namespace creation.**
   `scripts/atlas_relation_context_v9.py:128-143` accepted any loadable private key and the runner used it
   to create `STARTED.json` before checking it against the signer frozen in `run.json`. The reviewer
   demonstrated that an unrelated Ed25519 key could self-sign successfully. The required fix is to
   validate key type, raw public key, Base64 value, and fingerprint before any lifecycle path or global
   study-key consumption, with wrong-key regressions.

## Required revisions

- Bind both activation-cache completion hashes and canonical run/result inventories into result completion
  and the terminal, and immediately verify signed lifecycle artifacts under the frozen signer.
- Cryptographically verify the detached historical and final-freeze signatures over the exact payload bytes,
  not only their hashes.
- Safely shell-quote the operator-supplied key path in the tmux launcher.
- State that fit-source component uncertainty is conditioned on each fitted ridge model.

## Checks independently run by the reviewer

- Candidate/dependency hash audit: matched the frozen payload and inventory.
- Python compilation and shell syntax: passed.
- Attempt-13 tests: `13 passed`.
- Independent prepared-relation reconstruction: no matching, ancestry, reuse, component, or document-cap
  violations across 410 GENTLE and 640 CTeTex rows.
- Prior-CoNLL-U census reconciliation and both detached signatures: passed.
- GPU 2 UUID and idle-state audit: passed.
- Arbitrary-key signing probe: reproduced the missing signer check.

The code was not authorized or run under this blocked freeze.
