#!/usr/bin/env python3
"""Label-only builder for the relational attention-link discovery study."""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

import numpy as np
from scipy.optimize import linear_sum_assignment
from transformers import AutoTokenizer

sys.path.insert(0, str(Path(__file__).resolve().parent))

from relational_attention_edges_v1 import (
    CONFIG,
    NAMESPACE,
    ROOT,
    assert_new_destination,
    atomic_json,
    atomic_jsonl,
    bootstrap_indices,
    canonical_json_bytes,
    coarse_relation,
    inventory_digest,
    load_config,
    load_signing_key,
    recursive_inventory,
    sha256_file,
    sign_payload,
    stable_digest,
    stable_hex,
    verify_preservation,
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


def _split_name(path: Path) -> str:
    match = re.search(r"-(train|dev|test)(?:-[^.]+)?\.conllu$", path.name)
    return match.group(1) if match else path.stem


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
    canonical_tokens = [token.form.casefold() for token in tokens]
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


def _prior_conllu_paths() -> list[Path]:
    new_raw = (ROOT / "data/relational_attention_edges_v1_raw").resolve()
    paths: list[Path] = []
    for path in (ROOT / "data").rglob("*.conllu"):
        resolved = path.resolve()
        if new_raw in resolved.parents or any(
            part.startswith("relational_attention_edges_v1_discovery1") for part in resolved.parts
        ):
            continue
        paths.append(path)
    return sorted(paths, key=lambda p: p.as_posix().encode("utf-8"))


def _prior_sentence_hashes(paths: Sequence[Path]) -> dict[str, dict[str, Any]]:
    hashes: dict[str, dict[str, Any]] = {}
    for path in paths:
        forms: list[str] = []
        for line in path.read_text(encoding="utf-8", errors="replace").splitlines() + [""]:
            if not line:
                if forms:
                    digest = hashlib.sha256(canonical_json_bytes(forms)).hexdigest()
                    hashes.setdefault(digest, {"words": len(forms), "example_path": path.relative_to(ROOT).as_posix()})
                    forms = []
            elif not line.startswith("#"):
                parts = line.split("\t")
                if len(parts) == 10 and parts[0].isdigit():
                    forms.append(parts[1].casefold())
    return hashes


def _document_hashes(sentences: Sequence[Sentence]) -> dict[str, str]:
    grouped: dict[str, list[str]] = defaultdict(list)
    for sentence in sentences:
        grouped[sentence.document_id].append(sentence.token_hash)
    return {document: hashlib.sha256(canonical_json_bytes(values)).hexdigest() for document, values in grouped.items()}


def _prior_document_hashes(paths: Sequence[Path]) -> dict[str, dict[str, Any]]:
    output: dict[str, dict[str, Any]] = {}
    for path in paths:
        current_document: str | None = None
        sentence_forms: list[str] = []
        documents: dict[str, list[str]] = defaultdict(list)
        for line in path.read_text(encoding="utf-8", errors="replace").splitlines() + [""]:
            if line.startswith("# newdoc id = "):
                current_document = line.split("=", 1)[1].strip()
            elif not line:
                if sentence_forms and current_document is not None:
                    documents[current_document].append(hashlib.sha256(canonical_json_bytes(sentence_forms)).hexdigest())
                sentence_forms = []
            elif not line.startswith("#"):
                parts = line.split("\t")
                if len(parts) == 10 and parts[0].isdigit():
                    sentence_forms.append(parts[1].casefold())
        for document, sentence_hashes in documents.items():
            digest = hashlib.sha256(canonical_json_bytes(sentence_hashes)).hexdigest()
            output.setdefault(digest, {"path": path.relative_to(ROOT).as_posix(), "document": document})
    return output


def _prior_artifact_paths() -> list[Path]:
    roots = ("data", "pilot_runs", "results", "reports", "configs", "prereg", "docs", "analysis", "experiments")
    explicit = list(ROOT.glob("PLAN*.md")) + [ROOT / "ANALYSIS.md", ROOT / "RESULTS.md"]
    output: set[Path] = set()
    for name in roots:
        root = ROOT / name
        if root.exists():
            output.update(path for path in root.rglob("*") if path.is_file() and not path.is_symlink())
    output.update(path for path in explicit if path.is_file() and not path.is_symlink())
    excluded_exact = {
        (ROOT / "PLAN_RELATIONAL_EDGE_V1.md").resolve(),
        (ROOT / "reports/provenance/relational_attention_edges_v1_source_amendment.json").resolve(),
        (ROOT / "reports/architecture_program_closure_v1.json").resolve(),
        (ROOT / "docs/encoding_separability_paper_draft.md").resolve(),
    }
    filtered = []
    for path in output:
        resolved = path.resolve()
        if resolved in excluded_exact:
            continue
        if (ROOT / "data/relational_attention_edges_v1_raw").resolve() in resolved.parents:
            continue
        if any(part.startswith("relational_attention_edges_v1_discovery1") for part in resolved.parts):
            continue
        if (ROOT / "configs/relational_attention_edges_v1").resolve() in resolved.parents:
            continue
        if path.name.startswith("relational_attention_edges_v1_"):
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
    binary_suffixes = {".npy", ".npz", ".pt", ".pth", ".bin", ".safetensors", ".pkl", ".parquet", ".arrow"}
    if path.suffix.casefold() in binary_suffixes or path.stat().st_size > 64 * 1024 * 1024:
        digest = sha256_file(path)
        if digest in digests:
            digest_hits.add(digest)
        return alias_hits, digest_hits
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


def _walk_input_ids(value: Any) -> Iterable[list[int]]:
    if isinstance(value, Mapping):
        candidate = value.get("input_ids")
        if isinstance(candidate, list) and candidate and all(isinstance(item, int) and not isinstance(item, bool) for item in candidate):
            yield candidate
        for nested in value.values():
            yield from _walk_input_ids(nested)
    elif isinstance(value, list):
        for nested in value:
            yield from _walk_input_ids(nested)


def input_id_exposure_audit(aligned: Mapping[str, Sequence[Sentence]]) -> dict[str, Any]:
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
    for path in _prior_artifact_paths():
        if path.suffix.casefold() not in {".json", ".jsonl"} or path.stat().st_size > 64 * 1024 * 1024:
            continue
        scanned_files += 1
        try:
            if path.suffix.casefold() == ".jsonl":
                values = (json.loads(line) for line in path.read_text(encoding="utf-8", errors="strict").splitlines() if line)
            else:
                values = (json.loads(path.read_text(encoding="utf-8", errors="strict")),)
            for value in values:
                for ids in _walk_input_ids(value):
                    parsed_sequences += 1
                    digest = hashlib.sha256(canonical_json_bytes(ids)).hexdigest()
                    if digest in candidate_digests:
                        hits.append({"path": path.relative_to(ROOT).as_posix(), "input_ids_sha256": digest, "candidate_rows": candidate[digest][:20]})
        except (UnicodeDecodeError, json.JSONDecodeError, OSError):
            continue
    return {"scanned_json_files": scanned_files, "parsed_prior_input_id_sequences": parsed_sequences, "hits": hits, "eligible": not hits}


def exposure_audit(config: Mapping[str, Any], sentences: Mapping[str, Sequence[Sentence]]) -> dict[str, Any]:
    prior_paths = _prior_conllu_paths()
    prior_hashes = _prior_sentence_hashes(prior_paths)
    prior_document_hashes = _prior_document_hashes(prior_paths)
    new_raw_hashes = {digest for spec in config["sources"].values() for digest in spec["files"].values()}
    prior_file_hash_hits = []
    for path in prior_paths:
        digest = sha256_file(path)
        if digest in new_raw_hashes:
            prior_file_hash_hits.append({"path": path.relative_to(ROOT).as_posix(), "sha256": digest})

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
    for values in sentences.values():
        candidate_digests.update(row.sentence_hash for row in values)
        candidate_digests.update(row.token_hash for row in values)
    for values in candidate_document_digests.values():
        candidate_digests.update(values.values())
    artifact_hits: list[dict[str, Any]] = []
    for path in _prior_artifact_paths():
        found_aliases, found_digests = _scan_artifact(path, [value.encode("utf-8") for value in aliases], candidate_digests)
        if found_aliases or found_digests:
            rel = path.relative_to(ROOT).as_posix()
            artifact_hits.append({"path": rel, "aliases": sorted(found_aliases), "candidate_digests": sorted(found_digests)})
    # Any unexplained pre-existing alias or exact candidate digest outside raw linguistic data is blocking.
    blocking_artifact_hits = artifact_hits
    if blocking_artifact_hits:
        ineligible = True
    model_forward_hits = [row for row in artifact_hits if row["path"].startswith(("pilot_runs/", "results/")) or "cache" in row["path"].casefold() or "activation" in row["path"].casefold()]
    endpoint_score_hits = [row for row in artifact_hits if row["path"].startswith(("results/", "reports/", "pilot_runs/"))]
    return {
        "schema_version": "relational_attention_edges_v1_exposure_audit_v1",
        "status": "INELIGIBLE" if ineligible else "PASS_PROJECT_OUTCOME_UNSEEN_WITH_LABEL_ONLY_SCOUTING",
        "prior_conllu_files": len(prior_paths),
        "prior_sentence_hashes": len(prior_hashes),
        "exact_prior_raw_file_hits": prior_file_hash_hits,
        "historical_artifact_hits": artifact_hits,
        "blocking_artifact_hits": blocking_artifact_hits,
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


def build(output_root: Path | None = None, signing_key: Path | None = None) -> dict[str, Any]:
    config = load_config()
    preservation_sha = verify_preservation(config)
    data_root = output_root or (ROOT / config["paths"]["data_root"])
    prepared_root = data_root / "prepared"
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
        sign_payload(
            data_root / "TERMINAL_PRESCORE_INELIGIBLE.json",
            terminal,
            load_signing_key(signing_key or Path("/jumbo/lisp/f004ndc/.generated/sessions/unleashed-3/modes/unleashed/.secrets/attempt13_ed25519.pem"), config["signer"]),
        )
        return terminal

    aligned_by_source: dict[str, list[Sentence]] = {}
    alignment_reports: dict[str, dict[str, int]] = {}
    for source, raw in raw_sentences.items():
        aligned_by_source[source], alignment_reports[source] = align_sentences(raw, tokenizer, config, audit)
    input_id_audit = input_id_exposure_audit(aligned_by_source)
    audit["input_id_sequence_audit"] = input_id_audit
    if not input_id_audit["eligible"]:
        audit["status"] = "INELIGIBLE"
        audit["model_forward_on_candidate_source_found"] = True
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
        sign_payload(
            data_root / "TERMINAL_PRESCORE_INELIGIBLE.json",
            terminal,
            load_signing_key(signing_key or Path("/jumbo/lisp/f004ndc/.generated/sessions/unleashed-3/modes/unleashed/.secrets/attempt13_ed25519.pem"), config["signer"]),
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
    atomic_json(prepared_root / "manifest.json", manifest)
    if not all_eligible:
        sign_payload(
            data_root / "TERMINAL_PRESCORE_INELIGIBLE.json",
            {
                "schema_version": "relational_attention_edges_v1_prescore_terminal_v1",
                "status": "TERMINAL_PRESCORE_INELIGIBLE",
                "reason": "support_or_alignment_floor_failed",
                "manifest_sha256": sha256_file(prepared_root / "manifest.json"),
                "model_forward_run": False,
                "neural_training_run": False,
                "retry_authorized": False,
            },
            load_signing_key(signing_key or Path("/jumbo/lisp/f004ndc/.generated/sessions/unleashed-3/modes/unleashed/.secrets/attempt13_ed25519.pem"), config["signer"]),
        )
    verify_preservation(config)
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-root", type=Path)
    parser.add_argument("--signing-key", type=Path)
    args = parser.parse_args()
    output = args.output_root.resolve() if args.output_root else None
    result = build(output, args.signing_key)
    print(json.dumps(result, sort_keys=True, indent=2))


if __name__ == "__main__":
    main()
