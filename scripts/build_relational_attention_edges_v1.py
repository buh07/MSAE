#!/usr/bin/env python3
"""Label-only builder for the relational attention-link discovery study."""
from __future__ import annotations

import argparse
import hashlib
import json
import marshal
import pickletools
import re
import secrets
import sys
import types
import unicodedata
import zipfile
from collections import Counter, defaultdict, deque
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

import numpy as np
from scipy.optimize import linear_sum_assignment
from transformers import AutoTokenizer

sys.path.insert(0, str(Path(__file__).resolve().parent))

from relational_attention_edges_v1 import (
    CONFIG,
    EXPOSURE_UNIVERSE_PATH,
    EXPECTED_SIGNER,
    NAMESPACE,
    PRESCORE_LIFECYCLE_PATHS,
    ROOT,
    assert_new_destination,
    assert_permissions,
    atomic_json,
    atomic_jsonl,
    bootstrap_indices,
    canonical_json_bytes,
    coarse_relation,
    exclusive_sign_payload,
    inventory_digest,
    load_config,
    load_signing_key,
    read_json,
    recursive_inventory,
    semantic_config_digest,
    sha256_file,
    sign_payload,
    stable_digest,
    stable_hex,
    study_key,
    verify_preservation,
    verify_signed,
)


@dataclass(frozen=True)
class Token:
    token_id: int
    form: str
    upos: str
    head: int
    deprel: str
    misc: str
    order: int
    char_start: int
    char_end: int


@dataclass
class Sentence:
    source: str
    file_name: str
    split: str
    raw_document_id: str
    document_id: str
    sent_id: str
    text: str
    tokens: list[Token]
    has_mwt: bool
    has_empty: bool
    reconstruction_exact: bool
    token_hash: str
    sentence_hash: str
    input_ids: list[int] | None = None
    offsets: list[tuple[int, int]] | None = None
    spans: dict[int, list[int]] | None = None

    @property
    def key(self) -> str:
        return f"{self.source}:{self.file_name}:{self.sent_id}"


TEXT_ARTIFACT_SUFFIXES = {
    ".md", ".txt", ".log", ".csv", ".tsv", ".conllu", ".py", ".sh",
    ".html", ".htm", ".yaml", ".yml", ".toml", ".rst", ".diff", ".patch",
}
OPAQUE_STRUCTURED_SUFFIXES = {".pt", ".npy", ".npz", ".pkl", ".pyc"}
_PRESCORE_OWNER_NONCE: str | None = None
_PRESCORE_OWNER_CONTEXT: dict[str, Any] | None = None


def _split_name(path: Path) -> str:
    match = re.search(r"-(train|dev|test)(?:-[^.]+)?\.conllu$", path.name)
    return match.group(1) if match else path.stem


def _normalize_text(value: str) -> str:
    """Canonical project-content normalizer frozen before Discovery-2 prescoring."""
    return " ".join(unicodedata.normalize("NFKC", value).casefold().split())


class NormalizedTextMatcher:
    """Deterministic Aho-Corasick matcher with explicit alphanumeric boundaries."""

    def __init__(self, patterns: Mapping[str, str]) -> None:
        self.transitions: list[dict[str, int]] = [{}]
        self.fail: list[int] = [0]
        self.outputs: list[list[tuple[str, str]]] = [[]]
        for pattern, digest in sorted(patterns.items(), key=lambda item: item[0].encode("utf-8")):
            state = 0
            for char in pattern:
                state = self.transitions[state].setdefault(char, len(self.transitions))
                if state == len(self.transitions):
                    self.transitions.append({})
                    self.fail.append(0)
                    self.outputs.append([])
            self.outputs[state].append((pattern, digest))
        queue: deque[int] = deque()
        for state in self.transitions[0].values():
            queue.append(state)
        while queue:
            state = queue.popleft()
            for char, child in self.transitions[state].items():
                queue.append(child)
                fallback = self.fail[state]
                while fallback and char not in self.transitions[fallback]:
                    fallback = self.fail[fallback]
                self.fail[child] = self.transitions[fallback].get(char, 0)
                self.outputs[child].extend(self.outputs[self.fail[child]])

    def find(self, normalized_text: str) -> set[str]:
        state = 0
        hits: set[str] = set()
        for index, char in enumerate(normalized_text):
            while state and char not in self.transitions[state]:
                state = self.fail[state]
            state = self.transitions[state].get(char, 0)
            for pattern, digest in self.outputs[state]:
                start, end = index - len(pattern) + 1, index + 1
                left_ok = start == 0 or not (normalized_text[start - 1].isalnum() and pattern[0].isalnum())
                right_ok = end == len(normalized_text) or not (
                    normalized_text[end].isalnum() and pattern[-1].isalnum()
                )
                if left_ok and right_ok:
                    hits.add(digest)
        return hits


def _sentence_from_rows(
    *, source: str, path: Path, document: str | None, comments: Mapping[str, str], rows: Sequence[list[str]]
) -> Sentence:
    if document is None:
        raise RuntimeError(f"sentence lacks genuine newdoc id: {path}:{comments.get('sent_id')}")
    text = comments.get("text")
    sent_id = comments.get("sent_id")
    if text is None or sent_id is None:
        raise RuntimeError(f"sentence lacks text/sent_id: {path}:{document}")
    integer_rows = [row for row in rows if row[0].isdigit()]
    has_mwt = any("-" in row[0] for row in rows)
    has_empty = any("." in row[0] for row in rows)
    pieces: list[str] = []
    starts: list[int] = []
    ends: list[int] = []
    cursor = 0
    for index, row in enumerate(integer_rows):
        form = row[1]
        starts.append(cursor)
        pieces.append(form)
        cursor += len(form)
        ends.append(cursor)
        if index + 1 < len(integer_rows) and "SpaceAfter=No" not in row[9].split("|"):
            pieces.append(" ")
            cursor += 1
    reconstructed = "".join(pieces)
    tokens = [
        Token(
            token_id=int(row[0]),
            form=row[1],
            upos=row[3],
            head=int(row[6]),
            deprel=row[7],
            misc=row[9],
            order=index,
            char_start=starts[index],
            char_end=ends[index],
        )
        for index, row in enumerate(integer_rows)
    ]
    canonical_tokens = [_normalize_text(token.form) for token in tokens]
    token_hash = hashlib.sha256(canonical_json_bytes(canonical_tokens)).hexdigest()
    sentence_hash = hashlib.sha256(text.encode("utf-8")).hexdigest()
    split = _split_name(path)
    return Sentence(
        source=source,
        file_name=path.name,
        split=split,
        raw_document_id=document,
        document_id=f"{source}:{split}:{document}",
        sent_id=sent_id,
        text=text,
        tokens=tokens,
        has_mwt=has_mwt,
        has_empty=has_empty,
        reconstruction_exact=reconstructed == text,
        token_hash=token_hash,
        sentence_hash=sentence_hash,
    )


def parse_conllu(source: str, paths: Sequence[Path]) -> list[Sentence]:
    output: list[Sentence] = []
    raw_document_files: dict[str, set[str]] = defaultdict(set)
    for path in paths:
        current_document: str | None = None
        comments: dict[str, str] = {}
        rows: list[list[str]] = []

        def flush() -> None:
            nonlocal comments, rows
            if rows:
                sentence = _sentence_from_rows(
                    source=source, path=path, document=current_document, comments=comments, rows=rows
                )
                output.append(sentence)
                raw_document_files[sentence.raw_document_id].add(path.name)
            comments, rows = {}, []

        for line in path.read_text(encoding="utf-8").splitlines() + [""]:
            if not line:
                flush()
                continue
            if line.startswith("# newdoc id = "):
                current_document = line.split("=", 1)[1].strip()
            if line.startswith("# ") and " = " in line:
                key, value = line[2:].split(" = ", 1)
                comments[key] = value
            elif not line.startswith("#"):
                parts = line.split("\t")
                if len(parts) != 10:
                    raise RuntimeError(f"malformed CoNLL-U row: {path}:{line[:80]}")
                rows.append(parts)
    repeated = {doc: files for doc, files in raw_document_files.items() if len(files) > 1}
    if repeated:
        raise RuntimeError(f"raw document IDs repeat across selected analysis files: {list(repeated.items())[:5]}")
    return output


def _prior_conllu_paths(config: Mapping[str, Any]) -> list[Path]:
    """Return prior CoNLL-U files after exact, lineage-bound exclusions only."""
    excluded_exact = _current_program_allowlist(config)
    output_roots = _current_output_roots(config)
    paths: list[Path] = []
    for path in (ROOT / "data").rglob("*.conllu"):
        resolved = path.resolve()
        if resolved in excluded_exact or any(root == resolved or root in resolved.parents for root in output_roots):
            continue
        paths.append(path)
    return sorted(paths, key=lambda p: p.as_posix().encode("utf-8"))


def _strict_prior_conllu_sentences(path: Path) -> list[tuple[str | None, list[str]]]:
    """Parse historical CoNLL-U fail-closed for overlap normalization.

    Historical files need not provide ``newdoc`` comments, but every data row
    must be valid ten-column CoNLL-U and the file must be strict UTF-8.  Range
    and empty-node rows are validated and skipped; integer token rows supply
    the normalized sentence content.
    """
    current_document: str | None = None
    forms: list[str] = []
    output: list[tuple[str | None, list[str]]] = []
    sent_id_seen = False
    saw_data = False
    integer_ids: list[int] = []
    ranges: list[tuple[int, int]] = []
    empty_nodes: list[tuple[int, int]] = []

    def flush() -> None:
        nonlocal forms, sent_id_seen, saw_data, integer_ids, ranges, empty_nodes
        if sent_id_seen and not saw_data:
            raise RuntimeError(f"sentence header lacks data rows: {path}")
        if saw_data and not forms:
            raise RuntimeError(f"sentence lacks integer token rows: {path}")
        if ranges and any(end > len(integer_ids) for _, end in ranges):
            raise RuntimeError(f"CoNLL-U range exceeds sentence token sequence: {path}")
        if forms:
            output.append((current_document, forms))
        forms = []
        sent_id_seen = False
        saw_data = False
        integer_ids = []
        ranges = []
        empty_nodes = []

    raw = path.read_text(encoding="utf-8", errors="strict")
    if raw and re.search(r"(?:\r?\n){2}$", raw) is None:
        raise RuntimeError(f"historical CoNLL-U lacks final blank sentence terminator: {path}")
    for line_number, line in enumerate(
        raw.splitlines() + [""], 1
    ):
        if not line:
            flush()
            continue
        if line.startswith("# newdoc id = "):
            if sent_id_seen or saw_data:
                raise RuntimeError(f"newdoc marker inside sentence: {path}:{line_number}")
            document = line.split("=", 1)[1].strip()
            if not document:
                raise RuntimeError(f"empty newdoc id: {path}:{line_number}")
            current_document = document
            continue
        if line.startswith("# sent_id = "):
            if sent_id_seen or saw_data:
                raise RuntimeError(f"new sentence header before blank separator: {path}:{line_number}")
            if not line.split("=", 1)[1].strip():
                raise RuntimeError(f"empty sent_id: {path}:{line_number}")
            sent_id_seen = True
            continue
        if line.startswith("#"):
            if saw_data:
                raise RuntimeError(f"comment after data row before blank separator: {path}:{line_number}")
            continue
        parts = line.split("\t")
        if len(parts) != 10:
            raise RuntimeError(f"malformed CoNLL-U row (expected 10 columns): {path}:{line_number}")
        token_id = parts[0]
        saw_data = True
        if re.fullmatch(r"[1-9][0-9]*", token_id):
            numeric_id = int(token_id)
            expected_id = len(integer_ids) + 1
            if numeric_id != expected_id:
                raise RuntimeError(
                    f"non-monotone/restarted CoNLL-U integer ID: {path}:{line_number}:{token_id!r}"
                )
            if not parts[1]:
                raise RuntimeError(f"empty FORM in CoNLL-U row: {path}:{line_number}")
            integer_ids.append(numeric_id)
            forms.append(_normalize_text(parts[1]))
        elif match := re.fullmatch(r"([1-9][0-9]*)-([1-9][0-9]*)", token_id):
            start, end = int(match.group(1)), int(match.group(2))
            if start >= end:
                raise RuntimeError(f"invalid CoNLL-U range ID: {path}:{line_number}:{token_id!r}")
            if start != len(integer_ids) + 1 or (ranges and start <= ranges[-1][1]):
                raise RuntimeError(f"misplaced/overlapping CoNLL-U range ID: {path}:{line_number}:{token_id!r}")
            ranges.append((start, end))
        elif match := re.fullmatch(r"([1-9][0-9]*)\.([1-9][0-9]*)", token_id):
            base, suffix = int(match.group(1)), int(match.group(2))
            if not integer_ids or base != integer_ids[-1]:
                raise RuntimeError(f"misplaced CoNLL-U empty-node ID: {path}:{line_number}:{token_id!r}")
            previous_suffix = empty_nodes[-1][1] if empty_nodes and empty_nodes[-1][0] == base else 0
            if suffix != previous_suffix + 1:
                raise RuntimeError(f"non-monotone CoNLL-U empty-node ID: {path}:{line_number}:{token_id!r}")
            empty_nodes.append((base, suffix))
        else:
            raise RuntimeError(f"malformed CoNLL-U ID: {path}:{line_number}:{token_id!r}")
    return output


