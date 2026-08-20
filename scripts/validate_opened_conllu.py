#!/usr/bin/env python3
"""Deterministically validate all opened local CoNLL-U bytes without model imports."""

from __future__ import annotations

import argparse
import hashlib
import json
import platform
from pathlib import Path
import re
from typing import Any

try:
    from .conllu_spec import ConlluError, ParseResult, parse_file, validate_unique_sent_ids
except ImportError:  # direct script execution
    from conllu_spec import ConlluError, ParseResult, parse_file, validate_unique_sent_ids

ROOT = Path(__file__).resolve().parents[1]


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def canonical_bytes(value: Any) -> bytes:
    return (json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False) + "\n").encode()


def _manifest_relative(path: Path, data_root: Path) -> str:
    return "data/" + path.relative_to(data_root).as_posix()


_SHA_RE = re.compile(r"[0-9a-f]{64}\Z")


def _artifact_path(value: str) -> Path:
    path = Path(value)
    return path if path.is_absolute() else ROOT / path


def verify_freeze(freeze_path: Path, manifest_path: Path) -> dict[str, Any]:
    freeze = json.loads(freeze_path.read_text(encoding="utf-8"))
    if freeze.get("schema_version") != "relational_objects_v2_parser_validation_freeze_v1" or freeze.get("profile") != "strict":
        raise ValueError("invalid parser-validation freeze schema/profile")
    inventory = freeze.get("inventory")
    required = {"plan", "parser", "validator", "tests", "profile_note", "manifest"}
    if (
        not isinstance(inventory, list)
        or len(inventory) != len(required)
        or any(not isinstance(item, dict) for item in inventory)
        or len({item.get("role") for item in inventory}) != len(required)
        or {item.get("role") for item in inventory} != required
    ):
        raise ValueError("freeze inventory roles are incomplete or duplicated")
    verified: list[dict[str, Any]] = []
    for item in inventory:
        if set(item) != {"role", "path", "sha256"} or not _SHA_RE.fullmatch(str(item["sha256"])):
            raise ValueError("malformed freeze inventory entry")
        path = _artifact_path(str(item["path"]))
        if not path.is_file() or sha256_file(path) != item["sha256"]:
            raise ValueError(f"frozen artifact drift: {item['role']}")
        verified.append(dict(item))
    manifest_item = next(item for item in verified if item["role"] == "manifest")
    if _artifact_path(str(manifest_item["path"])).resolve() != manifest_path.resolve():
        raise ValueError("manifest argument differs from frozen manifest")
    expected_python = str(freeze.get("python_version"))
    if platform.python_version() != expected_python:
        raise ValueError(f"Python runtime drift: expected {expected_python}, got {platform.python_version()}")
    return {"freeze_sha256": sha256_file(freeze_path), "python_version": expected_python, "inventory": verified}


def validate_manifest_schema(manifest: dict[str, Any]) -> list[dict[str, Any]]:
    if manifest.get("schema_version") != "relational_objects_v2_opened_conllu_manifest_v1":
        raise ValueError("invalid opened manifest schema_version")
    entries = manifest.get("entries")
    if not isinstance(entries, list) or not entries:
        raise ValueError("opened manifest must contain at least one expected entry")
    if manifest.get("expected_physical_files") != len(entries):
        raise ValueError("expected_physical_files does not match entries")
    scan_roots = manifest.get("scan_roots")
    if not isinstance(scan_roots, list) or not scan_roots or len(set(scan_roots)) != len(scan_roots):
        raise ValueError("scan_roots must be a nonempty unique list")
    if any(not _canonical_data_path(root) for root in scan_roots):
        raise ValueError("every scan_root must start with data/")
    declared: set[str] = set()
    for entry in entries:
        required = {"path", "sha256", "bytes", "manifest_group", "role"}
        if not isinstance(entry, dict) or not required.issubset(entry):
            raise ValueError("malformed opened manifest entry")
        path = str(entry["path"])
        if not _canonical_data_path(path) or path in declared:
            raise ValueError("manifest paths must be unique and start with data/")
        declared.add(path)
        if not _SHA_RE.fullmatch(str(entry["sha256"])) or not isinstance(entry["bytes"], int) or entry["bytes"] <= 0:
            raise ValueError("manifest hash/size is malformed")
        if not isinstance(entry["manifest_group"], str) or not entry["manifest_group"]:
            raise ValueError("manifest_group must be nonempty")
        if entry["role"] not in {"parser_opened_development", "parser_qa_derived_aggregate", "relational_object_development"}:
            raise ValueError("manifest role is unknown")
        if not any(path == root or path.startswith(root + "/") for root in scan_roots):
            raise ValueError("manifest entry is outside scan_roots")
    for entry in entries:
        parents = entry.get("derived_concatenation_of")
        if parents is None:
            continue
        if not isinstance(parents, list) or len(parents) < 2 or len(set(parents)) != len(parents):
            raise ValueError("derivation parents must be a distinct list of at least two paths")
        if entry["path"] in parents or any(parent not in declared for parent in parents):
            raise ValueError("derivation parent is self or undeclared")
    return entries


