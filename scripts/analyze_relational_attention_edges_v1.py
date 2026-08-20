#!/usr/bin/env python3
"""Frozen transfer analysis for the relational QK-link discovery study."""
from __future__ import annotations

import json
import hashlib
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any, Mapping, Sequence

import numpy as np
from sklearn.metrics import balanced_accuracy_score, f1_score, roc_auc_score
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import RidgeClassifier

sys.path.insert(0, str(Path(__file__).resolve().parent))

from relational_attention_edges_v1 import ROOT, finite_interval, read_json, read_jsonl


PRIMARY_FEATURES = ("qk", "residual", "combined")
DESCRIPTIVE_FEATURES = ("attention", "transport", "value")


def _pipeline(config: Mapping[str, Any], alpha: float) -> Pipeline:
    scaler = config["analysis"]["scaler"]
    ridge = config["analysis"]["ridge"]
    return Pipeline(
        [
            ("scale", StandardScaler(**scaler)),
            ("ridge", RidgeClassifier(alpha=float(alpha), **ridge)),
        ]
    )


def _validate_binary(y: np.ndarray) -> None:
    if y.ndim != 1 or y.dtype.kind not in "iu" or set(np.unique(y).tolist()) != {0, 1}:
        raise ValueError("binary labels must be a rank-one integer array containing both classes")


def _feature(cache: Mapping[str, np.ndarray], name: str) -> np.ndarray:
    if name == "combined":
        value = np.concatenate((cache["residual"], cache["qk"]), axis=1)
        if value.ndim != 2 or not np.isfinite(value).all():
            raise ValueError("invalid combined feature matrix")
        return value
    if name not in (*PRIMARY_FEATURES, *DESCRIPTIVE_FEATURES):
        raise KeyError(name)
    value = np.asarray(cache[name], dtype=np.float64)
    if value.ndim != 2 or not np.isfinite(value).all():
        raise ValueError(f"invalid feature matrix: {name}")
    return value


def _select_alpha_binary(
    X: np.ndarray, y: np.ndarray, folds: np.ndarray, config: Mapping[str, Any]
) -> dict[str, Any]:
    _validate_binary(y)
    rows: list[dict[str, Any]] = []
    for alpha in config["analysis"]["alphas"]:
        scores: list[float] = []
        valid = True
        for fold in range(int(config["matching"]["folds"])):
            train, validation = folds != fold, folds == fold
            if not train.any() or not validation.any() or len(np.unique(y[train])) != 2 or len(np.unique(y[validation])) != 2:
                valid = False
                break
            model = _pipeline(config, float(alpha))
            model.fit(X[train], y[train])
            score = np.asarray(model.decision_function(X[validation]), dtype=np.float64)
            if not np.isfinite(score).all():
                valid = False
                break
            scores.append(float(roc_auc_score(y[validation], score)))
        rows.append({"alpha": float(alpha), "valid": valid, "fold_auc": scores, "mean_auc": float(np.mean(scores)) if valid else None})
    valid_rows = [row for row in rows if row["valid"]]
    if not valid_rows:
        raise RuntimeError("no valid binary alpha")
    selected = max(valid_rows, key=lambda row: (float(row["mean_auc"]), float(row["alpha"])))
    return {"selected_alpha": float(selected["alpha"]), "candidates": rows}


def _fit_binary(
    train: Mapping[str, np.ndarray], test: Mapping[str, np.ndarray], name: str, config: Mapping[str, Any]
) -> dict[str, Any]:
    X_train, X_test = _feature(train, name), _feature(test, name)
    y_train, y_test = np.asarray(train["label"], dtype=np.int64), np.asarray(test["label"], dtype=np.int64)
    _validate_binary(y_train)
    _validate_binary(y_test)
    folds = np.asarray(train["fold"], dtype=np.int64)
    selection = _select_alpha_binary(X_train, y_train, folds, config)
    model = _pipeline(config, selection["selected_alpha"])
    model.fit(X_train, y_train)
    scores = np.asarray(model.decision_function(X_test), dtype=np.float64)
    predictions = np.asarray(model.predict(X_test), dtype=np.int64)
    if not np.isfinite(scores).all():
        raise RuntimeError(f"nonfinite held-out scores: {name}")
    return {
        "feature": name,
        "selection": selection,
        "auc": float(roc_auc_score(y_test, scores)),
        "balanced_accuracy": float(balanced_accuracy_score(y_test, predictions)),
        "scores": scores,
    }


