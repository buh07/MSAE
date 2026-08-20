#!/usr/bin/env python3
"""Create or acknowledge the atlas-v1 prescore freeze record."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone

from atlas_freeze import FREEZE_RECORD, compute_bundle


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--ack-adversarial", action="store_true",
                        help="set only after the independent reviewer quotes this exact digest")
    args = parser.parse_args()
    record = compute_bundle()
    record["created_utc"] = datetime.now(timezone.utc).isoformat()
    record["adversarial_digest_quoted"] = bool(args.ack_adversarial)
    FREEZE_RECORD.write_text(json.dumps(record, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"bundle_sha256": record["bundle_sha256"],
                      "files": len(record["files"]),
                      "adversarial_digest_quoted": record["adversarial_digest_quoted"]}, indent=2))


if __name__ == "__main__":
    main()
