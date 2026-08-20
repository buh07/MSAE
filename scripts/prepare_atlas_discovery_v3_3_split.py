#!/usr/bin/env python3
"""Freeze attempt-7 legacy challenge, external fresh QA, and train-science split."""
from __future__ import annotations

import argparse
import base64
import hashlib
import json
from pathlib import Path
from typing import Any, Mapping

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

ROOT = Path(__file__).resolve().parents[1]
SALT = "atlas_discovery_v3_3_attempt7"
SOURCES = ("EWT", "GUM")
LEGACY_ROOT = ROOT / "data/atlas_discovery_v3_1_attempt5/prepared"
FRESH_ROOT = ROOT / "data/atlas_discovery_v3_3_attempt7_qa_compact_v3/prepared"
TERMINAL = ROOT / "pilot_runs/20260803_atlas_discovery_v3_1_attempt5/TERMINAL.json"
ATTEMPT5_SCORING_CONFIG = ROOT / "configs/atlas_discovery_v3/scoring.json"
EXPECTED_ATTEMPT5_SCORING_SHA256 = (
    "80b366e3ac48afc09bd810bf3398b428fc4e0adcc0903f41fd937b1bd3f56b52"
)
EXPECTED_ATTEMPT5_SIGNER_FINGERPRINT = (
    "56308de36cf46c6c18f0a08b54d0884dd88b23e1f612cc4b6c93c9844d72025d"
)


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def dig(*parts: Any) -> str:
    return hashlib.sha256("|".join(map(str, parts)).encode()).hexdigest()


def rows(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text().splitlines() if line]


def docs(row: Mapping[str, Any]) -> set[str]:
    return {
        str(row[key])
        for key in ("document_group", "donor_document_group")
        if row.get(key)
    }