def _prior_sentence_hashes(paths: Sequence[Path]) -> dict[str, dict[str, Any]]:
    hashes: dict[str, dict[str, Any]] = {}
    for path in paths:
        for _, forms in _strict_prior_conllu_sentences(path):
            digest = hashlib.sha256(canonical_json_bytes(forms)).hexdigest()
            hashes.setdefault(digest, {"words": len(forms), "example_path": path.relative_to(ROOT).as_posix()})
    return hashes


def _document_hashes(sentences: Sequence[Sentence]) -> dict[str, str]:
    grouped: dict[str, list[str]] = defaultdict(list)
    for sentence in sentences:
        grouped[sentence.document_id].append(sentence.token_hash)
    return {document: hashlib.sha256(canonical_json_bytes(values)).hexdigest() for document, values in grouped.items()}


def _prior_document_hashes(paths: Sequence[Path]) -> dict[str, dict[str, Any]]:
    output: dict[str, dict[str, Any]] = {}
    for path in paths:
        documents: dict[str, list[str]] = defaultdict(list)
        for document, sentence_forms in _strict_prior_conllu_sentences(path):
            if document is not None:
                documents[document].append(hashlib.sha256(canonical_json_bytes(sentence_forms)).hexdigest())
        for document, sentence_hashes in documents.items():
            digest = hashlib.sha256(canonical_json_bytes(sentence_hashes)).hexdigest()
            output.setdefault(digest, {"path": path.relative_to(ROOT).as_posix(), "document": document})
    return output


def _current_program_allowlist(config: Mapping[str, Any]) -> set[Path]:
    """Exact current-program/retired-D1 exclusions; never infer exclusions from names."""
    paths: set[Path] = set()
    for field in (
        "plan", "plan_review", "closure", "preservation", "raw_provenance",
        "source_amendment", "source_amendment_superseded", "failed_prescore",
    ):
        spec = config.get(field)
        if isinstance(spec, Mapping) and "path" in spec:
            paths.add((ROOT / str(spec["path"])).resolve(strict=False))
    paths.add(CONFIG.resolve(strict=False))
    for relative in (
        "scripts/relational_attention_edges_v1.py",
        "scripts/build_relational_attention_edges_v1.py",
        "scripts/analyze_relational_attention_edges_v1.py",
        "scripts/run_relational_attention_edges_v1.py",
        "scripts/run_relational_attention_edges_v1_pipeline.sh",
        "scripts/launch_relational_attention_edges_v1_tmux.sh",
        "tests/test_relational_attention_edges_v1.py",
    ):
        paths.add((ROOT / relative).resolve(strict=False))
    for spec in config["sources"].values():
        root = ROOT / spec["root"]
        paths.update((root / name).resolve(strict=False) for name in spec["files"])
    raw_provenance = read_json(ROOT / config["raw_provenance"]["path"])
    raw_root = ROOT / "data/relational_attention_edges_v1_raw"
    for entry in raw_provenance.get("files", []):
        if not isinstance(entry, Mapping) or not isinstance(entry.get("path"), str):
            raise RuntimeError("malformed raw-provenance file entry")
        paths.add((raw_root / entry["path"]).resolve(strict=False))
    retirement = verify_signed(ROOT / config["failed_prescore"]["path"], config["signer"]["public_key_fingerprint_sha256"])
    paths.update((ROOT / entry["path"]).resolve(strict=False) for entry in retirement["artifacts"])
    paths.add((ROOT / config["exposure"]["universe_path"]).resolve(strict=False))
    opaque_path = config["exposure"].get("opaque_sidecar_path")
    if isinstance(opaque_path, str):
        paths.add((ROOT / opaque_path).resolve(strict=False))
    role_path = config["exposure"].get("role_sidecar_path")
    if isinstance(role_path, str):
        paths.add((ROOT / role_path).resolve(strict=False))
    paths.add((ROOT / "reports/provenance/relational_attention_edges_v1_rebuild_attestation.json").resolve(strict=False))
    paths.add((ROOT / config["paths"]["candidate_review"]).resolve(strict=False))
    for field in ("prescore_record", "prescore_rebuild_record", "prescore_primary_complete", "prescore_terminal"):
        if field in config["paths"]:
            paths.add((ROOT / config["paths"][field]).resolve(strict=False))
    paths.update((ROOT / "configs/relational_attention_edges_v1" / name).resolve(strict=False) for name in ("FINAL_FREEZE.json", "REVIEWED_SHIP.json", "BACKEND_QA.json", "SCIENCE_AUTHORIZATION.json"))
    return paths


def _current_output_roots(config: Mapping[str, Any]) -> set[Path]:
    return {
        (ROOT / config["paths"][field]).resolve(strict=False)
        for field in ("data_root", "rebuild_root", "run_root", "result_root")
    }


def _all_project_artifact_paths(config: Mapping[str, Any]) -> list[Path]:
    roots = (
        "data", "pilot_runs", "pilot_outputs", "results", "reports", "configs", "prereg",
        "docs", "analysis", "experiments", "scripts", "tests",
    )
    output: set[Path] = set()
    universe_self = (ROOT / config["exposure"]["universe_path"]).resolve(strict=False)
    for name in roots:
        root = ROOT / name
        if root.exists():
            for path in root.rglob("*"):
                if "__pycache__" in path.parts:
                    continue
                if path.is_symlink() or (path.exists() and not path.is_file() and not path.is_dir()):
                    raise RuntimeError(f"unclassified/symlink project artifact node: {path}")
                if path.is_file() and path.resolve() != universe_self:
                    output.add(path)
    for path in ROOT.iterdir():
        if path.is_symlink() or (path.exists() and not path.is_file() and not path.is_dir()):
            raise RuntimeError(f"unclassified/symlink top-level project node: {path}")
        if path.is_file() and path.resolve() != universe_self:
            output.add(path)
    return sorted(output, key=lambda value: value.as_posix().encode("utf-8"))


def _prior_artifact_paths(config: Mapping[str, Any]) -> list[Path]:
    excluded_exact = _current_program_allowlist(config)
    output_roots = _current_output_roots(config)
    filtered = []
    for path in _all_project_artifact_paths(config):
        resolved = path.resolve()
        if resolved in excluded_exact:
            continue
        if any(root == resolved or root in resolved.parents for root in output_roots):
            continue
        filtered.append(path)
    return sorted(filtered, key=lambda value: value.as_posix().encode("utf-8"))


def _scan_artifact(path: Path, aliases: Sequence[bytes], digests: set[str]) -> tuple[set[str], set[str]]:
    alias_hits: set[str] = set()
    digest_hits: set[str] = set()
    path_bytes = path.as_posix().encode("utf-8")
    for alias in aliases:
        if alias in path_bytes:
            alias_hits.add(alias.decode("utf-8"))
    overlap = b""
    hex_pattern = re.compile(rb"(?<![0-9a-f])[0-9a-f]{64}(?![0-9a-f])")
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(4 * 1024 * 1024), b""):
            chunk = overlap + block
            for alias in aliases:
                if alias in chunk:
                    alias_hits.add(alias.decode("utf-8"))
            digest_hits.update(match.group(0).decode("ascii") for match in hex_pattern.finditer(chunk) if match.group(0).decode("ascii") in digests)
            overlap = chunk[-128:]
    return alias_hits, digest_hits


_TRACKED_METADATA = {
    "model_forward_run",
    "model_weights_loaded",
    "endpoint_scores_computed",
    "label_only_scouting_disclosed",
    "label_only",
    "stage",
    "status",
    "metadata_scope",
}


def _local_metadata(value: Mapping[str, Any]) -> dict[str, list[Any]]:
    return {
        str(key): [nested]
        for key, nested in value.items()
        if str(key) in _TRACKED_METADATA and isinstance(nested, (str, bool, int, float, type(None)))
    }


def _merge_metadata(*values: Mapping[str, Sequence[Any]]) -> dict[str, list[Any]]:
    output: dict[str, set[Any]] = defaultdict(set)
    for value in values:
        for key, items in value.items():
            output[key].update(items)
    return {key: sorted(items, key=str) for key, items in output.items()}


def _structured_record_hits(
    value: Any,
    *,
    candidate_text: set[str],
    candidate_tokens: set[str],
    candidate_input_ids: set[str],
    text_matcher: NormalizedTextMatcher | None,
    pointer: str,
    inherited_metadata: Mapping[str, Sequence[Any]] | None = None,
) -> tuple[list[dict[str, Any]], int]:
    """Return per-object hits; metadata never unions across sibling records."""
    inherited = dict(inherited_metadata or {})
    hits: list[dict[str, Any]] = []
    input_sequences = 0
    if isinstance(value, Mapping):
        own = _local_metadata(value)
        attached = _merge_metadata(inherited, own)
        candidate_ids = value.get("input_ids")
        if isinstance(candidate_ids, list) and candidate_ids and all(
            isinstance(item, int) and not isinstance(item, bool) for item in candidate_ids
        ):
            input_sequences += 1
            digest = hashlib.sha256(canonical_json_bytes(candidate_ids)).hexdigest()
            if digest in candidate_input_ids:
                hits.append(
                    {
                        "pointer": pointer + "/input_ids",
                        "input_ids_sha256": [digest],
                        "metadata": attached,
                    }
                )
        for key, nested in value.items():
            child_metadata: Mapping[str, Sequence[Any]] = attached
            if isinstance(nested, list) and any(isinstance(item, Mapping) for item in nested):
                scopes = {str(item).upper() for item in attached.get("metadata_scope", [])}
                if "FILE" not in scopes and "RECORD" not in scopes:
                    child_metadata = {}
            nested_hits, nested_count = _structured_record_hits(
                nested,
                candidate_text=candidate_text,
                candidate_tokens=candidate_tokens,
                candidate_input_ids=candidate_input_ids,
                text_matcher=text_matcher,
                pointer=f"{pointer}/{str(key).replace('~', '~0').replace('/', '~1')}",
                inherited_metadata=child_metadata,
            )
            hits.extend(nested_hits)
            input_sequences += nested_count
    elif isinstance(value, list):
        if value and all(isinstance(item, str) for item in value):
            digest = hashlib.sha256(canonical_json_bytes([_normalize_text(item) for item in value])).hexdigest()
            if digest in candidate_tokens:
                hits.append({"pointer": pointer, "token_list_hashes": [digest], "metadata": inherited})
        for index, nested in enumerate(value):
            nested_hits, nested_count = _structured_record_hits(
                nested,
                candidate_text=candidate_text,
                candidate_tokens=candidate_tokens,
                candidate_input_ids=candidate_input_ids,
                text_matcher=text_matcher,
                pointer=f"{pointer}/{index}",
                inherited_metadata=inherited,
            )
            hits.extend(nested_hits)
            input_sequences += nested_count
    elif isinstance(value, str):
        normalized = _normalize_text(value)
        if normalized:
            digest = hashlib.sha256(normalized.encode("utf-8")).hexdigest()
            matched = ({digest} if digest in candidate_text else set()) | (
                text_matcher.find(normalized) if text_matcher is not None else set()
            )
            if matched:
                hits.append({"pointer": pointer, "text_hashes": sorted(matched), "metadata": inherited})
    return hits, input_sequences


def _structured_file_evidence(
    path: Path,
    candidate_text: set[str],
    candidate_tokens: set[str],
    candidate_input_ids: set[str] | None = None,
    text_matcher: NormalizedTextMatcher | None = None,
) -> dict[str, Any]:
    records: list[dict[str, Any]] = []
    file_metadata: dict[str, list[Any]] = {}
    parsed_input_sequences = 0
    errors: list[str] = []
    try:
        if path.suffix.casefold() == ".jsonl":
            with path.open("r", encoding="utf-8", errors="strict") as handle:
                for number, line in enumerate(handle, 1):
                    if not line.strip():
                        continue
                    try:
                        values = (json.loads(line),)
                    except json.JSONDecodeError as exc:
                        raise RuntimeError(f"JSONL line {number}: {exc}") from exc
                    for value in values:
                        row_hits, count = _structured_record_hits(
                            value,
                            candidate_text=candidate_text,
                            candidate_tokens=candidate_tokens,
                            candidate_input_ids=candidate_input_ids or set(),
                            text_matcher=text_matcher,
                            pointer=f"line:{number}",
                        )
                        records.extend(row_hits)
                        parsed_input_sequences += count
        elif path.suffix.casefold() == ".json":
            value = json.loads(path.read_text(encoding="utf-8", errors="strict"))
            if isinstance(value, Mapping):
                top = _local_metadata(value)
                if "FILE" in {str(item).upper() for item in top.get("metadata_scope", [])}:
                    file_metadata = top
            row_hits, count = _structured_record_hits(
                value,
                candidate_text=candidate_text,
                candidate_tokens=candidate_tokens,
                candidate_input_ids=candidate_input_ids or set(),
                text_matcher=text_matcher,
                pointer="$",
            )
            records.extend(row_hits)
            parsed_input_sequences += count
        elif path.suffix.casefold() in TEXT_ARTIFACT_SUFFIXES or path.suffix.casefold() not in OPAQUE_STRUCTURED_SUFFIXES:
            with path.open("r", encoding="utf-8", errors="strict") as handle:
                for number, line in enumerate(handle, 1):
                    normalized = _normalize_text(line)
                    if normalized:
                        digest = hashlib.sha256(normalized.encode("utf-8")).hexdigest()
                        matched = ({digest} if digest in candidate_text else set()) | (
                            text_matcher.find(normalized) if text_matcher is not None else set()
                        )
                        if matched:
                            records.append(
                                {"pointer": f"line:{number}", "text_hashes": sorted(matched), "metadata": {}}
                            )
    except (OSError, UnicodeDecodeError, json.JSONDecodeError, RuntimeError) as exc:
        errors.append(f"{type(exc).__name__}:{exc}")
    return {
        "records": records,
        "file_metadata": file_metadata,
        "parsed_input_id_sequences": parsed_input_sequences,
        "errors": errors,
    }


