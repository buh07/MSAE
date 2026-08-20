#!/usr/bin/env python3
"""Build deterministic Tier-2, token-control, and group-count manifests."""

from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

import numpy as np

from msa_completion_common import (EVIDENCE_CLASS, ROOT, atomic_write_bytes,
                                   atomic_write_json, canonical_json_bytes,
                                   default_firewall, load_activation, read_json,
                                   sha256_file, stable_hash,
                                   verify_parent_checkpoint,
                                   verify_parent_transform)


ROLES = ["discovery", "calibration", "C1", "C2"]
CONTINUATION = {0: "prefix", 1: "first", 2: "continuation"}


def row_id(data: Any, row: int) -> str:
    unit = data.units[int(data.meta["unit_index"][row])]
    return f"{unit['variant_id']}:{int(data.meta['token_index'][row])}"


def label_for(data: Any, row: int, task: str) -> str:
    if task == "continuation_status":
        code = int(data.meta["continuation_code"][row])
        if code not in CONTINUATION:
            raise RuntimeError(f"unknown continuation code {code}")
        return CONTINUATION[code]
    if task == "context_offset":
        return str(int(data.meta["offset"][row]))
    word = int(data.meta["word_index"][row])
    if word < 0:
        return "__DROP__"
    record = data.records[int(data.meta["record_index"][row])]
    if task not in record["labels"] or word >= len(record["labels"][task]):
        raise RuntimeError(f"absent label {task} at activation row {row}")
    return str(record["labels"][task][word])


def candidate_rows(data: Any, task: str) -> dict[str, list[int]]:
    if task in {"continuation_status", "context_offset"}:
        rows = np.arange(len(data.x), dtype=np.int64)
    else:
        rows = np.flatnonzero(
            (data.meta["word_index"] >= 0)
            & (data.meta["continuation_code"] == 1))
    result: dict[str, list[int]] = defaultdict(list)
    for row in rows.tolist():
        label = label_for(data, row, task)
        if label != "__DROP__":
            result[label].append(row)
    return dict(result)


def hash_key(seed: int, role: str, task: str, label: str, rid: str) -> tuple[str, str]:
    payload = f"{seed}\0{role}\0{task}\0{label}\0{rid}".encode()
    return hashlib.sha256(payload).hexdigest(), rid


def select_rows(data: Any, role: str, task: str, eligible: list[str], cap: int, seed: int) -> list[dict[str, Any]]:
    candidates = candidate_rows(data, task)
    ordered: dict[str, list[tuple[tuple[str, str], int]]] = {}
    for label in eligible:
        ordered[label] = sorted((hash_key(seed, role, task, label, row_id(data, row)), row) for row in candidates.get(label, []))
    floor = cap // len(eligible)
    chosen: list[tuple[tuple[str, str], int, str]] = []
    remainder: list[tuple[tuple[str, str], int, str]] = []
    for label in eligible:
        take = min(floor, len(ordered[label]))
        chosen.extend((key, row, label) for key, row in ordered[label][:take])
        remainder.extend((key, row, label) for key, row in ordered[label][take:])
    if len(chosen) < cap:
        chosen.extend(sorted(remainder)[: cap - len(chosen)])
    chosen.sort()
    output: list[dict[str, Any]] = []
    for _, row, label in chosen:
        record = data.records[int(data.meta["record_index"][row])]
        unit = data.units[int(data.meta["unit_index"][row])]
        if unit.get("base_id") != record.get("base_id"):
            raise RuntimeError(f"activation unit is not a member of its parent base record: {role}/{task}/{row}")
        output.append({
            "row_id": row_id(data, row),
            "base_id": str(unit["base_id"]),
            "activation_row": int(row),
            "label": label,
            "source": str(record["source"]),
            "source_type": str(record["source_type"]),
            "document_group": str(record["document_group"]),
        })
    ids = [row["row_id"] for row in output]
    if len(ids) != len(set(ids)):
        raise RuntimeError(f"duplicate selected row IDs: {role}/{task}")
    return output


def snapshot_manifest(model: dict[str, str], firewall: Any) -> tuple[Path, dict[str, Any]]:
    from huggingface_hub import snapshot_download

    snapshot = Path(snapshot_download(model["name"], revision=model["revision"], local_files_only=True)).resolve()
    repo_root = snapshot.parents[1]
    blobs = (repo_root / "blobs").resolve()
    files = []
    for entry in sorted(snapshot.rglob("*")):
        if entry.is_dir():
            continue
        target = entry.resolve(strict=True)
        try:
            target.relative_to(blobs)
        except ValueError as exc:
            raise RuntimeError(f"HF snapshot entry escapes exact blobs root: {entry} -> {target}") from exc
        if not target.is_file():
            raise RuntimeError(f"HF snapshot target is not a regular file: {target}")
        firewall.register_file(entry)
        firewall.register_file(target)
        firewall.attest(entry)
        firewall.attest(target)
        files.append({"snapshot_path": str(entry), "target_path": str(target), "sha256": sha256_file(target), "size": target.stat().st_size})
    return snapshot, {"model": model, "snapshot": str(snapshot), "repo_root": str(repo_root), "files": files}


