"""Frozen public predecessor cleanup, ONLY for fresh synthetic defect reproductions.

Extracted without function edits from runner SHA256
7aa98231181fd19061726a68b004079a0c13310d0fcfa7f7938f45ef61ae2f4c.
NOT a production API. Production now refuses this obsolete destructive operation.
"""
import os
from pathlib import Path
import stat
import types

class GateFailure(RuntimeError):
    pass

protocol = types.SimpleNamespace(GateFailure=GateFailure)

def remove_tree_fd(fd: int) -> None:
    for name in os.listdir(fd):
        st = os.stat(name, dir_fd=fd, follow_symlinks=False)
        if stat.S_ISDIR(st.st_mode):
            child = os.open(name, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0)
                            | getattr(os, "O_NOFOLLOW", 0), dir_fd=fd)
            try:
                if (os.fstat(child).st_dev, os.fstat(child).st_ino) != (st.st_dev, st.st_ino):
                    raise protocol.GateFailure("scratch_identity_drift")
                remove_tree_fd(child)
            finally:
                os.close(child)
            os.rmdir(name, dir_fd=fd)
        else:
            os.unlink(name, dir_fd=fd)
    os.fsync(fd)

def cleanup_scratch(scratch: Path, parent_fd: int, scratch_fd: int,
                    identity: os.stat_result) -> None:
    current = os.stat(scratch.name, dir_fd=parent_fd, follow_symlinks=False)
    opened = os.fstat(scratch_fd)
    if ((current.st_dev, current.st_ino) != (identity.st_dev, identity.st_ino)
            or (opened.st_dev, opened.st_ino) != (identity.st_dev, identity.st_ino)):
        raise protocol.GateFailure("scratch_identity_drift")
    remove_tree_fd(scratch_fd)
    os.rmdir(scratch.name, dir_fd=parent_fd)
    os.fsync(parent_fd)
    try:
        os.stat(scratch.name, dir_fd=parent_fd, follow_symlinks=False)
    except FileNotFoundError:
        return
    raise protocol.GateFailure("scratch_cleanup_unproved")