def _fit_relation(
    train: Mapping[str, np.ndarray],
    test: Mapping[str, np.ndarray],
    train_examples: Sequence[Mapping[str, Any]],
    test_examples: Sequence[Mapping[str, Any]],
    name: str,
    classes: Sequence[str],
    config: Mapping[str, Any],
) -> dict[str, Any]:
    train_indices = np.asarray([index for index, row in enumerate(train_examples) if int(row["label"]) == 1 and row["relation"] in classes], dtype=np.int64)
    test_indices = np.asarray([index for index, row in enumerate(test_examples) if int(row["label"]) == 1 and row["relation"] in classes], dtype=np.int64)
    y_train = np.asarray([train_examples[index]["relation"] for index in train_indices])
    y_test = np.asarray([test_examples[index]["relation"] for index in test_indices])
    folds = np.asarray(train["fold"], dtype=np.int64)[train_indices]
    X_train, X_test = _feature(train, name)[train_indices], _feature(test, name)[test_indices]
    if set(np.unique(y_train)) != set(classes) or set(np.unique(y_test)) != set(classes):
        return {"eligible": False, "reason": "missing_fit_or_test_class"}
    candidates = []
    for alpha in config["analysis"]["alphas"]:
        fold_f1: list[float] = []
        valid = True
        for fold in range(int(config["matching"]["folds"])):
            fit, validation = folds != fold, folds == fold
            if set(np.unique(y_train[validation])) != set(classes) or set(np.unique(y_train[fit])) != set(classes):
                valid = False
                break
            model = _pipeline(config, float(alpha))
            model.fit(X_train[fit], y_train[fit])
            prediction = model.predict(X_train[validation])
            fold_f1.append(float(f1_score(y_train[validation], prediction, labels=list(classes), average="macro", zero_division=0)))
        candidates.append({"alpha": float(alpha), "valid": valid, "fold_macro_f1": fold_f1, "mean_macro_f1": float(np.mean(fold_f1)) if valid else None})
    valid_rows = [row for row in candidates if row["valid"]]
    if not valid_rows:
        return {"eligible": False, "reason": "no_alpha_with_all_classes_in_every_fold", "candidates": candidates}
    selected = max(valid_rows, key=lambda row: (float(row["mean_macro_f1"]), float(row["alpha"])))
    model = _pipeline(config, selected["alpha"])
    model.fit(X_train, y_train)
    prediction = model.predict(X_test)
    return {"eligible": True, "selected_alpha": selected["alpha"], "candidates": candidates, "macro_f1": float(f1_score(y_test, prediction, labels=list(classes), average="macro", zero_division=0)), "classes": list(classes)}


def _component_expansion(examples: Sequence[Mapping[str, Any]], components: Sequence[str], index_row: np.ndarray) -> np.ndarray:
    component_index = {value: index for index, value in enumerate(components)}
    counts = np.bincount(np.asarray(index_row, dtype=np.int64), minlength=len(components))
    expanded: list[int] = []
    for row_index, row in enumerate(examples):
        multiplicity = int(counts[component_index[str(row["component_id"])]])
        if multiplicity:
            expanded.extend([row_index] * multiplicity)
    return np.asarray(expanded, dtype=np.int64)