def _classify_hit(evidence: Mapping[str, Any]) -> str:
    metadata = evidence.get("metadata", {})
    forwards = set(metadata.get("model_forward_run", [])) | set(metadata.get("model_weights_loaded", []))
    endpoints = set(metadata.get("endpoint_scores_computed", []))
    if True in forwards:
        return "MODEL_FORWARD_EXPOSURE"
    if True in endpoints:
        return "ENDPOINT_SCORE_EXPOSURE"
    label_only = True in set(metadata.get("label_only", [])) or True in set(metadata.get("label_only_scouting_disclosed", []))
    statuses = " ".join(map(str, metadata.get("status", []))).upper()
    stages = " ".join(map(str, metadata.get("stage", []))).upper()
    if (
        evidence.get("signed_role_attestation_verified") is True
        and forwards
        and endpoints
        and forwards <= {False}
        and endpoints <= {False}
        and (label_only or "PRESCORE" in statuses or "LABEL" in stages)
    ):
        return "EXPLICIT_LABEL_ONLY_NONFATAL"
    return "UNRESOLVED_BLOCKING_HIT"


def _normalized_string_digests(values: Iterable[str]) -> list[str]:
    return sorted(
        {
            hashlib.sha256(normalized.encode("utf-8")).hexdigest()
            for value in values
            if (normalized := _normalize_text(value))
        }
    )


def _pickle_strings(raw: bytes) -> list[str]:
    values: list[str] = []
    for opcode, argument, _ in pickletools.genops(raw):
        if opcode.name in {"UNICODE", "BINUNICODE", "SHORT_BINUNICODE", "BINUNICODE8"} and isinstance(argument, str):
            values.append(argument)
        elif opcode.name in {"STRING", "BINSTRING", "SHORT_BINSTRING"} and isinstance(argument, (str, bytes)):
            values.append(argument.decode("utf-8", errors="strict") if isinstance(argument, bytes) else argument)
    return values


def _pickle_integer_runs(raw: bytes, minimum_length: int = 2) -> list[list[int]]:
    runs: list[list[int]] = []
    current: list[int] = []
    integer_ops = {"INT", "BININT", "BININT1", "BININT2", "LONG", "LONG1", "LONG4"}
    for opcode, argument, _ in pickletools.genops(raw):
        if opcode.name in integer_ops and isinstance(argument, int) and not isinstance(argument, bool):
            current.append(int(argument))
        else:
            if len(current) >= minimum_length:
                runs.append(current)
            current = []
    if len(current) >= minimum_length:
        runs.append(current)
    return runs


def _integer_objects(value: Any, pointer: str = "$") -> list[tuple[str, np.ndarray]]:
    output: list[tuple[str, np.ndarray]] = []
    try:
        import torch
    except ImportError:
        torch = None  # type: ignore[assignment]
    if torch is not None and isinstance(value, torch.Tensor):
        if not value.is_floating_point() and not value.is_complex() and value.ndim > 0:
            output.append((pointer, value.detach().cpu().numpy()))
    elif isinstance(value, np.ndarray):
        if value.dtype.kind in "biu" and value.ndim > 0:
            output.append((pointer, value))
    elif isinstance(value, Mapping):
        for key, nested in value.items():
            output.extend(_integer_objects(nested, f"{pointer}/{key}"))
    elif isinstance(value, (list, tuple)):
        if len(value) >= 2 and all(isinstance(item, int) and not isinstance(item, bool) for item in value):
            output.append((pointer, np.asarray(value, dtype=np.int64)))
        else:
            for index, nested in enumerate(value):
                output.extend(_integer_objects(nested, f"{pointer}/{index}"))
    return output


def _safe_torch_load(path: Path) -> Any:
    """Load tensor archives with the restricted weights-only unpickler.

    Historical checkpoints include NumPy RNG state.  PyTorch does not include
    NumPy's array constructor and dtype classes in its default weights-only
    allowlist, so enumerate exactly those inert reconstruction types while
    retaining ``weights_only=True``.  Never fall back to unrestricted pickle.
    """
    import torch

    numpy_dtype_types = sorted(
        {
            value
            for name in dir(np.dtypes)
            if name.endswith("DType") and isinstance((value := getattr(np.dtypes, name)), type)
        },
        key=lambda value: f"{value.__module__}.{value.__qualname__}",
    )
    safe_globals = [np.core.multiarray._reconstruct, np.ndarray, np.dtype, *numpy_dtype_types]
    with torch.serialization.safe_globals(safe_globals):
        return torch.load(path, map_location="cpu", weights_only=True, mmap=True)


def _code_strings(value: Any) -> Iterable[str]:
    if isinstance(value, str):
        yield value
    elif isinstance(value, types.CodeType):
        yield value.co_name
        yield value.co_filename
        for constant in value.co_consts:
            yield from _code_strings(constant)
    elif isinstance(value, (tuple, list, set, frozenset)):
        for nested in value:
            yield from _code_strings(nested)


def _code_integer_sequences(value: Any, pointer: str = "$") -> list[tuple[str, np.ndarray]]:
    output: list[tuple[str, np.ndarray]] = []
    if isinstance(value, types.CodeType):
        for index, constant in enumerate(value.co_consts):
            output.extend(_code_integer_sequences(constant, f"{pointer}/co_consts/{index}"))
    elif isinstance(value, (tuple, list)):
        if len(value) >= 2 and all(isinstance(item, int) and not isinstance(item, bool) for item in value):
            output.append((pointer, np.asarray(value, dtype=np.int64)))
        else:
            for index, nested in enumerate(value):
                output.extend(_code_integer_sequences(nested, f"{pointer}/{index}"))
    return output


def _opaque_probe(path: Path) -> dict[str, Any]:
    suffix = path.suffix.casefold()
    strings: list[str] = []
    integer_payloads: list[dict[str, Any]] = []
    if suffix == ".npy":
        array = np.load(path, mmap_mode="r", allow_pickle=False)
        if array.dtype.kind == "O":
            raise RuntimeError(f"object NPY is unsupported without a schema sidecar: {path}")
        if array.dtype.kind in "SU":
            strings.extend(map(str, np.asarray(array).reshape(-1).tolist()))
        if array.dtype.kind in "biu":
            integer_payloads.append({"member": "$ARRAY", "dtype": str(array.dtype), "shape": list(array.shape)})
        format_status = "NUMPY_ARRAY_HEADER_AND_TYPED_PAYLOAD_INSPECTED"
    elif suffix == ".npz":
        with np.load(path, allow_pickle=False) as archive:
            for name in sorted(archive.files):
                array = archive[name]
                if array.dtype.kind == "O":
                    raise RuntimeError(f"object NPZ member is unsupported without a schema sidecar: {path}:{name}")
                strings.append(name)
                if array.dtype.kind in "SU":
                    strings.extend(map(str, np.asarray(array).reshape(-1).tolist()))
                if array.dtype.kind in "biu":
                    integer_payloads.append({"member": name, "dtype": str(array.dtype), "shape": list(array.shape)})
        format_status = "NUMPY_ZIP_ALL_MEMBERS_TYPED_AND_INSPECTED"
    elif suffix == ".pt":
        if not zipfile.is_zipfile(path):
            raise RuntimeError(f"legacy/non-zip torch checkpoint unsupported: {path}")
        with zipfile.ZipFile(path) as archive:
            names = sorted(archive.namelist())
            data_members = [name for name in names if name.endswith("/data.pkl") or name == "data.pkl"]
            version_members = [name for name in names if name.endswith("/version") or name == "version"]
            if len(data_members) != 1 or not version_members:
                raise RuntimeError(f"torch archive lacks unique data.pkl/version: {path}")
            strings.extend(_pickle_strings(archive.read(data_members[0])))
            strings.extend(names)
        try:
            loaded = _safe_torch_load(path)
        except Exception as exc:
            raise RuntimeError(f"restricted weights-only torch inspection failed: {path}: {exc}") from exc
        integer_payloads.extend(
            {"member": pointer, "dtype": str(array.dtype), "shape": list(array.shape)}
            for pointer, array in _integer_objects(loaded)
        )
        format_status = "TORCH_ZIP_RESTRICTED_WEIGHTS_ONLY_AND_MEMBER_INVENTORY_INSPECTED"
    elif suffix == ".pkl":
        raw = path.read_bytes()
        strings.extend(_pickle_strings(raw))
        integer_payloads.extend(
            {
                "member": f"$PICKLE_INTEGER_RUN/{index}",
                "dtype": "python_int",
                "shape": [len(run)],
                "sha256": hashlib.sha256(canonical_json_bytes(run)).hexdigest(),
            }
            for index, run in enumerate(_pickle_integer_runs(raw))
        )
        format_status = "PICKLE_OPCODE_STREAM_INSPECTED_WITHOUT_EXECUTION"
    elif suffix == ".pyc":
        raw = path.read_bytes()
        if len(raw) < 16:
            raise RuntimeError(f"truncated pyc: {path}")
        code = marshal.loads(raw[16:])
        strings.extend(_code_strings(code))
        integer_payloads.extend(
            {"member": pointer, "dtype": str(array.dtype), "shape": list(array.shape)}
            for pointer, array in _code_integer_sequences(code)
        )
        format_status = "PYTHON_BYTECODE_CONSTANTS_INSPECTED_WITHOUT_EXECUTION"
    else:
        raise RuntimeError(f"unsupported opaque suffix: {path}")
    dangerous_names = sorted(
        {
            _normalize_text(value)
            for value in strings
            if _normalize_text(value) in {"input_ids", "token_ids", "source_text", "sentence_text", "raw_text"}
        }
    )
    return {
        "format_status": format_status,
        "normalized_string_hashes": _normalized_string_digests(strings),
        "integer_payloads": integer_payloads,
        "identity_bearing_field_names": dangerous_names,
        "identity_field_payload_disposition": (
            "INTEGER_PAYLOADS_FULLY_ENUMERATED" if integer_payloads else "NO_INTEGER_SEQUENCE_PAYLOAD_FOUND"
        ),
    }


def _artifact_reader(path: Path) -> str:
    suffix = path.suffix.casefold()
    if suffix in {".json", ".jsonl"}:
        return "STRUCTURED_JSON_CONTENT_METADATA_INPUT_IDS_PLUS_LITERAL_BYTES"
    if suffix == ".conllu":
        return "CONLLU_SENTENCE_DOCUMENT_TOKEN_NORMALIZER_PLUS_LITERAL_BYTES"
    if suffix in TEXT_ARTIFACT_SUFFIXES:
        return "UNICODE_LINE_NORMALIZER_PLUS_LITERAL_BYTES"
    if suffix in OPAQUE_STRUCTURED_SUFFIXES:
        return "SIGNED_OPAQUE_STRUCTURAL_SIDECAR_PLUS_LITERAL_BYTES"
    try:
        path.read_text(encoding="utf-8", errors="strict")
    except (OSError, UnicodeDecodeError) as exc:
        raise RuntimeError(f"unknown unsupported binary artifact requires an explicit reader: {path}") from exc
    return "UTF8_SNIFFED_LINE_NORMALIZER_PLUS_LITERAL_BYTES"


def create_opaque_sidecar(config: Mapping[str, Any], signing_key: Path) -> dict[str, Any]:
    output = ROOT / config["exposure"]["opaque_sidecar_path"]
    if output.exists():
        raise RuntimeError("opaque sidecar already exists")
    entries: list[dict[str, Any]] = []
    for path in _prior_artifact_paths(config):
        if path.suffix.casefold() not in OPAQUE_STRUCTURED_SUFFIXES:
            continue
        probe = _opaque_probe(path)
        if probe["identity_bearing_field_names"] and (
            path.suffix.casefold() == ".pkl" or not probe["integer_payloads"]
        ):
            raise RuntimeError(f"identity-bearing opaque artifact lacks proven payload disposition: {path}")
        entries.append(
            {
                "path": path.relative_to(ROOT).as_posix(),
                "bytes": path.stat().st_size,
                "sha256": sha256_file(path),
                **probe,
            }
        )
    payload = {
        "schema_version": "relational_attention_edges_v1_opaque_sidecar_v1",
        "status": "FROZEN_EXACT_OPAQUE_ARTIFACT_STRUCTURAL_AUDIT",
        "builder_sha256": sha256_file(Path(__file__)),
        "common_sha256": sha256_file(ROOT / "scripts/relational_attention_edges_v1.py"),
        "entries": entries,
        "entries_sha256": inventory_digest(entries),
        "files": len(entries),
        "pickle_or_bytecode_executed": False,
        "unknown_opaque_files_accepted": 0,
    }
    sign_payload(output, payload, load_signing_key(signing_key, config["signer"]))
    return payload


