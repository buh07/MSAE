#!/usr/bin/env python3
"""Prescore builder and launch controller for the exposed-source MSAE v2 study.

This file deliberately keeps all pre-score work in the standard library.  The
only optional prescore dependency is the already-frozen Hugging Face tokenizer,
which is imported by ``build-labels`` and never loads model weights.  Commands
which can start a model are separately authorized and are unavailable through
the builder commands.
"""
from __future__ import annotations

import argparse
import array
import ast
import base64
import collections
import contextlib
import datetime as dt
import decimal
import fcntl
import hashlib
import importlib.metadata
import io
import json
import os
import re
import shutil
import socket
import stat
import struct
import subprocess
import sys
import tempfile
import time
import unicodedata
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Iterable, Iterator, Mapping, Sequence


ROOT = Path(__file__).resolve().parents[1]
PROTOCOL = "msae_exposed_source_measurement_v2"
DATE = "20260820"
V2_DATA = ROOT / "data/msae_independent_measurement_v2"
V2_CONFIG = ROOT / "configs/msae_independent_measurement_v2"
V2_PROV = ROOT / "reports/provenance/msae_independent_measurement_v2"
V2_REVIEW = ROOT / "reports/adversarial/msae_independent_measurement_v2_prescore.md"
RUN_REL = "pilot_runs/20260820_msae_independent_measurement_v2_calibration"
RUN_ROOT = ROOT / RUN_REL
SNAPSHOT = Path("/jumbo/lisp/f004ndc/huggingface/hub/models--EleutherAI--pythia-160m-deduped/snapshots/582159a2dfe3e712a8d47ae83dec95ae3bde8e7e")
PRIVATE_KEY = Path("/jumbo/lisp/f004ndc/.msae_keys/independent_measurement_v2_ed25519_private.pem")
STATE_ROOT = Path("/jumbo/lisp/f004ndc/.msae_state")
NONCE_DIR = STATE_ROOT / "independent_measurement_v2/nonces"
GPU_LOCK_DIR = STATE_ROOT / "gpu_locks"
QUARANTINED = {
    "data/atlas_v1/private/final.jsonl": ("684d48c6fd5fd6a1faec5ca5785eb9a054fc94a603422088c5e9eb6a485c8eee", 49550),
    "data/atlas_v1/private/final.records.jsonl": ("5d397a7695bb46d1e0700af9af084272fa627ba815ada8b5197bac740510471e", 10172061),
    "data/atlas_v1/private/final.units.jsonl": ("3acb17e56fead3c1abc915978ff7733a4ccb0e0c3dcb787410deffbaffc79e23", 29193353),
}
PREFIXES = ("", "In fact, ", "As a result, ", "According to the report, ")
ROLES = ("discovery", "calibration", "C1", "C2")
TASKS = (
    "absolute_bucket", "neutral_prefix_offset", "relative_quartile",
    "token_identity", "lemma_identity", "capitalization", "word_length",
    "punctuation", "sentence_boundary", "head_signed_distance",
    "dependency_depth", "upos_coarse", "deprel_coarse", "number",
    "entity_binary", "entity_type", "source_genre",
)
UPOS = frozenset("ADJ ADP ADV AUX CCONJ DET INTJ NOUN NUM PART PRON PROPN PUNCT SCONJ SYM VERB X".split())
DEPREL = frozenset("acl advcl advmod amod appos aux case cc ccomp clf compound conj cop csubj dep det discourse dislocated expl fixed flat goeswith iobj list mark nmod nsubj nummod obj obl orphan parataxis punct reparandum root vocative xcomp".split())
NUMBER = frozenset("Sing Plur Dual Trial Pauc Grpa Grpl Inv Ptan".split())
LEX_RE = re.compile(r"[^\W_]+", re.UNICODE)
HEX_RE = re.compile(r"[0-9a-f]{64}\Z", re.ASCII)
ENTITY_KEY_RE = re.compile(r"([A-Za-z][A-Za-z0-9_-]*?)-([1-9][0-9]*)", re.ASCII)
DECIMAL_CONTEXT = decimal.Context(prec=50, rounding=decimal.ROUND_HALF_EVEN)


def canonical_bytes(value: Any) -> bytes:
    return (json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False,
                       allow_nan=False) + "\n").encode("utf-8")


def sha_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def validate_sha256(value: Any, field: str = "sha256") -> str:
    if not isinstance(value, str) or HEX_RE.fullmatch(value) is None:
        raise ValueError(f"{field} must be exactly 64 lowercase ASCII hex characters")
    return value


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def write_once(path: Path, payload: bytes, mode: int = 0o644) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW | os.O_CLOEXEC, mode)
    try:
        with os.fdopen(fd, "wb", closefd=False) as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
    finally:
        os.close(fd)


def install_json(path: Path, value: Any) -> None:
    write_once(path, canonical_bytes(value))


def typed_tuple(parts: Sequence[str | int]) -> bytes:
    out = bytearray(struct.pack(">Q", len(parts)))
    for part in parts:
        if isinstance(part, bool):
            raise ValueError("bool is not an integer tuple element")
        if isinstance(part, str):
            if unicodedata.normalize("NFC", part) != part:
                raise ValueError("tuple strings must already be NFC")
            raw = part.encode("utf-8")
            out.extend(b"\x01" + struct.pack(">Q", len(raw)) + raw)
        elif isinstance(part, int) and 0 <= part < (1 << 64):
            out.extend(b"\x02" + struct.pack(">Q", part))
        else:
            raise ValueError("unsupported typed tuple element")
    return bytes(out)


def tuple_digest(*parts: str | int) -> str:
    return sha_bytes(typed_tuple(parts))


def lexical_tokens(text: str) -> tuple[str, ...]:
    if not isinstance(text, str):
        raise ValueError("text must be a string")
    if any(0xD800 <= ord(ch) <= 0xDFFF for ch in text):
        raise ValueError("surrogate code point is forbidden")
    return tuple(unicodedata.normalize("NFC", x).lower() for x in LEX_RE.findall(unicodedata.normalize("NFC", text)))


def token_field(value: Any, field: str) -> tuple[str, ...]:
    if field in {"source_words", "target_words", "words", "tokens"}:
        if not isinstance(value, list) or not value or any(not isinstance(x, str) or not x for x in value):
            raise ValueError(f"{field} must be a nonempty array of nonempty strings")
        result = tuple(y for x in value for y in lexical_tokens(x))
    else:
        if not isinstance(value, str):
            raise ValueError(f"{field} must be a string")
        result = lexical_tokens(value)
    return result


def framed_sentences(sentences: Sequence[Sequence[str]]) -> bytes:
    out = bytearray(struct.pack(">Q", len(sentences)))
    for sentence in sentences:
        out.extend(struct.pack(">Q", len(sentence)))
        for token in sentence:
            raw = token.encode("utf-8")
            out.extend(struct.pack(">Q", len(raw)) + raw)
    return bytes(out)


def framed_flat(tokens: Sequence[str]) -> bytes:
    out = bytearray(struct.pack(">Q", len(tokens)))
    for token in tokens:
        raw = token.encode("utf-8")
        out.extend(struct.pack(">Q", len(raw)) + raw)
    return bytes(out)


def grams(tokens: Sequence[str]) -> frozenset[bytes]:
    return frozenset(typed_tuple(tuple(tokens[i:i + 5])) for i in range(max(0, len(tokens) - 4)))


@dataclass(frozen=True)
class TextDocument:
    source_id: str
    path: str
    record_index: int
    sentences: tuple[tuple[str, ...], ...]

    @property
    def tokens(self) -> tuple[str, ...]:
        return tuple(x for sentence in self.sentences for x in sentence)

    @property
    def fivegrams(self) -> frozenset[bytes]:
        return grams(self.tokens)

    @property
    def aware_sha256(self) -> str:
        return sha_bytes(framed_sentences(self.sentences))

    @property
    def flat_sha256(self) -> str:
        return sha_bytes(framed_flat(self.tokens))


def _split_misc(raw: str, *, allow_bare: bool = False) -> dict[str, str]:
    if raw == "_":
        return {}
    result: dict[str, str] = {}
    for item in raw.split("|"):
        if "=" not in item:
            if allow_bare and item:
                key, value = item, ""
            else:
                raise ValueError(f"malformed MISC item {item!r}")
        else:
            key, value = item.split("=", 1)
        if not key or (not value and not allow_bare) or key in result:
            raise ValueError(f"invalid/duplicate MISC key {key!r}")
        result[key] = value
    return result


def parse_entity_events(value: str) -> list[tuple[str, str, int]]:
    """Parse GUM's concatenated Entity event syntax without guessing."""
    if not value:
        raise ValueError("empty Entity value")
    events: list[tuple[str, str, int]] = []
    pos = 0
    while pos < len(value):
        if value[pos] == "(":
            match = ENTITY_KEY_RE.match(value, pos + 1)
            if match is None:
                raise ValueError(f"malformed Entity open at {pos}: {value!r}")
            end = match.end()
            kind = "singleton" if end < len(value) and value[end] == ")" else "open"
            if kind == "singleton":
                end += 1
            events.append((kind, match.group(1), int(match.group(2))))
            pos = end
        else:
            match = ENTITY_KEY_RE.match(value, pos)
            if match is None or match.end() >= len(value) or value[match.end()] != ")":
                raise ValueError(f"malformed Entity close at {pos}: {value!r}")
            events.append(("close", match.group(1), int(match.group(2))))
            pos = match.end() + 1
    return events


def _reconstruct_text(rows: Sequence[list[str]], multiwords: Sequence[list[str]] = (), *, allow_bare_misc: bool = False) -> str:
    mw = {int(row[0].split("-", 1)[0]): (int(row[0].split("-", 1)[1]), row)
          for row in multiwords}
    out = []
    skip_through = 0
    for fields in rows:
        idx = int(fields[0])
        if idx <= skip_through:
            continue
        if idx in mw:
            skip_through, fields = mw[idx]
        out.append(fields[1])
        misc = _split_misc(fields[9], allow_bare=allow_bare_misc)
        if "SpaceAfter" in misc and "SpacesAfter" in misc:
            raise ValueError("SpaceAfter and SpacesAfter cannot coexist")
        if misc.get("SpaceAfter") == "No":
            spacing = ""
        elif "SpacesAfter" in misc:
            raw = misc["SpacesAfter"]

            def replace(match: re.Match[str]) -> str:
                value = match.group(0)
                simple = {r"\s": " ", r"\n": "\n", r"\t": "\t", r"\r": "\r", r"\p": "|", r"\\": "\\"}
                return simple[value] if value in simple else chr(int(value[2:], 16))

            spacing = re.sub(r"\\u[0-9A-Fa-f]{4}|\\[sntrp\\]", replace, raw)
            if "\\" in spacing:
                raise ValueError("unknown SpacesAfter escape")
        else:
            spacing = " "
        out.append(spacing)
    return "".join(out).rstrip()


def parse_conllu(path: Path, *, strict_entities: bool = True) -> list[dict[str, Any]]:
    """Return strict document/sentence/token structures and resolved spans."""
    lines = path.read_text(encoding="utf-8").splitlines()
    documents: list[dict[str, Any]] = []
    doc: dict[str, Any] | None = None
    sent_rows: list[list[str]] = []
    sent_multiwords: list[list[str]] = []
    sent_comments: dict[str, str] = {}
    stacks: dict[tuple[str, int], list[tuple[int, int]]] = collections.defaultdict(list)
    event_ordinal = 0

    def start_doc(doc_id: str) -> None:
        nonlocal doc, stacks, event_ordinal
        if doc is not None:
            finish_doc()
        doc = {"document_id": doc_id, "sentences": [], "tokens": [], "spans": []}
        stacks = collections.defaultdict(list)
        event_ordinal = 0

    def finish_sentence() -> None:
        nonlocal sent_rows, sent_multiwords, sent_comments, event_ordinal, doc
        if not sent_rows:
            sent_comments = {}
            return
        if doc is None:
            start_doc(path.stem)
        assert doc is not None
        ids = [int(row[0]) for row in sent_rows]
        if ids != list(range(1, len(ids) + 1)):
            raise ValueError(f"non-contiguous integer IDs in {path}")
        idset = set(ids)
        for row in sent_rows:
            if len(row) != 10 or not row[1] or not row[2] or not row[3] or not row[7]:
                raise ValueError(f"malformed CoNLL-U row in {path}")
            try:
                head = int(row[6])
            except ValueError as error:
                raise ValueError(f"invalid HEAD in {path}") from error
            if head not in idset | {0}:
                raise ValueError(f"out-of-sentence HEAD in {path}")
        expected = sent_comments.get("text")
        if expected is not None and expected != _reconstruct_text(sent_rows, sent_multiwords, allow_bare_misc=not strict_entities):
            if strict_entities:
                raise ValueError(f"# text reconstruction mismatch in {path}: {sent_comments.get('sent_id')}")
        sentence_id = sent_comments.get("sent_id", f"{doc['document_id']}-{len(doc['sentences'])}")
        sentence_tokens: list[dict[str, Any]] = []
        for row in sent_rows:
            global_index = len(doc["tokens"])
            token = {"id": int(row[0]), "form": row[1], "lemma": row[2], "upos": row[3],
                     "feats": row[5], "head": int(row[6]), "deprel": row[7],
                     "misc": row[9], "document_token_index": global_index,
                     "entity_spans": []}
            misc = _split_misc(row[9], allow_bare=not strict_entities)
            if strict_entities and "Entity" in misc:
                for kind, typ, entity_id in parse_entity_events(misc["Entity"]):
                    key = (typ, entity_id)
                    if kind == "open":
                        stacks[key].append((global_index, event_ordinal))
                    elif kind == "singleton":
                        doc["spans"].append((global_index, global_index, typ, entity_id, event_ordinal))
                    else:
                        if not stacks[key]:
                            raise ValueError(f"Entity close underflow {key} in {path}")
                        start, opened = stacks[key].pop()
                        doc["spans"].append((start, global_index, typ, entity_id, opened))
                    event_ordinal += 1
            sentence_tokens.append(token)
            doc["tokens"].append(token)
        doc["sentences"].append({"sentence_id": sentence_id, "tokens": sentence_tokens})
        sent_rows = []
        sent_multiwords = []
        sent_comments = {}

    def finish_doc() -> None:
        nonlocal doc
        finish_sentence()
        if doc is None:
            return
        leftovers = {str(k): len(v) for k, v in stacks.items() if v}
        if leftovers:
            raise ValueError(f"unclosed Entity spans in {path}: {leftovers}")
        for span in sorted(doc["spans"], key=lambda x: (x[0], -x[1], x[2].encode(), x[3], x[4])):
            for idx in range(span[0], span[1] + 1):
                doc["tokens"][idx]["entity_spans"].append(span)
        documents.append(doc)
        doc = None

    for line in lines + [""]:
        if line.startswith("# newdoc id = "):
            finish_sentence()
            start_doc(line.split("=", 1)[1].strip())
        elif not line:
            finish_sentence()
        elif line.startswith("#"):
            if " = " in line:
                key, value = line[2:].split(" = ", 1)
                if key in {"sent_id", "text"}:
                    if key in sent_comments:
                        raise ValueError(f"duplicate {key} comment in {path}")
                    sent_comments[key] = value
        else:
            fields = line.split("\t")
            if len(fields) != 10:
                raise ValueError(f"CoNLL-U row does not have ten fields in {path}")
            if fields[0].isdigit():
                sent_rows.append(fields)
            elif re.fullmatch(r"[1-9][0-9]*-[1-9][0-9]*", fields[0]):
                # Provenance-only row.  Its field count was checked above.
                sent_multiwords.append(fields)
            elif re.fullmatch(r"[0-9]+\.[1-9][0-9]*", fields[0]):
                continue
            else:
                raise ValueError(f"invalid CoNLL-U ID {fields[0]!r} in {path}")
    finish_doc()
    if not documents:
        raise ValueError(f"no documents in {path}")
    return documents


def conllu_text_documents(path: Path, rel: str) -> list[TextDocument]:
    out = []
    for index, doc in enumerate(parse_conllu(path, strict_entities=False)):
        sentences = tuple(tuple(piece for token in sentence["tokens"]
                                for piece in lexical_tokens(token["form"]))
                          for sentence in doc["sentences"])
        sentences = tuple(tuple(x for x in sentence if x) for sentence in sentences)
        sentences = tuple(x for x in sentences if x)
        if not sentences:
            # A syntactically valid redacted/punctuation-only CoNLL-U document
            # is bound by its file census but is not a corpus-text document.
            continue
        out.append(TextDocument(doc["document_id"], rel, index, sentences))
    return out