def _bootstrap_binary(
    examples: Sequence[Mapping[str, Any]],
    pairs: Sequence[Mapping[str, Any]],
    maps: np.ndarray,
    scores: Mapping[str, np.ndarray],
    config: Mapping[str, Any],
) -> dict[str, Any]:
    components = sorted({str(row["component_id"]) for row in examples}, key=lambda value: value.encode("utf-8"))
    if maps.shape != (int(config["analysis"]["bootstrap_draws"]), len(components)):
        raise ValueError("bootstrap-map shape drift")
    labels = np.asarray([int(row["label"]) for row in examples], dtype=np.int64)
    pair_by_component: dict[str, list[Mapping[str, Any]]] = defaultdict(list)
    for pair in pairs:
        pair_by_component[str(pair["component_id"])].append(pair)
    draws: dict[str, list[float]] = {"qk_auc": [], "residual_auc": [], "combined_auc": [], "gain": [], "directionality": []}
    for index_row in maps:
        expanded = _component_expansion(examples, components, index_row)
        if not expanded.size or len(np.unique(labels[expanded])) != 2:
            for values in draws.values():
                values.append(float("nan"))
            continue
        try:
            qk_auc = float(roc_auc_score(labels[expanded], scores["qk"][expanded]))
            residual_auc = float(roc_auc_score(labels[expanded], scores["residual"][expanded]))
            combined_auc = float(roc_auc_score(labels[expanded], scores["combined"][expanded]))
        except ValueError:
            qk_auc = residual_auc = combined_auc = float("nan")
        counts = np.bincount(np.asarray(index_row, dtype=np.int64), minlength=len(components))
        wins, total = 0, 0
        for component_index, component in enumerate(components):
            multiplicity = int(counts[component_index])
            if not multiplicity:
                continue
            for pair in pair_by_component[component]:
                edge, nonedge = int(pair["edge_index"]), int(pair["nonedge_index"])
                wins += multiplicity * int(scores["qk"][edge] > scores["qk"][nonedge])
                total += multiplicity
        direction = float(wins / total) if total else float("nan")
        draws["qk_auc"].append(qk_auc)
        draws["residual_auc"].append(residual_auc)
        draws["combined_auc"].append(combined_auc)
        draws["gain"].append(combined_auc - residual_auc)
        draws["directionality"].append(direction)
    return {name: finite_interval(values, config) for name, values in draws.items()}


def _paired_swap_null(
    examples: Sequence[Mapping[str, Any]], pairs: Sequence[Mapping[str, Any]], swaps: np.ndarray, qk_scores: np.ndarray, config: Mapping[str, Any]
) -> dict[str, Any]:
    if swaps.shape != (int(config["analysis"]["bootstrap_draws"]), len(pairs)):
        raise ValueError("paired-swap map shape drift")
    labels = np.asarray([row["label"] for row in examples], dtype=np.int64)
    values = []
    for bits in swaps:
        permuted = np.array(qk_scores, copy=True)
        for bit, pair in zip(bits, pairs):
            if int(bit):
                edge, nonedge = int(pair["edge_index"]), int(pair["nonedge_index"])
                permuted[edge], permuted[nonedge] = permuted[nonedge], permuted[edge]
        values.append(float(roc_auc_score(labels, permuted)))
    observed = float(roc_auc_score(labels, qk_scores))
    array = np.asarray(values, dtype=np.float64)
    return {
        "role": "DESCRIPTIVE_PAIRED_LABEL_SWAP_NO_REFIT",
        "observed_qk_auc": observed,
        "draws": int(array.size),
        "mean": float(array.mean()),
        "lower": float(np.quantile(array, 0.025, method=config["analysis"]["quantile_method"])),
        "upper": float(np.quantile(array, 0.975, method=config["analysis"]["quantile_method"])),
        "upper_tail_fraction": float((1 + np.sum(array >= observed)) / (1 + array.size)),
    }


