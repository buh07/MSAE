#!/usr/bin/env python3
"""Prescore builder and launch controller for the exposed-source MSAE v3 study.

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
import builtins
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
import shlex
import shutil
import socket
import stat
import struct
import subprocess
import sys
import tempfile
import time
import unicodedata
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Iterable, Iterator, Mapping, Sequence


ROOT = Path(__file__).resolve().parents[1]
PROTOCOL = "msae_exposed_source_measurement_v3"
DATE = "20260820"
V3_DATA = ROOT / "data/msae_independent_measurement_v3"
V3_CONFIG = ROOT / "configs/msae_independent_measurement_v3"
V3_PROV = ROOT / "reports/provenance/msae_independent_measurement_v3"
V3_REVIEW = ROOT / "reports/adversarial/msae_independent_measurement_v3_prescore.md"
PRIMARY_BUILD_ROOT = Path("/tmp/msae_independent_measurement_v3_build_primary")
REBUILD_BUILD_ROOT = Path("/tmp/msae_independent_measurement_v3_build_rebuild")
RUN_REL = "pilot_runs/20260820_msae_independent_measurement_v3_calibration"
RUN_ROOT = ROOT / RUN_REL
SNAPSHOT = Path("/jumbo/lisp/f004ndc/huggingface/hub/models--EleutherAI--pythia-160m-deduped/snapshots/582159a2dfe3e712a8d47ae83dec95ae3bde8e7e")
PRIVATE_KEY = Path("/jumbo/lisp/f004ndc/.msae_keys/independent_measurement_v3_ed25519_private.pem")
STATE_ROOT = Path("/jumbo/lisp/f004ndc/.msae_state")
NONCE_DIR = STATE_ROOT / "independent_measurement_v3/nonces"
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

V3_DATA_PHASE_FILES: dict[str, tuple[str, ...]] = {
    "M0": (
        "data_baseline_manifest.json", "protected_v1_manifest.json",
        "protected_v2_manifest.json", "source_exposure.json",
        "v2_posthoc_boilerplate_analysis.json", "m0_completion_manifest.json",
    ),
    "M1": (
        "source_alias_manifest.json", "overlap_fixtures.json",
        "history_census.json", "history_overlap.json", "v1_row_crosswalk.json",
    ),
    "M2": (
        "label_rows.jsonl", "task_manifest.json", "support.json",
        "prefix_templates.json", "maps.json", "finite_pass_matrix.json",
        "protocol_imports.json",
    ),
    "M4": ("dependency_closure.json", "endpoint_registry.json", "environment_allowlist.json"),
}
V3_DATA_ALL_FILES = tuple(name for phase in ("M0", "M1", "M2", "M4")
                          for name in V3_DATA_PHASE_FILES[phase])
M0_INPUT_NAMES = V3_DATA_PHASE_FILES["M0"][:-1]
M1_TRANSACTION_ROOT = V3_PROV / ".m1_install_transaction"


def _phase_data_names(phase: str) -> set[str]:
    phases = ("M0", "M1", "M2", "M4")
    if phase == "M0_INPUTS":
        return set(M0_INPUT_NAMES)
    if phase == "M1_RECOVERY":
        return set(V3_DATA_PHASE_FILES["M0"]) | {
            name for name in V3_DATA_PHASE_FILES["M1"] if (V3_DATA / name).exists()
        }
    if phase not in phases:
        raise ValueError(f"unknown data-projection phase: {phase}")
    limit = phases.index(phase)
    return {name for current in phases[:limit + 1] for name in V3_DATA_PHASE_FILES[current]}


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


def _reject_json_constant(value: str) -> Any:
    raise ValueError(f"non-standard JSON constant is forbidden: {value}")


def _reject_duplicate_json_members(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate JSON member is forbidden: {key}")
        result[key] = value
    return result


def strict_json_loads(payload: str) -> Any:
    return json.loads(payload, parse_constant=_reject_json_constant,
                      object_pairs_hook=_reject_duplicate_json_members)


def read_json(path: Path) -> Any:
    return strict_json_loads(path.read_text(encoding="utf-8"))


def write_once(path: Path, payload: bytes, mode: int = 0o644) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW | os.O_CLOEXEC, mode)
    try:
        # Some project filesystems apply a creation ACL which can add execute
        # bits despite the requested open(2) mode.  The held descriptor is the
        # object we just created, so normalize it before any bytes are written.
        os.fchmod(fd, mode)
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
        if not isinstance(value, str) or not value:
            raise ValueError(f"{field} must be a nonempty string")
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
    source_record_indices: tuple[int, ...] = ()

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
        if "SpaceAfter" in misc and misc["SpaceAfter"] != "No":
            raise ValueError("SpaceAfter must be exactly 'No' when present")
        if misc.get("SpaceAfter") == "No":
            spacing = ""
        elif "SpacesAfter" in misc:
            raw = misc["SpacesAfter"]
            # Validate the raw value as a complete concatenation of registered
            # escapes before decoding.  This preserves a valid escaped literal
            # backslash instead of mistaking the decoded character for an
            # unknown escape.
            decoded: list[str] = []
            cursor = 0
            simple = {"s": " ", "n": "\n", "t": "\t", "r": "\r", "p": "|", "\\": "\\"}
            while cursor < len(raw):
                if raw[cursor] != "\\" or cursor + 1 >= len(raw):
                    raise ValueError("unknown/incomplete SpacesAfter escape")
                code = raw[cursor + 1]
                if code in simple:
                    decoded.append(simple[code])
                    cursor += 2
                elif (code == "u" and cursor + 6 <= len(raw)
                      and re.fullmatch(r"[0-9A-Fa-f]{4}", raw[cursor + 2:cursor + 6], re.ASCII)):
                    decoded.append(chr(int(raw[cursor + 2:cursor + 6], 16)))
                    cursor += 6
                else:
                    raise ValueError("unknown/incomplete SpacesAfter escape")
            spacing = "".join(decoded)
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
        doc = {"document_id": doc_id, "sentences": [], "tokens": [], "spans": [], "diagnostics": []}
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
        reconstructed = _reconstruct_text(sent_rows, sent_multiwords, allow_bare_misc=not strict_entities)
        if expected is not None and expected != reconstructed:
            if strict_entities:
                raise ValueError(f"# text reconstruction mismatch in {path}: {sent_comments.get('sent_id')}")
            doc["diagnostics"].append({"kind": "historical_text_comment_mismatch",
                                       "sentence_id": sent_comments.get("sent_id"),
                                       "comment_sha256": sha_bytes(expected.encode("utf-8")),
                                       "reconstruction_sha256": sha_bytes(reconstructed.encode("utf-8"))})
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


def _conllu_text_outcomes(
    parsed: Sequence[Mapping[str, Any]], rel: str
) -> tuple[list[TextDocument], list[dict[str, Any]]]:
    """Classify every parsed CoNLL-U document as text or typed non-text."""
    out: list[TextDocument] = []
    nontext: list[dict[str, Any]] = []
    for index, doc in enumerate(parsed):
        sentences = tuple(tuple(piece for token in sentence["tokens"]
                                for piece in lexical_tokens(token["form"]))
                          for sentence in doc["sentences"])
        sentences = tuple(tuple(x for x in sentence if x) for sentence in sentences)
        sentences = tuple(x for x in sentences if x)
        if not sentences:
            nontext.append({
                "kind": "punctuation_or_redaction_only_non_text",
                "path": rel,
                "document_id": doc["document_id"],
                "document_index": index,
                "identity": f"{rel}:{index}:conllu:punctuation_or_redaction_only_non_text",
            })
            continue
        out.append(TextDocument(doc["document_id"], rel, index, sentences))
    if len(out) + len(nontext) != len(parsed):
        raise AssertionError("CoNLL-U document census did not close")
    return out, nontext


def conllu_text_documents(path: Path, rel: str) -> list[TextDocument]:
    parsed = parse_conllu(path, strict_entities=False)
    return _conllu_text_outcomes(parsed, rel)[0]


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
        # Preserve lexical-empty sides here.  The caller must emit a distinct
        # side-level non-text outcome rather than silently dropping it.
        return [("source", token_field(obj["source_words"], "source_words")),
                ("target", token_field(obj["target_words"], "target_words"))]
    normalized = [(field, token_field(obj[field], field)) for field in present]
    if any(tokens != normalized[0][1] for _, tokens in normalized[1:]):
        raise ValueError(f"conflicting text fields at {path}:{index}")
    return [("base", normalized[0][1])]


def json_documents(path: Path, rel: str, *, jsonl: bool,
                   file_sha256: str | None = None) -> tuple[list[TextDocument], dict[str, Any]]:
    digest = validate_sha256(file_sha256 or sha_file(path), "JSON source file SHA-256")
    rows: list[Any]
    if jsonl:
        rows = []
        with path.open("r", encoding="utf-8") as handle:
            for index, line in enumerate(handle):
                try:
                    rows.append(strict_json_loads(line))
                except (json.JSONDecodeError, ValueError) as error:
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
    grouped_records: dict[str, list[dict[str, Any]]] = collections.OrderedDict()
    identities: dict[str, tuple[Any, ...]] = {}
    census = collections.Counter(rows=len(rows))
    nontext_details: list[dict[str, Any]] = []
    field_outcomes: list[dict[str, Any]] = []
    for index, row in enumerate(rows):
        records = _json_object_records(row, rel, index)
        present = [field for field in ("source_words", "target_words", "words", "tokens", "text", "sentence")
                   if isinstance(row, dict) and field in row]
        census["candidate_field_occurrences"] += len(present)
        if not records:
            census["non_text_rows"] += 1
            field_outcomes.append({"path": rel, "record_index": index,
                                   "kind": "non_text_row", "fields": []})
            continue
        if not isinstance(row, dict):
            raise AssertionError
        revision, group = row.get("source_revision"), row.get("document_group")
        stable_group = isinstance(revision, str) and revision and isinstance(group, str) and group
        paired = {side for side, _ in records} == {"source", "target"}
        for record_ordinal, (side, tokens) in enumerate(records):
            represented_fields = [f"{side}_words"] if paired else present
            if not tokens:
                identity = tuple_digest(PROTOCOL, "historical_json_nontext", digest, index, side)
                item = {"path": rel, "record_index": index, "side": side,
                        "fields": represented_fields,
                        "kind": "punctuation_or_redaction_only_non_text",
                        "identity": identity}
                nontext_details.append(item)
                field_outcomes.append(item)
                census["punctuation_or_redaction_only_non_text"] += 1
                census["punctuation_or_redaction_only_non_text_subrecords"] += 1
                census["nontext_field_occurrences"] += len(represented_fields)
                continue
            components = (("source_revision_document_group", revision, group, side)
                          if stable_group else ("file_record", digest, index, side))
            identity = tuple_digest(PROTOCOL, "historical_json_document", *components)
            semantic = (revision, group, side) if stable_group else (digest, index, side)
            if identity in identities and identities[identity] != semantic:
                raise ValueError(f"identity conflict in {rel}")
            identities[identity] = semantic
            grouped.setdefault(identity, []).append(tokens)
            grouped_records.setdefault(identity, []).append({
                "record_index": index, "side": side, "fields": represented_fields,
                "canonical_identity_components": list(components),
                "lexical_token_count": len(tokens),
                "normalized_sentence_sha256": sha_bytes(framed_sentences((tokens,))),
            })
            census[f"text_{side}"] += 1
            census["included_subrecords"] += 1
            census["included_primary_field_occurrences"] += 1
            census["equivalent_field_alias_occurrences"] += len(represented_fields) - 1
            for field_index, field in enumerate(represented_fields):
                field_outcomes.append({"path": rel, "record_index": index,
                                       "side": side, "field": field,
                                       "identity": identity,
                                       "kind": "included_primary" if field_index == 0 else "included_equivalent_alias"})
    docs = [TextDocument(identity, rel, grouped_records[identity][0]["record_index"], tuple(sentences),
                         tuple(item["record_index"] for item in grouped_records[identity]))
            for identity, sentences in grouped.items()]
    census["documents"] = len(docs)
    accounted = (census["included_primary_field_occurrences"]
                 + census["equivalent_field_alias_occurrences"]
                 + census["nontext_field_occurrences"])
    if accounted != census["candidate_field_occurrences"]:
        raise AssertionError(f"JSON candidate-field census did not close for {rel}")
    census["candidate_field_occurrences_accounted"] = accounted
    result: dict[str, Any] = dict(census)
    result["non_text_diagnostics"] = nontext_details
    result["candidate_field_outcomes"] = field_outcomes
    result["document_ledger"] = [
        {"canonical_document_index": index, "canonical_source_id": identity,
         "sentence_count": len(grouped[identity]), "source_records": grouped_records[identity]}
        for index, identity in enumerate(grouped)
    ]
    if (sum(item["sentence_count"] for item in result["document_ledger"])
            != census["included_subrecords"]):
        raise AssertionError(f"JSON record/document ledger did not close for {rel}")
    return docs, result


def line_documents(path: Path, rel: str, *, file_sha256: str | None = None
                   ) -> tuple[list[TextDocument], dict[str, Any]]:
    digest = validate_sha256(file_sha256 or sha_file(path), "line source file SHA-256")
    raw = path.read_bytes().decode("utf-8", errors="strict")
    physical = raw.split("\n")
    if physical and physical[-1] == "":
        physical.pop()
    ledger = []
    sentences = []
    included_indices = []
    for index, line in enumerate(physical):
        if line.endswith("\r"):
            line = line[:-1]
        tokens = lexical_tokens(line)
        outcome = "included_text" if tokens else "punctuation_or_redaction_only_non_text"
        ledger.append({"physical_line_index": index, "outcome": outcome,
                       "lexical_token_count": len(tokens),
                       "normalized_sentence_sha256": sha_bytes(framed_sentences((tokens,)))})
        if tokens:
            sentences.append(tokens)
            included_indices.append(index)
    source_id = f"{digest}:0:physical_lines"
    docs = ([] if not sentences else
            [TextDocument(source_id, rel, included_indices[0], tuple(sentences), tuple(included_indices))])
    census = {"adapter": path.suffix.lower()[1:], "physical_line_count": len(physical),
              "included_line_count": len(sentences),
              "non_text_line_count": len(physical) - len(sentences),
              "documents": len(docs), "canonical_source_id": source_id,
              "line_ledger": ledger,
              "classification": "included_text" if docs else "punctuation_or_redaction_only_non_text"}
    if census["included_line_count"] + census["non_text_line_count"] != census["physical_line_count"]:
        raise AssertionError(f"physical-line census did not close: {rel}")
    return docs, census


def _npy_descriptor_itemsize(descriptor: Any) -> int:
    """Return fixed bytes/item for a safe literal NPY dtype descriptor."""
    if isinstance(descriptor, str):
        match = re.fullmatch(r"[<>=|]?([?bBiufcmMOSUV])(\d+)", descriptor, re.ASCII)
        if match is None or match.group(1) == "O":
            raise ValueError("unsupported or object NPY dtype descriptor")
        count = int(match.group(2))
        if count <= 0:
            raise ValueError("nonpositive NPY dtype width")
        return count * (4 if match.group(1) == "U" else 1)
    if isinstance(descriptor, tuple) and len(descriptor) == 2:
        base, shape = descriptor
        if (not isinstance(shape, tuple) or any(isinstance(x, bool) or not isinstance(x, int) or x < 0
                                                for x in shape)):
            raise ValueError("invalid NPY subarray shape")
        return _npy_descriptor_itemsize(base) * _shape_product(shape)
    if isinstance(descriptor, list) and descriptor:
        total = 0
        names: set[str] = set()
        for field in descriptor:
            if not isinstance(field, tuple) or len(field) not in {2, 3} or not isinstance(field[0], str):
                raise ValueError("invalid structured NPY descriptor")
            if field[0] in names:
                raise ValueError("duplicate structured NPY field")
            names.add(field[0])
            width = _npy_descriptor_itemsize(field[1])
            if len(field) == 3:
                shape = field[2]
                if (not isinstance(shape, tuple) or any(isinstance(x, bool) or not isinstance(x, int) or x < 0
                                                        for x in shape)):
                    raise ValueError("invalid structured NPY field shape")
                width *= _shape_product(shape)
            total += width
        return total
    raise ValueError("unsupported NPY dtype descriptor")


def _shape_product(shape: tuple[int, ...]) -> int:
    product = 1
    for extent in shape:
        product *= extent
        if product > (1 << 63):
            raise ValueError("NPY shape overflow")
    return product


def _validate_npy_bytes(payload: bytes, *, identity: str) -> dict[str, Any]:
    if len(payload) < 10 or payload[:6] != b"\x93NUMPY":
        raise ValueError(f"invalid NPY magic/header: {identity}")
    major, minor = payload[6], payload[7]
    if (major, minor) == (1, 0):
        width, cursor, encoding = 2, 10, "latin1"
    elif major in {2, 3} and minor == 0:
        width, cursor, encoding = 4, 12, "latin1" if major == 2 else "utf-8"
    else:
        raise ValueError(f"unsupported NPY version: {identity}")
    header_length = int.from_bytes(payload[8:8 + width], "little")
    end = cursor + header_length
    if header_length <= 0 or end > len(payload):
        raise ValueError(f"truncated NPY header: {identity}")
    header_raw = payload[cursor:end]
    if not header_raw.endswith(b"\n") or end % 16 != 0:
        raise ValueError(f"malformed NPY header framing: {identity}")
    try:
        header = ast.literal_eval(header_raw.decode(encoding).strip())
    except (UnicodeDecodeError, SyntaxError, ValueError) as error:
        raise ValueError(f"invalid NPY header literal: {identity}") from error
    if (not isinstance(header, dict) or set(header) != {"descr", "fortran_order", "shape"}
            or not isinstance(header["fortran_order"], bool) or not isinstance(header["shape"], tuple)
            or any(isinstance(x, bool) or not isinstance(x, int) or x < 0 for x in header["shape"])):
        raise ValueError(f"invalid NPY header schema: {identity}")
    itemsize = _npy_descriptor_itemsize(header["descr"])
    expected_payload = _shape_product(header["shape"]) * itemsize
    if len(payload) - end != expected_payload:
        raise ValueError(f"NPY payload length mismatch: {identity}")
    return {"version": [major, minor], "header_bytes": header_length,
            "array_payload_bytes": expected_payload, "shape": list(header["shape"]),
            "fortran_order": header["fortran_order"],
            "descriptor_sha256": sha_bytes(repr(header["descr"]).encode("utf-8"))}


def verify_binary_array(path: Path, suffix: str) -> dict[str, Any]:
    payload = path.read_bytes()
    if suffix == ".npy":
        return {"container": "npy", "members": [{"name": path.name,
                 **_validate_npy_bytes(payload, identity=str(path))}]}
    if suffix != ".npz":
        raise ValueError(f"unknown binary-array suffix: {suffix}")
    if len(payload) < 4 or payload[:4] != b"PK\x03\x04":
        raise ValueError(f"invalid NPZ byte-zero local-file signature: {path}")
    try:
        with zipfile.ZipFile(io.BytesIO(payload), "r") as archive:
            infos = archive.infolist()
            names = [item.filename for item in infos]
            if (not infos or infos[0].header_offset != 0 or len(names) != len(set(names))
                    or archive.testzip() is not None
                    or any(item.is_dir() or item.flag_bits & 1 or not item.filename.endswith(".npy")
                           or Path(item.filename).name != item.filename
                           or payload[item.header_offset:item.header_offset + 4] != b"PK\x03\x04"
                           for item in infos)):
                raise ValueError(f"invalid NPZ member registry: {path}")
            members = []
            for item in infos:
                member = archive.read(item)
                members.append({"name": item.filename, "compressed_bytes": item.compress_size,
                                **_validate_npy_bytes(member, identity=f"{path}!{item.filename}")})
    except (zipfile.BadZipFile, RuntimeError, EOFError) as error:
        raise ValueError(f"invalid NPZ container: {path}") from error
    return {"container": "npz", "members": members}


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
    baseline = read_json(V3_DATA / "data_baseline_manifest.json")
    return [entry for entry in baseline["entries"] if entry["type"] == "regular"]


def iter_history(*, candidate_grams: set[bytes] | None = None,
                 audit_events: list[dict[str, Any]] | None = None) -> Iterator[tuple[TextDocument, dict[str, Any]]]:
    """Yield canonical historical text documents without opening quarantined bytes."""
    _, aliases = selected_documents()
    alias_paths = {x["path"]: x["sha256"] for x in aliases}
    seen_file_sha: dict[str, str] = {}
    seen_source: dict[str, tuple[str, str]] = {}
    for entry in sorted(_baseline_regular_entries(), key=lambda x: x["path"]):
        rel = entry["path"]
        if rel in QUARANTINED:
            if audit_events is not None:
                audit_events.append({"path": rel, "census": {"adapter": "sealed_quarantine",
                                                              "classification": "exposed_quarantined_not_scanned"}})
            continue
        if rel in alias_paths:
            if entry["sha256"] != alias_paths[rel]:
                raise ValueError(f"alias manifest mismatch: {rel}")
            if audit_events is not None:
                audit_events.append({"path": rel, "file_sha256": entry["sha256"],
                                     "census": {"adapter": "selected_alias", "classification": "same_frozen_source_copy"}})
            continue
        path = ROOT / rel
        suffix = path.suffix.lower()
        if suffix not in {".conllu", ".jsonl", ".json", ".md", ".diff", ".npy", ".npz"}:
            raise ValueError(f"unknown baseline suffix: {rel}")
        digest = entry["sha256"]
        if digest in seen_file_sha:
            if audit_events is not None:
                audit_events.append({"path": rel, "file_sha256": digest,
                                     "census": {"adapter": "byte_alias", "canonical_path": seen_file_sha[digest]}})
            continue
        seen_file_sha[digest] = rel
        if suffix in {".npy", ".npz"}:
            structure = verify_binary_array(path, suffix)
            if audit_events is not None:
                audit_events.append({"path": rel, "file_sha256": digest,
                                     "census": {"adapter": "binary_array_non_text", "documents": 0,
                                                "classification": "structurally_valid_binary_array_non_text",
                                                "structure": structure}})
            continue
        if suffix == ".conllu":
            parsed_conllu = parse_conllu(path, strict_entities=False)
            diagnostics = [{"path": rel, "document_id": doc["document_id"], **item}
                           for doc in parsed_conllu for item in doc["diagnostics"]]
            docs, nontext = _conllu_text_outcomes(parsed_conllu, rel)
            included_by_index = {doc.record_index: doc for doc in docs}
            document_ledger = []
            canonical_docs = []
            for document_index, parsed_doc in enumerate(parsed_conllu):
                canonical_source_id = f"{digest}:{document_index}"
                sentence_ledger = []
                for sentence_index, sentence in enumerate(parsed_doc["sentences"]):
                    normalized = tuple(piece for token in sentence["tokens"]
                                       for piece in lexical_tokens(token["form"]))
                    sentence_ledger.append({
                        "sentence_index": sentence_index,
                        "parsed_sentence_id": sentence["sentence_id"],
                        "integer_token_count": len(sentence["tokens"]),
                        "lexical_token_count": len(normalized),
                        "outcome": "included_text" if normalized else "punctuation_or_redaction_only_non_text",
                        "normalized_sentence_sha256": sha_bytes(framed_sentences((normalized,))),
                    })
                included = included_by_index.get(document_index)
                outcome = "included_text" if included is not None else "punctuation_or_redaction_only_non_text"
                document_ledger.append({
                    "document_index": document_index,
                    "parsed_document_id": parsed_doc["document_id"],
                    "canonical_source_id": canonical_source_id,
                    "sentence_count": len(sentence_ledger),
                    "sentences": sentence_ledger,
                    "outcome": outcome,
                })
                if included is not None:
                    canonical_docs.append(TextDocument(canonical_source_id, included.path,
                                                       included.record_index, included.sentences))
            docs = canonical_docs
            census = {"parsed_documents": len(parsed_conllu), "documents": len(docs),
                      "non_text_documents": len(nontext), "adapter": "conllu",
                      "parsed_sentences": sum(len(doc["sentences"]) for doc in parsed_conllu),
                      "document_ledger": document_ledger,
                      "diagnostics": diagnostics, "non_text_diagnostics": nontext}
            if census["documents"] + census["non_text_documents"] != census["parsed_documents"]:
                raise AssertionError(f"CoNLL-U census arithmetic mismatch: {rel}")
            if (sum(item["sentence_count"] for item in document_ledger) != census["parsed_sentences"]
                    or len({item["canonical_source_id"] for item in document_ledger}) != len(document_ledger)):
                raise AssertionError(f"CoNLL-U identity/sentence ledger did not close: {rel}")
        elif suffix in {".md", ".diff"}:
            docs, census = line_documents(path, rel, file_sha256=digest)
        else:
            docs, census = json_documents(path, rel, jsonl=suffix == ".jsonl", file_sha256=digest)
            census["adapter"] = suffix[1:]
        if audit_events is not None:
            audit_events.append({"path": rel, "file_sha256": digest, "census": census})
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


def short_sentence_gate(member_count: int, token_sum: int, selected_token_count: int) -> bool:
    return member_count >= 5 and token_sum >= 20 and selected_token_count > 0 and 10 * token_sum >= selected_token_count


def passage_coverage_gate(shared_distinct_grams: int, covered_positions: int, selected_token_count: int) -> bool:
    return (shared_distinct_grams >= 4 and covered_positions >= 20 and selected_token_count > 0
            and 10 * covered_positions >= selected_token_count)


def counterfactual_alignment_qa(
    frozen: Mapping[str, Any], inference_units: Sequence[Mapping[str, Any]],
    pair_registry: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    """Reconstruct every frozen pair mapping against its two source registries."""
    if frozen.get("schema_version") != "msae_independent_calibration_strata_v1":
        raise ValueError("unexpected calibration-strata schema")
    units_by_id: dict[str, Mapping[str, Any]] = {}
    for unit in inference_units:
        unit_id = unit.get("unit_id")
        if not isinstance(unit_id, str) or not unit_id or unit_id in units_by_id:
            raise ValueError("duplicate/missing source inference unit ID")
        units_by_id[unit_id] = unit
    pairs_by_id: dict[str, Mapping[str, Any]] = {}
    for pair in pair_registry:
        pair_id = pair.get("pair_id")
        if not isinstance(pair_id, str) or not pair_id or pair_id in pairs_by_id:
            raise ValueError("duplicate/missing source pair ID")
        pairs_by_id[pair_id] = pair
    rows: list[dict[str, Any]] = []
    expected_construct = {"pair_context": "document_context_anchor", "pair_entity": "entity_substitution"}
    for stratum_id, construct in expected_construct.items():
        stratum = frozen.get("strata", {}).get(stratum_id)
        if not isinstance(stratum, dict):
            raise ValueError(f"missing pair stratum: {stratum_id}")
        units = stratum.get("units")
        if (not isinstance(units, list) or len(units) != 16
                or stratum.get("selected_unit_or_pair_count") != 8
                or stratum.get("alignment_valid") is not True):
            raise ValueError(f"invalid frozen pair-stratum cardinality: {stratum_id}")
        projected_inputs = [{key: unit[key] for key in ("unit_id", "input_ids", "positions", "row_ids")}
                            for unit in units]
        if sha_bytes(canonical_bytes(projected_inputs)) != stratum.get("input_sha256"):
            raise ValueError(f"frozen pair-stratum input digest mismatch: {stratum_id}")
        flattened_rows = [row_id for unit in units for row_id in unit["row_ids"]]
        if flattened_rows != stratum.get("row_ids"):
            raise ValueError(f"frozen pair-stratum row order mismatch: {stratum_id}")
        seen_pairs: set[str] = set()
        for pair_index in range(8):
            source = units[2 * pair_index]
            target = units[2 * pair_index + 1]
            pair_id = source.get("pair_id")
            if (not isinstance(pair_id, str) or pair_id in seen_pairs or target.get("pair_id") != pair_id
                    or source.get("side") != "source" or target.get("side") != "target"
                    or source.get("kind") != "pair" or target.get("kind") != "pair"
                    or source.get("role") != "calibration" or target.get("role") != "calibration"
                    or source.get("unit_id") != f"pair:{pair_id}:source"
                    or target.get("unit_id") != f"pair:{pair_id}:target"):
                raise ValueError(f"pair identity/order mismatch: {stratum_id}:{pair_index}")
            seen_pairs.add(pair_id)
            registry = pairs_by_id.get(pair_id)
            if (registry is None or registry.get("construct") != construct or registry.get("role") != "calibration"):
                raise ValueError(f"pair registry mapping mismatch: {stratum_id}:{pair_id}")
            if registry.get("source_row_ids") != source.get("row_ids") or registry.get("target_row_ids") != target.get("row_ids"):
                raise ValueError(f"pair registry row mapping mismatch: {stratum_id}:{pair_id}")
            if units_by_id.get(source["unit_id"]) != source or units_by_id.get(target["unit_id"]) != target:
                raise ValueError(f"frozen/source inference-unit substitution: {stratum_id}:{pair_id}")
            for side, unit in (("source", source), ("target", target)):
                input_ids, positions, row_ids = unit.get("input_ids"), unit.get("positions"), unit.get("row_ids")
                if (not isinstance(input_ids, list) or not input_ids or any(type(x) is not int or x < 0 for x in input_ids)
                        or not isinstance(positions, list) or not positions
                        or any(type(x) is not int or x < 0 or x >= len(input_ids) for x in positions)
                        or positions != sorted(set(positions))
                        or not isinstance(row_ids, list) or len(row_ids) != len(positions)
                        or row_ids != [f"pair:{pair_id}:{side}:{i}" for i in range(len(row_ids))]):
                    raise ValueError(f"typed pair position/row mapping mismatch: {stratum_id}:{pair_id}:{side}")
            if len(source["row_ids"]) != len(target["row_ids"]):
                raise ValueError(f"pair source/target coverage mismatch: {stratum_id}:{pair_id}")
            rows.append({
                "stratum_id": stratum_id, "construct": construct, "pair_index": pair_index,
                "pair_id": pair_id, "source_unit_id": source["unit_id"], "target_unit_id": target["unit_id"],
                "source_input_sha256": sha_bytes(canonical_bytes(source["input_ids"])),
                "target_input_sha256": sha_bytes(canonical_bytes(target["input_ids"])),
                "source_positions_sha256": sha_bytes(canonical_bytes(source["positions"])),
                "target_positions_sha256": sha_bytes(canonical_bytes(target["positions"])),
                "source_row_ids_sha256": sha_bytes(canonical_bytes(source["row_ids"])),
                "target_row_ids_sha256": sha_bytes(canonical_bytes(target["row_ids"])),
                "source_unit_payload_sha256": sha_bytes(canonical_bytes(source)),
                "target_unit_payload_sha256": sha_bytes(canonical_bytes(target)),
                "pair_registry_payload_sha256": sha_bytes(canonical_bytes(registry)),
                "aligned_row_count": len(source["row_ids"]), "mapping_valid": True,
            })
    if len(rows) != 16 or len({row["pair_id"] for row in rows}) != 16:
        raise ValueError("pair alignment did not produce exactly sixteen distinct pairs")
    return {"schema_version": "msae_v3_counterfactual_cache_alignment_qa_v1",
            "protocol_id": PROTOCOL, "status": "eligible", "pair_count": len(rows),
            "frozen_strata_payload_sha256": sha_bytes(canonical_bytes(frozen)),
            "source_inference_units_payload_sha256": sha_bytes(canonical_bytes(list(inference_units))),
            "source_pair_registry_payload_sha256": sha_bytes(canonical_bytes(list(pair_registry))),
            "pairs": rows}


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
    if short_sentence_gate(len(shared_short), short_tokens, len(st)):
        reasons.append("cumulative_short_sentences")
    shared = sg & hg
    covered: set[int] = set()
    if shared:
        for index in range(max(0, len(st) - 4)):
            if typed_tuple(st[index:index + 5]) in shared:
                covered.update(range(index, index + 5))
    with decimal.localcontext(DECIMAL_CONTEXT):
        coverage = (decimal.Decimal(len(covered)) / decimal.Decimal(len(st))) if st else decimal.Decimal(0)
    if passage_coverage_gate(len(shared), len(covered), len(st)):
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
        "shared_short_selected_fraction": f"{short_tokens}/{len(st)}",
        "shared_short_tuple_set_sha256": sha_bytes(b"".join(struct.pack(">Q", len(typed_tuple(x))) + typed_tuple(x) for x in shared_short)),
        "covered_selected_positions": len(covered), "selected_coverage": format(coverage, "f"),
        "shared_gram_set_sha256": sha_bytes(b"".join(struct.pack(">Q", len(x)) + x for x in sorted(shared))),
        "covered_position_set_sha256": sha_bytes(b"".join(struct.pack(">Q", x) for x in sorted(covered))),
    }


def build_overlap_fixtures() -> dict[str, Any]:
    def doc(name: str, sentences: Sequence[Sequence[str]]) -> TextDocument:
        return TextDocument(name, name, 0, tuple(tuple(x) for x in sentences))
    def phrase_doc(name: str, shared: Sequence[Sequence[str]], total: int, marker: str, *, reverse: bool = False) -> TextDocument:
        ordered = list(reversed(shared)) if reverse else list(shared)
        sentences: list[tuple[str, ...]] = []
        used = 0
        for index, phrase in enumerate(ordered):
            sentences.append(tuple(phrase)); used += len(phrase)
            sentences.append((f"{marker}_separator_{index}",)); used += 1
        sentences.append(tuple(f"{marker}_filler_{i}" for i in range(total - used)))
        return doc(name, sentences)
    seq = tuple(f"t{i}" for i in range(100))
    fixtures: list[dict[str, Any]] = []
    def cycle(name: str, period: int, length: int, offset: int) -> TextDocument:
        tokens = tuple(f"c{(i + offset) % period}" for i in range(length))
        return doc(name, [tokens])

    def passage_history(name: str, source: Sequence[str], starts: Sequence[int]) -> TextDocument:
        tokens: list[str] = []
        for ordinal, start in enumerate(starts):
            if tokens:
                tokens.extend(f"{name}_separator_{ordinal}_{j}" for j in range(5))
            tokens.extend(source[start:start + 5])
        return doc(name, [tokens])

    cases = [
        ("exact_document", doc("s", [seq]), doc("h", [seq]), True),
        ("boundary_flattened", doc("s", [seq[i:i+4] for i in range(0, 100, 4)]), doc("h", [seq]), True),
        ("twenty_percent_edited_document", doc("s", [seq]),
         doc("h", [seq[:80] + tuple(f"edited{i}" for i in range(20))]), True),
        ("copied_15_token_sentence", doc("s", [[f"a{i}" for i in range(15)], ["unrelated"]]), doc("h", [[f"a{i}" for i in range(15)], ["else"]]), True),
        *[(f"exact_low_diversity_{length}_token_sentence",
           doc(f"sld{length}", [tuple("a" if i % 2 else "b" for i in range(length)), ("left",)]),
           doc(f"hld{length}", [tuple("a" if i % 2 else "b" for i in range(length)), ("right",)]), True)
          for length in (10, 15, 19)],
        ("fragmented_25_token_copy", doc("s", [tuple(f"fragment{i}" for i in range(250))]),
         passage_history("h", tuple(f"fragment{i}" for i in range(250)), (0, 30, 60, 90, 120)), True),
        ("unicode_case_normalization", doc("s", [lexical_tokens(" \tCAFÉ\u00a0Straße\n")]),
         doc("h", [lexical_tokens("cafe\u0301\u2003  STRAẞE")]), True),
        ("five_short_20_tokens", doc("s", [[f"x{i}_{j}" for j in range(4)] for i in range(5)]), doc("h", [[f"x{i}_{j}" for j in range(4)] for i in range(5)]), True),
        ("four_short_boilerplate", doc("s", [("steps",), ("buy",), ("by", "car"), ("yes",), tuple(f"sa{i}" for i in range(9))]), doc("h", [("steps",), ("buy",), ("by", "car"), ("yes",), tuple(f"hb{i}" for i in range(9))]), False),
        ("repeated_heading", doc("s", [("steps",)] * 20), doc("h", [("steps",)] * 30), False),
        ("unrelated", doc("s", [[f"a{i}" for i in range(60)]]), doc("h", [[f"b{i}" for i in range(60)]]), False),
        ("sentence_9_tokens_non_substantive", doc("s9", [tuple(f"q{i}" for i in range(9)), ("sx",)]),
         doc("h9", [tuple(f"q{i}" for i in range(9)), ("hx",)]), False),
        ("sentence_10_tokens_substantive", doc("s10", [tuple(f"q{i}" for i in range(10)), ("sx",)]),
         doc("h10", [tuple(f"q{i}" for i in range(10)), ("hx",)]), True),
        ("plain_jaccard_exact_0_80",
         doc("sj", [tuple(f"j{i}" for i in range(50))]),
         doc("hj", [tuple([*(f"j{i}" for i in range(48)), *(f"jh{i}" for i in range(9))])]), True),
        ("plain_jaccard_below_0_80",
         doc("sjb", [tuple(f"jb{i}" for i in range(50))]),
         doc("hjb", [tuple([*(f"jb{i}" for i in range(47)), *(f"jbh{i}" for i in range(10))])]), True),
    ]
    posthoc = read_json(V3_DATA / "v2_posthoc_boilerplate_analysis.json")
    if (posthoc.get("schema_version") != "msae_v3_v2_posthoc_boilerplate_analysis_v1"
            or posthoc.get("row_count") != 4):
        raise ValueError("v2 posthoc fixture registry drift")
    observed_names = ("min_esl", "min_childes", "bengali_esl", "bengali_childes")
    observed_phrase_sets: list[tuple[tuple[str, ...], ...]] = []
    for index, row in enumerate(posthoc["rows"]):
        phrases = tuple(tuple(item["tokens"]) for item in row["shared_short_tuples"])
        encoded = b"".join(struct.pack(">Q", len(typed_tuple(item))) + typed_tuple(item)
                           for item in sorted(phrases, key=typed_tuple))
        if (row.get("v2_collision_index") != index
                or len(phrases) != row.get("distinct_tuple_count")
                or sum(map(len, phrases)) != row.get("unique_tuple_token_sum")
                or sha_bytes(encoded) != row.get("shared_short_tuple_set_sha256")):
            raise ValueError(f"frozen v2 posthoc row drift: {index}")
        observed_phrase_sets.append(phrases)
    cases.extend([
        *( (f"observed_v2_negative_{observed_names[index]}",
            phrase_doc(f"v2s{index}", phrases, posthoc["rows"][index]["selected_token_count"], f"v2s{index}"),
            phrase_doc(f"v2h{index}", phrases, 1200, f"v2h{index}", reverse=True), False)
           for index, phrases in enumerate(observed_phrase_sets) ),
        ("independent_short_positive_at_10pct",
         phrase_doc("sp", tuple(tuple(f"p{i}_{j}" for j in range(4)) for i in range(5)), 200, "sp"),
         phrase_doc("hp", tuple(tuple(f"p{i}_{j}" for j in range(4)) for i in range(5)), 200, "hp", reverse=True), True),
    ])
    for name, left, right, expected in cases:
        all_grams = left.fivegrams | right.fivegrams
        weights = {g: decimal.Decimal(1) for g in all_grams}
        observed = pair_decision(left, right, weights)
        # The below-0.80 case still blocks through substantive passage coverage;
        # its document-Jaccard boundary is asserted independently below.
        if name == "plain_jaccard_below_0_80":
            expected = True
        if observed["blocking"] is not expected:
            raise AssertionError(f"fixture failed: {name}")
        fixtures.append({"name": name, "expected_blocking": expected, "observed": observed})

    for name, left, right, reason, expected in (
        ("document_49_tokens_not_comparable",
         doc("s49", [tuple(f"d49_{i}" for i in range(49))]),
         doc("h49", [tuple([*(f"d49_{i}" for i in range(47)), "other_a", "other_b"])]),
         "document_plain_jaccard", False),
        ("document_50_tokens_comparable",
         doc("s50", [tuple(f"d50_{i}" for i in range(50))]),
         doc("h50", [tuple(f"d50_{i}" for i in range(50))]),
         "document_plain_jaccard", True),
        ("document_19_grams_not_comparable", cycle("s19", 19, 57, 0), cycle("h19", 19, 57, 1),
         "document_plain_jaccard", False),
        ("document_20_grams_comparable", cycle("s20", 20, 60, 0), cycle("h20", 20, 60, 1),
         "document_plain_jaccard", True),
        ("sentence_5_distinct_grams", cycle("s5g", 5, 10, 0), cycle("h5g", 5, 10, 1),
         "nonexact_substantive_sentence", False),
        ("sentence_6_distinct_grams", cycle("s6g", 6, 12, 0), cycle("h6g", 6, 12, 1),
         "nonexact_substantive_sentence", True),
    ):
        observed = pair_decision(left, right, {g: decimal.Decimal(1) for g in left.fivegrams | right.fivegrams})
        if (reason in observed["reasons"]) is not expected:
            raise AssertionError(f"reason-boundary fixture failed: {name}")
        fixtures.append({"name": name, "reason_under_test": reason,
                         "expected_reason_present": expected, "observed": observed})

    for name, common_tokens, expected in (("weighted_jaccard_exact_0_75", 46, True),
                                           ("weighted_jaccard_below_0_75", 45, False)):
        left = doc(name + "_s", [tuple(f"w{i}" for i in range(50))])
        right = doc(name + "_h", [tuple([*(f"w{i}" for i in range(common_tokens)),
                                           *(f"{name}_u{i}" for i in range(56 - common_tokens))])])
        observed = pair_decision(left, right, {g: decimal.Decimal(1) for g in left.fivegrams | right.fivegrams})
        present = "document_idf_jaccard" in observed["reasons"]
        if present is not expected:
            raise AssertionError(f"weighted-Jaccard boundary fixture failed: {name}")
        fixtures.append({"name": name, "reason_under_test": "document_idf_jaccard",
                         "expected_reason_present": expected, "observed": observed})

    # Pair-level short-sentence boundaries.  Unique separators ensure a
    # different reason cannot manufacture a shared flattened five-gram.
    short_boundary_specs = (
        ("short_members_4", tuple(tuple(f"sm{i}_{j}" for j in range(5)) for i in range(4)), 100, False),
        ("short_members_5", tuple(tuple(f"sa{i}_{j}" for j in range(4)) for i in range(5)), 100, True),
        ("short_tokens_19", tuple([*(tuple(f"st{i}_{j}" for j in range(4)) for i in range(4)),
                                   tuple(f"st4_{j}" for j in range(3))]), 100, False),
        ("short_fraction_below", tuple(tuple(f"sf{i}_{j}" for j in range(4)) for i in range(5)), 201, False),
        ("short_fraction_at", tuple(tuple(f"se{i}_{j}" for j in range(4)) for i in range(5)), 200, True),
    )
    for name, phrases, selected_total, expected in short_boundary_specs:
        left = phrase_doc(name + "_s", phrases, selected_total, name + "_s")
        right = phrase_doc(name + "_h", phrases, 300, name + "_h", reverse=True)
        observed = pair_decision(left, right, {g: decimal.Decimal(1) for g in left.fivegrams | right.fivegrams})
        if ("cumulative_short_sentences" in observed["reasons"]) is not expected:
            raise AssertionError(f"short pair-level boundary fixture failed: {name}")
        fixtures.append({"name": name + "_pair", "reason_under_test": "cumulative_short_sentences",
                         "expected_reason_present": expected, "observed": observed})

    # Four distinct shared five-grams at twenty disjoint selected positions,
    # plus the adjacent selected-oriented fraction boundary.
    passage_source_200 = tuple(f"pass{i}" for i in range(200))
    passage_source_201 = passage_source_200 + ("pass200",)
    for name, source, starts, expected in (
        ("passage_3_grams", passage_source_200, (0, 20, 40), False),
        ("passage_19_positions", passage_source_200, (0, 5, 10, 14), False),
        ("passage_20_positions_at_10pct", passage_source_200, (0, 20, 40, 60), True),
        ("passage_20_positions_below_10pct", passage_source_201, (0, 20, 40, 60), False),
    ):
        selected_sentences = ([source[i:i + 25] for i in range(0, len(source), 25)]
                              if name in {"passage_19_positions", "passage_20_positions_at_10pct"}
                              else [source])
        left, right = doc(name + "_selected", selected_sentences), passage_history(name + "_historical", source, starts)
        observed = pair_decision(left, right, {g: decimal.Decimal(1) for g in left.fivegrams | right.fivegrams})
        passage_reason = "shared_passage_coverage" in observed["reasons"]
        if passage_reason is not expected:
            raise AssertionError(f"passage fixture failed: {name}")
        fixtures.append({"name": name, "expected_passage_blocking": expected,
                         "multi_sentence_selected": len(selected_sentences) > 1, "observed": observed})

    # Occurrence invariance is tested with genuinely different multiplicities.
    repeat_selected = phrase_doc("repeat_s", (("alpha", "beta", "gamma", "delta"),
                                                ("one", "two", "three", "four"),
                                                ("red", "blue", "green", "gold"),
                                                ("north", "south", "east", "west"),
                                                ("cat", "dog", "bird", "fish")), 200, "rs")
    once = doc("repeat_once", [tuple(x) for x in repeat_selected.sentences[:9:2]] + [("history",)])
    hundred = doc("repeat_hundred", [sentence for sentence in once.sentences[:-1] for _ in range(100)] + [("history",)])
    once_decision = pair_decision(repeat_selected, once, {g: decimal.Decimal(1) for g in repeat_selected.fivegrams | once.fivegrams})
    hundred_decision = pair_decision(repeat_selected, hundred, {g: decimal.Decimal(1) for g in repeat_selected.fivegrams | hundred.fivegrams})
    invariant_fields = ("shared_short_member_count", "shared_short_token_count", "shared_short_tuple_set_sha256")
    if any(once_decision[key] != hundred_decision[key] for key in invariant_fields):
        raise AssertionError("repeated short-sentence occurrences changed the distinct-tuple gate")
    fixtures.append({"name": "short_repeat_1_vs_100_invariance", "expected_equal_fields": list(invariant_fields),
                     "once": {key: once_decision[key] for key in invariant_fields},
                     "hundred": {key: hundred_decision[key] for key in invariant_fields}})
    boundary = {
        "short_members_4": short_sentence_gate(4, 40, 100),
        "short_members_5": short_sentence_gate(5, 40, 100),
        "short_tokens_19": short_sentence_gate(5, 19, 100),
        "short_tokens_20": short_sentence_gate(5, 20, 100),
        "short_fraction_below": short_sentence_gate(5, 20, 201),
        "short_fraction_at": short_sentence_gate(5, 20, 200),
        "passage_grams_3": passage_coverage_gate(3, 20, 100),
        "passage_grams_4": passage_coverage_gate(4, 20, 100),
        "passage_positions_19": passage_coverage_gate(4, 19, 100),
        "passage_positions_20": passage_coverage_gate(4, 20, 100),
        "passage_fraction_below": passage_coverage_gate(4, 20, 201),
        "passage_fraction_at": passage_coverage_gate(4, 20, 200),
        "punctuation_only_lexical_tokens": list(lexical_tokens("... --- []")),
    }
    expected_boundary = {"short_members_4": False, "short_members_5": True,
                         "short_tokens_19": False, "short_tokens_20": True,
                         "short_fraction_below": False, "short_fraction_at": True,
                         "passage_grams_3": False, "passage_grams_4": True,
                         "passage_positions_19": False, "passage_positions_20": True,
                         "passage_fraction_below": False, "passage_fraction_at": True,
                         "punctuation_only_lexical_tokens": []}
    if boundary != expected_boundary:
        raise AssertionError("inclusive boundary fixture failure")
    by_name = {item["name"]: item for item in fixtures}
    for index, observed_name in enumerate(observed_names):
        observed = by_name[f"observed_v2_negative_{observed_name}"]["observed"]
        frozen = posthoc["rows"][index]
        if (observed["shared_short_member_count"] != frozen["distinct_tuple_count"]
                or observed["shared_short_token_count"] != frozen["unique_tuple_token_sum"]
                or observed["shared_short_tuple_set_sha256"] != frozen["shared_short_tuple_set_sha256"]
                or "cumulative_short_sentences" in observed["reasons"]):
            raise AssertionError(f"observed v2 regression fixture drift: {observed_name}")
    with decimal.localcontext(DECIMAL_CONTEXT):
        plain_below_expected = decimal.Decimal(43) / decimal.Decimal(56)
        weighted_below_expected = decimal.Decimal(41) / decimal.Decimal(57)
        passage_below_expected = decimal.Decimal(20) / decimal.Decimal(201)
    if by_name["plain_jaccard_exact_0_80"]["observed"]["plain_jaccard"] != "0.8":
        raise AssertionError("exact plain-Jaccard boundary did not land at 0.80")
    if (decimal.Decimal(by_name["plain_jaccard_below_0_80"]["observed"]["plain_jaccard"])
            != plain_below_expected
            or "document_plain_jaccard" in by_name["plain_jaccard_below_0_80"]["observed"]["reasons"]):
        raise AssertionError("below plain-Jaccard boundary did not land below 0.80")
    if ("document_plain_jaccard" not in by_name["plain_jaccard_exact_0_80"]["observed"]["reasons"]
            or by_name["weighted_jaccard_exact_0_75"]["observed"]["weighted_jaccard"] != "0.75"
            or "document_idf_jaccard" not in by_name["weighted_jaccard_exact_0_75"]["observed"]["reasons"]):
        raise AssertionError("exact weighted-Jaccard boundary did not land at 0.75")
    weighted_below = by_name["weighted_jaccard_below_0_75"]["observed"]
    if (decimal.Decimal(weighted_below["weighted_jaccard"]) != weighted_below_expected
            or "document_idf_jaccard" in weighted_below["reasons"]):
        raise AssertionError("below weighted-Jaccard boundary did not remain below 0.75")
    passage_at = by_name["passage_20_positions_at_10pct"]["observed"]
    passage_below = by_name["passage_20_positions_below_10pct"]["observed"]
    if (passage_at["selected_coverage"] != "0.1" or "shared_passage_coverage" not in passage_at["reasons"]
            or passage_below["selected_coverage"] != format(passage_below_expected, "f")
            or "shared_passage_coverage" in passage_below["reasons"]):
        raise AssertionError("passage fraction boundary fixture failure")
    return {"schema_version": "msae_v3_overlap_fixtures_v1", "protocol_id": PROTOCOL,
            "thresholds_inclusive": True, "fixture_count": len(fixtures),
            "fixtures": fixtures, "boundary_fixtures": boundary, "status": "eligible"}


def _fsync_directory(path: Path) -> None:
    fd = os.open(path, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


@contextlib.contextmanager
def quarantine_open_tripwire() -> Iterator[dict[str, Any]]:
    """Fail before any content-open surface reaches a quarantined payload."""
    forbidden = {os.path.realpath(ROOT / rel): rel for rel in QUARANTINED}
    state: dict[str, Any] = {
        "tripwire": "builtins.open+io.open+os.open_preopen_realpath_guard",
        "forbidden_paths": sorted(QUARANTINED),
        "blocked_content_open_attempts": [],
        "before_lstat": [_quarantine_entry(rel) for rel in sorted(QUARANTINED)],
    }
    original_builtin_open = builtins.open
    original_io_open = io.open
    original_os_open = os.open

    def checked_path(file: Any, *, dir_fd: int | None = None) -> None:
        if isinstance(file, int):
            return
        try:
            raw = os.fsdecode(os.fspath(file))
        except TypeError:
            return
        if os.path.isabs(raw):
            candidate = os.path.realpath(raw)
        elif dir_fd is not None:
            base = os.path.realpath(os.readlink(f"/proc/self/fd/{dir_fd}"))
            candidate = os.path.realpath(os.path.join(base, raw))
        else:
            candidate = os.path.realpath(raw)
        if candidate in forbidden:
            state["blocked_content_open_attempts"].append(forbidden[candidate])
            raise PermissionError(f"quarantined payload content open blocked: {forbidden[candidate]}")

    def guarded_builtin(file: Any, *args: Any, **kwargs: Any) -> Any:
        checked_path(file)
        return original_builtin_open(file, *args, **kwargs)

    def guarded_io(file: Any, *args: Any, **kwargs: Any) -> Any:
        checked_path(file)
        return original_io_open(file, *args, **kwargs)

    def guarded_os(file: Any, flags: int, mode: int = 0o777, *, dir_fd: int | None = None) -> int:
        checked_path(file, dir_fd=dir_fd)
        return original_os_open(file, flags, mode, dir_fd=dir_fd)

    builtins.open = guarded_builtin
    io.open = guarded_io
    os.open = guarded_os
    try:
        yield state
    finally:
        os.open = original_os_open
        io.open = original_io_open
        builtins.open = original_builtin_open


def _install_m1_transaction(payloads: Mapping[str, bytes]) -> None:
    expected_names = set(V3_DATA_PHASE_FILES["M1"])
    if set(payloads) != expected_names:
        raise ValueError("M1 transaction payload set mismatch")
    target_state = {name: (V3_DATA / name).exists() for name in expected_names}
    if not M1_TRANSACTION_ROOT.exists() and any(target_state.values()):
        if not all(target_state.values()):
            raise ValueError("orphaned partial M1 outputs without recovery transaction")
        for name, payload in payloads.items():
            path = V3_DATA / name
            if (path.is_symlink() or not path.is_file() or path.read_bytes() != payload
                    or stat.S_IMODE(path.stat().st_mode) != 0o644):
                raise ValueError(f"completed M1 output drift: {name}")
        return
    if not M1_TRANSACTION_ROOT.exists():
        provenance_parent = M1_TRANSACTION_ROOT.parent.parent
        parent_st = provenance_parent.lstat()
        if not stat.S_ISDIR(parent_st.st_mode) or stat.S_ISLNK(parent_st.st_mode):
            raise ValueError("M1 provenance parent is not a real directory")
        if not M1_TRANSACTION_ROOT.parent.exists():
            M1_TRANSACTION_ROOT.parent.mkdir(mode=0o700)
            os.chmod(M1_TRANSACTION_ROOT.parent, 0o700)
            _fsync_directory(provenance_parent)
        prov_st = M1_TRANSACTION_ROOT.parent.lstat()
        if (not stat.S_ISDIR(prov_st.st_mode) or stat.S_ISLNK(prov_st.st_mode)
                or stat.S_IMODE(prov_st.st_mode) != 0o700 or prov_st.st_uid != os.getuid()):
            raise ValueError("invalid M1 provenance directory")
        M1_TRANSACTION_ROOT.mkdir(mode=0o700)
        os.chmod(M1_TRANSACTION_ROOT, 0o700)
        _fsync_directory(M1_TRANSACTION_ROOT.parent)
    st = M1_TRANSACTION_ROOT.lstat()
    if (not stat.S_ISDIR(st.st_mode) or stat.S_ISLNK(st.st_mode)
            or stat.S_IMODE(st.st_mode) != 0o700 or st.st_uid != os.getuid()):
        raise ValueError("invalid M1 recovery transaction directory")
    allowed_transaction_names = {"transaction.json"} | {
        f"{ordinal:02d}.{name}.payload"
        for ordinal, name in enumerate(V3_DATA_PHASE_FILES["M1"])
    }
    observed_transaction_names = {entry.name for entry in os.scandir(M1_TRANSACTION_ROOT)}
    unexpected_transaction_names = observed_transaction_names - allowed_transaction_names
    if unexpected_transaction_names:
        raise ValueError(f"undeclared M1 transaction entries: {sorted(unexpected_transaction_names)}")
    entries = []
    for ordinal, name in enumerate(V3_DATA_PHASE_FILES["M1"]):
        payload = payloads[name]
        staged_name = f"{ordinal:02d}.{name}.payload"
        staged = M1_TRANSACTION_ROOT / staged_name
        if staged.exists():
            staged_st = staged.lstat()
            if (not stat.S_ISREG(staged_st.st_mode) or stat.S_ISLNK(staged_st.st_mode)
                    or stat.S_IMODE(staged_st.st_mode) != 0o600 or staged.read_bytes() != payload):
                raise ValueError(f"M1 staged recovery payload drift: {name}")
        else:
            write_once(staged, payload, 0o600)
        entries.append({"name": name, "staged_name": staged_name,
                        "size": len(payload), "sha256": sha_bytes(payload), "target_mode": 0o644})
    descriptor = canonical_bytes({
        "schema_version": "msae_v3_m1_recoverable_install_v1", "protocol_id": PROTOCOL,
        "entries": entries, "entry_count": len(entries),
        "payload_set_sha256": sha_bytes(canonical_bytes(entries)),
    })
    descriptor_path = M1_TRANSACTION_ROOT / "transaction.json"
    if descriptor_path.exists():
        if (descriptor_path.is_symlink() or descriptor_path.read_bytes() != descriptor
                or stat.S_IMODE(descriptor_path.stat().st_mode) != 0o600):
            raise ValueError("M1 transaction descriptor drift")
    else:
        write_once(descriptor_path, descriptor, 0o600)
    _fsync_directory(M1_TRANSACTION_ROOT)
    for name in V3_DATA_PHASE_FILES["M1"]:
        target = V3_DATA / name
        payload = payloads[name]
        if target.exists():
            target_st = target.lstat()
            if (not stat.S_ISREG(target_st.st_mode) or stat.S_ISLNK(target_st.st_mode)
                    or stat.S_IMODE(target_st.st_mode) != 0o644 or target.read_bytes() != payload):
                raise ValueError(f"M1 target drift during recovery: {name}")
        else:
            write_once(target, payload, 0o644)
    _fsync_directory(V3_DATA)
    for name, payload in payloads.items():
        target = V3_DATA / name
        if target.read_bytes() != payload or sha_file(target) != sha_bytes(payload):
            raise AssertionError(f"M1 installed-byte verification failed: {name}")
    # Cleanup is itself recoverable: if interrupted, the next invocation
    # reconstructs any missing staged files from the fully recomputed payloads.
    descriptor_path.unlink()
    for entry in entries:
        (M1_TRANSACTION_ROOT / entry["staged_name"]).unlink()
    M1_TRANSACTION_ROOT.rmdir()
    _fsync_directory(M1_TRANSACTION_ROOT.parent)


def _overlap_candidate_key(selected_index: int, historical: TextDocument) -> tuple[int, str, int, str]:
    return (selected_index, historical.path, historical.record_index, historical.source_id)


def _build_overlap_impl(reviewed_m0_sha256: str, quarantine_state: dict[str, Any]) -> dict[str, Any]:
    recovering = M1_TRANSACTION_ROOT.exists() or any((V3_DATA / name).exists()
                                                      for name in V3_DATA_PHASE_FILES["M1"])
    verify_m0_completion(reviewed_m0_sha256,
                         projection_phase="M1_RECOVERY" if recovering else "M0")
    selected, aliases = selected_documents()
    alias_payload = {
        "schema_version": "msae_v3_source_alias_manifest_v1", "protocol_id": PROTOCOL,
        "selected_count": len(aliases), "root_file_count": len(aliases) + 2, "entries": aliases,
    }
    fixture_payload = build_overlap_fixtures()
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
    candidates: dict[tuple[int, str, int, str], TextDocument] = {}
    history_count = 0
    adapter_counts = collections.Counter()
    exact_flat = {doc.flat_sha256: i for i, doc in enumerate(selected)}
    exact_aware = {doc.aware_sha256: i for i, doc in enumerate(selected)}
    schema_census: list[dict[str, Any]] = []
    for hist, meta in iter_history(audit_events=schema_census):
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
            key = _overlap_candidate_key(si, hist)
            prior = candidates.get(key)
            if prior is not None and (prior.aware_sha256, prior.flat_sha256) != (hist.aware_sha256, hist.flat_sha256):
                raise ValueError(f"conflicting overlap candidate identity: {key}")
            candidates[key] = hist
    relevant = set()
    for (si, _, _, _), hist in candidates.items():
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
    for (si, _, _, _), hist in sorted(candidates.items(), key=lambda x: x[0]):
        decision = pair_decision(selected[si], hist, weights)
        record = {"selected_path": selected[si].path, "selected_document_id": selected[si].source_id,
                  "historical_path": hist.path, "historical_document_id": hist.source_id,
                  "historical_record_index": hist.record_index,
                  "historical_source_record_indices": list(hist.source_record_indices or (hist.record_index,)),
                  **decision}
        (collisions if decision["blocking"] else diagnostics).append(record)
    quarantine_after = [_quarantine_entry(rel) for rel in sorted(QUARANTINED)]
    if quarantine_after != quarantine_state["before_lstat"]:
        raise ValueError("quarantined payload metadata changed during M1 scan")
    quarantine_evidence = {
        "tripwire": quarantine_state["tripwire"],
        "forbidden_paths": quarantine_state["forbidden_paths"],
        "blocked_content_open_attempt_count": len(quarantine_state["blocked_content_open_attempts"]),
        "before_lstat": quarantine_state["before_lstat"], "after_scan_lstat": quarantine_after,
        "comparison_fields": ["type", "mode", "size", "device", "inode", "nlink", "ctime_ns",
                              "mtime_ns", "frozen_v1_sha256"],
        "content_reads": 0,
    }
    census = {
        "schema_version": "msae_v3_history_census_v1", "protocol_id": PROTOCOL,
        "selected_documents": len(selected), "historical_documents": history_count,
        "idf_universe_documents": universe, "candidate_pairs": len(candidates),
        "relevant_gram_count": len(relevant), "adapter_document_counts": dict(sorted(adapter_counts.items())),
        "schema_census": schema_census,
        "quarantine_audit": quarantine_evidence, "sealed_payload_content_reads": 0,
    }
    result = {
        "schema_version": "msae_v3_history_overlap_v1", "protocol_id": PROTOCOL,
        "source_disposition": "unchanged_exposed_source_technical_replication",
        "status": "eligible" if not collisions else "ineligible",
        "blocking_collision_count": len(collisions), "blocking_collisions": collisions,
        "nonblocking_candidate_diagnostics": diagnostics,
        "idf_universe_documents": universe,
        "idf_weight_payload_sha256": sha_bytes(canonical_bytes([
            [base64.b16encode(k).decode("ascii"), v, format(weights[k], "f")] for k, v in sorted(df.items())
        ])),
        "quarantine_audit": quarantine_evidence, "sealed_payload_content_reads": 0,
    }
    legacy_path = ROOT / "reports/provenance/msae_independent_measurement_v1/history_overlap.json"
    legacy = read_json(legacy_path)
    legacy_rows = legacy.get("blocking_collisions", [])
    visible_counts = collections.Counter(canonical_bytes(item) for item in legacy_rows)
    seen_visible = collections.Counter()
    rows = []
    for ordinal, item in enumerate(legacy_rows):
        encoded = canonical_bytes(item)
        occurrence = seen_visible[encoded]
        seen_visible[encoded] += 1
        rows.append({"legacy_index": ordinal, "legacy_row": item,
                     "legacy_visible_signature_sha256": sha_bytes(encoded),
                     "legacy_visible_signature_occurrence_ordinal": occurrence,
                     "legacy_visible_signature_multiplicity": visible_counts[encoded],
                     "v3_namespace": PROTOCOL,
                     "v3_diagnostic": "legacy_row_has_no_frozen_record_or_sentence_identity;v3_reaudits_independently"})
    if len(rows) != 206:
        raise ValueError("frozen v1 overlap row cardinality drift")
    crosswalk = {
        "schema_version": "v3_visible_legacy_row_crosswalk_v1", "protocol_id": PROTOCOL,
        "legacy_status": legacy["status"], "legacy_row_count": len(rows), "rows": rows,
        "legacy_artifact_path": str(legacy_path.relative_to(ROOT)),
        "legacy_artifact_sha256": sha_file(legacy_path),
        "legacy_rows_preserved_verbatim": True,
        "exact_v1_identity_replay_available": False,
        "reason": "the_frozen_v1_rows_and_owned_bytes_do_not_contain_the_generator_or_record_sentence_ids",
        "v3_overlap_result_sha256": sha_bytes(canonical_bytes(result)),
    }
    payloads = {
        "source_alias_manifest.json": canonical_bytes(alias_payload),
        "overlap_fixtures.json": canonical_bytes(fixture_payload),
        "history_census.json": canonical_bytes(census),
        "history_overlap.json": canonical_bytes(result),
        "v1_row_crosswalk.json": canonical_bytes(crosswalk),
    }
    _install_m1_transaction(payloads)
    verify_baseline_projection("M1")
    verify_m0_completion(reviewed_m0_sha256, projection_phase="M1")
    for name, payload in payloads.items():
        if (V3_DATA / name).read_bytes() != payload:
            raise AssertionError(f"M1 post-install byte drift: {name}")
    return result


def build_overlap(reviewed_m0_sha256: str) -> dict[str, Any]:
    with quarantine_open_tripwire() as quarantine_state:
        return _build_overlap_impl(reviewed_m0_sha256, quarantine_state)


def build_v2_posthoc_analysis() -> dict[str, Any]:
    validate_source_exposure()
    before = verify_protected_v2()
    v2_path = ROOT / "data/msae_independent_measurement_v2/history_overlap.json"
    v2 = read_json(v2_path)
    if v2.get("status") != "ineligible" or v2.get("blocking_collision_count") != 4:
        raise ValueError("frozen v2 overlap result drift")
    rows = []
    for index, collision in enumerate(v2["blocking_collisions"]):
        selected_path = ROOT / collision["selected_path"]
        historical_path = ROOT / collision["historical_path"]
        selected = conllu_text_documents(selected_path, collision["selected_path"])
        historical = conllu_text_documents(historical_path, collision["historical_path"])
        selected_doc = next(x for x in selected if x.source_id == collision["selected_document_id"])
        historical_doc = historical[collision["historical_record_index"]]
        shared = sorted({x for x in selected_doc.sentences if 0 < len(x) < 10} &
                        {x for x in historical_doc.sentences if 0 < len(x) < 10}, key=typed_tuple)
        token_sum = sum(map(len, shared))
        if (len(shared) != collision["shared_short_member_count"]
                or token_sum != collision["shared_short_token_count"]
                or len(selected_doc.tokens) != collision["selected_tokens"]
                or len(historical_doc.tokens) != collision["historical_tokens"]
                or collision["reasons"] != ["cumulative_short_sentences"]):
            raise ValueError(f"v2 collision {index} does not reproduce from its frozen identities")
        rows.append({
            "v2_collision_index": index,
            "selected_path": collision["selected_path"],
            "selected_document_id": collision["selected_document_id"],
            "historical_path": collision["historical_path"],
            "historical_document_id": collision["historical_document_id"],
            "historical_record_index": collision["historical_record_index"],
            "v2_reasons": collision["reasons"],
            "frozen_v2_collision_sha256": sha_bytes(canonical_bytes(collision)),
            "v2_plain_jaccard": collision["plain_jaccard"],
            "v2_weighted_jaccard": collision["weighted_jaccard"],
            "shared_short_tuples": [{"tokens": list(item), "typed_tuple_hex": typed_tuple(item).hex(),
                                      "typed_tuple_sha256": sha_bytes(typed_tuple(item))} for item in shared],
            "shared_short_tuple_set_sha256": sha_bytes(b"".join(struct.pack(">Q", len(typed_tuple(x))) + typed_tuple(x) for x in shared)),
            "distinct_tuple_count": len(shared), "unique_tuple_token_sum": token_sum,
            "selected_token_count": len(selected_doc.tokens),
            "exact_fraction": f"{token_sum}/{len(selected_doc.tokens)}",
            "v3_integer_fraction_gate": 10 * token_sum >= len(selected_doc.tokens),
            "interpretation": "posthoc_motivating_boilerplate_regression_not_independent_validation",
        })
    if any(row["v3_integer_fraction_gate"] for row in rows):
        raise AssertionError("observed v2 negatives do not pass the prospective v3 regression")
    result = {
        "schema_version": "msae_v3_v2_posthoc_boilerplate_analysis_v1", "protocol_id": PROTOCOL,
        "frozen_v2_history_overlap_path": str(v2_path.relative_to(ROOT)),
        "frozen_v2_history_overlap_sha256": sha_file(v2_path),
        "analysis_code_path": str(Path(__file__).relative_to(ROOT)),
        "analysis_code_sha256": sha_file(Path(__file__)),
        "rows": rows, "row_count": len(rows), "sealed_payload_content_reads": 0,
        "protected_v2_entry_count_before": before,
        "disposition": "motivating_regressions_only",
    }
    after = verify_protected_v2()
    if after != before:
        raise AssertionError("protected v2 manifest changed during post-hoc analysis")
    result["protected_v2_entry_count_after"] = after
    install_json(V3_DATA / "v2_posthoc_boilerplate_analysis.json", result)
    verify_baseline_projection("M0_INPUTS")
    return result


M0_REVIEW_PATHS = (
    "docs/rfc-msae-independent-measurement-v3.md",
    "scripts/msae_independent_measurement_v3.py",
    "tests/test_msae_independent_measurement_v3.py",
)


def _m0_completion_payload() -> dict[str, Any]:
    verify_protected_v1()
    verify_protected_v2()
    validate_source_exposure()
    posthoc = read_json(V3_DATA / "v2_posthoc_boilerplate_analysis.json")
    if (posthoc.get("schema_version") != "msae_v3_v2_posthoc_boilerplate_analysis_v1"
            or posthoc.get("protocol_id") != PROTOCOL or posthoc.get("row_count") != 4
            or posthoc.get("sealed_payload_content_reads") != 0
            or posthoc.get("analysis_code_sha256") != sha_file(Path(__file__))):
        raise ValueError("v2 posthoc semantic/code binding mismatch")
    artifact_paths = [V3_DATA / name for name in M0_INPUT_NAMES]
    review_paths = [ROOT / rel for rel in M0_REVIEW_PATHS]
    entries = [_content_entry(path) for path in [*artifact_paths, *review_paths]]
    if any(entry["type"] != "regular" for entry in entries):
        raise ValueError("M0 completion may bind only regular non-symlink files")
    return {
        "schema_version": "msae_v3_m0_completion_manifest_v1", "protocol_id": PROTOCOL,
        "m0_artifact_names": list(M0_INPUT_NAMES), "review_input_paths": list(M0_REVIEW_PATHS),
        "entries": entries, "entry_count": len(entries),
        "entries_sha256": sha_bytes(canonical_bytes(entries)),
        "protected_v1_entry_count": 372, "protected_v2_entry_count": 14,
        "quarantined_payload_content_reads": 0,
        "status": "m0_complete_ready_for_independent_review_pin",
    }


def build_m0_completion() -> dict[str, Any]:
    verify_baseline_projection("M0_INPUTS")
    payload = _m0_completion_payload()
    install_json(V3_DATA / "m0_completion_manifest.json", payload)
    verify_baseline_projection("M0")
    return payload


def verify_m0_completion(expected_sha256: str, *, projection_phase: str = "M0") -> dict[str, Any]:
    validate_sha256(expected_sha256, "reviewed M0 completion SHA-256")
    path = V3_DATA / "m0_completion_manifest.json"
    if sha_file(path) != expected_sha256:
        raise ValueError("reviewed M0 completion digest mismatch")
    observed = read_json(path)
    verify_baseline_projection(projection_phase)
    expected = _m0_completion_payload()
    if observed != expected or canonical_bytes(observed) != path.read_bytes():
        raise ValueError("M0 completion manifest semantic/canonical mismatch")
    return observed


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
    verify_baseline_projection("M1")
    # Tokenizer only: offline local path, no torch/model import and no GPU access.
    from transformers import AutoTokenizer
    tokenizer = AutoTokenizer.from_pretrained(str(SNAPSHOT), local_files_only=True)
    prefix_ids = [list(tokenizer(prefix, add_special_tokens=False)["input_ids"]) for prefix in PREFIXES]
    lengths = [len(x) for x in prefix_ids]
    if len(set(lengths)) != 4:
        raise ValueError(f"prefix token lengths are not distinct: {lengths}")
    templates = {
        "schema_version": "msae_v3_prefix_templates_v1", "protocol_id": PROTOCOL,
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
    row_path = V3_DATA / "label_rows.jsonl"
    row_path.parent.mkdir(parents=True, exist_ok=True)
    fd = os.open(row_path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o644)
    os.fchmod(fd, 0o644)
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
                        "schema_version": "msae_v3_label_row_v1", "protocol_id": PROTOCOL,
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
        "schema_version": "msae_v3_task_manifest_v1", "protocol_id": PROTOCOL,
        "tasks": list(TASKS), "roles": list(ROLES),
        "token_vocabulary": token_vocab, "lemma_vocabulary": lemma_vocab,
        "source_applicability": {
            "all": list(TASKS[:9]) + ["source_genre"],
            "ud_or_amalgum": list(TASKS[9:14]), "ner_or_amalgum": list(TASKS[14:16]),
        },
        "label_rows": output_count,
    }
    install_json(V3_DATA / "prefix_templates.json", templates)
    install_json(V3_DATA / "task_manifest.json", task_manifest)
    install_json(V3_DATA / "support.json", {
        "schema_version": "msae_v3_support_v1", "protocol_id": PROTOCOL,
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
    prefix_lengths = [len(item["token_ids"]) for item in read_json(V3_DATA / "prefix_templates.json")["templates"]]
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
        "schema_version": "msae_v3_bootstrap_maps_v1", "protocol_id": PROTOCOL,
        "date_salt": DATE, "draws_per_role_task": 500,
        "map_entries": entries,
    }
    matrix = {
        "schema_version": "msae_v3_finite_pass_matrix_v1", "protocol_id": PROTOCOL,
        "minimum_finite_draws": 490, "status": status, "finite_draw_counts": pass_counts,
        "map_payload_sha256": sha_bytes(canonical_bytes(maps)),
        "golden_chance": {"counts": [2, 1], "chance_macro_f1": "2/5", "denominator": "3/5"},
    }
    install_json(V3_DATA / "maps.json", maps)
    install_json(V3_DATA / "finite_pass_matrix.json", matrix)
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
        "schema_version": "msae_v3_protocol_imports_v1", "protocol_id": PROTOCOL,
        "source_path": "docs/rfc-msae-independent-measurement-v1.md",
        "source_sha256": sha_bytes(raw), "imports": entries,
        "v3_supersedes": ["v1_label_schema", "v1_parser_schema", "v1_support_schema", "v1_map_schema", "v1_absolute_bucket_cardinality"],
    }
    install_json(V3_DATA / "protocol_imports.json", result)
    verify_baseline_projection("M2")
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
    verify_baseline_projection("M2")
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
    write_once(V3_CONFIG / "ed25519_public.pem", public_bytes)
    if STATE_ROOT.exists():
        _secure_directory(STATE_ROOT, create=False)
    else:
        STATE_ROOT.mkdir(mode=0o700)
        _secure_directory(STATE_ROOT, create=False)
    protocol_state = STATE_ROOT / "independent_measurement_v3"
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
        "schema_version": "msae_v3_authorization_commitment_v1", "protocol_id": PROTOCOL,
        "operator_instruction": operator_instruction,
        "operator_instruction_sha256": sha_bytes(operator_instruction.encode("utf-8")),
        "public_key_path": "configs/msae_independent_measurement_v3/ed25519_public.pem",
        "public_key_sha256": sha_bytes(public_bytes),
        "public_key_fingerprint": sha_bytes(public_bytes),
        "private_key_binding": {"path": str(PRIVATE_KEY), "device": st.st_dev, "inode": st.st_ino,
                                "uid": st.st_uid, "mode": stat.S_IMODE(st.st_mode), "nlink": st.st_nlink,
                                "public_key_match": True},
        "algorithm": "Ed25519", "envelope_schema": "msae_v3_signed_authorization_v1",
        "allowed_scope": "calibration_replay_only", "maximum_lifetime_seconds": 86400,
        "nonce_directory": _directory_binding(NONCE_DIR),
        "gpu_lock_directory": _directory_binding(GPU_LOCK_DIR),
        "contains_execution_authorization": False,
    }
    install_json(V3_CONFIG / "authorization_commitment.json", commitment)
    return commitment


def verify_authorization(envelope_path: Path, *, consume: bool, run_root: Path | None = None) -> dict[str, Any]:
    from cryptography.hazmat.primitives import serialization
    commitment_path = V3_CONFIG / "authorization_commitment.json"
    commitment = read_json(commitment_path)
    envelope = read_json(envelope_path)
    signature = base64.b64decode(envelope.pop("signature_b64"), validate=True)
    signed = canonical_bytes(envelope)
    public_bytes = (V3_CONFIG / "ed25519_public.pem").read_bytes()
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
    stage_path = V3_PROV / "stage_a.json"
    if envelope.get("stage_a_sha256") != sha_file(stage_path):
        raise ValueError("authorization Stage-A mismatch")
    if envelope.get("operator_instruction_sha256") != commitment["operator_instruction_sha256"]:
        raise ValueError("authorization operator mismatch")
    if envelope.get("protocol_config_sha256") != sha_file(V3_CONFIG / "protocol.json"):
        raise ValueError("authorization protocol-config mismatch")
    if envelope.get("dependency_closure_sha256") != sha_file(V3_DATA / "dependency_closure.json"):
        raise ValueError("authorization dependency-closure mismatch")
    if envelope.get("review_verdict") != "SHIP":
        raise ValueError("authorization review verdict mismatch")
    review_digest = sha_file(V3_REVIEW)
    if envelope.get("review_sha256") != review_digest:
        raise ValueError("authorization review mismatch")
    now = int(time.time())
    issued, expires = envelope.get("issued_unix"), envelope.get("expires_unix")
    if (type(issued) is not int or type(expires) is not int or not issued <= now <= expires
            or expires - issued <= 0 or expires - issued > commitment["maximum_lifetime_seconds"]):
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
                os.fchmod(fd, 0o600)
                payload = canonical_bytes({"schema_version": "msae_v3_nonce_consumed_v1",
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
            path_stat = record_path.lstat()
            if ((record_stat.st_dev, record_stat.st_ino) != (path_stat.st_dev, path_stat.st_ino)
                    or not stat.S_ISREG(record_stat.st_mode) or stat.S_ISLNK(path_stat.st_mode)
                    or stat.S_IMODE(record_stat.st_mode) != 0o600 or record_stat.st_uid != os.getuid()
                    or record_stat.st_nlink != 1):
                raise ValueError("nonce record path/FD/type/ownership binding invalid")
        finally:
            os.close(directory_fd)
        if run_root is not None:
            install_json(run_root / "nonce_consumed.json", {
                "schema_version": "msae_v3_nonce_attestation_v1", "record_path": str(record_path),
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
    verify_candidate_manifest("post_review")
    commitment = read_json(V3_CONFIG / "authorization_commitment.json")
    if RUN_ROOT.exists():
        raise ValueError("run root must be absent before signing")
    if any(NONCE_DIR.iterdir()):
        raise ValueError("nonce directory must be empty before signing")
    private_stat = PRIVATE_KEY.lstat()
    expected_private = commitment["private_key_binding"]
    if (not stat.S_ISREG(private_stat.st_mode) or stat.S_ISLNK(private_stat.st_mode)
            or private_stat.st_dev != expected_private["device"]
            or private_stat.st_ino != expected_private["inode"]
            or private_stat.st_uid != expected_private["uid"]
            or private_stat.st_nlink != expected_private["nlink"]
            or stat.S_IMODE(private_stat.st_mode) != expected_private["mode"]):
        raise ValueError("private-key object binding drift")
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
        "scope": "calibration_replay_only", "commitment_sha256": sha_file(V3_CONFIG / "authorization_commitment.json"),
        "stage_a_sha256": sha_file(V3_PROV / "stage_a.json"),
        "protocol_config_sha256": sha_file(V3_CONFIG / "protocol.json"),
        "dependency_closure_sha256": sha_file(V3_DATA / "dependency_closure.json"),
        "operator_instruction_sha256": commitment["operator_instruction_sha256"],
        "review_sha256": sha_file(V3_REVIEW), "review_verdict": "SHIP",
        "nonce": nonce, "issued_unix": issued, "expires_unix": issued + 86400,
    }
    signed = canonical_bytes(envelope)
    signature = private.sign(signed)
    output = {**envelope, "signature_b64": base64.b64encode(signature).decode("ascii")}
    RUN_ROOT.mkdir(mode=0o700, parents=False)
    os.chmod(RUN_ROOT, 0o700)
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
        "schema_version": "msae_v3_endpoint_registry_v1", "protocol_id": PROTOCOL,
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
    runner_sha = sha_file(ROOT / "scripts/run_msae_independent_calibration_v3.py")
    module_sha = sha_file(Path(__file__))
    launcher_sha = sha_file(ROOT / "scripts/launch_msae_independent_calibration_v3.sh")
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
    install_json(V3_CONFIG / "protocol.json", config)
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
        ROOT / "docs/rfc-msae-independent-measurement-v3.md", ROOT / "docs/rfc-msae-independent-measurement-v1.md",
        ROOT / "TODO.md", ROOT / "scripts/msae_independent_measurement_v3.py",
        ROOT / "scripts/run_msae_independent_calibration_v3.py", ROOT / "scripts/launch_msae_independent_calibration_v3.sh",
        ROOT / "scripts/msae_measurement_remediation_v1.py", ROOT / "scripts/msae_measurement_v2.py",
        ROOT / "tests/test_msae_independent_measurement_v3.py",
        V3_CONFIG / "protocol.json", V3_CONFIG / "authorization_commitment.json", V3_CONFIG / "ed25519_public.pem",
        ROOT / "reports/provenance/msae_independent_measurement_v1/status.json",
        ROOT / "reports/provenance/msae_independent_measurement_v1/history_overlap.json",
        ROOT / "data/msae_independent_measurement_v1/calibration_strata.json",
        ROOT / "data/atlas_measurement_v2_4/prepared/calibration/inference_units.jsonl",
        ROOT / "data/atlas_measurement_v2_4/prepared/calibration/pairs.jsonl",
        ROOT / "data/atlas_v1/partitions/discovery.records.jsonl", ROOT / "data/atlas_v1/partitions/discovery.units.jsonl",
        ROOT / "data/atlas_v1/partitions/calibration.records.jsonl", ROOT / "data/atlas_v1/partitions/calibration.units.jsonl",
    ]
    for name in ("data_baseline_manifest", "protected_v1_manifest", "protected_v2_manifest", "source_exposure",
                 "v2_posthoc_boilerplate_analysis", "source_alias_manifest",
                 "overlap_fixtures", "history_census", "history_overlap", "v1_row_crosswalk", "task_manifest",
                 "support", "prefix_templates", "maps", "finite_pass_matrix", "protocol_imports"):
        local_paths.append(V3_DATA / f"{name}.json")
    local_paths.append(V3_DATA / "label_rows.jsonl")
    for item in checkpoints:
        local_paths.extend([ROOT / item["checkpoint_path"], ROOT / item["summary_path"], ROOT / item["metrics_path"]])
    alias_manifest = read_json(V3_DATA / "source_alias_manifest.json")
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
        "schema_version": "msae_v3_dependency_closure_v1", "protocol_id": PROTOCOL,
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
            "external_write_roots": [str(PRIVATE_KEY.parent), str(STATE_ROOT), "/tmp/msae_independent_measurement_v3_build_primary",
                                     "/tmp/msae_independent_measurement_v3_build_rebuild", str(RUN_ROOT)],
        },
        "runtime_policy": {"deterministic_algorithms": True, "tf32": False, "model_dtype": "float16",
                           "cache_dtype": "float32", "layer": 3,
                           "pooling": "registered_first_subtoken_rows",
                           "gpu_uuid_discovered_only_after_prescore_ship": True},
        "protocol_config_sha256": sha_file(V3_CONFIG / "protocol.json"),
        "authorization_commitment_sha256": sha_file(V3_CONFIG / "authorization_commitment.json"),
    }


def verify_dependency_closure() -> dict[str, Any]:
    path = V3_DATA / "dependency_closure.json"
    observed = read_json(path)
    if observed.get("schema_version") != "msae_v3_dependency_closure_v1" or observed.get("protocol_id") != PROTOCOL:
        raise ValueError("dependency closure schema/protocol mismatch")
    expected = closure_payload(checkpoint_registry())
    if canonical_bytes(observed) != canonical_bytes(expected):
        raise ValueError("dependency closure does not reproduce from current bytes")
    return observed


def environment_payload(closure: Mapping[str, Any]) -> dict[str, Any]:
    commitment = read_json(V3_CONFIG / "authorization_commitment.json")
    return {
        "schema_version": "msae_v3_environment_allowlist_v1", "protocol_id": PROTOCOL,
        "python_executable": closure["python_executable"], "python_version": closure["python_version"],
        "dependency_closure_payload_sha256": sha_bytes(canonical_bytes(closure)),
        "deterministic_algorithms": True, "allow_tf32": False,
        "model_revision": SNAPSHOT.name, "model_dtype": "float16", "cache_dtype": "float32",
        "layer": 3, "maximum_sequence_length": 128,
        "nonce_directory": commitment["nonce_directory"], "gpu_lock_directory": commitment["gpu_lock_directory"],
        "offline_environment": {"TRANSFORMERS_OFFLINE": "1", "HF_HUB_OFFLINE": "1", "CUDA_CACHE_DISABLE": "1"},
    }


_TYPED_STAGE_A_PATHS = (
    "data/msae_independent_measurement_v3/data_baseline_manifest.json",
    "data/msae_independent_measurement_v3/protected_v1_manifest.json",
    "data/msae_independent_measurement_v3/protected_v2_manifest.json",
    "data/msae_independent_measurement_v3/source_exposure.json",
    "data/msae_independent_measurement_v3/v2_posthoc_boilerplate_analysis.json",
    "data/msae_independent_measurement_v3/source_alias_manifest.json",
    "data/msae_independent_measurement_v3/overlap_fixtures.json",
    "data/msae_independent_measurement_v3/history_census.json",
    "data/msae_independent_measurement_v3/history_overlap.json",
    "data/msae_independent_measurement_v3/v1_row_crosswalk.json",
    "data/msae_independent_measurement_v3/label_rows.jsonl",
    "data/msae_independent_measurement_v3/task_manifest.json",
    "data/msae_independent_measurement_v3/support.json",
    "data/msae_independent_measurement_v3/prefix_templates.json",
    "data/msae_independent_measurement_v3/maps.json",
    "data/msae_independent_measurement_v3/finite_pass_matrix.json",
    "data/msae_independent_measurement_v3/protocol_imports.json",
    "data/msae_independent_measurement_v3/dependency_closure.json",
    "data/msae_independent_measurement_v3/endpoint_registry.json",
    "data/msae_independent_measurement_v3/environment_allowlist.json",
    "configs/msae_independent_measurement_v3/protocol.json",
    "configs/msae_independent_measurement_v3/authorization_commitment.json",
    "configs/msae_independent_measurement_v3/ed25519_public.pem",
)


def _overlay_path(relative: str, overlay_root: Path | None) -> Path:
    if overlay_root is not None:
        candidate = overlay_root / relative
        if candidate.exists():
            return candidate
    return ROOT / relative


def stage_a_payload(*, overlay_root: Path | None = None) -> dict[str, Any]:
    from msae_measurement_remediation_v1 import build_stage_a
    verify_baseline_projection("M4" if overlay_root is None else "M2")
    verify_protected_v1()
    verify_protected_v2()
    validate_source_exposure()
    posthoc = read_json(V3_DATA / "v2_posthoc_boilerplate_analysis.json")
    if (posthoc.get("schema_version") != "msae_v3_v2_posthoc_boilerplate_analysis_v1"
            or posthoc.get("row_count") != 4 or posthoc.get("disposition") != "motivating_regressions_only"):
        raise ValueError("v2 post-hoc analysis semantic mismatch")
    config_path = V3_CONFIG / "protocol.json"
    raw = config_path.read_bytes()
    config_sha = sha_bytes(raw)
    overlap = read_json(V3_DATA / "history_overlap.json")
    support = read_json(V3_DATA / "support.json")
    matrix = read_json(V3_DATA / "finite_pass_matrix.json")
    eligible = overlap["status"] == "eligible" and support["status"] == "eligible" and matrix["status"] == "eligible"
    artifact_relatives = {
        "candidate_confirmation_source": "data/msae_independent_measurement_v3/history_overlap.json",
        "immutable_source_revision": "data/msae_independent_measurement_v3/source_alias_manifest.json",
        "independent_grouping_provenance": "data/msae_independent_measurement_v3/v1_row_crosswalk.json",
        "label_support_audit": "data/msae_independent_measurement_v3/support.json",
        "construct_inventory": "data/msae_independent_measurement_v3/endpoint_registry.json",
        "counterfactual_template_specification": "data/msae_independent_measurement_v3/prefix_templates.json",
        "tolerance_ladder_frozen": "configs/msae_independent_measurement_v3/protocol.json",
        "dependency_attestation": "data/msae_independent_measurement_v3/dependency_closure.json",
    }
    evidence = {}
    for name, relative in artifact_relatives.items():
        path = _overlay_path(relative, overlay_root)
        status = "eligible" if (eligible or name not in {"candidate_confirmation_source", "independent_grouping_provenance", "label_support_audit"}) else "ineligible"
        evidence[name] = {
            "schema_version": "msae_endpoint_evidence_v1", "protocol_config_sha256": config_sha,
            "endpoint_name": name, "category": "stage_a", "status": status,
            "reasons": [] if status == "eligible" else ["typed_v3_gate_ineligible"],
            "evidence_artifact_sha256": sha_file(path),
            "observed_value": {"artifact_path": relative, "artifact_sha256": sha_file(path),
                               "source_revision": read_json(ROOT / "data/msae_independent_measurement_v1/source_partition.json")["source_revision"],
                               "partition_sha256": sha_file(V3_DATA / "source_alias_manifest.json")},
        }
    base = build_stage_a(raw, config_sha, evidence)
    typed = {rel: sha_file(_overlay_path(rel, overlay_root)) for rel in _TYPED_STAGE_A_PATHS}
    return {
        "schema_version": "msae_exposed_source_stage_a_v3", "protocol_id": PROTOCOL,
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
    path = V3_PROV / "stage_a.json"
    stage = read_json(path)
    if stage.get("schema_version") != "msae_exposed_source_stage_a_v3" or stage.get("protocol_id") != PROTOCOL:
        raise ValueError("not a v3 wrapper Stage A")
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


def _candidate_paths(*, overlay_root: Path | None = None) -> list[Path]:
    paths = [ROOT / "docs/rfc-msae-independent-measurement-v3.md", ROOT / "TODO.md",
             ROOT / "scripts/msae_independent_measurement_v3.py", ROOT / "scripts/run_msae_independent_calibration_v3.py",
             ROOT / "scripts/launch_msae_independent_calibration_v3.sh", ROOT / "tests/test_msae_independent_measurement_v3.py",
             V3_CONFIG / "protocol.json", V3_CONFIG / "authorization_commitment.json", V3_CONFIG / "ed25519_public.pem"]
    observed_names = {x.name for x in V3_DATA.iterdir()}
    expected_names = set(V3_DATA_ALL_FILES if overlay_root is None else _phase_data_names("M2"))
    if observed_names != expected_names:
        raise ValueError(f"v3 data candidate set mismatch: missing={sorted(expected_names-observed_names)}, "
                         f"extra={sorted(observed_names-expected_names)}")
    paths.extend(V3_DATA / name for name in V3_DATA_ALL_FILES)
    paths.extend([V3_PROV / "stage_a.json", V3_PROV / "status.json"])
    return paths


def _logical_content_entry(path: Path, overlay_root: Path | None) -> dict[str, Any]:
    relative = path.relative_to(ROOT).as_posix()
    actual = _overlay_path(relative, overlay_root)
    entry = _content_entry(actual, root=overlay_root if overlay_root is not None and actual.is_relative_to(overlay_root) else ROOT)
    entry["path"] = relative
    # Realpaths are meaningful only for symlinks.  M4 outputs are prohibited
    # from being symlinks, and pre-M4 symlink targets remain canonical.
    return entry


def build_candidate_manifest(*, overlay_root: Path | None = None,
                             repository_status: list[str] | None = None) -> dict[str, Any]:
    candidate_files = [_logical_content_entry(path, overlay_root) for path in _candidate_paths(overlay_root=overlay_root)]
    protected = read_json(V3_DATA / "protected_v1_manifest.json")
    protected_v2 = read_json(V3_DATA / "protected_v2_manifest.json")
    protected_paths = {entry["path"] for entry in protected["entries"]} | {entry["path"] for entry in protected_v2["entries"]}
    candidate_names = {entry["path"] for entry in candidate_files}
    status_lines = _git_status() if repository_status is None else repository_status
    classifications = []
    for line in status_lines:
        path = line.split(" ", 8)[-1]
        # Porcelain-v2 untracked rows are '? path'; tracked rows end with path.
        if line.startswith("? "):
            path = line[2:]
        classification = "candidate" if path in candidate_names or any(x.startswith(path.rstrip("/") + "/") for x in candidate_names) else "protected_baseline" if path in protected_paths or any(x.startswith(path.rstrip("/") + "/") for x in protected_paths) else "preexisting_other"
        classifications.append({"line": line, "path_projection": path, "classification": classification})
    stage_sha = sha_file(_overlay_path("reports/provenance/msae_independent_measurement_v3/stage_a.json", overlay_root))
    closure_sha = sha_file(_overlay_path("data/msae_independent_measurement_v3/dependency_closure.json", overlay_root))
    return {
        "schema_version": "msae_v3_prescore_candidate_manifest_v1", "protocol_id": PROTOCOL,
        "candidate_root_realpath": str(ROOT.resolve(strict=True)), "candidate_files": candidate_files,
        "candidate_tree_sha256": sha_bytes(canonical_bytes(candidate_files)),
        "dependency_closure_sha256": closure_sha, "stage_a_sha256": stage_sha,
        "repository_status": status_lines, "repository_status_classification": classifications,
        "required_absent_post_review_outputs": [str(V3_REVIEW.relative_to(ROOT)), RUN_REL],
        "required_external_state": {
            "private_key": read_json(V3_CONFIG / "authorization_commitment.json")["private_key_binding"],
            "nonce_directory": _directory_binding(NONCE_DIR), "gpu_lock_directory": _directory_binding(GPU_LOCK_DIR),
            "required_empty_nonce_directory": True,
            "required_absent_build_roots": ["/tmp/msae_independent_measurement_v3_build_primary", "/tmp/msae_independent_measurement_v3_build_rebuild"],
            "required_absent_review_files_pattern": "/tmp/msae_v3_prescore_{check,trace}_${manifest_sha256}.{json,log}",
            "required_absent_tmux_socket": f"/tmp/msae_independent_measurement_v3_{stage_sha}.sock",
        },
        "quarantined_entries": [_quarantine_entry(rel) for rel in sorted(QUARANTINED)],
        "sealed_payload_content_reads": 0, "self_hash_excluded": True,
    }


_M4_NEW_RELATIVES = (
    "data/msae_independent_measurement_v3/dependency_closure.json",
    "data/msae_independent_measurement_v3/endpoint_registry.json",
    "data/msae_independent_measurement_v3/environment_allowlist.json",
    "reports/provenance/msae_independent_measurement_v3/stage_a.json",
    "reports/provenance/msae_independent_measurement_v3/status.json",
    "reports/provenance/msae_independent_measurement_v3/prescore_candidate_manifest.json",
)


def _anticipated_m4_status() -> list[str]:
    current = _git_status()
    tracked = [line for line in current if not line.startswith("? ")]
    untracked = {line[2:]: line for line in current if line.startswith("? ")}
    # The manifest is self-excluded from its frozen projection; the verifier
    # permits exactly that one additional line.
    for relative in _M4_NEW_RELATIVES[:-1]:
        untracked.setdefault(relative, f"? {relative}")
    return [*tracked, *(untracked[path] for path in sorted(untracked, key=lambda x: x.encode()))]


def _tree_manifest(root: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for path in sorted(root.rglob("*"), key=lambda x: x.relative_to(root).as_posix().encode()):
        st = path.lstat()
        relative = path.relative_to(root).as_posix()
        if stat.S_ISDIR(st.st_mode) and not stat.S_ISLNK(st.st_mode):
            rows.append({"path": relative, "type": "directory", "mode": stat.S_IMODE(st.st_mode),
                         "size": st.st_size})
        elif stat.S_ISREG(st.st_mode) and not stat.S_ISLNK(st.st_mode):
            rows.append({"path": relative, "type": "regular", "mode": stat.S_IMODE(st.st_mode),
                         "size": st.st_size, "sha256": sha_file(path)})
        else:
            raise ValueError(f"unexpected M4 temporary-tree entry: {path}")
    return rows


def _materialize_m4_tree(root: Path, checkpoints: list[dict[str, Any]],
                         anticipated_status: list[str]) -> dict[str, Any]:
    os.mkdir(root, 0o700)
    os.chmod(root, 0o700)
    closure = closure_payload(checkpoints)
    registry = endpoint_registry()
    environment = environment_payload(closure)
    for relative, value in (
        (_M4_NEW_RELATIVES[0], closure), (_M4_NEW_RELATIVES[1], registry),
        (_M4_NEW_RELATIVES[2], environment),
    ):
        install_json(root / relative, value)
    stage_a = stage_a_payload(overlay_root=root)
    install_json(root / _M4_NEW_RELATIVES[3], stage_a)
    install_json(root / _M4_NEW_RELATIVES[4], {
        "schema_version": "msae_v3_prescore_status_v1", "protocol_id": PROTOCOL,
        "status": "ready_prescore_review" if stage_a["stage_ready"] else "blocked_prescore",
        "stage_a_ready": stage_a["stage_ready"],
        "stage_a_sha256": sha_file(root / _M4_NEW_RELATIVES[3]),
        "stage_b": "not_run", "stage_c": "not_run", "confirmation_partition": "replacement_required",
    })
    manifest = build_candidate_manifest(overlay_root=root, repository_status=anticipated_status)
    install_json(root / _M4_NEW_RELATIVES[5], manifest)
    return stage_a


def build_m4(checkpoints: list[dict[str, Any]]) -> dict[str, Any]:
    verify_baseline_projection("M2")
    if PRIMARY_BUILD_ROOT.exists() or REBUILD_BUILD_ROOT.exists():
        raise FileExistsError("M4 temporary roots must both be initially absent")
    anticipated_status = _anticipated_m4_status()
    staged_bytes: dict[str, bytes] = {}
    stage_a: dict[str, Any]
    try:
        stage_a = _materialize_m4_tree(PRIMARY_BUILD_ROOT, checkpoints, anticipated_status)
        rebuilt_stage = _materialize_m4_tree(REBUILD_BUILD_ROOT, checkpoints, anticipated_status)
        primary_manifest = _tree_manifest(PRIMARY_BUILD_ROOT)
        rebuild_manifest = _tree_manifest(REBUILD_BUILD_ROOT)
        if canonical_bytes(primary_manifest) != canonical_bytes(rebuild_manifest):
            raise ValueError("independent complete M4 tree manifests differ")
        if canonical_bytes(stage_a) != canonical_bytes(rebuilt_stage):
            raise ValueError("independent Stage-A bytes differ")
        for relative in _M4_NEW_RELATIVES:
            left = PRIMARY_BUILD_ROOT / relative
            right = REBUILD_BUILD_ROOT / relative
            if left.read_bytes() != right.read_bytes():
                raise ValueError(f"independent M4 output bytes differ: {relative}")
            staged_bytes[relative] = left.read_bytes()
    finally:
        shutil.rmtree(PRIMARY_BUILD_ROOT, ignore_errors=True)
        shutil.rmtree(REBUILD_BUILD_ROOT, ignore_errors=True)
    if PRIMARY_BUILD_ROOT.exists() or REBUILD_BUILD_ROOT.exists():
        raise RuntimeError("M4 temporary-root cleanup failed")
    for relative in _M4_NEW_RELATIVES:
        write_once(ROOT / relative, staged_bytes[relative])
    verify_baseline_projection("M4")
    if canonical_bytes(stage_a_payload()) != staged_bytes[_M4_NEW_RELATIVES[3]]:
        raise ValueError("installed Stage A does not reproduce")
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


def _enumerate_data_paths() -> set[str]:
    """Return every current data-tree entry without following symlinked dirs."""
    result: set[str] = set()
    data_root = ROOT / "data"
    for directory, dirnames, filenames in os.walk(data_root, topdown=True, followlinks=False):
        base = Path(directory)
        for name in [*dirnames, *filenames]:
            result.add((base / name).relative_to(ROOT).as_posix())
        # A symlink may appear in dirnames; record it but never traverse it.
        dirnames[:] = [name for name in dirnames if not (base / name).is_symlink()]
    return result


def verify_baseline_projection(phase: str = "M4") -> dict[str, int]:
    baseline = read_json(V3_DATA / "data_baseline_manifest.json")
    if (baseline.get("schema_version") != "msae_v3_data_baseline_manifest_v1"
            or baseline.get("protocol_id") != PROTOCOL
            or baseline.get("v3_root_absent_at_snapshot") is not True
            or baseline.get("quarantined_paths") != sorted(QUARANTINED)
            or not isinstance(baseline.get("entries"), list)):
        raise ValueError("baseline manifest semantic mismatch")
    baseline_paths = {entry["path"] for entry in baseline["entries"]}
    if len(baseline_paths) != len(baseline["entries"]):
        raise ValueError("duplicate baseline path")
    expected_v3 = {str((V3_DATA / name).relative_to(ROOT)) for name in _phase_data_names(phase)}
    expected_paths = baseline_paths | {str(V3_DATA.relative_to(ROOT))} | expected_v3
    observed_paths = _enumerate_data_paths()
    if observed_paths != expected_paths:
        raise ValueError(f"closed data projection mismatch for {phase}: "
                         f"missing={sorted(expected_paths-observed_paths)}, extra={sorted(observed_paths-expected_paths)}")
    root_stat = V3_DATA.lstat()
    if not stat.S_ISDIR(root_stat.st_mode) or stat.S_ISLNK(root_stat.st_mode):
        raise ValueError("v3 data root is not a real directory")
    for name in _phase_data_names(phase):
        path = V3_DATA / name
        st = path.lstat()
        if not stat.S_ISREG(st.st_mode) or stat.S_ISLNK(st.st_mode):
            raise ValueError(f"declared v3 data output is not a regular file: {name}")
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
            expected_sha, expected_size = QUARANTINED[entry["path"]]
            if (entry.get("type") != "regular"
                    or entry.get("verification_action") != "lstat_only_against_frozen_v1_evidence"
                    or entry.get("sha256") != expected_sha or entry.get("size") != expected_size):
                raise ValueError(f"quarantine baseline semantics drift: {entry['path']}")
            for key in ("type", "mode", "size", "device", "inode", "nlink", "ctime_ns", "mtime_ns"):
                if current[key] != entry.get(key):
                    raise ValueError(f"quarantine baseline metadata drift: {entry['path']}:{key}")
            lstat_only += 1
        else:
            if (entry.get("type") != "regular" or entry.get("verification_action") != "content_rehash"
                    or not stat.S_ISREG(st.st_mode) or stat.S_ISLNK(st.st_mode)
                    or stat.S_IMODE(st.st_mode) != entry.get("mode")
                    or st.st_size != entry.get("size") or sha_file(path) != entry.get("sha256")):
                raise ValueError(f"baseline content drift: {entry['path']}")
            checked += 1
    return {"content_rehash": checked, "lstat_only": lstat_only,
            "declared_v3_files": len(expected_v3), "observed_data_entries": len(observed_paths)}


def verify_protected_v1() -> int:
    protected = read_json(V3_DATA / "protected_v1_manifest.json")
    if (protected.get("schema_version") != "msae_v3_protected_v1_manifest_v1"
            or protected.get("protocol_id") != PROTOCOL or len(protected.get("entries", [])) != 372):
        raise ValueError("protected v1 manifest semantic mismatch")
    for entry in protected["entries"]:
        _verify_entry(entry)
    terminal = read_json(ROOT / "reports/provenance/msae_independent_measurement_v1/status.json")
    if terminal["status"] != "stopped_prescore" or terminal["stage_a_ready"] is not False or terminal["stage_b"] != "not_run" or terminal["stage_c"] != "not_run":
        raise ValueError("v1 terminal state was reinterpreted")
    return len(protected["entries"])


def verify_protected_v2() -> int:
    protected = read_json(V3_DATA / "protected_v2_manifest.json")
    if (protected.get("schema_version") != "msae_v3_protected_v2_terminal_manifest_v1"
            or protected.get("protocol_id") != PROTOCOL or len(protected.get("entries", [])) != 14
            or protected.get("v2_terminal_status") != "stopped_prescore_overlap_ineligible"
            or protected.get("v2_blocking_collision_count") != 4
            or protected.get("v2_stage_a_ready") is not False
            or protected.get("v2_stage_b") != "not_run" or protected.get("v2_stage_c") != "not_run"):
        raise ValueError("v2 terminal manifest semantics drift")
    for entry in protected["entries"]:
        _verify_entry(entry)
    terminal = read_json(ROOT / "reports/provenance/msae_independent_measurement_v2/status.json")
    if (terminal.get("status") != "stopped_prescore_overlap_ineligible" or terminal.get("stage_a_ready") is not False
            or terminal.get("stage_b") != "not_run" or terminal.get("stage_c") != "not_run"):
        raise ValueError("v2 terminal state was reinterpreted")
    overlap = read_json(ROOT / "data/msae_independent_measurement_v2/history_overlap.json")
    if overlap.get("status") != "ineligible" or overlap.get("blocking_collision_count") != 4:
        raise ValueError("v2 overlap result drift")
    return len(protected["entries"])


def validate_source_exposure() -> dict[str, Any]:
    value = read_json(V3_DATA / "source_exposure.json")
    exact_top = {
        "schema_version": "msae_source_exposure_incident_v3",
        "protocol_id": PROTOCOL,
        "disposition": "exposed_quarantined_not_scanned_by_v3",
        "session_date_utc": "2026-08-20",
        "wall_clock_time_unavailable": True,
        "content_returned_to_coordinator": False,
        "blindness_destroyed": True,
        "replacement_required_before_confirmation": True,
    }
    for key, expected in exact_top.items():
        if value.get(key) != expected:
            raise ValueError(f"source exposure semantic mismatch: {key}")
    if value.get("cause_command") != ('grep -R -l --include=\'*.json\' --include=\'*.jsonl\' '
                                        '\'"source_words"\\|"target_words"\' experiments/wip/MSAE/data'):
        raise ValueError("source exposure cause-command mismatch")
    entries = value.get("entries")
    if not isinstance(entries, list) or {item.get("path") for item in entries} != set(QUARANTINED):
        raise ValueError("source exposure quarantine entry set mismatch")
    for item in entries:
        rel = item["path"]
        expected_sha, expected_size = QUARANTINED[rel]
        if (item.get("frozen_v1_sha256"), item.get("size"), item.get("v1_status_at_v1_audit"),
                item.get("v3_current_status"), item.get("current_content_not_asserted")) != (
                expected_sha, expected_size, "excluded_sealed_unopened",
                "exposed_quarantined_not_scanned", True):
            raise ValueError(f"source exposure entry semantic mismatch: {rel}")
        current = _quarantine_entry(rel)
        for key in ("type", "mode", "size", "device", "inode", "nlink", "ctime_ns", "mtime_ns"):
            if item.get(key) != current[key]:
                raise ValueError(f"source exposure metadata drift: {rel}:{key}")
    predecessors = {(item.get("protocol_id"), item.get("status"), item.get("blocking_collisions"))
                    for item in value.get("predecessor_overlap_attempts", [])}
    if predecessors != {("msae_independent_measurement_v1", "stopped_prescore", 206),
                         ("msae_exposed_source_measurement_v2", "stopped_prescore_overlap_ineligible", 4)}:
        raise ValueError("source exposure predecessor history mismatch")
    return value


def verify_candidate_manifest(phase: str = "prescore") -> dict[str, Any]:
    manifest_path = V3_PROV / "prescore_candidate_manifest.json"
    manifest = read_json(manifest_path)
    if manifest.get("schema_version") != "msae_v3_prescore_candidate_manifest_v1" or manifest.get("protocol_id") != PROTOCOL:
        raise ValueError("candidate manifest schema mismatch")
    if manifest["candidate_root_realpath"] != str(ROOT.resolve(strict=True)):
        raise ValueError("candidate root mismatch")
    for entry in manifest["candidate_files"]:
        _verify_entry(entry)
    if sha_bytes(canonical_bytes(manifest["candidate_files"])) != manifest["candidate_tree_sha256"]:
        raise ValueError("candidate tree digest mismatch")
    if sha_file(V3_DATA / "dependency_closure.json") != manifest["dependency_closure_sha256"]:
        raise ValueError("closure digest mismatch")
    if sha_file(V3_PROV / "stage_a.json") != manifest["stage_a_sha256"]:
        raise ValueError("Stage-A digest mismatch")
    closure = verify_dependency_closure()
    if sha_bytes(canonical_bytes(closure)) != manifest["dependency_closure_sha256"]:
        raise ValueError("recomputed dependency-closure digest mismatch")
    current_status = _git_status()
    allowed_new = {f"? {str((V3_PROV / 'prescore_candidate_manifest.json').relative_to(ROOT))}"}
    if phase in {"post_review", "post_signature"}:
        allowed_new.add(f"? {str(V3_REVIEW.relative_to(ROOT))}")
    if phase == "post_signature":
        allowed_new.add(f"? {RUN_REL}/authorization.json")
    projected_status = [line for line in current_status if line not in allowed_new]
    if projected_status != manifest["repository_status"]:
        raise ValueError("repository status projection drift")
    validate_stage_a()
    baseline_counts = verify_baseline_projection()
    protected_count = verify_protected_v1()
    protected_v2_count = verify_protected_v2()
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
    review_exists = V3_REVIEW.exists()
    run_exists = RUN_ROOT.exists()
    if phase == "prescore":
        if review_exists or run_exists:
            raise ValueError("post-review output exists during prescore check")
    elif phase == "post_review":
        if not review_exists or run_exists:
            raise ValueError("post-review projection mismatch")
        review = V3_REVIEW.read_text(encoding="utf-8")
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
    return {"schema_version": "msae_v3_prescore_check_v1", "protocol_id": PROTOCOL,
            "phase": phase, "manifest_sha256": sha_file(manifest_path),
            "candidate_tree_sha256": manifest["candidate_tree_sha256"],
            "dependency_closure_sha256": manifest["dependency_closure_sha256"],
            "stage_a_sha256": manifest["stage_a_sha256"], "repository_status_sha256": sha_bytes(canonical_bytes(current_status)),
            "baseline_counts": baseline_counts, "protected_v1_entries": protected_count,
            "protected_v2_entries": protected_v2_count,
            "quarantined_metadata_checks": len(QUARANTINED), "sealed_payload_content_reads": 0,
            "eligible": True}


def prescore_traced_check(manifest: Path, output: Path, trace: Path) -> None:
    if manifest.resolve(strict=True) != (V3_PROV / "prescore_candidate_manifest.json").resolve(strict=True):
        raise ValueError("unexpected candidate manifest")
    fds = []
    try:
        for path in (output, trace):
            fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW | os.O_CLOEXEC, 0o600)
            os.fchmod(fd, 0o600)
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
    payload = {"schema_version": "msae_v3_technical_failure_v1", "protocol_id": PROTOCOL,
               "status": "not_run", "reason": message, "broker_pid": broker_pid,
               "worker_pid": worker_pid, "stage_b_written": (RUN_ROOT / "stage_b.json").exists()}
    with contextlib.suppress(FileExistsError):
        install_json(RUN_ROOT / "technical_failure.json", payload)
    if not (RUN_ROOT / "stage_b.json").exists():
        with contextlib.suppress(FileExistsError):
            install_json(RUN_ROOT / "status.json", {"schema_version": "msae_v3_runtime_status_v1",
                                                     "status": "technical_failure_not_run", "stage_b_ready": False})


def broker(socket_path: str, gpu_uuid: str, gpu_index: int) -> None:
    broker_log_fd = os.open(RUN_ROOT / "logs/broker.log", os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    os.fchmod(broker_log_fd, 0o600)
    os.dup2(broker_log_fd, 1)
    os.dup2(broker_log_fd, 2)
    if broker_log_fd > 2:
        os.close(broker_log_fd)
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
    _send_json(sock, {"schema_version": "msae_v3_broker_hello_v1", "pid": broker_pid,
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
            # Linux parent-death watchdog: an unexpected broker death must not
            # leave an unleased CUDA worker alive, so use SIGKILL rather than a
            # catchable/deferrable signal.
            import ctypes
            libc = ctypes.CDLL(None, use_errno=True)
            if libc.prctl(1, 9, 0, 0, 0) != 0:  # PR_SET_PDEATHSIG, SIGKILL
                raise OSError(ctypes.get_errno(), "prctl(PR_SET_PDEATHSIG) failed")
            if os.getppid() != broker_pid:
                raise RuntimeError("broker died during worker setup")
            signal_byte = os.read(ready_r, 1)
            if signal_byte != b"1":
                raise RuntimeError("launcher did not authorize worker handoff")
            os.close(ready_r)
            log_fd = os.open(RUN_ROOT / "logs/worker.log", os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
            os.fchmod(log_fd, 0o600)
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
                    str((ROOT / "scripts/run_msae_independent_calibration_v3.py").resolve()),
                    "--run-root", RUN_REL, "--gpu-uuid", gpu_uuid, "--broker-pid", str(broker_pid)]
            os.execve(argv[0], argv, environment)
        except BaseException as error:
            _runtime_failure(f"worker_setup:{type(error).__name__}:{error}", broker_pid=broker_pid, worker_pid=os.getpid())
            os._exit(125)
    os.close(ready_r)
    os.setpgid(worker_pid, worker_pid)
    hello = {"schema_version": "msae_v3_worker_handoff_v1", "broker_pid": broker_pid,
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
        if (re.fullmatch(r"[0-9]+", index, re.ASCII) is None
                or re.fullmatch(r"GPU-[0-9A-Fa-f-]{16,}", uuid, re.ASCII) is None
                or re.fullmatch(r"[0-9]+", memory, re.ASCII) is None
                or re.fullmatch(r"[0-9]+", utilization, re.ASCII) is None):
            raise ValueError("malformed nvidia-smi GPU row")
        if uuid not in busy and int(memory) < 1024 and int(utilization) <= 5:
            rows.append((int(memory), int(utilization), uuid, int(index)))
    return sorted(rows)


def _open_gpu_lock(uuid: str) -> tuple[int, Path]:
    binding = _directory_binding(GPU_LOCK_DIR)
    commitment = read_json(V3_CONFIG / "authorization_commitment.json")
    if any(binding[k] != commitment["gpu_lock_directory"][k] for k in ("path", "realpath", "device", "inode", "uid", "mode", "nlink")):
        raise ValueError("GPU lock directory drift")
    name = f"{sha_bytes(uuid.encode('ascii'))}.lock"
    directory_fd = os.open(GPU_LOCK_DIR, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC)
    try:
        try:
            fd = os.open(name, os.O_RDWR | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW | os.O_CLOEXEC,
                         0o600, dir_fd=directory_fd)
            os.fchmod(fd, 0o600)
        except FileExistsError:
            fd = os.open(name, os.O_RDWR | os.O_NOFOLLOW | os.O_CLOEXEC, dir_fd=directory_fd)
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
    os.chmod(RUN_ROOT / "logs", 0o700)
    socket_path = Path(f"/tmp/msae_independent_measurement_v3_{sha_file(V3_PROV / 'stage_a.json')}.sock")
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
    session = "msae-independent-v3-calibration"
    broker_argv = [str((ROOT / ".venv-atlas/bin/python").resolve()), "-B", "-I",
                   str(Path(__file__).resolve()), "broker", "--socket", str(handoff_socket),
                   "--gpu-uuid", uuid, "--gpu-index", str(index)]
    broker_command = "exec " + shlex.join(broker_argv)
    tmux_started = False
    handoff_complete = False
    worker: dict[str, Any] = {}
    hello: dict[str, Any] = {}
    try:
        subprocess.check_call(["/usr/bin/tmux", "-S", str(socket_path), "new-session", "-d", "-s", session, broker_command])
        tmux_started = True
        connection, _ = server.accept()
        hello = _recv_json(connection)
        if hello.get("schema_version") != "msae_v3_broker_hello_v1" or _start_ticks(int(hello["pid"])) != hello["start_ticks"]:
            raise ValueError("broker identity validation failed")
        connection.sendmsg([b"L"], [(socket.SOL_SOCKET, socket.SCM_RIGHTS, array.array("i", [lease_fd]))])
        worker = _recv_json(connection)
        if worker["broker_pid"] != hello["pid"] or worker["gpu_uuid"] != uuid or _start_ticks(worker["worker_pid"]) != worker["worker_start_ticks"]:
            raise ValueError("worker identity validation failed")
        lock_record = {"schema_version": "msae_v3_lock_acquired_v1", "protocol_id": PROTOCOL,
                       "gpu_uuid": uuid, "gpu_index": index, "memory_used_mib": memory,
                       "utilization_percent": utilization, "lock_path": str(lock_path),
                       "lock_device": os.fstat(lease_fd).st_dev, "lock_inode": os.fstat(lease_fd).st_ino,
                       "broker_pid": worker["broker_pid"], "broker_start_ticks": worker["broker_start_ticks"],
                       "worker_pid": worker["worker_pid"], "worker_start_ticks": worker["worker_start_ticks"],
                       "worker_pgid": worker["worker_pgid"], "stage_a_sha256": sha_file(V3_PROV / "stage_a.json"),
                       "authorization_envelope_sha256": authorization["envelope_sha256"]}
        install_json(RUN_ROOT / "lock_acquired.json", lock_record)
        handoff = {"schema_version": "msae_v3_live_handoff_v1", "status": "live_handoff_no_result_wait",
                   "session": session, "tmux_socket": str(socket_path), "run_root": RUN_REL,
                   "broker_pid": worker["broker_pid"], "worker_pid": worker["worker_pid"],
                   "gpu_uuid": uuid, "lock_acquired_sha256": sha_file(RUN_ROOT / "lock_acquired.json")}
        install_json(RUN_ROOT / "handoff.json", handoff)
        connection.sendall(b"G")
        pane_pid = int(subprocess.check_output(["/usr/bin/tmux", "-S", str(socket_path), "display-message", "-p",
                                                "-t", session, "#{pane_pid}"], text=True).strip())
        if pane_pid != worker["broker_pid"]:
            raise ValueError("tmux pane is not the bound broker")
        handoff_complete = True
    except BaseException:
        if tmux_started:
            with contextlib.suppress(Exception):
                subprocess.run(["/usr/bin/tmux", "-S", str(socket_path), "kill-session", "-t", session], check=False)
        with contextlib.suppress(Exception):
            os.killpg(int(worker.get("worker_pgid", -1)), 15)
        _runtime_failure("launcher_or_handoff_failure", broker_pid=int(worker.get("broker_pid", hello.get("pid", -1))),
                         worker_pid=int(worker["worker_pid"]) if "worker_pid" in worker else None)
        raise
    finally:
        server.close()
        with contextlib.suppress(FileNotFoundError):
            handoff_socket.unlink()
        if not handoff_complete:
            with contextlib.suppress(FileNotFoundError):
                socket_path.unlink()
        os.close(lease_fd)
    print(json.dumps(handoff, indent=2))
    return handoff


OPERATOR_INSTRUCTION = """Do these steps for me. Make sure to use /adversarial to find and fix any issues before running any experiments. Make sure to run the experiments on tmux on whichever GPUs are free. When the experiments are running, don't wait for the results. Preserve the prior attempt as failed; redesign the overlap gate to distinguish boilerplate from substantive reuse; retain AMALGUM only as an exposed-source technical replication; implement strict CoNLL-U/entity parsing, real prefix examples, four-role support and 500 maps, full execution closure, digest-based Stage-B QA, signed authorization/nonce handling, and behavioral failure-path tests."""


def main() -> None:
    parser = argparse.ArgumentParser()
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("fixtures")
    commands.add_parser("build-posthoc")
    commands.add_parser("build-m0-completion")
    overlap_parser = commands.add_parser("audit-overlap")
    overlap_parser.add_argument("--reviewed-m0-sha256", required=True)
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
        print(json.dumps(build_overlap(args.reviewed_m0_sha256), indent=2)[:10000])
    elif args.command == "build-posthoc":
        print(json.dumps(build_v2_posthoc_analysis(), indent=2))
    elif args.command == "build-m0-completion":
        print(json.dumps(build_m0_completion(), indent=2))
    elif args.command == "build-labels-maps":
        state = build_labels()
        print(json.dumps(build_maps(state), indent=2))
    elif args.command == "build-imports":
        print(json.dumps(build_protocol_imports(), indent=2))
    elif args.command == "setup-m3":
        commitment = setup_authorization_state(OPERATOR_INSTRUCTION)
        checkpoints = checkpoint_registry()
        config = build_protocol_config(checkpoints)
        print(json.dumps({"commitment_sha256": sha_file(V3_CONFIG / "authorization_commitment.json"),
                          "protocol_config_sha256": sha_file(V3_CONFIG / "protocol.json"),
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
