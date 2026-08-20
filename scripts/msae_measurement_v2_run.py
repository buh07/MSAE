#!/usr/bin/env python3
"""Config-bound execution utilities for the Atlas/MSAE measurement-v2 run.

This module is additive.  It never reads an Atlas private/final path and never
modifies the completion-v1 bundle.
"""

from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass
import base64
import hashlib
import json
import math
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
from typing import Any, Iterable, Mapping, Sequence
import urllib.request

import numpy as np

from msae_measurement_v2 import (
    SupportThresholds,
    audit_task_support,
    cap_rows_by_group,
    canonical_json_bytes,
    sha256_file,
)


ROOT = Path(__file__).resolve().parents[1]
SCHEMA = "atlas_measurement_v2_run_v1"
DROP = "__DROP__"
ROLES = ("discovery", "calibration", "C1", "C2")
PRIMARY_TASKS = ("relative_quartile", "head_signed_distance", "token_identity_v2")
DIAGNOSTIC_TASKS = ("deprel_coarse", "dependency_depth")
ALL_TASKS = PRIMARY_TASKS + DIAGNOSTIC_TASKS
FAMILY_TASKS = {
    "broad_structural_context_position": ("relative_quartile", "head_signed_distance"),
    "lexical_content": ("token_identity_v2",),
}
ESL_SENT_ID = re.compile(r"^(file[0-9]+\.txt)_([0-9]+)$")
GUM_SENT_ID = re.compile(r"^(.+)-([0-9]+)$")

UPOS_MAP = {
    **{x: "NOMINAL" for x in ("NOUN", "PROPN", "PRON")},
    **{x: "VERBAL" for x in ("VERB", "AUX")},
    **{x: "MODIFIER" for x in ("ADJ", "ADV")},
    **{x: "FUNCTION" for x in ("ADP", "CCONJ", "SCONJ", "DET", "PART")},
    "NUM": "QUANTITY", "PUNCT": "PUNCT", "INTJ": "OTHER", "SYM": "OTHER", "X": "OTHER",
}
DEPREL_MAP = {
    **{x: "CORE" for x in ("nsubj", "csubj", "obj", "iobj")},
    **{x: "CLAUSAL_COMPLEMENT" for x in ("ccomp", "xcomp")},
    **{x: "OBLIQUE" for x in ("obl", "vocative", "expl", "dislocated")},
    **{x: "NOMINAL" for x in ("nmod", "appos", "nummod", "acl", "amod", "det", "clf", "case")},
    **{x: "ADVERBIAL" for x in ("advcl", "advmod", "discourse")},
    **{x: "COORD" for x in ("conj", "cc")},
    **{x: "FUNCTION" for x in ("aux", "cop", "mark")},
    **{x: "MWE" for x in ("fixed", "flat", "compound", "list")},
    **{x: "REPAIR_OTHER" for x in ("parataxis", "orphan", "goeswith", "reparandum", "dep")},
    "root": "root", "punct": "punct",
}
CAP_MAP = {"lower": "lower", "title": "title", "upper": "other", "mixed": "other", "nonalpha": "nonalpha"}


def digest_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def stable_key(namespace: str, value: str) -> tuple[bytes, bytes]:
    return hashlib.sha256(f"atlas-measurement-v2|{namespace}|{value}".encode()).digest(), value.encode()


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]


def atomic_write_json(path: Path, value: Any) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n"
    fd, name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(name, path)
    finally:
        if os.path.exists(name):
            os.unlink(name)
    return hashlib.sha256(payload.encode()).hexdigest()


def atomic_create_json(path: Path, value: Any) -> str:
    """Publish canonical JSON exactly once without a check/replace race."""
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n"
    fd, name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(payload); handle.flush(); os.fsync(handle.fileno())
        try: os.link(name, path)
        except FileExistsError as exc: raise RuntimeError(f"create-once path exists: {path}") from exc
        directory_fd = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY)
        try: os.fsync(directory_fd)
        finally: os.close(directory_fd)
    finally:
        if os.path.exists(name): os.unlink(name)
    return hashlib.sha256(payload.encode()).hexdigest()


def atomic_write_jsonl(path: Path, rows: Iterable[Mapping[str, Any]]) -> tuple[str, int]:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    digest = hashlib.sha256()
    count = 0
    try:
        with os.fdopen(fd, "wb") as handle:
            for row in rows:
                payload = canonical_json_bytes(row)
                handle.write(payload)
                digest.update(payload)
                count += 1
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(name, path)
    finally:
        if os.path.exists(name):
            os.unlink(name)
    return digest.hexdigest(), count


def require_relative_path(raw: str) -> Path:
    path = Path(raw)
    if path.is_absolute() or not path.parts or any(x in {"", ".", ".."} for x in path.parts):
        raise ValueError(f"non-normalized repository path: {raw}")
    if any(x.lower() in {"private", "final", "blind", "unlock"} for x in path.parts):
        raise ValueError(f"forbidden path: {raw}")
    return path


def root_path(raw: str) -> Path:
    path = require_relative_path(raw)
    result = (ROOT / path).resolve(strict=False)
    result.relative_to(ROOT.resolve())
    return result


def verify_file(path: Path, expected: str) -> None:
    if not path.is_file() or path.is_symlink():
        raise RuntimeError(f"required regular file absent: {path}")
    observed = sha256_file(path)
    if observed != expected:
        raise RuntimeError(f"digest mismatch {path}: {observed} != {expected}")


