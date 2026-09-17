#!/usr/bin/env python3
"""Probe the obsolete cleanup interface on NEW synthetic Jumbo data.

Never invokes acquisition or opens a real source. Deliberately injected synthetic
foreign bytes are backed up outside the cleanup subject before testing. Failures
and before/after snapshots are retained; no cleanup retry occurs. Current production
refuses deletion. Maintained tests separately bind the frozen unsafe predecessor;
old traces/reports/checkpoints retain the original v1 harness and production bytes.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import os
from pathlib import Path
import stat

import acquire_msae_independent_norspan_v1 as acquisition


def inventory(root):
    return [{"path": p.relative_to(root).as_posix(), "device": p.lstat().st_dev,
             "inode": p.lstat().st_ino, "mode": stat.S_IMODE(p.lstat().st_mode),
             "nlink": p.lstat().st_nlink, "size": p.lstat().st_size}
            for p in sorted(root.rglob("*"))] if root.exists() else []


def probe(root, name):
    case = root / name; case.mkdir(mode=0o700)
    scratch = case / "scratch"; scratch.mkdir(mode=0o700)
    (scratch / "tracked").write_bytes(b"fixed owned synthetic evidence\n")
    foreign = b"fixed injected foreign evidence\n"
    (case / "foreign_before_image").write_bytes(foreign)
    (case / "owned_before_image").write_bytes((scratch / "tracked").read_bytes())
    if name == "foreign_extra":
        (scratch / "foreign").write_bytes(foreign)
    before = inventory(scratch)
    identity = scratch.lstat()
    parent = os.open(case, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    fd = os.open("scratch", os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=parent)
    real_unlink = os.unlink; injected = []
    def unlink(object_name, *, dir_fd):
        if name == "checked_then_substituted" and object_name == "tracked" and not injected:
            checked = os.stat(object_name, dir_fd=dir_fd, follow_symlinks=False)
            os.rename(object_name, "retained-original", src_dir_fd=dir_fd, dst_dir_fd=dir_fd)
            replacement = os.open(object_name, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
                                  0o600, dir_fd=dir_fd)
            try:
                os.write(replacement, foreign); os.fsync(replacement)
                s = os.fstat(replacement)
            finally:
                os.close(replacement)
            injected.append({"checked_device": checked.st_dev, "checked_inode": checked.st_ino,
                             "replacement_device": s.st_dev, "replacement_inode": s.st_ino})
        return real_unlink(object_name, dir_fd=dir_fd)
    error = None
    try:
        os.unlink = unlink
        acquisition.cleanup_scratch(scratch, parent, fd, identity)
    except BaseException as exc:
        error = {"type": type(exc).__name__, "message": str(exc), "errno": getattr(exc, "errno", None)}
    finally:
        os.unlink = real_unlink
        os.close(fd); os.close(parent)
    foreign_path = scratch / ("foreign" if name == "foreign_extra" else "tracked")
    return {"case": name, "before": before, "after": inventory(scratch), "error": error,
            "injected": injected, "foreign_name_preserved": foreign_path.exists(),
            "foreign_before_image_sha256": hashlib.sha256((case / "foreign_before_image").read_bytes()).hexdigest(),
            "result": "FAIL destructive synthetic foreign cleanup" if not foreign_path.exists() else "preserved"}


def main():
    parser = argparse.ArgumentParser(description=__doc__); parser.add_argument("--root", type=Path, required=True)
    root = parser.parse_args().root
    if not root.is_absolute() or root.parts[:2] != ("/", "jumbo") or ".." in root.parts:
        raise RuntimeError("fresh_absolute_jumbo_root_required")
    root.mkdir(mode=0o700)  # Exclusive; never reuse or remove an older subject.
    result = {"scope": "new synthetic interface-refusal probe only, not whole qualification",
              "cases": [probe(root, name) for name in ("foreign_extra", "checked_then_substituted")]}
    fd = os.open(root / "report.json", os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, "w") as out: out.write(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2))


if __name__ == "__main__": main()
