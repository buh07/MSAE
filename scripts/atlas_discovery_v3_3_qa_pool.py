#!/usr/bin/env python3
"""Deterministic utilities for the Atlas v3 discovery-only factor study.

This module deliberately contains no model training.  Data builders, fixed probes,
projection comparators, and report logic are separated so their contracts can be
tested without a GPU.
"""

from __future__ import annotations

import hashlib
import json
import math
import os
import platform
import subprocess
import sys
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Mapping, MutableMapping, Sequence

import numpy as np


NAMESPACE = "atlas_discovery_v3_3_attempt7_qa_pool"
DROP = "__DROP__"
NONRETAINED = "__NONRETAINED__"
UNKNOWN = "__UNKNOWN__"

UPOS_MAP = {
    "NOUN": "NOMINAL",
    "PROPN": "NOMINAL",
    "PRON": "NOMINAL",
    "VERB": "VERBAL",
    "AUX": "VERBAL",
    "ADJ": "MODIFIER",
    "ADV": "MODIFIER",
    "ADP": "FUNCTION",
    "CCONJ": "FUNCTION",
    "SCONJ": "FUNCTION",
    "DET": "FUNCTION",
    "PART": "FUNCTION",
    "NUM": "QUANTITY",
    "PUNCT": "PUNCT",
    "INTJ": "OTHER",
    "SYM": "OTHER",
    "X": "OTHER",
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
    "root": "root",
    "punct": "punct",
}

PRIMARY_TOKEN_VOCABULARY = (
    "a",
    "and",
    "but",
    "for",
    "in",
    "is",
    "it",
    "of",
    "on",
    "or",
    "that",
    "the",
    "to",
    "was",
    "with",
)

MAIN_TASKS = (
    "start_distance",
    "relative_quartile",
    "head_signed_distance",
    "dependency_depth",
    "deprel_coarse",
    "token_identity",
    "number",
    "upos_coarse",
    "capitalization",
    "word_length",
    "punctuation",
)


@dataclass(frozen=True)
class Token:
    token_id: int
    form: str
    lemma: str
    upos: str
    feats: Mapping[str, str]
    head: int
    deprel: str


@dataclass(frozen=True)
class Sentence:
    source: str
    document_id: str
    paragraph_id: str | None
    sent_id: str
    text: str | None
    tokens: tuple[Token, ...]


