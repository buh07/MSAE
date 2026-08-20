#!/usr/bin/env python3
"""Run the Atlas/MSAE v2 label-only public support audit.

This command cannot select roles, row roots, manifests, or output paths from the
command line.  Those values and every input digest are bound by the reviewed v2
configuration.  It performs no representation loading or model scoring.
"""

from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
import os
from pathlib import Path
import shutil
import sys
from typing import Any, Mapping, Sequence

from msae_measurement_v2 import (
    SupportThresholds,
    aggregate_endpoint_records,
    aggregate_statuses,
    audit_task_support,
    cap_rows_by_group,
    canonical_json_bytes,
    identity_document_frequencies,
    map_row_labels,
    resolve_allowlisted_inputs,
    select_identity_vocabulary,
    sha256_file,
    source_from_group,
    summarize_rows_by_source,
    validate_measurement_config,
    validate_output_root,
    verify_freeze_record,
)


ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = ROOT / "configs" / "atlas_measurement_v2" / "prescore.json"
CONFIG_SHA256 = "ba12af946448b31fe6657e87a1e1e8c906b1bcf88c2c42a4e973e2b888a191dc"
PROTECTED_SNAPSHOT_ROOTS = (
    "pilot_runs",
    "results",
    "data/atlas_completion_v1",
    "configs/atlas_completion",
)
EXPERIMENT_PROCESS_MARKERS = (
    b"train_msae",
    b"run_msae_",
    b"extract_atlas_activations",
    b"torchrun",
    b"accelerate launch",
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", required=True, help="must be configs/atlas_measurement_v2/prescore.json")
    return parser.parse_args()


def _load_bound_config(raw_path: str) -> dict[str, Any]:
    supplied = Path(raw_path)
    candidate = supplied if supplied.is_absolute() else ROOT / supplied
    if candidate.is_symlink() or candidate.resolve(strict=True) != CONFIG_PATH.resolve(strict=True):
        raise ValueError(f"only the reviewed config is accepted: {CONFIG_PATH.relative_to(ROOT)}")
    resolve_allowlisted_inputs(
        ROOT,
        [{"path": CONFIG_PATH.relative_to(ROOT).as_posix(), "sha256": CONFIG_SHA256}],
        [CONFIG_PATH.parent],
    )
    value = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    validate_measurement_config(value)
    if value.get("schema_version") != "atlas_measurement_v2_prescore_draft":
        raise ValueError("measurement config schema mismatch")
    if value.get("status") != "draft_prescore_only_no_scoring":
        raise ValueError("config is not restricted to draft prescore auditing")
    return value


def _thresholds(config: Mapping[str, Any]) -> SupportThresholds:
    raw = config["thresholds"]
    return SupportThresholds(
        min_groups=int(raw["min_groups"]),
        min_class_groups=int(raw["min_class_groups"]),
        max_rows_per_group=int(raw["max_rows_per_group"]),
        bootstrap_draws=int(raw["bootstrap_draws"]),
        min_finite_draws=int(raw["min_finite_draws"]),
        seed=int(raw["seed"]),
    )


def _snapshot_paths() -> list[str]:
    paths: list[str] = []
    for relative_root in PROTECTED_SNAPSHOT_ROOTS:
        root = ROOT / relative_root
        if root.is_symlink() or not root.exists():
            raise ValueError(f"protected snapshot root missing or symlinked: {relative_root}")
        if root.is_file():
            paths.append(relative_root)
            continue
        for directory, directory_names, filenames in os.walk(root, followlinks=False):
            directory_names.sort()
            filenames.sort()
            directory_path = Path(directory)
            if any((directory_path / name).is_symlink() for name in directory_names + filenames):
                raise ValueError(f"symlink found beneath protected snapshot root: {relative_root}")
            paths.extend((directory_path / name).relative_to(ROOT).as_posix() for name in filenames)
    return sorted(paths)


def _process_snapshot() -> dict[str, Any]:
    entries: list[dict[str, Any]] = []
    experiment_matches: list[dict[str, Any]] = []
    proc = Path("/proc")
    if not proc.is_dir():
        return {"available": False, "processes": [], "experiment_matches": []}
    for child in sorted((path for path in proc.iterdir() if path.name.isdigit()), key=lambda path: int(path.name)):
        try:
            if child.stat().st_uid != os.getuid():
                continue
            command = (child / "cmdline").read_bytes()
        except (FileNotFoundError, PermissionError, ProcessLookupError):
            continue
        entry = {
            "pid": int(child.name),
            "cmdline_sha256": hashlib.sha256(command).hexdigest(),
            "is_audit_process": b"audit_msae_measurement_v2.py" in command,
        }
        entries.append(entry)
        markers = [marker.decode("ascii") for marker in EXPERIMENT_PROCESS_MARKERS if marker in command]
        if markers:
            experiment_matches.append({**entry, "markers": markers})
    return {"available": True, "processes": entries, "experiment_matches": experiment_matches}


def _require_clean_process_snapshot(snapshot: Mapping[str, Any], *, stage: str) -> None:
    if snapshot.get("available") is not True:
        raise ValueError(f"process evidence is unavailable {stage}; audit fails closed")
    if snapshot.get("experiment_matches"):
        raise ValueError(f"an experiment-like process was active {stage} the prescore audit")


def _load_rows(path: Path, entry: Mapping[str, Any], prefix_map: Mapping[str, Mapping[str, str]]) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            raw = json.loads(line)
            for field in ("document_group", "label", "row_id"):
                if field not in raw:
                    raise ValueError(f"{entry['path']}:{line_number} lacks {field}")
            group = str(raw["document_group"])
            derived_source = source_from_group(group, str(entry["role"]), prefix_map)
            if entry["tier"] == "tier2":
                if str(raw.get("source")) != derived_source:
                    raise ValueError(f"{entry['path']}:{line_number} source disagrees with group prefix")
            elif "source" in raw and str(raw["source"]) != derived_source:
                raise ValueError(f"{entry['path']}:{line_number} unexpected Tier-1 source disagreement")
            rows.append(
                {
                    "document_group": group,
                    "source": derived_source,
                    "label": str(raw["label"]),
                    "row_id": str(raw["row_id"]),
                }
            )
    return rows


def _annotate_analytic_omission(source_reports: Mapping[str, dict[str, Any]]) -> None:
    for source_report in source_reports.values():
        groups = int(source_report["groups"])
        probabilities: dict[str, float] = {}
        if groups:
            for label, support in source_report["class_group_counts"].items():
                probabilities[label] = ((groups - int(support)) / groups) ** groups
        source_report["class_omission_probabilities"] = probabilities
        if probabilities:
            worst_label = max(probabilities, key=lambda label: (probabilities[label], label.encode("utf-8")))
            source_report["worst_class"] = {
                "label": worst_label,
                "groups": source_report["class_group_counts"][worst_label],
                "omission_probability": probabilities[worst_label],
            }
        else:
            source_report["worst_class"] = None


def _add_analytic_omission(result: dict[str, Any]) -> None:
    _annotate_analytic_omission(result["sources"])


def _apply_v2_row_contract(
    rows: Sequence[Mapping[str, Any]],
    entry: Mapping[str, Any],
    config: Mapping[str, Any],
    thresholds: SupportThresholds,
) -> tuple[list[Mapping[str, Any]], dict[str, Any]]:
    contract_name = str(entry["label_contract"])
    contract = config["label_contracts"][contract_name]
    contract_type = contract["type"]
    metadata: dict[str, Any] = {"label_contract": contract_name, "type": contract_type, "reasons": []}
    selected: list[Mapping[str, Any]]
    if contract_type == "raw":
        selected = list(rows)
    elif contract_type == "mapping":
        selected = map_row_labels(rows, contract["mapping"], strip_subtype=bool(contract.get("strip_subtype", False)))
    elif contract_type == "identity_vocabulary":
        frequencies = identity_document_frequencies(rows, expected_sources=entry["expected_sources"])
        try:
            vocabulary = select_identity_vocabulary(
                frequencies,
                minimum=int(contract["minimum_document_frequency_each_source"]),
                maximum_size=int(contract["maximum_vocabulary"]),
            )
        except ValueError:
            vocabulary = []
            metadata["reasons"].append("identity_vocabulary_infeasible")
        vocabulary_set = set(vocabulary)
        selected = [row for row in rows if str(row["label"]) in vocabulary_set]
        metadata["retained_vocabulary"] = vocabulary
    else:
        raise ValueError(f"unsupported label contract type: {contract_type}")
    selected = cap_rows_by_group(selected, max_rows_per_group=thresholds.max_rows_per_group)
    metadata["selected_rows"] = len(selected)
    return selected, metadata


def _family_readiness(config: Mapping[str, Any], audits: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    by_key = {(row["role"], row["task"]): row for row in audits if row["tier"] == "tier1"}
    output: dict[str, Any] = {}
    for role in config["roles"]:
        role_output: dict[str, Any] = {}
        for family, family_config in config["families"].items():
            constructs: dict[str, Any] = {}
            statuses: list[str] = []
            for construct in family_config["required_constructs"]:
                representative = family_config["representatives"].get(construct)
                if representative is None:
                    status = "not_run"
                    reasons = ["required_operationalization_not_built"]
                else:
                    audit = by_key.get((role, representative))
                    if audit is None:
                        status = "not_run"
                        reasons = ["representative_task_missing"]
                    else:
                        status = str(audit["status"])
                        reasons = list(audit["reasons"])
                statuses.append(status)
                constructs[construct] = {"representative_task": representative, "status": status, "reasons": reasons}
            aggregate = aggregate_statuses(statuses)
            role_output[family] = {**aggregate, "constructs": constructs, "finite_constructs": sum(s == "eligible" for s in statuses)}
        output[role] = role_output
    return output


def _endpoint_schema(config: Mapping[str, Any], audits: Sequence[Mapping[str, Any]], families: Mapping[str, Any]) -> dict[str, Any]:
    required_task_audits = [audit for audit in audits if audit["required_for_task_measurability"]]
    task_aggregate = aggregate_statuses([str(audit["status"]) for audit in required_task_audits])
    family_statuses = [family["status"] for role in families.values() for family in role.values()]
    family_aggregate = aggregate_statuses(family_statuses)
    endpoints = {
        "task_measurability": {
            "status": task_aggregate["status"],
            "reasons": [task_aggregate["reason"]],
            "observed_value": {
                "eligible_task_files": sum(audit["status"] == "eligible" for audit in audits),
                "total_task_files": len(audits),
                "eligible_required_task_files": sum(audit["status"] == "eligible" for audit in required_task_audits),
                "total_required_task_files": len(required_task_audits),
            },
        },
        "family_localization": {
            "status": family_aggregate["status"],
            "reasons": [family_aggregate["reason"]],
            "observed_value": None,
        },
        "family_stability": {
            "status": "not_run",
            "reasons": ["no_representation_scoring_authorized"],
            "observed_value": None,
        },
        "collateral_validity": {
            "status": "not_run",
            "reasons": ["no_representation_scoring_authorized"],
            "observed_value": None,
        },
        "counterfactual_validity": {
            "status": "not_run",
            "reasons": ["no_representation_scoring_authorized"],
            "observed_value": None,
        },
    }
    additional_blocks = []
    if config["replacement_confirmation"]["status"] != "ready":
        additional_blocks.append("replacement_confirmation_unset")
    aggregated = aggregate_endpoint_records(
        endpoints,
        required_endpoints=config["required_endpoints"],
        additional_blocking_reasons=additional_blocks,
    )
    return {
        "statuses": config["endpoint_statuses"],
        "required_endpoints": aggregated["required_endpoints"],
        "endpoints": aggregated["endpoints"],
        "overall_decision_eligibility": aggregated["overall"],
        "execution_authorization": "prescore_label_only_complete",
        "scoring_authorization": "not_granted",
    }


def _markdown(report: Mapping[str, Any]) -> str:
    counts = Counter(row["status"] for row in report["task_audits"])
    lines = [
        "# Atlas measurement v2 — static prescore audit",
        "",
        "> Label/group metadata only. No representations were loaded, no neural model was scored, and no final data were opened.",
        "",
        "## Decision",
        "",
        f"- Overall v2 decision eligibility: **{report['endpoint_validity']['overall_decision_eligibility']['status']}** "
        f"(`{report['endpoint_validity']['overall_decision_eligibility']['reason']}`).",
        "- `UD_English-LinES` is retired from v2 confirmation; the replacement source is unset.",
        "- The frozen completion-v1 result is unchanged and remains historical evidence.",
        f"- Task/source files: {len(report['task_audits'])} ({counts['eligible']} support-eligible; {counts['ineligible']} ineligible).",
        "",
        "## Historical raw-row support diagnostic",
        "",
        "This table preserves the pre-rebuild evidence that exposed the v1 failure. It is diagnostic only; v2 eligibility below is recomputed after the frozen label contract and document cap.",
        "",
        "| Tier | Role | Task | Source | Raw groups | Rarest raw class | Rarest raw class groups | Raw omission probability | Raw max rows/group |",
        "|---|---|---|---|---:|---|---:|---:|---:|",
    ]
    for audit in report["task_audits"]:
        for source, raw_report in audit["raw_support"].items():
            worst = raw_report["worst_class"]
            is_problem = (
                raw_report["groups"] < report["thresholds"]["min_groups"]
                or raw_report["max_rows_per_group"] > report["thresholds"]["max_rows_per_group"]
                or (worst is not None and worst["groups"] < report["thresholds"]["min_class_groups"])
            )
            if not is_problem:
                continue
            label = "—" if worst is None else worst["label"]
            groups = "—" if worst is None else str(worst["groups"])
            omission = "—" if worst is None else f"{worst['omission_probability']:.3%}"
            lines.append(
                f"| {audit['tier']} | {audit['role']} | {audit['task']} | {source} | {raw_report['groups']} | "
                f"{label} | {groups} | {omission} | {raw_report['max_rows_per_group']} |"
            )

    lines.extend([
        "",
        "## V2-projected support findings",
        "",
        "| Tier | Role | Task | Decision role | Source | Groups | Rarest selected class groups | Omission probability | Raw max rows/group | Selected max rows/group | Task-wide finite maps | Status |",
        "|---|---|---|---|---|---:|---:|---:|---:|---:|---:|---|",
    ])
    for audit in report["task_audits"]:
        for source, source_report in audit["sources"].items():
            worst = source_report["worst_class"]
            rare_groups = "—" if worst is None else str(worst["groups"])
            omission = "—" if worst is None else f"{worst['omission_probability']:.3%}"
            raw_max = audit["raw_support"][source]["max_rows_per_group"]
            decision_role = "required" if audit["required_for_task_measurability"] else "diagnostic"
            lines.append(
                f"| {audit['tier']} | {audit['role']} | {audit['task']} | {decision_role} | {source} | {source_report['groups']} | "
                f"{rare_groups} | {omission} | {raw_max} | {source_report['max_rows_per_group']} | "
                f"{audit['bootstrap']['finite_draws']}/{audit['bootstrap']['draws']} | {audit['status']} |"
            )

    lines.extend(["", "## Family measurability", ""])
    for role, role_families in report["family_readiness"].items():
        lines.append(f"### {role}")
        lines.append("")
        for family, value in role_families.items():
            missing = [name for name, construct in value["constructs"].items() if construct["status"] != "eligible"]
            lines.append(
                f"- **{family}: {value['status']}** — {value['finite_constructs']} eligible distinct constructs; "
                f"missing/ineligible: {', '.join(missing) if missing else 'none'}."
            )
        lines.append("")

    lines.extend(
        [
            "## Historical code context (not part of the label-only estimand)",
            "",
            "Static inspection of `scripts/run_msae_refit_worker.py:408-430` shows that paired K2 workers reuse the corresponding raw C2 bootstrap maps. The historical identical 414/500 counts therefore are not independent model failures.",
            "",
            "## Interpretation boundary",
            "",
            "This audit diagnoses support and eligibility only. Bootstrap finiteness does not create independent documents, and a finite task is not evidence of selective localization. Specificity-cache and stability utilities were unit-tested but not applied to model representations in this work.",
            "",
        ]
    )
    return "\n".join(lines)


def run(config: Mapping[str, Any]) -> dict[str, Any]:
    output_root = validate_output_root(ROOT, config["output_root"], ROOT / "reports")
    protocol, freeze_record = resolve_allowlisted_inputs(
        ROOT,
        [config["protocol"], config["freeze_record"]],
        [ROOT / "docs", ROOT / "configs" / "atlas_completion"],
    )
    inputs = resolve_allowlisted_inputs(ROOT, config["inputs"], [ROOT / path for path in config["allowed_input_roots"]])
    pre_freeze = verify_freeze_record(ROOT, freeze_record)
    if not pre_freeze["ok"]:
        raise ValueError("completion-v1 freeze verification failed before audit")
    before_paths = _snapshot_paths()
    before_processes = _process_snapshot()
    _require_clean_process_snapshot(before_processes, stage="before")
    thresholds = _thresholds(config)

    audits: list[dict[str, Any]] = []
    for entry, path in zip(config["inputs"], inputs):
        raw_rows = _load_rows(path, entry, config["source_prefix_map"])
        raw_support = summarize_rows_by_source(raw_rows, expected_sources=entry["expected_sources"])
        _annotate_analytic_omission(raw_support)
        rows, selection = _apply_v2_row_contract(raw_rows, entry, config, thresholds)
        audit = audit_task_support(
            rows,
            role=entry["role"],
            task=entry["task"],
            expected_sources=entry["expected_sources"],
            thresholds=thresholds,
            nuisance_pooled=bool(entry["nuisance_pooled"]),
        )
        audit["tier"] = entry["tier"]
        audit["input_path"] = entry["path"]
        audit["input_sha256"] = entry["sha256"]
        audit["required_for_task_measurability"] = bool(entry["required_for_task_measurability"])
        audit["raw_support"] = raw_support
        audit["selection"] = selection
        if selection["reasons"]:
            audit["reasons"] = sorted(set(audit["reasons"]) | set(selection["reasons"]))
            audit["status"] = "ineligible"
        _add_analytic_omission(audit)
        audits.append(audit)

    families = _family_readiness(config, audits)
    endpoints = _endpoint_schema(config, audits, families)
    report = {
        "schema_version": "atlas_measurement_v2_prescore_audit",
        "evidence_class": "label_only_static_support_audit_no_scoring",
        "protocol_sha256": config["protocol"]["sha256"],
        "config_sha256": sha256_file(CONFIG_PATH),
        "replacement_confirmation": config["replacement_confirmation"],
        "blind_final_policy": config["blind_final"],
        "thresholds": config["thresholds"],
        "task_audits": audits,
        "family_readiness": families,
        "endpoint_validity": endpoints,
    }

    temporary = output_root.parent / f".{output_root.name}.tmp.{os.getpid()}"
    if os.path.lexists(temporary):
        raise ValueError(f"temporary output already exists: {temporary}")
    temporary.mkdir(mode=0o755)
    try:
        (temporary / "prescore_audit.json").write_bytes(canonical_json_bytes(report))
        (temporary / "prescore_audit.md").write_text(_markdown(report), encoding="utf-8")
        (temporary / "endpoint_validity.json").write_bytes(canonical_json_bytes(endpoints))

        after_paths = _snapshot_paths()
        if after_paths != before_paths:
            raise ValueError("protected experiment/frozen path inventory changed during audit")
        after_processes = _process_snapshot()
        _require_clean_process_snapshot(after_processes, stage="after")
        post_freeze = verify_freeze_record(ROOT, freeze_record)
        if post_freeze != pre_freeze:
            raise ValueError("completion-v1 frozen inventory changed during audit")

        output_digests = {
            path.name: sha256_file(path)
            for path in sorted(temporary.iterdir(), key=lambda path: path.name.encode("utf-8"))
            if path.is_file()
        }
        io_inventory = {
            "schema_version": "atlas_measurement_v2_io_inventory",
            "config": {"path": CONFIG_PATH.relative_to(ROOT).as_posix(), "sha256": sha256_file(CONFIG_PATH)},
            "protocol": config["protocol"],
            "frozen_pre_and_post_identical": True,
            "freeze_inventory": pre_freeze["inventory"],
            "row_inputs": [
                {"path": entry["path"], "sha256": entry["sha256"], "tier": entry["tier"]} for entry in config["inputs"]
            ],
            "created_outputs_excluding_this_inventory": output_digests,
            "safety": {
                "model_scoring": False,
                "representation_loading": False,
                "network_capability": False,
                "process_creation_capability": False,
                "cuda_visible_devices": os.environ.get("CUDA_VISIBLE_DEVICES"),
                "hf_hub_offline": os.environ.get("HF_HUB_OFFLINE"),
                "transformers_offline": os.environ.get("TRANSFORMERS_OFFLINE"),
                "protected_path_inventory_unchanged": True,
                "process_snapshot_before": before_processes,
                "process_snapshot_after": after_processes,
            },
        }
        (temporary / "io_inventory.json").write_bytes(canonical_json_bytes(io_inventory))
        os.replace(temporary, output_root)
    except BaseException:
        shutil.rmtree(temporary, ignore_errors=True)
        raise
    return report


def main() -> int:
    args = parse_args()
    try:
        config = _load_bound_config(args.config)
        report = run(config)
    except (OSError, ValueError, KeyError, json.JSONDecodeError) as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 2
    counts = Counter(row["status"] for row in report["task_audits"])
    print(
        f"wrote {report['schema_version']}: {counts['eligible']} eligible, {counts['ineligible']} ineligible; "
        f"overall={report['endpoint_validity']['overall_decision_eligibility']['status']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