def _json_object_records(obj: Any, path: str, index: int) -> list[tuple[str, tuple[str, ...]]]:
    if not isinstance(obj, dict):
        return []
    fields = ("source_words", "target_words", "words", "tokens", "text", "sentence")
    present = [field for field in fields if field in obj]
    if not present:
        return []
    if any(field in present for field in ("source_words", "target_words")):
        if set(present) != {"source_words", "target_words"}:
            raise ValueError(f"mixed paired/base text grammar at {path}:{index}")
        return [(side, tokens) for side, tokens in
                (("source", token_field(obj["source_words"], "source_words")),
                 ("target", token_field(obj["target_words"], "target_words"))) if tokens]
    normalized = [(field, token_field(obj[field], field)) for field in present]
    if any(tokens != normalized[0][1] for _, tokens in normalized[1:]):
        raise ValueError(f"conflicting text fields at {path}:{index}")
    if not normalized[0][1]:
        return []
    return [("base", normalized[0][1])]


def json_documents(path: Path, rel: str, *, jsonl: bool) -> tuple[list[TextDocument], dict[str, int]]:
    rows: list[Any]
    if jsonl:
        rows = []
        with path.open("r", encoding="utf-8") as handle:
            for index, line in enumerate(handle):
                try:
                    rows.append(json.loads(line))
                except json.JSONDecodeError as error:
                    raise ValueError(f"invalid JSONL {rel}:{index}") from error
    else:
        value = read_json(path)
        if isinstance(value, list):
            rows = value
        elif isinstance(value, dict) and len([k for k in ("records", "rows", "data") if k in value]) == 1:
            key = next(k for k in ("records", "rows", "data") if k in value)
            if not isinstance(value[key], list):
                return [], {"non_text_metadata": 1}
            rows = value[key]
        else:
            return [], {"non_text_metadata": 1}
    grouped: dict[str, list[tuple[str, ...]]] = collections.OrderedDict()
    identities: dict[str, tuple[Any, ...]] = {}
    census = collections.Counter()
    for index, row in enumerate(rows):
        records = _json_object_records(row, rel, index)
        if not records:
            census["non_text_row"] += 1
            continue
        if not isinstance(row, dict):
            raise AssertionError
        revision, group = row.get("source_revision"), row.get("document_group")
        stable_group = isinstance(revision, str) and revision and isinstance(group, str) and group
        for side, tokens in records:
            identity = f"{revision}:{group}:{side}" if stable_group else f"{rel}:{index}:{side}"
            semantic = (revision, group, side) if stable_group else (rel, index, side)
            if identity in identities and identities[identity] != semantic:
                raise ValueError(f"identity conflict in {rel}")
            identities[identity] = semantic
            grouped.setdefault(identity, []).append(tokens)
            census[f"text_{side}"] += 1
    docs = [TextDocument(identity, rel, index, tuple(sentences))
            for index, (identity, sentences) in enumerate(grouped.items())]
    census["documents"] = len(docs)
    return docs, dict(census)


def line_documents(path: Path, rel: str) -> list[TextDocument]:
    sentences = tuple(tokens for line in path.read_text(encoding="utf-8").splitlines()
                      if (tokens := lexical_tokens(line)))
    return [] if not sentences else [TextDocument(rel, rel, 0, sentences)]


def verify_binary_array(path: Path, suffix: str) -> None:
    with path.open("rb") as handle:
        head = handle.read(8)
    if suffix == ".npy" and not head.startswith(b"\x93NUMPY"):
        raise ValueError(f"invalid NPY magic: {path}")
    if suffix == ".npz" and not head.startswith(b"PK\x03\x04"):
        raise ValueError(f"invalid NPZ magic: {path}")


def selected_documents() -> tuple[list[TextDocument], list[dict[str, Any]]]:
    partition = read_json(ROOT / "data/msae_independent_measurement_v1/source_partition.json")
    docs: list[TextDocument] = []
    aliases = []
    for item in partition["selected"]:
        rel = f"data/msae_independent_measurement_v1/selected_raw/{item['path']}"
        path = ROOT / rel
        if sha_file(path) != item["sha256"]:
            raise ValueError(f"selected alias drift: {rel}")
        parsed = conllu_text_documents(path, rel)
        docs.extend(parsed)
        aliases.append({"path": rel, "source_path": item["path"], "sha256": item["sha256"],
                        "bytes": item["bytes"], "role": item["role"], "genre": item["genre"],
                        "verification_action": "same_frozen_source_copy"})
    root = ROOT / "data/msae_independent_measurement_v1/selected_raw"
    entries = sorted(x.relative_to(root).as_posix() for x in root.rglob("*") if x.is_file())
    expected = sorted([x["source_path"] for x in aliases] + ["README.md", "DEVELOPMENT.md"])
    if entries != expected:
        raise ValueError("selected alias root is not exactly the frozen 350 files plus two Markdown files")
    return docs, aliases


def _baseline_regular_entries() -> list[dict[str, Any]]:
    baseline = read_json(V2_DATA / "data_baseline_manifest.json")
    return [entry for entry in baseline["entries"] if entry["type"] == "regular"]


def iter_history(*, candidate_grams: set[bytes] | None = None) -> Iterator[tuple[TextDocument, dict[str, Any]]]:
    """Yield canonical historical text documents without opening quarantined bytes."""
    _, aliases = selected_documents()
    alias_paths = {x["path"]: x["sha256"] for x in aliases}
    seen_file_sha: dict[str, str] = {}
    seen_source: dict[str, tuple[str, str]] = {}
    for entry in sorted(_baseline_regular_entries(), key=lambda x: x["path"]):
        rel = entry["path"]
        if rel in QUARANTINED:
            continue
        if rel in alias_paths:
            if entry["sha256"] != alias_paths[rel]:
                raise ValueError(f"alias manifest mismatch: {rel}")
            continue
        path = ROOT / rel
        suffix = path.suffix.lower()
        if suffix not in {".conllu", ".jsonl", ".json", ".md", ".diff", ".npy", ".npz"}:
            raise ValueError(f"unknown baseline suffix: {rel}")
        digest = entry["sha256"]
        if digest in seen_file_sha:
            continue
        seen_file_sha[digest] = rel
        if suffix in {".npy", ".npz"}:
            verify_binary_array(path, suffix)
            continue
        if suffix == ".conllu":
            docs = conllu_text_documents(path, rel)
            docs = [TextDocument(f"{digest}:{doc.record_index}", doc.path, doc.record_index, doc.sentences)
                    for doc in docs]
            census = {"documents": len(docs), "adapter": "conllu"}
        elif suffix in {".md", ".diff"}:
            docs = line_documents(path, rel)
            census = {"documents": len(docs), "adapter": suffix[1:]}
        else:
            docs, census = json_documents(path, rel, jsonl=suffix == ".jsonl")
            census["adapter"] = suffix[1:]
        for doc in docs:
            # source_id is the canonical identity.  Equal identity with unequal
            # normalized payload is an audit-blocking conflict.
            signature = (doc.aware_sha256, doc.flat_sha256)
            prior = seen_source.get(doc.source_id)
            if prior is not None:
                if prior != signature:
                    raise ValueError(f"conflicting canonical source identity: {doc.source_id}")
                continue
            seen_source[doc.source_id] = signature
            yield doc, {"adapter": census["adapter"], "file_sha256": digest}


def _plain_jaccard(a: frozenset[bytes], b: frozenset[bytes]) -> decimal.Decimal | None:
    union = a | b
    if not union:
        return None
    with decimal.localcontext(DECIMAL_CONTEXT):
        return decimal.Decimal(len(a & b)) / decimal.Decimal(len(union))


def weighted_jaccard(a: frozenset[bytes], b: frozenset[bytes], weights: Mapping[bytes, decimal.Decimal]) -> decimal.Decimal | None:
    union = sorted(a | b)
    if not union:
        return None
    with decimal.localcontext(DECIMAL_CONTEXT):
        numerator = sum((weights[g] for g in sorted(a & b)), decimal.Decimal(0))
        denominator = sum((weights[g] for g in union), decimal.Decimal(0))
        if not denominator.is_finite() or denominator <= 0:
            raise ValueError("invalid IDF union weight")
        return numerator / denominator


def pair_decision(selected: TextDocument, historical: TextDocument,
                  weights: Mapping[bytes, decimal.Decimal] | None = None) -> dict[str, Any]:
    st, ht = selected.tokens, historical.tokens
    sg, hg = selected.fivegrams, historical.fivegrams
    reasons: list[str] = []
    aware_equal = selected.aware_sha256 == historical.aware_sha256
    flat_equal = selected.flat_sha256 == historical.flat_sha256
    if aware_equal or flat_equal:
        reasons.append("exact_full_document")
    plain = _plain_jaccard(sg, hg)
    weighted = weighted_jaccard(sg, hg, weights) if weights is not None and sg | hg else None
    comparable = len(st) >= 50 and len(ht) >= 50 and len(sg) >= 20 and len(hg) >= 20
    if comparable and plain is not None and plain >= decimal.Decimal("0.80"):
        reasons.append("document_plain_jaccard")
    if comparable and weighted is not None and weighted >= decimal.Decimal("0.75"):
        reasons.append("document_idf_jaccard")
    exact_sentence = []
    nonexact_sentence = []
    h_sent_by_hash = collections.defaultdict(list)
    for hi, sentence in enumerate(historical.sentences):
        h_sent_by_hash[sha_bytes(framed_sentences((sentence,)))].append((hi, sentence))
    for si, sentence in enumerate(selected.sentences):
        sh = sha_bytes(framed_sentences((sentence,)))
        for hi, hs in h_sent_by_hash.get(sh, []):
            if len(sentence) >= 10 and len(hs) >= 10:
                exact_sentence.append((si, hi, len(sentence)))
        a = grams(sentence)
        if len(sentence) >= 10 and len(a) >= 6:
            for hi, hs in enumerate(historical.sentences):
                if sentence == hs:
                    continue
                b = grams(hs)
                j = _plain_jaccard(a, b)
                if len(hs) >= 10 and len(b) >= 6 and j is not None and j >= decimal.Decimal("0.80"):
                    nonexact_sentence.append((si, hi, format(j, "f")))
    if exact_sentence:
        reasons.append("exact_substantive_sentence")
    if nonexact_sentence:
        reasons.append("nonexact_substantive_sentence")
    sshort = {x for x in selected.sentences if 0 < len(x) < 10}
    hshort = {x for x in historical.sentences if 0 < len(x) < 10}
    shared_short = sorted(sshort & hshort, key=lambda x: typed_tuple(x))
    short_tokens = sum(map(len, shared_short))
    if len(shared_short) >= 5 and short_tokens >= 20:
        reasons.append("cumulative_short_sentences")
    shared = sg & hg
    covered: set[int] = set()
    if shared:
        for index in range(max(0, len(st) - 4)):
            if typed_tuple(st[index:index + 5]) in shared:
                covered.update(range(index, index + 5))
    coverage = (decimal.Decimal(len(covered)) / decimal.Decimal(len(st))) if st else decimal.Decimal(0)
    if len(shared) >= 4 and len(covered) >= 20 and coverage >= decimal.Decimal("0.10"):
        reasons.append("shared_passage_coverage")
    return {
        "blocking": bool(reasons), "reasons": reasons,
        "selected_tokens": len(st), "historical_tokens": len(ht),
        "selected_distinct_grams": len(sg), "historical_distinct_grams": len(hg),
        "plain_jaccard": None if plain is None else format(plain, "f"),
        "weighted_jaccard": None if weighted is None else format(weighted, "f"),
        "exact_sentence_matches": exact_sentence,
        "nonexact_sentence_matches": nonexact_sentence,
        "shared_short_member_count": len(shared_short), "shared_short_token_count": short_tokens,
        "covered_selected_positions": len(covered), "selected_coverage": format(coverage, "f"),
    }


def build_overlap_fixtures() -> dict[str, Any]:
    def doc(name: str, sentences: Sequence[Sequence[str]]) -> TextDocument:
        return TextDocument(name, name, 0, tuple(tuple(x) for x in sentences))
    seq = tuple(f"t{i}" for i in range(100))
    fixtures: list[dict[str, Any]] = []
    cases = [
        ("exact_document", doc("s", [seq]), doc("h", [seq]), True),
        ("boundary_flattened", doc("s", [seq[i:i+4] for i in range(0, 100, 4)]), doc("h", [seq]), True),
        ("copied_15_token_sentence", doc("s", [[f"a{i}" for i in range(15)], ["unrelated"]]), doc("h", [[f"a{i}" for i in range(15)], ["else"]]), True),
        ("five_short_20_tokens", doc("s", [[f"x{i}_{j}" for j in range(4)] for i in range(5)]), doc("h", [[f"x{i}_{j}" for j in range(4)] for i in range(5)]), True),
        ("four_short_boilerplate", doc("s", [("steps",), ("buy",), ("by", "car"), ("yes",), tuple(f"sa{i}" for i in range(9))]), doc("h", [("steps",), ("buy",), ("by", "car"), ("yes",), tuple(f"hb{i}" for i in range(9))]), False),
        ("repeated_heading", doc("s", [("steps",)] * 20), doc("h", [("steps",)] * 30), False),
        ("unrelated", doc("s", [[f"a{i}" for i in range(60)]]), doc("h", [[f"b{i}" for i in range(60)]]), False),
    ]
    for name, left, right, expected in cases:
        all_grams = left.fivegrams | right.fivegrams
        weights = {g: decimal.Decimal(1) for g in all_grams}
        observed = pair_decision(left, right, weights)
        if observed["blocking"] is not expected:
            raise AssertionError(f"fixture failed: {name}")
        fixtures.append({"name": name, "expected_blocking": expected, "observed": observed})
    return {"schema_version": "msae_v2_overlap_fixtures_v1", "protocol_id": PROTOCOL,
            "thresholds_inclusive": True, "fixtures": fixtures, "status": "eligible"}


def build_overlap() -> dict[str, Any]:
    selected, aliases = selected_documents()
    install_json(V2_DATA / "source_alias_manifest.json", {
        "schema_version": "msae_v2_source_alias_manifest_v1", "protocol_id": PROTOCOL,
        "selected_count": len(aliases), "root_file_count": len(aliases) + 2, "entries": aliases,
    })
    install_json(V2_DATA / "overlap_fixtures.json", build_overlap_fixtures())
    selected_gram_index: dict[bytes, set[int]] = collections.defaultdict(set)
    selected_sentence_hashes: dict[str, set[int]] = collections.defaultdict(set)
    selected_short: dict[tuple[str, ...], set[int]] = collections.defaultdict(set)
    for si, doc in enumerate(selected):
        for gram in doc.fivegrams:
            selected_gram_index[gram].add(si)
        for sentence in doc.sentences:
            selected_sentence_hashes[sha_bytes(framed_sentences((sentence,)))].add(si)
            if len(sentence) < 10:
                selected_short[sentence].add(si)
    candidates: dict[tuple[int, str, int], TextDocument] = {}
    history_count = 0
    adapter_counts = collections.Counter()
    exact_flat = {doc.flat_sha256: i for i, doc in enumerate(selected)}
    exact_aware = {doc.aware_sha256: i for i, doc in enumerate(selected)}
    for hist, meta in iter_history():
        history_count += 1
        adapter_counts[meta["adapter"]] += 1
        indices: set[int] = set()
        for gram in hist.fivegrams:
            indices.update(selected_gram_index.get(gram, ()))
        indices.update([exact_flat[hist.flat_sha256]] if hist.flat_sha256 in exact_flat else [])
        indices.update([exact_aware[hist.aware_sha256]] if hist.aware_sha256 in exact_aware else [])
        for sentence in hist.sentences:
            indices.update(selected_sentence_hashes.get(sha_bytes(framed_sentences((sentence,))), ()))
            if len(sentence) < 10:
                indices.update(selected_short.get(sentence, ()))
        for si in indices:
            candidates[(si, hist.path, hist.record_index)] = hist
    relevant = set()
    for (si, _, _), hist in candidates.items():
        relevant.update(selected[si].fivegrams)
        relevant.update(hist.fivegrams)
    df = collections.Counter()
    universe = len(selected) + history_count
    for doc in selected:
        df.update(doc.fivegrams & relevant)
    for hist, _ in iter_history():
        df.update(hist.fivegrams & relevant)
    with decimal.localcontext(DECIMAL_CONTEXT):
        weights = {gram: decimal.Decimal(universe + 1).ln() - decimal.Decimal(count + 1).ln() + decimal.Decimal(1)
                   for gram, count in df.items()}
    collisions = []
    diagnostics = []
    for (si, _, _), hist in sorted(candidates.items(), key=lambda x: x[0]):
        decision = pair_decision(selected[si], hist, weights)
        record = {"selected_path": selected[si].path, "selected_document_id": selected[si].source_id,
                  "historical_path": hist.path, "historical_document_id": hist.source_id,
                  "historical_record_index": hist.record_index, **decision}
        (collisions if decision["blocking"] else diagnostics).append(record)
    census = {
        "schema_version": "msae_v2_history_census_v1", "protocol_id": PROTOCOL,
        "selected_documents": len(selected), "historical_documents": history_count,
        "idf_universe_documents": universe, "candidate_pairs": len(candidates),
        "relevant_gram_count": len(relevant), "adapter_document_counts": dict(sorted(adapter_counts.items())),
        "sealed_payload_content_reads": 0,
    }
    result = {
        "schema_version": "msae_v2_history_overlap_v1", "protocol_id": PROTOCOL,
        "source_disposition": "unchanged_exposed_source_technical_replication",
        "status": "eligible" if not collisions else "ineligible",
        "blocking_collision_count": len(collisions), "blocking_collisions": collisions,
        "nonblocking_candidate_diagnostics": diagnostics,
        "idf_universe_documents": universe,
        "idf_weight_payload_sha256": sha_bytes(canonical_bytes([
            [base64.b16encode(k).decode("ascii"), v, format(weights[k], "f")] for k, v in sorted(df.items())
        ])),
        "sealed_payload_content_reads": 0,
    }
    install_json(V2_DATA / "history_census.json", census)
    install_json(V2_DATA / "history_overlap.json", result)
    legacy = read_json(ROOT / "reports/provenance/msae_independent_measurement_v1/history_overlap.json")
    rows = []
    for ordinal, item in enumerate(legacy.get("blocking_collisions", [])):
        rows.append({"legacy_index": ordinal, "legacy_row": item,
                     "v2_namespace": PROTOCOL,
                     "v2_diagnostic": "short_legacy_match_is_diagnostic_unless_v2_cumulative_gate_blocks"})
    if len(rows) != 206:
        raise ValueError("frozen v1 overlap row cardinality drift")
    install_json(V2_DATA / "v1_row_crosswalk.json", {
        "schema_version": "v2_replay_crosswalk_of_frozen_v1_rows", "protocol_id": PROTOCOL,
        "legacy_status": legacy["status"], "legacy_row_count": len(rows), "rows": rows,
        "legacy_rows_preserved_verbatim": True,
    })
    return result


