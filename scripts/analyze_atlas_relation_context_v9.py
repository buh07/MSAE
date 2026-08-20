#!/usr/bin/env python3
"""Analyze Attempt-13 caches with ephemeral cross-source ridge scorers."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Mapping, Sequence

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))

from atlas_discovery_v3_3_analysis import (
    choose_alpha,
    fit_ridge,
    macro_f1,
    normalized_recovery,
    prior_chance,
)
from atlas_relation_context_v9 import (
    CONFIG,
    PREPARED_ROOT,
    RESULT_ROOT,
    ROOT,
    RUN_ROOT,
    atomic_json,
    component_multiplicities,
    interval,
    normalized_delta,
    read_json,
    read_jsonl,
    relation_norm_audit,
    sha256_file,
)


SOURCES = ("GENTLE", "CTETEX")
TASKS = ("dependency_depth", "deprel_coarse", "head_signed_distance")
VARIANTS = ("child", "true", "sham", "sequential_offset")


class SourceData:
    def __init__(self, source: str) -> None:
        self.source = source
        cache = RUN_ROOT / "activations" / source
        self.row_ids = [row["row_id"] for row in read_jsonl(cache / "row_ids.jsonl")]
        self.index = {row_id: index for index, row_id in enumerate(self.row_ids)}
        if len(self.index) != len(self.row_ids):
            raise RuntimeError(f"duplicate cache row IDs: {source}")
        self.x = np.load(cache / "activations.float32.npy", mmap_mode="r", allow_pickle=False)
        if self.x.dtype != np.float32 or self.x.shape != (len(self.row_ids), 768) or not np.isfinite(self.x).all():
            raise RuntimeError(f"invalid activation cache: {source}")
        self.relations = read_jsonl(PREPARED_ROOT / source / "relation_rows.jsonl")
        referenced = {
            str(row[key])
            for row in self.relations
            for key in (
                "child_row_id",
                "head_row_id",
                "sham_row_id",
                "donor_child_row_id",
                "donor_candidate_row_id",
            )
        }
        if not referenced.issubset(self.index):
            raise RuntimeError(f"relation/cache foreign-key drift: {source}")

    def matrix(self, rows: Sequence[Mapping[str, Any]], variant: str) -> np.ndarray:
        child = np.asarray([self.x[self.index[str(row["child_row_id"])]] for row in rows], dtype=np.float64)
        if variant == "child":
            return child
        if variant == "true":
            candidate = np.asarray([self.x[self.index[str(row["head_row_id"])]] for row in rows], dtype=np.float64)
            delta = candidate - child
        elif variant == "sham":
            candidate = np.asarray([self.x[self.index[str(row["sham_row_id"])]] for row in rows], dtype=np.float64)
            delta = candidate - child
        elif variant == "sequential_offset":
            donor_child = np.asarray([self.x[self.index[str(row["donor_child_row_id"])]] for row in rows], dtype=np.float64)
            donor_candidate = np.asarray([self.x[self.index[str(row["donor_candidate_row_id"])]] for row in rows], dtype=np.float64)
            delta = donor_candidate - donor_child
        else:
            raise KeyError(variant)
        return np.concatenate([child, delta], axis=1)

    def norm_values(self) -> dict[str, np.ndarray]:
        child = np.asarray([self.x[self.index[str(row["child_row_id"])]] for row in self.relations], dtype=np.float64)
        head = np.asarray([self.x[self.index[str(row["head_row_id"])]] for row in self.relations], dtype=np.float64)
        sham = np.asarray([self.x[self.index[str(row["sham_row_id"])]] for row in self.relations], dtype=np.float64)
        donor_child = np.asarray([self.x[self.index[str(row["donor_child_row_id"])]] for row in self.relations], dtype=np.float64)
        donor_candidate = np.asarray([self.x[self.index[str(row["donor_candidate_row_id"])]] for row in self.relations], dtype=np.float64)
        return {
            "true": normalized_delta(head, child),
            "sham": normalized_delta(sham, child),
            "sequential_offset": normalized_delta(donor_candidate, donor_child),
        }


def _post_norm_support(rows: Sequence[Mapping[str, Any]], task: str, classes: Sequence[str], seed: int) -> dict[str, Any]:
    selected = [row for row in rows if str(row["labels"][task]) in classes]
    targets = {str(row["document_group"]) for row in selected}
    donors = {str(row["donor_document_group"]) for row in selected}
    components = sorted({str(row["component_id"]) for row in selected}, key=lambda value: value.encode("utf-8"))
    class_docs = {
        label: len({str(row["document_group"]) for row in selected if str(row["labels"][task]) == label})
        for label in classes
    }
    finite = 0
    for draw in range(500):
        multiplicities = component_multiplicities(components, direction="post-norm", endpoint=task, draw=draw, seed=seed)
        if all(
            sum(multiplicities.get(str(row["component_id"]), 0) for row in selected if str(row["labels"][task]) == label) > 0
            for label in classes
        ):
            finite += 1
    cv_training_complete = all(
        {
            str(row["labels"][task])
            for row in selected
            if int(row["fold"]) != fold
        }
        == set(classes)
        for fold in range(5)
    )
    eligible = (
        len(targets) >= 20
        and len(donors) >= 20
        and len(components) >= 10
        and all(class_docs[label] >= 10 for label in classes)
        and finite >= 490
        and cv_training_complete
    )
    return {
        "rows": len(selected),
        "target_documents": len(targets),
        "donor_documents": len(donors),
        "document_pair_components": len(components),
        "class_documents": class_docs,
        "finite_component_bootstrap_draws": finite,
        "cv_training_classes_complete": cv_training_complete,
        "eligible": eligible,
    }


def _weighted_intervals(
    rows: Sequence[Mapping[str, Any]],
    y_fit: np.ndarray,
    y_test: np.ndarray,
    predictions: Mapping[str, np.ndarray],
    classes: Sequence[str],
    *,
    direction: str,
    task: str,
    seed: int,
) -> dict[str, Any]:
    components = sorted({str(row["component_id"]) for row in rows}, key=lambda value: value.encode("utf-8"))
    draws: dict[str, list[float]] = {name: [] for name in ("raw_recovery", "true_minus_child", "true_minus_sham", "true_minus_sequential_offset")}
    for draw in range(500):
        multiplicities = component_multiplicities(components, direction=direction, endpoint=f"relation:{task}", draw=draw, seed=seed)
        weights = np.asarray([multiplicities.get(str(row["component_id"]), 0) for row in rows], dtype=np.float64)
        if any(weights[y_test == label].sum() <= 0 for label in classes):
            for values in draws.values():
                values.append(float("nan"))
            continue
        scores = {name: macro_f1(y_test, prediction, classes, weights) for name, prediction in predictions.items()}
        chance = prior_chance(y_fit, y_test, classes, weights)
        draws["raw_recovery"].append(normalized_recovery(scores["true"], chance))
        draws["true_minus_child"].append(scores["true"] - scores["child"])
        draws["true_minus_sham"].append(scores["true"] - scores["sham"])
        draws["true_minus_sequential_offset"].append(scores["true"] - scores["sequential_offset"])
    return {name: interval(values) for name, values in draws.items()}


def _evaluate_direction(
    fit: SourceData,
    test: SourceData,
    fit_rows: Sequence[Mapping[str, Any]],
    test_rows: Sequence[Mapping[str, Any]],
    task: str,
    classes: Sequence[str],
    config: Mapping[str, Any],
) -> dict[str, Any]:
    y_fit = np.asarray([str(row["labels"][task]) for row in fit_rows], dtype=str)
    y_test = np.asarray([str(row["labels"][task]) for row in test_rows], dtype=str)
    folds = np.asarray([int(row["fold"]) for row in fit_rows], dtype=int)
    predictions: dict[str, np.ndarray] = {}; alpha: dict[str, Any] = {}
    for variant in VARIANTS:
        x_fit = fit.matrix(fit_rows, variant); x_test = test.matrix(test_rows, variant)
        selected, grid = choose_alpha(
            x_fit,
            y_fit,
            folds,
            classes,
            config["analysis"]["alphas"],
            device=str(config["analysis"]["ridge_device"]),
            scale_floor=float(config["analysis"]["scale_floor"]),
        )
        model = fit_ridge(
            x_fit,
            y_fit,
            classes,
            selected,
            device=str(config["analysis"]["ridge_device"]),
            scale_floor=float(config["analysis"]["scale_floor"]),
        )
        predictions[variant] = model.predict(x_test)
        alpha[variant] = {"selected": selected, "cv_macro_f1": grid}
        del model
    scores = {variant: macro_f1(y_test, predictions[variant], classes) for variant in VARIANTS}
    chance = prior_chance(y_fit, y_test, classes)
    raw_recovery = normalized_recovery(scores["true"], chance)
    margins = {variant: scores["true"] - scores[variant] for variant in ("child", "sham", "sequential_offset")}
    direction = f"{fit.source}_to_{test.source}"
    intervals = _weighted_intervals(test_rows, y_fit, y_test, predictions, classes, direction=direction, task=task, seed=int(config["seed"]))
    raw_pass = (
        raw_recovery >= float(config["analysis"]["raw_normalized_recovery_minimum"])
        and intervals["raw_recovery"]["finite"] >= 490
        and intervals["raw_recovery"]["lower"] is not None
        and intervals["raw_recovery"]["lower"] > 0
    )
    isolation_pass = all(
        margins[variant] >= float(config["relation"]["margin_minimum"])
        and intervals[f"true_minus_{variant}"]["finite"] >= 490
        and intervals[f"true_minus_{variant}"]["lower"] is not None
        and intervals[f"true_minus_{variant}"]["lower"] > 0
        for variant in ("child", "sham", "sequential_offset")
    )
    classification = "isolated" if raw_pass and isolation_pass else ("decodable_not_isolated" if raw_pass else "not_demonstrated_decodable")
    return {
        "direction": direction,
        "task": task,
        "rows_fit": len(fit_rows),
        "rows_test": len(test_rows),
        "classes": list(classes),
        "macro_f1": scores,
        "chance_macro_f1": chance,
        "raw_normalized_recovery": raw_recovery,
        "margins": margins,
        "intervals": intervals,
        "alpha": alpha,
        "raw_decodability_pass": raw_pass,
        "isolation_pass": isolation_pass,
        "classification": classification,
        "eligible": True,
        "pass": raw_pass and isolation_pass,
    }


def analyze(config_path: Path) -> dict[str, Any]:
    config = read_json(config_path); manifest = read_json(PREPARED_ROOT / "manifest.json")
    if manifest.get("config_sha256") != sha256_file(config_path) or not manifest.get("authorization_eligible"):
        raise RuntimeError("prescore/config authorization drift")
    data = {source: SourceData(source) for source in SOURCES}
    norm_audits: dict[str, Any] = {}; informative_rows: dict[str, list[dict[str, Any]]] = {}
    for source in SOURCES:
        values = data[source].norm_values()
        audit = relation_norm_audit(
            values,
            threshold=float(config["relation_delta"]["informative_strictly_greater_than"]),
            maximum_rate=float(config["relation_delta"]["maximum_noninformative_rate"]),
        )
        mask = np.asarray(audit.pop("informative_mask"), dtype=bool)
        informative_rows[source] = [row for row, keep in zip(data[source].relations, mask, strict=True) if keep]
        norm_audits[source] = {
            **audit,
            "variant_quantiles": {
                name: {str(q): float(np.quantile(array, q)) for q in (0, 0.001, 0.01, 0.5, 0.99, 1.0)}
                for name, array in values.items()
            },
        }

    post_support: dict[str, dict[str, Any]] = {}; relation_eligible = True
    for source in SOURCES:
        post_support[source] = {}
        for task in TASKS:
            classes = manifest["sources"][source]["relation_support"]["tasks"][task]["classes"]
            post_support[source][task] = _post_norm_support(informative_rows[source], task, classes, int(config["seed"]))
            relation_eligible &= bool(norm_audits[source]["cap_pass"] and post_support[source][task]["eligible"])

    directions: dict[str, dict[str, Any]] = {}
    if relation_eligible:
        for fit_source, test_source in (("GENTLE", "CTETEX"), ("CTETEX", "GENTLE")):
            key = f"{fit_source}_to_{test_source}"; directions[key] = {}
            for task in TASKS:
                classes = tuple(manifest["sources"][fit_source]["relation_support"]["tasks"][task]["classes"])
                fit_rows = [row for row in informative_rows[fit_source] if str(row["labels"][task]) in classes]
                test_rows = [row for row in informative_rows[test_source] if str(row["labels"][task]) in classes]
                directions[key][task] = _evaluate_direction(data[fit_source], data[test_source], fit_rows, test_rows, task, classes, config)
    primary_pass = relation_eligible and all(row["pass"] for tasks in directions.values() for row in tasks.values())
    primary_status = "passed" if primary_pass else ("eligible_not_passed" if relation_eligible else "ineligible")

    secondary_reasons = {
        source: {
            "tasks": manifest["sources"][source]["task_support"],
            "interventions": manifest["sources"][source]["intervention_support"],
        }
        for source in SOURCES
        if not manifest["sources"][source]["secondary_prescore_eligible"]
    }
    secondary = {
        "status": "prescore_ineligible" if secondary_reasons else "not_implemented_for_unexpected_manifest",
        "eligible": False,
        "pass": False,
        "reasons": secondary_reasons,
        "scientific_scores_computed": False,
        "missingness_does_not_invalidate_relational_module": True,
    }
    if primary_pass:
        decision = "NOMINATE_LATER_RELATION_AWARE_COMPARISON"
    elif relation_eligible and all(row["raw_decodability_pass"] for tasks in directions.values() for row in tasks.values()):
        decision = "RELATIONAL_SIGNALS_DECODABLE_BUT_NOT_ISOLATED"
    elif relation_eligible:
        decision = "RELATIONAL_DECODABILITY_NOT_DEMONSTRATED_FOR_ALL_PRESPECIFIED_TASKS"
    else:
        decision = "RELATIONAL_ENDPOINT_INELIGIBLE"
    result = {
        "schema_version": "atlas_relation_context_v9_attempt13_result_v1",
        "status": "COMPLETE",
        "claim_scope": config["claim_scope"],
        "sources": list(SOURCES),
        "model": config["model"],
        "relation_delta_audit": norm_audits,
        "post_norm_support": post_support,
        "primary_relational_syntax": {"status": primary_status, "eligible": relation_eligible, "pass": primary_pass, "directions": directions},
        "secondary_sequential_context": secondary,
        "decision": decision,
        "training_authorized": False,
        "neural_training_run": False,
        "representation_training_run": False,
        "ephemeral_ridge_score_estimation_run": bool(relation_eligible),
        "fitted_probe_weights_persisted": False,
        "claim_limitations": [
            "exploratory and non-confirmatory",
            "sources are endpoint-outcome-naive with prior technical inference exposure",
            "collision rule was prescore-support-amended but endpoint-outcome-blind",
            "one model checkpoint and layer only",
            "secondary module structurally prescore-ineligible and not scientifically scored",
        ],
    }
    RESULT_ROOT.mkdir(parents=True, exist_ok=False)
    atomic_json(RESULT_ROOT / "result.json", result)
    lines = [
        "# Attempt 13 relational/context results",
        "",
        f"- Decision: **{decision}**",
        f"- Primary relational syntax: **{primary_status}**",
        "- Secondary sequential/context: **prescore ineligible** (reported separately)",
        "- Neural/representation training: **not run and not authorized**",
        "",
        "## Relational directions",
    ]
    for direction, tasks in directions.items():
        lines.append(f"\n### {direction}")
        for task, row in tasks.items():
            lines.append(
                f"- `{task}`: {row['classification']}; true F1={row['macro_f1']['true']:.4f}; "
                f"margins child/sham/sequential={row['margins']['child']:.4f}/"
                f"{row['margins']['sham']:.4f}/{row['margins']['sequential_offset']:.4f}."
            )
    (RESULT_ROOT / "report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return result


def main() -> None:
    parser = argparse.ArgumentParser(); parser.add_argument("--config", default=str(CONFIG.relative_to(ROOT))); args = parser.parse_args()
    result = analyze((ROOT / args.config).resolve()); print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