def load_config(path: Path) -> dict[str, Any]:
    path = path.resolve(strict=True)
    if path != (ROOT / "configs/atlas_measurement_v2/run.json").resolve(strict=True):
        raise ValueError("only the reviewed Atlas measurement-v2 config is accepted")
    cfg = read_json(path)
    if cfg.get("schema_version") != SCHEMA:
        raise ValueError("wrong v2 run schema")
    if int(cfg["seed"]) != 20260802 or int(cfg["bootstrap"]["draws"]) != 500:
        raise ValueError("seed/draw contract drift")
    if cfg["claim_scope"] != "broad_structural_context_position_vs_lexical_content":
        raise ValueError("claim scope drift")
    if cfg["absolute_position"]["status"] != "ineligible" or cfg["absolute_position"]["reason"] != "model_architecture_symmetry":
        raise ValueError("absolute-position disposition drift")
    if tuple(cfg["roles"]) != ROLES:
        raise ValueError("role drift")
    if tuple(cfg["tasks"]["primary"]) != PRIMARY_TASKS or tuple(cfg["tasks"]["diagnostic"]) != DIAGNOSTIC_TASKS:
        raise ValueError("task drift")
    if cfg["reviewer_trust"]["sha256_fingerprint"] != "668e132b5263caa9082f23c25d599250cb88adaa95d662c7498ecc1245c64dac":
        raise ValueError("reviewer trust-key drift")
    public = base64.b64decode(cfg["reviewer_trust"]["raw_public_key_base64"], validate=True)
    if len(public) != 32 or hashlib.sha256(public).hexdigest() != cfg["reviewer_trust"]["sha256_fingerprint"]:
        raise ValueError("reviewer public-key fingerprint mismatch")
    implementation = cfg.get("implementation_inventory")
    if not isinstance(implementation, dict) or not implementation:
        raise ValueError("implementation inventory absent")
    for relative, expected in implementation.items():
        verify_file(root_path(str(relative)), str(expected))
    return cfg


def config_sha(path: Path) -> str:
    return sha256_file(path.resolve(strict=True))


def download_verified(url: str, output: Path, expected: str) -> Path:
    output.parent.mkdir(parents=True, exist_ok=True)
    if output.exists():
        verify_file(output, expected)
        return output
    fd, name = tempfile.mkstemp(prefix=f".{output.name}.", suffix=".download", dir=output.parent)
    os.close(fd)
    try:
        with urllib.request.urlopen(url, timeout=120) as response, open(name, "wb") as handle:
            shutil.copyfileobj(response, handle)
        if sha256_file(Path(name)) != expected:
            raise RuntimeError(f"download digest mismatch: {url}")
        os.replace(name, output)
    finally:
        if os.path.exists(name):
            os.unlink(name)
    return output


def surface_labels(words: list[str]) -> tuple[list[str], list[str], list[str]]:
    caps: list[str] = []
    lengths: list[str] = []
    boundaries: list[str] = []
    for i, word in enumerate(words):
        letters = "".join(c for c in word if c.isalpha())
        if not letters:
            caps.append("nonalpha")
        elif letters.islower():
            caps.append("lower")
        elif letters.isupper():
            caps.append("upper")
        elif letters.istitle():
            caps.append("title")
        else:
            caps.append("mixed")
        n = len(word)
        lengths.append("1" if n == 1 else "2" if n == 2 else "3_4" if n <= 4 else "5_7" if n <= 7 else "8p")
        boundaries.append("single" if len(words) == 1 else "initial" if i == 0 else "final" if i == len(words)-1 else "interior")
    return caps, lengths, boundaries


def bucket_signed_distance(pos: int, head_pos: int | None) -> str:
    if head_pos is None:
        return "ROOT"
    delta = head_pos - pos
    side = "L" if delta < 0 else "R"
    mag = abs(delta)
    return side + ("1" if mag == 1 else "2" if mag == 2 else "3_4" if mag <= 4 else "5p")


def depth_for(pos: int, heads: list[int], id_to_pos: dict[int, int]) -> str:
    depth, current, seen = 0, pos, set()
    while True:
        if current in seen or depth > len(heads):
            return DROP
        seen.add(current)
        head = heads[current]
        if head == 0:
            return str(depth)
        if head not in id_to_pos:
            return DROP
        current = id_to_pos[head]
        depth += 1
        if depth >= 4:
            return "4p"


