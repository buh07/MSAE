#!/usr/bin/env python3
"""Closed post-gen2 controller for the MSAE gen5 successor protocol."""
from __future__ import annotations
import sys

# Remove the interpreter-added script directory using built-in-only operations
# before importing even standard-library modules.  The authorized commands use
# ``-I`` (so this is normally already absent), but a rejected non-isolated
# invocation must not get a pre-gate shadow-import opportunity either.
_early_script_directory = __file__.rpartition("/")[0]
sys.path[:] = [entry for entry in sys.path
               if entry != _early_script_directory
               and not (_early_script_directory == "scripts"
                        and entry.endswith("/scripts"))]

import importlib.machinery
import importlib.util
import os
import stat
from pathlib import Path
from typing import Any, Sequence

ROOT = Path(__file__).resolve().parents[1]

# ``-B`` disables bytecode writes, not bytecode reads.  The repository already
# contains ignored ``scripts/__pycache__`` entries, so every local module in the
# authorized execution closure is loaded from its reviewed source bytes by this
# exact finder/loader.  In particular, no timestamp-valid local ``.pyc`` can run
# before the static and behavioral closure gates.
SOURCE_ONLY_LOCAL_MODULES = frozenset({
    "msae_independent_measurement_v3",
    "msae_independent_measurement_v3_post_m1",
    "msae_independent_measurement_v3_post_m1_runtime",
    "msae_independent_measurement_v3_post_m2_gen5",
    "msae_independent_measurement_v3_post_m2_gen5_runtime",
    "msae_measurement_remediation_v1",
    "msae_measurement_v2",
    "run_msae_independent_calibration_v3",
    "run_msae_independent_calibration_v3_gen5",
})


def _source_only_bytes(path: Path) -> bytes:
    """Descriptor-safely read one owned, one-link local Python source file."""
    source = Path(path)
    directory = source.parent
    directory_fd = os.open(
        directory, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC)
    source_fd = -1
    try:
        directory_before = os.fstat(directory_fd)
        directory_path = directory.lstat()
        if (not stat.S_ISDIR(directory_before.st_mode)
                or stat.S_ISLNK(directory_path.st_mode)
                or (directory_before.st_dev, directory_before.st_ino) !=
                   (directory_path.st_dev, directory_path.st_ino)
                or directory_before.st_uid != os.getuid()
                or stat.S_IMODE(directory_before.st_mode) & 0o022):
            raise ImportError(f"unsafe source-only module directory: {directory}")
        source_fd = os.open(
            source.name, os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC,
            dir_fd=directory_fd)
        before = os.fstat(source_fd)
        if (not stat.S_ISREG(before.st_mode) or before.st_uid != os.getuid()
                or before.st_nlink != 1 or stat.S_IMODE(before.st_mode) & 0o022):
            raise ImportError(f"unsafe source-only module file: {source}")
        chunks: list[bytes] = []
        while True:
            chunk = os.read(source_fd, 1024 * 1024)
            if not chunk:
                break
            chunks.append(chunk)
        after = os.fstat(source_fd)
        source_path = source.lstat()
        directory_after = os.fstat(directory_fd)
        before_identity = (before.st_dev, before.st_ino, before.st_mode, before.st_uid,
                           before.st_nlink, before.st_size, before.st_mtime_ns,
                           before.st_ctime_ns)
        after_identity = (after.st_dev, after.st_ino, after.st_mode, after.st_uid,
                          after.st_nlink, after.st_size, after.st_mtime_ns,
                          after.st_ctime_ns)
        path_identity = (source_path.st_dev, source_path.st_ino, source_path.st_mode,
                         source_path.st_uid, source_path.st_nlink, source_path.st_size,
                         source_path.st_mtime_ns, source_path.st_ctime_ns)
        if (before_identity != after_identity or after_identity != path_identity
                or (directory_before.st_dev, directory_before.st_ino,
                    directory_before.st_mode, directory_before.st_uid) !=
                   (directory_after.st_dev, directory_after.st_ino,
                    directory_after.st_mode, directory_after.st_uid)):
            raise ImportError(f"source-only module changed during read: {source}")
        raw = b"".join(chunks)
        if len(raw) != before.st_size:
            raise ImportError(f"short source-only module read: {source}")
        return raw
    finally:
        if source_fd >= 0:
            os.close(source_fd)
        os.close(directory_fd)


class _SourceOnlyLoader(importlib.machinery.SourceFileLoader):
    def __init__(self, fullname: str, source: Path):
        self.source = Path(source)
        super().__init__(fullname, str(self.source))

    def path_stats(self, path: str) -> dict[str, Any]:
        del path
        # Raising here makes the standard source loader skip the bytecode-cache
        # lookup completely and compile the bytes returned by ``get_data``.
        raise OSError("source-only local module has no bytecode-cache metadata")

    def set_data(self, path: str, data: bytes, **kwargs: Any) -> None:
        del path, data, kwargs
        return None

    def get_data(self, path: str) -> bytes:
        if Path(path) != self.source:
            raise OSError(f"source-only loader rejected non-source path: {path}")
        return _source_only_bytes(self.source)


