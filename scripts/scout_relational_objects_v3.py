#!/usr/bin/env python3
"""Label/tokenizer-only feasibility scout for relational-objects v3."""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from concurrent.futures import ProcessPoolExecutor
from copy import deepcopy
from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
from typing import Any, Mapping, Sequence

import numpy as np
from scipy.optimize import linear_sum_assignment
from transformers import AutoTokenizer

from conllu_spec import RangeId, TokenId, parse_file
from relational_objects_v3 import ROOT, atomic_json, atomic_jsonl, canonical_bytes, load_json, sha256_file, stable_hex


@dataclass
class Token:
    token_id: int
    form: str
    lemma: str
    upos: str
    feats: str
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
    document_id: str
    sent_id: str
    text: str
    tokens: list[Token]
    has_mwt: bool
    has_empty: bool
    reconstruction_exact: bool
    input_ids: list[int] | None = None
    spans: dict[int, list[int]] | None = None

    @property
    def key(self) -> str:
        return f"{self.source}:{self.file_name}:{self.sent_id}"


def _comment_value(comments: Sequence[str], key: str) -> str | None:
    for line in comments:
        stripped = line[1:].strip()
        if "=" in stripped and stripped.split("=", 1)[0].strip() == key:
            return stripped.split("=", 1)[1].strip()
    return None


def load_sentences(source: str, paths: Sequence[Path]) -> list[Sentence]:
    output: list[Sentence] = []
    for path in paths:
        parsed = parse_file(path, profile="strict")
        current_document: str | None = None
        for sentence in parsed.sentences:
            newdoc = _comment_value(sentence.comments, "newdoc id")
            if newdoc:
                current_document = newdoc
            if current_document is None:
                raise RuntimeError(f"sentence lacks genuine newdoc id: {path}:{sentence.sent_id}")
            integer_rows = [row for row in sentence.rows if isinstance(row.id, TokenId) and not row.id.is_empty]
            pieces: list[str] = []
            tokens: list[Token] = []
            cursor = 0
            for index, row in enumerate(integer_rows):
                fields = row.fields
                start = cursor
                pieces.append(fields[1])
                cursor += len(fields[1])
                tokens.append(Token(row.id.major, fields[1], fields[2], fields[3], fields[5], int(fields[6]), fields[7], fields[9], index, start, cursor))
                if index + 1 < len(integer_rows) and "SpaceAfter=No" not in fields[9].split("|"):
                    pieces.append(" ")
                    cursor += 1
            reconstructed = "".join(pieces)
            output.append(
                Sentence(
                    source, path.name, f"{source}:{path.stem}:{current_document}", sentence.sent_id,
                    sentence.text, tokens,
                    any(isinstance(row.id, RangeId) for row in sentence.rows),
                    any(isinstance(row.id, TokenId) and row.id.is_empty for row in sentence.rows),
                    reconstructed == sentence.text,
                )
            )
    return output


def align_sentences(sentences: Sequence[Sentence], tokenizer: Any, maximum: int) -> tuple[list[Sentence], dict[str, int]]:
    counts: Counter[str] = Counter()
    output: list[Sentence] = []
    for sentence in sentences:
        counts["seen"] += 1
        if sentence.has_mwt:
            counts["multiword_token"] += 1
            continue
        if sentence.has_empty:
            counts["empty_node"] += 1
            continue
        if not sentence.reconstruction_exact:
            counts["surface_mismatch"] += 1
            continue
        encoded = tokenizer(sentence.text, add_special_tokens=False, return_offsets_mapping=True, truncation=False)
        ids = list(map(int, encoded["input_ids"]))
        offsets = [tuple(map(int, item)) for item in encoded["offset_mapping"]]
        if not ids or len(ids) > maximum:
            counts["length"] += 1
            continue
        spans: dict[int, list[int]] = {}
        used: set[int] = set()
        for token in sentence.tokens:
            selected = [index for index, (start, end) in enumerate(offsets) if end > token.char_start and start < token.char_end and end > start]
            if not selected or selected != list(range(selected[0], selected[-1] + 1)) or used.intersection(selected):
                counts["ambiguous_alignment"] += 1
                break
            spans[token.token_id] = selected
            used.update(selected)
        else:
            sentence.input_ids, sentence.spans = ids, spans
            output.append(sentence)
            counts["retained"] += 1
    return output, dict(counts)


def morph_signature(feats: str, keys: Sequence[str], vocabulary: Mapping[str, Sequence[str]]) -> tuple[str, ...]:
    parsed = {part.split("=", 1)[0]: part.split("=", 1)[1] for part in feats.split("|") if "=" in part}
    output=[]
    for key in keys:
        value=parsed.get(key,"NONE")
        output.append(f"{key}={value if value in vocabulary[key] or value == 'NONE' else 'OTHER'}")
    return tuple(output)