def verify_attempt5_terminal() -> dict[str, Any]:
    """Authenticate the terminal against the independently pinned config/signer."""
    if sha(ATTEMPT5_SCORING_CONFIG) != EXPECTED_ATTEMPT5_SCORING_SHA256:
        raise RuntimeError("attempt5 scoring configuration digest drift")
    scoring = json.loads(ATTEMPT5_SCORING_CONFIG.read_text())
    signer = scoring.get("qa_signer")
    if not isinstance(signer, Mapping):
        raise RuntimeError("attempt5 signer specification missing")
    if signer.get("algorithm") != "Ed25519":
        raise RuntimeError("attempt5 signer algorithm drift")
    public = base64.b64decode(str(signer.get("public_key_base64", "")), validate=True)
    fingerprint = hashlib.sha256(public).hexdigest()
    if (
        signer.get("public_key_fingerprint_sha256")
        != EXPECTED_ATTEMPT5_SIGNER_FINGERPRINT
        or fingerprint != EXPECTED_ATTEMPT5_SIGNER_FINGERPRINT
    ):
        raise RuntimeError("attempt5 signer fingerprint drift")

    envelope = json.loads(TERMINAL.read_text())
    terminal = envelope.get("payload")
    signature = envelope.get("signature")
    if (
        not isinstance(terminal, Mapping)
        or not isinstance(signature, Mapping)
        or terminal.get("status") != "TERMINAL_TECHNICALLY_INVALID"
    ):
        raise RuntimeError("attempt5 terminal malformed")
    terminal_scoring = terminal.get("scoring_config")
    if (
        not isinstance(terminal_scoring, Mapping)
        or terminal_scoring.get("path") != "configs/atlas_discovery_v3/scoring.json"
        or terminal_scoring.get("sha256") != EXPECTED_ATTEMPT5_SCORING_SHA256
    ):
        raise RuntimeError("attempt5 terminal does not bind the pinned scoring configuration")
    message = json.dumps(
        terminal, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode()
    if (
        hashlib.sha256(message).hexdigest() != signature.get("message_sha256")
        or signature.get("algorithm") != "Ed25519"
    ):
        raise RuntimeError("attempt5 terminal digest drift")
    Ed25519PublicKey.from_public_bytes(public).verify(
        base64.b64decode(str(signature.get("signature_base64", "")), validate=True),
        message,
    )
    return dict(terminal)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--output", default="configs/atlas_discovery_v3_3/population_split_v3.json"
    )
    args = parser.parse_args()
    verify_attempt5_terminal()

    fresh_manifest_path = FRESH_ROOT / "manifest.json"
    fresh_manifest = json.loads(fresh_manifest_path.read_text())
    if (
        fresh_manifest.get("schema_version")
        != "atlas_discovery_v3_3_attempt7_qa_compact_v3_prepared_v1"
        or fresh_manifest.get("role")
        != "external_devtest_technical_numerical_qa_only"
        or fresh_manifest.get("science_population_constructors_invoked") is not False
    ):
        raise RuntimeError("fresh technical-QA manifest role/scope drift")

    out_sources: dict[str, Any] = {}
    for source in SOURCES:
        legacy_pairs_path = LEGACY_ROOT / source / "intervention_pairs.jsonl"
        fresh_pairs_path = FRESH_ROOT / source / "intervention_pairs.jsonl"
        legacy_rows = rows(legacy_pairs_path)
        fresh_rows = rows(fresh_pairs_path)
        legacy_by_id = {row["pair_id"]: row for row in legacy_rows}
        qa_path = (
            ROOT
            / f"pilot_runs/20260803_atlas_discovery_v3_1_attempt5/failed_numerical_qa/{source}/qa_rows.json"
        )
        qa_rows = json.loads(qa_path.read_text())
        legacy_ids = [row["pair_id"] for row in qa_rows]
        if len(legacy_ids) != 32 or len(legacy_ids) != len(set(legacy_ids)):
            raise RuntimeError(f"legacy QA identity/count drift: {source}")
        if any(pair_id not in legacy_by_id for pair_id in legacy_ids):
            raise RuntimeError(f"legacy QA pair missing from parent: {source}")
        legacy = [legacy_by_id[pair_id] for pair_id in legacy_ids]
        legacy_docs = set().union(*(docs(row) for row in legacy))
        legacy_components = {str(row["component_id"]) for row in legacy}

        fresh: list[dict[str, Any]] = []
        used_docs: set[str] = set()
        used_components: set[str] = set()
        for construct in ("context_factorial", "relative_gap"):
            candidates = sorted(
                (row for row in fresh_rows if row["construct"] == construct),
                key=lambda row: dig(
                    SALT, "fresh-qa", source, construct, row["pair_id"]
                ),
            )
            for row in candidates:
                if docs(row) & used_docs or str(row["component_id"]) in used_components:
                    continue
                fresh.append(row)
                used_docs |= docs(row)
                used_components.add(str(row["component_id"]))
                if sum(item["construct"] == construct for item in fresh) == 8:
                    break
            if sum(item["construct"] == construct for item in fresh) != 8:
                raise RuntimeError(f"insufficient fresh QA {source}/{construct}")

        if legacy_docs & used_docs:
            raise RuntimeError(f"dev/test and train QA document IDs overlap: {source}")
        if legacy_components & used_components:
            raise RuntimeError(f"legacy/fresh QA component IDs overlap: {source}")
        train_documents = {
            str(row["document_group"])
            for row in rows(LEGACY_ROOT / source / "activation_rows.jsonl")
            if row.get("kind") == "main"
        }
        if used_docs & train_documents:
            raise RuntimeError(f"fresh QA overlaps any train-science document: {source}")

        out_sources[source] = {
            "legacy_parent_pairs": {
                "path": str(legacy_pairs_path.relative_to(ROOT)),
                "sha256": sha(legacy_pairs_path),
            },
            "legacy_qa_rows": {
                "path": str(qa_path.relative_to(ROOT)),
                "sha256": sha(qa_path),
            },
            "legacy_pair_ids": legacy_ids,
            "legacy_component_ids": sorted(legacy_components),
            "legacy_documents": sorted(legacy_docs),
            "fresh_parent_pairs": {
                "path": str(fresh_pairs_path.relative_to(ROOT)),
                "sha256": sha(fresh_pairs_path),
            },
            "fresh_pair_ids": [row["pair_id"] for row in fresh],
            "fresh_component_ids": sorted(used_components),
            "fresh_documents": sorted(used_docs),
            "science_excluded_documents": sorted(legacy_docs),
            "counts": {
                "legacy_pairs": len(legacy),
                "legacy_documents": len(legacy_docs),
                "fresh_pairs": len(fresh),
                "fresh_documents": len(used_docs),
                "science_excluded_documents": len(legacy_docs),
            },
        }

    output = {
        "schema_version": "atlas_discovery_v3_3_attempt7_population_split_v3",
        "salt": SALT,
        "attempt5_terminal": {
            "path": str(TERMINAL.relative_to(ROOT)),
            "sha256": sha(TERMINAL),
            "authenticated_scoring_config_sha256": EXPECTED_ATTEMPT5_SCORING_SHA256,
            "authenticated_signer_fingerprint_sha256": EXPECTED_ATTEMPT5_SIGNER_FINGERPRINT,
        },
        "qa_pool_manifest": {
            "path": str(fresh_manifest_path.relative_to(ROOT)),
            "sha256": sha(fresh_manifest_path),
        },
        "selection_rule": (
            "external dev+test: 8 context_factorial then 8 relative_gap per source "
            "by salted hash with greedy genuine-document/component disjointness"
        ),
        "activation_or_scientific_outcome_used": False,
        "sources": out_sources,
    }
    output_path = ROOT / args.output
    if output_path.exists() and json.loads(output_path.read_text()) != output:
        raise RuntimeError("existing split drift")
    if not output_path.exists():
        output_path.write_text(json.dumps(output, indent=2, sort_keys=True) + "\n")
    print(
        json.dumps(
            {
                "path": str(output_path.relative_to(ROOT)),
                "sha256": sha(output_path),
                "sources": {
                    source: out_sources[source]["counts"] for source in SOURCES
                },
            },
            indent=2,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