def build_token_controls(config: dict[str, Any], firewall: Any) -> dict[str, Any]:
    sources_path = firewall.attest(ROOT / "configs/atlas/data_sources.json")
    model = read_json(sources_path)["model"]
    snapshot, hf_manifest = snapshot_manifest(model, firewall)
    from transformers import AutoTokenizer

    tokenizer = AutoTokenizer.from_pretrained(snapshot, local_files_only=True, use_fast=True)
    transforms_path = firewall.attest(ROOT / "data/atlas_v1/transforms/C2.jsonl", role="C2")
    rows = []
    for line in transforms_path.read_text().splitlines():
        item = json.loads(line)
        if item["family"] != "lexical_entity_substitution" or item.get("token_aligned") is not True:
            continue
        source = tokenizer(item["source_words"], is_split_into_words=True, add_special_tokens=False)
        target = tokenizer(item["target_words"], is_split_into_words=True, add_special_tokens=False)
        sw, tw = source.word_ids(), target.word_ids()
        if sw != tw:
            raise RuntimeError(f"parent token_aligned row no longer aligns: {item['transform_id']}")
        changed_words = [i for i, (a, b) in enumerate(zip(item["source_words"], item["target_words"], strict=True)) if a != b]
        designated = [i for i, word in enumerate(sw) if word in changed_words]
        if not designated:
            raise RuntimeError(f"no changed token positions: {item['transform_id']}")
        rows.append({
            "transform_id": item["transform_id"],
            "template_group": item["template_group"],
            "source_input_ids": list(map(int, source["input_ids"])),
            "target_input_ids": list(map(int, target["input_ids"])),
            "word_ids": sw,
            "changed_word_indices": changed_words,
            "designated_token_positions": designated,
        })
    if len(rows) != 16 or len({row["template_group"] for row in rows}) != 4:
        raise RuntimeError(f"token-control population mismatch: {len(rows)} rows")
    return {"schema_version": "atlas_completion_token_controls_v1", "evidence_class": EVIDENCE_CLASS,
            "tokenizer": hf_manifest, "rows": rows}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, default=ROOT / "configs/atlas_completion/analysis.json")
    parser.add_argument("--output", type=Path, default=ROOT / "data/atlas_completion_v1")
    args = parser.parse_args()
    args.config = args.config.resolve()
    args.output = args.output.resolve()
    config = read_json(args.config)
    source_run_root = ROOT / config["source_run_root"]
    firewall = default_firewall(source_run_root)
    # This builder creates the inventory. Parent freeze/terminal verification
    # remains active, while recursive comparison to the not-yet-built file is
    # disabled only for this create-once bootstrap process.
    firewall.upstream_inventory_required = False
    firewall.register_root(args.output)
    config_path = firewall.attest(args.config)
    args.output.mkdir(parents=True, exist_ok=True)
    if any(args.output.iterdir()):
        raise RuntimeError(f"completion row output is create-once and nonempty: {args.output}")

    loaded = {role: load_activation(role, 3, source_run_root, firewall) for role in ROLES}
    counts: dict[str, dict[str, Counter[str]]] = {role: {} for role in ROLES}
    for role in ROLES:
        for task in config["sentinels"]:
            counts[role][task] = Counter({label: len(rows) for label, rows in candidate_rows(loaded[role], task).items()})

    manifest: dict[str, Any] = {"schema_version": "atlas_completion_tier2_rows_v1", "evidence_class": EVIDENCE_CLASS,
                                "seed": config["seed"], "config_sha256": sha256_file(config_path), "roles": {}, "tasks": {}}
    for task in config["sentinels"]:
        minimum = int(config["sentinel_min_support"].get(task, config["sentinel_min_support"]["default"]))
        eligible = sorted(label for label in set(counts["discovery"][task]) & set(counts["calibration"][task])
                          if counts["discovery"][task][label] >= minimum and counts["calibration"][task][label] >= minimum)
        if len(eligible) < 2:
            raise RuntimeError(f"sentinel lacks two discovery/calibration classes: {task}")
        manifest["tasks"][task] = {"minimum_support": minimum, "eligible_labels": eligible,
                                            "candidate_counts": {role: dict(sorted(counts[role][task].items())) for role in ROLES}}

    for role in ROLES:
        manifest["roles"][role] = {}
        cap = int(config["task_row_caps"][role])
        for task in config["sentinels"]:
            rows = select_rows(loaded[role], role, task, manifest["tasks"][task]["eligible_labels"], cap, int(config["seed"]))
            payload = b"".join(canonical_json_bytes(row) for row in rows)
            path = args.output / f"{role}.{task}.jsonl"
            digest = atomic_write_bytes(path, payload)
            classes = Counter(row["label"] for row in rows)
            parent_base_ids = {record["base_id"] for record in loaded[role].records}
            unknown_bases = sorted({row["base_id"] for row in rows} - parent_base_ids)
            if unknown_bases:
                raise RuntimeError(f"selected rows lack parent base membership: {role}/{task}")
            manifest["roles"][role][task] = {
                "path": f"data/atlas_completion_v1/{path.name}", "sha256": digest, "rows": len(rows),
                "classes": dict(sorted(classes.items())), "sources": sorted({row["source"] for row in rows}),
                "groups": len({(row["source"], row["document_group"]) for row in rows}),
                "qa": {"duplicate_row_ids": 0,
                       "unique_row_ids": len({row["row_id"] for row in rows}),
                       "parent_base_membership": True,
                       "unknown_parent_base_ids": []},
            }

    # Manifest-only Tier-1 group preflight.  It uses public row IDs/metadata only.
    tier1 = read_json(firewall.attest(ROOT / "configs/atlas/task_row_manifest.json"))
    group_rows: dict[str, Any] = {}
    for role in ["C1", "C2"]:
        group_rows[role] = {}
        for task, spec in sorted(tier1["roles"][role].items()):
            path = firewall.attest(ROOT / spec["path"], role=role)
            # Map row IDs through the same activation lookup used by scoring.
            from msa_completion_common import load_row_file

            _, _, sources, groups = load_row_file(path, loaded[role], firewall, role=role)
            per_source = {source: len(np.unique(groups[sources == source])) for source in sorted(np.unique(sources).tolist())}
            group_rows[role][task] = {"per_source": per_source, "minimum": min(per_source.values()), "total": len(set(zip(sources.tolist(), groups.tolist())))}
    known_invalid = [{"role": role, "task": task, **row} for role, tasks in group_rows.items() for task, row in tasks.items()
                     if row["minimum"] < int(config["minimum_groups_per_task_source"])]
    preflight = {
        "schema_version": "atlas_completion_preflight_v1", "evidence_class": EVIDENCE_CLASS,
        "group_counts": group_rows, "minimum_groups_per_task_source": config["minimum_groups_per_task_source"],
        "known_invalid": known_invalid, "joint_decision_forced_equivocal": bool(known_invalid),
        "diagnostic_continuation_authorized": True,
        "reason": "four/five-group LinES strata invalidate dependent randomization hypotheses" if known_invalid else None,
    }
    token_controls = build_token_controls(config, firewall)
    from atlas_freeze import verify_activation_complete, verify_freeze

    parent_freeze = verify_freeze()
    upstream_files: dict[str, str] = {}
    parent_bundle_files = sorted(parent_freeze["files"])
    partition_hashes = read_json(ROOT / "configs/atlas/partition_hashes.json")
    public_partition_files = sorted(
        rel for rel, spec in partition_hashes["files"].items()
        if spec.get("access") == "public_analysis")
    public_partition_files_by_role = {
        role: [rel for rel in public_partition_files
               if f"/{role}." in rel]
        for role in ROLES
    }
    analysis_row_files_by_role = {
        role: sorted(spec["path"] for spec in tier1["roles"][role].values())
        for role in ROLES
    }
    analysis_row_files = sorted({rel for paths in analysis_row_files_by_role.values()
                                 for rel in paths})
    public_role_files_by_role = {
        role: sorted(set(public_partition_files_by_role[role])
                     | set(analysis_row_files_by_role[role]))
        for role in ROLES
    }

    def bind(path: Path, expected: str | None = None) -> None:
        resolved = path.resolve()
        firewall.register_file(resolved)
        firewall.attest(resolved)
        try:
            name = str(resolved.relative_to(ROOT.resolve()))
        except ValueError:
            name = str(resolved)
        actual = sha256_file(resolved)
        if expected is not None and actual != expected:
            raise RuntimeError(f"upstream digest mismatch while inventorying: {resolved}")
        upstream_files[name] = actual

    bind(ROOT / "configs/atlas/freeze_record.json")
    for rel in parent_bundle_files:
        bind(ROOT / rel, parent_freeze["files"][rel])
    for rel in public_partition_files:
        bind(ROOT / rel, partition_hashes["files"][rel]["sha256"])
    for role in ROLES:
        for spec in tier1["roles"][role].values():
            bind(ROOT / spec["path"], spec["sha256"])
    for role in ROLES:
        directory = source_run_root / "raw_activations" / role
        record = verify_activation_complete(directory, role, parent_freeze)
        bind(directory / "COMPLETE.json")
        for name, spec in record["artifacts"].items():
            bind(directory / name, spec["sha256"])

    jobs = config["primary_checkpoints"] + config["descriptive_checkpoints"]
    for job in jobs:
        directory = source_run_root / "k2_transforms" / job
        record = verify_parent_transform(source_run_root, job, firewall)
        bind(directory / "COMPLETE.json")
        for role, role_record in record["roles"].items():
            for name, spec in role_record["artifacts"].items():
                bind(directory / role / name, spec["sha256"])
        checkpoint_spec = verify_parent_checkpoint(job, firewall)
        checkpoint = Path(checkpoint_spec["path"])
        bind(checkpoint, checkpoint_spec["sha256"])

    raw_root = ROOT / "results/atlas/raw_v1"
    bind(raw_root / "CALIBRATION_COMPLETE.json")
    raw_complete = read_json(firewall.attest(raw_root / "CALIBRATION_COMPLETE.json"))
    for name, digest in raw_complete["artifacts"].items():
        bind(raw_root / name, digest)

    k2_root = ROOT / "results/atlas/k2_v1"
    bind(k2_root / "COMPLETE.json")
    k2_complete = read_json(firewall.attest(k2_root / "COMPLETE.json"))
    for name, digest in k2_complete["artifacts"].items():
        bind(k2_root / name, digest)
    for job in jobs:
        marker = k2_root / f"{job}_functional_COMPLETE.json"
        result = k2_root / f"{job}_functional.json"
        bind(marker)
        bind(result, read_json(marker)["result_sha256"])
    bind(ROOT / "reports/architecture_decision.json")
    bind(ROOT / "reports/architecture_decision.md")
    upstream_inventory = {
        "schema_version": "atlas_completion_upstream_inventory_v1",
        "evidence_class": EVIDENCE_CLASS,
        "parent_bundle_sha256": parent_freeze["bundle_sha256"],
        "parent_bundle_files": parent_bundle_files,
        "public_partition_files": public_partition_files,
        "public_partition_files_by_role": public_partition_files_by_role,
        "analysis_row_files": analysis_row_files,
        "analysis_row_files_by_role": analysis_row_files_by_role,
        "public_role_files_by_role": public_role_files_by_role,
        "files": dict(sorted(upstream_files.items())),
    }
    # Calibration-selected K2 probe alphas are copied into a narrow pilot input
    # so the discovery/calibration-only pilot never opens the C2-bearing parent
    # audit results.  The source digest remains frozen for provenance.
    pilot_k2_alphas: dict[str, Any] = {
        "schema_version": "atlas_completion_pilot_k2_alphas_v1",
        "evidence_class": EVIDENCE_CLASS,
        "selection_role": "calibration",
        "jobs": {},
    }
    for job in config["primary_checkpoints"] + config["descriptive_checkpoints"]:
        audit_path = firewall.attest(ROOT / f"results/atlas/k2_v1/{job}_audit.json")
        audit = read_json(audit_path)
        if audit.get("job_id") != job:
            raise RuntimeError(f"parent K2 audit job mismatch: {job}")
        pilot_k2_alphas["jobs"][job] = {
            "source_audit_sha256": sha256_file(audit_path),
            "alpha_selection": {
                rep: {
                    task: {"selected": float(audit["alpha_selection"][rep][task]["selected"])}
                    for task in sorted(audit["alpha_selection"][rep])
                }
                for rep in ["pos", "content"]
            },
        }
    atomic_write_json(args.output / "tier2_manifest.json", manifest)
    atomic_write_json(args.output / "token_control_manifest.json", token_controls)
    atomic_write_json(args.output / "pilot_k2_alphas.json", pilot_k2_alphas)
    atomic_write_json(args.output / "upstream_inventory.json", upstream_inventory)
    atomic_write_json(args.output / "preflight.json", preflight)
    artifact_names = ["tier2_manifest.json", "token_control_manifest.json",
                      "pilot_k2_alphas.json", "upstream_inventory.json",
                      "preflight.json"]
    complete = {
        "schema_version": "atlas_completion_manifest_complete_v1", "evidence_class": EVIDENCE_CLASS,
        "config_sha256": sha256_file(config_path),
        "artifacts": {name: sha256_file(args.output / name) for name in artifact_names},
        "input_attestation": firewall.attestation,
    }
    atomic_write_json(args.output / "MEASUREMENT_COMPLETE.json", complete)
    print(json.dumps({"output": str(args.output), "sentinel_tasks": len(config["sentinels"]),
                      "known_invalid": len(known_invalid), "token_aligned_rows": len(token_controls["rows"])}, indent=2))


if __name__ == "__main__":
    main()