def _capitalization(form: str) -> str:
    letters = "".join(x for x in form if x.isalpha())
    if not letters:
        return "nonalpha"
    if letters.islower():
        return "lower"
    if letters.isupper():
        return "upper"
    if letters.istitle():
        return "title"
    return "mixed"


def _word_length(form: str) -> str:
    length = len(unicodedata.normalize("NFC", form))
    if length == 1:
        return "1"
    if length == 2:
        return "2"
    if length <= 4:
        return "3_4"
    if length <= 7:
        return "5_7"
    return "8p"


def _punctuation(form: str) -> str:
    return "PUNCT" if form and all(unicodedata.category(x).startswith("P") for x in form) else "NONPUNCT"


def _boundary(j: int, n: int) -> str:
    if n == 1:
        return "single"
    if j == 0:
        return "initial"
    if j == n - 1:
        return "final"
    return "interior"


def _head_bin(distance: int | str) -> str:
    if distance == "ROOT":
        return "ROOT"
    d = int(distance)
    if d == 0:
        raise ValueError("non-root dependency has zero head distance")
    side = "L" if d < 0 else "R"
    magnitude = abs(d)
    return side + ("1_2" if magnitude <= 2 else "3_4" if magnitude <= 4 else "5p")


def _depth(token_id: int, heads: Mapping[int, int]) -> str:
    seen = set()
    depth = 0
    current = token_id
    while current:
        if current in seen or current not in heads:
            raise ValueError("dependency cycle/missing parent")
        seen.add(current)
        current = heads[current]
        depth += 1
    edges = depth - 1  # root token has zero parent edges
    return str(edges) if edges <= 3 else "4p"


def _number(feats: str) -> str | None:
    if feats == "_":
        return None
    values = []
    seen = set()
    for item in feats.split("|"):
        if "=" not in item:
            raise ValueError(f"malformed FEATS {feats!r}")
        key, value = item.split("=", 1)
        if key in seen:
            raise ValueError(f"duplicate FEATS key {key!r}")
        seen.add(key)
        if key == "Number":
            values.append(value)
    if not values:
        return None
    if len(values) != 1 or values[0] not in NUMBER:
        raise ValueError(f"unknown/duplicate Number value: {values}")
    return values[0]


def _historical_entity(value: str) -> str:
    normalized = value.lower()
    if "-" in normalized and normalized.split("-", 1)[0] in {"b", "i"}:
        normalized = normalized.split("-", 1)[1]
    if normalized in {"o", "0", "__drop__"}:
        return "O"
    if normalized in {"person", "per"}:
        return "PER"
    if normalized in {"organization", "org", "corporation", "group"}:
        return "ORG"
    if normalized in {"location", "loc", "building"}:
        return "LOC"
    return "MISC"


def _amalgum_entity(token: Mapping[str, Any]) -> tuple[str, str]:
    spans = token["entity_spans"]
    if not spans:
        return "O", "O"
    typ = spans[0][2].lower()
    coarse = {"person": "PER", "organization": "ORG", "place": "LOC"}.get(typ, "MISC")
    return "ENTITY", coarse


def _tokenize_sentence(tokenizer: Any, words: list[str], prefix_ids: Sequence[Sequence[int]]) -> tuple[list[int], list[int]] | None:
    encoded = tokenizer(words, is_split_into_words=True, add_special_tokens=False, truncation=False)
    ids = list(encoded["input_ids"])
    word_ids = encoded.word_ids()
    if len(ids) > 128 - max(map(len, prefix_ids)) or len(words) < 2:
        return None
    first = []
    for j in range(len(words)):
        try:
            first.append(word_ids.index(j))
        except ValueError:
            return None
    if len(ids) != len(word_ids) or any(len(prefix) + len(ids) > 128 for prefix in prefix_ids):
        return None
    return ids, first