def verify_opaque_sidecar(config: Mapping[str, Any]) -> dict[str, Any]:
    spec = config["exposure"]
    path = ROOT / spec["opaque_sidecar_path"]
    if sha256_file(path) != spec["opaque_sidecar_sha256"]:
        raise RuntimeError("opaque sidecar config binding drift")
    payload = verify_signed(path, config["signer"]["public_key_fingerprint_sha256"])
    if (
        payload.get("status") != "FROZEN_EXACT_OPAQUE_ARTIFACT_STRUCTURAL_AUDIT"
        or payload.get("builder_sha256") != sha256_file(Path(__file__))
        or payload.get("common_sha256") != sha256_file(ROOT / "scripts/relational_attention_edges_v1.py")
        or payload.get("unknown_opaque_files_accepted") != 0
        or payload.get("pickle_or_bytecode_executed") is not False
    ):
        raise RuntimeError("opaque sidecar identity/status drift")
    current = [path for path in _prior_artifact_paths(config) if path.suffix.casefold() in OPAQUE_STRUCTURED_SUFFIXES]
    if [entry["path"] for entry in payload["entries"]] != [path.relative_to(ROOT).as_posix() for path in current]:
        raise RuntimeError("opaque sidecar path-set drift")
    for entry, path in zip(payload["entries"], current):
        if path.stat().st_size != entry["bytes"] or sha256_file(path) != entry["sha256"]:
            raise RuntimeError(f"opaque sidecar entry drift: {entry['path']}")
    if inventory_digest(payload["entries"]) != payload["entries_sha256"]:
        raise RuntimeError("opaque sidecar inventory digest drift")
    return payload


def _canonical_role_attestations(
    config: Mapping[str, Any], prior: Mapping[str, Path]
) -> list[dict[str, Any]]:
    entries: list[dict[str, Any]] = []
    for raw in config["exposure"].get("role_attestations", []):
        if not isinstance(raw, Mapping):
            raise RuntimeError("role attestation must be an object")
        path_text = str(raw.get("path", ""))
        path = prior.get(path_text)
        if path is None or raw.get("artifact_sha256") != sha256_file(path):
            raise RuntimeError(f"role attestation path/hash is not an exact prior artifact: {path_text}")
        entry = {
            "path": path_text,
            "artifact_sha256": raw["artifact_sha256"],
            "pointer": str(raw.get("pointer", "")),
            "stage": raw.get("stage"),
            "model_forward_run": raw.get("model_forward_run"),
            "endpoint_scores_computed": raw.get("endpoint_scores_computed"),
            "label_only": raw.get("label_only"),
        }
        if (
            not entry["pointer"]
            or entry["stage"] != "LABEL_ONLY_PRESCORE"
            or entry["model_forward_run"] is not False
            or entry["endpoint_scores_computed"] is not False
            or entry["label_only"] is not True
        ):
            raise RuntimeError(f"invalid role attestation: {path_text}")
        entries.append(entry)
    entries.sort(key=lambda row: (row["path"].encode("utf-8"), row["pointer"].encode("utf-8")))
    if len({(row["path"], row["pointer"]) for row in entries}) != len(entries):
        raise RuntimeError("duplicate role attestation")
    return entries


def create_role_sidecar(config: Mapping[str, Any], signing_key: Path) -> dict[str, Any]:
    output = ROOT / config["exposure"]["role_sidecar_path"]
    if output.exists():
        raise RuntimeError("role sidecar already exists")
    prior = {path.relative_to(ROOT).as_posix(): path for path in _prior_artifact_paths(config)}
    entries = _canonical_role_attestations(config, prior)
    payload = {
        "schema_version": "relational_attention_edges_v1_role_sidecar_v1",
        "status": "FROZEN_EXACT_RECORD_ROLE_ATTESTATIONS",
        "builder_sha256": sha256_file(Path(__file__)),
        "common_sha256": sha256_file(ROOT / "scripts/relational_attention_edges_v1.py"),
        "entries": entries,
        "entries_sha256": inventory_digest(entries),
        "files": len({row["path"] for row in entries}),
    }
    sign_payload(output, payload, load_signing_key(signing_key, config["signer"]))
    return payload


def verify_role_sidecar(config: Mapping[str, Any]) -> dict[str, Any]:
    spec = config["exposure"]
    path = ROOT / spec["role_sidecar_path"]
    if sha256_file(path) != spec["role_sidecar_sha256"]:
        raise RuntimeError("role sidecar config binding drift")
    payload = verify_signed(path, config["signer"]["public_key_fingerprint_sha256"])
    raw_entries = payload.get("entries")
    if not isinstance(raw_entries, list) or any(not isinstance(entry, Mapping) for entry in raw_entries):
        raise RuntimeError("role sidecar entries must be a list of objects")
    entries = [dict(entry) for entry in raw_entries]
    if (
        payload.get("schema_version") != "relational_attention_edges_v1_role_sidecar_v1"
        or payload.get("status") != "FROZEN_EXACT_RECORD_ROLE_ATTESTATIONS"
        or payload.get("builder_sha256") != sha256_file(Path(__file__))
        or payload.get("common_sha256") != sha256_file(ROOT / "scripts/relational_attention_edges_v1.py")
        or inventory_digest(entries) != payload.get("entries_sha256")
    ):
        raise RuntimeError("role sidecar identity/inventory drift")
    prior = {path.relative_to(ROOT).as_posix(): path for path in _prior_artifact_paths(config)}
    expected = _canonical_role_attestations(config, prior)
    if entries != expected:
        raise RuntimeError("role sidecar entries/config attestations drift")
    if payload.get("files") != len({entry["path"] for entry in entries}):
        raise RuntimeError("role sidecar file count drift")
    if len({(entry["path"], entry["pointer"]) for entry in entries}) != len(entries):
        raise RuntimeError("duplicate role sidecar entry")
    for entry in entries:
        current = prior.get(entry.get("path"))
        if (
            current is None
            or sha256_file(current) != entry.get("artifact_sha256")
            or not isinstance(entry.get("pointer"), str)
            or not entry.get("pointer")
            or entry.get("stage") != "LABEL_ONLY_PRESCORE"
            or entry.get("model_forward_run") is not False
            or entry.get("endpoint_scores_computed") is not False
            or entry.get("label_only") is not True
        ):
            raise RuntimeError(f"role sidecar entry drift: {entry.get('path')}")
    return payload


def _attach_role_attestation(
    evidence: dict[str, Any], artifact_sha256: str, role_entries: Mapping[tuple[str, str, str], Mapping[str, Any]]
) -> None:
    key = (str(evidence["path"]), artifact_sha256, str(evidence["pointer"]))
    attestation = role_entries.get(key)
    if attestation is None:
        return
    evidence["signed_role_attestation_verified"] = True
    evidence["metadata"] = _merge_metadata(
        evidence.get("metadata", {}),
        {
            "model_forward_run": [False],
            "endpoint_scores_computed": [False],
            "label_only": [True],
            "stage": ["LABEL_ONLY_PRESCORE"],
        },
    )


def create_exposure_universe(config: Mapping[str, Any], signing_key: Path) -> dict[str, Any]:
    output = ROOT / config["exposure"]["universe_path"]
    if output.exists():
        raise RuntimeError("exposure universe already exists")
    entries = []
    opaque = verify_opaque_sidecar(config)
    role = verify_role_sidecar(config)
    opaque_by_path = {entry["path"]: entry for entry in opaque["entries"]}
    for path in _prior_artifact_paths(config):
        reader = _artifact_reader(path)
        if reader == "SIGNED_OPAQUE_STRUCTURAL_SIDECAR_PLUS_LITERAL_BYTES" and path.relative_to(ROOT).as_posix() not in opaque_by_path:
            raise RuntimeError(f"opaque artifact lacks exact sidecar: {path}")
        entries.append({"path": path.relative_to(ROOT).as_posix(), "bytes": path.stat().st_size, "sha256": sha256_file(path), "reader": reader, "disposition": "MUST_SCAN_NO_SKIP"})
    excluded_exact = _current_program_allowlist(config)
    allowlist_bindings = []
    for path in _all_project_artifact_paths(config):
        if path.resolve() not in excluded_exact:
            continue
        allowlist_bindings.append(
            {
                "path": path.relative_to(ROOT).as_posix(),
                "bytes": path.stat().st_size,
                "sha256": sha256_file(path),
                "disposition": "EXCLUDED_EXACT_CURRENT_PROGRAM_OR_VERIFIED_D1_RETIREMENT",
            }
        )
    payload = {
        "schema_version": "relational_attention_edges_v1_exposure_universe_v1",
        "status": "FROZEN_EXHAUSTIVE_PRIOR_ARTIFACT_UNIVERSE",
        "config_projection_sha256": semantic_config_digest(config),
        "builder_sha256": sha256_file(Path(__file__)),
        "common_sha256": sha256_file(ROOT / "scripts/relational_attention_edges_v1.py"),
        "opaque_sidecar_sha256": sha256_file(ROOT / config["exposure"]["opaque_sidecar_path"]),
        "role_sidecar_sha256": sha256_file(ROOT / config["exposure"]["role_sidecar_path"]),
        "entries": entries,
        "entries_sha256": inventory_digest(entries),
        "files": len(entries),
        "allowlist_bindings": allowlist_bindings,
        "allowlist_bindings_sha256": inventory_digest(allowlist_bindings),
        "allowlisted_files": len(allowlist_bindings),
        "skipped_files": 0,
    }
    sign_payload(output, payload, load_signing_key(signing_key, config["signer"]))
    return payload


def verify_exposure_universe(config: Mapping[str, Any]) -> dict[str, Any]:
    path = ROOT / config["exposure"]["universe_path"]
    payload = verify_signed(path, config["signer"]["public_key_fingerprint_sha256"])
    if payload.get("status") != "FROZEN_EXHAUSTIVE_PRIOR_ARTIFACT_UNIVERSE" or payload.get("config_projection_sha256") != semantic_config_digest(config):
        raise RuntimeError("exposure universe identity drift")
    if payload.get("builder_sha256") != sha256_file(Path(__file__)) or payload.get("common_sha256") != sha256_file(ROOT / "scripts/relational_attention_edges_v1.py"):
        raise RuntimeError("exposure universe implementation drift")
    opaque = verify_opaque_sidecar(config)
    if payload.get("opaque_sidecar_sha256") != sha256_file(ROOT / config["exposure"]["opaque_sidecar_path"]):
        raise RuntimeError("exposure universe opaque-sidecar drift")
    verify_role_sidecar(config)
    if payload.get("role_sidecar_sha256") != sha256_file(ROOT / config["exposure"]["role_sidecar_path"]):
        raise RuntimeError("exposure universe role-sidecar drift")
    current_paths = _prior_artifact_paths(config)
    if [entry["path"] for entry in payload["entries"]] != [path.relative_to(ROOT).as_posix() for path in current_paths]:
        raise RuntimeError("exposure universe path-set drift")
    for entry, current in zip(payload["entries"], current_paths):
        if current.stat().st_size != entry["bytes"] or sha256_file(current) != entry["sha256"] or entry.get("disposition") != "MUST_SCAN_NO_SKIP":
            raise RuntimeError(f"exposure universe entry drift: {entry['path']}")
    if inventory_digest(payload["entries"]) != payload["entries_sha256"] or payload.get("skipped_files") != 0:
        raise RuntimeError("exposure universe self-digest/skip drift")
    if inventory_digest(payload.get("allowlist_bindings", [])) != payload.get("allowlist_bindings_sha256"):
        raise RuntimeError("exposure universe exact-allowlist digest drift")
    expected_allowlist = {path.resolve() for path in _current_program_allowlist(config)}
    for entry in payload.get("allowlist_bindings", []):
        current = ROOT / entry["path"]
        if current.resolve() not in expected_allowlist or not current.is_file():
            raise RuntimeError(f"exposure universe allowlist path drift: {entry['path']}")
        if current.stat().st_size != entry["bytes"] or sha256_file(current) != entry["sha256"]:
            raise RuntimeError(f"exposure universe allowlist entry drift: {entry['path']}")
    return payload