def source_only_module_spec(fullname: str, source: Path) -> Any:
    """Return a module spec whose loader cannot consult bytecode caches."""
    path = Path(source)
    if path.suffix != ".py" or not fullname or "/" in fullname or "\\" in fullname:
        raise ImportError(f"source-only module name/path mismatch: {fullname} {path}")
    spec = importlib.util.spec_from_loader(
        fullname, _SourceOnlyLoader(fullname, path), origin=str(path))
    if spec is None or spec.loader is None:
        raise ImportError(f"cannot construct source-only module spec: {fullname}")
    spec.has_location = True
    spec.cached = None
    return spec


class _SourceOnlyFinder:
    _msae_source_only_finder = True

    def __init__(self, scripts: Path):
        self.scripts = Path(scripts)

    def find_spec(self, fullname: str, path: Any = None, target: Any = None) -> Any:
        del path, target
        if fullname not in SOURCE_ONLY_LOCAL_MODULES:
            return None
        source = self.scripts / f"{fullname}.py"
        if source.name != f"{fullname}.py":
            raise ImportError(f"invalid source-only local module name: {fullname}")
        return source_only_module_spec(fullname, source)


def install_source_only_imports(scripts: Path | None = None) -> None:
    """Install the exact local-source finder once, before any local import."""
    expected = Path(scripts) if scripts is not None else ROOT / "scripts"
    existing = [finder for finder in sys.meta_path
                if finder.__class__.__dict__.get("_msae_source_only_finder") is True]
    if existing:
        if len(existing) != 1 or Path(existing[0].scripts) != expected:
            raise ImportError("conflicting source-only local-module finder")
        return
    sys.meta_path.insert(0, _SourceOnlyFinder(expected))


def sanitize_local_module_search_path(scripts: Path | None = None) -> None:
    """Keep the local scripts directory out of the default path finder."""
    forbidden = str(Path(scripts) if scripts is not None else ROOT / "scripts")
    sys.path[:] = [entry for entry in sys.path if entry != forbidden]
    if forbidden in sys.path:
        raise ImportError("local scripts directory survived source-only path sanitization")


sanitize_local_module_search_path()
install_source_only_imports()
import msae_independent_measurement_v3 as base
import msae_independent_measurement_v3_post_m1 as immutable_continuation
sanitize_local_module_search_path()

CONTROLLER_PATH = Path(__file__)
PLAN_PATH = ROOT / "docs/plan-msae-independent-measurement-v3-post-m5-gen5.md"
PLAN_REVIEW_PATH = ROOT / "reports/adversarial/msae_independent_measurement_v3_post_m2_gen5_plan.md"

# Only non-executing utilities needed by the runner are re-exported. Historical
# build/sign/launch/broker attributes are deliberately not forwarded.
PROTOCOL = base.PROTOCOL
V3_DATA = base.V3_DATA
V3_CONFIG = base.V3_CONFIG
V3_PROV = base.V3_PROV
GPU_LOCK_DIR = base.GPU_LOCK_DIR
SNAPSHOT = base.SNAPSHOT
PRIVATE_KEY = base.PRIVATE_KEY
PRIMARY_BUILD_ROOT = base.PRIMARY_BUILD_ROOT
REBUILD_BUILD_ROOT = base.REBUILD_BUILD_ROOT
STATE_ROOT = base.STATE_ROOT
NONCE_DIR = base.NONCE_DIR
RUN_ROOT = base.RUN_ROOT
QUARANTINED = base.QUARANTINED
V3_DATA_PHASE_FILES = base.V3_DATA_PHASE_FILES
canonical_bytes = base.canonical_bytes
sha_bytes = base.sha_bytes
sha_file = base.sha_file
read_json = base.read_json
write_once = base.write_once
install_json = base.install_json
strict_json_loads = base.strict_json_loads
validate_sha256 = base.validate_sha256
_content_entry = base._content_entry
_fsync_directory = base._fsync_directory
_start_ticks = base._start_ticks
_directory_binding = base._directory_binding
_secure_directory = base._secure_directory
quarantine_open_tripwire = base.quarantine_open_tripwire
verify_baseline_projection = base.verify_baseline_projection
counterfactual_alignment_qa = base.counterfactual_alignment_qa

verify_m1_completion = immutable_continuation.verify_m1_completion
extend_closure_payload = immutable_continuation.extend_closure_payload


def __getattr__(name: str) -> Any:
    raise AttributeError(f"gen5 controller does not expose legacy attribute: {name}")


def main(argv: Sequence[str] | None = None) -> None:
    raw = list(sys.argv[1:] if argv is None else argv)
    if not raw:
        raise SystemExit("a command is required")
    # Every supported command is successor-owned. M1/M2 construction and every
    # historical post-M2 execution route are terminally unavailable here.
    from msae_independent_measurement_v3_post_m2_gen5_runtime import dispatch
    dispatch(raw)


if __name__ == "__main__":
    main()
