#!/usr/bin/env python3
"""Specification-oriented CoNLL-U v2 parser used by relational-objects v2.

``strict`` enforces the transport, sentence metadata, ID, reference, and basic
tree constraints frozen in PLAN_RELATIONAL_OBJECTS_V2.md. ``reader`` differs
only by accepting CRLF and a clean EOF without a final blank separator while
reporting those deviations. It must never be presented as strict conformance.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re
import unicodedata
from typing import Iterable, Literal, Sequence

Profile = Literal["strict", "reader"]

UPOS = frozenset(
    {
        "ADJ", "ADP", "ADV", "AUX", "CCONJ", "DET", "INTJ", "NOUN",
        "NUM", "PART", "PRON", "PROPN", "PUNCT", "SCONJ", "SYM", "VERB", "X",
    }
)


class ConlluError(ValueError):
    """A deterministic format error with source and line context."""

    def __init__(self, code: str, source: str, line: int, detail: str) -> None:
        self.code = code
        self.source = source
        self.line = int(line)
        self.detail = detail
        super().__init__(f"{source}:{line}: [{code}] {detail}")


@dataclass(frozen=True, order=True)
class TokenId:
    major: int
    minor: int | None = None

    @property
    def is_empty(self) -> bool:
        return self.minor is not None

    def text(self) -> str:
        return str(self.major) if self.minor is None else f"{self.major}.{self.minor}"


@dataclass(frozen=True)
class RangeId:
    start: int
    end: int


@dataclass(frozen=True)
class Row:
    id: TokenId | RangeId
    fields: tuple[str, ...]
    line: int


@dataclass(frozen=True)
class Sentence:
    sent_id: str
    text: str
    comments: tuple[str, ...]
    rows: tuple[Row, ...]
    start_line: int

    @property
    def integer_rows(self) -> tuple[Row, ...]:
        return tuple(r for r in self.rows if isinstance(r.id, TokenId) and not r.id.is_empty)


@dataclass(frozen=True)
class ParseResult:
    sentences: tuple[Sentence, ...]
    deviations: tuple[str, ...]
    profile: Profile


_INT_RE = re.compile(r"[1-9][0-9]*\Z")
_RANGE_RE = re.compile(r"([1-9][0-9]*)-([1-9][0-9]*)\Z")
_EMPTY_RE = re.compile(r"(0|[1-9][0-9]*)\.([1-9][0-9]*)\Z")
_FEAT_NAME_RE = re.compile(r"[A-Z][A-Za-z0-9]*(?:\[[a-z0-9]+\])?\Z")
_FEAT_VALUE_RE = re.compile(r"[A-Z0-9][A-Za-z0-9]*\Z")
_REL_RE = re.compile(r"[^|:\s]+(?::[^|:\s]+)*\Z")
_BASIC_DEPREL_BASES = frozenset(
    {
        "acl", "advcl", "advmod", "amod", "appos", "aux", "case", "cc", "ccomp",
        "clf", "compound", "conj", "cop", "csubj", "dep", "det", "discourse",
        "dislocated", "expl", "fixed", "flat", "goeswith", "iobj", "list", "mark",
        "nmod", "nsubj", "nummod", "obj", "obl", "orphan", "parataxis", "punct",
        "reparandum", "root", "vocative", "xcomp",
    }
)
_ENHANCED_DEPREL_BASES = _BASIC_DEPREL_BASES | {"ref"}
_BASIC_DEPREL_RE = re.compile(r"[a-z]+(?::[a-z]+)?\Z")


def _fail(code: str, source: str, line: int, detail: str) -> None:
    raise ConlluError(code, source, line, detail)


def _typed_id(text: str, source: str, line: int) -> TokenId | RangeId:
    if _INT_RE.fullmatch(text):
        return TokenId(int(text))
    match = _RANGE_RE.fullmatch(text)
    if match:
        start, end = map(int, match.groups())
        if start >= end:
            _fail("ID_RANGE_ORDER", source, line, f"range start must be less than end: {text}")
        return RangeId(start, end)
    match = _EMPTY_RE.fullmatch(text)
    if match:
        return TokenId(int(match.group(1)), int(match.group(2)))
    _fail("ID_MALFORMED", source, line, f"malformed ID {text!r}")


def _check_pipe_attrs(value: str, source: str, line: int, field: str) -> None:
    if value == "_":
        return
    entries = value.split("|")
    for entry in entries:
        if "=" not in entry:
            _fail(f"{field}_GRAMMAR", source, line, f"malformed {field}: {value!r}")
        name, raw_values = entry.split("=", 1)
        values = raw_values.split(",")
        if not _FEAT_NAME_RE.fullmatch(name) or any(not _FEAT_VALUE_RE.fullmatch(item) for item in values):
            _fail(f"{field}_GRAMMAR", source, line, f"malformed {field}: {value!r}")
    keys = [entry.split("=", 1)[0] for entry in entries]
    if keys != sorted(keys, key=str.casefold) or len(keys) != len(set(keys)):
        _fail(f"{field}_ORDER", source, line, f"{field} keys must be unique and sorted")
    if field == "FEATS":
        for entry in entries:
            vals = entry.split("=", 1)[1].split(",")
            if vals != sorted(vals, key=str.casefold) or len(vals) != len(set(vals)):
                _fail("FEATS_VALUE_ORDER", source, line, "FEATS values must be unique and sorted")


def _parse_deps(value: str, source: str, line: int) -> list[tuple[TokenId, str]]:
    if value == "_":
        return []
    parsed: list[tuple[TokenId, str]] = []
    for entry in value.split("|"):
        if ":" not in entry:
            _fail("DEPS_GRAMMAR", source, line, f"missing relation in {entry!r}")
        head_text, relation = entry.split(":", 1)
        if not _REL_RE.fullmatch(relation) or relation.split(":", 1)[0] not in _ENHANCED_DEPREL_BASES:
            _fail("DEPS_RELATION", source, line, f"malformed relation {relation!r}")
        if head_text == "0":
            head = TokenId(0)
        else:
            maybe = _typed_id(head_text, source, line)
            if isinstance(maybe, RangeId):
                _fail("DEPS_RANGE_HEAD", source, line, "DEPS cannot reference a range")
            head = maybe
        parsed.append((head, relation))
    keys = [(h.major, -1 if h.minor is None else h.minor) for h, _ in parsed]
    if keys != sorted(keys):
        _fail("DEPS_ORDER", source, line, "DEPS heads are not in typed numeric order")
    pairs = [(h.text(), rel) for h, rel in parsed]
    if len(pairs) != len(set(pairs)):
        _fail("DEPS_DUPLICATE", source, line, "duplicate (head, relation) in DEPS")
    return parsed


def _validate_sentence(rows: list[Row], comments: list[tuple[str, int]], source: str, start_line: int) -> Sentence:
    sent_ids = [(match.group(1), line) for c, line in comments if (match := re.fullmatch(r"#\s+sent_id\s*=\s*(\S+)\s*", c))]
    texts = [(match.group(1), line) for c, line in comments if (match := re.fullmatch(r"#\s+text\s*=\s*(\S(?:.*\S)?)\s*", c))]
    if len(sent_ids) != 1 or not sent_ids[0][0]:
        _fail("SENT_ID_COUNT", source, start_line, "sentence requires exactly one nonempty sent_id")
    if len(texts) != 1 or not texts[0][0]:
        _fail("TEXT_COUNT", source, start_line, "sentence requires exactly one nonempty text")
    if not rows:
        _fail("SENTENCE_EMPTY", source, start_line, "sentence metadata has no rows")

    integer_rows = [r for r in rows if isinstance(r.id, TokenId) and not r.id.is_empty]
    ids = [r.id.major for r in integer_rows]  # type: ignore[union-attr]
    if ids != list(range(1, len(ids) + 1)):
        _fail("ID_NONCONSECUTIVE", source, integer_rows[0].line if integer_rows else start_line, f"integer IDs are {ids}")
    existing = {TokenId(i) for i in ids}
    empty_existing = {r.id for r in rows if isinstance(r.id, TokenId) and r.id.is_empty}

    last_range_end = 0
    pending_range_start: int | None = None
    seen_integer = 0
    empty_suffix: dict[int, int] = {}
    basic_heads: dict[int, int] = {}
    roots: list[int] = []
    for row in rows:
        fields = row.fields
        rid = row.id
        _check_pipe_attrs(fields[5], source, row.line, "FEATS")
        if any(" " in fields[index] for index in (0, 3, 4, 5, 6, 7, 8)):
            _fail("FIELD_SPACE", source, row.line, "fields other than FORM, LEMMA, and MISC cannot contain spaces")
        if isinstance(rid, RangeId):
            if rid.start != seen_integer + 1 or rid.start <= last_range_end:
                _fail("MWT_POSITION", source, row.line, "range must precede its covered tokens and not overlap")
            if any(fields[i] != "_" for i in (2, 3, 4, 6, 7, 8)):
                _fail("MWT_UNDERSCORE", source, row.line, "MWT restricted fields must be underscore")
            if fields[5] not in {"_", "Typo=Yes"}:
                _fail("MWT_FEATS", source, row.line, "MWT FEATS must be _ or Typo=Yes")
            last_range_end = rid.end
            pending_range_start = rid.start
            continue
        if rid.is_empty:
            if pending_range_start is not None:
                _fail("EMPTY_AFTER_MWT", source, row.line, "an empty node for the prior token must precede the following MWT range")
            if rid.major != seen_integer:
                _fail("EMPTY_POSITION", source, row.line, "empty node must follow its base and precede next integer")
            expected = empty_suffix.get(rid.major, 0) + 1
            if rid.minor != expected:
                _fail("EMPTY_SUFFIX", source, row.line, f"expected {rid.major}.{expected}")
            empty_suffix[rid.major] = expected
            if fields[6] != "_" or fields[7] != "_" or fields[8] == "_":
                _fail("EMPTY_FIELDS", source, row.line, "empty node requires HEAD/DEPREL _ and nonempty DEPS")
            if fields[3] != "_" and fields[3] not in UPOS:
                _fail("UPOS", source, row.line, f"unknown empty-node UPOS {fields[3]!r}")
        else:
            seen_integer += 1
            if rid.major != seen_integer:
                _fail("ID_POSITION", source, row.line, "integer IDs must be consecutive")
            if pending_range_start is not None and rid.major == pending_range_start:
                pending_range_start = None
            if fields[3] not in UPOS:
                _fail("UPOS", source, row.line, f"unknown UPOS {fields[3]!r}")
            if not re.fullmatch(r"0|[1-9][0-9]*", fields[6]):
                _fail("HEAD", source, row.line, "integer token HEAD must be a nonnegative integer")
            head = int(fields[6])
            if head == rid.major:
                _fail("HEAD_SELF", source, row.line, "basic HEAD cannot be self")
            if not _BASIC_DEPREL_RE.fullmatch(fields[7]) or fields[7].split(":", 1)[0] not in _BASIC_DEPREL_BASES:
                _fail("DEPREL", source, row.line, f"malformed dependency relation {fields[7]!r}")
            if (head == 0) != (fields[7] == "root"):
                _fail("ROOT_RELATION", source, row.line, "HEAD=0 iff DEPREL=root")
            basic_heads[rid.major] = head
            if head == 0:
                roots.append(rid.major)

        deps = _parse_deps(fields[8], source, row.line)
        for dep_head, _ in deps:
            if dep_head.major == 0 and dep_head.minor is None:
                continue
            if dep_head not in existing and dep_head not in empty_existing:
                _fail("DEPS_REFERENCE", source, row.line, f"unknown DEPS head {dep_head.text()}")

    for row in rows:
        if isinstance(row.id, RangeId) and row.id.end > len(integer_rows):
            _fail("MWT_RANGE", source, row.line, "range exceeds sentence integer IDs")
    if len(roots) != 1:
        _fail("ROOT_COUNT", source, start_line, f"expected one root, found {len(roots)}")
    for child, head in basic_heads.items():
        if head and head not in basic_heads:
            _fail("HEAD_REFERENCE", source, start_line, f"token {child} references absent HEAD {head}")
        seen: set[int] = set()
        cursor = child
        while cursor:
            if cursor in seen:
                _fail("HEAD_CYCLE", source, start_line, f"cycle through token {cursor}")
            seen.add(cursor)
            cursor = basic_heads[cursor]

    return Sentence(sent_ids[0][0], texts[0][0], tuple(c for c, _ in comments), tuple(rows), start_line)


def parse_bytes(data: bytes, *, source: str = "<bytes>", profile: Profile = "strict") -> ParseResult:
    if profile not in {"strict", "reader"}:
        raise ValueError(f"unknown profile: {profile}")
    try:
        raw = data.decode("utf-8", errors="strict")
    except UnicodeDecodeError as exc:
        _fail("UTF8", source, data[: exc.start].count(b"\n") + 1, "input is not strict UTF-8")
    if unicodedata.normalize("NFC", raw) != raw:
        for number, candidate in enumerate(raw.splitlines(), 1):
            if unicodedata.normalize("NFC", candidate) != candidate:
                _fail("UNICODE_NFC", source, number, "input is not NFC-normalized")
        _fail("UNICODE_NFC", source, 1, "input is not NFC-normalized")
    for index, character in enumerate(raw):
        if character in {"\t", "\n", "\r"}:
            continue
        if unicodedata.category(character) in {"Cc", "Zl", "Zp"}:
            _fail("LINE_ENDING", source, raw[:index].count("\n") + 1, f"forbidden control/line separator U+{ord(character):04X}")

    deviations: list[str] = []
    if "\r" in raw:
        if profile == "strict" or raw.replace("\r\n", "").find("\r") != -1:
            _fail("LINE_ENDING", source, 1, "strict profile requires LF-only line endings")
        raw = raw.replace("\r\n", "\n")
        deviations.append("CRLF_NORMALIZED")
    if raw and not raw.endswith("\n\n"):
        if profile == "strict":
            _fail("FINAL_BLANK", source, raw.count("\n") + 1, "file must end with a blank line")
        raw += "\n" if raw.endswith("\n") else "\n\n"
        if not raw.endswith("\n\n"):
            raw += "\n"
        deviations.append("CLEAN_EOF_ACCEPTED")
    if not raw:
        _fail("EMPTY_FILE", source, 1, "CoNLL-U file contains no sentences")

    sentences: list[Sentence] = []
    comments: list[tuple[str, int]] = []
    rows: list[Row] = []
    start_line = 1
    saw_data = False
    seen_sent_ids: set[str] = set()

    def flush(line: int) -> None:
        nonlocal comments, rows, start_line, saw_data
        if not comments and not rows:
            _fail("EXTRA_BLANK", source, line, "leading or repeated blank sentence separator")
        sentence = _validate_sentence(rows, comments, source, start_line)
        if sentence.sent_id in seen_sent_ids:
            _fail("SENT_ID_DUPLICATE", source, start_line, f"duplicate sent_id {sentence.sent_id!r}")
        seen_sent_ids.add(sentence.sent_id)
        sentences.append(sentence)
        comments, rows, saw_data = [], [], False
        start_line = line + 1

    for line_number, line in enumerate(raw.splitlines(), 1):
        if line == "":
            flush(line_number)
            continue
        if line.startswith("#"):
            if saw_data:
                _fail("COMMENT_AFTER_DATA", source, line_number, "comments must precede rows")
            if re.match(r"#\s+sent_id(?:\s|=|$)", line) and not re.fullmatch(r"#\s+sent_id\s*=\s*\S+\s*", line):
                _fail("SENT_ID_HEADER", source, line_number, "partial sent_id header")
            if re.match(r"#\s+text(?:\s|=|$)", line) and not re.fullmatch(r"#\s+text\s*=\s*\S(?:.*\S)?\s*", line):
                _fail("TEXT_HEADER", source, line_number, "partial text header")
            comments.append((line, line_number))
            continue
        saw_data = True
        fields = tuple(line.split("\t"))
        if len(fields) != 10:
            _fail("COLUMN_COUNT", source, line_number, f"expected 10 columns, got {len(fields)}")
        if any(field == "" for field in fields):
            _fail("EMPTY_FIELD", source, line_number, "empty fields must be represented by underscore")
        rows.append(Row(_typed_id(fields[0], source, line_number), fields, line_number))
    return ParseResult(tuple(sentences), tuple(deviations), profile)


def parse_file(path: Path | str, *, profile: Profile = "strict") -> ParseResult:
    file_path = Path(path)
    return parse_bytes(file_path.read_bytes(), source=file_path.as_posix(), profile=profile)


def validate_unique_sent_ids(results: Iterable[tuple[str, ParseResult]]) -> None:
    """Validate treebank/manifest-wide sent_id uniqueness across already parsed files."""
    seen: dict[str, str] = {}
    for source, result in results:
        for sentence in result.sentences:
            prior = seen.get(sentence.sent_id)
            if prior is not None:
                _fail("SENT_ID_DUPLICATE_MANIFEST", source, sentence.start_line, f"{sentence.sent_id!r} also in {prior}")
            seen[sentence.sent_id] = source


__all__: Sequence[str] = (
    "ConlluError", "ParseResult", "Profile", "RangeId", "Row", "Sentence", "TokenId",
    "parse_bytes", "parse_file", "validate_unique_sent_ids",
)