def input_id_exposure_audit(config: Mapping[str, Any], aligned: Mapping[str, Sequence[Sentence]]) -> dict[str, Any]:
    candidate: dict[str, list[dict[str, str]]] = defaultdict(list)
    candidate_digests: set[str] = set()
    for source, rows in aligned.items():
        for row in rows:
            assert row.input_ids is not None
            digest = hashlib.sha256(canonical_json_bytes(row.input_ids)).hexdigest()
            candidate[digest].append({"source": source, "sentence": row.key})
            candidate_digests.add(digest)
    hits: list[dict[str, Any]] = []
    scanned_files = 0
    parsed_sequences = 0
    scan_errors: list[dict[str, str]] = []
    universe = verify_exposure_universe(config)
    opaque = verify_opaque_sidecar(config)
    opaque_by_path = {entry["path"]: entry for entry in opaque["entries"]}
    role = verify_role_sidecar(config)
    role_entries = {
        (entry["path"], entry["artifact_sha256"], entry["pointer"]): entry for entry in role["entries"]
    }
    for entry in universe["entries"]:
        path = ROOT / entry["path"]
        if entry["reader"] != "STRUCTURED_JSON_CONTENT_METADATA_INPUT_IDS_PLUS_LITERAL_BYTES":
            continue
        scanned_files += 1
        structured = _structured_file_evidence(path, set(), set(), candidate_digests)
        if structured["errors"]:
            scan_errors.append({"path": entry["path"], "error": ";".join(structured["errors"])})
            continue
        parsed_sequences += int(structured["parsed_input_id_sequences"])
        for record in structured["records"]:
            for digest in record.get("input_ids_sha256", []):
                evidence = {
                    "path": entry["path"],
                    "pointer": record["pointer"],
                    "input_ids_sha256": digest,
                    "candidate_rows": candidate[digest][:20],
                    "metadata": record.get("metadata", {}),
                }
                _attach_role_attestation(evidence, entry["sha256"], role_entries)
                evidence["role"] = _classify_hit(evidence)
                hits.append(evidence)
    candidate_lengths = {len(row.input_ids or []) for rows in aligned.values() for row in rows}
    for entry in universe["entries"]:
        opaque_entry = opaque_by_path.get(entry["path"])
        if opaque_entry is None or not opaque_entry.get("integer_payloads"):
            continue
        path = ROOT / entry["path"]
        suffix = path.suffix.casefold()
        arrays: list[tuple[str, np.ndarray]] = []
        if suffix == ".npy":
            arrays.append(("$ARRAY", np.load(path, mmap_mode="r", allow_pickle=False)))
        elif suffix == ".npz":
            with np.load(path, allow_pickle=False) as archive:
                arrays.extend((name, np.asarray(archive[name])) for name in archive.files)
        elif suffix == ".pt":
            arrays.extend(_integer_objects(_safe_torch_load(path)))
        elif suffix == ".pkl":
            arrays.extend(
                (f"$PICKLE_INTEGER_RUN/{index}", np.asarray(run, dtype=np.int64))
                for index, run in enumerate(_pickle_integer_runs(path.read_bytes()))
            )
        elif suffix == ".pyc":
            raw = path.read_bytes()
            arrays.extend(_code_integer_sequences(marshal.loads(raw[16:])))
        else:
            continue
        for member, array in arrays:
            if array.dtype.kind not in "biu" or array.ndim == 0:
                continue
            width = int(array.shape[-1]) if array.ndim > 1 else int(array.shape[0])
            if width not in candidate_lengths:
                continue
            rows = np.asarray(array).reshape(-1, width)
            for row_index, row in enumerate(rows):
                digest = hashlib.sha256(canonical_json_bytes([int(value) for value in row.tolist()])).hexdigest()
                if digest in candidate_digests:
                    evidence = {
                        "path": entry["path"],
                        "pointer": f"$OPAQUE/{member}/{row_index}",
                        "input_ids_sha256": digest,
                        "candidate_rows": candidate[digest][:20],
                        "metadata": {},
                    }
                    _attach_role_attestation(evidence, entry["sha256"], role_entries)
                    evidence["role"] = _classify_hit(evidence)
                    hits.append(evidence)
    blocking = [row for row in hits if row["role"] != "EXPLICIT_LABEL_ONLY_NONFATAL"]
    return {
        "scanned_json_files": scanned_files,
        "parsed_prior_input_id_sequences": parsed_sequences,
        "hits": hits,
        "blocking_hits": blocking,
        "scan_errors": scan_errors,
        "model_forward_exposure_found": any(row["role"] == "MODEL_FORWARD_EXPOSURE" for row in hits),
        "endpoint_score_exposure_found": any(row["role"] == "ENDPOINT_SCORE_EXPOSURE" for row in hits),
        "eligible": not blocking and not scan_errors,
    }


def exposure_audit(config: Mapping[str, Any], sentences: Mapping[str, Sequence[Sentence]]) -> dict[str, Any]:
    universe = verify_exposure_universe(config)
    prior_paths = [
        ROOT / entry["path"]
        for entry in universe["entries"]
        if entry["reader"] == "CONLLU_SENTENCE_DOCUMENT_TOKEN_NORMALIZER_PLUS_LITERAL_BYTES"
    ]
    prior_hashes = _prior_sentence_hashes(prior_paths)
    prior_document_hashes = _prior_document_hashes(prior_paths)
    new_raw_hashes = {digest for spec in config["sources"].values() for digest in spec["files"].values()}
    prior_file_hash_hits = [
        {"path": entry["path"], "sha256": entry["sha256"]}
        for entry in universe["entries"]
        if entry["sha256"] in new_raw_hashes
    ]

    source_reports: dict[str, Any] = {}
    candidate_document_digests: dict[str, dict[str, str]] = {}
    ineligible = bool(prior_file_hash_hits)
    for source, values in sentences.items():
        candidate_document_digests[source] = _document_hashes(values)
        collisions = [row for row in values if row.token_hash in prior_hashes]
        document_collisions = [
            {"document_id": document, "sha256": digest, "prior": prior_document_hashes[digest]}
            for document, digest in candidate_document_digests[source].items()
            if digest in prior_document_hashes
        ]
        if document_collisions:
            ineligible = True
        by_document: dict[str, set[str]] = defaultdict(set)
        for row in collisions:
            by_document[row.document_id].add(row.token_hash)
        long_documents = {
            row.document_id
            for row in collisions
            if len(row.tokens) >= int(config["exposure"]["long_collision_min_words"])
        }
        multi_short_documents = {
            doc
            for doc, digests in by_document.items()
            if len(digests) >= int(config["exposure"]["short_collisions_per_document_to_remove"])
        }
        removed_documents = long_documents | multi_short_documents
        removed_sentences = {
            row.key for row in collisions if row.document_id not in removed_documents
        }
        source_reports[source] = {
            "candidate_sentences": len(values),
            "candidate_documents": len({row.document_id for row in values}),
            "sentence_collisions": len(collisions),
            "normalized_document_collisions": document_collisions,
            "long_collision_documents": sorted(long_documents),
            "multi_short_collision_documents": sorted(multi_short_documents),
            "removed_documents": sorted(removed_documents),
            "removed_sentences": sorted(removed_sentences),
            "collision_examples": [
                {
                    "sentence": row.key,
                    "words": len(row.tokens),
                    "prior_example_path": prior_hashes[row.token_hash]["example_path"],
                }
                for row in sorted(collisions, key=lambda item: item.key.encode("utf-8"))[:50]
            ],
        }

    # Search all historical project artifact families. New-program development paths are excluded.
    aliases = (
        "UD_Ukrainian-IU",
        "UD_Arabic-PADT",
        "UD_Latvian-LVTB",
        "uk_iu-ud-",
        "ar_padt-ud-",
        "lv_lvtb-ud-",
    )
    candidate_digests = set(new_raw_hashes)
    for source, values in sentences.items():
        removed_documents = set(source_reports[source]["removed_documents"])
        removed_sentences = set(source_reports[source]["removed_sentences"])
        retained = [row for row in values if row.document_id not in removed_documents and row.key not in removed_sentences]
        candidate_digests.update(row.sentence_hash for row in retained)
        candidate_digests.update(row.token_hash for row in retained)
        candidate_digests.update(
            digest for document, digest in candidate_document_digests[source].items() if document not in removed_documents
        )
    candidate_text_by_normalized = {
        _normalize_text(row.text): hashlib.sha256(_normalize_text(row.text).encode("utf-8")).hexdigest()
        for source, values in sentences.items()
        for row in values
        if row.document_id not in set(source_reports[source]["removed_documents"])
        and row.key not in set(source_reports[source]["removed_sentences"])
    }
    candidate_text_hashes = set(candidate_text_by_normalized.values())
    embedded_matcher = NormalizedTextMatcher(
        {
            text: digest
            for text, digest in candidate_text_by_normalized.items()
            if len(text) >= int(config["exposure"]["embedded_text_min_characters"])
        }
    )
    candidate_token_list_hashes = {
        hashlib.sha256(canonical_json_bytes([_normalize_text(token.form) for token in row.tokens])).hexdigest()
        for source, values in sentences.items()
        for row in values
        if row.document_id not in set(source_reports[source]["removed_documents"])
        and row.key not in set(source_reports[source]["removed_sentences"])
    }
    opaque = verify_opaque_sidecar(config)
    opaque_by_path = {entry["path"]: entry for entry in opaque["entries"]}
    role = verify_role_sidecar(config)
    role_entries = {
        (entry["path"], entry["artifact_sha256"], entry["pointer"]): entry for entry in role["entries"]
    }
    artifact_hits: list[dict[str, Any]] = []
    scan_ledger: list[dict[str, Any]] = []
    scan_errors: list[dict[str, str]] = []
    for entry in universe["entries"]:
        path = ROOT / entry["path"]
        try:
            found_aliases, found_digests = _scan_artifact(path, [value.encode("utf-8") for value in aliases], candidate_digests)
            structured = _structured_file_evidence(
                path, candidate_text_hashes, candidate_token_list_hashes, text_matcher=embedded_matcher
            )
            if structured["errors"]:
                raise RuntimeError(";".join(structured["errors"]))
            entry_hits: list[dict[str, Any]] = []
            if found_aliases or found_digests:
                entry_hits.append(
                    {
                        "path": entry["path"],
                        "pointer": "$FILE_LITERAL_BYTES",
                        "aliases": sorted(found_aliases),
                        "candidate_digests": sorted(found_digests),
                        "metadata": structured["file_metadata"],
                    }
                )
            for record in structured["records"]:
                entry_hits.append(
                    {
                        "path": entry["path"],
                        "pointer": record["pointer"],
                        "normalized_text_hashes": record.get("text_hashes", []),
                        "normalized_token_list_hashes": record.get("token_list_hashes", []),
                        "metadata": record.get("metadata", {}),
                    }
                )
            opaque_entry = opaque_by_path.get(entry["path"])
            if opaque_entry is not None:
                opaque_text_hits = sorted(
                    set(opaque_entry.get("normalized_string_hashes", [])) & candidate_text_hashes
                )
                if opaque_text_hits:
                    entry_hits.append(
                        {
                            "path": entry["path"],
                            "pointer": "$SIGNED_OPAQUE_SIDECAR_STRINGS",
                            "normalized_text_hashes": opaque_text_hits,
                            "metadata": {},
                        }
                    )
            for evidence in entry_hits:
                _attach_role_attestation(evidence, entry["sha256"], role_entries)
                evidence["role"] = _classify_hit(evidence)
            artifact_hits.extend(entry_hits)
            roles = sorted({str(evidence["role"]) for evidence in entry_hits})
            scan_ledger.append(
                {
                    "path": entry["path"],
                    "bytes": entry["bytes"],
                    "sha256": entry["sha256"],
                    "reader": entry["reader"],
                    "status": "SCANNED",
                    "hit": bool(entry_hits),
                    "roles": roles,
                }
            )
        except Exception as exc:
            error = {"path": entry["path"], "error": f"{type(exc).__name__}:{exc}"}
            scan_errors.append(error)
            scan_ledger.append({"path": entry["path"], "bytes": entry["bytes"], "sha256": entry["sha256"], "reader": entry["reader"], "status": "ERROR_BLOCKING", "hit": False, "role": None})
    blocking_artifact_hits = [row for row in artifact_hits if row["role"] != "EXPLICIT_LABEL_ONLY_NONFATAL"]
    if blocking_artifact_hits:
        ineligible = True
    if scan_errors:
        ineligible = True
    model_forward_hits = [row for row in artifact_hits if row["role"] == "MODEL_FORWARD_EXPOSURE"]
    endpoint_score_hits = [row for row in artifact_hits if row["role"] == "ENDPOINT_SCORE_EXPOSURE"]
    return {
        "schema_version": "relational_attention_edges_v1_exposure_audit_v1",
        "status": "INELIGIBLE" if ineligible else "PASS_PROJECT_OUTCOME_UNSEEN_WITH_LABEL_ONLY_SCOUTING",
        "prior_conllu_files": len(prior_paths),
        "prior_sentence_hashes": len(prior_hashes),
        "exact_prior_raw_file_hits": prior_file_hash_hits,
        "historical_artifact_hits": artifact_hits,
        "blocking_artifact_hits": blocking_artifact_hits,
        "exposure_universe_sha256": sha256_file(ROOT / config["exposure"]["universe_path"]),
        "scan_ledger": scan_ledger,
        "scan_ledger_sha256": inventory_digest(scan_ledger),
        "scan_errors": scan_errors,
        "skipped_files": 0,
        "sources": source_reports,
        "model_forward_on_candidate_source_found": bool(model_forward_hits),
        "endpoint_score_on_candidate_source_found": bool(endpoint_score_hits),
        "label_only_scouting_disclosed": True,
        "pythia_pretraining_overlap": "unknown",
    }