def parse_esl_files(paths: Sequence[Path], source: str, revision: str) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    seen_sent: set[str] = set()
    for path in paths:
        comments: dict[str, str] = {}
        rows: list[list[str]] = []

        def flush() -> None:
            nonlocal comments, rows
            if not rows:
                comments = {}
                return
            sent_id = comments.get("sent_id", "")
            match = ESL_SENT_ID.fullmatch(sent_id)
            if match is None or sent_id in seen_sent:
                raise RuntimeError(f"malformed/duplicate ESLSpok sent_id: {sent_id!r}")
            seen_sent.add(sent_id)
            ids = [int(row[0]) for row in rows]
            words = [row[1] for row in rows]
            upos = [row[3] for row in rows]
            heads = [int(row[6]) if row[6].isdigit() else 0 for row in rows]
            deprel = [row[7].split(":", 1)[0] for row in rows]
            id_to_pos = {token_id: i for i, token_id in enumerate(ids)}
            caps, lengths, boundaries = surface_labels(words)
            content_hash = digest_text(" ".join(" ".join(words).lower().split()))
            group = f"{source}:{match.group(1)}"
            labels = {
                "lemma": [word.lower() for word in words],
                "relative_quartile": [str(min(3, (4*i)//max(1, len(words)))) for i in range(len(words))],
                "head_signed_distance": [bucket_signed_distance(i, id_to_pos.get(h) if h else None) for i, h in enumerate(heads)],
                "dependency_depth": [depth_for(i, heads, id_to_pos) for i in range(len(words))],
                "boundary_state": boundaries,
                "upos": upos,
                "deprel_coarse": deprel,
                "capitalization": caps,
                "word_length": lengths,
            }
            base_id = digest_text(f"ud:{source}:{revision}:{sent_id}:{content_hash}")[:24]
            records.append({
                "base_id": base_id, "content_hash": content_hash, "source": source,
                "source_type": "UD", "source_revision": revision, "source_record_id": sent_id,
                "document_group": group, "source_order": int(match.group(2)), "words": words,
                "labels": labels,
            })
            comments, rows = {}, []

        for line in path.read_text(encoding="utf-8").splitlines() + [""]:
            if not line:
                flush()
            elif line.startswith("#"):
                raw = line[1:].strip()
                if "=" in raw:
                    key, value = raw.split("=", 1)
                    comments[key.strip()] = value.strip()
            else:
                parts = line.split("\t")
                if len(parts) == 10 and parts[0].isdigit():
                    rows.append(parts)
    return records


def normalize_existing_record(row: Mapping[str, Any], source: str) -> dict[str, Any]:
    item = dict(row)
    labels = {key: list(values) for key, values in row["labels"].items()}
    for raw in labels["upos"]:
        if raw not in UPOS_MAP:
            raise RuntimeError(f"unknown UPOS: {raw}")
    match = GUM_SENT_ID.fullmatch(str(row["source_record_id"])) if source == "UD_English-GUM" else None
    item["source_order"] = int(match.group(2)) if match else -1
    item["labels"] = labels
    return item


def split_esl(records: Sequence[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    groups = sorted({row["document_group"] for row in records}, key=lambda x: stable_key("C1C2", x))
    assignment = {group: ("C1" if i % 2 == 0 else "C2") for i, group in enumerate(groups)}
    output = {"C1": [], "C2": []}
    for row in records:
        output[assignment[row["document_group"]]].append(row)
    return output


def select_sentences(records: Sequence[dict[str, Any]], cap: int) -> list[dict[str, Any]]:
    by_group: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in records:
        by_group[row["document_group"]].append(row)
    selected: list[dict[str, Any]] = []
    for group in sorted(by_group):
        ordered = sorted(by_group[group], key=lambda row: stable_key("sentence-cap", row["base_id"]))
        selected.extend(ordered[:cap])
    return sorted(selected, key=lambda row: row["base_id"])


def identity_vocabulary(roles: Mapping[str, Sequence[dict[str, Any]]], minimum: int, maximum: int) -> tuple[list[str], dict[str, dict[str, int]]]:
    frequencies: dict[str, Counter[str]] = {}
    for role, records in roles.items():
        by_group: dict[str, set[str]] = defaultdict(set)
        for row in records:
            by_group[row["document_group"]].update(
                word.lower() for word in row["words"] if any(c.isalpha() for c in word)
            )
        counter: Counter[str] = Counter()
        for labels in by_group.values():
            counter.update(labels)
        frequencies[role] = counter
    common = set.intersection(*[{x for x, n in freq.items() if n >= minimum} for freq in frequencies.values()])
    ordered = sorted(common, key=lambda x: (-min(frequencies[r][x] for r in ROLES), -sum(frequencies[r][x] for r in ROLES), x.encode()))[:maximum]
    return ordered, {role: {label: frequencies[role][label] for label in ordered} for role in ROLES}


def tokenizer_word_layout(tokenizer: Any, words: Sequence[str], max_length: int) -> tuple[list[int], dict[int, int]]:
    full = tokenizer(list(words), is_split_into_words=True, add_special_tokens=False, truncation=False)
    ids = list(map(int, full["input_ids"]))
    word_ids = full.word_ids()
    if len(ids) > max_length:
        ids = ids[:max_length]
    spans: dict[int, list[int]] = defaultdict(list)
    for pos, word in enumerate(word_ids):
        if word is not None:
            spans[int(word)].append(pos)
    first = {word: positions[0] for word, positions in spans.items() if positions[-1] < max_length}
    return ids, first


def row_cap(rows: Sequence[Mapping[str, Any]], maximum: int) -> list[dict[str, Any]]:
    return [dict(row) for row in cap_rows_by_group(rows, max_rows_per_group=maximum)]


@dataclass(frozen=True)
class PairPopulation:
    entity: list[dict[str, Any]]
    context: list[dict[str, Any]]
    used_groups: frozenset[str]


def _first_single_token_propn(record: dict[str, Any], tokenizer: Any) -> tuple[int, str, int] | None:
    for index, upos in enumerate(record["labels"]["upos"]):
        if upos != "PROPN":
            continue
        word = record["words"][index]
        ids = tokenizer.encode(word, add_special_tokens=False)
        if len(ids) == 1 and any(c.isalpha() for c in word):
            return index, word, int(ids[0])
    return None


def build_pair_population(role: str, records: Sequence[dict[str, Any]], tokenizer: Any, max_length: int) -> PairPopulation:
    by_group: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in records:
        by_group[row["document_group"]].append(row)
    candidate: dict[str, tuple[dict[str, Any], int, str, int]] = {}
    for group, rows in by_group.items():
        for row in sorted(rows, key=lambda x: stable_key(f"entity-record|{role}", x["base_id"])):
            found = _first_single_token_propn(row, tokenizer)
            if found is not None:
                candidate[group] = (row, *found)
                break
    groups = sorted(candidate, key=lambda x: stable_key(f"entity-pair|{role}", x))
    entity: list[dict[str, Any]] = []
    used: set[str] = set()
    for source_group, donor_group in zip(groups[0::2], groups[1::2], strict=False):
        source, word_index, source_word, source_id = candidate[source_group]
        _, _, donor_word, donor_id = candidate[donor_group]
        if source_word.lower() == donor_word.lower():
            continue
        target_words = list(source["words"])
        target_words[word_index] = donor_word
        source_ids, source_first = tokenizer_word_layout(tokenizer, source["words"], max_length)
        target_ids, target_first = tokenizer_word_layout(tokenizer, target_words, max_length)
        if source_first.keys() != target_first.keys() or word_index not in source_first:
            continue
        # Single-token substitution must preserve the complete word-to-token layout.
        source_enc = tokenizer(source["words"], is_split_into_words=True, add_special_tokens=False, truncation=True, max_length=max_length)
        target_enc = tokenizer(target_words, is_split_into_words=True, add_special_tokens=False, truncation=True, max_length=max_length)
        if source_enc.word_ids() != target_enc.word_ids() or len(source_ids) != len(target_ids):
            continue
        word_positions = [i for i, value in enumerate(source_enc.word_ids()) if value == word_index]
        changed_positions = [i for i, (left, right) in enumerate(zip(source_ids, target_ids, strict=True)) if left != right]
        if len(word_positions) != 1 or changed_positions != word_positions:
            continue
        source_id = int(source_ids[word_positions[0]]); donor_id = int(target_ids[word_positions[0]])
        pair_id = digest_text(f"entity|{role}|{source_group}|{donor_group}|{source['base_id']}|{word_index}")[:24]
        component = f"entity_component:{source_group}+{donor_group}"
        entity.append({
            "pair_id": pair_id, "role": role, "construct": "entity_substitution",
            "component_group": component, "source_document_group": source_group,
            "donor_document_group": donor_group, "source_base_id": source["base_id"],
            "source_record_id": source["source_record_id"], "word_index": word_index,
            "source_word": source_word, "donor_word": donor_word,
            "source_token_id": source_id, "donor_token_id": donor_id,
            "source_input_ids": source_ids, "target_input_ids": target_ids,
            "source_positions": [source_first[word_index]], "target_positions": [target_first[word_index]],
        })
        used.update((source_group, donor_group))

    context: list[dict[str, Any]] = []
    for group in sorted(by_group, key=lambda x: stable_key(f"context-group|{role}", x)):
        if group in used:
            continue
        rows = sorted(by_group[group], key=lambda x: (int(x.get("source_order", -1)), x["source_record_id"]))
        if len(rows) < 2 or any(int(x.get("source_order", -1)) < 0 for x in rows):
            continue
        choices: list[tuple[int, int, int, str, dict[str, Any], dict[str, Any]]] = []
        for left, right in zip(rows, rows[1:], strict=False):
            gap = int(right["source_order"]) - int(left["source_order"])
            if gap <= 0:
                continue
            tie = digest_text(f"context-pair|{role}|{left['base_id']}|{right['base_id']}")
            choices.append((gap, int(left["source_order"]), int(right["source_order"]), tie, left, right))
        if not choices:
            continue
        gap, _, _, _, earlier, later = min(choices, key=lambda x: x[:4])
        earlier_ids, _ = tokenizer_word_layout(tokenizer, earlier["words"], max_length)
        later_ids, later_first = tokenizer_word_layout(tokenizer, later["words"], max_length)
        target_ids = earlier_ids + [0] + later_ids
        if len(target_ids) > max_length or not later_first:
            continue
        shift = len(earlier_ids) + 1
        word_indices = sorted(later_first)
        pair_id = digest_text(f"context|{role}|{group}|{earlier['base_id']}|{later['base_id']}")[:24]
        context.append({
            "pair_id": pair_id, "role": role, "construct": "document_context_anchor",
            "component_group": group, "document_group": group,
            "source_order_parser": "GUM_TRAILING_HYPHEN_INT" if role == "calibration" else "ESLSPOK_TRAILING_UNDERSCORE_INT",
            "earlier_base_id": earlier["base_id"], "later_base_id": later["base_id"],
            "earlier_record_id": earlier["source_record_id"], "later_record_id": later["source_record_id"],
            "source_order_gap": gap, "separator_token_id": 0,
            "source_input_ids": later_ids, "target_input_ids": target_ids,
            "source_positions": [later_first[i] for i in word_indices],
            "target_positions": [shift + later_first[i] for i in word_indices],
            "word_indices": word_indices,
        })
        used.add(group)
    return PairPopulation(entity=entity, context=context, used_groups=frozenset(used))


def _labels_for_main_row(record: dict[str, Any], word_index: int, identity: set[str]) -> dict[str, str]:
    upos_raw = record["labels"]["upos"][word_index]
    dep_raw = record["labels"]["deprel_coarse"][word_index].split(":", 1)[0]
    cap_raw = record["labels"]["capitalization"][word_index]
    if upos_raw not in UPOS_MAP or dep_raw not in DEPREL_MAP or cap_raw not in CAP_MAP:
        raise RuntimeError(f"unknown frozen label at {record['base_id']}:{word_index}")
    token = record["words"][word_index].lower()
    return {
        "relative_quartile": str(record["labels"]["relative_quartile"][word_index]),
        "head_signed_distance": str(record["labels"]["head_signed_distance"][word_index]),
        "dependency_depth": str(record["labels"]["dependency_depth"][word_index]),
        "deprel_coarse": DEPREL_MAP[dep_raw],
        "upos_coarse": UPOS_MAP[upos_raw],
        "capitalization": CAP_MAP[cap_raw],
        "word_length": str(record["labels"]["word_length"][word_index]),
        "punctuation": "punct" if upos_raw == "PUNCT" else "nonpunct",
        "token_identity_v2": token if token in identity else DROP,
        "token_identity_nuisance": token if token in identity else "__NONRETAINED__",
    }


def build_role_data(
    role: str,
    records: Sequence[dict[str, Any]],
    pairs: PairPopulation | None,
    identity: set[str],
    tokenizer: Any,
    cfg: Mapping[str, Any],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, list[dict[str, Any]]], list[dict[str, Any]]]:
    max_length = int(cfg["data"]["max_length"])
    source = str(records[0]["source"])
    units: list[dict[str, Any]] = []
    activation_rows: list[dict[str, Any]] = []
    candidates: dict[str, list[dict[str, Any]]] = {task: [] for task in ALL_TASKS}

    for record in records:
        input_ids, first = tokenizer_word_layout(tokenizer, record["words"], max_length)
        positions: list[int] = []
        row_ids: list[str] = []
        for word_index in sorted(first):
            row_id = f"main:{record['base_id']}:{word_index}"
            labels = _labels_for_main_row(record, word_index, identity)
            activation_index = len(activation_rows)
            activation_rows.append({
                "activation_index": activation_index, "row_id": row_id, "role": role,
                "kind": "main", "base_id": record["base_id"], "source_record_id": record["source_record_id"],
                "document_group": record["document_group"], "source": source,
                "word_index": word_index, "token_position": first[word_index], "labels": labels,
            })
            positions.append(first[word_index]); row_ids.append(row_id)
            for task in ALL_TASKS:
                label = labels[task]
                if label == DROP:
                    continue
                candidates[task].append({
                    "row_id": row_id, "activation_index": activation_index, "label": label,
                    "document_group": record["document_group"], "source": source,
                })
        unit_id = f"main:{record['base_id']}"
        units.append({"unit_id": unit_id, "role": role, "kind": "main", "input_ids": input_ids,
                      "positions": positions, "row_ids": row_ids})

    pair_rows: list[dict[str, Any]] = []
    if pairs is not None:
        for pair in sorted(pairs.entity + pairs.context, key=lambda row: row["pair_id"]):
            source_rows: list[str] = []
            target_rows: list[str] = []
            for side in ("source", "target"):
                row_ids: list[str] = []
                for local_index, position in enumerate(pair[f"{side}_positions"]):
                    row_id = f"pair:{pair['pair_id']}:{side}:{local_index}"
                    activation_index = len(activation_rows)
                    activation_rows.append({
                        "activation_index": activation_index, "row_id": row_id, "role": role,
                        "kind": "pair", "pair_id": pair["pair_id"], "construct": pair["construct"],
                        "component_group": pair["component_group"], "side": side,
                        "token_position": int(position),
                    })
                    row_ids.append(row_id)
                units.append({
                    "unit_id": f"pair:{pair['pair_id']}:{side}", "role": role, "kind": "pair",
                    "pair_id": pair["pair_id"], "side": side,
                    "input_ids": pair[f"{side}_input_ids"], "positions": pair[f"{side}_positions"],
                    "row_ids": row_ids,
                })
                if side == "source": source_rows = row_ids
                else: target_rows = row_ids
            pair_rows.append({
                "pair_id": pair["pair_id"], "role": role, "construct": pair["construct"],
                "component_group": pair["component_group"], "source_row_ids": source_rows,
                "target_row_ids": target_rows,
                "source_order_parser": pair.get("source_order_parser"),
            })

    for index, row in enumerate(activation_rows):
        if row["activation_index"] != index:
            raise AssertionError("activation row order drift")
    return units, activation_rows, candidates, pair_rows


def _existing_role_records(cfg: Mapping[str, Any], role: str) -> list[dict[str, Any]]:
    spec = cfg["existing_public_records"][role]
    path = root_path(spec["path"])
    verify_file(path, spec["sha256"])
    rows = [normalize_existing_record(row, spec["source"]) for row in read_jsonl(path) if row["source"] == spec["source"]]
    if not rows:
        raise RuntimeError(f"empty existing public source: {role}")
    return rows


def _prescore_reconnaissance(
    cfg: Mapping[str, Any], full_roles: Mapping[str, Sequence[dict[str, Any]]], tokenizer: Any,
) -> tuple[dict[str, list[dict[str, Any]]], list[str], dict[str, dict[str, int]], dict[str, PairPopulation | None], dict[str, Any]]:
    selected_roles={role:select_sentences(records,int(cfg["data"]["sentences_per_group"])) for role,records in full_roles.items()}
    vocab,vocab_frequencies=identity_vocabulary(
        selected_roles,int(cfg["support"]["min_class_groups"]),int(cfg["data"]["identity_vocabulary_max"]),
    )
    if len(vocab)<2:raise RuntimeError("identity vocabulary infeasible")
    populations:dict[str,PairPopulation|None]={"discovery":None}
    for role in ("calibration","C1","C2"):
        populations[role]=build_pair_population(role,selected_roles[role],tokenizer,int(cfg["data"]["max_length"]))
        population=populations[role];assert population is not None
        if len(population.entity)<int(cfg["data"]["entity_pair_minimum"]) or len(population.context)<int(cfg["data"]["context_pair_minimum"]):
            raise RuntimeError(f"counterfactual population infeasible: {role}")
    summary={"schema_version":"atlas_measurement_v2_reconnaissance_v1",
        "roles":{role:{"selected_records":len(selected_roles[role]),
            "groups":len({row["document_group"] for row in selected_roles[role]}),
            "entity_pairs":0 if populations[role] is None else len(populations[role].entity),
            "document_context_pairs":0 if populations[role] is None else len(populations[role].context)} for role in ROLES},
        "identity_vocabulary":vocab,"identity_document_frequencies":vocab_frequencies}
    return selected_roles,vocab,vocab_frequencies,populations,summary


def source_grouping(cfg: Mapping[str, Any], config_path: Path) -> dict[str, Any]:
    data_root = root_path(cfg["data_root"])
    raw_root = data_root / "raw" / "UD_English-ESLSpok" / cfg["replacement_source"]["revision"]
    paths: list[Path] = []
    for item in cfg["replacement_source"]["files"]:
        paths.append(download_verified(item["url"], raw_root / item["name"], item["sha256"]))
    records = parse_esl_files(paths, cfg["replacement_source"]["id"], cfg["replacement_source"]["revision"])
    split = split_esl(records)
    if len(records) != 2320 or {role: len({x["document_group"] for x in rows}) for role, rows in split.items()} != {"C1": 436, "C2": 436}:
        raise RuntimeError("replacement grouping cardinality drift")
    mapping = sorted((row["source_record_id"], row["document_group"], "C1" if row in split["C1"] else "C2") for row in records)
    mapping_digest = hashlib.sha256(b"".join(canonical_json_bytes(row) for row in mapping)).hexdigest()
    content_counts=Counter(str(row["content_hash"]) for row in records)
    from transformers import AutoTokenizer
    tokenizer=AutoTokenizer.from_pretrained(cfg["model"]["name"],revision=cfg["model"]["revision"],local_files_only=True,use_fast=True)
    full_roles={"discovery":_existing_role_records(cfg,"discovery"),"calibration":_existing_role_records(cfg,"calibration"),
                "C1":split["C1"],"C2":split["C2"]}
    _,_,_,_,reconnaissance=_prescore_reconnaissance(cfg,full_roles,tokenizer)
    reconnaissance_sha=hashlib.sha256(canonical_json_bytes(reconnaissance)).hexdigest()
    return {
        "schema_version": "atlas_measurement_v2_grouping_builder_v1",
        "config_sha256": sha256_file(config_path), "dataset_id": cfg["replacement_source"]["id"],
        "git_head":subprocess.check_output(["git","rev-parse","HEAD"],cwd=ROOT,text=True).strip(),
        "revision": cfg["replacement_source"]["revision"],
        "files": [{"name": item["name"], "url": item["url"], "sha256": item["sha256"]} for item in cfg["replacement_source"]["files"]],
        "tokenizer_model": cfg["model"],
        "natural_sampling_unit": "source transcript file prefix in sent_id",
        "source_field": "sent_id anchored regex ^(file[0-9]+\\.txt)_([0-9]+)$",
        "original_units": len(records), "groups": 872, "role_groups": {"C1": 436, "C2": 436},
        "repeated_content_hashes":sum(1 for count in content_counts.values() if count>1),
        "maximum_content_hash_multiplicity":max(content_counts.values()),
        "mapping_sha256": mapping_digest,
        "reconnaissance":reconnaissance,"reconnaissance_sha256":reconnaissance_sha,
        "dependence_rationale": "never split a public source transcript-file prefix; no claim of one speaker/session per prefix",
        "grouping_code_sha256": sha256_file(ROOT / "scripts/msae_measurement_v2_run.py"),
        "builder_identity": "atlas_measurement_v2_run.source_grouping",
    }


def sign_builder_payload(payload: Mapping[str, Any]) -> dict[str, Any]:
    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

    private = Ed25519PrivateKey.generate()
    public = private.public_key().public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw)
    message = canonical_json_bytes(payload)
    return {
        "payload": payload, "payload_sha256": hashlib.sha256(message).hexdigest(),
        "public_key_base64": base64.b64encode(public).decode(),
        "public_key_fingerprint": hashlib.sha256(public).hexdigest(),
        "signature_base64": base64.b64encode(private.sign(message)).decode(),
    }


def verify_signed_builder(envelope: Mapping[str, Any]) -> None:
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

    payload = envelope["payload"]
    message = canonical_json_bytes(payload)
    public = base64.b64decode(envelope["public_key_base64"], validate=True)
    signature = base64.b64decode(envelope["signature_base64"], validate=True)
    if hashlib.sha256(message).hexdigest() != envelope["payload_sha256"]:
        raise RuntimeError("builder payload digest mismatch")
    if hashlib.sha256(public).hexdigest() != envelope["public_key_fingerprint"]:
        raise RuntimeError("builder key fingerprint mismatch")
    Ed25519PublicKey.from_public_bytes(public).verify(signature, message)


def verify_reviewer_envelope(envelope: Mapping[str, Any], cfg: Mapping[str, Any], builder: Mapping[str, Any]) -> None:
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

    payload = envelope["payload"]
    required = {
        "schema_version": "atlas_measurement_v2_grouping_review_v1",
        "canonical_task_identity": cfg["reviewer_trust"]["canonical_task_identity"],
        "builder_payload_sha256": builder["payload_sha256"], "decision": "pass",
    }
    for key, value in required.items():
        if payload.get(key) != value:
            raise RuntimeError(f"reviewer payload mismatch: {key}")
    if builder["payload"].get("config_sha256")!=sha256_file(ROOT/"configs/atlas_measurement_v2/run.json"):
        raise RuntimeError("builder config digest is not current")
    observed_head=subprocess.check_output(["git","rev-parse","HEAD"],cwd=ROOT,text=True).strip()
    if builder["payload"].get("git_head")!=observed_head:
        raise RuntimeError("builder Git revision drift")
    if payload.get("grouping_code_sha256") != builder["payload"]["grouping_code_sha256"]:
        raise RuntimeError("reviewer grouping-code digest mismatch")
    for key in ("review_transcript_sha256", "grouping_code_diff_sha256"):
        if not isinstance(payload.get(key), str) or re.fullmatch(r"[0-9a-f]{64}", payload[key]) is None:
            raise RuntimeError(f"reviewer payload lacks digest: {key}")
    if not isinstance(payload.get("reviewed_utc"), str) or re.fullmatch(r"20[0-9]{2}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}Z", payload["reviewed_utc"]) is None:
        raise RuntimeError("reviewer payload timestamp malformed")
    if not isinstance(payload.get("reviewer_execution_identity"), str) or not payload["reviewer_execution_identity"]:
        raise RuntimeError("reviewer execution identity absent")
    if payload["reviewer_execution_identity"]==builder["payload"].get("builder_identity"):
        raise RuntimeError("builder/reviewer execution identities are not distinct")
    builder_public=base64.b64decode(builder["public_key_base64"],validate=True)
    if payload.get("builder_public_key_fingerprint")!=hashlib.sha256(builder_public).hexdigest():
        raise RuntimeError("reviewer did not bind builder public key")
    artifacts={
        "review_transcript_sha256":"reviewer_transcript.md",
        "grouping_code_diff_sha256":"grouping_code.diff",
    }
    for digest_key,name in artifacts.items():
        expected_path=f"{cfg['data_root']}/provenance/{name}"
        if payload.get(digest_key.replace("sha256","path"))!=expected_path:
            raise RuntimeError(f"reviewer artifact path mismatch: {name}")
        verify_file(root_path(expected_path),payload[digest_key])
    public = base64.b64decode(envelope["public_key_base64"], validate=True)
    if base64.b64encode(public).decode() != cfg["reviewer_trust"]["raw_public_key_base64"]:
        raise RuntimeError("reviewer trust key mismatch")
    message = canonical_json_bytes(payload)
    if hashlib.sha256(message).hexdigest() != envelope["payload_sha256"]:
        raise RuntimeError("reviewer payload digest mismatch")
    Ed25519PublicKey.from_public_bytes(public).verify(base64.b64decode(envelope["signature_base64"]), message)


def prepare_data(cfg: Mapping[str, Any], config_path: Path) -> dict[str, Any]:
    data_root = root_path(cfg["data_root"])
    output = data_root / "prepared"
    if output.exists():
        return verify_prepared(cfg, config_path)
    builder_path = data_root / "provenance" / "builder.json"
    reviewer_path = data_root / "provenance" / "reviewer.json"
    builder = read_json(builder_path); reviewer = read_json(reviewer_path)
    verify_signed_builder(builder)
    verify_reviewer_envelope(reviewer, cfg, builder)
    if builder["public_key_base64"] == reviewer["public_key_base64"]:
        raise RuntimeError("builder and reviewer trust keys must be distinct")
    if builder["payload"]["grouping_code_sha256"] != sha256_file(ROOT / "scripts/msae_measurement_v2_run.py"):
        raise RuntimeError("grouping code changed after signed review")

    from transformers import AutoTokenizer

    tokenizer = AutoTokenizer.from_pretrained(cfg["model"]["name"], revision=cfg["model"]["revision"], local_files_only=True, use_fast=True)
    raw_root = data_root / "raw" / "UD_English-ESLSpok" / cfg["replacement_source"]["revision"]
    paths = [raw_root / item["name"] for item in cfg["replacement_source"]["files"]]
    for path, item in zip(paths, cfg["replacement_source"]["files"], strict=True):
        verify_file(path, item["sha256"])
    esl = parse_esl_files(paths, cfg["replacement_source"]["id"], cfg["replacement_source"]["revision"])
    split = split_esl(esl)
    full_roles = {
        "discovery": _existing_role_records(cfg, "discovery"),
        "calibration": _existing_role_records(cfg, "calibration"),
        "C1": split["C1"], "C2": split["C2"],
    }
    selected_roles,vocab,vocab_frequencies,populations,reconnaissance=_prescore_reconnaissance(cfg,full_roles,tokenizer)
    if hashlib.sha256(canonical_json_bytes(reconnaissance)).hexdigest()!=builder["payload"]["reconnaissance_sha256"]:
        raise RuntimeError("signed reconnaissance drift")

    tmp = data_root / f".prepared.{os.getpid()}.tmp"
    if tmp.exists(): shutil.rmtree(tmp)
    tmp.mkdir(parents=True)
    role_reports: dict[str, Any] = {}
    input_inventory: dict[str, str] = {
        str(builder_path.relative_to(ROOT)): sha256_file(builder_path),
        str(reviewer_path.relative_to(ROOT)): sha256_file(reviewer_path),
    }
    thresholds = SupportThresholds(
        min_groups=int(cfg["support"]["min_groups"]), min_class_groups=int(cfg["support"]["min_class_groups"]),
        max_rows_per_group=int(cfg["support"]["max_rows_per_group"]), bootstrap_draws=int(cfg["bootstrap"]["draws"]),
        min_finite_draws=int(cfg["support"]["min_finite_draws"]), seed=int(cfg["seed"]),
    )
    for role in ROLES:
        units, activation_rows, candidates, pair_rows = build_role_data(
            role, selected_roles[role], populations[role], set(vocab), tokenizer, cfg
        )
        role_dir = tmp / role; (role_dir / "tasks").mkdir(parents=True)
        unit_sha, _ = atomic_write_jsonl(role_dir / "inference_units.jsonl", units)
        rows_sha, _ = atomic_write_jsonl(role_dir / "activation_rows.jsonl", activation_rows)
        pair_sha, _ = atomic_write_jsonl(role_dir / "pairs.jsonl", pair_rows)
        support: dict[str, Any] = {}
        task_specs: dict[str, Any] = {}
        for task in ALL_TASKS:
            selected = row_cap(candidates[task], int(cfg["support"]["max_rows_per_group"]))
            task_sha, _ = atomic_write_jsonl(role_dir / "tasks" / f"{task}.jsonl", selected)
            audit = audit_task_support(selected, role=role, task=task,
                                       expected_sources=[str(selected_roles[role][0]["source"])], thresholds=thresholds)
            if audit["status"] != "eligible":
                raise RuntimeError(f"prescore support failure {role}/{task}: {audit['reasons']}")
            support[task] = audit
            task_specs[task] = {"rows": len(selected), "sha256": task_sha}
        role_reports[role] = {
            "source": selected_roles[role][0]["source"], "records": len(selected_roles[role]),
            "groups": len({r["document_group"] for r in selected_roles[role]}),
            "activation_rows": len(activation_rows), "units": len(units),
            "entity_pairs": 0 if populations[role] is None else len(populations[role].entity),
            "document_context_pairs": 0 if populations[role] is None else len(populations[role].context),
            "units_sha256": unit_sha, "activation_rows_sha256": rows_sha, "pairs_sha256": pair_sha,
            "tasks": task_specs, "support": support,
        }
    manifest = {
        "schema_version": "atlas_measurement_v2_prepared_v1", "config_sha256": sha256_file(config_path),
        "builder_payload_sha256": builder["payload_sha256"], "reviewer_payload_sha256": reviewer["payload_sha256"],
        "tokenizer": cfg["model"], "identity_vocabulary": vocab,
        "identity_document_frequencies": vocab_frequencies, "roles": role_reports,
        "strict_absolute_position": {"status": "ineligible", "reason": "model_architecture_symmetry"},
        "input_inventory": input_inventory,
    }
    atomic_write_json(tmp / "manifest.json", manifest)
    os.replace(tmp, output)
    return manifest


def verify_prepared(cfg: Mapping[str, Any], config_path: Path) -> dict[str, Any]:
    root = root_path(cfg["data_root"]) / "prepared"
    manifest = read_json(root / "manifest.json")
    if manifest["config_sha256"] != sha256_file(config_path):
        raise RuntimeError("prepared config mismatch")
    for relative, expected in manifest.get("input_inventory", {}).items():
        verify_file(root_path(relative), expected)
    builder = read_json(root_path(cfg["data_root"]) / "provenance/builder.json")
    reviewer = read_json(root_path(cfg["data_root"]) / "provenance/reviewer.json")
    verify_signed_builder(builder)
    verify_reviewer_envelope(reviewer, cfg, builder)
    if builder["public_key_base64"] == reviewer["public_key_base64"]:
        raise RuntimeError("builder and reviewer trust keys must be distinct")
    if builder["payload"]["grouping_code_sha256"] != sha256_file(ROOT / "scripts/msae_measurement_v2_run.py"):
        raise RuntimeError("signed grouping code drift")
    if manifest.get("builder_payload_sha256") != builder["payload_sha256"]:
        raise RuntimeError("prepared builder provenance drift")
    if manifest.get("reviewer_payload_sha256") != reviewer["payload_sha256"]:
        raise RuntimeError("prepared reviewer provenance drift")
    for role in ROLES:
        spec = manifest["roles"][role]
        for name, key in (("inference_units.jsonl", "units_sha256"), ("activation_rows.jsonl", "activation_rows_sha256"), ("pairs.jsonl", "pairs_sha256")):
            verify_file(root / role / name, spec[key])
        for task in ALL_TASKS:
            verify_file(root / role / "tasks" / f"{task}.jsonl", spec["tasks"][task]["sha256"])
    return manifest


def cache_manifest(cache_dir: Path) -> dict[str, Any]:
    manifest = read_json(cache_dir / "manifest.json")
    verify_file(cache_dir / "values.float32.npy", manifest["values_sha256"])
    verify_file(cache_dir / "row_ids.json", manifest["row_ids_sha256"])
    values = np.load(cache_dir / "values.float32.npy", mmap_mode="r")
    if values.dtype != np.float32 or list(values.shape) != manifest["shape"]:
        raise RuntimeError(f"cache shape/dtype drift: {cache_dir}")
    row_ids = read_json(cache_dir / "row_ids.json")
    if len(row_ids) != len(values) or len(row_ids) != len(set(row_ids)):
        raise RuntimeError(f"cache row-id drift: {cache_dir}")
    return manifest


def write_vector_cache(output: Path, values: np.ndarray, row_ids: Sequence[str], lineage: Mapping[str, Any]) -> dict[str, Any]:
    if output.exists():
        return cache_manifest(output)
    if values.dtype != np.float32 or values.ndim != 2 or len(values) != len(row_ids) or len(set(row_ids)) != len(row_ids):
        raise ValueError("invalid float32 vector cache")
    tmp = output.parent / f".{output.name}.{os.getpid()}.tmp"
    if tmp.exists(): shutil.rmtree(tmp)
    tmp.mkdir(parents=True)
    np.save(tmp / "values.float32.npy", values, allow_pickle=False)
    atomic_write_json(tmp / "row_ids.json", list(row_ids))
    manifest = {
        "schema_version": "atlas_measurement_v2_vector_cache_v1", "shape": list(values.shape),
        "dtype": "float32", "values_sha256": sha256_file(tmp / "values.float32.npy"),
        "row_ids_sha256": sha256_file(tmp / "row_ids.json"), "lineage": dict(lineage),
    }
    atomic_write_json(tmp / "manifest.json", manifest)
    output.parent.mkdir(parents=True, exist_ok=True)
    os.replace(tmp, output)
    return manifest


def weighted_macro_f1(y_true: np.ndarray, y_pred: np.ndarray, weights: np.ndarray, classes: int) -> float:
    if not (len(y_true) == len(y_pred) == len(weights)) or classes < 2:
        raise ValueError("invalid macro-F1 inputs")
    values: list[float] = []
    for label in range(classes):
        true = y_true == label; pred = y_pred == label
        tp = float(weights[true & pred].sum()); fp = float(weights[~true & pred].sum()); fn = float(weights[true & ~pred].sum())
        denom = 2*tp + fp + fn
        values.append(0.0 if denom <= 0 else 2*tp/denom)
    return float(np.mean(values))


def group_multiplicities(
    groups: Sequence[str], *, role: str, task: str, source: str, draw: int, seed: int,
) -> dict[str, int]:
    unique = sorted(set(groups), key=lambda x: x.encode())
    if not unique:
        return {}
    counts = Counter()
    for slot in range(len(unique)):
        payload = f"atlas_measurement_v2|{seed}|{role}|{task}|{source}|{draw}|{slot}".encode()
        index = int.from_bytes(hashlib.sha256(payload).digest()[:8], "big") % len(unique)
        counts[unique[index]] += 1
    return dict(counts)


def interval(values: Sequence[float | None]) -> dict[str, Any]:
    finite = np.asarray([x for x in values if x is not None and math.isfinite(x)], np.float64)
    if len(finite) == 0:
        return {"finite": 0, "lower": None, "upper": None, "mean": None}
    return {"finite": len(finite), "lower": float(np.quantile(finite, 0.025, method="linear")),
            "upper": float(np.quantile(finite, 0.975, method="linear")), "mean": float(finite.mean())}


def cosine_distance(left: np.ndarray, right: np.ndarray) -> float | None:
    a = np.asarray(left, np.float64); b = np.asarray(right, np.float64)
    if a.shape != b.shape or a.ndim != 1 or not np.isfinite(a).all() or not np.isfinite(b).all():
        return None
    denom = float(np.linalg.norm(a) * np.linalg.norm(b))
    if denom <= 0:
        return None
    return float(1.0 - np.dot(a, b)/denom)


def cka_torch(left: np.ndarray, right: np.ndarray, device: str) -> float | None:
    import torch
    if left.shape[0] != right.shape[0] or left.shape[0] < 2 or not np.isfinite(left).all() or not np.isfinite(right).all():
        return None
    x = torch.as_tensor(np.asarray(left, np.float32), device=device)
    y = torch.as_tensor(np.asarray(right, np.float32), device=device)
    x = x - x.mean(0, keepdim=True); y = y - y.mean(0, keepdim=True)
    xy = torch.linalg.matrix_norm(x.T @ y).square()
    xx = torch.linalg.matrix_norm(x.T @ x); yy = torch.linalg.matrix_norm(y.T @ y)
    denom = xx*yy
    if not torch.isfinite(denom) or float(denom) <= 0:
        return None
    return float((xy/denom).detach().cpu())


def select_cka_rows(rows: Sequence[Mapping[str, Any]], maximum: int) -> list[dict[str, Any]]:
    by_group_label: dict[str, dict[str, list[Mapping[str, Any]]]] = defaultdict(lambda: defaultdict(list))
    for row in rows:
        by_group_label[str(row["document_group"])][str(row["label"])].append(row)
    for group in by_group_label:
        for label in by_group_label[group]:
            by_group_label[group][label].sort(key=lambda r: stable_key("cka-row", str(r["row_id"])))
    groups = sorted(by_group_label); output: list[dict[str, Any]] = []; pass_index = 0
    while len(output) < maximum:
        progressed = False
        for group in groups:
            for label in sorted(by_group_label[group]):
                values = by_group_label[group][label]
                if pass_index < len(values) and len(output) < maximum:
                    output.append(dict(values[pass_index])); progressed = True
        if not progressed: break
        pass_index += 1
    return sorted(output, key=lambda row: str(row["row_id"]).encode())