def decision_from_primary(directions: Mapping[str, Mapping[str, Any]], config: Mapping[str, Any]) -> dict[str, Any]:
    """Gate only on z, r and [r,z]; descriptive normalized attention is unreachable."""
    gates: dict[str, Any] = {}
    for direction, result in directions.items():
        qk = result["models"]["qk"]
        residual = result["models"]["residual"]
        combined = result["models"]["combined"]
        intervals = result["intervals"]
        point_gain = float(combined["auc"] - residual["auc"])
        point_direction = float(result["directionality"])
        gate = {
            "measurability": bool(result["measurable"] and all(intervals[name]["eligible"] for name in ("qk_auc", "gain", "directionality"))),
            "qk_recovery": bool(qk["auc"] >= config["analysis"]["qk_auc_minimum"] and intervals["qk_auc"].get("lower", -np.inf) > config["analysis"]["qk_auc_lower_minimum"]),
            "increment": bool(point_gain >= config["analysis"]["combined_minus_residual_minimum"] and intervals["gain"].get("lower", -np.inf) > 0.0),
            "directionality": bool(point_direction >= config["analysis"]["paired_direction_minimum"] and intervals["directionality"].get("lower", -np.inf) > config["analysis"]["paired_direction_lower_minimum"]),
        }
        gate["all"] = all(gate.values())
        gate["point_gain"] = point_gain
        gates[direction] = gate
    if not all(value["measurability"] for value in gates.values()):
        decision = "RELATIONAL_EDGE_STUDY_INELIGIBLE"
    elif not all(value["qk_recovery"] for value in gates.values()):
        decision = "MATCHED_QK_LINK_SIGNAL_NOT_DEMONSTRATED"
    elif not all(value["increment"] and value["directionality"] for value in gates.values()):
        decision = "MATCHED_QK_LINK_DETECTABLE_NOT_INCREMENTAL"
    else:
        decision = "MATCHED_QK_LINK_INCREMENTAL_PREDICTIVE_DISCOVERY"
    return {"decision": decision, "gates": gates, "gate_feature_reachability": ["qk", "residual", "combined"]}


def _distribution(values: np.ndarray) -> dict[str, Any]:
    values = np.asarray(values, dtype=np.float64)
    return {"n": int(values.size), "mean": float(values.mean()), "std": float(values.std(ddof=1)), "min": float(values.min()), "max": float(values.max())}