def _canonical_data_path(value: Any) -> bool:
    if not isinstance(value, str) or "\\" in value:
        return False
    path = Path(value)
    return bool(not path.is_absolute() and path.parts and path.parts[0] == "data" and all(part not in {".", ".."} for part in path.parts) and path.as_posix() == value)


def build_report(data_root: Path, manifest_path: Path, freeze_path: Path) -> dict[str, Any]:
    identity = verify_freeze(freeze_path, manifest_path)
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    expected_entries = validate_manifest_schema(manifest)
    expected_by_path = {str(entry["path"]): entry for entry in expected_entries}
    if len(expected_by_path) != len(expected_entries):
        raise ValueError("opened manifest repeats a physical path")
    paths_set: set[Path] = set()
    for raw_root in manifest["scan_roots"]:
        parts = Path(raw_root).parts
        scan_root = data_root.joinpath(*parts[1:])
        if scan_root.is_file():
            if scan_root.suffix == ".conllu":
                paths_set.add(scan_root)
        elif scan_root.exists():
            paths_set.update(scan_root.rglob("*.conllu"))
    paths = sorted(paths_set, key=lambda p: _manifest_relative(p, data_root).encode())
    discovered = {_manifest_relative(path, data_root): path for path in paths}
    coverage_errors: list[dict[str, Any]] = []
    for path in sorted(set(expected_by_path) - set(discovered)):
        coverage_errors.append({"code": "EXPECTED_PATH_MISSING", "path": path})
    for path in sorted(set(discovered) - set(expected_by_path)):
        coverage_errors.append({"code": "UNEXPECTED_PATH", "path": path, "sha256": sha256_file(discovered[path])})

    by_hash: dict[str, list[Path]] = {}
    for relative, expected in sorted(expected_by_path.items()):
        path = discovered.get(relative)
        if path is None:
            continue
        actual_hash = sha256_file(path)
        if actual_hash != expected["sha256"]:
            coverage_errors.append({"code": "HASH_MISMATCH", "path": relative, "expected": expected["sha256"], "actual": actual_hash})
            continue
        if path.stat().st_size != int(expected["bytes"]):
            coverage_errors.append({"code": "SIZE_MISMATCH", "path": relative, "expected": expected["bytes"], "actual": path.stat().st_size})
            continue
        by_hash.setdefault(actual_hash, []).append(path)

    for expected in expected_entries:
        derived = expected.get("derived_concatenation_of")
        if not derived:
            continue
        target = discovered.get(expected["path"])
        parents = [discovered.get(str(item)) for item in derived]
        if target is None or any(parent is None for parent in parents):
            continue
        if target.read_bytes() != b"".join(parent.read_bytes() for parent in parents if parent is not None):
            coverage_errors.append({"code": "DERIVATION_MISMATCH", "path": expected["path"], "derived_concatenation_of": derived})

    entries: list[dict[str, Any]] = []
    parse_cache: dict[str, ParseResult] = {}
    for digest in sorted(by_hash):
        copies = by_hash[digest]
        canonical = copies[0]
        relative = _manifest_relative(canonical, data_root)
        entry: dict[str, Any] = {
            "sha256": digest,
            "canonical_path": relative,
            "paths": [_manifest_relative(p, data_root) for p in copies],
            "bytes": canonical.stat().st_size,
        }
        try:
            result = parse_file(canonical, profile="strict")
            parse_cache[digest] = result
            entry.update(status="STRICT_PASS", sentences=len(result.sentences), rows=sum(len(s.rows) for s in result.sentences))
        except ConlluError as exc:
            entry.update(status="STRICT_FAIL", error={"code": exc.code, "line": exc.line, "detail": exc.detail})
            try:
                reader = parse_file(canonical, profile="reader")
                entry["reader"] = {"status": "PASS_WITH_DEVIATIONS", "deviations": list(reader.deviations), "sentences": len(reader.sentences)}
            except ConlluError as reader_exc:
                entry["reader"] = {"status": "FAIL", "error": {"code": reader_exc.code, "line": reader_exc.line, "detail": reader_exc.detail}}
        entries.append(entry)

    parsed_by_group: dict[str, list[tuple[str, ParseResult]]] = {}
    for expected in expected_entries:
        result = parse_cache.get(str(expected["sha256"]))
        if result is not None:
            parsed_by_group.setdefault(str(expected["manifest_group"]), []).append((str(expected["path"]), result))
    manifest_errors: list[dict[str, Any]] = []
    for parent in sorted(parsed_by_group):
        try:
            validate_unique_sent_ids(parsed_by_group[parent])
        except ConlluError as exc:
            manifest_errors.append({"treebank_root": parent, "code": exc.code, "source": exc.source, "line": exc.line, "detail": exc.detail})

    failures = sum(e["status"] != "STRICT_PASS" for e in entries) + len(manifest_errors) + len(coverage_errors)
    return {
        "schema_version": "opened_conllu_validation_v1",
        "profile": "strict",
        "official_specification": "https://universaldependencies.org/format.html",
        "model_imported": False,
        "model_forward_run": False,
        "data_root": data_root.relative_to(ROOT).as_posix() if data_root.is_relative_to(ROOT) else data_root.as_posix(),
        "opened_manifest_path": manifest_path.relative_to(ROOT).as_posix() if manifest_path.is_relative_to(ROOT) else manifest_path.as_posix(),
        "opened_manifest_sha256": sha256_file(manifest_path),
        "validation_identity": identity,
        "sent_id_manifest_rule": "use exact manifest_group; derived aggregates require byte-exact concatenation attestations",
        "scan_roots": manifest["scan_roots"],
        "physical_files": len(paths),
        "expected_physical_files": len(expected_entries),
        "distinct_byte_hashes": len(entries),
        "strict_pass_hashes": sum(e["status"] == "STRICT_PASS" for e in entries),
        "strict_failure_count": failures,
        "eligible_for_development_forward": failures == 0,
        "coverage_errors": coverage_errors,
        "manifest_errors": manifest_errors,
        "entries": entries,
    }


