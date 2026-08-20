# Attempt 13 prescore development finding: whole-document overlap rule

The first label-only builder pass stopped before model inference because the initially frozen rule
removed seven of GENTLE's 26 documents, leaving 19. The colliding sentences were generic short strings
such as `Hello ,`, `Okay .`, and `Description :`; no activation or scientific score existed.

This artifact preserves the reason for the failed prescore build. The successor rule is explicitly
**prescore-support-amended, endpoint-outcome-blind**: feasibility informed the amendment, but no model
activation or endpoint score existed. It is prospective with respect to representation outcomes:

- full-document overlap removes the document;
- an exact overlapping sentence with at least eight UD words removes the document;
- two or more distinct overlapping sentence signatures in one document remove the document;
- one isolated overlapping sentence shorter than eight UD words removes only that sentence and all
  rows derived from it.

The complete label-only collision census is
`reports/provenance/atlas_v3_9_attempt13_collision_census.json` (SHA-256
`7b29abf428914e9578dee0032ecab70e657d647f05681994f5d56c623a3f5099`). It records 12 collided
GENTLE sentences in seven documents, the full historical-hit lists and signatures, all word counts,
and both dispositions. The amended rule removes two whole documents and five isolated sentences,
leaving 24 GENTLE documents before downstream support gates; CTeTex has no collision.

The original partial label-only tree is archived beside this note. No task threshold, model output, or
endpoint result informed this amendment. The revised plan requires a new exact-hash `/adversarial`
verdict before implementation can authorize inference.