def _unmatched_distributions(examples: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    output: dict[str, Any] = {"role": "UNMATCHED_NON_GATING_POTENTIAL_CONFOUNDERS"}
    for field in ("query_index", "sequence_length"):
        by_class = {str(label): _distribution(np.asarray([row[field] for row in examples if int(row["label"]) == label])) for label in (0, 1)}
        pooled = np.sqrt((by_class["0"]["std"] ** 2 + by_class["1"]["std"] ** 2) / 2.0)
        by_class["standardized_mean_difference_edge_minus_nonedge"] = ((by_class["1"]["mean"] - by_class["0"]["mean"]) / pooled) if pooled else 0.0
        output[field] = by_class
    return output


def _strip_scores(value: Mapping[str, Any]) -> dict[str, Any]:
    return {key: item for key, item in value.items() if key != "scores"}


def _load_cache(path: Path) -> dict[str, np.ndarray]:
    with np.load(path, allow_pickle=False) as archive:
        return {key: np.array(archive[key], copy=True) for key in archive.files}


def analyze(config: Mapping[str, Any], cache_root: Path) -> dict[str, Any]:
    prepared = ROOT / config["paths"]["prepared_root"]
    sources: dict[str, dict[str, Any]] = {}
    for source in sorted(config["sources"]):
        examples = read_jsonl(prepared / source / "examples.jsonl")
        pairs = read_jsonl(prepared / source / "pairs.jsonl")
        cache = _load_cache(cache_root / f"{source}.features.npz")
        n = len(examples)
        expected = {"qk": (n, 12), "attention": (n, 12), "transport": (n, 768), "value": (n, 768), "residual": (n, 1536), "label": (n,), "fold": (n,)}
        for name, shape in expected.items():
            if name not in cache or cache[name].shape != shape or not np.isfinite(cache[name]).all():
                raise RuntimeError(f"cache contract failure: {source}:{name}")
        expected_indices = np.arange(n, dtype=np.int64)
        expected_id_hashes = np.asarray(
            [hashlib.sha256(str(row["example_id"]).encode("utf-8")).digest() for row in examples], dtype="|S32"
        )
        if (
            "example_index" not in cache
            or "example_id_sha256" not in cache
            or not np.array_equal(cache["example_index"], expected_indices)
            or not np.array_equal(cache["example_id_sha256"], expected_id_hashes)
        ):
            raise RuntimeError(f"cache explicit row-ID lineage failure: {source}")
        frozen_labels = np.asarray([row["label"] for row in examples], dtype=np.int64)
        frozen_folds = np.asarray([row["fold"] for row in examples], dtype=np.int64)
        if not np.array_equal(cache["label"], frozen_labels) or not np.array_equal(cache["fold"], frozen_folds):
            raise RuntimeError(f"cache row lineage failure: {source}")
        sources[source] = {"examples": examples, "pairs": pairs, "cache": cache, "unmatched": _unmatched_distributions(examples)}

    source_names = sorted(sources)
    relation_sets = [set(read_json(prepared / source / "support.json")["retained_relation_classes"]) for source in sorted(sources)]
    frozen_relation_classes = sorted(set.intersection(*relation_sets), key=lambda value: value.encode("utf-8"))
    directions: dict[str, Any] = {}
    for fit_source, test_source in ((source_names[0], source_names[1]), (source_names[1], source_names[0])):
        train, test = sources[fit_source], sources[test_source]
        models = {name: _fit_binary(train["cache"], test["cache"], name, config) for name in (*PRIMARY_FEATURES, *DESCRIPTIVE_FEATURES)}
        qk_scores = models["qk"]["scores"]
        wins = [qk_scores[int(pair["edge_index"])] > qk_scores[int(pair["nonedge_index"])] for pair in test["pairs"]]
        maps = np.load(prepared / test_source / "bootstrap_indices.uint32.npy", allow_pickle=False)
        intervals = _bootstrap_binary(test["examples"], test["pairs"], maps, {name: models[name]["scores"] for name in PRIMARY_FEATURES}, config)
        swap_maps = np.load(prepared / test_source / "paired_swap.uint8.npy", allow_pickle=False)
        relation = {
            name: _fit_relation(train["cache"], test["cache"], train["examples"], test["examples"], name, frozen_relation_classes, config)
            for name in PRIMARY_FEATURES
        }
        direction_key = f"{fit_source}_to_{test_source}"
        directions[direction_key] = {
            "fit_source": fit_source,
            "test_source": test_source,
            "measurable": True,
            "models": {name: _strip_scores(model) for name, model in models.items()},
            "intervals": intervals,
            "directionality": float(np.mean(wins)),
            "paired_swap_null": _paired_swap_null(test["examples"], test["pairs"], swap_maps, qk_scores, config),
            "relation_macro_f1": relation,
            "test_unmatched_potential_confounders": test["unmatched"],
        }
    decision = decision_from_primary(directions, config)
    return {
        "schema_version": "relational_attention_edges_v1_result_v1",
        "scope": "EXPLORATORY_MATCHED_CROSS_SOURCE_PREDICTIVE_ASSOCIATION",
        "directions": directions,
        "frozen_relation_classes": frozen_relation_classes,
        **decision,
        "claim_limits": [
            "No isolation or causal-attention-mechanism claim is authorized.",
            "Absolute query index and sequence length are unmatched non-gating potential confounders.",
            "Intervals condition on the exact fit-source estimator.",
            "No neural or representation model was trained.",
        ],
    }


def main() -> None:
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("config", type=Path)
    parser.add_argument("cache_root", type=Path)
    args = parser.parse_args()
    config = read_json(args.config)
    print(json.dumps(analyze(config, args.cache_root), sort_keys=True, indent=2))


if __name__ == "__main__":
    main()