def align_sentences(
    sentences: Sequence[Sentence], tokenizer: Any, config: Mapping[str, Any], audit: Mapping[str, Any]
) -> tuple[list[Sentence], dict[str, int]]:
    report = Counter()
    source_report = audit["sources"][sentences[0].source] if sentences else {"removed_documents": [], "removed_sentences": []}
    removed_docs, removed_sentences = set(source_report["removed_documents"]), set(source_report["removed_sentences"])
    output: list[Sentence] = []
    for sentence in sentences:
        report["seen"] += 1
        if sentence.document_id in removed_docs or sentence.key in removed_sentences:
            report["exposure_removed"] += 1
            continue
        if sentence.has_mwt:
            report["multiword_token"] += 1
            continue
        if sentence.has_empty:
            report["empty_node"] += 1
            continue
        if not sentence.reconstruction_exact:
            report["surface_mismatch"] += 1
            continue
        encoded = tokenizer(
            sentence.text,
            add_special_tokens=False,
            return_offsets_mapping=True,
            truncation=False,
        )
        input_ids = list(map(int, encoded["input_ids"]))
        offsets = [tuple(map(int, pair)) for pair in encoded["offset_mapping"]]
        if not input_ids or len(input_ids) > int(config["model"]["max_sequence_length"]):
            report["length"] += 1
            continue
        spans: dict[int, list[int]] = {}
        assigned_subtokens: set[int] = set()
        valid = True
        for token in sentence.tokens:
            selected = [
                index
                for index, (start, end) in enumerate(offsets)
                if end > token.char_start and start < token.char_end and end > start
            ]
            if (
                not selected
                or selected != list(range(selected[0], selected[-1] + 1))
                or any(index in assigned_subtokens for index in selected)
            ):
                valid = False
                break
            spans[token.token_id] = selected
            assigned_subtokens.update(selected)
        if not valid:
            report["ambiguous_alignment"] += 1
            continue
        sentence.input_ids, sentence.offsets, sentence.spans = input_ids, offsets, spans
        output.append(sentence)
        report["retained"] += 1
    return output, dict(report)


def _ancestors(token_id: int, by_id: Mapping[int, Token]) -> set[int]:
    output: set[int] = set()
    current = token_id
    while current in by_id and by_id[current].head:
        current = by_id[current].head
        if current in output:
            raise RuntimeError("dependency cycle")
        output.add(current)
    return output


def _candidate(sentence: Sentence, first: Token, second: Token, *, positive: bool, relation: str | None) -> dict[str, Any]:
    assert sentence.input_ids is not None and sentence.spans is not None
    earlier, later = (first, second) if first.order < second.order else (second, first)
    key_positions = sentence.spans[earlier.token_id]
    query_positions = sentence.spans[later.token_id]
    query_index = query_positions[-1]
    key_last = key_positions[-1]
    query_is_head = bool(positive and later.token_id in {first.head, second.head})
    # The primary feature is a pre-softmax rotary QK logit, not normalized
    # attention probability.  Match relative geometry and endpoint types exactly;
    # absolute prefix opportunity and total suffix length are not part of the
    # denominator-free primary estimand.
    stratum = (
        query_index - key_last,
        later.order - earlier.order,
        later.upos,
        earlier.upos,
        len(query_positions),
        len(key_positions),
    )
    return {
        "candidate_id": stable_hex(NAMESPACE, sentence.key, first.token_id, second.token_id, int(positive)),
        "sentence_key": sentence.key,
        "document_id": sentence.document_id,
        "query_index": query_index,
        "key_positions": key_positions,
        "query_token_id": later.token_id,
        "key_token_id": earlier.token_id,
        "query_is_head": query_is_head,
        "stratum": stratum,
        "relation": relation,
    }


def enumerate_candidates(sentences: Sequence[Sentence]) -> dict[str, dict[str, dict[tuple[Any, ...], list[dict[str, Any]]]]]:
    by_document: dict[str, dict[str, dict[tuple[Any, ...], list[dict[str, Any]]]]] = defaultdict(
        lambda: {"positive": defaultdict(list), "negative": defaultdict(list)}
    )
    positive_strata_by_partition: dict[int, set[tuple[Any, ...]]] = {0: set(), 1: set()}
    sentence_cache: list[tuple[Sentence, dict[int, Token], dict[int, set[int]]]] = []
    for sentence in sentences:
        by_id = {token.token_id: token for token in sentence.tokens}
        ancestors = {token.token_id: _ancestors(token.token_id, by_id) for token in sentence.tokens}
        sentence_cache.append((sentence, by_id, ancestors))
        partition = int.from_bytes(stable_digest(NAMESPACE, sentence.source, sentence.document_id)[:8], "big") & 1
        for child in sentence.tokens:
            if child.head == 0 or child.head not in by_id:
                continue
            head = by_id[child.head]
            row = _candidate(sentence, child, head, positive=True, relation=coarse_relation(child.deprel))
            by_document[sentence.document_id]["positive"][tuple(row["stratum"])].append(row)
            positive_strata_by_partition[partition].add(tuple(row["stratum"]))

    for sentence, by_id, ancestors in sentence_cache:
        partition = int.from_bytes(stable_digest(NAMESPACE, sentence.source, sentence.document_id)[:8], "big") & 1
        needed = positive_strata_by_partition[1 - partition]
        tokens = sentence.tokens
        for left_index, left in enumerate(tokens):
            for right in tokens[left_index + 1 :]:
                if left.head == right.token_id or right.head == left.token_id:
                    continue
                if right.token_id in ancestors[left.token_id] or left.token_id in ancestors[right.token_id]:
                    continue
                row = _candidate(sentence, left, right, positive=False, relation=None)
                stratum = tuple(row["stratum"])
                if stratum in needed:
                    by_document[sentence.document_id]["negative"][stratum].append(row)

    # Candidate reuse is bounded prospectively and deterministically within each document/stratum.
    for roles in by_document.values():
        for groups in roles.values():
            for stratum, values in groups.items():
                values.sort(key=lambda row: row["candidate_id"])
                groups[stratum] = values[:12]
    return by_document


def _orientation_rows(
    source: str,
    positive_doc: str,
    negative_doc: str,
    by_document: Mapping[str, Mapping[str, Mapping[tuple[Any, ...], Sequence[Mapping[str, Any]]]]],
    *,
    cap: int,
) -> list[dict[str, Any]]:
    positives = by_document[positive_doc]["positive"]
    negatives = by_document[negative_doc]["negative"]
    candidate_pairs: list[dict[str, Any]] = []
    for stratum in sorted(set(positives) & set(negatives), key=lambda value: canonical_json_bytes(value)):
        p_rows = sorted(positives[stratum], key=lambda row: str(row["candidate_id"]))
        n_rows = sorted(negatives[stratum], key=lambda row: str(row["candidate_id"]))
        for edge, nonedge in zip(p_rows, n_rows):
            pair_id = stable_hex(NAMESPACE, source, edge["candidate_id"], nonedge["candidate_id"])
            candidate_pairs.append({"pair_id": pair_id, "edge": dict(edge), "nonedge": dict(nonedge), "stratum": list(stratum)})
    candidate_pairs.sort(key=lambda row: str(row["pair_id"]))
    return candidate_pairs[:cap]


def match_documents(
    source: str,
    by_document: Mapping[str, Mapping[str, Mapping[tuple[Any, ...], Sequence[Mapping[str, Any]]]]],
    config: Mapping[str, Any],
) -> list[dict[str, Any]]:
    docs = sorted(by_document, key=lambda value: value.encode("utf-8"))
    left = [doc for doc in docs if int.from_bytes(stable_digest(NAMESPACE, source, doc)[:8], "big") & 1 == 0]
    right = [doc for doc in docs if int.from_bytes(stable_digest(NAMESPACE, source, doc)[:8], "big") & 1 == 1]
    candidates: list[tuple[int, int, int, str]] = []
    cap = int(config["matching"]["max_pairs_per_orientation"])
    for i, left_doc in enumerate(left):
        lp, ln = by_document[left_doc]["positive"], by_document[left_doc]["negative"]
        if not lp or not ln:
            continue
        for j, right_doc in enumerate(right):
            rp, rn = by_document[right_doc]["positive"], by_document[right_doc]["negative"]
            if not rp or not rn:
                continue
            yield_lr = min(cap, sum(min(len(lp[s]), len(rn[s])) for s in set(lp) & set(rn)))
            yield_rl = min(cap, sum(min(len(rp[s]), len(ln[s])) for s in set(rp) & set(ln)))
            if yield_lr and yield_rl:
                candidates.append((i, j, yield_lr + yield_rl, stable_hex(NAMESPACE, source, left_doc, right_doc)))
    if not candidates:
        return []
    rows, cols = len(left), len(right)
    pair_count = rows * cols
    max_matches = min(rows, cols)
    yield_base = max_matches * pair_count + 1
    cardinality_base = max_matches * (24 * yield_base + pair_count) + 1
    matrix = np.zeros((rows, cols), dtype=np.int64)
    ranked = sorted(candidates, key=lambda item: item[3])
    for rank, (i, j, pair_yield, _) in enumerate(ranked):
        lex_bonus = len(ranked) - rank
        matrix[i, j] = cardinality_base + pair_yield * yield_base + lex_bonus
    selected_i, selected_j = linear_sum_assignment(matrix, maximize=True)
    selected: list[dict[str, Any]] = []
    for i, j in zip(selected_i.tolist(), selected_j.tolist()):
        if matrix[i, j] <= 0:
            continue
        left_doc, right_doc = left[i], right[j]
        lr = _orientation_rows(source, left_doc, right_doc, by_document, cap=cap)
        rl = _orientation_rows(source, right_doc, left_doc, by_document, cap=cap)
        if not lr or not rl:
            raise RuntimeError("selected document pair lost bidirectional support")
        component_id = "component:" + stable_hex(NAMESPACE, source, left_doc, right_doc)[:24]
        selected.append(
            {
                "component_id": component_id,
                "documents": sorted((left_doc, right_doc), key=lambda value: value.encode("utf-8")),
                "left_positive_pairs": lr,
                "right_positive_pairs": rl,
                "pair_count": len(lr) + len(rl),
            }
        )
    selected.sort(key=lambda row: str(row["component_id"]))
    return selected


def assign_folds(components: list[dict[str, Any]], folds: int) -> None:
    pair_totals = [0] * folds
    component_totals = [0] * folds
    ordered = sorted(components, key=lambda row: (-int(row["pair_count"]), str(row["component_id"])))
    for component in ordered:
        fold = min(range(folds), key=lambda index: (pair_totals[index], component_totals[index], index))
        component["fold"] = fold
        pair_totals[fold] += int(component["pair_count"])
        component_totals[fold] += 1


