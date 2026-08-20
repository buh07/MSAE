#!/usr/bin/env python3
"""Create or verify the prescore immutable base-run inventory."""
from __future__ import annotations
import argparse
from msa_completion_common import ROOT, atomic_write_json, sha256_file
from msa_completion_continuation_common import (
    BASE_DIGEST, BASE_STOP_SHA, INVENTORY, RUN_ROOT, RESULT_ROOT, SOURCE_RUN,
    inventory_digest, recursive_inventory, verify_fixed_source_hashes,
)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--verify", action="store_true")
    args = parser.parse_args()
    verify_fixed_source_hashes()
    entries = recursive_inventory(SOURCE_RUN)
    payload = {
        "schema_version": "atlas_completion_source_run_inventory_v1",
        "root": str(SOURCE_RUN.relative_to(ROOT)),
        "entries": entries,
        "entry_count": len(entries),
        "inventory_sha256": inventory_digest(entries),
        "base_completion_bundle_sha256": BASE_DIGEST,
        "base_l3_stop_sha256": BASE_STOP_SHA,
        "recorded_utc": None,
    }
    # recorded_utc is intentionally null: identical state yields identical trust bytes.
    if args.verify:
        from msa_completion_common import read_json
        if read_json(INVENTORY) != payload:
            raise RuntimeError("source-run inventory does not match current base root")
    else:
        if RUN_ROOT.exists() or RESULT_ROOT.exists():
            raise RuntimeError("cannot snapshot after continuation output exists")
        atomic_write_json(INVENTORY, payload)
    print({"inventory": str(INVENTORY), "entries": len(entries),
           "inventory_sha256": payload["inventory_sha256"],
           "manifest_sha256": sha256_file(INVENTORY)})


if __name__ == "__main__":
    main()
