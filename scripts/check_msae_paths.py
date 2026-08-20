#!/usr/bin/env python3
"""Check live MSAE paths without rewriting frozen historical artifacts."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path


OBSOLETE = "/jumbo/lisp/f004ndc" + "/MSAE"
LIVE_GLOBS = ("*.md", "scripts/*.sh", "scripts/*.py")
MD_LINK = re.compile(r"\[[^]]*\]\(([^)#]+)(?:#[^)]*)?\)")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    args = parser.parse_args()
    root = args.root.resolve()
    failures: list[str] = []
    checked: list[str] = []

    for pattern in LIVE_GLOBS:
        for path in sorted(root.glob(pattern)):
            if not path.is_file():
                continue
            rel = path.relative_to(root).as_posix()
            checked.append(rel)
            text = path.read_text(errors="replace")
            if path.suffix != ".md" and OBSOLETE in text:
                failures.append(f"obsolete absolute root: {rel}")
            if path.suffix == ".md":
                for target in MD_LINK.findall(text):
                    if target.startswith(OBSOLETE):
                        failures.append(f"obsolete absolute link: {rel} -> {target}")
                        continue
                    if "://" in target or target.startswith(("mailto:", "/", "#")):
                        continue
                    resolved = (path.parent / target).resolve()
                    if not resolved.exists():
                        failures.append(f"broken local link: {rel} -> {target}")

    path_map = root / "reports/provenance/path_map.json"
    if not path_map.exists():
        failures.append("missing reports/provenance/path_map.json")
    else:
        mapping = json.loads(path_map.read_text())
        if Path(mapping["current_root"]).resolve() != root:
            failures.append("path_map current_root does not resolve to --root")

    print(json.dumps({"root": str(root), "checked": checked, "failures": failures}, indent=2))
    return bool(failures)


if __name__ == "__main__":
    sys.exit(main())
