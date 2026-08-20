#!/usr/bin/env python3
"""Build Attempt-13 label-only rows and intervention inputs.

The builder loads a pinned tokenizer but never loads model weights.  It applies
the exposure/overlap firewall before support checks and freezes endpoint-
specific prescore eligibility without looking at activations.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

import networkx as nx
from transformers import AutoTokenizer

sys.path.insert(0, str(Path(__file__).resolve().parent))

from atlas_discovery_v3_3 import (
    DEPREL_MAP,
    UPOS_MAP,
    Sentence,
    Token,
    _main_labels,
    _pick_token_by_hash,
    _proper_noun_quartiles,
    capitalization_label,
    maximum_cardinality_document_matching,
    parse_conllu,
    position_factorial,
    select_sham_heads,
    sentence_content_hash,
    sentence_length_label,
    token_layout,
)
from atlas_relation_context_v9 import (
    CONFIG,
    DATA_ROOT,
    HISTORICAL_ENVELOPE,
    HISTORICAL_PAYLOAD,
    NAMESPACE,
    PREPARED_ROOT,
    ROOT,
    atomic_json,
    atomic_jsonl,
    component_multiplicities,
    read_json,
    sha256_file,
    stable_digest,
    stable_fold,
    stable_hex,
)


SOURCES = ("GENTLE", "CTETEX")
TASKS = ("start_distance", "relative_quartile", "token_identity")
RELATION_TASKS = ("dependency_depth", "deprel_coarse", "head_signed_distance")


def _source_path(config: Mapping[str, Any], source: str) -> Path:
    rel = Path(str(config["sources"][source]["path"]))
    if rel.is_absolute() or ".." in rel.parts:
        raise RuntimeError("source path escapes repository")
    path = (ROOT / rel).resolve(strict=True)
    if not path.is_relative_to(ROOT) or path.is_symlink() or sha256_file(path) != config["sources"][source]["sha256"]:
        raise RuntimeError(f"source lineage drift: {source}")
    return path


def _raw_sentence_signatures(path: Path, tokenizer: Any) -> set[tuple[str, str]]:
    output: set[tuple[str, str]] = set()
    for block in path.read_text(encoding="utf-8").split("\n\n"):
        forms: list[str] = []
        for line in block.splitlines():
            fields = line.split("\t")
            if len(fields) == 10 and fields[0].isdigit():
                forms.append(fields[1])
        if not forms:
            continue
        normalized = " ".join(" ".join(word.lower() for word in forms).split())
        content = hashlib.sha256(normalized.encode("utf-8")).hexdigest()
        encoded = tokenizer(forms, is_split_into_words=True, add_special_tokens=False, truncation=False)
        sequence = hashlib.sha256(json.dumps(list(map(int, encoded["input_ids"])), separators=(",", ":")).encode()).hexdigest()
        output.add((content, sequence))
    return output


def _exposure_and_overlap_firewall(
    parsed: Mapping[str, list[Sentence]], source_paths: Mapping[str, Path], tokenizer: Any
) -> tuple[dict[str, list[Sentence]], dict[str, Any]]:
    historical = read_json(HISTORICAL_PAYLOAD)
    envelope = read_json(HISTORICAL_ENVELOPE)
    if envelope.get("payload_sha256") != sha256_file(HISTORICAL_PAYLOAD):
        raise RuntimeError("historical exposure envelope drift")

    # Every recoverable prior CoNLL-U source is conservative label-dependent
    # overlap material except the two exact technical copies being opened now.
    prior_paths = sorted(
        {
            path.resolve()
            for root in (ROOT / "data", ROOT / "pilot_runs")
            for path in root.rglob("*.conllu")
            if path.resolve() not in set(source_paths.values())
        },
        key=lambda path: str(path).encode("utf-8"),
    )
    prior_signatures: set[tuple[str, str]] = set()
    prior_inventory: list[dict[str, Any]] = []
    for path in prior_paths:
        if path.is_symlink() or not path.is_file():
            raise RuntimeError(f"unreadable/unclassified prior source: {path}")
        signatures = _raw_sentence_signatures(path, tokenizer)
        prior_signatures.update(signatures)
        prior_inventory.append(
            {
                "path": str(path.relative_to(ROOT)),
                "sha256": sha256_file(path),
                "sentence_signatures": len(signatures),
            }
        )

    census_path = ROOT / "reports/provenance/atlas_v3_9_attempt13_collision_census.json"
    census = read_json(census_path)
    if (
        census.get("schema_version") != "atlas_relation_context_v9_attempt13_label_only_collision_census_v1"
        or sha256_file(census_path) != "7b29abf428914e9578dee0032ecab70e657d647f05681994f5d56c623a3f5099"
        or census.get("activation_or_endpoint_result_used") is not False
    ):
        raise RuntimeError("collision census drift")
    removed: dict[str, dict[str, list[str]]] = {}
    retained: dict[str, list[Sentence]] = {}
    for source in SOURCES:
        rows = [row for row in census["collisions"] if row["source"] == source]
        rejected_documents = {
            str(row["document_id"])
            for row in rows
            if row["amended_disposition"] == "remove_whole_document"
        }
        rejected_sentences = {
            str(row["sent_id"])
            for row in rows
            if row["amended_disposition"] == "remove_sentence_from_all_model_input_roles"
        }
        if rejected_documents & {sentence.document_id for sentence in parsed[source] if sentence.sent_id in rejected_sentences}:
            raise RuntimeError("collision disposition overlap")
        retained[source] = [
            sentence
            for sentence in parsed[source]
            if sentence.document_id not in rejected_documents and sentence.sent_id not in rejected_sentences
        ]
        removed[source] = {
            "whole_documents": sorted(rejected_documents),
            "isolated_short_sentences": sorted(rejected_sentences),
            "context_gap_documents": sorted(
                {sentence.document_id for sentence in parsed[source] if sentence.sent_id in rejected_sentences}
            ),
        }
        observed_remaining = len({sentence.document_id for sentence in retained[source]})
        if observed_remaining != int(census["sources"][source]["remaining_documents"]):
            raise RuntimeError(f"collision census remaining-document drift: {source}")

    # Project exposure hits are classified prospectively.  Exact source uses
    # occur only in technical RoPE QA/validation or documentation; any result
    # tree outside the disclosed v8 lineage is fatal.
    hits = list(historical.get("source_alias_hash_hits", []))
    suspicious = [
        hit["path"]
        for hit in hits
        if str(hit["path"]).startswith("results/")
        and not str(hit["path"]).startswith("results/atlas_rope_v8_attempt12_analysis_recovery/")
    ]
    if suspicious:
        raise RuntimeError(f"unclassified prior result exposure: {suspicious[:5]}")
    return retained, {
        "schema_version": "atlas_relation_context_v9_attempt13_exposure_firewall_v1",
        "classification": "endpoint-outcome-naive_with_prior_technical_inference_exposure",
        "historical_payload_sha256": sha256_file(HISTORICAL_PAYLOAD),
        "historical_envelope_sha256": sha256_file(HISTORICAL_ENVELOPE),
        "historical_entries": historical["entry_count"],
        "historical_alias_hits": len(hits),
        "collision_census_path": str(census_path.relative_to(ROOT)),
        "collision_census_sha256": sha256_file(census_path),
        "classified_prior_technical_roots": [
            "data/atlas_rope_v4_attempt8",
            "data/atlas_rope_v5_attempt9",
            "data/atlas_rope_v7_attempt11",
            "pilot_runs/20260803_atlas_rope_technical_v4",
            "pilot_runs/20260803_atlas_rope_technical_v6",
            "pilot_runs/20260803_atlas_rope_technical_v7",
            "results/atlas_rope_v8_attempt12_analysis_recovery (lineage only; science rows are EWT/GUM)",
        ],
        "prior_conllu_inventory": prior_inventory,
        "prior_signature_count": len(prior_signatures),
        "removed_documents": removed,
        "unexplained_hits": [],
        "prior_label_dependent_full_source_score": False,
        "model_inference_performed": False,
    }


def _cap_by_document(rows: Sequence[Mapping[str, Any]], maximum: int, *, salt: str) -> list[dict[str, Any]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for raw in rows:
        grouped[str(raw["document_group"])].append(dict(raw))
    output: list[dict[str, Any]] = []
    for document in sorted(grouped, key=lambda value: value.encode("utf-8")):
        ordered = sorted(
            grouped[document],
            key=lambda row: (stable_digest(NAMESPACE, salt, row.get("row_id", row.get("pair_id"))), str(row).encode()),
        )
        output.extend(ordered[:maximum])
    return output


def _class_support(rows: Sequence[Mapping[str, Any]]) -> dict[str, int]:
    docs: dict[str, set[str]] = defaultdict(set)
    for row in rows:
        docs[str(row["label"])].add(str(row["document_group"]))
    return {label: len(values) for label, values in sorted(docs.items())}


def _bootstrap_finite(
    rows: Sequence[Mapping[str, Any]], classes: Sequence[str], *, endpoint: str, seed: int
) -> int:
    components = sorted({str(row["component_id"]) for row in rows}, key=lambda value: value.encode("utf-8"))
    finite = 0
    for draw in range(500):
        multiplicities = component_multiplicities(components, direction="label-only", endpoint=endpoint, draw=draw, seed=seed)
        if all(
            sum(multiplicities.get(str(row["component_id"]), 0) for row in rows if str(row["label"]) == label) > 0
            for label in classes
        ):
            finite += 1
    return finite


def _ancestors(token_id: int, by_id: Mapping[int, Token]) -> set[int]:
    output: set[int] = set()
    current = token_id
    while current in by_id and by_id[current].head:
        current = by_id[current].head
        if current in output:
            raise RuntimeError("dependency cycle")
        output.add(current)
    return output


def _relation_candidates(
    source: str,
    sentences: Sequence[Sentence],
    layouts: Mapping[str, Mapping[str, Any]],
    row_by_token: Mapping[tuple[str, int], str],
    *,
    seed: int,
    folds: int,
) -> tuple[list[dict[str, Any]], dict[str, list[dict[str, Any]]]]:
    targets: list[dict[str, Any]] = []
    donors: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for sentence in sentences:
        layout = layouts[sentence.sent_id]
        aligned = {token.token_id for token in sentence.tokens if (sentence.sent_id, token.token_id) in row_by_token}
        by_id = {token.token_id: token for token in sentence.tokens}
        positions = {token.token_id: index for index, token in enumerate(sentence.tokens)}
        fold = stable_fold(source, sentence.document_id, seed=seed, folds=folds)
        labels = {
            token.token_id: _main_labels(sentence, token, int(layout["first_positions"][token.token_id]), int(layout["untruncated_length"]))
            for token in sentence.tokens
            if token.token_id in aligned
        }
        for match in select_sham_heads(sentence, aligned_token_ids=aligned, coarse_upos=UPOS_MAP, seed=seed):
            child, head, sham = map(int, (match["child_token_id"], match["head_token_id"], match["sham_token_id"]))
            stratum = (
                fold,
                positions[head] - positions[child],
                int(layout["first_positions"][head]) - int(layout["first_positions"][child]),
                UPOS_MAP[by_id[child].upos],
                UPOS_MAP[by_id[head].upos],
                sentence_length_label(len(layout["input_ids"])),
            )
            targets.append(
                {
                    "target_id": f"{source}:{sentence.sent_id}:{child}",
                    "source": source,
                    "document": sentence.document_id,
                    "fold": fold,
                    "stratum": stratum,
                    "sent_id": sentence.sent_id,
                    "child": child,
                    "head": head,
                    "sham": sham,
                    "child_row_id": row_by_token[(sentence.sent_id, child)],
                    "head_row_id": row_by_token[(sentence.sent_id, head)],
                    "sham_row_id": row_by_token[(sentence.sent_id, sham)],
                    "labels": {task: labels[child][task] for task in RELATION_TASKS},
                }
            )
        for child in sorted(aligned):
            child_ancestors = _ancestors(child, by_id)
            for candidate in sorted(aligned):
                if candidate == child:
                    continue
                if by_id[child].head == candidate or by_id[candidate].head == child:
                    continue
                if candidate in child_ancestors or child in _ancestors(candidate, by_id):
                    continue
                stratum = (
                    fold,
                    positions[candidate] - positions[child],
                    int(layout["first_positions"][candidate]) - int(layout["first_positions"][child]),
                    UPOS_MAP[by_id[child].upos],
                    UPOS_MAP[by_id[candidate].upos],
                    sentence_length_label(len(layout["input_ids"])),
                )
                donors[sentence.document_id].append(
                    {
                        "donor_id": f"{source}:{sentence.sent_id}:{child}:{candidate}",
                        "source": source,
                        "document": sentence.document_id,
                        "fold": fold,
                        "stratum": stratum,
                        "child_row_id": row_by_token[(sentence.sent_id, child)],
                        "candidate_row_id": row_by_token[(sentence.sent_id, candidate)],
                    }
                )
    return targets, donors


def _match_relations(
    source: str, targets: Sequence[Mapping[str, Any]], donors: Mapping[str, Sequence[Mapping[str, Any]]]
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    targets_by_doc: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in targets:
        targets_by_doc[str(row["document"])].append(dict(row))
    donor_strata = {doc: {tuple(row["stratum"]) for row in rows} for doc, rows in donors.items()}
    target_strata = {doc: {tuple(row["stratum"]) for row in rows} for doc, rows in targets_by_doc.items()}
    candidates: list[dict[str, Any]] = []
    documents = sorted(set(targets_by_doc) & set(donors), key=lambda value: value.encode("utf-8"))
    for i, left in enumerate(documents):
        for right in documents[i + 1 :]:
            left_fold = int(targets_by_doc[left][0]["fold"])
            right_fold = int(targets_by_doc[right][0]["fold"])
            if left_fold != right_fold:
                continue
            if not ((target_strata[left] & donor_strata[right]) or (target_strata[right] & donor_strata[left])):
                continue
            candidates.append(
                {
                    "candidate_id": stable_hex(NAMESPACE, "relation-doc-pair", source, left, right),
                    "left_document": f"{source}:{left}",
                    "right_document": f"{source}:{right}",
                    "left_raw": left,
                    "right_raw": right,
                    "fold": left_fold,
                }
            )
    selected, report = maximum_cardinality_document_matching(candidates)
    output: list[dict[str, Any]] = []
    for pair in selected:
        left, right = str(pair["left_raw"]), str(pair["right_raw"])
        component_docs = sorted((f"{source}:{left}", f"{source}:{right}"), key=lambda value: value.encode("utf-8"))
        component = "component:relation:" + stable_hex(*component_docs)[:24]
        for target_doc, donor_doc in ((left, right), (right, left)):
            available: dict[tuple[Any, ...], list[dict[str, Any]]] = defaultdict(list)
            for donor in donors[donor_doc]:
                available[tuple(donor["stratum"])].append(dict(donor))
            for values in available.values():
                values.sort(key=lambda row: stable_digest(NAMESPACE, "relation-donor", row["donor_id"]))
            ordered_targets = sorted(
                targets_by_doc[target_doc], key=lambda row: stable_digest(NAMESPACE, "relation-target", row["target_id"])
            )
            retained = 0
            for target in ordered_targets:
                pool = available.get(tuple(target["stratum"]), [])
                if not pool or retained >= 24:
                    continue
                donor = pool.pop(0)
                row_id = f"{NAMESPACE}:relation:{stable_hex(target['target_id'], donor['donor_id'])[:24]}"
                output.append(
                    {
                        "row_id": row_id,
                        "source": source,
                        "document_group": f"{source}:{target_doc}",
                        "donor_document_group": f"{source}:{donor_doc}",
                        "component_id": component,
                        "component_documents": component_docs,
                        "fold": int(pair["fold"]),
                        "child_row_id": target["child_row_id"],
                        "head_row_id": target["head_row_id"],
                        "sham_row_id": target["sham_row_id"],
                        "donor_child_row_id": donor["child_row_id"],
                        "donor_candidate_row_id": donor["candidate_row_id"],
                        "exact_signed_ud_distance": int(target["stratum"][1]),
                        "exact_signed_subtoken_offset": int(target["stratum"][2]),
                        "child_upos_coarse": target["stratum"][3],
                        "candidate_upos_coarse": target["stratum"][4],
                        "sentence_length_bin": target["stratum"][5],
                        "labels": dict(target["labels"]),
                    }
                )
                retained += 1
    output.sort(key=lambda row: row["row_id"].encode("utf-8"))
    return output, {**report, "rows": len(output), "document_pair_components": len(selected)}


def _add_unit(
    units: list[dict[str, Any]],
    rows: list[dict[str, Any]],
    *,
    source: str,
    unit_id: str,
    kind: str,
    input_ids: Sequence[int],
    position_ids: Sequence[int],
    targets: Sequence[tuple[str, int, str]],
    max_length: int,
) -> None:
    if len(input_ids) != len(position_ids) or len(input_ids) > max_length:
        raise RuntimeError(f"invalid intervention unit: {unit_id}")
    positions: list[int] = []
    row_ids: list[str] = []
    for row_id, position, role in targets:
        if not 0 <= position < len(input_ids):
            raise RuntimeError(f"target outside intervention: {unit_id}")
        positions.append(int(position)); row_ids.append(row_id)
        rows.append({"row_id": row_id, "source": source, "kind": kind, "target_role": role})
    units.append(
        {
            "unit_id": unit_id,
            "source": source,
            "kind": kind,
            "input_ids": list(map(int, input_ids)),
            "position_ids": list(map(int, position_ids)),
            "attention_mask": [1] * len(input_ids),
            "positions": positions,
            "row_ids": row_ids,
        }
    )


def _interventions(
    source: str,
    sentences: Sequence[Sentence],
    layouts: Mapping[str, Mapping[str, Any]],
    tokenizer: Any,
    *,
    seed: int,
    folds: int,
    max_length: int,
    shift: int,
    separator: int,
    context_gap_documents: set[str],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]], dict[str, Any]]:
    units: list[dict[str, Any]] = []; activation_rows: list[dict[str, Any]] = []; pairs: list[dict[str, Any]] = []
    by_document: dict[str, list[Sentence]] = defaultdict(list)
    for sentence in sentences:
        by_document[sentence.document_id].append(sentence)

    # Relative gap: one target/component per document.
    for document, document_sentences in sorted(by_document.items()):
        candidates = [row for row in document_sentences if layouts[row.sent_id]["complete"] and len(layouts[row.sent_id]["input_ids"]) >= 4]
        if not candidates:
            continue
        sentence = min(candidates, key=lambda row: stable_digest(NAMESPACE, "gap-sentence", source, document, row.sent_id))
        layout = layouts[sentence.sent_id]; pivot = len(layout["input_ids"]) // 2
        before = [(token, pos) for token, pos in layout["first_positions"].items() if pos < pivot]
        after = [(token, pos) for token, pos in layout["first_positions"].items() if pos >= pivot]
        if not before or not after:
            continue
        pre_id, pre = min(before, key=lambda value: stable_digest(NAMESPACE, "gap-pre", source, sentence.sent_id, value[0]))
        post_id, post = min(after, key=lambda value: stable_digest(NAMESPACE, "gap-post", source, sentence.sent_id, value[0]))
        variants = position_factorial(
            target_ids=layout["input_ids"], true_prefix_ids=[1], unrelated_prefix_ids=[2], separator_id=separator,
            shift=shift, pivot_token_index=pivot,
        )
        pair_id = stable_hex(NAMESPACE, "gap", source, document)[:24]; row_map: dict[str, dict[str, str]] = {}
        for condition in ("bare", "relative_gap"):
            ids = variants[condition]
            mapped = {role: f"{NAMESPACE}:intervention:{pair_id}:{condition}:{role}" for role in ("pre", "post")}
            _add_unit(units, activation_rows, source=source, unit_id=f"{NAMESPACE}:unit:{pair_id}:{condition}", kind=condition,
                      input_ids=ids["input_ids"], position_ids=ids["position_ids"], targets=((mapped["pre"], pre, "pre"), (mapped["post"], post, "post")), max_length=max_length)
            row_map[condition] = mapped
        token = next(item for item in sentence.tokens if item.token_id == post_id)
        labels = _main_labels(sentence, token, post, int(layout["untruncated_length"]))
        pairs.append({"pair_id": pair_id, "construct": "relative_gap", "source": source,
                      "document_group": f"{source}:{document}", "component_id": f"{source}:{document}",
                      "fold": stable_fold(source, document, seed=seed, folds=folds), "target_metadata": labels, "rows": row_map})

    # True versus unrelated prefix, one disjoint target/donor pair per component.
    context_edges: list[dict[str, Any]] = []
    for document, document_sentences in sorted(by_document.items()):
        if document in context_gap_documents:
            continue
        adjacent = [
            (a, b)
            for a, b in zip(document_sentences, document_sentences[1:])
            if layouts[a.sent_id]["complete"]
            and layouts[b.sent_id]["complete"]
            and len(layouts[b.sent_id]["input_ids"]) >= 2
            and len(layouts[a.sent_id]["input_ids"]) + 1 + len(layouts[b.sent_id]["input_ids"]) <= max_length
        ]
        if not adjacent:
            continue
        previous, target = min(adjacent, key=lambda pair: stable_digest(NAMESPACE, "context-target", source, document, pair[1].sent_id))
        fold = stable_fold(source, document, seed=seed, folds=folds)
        for donor_doc, donor_sentences in sorted(by_document.items()):
            if donor_doc == document or stable_fold(source, donor_doc, seed=seed, folds=folds) != fold:
                continue
            donors = [row for row in donor_sentences if layouts[row.sent_id]["complete"] and len(layouts[row.sent_id]["input_ids"]) == len(layouts[previous.sent_id]["input_ids"]) and sentence_content_hash(row) != sentence_content_hash(previous)]
            if not donors:
                continue
            donor = min(donors, key=lambda row: stable_digest(NAMESPACE, "context-donor", source, document, donor_doc, row.sent_id))
            context_edges.append({"candidate_id": stable_hex(NAMESPACE, "context-edge", source, document, donor_doc, target.sent_id, donor.sent_id),
                                  "left_document": f"{source}:{document}", "right_document": f"{source}:{donor_doc}",
                                  "previous": previous, "target": target, "donor": donor, "fold": fold})
    selected_context, context_report = maximum_cardinality_document_matching(context_edges)
    for edge in selected_context:
        previous, target, donor = edge["previous"], edge["target"], edge["donor"]
        true_layout, target_layout, donor_layout = layouts[previous.sent_id], layouts[target.sent_id], layouts[donor.sent_id]
        eligible = [token.token_id for token in target.tokens if token.token_id in target_layout["first_positions"] and token.upos != "PUNCT"]
        token_id = _pick_token_by_hash(target, eligible, "context", seed)
        if token_id is None:
            continue
        position = int(target_layout["first_positions"][token_id]); prefix_len = len(true_layout["input_ids"]) + 1
        variants = position_factorial(target_ids=target_layout["input_ids"], true_prefix_ids=true_layout["input_ids"],
                                      unrelated_prefix_ids=donor_layout["input_ids"], separator_id=separator, shift=shift,
                                      pivot_token_index=max(1, len(target_layout["input_ids"]) // 2))
        pair_id = stable_hex(NAMESPACE, "context", source, target.document_id, target.sent_id, donor.document_id)[:24]; row_map: dict[str, str] = {}
        for condition in ("separator_only", "true_prefix", "unrelated_prefix"):
            row_id = f"{NAMESPACE}:intervention:{pair_id}:{condition}:target"; spec = variants[condition]
            target_pos = 1 + position if condition == "separator_only" else prefix_len + position
            _add_unit(units, activation_rows, source=source, unit_id=f"{NAMESPACE}:unit:{pair_id}:{condition}", kind=condition,
                      input_ids=spec["input_ids"], position_ids=spec["position_ids"], targets=((row_id, target_pos, "target"),), max_length=max_length)
            row_map[condition] = row_id
        docs = sorted((str(edge["left_document"]), str(edge["right_document"])), key=lambda value: value.encode("utf-8"))
        token = next(item for item in target.tokens if item.token_id == token_id)
        pairs.append({"pair_id": pair_id, "construct": "context_factorial", "source": source,
                      "document_group": f"{source}:{target.document_id}", "donor_document_group": f"{source}:{donor.document_id}",
                      "component_id": "component:context:" + stable_hex(*docs)[:24], "component_documents": docs,
                      "fold": int(edge["fold"]), "target_metadata": _main_labels(target, token, position, int(target_layout["untruncated_length"])), "rows": row_map})

    # Matched proper-noun substitutions, disjoint at the document level.
    quartiles = _proper_noun_quartiles(sentences); propn: list[tuple[Sentence, Token]] = []
    for sentence in sentences:
        layout = layouts[sentence.sent_id]
        if layout["complete"]:
            propn.extend((sentence, token) for token in sentence.tokens if token.upos == "PROPN" and len(layout["token_spans"].get(token.token_id, [])) == 1)
    edges: list[dict[str, Any]] = []
    for source_sentence, source_token in propn:
        source_layout = layouts[source_sentence.sent_id]; fold = stable_fold(source, source_sentence.document_id, seed=seed, folds=folds)
        control_ids = [token.token_id for token in source_sentence.tokens if token.token_id in source_layout["first_positions"] and token.token_id != source_token.token_id and token.upos != "PUNCT"]
        control_id = _pick_token_by_hash(source_sentence, control_ids, "proper-control", seed)
        if control_id is None:
            continue
        source_pos = int(source_layout["first_positions"][source_token.token_id]); words = [token.form for token in source_sentence.tokens]
        word_index = next(index for index, token in enumerate(source_sentence.tokens) if token.token_id == source_token.token_id)
        for donor_sentence, donor_token in propn:
            if donor_sentence.document_id == source_sentence.document_id or stable_fold(source, donor_sentence.document_id, seed=seed, folds=folds) != fold:
                continue
            if donor_token.form.lower() == source_token.form.lower() or capitalization_label(donor_token.form) != capitalization_label(source_token.form):
                continue
            if donor_token.feats.get("Number", "NONE") != source_token.feats.get("Number", "NONE") or quartiles[donor_token.form.lower()] != quartiles[source_token.form.lower()]:
                continue
            replacement = list(words); replacement[word_index] = donor_token.form
            encoded = tokenizer(replacement, is_split_into_words=True, add_special_tokens=False, truncation=False)
            ids = list(map(int, encoded["input_ids"])); word_ids = list(encoded.word_ids())
            if len(ids) != len(source_layout["input_ids"]) or word_ids != source_layout["word_ids"]:
                continue
            changed = [index for index, (a, b) in enumerate(zip(source_layout["input_ids"], ids)) if a != b]
            if changed != [source_pos]:
                continue
            edges.append({"candidate_id": stable_hex(NAMESPACE, "proper-edge", source, source_sentence.document_id, source_sentence.sent_id, source_token.token_id, donor_sentence.document_id, donor_token.token_id),
                          "left_document": f"{source}:{source_sentence.document_id}", "right_document": f"{source}:{donor_sentence.document_id}",
                          "source_sentence": source_sentence, "source_token": source_token, "donor_sentence": donor_sentence, "donor_token": donor_token,
                          "source_ids": source_layout["input_ids"], "target_ids": ids, "changed_position": source_pos,
                          "control_id": int(control_id), "fold": fold})
    selected_proper, proper_report = maximum_cardinality_document_matching(edges)
    for edge in selected_proper:
        sentence, token, donor_sentence, donor_token = edge["source_sentence"], edge["source_token"], edge["donor_sentence"], edge["donor_token"]
        layout = layouts[sentence.sent_id]; changed = int(edge["changed_position"]); control = int(layout["first_positions"][edge["control_id"]])
        pair_id = stable_hex(NAMESPACE, "proper", source, sentence.document_id, sentence.sent_id, token.token_id, donor_sentence.document_id)[:24]; row_map: dict[str, dict[str, str]] = {}
        for condition, ids in (("source", edge["source_ids"]), ("target", edge["target_ids"])):
            changed_row = f"{NAMESPACE}:intervention:{pair_id}:{condition}:changed"; control_row = f"{NAMESPACE}:intervention:{pair_id}:{condition}:control"
            _add_unit(units, activation_rows, source=source, unit_id=f"{NAMESPACE}:unit:{pair_id}:{condition}", kind=f"proper_noun_{condition}",
                      input_ids=ids, position_ids=list(range(len(ids))), targets=((changed_row, changed, "changed"), (control_row, control, "control")), max_length=max_length)
            row_map[condition] = {"changed": changed_row, "control": control_row}
        docs = sorted((str(edge["left_document"]), str(edge["right_document"])), key=lambda value: value.encode("utf-8"))
        pairs.append({"pair_id": pair_id, "construct": "proper_noun_substitution", "source": source,
                      "document_group": f"{source}:{sentence.document_id}", "donor_document_group": f"{source}:{donor_sentence.document_id}",
                      "component_id": "component:proper:" + stable_hex(*docs)[:24], "component_documents": docs, "fold": int(edge["fold"]),
                      "source_form": token.form, "donor_form": donor_token.form,
                      "target_metadata": _main_labels(sentence, token, changed, int(layout["untruncated_length"])), "rows": row_map})
    return units, activation_rows, pairs, {"context_matching": context_report, "proper_matching": proper_report}


def _support_interventions(pairs: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    output: dict[str, Any] = {}
    for construct in ("relative_gap", "context_factorial", "proper_noun_substitution"):
        selected = [row for row in pairs if row["construct"] == construct]
        targets = {str(row["document_group"]) for row in selected}
        donors = {str(row["donor_document_group"]) for row in selected if row.get("donor_document_group")}
        components = {str(row["component_id"]) for row in selected}
        if construct == "relative_gap":
            eligible = len(targets) >= 20 and len(components) >= 20
        else:
            all_docs = targets | donors
            eligible = len(targets) >= 12 and len(donors) >= 12 and len(components) >= 12 and len(all_docs) >= 24
        output[construct] = {"pairs": len(selected), "target_documents": len(targets), "donor_documents": len(donors) if donors else "not_applicable",
                             "components": len(components), "eligible": eligible}
    return output


def build(config_path: Path) -> dict[str, Any]:
    config = read_json(config_path)
    if config.get("schema_version") != "atlas_relation_context_v9_attempt13_run_v1" or config.get("neural_training_authorized") is not False:
        raise RuntimeError("unexpected Attempt-13 config")
    if DATA_ROOT.exists():
        manifest_path = PREPARED_ROOT / "manifest.json"
        if manifest_path.exists() and read_json(manifest_path).get("config_sha256") == sha256_file(config_path):
            return read_json(manifest_path)
        raise RuntimeError("Attempt-13 data namespace already exists")
    source_paths = {source: _source_path(config, source) for source in SOURCES}
    tokenizer = AutoTokenizer.from_pretrained(config["model"]["name"], revision=config["model"]["revision"], local_files_only=True)
    parsed = {source: parse_conllu(path, source) for source, path in source_paths.items()}
    raw_document_counts = {source: len({row.document_id for row in rows}) for source, rows in parsed.items()}
    if raw_document_counts != {"GENTLE": 26, "CTETEX": 196}:
        raise RuntimeError(f"genuine document count drift: {raw_document_counts}")
    parsed, firewall = _exposure_and_overlap_firewall(parsed, source_paths, tokenizer)
    atomic_json(DATA_ROOT / "exposure_firewall.json", firewall)

    seed = int(config["seed"]); folds = int(config["data"]["folds"]); max_length = int(config["data"]["max_length"])
    source_state: dict[str, Any] = {}; task_candidates: dict[str, dict[str, list[dict[str, Any]]]] = {}
    for source in SOURCES:
        sentences = parsed[source]; documents = {row.document_id for row in sentences}
        layouts = {row.sent_id: token_layout(tokenizer, row, max_length) for row in sentences}
        if len(documents) < 20:
            raise RuntimeError(f"source support below 20 after overlap firewall: {source}")
        units: list[dict[str, Any]] = []; activation_rows: list[dict[str, Any]] = []; row_by_token: dict[tuple[str, int], str] = {}
        candidates = {task: [] for task in TASKS}
        for sentence in sentences:
            layout = layouts[sentence.sent_id]
            if not layout["complete"]:
                continue
            positions: list[int] = []; row_ids: list[str] = []
            for token in sentence.tokens:
                if token.token_id not in layout["first_positions"]:
                    continue
                position = int(layout["first_positions"][token.token_id]); row_id = f"{NAMESPACE}:main:{source}:{sentence.sent_id}:{token.token_id}"
                labels = _main_labels(sentence, token, position, int(layout["untruncated_length"])); labels["token_identity"] = token.form.lower()
                document_group = f"{source}:{sentence.document_id}"
                activation_rows.append({"row_id": row_id, "source": source, "kind": "main", "document_group": document_group,
                                        "component_id": document_group, "fold": stable_fold(source, sentence.document_id, seed=seed, folds=folds),
                                        "sent_id": sentence.sent_id, "token_id": token.token_id, "token_position": position, "labels": labels})
                row_by_token[(sentence.sent_id, token.token_id)] = row_id; positions.append(position); row_ids.append(row_id)
                for task in TASKS:
                    candidates[task].append({"row_id": row_id, "label": labels[task], "document_group": document_group, "component_id": document_group})
            if row_ids:
                units.append({"unit_id": f"{NAMESPACE}:main:{source}:{sentence.sent_id}", "source": source, "kind": "main",
                              "input_ids": layout["input_ids"], "position_ids": list(range(len(layout["input_ids"]))), "attention_mask": [1] * len(layout["input_ids"]),
                              "positions": positions, "row_ids": row_ids})
        relation_targets, relation_donors = _relation_candidates(source, sentences, layouts, row_by_token, seed=seed, folds=folds)
        relations, relation_report = _match_relations(source, relation_targets, relation_donors)
        intervention_units, intervention_rows, pairs, matching = _interventions(
            source, sentences, layouts, tokenizer, seed=seed, folds=folds, max_length=max_length,
            shift=int(config["interventions"]["position_shift"]), separator=int(config["data"]["separator_token_id"]),
            context_gap_documents=set(firewall["removed_documents"][source]["context_gap_documents"]),
        )
        excluded_sequences = [
            list(map(int, row["signature"]["selected_subtoken_ids"]))
            for row in read_json(ROOT / "reports/provenance/atlas_v3_9_attempt13_collision_census.json")["collisions"]
            if row["source"] == source
        ]
        for unit in units + intervention_units:
            ids = list(map(int, unit["input_ids"]))
            for excluded in excluded_sequences:
                if excluded and any(ids[index : index + len(excluded)] == excluded for index in range(len(ids) - len(excluded) + 1)):
                    raise RuntimeError(f"excluded collision sequence leaked into prepared input: {source}/{unit['unit_id']}")
        source_state[source] = {"sentences": sentences, "documents": documents, "units": units + intervention_units,
                                "activation_rows": activation_rows + intervention_rows, "relations": relations, "pairs": pairs,
                                "relation_report": relation_report, "matching": matching}
        task_candidates[source] = candidates

    # Freeze shared transfer classes by document frequency in both sources.
    retained_classes: dict[str, list[str]] = {}
    for task in TASKS:
        common: set[str] | None = None
        for source in SOURCES:
            support = _class_support(task_candidates[source][task])
            eligible = {label for label, count in support.items() if count >= 10 and label != "__DROP__"}
            common = eligible if common is None else common & eligible
        retained_classes[task] = sorted(common or set(), key=lambda value: value.encode("utf-8"))

    manifest: dict[str, Any] = {
        "schema_version": "atlas_relation_context_v9_attempt13_prepared_v1", "status": "PRESCORE_COMPLETE",
        "config_sha256": sha256_file(config_path), "historical_payload_sha256": sha256_file(HISTORICAL_PAYLOAD),
        "exposure_firewall_sha256": sha256_file(DATA_ROOT / "exposure_firewall.json"), "raw_document_counts": raw_document_counts,
        "post_overlap_document_counts": {source: len(source_state[source]["documents"]) for source in SOURCES},
        "retained_task_classes": retained_classes, "sources": {}, "model_inference_performed": False, "neural_training_performed": False,
    }
    module_prescore: dict[str, dict[str, bool]] = {}
    for source in SOURCES:
        state = source_state[source]; root = PREPARED_ROOT / source
        units_sha, units_n = atomic_jsonl(root / "inference_units.jsonl", state["units"])
        rows_sha, rows_n = atomic_jsonl(root / "activation_rows.jsonl", state["activation_rows"])
        relation_sha, relation_n = atomic_jsonl(root / "relation_rows.jsonl", state["relations"])
        pairs_sha, pairs_n = atomic_jsonl(root / "intervention_pairs.jsonl", state["pairs"])
        task_manifest: dict[str, Any] = {}; support_manifest: dict[str, Any] = {}
        for task in TASKS:
            classes = retained_classes[task]
            selected = [row for row in task_candidates[source][task] if str(row["label"]) in classes]
            selected = _cap_by_document(selected, 24, salt=f"task-{task}")
            class_docs = _class_support(selected); finite = _bootstrap_finite(selected, classes, endpoint=f"task:{task}:{source}", seed=seed) if len(classes) >= 2 else 0
            eligible = len(classes) >= 2 and len({row["document_group"] for row in selected}) >= 20 and all(class_docs.get(label, 0) >= 10 for label in classes) and finite >= 490
            task_sha, task_n = atomic_jsonl(root / "tasks" / f"{task}.jsonl", selected)
            task_manifest[task] = {"sha256": task_sha, "rows": task_n}; support_manifest[task] = {"classes": classes, "class_documents": class_docs, "documents": len({row["document_group"] for row in selected}), "finite_bootstrap_draws": finite, "eligible": eligible}
        relation_support: dict[str, Any] = {
            "target_documents": len({row["document_group"] for row in state["relations"]}),
            "donor_documents": len({row["donor_document_group"] for row in state["relations"]}),
            "components": len({row["component_id"] for row in state["relations"]}),
            "matching": state["relation_report"], "tasks": {},
        }
        base_relation_ok = relation_support["target_documents"] >= 20 and relation_support["donor_documents"] >= 20 and relation_support["components"] >= 10
        for task in RELATION_TASKS:
            raw = [{"label": row["labels"][task], "document_group": row["document_group"], "component_id": row["component_id"]} for row in state["relations"]]
            common_classes: set[str] | None = None
            for other in SOURCES:
                other_raw = [{"label": row["labels"][task], "document_group": row["document_group"], "component_id": row["component_id"]} for row in source_state[other]["relations"]]
                eligible_classes = {label for label, count in _class_support(other_raw).items() if count >= 10}
                common_classes = eligible_classes if common_classes is None else common_classes & eligible_classes
            classes = sorted(common_classes or set(), key=lambda value: value.encode("utf-8"))
            selected = [row for row in raw if row["label"] in classes]; docs = _class_support(selected)
            finite = _bootstrap_finite(selected, classes, endpoint=f"relation:{task}:{source}", seed=seed) if len(classes) >= 2 else 0
            cv_training_complete = len(classes) >= 2 and all(
                {
                    str(row["labels"][task])
                    for row in state["relations"]
                    if str(row["labels"][task]) in classes and int(row["fold"]) != fold
                }
                == set(classes)
                for fold in range(folds)
            )
            relation_support["tasks"][task] = {"classes": classes, "class_documents": docs, "finite_component_bootstrap_draws": finite,
                                                        "cv_training_classes_complete": cv_training_complete,
                                                        "eligible": base_relation_ok and len(classes) >= 2 and all(docs.get(label, 0) >= 10 for label in classes) and finite >= 490 and cv_training_complete}
        relation_support["prescore_eligible"] = base_relation_ok and all(row["eligible"] for row in relation_support["tasks"].values())
        intervention_support = _support_interventions(state["pairs"])
        secondary_prescore = all(row["eligible"] for row in support_manifest.values()) and all(row["eligible"] for row in intervention_support.values())
        source_eligible = relation_support["prescore_eligible"] or secondary_prescore
        module_prescore[source] = {"relation": bool(relation_support["prescore_eligible"]), "secondary": bool(secondary_prescore)}
        manifest["sources"][source] = {
            "source_sha256": config["sources"][source]["sha256"], "documents": len(state["documents"]), "units": units_n, "activation_rows": rows_n,
            "relation_rows": relation_n, "intervention_pairs": pairs_n, "units_sha256": units_sha, "activation_rows_sha256": rows_sha,
            "relation_rows_sha256": relation_sha, "intervention_pairs_sha256": pairs_sha, "tasks": task_manifest, "task_support": support_manifest,
            "relation_support": relation_support, "intervention_support": intervention_support, "secondary_prescore_eligible": secondary_prescore,
            "any_module_prescore_eligible": source_eligible, "matching": state["matching"],
        }
    all_eligible = all(module_prescore[source]["relation"] for source in SOURCES) or all(
        module_prescore[source]["secondary"] for source in SOURCES
    )
    manifest["module_prescore"] = module_prescore
    manifest["authorization_eligible"] = all_eligible
    atomic_json(PREPARED_ROOT / "manifest.json", manifest)
    atomic_json(DATA_ROOT / "preflight.json", {"schema_version": "atlas_relation_context_v9_attempt13_preflight_v1",
                                                "status": "PASS" if all_eligible else "STOP_PRESCORE_INELIGIBLE",
                                                "manifest_sha256": sha256_file(PREPARED_ROOT / "manifest.json"),
                                                "endpoint_specific": {source: {"relation": manifest["sources"][source]["relation_support"]["prescore_eligible"],
                                                                                       "secondary": manifest["sources"][source]["secondary_prescore_eligible"]} for source in SOURCES},
                                                "model_inference_performed": False, "neural_training_performed": False})
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser(); parser.add_argument("--config", default=str(CONFIG.relative_to(ROOT))); args = parser.parse_args()
    manifest = build((ROOT / args.config).resolve())
    print(json.dumps({"manifest": str((PREPARED_ROOT / 'manifest.json').relative_to(ROOT)), "sha256": sha256_file(PREPARED_ROOT / "manifest.json"),
                      "authorization_eligible": manifest["authorization_eligible"], "sources": manifest["sources"]}, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
