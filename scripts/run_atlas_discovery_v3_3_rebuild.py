#!/usr/bin/env python3
"""Stage runner for the Atlas v3 discovery-only factor study."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Mapping

from atlas_discovery_v3_3_rebuild import build_prepared_data, sha256_file


ROOT = Path(__file__).resolve().parents[1]


def load_config(path: Path) -> dict[str, Any]:
    resolved = path.resolve(strict=True)
    if resolved.is_symlink() or not resolved.is_file() or not resolved.is_relative_to(ROOT):
        raise RuntimeError("config must be a regular in-repository file")
    config = json.loads(resolved.read_text(encoding="utf-8"))
    if config.get("schema_version") != "atlas_discovery_v3_3_attempt7_run_v1":
        raise RuntimeError("unknown v3 config schema")
    protocol = config.get("protocol", {})
    protocol_path = ROOT / str(protocol.get("path", ""))
    if sha256_file(protocol_path) != protocol.get("sha256"):
        raise RuntimeError("protocol digest drift")
    inventory = config.get("implementation_inventory", {})
    if not isinstance(inventory, Mapping) or not inventory:
        raise RuntimeError("empty implementation inventory")
    for raw, expected in inventory.items():
        candidate = (ROOT / str(raw)).resolve(strict=True)
        if not candidate.is_relative_to(ROOT) or candidate.is_symlink() or not candidate.is_file():
            raise RuntimeError(f"invalid implementation inventory path: {raw}")
        actual = sha256_file(candidate)
        if actual != expected:
            raise RuntimeError(f"implementation digest drift: {raw}:{actual}")
    return config


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="configs/atlas_discovery_v3_3/run_rebuild1.json")
    parser.add_argument("--stage", required=True, choices=("validate-config", "prepare"))
    args = parser.parse_args()
    config_path = (ROOT / args.config).resolve(strict=True)
    config = load_config(config_path)
    if args.stage == "validate-config":
        result: Any = {
            "status": "valid",
            "config": str(config_path.relative_to(ROOT)),
            "config_sha256": sha256_file(config_path),
            "protocol_sha256": config["protocol"]["sha256"],
            "representation_scoring_authorized": config["status"]
            == "frozen_discovery_representation_scoring_authorized",
        }
    else:
        result = build_prepared_data(config, config_path)
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
