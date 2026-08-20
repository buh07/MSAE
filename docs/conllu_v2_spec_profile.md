# CoNLL-U v2 parser profile used by relational-objects v2

- Official specification: <https://universaldependencies.org/format.html>
- Retrieved: 2026-08-04
- Scope: transport, ten-column rows, typed IDs, required sentence metadata, basic-tree integrity,
  enhanced-head references/order, multiword-token field restrictions, and empty-node placement.

The `strict` profile in `scripts/conllu_spec.py` enforces UTF-8/NFC, LF-only transport, a final blank
sentence separator, exactly one nonempty `sent_id` and `text` comment per sentence, integer IDs
`1..n`, basic-tree validity, range placement/nonoverlap, the MWT `FEATS=Typo=Yes` exception,
sentence-initial `0.j` and ordinary `i.j` empty nodes, and typed enhanced-reference ordering.

The `reader` profile is deliberately not called specification-conformant. It shares the structural
checks but accepts CRLF and/or a clean EOF without the closing blank line, emitting
`CRLF_NORMALIZED` and/or `CLEAN_EOF_ACCEPTED`. Reader success cannot rescue a strict validation
failure or authorize the development experiment.

This note records the frozen interpretation used by the local implementation. The official page,
not this paraphrase, is authoritative when the two differ.
