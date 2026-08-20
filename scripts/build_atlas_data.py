#!/usr/bin/env python3
"""Materialize deterministic, role-disjoint atlas-v1 sentence and token manifests."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import random
import sys
import urllib.request
from collections import Counter
from pathlib import Path
from typing import Any, Iterable

from datasets import load_dataset
from transformers import AutoTokenizer


ROOT = Path(__file__).resolve().parents[1]
DROP = "__DROP__"
WIKI_TAGS = ["O", "B-PER", "I-PER", "B-ORG", "I-ORG", "B-LOC", "I-LOC", "B-MISC", "I-MISC"]


def canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def digest_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def digest_text(value: str) -> str:
    return digest_bytes(value.encode("utf-8"))


def write_json(path: Path, value: Any) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = (json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode()
    path.write_bytes(payload)
    return digest_bytes(payload)


def write_jsonl(path: Path, rows: Iterable[dict[str, Any]]) -> tuple[str, int]:
    path.parent.mkdir(parents=True, exist_ok=True)
    count = 0
    h = hashlib.sha256()
    with path.open("wb") as f:
        for row in rows:
            payload = (canonical_json(row) + "\n").encode("utf-8")
            f.write(payload)
            h.update(payload)
            count += 1
    return h.hexdigest(), count


def download(url: str, path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists():
        tmp = path.with_suffix(path.suffix + ".tmp")
        with urllib.request.urlopen(url, timeout=120) as response, tmp.open("wb") as out:
            out.write(response.read())
        tmp.replace(path)
    return path


def cap_stable(rows: list[dict[str, Any]], cap: int, seed: int) -> list[dict[str, Any]]:
    return sorted(rows, key=lambda r: digest_text(f"{seed}:{r['base_id']}"))[: min(cap, len(rows))]


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


def surface_labels(words: list[str]) -> tuple[list[str], list[str], list[str]]:
    caps, lengths, boundaries = [], [], []
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
        boundaries.append("single" if len(words) == 1 else "initial" if i == 0 else "final" if i == len(words) - 1 else "interior")
    return caps, lengths, boundaries


def parse_ud(path: Path, source: str, revision: str) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    comments: dict[str, str] = {}
    rows: list[list[str]] = []
    current_doc: str | None = None

    def flush() -> None:
        nonlocal rows, comments, current_doc
        if not rows:
            comments = {}
            return
        ids = [int(r[0]) for r in rows]
        words = [r[1] for r in rows]
        lemmas = [r[2].lower() if r[2] != "_" else r[1].lower() for r in rows]
        upos = [r[3] for r in rows]
        heads = [int(r[6]) if r[6].isdigit() else 0 for r in rows]
        deprel = [r[7].split(":", 1)[0] for r in rows]
        numbers = []
        for r in rows:
            number = DROP
            for feat in r[5].split("|") if r[5] not in {"", "_"} else []:
                if feat.startswith("Number="):
                    number = feat.split("=", 1)[1]
                    break
            numbers.append(number)
        id_to_pos = {token_id: i for i, token_id in enumerate(ids)}
        head_dist = [bucket_signed_distance(i, id_to_pos.get(h) if h else None) for i, h in enumerate(heads)]
        depths = [depth_for(i, heads, id_to_pos) for i in range(len(words))]
        caps, lengths, boundaries = surface_labels(words)
        quartile = [str(min(3, (4 * i) // max(1, len(words)))) for i in range(len(words))]
        content = " ".join(words)
        content_hash = digest_text(" ".join(content.lower().split()))
        sent_id = comments.get("sent_id", str(len(records)))
        doc_id = current_doc or sent_id.split(".")[0]
        base_id = digest_text(f"ud:{source}:{revision}:{sent_id}:{content_hash}")[:24]
        records.append({
            "base_id": base_id, "content_hash": content_hash, "source": source, "source_type": "UD",
            "source_revision": revision, "source_record_id": sent_id, "document_group": f"{source}:{doc_id}",
            "words": words, "labels": {"lemma": lemmas, "relative_quartile": quartile,
            "head_signed_distance": head_dist, "dependency_depth": depths, "boundary_state": boundaries,
            "ner_coarse": [DROP] * len(words), "upos": upos, "deprel_coarse": deprel, "number": numbers,
            "capitalization": caps, "word_length": lengths, "source_type": ["UD"] * len(words)}
        })
        rows, comments = [], {}

    for line in path.read_text(encoding="utf-8").splitlines() + [""]:
        if not line:
            flush()
        elif line.startswith("#"):
            raw = line[1:].strip()
            if "=" in raw:
                key, value = raw.split("=", 1)
                comments[key.strip()] = value.strip()
                if key.strip() in {"newdoc id", "newdoc"}:
                    current_doc = value.strip()
        else:
            parts = line.split("\t")
            if len(parts) == 10 and parts[0].isdigit():
                rows.append(parts)
    return records


def coarse_ner(name: str) -> str:
    value = name.removeprefix("B-").removeprefix("I-").lower().replace("_", "-")
    if value in {"o", "0"}:
        return "O"
    if value in {"person", "per"}:
        return "PER"
    if value in {"location", "loc", "building"}:
        return "LOC"
    if value in {"organization", "org", "corporation", "group"}:
        return "ORG"
    return "MISC"


def load_ner(repo: str, revision: str, split: str, config: str | None = None) -> tuple[list[dict[str, Any]], str]:
    dataset = load_dataset(repo, config, split=split, revision=revision)
    feature = dataset.features["ner_tags"].feature
    names = getattr(feature, "names", None)
    if repo == "Babelscape/wikineural":
        names = WIKI_TAGS
    records: list[dict[str, Any]] = []
    for index, row in enumerate(dataset):
        words = [str(x) for x in row["tokens"]]
        if not words or len(words) != len(row["ner_tags"]):
            continue
        raw_names = [str(names[int(x)]) for x in row["ner_tags"]]
        ner = [coarse_ner(x) for x in raw_names]
        lemmas = [w.lower() for w in words]
        caps, lengths, boundaries = surface_labels(words)
        quartile = [str(min(3, (4 * i) // max(1, len(words)))) for i in range(len(words))]
        content_hash = digest_text(" ".join(" ".join(words).lower().split()))
        source_id = str(row.get("id", index))
        base_id = digest_text(f"ner:{repo}:{revision}:{split}:{source_id}:{content_hash}")[:24]
        records.append({
            "base_id": base_id, "content_hash": content_hash, "source": repo, "source_type": "NER",
            "source_revision": revision, "source_record_id": source_id, "document_group": f"{repo}:{split}:{source_id}",
            "words": words, "labels": {"lemma": lemmas, "relative_quartile": quartile,
            "head_signed_distance": [DROP] * len(words), "dependency_depth": [DROP] * len(words),
            "boundary_state": boundaries, "ner_coarse": ner, "upos": [DROP] * len(words),
            "deprel_coarse": [DROP] * len(words), "number": [DROP] * len(words),
            "capitalization": caps, "word_length": lengths, "source_type": ["NER"] * len(words)}
        })
    return records, str(getattr(dataset, "_fingerprint", ""))


def render_units(records: list[dict[str, Any]], role: str, config: dict[str, Any], tokenizer: Any) -> tuple[list[dict[str, Any]], Counter[str]]:
    offsets = config["packing"]["offsets"]
    max_length = int(config["packing"]["max_length"])
    prefix_vocab = config["prefix_vocabularies"][role]
    counters: Counter[str] = Counter()
    units = []
    for record in records:
        prefix_word = prefix_vocab[int(record["base_id"], 16) % len(prefix_vocab)]
        for offset in offsets:
            prefix = [prefix_word] * int(offset)
            packed = prefix + record["words"]
            encoded_full = tokenizer(packed, is_split_into_words=True, add_special_tokens=False, truncation=False)
            full_input_ids = encoded_full["input_ids"]
            full_word_ids = encoded_full.word_ids()
            input_ids = full_input_ids[:max_length]
            word_ids = full_word_ids[:max_length]
            full_spans: dict[int, list[int]] = {}
            for full_index, word_id in enumerate(full_word_ids):
                if word_id is not None:
                    full_spans.setdefault(int(word_id), []).append(full_index)
            complete_words = {word_id for word_id, positions in full_spans.items()
                              if word_id >= offset and positions[-1] < max_length}
            first_positions, seen = [], set()
            for token_index, word_id in enumerate(word_ids):
                if word_id is None or word_id < offset or word_id not in complete_words or word_id in seen:
                    continue
                seen.add(word_id)
                first_positions.append({"model_token_index": token_index, "word_index": word_id - offset})
            truncated_words = len(record["words"]) - len(complete_words)
            counters["tail_truncated_words"] += truncated_words
            counters["model_tokens"] += len(input_ids)
            counters["word_rows"] += len(first_positions)
            continuation = []
            seen_target: set[int] = set()
            for word_id in word_ids:
                if word_id is None:
                    continuation.append(DROP)
                elif word_id < offset:
                    continuation.append("prefix")
                elif word_id in seen_target:
                    continuation.append("continuation")
                else:
                    continuation.append("first")
                    seen_target.add(word_id)
            variant_id = digest_text(f"{record['base_id']}:{role}:{offset}:{prefix_word}")[:24]
            units.append({
                "variant_id": variant_id, "base_id": record["base_id"], "content_hash": record["content_hash"],
                "role": role, "offset": offset, "prefix_word": prefix_word, "input_ids": input_ids,
                "absolute_labels": {"abs_pos_16": [str(i // 8) for i in range(len(input_ids))],
                                    "abs_pos_8": [str(i // 16) for i in range(len(input_ids))]},
                "continuation_status": continuation, "first_subword_rows": first_positions,
                "tail_truncated_words": truncated_words,
            })
    return units, counters


def make_transforms(role: str, records: list[dict[str, Any]], units: list[dict[str, Any]], tokenizer: Any) -> list[dict[str, Any]]:
    lexicons = {
        "discovery": (["Alice", "Brian", "Maya", "Noah"], ["Paris", "London", "Rome", "Berlin"]),
        "calibration": (["Clara", "David", "Elena", "Felix"], ["Madrid", "Dublin", "Oslo", "Vienna"]),
        "C1": (["Grace", "Henry", "Iris", "Jonah"], ["Lisbon", "Prague", "Athens", "Warsaw"]),
        "C2": (["Keira", "Liam", "Mina", "Owen"], ["Helsinki", "Zurich", "Brussels", "Sofia"]),
        "final": (["Priya", "Quinn", "Rosa", "Samir"], ["Tallinn", "Riga", "Vilnius", "Zagreb"]),
    }
    lexical_verbs = ["visited", "left", "entered", "toured", "reached", "described", "photographed", "crossed"]
    transitive = ["praised", "questioned", "assisted", "called", "thanked", "followed", "greeted", "advised"]
    intransitive = ["arrived", "departed", "spoke", "waited", "returned", "rested", "worked", "smiled"]
    adjuncts = [["today"], ["yesterday"], ["on", "Monday"], ["before", "dinner"]]
    patients = ["student", "doctor", "artist", "driver", "teacher", "lawyer", "nurse", "editor"]
    rows: list[dict[str, Any]] = []
    visible: dict[tuple[str, int], set[int]] = {
        (unit["base_id"], int(unit["offset"])): {int(row["word_index"]) for row in unit["first_subword_rows"]}
        for unit in units if int(unit["offset"]) in {0, 32}
    }
    eligible_records = [record for record in records
                        if visible.get((record["base_id"], 0)) == set(range(len(record["words"])))
                        and visible.get((record["base_id"], 32)) == set(range(len(record["words"])))]
    sampled = sorted(eligible_records, key=lambda r: digest_text("transform:" + r["base_id"]))[:32]
    if len(sampled) != 32:
        raise RuntimeError(f"insufficient nontruncated position transforms for {role}: {len(sampled)}")
    for i, record in enumerate(sampled):
        rows.append({"transform_id": digest_text(f"{role}:position:{i}")[:24], "role": role,
                     "family": "position_shift", "template_group": f"position_{i % 4}",
                     "base_id": record["base_id"], "source_offset": 0, "target_offset": 32,
                     "intended_change": "absolute model-token position", "invariants": ["corpus words", "word labels"],
                     "automatic_invariant_check": visible[(record["base_id"], 0)] == visible[(record["base_id"], 32)] == set(range(len(record["words"])))})
    names, places = lexicons[role]
    for i in range(32):
        a, b = names[i % 4], names[(i + 1 + i // 8) % 4]
        place_a, place_b = places[(i // 4) % 4], places[(i // 4 + 1 + i // 16) % 4]
        verb, adjunct = lexical_verbs[i % 8], adjuncts[(i // 8) % 4]
        source = [a, verb, place_a] + adjunct + ["."]
        target = [b, verb, place_b] + adjunct + ["."]
        source_encoding = tokenizer(source, is_split_into_words=True, add_special_tokens=False)
        target_encoding = tokenizer(target, is_split_into_words=True, add_special_tokens=False)
        rows.append({"transform_id": digest_text(f"{role}:lexical:{i}")[:24], "role": role,
                     "family": "lexical_entity_substitution", "template_group": f"lexical_{i % 4}", "source_words": source, "target_words": target,
                     "token_aligned": source_encoding.word_ids() == target_encoding.word_ids(), "intended_change": "entity identity",
                     "invariants": ["predicate", "argument slots", "tense", "adjunct", "punctuation"],
                     "automatic_invariant_check": source[1] == target[1] and source[3:] == target[3:]})
        patient, structural_verb = patients[i % 8], transitive[(i // 4) % 8]
        structural_adjunct = adjuncts[(i // 8) % 4]
        source = [a, structural_verb, "the", patient] + structural_adjunct + ["."]
        target = ["The", patient, "was", structural_verb, "by", a] + structural_adjunct + ["."]
        rows.append({"transform_id": digest_text(f"{role}:structural:{i}")[:24], "role": role,
                     "family": "structural_active_passive", "template_group": f"structural_{i % 4}", "source_words": source, "target_words": target,
                     "token_aligned": False, "intended_change": "voice and dependency order",
                     "invariants": ["agent", "patient", "predicate", "tense", "adjunct"],
                     "automatic_invariant_check": a in target and patient in target and structural_verb in target})
        format_verb, format_adjunct = intransitive[i % 8], adjuncts[(i // 8) % 4]
        source = [a, format_verb] + format_adjunct + ["."]
        fronted = [word.capitalize() if j == 0 else word for j, word in enumerate(format_adjunct)]
        target = fronted + [",", a, format_verb, "."]
        rows.append({"transform_id": digest_text(f"{role}:format:{i}")[:24], "role": role,
                     "family": "punctuation_format", "template_group": f"format_{i % 4}", "source_words": source, "target_words": target,
                     "token_aligned": False, "intended_change": "punctuation and constituent order",
                     "invariants": ["participants", "event", "time"],
                     "automatic_invariant_check": a in target and format_verb in target})
    return rows


def task_manifest(vocab: dict[str, list[str]]) -> dict[str, Any]:
    return {
        "schema_version": "atlas_v1_tasks", "drop_label": DROP, "primary_metric": "macro_f1",
        "families": {
            "absolute_position": ["abs_pos_16", "abs_pos_8"],
            "relative_structural_position": ["relative_quartile", "head_signed_distance", "dependency_depth", "boundary_state"],
            "lexical_semantic_content": ["token_identity_256", "lemma_identity_256", "ner_coarse"],
        },
        "sentinels": ["upos", "deprel_coarse", "number", "capitalization", "word_length", "frequency_bin", "source_type", "continuation_status", "context_offset"],
        "vocabularies": vocab,
        "common_label_maps": {"ner_coarse": ["O", "PER", "ORG", "LOC", "MISC"]},
        "word_task_row_policy": "first_subword_only", "absolute_task_row_policy": "all_nonpadding_model_tokens",
        "unknown_policy": DROP,
    }


def validate_roles(role_records: dict[str, list[dict[str, Any]]], role_units: dict[str, list[dict[str, Any]]]) -> dict[str, Any]:
    failures = []
    roles = list(role_records)
    for i, left in enumerate(roles):
        left_ids = {r["base_id"] for r in role_records[left]}
        left_hash = {r["content_hash"] for r in role_records[left]}
        left_groups = {r["document_group"] for r in role_records[left]}
        for right in roles[i + 1:]:
            if left_ids & {r["base_id"] for r in role_records[right]}:
                failures.append(f"base_id overlap {left}/{right}")
            if left_hash & {r["content_hash"] for r in role_records[right]}:
                failures.append(f"content overlap {left}/{right}")
            if left_groups & {r["document_group"] for r in role_records[right]}:
                failures.append(f"document_group overlap {left}/{right}")
    for role, records in role_records.items():
        expected = {r["base_id"] for r in records}
        unit_groups: dict[str, int] = Counter(u["base_id"] for u in role_units[role])
        if set(unit_groups) != expected or any(n != 4 for n in unit_groups.values()):
            failures.append(f"offset grouping mismatch {role}")
        for record in records:
            n = len(record["words"])
            if any(len(values) != n for values in record["labels"].values()):
                failures.append(f"label alignment {role}/{record['base_id']}")
    return {"passed": not failures, "failures": failures,
            "role_base_counts": {k: len(v) for k, v in role_records.items()},
            "role_unit_counts": {k: len(v) for k, v in role_units.items()}}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, default=ROOT / "configs/atlas/data_sources.json")
    parser.add_argument("--output", type=Path, default=ROOT / "data/atlas_v1")
    parser.add_argument("--rebuild", action="store_true")
    args = parser.parse_args()
    config = json.loads(args.config.read_text())
    output = args.output
    if output.exists() and args.rebuild:
        import shutil
        shutil.rmtree(output)
    output.mkdir(parents=True, exist_ok=True)
    seed = int(config["seed"])
    random.seed(seed)
    os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")
    tokenizer = AutoTokenizer.from_pretrained(config["model"]["name"], revision=config["model"]["revision"], use_fast=True)
    tokenizer.padding_side = "right"
    prefix_qa = {}
    for role, words in config["prefix_vocabularies"].items():
        lengths = {w: len(tokenizer([w], is_split_into_words=True, add_special_tokens=False)["input_ids"]) for w in words}
        prefix_qa[role] = lengths
        if any(n != 1 for n in lengths.values()):
            raise RuntimeError(f"prefix vocabulary is not one-token: {role} {lengths}")

    raw_dir = output / "raw"
    roles_loaded: dict[str, list[dict[str, Any]]] = {}
    source_evidence: dict[str, Any] = {}
    for role in ["discovery", "calibration", "architecture_confirmation", "final"]:
        spec = config["roles"][role]
        ud = spec["ud"]
        ud_url = f"https://raw.githubusercontent.com/UniversalDependencies/{ud['repo']}/{ud['revision']}/{ud['file']}"
        ud_path = download(ud_url, raw_dir / ud["repo"] / ud["revision"] / ud["file"])
        ud_rows = cap_stable(parse_ud(ud_path, ud["repo"], ud["revision"]), int(ud["cap"]), seed)
        ner = spec["ner"]
        ner_rows, fingerprint = load_ner(ner["repo"], ner["revision"], ner["split"], ner.get("config"))
        ner_rows = cap_stable(ner_rows, int(ner["cap"]), seed)
        roles_loaded[role] = ud_rows + ner_rows
        source_evidence[role] = {"ud_url": ud_url, "ud_file_sha256": digest_bytes(ud_path.read_bytes()),
                                 "ud_selected": len(ud_rows), "ner_repo": ner["repo"], "ner_revision": ner["revision"],
                                 "ner_split": ner["split"], "ner_fingerprint": fingerprint, "ner_selected": len(ner_rows)}

    # Cross-role duplicate precedence: discovery > calibration > confirmation > final.
    seen_content: set[str] = set()
    duplicate_exclusions: Counter[str] = Counter()
    for role in ["discovery", "calibration", "architecture_confirmation", "final"]:
        kept = []
        for row in roles_loaded[role]:
            if row["content_hash"] in seen_content:
                duplicate_exclusions[role] += 1
            else:
                seen_content.add(row["content_hash"])
                kept.append(row)
        roles_loaded[role] = kept

    confirmation = roles_loaded.pop("architecture_confirmation")
    role_records: dict[str, list[dict[str, Any]]] = {"discovery": roles_loaded["discovery"], "calibration": roles_loaded["calibration"]}
    for source_type in ["UD", "NER"]:
        subset = [r for r in confirmation if r["source_type"] == source_type]
        by_group: dict[str, list[dict[str, Any]]] = {}
        for row in subset:
            by_group.setdefault(row["document_group"], []).append(row)
        ordered_groups = sorted(by_group, key=lambda group: digest_text("c12:" + group))
        for group_index, group in enumerate(ordered_groups):
            role_records.setdefault("C1" if group_index % 2 == 0 else "C2", []).extend(by_group[group])
    role_records["final"] = roles_loaded["final"]
    for role in role_records:
        role_records[role] = sorted(role_records[role], key=lambda r: r["base_id"])

    counts = Counter()
    lemma_counts = Counter()
    for record in role_records["discovery"]:
        counts.update(w.lower() for w in record["words"])
        lemma_counts.update(record["labels"]["lemma"])
    token_vocab = [w for w, _ in sorted(counts.items(), key=lambda x: (-x[1], x[0]))[:256]]
    lemma_vocab = [w for w, _ in sorted(lemma_counts.items(), key=lambda x: (-x[1], x[0]))[:256]]
    frequencies = sorted(counts.values())
    quantiles = [frequencies[int((len(frequencies) - 1) * q)] for q in (0.25, 0.5, 0.75)] if frequencies else [0, 0, 0]
    for records in role_records.values():
        for record in records:
            words = [w.lower() for w in record["words"]]
            record["labels"]["token_identity_256"] = [w if w in token_vocab else DROP for w in words]
            record["labels"]["lemma_identity_256"] = [w if w in lemma_vocab else DROP for w in record["labels"]["lemma"]]
            bins = []
            for word in words:
                c = counts.get(word, 0)
                bins.append("OOV" if c == 0 else "Q1" if c <= quantiles[0] else "Q2" if c <= quantiles[1] else "Q3" if c <= quantiles[2] else "Q4")
            record["labels"]["frequency_bin"] = bins

    role_units, render_stats = {}, {}
    for role, records in role_records.items():
        units, counters = render_units(records, role, config, tokenizer)
        role_units[role] = units
        render_stats[role] = dict(counters)

    firewall = validate_roles(role_records, role_units)
    if not firewall["passed"]:
        raise RuntimeError(f"firewall failed: {firewall['failures']}")

    hashes: dict[str, Any] = {"schema_version": "atlas_v1_partition_hashes", "files": {}}
    public_summary: dict[str, Any] = {"schema_version": "atlas_v1_public_split_summary", "roles": {}}
    for role in ["discovery", "calibration", "C1", "C2"]:
        for kind, rows in [("records", role_records[role]), ("units", role_units[role])]:
            path = output / "partitions" / f"{role}.{kind}.jsonl"
            h, n = write_jsonl(path, rows)
            hashes["files"][path.relative_to(ROOT).as_posix()] = {"sha256": h, "rows": n, "access": "public_analysis"}
        public_summary["roles"][role] = {"base_sentences": len(role_records[role]), "units": len(role_units[role]),
                                                  "sources": dict(Counter(r["source"] for r in role_records[role]))}

    private_dir = output / "private"
    for kind, rows in [("records", role_records["final"]), ("units", role_units["final"])]:
        path = private_dir / f"final.{kind}.jsonl"
        h, n = write_jsonl(path, rows)
        hashes["files"][path.relative_to(ROOT).as_posix()] = {"sha256": h, "rows": n, "access": "M8_only_unlock_required"}
    public_summary["roles"]["final"] = {"base_sentences": len(role_records["final"]), "units": len(role_units["final"]),
                                                   "sources": dict(Counter(r["source"] for r in role_records["final"])),
                                                   "labels_exposed_publicly": False}

    transform_qa = {}
    transform_manifest = {"schema_version": "atlas_v1_transforms", "roles": {}}
    for role, records in role_records.items():
        rows = make_transforms(role, records, role_units[role], tokenizer)
        path = (private_dir if role == "final" else output / "transforms") / f"{role}.jsonl"
        h, n = write_jsonl(path, rows)
        access = "M8_only_unlock_required" if role == "final" else "public_analysis"
        hashes["files"][path.relative_to(ROOT).as_posix()] = {"sha256": h, "rows": n, "access": access}
        ids = [r["transform_id"] for r in rows]
        content_pairs = [digest_text(canonical_json([r.get("source_words"), r.get("target_words"), r.get("base_id"), r.get("source_offset"), r.get("target_offset")])) for r in rows]
        bad_equal = sum(r.get("source_words") == r.get("target_words") for r in rows if "source_words" in r)
        bad_invariants = sum(not r.get("automatic_invariant_check", True) for r in rows)
        transform_qa[role] = {"rows": n, "unique_ids": len(set(ids)), "bad_equal_pairs": bad_equal,
                              "unique_content_pairs": len(set(content_pairs)), "bad_invariants": bad_invariants,
                              "families": dict(Counter(r["family"] for r in rows)),
                              "token_aligned_lexical": sum(bool(r.get("token_aligned")) for r in rows if r["family"] == "lexical_entity_substitution")}
        if len(ids) != len(set(ids)) or len(content_pairs) != len(set(content_pairs)) or bad_equal or bad_invariants:
            raise RuntimeError(f"transform QA failed for {role}")
        transform_manifest["roles"][role] = {"path": path.relative_to(ROOT).as_posix(), "sha256": h, "rows": n, "access": access}

    manifest = task_manifest({"token_identity_256": token_vocab, "lemma_identity_256": lemma_vocab,
                              "frequency_count_quartiles": quantiles})
    write_json(ROOT / "configs/atlas/task_manifest.json", manifest)
    # YAML-compatible JSON is intentionally duplicated at the roadmap's historical filename.
    write_json(ROOT / "configs/atlas/task_manifest.yaml", manifest)
    write_json(ROOT / "configs/atlas/transform_manifest.json", transform_manifest)
    write_json(ROOT / "configs/atlas/transform_manifest.yaml", transform_manifest)
    write_json(ROOT / "configs/atlas/partition_hashes.json", hashes)
    write_json(ROOT / "configs/atlas/public_split_summary.json", public_summary)
    private_manifest = {"schema_version": "atlas_v1_private_final", "unlock_path": ".atlas_final_unlock",
                        "unlock_present_at_freeze": (ROOT / ".atlas_final_unlock").exists(),
                        "policy": "M8 only; do not evaluate or report labels before signed architecture/checkpoint/claim freeze",
                        "files": {k: v for k, v in hashes["files"].items() if v["access"].startswith("M8")}}
    write_json(private_dir / "final_manifest.json", private_manifest)
    os.chmod(private_dir, 0o700)
    for private_file in private_dir.iterdir():
        if private_file.is_file():
            os.chmod(private_file, 0o600)
    qa = {"schema_version": "atlas_v1_data_qa", "firewall": firewall, "prefix_one_token": prefix_qa,
          "duplicate_exclusions": dict(duplicate_exclusions), "render_stats": render_stats,
          "transform_qa": transform_qa, "final_unlock_present": (ROOT / ".atlas_final_unlock").exists(),
          "source_evidence": source_evidence, "environment": {"python": sys.version, "platform": platform.platform()}}
    write_json(ROOT / "reports/atlas_data_qa.json", qa)
    if qa["final_unlock_present"]:
        raise RuntimeError("final unlock token exists during M2 freeze")
    print(json.dumps({"output": str(output), "firewall": firewall, "hash_file": "configs/atlas/partition_hashes.json"}, indent=2))


if __name__ == "__main__":
    main()
