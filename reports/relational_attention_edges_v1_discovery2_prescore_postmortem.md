# Relational attention edges Discovery 2 — prescore postmortem

## Formal status

`relational_attention_edges_v1_discovery2` is **terminally prescore-ineligible**. Preserve the
signed lifecycle records unchanged:

- opening: `pilot_runs/scientific_source_openings/relational_attention_edges_v1_discovery2.PRESCORE_OPENED.json`
  (`2a49115f8c5374d3e0e276aaeb293e3392c708d32523b40ac5663426ef06770c`)
- terminal: `pilot_runs/scientific_source_openings/relational_attention_edges_v1_discovery2.PRESCORE_TERMINAL.json`
  (`f989deb8d5a5f5ba70e6b63dcb9f2e9a772cb1a55f24f00868ac17c5c6606974`)

Both signed records bind study key
`412ffa172bfdc6d3f06f11817173d7de70fbb6b82f25ff4f1a8f8131277065d2`, config SHA-256
`7ba135534997ba77579543cc431fca6e51779e0f642544d1069af00af60248f6`, and owner nonce
`8b85ce05a29dfd29958ec0bdcebbf81e`. The terminal has `retry_authorized=false`.

## Failure

The historical-artifact exposure audit stopped before completion at Spanish-AnCora dev line 11538.
The row begins with enhanced empty-node ID `0.1`. The frozen strict parser accepts decimal IDs only
when the base is at least one and therefore incorrectly reported this valid sentence-initial empty
node as malformed. CoNLL-U permits `0.1`, `0.2`, and so on for empty nodes before the first surface
token.

This is a **technical measurement failure**, not a scientific result. It establishes nothing about
relational attention-edge representations, transfer, recovery, specificity, or support.

## Execution attestations

The signed terminal records:

- candidate-source model forward: false;
- endpoint scores computed: false;
- neural training: false.

No `FINAL_FREEZE`, candidate `REVIEWED_SHIP`, backend QA, science authorization, runner-ready,
scientific opening, or tmux experiment was created. The Discovery-2 data root contains no files.

## Decision

Do not delete or replace the terminal, edit the frozen parser/config and rerun, create the rebuild,
or launch the model. The reviewed lifecycle made Discovery 2 the sole no-retry prescore successor.

For a genuinely future program only, correct and test sentence-initial `0.j` empty nodes before a
new preregistration. Such a program must be explicitly separate from Discovery 2 and must not be
reported as its retry. No such successor is authorized here.