def render_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# Opened CoNLL-U strict-validation report",
        "",
        f"- Distinct hashes: `{report['distinct_byte_hashes']}` from `{report['physical_files']}` files",
        f"- Strict passes: `{report['strict_pass_hashes']}`",
        f"- Strict failures: `{report['strict_failure_count']}`",
        f"- Development forward eligible: `{str(report['eligible_for_development_forward']).lower()}`",
        "- Model import/forward: `false` / `false`",
        "",
        "| SHA-256 | Canonical path | Status | Sentences/error |",
        "|---|---|---:|---|",
    ]
    for entry in report["entries"]:
        detail = str(entry.get("sentences", ""))
        if "error" in entry:
            err = entry["error"]
            detail = f"{err['code']} at line {err['line']}: {err['detail']}"
        lines.append(f"| `{entry['sha256']}` | `{entry['canonical_path']}` | {entry['status']} | {detail} |")
    if report["coverage_errors"]:
        lines += ["", "## Coverage errors", ""]
        for err in report["coverage_errors"]:
            lines.append(f"- `{err['code']}`: `{err.get('path', '')}`")
    if report["manifest_errors"]:
        lines += ["", "## Manifest-wide errors", ""]
        for err in report["manifest_errors"]:
            lines.append(f"- `{err['treebank_root']}`: `{err['code']}` — {err['detail']}")
    return "\n".join(lines) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-root", type=Path, default=ROOT / "data")
    parser.add_argument("--manifest", type=Path, default=ROOT / "configs" / "relational_objects_v2" / "development_conllu_manifest.json")
    parser.add_argument("--freeze", type=Path, default=ROOT / "configs" / "relational_objects_v2" / "parser_validation_freeze.json")
    parser.add_argument("--json", type=Path, default=ROOT / "reports" / "opened_development_conllu_validation_v1.json")
    parser.add_argument("--markdown", type=Path, default=ROOT / "reports" / "opened_development_conllu_validation_v1.md")
    args = parser.parse_args()
    report = build_report(args.data_root.resolve(), args.manifest.resolve(), args.freeze.resolve())
    args.json.parent.mkdir(parents=True, exist_ok=True)
    args.json.write_bytes(canonical_bytes(report))
    args.markdown.write_text(render_markdown(report), encoding="utf-8")
    print(json.dumps({k: report[k] for k in ("physical_files", "distinct_byte_hashes", "strict_pass_hashes", "strict_failure_count", "eligible_for_development_forward")}, sort_keys=True))


if __name__ == "__main__":
    main()