def canonical_json_bytes(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def stable_digest(*parts: object) -> bytes:
    return hashlib.sha256("|".join(map(str, parts)).encode("utf-8")).digest()


def stable_hex(*parts: object) -> str:
    return hashlib.sha256("|".join(map(str, parts)).encode("utf-8")).hexdigest()


def stable_fold(source: str, document_id: str, *, seed: int, folds: int) -> int:
    if folds <= 1:
        raise ValueError("folds must exceed one")
    raw = stable_digest(NAMESPACE, "fold", seed, source, document_id)
    return int.from_bytes(raw[:8], "big") % folds


def label_blind_cap(
    rows: Sequence[Mapping[str, Any]], maximum: int, *, seed: int
) -> list[dict[str, Any]]:
    if maximum < 0:
        raise ValueError("maximum must be nonnegative")
    seen: set[str] = set()
    materialized: list[dict[str, Any]] = []
    for raw in rows:
        row = dict(raw)
        row_id = str(row.get("row_id", ""))
        if not row_id or row_id in seen:
            raise RuntimeError(f"missing/duplicate row_id: {row_id!r}")
        seen.add(row_id)
        materialized.append(row)
    materialized.sort(
        key=lambda row: (
            stable_digest(NAMESPACE, "row-cap", seed, row["row_id"]),
            str(row["row_id"]).encode("utf-8"),
        )
    )
    return materialized[:maximum]


def bootstrap_component_multiplicities(
    components: Sequence[str],
    *,
    direction: str,
    endpoint: str,
    draw: int,
    seed: int,
) -> dict[str, int]:
    ordered = sorted(set(map(str, components)), key=lambda value: value.encode("utf-8"))
    if len(ordered) != len(components):
        raise RuntimeError("bootstrap components must be unique")
    if not ordered:
        return {}
    output: Counter[str] = Counter()
    for slot in range(len(ordered)):
        raw = stable_digest(NAMESPACE, "bootstrap", seed, direction, endpoint, draw, slot)
        output[ordered[int.from_bytes(raw[:8], "big") % len(ordered)]] += 1
    return dict(output)


def maximum_cardinality_document_matching(
    candidates: Sequence[Mapping[str, Any]],
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Select a deterministic maximum-cardinality set of disjoint document pairs."""

    import networkx as nx

    canonical: dict[tuple[str, str], dict[str, Any]] = {}
    for raw in candidates:
        row = dict(raw)
        candidate_id = str(row.get("candidate_id", ""))
        left = str(row.get("left_document", ""))
        right = str(row.get("right_document", ""))
        if not candidate_id or not left or not right or left == right:
            raise RuntimeError("invalid matching candidate")
        pair = tuple(sorted((left, right), key=lambda value: value.encode("utf-8")))
        current = canonical.get(pair)
        if current is None or candidate_id.encode("utf-8") < str(current["candidate_id"]).encode("utf-8"):
            canonical[pair] = row
    ordered = sorted(
        canonical.items(),
        key=lambda item: (
            str(item[1]["candidate_id"]).encode("utf-8"),
            item[0][0].encode("utf-8"),
            item[0][1].encode("utf-8"),
        ),
    )
    graph = nx.Graph()
    nodes = sorted(
        {document for pair, _ in ordered for document in pair},
        key=lambda value: value.encode("utf-8"),
    )
    graph.add_nodes_from(nodes)
    total = len(ordered)
    for rank, (pair, row) in enumerate(ordered):
        graph.add_edge(pair[0], pair[1], weight=total - rank, candidate=row)
    matched_edges = nx.algorithms.matching.max_weight_matching(
        graph, maxcardinality=True, weight="weight"
    )
    selected = [dict(graph.get_edge_data(left, right)["candidate"]) for left, right in matched_edges]
    selected.sort(key=lambda row: str(row["candidate_id"]).encode("utf-8"))
    used = [
        str(row[key])
        for row in selected
        for key in ("left_document", "right_document")
    ]
    if len(used) != len(set(used)):
        raise RuntimeError("maximum matching reused a document across roles")
    maximum = len(matched_edges)
    report: dict[str, Any] = {
        "candidate_edges": len(ordered),
        "eligible_documents": len(nodes),
        "cardinality_upper_bound": len(nodes) // 2,
        "maximum_cardinality": maximum,
        "achieved_cardinality": len(selected),
    }
    if all("fold" in row for _, row in ordered):
        selected_by_fold = Counter(str(row["fold"]) for row in selected)
        report["maximum_cardinality_by_fold"] = dict(sorted(selected_by_fold.items()))
        report["achieved_cardinality_by_fold"] = dict(sorted(selected_by_fold.items()))
    return selected, report


def pooled_document_row_weights(
    rows: Sequence[Mapping[str, Any]], multiplicities: Mapping[str, int]
) -> np.ndarray:
    """Node-bootstrap weights for singleton and donor-linked held-out rows."""

    output: list[float] = []
    for row in rows:
        target = str(row["document_group"])
        weight = int(multiplicities.get(target, 0))
        donor = row.get("donor_document_group")
        if donor is not None:
            donor_text = str(donor)
            if donor_text == target:
                raise RuntimeError("donor-linked row has identical target and donor")
            weight *= int(multiplicities.get(donor_text, 0))
        output.append(float(weight))
    return np.asarray(output, dtype=np.float64)


def build_joint_cross_family_rows(
    intervention_pairs: Sequence[Mapping[str, Any]],
    *,
    source: str,
    seed: int,
    allowed_joint_cells: set[str] | None = None,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Freeze the balanced label-only four-class specificity population."""

    classes = (
        "proper_noun_substitution",
        "relative_gap",
        "true_context",
        "unrelated_context",
    )
    candidates: list[dict[str, Any]] = []
    for raw in intervention_pairs:
        row = dict(raw)
        metadata = row.get("target_metadata")
        if not isinstance(metadata, Mapping):
            continue
        stratum = {
            key: str(metadata[key])
            for key in ("start_distance", "upos_coarse", "capitalization", "word_length")
        }
        base = {
            "source": source,
            "document_group": str(row["document_group"]),
            "fold": int(row["fold"]),
            "stratum": stratum,
            "sentence_length": str(metadata["sentence_length"]),
            "source_document_length": int(row.get("source_document_length", 0)),
        }
        if "donor_document_group" in row:
            base["donor_document_group"] = str(row["donor_document_group"])
        construct = str(row["construct"])
        if construct == "relative_gap":
            candidates.append(
                {
                    **base,
                    "joint_row_id": f"{NAMESPACE}:joint:{source}:relative_gap:{row['pair_id']}",
                    "class_label": "relative_gap",
                    "pair_id": row["pair_id"],
                    "delta_rows": {
                        "reference": row["rows"]["bare"]["post"],
                        "candidate": row["rows"]["relative_gap"]["post"],
                    },
                }
            )
        elif construct == "context_factorial":
            for class_label, reference, candidate in (
                ("unrelated_context", "separator_only", "unrelated_prefix"),
                ("true_context", "unrelated_prefix", "true_prefix"),
            ):
                candidates.append(
                    {
                        **base,
                        "joint_row_id": f"{NAMESPACE}:joint:{source}:{class_label}:{row['pair_id']}",
                        "class_label": class_label,
                        "pair_id": row["pair_id"],
                        "delta_rows": {
                            "reference": row["rows"][reference],
                            "candidate": row["rows"][candidate],
                        },
                    }
                )
        elif construct == "proper_noun_substitution":
            candidates.append(
                {
                    **base,
                    "joint_row_id": f"{NAMESPACE}:joint:{source}:proper_noun_substitution:{row['pair_id']}",
                    "class_label": "proper_noun_substitution",
                    "pair_id": row["pair_id"],
                    "delta_rows": {
                        "reference": row["rows"]["source"]["changed"],
                        "candidate": row["rows"]["target"]["changed"],
                        "control_reference": row["rows"]["source"]["control"],
                        "control_candidate": row["rows"]["target"]["control"],
                    },
                }
            )
    raw_candidate_counts = Counter(str(row["class_label"]) for row in candidates)
    if allowed_joint_cells is not None:
        candidates = [
            row
            for row in candidates
            if "|".join(
                row["stratum"][field]
                for field in ("start_distance", "upos_coarse", "capitalization", "word_length")
            )
            in allowed_joint_cells
        ]
    by_fold_class: dict[int, dict[str, list[dict[str, Any]]]] = defaultdict(
        lambda: defaultdict(list)
    )
    for row in candidates:
        by_fold_class[int(row["fold"])][row["class_label"]].append(row)
    retained: list[dict[str, Any]] = []
    balanced_folds = 0
    for fold in sorted(by_fold_class):
        by_class = by_fold_class[fold]
        if any(class_label not in by_class for class_label in classes):
            continue
        count = min(len(by_class[class_label]) for class_label in classes)
        if count <= 0:
            continue
        balanced_folds += 1
        for class_label in classes:
            ordered = sorted(
                by_class[class_label],
                key=lambda row: (
                    stable_digest(
                        NAMESPACE,
                        "joint-cap",
                        seed,
                        source,
                        fold,
                        class_label,
                        row["joint_row_id"],
                    ),
                    str(row["joint_row_id"]).encode("utf-8"),
                ),
            )
            retained.extend(ordered[:count])
    retained.sort(key=lambda row: str(row["joint_row_id"]).encode("utf-8"))
    candidate_counts = Counter(str(row["class_label"]) for row in candidates)
    retained_counts = Counter(str(row["class_label"]) for row in retained)
    candidate_cells = {
        label: Counter(
            "|".join(row["stratum"][field] for field in ("start_distance", "upos_coarse", "capitalization", "word_length"))
            for row in candidates
            if row["class_label"] == label
        )
        for label in classes
    }
    retained_cells = {
        label: Counter(
            "|".join(row["stratum"][field] for field in ("start_distance", "upos_coarse", "capitalization", "word_length"))
            for row in retained
            if row["class_label"] == label
        )
        for label in classes
    }
    return retained, {
        "classes": list(classes),
        "raw_candidate_by_class": {
            label: raw_candidate_counts.get(label, 0) for label in classes
        },
        "candidate_by_class": {label: candidate_counts.get(label, 0) for label in classes},
        "source_common_excluded_by_class": {
            label: raw_candidate_counts.get(label, 0) - candidate_counts.get(label, 0)
            for label in classes
        },
        "retained_by_class": {label: retained_counts.get(label, 0) for label in classes},
        "excluded_by_class": {
            label: candidate_counts.get(label, 0) - retained_counts.get(label, 0)
            for label in classes
        },
        "balanced_folds": balanced_folds,
        "candidate_joint_cells_by_class": {
            label: dict(sorted(candidate_cells[label].items())) for label in classes
        },
        "retained_joint_cells_by_class": {
            label: dict(sorted(retained_cells[label].items())) for label in classes
        },
    }


def joint_cross_family_support_report(
    rows: Sequence[Mapping[str, Any]],
    population_report: Mapping[str, Any],
    *,
    source: str,
    seed: int,
    thresholds: Mapping[str, Any],
    bootstrap_draws: int,
    minimum_finite_draws: int,
) -> dict[str, Any]:
    classes = tuple(map(str, population_report["classes"]))
    by_class = {label: [row for row in rows if row["class_label"] == label] for label in classes}
    target_documents = {
        label: {str(row["document_group"]) for row in selected}
        for label, selected in by_class.items()
    }
    involved_documents = {
        label: {
            document
            for row in selected
            for document in (
                str(row["document_group"]),
                *(
                    (str(row["donor_document_group"]),)
                    if row.get("donor_document_group") is not None
                    else ()
                ),
            )
        }
        for label, selected in by_class.items()
    }
    by_fold = {
        label: Counter(int(row["fold"]) for row in selected)
        for label, selected in by_class.items()
    }
    all_documents = sorted(
        {document for values in involved_documents.values() for document in values},
        key=lambda value: value.encode("utf-8"),
    )
    finite = 0
    for draw in range(bootstrap_draws):
        multiplicities = bootstrap_component_multiplicities(
            all_documents,
            direction=f"support:{source}",
            endpoint="cross_family_specificity",
            draw=draw,
            seed=seed,
        )
        covered = {
            label: float(pooled_document_row_weights(selected, multiplicities).sum()) > 0
            for label, selected in by_class.items()
        }
        if all(covered.values()):
            finite += 1
    reasons: list[str] = []
    if any(len(selected) < int(thresholds["min_rows_per_class"]) for selected in by_class.values()):
        reasons.append("rows_per_class_below_minimum")
    if any(
        len(target_documents[label]) < int(thresholds["min_target_documents_per_class"])
        for label in classes
    ):
        reasons.append("target_documents_per_class_below_minimum")
    folds = range(int(thresholds["folds"]))
    if any(
        by_fold[label].get(fold, 0) < int(thresholds["min_rows_per_class_per_fold"])
        for label in classes
        for fold in folds
    ):
        reasons.append("rows_per_class_per_fold_below_minimum")
    if finite < minimum_finite_draws:
        reasons.append("pooled_bootstrap_finite_below_minimum")
    return {
        **dict(population_report),
        "status": "eligible" if not reasons else "ineligible",
        "reasons": reasons,
        "target_documents_by_class": {
            label: len(target_documents[label]) for label in classes
        },
        "involved_documents_by_class": {
            label: len(involved_documents[label]) for label in classes
        },
        "rows_by_class_by_fold": {
            label: {str(fold): by_fold[label].get(fold, 0) for fold in folds}
            for label in classes
        },
        "shared_node_bootstrap": {
            "documents": len(all_documents),
            "draws": bootstrap_draws,
            "finite_draws": finite,
            "minimum_finite_draws": minimum_finite_draws,
            "donor_linked_weight": "target_multiplicity_times_donor_multiplicity",
        },
    }


def _parse_feats(raw: str) -> dict[str, str]:
    if raw == "_":
        return {}
    output: dict[str, str] = {}
    for item in raw.split("|"):
        if "=" not in item:
            raise RuntimeError(f"malformed FEATS item: {item!r}")
        key, value = item.split("=", 1)
        if not key or key in output:
            raise RuntimeError(f"duplicate/empty FEATS key: {key!r}")
        output[key] = value
    return output


def parse_conllu(
    path: Path, source: str, *, exclusion_counts: dict[str, int] | None = None
) -> list[Sentence]:
    """Parse a source-pure CoNLL-U file and fail closed on grouping drift."""

    current_document: str | None = None
    current_paragraph: str | None = None
    seen_documents: set[str] = set()
    seen_sentences: set[str] = set()
    comments: dict[str, str] = {}
    token_rows: list[list[str]] = []
    output: list[Sentence] = []

    def flush() -> None:
        nonlocal comments, token_rows
        if not token_rows:
            comments = {}
            return
        if current_document is None:
            raise RuntimeError("sentence before newdoc id")
        sent_id = comments.get("sent_id", "")
        if not sent_id or sent_id in seen_sentences:
            raise RuntimeError(f"missing/duplicate sent_id: {sent_id!r}")
        seen_sentences.add(sent_id)
        ids = [int(row[0]) for row in token_rows]
        if len(ids) != len(set(ids)):
            raise RuntimeError(f"duplicate token ID in {sent_id}")
        id_set = set(ids)
        tokens: list[Token] = []
        for row in token_rows:
            head = int(row[6]) if row[6].isdigit() else -1
            if head < 0 or (head != 0 and head not in id_set):
                raise RuntimeError(f"malformed head in {sent_id}: {row[6]!r}")
            deprel = row[7].split(":", 1)[0]
            tokens.append(
                Token(
                    token_id=int(row[0]),
                    form=row[1],
                    lemma=row[2] if row[2] != "_" else row[1].lower(),
                    upos=row[3],
                    feats=_parse_feats(row[5]),
                    head=head,
                    deprel=deprel,
                )
            )
        output.append(
            Sentence(
                source=source,
                document_id=current_document,
                paragraph_id=current_paragraph,
                sent_id=sent_id,
                text=comments.get("text"),
                tokens=tuple(tokens),
            )
        )
        comments = {}
        token_rows = []

    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines() + [""], 1):
        if not line:
            flush()
            continue
        if line.startswith("#"):
            body = line[1:].strip()
            if body.startswith("newdoc id") and "=" in body:
                flush()
                document = body.split("=", 1)[1].strip()
                if not document or document in seen_documents:
                    raise RuntimeError(f"missing/duplicate newdoc id: {document!r}")
                seen_documents.add(document)
                current_document = document
                current_paragraph = None
            elif body.startswith("newpar id") and "=" in body:
                current_paragraph = body.split("=", 1)[1].strip() or None
            if "=" in body:
                key, value = body.split("=", 1)
                comments[key.strip()] = value.strip()
            continue
        fields = line.split("\t")
        if len(fields) != 10:
            raise RuntimeError(f"malformed CoNLL-U row at {path}:{line_number}")
        if fields[0].isdigit():
            token_rows.append(fields)
        elif "-" in fields[0]:
            # Multiword ranges and empty nodes are not representation rows.
            if exclusion_counts is not None:
                exclusion_counts["multiword_token_rows"] = (
                    exclusion_counts.get("multiword_token_rows", 0) + 1
                )
            continue
        elif "." in fields[0]:
            if exclusion_counts is not None:
                exclusion_counts["empty_node_rows"] = exclusion_counts.get("empty_node_rows", 0) + 1
            continue
        else:
            raise RuntimeError(f"unknown token ID at {path}:{line_number}: {fields[0]!r}")
    return output


def _canonical_root(path: Path) -> Path:
    if path.is_symlink():
        raise RuntimeError(f"symlink input forbidden: {path}")
    resolved = path.resolve(strict=True)
    cursor = path.absolute()
    while True:
        if cursor.is_symlink():
            raise RuntimeError(f"symlink component forbidden: {cursor}")
        if cursor.parent == cursor:
            break
        cursor = cursor.parent
    if not resolved.is_file():
        raise RuntimeError(f"source is not a regular file: {resolved}")
    return resolved


def resolve_source_inputs(
    config: Mapping[str, Any], *, verify_digests: bool = True, repository_root: Path | None = None
) -> dict[str, Path]:
    repository_root = (
        repository_root.resolve()
        if repository_root is not None
        else Path(str(config.get("repository_root", "."))).resolve()
    )
    sources = config.get("sources")
    if not isinstance(sources, Mapping) or set(sources) != {"EWT", "GUM"}:
        raise RuntimeError("sources must be exactly EWT and GUM")
    exact_contract = config.get("exact_source_paths", {"EWT": "ewt.conllu", "GUM": "gum.conllu"})
    forbidden = tuple(
        str(x).lower()
        for x in config.get(
            "forbidden_data_tokens",
            ("c1", "c2", "confirmation", "final", "blind", "private", "eslspok", "lines", "wikineural", "fewnerd", "wnut", "pud"),
        )
    )
    output: dict[str, Path] = {}
    for name in ("EWT", "GUM"):
        spec = sources[name]
        if not isinstance(spec, Mapping):
            raise RuntimeError(f"invalid source spec: {name}")
        raw = str(spec.get("path", ""))
        expected_raw = str(exact_contract[name])
        if raw != expected_raw:
            raise RuntimeError(f"not exact allowlisted source: {name}:{raw}")
        if any(token in raw.lower().replace("-", "") for token in forbidden):
            raise RuntimeError(f"forbidden source token: {raw}")
        relative = Path(raw)
        if relative.is_absolute() or ".." in relative.parts:
            raise RuntimeError(f"source path must be contained relative path: {raw}")
        path = _canonical_root(repository_root / relative)
        if not path.is_relative_to(repository_root):
            raise RuntimeError(f"source escapes repository root: {raw}")
        if verify_digests:
            expected = str(spec.get("sha256", ""))
            actual = sha256_file(path)
            if expected != actual:
                raise RuntimeError(f"source digest mismatch: {name}:{actual}")
        output[name] = path
    return output


def position_factorial(
    *,
    target_ids: Sequence[int],
    true_prefix_ids: Sequence[int],
    unrelated_prefix_ids: Sequence[int],
    separator_id: int,
    shift: int,
    pivot_token_index: int,
) -> dict[str, dict[str, list[int]]]:
    target = list(map(int, target_ids))
    true_prefix = list(map(int, true_prefix_ids))
    unrelated = list(map(int, unrelated_prefix_ids))
    if not target:
        raise ValueError("empty target")
    if len(true_prefix) != len(unrelated):
        raise ValueError("prefixes must have equal tokenized length")
    if not 0 < pivot_token_index < len(target):
        raise ValueError("pivot must be interior")
    prefix_shift = len(true_prefix) + 1
    base_positions = list(range(len(target)))
    shifted_target = [prefix_shift + index for index in range(len(target))]
    gap_positions = [index + (shift if index >= pivot_token_index else 0) for index in base_positions]
    return {
        "bare": {"input_ids": target, "position_ids": base_positions},
        "uniform_shift": {"input_ids": target, "position_ids": [shift + x for x in base_positions]},
        "relative_gap": {"input_ids": target, "position_ids": gap_positions},
        "prefix_position_only": {"input_ids": target, "position_ids": shifted_target},
        "separator_only": {
            "input_ids": [int(separator_id), *target],
            "position_ids": [0, *shifted_target],
        },
        "true_prefix": {
            "input_ids": [*true_prefix, int(separator_id), *target],
            "position_ids": list(range(prefix_shift + len(target))),
        },
        "unrelated_prefix": {
            "input_ids": [*unrelated, int(separator_id), *target],
            "position_ids": list(range(prefix_shift + len(target))),
        },
    }


def _side(child_position: int, candidate_position: int) -> str:
    return "left" if candidate_position < child_position else "right"


def _broad_distance(left_position: int, right_position: int) -> str:
    return "near" if abs(left_position - right_position) <= 2 else "far"


def select_sham_heads(
    sentence: Sentence,
    *,
    aligned_token_ids: set[int],
    coarse_upos: Mapping[str, str],
    seed: int,
) -> list[dict[str, Any]]:
    by_id = {token.token_id: token for token in sentence.tokens}
    positions = {token.token_id: index for index, token in enumerate(sentence.tokens)}
    children = [
        token
        for token in sentence.tokens
        if token.token_id in aligned_token_ids and token.head in aligned_token_ids and token.head != 0
    ]
    children.sort(
        key=lambda token: stable_digest(
            NAMESPACE, "sham-child", seed, sentence.source, sentence.document_id, sentence.sent_id, token.token_id
        )
    )
    used: set[int] = set()
    output: list[dict[str, Any]] = []
    for child in children:
        head = by_id[child.head]
        child_pos = positions[child.token_id]
        head_pos = positions[head.token_id]
        target_stratum = (
            _side(child_pos, head_pos),
            _broad_distance(child_pos, head_pos),
            coarse_upos.get(head.upos, head.upos),
        )
        candidates: list[Token] = []
        for candidate in sentence.tokens:
            if (
                candidate.token_id not in aligned_token_ids
                or candidate.token_id in used
                or candidate.token_id in {child.token_id, head.token_id}
            ):
                continue
            candidate_pos = positions[candidate.token_id]
            stratum = (
                _side(child_pos, candidate_pos),
                _broad_distance(child_pos, candidate_pos),
                coarse_upos.get(candidate.upos, candidate.upos),
            )
            if stratum == target_stratum:
                candidates.append(candidate)
        if not candidates:
            continue
        candidates.sort(
            key=lambda candidate: (
                abs(abs(positions[candidate.token_id] - child_pos) - abs(head_pos - child_pos)),
                stable_digest(
                    NAMESPACE,
                    "sham-candidate",
                    seed,
                    sentence.source,
                    sentence.document_id,
                    sentence.sent_id,
                    child.token_id,
                    candidate.token_id,
                ),
            )
        )
        sham = candidates[0]
        used.add(sham.token_id)
        output.append(
            {
                "child_token_id": child.token_id,
                "head_token_id": head.token_id,
                "sham_token_id": sham.token_id,
                "side": target_stratum[0],
                "broad_distance": target_stratum[1],
                "head_upos_coarse": target_stratum[2],
            }
        )
    return output


def raw_coordinate_weights(standardized_weights: np.ndarray, scale: np.ndarray) -> np.ndarray:
    weights = np.asarray(standardized_weights, dtype=np.float64)
    scale_array = np.asarray(scale, dtype=np.float64)
    if weights.ndim != 2 or scale_array.ndim != 1 or weights.shape[1] != scale_array.shape[0]:
        raise ValueError("weight/scale shape mismatch")
    if not np.isfinite(weights).all() or not np.isfinite(scale_array).all() or np.any(scale_array <= 0):
        raise ValueError("non-finite/non-positive scale")
    raw = weights / scale_array[None, :]
    return raw - raw.mean(axis=0, keepdims=True)


def _row_basis(block: np.ndarray, singular_floor: float) -> np.ndarray:
    array = np.asarray(block, dtype=np.float64)
    if array.ndim != 2 or array.shape[1] == 0 or not np.isfinite(array).all():
        raise ValueError("invalid basis block")
    _, singular, vt = np.linalg.svd(array, full_matrices=False)
    rank = int(np.sum(singular > singular_floor))
    if rank == 0:
        raise ValueError("rank-zero basis block")
    return vt[:rank]


def build_projector(
    blocks: Sequence[np.ndarray], *, rank: int, singular_floor: float
) -> tuple[np.ndarray, dict[str, Any]]:
    if not blocks or rank <= 0:
        raise ValueError("projector requires blocks and positive rank")
    bases: list[np.ndarray] = []
    width: int | None = None
    block_ranks: list[int] = []
    for block in blocks:
        basis = _row_basis(np.asarray(block), singular_floor)
        if width is None:
            width = basis.shape[1]
        elif basis.shape[1] != width:
            raise ValueError("basis feature width mismatch")
        block_ranks.append(basis.shape[0])
        bases.append(basis / math.sqrt(basis.shape[0]))
    stacked = np.concatenate(bases, axis=0)
    _, singular, vt = np.linalg.svd(stacked, full_matrices=False)
    numerical_rank = int(np.sum(singular > singular_floor))
    retained = min(rank, numerical_rank)
    if retained == 0 or width is None:
        raise ValueError("rank-zero combined basis")
    columns = vt[:retained].T
    projector = columns @ columns.T
    return projector, {
        "rank": retained,
        "numerical_rank": numerical_rank,
        "requested_rank": rank,
        "block_ranks": block_ranks,
        "singular_values": singular.tolist(),
    }


def _orthonormal_columns(basis: np.ndarray) -> np.ndarray:
    array = np.asarray(basis, dtype=np.float64)
    if array.ndim != 2 or not np.isfinite(array).all():
        raise ValueError("invalid basis")
    if array.shape[1] == 0:
        raise ValueError("empty basis")
    q, r = np.linalg.qr(array)
    diagonal = np.abs(np.diag(r))
    rank = int(np.sum(diagonal > 1e-10))
    if rank == 0:
        raise ValueError("rank-zero basis")
    return q[:, :rank]


def basis_overlap(left: np.ndarray, right: np.ndarray) -> float:
    a = _orthonormal_columns(left)
    b = _orthonormal_columns(right)
    if a.shape[0] != b.shape[0]:
        raise ValueError("basis feature width mismatch")
    singular = np.linalg.svd(a.T @ b, compute_uv=False)
    return float(np.sum(singular * singular) / min(a.shape[1], b.shape[1]))


def terminal_outcome(
    candidate_statuses: Mapping[str, str], *, technical_failure: bool
) -> str:
    allowed = {"ineligible", "eligible_not_passed", "passed"}
    if not candidate_statuses or any(value not in allowed for value in candidate_statuses.values()):
        raise ValueError("invalid candidate statuses")
    if technical_failure or any(value == "ineligible" for value in candidate_statuses.values()):
        return "technically_ineligible"
    passed = [key for key, value in candidate_statuses.items() if value == "passed"]
    if not passed:
        return "no_decomposition_nominated"
    if len(passed) > 1:
        return "multiple_discovery_candidates"
    return f"nominate_{passed[0]}"


def atomic_write_json(path: Path, value: Any) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False) + "\n"
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    temporary.write_text(payload, encoding="utf-8")
    os.replace(temporary, path)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def atomic_write_jsonl(path: Path, rows: Iterable[Mapping[str, Any]]) -> tuple[str, int]:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    digest = hashlib.sha256()
    count = 0
    with temporary.open("wb") as handle:
        for row in rows:
            payload = canonical_json_bytes(dict(row)) + b"\n"
            handle.write(payload)
            digest.update(payload)
            count += 1
    os.replace(temporary, path)
    return digest.hexdigest(), count


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]