def ancestors(token_id: int, by_id: Mapping[int, Token]) -> set[int]:
    found: set[int] = set()
    cursor = token_id
    while cursor in by_id and by_id[cursor].head:
        cursor = by_id[cursor].head
        if cursor in found:
            raise RuntimeError("dependency cycle")
        found.add(cursor)
    return found


def candidate(sentence: Sentence, first: Token, second: Token, *, label: int, orientation: str, relation: str | None, morph_keys: Sequence[str], morph_vocabulary: Mapping[str, Sequence[str]]) -> dict[str, Any]:
    assert sentence.spans is not None and sentence.input_ids is not None
    earlier, later = (first, second) if first.order < second.order else (second, first)
    if orientation not in {"later_query_is_head", "later_query_is_child"}:
        raise ValueError(orientation)
    head, child = (later, earlier) if orientation == "later_query_is_head" else (earlier, later)
    q_positions, k_positions = sentence.spans[later.token_id], sentence.spans[earlier.token_id]
    query = q_positions[-1]
    signature = (
        abs(later.order - earlier.order), orientation, later.upos, earlier.upos,
        morph_signature(later.feats, morph_keys, morph_vocabulary), morph_signature(earlier.feats, morph_keys, morph_vocabulary),
        later.upos == "PUNCT", earlier.upos == "PUNCT", len(q_positions), len(k_positions),
        min(252, (query // 4) * 4), ((query + 1) // 8) * 8, (len(sentence.input_ids) // 16) * 16,
    )
    base = stable_hex(sentence.key, min(first.token_id, second.token_id), max(first.token_id, second.token_id))
    return {
        "candidate_id": stable_hex(base, label, orientation), "base_pair_id": base,
        "sentence_key": sentence.key, "document_id": sentence.document_id, "label": label,
        "stratum": signature, "orientation": orientation, "relation": relation,
        "query_index": query, "key_positions": k_positions,
        "child_positions": sentence.spans[child.token_id], "head_positions": sentence.spans[head.token_id],
        "query_token_id": later.token_id, "key_token_id": earlier.token_id,
        "child_form": child.form, "head_form": head.form, "child_lemma": child.lemma, "head_lemma": head.lemma,
        "child_feats": child.feats, "head_feats": head.feats,
        "child_upos": child.upos, "head_upos": head.upos,
        "child_is_punct": child.upos == "PUNCT", "head_is_punct": head.upos == "PUNCT",
        "surface_gap": abs(later.order - earlier.order), "causal_key_count": query + 1,
        "sequence_length": len(sentence.input_ids),
    }


def enumerate_by_document(sentences: Sequence[Sentence], morph_keys: Sequence[str], morph_vocabulary: Mapping[str, Sequence[str]], candidate_cap: int) -> dict[str, dict[str, dict[tuple[Any, ...], list[dict[str, Any]]]]]:
    result: dict[str, dict[str, dict[tuple[Any, ...], list[dict[str, Any]]]]] = defaultdict(lambda: {"positive": defaultdict(list), "negative": defaultdict(list)})
    positive_strata: dict[int, set[tuple[Any, ...]]] = {0: set(), 1: set()}
    cached: list[tuple[Sentence, dict[int, Token], dict[int, set[int]], int]] = []
    for sentence in sentences:
        by_id = {token.token_id: token for token in sentence.tokens}
        ancestry = {token_id: ancestors(token_id, by_id) for token_id in by_id}
        partition = int(stable_hex(sentence.source, sentence.document_id)[:16], 16) & 1
        cached.append((sentence, by_id, ancestry, partition))
        for child in sentence.tokens:
            if child.head and child.head in by_id:
                head = by_id[child.head]
                orientation = "later_query_is_head" if head.order > child.order else "later_query_is_child"
                row = candidate(sentence, child, head, label=1, orientation=orientation, relation=child.deprel.split(":", 1)[0], morph_keys=morph_keys, morph_vocabulary=morph_vocabulary)
                stratum = tuple(row["stratum"])
                result[sentence.document_id]["positive"][stratum].append(row)
                positive_strata[partition].add(stratum)

    # A negative can only be used against a positive in the opposite, document-
    # disjoint partition.  Filtering before materialization bounds memory without
    # looking at model features or labels beyond the frozen dependency graph.
    for sentence, by_id, ancestry, partition in cached:
        needed = positive_strata[1 - partition]
        for i, left in enumerate(sentence.tokens):
            for right in sentence.tokens[i + 1 :]:
                if left.head == right.token_id or right.head == left.token_id:
                    continue
                if right.token_id in ancestry[left.token_id] or left.token_id in ancestry[right.token_id]:
                    continue
                for orientation in ("later_query_is_head", "later_query_is_child"):
                    row = candidate(sentence, left, right, label=0, orientation=orientation, relation=None, morph_keys=morph_keys, morph_vocabulary=morph_vocabulary)
                    stratum = tuple(row["stratum"])
                    if stratum in needed:
                        rows = result[sentence.document_id]["negative"][stratum]
                        rows.append(row)
                        rows.sort(key=lambda item: item["candidate_id"])
                        del rows[candidate_cap:]
    for roles in result.values():
        for strata in roles.values():
            for key, rows in strata.items():
                rows.sort(key=lambda row: row["candidate_id"])
                strata[key] = rows[:candidate_cap]
    return result


def orientation_pairs(source: str, positive_doc: str, negative_doc: str, pool: Mapping[str, Any], cap: int) -> list[dict[str, Any]]:
    positives, negatives = pool[positive_doc]["positive"], pool[negative_doc]["negative"]
    output: list[dict[str, Any]] = []
    used_negative: set[str] = set()
    for stratum in sorted(set(positives) & set(negatives), key=canonical_bytes):
        p_rows = sorted(positives[stratum], key=lambda row: row["candidate_id"])
        n_rows = [row for row in sorted(negatives[stratum], key=lambda row: row["candidate_id"]) if row["base_pair_id"] not in used_negative]
        for edge, nonedge in zip(p_rows, n_rows):
            if len(output) >= cap:
                break
            used_negative.add(nonedge["base_pair_id"])
            output.append({"pair_id": stable_hex(source, edge["candidate_id"], nonedge["candidate_id"]), "edge": edge, "nonedge": nonedge, "stratum": list(stratum)})
    return output


def match_components(source: str, pool: Mapping[str, Any], cap: int, maximum_components: int, target_pairs: int) -> list[dict[str, Any]]:
    documents = sorted(pool)
    left = [doc for doc in documents if int(stable_hex(source, doc)[:16], 16) & 1 == 0]
    right = [doc for doc in documents if int(stable_hex(source, doc)[:16], 16) & 1 == 1]
    cached: dict[tuple[int, int], tuple[list[dict[str, Any]], list[dict[str, Any]]]] = {}
    for i, left_doc in enumerate(left):
        for j, right_doc in enumerate(right):
            lr = orientation_pairs(source, left_doc, right_doc, pool, cap)
            rl = orientation_pairs(source, right_doc, left_doc, pool, cap)
            if lr and rl:
                cached[(i, j)] = (lr, rl)
    if not cached:
        return []
    # Lexicographic objective: maximize document-disjoint component cardinality,
    # then pair yield, then the stable document-pair digest.  The bases make a
    # lower-priority total mathematically unable to outweigh one higher-priority
    # unit across the whole assignment.
    rows_count, cols_count = len(left), len(right)
    pair_count = rows_count * cols_count
    max_matches = min(rows_count, cols_count)
    yield_base = max_matches * pair_count + 1
    cardinality_base = max_matches * (2 * cap * yield_base + pair_count) + 1
    matrix = np.zeros((rows_count, cols_count), dtype=np.int64)
    ranked = sorted(cached, key=lambda ij: stable_hex(left[ij[0]], right[ij[1]]))
    for rank, (i, j) in enumerate(ranked):
        lr, rl = cached[(i, j)]
        matrix[i, j] = cardinality_base + (len(lr) + len(rl)) * yield_base + (len(ranked) - rank)
    rows, cols = linear_sum_assignment(matrix, maximize=True)
    components: list[dict[str, Any]] = []
    for i, j in zip(rows.tolist(), cols.tolist()):
        if (i, j) not in cached:
            continue
        lr, rl = cached[(i, j)]
        components.append({
            "component_id": "component:" + stable_hex(source, left[i], right[j])[:24],
            "documents": sorted([left[i], right[j]]), "left_positive_pairs": lr,
            "right_positive_pairs": rl, "pair_count": len(lr) + len(rl),
        })
    components.sort(key=lambda row: (-row["pair_count"], row["component_id"]))
    components = components[:maximum_components]
    mandatory: set[str] = set()
    remaining: list[tuple[str, str, str]] = []
    for component in components:
        for field in ("left_positive_pairs", "right_positive_pairs"):
            selected = component[field]
            if selected:
                mandatory.add(selected[0]["pair_id"])
            remaining.extend((pair["pair_id"], component["component_id"], field) for pair in selected[1:])
    all_count = sum(component["pair_count"] for component in components)
    if all_count >= target_pairs and len(mandatory) <= target_pairs:
        keep = set(mandatory)
        for pair_id, _, _ in sorted(remaining):
            if len(keep) >= target_pairs:
                break
            keep.add(pair_id)
        for component in components:
            for field in ("left_positive_pairs", "right_positive_pairs"):
                component[field] = [pair for pair in component[field] if pair["pair_id"] in keep]
            component["pair_count"] = len(component["left_positive_pairs"]) + len(component["right_positive_pairs"])
    components.sort(key=lambda row: row["component_id"])
    totals = [0] * 5
    for component in sorted(components, key=lambda row: (-row["pair_count"], row["component_id"])):
        fold = min(range(5), key=lambda value: (totals[value], value))
        component["fold"] = fold
        totals[fold] += 1
    return sorted(components, key=lambda row: row["component_id"])


def flatten(source: str, components: Sequence[Mapping[str, Any]], sentences: Mapping[str, Sentence]) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    pairs: list[dict[str, Any]] = []
    examples: list[dict[str, Any]] = []
    unit_examples: dict[str, list[int]] = defaultdict(list)
    for component in components:
        for direction, selected in (("left_positive", component["left_positive_pairs"]), ("right_positive", component["right_positive_pairs"])):
            for pair in selected:
                pair_id = "pair:" + pair["pair_id"][:24]
                indices: dict[str, int] = {}
                for name in ("edge", "nonedge"):
                    row = pair[name]
                    index = len(examples)
                    indices[name] = index
                    example = {key: value for key, value in row.items() if key not in {"stratum", "candidate_id", "base_pair_id"}}
                    example.update({"example_index": index, "example_id": "example:" + stable_hex(pair_id, name)[:24], "pair_id": pair_id, "component_id": component["component_id"], "fold": component["fold"], "pair_direction": direction, "stratum_sha256": hashlib.sha256(canonical_bytes(row["stratum"])).hexdigest()})
                    examples.append(example)
                    unit_examples[row["sentence_key"]].append(index)
                pairs.append({"pair_id": pair_id, "component_id": component["component_id"], "fold": component["fold"], "orientation": pair["edge"]["orientation"], "edge_index": indices["edge"], "nonedge_index": indices["nonedge"], "documents": component["documents"], "stratum_sha256": examples[indices["edge"]]["stratum_sha256"]})
    units = []
    for key in sorted(unit_examples):
        sentence = sentences[key]
        assert sentence.input_ids is not None
        units.append({"unit_id": stable_hex(source, key)[:24], "source": source, "sentence_key": key, "input_ids": sentence.input_ids, "example_indices": unit_examples[key]})
    return examples, pairs, units


def _support(
    source: str,
    components: Sequence[Mapping[str, Any]],
    alignment: Mapping[str, int],
) -> dict[str, Any]:
    pairs = [
        pair
        for component in components
        for field in ("left_positive_pairs", "right_positive_pairs")
        for pair in component[field]
    ]
    orientations = Counter(pair["edge"]["orientation"] for pair in pairs)
    return {
        "source": source,
        "alignment": dict(alignment),
        "documents": len({doc for component in components for doc in component["documents"]}),
        "components": len(components),
        "pairs": len(pairs),
        "orientations": dict(sorted(orientations.items())),
        "fold_components": dict(sorted(Counter(str(component["fold"]) for component in components).items())),
    }


def canonical_cap_components(
    components: Sequence[Mapping[str, Any]], maximum_components: int, target_pairs: int
) -> list[dict[str, Any]]:
    """Apply the parent v2 post-assignment cap without recomputing the assignment."""
    selected = deepcopy(
        sorted(components, key=lambda row: (-int(row["pair_count"]), str(row["component_id"])))[:maximum_components]
    )
    mandatory: set[str] = set()
    remaining: list[tuple[str, str, str]] = []
    for component in selected:
        for field in ("left_positive_pairs", "right_positive_pairs"):
            pairs = component[field]
            if pairs:
                mandatory.add(pairs[0]["pair_id"])
            remaining.extend((pair["pair_id"], component["component_id"], field) for pair in pairs[1:])
    all_count = sum(int(component["pair_count"]) for component in selected)
    if all_count >= target_pairs and len(mandatory) <= target_pairs:
        keep = set(mandatory)
        for pair_id, _, _ in sorted(remaining):
            if len(keep) >= target_pairs:
                break
            keep.add(pair_id)
        for component in selected:
            for field in ("left_positive_pairs", "right_positive_pairs"):
                component[field] = [pair for pair in component[field] if pair["pair_id"] in keep]
            component["pair_count"] = len(component["left_positive_pairs"]) + len(component["right_positive_pairs"])
    totals = [0] * 5
    for component in sorted(selected, key=lambda row: (-int(row["pair_count"]), str(row["component_id"]))):
        fold = min(range(5), key=lambda value: (totals[value], value))
        component["fold"] = fold
        totals[fold] += 1
    return sorted(selected, key=lambda row: str(row["component_id"]))


def _scout_source(args: tuple[Mapping[str, Any], str]) -> tuple[str, dict[str, Any]]:
    config, source = args
    specification = config["sources"][source]
    paths = [ROOT / name for name in specification["analysis_files"]]
    for path in paths:
        relative = path.relative_to(ROOT).as_posix()
        if sha256_file(path) != specification["files"][relative]:
            raise RuntimeError(f"source drift: {path}")
    try:
        tokenizer = AutoTokenizer.from_pretrained(
            config["model"]["name"],
            revision=config["model"]["revision"],
            local_files_only=True,
            use_fast=True,
        )
        loaded = load_sentences(source, paths)
        sentences, alignment = align_sentences(loaded, tokenizer, config["model"]["max_sequence_length"])
        pool = enumerate_by_document(
            sentences,
            config["matching"]["morph_keys"],
            config["matching"]["morph_value_vocabulary"],
            config["matching"]["candidate_cap_per_stratum"],
        )
        uncapped = match_components(
            source,
            pool,
            config["matching"]["max_pairs_per_orientation"],
            max(1, len(pool)),
            2**31 - 1,
        )
        capped = canonical_cap_components(
            uncapped,
            config["matching"]["maximum_components"],
            config["matching"]["target_pairs"],
        )
        uncapped_support = _support(source, uncapped, alignment)
        capped_support = _support(source, capped, alignment)
        capped_support["eligible"] = (
            capped_support["components"] >= config["matching"]["minimum_components"]
            and capped_support["pairs"] >= config["matching"]["minimum_pairs"]
            and all(
                capped_support["orientations"].get(orientation, 0)
                >= config["matching"]["minimum_pairs_per_orientation"]
                for orientation in ("later_query_is_head", "later_query_is_child")
            )
        )
        record = {
            "status": "ELIGIBLE" if capped_support["eligible"] else "INELIGIBLE_SUPPORT",
            "input_sentences": len(loaded),
            "uncapped": uncapped_support,
            "capped": capped_support,
        }
    except Exception as exc:  # fail one source without hiding the pool member
        record = {
            "status": "INELIGIBLE_SOURCE_ERROR",
            "error_type": type(exc).__name__,
            "error": str(exc),
            "capped": {"eligible": False},
        }
    return source, record


def build(config: Mapping[str, Any], output_path: Path) -> dict[str, Any]:
    validation = load_json(ROOT / config["parser_validation"]["path"])
    if sha256_file(ROOT / config["parser_validation"]["path"]) != config["parser_validation"]["sha256"] or not validation["eligible_for_development_forward"]:
        raise RuntimeError("strict parser validation does not authorize prescore")
    if output_path.exists():
        raise RuntimeError("scout output already exists")
    records: dict[str, Any] = {}
    jobs = [(config, source) for source in config["source_selection_order"]]
    with ProcessPoolExecutor(max_workers=int(config["scout_parallel_jobs"])) as executor:
        for source, record in executor.map(_scout_source, jobs):
            records[source] = record
    eligible = [source for source in config["source_selection_order"] if records[source]["capped"].get("eligible", False)]
    selected = eligible[:2]
    report = {
        "schema_version": "relational_objects_v3_label_only_scout_v1",
        "namespace": config["namespace"],
        "config_sha256": sha256_file(ROOT / "configs/relational_objects_v3/scout.json"),
        "parser_validation_sha256": config["parser_validation"]["sha256"],
        "source_selection_order": list(config["source_selection_order"]),
        "eligible_sources": eligible,
        "selected_sources": selected,
        "study_eligible": len(selected) == 2,
        "sources": records,
        "tokenizer": {"name": config["model"]["name"], "revision": config["model"]["revision"]},
        "model_weights_loaded": False,
        "model_forward_run": False,
        "endpoint_scores_computed": False,
        "neural_training_run": False,
    }
    atomic_json(output_path, report)
    return report


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, default=ROOT / "configs/relational_objects_v3/scout.json")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(build(load_json(args.config), args.output), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