def flatten_components(
    source: str, components: Sequence[Mapping[str, Any]], sentence_by_key: Mapping[str, Sentence]
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    pair_rows: list[dict[str, Any]] = []
    example_rows: list[dict[str, Any]] = []
    for component in components:
        for orientation, pairs in (
            ("left_positive", component["left_positive_pairs"]),
            ("right_positive", component["right_positive_pairs"]),
        ):
            for pair in pairs:
                output_pair_id = f"pair:{str(pair['pair_id'])[:24]}"
                indices: dict[str, int] = {}
                for label_name, label in (("edge", 1), ("nonedge", 0)):
                    row = pair[label_name]
                    sentence = sentence_by_key[str(row["sentence_key"])]
                    assert sentence.input_ids is not None
                    example_id = f"example:{stable_hex(NAMESPACE, output_pair_id, label_name)[:24]}"
                    indices[label_name] = len(example_rows)
                    example_rows.append(
                        {
                            "example_index": len(example_rows),
                            "example_id": example_id,
                            "pair_id": output_pair_id,
                            "component_id": component["component_id"],
                            "fold": int(component["fold"]),
                            "source": source,
                            "label": label,
                            "sentence_key": row["sentence_key"],
                            "query_index": int(row["query_index"]),
                            "sequence_length": len(sentence.input_ids),
                            "key_positions": list(map(int, row["key_positions"])),
                            "query_is_head_assigned": bool(pair["edge"]["query_is_head"]),
                            "relation": pair["edge"]["relation"] if label else None,
                        }
                    )
                pair_rows.append(
                    {
                        "pair_id": output_pair_id,
                        "component_id": component["component_id"],
                        "documents": component["documents"],
                        "fold": int(component["fold"]),
                        "source": source,
                        "orientation": orientation,
                        "positive_document": pair["edge"]["document_id"],
                        "negative_document": pair["nonedge"]["document_id"],
                        "edge_index": indices["edge"],
                        "nonedge_index": indices["nonedge"],
                        "query_is_head_assigned": bool(pair["edge"]["query_is_head"]),
                        "matching_stratum": pair["stratum"],
                        "relation": pair["edge"]["relation"],
                    }
                )
    by_sentence: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for example in example_rows:
        by_sentence[str(example["sentence_key"])].append(example)
    units: list[dict[str, Any]] = []
    for sentence_key in sorted(by_sentence, key=lambda value: value.encode("utf-8")):
        sentence = sentence_by_key[sentence_key]
        assert sentence.input_ids is not None
        units.append(
            {
                "unit_id": sentence_key,
                "source": source,
                "document_id": sentence.document_id,
                "sent_id": sentence.sent_id,
                "source_file": sentence.file_name,
                "text_sha256": sentence.sentence_hash,
                "input_ids": sentence.input_ids,
                "attention_mask": [1] * len(sentence.input_ids),
                "examples": [
                    {
                        "example_index": int(row["example_index"]),
                        "query_index": int(row["query_index"]),
                        "key_positions": row["key_positions"],
                    }
                    for row in sorted(by_sentence[sentence_key], key=lambda item: int(item["example_index"]))
                ],
            }
        )
    return pair_rows, example_rows, units


def source_support(
    source: str, components: Sequence[Mapping[str, Any]], pairs: Sequence[Mapping[str, Any]], config: Mapping[str, Any]
) -> dict[str, Any]:
    documents = {doc for component in components for doc in component["documents"]}
    fold_pairs = Counter(int(row["fold"]) for row in pairs)
    fold_components: dict[int, set[str]] = defaultdict(set)
    relation_docs: dict[str, set[str]] = defaultdict(set)
    for row in pairs:
        fold_components[int(row["fold"])].add(str(row["component_id"]))
        relation_docs[str(row["relation"])].add(str(row["positive_document"]))
    retained_relations = sorted(
        relation
        for relation, docs in relation_docs.items()
        if len(docs) >= int(config["matching"]["minimum_relation_class_documents"])
    )
    checks = {
        "documents": len(documents) >= int(config["matching"]["minimum_documents"]),
        "components": len(components) >= int(config["matching"]["minimum_components"]),
        "pairs": len(pairs) >= int(config["matching"]["minimum_pairs"]),
        "fold_pairs": all(fold_pairs[fold] >= int(config["matching"]["minimum_pairs_per_fold"]) for fold in range(5)),
        "fold_components": all(
            len(fold_components[fold]) >= int(config["matching"]["minimum_components_per_fold"]) for fold in range(5)
        ),
        "both_orientations": all(component["left_positive_pairs"] and component["right_positive_pairs"] for component in components),
    }
    return {
        "source": source,
        "documents": len(documents),
        "components": len(components),
        "pairs": len(pairs),
        "examples": len(pairs) * 2,
        "fold_pairs": {str(key): value for key, value in sorted(fold_pairs.items())},
        "fold_components": {str(key): len(value) for key, value in sorted(fold_components.items())},
        "relation_class_documents": {key: len(value) for key, value in sorted(relation_docs.items())},
        "retained_relation_classes": retained_relations,
        "checks": checks,
        "eligible": all(checks.values()),
    }


def validate_unit_lineage(config: Mapping[str, Any], source: str, units: Sequence[Mapping[str, Any]]) -> None:
    """Fail closed if a provenance-only split or rejected source reaches inference."""
    if source not in config["sources"]:
        raise RuntimeError(f"rejected/unconfigured source reached inference units: {source}")
    selected_files = set(config["sources"][source]["analysis_files"])
    for unit in units:
        if unit.get("source") != source or unit.get("source_file") not in selected_files:
            raise RuntimeError(f"provenance-only/rejected split reached inference units: {source}")
        expected = config["sources"][source]["files"][unit["source_file"]]
        if "source_file_sha256" not in unit:
            raise RuntimeError(f"inference-unit source hash missing: {source}")
        observed = unit["source_file_sha256"]
        if observed != expected:
            raise RuntimeError(f"inference-unit source hash drift: {source}")


def _global_prescore_terminal(
    config: Mapping[str, Any], signing_key: Path, *, owner_nonce: str, reason: str, local_terminal: Path | None = None
) -> None:
    owner_records = []
    for field in ("prescore_record", "prescore_rebuild_record"):
        candidate = ROOT / config["paths"][field]
        if candidate.is_file():
            owner_records.append(verify_signed(candidate, config["signer"]["public_key_fingerprint_sha256"]))
    matching_records = [record for record in owner_records if record.get("owner_nonce") == owner_nonce]
    if len(matching_records) != 1:
        raise RuntimeError("refusing terminalization by a non-owner prescore invocation")
    owner_record = matching_records[0]
    payload = {
        "schema_version": "relational_attention_edges_v1_discovery2_global_prescore_terminal_v1",
        "status": "TERMINAL_PRESCORE_INELIGIBLE",
        "study_key": owner_record.get("study_key"),
        "config_sha256": owner_record.get("config_sha256"),
        "reason": reason,
        "owner_nonce": owner_nonce,
        "local_terminal": (
            {"path": local_terminal.relative_to(ROOT).as_posix(), "sha256": sha256_file(local_terminal)}
            if local_terminal is not None and local_terminal.is_file()
            else None
        ),
        "candidate_source_model_forward_run": False,
        "endpoint_scores_computed": False,
        "neural_training_run": False,
        "retry_authorized": False,
    }
    path = ROOT / config["paths"]["prescore_terminal"]
    try:
        exclusive_sign_payload(path, payload, load_signing_key(signing_key, config["signer"]))
    except FileExistsError:
        existing = verify_signed(path, config["signer"]["public_key_fingerprint_sha256"])
        if existing != payload:
            raise RuntimeError("conflicting Discovery-2 global prescore terminal already exists")


def _minimal_prescore_config() -> tuple[dict[str, Any], str, str]:
    """Load only enough immutable identity to consume a prescore claim."""
    config = read_json(CONFIG)
    if config.get("schema_version") != "relational_attention_edges_v1_discovery2_config_v1":
        raise RuntimeError("unexpected relational-link config schema")
    if config.get("namespace") != NAMESPACE or config.get("exploratory") is not True:
        raise RuntimeError("namespace/scope drift")
    assert_permissions(config)
    return config, sha256_file(CONFIG), study_key(config)


def _unvalidated_config_identity() -> tuple[str, str, str]:
    """Return raw bytes identity and a best-effort declared/provisional key.

    This function intentionally performs no protocol validation.  It exists so
    the canonical write-once opening can be consumed before malformed config or
    permission state is revealed.
    """
    raw = CONFIG.read_bytes()
    config_sha = hashlib.sha256(raw).hexdigest()
    key_status = "PROVISIONAL_INVALID_CONFIG"
    try:
        value = json.loads(raw)
        if isinstance(value, Mapping):
            declared_key = study_key(value)
            key_status = "DECLARED_PROTOCOL"
        else:
            raise TypeError("config root is not an object")
    except BaseException:
        declared_key = hashlib.sha256(
            canonical_json_bytes(
                {
                    "namespace": NAMESPACE,
                    "status": "PROVISIONAL_INVALID_CONFIG",
                    "raw_config_sha256": config_sha,
                }
            )
        ).hexdigest()
    return config_sha, declared_key, key_status


def _verify_primary_completion(
    config: Mapping[str, Any], *, expected_config_sha256: str, expected_study_key: str
) -> tuple[dict[str, Any], Path]:
    completion_path = ROOT / config["paths"]["prescore_primary_complete"]
    completion = verify_signed(completion_path, config["signer"]["public_key_fingerprint_sha256"])
    manifest_path = ROOT / config["paths"]["data_root"] / "prepared/manifest.json"
    opening_path = ROOT / config["paths"]["prescore_record"]
    opening = verify_signed(opening_path, config["signer"]["public_key_fingerprint_sha256"])
    if (
        completion.get("schema_version") != "relational_attention_edges_v1_discovery2_primary_complete_v1"
        or completion.get("status") != "PRESCORE_PRIMARY_COMPLETE"
        or completion.get("study_key") != expected_study_key
        or completion.get("config_sha256") != expected_config_sha256
        or completion.get("primary_manifest", {}).get("path") != manifest_path.relative_to(ROOT).as_posix()
        or completion.get("primary_manifest", {}).get("sha256") != sha256_file(manifest_path)
        or completion.get("prescore_opening_sha256") != sha256_file(opening_path)
        or completion.get("owner_nonce") != opening.get("owner_nonce")
        or opening.get("study_key") != expected_study_key
        or opening.get("config_sha256") != expected_config_sha256
        or opening.get("schema_version") != "relational_attention_edges_v1_discovery2_prescore_opening_v1"
        or opening.get("status") != "PRESCORE_OPENING_CONSUMED"
        or opening.get("study_key_status") != "DECLARED_PROTOCOL"
        or opening.get("primary_root") != PRESCORE_LIFECYCLE_PATHS["data_root"]
        or opening.get("rebuild_root") != PRESCORE_LIFECYCLE_PATHS["rebuild_root"]
        or opening.get("candidate_source_model_forward_run") is not False
        or opening.get("retry_authorized") is not False
        or completion.get("exposure_universe_sha256")
        != sha256_file(ROOT / config["exposure"]["universe_path"])
        or completion.get("retry_authorized") is not False
        or completion.get("candidate_source_model_forward_run") is not False
        or completion.get("endpoint_scores_computed") is not False
        or completion.get("neural_training_run") is not False
    ):
        raise RuntimeError("primary completion record drift")
    manifest = read_json(manifest_path)
    if (
        manifest.get("status") != "PRESCORE_COMPLETE"
        or manifest.get("all_primary_sources_eligible") is not True
        or manifest.get("study_key") != expected_study_key
        or completion.get("preservation_entries_sha256") != manifest.get("preservation_entries_sha256")
    ):
        raise RuntimeError("primary completion points to an ineligible manifest")
    return completion, manifest_path


def _build_impl(mode: str = "primary", signing_key: Path | None = None) -> dict[str, Any]:
    global _PRESCORE_OWNER_CONTEXT, _PRESCORE_OWNER_NONCE
    _PRESCORE_OWNER_NONCE = None
    _PRESCORE_OWNER_CONTEXT = None
    if mode not in {"primary", "rebuild"}:
        raise RuntimeError("build mode must be primary or rebuild")
    signing_key = signing_key or Path(
        "/jumbo/lisp/f004ndc/.generated/sessions/unleashed-3/modes/unleashed/.secrets/attempt13_ed25519.pem"
    )
    config_sha, prescore_study_key, key_status = _unvalidated_config_identity()
    bootstrap_config = {
        "paths": dict(PRESCORE_LIFECYCLE_PATHS),
        "signer": dict(EXPECTED_SIGNER),
        "exposure": {"universe_path": EXPOSURE_UNIVERSE_PATH},
    }
    private_key = load_signing_key(signing_key, EXPECTED_SIGNER)
    primary_root = ROOT / PRESCORE_LIFECYCLE_PATHS["data_root"]
    data_root = primary_root if mode == "primary" else ROOT / PRESCORE_LIFECYCLE_PATHS["rebuild_root"]
    prescore_record = ROOT / PRESCORE_LIFECYCLE_PATHS["prescore_record"]
    rebuild_record = ROOT / PRESCORE_LIFECYCLE_PATHS["prescore_rebuild_record"]
    global_terminal = ROOT / PRESCORE_LIFECYCLE_PATHS["prescore_terminal"]
    if global_terminal.exists():
        raise RuntimeError("Discovery-2 global prescore terminal already exists; no retry authorized")
    owner_nonce = secrets.token_hex(16)
    if mode == "primary":
        if prescore_record.exists() or (ROOT / PRESCORE_LIFECYCLE_PATHS["rebuild_root"]).exists():
            raise RuntimeError("Discovery-2 prescore identity was already consumed")
        exclusive_sign_payload(
            prescore_record,
            {
                "schema_version": "relational_attention_edges_v1_discovery2_prescore_opening_v1",
                "status": "PRESCORE_OPENING_CONSUMED",
                "study_key": prescore_study_key,
                "study_key_status": key_status,
                "config_sha256": config_sha,
                "owner_nonce": owner_nonce,
                "primary_root": PRESCORE_LIFECYCLE_PATHS["data_root"],
                "rebuild_root": PRESCORE_LIFECYCLE_PATHS["rebuild_root"],
                "candidate_source_model_forward_run": False,
                "retry_authorized": False,
            },
            private_key,
        )
        _PRESCORE_OWNER_NONCE = owner_nonce
        _PRESCORE_OWNER_CONTEXT = bootstrap_config
        raw_config, validated_config_sha, validated_study_key = _minimal_prescore_config()
        if (
            validated_config_sha != config_sha
            or validated_study_key != prescore_study_key
            or key_status != "DECLARED_PROTOCOL"
        ):
            raise RuntimeError("declared config/study identity is invalid or changed after primary claim")
    else:
        raw_config, validated_config_sha, validated_study_key = _minimal_prescore_config()
        if validated_config_sha != config_sha or validated_study_key != prescore_study_key:
            raise RuntimeError("config/study identity changed before rebuild claim")
        opening = verify_signed(prescore_record, EXPECTED_SIGNER["public_key_fingerprint_sha256"])
        if (
            opening.get("status") != "PRESCORE_OPENING_CONSUMED"
            or opening.get("study_key") != prescore_study_key
            or opening.get("config_sha256") != config_sha
        ):
            raise RuntimeError("rebuild lacks exact eligible primary prescore lineage")
        _, primary_manifest = _verify_primary_completion(
            bootstrap_config, expected_config_sha256=config_sha, expected_study_key=prescore_study_key
        )
        exclusive_sign_payload(
            rebuild_record,
            {
                "schema_version": "relational_attention_edges_v1_discovery2_rebuild_claim_v1",
                "status": "REBUILD_CLAIM_CONSUMED",
                "study_key": prescore_study_key,
                "config_sha256": config_sha,
                "owner_nonce": owner_nonce,
                "primary_manifest_sha256": sha256_file(primary_manifest),
                "retry_authorized": False,
            },
            private_key,
        )
        _PRESCORE_OWNER_NONCE = owner_nonce
        _PRESCORE_OWNER_CONTEXT = bootstrap_config
    # The one-shot identity is consumed before any validation that could reveal
    # candidate-source eligibility.  Full validation now runs under ownership.
    config = load_config()
    if sha256_file(CONFIG) != config_sha or study_key(config) != prescore_study_key:
        raise RuntimeError("config/study identity changed after prescore claim")
    if mode == "rebuild":
        _verify_primary_completion(
            config, expected_config_sha256=config_sha, expected_study_key=prescore_study_key
        )
    prepared_root = data_root / "prepared"
    verify_exposure_universe(config)
    preservation_sha = verify_preservation(config)
    assert_new_destination(config, data_root)
    if data_root.exists():
        raise RuntimeError(f"label-only output namespace already exists: {data_root}")
    data_root.mkdir(parents=True, exist_ok=False)
    tokenizer = AutoTokenizer.from_pretrained(
        config["model"]["name"],
        revision=config["model"]["revision"],
        local_files_only=True,
        use_fast=True,
    )
    if not tokenizer.is_fast:
        raise RuntimeError("exact offset alignment requires a fast tokenizer")
    raw_sentences: dict[str, list[Sentence]] = {}
    for source, spec in config["sources"].items():
        paths = [ROOT / spec["root"] / name for name in spec["analysis_files"]]
        if any(not path.is_file() for path in paths):
            raise RuntimeError(f"selected analysis file missing: {source}")
        raw_sentences[source] = parse_conllu(source, paths)
    audit = exposure_audit(config, raw_sentences)
    if audit["status"] != "PASS_PROJECT_OUTCOME_UNSEEN_WITH_LABEL_ONLY_SCOUTING":
        atomic_json(data_root / "exposure_audit.json", audit)
        terminal = {
            "schema_version": "relational_attention_edges_v1_prescore_terminal_v1",
            "status": "TERMINAL_PRESCORE_INELIGIBLE",
            "reason": "exposure_audit_failed",
            "config_sha256": sha256_file(CONFIG),
            "exposure_audit_sha256": sha256_file(data_root / "exposure_audit.json"),
            "model_forward_run": False,
            "neural_training_run": False,
            "retry_authorized": False,
        }
        local_terminal = data_root / "TERMINAL_PRESCORE_INELIGIBLE.json"
        sign_payload(
            local_terminal,
            terminal,
            load_signing_key(signing_key, config["signer"]),
        )
        _global_prescore_terminal(
            config, signing_key, owner_nonce=owner_nonce,
            reason="exposure_audit_failed", local_terminal=local_terminal,
        )
        return terminal

    aligned_by_source: dict[str, list[Sentence]] = {}
    alignment_reports: dict[str, dict[str, int]] = {}
    for source, raw in raw_sentences.items():
        aligned_by_source[source], alignment_reports[source] = align_sentences(raw, tokenizer, config, audit)
    input_id_audit = input_id_exposure_audit(config, aligned_by_source)
    audit["input_id_sequence_audit"] = input_id_audit
    if not input_id_audit["eligible"]:
        audit["status"] = "INELIGIBLE"
        audit["model_forward_on_candidate_source_found"] = bool(
            audit["model_forward_on_candidate_source_found"]
            or input_id_audit["model_forward_exposure_found"]
        )
        audit["endpoint_score_on_candidate_source_found"] = bool(
            audit["endpoint_score_on_candidate_source_found"]
            or input_id_audit["endpoint_score_exposure_found"]
        )
    atomic_json(data_root / "exposure_audit.json", audit)
    if audit["status"] != "PASS_PROJECT_OUTCOME_UNSEEN_WITH_LABEL_ONLY_SCOUTING":
        terminal = {
            "schema_version": "relational_attention_edges_v1_prescore_terminal_v1",
            "status": "TERMINAL_PRESCORE_INELIGIBLE",
            "reason": "input_id_sequence_exposure_audit_failed",
            "config_sha256": sha256_file(CONFIG),
            "exposure_audit_sha256": sha256_file(data_root / "exposure_audit.json"),
            "model_forward_run": False,
            "neural_training_run": False,
            "retry_authorized": False,
        }
        local_terminal = data_root / "TERMINAL_PRESCORE_INELIGIBLE.json"
        sign_payload(
            local_terminal,
            terminal,
            load_signing_key(signing_key, config["signer"]),
        )
        _global_prescore_terminal(
            config, signing_key, owner_nonce=owner_nonce,
            reason="input_id_sequence_exposure_audit_failed", local_terminal=local_terminal
        )
        return terminal

    source_outputs: dict[str, Any] = {}
    all_eligible = True
    for source, raw in raw_sentences.items():
        aligned, alignment_report = aligned_by_source[source], alignment_reports[source]
        sentence_by_key = {sentence.key: sentence for sentence in aligned}
        candidates = enumerate_candidates(aligned)
        components = match_documents(source, candidates, config)
        assign_folds(components, int(config["matching"]["folds"]))
        pairs, examples, units = flatten_components(source, components, sentence_by_key)
        for unit in units:
            unit["source_file_sha256"] = config["sources"][source]["files"][unit["source_file"]]
        validate_unit_lineage(config, source, units)
        support = source_support(source, components, pairs, config)
        all_eligible = all_eligible and bool(support["eligible"])
        source_root = prepared_root / source
        source_root.mkdir(parents=True, exist_ok=False)
        pair_sha, pair_n = atomic_jsonl(source_root / "pairs.jsonl", pairs)
        example_sha, example_n = atomic_jsonl(source_root / "examples.jsonl", examples)
        unit_sha, unit_n = atomic_jsonl(source_root / "inference_units.jsonl", units)
        component_ids = sorted((str(row["component_id"]) for row in components), key=lambda value: value.encode("utf-8"))
        atomic_json(source_root / "components.json", component_ids)
        maps = bootstrap_indices(
            component_ids,
            direction=f"test-source:{source}",
            seed=int(config["seed"]),
            draws=int(config["analysis"]["bootstrap_draws"]),
        )
        np.save(source_root / "bootstrap_indices.uint32.npy", maps, allow_pickle=False)
        swap = np.empty((int(config["analysis"]["bootstrap_draws"]), len(pairs)), dtype=np.uint8)
        for draw in range(swap.shape[0]):
            seed = int.from_bytes(stable_digest(NAMESPACE, "swap-null", source, config["seed"], draw)[:8], "big")
            swap[draw] = np.random.default_rng(seed).integers(0, 2, len(pairs), dtype=np.uint8)
        np.save(source_root / "paired_swap.uint8.npy", swap, allow_pickle=False)
        atomic_json(source_root / "support.json", {"alignment": alignment_report, **support})
        source_outputs[source] = {
            "raw_sentences": len(raw),
            "aligned_sentences": len(aligned),
            "aligned_documents": len({sentence.document_id for sentence in aligned}),
            "alignment": alignment_report,
            "support": support,
            "pairs": pair_n,
            "examples": example_n,
            "units": unit_n,
            "pairs_sha256": pair_sha,
            "examples_sha256": example_sha,
            "units_sha256": unit_sha,
            "bootstrap_sha256": sha256_file(source_root / "bootstrap_indices.uint32.npy"),
            "swap_sha256": sha256_file(source_root / "paired_swap.uint8.npy"),
        }
    manifest = {
        "schema_version": "relational_attention_edges_v1_prepared_manifest_v1",
        "status": "PRESCORE_COMPLETE" if all_eligible else "TERMINAL_PRESCORE_INELIGIBLE",
        "namespace": NAMESPACE,
        "study_key": prescore_study_key,
        "config_sha256": sha256_file(CONFIG),
        "preservation_entries_sha256": preservation_sha,
        "exposure_audit_sha256": sha256_file(data_root / "exposure_audit.json"),
        "sources": source_outputs,
        "all_primary_sources_eligible": all_eligible,
        "model_forward_run": False,
        "model_weights_loaded": False,
        "endpoint_scores_computed": False,
        "neural_training_run": False,
        "prepared_inventory": recursive_inventory(prepared_root),
    }
    manifest["prepared_inventory_sha256"] = inventory_digest(manifest["prepared_inventory"])
    manifest_path = prepared_root / "manifest.json"
    atomic_json(manifest_path, manifest)
    if not all_eligible:
        local_terminal = data_root / "TERMINAL_PRESCORE_INELIGIBLE.json"
        sign_payload(
            local_terminal,
            {
                "schema_version": "relational_attention_edges_v1_prescore_terminal_v1",
                "status": "TERMINAL_PRESCORE_INELIGIBLE",
                "reason": "support_or_alignment_floor_failed",
                "manifest_sha256": sha256_file(prepared_root / "manifest.json"),
                "model_forward_run": False,
                "neural_training_run": False,
                "retry_authorized": False,
            },
            load_signing_key(signing_key, config["signer"]),
        )
        _global_prescore_terminal(
            config, signing_key, owner_nonce=owner_nonce,
            reason="support_or_alignment_floor_failed", local_terminal=local_terminal
        )
    verify_preservation(config)
    verify_exposure_universe(config)
    if all_eligible and mode == "primary":
        opening = verify_signed(prescore_record, config["signer"]["public_key_fingerprint_sha256"])
        if opening.get("owner_nonce") != owner_nonce:
            raise RuntimeError("primary completion owner does not match prescore opening")
        exclusive_sign_payload(
            ROOT / config["paths"]["prescore_primary_complete"],
            {
                "schema_version": "relational_attention_edges_v1_discovery2_primary_complete_v1",
                "status": "PRESCORE_PRIMARY_COMPLETE",
                "study_key": prescore_study_key,
                "config_sha256": config_sha,
                "owner_nonce": owner_nonce,
                "prescore_opening_sha256": sha256_file(prescore_record),
                "primary_manifest": {
                    "path": manifest_path.relative_to(ROOT).as_posix(),
                    "sha256": sha256_file(manifest_path),
                },
                "preservation_entries_sha256": preservation_sha,
                "exposure_universe_sha256": sha256_file(ROOT / config["exposure"]["universe_path"]),
                "candidate_source_model_forward_run": False,
                "endpoint_scores_computed": False,
                "neural_training_run": False,
                "retry_authorized": False,
            },
            private_key,
        )
    return manifest


def build(mode: str = "primary", signing_key: Path | None = None) -> dict[str, Any]:
    """Run one owned prescore attempt and terminalize every post-claim failure."""
    try:
        return _build_impl(mode, signing_key)
    except BaseException as exc:
        if _PRESCORE_OWNER_NONCE is not None and _PRESCORE_OWNER_CONTEXT is not None:
            key_path = signing_key or Path(
                "/jumbo/lisp/f004ndc/.generated/sessions/unleashed-3/modes/unleashed/.secrets/attempt13_ed25519.pem"
            )
            try:
                _global_prescore_terminal(
                    _PRESCORE_OWNER_CONTEXT,
                    key_path,
                    owner_nonce=_PRESCORE_OWNER_NONCE,
                    reason=f"{type(exc).__name__}:{exc}",
                )
            except BaseException as terminal_exc:
                raise RuntimeError(
                    f"owned prescore failed and canonical terminalization also failed: {terminal_exc}"
                ) from exc
        raise


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--signing-key", type=Path)
    parser.add_argument("--create-opaque-sidecar", action="store_true")
    parser.add_argument("--create-role-sidecar", action="store_true")
    parser.add_argument("--create-exposure-universe", action="store_true")
    parser.add_argument("--rebuild", action="store_true")
    args = parser.parse_args()
    if args.create_opaque_sidecar:
        if args.signing_key is None or args.create_exposure_universe or args.create_role_sidecar or args.rebuild:
            raise RuntimeError("opaque-sidecar creation requires --signing-key and forbids other actions")
        config = read_json(CONFIG)
        assert config.get("namespace") == NAMESPACE
        print(json.dumps(create_opaque_sidecar(config, args.signing_key), sort_keys=True, indent=2))
        return
    if args.create_role_sidecar:
        if args.signing_key is None or args.create_exposure_universe or args.rebuild:
            raise RuntimeError("role-sidecar creation requires --signing-key and forbids other actions")
        config = read_json(CONFIG)
        assert config.get("namespace") == NAMESPACE
        print(json.dumps(create_role_sidecar(config, args.signing_key), sort_keys=True, indent=2))
        return
    if args.create_exposure_universe:
        if args.signing_key is None or args.rebuild:
            raise RuntimeError("exposure-universe creation requires --signing-key and forbids other actions")
        print(json.dumps(create_exposure_universe(load_config(), args.signing_key), sort_keys=True, indent=2))
        return
    if args.signing_key is None:
        raise RuntimeError("primary/rebuild prescore requires --signing-key")
    result = build("rebuild" if args.rebuild else "primary", args.signing_key)
    print(json.dumps(result, sort_keys=True, indent=2))


if __name__ == "__main__":
    main()