def capitalization_label(word: str) -> str:
    letters = "".join(char for char in word if char.isalpha())
    if not letters:
        return "nonalpha"
    if letters.islower():
        return "lower"
    if letters.isupper():
        return "upper"
    if letters.istitle():
        return "title"
    return "mixed"


def word_length_label(word: str) -> str:
    length = len(word)
    if length <= 1:
        return "1"
    if length == 2:
        return "2"
    if length <= 4:
        return "3-4"
    if length <= 7:
        return "5-7"
    return "8+"


def sentence_length_label(length: int) -> str:
    if length <= 4:
        return "1-4"
    if length <= 8:
        return "5-8"
    if length <= 16:
        return "9-16"
    if length <= 32:
        return "17-32"
    if length <= 64:
        return "33-64"
    return "65+"


def start_distance_label(position: int) -> str:
    if position <= 1:
        return str(position)
    if position <= 3:
        return "2-3"
    if position <= 7:
        return "4-7"
    if position <= 15:
        return "8-15"
    if position <= 31:
        return "16-31"
    return "32+"


def pair_distance_label(distance: int) -> str:
    if distance <= 2:
        return str(distance)
    if distance <= 4:
        return "3-4"
    if distance <= 8:
        return "5-8"
    return "9+"


def head_distance_label(child_position: int, head_position: int | None) -> str:
    if head_position is None:
        return "ROOT"
    delta = head_position - child_position
    side = "L" if delta < 0 else "R"
    magnitude = abs(delta)
    return side + ("1" if magnitude == 1 else "2" if magnitude == 2 else "3-4" if magnitude <= 4 else "5+")


def dependency_depth_label(token_id: int, by_id: Mapping[int, Token]) -> str:
    current = token_id
    seen: set[int] = set()
    depth = 0
    while True:
        if current in seen or current not in by_id:
            return DROP
        seen.add(current)
        head = by_id[current].head
        if head == 0:
            return str(depth) if depth < 4 else "4+"
        depth += 1
        current = head


def token_layout(tokenizer: Any, sentence: Sentence, max_length: int) -> dict[str, Any]:
    words = [token.form for token in sentence.tokens]
    encoding = tokenizer(words, is_split_into_words=True, add_special_tokens=False, truncation=False)
    input_ids = list(map(int, encoding["input_ids"]))
    word_ids = list(encoding.word_ids())
    if len(input_ids) != len(word_ids):
        raise RuntimeError(f"tokenizer word-id length mismatch: {sentence.sent_id}")
    spans: dict[int, list[int]] = defaultdict(list)
    for position, word_index in enumerate(word_ids):
        if word_index is not None:
            spans[int(word_index)].append(position)
    first_positions: dict[int, int] = {}
    token_spans: dict[int, list[int]] = {}
    for word_index, positions in spans.items():
        if word_index >= len(sentence.tokens):
            raise RuntimeError(f"tokenizer word index drift: {sentence.sent_id}")
        if positions and positions[-1] < max_length:
            token_id = sentence.tokens[word_index].token_id
            first_positions[token_id] = positions[0]
            token_spans[token_id] = positions
    return {
        "input_ids": input_ids[:max_length],
        "untruncated_length": len(input_ids),
        "first_positions": first_positions,
        "token_spans": token_spans,
        "word_ids": word_ids[:max_length],
        "complete": len(input_ids) <= max_length,
    }


