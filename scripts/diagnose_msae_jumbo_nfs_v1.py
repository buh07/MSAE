#!/usr/bin/env python3
"""Fresh synthetic Jumbo/NFS diagnostics; never reads actual experiment data.

Intentional link/unlink/cleanup scenarios manipulate ONLY subjects created here.
Historical cause is not inferred from an injected holder reproducing a symptom.
"""
from __future__ import annotations
import argparse
import collections
import json
import os
from pathlib import Path
import stat
import subprocess
import sys
import time

import acquire_msae_independent_norspan_v1 as acquisition


def metadata(s):
    return {"device": s.st_dev, "inode": s.st_ino, "mode": stat.S_IMODE(s.st_mode),
            "nlink": s.st_nlink, "size": s.st_size, "mtime_ns": s.st_mtime_ns,
            "ctime_ns": s.st_ctime_ns}


def snapshot(path):
    if not path.exists():
        return {"exists": False}
    result = {"exists": True, "root": metadata(path.lstat()), "entries": []}
    for p in sorted(path.rglob("*")):
        result["entries"].append({"path": p.relative_to(path).as_posix(), **metadata(p.lstat())})
    return result


def link_case(root, *, held):
    root.mkdir(mode=0o700)
    d = os.open(root, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    f = -1
    events = []
    try:
        f = os.open(".record.building", os.O_RDWR | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
                    0o600, dir_fd=d)
        os.fchmod(f, 0o644)
        payload = b"fixed synthetic diagnostic payload\n"
        os.write(f, payload)
        os.fsync(f)
        events.append({"operation": "stage_fsync", "fd": metadata(os.fstat(f))})
        if not held:
            os.close(f); f = -1
        os.link(".record.building", "record", src_dir_fd=d, dst_dir_fd=d, follow_symlinks=False)
        events.append({"operation": "link", "final": metadata(os.stat("record", dir_fd=d, follow_symlinks=False))})
        os.stat(".record.building", dir_fd=d, follow_symlinks=False)
        os.unlink(".record.building", dir_fd=d)
        final = os.stat("record", dir_fd=d, follow_symlinks=False)
        events.append({"operation": "unlink_then_stat", "final": metadata(final), "names": sorted(os.listdir(d))})
        status = "publication_metadata" if (final.st_nlink != 1 or final.st_size != len(payload)
                                               or stat.S_IMODE(final.st_mode) != 0o644) else "pass"
        os.fsync(d)
        return {"case": "legacy_held_writer" if held else "legacy_closed_writer",
                "introduced_holder": held, "status": status, "events": events,
                "before_holder_close": snapshot(root)}
    except OSError as e:
        return {"case": "legacy_held_writer" if held else "legacy_closed_writer",
                "introduced_holder": held, "status": "oserror", "errno": e.errno,
                "events": events, "failure_snapshot": snapshot(root)}
    finally:
        if f >= 0:
            os.close(f)
        os.close(d)


def scratch_case(root, *, held):
    root.mkdir(mode=0o700)
    repo = root / "repo"; repo.mkdir(mode=0o700)
    (repo / ".git").mkdir(mode=0o700)
    (repo / ".git/HEAD").write_bytes(b"fixed fake Git HEAD\n")
    (repo / "tracked").write_bytes(b"fixed synthetic fake source\n")
    (root / "home").mkdir(mode=0o700)
    holder = os.open(repo / "tracked", os.O_RDONLY | os.O_NOFOLLOW) if held else -1
    identity = root.lstat()
    parent = os.open(root.parent, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    fd = os.open(root.name, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=parent)
    before = snapshot(root)
    try:
        acquisition.cleanup_scratch(root, parent, fd, identity)
        result = {"case": "scratch_held_reader" if held else "scratch_closed_reader",
                  "introduced_holder": held, "status": "pass", "before": before,
                  "after": snapshot(root)}
    except OSError as e:
        result = {"case": "scratch_held_reader" if held else "scratch_closed_reader",
                  "introduced_holder": held, "status": "oserror", "errno": e.errno,
                  "before": before, "before_holder_close": snapshot(root)}
    finally:
        os.close(fd); os.close(parent)
        if holder >= 0:
            os.close(holder)
    # Observation only: do not retry removal or remove evidence.
    result["after_holder_close"] = snapshot(root)
    return result


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--root", type=Path, required=True)
    p.add_argument("--runs", type=int, default=64)
    a = p.parse_args()
    if not a.root.is_absolute() or a.root.parts[1:2] != ("jumbo",) or ".." in a.root.parts:
        p.error("root must be a fresh absolute Jumbo path")
    if not 1 <= a.runs <= 1000:
        p.error("runs outside [1,1000]")
    a.root.mkdir(mode=0o700)  # no exist_ok: never operate on retained subjects
    a.root.chmod(0o700)
    env = {}
    for name, argv in {"mount": ["findmnt", "-T", str(a.root), "-o", "TARGET,SOURCE,FSTYPE,OPTIONS"],
                       "capacity": ["df", "-Pk", str(a.root)], "kernel": ["uname", "-sr"]}.items():
        r = subprocess.run(argv, capture_output=True, timeout=20, check=True)
        env[name] = r.stdout.decode("utf-8", "strict")
    cases = []
    for i in range(a.runs):
        cases.append(link_case(a.root / f"legacy-closed-{i:04}", held=False))
        cases.append(scratch_case(a.root / f"scratch-closed-{i:04}", held=False))
    cases.append(link_case(a.root / "legacy-introduced-holder", held=True))
    cases.append(scratch_case(a.root / "scratch-introduced-holder", held=True))
    summary = collections.Counter((r["case"], r["status"], r.get("errno")) for r in cases)
    report = {"scope": "source-free fresh synthetic only; no historical-cause or production qualification",
              "utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "root": str(a.root),
              "runs": a.runs, "argv": sys.argv, "python": sys.version, "environment": env,
              "summary": [{"case": c, "status": s, "errno": e, "count": n}
                          for (c, s, e), n in summary.items()], "cases": cases,
              "historical_cause": "unproven; introduced holders are positive-control mechanisms only",
              "retries_of_failed_subject": 0, "old_evidence_cleanup": False}
    out = a.root / "diagnostics.json"
    with out.open("x") as f:
        json.dump(report, f, indent=2); f.write("\n")
    out.chmod(0o600)
    print(json.dumps({"root": str(a.root), "summary": report["summary"], "historical_cause": report["historical_cause"]}, indent=2))

if __name__ == "__main__":
    main()