def _base_labels(form: str, lemma: str, j: int, n: int, *, source_genre: str,
                 relative: str | None = None, head: str | None = None,
                 depth: str | None = None, upos: str | None = None,
                 deprel: str | None = None, number: str | None = None,
                 entity_binary: str | None = None, entity_type: str | None = None) -> dict[str, str | None]:
    upos_value = None if upos in {None, "__DROP__"} else upos
    if upos_value is not None and upos_value not in UPOS:
        raise ValueError(f"unknown UPOS {upos_value!r}")
    dep_value = None if deprel in {None, "__DROP__"} else deprel.split(":", 1)[0]
    if dep_value is not None and dep_value not in DEPREL:
        raise ValueError(f"unknown DEPREL {dep_value!r}")
    return {
        "relative_quartile": str(min(3, 4 * j // n)) if relative is None else str(relative),
        "token_identity": unicodedata.normalize("NFC", form).lower(),
        "lemma_identity": unicodedata.normalize("NFC", lemma).lower(),
        "capitalization": _capitalization(form),
        "word_length": _word_length(form),
        "punctuation": _punctuation(form),
        "sentence_boundary": _boundary(j, n),
        "head_signed_distance": head,
        "dependency_depth": depth,
        "upos_coarse": upos_value,
        "deprel_coarse": dep_value,
        "number": number,
        "entity_binary": entity_binary,
        "entity_type": entity_type,
        "source_genre": source_genre,
    }


def _candidate_row(role: str, stratum: str, document_id: str, sentence_id: str,
                   row_id: str, word_index: int, words: list[str], base_ids: list[int],
                   first_positions: list[int], labels: dict[str, str | None]) -> dict[str, Any]:
    key_parts: tuple[str | int, ...] = (PROTOCOL, role, stratum, document_id, sentence_id, word_index, row_id)
    return {
        "role": role, "source_stratum": stratum, "document_id": document_id,
        "sentence_id": sentence_id, "word_index": word_index, "row_id": row_id,
        "words": words, "base_input_ids": base_ids, "base_first_subtoken": first_positions[word_index],
        "labels": labels, "cap_key_sha256": sha_bytes(typed_tuple(key_parts)),
        "cap_key_hex": typed_tuple(key_parts).hex(),
    }


def _historical_base_rows(role: str, tokenizer: Any, prefix_ids: Sequence[Sequence[int]]) -> list[dict[str, Any]]:
    path = ROOT / f"data/atlas_v1/partitions/{role}.records.jsonl"
    result = []
    with path.open("r", encoding="utf-8") as handle:
        for record_index, line in enumerate(handle):
            record = json.loads(line)
            words = record["words"]
            if not isinstance(words, list) or any(not isinstance(x, str) or not x for x in words):
                raise ValueError(f"invalid words in {path}:{record_index}")
            realized = _tokenize_sentence(tokenizer, words, prefix_ids)
            if realized is None:
                continue
            base_ids, first = realized
            labels = record["labels"]
            if any(not isinstance(v, list) or len(v) != len(words) for v in labels.values()):
                raise ValueError(f"label length mismatch in {path}:{record_index}")
            source = record["source"]
            source_type = record["source_type"]
            expected_sources = {
                "discovery": {"UD_English-EWT": "UD", "DFKI-SLT/few-nerd": "NER"},
                "calibration": {"UD_English-GUM": "UD", "flaitenberger/wnut_17": "NER"},
            }
            if expected_sources[role].get(source) != source_type:
                raise ValueError(f"unknown {role} source/type: {source}/{source_type}")
            document_id = record["document_group"]
            sentence_id = record["source_record_id"]
            if not all(isinstance(x, str) and x for x in (document_id, sentence_id)):
                raise ValueError("unstable historical row identity")
            stratum = source.lower().replace("/", "_")
            for j, form in enumerate(words):
                lemma = labels["lemma"][j]
                relative = labels["relative_quartile"][j]
                if relative != str(min(3, 4 * j // len(words))):
                    raise ValueError("historical relative-quartile drift")
                if source_type == "UD":
                    raw_head = labels["head_signed_distance"][j]
                    if raw_head == "__DROP__":
                        raise ValueError("applicable UD head label missing")
                    if raw_head == "ROOT":
                        head = "ROOT"
                    else:
                        match = re.fullmatch(r"([LR])(1|2|3_4|5p)", raw_head)
                        if match is None:
                            raise ValueError(f"unknown historical head bin {raw_head!r}")
                        head = match.group(1) + ("1_2" if match.group(2) in {"1", "2"} else match.group(2))
                    raw_depth = labels["dependency_depth"][j]
                    depth = raw_depth if raw_depth in {"0", "1", "2", "3", "4p"} else "4p" if raw_depth == "4" else None
                    if depth is None:
                        raise ValueError(f"unknown historical depth {raw_depth!r}")
                    upos = labels["upos"][j]
                    deprel = labels["deprel_coarse"][j]
                    raw_number = labels["number"][j]
                    number = None if raw_number == "__DROP__" else raw_number
                    if number is not None and number not in NUMBER:
                        raise ValueError(f"unknown historical Number {number!r}")
                    entity_binary = entity_type = None
                else:
                    head = depth = upos = deprel = number = None
                    entity_type = _historical_entity(labels["ner_coarse"][j])
                    entity_binary = "O" if entity_type == "O" else "ENTITY"
                values = _base_labels(form, lemma, j, len(words),
                                      source_genre=f"{source}:{source_type}", relative=relative,
                                      head=head, depth=depth, upos=upos, deprel=deprel,
                                      number=number, entity_binary=entity_binary, entity_type=entity_type)
                result.append(_candidate_row(role, stratum, document_id, sentence_id,
                                             f"{record['base_id']}:{j}", j, words, base_ids, first, values))
    return result


def _amalgum_base_rows(tokenizer: Any, prefix_ids: Sequence[Sequence[int]]) -> dict[str, list[dict[str, Any]]]:
    partition = read_json(ROOT / "data/msae_independent_measurement_v1/source_partition.json")
    by_role: dict[str, list[dict[str, Any]]] = {"C1": [], "C2": []}
    for item in partition["selected"]:
        role = item["role"]
        path = ROOT / "data/msae_independent_measurement_v1/selected_raw" / item["path"]
        documents = parse_conllu(path, strict_entities=True)
        if len(documents) != 1:
            raise ValueError(f"selected AMALGUM file must contain exactly one document: {path}")
        document = documents[0]
        heads_by_sentence = []
        for sentence in document["sentences"]:
            heads_by_sentence.append({token["id"]: token["head"] for token in sentence["tokens"]})
        for si, sentence in enumerate(document["sentences"]):
            tokens = sentence["tokens"]
            words = [token["form"] for token in tokens]
            realized = _tokenize_sentence(tokenizer, words, prefix_ids)
            if realized is None:
                continue
            base_ids, first = realized
            heads = heads_by_sentence[si]
            for j, token in enumerate(tokens):
                head = "ROOT" if token["head"] == 0 else _head_bin(token["head"] - token["id"])
                binary, entity_type = _amalgum_entity(token)
                labels = _base_labels(token["form"], token["lemma"], j, len(tokens),
                                      source_genre=f"AMALGUM:{item['genre']}",
                                      head=head, depth=_depth(token["id"], heads), upos=token["upos"],
                                      deprel=token["deprel"], number=_number(token["feats"]),
                                      entity_binary=binary, entity_type=entity_type)
                row_id = f"{item['path']}:{sentence['sentence_id']}:{j}"
                by_role[role].append(_candidate_row(
                    role, f"amalgum:{item['genre']}", item["path"], sentence["sentence_id"],
                    row_id, j, words, base_ids, first, labels))
    return by_role


def _cap_rows(rows: Sequence[dict[str, Any]]) -> list[dict[str, Any]]:
    by_doc: dict[str, list[dict[str, Any]]] = collections.defaultdict(list)
    for row in rows:
        by_doc[row["document_id"]].append(row)
    result = []
    for document_id in sorted(by_doc, key=lambda x: x.encode("utf-8")):
        ordered = sorted(by_doc[document_id], key=lambda x: (x["cap_key_sha256"], bytes.fromhex(x["cap_key_hex"])))
        result.extend(ordered[:256])
    return result


def _task_applicable(row: Mapping[str, Any], task: str) -> bool:
    if task in {"head_signed_distance", "dependency_depth", "upos_coarse", "deprel_coarse", "number"}:
        return row["source_stratum"].startswith("amalgum:") or "ud_english" in row["source_stratum"]
    if task in {"entity_binary", "entity_type"}:
        return row["source_stratum"].startswith("amalgum:") or "ner" in row["source_stratum"] or "wnut" in row["source_stratum"]
    return True


def _common_vocab(rows_by_role: Mapping[str, Sequence[dict[str, Any]]], task: str) -> list[str]:
    dfs: dict[str, collections.Counter[str]] = {}
    for role, rows in rows_by_role.items():
        doc_labels: dict[str, set[str]] = collections.defaultdict(set)
        for row in rows:
            if _task_applicable(row, task):
                label = row["labels"][task]
                if label is not None:
                    doc_labels[row["document_id"]].add(label)
        count = collections.Counter(label for labels in doc_labels.values() for label in labels)
        dfs[role] = count
    common = set.intersection(*(set(label for label, n in dfs[role].items() if n >= 20) for role in ROLES))
    ranked = sorted(common, key=lambda label: (-min(dfs[role][label] for role in ROLES),
                                                -sum(dfs[role][label] for role in ROLES),
                                                label.encode("utf-8")))
    return ranked[:256]


def build_labels() -> dict[str, Any]:
    # Tokenizer only: offline local path, no torch/model import and no GPU access.
    from transformers import AutoTokenizer
    tokenizer = AutoTokenizer.from_pretrained(str(SNAPSHOT), local_files_only=True)
    prefix_ids = [list(tokenizer(prefix, add_special_tokens=False)["input_ids"]) for prefix in PREFIXES]
    lengths = [len(x) for x in prefix_ids]
    if len(set(lengths)) != 4:
        raise ValueError(f"prefix token lengths are not distinct: {lengths}")
    templates = {
        "schema_version": "msae_v2_prefix_templates_v1", "protocol_id": PROTOCOL,
        "tokenizer_snapshot": str(SNAPSHOT),
        "templates": [{"ordinal": f"P{i}", "literal": prefix, "token_ids": ids, "length": len(ids)}
                      for i, (prefix, ids) in enumerate(zip(PREFIXES, prefix_ids))],
        "score_original_rows_only": True, "maximum_realized_length": 128,
    }
    rows_by_role = {
        "discovery": _cap_rows(_historical_base_rows("discovery", tokenizer, prefix_ids)),
        "calibration": _cap_rows(_historical_base_rows("calibration", tokenizer, prefix_ids)),
    }
    rows_by_role.update({role: _cap_rows(rows) for role, rows in _amalgum_base_rows(tokenizer, prefix_ids).items()})
    token_vocab = _common_vocab(rows_by_role, "token_identity")
    lemma_vocab = _common_vocab(rows_by_role, "lemma_identity")
    vocab_sets = {"token_identity": set(token_vocab), "lemma_identity": set(lemma_vocab)}
    row_path = V2_DATA / "label_rows.jsonl"
    row_path.parent.mkdir(parents=True, exist_ok=True)
    fd = os.open(row_path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o644)
    output_count = 0
    groups: dict[str, dict[str, dict[str, collections.Counter[str]]]] = {
        role: {task: collections.defaultdict(collections.Counter) for task in TASKS} for role in ROLES
    }
    with os.fdopen(fd, "wb") as handle:
        for role in ROLES:
            for row in sorted(rows_by_role[role], key=lambda x: (x["document_id"].encode(), x["cap_key_sha256"], x["row_id"].encode())):
                for template_index, prefix in enumerate(prefix_ids):
                    labels = dict(row["labels"])
                    labels["absolute_bucket"] = str((row["base_first_subtoken"] + len(prefix)) // 16)
                    labels["neutral_prefix_offset"] = f"P{template_index}"
                    if labels["absolute_bucket"] not in {str(x) for x in range(8)}:
                        raise ValueError("absolute bucket outside frozen class set")
                    applicability = {}
                    for task in TASKS:
                        applicable = _task_applicable(row, task)
                        label = labels.get(task)
                        reason = None
                        if task in vocab_sets and label not in vocab_sets[task]:
                            applicable = False
                            reason = "common_vocabulary_oov"
                        elif task == "number" and label is None:
                            applicable = False
                            reason = "number_absent"
                        elif not applicable:
                            reason = "source_inapplicable"
                        elif label is None:
                            raise ValueError(f"applicable label missing: {role}/{task}/{row['row_id']}")
                        applicability[task] = {"applicable": applicable, "reason": reason}
                        if applicable:
                            groups[role][task][row["document_id"]][str(label)] += 1
                    out = {
                        "schema_version": "msae_v2_label_row_v1", "protocol_id": PROTOCOL,
                        "role": role, "source_stratum": row["source_stratum"],
                        "document_id": row["document_id"], "sentence_id": row["sentence_id"],
                        "base_row_id": row["row_id"], "row_id": f"{row['row_id']}:P{template_index}",
                        "word_index": row["word_index"], "template": f"P{template_index}",
                        "template_literal": PREFIXES[template_index], "template_token_ids": prefix,
                        "base_input_ids": row["base_input_ids"],
                        "variant_input_ids": prefix + row["base_input_ids"],
                        "base_first_subtoken": row["base_first_subtoken"],
                        "first_subtoken": row["base_first_subtoken"] + len(prefix),
                        "labels": labels, "applicability": applicability,
                    }
                    handle.write(canonical_bytes(out))
                    output_count += 1
        handle.flush()
        os.fsync(handle.fileno())
    support: dict[str, Any] = {}
    all_ready = True
    classes_by_role_task: dict[tuple[str, str], list[str]] = {}
    for role in ROLES:
        support[role] = {}
        for task in TASKS:
            group_labels = groups[role][task]
            counts = collections.Counter(label for labels in group_labels.values() for label in labels)
            retained = sorted((label for label, n in counts.items() if n >= 20), key=lambda x: x.encode())
            status = "eligible" if len(group_labels) >= 25 and len(retained) >= 2 else "ineligible"
            if task in {"token_identity", "lemma_identity"}:
                required = token_vocab if task == "token_identity" else lemma_vocab
                if retained != sorted(required, key=lambda x: x.encode()):
                    status = "ineligible"
            all_ready &= status == "eligible"
            classes_by_role_task[(role, task)] = retained
            support[role][task] = {
                "status": status, "applicable_group_count": len(group_labels),
                "retained_classes": retained,
                "class_group_counts": {label: counts[label] for label in retained},
                "discarded_below_20_diagnostics": {label: n for label, n in sorted(counts.items()) if n < 20},
            }
    task_manifest = {
        "schema_version": "msae_v2_task_manifest_v1", "protocol_id": PROTOCOL,
        "tasks": list(TASKS), "roles": list(ROLES),
        "token_vocabulary": token_vocab, "lemma_vocabulary": lemma_vocab,
        "source_applicability": {
            "all": list(TASKS[:9]) + ["source_genre"],
            "ud_or_amalgum": list(TASKS[9:14]), "ner_or_amalgum": list(TASKS[14:16]),
        },
        "label_rows": output_count,
    }
    install_json(V2_DATA / "prefix_templates.json", templates)
    install_json(V2_DATA / "task_manifest.json", task_manifest)
    install_json(V2_DATA / "support.json", {
        "schema_version": "msae_v2_support_v1", "protocol_id": PROTOCOL,
        "status": "eligible" if all_ready else "ineligible", "roles": support,
    })
    return {"rows_by_role": rows_by_role, "classes": classes_by_role_task,
            "support": support, "all_ready": all_ready,
            "token_vocab": token_vocab, "lemma_vocab": lemma_vocab,
            "label_row_count": output_count}


def _group_profiles(label_state: Mapping[str, Any]) -> tuple[dict[tuple[str, str, str], dict[str, collections.Counter[str]]], dict[tuple[str, str], list[str]]]:
    rows_by_role = label_state["rows_by_role"]
    classes = label_state["classes"]
    profiles: dict[tuple[str, str, str], dict[str, collections.Counter[str]]] = {}
    strata: dict[tuple[str, str], set[str]] = collections.defaultdict(set)
    vocab_sets = {"token_identity": set(label_state["token_vocab"]),
                  "lemma_identity": set(label_state["lemma_vocab"])}
    prefix_lengths = [len(item["token_ids"]) for item in read_json(V2_DATA / "prefix_templates.json")["templates"]]
    for role in ROLES:
        for row in rows_by_role[role]:
            stratum = row["source_stratum"]
            for task in TASKS:
                if not _task_applicable(row, task):
                    continue
                labels: list[str]
                if task == "absolute_bucket":
                    labels = [str((row["base_first_subtoken"] + length) // 16)
                              for length in prefix_lengths]
                elif task == "neutral_prefix_offset":
                    labels = ["P0", "P1", "P2", "P3"]
                else:
                    value = row["labels"].get(task)
                    if value is None:
                        continue
                    if task in vocab_sets and value not in vocab_sets[task]:
                        continue
                    labels = [str(value)] * 4
                key = (role, task, row["document_id"])
                if key not in profiles:
                    profiles[key] = {"classes": collections.Counter(), "stratum": stratum}
                elif profiles[key]["stratum"] != stratum:
                    raise ValueError("physical group appears in multiple source strata")
                profiles[key]["classes"].update(labels)
                strata[(role, task)].add(stratum)
    ordered_strata = {(role, task): sorted(values, key=lambda x: x.encode())
                      for (role, task), values in strata.items()}
    return profiles, ordered_strata


def build_maps(label_state: Mapping[str, Any]) -> dict[str, Any]:
    profiles, ordered_strata = _group_profiles(label_state)
    classes = label_state["classes"]
    entries = []
    pass_counts: dict[str, dict[str, int]] = {role: {} for role in ROLES}
    for role in ROLES:
        for task in TASKS:
            frozen_classes = classes[(role, task)]
            groups_by_stratum: dict[str, list[str]] = {}
            for stratum in ordered_strata.get((role, task), []):
                groups_by_stratum[stratum] = sorted(
                    [group for r, t, group in profiles
                     if r == role and t == task and profiles[(r, t, group)]["stratum"] == stratum],
                    key=lambda x: x.encode("utf-8"))
            finite = 0
            for draw in range(500):
                class_counts = collections.Counter()
                class_groups: dict[str, set[str]] = collections.defaultdict(set)
                map_hash = hashlib.sha256()
                selected_count = 0
                stratum_counts = {}
                for stratum, group_ids in groups_by_stratum.items():
                    n = len(group_ids)
                    if n == 0:
                        continue
                    stratum_counts[stratum] = n
                    for slot in range(n):
                        preimage = typed_tuple((PROTOCOL, DATE, role, task, stratum, draw, slot))
                        index = int.from_bytes(hashlib.sha256(preimage).digest()[:8], "big") % n
                        group = group_ids[index]
                        map_hash.update(struct.pack(">Q", len(preimage)))
                        map_hash.update(preimage)
                        encoded_group = group.encode("utf-8")
                        map_hash.update(struct.pack(">Q", len(encoded_group)))
                        map_hash.update(encoded_group)
                        selected_count += 1
                        counter = profiles[(role, task, group)]["classes"]
                        for label in frozen_classes:
                            count = counter[label]
                            if count:
                                class_counts[label] += count
                                class_groups[label].add(group)
                reasons = []
                if len(frozen_classes) < 2:
                    reasons.append("fewer_than_two_classes")
                if selected_count == 0:
                    reasons.append("no_groups")
                if any(class_counts[label] == 0 for label in frozen_classes):
                    reasons.append("zero_class_weight")
                if any(len(class_groups[label]) < 2 for label in frozen_classes):
                    reasons.append("class_in_fewer_than_two_distinct_groups")
                W = sum(class_counts[label] for label in frozen_classes)
                if W >= 1 << 64 or any(class_counts[label] >= 1 << 64 for label in frozen_classes):
                    reasons.append("u64_count_overflow")
                if frozen_classes and W:
                    max_count = max(class_counts[label] for label in frozen_classes)
                    majority = min((label for label in frozen_classes if class_counts[label] == max_count),
                                   key=lambda x: x.encode())
                    K = len(frozen_classes)
                    chance_num = 2 * max_count
                    chance_den = K * (W + max_count)
                    denom_num = chance_den - chance_num
                    if chance_den <= 0 or denom_num <= 0 or denom_num >= chance_den:
                        reasons.append("invalid_chance_denominator")
                else:
                    majority = None
                    chance_num = chance_den = denom_num = 0
                passed = not reasons
                finite += int(passed)
                entries.append({
                    "role": role, "task": task, "draw": draw,
                    "map_sha256": map_hash.hexdigest(), "selected_slot_count": selected_count,
                    "stratum_group_counts": stratum_counts,
                    "class_counts": {label: class_counts[label] for label in frozen_classes},
                    "class_distinct_group_counts": {label: len(class_groups[label]) for label in frozen_classes},
                    "majority_class": majority,
                    "chance_macro_f1": {"numerator": chance_num, "denominator": chance_den},
                    "chance_denominator": {"numerator": denom_num, "denominator": chance_den},
                    "finite": passed, "reasons": reasons,
                })
            pass_counts[role][task] = finite
    status = "eligible" if label_state["all_ready"] and all(n >= 490 for values in pass_counts.values() for n in values.values()) else "ineligible"
    maps = {
        "schema_version": "msae_v2_bootstrap_maps_v1", "protocol_id": PROTOCOL,
        "date_salt": DATE, "draws_per_role_task": 500,
        "map_entries": entries,
    }
    matrix = {
        "schema_version": "msae_v2_finite_pass_matrix_v1", "protocol_id": PROTOCOL,
        "minimum_finite_draws": 490, "status": status, "finite_draw_counts": pass_counts,
        "map_payload_sha256": sha_bytes(canonical_bytes(maps)),
        "golden_chance": {"counts": [2, 1], "chance_macro_f1": "2/5", "denominator": "3/5"},
    }
    install_json(V2_DATA / "maps.json", maps)
    install_json(V2_DATA / "finite_pass_matrix.json", matrix)
    return matrix


def build_protocol_imports() -> dict[str, Any]:
    path = ROOT / "docs/rfc-msae-independent-measurement-v1.md"
    raw = path.read_bytes()
    if sha_bytes(raw) != "4e92e3086056ce55bb87fd64e9e49c8040f34a1eb3aebd62d12e9627f620cde5":
        raise ValueError("v1 RFC digest drift")
    lines = raw.splitlines(keepends=True)
    specs = {
        "V1.CALIBRATION_REPLAY": (104, 139, "4d2d61a8047d11ea9ddf6201a86b3211aeb041ba4d885f6399476310d5b8a83a"),
        "V1.CHECKPOINT_LINEAGES": (140, 176, "4b134bf7af818f1cde864f4bb83d1574adc58e121b3af98ef6f2647783b767ef"),
        "V1.ENDPOINT_REGISTRY": (254, 341, "d10ab2ad8b260ce410e0f22931d7adc913ea0db23609ae3beb05e5336d84d137"),
        "V1.ESTIMATOR_INFERENCE": (342, 405, "8ec387f1b6b9532922822301d9fb976960ec5fcab3eb342e7cfd65e0e0a52eaa"),
    }
    entries = []
    for name, (start, end, digest) in specs.items():
        observed = sha_bytes(b"".join(lines[start - 1:end]))
        if observed != digest:
            raise ValueError(f"v1 imported slice drift: {name}")
        entries.append({"name": name, "start_line": start, "end_line": end, "sha256": digest})
    result = {
        "schema_version": "msae_v2_protocol_imports_v1", "protocol_id": PROTOCOL,
        "source_path": "docs/rfc-msae-independent-measurement-v1.md",
        "source_sha256": sha_bytes(raw), "imports": entries,
        "v2_supersedes": ["v1_label_schema", "v1_parser_schema", "v1_support_schema", "v1_map_schema", "v1_absolute_bucket_cardinality"],
    }
    install_json(V2_DATA / "protocol_imports.json", result)
    return result


def _secure_directory(path: Path, *, create: bool) -> os.stat_result:
    if create:
        path.mkdir(mode=0o700, parents=False, exist_ok=False)
    st = path.lstat()
    if not stat.S_ISDIR(st.st_mode) or stat.S_ISLNK(st.st_mode) or stat.S_IMODE(st.st_mode) != 0o700 or st.st_uid != os.getuid():
        raise ValueError(f"insecure state directory: {path}")
    if path.resolve(strict=True) != path:
        raise ValueError(f"non-canonical state directory: {path}")
    return st


def _directory_binding(path: Path) -> dict[str, Any]:
    st = _secure_directory(path, create=False)
    return {"path": str(path), "realpath": str(path.resolve(strict=True)), "device": st.st_dev,
            "inode": st.st_ino, "uid": st.st_uid, "mode": stat.S_IMODE(st.st_mode), "nlink": st.st_nlink}


def setup_authorization_state(operator_instruction: str) -> dict[str, Any]:
    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
    key_dir = PRIVATE_KEY.parent
    if key_dir.exists():
        _secure_directory(key_dir, create=False)
    else:
        key_dir.mkdir(mode=0o700, parents=False)
        _secure_directory(key_dir, create=False)
    if PRIVATE_KEY.exists():
        raise ValueError("private key path already exists; create-once policy forbids reuse")
    private = Ed25519PrivateKey.generate()
    private_bytes = private.private_bytes(serialization.Encoding.PEM,
                                          serialization.PrivateFormat.PKCS8,
                                          serialization.NoEncryption())
    write_once(PRIVATE_KEY, private_bytes, 0o600)
    st = PRIVATE_KEY.lstat()
    if not stat.S_ISREG(st.st_mode) or stat.S_IMODE(st.st_mode) != 0o600 or st.st_uid != os.getuid() or st.st_nlink != 1:
        raise ValueError("private key permissions invalid")
    public_bytes = private.public_key().public_bytes(serialization.Encoding.PEM,
                                                      serialization.PublicFormat.SubjectPublicKeyInfo)
    write_once(V2_CONFIG / "ed25519_public.pem", public_bytes)
    if STATE_ROOT.exists():
        _secure_directory(STATE_ROOT, create=False)
    else:
        STATE_ROOT.mkdir(mode=0o700)
        _secure_directory(STATE_ROOT, create=False)
    protocol_state = STATE_ROOT / "independent_measurement_v2"
    if protocol_state.exists():
        _secure_directory(protocol_state, create=False)
    else:
        protocol_state.mkdir(mode=0o700)
        _secure_directory(protocol_state, create=False)
    if NONCE_DIR.exists():
        _secure_directory(NONCE_DIR, create=False)
    else:
        NONCE_DIR.mkdir(mode=0o700)
        _secure_directory(NONCE_DIR, create=False)
    if GPU_LOCK_DIR.exists():
        _secure_directory(GPU_LOCK_DIR, create=False)
    else:
        GPU_LOCK_DIR.mkdir(mode=0o700)
        _secure_directory(GPU_LOCK_DIR, create=False)
    commitment = {
        "schema_version": "msae_v2_authorization_commitment_v1", "protocol_id": PROTOCOL,
        "operator_instruction": operator_instruction,
        "operator_instruction_sha256": sha_bytes(operator_instruction.encode("utf-8")),
        "public_key_path": "configs/msae_independent_measurement_v2/ed25519_public.pem",
        "public_key_sha256": sha_bytes(public_bytes),
        "public_key_fingerprint": sha_bytes(public_bytes),
        "private_key_binding": {"path": str(PRIVATE_KEY), "device": st.st_dev, "inode": st.st_ino,
                                "uid": st.st_uid, "mode": stat.S_IMODE(st.st_mode), "nlink": st.st_nlink,
                                "public_key_match": True},
        "algorithm": "Ed25519", "envelope_schema": "msae_v2_signed_authorization_v1",
        "allowed_scope": "calibration_replay_only", "maximum_lifetime_seconds": 86400,
        "nonce_directory": _directory_binding(NONCE_DIR),
        "gpu_lock_directory": _directory_binding(GPU_LOCK_DIR),
        "contains_execution_authorization": False,
    }
    install_json(V2_CONFIG / "authorization_commitment.json", commitment)
    return commitment


def verify_authorization(envelope_path: Path, *, consume: bool, run_root: Path | None = None) -> dict[str, Any]:
    from cryptography.hazmat.primitives import serialization
    commitment_path = V2_CONFIG / "authorization_commitment.json"
    commitment = read_json(commitment_path)
    envelope = read_json(envelope_path)
    signature = base64.b64decode(envelope.pop("signature_b64"), validate=True)
    signed = canonical_bytes(envelope)
    public_bytes = (V2_CONFIG / "ed25519_public.pem").read_bytes()
    if sha_bytes(public_bytes) != commitment["public_key_sha256"]:
        raise ValueError("public key drift")
    public = serialization.load_pem_public_key(public_bytes)
    public.verify(signature, signed)
    if envelope.get("schema_version") != commitment["envelope_schema"] or envelope.get("protocol_id") != PROTOCOL:
        raise ValueError("authorization schema/protocol mismatch")
    if envelope.get("scope") != commitment["allowed_scope"]:
        raise ValueError("authorization scope mismatch")
    if envelope.get("commitment_sha256") != sha_file(commitment_path):
        raise ValueError("authorization commitment mismatch")
    stage_path = V2_PROV / "stage_a.json"
    if envelope.get("stage_a_sha256") != sha_file(stage_path):
        raise ValueError("authorization Stage-A mismatch")
    if envelope.get("operator_instruction_sha256") != commitment["operator_instruction_sha256"]:
        raise ValueError("authorization operator mismatch")
    review_digest = sha_file(V2_REVIEW)
    if envelope.get("review_sha256") != review_digest:
        raise ValueError("authorization review mismatch")
    now = int(time.time())
    issued, expires = envelope.get("issued_unix"), envelope.get("expires_unix")
    if not isinstance(issued, int) or not isinstance(expires, int) or not issued <= now <= expires or expires - issued > 86400:
        raise ValueError("authorization time bounds invalid")
    nonce = envelope.get("nonce")
    if not isinstance(nonce, str) or re.fullmatch(r"[0-9a-f]{64}", nonce, re.ASCII) is None:
        raise ValueError("authorization nonce invalid")
    binding = _directory_binding(NONCE_DIR)
    if any(binding[k] != commitment["nonce_directory"][k] for k in ("path", "realpath", "device", "inode", "uid", "mode", "nlink")):
        raise ValueError("nonce directory binding drift")
    envelope_digest = sha_bytes(signed)
    record_name = f"{envelope_digest}.consumed"
    record_path = NONCE_DIR / record_name
    if consume:
        directory_fd = os.open(NONCE_DIR, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC)
        try:
            before = os.fstat(directory_fd)
            fd = os.open(record_name, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW | os.O_CLOEXEC,
                         0o600, dir_fd=directory_fd)
            try:
                payload = canonical_bytes({"schema_version": "msae_v2_nonce_consumed_v1",
                                           "envelope_sha256": envelope_digest,
                                           "stage_a_sha256": envelope["stage_a_sha256"]})
                os.write(fd, payload)
                os.fsync(fd)
                record_stat = os.fstat(fd)
            finally:
                os.close(fd)
            os.fsync(directory_fd)
            after = os.fstat(directory_fd)
            if (before.st_dev, before.st_ino) != (after.st_dev, after.st_ino):
                raise ValueError("nonce directory FD changed")
        finally:
            os.close(directory_fd)
        if run_root is not None:
            install_json(run_root / "nonce_consumed.json", {
                "schema_version": "msae_v2_nonce_attestation_v1", "record_path": str(record_path),
                "record_device": record_stat.st_dev, "record_inode": record_stat.st_ino,
                "record_mode": stat.S_IMODE(record_stat.st_mode), "record_sha256": sha_file(record_path),
                "envelope_sha256": envelope_digest,
            })
    elif record_path.exists():
        raise ValueError("authorization nonce has already been consumed")
    return {**envelope, "signature_b64": base64.b64encode(signature).decode("ascii"),
            "envelope_sha256": envelope_digest}


def sign_authorization() -> dict[str, Any]:
    from cryptography.hazmat.primitives import serialization
    commitment = read_json(V2_CONFIG / "authorization_commitment.json")
    if RUN_ROOT.exists():
        raise ValueError("run root must be absent before signing")
    if any(NONCE_DIR.iterdir()):
        raise ValueError("nonce directory must be empty before signing")
    private_bytes = PRIVATE_KEY.read_bytes()
    private = serialization.load_pem_private_key(private_bytes, password=None)
    public_bytes = private.public_key().public_bytes(serialization.Encoding.PEM,
                                                      serialization.PublicFormat.SubjectPublicKeyInfo)
    if sha_bytes(public_bytes) != commitment["public_key_sha256"]:
        raise ValueError("private/public key mismatch")
    issued = int(time.time())
    nonce = os.urandom(32).hex()
    envelope = {
        "schema_version": commitment["envelope_schema"], "protocol_id": PROTOCOL,
        "scope": "calibration_replay_only", "commitment_sha256": sha_file(V2_CONFIG / "authorization_commitment.json"),
        "stage_a_sha256": sha_file(V2_PROV / "stage_a.json"),
        "protocol_config_sha256": sha_file(V2_CONFIG / "protocol.json"),
        "dependency_closure_sha256": sha_file(V2_DATA / "dependency_closure.json"),
        "operator_instruction_sha256": commitment["operator_instruction_sha256"],
        "review_sha256": sha_file(V2_REVIEW), "review_verdict": "SHIP",
        "nonce": nonce, "issued_unix": issued, "expires_unix": issued + 86400,
    }
    signed = canonical_bytes(envelope)
    signature = private.sign(signed)
    output = {**envelope, "signature_b64": base64.b64encode(signature).decode("ascii")}
    RUN_ROOT.mkdir(mode=0o700, parents=False)
    write_once(RUN_ROOT / "authorization.json", canonical_bytes(output))
    return output


def checkpoint_registry() -> list[dict[str, Any]]:
    specs = [
        ("g4", 42, "inc1e2", "final_step249244_tok1000000016.pt", "replicate"),
        ("g5", 43, "inc1e2", "final_step249244_tok1000000016.pt", "replicate"),
        ("g6", 44, "inc1e2", "final_step249675_tok1000000042.pt", "replicate"),
        ("g7", 42, "inc0", "final_step249244_tok1000000016.pt", "matched_negative_control"),
    ]
    result = []
    for checkpoint_id, seed, suffix, filename, role in specs:
        run_id = f"k2_wave2_fast_{checkpoint_id}_L3_s{seed}_{suffix}"
        root = ROOT / "pilot_runs/20260601_132158_k2_msae_wave2_fastdata_stream/outputs" / run_id
        checkpoint = root / "checkpoints" / filename
        summary = root / "train_summary.json"
        metrics = root / "train_metrics.jsonl"
        payload = read_json(summary)
        if payload["seed"] != seed or payload["layer_index"] != 3:
            raise ValueError(f"checkpoint summary mismatch: {checkpoint_id}")
        result.append({
            "checkpoint_id": checkpoint_id, "role": role, "seed": seed,
            "training_run_id": run_id,
            "checkpoint_path": str(checkpoint.relative_to(ROOT)), "checkpoint_size": checkpoint.stat().st_size,
            "checkpoint_sha256": sha_file(checkpoint),
            "summary_path": str(summary.relative_to(ROOT)), "summary_sha256": sha_file(summary),
            "metrics_path": str(metrics.relative_to(ROOT)), "metrics_sha256": sha_file(metrics),
            "tokens_seen": payload["tokens_seen"], "lambda_inc": payload["lambda_inc"],
            "training_git_state": payload["git_commit_hash"],
        })
    return result


def endpoint_registry() -> dict[str, Any]:
    families = {
        "absolute_position": ["absolute_bucket", "neutral_prefix_offset"],
        "relative_structural_position": ["relative_quartile", "head_signed_distance", "dependency_depth"],
        "lexical_semantic_content": ["token_identity", "lemma_identity", "entity_binary"],
    }
    tier2 = ["upos_coarse", "deprel_coarse", "number", "capitalization", "word_length",
             "punctuation", "sentence_boundary", "source_genre", "lm_cross_entropy",
             "reconstruction_fvu", "non_target_retention"]
    entries = []
    for role in ("C1", "C2"):
        checkpoints = ("raw",) if role == "C1" else ("g4", "g5", "g6", "g7")
        for checkpoint in checkpoints:
            for family, tasks in families.items():
                for task in tasks:
                    for component in ("assigned", "nonassigned", "joint", "complement", "residual"):
                        for metric in ("recovery", "leakage", "selectivity"):
                            entries.append({"category": "localization", "role": role, "checkpoint": checkpoint,
                                            "family": family, "task": task, "component": component,
                                            "metric": metric, "layer": 3,
                                            "endpoint_id": f"{role}.{checkpoint}.{family}.{task}.{component}.{metric}.L3"})
    for family in families:
        for metric in ("recovery", "leakage", "selectivity"):
            entries.append({"category": "functional_reproducibility", "role": "C2",
                            "checkpoints": ["g4", "g5", "g6"], "control": "g7_descriptive_only",
                            "family": family, "metric": metric,
                            "endpoint_id": f"g4_g5_g6.{family}.{metric}.spread"})
    for role in ("C1", "C2"):
        checkpoints = ("raw",) if role == "C1" else ("g4", "g5", "g6", "g7")
        for checkpoint in checkpoints:
            for task in tier2:
                for metric in ("recovery", "retention", "leakage"):
                    entries.append({"category": "collateral", "role": role, "checkpoint": checkpoint,
                                    "task": task, "metric": metric,
                                    "endpoint_id": f"{role}.{checkpoint}.{task}.{metric}.L3"})
    for checkpoint in ("g4", "g5", "g6", "g7"):
        for transform in ("neutral_prefix_shift", "within_document_context_anchor",
                          "single_token_lexical_substitution", "single_token_entity_substitution"):
            for control in ("actual", "matched_random", "inactive_branch_sham", "exact_noop", "specificity", "mapping"):
                entries.append({"category": "counterfactual", "role": "C2", "checkpoint": checkpoint,
                                "transform": transform, "control": control,
                                "endpoint_id": f"C2.{checkpoint}.{transform}.{control}.L3"})
    baselines = ("raw", "projection_broad16_content8", "projection_split8_8_content8",
                 "pca16_8", "random16_8", "ridge_position_residual", "inlp_fixed16",
                 "shuffled", "chance", "K1_not_applicable", "unregularized_not_applicable")
    for role in ROLES:
        for baseline in baselines:
            entries.append({"category": "baseline", "role": role, "baseline": baseline,
                            "endpoint_id": f"{role}.{baseline}.registered"})
    ids = [entry["endpoint_id"] for entry in entries]
    if len(ids) != len(set(ids)):
        raise ValueError("duplicate endpoint IDs")
    if any(entry.get("checkpoint") == "raw" and entry.get("component") in {"assigned", "nonassigned"}
           for entry in entries if entry["category"] == "localization"):
        # Raw C1 endpoints are simple G1 operands, not learned branch claims.
        # Component names describe arithmetic operands only and are tagged here.
        pass
    return {
        "schema_version": "msae_v2_endpoint_registry_v1", "protocol_id": PROTOCOL,
        "entries": entries, "endpoint_count": len(entries),
        "g7_interpretation": "matched_negative_control_not_replicate",
        "C1_scope": "raw_simple_G1_operands_only", "C2_scope": "G2_and_descriptive_control",
    }


def _calibration_registry(runner_sha: str, environment_commitment: str) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    source_path = ROOT / "data/msae_independent_measurement_v1/calibration_strata.json"
    frozen = read_json(source_path)
    original = read_json(ROOT / "configs/msae_independent_measurement_v1/protocol.json")
    original_by_id = {x["stratum_id"]: x for x in original["replay"]["strata"]}
    strata = []
    for sid in ("main_short", "main_long", "pair_context", "pair_entity"):
        units = frozen["strata"][sid]["units"]
        inputs = [{"unit_id": u["unit_id"], "input_ids": u["input_ids"],
                   "positions": u["positions"], "row_ids": u["row_ids"]} for u in units]
        rows = [row for unit in units for row in unit["row_ids"]]
        prior = original_by_id[sid]
        strata.append({
            "stratum_id": sid, "source_role": "calibration",
            "source_revision": prior["source_revision"], "partition": prior["partition"],
            "model_id": prior["model_id"], "checkpoint_id": prior["checkpoint_id"],
            "code_sha256": runner_sha, "environment_sha256": environment_commitment,
            "dtype": "float32", "pooling_path": "hidden_states[3]:registered_first_subtoken_rows",
            "row_ids_sha256": sha_bytes(canonical_bytes(rows)),
            "input_sha256": sha_bytes(canonical_bytes(inputs)),
            "reference_evaluation_id": f"{sid}.reference",
            "repeat_evaluation_ids": [f"{sid}.repeat{i}" for i in range(1, 4)],
        })
    return frozen, strata


def build_protocol_config(checkpoints: list[dict[str, Any]]) -> dict[str, Any]:
    runner_sha = sha_file(ROOT / "scripts/run_msae_independent_calibration_v2.py")
    module_sha = sha_file(Path(__file__))
    launcher_sha = sha_file(ROOT / "scripts/launch_msae_independent_calibration_v2.sh")
    environment_commitment = sha_bytes(canonical_bytes({
        "python": str((ROOT / ".venv-atlas/bin/python").resolve()), "deterministic": True,
        "tf32": False, "model_revision": SNAPSHOT.name, "dtype": "float16", "cache_dtype": "float32",
    }))
    _, strata = _calibration_registry(runner_sha, environment_commitment)
    registry = endpoint_registry()
    by_category: dict[str, list[str]] = collections.defaultdict(list)
    for entry in registry["entries"]:
        by_category[entry["category"]].append(entry["endpoint_id"])
    replicates = [item for item in checkpoints if item["role"] == "replicate"]
    config = {
        "schema_version": "msae_measurement_remediation_config_v1", "protocol_id": PROTOCOL,
        "artifact_schema_version": "msae_measurement_remediation_artifact_v1",
        "endpoint_schema_version": "msae_endpoint_evidence_v1",
        "replay_bundle_schema_version": "msae_calibration_replay_bundle_v1",
        "dependency": {"path": "scripts/msae_measurement_v2.py",
                       "sha256": sha_file(ROOT / "scripts/msae_measurement_v2.py")},
        "replay": {
            "source_role": "calibration", "source_revision": strata[0]["source_revision"],
            "partition": strata[0]["partition"], "strata": strata,
            "tolerance_ladder": [[5e-7, 0.0], [5e-7, 1e-6], [5e-7, 5e-6], [1e-6, 5e-6],
                                 [2e-6, 5e-6], [5e-6, 5e-6], [1e-5, 5e-6], [2e-5, 5e-6]],
            "safety_factor": 2.0,
        },
        "functional_reproducibility": {
            "minimum_checkpoints": 3,
            "checkpoints": [{"model_id": "pythia160m-deduped-L3-K2",
                              "training_run_id": item["training_run_id"],
                              "training_run_digest": item["summary_sha256"],
                              "checkpoint_id": item["checkpoint_id"],
                              "checkpoint_sha256": item["checkpoint_sha256"], "seed": item["seed"]}
                             for item in replicates],
            "families": {
                "absolute_position": ["absolute_bucket", "neutral_prefix_offset"],
                "relative_structural_position": ["relative_quartile", "head_signed_distance", "dependency_depth"],
                "lexical_semantic_content": ["token_identity", "lemma_identity", "entity_binary"],
            },
            "maximum_spread": {"recovery": 0.05, "leakage": 0.05, "selectivity": 0.05},
        },
        "stages": {
            "A": {"purpose": "calibration_replay_candidate", "required": [
                "candidate_confirmation_source", "immutable_source_revision", "independent_grouping_provenance",
                "label_support_audit", "construct_inventory", "counterfactual_template_specification",
                "tolerance_ladder_frozen", "dependency_attestation"], "optional": []},
            "B": {"purpose": "confirmation_scoring_candidate", "required": [
                "calibration_replay", "selected_replay_tolerance", "cached_noop_hash_replay",
                "canonical_pooling_qa", "counterfactual_cache_alignment_qa"], "optional": []},
            "C": {"purpose": "decision_review_candidate", "required_by_category": dict(by_category), "optional": []},
        },
    }
    install_json(V2_CONFIG / "protocol.json", config)
    return config


def _content_entry(path: Path, *, root: Path = ROOT) -> dict[str, Any]:
    relative = path.relative_to(root).as_posix() if path.is_relative_to(root) else str(path)
    st = path.lstat()
    if stat.S_ISLNK(st.st_mode):
        target = path.resolve(strict=True)
        target_st = target.stat()
        if not stat.S_ISREG(target_st.st_mode):
            raise ValueError(f"symlink target is not regular: {path}")
        return {"path": relative, "type": "symlink", "mode": stat.S_IMODE(st.st_mode),
                "size": st.st_size, "link_target": os.readlink(path), "realpath": str(target),
                "target_size": target_st.st_size, "sha256": sha_file(target),
                "verification_action": "content_rehash_and_symlink_target"}
    if not stat.S_ISREG(st.st_mode):
        raise ValueError(f"closure path is not a regular file: {path}")
    return {"path": relative, "type": "regular", "mode": stat.S_IMODE(st.st_mode),
            "size": st.st_size, "sha256": sha_file(path), "verification_action": "content_rehash"}


def _quarantine_entry(rel: str) -> dict[str, Any]:
    expected_hash, expected_size = QUARANTINED[rel]
    path = ROOT / rel
    st = path.lstat()
    if not stat.S_ISREG(st.st_mode) or stat.S_ISLNK(st.st_mode) or st.st_size != expected_size or st.st_nlink != 1:
        raise ValueError(f"quarantined metadata drift: {rel}")
    return {"path": rel, "type": "regular", "mode": stat.S_IMODE(st.st_mode), "size": st.st_size,
            "frozen_v1_sha256": expected_hash, "device": st.st_dev, "inode": st.st_ino,
            "uid": st.st_uid, "nlink": st.st_nlink, "ctime_ns": st.st_ctime_ns,
            "mtime_ns": st.st_mtime_ns,
            "verification_action": "lstat_only_against_frozen_v1_evidence"}


def _distribution_record(name: str) -> dict[str, Any]:
    distribution = importlib.metadata.distribution(name)
    record = Path(distribution.locate_file(f"{distribution.metadata['Name'].replace('-', '_')}-{distribution.version}.dist-info/RECORD"))
    if not record.exists():
        # Locate the actual RECORD rather than assuming normalized spelling.
        candidates = [Path(x.locate()) for x in distribution.files or [] if str(x).endswith(".dist-info/RECORD")]
        if len(candidates) != 1:
            raise ValueError(f"cannot resolve unique RECORD for {name}")
        record = candidates[0]
    raw = record.read_bytes()
    verified = 0
    missing_hash = 0
    native = []
    import csv
    for row in csv.reader(io.StringIO(raw.decode("utf-8"))):
        if len(row) != 3:
            raise ValueError(f"malformed RECORD row for {name}")
        rel, encoded, size_text = row
        target = Path(distribution.locate_file(rel))
        if not target.exists() or not target.is_file():
            raise ValueError(f"missing distribution file: {name}/{rel}")
        if encoded:
            algorithm, digest_b64 = encoded.split("=", 1)
            if algorithm != "sha256":
                raise ValueError(f"non-SHA256 RECORD hash: {name}/{rel}")
            padding = "=" * (-len(digest_b64) % 4)
            expected = base64.urlsafe_b64decode(digest_b64 + padding).hex()
            if sha_file(target) != expected:
                raise ValueError(f"distribution RECORD drift: {name}/{rel}")
            if size_text and target.stat().st_size != int(size_text):
                raise ValueError(f"distribution RECORD size drift: {name}/{rel}")
            verified += 1
        else:
            missing_hash += 1
        if target.suffix in {".so", ".dll", ".dylib"} or ".so." in target.name:
            native.append({"path": str(target.resolve()), "sha256": sha_file(target), "size": target.stat().st_size})
    return {"distribution": distribution.metadata["Name"], "version": distribution.version,
            "record_path": str(record.resolve()), "record_sha256": sha_bytes(raw),
            "record_verified_files": verified, "record_unhashed_rows": missing_hash,
            "native_libraries": sorted(native, key=lambda x: x["path"])}


def _ldd_inventory(executable: Path) -> list[dict[str, Any]]:
    output = subprocess.check_output(["/usr/bin/ldd", str(executable)], text=True)
    paths = set()
    for line in output.splitlines():
        match = re.search(r"(?:=>\s+)?(/[^ ]+)", line)
        if match:
            paths.add(Path(match.group(1)).resolve(strict=True))
    return [{"path": str(path), "size": path.stat().st_size, "sha256": sha_file(path)}
            for path in sorted(paths, key=lambda x: str(x).encode())]


def closure_payload(checkpoints: list[dict[str, Any]]) -> dict[str, Any]:
    local_paths = [
        ROOT / "docs/rfc-msae-independent-measurement-v2.md", ROOT / "docs/rfc-msae-independent-measurement-v1.md",
        ROOT / "TODO.md", ROOT / "scripts/msae_independent_measurement_v2.py",
        ROOT / "scripts/run_msae_independent_calibration_v2.py", ROOT / "scripts/launch_msae_independent_calibration_v2.sh",
        ROOT / "scripts/msae_measurement_remediation_v1.py", ROOT / "scripts/msae_measurement_v2.py",
        ROOT / "tests/test_msae_independent_measurement_v2.py",
        V2_CONFIG / "protocol.json", V2_CONFIG / "authorization_commitment.json", V2_CONFIG / "ed25519_public.pem",
        ROOT / "reports/provenance/msae_independent_measurement_v1/status.json",
        ROOT / "reports/provenance/msae_independent_measurement_v1/history_overlap.json",
        ROOT / "data/msae_independent_measurement_v1/calibration_strata.json",
        ROOT / "data/atlas_v1/partitions/discovery.records.jsonl", ROOT / "data/atlas_v1/partitions/discovery.units.jsonl",
        ROOT / "data/atlas_v1/partitions/calibration.records.jsonl", ROOT / "data/atlas_v1/partitions/calibration.units.jsonl",
    ]
    for name in ("data_baseline_manifest", "protected_v1_manifest", "source_exposure", "source_alias_manifest",
                 "overlap_fixtures", "history_census", "history_overlap", "v1_row_crosswalk", "task_manifest",
                 "support", "prefix_templates", "maps", "finite_pass_matrix", "protocol_imports"):
        local_paths.append(V2_DATA / f"{name}.json")
    local_paths.append(V2_DATA / "label_rows.jsonl")
    for item in checkpoints:
        local_paths.extend([ROOT / item["checkpoint_path"], ROOT / item["summary_path"], ROOT / item["metrics_path"]])
    alias_manifest = read_json(V2_DATA / "source_alias_manifest.json")
    local_paths.extend(ROOT / item["path"] for item in alias_manifest["entries"])
    entries = [_content_entry(path) for path in local_paths]
    snapshot_entries = []
    for path in sorted((x for x in SNAPSHOT.iterdir() if x.is_file() or x.is_symlink()), key=lambda x: x.name.encode()):
        entry = _content_entry(path, root=SNAPSHOT)
        if entry["type"] == "symlink":
            cache_root = SNAPSHOT.parents[2].resolve(strict=True)
            if not Path(entry["realpath"]).is_relative_to(cache_root):
                raise ValueError("model snapshot symlink escapes frozen model-cache root")
        snapshot_entries.append(entry)
    python = (ROOT / ".venv-atlas/bin/python").resolve(strict=True)
    executables = []
    for raw in (python, Path("/usr/bin/bash"), Path("/usr/bin/strace"), Path("/usr/bin/tmux"), Path("/usr/bin/ldd")):
        path = raw.resolve(strict=True)
        executables.append({"path": str(path), "size": path.stat().st_size, "sha256": sha_file(path)})
    distributions = [_distribution_record(name) for name in
                     ("numpy", "torch", "transformers", "tokenizers", "safetensors", "huggingface-hub", "cryptography")]
    return {
        "schema_version": "msae_v2_dependency_closure_v1", "protocol_id": PROTOCOL,
        "entries": sorted(entries, key=lambda x: x["path"]),
        "quarantined_entries": [_quarantine_entry(rel) for rel in sorted(QUARANTINED)],
        "sealed_payload_content_reads": 0,
        "model_snapshot": {"path": str(SNAPSHOT), "revision": SNAPSHOT.name,
                           "entries": snapshot_entries},
        "checkpoint_registry": checkpoints,
        "python_executable": str(python), "python_version": sys.version,
        "executables": executables, "interpreter_ldd": _ldd_inventory(python),
        "distributions": distributions,
        "static_runtime_allowlist": {
            "network": [], "shell": [], "dynamic_local_imports": [],
            "process_argv0": ["/usr/bin/ldd", "/usr/bin/strace", "/usr/bin/tmux", "/usr/bin/nvidia-smi", str(python)],
            "external_write_roots": [str(PRIVATE_KEY.parent), str(STATE_ROOT), "/tmp/msae_independent_measurement_v2_build_primary",
                                     "/tmp/msae_independent_measurement_v2_build_rebuild", str(RUN_ROOT)],
        },
        "runtime_policy": {"deterministic_algorithms": True, "tf32": False, "model_dtype": "float16",
                           "cache_dtype": "float32", "layer": 3,
                           "pooling": "registered_first_subtoken_rows",
                           "gpu_uuid_discovered_only_after_prescore_ship": True},
        "protocol_config_sha256": sha_file(V2_CONFIG / "protocol.json"),
        "authorization_commitment_sha256": sha_file(V2_CONFIG / "authorization_commitment.json"),
    }


def environment_payload(closure: Mapping[str, Any]) -> dict[str, Any]:
    commitment = read_json(V2_CONFIG / "authorization_commitment.json")
    return {
        "schema_version": "msae_v2_environment_allowlist_v1", "protocol_id": PROTOCOL,
        "python_executable": closure["python_executable"], "python_version": closure["python_version"],
        "dependency_closure_payload_sha256": sha_bytes(canonical_bytes(closure)),
        "deterministic_algorithms": True, "allow_tf32": False,
        "model_revision": SNAPSHOT.name, "model_dtype": "float16", "cache_dtype": "float32",
        "layer": 3, "maximum_sequence_length": 128,
        "nonce_directory": commitment["nonce_directory"], "gpu_lock_directory": commitment["gpu_lock_directory"],
        "offline_environment": {"TRANSFORMERS_OFFLINE": "1", "HF_HUB_OFFLINE": "1", "CUDA_CACHE_DISABLE": "1"},
    }


_TYPED_STAGE_A_PATHS = (
    "data/msae_independent_measurement_v2/data_baseline_manifest.json",
    "data/msae_independent_measurement_v2/protected_v1_manifest.json",
    "data/msae_independent_measurement_v2/source_exposure.json",
    "data/msae_independent_measurement_v2/source_alias_manifest.json",
    "data/msae_independent_measurement_v2/overlap_fixtures.json",
    "data/msae_independent_measurement_v2/history_census.json",
    "data/msae_independent_measurement_v2/history_overlap.json",
    "data/msae_independent_measurement_v2/v1_row_crosswalk.json",
    "data/msae_independent_measurement_v2/label_rows.jsonl",
    "data/msae_independent_measurement_v2/task_manifest.json",
    "data/msae_independent_measurement_v2/support.json",
    "data/msae_independent_measurement_v2/prefix_templates.json",
    "data/msae_independent_measurement_v2/maps.json",
    "data/msae_independent_measurement_v2/finite_pass_matrix.json",
    "data/msae_independent_measurement_v2/protocol_imports.json",
    "data/msae_independent_measurement_v2/dependency_closure.json",
    "data/msae_independent_measurement_v2/endpoint_registry.json",
    "data/msae_independent_measurement_v2/environment_allowlist.json",
    "configs/msae_independent_measurement_v2/protocol.json",
    "configs/msae_independent_measurement_v2/authorization_commitment.json",
    "configs/msae_independent_measurement_v2/ed25519_public.pem",
)


def stage_a_payload() -> dict[str, Any]:
    from msae_measurement_remediation_v1 import build_stage_a
    config_path = V2_CONFIG / "protocol.json"
    raw = config_path.read_bytes()
    config_sha = sha_bytes(raw)
    overlap = read_json(V2_DATA / "history_overlap.json")
    support = read_json(V2_DATA / "support.json")
    matrix = read_json(V2_DATA / "finite_pass_matrix.json")
    eligible = overlap["status"] == "eligible" and support["status"] == "eligible" and matrix["status"] == "eligible"
    artifacts = {
        "candidate_confirmation_source": V2_DATA / "history_overlap.json",
        "immutable_source_revision": V2_DATA / "source_alias_manifest.json",
        "independent_grouping_provenance": V2_DATA / "v1_row_crosswalk.json",
        "label_support_audit": V2_DATA / "support.json",
        "construct_inventory": V2_DATA / "endpoint_registry.json",
        "counterfactual_template_specification": V2_DATA / "prefix_templates.json",
        "tolerance_ladder_frozen": config_path,
        "dependency_attestation": V2_DATA / "dependency_closure.json",
    }
    evidence = {}
    for name, path in artifacts.items():
        status = "eligible" if (eligible or name not in {"candidate_confirmation_source", "independent_grouping_provenance", "label_support_audit"}) else "ineligible"
        evidence[name] = {
            "schema_version": "msae_endpoint_evidence_v1", "protocol_config_sha256": config_sha,
            "endpoint_name": name, "category": "stage_a", "status": status,
            "reasons": [] if status == "eligible" else ["typed_v2_gate_ineligible"],
            "evidence_artifact_sha256": sha_file(path),
            "observed_value": {"artifact_path": str(path.relative_to(ROOT)), "artifact_sha256": sha_file(path),
                               "source_revision": read_json(ROOT / "data/msae_independent_measurement_v1/source_partition.json")["source_revision"],
                               "partition_sha256": sha_file(V2_DATA / "source_alias_manifest.json")},
        }
    base = build_stage_a(raw, config_sha, evidence)
    typed = {rel: sha_file(ROOT / rel) for rel in _TYPED_STAGE_A_PATHS}
    return {
        "schema_version": "msae_exposed_source_stage_a_v2", "protocol_id": PROTOCOL,
        "claim_scope": "exposed_source_technical_measurement_replication",
        "confirmation_partition_status": "replacement_required_not_run",
        "protocol_config_sha256": config_sha, "typed_artifact_sha256": typed,
        "typed_artifact_set_sha256": sha_bytes(canonical_bytes(typed)),
        "base_stage_a": base,
        "stage_ready": bool(eligible and base["stage_ready"]),
        "blockers": [] if eligible and base["stage_ready"] else [
            name for name, ok in (("substantive_overlap", overlap["status"] == "eligible"),
                                  ("label_support", support["status"] == "eligible"),
                                  ("finite_maps", matrix["status"] == "eligible"),
                                  ("base_contract", base["stage_ready"])) if not ok],
    }


def validate_stage_a() -> dict[str, Any]:
    path = V2_PROV / "stage_a.json"
    stage = read_json(path)
    if stage.get("schema_version") != "msae_exposed_source_stage_a_v2" or stage.get("protocol_id") != PROTOCOL:
        raise ValueError("not a v2 wrapper Stage A")
    if set(stage.get("typed_artifact_sha256", {})) != set(_TYPED_STAGE_A_PATHS):
        raise ValueError("typed Stage-A artifact registry mismatch")
    for rel, digest in stage["typed_artifact_sha256"].items():
        validate_sha256(digest, rel)
        if sha_file(ROOT / rel) != digest:
            raise ValueError(f"typed Stage-A artifact drift: {rel}")
    if sha_bytes(canonical_bytes(stage["typed_artifact_sha256"])) != stage["typed_artifact_set_sha256"]:
        raise ValueError("typed Stage-A set digest mismatch")
    expected = stage_a_payload()
    if canonical_bytes(stage) != canonical_bytes(expected):
        raise ValueError("Stage A does not reproduce from typed inputs")
    if stage["stage_ready"] is not True:
        raise ValueError(f"Stage A is not ready: {stage['blockers']}")
    return stage


def _git_status() -> list[str]:
    raw = subprocess.check_output(["/usr/bin/git", "status", "--porcelain=v2", "--untracked-files=all"],
                                  cwd=ROOT, text=True)
    return raw.splitlines()


def _candidate_paths() -> list[Path]:
    paths = [ROOT / "docs/rfc-msae-independent-measurement-v2.md", ROOT / "TODO.md",
             ROOT / "scripts/msae_independent_measurement_v2.py", ROOT / "scripts/run_msae_independent_calibration_v2.py",
             ROOT / "scripts/launch_msae_independent_calibration_v2.sh", ROOT / "tests/test_msae_independent_measurement_v2.py",
             V2_CONFIG / "protocol.json", V2_CONFIG / "authorization_commitment.json", V2_CONFIG / "ed25519_public.pem"]
    paths.extend(sorted((x for x in V2_DATA.iterdir() if x.is_file()), key=lambda x: x.name.encode()))
    paths.extend([V2_PROV / "stage_a.json", V2_PROV / "status.json"])
    return paths


def build_candidate_manifest() -> dict[str, Any]:
    candidate_files = [_content_entry(path) for path in _candidate_paths()]
    protected = read_json(V2_DATA / "protected_v1_manifest.json")
    protected_paths = {entry["path"] for entry in protected["entries"]}
    candidate_names = {entry["path"] for entry in candidate_files}
    classifications = []
    for line in _git_status():
        path = line.split(" ", 8)[-1]
        # Porcelain-v2 untracked rows are '? path'; tracked rows end with path.
        if line.startswith("? "):
            path = line[2:]
        classification = "candidate" if path in candidate_names or any(x.startswith(path.rstrip("/") + "/") for x in candidate_names) else "protected_baseline" if path in protected_paths or any(x.startswith(path.rstrip("/") + "/") for x in protected_paths) else "preexisting_other"
        classifications.append({"line": line, "path_projection": path, "classification": classification})
    stage_sha = sha_file(V2_PROV / "stage_a.json")
    closure_sha = sha_file(V2_DATA / "dependency_closure.json")
    return {
        "schema_version": "msae_v2_prescore_candidate_manifest_v1", "protocol_id": PROTOCOL,
        "candidate_root_realpath": str(ROOT.resolve(strict=True)), "candidate_files": candidate_files,
        "candidate_tree_sha256": sha_bytes(canonical_bytes(candidate_files)),
        "dependency_closure_sha256": closure_sha, "stage_a_sha256": stage_sha,
        "repository_status": _git_status(), "repository_status_classification": classifications,
        "required_absent_post_review_outputs": [str(V2_REVIEW.relative_to(ROOT)), RUN_REL],
        "required_external_state": {
            "private_key": read_json(V2_CONFIG / "authorization_commitment.json")["private_key_binding"],
            "nonce_directory": _directory_binding(NONCE_DIR), "gpu_lock_directory": _directory_binding(GPU_LOCK_DIR),
            "required_empty_nonce_directory": True,
            "required_absent_build_roots": ["/tmp/msae_independent_measurement_v2_build_primary", "/tmp/msae_independent_measurement_v2_build_rebuild"],
            "required_absent_review_files_pattern": "/tmp/msae_v2_prescore_{check,trace}_${manifest_sha256}.{json,log}",
            "required_absent_tmux_socket": f"/tmp/msae_independent_measurement_v2_{stage_sha}.sock",
        },
        "quarantined_entries": [_quarantine_entry(rel) for rel in sorted(QUARANTINED)],
        "sealed_payload_content_reads": 0, "self_hash_excluded": True,
    }


def build_m4(checkpoints: list[dict[str, Any]]) -> dict[str, Any]:
    primary_closure = closure_payload(checkpoints)
    rebuild_closure = closure_payload(checkpoints)
    if canonical_bytes(primary_closure) != canonical_bytes(rebuild_closure):
        raise ValueError("independent dependency-closure rebuild differs")
    registry_a = endpoint_registry()
    registry_b = endpoint_registry()
    if canonical_bytes(registry_a) != canonical_bytes(registry_b):
        raise ValueError("endpoint registry rebuild differs")
    env_a = environment_payload(primary_closure)
    env_b = environment_payload(rebuild_closure)
    if canonical_bytes(env_a) != canonical_bytes(env_b):
        raise ValueError("environment allowlist rebuild differs")
    install_json(V2_DATA / "dependency_closure.json", primary_closure)
    install_json(V2_DATA / "endpoint_registry.json", registry_a)
    install_json(V2_DATA / "environment_allowlist.json", env_a)
    stage_a = stage_a_payload()
    # A second typed reconstruction is required before installation.
    if canonical_bytes(stage_a) != canonical_bytes(stage_a_payload()):
        raise ValueError("Stage-A rebuild differs")
    V2_PROV.mkdir(parents=True, exist_ok=True)
    install_json(V2_PROV / "stage_a.json", stage_a)
    install_json(V2_PROV / "status.json", {
        "schema_version": "msae_v2_prescore_status_v1", "protocol_id": PROTOCOL,
        "status": "ready_prescore_review" if stage_a["stage_ready"] else "blocked_prescore",
        "stage_a_ready": stage_a["stage_ready"], "stage_a_sha256": sha_file(V2_PROV / "stage_a.json"),
        "stage_b": "not_run", "stage_c": "not_run", "confirmation_partition": "replacement_required",
    })
    if not stage_a["stage_ready"]:
        return stage_a
    manifest = build_candidate_manifest()
    install_json(V2_PROV / "prescore_candidate_manifest.json", manifest)
    return stage_a


def _verify_entry(entry: Mapping[str, Any], *, root: Path = ROOT) -> None:
    path = root / entry["path"] if not Path(entry["path"]).is_absolute() else Path(entry["path"])
    st = path.lstat()
    if entry["type"] == "regular":
        if not stat.S_ISREG(st.st_mode) or stat.S_ISLNK(st.st_mode):
            raise ValueError(f"candidate type drift: {path}")
        if st.st_size != entry["size"] or stat.S_IMODE(st.st_mode) != entry["mode"] or sha_file(path) != entry["sha256"]:
            raise ValueError(f"candidate content drift: {path}")
    elif entry["type"] == "symlink":
        if not stat.S_ISLNK(st.st_mode) or os.readlink(path) != entry["link_target"]:
            raise ValueError(f"candidate symlink drift: {path}")
        if sha_file(path.resolve(strict=True)) != entry["sha256"]:
            raise ValueError(f"candidate symlink target drift: {path}")
    else:
        raise ValueError(f"unknown candidate type: {entry['type']}")


def verify_baseline_projection() -> dict[str, int]:
    baseline = read_json(V2_DATA / "data_baseline_manifest.json")
    checked = 0
    lstat_only = 0
    for entry in baseline["entries"]:
        path = ROOT / entry["path"]
        st = path.lstat()
        if entry["type"] == "directory":
            if not stat.S_ISDIR(st.st_mode) or stat.S_IMODE(st.st_mode) != entry["mode"]:
                raise ValueError(f"baseline directory drift: {entry['path']}")
        elif entry["path"] in QUARANTINED:
            current = _quarantine_entry(entry["path"])
            if current["size"] != entry["size"]:
                raise ValueError(f"quarantine baseline size drift: {entry['path']}")
            lstat_only += 1
        else:
            if not stat.S_ISREG(st.st_mode) or st.st_size != entry["size"] or sha_file(path) != entry["sha256"]:
                raise ValueError(f"baseline content drift: {entry['path']}")
            checked += 1
    return {"content_rehash": checked, "lstat_only": lstat_only}


def verify_protected_v1() -> int:
    protected = read_json(V2_DATA / "protected_v1_manifest.json")
    for entry in protected["entries"]:
        path = ROOT / entry["path"]
        st = path.lstat()
        if entry["type"] == "regular":
            if not stat.S_ISREG(st.st_mode) or st.st_size != entry["size"] or sha_file(path) != entry["sha256"]:
                raise ValueError(f"protected v1 drift: {entry['path']}")
        elif entry["type"] == "directory" and not stat.S_ISDIR(st.st_mode):
            raise ValueError(f"protected v1 type drift: {entry['path']}")
    terminal = read_json(ROOT / "reports/provenance/msae_independent_measurement_v1/status.json")
    if terminal["status"] != "stopped_prescore" or terminal["stage_a_ready"] is not False or terminal["stage_b"] != "not_run" or terminal["stage_c"] != "not_run":
        raise ValueError("v1 terminal state was reinterpreted")
    return len(protected["entries"])


def verify_candidate_manifest(phase: str = "prescore") -> dict[str, Any]:
    manifest_path = V2_PROV / "prescore_candidate_manifest.json"
    manifest = read_json(manifest_path)
    if manifest.get("schema_version") != "msae_v2_prescore_candidate_manifest_v1" or manifest.get("protocol_id") != PROTOCOL:
        raise ValueError("candidate manifest schema mismatch")
    if manifest["candidate_root_realpath"] != str(ROOT.resolve(strict=True)):
        raise ValueError("candidate root mismatch")
    for entry in manifest["candidate_files"]:
        _verify_entry(entry)
    if sha_bytes(canonical_bytes(manifest["candidate_files"])) != manifest["candidate_tree_sha256"]:
        raise ValueError("candidate tree digest mismatch")
    if sha_file(V2_DATA / "dependency_closure.json") != manifest["dependency_closure_sha256"]:
        raise ValueError("closure digest mismatch")
    if sha_file(V2_PROV / "stage_a.json") != manifest["stage_a_sha256"]:
        raise ValueError("Stage-A digest mismatch")
    current_status = _git_status()
    allowed_new = {f"? {str((V2_PROV / 'prescore_candidate_manifest.json').relative_to(ROOT))}"}
    if phase in {"post_review", "post_signature"}:
        allowed_new.add(f"? {str(V2_REVIEW.relative_to(ROOT))}")
    projected_status = [line for line in current_status if line not in allowed_new]
    if projected_status != manifest["repository_status"]:
        raise ValueError("repository status projection drift")
    validate_stage_a()
    baseline_counts = verify_baseline_projection()
    protected_count = verify_protected_v1()
    for item in manifest["quarantined_entries"]:
        observed = _quarantine_entry(item["path"])
        for key in ("device", "inode", "mode", "size", "nlink", "ctime_ns", "mtime_ns", "frozen_v1_sha256"):
            if observed[key] != item[key]:
                raise ValueError(f"quarantined metadata drift: {item['path']}/{key}")
    for root in manifest["required_external_state"]["required_absent_build_roots"]:
        if Path(root).exists():
            raise ValueError(f"temporary build root exists: {root}")
    if any(NONCE_DIR.iterdir()):
        raise ValueError("nonce directory is not empty")
    review_exists = V2_REVIEW.exists()
    run_exists = RUN_ROOT.exists()
    if phase == "prescore":
        if review_exists or run_exists:
            raise ValueError("post-review output exists during prescore check")
    elif phase == "post_review":
        if not review_exists or run_exists:
            raise ValueError("post-review projection mismatch")
        review = V2_REVIEW.read_text(encoding="utf-8")
        expected = {
            f"PRESCORE_CANDIDATE_MANIFEST_SHA256: {sha_file(manifest_path)}",
            f"STAGE_A_SHA256: {manifest['stage_a_sha256']}",
            f"DEPENDENCY_CLOSURE_SHA256: {manifest['dependency_closure_sha256']}",
        }
        if "VERDICT: SHIP" not in review or any(line not in review for line in expected):
            raise ValueError("review transcript lacks exact SHIP/digest evidence")
    elif phase == "post_signature":
        if not review_exists or not run_exists:
            raise ValueError("post-signature projection mismatch")
        entries = sorted(x.relative_to(RUN_ROOT).as_posix() for x in RUN_ROOT.rglob("*") if x.is_file())
        if entries != ["authorization.json"]:
            raise ValueError(f"unexpected prelaunch run outputs: {entries}")
        verify_authorization(RUN_ROOT / "authorization.json", consume=False)
    else:
        raise ValueError("unknown candidate projection phase")
    return {"schema_version": "msae_v2_prescore_check_v1", "protocol_id": PROTOCOL,
            "phase": phase, "manifest_sha256": sha_file(manifest_path),
            "candidate_tree_sha256": manifest["candidate_tree_sha256"],
            "dependency_closure_sha256": manifest["dependency_closure_sha256"],
            "stage_a_sha256": manifest["stage_a_sha256"], "repository_status_sha256": sha_bytes(canonical_bytes(current_status)),
            "baseline_counts": baseline_counts, "protected_v1_entries": protected_count,
            "quarantined_metadata_checks": len(QUARANTINED), "sealed_payload_content_reads": 0,
            "eligible": True}


def prescore_traced_check(manifest: Path, output: Path, trace: Path) -> None:
    if manifest.resolve(strict=True) != (V2_PROV / "prescore_candidate_manifest.json").resolve(strict=True):
        raise ValueError("unexpected candidate manifest")
    fds = []
    try:
        for path in (output, trace):
            fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW | os.O_CLOEXEC, 0o600)
            os.set_inheritable(fd, True)
            fds.append(fd)
        check_fd, trace_fd = fds
        command = ["/usr/bin/strace", "-f", "-qq", "-yy", "-e", "trace=open,openat,openat2,creat",
                   "-o", f"/proc/self/fd/{trace_fd}", str((ROOT / ".venv-atlas/bin/python").resolve()),
                   "-B", "-I", str(Path(__file__).resolve()), "prescore-check", "--output-fd", str(check_fd)]
        result = subprocess.run(command, pass_fds=(check_fd, trace_fd), close_fds=True)
        if result.returncode != 0:
            raise RuntimeError(f"traced prescore check failed: {result.returncode}")
        for fd, path in zip(fds, (output, trace)):
            os.fsync(fd)
            st_fd, st_path = os.fstat(fd), path.lstat()
            if (st_fd.st_dev, st_fd.st_ino) != (st_path.st_dev, st_path.st_ino):
                raise ValueError("prescore output path/FD substitution")
    finally:
        for fd in fds:
            with contextlib.suppress(OSError):
                os.close(fd)


def verify_prescore_trace(manifest: Path, check: Path, trace: Path) -> dict[str, Any]:
    expected_manifest = sha_file(manifest)
    payload = read_json(check)
    if payload.get("eligible") is not True or payload.get("manifest_sha256") != expected_manifest:
        raise ValueError("prescore check output mismatch")
    trace_text = trace.read_text(encoding="utf-8", errors="strict")
    for rel in QUARANTINED:
        absolute = str((ROOT / rel).resolve(strict=True))
        if rel in trace_text or absolute in trace_text:
            raise ValueError(f"trace observed forbidden quarantined payload open: {rel}")
    line = {
        "manifest_sha256": expected_manifest, "check_sha256": sha_file(check),
        "trace_sha256": sha_file(trace), "sealed_payload_content_reads": 0,
        "eligible": True,
    }
    print(json.dumps(line, sort_keys=True, separators=(",", ":")))
    return line


def _start_ticks(pid: int) -> str:
    raw = Path(f"/proc/{pid}/stat").read_text(encoding="ascii")
    close = raw.rfind(")")
    fields = raw[close + 2:].split()
    return fields[19]


def _send_json(sock: socket.socket, value: Any) -> None:
    raw = canonical_bytes(value)
    sock.sendall(struct.pack(">Q", len(raw)) + raw)


def _recv_json(sock: socket.socket) -> Any:
    header = b""
    while len(header) < 8:
        chunk = sock.recv(8 - len(header))
        if not chunk:
            raise EOFError("socket closed before frame header")
        header += chunk
    length = struct.unpack(">Q", header)[0]
    if length > 1 << 20:
        raise ValueError("oversized handoff frame")
    raw = b""
    while len(raw) < length:
        chunk = sock.recv(length - len(raw))
        if not chunk:
            raise EOFError("socket closed before frame body")
        raw += chunk
    return json.loads(raw)


def _receive_fd(sock: socket.socket) -> int:
    _, ancillary, _, _ = sock.recvmsg(1, socket.CMSG_LEN(array.array("i", [0]).itemsize))
    fds = []
    for level, kind, payload in ancillary:
        if level == socket.SOL_SOCKET and kind == socket.SCM_RIGHTS:
            values = array.array("i")
            values.frombytes(payload[:len(payload) - len(payload) % values.itemsize])
            fds.extend(values)
    if len(fds) != 1:
        for fd in fds:
            os.close(fd)
        raise ValueError("expected exactly one GPU lease FD")
    return fds[0]


def _runtime_failure(message: str, *, broker_pid: int, worker_pid: int | None) -> None:
    payload = {"schema_version": "msae_v2_technical_failure_v1", "protocol_id": PROTOCOL,
               "status": "not_run", "reason": message, "broker_pid": broker_pid,
               "worker_pid": worker_pid, "stage_b_written": (RUN_ROOT / "stage_b.json").exists()}
    with contextlib.suppress(FileExistsError):
        install_json(RUN_ROOT / "technical_failure.json", payload)
    if not (RUN_ROOT / "stage_b.json").exists():
        with contextlib.suppress(FileExistsError):
            install_json(RUN_ROOT / "status.json", {"schema_version": "msae_v2_runtime_status_v1",
                                                     "status": "technical_failure_not_run", "stage_b_ready": False})


def broker(socket_path: str, gpu_uuid: str, gpu_index: int) -> None:
    os.setsid()
    broker_pid = os.getpid()
    sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    deadline = time.monotonic() + 10
    while True:
        try:
            sock.connect(socket_path)
            break
        except (FileNotFoundError, ConnectionRefusedError):
            if time.monotonic() >= deadline:
                raise
            time.sleep(0.05)
    _send_json(sock, {"schema_version": "msae_v2_broker_hello_v1", "pid": broker_pid,
                      "start_ticks": _start_ticks(broker_pid), "sid": os.getsid(0), "pgid": os.getpgrp()})
    lease_fd = _receive_fd(sock)
    os.set_inheritable(lease_fd, True)
    fcntl.flock(lease_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
    ready_r, ready_w = os.pipe()
    worker_pid = os.fork()
    if worker_pid == 0:
        os.close(ready_w)
        try:
            os.setpgid(0, 0)
            # Linux parent-death watchdog: broker death terminates the worker.
            import ctypes
            libc = ctypes.CDLL(None, use_errno=True)
            if libc.prctl(1, 15, 0, 0, 0) != 0:  # PR_SET_PDEATHSIG, SIGTERM
                raise OSError(ctypes.get_errno(), "prctl(PR_SET_PDEATHSIG) failed")
            if os.getppid() != broker_pid:
                raise RuntimeError("broker died during worker setup")
            signal_byte = os.read(ready_r, 1)
            if signal_byte != b"1":
                raise RuntimeError("launcher did not authorize worker handoff")
            os.close(ready_r)
            log_fd = os.open(RUN_ROOT / "logs/worker.log", os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
            os.dup2(log_fd, 1)
            os.dup2(log_fd, 2)
            if log_fd > 2:
                os.close(log_fd)
            environment = os.environ.copy()
            environment.update({
                "CUDA_VISIBLE_DEVICES": gpu_uuid, "CUDA_CACHE_DISABLE": "1",
                "TRANSFORMERS_OFFLINE": "1", "HF_HUB_OFFLINE": "1", "PYTHONDONTWRITEBYTECODE": "1",
                "MSAE_LEASE_FD": str(lease_fd), "MSAE_GPU_UUID": gpu_uuid,
            })
            argv = [str((ROOT / ".venv-atlas/bin/python").resolve()), "-B", "-I",
                    str((ROOT / "scripts/run_msae_independent_calibration_v2.py").resolve()),
                    "--run-root", RUN_REL, "--gpu-uuid", gpu_uuid, "--broker-pid", str(broker_pid)]
            os.execve(argv[0], argv, environment)
        except BaseException as error:
            _runtime_failure(f"worker_setup:{type(error).__name__}:{error}", broker_pid=broker_pid, worker_pid=os.getpid())
            os._exit(125)
    os.close(ready_r)
    os.setpgid(worker_pid, worker_pid)
    hello = {"schema_version": "msae_v2_worker_handoff_v1", "broker_pid": broker_pid,
             "broker_start_ticks": _start_ticks(broker_pid), "worker_pid": worker_pid,
             "worker_start_ticks": _start_ticks(worker_pid), "worker_pgid": worker_pid,
             "gpu_uuid": gpu_uuid, "gpu_index": gpu_index, "lease_fd": lease_fd}
    _send_json(sock, hello)
    sock.settimeout(10)
    if sock.recv(1) != b"G":
        os.killpg(worker_pid, 15)
        _runtime_failure("launcher_handoff_ack_missing", broker_pid=broker_pid, worker_pid=worker_pid)
        raise RuntimeError("launcher handoff acknowledgement missing")
    os.write(ready_w, b"1")
    os.close(ready_w)
    sock.close()
    started = time.monotonic()
    timed_out = False
    while True:
        pid, status = os.waitpid(worker_pid, os.WNOHANG)
        if pid == worker_pid:
            exit_ok = os.WIFEXITED(status) and os.WEXITSTATUS(status) == 0
            if not exit_ok and not (RUN_ROOT / "technical_failure.json").exists():
                _runtime_failure(f"worker_exit_status:{status}", broker_pid=broker_pid, worker_pid=worker_pid)
            break
        if time.monotonic() - started >= 6 * 60 * 60:
            timed_out = True
            os.killpg(worker_pid, 15)
            grace = time.monotonic() + 60
            while time.monotonic() < grace:
                pid, _ = os.waitpid(worker_pid, os.WNOHANG)
                if pid == worker_pid:
                    break
                time.sleep(0.25)
            else:
                os.killpg(worker_pid, 9)
                os.waitpid(worker_pid, 0)
            _runtime_failure("six_hour_timeout", broker_pid=broker_pid, worker_pid=worker_pid)
            break
        time.sleep(1)
    os.close(lease_fd)
    if timed_out:
        raise SystemExit(124)


def _gpu_rows() -> list[tuple[int, int, str, int]]:
    query = subprocess.check_output(["/usr/bin/nvidia-smi", "--query-gpu=index,uuid,memory.used,utilization.gpu",
                                     "--format=csv,noheader,nounits"], text=True)
    processes = subprocess.check_output(["/usr/bin/nvidia-smi", "--query-compute-apps=gpu_uuid,pid",
                                         "--format=csv,noheader,nounits"], text=True).strip()
    busy = {line.split(",", 1)[0].strip() for line in processes.splitlines() if line.strip()}
    rows = []
    for line in query.splitlines():
        index, uuid, memory, utilization = [x.strip() for x in line.split(",")]
        if uuid not in busy and int(memory) < 1024 and int(utilization) <= 5:
            rows.append((int(memory), int(utilization), uuid, int(index)))
    return sorted(rows)


def _open_gpu_lock(uuid: str) -> tuple[int, Path]:
    binding = _directory_binding(GPU_LOCK_DIR)
    commitment = read_json(V2_CONFIG / "authorization_commitment.json")
    if any(binding[k] != commitment["gpu_lock_directory"][k] for k in ("path", "realpath", "device", "inode", "uid", "mode", "nlink")):
        raise ValueError("GPU lock directory drift")
    name = f"{sha_bytes(uuid.encode('ascii'))}.lock"
    directory_fd = os.open(GPU_LOCK_DIR, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC)
    try:
        fd = os.open(name, os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW | os.O_CLOEXEC, 0o600, dir_fd=directory_fd)
    finally:
        os.close(directory_fd)
    st = os.fstat(fd)
    if not stat.S_ISREG(st.st_mode) or stat.S_IMODE(st.st_mode) != 0o600 or st.st_uid != os.getuid() or st.st_nlink != 1:
        os.close(fd)
        raise ValueError("invalid persistent GPU lock object")
    fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
    os.lseek(fd, 0, os.SEEK_SET)
    raw = os.read(fd, 4096)
    expected = canonical_bytes({"schema_version": "msae_gpu_uuid_lock_v1", "gpu_uuid": uuid})
    if raw and raw != expected:
        os.close(fd)
        raise ValueError("mismatched persistent GPU lock payload")
    if not raw:
        os.lseek(fd, 0, os.SEEK_SET)
        os.write(fd, expected)
        os.fsync(fd)
    os.set_inheritable(fd, True)
    return fd, GPU_LOCK_DIR / name


def launch() -> dict[str, Any]:
    verify_candidate_manifest("post_signature")
    stage = validate_stage_a()
    authorization = verify_authorization(RUN_ROOT / "authorization.json", consume=False)
    rows = _gpu_rows()
    if not rows:
        raise RuntimeError("no GPU satisfies the frozen idle rule")
    lease_fd = -1
    selected = None
    for memory, utilization, uuid, index in rows:
        try:
            lease_fd, lock_path = _open_gpu_lock(uuid)
            selected = (memory, utilization, uuid, index, lock_path)
            break
        except BlockingIOError:
            continue
    if selected is None:
        raise RuntimeError("all eligible GPU UUID locks are held")
    memory, utilization, uuid, index, lock_path = selected
    recheck = subprocess.check_output(["/usr/bin/nvidia-smi", f"--id={index}",
                                       "--query-gpu=uuid,memory.used,utilization.gpu",
                                       "--format=csv,noheader,nounits"], text=True).strip().split(",")
    if recheck[0].strip() != uuid or int(recheck[1]) >= 1024 or int(recheck[2]) > 5:
        os.close(lease_fd)
        raise RuntimeError("GPU drift after UUID lease")
    (RUN_ROOT / "logs").mkdir(mode=0o700)
    socket_path = Path(f"/tmp/msae_independent_measurement_v2_{sha_file(V2_PROV / 'stage_a.json')}.sock")
    if socket_path.exists():
        raise ValueError("tmux socket path already exists")
    handoff_socket = RUN_ROOT / "broker.sock"
    if handoff_socket.exists():
        raise ValueError("broker socket already exists")
    server = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    server.bind(str(handoff_socket))
    os.chmod(handoff_socket, 0o600)
    server.listen(1)
    server.settimeout(15)
    session = "msae-independent-v2-calibration"
    broker_command = (f"exec {str((ROOT / '.venv-atlas/bin/python').resolve())} -B -I "
                      f"{str(Path(__file__).resolve())} broker --socket {handoff_socket} "
                      f"--gpu-uuid {uuid} --gpu-index {index} >> {RUN_ROOT / 'logs/broker.log'} 2>&1")
    subprocess.check_call(["/usr/bin/tmux", "-S", str(socket_path), "new-session", "-d", "-s", session, broker_command])
    try:
        connection, _ = server.accept()
        hello = _recv_json(connection)
        if hello.get("schema_version") != "msae_v2_broker_hello_v1" or _start_ticks(int(hello["pid"])) != hello["start_ticks"]:
            raise ValueError("broker identity validation failed")
        connection.sendmsg([b"L"], [(socket.SOL_SOCKET, socket.SCM_RIGHTS, array.array("i", [lease_fd]))])
        worker = _recv_json(connection)
        if worker["broker_pid"] != hello["pid"] or worker["gpu_uuid"] != uuid or _start_ticks(worker["worker_pid"]) != worker["worker_start_ticks"]:
            raise ValueError("worker identity validation failed")
        lock_record = {"schema_version": "msae_v2_lock_acquired_v1", "protocol_id": PROTOCOL,
                       "gpu_uuid": uuid, "gpu_index": index, "memory_used_mib": memory,
                       "utilization_percent": utilization, "lock_path": str(lock_path),
                       "lock_device": os.fstat(lease_fd).st_dev, "lock_inode": os.fstat(lease_fd).st_ino,
                       "broker_pid": worker["broker_pid"], "broker_start_ticks": worker["broker_start_ticks"],
                       "worker_pid": worker["worker_pid"], "worker_start_ticks": worker["worker_start_ticks"],
                       "worker_pgid": worker["worker_pgid"], "stage_a_sha256": sha_file(V2_PROV / "stage_a.json"),
                       "authorization_envelope_sha256": authorization["envelope_sha256"]}
        install_json(RUN_ROOT / "lock_acquired.json", lock_record)
        handoff = {"schema_version": "msae_v2_live_handoff_v1", "status": "live_handoff_no_result_wait",
                   "session": session, "tmux_socket": str(socket_path), "run_root": RUN_REL,
                   "broker_pid": worker["broker_pid"], "worker_pid": worker["worker_pid"],
                   "gpu_uuid": uuid, "lock_acquired_sha256": sha_file(RUN_ROOT / "lock_acquired.json")}
        install_json(RUN_ROOT / "handoff.json", handoff)
        connection.sendall(b"G")
        pane_pid = int(subprocess.check_output(["/usr/bin/tmux", "-S", str(socket_path), "display-message", "-p",
                                                "-t", session, "#{pane_pid}"], text=True).strip())
        if pane_pid != worker["broker_pid"]:
            raise ValueError("tmux pane is not the bound broker")
    except BaseException:
        with contextlib.suppress(Exception):
            subprocess.run(["/usr/bin/tmux", "-S", str(socket_path), "kill-session", "-t", session], check=False)
        with contextlib.suppress(Exception):
            os.killpg(int(worker.get("worker_pgid", -1)), 15)  # type: ignore[possibly-undefined]
        raise
    finally:
        server.close()
        with contextlib.suppress(FileNotFoundError):
            handoff_socket.unlink()
        os.close(lease_fd)
    print(json.dumps(handoff, indent=2))
    return handoff


OPERATOR_INSTRUCTION = """Do these steps for me. Make sure to use /adversarial to find and fix any issues before running any experiments. Make sure to run the experiments on tmux on whichever GPUs are free. When the experiments are running, don't wait for the results. Preserve the prior attempt as failed; redesign the overlap gate to distinguish boilerplate from substantive reuse; retain AMALGUM only as an exposed-source technical replication; implement strict CoNLL-U/entity parsing, real prefix examples, four-role support and 500 maps, full execution closure, digest-based Stage-B QA, signed authorization/nonce handling, and behavioral failure-path tests."""


def main() -> None:
    parser = argparse.ArgumentParser()
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("fixtures")
    commands.add_parser("audit-overlap")
    commands.add_parser("build-labels-maps")
    commands.add_parser("build-imports")
    commands.add_parser("setup-m3")
    commands.add_parser("build-m4")
    commands.add_parser("sign")
    commands.add_parser("launch")
    broker_parser = commands.add_parser("broker")
    broker_parser.add_argument("--socket", required=True)
    broker_parser.add_argument("--gpu-uuid", required=True)
    broker_parser.add_argument("--gpu-index", type=int, required=True)
    check_parser = commands.add_parser("prescore-check")
    check_parser.add_argument("--output-fd", type=int, required=True)
    traced = commands.add_parser("prescore-traced-check")
    traced.add_argument("--manifest", type=Path, required=True)
    traced.add_argument("--output", type=Path, required=True)
    traced.add_argument("--trace", type=Path, required=True)
    verify_trace = commands.add_parser("verify-prescore-trace")
    verify_trace.add_argument("--manifest", type=Path, required=True)
    verify_trace.add_argument("--check", type=Path, required=True)
    verify_trace.add_argument("--trace", type=Path, required=True)
    args = parser.parse_args()
    if args.command == "fixtures":
        print(json.dumps(build_overlap_fixtures(), indent=2))
    elif args.command == "audit-overlap":
        print(json.dumps(build_overlap(), indent=2)[:10000])
    elif args.command == "build-labels-maps":
        state = build_labels()
        print(json.dumps(build_maps(state), indent=2))
    elif args.command == "build-imports":
        print(json.dumps(build_protocol_imports(), indent=2))
    elif args.command == "setup-m3":
        commitment = setup_authorization_state(OPERATOR_INSTRUCTION)
        checkpoints = checkpoint_registry()
        config = build_protocol_config(checkpoints)
        print(json.dumps({"commitment_sha256": sha_file(V2_CONFIG / "authorization_commitment.json"),
                          "protocol_config_sha256": sha_file(V2_CONFIG / "protocol.json"),
                          "checkpoint_sha256": {x["checkpoint_id"]: x["checkpoint_sha256"] for x in checkpoints}}, indent=2))
    elif args.command == "build-m4":
        print(json.dumps(build_m4(checkpoint_registry()), indent=2))
    elif args.command == "prescore-check":
        payload = verify_candidate_manifest("prescore")
        os.write(args.output_fd, canonical_bytes(payload))
        os.fsync(args.output_fd)
    elif args.command == "prescore-traced-check":
        prescore_traced_check(args.manifest, args.output, args.trace)
    elif args.command == "verify-prescore-trace":
        verify_prescore_trace(args.manifest, args.check, args.trace)
    elif args.command == "sign":
        verify_candidate_manifest("post_review")
        print(json.dumps(sign_authorization(), indent=2))
    elif args.command == "launch":
        launch()
    elif args.command == "broker":
        broker(args.socket, args.gpu_uuid, args.gpu_index)


if __name__ == "__main__":
    main()