def sentence_content_hash(sentence: Sentence) -> str:
    normalized = " ".join(" ".join(token.form.lower() for token in sentence.tokens).split())
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def _main_labels(sentence: Sentence, token: Token, position: int, tokenized_length: int) -> dict[str, str]:
    by_id = {item.token_id: item for item in sentence.tokens}
    positions = {item.token_id: index for index, item in enumerate(sentence.tokens)}
    if token.upos not in UPOS_MAP:
        raise RuntimeError(f"unknown UPOS {token.upos!r} at {sentence.sent_id}")
    if token.deprel not in DEPREL_MAP:
        raise RuntimeError(f"unknown deprel {token.deprel!r} at {sentence.sent_id}")
    head_position = positions.get(token.head) if token.head else None
    relative = min(3, (4 * positions[token.token_id]) // max(1, len(sentence.tokens)))
    lowered = token.form.lower()
    number = token.feats.get("Number", DROP)
    if number not in {"Sing", "Plur"}:
        number = DROP
    return {
        "start_distance": start_distance_label(position),
        "relative_quartile": str(relative),
        "head_signed_distance": head_distance_label(positions[token.token_id], head_position),
        "dependency_depth": dependency_depth_label(token.token_id, by_id),
        "deprel_coarse": DEPREL_MAP[token.deprel],
        "token_identity": lowered if lowered in PRIMARY_TOKEN_VOCABULARY else DROP,
        "lemma": token.lemma.lower(),
        "number": number,
        "upos_coarse": UPOS_MAP[token.upos],
        "capitalization": capitalization_label(token.form),
        "word_length": word_length_label(token.form),
        "punctuation": "punct" if token.upos == "PUNCT" else "nonpunct",
        "sentence_length": sentence_length_label(tokenized_length),
    }


def _group_cap_task_rows(
    rows: Sequence[Mapping[str, Any]], *, maximum: int, seed: int
) -> list[dict[str, Any]]:
    by_group: dict[str, list[Mapping[str, Any]]] = defaultdict(list)
    for row in rows:
        by_group[str(row["document_group"])].append(row)
    output: list[dict[str, Any]] = []
    for group in sorted(by_group, key=lambda value: value.encode("utf-8")):
        output.extend(label_blind_cap(by_group[group], maximum, seed=seed))
    return sorted(output, key=lambda row: str(row["row_id"]).encode("utf-8"))


def support_report(
    rows: Sequence[Mapping[str, Any]],
    *,
    source: str,
    task: str,
    thresholds: Mapping[str, Any],
    seed: int,
    expected_labels: Sequence[str] | None = None,
) -> dict[str, Any]:
    by_group_labels: dict[str, set[str]] = defaultdict(set)
    group_counts: Counter[str] = Counter()
    for row in rows:
        group = str(row["document_group"])
        label = str(row["label"])
        by_group_labels[group].add(label)
        group_counts[group] += 1
    observed = sorted({str(row["label"]) for row in rows}, key=lambda value: value.encode("utf-8"))
    labels = list(expected_labels) if expected_labels is not None else observed
    class_groups = {label: sum(label in values for values in by_group_labels.values()) for label in labels}
    reasons: list[str] = []
    if len(by_group_labels) < int(thresholds["min_groups"]):
        reasons.append("groups_below_minimum")
    if len(labels) < 2:
        reasons.append("fewer_than_two_labels")
    if any(value < int(thresholds["min_class_groups"]) for value in class_groups.values()):
        reasons.append("class_groups_below_minimum")
    if group_counts and max(group_counts.values()) > int(thresholds["max_rows_per_group"]):
        reasons.append("rows_per_group_above_maximum")
    groups = sorted(by_group_labels, key=lambda value: value.encode("utf-8"))
    finite = 0
    for draw in range(int(thresholds["bootstrap_draws"])):
        multiplicities = bootstrap_component_multiplicities(
            groups, direction=f"support:{source}", endpoint=task, draw=draw, seed=seed
        )
        covered: set[str] = set()
        for group, multiplicity in multiplicities.items():
            if multiplicity:
                covered.update(by_group_labels[group])
        if all(label in covered for label in labels):
            finite += 1
    if finite < int(thresholds["min_finite_draws"]):
        reasons.append("bootstrap_finite_below_minimum")
    return {
        "source": source,
        "task": task,
        "status": "eligible" if not reasons else "ineligible",
        "reasons": reasons,
        "rows": len(rows),
        "groups": len(by_group_labels),
        "labels": labels,
        "class_group_counts": class_groups,
        "max_rows_per_group": max(group_counts.values(), default=0),
        "bootstrap": {
            "draws": int(thresholds["bootstrap_draws"]),
            "finite_draws": finite,
            "minimum_finite_draws": int(thresholds["min_finite_draws"]),
        },
    }


def _select_pair_indices(sentence: Sentence, aligned_ids: Sequence[int], *, maximum: int, seed: int) -> list[tuple[int, int]]:
    ordered = sorted(aligned_ids)
    if len(ordered) < 2:
        return []
    pairs: set[tuple[int, int]] = set()
    attempts = max(64, maximum * 8)
    for slot in range(attempts):
        raw = stable_digest(NAMESPACE, "token-pair", seed, sentence.source, sentence.document_id, sentence.sent_id, slot)
        left_index = int.from_bytes(raw[:8], "big") % len(ordered)
        right_index = int.from_bytes(raw[8:16], "big") % (len(ordered) - 1)
        if right_index >= left_index:
            right_index += 1
        left, right = sorted((ordered[left_index], ordered[right_index]))
        pairs.add((left, right))
        if len(pairs) >= maximum:
            break
    return sorted(pairs)


def _proper_noun_quartiles(sentences: Sequence[Sentence]) -> dict[str, int]:
    by_form: dict[str, set[str]] = defaultdict(set)
    for sentence in sentences:
        for token in sentence.tokens:
            if token.upos == "PROPN":
                by_form[token.form.lower()].add(sentence.document_id)
    ordered = sorted(by_form, key=lambda form: (len(by_form[form]), form.encode("utf-8")))
    return {form: min(3, (4 * rank) // max(1, len(ordered))) for rank, form in enumerate(ordered)}


def _pick_token_by_hash(
    sentence: Sentence, token_ids: Sequence[int], namespace: str, seed: int
) -> int | None:
    if not token_ids:
        return None
    return min(
        token_ids,
        key=lambda token_id: stable_digest(
            NAMESPACE, namespace, seed, sentence.source, sentence.document_id, sentence.sent_id, token_id
        ),
    )


class _UnionFind:
    def __init__(self) -> None:
        self.parent: dict[str, str] = {}

    def find(self, item: str) -> str:
        self.parent.setdefault(item, item)
        if self.parent[item] != item:
            self.parent[item] = self.find(self.parent[item])
        return self.parent[item]

    def union(self, left: str, right: str) -> None:
        a, b = self.find(left), self.find(right)
        if a == b:
            return
        if a.encode("utf-8") <= b.encode("utf-8"):
            self.parent[b] = a
        else:
            self.parent[a] = b


def build_prepared_data_legacy_do_not_call(config: Mapping[str, Any], config_path: Path) -> dict[str, Any]:
    """Build all label-only rows and intervention inputs without loading a neural model."""

    from transformers import AutoTokenizer

    repository_root = config_path.resolve().parents[2]
    if str(config.get("data_root")) != "data/atlas_discovery_v3_3_attempt7_qa_compact":
        raise RuntimeError("attempt7 QA pool requires its exact technical-only namespace")
    data_root = repository_root / str(config["data_root"])
    if data_root.exists():
        manifest_path = data_root / "prepared" / "manifest.json"
        if manifest_path.exists():
            manifest = read_json(manifest_path)
            if manifest.get("config_sha256") != sha256_file(config_path):
                raise RuntimeError("existing prepared data belongs to a different config")
            return manifest
        raise RuntimeError(f"refusing partially existing data root: {data_root}")

    data_root.mkdir(parents=True)
    process_snapshot = {
        "schema_version": "atlas_discovery_v3_3_attempt7_qa_pool_process_snapshot_v1",
        "argv": sys.argv,
        "cwd": str(Path.cwd()),
        "executable": sys.executable,
        "platform": platform.platform(),
        "pid": os.getpid(),
        "process_table": subprocess.run(
            ["ps", "-eo", "pid=,ppid=,lstart=,args="],
            check=True,
            capture_output=True,
            text=True,
        ).stdout.splitlines(),
    }
    atomic_write_json(data_root / "process_snapshot_preopen.json", process_snapshot)

    source_paths = resolve_source_inputs(config, repository_root=repository_root)
    common_cell_spec = config["cross_family"]["common_joint_cells"]
    common_cell_path = _canonical_root(repository_root / str(common_cell_spec["path"]))
    if not common_cell_path.is_relative_to(repository_root):
        raise RuntimeError("common joint-cell artifact escapes repository")
    if sha256_file(common_cell_path) != str(common_cell_spec["sha256"]):
        raise RuntimeError("common joint-cell artifact drift")
    common_cell_artifact = read_json(common_cell_path)
    if common_cell_artifact.get("schema_version") != "atlas_discovery_v3_1_attempt5_common_joint_cells_v1":
        raise RuntimeError("unknown common joint-cell artifact")
    allowed_joint_cells = set(map(str, common_cell_artifact["cells"]))
    if len(allowed_joint_cells) != int(common_cell_artifact["common_cell_count"]):
        raise RuntimeError("duplicate/drifting common joint-cell allowlist")
    opened_input_ledger = {
        "schema_version": "atlas_discovery_v3_3_attempt7_qa_pool_opened_input_ledger_v1",
        "scope": "declared_scientific_inputs_loaded_by_the_v3_runner",
        "config": {
            "path": str(config_path.relative_to(repository_root)),
            "sha256": sha256_file(config_path),
        },
        "protocol": {
            "path": str(config["protocol"]["path"]),
            "sha256": sha256_file(repository_root / str(config["protocol"]["path"])),
        },
        "sources": {
            name: {
                "path": str(path.relative_to(repository_root)),
                "sha256": sha256_file(path),
                "role": "technical_numerical_qa_only",
            }
            for name, path in source_paths.items()
        },
        "model": {
            "name": str(config["model"]["name"]),
            "revision": str(config["model"]["revision"]),
            "role": "pinned_tokenizer_now_and_pinned_backbone_only_after_authorization",
        },
        "common_joint_cells": {
            "path": str(common_cell_path.relative_to(repository_root)),
            "sha256": sha256_file(common_cell_path),
            "role": "attempt5_label_only_source_common_nuisance_support",
        },
        "forbidden_or_blind_inputs_opened": False,
    }
    opened_input_ledger_sha = atomic_write_json(data_root / "opened_input_ledger.json", opened_input_ledger)
    model_spec = config["model"]
    tokenizer = AutoTokenizer.from_pretrained(
        str(model_spec["name"]), revision=str(model_spec["revision"]), local_files_only=True
    )
    max_length = int(config["data"]["max_length"])
    seed = int(config["seed"])
    parse_exclusions: dict[str, dict[str, int]] = {"EWT": {}, "GUM": {}}
    parsed = {
        name: parse_conllu(path, name, exclusion_counts=parse_exclusions[name])
        for name, path in source_paths.items()
    }
    raw_sentence_counts = {name: len(rows) for name, rows in parsed.items()}
    duplicates = set(map(sentence_content_hash, parsed["EWT"])) & set(
        map(sentence_content_hash, parsed["GUM"])
    )
    if duplicates:
        parsed = {
            name: [row for row in rows if sentence_content_hash(row) not in duplicates]
            for name, rows in parsed.items()
        }

    prepared_root = data_root / "prepared"
    manifest: dict[str, Any] = {
        "schema_version": "atlas_discovery_v3_3_attempt7_qa_pool_prepared_v1",
        "config_sha256": sha256_file(config_path),
        "protocol_sha256": sha256_file(repository_root / str(config["protocol"]["path"])),
        "source_input_sha256": {name: sha256_file(path) for name, path in source_paths.items()},
        # The required process snapshot is intentionally outside the deterministic
        # scientific manifest because PID/process-table contents are volatile.
        "process_snapshot_preopen_path": "process_snapshot_preopen.json",
        "opened_input_ledger_sha256": opened_input_ledger_sha,
        "cross_source_duplicate_hashes_excluded": len(duplicates),
        "common_joint_cells_sha256": sha256_file(common_cell_path),
        "common_joint_cell_count": len(allowed_joint_cells),
        "sources": {},
    }
    joint_rows_by_source: dict[str, list[dict[str, Any]]] = {}

    for source in ("EWT", "GUM"):
        sentences = parsed[source]
        layouts = {sentence.sent_id: token_layout(tokenizer, sentence, max_length) for sentence in sentences}
        by_document: dict[str, list[Sentence]] = defaultdict(list)
        for sentence in sentences:
            by_document[sentence.document_id].append(sentence)
        layout_exclusions = {
            "raw_sentences": raw_sentence_counts[source],
            "cross_source_duplicate_sentences": raw_sentence_counts[source] - len(sentences),
            "tokenizer_incomplete_sentences": sum(not row["complete"] for row in layouts.values()),
            "raw_words": sum(len(sentence.tokens) for sentence in sentences),
            "fully_aligned_words": sum(len(row["first_positions"]) for row in layouts.values()),
        }
        layout_exclusions["truncated_or_unaligned_full_words"] = (
            layout_exclusions["raw_words"] - layout_exclusions["fully_aligned_words"]
        )
        main_units: list[dict[str, Any]] = []
        activation_rows: list[dict[str, Any]] = []
        row_by_token: dict[tuple[str, int], str] = {}
        main_candidates: dict[str, list[dict[str, Any]]] = {task: [] for task in MAIN_TASKS}
        main_candidates["lemma_identity"] = []

        for sentence in sentences:
            layout = layouts[sentence.sent_id]
            first = layout["first_positions"]
            unit_positions: list[int] = []
            unit_row_ids: list[str] = []
            for token in sentence.tokens:
                if token.token_id not in first:
                    continue
                row_id = f"{NAMESPACE}:main:{source}:{sentence.sent_id}:{token.token_id}"
                labels = _main_labels(
                    sentence, token, int(first[token.token_id]), int(layout["untruncated_length"])
                )
                row_by_token[(sentence.sent_id, token.token_id)] = row_id
                row = {
                    "row_id": row_id,
                    "source": source,
                    "document_group": f"{source}:{sentence.document_id}",
                    "component_id": f"{source}:{sentence.document_id}",
                    "fold": stable_fold(source, sentence.document_id, seed=seed, folds=int(config["data"]["folds"])),
                    "sent_id": sentence.sent_id,
                    "source_document_length": len(by_document[sentence.document_id]),
                    "token_id": token.token_id,
                    "token_position": int(first[token.token_id]),
                    "labels": labels,
                    "kind": "main",
                }
                activation_rows.append(row)
                unit_positions.append(int(first[token.token_id]))
                unit_row_ids.append(row_id)
                for task in MAIN_TASKS:
                    label = labels[task]
                    if label == DROP:
                        continue
                    main_candidates[task].append(
                        {
                            "row_id": row_id,
                            "label": label,
                            "document_group": row["document_group"],
                            "component_id": row["component_id"],
                            "sent_id": sentence.sent_id,
                        }
                    )
                main_candidates["lemma_identity"].append(
                    {
                        "row_id": row_id,
                        "label": labels["lemma"],
                        "document_group": row["document_group"],
                        "component_id": row["component_id"],
                        "sent_id": sentence.sent_id,
                    }
                )
            if unit_row_ids:
                main_units.append(
                    {
                        "unit_id": f"{NAMESPACE}:main:{source}:{sentence.sent_id}",
                        "source": source,
                        "kind": "main",
                        "input_ids": layout["input_ids"],
                        "position_ids": list(range(len(layout["input_ids"]))),
                        "attention_mask": [1] * len(layout["input_ids"]),
                        "positions": unit_positions,
                        "row_ids": unit_row_ids,
                    }
                )

        pair_rows_raw: list[dict[str, Any]] = []
        for sentence in sentences:
            aligned = [token.token_id for token in sentence.tokens if (sentence.sent_id, token.token_id) in row_by_token]
            positions = {token.token_id: index for index, token in enumerate(sentence.tokens)}
            for left, right in _select_pair_indices(
                sentence, aligned, maximum=int(config["data"]["pairs_per_sentence"]), seed=seed
            ):
                row_id = f"{NAMESPACE}:pair:{source}:{sentence.sent_id}:{left}:{right}"
                pair_rows_raw.append(
                    {
                        "row_id": row_id,
                        "source": source,
                        "document_group": f"{source}:{sentence.document_id}",
                        "component_id": f"{source}:{sentence.document_id}",
                        "sent_id": sentence.sent_id,
                        "left_row_id": row_by_token[(sentence.sent_id, left)],
                        "right_row_id": row_by_token[(sentence.sent_id, right)],
                        "left_token_id": left,
                        "right_token_id": right,
                        "label": pair_distance_label(positions[right] - positions[left]),
                    }
                )
        pair_rows = _group_cap_task_rows(
            pair_rows_raw,
            maximum=int(config["support"]["max_rows_per_group"]),
            seed=seed,
        )

        relation_rows_raw: list[dict[str, Any]] = []
        for sentence in sentences:
            aligned = {token.token_id for token in sentence.tokens if (sentence.sent_id, token.token_id) in row_by_token}
            labels_by_token = {
                token.token_id: _main_labels(
                    sentence,
                    token,
                    int(layouts[sentence.sent_id]["first_positions"][token.token_id]),
                    int(layouts[sentence.sent_id]["untruncated_length"]),
                )
                for token in sentence.tokens
                if token.token_id in aligned
            }
            for match in select_sham_heads(
                sentence, aligned_token_ids=aligned, coarse_upos=UPOS_MAP, seed=seed
            ):
                child = int(match["child_token_id"])
                head = int(match["head_token_id"])
                sham = int(match["sham_token_id"])
                row_id = f"{NAMESPACE}:relation:{source}:{sentence.sent_id}:{child}"
                relation_rows_raw.append(
                    {
                        "row_id": row_id,
                        "source": source,
                        "document_group": f"{source}:{sentence.document_id}",
                        "component_id": f"{source}:{sentence.document_id}",
                        "sent_id": sentence.sent_id,
                        "child_row_id": row_by_token[(sentence.sent_id, child)],
                        "head_row_id": row_by_token[(sentence.sent_id, head)],
                        "sham_row_id": row_by_token[(sentence.sent_id, sham)],
                        "labels": {
                            task: labels_by_token[child][task]
                            for task in ("head_signed_distance", "dependency_depth", "deprel_coarse")
                        },
                        **match,
                    }
                )
        relation_rows = _group_cap_task_rows(
            [
                {**row, "label": row["labels"]["deprel_coarse"]}
                for row in relation_rows_raw
            ],
            maximum=int(config["support"]["max_rows_per_group"]),
            seed=seed,
        )
        keep_relation_ids = {row["row_id"] for row in relation_rows}
        relation_rows = [row for row in relation_rows_raw if row["row_id"] in keep_relation_ids]

        intervention_units: list[dict[str, Any]] = []
        intervention_rows: list[dict[str, Any]] = []
        intervention_pairs: list[dict[str, Any]] = []

        def add_unit(
            *, unit_id: str, kind: str, input_ids: Sequence[int], position_ids: Sequence[int], targets: Sequence[tuple[str, int, str]]
        ) -> None:
            if len(input_ids) != len(position_ids) or len(input_ids) > max_length:
                raise RuntimeError(f"invalid intervention unit layout: {unit_id}")
            positions: list[int] = []
            row_ids: list[str] = []
            for row_id, position, role in targets:
                if not 0 <= position < len(input_ids):
                    raise RuntimeError(f"intervention target outside input: {unit_id}:{position}")
                positions.append(int(position))
                row_ids.append(row_id)
                intervention_rows.append(
                    {
                        "row_id": row_id,
                        "source": source,
                        "kind": kind,
                        "target_role": role,
                    }
                )
            intervention_units.append(
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

        # One label-blind sequential-position target per document.
        sequential_targets: list[Sentence] = []
        for document, rows in by_document.items():
            candidates = [
                row
                for row in rows
                if layouts[row.sent_id]["complete"]
                and len(layouts[row.sent_id]["input_ids"]) >= 4
                and len(layouts[row.sent_id]["first_positions"]) >= 2
            ]
            if candidates:
                sequential_targets.append(
                    min(candidates, key=lambda row: stable_digest(NAMESPACE, "sequential-target", seed, source, document, row.sent_id))
                )
        for sentence in sequential_targets:
            layout = layouts[sentence.sent_id]
            input_ids = layout["input_ids"]
            pivot = len(input_ids) // 2
            before = [
                (token_id, pos)
                for token_id, pos in layout["first_positions"].items()
                if pos < pivot
            ]
            after = [
                (token_id, pos)
                for token_id, pos in layout["first_positions"].items()
                if pos >= pivot
            ]
            if not before or not after:
                continue
            pre_id, pre_pos = min(before, key=lambda item: stable_digest(NAMESPACE, "gap-pre", seed, source, sentence.sent_id, item[0]))
            post_id, post_pos = min(after, key=lambda item: stable_digest(NAMESPACE, "gap-post", seed, source, sentence.sent_id, item[0]))
            post_token = next(token for token in sentence.tokens if token.token_id == post_id)
            post_labels = _main_labels(
                sentence, post_token, post_pos, int(layout["untruncated_length"])
            )
            variants = position_factorial(
                target_ids=input_ids,
                true_prefix_ids=[1],
                unrelated_prefix_ids=[2],
                separator_id=int(config["data"]["separator_token_id"]),
                shift=int(config["interventions"]["position_shift"]),
                pivot_token_index=pivot,
            )
            pair_id = stable_hex(NAMESPACE, "sequential-pair", seed, source, sentence.document_id)[:24]
            condition_rows: dict[str, dict[str, str]] = {}
            for condition in ("bare", "uniform_shift", "relative_gap"):
                spec = variants[condition]
                rows_map = {
                    "pre": f"{NAMESPACE}:intervention:{pair_id}:{condition}:pre",
                    "post": f"{NAMESPACE}:intervention:{pair_id}:{condition}:post",
                }
                add_unit(
                    unit_id=f"{NAMESPACE}:intervention:{pair_id}:{condition}",
                    kind=condition,
                    input_ids=spec["input_ids"],
                    position_ids=spec["position_ids"],
                    targets=((rows_map["pre"], pre_pos, "pre"), (rows_map["post"], post_pos, "post")),
                )
                condition_rows[condition] = rows_map
            intervention_pairs.append(
                {
                    "pair_id": pair_id,
                    "construct": "relative_gap",
                    "source": source,
                    "document_group": f"{source}:{sentence.document_id}",
                    "component_id": f"{source}:{sentence.document_id}",
                    "fold": stable_fold(source, sentence.document_id, seed=seed, folds=int(config["data"]["folds"])),
                    "sent_id": sentence.sent_id,
                    "source_document_length": len(by_document[sentence.document_id]),
                    "pivot": pivot,
                    "pre_token_id": pre_id,
                    "post_token_id": post_id,
                    "target_metadata": {
                        key: post_labels[key]
                        for key in (
                            "start_distance",
                            "upos_coarse",
                            "capitalization",
                            "word_length",
                            "sentence_length",
                        )
                    },
                    "rows": condition_rows,
                }
            )

        # Natural-prefix factorial, one target per document and donor once.
        ordered_by_doc = {document: list(rows) for document, rows in by_document.items()}
        context_targets: list[tuple[Sentence, Sentence]] = []
        for document, rows in ordered_by_doc.items():
            candidates: list[tuple[Sentence, Sentence]] = []
            for previous, target in zip(rows, rows[1:], strict=False):
                left, right = layouts[previous.sent_id], layouts[target.sent_id]
                if not (left["complete"] and right["complete"]):
                    continue
                if len(right["input_ids"]) < 2:
                    continue
                if len(left["input_ids"]) + 1 + len(right["input_ids"]) > max_length:
                    continue
                eligible_tokens = [
                    token.token_id
                    for token in target.tokens
                    if token.token_id in right["first_positions"] and token.upos != "PUNCT"
                ]
                if eligible_tokens:
                    candidates.append((previous, target))
            if candidates:
                context_targets.append(
                    min(
                        candidates,
                        key=lambda pair: stable_digest(NAMESPACE, "context-target", seed, source, document, pair[1].sent_id),
                    )
                )
        donors_by_fold_length: dict[tuple[int, int], list[Sentence]] = defaultdict(list)
        for donor in sentences:
            layout = layouts[donor.sent_id]
            if layout["complete"]:
                fold = stable_fold(source, donor.document_id, seed=seed, folds=int(config["data"]["folds"]))
                donors_by_fold_length[(fold, len(layout["input_ids"]))].append(donor)
        context_candidates: list[dict[str, Any]] = []
        for previous, target in sorted(
            context_targets,
            key=lambda pair: stable_digest(NAMESPACE, "context-order", seed, source, pair[1].document_id),
        ):
            true_layout = layouts[previous.sent_id]
            fold = stable_fold(source, target.document_id, seed=seed, folds=int(config["data"]["folds"]))
            donors = [
                donor
                for donor in donors_by_fold_length[(fold, len(true_layout["input_ids"]))]
                if donor.document_id != target.document_id
                and sentence_content_hash(donor) != sentence_content_hash(previous)
            ]
            for donor in sorted(
                donors,
                key=lambda row: stable_digest(
                    NAMESPACE,
                    "context-donor",
                    seed,
                    source,
                    target.document_id,
                    target.sent_id,
                    row.document_id,
                    row.sent_id,
                ),
            ):
                candidate_id = stable_hex(
                    NAMESPACE,
                    "context-candidate",
                    seed,
                    source,
                    target.document_id,
                    target.sent_id,
                    donor.document_id,
                    donor.sent_id,
                )
                context_candidates.append(
                    {
                        "candidate_id": candidate_id,
                        "left_document": f"{source}:{target.document_id}",
                        "right_document": f"{source}:{donor.document_id}",
                        "previous": previous,
                        "target": target,
                        "donor": donor,
                        "fold": fold,
                    }
                )
        selected_context, context_match_report = maximum_cardinality_document_matching(context_candidates)
        for candidate in selected_context:
            previous = candidate["previous"]
            target = candidate["target"]
            donor = candidate["donor"]
            fold = int(candidate["fold"])
            true_layout, target_layout = layouts[previous.sent_id], layouts[target.sent_id]
            target_ids = [
                token.token_id
                for token in target.tokens
                if token.token_id in target_layout["first_positions"] and token.upos != "PUNCT"
            ]
            target_token_id = _pick_token_by_hash(target, target_ids, "context-token", seed)
            if target_token_id is None:
                raise RuntimeError("matched context target lost every aligned token")
            target_position = int(target_layout["first_positions"][target_token_id])
            variants = position_factorial(
                target_ids=target_layout["input_ids"],
                true_prefix_ids=true_layout["input_ids"],
                unrelated_prefix_ids=layouts[donor.sent_id]["input_ids"],
                separator_id=int(config["data"]["separator_token_id"]),
                shift=int(config["interventions"]["position_shift"]),
                pivot_token_index=max(1, len(target_layout["input_ids"]) // 2),
            )
            pair_id = stable_hex(NAMESPACE, "context-pair", seed, source, target.document_id, target.sent_id)[:24]
            condition_rows: dict[str, str] = {}
            shift_length = len(true_layout["input_ids"]) + 1
            for condition in (
                "bare",
                "prefix_position_only",
                "separator_only",
                "true_prefix",
                "unrelated_prefix",
            ):
                spec = variants[condition]
                if condition in {"bare", "prefix_position_only"}:
                    unit_target_position = target_position
                elif condition == "separator_only":
                    unit_target_position = 1 + target_position
                else:
                    unit_target_position = shift_length + target_position
                row_id = f"{NAMESPACE}:intervention:{pair_id}:{condition}:target"
                add_unit(
                    unit_id=f"{NAMESPACE}:intervention:{pair_id}:{condition}",
                    kind=condition,
                    input_ids=spec["input_ids"],
                    position_ids=spec["position_ids"],
                    targets=((row_id, unit_target_position, "target"),),
                )
                condition_rows[condition] = row_id
            token = next(item for item in target.tokens if item.token_id == target_token_id)
            labels = _main_labels(target, token, target_position, int(target_layout["untruncated_length"]))
            component_documents = sorted(
                (str(candidate["left_document"]), str(candidate["right_document"])),
                key=lambda value: value.encode("utf-8"),
            )
            intervention_pairs.append(
                {
                    "pair_id": pair_id,
                    "construct": "context_factorial",
                    "source": source,
                    "document_group": f"{source}:{target.document_id}",
                    "donor_document_group": f"{source}:{donor.document_id}",
                    "component_id": "component:context:" + stable_hex(*component_documents)[:24],
                    "component_documents": component_documents,
                    "fold": fold,
                    "target_sent_id": target.sent_id,
                    "source_document_length": len(by_document[target.document_id]),
                    "true_prefix_sent_id": previous.sent_id,
                    "unrelated_prefix_sent_id": donor.sent_id,
                    "prefix_length": len(true_layout["input_ids"]),
                    "target_token_id": target_token_id,
                    "target_metadata": {
                        key: labels[key]
                        for key in ("start_distance", "upos_coarse", "capitalization", "word_length", "sentence_length")
                    },
                    "rows": condition_rows,
                }
            )

        # Matched proper-noun substitutions.
        quartiles = _proper_noun_quartiles(sentences)
        propn_candidates: list[tuple[Sentence, Token]] = []
        for sentence in sentences:
            layout = layouts[sentence.sent_id]
            if not layout["complete"]:
                continue
            for token in sentence.tokens:
                if token.upos == "PROPN" and len(layout["token_spans"].get(token.token_id, [])) == 1:
                    propn_candidates.append((sentence, token))
        by_stratum: dict[tuple[int, str, str, int], list[tuple[Sentence, Token]]] = defaultdict(list)
        for sentence, token in propn_candidates:
            number = token.feats.get("Number", "NONE")
            fold = stable_fold(source, sentence.document_id, seed=seed, folds=int(config["data"]["folds"]))
            stratum = (fold, capitalization_label(token.form), number, quartiles[token.form.lower()])
            by_stratum[stratum].append((sentence, token))
        proper_edge_candidates: dict[tuple[str, str], dict[str, Any]] = {}
        for source_sentence, source_token in sorted(
            propn_candidates,
            key=lambda pair: stable_digest(
                NAMESPACE, "proper-source", seed, source, pair[0].document_id, pair[0].sent_id, pair[1].token_id
            ),
        ):
            fold = stable_fold(source, source_sentence.document_id, seed=seed, folds=int(config["data"]["folds"]))
            stratum = (
                fold,
                capitalization_label(source_token.form),
                source_token.feats.get("Number", "NONE"),
                quartiles[source_token.form.lower()],
            )
            source_layout = layouts[source_sentence.sent_id]
            words = [token.form for token in source_sentence.tokens]
            source_word_index = next(
                index for index, token in enumerate(source_sentence.tokens) if token.token_id == source_token.token_id
            )
            source_position = int(source_layout["first_positions"][source_token.token_id])
            control_ids = [
                token.token_id
                for token in source_sentence.tokens
                if token.token_id in source_layout["first_positions"]
                and token.token_id != source_token.token_id
                and token.upos != "PUNCT"
            ]
            control_token_id = _pick_token_by_hash(source_sentence, control_ids, "proper-control", seed)
            if control_token_id is None:
                continue
            for donor_sentence, donor_token in sorted(
                by_stratum[stratum],
                key=lambda pair: stable_digest(
                    NAMESPACE,
                    "proper-donor",
                    seed,
                    source,
                    source_sentence.document_id,
                    source_sentence.sent_id,
                    pair[0].document_id,
                    pair[0].sent_id,
                    pair[1].token_id,
                    pair[1].form,
                ),
            ):
                if (
                    donor_sentence.document_id == source_sentence.document_id
                    or donor_token.form.lower() == source_token.form.lower()
                ):
                    continue
                left_document = f"{source}:{source_sentence.document_id}"
                right_document = f"{source}:{donor_sentence.document_id}"
                document_pair = tuple(
                    sorted((left_document, right_document), key=lambda value: value.encode("utf-8"))
                )
                candidate_id = stable_hex(
                    NAMESPACE,
                    "proper-candidate",
                    seed,
                    source,
                    source_sentence.document_id,
                    source_sentence.sent_id,
                    source_token.token_id,
                    donor_sentence.document_id,
                    donor_sentence.sent_id,
                    donor_token.token_id,
                )
                existing = proper_edge_candidates.get(document_pair)
                if existing is not None and str(existing["candidate_id"]).encode("utf-8") <= candidate_id.encode("utf-8"):
                    continue
                replacement = list(words)
                replacement[source_word_index] = donor_token.form
                encoded = tokenizer(
                    replacement,
                    is_split_into_words=True,
                    add_special_tokens=False,
                    truncation=False,
                )
                target_ids = list(map(int, encoded["input_ids"]))
                target_word_ids = list(encoded.word_ids())
                if len(target_ids) != len(source_layout["input_ids"]) or target_word_ids != source_layout["word_ids"]:
                    continue
                changed = [
                    index
                    for index, (left, right) in enumerate(zip(source_layout["input_ids"], target_ids, strict=True))
                    if left != right
                ]
                if changed != [source_position]:
                    continue
                proper_edge_candidates[document_pair] = {
                    "candidate_id": candidate_id,
                    "left_document": left_document,
                    "right_document": right_document,
                    "source_sentence": source_sentence,
                    "source_token": source_token,
                    "donor_sentence": donor_sentence,
                    "donor_token": donor_token,
                    "source_ids": source_layout["input_ids"],
                    "target_ids": target_ids,
                    "changed_position": source_position,
                    "control_token_id": control_token_id,
                    "fold": fold,
                    "stratum": stratum,
                }
        selected_proper, proper_match_report = maximum_cardinality_document_matching(
            list(proper_edge_candidates.values())
        )
        for candidate in selected_proper:
            source_sentence = candidate["source_sentence"]
            source_token = candidate["source_token"]
            donor_sentence = candidate["donor_sentence"]
            donor_token = candidate["donor_token"]
            source_ids = candidate["source_ids"]
            target_ids = candidate["target_ids"]
            changed_position = int(candidate["changed_position"])
            control_token_id = int(candidate["control_token_id"])
            fold = int(candidate["fold"])
            stratum = candidate["stratum"]
            source_layout = layouts[source_sentence.sent_id]
            pair_id = stable_hex(
                NAMESPACE,
                "proper-pair",
                seed,
                source,
                source_sentence.document_id,
                source_sentence.sent_id,
                source_token.token_id,
                donor_sentence.document_id,
                donor_token.form,
            )[:24]
            control_position = int(source_layout["first_positions"][control_token_id])
            row_map: dict[str, dict[str, str]] = {}
            for condition, ids in (("source", source_ids), ("target", target_ids)):
                changed_row = f"{NAMESPACE}:intervention:{pair_id}:{condition}:changed"
                control_row = f"{NAMESPACE}:intervention:{pair_id}:{condition}:control"
                add_unit(
                    unit_id=f"{NAMESPACE}:intervention:{pair_id}:{condition}",
                    kind=f"proper_noun_{condition}",
                    input_ids=ids,
                    position_ids=list(range(len(ids))),
                    targets=(
                        (changed_row, changed_position, "changed"),
                        (control_row, control_position, "control"),
                    ),
                )
                row_map[condition] = {"changed": changed_row, "control": control_row}
            source_token_labels = _main_labels(
                source_sentence,
                source_token,
                changed_position,
                int(source_layout["untruncated_length"]),
            )
            component_documents = sorted(
                (str(candidate["left_document"]), str(candidate["right_document"])),
                key=lambda value: value.encode("utf-8"),
            )
            intervention_pairs.append(
                {
                    "pair_id": pair_id,
                    "construct": "proper_noun_substitution",
                    "source": source,
                    "document_group": f"{source}:{source_sentence.document_id}",
                    "donor_document_group": f"{source}:{donor_sentence.document_id}",
                    "component_id": "component:proper:" + stable_hex(*component_documents)[:24],
                    "component_documents": component_documents,
                    "fold": fold,
                    "sent_id": source_sentence.sent_id,
                    "source_document_length": len(by_document[source_sentence.document_id]),
                    "source_token_id": source_token.token_id,
                    "control_token_id": control_token_id,
                    "source_form": source_token.form,
                    "donor_form": donor_token.form,
                    "stratum": {
                        "capitalization": stratum[1],
                        "number": stratum[2],
                        "frequency_quartile": stratum[3],
                    },
                    "target_metadata": {
                        key: source_token_labels[key]
                        for key in ("start_distance", "upos_coarse", "capitalization", "word_length", "sentence_length")
                    },
                    "rows": row_map,
                }
            )

        if config.get("qa_only_compact") is True:
            selected_pairs: list[dict[str, Any]] = []
            used_documents: set[str] = set()
            used_components: set[str] = set()
            for construct, quota in (("context_factorial", 8), ("relative_gap", 8)):
                candidates = sorted(
                    (row for row in intervention_pairs if row["construct"] == construct),
                    key=lambda row: stable_digest(
                        "atlas_discovery_v3_3_attempt7", "fresh-qa", source, construct, row["pair_id"]
                    ),
                )
                chosen = 0
                for row in candidates:
                    documents = {
                        str(row[key])
                        for key in ("document_group", "donor_document_group")
                        if row.get(key) is not None
                    }
                    component = str(row["component_id"])
                    if documents & used_documents or component in used_components:
                        continue
                    selected_pairs.append(row)
                    used_documents.update(documents)
                    used_components.add(component)
                    chosen += 1
                    if chosen == quota:
                        break
                if chosen != quota:
                    raise RuntimeError(f"insufficient compact QA pairs: {source}/{construct}")
            selected_row_ids: set[str] = set()
            def collect_ids(value: Any) -> None:
                if isinstance(value, str):
                    selected_row_ids.add(value)
                elif isinstance(value, Mapping):
                    for child in value.values():
                        collect_ids(child)
            for pair in selected_pairs:
                collect_ids(pair["rows"])
            selected_units = [
                unit for unit in intervention_units if any(str(row_id) in selected_row_ids for row_id in unit["row_ids"])
            ]
            if any(not set(map(str, unit["row_ids"])).issubset(selected_row_ids) for unit in selected_units):
                raise RuntimeError("compact QA unit contains an unrelated activation row")
            selected_rows = [row for row in intervention_rows if str(row["row_id"]) in selected_row_ids]
            if [row_id for unit in selected_units for row_id in unit["row_ids"]] != [row["row_id"] for row in selected_rows]:
                raise RuntimeError("compact QA row/unit ordering drift")
            source_root = prepared_root / source
            units_sha, units_count = atomic_write_jsonl(source_root / "inference_units.jsonl", selected_units)
            rows_sha, rows_count = atomic_write_jsonl(source_root / "activation_rows.jsonl", selected_rows)
            pairs_sha, pairs_count = atomic_write_jsonl(source_root / "intervention_pairs.jsonl", selected_pairs)
            manifest["sources"][source] = {
                "role": "technical_numerical_qa_only",
                "documents": len(used_documents),
                "units": units_count,
                "activation_rows": rows_count,
                "intervention_pairs": pairs_count,
                "units_sha256": units_sha,
                "activation_rows_sha256": rows_sha,
                "intervention_pairs_sha256": pairs_sha,
                "pair_ids": [row["pair_id"] for row in selected_pairs],
                "component_ids": sorted(used_components),
                "document_ids": sorted(used_documents),
            }
            continue

        joint_rows, joint_population_report = build_joint_cross_family_rows(
            intervention_pairs,
            source=source,
            seed=seed,
            allowed_joint_cells=allowed_joint_cells,
        )
        joint_support = joint_cross_family_support_report(
            joint_rows,
            joint_population_report,
            source=source,
            seed=seed,
            thresholds={
                **config["cross_family"],
                "folds": int(config["data"]["folds"]),
            },
            bootstrap_draws=int(config["support"]["bootstrap_draws"]),
            minimum_finite_draws=int(config["support"]["min_finite_draws"]),
        )
        joint_rows_by_source[source] = joint_rows

        all_units = main_units + intervention_units
        all_rows = activation_rows + intervention_rows
        flattened = [row_id for unit in all_units for row_id in unit["row_ids"]]
        expected = [row["row_id"] for row in all_rows]
        if flattened != expected:
            raise RuntimeError(f"activation row/unit ordering drift for {source}")

        source_root = prepared_root / source
        units_sha, units_count = atomic_write_jsonl(source_root / "inference_units.jsonl", all_units)
        rows_sha, rows_count = atomic_write_jsonl(source_root / "activation_rows.jsonl", all_rows)
        pair_sha, pair_count = atomic_write_jsonl(source_root / "pair_rows.jsonl", pair_rows)
        relation_sha, relation_count = atomic_write_jsonl(source_root / "relation_rows.jsonl", relation_rows)
        intervention_sha, intervention_count = atomic_write_jsonl(
            source_root / "intervention_pairs.jsonl", intervention_pairs
        )
        joint_sha, joint_count = atomic_write_jsonl(
            source_root / "cross_family_rows.jsonl", joint_rows
        )
        task_manifest: dict[str, Any] = {}
        support: dict[str, Any] = {}
        for task, candidates in main_candidates.items():
            capped = _group_cap_task_rows(
                candidates,
                maximum=int(config["support"]["max_rows_per_group"]),
                seed=seed,
            )
            task_sha, task_count = atomic_write_jsonl(source_root / "tasks" / f"{task}.jsonl", capped)
            expected_labels = PRIMARY_TOKEN_VOCABULARY if task == "token_identity" else None
            support[task] = support_report(
                capped,
                source=source,
                task=task,
                thresholds=config["support"],
                seed=seed,
                expected_labels=expected_labels,
            )
            task_manifest[task] = {"sha256": task_sha, "rows": task_count}
        pair_support = support_report(
            pair_rows,
            source=source,
            task="pair_distance",
            thresholds=config["support"],
            seed=seed,
        )
        support["pair_distance"] = pair_support
        task_manifest["pair_distance"] = {"sha256": pair_sha, "rows": pair_count}

        intervention_counts: dict[str, Any] = {}
        for construct in ("relative_gap", "context_factorial", "proper_noun_substitution"):
            selected = [row for row in intervention_pairs if row["construct"] == construct]
            components = {row["component_id"] for row in selected}
            per_fold = Counter(int(row["fold"]) for row in selected)
            expected_folds = range(int(config["data"]["folds"]))
            reasons: list[str] = []
            if len(components) < int(config["interventions"]["min_components"]):
                reasons.append("components_below_minimum")
            if any(
                per_fold.get(fold, 0)
                < int(config["interventions"]["min_components_per_fold"])
                for fold in expected_folds
            ):
                reasons.append("fold_components_below_minimum")
            if construct == "relative_gap":
                if any(row["component_id"] != row["document_group"] for row in selected):
                    raise RuntimeError("relative-gap endpoint lost singleton document components")
                if len(components) != len({row["document_group"] for row in selected}):
                    raise RuntimeError("relative-gap component/document count drift")
                matching_report: Mapping[str, Any] | None = None
            else:
                used_documents: list[str] = []
                for row in selected:
                    documents = list(map(str, row.get("component_documents", [])))
                    if len(documents) != 2 or len(set(documents)) != 2:
                        raise RuntimeError(f"invalid two-document {construct} component")
                    used_documents.extend(documents)
                if len(used_documents) != len(set(used_documents)):
                    raise RuntimeError(f"document reused across {construct} components")
                if len(components) != len(selected):
                    raise RuntimeError(f"non-disjoint component IDs for {construct}")
                matching_report = (
                    context_match_report
                    if construct == "context_factorial"
                    else proper_match_report
                )
            intervention_counts[construct] = {
                "pairs": len(selected),
                "components": len(components),
                "components_by_fold": {
                    str(fold): per_fold.get(fold, 0) for fold in expected_folds
                },
                "matching": matching_report,
                "status": "eligible" if not reasons else "ineligible",
                "reasons": reasons,
            }
        relation_components = {row["component_id"] for row in relation_rows}
        if any(row["component_id"] != row["document_group"] for row in relation_rows):
            raise RuntimeError("relational endpoint lost singleton document components")
        intervention_counts["relational_contrast"] = {
            "pairs": len(relation_rows),
            "components": len(relation_components),
            "components_by_fold": {
                str(fold): len(
                    {
                        row["component_id"]
                        for row in relation_rows
                        if stable_fold(
                            source,
                            str(row["document_group"]).split(":", 1)[1],
                            seed=seed,
                            folds=int(config["data"]["folds"]),
                        )
                        == fold
                    }
                )
                for fold in range(int(config["data"]["folds"]))
            },
            "status": "eligible"
            if len(relation_components) >= int(config["interventions"]["min_components"])
            else "ineligible",
            "reasons": []
            if len(relation_components) >= int(config["interventions"]["min_components"])
            else ["components_below_minimum"],
        }

        manifest["sources"][source] = {
            "sentences": len(sentences),
            "documents": len(by_document),
            "paragraphs": len({row.paragraph_id for row in sentences if row.paragraph_id}),
            "units": units_count,
            "activation_rows": rows_count,
            "pair_rows": pair_count,
            "relation_rows": relation_count,
            "intervention_pairs": intervention_count,
            "cross_family_rows": joint_count,
            "units_sha256": units_sha,
            "activation_rows_sha256": rows_sha,
            "relation_rows_sha256": relation_sha,
            "intervention_pairs_sha256": intervention_sha,
            "cross_family_rows_sha256": joint_sha,
            "tasks": task_manifest,
            "support": support,
            "interventions": intervention_counts,
            "cross_family_specificity": joint_support,
            "exclusions": {**parse_exclusions[source], **layout_exclusions},
        }

    if config.get("qa_only_compact") is True:
        manifest["schema_version"] = "atlas_discovery_v3_3_attempt7_qa_compact_prepared_v1"
        manifest["role"] = "technical_numerical_qa_only"
        manifest_sha = atomic_write_json(prepared_root / "manifest.json", manifest)
        preflight = {
            "schema_version": "atlas_discovery_v3_3_attempt7_qa_compact_preflight_v1",
            "status": "COMPLETE",
            "prepared_manifest_sha256": manifest_sha,
            "representation_scoring_run": False,
            "neural_inference_run": False,
            "neural_training_run": False,
            "allowed_files_per_source": ["activation_rows.jsonl", "inference_units.jsonl", "intervention_pairs.jsonl"],
        }
        atomic_write_json(data_root / "preflight.json", preflight)
        return manifest

    common_support: dict[str, Any] = {}
    common_config = config["cross_family"]["common_support"]
    for fit_source, heldout_source in (("EWT", "GUM"), ("GUM", "EWT")):
        fit_rows = joint_rows_by_source[fit_source]
        heldout_rows = joint_rows_by_source[heldout_source]
        fit_cells = {
            tuple(row["stratum"][field] for field in config["cross_family"]["strata"])
            for row in fit_rows
        }
        class_reports: dict[str, Any] = {}
        reasons: list[str] = []
        for class_label in config["cross_family"]["classes"]:
            selected = [row for row in heldout_rows if row["class_label"] == class_label]
            common_rows = [
                row
                for row in selected
                if tuple(row["stratum"][field] for field in config["cross_family"]["strata"])
                in fit_cells
            ]
            unseen = len(selected) - len(common_rows)
            unseen_rate = unseen / len(selected) if selected else 1.0
            common_documents = {str(row["document_group"]) for row in common_rows}
            class_reasons: list[str] = []
            if unseen_rate > float(common_config["max_unseen_joint_cell_rate"]):
                class_reasons.append("unseen_joint_cell_rate_above_maximum")
            if len(common_rows) < int(common_config["min_common_rows_per_class"]):
                class_reasons.append("common_rows_below_minimum")
            if len(common_documents) < int(common_config["min_common_target_documents_per_class"]):
                class_reasons.append("common_target_documents_below_minimum")
            reasons.extend(f"{class_label}:{reason}" for reason in class_reasons)
            class_reports[class_label] = {
                "heldout_rows": len(selected),
                "unseen_joint_cell_rows": unseen,
                "unseen_joint_cell_rate": unseen_rate,
                "common_rows": len(common_rows),
                "common_target_documents": len(common_documents),
                "status": "eligible" if not class_reasons else "ineligible",
                "reasons": class_reasons,
            }
        common_support[f"{fit_source}_to_{heldout_source}"] = {
            "status": "eligible" if not reasons else "ineligible",
            "reasons": reasons,
            "fit_joint_cells": len(fit_cells),
            "classes": class_reports,
            "required_scientific_check": "full_and_fit_observed_subset_incremental_effect_same_positive_sign",
        }
    manifest["cross_source_common_support"] = common_support

    manifest_sha = atomic_write_json(prepared_root / "manifest.json", manifest)
    preflight = {
        "schema_version": "atlas_discovery_v3_3_attempt7_qa_pool_preflight_v1",
        "config_sha256": manifest["config_sha256"],
        "prepared_manifest_sha256": manifest_sha,
        "representation_scoring_run": False,
        "neural_training_run": False,
        "sources": {
            source: {
                "sentences": row["sentences"],
                "documents": row["documents"],
                "support": row["support"],
                "interventions": row["interventions"],
                "cross_family_specificity": row["cross_family_specificity"],
            }
            for source, row in manifest["sources"].items()
        },
        "cross_source_common_support": common_support,
        "all_required_measurement_populations_eligible": all(
            endpoint["status"] == "eligible"
            for source_row in manifest["sources"].values()
            for task, endpoint in source_row["support"].items()
            if task
            in {
                "start_distance",
                "relative_quartile",
                "head_signed_distance",
                "dependency_depth",
                "deprel_coarse",
                "token_identity",
                "pair_distance",
            }
        )
        and all(
            endpoint["status"] == "eligible"
            for source_row in manifest["sources"].values()
            for endpoint in source_row["interventions"].values()
        )
        and all(
            source_row["cross_family_specificity"]["status"] == "eligible"
            for source_row in manifest["sources"].values()
        )
        and all(endpoint["status"] == "eligible" for endpoint in common_support.values()),
    }
    atomic_write_json(data_root / "preflight.json", preflight)
    return manifest


def build_prepared_data(config: Mapping[str, Any], config_path: Path) -> dict[str, Any]:
    """Build only the external technical-QA position-translation challenge.

    This entry point intentionally does not invoke any of the science-population
    constructors retained above for historical comparison.  It emits only the
    relative-gap and context-factorial rows needed for numerical QA.
    """

    from transformers import AutoTokenizer

    repository_root = config_path.resolve().parents[2]
    expected_root = "data/atlas_discovery_v3_3_attempt7_qa_compact_v3"
    if config.get("qa_only_compact") is not True:
        raise RuntimeError("attempt7 external QA builder requires qa_only_compact=true")
    if str(config.get("data_root")) != expected_root:
        raise RuntimeError("attempt7 external QA builder requires its exact v2 technical-only namespace")
    data_root = repository_root / expected_root
    if data_root.exists():
        manifest_path = data_root / "prepared" / "manifest.json"
        if manifest_path.exists():
            manifest = read_json(manifest_path)
            if manifest.get("config_sha256") != sha256_file(config_path):
                raise RuntimeError("existing prepared QA data belongs to a different config")
            return manifest
        raise RuntimeError(f"refusing partially existing data root: {data_root}")

    data_root.mkdir(parents=True)
    process_snapshot = {
        "schema_version": "atlas_discovery_v3_3_attempt7_qa_compact_v3_process_snapshot_v1",
        "argv": sys.argv,
        "cwd": str(Path.cwd()),
        "executable": sys.executable,
        "platform": platform.platform(),
        "pid": os.getpid(),
        "process_table": subprocess.run(
            ["ps", "-eo", "pid=,ppid=,lstart=,args="],
            check=True,
            capture_output=True,
            text=True,
        ).stdout.splitlines(),
    }
    atomic_write_json(data_root / "process_snapshot_preopen.json", process_snapshot)

    source_paths = resolve_source_inputs(config, repository_root=repository_root)
    opened_input_ledger = {
        "schema_version": "atlas_discovery_v3_3_attempt7_qa_compact_v3_opened_input_ledger_v1",
        "scope": "external_devtest_technical_numerical_qa_only_no_scientific_population_construction",
        "config": {
            "path": str(config_path.relative_to(repository_root)),
            "sha256": sha256_file(config_path),
            "role": "technical_qa_builder_configuration",
        },
        "protocol": {
            "path": str(config["protocol"]["path"]),
            "sha256": sha256_file(repository_root / str(config["protocol"]["path"])),
            "role": "technical_qa_protocol",
        },
        "sources": {
            name: {
                "path": str(path.relative_to(repository_root)),
                "sha256": sha256_file(path),
                "role": "external_devtest_technical_numerical_qa_only",
            }
            for name, path in source_paths.items()
        },
        "model": {
            "name": str(config["model"]["name"]),
            "revision": str(config["model"]["revision"]),
            "role": "pinned_tokenizer_only_during_label_only_build",
        },
        "constructed_families": ["context_factorial", "relative_gap"],
        "persisted_conditions": {
            "context_factorial": ["bare", "prefix_position_only"],
            "relative_gap": ["bare", "uniform_shift"],
        },
        "science_population_constructors_invoked": False,
        "scientific_or_activation_outcomes_opened": False,
        "forbidden_or_blind_inputs_opened": False,
    }
    opened_input_ledger_sha = atomic_write_json(
        data_root / "opened_input_ledger.json", opened_input_ledger
    )

    model_spec = config["model"]
    tokenizer = AutoTokenizer.from_pretrained(
        str(model_spec["name"]),
        revision=str(model_spec["revision"]),
        local_files_only=True,
    )
    max_length = int(config["data"]["max_length"])
    seed = int(config["seed"])
    parse_exclusions: dict[str, dict[str, int]] = {"EWT": {}, "GUM": {}}
    parsed = {
        name: parse_conllu(path, name, exclusion_counts=parse_exclusions[name])
        for name, path in source_paths.items()
    }
    raw_sentence_counts = {name: len(rows) for name, rows in parsed.items()}
    duplicates = set(map(sentence_content_hash, parsed["EWT"])) & set(
        map(sentence_content_hash, parsed["GUM"])
    )
    if duplicates:
        parsed = {
            name: [row for row in rows if sentence_content_hash(row) not in duplicates]
            for name, rows in parsed.items()
        }

    prepared_root = data_root / "prepared"
    manifest: dict[str, Any] = {
        "schema_version": "atlas_discovery_v3_3_attempt7_qa_compact_v3_prepared_v1",
        "role": "external_devtest_technical_numerical_qa_only",
        "config_sha256": sha256_file(config_path),
        "protocol_sha256": sha256_file(repository_root / str(config["protocol"]["path"])),
        "source_input_sha256": {name: sha256_file(path) for name, path in source_paths.items()},
        "process_snapshot_preopen_path": "process_snapshot_preopen.json",
        "opened_input_ledger_sha256": opened_input_ledger_sha,
        "cross_source_duplicate_hashes_excluded": len(duplicates),
        "constructed_families": ["context_factorial", "relative_gap"],
        "persisted_conditions": {
            "context_factorial": ["bare", "prefix_position_only"],
            "relative_gap": ["bare", "uniform_shift"],
        },
        "science_population_constructors_invoked": False,
        "sources": {},
    }

    for source in ("EWT", "GUM"):
        sentences = parsed[source]
        layouts = {
            sentence.sent_id: token_layout(tokenizer, sentence, max_length)
            for sentence in sentences
        }
        by_document: dict[str, list[Sentence]] = defaultdict(list)
        for sentence in sentences:
            by_document[sentence.document_id].append(sentence)

        intervention_units: list[dict[str, Any]] = []
        intervention_rows: list[dict[str, Any]] = []
        intervention_pairs: list[dict[str, Any]] = []

        def add_unit(
            *,
            unit_id: str,
            kind: str,
            input_ids: Sequence[int],
            position_ids: Sequence[int],
            targets: Sequence[tuple[str, int, str]],
        ) -> None:
            if len(input_ids) != len(position_ids) or len(input_ids) > max_length:
                raise RuntimeError(f"invalid technical-QA intervention unit layout: {unit_id}")
            positions: list[int] = []
            row_ids: list[str] = []
            for row_id, position, role in targets:
                if not 0 <= position < len(input_ids):
                    raise RuntimeError(f"technical-QA target outside input: {unit_id}:{position}")
                positions.append(int(position))
                row_ids.append(row_id)
                intervention_rows.append(
                    {
                        "row_id": row_id,
                        "source": source,
                        "kind": kind,
                        "target_role": role,
                    }
                )
            intervention_units.append(
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

        # One label-blind sequential target per genuine document.  Only the
        # bare/uniform-shift null and relative-gap condition are constructed.
        sequential_targets: list[Sentence] = []
        for document, rows in by_document.items():
            candidates = [
                row
                for row in rows
                if layouts[row.sent_id]["complete"]
                and len(layouts[row.sent_id]["input_ids"]) >= 4
                and len(layouts[row.sent_id]["first_positions"]) >= 2
            ]
            if candidates:
                sequential_targets.append(
                    min(
                        candidates,
                        key=lambda row: stable_digest(
                            NAMESPACE,
                            "sequential-target",
                            seed,
                            source,
                            document,
                            row.sent_id,
                        ),
                    )
                )
        for sentence in sequential_targets:
            layout = layouts[sentence.sent_id]
            input_ids = layout["input_ids"]
            pivot = len(input_ids) // 2
            before = [
                (token_id, pos)
                for token_id, pos in layout["first_positions"].items()
                if pos < pivot
            ]
            after = [
                (token_id, pos)
                for token_id, pos in layout["first_positions"].items()
                if pos >= pivot
            ]
            if not before or not after:
                continue
            pre_id, pre_pos = min(
                before,
                key=lambda item: stable_digest(
                    NAMESPACE, "gap-pre", seed, source, sentence.sent_id, item[0]
                ),
            )
            post_id, post_pos = min(
                after,
                key=lambda item: stable_digest(
                    NAMESPACE, "gap-post", seed, source, sentence.sent_id, item[0]
                ),
            )
            pair_id = stable_hex(
                NAMESPACE, "sequential-pair", seed, source, sentence.document_id
            )[:24]
            condition_rows: dict[str, dict[str, str]] = {}
            condition_specs = {
                "bare": {"input_ids": input_ids, "position_ids": list(range(len(input_ids)))},
                "uniform_shift": {
                    "input_ids": input_ids,
                    "position_ids": [
                        int(config["interventions"]["position_shift"]) + index
                        for index in range(len(input_ids))
                    ],
                },
            }
            for condition in ("bare", "uniform_shift"):
                spec = condition_specs[condition]
                rows_map = {
                    "pre": f"{NAMESPACE}:intervention:{pair_id}:{condition}:pre",
                    "post": f"{NAMESPACE}:intervention:{pair_id}:{condition}:post",
                }
                add_unit(
                    unit_id=f"{NAMESPACE}:intervention:{pair_id}:{condition}",
                    kind=condition,
                    input_ids=spec["input_ids"],
                    position_ids=spec["position_ids"],
                    targets=(
                        (rows_map["pre"], pre_pos, "pre"),
                        (rows_map["post"], post_pos, "post"),
                    ),
                )
                condition_rows[condition] = rows_map
            intervention_pairs.append(
                {
                    "pair_id": pair_id,
                    "construct": "relative_gap",
                    "source": source,
                    "document_group": f"{source}:{sentence.document_id}",
                    "component_id": f"{source}:{sentence.document_id}",
                    "fold": stable_fold(
                        source,
                        sentence.document_id,
                        seed=seed,
                        folds=int(config["data"]["folds"]),
                    ),
                    "sent_id": sentence.sent_id,
                    "pivot": pivot,
                    "pre_token_id": pre_id,
                    "post_token_id": post_id,
                    "rows": condition_rows,
                }
            )

        # One natural-prefix target per document, with a document-disjoint donor.
        context_targets: list[tuple[Sentence, Sentence]] = []
        for document, rows in by_document.items():
            candidates: list[tuple[Sentence, Sentence]] = []
            for previous, target in zip(rows, rows[1:], strict=False):
                left, right = layouts[previous.sent_id], layouts[target.sent_id]
                if not (left["complete"] and right["complete"]):
                    continue
                if len(right["input_ids"]) < 2:
                    continue
                if len(left["input_ids"]) + 1 + len(right["input_ids"]) > max_length:
                    continue
                eligible_tokens = [
                    token.token_id
                    for token in target.tokens
                    if token.token_id in right["first_positions"] and token.upos != "PUNCT"
                ]
                if eligible_tokens:
                    candidates.append((previous, target))
            if candidates:
                context_targets.append(
                    min(
                        candidates,
                        key=lambda pair: stable_digest(
                            NAMESPACE,
                            "context-target",
                            seed,
                            source,
                            document,
                            pair[1].sent_id,
                        ),
                    )
                )
        donors_by_fold_length: dict[tuple[int, int], list[Sentence]] = defaultdict(list)
        for donor in sentences:
            layout = layouts[donor.sent_id]
            if layout["complete"]:
                fold = stable_fold(
                    source,
                    donor.document_id,
                    seed=seed,
                    folds=int(config["data"]["folds"]),
                )
                donors_by_fold_length[(fold, len(layout["input_ids"]))].append(donor)
        context_candidates: list[dict[str, Any]] = []
        for previous, target in sorted(
            context_targets,
            key=lambda pair: stable_digest(
                NAMESPACE, "context-order", seed, source, pair[1].document_id
            ),
        ):
            true_layout = layouts[previous.sent_id]
            fold = stable_fold(
                source,
                target.document_id,
                seed=seed,
                folds=int(config["data"]["folds"]),
            )
            donors = [
                donor
                for donor in donors_by_fold_length[(fold, len(true_layout["input_ids"]))]
                if donor.document_id != target.document_id
                and sentence_content_hash(donor) != sentence_content_hash(previous)
            ]
            for donor in sorted(
                donors,
                key=lambda row: stable_digest(
                    NAMESPACE,
                    "context-donor",
                    seed,
                    source,
                    target.document_id,
                    target.sent_id,
                    row.document_id,
                    row.sent_id,
                ),
            ):
                context_candidates.append(
                    {
                        "candidate_id": stable_hex(
                            NAMESPACE,
                            "context-candidate",
                            seed,
                            source,
                            target.document_id,
                            target.sent_id,
                            donor.document_id,
                            donor.sent_id,
                        ),
                        "left_document": f"{source}:{target.document_id}",
                        "right_document": f"{source}:{donor.document_id}",
                        "previous": previous,
                        "target": target,
                        "donor": donor,
                        "fold": fold,
                    }
                )
        selected_context, _ = maximum_cardinality_document_matching(context_candidates)
        for candidate in selected_context:
            previous = candidate["previous"]
            target = candidate["target"]
            donor = candidate["donor"]
            fold = int(candidate["fold"])
            true_layout, target_layout = layouts[previous.sent_id], layouts[target.sent_id]
            target_ids = [
                token.token_id
                for token in target.tokens
                if token.token_id in target_layout["first_positions"] and token.upos != "PUNCT"
            ]
            target_token_id = _pick_token_by_hash(target, target_ids, "context-token", seed)
            if target_token_id is None:
                raise RuntimeError("matched technical-QA context target lost every aligned token")
            target_position = int(target_layout["first_positions"][target_token_id])
            pair_id = stable_hex(
                NAMESPACE,
                "context-pair",
                seed,
                source,
                target.document_id,
                target.sent_id,
            )[:24]
            condition_rows: dict[str, str] = {}
            shift_length = len(true_layout["input_ids"]) + 1
            condition_specs = {
                "bare": {
                    "input_ids": target_layout["input_ids"],
                    "position_ids": list(range(len(target_layout["input_ids"]))),
                },
                "prefix_position_only": {
                    "input_ids": target_layout["input_ids"],
                    "position_ids": [
                        shift_length + index
                        for index in range(len(target_layout["input_ids"]))
                    ],
                },
            }
            for condition in ("bare", "prefix_position_only"):
                spec = condition_specs[condition]
                unit_target_position = target_position
                row_id = f"{NAMESPACE}:intervention:{pair_id}:{condition}:target"
                add_unit(
                    unit_id=f"{NAMESPACE}:intervention:{pair_id}:{condition}",
                    kind=condition,
                    input_ids=spec["input_ids"],
                    position_ids=spec["position_ids"],
                    targets=((row_id, unit_target_position, "target"),),
                )
                condition_rows[condition] = row_id
            component_documents = sorted(
                (str(candidate["left_document"]), str(candidate["right_document"])),
                key=lambda value: value.encode("utf-8"),
            )
            intervention_pairs.append(
                {
                    "pair_id": pair_id,
                    "construct": "context_factorial",
                    "source": source,
                    "document_group": f"{source}:{target.document_id}",
                    "donor_document_group": f"{source}:{donor.document_id}",
                    "component_id": "component:context:"
                    + stable_hex(*component_documents)[:24],
                    "component_documents": component_documents,
                    "fold": fold,
                    "target_sent_id": target.sent_id,
                    "true_prefix_sent_id": previous.sent_id,
                    "unrelated_prefix_sent_id": donor.sent_id,
                    "prefix_length": len(true_layout["input_ids"]),
                    "target_token_id": target_token_id,
                    "rows": condition_rows,
                }
            )

        # Freeze exactly 8 context and 8 relative challenges without document or
        # component reuse, using the attempt-level salt specified by the protocol.
        selected_pairs: list[dict[str, Any]] = []
        used_documents: set[str] = set()
        used_components: set[str] = set()
        for construct, quota in (("context_factorial", 8), ("relative_gap", 8)):
            candidates = sorted(
                (row for row in intervention_pairs if row["construct"] == construct),
                key=lambda row: stable_digest(
                    "atlas_discovery_v3_3_attempt7",
                    "fresh-qa",
                    source,
                    construct,
                    row["pair_id"],
                ),
            )
            chosen = 0
            for row in candidates:
                documents = {
                    str(row[key])
                    for key in ("document_group", "donor_document_group")
                    if row.get(key) is not None
                }
                component = str(row["component_id"])
                if documents & used_documents or component in used_components:
                    continue
                selected_pairs.append(row)
                used_documents.update(documents)
                used_components.add(component)
                chosen += 1
                if chosen == quota:
                    break
            if chosen != quota:
                raise RuntimeError(f"insufficient compact technical-QA pairs: {source}/{construct}")

        selected_row_ids: set[str] = set()

        def collect_ids(value: Any) -> None:
            if isinstance(value, str):
                selected_row_ids.add(value)
            elif isinstance(value, Mapping):
                for child in value.values():
                    collect_ids(child)

        for pair in selected_pairs:
            collect_ids(pair["rows"])
        selected_units = [
            unit
            for unit in intervention_units
            if any(str(row_id) in selected_row_ids for row_id in unit["row_ids"])
        ]
        if any(
            not set(map(str, unit["row_ids"])).issubset(selected_row_ids)
            for unit in selected_units
        ):
            raise RuntimeError("compact technical-QA unit contains an unrelated activation row")
        selected_rows = [
            row for row in intervention_rows if str(row["row_id"]) in selected_row_ids
        ]
        flattened_row_ids = [
            str(row_id) for unit in selected_units for row_id in unit["row_ids"]
        ]
        ordered_row_ids = [str(row["row_id"]) for row in selected_rows]
        if flattened_row_ids != ordered_row_ids:
            raise RuntimeError("compact technical-QA row/unit ordering drift")
        if len(ordered_row_ids) != len(set(ordered_row_ids)):
            raise RuntimeError("duplicate compact technical-QA activation row")

        source_root = prepared_root / source
        units_sha, units_count = atomic_write_jsonl(
            source_root / "inference_units.jsonl", selected_units
        )
        rows_sha, rows_count = atomic_write_jsonl(
            source_root / "activation_rows.jsonl", selected_rows
        )
        pairs_sha, pairs_count = atomic_write_jsonl(
            source_root / "intervention_pairs.jsonl", selected_pairs
        )
        exact_files = {
            path.name for path in source_root.iterdir() if path.is_file()
        }
        expected_files = {
            "activation_rows.jsonl",
            "inference_units.jsonl",
            "intervention_pairs.jsonl",
        }
        if exact_files != expected_files or any(path.is_dir() for path in source_root.iterdir()):
            raise RuntimeError(f"technical-QA source artifact allowlist drift: {source}")
        manifest["sources"][source] = {
            "role": "external_devtest_technical_numerical_qa_only",
            "raw_sentences": raw_sentence_counts[source],
            "cross_source_duplicate_sentences_excluded": raw_sentence_counts[source]
            - len(sentences),
            "documents": len(used_documents),
            "units": units_count,
            "activation_rows": rows_count,
            "intervention_pairs": pairs_count,
            "units_sha256": units_sha,
            "activation_rows_sha256": rows_sha,
            "intervention_pairs_sha256": pairs_sha,
            "pair_ids": [row["pair_id"] for row in selected_pairs],
            "component_ids": sorted(used_components),
            "document_ids": sorted(used_documents),
            "construct_counts": {
                construct: sum(row["construct"] == construct for row in selected_pairs)
                for construct in ("context_factorial", "relative_gap")
            },
        }

    manifest_sha = atomic_write_json(prepared_root / "manifest.json", manifest)
    preflight = {
        "schema_version": "atlas_discovery_v3_3_attempt7_qa_compact_v3_preflight_v1",
        "status": "COMPLETE",
        "config_sha256": manifest["config_sha256"],
        "prepared_manifest_sha256": manifest_sha,
        "role": "external_devtest_technical_numerical_qa_only",
        "representation_scoring_run": False,
        "neural_inference_run": False,
        "neural_training_run": False,
        "science_population_constructors_invoked": False,
        "allowed_files_per_source": [
            "activation_rows.jsonl",
            "inference_units.jsonl",
            "intervention_pairs.jsonl",
        ],
    }
    atomic_write_json(data_root / "preflight.json", preflight)
    return manifest
